"""Price monitor.

Tracks a list of products over time: fetches the current price for each
tracked product, appends a (timestamp, price) row to a CSV history file,
and reports which products dropped below their target price.

Demo mode uses a mock fetcher with predefined price moves — no network:

    python -m scrapers.price_monitor --demo
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from scrapers.utils import append_csv, fetch

HISTORY_FIELDNAMES = ["timestamp", "product", "url", "price", "target_price"]

MOCK_PAGES = {
    "https://example.com/p/headphones": (
        "Wireless Headphones Pro",
        '<div class="price">$69.99</div>',
        79.99,
    ),
    "https://example.com/p/keyboard": (
        "Mechanical Keyboard RGB",
        '<div class="price">$139.99</div>',
        120.00,
    ),
    "https://example.com/p/mouse": (
        "Ergonomic Wireless Mouse",
        '<div class="price">$29.99</div>',
        30.00,
    ),
}


def parse_price(text: str) -> Optional[float]:
    """Extract a numeric price from strings like '$1,299.99', '₹8,499'."""
    cleaned = text.replace(",", "")
    match = re.search(r"\d+(?:\.\d{1,2})?", cleaned)
    if not match:
        return None
    return float(match.group(0))


def extract_price_from_html(html: str) -> Optional[float]:
    """Pull the price out of a product page: common price selectors first."""
    soup = BeautifulSoup(html, "lxml")
    for selector in [".price", "#price", "[itemprop='price']", ".product-price"]:
        el = soup.select_one(selector)
        if el and el.get_text(strip=True):
            price = parse_price(el.get_text(strip=True))
            if price is not None:
                return price
    return None


def check_products(
    products: List[Dict[str, object]],
    *,
    history_csv: str,
    fetcher: Optional[Callable[[str], str]] = None,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    """Fetch current prices, append history rows, return (history_rows, alerts).

    Each product: {"name": str, "url": str, "target_price": float}.
    An alert fires when current price < target price.
    """
    do_fetch = fetcher or (lambda url: fetch(url))
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    history_rows: List[Dict[str, object]] = []
    alerts: List[Dict[str, object]] = []
    for product in products:
        name = str(product["name"])
        url = str(product["url"])
        target = float(product["target_price"])
        try:
            html = do_fetch(url)
            price = extract_price_from_html(html)
        except Exception:
            price = None
        row = {
            "timestamp": timestamp,
            "product": name,
            "url": url,
            "price": price if price is not None else "",
            "target_price": target,
        }
        history_rows.append(row)
        append_csv(
            {k: str(v) for k, v in row.items()},
            history_csv,
            fieldnames=HISTORY_FIELDNAMES,
        )
        if price is not None and price < target:
            alerts.append(
                {
                    "name": name,
                    "url": url,
                    "price": price,
                    "target_price": target,
                    "drop": round(target - price, 2),
                }
            )
    return history_rows, alerts


def demo_products() -> List[Dict[str, object]]:
    return [
        {"name": name, "url": url, "target_price": target}
        for url, (name, _html, target) in MOCK_PAGES.items()
    ]


def demo_fetcher(url: str) -> str:
    name, html, _target = MOCK_PAGES[url]
    return f"<html><body><h1>{name}</h1>{html}</body></html>"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Price monitor")
    parser.add_argument("--history", default="output/price_history.csv")
    parser.add_argument("--demo", action="store_true", help="Run with mock prices")
    args = parser.parse_args(argv)
    products = demo_products() if args.demo else []
    if not args.demo:
        parser.error("provide products via Python API; or use --demo")
    history, alerts = check_products(
        products, history_csv=args.history, fetcher=demo_fetcher
    )
    print(f"Checked {len(history)} products -> {args.history}")
    if alerts:
        print("PRICE DROP ALERTS:")
        for alert in alerts:
            print(
                f"  - {alert['name']}: ${alert['price']} "
                f"(target ${alert['target_price']}, saved ${alert['drop']})"
            )
    else:
        print("No price drops below target.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
