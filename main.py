import asyncio
import logging
import os
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

REFRESH_INTERVAL_MINUTES = 10

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Main")

load_dotenv()  # TODO: Remove if not used
TOKEN = os.getenv("BOT_TOKEN")


@aiocron.crontab(f"*/{REFRESH_INTERVAL_MINUTES} * * * *")
async def scheduled_scan():
    logger.info("Cron: Starting scheduled scan for new offers...")
    offers = scraper.get_new_offers()

    if offers:
        database.save_offers(offers)
        users = database.get_users()
        text = scraper.format_offer_message(offers)

        for user_id in users:
            try:
                await app.bot.send_message(
                    chat_id=user_id, text=text, parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Error al enviar a {user_id}: {e}")
    else:
        logger.info("Cron: No new offers found.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    database.add_user(user_id)
    await update.message.reply_text(
        f"✅ <b>¡Suscrito correctamente!</b> Te avisaré cuando detecte ofertas de wheelie cada {REFRESH_INTERVAL_MINUTES} min.",
        parse_mode="HTML",
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    database.remove_user(user_id)
    await update.message.reply_text(
        "🔕 <b>Suscripción cancelada.</b> Ya no recibirás más alertas.",
        parse_mode="HTML",
    )


async def offers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_offers = database.load_offers()
    text = scraper.format_offer_message(current_offers)
    await update.message.reply_text(text, parse_mode="HTML")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 <b>Ayuda de Wheelie Hunter</b>\n\n"
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
