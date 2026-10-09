# AIR KAVACH - User Guide

## Navigating the Application

1. **Home Landing Page (`Home`):**
   - High-level overview of the platform, methodology steps ("From Data to Decisions"), and key regional statistics.
2. **Main Dashboard (`Dashboard`):**
   - Real-time and historical system metrics: Total Observations (8,211), Active Stations (4), Detected Events (51), Evaluated Candidate Facilities (26).
3. **Monitoring View (`Monitoring`):**
   - Filter 15-minute high-frequency PM2.5 readings across the 4 Indore monitoring stations (Residency, Regional Park, Airport, Maguda).
4. **Pollution Events List (`Events`):**
   - Browse the 51 detected pollution spikes. Inspect start/end timestamps, peak PM2.5 concentration, and peak z-score.
5. **Event Workspace (`Workspace`):**
   - Deep-dive investigation view for a selected event. Displays station stats, wind direction, top candidate industrial facility rankings, and report generation controls.
6. **Interactive Map (`Map`):**
   - Leaflet map displaying real station markers, candidate factory locations, and event epicenters in Indore.
7. **Source Attribution (`Attribution`):**
   - Detailed screening breakdown combining distance decay ($e^{-d / 5.0}$) and meteorological wind vector alignment.
8. **AI Assistant (`AI Assistant`):**
   - Ask natural language investigation questions with transparent agentic execution traces.
9. **ML Models (`ML Models`):**
   - Monitor `IsolationForest` model status, feature schema, and trigger manual model retraining.
10. **Data Sources (`Data Sources`):**
    - Monitor OpenAQ live ingestion status and trigger incremental data fetching.
11. **Reports (`Reports`):**
    - Compile official JSON and PDF evidence reports.
12. **Settings (`Settings`):**
    - View service health and retention rules.
