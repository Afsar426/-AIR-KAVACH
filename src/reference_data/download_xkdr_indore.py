"""
AIR KAVACH - XKDR Historical Air Quality Downloader

Downloads daily air-quality aggregates for selected Indore stations.

Default demo access is limited to 2024 data.
The script checks the API response and records its coverage.

Daily aggregates are for historical analysis, not direct validation
of individual 15-minute pollution events.
"""

import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "reference" / "xkdr"
REPORT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "generated"
    / "reference_data"
)

BASE_URL = "https://airquality.xkdr.org"

DEMO_API_KEY = "aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"

STATIONS = {
    "site_5857": "Airport Area",
    "site_5248": "Chhoti Gwaltoli",
    "site_5856": "Maguda Nagar",
    "site_5855": "Regional Park",
    "site_5854": "Residency Area",
}

PARAMETERS = ["PM2.5", "PM10", "NO2", "SO2"]

START_DATE = "2024-01-01"
END_DATE = "2024-12-31"


def get_api_key():
    load_dotenv(PROJECT_ROOT / ".env")

    return (
        os.getenv("XKDR_API_KEY")
        or DEMO_API_KEY
    )


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    api_key = get_api_key()

    params = [
        ("station", station_id)
        for station_id in STATIONS
    ]

    params.extend(
        ("parameter", parameter)
        for parameter in PARAMETERS
    )

    params.extend([
        ("start", START_DATE),
        ("end", END_DATE),
        ("agg", "daily"),
        ("format", "csv"),
    ])

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/csv",
    }

    print("=" * 65)
    print("AIR KAVACH - XKDR HISTORICAL DATA DOWNLOAD")
    print("=" * 65)

    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Stations requested: {len(STATIONS)}")
    print(f"Pollutants requested: {', '.join(PARAMETERS)}")
    print("Aggregation: Daily")
    print("\nRequesting data...")

    response = requests.get(
        f"{BASE_URL}/v1/measurements",
        headers=headers,
        params=params,
        timeout=90,
    )

    print("HTTP status:", response.status_code)

    if response.status_code != 200:
        print("API request failed.")
        print("Response:", response.text[:1000])
        response.raise_for_status()

    truncated = response.headers.get(
        "X-Truncated",
        "unknown",
    )

    row_count_header = response.headers.get(
        "X-Row-Count",
        "unknown",
    )

    print("API row count header:", row_count_header)
    print("API truncated header:", truncated)

    # Save the original API response for reproducibility.
    raw_csv_path = RAW_DIR / "indore_daily_measurements_2024.csv"

    raw_csv_path.write_text(
        response.text,
        encoding="utf-8-sig",
    )

    print("\nRaw CSV saved:", raw_csv_path)

    if not response.text.strip():
        print("API returned an empty response.")
        return

    try:
        df = pd.read_csv(io.StringIO(response.text))
    except Exception as error:
        print("Could not parse CSV:", error)
        print("Inspect the raw CSV before proceeding.")
        return

    if df.empty:
        print("No measurements returned for this query.")
        print("Check station availability and API response.")
        return

    print("\nReturned columns:")
    print(list(df.columns))

    print("\nReturned rows:", len(df))

    # Save normalized records without assuming a fixed response schema.
    normalized_path = (
        RAW_DIR / "indore_daily_measurements_2024.parquet"
    )

    df.to_parquet(
        normalized_path,
        index=False,
    )

    print("Parquet saved:", normalized_path)

    # Build a coverage report when expected fields are present.
    if "station_id" in df.columns:
        station_col = "station_id"
    elif "site_id" in df.columns:
        station_col = "site_id"
    else:
        station_col = None

    if "parameter_name" in df.columns:
        parameter_col = "parameter_name"
    elif "parameter" in df.columns:
        parameter_col = "parameter"
    else:
        parameter_col = None

    time_col = next(
        (
            column
            for column in [
                "period_start",
                "collected_at",
                "timestamp",
            ]
            if column in df.columns
        ),
        None,
    )

    coverage = {
        "source": "XKDR India Air Quality Database",
        "downloaded_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "requested_start": START_DATE,
        "requested_end": END_DATE,
        "stations_requested": STATIONS,
        "parameters_requested": PARAMETERS,
        "aggregation": "daily",
        "returned_rows": len(df),
        "api_row_count_header": row_count_header,
        "api_truncated_header": truncated,
        "station_column": station_col,
        "parameter_column": parameter_col,
        "time_column": time_col,
        "columns": list(df.columns),
        "data_file": str(normalized_path),
        "limitations": [
            "Daily aggregates cannot validate individual 15-minute events.",
            "A missing station-pollutant combination does not mean zero pollution.",
            "Historical observations do not independently identify a factory source.",
        ],
    }

    if station_col:
        station_counts = (
            df.groupby(station_col)
            .size()
            .to_dict()
        )

        coverage["rows_by_station"] = {
            str(key): int(value)
            for key, value in station_counts.items()
        }

    if parameter_col:
        parameter_counts = (
            df.groupby(parameter_col)
            .size()
            .to_dict()
        )

        coverage["rows_by_parameter"] = {
            str(key): int(value)
            for key, value in parameter_counts.items()
        }

    if time_col:
        timestamps = pd.to_datetime(
            df[time_col],
            errors="coerce",
        )

        coverage["first_timestamp_returned"] = (
            str(timestamps.min())
            if timestamps.notna().any()
            else None
        )

        coverage["last_timestamp_returned"] = (
            str(timestamps.max())
            if timestamps.notna().any()
            else None
        )

    coverage_path = REPORT_DIR / "xkdr_download_coverage.json"

    coverage_path.write_text(
        json.dumps(
            coverage,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\nCoverage summary:")

    if station_col:
        print("\nRows by station:")
        print(df[station_col].value_counts().to_string())

    if parameter_col:
        print("\nRows by pollutant:")
        print(df[parameter_col].value_counts().to_string())

    if time_col:
        print("\nDate range:")
        print(coverage["first_timestamp_returned"])
        print("to")
        print(coverage["last_timestamp_returned"])

    print("\nCoverage report saved:", coverage_path)

    print("\nDownload step completed.")
    print(
        "Next: inspect station coverage, missing measurements, "
        "units, and timestamp conventions."
    )


if __name__ == "__main__":
    main()