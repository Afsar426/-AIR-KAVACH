import React, { useEffect, useState } from 'react';
import { fetchEventAttribution } from '../api';
import { Factory, Compass, HelpCircle, RefreshCw, Filter, Shield, AlertCircle, ArrowRight, Sparkles } from 'lucide-react';

export default function SourceAttributionPage({ region, onSelectEvent }) {
  const [eventId, setEventId] = useState('EVT-0001');
  const [attribution, setAttribution] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await fetchEventAttribution(eventId);
      setAttribution(res);
    } catch (err) {
      console.error("Error loading attribution:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [eventId]);

  const candidates = attribution?.candidates || [];
  const quickEvents = ['EVT-0001', 'EVT-0007', 'EVT-0017', 'EVT-0029', 'EVT-0047', 'EVT-0048'];

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
              Heuristic Screening Model
            </span>
          </div>
          <h1 className="page-title">Industrial Source Candidate Attribution</h1>
          <p className="page-subtitle">
            Heuristic geospatial screening combining exponential distance decay and surface wind vector trigonometry to prioritize facilities for ground inspection.
          </p>
        </div>

        {/* Event Selector Input */}
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <label htmlFor="attribution-event-id" style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Select Event ID:
          </label>
          <input 
            id="attribution-event-id"
            type="text" 
            value={eventId} 
            onChange={(e) => setEventId(e.target.value.toUpperCase())} 
            placeholder="e.g. EVT-0001"
            className="form-control text-mono"
            style={{ width: '130px', fontWeight: 600 }}
          />
          <button onClick={loadData} className="btn-secondary btn-sm" title="Refresh attribution ranking">
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>

      {/* Quick Event Pills */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.825rem' }}>
        <span className="text-muted" style={{ fontWeight: 600 }}>Representative Events:</span>
        {quickEvents.map(eid => (
          <button 
            key={eid}
            onClick={() => setEventId(eid)}
            className={`btn-ghost btn-sm text-mono ${eventId === eid ? 'badge-info' : ''}`}
            style={{ 
              backgroundColor: eventId === eid ? 'var(--primary-subtle)' : 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
              fontWeight: eventId === eid ? 700 : 500,
              color: eventId === eid ? 'var(--primary)' : 'var(--text-secondary)',
              padding: '0.25rem 0.6rem'
            }}
          >
            {eid}
          </button>
        ))}
      </div>

      {/* Formula & Weight Card */}
      <div className="card">
        <h3 style={{ fontSize: '1.1rem', marginBottom: '0.5rem', color: 'var(--primary)' }}>
          Attribution Methodology & Scoring Formulations
        </h3>
        <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
          Scores partition candidate proximity and upwind consistency across facilities within a 25 km radius.
        </p>

        <div className="grid-cols-3">
          <div style={{ padding: '0.9rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <strong style={{ fontSize: '0.825rem', color: 'var(--primary)', display: 'block', marginBottom: '0.25rem' }}>
              1. Distance Decay (30% Weight)
            </strong>
            <p style={{ fontSize: '0.785rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
              Formula: <code style={{ backgroundColor: 'var(--bg-surface)', padding: '0.1rem 0.3rem', borderRadius: '3px' }}>exp(-d / 5.0)</code><br />
              Exponential decay scaled over a 5 km characteristic buffer.
            </p>
          </div>

          <div style={{ padding: '0.9rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <strong style={{ fontSize: '0.825rem', color: 'var(--primary)', display: 'block', marginBottom: '0.25rem' }}>
              2. Wind Alignment (70% Weight)
            </strong>
            <p style={{ fontSize: '0.785rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
              Formula: <code style={{ backgroundColor: 'var(--bg-surface)', padding: '0.1rem 0.3rem', borderRadius: '3px' }}>cos(θ_sensor→fac - θ_wind_from)</code><br />
              Meteorological vector convention (direction wind originates FROM).
            </p>
          </div>

          <div style={{ padding: '0.9rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <strong style={{ fontSize: '0.825rem', color: 'var(--primary)', display: 'block', marginBottom: '0.25rem' }}>
              3. Normalized Screening Score Share
            </strong>
            <p style={{ fontSize: '0.785rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
              Formula: <code style={{ backgroundColor: 'var(--bg-surface)', padding: '0.1rem 0.3rem', borderRadius: '3px' }}>score / sum(all_scores)</code><br />
              Normalized index across candidates. <em>Not a causal probability.</em>
            </p>
          </div>
        </div>
      </div>

      {/* Attribution Candidates Table */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', color: 'var(--primary)', marginBottom: '0.2rem' }}>
              Ranked Candidate Facilities for <span className="text-mono">{eventId}</span>
            </h3>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', margin: 0 }}>
              Prioritization ranking for environmental compliance inspection teams.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {attribution?.evidence_sufficiency === 'insufficient_evidence' ? (
              <span className="badge badge-warning">Insufficient Evidence (&lt; 0.35)</span>
            ) : (
              <span className="badge badge-success">Screening Evidence Sufficient</span>
            )}
            {onSelectEvent && (
              <button 
                onClick={() => onSelectEvent(eventId)}
                className="btn-secondary btn-sm"
                title="Open comprehensive investigation workspace"
              >
                Inspect in Workspace <ArrowRight size={12} />
              </button>
            )}
          </div>
        </div>

        {loading ? (
          <div style={{ padding: '3.5rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.75rem', display: 'block', color: 'var(--accent)' }} />
            <p style={{ margin: 0 }}>Loading candidate attribution scores for {eventId}...</p>
          </div>
        ) : candidates.length === 0 ? (
          <div style={{ padding: '3rem 2rem', textAlign: 'center', color: 'var(--text-secondary)', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)' }}>
            <AlertCircle size={30} color="var(--warning)" style={{ margin: '0 auto 0.75rem' }} />
            <p style={{ margin: 0, fontWeight: 500 }}>No candidate facility records found for {eventId}. Ensure the event ID exists in the active dataset.</p>
          </div>
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: '60px' }}>Rank</th>
                  <th>Facility Name</th>
                  <th>Category</th>
                  <th style={{ textAlign: 'right' }}>Distance</th>
                  <th style={{ textAlign: 'right' }}>Distance Decay</th>
                  <th>Wind Alignment</th>
                  <th style={{ textAlign: 'right' }}>Score</th>
                  <th style={{ textAlign: 'right' }}>Screening Share</th>
                  <th>Evidence Classification</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c) => (
                  <tr key={c.factory_id}>
                    <td style={{ fontWeight: 700 }}>#{c.factory_rank}</td>
                    <td>
                      <strong>{c.factory_name}</strong>
                      <div style={{ fontSize: '0.725rem', color: 'var(--text-secondary)' }}>ID: {c.factory_id}</div>
                    </td>
                    <td>
                      <span className="badge badge-neutral" style={{ fontSize: '0.7rem' }}>
                        {c.facility_category}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                      {c.distance_km.toFixed(2)} km
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                      {c.distance_score.toFixed(3)}
                    </td>
                    <td>
                      <span className={`badge ${
                        c.wind_relationship?.includes('strong_upwind') ? 'badge-success' :
                        c.wind_relationship?.includes('upwind') ? 'badge-info' : 'badge-warning'
                      }`} style={{ fontSize: '0.7rem' }}>
                        <Compass size={11} style={{ marginRight: '3px' }} />
                        {c.wind_relationship?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--primary)' }}>
                      {c.attribution_score.toFixed(3)}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                      <strong>{((c.screening_score_share || c.relative_likelihood || 0) * 100).toFixed(1)}%</strong>
                    </td>
                    <td>
                      <span className="badge badge-info" style={{ fontSize: '0.675rem' }}>
                        {c.evidence_label?.replace(/_/g, ' ') || 'Screening Candidate'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Scientific Caveat Footer */}
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
          Candidate attribution scores indicate geographic proximity and upwind consistency within a heuristic screening framework. They do not constitute legal proof of industrial emissions or regulatory non-compliance.
        </div>
      </div>

    </div>
  );
}
