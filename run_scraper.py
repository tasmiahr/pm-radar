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
        """, job)
        return True


def keyword_match(job: dict, keyword: str) -> bool:
    """Return True if the keyword appears anywhere in the job's title, dept, or description."""
    kw = keyword.lower()
    return (
        kw in (job.get("title") or "").lower()
        or kw in (job.get("department") or "").lower()
        or kw in (job.get("description") or "").lower()
    )


# -----------------------------------------------------------------
# MAIN RUN FUNCTION
# -----------------------------------------------------------------

def run(keyword: str = None, tier_filter: int = None, global_search: bool = False):
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

    print(f"\n🚀 JobRadar -- {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   Companies: {len(companies)} | Keyword: '{keyword or 'all roles'}'")

    if CUSTOM_SKIP:
        names = ", ".join(c[0] for c in CUSTOM_SKIP)
        print(f"   ⏭️  Custom/browser-only (Phase 3): {names}")
    print()

    print(f"  {'COMPANY':<18} {'ATS':<12} {'FOUND':>6} {'NEW':>5}  RISK BREAKDOWN")
    print(f"  {'-'*60}")

    for (name, ats, slug, tier, work_pref) in companies:
        try:
            jobs = scrape_company(name, ats, slug, tier, work_pref)

            if keyword:
                jobs = [j for j in jobs if keyword_match(j, keyword)]

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
        description="JobRadar -- scrape jobs from your target companies"
    )
    parser.add_argument(
        "--keyword", "-k",
        help='Filter by keyword in title/dept/description. E.g. "product manager"'
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
        help="Also search ALL companies on Greenhouse/SmartRecruiters/Workable (requires --keyword)"
    )
    args = parser.parse_args()
    run(keyword=args.keyword, tier_filter=args.tier, global_search=args.global_search)
