import re
import time
import feedparser
import requests
import pandas as pd
from feeds.cache import is_feed_stale, save_articles, mark_feed_fetched, get_all_cached
from config import CACHE_TTL_SECONDS

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RSSBot/1.0)"}


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", " ", text).strip()


def _normalize_date(entry) -> str:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return time.strftime("%Y-%m-%dT%H:%M:%SZ", t)
            except Exception:
                pass
    return ""


def fetch_feed(feed_cfg: dict) -> list[dict]:
    resp = requests.get(feed_cfg["url"], timeout=15, headers=_HEADERS)
    resp.raise_for_status()
    parsed = feedparser.parse(resp.content)
    articles = []
    for entry in parsed.entries:
        summary = _strip_html(
            getattr(entry, "summary", "") or getattr(entry, "content", [{}])[0].get("value", "")
        )
        articles.append({
            "feed_id": feed_cfg["id"],
            "link": getattr(entry, "link", ""),
            "title": _strip_html(getattr(entry, "title", "(no title)")),
            "summary": summary[:2000],
            "published": _normalize_date(entry),
            "platform": feed_cfg["platform"],
            "category": feed_cfg["category"],
            "type": feed_cfg["type"],
        })
    return articles


def fetch_all(feeds: list[dict], conn, force: bool = False, on_feed=None) -> pd.DataFrame:
    for feed_cfg in feeds:
        if force or is_feed_stale(conn, feed_cfg["id"], CACHE_TTL_SECONDS):
            try:
                articles = fetch_feed(feed_cfg)
                new_count = save_articles(conn, feed_cfg["id"], articles) if articles else 0
                mark_feed_fetched(conn, feed_cfg["id"])
                if on_feed:
                    on_feed(feed_cfg["name"], new_count)
            except Exception:
                if on_feed:
                    on_feed(feed_cfg["name"], 0, error=True)

    feed_ids = [f["id"] for f in feeds]
    return get_all_cached(conn, feed_ids)
