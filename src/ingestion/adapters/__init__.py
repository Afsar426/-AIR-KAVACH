from src.ingestion.adapters.base_adapter import BaseProviderAdapter, NormalizedRecord
from src.ingestion.adapters.openaq_adapter import OpenAQAdapter
from src.ingestion.adapters.cpcb_adapter import CPCBAdapter
from src.ingestion.adapters.openmeteo_weather_adapter import OpenMeteoWeatherAdapter
from src.ingestion.adapters.openmeteo_airquality_adapter import OpenMeteoAirQualityAdapter
from src.ingestion.adapters.nasa_firms_adapter import NASAFIRMSAdapter
from src.ingestion.adapters.cems_adapter import CEMSAdapter

__all__ = [
    "BaseProviderAdapter",
    "NormalizedRecord",
    "OpenAQAdapter",
    "CPCBAdapter",
    "OpenMeteoWeatherAdapter",
    "OpenMeteoAirQualityAdapter",
    "NASAFIRMSAdapter",
    "CEMSAdapter",
]
