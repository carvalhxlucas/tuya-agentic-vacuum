import logging
import os
import re
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

from agent.tools import (
    locate_robot,
    return_to_base,
    set_clean_mode,
    start_cleaning,
    stop_cleaning,
)

ROBOT_TOOLS = [start_cleaning, stop_cleaning, return_to_base, locate_robot, set_clean_mode]

SYSTEM_PROMPT = """You are the control assistant for a vacuum robot. The user gives commands in natural language.
Your task is to interpret the intent and use EXACTLY one of the available tools.
Always respond in the same language the user wrote in — if they write in Portuguese, respond in Portuguese; if in English, respond in English.
Respond briefly and in a friendly way, confirming the action executed.
Use only the provided tools; do not invent other actions."""

CONFIRMATION_PROMPT = """The vacuum robot successfully executed the command: {action_desc}.
Write ONE short, friendly sentence confirming this to the user.
Respond in the same language as the user's original message: "{user_message}"
Do not add explanations, just the confirmation."""

ACTION_DESCRIPTIONS = {
    "start_cleaning": "started cleaning",
    "stop_cleaning": "paused / stopped cleaning",
    "return_to_base": "is returning to the charging base",
    "locate_robot": "emitted a locate signal (beep)",
    "set_clean_mode": "changed the cleaning mode to {mode}",
}

FALLBACK_MESSAGES_PT = {
    "start_cleaning": "Certo, iniciando a limpeza agora.",
    "stop_cleaning": "Certo, pausando o robô.",
    "return_to_base": "Certo, enviando o robô de volta para a base.",
    "locate_robot": "Certo, enviando o sinal de localização.",
    "set_clean_mode": "Certo, modo de limpeza alterado para {mode}.",
}

FALLBACK_MESSAGES_EN = {
    "start_cleaning": "Got it, starting cleaning now.",
    "stop_cleaning": "Got it, pausing the robot.",
    "return_to_base": "Got it, sending the robot back to base.",
    "locate_robot": "Got it, sending locate signal.",
    "set_clean_mode": "Got it, switching to {mode} mode.",
}


def _is_portuguese(text: str) -> bool:
    pt_words = {"limpar", "limpa", "limpeza", "iniciar", "inicia", "começa", "começar",
                "parar", "para", "pausar", "pausa", "voltar", "volta", "base", "carregar",
                "localizar", "localiza", "onde", "modo", "espiral", "aleatorio", "aleatório"}
    words = set(text.lower().split())
    return bool(words & pt_words)


def _friendly_message(action: str, params: dict, user_message: str) -> str:
    mode = (params or {}).get("mode", "") if isinstance(params, dict) else ""
    messages = FALLBACK_MESSAGES_PT if _is_portuguese(user_message) else FALLBACK_MESSAGES_EN
    template = messages.get(action, "Command executed.")
    return template.format(mode=mode) if "{mode}" in template else template


def _generate_confirmation(llm: Any, action_name: str, args: dict, user_message: str) -> str:
    try:
        mode = (args or {}).get("mode", "") if isinstance(args, dict) else ""
        desc = ACTION_DESCRIPTIONS.get(action_name, action_name).format(mode=mode)
        prompt = CONFIRMATION_PROMPT.format(action_desc=desc, user_message=user_message)
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception:
        return _friendly_message(action_name, args, user_message)


def _fallback_intent(message: str) -> tuple[str, Optional[str], Optional[dict]]:
    text = message.lower().strip()
    pt = _is_portuguese(text)

    if any(w in text for w in ["clean", "vacuum", "start", "sweep", "begin",
                                "limpar", "limpa", "aspirar", "iniciar", "começa", "começar", "limpeza"]):
        return (_friendly_message("start_cleaning", {}, message), "start_cleaning", None)

    if any(w in text for w in ["stop", "pause", "halt", "parar", "pausar", "para", "pausa"]):
        return (_friendly_message("stop_cleaning", {}, message), "stop_cleaning", None)

    if any(w in text for w in ["return", "base", "dock", "charge", "go back",
                                "voltar", "volta", "base", "carregar", "carrega"]):
        return (_friendly_message("return_to_base", {}, message), "return_to_base", None)

    if any(w in text for w in ["locate", "find", "where is",
                                "localizar", "localiza", "onde", "encontrar"]):
        return (_friendly_message("locate_robot", {}, message), "locate_robot", None)

    if any(w in text for w in ["mode", "smart", "random", "spiral", "mop", "wall",
                                "modo", "espiral", "aleatorio", "aleatório", "esfregão"]):
        mode = "smart"
        if "random" in text or "aleatorio" in text or "aleatório" in text:
            mode = "random"
        elif "spiral" in text or "espiral" in text:
            mode = "spiral"
        elif "wall" in text:
            mode = "wall_follow"
        elif "mop" in text or "esfregão" in text:
            mode = "mop"
        return (_friendly_message("set_clean_mode", {"mode": mode}, message), "set_clean_mode", {"mode": mode})

    if pt:
        return ("Não entendi o comando. Você pode pedir para iniciar ou pausar a limpeza, voltar para a base, localizar o robô ou mudar o modo de limpeza.", None, None)
    return ("I didn't recognize a valid command. You can ask to start or pause cleaning, return to base, locate the robot, or change the cleaning mode.", None, None)


def _is_error(result: str) -> bool:
    lowered = result.lower()
    return any(w in lowered for w in ("not configured", "failed", "rejected", "error", "invalid"))


def create_agent() -> Any:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
            return {"type": "langchain", "llm": llm.bind_tools(ROBOT_TOOLS), "llm_base": llm}
        except Exception:
            pass
    return {"type": "fallback"}


def execute_agent(agent: Any, message: str) -> tuple[str, Optional[str], Optional[dict]]:
    if agent.get("type") == "fallback":
        return _fallback_intent(message)
    llm = agent.get("llm")
    if not llm:
        return _fallback_intent(message)
    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=message),
        ]
        response = llm.invoke(messages)
        if hasattr(response, "tool_calls") and response.tool_calls:
            tc = response.tool_calls[0]
            name = tc.get("name") or (getattr(tc, "name", None))
            args = tc.get("args") or {}
            if hasattr(tc, "args"):
                args = tc.args or args
            tool_map = {t.name: t for t in ROBOT_TOOLS}
            if name in tool_map:
                logger.info("Calling tool %s with args %s", name, args)
                result = tool_map[name].invoke(args)
                logger.info("Tool %s returned: %s", name, result)
                if isinstance(result, str) and _is_error(result):
                    return (result, None, None)
                confirmation = _generate_confirmation(agent["llm_base"], name, args, message)
                return (confirmation, name, args if isinstance(args, dict) else None)
        return (response.content or "Command processed.", None, None)
    except Exception as e:
        logger.error("Agent error: %s", e)
        return _fallback_intent(message)
