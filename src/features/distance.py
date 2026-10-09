import math
import pandas as pd
from pathlib import Path


# =========================================================
# AIR KAVACH - SENSOR TO FACTORY DISTANCE
# =========================================================

FACTORY_FILE = Path(
    "data/processed/factories/factories_clean.parquet"
)

OUTPUT_FILE = Path(
    "data/features/sensor_factory_distances.parquet"
)


# ---------------------------------------------------------
# Sensor locations
# ---------------------------------------------------------

SENSORS = {
    "Residency": {
        "latitude": 22.7084,
        "longitude": 75.8815,
    },
    "Regional Park": {
        "latitude": 22.6780,
        "longitude": 75.8559,
    },
    "Airport": {
        "latitude": 22.7289,
        "longitude": 75.8076,
    },
    "Maguda": {
        "latitude": 22.7524,
        "longitude": 75.8872,
    },
}


# ---------------------------------------------------------
# Haversine distance
# ---------------------------------------------------------

def haversine_km(lat1, lon1, lat2, lon2):
    """
    Calculate great-circle distance between
    two latitude/longitude coordinates.
    """

    earth_radius_km = 6371.0

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    return earth_radius_km * c


# ---------------------------------------------------------
# Load factories
# ---------------------------------------------------------

print("=" * 70)
print("AIR KAVACH - SENSOR / FACTORY DISTANCE ANALYSIS")
print("=" * 70)

factories = pd.read_parquet(FACTORY_FILE)

print(f"Factories loaded: {len(factories)}")


# ---------------------------------------------------------
# Keep only attribution candidates
# ---------------------------------------------------------

factories = factories[
    factories["source_candidate"] == True
].copy()

print(f"Source candidates: {len(factories)}")


# ---------------------------------------------------------
# Calculate every sensor → factory distance
# ---------------------------------------------------------

records = []

for sensor_name, sensor in SENSORS.items():

    for _, factory in factories.iterrows():

        distance = haversine_km(
            sensor["latitude"],
            sensor["longitude"],
            factory["latitude"],
            factory["longitude"],
        )

        records.append(
            {
                "sensor": sensor_name,
                "sensor_latitude": sensor["latitude"],
                "sensor_longitude": sensor["longitude"],
                "factory_id": factory["factory_id"],
                "factory_name": factory["factory_name"],
                "facility_category": factory["facility_category"],
                "factory_latitude": factory["latitude"],
                "factory_longitude": factory["longitude"],
                "distance_km": round(distance, 3),
            }
        )


result = pd.DataFrame(records)


# ---------------------------------------------------------
# Sort
# ---------------------------------------------------------

result = result.sort_values(
    by=["sensor", "distance_km"]
).reset_index(drop=True)


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

result.to_parquet(
    OUTPUT_FILE,
    index=False,
)


# ---------------------------------------------------------
# Display nearest factories
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("NEAREST INDUSTRIAL CANDIDATES")
print("=" * 70)

for sensor_name in SENSORS:

    print(f"\n--- {sensor_name} ---")

    nearest = result[
        result["sensor"] == sensor_name
    ].head(5)

    print(
        nearest[
            [
                "factory_name",
                "facility_category",
                "distance_km",
            ]
        ].to_string(index=False)
    )


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("DISTANCE ANALYSIS COMPLETED")
print("=" * 70)

print(f"Total sensor/factory pairs: {len(result)}")

print("\nSaved to:")
print(OUTPUT_FILE)
