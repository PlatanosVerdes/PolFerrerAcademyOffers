import asyncio
import logging
import os
import random
from dotenv import load_dotenv

# Importaciones de la BASE de la librería
from telegram import BotCommand, Update
from telegram.error import Forbidden

# Importaciones de las EXTENSIONES
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

import scraper
import database

load_dotenv()

# Scan on a random interval within this range to spread load and stay less predictable.
REFRESH_MIN_MINUTES = 5
REFRESH_MAX_MINUTES = 15
VERSION_RELEASE = "1.4.0"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Main")

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logger.error("Error: BOT_TOKEN not found in environment variables.")
    exit(1)

# Global application instance
app = None


async def scheduled_scan():
    logger.info("Scanning for new offers...")
    all_items, date_range = scraper.get_new_offers()

    # Filter only offers (is_offer == True)
    offers = [item for item in all_items if item.get("is_offer", False)]

    # Load previously notified offers
    _, _, notified_offer_ids = database.load_cached_offers()

    # Find new offers that haven't been notified yet
    new_offers = []
    new_offer_ids = []
    for offer in offers:
        oid = database.offer_id(offer)
        if oid not in notified_offer_ids:
            new_offers.append(offer)
            new_offer_ids.append(oid)

    # Save all offers (for the /offers command)
    database.save_offers(offers, date_range)

    # Send notifications only for NEW offers
    if new_offers:
        logger.info(f"Found {len(new_offers)} new offers to notify")
        users = database.get_users()
        text = scraper.format_offer_message(new_offers)
        
        for user_id in users:
            try:
                await app.bot.send_message(
                    chat_id=user_id, text=text, parse_mode="HTML"
                )
            except Forbidden:
                logger.info(f"User {user_id} blocked the bot; removing.")
                database.remove_user(user_id)
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")

        database.mark_offers_as_notified(new_offer_ids)
    else:
        logger.info("No new offers found.")


async def _scan_loop():
    """Run scheduled_scan forever, sleeping a random 5-15 min between runs."""
    while True:
        try:
            await scheduled_scan()
        except Exception as e:
            logger.error(f"Scan loop error: {e}")
        delay = random.randint(REFRESH_MIN_MINUTES, REFRESH_MAX_MINUTES) * 60
        logger.info(f"Next scan in {delay // 60} min")
        await asyncio.sleep(delay)


async def offers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    tg_user = update.effective_user
    logger.info(f"User {user_id} requested offers from database.")

    users = database.get_users()
    was_subscribed = user_id in users

    # Silently capture/refresh display info (idempotent, no user-facing change).
    database.add_user(
        user_id,
        username=tg_user.username if tg_user else None,
        first_name=tg_user.first_name if tg_user else None,
    )

    if not was_subscribed:
        logger.info(f"Usuario {user_id} auto-suscrito al usar /offers")

        await update.message.reply_text(
            "✅ <i>He notado que no estabas en la lista de alertas. Te he suscrito automáticamente. Usa /stop si no quieres recibir avisos.</i>",
            parse_mode="HTML",
        )

    current_offers, date_range, _ = database.load_cached_offers()

    logger.info(f"Loaded {len(current_offers)} current/future offers from cache")
    for offer in current_offers:
        logger.info(
            f"  - {offer.get('date')} {offer.get('time')} - {offer.get('discipline')}"
        )

    text = scraper.format_offer_message(current_offers)
    await update.message.reply_text(text, parse_mode="HTML")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    tg_user = update.effective_user
    database.add_user(
        user_id,
        username=tg_user.username if tg_user else None,
        first_name=tg_user.first_name if tg_user else None,
    )
    await update.message.reply_text(
        f"✅ <b>¡Suscrito correctamente!</b> Te avisaré cuando detecte nuevas ofertas.\n\n"
        f"<i>Bot version: {VERSION_RELEASE}</i>",
        parse_mode="HTML",
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    database.remove_user(user_id)
    await update.message.reply_text(
        "🔕 <b>Suscripción cancelada.</b> Ya no recibirás más alertas.",
        parse_mode="HTML",
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 <b>Pol Academy Offers Hunter</b>\n\n"
        f"Este bot escanea la academia de Pol Ferrer cada {REFRESH_MIN_MINUTES}-{REFRESH_MAX_MINUTES} minutos buscando ofertas.\n\n"
        "<b>Comandos disponibles:</b>\n"
        "• /start - Suscribirse a las alertas automáticas.\n"
        "• /offers - Ver las ofertas activas actualmente.\n"
        "• /stop - Dejar de recibir notificaciones.\n"
        "• /help - Mostrar este mensaje de ayuda.\n\n"
        f"<i>Version: {VERSION_RELEASE}</i>"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


async def post_init(application):
    """Configure bot commands after the application has been initialized."""
    commands = [
        BotCommand("start", "Suscribirse a las alertas"),
        BotCommand("offers", "Ver ofertas actuales"),
        BotCommand("stop", "Cancelar suscripción"),
        BotCommand("help", "Información del bot"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Commands set successfully.")

    # Log DB path + count so a broken volume mount is obvious on startup.
    db_path = os.path.abspath(database.DB_FILE_USERS)
    subscriber_count = len(database.get_users())
    logger.info(f"📂 Subscriber DB: {db_path} ({subscriber_count} subscribers loaded)")

    # Backfill display info for existing subscribers (get_chat is read-only).
    known_info = database.get_users_info()
    for uid in database.get_users():
        if str(uid) in known_info:
            continue
        try:
            chat = await application.bot.get_chat(uid)
            database.add_user(
                uid, username=chat.username, first_name=chat.first_name
            )
            logger.info(f"ℹ️ Backfilled info for {uid}: @{chat.username}")
        except Exception as e:
            logger.warning(f"Could not backfill info for {uid}: {e}")

    # Start the periodic scan loop (random 5-15 min interval).
    asyncio.create_task(_scan_loop())


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("offers", offers_cmd))
    app.add_handler(CommandHandler("help", help_cmd))

    logger.info("Starting Offers Hunter Bot...")
    app.run_polling()
