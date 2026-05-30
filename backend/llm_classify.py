from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backend.ollama_client import ollama_base_url, ollama_model_default

from backend_1a import ALLOWED_LABELS, extract_label

CLASSIFICATION_COLUMNS = ("category", "confidence", "classify_source", "classify_debug")

DEFAULT_PROMPT_TEMPLATE = """
You are classifying warranty root cause into exactly one label.

Labels:
Plant
Material
Design

Definitions:
Plant: Manufacturing or assembly process issue (incorrect installation, loose parts, missing parts, improper routing, poor factory application).
Material: Defective, damaged, or failed component (cracked, broken, leaking, torn, faulty material).
Design: Engineering or design issue (software mismatch, design flaw causing repeated failure, system-level weakness).

Decision Rules:
1. If a part is leaking, cracked, torn, burst, or failed -> Material.
2. If the issue is incorrect assembly, loose/missing parts, or factory process -> Plant.
3. If both appear, pick the ROOT CAUSE: bad part -> Material, bad assembly -> Plant.
4. If neither clearly applies -> Design.
5. Output EXACTLY one word: Plant or Material or Design.
6. Do NOT explain.

Warranty text:
{text}

Answer:
""".strip()


@dataclass
class ClassifyResult:
    row_number: int
    dealer_comment: str
    category: str
    confidence: float
    source: str
    debug_message: str


def _classify_via_provider(
    text: str,
    provider: str,
    api_key: str,
    model_name: str,
    prompt_template: str,
    ollama_base_url_override: str | None = None,
):
    """
    Plug-in point for LLM providers. Returns (label, confidence, source, debug).

    Currently routes to the existing Ollama backend (backend_1a.classify_with_ollama)
    when provider=='ollama'. For openai/anthropic, returns a TODO so the team can
    drop in their preferred SDK call.
    """
    if provider == "ollama":
        from backend_1a import classify_with_ollama  # reuse existing implementation

        return classify_with_ollama(
            text=text,
            prompt_template=prompt_template,
            model_name=model_name or ollama_model_default(),
            ollama_host=ollama_base_url_override or ollama_base_url(),
        )

    if provider in ("openai", "anthropic"):
        if not api_key:
            return "ERROR", 0.0, "error", f"{provider}: API key not provided"
        # TODO: drop in actual SDK call here. Kept as a stub by request.
        return "TODO", 0.0, "stub", f"{provider} integration not yet implemented"

    return "ERROR", 0.0, "error", f"unknown provider: {provider}"


def normalize_category_label(label: str, raw_output: str = "") -> str:
    """
    Coerce classifier output to Plant / Material / Design / SKIP when possible.
    ERROR/TIMEOUT are returned unchanged for UI diagnostics.
    """
    label = (label or "").strip()
    if label in ALLOWED_LABELS or label == "SKIP":
        return label
    if label in {"ERROR", "TIMEOUT", "TODO"}:
        return label
    if label == "INVALID":
        parsed = extract_label(raw_output)
        return parsed if parsed in ALLOWED_LABELS else "Design"
    parsed = extract_label(label)
    if parsed in ALLOWED_LABELS:
        return parsed
    return label


def classify_dataframe(
    df: pd.DataFrame,
    text_column: str = "Dealer Comments",
    provider: str = "ollama",
    api_key: str = "",
    model_name: str = "",
    prompt_template: str | None = None,
    progress_cb=None,
    ollama_base_url_override: str | None = None,
) -> pd.DataFrame:
    """
    Run LLM classification across the dealer-comment column of a cleaned warranty df.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned warranty data (output of clean_warranty.clean_warranty).
    text_column : str
        Column holding the dealer comment to classify.
    provider : str
        One of "ollama", "openai", "anthropic".
    api_key : str
        API key for cloud providers (ignored for ollama).
    model_name : str
        Model identifier (provider-specific).
    prompt_template : str | None
        Override the default classification prompt. Use "{text}" placeholder.
    progress_cb : callable | None
        Optional callback receiving (current_index, total) for progress updates.
    """
    if text_column not in df.columns:
        raise ValueError(f"Column '{text_column}' not found in dataframe.")

    template = prompt_template if prompt_template else DEFAULT_PROMPT_TEMPLATE

    # Keep all cleaned warranty columns; append classification fields (Mike review export).
    out = df.reset_index(drop=True).copy()
    out["category"] = pd.Series([pd.NA] * len(out), dtype="object")
    out["confidence"] = pd.NA
    out["classify_source"] = pd.Series([pd.NA] * len(out), dtype="object")
    out["classify_debug"] = pd.Series([pd.NA] * len(out), dtype="object")

    total = len(out)
    texts = out[text_column].astype(str)
    for i in range(total):
        cleaned = texts.iloc[i].strip()
        if not cleaned or cleaned.lower() == "nan":
            out.at[i, "category"] = "SKIP"
            out.at[i, "confidence"] = 0.0
            out.at[i, "classify_source"] = "skip"
            out.at[i, "classify_debug"] = "empty comment"
            if progress_cb is not None:
                progress_cb(i + 1, total)
            continue

        label, confidence, source, debug = _classify_via_provider(
            text=cleaned,
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            prompt_template=template,
            ollama_base_url_override=ollama_base_url_override,
        )

        raw = debug.split("raw_output=", 1)[-1] if "raw_output=" in (debug or "") else ""
        label = normalize_category_label(label, raw_output=raw)

        out.at[i, "category"] = label
        out.at[i, "confidence"] = float(confidence)
        out.at[i, "classify_source"] = source
        out.at[i, "classify_debug"] = debug

        if progress_cb is not None:
            progress_cb(i + 1, total)

    # 1A adds an empty "Classification" placeholder; fill it from the real result column.
    if "category" in out.columns:
        out["Classification"] = out["category"]

    return out
