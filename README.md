# Tuya Agentic Vacuum

Control your Tuya-compatible robot vacuum with natural language via Telegram. Send text or voice messages and an AI agent translates them into device commands. Runs fully locally — no cloud AI required.

## How it works

```
Telegram message (text or voice)
        ↓
   AI Agent (Ollama local · OpenAI fallback · regex fallback)
        ↓
   Tuya Open Platform API
        ↓
   Robot vacuum
```

## Prerequisites

- Python 3.11+
- A Tuya-compatible robot vacuum
- [Ollama](https://ollama.com) installed locally (recommended)
- A [Tuya IoT Platform](https://iot.tuya.com) developer account
- A Telegram bot token (via [@BotFather](https://t.me/botfather))

## 1. Ollama setup (recommended)

Ollama runs the AI model locally — no API keys or internet required for the agent.

```bash
# Install Ollama from https://ollama.com, then pull the default model:
ollama pull qwen2.5:3b
```

`qwen2.5:3b` requires ~4 GB of RAM and works well for intent classification and multilingual responses. You can swap it for any model that supports tool calling (e.g. `llama3.2:3b`, `mistral:7b`).

## 2. Tuya IoT Platform setup

1. Sign in at the Tuya IoT Platform and create a **Cloud Development** project
2. Under **Overview**, copy your **Access ID** and **Access Secret**
3. Go to **Devices → Link Tuya App Account** and link your Smart Life / Tuya Smart account — this makes your devices visible to the project
4. Set the API endpoint based on your region:
   - Americas: `https://openapi.tuyaus.com`
   - Europe: `https://openapi.tuyaeu.com`
   - China: `https://openapi.tuyacn.com`
   - India: `https://openapi.tuyain.com`

## 3. Telegram bot setup

1. Open Telegram and start a conversation with [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the prompts
3. Copy the token BotFather gives you

## 4. Configure

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
OLLAMA_MODEL=qwen2.5:3b         # or any tool-calling model you have pulled
TUYA_ACCESS_ID=...
TUYA_ACCESS_SECRET=...
TUYA_API_ENDPOINT=https://openapi.tuyaus.com
TELEGRAM_BOT_TOKEN=...
```

> `TUYA_DEVICE_ID` is not required — use `/devices` in the bot to discover and select your robot.

## 5. Install and run

```bash
pip install -r requirements.txt
python3 bot.py
```

## 6. First use

1. Open your bot on Telegram and send `/start`
2. Send `/devices` — select your robot from the list
3. Start sending commands:
   - *"Começa a limpar"* / *"Start cleaning"*
   - *"Volta para a base"* / *"Return to base"*
   - *"Modo espiral"* / *"Clean in spiral mode"*
   - Or send a **voice message** (requires `OPENAI_API_KEY` for Whisper transcription)

## Bot commands

| Command | Description |
|---|---|
| `/start` | Welcome message and quick action buttons |
| `/status` | Current status, battery, mode and cleaning stats |
| `/devices` | List and select which Tuya device to control |

## LLM fallback chain

The agent tries each option in order:

1. **Ollama** — local, no cost, requires Ollama running with a tool-calling model
2. **OpenAI** — cloud fallback, set `OPENAI_API_KEY` in `.env`
3. **Regex** — no LLM at all, handles the most common commands

Voice messages require `OPENAI_API_KEY` (Whisper) regardless of which LLM is used for text.

## Supported cleaning modes

`smart` · `random` · `spiral` · `wall_follow` · `mop` · `left_bow` · `right_bow`
