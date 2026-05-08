#!/usr/bin/env python3
"""
JobRadar -- Slug Verifier
If a company's scraper returns 0 jobs, run this to find the correct slug.

Usage:
    python verify_slugs.py                  # test all companies
    python verify_slugs.py --company Stripe # test one company
    python verify_slugs.py --fix            # auto-update companies.py with working slugs
"""

import sys
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from companies import SCRAPEABLE

HEADERS = {"User-Agent": "JobRadar/1.0"}

# Common alternate slugs to try if the primary fails
GREENHOUSE_ALTERNATES = {
    "meta": ["meta", "metacareers", "facebookapp", "facebook"],
    "block": ["block", "square", "squareinc"],
    "wise": ["wise", "transferwise"],
    "spotify": ["spotify", "spotifyjobs"],
    "realtor.com": ["realtordotcom", "move", "realtor"],
    "thepointsguy": ["thepointsguy", "tpg", "pointsguy"],
    "sofi": ["sofi", "sofitech"],
    "toast": ["toasttab", "toast"],
    "apollo.io": ["apollo", "apolloio"],
    "scale ai": ["scaleai", "scale-ai", "scale"],
    "glean": ["glean", "gleanwork"],
}


def check_greenhouse(slug: str) -> tuple[bool, int]:
    try:
        r = requests.get(
            f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
            headers=HEADERS, timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return True, len(data.get("jobs", []))
        return False, 0
    except Exception:
        return False, 0


def check_lever(slug: str) -> tuple[bool, int]:
    try:
        r = requests.get(
            f"https://api.lever.co/v0/postings/{slug}?mode=json",
            headers=HEADERS, timeout=10
        )
        if r.status_code == 200:
            return True, len(r.json())
        return False, 0
    except Exception:
        return False, 0


def check_ashby(slug: str) -> tuple[bool, int]:
    try:
        r = requests.get(
            "https://api.ashbyhq.com/posting-api/job-board",
            params={"organizationHostedJobsPageName": slug},
            headers=HEADERS, timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return True, len(data.get("jobs", []))
        return False, 0
    except Exception:
        return False, 0


def verify_company(name: str, ats: str, slug: str) -> dict:
    checkers = {"greenhouse": check_greenhouse, "lever": check_lever, "ashby": check_ashby}
    checker = checkers.get(ats)
    if not checker:
        return {"name": name, "ats": ats, "slug": slug, "status": "skipped", "jobs": 0}

    ok, count = checker(slug)
    if ok:
        return {"name": name, "ats": ats, "slug": slug, "status": "✅", "jobs": count}

    # Try alternates
    alternates = GREENHOUSE_ALTERNATES.get(name.lower(), [])
    for alt in alternates:
        ok, count = checker(alt)
        if ok:
            return {"name": name, "ats": ats, "slug": alt, "status": "✅ (fixed)", "jobs": count, "correct_slug": alt}
        time.sleep(0.2)

    return {"name": name, "ats": ats, "slug": slug, "status": "❌ needs manual fix", "jobs": 0}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", "-c", help="Test a specific company")
    parser.add_argument("--fix", action="store_true", help="Print corrected companies.py entries")
    args = parser.parse_args()

    companies = SCRAPEABLE
    if args.company:
        companies = [c for c in companies if args.company.lower() in c[0].lower()]

    print(f"\n🔍 Verifying {len(companies)} company ATS slugs...\n")
    print(f"  {'COMPANY':<20} {'ATS':<12} {'SLUG':<25} {'STATUS':<20} {'JOBS'}")
    print(f"  {'-'*85}")

    fixes_needed = []
    for (name, ats, slug, tier, work_pref) in companies:
        result = verify_company(name, ats, slug)
        print(f"  {result['name']:<20} {result['ats']:<12} {result['slug']:<25} {result['status']:<20} {result['jobs']}")
        if "❌" in result["status"]:
            fixes_needed.append(result)
        time.sleep(0.3)

    if fixes_needed:
        print(f"\n\n  ⚠️  {len(fixes_needed)} companies need manual slug fixes:")
        for r in fixes_needed:
            print(f"     * {r['name']} ({r['ats']}) -- check: https://boards.greenhouse.io/{r['slug']}/")
        print(f"\n  To find the correct slug:")
        print(f"  1. Go to the company's careers page")
        print(f"  2. Look for greenhouse.io/SLUG or lever.co/SLUG in the URL")
        print(f"  3. Update companies.py with the correct slug")
    else:
        print(f"\n  ✅ All slugs verified!")


if __name__ == "__main__":
    main()
