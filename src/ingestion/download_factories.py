import os
import requests
import pandas as pd


# =========================================================
# AIR KAVACH
# Industrial Facility Data Downloader
# Source: OpenStreetMap via Overpass API
# =========================================================

OUTPUT_DIR = "data/raw/factories"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================================================
# REGION
# Indore + Pithampur region
#
# Later these values can be changed for any region.
# =========================================================

SOUTH = 22.45
WEST = 75.55
NORTH = 22.90
EAST = 76.10


# =========================================================
# OVERPASS SERVERS
# =========================================================

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


# =========================================================
# USER AGENT
# =========================================================

HEADERS = {
    "User-Agent": (
        "AIR-KAVACH/1.0 "
        "(industrial pollution source attribution research)"
    ),
    "Accept": "application/json",
}


# =========================================================
# OVERPASS QUERY
#
# We collect mapped industrial works/facilities.
# =========================================================

query = f"""
[out:json][timeout:120];

(
    nwr["man_made"="works"]({SOUTH},{WEST},{NORTH},{EAST});
    nwr["industrial"]({SOUTH},{WEST},{NORTH},{EAST});
);

out center tags;
"""


# =========================================================
# DOWNLOAD
# =========================================================

data = None

for url in OVERPASS_URLS:

    print("=" * 70)
    print("Trying Overpass server:")
    print(url)

    try:

        response = requests.get(
            url,
            params={
                "data": query
            },
            headers=HEADERS,
            timeout=180
        )

        print("Status:", response.status_code)

        if response.ok:

            data = response.json()

            print("Overpass request successful.")

            break

        else:

            print("Server returned an error:")
            print(response.text[:500])

    except requests.RequestException as error:

        print("Connection error:")
        print(error)


# =========================================================
# CHECK RESULT
# =========================================================

if data is None:

    raise RuntimeError(
        "Could not retrieve OpenStreetMap data "
        "from available Overpass servers."
    )


# =========================================================
# READ ELEMENTS
# =========================================================

elements = data.get(
    "elements",
    []
)

print("\nOSM elements received:", len(elements))


# =========================================================
# PROCESS FACILITIES
# =========================================================

factories = []


for element in elements:

    tags = element.get(
        "tags",
        {}
    )


    # -----------------------------------------------------
    # Coordinates
    # -----------------------------------------------------

    latitude = element.get("lat")
    longitude = element.get("lon")


    # Ways / relations
    if latitude is None or longitude is None:

        center = element.get(
            "center",
            {}
        )

        latitude = center.get("lat")
        longitude = center.get("lon")


    # Skip records without coordinates
    if latitude is None or longitude is None:

        continue


    # -----------------------------------------------------
    # OSM identity
    # -----------------------------------------------------

    osm_type = element.get(
        "type"
    )

    osm_id = element.get(
        "id"
    )

    factory_id = (
        f"OSM-{osm_type}-{osm_id}"
    )


    # -----------------------------------------------------
    # Facility name
    # -----------------------------------------------------

    factory_name = (
        tags.get("name")
        or tags.get("official_name")
        or tags.get("brand")
        or "Unnamed Facility"
    )


    # -----------------------------------------------------
    # Industry type
    # -----------------------------------------------------

    industry_type = (
        tags.get("industrial")
        or tags.get("craft")
        or tags.get("man_made")
        or "unknown"
    )


    # -----------------------------------------------------
    # Additional metadata
    # -----------------------------------------------------

    operator = tags.get(
        "operator"
    )

    website = tags.get(
        "website"
    )


    # -----------------------------------------------------
    # Create record
    # -----------------------------------------------------

    factories.append(
        {
            "factory_id": factory_id,
            "factory_name": factory_name,
            "industry_type": industry_type,
            "latitude": latitude,
            "longitude": longitude,
            "operator": operator,
            "website": website,
            "osm_type": osm_type,
            "osm_id": osm_id,
            "source": "OpenStreetMap",
        }
    )


# =========================================================
# DATAFRAME
# =========================================================

df = pd.DataFrame(
    factories
)


if df.empty:

    raise RuntimeError(
        "No industrial facilities were found "
        "in the selected region."
    )


# =========================================================
# REMOVE DUPLICATES
# =========================================================

df = df.drop_duplicates(
    subset=[
        "factory_id"
    ]
)


# =========================================================
# VALIDATE COORDINATES
# =========================================================

df = df[
    df["latitude"].between(
        -90,
        90
    )
    &
    df["longitude"].between(
        -180,
        180
    )
]


# =========================================================
# SORT
# =========================================================

df = df.sort_values(
    [
        "industry_type",
        "factory_name"
    ]
).reset_index(
    drop=True
)


# =========================================================
# SAVE
# =========================================================

output_file = os.path.join(
    OUTPUT_DIR,
    "factories_osm.csv"
)

df.to_csv(
    output_file,
    index=False
)


# =========================================================
# SUMMARY
# =========================================================

print("\n" + "=" * 70)
print("AIR KAVACH - INDUSTRIAL FACILITY DATA")
print("=" * 70)

print(
    "Total facilities:",
    len(df)
)


print("\nIndustry types:")

print(
    df["industry_type"]
    .value_counts()
    .head(20)
    .to_string()
)


print("\nNamed facilities:")

named = df[
    df["factory_name"]
    != "Unnamed Facility"
]


print(
    named[
        [
            "factory_id",
            "factory_name",
            "industry_type",
            "latitude",
            "longitude"
        ]
    ]
    .head(20)
    .to_string(
        index=False
    )
)


print("\nSaved to:")

print(
    output_file
)


print(
    "\nFactory data download completed."
)