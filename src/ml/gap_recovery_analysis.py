"""
AIR KAVACH — Gap Recovery Analysis

Purpose:
1. Compare 15, 30 and 60 minute gap thresholds.
2. Measure eligible observations under each rule.
3. Identify short segments that cannot build sufficient history.
4. Measure how many observations are excluded at segment starts.
5. Save diagnostic reports without changing existing data.

IMPORTANT:
Alternative thresholds are for comparison only.
They are not automatically better or scientifically validated.
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
    ROOT
    / "data"
    / "processed"
    / "air_quality"
    / "air_quality.parquet"
)

OUTPUT_DIR = ROOT / "reports" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

THRESHOLD_REPORT = (
    OUTPUT_DIR / "gap_recovery_threshold_comparison.csv"
)

SEGMENT_REPORT = (
    OUTPUT_DIR / "gap_recovery_segment_details.csv"
)

STATION_REPORT = (
    OUTPUT_DIR / "gap_recovery_station_summary.csv"
)

JSON_REPORT = (
    OUTPUT_DIR / "gap_recovery_report.json"
)

GAP_THRESHOLDS_MINUTES = [15, 30, 60]

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
            f"Required columns missing: {sorted(missing)}"
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
        errors="coerce",
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

    duplicates = int(
        df.duplicated(
            subset=["station", "timestamp"]
        ).sum()
    )

    if duplicates:
        raise ValueError(
            f"Found {duplicates} duplicate station-timestamp rows."
        )

    return df


# ============================================================
# ANALYSE ONE GAP THRESHOLD
# ============================================================

def analyse_threshold(df, threshold_minutes):
    segment_rows = []
    station_rows = []

    eligible_by_index = pd.Series(
        False,
        index=df.index,
        dtype=bool,
    )

    segment_id_by_index = pd.Series(
        -1,
        index=df.index,
        dtype=int,
    )

    gap_by_index = pd.Series(
        np.nan,
        index=df.index,
        dtype=float,
    )

    # --------------------------------------------------------
    # Process each station independently.
    # --------------------------------------------------------

    for station, original_group in df.groupby(
        "station",
        sort=True,
    ):
        group = original_group.sort_values(
            "timestamp"
        ).copy()

        gaps = (
            group["timestamp"]
            .diff()
            .dt.total_seconds()
            .div(60)
        )

        # Each gap above the chosen threshold starts a segment.
        local_segment_ids = (
            gaps.gt(threshold_minutes)
            .cumsum()
            .astype(int)
        )

        local_eligible = pd.Series(
            False,
            index=group.index,
            dtype=bool,
        )

        for segment_id, segment in group.groupby(
            local_segment_ids,
            sort=True,
        ):
            indices = segment.index

            # The first 24 readings cannot have 24 previous
            # observations inside this continuous segment.
            # The 25th reading is the first eligible one.
            segment_eligible = (
                np.arange(len(segment)) >= MIN_HISTORY
            )

            local_eligible.loc[indices] = (
                segment_eligible
            )

            segment_rows.append({
                "threshold_minutes": threshold_minutes,
                "station": station,
                "segment_id": int(segment_id),
                "start_timestamp": (
                    segment["timestamp"].iloc[0]
                ),
                "end_timestamp": (
                    segment["timestamp"].iloc[-1]
                ),
                "observations": int(len(segment)),
                "eligible_observations": int(
                    segment_eligible.sum()
                ),
                "ineligible_observations": int(
                    (~segment_eligible).sum()
                ),
                "eligible_percent": round(
                    float(segment_eligible.mean() * 100),
                    2,
                ),
                "duration_minutes": round(
                    (
                        segment["timestamp"].iloc[-1]
                        - segment["timestamp"].iloc[0]
                    ).total_seconds() / 60,
                    2,
                ),
                "too_short_for_eligibility": bool(
                    len(segment) <= MIN_HISTORY
                ),
            })

        eligible_by_index.loc[group.index] = (
            local_eligible
        )

        segment_id_by_index.loc[group.index] = (
            local_segment_ids
        )

        gap_by_index.loc[group.index] = gaps

        station_rows.append({
            "threshold_minutes": threshold_minutes,
            "station": station,
            "total_observations": int(len(group)),
            "segment_count": int(
                local_segment_ids.nunique()
            ),
            "large_gap_count": int(
                gaps.gt(threshold_minutes).sum()
            ),
            "eligible_observations": int(
                local_eligible.sum()
            ),
            "ineligible_observations": int(
                (~local_eligible).sum()
            ),
            "eligible_percent": round(
                float(local_eligible.mean() * 100),
                2,
            ),
            "short_segments_le_24_rows": int(
                sum(
                    len(segment) <= MIN_HISTORY
                    for _, segment in group.groupby(
                        local_segment_ids
                    )
                )
            ),
        })

    # --------------------------------------------------------
    # Overall summary for this threshold.
    # --------------------------------------------------------

    segment_df = pd.DataFrame(segment_rows)
    station_df = pd.DataFrame(station_rows)

    total = len(df)
    eligible_count = int(eligible_by_index.sum())

    summary = {
        "threshold_minutes": threshold_minutes,
        "total_observations": total,
        "segment_count": int(len(segment_df)),
        "large_gap_count": int(
            station_df["large_gap_count"].sum()
        ),
        "eligible_observations": eligible_count,
        "ineligible_observations": total - eligible_count,
        "eligible_percent": round(
            eligible_count / total * 100,
            2,
        ) if total else 0,
        "short_segments_le_24_rows": int(
            segment_df["too_short_for_eligibility"].sum()
        ),
        "segments_with_no_eligible_rows": int(
            (
                segment_df["eligible_observations"] == 0
            ).sum()
        ),
        "segments_with_eligible_rows": int(
            (
                segment_df["eligible_observations"] > 0
            ).sum()
        ),
    }

    return summary, segment_df, station_df


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 72)
    print("AIR KAVACH — GAP RECOVERY ANALYSIS")
    print("=" * 72)

    df = load_data()

    print(f"\nInput observations: {len(df)}")
    print(
        "Stations:",
        ", ".join(sorted(df["station"].unique())),
    )

    print(f"Gap thresholds: {GAP_THRESHOLDS_MINUTES}")
    print(f"Minimum previous observations: {MIN_HISTORY}")
    print(f"Rolling window: {ROLLING_WINDOW}")

    all_summaries = []
    all_segments = []
    all_station_summaries = []

    for threshold in GAP_THRESHOLDS_MINUTES:
        summary, segments, stations = analyse_threshold(
            df,
            threshold,
        )

        all_summaries.append(summary)
        all_segments.append(segments)
        all_station_summaries.append(stations)

    threshold_report = pd.DataFrame(all_summaries)

    segment_report = pd.concat(
        all_segments,
        ignore_index=True,
    )

    station_report = pd.concat(
        all_station_summaries,
        ignore_index=True,
    )

    # --------------------------------------------------------
    # Compare eligible rows against the 15-minute baseline.
    # --------------------------------------------------------

    baseline = threshold_report.loc[
        threshold_report["threshold_minutes"] == 15,
        "eligible_observations",
    ]

    baseline_eligible = (
        int(baseline.iloc[0])
        if not baseline.empty
        else 0
    )

    threshold_report[
        "eligible_change_vs_15min"
    ] = (
        threshold_report["eligible_observations"]
        - baseline_eligible
    )

    threshold_report[
        "eligibility_change_percentage_points_vs_15min"
    ] = (
        threshold_report["eligible_percent"]
        - float(
            threshold_report.loc[
                threshold_report["threshold_minutes"] == 15,
                "eligible_percent",
            ].iloc[0]
        )
    )

    # --------------------------------------------------------
    # Save all reports.
    # --------------------------------------------------------

    threshold_report.to_csv(
        THRESHOLD_REPORT,
        index=False,
    )

    segment_report.to_csv(
        SEGMENT_REPORT,
        index=False,
    )

    station_report.to_csv(
        STATION_REPORT,
        index=False,
    )

    report = {
        "project": "AIR KAVACH",
        "input_observations": int(len(df)),
        "stations": sorted(
            df["station"].unique().tolist()
        ),
        "gap_thresholds_minutes": GAP_THRESHOLDS_MINUTES,
        "minimum_history": MIN_HISTORY,
        "rolling_window": ROLLING_WINDOW,
        "threshold_results": threshold_report.to_dict(
            orient="records"
        ),
        "limitations": [
            "Alternative thresholds are diagnostic scenarios only.",
            "Eligibility does not establish anomaly or pollution-event status.",
            "A larger gap threshold can join observations across longer intervals.",
            "The diagnostic uses observation counts and does not validate temporal continuity scientifically.",
            "No model accuracy or source-attribution accuracy is calculated.",
        ],
        "outputs": {
            "threshold_comparison": str(THRESHOLD_REPORT),
            "segment_details": str(SEGMENT_REPORT),
            "station_summary": str(STATION_REPORT),
        },
    }

    JSON_REPORT.write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # Print results.
    # --------------------------------------------------------

    print("\nOVERALL THRESHOLD COMPARISON:")

    print(
        threshold_report[
            [
                "threshold_minutes",
                "total_observations",
                "segment_count",
                "large_gap_count",
                "eligible_observations",
                "ineligible_observations",
                "eligible_percent",
                "eligible_change_vs_15min",
                "short_segments_le_24_rows",
            ]
        ].to_string(index=False)
    )

    print("\nSTATION COMPARISON:")

    print(
        station_report[
            [
                "threshold_minutes",
                "station",
                "segment_count",
                "large_gap_count",
                "eligible_observations",
                "ineligible_observations",
                "eligible_percent",
            ]
        ].to_string(index=False)
    )

    print("\nSaved reports:")
    print(THRESHOLD_REPORT)
    print(SEGMENT_REPORT)
    print(STATION_REPORT)
    print(JSON_REPORT)

    print("\nIMPORTANT:")
    print(
        "This analysis compares eligibility under alternative gap rules."
    )
    print(
        "It does not prove that a larger threshold is better."
    )


if __name__ == "__main__":
    main()