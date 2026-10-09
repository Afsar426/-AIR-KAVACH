import os
import csv
import io
from typing import Dict, Any, List, Optional
import requests
from src.utils.logger import get_logger
from src.ingestion.adapters.base_adapter import BaseProviderAdapter, NormalizedRecord

logger = get_logger("nasa_firms_adapter")


class NASAFIRMSAdapter(BaseProviderAdapter):
    """
    Adapter for NASA FIRMS (Fire Information for Resource Management System).
    Provides satellite-detected thermal anomalies (MODIS & VIIRS) for detecting
    biomass, agricultural residue, and stubble burning that could confound
    industrial point-source attribution.
    """

    BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

    def __init__(self, map_key: Optional[str] = None):
        super().__init__(provider_id="nasa_firms", display_name="NASA FIRMS Satellite Thermal Anomalies", priority=3)
        self.map_key = map_key or os.getenv("NASA_FIRMS_MAP_KEY", "")

    def health_check(self) -> Dict[str, Any]:
        """Checks NASA FIRMS API availability."""
        if not self.map_key:
            return {
                "provider": self.provider_id,
                "status": "configured_pending_key",
                "authenticated": False,
                "data_type": "satellite",
                "message": "NASA_FIRMS_MAP_KEY not configured. Register at firms.modaps.eosdis.nasa.gov for free map key.",
            }
        try:
            # Ping with minimal query bounding box (1x1 degree)
            url = f"{self.BASE_URL}/{self.map_key}/VIIRS_SNPP_NRT/75,22,76,23/1"
            resp = requests.get(url, timeout=10)
            if resp.ok:
                return {
                    "provider": self.provider_id,
                    "status": "connected",
                    "authenticated": True,
                    "data_type": "satellite",
                    "latency_ms": int(resp.elapsed.total_seconds() * 1000),
                    "message": "NASA FIRMS API active (VIIRS NRT)",
                }
            return {
                "provider": self.provider_id,
                "status": "degraded",
                "status_code": resp.status_code,
                "message": resp.text[:200],
            }
        except Exception as e:
            return {
                "provider": self.provider_id,
                "status": "unavailable",
                "error": str(e),
                "message": "Failed to reach NASA FIRMS API",
            }

    def fetch_records(
        self,
        bounding_box: tuple[float, float, float, float],  # (min_lon, min_lat, max_lon, max_lat)
        day_range: int = 1,
        source: str = "VIIRS_SNPP_NRT",
    ) -> List[NormalizedRecord]:
        """
        Retrieves active fire / thermal anomaly detections within bounding box.
        Format bounding box: (min_lon, min_lat, max_lon, max_lat).
        """
        if not self.map_key:
            logger.info("NASA_FIRMS_MAP_KEY not set; skipping live FIRMS query.")
            return []

        min_lon, min_lat, max_lon, max_lat = bounding_box
        area_str = f"{min_lon:.2f},{min_lat:.2f},{max_lon:.2f},{max_lat:.2f}"
        url = f"{self.BASE_URL}/{self.map_key}/{source}/{area_str}/{day_range}"

        records: List[NormalizedRecord] = []
        try:
            resp = requests.get(url, timeout=25)
            if not resp.ok:
                logger.error(f"NASA FIRMS fetch failed ({resp.status_code}): {resp.text[:200]}")
                return []

            reader = csv.DictReader(io.StringIO(resp.text))
            for row in reader:
                try:
                    lat = float(row.get("latitude", 0))
                    lon = float(row.get("longitude", 0))
                    frp = float(row.get("frp", 0))  # Fire Radiative Power (MW)
                    acq_date = row.get("acq_date")
                    acq_time = row.get("acq_time", "0000").zfill(4)
                    hh = acq_time[:2]
                    mm = acq_time[2:]
                    ts_utc = f"{acq_date}T{hh}:{mm}:00Z"

                    records.append(
                        NormalizedRecord(
                            provider_id=self.provider_id,
                            data_type="satellite",
                            timestamp_utc=ts_utc,
                            station_id=f"FIRE-{lat:.3f}-{lon:.3f}",
                            station_name=f"Thermal Anomaly ({source})",
                            latitude=lat,
                            longitude=lon,
                            parameter="fire_radiative_power",
                            value=frp,
                            unit="MW",
                            quality_flag="valid",
                            provenance={
                                "confidence": row.get("confidence"),
                                "bright_ti4": row.get("bright_ti4"),
                                "satellite": row.get("satellite"),
                            },
                        )
                    )
                except Exception as err:
                    logger.debug(f"Error parsing FIRMS row: {err}")

        except Exception as e:
            logger.error(f"Exception during NASA FIRMS request: {e}")

        return records
