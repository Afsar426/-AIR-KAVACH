"""
AIR KAVACH - Reference Data Catalog

Purpose:
Maintain a structured registry of external datasets that may support
industrial pollution investigation and source attribution.

Important:
Registering a dataset does not mean its data has been downloaded,
validated, or independently verified.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


# Project root: AIR-KAVACH/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = PROJECT_ROOT / "reports" / "generated" / "reference_data"

CSV_OUTPUT = OUTPUT_DIR / "reference_data_catalog.csv"
JSON_OUTPUT = OUTPUT_DIR / "reference_data_catalog.json"


DATASETS = [
    {
        "dataset_id": "REF-001",
        "name": "OpenAQ",
        "url": "https://openaq.org/",
        "category": "Air Quality Observations",
        "geographic_scope": "Global",
        "potential_use": (
            "Collect historical pollutant observations, identify pollution "
            "events, and expand monitoring-station coverage."
        ),
        "required_fields": (
            "timestamp, station_id, latitude, longitude, pollutant, value, unit"
        ),
        "limitations": (
            "Station coverage, historical availability, sensor quality, "
            "and temporal overlap must be checked for each location."
        ),
        "verification_status": "existing_source_requires_expansion_audit",
        "download_status": "partially_downloaded",
        "priority": "high",
    },
    {
        "dataset_id": "REF-002",
        "name": "India Air Quality Database - XKDR Forum",
        "url": "https://airquality.xkdr.org/",
        "category": "Indian Air Quality Data",
        "geographic_scope": "India",
        "potential_use": (
            "Investigate additional Indian monitoring records and possible "
            "historical observations for comparison with OpenAQ."
        ),
        "required_fields": (
            "station, timestamp, pollutant, measurement, coordinates"
        ),
        "limitations": (
            "Actual fields, station coverage, historical period, access "
            "conditions, and overlap with the current Indore dataset "
            "must be verified."
        ),
        "verification_status": "pending_source_inspection",
        "download_status": "not_downloaded",
        "priority": "high",
    },
    {
        "dataset_id": "REF-003",
        "name": "ERA5 Reanalysis",
        "url": "https://cds.climate.copernicus.eu/",
        "category": "Meteorological Reanalysis",
        "geographic_scope": "Global",
        "potential_use": (
            "Provide historical wind and weather fields for investigating "
            "pollution transport conditions."
        ),
        "required_fields": (
            "timestamp, latitude, longitude, u10, v10"
        ),
        "limitations": (
            "Reanalysis is not a direct measurement at each factory. "
            "Spatial and temporal resolution, access requirements, "
            "and agreement with local observations must be assessed."
        ),
        "verification_status": "pending_access_and_coverage_check",
        "download_status": "not_downloaded",
        "priority": "high",
    },
    {
        "dataset_id": "REF-004",
        "name": "EDGAR Emissions Inventory",
        "url": "https://edgar.jrc.ec.europa.eu/",
        "category": "Emissions Inventory",
        "geographic_scope": "Global",
        "potential_use": (
            "Provide regional emissions context and investigate whether "
            "relevant pollutants and industrial sectors are represented."
        ),
        "required_fields": (
            "year, pollutant, sector, geographic_unit, emissions_value"
        ),
        "limitations": (
            "Inventory estimates do not automatically provide actual "
            "emissions from a named factory during a specific event."
        ),
        "verification_status": "pending_inventory_inspection",
        "download_status": "not_downloaded",
        "priority": "medium",
    },
    {
        "dataset_id": "REF-005",
        "name": "Published Indian PM2.5 Source Attribution Research",
        "url": (
            "https://acp.copernicus.org/articles/26/10533/2026/"
            "acp-26-10533-2026.html"
        ),
        "category": "Research and Supplementary Data",
        "geographic_scope": "India",
        "potential_use": (
            "Review source-attribution methodology and check for "
            "downloadable supplementary data that can support validation."
        ),
        "required_fields": (
            "documented_source_labels, locations, timestamps, "
            "pollutant_measurements, methodology"
        ),
        "limitations": (
            "Published regional source attribution may not identify "
            "individual factories or overlap with our Indore events."
        ),
        "verification_status": "paper_and_supplementary_files_need_review",
        "download_status": "not_downloaded",
        "priority": "medium",
    },
    {
        "dataset_id": "REF-006",
        "name": "OpenStreetMap Industrial Facilities",
        "url": "https://www.openstreetmap.org/",
        "category": "Facility Locations",
        "geographic_scope": "Global",
        "potential_use": (
            "Expand and cross-check mapped industrial facility locations "
            "and available facility classifications."
        ),
        "required_fields": (
            "facility_id, name, latitude, longitude, industrial_tags"
        ),
        "limitations": (
            "Facility records can be incomplete or outdated. A mapped "
            "facility is not proof that it emitted pollution during an event."
        ),
        "verification_status": "existing_source_requires_quality_review",
        "download_status": "partially_downloaded",
        "priority": "medium",
    },
]


def validate_catalog(datasets):
    """Check basic catalog integrity without claiming data validation."""

    errors = []
    seen_ids = set()

    for dataset in datasets:
        dataset_id = dataset.get("dataset_id")

        if not dataset_id:
            errors.append("Dataset found without dataset_id.")
            continue

        if dataset_id in seen_ids:
            errors.append(f"Duplicate dataset_id: {dataset_id}")

        seen_ids.add(dataset_id)

        required_keys = [
            "name",
            "url",
            "category",
            "potential_use",
            "verification_status",
            "download_status",
        ]

        for key in required_keys:
            if not dataset.get(key):
                errors.append(
                    f"{dataset_id}: missing required field '{key}'"
                )

    return errors


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    errors = validate_catalog(DATASETS)

    if errors:
        print("CATALOG VALIDATION FAILED")

        for error in errors:
            print(f"- {error}")

        raise SystemExit(1)

    generated_at = datetime.now(timezone.utc).isoformat()

    catalog_document = {
        "project": "AIR KAVACH",
        "catalog_version": "1.0",
        "generated_at_utc": generated_at,
        "dataset_count": len(DATASETS),
        "important_note": (
            "Catalog registration is not proof of dataset availability, "
            "data quality, source attribution, or factory responsibility."
        ),
        "datasets": DATASETS,
    }

    # Save machine-readable JSON.
    with JSON_OUTPUT.open("w", encoding="utf-8") as file:
        json.dump(
            catalog_document,
            file,
            indent=4,
            ensure_ascii=False,
        )

    # Save spreadsheet-compatible CSV.
    fieldnames = list(DATASETS[0].keys())

    with CSV_OUTPUT.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(DATASETS)

    print("=" * 60)
    print("AIR KAVACH - REFERENCE DATA CATALOG")
    print("=" * 60)

    print(f"Catalog validation: PASSED")
    print(f"Datasets registered: {len(DATASETS)}")
    print(f"Generated at UTC: {generated_at}")

    print("\nDataset status:")

    for dataset in DATASETS:
        print(
            f"- {dataset['dataset_id']} | "
            f"{dataset['name']} | "
            f"{dataset['verification_status']}"
        )

    print("\nOutput files:")
    print(f"CSV:  {CSV_OUTPUT}")
    print(f"JSON: {JSON_OUTPUT}")

    print("\nNote:")
    print(
        "Sources are registered for investigation. "
        "Their data has not all been independently verified or downloaded."
    )


if __name__ == "__main__":
    main()