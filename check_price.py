import requests
import json
import re
from datetime import datetime

# Fecha que quieres investigar
TARGET_DATE = "2026-02-25" # Miércoles
TARGET_HOUR = 10

URL_POL = "https://www.polferrer.com"
HEADERS = { "User-Agent": "Mozilla/5.0" }

def check_specific_date():
    print(f"🕵️‍♂️ Investigando precio para el {TARGET_DATE} a las {TARGET_HOUR}:00h...")
    
    # 1. Descargar
    resp = requests.get(URL_POL, headers=HEADERS)
    html = resp.text
    
    # 2. Extraer Ofertas y Tarifas
    match_offers = re.search(r'\\?"offers\\?":\s*(\[\{.*?\}\])', html)
    match_rates = re.search(r'\\?"rates\\?":\s*(\[\{.*?\}\])', html)
    
    if not match_offers or not match_rates:
        print("❌ No se pudo leer el JSON de la web.")
        return

    # Limpiar JSON
    offers = json.loads(match_offers.group(1).replace('\\"', '"').replace('$D', ''))
    rates = json.loads(match_rates.group(1).replace('\\"', '"').replace('$D', ''))

    # 3. BUSCAR EN OFERTAS (Prioridad 1)
    # ¿Hay una oferta específica para ese día exacto?
    for o in offers:
        if o.get("date", "").startswith(TARGET_DATE) and o.get("hour") == TARGET_HOUR:
            cents = o.get("cents", 0)
            print(f"\n✅ ENCONTRADO EN 'OFFERS' (Es un día especial)")
            print(f"   Precio JSON (Depósito): {cents/100:.0f}€")
            print(f"   Precio Web Estimado (x2): {(cents*2)/100:.0f}€")
            return

    # 4. BUSCAR EN TARIFAS ESTÁNDAR (Prioridad 2)
    # Si no es oferta, miramos cuánto vale ese día de la semana normalmente
    dt = datetime.strptime(TARGET_DATE, "%Y-%m-%d")
    day_of_week = dt.weekday() # 0=Lunes, ... 2=Miércoles, ... 6=Domingo
    # OJO: Python: Lunes=0, Domingo=6. 
    # Next.js suele usar Domingo=0 o Lunes=1. 
    # En tus logs anteriores vi: "dayOfWeek":0 para Domingo. Así que hay que ajustar.
    # Python (Mon=0...Sun=6) -> Next (Sun=0, Mon=1...Sat=6) ?
    # Vamos a probar con la conversión estándar de JS: Sunday=0.
    js_day = (day_of_week + 1) % 7 

    print(f"   (Buscando tarifa base para Día de semana: {js_day})")

    found_rate = False
    for r in rates:
        if r.get("dayOfWeek") == js_day and r.get("hour") == TARGET_HOUR:
            cents = r.get("cents", 0)
            disc = r.get("discipline")
            print(f"\n✅ ENCONTRADO EN 'RATES' (Tarifa Estándar)")
            print(f"   Disciplina: {disc}")
            print(f"   Precio JSON (Depósito): {cents/100:.0f}€")
            print(f"   Precio Web Estimado (x2): {(cents*2)/100:.0f}€")
            found_rate = True
            break
    
    if not found_rate:
        print("❌ No hay tarifa definida para esa hora.")

if __name__ == "__main__":
    check_specific_date()