import React, { useEffect, useState } from 'react';
import { fetchSummary } from '../api';
import { 
  Activity, 
  Radio, 
  AlertTriangle, 
  Factory, 
  RefreshCw, 
  Clock, 
  Globe, 
  Shield, 
  CheckCircle2, 
  AlertCircle,
  Calendar,
  Layers,
  ArrowRight
} from 'lucide-react';

export default function MainDashboard({ region, onNavigateToEvent, onNavigateToEvents }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await fetchSummary(region?.city || "", region?.state_ut || "");
      setSummary(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [region]);

  if (loading) {
    return (
      <div style={{ padding: '4rem 2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <RefreshCw size={26} className="spin" style={{ margin: '0 auto 1rem', display: 'block', color: 'var(--accent)' }} />
        <p style={{ fontWeight: 500 }}>Loading Environmental Intelligence Summary for {region?.name || "Selected Region"}...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert-callout alert-callout-critical">
        <AlertTriangle size={20} color="var(--critical)" style={{ flexShrink: 0 }} />
        <div>
          <strong style={{ display: 'block', marginBottom: '0.25rem' }}>Error Loading Summary</strong>
          <p style={{ margin: 0, fontSize: '0.875rem' }}>{error}</p>
          <button onClick={loadData} className="btn-secondary btn-sm" style={{ marginTop: '0.75rem' }}>
            <RefreshCw size={12} /> Retry Connection
          </button>
        </div>
      </div>
    );
  }

  const isNoData = summary?.geographic_scope?.coverage_status === 'no_usable_data';
  const dataPeriod = summary?.data_period || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      
      {/* 1. Header Banner */}
      <div className="page-header" style={{ marginBottom: 0 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem', flexWrap: 'wrap' }}>
            <span className="badge badge-info">
              Scope: {summary?.geographic_scope?.selected_region || region?.name}
            </span>
            {isNoData ? (
              <span className="badge badge-warning">
                <AlertCircle size={11} style={{ marginRight: '2px' }} />
                Feeds Pending
              </span>
            ) : (
              <span className="badge badge-success">
                <CheckCircle2 size={11} style={{ marginRight: '2px' }} />
                Data Active (Indore Baseline)
              </span>
            )}
          </div>
          <h1 className="page-title">Environmental Intelligence Dashboard</h1>
          <p className="page-subtitle">
            Continuous CPCB CAAQMS air quality monitoring, rolling baseline statistical anomaly detection, and meteorological candidate facility screening.
          </p>
        </div>

        <button onClick={loadData} className="btn-secondary" title="Refresh dashboard metrics">
          <RefreshCw size={14} /> Refresh Summary
        </button>
      </div>

      {/* 2. Data Freshness & Period Banner */}
      <div 
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          padding: '0.85rem 1.25rem',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border)',
          fontSize: '0.85rem'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <Clock size={16} color="var(--accent)" style={{ flexShrink: 0 }} />
          <span>
            <strong>Observation Baseline Period:</strong>{' '}
            {dataPeriod.start ? new Date(dataPeriod.start).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : 'N/A'} —{' '}
            {dataPeriod.end ? new Date(dataPeriod.end).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : 'N/A'}{' '}
            <span className="text-muted">({dataPeriod.days_covered ? `${dataPeriod.days_covered} days archival archive` : 'Zero observations'})</span>
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="badge badge-neutral" style={{ fontSize: '0.7rem' }}>
            15-Min Continuous CAAQMS Sampling
          </span>
        </div>
      </div>

      {/* 3. Coverage Alert If Non-Active Region */}
      {isNoData && (
        <div className="alert-callout alert-callout-warning">
          <AlertCircle size={22} color="var(--warning)" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <h4 style={{ color: 'var(--primary)', marginBottom: '0.25rem', fontSize: '0.95rem' }}>
              Data Feeds Scheduled for {region?.name}
            </h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.5, margin: 0 }}>
              {summary?.geographic_scope?.coverage_description || 
                "Geographic boundaries and candidate industrial classifications are registered in the catalog, but high-frequency observation parquets have not yet been ingested."}
            </p>
            <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Switch to <strong>Indore, Madhya Pradesh</strong> in the geographic scope selector to inspect 8,211 verified readings and 48 confirmed events.
            </div>
          </div>
        </div>
      )}

      {/* 4. Top Key Metric Cards (Visual Hierarchy) */}
      <div className="grid-cols-4">
        
        {/* Metric 1: Pollution Events (Hero Accent) */}
        <div className="card" style={{ borderLeft: '4px solid var(--critical)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)' }}>
              Pollution Events
            </span>
            <AlertTriangle size={17} color="var(--critical)" />
          </div>
          <div style={{ fontSize: '2.4rem', fontWeight: 700, color: isNoData ? 'var(--text-secondary)' : 'var(--critical)', lineHeight: 1.1, margin: '0.25rem 0' }}>
            {summary.total_events}
          </div>
          <div style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
            {isNoData ? "0 registered spikes" : "Confirmed past-only spikes (Z ≥ 2.0σ)"}
          </div>
        </div>

        {/* Metric 2: Total Observations */}
        <div className="card" style={{ borderLeft: '4px solid var(--accent)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)' }}>
              Total Observations
            </span>
            <Activity size={17} color="var(--accent)" />
          </div>
          <div style={{ fontSize: '2.4rem', fontWeight: 700, color: 'var(--primary)', lineHeight: 1.1, margin: '0.25rem 0' }}>
            {summary.total_observations.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.775rem', color: isNoData ? 'var(--text-secondary)' : 'var(--success)', fontWeight: 600 }}>
            {isNoData ? "Awaiting feed ingest" : "15-minute sampling telemetry"}
          </div>
        </div>

        {/* Metric 3: Monitoring Stations */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)' }}>
              Monitoring Nodes
            </span>
            <Radio size={17} color="var(--primary)" />
          </div>
          <div style={{ fontSize: '2.4rem', fontWeight: 700, color: 'var(--primary)', lineHeight: 1.1, margin: '0.25rem 0' }}>
            {summary.total_stations}
          </div>
          <div style={{ fontSize: '0.775rem', color: 'var(--text-secondary)' }}>
            {isNoData ? "0 nodes online" : "Active continuous CAAQMS stations"}
          </div>
        </div>

        {/* Metric 4: Candidate Industrial Facilities */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)' }}>
              Candidate Facilities
            </span>
            <Factory size={17} color="var(--primary)" />
          </div>
          <div style={{ fontSize: '2.4rem', fontWeight: 700, color: 'var(--primary)', lineHeight: 1.1, margin: '0.25rem 0' }}>
            {summary.source_candidates_evaluated}
          </div>
          <div style={{ fontSize: '0.775rem', color: 'var(--text-secondary)' }}>
            {isNoData ? "Industrial hubs defined" : "Mapped facilities in 25 km radius"}
          </div>
        </div>

      </div>

      {/* 5. Monitored Stations Breakdown Table */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', color: 'var(--primary)', marginBottom: '0.2rem' }}>
              Monitoring Stations & Telemetry Summary
            </h3>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', margin: 0 }}>
              Station-level operational status, observation volume, and detected pollution elevation counts.
            </p>
          </div>
          <span className="badge badge-neutral">
            {summary.stations.length} Station Nodes
          </span>
        </div>

        {summary.stations.length === 0 ? (
          <div style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-secondary)', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)' }}>
            <AlertCircle size={28} color="var(--warning)" style={{ margin: '0 auto 0.75rem' }} />
            <p style={{ margin: 0 }}>No monitoring station observations loaded for {region?.name}. Select Indore to inspect high-frequency station observations.</p>
          </div>
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Station Name</th>
                  <th style={{ textAlign: 'right' }}>Observations</th>
                  <th style={{ textAlign: 'right' }}>Latest PM2.5</th>
                  <th style={{ textAlign: 'right' }}>Max Recorded Peak</th>
                  <th style={{ textAlign: 'center' }}>Spikes Detected</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {summary.stations.map((st) => (
                  <tr key={st.station}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Radio size={14} color="var(--accent)" />
                        <strong>{st.station} CAAQMS</strong>
                      </div>
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                      {st.observations.toLocaleString()}
                    </td>
                    <td style={{
                      textAlign: 'right',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 700,
                      color: st.latest_pm25 > 60 ? 'var(--critical)' : 'var(--text-primary)'
                    }}>
                      {st.latest_pm25 ? `${st.latest_pm25.toFixed(1)} µg/m³` : 'N/A'}
                    </td>
                    <td style={{ 
                      textAlign: 'right', 
                      fontFamily: 'var(--font-mono)', 
                      fontWeight: 700, 
                      color: 'var(--critical)' 
                    }}>
                      {st.maximum_pm25 ? `${st.maximum_pm25.toFixed(1)} µg/m³` : 'N/A'}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <span className="badge badge-critical">
                        {st.detected_events} Spikes
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button 
                        onClick={() => {
                          if (onNavigateToEvents) {
                            onNavigateToEvents(st.station);
                          } else if (onNavigateToEvent) {
                            onNavigateToEvent(null);
                          }
                        }}
                        className="btn-secondary btn-sm"
                        title={`Inspect events at ${st.station}`}
                      >
                        Inspect Spikes <ArrowRight size={11} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 6. Scientific & Regulatory Caveat */}
      <div 
        style={{
          padding: '1rem 1.25rem',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border)',
          fontSize: '0.8rem',
          color: 'var(--text-secondary)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          lineHeight: 1.5
        }}
      >
        <Shield size={18} color="var(--accent)" style={{ flexShrink: 0 }} />
        <div>
          <strong style={{ color: 'var(--primary)' }}>Scientific Governance Disclaimer: </strong>
          {summary.scientific_caveat}
        </div>
      </div>

    </div>
  );
}
