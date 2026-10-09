import React, { useEffect, useState } from 'react';
import { postGenerateReport, fetchReportsList, fetchReportById } from '../api';
import { FileText, Download, CheckCircle2, RefreshCw, Clock, Shield, Eye } from 'lucide-react';

export default function ReportsPage() {
  const [eventId, setEventId] = useState('EVT-0001');
  const [report, setReport] = useState(null);
  const [reportsList, setReportsList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingList, setLoadingList] = useState(true);

  const loadReports = async () => {
    try {
      setLoadingList(true);
      const res = await fetchReportsList();
      setReportsList(res?.reports || []);
    } catch (err) {
      console.warn("Error fetching reports list:", err);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const handleGenerate = async (e) => {
    if (e) e.preventDefault();
    if (!eventId.trim()) return;

    try {
      setLoading(true);
      const res = await postGenerateReport(eventId);
      setReport(res);
      await loadReports();
    } catch (err) {
      alert("Error compiling report: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleViewReport = async (repId) => {
    try {
      const rep = await fetchReportById(repId);
      setReport(rep);
    } catch (err) {
      alert("Error loading report: " + err.message);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      <div className="page-header">
        <div>
          <h2 className="page-title">Investigation Reports & Audit History</h2>
          <p className="page-subtitle">
            Reproducible environmental intelligence dossiers compiling observed sensor facts, local wind vectors, source candidate screenings, and provenance traces.
          </p>
        </div>
      </div>

      {/* Generation Bar */}
      <form onSubmit={handleGenerate} className="card" style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <FileText size={20} color="var(--accent)" />
        <label htmlFor="report-event-id-input" style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
          Compile Report for Event ID:
        </label>
        <input 
          id="report-event-id-input"
          type="text" 
          value={eventId} 
          onChange={(e) => setEventId(e.target.value)} 
          placeholder="e.g. EVT-0001"
          style={{
            padding: '0.55rem 0.85rem',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.85rem',
            color: 'var(--text-primary)',
            minWidth: '180px'
          }}
        />
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? <RefreshCw size={16} className="spin" /> : <Download size={16} />} Compile & Persist Report
        </button>
      </form>

      {/* Display Active Generated Report */}
      {report && (
        <div className="card" style={{ borderLeft: '4px solid var(--accent)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
            <div>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.35rem' }}>
                <span className="badge badge-success">{report.report_id}</span>
                <span className="badge badge-info">{report.event_id}</span>
              </div>
              <h3 style={{ fontSize: '1.35rem', color: 'var(--primary)', margin: 0 }}>
                AIR KAVACH Official Investigation Dossier
              </h3>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                Generated: {new Date(report.generated_at).toLocaleString()} | Scope: {report.geographic_scope || "Indore, Madhya Pradesh"}
              </div>
            </div>
          </div>

          {/* Executive Summary */}
          <div style={{ padding: '1.1rem 1.25rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-md)', marginBottom: '1.25rem', border: '1px solid var(--border)' }}>
            <h4 style={{ fontSize: '0.9rem', marginBottom: '0.4rem', color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
              Executive Investigation Summary
            </h4>
            <p style={{ fontSize: '0.925rem', color: 'var(--text-primary)', lineHeight: 1.6, margin: 0 }}>
              {report.investigation_summary}
            </p>
          </div>

          {/* Observed Facts Breakdown if available */}
          {report.observed_facts && Object.keys(report.observed_facts).length > 0 && (
            <div style={{ marginBottom: '1.25rem' }}>
              <h4 style={{ fontSize: '0.9rem', marginBottom: '0.65rem', color: 'var(--primary)' }}>
                Observed In-Situ Environmental Facts
              </h4>
              <div className="grid-cols-4">
                <div style={{ padding: '0.75rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Station</div>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem', marginTop: '0.2rem' }}>{report.observed_facts.station_name || report.observed_facts.station || 'N/A'}</div>
                </div>
                <div style={{ padding: '0.75rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Peak Observed PM2.5</div>
                  <div style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--critical)', marginTop: '0.2rem' }}>
                    {report.observed_facts.peak_pm25 ? `${report.observed_facts.peak_pm25.toFixed(1)} µg/m³` : 'N/A'}
                  </div>
                </div>
                <div style={{ padding: '0.75rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Rolling Baseline</div>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem', marginTop: '0.2rem' }}>
                    {report.observed_facts.baseline_mean ? `${report.observed_facts.baseline_mean.toFixed(1)} µg/m³` : 'N/A'}
                  </div>
                </div>
                <div style={{ padding: '0.75rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Duration</div>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem', marginTop: '0.2rem' }}>
                    {report.observed_facts.duration_hours ? `${report.observed_facts.duration_hours}h` : 'N/A'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Candidate Rankings Table if available */}
          {report.candidate_rankings && report.candidate_rankings.length > 0 && (
            <div style={{ marginBottom: '1.25rem' }}>
              <h4 style={{ fontSize: '0.9rem', marginBottom: '0.65rem', color: 'var(--primary)' }}>
                Industrial Candidate Facility Rankings (Geometric Alignment Screening)
              </h4>
              <div className="data-table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Facility Name</th>
                      <th>Category</th>
                      <th>Distance</th>
                      <th>Wind Alignment</th>
                      <th>Screening Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.candidate_rankings.slice(0, 5).map((c, i) => (
                      <tr key={c.factory_id || i}>
                        <td><strong>#{i + 1}</strong></td>
                        <td><strong>{c.name || c.factory_name}</strong></td>
                        <td><span className="badge badge-info">{c.category || 'Industrial'}</span></td>
                        <td>{c.distance_km ? `${c.distance_km.toFixed(1)} km` : 'N/A'}</td>
                        <td>{c.wind_alignment != null ? `${(c.wind_alignment * 100).toFixed(0)}%` : 'N/A'}</td>
                        <td><strong>{c.attribution_score != null ? (c.attribution_score * 100).toFixed(1) : 'N/A'}</strong></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Disclaimer & Limitations */}
          {report.disclaimer && (
            <div className="alert-callout alert-callout-warning" style={{ marginBottom: '1.25rem' }}>
              <Shield size={18} color="var(--warning)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div style={{ fontSize: '0.825rem', lineHeight: '1.5' }}>
                <strong>Scientific Safeguard Notice:</strong> {report.disclaimer}
              </div>
            </div>
          )}

          {/* Collapsible Full JSON Evidence Payload */}
          <details style={{ marginTop: '0.75rem', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '0.75rem 1rem', backgroundColor: 'var(--bg-main)' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 600, fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
              Inspect Full Reproducible Evidence Payload (JSON & Execution Trace)
            </summary>
            <pre style={{ backgroundColor: '#141F2E', color: '#A8C5DA', padding: '1rem', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', overflowX: 'auto', maxHeight: '350px', marginTop: '0.75rem' }}>
              {JSON.stringify(report.result_payload || report, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {/* Historical Persisted Reports List */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ fontSize: '1.15rem', color: 'var(--primary)' }}>
            Persisted Investigation Reports on Disk
          </h3>
          <button onClick={loadReports} className="btn-secondary" style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}>
            <RefreshCw size={12} /> Refresh List
          </button>
        </div>

        {loadingList ? (
          <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            Loading historical reports...
          </div>
        ) : reportsList.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)' }}>
            No saved reports yet. Enter an Event ID above and click "Compile & Persist Report".
          </div>
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Report ID</th>
                  <th>Event ID</th>
                  <th>Generated (UTC)</th>
                  <th>Summary Preview</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {reportsList.map((r) => (
                  <tr key={r.report_id}>
                    <td><code>{r.report_id}</code></td>
                    <td><span className="badge badge-critical">{r.event_id}</span></td>
                    <td>{new Date(r.generated_at).toLocaleString()}</td>
                    <td style={{ fontSize: '0.8rem', maxWidth: '350px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {r.summary}
                    </td>
                    <td>
                      <button 
                        onClick={() => handleViewReport(r.report_id)}
                        className="btn-secondary"
                        style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem', display: 'flex', alignItems: 'center', gap: '3px' }}
                      >
                        <Eye size={12} /> View Dossier
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
