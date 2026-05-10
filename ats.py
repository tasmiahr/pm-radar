
import re
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
# SALARY EXTRACTION
# Tries structured API fields first, then regex on description text
# -----------------------------------------------------------------

# Patterns that match salary ranges like:
#   $150,000 - $200,000  |  $150k-$200k  |  150,000 to 200,000
#   USD 150000-200000     |  Base pay: $175K  |  $175,000/year
_SALARY_RE = re.compile(
    r'\$[\d,]+[kK]?\s*(?:[-–—to]+\s*\$[\d,]+[kK]?)?'
    r'|USD\s*[\d,]+[kK]?\s*(?:[-–—to]+\s*[\d,]+[kK]?)?'
    r'|\b[\d,]{5,}\s*(?:[-–—to]+\s*[\d,]{5,})?\s*(?:USD|per year|annually|\/yr)',
    re.IGNORECASE
)

def _extract_salary(description: str, structured: str = None) -> Optional[str]:
    """
    Return a clean salary string or None.
    structured = value from ATS API salary field if available.
    Falls back to regex on description.
    """
    # 1. Use structured field if ATS provides it
    if structured and str(structured).strip():
        val = str(structured).strip()
        if len(val) > 3:
            return val

    # 2. Regex scan of description
    if not description:
        return None
    matches = _SALARY_RE.findall(description)
    if not matches:
        return None

    # Pick the longest/most specific match
    best = max(matches, key=len).strip()
    # Clean up whitespace
    best = re.sub(r'\s+', ' ', best)
    # Cap length to avoid grabbing garbage
    if len(best) > 60:
        return None
    return best


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
                print(f"  ⚠️  Rate limited (429) [{url}] — waiting 10s")
                time.sleep(10)
                continue
            if r.status_code == 403:
                print(f"  ⚠️  Blocked (403) [{url}] — {r.text[:100]}")
                return None
            if r.status_code >= 500:
                print(f"  ⚠️  Server error ({r.status_code}) [{url}]")
                time.sleep(2)
                continue
            print(f"  ⚠️  HTTP {r.status_code} [{url}]")
            return None
        except Exception as e:
            if attempt == retries:
                print(f"  ⚠️  Request failed [{url}]: {e}")
            else:
                time.sleep(1)
    return None


def _build_job(base: dict) -> dict:
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
        "salary":      base.get("salary"),
        "ghost_risk":  base.get("ghost_risk", "low"),
        "ghost_reason":base.get("ghost_reason", ""),
    }


# -----------------------------------------------------------------
# GREENHOUSE
# Official API docs: https://developers.greenhouse.io/job-board.html
# URL pattern: boards-api.greenhouse.io/v1/boards/{slug}/jobs
# -----------------------------------------------------------------

def scrape_greenhouse(slug: str, company: str, tier: int, work_pref: str) -> list[dict]:
    # Try both API endpoints - same API, boards-api.greenhouse.io works for both
    # old URL: boards.greenhouse.io/slug
    # new URL: job-boards.greenhouse.io/slug  (same API token, same endpoint)
    data = _safe_get(
        f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
        params={"content": "true", "pay_transparency": "true"}
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

        # Greenhouse pay transparency: pay_input_ranges field
        structured_sal = None
        pay_ranges = j.get("pay_input_ranges") or []
        if pay_ranges:
            r = pay_ranges[0]
            lo = r.get("min_cents", 0) or 0
            hi = r.get("max_cents", 0) or 0
            curr = r.get("currency_type", "USD")
            if lo and hi:
                structured_sal = f"{curr} ${lo//100:,} - ${hi//100:,}"
            elif lo:
                structured_sal = f"{curr} ${lo//100:,}+"

        salary = _extract_salary(description, structured_sal)

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
            "salary":      salary,
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

        # Lever exposes salaryRange on some listings
        sal_range = j.get("salaryRange") or {}
        if sal_range and sal_range.get("min"):
            curr = sal_range.get("currency", "USD")
            lo   = sal_range.get("min", 0)
            hi   = sal_range.get("max", 0)
            interval = sal_range.get("interval", "")
            if hi and hi != lo:
                structured_sal = f"{curr} ${lo:,} - ${hi:,}{' /'+interval if interval else ''}"
            else:
                structured_sal = f"{curr} ${lo:,}+"
        else:
            structured_sal = None

        salary = _extract_salary(description, structured_sal)

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
            "salary":      salary,
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
        params={"organizationHostedJobsPageName": slug, "includeCompensation": "true"}
    )
    if not data or "jobs" not in data:
        # Try alternate Ashby endpoint
        data = _safe_get(
            f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
            params={"includeCompensation": "true"}
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

        # Get best available description
        description = (
            j.get("descriptionPlain") or
            j.get("description") or
            j.get("descriptionSocial") or
            ""
        )

        # Salary from Ashby compensation fields
        comp = j.get("compensation") or {}
        sal_struct = None
        if comp:
            lo = comp.get("minValue") or comp.get("min")
            hi = comp.get("maxValue") or comp.get("max")
            curr = comp.get("currencyCode", "USD")
            interval = comp.get("interval", "")
            if lo and hi:
                interval_label = {"YEAR": "/yr", "MONTH": "/mo", "HOUR": "/hr"}.get(interval, "")
                sal_struct = f"{curr} ${int(lo):,} - ${int(hi):,}{interval_label}"

        risk, reason = _ghost_risk(days_old, title, description)
        salary = _extract_salary(description, sal_struct)

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
            "salary":      salary,
            "ghost_risk":  risk,
            "ghost_reason":reason,
        }))
    return jobs



# -----------------------------------------------------------------
# SMARTRECRUITERS
# Public API: api.smartrecruiters.com/v1/companies/{slug}/postings
# URL pattern: careers.smartrecruiters.com/{slug}
# No auth required for public postings
# -----------------------------------------------------------------

def scrape_smartrecruiters(slug: str, company: str, tier: int, work_pref: str) -> list[dict]:
    all_jobs = []
    offset   = 0
    limit    = 100

    while True:
        data = _safe_get(
            f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
            params={"limit": limit, "offset": offset}
        )
        if not data or "content" not in data:
            if offset == 0:
                print(f"  ❌ {company}: SmartRecruiters returned no jobs (slug='{slug}')")
            break

        batch = data["content"]
        if not batch:
            break

        for j in batch:
            location_obj = j.get("location") or {}
            city    = location_obj.get("city", "") or ""
            country = location_obj.get("country", "") or ""
            remote  = location_obj.get("remote", False)
            location = ", ".join(filter(None, [city, country]))

            remote_ok = remote or any(kw in (j.get("name","") or "").lower()
                                      for kw in ["remote", "anywhere"])

            raw_date  = j.get("releasedDate") or j.get("createdOn") or ""
            posted_at = raw_date[:10] if raw_date else None
            days_old, hours_old = _parse_age(raw_date)

            title       = j.get("name", "")
            description = j.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text", "") or ""
            risk, reason = _ghost_risk(days_old, title, description)

            # SmartRecruiters exposes compensation on some listings
            comp_obj = j.get("compensation") or {}
            if comp_obj.get("min") and comp_obj.get("max"):
                curr = comp_obj.get("currency", "USD")
                lo   = comp_obj["min"]
                hi   = comp_obj["max"]
                sal_struct = f"{curr} ${lo:,} - ${hi:,}"
            else:
                sal_struct = None
            salary = _extract_salary(description, sal_struct)

            ref = j.get("ref", "") or ""
            url = ref if ref.startswith("http") else f"https://careers.smartrecruiters.com/{slug}/{j.get('id','')}"

            all_jobs.append(_build_job({
                "id":          f"sr_{j['id']}",
                "source":      "smartrecruiters",
                "company":     company,
                "tier":        tier,
                "work_pref":   work_pref,
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

        # Paginate if more pages exist
        total = data.get("totalFound", 0)
        offset += limit
        if offset >= total:
            break
        time.sleep(0.3)

    return all_jobs


# -----------------------------------------------------------------
# WORKABLE
# Public API: apply.workable.com/api/v3/accounts/{slug}/jobs
# URL pattern: apply.workable.com/{slug}
# -----------------------------------------------------------------

def scrape_workable(slug: str, company: str, tier: int, work_pref: str) -> list[dict]:
    all_jobs = []
    next_page = None
    tried_v1 = False

    while True:
        params = {"limit": 100, "details": "true"}
        if next_page:
            params["after"] = next_page

        data = _safe_get(
            f"https://apply.workable.com/api/v3/accounts/{slug}/jobs",
            params=params
        )

        # Fall back to v1 widget endpoint if v3 fails
        if not data and not tried_v1 and not all_jobs:
            tried_v1 = True
            data = _safe_get(
                f"https://apply.workable.com/api/v1/widget/accounts/{slug}/jobs",
                params={"details": "true"}
            )

        if not data or "results" not in data:
            if not all_jobs:
                print(f"  ❌ {company}: Workable returned no jobs (slug='{slug}')")
            break

        for j in data["results"]:
            location  = j.get("location", "") or ""
            title     = j.get("title", "") or ""
            remote_ok = j.get("remote", False) or "remote" in location.lower()

            raw_date  = j.get("published_on") or j.get("created_at") or ""
            posted_at = raw_date[:10] if raw_date else None
            days_old, hours_old = _parse_age(raw_date)

            description = j.get("description", "") or j.get("requirements", "") or ""
            risk, reason = _ghost_risk(days_old, title, description)
            salary = _extract_salary(description)

            shortcode = j.get("shortcode", "") or j.get("id", str(len(all_jobs)))
            url = j.get("url") or f"https://apply.workable.com/{slug}/j/{shortcode}"

            all_jobs.append(_build_job({
                "id":          f"wk_{shortcode}",
                "source":      "workable",
                "company":     company,
                "tier":        tier,
                "work_pref":   work_pref,
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
        if not next_page:
            break
        time.sleep(0.3)

    return all_jobs


# -----------------------------------------------------------------
# JAZZ HR (apply.jazz.co)
# Public API: app.jazz.co/api/jobs?company={slug}
# URL pattern: apply.jazz.co/{slug}
# -----------------------------------------------------------------

def scrape_jazz(slug: str, company: str, tier: int, work_pref: str) -> list[dict]:
    data = _safe_get(
        "https://app.jazz.co/api/jobs",
        params={"company": slug}
    )

    # Jazz returns either a list or {"jobs": [...]}
    if isinstance(data, list):
        jobs_raw = data
    elif isinstance(data, dict) and "jobs" in data:
        jobs_raw = data["jobs"]
    else:
        print(f"  ❌ {company}: Jazz returned no jobs (slug='{slug}')")
        return []

    jobs = []
    for j in jobs_raw:
        location  = j.get("city") or j.get("location") or ""
        state     = j.get("state", "")
        if state and state not in location:
            location = f"{location}, {state}".strip(", ")

        title     = j.get("title", "") or ""
        remote_ok = "remote" in location.lower() or "remote" in title.lower()

        raw_date  = j.get("open_date") or j.get("created_at") or ""
        posted_at = raw_date[:10] if raw_date else None
        days_old, hours_old = _parse_age(raw_date)

        description = j.get("description", "") or ""
        risk, reason = _ghost_risk(days_old, title, description)
        salary = _extract_salary(description)

        job_id = j.get("id", "")
        url    = j.get("apply_url") or f"https://apply.jazz.co/{slug}?job_id={job_id}"

        jobs.append(_build_job({
            "id":          f"jz_{job_id}",
            "source":      "jazz",
            "company":     company,
            "tier":        tier,
            "work_pref":   work_pref,
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
    return jobs


# -----------------------------------------------------------------
# WORKDAY
# POST API: https://{slug}.wd5.myworkdayjobs.com/wday/cxs/{slug}/External/jobs
# No auth required for external postings.
# Covers: Nvidia, Capital One, Visa, PayPal, Intuit, Atlassian, Adobe, Experian
# -----------------------------------------------------------------

# Workday slugs differ from display names -- map them here
WORKDAY_SLUGS = {
    # Format: company_name -> (subdomain, board_name, workday_version)
    # workday_version: "wd5" (default) or "wd1" (older companies)
    "Nvidia":       ("nvidia",      "NVIDIAExternalCareerSite", "wd5"),
    "Capital One":  ("capitalone",  "Capital_One",              "wd5"),
    "Visa":         ("visa",        "Visa",                     "wd5"),
    "PayPal":       ("paypal",      "jobs",                     "wd1"),
    "Intuit":       ("intuit",      "Intuit_Careers",           "wd5"),
    "Atlassian":    ("atlassian",   "atlassian",                "wd5"),
    "Adobe":        ("adobe",       "adobe",                    "wd5"),
    "Experian":     ("experian",    "experian",                 "wd5"),
    "Dell":         ("dell",        "dellexternal",             "wd5"),
    "Oracle":       ("oracle",      "oracle",                   "wd5"),
    "Tesla":        ("tesla",       "Tesla",                    "wd5"),
    "Cisco":        ("cisco",       "Cisco-External-Jobs",      "wd5"),
}


def scrape_workday(slug: str, company: str, tier: int, work_pref: str) -> list[dict]:
    """
    slug format: "company_subdomain|board_name" e.g. "nvidia|NVIDIAExternalCareerSite"
    If just a company name is passed, look up in WORKDAY_SLUGS.
    """
    # Resolve slug
    if "|" in slug:
        parts = slug.split("|")
        subdomain = parts[0]
        board     = parts[1]
        wd_ver    = parts[2] if len(parts) > 2 else "wd5"
    elif company in WORKDAY_SLUGS:
        subdomain, board, wd_ver = WORKDAY_SLUGS[company]
    else:
        print(f"  ❌ {company}: Workday slug not configured. Add to WORKDAY_SLUGS.")
        return []

    base_url = f"https://{subdomain}.{wd_ver}.myworkdayjobs.com/wday/cxs/{subdomain}/{board}/jobs"

    all_jobs = []
    offset = 0
    limit  = 20

    while True:
        try:
            r = SESSION.post(
                base_url,
                json={"limit": limit, "offset": offset, "searchText": ""},
                headers={**HEADERS, "Accept": "application/json", "Content-Type": "application/json"},
                timeout=20,
            )
            if r.status_code != 200:
                if offset == 0:
                    print(f"  ❌ {company}: Workday returned {r.status_code} (url={base_url})")
                break
            data = r.json()
        except Exception as e:
            if offset == 0:
                print(f"  ❌ {company}: Workday request failed: {e}")
            break

        postings = data.get("jobPostings", [])
        if not postings:
            break

        for j in postings:
            title    = j.get("title", "") or ""
            location = j.get("locationsText", "") or j.get("location", "") or ""
            remote_ok = "remote" in location.lower() or "remote" in title.lower()

            path = j.get("externalPath", "") or ""
            url  = f"https://{subdomain}.{wd_ver}.myworkdayjobs.com/en-US/{board}{path}"

            posted_raw = j.get("postedOn", "") or ""
            posted_at  = None
            days_old   = None
            hours_old  = None
            if posted_raw:
                if "T" in posted_raw or len(posted_raw) == 10:
                    days_old, hours_old = _parse_age(posted_raw)
                    posted_at = posted_raw[:10]
                else:
                    m = re.search(r"(\d+)\s+day", posted_raw, re.IGNORECASE)
                    if m:
                        days_old  = int(m.group(1))
                        hours_old = days_old * 24
                    m2 = re.search(r"(\d+)\s+hour", posted_raw, re.IGNORECASE)
                    if m2:
                        hours_old = int(m2.group(1))
                        days_old  = hours_old // 24
                    elif "today" in posted_raw.lower() or "just now" in posted_raw.lower():
                        days_old, hours_old = 0, 0

            description = j.get("jobDescription", {}).get("text", "") or "" \
                if isinstance(j.get("jobDescription"), dict) else ""
            risk, reason = _ghost_risk(days_old, title, description)
            salary = _extract_salary(description)

            all_jobs.append(_build_job({
                "id":          f"wd_{abs(hash(url))}",
                "source":      "workday",
                "company":     company,
                "tier":        tier,
                "work_pref":   work_pref,
                "title":       title,
                "department":  "",
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

        total = data.get("total", 0)
        offset += limit
        if offset >= total:
            break
        time.sleep(0.5)

    return all_jobs


# -----------------------------------------------------------------
# EIGHTFOLD AI
# Many large enterprises use eightfold.ai as their career site.
# URL pattern: {company}.eightfold.ai/careers
# API: {company}.eightfold.ai/api/apply/v2/jobs?domain={domain}
# No auth required for public job listings.
#
# HOW TO FIND THE SLUG:
#   1. Go to company careers page
#   2. If URL is like "careers.microsoft.com" powered by Eightfold,
#      the slug is usually the company subdomain on eightfold.ai
#   3. OR check source for eightfold references
#
# Companies known to use Eightfold:
#   Visa, Capital One, American Express, Cisco, Nvidia, etc.
# -----------------------------------------------------------------

def scrape_eightfold(slug: str, company: str, tier: int, work_pref: str) -> list[dict]:
    """
    slug format: "subdomain|domain" e.g. "aexp|aexp.com"
    or just "subdomain" and domain will be inferred as "{subdomain}.com"
    """
    if "|" in slug:
        subdomain, domain = slug.split("|", 1)
    else:
        subdomain = slug
        domain = f"{slug}.com"

    base_url = f"https://{subdomain}.eightfold.ai"
    all_jobs = []
    start = 0
    limit = 100

    while True:
        # Try SmartApply pattern first (most common)
        data = _safe_get(
            f"{base_url}/api/apply/v2/jobs",
            params={"domain": domain, "start": start, "num": limit, "hl": "en"}
        )

        if not data:
            # Try PCSX pattern as fallback
            data = _safe_get(
                f"{base_url}/api/pcsx/search",
                params={"domain": domain, "query": "", "start": start, "num": limit}
            )
            if data:
                data = data.get("data", data)

        if not data:
            if start == 0:
                print(f"  ❌ {company}: Eightfold returned no data (slug='{slug}')")
            break

        positions = data.get("positions", [])
        if not positions:
            break

        total = data.get("totalJobs", data.get("total", 0))

        for j in positions:
            location = j.get("location", "") or j.get("city", "") or ""
            if isinstance(location, list):
                location = ", ".join(location)
            title     = j.get("name", "") or j.get("title", "") or ""
            remote_ok = "remote" in location.lower() or "remote" in title.lower()

            # Eightfold dates are in epoch ms or ISO
            posted_raw = j.get("t_create") or j.get("created_at") or ""
            if isinstance(posted_raw, (int, float)) and posted_raw > 1000000000000:
                posted_raw = posted_raw / 1000  # ms to seconds
            if isinstance(posted_raw, (int, float)):
                from datetime import datetime, timezone
                dt = datetime.fromtimestamp(posted_raw, tz=timezone.utc)
                posted_at = dt.strftime("%Y-%m-%d")
                days_old, hours_old = _parse_age(dt.isoformat())
            else:
                posted_at = str(posted_raw)[:10] if posted_raw else None
                days_old, hours_old = _parse_age(posted_raw if isinstance(posted_raw, str) else None)

            description = j.get("description", "") or j.get("job_description", "") or ""
            risk, reason = _ghost_risk(days_old, title, description)
            salary = _extract_salary(description)

            job_id_raw = j.get("id") or j.get("job_id") or f"{subdomain}_{start}_{len(all_jobs)}"
            url = f"{base_url}/careers/job/{job_id_raw}"

            all_jobs.append(_build_job({
                "id":          f"ef_{job_id_raw}",
                "source":      "eightfold",
                "company":     company,
                "tier":        tier,
                "work_pref":   work_pref,
                "title":       title,
                "department":  j.get("department", "") or "",
                "location":    location,
                "remote_ok":   int(remote_ok),
                "url":         url,
                "posted_at":   posted_at,
                "days_old":    days_old,
                "hours_old":   hours_old,
                "description": (description or "")[:3000],
                "salary":      salary,
                "ghost_risk":  risk,
                "ghost_reason":reason,
            }))

        start += limit
        if start >= total or len(positions) < limit:
            break
        time.sleep(0.5)

    return all_jobs


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
    if ats == "smartrecruiters":
        return scrape_smartrecruiters(slug, name, tier, work_pref)
    if ats == "workable":
        return scrape_workable(slug, name, tier, work_pref)
    if ats == "jazz":
        return scrape_jazz(slug, name, tier, work_pref)
    if ats == "workday":
        return scrape_workday(slug or name, name, tier, work_pref)
    if ats == "eightfold":
        return scrape_eightfold(slug, name, tier, work_pref)
    return []
