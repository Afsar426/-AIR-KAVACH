"""
AIR KAVACH - XKDR Historical Data Quality Audit

Audits:
- Missing values
- Duplicate station/pollutant/date records
- Station and pollutant coverage
- Measurement units
- Negative measurements
- Date coverage
- Daily sample-count quality

Important:
XKDR period_start timestamps are interpreted as IST wall-clock
timestamps according to the database documentation.

This script does not merge data or infer industrial source attribution.
"""

import json
from pathlib import Path

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


def save_csv(dataframe, filename):
    path = OUTPUT_DIR / filename
    dataframe.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Saved: {path}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {INPUT_FILE}"
        )

    df = pd.read_parquet(INPUT_FILE)

    print("=" * 70)
    print("AIR KAVACH - XKDR DATA QUALITY AUDIT")
    print("=" * 70)

    print("\n[1] Basic information")
    print("-" * 70)

    print("Input:", INPUT_FILE)
    print("Rows:", len(df))
    print("Columns:", len(df.columns))
    print("Column names:", list(df.columns))

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
            f"Required columns missing: {missing_columns}"
        )

    # Parse daily timestamps as naive local time.
    # Convert to UTC only in a separate derived column.
    df["period_start_ist"] = pd.to_datetime(
        df["period_start"],
        errors="coerce",
    )

    df["period_start_utc"] = (
        df["period_start_ist"]
        .dt.tz_localize(
            "Asia/Kolkata",
            ambiguous="NaT",
            nonexistent="NaT",
        )
        .dt.tz_convert("UTC")
    )

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

    # ---------------------------------------------------------
    # 2. Missing values
    # ---------------------------------------------------------
    print("\n[2] Missing values")
    print("-" * 70)

    missing_report = pd.DataFrame({
        "column": df.columns,
        "missing_count": [
            int(df[column].isna().sum())
            for column in df.columns
        ],
    })

    missing_report["missing_percent"] = (
        missing_report["missing_count"] / len(df) * 100
        if len(df)
        else 0
    )

    print(missing_report.to_string(index=False))

    save_csv(
        missing_report,
        "xkdr_missing_values.csv",
    )

    # ---------------------------------------------------------
    # 3. Duplicate records
    # ---------------------------------------------------------
    print("\n[3] Duplicate checks")
    print("-" * 70)

    duplicate_key = [
        "station_id",
        "parameter_name",
        "period_start",
    ]

    duplicate_mask = df.duplicated(
        subset=duplicate_key,
        keep=False,
    )

    duplicate_rows = df.loc[duplicate_mask].copy()

    print(
        "Rows participating in duplicate station/parameter/date keys:",
        len(duplicate_rows),
    )

    save_csv(
        duplicate_rows,
        "xkdr_duplicate_records.csv",
    )

    # ---------------------------------------------------------
    # 4. Station and pollutant coverage
    # ---------------------------------------------------------
    print("\n[4] Station and pollutant coverage")
    print("-" * 70)

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
            records=("period_start_ist", "size"),
            first_date=("period_start_ist", "min"),
            last_date=("period_start_ist", "max"),
            distinct_days=("period_start_ist", "nunique"),
            valid_mean=("mean", "count"),
            valid_min=("min", "count"),
            valid_max=("max", "count"),
            valid_sample_count=("n", "count"),
        )
        .reset_index()
    )

    coverage["possible_calendar_days"] = (
        coverage["last_date"] - coverage["first_date"]
    ).dt.days + 1

    coverage["calendar_coverage_percent"] = (
        100
        * coverage["distinct_days"]
        / coverage["possible_calendar_days"]
    )

    coverage["calendar_coverage_percent"] = (
        coverage["calendar_coverage_percent"].round(2)
    )

    print(coverage.to_string(index=False))

    save_csv(
        coverage,
        "xkdr_station_pollutant_coverage.csv",
    )

    # ---------------------------------------------------------
    # 5. Unit consistency
    # ---------------------------------------------------------
    print("\n[5] Units by pollutant")
    print("-" * 70)

    units_report = (
        df.groupby(
            ["parameter_name", "unit"],
            dropna=False,
        )
        .size()
        .reset_index(name="record_count")
    )

    print(units_report.to_string(index=False))

    save_csv(
        units_report,
        "xkdr_units_report.csv",
    )

    # ---------------------------------------------------------
    # 6. Measurement range checks
    # ---------------------------------------------------------
    print("\n[6] Measurement range checks")
    print("-" * 70)

    negative_mean = df["mean"] < 0
    negative_min = df["min"] < 0
    negative_max = df["max"] < 0

    invalid_order = (
        (df["min"] > df["mean"])
        | (df["mean"] > df["max"])
    )

    invalid_sample_count = df["n"] < 0

    range_checks = {
        "negative_mean_rows": int(negative_mean.sum()),
        "negative_min_rows": int(negative_min.sum()),
        "negative_max_rows": int(negative_max.sum()),
        "min_mean_max_order_violations": int(
            invalid_order.sum()
        ),
        "negative_sample_count_rows": int(
            invalid_sample_count.sum()
        ),
        "missing_mean_rows": int(df["mean"].isna().sum()),
        "missing_min_rows": int(df["min"].isna().sum()),
        "missing_max_rows": int(df["max"].isna().sum()),
        "missing_sample_count_rows": int(df["n"].isna().sum()),
    }

    for name, count in range_checks.items():
        print(f"{name}: {count}")

    suspicious_mask = (
        negative_mean
        | negative_min
        | negative_max
        | invalid_order
        | invalid_sample_count
    )

    suspicious = df.loc[suspicious_mask].copy()

    save_csv(
        suspicious,
        "xkdr_suspicious_measurements.csv",
    )

    # ---------------------------------------------------------
    # 7. Overall numeric statistics
    # ---------------------------------------------------------
    print("\n[7] Descriptive statistics")
    print("-" * 70)

    statistics = (
        df.groupby(
            ["parameter_name", "unit"],
            dropna=False,
        )
        .agg(
            records=("mean", "count"),
            mean_of_daily_means=("mean", "mean"),
            median_daily_mean=("mean", "median"),
            minimum_observed_value=("min", "min"),
            maximum_observed_value=("max", "max"),
            average_sample_count=("n", "mean"),
        )
        .reset_index()
    )

    print(statistics.to_string(index=False))

    save_csv(
        statistics,
        "xkdr_pollutant_statistics.csv",
    )

    # ---------------------------------------------------------
    # 8. Timestamp and period summary
    # ---------------------------------------------------------
    valid_dates = df["period_start_ist"].dropna()

    timestamp_summary = {
        "timestamp_interpretation": (
            "XKDR period_start interpreted as IST wall-clock time "
            "based on published database metadata."
        ),
        "first_date_ist": (
            str(valid_dates.min()) if len(valid_dates) else None
        ),
        "last_date_ist": (
            str(valid_dates.max()) if len(valid_dates) else None
        ),
        "first_timestamp_utc": (
            str(df["period_start_utc"].min())
            if df["period_start_utc"].notna().any()
            else None
        ),
        "last_timestamp_utc": (
            str(df["period_start_utc"].max())
            if df["period_start_utc"].notna().any()
            else None
        ),
        "rows_with_unparseable_timestamps": int(
            df["period_start_ist"].isna().sum()
        ),
    }

    # ---------------------------------------------------------
    # 9. Final report
    # ---------------------------------------------------------
    report = {
        "project": "AIR KAVACH",
        "dataset": "XKDR Indore Daily Measurements 2024",
        "rows": int(len(df)),
        "unique_stations": int(df["station_id"].nunique()),
        "unique_pollutants": int(
            df["parameter_name"].nunique()
        ),
        "unique_units": int(df["unit"].nunique()),
        "duplicate_key_rows": int(duplicate_mask.sum()),
        "missing_values_by_column": {
            str(key): int(value)
            for key, value in df.isna().sum().items()
        },
        "range_checks": range_checks,
        "timestamp_summary": timestamp_summary,
        "limitations": [
            "Daily aggregate data cannot validate individual 15-minute events.",
            "Calendar coverage does not guarantee valid measurements on every day.",
            "Missing records must not be interpreted as zero pollution.",
            "Data quality checks do not establish factory-level source attribution.",
        ],
    }

    report_path = OUTPUT_DIR / "xkdr_quality_audit.json"

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 70)
    print("AUDIT COMPLETED")
    print("=" * 70)

    print("Quality report:", report_path)
    print("Coverage report: xkdr_station_pollutant_coverage.csv")
    print("Units report: xkdr_units_report.csv")
    print("Statistics report: xkdr_pollutant_statistics.csv")

    print(
        "\nNext step: inspect coverage and units before integrating "
        "these observations with the existing AIR KAVACH dataset."
    )


if __name__ == "__main__":
    main()