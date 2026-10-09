"""
AIR KAVACH — Historical Feature Quality Test

Compare historical feature behaviour under 15, 30 and 60-minute
segment gap thresholds.

Checks:
- Past mean
- Past standard deviation
- Deviation from past mean
- Feature availability
- Feature changes following large gaps

This is a diagnostic, not an accuracy evaluation.
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

SUMMARY_FILE = (
    OUTPUT_DIR / "historical_feature_quality_summary.csv"
)

STATION_FILE = (
    OUTPUT_DIR / "historical_feature_quality_station.csv"
)

OBSERVATION_FILE = (
    OUTPUT_DIR / "historical_feature_quality_observations.csv"
)

GAP_FILE = (
    OUTPUT_DIR / "historical_feature_quality_gap_review.csv"
)

JSON_FILE = (
    OUTPUT_DIR / "historical_feature_quality_report.json"
)

GAP_THRESHOLDS = [15, 30, 60]

ROLLING_WINDOW = 96
MIN_HISTORY = 24


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
            f"Missing required columns: {sorted(missing)}"
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
    ).copy()

    df = df.sort_values(
        ["station", "timestamp"]
    ).reset_index(drop=True)

    duplicate_count = int(
        df.duplicated(
            subset=["station", "timestamp"]
        ).sum()
    )

    if duplicate_count:
        raise ValueError(
            f"Found {duplicate_count} duplicate "
            "station-timestamp rows."
        )

    return df


# ============================================================
# BUILD HISTORICAL FEATURES
# ============================================================

def build_features(df, gap_threshold):
    all_groups = []

    for station, original_group in df.groupby(
        "station",
        sort=True,
    ):
        group = original_group.copy()

        group = group.sort_values(
            "timestamp"
        ).reset_index(drop=True)

        group["gap_minutes"] = (
            group["timestamp"]
            .diff()
            .dt.total_seconds()
            .div(60)
        )

        group["segment_id"] = (
            group["gap_minutes"]
            .gt(gap_threshold)
            .cumsum()
            .astype(int)
        )

        group["past_mean"] = np.nan
        group["past_std"] = np.nan
        group["deviation"] = np.nan
        group["history_count"] = 0

        for segment_id, segment in group.groupby(
            "segment_id",
            sort=True,
        ):
            indices = segment.index

            past_values = (
                segment["value"]
                .astype(float)
                .shift(1)
            )

            past_mean = past_values.rolling(
                ROLLING_WINDOW,
                min_periods=MIN_HISTORY,
            ).mean()

            past_std = past_values.rolling(
                ROLLING_WINDOW,
                min_periods=MIN_HISTORY,
            ).std()

            history_count = (
                past_values.notna()
                .rolling(
                    ROLLING_WINDOW,
                    min_periods=1,
                )
                .sum()
            )

            group.loc[
                indices, "past_mean"
            ] = past_mean.to_numpy()

            group.loc[
                indices, "past_std"
            ] = past_std.to_numpy()

            group.loc[
                indices, "deviation"
            ] = (
                segment["value"].astype(float)
                - past_mean
            ).to_numpy()

            group.loc[
                indices, "history_count"
            ] = history_count.to_numpy()

        group["eligible"] = (
            group["past_mean"].notna()
            & group["past_std"].notna()
            & group["deviation"].notna()
        )

        group["gap_threshold_minutes"] = (
            gap_threshold
        )

        all_groups.append(group)

    return pd.concat(
        all_groups,
        ignore_index=True,
    )


# ============================================================
# SUMMARY STATISTICS
# ============================================================

def summarize_features(featured):
    rows = []

    feature_columns = [
        "past_mean",
        "past_std",
        "deviation",
    ]

    for (threshold, station), group in featured.groupby(
        ["gap_threshold_minutes", "station"],
        sort=True,
    ):
        eligible = group[group["eligible"]]

        row = {
            "gap_threshold_minutes": int(threshold),
            "station": station,
            "total_observations": int(len(group)),
            "eligible_observations": int(len(eligible)),
            "ineligible_observations": int(
                len(group) - len(eligible)
            ),
            "eligible_percent": round(
                float(group["eligible"].mean() * 100),
                2,
            ),
            "segment_count": int(
                group["segment_id"].nunique()
            ),
            "large_gap_count": int(
                group["gap_minutes"].gt(threshold).sum()
            ),
        }

        for feature in feature_columns:
            values = eligible[feature].dropna()

            row[f"{feature}_mean"] = (
                float(values.mean())
                if len(values) else np.nan
            )

            row[f"{feature}_median"] = (
                float(values.median())
                if len(values) else np.nan
            )

            row[f"{feature}_p90"] = (
                float(values.quantile(0.90))
                if len(values) else np.nan
            )

        row["absolute_deviation_median"] = (
            float(eligible["deviation"].abs().median())
            if len(eligible) else np.nan
        )

        rows.append(row)

    return pd.DataFrame(rows)


# ============================================================
# OBSERVATIONS AFTER LARGE GAPS
# ============================================================

def build_gap_review(featured):
    rows = []

    for threshold in GAP_THRESHOLDS:
        subset = featured[
            featured["gap_threshold_minutes"] == threshold
        ]

        for station, group in subset.groupby("station"):
            group = group.sort_values("timestamp")

            # The first observation in each segment has a gap
            # that triggered a new segment, except the first
            # segment of a station.
            starts = group[
                group["gap_minutes"] > threshold
            ]

            for _, start_row in starts.iterrows():
                segment_id = start_row["segment_id"]

                segment = group[
                    group["segment_id"] == segment_id
                ].sort_values("timestamp")

                # First observation after the gap plus the next
                # 24 observations. These rows are for inspection.
                window = segment.head(MIN_HISTORY + 1)

                rows.append({
                    "threshold_minutes": threshold,
                    "station": station,
                    "gap_minutes": float(
                        start_row["gap_minutes"]
                    ),
                    "gap_start_observation": (
                        start_row["timestamp"]
                    ),
                    "segment_id": int(segment_id),
                    "segment_length": int(len(segment)),
                    "first_25_rows_eligible": int(
                        window["eligible"].sum()
                    ),
                    "first_25_rows_total": int(len(window)),
                    "first_25_rows_past_mean_available": int(
                        window["past_mean"].notna().sum()
                    ),
                    "first_25_rows_past_std_available": int(
                        window["past_std"].notna().sum()
                    ),
                    "first_25_rows_abs_deviation_median": (
                        float(window["deviation"].abs().median())
                        if window["deviation"].notna().any()
                        else np.nan
                    ),
                })

    return pd.DataFrame(rows)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 72)
    print("AIR KAVACH — HISTORICAL FEATURE QUALITY TEST")
    print("=" * 72)

    raw = load_data()

    print(f"\nInput observations: {len(raw)}")
    print(
        "Stations:",
        ", ".join(sorted(raw["station"].unique())),
    )

    all_results = []

    for threshold in GAP_THRESHOLDS:
        print(
            f"\nProcessing gap threshold: {threshold} minutes"
        )

        featured = build_features(
            raw,
            threshold,
        )

        print(
            f"Eligible observations: "
            f"{featured['eligible'].sum()} / {len(featured)} "
            f"({featured['eligible'].mean() * 100:.2f}%)"
        )

        all_results.append(featured)

    combined = pd.concat(
        all_results,
        ignore_index=True,
    )

    summary = summarize_features(combined)
    gap_review = build_gap_review(combined)

    # Save station-level summary.
    summary.to_csv(
        STATION_FILE,
        index=False,
    )

    # Overall threshold summary.
    overall = (
        combined.groupby("gap_threshold_minutes")
        .agg(
            total_observations=("value", "size"),
            eligible_observations=("eligible", "sum"),
            segment_count=(
                "segment_id",
                lambda x: x.groupby(
                    combined.loc[x.index, "station"]
                ).nunique().sum(),
            ),
            large_gap_count=(
                "gap_minutes",
                lambda x: int(
                    x.gt(
                        combined.loc[
                            x.index,
                            "gap_threshold_minutes",
                        ].iloc[0]
                    ).sum()
                ),
            ),
        )
        .reset_index()
    )

    overall["ineligible_observations"] = (
        overall["total_observations"]
        - overall["eligible_observations"]
    )

    overall["eligible_percent"] = (
        overall["eligible_observations"]
        / overall["total_observations"]
        * 100
    ).round(2)

    # Save observation-level results.
    observation_columns = [
        "station",
        "timestamp",
        "value",
        "gap_minutes",
        "segment_id",
        "gap_threshold_minutes",
        "history_count",
        "past_mean",
        "past_std",
        "deviation",
        "eligible",
    ]

    combined[observation_columns].to_csv(
        OBSERVATION_FILE,
        index=False,
    )

    gap_review.to_csv(
        GAP_FILE,
        index=False,
    )

    report = {
        "project": "AIR KAVACH",
        "input_observations": int(len(raw)),
        "stations": sorted(
            raw["station"].unique().tolist()
        ),
        "gap_thresholds": GAP_THRESHOLDS,
        "rolling_window": ROLLING_WINDOW,
        "minimum_history": MIN_HISTORY,
        "overall_results": overall.to_dict(
            orient="records"
        ),
        "limitations": [
            "Feature availability does not establish feature correctness.",
            "Larger gap thresholds can connect readings across longer periods.",
            "No model accuracy or causal attribution is evaluated.",
            "No gap threshold is automatically recommended by this diagnostic.",
        ],
        "outputs": {
            "summary": str(SUMMARY_FILE),
            "station_summary": str(STATION_FILE),
            "observations": str(OBSERVATION_FILE),
            "gap_review": str(GAP_FILE),
        },
    }

    SUMMARY_FILE.write_text(
        overall.to_csv(index=False),
        encoding="utf-8",
    )

    JSON_FILE.write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )

    print("\nOVERALL FEATURE QUALITY SUMMARY:")

    print(
        overall.round(3).to_string(index=False)
    )

    print("\nSTATION FEATURE SUMMARY:")

    print(
        summary[
            [
                "gap_threshold_minutes",
                "station",
                "eligible_observations",
                "eligible_percent",
                "past_std_median",
                "absolute_deviation_median",
            ]
        ]
        .round(3)
        .to_string(index=False)
    )

    print("\nSaved reports:")
    print(SUMMARY_FILE)
    print(STATION_FILE)
    print(OBSERVATION_FILE)
    print(GAP_FILE)
    print(JSON_FILE)

    print("\nIMPORTANT:")
    print(
        "This is a feature diagnostic, not an accuracy test."
    )


if __name__ == "__main__":
    main()