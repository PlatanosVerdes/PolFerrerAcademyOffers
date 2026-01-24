import time
import logging
import os

# Custom modules
import scraper
import telegram_bot

# Global Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Main")

CHECK_INTERVAL_MINUTES = 60

if __name__ == "__main__":
    if not os.getenv("BOT_TOKEN"):
        logger.error("❌ ERROR: BOT_TOKEN environment variable is missing.")
        exit()

    logger.info("🤖 Modular Bot Started (Docker).")

    last_update_id = 0
    last_scan_time = 0

    try:
        while True:
            # 1. Handle Telegram Updates (Fast check)
            last_update_id = telegram_bot.check_updates(last_update_id)

            # 2. Handle Web Scraping (Slow check, every X minutes)
            current_time = time.time()
            if current_time - last_scan_time > (CHECK_INTERVAL_MINUTES * 60):

                # Ask scraper to look for offers
                offers = scraper.get_new_offers()

                if offers:
                    logger.info(f"Found {len(offers)} offers.")
                    # Format the message
                    message_text = scraper.format_offer_message(offers)
                    # Broadcast to Telegram
                    telegram_bot.broadcast_message(message_text)
                else:
                    logger.info("Scan complete. No new offers found.")

                last_scan_time = current_time

            # Short sleep to prevent CPU saturation
            time.sleep(2)

    except KeyboardInterrupt:
        logger.info("Bot stopped manually.")
