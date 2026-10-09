# AIR KAVACH (एयर कवच) — Frontend UI/UX Redesign Review

**Document Version:** 1.0.0  
**Date:** October 2026  
**Scope:** Frontend UI/UX Redesign Only — Feature Set Final & Frozen  
**Platform:** Environmental Intelligence & Industrial Pollution Source Attribution Platform  

---

## 1. Executive Summary

AIR KAVACH's React/Vite frontend has been completely redesigned into a clean, disciplined, and professional Environmental Intelligence platform. The design emphasizes scientific credibility, geospatial clarity, reproducible evidentiary reporting, and operational honesty.

### Strict Scope Adherence
* **Feature Set Frozen:** Zero new features, backend APIs, external providers, or machine learning model alterations were introduced.
* **No Generic Aesthetics:** Replaced generic neon AI dashboard tropes with a restrained, high-contrast, editorial palette designed specifically for environmental engineering and regulatory oversight.
* **Preserved Functionality:** All 12 views, API client calls, interactive map layers, event filters, CSV intake workflows, and agentic trace dialogs remain completely functional.

---

## 2. Usability Audit & Identified Deficiencies

During the comprehensive audit of the initial frontend, several usability and information architecture flaws were documented:

1. **Navigation Bar Clutter:** The previous header displayed 12 flat navigation buttons stretching horizontally across the screen, breaking and wrapping unpredictably on laptop displays and unusable on mobile viewports.
2. **Fragmented Investigation Flow:** The Investigation Workspace displayed disorganized panels rather than guiding an environmental investigator through the logical evidentiary chain (A through H).
3. **Residual CSS Variable Drift:** Multiple pages relied on deprecated or inconsistent CSS variables (`var(--surface)`, `var(--text-main)`, `var(--bg)`), resulting in inconsistent backgrounds, borders, and margins.
4. **Ambiguous Data Recency:** Station telemetry timestamps and dataset periods lacked upfront context regarding real observation dates versus real-time mock data.
5. **Absence of Responsive Drawer Navigation:** Mobile and tablet screens had no accessible navigation drawer or collapsible hamburger menu.
6. **Raw Unformatted JSON Output:** Reports and assistant responses initially dumped dense JSON blocks directly into view cards without structured executive summaries or candidate ranking tables.

---

## 3. Approved Brand Palette & Design Tokens

The approved AIR KAVACH palette was rigorously implemented as standard CSS custom properties in `frontend/src/index.css`:

| Token | Hex / Value | Semantic Role |
| :--- | :--- | :--- |
| `--bg-main` | `#F7F8F6` | Primary background canvas |
| `--bg-surface` | `#FFFFFF` | Elevated card surfaces and panels |
| `--primary` | `#1D3557` | Primary brand deep navy, major headings, key metrics |
| `--primary-hover` | `#29486F` | Interactive hover state for primary elements |
| `--primary-subtle` | `#E8EEF5` | Active nav dropdown pill background |
| `--text-primary` | `#24313D` | High-contrast body text and tabular data |
| `--text-secondary` | `#64748B` | Labels, metadata, captions, secondary notes |
| `--border` | `#E1E6E5` | Structural dividers, card borders |
| `--border-subtle` | `#ECEFEF` | Table row dividers |
| `--accent` | `#3C8D91` | Deep spruce accent for icons, active tabs, subtle links |
| `--accent-hover` | `#2D6F72` | Hover state for accent buttons |
| `--accent-light` | `#EBF5F5` | Information callout background, selected row tint |
| `--critical` | `#DC4545` | Confirmed spikes, invalid rows, high risk |
| `--critical-light` | `#FDE8E8` | Critical badge and alert backgrounds |
| `--warning` | `#D99526` | Calm wind diffusion warnings, missing CEMS notices |
| `--warning-light` | `#FEF3E2` | Warning badge and alert backgrounds |
| `--success` | `#27845B` | Valid rows, connected feeds, low risk |
| `--success-light` | `#E6F4EA` | Success badge and alert backgrounds |

### Typography & Spacing Scale
* **Body Font:** Inter, system-ui, `-apple-system`, `sans-serif` (clean, highly legible at small telemetry sizes).
* **Monospace Font:** JetBrains Mono, `SFMono-Regular`, `Consolas`, monospace (used for Event IDs, timestamps, coordinates, sensor IDs).
* **Radius Tokens:** `--radius-sm` (4px), `--radius-md` (8px), `--radius-lg` (12px), `--radius-full` (9999px).
* **Elevation Tokens:** Subtle, crisp shadows (`--shadow-xs`, `--shadow-sm`, `--shadow-md`, `--shadow-lg`) avoiding heavy blurs.

---

## 4. Reorganized Navigation Architecture

Navigation was restructured from a flat 12-button bar into **five logical, domain-driven dropdown groups** plus a slide-out mobile drawer:

```
[AIR KAVACH Logo] 
├── OVERVIEW
│   ├── Platform Intro (Landing Page)
│   └── Regional Dashboard (Main Overview)
├── MONITOR
│   ├── Air Quality Telemetry (Observations & Trends)
│   ├── Pollution Events (Confirmed Anomalies)
│   └── Geospatial Map (Interactive GIS Layer)
├── INVESTIGATE
│   ├── Source Attribution (Geometric Screening)
│   ├── Investigation Workspace (Sections A–H)
│   └── AI Assistant (Agentic Natural Language Q&A)
├── DATA
│   ├── Data Sources & Intake (Adapters & CSV Import)
│   └── ML Models (Isolation Forest Lifecycle)
└── REPORTS & SYSTEM
    ├── Official Reports (Dossiers & Audit History)
    └── Settings & Status (Backend Health & Coverage)
[Region Selector: Globe + Dropdown + Status Badge]
```

### Responsive Mobile Drawer
* Added a dedicated hamburger button (`<Menu size={20} />`) displayed below `1120px` viewport width.
* Accessible slide-out drawer overlay (`.mobile-drawer-overlay`) with backdrop blur.
* Includes grouped navigation sections, one-click page routing, and automatic closure on selection.
* Outside-click event listeners on desktop navigation dropdowns to ensure clean dismissal.

---

## 5. Page-by-Page Redesign Documentation

### 5.1 Main Dashboard (`MainDashboard.jsx`)
* **Honest Data Freshness Banner:** Directly renders `summary.data_period` start and end dates with clear tags indicating archival observation periods.
* **Hero Key Performance Indicators:**
  - Confirmed Pollution Events ($Z \ge 2.0\sigma$)
  - In-Situ CAAQMS Observations (total records ingested)
  - Active Stations in Selected Region
  - Industrial Candidate Facilities in Proximity
* **Station Telemetry Table:** Clean tabular layout with station coordinates, peak PM2.5 readings, and instant "Inspect Spikes" buttons that pre-filter the Events view.
* **Scientific Caveat Card:** Restrained footer callout citing data provenance and absence of real-time CEMS telemetry.

### 5.2 Air Quality Monitoring (`MonitoringPage.jsx`)
* **Filter Bar:** Station selection dropdown, observation count counter, and refresh button.
* **Pagination Controls:** Clean 50-row paginated data table with "Previous" and "Next" buttons and page counter.
* **Telemetry Table:** Monospace ISO timestamps, formatted numeric values with unit badges, parameter pill tags, and station labels.
* **Empty State Handling:** Graceful, informative alert callouts for non-Indore regions where feeds are pending.

### 5.3 Pollution Events (`PollutionEventsPage.jsx`)
* **Live Search Filter:** Instant client-side search by Event ID or Station name with clear button.
* **Event Telemetry Table:** Highlights peak PM2.5 readings, calculated statistical $Z$-scores, and 5-state lifecycle badges (`candidate`, `investigating`, `confirmed`, `disputed`, `resolved`).
* **One-Click Workspace Hand-off:** "Investigate" button navigates straight to the Investigation Workspace with the target Event ID pre-loaded.

### 5.4 Investigation Workspace (`EventWorkspacePage.jsx`)
Structured strictly into the required **Sections A through H**:
* **Section A — Event Overview:** Event ID badge, monitoring station, timing, duration, peak PM2.5, $Z$-score, and current lifecycle badge with dropdown updater.
* **Section B — Observed Environmental Facts:** In-situ CAAQMS readings, 15-minute interval observations, rolling baseline value, and clear notes confirming the shifted baseline ($shift=1$) avoids current-spike contamination.
* **Section C — Weather & Meteorological Context:** Wind FROM direction in degrees, cardinal direction pill, wind speed (m/s), calm wind diffusion flag ($< 0.5$ m/s), and weather coverage percentage.
* **Section D — Candidate Industrial Facilities:** Formatted screening ranking table including facility name, industrial sector, radial distance (km), wind alignment percentage, screening score, and normalized score share.
* **Section E — Screening Scores & Methodology Limitations:** Mathematical formula transparency breakdown:
  $$\text{Score} = 0.30 \times \text{DistanceDecay} + 0.70 \times \text{WindAlignment}$$
  Explains why scores represent geometric candidate likelihood rather than legal causal proof.
* **Section F — Missing Evidence & Uncertainty Audit:**
  - *Mandatory CEMS Warning Banner:* Prominently notes that industrial facility stacks do not have connected real-time Continuous Emission Monitoring Systems.
  - *Missing Telemetry Audit:* Itemizes unobserved factors (stack plume rise, local building downwash, mobile vehicular corridors).
* **Section G — Automated Investigation Synthesis & Execution Trace:** Executive summary narrative accompanied by a collapsible terminal-styled tool execution trace.
* **Section H — Official Investigation Dossier Export:** Compiles, generates, and persists official JSON investigation dossiers to disk via `postGenerateReport`.

### 5.5 Geospatial Map (`InteractiveMapPage.jsx`)
* **Floating Layer Controls:** High-contrast toggle chips for Monitoring Stations, Pollution Spikes, and Industrial Candidate Facilities.
* **Custom Marker Design:** Leaflet DivIcons with crisp SVG glyphs and distinct color tokens (Navy for Stations, Red for Spikes, Slate for Industrial Plants).
* **Responsive Map Container:** Maintains clean dimensions across desktop and mobile screens.

### 5.6 Source Attribution (`SourceAttributionPage.jsx`)
* **Quick-Select Event Pills:** One-click shortcuts for representative benchmark events (`EVT-0001`, `EVT-0007`, `EVT-0017`, `EVT-0029`, `EVT-0047`, `EVT-0048`).
* **Formula Transparency Cards:** Explicitly displays the exponential distance decay equation:
  $$\text{DistanceDecay}(d) = \exp(-d / d_0)$$
  and cosine wind alignment angle calculation.
* **Rankings Table & Direct Navigation:** Candidate table with "Inspect in Workspace" button.

### 5.7 AI Assistant (`AIAssistantPage.jsx`)
* **Suggested Query Chips:** One-click prompts for common investigation questions.
* **Disaggregated Evidence Cards:**
  - *Observed Environmental Facts* (in-situ station readings)
  - *Modeled & Statistical Estimates* (candidate source rankings)
  - *Missing Evidence & Limitations* (unmonitored factors)
* **Collapsible Execution Trace:** Dark terminal block displaying agent tool invocations, parameters, and return payloads.

### 5.8 Data Sources & Ingestion (`DataSourcesPage.jsx`)
* **Connected Providers Matrix:** 6 independent provider adapter status cards (OpenAQ v3, CPCB, Open-Meteo Weather, Open-Meteo Modeled AQ, NASA FIRMS, CEMS) with latency, data age, and manual sync triggers.
* **Manual Data Intake & CSV Dropzone:** Clean drag-and-drop zone with file preview, column mapping selector, test-mode isolation checkbox, and schema validation counts.
* **Chronological Ingestion Audit Ledger:** Filterable audit table tracking all ingestion jobs, environment tags (PROD vs TEST), accepted records, and rejection counts.
* **Pan-India Coverage Status Matrix:** Comprehensive table detailing data availability across all registered Indian states and cities.

### 5.9 Machine Learning Model Lifecycle (`ModelMonitoringPage.jsx`)
* **Artifact Recency & Ensemble Counters:** Displays model artifact state (`isolation_forest_v1.joblib`), number of isolation trees (300), contamination rate (0.02), and training sample counts.
* **Methodology Banner:** Explains unsupervised anomaly scoring on rolling features.
* **Feature Schema Badges:** Visual tags for all input feature dimensions fed into the isolation trees.
* **Retraining Trigger:** Action button to retrain model artifacts on demand.

### 5.10 Reports & Audit History (`ReportsPage.jsx`)
* **Compilation Bar:** Event ID input form with compile and persist actions.
* **Dossier Viewer:** Structured executive view showing executive summary, observed facts grid, candidate rankings table, and legal safeguard notice.
* **Collapsible Raw JSON:** Full verifiable evidence payload available inside an expandable `<details>` section.
* **Historical Reports Table:** Chronological table of saved reports with one-click "View Dossier" actions.

### 5.11 System Settings & Health (`SettingsPage.jsx`)
* **System Service Status:** Clean health checklist for FastAPI backend, Parquet storage datasets, Isolation Forest model, and OpenAQ feeds.
* **Pan-India Readiness & Governance:** Pan-India status indicators and explicit scientific data governance notes (raw data preservation, rolling baseline shift=1).

---

## 6. Accessibility & Responsiveness Audit

* **Accessible Focus Indicators:** Standardized `:focus-visible` styling (`outline: 2px solid var(--accent); outline-offset: 2px;`) across all interactive buttons, inputs, links, and selects.
* **Semantic HTML:** Replaced untyped click targets with native `<button>`, `<label htmlFor="...">`, `<input>`, `<select>`, and `<table>` elements.
* **Text Contrast Compliance:** High-contrast text `#24313D` on `#FFFFFF` and `#F7F8F6` canvases exceeds WCAG AA standards (contrast ratio $> 11:1$). Secondary text `#64748B` exceeds $> 4.5:1$.
* **Responsive Breakpoints:**
  - `1440px`: Max-width container centering.
  - `1120px`: Desktop dropdown navigation collapses to mobile toggle; 4-column metric grids collapse to 2 columns.
  - `900px`: 3-column and 2-column grids collapse to single columns.
  - `640px`: Padding scales down to 1rem for phone viewports.

---

## 7. Scientific Guardrails & CEMS Integrity

All core scientific and legal safeguards remain strictly intact:
1. **No Fabricated Causal Accuracy:** Candidate rankings are clearly marked as geometric screening alignment scores, not causal proof.
2. **CEMS Absence Prominence:** Mandatory warning callouts explicitly inform users that industrial stacks lack live CEMS sensors.
3. **Shifted Baseline Integrity:** Detection displays explicitly confirm rolling baseline calculations utilize $shift=1$ to prevent current spike contamination.
4. **Honest Data Recency:** Observation dates reflect actual ingested timestamps without claiming simulated real-time status.

---

## 8. Build & Automated Test Verification

### Frontend Production Build
```bash
> frontend@0.0.0 build
> vite build

vite v8.3.4 building client environment for production...
transforming...
✓ 1956 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.45 kB │ gzip:   0.29 kB
dist/assets/index-B-z36ggL.css   26.72 kB │ gzip:   9.04 kB
dist/assets/index-klp8nXMI.js   540.93 kB │ gzip: 149.07 kB
✓ built in 206ms
```
* **Status:** Passed with exit code 0.
* **Result:** Zero bundle syntax errors, zero missing imports.

### Backend Automated Test Suite
```bash
.\.venv\Scripts\python.exe -m pytest
======================= 61 passed, 1 warning in 31.95s ========================
```
* **Status:** Passed with exit code 0.
* **Result:** All 61 automated tests across unit, integration, scientific validation, and Pan-India coverage pass without regressions.

---

## 9. Conclusion

The AIR KAVACH frontend is now a cohesive, high-performance, and professionally styled Environmental Intelligence platform. All functional contracts, API clients, and scientific safeguards have been strictly maintained, providing an intuitive and defensible user experience for environmental monitoring across India.
