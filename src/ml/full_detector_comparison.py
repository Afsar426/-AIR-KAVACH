"""
AIR KAVACH - Full-dataset comparison: Isolation Forest vs statistical detector.

Run from the project root:
    python src/ml/full_detector_comparison.py

Reads existing processed data and saved model outputs. It does not retrain models
or modify existing events, attribution, confidence, or map outputs.
The report is descriptive: no verified labels exist, so it does not calculate
accuracy, precision, recall, or false-positive rate.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
AQ_PATH = ROOT / "data" / "processed" / "air_quality" / "air_quality.parquet"
BASELINE_PATH = ROOT / "data" / "features" / "ml_anomaly_scores.parquet"
EVENTS_PATH = ROOT / "data" / "processed" / "events" / "pollution_events.parquet"
OUT_ROWS = ROOT / "reports" / "generated" / "full_detector_comparison.csv"
OUT_EPISODES = ROOT / "reports" / "generated" / "detector_disagreement_episodes.csv"
OUT_JSON = ROOT / "reports" / "generated" / "full_detector_comparison_report.json"

def boolify(series):
    if series.dtype == bool:
        return series
    return series.astype(str).str.strip().str.lower().isin(["true", "1", "yes"])

def value_group(v):
    if pd.isna(v):
        return "missing"
    if v < 5:
        return "very_low_below_5"
    if v < 35:
        return "5_to_below_35"
    if v < 100:
        return "35_to_below_100"
    return "100_plus"

def main():
    for p in [AQ_PATH, BASELINE_PATH, EVENTS_PATH]:
        if not p.exists():
            raise FileNotFoundError(f"Required input missing: {p}")

    aq = pd.read_parquet(AQ_PATH)
    baseline = pd.read_parquet(BASELINE_PATH)
    events = pd.read_parquet(EVENTS_PATH)

    req_aq = {"station", "timestamp", "value"}
    req_base = {"station", "timestamp", "value", "anomaly_score",
                "isolation_forest_anomaly", "statistical_flag"}
    req_events = {"event_id", "station", "start_time", "end_time"}
    for label, df, req in [
        ("air quality", aq, req_aq),
        ("baseline", baseline, req_base),
        ("events", events, req_events),
    ]:
        missing = req - set(df.columns)
        if missing:
            raise ValueError(f"{label} input missing columns: {sorted(missing)}")

    for df in [aq, baseline]:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    events["start_time"] = pd.to_datetime(events["start_time"], utc=True, errors="coerce")
    events["end_time"] = pd.to_datetime(events["end_time"], utc=True, errors="coerce")
    baseline["isolation_forest_anomaly"] = boolify(baseline["isolation_forest_anomaly"])
    baseline["statistical_flag"] = boolify(baseline["statistical_flag"])
    baseline["anomaly_score"] = pd.to_numeric(baseline["anomaly_score"], errors="coerce")
    baseline["value"] = pd.to_numeric(baseline["value"], errors="coerce")
    aq["value"] = pd.to_numeric(aq["value"], errors="coerce")

    # Verify that the baseline output aligns one-to-one with the processed sensor data.
    if aq.duplicated(["station", "timestamp"]).any():
        raise ValueError("Duplicate station/timestamp keys in processed air-quality data.")
    if baseline.duplicated(["station", "timestamp"]).any():
        raise ValueError("Duplicate station/timestamp keys in saved baseline.")
    merged = aq[["station", "timestamp", "value"]].merge(
        baseline.drop(columns=["value"], errors="ignore"),
        on=["station", "timestamp"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    if not merged["_merge"].eq("both").all():
        missing = int((merged["_merge"] != "both").sum())
        raise ValueError(f"{missing} air-quality rows did not match the saved baseline output.")
    merged = merged.drop(columns="_merge")
    # Keep processed data's value as the canonical reading.
    merged["value"] = aq["value"].to_numpy()
    merged["ml_scored"] = merged["anomaly_score"].notna()
    merged["agreement_group"] = np.select(
        [
            merged["isolation_forest_anomaly"] & merged["statistical_flag"],
            merged["isolation_forest_anomaly"] & ~merged["statistical_flag"],
            ~merged["isolation_forest_anomaly"] & merged["statistical_flag"],
        ],
        ["both_flagged", "ml_only", "statistical_only"],
        default="neither_flagged",
    )
    merged["reading_group"] = merged["value"].map(value_group)

    scored = merged[merged["ml_scored"]].copy()
    if scored.empty:
        raise RuntimeError("No rows have ML scores; cannot compare on common scored rows.")

    # Summary on common rows with ML scores.
    group_counts = scored["agreement_group"].value_counts().to_dict()
    both = int(group_counts.get("both_flagged", 0))
    ml_only = int(group_counts.get("ml_only", 0))
    stat_only = int(group_counts.get("statistical_only", 0))
    neither = int(group_counts.get("neither_flagged", 0))
    common_n = len(scored)
    agreement = (both + neither) / common_n
    flagged_union = both + ml_only + stat_only
    jaccard = both / flagged_union if flagged_union else None

    # Per-station comparison.
    per_station = []
    for station, g in scored.groupby("station", sort=True):
        counts = g["agreement_group"].value_counts().to_dict()
        per_station.append({
            "station": str(station),
            "scored_rows": int(len(g)),
            "both_flagged": int(counts.get("both_flagged", 0)),
            "ml_only": int(counts.get("ml_only", 0)),
            "statistical_only": int(counts.get("statistical_only", 0)),
            "neither_flagged": int(counts.get("neither_flagged", 0)),
            "ml_flagged": int(g["isolation_forest_anomaly"].sum()),
            "statistical_flagged": int(g["statistical_flag"].sum()),
            "agreement_percent": round(100 * (
                counts.get("both_flagged", 0) + counts.get("neither_flagged", 0)
            ) / len(g), 2),
        })

    # Analyze what disagreement observations look like, particularly low readings.
    disagreement = scored[scored["agreement_group"].isin(["ml_only", "statistical_only"])].copy()
    disagreement["event_ids"] = ""
    for idx, row in disagreement.iterrows():
        hits = events[
            (events["station"] == row["station"])
            & (events["start_time"] <= row["timestamp"])
            & (events["end_time"] >= row["timestamp"])
        ]
        disagreement.at[idx, "event_ids"] = ";".join(hits["event_id"].astype(str).tolist())
    disagreement["event_overlap"] = disagreement["event_ids"].astype(str).str.len().gt(0)
    disagreement_cols = [
        "station", "timestamp", "value", "anomaly_score", "gap_minutes",
        "past_mean", "past_std", "deviation", "agreement_group",
        "reading_group", "event_overlap", "event_ids"
    ]
    disagreement_cols = [c for c in disagreement_cols if c in disagreement.columns]
    disagreement[disagreement_cols].sort_values(
        ["agreement_group", "anomaly_score"], ascending=[True, False]
    ).to_csv(OUT_ROWS, index=False)

    disagreement_reading = (
        disagreement.groupby(["agreement_group", "reading_group"], as_index=False)
        .agg(observations=("value", "size"),
             mean_pm25=("value", "mean"),
             median_pm25=("value", "median"),
             max_pm25=("value", "max"),
             event_overlap_count=("event_overlap", "sum"))
    )
    disagreement_reading[["mean_pm25", "median_pm25", "max_pm25"]] = disagreement_reading[
        ["mean_pm25", "median_pm25", "max_pm25"]
    ].round(2)

    # Group consecutive disagreement observations into review episodes per station
    # and disagreement type. This is a convenience grouping, not event truth.
    d = disagreement.sort_values(["station", "agreement_group", "timestamp"]).copy()
    delta = d.groupby(["station", "agreement_group"])["timestamp"].diff().dt.total_seconds().div(60)
    d["new_episode"] = delta.isna() | (delta > 30)
    d["episode_number"] = d.groupby(["station", "agreement_group"])["new_episode"].cumsum().astype(int)
    d["review_episode_id"] = d.apply(
        lambda r: f"DISAGREE-{str(r['station']).upper().replace(' ', '-')}-"
                  f"{str(r['agreement_group']).upper()}-{r['episode_number']:03d}", axis=1
    )
    episodes = (
        d.groupby(["station", "agreement_group", "review_episode_id"], as_index=False)
        .agg(
            start_time=("timestamp", "min"),
            end_time=("timestamp", "max"),
            observations=("timestamp", "size"),
            peak_pm25=("value", "max"),
            min_pm25=("value", "min"),
            mean_pm25=("value", "mean"),
            max_anomaly_score=("anomaly_score", "max"),
            any_event_overlap=("event_overlap", "max"),
            event_ids=("event_ids", lambda s: ";".join(sorted({
                item for v in s.fillna("").astype(str)
                for item in v.split(";") if item
            }))),
        )
    )
    episodes["duration_minutes"] = (episodes["end_time"] - episodes["start_time"]).dt.total_seconds() / 60
    episodes.to_csv(OUT_EPISODES, index=False)

    # A score threshold of 35 is only a descriptive bucket used in prior review,
    # not a regulatory/health threshold or ground-truth definition.
    high_ml_only = disagreement[
        (disagreement["agreement_group"] == "ml_only") & (disagreement["value"] >= 35)
    ]
    low_ml_only = disagreement[
        (disagreement["agreement_group"] == "ml_only") & (disagreement["value"] < 5)
    ]
    event_overlap_disagreement = int(disagreement["event_overlap"].sum())
    report = {
        "status": "DESCRIPTIVE_COMPARISON_COMPLETE",
        "rows": {
            "processed_air_quality": int(len(aq)),
            "saved_baseline": int(len(baseline)),
            "joined_rows": int(len(merged)),
            "rows_with_ml_scores": int(common_n),
            "rows_without_ml_scores": int((~merged["ml_scored"]).sum()),
        },
        "full_dataset_flag_counts_in_saved_baseline": {
            "ml_flagged_all_rows": int(merged["isolation_forest_anomaly"].sum()),
            "statistical_flagged_all_rows": int(merged["statistical_flag"].sum()),
        },
        "common_scored_rows_comparison": {
            "both_flagged": both,
            "ml_only": ml_only,
            "statistical_only": stat_only,
            "neither_flagged": neither,
            "agreement_percent": round(100 * agreement, 2),
            "flagged_union": int(flagged_union),
            "jaccard_overlap_percent": round(100 * jaccard, 2) if jaccard is not None else None,
            "warning": "Agreement is not accuracy; the large neither-flagged group can inflate agreement.",
        },
        "per_station": per_station,
        "disagreement_reading_groups": disagreement_reading.to_dict(orient="records"),
        "disagreement_summary": {
            "total_disagreement_observations": int(len(disagreement)),
            "ml_only_observations_with_value_ge_35": int(len(high_ml_only)),
            "ml_only_observations_with_value_lt_5": int(len(low_ml_only)),
            "disagreement_observations_overlapping_existing_events": event_overlap_disagreement,
            "review_episodes_grouped_with_30_min_gap": int(len(episodes)),
        },
        "limitations": [
            "No independently verified anomaly labels are available.",
            "This compares two detectors on the same underlying sensor data; it is not independent validation.",
            "The statistical_flag column reproduces the current statistical baseline saved in the ML output; it is not necessarily identical to the gap-aware diagnostic baseline.",
            "ML-only does not mean false positive; statistical-only does not mean false negative.",
            "The 35 and 5 µg/m³ cutoffs are descriptive review buckets only, not validated thresholds.",
            "Event overlap is temporal comparison only, not proof of pollution causation or source identity.",
        ],
        "outputs": [
            str(OUT_ROWS.relative_to(ROOT)),
            str(OUT_EPISODES.relative_to(ROOT)),
            str(OUT_JSON.relative_to(ROOT)),
        ],
    }
    OUT_JSON.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("=" * 80)
    print("AIR KAVACH - FULL DETECTOR COMPARISON")
    print("=" * 80)
    print("Processed observations:", len(aq))
    print("Rows with ML scores:", common_n)
    print("Rows without ML scores:", int((~merged["ml_scored"]).sum()))
    print("\nCOMMON SCORED ROWS")
    print(f"Both flagged:        {both}")
    print(f"ML only:             {ml_only}")
    print(f"Statistical only:    {stat_only}")
    print(f"Neither flagged:     {neither}")
    print(f"Agreement:           {100 * agreement:.2f}% (NOT accuracy)")
    print(f"Jaccard flag overlap:{100 * jaccard: .2f}%" if jaccard is not None else "Jaccard flag overlap: N/A")
    print("\nPER-STATION COMPARISON")
    print(pd.DataFrame(per_station).to_string(index=False))
    print("\nDISAGREEMENT BY READING GROUP")
    print(disagreement_reading.to_string(index=False))
    print("\nDISAGREEMENT SUMMARY")
    print(json.dumps(report["disagreement_summary"], indent=2))
    print("\nSaved:", OUT_ROWS.relative_to(ROOT))
    print("Saved:", OUT_EPISODES.relative_to(ROOT))
    print("Saved:", OUT_JSON.relative_to(ROOT))
    print("\nNo model retraining or existing event/attribution/map changes.")
    print("This is a detector comparison, not an accuracy test.")
    print("COMPARISON COMPLETE")

if __name__ == "__main__":
    main()
