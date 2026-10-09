import os
import pandas as pd
import numpy as np


INPUT_FILE = "data/processed/air_quality/air_quality.parquet"
OUTPUT_DIR = "data/processed/events"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

ROLLING_WINDOW = 24 * 4
# 24 hours × 4 readings/hour = 96 readings

MIN_EVENT_DURATION = 4
# Minimum 4 consecutive 15-minute readings
# = 1 hour


Z_THRESHOLD = 2.0
# Reading must be approximately 2 standard deviations
# above the rolling baseline


# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------

df = pd.read_parquet(INPUT_FILE)

print("=" * 70)
print("AIR KAVACH - POLLUTION EVENT DETECTION")
print("=" * 70)

print("Input rows:", len(df))


# ---------------------------------------------------------
# Prepare timestamp
# ---------------------------------------------------------

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    utc=True
)

df = df.sort_values(
    [
        "station",
        "timestamp"
    ]
)


# ---------------------------------------------------------
# Calculate rolling baseline
# ---------------------------------------------------------

df["rolling_mean"] = (
    df.groupby("station")["value"]
    .transform(
        lambda x: x.rolling(
            ROLLING_WINDOW,
            min_periods=24
        ).mean()
    )
)

df["rolling_std"] = (
    df.groupby("station")["value"]
    .transform(
        lambda x: x.rolling(
            ROLLING_WINDOW,
            min_periods=24
        ).std()
    )
)


# ---------------------------------------------------------
# Calculate anomaly score
# ---------------------------------------------------------

df["z_score"] = (
    (df["value"] - df["rolling_mean"])
    /
    df["rolling_std"].replace(0, np.nan)
)


# ---------------------------------------------------------
# Detect pollution spike
# ---------------------------------------------------------

df["is_spike"] = (
    (df["z_score"] >= Z_THRESHOLD)
    &
    (df["value"] > df["rolling_mean"])
)


# ---------------------------------------------------------
# Group consecutive spike readings
# ---------------------------------------------------------

df["spike_change"] = (
    df.groupby("station")["is_spike"]
    .transform(
        lambda x: x.ne(x.shift()).cumsum()
    )
)


spikes = df[
    df["is_spike"]
].copy()


if spikes.empty:

    print("\nNo pollution events detected.")

    output_file = os.path.join(
        OUTPUT_DIR,
        "pollution_events.parquet"
    )

    pd.DataFrame().to_parquet(
        output_file,
        index=False
    )

    raise SystemExit


# ---------------------------------------------------------
# Build event groups
# ---------------------------------------------------------

events = []

event_id = 1


for (station, group_id), group in spikes.groupby(
    [
        "station",
        "spike_change"
    ]
):

    # Require minimum duration
    if len(group) < MIN_EVENT_DURATION:
        continue

    start_time = group["timestamp"].min()
    end_time = group["timestamp"].max()

    peak_row = group.loc[
        group["value"].idxmax()
    ]

    events.append(
        {
            "event_id": f"EVT-{event_id:04d}",

            "station": station,

            "start_time": start_time,

            "end_time": end_time,

            "duration_minutes": (
                end_time - start_time
            ).total_seconds() / 60 + 15,

            "peak_pm25": peak_row["value"],

            "peak_time": peak_row["timestamp"],

            "peak_z_score": peak_row["z_score"],

            "mean_pm25": group["value"].mean(),

            "baseline_mean": group["rolling_mean"].mean(),

            "max_z_score": group["z_score"].max(),

            "readings": len(group),
        }
    )

    event_id += 1


# ---------------------------------------------------------
# Convert events to DataFrame
# ---------------------------------------------------------

events_df = pd.DataFrame(events)


# ---------------------------------------------------------
# Sort by severity
# ---------------------------------------------------------

if not events_df.empty:

    events_df = events_df.sort_values(
        "peak_pm25",
        ascending=False
    ).reset_index(drop=True)


# ---------------------------------------------------------
# Save events
# ---------------------------------------------------------

output_file = os.path.join(
    OUTPUT_DIR,
    "pollution_events.parquet"
)

events_df.to_parquet(
    output_file,
    index=False
)


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

print("\nPollution events detected:", len(events_df))

if not events_df.empty:

    print("\nTop events:")

    print(
        events_df[
            [
                "event_id",
                "station",
                "start_time",
                "end_time",
                "peak_pm25",
                "max_z_score",
                "duration_minutes",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

print("\nSaved to:")
print(output_file)

print("\nEvent detection completed.")