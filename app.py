import os
import datetime as _dt
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from config import FEEDS, SCRAPERS, DB_PATH, CACHE_TTL_SECONDS
from feeds.cache import init_db, is_feed_stale, get_all_cached, last_fetch_time
from feeds.fetcher import fetch_all
from feeds.scraper import scrape_all
from ui.sidebar import render_sidebar
from ui.feed_view import apply_filters, render_articles, _format_date

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

:root {
    --bg:          #080e16;
    --bg2:         #0e1a26;
    --bg3:         #152030;
    --teal:        #5c9db0;
    --teal-lt:     #88b7b8;
    --teal-hi:     #b0e1d8;
    --teal-dim:    rgba(136,183,184,0.11);
    --teal-glow:   rgba(136,183,184,0.24);
    --gold:        #d6ad5e;
    --gold-lt:     #f2d96e;
    --gold-dim:    rgba(214,173,94,0.11);
    --orange:      #f9a560;
    --amber:       #b6872c;
    --text:        #92acbd;
    --text-hi:     #b2cad6;
    --text-dim:    #3a5060;
    --green:       #21a559;
    --red:         #ec4f4f;
    --red-dk:      #a11212;
    --border:      rgba(92,157,176,0.22);
    --border-hi:   rgba(92,157,176,0.50);
}

.stApp {
    background-color: var(--bg) !important;
    background-image:
        linear-gradient(rgba(136,183,184,0.022) 1px, transparent 1px),
        linear-gradient(90deg, rgba(136,183,184,0.022) 1px, transparent 1px);
    background-size: 48px 48px;
    color: var(--text) !important;
}

.stApp::after {
    content: "";
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 3px,
        rgba(0,0,0,0.09) 3px,
        rgba(0,0,0,0.09) 4px
    );
    pointer-events: none;
    z-index: 9998;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse at 8% 0%,  rgba(136,183,184,0.06) 0%, transparent 48%),
        radial-gradient(ellipse at 92% 100%, rgba(14,60,100,0.08) 0%, transparent 48%);
}

*, *::before, *::after {
    font-family: 'Share Tech Mono', 'Lucida Console', 'Courier New', monospace !important;
    letter-spacing: 0.04em;
}

h2, h3, h4 {
    color: var(--gold) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.14em !important;
}

p, .stMarkdown, [data-testid="stMarkdownContainer"] p {
    color: var(--text) !important;
}

.expanse-banner {
    position: relative;
    border: 1px solid var(--teal);
    background: linear-gradient(100deg, rgba(136,183,184,0.07) 0%, transparent 65%);
    padding: 0.9rem 1.4rem 0.8rem;
    margin-bottom: 1.4rem;
}
.expanse-banner::before, .expanse-banner::after {
    content: "";
    position: absolute;
    width: 12px; height: 12px;
    border-color: var(--teal-hi);
    border-style: solid;
}
.expanse-banner::before { top: -2px; left: -2px; border-width: 2px 0 0 2px; }
.expanse-banner::after  { bottom: -2px; right: -2px; border-width: 0 2px 2px 0; }
.banner-meta {
    display: flex;
    justify-content: space-between;
    color: var(--text-dim);
    font-size: 0.68rem;
    letter-spacing: 0.16em;
    margin-bottom: 0.3rem;
    text-transform: uppercase;
}
.banner-online { color: var(--green); }
.banner-title {
    color: var(--gold-lt);
    font-size: 1.45rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    text-shadow: 0 0 24px rgba(242,217,110,0.35);
    line-height: 1.2;
}
.banner-sub {
    color: var(--text-dim);
    font-size: 0.67rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-top: 0.2rem;
}

[data-testid="stHeader"] {
    background: linear-gradient(180deg, #0b1620 0%, transparent 100%) !important;
    border-bottom: 1px solid var(--border) !important;
}

[data-testid="stMainBlockContainer"] {
    padding-top: 5rem !important;
}

button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: transparent !important;
    border: 1px solid var(--teal-lt) !important;
    color: var(--teal-lt) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    box-shadow: 0 0 8px rgba(136,183,184,0.13) !important;
    transition: all 0.15s !important;
    border-radius: 2px !important;
}
button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    background: var(--teal-glow) !important;
    box-shadow: 0 0 18px rgba(176,225,216,0.30) !important;
}

button[kind="secondary"],
[data-testid="stBaseButton-secondary"] {
    background: transparent !important;
    border: 1px solid var(--border-hi) !important;
    color: var(--text) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    border-radius: 2px !important;
    transition: all 0.15s !important;
}
button[kind="secondary"]:hover,
[data-testid="stBaseButton-secondary"]:hover {
    background: var(--teal-dim) !important;
    border-color: var(--teal) !important;
    color: var(--teal-lt) !important;
}

[data-testid="stDownloadButton"] button {
    border-color: var(--gold) !important;
    color: var(--gold) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    border-radius: 2px !important;
    background: transparent !important;
    transition: all 0.15s !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: var(--gold-dim) !important;
    box-shadow: 0 0 12px rgba(214,173,94,0.25) !important;
    color: var(--gold-lt) !important;
}

[data-testid="stWidgetLabel"] p, label {
    color: var(--text-dim) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    font-size: 0.76rem !important;
}

[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
    background: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    border-radius: 2px !important;
    color: var(--text-hi) !important;
}
[data-testid="stSelectbox"] svg,
[data-testid="stMultiSelect"] svg { fill: var(--teal) !important; }
li[role="option"]:hover { background: var(--teal-dim) !important; }
li[role="option"][aria-selected="true"] {
    background: rgba(136,183,184,0.16) !important;
    color: var(--teal-hi) !important;
}

[data-testid="stRadio"] [data-baseweb="radio"] div { border-color: var(--teal) !important; }
[data-testid="stRadio"] label span { color: var(--text) !important; }

[data-testid="stAlert"] {
    background: var(--bg3) !important;
    border-radius: 2px !important;
    color: var(--text) !important;
}
[data-testid="stAlert"][data-baseweb="notification"][kind="info"]     { border-left: 3px solid var(--teal) !important; }
[data-testid="stAlert"][data-baseweb="notification"][kind="positive"] { border-left: 3px solid var(--green) !important; }
[data-testid="stAlert"][data-baseweb="notification"][kind="warning"]  { border-left: 3px solid var(--gold) !important; }
[data-testid="stAlert"][data-baseweb="notification"][kind="negative"] { border-left: 3px solid var(--red) !important; }

hr { border-color: var(--border) !important; }

.stCaption, [data-testid="stCaptionContainer"] { color: var(--text-dim) !important; }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg2); }
::-webkit-scrollbar-thumb { background: rgba(92,157,176,0.32); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--teal-lt); }
</style>
"""

_HEADER_HTML = """
<div class="expanse-banner">
    <div class="banner-title">NEWS PULSE</div>
    <div class="banner-sub">FEED AGGREGATOR &nbsp;&middot;&nbsp; RSS &amp; SCRAPER</div>
</div>
"""

st.set_page_config(
    page_title="News Pulse",
    page_icon="⚡",
    layout="wide",
)

st.markdown(_CSS, unsafe_allow_html=True)

os.makedirs("data", exist_ok=True)

if "db_conn" not in st.session_state:
    st.session_state["db_conn"] = init_db(DB_PATH)

conn = st.session_state["db_conn"]

# ── 1. Load from DuckDB (no network) so sidebar has stable options ──────────
all_feed_ids = [f["id"] for f in FEEDS] + [s["id"] for s in SCRAPERS]
cached_df = get_all_cached(conn, all_feed_ids)

ts = last_fetch_time(conn)
last_refreshed = _dt.datetime.fromtimestamp(ts).strftime("%d %b %Y") if ts else "—"

# ── 2. Sidebar (always same widgets in same order) ───────────────────────────
# Use the filtered count from the previous rerun so the metric matches what's shown.
# Falls back to raw DB count on very first load, then stays accurate.
_sidebar_count = st.session_state.get("_filtered_count", len(cached_df))
filters = render_sidebar(cached_df, article_count=_sidebar_count, last_refreshed=last_refreshed)

if filters["refresh_ms"] > 0:
    st_autorefresh(interval=filters["refresh_ms"], key="autorefresh")

# ── 3. Header ────────────────────────────────────────────────────────────────
st.markdown(_HEADER_HTML, unsafe_allow_html=True)

# ── 4. Progress bar slot (always present, hidden when idle) ──────────────────
force = st.session_state.pop("force_refresh", False)
all_stale = [
    f for f in FEEDS + SCRAPERS
    if force or is_feed_stale(conn, f["id"], CACHE_TTL_SECONDS)
]
total_stale = len(all_stale)

progress_bar = st.empty()

if total_stale:
    progress_bar.progress(0, text=f"Fetching 0 / {total_stale} sources…")
    completed = [0]

    def _on_feed(name, new_count, error=False):
        completed[0] += 1
        pct = completed[0] / total_stale
        label = f"{'⚠ ' if error else ''}Fetching {name}… ({completed[0]} / {total_stale})"
        progress_bar.progress(pct, text=label)

    fetch_all(FEEDS, conn, force=force, on_feed=_on_feed)
    scrape_all(SCRAPERS, conn, force=force, on_feed=_on_feed)

    progress_bar.progress(1.0, text=f"✓ Updated {completed[0]} sources")
    import time as _t; _t.sleep(0.8)
    progress_bar.empty()

# ── 5. Reload fresh data from DuckDB, apply filters, render ─────────────────
df = get_all_cached(conn, all_feed_ids)
filtered_df = apply_filters(df, filters)
st.session_state["_filtered_count"] = len(filtered_df)

latest = df["published"].dropna().max() if not df.empty else ""
last_item = f" · Last item: {_format_date(latest)}" if latest else ""
st.caption(f"{len(filtered_df)} article{'s' if len(filtered_df) != 1 else ''}{last_item}")

render_articles(filtered_df)
