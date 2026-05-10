#!/usr/bin/env python3




import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from companies import SCRAPEABLE, WORKDAY, CUSTOM_SKIP
from scrapers.ats import scrape_company
from scrapers.global_search import search_all_platforms
from scrapers.jobspy_search import run_jobspy
from scrapers.builtin_search import scrape_builtin
from db import get_conn, init_db


# -----------------------------------------------------------------
# DATABASE HELPERS
# -----------------------------------------------------------------

def upsert_job(conn, job: dict) -> bool:
    """
    Insert a new job, or update last_seen + ghost_risk if it already exists.
    Returns True if this is a brand-new job.
    """
    existing = conn.execute(
        "SELECT id FROM jobs WHERE id = ?", (job["id"],)
    ).fetchone()

    if existing:
        # Job already in DB -- just refresh the staleness fields
        conn.execute("""
            UPDATE jobs
            SET last_seen    = datetime('now'),
                ghost_risk   = ?,
                ghost_reason = ?,
                location     = ?,
                days_old     = ?,
                hours_old    = ?
            WHERE id = ?
        """, (
            job["ghost_risk"], job["ghost_reason"],
            job["location"], job["days_old"], job["hours_old"],
            job["id"]
        ))
        return False
    else:
        conn.execute("""
            INSERT INTO jobs (
                id, source, company, tier, work_pref, title, department,
                location, remote_ok, url, posted_at, days_old, hours_old,
                description, salary, ghost_risk, ghost_reason
            ) VALUES (
                :id, :source, :company, :tier, :work_pref, :title, :department,
                :location, :remote_ok, :url, :posted_at, :days_old, :hours_old,
                :description, :salary, :ghost_risk, :ghost_reason
            )
        """, {
            "id":          job.get("id"),
            "source":      job.get("source"),
            "company":     job.get("company"),
            "tier":        job.get("tier", 99),
            "work_pref":   job.get("work_pref", "unknown"),
            "title":       job.get("title", ""),
            "department":  job.get("department", ""),
            "location":    job.get("location", ""),
            "remote_ok":   job.get("remote_ok", 0),
            "url":         job.get("url", ""),
            "posted_at":   job.get("posted_at"),
            "days_old":    job.get("days_old"),
            "hours_old":   job.get("hours_old"),
            "description": job.get("description", ""),
            "salary":      job.get("salary"),
            "ghost_risk":  job.get("ghost_risk", "low"),
            "ghost_reason":job.get("ghost_reason", ""),
        })
        return True


def keyword_match(job: dict, keyword: str) -> bool:
    """
    Return True if keyword matches the job.
    Checks title first (most reliable), then department, then description.
    If description is empty, only requires title or department match.
    """
    kw = keyword.lower()
    title  = (job.get("title") or "").lower()
    dept   = (job.get("department") or "").lower()
    desc   = (job.get("description") or "").lower()

    # Always check title and department
    if kw in title or kw in dept:
        return True

    # Only check description if it's substantive (>100 chars)
    # This prevents false negatives when description is empty/short
    if desc and len(desc) > 100 and kw in desc:
        return True

    return False


# All US states — full names and abbreviations
US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york", "north carolina",
    "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
    "rhode island", "south carolina", "south dakota", "tennessee", "texas",
    "utah", "vermont", "virginia", "washington", "west virginia",
    "wisconsin", "wyoming", "district of columbia",
}

US_STATE_ABBREVS = {
    "al","ak","az","ar","ca","co","ct","de","fl","ga","hi","id","il","in",
    "ia","ks","ky","la","me","md","ma","mi","mn","ms","mo","mt","ne","nv",
    "nh","nj","nm","ny","nc","nd","oh","ok","or","pa","ri","sc","sd","tn",
    "tx","ut","vt","va","wa","wv","wi","wy","dc",
}

# Major US cities — standalone city names without state that are clearly US
US_CITIES = {
    "new york", "los angeles", "chicago", "houston", "phoenix", "philadelphia",
    "san antonio", "san diego", "dallas", "san jose", "austin", "jacksonville",
    "fort worth", "columbus", "charlotte", "indianapolis", "san francisco",
    "seattle", "denver", "nashville", "oklahoma city", "el paso", "washington",
    "boston", "portland", "las vegas", "memphis", "louisville", "baltimore",
    "milwaukee", "albuquerque", "tucson", "fresno", "sacramento", "mesa",
    "kansas city", "atlanta", "omaha", "colorado springs", "raleigh",
    "long beach", "virginia beach", "miami", "oakland", "minneapolis",
    "tulsa", "tampa", "arlington", "new orleans", "cleveland", "bakersfield",
    "aurora", "anaheim", "santa ana", "corpus christi", "riverside", "lexington",
    "st. louis", "pittsburgh", "stockton", "anchorage", "cincinnati",
    "st. paul", "greensboro", "lincoln", "orlando", "irvine", "newark",
    "durham", "chula vista", "plano", "fort wayne", "chandler", "madison",
    "lubbock", "scottsdale", "reno", "buffalo", "gilbert", "glendale",
    "north las vegas", "winston-salem", "chesapeake", "norfolk", "fremont",
    "garland", "irving", "hialeah", "richmond", "baton rouge", "birmingham",
    "rochester", "spokane", "des moines", "montgomery", "modesto", "fayetteville",
    "tacoma", "fontana", "moreno valley", "glendale", "akron", "yonkers",
    "aurora", "huntington beach", "little rock", "tempe", "worcester",
    "salt lake city", "knoxville", "new haven", "providence", "oxnard",
    "hartford", "bridgeport", "syracuse", "albany", "springfield",
    "new york city", "nyc", "sf", "la", "dc",
    # Common tech hub shorthand
    "bay area", "silicon valley", "research triangle",
}

def is_us_location(loc: str) -> bool:
    """
    Return True if a location string appears to be in the United States.
    Handles: full country name, state names, state abbreviations (with comma),
    standalone city names, remote, and empty locations.
    """
    loc = loc.lower().strip()

    if not loc:
        return True  # no location = include (likely remote)

    # Explicit remote/distributed = US-eligible UNLESS qualified with non-US region
    if any(w in loc for w in ["remote", "anywhere", "distributed", "work from home", "wfh"]):
        # Check if remote is qualified with a non-US region
        non_us_qualifiers = [
            "europe", "emea", "apac", "latam", "canada", "uk", "india",
            "australia", "germany", "france", "netherlands", "ireland",
            "brazil", "mexico", "asia", "africa",
        ]
        if any(q in loc for q in non_us_qualifiers):
            return False  # e.g. "Remote - Europe", "Remote (EMEA only)"
        return True

    # Explicit US markers
    if any(m in loc for m in ["united states", "usa", "u.s.", "u.s.a"]):
        return True

    # Explicit non-US countries — fast reject
    non_us = [
        "canada", "toronto", "vancouver", "montreal", "united kingdom", "london",
        "england", "scotland", "ireland", "dublin", "australia", "sydney",
        "melbourne", "germany", "berlin", "france", "paris", "netherlands",
        "amsterdam", "india", "bangalore", "bengaluru", "hyderabad", "mumbai",
        "singapore", "japan", "tokyo", "china", "beijing", "shanghai",
        "brazil", "mexico", "poland", "warsaw", "spain", "madrid", "italy",
        "rome", "milan", "sweden", "stockholm", "denmark", "oslo", "norway",
        "finland", "israel", "tel aviv", "philippines", "indonesia",
        "south korea", "seoul", "taiwan", "new zealand",
    ]
    if any(c in loc for c in non_us):
        return False

    # State full name anywhere in string
    if any(state in loc for state in US_STATES):
        return True

    # State abbreviation with comma: ", CA" or ", NY" etc
    import re as _re
    if _re.search(r',\s*([a-z]{2})\b', loc):
        m = _re.search(r',\s*([a-z]{2})\b', loc)
        if m and m.group(1) in US_STATE_ABBREVS:
            return True

    # Standalone 2-letter state at end: "Austin TX" or "Austin, TX"
    parts = _re.split(r'[\s,]+', loc)
    if parts and parts[-1] in US_STATE_ABBREVS:
        return True

    # Known US city name
    if any(city in loc for city in US_CITIES):
        return True

    # If location is very short and unrecognized, be inclusive (don't filter out)
    if len(loc) < 20 and not any(c.isdigit() for c in loc):
        return True

    return False


def location_match(job: dict, location_filter: str) -> bool:
    """
    Return True if job location matches the filter.
    location_filter can be comma-separated for multiple: "usa,canada"
    """
    loc = (job.get("location") or "").lower()

    # Support comma-separated: "usa,canada" -> match if ANY matches
    filters = [lf.strip() for lf in location_filter.lower().split(",") if lf.strip()]

    for lf in filters:
        if lf in ("usa", "united states", "us"):
            if is_us_location(loc): return True

        elif lf == "remote":
            if any(w in loc for w in ["remote", "anywhere", "distributed"]) or not loc:
                return True

        elif lf == "canada":
            if any(c in loc for c in ["canada", "toronto", "vancouver", "montreal",
                                       "calgary", "ottawa", ", on", ", bc", ", ab"]):
                return True

        elif lf in ("uk", "united kingdom"):
            if any(c in loc for c in ["united kingdom", "london", "manchester",
                                       "edinburgh", "england", ", uk"]):
                return True

        elif lf == "europe":
            if any(c in loc for c in ["europe", "london", "berlin", "amsterdam",
                                       "paris", "dublin", "stockholm", "zurich"]):
                return True

        else:
            # Generic: filter string appears in location, or no location
            if lf in loc or not loc:
                return True

    return False


# -----------------------------------------------------------------
# MAIN RUN FUNCTION
# -----------------------------------------------------------------

def run(keyword: str = None, tier_filter: int = None, global_search: bool = False,
        location_filter: str = None, use_jobspy: bool = False, use_builtin: bool = False):
    init_db()
    conn = get_conn()

    # Filter company list if tier is specified
    # companies tuple: (name, ats, slug, tier, work_pref) -- tier is index 3
    companies = SCRAPEABLE
    if tier_filter is not None:
        companies = [c for c in companies if c[3] == tier_filter]

    total_found = 0
    total_new   = 0
    errors      = []
    start       = time.time()

    print(f"\n🚀 PM Radar -- {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   Companies: {len(companies)} | Keyword: '{keyword or 'all roles'}' | Location: '{location_filter or 'anywhere'}'")

    if CUSTOM_SKIP:
        names = ", ".join(c[0] for c in CUSTOM_SKIP)
        print(f"   Skipping (browser-only): {names}")
    print()

    print(f"  {'COMPANY':<18} {'ATS':<12} {'FOUND':>6} {'NEW':>5}  RISK BREAKDOWN")
    print(f"  {'-'*60}")

    for (name, ats, slug, tier, work_pref) in companies:
        try:
            jobs = scrape_company(name, ats, slug, tier, work_pref)
            raw_count = len(jobs)

            if keyword:
                jobs = [j for j in jobs if keyword_match(j, keyword)]

            if location_filter:
                jobs = [j for j in jobs if location_match(j, location_filter)]

            # Log if filtering removed everything
            if raw_count > 0 and len(jobs) == 0:
                print(f"  ⚠️  {name}: {raw_count} jobs fetched but 0 passed filters (keyword='{keyword}', location='{location_filter}')")

            new_count  = 0
            risk_tally = {}
            for job in jobs:
                is_new = upsert_job(conn, job)
                if is_new:
                    new_count += 1
                r = job["ghost_risk"]
                risk_tally[r] = risk_tally.get(r, 0) + 1

            conn.commit()
            total_found += len(jobs)
            total_new   += new_count

            risk_str = "  ".join(f"{k}:{v}" for k, v in sorted(risk_tally.items())) or "--"
            print(f"  {name:<18} {ats:<12} {len(jobs):>6} {new_count:>5}  {risk_str}")

        except Exception as e:
            errors.append(f"{name}: {e}")
            print(f"  {name:<18} {'ERROR':<12}  ❌ {e}")

        time.sleep(0.35)  # be polite to the APIs

    # ── GLOBAL SEARCH (all companies on each ATS platform) ──────────
    if global_search and keyword:
        print(f"\n  🌐 Global ATS search for '{keyword}' across all platforms...")
        print(f"  {'-'*60}")
        try:
            global_jobs = search_all_platforms(
                keyword=keyword,
                max_per_platform=300,
            )
            # Apply location filter to global results too
            if location_filter:
                global_jobs = [j for j in global_jobs if location_match(j, location_filter)]

            global_new = 0
            for job in global_jobs:
                is_new = upsert_job(conn, job)
                if is_new:
                    global_new += 1
            conn.commit()
            total_found += len(global_jobs)
            total_new   += global_new
            print(f"\n  🌐 Global search: {len(global_jobs)} jobs found, {global_new} new")
        except Exception as e:
            errors.append(f"Global search: {e}")
            print(f"  ❌ Global search error: {e}")
    elif global_search and not keyword:
        print("\n  ⚠️  --global requires --keyword to avoid pulling millions of jobs")

    # ── JOBSPY SEARCH (Indeed, Google Jobs, ZipRecruiter) ────────────
    if use_jobspy and keyword:
        print(f"\n  🔍 JobSpy search across Indeed, Google, ZipRecruiter...")
        print(f"  {'-'*60}")
        try:
            # Convert location filter to a JobSpy-friendly string
            jobspy_location = "United States"
            if location_filter:
                lf = location_filter.lower().split(",")[0].strip()
                if lf in ("usa", "united states", "us"):
                    jobspy_location = "United States"
                elif lf == "remote":
                    jobspy_location = "United States"
                elif lf == "canada":
                    jobspy_location = "Canada"
                elif lf in ("uk", "united kingdom"):
                    jobspy_location = "United Kingdom"
                else:
                    jobspy_location = location_filter.split(",")[0].strip()

            jobspy_jobs = run_jobspy(
                keyword=keyword,
                location=jobspy_location,
                hours_old=72,           # last 3 days
                results_per_site=100,   # per source
                is_remote=False,        # don't filter remote-only
            )

            if location_filter:
                jobspy_jobs = [j for j in jobspy_jobs if location_match(j, location_filter)]

            jobspy_new = 0
            for job in jobspy_jobs:
                is_new = upsert_job(conn, job)
                if is_new:
                    jobspy_new += 1
            conn.commit()
            total_found += len(jobspy_jobs)
            total_new   += jobspy_new
            print(f"  🔍 JobSpy: {len(jobspy_jobs)} jobs, {jobspy_new} new")
        except Exception as e:
            errors.append(f"JobSpy: {e}")
            print(f"  ❌ JobSpy error: {e}")
    elif use_jobspy and not keyword:
        print("\n  ⚠️  --jobspy requires --keyword")

    # ── BUILT IN AUSTIN SCRAPE ───────────────────────────────────────
    if use_builtin:
        print(f"\n  🏙️  Built In Austin — product manager listings...")
        print(f"  {'-'*60}")
        try:
            builtin_jobs = scrape_builtin(
                category="product",
                city_slug="austin",
                max_pages=10,
            )
            if location_filter:
                builtin_jobs = [j for j in builtin_jobs if location_match(j, location_filter)]

            builtin_new = 0
            for job in builtin_jobs:
                is_new = upsert_job(conn, job)
                if is_new:
                    builtin_new += 1
            conn.commit()
            total_found += len(builtin_jobs)
            total_new   += builtin_new
            print(f"  🏙️  Built In Austin: {len(builtin_jobs)} jobs, {builtin_new} new")
        except Exception as e:
            errors.append(f"Built In: {e}")
            print(f"  ❌ Built In error: {e}")
        print("      Example: python run_scraper.py --global -k 'product manager'")

    elapsed = time.time() - start

    # Log this run
    conn.execute(
        "INSERT INTO scrape_runs (companies, jobs_found, jobs_new, errors) VALUES (?,?,?,?)",
        (len(companies), total_found, total_new, "; ".join(errors) or None)
    )
    conn.commit()
    conn.close()

    print(f"\n{'-'*60}")
    print(f"  ✅ Done in {elapsed:.1f}s")
    print(f"  📋 Matching jobs found : {total_found}")
    print(f"  🆕 New jobs added      : {total_new}")
    if errors:
        print(f"  ⚠️  Companies errored  : {len(errors)}")
        for e in errors:
            print(f"     * {e}")
    print(f"  💾 Database            : data/jobs.db")
    print(f"\n  Next: python view_jobs.py --fresh 7 --risk low\n")


# -----------------------------------------------------------------
# CLI
# -----------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PM Radar -- scrape jobs from your target companies"
    )
    parser.add_argument(
        "--keyword", "-k",
        help='Filter by keyword in title/dept/description. E.g. "product manager"'
    )
    parser.add_argument(
        "--location", "-l",
        help='Filter by location. E.g. "usa", "united states", "remote", "canada", "uk"'
    )
    parser.add_argument(
        "--tier", "-t",
        type=int, choices=[0, 1, 2],
        help="Only scrape one tier (0=hybrid, 1=remote, 2=ok)"
    )
    parser.add_argument(
        "--global", "-g",
        dest="global_search",
        action="store_true",
        help="Also search ALL companies on SmartRecruiters/Workable (requires --keyword)"
    )
    parser.add_argument(
        "--jobspy", "-j",
        dest="use_jobspy",
        action="store_true",
        help="Also search Indeed, Google Jobs, ZipRecruiter via JobSpy (requires --keyword)"
    )
    parser.add_argument(
        "--builtin", "-b",
        dest="use_builtin",
        action="store_true",
        help="Also scrape Built In Austin product manager listings (HTML scraper)"
    )
    args = parser.parse_args()
    run(keyword=args.keyword, tier_filter=args.tier,
        global_search=args.global_search, location_filter=args.location,
        use_jobspy=args.use_jobspy, use_builtin=args.use_builtin)
