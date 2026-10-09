from pathlib import Path

import pandas as pd


# ============================================================
# AIR KAVACH - EVIDENCE CHAIN ENGINE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "features"
    / "event_factory_confidence.parquet"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "features"
    / "event_evidence_chain.parquet"
)


# ============================================================
# CONFIGURATION
# ============================================================

# Number of candidates retained for the regulator-facing
# evidence chain for each pollution event.

TOP_CANDIDATES = 3


# ============================================================
# EVIDENCE HELPERS
# ============================================================

def wind_evidence_text(row):
    """
    Generate human-readable wind evidence.
    """

    relationship = row["wind_relationship"]

    if relationship == "strong_upwind":
        return (
            "Factory lies strongly upwind of the monitoring "
            "station during the pollution event."
        )

    if relationship == "upwind":
        return (
            "Factory lies upwind of the monitoring station "
            "during the pollution event."
        )

    if relationship == "crosswind":
        return (
            "Factory has a crosswind relationship with the "
            "monitoring station."
        )

    if relationship == "downwind":
        return (
            "Factory is downwind of the monitoring station "
            "under the observed wind direction."
        )

    if relationship == "strong_downwind":
        return (
            "Factory is strongly downwind of the monitoring "
            "station under the observed wind direction."
        )

    return (
        "Wind relationship could not be determined."
    )


def distance_evidence_text(distance):

    if distance <= 2:
        return (
            f"Very close geographic distance "
            f"({distance:.2f} km)."
        )

    if distance <= 5:
        return (
            f"Moderate geographic distance "
            f"({distance:.2f} km)."
        )

    return (
        f"Longer geographic distance "
        f"({distance:.2f} km)."
    )


def confidence_evidence_text(row):

    level = row["confidence_level"]
    confidence = row["confidence_percent"]

    if level == "high":
        return (
            f"Evidence confidence is high "
            f"({confidence:.1f}%)."
        )

    if level == "moderate":
        return (
            f"Evidence confidence is moderate "
            f"({confidence:.1f}%)."
        )

    return (
        f"Evidence confidence is low "
        f"({confidence:.1f}%)."
    )


def uncertainty_evidence_text(row):

    level = row["uncertainty_level"]
    uncertainty = row["uncertainty_percent"]

    if level == "low":
        return (
            f"Estimated uncertainty is low "
            f"({uncertainty:.1f}%)."
        )

    if level == "moderate":
        return (
            f"Estimated uncertainty is moderate "
            f"({uncertainty:.1f}%)."
        )

    return (
        f"Estimated uncertainty is high "
        f"({uncertainty:.1f}%)."
    )


def wind_quality_text(row):

    quality = row["wind_evidence_quality"]

    if quality == "good":
        return (
            "Wind evidence quality is good."
        )

    if quality == "limited":
        return (
            "Wind evidence is available but limited."
        )

    return (
        "Wind evidence quality is weak."
    )


# ============================================================
# MAIN EVIDENCE EXPLANATION
# ============================================================

def build_evidence_explanation(row):

    evidence_points = []

    # --------------------------------------------------------
    # Pollution event
    # --------------------------------------------------------

    evidence_points.append(
        f"Pollution event detected at "
        f"{row['station']} with peak PM2.5 "
        f"of {row['peak_pm25']:.2f}."
    )

    # --------------------------------------------------------
    # Geographic evidence
    # --------------------------------------------------------

    evidence_points.append(
        distance_evidence_text(
            row["distance_km"]
        )
    )

    # --------------------------------------------------------
    # Wind evidence
    # --------------------------------------------------------

    evidence_points.append(
        wind_evidence_text(row)
    )

    # --------------------------------------------------------
    # Wind quality
    # --------------------------------------------------------

    evidence_points.append(
        wind_quality_text(row)
    )

    # --------------------------------------------------------
    # Attribution
    # --------------------------------------------------------

    evidence_points.append(
        f"Relative attribution score is "
        f"{row['attribution_score']:.3f}."
    )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    evidence_points.append(
        confidence_evidence_text(row)
    )

    # --------------------------------------------------------
    # Uncertainty
    # --------------------------------------------------------

    evidence_points.append(
        uncertainty_evidence_text(row)
    )

    # --------------------------------------------------------
    # Candidate ambiguity
    # --------------------------------------------------------

    if row["separation_score"] < 0.20:

        evidence_points.append(
            "The top candidates have similar scores, "
            "which increases attribution ambiguity."
        )

    # --------------------------------------------------------
    # Wind speed limitation
    # --------------------------------------------------------

    if not row["wind_speed_available"]:

        evidence_points.append(
            "Wind speed data was unavailable for this event."
        )

    elif (
        not pd.isna(
            row["wind_speed_mean_mps"]
        )
        and
        row["wind_speed_mean_mps"] < 0.10
    ):

        evidence_points.append(
            "Observed wind speed was very low, "
            "which increases transport uncertainty."
        )

    # --------------------------------------------------------
    # Scientific limitation
    # --------------------------------------------------------

    evidence_points.append(
        "This result is a source-screening and "
        "investigation signal, not proof of legal or "
        "operational responsibility."
    )

    return " ".join(
        evidence_points
    )


# ============================================================
# RECOMMENDATION
# ============================================================

def build_recommendation(row):

    if row["investigation_status"] == (
        "high_confidence_candidate"
    ):

        return (
            "Prioritize this facility for further "
            "investigation and atmospheric modelling."
        )

    if row["investigation_status"] == (
        "moderate_confidence_candidate"
    ):

        return (
            "Consider this facility as a priority "
            "investigation candidate; validate with "
            "additional meteorology or dispersion modelling."
        )

    if row["investigation_status"] == (
        "low_confidence_candidate"
    ):

        return (
            "Treat this facility as a weak candidate "
            "and seek additional evidence."
        )

    if row["investigation_status"] == (
        "no_reliable_source"
    ):

        return (
            "Do not assign a reliable industrial source "
            "from the available evidence."
        )

    return (
        "Retain as a supporting candidate for further analysis."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print(
        "AIR KAVACH - EVIDENCE CHAIN ENGINE"
    )
    print("=" * 70)

    # ========================================================
    # 1. LOAD CONFIDENCE RESULTS
    # ========================================================

    print(
        "\n[1/6] Loading confidence results..."
    )

    df = pd.read_parquet(
        INPUT_FILE
    )

    print(
        f"Rows loaded: {len(df)}"
    )

    # ========================================================
    # 2. VALIDATE INPUT
    # ========================================================

    print(
        "\n[2/6] Validating input schema..."
    )

    required_columns = [
        "event_id",
        "station",

        "factory_id",
        "factory_name",

        "peak_pm25",

        "factory_rank",

        "attribution_score",
        "relative_likelihood",

        "distance_km",

        "wind_direction_mean_deg",
        "wind_speed_mean_mps",
        "wind_coverage",

        "wind_speed_available",

        "wind_relationship",
        "wind_evidence_quality",

        "separation_score",

        "confidence_score",
        "confidence_percent",
        "confidence_level",

        "uncertainty_score",
        "uncertainty_percent",
        "uncertainty_level",

        "source_identification_status",
        "investigation_status",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            f"Missing columns: {missing}"
        )

    print(
        "Input schema OK."
    )

    # ========================================================
    # 3. SELECT TOP CANDIDATES
    # ========================================================

    print(
        "\n[3/6] Selecting top evidence candidates..."
    )

    evidence = (
        df[
            df["factory_rank"]
            <= TOP_CANDIDATES
        ]
        .copy()
    )

    evidence = evidence.sort_values(
        [
            "event_id",
            "factory_rank"
        ]
    )

    print(
        f"Evidence rows retained: "
        f"{len(evidence)}"
    )

    # ========================================================
    # 4. BUILD EVIDENCE CHAIN
    # ========================================================

    print(
        "\n[4/6] Building evidence chains..."
    )

    evidence[
        "wind_evidence"
    ] = evidence.apply(
        wind_evidence_text,
        axis=1
    )

    evidence[
        "distance_evidence"
    ] = evidence[
        "distance_km"
    ].apply(
        distance_evidence_text
    )

    evidence[
        "confidence_evidence"
    ] = evidence.apply(
        confidence_evidence_text,
        axis=1
    )

    evidence[
        "uncertainty_evidence"
    ] = evidence.apply(
        uncertainty_evidence_text,
        axis=1
    )

    evidence[
        "overall_evidence_explanation"
    ] = evidence.apply(
        build_evidence_explanation,
        axis=1
    )

    evidence[
        "recommended_action"
    ] = evidence.apply(
        build_recommendation,
        axis=1
    )

    # ========================================================
    # EVENT-LEVEL STATUS
    # ========================================================

    top_candidates = (
        evidence[
            evidence["factory_rank"] == 1
        ]
        .copy()
    )

    # --------------------------------------------------------
    # Event source status
    # --------------------------------------------------------

    def event_status(row):

        return row[
            "investigation_status"
        ]

    top_candidates[
        "event_investigation_status"
    ] = top_candidates.apply(
        event_status,
        axis=1
    )

    event_status_map = dict(
        zip(
            top_candidates[
                "event_id"
            ],
            top_candidates[
                "event_investigation_status"
            ]
        )
    )

    evidence[
        "event_investigation_status"
    ] = evidence[
        "event_id"
    ].map(
        event_status_map
    )

    # ========================================================
    # 5. PREPARE OUTPUT
    # ========================================================

    print(
        "\n[5/6] Preparing evidence output..."
    )

    output_columns = [
        "event_id",
        "station",

        "factory_rank",

        "factory_id",
        "factory_name",

        "peak_pm25",

        "distance_km",
        "distance_evidence",

        "wind_direction_mean_deg",
        "wind_speed_mean_mps",
        "wind_coverage",

        "wind_relationship",
        "wind_evidence",
        "wind_evidence_quality",

        "attribution_score",
        "relative_likelihood",

        "confidence_score",
        "confidence_percent",
        "confidence_level",
        "confidence_evidence",

        "uncertainty_score",
        "uncertainty_percent",
        "uncertainty_level",
        "uncertainty_evidence",

        "separation_score",

        "source_identification_status",
        "investigation_status",

        "event_investigation_status",

        "overall_evidence_explanation",

        "recommended_action",
    ]

    result = evidence[
        output_columns
    ].copy()

    # ========================================================
    # SAVE
    # ========================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_parquet(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # 6. DISPLAY SUMMARY
    # ========================================================

    print(
        "\n[6/6] Evidence chain completed."
    )

    print(
        "\n" + "-" * 70
    )

    print(
        "TOP INVESTIGATION CANDIDATES"
    )

    print(
        "-" * 70
    )

    top = (
        result[
            result["factory_rank"] == 1
        ]
        .sort_values(
            "confidence_score",
            ascending=False
        )
        .head(15)
    )

    display_columns = [
        "event_id",
        "station",
        "factory_name",
        "attribution_score",
        "confidence_percent",
        "confidence_level",
        "uncertainty_level",
        "investigation_status",
    ]

    print(
        top[
            display_columns
        ].to_string(
            index=False
        )
    )

    # ========================================================
    # EXAMPLE EVIDENCE CHAIN
    # ========================================================

    if not top.empty:

        example = top.iloc[0]

        print(
            "\n" + "-" * 70
        )

        print(
            "EXAMPLE EVIDENCE CHAIN"
        )

        print(
            "-" * 70
        )

        print(
            f"Event: "
            f"{example['event_id']}"
        )

        print(
            f"Sensor: "
            f"{example['station']}"
        )

        print(
            f"Candidate: "
            f"{example['factory_name']}"
        )

        print(
            f"Distance: "
            f"{example['distance_km']:.2f} km"
        )

        print(
            f"Wind relationship: "
            f"{example['wind_relationship']}"
        )

        print(
            f"Attribution score: "
            f"{example['attribution_score']:.3f}"
        )

        print(
            f"Confidence: "
            f"{example['confidence_percent']:.1f}%"
        )

        print(
            f"Uncertainty: "
            f"{example['uncertainty_percent']:.1f}%"
        )

        print(
            f"Status: "
            f"{example['investigation_status']}"
        )

        print(
            "\nExplanation:"
        )

        print(
            example[
                "overall_evidence_explanation"
            ]
        )

        print(
            "\nRecommended action:"
        )

        print(
            example[
                "recommended_action"
            ]
        )

    # ========================================================
    # OUTPUT
    # ========================================================

    print(
        "\nOutput:"
    )

    print(
        OUTPUT_FILE
    )

    print(
        "\nAIR KAVACH evidence chain is ready."
    )

    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()