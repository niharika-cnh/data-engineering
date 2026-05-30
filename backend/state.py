from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = PROJECT_ROOT / "artifacts"
IMG_DIR = PROJECT_ROOT / "img"

WARRANTY_CLEAN = ARTIFACTS / "warranty_cleaned.parquet"
WARRANTY_CLASSIFIED = ARTIFACTS / "warranty_classified.parquet"
TEST_CLEAN_LONG = ARTIFACTS / "test_data_long.parquet"
TEST_CLEAN_PIVOT = ARTIFACTS / "test_data_per_transmission.parquet"

PARETO_DIR = ARTIFACTS / "pareto"
PARETO_CHART_COST = PARETO_DIR / "pareto_costs.png"
PARETO_CHART_OCC = PARETO_DIR / "pareto_occurrences.png"
PARETO_AGG = PARETO_DIR / "aggregated.parquet"
PARETO_STATS = PARETO_DIR / "stats.json"

MODEL_DIR = ARTIFACTS / "models"
MODEL_METADATA = MODEL_DIR / "metadata.json"


def ensure_dirs() -> None:
    for d in (ARTIFACTS, PARETO_DIR, MODEL_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _mtime(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    to_save = df.copy()
    for col in ("category", "classify_source", "classify_debug", "classification_debug"):
        if col in to_save.columns:
            to_save[col] = to_save[col].astype("string")
    if "confidence" in to_save.columns:
        to_save["confidence"] = pd.to_numeric(to_save["confidence"], errors="coerce")
    to_save.to_parquet(path, index=False)


def load_dataframe(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_parquet(path)


def save_json(data: dict, path: Path) -> None:
    ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def save_model(model: Any, name: str) -> Path:
    ensure_dirs()
    path = MODEL_DIR / f"{name}.joblib"
    joblib.dump(model, path)
    return path


def load_model(name: str) -> Any | None:
    path = MODEL_DIR / f"{name}.joblib"
    if not path.exists():
        return None
    return joblib.load(path)


@dataclass
class ArtifactStatus:
    name: str
    available: bool
    updated: str | None
    detail: str = ""


def dashboard_status() -> list[ArtifactStatus]:
    items: list[ArtifactStatus] = []

    df = load_dataframe(WARRANTY_CLEAN)
    items.append(
        ArtifactStatus(
            "Warranty claims cleaned",
            df is not None,
            _mtime(WARRANTY_CLEAN),
            f"{len(df):,} rows" if df is not None else "Open 1A",
        )
    )

    df = load_dataframe(WARRANTY_CLASSIFIED)
    items.append(
        ArtifactStatus(
            "Claims classified (2M/1D)",
            df is not None,
            _mtime(WARRANTY_CLASSIFIED),
            f"{len(df):,} rows" if df is not None else "Open 1B",
        )
    )

    df = load_dataframe(TEST_CLEAN_PIVOT)
    items.append(
        ArtifactStatus(
            "Test data processed",
            df is not None,
            _mtime(TEST_CLEAN_PIVOT),
            f"{len(df):,} units" if df is not None else "Open 2B",
        )
    )

    items.append(
        ArtifactStatus(
            "Pareto analysis",
            PARETO_CHART_COST.exists(),
            _mtime(PARETO_CHART_COST),
            "Open 2A" if not PARETO_CHART_COST.exists() else "Charts saved",
        )
    )

    meta = load_json(MODEL_METADATA)
    items.append(
        ArtifactStatus(
            "Prediction models",
            meta is not None,
            _mtime(MODEL_METADATA),
            f"Target: {meta['target']}" if meta else "Optional ML module",
        )
    )

    return items
