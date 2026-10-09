const DEFAULT_API = window.location.hostname === '127.0.0.1' ? 'http://127.0.0.1:8000' : 'http://localhost:8000';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || DEFAULT_API;

async function apiFetch(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE_URL}${endpoint}`, options);
    if (!res.ok) {
      throw new Error(`API error ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (err) {
    // Fallback to 127.0.0.1 if localhost failed or vice versa
    const fallbackBase = API_BASE_URL.includes('localhost') ? 'http://127.0.0.1:8000' : 'http://localhost:8000';
    try {
      const fallbackRes = await fetch(`${fallbackBase}${endpoint}`, options);
      if (!fallbackRes.ok) throw new Error(`Fallback error ${fallbackRes.status}`);
      return await fallbackRes.json();
    } catch (fbErr) {
      throw err;
    }
  }
}

export async function fetchHealth() {
  return apiFetch('/health');
}

export async function fetchReady() {
  return apiFetch('/ready');
}

export async function fetchSummary(city = "", state_ut = "") {
  const params = new URLSearchParams();
  if (city) params.append("city", city);
  if (state_ut) params.append("state_ut", state_ut);
  const q = params.toString() ? `?${params.toString()}` : "";
  return apiFetch(`/api/summary${q}`);
}

export async function fetchCoverage() {
  return apiFetch('/api/coverage');
}

export async function fetchStations(city = "", state_ut = "") {
  const params = new URLSearchParams();
  if (city) params.append("city", city);
  if (state_ut) params.append("state_ut", state_ut);
  const q = params.toString() ? `?${params.toString()}` : "";
  return apiFetch(`/api/stations${q}`);
}

export async function fetchObservations(station = "", city = "", limit = 100, offset = 0) {
  const params = new URLSearchParams({ limit, offset });
  if (station) params.append("station", station);
  if (city) params.append("city", city);
  return apiFetch(`/api/observations?${params}`);
}

export async function fetchEvents(station = "", city = "", min_peak_pm25 = null, limit = 50, offset = 0) {
  const params = new URLSearchParams({ limit, offset });
  if (station) params.append("station", station);
  if (city) params.append("city", city);
  if (min_peak_pm25) params.append("min_peak_pm25", min_peak_pm25);
  return apiFetch(`/api/events?${params}`);
}

export async function fetchEventDetails(eventId) {
  return apiFetch(`/api/events/${eventId}`);
}

export async function fetchEventAttribution(eventId) {
  return apiFetch(`/api/attribution/${eventId}`);
}

export async function fetchEventEvidence(eventId) {
  return apiFetch(`/api/evidence/${eventId}`);
}

export async function fetchMapData(city = "") {
  const q = city ? `?city=${encodeURIComponent(city)}` : "";
  return apiFetch(`/api/map${q}`);
}

export async function fetchIngestionStatus() {
  return apiFetch('/api/ingestion/status');
}

export async function fetchIngestionJobs() {
  return apiFetch('/api/ingestion/jobs');
}

export async function triggerIngestion(regionId = "in-mp-indore") {
  return apiFetch('/api/ingestion/run', {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ region_id: regionId, provider: "openaq" }),
  });
}

export async function fetchModelStatus() {
  return apiFetch('/api/models/status');
}

export async function fetchModelVersions() {
  return apiFetch('/api/models/versions');
}

export async function triggerModelTraining() {
  return apiFetch('/api/models/train', { method: "POST" });
}

export async function postAgentQuery(query, eventId = null, regionId = null) {
  return apiFetch('/api/assistant/investigate', {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, event_id: eventId, region_id: regionId }),
  });
}

export async function postGenerateReport(eventId) {
  return apiFetch('/api/reports', {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_id: eventId, include_trace: true }),
  });
}

export async function fetchReportsList() {
  return apiFetch('/api/reports');
}

export async function fetchReportById(reportId) {
  return apiFetch(`/api/reports/${reportId}`);
}

export async function fetchSystemStatus() {
  return apiFetch('/api/system/status');
}

export async function fetchProvidersStatus() {
  return apiFetch('/api/providers/status');
}

export async function syncProvider(providerId, regionId = "in-mp-indore", options = {}) {
  return apiFetch('/api/providers/sync', {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider_id: providerId, region_id: regionId, options }),
  });
}

export async function previewIntake(csvContent, rows = null, columnMapping = null, dataType = "observed") {
  return apiFetch('/api/intake/preview', {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      csv_content: csvContent,
      rows: rows,
      column_mapping: columnMapping,
      data_type: dataType,
    }),
  });
}

export async function commitIntake(records, regionId = "in-mp-indore", sourceLabel = "CSV Upload", dataType = "observed", isTest = false, environment = "production") {
  return apiFetch('/api/intake/commit', {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      records: records,
      region_id: regionId,
      source_label: sourceLabel,
      data_type: dataType,
      is_test: isTest,
      environment: environment,
    }),
  });
}

export async function fetchIntakeHistory(limit = 50, environment = null) {
  const envParam = environment ? `&environment=${encodeURIComponent(environment)}` : "";
  return apiFetch(`/api/intake/history?limit=${limit}${envParam}`);
}

