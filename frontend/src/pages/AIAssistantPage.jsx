import React, { useState, useEffect } from 'react';
import { postAgentQuery } from '../api';
import { Shield, Send, RefreshCw, Terminal, CheckCircle2, AlertCircle, FileText, Globe, Layers, ArrowRight, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';

export default function AIAssistantPage({ region, initialEventId }) {
  const [query, setQuery] = useState(initialEventId ? `Investigate event ${initialEventId}` : '');
  const [eventId, setEventId] = useState(initialEventId || '');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showTrace, setShowTrace] = useState(true);

  useEffect(() => {
    if (initialEventId) {
      setEventId(initialEventId);
      setQuery(`Investigate event ${initialEventId}`);
    }
  }, [initialEventId]);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    try {
      setLoading(true);
      const res = await postAgentQuery(query, eventId || null, region?.id || null);
      setResponse(res);
    } catch (err) {
      alert("Error executing investigation query: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePreset = (presetText) => {
    setQuery(presetText);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      
      {/* Page Header */}
      <div className="page-header" style={{ marginBottom: 0 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
            <span className="badge badge-info">
              Scope: {region?.name || "Pan-India"}
            </span>
            <span className="badge badge-success">
              Deterministic Analytical Tool Registry
            </span>
          </div>
          <h1 className="page-title">Agentic AI Investigation Assistant</h1>
          <p className="page-subtitle">
            Natural language environmental intelligence queries executed via deterministic tools, trigonometry calculations, and verified execution traces.
          </p>
        </div>
      </div>

      {/* Preset Query Chips */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <span className="text-muted" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Suggested Queries:</span>
        <button onClick={() => handlePreset('Investigate event EVT-0001')} className="btn-secondary btn-sm">
          🔍 Investigate EVT-0001
        </button>
        <button onClick={() => handlePreset('Screen candidate facilities for EVT-0007')} className="btn-secondary btn-sm">
          🏭 Screen Candidates for EVT-0007
        </button>
        <button onClick={() => handlePreset('Check live ingestion status')} className="btn-secondary btn-sm">
          📡 Check Ingestion Status
        </button>
        <button onClick={() => handlePreset('Evaluate Isolation Forest model status')} className="btn-secondary btn-sm">
          🤖 Evaluate ML Model
        </button>
        <button onClick={() => handlePreset('What is the pollution in Delhi?')} className="btn-secondary btn-sm">
          🌐 Check Delhi Coverage
        </button>
      </div>

      {/* Query Input Box Form */}
      <form onSubmit={handleSubmit} className="card" style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', padding: '1rem 1.25rem' }}>
        <Sparkles size={20} color="var(--accent)" style={{ flexShrink: 0 }} />
        <input 
          type="text" 
          value={query} 
          onChange={(e) => setQuery(e.target.value)} 
          placeholder="Ask an investigative query (e.g., 'Investigate candidate factories for EVT-0017')..."
          className="form-control"
          style={{
            flex: 1,
            border: 'none',
            fontSize: '0.925rem',
            padding: '0.5rem 0',
            backgroundColor: 'transparent'
          }}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !query.trim()} className="btn-primary" style={{ padding: '0.65rem 1.35rem' }}>
          {loading ? <RefreshCw size={15} className="spin" /> : <Send size={15} />} Run Query
        </button>
      </form>

      {/* Response & Trace Container */}
      {response && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Summary Response Card */}
          <div className="card" style={{ borderLeft: '4px solid var(--accent)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span className="badge badge-info text-mono" style={{ fontSize: '0.7rem' }}>
                  REQ: {response.request_id}
                </span>
                <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>
                  Grounded in Analytical Parquet Store
                </span>
              </div>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Latency: {response.execution_trace?.duration_sec || 0.05}s
              </span>
            </div>

            <p style={{ fontSize: '1.025rem', color: 'var(--text-primary)', lineHeight: 1.6, marginBottom: '0.75rem' }}>
              {response.summary}
            </p>

            {response.scientific_disclaimer && (
              <div style={{ fontSize: '0.785rem', color: 'var(--text-secondary)', padding: '0.5rem 0.75rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', lineHeight: 1.45 }}>
                <strong>Caveat:</strong> {response.scientific_disclaimer}
              </div>
            )}
          </div>

          {/* Disaggregated Facts & Modeled Estimates */}
          {response.observed_facts?.station && (
            <div className="grid-cols-2">
              <div className="card">
                <h4 style={{ color: 'var(--primary)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.95rem' }}>
                  <CheckCircle2 size={16} color="var(--success)" /> Observed Facts (Station Data)
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.825rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-muted">Station / City:</span>
                    <strong>{response.observed_facts.station} ({response.observed_facts.city})</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-muted">Event Window:</span>
                    <span>{response.observed_facts.start_time ? new Date(response.observed_facts.start_time).toUTCString() : 'N/A'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-muted">Peak Concentration:</span>
                    <strong style={{ color: 'var(--critical)' }}>{response.observed_facts.peak_pm25 ? `${response.observed_facts.peak_pm25.toFixed(1)} µg/m³` : 'N/A'}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-muted">Observed Surface Wind:</span>
                    <strong>{response.observed_facts.wind_direction_mean_deg != null ? `${response.observed_facts.wind_direction_mean_deg.toFixed(1)}° (${response.observed_facts.wind_speed_mean_mps ? response.observed_facts.wind_speed_mean_mps.toFixed(2) + ' m/s' : 'Speed unrecorded'})` : 'Unrecorded'}</strong>
                  </div>
                </div>
              </div>

              <div className="card">
                <h4 style={{ color: 'var(--primary)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.95rem' }}>
                  <Layers size={16} color="var(--accent)" /> Modeled Estimates
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.825rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-muted">Baseline Estimation:</span>
                    <code className="text-mono" style={{ fontSize: '0.75rem' }}>{response.modeled_estimates?.baseline_method || 'Past-only shift(1).rolling(96)'}</code>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-muted">Peak Z-Score:</span>
                    <strong>{response.modeled_estimates?.peak_z_score ? `+${response.modeled_estimates.peak_z_score.toFixed(2)} σ` : 'N/A'}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-muted">Lifecycle Status:</span>
                    <span className="badge badge-info" style={{ fontSize: '0.675rem' }}>{response.modeled_estimates?.temporal_lifecycle_status?.toUpperCase() || 'HISTORICAL'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-muted">Dispersion Scale:</span>
                    <strong>{response.modeled_estimates?.dispersion_scale_km || 5.0} km exponential</strong>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Candidate Rankings */}
          {response.candidate_rankings?.length > 0 && (
            <div className="card">
              <h4 style={{ color: 'var(--primary)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.95rem' }}>
                <Globe size={16} color="var(--accent)" /> Plausible Source Candidates (Geospatial Screening)
              </h4>
              <div className="data-table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th style={{ width: '60px' }}>Rank</th>
                      <th>Facility Name</th>
                      <th>Distance</th>
                      <th>Wind Orientation</th>
                      <th>Screening Score</th>
                      <th>Classification Label</th>
                    </tr>
                  </thead>
                  <tbody>
                    {response.candidate_rankings.map((c, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 700 }}>#{c.factory_rank || i + 1}</td>
                        <td><strong>{c.factory_name}</strong></td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{c.distance_km ? `${c.distance_km.toFixed(2)} km` : 'N/A'}</td>
                        <td>
                          <span className={`badge ${c.wind_relationship?.includes('upwind') ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '0.7rem' }}>
                            {c.wind_relationship?.replace(/_/g, ' ') || 'aligned'}
                          </span>
                        </td>
                        <td style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--primary)' }}>
                          {c.attribution_score ? c.attribution_score.toFixed(3) : 'N/A'}
                        </td>
                        <td>
                          <span className="badge badge-info" style={{ fontSize: '0.675rem' }}>
                            {c.evidence_label?.replace(/_/g, ' ') || 'GEOSPATIAL SCREENING SUPPORT'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Missing Evidence Callout */}
          {response.missing_evidence?.length > 0 && (
            <div className="alert-callout alert-callout-warning">
              <AlertCircle size={20} color="var(--warning)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong style={{ color: 'var(--primary)', fontSize: '0.9rem', display: 'block', marginBottom: '0.35rem' }}>
                  Missing or Incomplete Telemetry Noted by Agent
                </strong>
                <ul style={{ paddingLeft: '1.25rem', fontSize: '0.825rem', color: 'var(--text-primary)', margin: 0, lineHeight: 1.5 }}>
                  {response.missing_evidence.map((warn, i) => (
                    <li key={i}>{warn}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Execution Trace */}
          {response.execution_trace && (
            <div className="card" style={{ backgroundColor: '#141F2E', color: '#D5E2EE', border: '1px solid #23354C' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Terminal size={17} color="var(--accent)" />
                  <h4 style={{ color: '#FFFFFF', margin: 0, fontSize: '0.925rem' }}>Agent Execution Trace & Tool Sequence</h4>
                </div>
                <button 
                  onClick={() => setShowTrace(!showTrace)} 
                  style={{ background: 'none', border: 'none', color: '#A0B8D0', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600 }}
                >
                  {showTrace ? "Hide Details" : "View Details"}
                </button>
              </div>

              {showTrace && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.825rem' }}>
                  <div style={{ display: 'flex', gap: '1.5rem', borderBottom: '1px solid #23354C', paddingBottom: '0.65rem', flexWrap: 'wrap' }}>
                    <div><span style={{ color: '#889EB8' }}>Task Type:</span> <code>{response.execution_trace.task_type}</code></div>
                    <div><span style={{ color: '#889EB8' }}>Tools:</span> {response.execution_trace.executed_tools?.length || 0} calls</div>
                    <div><span style={{ color: '#889EB8' }}>Status:</span> <span style={{ color: 'var(--success)' }}>{response.execution_trace.status}</span></div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                    {response.execution_trace.executed_tools?.map((tool, idx) => (
                      <div 
                        key={idx}
                        style={{
                          padding: '0.6rem 0.85rem',
                          backgroundColor: '#1B293C',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.785rem',
                          fontFamily: 'var(--font-mono)'
                        }}
                      >
                        <span style={{ color: '#68B3B7', fontWeight: 600 }}>Step {idx + 1}: {tool.tool}</span>
                        <div style={{ color: '#889EB8', fontSize: '0.725rem', marginTop: '2px' }}>
                          Inputs: {JSON.stringify(tool.inputs || {})}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      )}

    </div>
  );
}
