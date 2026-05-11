# Pulse

A Streamlit RSS aggregator styled after *The Expanse* UI aesthetic. Fetches articles and release notes from ~38 RSS feeds plus a custom scraper, caches them in DuckDB, and displays them in a filterable card feed.

---

## Files

| File | Purpose |
|---|---|
| `app.py` | Entry point — orchestrates fetch cycle, header, sidebar, article rendering |
| `config.py` | All feed definitions, scraper definitions, platform colour map, cache TTL, DB path |
| `feeds/fetcher.py` | RSS fetching via `feedparser`, HTML stripping, date normalisation |
| `feeds/cache.py` | DuckDB layer — `articles` + `fetch_log` tables, upsert on conflict |
| `feeds/scraper.py` | Custom HTML scrapers for sites without RSS (Anthropic News) |
| `ui/sidebar.py` | Category / Platform / Content Type filters, auto-refresh selector, Refresh Now button |
| `ui/feed_view.py` | Article card layout, platform badges, pagination (50/page), `apply_filters` |
| `requirements.txt` | Python dependencies |
| `.streamlit/config.toml` | Streamlit server config (port 8501, dark base theme) |
| `data/feeds.duckdb` | Persisted article cache (auto-created, not committed) |

---

## Running

```bash
# Install dependencies (one-time)
pip install -r requirements.txt

# Start the app
streamlit run app.py
```

App runs at http://localhost:8501 (configured in `.streamlit/config.toml`).

> If running via the system conda `streamlit` rather than the project venv, make sure the following are installed in that environment:
> `pip install feedparser beautifulsoup4 requests streamlit-autorefresh`

The DuckDB file at `data/` is created automatically on first run.

---

## Feed Categories

| Category | Platforms |
|---|---|
| AI | Anthropic, OpenAI, Google, Hugging Face, Ollama, LangChain, LlamaIndex |
| Cloud | AWS, Google Cloud |
| Data Tools | Snowflake, dbt, Databricks, DuckDB, MongoDB, Redis, Apache Iceberg, Delta Lake, Polars, Airbyte |
| Orchestration | Apache Airflow, Prefect |
| Marketing | Google Ads, Amazon Ads, Meta, Pinterest |

Total: ~38 RSS feeds + 1 custom scraper (Anthropic News, which has no RSS).

---

## Feed and Scraper Config (`config.py`)

Each entry in `FEEDS` has:

```python
{
    "id":       "unique_string",   # used as primary key in DuckDB
    "name":     "Display Name",
    "url":      "https://...",
    "category": "AI",              # AI | Cloud | Data Tools | Orchestration | Marketing
    "platform": "Anthropic",       # used for badge colour + filter
    "type":     "blog",            # blog | releases
}
```

`SCRAPERS` uses the same shape. Add a matching function in `feeds/scraper.py` and register it in `_SCRAPER_MAP`.

`CACHE_TTL_SECONDS = 1800` — feeds older than 30 minutes are re-fetched on next load.

---

## Database Tables

### `articles`
Primary key: `(feed_id, link)`. On conflict, updates title, summary, and published date.

| Column | Type |
|---|---|
| `feed_id` | VARCHAR |
| `link` | VARCHAR |
| `title` | VARCHAR |
| `summary` | VARCHAR (truncated to 2000 chars) |
| `published` | VARCHAR (ISO 8601) |
| `platform` | VARCHAR |
| `category` | VARCHAR |
| `type` | VARCHAR |

### `fetch_log`
Tracks last successful fetch time per feed.

| Column | Type |
|---|---|
| `feed_id` | VARCHAR (PK) |
| `fetched_at` | DOUBLE (Unix timestamp) |

---

## UI Features

- **Sidebar filters**: Category (multi), Platform (multi), Content Type (All / blog / releases)
- **Auto-refresh**: Off / 5 / 15 / 30 / 60 min via `streamlit-autorefresh`
- **Refresh Now**: forces all feeds to re-fetch regardless of TTL
- **Pagination**: 50 articles per page, "Load more" button
- **Article age cutoff**: articles older than 62 days are excluded from the view

---

## Theme

Expanse-inspired dark UI (same palette as the Campaign Exception Logger project):

| Role | Color |
|---|---|
| Background | `#080e16` / `#0e1a26` / `#152030` |
| Primary accent (teal) | `#88b7b8` / `#b0e1d8` |
| Section headers (gold) | `#d6ad5e` / `#f2d96e` |
| Body text | `#92acbd` / `#b2cad6` |
| Success / online | `#21a559` |
| Error | `#ec4f4f` |

Font: Share Tech Mono (Google Fonts). Scanline overlay + teal grid background via CSS.

Platform badge colours are defined in `PLATFORM_COLORS` in `config.py` and are intentionally kept distinct per-platform for quick visual scanning.
