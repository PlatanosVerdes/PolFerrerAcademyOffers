import requests
import json
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

# Configure Logger
logger = logging.getLogger("Scraper")

# Constants
BASE_URL = "https://www.polferrer.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
# Regex to capture the "offers" array inside the Next.js script
OFFERS_PATTERN = re.compile(r'\\?"offers\\?":\s*(\[\{.*?\}\])')
# Same idea for the "events" array (one entry per day the event runs).
EVENTS_PATTERN = re.compile(r'\\?"events\\?":\s*(\[\{.*?\}\])')
# Event slugs the homepage links to; tells us which events currently exist.
EVENT_SLUG_PATTERN = re.compile(r'/eventos/([a-z0-9\-]+)')
# Cap the forward week scan so a missing/far event can't loop forever.
MAX_LOOKAHEAD_WEEKS = 16


def _process_offer(raw_item: Dict) -> Dict[str, str]:
    """
    Internal helper: Parses a single raw offer item, calculates the real price,
    and formats the date and time correctly.
    """
    # Warn (don't fail) if the site drops fields we depend on.
    for required in ("date", "cents"):
        if required not in raw_item:
            logger.warning(
                f"⚠️ Offer item missing '{required}'. Site schema may have "
                f"changed. Raw keys: {sorted(raw_item.keys())}"
            )

    # 1. Price Calculation (Deposit x 2)
    deposit_cents = raw_item.get("cents", 0)
    total_price_euro = (deposit_cents * 2) / 100

    # 2. Date & Time Parsing
    raw_date = raw_item.get("date", "")
    raw_hour = raw_item.get("hour")

    # Fall back to the 'disciplines' array used by the site's 'rates' block.
    discipline = raw_item.get("discipline")
    if discipline is None:
        disciplines = raw_item.get("disciplines")
        if isinstance(disciplines, list) and disciplines:
            discipline = disciplines[0]
        else:
            logger.warning(
                f"⚠️ Offer item missing 'discipline'/'disciplines'. Raw keys: "
                f"{sorted(raw_item.keys())}"
            )
            discipline = "General"

    try:
        # Parse date
        dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        formatted_date = dt.strftime("%Y-%m-%d")

        # Parse time: Use 'hour' field if available, otherwise use ISO time
        if raw_hour is not None:
            formatted_time = f"{int(raw_hour):02d}:00"
        else:
            formatted_time = dt.strftime("%H:%M")

    except ValueError:
        formatted_date = raw_date
        formatted_time = f"{raw_hour}:00" if raw_hour is not None else "??"

    return {
        "is_offer": True,
        "discipline": discipline.capitalize(),
        "date": formatted_date,
        "time": formatted_time,
        "price": f"{total_price_euro:.0f}€",
        "original_date": raw_date,
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

        # An empty offers list is the normal "no offers" state, not an error.
        if re.search(r'\\?"offers\\?":\s*\[\]', response.text):
            return [], "no offers"

        # Extract the specific JSON block using Regex
        match = OFFERS_PATTERN.search(response.text)

        if not match:
            logger.warning("⚠️ 'offers' block not found in HTML.")
            return [], "No data found"

        # Clean Next.js artifacts (escaped quotes and $D prefixes)
        clean_json = match.group(1).replace('\\"', '"').replace("$D", "")

        try:
            raw_offers_data = json.loads(clean_json)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing JSON: {e}")
            return [], "JSON Error"

        # Process offers using list comprehension
        found_items = [_process_offer(item) for item in raw_offers_data]

        # TODO: Extract date range from the page if needed. For now, we return "unknown".
        date_range = "unknown"

        logger.info(
            f"✅ Analysis complete. {f'{len(found_items)} ofertas encontradas' if found_items else 'Sin ofertas'}"
        )
        return found_items, date_range

    except requests.RequestException as e:
        logger.error(f"❌ Network error during scraping: {e}")
        return [], "Network Error"
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return [], "Unexpected Error"


def _week_url(offer: Dict) -> str:
    """Booking URL for the offer's week ('?week=' expects that week's Monday)."""
    raw = offer.get("original_date") or offer.get("date", "")
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        monday = dt.date() - timedelta(days=dt.weekday())
        return f"{BASE_URL}/?week={monday.isoformat()}"
    except (ValueError, AttributeError):
        return BASE_URL


def format_offer_message(offers: List[Dict]) -> str:
    """
    Formats the list of offers into an HTML message for Telegram.
    """
    if not offers:
        return f"🔎 No hay ofertas disponibles en este momento. Visita {BASE_URL} para ver todas las actividades."

    lines = ["🚨 <b>¡NUEVAS OFERTAS!</b> 🚨", ""]

    for offer in offers:
        lines.append(
            f"📅 <b>{offer['date']}</b> a las <b>{offer['time']}</b>\n"
            f"🏍️ {offer['discipline']} - 💰 <b>{offer['price']}</b>\n"
            f'🔗 <a href="{_week_url(offer)}">Reservar esta semana</a>\n'
        )

    return "\n".join(lines)


def _parse_week_events(html: str) -> List[Dict]:
    """Parse the per-day 'events' entries from a single week's HTML (raw)."""
    if re.search(r'\\?"events\\?":\s*\[\]', html):
        return []
    match = EVENTS_PATTERN.search(html)
    if not match:
        return []
    clean_json = match.group(1).replace('\\"', '"').replace("$D", "")
    try:
        return json.loads(clean_json)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parsing events JSON: {e}")
        return []


def _week_monday(day) -> "datetime.date":
    return day - timedelta(days=day.weekday())


def get_new_events() -> List[Dict]:
    """
    Fetch upcoming events. The homepage lists which events exist (via
    '/eventos/<slug>' links); their structured per-day data only shows on the
    week they run, so we scan forward week by week until every listed event is
    found. Multiple per-day entries are grouped into one event with a date range.
    Returns [] with zero extra requests when the homepage lists no events.
    """
    try:
        logger.info("📡 Downloading homepage to look for events...")
        home = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        home.raise_for_status()

        wanted_slugs = set(EVENT_SLUG_PATTERN.findall(home.text))
        if not wanted_slugs:
            logger.info("✅ No events listed on the homepage.")
            return []

        logger.info(f"🔎 Homepage lists events: {sorted(wanted_slugs)}. Scanning weeks...")
        grouped: Dict[str, Dict] = {}
        start_monday = _week_monday(datetime.now().date())

        for i in range(MAX_LOOKAHEAD_WEEKS):
            monday = start_monday + timedelta(weeks=i)
            # Reuse the already-downloaded homepage for the current week.
            if i == 0:
                week_html = home.text
            else:
                resp = requests.get(
                    f"{BASE_URL}/?week={monday.isoformat()}", headers=HEADERS, timeout=15
                )
                resp.raise_for_status()
                week_html = resp.text

            for raw in _parse_week_events(week_html):
                _group_event_entry(grouped, raw)

            # Stop once we've located every event the homepage advertises.
            if wanted_slugs.issubset(grouped.keys()):
                logger.info(f"✅ Located all {len(grouped)} event(s) by week {monday.isoformat()}.")
                break
        else:
            missing = wanted_slugs - grouped.keys()
            if missing:
                logger.warning(f"⚠️ Events not found within {MAX_LOOKAHEAD_WEEKS} weeks: {sorted(missing)}")

        events = [_finalize_event(e) for e in grouped.values()]
        logger.info(f"✅ Events scan complete. {len(events)} event(s) found.")
        return events

    except requests.RequestException as e:
        logger.error(f"❌ Network error scanning events: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Unexpected error scanning events: {e}")
        return []


def _group_event_entry(grouped: Dict[str, Dict], raw: Dict):
    """Accumulate one raw per-day event entry into the grouped-by-slug map."""
    slug = raw.get("slug")
    if not slug:
        logger.warning(f"⚠️ Event entry missing 'slug'. Raw keys: {sorted(raw.keys())}")
        return None

    disciplines = raw.get("disciplines") or []
    entry = grouped.setdefault(
        slug,
        {
            "slug": slug,
            "name": raw.get("name", slug),
            "disciplines": disciplines,
            "cents": raw.get("cents", 0),
            "dates": [],
            "all_full": True,
        },
    )

    raw_date = raw.get("date", "")
    try:
        dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        entry["dates"].append(dt.strftime("%Y-%m-%d"))
    except ValueError:
        if raw_date:
            entry["dates"].append(raw_date[:10])

    if not raw.get("isFull", False):
        entry["all_full"] = False
    return entry


def _finalize_event(entry: Dict) -> Dict[str, str]:
    """Turn an accumulated event into the flat dict the bot notifies with."""
    dates = sorted(entry["dates"])
    start_date = dates[0] if dates else "??"
    end_date = dates[-1] if dates else "??"
    disciplines = ", ".join(d.capitalize() for d in entry["disciplines"]) or "General"
    price_euro = entry.get("cents", 0) / 100

    return {
        "is_event": True,
        "slug": entry["slug"],
        "name": entry["name"],
        "disciplines": disciplines,
        "start_date": start_date,
        "end_date": end_date,
        "is_full": entry["all_full"],
        "price": f"{price_euro:.0f}€",
        "url": f"{BASE_URL}/eventos/{entry['slug']}",
    }


def format_event_message(events: List[Dict]) -> str:
    """Format the list of events into an HTML message for Telegram."""
    if not events:
        return f"🔎 No hay eventos programados en este momento. Visita {BASE_URL} para ver todas las actividades."

    lines = ["🎉 <b>¡NUEVOS EVENTOS!</b> 🎉", ""]

    for event in events:
        if event["start_date"] == event["end_date"]:
            when = f"📅 <b>{event['start_date']}</b>"
        else:
            when = f"📅 <b>{event['start_date']}</b> → <b>{event['end_date']}</b>"

        status = " ⛔ <i>COMPLETO</i>" if event.get("is_full") else ""
        lines.append(
            f"🏆 <b>{event['name']}</b>{status}\n"
            f"{when}\n"
            f"🏍️ {event['disciplines']} - 💰 <b>{event['price']}</b>\n"
            f'🔗 <a href="{event["url"]}">Ver evento</a>\n'
        )

    return "\n".join(lines)
