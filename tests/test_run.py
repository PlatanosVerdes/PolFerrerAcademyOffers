import sys
from pathlib import Path

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import scraper
import database
import time

# Basic logging configuration to see what happens
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TestRun")


# Copy the helper function from main.py
def generate_offer_id(offer):
    """Generate a unique ID for an offer based on its details."""
    return (
        f"{offer.get('discipline', '')}_{offer.get('date', '')}_{offer.get('time', '')}"
    )


def run_simulation():
    print("🚀 Starting simulation (DRY RUN)...")

    # 1. Run the Scraper
    logger.info("Scraping offers...")
    try:
        # Note: Make sure scraper.get_new_offers() is not async.
        # If you used the requests version I provided earlier, it's synchronous.
        all_items, date_range = scraper.get_new_offers()
    except Exception as e:
        logger.error(f"Scraper error: {e}")
        return

    # 2. Filter only real offers
    offers = [item for item in all_items if item.get("is_offer", False)]
    print(f"📊 Total items found: {len(all_items)}")
    print(f"🔥 Real offers found: {len(offers)}")

    # 3. Load what we already have in database
    _, _, notified_offer_ids = database.load_cached_offers()
    print(f"💾 Offers already notified previously in DB: {len(notified_offer_ids)}")

    # 4. New offers detection logic
    new_offers = []
    new_offer_ids = []

    for offer in offers:
        offer_id = generate_offer_id(offer)

        # Simulate the check
        if offer_id not in notified_offer_ids:
            new_offers.append(offer)
            new_offer_ids.append(offer_id)
            print(f"   -> [NEW] {offer['date']} - {offer['discipline']}")
        else:
            print(f"   -> [ALREADY SEEN] {offer['date']} - {offer['discipline']}")

    # 5. Simulate saving and notification
    if new_offers:
        print(f"\n🔔 {len(new_offers)} notifications would be sent!")

        # Simulate text formatting
        text = scraper.format_offer_message(new_offers)
        print("-" * 20)
        print("Message body that the user would receive:")
        print(text)
        print("-" * 20)

        # This is where the bot would send the message.
        # In the test, we only save to DB if we want to update the state.
        # If you want to test it many times, COMMENT the following line so they don't get saved
        # and always appear as "New".

        # database.save_offers(offers, date_range)
        # database.mark_offers_as_notified(new_offer_ids)
        # print("✅ Database updated (Simulation).")

    else:
        print("\n😴 No new offers to notify.")


if __name__ == "__main__":
    run_simulation()
