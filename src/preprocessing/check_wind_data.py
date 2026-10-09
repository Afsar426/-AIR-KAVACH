import ast
import pandas as pd
from pathlib import Path


DATA_DIR = Path("data/raw/weather/openaq")


FILES = [
    "residency_wind_direction.csv",
    "residency_wind_speed.csv",
    "regional_park_wind_direction.csv",
    "regional_park_wind_speed.csv",
    "airport_wind_direction.csv",
    "airport_wind_speed.csv",
    "maguda_wind_direction.csv",
]


print("=" * 70)
print("AIR KAVACH - WIND DATA QUALITY CHECK")
print("=" * 70)


for filename in FILES:

    path = DATA_DIR / filename

    if not path.exists():
        print(f"\nMISSING: {filename}")
        continue

    df = pd.read_csv(path)

    print("\n" + "-" * 70)
    print(filename)
    print("-" * 70)

    print("Rows:", len(df))

    # -----------------------------------------------------
    # Extract timestamps from OpenAQ period
    # -----------------------------------------------------

    def extract_start(period_text):

        try:
            period = ast.literal_eval(period_text)

            return period["datetimeFrom"]["utc"]

        except Exception:
            return None

    def extract_end(period_text):

        try:
            period = ast.literal_eval(period_text)

            return period["datetimeTo"]["utc"]

        except Exception:
            return None

    start_times = df["period"].apply(
        extract_start
    )

    end_times = df["period"].apply(
        extract_end
    )

    start_times = pd.to_datetime(
        start_times,
        errors="coerce",
        utc=True,
    )

    end_times = pd.to_datetime(
        end_times,
        errors="coerce",
        utc=True,
    )

    print("\nTimestamp range:")
    print("Start:", start_times.min())
    print("End:  ", end_times.max())

    print(
        "Missing timestamps:",
        start_times.isna().sum(),
    )

    print(
        "Duplicate timestamps:",
        start_times.duplicated().sum(),
    )

    # -----------------------------------------------------
    # Measurement
    # -----------------------------------------------------

    values = pd.to_numeric(
        df["value"],
        errors="coerce",
    )

    print("\nMeasurement statistics:")
    print("Min:", values.min())
    print("Max:", values.max())
    print("Mean:", round(values.mean(), 3))
    print("Missing:", values.isna().sum())

    # -----------------------------------------------------
    # Direction validation
    # -----------------------------------------------------

    if "direction" in filename:

        invalid = (
            (values < 0)
            | (values > 360)
        ).sum()

        print(
            "Invalid wind directions:",
            invalid,
        )

    # -----------------------------------------------------
    # Speed validation
    # -----------------------------------------------------

    if "speed" in filename:

        negative = (
            values < 0
        ).sum()

        print(
            "Negative wind speeds:",
            negative,
        )

    # -----------------------------------------------------
    # Sample
    # -----------------------------------------------------

    sample = pd.DataFrame(
        {
            "timestamp": start_times,
            "value": values,
        }
    )

    print("\nFirst 3 observations:")
    print(
        sample.head(3)
        .to_string(index=False)
    )

    print("\nLast 3 observations:")
    print(
        sample.tail(3)
        .to_string(index=False)
    )


print("\n" + "=" * 70)
print("WIND DATA QUALITY CHECK COMPLETED")
print("=" * 70)
