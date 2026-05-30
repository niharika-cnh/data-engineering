from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _to_num(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.replace({"-": np.nan, "": np.nan, "nan": np.nan})
    s = s.str.replace(",", "", regex=False)
    return pd.to_numeric(s, errors="coerce")


def _read_any(file) -> pd.DataFrame:
    """Read csv or xlsx based on filename / extension."""
    name = getattr(file, "name", str(file)).lower()
    if name.endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)


def compute_zscores(df: pd.DataFrame) -> pd.DataFrame:
    """Empirical z-score per Parameter group."""
    df = df.copy()
    df["z_score"] = 0.0

    for parameter, group in df.groupby("Parameter", sort=False):
        values = _to_num(group["Value"]).astype("float")
        mean = values.mean()
        std = values.std()
        if std and not np.isnan(std):
            df.loc[group.index, "z_score"] = (values - mean) / std
        else:
            df.loc[group.index, "z_score"] = 0.0

    return df


def filter_abnormal_accepted(df: pd.DataFrame, z_threshold: float) -> pd.DataFrame:
    """
    Rows with |z_score| above threshold but measured value still within min/max.
    """
    return df[
        (df["z_score"].abs() > z_threshold)
        & (df["Value"] >= df["Minimum"])
        & (df["Value"] <= df["Maximum"])
    ].copy()


def summarize_abnormal_accepted_by_test(df: pd.DataFrame) -> pd.DataFrame:
    """Count abnormal-but-accepted rows per test name, descending."""
    if df.empty or "Test" not in df.columns:
        return pd.DataFrame(columns=["Test", "abnormal_accepted_count"])
    summary = (
        df.groupby("Test", sort=False)
        .size()
        .reset_index(name="abnormal_accepted_count")
        .sort_values("abnormal_accepted_count", ascending=False)
    )
    return summary


def clean_test_data(
    file,
    z_threshold: float = 1.0,
    drop_missing_test_pct: float = 0.9,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Clean raw transmission test data and produce two artifacts:
      - long-format dataframe with z-scores and pass/fail flags
      - per-transmission pivot (rows = SerialNumber, cols = Test, values = pass rate)

    Mirrors 1b_Zscore_calculation/clean_test_zscore.ipynb.

    Parameters
    ----------
    file : path-like or file-like
        Raw test data file (CSV or XLSX).
    z_threshold : float
        Z-score threshold for marking a parameter as failed.
    drop_missing_test_pct : float
        Drop test columns from the pivot that are missing for >X% of transmissions.
    """
    df = _read_any(file)

    if "SerialNumber" in df.columns:
        df["SerialNumber"] = df["SerialNumber"].astype(str).str.upper()

    df = df[df["Maximum"] != df["Minimum"]].copy()

    df["Value"] = _to_num(df["Value"])
    df["Maximum"] = _to_num(df["Maximum"])
    df["Minimum"] = _to_num(df["Minimum"])
    df = df.dropna(subset=["Value"])

    df = compute_zscores(df)

    df["Passed"] = (
        (df["z_score"].abs() < z_threshold)
        & (df["Value"] <= df["Maximum"])
        & (df["Value"] >= df["Minimum"])
    )

    test_pivot = df.pivot_table(
        index="SerialNumber",
        columns="Test",
        values="Passed",
        aggfunc="mean",
    )

    threshold_n = test_pivot.shape[0] * (1 - drop_missing_test_pct)
    test_pivot = test_pivot.dropna(axis=1, thresh=threshold_n)
    test_pivot = test_pivot.reset_index()

    return df, test_pivot
