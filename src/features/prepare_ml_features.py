from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# AIR KAVACH - INDEPENDENT ML FEATURE ENGINEERING
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT
    / "data"
    / "features"
    / "ml"
    / "attribution_dataset.parquet"
)

OUTPUT_DIR = (
    ROOT
    / "data"
    / "features"
    / "ml"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "independent_ml_features.parquet"
)

CSV_FILE = (
    OUTPUT_DIR
    / "independent_ml_features.csv"
)

MANIFEST_FILE = (
    OUTPUT_DIR
    / "feature_manifest.csv"
)


def require_columns(df, columns):
    missing = [
        column
        for column in columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}\n"
            f"Available columns: {df.columns.tolist()}"
        )


def circular_features(
    degrees,
    prefix
):
    """
    Convert an angular variable into sine and cosine.

    This avoids treating 359 degrees and 1 degree
    as very different values.
    """

    radians = np.deg2rad(
        pd.to_numeric(
            degrees,
            errors="coerce"
        )
    )

    return (
        np.sin(radians),
        np.cos(radians)
    )


def main():

    print("=" * 72)
    print("AIR KAVACH - INDEPENDENT ML FEATURE ENGINEERING")
    print("=" * 72)

    # --------------------------------------------------------
    # 1. LOAD DATASET
    # --------------------------------------------------------

    print("\n[1/7] Loading validated dataset...")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {INPUT_FILE}"
        )

    df = pd.read_parquet(
        INPUT_FILE
    )

    print("Rows:", len(df))
    print("Columns:", len(df.columns))

    # --------------------------------------------------------
    # 2. VALIDATE INPUT SCHEMA
    # --------------------------------------------------------

    print("\n[2/7] Validating required columns...")

    required_columns = [
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
        "wind_speed_mean_mps",
        "wind_coverage",
        "wind_alignment",
    ]

    require_columns(
        df,
        required_columns
    )

    if df.duplicated(
        subset=[
            "event_id",
            "station",
            "factory_id"
        ]
    ).any():

        raise ValueError(
            "Duplicate event-factory pairs detected."
        )

    print("Schema validation passed.")

    # --------------------------------------------------------
    # 3. PRESERVE IDENTIFIERS AND RAW EVIDENCE
    # --------------------------------------------------------

    print("\n[3/7] Selecting independent evidence features...")

    feature_df = df[
        [
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
            "wind_speed_mean_mps",
            "wind_coverage",
            "wind_alignment",
        ]
    ].copy()

    # --------------------------------------------------------
    # 4. TEMPORAL FEATURE ENGINEERING
    # --------------------------------------------------------

    print("\n[4/7] Engineering temporal features...")

    feature_df["peak_time"] = pd.to_datetime(
        feature_df["peak_time"],
        utc=True,
        errors="coerce"
    )

    feature_df["start_time"] = pd.to_datetime(
        feature_df["start_time"],
        utc=True,
        errors="coerce"
    )

    feature_df["end_time"] = pd.to_datetime(
        feature_df["end_time"],
        utc=True,
        errors="coerce"
    )

    # These timestamps represent UTC, not local time.

    feature_df["event_hour_utc"] = (
        feature_df["peak_time"].dt.hour
    )

    feature_df["event_day_of_week_utc"] = (
        feature_df["peak_time"].dt.dayofweek
    )

    hour_angle = (
        2
        * np.pi
        * feature_df["event_hour_utc"]
        / 24
    )

    feature_df["event_hour_sin"] = (
        np.sin(hour_angle)
    )

    feature_df["event_hour_cos"] = (
        np.cos(hour_angle)
    )

    # --------------------------------------------------------
    # 5. WIND FEATURE ENGINEERING
    # --------------------------------------------------------

    print("\n[5/7] Engineering wind features...")

    direction = pd.to_numeric(
        feature_df["wind_direction_mean_deg"],
        errors="coerce"
    )

    direction_valid = (
        direction.notna()
        & direction.ge(0)
        & direction.le(360)
    )

    # 360 degrees and 0 degrees represent the same direction.
    normalized_direction = direction % 360

    (
        feature_df["wind_direction_sin"],
        feature_df["wind_direction_cos"]
    ) = circular_features(
        normalized_direction,
        "wind_direction"
    )

    feature_df.loc[
        ~direction_valid,
        [
            "wind_direction_sin",
            "wind_direction_cos"
        ]
    ] = np.nan

    speed = pd.to_numeric(
        feature_df["wind_speed_mean_mps"],
        errors="coerce"
    )

    # Negative speed values are invalid.
    speed = speed.where(
        speed >= 0,
        np.nan
    )

    feature_df["wind_speed_mean_mps"] = speed

    # Keep missingness explicit.
    feature_df["wind_speed_missing"] = (
        speed.isna().astype("int8")
    )

    # Missing wind speed remains missing.
    # Do not replace it with zero.

    coverage = pd.to_numeric(
        feature_df["wind_coverage"],
        errors="coerce"
    )

    coverage = coverage.where(
        coverage.between(0, 1),
        np.nan
    )

    feature_df["wind_coverage"] = coverage

    # --------------------------------------------------------
    # 6. POLLUTION AND GEOGRAPHIC FEATURES
    # --------------------------------------------------------

    print("\n[6/7] Engineering pollution and geographic features...")

    numeric_columns = [
        "peak_pm25",
        "peak_z_score",
        "event_duration_minutes",
        "distance_km",
        "wind_alignment",
    ]

    for column in numeric_columns:

        feature_df[column] = pd.to_numeric(
            feature_df[column],
            errors="coerce"
        )

    # Invalid physical values are marked missing.
    feature_df["distance_km"] = (
        feature_df["distance_km"]
        .where(feature_df["distance_km"] >= 0)
    )

    feature_df["peak_pm25"] = (
        feature_df["peak_pm25"]
        .where(feature_df["peak_pm25"] >= 0)
    )

    feature_df["event_duration_minutes"] = (
        feature_df["event_duration_minutes"]
        .where(
            feature_df["event_duration_minutes"] >= 0
        )
    )

    # Log transforms reduce the influence of extreme values.
    feature_df["log_distance_km"] = np.log1p(
        feature_df["distance_km"]
    )

    feature_df["log_peak_pm25"] = np.log1p(
        feature_df["peak_pm25"]
    )

    # Missingness indicators.
    feature_df["distance_missing"] = (
        feature_df["distance_km"]
        .isna()
        .astype("int8")
    )

    feature_df["wind_alignment_missing"] = (
        feature_df["wind_alignment"]
        .isna()
        .astype("int8")
    )

    # --------------------------------------------------------
    # FEATURE GROUPS
    # --------------------------------------------------------

    identity_columns = [
        "event_id",
        "station",
        "factory_id",
        "factory_name",
        "start_time",
        "end_time",
        "peak_time",
    ]

    categorical_features = [
        "station",
        "facility_category",
    ]

    numeric_features = [
        "event_hour_utc",
        "event_day_of_week_utc",
        "event_hour_sin",
        "event_hour_cos",
        "peak_pm25",
        "log_peak_pm25",
        "peak_z_score",
        "event_duration_minutes",
        "distance_km",
        "log_distance_km",
        "wind_direction_sin",
        "wind_direction_cos",
        "wind_speed_mean_mps",
        "wind_speed_missing",
        "wind_coverage",
        "wind_alignment",
        "wind_alignment_missing",
        "distance_missing",
    ]

    # Candidate identifiers are metadata, not model features.
    metadata_columns = [
        "factory_id",
        "factory_name",
        "event_id",
        "start_time",
        "end_time",
        "peak_time",
    ]

    # --------------------------------------------------------
    # SAVE DATASET
    # --------------------------------------------------------

    output_columns = list(
        dict.fromkeys(
            identity_columns
            + categorical_features
            + numeric_features
        )
    )

    output = feature_df[
        output_columns
    ].copy()

    output.to_parquet(
        OUTPUT_FILE,
        index=False
    )

    output.to_csv(
        CSV_FILE,
        index=False
    )

    # Feature manifest documents intended use.
    manifest_rows = []

    for column in categorical_features:

        manifest_rows.append({
            "feature": column,
            "type": "categorical",
            "role": "model_input_candidate",
        })

    for column in numeric_features:

        manifest_rows.append({
            "feature": column,
            "type": "numeric",
            "role": "model_input_candidate",
        })

    for column in metadata_columns:

        manifest_rows.append({
            "feature": column,
            "type": "metadata",
            "role": "identifier_or_audit_only",
        })

    manifest = pd.DataFrame(
        manifest_rows
    )

    manifest.to_csv(
        MANIFEST_FILE,
        index=False
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 72)
    print("FEATURE ENGINEERING SUMMARY")
    print("=" * 72)

    print("Rows:", len(output))
    print("Events:", output["event_id"].nunique())
    print("Stations:", output["station"].nunique())
    print("Factories:", output["factory_id"].nunique())

    print(
        "Categorical input candidates:",
        len(categorical_features)
    )

    print(
        "Numeric input candidates:",
        len(numeric_features)
    )

    print("\nMissing values in numeric features:")

    print(
        output[numeric_features]
        .isna()
        .sum()
        .to_string()
    )

    print("\nExcluded from independent model inputs:")
    print("- attribution_score")
    print("- relative_likelihood")
    print("- confidence_percent")
    print("- uncertainty_percent")
    print("- factory_rank")

    print("\nOutput files:")
    print(OUTPUT_FILE)
    print(CSV_FILE)
    print(MANIFEST_FILE)

    print("\nIMPORTANT:")
    print(
        "This is a feature dataset, not a labelled "
        "training dataset."
    )

    print(
        "No source labels were fabricated and "
        "no model was trained."
    )

    print("\nAIR KAVACH FEATURE ENGINEERING COMPLETE")


if __name__ == "__main__":
    main()