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
SPORTSCORE_URL = "https://sportscore.com/api/widget/matches/"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")


def get_live_matches():
    """Fetch current football matches from SportScore's public API."""
    response = requests.get(
        SPORTSCORE_URL,
        params={"sport": "football", "limit": 50},
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()
    if isinstance(data, dict):
        matches = data.get("matches") or data.get("data") or data.get("results") or []
    else:
        matches = data

    if not isinstance(matches, list):
        raise RuntimeError("Unexpected SportScore response format")

    live_matches = []
    for match in matches:
        status = str(
            match.get("status")
            or match.get("state")
            or match.get("matchStatus")
            or ""
        ).lower()

        if any(word in status for word in ("live", "inplay", "in-play", "playing", "halftime")):
            live_matches.append(match)

    return live_matches


def value(obj, *keys, default=None):
    if not isinstance(obj, dict):
        return default
    for key in keys:
        if obj.get(key) is not None:
            return obj[key]
    return default


def team_name(match, side):
    teams = match.get("teams") or {}
    team = teams.get(side) or match.get(f"{side}Team") or {}
    if isinstance(team, str):
        return team
    return value(team, "name", "title", default=side.title())


def score_value(match, side):
    score = match.get("score") or match.get("scores") or {}
    value_from_score = value(score, side, f"{side}Score", default=None)
    if isinstance(value_from_score, dict):
        value_from_score = value(value_from_score, "current", "value", "goals", default=None)
    if value_from_score is None:
        value_from_score = value(match, f"{side}Score", default=0)
    return 0 if value_from_score is None else value_from_score


def league_name(match):
    league = match.get("league") or match.get("competition") or {}
    if isinstance(league, str):
        return league
    return value(league, "name", "title", default="")


def match_status(match):
    status = value(match, "status", "state", "matchStatus", default="LIVE")
    if isinstance(status, dict):
        status = value(status, "name", "short", "type", default="LIVE")
    status = str(status).replace("_", " ").title()

    minute = value(match, "minute", "elapsed", "matchMinute", default=None)
    if minute is not None and str(minute).isdigit():
        return f"{minute}'"
    return status


def format_match(match):
    home = html.escape(str(team_name(match, "home")))
    away = html.escape(str(team_name(match, "away")))
    competition = html.escape(str(league_name(match)))
    home_score = score_value(match, "home")
    away_score = score_value(match, "away")
    status = html.escape(match_status(match))

    lines = [f"⚽ <b>{home}  {home_score} - {away_score}  {away}</b>"]
    if competition:
        lines.append(competition)
    lines.append(f"<b>{status}</b>")
    return "\n".join(lines)


def format_matches(matches):
    if not matches:
        return "⚽ <b>LIVE MATCHES</b>\n\nNo live matches right now."

    blocks = ["⚽ <b>LIVE MATCHES</b>", ""]
    blocks.extend(format_match(match) for match in matches)
    return "\n\n".join(blocks)


def keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔄 Refresh", callback_data="live")]]
    )


def add_update_time(text):
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    return f"{text}\n\n<i>Updated {now}</i>"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "<b>Match Bot</b>\n\n"
        "See live football matches and current scorelines directly in Telegram.\n\n"
        "Tap the button below to check the latest matches."
    )
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard(),
    )


async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        matches = get_live_matches()
        text = add_update_time(format_matches(matches))
    except requests.RequestException:
        logger.exception("SportScore request failed")
        text = (
            "⚠️ <b>Live scores are temporarily unavailable.</b>\n\n"
            "Please try again shortly."
        )
    except Exception:
        logger.exception("Unexpected error while loading live matches")
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
