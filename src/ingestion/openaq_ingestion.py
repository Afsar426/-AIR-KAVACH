import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import requests
from src.utils.logger import get_logger
from src.utils.config import OPENAQ_API_KEY, AIR_QUALITY_FILE, DATA_DIR

logger = get_logger("openaq_ingestion")

SENSORS = {
    "Residency": 12238477,
    "Regional_Park": 12238486,
    "Airport": 12238495,
    "Maguda": 12815122,
}

BASE_URL = "https://api.openaq.org/v3/sensors"


class OpenAQIngestionService:
    def __init__(self, api_key: str = OPENAQ_API_KEY):
        self.api_key = api_key
        self.headers = {"X-API-Key": self.api_key} if self.api_key else {}
        self.history_file = DATA_DIR / "processed" / "air_quality" / "ingestion_history.json"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def fetch_sensor_measurements(
        self,
        sensor_id: int,
        datetime_from: Optional[str] = None,
        datetime_to: Optional[str] = None,
        max_pages: int = 5,
    ) -> List[Dict[str, Any]]:
        url = f"{BASE_URL}/{sensor_id}/measurements"
        page = 1
        all_records = []

        while page <= max_pages:
            params: Dict[str, Any] = {"limit": 1000, "page": page}
            if datetime_from:
                params["datetime_from"] = datetime_from
            if datetime_to:
                params["datetime_to"] = datetime_to

            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                if response.status_code == 429:
                    logger.warning("OpenAQ rate limit hit (429). Retrying after backoff...")
                    time.sleep(5)
                    continue

                if not response.ok:
                    logger.error(f"OpenAQ request failed ({response.status_code}): {response.text}")
                    break

                data = response.json()
                records = data.get("results", [])
                if not records:
                    break

                all_records.extend(records)
                if len(records) < 1000:
                    break

                page += 1
                time.sleep(0.2)
            except Exception as e:
                logger.error(f"Exception during OpenAQ fetch for sensor {sensor_id}: {e}")
                break

        return all_records

    def run_ingestion(self) -> Dict[str, Any]:
        logger.info("Starting OpenAQ Incremental Ingestion Cycle...")
        start_time = time.time()
        new_records_count = 0
        rejected_records_count = 0
        sensor_stats = {}

        # Load existing dataset if present
        if AIR_QUALITY_FILE.exists():
            try:
                existing_df = pd.read_parquet(AIR_QUALITY_FILE)
            except Exception as e:
                logger.error(f"Error loading existing parquet: {e}")
                existing_df = pd.DataFrame()
        else:
            existing_df = pd.DataFrame()

        new_rows = []

        for station_name, sensor_id in SENSORS.items():
            records = self.fetch_sensor_measurements(sensor_id=sensor_id, max_pages=2)
            valid_count = 0
            for r in records:
                # Schema validation & normalization
                try:
                    ts = r.get("period", {}).get("datetimeFrom", {}).get("utc") or r.get("datetime", {}).get("utc")
                    val = r.get("value")
                    if ts is None or val is None or val < 0:
                        rejected_records_count += 1
                        continue

                    new_rows.append({
                        "station": station_name,
                        "sensor_id": str(sensor_id),
                        "timestamp": pd.to_datetime(ts, utc=True),
                        "parameter": "pm25",
                        "value": float(val),
                        "unit": r.get("parameter", {}).get("units", "µg/m³"),
                    })
                    valid_count += 1
                except Exception:
                    rejected_records_count += 1

            sensor_stats[station_name] = {"raw_fetched": len(records), "valid_parsed": valid_count}

        if new_rows:
            fetched_df = pd.DataFrame(new_rows)

            if not existing_df.empty:
                # Deduplicate based on station and timestamp
                combined_df = pd.concat([existing_df, fetched_df], ignore_index=True)
                combined_df["timestamp"] = pd.to_datetime(combined_df["timestamp"], utc=True)
                combined_df = combined_df.drop_duplicates(subset=["station", "timestamp"], keep="last")
            else:
                combined_df = fetched_df

            combined_df = combined_df.sort_values(["station", "timestamp"]).reset_index(drop=True)
            new_records_count = len(combined_df) - len(existing_df) if not existing_df.empty else len(combined_df)

            # Persist updated dataset safely
            AIR_QUALITY_FILE.parent.mkdir(parents=True, exist_ok=True)
            combined_df.to_parquet(AIR_QUALITY_FILE, index=False)
            total_observations = len(combined_df)
            latest_observation_ts = combined_df["timestamp"].max().isoformat()
        else:
            total_observations = len(existing_df) if not existing_df.empty else 0
            latest_observation_ts = existing_df["timestamp"].max().isoformat() if not existing_df.empty else None

        duration = time.time() - start_time
        summary = {
            "status": "success",
            "ingestion_timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
            "execution_duration_sec": round(duration, 3),
            "new_records_added": new_records_count,
            "rejected_records": rejected_records_count,
            "total_observations": total_observations,
            "latest_observation_timestamp": latest_observation_ts,
            "sensor_stats": sensor_stats,
        }

        # Write to ingestion history
        history = []
        if self.history_file.exists():
            try:
                history = json.loads(self.history_file.read_text(encoding="utf-8"))
            except Exception:
                history = []
        history.append(summary)
        # Keep last 50 ingestion logs
        self.history_file.write_text(json.dumps(history[-50:], indent=2), encoding="utf-8")

        logger.info(f"Ingestion completed: {new_records_count} new records added. Total: {total_observations}")
        return summary

    def get_ingestion_status(self) -> Dict[str, Any]:
        if not AIR_QUALITY_FILE.exists():
            return {
                "status": "no_data",
                "total_observations": 0,
                "latest_observation_timestamp": None,
                "last_ingestion_summary": None,
            }

        try:
            df = pd.read_parquet(AIR_QUALITY_FILE)
            history = []
            if self.history_file.exists():
                history = json.loads(self.history_file.read_text(encoding="utf-8"))

            last_summary = history[-1] if history else None

            return {
                "status": "healthy" if len(df) > 0 else "empty",
                "total_observations": len(df),
                "stations_count": int(df["station"].nunique()),
                "data_period": {
                    "start": df["timestamp"].min().isoformat() if not df.empty else None,
                    "end": df["timestamp"].max().isoformat() if not df.empty else None,
                },
                "latest_observation_timestamp": df["timestamp"].max().isoformat() if not df.empty else None,
                "last_ingestion_summary": last_summary,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
