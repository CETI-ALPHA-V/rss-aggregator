# m[AI]ntain

A news and release-notes aggregator for AI, data, cloud and marketing tools. It pulls from 86 RSS feeds, 19 official YouTube channels and a custom scraper, caches everything in DuckDB, and serves it through a web app with three pages:

- **Feed** — searchable, filterable article list grouped by day
- **AI Benchmarks** — live LLM leaderboard from LiveBench with a quality-vs-cost chart, sortable table and side-by-side comparison
- **Digest** — turn any filtered slice of the feed into an Outlook email, Teams post or plain-text summary

The web app is a **FastAPI** backend (`api/`) plus a **React + Tailwind** frontend (`web/`). The original Streamlit app (`app.py`) still works and shares the same feed code and database — see [Legacy Streamlit app](#legacy-streamlit-app).

---

## Running

### One-time setup

```bash
pip install -r requirements.txt
cd web && npm install && cd ..
```

### Production-style (one server)

Build the frontend once, then FastAPI serves both the API and the UI:

```bash
cd web && npm run build && cd ..
python3 -m uvicorn api.main:app --port 8000
```

Open http://localhost:8000.

### Development (hot reload)

Run the API and the Vite dev server side by side — Vite proxies `/api` to port 8000:

```bash
python3 -m uvicorn api.main:app --port 8000 --reload
```

```bash
cd web && npm run dev
```

Open http://localhost:5173.

### Notes

- **Feeds refresh in the background.** On startup the server fetches any feed older than 30 minutes, then re-checks every 30 minutes. Pages always load instantly from the cache; the header shows refresh progress, and the refresh button forces a full re-fetch.
- **Only one app at a time per database.** DuckDB allows a single writer, so stop the Streamlit app before starting the API (or vice versa). To run both, point the API at a different file with `MAINTAIN_DB=path/to/other.duckdb`.
- `MAINTAIN_NO_REFRESH=1` starts the API without the background fetcher (useful against a copied database).
- `.claude/launch.json` defines a `maintain` server for starting it from the Claude desktop app's preview pane.

---

## Files

| Path | Purpose |
|---|---|
| `api/main.py` | FastAPI app — JSON endpoints, filtering in SQL, serves `web/dist` with SPA fallback |
| `api/refresher.py` | Background thread that fetches feeds on startup and every `CACHE_TTL_SECONDS` |
| `api/benchmarks.py` | Fetches the newest LiveBench release, computes overall score and cost per task, cross-references open-weight models with Hugging Face, caches it in `data/livebench.json` |
| `digest.py` | Framework-free digest generators (Outlook HTML, Teams markdown, plain text), shared by both apps |
| `web/src/pages/` | `FeedPage`, `BenchmarksPage`, `DigestPage` |
| `web/src/components/` | App shell (`Layout`), shared UI primitives (`ui.tsx`), `PlatformPicker` |
| `web/src/lib/` | API types + fetch hook, URL↔filter state, formatting, theme, refresh status |
| `config.py` | Feed and scraper definitions, platform colours, cache TTL, DB path, `MODEL_SOURCES`, offline benchmark fallback (`LLM_INVENTORY`) |
| `feeds/fetcher.py` | RSS fetching via `feedparser`, HTML stripping, date normalisation |
| `feeds/cache.py` | DuckDB layer — `articles` + `fetch_log` tables, upsert on conflict |
| `feeds/scraper.py` | Custom HTML scrapers for sites without RSS (Anthropic News) |
| `app.py`, `ui/` | Legacy Streamlit app |
| `test_filters.py` | Tests for the Streamlit app's `apply_filters` |
| `data/feeds.duckdb` | Article cache (auto-created, not committed) |

---

## API

All endpoints are `GET` unless noted. Article endpoints accept the same filters: repeatable `category` and `platform`, `type` (`blog` / `releases` / `video`), `days`, and `q` (case-insensitive substring of title or summary). Articles without a date are always included.

| Endpoint | Returns |
|---|---|
| `/api/meta` | Categories, platforms (with colour and article count), totals, last refresh time |
| `/api/articles?…&limit=50&offset=0` | `{ total, items }`, newest first (limit ≤ 200) |
| `/api/digest?…&limit=25` | `{ subject, count, total, html, teams, text }` (limit ≤ 500) |
| `/api/benchmarks` | Latest LiveBench release: categories (with weights), models with scores and cost per task, Hugging Face stats for open-weight models (`hf`), `live` flag, provider colours |
| `/api/tool-releases` | Latest `releases` article per `MODEL_SOURCES` platform |
| `/api/status` | Background refresh progress (`running`, `done`, `total`, `errors`, …) |
| `POST /api/refresh` | Starts a full feed re-fetch (no-op if one is already running) and re-checks LiveBench |

Interactive docs: http://localhost:8000/docs.

---

## Web app

- **Feed** — one tab per category (with article counts for the current filters), search, a multi-select platform picker scoped to the active tab, date range (today / 7 / 30 / 60 days / all), content type (blog / releases / videos, with thumbnails for videos), list or card layout, grouped by day, 50 at a time with "Load more". Filters live in the URL, so any view can be bookmarked or shared, and **Create digest** carries them to the Digest page.
- **AI Benchmarks** (`/benchmarks`; the old `/models` link redirects) — headline tiles (top overall, best value among models within 10% of the top score, top open-weights, top in LiveBench's most heavily weighted category), a log-scale quality-vs-cost scatter chart, a sortable leaderboard with the top three per column highlighted, a radar + table comparison of up to three models, and a Hugging Face column (monthly downloads + licence). An **Open-weight models on Hugging Face** panel puts each open model's LiveBench score beside its downloads, likes, size, licence, last update and the other benchmark results Hugging Face lists for it. Below it, the latest SDK/CLI release from each AI provider's feeds.
- **Digest** — choose date range, type, categories, platforms and max articles; preview the Outlook email (rendered in a sandboxed frame), then copy as rich text, copy Teams markdown or plain text, or download `.html` / `.txt`.
- Dark mode by default, with a light-mode toggle in the header (the choice is remembered per browser); responsive down to phone width.

---

## Feed Categories

| Category | Platforms |
|---|---|
| AI | Anthropic, OpenAI, Google, Google DeepMind, NVIDIA, Hugging Face, Ollama, LangChain, LlamaIndex, vLLM, Mistral AI, Microsoft Foundry, AWS, Simon Willison |
| Cloud | AWS, Google Cloud, Azure, Cloudflare, Kubernetes, HashiCorp, Docker |
| Data Tools | Snowflake, dbt, Databricks, DuckDB, MotherDuck, MongoDB, Redis, PostgreSQL, ClickHouse, Confluent, Microsoft Fabric, Power BI, Apache Iceberg, Delta Lake, Polars, pandas, Airbyte, Streamlit, Python, Apache Spark |
| Orchestration | Apache Airflow, Prefect, Dagster, Astronomer, Temporal, Kestra, GitHub |
| Marketing | Google Ads, Google Marketing Platform, Google Search Central, Search Engine Journal, Amazon Ads, Meta, Pinterest, Microsoft Ads, TikTok, LinkedIn |

Total: 86 RSS feeds + 19 YouTube channels + 1 custom scraper (Anthropic News, which has no RSS).

**YouTube channels** (type `video`): Anthropic, OpenAI, Google DeepMind, Google for Developers, Hugging Face, LangChain, NVIDIA Developer, Databricks, Snowflake, dbt Labs, Google Cloud Tech, Microsoft Azure, AWS Developers, GitHub, Astronomer, Google Ads, Amazon Ads, Microsoft Advertising, LinkedIn. Each channel's feed carries its 15 most recent videos; the web app shows a thumbnail for each.

---

## Config (`config.py`)

Each entry in `FEEDS` has:

```python
{
    "id":       "unique_string",   # used as primary key in DuckDB
    "name":     "Display Name",
    "url":      "https://...",
    "category": "AI",              # AI | Cloud | Data Tools | Orchestration | Marketing
    "platform": "Anthropic",       # used for colour + filter
    "type":     "blog",            # blog | releases | video
}
```

To add a YouTube channel, add a `_youtube(feed_id, name, channel_id, category, platform)` line to the list at the end of `FEEDS`. The channel ID (starts with `UC`, 24 characters) is in the page source of the channel's `youtube.com/@handle` page — check that `https://www.youtube.com/feeds/videos.xml?channel_id=<id>` returns the right channel before adding it.

`SCRAPERS` uses the same shape. Add a matching function in `feeds/scraper.py` and register it in `_SCRAPER_MAP`.

Changing a feed's `category`, `platform` or `type` applies to already-cached articles too: both apps re-sync those columns from config on startup.

`CACHE_TTL_SECONDS = 1800` — feeds older than 30 minutes are re-fetched.

`PLATFORM_COLORS` — colour per platform/provider, used for avatars, chips and chart points.

`MODEL_SOURCES` — one entry per AI platform with a hand-curated current flagship `model` and `notes`, joined against the newest cached `releases` article for that platform (an SDK/CLI version, not a model version).

**Benchmarks are live.** `api/benchmarks.py` reads LiveBench's release list and model names/organisations from its site bundle, downloads the newest release's `table.csv`, `categories.json` and `cost.csv`, and computes the overall score (LiveBench's weighted average) and cost per successful task exactly as the site does. For the open-weight models LiveBench links to Hugging Face, it also pulls downloads (last 30 days), likes, licence, parameter count, last update and Hugging Face's listed eval results from the public Hugging Face API (no key needed). It re-checks daily (and when you press refresh) and caches the result in `data/livebench.json`. Columns follow whatever categories LiveBench publishes, so a new benchmark version needs no code change. If LiveBench can't be reached the last cached release is shown; with no cache at all, the page falls back to `LLM_INVENTORY`, an old hand-copied snapshot, and says so.

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

## Legacy Streamlit app

```bash
streamlit run app.py
```

Runs at http://localhost:8501. Same data and features in the original dark "terminal" styling: Feed and Model Updates tabs, sidebar filters, and a Share Digest dialog built on the same `digest.py`. It fetches stale feeds on page load rather than in the background. To retire it, delete `app.py`, `ui/`, `test_filters.py`, `.streamlit/` and the `streamlit` / `streamlit-autorefresh` lines in `requirements.txt` — nothing in `api/` or `web/` depends on them.

> The committed `.venv/` is a Windows virtualenv and won't run on macOS; use your system or conda Python.
