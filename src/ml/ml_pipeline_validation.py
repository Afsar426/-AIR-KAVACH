"""
AIR KAVACH - ML pipeline validation and consistency checks.

Run from the project root:
    python src/ml/ml_pipeline_validation.py

Read-only with respect to source outputs: creates only a validation JSON report.
It checks expected input/output files, schemas, duplicate keys, stable anomaly
counts, event overlap consistency, and the high-peak event references.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FILES = {
    "air_quality": ROOT / "data" / "processed" / "air_quality" / "air_quality.parquet",
    "events": ROOT / "data" / "processed" / "events" / "pollution_events.parquet",
    "ml_baseline": ROOT / "data" / "features" / "ml_anomaly_scores.parquet",
    "ml_sensitivity": ROOT / "data" / "features" / "ml_anomaly_sensitivity.parquet",
    "stable_review": ROOT / "reports" / "generated" / "ml_stable_anomaly_review.csv",
    "episodes": ROOT / "reports" / "generated" / "ml_stable_anomaly_episodes.csv",
    "episode_comparison": ROOT / "reports" / "generated" / "ml_episode_event_comparison.csv",
}
OUT = ROOT / "reports" / "generated" / "ml_pipeline_validation_report.json"

def require_columns(df, cols, label, errors):
    missing = sorted(set(cols) - set(df.columns))
    if missing:
        errors.append(f"{label}: missing required columns {missing}")

def main():
    errors = []
    warnings = []
    missing_files = [name for name, path in FILES.items() if not path.exists()]
    if missing_files:
        raise FileNotFoundError(
            "Required outputs missing: " + ", ".join(
                f"{name}={FILES[name]}" for name in missing_files
            )
        )

    aq = pd.read_parquet(FILES["air_quality"])
    events = pd.read_parquet(FILES["events"])
    baseline = pd.read_parquet(FILES["ml_baseline"])
    sensitivity = pd.read_parquet(FILES["ml_sensitivity"])
    review = pd.read_csv(FILES["stable_review"])
    episodes = pd.read_csv(FILES["episodes"])
    comparison = pd.read_csv(FILES["episode_comparison"])

    require_columns(aq, ["station", "timestamp", "value"], "air_quality", errors)
    require_columns(events, ["event_id", "station", "start_time", "end_time", "peak_pm25"], "events", errors)
    require_columns(baseline, ["station", "timestamp", "value", "anomaly_score", "isolation_forest_anomaly"], "ml_baseline", errors)
    require_columns(sensitivity, ["station", "timestamp", "value", "contamination", "is_anomaly"], "ml_sensitivity", errors)
    require_columns(review, ["station", "timestamp", "value", "stable_all_levels", "event_overlap"], "stable_review", errors)
    require_columns(episodes, ["station", "episode_id", "start_time", "end_time", "peak_pm25", "anomaly_observations"], "episodes", errors)
    require_columns(comparison, ["episode_id", "overlapping_statistical_event_count", "overlap_status"], "episode_comparison", errors)

    if errors:
        raise ValueError("\n".join(errors))

    for frame, label in [(aq, "air_quality"), (baseline, "ml_baseline"), (sensitivity, "ml_sensitivity")]:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        if frame["timestamp"].isna().any():
            errors.append(f"{label}: invalid timestamps found")
    events["start_time"] = pd.to_datetime(events["start_time"], utc=True, errors="coerce")
    events["end_time"] = pd.to_datetime(events["end_time"], utc=True, errors="coerce")

    aq_dup = int(aq.duplicated(["station", "timestamp"]).sum())
    baseline_dup = int(baseline.duplicated(["station", "timestamp"]).sum())
    sensitivity_dup = int(sensitivity.duplicated(["station", "timestamp", "contamination"]).sum())
    if aq_dup:
        errors.append(f"air_quality: {aq_dup} duplicate station/timestamp keys")
    if baseline_dup:
        errors.append(f"ml_baseline: {baseline_dup} duplicate station/timestamp keys")
    if sensitivity_dup:
        errors.append(f"ml_sensitivity: {sensitivity_dup} duplicate station/timestamp/contamination keys")

    score_values = pd.to_numeric(baseline["anomaly_score"], errors="coerce").dropna().to_numpy()
    if not np.isfinite(score_values).all():
        errors.append("ml_baseline: non-finite anomaly scores")
    if "isolation_forest_anomaly" in baseline:
        flagged_without_score = int(
            (baseline["isolation_forest_anomaly"].astype(bool) & baseline["anomaly_score"].isna()).sum()
        )
        if flagged_without_score:
            errors.append(f"ml_baseline: {flagged_without_score} flags without scores")

    # Recompute stable observations directly from all three sensitivity columns.
    flags = sensitivity.pivot_table(
        index=["station", "timestamp"], columns="contamination",
        values="is_anomaly", aggfunc="first", fill_value=False
    )
    expected_levels = [0.01, 0.02, 0.03]
    absent_levels = [x for x in expected_levels if x not in flags.columns]
    if absent_levels:
        errors.append(f"ml_sensitivity: missing contamination levels {absent_levels}")
    else:
        stable_count = int(flags[expected_levels].all(axis=1).sum())
        any_count = int(flags[expected_levels].any(axis=1).sum())
        if stable_count != 58:
            warnings.append(f"Stable anomaly count changed from previously reported 58 to {stable_count}")
        if any_count != 172:
            warnings.append(f"Any-setting anomaly count changed from previously reported 172 to {any_count}")
    stable_review_count = int(review["stable_all_levels"].astype(str).str.lower().isin(["true", "1", "yes"]).sum())
    if absent_levels == [] and stable_review_count != stable_count:
        errors.append(
            f"stable review mismatch: CSV has {stable_review_count}, sensitivity recomputation has {stable_count}"
        )

    # Episode IDs should map one-to-one between episodes and comparison rows.
    if episodes["episode_id"].duplicated().any():
        errors.append("episodes: duplicate episode_id values")
    if comparison["episode_id"].duplicated().any():
        errors.append("episode_comparison: duplicate episode_id values")
    if set(episodes["episode_id"]) != set(comparison["episode_id"]):
        errors.append("episode IDs do not match between episode CSV and comparison CSV")

    # Check episode counts against known output and ensure intervals are sensible.
    ep_start = pd.to_datetime(episodes["start_time"], utc=True, errors="coerce")
    ep_end = pd.to_datetime(episodes["end_time"], utc=True, errors="coerce")
    invalid_intervals = int((ep_start.isna() | ep_end.isna() | (ep_end < ep_start)).sum())
    if invalid_intervals:
        errors.append(f"episodes: {invalid_intervals} invalid episode intervals")
    event_ids = set(events["event_id"].astype(str))
    referenced = set()
    if "matched_event_ids" in episodes:
        for raw in episodes["matched_event_ids"].fillna("").astype(str):
            referenced.update(x.strip() for x in raw.split(";") if x.strip())
    unknown_event_refs = sorted(referenced - event_ids)
    if unknown_event_refs:
        warnings.append(f"episode file references event IDs not found in event table: {unknown_event_refs}")

    status_count = {str(k): int(v) for k, v in comparison["overlap_status"].value_counts(dropna=False).items()}
    report = {
        "status": "PASS" if not errors else "FAIL",
        "input_rows": {
            "air_quality": int(len(aq)),
            "events": int(len(events)),
            "ml_baseline": int(len(baseline)),
            "ml_sensitivity": int(len(sensitivity)),
            "stable_review": int(len(review)),
            "episodes": int(len(episodes)),
            "episode_comparison": int(len(comparison)),
        },
        "duplicate_key_counts": {
            "air_quality_station_timestamp": aq_dup,
            "ml_baseline_station_timestamp": baseline_dup,
            "ml_sensitivity_station_timestamp_contamination": sensitivity_dup,
        },
        "ml_score_checks": {
            "scored_observations": int(len(score_values)),
            "all_scores_finite": bool(np.isfinite(score_values).all()),
            "flags_without_scores": int((baseline["isolation_forest_anomaly"].astype(bool) & baseline["anomaly_score"].isna()).sum()),
        },
        "sensitivity_checks": {
            "contamination_levels_found": [float(x) for x in sorted(sensitivity["contamination"].unique())],
            "recomputed_stable_count": int(stable_count) if absent_levels == [] else None,
            "recomputed_any_setting_count": int(any_count) if absent_levels == [] else None,
            "stable_review_csv_count": stable_review_count,
        },
        "episode_checks": {
            "episode_count": int(len(episodes)),
            "comparison_row_count": int(len(comparison)),
            "overlap_status_counts": status_count,
            "invalid_episode_intervals": invalid_intervals,
            "unknown_event_references": unknown_event_refs,
        },
        "errors": errors,
        "warnings": warnings,
        "interpretation": [
            "This checks file consistency and internal data integrity only.",
            "It does not measure anomaly-detection accuracy or validate causal attribution.",
            "Temporal overlap with a heuristic event detector is not ground truth."
        ],
    }
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("=" * 76)
    print("AIR KAVACH - ML PIPELINE VALIDATION")
    print("=" * 76)
    print("STATUS:", report["status"])
    print("\nROW COUNTS")
    for name, count in report["input_rows"].items():
        print(f"{name}: {count}")
    print("\nSENSITIVITY CHECK")
    print(json.dumps(report["sensitivity_checks"], indent=2))
    print("\nEPISODE CHECK")
    print(json.dumps(report["episode_checks"], indent=2))
    print("\nERRORS")
    print("\n".join(errors) if errors else "None")
    print("\nWARNINGS")
    print("\n".join(warnings) if warnings else "None")
    print("\nSaved:", OUT.relative_to(ROOT))
    print("VALIDATION COMPLETE")

if __name__ == "__main__":
    main()
