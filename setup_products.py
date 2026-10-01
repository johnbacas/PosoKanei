#!/usr/bin/env python3
"""
setup_products.py
------------------
Run this ONCE (and again any time you want to add/remove products) to
build your tracked product list (products.json).

It searches PosoKanei by product name, shows you the matches, and lets
you pick the exact product so future daily runs use a stable product ID
instead of re-guessing from a fuzzy name search.

Usage:
    pip install requests
    python setup_products.py
"""

import json
import sys
import time
from pathlib import Path

import requests

API_BASE = "https://api.posokanei.gov.gr"
PRODUCTS_FILE = Path(__file__).parent / "products.json"
MIN_INTERVAL_S = 0.8  # be gentle with the (undocumented) API
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


def search_products(query: str, page_size: int = 8):
    body = {
        "title": query,
        "page": 1,
        "page_size": page_size,
        "sort_by": "name",
        "sort_order": "asc",
    }
    resp = requests.post(f"{API_BASE}/products/search", json=body, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json().get("products", [])


def load_existing():
    if PRODUCTS_FILE.exists():
        return json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))
    return []


def save(products):
    PRODUCTS_FILE.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {len(products)} product(s) to {PRODUCTS_FILE}")


def main():
    tracked = load_existing()
    if tracked:
        print(f"You already have {len(tracked)} product(s) tracked:")
        for i, p in enumerate(tracked, start=1):
            print(f"  [{i}] {p['name']}  (id: {p['id']})")
        print()

    print("Type a product name to search ('done' to finish, 'list' to see tracked items, 'remove' to remove one):\n")

    while True:
        query = input("Search> ").strip()
        if not query:
            continue
        if query.lower() == "done":
            break
        if query.lower() == "list":
            if not tracked:
                print("  Nothing tracked yet.")
            for i, p in enumerate(tracked, start=1):
                print(f"  [{i}] {p['name']}  (id: {p['id']})")
            continue
        if query.lower() == "remove":
            if not tracked:
                print("  Nothing tracked yet.\n")
                continue
            for i, p in enumerate(tracked, start=1):
                print(f"  [{i}] {p['name']}")
            choice = input("  Remove which number? (0 to cancel): ").strip()
            if not choice.isdigit() or int(choice) == 0:
                print("  Cancelled.\n")
                continue
            idx = int(choice) - 1
            if idx < 0 or idx >= len(tracked):
                print("  Invalid choice.\n")
                continue
            removed = tracked.pop(idx)
            save(tracked)
            print(f"  Removed: {removed['name']}\n")
            continue

        try:
            results = search_products(query)
        except requests.RequestException as e:
            print(f"  Search failed: {e}")
            continue

        time.sleep(MIN_INTERVAL_S)

        if not results:
            print("  No matches. Try a different / shorter search term.")
            continue

        print(f"\n  Found {len(results)} match(es):")
        for i, p in enumerate(results, start=1):
            brand = p.get("brand") or "-"
            unit = p.get("unit") or ""
            qty = p.get("unit_quantity") or ""
            print(f"  [{i}] {p['name']}  | brand: {brand} | {qty}{unit} | id: {p['id']}")
        print("  [0] None of these / skip")

        choice = input("  Pick a number: ").strip()
        if not choice.isdigit() or int(choice) == 0:
            print("  Skipped.\n")
            continue

        idx = int(choice) - 1
        if idx < 0 or idx >= len(results):
            print("  Invalid choice, skipped.\n")
            continue

        chosen = results[idx]
        if any(p["id"] == chosen["id"] for p in tracked):
            print("  Already tracked.\n")
            continue

        tracked.append({"id": chosen["id"], "name": chosen["name"]})
        save(tracked)  # save immediately so nothing is lost if you quit early
        print(f"  Added: {chosen['name']}\n")

    print("\nAll done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped early, but everything you'd already added was saved as you went.")
        sys.exit(1)
