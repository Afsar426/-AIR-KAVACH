import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# API Keys
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Directory Paths
DATA_DIR = PROJECT_ROOT / os.getenv("DATA_DIR", "data")
MODELS_DIR = PROJECT_ROOT / os.getenv("MODELS_DIR", "models")
REPORTS_DIR = PROJECT_ROOT / os.getenv("REPORTS_DIR", "reports")

# File Paths
AIR_QUALITY_FILE = DATA_DIR / "processed" / "air_quality" / "air_quality.parquet"
EVENTS_FILE = DATA_DIR / "processed" / "events" / "pollution_events.parquet"
FACTORIES_FILE = DATA_DIR / "processed" / "factories" / "factories_clean.parquet"
WIND_FILE = DATA_DIR / "processed" / "weather" / "wind.parquet"
DISTANCES_FILE = DATA_DIR / "features" / "sensor_factory_distances.parquet"
ATTRIBUTION_FILE = DATA_DIR / "features" / "event_factory_attribution.parquet"
CONFIDENCE_FILE = DATA_DIR / "features" / "event_factory_confidence.parquet"
EVENT_WIND_FILE = DATA_DIR / "features" / "pollution_events_with_wind.parquet"
ML_SCORES_FILE = DATA_DIR / "features" / "ml_anomaly_scores.parquet"
MAP_FILE = PROJECT_ROOT / "backend" / "map_data.json"

ISOLATION_FOREST_MODEL_DIR = MODELS_DIR / "isolation_forest"
