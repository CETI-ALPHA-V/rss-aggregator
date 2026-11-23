import base64
import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from digest import digest_subject, generate_email_html, generate_email_plain, generate_teams_message


@st.dialog("Share Digest", width="large")
def _share_dialog(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No articles to export — adjust your filters first.")
        return

    articles = df.to_dict("records")
    subject = digest_subject(articles)

    st.caption("Suggested subject line")
    st.code(subject, language=None)

    html_content = generate_email_html(articles)
    plain_content = generate_email_plain(articles)
    teams_content = generate_teams_message(articles)

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
    function b64DecodeUtf8(str) {{
      const binary = atob(str);
      const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
      return new TextDecoder('utf-8').decode(bytes);
    }}
    const raw = b64DecodeUtf8("{html_b64}");
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
            file_name=f"maintain_{datetime.date.today().strftime('%Y%m%d')}.html",
            mime="text/html",
            key="dl_email_html",
        )

    with tab_teams:
        st.caption("Copy and paste into a Teams message or channel post. Teams renders markdown automatically.")
        st.download_button(
            "Download .txt",
            data=teams_content,
            file_name=f"maintain_teams_{datetime.date.today().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            key="dl_teams",
        )
        st.code(teams_content, language="markdown")

    with tab_plain:
        st.download_button(
            "Download .txt",
            data=plain_content,
            file_name=f"maintain_{datetime.date.today().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            key="dl_email_plain",
        )
        st.code(plain_content, language="text")


def render_email_export(df: pd.DataFrame) -> None:
    if st.button("Share Digest", use_container_width=True, type="secondary"):
        _share_dialog(df)
