#!/usr/bin/env python3
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import requests

DB_PATH      = Path(__file__).parent / "data" / "jobs.db"
RESUMES_DIR  = Path(__file__).parent / "resumes"
GEMINI_URL   = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

PROMPT = """You are a PM hiring expert. Score this candidate's resume against the job.

JOB TITLE: {title}
COMPANY: {company}

JOB DESCRIPTION:
{jd}

RESUME:
{resume}

Reply ONLY with a JSON object, no markdown, no explanation:
{{"score": <0-100>, "verdict": "<Strong Apply|Apply|Apply with Caution|Skip>", "reason": "<one sentence why>"}}

Score guide: 80-100=strong fit, 60-79=good fit, 40-59=partial fit, 0-39=poor fit."""


def load_resume() -> str:
    RESUMES_DIR.mkdir(exist_ok=True)
    files = list(RESUMES_DIR.glob("*.txt"))
    if not files:
        print("  ⚠️  No resume found in resumes/ folder — skipping match scoring")
        print("      Add resumes/resume.txt to enable auto-matching")
        sys.exit(0)
    # Use first file found, prefer one named "resume.txt"
    preferred = RESUMES_DIR / "resume.txt"
    path = preferred if preferred.exists() else files[0]
    text = path.read_text(encoding="utf-8").strip()
    print(f"  📄 Resume: {path.name} ({len(text)} chars)")
    return text


def call_gemini(prompt: str, api_key: str) -> dict:
    r = requests.post(
        GEMINI_URL,
        params={"key": api_key},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200}},
        timeout=20,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Gemini API {r.status_code}: {r.text[:200]}")

    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    raw = re.sub(r"^```json|^```|```$", "", raw).strip()
    return json.loads(raw)


def run(title_filter: str = None, limit: int = 100, dry_run: bool = False):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  ⚠️  GEMINI_API_KEY not set — skipping auto-match")
        print("      Add it to GitHub Secrets to enable auto-scoring")
        sys.exit(0)

    if not DB_PATH.exists():
        print("  ⚠️  No database found — run scraper first")
        sys.exit(0)

    resume = load_resume()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Only score jobs that:
    # 1. Have no match score yet
    # 2. Have a non-empty description
    # 3. Optionally match a title filter
    # 4. Are not ghost jobs (high risk)
    query = """
        SELECT id, title, company, description
        FROM jobs
        WHERE match_score IS NULL
          AND description IS NOT NULL
          AND length(description) > 100
          AND ghost_risk != 'high'
    """
    params = []
    if title_filter:
        query += " AND (title LIKE ? OR department LIKE ?)"
        kw = f"%{title_filter}%"
        params += [kw, kw]

    query += f" ORDER BY first_seen DESC LIMIT {limit}"

    jobs = conn.execute(query, params).fetchall()

    if not jobs:
        print("  ✅ No unscored jobs found — all caught up")
        conn.close()
        return

    print(f"  🎯 Scoring {len(jobs)} jobs against your resume...")
    print(f"  {'COMPANY':<18} {'TITLE':<38} {'SCORE':>6}  VERDICT")
    print(f"  {'-'*75}")

    scored = 0
    errors = 0

    for job in jobs:
        try:
            prompt = PROMPT.format(
                title   = job["title"],
                company = job["company"],
                jd      = (job["description"] or "")[:3000],
                resume  = resume[:3000],
            )

            if dry_run:
                print(f"  {job['company']:<18} {job['title'][:37]:<38} {'(dry)':>6}  --")
                continue

            result = call_gemini(prompt, api_key)
            score   = int(result.get("score", 0))
            verdict = result.get("verdict", "")
            reason  = result.get("reason", "")

            conn.execute(
                "UPDATE jobs SET match_score = ?, notes = ? WHERE id = ?",
                (score, reason, job["id"])
            )
            conn.commit()
            scored += 1

            score_color = (
                "🟢" if score >= 75 else
                "🟡" if score >= 55 else
                "🔴"
            )
            print(f"  {job['company']:<18} {job['title'][:37]:<38} {score:>5}%  {score_color} {verdict}")

            # Gemini free tier: 15 RPM limit — stay safe at 12/min
            time.sleep(5)

        except Exception as e:
            errors += 1
            print(f"  {job['company']:<18} {'ERROR':<38}  ❌ {e}")
            time.sleep(2)

    conn.close()
    print(f"\n  ✅ Scored {scored} jobs  |  {errors} errors")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Auto-match jobs against your resume")
    parser.add_argument("--filter", "-f", help='Only score jobs matching title keyword e.g. "product manager"')
    parser.add_argument("--limit",  "-l", type=int, default=100, help="Max jobs to score per run (default 100)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be scored without calling API")
    args = parser.parse_args()

    run(title_filter=args.filter, limit=args.limit, dry_run=args.dry_run)
