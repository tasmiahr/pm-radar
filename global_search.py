#!/usr/bin/env python3
# scrapers/global_search.py
#
# Searches entire ATS platforms by keyword — not just your watchlist companies.
# Greenhouse alone has 5,000+ companies. SmartRecruiters has 4,000+. Workable 20,000+.
#
# Called by run_scraper.py when --global flag is used.

import re
import time
from datetime import datetime, timezone
from typing import Optional

import requests

from scrapers.ats import (
    HEADERS, SESSION, _parse_age, _ghost_risk, _extract_salary, _build_job
)


# -----------------------------------------------------------------
# GREENHOUSE GLOBAL SEARCH
# API: https://boards-api.greenhouse.io/v1/boards
# Returns all boards (companies), then we search each for the keyword.
# Smarter: use the job search endpoint which searches across all boards.
# -----------------------------------------------------------------

def search_greenhouse(keyword: str, max_results: int = 500) -> list[dict]:
    """
    Search ALL companies on Greenhouse for a keyword.
    Uses the undocumented but stable global search endpoint.
    """
    print(f"  🌐 Greenhouse global search: '{keyword}'")
    jobs = []
    page = 1

    while len(jobs) < max_results:
        data = _safe_get(
            "https://boards-api.greenhouse.io/v1/boards/greenhouse/jobs",
            params={"q": keyword, "content": "true", "page": page, "per_page": 100}
        )

        # Greenhouse global search endpoint
        if not data:
            # Try alternate endpoint
            data = _safe_get(
                "https://api.greenhouse.io/v1/boards/jobs",
                params={"q": keyword, "per_page": 100, "page": page}
            )

        if not data or not data.get("jobs"):
            break

        batch = data["jobs"]
        if not batch:
            break

        for j in batch:
            location = (j.get("location") or {}).get("name", "") or ""
            title    = j.get("title", "") or ""
            company  = j.get("company", {}).get("name", "") if isinstance(j.get("company"), dict) else j.get("company_name", "") or "Unknown"
            remote_ok = any(kw in location.lower() or kw in title.lower()
                           for kw in ["remote", "anywhere", "distributed"])

            raw_date  = j.get("updated_at") or j.get("created_at") or ""
            posted_at = raw_date[:10] if raw_date else None
            days_old, hours_old = _parse_age(raw_date)

            description = j.get("content", "") or ""
            risk, reason = _ghost_risk(days_old, title, description)
            salary = _extract_salary(description)

            jobs.append(_build_job({
                "id":          f"gh_{j['id']}",
                "source":      "greenhouse",
                "company":     company,
                "tier":        99,  # 99 = discovered via global search, not watchlist
                "work_pref":   "unknown",
                "title":       title,
                "department":  ((j.get("departments") or [{}])[0]).get("name", ""),
                "location":    location,
                "remote_ok":   int(remote_ok),
                "url":         j.get("absolute_url", ""),
                "posted_at":   posted_at,
                "days_old":    days_old,
                "hours_old":   hours_old,
                "description": description,
                "salary":      salary,
                "ghost_risk":  risk,
                "ghost_reason":reason,
            }))

        page += 1
        # Check if there are more pages
        meta = data.get("meta", {})
        total_pages = meta.get("total_pages", 1)
        if page > total_pages:
            break
        time.sleep(0.5)

    print(f"     → {len(jobs)} jobs found")
    return jobs


# -----------------------------------------------------------------
# SMARTRECRUITERS GLOBAL SEARCH
# API: https://api.smartrecruiters.com/v1/postings?q=KEYWORD
# Public, no auth, paginated. Searches all companies on the platform.
# -----------------------------------------------------------------

def search_smartrecruiters(keyword: str, max_results: int = 500) -> list[dict]:
    """Search ALL companies on SmartRecruiters for a keyword."""
    print(f"  🌐 SmartRecruiters global search: '{keyword}'")
    jobs  = []
    offset = 0
    limit  = 100

    while len(jobs) < max_results:
        data = _safe_get(
            "https://api.smartrecruiters.com/v1/postings",
            params={
                "q":      keyword,
                "limit":  limit,
                "offset": offset,
            }
        )

        if not data or "content" not in data:
            break

        batch = data["content"]
        if not batch:
            break

        for j in batch:
            loc_obj  = j.get("location") or {}
            city     = loc_obj.get("city", "") or ""
            country  = loc_obj.get("country", "") or ""
            remote   = loc_obj.get("remote", False)
            location = ", ".join(filter(None, [city, country]))
            title    = j.get("name", "") or ""
            company  = (j.get("company") or {}).get("name", "") or "Unknown"

            remote_ok = remote or any(kw in title.lower() for kw in ["remote", "anywhere"])

            raw_date  = j.get("releasedDate") or j.get("createdOn") or ""
            posted_at = raw_date[:10] if raw_date else None
            days_old, hours_old = _parse_age(raw_date)

            description = ""
            comp_obj = j.get("compensation") or {}
            sal_struct = None
            if comp_obj.get("min") and comp_obj.get("max"):
                curr = comp_obj.get("currency", "USD")
                sal_struct = f"{curr} ${comp_obj['min']:,} - ${comp_obj['max']:,}"

            risk, reason = _ghost_risk(days_old, title, description)
            salary = _extract_salary(description, sal_struct)

            ref = j.get("ref", "") or ""
            url = ref if ref.startswith("http") else f"https://jobs.smartrecruiters.com/{j.get('id','')}"

            jobs.append(_build_job({
                "id":          f"sr_{j['id']}",
                "source":      "smartrecruiters",
                "company":     company,
                "tier":        99,
                "work_pref":   "unknown",
                "title":       title,
                "department":  (j.get("department") or {}).get("label", ""),
                "location":    location,
                "remote_ok":   int(remote_ok),
                "url":         url,
                "posted_at":   posted_at,
                "days_old":    days_old,
                "hours_old":   hours_old,
                "description": description,
                "salary":      salary,
                "ghost_risk":  risk,
                "ghost_reason":reason,
            }))

        total = data.get("totalFound", 0)
        offset += limit
        if offset >= min(total, max_results):
            break
        time.sleep(0.4)

    print(f"     → {len(jobs)} jobs found")
    return jobs


# -----------------------------------------------------------------
# WORKABLE GLOBAL SEARCH
# API: https://apply.workable.com/api/v3/jobs?query=KEYWORD
# Public endpoint, paginated. 20,000+ companies.
# -----------------------------------------------------------------

def search_workable(keyword: str, max_results: int = 500) -> list[dict]:
    """Search ALL companies on Workable for a keyword."""
    print(f"  🌐 Workable global search: '{keyword}'")
    jobs      = []
    next_page = None

    while len(jobs) < max_results:
        params = {"query": keyword, "limit": 100}
        if next_page:
            params["after"] = next_page

        data = _safe_get("https://apply.workable.com/api/v3/jobs", params=params)

        if not data or "results" not in data:
            break

        batch = data["results"]
        if not batch:
            break

        for j in batch:
            location  = j.get("location", "") or ""
            title     = j.get("title", "") or ""
            company   = j.get("company", {}).get("name", "") if isinstance(j.get("company"), dict) else "Unknown"
            remote_ok = j.get("remote", False) or "remote" in location.lower()

            raw_date  = j.get("published_on") or j.get("created_at") or ""
            posted_at = raw_date[:10] if raw_date else None
            days_old, hours_old = _parse_age(raw_date)

            description = j.get("description", "") or ""
            risk, reason = _ghost_risk(days_old, title, description)
            salary = _extract_salary(description)

            url = j.get("url") or f"https://apply.workable.com/{j.get('shortcode','')}"

            jobs.append(_build_job({
                "id":          f"wk_{j['shortcode']}",
                "source":      "workable",
                "company":     company,
                "tier":        99,
                "work_pref":   "unknown",
                "title":       title,
                "department":  j.get("department", ""),
                "location":    location,
                "remote_ok":   int(remote_ok),
                "url":         url,
                "posted_at":   posted_at,
                "days_old":    days_old,
                "hours_old":   hours_old,
                "description": description,
                "salary":      salary,
                "ghost_risk":  risk,
                "ghost_reason":reason,
            }))

        next_page = data.get("nextPage")
        if not next_page or len(jobs) >= max_results:
            break
        time.sleep(0.4)

    print(f"     → {len(jobs)} jobs found")
    return jobs


# -----------------------------------------------------------------
# ASHBY GLOBAL SEARCH
# API: https://api.ashbyhq.com/posting-api/job-board/search
# Searches across all Ashby boards.
# -----------------------------------------------------------------

def search_ashby(keyword: str, max_results: int = 300) -> list[dict]:
    """Search ALL companies on Ashby for a keyword."""
    print(f"  🌐 Ashby global search: '{keyword}'")

    data = _safe_get(
        "https://api.ashbyhq.com/posting-api/job-board/search",
        params={"query": keyword, "limit": max_results}
    )

    if not data or "results" not in data:
        # Try alternate endpoint
        data = _safe_get(
            "https://api.ashbyhq.com/posting-api/job-board",
            params={"query": keyword}
        )

    if not data:
        print(f"     → Ashby global search not available (company-specific only)")
        return []

    raw_jobs = data.get("results") or data.get("jobs") or []
    jobs = []

    for j in raw_jobs:
        location  = j.get("location", "") or ""
        title     = j.get("title", "") or ""
        company   = j.get("organizationName", "") or j.get("company", "") or "Unknown"
        remote_ok = j.get("isRemote", False) or "remote" in location.lower()

        raw_date  = (j.get("publishedDate", "") or "")[:10]
        days_old, hours_old = _parse_age(raw_date + "T00:00:00+00:00" if raw_date else None)

        description = j.get("descriptionSocial", "") or ""
        risk, reason = _ghost_risk(days_old, title, description)
        salary = _extract_salary(description)

        jobs.append(_build_job({
            "id":          f"ab_{j['id']}",
            "source":      "ashby",
            "company":     company,
            "tier":        99,
            "work_pref":   "unknown",
            "title":       title,
            "department":  j.get("department", ""),
            "location":    location,
            "remote_ok":   int(remote_ok),
            "url":         j.get("jobUrl", ""),
            "posted_at":   raw_date or None,
            "days_old":    days_old,
            "hours_old":   hours_old,
            "description": description,
            "salary":      salary,
            "ghost_risk":  risk,
            "ghost_reason":reason,
        }))

    print(f"     → {len(jobs)} jobs found")
    return jobs


# -----------------------------------------------------------------
# GLOBAL SEARCH RUNNER
# Called by run_scraper.py with --global flag
# -----------------------------------------------------------------

def search_all_platforms(
    keyword: str,
    max_per_platform: int = 300,
    platforms: list = None
) -> list[dict]:
    """
    Search across all ATS platforms for a keyword.
    Returns deduplicated list of jobs from all platforms.
    """
    if platforms is None:
        platforms = ["greenhouse", "smartrecruiters", "workable"]
        # ashby global search endpoint may not exist — try but don't rely on it

    all_jobs = []
    seen_ids = set()

    searchers = {
        "greenhouse":      lambda: search_greenhouse(keyword, max_per_platform),
        "smartrecruiters": lambda: search_smartrecruiters(keyword, max_per_platform),
        "workable":        lambda: search_workable(keyword, max_per_platform),
        "ashby":           lambda: search_ashby(keyword, max_per_platform),
    }

    for platform in platforms:
        if platform not in searchers:
            continue
        try:
            jobs = searchers[platform]()
            new = 0
            for j in jobs:
                if j["id"] not in seen_ids:
                    seen_ids.add(j["id"])
                    all_jobs.append(j)
                    new += 1
            if new != len(jobs):
                print(f"     ({len(jobs)-new} duplicates removed)")
        except Exception as e:
            print(f"  ❌ {platform} global search failed: {e}")
        time.sleep(1)

    return all_jobs


def _safe_get(url, params=None, retries=2):
    for attempt in range(retries + 1):
        try:
            r = SESSION.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(10)
        except Exception as e:
            if attempt == retries:
                return None
    return None
