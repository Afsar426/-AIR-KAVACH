from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field


# 1. Geographic Region Schema
class GeographicRegionSchema(BaseModel):
    id: str
    name: str
    country: str = "India"
    country_code: str = "IN"
    state_ut: str
    city: str
    district: Optional[str] = None
    industrial_region: Optional[str] = None
    latitude: float
    longitude: float
    bounding_box: Optional[Tuple[float, float, float, float]] = None
    coverage_status: str
    coverage_description: str
    available_pollutants: List[str] = Field(default_factory=list)
    has_wind_data: bool = False
    has_facilities_data: bool = False
    station_count: int = 0


# 2. Monitoring Station Schema
class MonitoringStationSchema(BaseModel):
    station_id: str
    station_name: str
    city: str
    state_ut: str
    country: str = "India"
    latitude: float
    longitude: float
    source_network: str = "OpenAQ / CPCB"
    active_pollutants: List[str] = Field(default_factory=lambda: ["pm25"])
    is_operational: bool = True


# 3. Observation Record Schema
class ObservationRecord(BaseModel):
    station: str
    sensor_id: Optional[str] = None
    timestamp: str
    parameter: str
    value: float
    unit: str


# 4. Meteorological Observation Schema
class MeteorologicalObservation(BaseModel):
    timestamp: str
    station: str
    wind_direction_deg: Optional[float] = None
    wind_speed_mps: Optional[float] = None
    source_provider: str = "ERA5 / OpenAQ"
    quality_flag: str = "valid"


# 5. Industrial Facility Schema
class IndustrialFacilitySchema(BaseModel):
    factory_id: str
    factory_name: str
    industry_type: Optional[str] = None
    latitude: float
    longitude: float
    operator: Optional[str] = None
    facility_category: Optional[str] = None
    source_candidate: bool = True
    state_ut: str = "Madhya Pradesh"
    city: str = "Indore"


# 6. Pollution Event Schema
class EventRecord(BaseModel):
    event_id: str
    station: str
    start_time: str
    end_time: str
    duration_minutes: float
    peak_pm25: float
    peak_time: Optional[str] = None
    peak_z_score: Optional[float] = None
    mean_pm25: Optional[float] = None
    baseline_mean: Optional[float] = None
    max_z_score: Optional[float] = None
    readings: int
    city: str = "Indore"
    state_ut: str = "Madhya Pradesh"


# 7. Candidate Attribution Record Schema
class CandidateAttributionRecord(BaseModel):
    event_id: str
    station: str
    factory_id: str
    factory_name: str
    facility_category: Optional[str] = None
    peak_pm25: float
    distance_km: float
    distance_score: float
    wind_direction_mean_deg: Optional[float] = None
    wind_speed_mean_mps: Optional[float] = None
    bearing_sensor_to_factory_deg: Optional[float] = None
    wind_alignment: Optional[float] = None
    wind_relationship: Optional[str] = None
    wind_evidence_quality: Optional[str] = None
    attribution_score: float
    relative_likelihood: float
    factory_rank: int
    source_identification_status: str
    evidence_label: str


# 8. Evidence Record Schema
class EvidenceRecord(BaseModel):
    evidence_id: str
    investigation_id: str
    event_id: str
    evidence_type: str
    source_record: str
    geographic_region: str
    source_provider: str
    observation_timestamp: str
    processing_step: str
    algorithm_version: str
    derived_result: Dict[str, Any]
    supporting_interpretation: str
    limitations: List[str] = Field(default_factory=list)


# 9. Ingestion Job Schema
class IngestionJob(BaseModel):
    job_id: str
    provider: str
    geographic_region: str
    start_time: str
    end_time: Optional[str] = None
    status: str
    records_discovered: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    duplicates_ignored: int = 0
    invalid_records_rejected: int = 0
    failure_reason: Optional[str] = None
    data_time_range: Optional[Dict[str, Optional[str]]] = None
    duration_sec: Optional[float] = None


# 10. Model Version & Run Schema
class ModelVersionSchema(BaseModel):
    version: str
    model_type: str
    n_estimators: int
    contamination: float
    random_state: int
    total_training_samples: int
    feature_schema: List[str]
    trained_at: str
    station_summary: Dict[str, Any]
    artifact_file: str


# 11. Execution Trace Schema
class ExecutionTrace(BaseModel):
    request_id: str
    query: str
    task_classification: str
    workflow_steps: List[str]
    selected_tools: List[str]
    data_sources: List[str]
    model_versions: Dict[str, str]
    status: str
    missing_evidence: List[str]
    timestamp: str
    tool_inputs: Optional[Dict[str, Any]] = None
    tool_outputs: Optional[Dict[str, Any]] = None


# 12. Investigation & Report Schema
class InvestigationReportSchema(BaseModel):
    report_id: str
    event_id: str
    generated_at: str
    geographic_scope: str
    event_details: Optional[Dict[str, Any]] = None
    meteorological_evidence: Optional[Dict[str, Any]] = None
    candidate_rankings: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_chain: Optional[Dict[str, Any]] = None
    provenance: Optional[Dict[str, Any]] = None
    limitations: List[str] = Field(default_factory=list)
    investigation_summary: str
    execution_trace: Optional[Dict[str, Any]] = None
