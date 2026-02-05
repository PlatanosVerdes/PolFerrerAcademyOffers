import logging
import scraper
import database
import time

# Configuración básica de logs para ver qué pasa
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TestRun")


# Copiamos la función auxiliar de tu main.py
def generate_offer_id(offer):
    """Generate a unique ID for an offer based on its details."""
    return (
        f"{offer.get('discipline', '')}_{offer.get('date', '')}_{offer.get('time', '')}"
    )


def run_simulation():
    print("🚀 Iniciando simulación (DRY RUN)...")

    # 1. Ejecutar el Scraper
    logger.info("Scraping ofertas...")
    try:
        # Nota: Asegúrate de que scraper.get_new_offers() no sea async.
        # Si usaste la versión con requests que te pasé antes, es síncrona.
        all_items, date_range = scraper.get_new_offers()
    except Exception as e:
        logger.error(f"Error en el scraper: {e}")
        return

    # 2. Filtrar solo ofertas reales
    offers = [item for item in all_items if item.get("is_offer", False)]
    print(f"📊 Total items encontrados: {len(all_items)}")
    print(f"🔥 Ofertas reales encontradas: {len(offers)}")

    # 3. Cargar lo que ya tenemos en base de datos
    _, _, notified_offer_ids = database.load_cached_offers()
    print(f"💾 Ofertas ya notificadas anteriormente en DB: {len(notified_offer_ids)}")

    # 4. Lógica de detección de nuevas ofertas
    new_offers = []
    new_offer_ids = []

    for offer in offers:
        offer_id = generate_offer_id(offer)

        # Simulamos la comprobación
        if offer_id not in notified_offer_ids:
            new_offers.append(offer)
            new_offer_ids.append(offer_id)
            print(f"   -> [NUEVA] {offer['date']} - {offer['discipline']}")
        else:
            print(f"   -> [YA VISTA] {offer['date']} - {offer['discipline']}")

    # 5. Simular el guardado y notificación
    if new_offers:
        print(f"\n🔔 ¡Se enviarían {len(new_offers)} notificaciones!")

        # Simulamos el formateo del texto
        text = scraper.format_offer_message(new_offers)
        print("-" * 20)
        print("Cuerpo del mensaje que recibiría el usuario:")
        print(text)
        print("-" * 20)

        # Aquí es donde el bot enviaría el mensaje.
        # En el test, solo guardamos en DB si queremos actualizar el estado.
        # Si quieres probarlo muchas veces, COMENTA la siguiente línea para que no se guarden
        # y siempre te aparezcan como "Nuevas".

        # database.save_offers(offers, date_range)
        # database.mark_offers_as_notified(new_offer_ids)
        # print("✅ Base de datos actualizada (Simulación).")

    else:
        print("\n😴 No hay ofertas nuevas que notificar.")


if __name__ == "__main__":
    run_simulation()
