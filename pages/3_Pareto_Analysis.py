from __future__ import annotations

import streamlit as st

from backend import pareto, state, ui

state.ensure_dirs()

ui.page_header(
    "2A",
    "2A · Plant-Related Pareto Analysis",
    "Prioritize plant-controlled warranty contributors by claim frequency and cost.",
)

st.markdown(
    "Use classification output from **1B** together with parts and claims data to focus on "
    "**plant-related** warranty drivers at assembly stations."
)

with st.expander("Inputs and technical notes", expanded=False):
    st.markdown(
        "- **Racine parts data** — links part numbers to assembly stations  \n"
        "- **Claims report** — warranty cost and part detail  \n"
        "- Charts rank top stations by total cost and claim count"
    )

ui.section_label("Upload files")
pcol, ccol = st.columns(2)
parts_file = pcol.file_uploader("Racine parts data (.xlsx)", type=["xlsx"], key="pareto_parts")
claims_file = ccol.file_uploader("Warranty claims report (.xlsx)", type=["xlsx"], key="pareto_claims")

top_n = st.slider("Top stations to display", 5, 30, 15)

if st.button("Generate Pareto analysis", type="primary", disabled=not (parts_file and claims_file)):
    with st.spinner("Building analysis…"):
        try:
            stats = pareto.run_pareto(
                claims_file=claims_file,
                parts_file=parts_file,
                out_dir=state.PARETO_DIR,
                top_n=top_n,
            )
            state.save_json(stats, state.PARETO_STATS)
            st.success("Analysis complete.")
        except Exception as e:
            st.error(f"Analysis failed: {e}")

cached_stats = state.load_json(state.PARETO_STATS)
if cached_stats:
    st.markdown("---")
    ui.section_title("Results")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total claims", f"{cached_stats['total_claims']:,}")
    m2.metric("Plant-mapped", f"{cached_stats['mapped_claims']:,}", f"{cached_stats['mapping_rate']*100:.1f}%")
    m3.metric("Warranty cost", f"${cached_stats['total_warranty_cost']:,.0f}")
    m4.metric("Top station", str(cached_stats["top_station_id"]))

    l, r = st.columns(2)
    if state.PARETO_CHART_COST.exists():
        l.image(str(state.PARETO_CHART_COST), caption="Pareto by cost", use_container_width=True)
    if state.PARETO_CHART_OCC.exists():
        r.image(str(state.PARETO_CHART_OCC), caption="Pareto by occurrence", use_container_width=True)

    ui.section_label("Top stations")
    st.dataframe(cached_stats["top_n_stations"], use_container_width=True)
