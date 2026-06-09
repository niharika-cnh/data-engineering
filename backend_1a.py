from __future__ import annotations
import pandas as pd
import os
import re
import requests

from backend.ollama_client import ollama_base_url, ollama_model_default

OLLAMA_HOST = ollama_base_url()
OLLAMA_BASE_URL = OLLAMA_HOST
MODEL_NAME = ollama_model_default()

ALLOWED_LABELS = {"Plant", "Material", "Design"}

PLANT_KEYWORDS = [
    "improper assembly",
    "from factory",
    "not installed correctly",
    "not installed",
    "poor application",
    "no paint applied",
    "incorrectly routed",
    "not tightened properly",
    "not tightened",
    "overtightened",
    # Added based on Mike's warranty claim review.
    "poor paint",
    "oil level",
    "clamp loose",
    "fluid leak",
    "rubbing",
    "not connected",
    "bad hose clamp",
    "kinked",
    "damaged",
    "low oil",
]

MATERIAL_KEYWORDS = [
    "cracked",
    "faulty",
    "seal failed",
    "gasket failed",
    "drilled",
    "weld",
    "molded",
    "crimp",
    "machining",
    "idler",
    "o-ring failed",
    "o ring failed",
    "o-ring torn",
    "o ring torn",
]

DEFAULT_PROMPT_TEMPLATE = """
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
""".strip()


def extract_label(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return "INVALID"
    # Prefer the first line / token (models often add extra text).
    first_line = s.splitlines()[0].strip()
    for chunk in (first_line, s):
        m = re.search(r"\b(Plant|Material|Design)\b", chunk, flags=re.IGNORECASE)
        if m:
            return m.group(1).capitalize()
    return "INVALID"


def count_keyword_hits(text_lower: str, keywords: list[str]) -> int:
    hits = 0
    for kw in keywords:
        kw_l = kw.lower().strip()
        if not kw_l:
            continue
        if " " in kw_l or "-" in kw_l:
            if kw_l in text_lower:
                hits += 1
        else:
            if re.search(rf"\b{re.escape(kw_l)}\b", text_lower):
                hits += 1
    return hits


def build_prompt(text: str, prompt_template: str | None = None) -> str:
    template = prompt_template.strip() if prompt_template else DEFAULT_PROMPT_TEMPLATE
    return template.replace("{text}", text)


def classify_with_ollama(
    text: str,
    prompt_template: str | None = None,
    model_name: str = MODEL_NAME,
    ollama_host: str = OLLAMA_HOST,
) -> tuple[str, float, str, str]:
    text = "" if text is None else str(text)
    cleaned = text.strip()

    if cleaned == "" or cleaned.lower() == "nan":
        return "SKIP", 0.0, "error", "empty text"

    text_lower = cleaned.lower()

    plant_hits = count_keyword_hits(text_lower, PLANT_KEYWORDS)
    material_hits = count_keyword_hits(text_lower, MATERIAL_KEYWORDS)
    hit_count = plant_hits + material_hits

    if hit_count > 0 and plant_hits != material_hits:
        base_score = 0.85
        keyword_bonus = min(0.05 * hit_count, 0.15)
        confidence = min(base_score + keyword_bonus, 1.0)

        if plant_hits > material_hits:
            return "Plant", round(confidence, 3), "rule", f"rule-based: plant_hits={plant_hits}, material_hits={material_hits}"
        return "Material", round(confidence, 3), "rule", f"rule-based: plant_hits={plant_hits}, material_hits={material_hits}"

    prompt = build_prompt(cleaned, prompt_template)

    try:
        response = requests.post(
            f"{ollama_host}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
            },
            timeout=180,
        )

        if response.status_code != 200:
            err_detail = response.text[:300]
            try:
                err_json = response.json()
                err_detail = err_json.get("error", err_detail)
            except Exception:
                pass
            if response.status_code == 404 and "not found" in err_detail.lower():
                return (
                    "ERROR",
                    0.0,
                    "error",
                    f"model '{model_name}' not found — run: ollama pull {model_name}",
                )
            return "ERROR", 0.2, "error", f"http {response.status_code}: {err_detail}"

        data = response.json()
        raw_output = (data.get("response") or "").strip()

        if not raw_output:
            return "ERROR", 0.2, "error", "empty response from ollama"

        label = extract_label(raw_output)

        if label not in ALLOWED_LABELS:
            return "INVALID", 0.25, "llm", f"raw_output={raw_output[:300]}"

        base_score = 0.70
        keyword_bonus = min(0.03 * hit_count, 0.12)

        verbosity_penalty = 0.0
        if raw_output.strip() not in ALLOWED_LABELS:
            verbosity_penalty += 0.10

        matches = re.findall(
            r"\b(Plant|Material|Design)\b",
            raw_output,
            flags=re.IGNORECASE,
        )
        if len(matches) > 1:
            verbosity_penalty += 0.10

        length_words = len(cleaned.split())
        prompt_length_penalty = 0.10 if (length_words < 5 or length_words > 120) else 0.0

        confidence = base_score + keyword_bonus - verbosity_penalty - prompt_length_penalty
        confidence = max(0.0, min(1.0, confidence))

        return label, round(confidence, 3), "llm", f"raw_output={raw_output[:300]}"

    except requests.Timeout:
        return "TIMEOUT", 0.1, "error", f"timeout calling {ollama_host}/api/generate"
    except requests.RequestException as e:
        return "ERROR", 0.1, "error", f"requests exception: {str(e)}"
    except Exception as e:
        return "ERROR", 0.1, "error", f"unexpected exception: {str(e)}"


def run_1a_pipeline(
    df_input: pd.DataFrame,
    text_col_index: int = 1,
    prompt_template: str | None = None,
    model_name: str = MODEL_NAME,
    ollama_host: str = OLLAMA_HOST,
) -> pd.DataFrame:
    if df_input.shape[1] <= text_col_index:
        raise ValueError(
            f"Expected at least {text_col_index + 1} columns. "
            f"Could not find text column at index {text_col_index}."
        )

    texts = df_input.iloc[:, text_col_index].astype(str)
    results = []

    for idx, text in texts.items():
        category, confidence, source, debug_message = classify_with_ollama(
            text=text,
            prompt_template=prompt_template,
            model_name=model_name,
            ollama_host=ollama_host,
        )

        if category == "SKIP":
            continue

        results.append(
            {
                "row_number": idx + 1,
                "dealer_comment": str(text),
                "category": category,
                "confidence": confidence,
                "source": source,
                "debug_message": debug_message,
            }
        )

    return pd.DataFrame(results)

if __name__ == "__main__":
    main()