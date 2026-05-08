#!/usr/bin/env python3
“””
view_jobs.py — Browse and filter your job pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT THIS FILE DOES:
Queries data/jobs.db with your chosen filters and prints a table.
Optionally exports to CSV. Does NOT make any network requests.

EXECUTION ORDER:
view_jobs.py → imports db.py → queries data/jobs.db → prints table

TIME WINDOW FILTERING:
–hours 6       jobs posted in the last 6 hours
–hours 12      jobs posted in the last 12 hours
–hours 24      jobs posted in the last 24 hours (same as –days 1)
–days 1        jobs posted in the last 1 day
–days 3        jobs posted in the last 3 days
–days 7        jobs posted in the last 7 days
(only one of –hours or –days can be used at a time)

USAGE EXAMPLES:
python view_jobs.py                             # all jobs, sorted by tier + age
python view_jobs.py –hours 24                  # last 24 hours only
python view_jobs.py –days 7 –risk low         # last 7 days, low ghost risk
python view_jobs.py –days 3 –remote           # last 3 days, remote-tagged
python view_jobs.py –company Stripe            # one company
python view_jobs.py –keyword “product”         # keyword in title/dept
python view_jobs.py –tier 1 –days 7           # tier 1, last week
python view_jobs.py –summary                   # pipeline stats overview
python view_jobs.py –verbose                   # include URL + description snippet
python view_jobs.py –export jobs.csv           # save to spreadsheet
python view_jobs.py –days 7 –export fresh.csv # combine filters + export
“””

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(**file**).parent))
from db import get_conn

RISK_ICON  = {“low”: “✅”, “medium”: “⚠️ “, “high”: “🚫”}
TIER_LABEL = {0: “T0·hybrid”, 1: “T1·remote”, 2: “T2·ok”}

# ─────────────────────────────────────────────────────────────────

# QUERY BUILDER

# ─────────────────────────────────────────────────────────────────

def build_query(args) -> tuple[str, list]:
“”“Turn CLI args into a WHERE clause + params list.”””
where  = [“1=1”]
params = []

```
# ── Time window (hours takes priority over days) ──────────────
if args.hours is not None:
    where.append("(hours_old IS NULL OR hours_old <= ?)")
    params.append(args.hours)
elif args.days is not None:
    where.append("(days_old IS NULL OR days_old <= ?)")
    params.append(args.days)

# ── Other filters ─────────────────────────────────────────────
if args.keyword:
    where.append("(title LIKE ? OR department LIKE ? OR description LIKE ?)")
    kw = f"%{args.keyword}%"
    params += [kw, kw, kw]

if args.company:
    where.append("company LIKE ?")
    params.append(f"%{args.company}%")

if args.remote:
    where.append("remote_ok = 1")

if args.risk:
    where.append("ghost_risk = ?")
    params.append(args.risk)

if args.tier is not None:
    where.append("tier = ?")
    params.append(args.tier)

if args.status:
    where.append("status = ?")
    params.append(args.status)

return " AND ".join(where), params
```

# ─────────────────────────────────────────────────────────────────

# DISPLAY

# ─────────────────────────────────────────────────────────────────

def display_jobs(rows, verbose: bool = False):
if not rows:
print(”\n  No jobs match those filters.\n”)
return

```
print(f"\n{'─'*105}")
print(f"  {'#':<4} {'COMPANY':<16} {'TITLE':<40} {'LOCATION':<18} {'AGE':<9} {'RISK':<6} {'TIER'}")
print(f"{'─'*105}")

for i, r in enumerate(rows, 1):
    # Age string: prefer hours if < 48h, else days
    if r["hours_old"] is not None and r["hours_old"] < 48:
        age_str = f"{r['hours_old']}h"
    elif r["days_old"] is not None:
        age_str = f"{r['days_old']}d"
    else:
        age_str = "?"

    risk_icon  = RISK_ICON.get(r["ghost_risk"], "?")
    tier_str   = TIER_LABEL.get(r["tier"], "?")
    location   = (r["location"] or "")[:17]
    title      = (r["title"] or "")[:39]
    company    = (r["company"] or "")[:15]
    remote_tag = " 🌐" if r["remote_ok"] else ""

    print(f"  {i:<4} {company:<16} {title:<40} {location:<18} {age_str:<9} {risk_icon:<6} {tier_str}{remote_tag}")

    if verbose:
        print(f"       🔗 {r['url']}")
        snippet = (r["description"] or "")[:150].replace("\n", " ")
        print(f"       📝 {snippet}...")
        print(f"       ℹ️  {r['ghost_reason']}")
        print()

print(f"{'─'*105}")
print(f"  {len(rows)} job(s) shown\n")
```

def print_summary(conn):
s = conn.execute(”””
SELECT
COUNT(*)                                          AS total,
SUM(CASE WHEN hours_old <= 6  THEN 1 ELSE 0 END) AS h6,
SUM(CASE WHEN hours_old <= 12 THEN 1 ELSE 0 END) AS h12,
SUM(CASE WHEN hours_old <= 24 THEN 1 ELSE 0 END) AS h24,
SUM(CASE WHEN days_old  <= 3  THEN 1 ELSE 0 END) AS d3,
SUM(CASE WHEN days_old  <= 7  THEN 1 ELSE 0 END) AS d7,
SUM(CASE WHEN ghost_risk=‘low’    THEN 1 ELSE 0 END) AS low_r,
SUM(CASE WHEN ghost_risk=‘medium’ THEN 1 ELSE 0 END) AS med_r,
SUM(CASE WHEN ghost_risk=‘high’   THEN 1 ELSE 0 END) AS high_r,
SUM(CASE WHEN remote_ok=1         THEN 1 ELSE 0 END) AS remote,
SUM(CASE WHEN status=‘applied’    THEN 1 ELSE 0 END) AS applied,
SUM(CASE WHEN status=‘new’        THEN 1 ELSE 0 END) AS new_status
FROM jobs
“””).fetchone()

```
last = conn.execute(
    "SELECT run_at, jobs_new FROM scrape_runs ORDER BY id DESC LIMIT 1"
).fetchone()

print(f"\n  📊 JobRadar Pipeline")
print(f"  {'─'*38}")
print(f"  Total tracked      : {s['total']}")
print(f"  ── By recency ──────────────────")
print(f"  Last 6 hours       : {s['h6']}")
print(f"  Last 12 hours      : {s['h12']}")
print(f"  Last 24 hours      : {s['h24']}")
print(f"  Last 3 days        : {s['d3']}")
print(f"  Last 7 days        : {s['d7']}")
print(f"  ── By ghost risk ───────────────")
print(f"  ✅ Low             : {s['low_r']}")
print(f"  ⚠️  Medium          : {s['med_r']}")
print(f"  🚫 High            : {s['high_r']}")
print(f"  ── By status ───────────────────")
print(f"  New (unreviewed)   : {s['new_status']}")
print(f"  Applied            : {s['applied']}")
print(f"  🌐 Remote-tagged   : {s['remote']}")
if last:
    print(f"  ── Last scrape ─────────────────")
    print(f"  {last['run_at']}  (+{last['jobs_new']} new)")
print()
```

def export_csv(rows, path: str):
fields = [
“company”, “tier”, “work_pref”, “title”, “department”, “location”,
“remote_ok”, “hours_old”, “days_old”, “posted_at”,
“ghost_risk”, “ghost_reason”, “url”, “status”, “match_score”
]
with open(path, “w”, newline=””, encoding=“utf-8”) as f:
writer = csv.DictWriter(f, fieldnames=fields, extrasaction=“ignore”)
writer.writeheader()
writer.writerows([dict(r) for r in rows])
print(f”  📄 Exported {len(rows)} jobs → {path}”)

# ─────────────────────────────────────────────────────────────────

# CLI

# ─────────────────────────────────────────────────────────────────

def main():
parser = argparse.ArgumentParser(
description=“JobRadar — browse your job pipeline”,
formatter_class=argparse.RawDescriptionHelpFormatter,
epilog=”””
Time window examples:
–hours 6          last 6 hours
–hours 12         last 12 hours
–hours 24         last 24 hours
–days 1           last 1 day
–days 3           last 3 days
–days 7           last 7 days
“””
)

```
# ── Time window ───────────────────────────────────────────────
time_group = parser.add_mutually_exclusive_group()
time_group.add_argument(
    "--hours", type=int, metavar="N",
    help="Jobs posted within last N hours (6, 12, 24, etc.)"
)
time_group.add_argument(
    "--days", type=int, metavar="N",
    help="Jobs posted within last N days (1, 3, 7, etc.)"
)

# ── Other filters ─────────────────────────────────────────────
parser.add_argument("--keyword",  "-k", help="Keyword in title/dept/description")
parser.add_argument("--company",  "-c", help="Filter by company name")
parser.add_argument("--remote",   "-r", action="store_true", help="Remote-tagged only")
parser.add_argument("--risk",     choices=["low","medium","high"], help="Ghost risk level")
parser.add_argument("--tier",     type=int, choices=[0,1,2], help="Tier filter")
parser.add_argument("--status",   help="Status: new | reviewing | applied | rejected | offer")

# ── Output options ────────────────────────────────────────────
parser.add_argument("--summary",  "-s", action="store_true", help="Show pipeline stats")
parser.add_argument("--verbose",  "-v", action="store_true", help="Show URLs + description")
parser.add_argument("--export",   metavar="FILE.csv",        help="Export results to CSV")

args = parser.parse_args()
conn = get_conn()

if args.summary:
    print_summary(conn)

where, params = build_query(args)
rows = conn.execute(
    f"SELECT * FROM jobs WHERE {where} ORDER BY tier ASC, hours_old ASC NULLS LAST, days_old ASC NULLS LAST",
    params
).fetchall()

if args.export:
    export_csv(rows, args.export)
else:
    display_jobs(rows, verbose=args.verbose)

conn.close()
```

if **name** == “**main**”:
main()
