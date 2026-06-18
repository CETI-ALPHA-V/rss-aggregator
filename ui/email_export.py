import base64
import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config import PLATFORM_COLORS


def _format_date(published: str) -> str:
    if not published:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(published.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return published[:10]


def _group_by_category(df: pd.DataFrame) -> dict:
    groups: dict[str, list[dict]] = {}
    for _, row in df.iterrows():
        cat = row.get("category") or "Other"
        groups.setdefault(cat, []).append(row.to_dict())
    return dict(sorted(groups.items()))


def _source_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lstrip("www.") if url else ""
    except Exception:
        return ""


def _type_pill_html(content_type: str) -> str:
    if not content_type:
        return ""
    bg = "#e8f4ec" if content_type == "releases" else "#e8f0fb"
    fg = "#1a7a3c" if content_type == "releases" else "#1a3a8c"
    return (
        f'<span style="background:{bg};color:{fg};border:1px solid {fg}40;'
        f'padding:1px 7px;font-size:10px;font-weight:700;'
        f'font-family:Courier New,monospace;letter-spacing:1px;'
        f'text-transform:uppercase;margin-left:8px;">{content_type}</span>'
    )


def _article_rows_html(articles: list[dict]) -> str:
    rows = ""
    for art in articles:
        title = art.get("title") or "(no title)"
        link = art.get("link") or ""
        summary = art.get("summary") or ""
        platform = art.get("platform") or ""
        content_type = art.get("type") or ""
        date_str = _format_date(art.get("published") or "")
        color = PLATFORM_COLORS.get(platform, "#71717a")
        domain = _source_domain(link)

        summary_text = (summary[:400] + "…") if len(summary) > 400 else summary
        title_html = (
            f'<a href="{link}" style="color:#1a56c4;text-decoration:none;'
            f'font-weight:600;font-size:14px;line-height:1.4;">{title}</a>'
            if link
            else f'<span style="font-weight:600;font-size:14px;">{title}</span>'
        )
        domain_html = (
            f'<div style="margin-top:2px;margin-bottom:4px;">'
            f'<a href="{link}" style="color:#aaaaaa;font-size:11px;text-decoration:none;'
            f'font-family:Courier New,monospace;">{domain}</a></div>'
            if domain else ""
        )
        summary_html = (
            f'<div style="color:#444444;font-size:12px;line-height:1.6;margin-top:4px;">'
            f"{summary_text}</div>"
            if summary_text else ""
        )

        initial = platform[0].upper() if platform else "?"
        type_symbol = "↑" if content_type == "releases" else "✦"

        rows += f"""
          <tr>
            <td style="padding:12px 8px 12px 0;vertical-align:top;
              border-bottom:1px solid #e8e8e8;width:52px;">
              <table width="44" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td bgcolor="{color}" width="44" height="44"
                    style="background:{color};width:44px;height:44px;
                    text-align:center;vertical-align:middle;">
                    <span style="color:#ffffff;font-size:18px;font-weight:700;
                      font-family:Arial,sans-serif;line-height:44px;">{initial}</span>
                  </td>
                </tr>
                <tr>
                  <td style="text-align:center;padding-top:3px;">
                    <span style="color:{color};font-size:10px;font-family:Arial,sans-serif;
                      font-weight:700;letter-spacing:1px;">{type_symbol}</span>
                  </td>
                </tr>
              </table>
            </td>
            <td style="padding:13px 0 13px 10px;border-bottom:1px solid #e8e8e8;
              border-left:3px solid {color};">
              <div style="margin-bottom:7px;">
                <span style="background:#f0f0f0;color:{color};border:1px solid {color};
                  padding:2px 9px;font-size:11px;font-weight:700;
                  font-family:Courier New,monospace;letter-spacing:1px;">{platform}</span>
                {_type_pill_html(content_type)}
                <span style="color:#999999;font-size:11px;margin-left:10px;
                  font-family:Courier New,monospace;">{date_str}</span>
              </div>
              <div style="margin-bottom:2px;">{title_html}</div>
              {domain_html}
              {summary_html}
            </td>
          </tr>"""
    return rows


def generate_email_html(df: pd.DataFrame) -> str:
    today = datetime.date.today().strftime("%d %b %Y")
    count = len(df)
    groups = _group_by_category(df)

    sections = ""
    for category, articles in groups.items():
        articles_sorted = sorted(
            articles, key=lambda x: x.get("published") or "", reverse=True
        )
        article_rows = _article_rows_html(articles_sorted)
        sections += f"""
          <tr>
            <td style="padding:22px 0 6px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="border-bottom:2px solid #cccccc;padding-bottom:7px;">
                    <span style="color:#222222;font-size:11px;font-weight:700;
                      letter-spacing:3px;text-transform:uppercase;
                      font-family:Courier New,monospace;">{category}</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding-left:16px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                {article_rows}
              </table>
            </td>
          </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Byte Brief Digest — {today}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f6f8;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
    style="background-color:#f4f6f8;padding:28px 16px;">
    <tr>
      <td align="center">
        <table width="900" cellpadding="0" cellspacing="0" border="0"
          style="background:#ffffff;border-radius:4px;
          border:1px solid #e2e8f0;overflow:hidden;">

          <!-- Header -->
          <tr>
            <td bgcolor="#1e3a58" style="background:#1e3a58;padding:24px 32px 20px;">
              <div style="color:#f2d96e;font-family:'Courier New',monospace;
                font-size:22px;font-weight:700;letter-spacing:5px;
                text-transform:uppercase;">BYTE BRIEF</div>
              <div style="color:#a8cfe0;font-family:'Courier New',monospace;
                font-size:10px;letter-spacing:3px;text-transform:uppercase;
                margin-top:5px;">FRESH BYTES &nbsp;&middot;&nbsp; DAILY BRIEF &nbsp;&middot;&nbsp; {today}</div>
            </td>
          </tr>

          <!-- Stats bar -->
          <tr>
            <td bgcolor="#ddeaf4" style="background:#ddeaf4;padding:8px 32px;">
              <span style="color:#1e3a58;font-family:'Courier New',monospace;
                font-size:10px;letter-spacing:2px;text-transform:uppercase;">
                {count} ARTICLE{"S" if count != 1 else ""} &nbsp;&middot;&nbsp;
                {len(groups)} {"CATEGORIES" if len(groups) != 1 else "CATEGORY"}
              </span>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:4px 32px 28px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                {sections}
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f9fafb;padding:14px 32px;
              border-top:1px solid #e2e8f0;">
              <p style="margin:0;color:#bbbbbb;font-size:10px;
                font-family:'Courier New',monospace;letter-spacing:1px;
                text-transform:uppercase;">
                Generated by Byte Brief &nbsp;&middot;&nbsp; {today}
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def generate_email_plain(df: pd.DataFrame) -> str:
    today = datetime.date.today().strftime("%d %b %Y")
    count = len(df)
    groups = _group_by_category(df)

    lines = [
        f"BYTE BRIEF — DIGEST | {today}",
        f"{count} article{'s' if count != 1 else ''} across {len(groups)} {'categories' if len(groups) != 1 else 'category'}",
        "=" * 60,
        "",
    ]

    for category, articles in groups.items():
        articles_sorted = sorted(
            articles, key=lambda x: x.get("published") or "", reverse=True
        )
        lines.append(f"[ {category.upper()} ]")
        lines.append("-" * 40)

        for art in articles_sorted:
            title = art.get("title") or "(no title)"
            link = art.get("link") or ""
            platform = art.get("platform") or ""
            date_str = _format_date(art.get("published") or "")
            summary = art.get("summary") or ""

            meta = " | ".join(x for x in [platform, date_str] if x)
            lines.append(f"  {title}")
            if meta:
                lines.append(f"  {meta}")
            if link:
                lines.append(f"  {link}")
            if summary:
                short = (summary[:220] + "…") if len(summary) > 220 else summary
                lines.append(f"  {short}")
            lines.append("")

        lines.append("")

    lines += ["—", f"Generated by Byte Brief | {today}"]
    return "\n".join(lines)


def generate_teams_message(df: pd.DataFrame) -> str:
    today = datetime.date.today().strftime("%d %b %Y")
    count = len(df)
    groups = _group_by_category(df)

    lines = [
        f"**BYTE BRIEF** | {today}",
        "",
        f"*{count} article{'s' if count != 1 else ''} across {len(groups)} {'categories' if len(groups) != 1 else 'category'}*",
        "",
    ]

    for category, articles in groups.items():
        articles_sorted = sorted(
            articles, key=lambda x: x.get("published") or "", reverse=True
        )
        lines.append(f"---")
        lines.append(f"**{category.upper()}**")
        lines.append("")

        for art in articles_sorted:
            title = art.get("title") or "(no title)"
            link = art.get("link") or ""
            platform = art.get("platform") or ""
            date_str = _format_date(art.get("published") or "")
            summary = art.get("summary") or ""

            title_md = f"[{title}]({link})" if link else title
            meta = " · ".join(x for x in [platform, date_str] if x)
            lines.append(f"• **{title_md}**")
            if meta:
                lines.append(f"  *{meta}*")
            if summary:
                short = (summary[:160] + "…") if len(summary) > 160 else summary
                lines.append(f"  {short}")
            lines.append("")

    lines.append("---")
    lines.append(f"*Generated by Byte Brief · {today}*")
    return "\n".join(lines)


@st.dialog("Share Digest", width="large")
def _share_dialog(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No articles to export — adjust your filters first.")
        return

    today = datetime.date.today().strftime("%d %b %Y")
    count = len(df)
    subject = f"Byte Brief Digest — {today} ({count} article{'s' if count != 1 else ''})"

    st.caption("Suggested subject line")
    st.code(subject, language=None)

    html_content = generate_email_html(df)
    plain_content = generate_email_plain(df)
    teams_content = generate_teams_message(df)

    tab_outlook, tab_teams, tab_plain = st.tabs(["Outlook", "Teams", "Plain Text"])

    with tab_outlook:
        html_b64 = base64.b64encode(html_content.encode()).decode()
        component_html = f"""<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #080e16;
    font-family: 'Courier New', monospace;
    padding: 10px;
  }}
  .toolbar {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }}
  .btn {{
    background: transparent;
    border: 1px solid #88b7b8;
    color: #88b7b8;
    padding: 7px 18px;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    cursor: pointer;
    border-radius: 2px;
    transition: all 0.15s;
    white-space: nowrap;
  }}
  .btn:hover {{ background: rgba(136,183,184,0.15); }}
  .btn.success {{ border-color: #21a559; color: #21a559; }}
  .status {{
    color: #92acbd;
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
  }}
  #preview-wrap {{
    border: 1px solid rgba(92,157,176,0.22);
    border-radius: 2px;
    overflow: hidden;
    background: #f4f6f8;
  }}
  iframe {{
    display: block;
    width: 100%;
    border: none;
  }}
  #copy-src {{
    position: fixed;
    left: -9999px;
    top: 0;
    width: 900px;
    background: #fff;
  }}
</style>
</head>
<body>
  <div class="toolbar">
    <button class="btn" id="copyBtn" onclick="doCopy()">Copy for Outlook</button>
    <span class="status" id="status"></span>
  </div>
  <div id="preview-wrap">
    <iframe id="preview" height="600" srcdoc=""></iframe>
  </div>
  <div id="copy-src"></div>
  <script>
    const raw = atob("{html_b64}");
    document.getElementById('preview').srcdoc = raw;
    const parser = new DOMParser();
    const doc = parser.parseFromString(raw, 'text/html');
    document.getElementById('copy-src').innerHTML = doc.body.innerHTML;

    function doCopy() {{
      const el = document.getElementById('copy-src');
      if (window.ClipboardItem) {{
        const blob = new Blob([raw], {{ type: 'text/html' }});
        navigator.clipboard.write([new ClipboardItem({{ 'text/html': blob }})])
          .then(() => feedback(true))
          .catch(() => fallbackCopy(el));
      }} else {{
        fallbackCopy(el);
      }}
    }}
    function fallbackCopy(el) {{
      const range = document.createRange();
      range.selectNodeContents(el);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      const ok = document.execCommand('copy');
      sel.removeAllRanges();
      feedback(ok);
    }}
    function feedback(success) {{
      const btn = document.getElementById('copyBtn');
      const status = document.getElementById('status');
      if (success) {{
        btn.textContent = 'Copied!';
        btn.classList.add('success');
        status.textContent = 'Paste into Outlook compose window';
      }} else {{
        status.textContent = 'Copy failed — try downloading the .html file';
      }}
      setTimeout(() => {{
        btn.textContent = 'Copy for Outlook';
        btn.classList.remove('success');
        status.textContent = '';
      }}, 3000);
    }}
  </script>
</body>
</html>"""
        components.html(component_html, height=680, scrolling=False)
        st.download_button(
            "Download .html",
            data=html_content,
            file_name=f"byte_brief_{datetime.date.today().strftime('%Y%m%d')}.html",
            mime="text/html",
            key="dl_email_html",
        )

    with tab_teams:
        st.caption("Copy and paste into a Teams message or channel post. Teams renders markdown automatically.")
        st.download_button(
            "Download .txt",
            data=teams_content,
            file_name=f"byte_brief_teams_{datetime.date.today().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            key="dl_teams",
        )
        st.code(teams_content, language="markdown")

    with tab_plain:
        st.download_button(
            "Download .txt",
            data=plain_content,
            file_name=f"byte_brief_{datetime.date.today().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            key="dl_email_plain",
        )
        st.code(plain_content, language="text")


def render_email_export(df: pd.DataFrame) -> None:
    if st.button("Share Digest", use_container_width=True, type="secondary"):
        _share_dialog(df)
