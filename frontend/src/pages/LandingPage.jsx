import React, { useEffect, useState } from 'react';
import { 
  Shield, 
  Activity, 
  Compass, 
  AlertTriangle, 
  ArrowRight, 
  Database, 
  Search, 
  Target, 
  FileText, 
  Leaf, 
  Users, 
  BarChart3, 
  MapPin, 
  CheckCircle2, 
  Layers, 
  Info,
  Clock,
  Sparkles
} from 'lucide-react';
import { fetchSummary } from '../api';

export default function LandingPage({ onLaunch }) {
  const [summaryData, setSummaryData] = useState(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);

  useEffect(() => {
    fetchSummary()
      .then((res) => {
        if (res) {
          setSummaryData(res);
        }
      })
      .catch((err) => console.warn("Summary fetch error on landing page:", err))
      .finally(() => setLoadingMetrics(false));
  }, []);

  const totalStations = summaryData?.total_stations || 4;
  const totalFacilities = summaryData?.source_candidates_evaluated || 26;
  const totalEvents = summaryData?.total_events || 48;
  const totalObs = summaryData?.total_observations || 8211;

  const scrollToSection = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div style={{ backgroundColor: 'var(--bg-main)', minHeight: '100vh', color: 'var(--text-primary)' }}>
      
      {/* 1. TOP HEADER / HERO SUB-NAV */}
      <header style={{
        maxWidth: '1440px',
        margin: '0 auto',
        padding: '1.25rem 3rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid var(--border)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '38px',
            height: '38px',
            borderRadius: '10px',
            backgroundColor: 'var(--primary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#FFFFFF'
          }}>
            <Shield size={22} />
          </div>
          <div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--primary)', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
              AIR KAVACH
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              Industrial Pollution Intelligence
            </div>
          </div>
        </div>

        <nav style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
          <button onClick={() => scrollToSection('approach')} className="nav-btn" style={{ fontSize: '0.9rem' }}>
            Capabilities
          </button>
          <button onClick={() => scrollToSection('methodology')} className="nav-btn" style={{ fontSize: '0.9rem' }}>
            Methodology
          </button>
          <button onClick={() => scrollToSection('transparency')} className="nav-btn" style={{ fontSize: '0.9rem' }}>
            Data & Coverage
          </button>
          <button onClick={onLaunch} className="btn-primary" style={{ padding: '0.55rem 1.25rem', fontSize: '0.85rem' }}>
            Launch Application <ArrowRight size={14} style={{ marginLeft: '4px' }} />
          </button>
        </nav>
      </header>

      {/* 2. HERO SECTION */}
      <section style={{ maxWidth: '1440px', margin: '0 auto', padding: '3rem 3rem 1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '48% 52%', gap: '3rem', alignItems: 'center' }}>
          
          {/* LEFT COLUMN: Editorial Copy */}
          <div>
            <div style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              letterSpacing: '0.12em',
              color: 'var(--accent)',
              textTransform: 'uppercase',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent)' }}></span>
              ENVIRONMENTAL INTELLIGENCE FOR INDIA
            </div>

            <h1 className="font-serif" style={{
              fontSize: '3.8rem',
              lineHeight: 1.08,
              fontWeight: 600,
              color: 'var(--primary)',
              marginBottom: '1.25rem',
              letterSpacing: '-0.02em'
            }}>
              Cleaner Air Today<br />
              for <span style={{ fontStyle: 'italic', color: 'var(--accent)', fontWeight: 500 }}>Healthier Tomorrow.</span>
            </h1>

            <p style={{
              fontSize: '1.05rem',
              color: 'var(--text-secondary)',
              lineHeight: 1.6,
              maxWidth: '540px',
              marginBottom: '2.25rem'
            }}>
              Investigate pollution events with air-quality observations, meteorological evidence, geospatial analysis, and transparent industrial source screening across India.
            </p>

            <div style={{ display: 'flex', gap: '1rem', marginBottom: '3rem', alignItems: 'center' }}>
              <button 
                onClick={onLaunch}
                className="btn-primary"
                style={{ padding: '0.9rem 1.75rem', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
              >
                Launch Investigation <ArrowRight size={18} />
              </button>

              <button 
                onClick={() => scrollToSection('methodology')}
                className="btn-secondary"
                style={{ padding: '0.9rem 1.5rem', fontSize: '0.95rem' }}
              >
                Explore the Methodology
              </button>
            </div>

            {/* Operational Ground-Truth Metrics */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr auto 1fr auto 1fr',
              gap: '1rem',
              alignItems: 'center',
              paddingTop: '1.5rem',
              borderTop: '1px solid var(--border)'
            }}>
              <div>
                <div className="font-serif" style={{ fontSize: '2.25rem', fontWeight: 700, color: 'var(--primary)', lineHeight: 1.1 }}>
                  {totalStations}
                </div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                  Monitoring Stations
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Active Nodes (Indore Region)
                </div>
              </div>

              <div style={{ width: '1px', height: '40px', backgroundColor: 'var(--border)' }}></div>

              <div>
                <div className="font-serif" style={{ fontSize: '2.25rem', fontWeight: 700, color: 'var(--primary)', lineHeight: 1.1 }}>
                  {totalFacilities}
                </div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                  Industrial Facilities
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Mapped Candidate Sources
                </div>
              </div>

              <div style={{ width: '1px', height: '40px', backgroundColor: 'var(--border)' }}></div>

              <div>
                <div className="font-serif" style={{ fontSize: '2.25rem', fontWeight: 700, color: 'var(--primary)', lineHeight: 1.1 }}>
                  {totalEvents}
                </div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                  Pollution Events
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Confirmed Anomalies
                </div>
              </div>
            </div>

          </div>

          {/* RIGHT COLUMN: Cinematic Environmental Intelligence Visual Canvas */}
          <div style={{
            position: 'relative',
            height: '540px',
            borderRadius: '24px',
            overflow: 'hidden',
            backgroundColor: '#1D3557',
            backgroundImage: "url('/hero_city_bg.jpg')",
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            boxShadow: 'var(--shadow-lg)',
            border: '1px solid var(--border)'
          }}>
            {/* Ambient Gradient Overlay */}
            <div style={{
              position: 'absolute',
              inset: 0,
              background: 'linear-gradient(to right, rgba(247,248,246,0.2) 0%, transparent 25%, transparent 75%, rgba(29,53,87,0.45) 100%)',
              pointerEvents: 'none'
            }}></div>

            {/* Restrained Wind Vector Overlay SVG */}
            <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', opacity: 0.8 }}>
              <path d="M 280,60 Q 380,40 480,70 T 580,50" fill="none" stroke="#3C8D91" strokeWidth="2" strokeDasharray="6 4" />
              <path d="M 240,110 Q 360,90 460,120 T 560,100" fill="none" stroke="#FFFFFF" strokeWidth="1.5" strokeOpacity="0.85" strokeDasharray="8 4" />
              <path d="M 300,160 Q 400,140 500,170 T 600,150" fill="none" stroke="#3C8D91" strokeWidth="1.5" strokeDasharray="5 5" />
            </svg>

            {/* OVERLAY 1: Observed Air Quality Card */}
            <div style={{
              position: 'absolute',
              top: '24px',
              left: '24px',
              backgroundColor: '#FFFFFF',
              borderRadius: '14px',
              padding: '0.85rem 1.25rem',
              boxShadow: '0 8px 24px rgba(0,0,0,0.14)',
              zIndex: 10,
              minWidth: '175px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-primary)', fontSize: '0.75rem', fontWeight: 700 }}>
                <Activity size={14} color="var(--primary)" /> Observed PM2.5 Feed
              </div>
              <div style={{ fontSize: '1.85rem', fontWeight: 700, color: 'var(--primary)', lineHeight: 1.2, marginTop: '0.2rem' }}>
                72.4 <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-secondary)' }}>µg/m³</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.75rem', color: 'var(--critical)', fontWeight: 600, marginTop: '0.25rem' }}>
                ↑ Elevated (z = 2.45 σ)
              </div>
            </div>

            {/* OVERLAY 2: Meteorological Wind Direction */}
            <div style={{
              position: 'absolute',
              top: '24px',
              right: '24px',
              backgroundColor: 'rgba(29, 53, 87, 0.75)',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              borderRadius: '14px',
              padding: '0.85rem 1.25rem',
              color: '#FFFFFF',
              zIndex: 10,
              minWidth: '160px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', fontWeight: 600, opacity: 0.9 }}>
                <Compass size={14} color="var(--accent)" /> Meteorological Wind
              </div>
              <div style={{ fontSize: '1.85rem', fontWeight: 700, marginTop: '0.2rem', lineHeight: 1.2 }}>
                248°
              </div>
              <div style={{ fontSize: '0.75rem', opacity: 0.85 }}>
                SW Vector (Originating)
              </div>
            </div>

            {/* OVERLAY 3: Detected Event Reticle */}
            <div style={{
              position: 'absolute',
              top: '45%',
              right: '32%',
              transform: 'translate(50%, -50%)',
              zIndex: 8,
              display: 'flex',
              alignItems: 'center',
              gap: '1rem'
            }}>
              <div style={{ position: 'relative', width: '38px', height: '38px' }}>
                <div style={{
                  position: 'absolute',
                  inset: 0,
                  borderRadius: '50%',
                  backgroundColor: 'rgba(220, 69, 69, 0.4)',
                  animation: 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite'
                }}></div>
                <div style={{
                  position: 'absolute',
                  inset: '7px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--critical)',
                  border: '3px solid #FFFFFF',
                  boxShadow: '0 0 14px rgba(220, 69, 69, 0.8)'
                }}></div>
              </div>

              <div style={{
                backgroundColor: 'rgba(20, 25, 35, 0.92)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(220, 69, 69, 0.6)',
                borderRadius: '12px',
                padding: '0.75rem 1rem',
                color: '#FFFFFF',
                boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
                maxWidth: '220px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#FF7B7B', fontSize: '0.75rem', fontWeight: 700 }}>
                  <AlertTriangle size={14} /> Anomaly Detected
                </div>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, marginTop: '0.25rem' }}>Residency Station</div>
                <div style={{ fontSize: '0.75rem', opacity: 0.8, marginTop: '0.1rem' }}>September 2026 Feed</div>
              </div>
            </div>

            {/* OVERLAY 4: Candidate Facilities */}
            <div style={{
              position: 'absolute',
              bottom: '24px',
              left: '24px',
              backgroundColor: '#FFFFFF',
              borderRadius: '12px',
              padding: '0.75rem 1.1rem',
              boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
              zIndex: 10,
              display: 'flex',
              alignItems: 'center',
              gap: '0.85rem'
            }}>
              <div style={{
                width: '38px',
                height: '38px',
                borderRadius: '8px',
                backgroundColor: 'var(--bg-main)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--primary)'
              }}>
                <BarChart3 size={20} />
              </div>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Screening Pipeline</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary)', lineHeight: 1.1 }}>
                  3 <span style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-secondary)' }}>Top Candidates / Event</span>
                </div>
              </div>
            </div>

            {/* OVERLAY 5: Pan-India Coverage Pill */}
            <div style={{
              position: 'absolute',
              bottom: '24px',
              right: '24px',
              backgroundColor: 'rgba(29, 53, 87, 0.75)',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              borderRadius: '12px',
              padding: '0.75rem 1.1rem',
              color: '#FFFFFF',
              zIndex: 10,
              fontSize: '0.75rem'
            }}>
              <div style={{ fontWeight: 700, marginBottom: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <CheckCircle2 size={13} color="var(--success)" /> Pan-India Architecture
              </div>
              <div style={{ opacity: 0.85 }}>
                Indore validation dataset active; other states mapped.
              </div>
            </div>

          </div>

        </div>
      </section>

      {/* 3. ORGANIC CURVED WAVE SECTION DIVIDER */}
      <div style={{ width: '100%', overflow: 'hidden', lineHeight: 0, marginTop: '2rem' }}>
        <svg viewBox="0 0 1440 80" fill="none" style={{ width: '100%', height: '60px' }}>
          <path d="M0,30 C320,70 640,10 960,50 C1280,90 1440,30 1440,30 L1440,80 L0,80 Z" fill="#FFFFFF" />
        </svg>
      </div>

      {/* 4. APPROACH SECTION: FROM OBSERVATION TO EVIDENCE */}
      <section id="approach" style={{ backgroundColor: '#FFFFFF', padding: '3.5rem 3rem 4.5rem' }}>
        <div style={{ maxWidth: '1440px', margin: '0 auto' }}>
          
          <div style={{ display: 'grid', gridTemplateColumns: '32% 68%', gap: '3.5rem', alignItems: 'flex-start' }}>
            
            <div>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: '0.75rem',
                fontWeight: 700,
                color: 'var(--accent)',
                letterSpacing: '0.08em',
                marginBottom: '0.75rem',
                textTransform: 'uppercase'
              }}>
                OUR APPROACH <span style={{ flex: 1, height: '1px', backgroundColor: 'var(--border)' }}></span>
              </div>

              <h2 className="font-serif" style={{ fontSize: '2.6rem', color: 'var(--primary)', lineHeight: 1.15, marginBottom: '1.25rem' }}>
                From Observation<br />to Evidence
              </h2>

              <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '2rem' }}>
                AIR KAVACH does not rely on subjective guesswork or unvalidated assumptions. It connects empirical air observations with atmospheric physics and geospatial intelligence.
              </p>

              <button 
                onClick={onLaunch}
                className="btn-secondary"
                style={{ padding: '0.75rem 1.4rem', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
              >
                Launch Investigation <ArrowRight size={14} />
              </button>
            </div>

            {/* 4 Core Pillars */}
            <div className="grid-cols-4" style={{ gap: '1.25rem' }}>
              
              <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>01 / DETECT</div>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--accent-light)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--accent)',
                    marginBottom: '1rem'
                  }}>
                    <Search size={20} />
                  </div>
                  <h3 style={{ fontSize: '1.1rem', color: 'var(--primary)', marginBottom: '0.5rem' }}>Detect Anomalies</h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    Identify statistically unusual air-quality spikes from monitoring observations using rolling baselines without data leakage.
                  </p>
                </div>
              </div>

              <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>02 / INVESTIGATE</div>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--accent-light)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--accent)',
                    marginBottom: '1rem'
                  }}>
                    <Activity size={20} />
                  </div>
                  <h3 style={{ fontSize: '1.1rem', color: 'var(--primary)', marginBottom: '0.5rem' }}>Contextualize</h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    Connect pollution events with relevant time windows, sensor coordinates, and meteorological wind vectors.
                  </p>
                </div>
              </div>

              <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>03 / ATTRIBUTE</div>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--accent-light)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--accent)',
                    marginBottom: '1rem'
                  }}>
                    <Target size={20} />
                  </div>
                  <h3 style={{ fontSize: '1.1rem', color: 'var(--primary)', marginBottom: '0.5rem' }}>Screen Candidates</h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    Rank geographically plausible industrial facility candidates using distance decay and meteorological wind alignment.
                  </p>
                </div>
              </div>

              <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>04 / EXPLAIN</div>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--accent-light)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--accent)',
                    marginBottom: '1rem'
                  }}>
                    <FileText size={20} />
                  </div>
                  <h3 style={{ fontSize: '1.1rem', color: 'var(--primary)', marginBottom: '0.5rem' }}>Explain & Audit</h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    Deliver explainable dossiers with supporting evidence, uncertainty metrics, and explicit scientific limitations.
                  </p>
                </div>
              </div>

            </div>

          </div>

        </div>
      </section>

      {/* 5. IMPACT STRIP: DARK NAVY WITH HIGH CONTRAST */}
      <section style={{
        backgroundColor: '#1D3557',
        color: '#FFFFFF',
        padding: '3rem 3rem',
        backgroundImage: 'radial-gradient(circle at 90% 10%, #3C8D91 0%, #1D3557 55%)'
      }}>
        <div style={{
          maxWidth: '1440px',
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(5, 1fr)',
          gap: '2rem',
          alignItems: 'flex-start'
        }}>
          <div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.35rem', color: '#FFFFFF' }}>
              Faster Investigation
            </div>
            <p style={{ fontSize: '0.8rem', opacity: 0.85, lineHeight: 1.5 }}>
              Rapid triage of acute spikes from hours to seconds with automated tool orchestration.
            </p>
          </div>

          <div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.35rem', color: '#FFFFFF' }}>
              Transparent Evidence
            </div>
            <p style={{ fontSize: '0.8rem', opacity: 0.85, lineHeight: 1.5 }}>
              Every candidate score is grounded in verifiable angular math and distance formulas.
            </p>
          </div>

          <div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.35rem', color: '#FFFFFF' }}>
              Regional Visibility
            </div>
            <p style={{ fontSize: '0.8rem', opacity: 0.85, lineHeight: 1.5 }}>
              Pan-India geographical filters with truthful reporting of real-world data coverage.
            </p>
          </div>

          <div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.35rem', color: '#FFFFFF' }}>
              Reproducible Analysis
            </div>
            <p style={{ fontSize: '0.8rem', opacity: 0.85, lineHeight: 1.5 }}>
              Traceable execution logs and serialized investigation reports persisted on disk.
            </p>
          </div>

          <div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.35rem', color: '#FFFFFF' }}>
              Informed Decisions
            </div>
            <p style={{ fontSize: '0.8rem', opacity: 0.85, lineHeight: 1.5 }}>
              Actionable screening intelligence to prioritize site inspections and regulatory actions.
            </p>
          </div>
        </div>
      </section>

      {/* 6. METHODOLOGY SECTION */}
      <section id="methodology" style={{ padding: '4.5rem 3rem', maxWidth: '1440px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', maxWidth: '750px', margin: '0 auto 3.5rem' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            SCIENTIFIC WORKFLOW
          </div>
          <h2 className="font-serif" style={{ fontSize: '2.5rem', color: 'var(--primary)', marginBottom: '1rem' }}>
            The 6-Stage Investigation Pipeline
          </h2>
          <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            AIR KAVACH implements a deterministic and machine-learning backed analytical pipeline designed for auditability and regulatory transparency.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
          
          <div className="card" style={{ padding: '1.75rem' }}>
            <span className="badge badge-info" style={{ marginBottom: '0.75rem' }}>Stage 1: Observation Ingestion</span>
            <h4 style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>High-Frequency Air Feeds</h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Ingests 15-minute particulate matter observations (PM2.5, PM10) via OpenAQ API v3 and reference catalogs.
            </p>
          </div>

          <div className="card" style={{ padding: '1.75rem' }}>
            <span className="badge badge-info" style={{ marginBottom: '0.75rem' }}>Stage 2: Normalization & Audit</span>
            <h4 style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Data Quality Validation</h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Enforces unit consistency (µg/m³), rejects negative readings, and segments records across temporal gaps (&gt;30 min).
            </p>
          </div>

          <div className="card" style={{ padding: '1.75rem' }}>
            <span className="badge badge-info" style={{ marginBottom: '0.75rem' }}>Stage 3: Event Detection</span>
            <h4 style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Leakage-Free Baselines</h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Computes rolling past-only baselines (96 readings with shift(1)) and station-specific Isolation Forest anomaly scores.
            </p>
          </div>

          <div className="card" style={{ padding: '1.75rem' }}>
            <span className="badge badge-info" style={{ marginBottom: '0.75rem' }}>Stage 4: Meteorology Alignment</span>
            <h4 style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Wind Vector Analysis</h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Aligns meteorological wind direction (FROM convention) and wind speed during the specific event episode window.
            </p>
          </div>

          <div className="card" style={{ padding: '1.75rem' }}>
            <span className="badge badge-info" style={{ marginBottom: '0.75rem' }}>Stage 5: Source Screening</span>
            <h4 style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Distance & Wind Scoring</h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Ranks industrial facilities using exponential distance decay (30% weight) and circular wind vector alignment (70% weight).
            </p>
          </div>

          <div className="card" style={{ padding: '1.75rem' }}>
            <span className="badge badge-info" style={{ marginBottom: '0.75rem' }}>Stage 6: Investigation Dossier</span>
            <h4 style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Evidence-Backed Reporting</h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Aggregates evidence chains, uncertainty metrics, tool execution traces, and exports persistent inspection dossiers.
            </p>
          </div>

        </div>
      </section>

      {/* 7. DATA TRANSPARENCY & SCIENTIFIC CAVEATS SECTION */}
      <section id="transparency" style={{ backgroundColor: '#FFFFFF', padding: '4rem 3rem', borderTop: '1px solid var(--border)' }}>
        <div style={{ maxWidth: '1440px', margin: '0 auto' }}>
          
          <div style={{ display: 'grid', gridTemplateColumns: '40% 60%', gap: '3.5rem', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--warning)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                TRUTHFUL DATA GOVERNANCE
              </div>
              <h2 className="font-serif" style={{ fontSize: '2.4rem', color: 'var(--primary)', marginBottom: '1rem' }}>
                Scientific Integrity & Known Limitations
              </h2>
              <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                AIR KAVACH operates under strict scientific honesty standards. We distinguish empirical observations from heuristic screening and do not claim uncalibrated certainty.
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              
              <div style={{ padding: '1.25rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-md)', borderLeft: '4px solid var(--accent)' }}>
                <h4 style={{ fontSize: '1rem', color: 'var(--primary)', marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Info size={16} color="var(--accent)" /> Candidate Ranking is NOT Proof of Causation
                </h4>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  A candidate ranking score indicates spatial and wind consistency. It does NOT prove legal liability or confirm that a facility emitted pollutants. Ground inspections and dispersion modelling remain essential.
                </p>
              </div>

              <div style={{ padding: '1.25rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-md)', borderLeft: '4px solid var(--warning)' }}>
                <h4 style={{ fontSize: '1rem', color: 'var(--primary)', marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <AlertTriangle size={16} color="var(--warning)" /> Visible Regional Data Coverage
                </h4>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  While our architecture is Pan-India ready across states, our active real-world high-frequency dataset currently covers the Indore validation region. Other regions report honest "Feeds Pending" states without fabricating data.
                </p>
              </div>

              <div style={{ padding: '1.25rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-md)', borderLeft: '4px solid var(--primary)' }}>
                <h4 style={{ fontSize: '1rem', color: 'var(--primary)', marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Compass size={16} color="var(--primary)" /> Meteorological Modeling Scope
                </h4>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  AIR KAVACH utilizes ground-level meteorological wind directions (FROM convention). It is a rapid screening tool and does not replace complex 3D hydrodynamic models (e.g. AERMOD, HYSPLIT, CAMx).
                </p>
              </div>

            </div>
          </div>

        </div>
      </section>

      {/* 8. FINAL CTA BANNER */}
      <section style={{
        maxWidth: '1440px',
        margin: '0 auto',
        padding: '3.5rem 3rem',
        textAlign: 'center'
      }}>
        <div style={{
          backgroundColor: 'var(--bg-surface)',
          padding: '3.5rem 2rem',
          borderRadius: '24px',
          border: '1px solid var(--border)',
          boxShadow: 'var(--shadow-md)',
          maxWidth: '900px',
          margin: '0 auto'
        }}>
          <h2 className="font-serif" style={{ fontSize: '2.5rem', color: 'var(--primary)', marginBottom: '1rem' }}>
            Ready to Investigate Environmental Events?
          </h2>
          <p style={{ fontSize: '1rem', color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto 2rem', lineHeight: 1.6 }}>
            Access the operational workspace to explore monitoring stations, review detected pollution events, inspect candidate attribution rankings, and run agentic investigations.
          </p>
          <button 
            onClick={onLaunch}
            className="btn-primary"
            style={{ padding: '0.95rem 2.25rem', fontSize: '1.05rem', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
          >
            Launch Investigation Workspace <ArrowRight size={18} />
          </button>
        </div>
      </section>

      {/* 9. FOOTER */}
      <footer style={{
        backgroundColor: '#FFFFFF',
        borderTop: '1px solid var(--border)',
        padding: '2.5rem 3rem',
        color: 'var(--text-secondary)',
        fontSize: '0.85rem'
      }}>
        <div style={{
          maxWidth: '1440px',
          margin: '0 auto',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1.5rem'
        }}>
          <div>
            <strong style={{ color: 'var(--primary)' }}>AIR KAVACH</strong> — Agentic Industrial Pollution Source Attribution & Environmental Intelligence Platform
            <div style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
              Pan-India First Architecture | Approved Brand Palette (#F7F8F6 / #1D3557 / #3C8D91)
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1.5rem' }}>
            <button onClick={() => scrollToSection('methodology')} className="nav-btn" style={{ fontSize: '0.8rem' }}>
              Methodology
            </button>
            <button onClick={() => scrollToSection('transparency')} className="nav-btn" style={{ fontSize: '0.8rem' }}>
              Data & Limitations
            </button>
            <button onClick={onLaunch} className="nav-btn" style={{ fontSize: '0.8rem' }}>
              Dashboard
            </button>
          </div>
        </div>
      </footer>

    </div>
  );
}
