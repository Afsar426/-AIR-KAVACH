"""
AIR KAVACH — Holdout Distribution Shift Diagnostic

Purpose:
- Compare training, validation and test distributions.
- Inspect daily anomaly flag rates.
- Identify possible temporal distribution shift.
- Export unusual observations for manual review.

This script does not retrain or modify the model.
It does not calculate accuracy because ground-truth labels
are not available.

Run from project root:
    python src/ml/holdout_drift_diagnostic.py
"""

from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd


# =====================================================
# CONFIGURATION
# =====================================================

ROOT = Path.cwd()

INPUT_FILE = (
    ROOT
    / "reports/generated/chronological_holdout_scores.csv"
)

OUTPUT_DIR = ROOT / "reports/generated"

STATION_SUMMARY_FILE = (
    OUTPUT_DIR / "holdout_drift_station_summary.csv"
)

DAILY_SUMMARY_FILE = (
    OUTPUT_DIR / "holdout_drift_daily_summary.csv"
)

FLAGGED_FILE = (
    OUTPUT_DIR / "holdout_drift_flagged_observations.csv"
)

REPORT_FILE = (
    OUTPUT_DIR / "holdout_drift_report.json"
)

FEATURE_COLUMNS = [
    "value",
    "deviation",
    "past_std",
    "hour_sin",
    "hour_cos",
]

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================
# LOAD DATA
# =====================================================

def load_data():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"File not found: {INPUT_FILE}\n"
            "Run chronological_holdout_test.py first."
        )

    df = pd.read_csv(INPUT_FILE)

    required = {
        "station",
        "timestamp",
        "split",
        "value",
        "anomaly_score",
        "is_anomaly",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
        errors="coerce",
    )

    for col in FEATURE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

    df["anomaly_score"] = pd.to_numeric(
        df["anomaly_score"],
        errors="coerce",
    )

    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce",
    )

    # CSV may represent missing nullable booleans as blank.
    df["is_anomaly"] = (
        df["is_anomaly"]
        .astype("string")
        .str.strip()
        .str.lower()
        .map({
            "true": True,
            "false": False,
            "1": True,
            "0": False,
        })
        .astype("boolean")
    )

    df = df.dropna(
        subset=["station", "timestamp", "split"]
    )

    df["date"] = df["timestamp"].dt.strftime(
        "%Y-%m-%d"
    )

    return df


# =====================================================
# STATION + SPLIT SUMMARY
# =====================================================

def build_station_summary(df):

    rows = []

    scored = df.dropna(
        subset=["is_anomaly", "anomaly_score"]
    ).copy()

    for (split, station), group in scored.groupby(
        ["split", "station"],
        sort=True,
    ):

        flagged = group[
            group["is_anomaly"].astype(bool)
        ]

        row = {
            "split": split,
            "station": station,
            "scored_rows": int(len(group)),
            "flagged_rows": int(len(flagged)),
            "flag_rate_percent": round(
                100 * len(flagged) / len(group),
                3,
            ) if len(group) else None,
            "pm25_mean": round(
                float(group["value"].mean()),
                3,
            ),
            "pm25_median": round(
                float(group["value"].median()),
                3,
            ),
            "pm25_p90": round(
                float(group["value"].quantile(0.90)),
                3,
            ),
            "pm25_max": round(
                float(group["value"].max()),
                3,
            ),
            "score_mean": round(
                float(group["anomaly_score"].mean()),
                6,
            ),
            "score_median": round(
                float(group["anomaly_score"].median()),
                6,
            ),
            "score_p90": round(
                float(group["anomaly_score"].quantile(0.90)),
                6,
            ),
        }

        # Compare model input feature distributions.
        for feature in FEATURE_COLUMNS:

            if feature not in group.columns:
                continue

            values = group[feature].dropna()

            row[f"{feature}_mean"] = (
                round(float(values.mean()), 6)
                if len(values) else None
            )

            row[f"{feature}_median"] = (
                round(float(values.median()), 6)
                if len(values) else None
            )

        rows.append(row)

    return pd.DataFrame(rows)


# =====================================================
# DAILY SUMMARY
# =====================================================

def build_daily_summary(df):

    scored = df.dropna(
        subset=["is_anomaly", "anomaly_score"]
    ).copy()

    daily = (
        scored.groupby(
            ["split", "station", "date"],
            sort=True,
        )
        .agg(
            observations=("value", "size"),
            flagged_observations=(
                "is_anomaly",
                lambda s: int(s.astype(bool).sum()),
            ),
            pm25_mean=("value", "mean"),
            pm25_max=("value", "max"),
            anomaly_score_mean=("anomaly_score", "mean"),
            anomaly_score_min=("anomaly_score", "min"),
        )
        .reset_index()
    )

    daily["flag_rate_percent"] = (
        100
        * daily["flagged_observations"]
        / daily["observations"]
    )

    numeric_cols = [
        "pm25_mean",
        "pm25_max",
        "anomaly_score_mean",
        "anomaly_score_min",
        "flag_rate_percent",
    ]

    daily[numeric_cols] = daily[numeric_cols].round(4)

    return daily


# =====================================================
# FLAGGED OBSERVATIONS
# =====================================================

def build_flagged_review(df):

    flagged = df[
        df["is_anomaly"].fillna(False)
    ].copy()

    available = [
        "station",
        "timestamp",
        "split",
        "value",
        "anomaly_score",
    ]

    for col in FEATURE_COLUMNS:
        if col in flagged.columns and col not in available:
            available.append(col)

    flagged = flagged[available].sort_values(
        ["split", "station", "timestamp"]
    )

    return flagged


# =====================================================
# MAIN
# =====================================================

def main():

    print("=" * 72)
    print("AIR KAVACH — HOLDOUT DRIFT DIAGNOSTIC")
    print("=" * 72)

    df = load_data()

    print(f"\nInput rows: {len(df)}")

    print("\nRows by split:")
    print(
        df.groupby("split")
        .size()
        .to_string()
    )

    print("\nStation availability by split:")

    print(
        df.groupby(["split", "station"])
        .size()
        .to_string()
    )

    station_summary = build_station_summary(df)

    daily_summary = build_daily_summary(df)

    flagged_review = build_flagged_review(df)

    station_summary.to_csv(
        STATION_SUMMARY_FILE,
        index=False,
    )

    daily_summary.to_csv(
        DAILY_SUMMARY_FILE,
        index=False,
    )

    flagged_review.to_csv(
        FLAGGED_FILE,
        index=False,
    )

    report = {
        "project": "AIR KAVACH",
        "analysis": "Chronological holdout distribution diagnostic",
        "input_rows": int(len(df)),
        "split_counts": {
            str(k): int(v)
            for k, v in df.groupby("split").size().items()
        },
        "station_availability": {
            str(split): {
                str(station): int(count)
                for station, count in group.items()
            }
            for split, group in (
                df.groupby("split")["station"]
                .value_counts()
                .groupby(level=0)
            )
        },
        "flagged_observation_count": int(
            len(flagged_review)
        ),
        "outputs": [
            str(STATION_SUMMARY_FILE.relative_to(ROOT)),
            str(DAILY_SUMMARY_FILE.relative_to(ROOT)),
            str(FLAGGED_FILE.relative_to(ROOT)),
        ],
        "limitations": [
            "No verified ground-truth labels were used.",
            "Flag rate is not accuracy, precision, or recall.",
            "Distribution differences suggest possible drift but do not prove its cause.",
            "Test-period results must not be used to tune the model.",
            "Airport has no validation/test observations in the current dataset.",
        ],
    }

    REPORT_FILE.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nSTATION + SPLIT SUMMARY:")
    print(station_summary.to_string(index=False))

    print("\nDAILY FLAG RATES:")
    print(
        daily_summary[
            [
                "split",
                "station",
                "date",
                "observations",
                "flagged_observations",
                "flag_rate_percent",
                "pm25_mean",
                "pm25_max",
            ]
        ].to_string(index=False)
    )

    print("\nFlagged observations exported:")
    print(len(flagged_review))

    print("\nSaved reports:")
    print(STATION_SUMMARY_FILE)
    print(DAILY_SUMMARY_FILE)
    print(FLAGGED_FILE)
    print(REPORT_FILE)

    print(
        "\nIMPORTANT: This diagnostic investigates distribution "
        "differences. It does not establish model accuracy."
    )


if __name__ == "__main__":

    try:
        main()

    except Exception as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)