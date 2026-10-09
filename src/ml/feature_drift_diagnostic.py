from pathlib import Path
import json

import numpy as np
import pandas as pd


# ============================================================
# AIR KAVACH — FEATURE DRIFT DIAGNOSTIC
# Compare training, validation and test feature distributions.
# This does not measure model accuracy.
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT
    / "reports"
    / "generated"
    / "chronological_holdout_scores.csv"
)

OUTPUT_DIR = ROOT / "reports" / "generated"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_REPORT = (
    OUTPUT_DIR / "feature_drift_station_report.csv"
)

DRIFT_REPORT = (
    OUTPUT_DIR / "feature_drift_comparison.csv"
)

JSON_REPORT = (
    OUTPUT_DIR / "feature_drift_report.json"
)

FEATURES = [
    "value",
    "past_mean",
    "past_std",
    "deviation",
    "hour_sin",
    "hour_cos",
    "anomaly_score",
]


def main():
    print("=" * 72)
    print("AIR KAVACH — FEATURE DRIFT DIAGNOSTIC")
    print("=" * 72)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Required input file not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required = {"station", "split", "timestamp"}

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    available_features = [
        feature
        for feature in FEATURES
        if feature in df.columns
    ]

    if not available_features:
        raise ValueError(
            "No expected feature columns found."
        )

    df["station"] = (
        df["station"].astype(str).str.strip()
    )

    df["split"] = (
        df["split"].astype(str).str.strip().str.lower()
    )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True,
    )

    for feature in available_features:
        df[feature] = pd.to_numeric(
            df[feature],
            errors="coerce",
        )

    print(f"\nInput rows: {len(df)}")
    print(f"Available features: {available_features}")

    print("\nRows by split:")
    print(df["split"].value_counts().to_string())

    station_rows = []
    comparison_rows = []

    splits = ["train", "validation", "test"]

    # --------------------------------------------------------
    # 1. Per-station feature summaries
    # --------------------------------------------------------

    for station in sorted(df["station"].dropna().unique()):

        station_data = df[
            df["station"] == station
        ]

        for feature in available_features:

            for split in splits:

                values = station_data.loc[
                    station_data["split"] == split,
                    feature,
                ].dropna()

                if values.empty:
                    continue

                station_rows.append({
                    "station": station,
                    "feature": feature,
                    "split": split,
                    "count": int(len(values)),
                    "mean": float(values.mean()),
                    "std": float(values.std()),
                    "median": float(values.median()),
                    "p10": float(values.quantile(0.10)),
                    "p90": float(values.quantile(0.90)),
                    "minimum": float(values.min()),
                    "maximum": float(values.max()),
                })

            # ------------------------------------------------
            # 2. Compare each later split with training.
            # ------------------------------------------------

            train_values = station_data.loc[
                station_data["split"] == "train",
                feature,
            ].dropna()

            if len(train_values) < 2:
                continue

            train_mean = float(train_values.mean())
            train_std = float(train_values.std())

            train_p01 = float(
                train_values.quantile(0.01)
            )

            train_p99 = float(
                train_values.quantile(0.99)
            )

            train_median = float(
                train_values.median()
            )

            train_iqr = float(
                train_values.quantile(0.75)
                - train_values.quantile(0.25)
            )

            for split in ["validation", "test"]:

                current = station_data.loc[
                    station_data["split"] == split,
                    feature,
                ].dropna()

                if current.empty:
                    continue

                current_mean = float(current.mean())
                current_std = float(current.std())

                # Standardized mean difference.
                # A zero/near-zero denominator is handled safely.
                pooled_std = np.sqrt(
                    (
                        train_std ** 2
                        + current_std ** 2
                    ) / 2
                )

                if pooled_std > 1e-12:
                    standardized_difference = (
                        current_mean - train_mean
                    ) / pooled_std
                else:
                    standardized_difference = np.nan

                outside_reference = (
                    (current < train_p01)
                    | (current > train_p99)
                )

                comparison_rows.append({
                    "station": station,
                    "feature": feature,
                    "comparison": f"train_vs_{split}",
                    "train_count": int(len(train_values)),
                    "comparison_count": int(len(current)),
                    "train_mean": train_mean,
                    "comparison_mean": current_mean,
                    "mean_difference": (
                        current_mean - train_mean
                    ),
                    "train_median": train_median,
                    "comparison_median": float(
                        current.median()
                    ),
                    "train_std": train_std,
                    "comparison_std": current_std,
                    "train_iqr": train_iqr,
                    "comparison_iqr": float(
                        current.quantile(0.75)
                        - current.quantile(0.25)
                    ),
                    "standardized_mean_difference": (
                        standardized_difference
                    ),
                    "outside_train_1_99_percent": float(
                        outside_reference.mean() * 100
                    ),
                    "train_p01": train_p01,
                    "train_p99": train_p99,
                    "comparison_p90": float(
                        current.quantile(0.90)
                    ),
                })

    station_report = pd.DataFrame(station_rows)

    comparison_report = pd.DataFrame(
        comparison_rows
    )

    # --------------------------------------------------------
    # 3. Missing feature coverage by split.
    # --------------------------------------------------------

    coverage_rows = []

    for (station, split), group in df.groupby(
        ["station", "split"]
    ):

        for feature in available_features:

            total = len(group)
            valid_count = int(
                group[feature].notna().sum()
            )

            coverage_rows.append({
                "station": station,
                "split": split,
                "feature": feature,
                "total_rows": int(total),
                "valid_rows": valid_count,
                "missing_rows": int(total - valid_count),
                "missing_percent": (
                    (total - valid_count) / total * 100
                    if total else np.nan
                ),
            })

    coverage_report = pd.DataFrame(coverage_rows)

    # --------------------------------------------------------
    # 4. Save reports.
    # --------------------------------------------------------

    station_report.to_csv(
        FEATURE_REPORT,
        index=False,
    )

    comparison_report.to_csv(
        DRIFT_REPORT,
        index=False,
    )

    coverage_report.to_csv(
        OUTPUT_DIR / "feature_drift_coverage.csv",
        index=False,
    )

    summary = {
        "input_rows": int(len(df)),
        "stations": sorted(
            df["station"].dropna().unique().tolist()
        ),
        "available_features": available_features,
        "rows_by_split": {
            str(k): int(v)
            for k, v in df["split"].value_counts().items()
        },
        "comparison_rows": int(
            len(comparison_report)
        ),
        "interpretation": (
            "Feature distribution comparison only. "
            "Distribution differences do not prove their cause "
            "and do not establish model accuracy or pollution-source causation."
        ),
        "reports": {
            "station_summary": str(FEATURE_REPORT),
            "train_future_comparison": str(DRIFT_REPORT),
            "feature_coverage": str(
                OUTPUT_DIR / "feature_drift_coverage.csv"
            ),
        },
    }

    with open(
        JSON_REPORT,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(summary, file, indent=2)

    # --------------------------------------------------------
    # 5. Print key results.
    # --------------------------------------------------------

    print("\nFEATURE DRIFT COMPARISON:")

    if not comparison_report.empty:

        display_columns = [
            "station",
            "feature",
            "comparison",
            "train_mean",
            "comparison_mean",
            "standardized_mean_difference",
            "outside_train_1_99_percent",
        ]

        print(
            comparison_report[display_columns]
            .round(4)
            .to_string(index=False)
        )

    print("\nFEATURE COVERAGE:")
    print(
        coverage_report[
            [
                "station",
                "split",
                "feature",
                "missing_rows",
                "missing_percent",
            ]
        ]
        .round(2)
        .to_string(index=False)
    )

    print("\nSaved reports:")
    print(FEATURE_REPORT)
    print(DRIFT_REPORT)
    print(OUTPUT_DIR / "feature_drift_coverage.csv")
    print(JSON_REPORT)

    print("\nIMPORTANT:")
    print(
        "This report detects distribution differences, "
        "not verified environmental change or model accuracy."
    )


if __name__ == "__main__":
    main()