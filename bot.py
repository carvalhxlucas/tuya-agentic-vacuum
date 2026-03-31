import asyncio
import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TimedOut
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from agent import create_agent, execute_agent
from agent.tools import get_device_state, list_devices, save_device_id

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent


def _user_id(update: Update) -> str:
    return str(update.effective_user.id) if update.effective_user else "default"


QUICK_ACTIONS_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("▶️ Iniciar", callback_data="action:start_cleaning"),
        InlineKeyboardButton("⏸️ Pausar", callback_data="action:stop_cleaning"),
    ],
    [
        InlineKeyboardButton("🏠 Base", callback_data="action:return_to_base"),
        InlineKeyboardButton("📍 Localizar", callback_data="action:locate_robot"),
    ],
])

ACTION_MESSAGES = {
    "action:start_cleaning": "iniciar limpeza",
    "action:stop_cleaning": "pausar limpeza",
    "action:return_to_base": "voltar para a base",
    "action:locate_robot": "localizar o robô",
}

STATUS_LABELS = {
    "cleaning": "🤖 Limpando",
    "docked": "🔌 Na base",
    "idle": "💤 Parado",
    "returning": "🔄 Voltando para base",
    "error": "❌ Erro",
}

MODE_LABELS = {
    "standby": "Standby",
    "smart": "Inteligente",
    "random": "Aleatório",
    "spiral": "Espiral",
    "wall_follow": "Bordas",
    "mop": "Esfregão",
    "left_bow": "Arco esquerda",
    "right_bow": "Arco direita",
    "left_spiral": "Espiral esquerda",
    "right_spiral": "Espiral direita",
    "partial_bow": "Arco parcial",
    "chargego": "Retornando para base",
}


def _format_time(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h}h {m:02d}min"
    return f"{m}min"


def _build_status_text(state: dict) -> str:
    status_label = STATUS_LABELS.get(state["status"], state["status"])
    battery = state.get("batteryLevel", 0)
    mode = MODE_LABELS.get(state.get("mode", "standby"), state.get("mode", ""))
    total_area = state.get("totalCleanArea", 0)
    total_time = state.get("totalCleanTime", 0)
    clean_count = state.get("cleanCount", 0)

    lines = [
        f"{status_label}  🔋 {battery}%",
        f"Modo: {mode}",
        "",
        f"📐 {total_area} m² limpos no total",
        f"⏱️ {_format_time(total_time)} de limpeza",
        f"🔁 {clean_count} limpezas realizadas",
    ]
    return "\n".join(lines)


def _transcribe_audio(file_path: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        with open(file_path, "rb") as f:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=f)
        return transcript.text.strip()
    except Exception as e:
        logger.error("Whisper transcription error: %s", e)
        return None


async def cmd_devices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    devices = await asyncio.to_thread(list_devices)

    if not devices:
        await update.message.reply_text(
            "Nenhum dispositivo encontrado.\n\n"
            "Verifique se o TUYA_ACCESS_ID e TUYA_ACCESS_SECRET estão corretos "
            "e se há dispositivos vinculados ao seu projeto na Tuya IoT Platform."
        )
        return

    keyboard = [
        [InlineKeyboardButton(
            f"🤖 {d.get('name', 'Dispositivo')} — {d.get('product_name', d.get('id', ''))}",
            callback_data=f"device:{d['id']}",
        )]
        for d in devices
    ]
    await update.message.reply_text(
        f"*{len(devices)} dispositivo(s) encontrado(s).* Selecione qual deseja controlar:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Olá! Sou o assistente do seu robô aspirador 🤖\n\n"
        "Me diga o que ele deve fazer em linguagem natural, mande um áudio, "
        "ou use os botões abaixo para ações rápidas.\n\n"
        "Comandos disponíveis:\n"
        "/status — estado atual do robô\n"
        "/devices — selecionar dispositivo Tuya",
        reply_markup=QUICK_ACTIONS_KEYBOARD,
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    state = await asyncio.to_thread(get_device_state)
    if state is None:
        await update.message.reply_text(
            "❌ Não foi possível obter o estado do robô. Verifique as credenciais Tuya no .env.",
        )
        return
    await update.message.reply_text(
        _build_status_text(state),
        reply_markup=QUICK_ACTIONS_KEYBOARD,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if not text or not text.strip():
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        message, _, _ = await asyncio.to_thread(execute_agent, _get_agent(), text.strip(), _user_id(update))
    except Exception as e:
        logger.error("Agent error: %s", e)
        await update.message.reply_text("Ocorreu um erro ao processar o comando. Tente novamente.")
        return
    await update.message.reply_text(message, reply_markup=QUICK_ACTIONS_KEYBOARD)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if not os.getenv("OPENAI_API_KEY"):
        await update.message.reply_text(
            "Mensagens de voz precisam do OPENAI_API_KEY configurado no .env."
        )
        return

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name
        await voice_file.download_to_drive(tmp_path)
    except Exception as e:
        logger.error("Voice download error: %s", e)
        await update.message.reply_text("Não consegui processar o áudio. Tente novamente.")
        return

    text = await asyncio.to_thread(_transcribe_audio, tmp_path)

    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    if not text:
        await update.message.reply_text("Não entendi o áudio. Pode repetir ou digitar o comando?")
        return

    logger.info("Voice transcribed: %s", text)

    try:
        message, _, _ = await asyncio.to_thread(execute_agent, _get_agent(), text, _user_id(update))
    except Exception as e:
        logger.error("Agent error: %s", e)
        await update.message.reply_text("Ocorreu um erro ao processar o comando.")
        return

    await update.message.reply_text(
        f'🎙️ _"{text}"_\n\n{message}',
        parse_mode="Markdown",
        reply_markup=QUICK_ACTIONS_KEYBOARD,
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data.startswith("device:"):
        device_id = query.data.removeprefix("device:")
        save_device_id(device_id)
        await query.edit_message_text(
            f"✅ Dispositivo selecionado e salvo!\n\n"
            f"ID: `{device_id}`\n\n"
            "Você já pode enviar comandos.",
            parse_mode="Markdown",
        )
        return

    natural_message = ACTION_MESSAGES.get(query.data)
    if not natural_message:
        return

    try:
        message, _, _ = await asyncio.to_thread(execute_agent, _get_agent(), natural_message, _user_id(update))
    except Exception as e:
        logger.error("Agent error: %s", e)
        await query.edit_message_text("Ocorreu um erro ao processar o comando.")
        return

    await query.edit_message_text(message, reply_markup=QUICK_ACTIONS_KEYBOARD)


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, TimedOut):
        logger.warning("Telegram request timed out (transient): %s", context.error)
        return
    logger.error("Unhandled exception", exc_info=context.error)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN não configurado no .env")

    app = Application.builder().token(token).build()
    app.add_error_handler(handle_error)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("devices", cmd_devices))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^(action:|device:)"))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot iniciado. Aguardando mensagens...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
