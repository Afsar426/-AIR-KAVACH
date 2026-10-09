from pathlib import Path
import numpy as np
import pandas as pd

# AIR KAVACH - transparent factory attribution screening heuristic.
# Scores are NOT calibrated probabilities and do NOT prove causation.

BASE_DIR = Path(__file__).resolve().parents[2]
EVENTS_FILE = BASE_DIR / "data" / "features" / "pollution_events_with_wind.parquet"
DISTANCE_FILE = BASE_DIR / "data" / "features" / "sensor_factory_distances.parquet"
OUTPUT_FILE = BASE_DIR / "data" / "features" / "event_factory_attribution.parquet"

DISTANCE_SCALE_KM = 5.0
WIND_WEIGHT = 0.70
DISTANCE_WEIGHT = 0.30
NO_RELIABLE_SOURCE_THRESHOLD = 0.35


def calculate_bearing(lat1, lon1, lat2, lon2):
    """Initial bearing from point 1 to point 2, clockwise from North."""
    lat1, lat2 = np.radians(lat1), np.radians(lat2)
    delta_lon = np.radians(lon2 - lon1)
    x = np.sin(delta_lon) * np.cos(lat2)
    y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(delta_lon)
    return (np.degrees(np.arctan2(x, y)) + 360) % 360


def circular_angle_difference(angle1, angle2):
    """Smallest angular difference, 0 to 180 degrees."""
    if pd.isna(angle1) or pd.isna(angle2):
        return np.nan
    return abs((angle1 - angle2 + 180) % 360 - 180)


def calculate_alignment(sensor_to_factory_bearing, wind_direction):
    """
    Meteorological wind direction is the direction wind comes FROM.
    Compare it with the bearing from sensor TO factory.
    +1 = factory directly upwind; 0 = crosswind; -1 = downwind.
    This is geometric screening, not dispersion modelling.
    """
    difference = circular_angle_difference(sensor_to_factory_bearing, wind_direction)
    if pd.isna(difference):
        return np.nan
    return float(np.cos(np.radians(difference)))


def calculate_distance_score(distance_km):
    """Heuristic distance decay; not an atmospheric concentration model."""
    if pd.isna(distance_km) or distance_km < 0:
        return 0.0
    return float(np.exp(-distance_km / DISTANCE_SCALE_KM))


def classify_alignment(score):
    if pd.isna(score):
        return "unknown"
    if score >= 0.75:
        return "strong_upwind"
    if score >= 0.25:
        return "upwind"
    if score > -0.25:
        return "crosswind"
    if score > -0.75:
        return "downwind"
    return "strong_downwind"


def classify_evidence(row):
    relationship, distance = row["wind_relationship"], row["distance_km"]
    if pd.isna(distance):
        return "incomplete_geospatial_evidence"
    if relationship in ("strong_upwind", "upwind") and distance <= 5:
        return "strong_geospatial_wind_evidence"
    if relationship in ("strong_upwind", "upwind"):
        return "upwind_evidence"
    if relationship == "unknown" and distance <= 5:
        return "nearby_wind_evidence_unavailable"
    if distance <= 5:
        return "nearby_but_wind_alignment_weak"
    return "weak_geospatial_evidence"


def main():
    print("=" * 70)
    print("AIR KAVACH - FACTORY ATTRIBUTION ENGINE")
    print("=" * 70)

    print("\n[1/7] Loading pollution events...")
    events = pd.read_parquet(EVENTS_FILE)
    print(f"Events loaded: {len(events)}")

    print("\n[2/7] Loading sensor-factory distances...")
    distances = pd.read_parquet(DISTANCE_FILE)
    print(f"Distance pairs loaded: {len(distances)}")

    print("\n[3/7] Validating input data...")
    required_event_columns = [
        "event_id", "station", "peak_pm25",
        "wind_direction_mean_deg", "wind_speed_mean_mps", "wind_coverage",
    ]
    required_distance_columns = [
        "sensor", "factory_id", "factory_name", "facility_category",
        "sensor_latitude", "sensor_longitude", "factory_latitude",
        "factory_longitude", "distance_km",
    ]
    missing_events = [c for c in required_event_columns if c not in events.columns]
    missing_distances = [c for c in required_distance_columns if c not in distances.columns]
    if missing_events:
        raise ValueError(f"Missing columns in event data: {missing_events}")
    if missing_distances:
        raise ValueError(f"Missing columns in distance data: {missing_distances}")
    if events["event_id"].isna().any():
        raise ValueError("Event data contains missing event_id values.")
    if distances[["sensor", "factory_id"]].isna().any().any():
        raise ValueError("Distance data contains missing sensor or factory_id values.")
    print("Input schemas OK.")

    print("\n[4/7] Creating event-factory candidates...")
    merged = events.merge(distances, left_on="station", right_on="sensor", how="inner")
    print(f"Candidate pairs created: {len(merged)}")
    if merged.empty:
        raise ValueError("No event-factory pairs created. Check station/sensor names.")

    print("\n[5/7] Calculating geographic and wind alignment...")
    merged["bearing_sensor_to_factory_deg"] = merged.apply(
        lambda r: calculate_bearing(
            r["sensor_latitude"], r["sensor_longitude"],
            r["factory_latitude"], r["factory_longitude"],
        ), axis=1,
    )
    # Retained for compatibility/display; not used for wind-FROM comparison.
    merged["bearing_factory_to_sensor_deg"] = (
        merged["bearing_sensor_to_factory_deg"] + 180
    ) % 360

    # Correct convention: sensor -> factory bearing compared to wind direction FROM.
    merged["wind_angle_difference_deg"] = merged.apply(
        lambda r: circular_angle_difference(
            r["bearing_sensor_to_factory_deg"], r["wind_direction_mean_deg"]
        ), axis=1,
    )
    merged["wind_alignment"] = merged.apply(
        lambda r: calculate_alignment(
            r["bearing_sensor_to_factory_deg"], r["wind_direction_mean_deg"]
        ), axis=1,
    )
    # Missing wind direction must not create NaN attribution scores.
    merged["positive_wind_alignment"] = merged["wind_alignment"].clip(lower=0).fillna(0.0)
    merged["distance_score"] = merged["distance_km"].apply(calculate_distance_score)
    merged["attribution_score"] = (
        WIND_WEIGHT * merged["positive_wind_alignment"]
        + DISTANCE_WEIGHT * merged["distance_score"]
    ).clip(lower=0.0, upper=1.0)

    merged["wind_direction_available"] = merged["wind_direction_mean_deg"].notna()
    merged["wind_speed_available"] = merged["wind_speed_mean_mps"].notna()
    coverage = pd.to_numeric(merged["wind_coverage"], errors="coerce").fillna(0.0)
    speed = pd.to_numeric(merged["wind_speed_mean_mps"], errors="coerce")
    good_wind = (
        merged["wind_direction_available"] & merged["wind_speed_available"]
        & (speed > 0.1) & (coverage >= 0.75)
    )
    limited_wind = merged["wind_direction_available"] & (coverage >= 0.75)
    merged["wind_evidence_quality"] = np.select(
        [good_wind, limited_wind], ["good", "limited"], default="weak"
    )
    merged["wind_relationship"] = merged["wind_alignment"].apply(classify_alignment)

    print("\n[6/7] Ranking factory candidates...")
    merged = merged.sort_values(
        ["event_id", "attribution_score", "distance_km"],
        ascending=[True, False, True], kind="mergesort",
    ).copy()
    merged["factory_rank"] = merged.groupby("event_id").cumcount() + 1
    merged["top_event_score"] = merged.groupby("event_id")["attribution_score"].transform("max")
    event_has_wind = merged.groupby("event_id")["wind_direction_mean_deg"].transform(
        lambda s: s.notna().any()
    )
    merged["source_identification_status"] = np.where(
        (merged["top_event_score"] < NO_RELIABLE_SOURCE_THRESHOLD) | (~event_has_wind),
        "no_reliable_source", "candidate_source_found",
    )
    score_sum = merged.groupby("event_id")["attribution_score"].transform("sum")
    merged["relative_likelihood"] = np.where(
        score_sum > 0, merged["attribution_score"] / score_sum, 0.0
    )
    # Normalized heuristic score share, NOT probability of causation.
    merged["evidence_label"] = merged.apply(classify_evidence, axis=1)

    output_columns = [
        "event_id", "station", "factory_id", "factory_name", "facility_category",
        "peak_pm25", "distance_km", "distance_score",
        "wind_direction_mean_deg", "wind_speed_mean_mps", "wind_coverage",
        "bearing_sensor_to_factory_deg", "bearing_factory_to_sensor_deg",
        "wind_angle_difference_deg", "wind_alignment", "positive_wind_alignment",
        "wind_relationship", "wind_evidence_quality", "attribution_score",
        "relative_likelihood", "factory_rank", "top_event_score",
        "source_identification_status", "evidence_label",
    ]
    result = merged[output_columns].copy()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUTPUT_FILE, index=False)

    print("\n[7/7] Attribution scoring completed.")
    print("-" * 70)
    print(f"Events: {result['event_id'].nunique()}")
    print(f"Factory-event pairs: {len(result)}")
    print(f"Factories evaluated: {result['factory_id'].nunique()}")
    no_wind_events = result.loc[
        result["wind_direction_mean_deg"].isna(), "event_id"
    ].nunique()
    print(f"Events with missing wind direction (counted by rows): {no_wind_events}")
    top = result[result["factory_rank"] == 1][[
        "event_id", "station", "factory_name", "facility_category", "distance_km",
        "wind_relationship", "attribution_score", "relative_likelihood",
        "wind_evidence_quality", "source_identification_status",
    ]].sort_values("attribution_score", ascending=False).head(15)
    print("\nTop candidates:")
    print(top.to_string(index=False))
    print(f"\nOutput: {OUTPUT_FILE}")
    print("\nIMPORTANT: Scores are heuristic investigation metrics, not calibrated")
    print("probabilities or proof of responsibility. This does not replace")
    print("atmospheric dispersion modelling or regulatory investigation.")
    print("=" * 70)
    print("AIR KAVACH ATTRIBUTION ENGINE READY")
    print("=" * 70)


if __name__ == "__main__":
    main()
