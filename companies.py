# HOW TO ADD A COMPANY:
# Find their ATS from any job URL on their careers page:
#   boards.greenhouse.io/SLUG          -> "greenhouse", "SLUG"
#   jobs.lever.co/SLUG                 -> "lever",      "SLUG"
#   jobs.ashbyhq.com/SLUG              -> "ashby",      "SLUG"
#   careers.smartrecruiters.com/SLUG   -> "smartrecruiters", "SLUG"
#   apply.workable.com/SLUG            -> "workable",   "SLUG"
#   {company}.wd5.myworkdayjobs.com    -> "workday",    None

COMPANIES = [

    # ============================================================
    # TIER 0 -- Hybrid OK
    # ============================================================
    ("OpenAI",      "ashby",      "openai",              0, "hybrid"),  # moved to Ashby
    ("Meta",        "greenhouse", "meta",                0, "hybrid"),  # try meta direct
    ("Anthropic",   "lever",      "anthropic",           0, "hybrid"),
    ("Stripe",      "greenhouse", "stripe",              0, "hybrid"),
    ("Expedia",     "greenhouse", "expedia",             0, "hybrid"),  # fixed slug
    ("Cloudflare",  "greenhouse", "cloudflare",          0, "hybrid"),
    ("Capital One", "workday",    None,                  0, "hybrid"),
    ("Visa",        "workday",    None,                  0, "hybrid"),

    # ============================================================
    # TIER 1 -- Remote Preferred
    # ============================================================
    ("Affirm",       "greenhouse", "affirm",             1, "remote"),
    ("Zillow",       "greenhouse", "zillow",             1, "remote"),
    ("Airbnb",       "greenhouse", "airbnb",             1, "remote"),
    ("Adyen",        "greenhouse", "adyen",              1, "remote"),
    ("NerdWallet",   "greenhouse", "nerdwallet",         1, "remote"),
    ("ThePointsGuy", "greenhouse", "thepointsguy",       1, "remote"),
    ("Block",        "greenhouse", "block",              1, "remote"),
    ("Coinbase",     "ashby",      "coinbase",           1, "remote"),  # moved to Ashby
    ("SoFi",         "greenhouse", "sofi",               1, "remote"),
    ("Wealthfront",  "ashby",      "wealthfront",        1, "remote"),  # try Ashby
    ("Wise",         "lever",      "wise",               1, "remote"),  # fixed slug
    ("HubSpot",      "greenhouse", "hubspot",            1, "remote"),
    ("GitHub",       "greenhouse", "github",             1, "remote"),
    ("Dropbox",      "greenhouse", "dropbox",            1, "remote"),
    ("Figma",        "ashby",      "figma",              1, "remote"),  # moved to Ashby
    ("Miro",         "greenhouse", "miroeng",            1, "remote"),  # fixed slug
    ("Notion",       "ashby",      "notion",             1, "remote"),
    ("Zapier",       "greenhouse", "zapier",             1, "remote"),
    ("Scale AI",     "ashby",      "scaleai",            1, "remote"),
    ("Glean",        "ashby",      "glean",              1, "remote"),
    ("Apollo.io",    "greenhouse", "apollo",             1, "remote"),
    ("Bumble",       "greenhouse", "bumble",             1, "remote"),
    ("Canva",        "greenhouse", "canva",              1, "remote"),
    ("Realtor.com",  "greenhouse", "realtor",            1, "remote"),  # fixed slug
    ("Spotify",      "lever",      "spotify",            1, "remote"),
    ("Pinterest",    "greenhouse", "pinterest",          1, "remote"),
    ("Marqeta",      "greenhouse", "marqeta",            1, "remote"),
    ("Bankrate",     "greenhouse", "bankrate",           1, "remote"),
    ("Reddit",       "greenhouse", "reddit",             1, "remote"),
    ("Docker",       "greenhouse", "docker",             1, "remote"),
    ("PayPal",       "workday",    None,                 1, "remote"),
    ("Intuit",       "workday",    None,                 1, "remote"),
    ("Atlassian",    "workday",    None,                 1, "remote"),
    ("Adobe",        "workday",    None,                 1, "remote"),

    # ============================================================
    # TIER 2 -- Open To It
    # ============================================================
    ("Hopper",       "greenhouse", "hopper",             2, "ok"),
    ("eBay",         "greenhouse", "ebay",               2, "ok"),
    ("Nextdoor",     "ashby",      "nextdoor",           2, "ok"),  # moved to Ashby
    ("Experian",     "workday",    None,                 2, "ok"),

    # ============================================================
    # EXTRA -- SmartRecruiters / Workable / Ashby
    # ============================================================
    ("Smartsheet",   "smartrecruiters", "smartsheet",   1, "remote"),
    ("Twilio",       "ashby",           "twilio",       1, "remote"),  # Twilio -> Ashby
    ("Brex",         "ashby",           "brex",         1, "remote"),  # Brex -> Ashby
    ("Deel",         "ashby",           "deel",         1, "remote"),  # Deel -> Ashby
    ("Rippling",     "ashby",           "rippling",     1, "remote"),  # Rippling -> Ashby
    ("Nvidia",       "workday",         None,           0, "hybrid"),

]

# Auto-split used by run_scraper.py
SCRAPEABLE = [
    c for c in COMPANIES
    if c[1] in ("greenhouse", "lever", "ashby", "smartrecruiters", "workable", "jazz")
    and c[2] is not None
    or c[1] == "workday"
]
WORKDAY     = [c for c in COMPANIES if c[1] == "workday"]
CUSTOM_SKIP = [c for c in COMPANIES if c[1] == "custom"]
