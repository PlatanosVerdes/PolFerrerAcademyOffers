import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
DB_FILE = "subscribers.json"


def load_subscribers():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_subscriber(chat_id):
    subs = load_subscribers()
    if chat_id not in subs:
        subs.append(chat_id)
        with open(DB_FILE, "w") as f:
            json.dump(subs, f)
        logger.info(f"✅ New subscriber saved: {chat_id}")
        return True
    return False


def remove_subscriber(chat_id):
    subs = load_subscribers()
    if chat_id in subs:
        subs.remove(chat_id)
        with open(DB_FILE, "w") as f:
            json.dump(subs, f)
        logger.info(f"🗑️ Subscriber removed: {chat_id}")


def send_message(chat_id, text):
    if not TELEGRAM_TOKEN:
        logger.error("Missing TELEGRAM_TOKEN")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=payload, timeout=10)
        # If user blocked the bot (403), remove them from database
        if r.status_code == 403:
            logger.warning(f"User {chat_id} blocked the bot. Removing.")
            remove_subscriber(chat_id)
    except Exception as e:
        logger.error(f"Error sending message to {chat_id}: {e}")


def broadcast_message(text_message):
    subs = load_subscribers()
    if not subs:
        logger.info("No subscribers to notify.")
        return

    logger.info(f"📢 Broadcasting alert to {len(subs)} users...")
    for chat_id in subs:
        send_message(chat_id, text_message)


def check_updates(last_update_id):
    """Checks for new messages from users (subscribers)."""
    if not TELEGRAM_TOKEN:
        return last_update_id

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 5}

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "result" in data:
            for update in data["result"]:
                last_update_id = update["update_id"]

                if "message" in update and "text" in update["message"]:
                    chat_id = update["message"]["chat"]["id"]
                    text = update["message"]["text"]

                    if text == "/start":
                        is_new = save_subscriber(chat_id)
                        if is_new:
                            send_message(
                                chat_id,
                                "👋 <b>Welcome to WheelieHunter!</b>\nI will notify you automatically when new offers are detected.",
                            )
                        else:
                            send_message(
                                chat_id,
                                "You are already subscribed. Waiting for offers...",
                            )

                    elif text == "/stop":
                        remove_subscriber(chat_id)
                        send_message(
                            chat_id,
                            "🔕 You have unsubscribed. You will not receive further alerts.",
                        )

        return last_update_id
    except Exception as e:
        logger.error(f"Error checking Telegram updates: {e}")
        return last_update_id
