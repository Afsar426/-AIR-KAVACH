from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# AIR KAVACH - CONSERVATIVE CONFIDENCE & UNCERTAINTY ENGINE
# ============================================================
# These scores describe evidence completeness/consistency within a
# heuristic screening pipeline. They are NOT calibrated probabilities
# and do NOT establish that a factory caused a pollution event.
# No verified source labels are currently available for calibration.
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE_DIR / "data" / "features" / "event_factory_attribution.parquet"
OUTPUT_FILE = BASE_DIR / "data" / "features" / "event_factory_confidence.parquet"

# Deliberately conservative ceiling until validated against verified labels.
MAX_CONFIDENCE = 0.75


def confidence_label(score):
    """Conservative evidence-strength label, not causal probability."""
    if score >= 0.65:
        return "stronger_screening_evidence"
    if score >= 0.40:
        return "moderate_screening_evidence"
    return "limited_screening_evidence"


def uncertainty_label(score):
    if score <= 0.35:
        return "lower_relative_uncertainty"
    if score <= 0.60:
        return "moderate_relative_uncertainty"
    return "higher_relative_uncertainty"


def calculate_wind_reliability(row):
    """
    Score the availability/quality of wind observations.
    Missing wind speed is penalized; very low speed reduces confidence
    in directional transport interpretation.
    """
    direction = row["wind_direction_mean_deg"]
    speed = row["wind_speed_mean_mps"]
    coverage = row["wind_coverage"]

    if pd.isna(direction):
        return 0.0

    coverage_score = float(np.clip(
        0.0 if pd.isna(coverage) else coverage, 0.0, 1.0
    ))

    if pd.isna(speed):
        speed_score = 0.0
    elif speed < 0.05:
        speed_score = 0.20
    elif speed < 0.10:
        speed_score = 0.35
    elif speed < 0.20:
        speed_score = 0.60
    else:
        speed_score = 1.0

    return float(0.60 * coverage_score + 0.40 * speed_score)


def calculate_spatial_compatibility(row):
    distance_score = row["distance_score"]
    alignment = row["positive_wind_alignment"]

    distance_score = 0.0 if pd.isna(distance_score) else float(
        np.clip(distance_score, 0.0, 1.0)
    )
    alignment = 0.0 if pd.isna(alignment) else float(
        np.clip(alignment, 0.0, 1.0)
    )

    # Same broad evidence components as the screening score, but this
    # metric is reported separately and must not be interpreted as probability.
    return 0.40 * distance_score + 0.60 * alignment


def main():
    print("=" * 70)
    print("AIR KAVACH - CONSERVATIVE CONFIDENCE & UNCERTAINTY ENGINE")
    print("=" * 70)

    print("\n[1/7] Loading attribution results...")
    df = pd.read_parquet(INPUT_FILE)
    print(f"Rows loaded: {len(df)}")

    required_columns = [
        "event_id", "station", "factory_id", "factory_name",
        "peak_pm25", "factory_rank", "attribution_score",
        "relative_likelihood", "distance_km", "distance_score",
        "wind_direction_mean_deg", "wind_speed_mean_mps",
        "wind_coverage", "positive_wind_alignment",
        "wind_relationship", "wind_evidence_quality",
        "source_identification_status",
    ]
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in attribution data: {missing}")

    if df.empty:
        raise ValueError("Attribution input is empty.")

    print("\n[2/7] Validating event rankings...")
    duplicate_pairs = df.duplicated(["event_id", "factory_id"]).sum()
    if duplicate_pairs:
        raise ValueError(
            f"Found {duplicate_pairs} duplicate event-factory pairs; "
            "resolve duplicates before calculating confidence."
        )

    # Recompute ranking to ensure confidence uses the current score order.
    df = df.sort_values(
        ["event_id", "attribution_score", "distance_km"],
        ascending=[True, False, True],
        kind="mergesort",
    ).copy()
    df["factory_rank"] = df.groupby("event_id").cumcount() + 1

    print("\n[3/7] Measuring top-candidate separation...")
    grouped = df.groupby("event_id")["attribution_score"]
    df["second_best_score"] = grouped.shift(-1)

    # For the top-ranked candidate, compare its score with the event's
    # second-ranked candidate. For other candidates this remains a diagnostic.
    df["score_gap"] = (
        df["attribution_score"] - df["second_best_score"]
    ).fillna(0.0).clip(lower=0.0)

    df["separation_score"] = np.where(
        df["factory_rank"] == 1,
        np.where(
            df["attribution_score"] > 0,
            (df["score_gap"] / df["attribution_score"]).clip(0.0, 1.0),
            0.0,
        ),
        0.0,
    )

    print("\n[4/7] Evaluating wind and spatial evidence...")
    df["wind_direction_available"] = df["wind_direction_mean_deg"].notna()
    df["wind_speed_available"] = df["wind_speed_mean_mps"].notna()

    df["wind_reliability_score"] = df.apply(calculate_wind_reliability, axis=1)
    df["spatial_compatibility_score"] = df.apply(
        calculate_spatial_compatibility, axis=1
    )

    print("\n[5/7] Calculating conservative evidence scores...")
    # A confidence-like evidence index, NOT a probability of causation.
    df["raw_confidence"] = (
        0.40 * df["spatial_compatibility_score"]
        + 0.30 * df["wind_reliability_score"]
        + 0.30 * df["separation_score"]
    )

    df["confidence_score"] = df["raw_confidence"].clip(
        lower=0.0, upper=MAX_CONFIDENCE
    )

    # Explicitly penalize the leading candidate if the event has no usable
    # wind direction or no wind-speed measurement.
    event_direction_available = df.groupby("event_id")[
        "wind_direction_available"
    ].transform("any")
    event_speed_available = df.groupby("event_id")[
        "wind_speed_available"
    ].transform("any")

    df["wind_evidence_limitation"] = np.select(
        [
            ~event_direction_available,
            ~event_speed_available,
        ],
        [
            "wind_direction_unavailable",
            "wind_speed_unavailable",
        ],
        default="wind_direction_and_speed_available",
    )

    # Additional conservative cap when wind speed is unavailable for the event.
    df.loc[~event_speed_available, "confidence_score"] = np.minimum(
        df.loc[~event_speed_available, "confidence_score"], 0.50
    )

    # If the attribution engine already says no reliable source, preserve that
    # status and do not present the top candidate as a reliable identification.
    df["confidence_percent"] = (df["confidence_score"] * 100).round(1)
    df["confidence_level"] = df["confidence_score"].apply(confidence_label)
    df["uncertainty_score"] = 1.0 - df["confidence_score"]
    df["uncertainty_percent"] = (df["uncertainty_score"] * 100).round(1)
    df["uncertainty_level"] = df["uncertainty_score"].apply(uncertainty_label)

    print("\n[6/7] Building explanations and investigation status...")
    def build_explanation(row):
        reasons = []

        if row["wind_relationship"] in ("strong_upwind", "upwind"):
            reasons.append(str(row["wind_relationship"]).replace("_", " "))
        elif row["wind_relationship"] == "unknown":
            reasons.append("wind direction unavailable")

        if pd.notna(row["distance_km"]):
            if row["distance_km"] <= 2:
                reasons.append("facility is within 2 km")
            elif row["distance_km"] <= 5:
                reasons.append("facility is within 5 km")
            else:
                reasons.append("facility is more than 5 km away")

        if row["wind_evidence_limitation"] == "wind_speed_unavailable":
            reasons.append("wind speed unavailable; transport evidence is limited")
        elif row["wind_evidence_limitation"] == "wind_direction_unavailable":
            reasons.append("wind direction unavailable")

        if row["factory_rank"] == 1 and row["separation_score"] < 0.10:
            reasons.append("top candidate is difficult to distinguish from runner-up")
        elif row["factory_rank"] == 1 and row["separation_score"] < 0.25:
            reasons.append("top candidate has only modest separation from runner-up")

        if not reasons:
            reasons.append("limited independent evidence for source attribution")

        return "; ".join(reasons)

    df["confidence_explanation"] = df.apply(build_explanation, axis=1)

    def investigation_status(row):
        if row["source_identification_status"] == "no_reliable_source":
            return "no_reliable_source"
        if row["factory_rank"] != 1:
            return "supporting_candidate"
        if row["wind_evidence_limitation"] != "wind_direction_and_speed_available":
            return "candidate_requires_meteorological_validation"
        if row["confidence_level"] == "stronger_screening_evidence":
            return "stronger_screening_candidate_not_confirmed"
        if row["confidence_level"] == "moderate_screening_evidence":
            return "moderate_screening_candidate"
        return "limited_evidence_candidate"

    df["investigation_status"] = df.apply(investigation_status, axis=1)

    output_columns = [
        "event_id", "station", "factory_id", "factory_name", "peak_pm25",
        "factory_rank", "attribution_score", "relative_likelihood",
        "distance_km", "distance_score",
        "wind_direction_mean_deg", "wind_speed_mean_mps", "wind_coverage",
        "wind_direction_available", "wind_speed_available",
        "positive_wind_alignment", "wind_relationship",
        "wind_reliability_score", "spatial_compatibility_score",
        "second_best_score", "score_gap", "separation_score",
        "confidence_score", "confidence_percent", "confidence_level",
        "uncertainty_score", "uncertainty_percent", "uncertainty_level",
        "wind_evidence_quality", "wind_evidence_limitation",
        "source_identification_status", "investigation_status",
        "confidence_explanation",
    ]
    result = df[output_columns].copy()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUTPUT_FILE, index=False)

    print("\n[7/7] Confidence analysis completed.")
    print("-" * 70)
    print(f"Events: {result['event_id'].nunique()}")
    print(f"Rows: {len(result)}")
    print("Top-ranked candidates by confidence/evidence score:")
    top = result[result["factory_rank"] == 1].sort_values(
        "confidence_score", ascending=False
    ).head(15)
    display_columns = [
        "event_id", "station", "factory_name", "attribution_score",
        "confidence_percent", "confidence_level", "uncertainty_percent",
        "wind_evidence_limitation", "investigation_status",
    ]
    print(top[display_columns].to_string(index=False))
    print("\nConfidence label distribution among top-ranked candidates:")
    print(top["confidence_level"].value_counts().to_dict())
    print(f"\nOutput: {OUTPUT_FILE}")
    print("\nIMPORTANT:")
    print("Evidence scores are heuristic screening indicators, not calibrated")
    print("probabilities that a facility caused pollution. No verified source")
    print("labels are available to validate or calibrate these scores.")
    print("Use atmospheric dispersion modelling and independent evidence")
    print("before drawing regulatory conclusions.")
    print("=" * 70)
    print("AIR KAVACH CONFIDENCE ENGINE READY")
    print("=" * 70)


class ConfidenceEngine:
    def run(self):
        return main()


if __name__ == "__main__":
    main()
