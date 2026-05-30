import os
from io import BytesIO

import pandas as pd
import streamlit as st

from backend_1a import run_1a_pipeline

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="CNH / Data Mine Analytics Dashboard",
    layout="centered"
)

# =========================
# HELPER FUNCTIONS
# =========================
def convert_df_to_excel(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="classification_results")
    return output.getvalue()


def load_uploaded_file(uploaded_file, header_option="infer"):
    """
    Read uploaded csv/xlsx file into DataFrame.
    header_option:
        - "infer": pandas default header behavior
        - None: treat first row as data
    """
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file, header=header_option)
    return pd.read_excel(uploaded_file, header=header_option)


# =========================
# LOGOS / HEADER
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
cnh_logo = os.path.join(BASE_DIR, "img", "CNH_Industrial.jpg")
if os.path.exists(cnh_logo):
    st.image(cnh_logo, width=200)

st.title("CNH / Data Mine Dashboard")
st.write("Interactive dashboard for warranty classification, test analysis, workstation attribution, and predictive modeling.")

st.markdown("---")

# =========================
# SECTION 1A: LLM CLASSIFICATION
# =========================
st.header("Section 1A: LLM Classification")

default_prompt = """
You are classifying warranty root cause into exactly one label.

Labels:
Plant
Material
Design

Definitions:

Plant:
Manufacturing or assembly process issue.
Examples:
- Incorrect installation
- Loose or not tightened components
- Improper routing
- Missing parts
- Poor factory application (sealant, paint, etc.)
- Not fastened or assembled correctly

Material:
Defective, damaged, or failed component/material.
Examples:
- Cracked, broken, or damaged parts
- Leaking seals, gaskets, or O-rings
- Burst or torn components
- Faulty or weak material
- Component failure during normal use

Design:
Engineering or design issue.
Examples:
- Software mismatch
- Design flaw causing repeated failure
- System-level design weakness

Decision Rules:

1. If a part is described as leaking, cracked, torn, burst, or failed -> choose Material.
2. If the issue is due to incorrect assembly, loose/missing parts, or factory process -> choose Plant.
3. If both appear, choose the ROOT CAUSE:
   - Bad part -> Material
   - Bad assembly -> Plant
4. If neither clearly applies -> choose Design.
5. Output EXACTLY one word: Plant or Material or Design.
6. Do NOT explain.

Warranty text:
{text}

Answer:
"""

llm_prompt = st.text_area(
    "Enter LLM Prompt",
    value=default_prompt,
    height=300
)

warranty_file = st.file_uploader(
    "Upload Warranty Data Spreadsheet",
    type=["csv", "xlsx"],
    key="warranty_upload"
)

has_header_1a = st.checkbox("My 1A file has column headers", value=True, key="header_1a")
header_setting_1a = "infer" if has_header_1a else None

text_col_index = st.number_input(
    "Text column index for warranty comment (0-based)",
    min_value=0,
    value=1,
    step=1,
    key="text_col_index_1a"
)

run_1a = st.button("Run 1A Classification", key="run_1a_btn")

if warranty_file is not None:
    try:
        df_warranty = load_uploaded_file(warranty_file, header_option=header_setting_1a)

        st.subheader("Preview Warranty Data")
        st.dataframe(df_warranty.head())

        if run_1a:
            with st.spinner("Running 1A classification..."):
                df_result = run_1a_pipeline(df_warranty, 
                                            text_col_index=text_col_index, 
                                            prompt_template=llm_promp
                                           )

            st.success("1A classification complete.")

            st.subheader("Classification Results Preview")
            st.dataframe(df_result.head(20))

            if not df_result.empty:
                st.subheader("1A Summary")

                total_rows = len(df_result)
                avg_conf = df_result["confidence"].mean()

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Classified Rows", total_rows)
                with col2:
                    st.metric("Average Confidence", f"{avg_conf:.3f}")

                st.write("Category Counts")
                st.bar_chart(df_result["category"].value_counts())

                st.write("Source Counts")
                st.bar_chart(df_result["source"].value_counts())

                low_conf_df = df_result[df_result["confidence"] < 0.75]
                st.write("Low-Confidence Claims (< 0.75)")
                if low_conf_df.empty:
                    st.success("No low-confidence claims found.")
                else:
                    st.dataframe(low_conf_df)

            excel_data = convert_df_to_excel(df_result)

            st.download_button(
                label="Download Classified Excel File",
                data=excel_data,
                file_name="classified_claims_new.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_1a"
            )

    except Exception as e:
        st.error(f"Error while processing 1A file: {e}")

st.markdown("---")

# =========================
# SECTION 1B: Z-SCORE CALCULATION
# =========================
st.header("Section 1B: Transmission Test Z-Score Calculation")

z_threshold = st.number_input(
    "Number of Standard Deviations (Z-score threshold)",
    min_value=0.0,
    value=1.0,
    step=0.1,
    key="z_threshold_1b"
)

test_file = st.file_uploader(
    "Upload Transmission Test Data",
    type=["csv", "xlsx"],
    key="test_upload"
)

has_header_1b = st.checkbox("My 1B file has column headers", value=True, key="header_1b")
header_setting_1b = "infer" if has_header_1b else None

run_1b = st.button("Run 1B Z-Score Analysis", key="run_1b_btn")

if test_file is not None:
    try:
        df_test = load_uploaded_file(test_file, header_option=header_setting_1b)
        st.subheader("Preview Test Data")
        st.dataframe(df_test.head())

        if run_1b:
            st.success("1B analysis triggered.")
            st.write(f"Current Z-score threshold: {z_threshold}")
            st.info("1B calculation logic not fully connected yet.")
    except Exception as e:
        st.error(f"Error while processing 1B file: {e}")

st.markdown("---")

# =========================
# SECTION 2A: WORKSTATION ATTRIBUTION
# =========================
st.header("Section 2A: Attribute Warranty Failures to Assembly Stations")

workstation_file = st.file_uploader(
    "Upload Workstation Data",
    type=["csv", "xlsx"],
    key="workstation_upload"
)

has_header_2a = st.checkbox("My 2A file has column headers", value=True, key="header_2a")
header_setting_2a = "infer" if has_header_2a else None

run_2a = st.button("Run 2A Workstation Attribution", key="run_2a_btn")

if workstation_file is not None:
    try:
        df_workstation = load_uploaded_file(workstation_file, header_option=header_setting_2a)

        st.subheader("Preview Workstation Data")
        st.dataframe(df_workstation.head())

        if run_2a:
            st.success("2A attribution triggered.")
            st.subheader("Failure Attribution Pie Chart")

            if "station" in df_workstation.columns:
                pie_data = df_workstation["station"].value_counts()
                fig = pie_data.plot.pie(autopct="%1.1f%%").figure
                st.pyplot(fig)
            else:
                st.info("Add a 'station' column to visualize pie chart.")
    except Exception as e:
        st.error(f"Error while processing 2A file: {e}")

st.markdown("---")

# =========================
# SECTION 2B: PREDICTIVE MODEL
# =========================
st.header("Section 2B: Predictive Modeling")

component_file = st.file_uploader(
    "Upload Unique Component Descriptions",
    type=["csv", "xlsx"],
    key="component_upload"
)

has_header_2b = st.checkbox("My 2B file has column headers", value=True, key="header_2b")
header_setting_2b = "infer" if has_header_2b else None

run_2b_train = st.button("Train 2B Predictive Model", key="train_2b_btn")
run_2b_predict = st.button("Run 2B Predictive Model", key="run_2b_btn")

if component_file is not None:
    try:
        df_components = load_uploaded_file(component_file, header_option=header_setting_2b)
        st.subheader("Preview Component Data")
        st.dataframe(df_components.head())

        if run_2b_train:
            st.success("2B model training triggered (NOT IMPLEMENTED YET).")

        if run_2b_predict:
            st.write("Accuracy: __%")
            st.success("2B model execution triggered (NOT IMPLEMENTED YET).")

    except Exception as e:
        st.error(f"Error while processing 2B file: {e}")
else:
    # optional: still allow button feedback if user presses without file
    if run_2b_train:
        st.warning("Please upload a 2B input file before training.")
    if run_2b_predict:
        st.warning("Please upload a 2B input file before running prediction.")