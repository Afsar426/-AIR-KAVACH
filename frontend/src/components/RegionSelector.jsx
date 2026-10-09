import React from 'react';
import { Globe, AlertCircle, CheckCircle2 } from 'lucide-react';

export const REGIONS_OPTIONS = [
  {
    id: "national",
    name: "Pan-India National Scope",
    city: "",
    state_ut: "",
    status: "partial_coverage",
    statusLabel: "Pan-India Multi-Region",
    description: "Multi-region environmental monitoring architecture across India."
  },
  {
    id: "in-mp-indore",
    name: "Indore, Madhya Pradesh",
    city: "Indore",
    state_ut: "Madhya Pradesh",
    status: "recent_data_available",
    statusLabel: "Active Validation Region (Full Data)",
    description: "4 stations, 15-minute PM2.5, wind vectors, 26 industrial facilities."
  },
  {
    id: "in-dl-delhi",
    name: "Delhi NCR",
    city: "Delhi",
    state_ut: "Delhi",
    status: "no_usable_data",
    statusLabel: "Registered (Ingestion Feed Pending)",
    description: "Boundary & Okhla/Mayapuri industrial hubs registered; feed scheduled."
  },
  {
    id: "in-mh-mumbai",
    name: "Mumbai, Maharashtra",
    city: "Mumbai",
    state_ut: "Maharashtra",
    status: "no_usable_data",
    statusLabel: "Registered (Ingestion Feed Pending)",
    description: "Thane-Belapur corridor registered; awaiting local feed."
  },
  {
    id: "in-gj-ahmedabad",
    name: "Ahmedabad, Gujarat",
    city: "Ahmedabad",
    state_ut: "Gujarat",
    status: "no_usable_data",
    statusLabel: "Registered (Ingestion Feed Pending)",
    description: "Vatva/Naroda industrial clusters defined."
  },
  {
    id: "in-ka-bengaluru",
    name: "Bengaluru, Karnataka",
    city: "Bengaluru",
    state_ut: "Karnataka",
    status: "no_usable_data",
    statusLabel: "Registered (Ingestion Feed Pending)",
    description: "Peenya industrial complex defined."
  },
  {
    id: "in-up-kanpur",
    name: "Kanpur, Uttar Pradesh",
    city: "Kanpur",
    state_ut: "Uttar Pradesh",
    status: "no_usable_data",
    statusLabel: "Registered (Ingestion Feed Pending)",
    description: "Panki industrial corridor defined."
  }
];

export default function RegionSelector({ selectedRegion, onSelectRegion }) {
  const current = REGIONS_OPTIONS.find(r => r.id === selectedRegion) || REGIONS_OPTIONS[1];

  return (
    <div 
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.65rem',
        backgroundColor: 'var(--bg-surface)',
        padding: '0.35rem 0.75rem',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border)',
        boxShadow: 'var(--shadow-xs)'
      }}
      aria-label="Geographical Scope Selector"
    >
      <Globe size={15} color="var(--accent)" style={{ flexShrink: 0 }} />
      
      <div style={{ display: 'flex', flexDirection: 'column', minWidth: '150px' }}>
        <label 
          htmlFor="geo-region-select"
          style={{ 
            fontSize: '0.625rem', 
            textTransform: 'uppercase', 
            color: 'var(--text-secondary)', 
            fontWeight: 700, 
            letterSpacing: '0.04em',
            lineHeight: 1
          }}
        >
          Geographic Scope
        </label>
        <select
          id="geo-region-select"
          value={selectedRegion}
          onChange={(e) => onSelectRegion(e.target.value)}
          style={{
            border: 'none',
            outline: 'none',
            backgroundColor: 'transparent',
            fontFamily: 'var(--font-heading)',
            fontSize: '0.825rem',
            fontWeight: 600,
            color: 'var(--primary)',
            cursor: 'pointer',
            padding: 0,
            marginTop: '1px'
          }}
        >
          {REGIONS_OPTIONS.map(r => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </div>

      <div style={{ display: 'flex', alignItems: 'center' }}>
        {current.status === 'recent_data_available' ? (
          <span 
            className="badge badge-success" 
            style={{ fontSize: '0.65rem', padding: '0.15rem 0.45rem', whiteSpace: 'nowrap' }}
            title="Real 15-minute observations loaded"
          >
            <CheckCircle2 size={10} style={{ marginRight: '2px' }} /> Active Data
          </span>
        ) : (
          <span 
            className="badge badge-warning" 
            style={{ fontSize: '0.65rem', padding: '0.15rem 0.45rem', whiteSpace: 'nowrap' }}
            title="Registered region; local feeds scheduled"
          >
            <AlertCircle size={10} style={{ marginRight: '2px' }} /> Feeds Pending
          </span>
        )}
      </div>
    </div>
  );
}
