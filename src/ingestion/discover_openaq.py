import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAQ_API_KEY")

if not api_key:
    raise ValueError("OPENAQ_API_KEY not found in .env")

url = "https://api.openaq.org/v3/locations"

headers = {
    "X-API-Key": api_key
}

# Indore approximate center
latitude = 22.7196
longitude = 75.8577

params = {
    "coordinates": f"{latitude},{longitude}",
    "radius": 25000,
    "limit": 100
}

response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=30
)

print("Status Code:", response.status_code)

if not response.ok:
    print("OpenAQ request failed:")
    print(response.text)
    raise SystemExit

data = response.json()

locations = data.get("results", [])

print(f"\nFound {len(locations)} monitoring locations.\n")

for location in locations:
    print("-" * 60)

    print("ID:", location.get("id"))
    print("Name:", location.get("name"))

    coordinates = location.get("coordinates", {})
    print(
        "Coordinates:",
        coordinates.get("latitude"),
        coordinates.get("longitude")
    )

    print("Country:", location.get("country", {}).get("name"))

    sensors = location.get("sensors", [])

    print("Sensors:")

    for sensor in sensors:
        parameter = sensor.get("parameter", {})
        print(
            f"  Sensor {sensor.get('id')} -> "
            f"{parameter.get('name')} ({parameter.get('units')})"
        )

print("\nDiscovery completed.")