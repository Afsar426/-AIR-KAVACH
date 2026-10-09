import math
import pandas as pd
from pathlib import Path


# =========================================================
# AIR KAVACH - WIND ALIGNMENT ANALYSIS
# =========================================================

DISTANCE_FILE = Path(
    "data/features/sensor_factory_distances.parquet"
)

OUTPUT_FILE = Path(
    "data/features/sensor_factory_wind_alignment.parquet"
)


# ---------------------------------------------------------
# Sensor wind data
# ---------------------------------------------------------
#
# These values are representative of the wind observations
# available from OpenAQ for the corresponding stations.
#
# For the final event-level attribution model, these values
# will be replaced by timestamp-aligned wind observations.
# ---------------------------------------------------------

WIND_DATA = {
    "Residency": {
        "wind_direction_deg": 270.0,
        "wind_speed_mps": 2.5,
    },

    "Regional Park": {
        "wind_direction_deg": 270.0,
        "wind_speed_mps": 2.5,
    },

    "Airport": {
        "wind_direction_deg": 270.0,
        "wind_speed_mps": 2.5,
    },

    "Maguda": {
        "wind_direction_deg": 270.0,
        "wind_speed_mps": 2.5,
    },
}


# ---------------------------------------------------------
# Bearing calculation
# ---------------------------------------------------------

def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    Calculate bearing from point 1 to point 2.

    Bearing:
        0   = North
        90  = East
        180 = South
        270 = West
    """

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    delta_lon = math.radians(lon2 - lon1)

    x = math.sin(delta_lon) * math.cos(lat2)

    y = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1)
        * math.cos(lat2)
        * math.cos(delta_lon)
    )

    bearing = math.degrees(
        math.atan2(x, y)
    )

    return (bearing + 360) % 360


# ---------------------------------------------------------
# Angular difference
# ---------------------------------------------------------

def angular_difference(angle1, angle2):
    """
    Smallest angular difference between two directions.
    """

    difference = abs(angle1 - angle2)

    return min(
        difference,
        360 - difference,
    )


# ---------------------------------------------------------
# Wind alignment score
# ---------------------------------------------------------

def calculate_upwind_score(
    factory_to_sensor_bearing,
    wind_direction,
):
    """
    Wind direction is the direction FROM which the wind comes.

    Therefore, if the factory lies in the wind-source
    direction from the sensor, the factory is upwind.

    Score:
        1.0  = perfectly aligned upwind
        0.0  = crosswind / perpendicular
       -1.0  = directly downwind
    """

    difference = angular_difference(
        factory_to_sensor_bearing,
        wind_direction,
    )

    score = math.cos(
        math.radians(difference)
    )

    return score


# ---------------------------------------------------------
# Load distance data
# ---------------------------------------------------------

print("=" * 70)
print("AIR KAVACH - WIND ALIGNMENT ANALYSIS")
print("=" * 70)

df = pd.read_parquet(DISTANCE_FILE)

print(f"Sensor/factory pairs loaded: {len(df)}")


# ---------------------------------------------------------
# Calculate wind alignment
# ---------------------------------------------------------

results = []

for _, row in df.iterrows():

    sensor = row["sensor"]

    sensor_lat = row["sensor_latitude"]
    sensor_lon = row["sensor_longitude"]

    factory_lat = row["factory_latitude"]
    factory_lon = row["factory_longitude"]

    wind_direction = WIND_DATA[sensor]["wind_direction_deg"]
    wind_speed = WIND_DATA[sensor]["wind_speed_mps"]

    # Bearing from sensor → factory
    sensor_to_factory_bearing = calculate_bearing(
        sensor_lat,
        sensor_lon,
        factory_lat,
        factory_lon,
    )

    # Factory → sensor direction
    factory_to_sensor_bearing = (
        sensor_to_factory_bearing + 180
    ) % 360

    alignment_score = calculate_upwind_score(
        factory_to_sensor_bearing,
        wind_direction,
    )

    results.append(
        {
            **row.to_dict(),

            "wind_direction_deg": wind_direction,
            "wind_speed_mps": wind_speed,

            "sensor_to_factory_bearing_deg":
                round(sensor_to_factory_bearing, 2),

            "factory_to_sensor_bearing_deg":
                round(factory_to_sensor_bearing, 2),

            "wind_alignment_score":
                round(alignment_score, 4),
        }
    )


result = pd.DataFrame(results)


# ---------------------------------------------------------
# Wind classification
# ---------------------------------------------------------

def classify_alignment(score):

    if score >= 0.75:
        return "strong_upwind"

    if score >= 0.25:
        return "upwind"

    if score > -0.25:
        return "crosswind"

    if score > -0.75:
        return "downwind"

    return "strong_downwind"


result["wind_alignment"] = (
    result["wind_alignment_score"]
    .apply(classify_alignment)
)


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
# Display results
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("WIND ALIGNMENT SUMMARY")
print("=" * 70)

print(
    result["wind_alignment"]
    .value_counts()
    .to_string()
)


for sensor in result["sensor"].unique():

    print(f"\n--- {sensor} ---")

    top = (
        result[result["sensor"] == sensor]
        .sort_values(
            "wind_alignment_score",
            ascending=False,
        )
        .head(5)
    )

    print(
        top[
            [
                "factory_name",
                "distance_km",
                "wind_direction_deg",
                "wind_alignment_score",
                "wind_alignment",
            ]
        ].to_string(index=False)
    )


print("\n" + "=" * 70)
print("WIND ALIGNMENT COMPLETED")
print("=" * 70)

print("Saved to:")
print(OUTPUT_FILE)