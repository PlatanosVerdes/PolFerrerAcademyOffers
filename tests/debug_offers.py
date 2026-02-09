#!/usr/bin/env python3
"""Debug script to check current offers"""
import scraper
import database
from datetime import datetime

print(f"=== FECHA ACTUAL: {datetime.now().date()} ===\n")

# 1. Check scraper
print("1️⃣ OFERTAS DEL SCRAPER:")
offers, date_range = scraper.get_new_offers()
print(f"   Total: {len(offers)}")
for offer in offers:
    print(
        f"   - {offer['date']} {offer['time']} - {offer['discipline']} ({offer['price']})"
    )

# 2. Check saved cache
print("\n2️⃣ OFERTAS EN CACHE (offers_cache.json):")
cached_offers, cached_range, notified = database.load_cached_offers()
print(f"   Total: {len(cached_offers)}")
for offer in cached_offers:
    print(
        f"   - {offer['date']} {offer['time']} - {offer['discipline']} ({offer['price']})"
    )

# 3. Check if filtering works
print("\n3️⃣ TEST DE FILTRADO:")
test_offers = [
    {"date": "2026-02-08", "discipline": "Test", "time": "10:00", "price": "50€"},
    {"date": "2026-02-09", "discipline": "Test", "time": "11:00", "price": "50€"},
    {"date": "2026-02-10", "discipline": "Test", "time": "12:00", "price": "50€"},
]
for offer in test_offers:
    is_valid = database._is_current_or_future_offer(offer)
    print(f"   {offer['date']}: {'✅ VÁLIDA' if is_valid else '❌ ANTIGUA'}")
