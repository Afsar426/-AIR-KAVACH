from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import hashlib
from dotenv import load_dotenv

load_dotenv()


class NormalizedRecord(BaseModel):
    """
    Canonical normalized schema for environmental, meteorological,
    satellite, and industrial emission records across all data providers.
    """
    provider_id: str
    data_type: str = Field(..., description="'observed' | 'modeled' | 'satellite' | 'cems' | 'derived'")
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp of the observation")
    retrieval_timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp when AIR KAVACH retrieved this record"
    )
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    state_ut: Optional[str] = None
    country: str = "IN"
    parameter: str = Field(..., description="Parameter code, e.g. pm25, wind_direction_10m, frp")
    value: float
    unit: str
    quality_flag: str = Field(default="valid", description="'valid' | 'suspect' | 'invalid' | 'stale'")
    quality_reason: Optional[str] = None
    record_id: Optional[str] = None
    is_test: bool = Field(default=False, description="Flag explicitly indicating test or synthetic record")
    environment: str = Field(default="production", description="'production' | 'test' | 'staging'")
    provenance: Dict[str, Any] = Field(default_factory=dict)

    def generate_record_id(self) -> str:
        """Computes deterministic hash-based primary record identifier."""
        raw_key = f"{self.provider_id}:{self.station_id or self.station_name}:{self.parameter}:{self.timestamp_utc}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]

    def model_post_init(self, __context: Any) -> None:
        if not self.record_id:
            self.record_id = self.generate_record_id()


class BaseProviderAdapter(ABC):
    """Abstract interface that all data provider adapters must implement."""

    def __init__(self, provider_id: str, display_name: str, priority: int = 1):
        self.provider_id = provider_id
        self.display_name = display_name
        self.priority = priority

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Verifies API connectivity, credentials, and endpoint availability."""
        pass

    @abstractmethod
    def fetch_records(self, **kwargs) -> List[NormalizedRecord]:
        """Retrieves and normalizes records from the provider."""
        pass
