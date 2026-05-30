from __future__ import annotations

import streamlit as st

from backend import nav_pages, state, ui

st.set_page_config(
    page_title="CNH Warranty & Test Analytics",
    page_icon="img/CNH_Industrial.jpg" if state.IMG_DIR.joinpath("CNH_Industrial.jpg").exists() else None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

ui.apply_global_styles()

pages = nav_pages.app_pages()

# Register pages before st.page_link (avoids KeyError: 'url_pathname')
nav = st.navigation(pages, position="hidden")

cnh_logo = state.IMG_DIR / "CNH_Industrial.jpg"
ui.render_top_nav(
    cnh_logo if cnh_logo.exists() else None,
    pages,
    nav_pages.TOP_NAV,
)

nav.run()
