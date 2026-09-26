"""Job-listings scraper.

Scrapes job cards (title, company, location, salary, posted date) from a
job-board-style HTML layout into CSV.

Demo mode runs entirely offline against bundled sample HTML:

    python -m scrapers.job_listings --demo
"""

import argparse
import sys
from typing import Dict, List

from bs4 import BeautifulSoup

from scrapers.utils import fetch, save_csv

SAMPLE_HTML = """\
<html><body>
<div class="jobs">
  <article class="job-card">
    <h2 class="job-title">Senior Python Developer</h2>
    <div class="company">TechNova Solutions</div>
    <span class="location">Remote</span>
    <span class="salary">$120k - $150k</span>
    <time class="posted-date" datetime="2026-09-24">2 days ago</time>
  </article>
  <article class="job-card">
    <h2 class="job-title">Data Analyst (SQL/Power BI)</h2>
    <div class="company">Bright Insights Ltd</div>
    <span class="location">Bengaluru, India</span>
    <span class="salary">₹8–12 LPA</span>
    <time class="posted-date" datetime="2026-09-20">6 days ago</time>
  </article>
  <article class="job-card">
    <h2 class="job-title">Web Scraping Specialist</h2>
    <div class="company">DataWorks</div>
    <span class="location">Remote</span>
    <span class="salary">$40/hr</span>
    <time class="posted-date" datetime="2026-09-26">today</time>
  </article>
</div>
</body></html>
"""

FIELDNAMES = ["title", "company", "location", "salary", "posted_date"]


def parse_jobs(html: str) -> List[Dict[str, str]]:
    """Parse job cards from job-board-style HTML."""
    soup = BeautifulSoup(html, "lxml")
    jobs = []
    for card in soup.select(".job-card"):
        title_el = card.select_one(".job-title")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue
        company_el = card.select_one(".company")
        location_el = card.select_one(".location")
        salary_el = card.select_one(".salary")
        posted_el = card.select_one(".posted-date")
        jobs.append(
            {
                "title": title,
                "company": company_el.get_text(strip=True) if company_el else "",
                "location": location_el.get_text(strip=True) if location_el else "",
                "salary": salary_el.get_text(strip=True) if salary_el else "",
                "posted_date": posted_el.get_text(strip=True) if posted_el else "",
            }
        )
    return jobs


def scrape_jobs(url: str, out_csv: str, *, demo: bool = False) -> List[Dict[str, str]]:
    """Full pipeline: fetch -> parse -> save CSV."""
    html = SAMPLE_HTML if demo else fetch(url)
    jobs = parse_jobs(html)
    save_csv(jobs, out_csv, fieldnames=FIELDNAMES)
    return jobs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Job-listings scraper")
    parser.add_argument("--url", default="", help="Job board search results URL")
    parser.add_argument("--out", default="output/job_listings.csv")
    parser.add_argument("--demo", action="store_true", help="Run against bundled sample HTML")
    args = parser.parse_args(argv)
    if not args.demo and not args.url:
        parser.error("--url is required unless --demo is used")
    jobs = scrape_jobs(args.url, args.out, demo=args.demo)
    print(f"Collected {len(jobs)} job listings -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
