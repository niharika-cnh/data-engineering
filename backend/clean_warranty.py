from __future__ import annotations

import pandas as pd

# Each entry: (canonical_name, [raw variants to accept from the spreadsheet]).
# We rename any matching variant to the canonical name on load, so downstream
# code only ever has to reference the canonical name even if the source file
# has backslash characters, typos, or whitespace quirks.
COLUMN_ALIASES: list[tuple[str, list[str]]] = [
    ("Component Description", ["Component Description"]),
    ("Failure Index Description", ["Failure Index Description"]),
    ("Causal Part Code", ["Causal Part Code"]),
    ("Causal Part Description", ["Causal Part Description", "Causal Part Descriprion"]),
    ("Dealer Comments", ["Dealer Comments"]),
    ("Warranty Type Code", ["Warranty Type Code"]),
    ("Warranty Class Code", ["Warranty Class Code"]),
    ("Serial Number", ["Serial Number"]),
    (
        "Techtype or VCB Code",
        ["Techtype or VCB Code", "Techtype \\ VCB Code", "Techtype\\VCB Code", "Techtype \\VCB Code"],
    ),
    ("Techtype Description", ["Techtype Description"]),
    ("Production Date", ["Production Date"]),
    ("Base Warranty Start Date", ["Base Warranty Start Date"]),
    ("Failure Date", ["Failure Date"]),
    ("Repair Date", ["Repair Date"]),
    (
        "Worked Hours or Mileage km",
        [
            "Worked Hours or Mileage km",
            "Worked Hours\\ Mileage km",
            "Worked Hours \\ Mileage km",
            "Worked Hours\\Mileage km",
        ],
    ),
    ("Total Amount with Standard Net Local Currency", ["Total Amount with Standard Net Local Currency"]),
    ("Claim Type Code", ["Claim Type Code"]),
    ("Claim Status Code", ["Claim Status Code"]),
    ("Transmission Number", ["Transmission Number"]),
]

KEEP_COLUMNS = [canonical for canonical, _ in COLUMN_ALIASES]


def _resolve_aliases(df: pd.DataFrame) -> pd.DataFrame:
    """Rename any recognized raw-variant column to its canonical name."""
    existing = set(df.columns)
    rename_map: dict[str, str] = {}
    for canonical, variants in COLUMN_ALIASES:
        if canonical in existing:
            continue
        for variant in variants:
            if variant in existing:
                rename_map[variant] = canonical
                break
    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def _fill_missing_start_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing Base Warranty Start Date with Jan 1 of the representative year
    of the dataset (the most common year among existing values). If no dates
    are available at all, fall back to Jan 1 of the current calendar year.
    """
    if "Base Warranty Start Date" not in df.columns:
        return df

    dates = pd.to_datetime(df["Base Warranty Start Date"], errors="coerce")
    non_null = dates.dropna()
    if len(non_null):
        year = int(non_null.dt.year.mode().iloc[0])
    else:
        year = pd.Timestamp.now().year
    fallback = pd.Timestamp(year=year, month=1, day=1)

    df = df.copy()
    df["Base Warranty Start Date"] = dates.fillna(fallback)
    return df


def clean_warranty(
    file,
    sheet_name: str = "Paid",
    header_row: int = 1,
    only_basic_warranty: bool = True,
    only_dealer_found: bool = False,
    drop_missing_warranty_start: bool = False,
) -> pd.DataFrame:
    """
    Clean a raw warranty claims Excel file.

    Mirrors 1b_Zscore_calculation/clean_warranty.ipynb with two additions:
      - resolves backslash / typo variants in column names to canonical names,
      - fills missing Base Warranty Start Date with Jan 1 of the data's
        representative year (unless ``drop_missing_warranty_start`` is set).

    Parameters
    ----------
    file : path-like or file-like
        Raw warranty Excel file (e.g., "UPDATED Full Claims Report.xlsx").
    sheet_name : str
        Worksheet to read.
    header_row : int
        Row index (0-based) containing the column headers. Default 1 because
        row 0 is a title banner in the source spreadsheet.
    only_basic_warranty : bool
        Keep only rows where Warranty Class Code == "BW".
    only_dealer_found : bool
        Keep only rows where Warranty Type Code == "Z".
    drop_missing_warranty_start : bool
        If True, drop rows missing Base Warranty Start Date entirely.
        If False (default), fill the missing values with Jan 1 of the most
        common year in the dataset.
    """
    df = pd.read_excel(file, sheet_name=sheet_name, header=header_row)
    df = _resolve_aliases(df)

    if only_basic_warranty and "Warranty Class Code" in df.columns:
        df = df[df["Warranty Class Code"] == "BW"]

    if only_dealer_found and "Warranty Type Code" in df.columns:
        df = df[df["Warranty Type Code"] == "Z"]

    available = [c for c in KEEP_COLUMNS if c in df.columns]
    df = df[available].copy()

    if drop_missing_warranty_start:
        if "Base Warranty Start Date" in df.columns:
            df = df.dropna(subset=["Base Warranty Start Date"])
    else:
        df = _fill_missing_start_dates(df)

    # Plant/Material/Design is written in 1B as `category` (and mirrored to `Classification`).
    df = df.reset_index(drop=True)
    return df
