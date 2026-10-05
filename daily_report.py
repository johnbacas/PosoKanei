#!/usr/bin/env python3
"""
daily_report.py
----------------
Run this every morning. It reads products.json (built by setup_products.py),
fetches today's retailer prices for each product from PosoKanei, and writes
two report files into reports/:

  - reports/YYYY-MM-DD_prices.csv     -> full price matrix (product x retailer)
  - reports/YYYY-MM-DD_cheapest.txt   -> "which supermarket is cheapest for what" (in Greek)

Usage:
    pip install requests
    python daily_report.py
"""

import csv
import json
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

import requests

API_BASE = "https://api.posokanei.gov.gr"
BASE_DIR = Path(__file__).parent
PRODUCTS_FILE = BASE_DIR / "products.json"
REPORTS_DIR = BASE_DIR / "reports"
HISTORY_FILE = BASE_DIR / "price_history.json"
MIN_INTERVAL_S = 1.5  # be gentle with the (undocumented) API
HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "origin": "https://posokanei.gov.gr",
    "referer": "https://posokanei.gov.gr/",
    "accept-language": "el-GR,el;q=0.9,en;q=0.8",
}
ROUND_DP = 2  # compare prices rounded to cents so 3.4500 vs 3.4501 still ties

# Fallback only - used when a retailer's history entries have no "country" field at all.
GREEK_RETAILER_IDS = {
    "bazaar", "lidl", "market_in", "mymarket", "ab_vasilopoulos",
    "galaxias", "kritikos", "masoutis", "synka", "sklavenitis", "halkiadakis",
}


def load_products():
    if not PRODUCTS_FILE.exists():
        print(f"No {PRODUCTS_FILE} found. Run setup_products.py first.")
        sys.exit(1)
    return json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))


def get_product(product_id: str, include_history: bool = False):
    params = {
        "countries": "GR",
        "include_tax": "true",
    }
    if include_history:
        params["include_history"] = "true"
    resp = requests.get(f"{API_BASE}/products/{product_id}", params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()

def historic_prices(data: dict):
    """Real historic minimum price, overall and per Greek retailer, from PosoKanei's own history data.
    
    Returns {"global_min": float | None, "min_per_retailer": {retailer_id: float}}.
    retailer_id here is whatever key PosoKanei's history block uses (e.g. "mymarket") -
    translating that to a display name happens in the caller, since this function has
    no access to retailer_prices.
    """
    
    daily_prices = (data.get("history") or {}).get("daily_prices") or {}
    min_per_retailer = {}
    for retailer_id, entries in daily_prices.items():
        if not entries:
            continue  # nothing to check

        first_country = entries[0].get("country")
        if first_country is not None:
            if first_country != "GR":
                continue  # whole retailer is non-Greek - skip it entirely
        elif retailer_id not in GREEK_RETAILER_IDS:
            continue  # no country info at all - fall back to the known-id list

        prices = [e["price"] for e in entries if e.get("price") is not None]
        if prices:
            min_per_retailer[retailer_id] = min(prices)

    global_min = min(min_per_retailer.values()) if min_per_retailer else None
    return {"global_min": global_min, "min_per_retailer": min_per_retailer}
    

def load_history_file():
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return {}


def save_history_file(history: dict):
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def retailer_label(rp: dict) -> str:
    # NOTE: retailer_name is the *product's* name as that retailer lists it,
    # not the store's name - never use it here, even as a fallback.
    return rp.get("retailer_display_name") or rp.get("retailer") or "Unknown"


def retailers_at_min(entry: dict) -> str:
    """Comma-separated list of retailer labels that hit this product's global_min."""
    global_min = entry.get("global_min")
    per_retailer = entry.get("min_per_retailer") or {}
    winners = sorted(r for r, p in per_retailer.items() if p == global_min)
    return ", ".join(winners) if winners else "n/a"


def main():
    tracked = load_products()
    if not tracked:
        print("products.json is empty. Run setup_products.py to add products first.")
        sys.exit(1)

    REPORTS_DIR.mkdir(exist_ok=True)
    today = date.today().isoformat()

    answer = input("Include price history in this report? (Y/N): ").strip().lower()
    want_history = answer == "y"

    # product_name -> {retailer_label: price}
    price_matrix = {}
    # product_name -> {"global_min":..., "min_per_retailer": {label: price}} just fetched this run
    fresh_hist = {}
    all_retailers = set()
    failures = []

    print(f"Fetching prices for {len(tracked)} product(s)...")
    for item in tracked:
        pid, name = item["id"], item["name"]
        try:
            data = get_product(pid, include_history=want_history)
        except requests.RequestException as e:
            print(f"  ! Failed to fetch '{name}' ({pid}): {e}")
            failures.append(name)
            time.sleep(MIN_INTERVAL_S)
            continue

        prices = {}
        id_to_label = {}
        for rp in data.get("retailer_prices", []) or []:
            label = retailer_label(rp)
            rid = rp.get("retailer")
            if rid:
                id_to_label[rid] = label
            price = rp.get("price")
            if price is None:
                continue
            all_retailers.add(label)
            # if a retailer appears twice (e.g. discount vs regular), keep the lower one
            if label not in prices or price < prices[label]:
                prices[label] = round(float(price), ROUND_DP)

        price_matrix[name] = prices

        if want_history:
            hp = historic_prices(data)
            fresh_hist[name] = {
                "global_min": round(hp["global_min"], ROUND_DP) if hp["global_min"] is not None else None,
                "min_per_retailer": {
                    id_to_label.get(rid, rid): round(price, ROUND_DP)
                    for rid, price in hp["min_per_retailer"].items()
                },
            }

        print(f"  - {name}: {len(prices)} retailer price(s)")
        time.sleep(MIN_INTERVAL_S)

    # Update price_history.json only when history was actually fetched this run
    if want_history:
        stored_history = load_history_file()
        for name, hp in fresh_hist.items():
            if hp["global_min"] is not None:
                stored_history[name] = {
                    "global_min": hp["global_min"],
                    "min_per_retailer": hp["min_per_retailer"],
                    "as_of": today,
                }
        save_history_file(stored_history)
        print(f"Updated {HISTORY_FILE}")

    # The report always reads from price_history.json - fresh if we just
    # updated it above, otherwise whatever was last saved there
    hist_lookup = load_history_file()

    all_retailers = sorted(all_retailers)

    # --- write full price matrix CSV ---
    csv_path = REPORTS_DIR / f"{today}_prices.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["product"] + all_retailers)
        for name, prices in sorted(price_matrix.items()):
            row = [name] + [prices.get(r, "") for r in all_retailers]
            writer.writerow(row)

    # --- who's cheapest today, grouped by retailer ---
    cheapest_by_retailer = defaultdict(list)
    products_with_no_price = []

    for name, prices in sorted(price_matrix.items()):
        if not prices:
            products_with_no_price.append(name)
            continue
        today_min = min(prices.values())
        for retailer, price in prices.items():
            if price == today_min:
                cheapest_by_retailer[retailer].append((name, price))

    # --- write human-readable report (Greek) ---
    txt_path = REPORTS_DIR / f"{today}_cheapest.txt"
    with txt_path.open("w", encoding="utf-8") as f:
        f.write(f"Σύγκριση τιμών από το PosoKanei - {today}\n")
        f.write("=" * 50 + "\n\n")
        
        f.write("*" * 23 + "\n")
        f.write("*  Τιμές ανά προϊόν:  *\n")
        f.write("*" * 23 + "\n\n")
        for i, (name, prices) in enumerate(sorted(price_matrix.items()), start=1):
            if not prices:
                f.write(f"  {i}. {name}: δεν βρέθηκαν τιμές\n")
                continue
            parts = ", ".join(f"{r}={p:.2f}" for r, p in sorted(prices.items()))
            f.write(f"  {i}. {name}:\n {parts}\n")
        
        f.write("\n" + "*" * 43 + "\n")
        f.write("*  Φθηνότερα προϊόντα ανά σούπερ μάρκετ:  *\n")
        f.write("*" * 43 + "\n")
        for retailer in sorted(cheapest_by_retailer.keys()):
            f.write(f"\n{retailer}:\n")
            for name, price in sorted(cheapest_by_retailer[retailer]):
                entry = hist_lookup.get(name)
                if entry and entry.get("global_min") is not None:
                    hist_str = f"{entry['global_min']:.2f}"
                    retailers_str = retailers_at_min(entry)
                    f.write(f"{name}: {price:.2f}  (Ελάχιστη τιμή: {hist_str} σε {retailers_str})\n")
                else:
                    f.write(f"{name}: {price:.2f}  (Ελάχιστη τιμή: n/a)\n")

        if products_with_no_price:
            f.write("\nΔεν βρέθηκαν τιμές για:\n")
            for name in products_with_no_price:
                f.write(f"  - {name}\n")

        if failures:
            f.write("\nΑποτυχία λήψης (σφάλμα δικτύου/API):\n")
            for name in failures:
                f.write(f"  - {name}\n")

    print(f"\nDone. Reports written to:\n  {csv_path}\n  {txt_path}")


if __name__ == "__main__":
    main()
