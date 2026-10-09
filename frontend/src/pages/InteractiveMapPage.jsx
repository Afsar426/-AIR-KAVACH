import React, { useEffect, useState, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, CircleMarker, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { fetchMapData } from '../api';
import { Layers, RefreshCw, Compass, Factory, Radio, MapPin, AlertCircle, Info } from 'lucide-react';

// Custom Marker Icons using brand colors
const stationIcon = L.divIcon({
  className: 'custom-station-icon',
  html: `<div style="background-color:#1D3557; color:#FFFFFF; padding:4px 8px; border-radius:12px; font-weight:600; font-size:10px; border:2px solid #FFFFFF; box-shadow:0 2px 6px rgba(0,0,0,0.3); white-space:nowrap; display:flex; align-items:center; gap:3px;">📍 Station</div>`,
  iconSize: [68, 24],
  iconAnchor: [34, 12]
});

const factoryIcon = L.divIcon({
  className: 'custom-factory-icon',
  html: `<div style="background-color:#3C8D91; color:#FFFFFF; padding:3px 7px; border-radius:10px; font-weight:600; font-size:9px; border:1px solid #FFFFFF; box-shadow:0 2px 5px rgba(0,0,0,0.25); white-space:nowrap; display:flex; align-items:center; gap:3px;">🏭 Factory</div>`,
  iconSize: [60, 20],
  iconAnchor: [30, 10]
});

// Helper component to auto-recenter map when region changes
function ChangeMapView({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
}

export default function InteractiveMapPage({ region }) {
  const [mapData, setMapData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Layer Toggles
  const [showStations, setShowStations] = useState(true);
  const [showFactories, setShowFactories] = useState(true);
  const [showEvents, setShowEvents] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await fetchMapData(region?.city || "");
      setMapData(res);
    } catch (err) {
      console.error("Error loading map data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [region]);

  const mapCenter = useMemo(() => {
    if (region && region.city === "Indore") {
      return [22.7196, 75.8577];
    } else if (region && region.city === "Delhi") {
      return [28.6139, 77.2090];
    } else if (region && region.city === "Mumbai") {
      return [19.0760, 72.8777];
    } else if (region && region.city === "Ahmedabad") {
      return [23.0225, 72.5714];
    } else if (region && region.city === "Bengaluru") {
      return [12.9716, 77.5946];
    } else if (region && region.city === "Kanpur") {
      return [26.4499, 80.3319];
    }
    return [22.7196, 75.8577]; // Default
  }, [region]);

  const mapZoom = (region && region.city) ? 12 : 5;

  // Extract unique factories from map events
  const factoriesList = useMemo(() => {
    if (!mapData?.events) return [];
    const map = new Map();
    for (const evt of mapData.events) {
      for (const cand of (evt.candidates || [])) {
        const f = cand.factory;
        if (f && f.id && !map.has(f.id)) {
          map.set(f.id, {
            id: f.id,
            name: f.name || "Industrial Facility",
            category: f.category || "industrial",
            latitude: f.latitude,
            longitude: f.longitude,
          });
        }
      }
    }
    return Array.from(map.values());
  }, [mapData]);

  const isNoData = region && region.city && region.city !== "Indore";

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', minHeight: 'calc(100vh - 200px)' }}>
      
      {/* Map Header & Controls */}
      <div className="page-header" style={{ marginBottom: 0 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
            <span className="badge badge-info">
              Scope: {region?.name || "Pan-India"}
            </span>
            {isNoData && (
              <span className="badge badge-warning">
                <AlertCircle size={11} style={{ marginRight: '2px' }} />
                Boundary Mapped (Feed Pending)
              </span>
            )}
          </div>
          <h1 className="page-title">Geospatial Environmental Map</h1>
          <p className="page-subtitle">
            Geospatial representation of CPCB continuous monitoring stations, candidate industrial facilities, and statistical pollution spike epicenters.
          </p>
        </div>

        {/* Layer Controls Bar */}
        <div 
          style={{
            display: 'flex',
            gap: '1rem',
            alignItems: 'center',
            backgroundColor: 'var(--bg-surface)',
            padding: '0.5rem 1rem',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border)',
            boxShadow: 'var(--shadow-xs)',
            flexWrap: 'wrap'
          }}
          aria-label="Layer visibility controls"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--primary)', fontWeight: 600, fontSize: '0.8rem' }}>
            <Layers size={15} color="var(--accent)" /> Layers:
          </div>
          
          <label style={{ fontSize: '0.825rem', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer', color: 'var(--text-primary)' }}>
            <input 
              type="checkbox" 
              checked={showStations} 
              onChange={(e) => setShowStations(e.target.checked)} 
              style={{ accentColor: 'var(--primary)' }}
            /> 
            Stations
          </label>

          <label style={{ fontSize: '0.825rem', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer', color: 'var(--text-primary)' }}>
            <input 
              type="checkbox" 
              checked={showEvents} 
              onChange={(e) => setShowEvents(e.target.checked)} 
              style={{ accentColor: 'var(--critical)' }}
            /> 
            Events
          </label>

          <label style={{ fontSize: '0.825rem', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer', color: 'var(--text-primary)' }}>
            <input 
              type="checkbox" 
              checked={showFactories} 
              onChange={(e) => setShowFactories(e.target.checked)} 
              style={{ accentColor: 'var(--accent)' }}
            /> 
            Factories
          </label>

          <button onClick={loadData} className="btn-secondary btn-sm" style={{ marginLeft: '0.25rem' }}>
            <RefreshCw size={12} /> Reload
          </button>
        </div>
      </div>

      {/* Map Box Container */}
      <div 
        className="card" 
        style={{ 
          flex: 1, 
          minHeight: '520px', 
          padding: 0, 
          overflow: 'hidden', 
          position: 'relative',
          borderRadius: 'var(--radius-md)'
        }}
      >
        {isNoData && (
          <div style={{
            position: 'absolute',
            top: '1rem',
            left: '3.5rem',
            zIndex: 1000,
            backgroundColor: 'rgba(255, 255, 255, 0.96)',
            backdropFilter: 'blur(8px)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            padding: '0.85rem 1.25rem',
            boxShadow: 'var(--shadow-md)',
            maxWidth: '380px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--warning)', fontWeight: 700, fontSize: '0.85rem' }}>
              <AlertCircle size={16} /> Regional Feed Scheduled
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem', lineHeight: 1.45, margin: 0 }}>
              The geographic boundary for <strong>{region.name}</strong> is registered, but high-frequency observation parquets have not been loaded. Switch to <strong>Indore</strong> in the top scope selector to inspect 4 stations, 48 events, and 26 mapped facilities.
            </p>
          </div>
        )}

        {loading ? (
          <div style={{ height: '100%', minHeight: '520px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
            <RefreshCw size={26} className="spin" style={{ marginBottom: '0.75rem', color: 'var(--accent)' }} />
            <p style={{ margin: 0, fontWeight: 500 }}>Loading geospatial layers & coordinates...</p>
          </div>
        ) : (
          <MapContainer center={mapCenter} zoom={mapZoom} scrollWheelZoom={true} style={{ width: '100%', height: '100%', minHeight: '520px' }}>
            <ChangeMapView center={mapCenter} zoom={mapZoom} />
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {/* Render Monitoring Stations */}
            {showStations && mapData?.stations?.map((st, idx) => (
              <Marker key={`st-${idx}`} position={[st.latitude, st.longitude]} icon={stationIcon}>
                <Popup>
                  <div style={{ fontFamily: 'var(--font-body)', padding: '0.25rem' }}>
                    <div className="badge badge-info" style={{ fontSize: '0.65rem', marginBottom: '0.35rem' }}>
                      CAAQMS Node
                    </div>
                    <h4 style={{ color: 'var(--primary)', margin: 0, fontSize: '0.95rem' }}>{st.station_name} Station</h4>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                      {st.city}, {st.state_ut}
                    </div>
                    <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', marginTop: '0.3rem', fontFamily: 'var(--font-mono)' }}>
                      Lat: {st.latitude.toFixed(4)}, Lon: {st.longitude.toFixed(4)}
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}

            {/* Render Pollution Event Epicenters */}
            {showEvents && mapData?.events?.map((evt, idx) => (
              <CircleMarker
                key={`evt-${idx}`}
                center={[evt.sensor.latitude, evt.sensor.longitude]}
                radius={Math.min(22, Math.max(9, evt.peak_pm25 / 10))}
                pathOptions={{
                  color: 'var(--critical)',
                  fillColor: 'var(--critical)',
                  fillOpacity: 0.35,
                  weight: 2,
                }}
              >
                <Popup>
                  <div style={{ fontFamily: 'var(--font-body)', padding: '0.25rem' }}>
                    <span className="badge badge-critical text-mono" style={{ fontSize: '0.65rem', marginBottom: '0.35rem' }}>
                      {evt.event_id}
                    </span>
                    <h4 style={{ color: 'var(--primary)', margin: '0.2rem 0', fontSize: '0.95rem' }}>
                      {evt.station} Spike
                    </h4>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--critical)' }}>
                      Peak PM2.5: {evt.peak_pm25.toFixed(1)} µg/m³
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                      Wind FROM: {evt.wind?.direction_from_deg ? `${evt.wind.direction_from_deg.toFixed(0)}° (${evt.wind.relationship})` : 'N/A'}
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}

            {/* Render Candidate Factories */}
            {showFactories && factoriesList.map((f, idx) => (
              <Marker key={`fac-${idx}`} position={[f.latitude, f.longitude]} icon={factoryIcon}>
                <Popup>
                  <div style={{ fontFamily: 'var(--font-body)', padding: '0.25rem' }}>
                    <span className="badge badge-neutral" style={{ fontSize: '0.65rem', marginBottom: '0.3rem' }}>
                      {f.category}
                    </span>
                    <h4 style={{ color: 'var(--primary)', margin: '0.2rem 0', fontSize: '0.95rem' }}>{f.name}</h4>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>ID: {f.id}</div>
                    <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', marginTop: '0.25rem', fontFamily: 'var(--font-mono)' }}>
                      Coords: {f.latitude.toFixed(4)}, {f.longitude.toFixed(4)}
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        )}
      </div>

    </div>
  );
}
