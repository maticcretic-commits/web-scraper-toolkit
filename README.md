# Web Scraper Toolkit

A practical Python toolkit for the most common freelance data-collection jobs:
scrape marketplace products (with images), scrape job listings, and monitor
prices over time. Everything runs from the command line and outputs clean CSVs
ready to hand to a client or load into Google Sheets.

## Problem it solves

Freelance clients constantly need structured data they can't easily get by hand:
competitor product catalogs, bulk job postings, or daily price tracking. This
toolkit turns those requests into repeatable, one-command scrapers with polite
fetching (retries, user-agent rotation, rate limiting) built in.

## Features

- **Marketplace collector** (`scrapers/marketplace.py`) — scrapes product cards
  (name, price, image URL, rating), downloads product images, writes CSV.
- **Job-listings scraper** (`scrapers/job_listings.py`) — scrapes job cards
  (title, company, location, salary, posted date) into CSV.
- **Price monitor** (`scrapers/price_monitor.py`) — tracks product prices over
  time, appends to a CSV history, and alerts when a price drops below a target.
- **Polite by default** — retries with backoff, rotating user agents, and a
  configurable delay between requests (`scrapers/utils.py`).
- **Demo mode everywhere** — every scraper runs offline against bundled sample
  HTML (`--demo`), so you can try the full pipeline with zero setup.

## Tech stack

Python 3 · `requests` · `beautifulsoup4` + `lxml` · `pandas` (for downstream
analysis) · `pytest` for tests.

## Quickstart

```bash
pip install -r requirements.txt

# Marketplace collector (demo mode — no network needed)
python -m scrapers.marketplace --demo

# Job listings (demo mode)
python -m scrapers.job_listings --demo

# Price monitor (demo mode — mock prices, alerts on drops)
python -m scrapers.price_monitor --demo

# Run the tests
python -m pytest tests/ -q
```

Live scraping (example):

```bash
python -m scrapers.marketplace --url https://example-shop.com/listings \
    --out output/products.csv --images output/images
python -m scrapers.job_listings --url https://example-jobs.com/search?q=python \
    --out output/jobs.csv
```

> Please respect each site's Terms of Service and `robots.txt`, and keep request
> rates low. The toolkit is built for polite, low-volume data collection.

## Sample output

`marketplace_products.csv`:

| name | price | image_url | rating | image_file |
|---|---|---|---|---|
| Wireless Headphones Pro | $79.99 | https://example.com/img/headphones.jpg | 4.5 | wireless-headphones-pro.jpg |
| Mechanical Keyboard RGB | $129.50 | https://example.com/img/keyboard.jpg | 4.8 | mechanical-keyboard-rgb.jpg |
| Ergonomic Wireless Mouse | $34.99 | https://example.com/img/mouse.jpg | 4.2 | ergonomic-wireless-mouse.jpg |

`job_listings.csv`:

| title | company | location | salary | posted_date |
|---|---|---|---|---|
| Senior Python Developer | TechNova Solutions | Remote | $120k - $150k | 2 days ago |
| Data Analyst (SQL/Power BI) | Bright Insights Ltd | Bengaluru, India | ₹8–12 LPA | 6 days ago |
| Web Scraping Specialist | DataWorks | Remote | $40/hr | today |

`price_history.csv` (one row appended per check):

| timestamp | product | url | price | target_price |
|---|---|---|---|---|
| 2026-09-26T06:00:00Z | Wireless Headphones Pro | https://example.com/p/headphones | 69.99 | 79.99 |

## Project layout

```
web-scraper-toolkit/
├── scrapers/
│   ├── utils.py          # fetch w/ retries + UA rotation + rate limit, CSV helpers
│   ├── marketplace.py    # product + image collector
│   ├── job_listings.py   # job-board scraper
│   └── price_monitor.py  # price tracker with drop alerts
├── tests/
│   └── test_scrapers.py  # offline unit tests (mocked HTML, no network)
├── requirements.txt
└── .gitignore
```

## License

MIT — use it in your own client projects freely.
