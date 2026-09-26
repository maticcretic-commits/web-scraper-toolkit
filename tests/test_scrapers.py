"""Unit tests for the Web Scraper Toolkit — all offline, no live network calls."""

import csv
import os

import pytest

from scrapers import marketplace, job_listings, price_monitor
from scrapers import utils


# --------------------------------------------------------------------------
# Fixtures: mock HTML
# --------------------------------------------------------------------------

MARKETPLACE_HTML = """\
<html><body>
<div class="products">
  <div class="product-card">
    <img class="product-image" src="/img/a.jpg"/>
    <h2 class="product-name">Alpha Gadget</h2>
    <span class="product-price">$49.99</span>
    <span class="product-rating">4.1</span>
  </div>
  <div class="product-card">
    <img class="product-image" src="https://cdn.example.com/b.jpg"/>
    <h2 class="product-name">Beta Widget</h2>
    <span class="product-price">₹1,299.00</span>
    <span class="product-rating">3.9</span>
  </div>
  <div class="product-card">
    <span class="product-price">$9.99</span>
  </div>
</div>
</body></html>
"""

JOBS_HTML = """\
<html><body>
<article class="job-card">
  <h2 class="job-title">QA Engineer</h2>
  <div class="company">Acme Corp</div>
  <span class="location">Patna, India</span>
  <span class="salary">₹6–8 LPA</span>
  <time class="posted-date">2026-09-25</time>
</article>
<article class="job-card">
  <h2 class="job-title">Support Agent</h2>
  <div class="company">Acme Corp</div>
</article>
</body></html>
"""


# --------------------------------------------------------------------------
# marketplace.py
# --------------------------------------------------------------------------

def test_parse_products_extracts_all_fields():
    products = marketplace.parse_products(MARKETPLACE_HTML, base_url="https://shop.example.com")
    assert len(products) == 2  # malformed card without a name is skipped
    first = products[0]
    assert first["name"] == "Alpha Gadget"
    assert first["price"] == "$49.99"
    assert first["rating"] == "4.1"
    # relative image URL resolved against base_url
    assert first["image_url"] == "https://shop.example.com/img/a.jpg"
    assert products[1]["image_url"] == "https://cdn.example.com/b.jpg"


def test_parse_products_missing_optional_fields():
    html = (
        '<div class="product-card">'
        '<h2 class="product-name">Lonely Item</h2>'
        "</div>"
    )
    products = marketplace.parse_products(html)
    assert len(products) == 1
    assert products[0]["price"] == ""
    assert products[0]["image_url"] == ""
    assert products[0]["rating"] == ""


def test_demo_pipeline_writes_csv_and_images(tmp_path):
    out_csv = str(tmp_path / "products.csv")
    images_dir = str(tmp_path / "images")
    products = marketplace.scrape_marketplace("", out_csv, images_dir, demo=True)
    assert len(products) == 3
    with open(out_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3
    assert rows[0]["name"] == "Wireless Headphones Pro"
    assert rows[0]["price"] == "$79.99"
    assert rows[0]["rating"] == "4.5"
    assert rows[0]["image_file"].endswith(".jpg")
    assert os.path.exists(os.path.join(images_dir, rows[0]["image_file"]))


# --------------------------------------------------------------------------
# job_listings.py
# --------------------------------------------------------------------------

def test_parse_jobs_extracts_all_fields():
    jobs = job_listings.parse_jobs(JOBS_HTML)
    assert len(jobs) == 2
    first = jobs[0]
    assert first["title"] == "QA Engineer"
    assert first["company"] == "Acme Corp"
    assert first["location"] == "Patna, India"
    assert first["salary"] == "₹6–8 LPA"
    assert first["posted_date"] == "2026-09-25"


def test_parse_jobs_tolerates_missing_fields():
    jobs = job_listings.parse_jobs(JOBS_HTML)
    second = jobs[1]
    assert second["title"] == "Support Agent"
    assert second["location"] == ""
    assert second["salary"] == ""


def test_demo_pipeline_writes_job_csv(tmp_path):
    out_csv = str(tmp_path / "jobs.csv")
    jobs = job_listings.scrape_jobs("", out_csv, demo=True)
    assert len(jobs) == 3
    with open(out_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[1]["title"] == "Data Analyst (SQL/Power BI)"
    assert rows[1]["location"] == "Bengaluru, India"


# --------------------------------------------------------------------------
# price_monitor.py
# --------------------------------------------------------------------------

def test_parse_price_formats():
    assert price_monitor.parse_price("$1,299.99") == 1299.99
    assert price_monitor.parse_price("₹8,499") == 8499.0
    assert price_monitor.parse_price("Price: 49.5 USD") == 49.5
    assert price_monitor.parse_price("out of stock") is None


def test_extract_price_from_html():
    html = '<html><body><span class="price">$59.95</span></body></html>'
    assert price_monitor.extract_price_from_html(html) == 59.95
    assert price_monitor.extract_price_from_html("<html></html>") is None


def test_price_drop_alert_logic(tmp_path):
    history = str(tmp_path / "history.csv")
    products = [
        {"name": "Cheap", "url": "https://x/cheap", "target_price": 100.0},
        {"name": "Expensive", "url": "https://x/expensive", "target_price": 10.0},
        {"name": "Broken", "url": "https://x/broken", "target_price": 50.0},
    ]

    def fetcher(url):
        return {
            "https://x/cheap": '<span class="price">$90.00</span>',
            "https://x/expensive": '<span class="price">$20.00</span>',
        }[url]  # "broken" raises KeyError -> treated as fetch failure

    history_rows, alerts = price_monitor.check_products(
        products, history_csv=history, fetcher=fetcher
    )
    assert len(history_rows) == 3
    # only the product below its target fires an alert
    assert len(alerts) == 1
    assert alerts[0]["name"] == "Cheap"
    assert alerts[0]["price"] == 90.0
    assert alerts[0]["drop"] == 10.0
    # history file has one row per product
    with open(history, newline="", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 3


def test_price_monitor_demo_end_to_end(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = price_monitor.main(["--demo", "--history", "history.csv"])
    assert rc == 0
    with open("history.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # mock data: headphones 69.99 < 79.99 (alert), keyboard 139.99 > 120 (no alert),
    # mouse 29.99 < 30.00 (alert) — all three rows still recorded
    assert len(rows) == 3


# --------------------------------------------------------------------------
# utils.py
# --------------------------------------------------------------------------

def test_save_csv_roundtrip(tmp_path):
    path = str(tmp_path / "nested" / "out.csv")
    rows = [{"a": "1", "b": "x"}, {"a": "2", "b": "y"}]
    utils.save_csv(rows, path)
    with open(path, newline="", encoding="utf-8") as f:
        assert list(csv.DictReader(f)) == rows


def test_save_csv_empty_rows_raises(tmp_path):
    with pytest.raises(ValueError):
        utils.save_csv([], str(tmp_path / "empty.csv"))


def test_append_csv_creates_header_once(tmp_path):
    path = str(tmp_path / "hist.csv")
    utils.append_csv({"a": "1"}, path)
    utils.append_csv({"a": "2"}, path)
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [r["a"] for r in rows] == ["1", "2"]


def test_slugify():
    assert utils.slugify("Wireless Headphones Pro!") == "wireless-headphones-pro"
    assert utils.slugify("") == "item"
