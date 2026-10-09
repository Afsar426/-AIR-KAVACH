import os
import pandas as pd


DATA_DIR = "data/raw/air_quality/openaq"

FILES = {
    "Residency": "residency_pm25.csv",
    "Regional Park": "regional_park_pm25.csv",
    "Airport": "airport_pm25.csv",
    "Maguda": "maguda_pm25.csv",
}


def check_file(name, filename):

    print("\n" + "=" * 75)
    print(f"DATA QUALITY CHECK: {name}")
    print("=" * 75)

    path = os.path.join(DATA_DIR, filename)

    if not os.path.exists(path):
        print("File not found:", path)
        return

    df = pd.read_csv(path)

    print("\nRows:", len(df))
    print("Columns:")
    print(df.columns.tolist())

    print("\nFirst 3 records:")
    print(df.head(3).to_string())

    # -----------------------------------------------------
    # Find timestamp column
    # -----------------------------------------------------

    timestamp_columns = [
        "period.datetimeFrom.utc",
        "period.datetimeTo.utc",
        "datetime.utc",
        "date.utc",
    ]

    timestamp_column = None

    for column in timestamp_columns:
        if column in df.columns:
            timestamp_column = column
            break

    if timestamp_column:

        df[timestamp_column] = pd.to_datetime(
            df[timestamp_column],
            errors="coerce",
            utc=True
        )

        print("\nTimestamp column:", timestamp_column)
        print("First timestamp:", df[timestamp_column].min())
        print("Last timestamp:", df[timestamp_column].max())

        print(
            "Invalid timestamps:",
            df[timestamp_column].isna().sum()
        )

    else:

        print("\nWARNING: Timestamp column not automatically detected.")

    # -----------------------------------------------------
    # Find PM2.5 value column
    # -----------------------------------------------------

    value_column = None

    possible_columns = [
        "value",
        "measurements.value",
        "result",
    ]

    for column in possible_columns:
        if column in df.columns:
            value_column = column
            break

    if value_column:

        df[value_column] = pd.to_numeric(
            df[value_column],
            errors="coerce"
        )

        print("\nPM2.5 value column:", value_column)

        print("Missing values:", df[value_column].isna().sum())

        print(
            "Negative values:",
            (df[value_column] < 0).sum()
        )

        print("Minimum:", df[value_column].min())
        print("Maximum:", df[value_column].max())
        print("Mean:", round(df[value_column].mean(), 2))
        print("Median:", round(df[value_column].median(), 2))

    else:

        print("\nWARNING: PM2.5 value column not detected.")

    # -----------------------------------------------------
    # Duplicate check
    # -----------------------------------------------------

    print("\nDuplicate rows:", df.duplicated().sum())

    # -----------------------------------------------------
    # Missing values
    # -----------------------------------------------------

    print("\nMissing values by column:")

    missing = df.isna().sum()

    print(
        missing[missing > 0].sort_values(
            ascending=False
        ).to_string()
        if (missing > 0).any()
        else "No missing values."
    )


# ---------------------------------------------------------
# Run checks
# ---------------------------------------------------------

for name, filename in FILES.items():

    check_file(
        name,
        filename
    )


print("\n" + "=" * 75)
print("AIR KAVACH - DATA QUALITY CHECK COMPLETED")
print("=" * 75)