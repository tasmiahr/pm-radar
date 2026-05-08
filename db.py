import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "jobs.db"


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id           TEXT PRIMARY KEY,
            source       TEXT NOT NULL,
            company      TEXT NOT NULL,
            tier         INTEGER NOT NULL,
            work_pref    TEXT NOT NULL,
            title        TEXT NOT NULL,
            department   TEXT,
            location     TEXT,
            remote_ok    INTEGER DEFAULT 0,
            url          TEXT NOT NULL,
            posted_at    TEXT,
            days_old     INTEGER,
            hours_old    INTEGER,
            description  TEXT,
            salary       TEXT,
            ghost_risk   TEXT DEFAULT 'low',
            ghost_reason TEXT,
            first_seen   TEXT DEFAULT (datetime('now')),
            last_seen    TEXT DEFAULT (datetime('now')),
            status       TEXT DEFAULT 'new',
            match_score  INTEGER,
            notes        TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS scrape_runs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at     TEXT DEFAULT (datetime('now')),
            companies  INTEGER,
            jobs_found INTEGER,
            jobs_new   INTEGER,
            errors     TEXT
        )
    """)

    # Migrations -- safe to run on existing DB
    for col, typedef in [
        ("hours_old", "INTEGER"),
        ("salary",    "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()
    print(f"OK Database ready at {DB_PATH}")


if __name__ == "__main__":
    init_db()
