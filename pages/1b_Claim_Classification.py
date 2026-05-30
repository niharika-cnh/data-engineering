from __future__ import annotations

import pandas as pd
import streamlit as st

from backend import llm_classify, nav_pages, ollama_client, state, ui

state.ensure_dirs()

ALLOWED_CATEGORIES = {"Plant", "Material", "Design", "SKIP"}


def _display_classification_results(df: pd.DataFrame) -> None:
    """Render metrics, optional issue banner, table, and download."""
    if df is None or df.empty:
        st.info("No classification rows to display.")
        return

    df = df.copy()
    if "category" in df.columns:
        df["Classification"] = df["category"]

    with st.container(border=True):
        ui.review_panel(
            "1B · Classification output",
            "Review assignments: **Plant** (assembly/process), **Material** (component failure), "
            "**Design/Engineering** (design root cause). Plant-related claims support **2A** Pareto.",
        )

    if "category" not in df.columns:
        st.error("Classification output is missing a `category` column.")
        st.dataframe(df, use_container_width=True, height=380)
        return

    cats = df["category"].astype(str)
    errors = cats.isin(["ERROR", "TIMEOUT", "TODO", "INVALID"])
    n_err = int(errors.sum())
    n_ok = int(cats.isin(ALLOWED_CATEGORIES).sum())

    if n_err:
        st.error(
            f"**{n_err}** row(s) could not be classified (often **Ollama model not installed**). "
            "Pull the model shown in *Ollama status*, then run classification again. "
            "Rows with keyword matches may still show Plant/Material from rules."
        )
        if "classify_debug" in df.columns:
            with st.expander("View classification errors (debug)", expanded=False):
                st.dataframe(
                    df.loc[errors, ["category", "classify_debug"] + [c for c in ("Dealer Comments",) if c in df.columns]],
                    use_container_width=True,
                )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total rows", f"{len(df):,}")
    vc = cats.value_counts()
    c2.metric("Plant", f"{int(vc.get('Plant', 0)):,}", help="→ 2A Pareto")
    c3.metric("Material", f"{int(vc.get('Material', 0)):,}")
    c4.metric("Design / Engineering", f"{int(vc.get('Design', 0)):,}")

    if "confidence" in df.columns:
        conf = pd.to_numeric(df.loc[cats.isin(ALLOWED_CATEGORIES), "confidence"], errors="coerce")
        if conf.notna().any():
            st.metric("Avg. confidence (classified)", f"{conf.mean():.2f}")

    review = df[cats.isin(ALLOWED_CATEGORIES)]
    if not review.empty and "category" in review.columns:
        st.bar_chart(review["category"].value_counts())

    ui.section_label("Classified claims table")
    hide_cols = {"classify_debug"}
    # Avoid duplicate empty legacy column when `category` holds the result.
    if "category" in df.columns and "Classification" in df.columns:
        hide_cols.add("Classification")
    show_cols = [c for c in df.columns if c not in hide_cols]
    st.caption("**category** = Plant / Material / Design (from rules or Ollama).")
    st.dataframe(df[show_cols], use_container_width=True, height=420)

    st.download_button(
        "Download warranty_classified_plant_material_design.csv",
        data=df.to_csv(index=False).encode(),
        file_name="warranty_classified_plant_material_design.csv",
        mime="text/csv",
        type="primary",
        key="download_classified_cached",
    )
    st.page_link(nav_pages.app_pages()[3], label="Continue to 2A · Plant Pareto Analysis →")


ui.page_header(
    "1B",
    "1B · Warranty Claim Classification",
    "Separate Plant, Material, and Design/Engineering claims. Plant-related results feed 2A Pareto analysis.",
)

cached = state.load_dataframe(state.WARRANTY_CLEAN)
if cached is None:
    st.warning("Complete **1A · Warranty Preparation** before running classification.")
    st.page_link(nav_pages.app_pages()[1], label="Go to 1A · Warranty Preparation →")
else:
    ui.section_label("Classification", "Uses cleaned warranty output from step 1A")

    with st.expander("Model & prompt settings", expanded=False):
        col_p, col_k, col_m = st.columns([1, 2, 2])
        provider = col_p.selectbox("Provider", ["ollama", "openai", "anthropic"], index=0)
        api_key = col_k.text_input(
            "API key" + (" (not required for Ollama)" if provider == "ollama" else ""),
            type="password",
        )
        default_model = {
            "ollama": ollama_client.ollama_model_default(),
            "openai": "gpt-4o-mini",
            "anthropic": "claude-sonnet-4-6",
        }[provider]
        model_name = col_m.text_input(
            "Model",
            value=default_model,
            key="1b_model_name",
            help=(
                f"Default local test model: {ollama_client.DEFAULT_OLLAMA_MODEL}. "
                f"Optional production model: {ollama_client.ALTERNATE_OLLAMA_MODEL}."
            ),
        )
        if provider == "ollama":
            st.caption(
                f"Ollama URL: `{ollama_client.ollama_base_url()}` · "
                f"Default: `{ollama_client.DEFAULT_OLLAMA_MODEL}` · "
                f"Also supported: `{ollama_client.ALTERNATE_OLLAMA_MODEL}`"
            )
        text_col = st.selectbox(
            "Comment column",
            options=list(cached.columns),
            index=list(cached.columns).index("Dealer Comments") if "Dealer Comments" in cached.columns else 0,
        )
        prompt = st.text_area(
            "Classification prompt ({text} = dealer comment)",
            value=llm_classify.DEFAULT_PROMPT_TEMPLATE,
            height=180,
        )
        sample_size = st.number_input("Row limit (0 = all)", min_value=0, value=20, step=10)

    selected_model = (model_name or ollama_client.ollama_model_default()).strip()

    ui.section_label("Ollama status")
    if provider == "ollama":
        ready, ready_msg = ollama_client.check_ollama_ready(selected_model)
        installed = ollama_client.list_ollama_models()
        if installed:
            st.caption(f"Installed models: {', '.join(installed)}")
        if ready:
            st.success("Ollama detected. Classification is available.")
            st.caption(ready_msg)
        else:
            st.warning(
                "Ollama is required only for new claim classification runs. "
                "Start Ollama locally before running classification."
            )
            if "ollama pull" in ready_msg:
                st.markdown(ready_msg.split("\n\n")[0])
                st.code(ready_msg.split("\n\n")[-1].strip(), language="powershell")
            else:
                st.markdown(ready_msg)
    else:
        st.info("Using a cloud provider — Ollama is not required for this run.")

    with st.expander(
        "How to start Ollama locally",
        expanded=provider == "ollama" and not ollama_client.check_ollama_ready(selected_model)[0],
    ):
        st.markdown(
            """
**1. Check installation**
```powershell
ollama --version
```

**2. Start Ollama**
```powershell
ollama serve
```

**3. Pull the default model** (must match the **Model** field above)
```powershell
ollama pull llama3.2:1b
```

**4. Other supported models** (change **Model** in settings to match)
```powershell
ollama pull llama3.2:3b
ollama pull gemma3:27b-8
```

**5. Run the app**
```powershell
streamlit run app.py
```
            """
        )

    needs_ollama = provider == "ollama"
    ollama_ready = True
    if needs_ollama:
        ollama_ready, _ = ollama_client.check_ollama_ready(selected_model)
    run_disabled = needs_ollama and not ollama_ready
    if run_disabled:
        st.caption("Install the model above to enable **Run classification** (saved results below stay available).")

    if st.button("Run classification", type="primary", disabled=run_disabled):
        df_input = cached if sample_size == 0 else cached.head(int(sample_size))
        progress = st.progress(0, text="Starting…")

        def cb(i, total):
            pct = int(i / max(total, 1) * 100)
            progress.progress(min(pct, 100), text=f"Processing {i}/{total}")

        try:
            df_out = llm_classify.classify_dataframe(
                df_input,
                text_column=text_col,
                provider=provider,
                api_key=api_key,
                model_name=model_name,
                prompt_template=prompt,
                progress_cb=cb,
                ollama_base_url_override=ollama_client.ollama_base_url(),
            )
            progress.empty()

            err_n = int(df_out["category"].astype(str).isin(["ERROR", "TIMEOUT"]).sum()) if "category" in df_out.columns else 0
            try:
                state.save_dataframe(df_out, state.WARRANTY_CLASSIFIED)
            except Exception as save_err:
                st.warning(f"Could not save to artifacts: {save_err}. Showing results below.")

            st.session_state["1b_classified_df"] = df_out

            if err_n:
                st.warning(
                    f"Finished {len(df_out):,} rows — **{err_n}** need attention (see table). "
                    "If all rows show ERROR, run `ollama pull` for your model name."
                )
            else:
                st.success(f"Classified {len(df_out):,} claims (Plant / Material / Design).")
        except Exception as e:
            progress.empty()
            st.error(f"Classification failed: {e}")

    display_df = st.session_state.get("1b_classified_df")
    if display_df is None:
        display_df = state.load_dataframe(state.WARRANTY_CLASSIFIED)

    if display_df is not None:
        st.markdown("---")
        _display_classification_results(display_df)
