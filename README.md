# Match Bot

A simple Telegram utility bot for checking live football matches and current scorelines.

## Features

- Live football matches
- Current scorelines
- Match minute/status when available
- League/competition name when available
- Refresh button for updated scores

## Setup

Set this environment variable:

- `BOT_TOKEN` — Telegram bot token from BotFather

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
python bot.py
```

The bot uses SportScore's public football endpoint for live match data. No sports API key is required.
