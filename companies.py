# HOW TO ADD A COMPANY:
# Find their ATS from any job URL on their careers page:
#   boards.greenhouse.io/SLUG          -> "greenhouse", "SLUG"
#   jobs.lever.co/SLUG                 -> "lever",      "SLUG"
#   jobs.ashbyhq.com/SLUG              -> "ashby",      "SLUG"
#   careers.smartrecruiters.com/SLUG   -> "smartrecruiters", "SLUG"
#   apply.workable.com/SLUG            -> "workable",   "SLUG"
#   apply.jazz.co/SLUG                 -> "jazz",       "SLUG"
#   {company}.wd5.myworkdayjobs.com    -> "workday",    None  (slug resolved from WORKDAY_SLUGS in ats.py)
#   Custom site requiring browser      -> "custom",     None  (Phase 3)

COMPANIES = [

    # ============================================================
    # TIER 0 -- Hybrid OK
    # ============================================================

    # Greenhouse
    ("OpenAI",      "greenhouse", "openai",              0, "hybrid"),
    ("Meta",        "greenhouse", "meta",                0, "hybrid"),
    ("Stripe",      "greenhouse", "stripe",              0, "hybrid"),
    ("Expedia",     "greenhouse", "expediagroup",        0, "hybrid"),
    ("Cloudflare",  "greenhouse", "cloudflare",          0, "hybrid"),

    # Lever
    ("Anthropic",   "lever",      "anthropic",           0, "hybrid"),

    # Workday -- now active
    ("Nvidia",      "workday",    None,                  0, "hybrid"),
    ("Capital One", "workday",    None,                  0, "hybrid"),
    ("Visa",        "workday",    None,                  0, "hybrid"),

    # Custom (Phase 3 -- needs browser automation)
    ("Google",      "custom",     None,                  0, "hybrid"),
    ("Apple",       "custom",     None,                  0, "hybrid"),

    # ============================================================
    # TIER 1 -- Remote Preferred
    # ============================================================

    # Greenhouse
    ("Affirm",       "greenhouse", "affirm",             1, "remote"),
    ("Zillow",       "greenhouse", "zillow",             1, "remote"),
    ("Airbnb",       "greenhouse", "airbnb",             1, "remote"),
    ("Adyen",        "greenhouse", "adyen",              1, "remote"),
    ("NerdWallet",   "greenhouse", "nerdwallet",         1, "remote"),
    ("ThePointsGuy", "greenhouse", "thepointsguy",       1, "remote"),
    ("Block",        "greenhouse", "block",              1, "remote"),
    ("Coinbase",     "greenhouse", "coinbase",           1, "remote"),
    ("SoFi",         "greenhouse", "sofi",               1, "remote"),
    ("Wealthfront",  "greenhouse", "wealthfront",        1, "remote"),
    ("HubSpot",      "greenhouse", "hubspot",            1, "remote"),
    ("GitHub",       "greenhouse", "github",             1, "remote"),
    ("Dropbox",      "greenhouse", "dropbox",            1, "remote"),
    ("Miro",         "greenhouse", "miro",               1, "remote"),
    ("Zapier",       "greenhouse", "zapier",             1, "remote"),
    ("Apollo.io",    "greenhouse", "apollo",             1, "remote"),
    ("Bumble",       "greenhouse", "bumble",             1, "remote"),
    ("Canva",        "greenhouse", "canva",              1, "remote"),
    ("Realtor.com",  "greenhouse", "realtordotcom",      1, "remote"),
    ("Pinterest",    "greenhouse", "pinterest",          1, "remote"),
    ("Marqeta",      "greenhouse", "marqeta",            1, "remote"),
    ("Bankrate",     "greenhouse", "bankrate",           1, "remote"),
    ("Reddit",       "greenhouse", "reddit",             1, "remote"),
    ("Docker",       "greenhouse", "docker",             1, "remote"),

    # Lever
    ("Wise",         "lever",      "transferwise",       1, "remote"),
    ("Figma",        "lever",      "figma",              1, "remote"),
    ("Spotify",      "lever",      "spotify",            1, "remote"),

    # Ashby
    ("Notion",       "ashby",      "notion",             1, "remote"),
    ("Scale AI",     "ashby",      "scaleai",            1, "remote"),
    ("Glean",        "ashby",      "glean",              1, "remote"),

    # Workday -- now active
    ("PayPal",       "workday",    None,                 1, "remote"),
    ("Intuit",       "workday",    None,                 1, "remote"),
    ("Atlassian",    "workday",    None,                 1, "remote"),
    ("Adobe",        "workday",    None,                 1, "remote"),

    # ============================================================
    # TIER 2 -- Open To It
    # ============================================================

    # Greenhouse
    ("Hopper",       "greenhouse", "hopper",             2, "ok"),
    ("eBay",         "greenhouse", "ebay",               2, "ok"),
    ("Nextdoor",     "greenhouse", "nextdoor",           2, "ok"),

    # Workday -- now active
    ("Experian",     "workday",    None,                 2, "ok"),

    # ============================================================
    # EXTRA -- SmartRecruiters / Workable examples
    # ============================================================
    ("Smartsheet",   "smartrecruiters", "smartsheet",   1, "remote"),
    ("Twilio",       "smartrecruiters", "twilio",       1, "remote"),
    ("Brex",         "smartrecruiters", "brex",         1, "remote"),
    ("Deel",         "workable",        "deel",         1, "remote"),
    ("Rippling",     "workable",        "rippling",     1, "remote"),

]

# Auto-split used by run_scraper.py -- do not edit
SCRAPEABLE = [
    c for c in COMPANIES
    if c[1] in ("greenhouse", "lever", "ashby", "smartrecruiters", "workable", "jazz")
    and c[2] is not None
    or c[1] == "workday"
]
WORKDAY    = [c for c in COMPANIES if c[1] == "workday"]
CUSTOM_SKIP = [c for c in COMPANIES if c[1] == "custom"]
