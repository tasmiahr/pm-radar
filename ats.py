"""
scrapers/ats.py -- Greenhouse, Lever, Ashby API scrapers
------------------------------------------------------
All three use official public JSON endpoints -- no browser, no login.
Called by run_scraper.py. You shouldn't need to edit this file.
"""

import requests
import time
from datetime import datetime, timezone
from typing import Optional

HEADERS = {
    "User-Agent": "JobRadar/1.0 (personal job search tool)",
    "Accept": "application/json",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# -----------------------------------------------------------------
# SHARED HELPERS
# -----------------------------------------------------------------

def _parse_age(date_str: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """
    Given an ISO 8601 date/datetime string, return (days_old, hours_old).
    Both are None if the date is missing or unparseable.
    """
    if not date_str:
        return None, None
    try:
        # Normalize: handle both "2026-04-01" and "2026-04-01T12:00:00Z"
        if "T" not in date_str:
            date_str = date_str + "T00:00:00+00:00"
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        days  = delta.days
        hours = int(delta.total_seconds() // 3600)
        return days, hours
    except Exception:
        return None, None


def _ghost_risk(days_old: Optional[int], title: str, description: str) -> tuple[str, str]:
    """
    Heuristic legitimacy check. Returns (risk_level, reason).
    risk_level: "low" | "medium" | "high"
    """
    reasons = []

    if days_old is not None:
        if days_old > 90:
            return "high", f"posted {days_old}d ago (>90d = almost certainly ghost)"
        if days_old > 60:
            reasons.append(f"posted {days_old}d ago (>60d = likely ghost)")

    vague = ["various roles", "general application", "talent community", "future opportunities", "pipeline"]
    if any(v in title.lower() for v in vague):
        reasons.append("vague/pipeline title")

    if description and len(description.strip()) < 200:
        reasons.append("very short description (<200 chars)")

    if not reasons:
        return "low", "fresh posting from official ATS"
    if len(reasons) == 1 and (days_old is None or days_old <= 60):
        return "medium", reasons[0]
    return "high", "; ".join(reasons)


def _safe_get(url: str, params: dict = None, retries: int = 2) -> Optional[dict | list]:
    """GET with retry + polite error handling."""
    for attempt in range(retries + 1):
        try:
            r = SESSION.get(url, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(5)
        except Exception as e:
            if attempt == retries:
                print(f"  ⚠️  Request failed [{url}]: {e}")
    return None


def _build_job(base: dict) -> dict:
    """Shared job dict structure -- keeps all scrapers consistent."""
    return {
        "id":          base["id"],
        "source":      base["source"],
        "company":     base["company"],
        "tier":        base["tier"],
        "work_pref":   base["work_pref"],
        "title":       base.get("title", ""),
        "department":  base.get("department", ""),
        "location":    base.get("location", ""),
        "remote_ok":   base.get("remote_ok", 0),
        "url":         base.get("url", ""),
        "posted_at":   base.get("posted_at"),
        "days_old":    base.get("days_old"),
        "hours_old":   base.get("hours_old"),
        "description": (base.get("description") or "")[:3000],
        "ghost_risk":  base.get("ghost_risk", "low"),
        "ghost_reason":base.get("ghost_reason", ""),
    }


# -----------------------------------------------------------------
# GREENHOUSE
# Official API docs: https://developers.greenhouse.io/job-board.html
# URL pattern: boards-api.greenhouse.io/v1/boards/{slug}/jobs
# -----------------------------------------------------------------

def scrape_greenhouse(slug: str, company: str, tier: int, work_pref: str) -> list[dict]:
    data = _safe_get(
        f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
        params={"content": "true"}
    )
    if not data or "jobs" not in data:
        print(f"  ❌ {company}: Greenhouse returned no jobs (slug='{slug}')")
        return []

    jobs = []
    for j in data["jobs"]:
        location = (j.get("location") or {}).get("name", "") or ""
        title    = j.get("title", "")

        remote_ok = any(
            kw in location.lower() or kw in title.lower()
            for kw in ["remote", "anywhere", "distributed"]
        )

        # Greenhouse gives updated_at (ISO string), fall back to created_at
        raw_date = j.get("updated_at") or j.get("created_at") or ""
        posted_at = raw_date[:10] if raw_date else None   # "YYYY-MM-DD"
        days_old, hours_old = _parse_age(raw_date)

        description = j.get("content", "") or ""
        risk, reason = _ghost_risk(days_old, title, description)

        jobs.append(_build_job({
            "id":          f"gh_{j['id']}",
            "source":      "greenhouse",
            "company":     company,
            "tier":        tier,
            "work_pref":   work_pref,
            "title":       title,
            "department":  ((j.get("departments") or [{}])[0]).get("name", ""),
            "location":    location,
            "remote_ok":   int(remote_ok),
            "url":         j.get("absolute_url", ""),
            "posted_at":   posted_at,
            "days_old":    days_old,
            "hours_old":   hours_old,
            "description": description,
            "ghost_risk":  risk,
            "ghost_reason":reason,
        }))
    return jobs


# -----------------------------------------------------------------
# LEVER
# Official API docs: https://hire.lever.co/developer/postings
# URL pattern: api.lever.co/v0/postings/{slug}
# Note: timestamps are Unix milliseconds, not ISO strings
# -----------------------------------------------------------------

def scrape_lever(slug: str, company: str, tier: int, work_pref: str) -> list[dict]:
    data = _safe_get(
        f"https://api.lever.co/v0/postings/{slug}",
        params={"mode": "json"}
    )
    if not isinstance(data, list):
        print(f"  ❌ {company}: Lever returned no jobs (slug='{slug}')")
        return []

    jobs = []
    for j in data:
        cats       = j.get("categories") or {}
        location   = cats.get("location", "") or ""
        commitment = cats.get("commitment", "") or ""
        title      = j.get("text", "")

        remote_ok = any(
            kw in (location + " " + commitment).lower()
            for kw in ["remote", "anywhere", "distributed"]
        )

        # Lever: createdAt is Unix timestamp in milliseconds
        created_ms = j.get("createdAt")
        if created_ms:
            created_dt = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
            posted_at  = created_dt.strftime("%Y-%m-%d")
            now        = datetime.now(timezone.utc)
            delta      = now - created_dt
            days_old   = delta.days
            hours_old  = int(delta.total_seconds() // 3600)
        else:
            posted_at = days_old = hours_old = None

        description = j.get("descriptionPlain", "") or j.get("description", "") or ""
        risk, reason = _ghost_risk(days_old, title, description)

        jobs.append(_build_job({
            "id":          f"lv_{j['id']}",
            "source":      "lever",
            "company":     company,
            "tier":        tier,
            "work_pref":   work_pref,
            "title":       title,
            "department":  cats.get("department", ""),
            "location":    location,
            "remote_ok":   int(remote_ok),
            "url":         j.get("hostedUrl", ""),
            "posted_at":   posted_at,
            "days_old":    days_old,
            "hours_old":   hours_old,
            "description": description,
            "ghost_risk":  risk,
            "ghost_reason":reason,
        }))
    return jobs


# -----------------------------------------------------------------
# ASHBY
# API: api.ashbyhq.com/posting-api/job-board
# URL pattern: jobs.ashbyhq.com/{slug}
# -----------------------------------------------------------------

def scrape_ashby(slug: str, company: str, tier: int, work_pref: str) -> list[dict]:
    data = _safe_get(
        "https://api.ashbyhq.com/posting-api/job-board",
        params={"organizationHostedJobsPageName": slug}
    )
    if not data or "jobs" not in data:
        print(f"  ❌ {company}: Ashby returned no jobs (slug='{slug}')")
        return []

    jobs = []
    for j in data["jobs"]:
        location  = j.get("location", "") or ""
        title     = j.get("title", "")
        remote_ok = j.get("isRemote", False) or "remote" in location.lower()

        raw_date  = j.get("publishedDate", "") or ""
        posted_at = raw_date[:10] if raw_date else None
        days_old, hours_old = _parse_age(raw_date)

        description = j.get("descriptionSocial", "") or ""
        risk, reason = _ghost_risk(days_old, title, description)

        jobs.append(_build_job({
            "id":          f"ab_{j['id']}",
            "source":      "ashby",
            "company":     company,
            "tier":        tier,
            "work_pref":   work_pref,
            "title":       title,
            "department":  j.get("department", ""),
            "location":    location,
            "remote_ok":   int(remote_ok),
            "url":         j.get("jobUrl", ""),
            "posted_at":   posted_at,
            "days_old":    days_old,
            "hours_old":   hours_old,
            "description": description,
            "ghost_risk":  risk,
            "ghost_reason":reason,
        }))
    return jobs


# -----------------------------------------------------------------
# ROUTER -- called by run_scraper.py
# -----------------------------------------------------------------

def scrape_company(name: str, ats: str, slug: str, tier: int, work_pref: str) -> list[dict]:
    if ats == "greenhouse":
        return scrape_greenhouse(slug, name, tier, work_pref)
    if ats == "lever":
        return scrape_lever(slug, name, tier, work_pref)
    if ats == "ashby":
        return scrape_ashby(slug, name, tier, work_pref)
    return []
