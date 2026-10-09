# AIR KAVACH - Production Deployment & Operations Guide

## 1. System Requirements & Architecture

### Minimum Host Specifications
- **CPU**: 2 vCPUs (x86_64 or ARM64)
- **Memory**: 4 GB RAM minimum (8 GB recommended for multi-station Isolation Forest retraining)
- **Disk**: 10 GB SSD storage
- **Operating Systems**: Linux (Ubuntu 22.04 LTS / Debian 12), Windows 10/11 with WSL2, or macOS 13+
- **Runtimes**:
  - Python: 3.11, 3.12, or 3.13
  - Node.js: 20 LTS, 22 LTS, or 24 Current
  - Docker: 24.0+ and Docker Compose 2.20+

---

## 2. Environment Configuration

Copy the sample environment file to create your local production configuration:
```bash
cp .env.example .env
```

### Environment Variables Reference

| Variable | Default Value | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Backend API bind host interface |
| `PORT` | `8000` | Backend API listen port |
| `ENVIRONMENT` | `production` | Runtime mode (`development`, `staging`, `production`) |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated list of allowed frontend origins |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `DATA_DIR` | `./data` | Path to persistent storage containing raw & processed Parquet files |
| `MODELS_DIR` | `./models` | Path to serialized ML model joblib artifacts |
| `REPORTS_DIR` | `./reports` | Path to persisted investigation reports |
| `OPENAQ_API_KEY` | *(Optional)* | OpenAQ v3 API key for extended rate limits |
| `GEMINI_API_KEY` | *(Optional)* | Google Gemini API key for external LLM augmentation (offline fallback used if omitted) |

---

## 3. Containerized Deployment with Docker Compose

The repository includes a production multi-container setup via `docker-compose.yml`.

### 3.1 Architecture Overview
- **`backend` service**: Python 3.13-slim running FastAPI via Uvicorn. Binds to port `8000`. Volumes are mounted for `./data`, `./models`, and `./reports` to preserve ingested data across container restarts.
- **`frontend` service**: Multi-stage build (Node 24 Alpine builds static Vite assets; Nginx Alpine serves the single-page application). Binds to port `3000`.

### 3.2 Launching the Stack
```bash
# Build and start all services in detached mode
docker-compose up -d --build

# Inspect running containers
docker-compose ps

# Tail logs across all services
docker-compose logs -f
```

### 3.3 Accessing Services
- **Web User Interface**: `http://localhost:3000`
- **FastAPI Backend REST API**: `http://localhost:8000`
- **Interactive OpenAPI Documentation**: `http://localhost:8000/docs`
- **ReDoc API Documentation**: `http://localhost:8000/redoc`

---

## 4. Local Native Startup (Without Docker)

### 4.1 Backend Service (PowerShell / Windows)
```powershell
# 1. Activate Python virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Verify dependencies
pip install -r requirements.txt

# 3. Start Uvicorn backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4.2 Frontend Service (PowerShell / Windows)
```powershell
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies (if not cached)
npm install

# 3. Start development server
npm run dev
# Accessible at http://localhost:5173
```

---

## 5. Health Checks & Verification Probes

AIR KAVACH exposes dedicated endpoints for container orchestrators (Kubernetes, Docker Swarm, AWS ECS):

### 5.1 Liveness Probe (`GET /health`)
Verifies that the HTTP event loop is active and responsive.
```bash
curl -f http://localhost:8000/health
# Expect: {"status": "healthy", ...}
```

### 5.2 Readiness Probe (`GET /ready`)
Verifies that all required Parquet files and ML model artifacts are mounted, valid, and loaded in memory.
```bash
curl -f http://localhost:8000/ready
# Expect HTTP 200: {"status": "ready", "components": {...}}
# If core data files are missing, returns HTTP 503
```

---

## 6. Backup & Persistent Storage

To ensure zero data loss during upgrades:
- Regularly backup `./data/` (contains raw, processed, and feature Parquet files).
- Regularly backup `./reports/` (contains generated audit reports).
- Models can be recreated at any time by issuing `POST /api/models/train` or running `python -m src.ml.isolation_forest`.

---

## 7. Troubleshooting & Operational Runbooks

| Symptom | Root Cause | Solution |
|---|---|---|
| `GET /ready` returns `503` | Feature Parquet files or model missing from `./data` | Run `python -m src.event_detection.event_processor` and `python -m src.attribution.attribution_engine` |
| Frontend displays "Network Error" | Backend not listening on port 8000 or CORS mismatch | Check `docker-compose logs backend` and verify `CORS_ORIGINS` in `.env` |
| `UnicodeEncodeError` in Windows console | Terminal default charset (cp1252) cannot print special characters | Ensure Python runs with UTF-8 (`PYTHONIOENCODING=utf-8`) |
| Container port 8000 conflict | Another process is using port 8000 | Set `PORT=8001` in `.env` or stop conflicting process (`netstat -ano \| findstr 8000`) |
