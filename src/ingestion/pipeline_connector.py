from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from src.utils.logger import get_logger
from src.utils.config import (
    AIR_QUALITY_FILE,
    EVENTS_FILE,
    FACTORIES_FILE,
    WIND_FILE,
    ATTRIBUTION_FILE,
    CONFIDENCE_FILE,
    EVENT_WIND_FILE,
    MAP_FILE,
    DATA_DIR,
)
from src.ingestion.adapters.base_adapter import NormalizedRecord
from src.ingestion.quality import QualityValidator, IntakeLedger
from src.event_detection.event_processor import EventProcessor
from src.features.event_wind_alignment import EventWindAligner
from src.attribution.attribution_engine import AttributionEngine
from src.attribution.confidence import ConfidenceEngine
from src.evidence.map_data import generate_map_data

logger = get_logger("pipeline_connector")


class PipelineConnector:
    """
    Connects ingested and uploaded environmental records to the
    existing analytical and source attribution pipeline without data leakage.
    """

    def __init__(self):
        self.ledger = IntakeLedger()

    def ingest_and_process_air_quality(
        self,
        records: List[NormalizedRecord],
        region_id: str = "in-mp-indore",
        source_label: str = "Direct Feed / Upload",
        is_test: bool = False,
        environment: str = "production",
    ) -> Dict[str, Any]:
        """
        Validates, deduplicates, and incorporates new air quality records into
        the analytical store. If events are detected, updates attribution and map data.
        Guarantees complete test isolation when is_test=True or environment='test'.
        """
        if not records:
            return {"status": "no_records", "accepted": 0, "rejected": 0}

        is_test_run = is_test or environment == "test" or region_id.startswith("in-test-")

        # 1. Quality Validation
        validated_records, val_summary = QualityValidator.validate_batch(records)
        accepted_records = [r for r in validated_records if r.quality_flag in ("valid", "suspect", "stale")]
        rejected_count = len(records) - len(accepted_records)

        if not accepted_records:
            self.ledger.log_import(
                source=source_label,
                data_type="observed",
                records_received=len(records),
                records_accepted=0,
                records_rejected=len(records),
                validation_errors=val_summary["errors"],
                region_id=region_id,
                is_test=is_test_run,
                environment="test" if is_test_run else environment,
            )
            return {
                "status": "all_rejected",
                "received": len(records),
                "accepted": 0,
                "rejected": len(records),
                "validation_errors": val_summary["errors"],
                "is_test": is_test_run,
            }

        # 2. Build DataFrame
        rows = []
        for r in accepted_records:
            rows.append({
                "station": r.station_name or r.station_id or "Station",
                "sensor_id": str(r.station_id or "SENS-01"),
                "timestamp": pd.to_datetime(r.timestamp_utc, utc=True),
                "parameter": r.parameter,
                "value": float(r.value),
                "unit": r.unit,
                "city": r.city or "Indore",
                "quality_flag": r.quality_flag,
            })
        new_df = pd.DataFrame(rows)
        new_df = new_df.drop_duplicates(
            subset=["station", "timestamp", "parameter"], keep="last"
        )

        # 3. Idempotent Merge into Parquet
        # Isolate test runs into test_intake directory to prevent production contamination
        if is_test_run:
            target_parquet = DATA_DIR / "test_intake" / f"{region_id}_air_quality.parquet"
            target_parquet.parent.mkdir(parents=True, exist_ok=True)
        elif region_id == "in-mp-indore":
            target_parquet = AIR_QUALITY_FILE
        else:
            target_parquet = DATA_DIR / "processed" / "air_quality" / f"{region_id}_air_quality.parquet"
            target_parquet.parent.mkdir(parents=True, exist_ok=True)

        existing_len = 0
        if target_parquet.exists():
            try:
                existing_df = pd.read_parquet(target_parquet)
                existing_len = len(existing_df)
                if "sensor_id" in existing_df.columns:
                    existing_df["sensor_id"] = existing_df["sensor_id"].astype(str)
                if "sensor_id" in new_df.columns:
                    new_df["sensor_id"] = new_df["sensor_id"].astype(str)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                combined_df["timestamp"] = pd.to_datetime(combined_df["timestamp"], utc=True)
                # Deduplicate on (station, timestamp, parameter)
                combined_df = combined_df.drop_duplicates(
                    subset=["station", "timestamp", "parameter"], keep="last"
                )
            except Exception as e:
                logger.error(f"Error reading existing parquet {target_parquet}: {e}")
                combined_df = new_df
        else:
            combined_df = new_df

        combined_df = combined_df.sort_values(["station", "timestamp"]).reset_index(drop=True)
        target_parquet.parent.mkdir(parents=True, exist_ok=True)
        combined_df.to_parquet(target_parquet, index=False)

        new_net_inserted = max(0, len(combined_df) - existing_len)

        # 4. Trigger Event Detection only for real production regional pipelines
        events_count = 0
        attribution_status = "skipped"

        if not is_test_run and region_id == "in-mp-indore":
            try:
                event_proc = EventProcessor()
                events_df = event_proc.detect_events(combined_df)
                events_count = len(events_df)

                if events_count > 0:
                    # Run wind alignment
                    aligner = EventWindAligner()
                    aligner.run()

                    # Run attribution
                    attr_engine = AttributionEngine()
                    attr_engine.run()

                    # Run confidence scoring
                    conf_engine = ConfidenceEngine()
                    conf_engine.run()

                    # Recompute GeoJSON Map Layer
                    generate_map_data()
                    attribution_status = "recomputed_success"
            except Exception as pipe_err:
                logger.error(f"Error during downstream pipeline execution: {pipe_err}")
                attribution_status = f"error: {str(pipe_err)}"

        # 5. Log Import Ledger
        entry = self.ledger.log_import(
            source=source_label,
            data_type="observed",
            records_received=len(records),
            records_accepted=len(accepted_records),
            records_rejected=rejected_count,
            validation_errors=val_summary["errors"],
            region_id=region_id,
            is_test=is_test_run,
            environment="test" if is_test_run else environment,
            details={
                "net_inserted_rows": new_net_inserted,
                "total_rows_in_store": len(combined_df),
                "events_detected": events_count,
                "attribution_status": attribution_status,
                "storage_file": str(target_parquet),
            },
        )

        return {
            "status": "success",
            "job_id": entry["job_id"],
            "records_received": len(records),
            "records_accepted": len(accepted_records),
            "records_rejected": rejected_count,
            "net_new_inserted": new_net_inserted,
            "total_dataset_size": len(combined_df),
            "events_detected": events_count,
            "attribution_status": attribution_status,
            "is_test": is_test_run,
            "environment": "test" if is_test_run else environment,
            "isolated_store": str(target_parquet) if is_test_run else None,
        }

    def ingest_weather_records(
        self,
        records: List[NormalizedRecord],
        region_id: str = "in-mp-indore",
        source_label: str = "Open-Meteo Weather",
    ) -> Dict[str, Any]:
        """Idempotently saves weather observations into wind store."""
        if not records:
            return {"status": "no_records", "accepted": 0}

        validated_records, val_summary = QualityValidator.validate_batch(records)
        accepted = [r for r in validated_records if r.quality_flag in ("valid", "suspect")]

        if not accepted:
            return {"status": "rejected", "errors": val_summary["errors"]}

        rows = []
        for r in accepted:
            rows.append({
                "timestamp": pd.to_datetime(r.timestamp_utc, utc=True),
                "parameter": r.parameter,
                "value": float(r.value),
                "unit": r.unit,
                "station": r.station_name or "WeatherStation",
            })
        w_df = pd.DataFrame(rows)

        if WIND_FILE.exists():
            try:
                exist_w = pd.read_parquet(WIND_FILE)
                merged = pd.concat([exist_w, w_df], ignore_index=True).drop_duplicates(
                    subset=["timestamp", "parameter"], keep="last"
                )
            except Exception:
                merged = w_df
        else:
            merged = w_df

        merged.to_parquet(WIND_FILE, index=False)
        self.ledger.log_import(
            source=source_label,
            data_type="observed_weather",
            records_received=len(records),
            records_accepted=len(accepted),
            records_rejected=len(records) - len(accepted),
            region_id=region_id,
        )
        return {"status": "success", "accepted": len(accepted), "total_weather_rows": len(merged)}

    def ingest_facilities(
        self,
        facilities_list: List[Dict[str, Any]],
        region_id: str = "in-mp-indore",
        source_label: str = "Facility Registry Import",
    ) -> Dict[str, Any]:
        """Idempotently adds registered industrial facilities to the candidate catalog."""
        if not facilities_list:
            return {"status": "no_facilities", "accepted": 0}

        valid_facs = []
        for f in facilities_list:
            if "factory_id" in f and "latitude" in f and "longitude" in f and "factory_name" in f:
                try:
                    lat = float(f["latitude"])
                    lon = float(f["longitude"])
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        valid_facs.append({
                            "factory_id": str(f["factory_id"]),
                            "factory_name": str(f["factory_name"]),
                            "latitude": lat,
                            "longitude": lon,
                            "facility_category": str(f.get("facility_category", "industrial_works")),
                            "city": str(f.get("city", "Indore")),
                            "state_ut": str(f.get("state_ut", "Madhya Pradesh")),
                        })
                except Exception:
                    pass

        if not valid_facs:
            return {"status": "all_invalid", "accepted": 0}

        fac_df = pd.DataFrame(valid_facs)
        if FACTORIES_FILE.exists():
            try:
                exist_f = pd.read_parquet(FACTORIES_FILE)
                merged_f = pd.concat([exist_f, fac_df], ignore_index=True).drop_duplicates(
                    subset=["factory_id"], keep="last"
                )
            except Exception:
                merged_f = fac_df
        else:
            merged_f = fac_df

        FACTORIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        merged_f.to_parquet(FACTORIES_FILE, index=False)

        self.ledger.log_import(
            source=source_label,
            data_type="facility_registry",
            records_received=len(facilities_list),
            records_accepted=len(valid_facs),
            records_rejected=len(facilities_list) - len(valid_facs),
            region_id=region_id,
        )

        return {"status": "success", "accepted": len(valid_facs), "total_facilities": len(merged_f)}
