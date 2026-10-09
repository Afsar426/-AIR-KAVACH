import pandas as pd
from pathlib import Path


INPUT_FILE = Path("data/raw/factories/factories_osm.csv")
OUTPUT_FILE = Path("data/processed/factories/factories_clean.parquet")


# ---------------------------------------------------------
# Load
# ---------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print("=" * 70)
print("AIR KAVACH - FACTORY DATA CLEANING")
print("=" * 70)

print(f"Raw facilities: {len(df)}")


# ---------------------------------------------------------
# Coordinate validation
# ---------------------------------------------------------

df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

valid_coordinates = (
    df["latitude"].between(-90, 90)
    & df["longitude"].between(-180, 180)
)

df = df[valid_coordinates].copy()

print(f"After coordinate validation: {len(df)}")


# ---------------------------------------------------------
# Normalize factory names
# ---------------------------------------------------------

df["factory_name"] = (
    df["factory_name"]
    .fillna("")
    .astype(str)
    .str.strip()
)

unnamed_mask = (
    df["factory_name"].eq("")
    | df["factory_name"].str.lower().eq("nan")
    | df["factory_name"].str.lower().eq("unnamed facility")
)

df.loc[unnamed_mask, "factory_name"] = "Unnamed Industrial Facility"


# ---------------------------------------------------------
# Normalize industry type
# ---------------------------------------------------------

df["industry_type"] = (
    df["industry_type"]
    .fillna("unknown")
    .astype(str)
    .str.lower()
    .str.strip()
)


# ---------------------------------------------------------
# Remove obvious non-industrial records
# ---------------------------------------------------------

exclude_keywords = [
    "cemetry",
    "cemetery",
    "office",
]

name_text = df["factory_name"].str.lower()

exclude_mask = name_text.str.contains(
    "|".join(exclude_keywords),
    regex=True,
    na=False,
)

excluded = df[exclude_mask].copy()

df = df[~exclude_mask].copy()

print(f"Excluded obvious non-industrial records: {len(excluded)}")

if len(excluded) > 0:
    print("\nExcluded:")
    print(
        excluded[
            ["factory_name", "industry_type", "latitude", "longitude"]
        ].to_string(index=False)
    )


# ---------------------------------------------------------
# Classify facility
# ---------------------------------------------------------

def classify_facility(row):

    name = row["factory_name"].lower()
    industry = row["industry_type"].lower()

    if "petro" in name or "chemical" in name:
        return "chemical"

    if "steel" in name or "metal" in name:
        return "metal"

    if "textile" in name or "textiles" in name:
        return "textile"

    if "food" in name or "nutrition" in name:
        return "food"

    if "depot" in name or industry == "depot":
        return "depot"

    if industry == "works":
        return "industrial_works"

    return "unknown"


df["facility_category"] = df.apply(classify_facility, axis=1)


# ---------------------------------------------------------
# Source eligibility
# ---------------------------------------------------------

# Depot is retained as contextual infrastructure,
# but is NOT treated as a primary industrial source.

df["source_candidate"] = df["facility_category"].isin(
    [
        "chemical",
        "metal",
        "textile",
        "food",
        "industrial_works",
    ]
)


# ---------------------------------------------------------
# Remove duplicate facility IDs
# ---------------------------------------------------------

df = df.drop_duplicates(
    subset=["factory_id"],
    keep="first",
)


# ---------------------------------------------------------
# Sort
# ---------------------------------------------------------

df = df.sort_values(
    by=["source_candidate", "facility_category", "factory_name"],
    ascending=[False, True, True],
).reset_index(drop=True)


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

df.to_parquet(
    OUTPUT_FILE,
    index=False,
)


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("CLEAN FACTORY DATASET")
print("=" * 70)

print(f"Final facilities: {len(df)}")

print("\nFacility categories:")

print(
    df["facility_category"]
    .value_counts()
    .to_string()
)

print("\nSource candidates:")

print(
    df["source_candidate"]
    .value_counts()
    .to_string()
)

print("\nIndustrial source candidates:")

print(
    df[df["source_candidate"]][
        [
            "factory_id",
            "factory_name",
            "facility_category",
            "latitude",
            "longitude",
        ]
    ].to_string(index=False)
)

print("\nSaved to:")
print(OUTPUT_FILE)

print("\nFactory cleaning completed successfully.")