import React, { useEffect, useState, useMemo } from 'react';
import { fetchEvents, fetchStations } from '../api';
import { AlertTriangle, Filter, ArrowRight, RefreshCw, Search, AlertCircle, Compass } from 'lucide-react';

export default function PollutionEventsPage({ region, onSelectEvent, initialStation }) {
  const [station, setStation] = useState(initialStation || '');
  const [searchTerm, setSearchTerm] = useState('');
  const [stationsList, setStationsList] = useState([]);
  const [eventsData, setEventsData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Sync initialStation if provided from outside navigation
  useEffect(() => {
    if (initialStation !== undefined) {
      setStation(initialStation || '');
    }
  }, [initialStation]);

  // Load stations for current region
  useEffect(() => {
    fetchStations(region?.city || "", region?.state_ut || "")
      .then((res) => {
        setStationsList(res.stations || []);
        if (initialStation) {
          setStation(initialStation);
        } else {
          setStation('');
        }
      })
      .catch(() => setStationsList([]));
  }, [region, initialStation]);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await fetchEvents(station, region?.city || "");
      setEventsData(res);
    } catch (err) {
      console.error("Error loading events:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [station, region]);

  const isNoData = eventsData?.coverage_status === 'no_usable_data' || (eventsData && eventsData.total === 0);

  // Client-side quick search over loaded events
  const filteredEvents = useMemo(() => {
    const list = eventsData?.events || [];
    if (!searchTerm.trim()) return list;
    const term = searchTerm.toLowerCase();
    return list.filter(e => 
      e.event_id?.toLowerCase().includes(term) ||
      e.station?.toLowerCase().includes(term)
    );
  }, [eventsData, searchTerm]);

  const renderLifecycleBadge = (status) => {
    switch (status) {
      case 'active':
        return <span className="badge badge-critical">🔴 Active Spike</span>;
      case 'resolved':
        return <span className="badge badge-success">✓ Resolved</span>;
      case 'recent':
        return <span className="badge badge-warning">Recent (≤30d)</span>;
      case 'historical':
        return <span className="badge badge-info">Historical Archive</span>;
      default:
        return <span className="badge badge-info">{status || 'Historical'}</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      
      {/* Page Header */}
      <div className="page-header" style={{ marginBottom: 0 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
            <span className="badge badge-info">
              Scope: {region?.name || "All Regions"}
            </span>
            <span className="badge badge-critical">
              {eventsData?.total || 0} Statistical Spikes Detected
            </span>
          </div>
          <h1 className="page-title">Detected Pollution Events</h1>
          <p className="page-subtitle">
            Anomalous PM2.5 elevation episodes detected via past-only rolling baseline ($Z \ge 2.0\sigma$) without future data leakage.
          </p>
        </div>

        {/* Filter Controls */}
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Quick Search */}
          <div style={{ position: 'relative' }}>
            <input 
              type="search"
              placeholder="Search Event ID or station..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-control"
              style={{ width: '220px', paddingLeft: '2rem' }}
            />
            <Search size={14} color="var(--text-secondary)" style={{ position: 'absolute', left: '0.65rem', top: '50%', transform: 'translateY(-50%)' }} />
          </div>

          {/* Station Filter */}
          <select 
            value={station} 
            onChange={(e) => setStation(e.target.value)}
            className="form-control"
            style={{ fontWeight: 500, minWidth: '180px' }}
          >
            <option value="">All Stations in {region?.city || "Region"}</option>
            {stationsList.map((st) => (
              <option key={st.station_id} value={st.station_name}>
                {st.station_name} CAAQMS
              </option>
            ))}
          </select>

          <button onClick={loadData} className="btn-secondary btn-sm" title="Refresh events list">
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>

      {/* Events Table Card */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', color: 'var(--primary)', marginBottom: '0.2rem' }}>
              Confirmed Elevation Episodes {eventsData ? `(${filteredEvents.length} shown of ${eventsData.total})` : ''}
            </h3>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', margin: 0 }}>
              Click "Investigate" on any event to inspect meteorological wind alignment and screen candidate industrial sources.
            </p>
          </div>
          <span className="badge badge-neutral">
            Threshold: Z-Score ≥ 2.0σ
          </span>
        </div>

        {loading ? (
          <div style={{ padding: '3.5rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.75rem', display: 'block', color: 'var(--accent)' }} />
            <p style={{ margin: 0 }}>Loading detected events for {region?.name}...</p>
          </div>
        ) : isNoData ? (
          <div style={{ padding: '3.5rem 2rem', textAlign: 'center', color: 'var(--text-secondary)', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)' }}>
            <AlertCircle size={32} color="var(--warning)" style={{ margin: '0 auto 1rem' }} />
            <h4 style={{ color: 'var(--primary)', marginBottom: '0.5rem', fontSize: '1.1rem' }}>No Pollution Events for {region?.name}</h4>
            <p style={{ fontSize: '0.875rem', maxWidth: '540px', margin: '0 auto' }}>
              No pollution spikes have been detected because observation records are not yet ingested for this region. Switch to <strong>Indore, Madhya Pradesh</strong> in the top geographic scope selector to inspect 48 confirmed events.
            </p>
          </div>
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Event ID</th>
                  <th>Lifecycle Status</th>
                  <th>Station</th>
                  <th>Start Time (UTC)</th>
                  <th>End Time (UTC)</th>
                  <th style={{ textAlign: 'right' }}>Duration</th>
                  <th style={{ textAlign: 'right' }}>Peak PM2.5</th>
                  <th style={{ textAlign: 'center' }}>Peak Z-Score</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredEvents.map((evt) => (
                  <tr key={evt.event_id}>
                    <td>
                      <span className="badge badge-critical text-mono" style={{ fontSize: '0.725rem' }}>
                        {evt.event_id}
                      </span>
                    </td>
                    <td>{renderLifecycleBadge(evt.temporal_status)}</td>
                    <td><strong>{evt.station}</strong></td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.785rem' }}>
                      {new Date(evt.start_time).toUTCString()}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.785rem' }}>
                      {new Date(evt.end_time).toUTCString()}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                      {evt.duration_minutes} min
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--critical)' }}>
                      {evt.peak_pm25.toFixed(1)} µg/m³
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>
                        +{evt.peak_z_score ? evt.peak_z_score.toFixed(2) : '2.0+'} σ
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button 
                        onClick={() => onSelectEvent(evt.event_id)}
                        className="btn-primary btn-sm"
                        title={`Open investigation workspace for ${evt.event_id}`}
                      >
                        Investigate <ArrowRight size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
                {filteredEvents.length === 0 && (
                  <tr>
                    <td colSpan="9" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                      No events match search term "{searchTerm}".
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
