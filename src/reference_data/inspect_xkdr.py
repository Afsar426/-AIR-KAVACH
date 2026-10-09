"""
AIR KAVACH - XKDR India Air Quality Database Inspector

Purpose:
1. Check API availability.
2. Inspect published database metadata.
3. Find available Indore/Madhya Pradesh monitoring stations.
4. Save the inspection results for reproducibility.

This script inspects availability. It does not claim that any
factory has been independently identified as a pollution source.
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "generated"
    / "reference_data"
)

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "reference" / "xkdr"

BASE_URL = "https://airquality.xkdr.org"

# Public demo key documented by XKDR.
# It has limited access; use your own key for broader archive access.
DEMO_API_KEY = "aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"


def get_api_key():
    load_dotenv(PROJECT_ROOT / ".env")

    return (
        os.getenv("XKDR_API_KEY")
        or DEMO_API_KEY
    )


def fetch_json(endpoint, api_key, params=None):
    url = f"{BASE_URL}{endpoint}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    response = requests.get(
        url,
        headers=headers,
        params=params or {},
        timeout=45,
    )

    response.raise_for_status()

    return response


def save_json(filename, content):
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    path = RAW_DIR / filename

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            content,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    return path


def extract_results(payload):
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        results = payload.get("results")

        if isinstance(results, list):
            return results

        data = payload.get("data")

        if isinstance(data, list):
            return data

    return []


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    api_key = get_api_key()

    print("=" * 65)
    print("AIR KAVACH - XKDR REFERENCE DATA INSPECTION")
    print("=" * 65)

    session_info = {
        "source": "India Air Quality Database - XKDR Forum",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE_URL,
        "credential_type": (
            "custom_api_key"
            if os.getenv("XKDR_API_KEY")
            else "public_demo_key"
        ),
    }

    # 1. Inspect published metadata.
    print("\n[1/3] Checking published database metadata...")

    try:
        meta_response = fetch_json(
            "/v1/meta",
            api_key,
        )

        meta = meta_response.json()

        save_json("metadata.json", meta)

        print("Metadata request: SUCCESS")
        print("HTTP status:", meta_response.status_code)

        if isinstance(meta, dict):
            for key, value in meta.items():
                if key in {"schema", "columns"}:
                    print(f"{key}: available")
                else:
                    print(f"{key}: {str(value)[:300]}")

    except requests.RequestException as error:
        print("Metadata request: FAILED")
        print("Reason:", error)
        print(
            "\nCheck internet access and API credentials. "
            "No dataset availability conclusion can be made."
        )
        sys.exit(1)

    # 2. Query station registry for Indore.
    print("\n[2/3] Searching station registry for Indore...")

    station_records = []

    try:
        response = fetch_json(
            "/v1/stations",
            api_key,
            params={
                "city": "Indore",
                "format": "json",
            },
        )

        station_payload = response.json()

        save_json("indore_stations_response.json", station_payload)

        station_records = extract_results(station_payload)

        print("Indore station request: SUCCESS")
        print("HTTP status:", response.status_code)
        print("Returned records:", len(station_records))

    except requests.RequestException as error:
        print("Indore station request: FAILED")
        print("Reason:", error)

    # If the city filter returns no results, inspect MP station registry.
    if not station_records:
        print(
            "\nNo records returned for the exact city filter. "
            "Trying the Madhya Pradesh state filter..."
        )

        try:
            response = fetch_json(
                "/v1/stations",
                api_key,
                params={
                    "state": "Madhya Pradesh",
                    "format": "json",
                },
            )

            state_payload = response.json()

            save_json(
                "madhya_pradesh_stations_response.json",
                state_payload,
            )

            station_records = extract_results(state_payload)

            print("State station request: SUCCESS")
            print("Returned records:", len(station_records))

        except requests.RequestException as error:
            print("State station request: FAILED")
            print("Reason:", error)

    # 3. Save station records.
    if station_records:
        csv_path = OUTPUT_DIR / "xkdr_indore_stations.csv"

        columns = sorted(
            {
                key
                for record in station_records
                if isinstance(record, dict)
                for key in record.keys()
            }
        )

        with csv_path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=columns,
                extrasaction="ignore",
            )

            writer.writeheader()

            for record in station_records:
                writer.writerow(
                    {
                        key: json.dumps(value, ensure_ascii=False)
                        if isinstance(value, (list, dict))
                        else value
                        for key, value in record.items()
                    }
                )

        print("\nStation records saved:", csv_path)

        print("\nStation preview:")

        for station in station_records[:10]:
            print(
                "-",
                station.get("station_name", station.get("name", "Unknown")),
                "|",
                station.get("city_name", station.get("city", "Unknown")),
                "|",
                station.get("station_id", station.get("id", "Unknown")),
            )

    else:
        print(
            "\nNo station records were extracted. "
            "Inspect the saved raw response and API schema before retrying."
        )

    session_info["station_records_returned"] = len(station_records)

    save_json("inspection_summary.json", session_info)

    print("\n[3/3] Inspection completed.")
    print("Raw API responses:", RAW_DIR)
    print("Inspection summary:", RAW_DIR / "inspection_summary.json")

    print(
        "\nIMPORTANT: Station discovery does not prove that "
        "historical measurements overlap with AIR KAVACH events."
    )


if __name__ == "__main__":
    main()