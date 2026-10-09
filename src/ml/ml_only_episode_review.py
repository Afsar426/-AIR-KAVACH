"""
AIR KAVACH — ML-Only Elevated Episode Review

Purpose:
- Group elevated ML-only observations into episodes.
- Summarize start/end time, duration, peak and mean PM2.5.
- Check overlap with existing statistical events.
- Preserve wind information as supporting context.

Run from project root:
    python src/ml/ml_only_episode_review.py

Input:
    reports/generated/ml_only_elevated_review.csv

Outputs:
    reports/generated/ml_only_elevated_episodes.csv
    reports/generated/ml_only_elevated_episode_report.json

Note:
This is exploratory analysis, not ground-truth validation.
"""

from pathlib import Path
import json
import pandas as pd

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

ROOT = Path.cwd()

INPUT_FILE = ROOT / "reports/generated/ml_only_elevated_review.csv"
OUTPUT_DIR = ROOT / "reports/generated"

# A new episode begins when the gap between consecutive
# observations exceeds this threshold.
MAX_GAP_MINUTES = 30

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

def load_data():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}\n"
            "Run ml_only_elevated_review.py first."
        )

    df = pd.read_csv(INPUT_FILE)

    required_columns = [
        "station",
        "timestamp",
        "value",
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
        errors="coerce",
    )

    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce",
    )

    df = df.dropna(
        subset=["station", "timestamp", "value"]
    )

    # This input should already contain ML-only elevated
    # observations, but filter defensively.
    df = df[df["value"] >= 35].copy()

    df = df.sort_values(
        ["station", "timestamp"]
    ).reset_index(drop=True)

    return df


# --------------------------------------------------
# GROUP OBSERVATIONS INTO EPISODES
# --------------------------------------------------

def create_episodes(df):
    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    time_gap = (
        df.groupby("station")["timestamp"]
        .diff()
        .dt.total_seconds()
        .div(60)
    )

    # Start a new episode when:
    # 1. This is the first observation for a station.
    # 2. The gap is greater than MAX_GAP_MINUTES.
    new_episode = (
        time_gap.isna()
        | (time_gap > MAX_GAP_MINUTES)
    )

    df["episode_number"] = (
        new_episode.groupby(df["station"]).cumsum()
    )

    episodes = []

    for (station, episode_number), group in df.groupby(
        ["station", "episode_number"],
        sort=True,
    ):
        group = group.sort_values("timestamp")

        start = group["timestamp"].min()
        end = group["timestamp"].max()

        peak_row = group.loc[group["value"].idxmax()]

        # Duration is based on first and last observed readings.
        # It is not an estimate of the full physical pollution period.
        duration_minutes = (
            end - start
        ).total_seconds() / 60

        episode = {
            "episode_id": (
                f"ML-{str(station).upper().replace(' ', '-')}-"
                f"{int(episode_number):03d}"
            ),
            "station": station,
            "start_time_utc": start.isoformat(),
            "end_time_utc": end.isoformat(),
            "duration_minutes": round(
                duration_minutes, 2
            ),
            "observation_count": int(len(group)),
            "mean_pm25": round(
                float(group["value"].mean()), 3
            ),
            "peak_pm25": round(
                float(group["value"].max()), 3
            ),
            "peak_timestamp_utc": (
                peak_row["timestamp"].isoformat()
            ),
            "min_pm25": round(
                float(group["value"].min()), 3
            ),
            "grouping_gap_minutes": MAX_GAP_MINUTES,
        }

        # Include available model-score information.
        if "anomaly_score" in group.columns:
            scores = pd.to_numeric(
                group["anomaly_score"],
                errors="coerce",
            ).dropna()

            episode["mean_anomaly_score"] = (
                round(float(scores.mean()), 6)
                if len(scores) else None
            )

        # Wind direction and speed are context only.
        for col in [
            "wind_direction_deg",
            "wind_speed_mps",
        ]:
            if col in group.columns:
                vals = pd.to_numeric(
                    group[col],
                    errors="coerce",
                ).dropna()

                episode[f"{col}_mean"] = (
                    round(float(vals.mean()), 3)
                    if len(vals) else None
                )

        # Existing event-overlap flag comes from the
        # earlier review report.
        if "event_overlap" in group.columns:
            overlap = (
                group["event_overlap"]
                .astype(str)
                .str.lower()
                .isin(["true", "1", "yes"])
            )

            episode["overlaps_existing_event"] = bool(
                overlap.any()
            )
        else:
            episode["overlaps_existing_event"] = None

        if "overlapping_event_ids" in group.columns:
            ids = (
                group["overlapping_event_ids"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            unique_ids = sorted({
                item
                for value in ids
                if value
                for item in value.split(";")
                if item.strip()
            })

            episode["overlapping_event_ids"] = (
                ";".join(unique_ids)
            )

        episodes.append(episode)

    return pd.DataFrame(episodes)


# --------------------------------------------------
# SAVE REPORTS
# --------------------------------------------------

def main():
    print("=" * 65)
    print("AIR KAVACH — ML-ONLY ELEVATED EPISODE REVIEW")
    print("=" * 65)

    df = load_data()

    print(f"\nElevated ML-only observations loaded: {len(df)}")
    print(f"Stations found: {df['station'].nunique()}")

    episodes = create_episodes(df)

    csv_path = (
        OUTPUT_DIR / "ml_only_elevated_episodes.csv"
    )

    json_path = (
        OUTPUT_DIR / "ml_only_elevated_episode_report.json"
    )

    episodes.to_csv(csv_path, index=False)

    station_counts = {}

    if not episodes.empty:
        station_counts = {
            str(station): int(count)
            for station, count in (
                episodes.groupby("station").size().items()
            )
        }

    report = {
        "project": "AIR KAVACH",
        "analysis": "ML-only elevated observation episode grouping",
        "input_observation_count": int(len(df)),
        "episode_count": int(len(episodes)),
        "station_episode_counts": station_counts,
        "grouping_gap_minutes": MAX_GAP_MINUTES,
        "threshold_pm25": 35,
        "total_episode_observations": int(
            episodes["observation_count"].sum()
        ) if not episodes.empty else 0,
        "episodes_overlapping_existing_events": int(
            episodes["overlaps_existing_event"].sum()
        ) if (
            not episodes.empty
            and "overlaps_existing_event" in episodes.columns
            and episodes["overlaps_existing_event"].notna().any()
        ) else None,
        "interpretation": [
            "Episodes are grouped using station and timestamp continuity.",
            "The 30-minute grouping threshold is an operational choice, not a validated physical boundary.",
            "Episode duration is the interval between first and last observed readings.",
            "ML-only means the ML detector flagged the observation while the statistical baseline did not.",
            "Episodes are not confirmed pollution incidents.",
            "Wind information is contextual evidence, not proof of industrial source causation.",
            "Existing-event overlap is not independent model validation."
        ],
        "outputs": [
            str(csv_path.relative_to(ROOT)),
            str(json_path.relative_to(ROOT)),
        ],
    }

    json_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"\nEpisodes created: {len(episodes)}")

    print("\nEpisodes by station:")
    if not episodes.empty:
        print(
            episodes.groupby("station")
            .size()
            .to_string()
        )
    else:
        print("No episodes found.")

    print("\nEpisode details:")

    if not episodes.empty:
        display_columns = [
            "episode_id",
            "station",
            "start_time_utc",
            "end_time_utc",
            "duration_minutes",
            "observation_count",
            "mean_pm25",
            "peak_pm25",
        ]

        print(
            episodes[display_columns]
            .to_string(index=False)
        )

    print("\nSaved reports:")
    print(csv_path)
    print(json_path)

    print(
        "\nNOTE: These are exploratory episode summaries, "
        "not confirmed pollution events or accuracy metrics."
    )


if __name__ == "__main__":
    main()