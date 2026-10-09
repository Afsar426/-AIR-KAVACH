from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import json
import uuid
import pandas as pd
from src.utils.logger import get_logger
from src.utils.config import DATA_DIR
from src.ingestion.adapters.base_adapter import NormalizedRecord

logger = get_logger("quality_validator")

# Physical plausible bounds for environmental parameters
PARAM_BOUNDS = {
    "pm25": {"min": 0.0, "max": 2000.0, "unit": "µg/m³"},
    "pm10": {"min": 0.0, "max": 3000.0, "unit": "µg/m³"},
    "no2": {"min": 0.0, "max": 1000.0, "unit": "µg/m³"},
    "so2": {"min": 0.0, "max": 2000.0, "unit": "µg/m³"},
    "co": {"min": 0.0, "max": 100.0, "unit": "mg/m³"},
    "o3": {"min": 0.0, "max": 1000.0, "unit": "µg/m³"},
    "wind_direction_10m": {"min": 0.0, "max": 360.0, "unit": "degrees"},
    "wind_speed_10m": {"min": 0.0, "max": 100.0, "unit": "m/s"},
    "temperature_2m": {"min": -50.0, "max": 65.0, "unit": "°C"},
    "fire_radiative_power": {"min": 0.0, "max": 50000.0, "unit": "MW"},
    "stack_pm": {"min": 0.0, "max": 10000.0, "unit": "mg/Nm³"},
}


class QualityValidator:
    """
    Unified validation and freshness evaluation engine.
    Audits physical bounds, timestamps, geodetic coordinates,
    temporal staleness, and assigns explicit quality flags with reasons.
    """

    @staticmethod
    def validate_record(record: NormalizedRecord, max_staleness_hours: Optional[float] = None) -> NormalizedRecord:
        reasons = []

        # 1. Geodetic Coordinate Sanity Check
        if record.latitude is not None:
            if not (-90.0 <= record.latitude <= 90.0):
                reasons.append(f"Latitude out of bounds [-90, 90]: {record.latitude}")
        if record.longitude is not None:
            if not (-180.0 <= record.longitude <= 180.0):
                reasons.append(f"Longitude out of bounds [-180, 180]: {record.longitude}")

        # 2. Timestamp Validation
        try:
            obs_dt = pd.to_datetime(record.timestamp_utc, utc=True)
            now_dt = datetime.now(timezone.utc)
            if obs_dt > now_dt:
                reasons.append(f"Future observation timestamp: {record.timestamp_utc}")
            
            # Check staleness if explicitly requested
            if max_staleness_hours is not None and record.data_type in ("observed", "observed_live"):
                retrieval_dt = pd.to_datetime(record.retrieval_timestamp_utc, utc=True)
                age_hours = (retrieval_dt - obs_dt).total_seconds() / 3600.0
                if age_hours > max_staleness_hours:
                    record.quality_flag = "stale"
                    record.quality_reason = f"Observation is {age_hours:.1f} hours old (> {max_staleness_hours}h limit)"
        except Exception as e:
            reasons.append(f"Invalid timestamp format: {record.timestamp_utc} ({e})")

        # 3. Physical Value Range Bounds Check
        param_clean = record.parameter.lower().replace(".", "").replace(" ", "_")
        if param_clean in PARAM_BOUNDS:
            bounds = PARAM_BOUNDS[param_clean]
            if record.value < bounds["min"]:
                reasons.append(f"Value {record.value} below physical minimum {bounds['min']} {bounds['unit']}")
            elif record.value > bounds["max"]:
                reasons.append(f"Value {record.value} exceeds physical maximum {bounds['max']} {bounds['unit']}")

        # 4. Synthesize Flag and Explanation
        if reasons:
            record.quality_flag = "invalid" if any("out of bounds" in r or "below physical" in r or "Invalid timestamp" in r for r in reasons) else "suspect"
            record.quality_reason = "; ".join(reasons)
        elif record.quality_flag not in ("stale", "suspect"):
            record.quality_flag = "valid"
            record.quality_reason = None

        return record

    @classmethod
    def validate_batch(cls, records: List[NormalizedRecord]) -> Tuple[List[NormalizedRecord], Dict[str, Any]]:
        validated = []
        counts = {"valid": 0, "suspect": 0, "invalid": 0, "stale": 0}
        error_reasons = {}

        for rec in records:
            v_rec = cls.validate_record(rec)
            validated.append(v_rec)
            counts[v_rec.quality_flag] = counts.get(v_rec.quality_flag, 0) + 1
            if v_rec.quality_reason:
                error_reasons[v_rec.quality_reason] = error_reasons.get(v_rec.quality_reason, 0) + 1

        summary = {
            "total": len(records),
            "counts": counts,
            "acceptance_rate_pct": round((counts["valid"] / max(1, len(records))) * 100, 2),
            "errors": error_reasons,
        }
        return validated, summary


class IntakeLedger:
    """
    Persistent intake and import history ledger.
    Guarantees auditability across all data ingestion and CSV upload jobs.
    """

    def __init__(self, ledger_file: Optional[Path] = None):
        self.ledger_file = ledger_file or (DATA_DIR / "processed" / "intake_history.json")
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_file.exists():
            self._write_entries([])

    def _read_entries(self) -> List[Dict[str, Any]]:
        try:
            with open(self.ledger_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _write_entries(self, entries: List[Dict[str, Any]]) -> None:
        with open(self.ledger_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)

    def log_import(
        self,
        source: str,
        data_type: str,
        records_received: int,
        records_accepted: int,
        records_rejected: int,
        validation_errors: Optional[Dict[str, int]] = None,
        region_id: str = "in-mp-indore",
        details: Optional[Dict[str, Any]] = None,
        is_test: bool = False,
        environment: str = "production",
    ) -> Dict[str, Any]:
        """Appends an import job entry to the persistent ledger."""
        job_id = f"IMP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        entry = {
            "job_id": job_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "data_type": data_type,
            "region_id": region_id,
            "records_received": records_received,
            "records_accepted": records_accepted,
            "records_rejected": records_rejected,
            "validation_errors": validation_errors or {},
            "status": "completed" if records_accepted > 0 or records_received == 0 else "failed",
            "is_test": is_test,
            "environment": environment,
            "details": details or {},
        }
        entries = self._read_entries()
        entries.insert(0, entry)  # Prepend newest
        self._write_entries(entries[:500])  # Retain last 500 jobs
        return entry

    def list_history(
        self,
        limit: int = 50,
        environment: Optional[str] = None,
        is_test: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        entries = self._read_entries()
        if environment:
            entries = [e for e in entries if e.get("environment") == environment]
        if is_test is not None:
            entries = [e for e in entries if e.get("is_test", False) == is_test]
        return entries[:limit]
