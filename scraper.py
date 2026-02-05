import requests
import json
import re
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Configure Logger
logger = logging.getLogger("Scraper")

# Constants
BASE_URL = "https://www.polferrer.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
# Regex to capture the "offers" array inside the Next.js script
OFFERS_PATTERN = re.compile(r'\\?"offers\\?":\s*(\[\{.*?\}\])')


def _process_offer(raw_item: Dict) -> Dict[str, str]:
    """
    Internal helper: Parses a single raw offer item, calculates the real price, 
    and formats the date.
    """
    # 1. Price Calculation
    # JSON contains the deposit (50%). We multiply by 2 for the full price.
    deposit_cents = raw_item.get("cents", 0)
    total_price_euro = (deposit_cents * 2) / 100

    # 2. Date Parsing
    raw_date = raw_item.get("date", "")
    try:
        # Handle ISO format. Replace Z with +00:00 for compatibility
        dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        formatted_date = dt.strftime("%Y-%m-%d")
        formatted_time = dt.strftime("%H:%M")
    except ValueError:
        formatted_date = raw_date
        formatted_time = "??"

    return {
        "is_offer": True,
        "discipline": raw_item.get("discipline", "General").capitalize(),
        "date": formatted_date,
        "time": formatted_time,
        "price": f"{total_price_euro:.0f}€",
        "original_date": raw_date
    }


def get_new_offers() -> Tuple[List[Dict], str]:
    """
    Main function called by main.py.
    Fetches the website, extracts the hidden JSON data using Regex, 
    and parses available offers.
    """
    try:
        logger.info("📡 Downloading data from PolFerrer...")
        response = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()

        # Extract the specific JSON block using Regex
        match = OFFERS_PATTERN.search(response.text)
        
        if not match:
            logger.warning("⚠️ 'offers' block not found in HTML.")
            return [], "No data found"

        # Clean Next.js artifacts (escaped quotes and $D prefixes)
        clean_json = match.group(1).replace('\\"', '"').replace('$D', '')
        
        try:
            raw_offers_data = json.loads(clean_json)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing JSON: {e}")
            return [], "JSON Error"

        # Process offers using list comprehension
        found_items = [_process_offer(item) for item in raw_offers_data]

        # Generate summary string for logs
        summary = f"{len(found_items)} ofertas encontradas" if found_items else "Sin ofertas"

        logger.info(f"✅ Analysis complete. {summary}")
        return found_items, summary

    except requests.RequestException as e:
        logger.error(f"❌ Network error during scraping: {e}")
        return [], "Network Error"
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return [], "Unexpected Error"


def format_offer_message(offers: List[Dict]) -> str:
    """
    Formats the list of offers into an HTML message for Telegram (in Spanish).
    """
    if not offers:
        return "🔎 No hay ofertas disponibles en este momento."

    # Using a list of strings is more efficient than string concatenation
    lines = ["🚨 <b>¡NUEVAS OFERTAS DETECTADAS!</b> 🚨", ""]
    
    for offer in offers:
        lines.append(
            f"📅 <b>{offer['date']}</b> a las {offer['time']}\n"
            f"🏍️ {offer['discipline']} - 💰 <b>{offer['price']}</b>\n"
        )

    lines.append(f'🔗 <a href="{BASE_URL}">Reservar ahora</a>')
    
    return "\n".join(lines)