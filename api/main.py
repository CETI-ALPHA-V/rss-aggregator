import html
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

import digest
from api.benchmarks import BenchmarkStore
from api.refresher import Refresher
from config import DB_PATH, FEEDS, MODEL_SOURCES, PLATFORM_COLORS, SCRAPERS
from feeds.cache import init_db, last_fetch_time, sync_feed_metadata

_SOURCES = FEEDS + SCRAPERS
_FEED_IDS = [s["id"] for s in _SOURCES]
_COLUMNS = ["feed_id", "link", "title", "summary", "published", "platform", "category", "type"]
_WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.environ.get("MAINTAIN_DB", DB_PATH)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    app.state.conn = init_db(db_path)
    sync_feed_metadata(app.state.conn, _SOURCES)
    app.state.refresher = Refresher(app.state.conn)
    app.state.benchmarks = BenchmarkStore(Path(db_path).parent / "livebench.json")
    if os.environ.get("MAINTAIN_NO_REFRESH") != "1":
        app.state.refresher.start()
        app.state.benchmarks.start()
    yield
    app.state.refresher.stop()
    app.state.conn.close()


app = FastAPI(title="m[AI]ntain API", lifespan=lifespan)


def _cursor():
    return app.state.conn.cursor()


def _iso(ts: float | None) -> str | None:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat() if ts else None


def _where(categories: list[str], platforms: list[str], type_: str | None,
           days: int | None, q: str | None) -> tuple[str, list]:
    clauses = [f"feed_id IN ({', '.join('?' * len(_FEED_IDS))})"]
    params: list = list(_FEED_IDS)
    if categories:
        clauses.append(f"category IN ({', '.join('?' * len(categories))})")
        params += categories
    if platforms:
        clauses.append(f"platform IN ({', '.join('?' * len(platforms))})")
        params += platforms
    if type_ in ("blog", "releases", "video"):
        clauses.append("type = ?")
        params.append(type_)
    if days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        clauses.append("(published IS NULL OR published = '' OR published >= ?)")
        params.append(cutoff)
    if q and q.strip():
        needle = q.strip().lower()
        clauses.append("(contains(lower(title), ?) OR contains(lower(coalesce(summary, '')), ?))")
        params += [needle, needle]
    return " AND ".join(clauses), params


def _clean(text: str | None) -> str | None:
    # Feeds store text with HTML entities still encoded (&#8217; etc.); clients escape it themselves.
    return html.unescape(text) if text else text


def _query_articles(cur, where: str, params: list, limit: int, offset: int) -> tuple[int, list[dict]]:
    total = cur.execute(f"SELECT COUNT(*) FROM articles WHERE {where}", params).fetchone()[0]
    rows = cur.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM articles WHERE {where} "
        f"ORDER BY published DESC NULLS LAST, title LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()
    items = [dict(zip(_COLUMNS, r)) for r in rows]
    for item in items:
        item["title"] = _clean(item["title"])
        item["summary"] = _clean(item["summary"])
    return total, items


@app.get("/api/meta")
def meta():
    cur = _cursor()
    try:
        in_feeds = f"feed_id IN ({', '.join('?' * len(_FEED_IDS))})"
        counts = dict(cur.execute(
            f"SELECT platform, COUNT(*) FROM articles WHERE {in_feeds} GROUP BY platform", _FEED_IDS,
        ).fetchall())
        now = datetime.now(timezone.utc)
        iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
        # Upper bound excludes future-dated posts (e.g. announcements dated next month).
        new_24h, new_7d = cur.execute(
            f"SELECT COUNT(*) FILTER (WHERE published >= ?), COUNT(*) FILTER (WHERE published >= ?) "
            f"FROM articles WHERE {in_feeds} AND published <> '' AND published <= ?",
            [iso(now - timedelta(days=1)), iso(now - timedelta(days=7)), *_FEED_IDS, iso(now)],
        ).fetchone()
        last = last_fetch_time(cur)
    finally:
        cur.close()

    platforms: dict[str, dict] = {}
    for s in _SOURCES:
        p = platforms.setdefault(s["platform"], {
            "name": s["platform"], "categories": [],
            "color": PLATFORM_COLORS.get(s["platform"], "#71717a"),
            "articles": counts.get(s["platform"], 0),
        })
        if s["category"] not in p["categories"]:
            p["categories"].append(s["category"])

    return {
        "categories": sorted({s["category"] for s in _SOURCES}),
        "platforms": sorted(platforms.values(), key=lambda p: p["name"].lower()),
        "total_articles": sum(counts.values()),
        "new_24h": new_24h,
        "new_7d": new_7d,
        "source_count": len(_SOURCES),
        "last_refreshed": _iso(last),
    }


@app.get("/api/articles")
def articles(
    category: list[str] = Query(default=[]),
    platform: list[str] = Query(default=[]),
    type: str | None = None,
    days: int | None = Query(default=None, ge=1),
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    where, params = _where(category, platform, type, days, q)
    facet_where, facet_params = _where([], platform, type, days, q)
    cur = _cursor()
    try:
        total, items = _query_articles(cur, where, params, limit, offset)
        category_counts = dict(cur.execute(
            f"SELECT category, COUNT(*) FROM articles WHERE {facet_where} GROUP BY category", facet_params,
        ).fetchall())
    finally:
        cur.close()
    # category_counts ignores the category filter, so each tab can show its own count.
    return {"total": total, "items": items, "category_counts": category_counts}


@app.get("/api/digest")
def make_digest(
    category: list[str] = Query(default=[]),
    platform: list[str] = Query(default=[]),
    type: str | None = None,
    days: int | None = Query(default=None, ge=1),
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
):
    where, params = _where(category, platform, type, days, q)
    cur = _cursor()
    try:
        total, items = _query_articles(cur, where, params, limit, 0)
    finally:
        cur.close()
    return {
        "total": total,
        "count": len(items),
        "subject": digest.digest_subject(items),
        "html": digest.generate_email_html(items),
        "teams": digest.generate_teams_message(items),
        "text": digest.generate_email_plain(items),
    }


@app.get("/api/benchmarks")
def benchmarks():
    return {**app.state.benchmarks.get(), "colors": PLATFORM_COLORS}


@app.get("/api/tool-releases")
def tool_releases():
    cur = _cursor()
    try:
        rows = []
        for src in MODEL_SOURCES:
            latest = cur.execute(
                "SELECT title, published, link FROM articles WHERE platform = ? AND type = 'releases' "
                "ORDER BY published DESC NULLS LAST LIMIT 1",
                [src["platform"]],
            ).fetchone()
            rows.append({
                **src,
                "color": PLATFORM_COLORS.get(src["platform"], "#71717a"),
                "release": _clean(latest[0]) if latest else None,
                "released": latest[1] if latest else None,
                "link": latest[2] if latest else None,
            })
    finally:
        cur.close()
    return {"items": rows}


@app.get("/api/status")
def status():
    cur = _cursor()
    try:
        last = last_fetch_time(cur)
    finally:
        cur.close()
    state = dict(app.state.refresher.state)
    state["last_finished"] = _iso(state["last_finished"])
    return {**state, "last_refreshed": _iso(last)}


@app.post("/api/refresh", status_code=202)
def refresh():
    started = app.state.refresher.trigger()
    app.state.benchmarks.refresh_async()
    return {"started": started}


# ── Built frontend (production) ──────────────────────────────────────────────
# In dev, Vite serves the UI on :5173 and proxies /api here. After
# `npm run build`, this server also serves web/dist with SPA fallback.
@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith("api/") or not _WEB_DIST.exists():
        raise HTTPException(status_code=404)
    candidate = (_WEB_DIST / path).resolve()
    if path and candidate.is_file() and _WEB_DIST in candidate.parents:
        return FileResponse(candidate)
    return FileResponse(_WEB_DIST / "index.html")
