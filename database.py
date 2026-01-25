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


def save_offers(new_offers):
    data = _read()
    data["offers"] = new_offers
    _write(data)


def load_offers():
    return _read().get("offers", [])


def get_users():
    return _read().get("users", [])


def _read():
    _setup()
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": [], "offers": []}


def _write(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)
