import html
import logging
import os
from datetime import datetime, timezone

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
API_URL = "https://v3.football.api-sports.io/fixtures"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not API_FOOTBALL_KEY:
    raise RuntimeError("API_FOOTBALL_KEY is not set")


def get_live_matches():
    response = requests.get(
        API_URL,
        headers={"x-apisports-key": API_FOOTBALL_KEY},
        params={"live": "all"},
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()
    if data.get("errors"):
        raise RuntimeError(f"API-Football error: {data['errors']}")

    return data.get("response", [])


def match_status(status):
    short = status.get("short", "LIVE")
    elapsed = status.get("elapsed")

    if short in {"HT", "INT"}:
        return "HT"
    if short in {"ET", "BT"} and elapsed is not None:
        return f"{elapsed}'"
    if elapsed is not None and short not in {"P", "SUSP", "INT", "ABD", "CANC", "PST"}:
        return f"{elapsed}'"
    return short


def format_match(match):
    fixture = match.get("fixture", {})
    teams = match.get("teams", {})
    goals = match.get("goals", {})
    league = match.get("league", {})

    home = html.escape(teams.get("home", {}).get("name") or "Home")
    away = html.escape(teams.get("away", {}).get("name") or "Away")
    league_name = html.escape(league.get("name") or "")
    country = html.escape(league.get("country") or "")

    home_score = goals.get("home")
    away_score = goals.get("away")
    home_score = 0 if home_score is None else home_score
    away_score = 0 if away_score is None else away_score

    status = match_status(fixture.get("status", {}))
    competition = league_name
    if country and league_name:
        competition = f"{league_name} • {country}"

    lines = [f"⚽ <b>{home}  {home_score} - {away_score}  {away}</b>"]
    if competition:
        lines.append(competition)
    lines.append(f"<b>{html.escape(status)}</b>")
    return "\n".join(lines)


def format_matches(matches):
    if not matches:
        return (
            "⚽ <b>LIVE MATCHES</b>\n\n"
            "No live matches right now.\n"
            "Check again later for new games."
        )

    # Keep the display compact and ordered by competition, then kickoff time.
    matches = sorted(
        matches,
        key=lambda m: (
            (m.get("league", {}).get("name") or "").lower(),
            m.get("fixture", {}).get("date") or "",
        ),
    )

    blocks = ["⚽ <b>LIVE MATCHES</b>", ""]
    blocks.extend(format_match(match) for match in matches)
    return "\n\n".join(blocks)


def keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔄 Refresh scores", callback_data="live")]]
    )


def updated_text(text):
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    return f"{text}\n\n<i>Updated {now}</i>"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "<b>Match Bot</b>\n\n"
        "Check live football matches and current scorelines directly in Telegram.\n\n"
        "Tap below to see what's happening now."
    )
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard(),
    )


async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        matches = get_live_matches()
        text = updated_text(format_matches(matches))
    except requests.RequestException:
        logger.exception("Football API request failed")
        text = (
            "⚠️ <b>Live scores are temporarily unavailable.</b>\n\n"
            "Please try again shortly."
        )
    except Exception:
        logger.exception("Unexpected error while loading matches")
        text = (
            "⚠️ <b>We couldn't load the live matches right now.</b>\n\n"
            "Please try again shortly."
        )

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard(),
            )
        except Exception:
            await query.message.reply_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard(),
            )
        return

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard(),
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Telegram update error", exc_info=context.error)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CallbackQueryHandler(live, pattern=r"^live$"))
    app.add_error_handler(error_handler)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
