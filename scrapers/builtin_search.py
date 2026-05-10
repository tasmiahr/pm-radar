#!/usr/bin/env python3
# scrapers/builtin_search.py
#
# Scrapes Built In Austin job listings from HTML.
# Pages are server-side rendered so we parse the HTML directly.
# No API key needed. Polite crawling with delays.
#
# URL pattern: https://www.builtinaustin.com/jobs/product?page=N
# Also supports: builtinboston.com, builtinnyc.com, builtinsf.com, etc.

import re
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def _parse_age_from_text(text: str):
    """Parse '2 Days Ago', 'Yesterday', '18 Hours Ago' into (days_old, hours_old)."""
    if not text:
        return None, None
    t = text.lower().strip()
    if "yesterday" in t:
        return 1, 24
    if "hour" in t:
        m = re.search(r"(\d+)\s*hour", t)
        h = int(m.group(1)) if m else 1
        return h // 24, h
    if "day" in t:
        m = re.search(r"(\d+)\s*day", t)
        d = int(m.group(1)) if m else 1
        return d, d * 24
    if "week" in t:
        m = re.search(r"(\d+)\s*week", t)
        d = (int(m.group(1)) if m else 1) * 7
        return d, d * 24
    if "month" in t:
        m = re.search(r"(\d+)\s*month", t)
        d = (int(m.group(1)) if m else 1) * 30
        return d, d * 24
    # "reposted X days ago" — treat same as posted
    return None, None


def _parse_salary(text: str) -> Optional[str]:
    """Extract salary from text like '159K-246K Annually' or '$75K-$205K'."""
    if not text:
        return None
    m = re.search(r'\$?(\d+K?[\d,]*)\s*[-–]\s*\$?(\d+K?[\d,]*)\s*(annually|per year|/yr|hourly)?',
                  text, re.IGNORECASE)
    if m:
        lo, hi, interval = m.group(1), m.group(2), m.group(3) or ""
        suffix = "/yr" if "annual" in interval.lower() or "year" in interval.lower() else \
                 "/hr" if "hour" in interval.lower() else ""
        return f"${lo} - ${hi}{suffix}".replace("K", "K")
    return None


def scrape_builtin(
    category: str = "product",
    city_slug: str = "austin",
    max_pages: int = 5,
) -> list[dict]:
    """
    Scrape Built In jobs for a category and city.

    Args:
        category:  URL path segment e.g. "product", "software-engineer", "data"
        city_slug: "austin", "boston", "nyc", "sf", "chicago", "seattle", "la", "colorado"
        max_pages: max pages to scrape (each page has ~20 jobs)
    """
    domain_map = {
        "austin":   "www.builtinaustin.com",
        "boston":   "www.builtinboston.com",
        "nyc":      "www.builtinnyc.com",
        "sf":       "www.builtinsf.com",
        "chicago":  "www.builtinchicago.org",
        "seattle":  "www.builtinseattle.com",
        "la":       "www.builtinla.com",
        "colorado": "www.builtincolorado.com",
    }
    domain = domain_map.get(city_slug, f"www.builtin{city_slug}.com")
    base_url = f"https://{domain}/jobs/{category}"

    print(f"  🌐 Built In {city_slug.title()} — /jobs/{category}")

    all_jobs = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        url = base_url if page == 1 else f"{base_url}?page={page}"

        try:
            r = SESSION.get(url, timeout=20)
            if r.status_code == 404:
                break
            if r.status_code != 200:
                print(f"     HTTP {r.status_code} on page {page}")
                break
        except Exception as e:
            print(f"     Error on page {page}: {e}")
            break

        soup = BeautifulSoup(r.text, "html.parser")

        # Each job is in an <article> or a <div> with a job link
        # Built In renders each job as a section with company name, title, date, location
        jobs_on_page = 0

        # Find all job links — format: /job/{slug}/{id}
        job_links = soup.find_all("a", href=re.compile(r"/job/[^/]+/\d+"))

        # Also find via heading tags within job cards
        for link in job_links:
            href = link.get("href", "")
            if not href:
                continue

            # Extract job ID from URL
            m = re.search(r"/job/[^/]+/(\d+)", href)
            if not m:
                continue
            job_id = m.group(1)
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            # Job title is the link text (if it's a heading link)
            title = link.get_text(strip=True)
            if len(title) < 5 or len(title) > 200:
                continue

            # Walk up to find the card container
            card = link
            for _ in range(6):
                card = card.parent
                if card is None:
                    break

            # Extract company name — look for company link nearby
            company = ""
            if card:
                company_links = card.find_all("a", href=re.compile(r"/company/"))
                if company_links:
                    company = company_links[0].get_text(strip=True)

            if not company:
                continue

            # Extract text content for mining other fields
            card_text = card.get_text(" ", strip=True) if card else ""

            # Location
            location = "Austin, TX"  # default for builtinaustin
            loc_m = re.search(
                r"(Remote|Hybrid|In-Office)[^•\n]*?([A-Z][a-z]+ ?,?\s*[A-Z]{2})",
                card_text
            )
            if loc_m:
                location = f"{loc_m.group(1)} — {loc_m.group(2)}"

            # Work type
            remote_ok = False
            if "remote" in card_text.lower():
                remote_ok = True

            # Salary
            salary = None
            sal_m = re.search(r"\$?[\d,]+K?\s*[-–]\s*\$?[\d,]+K?\s*(?:Annually|Per Year|Hourly)?",
                              card_text, re.IGNORECASE)
            if sal_m:
                salary = _parse_salary(sal_m.group(0))

            # Date posted
            days_old, hours_old = None, None
            posted_text = ""
            date_m = re.search(
                r"(\d+\s*(?:Hours?|Days?|Weeks?|Months?)\s*Ago|Yesterday|Reposted[^•\n]*?(\d+\s*(?:Hours?|Days?|Weeks?)\s*Ago|Yesterday))",
                card_text, re.IGNORECASE
            )
            if date_m:
                posted_text = date_m.group(0)
                # If reposted, use the inner date
                inner = re.search(r"(\d+\s*(?:Hours?|Days?|Weeks?)\s*Ago|Yesterday)", posted_text, re.IGNORECASE)
                parse_text = inner.group(1) if inner else posted_text
                days_old, hours_old = _parse_age_from_text(parse_text)

            # Ghost risk
            risk = "low"
            reason = "Built In Austin listing"
            if days_old is not None and days_old > 60:
                risk = "high"
                reason = f"{days_old}d old"
            elif days_old is not None and days_old > 30:
                risk = "medium"
                reason = f"{days_old}d old"

            url_full = f"https://{domain}{href}"

            all_jobs.append({
                "id":          f"bi_{job_id}",
                "source":      "builtin",
                "company":     company,
                "tier":        99,
                "work_pref":   "remote" if remote_ok else "unknown",
                "title":       title,
                "department":  "",
                "location":    location,
                "remote_ok":   int(remote_ok),
                "url":         url_full,
                "posted_at":   None,
                "days_old":    days_old,
                "hours_old":   hours_old,
                "description": "",
                "salary":      salary,
                "ghost_risk":  risk,
                "ghost_reason":reason,
            })
            jobs_on_page += 1

        print(f"     Page {page}: {jobs_on_page} jobs")

        if jobs_on_page == 0:
            break

        # Check if there's a next page
        next_link = soup.find("a", href=re.compile(rf"/jobs/{category}\?page={page+1}"))
        if not next_link and page > 1:
            break

        time.sleep(2)  # polite delay between pages

    print(f"     → {len(all_jobs)} total Built In jobs found")
    return all_jobs
