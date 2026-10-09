import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAQ_API_KEY")

if not api_key:
    raise ValueError("OPENAQ_API_KEY not found in .env")

headers = {
    "X-API-Key": api_key
}

# Important AIR KAVACH sensors
sensors = {
    # Pithampur
    "Pithampur PM2.5": 14891,
    "Pithampur PM10": 14856,
    "Pithampur NO2": 14836,
    "Pithampur SO2": 14903,
    "Pithampur Wind Direction": 14340723,
    "Pithampur Wind Speed": 14340724,

    # Residency Area
    "Residency PM2.5": 12238477,
    "Residency Wind Direction": 14341605,
    "Residency Wind Speed": 14341606,

    # Regional Park
    "Regional Park PM2.5": 12238486,
    "Regional Park Wind Direction": 14341608,
    "Regional Park Wind Speed": 14341609,

    # Airport
    "Airport PM2.5": 12238495,
    "Airport Wind Direction": 14341613,
    "Airport Wind Speed": 14341614,

    # Maguda Nagar
    "Maguda PM2.5": 12815122,
    "Maguda Wind Direction": 14341611,
}

for name, sensor_id in sensors.items():

    url = f"https://api.openaq.org/v3/sensors/{sensor_id}"

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    print("=" * 70)
    print(name)
    print("Sensor ID:", sensor_id)
    print("Status:", response.status_code)

    if response.ok:

        data = response.json()

        results = data.get("results", [])

        if not results:
            print("No sensor information returned.")
            continue

        # OpenAQ returns results as a list
        sensor = results[0]

        parameter = sensor.get("parameter", {})

        print("Parameter:", parameter.get("name"))
        print("Units:", parameter.get("units"))

        if sensor.get("datetimeFirst"):
            print("First data:", sensor["datetimeFirst"])

        if sensor.get("datetimeLast"):
            print("Last data:", sensor["datetimeLast"])

    else:
        print("ERROR:")
        print(response.text)

print("=" * 70)
print("Data availability check completed.")