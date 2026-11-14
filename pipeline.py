
# ============================================================
# FIREWATCH INDIA - DISTRICT-WISE DATA PROCESSING PIPELINE
# MODIS + VIIRS | Uttarakhand | 2012-2026
# ============================================================

import re
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

# ============================================================
# 1. PROJECT PATHS AND SETTINGS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = Path(
    r"C:\Users\razam\OneDrive\Desktop\Dataset"
)

OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BOUNDARY_DIR = BASE_DIR / "boundaries"
BOUNDARY_DIR.mkdir(parents=True, exist_ok=True)

BOUNDARY_FILE = BOUNDARY_DIR / "uttarakhand_districts.geojson"

MODIS_FILE = DATA_DIR / "MODIS_Exact_Uttarakhand.csv"
VIIRS_FILE = DATA_DIR / "VIIRS_Exact_Uttarakhand.csv"

GRID_SIZE = 0.01
START_DATE = "2012-01-01"
END_DATE = "2026-12-31"

DISTRICTS = [
    "Almora",
    "Bageshwar",
    "Chamoli",
    "Champawat",
    "Dehradun",
    "Haridwar",
    "Nainital",
    "Pauri Garhwal",
    "Pithoragarh",
    "Rudraprayag",
    "Tehri Garhwal",
    "Udham Singh Nagar",
    "Uttarkashi"
]

# ============================================================
# 2. DOWNLOAD BOUNDARY FILE IF NOT AVAILABLE
# ============================================================

if not BOUNDARY_FILE.exists():

    print("\nDistrict boundary file not found.")
    print("Downloading Uttarakhand GeoJSON...")

    GEOJSON_URL = (
        "https://raw.githubusercontent.com/"
        "satdixit/india-shapefiles/master/"
        "STATES/UTTARAKHAND/"
        "UTTARAKHAND_DISTRICTS.geojson"
    )

    try:
        urllib.request.urlretrieve(
            GEOJSON_URL,
            BOUNDARY_FILE
        )

        print("Boundary file downloaded successfully!")

    except Exception as exc:
        raise RuntimeError(
            "Boundary download failed. "
            "Check your internet connection."
        ) from exc

print("Boundary file:", BOUNDARY_FILE)

# ============================================================
# 3. CHECK REQUIRED FILES AND LIBRARIES
# ============================================================

for file in [MODIS_FILE, VIIRS_FILE, BOUNDARY_FILE]:

    if not file.exists():
        raise FileNotFoundError(
            f"Required file not found: {file}"
        )

try:
    import geopandas as gpd

except ImportError:
    raise ImportError(
        "Install GeoPandas using:\n"
        "python -m pip install geopandas shapely"
    )

# ============================================================
# 4. LOAD DISTRICT BOUNDARIES
# ============================================================

print("\nSTEP 1: LOADING DISTRICT BOUNDARIES")

boundaries = gpd.read_file(BOUNDARY_FILE)

if boundaries.crs is None:
    raise ValueError(
        "District boundary file has no CRS information."
    )

boundaries = boundaries.to_crs("EPSG:4326")

name_candidates = [
    "district",
    "DISTRICT",
    "District",
    "NAME_2",
    "NAME",
    "DTNAME",
    "dtname",
    "DIST_NAME"
]

DISTRICT_FIELD = next(
    (
        col for col in name_candidates
        if col in boundaries.columns
    ),
    None
)

if DISTRICT_FIELD is None:
    raise ValueError(
        "District name column not found.\n"
        f"Available columns: {list(boundaries.columns)}"
    )


def normalize_district(value):

    if pd.isna(value):
        return None

    value = re.sub(
        r"\s+",
        " ",
        str(value).strip()
    ).lower()

    # Correct names according to the downloaded GeoJSON
    aliases = {
        "hardwar": "Haridwar",
        "haridwar": "Haridwar",

        "garhwal": "Pauri Garhwal",
        "pauri": "Pauri Garhwal",
        "pauri garhwal": "Pauri Garhwal",

        "tehri": "Tehri Garhwal",
        "tehri garhwal": "Tehri Garhwal",

        "udham singh nagar": "Udham Singh Nagar",
        "us nagar": "Udham Singh Nagar",
        "u s nagar": "Udham Singh Nagar"
    }

    if value in aliases:
        return aliases[value]

    for district in DISTRICTS:

        if value == district.lower():
            return district

    return value.title()


boundaries["district"] = (
    boundaries[DISTRICT_FIELD]
    .apply(normalize_district)
)

boundaries = boundaries[
    boundaries["district"].isin(DISTRICTS)
].copy()

# Combine duplicate boundary features by district
boundaries = boundaries[
    ["district", "geometry"]
].dissolve(
    by="district",
    as_index=False
)

missing = sorted(
    set(DISTRICTS) -
    set(boundaries["district"].unique())
)

if missing:

    raise ValueError(
        f"Missing districts in boundary file: {missing}\n"
        f"Districts found: {sorted(boundaries['district'].unique())}"
    )

print("District boundaries loaded:", len(boundaries))

print(
    "Districts:",
    ", ".join(sorted(boundaries["district"].unique()))
)

# ============================================================
# 5. LOAD NASA MODIS AND VIIRS DATA
# ============================================================

print("\nSTEP 2: LOADING NASA DATASETS")

modis = pd.read_csv(
    MODIS_FILE,
    dtype={"version": "string"},
    low_memory=False
)

viirs = pd.read_csv(
    VIIRS_FILE,
    dtype={"version": "string"},
    low_memory=False
)

print("MODIS loaded:", modis.shape)
print("VIIRS loaded:", viirs.shape)

# ============================================================
# 6. DATA CLEANING
# ============================================================

def clean_data(df, sensor):

    df = df.copy()

    required = [
        "latitude",
        "longitude",
        "acq_date",
        "confidence",
        "frp"
    ]

    missing_columns = [
        col for col in required
        if col not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            f"{sensor} missing columns: {missing_columns}"
        )

    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce"
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce"
    )

    df["acq_date"] = pd.to_datetime(
        df["acq_date"],
        errors="coerce"
    )

    df["frp"] = pd.to_numeric(
        df["frp"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "latitude",
            "longitude",
            "acq_date"
        ]
    ).copy()

    df = df[
        df["latitude"].between(-90, 90)
        &
        df["longitude"].between(-180, 180)
        &
        df["acq_date"].between(
            START_DATE,
            END_DATE
        )
    ].copy()

    numeric_cols = [
        "brightness",
        "scan",
        "track",
        "bright_t31",
        "acq_time"
    ]

    for col in numeric_cols:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    df["confidence_original"] = (
        df["confidence"].astype("string")
    )

    if sensor == "MODIS":

        confidence = pd.to_numeric(
            df["confidence"],
            errors="coerce"
        )

        df["confidence_level"] = np.select(
            [
                confidence <= 30,

                (confidence > 30)
                & (confidence <= 80),

                confidence > 80
            ],
            [
                "low",
                "nominal",
                "high"
            ],
            default="unknown"
        )

    else:

        confidence = (
            df["confidence"]
            .astype("string")
            .str.lower()
            .str.strip()
        )

        df["confidence_level"] = (
            confidence.map({
                "l": "low",
                "n": "nominal",
                "h": "high"
            }).fillna("unknown")
        )

    df["sensor_source"] = sensor

    df = df.drop_duplicates()

    return df


modis = clean_data(modis, "MODIS")
viirs = clean_data(viirs, "VIIRS")

print("Clean MODIS:", modis.shape)
print("Clean VIIRS:", viirs.shape)

if modis.empty or viirs.empty:

    raise ValueError(
        "One of the cleaned datasets is empty. "
        "Check source CSV files and date range."
    )

# ============================================================
# 7. ASSIGN HOTSPOTS TO DISTRICTS
# ============================================================

print("\nSTEP 3: DISTRICT-WISE SPATIAL MATCHING")


def assign_districts(df, sensor):

    points = gpd.GeoDataFrame(
        df.copy(),

        geometry=gpd.points_from_xy(
            df["longitude"],
            df["latitude"]
        ),

        crs="EPSG:4326"
    )

    joined = gpd.sjoin(
        points,

        boundaries[
            ["district", "geometry"]
        ],

        how="left",

        predicate="intersects"
    )

    joined = joined.drop(
        columns=["index_right"],
        errors="ignore"
    )

    outside = joined["district"].isna().sum()

    print(
        f"{sensor} points outside districts: {outside:,}"
    )

    joined = joined.dropna(
        subset=["district"]
    ).copy()

    joined = pd.DataFrame(
        joined.drop(columns=["geometry"])
    )

    return joined


modis = assign_districts(modis, "MODIS")
viirs = assign_districts(viirs, "VIIRS")

print("MODIS district observations:", len(modis))
print("VIIRS district observations:", len(viirs))

if modis.empty or viirs.empty:

    raise ValueError(
        "No observations were assigned to districts. "
        "Check coordinates and boundary CRS."
    )

# ============================================================
# 8. CREATE COMMON SPATIAL GRID
# ============================================================

print("\nSTEP 4: CREATING COMMON GRID")


def create_grid(df):

    df = df.copy()

    df["grid_lat"] = (
        np.floor(
            df["latitude"] / GRID_SIZE
        ) * GRID_SIZE
    ).round(6)

    df["grid_lon"] = (
        np.floor(
            df["longitude"] / GRID_SIZE
        ) * GRID_SIZE
    ).round(6)

    return df


modis = create_grid(modis)
viirs = create_grid(viirs)

# ============================================================
# 9. CALCULATE DAILY ACTIVE GRID-DAYS
# ============================================================

print("\nSTEP 5: CALCULATING DAILY ACTIVITY")


def calculate_active_grid_days(df):

    result = (
        df.groupby(
            [
                "district",
                "grid_lat",
                "grid_lon",
                "acq_date",
                "sensor_source"
            ],
            as_index=False
        )
        .agg(
            hotspot_count=("latitude", "size"),
            mean_frp=("frp", "mean")
        )
    )

    # One unique grid + date + sensor = one active grid-day
    result["burning_day"] = 1

    return result


modis_days = calculate_active_grid_days(modis)
viirs_days = calculate_active_grid_days(viirs)

print("MODIS active grid-days:", len(modis_days))
print("VIIRS active grid-days:", len(viirs_days))

# ============================================================
# 10. CALCULATE WEEKLY DISTRICT ACTIVITY
# ============================================================

print("\nSTEP 6: CALCULATING WEEKLY ACTIVITY")


def weekly_activity(df, sensor):

    df = df.copy()

    iso = df["acq_date"].dt.isocalendar()

    df["year"] = iso.year.astype(int)
    df["week"] = iso.week.astype(int)

    weekly = (
        df.groupby(
            [
                "district",
                "year",
                "week"
            ],
            as_index=False
        )
        .agg(
            burning_day=("burning_day", "sum"),
            hotspot_count=("hotspot_count", "sum"),
            mean_frp=("mean_frp", "mean")
        )
    )

    weekly = weekly.rename(
        columns={
            "burning_day": f"{sensor.lower()}_activity",

            "hotspot_count": f"{sensor.lower()}_hotspots",

            "mean_frp": f"{sensor.lower()}_mean_frp"
        }
    )

    return weekly


modis_weekly = weekly_activity(
    modis_days,
    "MODIS"
)

viirs_weekly = weekly_activity(
    viirs_days,
    "VIIRS"
)

print("MODIS weekly records:", len(modis_weekly))
print("VIIRS weekly records:", len(viirs_weekly))

# ============================================================
# 11. SENSOR OVERLAP COMPARISON AND CALIBRATION
# ============================================================

print("\nSTEP 7: SENSOR OVERLAP COMPARISON")

comparison = pd.merge(
    modis_weekly,
    viirs_weekly,

    on=[
        "district",
        "year",
        "week"
    ],

    how="inner"
)

valid = comparison[
    (comparison["modis_activity"] > 0)
    &
    (comparison["viirs_activity"] > 0)
].copy()

if valid.empty:

    raise ValueError(
        "No common active district-weeks found. "
        "Check date coverage and district matching."
    )

valid["ratio"] = (
    valid["modis_activity"]
    /
    valid["viirs_activity"]
)

calibration = (
    valid.groupby("district")["ratio"]
    .median()
    .rename("calibration_factor")
    .reset_index()
)

print("District calibration factors:")

print(
    calibration.to_string(index=False)
)

# ============================================================
# 12. HARMONIZE DISTRICT-WISE WEEKLY DATA
# ============================================================

print("\nSTEP 8: HARMONIZING DATA")

all_weeks = pd.merge(
    modis_weekly,
    viirs_weekly,

    on=[
        "district",
        "year",
        "week"
    ],

    how="outer"
)

all_weeks = all_weeks.merge(
    calibration,
    on="district",
    how="left"
)

# Convert VIIRS activity to MODIS-equivalent scale
all_weeks["viirs_adjusted"] = (
    all_weeks["viirs_activity"]
    *
    all_weeks["calibration_factor"]
)

both_sensors = (
    all_weeks["modis_activity"].notna()
    &
    all_weeks["viirs_adjusted"].notna()
)

only_modis = (
    all_weeks["modis_activity"].notna()
    &
    all_weeks["viirs_adjusted"].isna()
)

only_viirs = (
    all_weeks["modis_activity"].isna()
    &
    all_weeks["viirs_adjusted"].notna()
)

all_weeks["harmonized_activity"] = np.nan

all_weeks.loc[
    both_sensors,
    "harmonized_activity"
] = (
    all_weeks.loc[
        both_sensors,
        "modis_activity"
    ]
    +
    all_weeks.loc[
        both_sensors,
        "viirs_adjusted"
    ]
) / 2

all_weeks.loc[
    only_modis,
    "harmonized_activity"
] = all_weeks.loc[
    only_modis,
    "modis_activity"
]

all_weeks.loc[
    only_viirs,
    "harmonized_activity"
] = all_weeks.loc[
    only_viirs,
    "viirs_adjusted"
]

all_weeks = all_weeks.sort_values(
    [
        "district",
        "year",
        "week"
    ]
).reset_index(drop=True)

# Show which sensor contributed to each weekly record
all_weeks["sensor_availability"] = np.select(
    [
        all_weeks["modis_activity"].notna()
        & all_weeks["viirs_activity"].notna(),

        all_weeks["modis_activity"].notna(),

        all_weeks["viirs_activity"].notna()
    ],
    [
        "MODIS + VIIRS",
        "MODIS only",
        "VIIRS only"
    ],
    default="No sensor data"
)

# ============================================================
# 13. DISTRICT-WISE HISTORICAL BASELINE AND ANOMALIES
# ============================================================

print("\nSTEP 9: HISTORICAL BASELINE AND ANOMALIES")

baseline = (
    all_weeks.groupby(
        [
            "district",
            "week"
        ]
    )["harmonized_activity"]
    .agg(
        historical_median="median",

        historical_q1=lambda x: x.quantile(0.25),

        historical_q3=lambda x: x.quantile(0.75)
    )
    .reset_index()
)

all_weeks = all_weeks.merge(
    baseline,

    on=[
        "district",
        "week"
    ],

    how="left"
)

all_weeks["anomaly_percent"] = np.where(
    all_weeks["historical_median"] > 0,

    (
        (
            all_weeks["harmonized_activity"]
            -
            all_weeks["historical_median"]
        )
        /
        all_weeks["historical_median"]
    ) * 100,

    np.nan
)

iqr = (
    all_weeks["historical_q3"]
    -
    all_weeks["historical_q1"]
)

upper_threshold = (
    all_weeks["historical_q3"]
    +
    1.5 * iqr
)

all_weeks["status"] = np.where(
    all_weeks["harmonized_activity"].notna()
    &
    (
        all_weeks["harmonized_activity"]
        >
        upper_threshold
    ),

    "Unusual",

    "Normal"
)

# ============================================================
# 14. SAVE OUTPUT FILES
# ============================================================

print("\nSTEP 10: SAVING OUTPUT FILES")

modis.to_csv(
    OUTPUT_DIR / "MODIS_Cleaned_Districts_2012_2026.csv",
    index=False
)

viirs.to_csv(
    OUTPUT_DIR / "VIIRS_Cleaned_Districts_2012_2026.csv",
    index=False
)

modis_days.to_csv(
    OUTPUT_DIR / "MODIS_Daily_District_Activity.csv",
    index=False
)

viirs_days.to_csv(
    OUTPUT_DIR / "VIIRS_Daily_District_Activity.csv",
    index=False
)

all_weeks.to_csv(
    OUTPUT_DIR / "Harmonized_Weekly_Activity.csv",
    index=False
)

comparison.to_csv(
    OUTPUT_DIR / "District_Sensor_Overlap_Comparison.csv",
    index=False
)

# District summary
district_summary = (
    all_weeks.groupby("district")
    .agg(
        weekly_records=(
            "harmonized_activity",
            "count"
        ),

        total_harmonized_activity=(
            "harmonized_activity",
            "sum"
        ),

        unusual_weeks=(
            "status",
            lambda x: (x == "Unusual").sum()
        )
    )
    .reset_index()
)

district_summary.to_csv(
    OUTPUT_DIR / "District_Summary.csv",
    index=False
)

# ============================================================
# 15. FINAL REPORT
# ============================================================

print("\n==========================================")
print("FIREWATCH INDIA PIPELINE COMPLETED")
print("==========================================")

print("MODIS observations:", len(modis))
print("VIIRS observations:", len(viirs))

print(
    "MODIS weekly records:",
    len(modis_weekly)
)

print(
    "VIIRS weekly records:",
    len(viirs_weekly)
)

print(
    "Harmonized weekly records:",
    len(all_weeks)
)

print(
    "Districts represented:",
    all_weeks["district"].nunique()
)

print("\nDISTRICT SUMMARY:")

print(
    district_summary.to_string(index=False)
)

print("\nOUTPUT DIRECTORY:")
print(OUTPUT_DIR)

print("\nALL OUTPUT FILES SAVED SUCCESSFULLY!")

print(
    "\nNOTE: This is a research prototype. "
    "Sensor calibration, observation coverage, satellite overpass "
    "differences, grid-area variation and historical boundary changes "
    "require further validation. Hotspot activity is not the same as "
    "fire count or burned area."
)
