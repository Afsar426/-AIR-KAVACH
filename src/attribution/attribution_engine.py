from pathlib import Path
from typing import Dict, Any
import numpy as np
import pandas as pd
from src.utils.logger import get_logger
from src.utils.config import (
    EVENTS_FILE,
    DISTANCES_FILE,
    ATTRIBUTION_FILE,
    CONFIDENCE_FILE,
    WIND_FILE,
    EVENT_WIND_FILE,
)

logger = get_logger("attribution_engine")

DISTANCE_SCALE_KM = 5.0
WIND_WEIGHT = 0.70
DISTANCE_WEIGHT = 0.30
NO_RELIABLE_SOURCE_THRESHOLD = 0.35


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 to point 2 in degrees clockwise from North."""
    lat1, lat2 = np.radians(lat1), np.radians(lat2)
    delta_lon = np.radians(lon2 - lon1)
    x = np.sin(delta_lon) * np.cos(lat2)
    y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(delta_lon)
    return float((np.degrees(np.arctan2(x, y)) + 360) % 360)


def circular_angle_difference(angle1: float, angle2: float) -> float:
    """Smallest angular difference, 0 to 180 degrees."""
    if pd.isna(angle1) or pd.isna(angle2):
        return np.nan
    return float(abs((angle1 - angle2 + 180) % 360 - 180))


def calculate_alignment(sensor_to_factory_bearing: float, wind_direction: float) -> float:
    """
    Meteorological wind direction is the direction wind comes FROM.
    Compare it with the bearing from sensor TO factory.
    +1 = factory directly upwind; 0 = crosswind; -1 = downwind.
    """
    diff = circular_angle_difference(sensor_to_factory_bearing, wind_direction)
    if pd.isna(diff):
        return np.nan
    return float(np.cos(np.radians(diff)))


def calculate_distance_score(distance_km: float) -> float:
    if pd.isna(distance_km) or distance_km < 0:
        return 0.0
    return float(np.exp(-distance_km / DISTANCE_SCALE_KM))


def classify_alignment(score: float) -> str:
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


def classify_evidence(row: pd.Series) -> str:
    relationship, distance = row["wind_relationship"], row["distance_km"]
    if pd.isna(distance):
        return "INSUFFICIENT GEOSPATIAL EVIDENCE"
    if relationship in ("strong_upwind", "upwind") and distance <= 5:
        return "GEOSPATIAL SCREENING SUPPORT"
    if relationship in ("strong_upwind", "upwind"):
        return "WIND ALIGNMENT SUPPORT"
    if relationship == "unknown" and distance <= 5:
        return "INSUFFICIENT METEOROLOGICAL EVIDENCE"
    if distance <= 5:
        return "NEARBY BUT WIND MISALIGNED"
    return "WEAK GEOSPATIAL SCREENING EVIDENCE"


class SourceAttributionEngine:
    def __init__(self):
        self.events_file = EVENTS_FILE
        self.distances_file = DISTANCES_FILE
        self.wind_file = WIND_FILE
        self.output_attribution = ATTRIBUTION_FILE
        self.output_confidence = CONFIDENCE_FILE

    def run(self) -> Dict[str, Any]:
        return self.run_attribution()

    def run_attribution(self) -> Dict[str, Any]:
        logger.info("Executing Industrial Source Attribution Engine...")
        if not self.events_file.exists():
            raise FileNotFoundError(f"Events dataset missing: {self.events_file}")
        if not self.distances_file.exists():
            raise FileNotFoundError(f"Sensor-factory distances dataset missing: {self.distances_file}")

        events = pd.read_parquet(self.events_file)
        distances = pd.read_parquet(self.distances_file)

        if events.empty:
            return {"status": "no_events", "candidates_evaluated": 0}

        # Check for wind data
        if EVENT_WIND_FILE.exists():
            events_wind = pd.read_parquet(EVENT_WIND_FILE)
            events = events.merge(
                events_wind[["event_id", "wind_direction_mean_deg", "wind_speed_mean_mps", "wind_coverage"]],
                on="event_id",
                how="left",
            )
        else:
            events["wind_direction_mean_deg"] = np.nan
            events["wind_speed_mean_mps"] = np.nan
            events["wind_coverage"] = 0.0

        # Pair events with factories
        merged = events.merge(distances, left_on="station", right_on="sensor", how="inner")
        if merged.empty:
            raise ValueError("No event-factory pairs created.")

        merged["bearing_sensor_to_factory_deg"] = merged.apply(
            lambda r: calculate_bearing(
                r["sensor_latitude"], r["sensor_longitude"],
                r["factory_latitude"], r["factory_longitude"],
            ),
            axis=1,
        )
        merged["bearing_factory_to_sensor_deg"] = (merged["bearing_sensor_to_factory_deg"] + 180) % 360

        merged["wind_angle_difference_deg"] = merged.apply(
            lambda r: circular_angle_difference(
                r["bearing_sensor_to_factory_deg"], r["wind_direction_mean_deg"]
            ),
            axis=1,
        )
        merged["wind_alignment"] = merged.apply(
            lambda r: calculate_alignment(
                r["bearing_sensor_to_factory_deg"], r["wind_direction_mean_deg"]
            ),
            axis=1,
        )
        merged["positive_wind_alignment"] = merged["wind_alignment"].clip(lower=0).fillna(0.0)
        merged["distance_score"] = merged["distance_km"].apply(calculate_distance_score)
        merged["attribution_score"] = (
            WIND_WEIGHT * merged["positive_wind_alignment"] + DISTANCE_WEIGHT * merged["distance_score"]
        ).clip(lower=0.0, upper=1.0)

        merged["wind_direction_available"] = merged["wind_direction_mean_deg"].notna()
        merged["wind_speed_available"] = merged["wind_speed_mean_mps"].notna()
        coverage = pd.to_numeric(merged["wind_coverage"], errors="coerce").fillna(0.0)
        speed = pd.to_numeric(merged["wind_speed_mean_mps"], errors="coerce")

        good_wind = (
            merged["wind_direction_available"] & merged["wind_speed_available"] & (speed > 0.1) & (coverage >= 0.75)
        )
        limited_wind = merged["wind_direction_available"] & (coverage >= 0.75)
        merged["wind_evidence_quality"] = np.select([good_wind, limited_wind], ["good", "limited"], default="weak")
        merged["wind_relationship"] = merged["wind_alignment"].apply(classify_alignment)

        merged = merged.sort_values(
            ["event_id", "attribution_score", "distance_km"],
            ascending=[True, False, True],
            kind="mergesort",
        ).copy()

        merged["factory_rank"] = merged.groupby("event_id").cumcount() + 1
        merged["top_event_score"] = merged.groupby("event_id")["attribution_score"].transform("max")
        event_has_wind = merged.groupby("event_id")["wind_direction_mean_deg"].transform(lambda s: s.notna().any())

        merged["source_identification_status"] = np.where(
            (merged["top_event_score"] < NO_RELIABLE_SOURCE_THRESHOLD) | (~event_has_wind),
            "no_reliable_source",
            "candidate_source_found",
        )
        score_sum = merged.groupby("event_id")["attribution_score"].transform("sum")
        merged["relative_likelihood"] = np.where(score_sum > 0, merged["attribution_score"] / score_sum, 0.0)
        merged["screening_score_share"] = merged["relative_likelihood"]
        merged["direct_emissions_evidence"] = "DIRECT EMISSIONS EVIDENCE UNAVAILABLE (CEMS UNCONNECTED)"
        merged["evidence_label"] = merged.apply(classify_evidence, axis=1)

        output_columns = [
            "event_id", "station", "factory_id", "factory_name", "facility_category",
            "peak_pm25", "distance_km", "distance_score",
            "wind_direction_mean_deg", "wind_speed_mean_mps", "wind_coverage",
            "bearing_sensor_to_factory_deg", "bearing_factory_to_sensor_deg",
            "wind_angle_difference_deg", "wind_alignment", "positive_wind_alignment",
            "wind_relationship", "wind_evidence_quality", "attribution_score",
            "relative_likelihood", "screening_score_share", "factory_rank", "top_event_score",
            "source_identification_status", "evidence_label", "direct_emissions_evidence",
        ]

        result = merged[output_columns].copy()
        self.output_attribution.parent.mkdir(parents=True, exist_ok=True)
        result.to_parquet(self.output_attribution, index=False)

        # Build confidence dataframe
        confidence_cols = [
            "event_id", "station", "factory_id", "factory_name", "facility_category",
            "factory_rank", "attribution_score", "relative_likelihood", "screening_score_share",
            "distance_km", "wind_relationship", "wind_evidence_quality", "evidence_label",
            "source_identification_status", "direct_emissions_evidence",
        ]
        result[confidence_cols].to_parquet(self.output_confidence, index=False)

        summary = {
            "status": "success",
            "events_evaluated": int(result["event_id"].nunique()),
            "candidate_records_generated": int(len(result)),
            "unique_factories_evaluated": int(result["factory_id"].nunique()),
            "output_attribution_file": str(self.output_attribution),
            "output_confidence_file": str(self.output_confidence),
        }
        logger.info(f"Attribution complete: {len(result)} candidate records generated.")
        return summary


AttributionEngine = SourceAttributionEngine
