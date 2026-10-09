from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd

ROOT = Path.cwd()
ML_PATH = ROOT / "data/features/ml_anomaly_scores.parquet"
AIR_PATH = ROOT / "data/processed/air_quality/air_quality.parquet"
EVENT_PATH = ROOT / "data/processed/events/pollution_events.parquet"
WIND_PATH = ROOT / "data/processed/weather/wind.parquet"
SENSITIVITY_PATH = ROOT / "data/features/ml_anomaly_sensitivity.parquet"
OUT_DIR = ROOT / "reports/generated"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ELEVATED_THRESHOLD = 35.0
LOW_THRESHOLD = 5.0
CONTEXT_HOURS = 2
MAX_CONTEXT_GAP_MINUTES = 15
WIND_TOLERANCE_MINUTES = 30


def fail(message):
    print(f"ERROR: {message}")
    sys.exit(1)


def load(path, name, required=True):
    if not path.exists():
        if required:
            fail(f"{name} not found: {path}")
        return None
    try:
        return pd.read_parquet(path)
    except Exception as exc:
        fail(f"Could not read {name}: {exc}")


def first_col(df, options):
    return next((c for c in options if c in df.columns), None)


def prepare_times(df):
    if df is not None and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df


def attach_event_overlap(candidates, events):
    candidates = candidates.copy()
    candidates["event_overlap"] = False
    candidates["overlapping_event_ids"] = ""
    if events is None or events.empty:
        return candidates
    station_col = first_col(events, ["station", "station_name"])
    start_col = first_col(events, ["start_time", "event_start", "start_timestamp", "start"])
    end_col = first_col(events, ["end_time", "event_end", "end_timestamp", "end"])
    id_col = first_col(events, ["event_id", "event_code", "id"])
    if not all([station_col, start_col, end_col]):
        print("WARNING: Event columns not recognized; skipping overlap check.")
        return candidates
    ev = events.copy()
    ev[start_col] = pd.to_datetime(ev[start_col], utc=True, errors="coerce")
    ev[end_col] = pd.to_datetime(ev[end_col], utc=True, errors="coerce")
    for idx, row in candidates.iterrows():
        match = ev[
            (ev[station_col].astype(str) == str(row["station"])) &
            (ev[start_col] <= row["timestamp"]) &
            (ev[end_col] >= row["timestamp"])
        ]
        if len(match):
            candidates.at[idx, "event_overlap"] = True
            candidates.at[idx, "overlapping_event_ids"] = (
                ";".join(match[id_col].astype(str).unique()) if id_col else f"{len(match)} event(s)"
            )
    return candidates


def add_context(candidates, air):
    air = air.copy()
    air["timestamp"] = pd.to_datetime(air["timestamp"], utc=True, errors="coerce")
    air["value"] = pd.to_numeric(air["value"], errors="coerce")
    air = air.dropna(subset=["station", "timestamp", "value"]).sort_values(["station", "timestamp"])
    rows = []
    for _, cand in candidates.iterrows():
        ts, station = cand["timestamp"], cand["station"]
        same = air[air["station"].astype(str) == str(station)]
        window = same[
            (same["timestamp"] >= ts - pd.Timedelta(hours=CONTEXT_HOURS)) &
            (same["timestamp"] <= ts + pd.Timedelta(hours=CONTEXT_HOURS))
        ].sort_values("timestamp")
        before = same[same["timestamp"] < ts].tail(1)
        after = same[same["timestamp"] > ts].head(1)
        intervals = window["timestamp"].diff().dropna().dt.total_seconds() / 60
        max_gap = float(intervals.max()) if len(intervals) else None
        gap_count = int((intervals > MAX_CONTEXT_GAP_MINUTES).sum()) if len(intervals) else 0
        pv = float(before.iloc[0]["value"]) if len(before) else None
        nv = float(after.iloc[0]["value"]) if len(after) else None
        trend = None
        if pv is not None and nv is not None:
            trend = "rising_across_candidate" if nv > pv else ("falling_across_candidate" if nv < pv else "flat_across_candidate")
        out = cand.to_dict()
        out.update({
            "context_window_hours_each_side": CONTEXT_HOURS,
            "context_observation_count": int(len(window)),
            "context_min_value": float(window["value"].min()) if len(window) else None,
            "context_mean_value": float(window["value"].mean()) if len(window) else None,
            "context_max_value": float(window["value"].max()) if len(window) else None,
            "nearest_previous_timestamp": before.iloc[0]["timestamp"].isoformat() if len(before) else None,
            "nearest_previous_value": pv,
            "nearest_next_timestamp": after.iloc[0]["timestamp"].isoformat() if len(after) else None,
            "nearest_next_value": nv,
            "context_max_gap_minutes": max_gap,
            "context_gap_count_over_15min": gap_count,
            "context_has_gap_over_15min": bool(gap_count > 0),
            "simple_context_trend": trend,
        })
        rows.append(out)
    return pd.DataFrame(rows)


def add_wind(candidates, wind):
    candidates = candidates.copy()
    candidates["wind_timestamp"] = None
    candidates["wind_direction_deg"] = np.nan
    candidates["wind_speed_mps"] = np.nan
    candidates["wind_time_difference_minutes"] = np.nan
    if wind is None or wind.empty:
        print("WARNING: Wind file missing/empty; wind context skipped.")
        return candidates
    if not {"timestamp", "station"}.issubset(wind.columns):
        print("WARNING: Wind data columns not recognized; wind context skipped.")
        return candidates
    w = wind.copy()
    w["timestamp"] = pd.to_datetime(w["timestamp"], utc=True, errors="coerce")
    for col in ["wind_direction_deg", "wind_speed_mps"]:
        if col not in w.columns:
            w[col] = np.nan
        w[col] = pd.to_numeric(w[col], errors="coerce")
    w = w.dropna(subset=["timestamp", "station"])
    for idx, cand in candidates.iterrows():
        same = w[w["station"].astype(str) == str(cand["station"])].copy()
        if same.empty:
            continue
        same["diff_min"] = (same["timestamp"] - cand["timestamp"]).abs().dt.total_seconds() / 60
        nearest = same.sort_values(["diff_min", "timestamp"]).iloc[0]
        if nearest["diff_min"] <= WIND_TOLERANCE_MINUTES:
            candidates.at[idx, "wind_timestamp"] = nearest["timestamp"].isoformat()
            candidates.at[idx, "wind_time_difference_minutes"] = float(nearest["diff_min"])
            candidates.at[idx, "wind_direction_deg"] = nearest["wind_direction_deg"]
            candidates.at[idx, "wind_speed_mps"] = nearest["wind_speed_mps"]
    return candidates


def main():
    print("=" * 68)
    print("AIR KAVACH — ML-ONLY ANOMALY CONTEXT REVIEW")
    print("=" * 68)
    ml = prepare_times(load(ML_PATH, "ML anomaly scores"))
    air = prepare_times(load(AIR_PATH, "processed air quality"))
    events = prepare_times(load(EVENT_PATH, "pollution events", required=False))
    wind = prepare_times(load(WIND_PATH, "wind data", required=False))
    sensitivity = prepare_times(load(SENSITIVITY_PATH, "sensitivity data", required=False))

    if not {"station", "timestamp", "value"}.issubset(ml.columns):
        fail(f"ML file needs station/timestamp/value. Columns: {list(ml.columns)}")
    ml_flag = first_col(ml, ["isolation_forest_anomaly", "ml_anomaly", "is_anomaly", "anomaly_flag"])
    stat_flag = first_col(ml, ["statistical_flag", "stat_flag", "baseline_flag"])
    score_col = first_col(ml, ["anomaly_score", "score", "decision_score"])
    if not ml_flag or not stat_flag:
        fail(f"Could not identify ML/statistical flag columns. Columns: {list(ml.columns)}")
    ml[ml_flag] = ml[ml_flag].fillna(False).astype(bool)
    ml[stat_flag] = ml[stat_flag].fillna(False).astype(bool)
    ml["value"] = pd.to_numeric(ml["value"], errors="coerce")
    ml_only = ml[ml[ml_flag] & ~ml[stat_flag]].copy()

    elevated = ml_only[ml_only["value"] >= ELEVATED_THRESHOLD].copy()
    low = ml_only[ml_only["value"] < LOW_THRESHOLD].copy()
    middle_count = int(((ml_only["value"] >= LOW_THRESHOLD) & (ml_only["value"] < ELEVATED_THRESHOLD)).sum())
    if score_col and score_col != "anomaly_score":
        elevated = elevated.rename(columns={score_col: "anomaly_score"})
        low = low.rename(columns={score_col: "anomaly_score"})

    elevated = add_wind(attach_event_overlap(add_context(elevated, air), events), wind)
    low = add_wind(attach_event_overlap(add_context(low, air), events), wind)

    if sensitivity is not None and {"station", "timestamp"}.issubset(sensitivity.columns):
        flag_cols = [c for c in sensitivity.columns if ("flag" in c.lower() or "anomaly" in c.lower()) and c not in {"station", "timestamp"}]
        if flag_cols:
            sens = sensitivity[["station", "timestamp"] + flag_cols].drop_duplicates(["station", "timestamp"])
            elevated = elevated.merge(sens, on=["station", "timestamp"], how="left", suffixes=("", "_sensitivity"))
            low = low.merge(sens, on=["station", "timestamp"], how="left", suffixes=("", "_sensitivity"))

    elevated_path = OUT_DIR / "ml_only_elevated_review.csv"
    low_path = OUT_DIR / "ml_only_low_reading_review.csv"
    report_path = OUT_DIR / "ml_only_elevated_review_report.json"
    elevated.sort_values(["station", "timestamp"]).to_csv(elevated_path, index=False)
    low.sort_values(["station", "timestamp"]).to_csv(low_path, index=False)

    def counts(df):
        return {str(k): int(v) for k, v in df.groupby("station").size().to_dict().items()} if len(df) else {}

    report = {
        "purpose": "Contextual review only; not ground-truth model validation.",
        "counts": {
            "ml_scored_rows": int(len(ml)),
            "ml_only_rows": int(len(ml_only)),
            "elevated_ml_only_ge_35": int(len(elevated)),
            "low_ml_only_lt_5": int(len(low)),
            "middle_ml_only_5_to_below_35": middle_count,
        },
        "elevated": {
            "station_counts": counts(elevated),
            "event_overlap_count": int(elevated["event_overlap"].sum()) if len(elevated) else 0,
            "context_gap_over_15min_count": int(elevated["context_has_gap_over_15min"].sum()) if len(elevated) else 0,
            "wind_within_30min_count": int(elevated["wind_time_difference_minutes"].notna().sum()) if len(elevated) else 0,
            "min_value": float(elevated["value"].min()) if len(elevated) else None,
            "median_value": float(elevated["value"].median()) if len(elevated) else None,
            "max_value": float(elevated["value"].max()) if len(elevated) else None,
        },
        "low_readings": {"station_counts": counts(low)},
        "thresholds": {"elevated": "PM2.5 value >= 35 µg/m³", "low_review": "PM2.5 value < 5 µg/m³", "context_hours_each_side": 2, "gap_warning_minutes": 15, "wind_tolerance_minutes": 30},
        "warnings": [
            "ML-only means ML flagged a row and the statistical baseline did not; it is not a confirmed true positive.",
            "Low readings are candidates for data-quality review, not automatically sensor errors.",
            "Event overlap uses existing statistical event windows and is not independent validation.",
            "Wind alignment is contextual evidence, not proof of source causation."
        ],
        "outputs": [str(elevated_path.relative_to(ROOT)), str(low_path.relative_to(ROOT)), str(report_path.relative_to(ROOT))]
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\nML-scored rows: {len(ml)}")
    print(f"ML-only observations: {len(ml_only)}")
    print(f"Elevated ML-only observations (>=35): {len(elevated)}")
    print(f"Low-reading ML-only observations (<5): {len(low)}")
    print(f"Other ML-only observations (5 to <35): {middle_count}")
    print("\nElevated candidates by station:")
    print(elevated.groupby("station").size().to_string() if len(elevated) else "None")
    print(f"Overlapping existing events: {report['elevated']['event_overlap_count']}")
    print(f"With >15-minute context gaps: {report['elevated']['context_gap_over_15min_count']}")
    print(f"With wind within 30 minutes: {report['elevated']['wind_within_30min_count']}")
    print("\nSaved:")
    print(elevated_path)
    print(low_path)
    print(report_path)
    print("\nThis is a review report, not an accuracy score or ground-truth test.")


if __name__ == "__main__":
    main()
