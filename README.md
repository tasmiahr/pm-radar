# # 🎯 JobRadar — Personal Job Search CRM

> Automated job scraper + resume matcher for your curated company list.
> Built with Python, SQLite, and the Anthropic API.

## What It Does

- **Scrapes** job postings directly from company ATS systems (Greenhouse, Lever, Ashby) via their public APIs
- **Flags ghost jobs** based on posting age, title patterns, and description quality
- **Stores everything** in a local SQLite database — portable, searchable, git-friendly
- **Matches your resume** against any job using Claude AI — score, gaps, tailored bullets

## Setup (5 minutes)

```bash
# 1. Clone and install
git clone <your-repo>
cd jobradar
pip install requests rich

# 2. Add your resume(s)
mkdir resumes
# Add your resume as plain text:
# resumes/senior_pm.txt
# resumes/fintech_pm.txt
# etc.

# 3. Set your Anthropic API key (for resume matching)
export ANTHROPIC_API_KEY=sk-ant-...

# 4. Run the scraper
python run_scraper.py --keyword "product manager"
```

## Usage

### Scrape all target companies

```bash
python run_scraper.py
```

### Scrape with keyword filter

```bash
python run_scraper.py --keyword "senior product manager"
python run_scraper.py --keyword "PM" --tier 1     # tier 1 companies only
```

### View your job pipeline

```bash
python view_jobs.py                        # all jobs
python view_jobs.py --fresh 7              # posted in last 7 days
python view_jobs.py --remote --risk low    # remote + low ghost risk
python view_jobs.py --company Stripe       # specific company
python view_jobs.py --summary              # pipeline stats
python view_jobs.py --export jobs.csv      # export to spreadsheet
```

### Match your resume to a job

```bash
# By job ID from your DB
python match_resume.py --job-id gh_123456

# By direct URL
python match_resume.py --job-url https://boards.greenhouse.io/stripe/jobs/123

# Compare ALL your resumes against one JD
python match_resume.py --job-id gh_123456 --all-resumes

# From a pasted JD file
python match_resume.py --jd-file stripe_pm.txt
```

## Ghost Job Risk Legend

|Flag    |Meaning                               |
|--------|--------------------------------------|
|✅ low   |Fresh posting, direct from company ATS|
|⚠️ medium|30-60 days old or vague title         |
|🚫 high  |60+ days old — likely ghost/evergreen |

## Company Coverage

|Tier            |ATS                   |Companies                                                        |
|----------------|----------------------|-----------------------------------------------------------------|
|T0 (hybrid ok)  |Greenhouse/Lever      |OpenAI, Anthropic, Stripe, Cloudflare                            |
|T1 (remote pref)|Greenhouse/Lever/Ashby|Affirm, Airbnb, Coinbase, Figma, Notion, Reddit, HubSpot, GitHub…|
|T2 (ok)         |Greenhouse            |Toast, SurveyMonkey, Hopper, eBay, Nextdoor                      |
|⚠️ Phase 2       |Workday               |Adobe, PayPal, Intuit, Atlassian, Capital One, Visa              |
|⚠️ Phase 2       |Custom                |Google, Apple, Nvidia, Meta, Spotify                             |

## Architecture

```
jobradar/
├── run_scraper.py      # Main scraper — run this daily
├── view_jobs.py        # CLI browser for your pipeline
├── match_resume.py     # LLM resume matcher
├── companies.py        # Your target company list + ATS config
├── db.py               # SQLite schema
├── scrapers/
│   └── ats.py          # Greenhouse + Lever + Ashby scrapers
├── resumes/            # Your resume files (plain text)
│   └── senior_pm.txt
└── data/
    └── jobs.db         # Your job database (auto-created)
```

## Automating with GitHub Actions

Create `.github/workflows/scrape.yml`:

```yaml
name: Daily Job Scrape
on:
  schedule:
    - cron: '0 9,17 * * 1-5'  # 9am and 5pm weekdays
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with: { python-version: '3.11' }
      - run: pip install requests
      - run: python run_scraper.py --keyword "product manager"
      - uses: actions/upload-artifact@v4
        with:
          name: jobs-db
          path: data/jobs.db
```

## Roadmap

- [x] Greenhouse + Lever + Ashby scrapers
- [x] SQLite job database with deduplication
- [x] Ghost job legitimacy detection
- [x] LLM resume matcher with score + gaps
- [ ] Workday scraper (Phase 2)
- [ ] Streamlit dashboard
- [ ] LinkedIn applicant count (Phase 3)
- [ ] Company financial health check via EDGAR