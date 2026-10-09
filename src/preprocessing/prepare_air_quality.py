import os
import pandas as pd


RAW_DIR = "data/raw/air_quality/openaq"
OUTPUT_DIR = "data/processed/air_quality"

os.makedirs(OUTPUT_DIR, exist_ok=True)


FILES = {
    "Residency": {
        "file": "residency_pm25.csv",
        "sensor_id": 12238477,
    },
    "Regional Park": {
        "file": "regional_park_pm25.csv",
        "sensor_id": 12238486,
    },
    "Airport": {
        "file": "airport_pm25.csv",
        "sensor_id": 12238495,
    },
    "Maguda": {
        "file": "maguda_pm25.csv",
        "sensor_id": 12815122,
    },
}


def process_station(station_name, info):

    path = os.path.join(
        RAW_DIR,
        info["file"]
    )

    print("=" * 70)
    print(f"Processing: {station_name}")

    df = pd.read_csv(path)

    # -----------------------------------------------------
    # Select useful columns
    # -----------------------------------------------------

    df = df[
        [
            "value",
            "parameter.name",
            "parameter.units",
            "period.datetimeFrom.utc",
        ]
    ].copy()

    # -----------------------------------------------------
    # Rename columns
    # -----------------------------------------------------

    df.rename(
        columns={
            "value": "value",
            "parameter.name": "parameter",
            "parameter.units": "unit",
            "period.datetimeFrom.utc": "timestamp",
        },
        inplace=True
    )

    # -----------------------------------------------------
    # Add station information
    # -----------------------------------------------------

    df["station"] = station_name
    df["sensor_id"] = info["sensor_id"]

    # -----------------------------------------------------
    # Convert timestamp
    # -----------------------------------------------------

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True
    )

    # -----------------------------------------------------
    # Convert PM2.5 value
    # -----------------------------------------------------

    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce"
    )

    # -----------------------------------------------------
    # Remove invalid records
    # -----------------------------------------------------

    df = df.dropna(
        subset=[
            "timestamp",
            "value"
        ]
    )

    df = df[df["value"] >= 0]

    # -----------------------------------------------------
    # Remove duplicates
    # -----------------------------------------------------

    df = df.drop_duplicates(
        subset=[
            "station",
            "timestamp",
            "parameter"
        ]
    )

    # -----------------------------------------------------
    # Sort
    # -----------------------------------------------------

    df = df.sort_values(
        "timestamp"
    )

    # -----------------------------------------------------
    # Final column order
    # -----------------------------------------------------

    df = df[
        [
            "station",
            "sensor_id",
            "timestamp",
            "parameter",
            "value",
            "unit",
        ]
    ]

    print("Clean rows:", len(df))
    print("Start:", df["timestamp"].min())
    print("End:", df["timestamp"].max())

    return df


# ---------------------------------------------------------
# Process all stations
# ---------------------------------------------------------

all_data = []

for station_name, info in FILES.items():

    df = process_station(
        station_name,
        info
    )

    all_data.append(df)


# ---------------------------------------------------------
# Combine
# ---------------------------------------------------------

combined = pd.concat(
    all_data,
    ignore_index=True
)

combined = combined.sort_values(
    [
        "timestamp",
        "station"
    ]
)


# ---------------------------------------------------------
# Save Parquet
# ---------------------------------------------------------

output_path = os.path.join(
    OUTPUT_DIR,
    "air_quality.parquet"
)

combined.to_parquet(
    output_path,
    index=False
)


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("AIR KAVACH - PROCESSED AIR QUALITY DATA")
print("=" * 70)

print("Total rows:", len(combined))

print("\nRows by station:")

print(
    combined.groupby("station")
    .size()
    .to_string()
)

print("\nParameters:")

print(
    combined["parameter"]
    .value_counts()
    .to_string()
)

print("\nSaved to:")
print(output_path)

print("\nProcessing completed.")