import json
import os
import logging
from datetime import datetime

logger = logging.getLogger("Database")

DB_PATH = "data"
DB_FILE_USERS = os.path.join(DB_PATH, "database.json")
DB_OFFERS_CACHE = os.path.join(DB_PATH, "offers_cache.json")


def _setup():
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    if not os.path.exists(DB_FILE_USERS):
        with open(DB_FILE_USERS, "w") as f:
            json.dump({"users": [], "offers": []}, f)


def add_user(user_id):
    data = _read()
    if user_id not in data["users"]:
        data["users"].append(user_id)
        _write(data)


def remove_user(user_id):
    data = _read()
    if user_id in data["users"]:
        data["users"].remove(user_id)
        _write(data)


def _is_current_or_future_offer(offer):
    """Check if an offer is from today or a future date."""
    try:
        offer_date_str = offer.get("date", "")
        offer_date = datetime.strptime(offer_date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        is_valid = offer_date >= today
        logger.debug(
            f"Checking offer {offer_date_str}: {offer_date} >= {today} = {is_valid}"
        )
        return is_valid
    except (ValueError, TypeError) as e:
        # If date parsing fails, keep the offer to be safe
        logger.warning(f"Failed to parse date '{offer.get('date', '')}': {e}")
        return True


def save_offers(offers, date_range):
    # Filter to keep only current and future offers
    current_offers = [offer for offer in offers if _is_current_or_future_offer(offer)]

    # Generate IDs for current offers
    current_offer_ids = set(
        f"{offer.get('discipline', '')}_{offer.get('date', '')}_{offer.get('time', '')}"
        for offer in current_offers
    )

    # Preserve only notified IDs that correspond to current/future offers
    old_notified = []
    if os.path.exists(DB_OFFERS_CACHE):
        try:
            with open(DB_OFFERS_CACHE, "r") as f:
                existing = json.load(f)
                old_notified = existing.get("notified_offers", [])
        except Exception as e:
            logger.warning(f"Failed to read {DB_OFFERS_CACHE}: {e}")

    # Keep only notified IDs that are still in current offers
    cleaned_notified = [nid for nid in old_notified if nid in current_offer_ids]

    data = {
        "offers": current_offers,
        "date_range": date_range,
        "notified_offers": cleaned_notified,
    }

    with open(DB_OFFERS_CACHE, "w") as f:
        json.dump(data, f)


def load_cached_offers():
    """Load cached offers, filtering to keep only current and future ones."""
    if not os.path.exists(DB_OFFERS_CACHE):
        logger.debug(f"No {DB_OFFERS_CACHE} found")
        return [], "unknown", []
    with open(DB_OFFERS_CACHE, "r") as f:
        data = json.load(f)
        all_offers = data.get("offers", [])
        logger.debug(f"Loaded {len(all_offers)} offers from cache, filtering...")
        # Filter again on load to ensure we only return current/future offers
        current_offers = [
            offer for offer in all_offers if _is_current_or_future_offer(offer)
        ]
        logger.debug(f"After filtering: {len(current_offers)} current/future offers")
        return (
            current_offers,
            data.get("date_range", "unknown"),
            data.get("notified_offers", []),
        )


def get_users():
    return _read().get("users", [])


def _read():
    _setup()
    try:
        with open(DB_FILE_USERS, "r") as f:
            return json.load(f)
    except:
        return {"users": [], "offers": []}


def _write(data):
    _setup()
    with open(DB_FILE_USERS, "w") as f:
        json.dump(data, f)


def mark_offers_as_notified(offer_ids):
    """Mark offers as already notified to avoid duplicate alerts."""
    if not os.path.exists(DB_OFFERS_CACHE):
        return
    try:
        with open(DB_OFFERS_CACHE, "r") as f:
            data = json.load(f)
        # Add new offer IDs to the notified list (avoid duplicates)
        existing_notified = set(data.get("notified_offers", []))
        existing_notified.update(offer_ids)
        data["notified_offers"] = list(existing_notified)
        with open(DB_OFFERS_CACHE, "w") as f:
            json.dump(data, f)
    except:
        pass
