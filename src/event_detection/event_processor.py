from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from src.utils.logger import get_logger
from src.utils.config import AIR_QUALITY_FILE, EVENTS_FILE
from src.geo.registry import GeoRegistryService
from src.event_detection.lifecycle import EventLifecycleManager

logger = get_logger("event_processor")

ROLLING_WINDOW = 96  # 24 hours * 4 readings/hour (historical context)
MIN_PERIODS = 24     # Minimum 6 hours of historical readings required
MIN_EVENT_READINGS = 4  # Minimum 4 consecutive elevated readings = 1 hour nominal
MAX_SPIKE_GAP_MINUTES = 30  # Gaps > 30 mins segment episodes
Z_THRESHOLD = 2.0
ALGORITHM_VERSION = "2.1.0-leakage-free"


class EventProcessor:
    def __init__(self, input_file: Optional[Path] = None, output_file: Optional[Path] = None):
        self.input_file = input_file or AIR_QUALITY_FILE
        self.output_file = output_file or EVENTS_FILE

    def detect_events(self, df: Optional[pd.DataFrame] = None, save: bool = True) -> pd.DataFrame:
        """
        Detects pollution events from processed air quality observations.
        Ensures strict past-only baseline without current-observation contamination,
        handles temporal gaps between readings, and guarantees idempotent event IDs.
        """
        if df is None:
            if not self.input_file.exists():
                raise FileNotFoundError(f"Air quality dataset missing: {self.input_file}")
            df = pd.read_parquet(self.input_file)
        else:
            df = df.copy()

        if df.empty:
            return pd.DataFrame()

        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        if "parameter" in df.columns:
            df = df.drop_duplicates(subset=["station", "timestamp", "parameter"], keep="last")
        else:
            df = df.drop_duplicates(subset=["station", "timestamp"], keep="last")
        df = df.sort_values(["station", "timestamp"]).reset_index(drop=True)
        latest_obs_by_station = df.groupby("station")["timestamp"].max().to_dict()

        # Gap detection between consecutive station readings
        df["gap_minutes"] = df.groupby("station")["timestamp"].diff().dt.total_seconds() / 60
        starts_segment = df["gap_minutes"].isna() | (df["gap_minutes"] > MAX_SPIKE_GAP_MINUTES)
        df["segment_id"] = starts_segment.groupby(df["station"]).cumsum()

        # Strict past-only rolling baseline using shift(1) to avoid current observation contamination
        keys = ["station", "segment_id"]
        grouped_vals = df.groupby(keys, sort=False)["value"]

        df["rolling_mean"] = grouped_vals.transform(
            lambda s: s.shift(1).rolling(ROLLING_WINDOW, min_periods=MIN_PERIODS).mean()
        )
        df["rolling_std"] = grouped_vals.transform(
            lambda s: s.shift(1).rolling(ROLLING_WINDOW, min_periods=MIN_PERIODS).std()
        )

        # Statistical anomaly indicator
        df["z_score"] = (df["value"] - df["rolling_mean"]) / df["rolling_std"].replace(0, np.nan)
        df["is_spike"] = (
            (df["z_score"] >= Z_THRESHOLD) &
            (df["value"] > df["rolling_mean"]) &
            df["rolling_mean"].notna()
        )

        # Segment consecutive spikes; break if gap > MAX_SPIKE_GAP_MINUTES
        df["spike_gap"] = df.groupby("station")["timestamp"].diff().dt.total_seconds() / 60
        df["spike_break"] = (
            df["is_spike"].ne(df.groupby("station")["is_spike"].shift()) |
            (df["is_spike"] & (df["spike_gap"] > MAX_SPIKE_GAP_MINUTES))
        )
        df["spike_group"] = df.groupby("station")["spike_break"].cumsum()

        spikes = df[df["is_spike"]].copy()

        events = []
        if not spikes.empty:
            # Sort chronologically for deterministic event assignment
            for (station, group_id), group in spikes.groupby(["station", "spike_group"], sort=True):
                if len(group) < MIN_EVENT_READINGS:
                    continue

                start_time = group["timestamp"].min()
                end_time = group["timestamp"].max()
                peak_row = group.loc[group["value"].idxmax()]
                duration = float((end_time - start_time).total_seconds() / 60 + 15)

                latest_stn_ts = latest_obs_by_station.get(str(station), end_time)
                lifecycle_meta = EventLifecycleManager.classify_event(
                    start_time=start_time,
                    end_time=end_time,
                    latest_station_obs_time=latest_stn_ts,
                    readings_count=int(len(group)),
                )

                events.append({
                    "station": str(station),
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_minutes": duration,
                    "peak_pm25": round(float(peak_row["value"]), 2),
                    "peak_time": peak_row["timestamp"],
                    "peak_z_score": round(float(peak_row["z_score"]), 2),
                    "mean_pm25": round(float(group["value"].mean()), 2),
                    "baseline_mean": round(float(group["rolling_mean"].mean()), 2),
                    "max_z_score": round(float(group["z_score"].max()), 2),
                    "readings": int(len(group)),
                    "detection_method": "rolling_z_score_past_only",
                    "algorithm_version": ALGORITHM_VERSION,
                    "event_status": "confirmed_anomaly",
                    "temporal_status": lifecycle_meta["temporal_status"],
                    "lifecycle_label": lifecycle_meta["lifecycle_label"],
                    "is_active": lifecycle_meta["is_active"],
                    "latest_station_observation": lifecycle_meta["latest_station_observation"],
                    "pollutant": "pm25",
                    "city": "Indore",
                    "state_ut": "Madhya Pradesh",
                })

        events_df = pd.DataFrame(events)
        if not events_df.empty:
            # Deterministic, stable event IDs sorted chronologically
            events_df = events_df.sort_values(["start_time", "station"]).reset_index(drop=True)
            events_df["event_id"] = [f"EVT-{i+1:04d}" for i in range(len(events_df))]
            # Reorder columns with event_id first
            cols = ["event_id"] + [c for c in events_df.columns if c != "event_id"]
            events_df = events_df[cols]

        if save:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            events_df.to_parquet(self.output_file, index=False)
        return events_df

    def process_events(self) -> Dict[str, Any]:
        """
        Runs event detection on input_file and returns summary metadata dictionary.
        """
        logger.info("Running pollution event detection engine (leakage-free baseline)...")
        events_df = self.detect_events()
        summary = {
            "status": "success",
            "events_detected": len(events_df),
            "stations_affected": int(events_df["station"].nunique()) if not events_df.empty else 0,
            "max_event_pm25": float(events_df["peak_pm25"].max()) if not events_df.empty else 0.0,
            "algorithm_version": ALGORITHM_VERSION,
            "output_file": str(self.output_file),
        }
        logger.info(f"Event detection complete. Detected {len(events_df)} pollution events.")
        return summary
