# AIR KAVACH - Known Scientific Limitations & Operational Boundaries

This document defines the scientific boundaries, physical assumptions, and operational caveats of the AIR KAVACH platform.

---

## 1. Atmospheric & Dispersion Modeling Boundaries

### 1.1 Two-Dimensional Surface Approximation vs. 3D Fluid Dynamics
- **Current Formulation**: AIR KAVACH evaluates horizontal vector alignment using 10-meter surface wind measurements and a circular cosine alignment function $\max(0, \cos(\Delta\theta))$.
- **Atmospheric Reality**: Plumes emitted from industrial stacks rise buoyantly and are transported by winds aloft. The Planetary Boundary Layer (PBL) height, vertical wind shear (directional veering with altitude), and atmospheric stability classes (Pasquill-Gifford A through F) heavily influence vertical mixing.
- **Implication**: During strong nocturnal temperature inversions, plumes from tall stacks may stay aloft and decouple from ground-level monitoring stations, whereas ground-level fugitive emissions may accumulate intensely. AIR KAVACH serves as an initial spatial screening heuristic, not a full 3D Lagrangian trajectory (HYSPLIT) or Eulerian photochemical dispersion model (AERMOD, CMAQ, CAMx).

### 1.2 Topographical & Urban Canopy Channeling
- Surface winds measured at municipal weather stations may experience localized aerodynamic deflection around urban structures, hills, or river valleys. Macro-scale ERA5 wind reanalysis may smooth out these sub-kilometer micro-scale wind vectors.

---

## 2. Industrial Facility Metadata & Emission Dynamics

### 2.1 Absence of Continuous Emission Monitoring (CEMS) Logs
- Candidate facilities in the database are indexed by spatial location, category, and administrative boundaries.
- **Critical Caveat**: Public datasets do not currently expose real-time CEMS stack telemetry. The platform cannot independently verify whether a specific factory was operating, undergoing maintenance, or running at peak capacity during the exact hours of an event.

### 2.2 Stack Height & Plume Buoyancy
- Emission release height significantly alters ground-level concentration profiles:
  - Low fugitive ground sources (e.g., aggregate crushing, diesel generators) peak within $0.5\text{--}2.0\text{ km}$.
  - Tall industrial stacks (e.g., thermal power plants $>100\text{m}$) may not touch the ground until $5\text{--}15\text{ km}$ downwind.
- AIR KAVACH's exponential decay function ($e^{-d / 5.0}$) represents an average composite dispersion across industrial categories.

---

## 3. Spatial Resolution & Sensor Density

### 3.1 Sparsity of Monitoring Stations
- Indore features 4 official CAAQMS stations across a municipal area of over 500 square kilometers.
- Spatially isolated emission spikes occurring outside the direct upwind fetch of these four sensors will not be captured.
- Expanding coverage across other Indian urban centers requires denser micro-sensor or satellite-derived aerosol optical depth (AOD) integration.

---

## 4. Atmospheric Chemistry & Secondary Aerosol Formation

- **Primary vs. Secondary Particulates**: $\text{PM}_{2.5}$ comprises both primary emitted soot/ash and secondary aerosols formed via the chemical conversion of gaseous precursors ($\text{SO}_2 \to \text{sulfates}$, $\text{NO}_x \to \text{nitrates}$, $\text{VOCs} \to \text{secondary organic aerosols}$).
- Secondary particle formation can occur over transport durations of 2 to 24 hours, meaning the original gaseous emission source may be located tens or hundreds of kilometers upwind from where peak particulate concentrations are detected.

---

## 5. Regulatory & Decision-Support Status

- **Screening Prioritization**: AIR KAVACH is engineered as a **decision-support and investigative prioritizer** for environmental inspection officers, researchers, and citizen advocates.
- **Not Legal Proof**: An elevated attribution score ($S \ge 0.70$) indicates **geometric and meteorological plausibility**, establishing grounds for targeted physical stack inspection or targeted mobile sampling. It does not constitute certified legal causation or regulatory citation evidence in isolation.

---

## 6. Multi-Provider & Remote Sensing Limitations

### 6.1 Satellite Thermal Detections (NASA FIRMS)
- MODIS and VIIRS satellite active fire detections are constrained by polar-orbit overpass timing (typically 1–2 passes per sensor per day). Short-duration agricultural burns between satellite overpasses may not be captured.
- Heavy cloud cover or thick smog during monsoon and winter peak episodes can obscure infrared thermal signatures from satellite sensors.

### 6.2 Modeled Air Quality vs. Ground Telemetry (Open-Meteo / Copernicus CAMS)
- Numerical atmospheric models operate on coarse grid cells (typically $0.1^\circ \times 0.1^\circ$ or $\approx 10\text{ km} \times 10\text{ km}$).
- Modeled concentrations represent spatial volume averages and cannot resolve sub-kilometer industrial plume incursions or street canyon trapping. Modeled data is labeled strictly with `data_type: 'modeled'` and must never be substituted for in-situ CAAQMS measurements.

### 6.3 Rate Limits & Network Availability of External APIs
- OpenAQ and data.gov.in public tiers are subject to rate limiting and intermittent server latency. AIR KAVACH implements local Parquet persistence and fallback caching so that external provider downtime never disrupts investigative operations or system uptime.
