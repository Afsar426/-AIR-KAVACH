from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# AIR KAVACH - ATTRIBUTION BASELINE ANALYSIS
# ============================================================

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


def main():

    print("=" * 72)
    print("AIR KAVACH - ATTRIBUTION BASELINE ANALYSIS")
    print("=" * 72)

    # --------------------------------------------------------
    # 1. Load dataset
    # --------------------------------------------------------

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {INPUT_FILE}"
        )

    df = pd.read_parquet(INPUT_FILE)

    print("\n[1/6] Dataset loaded")

    print("Rows:", len(df))
    print("Events:", df["event_id"].nunique())
    print("Factories:", df["factory_id"].nunique())

    # --------------------------------------------------------
    # 2. Separate raw evidence from derived scores
    # --------------------------------------------------------

    print("\n[2/6] Feature groups")

    raw_evidence_features = [
        "distance_km",
        "peak_pm25",
        "peak_z_score",
        "event_duration_minutes",
        "wind_direction_mean_deg",
        "wind_speed_mean_mps",
        "wind_coverage",
        "wind_alignment",
        "facility_category",
    ]

    heuristic_output_features = [
        "attribution_score",
        "relative_likelihood",
        "confidence_percent",
        "uncertainty_percent",
    ]

    raw_available = [
        col
        for col in raw_evidence_features
        if col in df.columns
    ]

    derived_available = [
        col
        for col in heuristic_output_features
        if col in df.columns
    ]

    print("\nRaw evidence features:")

    for col in raw_available:
        print(" -", col)

    print("\nDerived heuristic outputs:")

    for col in derived_available:
        print(" -", col)

    print(
        "\nNote: Derived outputs should not be used as "
        "inputs when attempting to independently predict "
        "the same heuristic output."
    )

    # --------------------------------------------------------
    # 3. Event-level ranking diagnostics
    # --------------------------------------------------------

    print("\n[3/6] Candidate ranking diagnostics")

    required = [
        "event_id",
        "station",
        "factory_id",
        "factory_name",
        "attribution_score",
        "distance_km",
        "wind_alignment",
    ]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns: {missing}"
        )

    ranked = df.copy()

    ranked = ranked.sort_values(
        [
            "event_id",
            "attribution_score",
        ],
        ascending=[True, False]
    )

    ranked["score_rank"] = (
        ranked.groupby("event_id")
        ["attribution_score"]
        .rank(
            method="first",
            ascending=False
        )
        .astype(int)
    )

    event_rows = []

    for event_id, group in ranked.groupby("event_id"):

        group = group.sort_values(
            "attribution_score",
            ascending=False
        )

        top = group.iloc[0]

        second_score = (
            group.iloc[1]["attribution_score"]
            if len(group) > 1
            else np.nan
        )

        top_score = float(
            top["attribution_score"]
        )

        if pd.notna(second_score):

            score_gap = (
                top_score - float(second_score)
            )

        else:
            score_gap = np.nan

        event_rows.append({

            "event_id": event_id,

            "station": top["station"],

            "candidate_count": len(group),

            "top_factory_id": top["factory_id"],

            "top_factory_name": top["factory_name"],

            "top_attribution_score": top_score,

            "second_attribution_score": second_score,

            "top_two_score_gap": score_gap,

            "top_distance_km": top["distance_km"],

            "top_wind_alignment": top["wind_alignment"],

            "top_candidate_is_unique":
                bool(
                    pd.notna(score_gap)
                    and score_gap > 0
                ),

        })

    event_summary = pd.DataFrame(
        event_rows
    )

    event_summary.to_csv(
        OUTPUT_DIR
        / "attribution_event_baseline.csv",
        index=False
    )

    print(
        "Event summaries:",
        len(event_summary)
    )

    print(
        "\nTop candidate examples:"
    )

    print(
        event_summary[
            [
                "event_id",
                "station",
                "top_factory_name",
                "top_attribution_score",
                "top_two_score_gap",
            ]
        ].head(10).to_string(index=False)
    )

    # --------------------------------------------------------
    # 4. Candidate score distribution
    # --------------------------------------------------------

    print("\n[4/6] Attribution score distribution")

    print(
        df["attribution_score"]
        .describe()
        .round(4)
        .to_string()
    )

    score_stats = (
        df.groupby("station")
        ["attribution_score"]
        .agg(
            ["count", "mean", "median", "min", "max"]
        )
        .round(4)
    )

    print(
        "\nScore distribution by station:"
    )

    print(
        score_stats.to_string()
    )

    score_stats.to_csv(
        OUTPUT_DIR
        / "attribution_score_by_station.csv"
    )

    # --------------------------------------------------------
    # 5. Wind quality analysis
    # --------------------------------------------------------

    print("\n[5/6] Wind quality analysis")

    wind_summary = (
        df.groupby("station")
        .agg(
            candidate_rows=("factory_id", "size"),

            missing_wind_speed=(
                "wind_speed_mean_mps",
                lambda values: int(
                    values.isna().sum()
                )
            ),

            mean_wind_speed=(
                "wind_speed_mean_mps",
                "mean"
            ),

            mean_wind_coverage=(
                "wind_coverage",
                "mean"
            ),
        )
        .reset_index()
    )

    wind_summary["missing_wind_speed_percent"] = (
        wind_summary["missing_wind_speed"]
        / wind_summary["candidate_rows"]
        * 100
    ).round(2)

    print(
        wind_summary.round(3).to_string(index=False)
    )

    wind_summary.to_csv(
        OUTPUT_DIR
        / "attribution_wind_quality.csv",
        index=False
    )

    # --------------------------------------------------------
    # 6. Training readiness assessment
    # --------------------------------------------------------

    print("\n[6/6] ML training readiness")

    verified_label_count = (
        int(
            df["source_label"].notna().sum()
        )
        if "source_label" in df.columns
        else 0
    )

    print(
        "Verified source labels:",
        verified_label_count
    )

    if verified_label_count == 0:

        print(
            "\nSTATUS: NOT READY FOR SUPERVISED "
            "SOURCE CLASSIFICATION."
        )

        print(
            "Recommended next action: establish a "
            "defensible label strategy or obtain "
            "independent reference data."
        )

    print(
        "\nImportant: Top-ranked candidates are "
        "heuristic rankings, not verified source "
        "identifications."
    )

    print(
        "\nReports saved to:",
        OUTPUT_DIR
    )

    print(
        "\nAIR KAVACH BASELINE ANALYSIS COMPLETE"
    )


if __name__ == "__main__":
    main()