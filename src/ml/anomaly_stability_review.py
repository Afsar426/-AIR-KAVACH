"""
AIR KAVACH - Review stable Isolation Forest anomalies against detected events.

Run from the project root:
    python src/ml/anomaly_stability_review.py

Reads existing sensitivity and event outputs only. It does not modify model,
event, attribution, or map outputs. It produces review CSV/JSON files only.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SENSITIVITY = ROOT / "data" / "features" / "ml_anomaly_sensitivity.parquet"
EVENTS = ROOT / "data" / "processed" / "events" / "pollution_events.parquet"
OUT_CSV = ROOT / "reports" / "generated" / "ml_stable_anomaly_review.csv"
OUT_JSON = ROOT / "reports" / "generated" / "ml_stable_anomaly_review.json"

LEVELS = (0.01, 0.02, 0.03)

def main():
    if not SENSITIVITY.exists():
        raise FileNotFoundError(f"Missing sensitivity output: {SENSITIVITY}")
    if not EVENTS.exists():
        raise FileNotFoundError(f"Missing event output: {EVENTS}")

    scored = pd.read_parquet(SENSITIVITY)
    events = pd.read_parquet(EVENTS)

    required_scores = {"station", "timestamp", "value", "contamination", "is_anomaly", "anomaly_score"}
    required_events = {"station", "start_time", "end_time", "event_id"}
    if required_scores - set(scored.columns):
        raise ValueError(f"Sensitivity file missing columns: {sorted(required_scores - set(scored.columns))}")
    if required_events - set(events.columns):
        raise ValueError(f"Event file missing columns: {sorted(required_events - set(events.columns))}")

    scored["timestamp"] = pd.to_datetime(scored["timestamp"], utc=True, errors="coerce")
    events["start_time"] = pd.to_datetime(events["start_time"], utc=True, errors="coerce")
    events["end_time"] = pd.to_datetime(events["end_time"], utc=True, errors="coerce")
    scored = scored.dropna(subset=["station", "timestamp", "value", "contamination"])
    events = events.dropna(subset=["station", "start_time", "end_time", "event_id"])

    # A stable observation is flagged at all tested contamination settings.
    flags = scored.pivot_table(
        index=["station", "timestamp"],
        columns="contamination",
        values="is_anomaly",
        aggfunc="first",
        fill_value=False,
    )
    for level in LEVELS:
        if level not in flags.columns:
            flags[level] = False
    flags = flags.sort_index(axis=1)
    stable_index = flags[list(LEVELS)].all(axis=1)
    any_index = flags[list(LEVELS)].any(axis=1)

    base = (
        scored[scored["contamination"] == 0.02]
        .drop_duplicates(["station", "timestamp"])
        .set_index(["station", "timestamp"])
    )
    review = base.copy()
    review["flagged_at_1pct"] = flags[0.01].reindex(review.index, fill_value=False).astype(bool)
    review["flagged_at_2pct"] = flags[0.02].reindex(review.index, fill_value=False).astype(bool)
    review["flagged_at_3pct"] = flags[0.03].reindex(review.index, fill_value=False).astype(bool)
    review["stable_all_levels"] = stable_index.reindex(review.index, fill_value=False).astype(bool)
    review["flagged_any_level"] = any_index.reindex(review.index, fill_value=False).astype(bool)
    review = review.reset_index()

    # Event match means timestamp falls within an already detected event's interval
    # at the same station. It is temporal overlap, not ground-truth validation.
    event_matches = []
    for row in review.itertuples(index=False):
        hits = events[
            (events["station"] == row.station)
            & (events["start_time"] <= row.timestamp)
            & (events["end_time"] >= row.timestamp)
        ]
        event_matches.append({
            "event_overlap": not hits.empty,
            "matched_event_ids": ";".join(hits["event_id"].astype(str).tolist()),
        })
    match_df = pd.DataFrame(event_matches)
    review = pd.concat([review.reset_index(drop=True), match_df], axis=1)

    # Broad descriptive groups only; not a physical/source classification.
    review["reading_group"] = np.select(
        [review["value"] >= 100, review["value"] >= 35, review["value"] < 5],
        ["very_high_100_plus", "elevated_35_to_99_9", "very_low_below_5"],
        default="other_5_to_34_9",
    )

    stable = review[review["stable_all_levels"]].copy()
    any_flag = review[review["flagged_any_level"]].copy()
    stable.to_csv(OUT_CSV, index=False)

    def counts(series):
        return {str(k): int(v) for k, v in series.value_counts(dropna=False).items()}

    station_summary = (
        review[review["flagged_any_level"]]
        .groupby(["station", "stable_all_levels"], as_index=False)
        .agg(observations=("timestamp", "size"),
             mean_pm25=("value", "mean"),
             median_pm25=("value", "median"),
             max_pm25=("value", "max"),
             event_overlap_count=("event_overlap", "sum"))
    )
    station_summary[["mean_pm25", "median_pm25", "max_pm25"]] = station_summary[
        ["mean_pm25", "median_pm25", "max_pm25"]
    ].round(2)

    report = {
        "purpose": "Descriptive review of stable and sensitivity-dependent ML anomalies.",
        "input_observations_scored_at_2pct": int(len(review)),
        "stable_all_levels_count": int(stable["stable_all_levels"].sum()),
        "flagged_any_level_count": int(any_flag["flagged_any_level"].sum()),
        "stable_by_station": counts(stable["station"]),
        "stable_reading_groups": counts(stable["reading_group"]),
        "stable_event_overlap_count": int(stable["event_overlap"].sum()),
        "stable_event_nonoverlap_count": int((~stable["event_overlap"]).sum()),
        "all_flagged_event_overlap_count": int(any_flag["event_overlap"].sum()),
        "all_flagged_event_nonoverlap_count": int((~any_flag["event_overlap"]).sum()),
        "station_summary_for_flagged_observations": station_summary.to_dict(orient="records"),
        "stable_examples_highest_score": stable.sort_values("anomaly_score", ascending=False)
            [["station", "timestamp", "value", "anomaly_score", "event_overlap", "matched_event_ids"]]
            .head(20).to_dict(orient="records"),
        "limitations": [
            "Event overlap is not ground truth because events were created by another heuristic detector.",
            "Stable anomaly means stable only across the tested 1%, 2%, and 3% settings.",
            "Low readings can be anomalies and must not automatically be treated as pollution spikes.",
            "No source attribution or causation is established by this review."
        ],
    }
    OUT_JSON.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("=" * 76)
    print("AIR KAVACH - STABLE ANOMALY REVIEW")
    print("=" * 76)
    print("Observations scored at 2%:", len(review))
    print("Stable at all 3 settings:", int(stable["stable_all_levels"].sum()))
    print("Flagged at any setting:", int(any_flag["flagged_any_level"].sum()))
    print("\nSTABLE ANOMALIES BY STATION")
    print(stable.groupby("station").size().to_string())
    print("\nSTABLE ANOMALIES BY READING GROUP")
    print(stable["reading_group"].value_counts().to_string())
    print("\nSTABLE ANOMALY OVERLAP WITH EXISTING EVENTS")
    print("Overlapping detected event:", int(stable["event_overlap"].sum()))
    print("No event overlap:", int((~stable["event_overlap"]).sum()))
    print("\nSTABLE ANOMALIES - TOP 20 BY SCORE")
    cols = ["station", "timestamp", "value", "anomaly_score", "reading_group", "event_overlap", "matched_event_ids"]
    print(stable.sort_values("anomaly_score", ascending=False)[cols].head(20).to_string(index=False))
    print("\nSaved:", OUT_CSV.relative_to(ROOT))
    print("Saved:", OUT_JSON.relative_to(ROOT))
    print("\nNo existing event, attribution, or map files were modified.")
    print("Event overlap is comparison only, not proof of correctness.")
    print("REVIEW COMPLETE")

if __name__ == "__main__":
    main()
