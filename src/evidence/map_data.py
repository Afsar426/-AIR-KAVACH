from pathlib import Path
import json

import numpy as np
import pandas as pd


# AIR KAVACH - FRESH MAP DATA GENERATOR
# Builds map data from the CURRENT attribution and confidence outputs,
# rather than the older geospatial-evidence snapshot.

BASE_DIR = Path(__file__).resolve().parents[2]

ATTRIBUTION_FILE = (
    BASE_DIR / "data" / "features" / "event_factory_attribution.parquet"
)
CONFIDENCE_FILE = (
    BASE_DIR / "data" / "features" / "event_factory_confidence.parquet"
)
DISTANCE_FILE = (
    BASE_DIR / "data" / "features" / "sensor_factory_distances.parquet"
)
OUTPUT_FILE = BASE_DIR / "backend" / "map_data.json"

TOP_CANDIDATES_PER_EVENT = 3


def clean_value(value):
    """Convert pandas/numpy values into JSON-safe Python values."""
    if value is None:
        return None

    if isinstance(value, (np.bool_, bool)):
        return bool(value)

    if pd.isna(value):
        return None

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating,)):
        value = float(value)
        return value if np.isfinite(value) else None

    if hasattr(value, "item"):
        try:
            return clean_value(value.item())
        except Exception:
            pass

    return value


def main():
    print("=" * 70)
    print("AIR KAVACH - FRESH MAP DATA GENERATOR")
    print("=" * 70)

    for path in (ATTRIBUTION_FILE, CONFIDENCE_FILE, DISTANCE_FILE):
        if not path.exists():
            raise FileNotFoundError(f"Required input file not found: {path}")

    print("\n[1/6] Loading current pipeline outputs...")
    attribution = pd.read_parquet(ATTRIBUTION_FILE)
    confidence = pd.read_parquet(CONFIDENCE_FILE)
    distances = pd.read_parquet(DISTANCE_FILE)

    print(f"Attribution rows: {len(attribution)}")
    print(f"Confidence rows: {len(confidence)}")
    print(f"Sensor-factory distance rows: {len(distances)}")

    attribution_required = [
        "event_id", "station", "factory_id", "factory_name",
        "facility_category", "peak_pm25", "distance_km", "distance_score",
        "wind_direction_mean_deg", "wind_speed_mean_mps", "wind_coverage",
        "wind_relationship", "wind_evidence_quality", "attribution_score",
        "relative_likelihood", "factory_rank", "source_identification_status",
        "evidence_label",
    ]
    confidence_required = [
        "event_id", "station", "factory_id", "confidence_percent",
        "confidence_level", "uncertainty_percent", "uncertainty_level",
        "investigation_status", "confidence_explanation",
        "wind_evidence_limitation", "separation_score",
    ]
    distance_required = [
        "sensor", "factory_id", "sensor_latitude", "sensor_longitude",
        "factory_latitude", "factory_longitude", "distance_km",
    ]

    for label, frame, required in (
        ("attribution", attribution, attribution_required),
        ("confidence", confidence, confidence_required),
        ("distances", distances, distance_required),
    ):
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise ValueError(f"Missing columns in {label} input: {missing}")

    print("\n[2/6] Joining current confidence and geographic coordinates...")
    confidence_columns = [
        "event_id", "station", "factory_id",
        "confidence_percent", "confidence_level",
        "uncertainty_percent", "uncertainty_level",
        "investigation_status", "confidence_explanation",
        "wind_evidence_limitation", "separation_score",
        "wind_reliability_score", "spatial_compatibility_score",
    ]
    confidence_subset = confidence[confidence_columns].copy()

    merged = attribution.merge(
        confidence_subset,
        on=["event_id", "station", "factory_id"],
        how="left",
        validate="one_to_one",
        indicator="_confidence_merge",
    )

    missing_confidence = int((merged["_confidence_merge"] != "both").sum())
    if missing_confidence:
        raise ValueError(
            f"{missing_confidence} attribution rows did not match confidence rows. "
            "Rerun confidence.py after scoring.py before generating map data."
        )
    merged = merged.drop(columns=["_confidence_merge"])

    # Distances are one row per station/factory pair and contain coordinates.
    merged = merged.merge(
        distances[
            [
                "sensor", "factory_id", "sensor_latitude", "sensor_longitude",
                "factory_latitude", "factory_longitude",
            ]
        ],
        left_on=["station", "factory_id"],
        right_on=["sensor", "factory_id"],
        how="left",
        validate="many_to_one",
        indicator="_geo_merge",
    )

    missing_geo = int((merged["_geo_merge"] != "both").sum())
    if missing_geo:
        raise ValueError(
            f"{missing_geo} rows did not match station/factory coordinates. "
            "Check station names and distance data."
        )
    merged = merged.drop(columns=["_geo_merge", "sensor"])

    # Confirm that the map distance agrees with the current attribution distance.
    # A small tolerance is allowed for rounding/serialization.
    distance_check = merged["distance_km"].sub(
        merged.merge(
            distances[["sensor", "factory_id", "distance_km"]].rename(
                columns={"distance_km": "distance_from_reference_km"}
            ),
            left_on=["station", "factory_id"],
            right_on=["sensor", "factory_id"],
            how="left",
            validate="many_to_one",
        )["distance_from_reference_km"]
    ).abs()
    if distance_check.dropna().gt(0.01).any():
        raise ValueError(
            "Attribution distances differ from the sensor-factory distance reference "
            "by more than 0.01 km. Investigate before publishing map data."
        )

    print(f"Joined rows: {len(merged)}")
    print("Confidence and coordinates matched successfully.")

    print("\n[3/6] Selecting top candidates per event...")
    merged = merged.sort_values(
        ["event_id", "factory_rank"],
        ascending=[True, True],
        kind="mergesort",
    )
    selected = merged[merged["factory_rank"] <= TOP_CANDIDATES_PER_EVENT].copy()

    # Determine whether each event has wind direction/speed data.
    event_wind = merged.groupby("event_id").agg(
        event_wind_direction_available=(
            "wind_direction_mean_deg", lambda s: bool(s.notna().any())
        ),
        event_wind_speed_available=(
            "wind_speed_mean_mps", lambda s: bool(s.notna().any())
        ),
    )
    selected = selected.join(event_wind, on="event_id")

    print(f"Map candidate records selected: {len(selected)}")
    print(f"Events represented: {selected['event_id'].nunique()}")

    print("\n[4/6] Building event/candidate JSON...")
    events = {}

    for _, row in selected.iterrows():
        event_id = clean_value(row["event_id"])

        candidate = {
            "event_id": event_id,
            "station": clean_value(row["station"]),
            "sensor": {
                "latitude": clean_value(row["sensor_latitude"]),
                "longitude": clean_value(row["sensor_longitude"]),
            },
            "factory": {
                "id": clean_value(row["factory_id"]),
                "name": clean_value(row["factory_name"]),
                "category": clean_value(row["facility_category"]),
                "latitude": clean_value(row["factory_latitude"]),
                "longitude": clean_value(row["factory_longitude"]),
                "rank": int(row["factory_rank"]),
            },
            "pollution": {
                "peak_pm25": clean_value(row["peak_pm25"]),
            },
            "distance": {
                "km": clean_value(row["distance_km"]),
            },
            "wind": {
                "direction_from_deg": clean_value(
                    row["wind_direction_mean_deg"]
                ),
                "speed_mps": clean_value(row["wind_speed_mean_mps"]),
                "coverage": clean_value(row["wind_coverage"]),
                "relationship": clean_value(row["wind_relationship"]),
                "evidence_quality": clean_value(row["wind_evidence_quality"]),
                "event_direction_available": clean_value(
                    row["event_wind_direction_available"]
                ),
                "event_speed_available": clean_value(
                    row["event_wind_speed_available"]
                ),
            },
            "attribution": {
                "score": clean_value(row["attribution_score"]),
                "relative_score_share": clean_value(
                    row["relative_likelihood"]
                ),
                "score_interpretation": (
                    "Heuristic screening score/share; not a probability "
                    "that this facility caused the event."
                ),
                "evidence_label": clean_value(row["evidence_label"]),
                "source_identification_status": clean_value(
                    row["source_identification_status"]
                ),
            },
            "confidence": {
                "percent": clean_value(row["confidence_percent"]),
                "level": clean_value(row["confidence_level"]),
                "interpretation": (
                    "Relative evidence-strength index; not a calibrated "
                    "probability of causation."
                ),
            },
            "uncertainty": {
                "percent": clean_value(row["uncertainty_percent"]),
                "level": clean_value(row["uncertainty_level"]),
                "wind_limitation": clean_value(
                    row["wind_evidence_limitation"]
                ),
                "candidate_separation_score": clean_value(
                    row["separation_score"]
                ),
            },
            "investigation": {
                "status": clean_value(row["investigation_status"]),
                "explanation": clean_value(row["confidence_explanation"]),
            },
        }

        if event_id not in events:
            events[event_id] = {
                "event_id": event_id,
                "station": clean_value(row["station"]),
                "sensor": candidate["sensor"],
                "peak_pm25": clean_value(row["peak_pm25"]),
                "wind": candidate["wind"],
                "source_identification_status": clean_value(
                    row["source_identification_status"]
                ),
                "candidates": [],
            }

        events[event_id]["candidates"].append(candidate)

    # Candidate rank order is explicit and stable.
    for event in events.values():
        event["candidates"].sort(key=lambda item: item["factory"]["rank"])

    print("\n[5/6] Writing fresh map JSON...")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "project": "AIR KAVACH",
        "description": (
            "Current pollution-event and factory-candidate screening evidence. "
            "Scores are heuristic and do not establish causation."
        ),
        "generated_from": [
            str(ATTRIBUTION_FILE.relative_to(BASE_DIR)),
            str(CONFIDENCE_FILE.relative_to(BASE_DIR)),
            str(DISTANCE_FILE.relative_to(BASE_DIR)),
        ],
        "candidate_limit_per_event": TOP_CANDIDATES_PER_EVENT,
        "total_records": int(len(selected)),
        "total_events": int(len(events)),
        "scientific_caveat": (
            "Attribution scores and confidence indices are not calibrated "
            "probabilities or proof of responsibility. Verify with independent "
            "evidence and suitable atmospheric dispersion modelling."
        ),
        "events": list(events.values()),
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False, allow_nan=False)

    print("\n[6/6] Summary and consistency check...")
    print(f"Events: {len(events)}")
    print(f"Candidate records: {len(selected)}")
    print(f"Output: {OUTPUT_FILE}")
    sample_event_id = sorted(events.keys())[0]
    sample = events[sample_event_id]
    print(f"Sample event: {sample_event_id}")
    if sample["candidates"]:
        top = sample["candidates"][0]
        print(
            "Top candidate: "
            f"{top['factory']['name']} | "
            f"rank={top['factory']['rank']} | "
            f"distance={top['distance']['km']} km | "
            f"score={top['attribution']['score']}"
        )

    print("\nMAP DATA GENERATION COMPLETE")
    print("=" * 70)


generate_map_data = main


if __name__ == "__main__":
    main()
