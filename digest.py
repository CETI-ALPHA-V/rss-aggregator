"""Digest generators (Outlook HTML, Teams markdown, plain text).

Framework-free so both the Streamlit app and the FastAPI backend can use them.
Each generator takes a list of article dicts (feed_id, link, title, summary,
published, platform, category, type).
"""
import datetime
from html import escape
from urllib.parse import urlparse

from config import PLATFORM_COLORS


def _today() -> str:
    return datetime.date.today().strftime("%d %b %Y")


def _format_date(published: str) -> str:
    if not published:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(published.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return published[:10]


def _group_by_category(articles: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for art in articles:
        groups.setdefault(art.get("category") or "Other", []).append(art)
    return {
        cat: sorted(items, key=lambda a: a.get("published") or "", reverse=True)
        for cat, items in sorted(groups.items())
    }


def _source_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""


def _readable_text(hex_color: str) -> str:
    """White or near-black, whichever reads better on `hex_color`."""
    try:
        n = int(hex_color.lstrip("#"), 16)
    except ValueError:
        return "#ffffff"

    def channel(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (n >> 16) & 255, (n >> 8) & 255, n & 255
    luminance = 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
    return "#18181b" if luminance > 0.45 else "#ffffff"


def _plural(n: int, word: str, plural: str | None = None) -> str:
    return f"{n} {word if n == 1 else (plural or word + 's')}"


def digest_subject(articles: list[dict]) -> str:
    return f"m[AI]ntain Digest — {_today()} ({_plural(len(articles), 'article')})"


def _type_pill_html(content_type: str) -> str:
    if not content_type:
        return ""
    bg, fg = {
        "releases": ("#e8f4ec", "#1a7a3c"),
        "video": ("#fdecec", "#b42318"),
    }.get(content_type, ("#e8f0fb", "#1a3a8c"))
    return (
        f'<span style="background:{bg};color:{fg};border:1px solid {fg}40;'
        f'padding:1px 7px;font-size:10px;font-weight:700;'
        f'font-family:Arial,sans-serif;letter-spacing:1px;'
        f'text-transform:uppercase;margin-left:8px;">{escape(content_type)}</span>'
    )


def _article_rows_html(articles: list[dict]) -> str:
    rows = ""
    for art in articles:
        title = escape(art.get("title") or "(no title)")
        link = art.get("link") or ""
        href = escape(link, quote=True)
        summary = art.get("summary") or ""
        platform = art.get("platform") or ""
        content_type = art.get("type") or ""
        date_str = _format_date(art.get("published") or "")
        color = PLATFORM_COLORS.get(platform, "#71717a")
        domain = escape(_source_domain(link))

        summary_text = escape((summary[:400] + "…") if len(summary) > 400 else summary)
        title_html = (
            f'<a href="{href}" style="color:#0f766e;text-decoration:none;'
            f'font-weight:600;font-size:14px;line-height:1.4;">{title}</a>'
            if link
            else f'<span style="font-weight:600;font-size:14px;">{title}</span>'
        )
        domain_html = (
            f'<div style="margin-top:2px;margin-bottom:4px;">'
            f'<a href="{href}" style="color:#999999;font-size:11px;text-decoration:none;">{domain}</a></div>'
            if domain else ""
        )
        summary_html = (
            f'<div style="color:#444444;font-size:12px;line-height:1.6;margin-top:4px;">'
            f"{summary_text}</div>"
            if summary_text else ""
        )
        initial = escape(platform[0].upper()) if platform else "?"

        rows += f"""
          <tr>
            <td style="padding:12px 8px 12px 0;vertical-align:top;
              border-bottom:1px solid #e8e8e8;width:52px;">
              <table width="40" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td bgcolor="{color}" width="40" height="40"
                    style="background:{color};width:40px;height:40px;border-radius:8px;
                    text-align:center;vertical-align:middle;">
                    <span style="color:{_readable_text(color)};font-size:16px;font-weight:700;
                      font-family:Arial,sans-serif;line-height:40px;">{initial}</span>
                  </td>
                </tr>
              </table>
            </td>
            <td style="padding:13px 0 13px 10px;border-bottom:1px solid #e8e8e8;">
              <div style="margin-bottom:6px;">
                <span style="color:#374151;font-size:12px;font-weight:700;
                  font-family:Arial,sans-serif;">{escape(platform)}</span>
                {_type_pill_html(content_type)}
                <span style="color:#999999;font-size:11px;margin-left:10px;
                  font-family:Arial,sans-serif;">{date_str}</span>
              </div>
              <div style="margin-bottom:2px;">{title_html}</div>
              {domain_html}
              {summary_html}
            </td>
          </tr>"""
    return rows


def generate_email_html(articles: list[dict]) -> str:
    today = _today()
    groups = _group_by_category(articles)

    sections = ""
    for category, items in groups.items():
        sections += f"""
          <tr>
            <td style="padding:22px 0 6px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="border-bottom:2px solid #e2e8f0;padding-bottom:7px;">
                    <span style="color:#111827;font-size:12px;font-weight:700;
                      letter-spacing:2px;text-transform:uppercase;
                      font-family:Arial,sans-serif;">{escape(category)}</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td>
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                {_article_rows_html(items)}
              </table>
            </td>
          </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>m[AI]ntain Digest — {today}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f6f8;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
    style="background-color:#f4f6f8;padding:28px 16px;">
    <tr>
      <td align="center">
        <table width="760" cellpadding="0" cellspacing="0" border="0"
          style="background:#ffffff;border-radius:8px;
          border:1px solid #e2e8f0;overflow:hidden;">
          <tr>
            <td bgcolor="#0b1120" style="background:#0b1120;padding:24px 32px 20px;">
              <div style="color:#ffffff;font-family:Arial,sans-serif;
                font-size:22px;font-weight:700;letter-spacing:0.5px;">m[AI]ntain</div>
              <div style="color:#94a3b8;font-family:Arial,sans-serif;
                font-size:12px;margin-top:4px;">Daily digest &nbsp;&middot;&nbsp; {today}</div>
            </td>
          </tr>
          <tr>
            <td bgcolor="#ccfbf1" style="background:#ccfbf1;padding:8px 32px;">
              <span style="color:#115e59;font-family:Arial,sans-serif;font-size:12px;">
                {_plural(len(articles), 'article')} &nbsp;&middot;&nbsp;
                {_plural(len(groups), 'category', 'categories')}
              </span>
            </td>
          </tr>
          <tr>
            <td style="padding:4px 32px 28px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                {sections}
              </table>
            </td>
          </tr>
          <tr>
            <td style="background:#f9fafb;padding:14px 32px;border-top:1px solid #e2e8f0;">
              <p style="margin:0;color:#9ca3af;font-size:11px;font-family:Arial,sans-serif;">
                Generated by m[AI]ntain &nbsp;&middot;&nbsp; {today}
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def generate_email_plain(articles: list[dict]) -> str:
    today = _today()
    groups = _group_by_category(articles)

    lines = [
        f"m[AI]ntain — DIGEST | {today}",
        f"{_plural(len(articles), 'article')} across {_plural(len(groups), 'category', 'categories')}",
        "=" * 60,
        "",
    ]
    for category, items in groups.items():
        lines.append(f"[ {category.upper()} ]")
        lines.append("-" * 40)
        for art in items:
            link = art.get("link") or ""
            summary = art.get("summary") or ""
            meta = " | ".join(
                x for x in [art.get("platform") or "", _format_date(art.get("published") or "")] if x
            )
            lines.append(f"  {art.get('title') or '(no title)'}")
            if meta:
                lines.append(f"  {meta}")
            if link:
                lines.append(f"  {link}")
            if summary:
                lines.append(f"  {(summary[:220] + '…') if len(summary) > 220 else summary}")
            lines.append("")
        lines.append("")

    lines += ["—", f"Generated by m[AI]ntain | {today}"]
    return "\n".join(lines)


def generate_teams_message(articles: list[dict]) -> str:
    today = _today()
    groups = _group_by_category(articles)

    lines = [
        f"**m[AI]ntain** | {today}",
        "",
        f"*{_plural(len(articles), 'article')} across {_plural(len(groups), 'category', 'categories')}*",
        "",
    ]
    for category, items in groups.items():
        lines += ["---", f"**{category.upper()}**", ""]
        for art in items:
            title = art.get("title") or "(no title)"
            link = art.get("link") or ""
            summary = art.get("summary") or ""
            meta = " · ".join(
                x for x in [art.get("platform") or "", _format_date(art.get("published") or "")] if x
            )
            lines.append(f"• **{f'[{title}]({link})' if link else title}**")
            if meta:
                lines.append(f"  *{meta}*")
            if summary:
                lines.append(f"  {(summary[:160] + '…') if len(summary) > 160 else summary}")
            lines.append("")

    lines += ["---", f"*Generated by m[AI]ntain · {today}*"]
    return "\n".join(lines)
