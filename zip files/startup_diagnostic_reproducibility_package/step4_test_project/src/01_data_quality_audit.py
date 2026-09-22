"""Step 2: simple, read-only data-quality audit for the startup CSV files."""

from pathlib import Path
import pandas as pd


# Use the standard project folders.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_FOLDER = PROJECT_ROOT / "data" / "raw"
REPORT_FILE = PROJECT_ROOT / "outputs" / "quality" / "raw_data_quality_report.csv"
REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

# These columns should contain only 0 or 1 when they are present.
FAILURE_FLAGS = [
    "Giants", "No Budget", "Competition", "Poor Market Fit",
    "Acquisition Stagnation", "Platform Dependency",
    "High Operational Costs", "Monetization Failure", "Niche Limits",
    "Execution Flaws", "Trend Shifts", "Toxicity/Trust Issues",
    "Regulatory Pressure", "Overhype",
]

# Ignore the report itself if the script is run more than once.
csv_files = [
    file for file in DATA_FOLDER.glob("*.csv")
    if file.name != REPORT_FILE.name
]

if not csv_files:
    raise FileNotFoundError("No CSV files were found beside this script.")

report_rows = []

for file in sorted(csv_files):
    df = pd.read_csv(file, low_memory=False)

    print(f"\nFile: {file.name}")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print(f"Duplicate rows: {df.duplicated().sum():,}")

    # Check missing values and save one report row per column.
    missing = df.isna().sum()
    for column in df.columns:
        report_rows.append(
            {
                "file": file.name,
                "column": column,
                "data_type": str(df[column].dtype),
                "missing_count": int(missing[column]),
                "missing_percent": round(missing[column] / len(df) * 100, 2),
                "unique_values": int(df[column].nunique(dropna=True)),
            }
        )

    print("Columns with missing values:")
    print(missing[missing > 0] if (missing > 0).any() else "None")

    # Check repeated startup or company identifiers.
    for id_column in ["startup_id", "Name", "name"]:
        if id_column in df.columns:
            duplicate_ids = df[id_column].astype("string").str.lower().duplicated().sum()
            print(f"Duplicate {id_column} values: {duplicate_ids:,}")
            break

    # Check that failure flags contain only 0 and 1.
    for flag in FAILURE_FLAGS:
        if flag in df.columns:
            invalid_count = (~df[flag].dropna().isin([0, 1])).sum()
            if invalid_count > 0:
                print(f"Invalid values in {flag}: {invalid_count:,}")

    # Extra checks for the large startup-status dataset.
    if file.name == "big_startup_secsees_dataset.csv":
        valid_statuses = ["operating", "closed", "acquired", "ipo"]
        invalid_statuses = (~df["status"].dropna().isin(valid_statuses)).sum()
        print(f"Unexpected status values: {invalid_statuses:,}")

        funding = pd.to_numeric(
            df["funding_total_usd"].replace("-", pd.NA), errors="coerce"
        )
        print(f"Missing or non-numeric funding totals: {funding.isna().sum():,}")
        print(f"Negative funding totals: {(funding < 0).sum():,}")

        first_funding = pd.to_datetime(df["first_funding_at"], errors="coerce")
        last_funding = pd.to_datetime(df["last_funding_at"], errors="coerce")
        wrong_order = (last_funding < first_funding).sum()
        print(f"Last-funding dates before first-funding dates: {wrong_order:,}")

    # Extra checks for the synthetic operating-metrics dataset.
    if file.name == "synthetic_startup_metrics.csv":
        numeric_columns = [
            "mrr_usd", "cac_usd", "ltv_usd", "monthly_burn_usd",
            "cash_in_bank_usd", "runway_months",
        ]
        for column in numeric_columns:
            print(f"Negative values in {column}: {(df[column] < 0).sum():,}")

        calculated_ratio = df["ltv_usd"] / df["cac_usd"]
        ratio_errors = ((calculated_ratio - df["ltv_cac_ratio"]).abs() > 0.02).sum()
        print(f"LTV/CAC calculation mismatches: {ratio_errors:,}")

        calculated_runway = df["cash_in_bank_usd"] / df["monthly_burn_usd"]
        runway_errors = ((calculated_runway - df["runway_months"]).abs() > 0.1).sum()
        print(f"Runway calculation mismatches: {runway_errors:,}")

# Save the column-level audit report. The original CSV files are unchanged.
pd.DataFrame(report_rows).to_csv(REPORT_FILE, index=False)

print(f"\nAudit finished. Report saved as: {REPORT_FILE.name}")
