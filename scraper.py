import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

TARGET_URL = "https://www.polferrer.com"

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


def get_new_offers():
    """
    Scans the website and returns a list of offer objects.
    Returns empty list if error or no offers.
    """
    logger.info(f"🔎 Scanning target URL...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=15)
        if response.status_code == 200:
            items = extract_calendar_matrix(response.text)
            # Filter only items marked as offers
            offers = [i for i in items if i.get("is_offer")]
            return offers
        else:
            logger.error(f"Error status code: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Scan error: {e}")
        return []


def format_offer_message(offers):
    """Converts the offer list into a formatted string for Telegram."""
    if not offers:
        return None

    msg = ["🚨 <b>NEW OFFERS FOUND!</b> 🚨", ""]
    for o in offers:
        msg.append(
            f"📅 {o.get('date')} - {o.get('time')}\n🏍️ {o.get('discipline')} - 💰 {o.get('price')}\n"
        )
    msg.append(f"🔗 <a href='{TARGET_URL}'>Book Now</a>")
    return "\n".join(msg)
