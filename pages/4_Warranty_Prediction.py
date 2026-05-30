from __future__ import annotations

from dataclasses import asdict

import pandas as pd
import streamlit as st

from backend import prediction, state, ui

state.ensure_dirs()

ui.page_header(
    "ML",
    "Warranty Prediction",
    "Optional: train models linking test results to warranty outcomes (requires 1A and 2B outputs).",
)

with st.expander("About this module", expanded=False):
    st.caption(
        "Trains separate LightGBM models for CVT and PowerTrain. "
        "Supplements the core 1A / 1B / 2A / 2B quality workflow."
    )

ui.section_label("Prerequisites")
warranty = state.load_dataframe(state.WARRANTY_CLEAN)
test_pivot = state.load_dataframe(state.TEST_CLEAN_PIVOT)

s1, s2 = st.columns(2)
s1.metric(
    "1A — Cleaned warranty",
    "Ready" if warranty is not None else "Required",
    f"{len(warranty):,} rows" if warranty is not None else "Run 1A first",
)
s2.metric(
    "2B — Cleaned test data",
    "Ready" if test_pivot is not None else "Required",
    f"{test_pivot.shape[0]:,} units" if test_pivot is not None else "Run 2B first",
)

components_file = st.file_uploader(
    "Component descriptions (.csv)",
    type=["csv"],
    key="components_upload",
    help="Columns: Component Description, Is Transmission Related",
)

target = st.radio(
    "Prediction target",
    options=[
        (prediction.TARGET_COMPONENT, "Component description"),
        (prediction.TARGET_GENERAL, "General warranty type"),
        (prediction.TARGET_BINARY, "Failure vs. no failure"),
    ],
    format_func=lambda x: x[1],
    index=1,
)

can_train = warranty is not None and test_pivot is not None and components_file is not None

if st.button("Train models", type="primary", disabled=not can_train):
    try:
        comp_df = pd.read_csv(components_file, encoding="unicode_escape")
        tx_components = (
            comp_df[comp_df["Is Transmission Related"].isin(["Y", 1, "1", True])]["Component Description"]
            .dropna()
            .tolist()
        )

        with st.spinner("Preparing datasets…"):
            cvt_pivot, pt_pivot = prediction.split_cvt_powertrain(test_pivot)
            cvt_with_y = prediction.attach_target(cvt_pivot, warranty, tx_components, target)
            pt_with_y = prediction.attach_target(pt_pivot, warranty, tx_components, target)

        metadata = {"target": target}
        family_results = {}

        for fam, df_fam in (("cvt", cvt_with_y), ("powertrain", pt_with_y)):
            if len(df_fam) == 0 or df_fam["y"].nunique() < 2:
                st.warning(f"{fam.upper()}: insufficient data — skipped.")
                continue

            with st.spinner(f"Training {fam.upper()}…"):
                model, le, feat_names, result = prediction.train_one(
                    df_fam, family=fam, target=target, out_dir=state.MODEL_DIR
                )

            with st.spinner(f"Explainability ({fam.upper()})…"):
                X_for_shap = df_fam.drop(columns=["SerialNumber", "y"]).select_dtypes(include="number")
                X_for_shap.columns = feat_names
                prediction.render_shap(
                    model,
                    X_for_shap,
                    state.MODEL_DIR / f"shap_{fam}.png",
                    title=f"{fam.upper()} — {target}",
                )

            state.save_model(model, f"{fam}_{target}_model")
            state.save_model(le, f"{fam}_{target}_le")
            state.save_json({"features": feat_names}, state.MODEL_DIR / f"{fam}_{target}_features.json")
            metadata[fam] = asdict(result)
            family_results[fam] = result

        state.save_json(metadata, state.MODEL_METADATA)
        st.success("Training complete.")

        for fam, result in family_results.items():
            ui.section_title(f"{fam.upper()} performance")
            a, b, c = st.columns(3)
            a.metric("Test accuracy", f"{result.accuracy_test*100:.1f}%")
            b.metric("Cross-validation", f"{result.cv_mean*100:.1f}%", f"± {result.cv_std*100:.1f}%")
            c.metric("Train / test", f"{result.n_train} / {result.n_test}")
            with st.expander("Classification report"):
                st.text(result.classification_report)
            shap_path = state.MODEL_DIR / f"shap_{fam}.png"
            if shap_path.exists():
                st.image(str(shap_path), use_container_width=True)
    except Exception as e:
        st.error(f"Training failed: {e}")

if not can_train:
    missing = []
    if warranty is None:
        missing.append("1A cleaned warranty")
    if test_pivot is None:
        missing.append("2B cleaned test data")
    if components_file is None:
        missing.append("component descriptions file")
    st.info("Required: " + ", ".join(missing))

meta = state.load_json(state.MODEL_METADATA)
if meta:
    st.markdown("---")
    ui.section_title("Last trained model")
    st.caption(f"Target: **{meta.get('target')}** · {state._mtime(state.MODEL_METADATA)}")
