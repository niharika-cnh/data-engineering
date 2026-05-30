# Mike run guide — CNH Warranty & Test Analytics

## Hosted Streamlit vs local laptop

| Capability | Hosted Streamlit (Cloud) | Local laptop (`streamlit run app.py`) |
|------------|--------------------------|----------------------------------------|
| UI review, navigation, workflow | Yes | Yes |
| **1A** Warranty preparation | Yes | Yes |
| **2A** Plant Pareto (with saved/classified inputs as applicable) | Yes | Yes |
| **2B** Test Analytics (Z-score, abnormal-but-accepted) | **Yes — Ollama not required** | Yes |
| **Prediction** page | Yes (if artifacts/models present) | Yes |
| View/download **existing** 1B classification artifact | Yes (if `artifacts/warranty_classified.parquet` was deployed or uploaded) | Yes |
| **New** 1B claim classification runs | **No** — needs local Ollama or a hosted LLM API | Yes (with Ollama) |

**Summary**

- The **hosted Streamlit link** can be used for UI review, **1A**, **2A/2B**, and **existing outputs** already saved in artifacts.
- **New 1B classification** requires **local Ollama** on your laptop (or another LLM provider when implemented).
- **Ollama is not required for 2B Test Analytics.**

---

## Local setup — Ollama (1B only)

**Current local test model:** `llama3.2:1b` (app default).  
**Optional production model:** `gemma3:27b-8` — still supported; set it in **1B → Model** after `ollama pull gemma3:27b-8`.

1. **Check installation**
   ```powershell
   ollama --version
   ```

2. **Start Ollama** (leave this terminal open)
   ```powershell
   ollama serve
   ```

3. **Pull the default model**
   ```powershell
   ollama pull llama3.2:1b
   ```

4. **Other models** (edit **Model** on 1B to match after pull)
   ```powershell
   ollama pull llama3.2:3b
   ollama pull gemma3:27b-8
   ```

5. **Run the Streamlit app**
   ```powershell
   cd "<project-root>"
   .\.venv\Scripts\activate
   streamlit run app.py
   ```

### Optional environment variables

| Variable | Default |
|----------|---------|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | `llama3.2:1b` |

Legacy alias: `OLLAMA_HOST` (same meaning as `OLLAMA_BASE_URL`).

---

## Workflow checklist

1. **1A** — Upload and clean warranty data.
2. **1B** — Confirm **Ollama status** shows available → **Run classification** → download `warranty_classified_plant_material_design.csv`.
3. **2A** — Pareto on plant-classified claims (uses 1B output).
4. **2B** — Upload test data, threshold **1.0**, **Process test data** → download abnormal-but-accepted CSVs.
5. **Prediction** — Optional ML step when artifacts are ready.

---

## Streamlit Cloud behavior

- The app **loads all pages** even when Ollama is not running.
- On **1B**, **Run classification** is disabled when Ollama is unreachable; a warning explains that only **new** runs need Ollama.
- Previously saved `artifacts/warranty_classified.parquet` can still be **viewed and downloaded** on Cloud if that file is present in the deployment environment.
- **Mike can use 2B from the hosted link** without Ollama (upload test file, process, download Mike CSVs). Z-score and abnormal-but-accepted logic run entirely in Python/pandas.

---

## Regenerating outputs after code changes

See **CHANGELOG_CNH_UPDATES.md** → *Mike Request Verification and Output Regeneration* and *Ollama Local Setup and Classification Guardrails*.

To clear all saved runs locally:

```powershell
Remove-Item -Recurse -Force .\artifacts
```
