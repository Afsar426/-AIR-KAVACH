from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd


# ============================================================
# AIR KAVACH — SCORE DISTRIBUTION TEST
# Purpose: Compare train, validation and test model behaviour.
# This is a diagnostic, NOT an accuracy evaluation.
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = ROOT / "reports" / "generated" / "chronological_holdout_scores.csv"
OUTPUT_DIR = ROOT / "reports" / "generated"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STATION_REPORT = OUTPUT_DIR / "score_distribution_station_report.csv"
DAILY_REPORT = OUTPUT_DIR / "score_distribution_daily_report.csv"
OBSERVATION_REPORT = OUTPUT_DIR / "score_distribution_observations.csv"
JSON_REPORT = OUTPUT_DIR / "score_distribution_report.json"


def find_column(df, candidates, description, required=True):
    """Find a column without assuming one exact naming convention."""
    lookup = {str(c).strip().lower(): c for c in df.columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    if required:
        raise ValueError(
            f"Could not identify {description} column.\n"
            f"Available columns: {list(df.columns)}"
        )

    return None


def main():
    print("=" * 72)
    print("AIR KAVACH — SCORE DISTRIBUTION TEST")
    print("=" * 72)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}\n"
            "Run chronological_holdout_test.py first."
        )

    df = pd.read_csv(INPUT_FILE)

    print(f"\nInput file: {INPUT_FILE}")
    print(f"Input rows: {len(df)}")
    print(f"Available columns: {list(df.columns)}")

    # Identify columns robustly.
    station_col = find_column(
        df, ["station", "station_name"], "station"
    )

    split_col = find_column(
        df, ["split", "data_split", "period"], "split"
    )

    score_col = find_column(
        df,
        ["score", "anomaly_score", "model_score",
         "decision_score", "anomaly_strength"],
        "anomaly score"
    )

    timestamp_col = find_column(
        df,
        ["timestamp", "datetime", "date_time", "time"],
        "timestamp"
    )

    value_col = find_column(
        df,
        ["value", "pm25", "pm2_5", "pm25_value"],
        "PM2.5 value"
    )

    flag_col = find_column(
        df,
        ["is_anomaly", "ml_flag", "anomaly_flag",
         "flagged", "is_flagged", "prediction"],
        "anomaly flag",
        required=False
    )

    # Standardize internal column names.
    rename_map = {
        station_col: "station",
        split_col: "split",
        score_col: "score",
        timestamp_col: "timestamp",
        value_col: "pm25",
    }

    if flag_col is not None:
        rename_map[flag_col] = "flag"

    df = df.rename(columns=rename_map)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"], errors="coerce", utc=True
    )

    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df["pm25"] = pd.to_numeric(df["pm25"], errors="coerce")

    df["station"] = df["station"].astype(str).str.strip()
    df["split"] = (
        df["split"].astype(str).str.strip().str.lower()
    )

    if "flag" in df.columns:
        if df["flag"].dtype == object:
            normalized = df["flag"].astype(str).str.lower().str.strip()

            mapping = {
                "true": 1, "false": 0,
                "yes": 1, "no": 0,
                "1": 1, "0": 0,
                "anomaly": 1, "normal": 0,
                "flagged": 1, "not_flagged": 0,
            }

            df["flag"] = normalized.map(mapping)

        else:
            df["flag"] = pd.to_numeric(
                df["flag"], errors="coerce"
            )

        df["flag"] = df["flag"].where(
            df["flag"].isin([0, 1])
        )

    # Only rows with valid timestamps, scores and PM2.5 values.
    valid = df.dropna(
        subset=["timestamp", "score", "pm25"]
    ).copy()

    if valid.empty:
        raise ValueError(
            "No valid scored observations found in the input file."
        )

    print(f"Valid scored rows: {len(valid)}")

    print("\nRows by split:")
    print(valid["split"].value_counts().to_string())

    # --------------------------------------------------------
    # STEP A: Determine score direction from training labels.
    # Higher scores may mean more anomalous, or lower scores
    # may mean more anomalous. We infer direction if possible.
    # --------------------------------------------------------

    train = valid[valid["split"] == "train"].copy()

    direction = "unknown"
    direction_note = (
        "Could not infer score direction from training flags."
    )

    if "flag" in valid.columns:
        train_labeled = train.dropna(subset=["flag"])

        flagged_scores = train_labeled.loc[
            train_labeled["flag"] == 1, "score"
        ]

        normal_scores = train_labeled.loc[
            train_labeled["flag"] == 0, "score"
        ]

        if len(flagged_scores) > 0 and len(normal_scores) > 0:
            flagged_median = float(flagged_scores.median())
            normal_median = float(normal_scores.median())

            if flagged_median > normal_median:
                direction = "higher_is_more_anomalous"
                direction_note = (
                    "Training flagged rows have a higher median score."
                )
            elif flagged_median < normal_median:
                direction = "lower_is_more_anomalous"
                direction_note = (
                    "Training flagged rows have a lower median score."
                )
            else:
                direction_note = (
                    "Flagged and unflagged training medians are equal."
                )

    print("\nScore direction:")
    print(direction)
    print(direction_note)

    # --------------------------------------------------------
    # STEP B: Compare score distributions by station and split.
    # --------------------------------------------------------

    station_rows = []

    for (station, split), group in valid.groupby(
        ["station", "split"], dropna=False
    ):
        scores = group["score"].dropna()
        pm25 = group["pm25"].dropna()

        row = {
            "station": station,
            "split": split,
            "rows": len(group),
            "score_mean": scores.mean(),
            "score_std": scores.std(),
            "score_min": scores.min(),
            "score_p10": scores.quantile(0.10),
            "score_p25": scores.quantile(0.25),
            "score_median": scores.median(),
            "score_p75": scores.quantile(0.75),
            "score_p90": scores.quantile(0.90),
            "score_p95": scores.quantile(0.95),
            "score_p98": scores.quantile(0.98),
            "score_max": scores.max(),
            "pm25_mean": pm25.mean(),
            "pm25_median": pm25.median(),
            "pm25_p90": pm25.quantile(0.90),
            "pm25_max": pm25.max(),
        }

        if "flag" in group.columns:
            flags = group["flag"].dropna()

            row["flagged_rows"] = int((flags == 1).sum())
            row["flag_rate_percent"] = (
                float((flags == 1).mean() * 100)
                if len(flags) else np.nan
            )

        station_rows.append(row)

    station_report = pd.DataFrame(station_rows)

    # --------------------------------------------------------
    # STEP C: Compare future scores with training score range.
    #
    # If higher score = more anomalous, use training 98th
    # percentile. If lower score = more anomalous, use 2nd
    # percentile. This is a diagnostic comparison only.
    # --------------------------------------------------------

    threshold_rows = []

    for station in sorted(valid["station"].unique()):
        station_train = valid[
            (valid["station"] == station)
            & (valid["split"] == "train")
        ]

        if station_train.empty:
            continue

        train_scores = station_train["score"].dropna()

        if train_scores.empty:
            continue

        if direction == "higher_is_more_anomalous":
            reference_threshold = float(
                train_scores.quantile(0.98)
            )
            threshold_rule = "training_98th_percentile"
        elif direction == "lower_is_more_anomalous":
            reference_threshold = float(
                train_scores.quantile(0.02)
            )
            threshold_rule = "training_2nd_percentile"
        else:
            reference_threshold = np.nan
            threshold_rule = "direction_unknown"

        for split in ["train", "validation", "test"]:
            current = valid[
                (valid["station"] == station)
                & (valid["split"] == split)
            ]

            if current.empty:
                continue

            if pd.notna(reference_threshold):
                if direction == "higher_is_more_anomalous":
                    beyond = (
                        current["score"] > reference_threshold
                    )
                else:
                    beyond = (
                        current["score"] < reference_threshold
                    )

                beyond_count = int(beyond.sum())
                beyond_rate = float(beyond.mean() * 100)
            else:
                beyond_count = None
                beyond_rate = None

            threshold_rows.append({
                "station": station,
                "split": split,
                "rows": len(current),
                "training_reference_threshold": reference_threshold,
                "threshold_rule": threshold_rule,
                "outside_training_reference_count": beyond_count,
                "outside_training_reference_percent": beyond_rate,
                "score_median": current["score"].median(),
                "score_p90": current["score"].quantile(0.90),
                "score_p98": current["score"].quantile(0.98),
            })

    threshold_report = pd.DataFrame(threshold_rows)

    # --------------------------------------------------------
    # STEP D: Daily score/flag behaviour.
    # --------------------------------------------------------

    valid["date"] = valid["timestamp"].dt.strftime("%Y-%m-%d")

    daily_group_columns = ["split", "station", "date"]

    daily_agg = {
        "timestamp": "count",
        "pm25": ["mean", "max"],
        "score": ["mean", "median", "max"],
    }

    daily_report = (
        valid.groupby(daily_group_columns)
        .agg(daily_agg)
    )

    daily_report.columns = [
        "_".join(str(part) for part in col if part)
        for col in daily_report.columns.to_flat_index()
    ]

    daily_report = daily_report.reset_index()
    daily_report = daily_report.rename(
        columns={"timestamp_count": "observations"}
    )

    if "flag" in valid.columns:
        daily_flags = (
            valid.groupby(daily_group_columns)["flag"]
            .agg(
                flagged_observations=lambda x: int(
                    (x == 1).sum()
                ),
                flag_rate_percent=lambda x: (
                    float((x == 1).mean() * 100)
                    if x.notna().any() else np.nan
                ),
            )
            .reset_index()
        )

        daily_report = daily_report.merge(
            daily_flags,
            on=daily_group_columns,
            how="left"
        )

    # --------------------------------------------------------
    # STEP E: Export observation-level diagnostic.
    # --------------------------------------------------------

    observation_columns = [
        "timestamp", "station", "split", "pm25", "score"
    ]

    if "flag" in valid.columns:
        observation_columns.append("flag")

    observations_report = valid[observation_columns].copy()

    if pd.notna(
        threshold_report.get(
            "training_reference_threshold",
            pd.Series(dtype=float)
        )
    ).any() if "training_reference_threshold" in threshold_report.columns else False:
        threshold_lookup = (
            threshold_report[
                threshold_report["split"] == "train"
            ][["station", "training_reference_threshold"]]
            .drop_duplicates("station")
        )

        observations_report = observations_report.merge(
            threshold_lookup,
            on="station",
            how="left"
        )

        if direction == "higher_is_more_anomalous":
            observations_report["outside_training_reference"] = (
                observations_report["score"]
                > observations_report["training_reference_threshold"]
            )
        elif direction == "lower_is_more_anomalous":
            observations_report["outside_training_reference"] = (
                observations_report["score"]
                < observations_report["training_reference_threshold"]
            )

    # --------------------------------------------------------
    # STEP F: Save reports and summary.
    # --------------------------------------------------------

    station_report.to_csv(STATION_REPORT, index=False)
    daily_report.to_csv(DAILY_REPORT, index=False)
    observations_report.to_csv(OBSERVATION_REPORT, index=False)

    summary = {
        "input_rows": int(len(df)),
        "valid_scored_rows": int(len(valid)),
        "rows_by_split": {
            str(k): int(v)
            for k, v in valid["split"].value_counts().items()
        },
        "stations": sorted(
            valid["station"].dropna().unique().tolist()
        ),
        "score_direction": direction,
        "score_direction_note": direction_note,
        "flag_column_available": "flag" in valid.columns,
        "interpretation": (
            "Distribution diagnostic only. "
            "It does not measure accuracy, precision, recall, "
            "causal attribution or verified pollution events."
        ),
        "reports": {
            "station": str(STATION_REPORT),
            "daily": str(DAILY_REPORT),
            "observations": str(OBSERVATION_REPORT),
        },
    }

    with open(JSON_REPORT, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, default=str)

    print("\nSTATION SCORE DISTRIBUTION:")
    display_columns = [
        "station", "split", "rows",
        "score_median", "score_p90", "score_p98",
        "pm25_median", "pm25_p90"
    ]

    if "flag_rate_percent" in station_report.columns:
        display_columns.append("flag_rate_percent")

    print(
        station_report[display_columns]
        .round(4)
        .to_string(index=False)
    )

    print("\nTRAINING REFERENCE COMPARISON:")
    if not threshold_report.empty:
        print(
            threshold_report.round(4).to_string(index=False)
        )
    else:
        print("No threshold comparison could be generated.")

    print("\nSaved reports:")
    print(STATION_REPORT)
    print(DAILY_REPORT)
    print(OBSERVATION_REPORT)
    print(JSON_REPORT)

    print("\nIMPORTANT:")
    print(
        "These score ranges are diagnostic references, not validated "
        "operational thresholds."
    )
    print(
        "This test does not establish model accuracy or source causation."
    )


if __name__ == "__main__":
    main()