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
    ("NerdWallet",   "ashby",      "nerdwallet",         1, "remote"),  # moved to Ashby
    ("ThePointsGuy", "ashby",      "thepointsguy",       1, "remote"),  # try Ashby
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
    ("Bumble",       "lever",      "bumbleinc",          1, "remote"),  # fixed slug
    ("Canva",        "ashby",      "canva",              1, "remote"),  # try Ashby
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
    ("Hopper",       "ashby",      "hopper",             2, "ok"),  # moved to Ashby
    ("eBay",         "greenhouse", "ebay",               2, "ok"),
    ("Nextdoor",     "ashby",      "nextdoor",           2, "ok"),  # moved to Ashby
    ("Experian",     "workday",    None,                 2, "ok"),

    # ============================================================
    # EXTRA -- SmartRecruiters / Workable / Ashby
    # ============================================================
    ("Smartsheet",   "smartrecruiters", "smartsheet",   1, "remote"),
    ("Twilio",       "ashby",           "twilio",       1, "remote"),
    ("Brex",         "ashby",           "brex",         1, "remote"),
    ("Deel",         "ashby",           "deel",         1, "remote"),
    ("Rippling",     "ashby",           "rippling",     1, "remote"),
    ("Nvidia",       "workday",         None,           0, "hybrid"),

    # ============================================================
    # EXPANDED WATCHLIST -- fintech, SaaS, crypto, data
    # job-boards.greenhouse.io companies use same API token
    # ============================================================

    # Fintech / payments
    ("Robinhood",    "greenhouse", "robinhood",         1, "remote"),
    ("Plaid",        "greenhouse", "plaid",             1, "remote"),
    ("Chime",        "greenhouse", "chime",             1, "remote"),
    ("Ramp",         "ashby",      "ramp",              1, "remote"),
    ("Mercury",      "ashby",      "mercury",           1, "remote"),
    ("Braintree",    "greenhouse", "braintree",         1, "remote"),
    ("Checkout.com", "greenhouse", "checkout",          1, "remote"),
    ("Klarna",       "greenhouse", "klarna",            1, "remote"),
    ("Betterment",   "greenhouse", "betterment",        1, "remote"),
    ("Acorns",       "greenhouse", "acorns",            1, "remote"),
    ("Stash",        "greenhouse", "stash",             1, "remote"),

    # Crypto
    ("Gemini",       "greenhouse", "gemini",            1, "remote"),
    ("Kraken",       "greenhouse", "kraken",            1, "remote"),
    ("Chainalysis",  "greenhouse", "chainalysis",       1, "remote"),
    ("Circle",       "greenhouse", "circle",            1, "remote"),
    ("Paxos",        "greenhouse", "paxos",             1, "remote"),

    # SaaS / productivity
    ("Airtable",     "greenhouse", "airtable",          1, "remote"),
    ("Asana",        "greenhouse", "asana",             1, "remote"),
    ("Webflow",      "greenhouse", "webflow",           1, "remote"),
    ("Retool",       "greenhouse", "retool",            1, "remote"),
    ("Linear",       "ashby",      "linear",            1, "remote"),
    ("Vercel",       "ashby",      "vercel",            1, "remote"),
    ("Loom",         "greenhouse", "loom",              1, "remote"),
    ("Airtable",     "greenhouse", "airtable",          1, "remote"),
    ("Productboard", "greenhouse", "productboard",      1, "remote"),
    ("Typeform",     "greenhouse", "typeform",          1, "remote"),

    # Analytics / data
    ("Amplitude",    "greenhouse", "amplitude",         1, "remote"),
    ("Mixpanel",     "greenhouse", "mixpanel",          1, "remote"),
    ("Databricks",   "greenhouse", "databricks",        1, "remote"),
    ("Snowflake",    "greenhouse", "snowflake",         1, "remote"),
    ("Confluent",    "greenhouse", "confluent",         1, "remote"),
    ("dbt Labs",     "greenhouse", "dbtlabs",           1, "remote"),
    ("Heap",         "greenhouse", "heap",              1, "remote"),
    ("FullStory",    "greenhouse", "fullstory",         1, "remote"),

    # CRM / sales
    ("Gong",         "greenhouse", "gong",              1, "remote"),
    ("Outreach",     "greenhouse", "outreach",          1, "remote"),
    ("Salesloft",    "greenhouse", "salesloft",         1, "remote"),
    ("Intercom",     "greenhouse", "intercom",          1, "remote"),

    # HR / people
    ("Gusto",        "greenhouse", "gusto",             1, "remote"),
    ("Lattice",      "greenhouse", "lattice",           1, "remote"),
    ("Carta",        "greenhouse", "carta",             1, "remote"),

    # Security / infra
    ("Okta",         "greenhouse", "okta",              1, "remote"),
    ("Checkr",       "greenhouse", "checkr",            1, "remote"),
    ("Cloudflare",   "greenhouse", "cloudflare",        0, "hybrid"),

    # Gaming / media
    ("Zynga",        "greenhouse", "zyngacareers",      2, "ok"),
    ("NBCUniversal", "smartrecruiters", "NBCUniversal", 2, "ok"),

    # Travel
    ("Navan",        "greenhouse", "navan",             1, "remote"),

    # ============================================================
    # AUSTIN, TX COMPANIES
    # Silicon Hills -- major tech hub
    # ============================================================

    # Large Austin employers (Workday/custom ATS)
    ("Dell",           "workday",    None,              0, "hybrid"),  # Dell HQ Austin
    ("Oracle",         "workday",    None,              0, "hybrid"),  # Oracle HQ Austin
    ("Tesla",          "workday",    None,              0, "hybrid"),  # major Austin employer
    ("Indeed",         "greenhouse", "indeed",          0, "hybrid"),  # Indeed HQ Austin
    ("HomeAway/VRBO",  "greenhouse", "homeaway",        0, "hybrid"),  # Expedia subsidiary Austin

    # Austin fintech
    ("Q2",             "greenhouse", "q2ebanking",      1, "remote"),  # fintech Austin
    ("Opcity",         "greenhouse", "opcity",          2, "ok"),
    ("WP Engine",      "greenhouse", "wpengine",        1, "remote"),
    ("Kforce",         "greenhouse", "kforce",          2, "ok"),
    ("Vrbo",           "greenhouse", "vrbo",            1, "remote"),
    ("Bumble",         "lever",      "bumbleinc",       0, "hybrid"),  # Bumble HQ Austin
    ("Match Group",    "greenhouse", "matchgroup",      0, "hybrid"),  # Match HQ Dallas/Austin
    ("BigCommerce",    "greenhouse", "bigcommerce",     1, "remote"),
    ("Opcity",         "greenhouse", "opcity",          2, "ok"),
    ("Civitas",        "greenhouse", "civitaslearning",  2, "ok"),
    ("Atmosphere",     "greenhouse", "atmosphere",      2, "ok"),
    ("Sana Benefits",  "ashby",      "sanabenefits",    1, "remote"),
    ("Ojo Labs",       "greenhouse", "ojolabs",         2, "ok"),
    ("Liveoak Tech",   "greenhouse", "liveoaktech",     2, "ok"),
    ("NinjaRMM",       "greenhouse", "ninjarmm",        1, "remote"),
    ("Shipstation",    "greenhouse", "shipstation",     1, "remote"),
    ("Bazaarvoice",    "greenhouse", "bazaarvoice",     2, "ok"),
    ("Dosh",           "greenhouse", "dosh",            2, "ok"),
    ("Khoros",         "greenhouse", "khoros",          2, "ok"),
    ("Phunware",       "greenhouse", "phunware",        2, "ok"),
    ("Yodle",          "greenhouse", "yodle",           2, "ok"),
    ("CrowdStrike",    "greenhouse", "crowdstrike",     1, "remote"),  # HQ Austin
    ("Procore",        "greenhouse", "procore",         1, "remote"),  # Austin office
    ("SailPoint",      "greenhouse", "sailpoint",       1, "remote"),  # HQ Austin
    ("Hyperion",       "greenhouse", "hyperion",        2, "ok"),
    ("Spredfast",      "greenhouse", "spredfast",       2, "ok"),
    ("Drillinginfo",   "greenhouse", "drillinginfo",    2, "ok"),
    ("Keller Williams","greenhouse", "kellerwilliams",  0, "hybrid"),  # HQ Austin
    ("Upstart",      "greenhouse", "upstart",         1, "remote"),  # AI lending, Austin office
    ("Motive",       "greenhouse", "gomotive",         1, "remote"),  # fleet mgmt, Austin office
    ("Bestow",       "greenhouse", "bestow",           2, "ok"),      # insurance tech, Austin
    ("Cloudera",     "greenhouse", "cloudera",         1, "remote"),  # data platform
    ("Blackbaud",    "greenhouse", "blackbaud",        2, "ok"),      # nonprofit software
    ("Striveworks",  "greenhouse", "striveworks",      2, "ok"),      # AI/ML, Austin
    ("Vrbo",         "greenhouse", "vrbo",             1, "remote"),  # Expedia subsidiary
    ("Opcity",       "greenhouse", "opcity",           2, "ok"),      # real estate, Austin
    ("Apptronik",    "greenhouse", "apptronik",        2, "ok"),      # robotics, Austin
    ("Iodine",       "greenhouse", "iodinellc",        2, "ok"),      # healthcare AI, Austin
    ("Modernizing",  "greenhouse", "modernizemedicine",2, "ok"),      # health IT

    # Eightfold AI career sites
    # Format: ("Company", "eightfold", "subdomain|domain", tier, pref)
    ("American Express", "eightfold", "aexp|aexp.com",          0, "hybrid"),
    # Cisco redirects to careers.cisco.com which uses Workday
    ("Cisco",            "workday",   None,                      0, "hybrid"),
    ("Johnson & Johnson","eightfold", "jnj|jnj.com",            2, "ok"),
    ("Walmart",          "eightfold", "walmart|walmart.com",     2, "ok"),
    ("Target",           "eightfold", "target|target.com",       2, "ok"),

]

# Auto-split used by run_scraper.py
SCRAPEABLE = [
    c for c in COMPANIES
    if c[1] in ("greenhouse", "lever", "ashby", "smartrecruiters",
                "workable", "jazz", "eightfold")
    and c[2] is not None
    or c[1] == "workday"
]
WORKDAY     = [c for c in COMPANIES if c[1] == "workday"]
CUSTOM_SKIP = [c for c in COMPANIES if c[1] == "custom"]
