import time
import duckdb
import pandas as pd


def init_db(db_path: str) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            feed_id   VARCHAR,
            link      VARCHAR,
            title     VARCHAR,
            summary   VARCHAR,
            published VARCHAR,
            platform  VARCHAR,
            category  VARCHAR,
            type      VARCHAR,
            PRIMARY KEY (feed_id, link)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fetch_log (
            feed_id    VARCHAR PRIMARY KEY,
            fetched_at DOUBLE
        )
    """)
    return conn


def is_feed_stale(conn, feed_id: str, ttl: int) -> bool:
    row = conn.execute(
        "SELECT fetched_at FROM fetch_log WHERE feed_id = ?", [feed_id]
    ).fetchone()
    if row is None:
        return True
    return (time.time() - row[0]) > ttl


def save_articles(conn, feed_id: str, articles: list[dict]) -> int:
    """Insert new articles, skip duplicates. Returns count of newly inserted rows."""
    if not articles:
        return 0
    rows = [
        [a["feed_id"], a["link"], a["title"], a["summary"],
         a["published"], a["platform"], a["category"], a["type"]]
        for a in articles
    ]
    before = conn.execute("SELECT COUNT(*) FROM articles WHERE feed_id = ?", [feed_id]).fetchone()[0]
    conn.executemany("""
        INSERT INTO articles (feed_id, link, title, summary, published, platform, category, type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (feed_id, link) DO UPDATE SET
            title    = excluded.title,
            summary  = excluded.summary,
            published = excluded.published
    """, rows)
    after = conn.execute("SELECT COUNT(*) FROM articles WHERE feed_id = ?", [feed_id]).fetchone()[0]
    return after - before


def mark_feed_fetched(conn, feed_id: str) -> None:
    conn.execute("""
        INSERT INTO fetch_log (feed_id, fetched_at) VALUES (?, ?)
        ON CONFLICT (feed_id) DO UPDATE SET fetched_at = excluded.fetched_at
    """, [feed_id, time.time()])


def load_articles(conn, feed_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT feed_id, link, title, summary, published, platform, category, type "
        "FROM articles WHERE feed_id = ?",
        [feed_id]
    ).fetchall()
    cols = ["feed_id", "link", "title", "summary", "published", "platform", "category", "type"]
    return [dict(zip(cols, r)) for r in rows]


def get_all_cached(conn, feed_ids: list[str]) -> pd.DataFrame:
    if not feed_ids:
        return pd.DataFrame(columns=["feed_id","link","title","summary","published","platform","category","type"])
    placeholders = ", ".join("?" * len(feed_ids))
    return conn.execute(
        f"SELECT feed_id, link, title, summary, published, platform, category, type "
        f"FROM articles WHERE feed_id IN ({placeholders}) ORDER BY published DESC",
        feed_ids
    ).df()


def last_fetch_time(conn) -> float:
    row = conn.execute("SELECT MAX(fetched_at) FROM fetch_log").fetchone()
    return row[0] if row and row[0] else 0.0
