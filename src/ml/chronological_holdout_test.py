"""
AIR KAVACH — Chronological ML Holdout Evaluation

Purpose:
1. Build past-only time-series features.
2. Split observations chronologically.
3. Train Isolation Forest on training-period data only.
4. Evaluate anomaly flags on later validation/test periods.
5. Save scores and summary reports.

IMPORTANT:
No ground-truth labels are available in this evaluation.
Therefore, this script does NOT calculate model accuracy,
precision, recall, or F1-score.

Run from the project root:
    python src/ml/chronological_holdout_test.py
"""

from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


# =========================================================
# CONFIGURATION
# =========================================================

ROOT = Path.cwd()

INPUT_FILE = (
    ROOT / "data/processed/air_quality/air_quality.parquet"
)

OUTPUT_DIR = ROOT / "reports/generated"

SCORES_FILE = (
    OUTPUT_DIR / "chronological_holdout_scores.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "chronological_holdout_summary.csv"
)

REPORT_FILE = (
    OUTPUT_DIR / "chronological_holdout_report.json"
)

TRAIN_FRACTION = 0.70
VALIDATION_FRACTION = 0.15

CONTAMINATION = 0.02
N_ESTIMATORS = 300
RANDOM_STATE = 42

ROLLING_WINDOW = 96
MIN_HISTORY = 24
MAX_CONTINUOUS_GAP_MINUTES = 15

FEATURES = [
    "value",
    "deviation",
    "past_std",
    "hour_sin",
    "hour_cos",
]

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# 1. LOAD DATA
# =========================================================

def load_data():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    df = pd.read_parquet(INPUT_FILE)

    required = {
        "station",
        "timestamp",
        "value",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
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
    )

    df = df.sort_values(
        ["station", "timestamp"]
    ).reset_index(drop=True)

    # Avoid ambiguous duplicate station-timestamp observations.
    duplicate_count = int(
        df.duplicated(
            subset=["station", "timestamp"]
        ).sum()
    )

    if duplicate_count:
        raise ValueError(
            f"Found {duplicate_count} duplicate "
            "station-timestamp rows. Resolve duplicates first."
        )

    return df


# =========================================================
# 2. BUILD PAST-ONLY FEATURES
# =========================================================

def build_features(df):
    """
    Historical rolling features use previous observations only.

    Current value is available at prediction time.
    Future observations are never used to construct
    the rolling mean or standard deviation.
    """

    all_groups = []

    for station, station_df in df.groupby(
        "station",
        sort=True,
    ):
        station_df = station_df.copy()

        station_df = station_df.sort_values(
            "timestamp"
        ).reset_index(drop=True)

        gap_minutes = (
            station_df["timestamp"]
            .diff()
            .dt.total_seconds()
            .div(60)
        )

        # Start a new segment after gaps > 15 minutes.
        station_df["segment_id"] = (
            gap_minutes
            .gt(MAX_CONTINUOUS_GAP_MINUTES)
            .cumsum()
        )

        station_df["past_mean"] = np.nan
        station_df["past_std"] = np.nan

        for _, indices in station_df.groupby(
            "segment_id"
        ).groups.items():

            values = (
                station_df.loc[indices, "value"]
                .astype(float)
            )

            past_values = values.shift(1)

            station_df.loc[
                indices, "past_mean"
            ] = (
                past_values
                .rolling(
                    ROLLING_WINDOW,
                    min_periods=MIN_HISTORY,
                )
                .mean()
                .to_numpy()
            )

            station_df.loc[
                indices, "past_std"
            ] = (
                past_values
                .rolling(
                    ROLLING_WINDOW,
                    min_periods=MIN_HISTORY,
                )
                .std()
                .to_numpy()
            )

        station_df["deviation"] = (
            station_df["value"]
            - station_df["past_mean"]
        )

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

        all_groups.append(station_df)

    result = pd.concat(
        all_groups,
        ignore_index=True,
    )

    return result.sort_values(
        ["timestamp", "station"]
    ).reset_index(drop=True)


# =========================================================
# 3. CHRONOLOGICAL DATE SPLIT
# =========================================================

def assign_splits(df):
    dates = sorted(
        df["timestamp"].dt.floor("D").dropna().unique()
    )

    if len(dates) < 10:
        raise ValueError(
            "Not enough unique dates for a useful "
            "chronological split."
        )

    train_end = int(
        len(dates) * TRAIN_FRACTION
    )

    validation_end = int(
        len(dates)
        * (TRAIN_FRACTION + VALIDATION_FRACTION)
    )

    train_end = max(1, train_end)

    validation_end = max(
        train_end + 1,
        validation_end,
    )

    validation_end = min(
        validation_end,
        len(dates) - 1,
    )

    train_dates = set(dates[:train_end])

    validation_dates = set(
        dates[train_end:validation_end]
    )

    test_dates = set(
        dates[validation_end:]
    )

    df = df.copy()

    df["date"] = df["timestamp"].dt.floor("D")

    df["split"] = np.select(
        [
            df["date"].isin(train_dates),
            df["date"].isin(validation_dates),
            df["date"].isin(test_dates),
        ],
        [
            "train",
            "validation",
            "test",
        ],
        default="unassigned",
    )

    boundaries = {
        "train_start": str(dates[0]),
        "train_end": str(dates[train_end - 1]),
        "validation_start": str(
            dates[train_end]
        ),
        "validation_end": str(
            dates[validation_end - 1]
        ),
        "test_start": str(
            dates[validation_end]
        ),
        "test_end": str(dates[-1]),
        "unique_dates": len(dates),
    }

    return df, boundaries


# =========================================================
# 4. TRAIN ON TRAINING PERIOD ONLY
# =========================================================

def train_and_score(df):
    df = df.copy()

    df["anomaly_score"] = np.nan
    df["is_anomaly"] = pd.Series(
        pd.NA,
        index=df.index,
        dtype="boolean",
    )

    df["model_trained"] = False

    models = {}

    for station in sorted(
        df["station"].unique()
    ):

        station_mask = (
            df["station"] == station
        )

        train_mask = (
            station_mask
            & (df["split"] == "train")
        )

        eligible_train = df.loc[
            train_mask
            & df[FEATURES].notna().all(axis=1)
        ]

        if len(eligible_train) < 100:
            print(
                f"WARNING: {station}: only "
                f"{len(eligible_train)} eligible "
                "training rows. Skipping station."
            )
            continue

        model = IsolationForest(
            n_estimators=N_ESTIMATORS,
            contamination=CONTAMINATION,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )

        model.fit(
            eligible_train[FEATURES]
        )

        models[station] = model

        # Score all eligible observations for this station.
        # The model itself was fitted on training data only.
        score_mask = (
            station_mask
            & df[FEATURES].notna().all(axis=1)
        )

        eligible_indices = df.index[
            score_mask
        ]

        eligible_features = df.loc[
            eligible_indices, FEATURES
        ]

        predictions = model.predict(
            eligible_features
        )

        decision_values = model.decision_function(
            eligible_features
        )

        # Higher anomaly_score means more unusual.
        anomaly_scores = -decision_values

        df.loc[
            eligible_indices,
            "anomaly_score",
        ] = anomaly_scores

        df.loc[
            eligible_indices,
            "is_anomaly",
        ] = (predictions == -1)

        df.loc[
            eligible_indices,
            "model_trained",
        ] = True

        print(
            f"{station}: "
            f"training rows={len(eligible_train)}, "
            f"scored rows={len(eligible_indices)}"
        )

    return df, models


# =========================================================
# 5. BUILD SUMMARY
# =========================================================

def build_summary(df):
    rows = []

    scored = df[
        df["model_trained"]
        & df["is_anomaly"].notna()
    ].copy()

    for (split, station), group in scored.groupby(
        ["split", "station"],
        sort=True,
    ):

        flagged = group[
            group["is_anomaly"].astype(bool)
        ]

        rows.append({
            "split": split,
            "station": station,
            "scored_observations": int(len(group)),
            "flagged_observations": int(len(flagged)),
            "flag_rate_percent": round(
                100 * len(flagged) / len(group),
                3,
            ) if len(group) else None,
            "mean_pm25": round(
                float(group["value"].mean()),
                3,
            ),
            "mean_anomaly_score": round(
                float(group["anomaly_score"].mean()),
                6,
            ),
            "max_pm25": round(
                float(group["value"].max()),
                3,
            ),
        })

    return pd.DataFrame(rows)


# =========================================================
# 6. MAIN
# =========================================================

def main():
    print("=" * 70)
    print("AIR KAVACH — CHRONOLOGICAL HOLDOUT EVALUATION")
    print("=" * 70)

    raw = load_data()

    print(f"\nInput observations: {len(raw)}")
    print(
        "Stations:",
        ", ".join(sorted(raw["station"].unique())),
    )

    features = build_features(raw)

    features, boundaries = assign_splits(
        features
    )

    print("\nChronological boundaries:")
    print(json.dumps(boundaries, indent=2))

    print("\nRows per split:")

    print(
        features.groupby("split")
        .size()
        .to_string()
    )

    scored, models = train_and_score(
        features
    )

    scored.to_csv(
        SCORES_FILE,
        index=False,
    )

    summary = build_summary(scored)

    summary.to_csv(
        SUMMARY_FILE,
        index=False,
    )

    print("\nHoldout summary:")
    if not summary.empty:
        print(summary.to_string(index=False))
    else:
        print("No eligible rows were scored.")

    test_rows = scored[
        (scored["split"] == "test")
        & scored["is_anomaly"].notna()
    ]

    report = {
        "project": "AIR KAVACH",
        "evaluation_type": (
            "Chronological holdout; unlabelled evaluation"
        ),
        "input_observations": int(len(raw)),
        "feature_eligible_observations": int(
            scored["model_trained"].sum()
        ),
        "models_trained": sorted(models.keys()),
        "split_boundaries": boundaries,
        "train_fraction": TRAIN_FRACTION,
        "validation_fraction": VALIDATION_FRACTION,
        "test_fraction_approx": round(
            1 - TRAIN_FRACTION - VALIDATION_FRACTION,
            3,
        ),
        "contamination": CONTAMINATION,
        "n_estimators": N_ESTIMATORS,
        "test_scored_observations": int(
            len(test_rows)
        ),
        "test_flagged_observations": int(
            test_rows["is_anomaly"].astype(bool).sum()
        ),
        "outputs": [
            str(SCORES_FILE.relative_to(ROOT)),
            str(SUMMARY_FILE.relative_to(ROOT)),
            str(REPORT_FILE.relative_to(ROOT)),
        ],
        "limitations": [
            "No verified ground-truth labels were used.",
            "Flag rates are not accuracy, precision, or recall.",
            "Models are trained separately for each station.",
            "Training uses only the chronological training period.",
            "Past-only features may use earlier observations from the validation/test period, as in a rolling operational system.",
            "The test period must not be used to tune thresholds or model settings.",
            "This evaluates temporal behaviour, not factory-source attribution.",
        ],
    }

    REPORT_FILE.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nSaved reports:")
    print(SCORES_FILE)
    print(SUMMARY_FILE)
    print(REPORT_FILE)

    print(
        "\nIMPORTANT: This is a chronological, "
        "unlabelled evaluation—not an accuracy test."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)