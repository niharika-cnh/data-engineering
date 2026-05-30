# CNH Warranty & Test Analytics — Change Log

**Repository:** [niharika-cnh/data-engineering](https://github.com/niharika-cnh/data-engineering)  
**Prepared for:** CNH stakeholders (e.g. Mike) and project teammates  
**Last updated:** 2026-05-31

---

## Overview

This document records dashboard updates in two parts:

1. **Code & data changes** — requested in the **May 29, 2026** meeting (Mike). These affect Z-score logic, exports, and how results are computed or saved. Backend/model pipelines are unchanged except where noted below.
2. **UI & UX changes** — visual layout, navigation, branding, and presentation only. No change to core data processing rules unless a control default is exposed in the UI.

**Workflow preserved throughout:** **1A** → **1B** → **2A** → **2B** (plus optional **Warranty Prediction**).

---

## Meeting context (May 29, 2026)

| # | Request | Addressed in |
|---|---------|----------------|
| 1 | Change Z-score abnormal threshold from **2.0** to **1.0** | Code + UI (2B) |
| 2 | Export test rows where \|z\| > threshold but value still within min/max; summary **by test name** | Code + UI (2B) |
| 3 | Show and download warranty claims with **Plant / Material / Design** classification | Code + UI (1B, Home) |
| 4 | Remove Purdue branding; CNH-only internal tool | UI only |

---

# Part 1 — Code & data changes (May 29 meeting)

**Date basis:** Per last meeting — **May 29, 2026**  
**Scope:** Backend helpers, defaults, saved artifacts, and download contents. No changes to Pareto engine, warranty cleaning rules, or LightGBM training logic beyond using the new Z-score default when test data is processed.

---

## 1.1 Z-score threshold default (2.0 → 1.0)

| Location | Change |
|----------|--------|
| `backend/clean_test.py` | `clean_test_data(..., z_threshold=1.0)` — was `2.0` |
| `pages/2_Part_B_Warranty_Prediction.py` | UI control default `1.0` (display only; calls same backend) |
| `frontend.py` | Legacy entry default `1.0` (not used by `app.py`) |

**Pass/fail rule (unchanged):** A row **passes** when `|z_score| < threshold` **and** `Minimum ≤ Value ≤ Maximum`.

**Note:** Re-run **2B · Process test data** after deploy so saved `artifacts/` reflect threshold **1.0** in pass/fail flags.

---

## 1.2 Abnormal-but-accepted test results (new logic)

**New functions in `backend/clean_test.py`:**

| Function | Purpose |
|----------|---------|
| `filter_abnormal_accepted(df, z_threshold)` | Rows where `\|z_score\| > threshold` and value is still within min/max |
| `summarize_abnormal_accepted_by_test(df)` | Count per `Test` name, sorted descending |

**Definition (Mike review):**

- `|z_score| >` selected threshold (default **1.0**)
- `Value >= Minimum`
- `Value <= Maximum`

**Download filenames (fixed labels for review package):**

| File | Contents |
|------|----------|
| `abnormal_accepted_test_results_z_gt_1.csv` | All matching rows (long format) |
| `abnormal_accepted_test_summary_by_test.csv` | Count per test name |

The filter uses the **threshold selected in the UI** at review time; filenames keep `_z_gt_1` as the agreed export name.

---

## 1.3 Warranty classification — export, columns, and Ollama integration

| Output | Description |
|--------|-------------|
| `warranty_classified_plant_material_design.csv` | Full cleaned warranty rows plus classification fields |

**Canonical result column:** `category` = **Plant**, **Material**, or **Design** (Design = engineering/design in the prompt).

**Supporting columns:**

| Column | Meaning |
|--------|---------|
| `confidence` | Score for the assigned label |
| `classify_source` | `rule` (keyword match), `llm` (Ollama), or `skip` |
| `classify_debug` | Raw model output or error detail for troubleshooting |

**Legacy `Classification` column:** 1A no longer creates an empty placeholder. After **1B** runs, `Classification` is set equal to `category` for backward compatibility in CSV export. The **1B table hides** the duplicate `Classification` column when `category` is present.

**`backend/llm_classify.py` updates:**

- `classify_dataframe()` keeps all 1A warranty columns and appends classification fields row-by-row.
- `normalize_category_label()` maps LLM output to Plant / Material / Design; **INVALID** may fall back to **Design** when parseable.
- Ollama host/model passed through to `backend_1a.classify_with_ollama()`.

**`backend/ollama_client.py` (new):** Preflight via `/api/tags`; default model **`llama3.2:1b`**; **`gemma3:27b-8`** still supported via UI.

---

## 1.4 Code files modified (cumulative — May 29 meeting + follow-up)

| File | What changed |
|------|----------------|
| `backend/clean_test.py` | Default threshold **1.0**; `filter_abnormal_accepted`; `summarize_abnormal_accepted_by_test` |
| `backend/clean_warranty.py` | Removed empty `Classification` placeholder; 1B writes `category` |
| `backend/llm_classify.py` | Full-row export; `normalize_category_label`; `classify_source` / `classify_debug`; sync `Classification` ← `category` |
| `backend/ollama_client.py` | **New** — URL/model defaults, `list_ollama_models`, `check_ollama_ready`, model install check |
| `backend_1a.py` | Env-based Ollama URL/model; clearer 404 when model not pulled; improved `extract_label` |
| `backend/state.py` | Parquet save typing for classification columns; artifact paths |
| `pages/2_Part_B_Warranty_Prediction.py` | Abnormal-but-accepted section, downloads, artifact refresh note |
| `pages/1b_Claim_Classification.py` | Ollama status, model preflight, guarded run button, results table, error banner |
| `pages/1a_Warranty_Preparation.py` | Warranty clean only (split from legacy Part A page) |
| `home.py` | Optional classified/pareto preview + download |
| `MIKE_RUN_GUIDE.md` | **New** — local vs hosted Streamlit, Ollama steps, Mike file checklist |
| `frontend.py` | Threshold default **1.0** only (legacy; not main app) |

---

## 1.5 How to test — code / data behavior

1. **2B — Z-score & abnormal-but-accepted**
   - `streamlit run app.py` → **2B · Test Analytics**
   - Confirm threshold default **1.0**
   - Upload test file → **Process test data**
   - Verify abnormal table and both CSV downloads
   - Change threshold without re-processing — table updates from cached long data

2. **1B — Classification export**
   - Complete **1A**, run classification on **1B** (Ollama required for new runs)
   - Download `warranty_classified_plant_material_design.csv`

3. **Artifacts**
   - Saved under `artifacts/` (see Part 2 for clearing outputs)

---

## 1.6 Code assumptions

- Test columns: `Parameter`, `Value`, `Minimum`, `Maximum`, `Test`, `SerialNumber`, etc.
- Engineering classification = **Design** in `category` column
- Ollama must be running locally for **new** 1B classifications (`http://127.0.0.1:11434`, default model `llama3.2:1b`)

---

# Part 2 — UI & UX changes

**Implementation dates:** Primarily **2026-05-30** (iterative UI refresh after May 29 meeting)  
**Scope:** Layout, navigation, CSS, labels, branding only. Does not alter Mike’s Z-score or abnormal-but-accepted **logic**.

---

## 2.1 Navigation & app shell

| Item | Detail |
|------|--------|
| Entry point | `streamlit run app.py` |
| Sidebar | Hidden (CSS); collapsed in `set_page_config` |
| Primary nav | Sticky **top bar** with `st.page_link()` |
| Streamlit pages | `st.navigation(..., position="hidden")` |
| Page registry | `backend/nav_pages.py` — single source for routes and labels |

**Top navigation labels (short, no clipping):**

| Link | Page |
|------|------|
| Home | Landing |
| 1A Prep | Warranty Preparation |
| 1B Classify | Claim Classification |
| 2A Pareto | Plant Pareto Analysis |
| 2B Tests | Test Analytics |
| Prediction | Warranty Prediction |

**Bug fix:** `KeyError: 'url_pathname'` — call `st.navigation()` before `st.page_link()`; pass `st.Page` objects, not file path strings.

---

## 2.2 Home page

| Element | Description |
|---------|-------------|
| Hero | Compact charcoal banner; title **Warranty & Test Analytics Platform**; subtitle; badges (Racine Plant, Warranty Analytics, Test Stand Review, Internal Use) |
| Workflow grid | 2×2 cards: **1A**, **1B**, **2A**, **2B** with badge, title, description, metadata, **Open 1A** / **Open 1B** / etc. buttons inside each card |
| Status | **Current workflow status** — compact cards with step badges |
| Help | **How to use this platform** expander |
| Outputs | **Recent outputs** expander (classification chart, Pareto snapshot when artifacts exist) |

**Removed (UI preference):**

- Executive summary strip (Workflow / Primary users / Current focus / Output)
- **Warranty & Test** subtitle under logo in top nav (logo + **CNH Analytics** only)

---

## 2.3 Page-level UI (1A / 1B / 2A / 2B / Prediction)

Each workflow page uses a **step banner**: badge + title + one-line business purpose.

| Step | Page file | UI highlights |
|------|-----------|----------------|
| **1A** | `pages/1a_Warranty_Preparation.py` | Upload, processing options in expander, cleaned table preview, download |
| **1B** | `pages/1b_Claim_Classification.py` | Ollama status + installed model list; `ollama pull <model>` when missing; **Plant / Material / Design** metrics; **`category`** table (not empty `Classification`); error/debug expander; link to 2A |
| **2A** | `pages/3_Pareto_Analysis.py` | Plant Pareto explanation; uploads; KPI metrics; charts (dedicated page, was formerly a tab) |
| **2B** | `pages/2_Part_B_Warranty_Prediction.py` | Z-score control (default **1.0**); **2B · Abnormal but Accepted Test Results** review panel; **Download Detailed Abnormal Results** / **Download Test-Level Summary** |
| **ML** | `pages/4_Warranty_Prediction.py` | Prerequisites; training UI (dedicated page, was formerly a tab) |

**Legacy:** `pages/1_Part_A_Warranty_Classification.py` — redirect to 1A/1B only; not in navigation.

---

## 2.4 Branding & visual style

| Item | Detail |
|------|--------|
| Purdue logo | Removed / hidden on all primary pages |
| CNH logo | Top navigation (subtle white pad on dark bar) |
| Colors | Charcoal/navy `#161b26`, accent red `#E40521`, neutral grays |
| Typography | Inter (Google Fonts) with system fallback |
| Max width | ~1200px content container |
| Theme | `.streamlit/config.toml` — CNH red primary |

**Wording:** Internal analytics / platform / workflow language — no academic or project-demo phrasing.

---

## 2.5 UI files modified (cumulative)

| File | Role |
|------|------|
| `backend/ui.py` | Global CSS, `render_top_nav`, hero, workflow cards, page headers, review panels, status strip |
| `backend/nav_pages.py` | Page list, nav labels, workflow card copy |
| `app.py` | Page config, styles, navigation, top nav |
| `home.py` | Landing layout |
| `pages/1a_Warranty_Preparation.py` | 1A UI |
| `pages/1b_Claim_Classification.py` | 1B UI |
| `pages/3_Pareto_Analysis.py` | 2A UI |
| `pages/2_Part_B_Warranty_Prediction.py` | 2B UI |
| `pages/4_Warranty_Prediction.py` | Prediction UI |
| `pages/1_Part_A_Warranty_Classification.py` | Legacy redirect |
| `backend/state.py` | Pipeline status labels (1A/1B/2A/2B hints) |

**Not used for main app:** `frontend.py` (legacy single-page dashboard; minimal threshold/branding touch only).

---

## 2.6 How to test — UI

```bash
streamlit run app.py
```

Hard-refresh browser (**Ctrl+F5**).

| Check | Where |
|-------|--------|
| Top nav, no sidebar | All pages |
| Home hero + 2×2 cards with in-card buttons | Home |
| Step banners | 1A, 1B, 2A, 2B, Prediction |
| 2B abnormal section + download labels | 2B · Test Analytics |
| No Purdue logo | Home / header |

---

## 2.7 UI deployment notes

- Deploy all `pages/*.py`, `backend/ui.py`, `backend/nav_pages.py`, `app.py`, `home.py`
- Streamlit **≥ 1.36** recommended (`position="hidden"`, `st.page_link`, `st.container(border=True)`)
- Google Fonts CDN used for Inter (offline fallback to system fonts)
- CSS `:has()` used for card hover (modern browsers)
- Confirm `.gitignore` excludes `artifacts/`, `.venv/`, `.env`, and large raw data before publishing to GitHub.

---

## Quick reference — clearing saved outputs

To reset all cached runs (no code change):

```powershell
Remove-Item -Recurse -Force .\artifacts
```

Then refresh the app. The `artifacts` folder is recreated on the next successful run.

---

## Mike Request Verification and Output Regeneration

**Date:** 2026-05-30

### What was verified

| Mike request (2026-05-29) | Status |
|---------------------------|--------|
| Z-score abnormal threshold default **1.0** (was 2.0) in backend + 2B UI | Verified in `backend/clean_test.py`, `pages/2_Part_B_Warranty_Prediction.py`, legacy `frontend.py` |
| Abnormal-but-accepted: `\|z\| > threshold` AND value within min/max | Verified in `filter_abnormal_accepted()` — uses `>`, `abs(z_score)`, inclusive min/max |
| Summary by **Test** name, count descending | Verified in `summarize_abnormal_accepted_by_test()` |
| Warranty export with Plant / Material / Design + original claim rows | Verified on **1B**; `classify_dataframe()` now merges classification columns onto the full cleaned warranty dataframe |
| Purdue branding removed from app UI | Verified (no Purdue references in `.py` pages / `backend/ui.py`) |

### Files checked

- `backend/clean_test.py` — `z_threshold=1.0`, `filter_abnormal_accepted`, `summarize_abnormal_accepted_by_test`
- `pages/2_Part_B_Warranty_Prediction.py` — threshold control default 1.0, review section, CSV downloads, artifact refresh note
- `pages/1b_Claim_Classification.py` — classified table + download
- `backend/llm_classify.py` — full-row classification export
- `backend/state.py` — artifact paths under `artifacts/`
- `frontend.py` — legacy entry; threshold default 1.0 (not primary; use `app.py`)

### Output files that must be regenerated

| File | Page | Artifact / action |
|------|------|-------------------|
| `warranty_classified_plant_material_design.csv` | 1B · Claim Classification | Re-run **Run classification** after 1A (saves `artifacts/warranty_classified.parquet`) |
| `abnormal_accepted_test_results_z_gt_1.csv` | 2B · Test Analytics | Re-run **Process test data** with threshold **1.0** (uses `artifacts/test_data_long.parquet`) |
| `abnormal_accepted_test_summary_by_test.csv` | 2B · Test Analytics | Same as above (derived from abnormal-but-accepted filter) |

**Note:** Saved test parquet may still contain `Passed` flags computed under an older threshold. **Re-run Process test data** after any Z-score threshold change to refresh saved artifacts. The abnormal-but-accepted tables re-filter using the current UI threshold and stored `z_score` values; pass/fail pivot columns require a full reprocess.

### Steps to regenerate outputs

1. **Environment**
   ```powershell
   cd "<project-root>"
   .\.venv\Scripts\activate
   streamlit run app.py
   ```
2. **Warranty classification CSV**
   - **1A · Warranty Preparation** → upload warranty file → process/save.
   - **1B · Claim Classification** → confirm Ollama is running (default model `llama3.2:1b`) → **Run classification** → **Download warranty_classified_plant_material_design.csv**.
3. **Abnormal-but-accepted CSVs**
   - **2B · Test Analytics** → confirm **Z-score abnormality threshold** = **1.0** → upload test file → **Process test data** → download both CSVs from **2B · Abnormal but Accepted Test Results**.
4. **Optional full reset**
   ```powershell
   Remove-Item -Recurse -Force .\artifacts
   ```
   Then repeat steps 2–3.

### Assumptions

- Download filenames use `_z_gt_1` as the Mike-request label; the filter uses the **selected** threshold (default 1.0), not a hard-coded constant in code.
- Classification requires a running Ollama instance (or another configured provider when implemented).
- `README.md` may still mention Purdue academically; the Streamlit app UI is CNH-only.

---

## Ollama default model — llama3.2:1b (local testing)

**Date:** 2026-05-30

- **Default Ollama model** for 1B is **`llama3.2:1b`** (`backend/ollama_client.py`, editable on **1B → Model**).
- **`gemma3:27b-8`** remains supported; change the **Model** field and run `ollama pull gemma3:27b-8`.
- **Run classification** is enabled only when the selected model appears in `ollama list` / `/api/tags`; otherwise the page shows `ollama pull <selected_model>`.

---

## Ollama Local Setup and Classification Guardrails

**Date:** 2026-05-30

### Files changed

| File | Change |
|------|--------|
| `backend/ollama_client.py` | **New** — `check_ollama_available()`, `ollama_base_url()`, `ollama_model_default()` |
| `backend_1a.py` | Defaults from `OLLAMA_BASE_URL` / `OLLAMA_HOST` and `OLLAMA_MODEL` env vars |
| `backend/llm_classify.py` | Passes Ollama host into `classify_with_ollama`; lazy import only on classify |
| `pages/1b_Claim_Classification.py` | Ollama status, setup expander, guarded **Run classification** |
| `MIKE_RUN_GUIDE.md` | **New** — hosted vs local, Ollama steps, Streamlit Cloud limits |

### Ollama scope

- Ollama HTTP calls occur only when **1B · Claim Classification** runs with provider **ollama** (`backend/llm_classify` → `backend_1a.classify_with_ollama`).
- **1A, 2A, 2B, Prediction, Home** do not import or call Ollama at page load.
- Legacy `frontend.py` still references `run_1a_pipeline` (Ollama); primary entry is `app.py` → multipage workflow.

### Status check (1B)

- Lists **installed models** from `ollama list` / `/api/tags`.
- **Ready:** “Ollama detected. Classification is available.”
- **Not ready:** Warning + copyable command `ollama pull <selected_model>` when the **Model** field does not match an installed tag.
- **Run classification** disabled until the selected model is installed (server up + model in `/api/tags`); saved artifacts remain viewable/downloadable.
- **Session display:** Last run also kept in `st.session_state["1b_classified_df"]` so the table appears immediately after classification.

### Local setup commands

Documented in **1B** expander *How to start Ollama locally* and in `MIKE_RUN_GUIDE.md`:

`ollama --version` → `ollama serve` → `ollama pull llama3.2:1b` (or `ollama pull llama3.2:3b`) → `streamlit run app.py`

### Model configurability

| Setting | Default | Override |
|---------|---------|----------|
| Base URL | `http://127.0.0.1:11434` | `OLLAMA_BASE_URL` or `OLLAMA_HOST` |
| Model | `llama3.2:1b` | `OLLAMA_MODEL` env or **Model** field on 1B |

### Streamlit Cloud limitation

- Cloud cannot reach `127.0.0.1:11434` on the user’s laptop.
- **New** 1B classifications require local Ollama (or a future cloud LLM provider).
- **2B Test Analytics** works on Cloud without Ollama.

---

## Latest changes summary (2026-05-31)

| Area | Change |
|------|--------|
| **1B classification** | Use **`category`** for Plant / Material / Design; fixed empty **`Classification`** column from 1A |
| **Export** | CSV includes all warranty fields + `category`, `confidence`, `classify_source`, `classify_debug` |
| **Ollama** | Default **`llama3.2:1b`**; preflight checks model in `/api/tags`; shows `ollama pull <model>` if missing |
| **Alternates** | **`gemma3:27b-8`**, **`llama3.2:3b`** still supported via editable **Model** field |
| **Errors** | Rows with `ERROR` / `TIMEOUT` show debug panel; often caused by model not pulled or corporate network blocking `ollama pull` |
| **2B** | Unchanged in this pass (Z-score **1.0**, abnormal-but-accepted CSVs per Mike) |
| **Docs** | `MIKE_RUN_GUIDE.md` — hosted vs local, Ollama, regeneration steps |

---

## Document history

| Date | Update |
|------|--------|
| 2026-05-29 | Meeting requirements captured → **Part 1** (code/data) |
| 2026-05-30 | UI refresh, navigation, enterprise layout → **Part 2** |
| 2026-05-30 | Changelog consolidated; code vs UI separated; executive strip and nav subtitle removed |
| 2026-05-30 | Mike request verification section; classification export merges full warranty rows |
| 2026-05-30 | Ollama local setup, 1B guardrails, `MIKE_RUN_GUIDE.md` |
| 2026-05-30 | Default Ollama model `llama3.2:1b`; model preflight via /api/tags; `gemma3:27b-8` still supported |
| 2026-05-31 | Changelog refresh: `category` vs `Classification`, llm_classify/ollama_client updates, 1B UI status/pull command, latest summary section |
