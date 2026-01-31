import asyncio
import logging
import os
from pydoc import text
import aiocron
from dotenv import load_dotenv

# Importaciones de la BASE de la librería
from telegram import BotCommand, Update

# Importaciones de las EXTENSIONES
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

import scraper
import database

REFRESH_INTERVAL_MINUTES = 1

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Main")

# load_dotenv()  # TODO: Remove if not used
TOKEN = os.getenv("BOT_TOKEN")


@aiocron.crontab(f"*/{REFRESH_INTERVAL_MINUTES} * * * *")
async def scheduled_scan():
    logger.info("Cron: Scanning for new offers...")
    offers, date_range = scraper.get_new_offers()

    # Guardamos siempre lo último detectado en la caché
    database.save_offers(offers, date_range)

    if offers:
        users = database.load_subscribers()  # Usamos tu función de subscribers.json
        text = scraper.format_offer_message(offers, date_range)
        for user_id in users:
            await send_async_message(user_id, text)  # O usar app.bot.send_message
    else:
        logger.info("Cron: No new offers found.")


async def offers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_chat.id} requested offers from database.")

    # LEER DE LA BASE DE DATOS, NO DEL SCRAPER
    current_offers, date_range = database.load_cached_offers()

    text = scraper.format_offer_message(current_offers, date_range)
    await update.message.reply_text(text, parse_mode="HTML")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    database.add_user(user_id)
    await update.message.reply_text(
        f"✅ <b>¡Suscrito correctamente!</b> Te avisaré cuando detecte nuevas ofertas.",
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
        "Este bot escanea la academia de Pol Ferrer cada 10 minutos buscando ofertas.\n\n"
        "<b>Comandos disponibles:</b>\n"
        "• /start - Suscribirse a las alertas automáticas.\n"
        "• /offers - Ver las ofertas activas actualmente.\n"
        "• /stop - Dejar de recibir notificaciones.\n"
        "• /help - Mostrar este mensaje de ayuda."
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


async def post_init(application):
    """Configura el menú de comandos automáticamente al arrancar."""
    commands = [
        BotCommand("start", "Suscribirse a las alertas"),
        BotCommand("offers", "Ver ofertas actuales"),
        BotCommand("stop", "Cancelar suscripción"),
        BotCommand("help", "Información del bot"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Commands set successfully.")


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("offers", offers_cmd))
    app.add_handler(CommandHandler("help", help_cmd))

    logger.info("\Starting Offers Hunter Bot...")
    app.run_polling()
