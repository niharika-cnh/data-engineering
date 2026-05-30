# CNH Data Engineering and Systems Connectivity

Streamlit dashboard for the CNH × Purdue Data Mine warranty / test-data project.

## Pages

- **Dashboard** (`app.py`) — pipeline status, Part 2A Pareto + stats, Part 2B model metrics & SHAP, end-to-end inference on raw warranty + test files.
- **Part A: Warranty Classification** — clean raw warranty Excel, run LLM classification (Plant / Material / Design), generate plant-attribution Pareto charts.
- **Part B: Warranty Prediction from Test Data** — clean raw test data, then train CVT and PowerTrain LightGBM models against three target types: raw component description, general warranty type, or binary failure.

State persists between runs under `artifacts/` (cleaned data, models, charts, metadata).

## Install

```bash
# from project root
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS / Linux

pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Streamlit opens at <http://localhost:8501>. Navigate via the sidebar.

## Workflow

1. **Part A → Clean warranty data** — upload raw warranty Excel (e.g. *UPDATED Full Claims Report.xlsx*).
2. **Part A → LLM classify** *(optional)* — pick a provider, paste an API key, and classify dealer comments. Currently wired for Ollama; OpenAI / Anthropic providers are stubbed in [backend/llm_classify.py](backend/llm_classify.py) for you to fill in.
3. **Part A → Pareto** — upload the Racine parts file and a claims file to generate plant-attribution Pareto charts.
4. **Part B → Clean test data** — upload raw test data CSV / XLSX (e.g. *4Q24-1Q26.csv*).
5. **Part B → Train model** — choose the target type, upload `Unique Component Descriptions.csv`, and train CVT + PowerTrain models. Cleaned warranty + cleaned test data flow in automatically.
6. **Dashboard → Run prediction** — upload raw warranty + raw test files; the app cleans them, splits CVT vs PowerTrain, and runs the trained models end-to-end.

## Project layout

```
app.py                                # Dashboard entry point
pages/
  1_Part_A_Warranty_Classification.py
  2_Part_B_Warranty_Prediction.py
backend/
  state.py            # paths + disk persistence helpers
  clean_warranty.py   # 1A cleaning logic (from clean_warranty.ipynb)
  clean_test.py       # 1B cleaning logic (from clean_test_zscore.ipynb)
  llm_classify.py     # LLM provider abstraction (Ollama wired, OpenAI/Anthropic stubbed)
  pareto.py           # 2A plant-attribution Pareto pipeline
  prediction.py       # 2B CVT + PowerTrain model training & inference
artifacts/                            # auto-created at runtime
backend_1a.py                         # legacy LLM helpers (still used by llm_classify.py)
1b_Zscore_calculation/                # original notebooks + raw data
2a_plant_warranty/                    # original 2A scripts + records
2b_test_to_warranty_prediction/       # original 2B notebook + records
img/                                  # CNH and Purdue logos
.streamlit/config.toml                # theme + upload size
```
