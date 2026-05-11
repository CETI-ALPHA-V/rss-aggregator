import re
import requests
from bs4 import BeautifulSoup
from feeds.cache import is_feed_stale, save_articles, mark_feed_fetched
from config import CACHE_TTL_SECONDS


def _parse_anthropic_date(raw: str) -> str:
    """Convert 'Apr 16, 2026' to ISO8601."""
    try:
        from datetime import datetime
        return datetime.strptime(raw.strip(), "%b %d, %Y").strftime("%Y-%m-%dT00:00:00Z")
    except Exception:
        return ""


def _scrape_anthropic_news(cfg: dict) -> list[dict]:
    try:
        resp = requests.get(cfg["url"], timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Cards are <a href="/news/slug"> elements containing h2/h4, time, and p.body-3
    cards = [
        a for a in soup.find_all("a", href=True)
        if a["href"].startswith("/news/") and a["href"] != "/news"
    ]

    seen = set()
    articles = []
    for card in cards:
        href = card["href"]
        if href in seen:
            continue
        seen.add(href)

        link = f"https://www.anthropic.com{href}"

        # Featured layout: title in <h2>/<h4>
        title_el = card.find(["h2", "h3", "h4"])
        if not title_el:
            # List layout: title in <span class="...title...">
            title_el = card.find("span", class_=lambda c: c and "title" in c)
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        time_el = card.find("time")
        published = _parse_anthropic_date(time_el.get_text()) if time_el else ""

        # Summary only present in featured cards
        body_el = card.find("p", class_=lambda c: c and "body-3" in c)
        summary = body_el.get_text(strip=True) if body_el else ""

        articles.append({
            "feed_id": cfg["id"],
            "link": link,
            "title": title[:200],
            "summary": summary[:2000],
            "published": published,
            "platform": cfg["platform"],
            "category": cfg["category"],
            "type": cfg["type"],
        })

    return articles


_SCRAPER_MAP = {
    "anthropic_news": _scrape_anthropic_news,
}


def scrape_all(scrapers: list[dict], conn, force: bool = False, on_feed=None) -> list[dict]:
    from feeds.cache import load_articles
    results = []
    for cfg in scrapers:
        if force or is_feed_stale(conn, cfg["id"], CACHE_TTL_SECONDS):
            scrape_fn = _SCRAPER_MAP.get(cfg["id"])
            if scrape_fn:
                try:
                    articles = scrape_fn(cfg)
                    new_count = save_articles(conn, cfg["id"], articles) if articles else 0
                    mark_feed_fetched(conn, cfg["id"])
                    if on_feed:
                        on_feed(cfg["name"], new_count)
                except Exception:
                    if on_feed:
                        on_feed(cfg["name"], 0, error=True)

        results.extend(load_articles(conn, cfg["id"]))

    return results
