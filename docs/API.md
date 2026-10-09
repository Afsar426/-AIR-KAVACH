# AIR KAVACH - API Specification

The FastAPI backend runs on port 8000 by default and provides interactive OpenAPI documentation at `/docs`.

## Endpoints Summary

- `GET /` - Root status and API documentation URL.
- `GET /health` - System health and file check.
- `GET /api/summary` - Aggregated observation counts, event totals, station list, and scientific caveat.
- `GET /api/observations` - Paginated air quality observations feed with station filtering.
- `GET /api/events` - Paginated list of detected pollution events.
- `GET /api/events/{event_id}` - Event details.
- `GET /api/attribution/{event_id}` - Ranked candidate industrial facilities for a specific event.
- `GET /api/evidence/{event_id}` - Evidence chain and wind metadata.
- `GET /api/map` - Geospatial map JSON containing station coordinates, factory markers, and event epicenters.
- `GET /api/ingestion/status` - Live OpenAQ ingestion status.
- `POST /api/ingestion/run` - Trigger incremental ingestion cycle.
- `GET /api/models/status` - Isolation Forest model metadata and serialized status.
- `POST /api/models/train` - Trigger Isolation Forest model training and joblib serialization.
- `POST /api/assistant/investigate` - Natural language AI investigation assistant query endpoint.
- `POST /api/reports` - Generate structured JSON/PDF investigation report.
