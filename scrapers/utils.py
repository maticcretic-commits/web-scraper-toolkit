"""Shared helpers: polite fetching, retries, user-agent rotation, CSV export."""

import csv
import os
import random
import time
from typing import Dict, Iterable, List, Optional

import requests

USER_AGENTS = [
    # A small rotation of common desktop browser user agents.
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]


def fetch(
    url: str,
    *,
    retries: int = 3,
    backoff: float = 1.5,
    delay: float = 1.0,
    timeout: float = 20.0,
    session: Optional[requests.Session] = None,
) -> str:
    """Fetch a page politely: random UA, retry with backoff, rate-limited delay.

    Raises the last exception if all retries fail.
    """
    sess = session or requests.Session()
    last_error: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = sess.get(
                url,
                headers={"User-Agent": random.choice(USER_AGENTS)},
                timeout=timeout,
            )
            resp.raise_for_status()
            time.sleep(delay)  # polite pause between requests
            return resp.text
        except (requests.RequestException, OSError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    assert last_error is not None
    raise last_error


def save_csv(
    rows: Iterable[Dict[str, str]],
    path: str,
    fieldnames: Optional[List[str]] = None,
) -> str:
    """Write a list of dicts to CSV. Returns the file path."""
    rows = list(rows)
    if not rows:
        raise ValueError("No rows to write")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fieldnames = fieldnames or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def append_csv(
    row: Dict[str, str],
    path: str,
    fieldnames: Optional[List[str]] = None,
) -> str:
    """Append a single dict row to a CSV, creating the header if needed."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    exists = os.path.exists(path) and os.path.getsize(path) > 0
    fieldnames = fieldnames or list(row.keys())
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow(row)
    return path


def slugify(value: str) -> str:
    """Make a filesystem-safe slug from a product name."""
    slug = "".join(c.lower() if c.isalnum() else "-" for c in value)
    slug = "-".join(filter(None, slug.split("-")))
    return slug[:80] or "item"
