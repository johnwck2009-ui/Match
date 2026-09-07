import os
import html
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
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
        timeout=15,
    )
    response.raise_for_status()
    return response.json().get("response", [])


def format_matches(matches):
    if not matches:
        return "⚽ <b>No live matches right now.</b>\n\nCheck again later for live scores."

    lines = ["⚽ <b>LIVE MATCHES</b>", ""]
    for match in matches:
        fixture = match.get("fixture", {})
        teams = match.get("teams", {})
        goals = match.get("goals", {})
        league = match.get("league", {})
        status = fixture.get("status", {})

        home = html.escape(teams.get("home", {}).get("name", "Home"))
        away = html.escape(teams.get("away", {}).get("name", "Away"))
        home_score = goals.get("home")
        away_score = goals.get("away")
        home_score = 0 if home_score is None else home_score
        away_score = 0 if away_score is None else away_score
        elapsed = status.get("elapsed")
        status_text = f"{elapsed}'" if elapsed is not None else status.get("short", "LIVE")
        league_name = html.escape(league.get("name", ""))

        lines.append(f"<b>{home}  {home_score} - {away_score}  {away}</b>")
        if league_name:
            lines.append(f"{league_name} • {status_text}")
        else:
            lines.append(status_text)
        lines.append("")

    return "\n".join(lines).strip()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("⚽ Live Matches", callback_data="live")]]
    await update.message.reply_text(
        "<b>Match Bot</b>\n\nCheck live football matches and current scorelines in one place.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        matches = get_live_matches()
        text = format_matches(matches)
    except requests.RequestException as exc:
        logger.exception("Football API request failed: %s", exc)
        text = "⚠️ <b>Unable to load live matches right now.</b>\n\nPlease try again shortly."
    except Exception:
        logger.exception("Unexpected error while loading matches")
        text = "⚠️ <b>Something went wrong.</b>\n\nPlease try again shortly."

    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="live")]]
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception:
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Telegram update error", exc_info=context.error)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CallbackQueryHandler(live, pattern="^live$"))
    app.add_error_handler(error_handler)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
