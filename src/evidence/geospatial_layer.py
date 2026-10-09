from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# AIR KAVACH - GEOSPATIAL EVIDENCE LAYER
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

EVIDENCE_FILE = (
    BASE_DIR
    / "data"
    / "features"
    / "event_evidence_chain.parquet"
)

DISTANCE_FILE = (
    BASE_DIR
    / "data"
    / "features"
    / "sensor_factory_distances.parquet"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "features"
    / "event_geospatial_evidence.parquet"
)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("AIR KAVACH - GEOSPATIAL EVIDENCE LAYER")
    print("=" * 70)

    # ========================================================
    # 1. LOAD EVIDENCE DATA
    # ========================================================

    print("\n[1/6] Loading evidence chain...")

    evidence = pd.read_parquet(
        EVIDENCE_FILE
    )

    print(
        f"Evidence rows loaded: {len(evidence)}"
    )

    # ========================================================
    # 2. LOAD GEOGRAPHIC DATA
    # ========================================================

    print(
        "\n[2/6] Loading sensor-factory coordinates..."
    )

    distances = pd.read_parquet(
        DISTANCE_FILE
    )

    print(
        f"Geographic rows loaded: {len(distances)}"
    )

    # ========================================================
    # 3. VALIDATE SCHEMA
    # ========================================================

    print(
        "\n[3/6] Validating schemas..."
    )

    required_evidence_columns = [
        "event_id",
        "station",

        "factory_id",
        "factory_name",

        "factory_rank",

        "peak_pm25",

        "distance_km",

        "wind_direction_mean_deg",
        "wind_speed_mean_mps",

        "wind_relationship",

        "attribution_score",
        "relative_likelihood",

        "confidence_percent",
        "confidence_level",

        "uncertainty_percent",
        "uncertainty_level",

        "investigation_status",
    ]

    required_distance_columns = [
        "sensor",
        "sensor_latitude",
        "sensor_longitude",

        "factory_id",
        "factory_latitude",
        "factory_longitude",
    ]

    missing_evidence = [
        column
        for column in required_evidence_columns
        if column not in evidence.columns
    ]

    missing_distance = [
        column
        for column in required_distance_columns
        if column not in distances.columns
    ]

    if missing_evidence:

        raise ValueError(
            "Missing columns in evidence data: "
            f"{missing_evidence}"
        )

    if missing_distance:

        raise ValueError(
            "Missing columns in distance data: "
            f"{missing_distance}"
        )

    print(
        "Schemas OK."
    )

    # ========================================================
    # 4. MERGE GEOSPATIAL COORDINATES
    # ========================================================

    print(
        "\n[4/6] Joining geographic coordinates..."
    )

    coordinates = distances[
        [
            "sensor",
            "sensor_latitude",
            "sensor_longitude",

            "factory_id",
            "factory_latitude",
            "factory_longitude",
        ]
    ].drop_duplicates(
        subset=[
            "sensor",
            "factory_id"
        ]
    )

    geospatial = evidence.merge(
        coordinates,
        left_on=[
            "station",
            "factory_id"
        ],
        right_on=[
            "sensor",
            "factory_id"
        ],
        how="left"
    )

    # Remove duplicate sensor field after merge.
    if "sensor" in geospatial.columns:
        geospatial = geospatial.drop(
            columns=["sensor"]
        )

    # ========================================================
    # COORDINATE VALIDATION
    # ========================================================

    coordinate_columns = [
        "sensor_latitude",
        "sensor_longitude",
        "factory_latitude",
        "factory_longitude",
    ]

    missing_coordinate_rows = (
        geospatial[
            coordinate_columns
        ]
        .isna()
        .any(axis=1)
        .sum()
    )

    print(
        f"Rows without complete coordinates: "
        f"{missing_coordinate_rows}"
    )

    if missing_coordinate_rows > 0:

        print(
            "WARNING: Some map features have incomplete "
            "coordinates."
        )

    # ========================================================
    # 5. CREATE MAP-READY FIELDS
    # ========================================================

    print(
        "\n[5/6] Creating map-ready evidence fields..."
    )

    # --------------------------------------------------------
    # Candidate type
    # --------------------------------------------------------

    geospatial[
        "map_feature_type"
    ] = "factory_candidate"

    # --------------------------------------------------------
    # Candidate priority
    # --------------------------------------------------------

    def candidate_priority(rank):

        if rank == 1:
            return "primary_candidate"

        if rank == 2:
            return "secondary_candidate"

        if rank == 3:
            return "tertiary_candidate"

        return "supporting_candidate"

    geospatial[
        "candidate_priority"
    ] = geospatial[
        "factory_rank"
    ].apply(
        candidate_priority
    )

    # --------------------------------------------------------
    # Confidence display
    # --------------------------------------------------------

    geospatial[
        "confidence_display"
    ] = (
        geospatial[
            "confidence_percent"
        ].round(1).astype(str)
        + "%"
    )

    geospatial[
        "uncertainty_display"
    ] = (
        geospatial[
            "uncertainty_percent"
        ].round(1).astype(str)
        + "%"
    )

    # --------------------------------------------------------
    # Attribution display
    # --------------------------------------------------------

    geospatial[
        "attribution_display"
    ] = (
        geospatial[
            "attribution_score"
        ].round(3)
    )

    # --------------------------------------------------------
    # Distance display
    # --------------------------------------------------------

    geospatial[
        "distance_display"
    ] = (
        geospatial[
            "distance_km"
        ].round(2)
    )

    # --------------------------------------------------------
    # Wind display
    # --------------------------------------------------------

    geospatial[
        "wind_direction_display"
    ] = (
        geospatial[
            "wind_direction_mean_deg"
        ].round(1)
    )

    geospatial[
        "wind_speed_display"
    ] = (
        geospatial[
            "wind_speed_mean_mps"
        ].round(3)
    )

    # --------------------------------------------------------
    # Event intensity
    # --------------------------------------------------------

    geospatial[
        "pollution_intensity"
    ] = np.where(
        geospatial[
            "peak_pm25"
        ] >= 100,
        "very_high",

        np.where(
            geospatial[
                "peak_pm25"
            ] >= 50,
            "high",

            np.where(
                geospatial[
                    "peak_pm25"
                ] >= 35,
                "moderate",
                "elevated"
            )
        )
    )

    # --------------------------------------------------------
    # Wind arrow endpoint
    # --------------------------------------------------------
    #
    # This is a visualization helper.
    #
    # It does NOT represent actual atmospheric plume
    # propagation.

    def calculate_wind_endpoint(
        latitude,
        longitude,
        direction,
        distance_degrees=0.02
    ):

        if (
            pd.isna(latitude)
            or pd.isna(longitude)
            or pd.isna(direction)
        ):

            return pd.Series(
                [np.nan, np.nan]
            )

        direction_rad = np.radians(
            direction
        )

        endpoint_lat = (
            latitude
            +
            distance_degrees
            *
            np.cos(direction_rad)
        )

        longitude_scale = max(
            np.cos(
                np.radians(latitude)
            ),
            0.1
        )

        endpoint_lon = (
            longitude
            +
            (
                distance_degrees
                *
                np.sin(direction_rad)
                /
                longitude_scale
            )
        )

        return pd.Series(
            [
                endpoint_lat,
                endpoint_lon
            ]
        )

    wind_endpoints = geospatial.apply(
        lambda row:
        calculate_wind_endpoint(
            row["sensor_latitude"],
            row["sensor_longitude"],
            row["wind_direction_mean_deg"]
        ),
        axis=1
    )

    wind_endpoints.columns = [
        "wind_arrow_latitude",
        "wind_arrow_longitude"
    ]

    geospatial = pd.concat(
        [
            geospatial,
            wind_endpoints
        ],
        axis=1
    )

    # ========================================================
    # MAP POPUP TEXT
    # ========================================================

    def build_popup(row):

        return (
            f"Event: {row['event_id']} | "
            f"Station: {row['station']} | "
            f"Candidate: {row['factory_name']} | "
            f"Rank: #{row['factory_rank']} | "
            f"Distance: {row['distance_km']:.2f} km | "
            f"Wind: {row['wind_relationship']} | "
            f"Attribution: {row['attribution_score']:.3f} | "
            f"Confidence: {row['confidence_percent']:.1f}% | "
            f"Uncertainty: {row['uncertainty_percent']:.1f}%"
        )

    geospatial[
        "map_popup"
    ] = geospatial.apply(
        build_popup,
        axis=1
    )

    # ========================================================
    # FINAL OUTPUT COLUMNS
    # ========================================================

    output_columns = [
        "event_id",
        "station",

        "sensor_latitude",
        "sensor_longitude",

        "factory_id",
        "factory_name",

        "factory_latitude",
        "factory_longitude",

        "factory_rank",
        "candidate_priority",

        "peak_pm25",
        "pollution_intensity",

        "distance_km",
        "distance_display",

        "wind_direction_mean_deg",
        "wind_speed_mean_mps",

        "wind_direction_display",
        "wind_speed_display",

        "wind_relationship",

        "wind_arrow_latitude",
        "wind_arrow_longitude",

        "attribution_score",
        "attribution_display",
        "relative_likelihood",

        "confidence_percent",
        "confidence_display",
        "confidence_level",

        "uncertainty_percent",
        "uncertainty_display",
        "uncertainty_level",

        "investigation_status",

        "map_feature_type",

        "map_popup",
    ]

    # Make sure all requested columns exist.
    missing_output = [
        column
        for column in output_columns
        if column not in geospatial.columns
    ]

    if missing_output:

        raise ValueError(
            "Missing output columns: "
            f"{missing_output}"
        )

    result = geospatial[
        output_columns
    ].copy()

    # ========================================================
    # SAVE
    # ========================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_parquet(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print(
        "\n[6/6] Geospatial evidence layer completed."
    )

    print(
        "\n" + "-" * 70
    )

    print(
        "GEOSPATIAL SUMMARY"
    )

    print(
        "-" * 70
    )

    print(
        f"Rows: {len(result)}"
    )

    print(
        f"Events: "
        f"{result['event_id'].nunique()}"
    )

    print(
        f"Stations: "
        f"{result['station'].nunique()}"
    )

    print(
        f"Factories: "
        f"{result['factory_id'].nunique()}"
    )

    print(
        f"Primary candidates: "
        f"{(
            result['factory_rank'] == 1
        ).sum()}"
    )

    print(
        f"Rows with complete coordinates: "
        f"{(
            ~result[
                [
                    'sensor_latitude',
                    'sensor_longitude',
                    'factory_latitude',
                    'factory_longitude'
                ]
            ].isna().any(axis=1)
        ).sum()}"
    )

    print(
        "\nSample map-ready records:"
    )

    sample_columns = [
        "event_id",
        "station",
        "factory_name",
        "factory_rank",
        "distance_km",
        "wind_relationship",
        "attribution_score",
        "confidence_percent",
        "uncertainty_percent",
    ]

    print(
        result[
            sample_columns
        ]
        .head(10)
        .to_string(
            index=False
        )
    )

    print(
        "\nOutput:"
    )

    print(
        OUTPUT_FILE
    )

    print(
        "\nNOTE:"
    )

    print(
        "Wind arrow coordinates are visualization helpers "
        "for the observed wind direction. They are NOT "
        "an atmospheric plume simulation."
    )

    print("=" * 70)
    print(
        "AIR KAVACH GEOSPATIAL EVIDENCE READY"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()