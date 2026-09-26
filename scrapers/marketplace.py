"""Marketplace product + image collector.

Scrapes product cards (name, price, image URL, rating) from a generic
marketplace-style HTML layout, downloads the product images, and writes
everything to CSV + an images folder.

Demo mode runs entirely offline against bundled sample HTML:

    python -m scrapers.marketplace --demo
"""

import argparse
import os
import sys
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from scrapers.utils import fetch, save_csv, slugify

SAMPLE_HTML = """\
<html><body>
<div class="products">
  <div class="product-card">
    <img class="product-image" src="https://example.com/img/headphones.jpg" alt="Wireless Headphones"/>
    <h2 class="product-name">Wireless Headphones Pro</h2>
    <span class="product-price">$79.99</span>
    <span class="product-rating">4.5</span>
  </div>
  <div class="product-card">
    <img class="product-image" src="https://example.com/img/keyboard.jpg" alt="Mechanical Keyboard"/>
    <h2 class="product-name">Mechanical Keyboard RGB</h2>
    <span class="product-price">$129.50</span>
    <span class="product-rating">4.8</span>
  </div>
  <div class="product-card">
    <img class="product-image" src="https://example.com/img/mouse.jpg" alt="Ergonomic Mouse"/>
    <h2 class="product-name">Ergonomic Wireless Mouse</h2>
    <span class="product-price">$34.99</span>
    <span class="product-rating">4.2</span>
  </div>
</div>
</body></html>
"""

FIELDNAMES = ["name", "price", "image_url", "rating", "image_file"]


def parse_products(html: str, base_url: str = "") -> List[Dict[str, str]]:
    """Parse product cards from marketplace-style HTML."""
    soup = BeautifulSoup(html, "lxml")
    products = []
    for card in soup.select(".product-card"):
        name_el = card.select_one(".product-name")
        price_el = card.select_one(".product-price")
        img_el = card.select_one(".product-image")
        rating_el = card.select_one(".product-rating")
        name = name_el.get_text(strip=True) if name_el else ""
        if not name:
            continue  # skip malformed cards
        image_url = img_el.get("src", "") if img_el else ""
        if base_url and image_url:
            image_url = urljoin(base_url, image_url)
        products.append(
            {
                "name": name,
                "price": price_el.get_text(strip=True) if price_el else "",
                "image_url": image_url,
                "rating": rating_el.get_text(strip=True) if rating_el else "",
                "image_file": "",
            }
        )
    return products


def download_image(url: str, dest_path: str, *, timeout: float = 20.0) -> bool:
    """Download one image to dest_path. Returns True on success."""
    if not url:
        return False
    try:
        resp = requests.get(url, stream=True, timeout=timeout)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except requests.RequestException:
        return False


def download_images(
    products: List[Dict[str, str]],
    images_dir: str,
    *,
    demo: bool = False,
) -> List[Dict[str, str]]:
    """Download each product image into images_dir; records image_file name.

    In demo mode no network is used — a placeholder file is written instead.
    """
    os.makedirs(images_dir, exist_ok=True)
    for product in products:
        filename = slugify(product["name"]) + ".jpg"
        dest = os.path.join(images_dir, filename)
        if demo:
            with open(dest, "wb") as f:
                f.write(b"DEMO-IMAGE-PLACEHOLDER")
            ok = True
        else:
            ok = download_image(product["image_url"], dest)
        product["image_file"] = filename if ok else ""
    return products


def scrape_marketplace(
    url: str,
    out_csv: str,
    images_dir: str,
    *,
    demo: bool = False,
) -> List[Dict[str, str]]:
    """Full pipeline: fetch -> parse -> download images -> save CSV."""
    html = SAMPLE_HTML if demo else fetch(url)
    products = parse_products(html, base_url=url)
    download_images(products, images_dir, demo=demo)
    save_csv(products, out_csv, fieldnames=FIELDNAMES)
    return products


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Marketplace product+image collector")
    parser.add_argument("--url", default="", help="Marketplace listing page URL")
    parser.add_argument("--out", default="output/marketplace_products.csv")
    parser.add_argument("--images", default="output/marketplace_images")
    parser.add_argument("--demo", action="store_true", help="Run against bundled sample HTML")
    args = parser.parse_args(argv)
    if not args.demo and not args.url:
        parser.error("--url is required unless --demo is used")
    products = scrape_marketplace(args.url, args.out, args.images, demo=args.demo)
    print(f"Collected {len(products)} products -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
