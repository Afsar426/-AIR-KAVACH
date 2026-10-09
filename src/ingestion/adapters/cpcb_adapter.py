import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import requests
from src.utils.logger import get_logger
from src.ingestion.adapters.base_adapter import BaseProviderAdapter, NormalizedRecord

logger = get_logger("cpcb_adapter")


class CPCBAdapter(BaseProviderAdapter):
    """
    Adapter for Central Pollution Control Board (CPCB) CAAQMS data via data.gov.in.
    Endpoint: Real-Time Air Quality Index for Various Cities across India.
    """

    RESOURCE_ID = "3b0139f6-f772-47fa-8232-3228577ac712"
    BASE_URL = "https://api.data.gov.in/resource"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(provider_id="cpcb_datagov", display_name="CPCB / data.gov.in", priority=1)
        self.api_key = api_key or os.getenv("DATAGOVIN_API_KEY", "")

    def health_check(self) -> Dict[str, Any]:
        """Checks data.gov.in CPCB resource availability."""
        if not self.api_key:
            return {
                "provider": self.provider_id,
                "status": "configured_pending_key",
                "authenticated": False,
                "message": "DATAGOVIN_API_KEY not set. Set key in .env or use mock/offline feeds.",
            }
        try:
            url = f"{self.BASE_URL}/{self.RESOURCE_ID}"
            params = {"api-key": self.api_key, "format": "json", "limit": 1}
            resp = requests.get(url, params=params, timeout=10)
            if resp.ok:
                return {
                    "provider": self.provider_id,
                    "status": "connected",
                    "authenticated": True,
                    "latency_ms": int(resp.elapsed.total_seconds() * 1000),
                    "message": "CPCB / data.gov.in API active",
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
                "message": "Failed to reach data.gov.in",
            }

    def fetch_records(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 500,
    ) -> List[NormalizedRecord]:
        """
        Fetches official CPCB station observations from data.gov.in.
        """
        if not self.api_key:
            logger.info("DATAGOVIN_API_KEY not provided; skipping live CPCB fetch.")
            return []

        url = f"{self.BASE_URL}/{self.RESOURCE_ID}"
        params: Dict[str, Any] = {
            "api-key": self.api_key,
            "format": "json",
            "limit": limit,
        }
        if city:
            params["filters[city]"] = city
        if state:
            params["filters[state]"] = state

        records: List[NormalizedRecord] = []
        try:
            resp = requests.get(url, params=params, timeout=25)
            if not resp.ok:
                logger.error(f"CPCB fetch failed ({resp.status_code}): {resp.text[:200]}")
                return []

            data = resp.json()
            raw_records = data.get("records", [])

            for r in raw_records:
                try:
                    # Parse timestamp (format e.g., '21-09-2026 15:00:00' or ISO)
                    raw_ts = r.get("last_update")
                    if not raw_ts:
                        continue
                    try:
                        dt = datetime.strptime(raw_ts, "%d-%m-%Y %H:%M:%S").replace(tzinfo=timezone.utc)
                        ts_utc = dt.isoformat()
                    except Exception:
                        ts_utc = pd.to_datetime(raw_ts, utc=True).isoformat()

                    val = r.get("pollutant_avg") or r.get("pollutant_max")
                    if val is None or float(val) < 0:
                        continue

                    # Standardize pollutant parameter
                    p_raw = str(r.get("pollutant_id", "pm25")).lower().replace(".", "")
                    param_name = "pm25" if "pm2" in p_raw else ("pm10" if "pm10" in p_raw else p_raw)

                    rec = NormalizedRecord(
                        provider_id=self.provider_id,
                        data_type="observed",
                        timestamp_utc=ts_utc,
                        station_id=f"CPCB-{r.get('station', 'STN')[:12]}",
                        station_name=r.get("station"),
                        city=r.get("city"),
                        state_ut=r.get("state"),
                        country="IN",
                        parameter=param_name,
                        value=float(val),
                        unit="µg/m³",
                        quality_flag="valid",
                        provenance={"raw": r},
                    )
                    records.append(rec)
                except Exception as row_err:
                    logger.debug(f"Error parsing CPCB record: {row_err}")

        except Exception as e:
            logger.error(f"Exception during CPCB request: {e}")

        return records
