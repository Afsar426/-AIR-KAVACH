"""
AIR KAVACH — Common Observation Comparison

Compares historical features for observations that remain
eligible under all three gap thresholds: 15, 30 and 60 minutes.

This is a feature consistency diagnostic.
It does not measure anomaly detection accuracy.
"""

from pathlib import Path
import json

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT / "data" / "processed"
    / "air_quality" / "air_quality.parquet"
)

OUTPUT_DIR = ROOT / "reports" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

THRESHOLDS = [15, 30, 60]
WINDOW = 96
MIN_HISTORY = 24

SUMMARY_FILE = (
    OUTPUT_DIR / "common_observation_comparison_summary.csv"
)

STATION_FILE = (
    OUTPUT_DIR / "common_observation_comparison_station.csv"
)

DETAIL_FILE = (
    OUTPUT_DIR / "common_observation_comparison_details.csv"
)

REPORT_FILE = (
    OUTPUT_DIR / "common_observation_comparison_report.json"
)


# ============================================================
# LOAD DATA
# ============================================================

def load_data():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    df = pd.read_parquet(INPUT_FILE)

    required = {"station", "timestamp", "value"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True,
    )

    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce",
    )

    df = df.dropna(
        subset=["station", "timestamp", "value"]
    )

    df = df.sort_values(
        ["station", "timestamp"]
    ).reset_index(drop=True)

    duplicates = df.duplicated(
        subset=["station", "timestamp"]
    ).sum()

    if duplicates:
        raise ValueError(
            f"Found {duplicates} duplicate station-timestamp rows."
        )

    return df


# ============================================================
# BUILD FEATURES FOR ONE GAP THRESHOLD
# ============================================================

def build_features(df, threshold):
    results = []

    for station, station_df in df.groupby(
        "station",
        sort=True,
    ):
        station_df = station_df.copy().reset_index(drop=True)

        station_df["gap_minutes"] = (
            station_df["timestamp"]
            .diff()
            .dt.total_seconds()
            / 60
        )

        station_df["segment_id"] = (
            station_df["gap_minutes"]
            .gt(threshold)
            .cumsum()
            .astype(int)
        )

        station_df["past_mean"] = np.nan
        station_df["past_std"] = np.nan

        for _, segment in station_df.groupby(
            "segment_id",
            sort=True,
        ):
            indices = segment.index

            # Shift first: current observation is not included
            # in its own historical reference.
            past = segment["value"].shift(1)

            rolling_mean = past.rolling(
                WINDOW,
                min_periods=MIN_HISTORY,
            ).mean()

            rolling_std = past.rolling(
                WINDOW,
                min_periods=MIN_HISTORY,
            ).std()

            station_df.loc[
                indices, "past_mean"
            ] = rolling_mean.to_numpy()

            station_df.loc[
                indices, "past_std"
            ] = rolling_std.to_numpy()

        station_df["deviation"] = (
            station_df["value"]
            - station_df["past_mean"]
        )

        station_df["eligible"] = (
            station_df["past_mean"].notna()
            & station_df["past_std"].notna()
            & station_df["deviation"].notna()
        )

        station_df["gap_threshold_minutes"] = threshold

        results.append(station_df)

    return pd.concat(results, ignore_index=True)


# ============================================================
# COMPARE COMMON OBSERVATIONS
# ============================================================

def main():
    print("=" * 72)
    print("AIR KAVACH — COMMON-OBSERVATION COMPARISON")
    print("=" * 72)

    raw = load_data()

    print(f"\nInput observations: {len(raw)}")

    results = []

    for threshold in THRESHOLDS:
        print(
            f"Building features for {threshold}-minute threshold..."
        )

        results.append(
            build_features(raw, threshold)
        )

    combined = pd.concat(
        results,
        ignore_index=True,
    )

    # Each station-timestamp observation should appear once
    # per threshold.
    combined = combined.sort_values(
        ["station", "timestamp", "gap_threshold_minutes"]
    )

    # Only compare rows eligible at every threshold.
    eligibility = combined.pivot(
        index=["station", "timestamp"],
        columns="gap_threshold_minutes",
        values="eligible",
    )

    common_index = eligibility.index[
        eligibility[THRESHOLDS].fillna(False).all(axis=1)
    ]

    print(
        f"\nCommon observations eligible under all thresholds: "
        f"{len(common_index)}"
    )

    common = combined.set_index(
        ["station", "timestamp"]
    ).loc[common_index].reset_index()

    # Put threshold-specific feature values side by side.
    detail_frames = []

    for threshold in THRESHOLDS:
        subset = common[
            common["gap_threshold_minutes"] == threshold
        ][
            [
                "station",
                "timestamp",
                "value",
                "past_mean",
                "past_std",
                "deviation",
                "segment_id",
            ]
        ].copy()

        subset = subset.rename(
            columns={
                "value": f"value_{threshold}",
                "past_mean": f"past_mean_{threshold}",
                "past_std": f"past_std_{threshold}",
                "deviation": f"deviation_{threshold}",
                "segment_id": f"segment_id_{threshold}",
            }
        )

        detail_frames.append(subset)

    details = detail_frames[0]

    for frame in detail_frames[1:]:
        details = details.merge(
            frame,
            on=["station", "timestamp"],
            how="inner",
            validate="one_to_one",
        )

    # Check value consistency across thresholds.
    details["input_value_difference"] = (
        details[
            [f"value_{t}" for t in THRESHOLDS]
        ].max(axis=1)
        - details[
            [f"value_{t}" for t in THRESHOLDS]
        ].min(axis=1)
    )

    # Absolute feature differences between thresholds.
    for feature in ["past_mean", "past_std", "deviation"]:
        details[f"{feature}_diff_15_30"] = (
            details[f"{feature}_15"]
            - details[f"{feature}_30"]
        ).abs()

        details[f"{feature}_diff_15_60"] = (
            details[f"{feature}_15"]
            - details[f"{feature}_60"]
        ).abs()

        details[f"{feature}_diff_30_60"] = (
            details[f"{feature}_30"]
            - details[f"{feature}_60"]
        ).abs()

    # Overall comparison.
    summary_rows = []

    for feature in ["past_mean", "past_std", "deviation"]:
        for left, right in [(15, 30), (15, 60), (30, 60)]:
            diff = (
                details[f"{feature}_{left}"]
                - details[f"{feature}_{right}"
                ]
            ).abs()

            summary_rows.append({
                "feature": feature,
                "comparison": f"{left}_vs_{right}",
                "common_observations": int(len(details)),
                "mean_absolute_difference": (
                    float(diff.mean()) if len(diff) else None
                ),
                "median_absolute_difference": (
                    float(diff.median()) if len(diff) else None
                ),
                "p90_absolute_difference": (
                    float(diff.quantile(0.90))
                    if len(diff) else None
                ),
                "max_absolute_difference": (
                    float(diff.max()) if len(diff) else None
                ),
            })

    summary = pd.DataFrame(summary_rows)

    # Station-level comparison.
    station_rows = []

    for station, group in details.groupby("station"):
        row = {
            "station": station,
            "common_observations": int(len(group)),
        }

        for feature in ["past_mean", "past_std", "deviation"]:
            for left, right in [(15, 30), (15, 60), (30, 60)]:
                col = f"{feature}_diff_{left}_{right}"

                row[f"{col}_median"] = (
                    float(group[col].median())
                    if len(group) else None
                )

                row[f"{col}_p90"] = (
                    float(group[col].quantile(0.90))
                    if len(group) else None
                )

        station_rows.append(row)

    station_summary = pd.DataFrame(station_rows)

    # Sanity check: source value must be identical across thresholds.
    value_diff_max = (
        float(details["input_value_difference"].max())
        if len(details) else None
    )

    if value_diff_max is not None and value_diff_max != 0:
        raise ValueError(
            "Input values changed across threshold runs. "
            "Review data alignment."
        )

    summary.to_csv(SUMMARY_FILE, index=False)
    station_summary.to_csv(STATION_FILE, index=False)
    details.to_csv(DETAIL_FILE, index=False)

    report = {
        "project": "AIR KAVACH",
        "input_observations": int(len(raw)),
        "thresholds_minutes": THRESHOLDS,
        "common_observations": int(len(details)),
        "common_observations_by_station": (
            station_summary[
                ["station", "common_observations"]
            ].to_dict(orient="records")
        ),
        "input_value_difference_max": value_diff_max,
        "summary": summary.to_dict(orient="records"),
        "limitations": [
            "This is a feature consistency test, not a model accuracy test.",
            "Only observations eligible at all thresholds are compared.",
            "Results may not represent observations eligible at only one threshold.",
            "No verified pollution-event labels are used.",
        ],
    }

    REPORT_FILE.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nOVERALL FEATURE DIFFERENCES:")
    print(summary.round(4).to_string(index=False))

    print("\nCOMMON OBSERVATIONS BY STATION:")
    print(
        station_summary[
            ["station", "common_observations"]
        ].to_string(index=False)
    )

    print("\nSaved files:")
    print(SUMMARY_FILE)
    print(STATION_FILE)
    print(DETAIL_FILE)
    print(REPORT_FILE)

    print("\nCompleted. No model settings were changed.")


if __name__ == "__main__":
    main()