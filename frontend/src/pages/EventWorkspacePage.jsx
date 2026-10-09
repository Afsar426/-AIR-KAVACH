import React, { useEffect, useState } from 'react';
import { 
  fetchEventDetails, 
  fetchEventAttribution, 
  fetchEventEvidence, 
  fetchEvents,
  postGenerateReport, 
  postAgentQuery 
} from '../api';
import { 
  AlertTriangle, 
  Compass, 
  MapPin, 
  Factory, 
  Shield, 
  FileText, 
  ArrowLeft, 
  RefreshCw, 
  CheckCircle2, 
  Terminal, 
  HelpCircle, 
  Info,
  ChevronDown,
  ChevronUp,
  Wind,
  Activity,
  Download,
  AlertCircle,
  Clock,
  Sparkles
} from 'lucide-react';

const BENCHMARK_EVENTS = ['EVT-0001', 'EVT-0007', 'EVT-0017', 'EVT-0029', 'EVT-0047', 'EVT-0048'];

export default function EventWorkspacePage({ eventId, onBack, onNavigateToAssistant, onSelectEvent, region }) {
  const [details, setDetails] = useState(null);
  const [attribution, setAttribution] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [agentTrace, setAgentTrace] = useState(null);
  const [loading, setLoading] = useState(false);
  const [availableEvents, setAvailableEvents] = useState([]);
  const [loadingEventsList, setLoadingEventsList] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportSuccess, setReportSuccess] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [showTrace, setShowTrace] = useState(false);

  // Fetch available events for in-workspace switching and quick navigation
  useEffect(() => {
    let isMounted = true;
    const loadAvailable = async () => {
      try {
        setLoadingEventsList(true);
        const res = await fetchEvents("", region?.city || "Indore", null, 100);
        if (isMounted && res?.events) {
          setAvailableEvents(res.events);
        }
      } catch (e) {
        console.debug("Could not fetch available events list:", e);
      } finally {
        if (isMounted) setLoadingEventsList(false);
      }
    };
    loadAvailable();
    return () => { isMounted = false; };
  }, [region?.city]);

  const loadData = async (targetId) => {
    if (!targetId) return;
    try {
      setLoading(true);
      const [dRes, aRes, eRes] = await Promise.all([
        fetchEventDetails(targetId),
        fetchEventAttribution(targetId),
        fetchEventEvidence(targetId),
      ]);
      setDetails(dRes.event);
      setAttribution(aRes);
      setEvidence(eRes);

      // Fetch automated investigation trace from agent orchestrator
      try {
        const traceRes = await postAgentQuery(`Investigate event ${targetId}`, targetId);
        setAgentTrace(traceRes);
      } catch (tErr) {
        console.debug("Agent trace fetch fallback:", tErr);
      }
    } catch (err) {
      console.error("Error loading workspace data:", err);
      setDetails(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (eventId) {
      loadData(eventId);
    } else {
      setLoading(false);
      setDetails(null);
      setAttribution(null);
      setEvidence(null);
      setAgentTrace(null);
    }
  }, [eventId]);

  const handleGenerateReport = async () => {
    try {
      setGeneratingReport(true);
      const res = await postGenerateReport(eventId);
      setReportData(res);
      setReportSuccess(true);
      setTimeout(() => setReportSuccess(false), 6000);
    } catch (err) {
      alert("Error generating report: " + err.message);
    } finally {
      setGeneratingReport(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '4rem 2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <RefreshCw size={26} className="spin" style={{ margin: '0 auto 1rem', display: 'block', color: 'var(--accent)' }} />
        <p style={{ fontWeight: 500 }}>Loading Forensic Investigation Workspace for {eventId}...</p>
      </div>
    );
  }

  // Graceful empty state when no event is selected
  if (!eventId) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '780px', margin: '1rem auto', width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button onClick={onBack} className="btn-secondary">
            <ArrowLeft size={16} /> Back to Events List
          </button>
        </div>

        <div className="card" style={{ padding: '2.5rem', textAlign: 'center' }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            backgroundColor: 'var(--bg-main)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1.25rem',
            border: '1px solid var(--border)'
          }}>
            <Compass size={24} style={{ color: 'var(--primary)' }} />
          </div>

          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--primary)', marginBottom: '0.5rem' }}>
            Forensic Investigation Workspace
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', maxWidth: '520px', margin: '0 auto 1.75rem', lineHeight: 1.5 }}>
            Select a detected pollution incident to conduct forensic multi-evidence source attribution, wind vector trajectory analysis, and automated causal audit.
          </p>

          <div style={{ maxWidth: '440px', margin: '0 auto 1.5rem', textAlign: 'left' }}>
            <label style={{ display: 'block', fontSize: '0.785rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Select Active Incident
            </label>
            <select
              className="form-select"
              value=""
              onChange={(e) => onSelectEvent && e.target.value && onSelectEvent(e.target.value)}
              style={{ width: '100%', padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', fontSize: '0.875rem' }}
            >
              <option value="" disabled>Choose an incident to investigate...</option>
              {availableEvents.map(evt => (
                <option key={evt.id} value={evt.id}>
                  {evt.id} — {evt.station || 'Station'} ({Math.round(evt.peak_pm25 || 0)} µg/m³ peak)
                </option>
              ))}
            </select>
          </div>

          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1.25rem', marginTop: '1.25rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.75rem' }}>
              Or choose a benchmark validation incident:
            </span>
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              {BENCHMARK_EVENTS.map((id) => (
                <button
                  key={id}
                  onClick={() => onSelectEvent && onSelectEvent(id)}
                  className="btn-secondary"
                  style={{ fontSize: '0.785rem', padding: '0.35rem 0.75rem' }}
                >
                  <Activity size={13} style={{ color: 'var(--critical)' }} />
                  {id}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Graceful state when requested event is not found
  if (!details) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '780px', margin: '1rem auto', width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button onClick={onBack} className="btn-secondary">
            <ArrowLeft size={16} /> Return to Events List
          </button>
        </div>

        <div className="card" style={{ padding: '2.5rem', textAlign: 'center' }}>
          <AlertTriangle size={32} color="var(--critical)" style={{ margin: '0 auto 1rem' }} />
          <h3 style={{ color: 'var(--primary)', marginBottom: '0.5rem' }}>Incident Not Found: {eventId}</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', maxWidth: '480px', margin: '0 auto 1.5rem', lineHeight: 1.5 }}>
            The requested pollution incident could not be located in analytical storage. Select another incident from the list below to proceed with forensic investigation.
          </p>

          <div style={{ maxWidth: '440px', margin: '0 auto 1.5rem', textAlign: 'left' }}>
            <label style={{ display: 'block', fontSize: '0.785rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Select Available Incident
            </label>
            <select
              className="form-select"
              value=""
              onChange={(e) => onSelectEvent && e.target.value && onSelectEvent(e.target.value)}
              style={{ width: '100%', padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', fontSize: '0.875rem' }}
            >
              <option value="" disabled>Choose an incident to investigate...</option>
              {availableEvents.map(evt => (
                <option key={evt.id} value={evt.id}>
                  {evt.id} — {evt.station || 'Station'} ({Math.round(evt.peak_pm25 || 0)} µg/m³ peak)
                </option>
              ))}
            </select>
          </div>

          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1.25rem', marginTop: '1.25rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.75rem' }}>
              Or choose a benchmark validation incident:
            </span>
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              {BENCHMARK_EVENTS.map((id) => (
                <button
                  key={id}
                  onClick={() => onSelectEvent && onSelectEvent(id)}
                  className="btn-secondary"
                  style={{ fontSize: '0.785rem', padding: '0.35rem 0.75rem' }}
                >
                  <Activity size={13} style={{ color: 'var(--critical)' }} />
                  {id}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const windEvidence = evidence?.wind_evidence || {};
  const candidates = attribution?.candidates || [];
  const topCandidate = candidates[0];

  // Extract tools trace safely whether object or array
  const rawTrace = agentTrace?.execution_trace;
  const executedTools = Array.isArray(rawTrace) 
    ? rawTrace 
    : (rawTrace?.executed_tools || []);
  const reasoningSteps = rawTrace?.reasoning_steps || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      {/* Top Action Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button onClick={onBack} className="btn-secondary" title="Return to pollution events list">
            <ArrowLeft size={16} /> Back to Events List
          </button>

          {availableEvents.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Incident:</span>
              <select
                className="form-select"
                value={eventId}
                onChange={(e) => onSelectEvent && onSelectEvent(e.target.value)}
                style={{ 
                  padding: '0.35rem 0.65rem', 
                  fontSize: '0.8125rem', 
                  borderRadius: 'var(--radius-sm)', 
                  border: '1px solid var(--border)',
                  minWidth: '220px'
                }}
                title="Switch active incident"
              >
                {availableEvents.map(evt => (
                  <option key={evt.id} value={evt.id}>
                    {evt.id} — {evt.station || 'Station'} ({Math.round(evt.peak_pm25 || 0)} µg/m³)
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button 
            onClick={() => onNavigateToAssistant(eventId)} 
            className="btn-secondary"
            title="Ask AI questions about this specific event"
          >
            <Sparkles size={16} color="var(--accent)" /> Ask AI Assistant
          </button>

          <button 
            onClick={handleGenerateReport} 
            disabled={generatingReport}
            className="btn-primary"
            title="Compile persistent disaggregated investigation dossier"
          >
            <FileText size={16} /> {generatingReport ? "Exporting Dossier..." : "Generate Investigation Report"}
          </button>
        </div>
      </div>

      {reportSuccess && (
        <div className="alert-callout alert-callout-success">
          <CheckCircle2 size={20} color="var(--success)" style={{ flexShrink: 0 }} />
          <div>
            <strong style={{ display: 'block', color: 'var(--success)' }}>
              Investigation Report Successfully Compiled & Persisted!
            </strong>
            <span style={{ fontSize: '0.85rem' }}>
              Dossier ID: <code>{reportData?.report_id || `REP-${eventId}`}</code> saved to <code>reports/investigations/</code> with verified in-situ facts and candidate screening scores.
            </span>
          </div>
        </div>
      )}

      {/* ==================================================================
          SECTION A: EVENT OVERVIEW
          ================================================================== */}
      <div className="card" style={{ borderLeft: '5px solid var(--critical)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1.5rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
              <span className="badge badge-critical text-mono" style={{ fontSize: '0.75rem' }}>
                INCIDENT: {details.event_id}
              </span>
              <span className={`badge ${
                details.temporal_status === 'active' ? 'badge-critical' : 
                details.temporal_status === 'resolved' ? 'badge-success' : 
                details.temporal_status === 'recent' ? 'badge-warning' : 'badge-info'
              }`}>
                {details.temporal_status === 'active' ? '🔴 Active Spike' : 
                 details.temporal_status === 'resolved' ? '✓ Resolved' : 
                 details.temporal_status === 'recent' ? 'Recent (≤30d)' : 'Historical Archive'}
              </span>
              <span className="badge badge-neutral">
                Indore Urban Monitoring Node
              </span>
            </div>

            <h2 style={{ fontSize: '1.85rem', color: 'var(--primary)', letterSpacing: '-0.02em', marginBottom: '0.35rem' }}>
              {details.station} CAAQMS Elevation Episode
            </h2>
            
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', margin: 0 }}>
              Detected from <strong>{new Date(details.start_time).toUTCString()}</strong> to <strong>{new Date(details.end_time).toUTCString()}</strong> ({details.duration_minutes} min duration)
            </p>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              PEAK CONCENTRATION
            </div>
            <div style={{ fontSize: '2.6rem', fontWeight: 700, color: 'var(--critical)', lineHeight: 1.1, margin: '0.2rem 0' }}>
              {details.peak_pm25.toFixed(1)} <span style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-secondary)' }}>µg/m³</span>
            </div>
            <span className="badge badge-warning" style={{ fontSize: '0.75rem' }}>
              +{details.peak_z_score ? details.peak_z_score.toFixed(2) : '2.0'} σ Above Shifted Baseline
            </span>
          </div>
        </div>
      </div>

      {/* ==================================================================
          SECTION F (PRE-EMPTIVE): MANDATORY CEMS GUARDRAIL BANNER
          ================================================================== */}
      <div 
        style={{
          padding: '1.1rem 1.35rem',
          backgroundColor: 'var(--bg-surface)',
          borderLeft: '4px solid var(--warning)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border)',
          borderLeftWidth: '4px',
          borderLeftColor: 'var(--warning)',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.85rem'
        }}
      >
        <AlertTriangle size={20} color="var(--warning)" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div>
          <strong style={{ color: 'var(--primary)', fontSize: '0.9rem', display: 'block', letterSpacing: '0.02em', marginBottom: '0.25rem' }}>
            DIRECT EMISSIONS EVIDENCE UNAVAILABLE (CEMS UNCONNECTED)
          </strong>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
            Candidate rankings are based strictly on geometric surface wind alignment and spatial distance decay. 
            Continuous emission monitoring system (CEMS) telemetry is not connected for candidate facilities. 
            These results are heuristic screening indicators for ground inspectors, <strong>NOT</strong> legal proof of industrial liability or regulatory violation.
          </p>
        </div>
      </div>

      {/* ==================================================================
          SECTIONS B & C: OBSERVED IN-SITU FACTS & WEATHER EVIDENCE
          ================================================================== */}
      <div className="grid-cols-2">
        
        {/* SECTION B: Observed Environmental Evidence */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <h3 style={{ fontSize: '1.1rem', color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
              <Activity size={18} color="var(--success)" /> B. Observed Environmental Facts
            </h3>
            <span className="badge badge-success">In-Situ CAAQMS</span>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.45rem' }}>
              <span className="text-muted">Monitoring Node:</span>
              <strong>{details.station} Station (Indore, MP)</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.45rem' }}>
              <span className="text-muted">Observed Peak PM2.5:</span>
              <strong style={{ color: 'var(--critical)' }}>{details.peak_pm25.toFixed(1)} µg/m³</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.45rem' }}>
              <span className="text-muted">Duration & Sampling Intervals:</span>
              <strong>{details.duration_minutes} min ({details.readings || details.num_readings || 4} continuous 15-min intervals)</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.45rem' }}>
              <span className="text-muted">24h Rolling Baseline Mean:</span>
              <strong>{details.baseline_mean ? `${details.baseline_mean.toFixed(1)} µg/m³` : 'N/A'}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-muted">Baseline Estimation Method:</span>
              <span className="badge badge-neutral text-mono" style={{ fontSize: '0.675rem' }}>shift(1).rolling(96) Past-Only</span>
            </div>
          </div>
        </div>

        {/* SECTION C: Weather and Wind Evidence */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <h3 style={{ fontSize: '1.1rem', color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
              <Wind size={18} color="var(--accent)" /> C. Weather & Wind Telemetry
            </h3>
            <span className="badge badge-info">Surface Vectors</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.45rem', alignItems: 'center' }}>
              <span className="text-muted">Surface Wind Direction (FROM):</span>
              <strong>
                {windEvidence.wind_direction_mean_deg 
                  ? `${windEvidence.wind_direction_mean_deg.toFixed(1)}° (Circular Mean)`
                  : 'Wind direction unrecorded'}
              </strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.45rem', alignItems: 'center' }}>
              <span className="text-muted">Surface Wind Speed:</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <strong>
                  {windEvidence.wind_speed_mean_mps != null
                    ? `${windEvidence.wind_speed_mean_mps.toFixed(2)} m/s`
                    : 'Speed channel unrecorded'}
                </strong>
                {windEvidence.is_calm_wind && (
                  <span className="badge badge-warning" style={{ fontSize: '0.675rem', padding: '0.15rem 0.45rem' }}>
                    Calm (&lt;0.5 m/s)
                  </span>
                )}
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.45rem' }}>
              <span className="text-muted">Temporal Window Coverage:</span>
              <strong>{windEvidence.wind_coverage ? `${(windEvidence.wind_coverage * 100).toFixed(1)}% completeness` : 'N/A'}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.45rem' }}>
              <span className="text-muted">Transport Physics Regime:</span>
              <strong>
                {windEvidence.is_calm_wind ? 'Microscale Diffusion / Stagnation' : 'Horizontal Advective Plume'}
              </strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-muted">Temporal Alignment Window:</span>
              <span className="badge badge-neutral" style={{ fontSize: '0.675rem' }}>±60 min Tolerance</span>
            </div>
          </div>
        </div>

      </div>

      {/* ==================================================================
          SECTION D: CANDIDATE INDUSTRIAL FACILITIES
          ================================================================== */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', color: 'var(--primary)', marginBottom: '0.2rem' }}>
              D. Candidate Industrial Facilities Screening Ranking
            </h3>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', margin: 0 }}>
              Facilities ranked by heuristic screening score combining 70% directional wind alignment and 30% spatial proximity within 25 km buffer.
            </p>
          </div>
          <span className="badge badge-neutral">
            {candidates.length} Facilities Evaluated
          </span>
        </div>

        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '60px' }}>Rank</th>
                <th>Factory Name</th>
                <th>Category</th>
                <th style={{ textAlign: 'right' }}>Distance</th>
                <th>Wind Relationship</th>
                <th style={{ textAlign: 'right' }}>Score</th>
                <th style={{ textAlign: 'right' }}>Score Share</th>
                <th>Evidence Classification</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((fac) => (
                <tr key={fac.factory_id}>
                  <td style={{ fontWeight: 700 }}>#{fac.factory_rank}</td>
                  <td>
                    <strong>{fac.factory_name}</strong>
                    <div style={{ fontSize: '0.725rem', color: 'var(--text-secondary)' }}>ID: {fac.factory_id}</div>
                  </td>
                  <td>
                    <span className="badge badge-neutral" style={{ fontSize: '0.7rem' }}>
                      {fac.facility_category}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                    {fac.distance_km.toFixed(2)} km
                  </td>
                  <td>
                    <span className={`badge ${
                      fac.wind_relationship?.includes('strong_upwind') ? 'badge-success' :
                      fac.wind_relationship?.includes('upwind') ? 'badge-info' : 'badge-warning'
                    }`} style={{ fontSize: '0.7rem' }}>
                      <Compass size={11} style={{ marginRight: '3px' }} />
                      {fac.wind_relationship?.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--primary)' }}>
                    {fac.attribution_score.toFixed(3)}
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                    {((fac.screening_score_share || fac.relative_likelihood || 0) * 100).toFixed(1)}%
                  </td>
                  <td>
                    <span className="badge badge-info" style={{ fontSize: '0.675rem' }}>
                      {fac.evidence_label?.replace(/_/g, ' ') || 'Screening Candidate'}
                    </span>
                  </td>
                </tr>
              ))}
              {candidates.length === 0 && (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-secondary)' }}>
                    No industrial candidates identified within 25 km radius.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ==================================================================
          SECTION E: SCREENING SCORES & METHODOLOGY LIMITATIONS
          ================================================================== */}
      <div className="card">
        <h3 style={{ fontSize: '1.15rem', color: 'var(--primary)', marginBottom: '0.75rem' }}>
          E. Screening Methodology & Scoring Formulations
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
          Heuristic formulation transparently balances exponential spatial distance decay against meteorological vector alignment.
        </p>

        <div className="grid-cols-3">
          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <strong style={{ fontSize: '0.85rem', color: 'var(--primary)', display: 'block', marginBottom: '0.35rem' }}>
              1. Spatial Distance Decay (30% Weight)
            </strong>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
              Formula: <code style={{ backgroundColor: 'var(--bg-surface)', padding: '0.1rem 0.35rem', borderRadius: '3px' }}>exp(-d / 5.0 km)</code><br />
              Heuristic exponential decay scaled over a 5 km characteristic boundary layer dispersion buffer.
            </p>
          </div>

          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <strong style={{ fontSize: '0.85rem', color: 'var(--primary)', display: 'block', marginBottom: '0.35rem' }}>
              2. Meteorological Wind Alignment (70% Weight)
            </strong>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
              Formula: <code style={{ backgroundColor: 'var(--bg-surface)', padding: '0.1rem 0.35rem', borderRadius: '3px' }}>cos(θ_sensor→fac - θ_wind_from)</code><br />
              Meteorological convention (wind FROM origin) comparing sensor-to-factory bearing against wind direction.
            </p>
          </div>

          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <strong style={{ fontSize: '0.85rem', color: 'var(--primary)', display: 'block', marginBottom: '0.35rem' }}>
              3. Normalized Screening Score Share
            </strong>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
              Formula: <code style={{ backgroundColor: 'var(--bg-surface)', padding: '0.1rem 0.35rem', borderRadius: '3px' }}>score_i / sum(all_scores)</code><br />
              Relative heuristic index partition across candidate facilities within 25 km. <em>Not a causal probability.</em>
            </p>
          </div>
        </div>
      </div>

      {/* ==================================================================
          SECTION F: MISSING EVIDENCE & UNCERTAINTY AUDIT
          ================================================================== */}
      <div className="card" style={{ borderLeft: '4px solid var(--warning)' }}>
        <h3 style={{ fontSize: '1.15rem', color: 'var(--primary)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={18} color="var(--warning)" /> F. Missing Evidence & Scientific Uncertainty Audit
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
          Defensible environmental intelligence requires explicit enumeration of unmeasured atmospheric and operational parameters.
        </p>

        <ul style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: '1.6', margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <li>
            <strong>Absence of Continuous Stack CEMS Telemetry:</strong> Candidate facilities lack live in-stack mass emission telemetry (g/s). Operational uptime during elevation hours is unconfirmed.
          </li>
          <li>
            <strong>Two-Dimensional Horizontal Approximation:</strong> Calculations use 10m surface anemometer vectors. Planetary boundary layer mixing height, vertical wind shear, and stack thermal buoyancy are unrecorded.
          </li>
          {windEvidence.is_calm_wind && (
            <li style={{ color: 'var(--warning)', fontWeight: 600 }}>
              <strong>Calm Wind Stagnation ($u &lt; 0.5$ m/s):</strong> Mechanical anemometer operates near stiction threshold; transport is governed by microscale diffusion and local trapping rather than directional plumes.
            </li>
          )}
          {topCandidate && topCandidate.distance_km > 15 && (
            <li style={{ color: 'var(--warning)', fontWeight: 600 }}>
              <strong>Elevated Plume Dilution Distance:</strong> Top ranked candidate is {topCandidate.distance_km.toFixed(1)} km away. Significant atmospheric dispersion and dilution occur over this distance.
            </li>
          )}
          <li>
            <strong>Mandatory Regulatory Requirement:</strong> Formal regulatory sanctions or legal enforcement require validated Gaussian/Lagrangian dispersion modeling (AERMOD or HYSPLIT) coupled with ground stack inspection.
          </li>
        </ul>
      </div>

      {/* ==================================================================
          SECTION G: AGENTIC AI INVESTIGATION & EXECUTION TRACE
          ================================================================== */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sparkles size={18} color="var(--accent)" />
            <h3 style={{ fontSize: '1.15rem', color: 'var(--primary)', margin: 0 }}>
              G. Automated Investigation Synthesis & Execution Trace
            </h3>
          </div>
          {agentTrace?.request_id && (
            <span className="badge badge-info text-mono" style={{ fontSize: '0.7rem' }}>
              REQ: {agentTrace.request_id}
            </span>
          )}
        </div>

        {agentTrace?.summary && (
          <div style={{ padding: '0.85rem 1rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem', lineHeight: 1.55, marginBottom: '1rem', border: '1px solid var(--border-subtle)' }}>
            <strong>Synthesis: </strong> {agentTrace.summary}
          </div>
        )}

        {/* Collapsible Tool Execution Trace */}
        <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '0.75rem' }}>
          <button 
            onClick={() => setShowTrace(!showTrace)}
            className="btn-ghost"
            style={{ width: '100%', justifyContent: 'space-between', padding: '0.5rem 0' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Terminal size={15} color="var(--accent)" />
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--primary)' }}>
                Inspect Multi-Step Tool Execution Trace ({executedTools.length} Tools Executed)
              </span>
            </div>
            {showTrace ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {showTrace && (
            <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <p style={{ fontSize: '0.785rem', color: 'var(--text-secondary)', margin: 0 }}>
                Deterministic backend execution trace recording exact tool calls, inputs, and execution status.
              </p>
              {executedTools.map((toolCall, idx) => (
                <div 
                  key={idx}
                  style={{ 
                    padding: '0.75rem', 
                    backgroundColor: 'var(--bg-main)', 
                    borderRadius: 'var(--radius-sm)', 
                    fontSize: '0.785rem',
                    border: '1px solid var(--border-subtle)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                    <span style={{ fontWeight: 600, color: 'var(--primary)' }}>
                      Step {idx + 1}: <code className="text-mono" style={{ color: 'var(--accent)' }}>{toolCall.tool || toolCall.tool_name}</code>
                    </span>
                    <span className="badge badge-success" style={{ fontSize: '0.65rem' }}>
                      {toolCall.status || 'success'}
                    </span>
                  </div>
                  <div className="text-muted text-mono" style={{ fontSize: '0.725rem' }}>
                    Inputs: {JSON.stringify(toolCall.inputs || toolCall.arguments || {})}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ==================================================================
          SECTION H: PERSISTENT REPORT GENERATION ACTION
          ================================================================== */}
      <div 
        style={{
          padding: '1.25rem 1.5rem',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem'
        }}
      >
        <div>
          <h4 style={{ color: 'var(--primary)', marginBottom: '0.2rem', fontSize: '1rem' }}>
            H. Official Investigation Dossier Export
          </h4>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', margin: 0 }}>
            Compiles in-situ telemetry, wind vectors, and candidate rankings into an immutable, disaggregated JSON dossier.
          </p>
        </div>

        <button 
          onClick={handleGenerateReport} 
          disabled={generatingReport}
          className="btn-primary"
        >
          {generatingReport ? (
            <><RefreshCw size={15} className="spin" /> Compiling Dossier...</>
          ) : (
            <><FileText size={15} /> Compile & Persist Official Dossier</>
          )}
        </button>
      </div>

    </div>
  );
}
