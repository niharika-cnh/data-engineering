from __future__ import annotations

import streamlit as st

from backend import clean_warranty, nav_pages, state, ui

state.ensure_dirs()

ui.page_header(
    "1A",
    "1A · Warranty Preparation",
    "Clean and standardize raw warranty claim files for classification (1B) and plant Pareto review (2A).",
)

ui.section_label("Upload & process", "Input: raw warranty claims workbook · Output: cleaned claims table")

file = st.file_uploader(
    "Warranty claims file (.xlsx)",
    type=["xlsx"],
    key="warranty_clean_upload",
)

with st.expander("Processing options", expanded=False):
    c1, c2, c3 = st.columns([2, 1, 2])
    sheet_name = c1.text_input("Worksheet name", value="Paid")
    header_row = c2.number_input("Header row (0-based)", min_value=0, value=1)
    only_bw = c3.checkbox("Basic warranty only (BW)", value=True)
    c4, c5 = st.columns(2)
    only_z = c4.checkbox("Dealer-found claims only (Z)", value=False)
    drop_missing = c5.checkbox("Exclude missing warranty start date", value=False)

if st.button("Process warranty data", type="primary", disabled=file is None):
    with st.spinner("Processing…"):
        df = clean_warranty.clean_warranty(
            file,
            sheet_name=sheet_name,
            header_row=int(header_row),
            only_basic_warranty=only_bw,
            only_dealer_found=only_z,
            drop_missing_warranty_start=drop_missing,
        )
        state.save_dataframe(df, state.WARRANTY_CLEAN)
    st.success(f"Processed {len(df):,} claim rows.")

cached = state.load_dataframe(state.WARRANTY_CLEAN)
if cached is not None:
    st.markdown("---")
    ui.section_title("Cleaned warranty claims")
    m1, m2 = st.columns(2)
    m1.metric("Rows", f"{len(cached):,}")
    m2.metric("Fields", len(cached.columns))
    with st.expander("Data preview", expanded=True):
        st.dataframe(cached.head(50), use_container_width=True, height=300)
    st.download_button(
        "Download cleaned warranty claims (CSV)",
        data=cached.to_csv(index=False).encode(),
        file_name="warranty_cleaned.csv",
        mime="text/csv",
        type="primary",
    )
    st.page_link(nav_pages.app_pages()[2], label="Continue to 1B · Claim Classification →")
