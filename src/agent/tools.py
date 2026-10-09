import json
import time
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import numpy as np
import pandas as pd

from src.utils.logger import get_logger
from src.utils.config import (
    AIR_QUALITY_FILE,
    EVENTS_FILE,
    ATTRIBUTION_FILE,
    CONFIDENCE_FILE,
    EVENT_WIND_FILE,
    FACTORIES_FILE,
    DISTANCES_FILE,
    ISOLATION_FOREST_MODEL_DIR,
    REPORTS_DIR,
)
from src.geo.registry import GeoRegistryService, CoverageStatus

logger = get_logger("agent_tools")


class AgentToolRegistry:
    """Allowlisted typed analytical tools executable by the Agentic AI Orchestrator."""

    @staticmethod
    def get_region_coverage(region_id: Optional[str] = None, city: Optional[str] = None, state_ut: Optional[str] = None) -> Dict[str, Any]:
        """Inspects data coverage for a given geographic scope across India."""
        if region_id:
            reg = GeoRegistryService.get_region_by_id(region_id)
            if reg:
                return {
                    "region_id": reg.id,
                    "region_name": reg.name,
                    "city": reg.city,
                    "state_ut": reg.state_ut,
                    "coverage_status": reg.coverage_status.value,
                    "coverage_description": reg.coverage_description,
                    "has_wind_data": reg.has_wind_data,
                    "has_facilities_data": reg.has_facilities_data,
                    "station_count": reg.station_count,
                }
        if city or state_ut:
            reg, status = GeoRegistryService.match_region(state_ut=state_ut, city=city)
            if reg:
                return {
                    "region_id": reg.id,
                    "region_name": reg.name,
                    "city": reg.city,
                    "state_ut": reg.state_ut,
                    "coverage_status": status.value,
                    "coverage_description": reg.coverage_description,
                    "has_wind_data": reg.has_wind_data,
                    "has_facilities_data": reg.has_facilities_data,
                    "station_count": reg.station_count,
                }
            return {
                "region_id": "unregistered-region",
                "coverage_status": CoverageStatus.NO_USABLE_DATA.value,
                "coverage_description": f"No observations loaded for requested area ({city or state_ut}).",
                "has_wind_data": False,
                "has_facilities_data": False,
                "station_count": 0,
            }

        # Default national overview
        return {
            "region_id": "national-pan-india",
            "region_name": "Pan-India Environmental Intelligence Scope",
            "city": "All",
            "state_ut": "All",
            "coverage_status": CoverageStatus.PARTIAL_COVERAGE.value,
            "coverage_description": "Pan-India multi-region architecture active. Full 15-minute observations loaded for Indore validation region; other states registered.",
            "has_wind_data": True,
            "has_facilities_data": True,
            "station_count": 4,
        }

    @staticmethod
    def get_air_quality_observations(station: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        """Retrieves raw or normalized air quality readings."""
        if not AIR_QUALITY_FILE.exists():
            return {"total": 0, "records": [], "status": "missing_dataset"}
        df = pd.read_parquet(AIR_QUALITY_FILE)
        if station:
            df = df[df["station"].str.casefold() == station.casefold()]
        df = df.sort_values("timestamp", ascending=False).head(limit)
        clean = df.astype(object).where(pd.notna(df), None)
        return {
            "total_available": len(df),
            "records": json.loads(clean.to_json(orient="records", date_format="iso")),
            "status": "success",
        }

    @staticmethod
    def get_event_details(event_id: str) -> Dict[str, Any]:
        """Fetches metadata, timings, and severity metrics for a detected pollution event."""
        if not EVENTS_FILE.exists():
            return {"error": "Events dataset not found", "event": None}
        df = pd.read_parquet(EVENTS_FILE)
        matched = df[df["event_id"].astype(str) == event_id]
        if matched.empty:
            return {"error": f"Event {event_id} not found", "event": None}
        clean = matched.astype(object).where(pd.notna(matched), None)
        return {"event": json.loads(clean.to_json(orient="records", date_format="iso"))[0], "status": "success"}

    @staticmethod
    def detect_pollution_events() -> Dict[str, Any]:
        """Executes the statistical and ML pollution event detector."""
        from src.event_detection.event_processor import EventProcessor
        ep = EventProcessor()
        return ep.process_events()

    @staticmethod
    def get_meteorological_context(event_id: str) -> Dict[str, Any]:
        """Extracts aligned meteorological wind vectors during an event window."""
        if not EVENT_WIND_FILE.exists():
            return {"wind_available": False, "reason": "No aligned weather file present"}
        df = pd.read_parquet(EVENT_WIND_FILE)
        matched = df[df["event_id"].astype(str) == event_id]
        if matched.empty:
            return {"wind_available": False, "reason": f"Event {event_id} has no meteorological record"}
        row = matched.iloc[0]
        speed = float(row["wind_speed_mean_mps"]) if pd.notna(row.get("wind_speed_mean_mps")) else None
        dir_deg = float(row["wind_direction_mean_deg"]) if pd.notna(row.get("wind_direction_mean_deg")) else None
        is_calm = speed is not None and speed < 0.5
        return {
            "wind_available": dir_deg is not None,
            "wind_direction_mean_deg": dir_deg,
            "wind_speed_mean_mps": speed,
            "wind_coverage": float(row.get("wind_coverage", 0.0)) if pd.notna(row.get("wind_coverage")) else 0.0,
            "observations_count": int(row.get("wind_observations", 0)),
            "is_calm_wind": is_calm,
            "wind_speed_missing": speed is None,
            "weather_match_status": row.get("weather_match_status") or ("calm_wind" if is_calm else ("matched_observed" if dir_deg is not None else "insufficient_weather")),
        }

    @staticmethod
    def get_nearby_facilities(station: str, max_distance_km: float = 15.0) -> List[Dict[str, Any]]:
        """Finds candidate industrial facilities within distance radius of a monitoring station."""
        if not DISTANCES_FILE.exists():
            return []
        df = pd.read_parquet(DISTANCES_FILE)
        matched = df[(df["sensor"].str.casefold() == station.casefold()) & (df["distance_km"] <= max_distance_km)]
        clean = matched.astype(object).where(pd.notna(matched), None)
        return json.loads(clean.to_json(orient="records"))

    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Great-circle distance between two geographic coordinates in kilometers."""
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0)**2
        return float(6371.0 * 2.0 * np.arcsin(np.sqrt(a)))

    @staticmethod
    def calculate_wind_alignment(sensor_lat: float, sensor_lon: float, factory_lat: float, factory_lon: float, wind_direction_from_deg: float) -> Dict[str, Any]:
        """Calculates sensor-to-factory bearing and angular alignment with wind vector."""
        lat1, lon1, lat2, lon2 = map(np.radians, [sensor_lat, sensor_lon, factory_lat, factory_lon])
        dlon = lon2 - lon1
        x = np.sin(dlon) * np.cos(lat2)
        y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
        bearing = float((np.degrees(np.arctan2(x, y)) + 360) % 360)
        ang_diff = float(abs((bearing - wind_direction_from_deg + 180) % 360 - 180))
        alignment = float(np.cos(np.radians(ang_diff)))
        return {
            "bearing_sensor_to_factory_deg": bearing,
            "wind_direction_from_deg": wind_direction_from_deg,
            "angular_difference_deg": ang_diff,
            "alignment_score": alignment,
            "is_upwind": alignment >= 0.25,
        }

    @staticmethod
    def rank_source_candidates(event_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Ranks candidate industrial facilities using distance decay and wind vector alignment."""
        if not ATTRIBUTION_FILE.exists():
            return []
        df = pd.read_parquet(ATTRIBUTION_FILE)
        matched = df[df["event_id"].astype(str) == event_id].sort_values("factory_rank", ascending=True).head(limit)
        clean = matched.astype(object).where(pd.notna(matched), None)
        return json.loads(clean.to_json(orient="records"))

    @staticmethod
    def get_evidence_chain(event_id: str) -> Dict[str, Any]:
        """Gathers full multi-source evidence chain for an event."""
        conf_df = pd.read_parquet(CONFIDENCE_FILE) if CONFIDENCE_FILE.exists() else pd.DataFrame()
        matched = conf_df[conf_df["event_id"].astype(str) == event_id] if not conf_df.empty else pd.DataFrame()
        clean = matched.astype(object).where(pd.notna(matched), None)
        candidates = json.loads(clean.to_json(orient="records")) if not matched.empty else []
        return {
            "event_id": event_id,
            "candidate_count": len(candidates),
            "candidates": candidates,
            "limitations": [
                "Scores represent heuristic evidence strength, not calibrated causation probability.",
                "Wind vector uses ground monitoring; atmospheric dispersion models (AERMOD/HYSPLIT) are recommended for legal compliance.",
            ],
        }

    @staticmethod
    def inspect_data_quality() -> Dict[str, Any]:
        """Audits observations, missing values, duplicates, and freshness."""
        if not AIR_QUALITY_FILE.exists():
            return {"status": "no_data"}
        df = pd.read_parquet(AIR_QUALITY_FILE)
        return {
            "total_records": len(df),
            "stations": list(df["station"].unique()),
            "earliest_timestamp": df["timestamp"].min().isoformat() if not df.empty else None,
            "latest_timestamp": df["timestamp"].max().isoformat() if not df.empty else None,
            "null_values": int(df["value"].isna().sum()),
            "negative_values": int((df["value"] < 0).sum()),
            "units": list(df["unit"].unique()),
        }

    @staticmethod
    def inspect_model_status() -> Dict[str, Any]:
        """Reports Isolation Forest model lifecycle status and feature metadata."""
        meta_file = ISOLATION_FOREST_MODEL_DIR / "metadata.json"
        if not meta_file.exists():
            return {"status": "not_trained", "version": None}
        with meta_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def inspect_ingestion_status() -> Dict[str, Any]:
        """Reports latest OpenAQ / weather ingestion run metadata."""
        hist_file = AIR_QUALITY_FILE.parent / "ingestion_history.json"
        if hist_file.exists():
            with hist_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {"status": "idle", "last_run": None}

    @staticmethod
    def generate_investigation_report(event_id: str, summary_text: str, result_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Compiles and exports reproducible disaggregated investigation report to persistent disk."""
        report_id = f"REP-{event_id}-{int(time.time())}"
        
        event_data = result_payload.get("event") or {}
        met_context = result_payload.get("meteorological_context") or {}
        candidates = result_payload.get("candidates") or []
        
        observed_facts = {
            "station": event_data.get("station"),
            "city": event_data.get("city", "Indore"),
            "state_ut": event_data.get("state_ut", "Madhya Pradesh"),
            "start_time": event_data.get("start_time"),
            "end_time": event_data.get("end_time"),
            "duration_minutes": event_data.get("duration_minutes"),
            "peak_pm25": event_data.get("peak_pm25"),
            "baseline_mean": event_data.get("baseline_mean"),
            "reading_count": event_data.get("num_readings") or event_data.get("readings", 4),
            "wind_direction_mean_deg": met_context.get("wind_direction_mean_deg"),
            "wind_speed_mean_mps": met_context.get("wind_speed_mean_mps"),
            "wind_coverage": met_context.get("wind_coverage", 0.0),
            "is_calm_wind": met_context.get("is_calm_wind", False),
            "weather_match_status": met_context.get("weather_match_status", "matched_observed"),
        }
        
        modeled_estimates = {
            "peak_z_score": event_data.get("peak_z_score"),
            "anomaly_score": event_data.get("anomaly_score") or event_data.get("ml_anomaly_score"),
            "temporal_lifecycle_status": event_data.get("temporal_status", "historical"),
            "dispersion_scale_km": 5.0,
            "baseline_method": "past-only rolling 24h baseline (shift(1).rolling(96))",
            "distance_decay_formula": "exp(-d / 5.0)",
            "scoring_formula": "0.7 * wind_alignment + 0.3 * distance_decay",
        }
        
        missing_evidence = [
            "Direct continuous emissions monitoring system (CEMS) telemetry is unavailable for candidate facilities.",
            "Planetary boundary layer mixing height and vertical wind shear observations are unrecorded.",
            "Real-time operational run-time logs for candidate industrial facilities are unverified.",
        ]
        if met_context.get("wind_speed_missing"):
            missing_evidence.append("Surface anemometer wind speed is unrecorded for this monitoring station during event hours.")
        if met_context.get("is_calm_wind"):
            missing_evidence.append("Calm surface winds (< 0.5 m/s) observed; transport is dominated by diffusion rather than horizontal advection.")
        if not candidates:
            missing_evidence.append("No mapped industrial facilities located within search radius buffer.")
        
        limitations = [
            "Attribution scores reflect heuristic geospatial and meteorological screening index, NOT verified legal causation or calibrated dispersion probability.",
            "AERMOD or HYSPLIT dispersion modeling is required for regulatory enforcement or legal action.",
            "Candidate rankings are based on 10m surface horizontal wind alignment without accounting for complex terrain or building downwash.",
        ]
        
        provenance = {
            "system": "AIR KAVACH Pan-India Environmental Intelligence Platform",
            "version": "2.1.0",
            "attribution_methodology": "Heuristic distance decay (30%) + wind alignment (70%)",
            "event_detection_engine": "Past-only rolling baseline (shift(1)) + Z-score thresholding",
            "report_generated_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        }
        
        report_data = {
            "report_id": report_id,
            "event_id": event_id,
            "generated_at": provenance["report_generated_utc"],
            "investigation_summary": summary_text,
            "observed_facts": observed_facts,
            "modeled_estimates": modeled_estimates,
            "candidate_rankings": candidates,
            "missing_evidence": missing_evidence,
            "limitations": limitations,
            "provenance": provenance,
            "result_payload": result_payload,
            "disclaimer": (
                "Candidate rankings are heuristic screening metrics indicating geographic and meteorological consistency, "
                "not proof of legal liability or proven industrial causation."
            ),
        }
        out_dir = REPORTS_DIR / "investigations"
        out_dir.mkdir(parents=True, exist_ok=True)
        report_file = out_dir / f"{report_id}.json"
        with report_file.open("w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        return {
            "report_id": report_id,
            "file_path": str(report_file),
            "status": "persisted",
            "observed_facts": observed_facts,
            "modeled_estimates": modeled_estimates,
            "candidate_rankings": candidates,
            "missing_evidence": missing_evidence,
            "limitations": limitations,
            "provenance": provenance,
        }
