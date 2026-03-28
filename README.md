# Tuya Agentic Vacuum

Control your Tuya-compatible robot vacuum with natural language via Telegram. Send text or voice messages and an AI agent translates them into device commands.

## How it works

```
Telegram message (text or voice)
        ↓
   AI Agent (GPT-4o-mini or regex fallback)
        ↓
   Tuya Open Platform API
        ↓
   Robot vacuum
```

## Prerequisites

- Python 3.11+
- A Tuya-compatible robot vacuum
- A [Tuya IoT Platform](https://iot.tuya.com) developer account
- A Telegram bot token (via [@BotFather](https://t.me/botfather))
- An OpenAI API key (optional — enables GPT-4o-mini and voice commands)

## 1. Tuya IoT Platform setup

1. Sign in at the Tuya IoT Platform and create a **Cloud Development** project
2. Under **Overview**, copy your **Access ID** and **Access Secret**
3. Go to **Devices → Link Tuya App Account** and link your Smart Life / Tuya Smart account — this makes your devices visible to the project
4. Set the API endpoint based on your region:
   - Americas: `https://openapi.tuyaus.com`
   - Europe: `https://openapi.tuyaeu.com`
   - China: `https://openapi.tuyacn.com`
   - India: `https://openapi.tuyain.com`

## 2. Telegram bot setup

1. Open Telegram and start a conversation with [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the prompts
3. Copy the token BotFather gives you

## 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=sk-...          # optional, enables GPT and voice
TUYA_ACCESS_ID=...
TUYA_ACCESS_SECRET=...
TUYA_API_ENDPOINT=https://openapi.tuyaus.com
TELEGRAM_BOT_TOKEN=...
```

> `TUYA_DEVICE_ID` is not required — use `/devices` in the bot to discover and select your robot.

## 4. Install and run

```bash
pip install -r requirements.txt
python3 bot.py
```

## 5. First use

1. Open your bot on Telegram and send `/start`
2. Send `/devices` to list the robots linked to your Tuya account and select one
3. Start sending commands in natural language:
   - *"Start cleaning"* / *"Começa a limpar"*
   - *"Return to base"* / *"Volta para a base"*
   - *"Clean in spiral mode"* / *"Modo espiral"*
   - Or send a **voice message** (requires OpenAI API key)

## Bot commands

| Command | Description |
|---|---|
| `/start` | Welcome message and quick action buttons |
| `/status` | Current robot status, battery, mode and cleaning stats |
| `/devices` | List and select which Tuya device to control |

## Supported cleaning modes

`smart` · `random` · `spiral` · `wall_follow` · `mop` · `left_bow` · `right_bow`

## Without an OpenAI key

The bot still works using a regex-based intent fallback. Voice messages require the OpenAI key (Whisper transcription).
