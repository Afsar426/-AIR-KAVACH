"""
AIR KAVACH - XKDR Historical Data Preprocessing

Input:
    data/raw/reference/xkdr/indore_daily_measurements_2024.parquet

Outputs:
    data/processed/air_quality/xkdr_daily_2024.parquet
    data/processed/air_quality/xkdr_daily_2024.csv
    reports/generated/reference_data/xkdr_preprocessing_summary.json
    reports/generated/reference_data/xkdr_flagged_observations.csv

Important:
- Daily data is kept separate from 15-minute event observations.
- High readings are flagged, not automatically removed.
- Original measurement values and units are preserved.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "reference"
    / "xkdr"
    / "indore_daily_measurements_2024.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "air_quality"
)

REPORT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "generated"
    / "reference_data"
)

STATION_NAMES = {
    "site_5857": "Airport Area",
    "site_5248": "Chhoti Gwaltoli",
    "site_5856": "Maguda Nagar",
    "site_5855": "Regional Park",
    "site_5854": "Residency Area",
}

# These are screening thresholds for review, not universal
# physical limits or proof that a reading is incorrect.
REVIEW_THRESHOLDS = {
    "PM2.5": 250.0,
    "PM10": 500.0,
    "NO2": 200.0,
    "SO2": 100.0,
}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    df = pd.read_parquet(INPUT_FILE)

    required_columns = [
        "station_id",
        "parameter_name",
        "unit",
        "period_start",
        "mean",
        "min",
        "max",
        "n",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    original_rows = len(df)

    # Preserve original source values for traceability.
    df["source_dataset"] = "XKDR India Air Quality Database"
    df["source_file"] = INPUT_FILE.name
    df["source_aggregation"] = "daily"
    df["source_period_start"] = df["period_start"].astype(str)

    # Standardize text fields without changing measurement meaning.
    df["station_id"] = (
        df["station_id"]
        .astype("string")
        .str.strip()
    )

    df["parameter_name"] = (
        df["parameter_name"]
        .astype("string")
        .str.strip()
        .str.upper()
        .replace({
            "PM2.5": "PM2.5",
            "PM10": "PM10",
            "NO2": "NO2",
            "SO2": "SO2",
        })
    )

    df["unit"] = (
        df["unit"]
        .astype("string")
        .str.strip()
    )

    # Parse the database's naive local timestamps as IST.
    local_time = pd.to_datetime(
        df["period_start"],
        errors="coerce",
    )

    df["timestamp_ist"] = local_time.dt.tz_localize(
        "Asia/Kolkata",
        ambiguous="NaT",
        nonexistent="NaT",
    )

    df["timestamp_utc"] = (
        df["timestamp_ist"]
        .dt.tz_convert("UTC")
    )

    # Convert measurement fields to numeric.
    for column in ["mean", "min", "max", "n"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df["station_name"] = (
        df["station_id"]
        .map(STATION_NAMES)
        .fillna("Unknown station")
    )

    df["parameter_name"] = df["parameter_name"].replace({
        "PM 2.5": "PM2.5",
        "PM 10": "PM10",
    })

    # Preserve all rows and explicitly identify quality concerns.
    df["flag_negative_measurement"] = (
        (df["mean"] < 0)
        | (df["min"] < 0)
        | (df["max"] < 0)
    ).fillna(False)

    df["flag_invalid_min_mean_max_order"] = (
        (df["min"] > df["mean"])
        | (df["mean"] > df["max"])
    ).fillna(False)

    df["flag_missing_measurement"] = (
        df[["mean", "min", "max", "n"]]
        .isna()
        .any(axis=1)
    )

    df["flag_nonpositive_sample_count"] = (
        df["n"] <= 0
    ).fillna(False)

    df["review_threshold"] = df["parameter_name"].map(
        REVIEW_THRESHOLDS
    )

    df["flag_high_daily_mean_for_review"] = (
        df["mean"] > df["review_threshold"]
    ).fillna(False)

    # Flag low sample counts for review.
# This is a provisional screening threshold, not a validated completeness rule.
    df["flag_low_sample_count"] = (
    df["n"] < 12
    ).fillna(False)

    df["quality_review_required"] = df[
    [
        "flag_negative_measurement",
        "flag_invalid_min_mean_max_order",
        "flag_missing_measurement",
        "flag_nonpositive_sample_count",
        "flag_high_daily_mean_for_review",
        "flag_low_sample_count",
    ]
    ].any(axis=1)

    df["timestamp_parse_failed"] = (
        df["timestamp_utc"].isna()
    )

    # Check standardized key uniqueness.
    key_columns = [
        "station_id",
        "parameter_name",
        "timestamp_utc",
    ]

    df["duplicate_key"] = df.duplicated(
        subset=key_columns,
        keep=False,
    )

    # Preserve units; never silently convert or mix them.
    unit_counts = (
        df.groupby(
            ["parameter_name", "unit"],
            dropna=False,
        )
        .size()
        .reset_index(name="records")
    )

    unit_counts.to_csv(
        REPORT_DIR / "xkdr_preprocessing_units.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # Save the full dataset, including flagged observations.
    parquet_path = OUTPUT_DIR / "xkdr_daily_2024.parquet"
    csv_path = OUTPUT_DIR / "xkdr_daily_2024.csv"

    df.to_parquet(parquet_path, index=False)
    df.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig",
    )

    # Save all rows requiring manual review.
    flagged = df.loc[
        df["quality_review_required"]
        | df["timestamp_parse_failed"]
        | df["duplicate_key"]
    ].copy()

    flagged_path = (
        REPORT_DIR / "xkdr_flagged_observations.csv"
    )

    flagged.to_csv(
        flagged_path,
        index=False,
        encoding="utf-8-sig",
    )

    # Coverage by station and pollutant.
    coverage = (
        df.groupby(
            [
                "station_id",
                "station_name",
                "parameter_name",
                "unit",
            ],
            dropna=False,
        )
        .agg(
            records=("timestamp_utc", "size"),
            valid_mean=("mean", "count"),
            distinct_days=("timestamp_utc", "nunique"),
            first_timestamp_utc=("timestamp_utc", "min"),
            last_timestamp_utc=("timestamp_utc", "max"),
            flagged_records=("quality_review_required", "sum"),
        )
        .reset_index()
    )

    coverage.to_csv(
        REPORT_DIR / "xkdr_preprocessed_coverage.csv",
        index=False,
        encoding="utf-8-sig",
    )

    summary = {
        "project": "AIR KAVACH",
        "dataset": "XKDR Indore Daily Measurements 2024",
        "processed_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "input_rows": int(original_rows),
        "output_rows": int(len(df)),
        "rows_removed": int(original_rows - len(df)),
        "unique_stations": int(df["station_id"].nunique()),
        "unique_pollutants": int(
            df["parameter_name"].nunique()
        ),
        "unique_units": int(df["unit"].nunique()),
        "aggregation_level": "daily",
        "timestamp_policy": (
            "Source period_start is interpreted as IST, then converted "
            "to UTC. Daily values remain daily aggregates."
        ),
        "duplicate_key_rows": int(df["duplicate_key"].sum()),
        "timestamp_parse_failures": int(
            df["timestamp_parse_failed"].sum()
        ),
        "quality_review_rows": int(
            df["quality_review_required"].sum()
        ),
        "high_daily_mean_review_rows": int(
            df["flag_high_daily_mean_for_review"].sum()
        ),
        "negative_measurement_rows": int(
            df["flag_negative_measurement"].sum()
        ),
        "invalid_order_rows": int(
            df["flag_invalid_min_mean_max_order"].sum()
        ),
        "missing_measurement_rows": int(
            df["flag_missing_measurement"].sum()
        ),
        "nonpositive_sample_count_rows": int(
            df["flag_nonpositive_sample_count"].sum()
        ),
        "units": [
            {
                "parameter": str(row["parameter_name"]),
                "unit": str(row["unit"]),
                "records": int(row["records"]),
            }
            for _, row in unit_counts.iterrows()
        ],
        "outputs": {
            "parquet": str(parquet_path),
            "csv": str(csv_path),
            "flagged_records": str(flagged_path),
        },
        "limitations": [
            "Daily averages cannot be treated as 15-minute measurements.",
            "High-value flags indicate review candidates, not confirmed errors.",
            "Historical air-quality observations do not independently establish factory attribution.",
            "Source station identifiers must be mapped and validated before cross-dataset comparisons.",
        ],
    }

    summary_path = (
        REPORT_DIR / "xkdr_preprocessing_summary.json"
    )

    summary_path.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("=" * 70)
    print("AIR KAVACH - XKDR PREPROCESSING COMPLETED")
    print("=" * 70)

    print(f"Input rows: {original_rows}")
    print(f"Output rows: {len(df)}")
    print(f"Rows removed: {original_rows - len(df)}")
    print(f"Unique stations: {df['station_id'].nunique()}")
    print(f"Unique pollutants: {df['parameter_name'].nunique()}")
    print(f"Rows flagged for review: {len(flagged)}")
    print(
        "High daily means flagged:",
        int(df["flag_high_daily_mean_for_review"].sum()),
    )

    print("\nOutput files:")
    print(parquet_path)
    print(csv_path)
    print(flagged_path)
    print(summary_path)

    print(
        "\nNo historical records were merged with the "
        "existing 15-minute event dataset."
    )


if __name__ == "__main__":
    main()