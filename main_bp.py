import requests
from bs4 import BeautifulSoup
import logging
import time
import json
import os

# --- ⚙️ CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")

CHECK_INTERVAL_MINUTES = 60  # Escanear la web cada 60 min
URL_OBJETIVO = "https://www.polferrer.com"
DB_FILE = "subscribers.json"  # Archivo donde guardaremos a la gente

# --- GLOBAL SETTINGS (CSS COLORS) ---
COLOR_WHEELIE = "border-lime-600"
COLOR_DRIFT = "border-red-600"
COLOR_OFFROAD = "border-amber-500"
COLOR_STOPPIE = "border-blue-600"
COLOR_ASPHALT = "border-zinc-600"

DISCIPLINE_MAP = {
    COLOR_WHEELIE: "Wheelie 🟢",
    COLOR_DRIFT: "Drift 🔴",
    COLOR_OFFROAD: "Off-road 🟠",
    COLOR_STOPPIE: "Stoppie 🔵",
    COLOR_ASPHALT: "Asphalt/General ⚪",
}

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# --- GESTIÓN DE SUSCRIPTORES ---
def load_subscribers():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_subscriber(chat_id):
    subs = load_subscribers()
    if chat_id not in subs:
        subs.append(chat_id)
        with open(DB_FILE, "w") as f:
            json.dump(subs, f)
        logger.info(f"✅ Nuevo suscriptor guardado: {chat_id}")
        return True
    return False


def remove_subscriber(chat_id):
    subs = load_subscribers()
    if chat_id in subs:
        subs.remove(chat_id)
        with open(DB_FILE, "w") as f:
            json.dump(subs, f)
        logger.info(f"🗑️ Suscriptor eliminado: {chat_id}")


# --- TELEGRAM API ---
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=payload)
        # Si el usuario bloqueó el bot (403), lo borramos de la lista
        if r.status_code == 403:
            logger.warning(f"Usuario {chat_id} bloqueó el bot. Eliminando.")
            remove_subscriber(chat_id)
    except Exception as e:
        logger.error(f"Error enviando mensaje a {chat_id}: {e}")


def broadcast_message(message):
    subs = load_subscribers()
    if not subs:
        logger.info("No hay suscriptores a los que avisar.")
        return

    logger.info(f"📢 Enviando alerta a {len(subs)} usuarios...")
    for chat_id in subs:
        send_message(chat_id, message)


def check_new_users(last_update_id):
    """Revisa si alguien nuevo ha hablado al bot"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 5}

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if "result" in data:
            for update in data["result"]:
                last_update_id = update["update_id"]

                # Ver si es un mensaje de texto
                if "message" in update and "text" in update["message"]:
                    chat_id = update["message"]["chat"]["id"]
                    text = update["message"]["text"]

                    if text == "/start":
                        is_new = save_subscriber(chat_id)
                        if is_new:
                            send_message(
                                chat_id,
                                "👋 <b>¡Bienvenido al WheelieHunter!</b>\nTe avisaré automáticamente cuando detecte ofertas.",
                            )
                        else:
                            send_message(
                                chat_id, "Ya estás suscrito. ¡A esperar ofertas!"
                            )

                    elif text == "/stop":
                        remove_subscriber(chat_id)
                        send_message(
                            chat_id, "🔕 Te has dado de baja. No recibirás más alertas."
                        )

        return last_update_id
    except Exception as e:
        logger.error(f"Error comprobando actualizaciones: {e}")
        return last_update_id


def extract_calendar_matrix(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    found_items = []

    # 1. Find all Grid Rows (Tailwind class 'grid-cols-8')
    grid_rows = soup.find_all("div", class_="grid-cols-8")

    if not grid_rows:
        logger.error(
            "No 'grid-cols-8' rows found. The HTML might not be fully rendered or class names changed."
        )
        return []

    logger.debug(f"Structure check: Found {len(grid_rows)} rows in the calendar grid.")

    # Dictionary to map Column Index (1-7) -> Date String
    col_date_map = {}

    # --- PROCESS ROWS ---
    for row_index, row in enumerate(grid_rows):

        # Get immediate children (The 8 cells of the row)
        # Using recursive=False is CRITICAL to stay on the grid level
        # We find ALL tags (divs for structure, buttons for slots)
        cells = row.find_all(True, recursive=False)

        # Safety check: A valid grid row should have roughly 8 columns
        if len(cells) < 8:
            continue

        # --- ROW 0: HEADERS (Dates) ---
        if row_index == 0:
            for col_idx, cell in enumerate(cells):
                if col_idx == 0:
                    continue  # Skip the top-left empty corner

                # Extract clean date. The HTML usually puts the clean date (e.g. "19 ene")
                # inside a div with 'text-gray-500'. We try to find that first.
                date_div = cell.find("div", class_="text-gray-500")

                if date_div:
                    date_text = date_div.get_text(strip=True)
                else:
                    # Fallback: get all text joined by space
                    date_text = cell.get_text(" ", strip=True)

                col_date_map[col_idx] = date_text

            # --- NEW: PRINT THE DETECTED WEEK ---
            start_date = col_date_map.get(1, "?")
            end_date = col_date_map.get(7, "?")
            logger.info(
                f"📅 CURRENT WEEK DETECTED: From [{start_date}] to [{end_date}]"
            )
            continue

        # --- ROW > 0: TIME SLOTS ---

        # 1. Get Time Label (Column 0)
        # e.g., joins "10", ":00", "-", "12", ":00" -> "10:00-12:00"
        time_text = cells[0].get_text("", strip=True)

        # 2. Check Columns 1-7 (Days of the week)
        for col_idx in range(1, 8):
            # Safety break if row is shorter than expected
            if col_idx >= len(cells):
                break

            element = cells[col_idx]

            # Identify if there is a button (Active Slot)
            # The button might be the element itself OR nested inside
            button = None
            if element.name == "button":
                button = element
            else:
                button = element.find("button")

            if button:
                classes = button.get("class", [])

                # A. Identify Discipline
                discipline = "Unknown"
                for css, name in DISCIPLINE_MAP.items():
                    if css in classes:
                        discipline = name
                        break

                # B. Get Text info
                text_content = button.get_text(" ", strip=True)

                # C. Check if it is an OFFER
                is_offer = "Oferta" in text_content or "Offer" in text_content

                # D. Extract Price
                price_span = button.find("span")
                price = price_span.get_text(strip=True) if price_span else "N/A"

                if discipline != "Unknown":
                    # Log finding an offer immediately for debugging
                    if is_offer:
                        logger.info(
                            f"⚡ OFFER FOUND! {discipline} on {col_date_map.get(col_idx)} at {time_text}"
                        )

                    found_items.append(
                        {
                            "is_offer": is_offer,
                            "discipline": discipline,
                            "date": col_date_map.get(col_idx, "Unknown Date"),
                            "time": time_text,
                            "price": price,
                            "raw_text": text_content,
                        }
                    )

    return found_items


def scan_web():
    logger.info(f"🔎 Escaneando web...")
    headers = {"User-Agent": "Mozilla/5.0..."}  # Usa el user agent completo de antes
    try:
        response = requests.get(URL_OBJETIVO, headers=headers)
        if response.status_code == 200:
            items = extract_calendar_matrix(response.text)
            offers = [i for i in items if i["is_offer"]]

            logger.info(f"Escaneo fin. Total: {len(items)}. Ofertas: {len(offers)}")

            if offers:
                msg = ["🚨 <b>¡NUEVAS OFERTAS!</b> 🚨", ""]
                for o in offers:
                    msg.append(
                        f"📅 {o['date']} - {o['time']}\n🏍️ {o['discipline']} - 💰 {o['price']}\n"
                    )
                msg.append(f"🔗 <a href='{URL_OBJETIVO}'>Reservar</a>")

                broadcast_message("\n".join(msg))
            else:
                logger.info("Nada nuevo.")
    except Exception as e:
        logger.error(f"Error en escaneo: {e}")


# --- BUCLE PRINCIPAL ---
if __name__ == "__main__":
    if TELEGRAM_TOKEN == "TU_TOKEN_AQUI":
        print("❌ ERROR: Configura el TELEGRAM_TOKEN")
        exit()

    logger.info("🤖 Bot Público Iniciado. Esperando suscriptores...")

    last_update_id = 0
    last_scan_time = 0

    # Bucle infinito inteligente
    try:
        while True:
            # 1. Atender a usuarios de Telegram (Rápido, cada 2 segundos)
            last_update_id = check_new_users(last_update_id)

            # 2. Comprobar si toca escanear la web (Lento, cada 60 minutos)
            current_time = time.time()
            if current_time - last_scan_time > (CHECK_INTERVAL_MINUTES * 60):
                scan_web()
                last_scan_time = current_time

            # Pequeña pausa para no saturar la CPU
            time.sleep(2)

    except KeyboardInterrupt:
        logger.info("Bot detenido.")
