import math
import pandas as pd
from pathlib import Path

# =========================================================
# AIR KAVACH - POLLUTION EVENT + ACTUAL WIND ALIGNMENT
# =========================================================

EVENT_FILE = Path("data/processed/events/pollution_events.parquet")
WIND_FILE = Path("data/processed/weather/wind.parquet")
OUTPUT_FILE = Path("data/features/pollution_events_with_wind.parquet")


def circular_mean_degrees(values):
    values = pd.Series(values).dropna()
    if len(values) == 0:
        return None

    radians = values.apply(math.radians)
    sin_mean = math.sin(
        math.atan2(
            sum(math.sin(x) for x in radians),
            sum(math.cos(x) for x in radians),
        )
    )
    cos_mean = math.cos(
        math.atan2(
            sum(math.sin(x) for x in radians),
            sum(math.cos(x) for x in radians),
        )
    )
    angle = math.degrees(math.atan2(sin_mean, cos_mean))
    return angle % 360


class EventWindAligner:
    """Aligns detected pollution episodes with coincident surface meteorological wind vectors."""

    def __init__(self, event_file: Path = EVENT_FILE, wind_file: Path = WIND_FILE, output_file: Path = OUTPUT_FILE):
        self.event_file = event_file
        self.wind_file = wind_file
        self.output_file = output_file

    def run(self) -> pd.DataFrame:
        if not self.event_file.exists() or not self.wind_file.exists():
            return pd.DataFrame()

        events = pd.read_parquet(self.event_file)
        wind = pd.read_parquet(self.wind_file)

        events["start_time"] = pd.to_datetime(events["start_time"], utc=True)
        events["end_time"] = pd.to_datetime(events["end_time"], utc=True)
        wind["timestamp"] = pd.to_datetime(wind["timestamp"], utc=True)

        results = []
        for _, event in events.iterrows():
            station = event["station"]
            event_start = event["start_time"]
            event_end = event["end_time"]

            station_wind = wind[wind["station"] == station].copy()
            event_wind = station_wind[
                (station_wind["timestamp"] >= event_start) &
                (station_wind["timestamp"] <= event_end)
            ]

            # Support both wide schema ('wind_direction_deg', 'wind_speed_mps') and long schema ('parameter', 'value')
            if "parameter" in event_wind.columns and "value" in event_wind.columns:
                wind_dir_data = event_wind[
                    (event_wind["parameter"].isin(["wind_direction_10m", "wind_direction", "wind_direction_deg"])) &
                    (event_wind["value"].notna())
                ]["value"]
                wind_speed_data = event_wind[
                    (event_wind["parameter"].isin(["wind_speed_10m", "wind_speed", "wind_speed_mps"])) &
                    (event_wind["value"].notna())
                ]["value"]
            else:
                wind_dir_col = "wind_direction_deg" if "wind_direction_deg" in event_wind.columns else "wind_direction"
                wind_speed_col = "wind_speed_mps" if "wind_speed_mps" in event_wind.columns else "wind_speed"
                wind_dir_data = event_wind[wind_dir_col].dropna() if wind_dir_col in event_wind.columns else pd.Series(dtype=float)
                wind_speed_data = event_wind[wind_speed_col].dropna() if wind_speed_col in event_wind.columns else pd.Series(dtype=float)

            # Expected 15-minute intervals
            duration_minutes = (event_end - event_start).total_seconds() / 60.0
            expected_obs = max(1, round(duration_minutes / 15.0) + 1)
            actual_obs = len(wind_dir_data)
            coverage = min(1.0, actual_obs / expected_obs) if expected_obs > 0 else 0.0

            dir_mean = circular_mean_degrees(wind_dir_data)
            speed_mean = float(wind_speed_data.mean()) if len(wind_speed_data) > 0 and pd.notna(wind_speed_data.mean()) else None

            is_calm = bool(speed_mean is not None and speed_mean < 0.5)
            if coverage < 0.25 or dir_mean is None:
                match_status = "insufficient_weather"
            elif is_calm:
                match_status = "calm_wind"
            else:
                match_status = "matched_observed"

            res_row = dict(event)
            res_row.update({
                "wind_direction_mean_deg": dir_mean,
                "wind_speed_mean_mps": speed_mean,
                "wind_observations": actual_obs,
                "wind_coverage": coverage,
                "is_calm_wind": is_calm,
                "weather_match_status": match_status,
            })
            results.append(res_row)

        result_df = pd.DataFrame(results)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        result_df.to_parquet(self.output_file, index=False)
        return result_df


def align_events():
    aligner = EventWindAligner()
    return aligner.run()


if __name__ == "__main__":
    print("=" * 70)
    print("AIR KAVACH - EVENT / WIND ALIGNMENT")
    print("=" * 70)
    res = align_events()
    print(f"Events processed: {len(res)}")
    print(f"Saved to: {OUTPUT_FILE}")