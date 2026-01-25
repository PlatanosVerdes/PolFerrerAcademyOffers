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

# Mapa para traducir el texto del JSON a tus Emojis
JSON_DISCIPLINE_MAP = {
    "wheelie": "Wheelie 🟢",
    "drift": "Drift 🔴",
    "offroad": "Off-road 🟠",
    "stoppie": "Stoppie 🔵",
    "asphalt": "Asfalto ⚪",
    "racing": "Racing 🏁",
}


def get_new_offers():
    """Fetches the site and returns only the active offers."""
    try:
        response = requests.get(URL_POL, headers=HEADERS, timeout=15)
        response.raise_for_status()

        # Ahora extraemos los datos crudos, que contienen TODAS las semanas
        items = _extract_hidden_json_data(response.text)

        # Filtramos solo lo que sea Wheelie (o lo que quieras)
        # Nota: En el JSON, todo lo que está en la lista "offers" ES una oferta.
        return [i for i in items if "Wheelie" in i["discipline"]]

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return []


def _extract_hidden_json_data(html_content):
    """
    Extrae los datos ocultos del JSON de Next.js en lugar de mirar los divs.
    Esto permite ver ofertas de meses futuros sin hacer click.
    """
    found_items = []

    # 1. Buscamos el patrón donde se guardan los datos: "offers":[ ... ]
    # Esto es mucho más robusto que buscar clases CSS que pueden cambiar
    patron = r'"offers":(\[.*?\]),"rates"'
    coincidencia = re.search(patron, html_content)

    if not coincidencia:
        logger.warning("No se encontraron datos internos (JSON) en el HTML.")
        return []

    # 2. Limpiamos el JSON (Next.js pone símbolos raros como $D antes de las fechas)
    datos_crudos = coincidencia.group(1)
    json_limpio = datos_crudos.replace('"$D', '"')

    try:
        lista_ofertas = json.loads(json_limpio)
    except json.JSONDecodeError:
        logger.error("Error al interpretar el JSON oculto.")
        return []

    # 3. Procesamos la lista limpia
    for item in lista_ofertas:
        # --- Formatear Fecha ---
        fecha_raw = item.get("date", "")
        try:
            # Quitamos la 'Z' y parseamos. Ejemplo: 2026-01-23T00:00:00.000Z
            dt_object = datetime.fromisoformat(fecha_raw.replace("Z", ""))
            # Formato legible: 23 ene
            fecha_bonita = dt_object.strftime("%d %b")
        except ValueError:
            fecha_bonita = fecha_raw

        # --- Formatear Precio ---
        # El precio viene en centimos (5000 = 50.00)
        cents = item.get("cents", 0)
        precio_fmt = f"{cents / 100:.0f}€"

        # --- Mapear Disciplina ---
        raw_discipline = item.get("discipline", "unknown")
        discipline_display = JSON_DISCIPLINE_MAP.get(
            raw_discipline, f"{raw_discipline.capitalize()} ❓"
        )

        # Construimos el objeto igual que lo hacías tú antes
        found_items.append(
            {
                "is_offer": True,  # Si está en esta lista JSON, ES una oferta
                "discipline": discipline_display,
                "date": fecha_bonita,
                "time": f"{item.get('hour')}:00",  # La hora viene como entero (ej: 17)
                "price": precio_fmt,
            }
        )

    # Ordenamos por fecha para que salga bonito
    # (Necesitamos volver a parsear la fecha para ordenar, o confiar en el orden del json)
    # Aquí simplemente devolvemos la lista tal cual
    return found_items


def format_offer_message(offers):
    if not offers:
        return "No hay ofertas disponibles en este momento."

    msg = ["🚨 <b>¡NUEVAS OFERTAS DETECTADAS!</b> 🚨", ""]

    for o in offers:
        msg.append(
            f"📅 <b>{o['date']}</b> - {o['time']}\n"
            f"🏍️ {o['discipline']} - 💰 <b>{o['price']}</b>\n"
        )

    msg.append(f'🔗 <a href="{URL_POL}">Reservar plaza</a>')
    return "\n".join(msg)


# --- PRUEBA RÁPIDA (Solo para ejecutar este fichero) ---
if __name__ == "__main__":
    ofertas = get_new_offers()
    print(format_offer_message(ofertas))
