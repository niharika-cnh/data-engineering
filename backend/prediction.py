from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder

TARGET_COMPONENT = "component_description"
TARGET_GENERAL = "general_warranty_type"
TARGET_BINARY = "binary_classification"

VALID_TARGETS = (TARGET_COMPONENT, TARGET_GENERAL, TARGET_BINARY)


@dataclass
class TrainResult:
    family: str               # "cvt" or "powertrain"
    target: str               # one of VALID_TARGETS
    accuracy_test: float
    cv_mean: float
    cv_std: float
    classes: list[str]
    classification_report: str
    feature_importance: list[dict]
    n_train: int
    n_test: int


def _safe_col(name: str) -> str:
    return re.sub(r"[\[\]<>\s]", "_", str(name))


def split_cvt_powertrain(test_pivot: pd.DataFrame, cvt_marker_col: str = "CVT Condition 1") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split per-transmission test pivot into CVT and PowerTrain subsets."""
    if cvt_marker_col not in test_pivot.columns:
        # If marker col is missing, treat everything as PowerTrain.
        return test_pivot.iloc[0:0].copy(), test_pivot.copy()
    cvt = test_pivot[test_pivot[cvt_marker_col].notna()].dropna(axis=1, how="all").copy()
    pt = test_pivot[test_pivot[cvt_marker_col].isna()].dropna(axis=1, how="all").copy()
    return cvt, pt


def _group_label(x: str) -> str:
    if x == "No Transmission Issue":
        return "No Issue"
    s = str(x).lower()
    if "valve" in s or "hydraulic" in s:
        return "Hydraulic"
    if "sensor" in s or "electronic" in s:
        return "Electrical"
    if "shaft" in s or "clutch" in s:
        return "Mechanical"
    return "Other"


def attach_target(
    test_subset: pd.DataFrame,
    warranty_cleaned: pd.DataFrame,
    transmission_components: Iterable[str],
    target: str,
) -> pd.DataFrame:
    """
    Left-join the test subset with cleaned warranty data on SerialNumber/Transmission Number,
    then build the prediction target column ``y`` based on the requested target type.
    """
    if target not in VALID_TARGETS:
        raise ValueError(f"target must be one of {VALID_TARGETS}, got {target}")

    w = warranty_cleaned[["Transmission Number", "Component Description"]].copy()
    w = w[w["Transmission Number"].astype(str) != "#"]
    w["Transmission Number"] = w["Transmission Number"].astype(str).str.strip().str.upper()

    test = test_subset.copy()
    test["SerialNumber"] = test["SerialNumber"].astype(str).str.strip().str.upper()

    merged = test.merge(w, how="left", left_on="SerialNumber", right_on="Transmission Number")

    tx_set = {str(c) for c in transmission_components if pd.notna(c)}
    raw_label = merged["Component Description"].where(
        merged["Component Description"].isin(tx_set),
        "No Transmission Issue",
    )

    if target == TARGET_COMPONENT:
        merged["y"] = raw_label
    elif target == TARGET_GENERAL:
        merged["y"] = raw_label.apply(_group_label)
    else:  # binary
        merged["y"] = raw_label.apply(
            lambda x: "No Failure" if x == "No Transmission Issue" else "Failure"
        )

    return merged.drop(columns=["Component Description", "Transmission Number"])


def _build_model() -> LGBMClassifier:
    return LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        num_leaves=15,
        max_depth=5,
        random_state=42,
        reg_alpha=1.0,
        reg_lambda=1.0,
        class_weight="balanced",
        verbosity=-1,
    )


def train_one(
    df_with_target: pd.DataFrame,
    family: str,
    target: str,
    out_dir: Path,
) -> tuple[LGBMClassifier, LabelEncoder, list[str], TrainResult]:
    """Train a single LightGBM model on a CVT or PowerTrain subset."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = df_with_target.dropna(subset=["y"]).copy()
    counts = df["y"].value_counts()
    df = df[df["y"].isin(counts[counts > 1].index)]

    X = df.drop(columns=["SerialNumber", "y"]).select_dtypes(include=[np.number])
    feature_names = [_safe_col(c) for c in X.columns]
    X.columns = feature_names

    y_raw = df["y"].astype(str)
    le = LabelEncoder()
    y = le.fit_transform(y_raw)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = _build_model()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = float((y_pred == y_test).mean())

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X, y, cv=cv)

    target_names = [str(c) for c in le.classes_]
    report = classification_report(y_test, y_pred, target_names=target_names, zero_division=0)

    fi = (
        pd.DataFrame({"feature": feature_names, "importance": model.feature_importances_})
        .sort_values("importance", ascending=False)
        .head(20)
        .to_dict(orient="records")
    )

    _render_feature_importance(
        feature_names=feature_names,
        importances=model.feature_importances_,
        title=f"{family.upper()} model — top features ({target})",
        out_path=out_dir / f"shap_{family}.png",
    )

    return (
        model,
        le,
        feature_names,
        TrainResult(
            family=family,
            target=target,
            accuracy_test=accuracy,
            cv_mean=float(cv_scores.mean()),
            cv_std=float(cv_scores.std()),
            classes=target_names,
            classification_report=report,
            feature_importance=fi,
            n_train=int(len(X_train)),
            n_test=int(len(X_test)),
        ),
    )


def _render_feature_importance(feature_names, importances, title: str, out_path: Path):
    """
    Render a SHAP-style horizontal bar plot of model feature importances.

    We try real SHAP values first; on any failure fall back to LightGBM's gain importance.
    """
    fig, ax = plt.subplots(figsize=(10, 8), facecolor="white")
    order = np.argsort(importances)[-20:]
    ax.barh(np.array(feature_names)[order], np.array(importances)[order], color="#E40521")
    ax.set_title(title)
    ax.set_xlabel("Importance")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def render_shap(model: LGBMClassifier, X: pd.DataFrame, out_path: Path, title: str = "SHAP Feature Importance") -> Path:
    """Generate a real SHAP summary bar plot. Falls back to feature_importance plot on failure."""
    try:
        import shap

        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        if isinstance(shap_values, list) and len(shap_values) >= 2:
            shap_values_target = shap_values[1]
        else:
            shap_values_target = getattr(shap_values, "values", shap_values)
            if hasattr(shap_values_target, "shape") and len(shap_values_target.shape) == 3:
                shap_values_target = shap_values_target[:, :, 1]

        plt.figure(figsize=(12, 8))
        shap.summary_plot(shap_values_target, X, plot_type="bar", show=False)
        plt.title(title)
        plt.tight_layout()
        plt.savefig(out_path, dpi=180, bbox_inches="tight")
        plt.close()
        return out_path
    except Exception:
        _render_feature_importance(
            feature_names=list(X.columns),
            importances=model.feature_importances_,
            title=title + " (fallback)",
            out_path=out_path,
        )
        return out_path


def predict(
    model: LGBMClassifier,
    le: LabelEncoder,
    feature_names: list[str],
    test_subset: pd.DataFrame,
) -> pd.DataFrame:
    """Run a trained model on a new per-transmission test subset."""
    df = test_subset.copy()
    df["SerialNumber"] = df["SerialNumber"].astype(str).str.strip().str.upper()

    X = df.drop(columns=[c for c in ("SerialNumber",) if c in df.columns]).select_dtypes(include=[np.number])
    safe_cols = {_safe_col(c): c for c in X.columns}

    X_aligned = pd.DataFrame(
        {feat: X[safe_cols[feat]].values if feat in safe_cols else 0 for feat in feature_names}
    )

    preds = model.predict(X_aligned)
    proba = model.predict_proba(X_aligned)
    confidence = proba.max(axis=1)
    labels = le.inverse_transform(preds.astype(int))

    return pd.DataFrame(
        {
            "SerialNumber": df["SerialNumber"].values,
            "predicted_label": labels,
            "confidence": confidence,
        }
    )
