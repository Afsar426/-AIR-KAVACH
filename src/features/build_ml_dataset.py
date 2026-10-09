from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# AIR KAVACH - ML READY ATTRIBUTION DATASET BUILDER
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

FEATURE_DIR = PROJECT_ROOT / "data" / "features"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_DIR = FEATURE_DIR / "ml"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "attribution_dataset.parquet"
CSV_OUTPUT_FILE = OUTPUT_DIR / "attribution_dataset.csv"


INPUT_FILES = {
    "events": (
        PROCESSED_DIR
        / "events"
        / "pollution_events.parquet"
    ),
    "event_wind": (
        FEATURE_DIR
        / "pollution_events_with_wind.parquet"
    ),
    "distances": (
        FEATURE_DIR
        / "sensor_factory_distances.parquet"
    ),
    "attribution": (
        FEATURE_DIR
        / "event_factory_attribution.parquet"
    ),
    "confidence": (
        FEATURE_DIR
        / "event_factory_confidence.parquet"
    ),
    "factories": (
        PROCESSED_DIR
        / "factories"
        / "factories_clean.parquet"
    ),
}


def load_parquet(name, path):
    """Load and validate an existing Parquet file."""

    if not path.exists():
        raise FileNotFoundError(
            f"Required file '{name}' not found:\n{path}"
        )

    df = pd.read_parquet(path)

    print(
        f"{name}: {len(df)} rows, "
        f"{len(df.columns)} columns"
    )

    return df


def require_columns(df, columns, dataset_name):
    """Check whether required columns exist."""

    missing = [
        column
        for column in columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{dataset_name} is missing columns: {missing}\n"
            f"Available columns: {df.columns.tolist()}"
        )


def add_if_missing(df, column, default=np.nan):
    """Add an optional feature if it does not exist."""

    if column not in df.columns:
        df[column] = default

    return df


def main():

    print("=" * 72)
    print("AIR KAVACH - ML ATTRIBUTION DATASET BUILDER")
    print("=" * 72)

    # --------------------------------------------------------
    # 1. LOAD INPUT DATASETS
    # --------------------------------------------------------

    print("\n[1/7] Loading datasets...")

    events = load_parquet(
        "Pollution events",
        INPUT_FILES["events"]
    )

    event_wind = load_parquet(
        "Event wind",
        INPUT_FILES["event_wind"]
    )

    distances = load_parquet(
        "Sensor-factory distances",
        INPUT_FILES["distances"]
    )

    attribution = load_parquet(
        "Attribution scores",
        INPUT_FILES["attribution"]
    )

    confidence = load_parquet(
        "Confidence scores",
        INPUT_FILES["confidence"]
    )

    factories = load_parquet(
        "Factory metadata",
        INPUT_FILES["factories"]
    )

    # --------------------------------------------------------
    # 2. VALIDATE SCHEMAS
    # --------------------------------------------------------

    print("\n[2/7] Validating schemas...")

    require_columns(
        events,
        [
            "event_id",
            "station",
            "start_time",
            "end_time",
            "peak_pm25",
            "peak_time",
            "peak_z_score",
            "duration_minutes",
        ],
        "Pollution events"
    )

    require_columns(
        event_wind,
        [
            "event_id",
            "station",
            "wind_direction_mean_deg",
            "wind_speed_mean_mps",
            "wind_coverage",
        ],
        "Event wind"
    )

    require_columns(
        distances,
        [
            "sensor",
            "factory_id",
            "facility_category",
            "distance_km",
        ],
        "Sensor-factory distances"
    )

    require_columns(
        attribution,
        [
            "event_id",
            "station",
            "factory_id",
            "attribution_score",
            "relative_likelihood",
            "wind_alignment",
            "wind_relationship",
        ],
        "Attribution"
    )

    require_columns(
        confidence,
        [
            "event_id",
            "station",
            "factory_id",
            "confidence_percent",
            "uncertainty_percent",
            "confidence_level",
            "uncertainty_level",
        ],
        "Confidence"
    )

    require_columns(
        factories,
        [
            "factory_id",
            "factory_name",
            "facility_category",
        ],
        "Factories"
    )

    print("Required schemas validated.")

    # --------------------------------------------------------
    # 3. PREPARE EVENT FEATURES
    # --------------------------------------------------------

    print("\n[3/7] Preparing event features...")

    event_features = events[
        [
            "event_id",
            "station",
            "start_time",
            "end_time",
            "peak_pm25",
            "peak_time",
            "peak_z_score",
            "duration_minutes",
        ]
    ].copy()

    event_features = event_features.merge(
        event_wind[
            [
                "event_id",
                "station",
                "wind_direction_mean_deg",
                "wind_speed_mean_mps",
                "wind_speed_min_mps",
                "wind_speed_max_mps",
                "wind_coverage",
                "wind_observations",
            ]
        ],
        on=["event_id", "station"],
        how="left",
        validate="one_to_one"
    )

    event_features.rename(
        columns={
            "duration_minutes": "event_duration_minutes",
        },
        inplace=True
    )

    event_features["event_duration_minutes"] = pd.to_numeric(
        event_features["event_duration_minutes"],
        errors="coerce"
    )

    event_features["peak_pm25"] = pd.to_numeric(
        event_features["peak_pm25"],
        errors="coerce"
    )

    event_features["peak_z_score"] = pd.to_numeric(
        event_features["peak_z_score"],
        errors="coerce"
    )

    print(
        "Event feature rows:",
        len(event_features)
    )

    # --------------------------------------------------------
    # 4. PREPARE FACTORY METADATA
    # --------------------------------------------------------

    print("\n[4/7] Preparing factory metadata...")

    factory_metadata = factories[
        [
            "factory_id",
            "factory_name",
            "facility_category",
        ]
    ].drop_duplicates(
        subset=["factory_id"]
    )

    distance_features = distances[
        [
            "sensor",
            "factory_id",
            "distance_km",
        ]
    ].copy()

    distance_features.rename(
        columns={
            "sensor": "station",
        },
        inplace=True
    )

    distance_features = distance_features.drop_duplicates(
        subset=["station", "factory_id"]
    )

    # --------------------------------------------------------
    # 5. BUILD EVENT-FACTORY PAIRS
    # --------------------------------------------------------

    print("\n[5/7] Building event-factory feature table...")

    attribution_features = attribution.copy()

    attribution_features = attribution_features.merge(
        confidence[
            [
                "event_id",
                "station",
                "factory_id",
                "confidence_percent",
                "uncertainty_percent",
                "confidence_level",
                "uncertainty_level",
            ]
        ].drop_duplicates(
            subset=["event_id", "station", "factory_id"]
        ),
        on=["event_id", "station", "factory_id"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_confidence")
    )

    attribution_features = attribution_features.merge(
        event_features,
        on=["event_id", "station"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_event")
    )

    attribution_features = attribution_features.merge(
        distance_features,
        on=["station", "factory_id"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_distance")
    )

    attribution_features = attribution_features.merge(
        factory_metadata,
        on="factory_id",
        how="left",
        validate="many_to_one",
        suffixes=("", "_factory")
    )

    # Use existing distance if the attribution table already
    # contains it; otherwise use the distance lookup.
    if "distance_km" not in attribution_features.columns:
        if "distance_km_distance" in attribution_features.columns:
            attribution_features["distance_km"] = (
                attribution_features["distance_km_distance"]
            )

    # --------------------------------------------------------
    # 6. CREATE DERIVED FEATURES AND VALIDATE
    # --------------------------------------------------------

    print("\n[6/7] Creating and validating ML features...")

    df = attribution_features.copy()

    # Optional fields: preserve missing values honestly.
    optional_columns = [
        "wind_speed_mean_mps",
        "wind_coverage",
        "peak_pm25",
        "peak_z_score",
        "event_duration_minutes",
        "wind_alignment",
        "relative_likelihood",
        "confidence_percent",
        "uncertainty_percent",
        "distance_km",
    ]

    for column in optional_columns:
        df = add_if_missing(df, column)

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # Circular representation of wind direction.
    direction = pd.to_numeric(
        df["wind_direction_mean_deg"],
        errors="coerce"
    )

    radians = np.deg2rad(direction)

    df["wind_direction_sin"] = np.sin(radians)
    df["wind_direction_cos"] = np.cos(radians)

    # Wind speed quality flags.
    df["wind_speed_missing"] = (
        df["wind_speed_mean_mps"].isna().astype(int)
    )

    df["wind_coverage_missing"] = (
        df["wind_coverage"].isna().astype(int)
    )

    # Do not invent values for unavailable observations.
    # Missing data will remain NaN and be handled later.

    # Preserve identifiers, features, and diagnostic fields.
    feature_columns = [
        "event_id",
        "station",
        "factory_id",
        "factory_name",
        "facility_category",
        "start_time",
        "end_time",
        "peak_time",
        "peak_pm25",
        "peak_z_score",
        "event_duration_minutes",
        "distance_km",
        "wind_direction_mean_deg",
        "wind_direction_sin",
        "wind_direction_cos",
        "wind_speed_mean_mps",
        "wind_speed_min_mps",
        "wind_speed_max_mps",
        "wind_coverage",
        "wind_observations",
        "wind_speed_missing",
        "wind_coverage_missing",
        "wind_alignment",
        "wind_relationship",
        "attribution_score",
        "relative_likelihood",
        "confidence_percent",
        "uncertainty_percent",
        "confidence_level",
        "uncertainty_level",
    ]

    for column in feature_columns:
        df = add_if_missing(df, column)

    dataset = df[feature_columns].copy()

    # Keep one row per event-factory pair.
    dataset = dataset.drop_duplicates(
        subset=["event_id", "station", "factory_id"]
    )

    # Remove rows that cannot be identified.
    dataset = dataset.dropna(
        subset=[
            "event_id",
            "station",
            "factory_id",
        ]
    )

    # Explicitly state that verified source labels are unavailable.
    dataset["source_label"] = pd.Series(
        pd.NA,
        index=dataset.index,
        dtype="Int64"
    )

    dataset["label_status"] = "unlabelled"

    # Record data quality flags.
    dataset["missing_distance"] = (
        dataset["distance_km"].isna().astype(int)
    )

    dataset["missing_wind_direction"] = (
        dataset["wind_direction_mean_deg"]
        .isna()
        .astype(int)
    )

    dataset["missing_peak_pm25"] = (
        dataset["peak_pm25"].isna().astype(int)
    )

    # --------------------------------------------------------
    # 7. SAVE AND SUMMARISE
    # --------------------------------------------------------

    print("\n[7/7] Saving ML-ready dataset...")

    dataset.to_parquet(
        OUTPUT_FILE,
        index=False
    )

    dataset.to_csv(
        CSV_OUTPUT_FILE,
        index=False
    )

    print("\n" + "=" * 72)
    print("AIR KAVACH - ML DATASET SUMMARY")
    print("=" * 72)

    print("Total rows:", len(dataset))

    print(
        "Unique events:",
        dataset["event_id"].nunique()
    )

    print(
        "Unique stations:",
        dataset["station"].nunique()
    )

    print(
        "Unique factories:",
        dataset["factory_id"].nunique()
    )

    print(
        "Unique event-factory pairs:",
        dataset[
            ["event_id", "station", "factory_id"]
        ].drop_duplicates().shape[0]
    )

    print(
        "Verified source labels:",
        int(dataset["source_label"].notna().sum())
    )

    print(
        "Unlabelled rows:",
        int(dataset["source_label"].isna().sum())
    )

    print("\nMissing values in important features:")

    important_features = [
        "distance_km",
        "peak_pm25",
        "peak_z_score",
        "wind_direction_mean_deg",
        "wind_speed_mean_mps",
        "wind_coverage",
        "wind_alignment",
    ]

    print(
        dataset[important_features]
        .isna()
        .sum()
        .to_string()
    )

    print("\nSample records:")

    print(
        dataset[
            [
                "event_id",
                "station",
                "factory_name",
                "distance_km",
                "wind_speed_mean_mps",
                "wind_alignment",
                "attribution_score",
                "source_label",
                "label_status",
            ]
        ].head(10).to_string(index=False)
    )

    print("\nParquet output:")
    print(OUTPUT_FILE)

    print("\nCSV output:")
    print(CSV_OUTPUT_FILE)

    print("\n" + "=" * 72)
    print("ML-READY DATASET CREATED")
    print("Note: Dataset is unlabelled; no ML model was trained.")
    print("=" * 72)


if __name__ == "__main__":
    main()