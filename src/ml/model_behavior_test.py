"""
AIR KAVACH - Model behavior test / explainability walkthrough.

Run from project root:
    python src/ml/model_behavior_test.py

This script reads the existing ML, air-quality, and event outputs. It does not
train a new model and does not change event, attribution, confidence, or map data.
It tests whether representative examples behave consistently with the already
saved model outputs. This is NOT an accuracy test because no verified labels
are available.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
AQ_PATH = ROOT / "data" / "processed" / "air_quality" / "air_quality.parquet"
BASELINE_PATH = ROOT / "data" / "features" / "ml_anomaly_scores.parquet"
SENS_PATH = ROOT / "data" / "features" / "ml_anomaly_sensitivity.parquet"
EVENT_PATH = ROOT / "data" / "processed" / "events" / "pollution_events.parquet"
OUT_CSV = ROOT / "reports" / "generated" / "model_behavior_test_cases.csv"
OUT_JSON = ROOT / "reports" / "generated" / "model_behavior_test_report.json"

def parse_bool(series):
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin(["true", "1", "yes"])

def main():
    for p in [AQ_PATH, BASELINE_PATH, SENS_PATH, EVENT_PATH]:
        if not p.exists():
            raise FileNotFoundError(f"Required file missing: {p}")

    aq = pd.read_parquet(AQ_PATH)
    baseline = pd.read_parquet(BASELINE_PATH)
    sensitivity = pd.read_parquet(SENS_PATH)
    events = pd.read_parquet(EVENT_PATH)

    for frame in [aq, baseline, sensitivity]:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    events["start_time"] = pd.to_datetime(events["start_time"], utc=True, errors="coerce")
    events["end_time"] = pd.to_datetime(events["end_time"], utc=True, errors="coerce")

    if "isolation_forest_anomaly" not in baseline:
        raise ValueError("Baseline output missing isolation_forest_anomaly")
    if "statistical_flag" not in baseline:
        raise ValueError("Baseline output missing statistical_flag")

    baseline["isolation_forest_anomaly"] = parse_bool(baseline["isolation_forest_anomaly"])
    baseline["statistical_flag"] = parse_bool(baseline["statistical_flag"])
    sensitivity["is_anomaly"] = parse_bool(sensitivity["is_anomaly"])

    # Representative cases observed in the user's current experiment outputs.
    cases = [
        ("Airport", "2026-09-06T14:30:00Z", "Very high reading overlapping EVT-0005"),
        ("Maguda", "2026-09-30T23:45:00Z", "Elevated reading flagged by ML; inspect event overlap"),
        ("Residency", "2026-09-23T04:00:00Z", "Very low reading flagged by ML; potential data-quality review"),
        ("Regional Park", "2026-09-24T12:00:00Z", "Very low reading flagged by ML; potential data-quality review"),
    ]
    rows = []
    used = set()

    def append_case(station, timestamp, case_type):
        key = (station, pd.Timestamp(timestamp))
        if key in used:
            return
        used.add(key)
        aq_hit = aq[(aq["station"] == station) & (aq["timestamp"] == key[1])]
        b_hit = baseline[(baseline["station"] == station) & (baseline["timestamp"] == key[1])]
        if aq_hit.empty:
            rows.append({
                "station": station, "timestamp": key[1], "case_type": case_type,
                "value": np.nan, "baseline_ml_flag_2pct": None,
                "statistical_flag": None, "anomaly_score_2pct": np.nan,
                "flag_1pct": None, "flag_2pct": None, "flag_3pct": None,
                "event_ids": "", "result_note": "Timestamp not present in input data",
            })
            return
        value = float(aq_hit.iloc[0]["value"])
        b = b_hit.iloc[0] if not b_hit.empty else None
        s = sensitivity[(sensitivity["station"] == station) & (sensitivity["timestamp"] == key[1])]
        flags = {}
        for level in [0.01, 0.02, 0.03]:
            sub = s[np.isclose(pd.to_numeric(s["contamination"]), level)]
            flags[level] = bool(sub.iloc[0]["is_anomaly"]) if not sub.empty else None

        matched = events[
            (events["station"] == station)
            & (events["start_time"] <= key[1])
            & (events["end_time"] >= key[1])
        ]
        if value >= 100:
            reading_interpretation = "Very high reading; investigate as a pollution candidate"
        elif value < 5:
            reading_interpretation = "Very low reading; inspect sensor/data quality before calling pollution"
        elif value >= 35:
            reading_interpretation = "Elevated reading; review temporal and weather context"
        else:
            reading_interpretation = "Not high by this simple review threshold; model flag is context-dependent"

        rows.append({
            "station": station,
            "timestamp": key[1],
            "case_type": case_type,
            "value": value,
            "baseline_ml_flag_2pct": bool(b["isolation_forest_anomaly"]) if b is not None else None,
            "statistical_flag": bool(b["statistical_flag"]) if b is not None else None,
            "anomaly_score_2pct": float(b["anomaly_score"]) if b is not None and pd.notna(b["anomaly_score"]) else np.nan,
            "deviation_from_past_mean": float(b["deviation"]) if b is not None and "deviation" in b and pd.notna(b["deviation"]) else np.nan,
            "past_mean": float(b["past_mean"]) if b is not None and "past_mean" in b and pd.notna(b["past_mean"]) else np.nan,
            "past_std": float(b["past_std"]) if b is not None and "past_std" in b and pd.notna(b["past_std"]) else np.nan,
            "gap_minutes": float(b["gap_minutes"]) if b is not None and "gap_minutes" in b and pd.notna(b["gap_minutes"]) else np.nan,
            "flag_1pct": flags[0.01],
            "flag_2pct": flags[0.02],
            "flag_3pct": flags[0.03],
            "event_ids": ";".join(matched["event_id"].astype(str).tolist()),
            "event_overlap": not matched.empty,
            "reading_interpretation": reading_interpretation,
            "result_note": "Saved model output lookup; not ground-truth validation",
        })

    for station, ts, label in cases:
        append_case(station, ts, label)

    # Add one deterministic normal-control example per station: a scored row
    # not flagged at 2%, with the lowest anomaly score (least anomalous under
    # the script's score convention). This is only a model-behavior control.
    for station, group in baseline.groupby("station", sort=True):
        candidates = group[
            (~group["isolation_forest_anomaly"])
            & group["anomaly_score"].notna()
        ].sort_values("anomaly_score", ascending=True)
        if not candidates.empty:
            row = candidates.iloc[0]
            append_case(station, row["timestamp"], "Unflagged control: low anomaly score")

    result = pd.DataFrame(rows).sort_values(["station", "timestamp"])
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True)
    result.to_csv(OUT_CSV, index=False)

    valid = result[result["value"].notna()]
    flagged = valid[valid["baseline_ml_flag_2pct"] == True]
    report = {
        "purpose": "Representative behavior test of existing saved model outputs.",
        "input_rows": {
            "air_quality": int(len(aq)),
            "baseline_rows": int(len(baseline)),
            "sensitivity_rows": int(len(sensitivity)),
            "existing_events": int(len(events)),
        },
        "test_case_count": int(len(result)),
        "cases_found_in_data": int(result["value"].notna().sum()),
        "cases_missing_from_data": int(result["value"].isna().sum()),
        "representative_ml_flagged_cases": int(len(flagged)),
        "flagged_case_event_overlap_count": int(flagged["event_overlap"].fillna(False).sum()) if "event_overlap" in flagged else 0,
        "flagged_case_examples": flagged[[
            c for c in ["station", "timestamp", "value", "anomaly_score_2pct",
                        "statistical_flag", "flag_1pct", "flag_2pct", "flag_3pct",
                        "event_ids", "reading_interpretation"] if c in flagged.columns
        ]].to_dict(orient="records"),
        "interpretation": [
            "This verifies lookup and behavior of saved outputs on representative examples; it does not retrain the model.",
            "No verified labels exist, so accuracy, precision, recall, and false-positive rate cannot be measured.",
            "Isolation Forest detects unusual feature combinations, not pollution causation.",
            "A low PM2.5 reading may be an anomaly but is not a pollution spike.",
            "The source-attribution score is a separate heuristic layer, not a trained supervised ML model."
        ],
        "next_evaluation_needed": [
            "Expert-reviewed labels for a sample of anomaly observations/events.",
            "Sensor maintenance/quality metadata where available.",
            "A held-out time period for testing if enough data becomes available."
        ]
    }
    OUT_JSON.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("=" * 78)
    print("AIR KAVACH - MODEL BEHAVIOR TEST")
    print("=" * 78)
    print("This reads existing outputs; no model retraining or project-output changes.")
    print(f"Air-quality rows: {len(aq)} | Baseline rows: {len(baseline)} | Sensitivity rows: {len(sensitivity)}")
    print(f"Existing statistical events: {len(events)}")
    print(f"Test cases: {len(result)} | Found: {int(result['value'].notna().sum())}")
    print("\nCASE RESULTS")
    cols = [c for c in [
        "station", "timestamp", "case_type", "value", "anomaly_score_2pct",
        "baseline_ml_flag_2pct", "statistical_flag", "flag_1pct", "flag_2pct",
        "flag_3pct", "event_ids", "reading_interpretation"
    ] if c in result.columns]
    print(result[cols].to_string(index=False))
    print("\nSUMMARY")
    print("ML-flagged representative cases:", len(flagged))
    print("Flagged cases overlapping existing events:", report["flagged_case_event_overlap_count"])
    print("\nSaved:", OUT_CSV.relative_to(ROOT))
    print("Saved:", OUT_JSON.relative_to(ROOT))
    print("\nNo model was retrained. No event, attribution, confidence, or map files were modified.")
    print("This is a behavior check, not an accuracy test.")
    print("MODEL BEHAVIOR TEST COMPLETE")

if __name__ == "__main__":
    main()
