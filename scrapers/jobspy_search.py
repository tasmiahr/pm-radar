# scrapers/jobspy_search.py
#
# JobSpy integration — scrapes Indeed, Google Jobs, ZipRecruiter
# Covers ALL companies, not just your watchlist.
# Called by run_scraper.py when --jobspy flag is used.
#
# Install: pip install jobspy (added to requirements.txt)
# Docs: https://github.com/speedyapply/JobSpy

import time
from datetime import datetime, timezone
from typing import Optional

try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False


def run_jobspy(
    keyword: str = "product manager",
    location: str = "United States",
    hours_old: int = 72,
    results_per_site: int = 50,
    is_remote: bool = False,
) -> list[dict]:
    """
    Scrape jobs from Indeed, Google Jobs, and ZipRecruiter using JobSpy.
    Returns a list of job dicts in our standard format.

    Args:
        keyword:          Search term e.g. "product manager"
        location:         Location string e.g. "United States", "New York, NY"
        hours_old:        Only jobs posted within this many hours
        results_per_site: Max results per job board (Indeed, Google, ZipRecruiter)
        is_remote:        Filter for remote jobs only
    """
    if not JOBSPY_AVAILABLE:
        print("  ⚠️  JobSpy not installed — run: pip install jobspy")
        return []

    print(f"  🌐 JobSpy search: '{keyword}' | location: '{location}' | last {hours_old}h")
    print(f"     Sources: Indeed, Google Jobs, ZipRecruiter")

    try:
        df = scrape_jobs(
            site_name=["indeed", "zip_recruiter", "google"],
            search_term=keyword,
            google_search_term=f"{keyword} jobs in {location} since {'yesterday' if hours_old <= 24 else 'last week'}",
            location=location,
            results_wanted=results_per_site,
            hours_old=hours_old,
            country_indeed="USA",
            is_remote=is_remote,
            description_format="markdown",
            verbose=0,  # suppress jobspy internal logs
        )
    except Exception as e:
        print(f"  ❌ JobSpy error: {e}")
        return []

    if df is None or len(df) == 0:
        print(f"     → 0 jobs found")
        return []

    jobs = []
    now = datetime.now(timezone.utc)

    for _, row in df.iterrows():
        try:
            # Source mapping
            site = str(row.get("site", "")).lower()
            source_map = {
                "indeed":        "indeed",
                "zip_recruiter": "ziprecruiter",
                "google":        "google",
                "linkedin":      "linkedin",
                "glassdoor":     "glassdoor",
            }
            source = source_map.get(site, site)

            # Build unique ID from URL or site+title+company
            url     = str(row.get("job_url", "") or "")
            company = str(row.get("company", "") or "Unknown").strip()
            title   = str(row.get("title", "") or "").strip()
            job_id  = f"{source}_{abs(hash(url or f'{company}{title}'))}"

            # Location
            city    = str(row.get("city", "") or "")
            state   = str(row.get("state", "") or "")
            country = str(row.get("country", "") or "")
            loc_parts = [p for p in [city, state] if p]
            if country and country.upper() not in ("US", "USA", "UNITED STATES"):
                loc_parts.append(country)
            location_str = ", ".join(loc_parts) if loc_parts else ""

            # Remote
            job_type  = str(row.get("job_type", "") or "").lower()
            is_remote_job = (
                bool(row.get("is_remote")) or
                "remote" in location_str.lower() or
                "remote" in title.lower()
            )

            # Date posted
            date_posted = row.get("date_posted")
            posted_at   = None
            days_old    = None
            hours_old_v = None
            if date_posted is not None:
                try:
                    if hasattr(date_posted, "year"):
                        dt = datetime(date_posted.year, date_posted.month,
                                     date_posted.day, tzinfo=timezone.utc)
                    else:
                        from datetime import date as ddate
                        d = datetime.strptime(str(date_posted)[:10], "%Y-%m-%d")
                        dt = d.replace(tzinfo=timezone.utc)
                    posted_at   = dt.strftime("%Y-%m-%d")
                    delta       = now - dt
                    days_old    = delta.days
                    hours_old_v = int(delta.total_seconds() // 3600)
                except Exception:
                    pass

            # Description
            description = str(row.get("description", "") or "")[:3000]

            # Salary
            salary = None
            min_amt = row.get("min_amount")
            max_amt = row.get("max_amount")
            interval = str(row.get("interval", "") or "")
            if min_amt and max_amt:
                try:
                    interval_label = {"yearly": "/yr", "monthly": "/mo", "hourly": "/hr"}.get(interval, "")
                    salary = f"${int(min_amt):,} - ${int(max_amt):,}{interval_label}"
                except Exception:
                    pass
            elif min_amt:
                try:
                    salary = f"${int(min_amt):,}+"
                except Exception:
                    pass

            # Ghost risk heuristic
            risk = "low"
            reason = f"fresh posting via {source}"
            if days_old is not None and days_old > 60:
                risk = "high"
                reason = f"{days_old}d old — likely ghost"
            elif days_old is not None and days_old > 30:
                risk = "medium"
                reason = f"{days_old}d old"

            jobs.append({
                "id":          job_id,
                "source":      source,
                "company":     company,
                "tier":        99,          # discovered via search, not watchlist
                "work_pref":   "remote" if is_remote_job else "unknown",
                "title":       title,
                "department":  "",
                "location":    location_str,
                "remote_ok":   int(is_remote_job),
                "url":         url,
                "posted_at":   posted_at,
                "days_old":    days_old,
                "hours_old":   hours_old_v,
                "description": description,
                "salary":      salary,
                "ghost_risk":  risk,
                "ghost_reason":reason,
            })

        except Exception as e:
            continue  # skip malformed rows

    # Source breakdown
    from collections import Counter
    src_counts = Counter(j["source"] for j in jobs)
    for src, cnt in sorted(src_counts.items()):
        print(f"     {src}: {cnt} jobs")
    print(f"     → {len(jobs)} total jobs found")

    return jobs
