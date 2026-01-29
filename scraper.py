import requests
import logging
import re
import json
from datetime import datetime

logger = logging.getLogger("Scraper")

URL_POL = "https://www.polferrer.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

JSON_DISCIPLINE_MAP = {
    "wheelie": "Wheelie 🟢",
    "drift": "Drift 🔴",
    "offroad": "Off-road 🟠",
    "stoppie": "Stoppie 🔵",
    "asphalt": "Asfalto ⚪",
}

def get_new_offers():
    """Fetches the site and returns active offers and the detected range."""
    try:
        response = requests.get(URL_POL, headers=HEADERS, timeout=15)
        response.raise_for_status()

        # Extraemos los datos del JSON oculto
        offers = _extract_hidden_json_data(response.text)
        
        # Intentamos sacar el rango de fechas para el mensaje "vacio"
        # Usamos la primera y última oferta si existen como referencia
        if offers:
            date_range = f"del {offers[0]['date']} al {offers[-1]['date']}"
        else:
            date_range = "próximas semanas"

        return offers, date_range

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return [], "Error"

def _extract_hidden_json_data(html_content):
    found_items = []
    # Buscamos el objeto "offers" dentro del script de Next.js
    patron = r'"offers":(\[.*?\]),"rates"'
    coincidencia = re.search(patron, html_content)

    if not coincidencia:
        logger.warning("No internal JSON data found in HTML.")
        return []

    json_limpio = coincidencia.group(1).replace('"$D', '"')

    try:
        lista_ofertas = json.loads(json_limpio)
    except json.JSONDecodeError:
        logger.error("Error decoding hidden JSON.")
        return []

    for item in lista_ofertas:
        # Fecha
        fecha_raw = item.get("date", "")
        try:
            dt_object = datetime.fromisoformat(fecha_raw.replace("Z", ""))
            fecha_bonita = dt_object.strftime("%d %b")
        except:
            fecha_bonita = fecha_raw

        # Precio
        cents = item.get("cents", 0)
        precio_fmt = f"{cents / 100:.0f}€"

        # Disciplina
        raw_discipline = item.get("discipline", "unknown")
        discipline_display = JSON_DISCIPLINE_MAP.get(
            raw_discipline, f"{raw_discipline.capitalize()} ❓"
        )

        found_items.append({
            "is_offer": True,
            "discipline": discipline_display,
            "date": fecha_bonita,
            "time": f"{item.get('hour')}:00",
            "price": precio_fmt,
        })

    return found_items

def format_offer_message(offers, date_range):
    if not offers:
        return f"🔎 No hay ofertas disponibles para las fechas detectadas (<b>{date_range}</b>)."

    msg = ["🚨 <b>¡NUEVAS OFERTAS DETECTADAS!</b> 🚨", ""]

    for o in offers:
        msg.append(
            f"📅 <b>{o['date']}</b> - {o['time']}\n"
            f"🏍️ {o['discipline']} - 💰 <b>{o['price']}</b>\n"
        )

    msg.append(f'🔗 <a href="{URL_POL}">Reservar plaza</a>')
    return "\n".join(msg)