"""Single source of truth for Streamlit multipage navigation (UI only)."""

from __future__ import annotations

import streamlit as st

# Workflow module: (badge, title, description, metadata, cta_label, page_index)
WorkflowModule = tuple[str, str, str, str, str, int]


def app_pages() -> list[st.Page]:
    """Pages without sidebar icons — keeps top nav compact and unclipped."""
    return [
        st.Page("home.py", title="Home", default=True),
        st.Page("pages/1a_Warranty_Preparation.py", title="1A · Warranty Preparation"),
        st.Page("pages/1b_Claim_Classification.py", title="1B · Claim Classification"),
        st.Page("pages/3_Pareto_Analysis.py", title="2A · Plant Pareto Analysis"),
        st.Page("pages/2_Part_B_Warranty_Prediction.py", title="2B · Test Analytics"),
        st.Page("pages/4_Warranty_Prediction.py", title="Warranty Prediction"),
    ]


TOP_NAV: list[tuple[int, str]] = [
    (0, "Home"),
    (1, "1A Prep"),
    (2, "1B Classify"),
    (3, "2A Pareto"),
    (4, "2B Tests"),
    (5, "Prediction"),
]

WORKFLOW_MODULES: list[WorkflowModule] = [
    (
        "1A",
        "Warranty Preparation",
        "Clean and standardize raw warranty claim files for classification and downstream analysis.",
        "Input: warranty claims",
        "Open 1A",
        1,
    ),
    (
        "1B",
        "Claim Classification",
        "Classify claims into Plant, Material, or Design/Engineering categories for review.",
        "Output: 2M/1D assignment",
        "Open 1B",
        2,
    ),
    (
        "2A",
        "Plant Pareto Analysis",
        "Prioritize plant-controlled warranty contributors by station, process, frequency, or cost.",
        "Focus: plant-related claims",
        "Open 2A",
        3,
    ),
    (
        "2B",
        "Test Abnormality Review",
        "Identify accepted test results that exceed the selected Z-score threshold while remaining within min/max limits.",
        "Default threshold: Z > 1",
        "Open 2B",
        4,
    ),
]

EXECUTIVE_SUMMARY: list[tuple[str, str]] = [
    ("Workflow", "1A–2B analytics pipeline"),
    ("Primary users", "Manufacturing engineering & quality"),
    ("Current focus", "Z-score abnormality review"),
    ("Output", "Downloadable review files"),
]
