"""Legacy combined page — use 1A and 1B from the top navigation."""

from __future__ import annotations

import streamlit as st

from backend import nav_pages, ui

ui.page_header(
    "1A / 1B",
    "Warranty workflow",
    "This module has been split into separate steps. Use the top navigation to open 1A or 1B.",
)
st.info("Open **1A · Warranty Preparation** or **1B · Claim Classification** from the top navigation bar.")
c1, c2 = st.columns(2)
_pages = nav_pages.app_pages()
c1.page_link(_pages[1], label="1A · Warranty Preparation", use_container_width=True)
c2.page_link(_pages[2], label="1B · Claim Classification", use_container_width=True)
