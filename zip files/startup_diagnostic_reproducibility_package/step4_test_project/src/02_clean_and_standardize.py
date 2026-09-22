"""Step 3: clean and standardize the startup CSV files.

The script creates new CSV files in a cleaned_data folder.
It never overwrites the original files.
"""

from pathlib import Path
import re
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_FOLDER = PROJECT_ROOT / "data" / "raw"
CLEAN_FOLDER = PROJECT_ROOT / "data" / "cleaned"
CLEAN_FOLDER.mkdir(parents=True, exist_ok=True)

# All possible failure flags found in the sector files.
FAILURE_FLAGS = [
    "Giants", "No Budget", "Competition", "Poor Market Fit",
    "Acquisition Stagnation", "Platform Dependency",
    "High Operational Costs", "Monetization Failure", "Niche Limits",
    "Execution Flaws", "Trend Shifts", "Toxicity/Trust Issues",
    "Regulatory Pressure", "Overhype",
]


def normalize_name(value):
    """Create a lowercase name without spaces or punctuation."""
    if pd.isna(value):
        return pd.NA
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def parse_money(value):
    """Convert values such as $2.5M or $1.4B to US dollars."""
    if pd.isna(value):
        return pd.NA

    text = str(value).upper().replace(",", "")
    match = re.search(r"\$?\s*(\d+(?:\.\d+)?)\s*([KMB]?)", text)
    if not match:
        return pd.NA

    number = float(match.group(1))
    multiplier = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    return number * multiplier[match.group(2)]


def extract_years(value):
    """Extract the first and last four-digit years from a text value."""
    years = re.findall(r"\d{4}", str(value))
    if len(years) >= 2:
        return int(years[0]), int(years[-1])
    return pd.NA, pd.NA


summary = []


# ---------------------------------------------------------------------------
# 1. Clean the large startup-status dataset
# ---------------------------------------------------------------------------
big_file = DATA_FOLDER / "big_startup_secsees_dataset.csv"
big = pd.read_csv(big_file, low_memory=False)
rows_before = len(big)

# Remove only exact duplicates and duplicate permalinks.
# Repeated company names are kept because names are not unique identifiers.
big = big.drop_duplicates()
big = big.drop_duplicates(subset="permalink", keep="first")

big["name"] = big["name"].astype("string").str.strip().replace("", pd.NA)
big["name_normalized"] = big["name"].apply(normalize_name)
big["status"] = big["status"].astype("string").str.strip().str.lower()

# Standardize categories and locations. Unknown text values stay explicit.
big["category_list"] = (
    big["category_list"].astype("string").str.strip()
    .str.replace(r"\s*\|\s*", "|", regex=True)
    .replace("", pd.NA).fillna("Unknown")
)
big["primary_category"] = big["category_list"].str.split("|").str[0]

for column in ["country_code", "state_code", "region", "city"]:
    big[column] = (
        big[column].astype("string").str.strip().replace("", pd.NA).fillna("Unknown")
    )
big["country_code"] = big["country_code"].str.upper()

# Convert funding to a number. A dash becomes a missing value, not zero.
big["funding_total_usd_raw"] = big["funding_total_usd"]
big["funding_total_usd"] = pd.to_numeric(
    big["funding_total_usd_raw"].replace("-", pd.NA), errors="coerce"
)
big["funding_total_missing"] = big["funding_total_usd"].isna()
big["funding_rounds"] = pd.to_numeric(big["funding_rounds"], errors="coerce").astype("Int64")

# Convert date text to real dates. Unknown dates remain missing.
for column in ["founded_at", "first_funding_at", "last_funding_at"]:
    big[column] = pd.to_datetime(big[column], errors="coerce")

big_output = CLEAN_FOLDER / "big_startups_clean.csv"
big.to_csv(big_output, index=False, date_format="%Y-%m-%d")
summary.append([big_file.name, rows_before, len(big), rows_before - len(big), big_output.name])


# ---------------------------------------------------------------------------
# 2. Clean the master startup-failure file
# ---------------------------------------------------------------------------
master_file = DATA_FOLDER / "Startup Failures.csv"
master = pd.read_csv(master_file)
rows_before = len(master)
master = master.drop_duplicates()

master["Name"] = master["Name"].astype("string").str.strip()
master["name_normalized"] = master["Name"].apply(normalize_name)
master["Sector"] = master["Sector"].astype("string").str.strip()

year_pairs = master["Years of Operation"].apply(extract_years)
master["start_year"] = [pair[0] for pair in year_pairs]
master["end_year"] = [pair[1] for pair in year_pairs]
master[["start_year", "end_year"]] = master[["start_year", "end_year"]].astype("Int64")
master["duplicate_name"] = master["name_normalized"].duplicated(keep=False)

master_output = CLEAN_FOLDER / "startup_failures_master_clean.csv"
master.to_csv(master_output, index=False)
summary.append([master_file.name, rows_before, len(master), rows_before - len(master), master_output.name])


# ---------------------------------------------------------------------------
# 3. Clean and harmonize the six detailed sector failure files
# ---------------------------------------------------------------------------
failure_files = [
    file for file in DATA_FOLDER.glob("Startup Fail*.csv")
    if file.name != "Startup Failures.csv"
]

for file in sorted(failure_files):
    failure = pd.read_csv(file)
    rows_before = len(failure)
    failure = failure.drop_duplicates()

    failure["Name"] = failure["Name"].astype("string").str.strip()
    failure["name_normalized"] = failure["Name"].apply(normalize_name)
    failure["Sector"] = failure["Sector"].astype("string").str.strip()

    year_pairs = failure["Years of Operation"].apply(extract_years)
    failure["start_year"] = [pair[0] for pair in year_pairs]
    failure["end_year"] = [pair[1] for pair in year_pairs]
    failure[["start_year", "end_year"]] = failure[["start_year", "end_year"]].astype("Int64")

    # Keep the original funding text and add a numeric version.
    failure["funding_raised_usd"] = failure["How Much They Raised"].apply(parse_money)
    failure["funding_needs_review"] = (
        failure["How Much They Raised"].astype("string").str.contains(r"\+|\(|LOW", case=False, na=True)
        | failure["funding_raised_usd"].isna()
    )

    # Every file receives the same flag columns.
    # A flag absent from a source file is unknown, so it becomes missing—not zero.
    for flag in FAILURE_FLAGS:
        if flag not in failure.columns:
            failure[flag] = pd.NA
        flag_values = pd.to_numeric(failure[flag], errors="coerce")
        failure[flag] = flag_values.where(flag_values.isin([0, 1])).astype("Int64")

    failure["duplicate_name"] = failure["name_normalized"].duplicated(keep=False)

    output = CLEAN_FOLDER / f"{file.stem}_clean.csv"
    failure.to_csv(output, index=False)
    summary.append([file.name, rows_before, len(failure), rows_before - len(failure), output.name])


# ---------------------------------------------------------------------------
# 4. Clean and validate the synthetic operating-metrics dataset
# ---------------------------------------------------------------------------
metrics_file = DATA_FOLDER / "synthetic_startup_metrics.csv"
metrics = pd.read_csv(metrics_file)
rows_before = len(metrics)
metrics = metrics.drop_duplicates()
metrics = metrics.drop_duplicates(subset="startup_id", keep="first")

metrics["startup_id"] = metrics["startup_id"].astype("string").str.strip().str.upper()
for column in ["stage", "category_group", "health_status"]:
    metrics[column] = metrics[column].astype("string").str.strip()

numeric_columns = [
    "mrr_usd", "cac_usd", "ltv_usd", "ltv_cac_ratio",
    "monthly_burn_usd", "cash_in_bank_usd", "runway_months",
]
for column in numeric_columns:
    metrics[column] = pd.to_numeric(metrics[column], errors="coerce")
    metrics.loc[metrics[column] < 0, column] = pd.NA

# Recalculate the two derived metrics and compare them with the supplied values.
metrics["ltv_cac_ratio_calculated"] = (metrics["ltv_usd"] / metrics["cac_usd"]).round(2)
metrics["ltv_cac_valid"] = (
    metrics["ltv_cac_ratio_calculated"] - metrics["ltv_cac_ratio"]
).abs() <= 0.02

metrics["runway_months_calculated"] = (
    metrics["cash_in_bank_usd"] / metrics["monthly_burn_usd"]
).round(1)
metrics["runway_valid"] = (
    metrics["runway_months_calculated"] - metrics["runway_months"]
).abs() <= 0.1

metrics_output = CLEAN_FOLDER / "synthetic_startup_metrics_clean.csv"
metrics.to_csv(metrics_output, index=False)
summary.append([metrics_file.name, rows_before, len(metrics), rows_before - len(metrics), metrics_output.name])


# Save a short record of what was created.
summary_columns = ["source_file", "rows_before", "rows_after", "duplicates_removed", "clean_file"]
pd.DataFrame(summary, columns=summary_columns).to_csv(
    CLEAN_FOLDER / "cleaning_summary.csv", index=False
)

print("Cleaning finished.")
print(f"Clean files saved in: {CLEAN_FOLDER}")
