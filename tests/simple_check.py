#!/usr/bin/env python3
import sys

sys.path.insert(0, "/home/jorge.gonzalez/personal/PolFerrerAcademyOffers")
import database
from datetime import datetime

print(f"Fecha actual: {datetime.now().date()}")
print()

cached_offers, cached_range, notified = database.load_cached_offers()
print(f"Ofertas en cache: {len(cached_offers)}")
for offer in cached_offers:
    print(f"  {offer['date']} {offer['time']} - {offer['discipline']}")
