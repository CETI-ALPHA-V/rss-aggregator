import html

import pandas as pd
import streamlit as st

from config import LLM_INVENTORY, LLM_INVENTORY_SOURCE, MODEL_SOURCES, PLATFORM_COLORS
from ui.feed_view import _format_date

_TABLE_CSS = """
<style>
.model-table { width: 100%; border-collapse: collapse; margin-bottom: 1.2rem; }
.model-table th {
    text-align: left; color: var(--text-dim); font-size: 0.68rem;
    text-transform: uppercase; letter-spacing: 0.1em;
    border-bottom: 1px solid var(--border-hi); padding: 6px 10px;
    white-space: nowrap;
}
.model-table td {
    border-bottom: 1px solid var(--border); padding: 9px 10px;
    font-size: 0.84rem; color: var(--text-hi); vertical-align: top;
}
.model-table tr:hover td { background: var(--teal-dim); }
.model-table-scroll { overflow-x: auto; margin-bottom: 1.2rem; }
.model-table-scroll .model-table { min-width: 980px; margin-bottom: 0; }
</style>
"""


def _latest_release(df: pd.DataFrame, platform: str) -> tuple[str, str]:
    subset = df[(df["platform"] == platform) & (df["type"] == "releases")]
    if subset.empty:
        return "—", "—"
    top = subset.sort_values("published", ascending=False, na_position="last").iloc[0]
    version = html.escape((top.get("title") or "").strip() or "—")
    released = _format_date(top.get("published") or "") or "—"
    return version, released


def _tier_pill(tier: str) -> str:
    color = "var(--gold)" if tier == "Frontier" else "var(--teal-lt)"
    return (
        f'<span style="color:{color};font-weight:600;letter-spacing:0.08em;'
        f'text-transform:uppercase;font-size:0.76rem;">{html.escape(tier)}</span>'
    )


def _source_badge(platform: str) -> str:
    color = PLATFORM_COLORS.get(platform, "#71717a")
    return (
        f'<span style="background:{color}18;color:{color};border:1px solid {color}35;'
        f'padding:2px 10px;border-radius:2px;font-weight:600;font-size:0.82rem;">'
        f'{html.escape(platform)}</span>'
    )


def render_model_table(df: pd.DataFrame) -> None:
    """Shows one row per MODEL_SOURCES entry. "Model" is hand-curated in
    config.py — there's no feed that reliably announces model names, so this
    needs to be kept current by hand. "Tool/SDK Release" is derived live from
    the newest cached `type == "releases"` article for that platform (that's
    the CLI/SDK/library version, not the model itself, but it's real and
    auto-updating). Uses the full unfiltered cache so it always reflects the
    true latest release, independent of the sidebar's date-range filter."""
    st.markdown(_TABLE_CSS, unsafe_allow_html=True)

    rows = []
    for src in MODEL_SOURCES:
        tool_version, released = _latest_release(df, src["platform"])
        model_name = html.escape(src.get("model") or "") or (
            '<span style="color:var(--text-dim);">— update config.py —</span>'
        )
        rows.append(
            "<tr>"
            f"<td>{_source_badge(src['platform'])}</td>"
            f"<td>{_tier_pill(src['tier'])}</td>"
            f"<td style='color:var(--teal-hi);font-weight:600;'>{model_name}</td>"
            f"<td>{tool_version}</td>"
            f"<td>{released}</td>"
            f"<td style='color:var(--text);'>{html.escape(src['notes'])}</td>"
            "</tr>"
        )

    table_html = (
        '<table class="model-table"><thead><tr>'
        "<th>Source</th><th>Tier</th><th>Model</th><th>Tool/SDK Release</th>"
        "<th>Released</th><th>Notes</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


def _score_cell(value, bold: bool = False) -> str:
    if value is None:
        return '<span style="color:var(--text-dim);">—</span>'
    style = "font-weight:700;color:var(--gold-lt);" if bold else ""
    return f'<span style="{style}">{html.escape(f"{value:g}")}</span>'


def render_llm_inventory(providers: list[str] | None = None, search: str = "") -> None:
    """Static snapshot of the top models from the LiveBench.AI leaderboard —
    see config.py's LLM_INVENTORY for the source release date and how to
    refresh it (there's no stable API, so this needs a manual re-pull from
    the live page periodically).

    providers: if non-empty, only show rows whose provider is in this list.
    search: case-insensitive substring match against the model name.
    """
    st.markdown(_TABLE_CSS, unsafe_allow_html=True)
    st.caption(f"Source: {LLM_INVENTORY_SOURCE} · sorted by Overall score")

    items = LLM_INVENTORY
    if providers:
        items = [m for m in items if m["provider"] in providers]
    if search.strip():
        needle = search.strip().lower()
        items = [m for m in items if needle in m["model"].lower()]

    if not items:
        st.info("No models match your filters.")
        return

    rows = []
    for m in items:
        model_cell = f"<div style='color:var(--teal-hi);font-weight:600;'>{html.escape(m['model'])}</div>"
        rows.append(
            "<tr>"
            f"<td>{model_cell}</td>"
            f"<td>{_source_badge(m['provider'])}</td>"
            f"<td>{_tier_pill(m['tier'])}</td>"
            f"<td>{_score_cell(m['overall'], bold=True)}</td>"
            f"<td>{_score_cell(m['reasoning'])}</td>"
            f"<td>{_score_cell(m['coding'])}</td>"
            f"<td>{_score_cell(m['agentic_coding'])}</td>"
            f"<td>{_score_cell(m['mathematics'])}</td>"
            f"<td>{_score_cell(m['data_analysis'])}</td>"
            f"<td>{_score_cell(m['language'])}</td>"
            f"<td>{_score_cell(m['instruction_following'])}</td>"
            f"<td>${_score_cell(m['cost'])}</td>"
            "</tr>"
        )

    table_html = (
        '<div class="model-table-scroll"><table class="model-table"><thead><tr>'
        "<th>Model</th><th>Provider</th><th>Tier</th><th>Overall</th><th>Reasoning</th>"
        "<th>Coding</th><th>Agentic Coding</th><th>Math</th><th>Data Analysis</th>"
        "<th>Language</th><th>Instr. Following</th><th>Cost/Task</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)
