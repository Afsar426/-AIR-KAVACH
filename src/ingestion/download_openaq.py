import os
import requests
import pandas as pd
from dotenv import load_dotenv

# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------

load_dotenv()

API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    raise ValueError("OPENAQ_API_KEY not found in .env")


# ---------------------------------------------------------
# OpenAQ configuration
# ---------------------------------------------------------

BASE_URL = "https://api.openaq.org/v3/sensors"

HEADERS = {
    "X-API-Key": API_KEY
}


# ---------------------------------------------------------
# Test date range
# ---------------------------------------------------------

START_DATE = "2026-09-01T00:00:00Z"
END_DATE = "2026-10-01T00:00:00Z"


# ---------------------------------------------------------
# PM2.5 sensors
# ---------------------------------------------------------

SENSORS = {
    "Residency": 12238477,
    "Regional_Park": 12238486,
    "Airport": 12238495,
    "Maguda": 12815122,
}


# ---------------------------------------------------------
# Output directory
# ---------------------------------------------------------

OUTPUT_DIR = "data/raw/air_quality/openaq"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------
# Download sensor data
# ---------------------------------------------------------

def download_sensor(name, sensor_id):

    print("\n" + "=" * 70)
    print(f"Downloading: {name}")
    print(f"Sensor ID: {sensor_id}")

    url = f"{BASE_URL}/{sensor_id}/measurements"

    page = 1
    all_records = []

    while True:

        params = {
            "datetime_from": START_DATE,
            "datetime_to": END_DATE,
            "limit": 1000,
            "page": page
        }

        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=60
        )

        print(
            f"Page {page} | "
            f"Status: {response.status_code}"
        )

        # -------------------------------------------------
        # API error
        # -------------------------------------------------

        if not response.ok:

            print("OpenAQ API request failed.")
            print("Response:")
            print(response.text)

            break

        # -------------------------------------------------
        # Read JSON
        # -------------------------------------------------

        data = response.json()

        records = data.get("results", [])

        # -------------------------------------------------
        # No more records
        # -------------------------------------------------

        if not records:

            print("No more records available.")
            break

        # -------------------------------------------------
        # Add records
        # -------------------------------------------------

        all_records.extend(records)

        meta = data.get("meta", {})
        found = meta.get("found")

        print(
            f"Received: {len(records)} | "
            f"Collected: {len(all_records)} | "
            f"Available: {found}"
        )

        # -------------------------------------------------
        # Last page detection
        # -------------------------------------------------

        if len(records) < 1000:

            print("Last page reached.")
            break

        # -------------------------------------------------
        # Handle OpenAQ found value
        #
        # It can be:
        # 1000
        # ">1000"
        # None
        # -------------------------------------------------

        if found is not None:

            try:

                found_number = int(found)

                if len(all_records) >= found_number:

                    print("All available records collected.")
                    break

            except (ValueError, TypeError):

                # Example:
                # found = ">1000"
                #
                # Continue to next page.

                pass

        page += 1

    # -----------------------------------------------------
    # No data
    # -----------------------------------------------------

    if not all_records:

        print("No data found for this sensor.")
        return

    # -----------------------------------------------------
    # Convert JSON → DataFrame
    # -----------------------------------------------------

    df = pd.json_normalize(all_records)

    # -----------------------------------------------------
    # Save CSV
    # -----------------------------------------------------

    output_file = os.path.join(
        OUTPUT_DIR,
        f"{name.lower()}_pm25.csv"
    )

    df.to_csv(
        output_file,
        index=False
    )

    print(f"Saved: {output_file}")
    print(f"Rows: {len(df)}")


# ---------------------------------------------------------
# Download all sensors
# ---------------------------------------------------------

for name, sensor_id in SENSORS.items():

    download_sensor(
        name,
        sensor_id
    )


# ---------------------------------------------------------
# Finished
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("AIR KAVACH - OpenAQ PM2.5 download completed.")
print("=" * 70)