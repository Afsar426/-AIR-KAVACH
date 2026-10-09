from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np


class CoverageStatus(str, Enum):
    RECENT_DATA_AVAILABLE = "recent_data_available"
    HISTORICAL_DATA_ONLY = "historical_data_only"
    PARTIAL_COVERAGE = "partial_coverage"
    MISSING_METEOROLOGY = "missing_meteorology"
    MISSING_FACILITIES = "missing_facilities"
    INSUFFICIENT_TEMPORAL_OVERLAP = "insufficient_temporal_overlap"
    NO_USABLE_DATA = "no_usable_data"


@dataclass
class GeographicRegion:
    id: str
    name: str
    country: str = "India"
    country_code: str = "IN"
    state_ut: str = ""
    city: str = ""
    district: Optional[str] = None
    industrial_region: Optional[str] = None
    latitude: float = 0.0
    longitude: float = 0.0
    bounding_box: Optional[Tuple[float, float, float, float]] = None  # (min_lat, min_lon, max_lat, max_lon)
    coverage_status: CoverageStatus = CoverageStatus.NO_USABLE_DATA
    coverage_description: str = ""
    available_pollutants: List[str] = field(default_factory=list)
    has_wind_data: bool = False
    has_facilities_data: bool = False
    station_count: int = 0


@dataclass
class StationMetadata:
    station_id: str
    station_name: str
    city: str
    state_ut: str
    country: str = "India"
    latitude: float = 0.0
    longitude: float = 0.0
    source_network: str = "OpenAQ / CPCB"
    elevation_m: Optional[float] = None
    active_pollutants: List[str] = field(default_factory=lambda: ["pm25"])
    is_operational: bool = True


# Canonical India Geographic Registry
REGIONS_REGISTRY: Dict[str, GeographicRegion] = {
    "in-mp-indore": GeographicRegion(
        id="in-mp-indore",
        name="Indore Metropolitan Area",
        country="India",
        country_code="IN",
        state_ut="Madhya Pradesh",
        city="Indore",
        district="Indore",
        industrial_region="Pithampur / Sanwer Road Industrial Belt",
        latitude=22.7196,
        longitude=75.8577,
        bounding_box=(22.6000, 75.7500, 22.8200, 75.9500),
        coverage_status=CoverageStatus.RECENT_DATA_AVAILABLE,
        coverage_description="Full high-frequency September 2026 PM2.5, aligned weather observations, 26 candidate industrial facilities, and 2024 daily reference baseline.",
        available_pollutants=["pm25", "pm10", "no2", "so2", "co"],
        has_wind_data=True,
        has_facilities_data=True,
        station_count=4,
    ),
    "in-dl-delhi": GeographicRegion(
        id="in-dl-delhi",
        name="National Capital Territory of Delhi",
        country="India",
        country_code="IN",
        state_ut="Delhi",
        city="Delhi",
        district="Central Delhi",
        industrial_region="Okhla / Mayapuri / Bawana Industrial Areas",
        latitude=28.6139,
        longitude=77.2090,
        bounding_box=(28.4000, 76.8500, 28.9000, 77.4000),
        coverage_status=CoverageStatus.NO_USABLE_DATA,
        coverage_description="Geographic boundary and station metadata registered. Operational observations awaiting scheduled ingestion feed.",
        available_pollutants=["pm25", "pm10"],
        has_wind_data=False,
        has_facilities_data=False,
        station_count=0,
    ),
    "in-mh-mumbai": GeographicRegion(
        id="in-mh-mumbai",
        name="Mumbai Metropolitan Region",
        country="India",
        country_code="IN",
        state_ut="Maharashtra",
        city="Mumbai",
        district="Mumbai City",
        industrial_region="Thane-Belapur / Chembur Industrial Corridor",
        latitude=19.0760,
        longitude=72.8777,
        bounding_box=(18.8500, 72.7500, 19.3500, 73.1500),
        coverage_status=CoverageStatus.NO_USABLE_DATA,
        coverage_description="Metropolitan region configured. No active local parquet cache currently stored.",
        available_pollutants=["pm25"],
        has_wind_data=False,
        has_facilities_data=False,
        station_count=0,
    ),
    "in-gj-ahmedabad": GeographicRegion(
        id="in-gj-ahmedabad",
        name="Ahmedabad Urban Area",
        country="India",
        country_code="IN",
        state_ut="Gujarat",
        city="Ahmedabad",
        district="Ahmedabad",
        industrial_region="Vatva / Naroda Industrial Estate",
        latitude=23.0225,
        longitude=72.5714,
        bounding_box=(22.9000, 72.4500, 23.1500, 72.7000),
        coverage_status=CoverageStatus.NO_USABLE_DATA,
        coverage_description="Candidate industrial hub mapped. Awaiting OpenAQ sensor ingest.",
        available_pollutants=[],
        has_wind_data=False,
        has_facilities_data=False,
        station_count=0,
    ),
    "in-ka-bengaluru": GeographicRegion(
        id="in-ka-bengaluru",
        name="Bengaluru Urban",
        country="India",
        country_code="IN",
        state_ut="Karnataka",
        city="Bengaluru",
        district="Bengaluru Urban",
        industrial_region="Peenya Industrial Complex",
        latitude=12.9716,
        longitude=77.5946,
        bounding_box=(12.8000, 77.4500, 13.1500, 77.7500),
        coverage_status=CoverageStatus.NO_USABLE_DATA,
        coverage_description="Region metadata registered. No observations currently loaded.",
        available_pollutants=[],
        has_wind_data=False,
        has_facilities_data=False,
        station_count=0,
    ),
    "in-up-kanpur": GeographicRegion(
        id="in-up-kanpur",
        name="Kanpur Industrial Belt",
        country="India",
        country_code="IN",
        state_ut="Uttar Pradesh",
        city="Kanpur",
        district="Kanpur Nagar",
        industrial_region="Panki / Fazalganj Industrial Area",
        latitude=26.4499,
        longitude=80.3319,
        bounding_box=(26.3500, 80.2000, 26.5500, 80.4500),
        coverage_status=CoverageStatus.NO_USABLE_DATA,
        coverage_description="Candidate high-emission corridor defined. Data feed pending.",
        available_pollutants=[],
        has_wind_data=False,
        has_facilities_data=False,
        station_count=0,
    ),
}

# Monitoring Stations Registry
STATIONS_REGISTRY: Dict[str, StationMetadata] = {
    "Residency": StationMetadata(
        station_id="IND-RES-01",
        station_name="Residency",
        city="Indore",
        state_ut="Madhya Pradesh",
        country="India",
        latitude=22.7084,
        longitude=75.8815,
        source_network="OpenAQ / CPCB",
        active_pollutants=["pm25"],
        is_operational=True,
    ),
    "Regional Park": StationMetadata(
        station_id="IND-REG-02",
        station_name="Regional Park",
        city="Indore",
        state_ut="Madhya Pradesh",
        country="India",
        latitude=22.6780,
        longitude=75.8559,
        source_network="OpenAQ / CPCB",
        active_pollutants=["pm25"],
        is_operational=True,
    ),
    "Airport": StationMetadata(
        station_id="IND-AIR-03",
        station_name="Airport",
        city="Indore",
        state_ut="Madhya Pradesh",
        country="India",
        latitude=22.7289,
        longitude=75.8076,
        source_network="OpenAQ / CPCB",
        active_pollutants=["pm25"],
        is_operational=True,
    ),
    "Maguda": StationMetadata(
        station_id="IND-MAG-04",
        station_name="Maguda",
        city="Indore",
        state_ut="Madhya Pradesh",
        country="India",
        latitude=22.7524,
        longitude=75.8872,
        source_network="OpenAQ / CPCB",
        active_pollutants=["pm25"],
        is_operational=True,
    ),
}


class GeoRegistryService:
    @staticmethod
    def get_all_regions() -> List[Dict[str, Any]]:
        return [
            {
                "id": r.id,
                "name": r.name,
                "country": r.country,
                "state_ut": r.state_ut,
                "city": r.city,
                "district": r.district,
                "industrial_region": r.industrial_region,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "bounding_box": r.bounding_box,
                "coverage_status": r.coverage_status.value,
                "coverage_description": r.coverage_description,
                "available_pollutants": r.available_pollutants,
                "has_wind_data": r.has_wind_data,
                "has_facilities_data": r.has_facilities_data,
                "station_count": r.station_count,
            }
            for r in REGIONS_REGISTRY.values()
        ]

    @staticmethod
    def get_region_by_id(region_id: str) -> Optional[GeographicRegion]:
        return REGIONS_REGISTRY.get(region_id.lower())

    @staticmethod
    def get_stations(
        city: Optional[str] = None,
        state_ut: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        for s in STATIONS_REGISTRY.values():
            if city and s.city.lower() != city.lower():
                continue
            if state_ut and s.state_ut.lower() != state_ut.lower():
                continue
            results.append({
                "station_id": s.station_id,
                "station_name": s.station_name,
                "city": s.city,
                "state_ut": s.state_ut,
                "country": s.country,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "source_network": s.source_network,
                "active_pollutants": s.active_pollutants,
                "is_operational": s.is_operational,
            })
        return results

    @staticmethod
    def match_region(
        country: Optional[str] = None,
        state_ut: Optional[str] = None,
        city: Optional[str] = None,
        station: Optional[str] = None,
    ) -> Tuple[Optional[GeographicRegion], CoverageStatus]:
        """Resolves region and assesses actual data coverage without Indore-leakage."""
        if station:
            st = STATIONS_REGISTRY.get(station)
            if st:
                # Match to Indore
                return REGIONS_REGISTRY.get("in-mp-indore"), CoverageStatus.RECENT_DATA_AVAILABLE
            return None, CoverageStatus.NO_USABLE_DATA

        if city:
            c_low = city.lower()
            if "indore" in c_low:
                return REGIONS_REGISTRY.get("in-mp-indore"), CoverageStatus.RECENT_DATA_AVAILABLE
            for reg in REGIONS_REGISTRY.values():
                if reg.city.lower() == c_low:
                    return reg, reg.coverage_status
            return None, CoverageStatus.NO_USABLE_DATA

        if state_ut:
            st_low = state_ut.lower()
            if "madhya pradesh" in st_low or st_low == "mp":
                return REGIONS_REGISTRY.get("in-mp-indore"), CoverageStatus.RECENT_DATA_AVAILABLE
            for reg in REGIONS_REGISTRY.values():
                if reg.state_ut.lower() == st_low:
                    return reg, reg.coverage_status
            return None, CoverageStatus.NO_USABLE_DATA

        # Default national scope
        return None, CoverageStatus.PARTIAL_COVERAGE

    @staticmethod
    def is_within_bounding_box(
        lat: float,
        lon: float,
        bbox: Tuple[float, float, float, float],
    ) -> bool:
        min_lat, min_lon, max_lat, max_lon = bbox
        return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon
