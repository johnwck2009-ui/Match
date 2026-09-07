# Match Bot

A simple Telegram utility bot for checking live football matches and current scorelines.

## Features

- Live football matches from supported competitions
- Current scorelines
- Match minute/status
- League/competition name
- Refresh button for updated scores

## Setup

Set these environment variables:

- `BOT_TOKEN` — Telegram bot token from BotFather
- `API_FOOTBALL_KEY` — API-Football API key

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
python bot.py
```

The bot uses API-Football's live fixtures endpoint (`live=all`). Keep API credentials in environment variables and never commit them to the repository.
