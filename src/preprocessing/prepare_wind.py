import ast
import pandas as pd
from pathlib import Path


# =========================================================
# AIR KAVACH - PREPARE UNIFIED WIND DATA
# =========================================================

INPUT_DIR = Path(
    "data/raw/weather/openaq"
)

OUTPUT_FILE = Path(
    "data/processed/weather/wind.parquet"
)


STATIONS = {
    "Residency": {
        "direction": "residency_wind_direction.csv",
        "speed": "residency_wind_speed.csv",
    },
    "Regional Park": {
        "direction": "regional_park_wind_direction.csv",
        "speed": "regional_park_wind_speed.csv",
    },
    "Airport": {
        "direction": "airport_wind_direction.csv",
        "speed": "airport_wind_speed.csv",
    },
    "Maguda": {
        "direction": "maguda_wind_direction.csv",
        "speed": None,
    },
}


# ---------------------------------------------------------
# Extract timestamp from OpenAQ period
# ---------------------------------------------------------

def extract_timestamp(period_text):

    try:
        period = ast.literal_eval(period_text)

        return period["datetimeFrom"]["utc"]

    except Exception:
        return None


# ---------------------------------------------------------
# Load direction
# ---------------------------------------------------------

def load_direction(filename):

    path = INPUT_DIR / filename

    df = pd.read_csv(path)

    df["timestamp"] = pd.to_datetime(
        df["period"].apply(extract_timestamp),
        utc=True,
        errors="coerce",
    )

    df["wind_direction_deg"] = pd.to_numeric(
        df["value"],
        errors="coerce",
    )

    return df[
        [
            "timestamp",
            "wind_direction_deg",
        ]
    ]


# ---------------------------------------------------------
# Load speed
# ---------------------------------------------------------

def load_speed(filename):

    path = INPUT_DIR / filename

    df = pd.read_csv(path)

    df["timestamp"] = pd.to_datetime(
        df["period"].apply(extract_timestamp),
        utc=True,
        errors="coerce",
    )

    df["wind_speed_mps"] = pd.to_numeric(
        df["value"],
        errors="coerce",
    )

    return df[
        [
            "timestamp",
            "wind_speed_mps",
        ]
    ]


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

print("=" * 70)
print("AIR KAVACH - UNIFIED WIND DATA PREPARATION")
print("=" * 70)


all_station_data = []


for station, files in STATIONS.items():

    print("\n" + "-" * 70)
    print(f"Processing: {station}")
    print("-" * 70)

    direction = load_direction(
        files["direction"]
    )

    print(
        f"Direction observations: "
        f"{len(direction)}"
    )

    if files["speed"] is not None:

        speed = load_speed(
            files["speed"]
        )

        print(
            f"Speed observations: "
            f"{len(speed)}"
        )

        merged = pd.merge(
            direction,
            speed,
            on="timestamp",
            how="outer",
        )

    else:

        merged = direction.copy()

        merged["wind_speed_mps"] = pd.NA

        print(
            "Wind speed: unavailable"
        )

    merged["station"] = station

    all_station_data.append(
        merged
    )


# ---------------------------------------------------------
# Combine stations
# ---------------------------------------------------------

wind = pd.concat(
    all_station_data,
    ignore_index=True,
)


# ---------------------------------------------------------
# Sort
# ---------------------------------------------------------

wind = wind.sort_values(
    ["station", "timestamp"]
).reset_index(drop=True)


# ---------------------------------------------------------
# Validation
# ---------------------------------------------------------

wind["wind_direction_deg"] = pd.to_numeric(
    wind["wind_direction_deg"],
    errors="coerce",
)

wind["wind_speed_mps"] = pd.to_numeric(
    wind["wind_speed_mps"],
    errors="coerce",
)


# Direction should be 0–360
invalid_direction = (
    wind["wind_direction_deg"].notna()
    & (
        (wind["wind_direction_deg"] < 0)
        | (wind["wind_direction_deg"] > 360)
    )
).sum()


# Speed cannot be negative
invalid_speed = (
    wind["wind_speed_mps"].notna()
    & (wind["wind_speed_mps"] < 0)
).sum()


print("\n" + "=" * 70)
print("VALIDATION")
print("=" * 70)

print(
    "Invalid wind directions:",
    invalid_direction,
)

print(
    "Invalid wind speeds:",
    invalid_speed,
)

print(
    "Missing timestamps:",
    wind["timestamp"].isna().sum(),
)


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

wind.to_parquet(
    OUTPUT_FILE,
    index=False,
)


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("UNIFIED WIND DATASET")
print("=" * 70)

print(
    f"Total observations: {len(wind)}"
)

print("\nObservations by station:")

print(
    wind.groupby("station")
    .size()
    .to_string()
)

print("\nColumns:")

print(
    wind.columns.tolist()
)

print("\nSample:")

print(
    wind.head(10).to_string(
        index=False
    )
)

print("\nSaved to:")
print(OUTPUT_FILE)

print("\nWind preparation completed.")