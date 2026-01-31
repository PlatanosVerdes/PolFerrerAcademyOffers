import requests
import logging
import json
from datetime import datetime
from bs4 import BeautifulSoup

logger = logging.getLogger("Scraper")

URL_POL = "https://www.polferrer.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

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
    """Extrae ofertas usando BeautifulSoup (método que funciona de main_bp.py)"""
    soup = BeautifulSoup(html_content, "html.parser")
    found_items = []

    # 1. Encontrar todas las filas de la matriz (Tailwind class 'grid-cols-8')
    grid_rows = soup.find_all("div", class_="grid-cols-8")

    if not grid_rows:
        logger.warning(
            "No 'grid-cols-8' rows found. La estructura HTML puede haber cambiado."
        )
        return []

    logger.debug(
        f"Estructura: Encontrados {len(grid_rows)} filas en la matriz del calendario."
    )

    # Diccionario para mapear Índice de Columna (1-7) -> Fecha
    col_date_map = {}

    # --- PROCESAR FILAS ---
    for row_index, row in enumerate(grid_rows):
        # Obtener hijos inmediatos (Las 8 celdas de la fila)
        cells = row.find_all(True, recursive=False)

        # Una fila válida debe tener aproximadamente 8 columnas
        if len(cells) < 8:
            continue

        # --- FILA 0: HEADERS (Fechas) ---
        if row_index == 0:
            for col_idx, cell in enumerate(cells):
                if col_idx == 0:
                    continue  # Saltar la esquina superior izquierda

                # Extraer la fecha limpia
                date_div = cell.find("div", class_="text-gray-500")
                if date_div:
                    date_text = date_div.get_text(strip=True)
                else:
                    date_text = cell.get_text(" ", strip=True)

                col_date_map[col_idx] = date_text

            # Mostrar la semana detectada
            start_date = col_date_map.get(1, "?")
            end_date = col_date_map.get(7, "?")
            logger.info(f"📅 SEMANA DETECTADA: Del [{start_date}] al [{end_date}]")
            continue

        # --- FILA > 0: FRANJAS HORARIAS ---
        # 1. Obtener etiqueta de tiempo (Columna 0)
        time_text = cells[0].get_text("", strip=True)

        # 2. Verificar Columnas 1-7 (Días de la semana)
        for col_idx in range(1, 8):
            if col_idx >= len(cells):
                break

            element = cells[col_idx]

            # Identificar si hay un botón (Franja activa)
            button = None
            if element.name == "button":
                button = element
            else:
                button = element.find("button")

            if button:
                classes = button.get("class", [])

                # A. Identificar Disciplina
                discipline = "Unknown"
                for css, name in DISCIPLINE_MAP.items():
                    if css in classes:
                        discipline = name
                        break

                # B. Obtener contenido de texto
                text_content = button.get_text(" ", strip=True)

                # C. Verificar si es una OFERTA
                is_offer = "Oferta" in text_content or "Offer" in text_content

                # D. Extraer Precio
                price_span = button.find("span")
                price = price_span.get_text(strip=True) if price_span else "N/A"

                if discipline != "Unknown":
                    # Loguear si es una oferta para debug
                    if is_offer:
                        logger.info(
                            f"⚡ OFERTA ENCONTRADA! {discipline} el {col_date_map.get(col_idx)} a las {time_text}"
                        )

                    found_items.append(
                        {
                            "is_offer": is_offer,
                            "discipline": discipline,
                            "date": col_date_map.get(col_idx, "Unknown Date"),
                            "time": time_text,
                            "price": price,
                        }
                    )

    return found_items


def format_offer_message(offers):
    if not offers:
        return f"🔎 No hay ofertas disponibles por el momento."

    msg = ["🚨<b>¡NUEVAS OFERTAS!</b>🚨", ""]

    for o in offers:
        msg.append(
            f"📅 <b>{o['date']}</b> - {o['time']}\n"
            f"🏍️ {o['discipline']} - 💰 <b>{o['price']}</b>\n"
        )

    msg.append(f'🔗 <a href="{URL_POL}">Reservar plaza</a>')
    return "\n".join(msg)
