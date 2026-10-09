"""
AIR KAVACH exploratory Isolation Forest baseline.
Run from the AIR-KAVACH project root:
    python src/ml/anomaly_baseline.py

This creates new output files only and does not overwrite existing event,
attribution, confidence, or map outputs. Scores are exploratory, not accuracy
or source-attribution probabilities.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

ROOT = Path(".")
INPUT_FILE = ROOT / "data/processed/air_quality/air_quality.parquet"
OUTPUT_FILE = ROOT / "data/features/ml_anomaly_scores.parquet"
REPORT_DIR = ROOT / "reports/generated"
WINDOW = 96
MIN_PERIODS = 24
MAX_GAP_MINUTES = 15
CONTAMINATION = 0.02
RANDOM_STATE = 42


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing {INPUT_FILE}")
    df = pd.read_parquet(INPUT_FILE)
    required = {"station", "timestamp", "value", "parameter"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    df = df[df["parameter"].astype(str).str.lower().eq("pm25")].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["station", "timestamp", "value"])
    df = df.sort_values(["station", "timestamp"]).reset_index(drop=True)

    if df.duplicated(["station", "timestamp"]).any():
        raise ValueError("Duplicate station/timestamp rows found.")
    if (df["value"] < 0).any() or not np.isfinite(df["value"]).all():
        raise ValueError("Negative or non-finite PM2.5 values found.")

    # Split each station into continuous 15-minute segments. Features only use
    # earlier readings from the same segment, so no future leakage or gap bridging.
    df["gap_minutes"] = df.groupby("station")["timestamp"].diff().dt.total_seconds() / 60
    starts_segment = df["gap_minutes"].isna() | (df["gap_minutes"] > MAX_GAP_MINUTES)
    df["segment_id"] = starts_segment.groupby(df["station"]).cumsum()
    keys = ["station", "segment_id"]

    values = df.groupby(keys, sort=False)["value"]
    df["past_mean"] = values.transform(
        lambda s: s.shift(1).rolling(WINDOW, min_periods=MIN_PERIODS).mean()
    )
    df["past_std"] = values.transform(
        lambda s: s.shift(1).rolling(WINDOW, min_periods=MIN_PERIODS).std()
    )
    df["deviation"] = df["value"] - df["past_mean"]
    df["past_z_score"] = df["deviation"] / df["past_std"].replace(0, np.nan)

    hour = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)

    features = ["value", "deviation", "past_std", "hour_sin", "hour_cos"]
    usable = df[features].replace([np.inf, -np.inf], np.nan).notna().all(axis=1)
    scored = df.copy()
    scored["anomaly_score"] = np.nan
    scored["isolation_forest_anomaly"] = False
    station_results = []

    for station in scored.loc[usable, "station"].unique():
        idx = scored.index[usable & scored["station"].eq(station)]
        X = scored.loc[idx, features].astype(float)
        if len(X) < 50:
            station_results.append({
                "station": str(station), "eligible_rows": len(X),
                "status": "skipped_fewer_than_50_rows", "anomalies": 0
            })
            continue

        model = IsolationForest(
            n_estimators=300,
            contamination=CONTAMINATION,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
        model.fit(X)
        scores = -model.decision_function(X)  # Higher = more anomalous
        flags = model.predict(X) == -1
        scored.loc[idx, "anomaly_score"] = scores
        scored.loc[idx, "isolation_forest_anomaly"] = flags
        station_results.append({
            "station": str(station),
            "eligible_rows": int(len(X)),
            "status": "trained",
            "anomalies": int(flags.sum()),
            "flagged_percent": round(float(flags.mean() * 100), 3),
        })

    # Reproduce the existing current-inclusive statistical detector for comparison.
    scored["current_mean"] = scored.groupby("station", sort=False)["value"].transform(
        lambda s: s.rolling(WINDOW, min_periods=MIN_PERIODS).mean()
    )
    scored["current_std"] = scored.groupby("station", sort=False)["value"].transform(
        lambda s: s.rolling(WINDOW, min_periods=MIN_PERIODS).std()
    )
    scored["current_z_score"] = (
        (scored["value"] - scored["current_mean"])
        / scored["current_std"].replace(0, np.nan)
    )
    scored["statistical_flag"] = (
        (scored["current_z_score"] >= 2.0)
        & (scored["value"] > scored["current_mean"])
    )

    valid = scored["anomaly_score"].notna() & scored["current_z_score"].notna()
    stat = scored.loc[valid, "statistical_flag"].to_numpy(dtype=bool)
    ml = scored.loc[valid, "isolation_forest_anomaly"].to_numpy(dtype=bool)
    both = int(np.sum(stat & ml))
    stat_only = int(np.sum(stat & ~ml))
    ml_only = int(np.sum(~stat & ml))
    neither = int(np.sum(~stat & ~ml))
    n = int(valid.sum())
    agreement = float((both + neither) / n) if n else None

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_cols = [
        "station", "timestamp", "value", "unit", "gap_minutes", "segment_id",
        "past_mean", "past_std", "deviation", "past_z_score", "hour_sin",
        "hour_cos", "current_z_score", "statistical_flag", "anomaly_score",
        "isolation_forest_anomaly",
    ]
    scored[output_cols].to_parquet(OUTPUT_FILE, index=False)

    top_file = REPORT_DIR / "ml_anomaly_top_candidates.csv"
    scored[scored["anomaly_score"].notna()].sort_values(
        "anomaly_score", ascending=False
    ).groupby("station", group_keys=False).head(10)[
        ["station", "timestamp", "value", "anomaly_score",
         "statistical_flag", "isolation_forest_anomaly"]
    ].to_csv(top_file, index=False)

    report = {
        "experiment": "exploratory_station_specific_isolation_forest",
        "input_rows": int(len(scored)),
        "eligible_rows_scored": int(scored["anomaly_score"].notna().sum()),
        "contamination_parameter": CONTAMINATION,
        "random_state": RANDOM_STATE,
        "stations": station_results,
        "comparison": {
            "rows_with_both_scores": n,
            "flagged_by_both": both,
            "statistical_only": stat_only,
            "isolation_forest_only": ml_only,
            "neither_flagged": neither,
            "agreement_fraction": agreement,
            "note": "Agreement is not accuracy. No verified anomaly labels are available.",
        },
        "outputs": [str(OUTPUT_FILE), str(top_file)],
    }
    report_file = REPORT_DIR / "ml_anomaly_baseline_report.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=" * 68)
    print("AIR KAVACH - EXPLORATORY ISOLATION FOREST BASELINE")
    print("=" * 68)
    print("Input observations:", len(scored))
    print("Rows scored:", int(scored["anomaly_score"].notna().sum()))
    print("Contamination parameter:", CONTAMINATION)
    print("\nSTATION RESULTS")
    print(pd.DataFrame(station_results).to_string(index=False))
    print("\nCOMPARISON ON ROWS WITH BOTH SCORES")
    print("Rows:", n)
    print("Flagged by both:", both)
    print("Statistical detector only:", stat_only)
    print("Isolation Forest only:", ml_only)
    print("Neither flagged:", neither)
    print("Agreement fraction:", round(agreement, 4) if agreement is not None else "N/A")
    print("\nAgreement is not accuracy; there are no verified anomaly labels.")
    print("\nSaved:", OUTPUT_FILE)
    print("Saved:", top_file)
    print("Saved:", report_file)
    print("Existing event/attribution/map files were not modified.")
    print("EXPERIMENT COMPLETE")


if __name__ == "__main__":
    main()