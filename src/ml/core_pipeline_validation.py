from pathlib import Path
import json

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = ROOT / "reports" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_CSV = OUTPUT_DIR / "core_pipeline_validation.csv"
REPORT_JSON = OUTPUT_DIR / "core_pipeline_validation.json"


FILES = {
    "air_quality": (
        "data/processed/air_quality/air_quality.parquet"
    ),
    "pollution_events": (
        "data/processed/events/pollution_events.parquet"
    ),
    "factories": (
        "data/processed/factories/factories_clean.parquet"
    ),
    "wind": (
        "data/processed/weather/wind.parquet"
    ),
    "attribution": (
        "data/features/event_factory_attribution.parquet"
    ),
    "confidence": (
        "data/features/event_factory_confidence.parquet"
    ),
    "evidence_chain": (
        "data/features/event_evidence_chain.parquet"
    ),
    "geospatial_evidence": (
        "data/features/event_geospatial_evidence.parquet"
    ),
    "ml_anomaly_scores": (
        "data/features/ml_anomaly_scores.parquet"
    ),
    "event_wind_alignment": (
        "data/features/pollution_events_with_wind.parquet"
    ),
    "distance_features": (
        "data/features/sensor_factory_distances.parquet"
    ),
    "wind_alignment": (
        "data/features/sensor_factory_wind_alignment.parquet"
    ),
}


def inspect_file(name, relative_path):
    path = ROOT / relative_path

    result = {
        "module": name,
        "file": relative_path,
        "exists": path.exists(),
        "readable": False,
        "row_count": None,
        "column_count": None,
        "columns": None,
        "missing_cells": None,
        "duplicate_rows": None,
        "error": None,
    }

    if not path.exists():
        result["error"] = "File not found"
        return result

    try:
        df = pd.read_parquet(path)

        result["readable"] = True
        result["row_count"] = int(len(df))
        result["column_count"] = int(len(df.columns))
        result["columns"] = ", ".join(map(str, df.columns))
        result["missing_cells"] = int(df.isna().sum().sum())
        result["duplicate_rows"] = int(
            df.duplicated().sum()
        )

    except Exception as exc:
        result["error"] = (
            f"{type(exc).__name__}: {exc}"
        )

    return result


def main():
    print("=" * 72)
    print("AIR KAVACH — CORE PIPELINE VALIDATION")
    print("=" * 72)

    results = []

    for name, relative_path in FILES.items():
        result = inspect_file(name, relative_path)
        results.append(result)

        if result["readable"]:
            status = "READABLE"
            print(
                f"[{status}] {name}: "
                f"{result['row_count']} rows, "
                f"{result['column_count']} columns"
            )
        else:
            print(
                f"[ERROR] {name}: {result['error']}"
            )

    report_df = pd.DataFrame(results)

    report_df.to_csv(
        REPORT_CSV,
        index=False,
    )

    report = {
        "project": "AIR KAVACH",
        "total_files_checked": len(results),
        "existing_files": int(
            report_df["exists"].sum()
        ),
        "readable_files": int(
            report_df["readable"].sum()
        ),
        "unreadable_or_missing_files": int(
            (~report_df["readable"]).sum()
        ),
        "total_missing_cells": int(
            report_df["missing_cells"].fillna(0).sum()
        ),
        "files": results,
        "limitations": [
            "Readable files do not prove scientific validity.",
            "This test does not verify attribution accuracy.",
            "This test does not verify that outputs were generated from the latest inputs.",
            "Cross-file schema and event-reference checks are not performed by this initial test.",
        ],
    }

    REPORT_JSON.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nSUMMARY")
    print("-" * 72)
    print(f"Files checked: {len(results)}")
    print(f"Readable: {report['readable_files']}")
    print(
        "Missing/unreadable: "
        f"{report['unreadable_or_missing_files']}"
    )
    print(
        "Missing cells across readable files: "
        f"{report['total_missing_cells']}"
    )

    print("\nReports saved:")
    print(REPORT_CSV)
    print(REPORT_JSON)


if __name__ == "__main__":
    main()