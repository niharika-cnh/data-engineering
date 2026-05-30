from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

GENERIC_KEYWORDS = {"O-RING", "ORING", "BOLT", "SCREW", "WASHER", "NUT", "PIN", "SEAL", "GASKET", "TIE", "CIRCLIP", "RING"}
CONTEXTUAL_KEYWORDS = {"CAB", "FRAME", "PTO", "HYDRAULIC", "ENGINE", "ROOF", "AXLE", "PUMP", "DOOR", "GLASS", "WHEEL", "SEAT", "STEERING", "TRANSMISSION", "HOSE", "VALVE", "FILTER", "CYLINDER"}


def _classify_description(desc: str) -> str:
    if pd.isna(desc):
        return "NON_GENERIC"
    cleaned = re.sub(r"[^A-Z0-9\s]", " ", str(desc).upper())
    tokens = set(cleaned.split())
    has_generic = bool(tokens & GENERIC_KEYWORDS)
    has_context = bool(tokens & CONTEXTUAL_KEYWORDS)
    if has_generic and has_context:
        return "CONTEXTUAL_GENERIC"
    if has_generic:
        return "PURE_GENERIC"
    return "NON_GENERIC"


def _load_parts(parts_file) -> pd.DataFrame:
    df = pd.read_excel(parts_file)
    df = df.rename(
        columns={
            "ActivityConsumption|ItemID": "Part_Number",
            "ItemID Description": "Part_Description",
            "WorkStation|ID": "Assembly_Station_ID",
            "WorkStation|Description": "Assembly_Station_Desc",
            "ActivityLocal|OperatorID": "Operator_ID",
        }
    )
    df["Part_Number"] = df["Part_Number"].astype(str).str.strip().str.upper()
    df = df.dropna(subset=["Part_Number"]).drop_duplicates(subset=["Part_Number"], keep="first")
    return df


def _load_claims(claims_file, sheet_name: str = "Paid", header_row: int = 1) -> pd.DataFrame:
    df = pd.read_excel(claims_file, sheet_name=sheet_name, header=header_row)
    rename_map = {
        "Causal Part Code": "Part_Number",
        "Causal Part Descriprion": "Part_Description_Claims",
        "Causal Part Description": "Part_Description_Claims",
        "Total Amount with Standard Net Local Currency": "Warranty_Cost",
        "Production Plant Code": "Plant_Code",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    if "Warranty_Cost" in df.columns:
        df["Warranty_Cost"] = df["Warranty_Cost"].fillna(0)
    df["Part_Number"] = df["Part_Number"].astype(str).str.strip().str.upper()
    if "Part_Description_Claims" in df.columns:
        df["Part_Description_Claims"] = df["Part_Description_Claims"].astype(str).str.strip().str.upper()
    return df


def run_pareto(
    claims_file,
    parts_file,
    out_dir: Path,
    top_n: int = 15,
) -> dict:
    """
    Generate the Part 2A pareto pipeline.

    Parameters
    ----------
    claims_file : path-like or file-like
        Raw warranty claims Excel file.
    parts_file : path-like or file-like
        Racine parts data Excel file.
    out_dir : Path
        Directory to write chart PNGs and aggregated parquet.
    top_n : int
        Number of top assembly stations to display.

    Returns
    -------
    dict with summary statistics and paths to generated artifacts.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df_parts = _load_parts(parts_file)
    df_claims = _load_claims(claims_file)

    df_claims["generic_classification"] = df_claims["Part_Description_Claims"].apply(_classify_description)
    df_claims = df_claims[df_claims["generic_classification"] != "PURE_GENERIC"].copy()

    df_merged = df_claims.merge(
        df_parts[["Part_Number", "Assembly_Station_ID", "Assembly_Station_Desc", "Operator_ID"]],
        on="Part_Number",
        how="left",
    )

    mapped = df_merged[df_merged["Assembly_Station_ID"].notna()].copy()
    unmapped = df_merged[df_merged["Assembly_Station_ID"].isna()]

    if "Plant_Code" in mapped.columns:
        mapped = mapped[mapped["Plant_Code"].notna()].copy()
    mapped["Assembly_Station_Desc"] = mapped["Assembly_Station_Desc"].fillna(mapped["Assembly_Station_ID"])

    claim_count_col = "Claim Number" if "Claim Number" in mapped.columns else mapped.columns[0]
    agg = (
        mapped.groupby(["Assembly_Station_ID", "Assembly_Station_Desc"])
        .agg(
            Claim_Occurrences=(claim_count_col, "count"),
            Total_Warranty_Cost=("Warranty_Cost", "sum"),
        )
        .reset_index()
    )
    agg = agg.sort_values("Total_Warranty_Cost", ascending=False).reset_index(drop=True)
    total_cost = agg["Total_Warranty_Cost"].sum()
    if total_cost > 0:
        agg["Percentage_Contribution"] = agg["Total_Warranty_Cost"] / total_cost * 100
        agg["Cumulative_Percentage"] = agg["Percentage_Contribution"].cumsum()
    else:
        agg["Percentage_Contribution"] = 0.0
        agg["Cumulative_Percentage"] = 0.0

    cost_chart = out_dir / "pareto_costs.png"
    occ_chart = out_dir / "pareto_occurrences.png"
    agg_path = out_dir / "aggregated.parquet"

    _render_pareto(
        df=agg.head(top_n),
        x_col="Assembly_Station_ID",
        y_col="Total_Warranty_Cost",
        cum_col="Cumulative_Percentage",
        title=f"Pareto: Warranty Cost by Assembly Station (Top {top_n})",
        y_label="Total Warranty Cost ($)",
        bar_color="#FFE9A8",
        value_fmt="${:,.0f}",
        out_path=cost_chart,
    )

    agg_occ = agg.sort_values("Claim_Occurrences", ascending=False).reset_index(drop=True)
    total_occ = agg_occ["Claim_Occurrences"].sum()
    agg_occ["Cumulative_Percentage_Occ"] = (
        agg_occ["Claim_Occurrences"] / total_occ * 100
    ).cumsum() if total_occ > 0 else 0

    _render_pareto(
        df=agg_occ.head(top_n),
        x_col="Assembly_Station_ID",
        y_col="Claim_Occurrences",
        cum_col="Cumulative_Percentage_Occ",
        title=f"Pareto: Claim Occurrences by Assembly Station (Top {top_n})",
        y_label="Number of Claims",
        bar_color="#A8D8FF",
        value_fmt="{:,.0f}",
        out_path=occ_chart,
    )

    agg.to_parquet(agg_path, index=False)

    return {
        "total_claims": int(len(df_claims)),
        "mapped_claims": int(len(mapped)),
        "unmapped_claims": int(len(unmapped)),
        "mapping_rate": float(len(mapped) / len(df_claims)) if len(df_claims) else 0.0,
        "total_warranty_cost": float(total_cost),
        "top_station_id": str(agg["Assembly_Station_ID"].iloc[0]) if len(agg) else "",
        "top_station_cost": float(agg["Total_Warranty_Cost"].iloc[0]) if len(agg) else 0.0,
        "top_n_stations": agg.head(top_n)[["Assembly_Station_ID", "Assembly_Station_Desc", "Total_Warranty_Cost", "Claim_Occurrences"]].to_dict(orient="records"),
        "cost_chart": str(cost_chart),
        "occurrences_chart": str(occ_chart),
        "aggregated_parquet": str(agg_path),
    }


def _render_pareto(df, x_col, y_col, cum_col, title, y_label, bar_color, value_fmt, out_path: Path):
    fig, ax1 = plt.subplots(figsize=(12, 6), facecolor="white")

    sns.barplot(x=x_col, y=y_col, data=df, color=bar_color, ax=ax1, edgecolor="black")
    ax1.set_xlabel("Assembly Station")
    ax1.set_ylabel(y_label)
    ax1.tick_params(axis="x", rotation=45)
    for label in ax1.get_xticklabels():
        label.set_horizontalalignment("right")

    if df[y_col].max() > 0:
        ax1.set_ylim(0, df[y_col].max() * 1.25)

    ax2 = ax1.twinx()
    ax2.plot(df[x_col], df[cum_col], color="#222222", marker="o", ms=5)
    ax2.set_ylabel("Cumulative Percentage (%)")
    ax2.set_ylim(0, 105)

    for p in ax1.patches:
        height = p.get_height()
        if height > 0:
            ax1.text(
                p.get_x() + p.get_width() / 2,
                height + (df[y_col].max() * 0.02),
                value_fmt.format(height),
                ha="center",
                va="bottom",
                fontsize=9,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=0.5),
            )

    ax1.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
