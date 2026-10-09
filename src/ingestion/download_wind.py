import os
import requests
import pandas as pd

from dotenv import load_dotenv
from pathlib import Path


# =========================================================
# AIR KAVACH - ACTUAL OPENAQ WIND DATA
# =========================================================

load_dotenv()

API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    raise ValueError("OPENAQ_API_KEY not found in .env")


BASE_URL = "https://api.openaq.org/v3/sensors"

OUTPUT_DIR = Path(
    "data/raw/weather/openaq"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ---------------------------------------------------------
# September 2026
# ---------------------------------------------------------

DATETIME_FROM = "2026-09-01T00:00:00Z"
DATETIME_TO = "2026-10-01T00:00:00Z"


# ---------------------------------------------------------
# Actual OpenAQ wind sensors
# ---------------------------------------------------------

WIND_SENSORS = {
    "Residency": {
        "wind_direction": 14341605,
        "wind_speed": 14341606,
    },

    "Regional Park": {
        "wind_direction": 14341608,
        "wind_speed": 14341609,
    },

    "Airport": {
        "wind_direction": 14341613,
        "wind_speed": 14341614,
    },

    "Maguda": {
        "wind_direction": 14341611,
        "wind_speed": None,
    },
}


HEADERS = {
    "X-API-Key": API_KEY,
    "Accept": "application/json",
}


# ---------------------------------------------------------
# Download one sensor
# ---------------------------------------------------------

def download_sensor(sensor_id):

    url = f"{BASE_URL}/{sensor_id}/measurements"

    params = {
        "datetime_from": DATETIME_FROM,
        "datetime_to": DATETIME_TO,
        "limit": 1000,
        "page": 1,
    }

    all_rows = []

    while True:

        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=60,
        )

        print(
            f"Sensor {sensor_id} | "
            f"Page {params['page']} | "
            f"Status {response.status_code}"
        )

        if not response.ok:
            print(response.text[:1000])
            break

        data = response.json()

        rows = data.get("results", [])

        if not rows:
            break

        all_rows.extend(rows)

        meta = data.get("meta", {})

        found = meta.get("found")

        if isinstance(found, str):
            try:
                found = int(
                    found.replace(">", "")
                )
            except ValueError:
                found = None

        if found is not None:
            if len(all_rows) >= found:
                break

        if len(rows) < 1000:
            break

        params["page"] += 1

    return all_rows


# ---------------------------------------------------------
# Main download
# ---------------------------------------------------------

print("=" * 70)
print("AIR KAVACH - ACTUAL WIND DATA DOWNLOAD")
print("=" * 70)

for station, sensors in WIND_SENSORS.items():

    print("\n" + "-" * 70)
    print(f"Station: {station}")
    print("-" * 70)

    # -----------------------------------------------------
    # Wind direction
    # -----------------------------------------------------

    direction_sensor = sensors["wind_direction"]

    direction_rows = download_sensor(
        direction_sensor
    )

    if direction_rows:

        direction_df = pd.DataFrame(
            direction_rows
        )

        direction_file = (
            OUTPUT_DIR
            / f"{station.lower().replace(' ', '_')}_wind_direction.csv"
        )

        direction_df.to_csv(
            direction_file,
            index=False,
        )

        print(
            f"Wind direction rows: "
            f"{len(direction_df)}"
        )

        print(
            f"Saved: {direction_file}"
        )

    else:

        print(
            "No wind direction data received."
        )

    # -----------------------------------------------------
    # Wind speed
    # -----------------------------------------------------

    speed_sensor = sensors["wind_speed"]

    if speed_sensor is None:

        print(
            "Wind speed sensor not configured "
            "for this station."
        )

        continue

    speed_rows = download_sensor(
        speed_sensor
    )

    if speed_rows:

        speed_df = pd.DataFrame(
            speed_rows
        )

        speed_file = (
            OUTPUT_DIR
            / f"{station.lower().replace(' ', '_')}_wind_speed.csv"
        )

        speed_df.to_csv(
            speed_file,
            index=False,
        )

        print(
            f"Wind speed rows: "
            f"{len(speed_df)}"
        )

        print(
            f"Saved: {speed_file}"
        )

    else:

        print(
            "No wind speed data received."
        )


print("\n" + "=" * 70)
print("WIND DATA DOWNLOAD COMPLETED")
print("=" * 70)
