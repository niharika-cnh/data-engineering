"""Shared Streamlit UI helpers (CSS, headers, layout). No data/model logic."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

STATUS_STEP_BADGE: dict[str, str] = {
    "Warranty claims cleaned": "1A",
    "Claims classified (2M/1D)": "1B",
    "Test data processed": "2B",
    "Pareto analysis": "2A",
    "Prediction models": "ML",
}

GLOBAL_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }

  [data-testid="stSidebar"],
  [data-testid="stSidebarCollapsedControl"],
  [data-testid="collapsedControl"] {
    display: none !important;
  }

  header[data-testid="stHeader"] {
    background: transparent !important;
    box-shadow: none !important;
  }
  #MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; height: 0; }

  .main .block-container {
    padding-top: 0.35rem;
    padding-bottom: 1.5rem;
    max-width: 1200px;
    padding-left: 1.25rem;
    padding-right: 1.25rem;
  }

  /* —— Top navigation —— */
  .cnh-topnav-wrap {
    background: #161b26;
    border-bottom: 2px solid #E40521;
    margin: 0 -1.25rem 1rem -1.25rem;
    padding: 0.5rem 1.25rem;
    position: sticky;
    top: 0;
    z-index: 1000;
    box-shadow: 0 1px 4px rgba(0,0,0,0.12);
  }
  .cnh-topnav-brand {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    min-width: 0;
  }
  .cnh-topnav-brand img {
    width: 56px !important;
    height: auto;
    background: #fff;
    padding: 3px 5px;
    border-radius: 3px;
    flex-shrink: 0;
  }
  .cnh-brand-text {
    color: #fff;
    font-size: 0.88rem;
    font-weight: 600;
    margin: 0;
    line-height: 1.2;
    white-space: nowrap;
  }
  .cnh-brand-sub {
    color: #8b95a5;
    font-size: 0.65rem;
    margin: 0;
    letter-spacing: 0.03em;
  }

  /* Top nav page links — compact, no clip */
  [data-testid="cnh-topnav-row"] [data-testid="stPageLink"] {
    width: 100%;
  }
  [data-testid="cnh-topnav-row"] [data-testid="stPageLink"] a {
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    padding: 0.35rem 0.5rem !important;
    color: #c8ced8 !important;
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 4px !important;
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: unset !important;
    justify-content: center !important;
    min-height: 2rem !important;
    line-height: 1.2 !important;
  }
  [data-testid="cnh-topnav-row"] [data-testid="stPageLink"] a p {
    font-size: 0.75rem !important;
    white-space: nowrap !important;
  }
  [data-testid="cnh-topnav-row"] [data-testid="stPageLink"] a:hover {
    color: #fff !important;
    background: rgba(255,255,255,0.07) !important;
  }
  [data-testid="cnh-topnav-row"] [data-testid="stPageLink"] a[aria-current="page"] {
    color: #fff !important;
    background: rgba(228, 5, 33, 0.22) !important;
    border-color: rgba(228, 5, 33, 0.55) !important;
    font-weight: 600 !important;
  }
  /* Hide material icons in top nav (saves horizontal space) */
  [data-testid="cnh-topnav-row"] [data-testid="stPageLink"] [data-testid="stIconMaterial"] {
    display: none !important;
  }

  /* —— Hero —— */
  .cnh-hero {
    background: linear-gradient(118deg, #161b26 0%, #1e2636 55%, #232d3f 100%);
    border-radius: 6px;
    padding: 1rem 1.15rem 0.85rem;
    margin: 0 0 0.5rem 0;
    border-left: 3px solid #E40521;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }
  .cnh-hero-title {
    color: #fff;
    font-size: 1.35rem;
    font-weight: 700;
    margin: 0 0 0.35rem 0;
    line-height: 1.2;
    letter-spacing: -0.02em;
  }
  .cnh-hero-subtitle {
    color: #a8b0bc;
    font-size: 0.82rem;
    line-height: 1.5;
    margin: 0 0 0.5rem 0;
    max-width: 36rem;
  }
  .cnh-hero-badges { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .cnh-meta-badge {
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: #dce0e6;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 3px;
    padding: 0.18rem 0.42rem;
    white-space: nowrap;
  }

  /* —— Executive summary strip —— */
  .cnh-exec-card {
    background: #f8f9fb;
    border: 1px solid #e4e7ec;
    border-radius: 5px;
    padding: 0.55rem 0.7rem;
    height: 100%;
    min-height: 3.5rem;
  }
  .cnh-exec-label {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6b7280;
    margin: 0 0 0.2rem 0;
  }
  .cnh-exec-value {
    font-size: 0.8rem;
    font-weight: 500;
    color: #1a1f2e;
    margin: 0;
    line-height: 1.4;
  }

  /* —— Section headers —— */
  .cnh-section-title {
    font-size: 0.88rem;
    font-weight: 600;
    color: #1a1f2e;
    margin: 1.25rem 0 0.65rem 0;
    letter-spacing: -0.01em;
  }
  .cnh-section-label {
    font-size: 0.67rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #6b7280;
    margin: 0 0 0.35rem 0;
  }

  /* —— Workflow module cards —— */
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.cnh-wf-marker) {
    border-color: #dfe3ea !important;
    border-radius: 6px !important;
    background: #fff !important;
    box-shadow: 0 1px 2px rgba(16,24,40,0.04) !important;
    min-height: 11.5rem;
    transition: box-shadow 0.15s ease, border-color 0.15s ease;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.cnh-wf-marker):hover {
    border-color: #c8ced8 !important;
    box-shadow: 0 4px 12px rgba(16,24,40,0.08) !important;
  }
  .cnh-wf-badge {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    color: #fff;
    background: #161b26;
    border-radius: 3px;
    padding: 0.15rem 0.4rem;
    margin-bottom: 0.45rem;
  }
  .cnh-wf-title {
    font-size: 0.92rem;
    font-weight: 600;
    color: #1a1f2e;
    margin: 0 0 0.35rem 0;
    line-height: 1.35;
  }
  .cnh-wf-desc {
    font-size: 0.78rem;
    color: #5c6573;
    line-height: 1.5;
    margin: 0 0 0.5rem 0;
    min-height: 3.6rem;
  }
  .cnh-wf-meta {
    font-size: 0.68rem;
    color: #8b95a5;
    margin: 0 0 0.65rem 0;
    font-weight: 500;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.cnh-wf-marker) [data-testid="stPageLink"] {
    margin-top: 0.15rem;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.cnh-wf-marker) [data-testid="stPageLink"] a {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 0.4rem 0.75rem !important;
    background: #161b26 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 4px !important;
    justify-content: center !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.cnh-wf-marker) [data-testid="stPageLink"] a:hover {
    background: #2a3344 !important;
    color: #fff !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.cnh-wf-marker) [data-testid="stIconMaterial"] {
    display: none !important;
  }

  /* —— Page headers (inner pages) —— */
  .cnh-page-banner {
    background: linear-gradient(90deg, #f6f7f9 0%, #fafbfc 100%);
    border: 1px solid #e4e7ec;
    border-left: 3px solid #E40521;
    border-radius: 6px;
    padding: 0.7rem 1rem;
    margin-bottom: 1rem;
  }
  .cnh-page-banner h1 {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0 0 0.2rem 0;
    padding: 0;
    border: none;
    color: #1a1f2e;
    line-height: 1.3;
  }
  .cnh-step-badge {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    color: #fff;
    background: #161b26;
    border-radius: 3px;
    padding: 0.12rem 0.38rem;
    margin-right: 0.4rem;
    vertical-align: middle;
  }
  .cnh-page-subtitle {
    color: #5c6573;
    font-size: 0.8rem;
    line-height: 1.45;
    margin: 0;
  }

  /* —— Review panels (2B abnormal, etc.) —— */
  [data-testid="cnh-review-panel"] {
    border: 1px solid #e4e7ec !important;
    border-radius: 6px !important;
    padding: 0.9rem 1rem !important;
    background: #fafbfc !important;
    margin-top: 0.75rem;
  }
  .cnh-review-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: #1a1f2e;
    margin: 0 0 0.35rem 0;
  }
  .cnh-review-desc {
    font-size: 0.8rem;
    color: #5c6573;
    line-height: 1.5;
    margin: 0 0 0.75rem 0;
  }

  /* —— Status strip —— */
  .cnh-status-compact {
    background: #fff;
    border: 1px solid #e4e7ec;
    border-radius: 5px;
    padding: 0.5rem 0.65rem;
  }
  .cnh-status-compact.ok { border-left: 3px solid #2e6b3e; }
  .cnh-status-compact.warn { border-left: 3px solid #c41e3a; }
  .cnh-status-row { display: flex; align-items: center; gap: 0.4rem; }
  .cnh-status-badge {
    font-size: 0.6rem;
    font-weight: 700;
    color: #fff;
    background: #161b26;
    border-radius: 3px;
    padding: 0.1rem 0.32rem;
    flex-shrink: 0;
  }
  .cnh-status-title { font-size: 0.76rem; font-weight: 600; color: #1a1f2e; }
  .cnh-status-detail { font-size: 0.68rem; color: #6b7280; margin-top: 0.1rem; line-height: 1.35; }

  /* —— Streamlit widgets polish —— */
  div[data-testid="stMetric"] {
    background: #f8f9fb;
    padding: 0.5rem 0.7rem;
    border-radius: 5px;
    border: 1px solid #e4e7ec;
  }
  div[data-testid="stMetricLabel"] { font-size: 0.74rem; color: #6b7280; }
  div[data-testid="stMetricValue"] { font-size: 1.1rem !important; }

  .stDownloadButton button, .stButton > button[kind="primary"] {
    font-weight: 600;
    border-radius: 4px;
  }

  hr.cnh-divider {
    border: none;
    border-top: 1px solid #e4e7ec;
    margin: 1.25rem 0;
  }
</style>
"""


def apply_global_styles() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def _logo_img_html(logo_path: Path, width: int = 56) -> str:
    if not logo_path.exists():
        return ""
    import base64

    suffix = logo_path.suffix.lower()
    mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"
    b64 = base64.b64encode(logo_path.read_bytes()).decode()
    return (
        f'<img src="data:{mime};base64,{b64}" alt="CNH Industrial" '
        f'style="width:{width}px;height:auto;" />'
    )


def render_top_nav(
    logo_path: Path | None,
    pages: list,
    nav_links: list[tuple[int, str]],
) -> None:
    """Compact enterprise top bar. Call after st.navigation()."""
    st.markdown('<div class="cnh-topnav-wrap">', unsafe_allow_html=True)

    # Brand + nav in one row: brand ~18%, each link gets equal share
    n_links = len(nav_links)
    widths = [1.35] + [1.0] * n_links
    cols = st.columns(widths, gap="small")

    with cols[0]:
        if logo_path and logo_path.exists():
            st.markdown(
                f'<div class="cnh-topnav-brand">{_logo_img_html(logo_path)}'
                '<div><p class="cnh-brand-text">CNH Analytics</p></div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<p class="cnh-brand-text">CNH Analytics</p>', unsafe_allow_html=True)

    st.markdown('<div data-testid="cnh-topnav-row" style="display:contents"></div>', unsafe_allow_html=True)
    for col, (page_idx, label) in zip(cols[1:], nav_links):
        with col:
            st.page_link(pages[page_idx], label=label, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)


def enterprise_hero(title: str, subtitle: str, meta_badges: list[str]) -> None:
    badges_html = "".join(f'<span class="cnh-meta-badge">{b}</span>' for b in meta_badges)
    st.markdown(
        f"""<div class="cnh-hero">
              <p class="cnh-hero-title">{title}</p>
              <p class="cnh-hero-subtitle">{subtitle}</p>
              <div class="cnh-hero-badges">{badges_html}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def executive_summary_strip(items: list[tuple[str, str]]) -> None:
    cols = st.columns(len(items), gap="small")
    for col, (label, value) in zip(cols, items):
        col.markdown(
            f"""<div class="cnh-exec-card">
                  <p class="cnh-exec-label">{label}</p>
                  <p class="cnh-exec-value">{value}</p>
                </div>""",
            unsafe_allow_html=True,
        )


def page_header(step: str, title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""<div class="cnh-page-banner">
              <h1><span class="cnh-step-badge">{step}</span>{title}</h1>
              {f'<p class="cnh-page-subtitle">{subtitle}</p>' if subtitle else ''}
            </div>""",
        unsafe_allow_html=True,
    )


def section_title(text: str) -> None:
    st.markdown(f'<p class="cnh-section-title">{text}</p>', unsafe_allow_html=True)


def section_label(text: str, help_text: str = "") -> None:
    st.markdown(f'<p class="cnh-section-label">{text}</p>', unsafe_allow_html=True)
    if help_text:
        st.caption(help_text)


def workflow_module_cards(modules: list, pages: list) -> None:
    """(badge, title, desc, metadata, cta_label, page_index)."""
    for row in (modules[:2], modules[2:4]):
        cols = st.columns(2, gap="medium")
        for col, mod in zip(cols, row):
            badge, title, desc, meta, cta, page_idx = mod
            with col:
                with st.container(border=True):
                    st.markdown('<div class="cnh-wf-marker"></div>', unsafe_allow_html=True)
                    st.markdown(
                        f'<span class="cnh-wf-badge">{badge}</span>'
                        f'<p class="cnh-wf-title">{title}</p>'
                        f'<p class="cnh-wf-desc">{desc}</p>'
                        f'<p class="cnh-wf-meta">{meta}</p>',
                        unsafe_allow_html=True,
                    )
                    st.page_link(pages[page_idx], label=cta, use_container_width=True)


def review_panel(title: str, description: str) -> None:
    """Open a styled review section container; close with end_review_panel()."""
    st.markdown(
        f"""<div data-testid="cnh-review-panel">
              <p class="cnh-review-title">{title}</p>
              <p class="cnh-review-desc">{description}</p>
            </div>""",
        unsafe_allow_html=True,
    )


def compact_workflow_status(items: list) -> None:
    cols = st.columns(min(len(items), 5), gap="small")
    for col, item in zip(cols, items):
        css = "ok" if item.available else "warn"
        badge = STATUS_STEP_BADGE.get(item.name, "—")
        state_txt = "Ready" if item.available else "Pending"
        detail = item.detail or "—"
        ts = f" · {item.updated}" if item.updated else ""
        col.markdown(
            f"""<div class="cnh-status-compact {css}">
                  <div class="cnh-status-row">
                    <span class="cnh-status-badge">{badge}</span>
                    <span class="cnh-status-title">{item.name}</span>
                  </div>
                  <div class="cnh-status-detail">{state_txt} — {detail}{ts}</div>
                </div>""",
            unsafe_allow_html=True,
        )


def divider() -> None:
    st.markdown('<hr class="cnh-divider" />', unsafe_allow_html=True)


section_header = section_label
hero_header = enterprise_hero
feature_cards = workflow_module_cards
