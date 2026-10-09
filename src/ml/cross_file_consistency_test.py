from pathlib import Path
import json

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "reports" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "events": "data/processed/events/pollution_events.parquet",
    "attribution": "data/features/event_factory_attribution.parquet",
    "confidence": "data/features/event_factory_confidence.parquet",
    "evidence_chain": "data/features/event_evidence_chain.parquet",
    "geospatial": "data/features/event_geospatial_evidence.parquet",
}

CSV_OUT = OUTPUT_DIR / "cross_file_consistency_report.csv"
JSON_OUT = OUTPUT_DIR / "cross_file_consistency_report.json"
MISSING_OUT = OUTPUT_DIR / "missing_value_audit.csv"


def load_parquet(name, relative_path):
    path = ROOT / relative_path

    if not path.exists():
        raise FileNotFoundError(f"{name}: file not found: {path}")

    return pd.read_parquet(path)


def find_column(df, candidates):
    lookup = {str(col).lower(): col for col in df.columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    return None


def main():
    print("=" * 72)
    print("AIR KAVACH — CROSS-FILE CONSISTENCY TEST")
    print("=" * 72)

    data = {
        name: load_parquet(name, path)
        for name, path in FILES.items()
    }

    for name, df in data.items():
        print(f"{name}: {len(df)} rows")

    # --------------------------------------------------------
    # Missing-value audit
    # --------------------------------------------------------
    missing_rows = []

    for name, df in data.items():
        for column in df.columns:
            missing_count = int(df[column].isna().sum())

            if missing_count:
                missing_rows.append({
                    "file": name,
                    "column": str(column),
                    "missing_count": missing_count,
                    "row_count": len(df),
                    "missing_percent": round(
                        missing_count / len(df) * 100, 2
                    ) if len(df) else 0,
                })

    missing_df = pd.DataFrame(
        missing_rows,
        columns=[
            "file",
            "column",
            "missing_count",
            "row_count",
            "missing_percent",
        ],
    )

    missing_df.to_csv(MISSING_OUT, index=False)

    # --------------------------------------------------------
    # Identify event ID columns
    # --------------------------------------------------------
    event_candidates = [
        "event_id",
        "event",
        "pollution_event_id",
    ]

    event_col = find_column(
        data["events"],
        event_candidates,
    )

    if event_col is None:
        raise ValueError(
            "Could not identify event ID column in pollution events. "
            f"Available columns: {list(data['events'].columns)}"
        )

    valid_event_ids = set(
        data["events"][event_col].dropna().astype(str)
    )

    checks = []

    def add_check(check, source, checked, failures, note):
        checks.append({
            "check": check,
            "source": source,
            "records_checked": int(checked),
            "failure_count": int(failures),
            "status": "PASS" if failures == 0 else "REVIEW",
            "note": note,
        })

    # --------------------------------------------------------
    # Check event references in each downstream file
    # --------------------------------------------------------
    event_reference_columns = {}

    for name in [
        "attribution",
        "confidence",
        "evidence_chain",
        "geospatial",
    ]:
        df = data[name]

        column = find_column(df, event_candidates)
        event_reference_columns[name] = column

        if column is None:
            add_check(
                "event_reference",
                name,
                len(df),
                len(df),
                "No recognizable event ID column; requires review.",
            )
            continue

        refs = df[column].dropna().astype(str)

        invalid_count = int(
            (~refs.isin(valid_event_ids)).sum()
        )

        null_count = int(df[column].isna().sum())

        add_check(
            "event_reference",
            name,
            len(df),
            invalid_count + null_count,
            (
                f"Event column={column}; "
                f"invalid references={invalid_count}; "
                f"null references={null_count}"
            ),
        )

    # --------------------------------------------------------
    # Compare event-factory pairs in attribution/confidence
    # --------------------------------------------------------
    attribution = data["attribution"]
    confidence = data["confidence"]

    attr_event_col = event_reference_columns["attribution"]
    conf_event_col = event_reference_columns["confidence"]

    factory_candidates = [
        "factory_id",
        "source_id",
        "facility_id",
        "factory_name",
        "source_name",
        "facility_name",
    ]

    attr_factory_col = find_column(
        attribution,
        factory_candidates,
    )

    conf_factory_col = find_column(
        confidence,
        factory_candidates,
    )

    if (
        attr_event_col is not None
        and conf_event_col is not None
        and attr_factory_col is not None
        and conf_factory_col is not None
    ):
        attr_pairs = set(
            zip(
                attribution[attr_event_col].astype(str),
                attribution[attr_factory_col].astype(str),
            )
        )

        conf_pairs = set(
            zip(
                confidence[conf_event_col].astype(str),
                confidence[conf_factory_col].astype(str),
            )
        )

        missing_pairs = conf_pairs - attr_pairs

        add_check(
            "confidence_event_factory_pairs",
            "confidence",
            len(conf_pairs),
            len(missing_pairs),
            (
                "Confidence event-factory pairs missing from "
                f"attribution={len(missing_pairs)}"
            ),
        )
    else:
        add_check(
            "confidence_event_factory_pairs",
            "confidence",
            len(confidence),
            len(confidence),
            (
                "Could not confidently identify event/factory columns. "
                f"Attribution columns={list(attribution.columns)}; "
                f"confidence columns={list(confidence.columns)}"
            ),
        )

    # --------------------------------------------------------
    # Save reports
    # --------------------------------------------------------
    report_df = pd.DataFrame(checks)
    report_df.to_csv(CSV_OUT, index=False)

    report = {
        "project": "AIR KAVACH",
        "files_loaded": {
            name: len(df)
            for name, df in data.items()
        },
        "checks": checks,
        "missing_value_columns": missing_rows,
        "limitations": [
            "PASS means structural consistency only.",
            "This test does not validate scientific correctness.",
            "It does not verify that files were generated from the latest inputs.",
            "Factory/source identity matching depends on available identifiers.",
        ],
    }

    JSON_OUT.write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )

    print("\nCONSISTENCY CHECKS:")
    print(report_df.to_string(index=False))

    print("\nMissing-value columns:")
    if missing_df.empty:
        print("No missing values found in checked files.")
    else:
        print(
            missing_df.sort_values(
                "missing_count",
                ascending=False,
            ).to_string(index=False)
        )

    print("\nReports saved:")
    print(CSV_OUT)
    print(JSON_OUT)
    print(MISSING_OUT)


if __name__ == "__main__":
    main()