"""
AIR KAVACH - Historical Pollution Pattern Analysis

Input:
    data/processed/air_quality/xkdr_daily_2024.parquet

Outputs:
    reports/generated/reference_data/
        monthly_pollution_trends.csv
        station_pollution_summary.csv
        historical_data_coverage.csv
        historical_pollution_analysis.json
        monthly pollutant charts

Important:
- Daily observations remain daily aggregates.
- High readings are not automatically removed.
- Low sample counts are reported as a quality indicator.
- Historical data does not establish factory-level attribution.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "air_quality"
    / "xkdr_daily_2024.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "generated"
    / "reference_data"
)

CHART_DIR = OUTPUT_DIR / "charts"

POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2"]


def save_csv(df, filename):
    path = OUTPUT_DIR / filename

    df.to_csv(
        path,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Saved: {path}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    df = pd.read_parquet(INPUT_FILE)

    required_columns = [
        "station_id",
        "station_name",
        "parameter_name",
        "unit",
        "timestamp_utc",
        "mean",
        "min",
        "max",
        "n",
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Required columns missing: {missing}"
        )

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    for column in ["mean", "min", "max", "n"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df["parameter_name"] = (
        df["parameter_name"]
        .astype(str)
        .str.strip()
    )

    df["month"] = (
        df["timestamp_utc"]
        .dt.tz_convert("Asia/Kolkata")
        .dt.to_period("M")
        .astype(str)
    )

    # Preserve all source records.
    # n < 12 is a provisional review indicator only.
    df["low_sample_count_flag"] = (
        df["n"] < 12
    ).fillna(False)

    df["high_daily_mean_flag"] = (
        df["flag_high_daily_mean_for_review"]
        .fillna(False)
        .astype(bool)
    )

    df["review_flag"] = (
        df["quality_review_required"]
        .fillna(False)
        .astype(bool)
    )

    # -------------------------------------------------
    # 1. Monthly pollutant trends
    # -------------------------------------------------
    monthly = (
        df.groupby(
            [
                "station_id",
                "station_name",
                "parameter_name",
                "unit",
                "month",
            ],
            dropna=False,
        )
        .agg(
            record_count=("mean", "count"),
            mean_daily_mean=("mean", "mean"),
            median_daily_mean=("mean", "median"),
            min_observed=("min", "min"),
            max_observed=("max", "max"),
            average_sample_count=("n", "mean"),
            low_sample_count_days=(
                "low_sample_count_flag",
                "sum",
            ),
            high_daily_mean_days=(
                "high_daily_mean_flag",
                "sum",
            ),
            flagged_days=("review_flag", "sum"),
        )
        .reset_index()
    )

    monthly["mean_daily_mean"] = (
        monthly["mean_daily_mean"].round(3)
    )

    monthly["median_daily_mean"] = (
        monthly["median_daily_mean"].round(3)
    )

    monthly["average_sample_count"] = (
        monthly["average_sample_count"].round(2)
    )

    save_csv(
        monthly,
        "monthly_pollution_trends.csv",
    )

    # -------------------------------------------------
    # 2. Station-wise pollutant statistics
    # -------------------------------------------------
    station_summary = (
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
            available_daily_records=("mean", "count"),
            average_daily_mean=("mean", "mean"),
            median_daily_mean=("mean", "median"),
            minimum_observed=("min", "min"),
            maximum_observed=("max", "max"),
            average_sample_count=("n", "mean"),
            low_sample_count_days=(
                "low_sample_count_flag",
                "sum",
            ),
            high_daily_mean_days=(
                "high_daily_mean_flag",
                "sum",
            ),
            flagged_days=("review_flag", "sum"),
            first_timestamp=("timestamp_utc", "min"),
            last_timestamp=("timestamp_utc", "max"),
        )
        .reset_index()
    )

    save_csv(
        station_summary,
        "station_pollution_summary.csv",
    )

    # -------------------------------------------------
    # 3. Coverage by station, pollutant and month
    # -------------------------------------------------
    coverage = (
        df.groupby(
            [
                "station_id",
                "station_name",
                "parameter_name",
                "month",
            ],
            dropna=False,
        )
        .agg(
            available_records=("mean", "count"),
            low_sample_count_records=(
                "low_sample_count_flag",
                "sum",
            ),
            flagged_records=("review_flag", "sum"),
        )
        .reset_index()
    )

    coverage["expected_calendar_days"] = (
        pd.PeriodIndex(
            coverage["month"],
            freq="M",
        ).days_in_month
    )

    coverage["calendar_coverage_percent"] = (
        100
        * coverage["available_records"]
        / coverage["expected_calendar_days"]
    ).round(2)

    save_csv(
        coverage,
        "historical_data_coverage.csv",
    )

    # -------------------------------------------------
    # 4. Monthly trend charts
    # -------------------------------------------------
    for pollutant in POLLUTANTS:
        pollutant_df = monthly.loc[
            monthly["parameter_name"] == pollutant
        ].copy()

        if pollutant_df.empty:
            print(
                f"No data available for chart: {pollutant}"
            )
            continue

        fig, ax = plt.subplots(figsize=(12, 6))

        for station_name, station_data in (
            pollutant_df.groupby("station_name")
        ):
            station_data = station_data.sort_values("month")

            ax.plot(
                station_data["month"],
                station_data["mean_daily_mean"],
                marker="o",
                label=station_name,
            )

        ax.set_title(
            f"2024 Monthly {pollutant} Trends - Indore"
        )

        ax.set_xlabel("Month")
        ax.set_ylabel("Mean of Daily Mean Values (µg/m³)")

        ax.tick_params(
            axis="x",
            labelrotation=45,
        )

        ax.legend()
        ax.grid(True, alpha=0.3)

        fig.tight_layout()

        chart_path = (
            CHART_DIR
            / f"monthly_{pollutant.replace('.', '_')}_trend.png"
        )

        fig.savefig(
            chart_path,
            dpi=160,
            bbox_inches="tight",
        )

        plt.close(fig)

        print(f"Saved chart: {chart_path}")

    # -------------------------------------------------
    # 5. Summary report
    # -------------------------------------------------
    summary = {
        "project": "AIR KAVACH",
        "dataset": "XKDR Indore Daily Measurements 2024",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "input_rows": int(len(df)),
        "unique_stations": int(df["station_id"].nunique()),
        "unique_pollutants": int(
            df["parameter_name"].nunique()
        ),
        "available_months": sorted(
            df["month"].dropna().unique().tolist()
        ),
        "low_sample_count_records": int(
            df["low_sample_count_flag"].sum()
        ),
        "high_daily_mean_records": int(
            df["high_daily_mean_flag"].sum()
        ),
        "records_flagged_for_review": int(
            df["review_flag"].sum()
        ),
        "outputs": {
            "monthly_trends": (
                "reports/generated/reference_data/"
                "monthly_pollution_trends.csv"
            ),
            "station_summary": (
                "reports/generated/reference_data/"
                "station_pollution_summary.csv"
            ),
            "coverage": (
                "reports/generated/reference_data/"
                "historical_data_coverage.csv"
            ),
            "charts": (
                "reports/generated/reference_data/charts/"
            ),
        },
        "limitations": [
            "The source contains daily aggregate observations.",
            "Calendar coverage does not establish complete daily sampling.",
            "Low sample count is a provisional review indicator.",
            "Monthly averages do not establish industrial source attribution.",
            "Station differences may reflect location, measurement coverage, "
            "meteorology, and other sources of pollution.",
        ],
    }

    summary_path = (
        OUTPUT_DIR / "historical_pollution_analysis.json"
    )

    summary_path.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 65)
    print("HISTORICAL POLLUTION ANALYSIS COMPLETED")
    print("=" * 65)

    print("Input rows:", len(df))
    print("Stations:", df["station_id"].nunique())
    print("Pollutants:", df["parameter_name"].nunique())
    print(
        "Low sample count records:",
        int(df["low_sample_count_flag"].sum()),
    )
    print(
        "High daily mean records:",
        int(df["high_daily_mean_flag"].sum()),
    )

    print("\nReports saved in:", OUTPUT_DIR)


if __name__ == "__main__":
    main()