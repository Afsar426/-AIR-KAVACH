import time
import os
from typing import Dict, Any, List, Optional
import requests
from src.utils.logger import get_logger
from src.ingestion.adapters.base_adapter import BaseProviderAdapter, NormalizedRecord

logger = get_logger("openaq_adapter")


class OpenAQAdapter(BaseProviderAdapter):
    """
    Adapter for OpenAQ API v3.
    Provides observed ambient air quality monitoring (CAAQMS) measurements.
    """

    BASE_URL = "https://api.openaq.org/v3"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(provider_id="openaq_v3", display_name="OpenAQ v3 API", priority=1)
        self.api_key = api_key or os.getenv("OPENAQ_API_KEY", "")
        self.headers = {"X-API-Key": self.api_key} if self.api_key else {}

    def health_check(self) -> Dict[str, Any]:
        """Checks OpenAQ v3 API connectivity."""
        try:
            url = f"{self.BASE_URL}/countries"
            resp = requests.get(url, headers=self.headers, params={"limit": 1}, timeout=10)
            if resp.ok:
                return {
                    "provider": self.provider_id,
                    "status": "connected",
                    "authenticated": bool(self.api_key),
                    "latency_ms": int(resp.elapsed.total_seconds() * 1000),
                    "message": "OpenAQ v3 API reachable",
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
                "message": "Failed to connect to OpenAQ v3 API",
            }

    def fetch_records(
        self,
        sensor_id: Optional[int] = None,
        location_id: Optional[int] = None,
        station_name: Optional[str] = None,
        city: Optional[str] = None,
        datetime_from: Optional[str] = None,
        datetime_to: Optional[str] = None,
        max_pages: int = 2,
    ) -> List[NormalizedRecord]:
        """
        Fetches measurements and normalizes them into NormalizedRecord.
        Handles rate limiting, pagination, and missing fields.
        """
        if not sensor_id and not location_id:
            logger.warning("Neither sensor_id nor location_id provided to OpenAQAdapter")
            return []

        url = f"{self.BASE_URL}/sensors/{sensor_id}/measurements" if sensor_id else f"{self.BASE_URL}/locations/{location_id}/measurements"
        records: List[NormalizedRecord] = []
        page = 1

        while page <= max_pages:
            params: Dict[str, Any] = {"limit": 1000, "page": page}
            if datetime_from:
                params["datetime_from"] = datetime_from
            if datetime_to:
                params["datetime_to"] = datetime_to

            try:
                resp = requests.get(url, headers=self.headers, params=params, timeout=25)
                if resp.status_code == 429:
                    logger.warning("OpenAQ rate limit hit (429). Backing off 3s...")
                    time.sleep(3)
                    continue

                if not resp.ok:
                    logger.error(f"OpenAQ request failed ({resp.status_code}): {resp.text[:200]}")
                    break

                data = resp.json()
                raw_results = data.get("results", [])
                if not raw_results:
                    break

                for r in raw_results:
                    try:
                        # Extract timestamps safely
                        period = r.get("period", {})
                        ts_utc = (
                            period.get("datetimeFrom", {}).get("utc")
                            or period.get("datetimeTo", {}).get("utc")
                            or r.get("datetime", {}).get("utc")
                        )
                        val = r.get("value")
                        if ts_utc is None or val is None:
                            continue

                        # Extract parameter and unit
                        param_obj = r.get("parameter", {})
                        param_name = param_obj.get("name", "pm25").lower()
                        unit_str = param_obj.get("units", "µg/m³")

                        rec = NormalizedRecord(
                            provider_id=self.provider_id,
                            data_type="observed",
                            timestamp_utc=ts_utc,
                            station_id=str(sensor_id or location_id),
                            station_name=station_name or f"Sensor-{sensor_id}",
                            city=city,
                            parameter=param_name,
                            value=float(val),
                            unit=unit_str,
                            quality_flag="valid" if float(val) >= 0 else "invalid",
                            quality_reason=None if float(val) >= 0 else "Negative concentration value",
                            provenance={"raw_id": r.get("id"), "sensor_id": sensor_id},
                        )
                        records.append(rec)
                    except Exception as err:
                        logger.debug(f"Failed to normalize OpenAQ measurement: {err}")

                if len(raw_results) < 1000:
                    break
                page += 1
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Exception during OpenAQ fetch: {e}")
                break

        return records
