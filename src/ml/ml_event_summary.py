"""
AIR KAVACH - Group ML anomaly observations into reviewable episodes and compare
them with existing statistical events.

Run from the project root:
    python src/ml/ml_event_summary.py

This is an analysis-only script. It does not alter the existing event detector,
source-attribution results, confidence values, or map data.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REVIEW_FILE = ROOT / "reports" / "generated" / "ml_stable_anomaly_review.csv"
EVENTS_FILE = ROOT / "data" / "processed" / "events" / "pollution_events.parquet"
OUT_EPISODES = ROOT / "reports" / "generated" / "ml_stable_anomaly_episodes.csv"
OUT_COMPARISON = ROOT / "reports" / "generated" / "ml_episode_event_comparison.csv"
OUT_REPORT = ROOT / "reports" / "generated" / "ml_episode_summary.json"

GAP_MINUTES = 30
REVIEW_LEVEL = 35.0

def main():
    if not REVIEW_FILE.exists():
        raise FileNotFoundError(f"Missing input: {REVIEW_FILE}")
    if not EVENTS_FILE.exists():
        raise FileNotFoundError(f"Missing input: {EVENTS_FILE}")

    df = pd.read_csv(REVIEW_FILE)
    events = pd.read_parquet(EVENTS_FILE)

    needed = {"station", "timestamp", "value", "anomaly_score",
              "stable_all_levels", "event_overlap", "matched_event_ids"}
    if needed - set(df.columns):
        raise ValueError(f"Review CSV missing columns: {sorted(needed - set(df.columns))}")
    event_needed = {"event_id", "station", "start_time", "end_time", "peak_pm25"}
    if event_needed - set(events.columns):
        raise ValueError(f"Event data missing columns: {sorted(event_needed - set(events.columns))}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    events["start_time"] = pd.to_datetime(events["start_time"], utc=True, errors="coerce")
    events["end_time"] = pd.to_datetime(events["end_time"], utc=True, errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["anomaly_score"] = pd.to_numeric(df["anomaly_score"], errors="coerce")
    df = df.dropna(subset=["station", "timestamp", "value", "anomaly_score"]).copy()
    df["stable_all_levels"] = df["stable_all_levels"].astype(str).str.lower().isin(["true", "1", "yes"])
    stable = df[df["stable_all_levels"]].copy()

    # Build episodes from stable observations at each station. An episode ends
    # if the gap between stable anomaly timestamps exceeds 30 minutes.
    stable = stable.sort_values(["station", "timestamp"])
    stable["minutes_since_previous_stable"] = (
        stable.groupby("station")["timestamp"].diff().dt.total_seconds().div(60)
    )
    stable["new_episode"] = (
        stable["minutes_since_previous_stable"].isna()
        | (stable["minutes_since_previous_stable"] > GAP_MINUTES)
    )
    stable["episode_number"] = stable.groupby("station")["new_episode"].cumsum().astype(int)
    stable["episode_id"] = stable.apply(
        lambda r: f"ML-{str(r['station']).upper().replace(' ', '-')}-{r['episode_number']:03d}",
        axis=1,
    )

    episodes = (
        stable.groupby(["station", "episode_id"], as_index=False)
        .agg(
            start_time=("timestamp", "min"),
            end_time=("timestamp", "max"),
            anomaly_observations=("timestamp", "size"),
            peak_pm25=("value", "max"),
            min_pm25=("value", "min"),
            mean_pm25=("value", "mean"),
            max_anomaly_score=("anomaly_score", "max"),
            any_existing_event_overlap=("event_overlap", "max"),
            matched_event_ids=("matched_event_ids", lambda s: ";".join(
                sorted({token for value in s.fillna("").astype(str)
                        for token in value.split(";") if token.strip()})
            )),
        )
    )
    episodes["duration_minutes"] = (
        episodes["end_time"] - episodes["start_time"]
    ).dt.total_seconds().div(60)
    episodes["episode_group"] = np.select(
        [
            episodes["peak_pm25"] >= 100,
            episodes["peak_pm25"] >= REVIEW_LEVEL,
            episodes["peak_pm25"] < 5,
        ],
        ["peak_100_plus", "peak_35_to_99_9", "low_reading_review"],
        default="other_review",
    )
    episodes["mean_pm25"] = episodes["mean_pm25"].round(2)
    episodes["max_anomaly_score"] = episodes["max_anomaly_score"].round(6)

    # Compare each ML episode interval with existing statistical events at the
    # same station. Temporal overlap is descriptive only, not truth validation.
    comp = []
    for ep in episodes.itertuples(index=False):
        hits = events[
            (events["station"] == ep.station)
            & (events["start_time"] <= ep.end_time)
            & (events["end_time"] >= ep.start_time)
        ]
        comp.append({
            "station": ep.station,
            "episode_id": ep.episode_id,
            "ml_start_time": ep.start_time,
            "ml_end_time": ep.end_time,
            "ml_peak_pm25": ep.peak_pm25,
            "ml_anomaly_observations": ep.anomaly_observations,
            "overlapping_statistical_event_count": int(len(hits)),
            "overlapping_event_ids": ";".join(hits["event_id"].astype(str).tolist()),
            "overlap_status": "overlaps_existing_event" if len(hits) else "no_temporal_overlap",
        })
    comparison = pd.DataFrame(comp)

    episodes.to_csv(OUT_EPISODES, index=False)
    comparison.to_csv(OUT_COMPARISON, index=False)
    report = {
        "method": {
            "stable_definition": "Observation flagged at contamination 0.01, 0.02 and 0.03.",
            "episode_gap_minutes": GAP_MINUTES,
            "event_comparison": "Same-station time-interval overlap.",
            "interpretation": "Descriptive review, not ground-truth validation or source attribution."
        },
        "stable_observation_count": int(len(stable)),
        "episode_count": int(len(episodes)),
        "episodes_by_station": {str(k): int(v) for k, v in episodes.groupby("station").size().items()},
        "episodes_by_group": {str(k): int(v) for k, v in episodes.groupby("episode_group").size().items()},
        "episodes_overlapping_existing_event": int((comparison["overlapping_statistical_event_count"] > 0).sum()),
        "episodes_without_temporal_overlap": int((comparison["overlapping_statistical_event_count"] == 0).sum()),
        "high_peak_episodes": episodes[episodes["peak_pm25"] >= 100].to_dict(orient="records"),
        "limitations": [
            "Episode grouping is an operational review rule, not a validated event segmentation model.",
            "A stable ML anomaly can be a low reading or sensor/data anomaly.",
            "Overlap with the statistical detector is not independent validation because both use the same sensor dataset.",
            "Do not infer a factory source from anomaly or event overlap."
        ]
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("=" * 76)
    print("AIR KAVACH - ML ANOMALY EPISODE SUMMARY")
    print("=" * 76)
    print("Stable anomaly observations:", len(stable))
    print("Grouped ML episodes:", len(episodes))
    print("\nEPISODES BY STATION")
    print(episodes.groupby("station").size().to_string())
    print("\nEPISODES BY GROUP")
    print(episodes["episode_group"].value_counts().to_string())
    print("\nOVERLAP WITH EXISTING STATISTICAL EVENTS")
    print("Episodes overlapping:", int((comparison["overlapping_statistical_event_count"] > 0).sum()))
    print("Episodes with no overlap:", int((comparison["overlapping_statistical_event_count"] == 0).sum()))
    print("\nEPISODES WITH PEAK PM2.5 >= 100")
    high = episodes[episodes["peak_pm25"] >= 100]
    if high.empty:
        print("None")
    else:
        print(high[["station", "episode_id", "start_time", "end_time",
                    "anomaly_observations", "peak_pm25", "matched_event_ids"]].to_string(index=False))
    print("\nSaved:", OUT_EPISODES.relative_to(ROOT))
    print("Saved:", OUT_COMPARISON.relative_to(ROOT))
    print("Saved:", OUT_REPORT.relative_to(ROOT))
    print("\nNo existing detector, attribution, or map files were modified.")
    print("SUMMARY COMPLETE")

if __name__ == "__main__":
    main()
