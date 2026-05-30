from __future__ import annotations

import streamlit as st

from backend import nav_pages, state, ui

state.ensure_dirs()

pages = nav_pages.app_pages()

ui.enterprise_hero(
    "Warranty & Test Analytics Platform",
    "Internal analytics workspace for warranty classification, plant Pareto review, and transmission test abnormality analysis.",
    ["Racine Plant", "Warranty Analytics", "Test Stand Review", "Internal Use"],
)

ui.section_title("Workflow modules")
ui.workflow_module_cards(nav_pages.WORKFLOW_MODULES, pages)

ui.section_title("Current workflow status")
ui.compact_workflow_status(state.dashboard_status())

ui.divider()

with st.expander("How to use this platform", expanded=False):
    st.markdown(
        """
1. Select a workflow module or use the **top navigation**.  
2. Upload warranty and test files in **1A**, **1B**, **2A**, or **2B**.  
3. Review Pareto outputs and **abnormal-but-accepted** test results in **2B**.  
4. Download review files for engineering and quality sign-off.  
        """
    )

with st.expander("Recent outputs", expanded=False):
    classified = state.load_dataframe(state.WARRANTY_CLASSIFIED)
    if classified is not None:
        st.caption("1B — Classification output")
        if "category" in classified.columns:
            st.bar_chart(classified["category"].value_counts())
        st.download_button(
            "Download classified claims (CSV)",
            data=classified.to_csv(index=False).encode(),
            file_name="warranty_classified_plant_material_design.csv",
            mime="text/csv",
            key="home_download_classified",
        )

    pareto_stats = state.load_json(state.PARETO_STATS)
    if pareto_stats and state.PARETO_CHART_COST.exists():
        st.caption("2A — Pareto snapshot")
        c1, c2, c3 = st.columns(3)
        c1.metric("Claims", f"{pareto_stats['total_claims']:,}")
        c2.metric("Plant-mapped", f"{pareto_stats['mapping_rate']*100:.1f}%")
        c3.metric("Top station", str(pareto_stats["top_station_id"]))
        st.image(str(state.PARETO_CHART_COST), use_container_width=True)

st.caption("CNH internal use · Racine warranty & test analytics workspace")
