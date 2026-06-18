import streamlit as st
import pandas as pd

REFRESH_OPTIONS = {
    "Off": 0,
    "5 min": 5 * 60 * 1000,
    "15 min": 15 * 60 * 1000,
    "30 min": 30 * 60 * 1000,
    "60 min": 60 * 60 * 1000,
}

DATE_RANGE_OPTIONS = {
    "Today": 1,
    "Last 7 days": 7,
    "Last 30 days": 30,
    "Last 60 days": 60,
    "All time": None,
}

_SIDEBAR_CSS = """
<style>
[data-testid="stSidebar"] {
    background-color: var(--bg2) !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] h1 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--teal-lt);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 0;
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: var(--text-dim) !important;
    font-size: 0.75rem;
}

[data-testid="stSidebar"] hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 0.5rem 0;
}

[data-testid="stSidebar"] .stRadio label p,
[data-testid="stSidebar"] .stSelectbox label p,
[data-testid="stSidebar"] .stMultiSelect label p {
    font-size: 0.7rem !important;
    font-weight: 500 !important;
    color: var(--text-dim) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
}

[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: transparent !important;
    border: 1px solid var(--teal-lt) !important;
    color: var(--teal-lt) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    box-shadow: 0 0 8px rgba(136,183,184,0.13) !important;
    border-radius: 2px !important;
    font-size: 0.82rem;
    transition: all 0.15s;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: var(--teal-glow) !important;
    box-shadow: 0 0 18px rgba(176,225,216,0.30) !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background-color: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    border-radius: 2px !important;
    box-shadow: none !important;
    color: var(--text-hi) !important;
}

[data-testid="stSidebar"] [data-baseweb="tag"] {
    background-color: var(--teal-dim) !important;
    color: var(--teal-lt) !important;
    border-radius: 2px !important;
    font-size: 0.72rem !important;
    border: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] span[role="presentation"] svg {
    fill: var(--teal) !important;
}

[data-testid="stSidebar"] [data-baseweb="menu"] {
    background-color: var(--bg2) !important;
    border: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] [data-baseweb="menu"] li {
    color: var(--text) !important;
    font-size: 0.82rem !important;
}
[data-testid="stSidebar"] [data-baseweb="menu"] li:hover,
[data-testid="stSidebar"] [data-baseweb="menu"] [aria-selected="true"] {
    background-color: var(--teal-dim) !important;
}
[data-testid="stSidebar"] [data-baseweb="menu"] svg {
    fill: var(--teal) !important;
}

[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
    font-size: 0.82rem !important;
    color: var(--text) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

[data-testid="stSidebar"] .stRadio div[data-baseweb="radio"] div {
    background-color: var(--teal) !important;
    border-color: var(--teal) !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] span {
    color: var(--text) !important;
    font-size: 0.82rem !important;
}

[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 2px;
    padding: 0.5rem 0.75rem;
}
[data-testid="stSidebar"] [data-testid="stMetricLabel"] p {
    font-size: 0.68rem !important;
    color: var(--text-dim) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: var(--teal-lt) !important;
}
</style>
"""


def render_sidebar(df: pd.DataFrame, article_count: int = 0, last_refreshed: str = "") -> dict:
    with st.sidebar:
        st.markdown(_SIDEBAR_CSS, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        col1.metric("Articles", article_count)
        col2.metric("Refreshed", last_refreshed or "—")
        st.divider()

        if st.button("Refresh Now", use_container_width=True, type="primary", key="btn_refresh"):
            st.session_state["force_refresh"] = True
            st.rerun()

        interval_label = st.selectbox(
            "Auto-refresh",
            options=list(REFRESH_OPTIONS.keys()),
            index=0,
            key="sel_interval",
        )

        content_type = st.radio(
            "Content type", options=["All", "blog", "releases"],
            horizontal=True, key="filter_type",
        )

        date_label = st.selectbox(
            "Date range",
            options=list(DATE_RANGE_OPTIONS.keys()),
            index=2,  # default: Last 30 days
            key="sel_date_range",
        )

        st.divider()

        all_categories = sorted(df["category"].dropna().unique().tolist()) if not df.empty else []
        all_platforms = sorted(df["platform"].dropna().unique().tolist()) if not df.empty else []

        # Seed session state once so user selections survive reruns.
        # Without explicit keys + session state, multiselect resets to `default`
        # on every rerun, creating an apparent re-running loop.
        if "filter_categories" not in st.session_state:
            st.session_state["filter_categories"] = all_categories
        if "filter_platform" not in st.session_state:
            st.session_state["filter_platform"] = "All"

        # Drop any stored values that no longer exist in options (e.g. feed removed)
        st.session_state["filter_categories"] = [
            c for c in st.session_state["filter_categories"] if c in all_categories
        ]
        if st.session_state["filter_platform"] not in ["All"] + all_platforms:
            st.session_state["filter_platform"] = "All"

        categories = st.multiselect("Category", options=all_categories, key="filter_categories")
        platform = st.selectbox("Platform", options=["All"] + all_platforms, key="filter_platform")

    return {
        "categories": categories,
        "platforms": [platform] if platform != "All" else all_platforms,
        "type": content_type,
        "keyword": "",
        "refresh_ms": REFRESH_OPTIONS[interval_label],
        "days": DATE_RANGE_OPTIONS[date_label],
    }
