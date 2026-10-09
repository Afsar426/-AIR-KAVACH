from pathlib import Path

import numpy as np
import pandas as pd


# ==========================================================
# AIR KAVACH - ML DATASET VALIDATION
# ==========================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT
    / "data"
    / "features"
    / "ml"
    / "attribution_dataset.parquet"
)

OUTPUT_DIR = ROOT / "reports" / "generated"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():

    section("AIR KAVACH - ML DATASET VALIDATION")

    # ------------------------------------------------------
    # 1. Load dataset
    # ------------------------------------------------------

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {INPUT_FILE}"
        )

    df = pd.read_parquet(INPUT_FILE)

    print("\n[1] Dataset dimensions")
    print("Rows:", len(df))
    print("Columns:", len(df.columns))
    print("Unique events:", df["event_id"].nunique())
    print("Unique stations:", df["station"].nunique())
    print("Unique factories:", df["factory_id"].nunique())

    # ------------------------------------------------------
    # 2. Check duplicate event-factory pairs
    # ------------------------------------------------------

    print("\n[2] Duplicate checks")

    pair_columns = [
        "event_id",
        "station",
        "factory_id",
    ]

    duplicate_pairs = df.duplicated(
        subset=pair_columns
    ).sum()

    print(
        "Duplicate event-factory pairs:",
        int(duplicate_pairs)
    )

    # ------------------------------------------------------
    # 3. Missing-value report
    # ------------------------------------------------------

    section("MISSING VALUE ANALYSIS")

    missing = df.isna().sum()

    missing_report = pd.DataFrame({
        "column": missing.index,
        "missing_count": missing.values,
        "missing_percent": (
            missing.values / max(len(df), 1) * 100
        ).round(2),
    })

    missing_report = missing_report.sort_values(
        "missing_percent",
        ascending=False
    )

    print(
        missing_report[
            missing_report["missing_count"] > 0
        ].to_string(index=False)
    )

    missing_report.to_csv(
        OUTPUT_DIR / "ml_missing_value_report.csv",
        index=False
    )

    # ------------------------------------------------------
    # 4. Numerical feature statistics
    # ------------------------------------------------------

    section("NUMERICAL FEATURE STATISTICS")

    numeric_columns = [
        "distance_km",
        "peak_pm25",
        "peak_z_score",
        "event_duration_minutes",
        "wind_direction_mean_deg",
        "wind_speed_mean_mps",
        "wind_coverage",
        "wind_alignment",
        "attribution_score",
        "relative_likelihood",
        "confidence_percent",
        "uncertainty_percent",
    ]

    numeric_columns = [
        col
        for col in numeric_columns
        if col in df.columns
    ]

    stats = df[numeric_columns].describe().T

    print(stats.round(3).to_string())

    stats.to_csv(
        OUTPUT_DIR / "ml_numeric_feature_statistics.csv"
    )

    # ------------------------------------------------------
    # 5. Range and consistency checks
    # ------------------------------------------------------

    section("FEATURE RANGE CHECKS")

    checks = {}

    checks["negative_distance"] = int(
        (df["distance_km"] < 0).sum()
    )

    checks["negative_pm25"] = int(
        (df["peak_pm25"] < 0).sum()
    )

    checks["invalid_wind_direction"] = int(
        (
            df["wind_direction_mean_deg"].notna()
            &
            (
                (df["wind_direction_mean_deg"] < 0)
                |
                (df["wind_direction_mean_deg"] > 360)
            )
        ).sum()
    )

    checks["invalid_wind_speed"] = int(
        (
            df["wind_speed_mean_mps"].notna()
            &
            (df["wind_speed_mean_mps"] < 0)
        ).sum()
    )

    checks["invalid_wind_coverage"] = int(
        (
            df["wind_coverage"].notna()
            &
            (
                (df["wind_coverage"] < 0)
                |
                (df["wind_coverage"] > 1)
            )
        ).sum()
    )

    checks["invalid_confidence"] = int(
        (
            df["confidence_percent"].notna()
            &
            (
                (df["confidence_percent"] < 0)
                |
                (df["confidence_percent"] > 100)
            )
        ).sum()
    )

    checks["invalid_uncertainty"] = int(
        (
            df["uncertainty_percent"].notna()
            &
            (
                (df["uncertainty_percent"] < 0)
                |
                (df["uncertainty_percent"] > 100)
            )
        ).sum()
    )

    for name, value in checks.items():
        print(f"{name}: {value}")

    # ------------------------------------------------------
    # 6. Source label audit
    # ------------------------------------------------------

    section("LABEL AUDIT")

    if "source_label" in df.columns:

        print(
            "Verified labels:",
            int(df["source_label"].notna().sum())
        )

        print(
            "Unlabelled rows:",
            int(df["source_label"].isna().sum())
        )

    print(
        "\nNo verified source labels are currently available."
    )

    print(
        "Therefore, supervised classification metrics "
        "cannot yet be calculated honestly."
    )

    # ------------------------------------------------------
    # 7. Event-level leakage warning
    # ------------------------------------------------------

    section("LEAKAGE AND EVALUATION WARNINGS")

    print(
        "1. Attribution score is produced by the existing "
        "heuristic engine."
    )

    print(
        "2. Confidence and uncertainty are derived from "
        "existing attribution evidence."
    )

    print(
        "3. Do not use these outputs as input features "
        "when attempting to independently reproduce "
        "the same heuristic score."
    )

    print(
        "4. Candidates belonging to the same event are "
        "related observations."
    )

    print(
        "5. Train/test splitting must keep all candidates "
        "from one event in the same split."
    )

    # ------------------------------------------------------
    # 8. Event and station distributions
    # ------------------------------------------------------

    section("EVENT DISTRIBUTION BY STATION")

    station_counts = (
        df.groupby("station")["event_id"]
        .nunique()
        .sort_values(ascending=False)
    )

    print(station_counts.to_string())

    station_counts.to_csv(
        OUTPUT_DIR / "ml_events_by_station.csv"
    )

    # ------------------------------------------------------
    # 9. Final status
    # ------------------------------------------------------

    section("VALIDATION SUMMARY")

    print(
        "Duplicate event-factory pairs:",
        int(duplicate_pairs)
    )

    print(
        "Feature range violations:",
        sum(checks.values())
    )

    print(
        "Wind speed missing values:",
        int(df["wind_speed_mean_mps"].isna().sum())
    )

    print(
        "Validation reports saved to:"
    )

    print(OUTPUT_DIR)

    print(
        "\nDATASET AUDIT COMPLETE"
    )


if __name__ == "__main__":
    main()