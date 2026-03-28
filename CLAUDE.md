# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A natural-language vacuum robot controller. The user types commands in a chat UI; the backend interprets them via an LLM (GPT-4o-mini via LangChain) or a regex-based fallback, then dispatches Tuya IoT API commands to the physical robot.

## Structure

- `main.py` — FastAPI app
- `bot.py` — Telegram bot (interface principal)
- `agent/` — agente LangChain + ferramentas Tuya

## Backend

### Running

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in credentials
python3 bot.py          # bot do Telegram (interface principal)
uvicorn main:app --reload  # API REST (opcional, sem frontend)
```

### Environment variables (`.env`)

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | If present, uses GPT-4o-mini; otherwise falls back to regex intent matching |
| `TUYA_ACCESS_ID` | Tuya Open Platform access ID |
| `TUYA_ACCESS_SECRET` | Tuya Open Platform access secret |
| `TUYA_DEVICE_ID` | Target vacuum device ID |
| `TUYA_API_ENDPOINT` | Defaults to `https://openapi.tuyaus.com` |
| `TELEGRAM_BOT_TOKEN` | Token do bot do Telegram (obter via @BotFather) |

### Agent architecture

`agent/runner.py` — `create_agent()` returns a dict `{"type": "langchain", "llm": ...}` or `{"type": "fallback"}`. `execute_agent()` calls the LLM with tool bindings; on any failure it falls back to `_fallback_intent()` (keyword/regex matching).

`agent/tools.py` — LangChain `@tool`-decorated functions that call `_send_commands()` → Tuya REST API. The Tuya client is a module-level singleton (lazy-initialized on first use).

### API endpoints

- `GET /health` — liveness check
- `GET /robot/state` — returns `{status, batteryLevel}` from live Tuya device
- `POST /chat` — accepts `{message}`, returns `{message, actionPayload?}`

## Telegram Bot (`bot.py`)

The bot is the primary interface. Handlers:

- `/start` — welcome message + inline keyboard
- `/status` — estado atual do robô (status, bateria, modo, stats) + inline keyboard
- Texto livre — processado pelo agente (LangChain ou fallback regex)
- Mensagem de voz — transcrita via OpenAI Whisper e processada como texto
- Botões inline — atalhos para `start_cleaning`, `stop_cleaning`, `return_to_base`, `locate_robot`

`get_device_state()` retorna: `status`, `batteryLevel`, `mode`, `totalCleanArea`, `totalCleanTime`, `cleanCount`.
