import json
import os

DB_FILE = "data/database.json"


def _setup():
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
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


def save_offers(offers, date_range):
    data = {"offers": offers, "date_range": date_range, "notified_offers": []}
    # Preserve existing notified offers
    if os.path.exists("offers_cache.json"):
        try:
            with open("offers_cache.json", "r") as f:
                existing = json.load(f)
                data["notified_offers"] = existing.get("notified_offers", [])
        except:
            pass
    with open("offers_cache.json", "w") as f:
        json.dump(data, f)


def load_cached_offers():
    if not os.path.exists("offers_cache.json"):
        return [], "unknown", []
    with open("offers_cache.json", "r") as f:
        data = json.load(f)
        return (
            data.get("offers", []),
            data.get("date_range", "unknown"),
            data.get("notified_offers", []),
        )


def get_users():
    return _read().get("users", [])


def _read():
    _setup()
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": [], "offers": []}


def mark_offers_as_notified(offer_ids):
    """Mark offers as already notified to avoid duplicate alerts."""
    if not os.path.exists("offers_cache.json"):
        return
    try:
        with open("offers_cache.json", "r") as f:
            data = json.load(f)
        # Add new offer IDs to the notified list (avoid duplicates)
        existing_notified = set(data.get("notified_offers", []))
        existing_notified.update(offer_ids)
        data["notified_offers"] = list(existing_notified)
        with open("offers_cache.json", "w") as f:
            json.dump(data, f)
    except:
        pass
