from typing import Dict, Any, List, Optional
import requests
from src.utils.logger import get_logger
from src.ingestion.adapters.base_adapter import BaseProviderAdapter, NormalizedRecord

logger = get_logger("openmeteo_airquality_adapter")


class OpenMeteoAirQualityAdapter(BaseProviderAdapter):
    """
    Adapter for Open-Meteo Modeled Air Quality API (Copernicus CAMS & ECMWF Chemical Reanalysis).
    CRITICAL: All records from this adapter are explicitly labeled `data_type: 'modeled'`,
    distinguishing numerical grid simulations from ground CAAQMS sensor observations.
    """

    BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

    def __init__(self):
        super().__init__(
            provider_id="openmeteo_airquality_model",
            display_name="Open-Meteo Modeled AQ (CAMS)",
            priority=2,
        )

    def health_check(self) -> Dict[str, Any]:
        """Checks Open-Meteo Modeled AQ endpoint connectivity."""
        try:
            params = {"latitude": 22.7126, "longitude": 75.8753, "hourly": "pm2_5", "forecast_days": 1}
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            if resp.ok:
                return {
                    "provider": self.provider_id,
                    "status": "connected",
                    "authenticated": True,
                    "data_type": "modeled",
                    "latency_ms": int(resp.elapsed.total_seconds() * 1000),
                    "message": "Open-Meteo Modeled AQ API reachable (CAMS)",
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
                "message": "Failed to reach Open-Meteo Modeled AQ API",
            }

    def fetch_records(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        city: Optional[str] = None,
    ) -> List[NormalizedRecord]:
        """
        Fetches modeled PM2.5, PM10, NO2, SO2 grid estimates for coordinates and date window.
        Dates: 'YYYY-MM-DD'.
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,ozone",
            "timezone": "UTC",
        }

        records: List[NormalizedRecord] = []
        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=30)
            if not resp.ok:
                logger.error(f"Open-Meteo AQ fetch failed ({resp.status_code}): {resp.text[:200]}")
                return []

            data = resp.json()
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            pm25_vals = hourly.get("pm2_5", [])
            pm10_vals = hourly.get("pm10", [])
            no2_vals = hourly.get("nitrogen_dioxide", [])

            for i, t_str in enumerate(times):
                ts_utc = f"{t_str}:00Z" if len(t_str) == 16 else f"{t_str}Z"

                # 1. Modeled PM2.5
                if i < len(pm25_vals) and pm25_vals[i] is not None:
                    records.append(
                        NormalizedRecord(
                            provider_id=self.provider_id,
                            data_type="modeled",  # Strictly distinguished
                            timestamp_utc=ts_utc,
                            station_id=f"MODEL-{latitude:.2f}-{longitude:.2f}",
                            station_name=f"CAMS Model Grid ({latitude:.2f}, {longitude:.2f})",
                            latitude=latitude,
                            longitude=longitude,
                            city=city,
                            parameter="pm25",
                            value=float(pm25_vals[i]),
                            unit="µg/m³",
                            quality_flag="valid",
                            provenance={"model_source": "Copernicus CAMS European Reanalysis"},
                        )
                    )

                # 2. Modeled PM10
                if i < len(pm10_vals) and pm10_vals[i] is not None:
                    records.append(
                        NormalizedRecord(
                            provider_id=self.provider_id,
                            data_type="modeled",
                            timestamp_utc=ts_utc,
                            station_id=f"MODEL-{latitude:.2f}-{longitude:.2f}",
                            station_name=f"CAMS Model Grid ({latitude:.2f}, {longitude:.2f})",
                            latitude=latitude,
                            longitude=longitude,
                            city=city,
                            parameter="pm10",
                            value=float(pm10_vals[i]),
                            unit="µg/m³",
                            quality_flag="valid",
                            provenance={"model_source": "Copernicus CAMS"},
                        )
                    )

                # 3. Modeled NO2
                if i < len(no2_vals) and no2_vals[i] is not None:
                    records.append(
                        NormalizedRecord(
                            provider_id=self.provider_id,
                            data_type="modeled",
                            timestamp_utc=ts_utc,
                            station_id=f"MODEL-{latitude:.2f}-{longitude:.2f}",
                            station_name=f"CAMS Model Grid ({latitude:.2f}, {longitude:.2f})",
                            latitude=latitude,
                            longitude=longitude,
                            city=city,
                            parameter="no2",
                            value=float(no2_vals[i]),
                            unit="µg/m³",
                            quality_flag="valid",
                            provenance={"model_source": "Copernicus CAMS"},
                        )
                    )

        except Exception as e:
            logger.error(f"Exception during Open-Meteo AQ fetch: {e}")

        return records
