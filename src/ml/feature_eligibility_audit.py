"""
AIR KAVACH — Feature Eligibility Audit

Checks:
1. Missing feature counts.
2. Time gaps between observations.
3. Continuous segment lengths.
4. Eligibility for rolling features.
5. Eligible observations by chronological split.

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
    ROOT / "data" / "processed" / "air_quality"
    / "air_quality.parquet"
)

OUTPUT_DIR = ROOT / "reports" / "generated"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STATION_REPORT = OUTPUT_DIR / "feature_eligibility_station.csv"
SEGMENT_REPORT = OUTPUT_DIR / "feature_eligibility_segments.csv"
GAP_REPORT = OUTPUT_DIR / "feature_eligibility_gaps.csv"
SPLIT_REPORT = OUTPUT_DIR / "feature_eligibility_splits.csv"
JSON_REPORT = OUTPUT_DIR / "feature_eligibility_report.json"

ROLLING_WINDOW = 96
MIN_HISTORY = 24
MAX_GAP_MINUTES = 15

TRAIN_FRACTION = 0.70
VALIDATION_FRACTION = 0.15

FEATURES = [
    "value",
    "deviation",
    "past_std",
    "hour_sin",
    "hour_cos",
]


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

    duplicate_count = int(
        df.duplicated(
            subset=["station", "timestamp"]
        ).sum()
    )

    if duplicate_count:
        raise ValueError(
            f"Found {duplicate_count} duplicate station-timestamp rows."
        )

    return df


# ============================================================
# ASSIGN CHRONOLOGICAL SPLITS
# ============================================================

def assign_splits(df):
    dates = sorted(
        df["timestamp"].dt.floor("D").unique()
    )

    if len(dates) < 10:
        raise ValueError(
            "Not enough dates for chronological splitting."
        )

    train_end = max(
        1, int(len(dates) * TRAIN_FRACTION)
    )

    validation_end = int(
        len(dates)
        * (TRAIN_FRACTION + VALIDATION_FRACTION)
    )

    validation_end = max(
        train_end + 1, validation_end
    )

    validation_end = min(
        validation_end, len(dates) - 1
    )

    df = df.copy()
    df["date"] = df["timestamp"].dt.floor("D")

    df["split"] = np.select(
        [
            df["date"].isin(dates[:train_end]),
            df["date"].isin(
                dates[train_end:validation_end]
            ),
            df["date"].isin(dates[validation_end:]),
        ],
        ["train", "validation", "test"],
        default="unassigned",
    )

    return df


# ============================================================
# BUILD FEATURES AND AUDIT SEGMENTS
# ============================================================

def build_audit_features(df):
    all_groups = []
    segment_rows = []
    gap_rows = []

    for station, station_df in df.groupby(
        "station", sort=True
    ):
        station_df = station_df.copy()

        station_df = station_df.sort_values(
            "timestamp"
        ).reset_index(drop=True)

        station_df["gap_minutes"] = (
            station_df["timestamp"]
            .diff()
            .dt.total_seconds()
            / 60
        )

        # New segment starts after a gap > 15 minutes.
        station_df["segment_id"] = (
            station_df["gap_minutes"]
            .gt(MAX_GAP_MINUTES)
            .cumsum()
            .astype(int)
        )

        station_df["past_mean"] = np.nan
        station_df["past_std"] = np.nan

        for segment_id, segment in station_df.groupby(
            "segment_id", sort=True
        ):
            idx = segment.index
            values = segment["value"].astype(float)

            past_values = values.shift(1)

            past_mean = past_values.rolling(
                ROLLING_WINDOW,
                min_periods=MIN_HISTORY,
            ).mean()

            past_std = past_values.rolling(
                ROLLING_WINDOW,
                min_periods=MIN_HISTORY,
            ).std()

            station_df.loc[idx, "past_mean"] = (
                past_mean.to_numpy()
            )

            station_df.loc[idx, "past_std"] = (
                past_std.to_numpy()
            )

            segment_rows.append({
                "station": station,
                "segment_id": int(segment_id),
                "start": segment["timestamp"].min(),
                "end": segment["timestamp"].max(),
                "observations": int(len(segment)),
                "eligible_rolling_rows": int(
                    past_mean.notna().sum()
                ),
                "ineligible_rolling_rows": int(
                    past_mean.isna().sum()
                ),
                "has_24_observations": bool(
                    len(segment) >= MIN_HISTORY + 1
                ),
            })

        # Record large time gaps.
        large_gaps = station_df[
            station_df["gap_minutes"] > MAX_GAP_MINUTES
        ]

        for _, row in large_gaps.iterrows():
            gap_rows.append({
                "station": station,
                "previous_timestamp": (
                    station_df.loc[
                        row.name - 1, "timestamp"
                    ]
                    if row.name > 0
                    else pd.NaT
                ),
                "current_timestamp": row["timestamp"],
                "gap_minutes": row["gap_minutes"],
                "new_segment_id": row["segment_id"],
            })

        hour = (
            station_df["timestamp"].dt.hour
            + station_df["timestamp"].dt.minute / 60.0
        )

        station_df["hour_sin"] = np.sin(
            2 * np.pi * hour / 24
        )

        station_df["hour_cos"] = np.cos(
            2 * np.pi * hour / 24
        )

        station_df["deviation"] = (
            station_df["value"]
            - station_df["past_mean"]
        )

        station_df["eligible"] = (
            station_df[FEATURES]
            .notna()
            .all(axis=1)
        )

        all_groups.append(station_df)

    result = pd.concat(
        all_groups,
        ignore_index=True,
    )

    return (
        result,
        pd.DataFrame(segment_rows),
        pd.DataFrame(gap_rows),
    )


# ============================================================
# STATION SUMMARY
# ============================================================

def build_station_report(df):
    rows = []

    for station, group in df.groupby("station"):
        eligible = group["eligible"]

        rows.append({
            "station": station,
            "total_observations": int(len(group)),
            "eligible_observations": int(eligible.sum()),
            "ineligible_observations": int((~eligible).sum()),
            "eligible_percent": round(
                float(eligible.mean() * 100), 2
            ),
            "missing_past_mean": int(
                group["past_mean"].isna().sum()
            ),
            "missing_past_std": int(
                group["past_std"].isna().sum()
            ),
            "missing_deviation": int(
                group["deviation"].isna().sum()
            ),
            "large_gaps": int(
                (group["gap_minutes"] > MAX_GAP_MINUTES).sum()
            ),
            "segment_count": int(
                group["segment_id"].nunique()
            ),
            "maximum_gap_minutes": (
                float(group["gap_minutes"].max())
                if group["gap_minutes"].notna().any()
                else None
            ),
        })

    return pd.DataFrame(rows)


# ============================================================
# SPLIT SUMMARY
# ============================================================

def build_split_report(df):
    rows = []

    for (station, split), group in df.groupby(
        ["station", "split"]
    ):
        eligible = group["eligible"]

        rows.append({
            "station": station,
            "split": split,
            "total_observations": int(len(group)),
            "eligible_observations": int(eligible.sum()),
            "ineligible_observations": int((~eligible).sum()),
            "eligible_percent": round(
                float(eligible.mean() * 100), 2
            ),
            "missing_past_mean": int(
                group["past_mean"].isna().sum()
            ),
            "missing_past_std": int(
                group["past_std"].isna().sum()
            ),
        })

    return pd.DataFrame(rows)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 72)
    print("AIR KAVACH — FEATURE ELIGIBILITY AUDIT")
    print("=" * 72)

    raw = load_data()
    raw = assign_splits(raw)

    print(f"\nInput observations: {len(raw)}")
    print(
        "Stations:",
        ", ".join(sorted(raw["station"].unique())),
    )

    featured, segments, gaps = build_audit_features(raw)

    station_report = build_station_report(featured)
    split_report = build_split_report(featured)

    station_report.to_csv(
        STATION_REPORT, index=False
    )

    segments.to_csv(
        SEGMENT_REPORT, index=False
    )

    gaps.to_csv(
        GAP_REPORT, index=False
    )

    split_report.to_csv(
        SPLIT_REPORT, index=False
    )

    summary = {
        "input_observations": int(len(featured)),
        "eligible_observations": int(
            featured["eligible"].sum()
        ),
        "ineligible_observations": int(
            (~featured["eligible"]).sum()
        ),
        "eligible_percent": round(
            float(featured["eligible"].mean() * 100), 2
        ),
        "segment_count": int(
            featured.groupby("station")["segment_id"]
            .nunique()
            .sum()
        ),
        "large_gap_count": int(
            (featured["gap_minutes"] > MAX_GAP_MINUTES).sum()
        ),
        "rolling_window": ROLLING_WINDOW,
        "minimum_history": MIN_HISTORY,
        "maximum_continuous_gap_minutes": MAX_GAP_MINUTES,
        "interpretation": (
            "Eligibility audit only. Ineligible observations "
            "are not necessarily anomalous or invalid."
        ),
        "reports": {
            "station": str(STATION_REPORT),
            "segments": str(SEGMENT_REPORT),
            "gaps": str(GAP_REPORT),
            "splits": str(SPLIT_REPORT),
        },
    }

    JSON_REPORT.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\nSTATION ELIGIBILITY SUMMARY:")
    print(
        station_report.round(2).to_string(index=False)
    )

    print("\nELIGIBILITY BY SPLIT:")
    print(
        split_report.round(2).to_string(index=False)
    )

    print("\nOverall eligible observations:")
    print(
        f"{featured['eligible'].sum()} / {len(featured)} "
        f"({featured['eligible'].mean() * 100:.2f}%)"
    )

    print("\nTotal segments:", len(segments))
    print("Large gaps:", len(gaps))

    print("\nSaved reports:")
    print(STATION_REPORT)
    print(SEGMENT_REPORT)
    print(GAP_REPORT)
    print(SPLIT_REPORT)
    print(JSON_REPORT)

    print(
        "\nIMPORTANT: This audit investigates feature availability; "
        "it does not establish model accuracy."
    )


if __name__ == "__main__":
    main()