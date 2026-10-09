from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import requests
from src.utils.logger import get_logger
from src.ingestion.adapters.base_adapter import BaseProviderAdapter, NormalizedRecord

logger = get_logger("openmeteo_weather_adapter")


class OpenMeteoWeatherAdapter(BaseProviderAdapter):
    """
    Adapter for Open-Meteo Historical & Current Weather API (ERA5 Reanalysis & Measurements).
    Retrieves hourly 10m wind speed, wind direction (FROM convention), and temperature.
    """

    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self):
        super().__init__(provider_id="openmeteo_weather", display_name="Open-Meteo Weather API", priority=2)

    def health_check(self) -> Dict[str, Any]:
        """Checks Open-Meteo weather endpoint connectivity."""
        try:
            params = {"latitude": 22.7126, "longitude": 75.8753, "hourly": "wind_speed_10m", "forecast_days": 1}
            resp = requests.get(self.FORECAST_URL, params=params, timeout=10)
            if resp.ok:
                return {
                    "provider": self.provider_id,
                    "status": "connected",
                    "authenticated": True,  # Open tier
                    "latency_ms": int(resp.elapsed.total_seconds() * 1000),
                    "message": "Open-Meteo Weather API reachable (free tier)",
                }
            elif resp.status_code == 429:
                # Try historical archive endpoint fallback
                archive_params = {"latitude": 22.7126, "longitude": 75.8753, "start_date": "2026-09-01", "end_date": "2026-09-01", "hourly": "wind_speed_10m"}
                arch_resp = requests.get(self.ARCHIVE_URL, params=archive_params, timeout=10)
                if arch_resp.ok:
                    return {
                        "provider": self.provider_id,
                        "status": "connected",
                        "authenticated": True,
                        "latency_ms": int(arch_resp.elapsed.total_seconds() * 1000),
                        "message": "Open-Meteo Weather Archive reachable (forecast tier rate-limited, historical active)",
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
                "message": "Failed to reach Open-Meteo Weather API",
            }

    def fetch_records(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        station_name: Optional[str] = None,
        city: Optional[str] = None,
    ) -> List[NormalizedRecord]:
        """
        Fetches hourly historical wind and weather conditions for given coordinates and date range.
        Format for dates: 'YYYY-MM-DD'.
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "wind_speed_10m,wind_direction_10m,temperature_2m,relative_humidity_2m",
            "timezone": "UTC",
        }

        records: List[NormalizedRecord] = []
        try:
            resp = requests.get(self.ARCHIVE_URL, params=params, timeout=30)
            if not resp.ok:
                # Try fallback to forecast URL if dates are recent
                resp = requests.get(self.FORECAST_URL, params=params, timeout=30)

            if not resp.ok:
                logger.error(f"Open-Meteo weather fetch failed ({resp.status_code}): {resp.text[:200]}")
                return []

            data = resp.json()
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            w_speeds = hourly.get("wind_speed_10m", [])
            w_dirs = hourly.get("wind_direction_10m", [])
            temps = hourly.get("temperature_2m", [])

            for i, t_str in enumerate(times):
                try:
                    # ISO 8601 UTC timestamp
                    ts_utc = f"{t_str}:00Z" if len(t_str) == 16 else f"{t_str}Z"

                    # 1. Wind Direction (FROM convention: 0-360)
                    if i < len(w_dirs) and w_dirs[i] is not None:
                        w_dir = float(w_dirs[i])
                        records.append(
                            NormalizedRecord(
                                provider_id=self.provider_id,
                                data_type="observed",
                                timestamp_utc=ts_utc,
                                station_id=f"WTH-{latitude:.2f}-{longitude:.2f}",
                                station_name=station_name or "Meteorological Station",
                                latitude=latitude,
                                longitude=longitude,
                                city=city,
                                parameter="wind_direction_10m",
                                value=w_dir,
                                unit="degrees",
                                quality_flag="valid" if 0 <= w_dir < 360 else "invalid",
                                provenance={"convention": "FROM True North"},
                            )
                        )

                    # 2. Wind Speed (m/s converted if km/h)
                    if i < len(w_speeds) and w_speeds[i] is not None:
                        # Open-Meteo default is km/h, convert to m/s
                        speed_mps = round(float(w_speeds[i]) / 3.6, 2)
                        records.append(
                            NormalizedRecord(
                                provider_id=self.provider_id,
                                data_type="observed",
                                timestamp_utc=ts_utc,
                                station_id=f"WTH-{latitude:.2f}-{longitude:.2f}",
                                station_name=station_name or "Meteorological Station",
                                latitude=latitude,
                                longitude=longitude,
                                city=city,
                                parameter="wind_speed_10m",
                                value=speed_mps,
                                unit="m/s",
                                quality_flag="valid" if speed_mps >= 0 else "invalid",
                                provenance={"converted_from_kmh": float(w_speeds[i])},
                            )
                        )

                    # 3. Ambient Temperature (°C)
                    if i < len(temps) and temps[i] is not None:
                        records.append(
                            NormalizedRecord(
                                provider_id=self.provider_id,
                                data_type="observed",
                                timestamp_utc=ts_utc,
                                station_id=f"WTH-{latitude:.2f}-{longitude:.2f}",
                                station_name=station_name or "Meteorological Station",
                                latitude=latitude,
                                longitude=longitude,
                                city=city,
                                parameter="temperature_2m",
                                value=float(temps[i]),
                                unit="°C",
                                quality_flag="valid",
                            )
                        )

                except Exception as err:
                    logger.debug(f"Error parsing weather row: {err}")

        except Exception as e:
            logger.error(f"Exception during Open-Meteo weather fetch: {e}")

        return records
