from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
from config import PLATFORM_COLORS


def _parse_dt(val: str):
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except Exception:
        return None


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    if df.empty:
        return df

    # Drop articles older than 2 months; keep rows with no date
    cutoff = datetime.now(timezone.utc) - timedelta(days=62)
    parsed = df["published"].apply(_parse_dt)
    df = df[(parsed.isna()) | (parsed >= cutoff)]

    if filters["categories"]:
        df = df[df["category"].isin(filters["categories"])]

    if filters["platforms"]:
        df = df[df["platform"].isin(filters["platforms"])]

    if filters["type"] != "All":
        df = df[df["type"] == filters["type"]]

    kw = filters.get("keyword", "")
    if kw:
        mask = (
            df["title"].str.contains(kw, case=False, na=False)
            | df["summary"].str.contains(kw, case=False, na=False)
        )
        df = df[mask]

    return df


def _source_domain(url: str) -> str:
    if not url:
        return ""
    try:
        host = urlparse(url).netloc.lstrip("www.")
        return host
    except Exception:
        return ""


def _badge(platform: str, source_url: str = "") -> str:
    color = PLATFORM_COLORS.get(platform, "#71717a")
    domain = _source_domain(source_url)
    label = (
        f'{platform} <span style="font-weight:400;opacity:0.6;font-size:0.79rem;">· {domain}</span>'
        if domain else platform
    )
    return (
        f'<span style="background:{color}18;color:{color};border:1px solid {color}35;'
        f'padding:3px 14px;border-radius:2px;font-size:0.82rem;font-weight:600;'
        f'letter-spacing:0.08em;font-family:\'Share Tech Mono\',monospace;">{label}</span>'
    )


def _type_pill(content_type: str) -> str:
    return (
        f'<span style="color:var(--text-dim);font-size:0.72rem;letter-spacing:0.1em;'
        f'font-family:\'Share Tech Mono\',monospace;text-transform:uppercase;">{content_type}</span>'
    )


def _format_date(published: str) -> str:
    if not published:
        return ""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return published[:10]


_CARD_CSS = """
<style>
[data-testid="stPills"] button {
    background-color: var(--bg2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-dim) !important;
    border-radius: 2px !important;
    font-size: 0.8rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    transition: all 0.15s !important;
}
[data-testid="stPills"] button:hover {
    border-color: var(--teal) !important;
    color: var(--teal-lt) !important;
}
[data-testid="stPills"] button[aria-checked="true"],
[data-testid="stPills"] button[data-active="true"] {
    background-color: var(--teal-dim) !important;
    border-color: var(--teal) !important;
    color: var(--teal-hi) !important;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: var(--bg2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 2px !important;
    padding: 0.1rem 0.25rem !important;
    margin-bottom: 0.5rem !important;
    transition: border-color 0.15s;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: var(--teal) !important;
}

[data-testid="stMarkdownContainer"] a {
    color: var(--text-hi) !important;
    text-decoration: none !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
}
[data-testid="stMarkdownContainer"] a:hover {
    color: var(--teal-hi) !important;
}

[data-testid="stMarkdownContainer"] strong {
    color: var(--text-hi) !important;
    font-size: 0.9rem !important;
}

[data-testid="stCaptionContainer"] p {
    color: var(--text) !important;
    font-size: 0.82rem !important;
    line-height: 1.6 !important;
}

[data-testid="stAppViewBlockContainer"] > div > [data-testid="stCaptionContainer"] p {
    color: var(--text-dim) !important;
    font-size: 0.78rem !important;
}
</style>
"""


_PAGE_SIZE = 50


def render_articles(df: pd.DataFrame) -> None:
    st.markdown(_CARD_CSS, unsafe_allow_html=True)

    if df.empty:
        render_empty_state()
        return

    df = df.sort_values("published", ascending=False, na_position="last").reset_index(drop=True)

    # Reset page when the filtered result set changes
    result_key = f"{len(df)}_{df['link'].iloc[0] if len(df) else ''}"
    if st.session_state.get("_articles_key") != result_key:
        st.session_state["_articles_key"] = result_key
        st.session_state["_articles_page"] = 1

    page = st.session_state.get("_articles_page", 1)
    show_n = page * _PAGE_SIZE
    display_df = df.iloc[:show_n]

    for _, row in display_df.iterrows():
        title = row.get("title") or "(no title)"
        link = row.get("link") or ""
        summary = row.get("summary") or ""
        platform = row.get("platform") or ""
        content_type = row.get("type") or ""
        date_str = _format_date(row.get("published") or "")

        with st.container(border=True):
            header_html = (
                f'{_badge(platform, link)}&nbsp;&nbsp;{_type_pill(content_type)}'
                f'<span style="float:right;color:var(--text-dim);font-size:0.72rem;'
                f'letter-spacing:0.1em;font-family:\'Share Tech Mono\',monospace;">{date_str}</span>'
            )
            st.markdown(header_html, unsafe_allow_html=True)

            if link:
                st.markdown(f"**[{title}]({link})**")
            else:
                st.markdown(f"**{title}**")

            if summary:
                display = summary[:600] + ("…" if len(summary) > 600 else "")
                st.caption(display)

    remaining = len(df) - show_n
    if remaining > 0:
        if st.button(f"Load {min(_PAGE_SIZE, remaining)} more  ({remaining} remaining)", key="load_more_btn"):
            st.session_state["_articles_page"] = page + 1
            st.rerun()


def render_empty_state() -> None:
    st.info("No articles match your filters. Try adjusting the sidebar or refreshing.")
