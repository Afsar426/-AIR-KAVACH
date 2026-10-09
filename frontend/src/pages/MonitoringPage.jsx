import React, { useEffect, useState } from 'react';
import { fetchObservations, fetchStations } from '../api';
import { Activity, Filter, RefreshCw, Calendar, Database, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';

export default function MonitoringPage({ region }) {
  const [station, setStation] = useState('');
  const [stationsList, setStationsList] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);

  // Load available stations for current region
  useEffect(() => {
    fetchStations(region?.city || "", region?.state_ut || "")
      .then((res) => {
        const list = res.stations || [];
        setStationsList(list);
        setStation(''); // Reset selected station on region change
        setPage(0);
      })
      .catch(() => setStationsList([]));
  }, [region]);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await fetchObservations(station, region?.city || "", 50, page * 50);
      setData(res);
    } catch (err) {
      console.error("Error loading observations:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [station, page, region]);

  const isNoData = data?.coverage_status === 'no_usable_data' || (data && data.total === 0);
  const totalPages = Math.ceil((data?.total || 1) / 50);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      
      {/* Page Header */}
      <div className="page-header" style={{ marginBottom: 0 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
            <span className="badge badge-info">
              Scope: {region?.name || "All Regions"}
            </span>
            <span className="badge badge-neutral">
              15-Min Continuous Telemetry
            </span>
          </div>
          <h1 className="page-title">Continuous Air Quality Monitoring</h1>
          <p className="page-subtitle">
            High-frequency ambient air quality observations recorded across continuous monitoring stations in {region?.name || "India"}.
          </p>
        </div>

        {/* Station Filter Dropdown */}
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <label htmlFor="station-filter" style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Filter Station:
          </label>
          <select 
            id="station-filter"
            value={station} 
            onChange={(e) => { setStation(e.target.value); setPage(0); }}
            className="form-control"
            style={{ fontWeight: 500, minWidth: '220px' }}
          >
            <option value="">All Stations in {region?.city || "Region"}</option>
            {stationsList.map((st) => (
              <option key={st.station_id} value={st.station_name}>
                {st.station_name} CAAQMS
              </option>
            ))}
          </select>
          <button onClick={loadData} className="btn-secondary btn-sm" title="Refresh observations">
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>

      {/* Observation Table Card */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', color: 'var(--primary)', marginBottom: '0.2rem' }}>
              Observation Records {data ? `(${data.total.toLocaleString()} Total Readings)` : ''}
            </h3>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', margin: 0 }}>
              Chronological 15-minute sampling intervals normalized across CPCB specifications.
            </p>
          </div>
          <span className="badge badge-neutral">
            50 Rows / Page
          </span>
        </div>

        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.75rem', display: 'block', color: 'var(--accent)' }} />
            <p style={{ margin: 0 }}>Loading observations for {region?.name}...</p>
          </div>
        ) : isNoData ? (
          <div style={{ padding: '3.5rem 2rem', textAlign: 'center', color: 'var(--text-secondary)', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)' }}>
            <AlertCircle size={32} color="var(--warning)" style={{ margin: '0 auto 1rem' }} />
            <h4 style={{ color: 'var(--primary)', marginBottom: '0.5rem', fontSize: '1.1rem' }}>No Observation Records for {region?.name}</h4>
            <p style={{ fontSize: '0.875rem', maxWidth: '540px', margin: '0 auto' }}>
              High-frequency monitoring feeds have not yet been ingested for this region. Switch to <strong>Indore, Madhya Pradesh</strong> in the top geographic scope selector to inspect 8,211 verified historical readings.
            </p>
          </div>
        ) : (
          <>
            <div className="data-table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Timestamp (UTC)</th>
                    <th>Monitoring Station</th>
                    <th>Sensor ID</th>
                    <th>Parameter</th>
                    <th style={{ textAlign: 'right' }}>Observed Concentration</th>
                    <th>Unit</th>
                    <th style={{ textAlign: 'center' }}>Air Quality Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.observations.map((obs, idx) => (
                    <tr key={idx}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                        {new Date(obs.timestamp).toUTCString()}
                      </td>
                      <td>
                        <strong>{obs.station}</strong>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', fontSize: '0.785rem' }}>
                        {obs.sensor_id || 'N/A'}
                      </td>
                      <td>
                        <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>
                          {obs.parameter.toUpperCase()}
                        </span>
                      </td>
                      <td style={{
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 700,
                        color: obs.value > 100 ? 'var(--critical)' : obs.value > 60 ? 'var(--warning)' : 'var(--text-primary)'
                      }}>
                        {obs.value.toFixed(1)}
                      </td>
                      <td style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                        {obs.unit}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <span className={`badge ${
                          obs.value > 90 ? 'badge-critical' : 
                          obs.value > 60 ? 'badge-warning' : 'badge-success'
                        }`} style={{ fontSize: '0.675rem' }}>
                          {obs.value > 90 ? 'Critical Spike' : obs.value > 60 ? 'Elevated' : 'Normal Baseline'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border)', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                Showing page <strong>{page + 1}</strong> of <strong>{totalPages}</strong> ({data?.total.toLocaleString()} total observations)
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <button 
                  disabled={page === 0} 
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  className="btn-secondary btn-sm"
                  title="Previous page"
                >
                  <ChevronLeft size={14} /> Previous
                </button>
                <button 
                  disabled={(page + 1) * 50 >= (data?.total || 0)} 
                  onClick={() => setPage(p => p + 1)}
                  className="btn-secondary btn-sm"
                  title="Next page"
                >
                  Next <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

    </div>
  );
}
