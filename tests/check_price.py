import sys
from pathlib import Path

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import json
import re
from datetime import datetime

# Date you want to investigate
TARGET_DATE = "2026-02-25"  # Wednesday
TARGET_HOUR = 10

URL_POL = "https://www.polferrer.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def check_specific_date():
    print(f"🕵️‍♂️ Investigating price for {TARGET_DATE} at {TARGET_HOUR}:00h...")

    # 1. Download
    resp = requests.get(URL_POL, headers=HEADERS)
    html = resp.text

    # 2. Extract Offers and Rates
    match_offers = re.search(r'\\?"offers\\?":\s*(\[\{.*?\}\])', html)
    match_rates = re.search(r'\\?"rates\\?":\s*(\[\{.*?\}\])', html)

    if not match_offers or not match_rates:
        print("❌ Could not read JSON from the website.")
        return

    # Clean JSON
    offers = json.loads(match_offers.group(1).replace('\\"', '"').replace("$D", ""))
    rates = json.loads(match_rates.group(1).replace('\\"', '"').replace("$D", ""))

    # 3. SEARCH IN OFFERS (Priority 1)
    # Is there a specific offer for that exact day?
    for o in offers:
        if o.get("date", "").startswith(TARGET_DATE) and o.get("hour") == TARGET_HOUR:
            cents = o.get("cents", 0)
            print(f"\n✅ FOUND IN 'OFFERS' (It's a special day)")
            print(f"   JSON Price (Deposit): {cents/100:.0f}€")
            print(f"   Estimated Web Price (x2): {(cents*2)/100:.0f}€")
            return

    # 4. SEARCH IN STANDARD RATES (Priority 2)
    # If it's not an offer, we check how much that day of the week normally costs
    dt = datetime.strptime(TARGET_DATE, "%Y-%m-%d")
    day_of_week = dt.weekday()  # 0=Monday, ... 2=Wednesday, ... 6=Sunday
    # NOTE: Python: Monday=0, Sunday=6.
    # Next.js usually uses Sunday=0 or Monday=1.
    # In your previous logs I saw: "dayOfWeek":0 for Sunday. So we need to adjust.
    # Python (Mon=0...Sun=6) -> Next (Sun=0, Mon=1...Sat=6) ?
    # Let's try with the standard JS conversion: Sunday=0.
    js_day = (day_of_week + 1) % 7

    print(f"   (Looking for base rate for Day of week: {js_day})")

    found_rate = False
    for r in rates:
        if r.get("dayOfWeek") == js_day and r.get("hour") == TARGET_HOUR:
            cents = r.get("cents", 0)
            disc = r.get("discipline")
            print(f"\n✅ FOUND IN 'RATES' (Standard Rate)")
            print(f"   Discipline: {disc}")
            print(f"   JSON Price (Deposit): {cents/100:.0f}€")
            print(f"   Estimated Web Price (x2): {(cents*2)/100:.0f}€")
            found_rate = True
            break

    if not found_rate:
        print("❌ No rate defined for that hour.")


if __name__ == "__main__":
    check_specific_date()
