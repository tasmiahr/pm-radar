#!/usr/bin/env python3




import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH  = Path(__file__).parent / "data" / "jobs.db"
OUT_PATH = Path(__file__).parent / "dashboard_data.json"


def export(keyword=None, days=None, hours=None, risk=None, out_path=OUT_PATH):
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        print(f"   Run: python run_scraper.py  first")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # -- Build WHERE clause ---------------------------------------
    where  = ["1=1"]
    params = []

    if keyword:
        kw = f"%{keyword}%"
        where.append("(title LIKE ? OR department LIKE ? OR description LIKE ?)")
        params += [kw, kw, kw]

    if hours is not None:
        where.append("(hours_old IS NULL OR hours_old <= ?)")
        params.append(hours)
    elif days is not None:
        where.append("(days_old IS NULL OR days_old <= ?)")
        params.append(days)

    if risk:
        where.append("ghost_risk = ?")
        params.append(risk)

    # -- Fetch jobs -----------------------------------------------
    rows = conn.execute(f"""
        SELECT
            id, source, company, tier, work_pref,
            title, department, location, remote_ok,
            url, posted_at, days_old, hours_old,
            ghost_risk, ghost_reason,
            first_seen, last_seen, status,
            match_score, notes,
            salary,
            NULL AS applicants
        FROM jobs
        WHERE {' AND '.join(where)}
        ORDER BY hours_old ASC NULLS LAST, days_old ASC NULLS LAST
    """, params).fetchall()

    jobs = []
    for r in rows:
        d = dict(r)
        d["remote_ok"] = 1 if d.get("remote_ok") else 0
        jobs.append(d)

    # -- How many were new in the most recent scrape run? ---------
    last_run = conn.execute("""
        SELECT jobs_new, run_at FROM scrape_runs
        ORDER BY id DESC LIMIT 1
    """).fetchone()
    new_this_run = last_run["jobs_new"] if last_run else 0
    last_run_at  = last_run["run_at"]   if last_run else None

    conn.close()

    # -- Write output ---------------------------------------------
    now = datetime.now(timezone.utc).strftime("%b %d %Y %H:%M UTC")
    output = {
        "meta": {
            "exported_at":  now,
            "last_scrape":  last_run_at,
            "total":        len(jobs),
            "new_this_run": new_this_run,
            "filters": {
                "keyword": keyword,
                "days":    days,
                "hours":   hours,
                "risk":    risk,
            }
        },
        "jobs": jobs
    }

    Path(out_path).write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print(f"✅ Exported {len(jobs)} jobs → {out_path}")
    print(f"   New this run : {new_this_run}")
    print(f"   Last scrape  : {last_run_at}")

    return new_this_run   # returned so notify.py can use it


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export jobs DB to JSON for dashboard")
    parser.add_argument("--keyword", "-k")
    parser.add_argument("--days",    type=int)
    parser.add_argument("--hours",   type=int)
    parser.add_argument("--risk",    choices=["low","medium","high"])
    parser.add_argument("--out", "-o", default=str(OUT_PATH))
    args = parser.parse_args()

    export(
        keyword  = args.keyword,
        days     = args.days,
        hours    = args.hours,
        risk     = args.risk,
        out_path = args.out,
    )
