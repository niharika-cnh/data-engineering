from __future__ import annotations

import pandas as pd
import streamlit as st

from backend import clean_test, state, ui

state.ensure_dirs()


def _render_abnormal_accepted_section(df_long: pd.DataFrame, z_threshold: float) -> None:
    with st.container(border=True):
        ui.review_panel(
            "2B · Abnormal but Accepted Test Results",
            "These records passed official min/max limits but exceed the selected Z-score threshold, "
            "making them candidates for engineering review.",
        )
        abnormal = clean_test.filter_abnormal_accepted(df_long, z_threshold)
        c1, c2 = st.columns(2)
        c1.metric("Records for review", f"{len(abnormal):,}")
        c2.metric("Z-score threshold", f"|z| > {z_threshold}")

        if abnormal.empty:
            st.info("No records match at the current threshold.")
            return

        ui.section_label("Detailed abnormal results")
        st.dataframe(abnormal, use_container_width=True, height=380)

        summary = clean_test.summarize_abnormal_accepted_by_test(abnormal)
        ui.section_label("Test-level summary")
        st.dataframe(summary, use_container_width=True, height=240)

        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "Download Detailed Abnormal Results",
                data=abnormal.to_csv(index=False).encode(),
                file_name="abnormal_accepted_test_results_z_gt_1.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True,
            )
        with d2:
            st.download_button(
                "Download Test-Level Summary",
                data=summary.to_csv(index=False).encode(),
                file_name="abnormal_accepted_test_summary_by_test.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_abnormal_summary",
            )


ui.page_header(
    "2B",
    "2B · Test Analytics",
    "Process transmission test data and review abnormal-but-accepted results for engineering follow-up.",
)

ui.section_label("Test data processing", "Upload raw transmission test results from the test stand")

st.info("Re-run Process test data after threshold changes to refresh saved artifacts.")

test_file = st.file_uploader(
    "Transmission test file (.csv or .xlsx)",
    type=["csv", "xlsx"],
    key="test_clean_upload",
)

c1, c2 = st.columns(2)
z_threshold = c1.number_input(
    "Z-score abnormality threshold",
    min_value=0.0,
    value=1.0,
    step=0.1,
    help="Default 1.0 per quality review standard. Rows with |z| above this value are flagged.",
)
drop_pct = c2.slider(
    "Minimum test coverage (%)",
    50,
    99,
    90,
    help="Exclude tests missing on more than the selected share of units.",
)
drop_pct_frac = drop_pct / 100.0

with st.expander("Pass/fail logic (technical reference)", expanded=False):
    st.markdown(
        "A test **passes** when |z-score| is below the threshold and the value is within min/max. "
        "**Abnormal but accepted** rows exceed the Z-score limit but remain inside acceptance limits."
    )

clean_clicked = st.button("Process test data", type="primary", disabled=test_file is None)
if clean_clicked:
    with st.spinner("Processing…"):
        df_long, df_pivot = clean_test.clean_test_data(
            test_file,
            z_threshold=z_threshold,
            drop_missing_test_pct=drop_pct_frac,
        )
        state.save_dataframe(df_long, state.TEST_CLEAN_LONG)
        state.save_dataframe(df_pivot, state.TEST_CLEAN_PIVOT)

    st.success(f"Processed {len(df_long):,} measurements · {df_pivot.shape[0]:,} units.")
    ui.section_label("Per-unit summary (preview)")
    st.dataframe(df_pivot.head(20), use_container_width=True)
    _render_abnormal_accepted_section(df_long, z_threshold)

cached_long = state.load_dataframe(state.TEST_CLEAN_LONG)
cached = state.load_dataframe(state.TEST_CLEAN_PIVOT)
if cached is not None:
    ui.divider()
    ui.section_title("Saved outputs")
    m1, m2 = st.columns(2)
    m1.metric("Units", f"{cached.shape[0]:,}")
    m2.metric("Tests", cached.shape[1] - 1)
    st.download_button(
        "Download per-unit test summary (CSV)",
        data=cached.to_csv(index=False).encode(),
        file_name="test_data_per_transmission.csv",
        mime="text/csv",
    )
if cached_long is not None and not clean_clicked:
    st.caption(
        f"Showing saved test data from disk. Current review threshold: **|z| > {z_threshold}**. "
        "Click **Process test data** to regenerate artifacts after changing the threshold."
    )
    _render_abnormal_accepted_section(cached_long, z_threshold)
