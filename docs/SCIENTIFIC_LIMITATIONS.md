# AIR KAVACH - Scientific Limitations & Disclaimers

AIR KAVACH is an investigative decision-support platform designed to narrow candidate industrial facilities for environmental monitoring. It does **NOT** replace scientific atmospheric dispersion modeling and does **NOT** establish legal guilt or regulatory non-compliance.

## Key Scientific Limitations

1. **Heuristic Screening Engine:**
   - Attribution scores combine geometric bearing alignment and exponential distance decay. This is a geometric heuristic, not a numerical fluid dynamics or Gaussian plume dispersion model (such as AERMOD, HYSPLIT, CAMx, or CMAQ).
2. **Missing Meteorological Variables:**
   - Calculations do not incorporate atmospheric stability class, mixing height layer, vertical wind shear, boundary layer turbulence, temperature inversion layers, or humidity.
3. **Facility Emission Data:**
   - Facility candidate rankings are based on spatial location and category metadata. Facility stack height, exit gas temperature, exit velocity, and actual emissions flow rates are not included.
4. **No Probability Calibration:**
   - `relative_likelihood` is a normalized heuristic score share among candidate facilities in the spatial buffer. It is **not** a calibrated posterior probability of causation.
5. **No Ground-Truth Labels:**
   - The platform does not claim validated supervised accuracy, precision, or recall due to the lack of ground-truth stack emissions logs.
