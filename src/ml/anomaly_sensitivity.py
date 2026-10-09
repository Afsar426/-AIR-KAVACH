"""
AIR KAVACH - Isolation Forest contamination sensitivity experiment.

Run from the project root:
    python src/ml/anomaly_sensitivity.py

This script does not overwrite the existing ML baseline or attribution files.
It trains exploratory per-station Isolation Forest models at contamination
levels 0.01, 0.02 and 0.03, then compares which observations remain flagged.
No verified anomaly labels are available; results are sensitivity diagnostics,
not accuracy measurements.
"""
from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data" / "processed" / "air_quality" / "air_quality.parquet"
SCORES_INPUT = ROOT / "data" / "features" / "ml_anomaly_scores.parquet"
OUT_PARQUET = ROOT / "data" / "features" / "ml_anomaly_sensitivity.parquet"
OUT_CSV = ROOT / "reports" / "generated" / "ml_anomaly_sensitivity.csv"
OUT_JSON = ROOT / "reports" / "generated" / "ml_anomaly_sensitivity_report.json"
CONTAMINATIONS = (0.01, 0.02, 0.03)
RANDOM_STATE = 42
N_ESTIMATORS = 300
MAX_GAP_MINUTES = 15.0

def make_features(frame):
    """Create past-only, gap-aware time-series features for one station."""
    df = frame.sort_values("timestamp").copy()
    delta = df["timestamp"].diff().dt.total_seconds().div(60)
    df["gap_minutes"] = delta
    # Start a new segment whenever the current timestamp is not exactly
    # one 15-minute interval after the previous observation.
    new_segment = delta.ne(15.0)
    if len(new_segment):
        new_segment.iloc[0] = True
    df["segment_id"] = new_segment.cumsum()

    df["past_mean"] = (
        df.groupby("segment_id", sort=False)["value"]
          .transform(lambda s: s.shift(1).rolling(96, min_periods=24).mean())
    )
    df["past_std"] = (
        df.groupby("segment_id", sort=False)["value"]
          .transform(lambda s: s.shift(1).rolling(96, min_periods=24).std())
    )
    df["deviation"] = df["value"] - df["past_mean"]
    hour = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60.0
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    return df

def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Required input not found: {INPUT}")
    raw = pd.read_parquet(INPUT)
    required = {"station", "timestamp", "value"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {sorted(missing)}")

    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True, errors="coerce")
    raw["value"] = pd.to_numeric(raw["value"], errors="coerce")
    raw = raw.dropna(subset=["station", "timestamp", "value"]).copy()
    raw = raw[np.isfinite(raw["value"]) & (raw["value"] >= 0)].copy()
    if raw.duplicated(["station", "timestamp"]).any():
        raise ValueError("Duplicate station/timestamp rows detected; stop for data review.")

    parts = []
    for station, group in raw.groupby("station", sort=True):
        features = make_features(group)
        feature_cols = ["value", "deviation", "past_std", "hour_sin", "hour_cos"]
        eligible = features[feature_cols].replace([np.inf, -np.inf], np.nan).notna().all(axis=1)
        eligible &= features["past_std"] > 0
        fit = features.loc[eligible].copy()
        if len(fit) < 100:
            warnings.warn(f"Skipping {station}: only {len(fit)} eligible rows.")
            continue

        # Use the same feature set for each contamination level.
        X = fit[feature_cols].to_numpy(dtype=float)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        for contamination in CONTAMINATIONS:
            model = IsolationForest(
                n_estimators=N_ESTIMATORS,
                contamination=contamination,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )
            model.fit(X_scaled)
            # Larger score means more anomalous in this output convention.
            score = -model.decision_function(X_scaled)
            pred = model.predict(X_scaled) == -1
            part = fit[["station", "timestamp", "value", "gap_minutes"]].copy()
            part["contamination"] = contamination
            part["anomaly_score"] = score
            part["is_anomaly"] = pred
            parts.append(part)

    if not parts:
        raise RuntimeError("No station models were trained.")
    results = pd.concat(parts, ignore_index=True)

    summary = (
        results.groupby(["contamination", "station"], as_index=False)
        .agg(eligible_rows=("is_anomaly", "size"),
             anomalies=("is_anomaly", "sum"),
             mean_anomalous_value=("value", lambda s: float("nan")))
    )
    # Calculate mean values only for flagged observations.
    means = (
        results[results["is_anomaly"]]
        .groupby(["contamination", "station"])["value"]
        .mean()
        .rename("mean_pm25_among_anomalies")
        .reset_index()
    )
    summary = summary.drop(columns=["mean_anomalous_value"]).merge(
        means, on=["contamination", "station"], how="left"
    )
    summary["flagged_percent"] = (
        100 * summary["anomalies"] / summary["eligible_rows"]
    ).round(3)
    summary["mean_pm25_among_anomalies"] = summary[
        "mean_pm25_among_anomalies"
    ].round(2)

    # Stability: how many observations are flagged at all three settings?
    pivot = results.pivot_table(
        index=["station", "timestamp"], columns="contamination",
        values="is_anomaly", aggfunc="first", fill_value=False
    )
    for c in CONTAMINATIONS:
        if c not in pivot.columns:
            pivot[c] = False
    pivot = pivot.sort_index(axis=1)
    stable_all = pivot[list(CONTAMINATIONS)].all(axis=1)
    any_flag = pivot[list(CONTAMINATIONS)].any(axis=1)
    stability = {
        "observations_scored_at_all_levels": int(len(pivot)),
        "flagged_at_all_three_levels": int(stable_all.sum()),
        "flagged_at_least_one_level": int(any_flag.sum()),
        "stable_share_of_any_flagged_percent": round(
            100 * stable_all.sum() / max(int(any_flag.sum()), 1), 2
        ),
        "pairwise_intersections": {},
    }
    for i, a in enumerate(CONTAMINATIONS):
        for b in CONTAMINATIONS[i + 1:]:
            A = pivot[a].astype(bool)
            B = pivot[b].astype(bool)
            union = int((A | B).sum())
            stability["pairwise_intersections"][f"{a:.2f}_vs_{b:.2f}"] = {
                "flagged_a": int(A.sum()),
                "flagged_b": int(B.sum()),
                "intersection": int((A & B).sum()),
                "union": union,
                "jaccard_percent": round(100 * int((A & B).sum()) / max(union, 1), 2),
            }

    results["timestamp"] = pd.to_datetime(results["timestamp"], utc=True)
    summary.to_csv(OUT_CSV, index=False)
    results.to_parquet(OUT_PARQUET, index=False)
    report = {
        "experiment": "Isolation Forest contamination sensitivity",
        "input": str(INPUT.relative_to(ROOT)),
        "rows_in_input": int(len(raw)),
        "contamination_levels": list(CONTAMINATIONS),
        "n_estimators": N_ESTIMATORS,
        "random_state": RANDOM_STATE,
        "feature_columns": ["value", "deviation", "past_std", "hour_sin", "hour_cos"],
        "gap_handling": "Past-only rolling features reset at any interval other than 15 minutes.",
        "station_summary": summary.to_dict(orient="records"),
        "stability": stability,
        "limitations": [
            "No verified anomaly labels; this is not an accuracy evaluation.",
            "Contamination is a model parameter, not a measured real-world anomaly rate.",
            "Anomalies are observations, not independent pollution events.",
            "Unusual low readings may indicate sensor/data issues and need review."
        ]
    }
    OUT_JSON.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("=" * 76)
    print("AIR KAVACH - ISOLATION FOREST SENSITIVITY")
    print("=" * 76)
    print("Input observations:", len(raw))
    print("\nSTATION SUMMARY")
    print(summary.to_string(index=False))
    print("\nSTABILITY CHECK")
    print(json.dumps(stability, indent=2))
    print("\nSaved:", OUT_PARQUET.relative_to(ROOT))
    print("Saved:", OUT_CSV.relative_to(ROOT))
    print("Saved:", OUT_JSON.relative_to(ROOT))
    print("\nNo existing baseline, event, attribution, or map files were modified.")
    print("No verified labels are available; do not interpret these results as accuracy.")
    print("EXPERIMENT COMPLETE")

if __name__ == "__main__":
    main()
