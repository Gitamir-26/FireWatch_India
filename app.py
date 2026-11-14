
# ============================================================
# FIREWATCH INDIA
# STATEWIDE + DISTRICT-WISE STREAMLIT DASHBOARD
# NASA MODIS + VIIRS | UTTARAKHAND | 2012-2026
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import re
import numpy as np

# Optional mapping libraries. The rest of the dashboard works without them.
try:
    import geopandas as gpd
    import folium
    from folium.plugins import HeatMap
    from streamlit.components.v1 import html as st_html
    MAPS_AVAILABLE = True
except Exception:
    MAPS_AVAILABLE = False

# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="FireWatch India",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 2. CUSTOM STYLING
# ============================================================

st.markdown("""
<style>
.main {
    background-color: #f7f9fc;
}
.block-container {
    padding-top: 1.5rem;
}
h1 {
    color: #174c35;
}
h2, h3 {
    color: #245c43;
}
[data-testid="stMetric"] {
    background-color: white;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #e5e9ef;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 3. LOAD PROCESSED DATA
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_FILE = (
    BASE_DIR
    / "outputs"
    / "Harmonized_Weekly_Activity.csv"
)

@st.cache_data
def load_data(file_path, modified_time):
    return pd.read_csv(file_path)

if not DATA_FILE.exists():
    st.error(
        "Processed dataset not found. "
        "Please run pipeline.py first."
    )
    st.stop()

try:
    df = load_data(
        str(DATA_FILE),
        DATA_FILE.stat().st_mtime
    )

except Exception as error:
    st.error(f"Unable to load dataset: {error}")
    st.stop()

if df.empty:
    st.error("The harmonized dataset is empty.")
    st.stop()

# ============================================================
# 4. DATA VALIDATION AND CLEANING
# ============================================================

required_columns = [
    "year",
    "week",
    "district",
    "harmonized_activity",
    "modis_activity",
    "viirs_activity",
    "viirs_adjusted",
    "historical_median",
    "anomaly_percent",
    "status",
    "calibration_factor"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    st.error("Required columns are missing:")
    st.write(missing_columns)
    st.stop()

numeric_columns = [
    "year",
    "week",
    "harmonized_activity",
    "modis_activity",
    "viirs_activity",
    "viirs_adjusted",
    "historical_median",
    "anomaly_percent",
    "calibration_factor"
]

# Optional baseline columns
for col in ["historical_q1", "historical_q3"]:
    if col in df.columns:
        numeric_columns.append(col)

for col in numeric_columns:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

df["district"] = (
    df["district"]
    .astype("string")
    .str.strip()
)

df["status"] = (
    df["status"]
    .fillna("No data")
    .astype(str)
)

df = df.dropna(
    subset=["year", "week", "district"]
)

df["year"] = df["year"].astype(int)
df["week"] = df["week"].astype(int)

# ============================================================
# 5. HEADER
# ============================================================

st.title("🔥 FireWatch India")

st.subheader(
    "Satellite-Based Fire Activity Monitoring System"
)

st.markdown("""
Explore historical fire hotspot activity in Uttarakhand
using NASA MODIS and VIIRS satellite observations.

The dashboard provides two levels of analysis:

- **Uttarakhand Statewide Analysis:** Overall regional activity.
- **District-wise Analysis:** Activity of individual or selected districts.

Explore weekly trends, annual patterns, satellite comparisons,
historical baselines and unusual activity periods.
""")

st.caption(
    "Study Area: Uttarakhand, India | Study Period: 2012–2026"
)

st.divider()

# ============================================================
# 6. SIDEBAR CONTROLS
# ============================================================

st.sidebar.title("🔥 Dashboard Controls")

st.sidebar.selectbox(
    "Select Region",
    ["Uttarakhand"]
)

st.sidebar.markdown("### District Selection")

districts = [
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

available_districts = sorted(
    df["district"].dropna().unique().tolist()
)

district_options = [
    district for district in districts
    if district in available_districts
]

# Empty selection = entire Uttarakhand
selected_districts = st.sidebar.multiselect(
    "Select Districts (Optional)",
    options=district_options,
    default=[],
    help=(
        "Leave this empty to see complete Uttarakhand "
        "statewide activity."
    )
)

if selected_districts:
    dashboard_mode = "District-wise Analysis"

    st.sidebar.success(
        f"{len(selected_districts)} district(s) selected"
    )

else:
    dashboard_mode = "Uttarakhand Statewide Analysis"

    st.sidebar.success(
        "Complete Uttarakhand region selected"
    )

st.sidebar.divider()

st.sidebar.markdown("### Year Selection")

available_years = sorted(
    df["year"].dropna().unique().astype(int).tolist()
)

selected_year = st.sidebar.selectbox(
    "Select Year",
    options=available_years,
    index=len(available_years) - 1
)

st.sidebar.divider()

st.sidebar.caption(
    f"Available districts: {len(district_options)} / 13"
)

st.sidebar.caption(
    f"Available years: {min(available_years)}–{max(available_years)}"
)

# ============================================================
# 7. PREPARE STATEWIDE DATA
# ============================================================

# Sum district activity by year and week.
# This produces a statewide aggregate from the
# district-level harmonized records.

sum_columns = [
    "harmonized_activity",
    "modis_activity",
    "viirs_activity",
    "viirs_adjusted",
    "historical_median"
]

if "historical_q1" in df.columns:
    sum_columns.append("historical_q1")

if "historical_q3" in df.columns:
    sum_columns.append("historical_q3")

aggregation = {}

for col in sum_columns:
    if col in df.columns:
        aggregation[col] = (
            lambda x: x.sum(min_count=1)
        )

aggregation["calibration_factor"] = "mean"

regional_data = (
    df.groupby(["year", "week"], as_index=False)
    .agg(aggregation)
)

regional_data["district"] = "Uttarakhand"

# Regional anomaly percentage against aggregated
# district historical medians.
regional_data["anomaly_percent"] = (
    (
        regional_data["harmonized_activity"]
        - regional_data["historical_median"]
    )
    / regional_data["historical_median"].replace(0, pd.NA)
) * 100

# Regional baseline status:
# Use summed district quartiles when available.
if (
    "historical_q1" in regional_data.columns
    and "historical_q3" in regional_data.columns
):

    regional_iqr = (
        regional_data["historical_q3"]
        - regional_data["historical_q1"]
    )

    regional_threshold = (
        regional_data["historical_q3"]
        + 1.5 * regional_iqr
    )

    regional_data["status"] = "Normal"

    regional_data.loc[
        regional_data["harmonized_activity"].isna(),
        "status"
    ] = "No data"

    regional_data.loc[
        regional_data["harmonized_activity"]
        > regional_threshold,
        "status"
    ] = "Unusual"

    regional_status_note = (
        "Regional unusual status is estimated using "
        "aggregated district baseline quartiles."
    )

else:

    regional_data["status"] = "Baseline comparison only"

    regional_status_note = (
        "Regional IQR-based unusual status could not be "
        "recalculated because historical quartiles "
        "are not available in the source dataset."
    )

# Regional sensor availability
modis_present = regional_data["modis_activity"].notna()
viirs_present = regional_data["viirs_activity"].notna()

regional_data["sensor_availability"] = "No data"

regional_data.loc[
    modis_present & viirs_present,
    "sensor_availability"
] = "Both sensors"

regional_data.loc[
    modis_present & ~viirs_present,
    "sensor_availability"
] = "MODIS only"

regional_data.loc[
    ~modis_present & viirs_present,
    "sensor_availability"
] = "VIIRS only"

# ============================================================
# 8. FILTER DATA ACCORDING TO SELECTION
# ============================================================

if selected_districts:

    # District-wise mode
    data = df[
        (df["year"] == selected_year)
        & (df["district"].isin(selected_districts))
    ].copy()

    analysis_title = "District-wise Analysis"

    comparison_title = "Selected Districts"

else:

    # Statewide mode
    data = regional_data[
        regional_data["year"] == selected_year
    ].copy()

    analysis_title = "Uttarakhand Statewide Analysis"

    comparison_title = "Entire Uttarakhand Region"

if data.empty:
    st.warning(
        "No records available for this year or selection."
    )
    st.stop()

data = data.sort_values(
    ["district", "week"]
)

# ============================================================
# 8A. YEAR-SELECTED HISTORICAL RANGE + DISTRICT ALERTS
# ============================================================

st.divider()
st.header("🚨 Year-wise District Fire Activity Early-Warning System")
st.caption(
    f"Alert analysis for the year selected in the sidebar: {selected_year}. "
    "Every district is checked separately using its latest available week "
    "within that selected year and a historical reference from earlier years."
)

history = df.copy()
for col in ["year", "week", "harmonized_activity", "modis_activity", "viirs_activity"]:
    if col in history.columns:
        history[col] = pd.to_numeric(history[col], errors="coerce")

history["district"] = history["district"].astype(str).str.strip()
history = history.dropna(
    subset=["year", "week", "district", "harmonized_activity"]
).copy()
history["year"] = history["year"].astype(int)
history["week"] = history["week"].astype(int)
history = history[history["week"].between(1, 53)]
history = history[history["district"].str.lower().ne("nan")]

district_aliases = {
    "hardwar": "Haridwar",
    "haridwar": "Haridwar",
    "garhwal": "Pauri Garhwal",
    "pauri": "Pauri Garhwal",
    "tehri": "Tehri Garhwal",
    "udham singh nagar": "Udham Singh Nagar"
}
history["district"] = history["district"].apply(
    lambda x: district_aliases.get(x.strip().lower(), x.strip().title())
)

all_13_districts = [
    "Almora", "Bageshwar", "Chamoli", "Champawat", "Dehradun",
    "Haridwar", "Nainital", "Pauri Garhwal", "Pithoragarh",
    "Rudraprayag", "Tehri Garhwal", "Udham Singh Nagar", "Uttarkashi"
]

def seasonal_week_window(target_week):
    # Same week plus immediately adjacent weeks, with year-wrap handling.
    return {
        ((int(target_week) - 2) % 52) + 1,
        int(target_week),
        (int(target_week) % 52) + 1
    }

def get_reference_range(values):
    vals = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    vals = vals[vals >= 0]
    if len(vals) < 5:
        return {
            "sample_n": int(len(vals)), "median": np.nan,
            "p75": np.nan, "p90": np.nan, "p95": np.nan,
            "maximum": np.nan
        }
    return {
        "sample_n": int(len(vals)),
        "median": float(vals.median()),
        "p75": float(vals.quantile(0.75)),
        "p90": float(vals.quantile(0.90)),
        "p95": float(vals.quantile(0.95)),
        "maximum": float(vals.max())
    }

def evaluate_range(current, ref):
    p90, p95 = ref["p90"], ref["p95"]
    if pd.isna(current) or pd.isna(p90) or pd.isna(p95):
        return "INSUFFICIENT HISTORY", np.nan
    usage = current / p90 * 100 if p90 > 0 else (100.0 if current > 0 else 0.0)
    if current >= p95 and current > p90:
        return "CRITICAL", usage
    if current >= p90:
        return "ALERT", usage
    if current >= 0.80 * p90:
        return "PRE-ALERT", usage
    return "NORMAL", usage

if history.empty:
    st.warning("Historical weekly activity records are not available.")
else:
    # IMPORTANT: current-year rows are taken from selected_year, not the
    # latest year in the complete dataset. This makes the sidebar year work.
    selected_year_data = history[history["year"] == int(selected_year)].copy()

    if selected_year_data.empty:
        st.warning(f"No activity records are available for {selected_year}.")
    else:
        district_names = sorted(set(all_13_districts) | set(history["district"].unique()))
        district_alert_rows = []

        for district_name in district_names:
            district_selected_year = selected_year_data[
                selected_year_data["district"] == district_name
            ].copy()

            if district_selected_year.empty:
                district_alert_rows.append({
                    "District": district_name,
                    "Selected year": int(selected_year),
                    "Latest week": np.nan,
                    "Latest activity": np.nan,
                    "Historical median": np.nan,
                    "Historical P75": np.nan,
                    "Early-warning level (80% P90)": np.nan,
                    "Alert threshold (P90)": np.nan,
                    "Critical threshold (P95)": np.nan,
                    "Historical maximum": np.nan,
                    "P90 range used (%)": np.nan,
                    "Reference samples": 0,
                    "MODIS activity": np.nan,
                    "VIIRS activity": np.nan,
                    "Alert level": "NO DATA IN SELECTED YEAR"
                })
                continue

            # For the selected year, use that district's latest week available.
            current_row = district_selected_year.sort_values("week").iloc[-1]
            current_week = int(current_row["week"])
            current_activity = float(current_row["harmonized_activity"])

            # Reference only earlier years; never use selected-year records
            # to calculate the historical threshold.
            past = history[
                (history["district"] == district_name)
                & (history["year"] < int(selected_year))
                & (history["week"].isin(seasonal_week_window(current_week)))
            ]
            ref = get_reference_range(past["harmonized_activity"])
            level, p90_usage = evaluate_range(current_activity, ref)

            district_alert_rows.append({
                "District": district_name,
                "Selected year": int(selected_year),
                "Latest week": current_week,
                "Latest activity": current_activity,
                "Historical median": ref["median"],
                "Historical P75": ref["p75"],
                "Early-warning level (80% P90)": (
                    ref["p90"] * 0.80 if pd.notna(ref["p90"]) else np.nan
                ),
                "Alert threshold (P90)": ref["p90"],
                "Critical threshold (P95)": ref["p95"],
                "Historical maximum": ref["maximum"],
                "P90 range used (%)": p90_usage,
                "Reference samples": ref["sample_n"],
                "MODIS activity": current_row.get("modis_activity", np.nan),
                "VIIRS activity": current_row.get("viirs_activity", np.nan),
                "Alert level": level
            })

        district_alerts = pd.DataFrame(district_alert_rows)

        st.info(
            f"Selected analysis year: **{selected_year}**. "
            "For each district, the app uses its latest available week within "
            f"{selected_year}. Historical thresholds use only earlier years "
            "and the same week plus adjacent weeks."
        )

        alert_order = {
            "CRITICAL": 0, "ALERT": 1, "PRE-ALERT": 2,
            "NORMAL": 3, "INSUFFICIENT HISTORY": 4,
            "NO DATA IN SELECTED YEAR": 5
        }
        district_alerts["_sort"] = (
            district_alerts["Alert level"].map(alert_order).fillna(6)
        )
        display_all_alerts = district_alerts.sort_values(
            ["_sort", "P90 range used (%)"],
            ascending=[True, False],
            na_position="last"
        ).drop(columns="_sort")

        st.subheader(f"All 13 Districts – {selected_year} Historical Range and Alert Status")
        st.dataframe(
            display_all_alerts.round(2),
            use_container_width=True,
            hide_index=True
        )

        # Respect the sidebar district filter, while retaining all-district
        # status above. Empty district selection means statewide/all districts.
        if selected_districts:
            selected_alerts = district_alerts[
                district_alerts["District"].isin(selected_districts)
            ].copy()
            selected_label = ", ".join(selected_districts)
        else:
            selected_alerts = district_alerts.copy()
            selected_label = "All Uttarakhand districts"

        active_levels = ["PRE-ALERT", "ALERT", "CRITICAL"]
        selected_active = selected_alerts[
            selected_alerts["Alert level"].isin(active_levels)
        ].copy()

        st.subheader(f"{selected_year} Alert Message: {selected_label}")

        if not selected_active.empty:
            selected_active = selected_active.sort_values(
                "P90 range used (%)", ascending=False
            )
            top_alert = selected_active.iloc[0]
            level = top_alert["Alert level"]
            district = top_alert["District"]

            if level == "CRITICAL":
                banner_color = "#8b0018"
                message = f"🚨 CRITICAL FIRE ACTIVITY: {district} – {selected_year} 🚨"
            elif level == "ALERT":
                banner_color = "#c62828"
                message = f"⚠️ UNUSUAL FIRE ACTIVITY: {district} – {selected_year} ⚠️"
            else:
                banner_color = "#d97706"
                message = f"⚠️ EARLY WARNING: ACTIVITY RISING IN {district} – {selected_year} ⚠️"

            st.markdown(f"""
            <style>
            @keyframes districtFireBlink {{
                0%, 100% {{ background:{banner_color}; opacity:1; }}
                50% {{ background:#321010; opacity:.55; }}
            }}
            .district-fire-alert {{
                animation:districtFireBlink 0.9s infinite;
                color:white; padding:20px; border-radius:12px;
                text-align:center; font-size:22px; font-weight:900;
                border:2px solid white; margin:12px 0;
            }}
            </style>
            <div class="district-fire-alert">{message}</div>
            """, unsafe_allow_html=True)

            st.error(
                f"{district} in {selected_year}, Week {int(top_alert['Latest week'])}: "
                f"activity **{top_alert['Latest activity']:.2f}**; "
                f"historical P90 **{top_alert['Alert threshold (P90)']:.2f}**; "
                f"historical P95 **{top_alert['Critical threshold (P95)']:.2f}**. "
                f"Status: **{level}**."
            )
            st.dataframe(
                selected_active[[
                    "District", "Selected year", "Latest week", "Latest activity",
                    "Historical median", "Alert threshold (P90)",
                    "Critical threshold (P95)", "P90 range used (%)", "Alert level"
                ]].round(2),
                use_container_width=True,
                hide_index=True
            )

            # Attempt automatic warning audio when an alert is present.
            # Browser autoplay policies may block sound until the user has
            # interacted with this site/tab at least once. Once permission is
            # granted by the browser, subsequent alert reruns can play automatically.
            import streamlit.components.v1 as components
            alarm_key = (
                f"{selected_year}-"
                + "-".join(sorted(selected_active["District"].astype(str).tolist()))
                + "-"
                + "-".join(sorted(selected_active["Alert level"].astype(str).tolist()))
            )
            # Keep the key stable for the same active alert so Streamlit reruns
            # do not repeatedly trigger the same alarm.
            import hashlib
            alarm_token = hashlib.md5(alarm_key.encode("utf-8")).hexdigest()

            components.html(f"""
            <div style="font-family:Arial;padding:8px 0">
              <div id="autoAlarmStatus"
                   style="font-weight:700;color:#8b0018;padding:10px 12px;
                   border-radius:8px;background:#fff0f0">
                🚨 Unusual fire activity detected. Attempting automatic alarm…
              </div>
              <div style="font-size:12px;color:#666;margin-top:6px">
                If your browser blocks automatic sound, interact once with this page
                (for example, click anywhere) and refresh. Browser autoplay rules
                cannot be overridden by dashboard code.
              </div>
            </div>
            <script>
            (function() {{
              const token = "{alarm_token}";
              const status = document.getElementById("autoAlarmStatus");
              const storageKey = "firewatch_alarm_last_token";
              const alreadyPlayed = sessionStorage.getItem(storageKey) === token;

              async function playAlarm() {{
                const AudioCtx = window.AudioContext || window.webkitAudioContext;
                if (!AudioCtx) {{
                  status.textContent = "🚨 Alert active. This browser does not support Web Audio.";
                  return;
                }}
                const ctx = new AudioCtx();
                try {{
                  await ctx.resume();
                  if (ctx.state !== "running") {{
                    status.textContent =
                      "🚨 Alert active. Browser blocked autoplay; interact with this page once, then refresh.";
                    await ctx.close();
                    return;
                  }}

                  let n = 0;
                  function beep() {{
                    if (n >= 12) {{
                      status.textContent = "🔊 Automatic warning alarm played for this alert.";
                      sessionStorage.setItem(storageKey, token);
                      ctx.close();
                      return;
                    }}
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = "sawtooth";
                    osc.frequency.value = (n % 2 === 0) ? 880 : 660;
                    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.13, ctx.currentTime + 0.025);
                    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.20);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.22);
                    n++;
                    setTimeout(beep, 300);
                  }}
                  status.textContent = "🔊 Automatic warning alarm is playing…";
                  beep();
                }} catch (err) {{
                  status.textContent =
                    "🚨 Alert active. Browser requires a user interaction before sound can play.";
                  try {{ await ctx.close(); }} catch (e) {{}}
                }}
              }}

              if (!alreadyPlayed) {{
                // Small delay lets the Streamlit component finish mounting.
                setTimeout(playAlarm, 250);
              }} else {{
                status.textContent = "🚨 Alert remains active. Alarm already played for this alert.";
              }}
            }})();
            </script>
            """, height=92)
        else:
            no_data = selected_alerts[
                selected_alerts["Alert level"].isin([
                    "NO DATA IN SELECTED YEAR", "INSUFFICIENT HISTORY"
                ])
            ]
            if not no_data.empty:
                st.warning(
                    f"Some selected districts have no data in {selected_year} "
                    "or fewer than five comparable historical observations. "
                    "See the district table for details."
                )
            else:
                st.success(
                    f"✅ No unusual activity threshold was crossed for "
                    f"{selected_label} in {selected_year}."
                )

        # Statewide summary is also calculated for the selected year.
        st.subheader(f"Uttarakhand Statewide Historical Range – {selected_year}")
        state_yearly = (
            history[history["year"] == int(selected_year)]
            .groupby("week", as_index=False)
            .agg(
                harmonized_activity=("harmonized_activity", "sum"),
                modis_activity=("modis_activity", lambda x: x.sum(min_count=1)),
                viirs_activity=("viirs_activity", lambda x: x.sum(min_count=1))
            )
        )

        if not state_yearly.empty:
            state_latest = state_yearly.sort_values("week").iloc[-1]
            state_week = int(state_latest["week"])
            state_current = float(state_latest["harmonized_activity"])
            state_past = (
                history[
                    (history["year"] < int(selected_year))
                    & (history["week"].isin(seasonal_week_window(state_week)))
                ]
                .groupby(["year", "week"], as_index=False)
                ["harmonized_activity"].sum()
            )
            state_ref = get_reference_range(state_past["harmonized_activity"])
            state_level, _ = evaluate_range(state_current, state_ref)

            state_cols = st.columns(5)
            state_cols[0].metric("Latest activity", f"{state_current:,.2f}")
            state_cols[1].metric(
                "Early-warning level",
                f"{state_ref['p90'] * 0.8:,.2f}" if pd.notna(state_ref["p90"]) else "N/A"
            )
            state_cols[2].metric(
                "Alert threshold (P90)",
                f"{state_ref['p90']:,.2f}" if pd.notna(state_ref["p90"]) else "N/A"
            )
            state_cols[3].metric(
                "Critical threshold (P95)",
                f"{state_ref['p95']:,.2f}" if pd.notna(state_ref["p95"]) else "N/A"
            )
            state_cols[4].metric("Current status", state_level)
            st.caption(
                f"Selected year {selected_year}, week {state_week} | "
                f"MODIS: {state_latest['modis_activity']:,.2f} | "
                f"VIIRS: {state_latest['viirs_activity']:,.2f} | "
                f"Historical samples: {state_ref['sample_n']}"
            )

        alert_download = display_all_alerts.to_csv(index=False).encode("utf-8")
        st.download_button(
            f"Download {selected_year} All-District Alert Report (CSV)",
            data=alert_download,
            file_name=f"FireWatch_All_District_Alerts_{selected_year}.csv",
            mime="text/csv"
        )

        st.info(
            "Method: Current activity is taken from the latest available week "
            "within the selected sidebar year. Historical thresholds are "
            "calculated only from earlier years for the same week and adjacent "
            "weeks. PRE-ALERT begins at 80% of P90, ALERT at P90, and CRITICAL "
            "at P95. At least five historical observations are required. "
            "These are statistical unusual-activity indicators, not fire "
            "predictions or confirmation. Browser sound requires a user click."
        )

# ============================================================
# 9. DASHBOARD OVERVIEW
# ============================================================

st.header(
    f"{analysis_title} - {selected_year}"
)

if selected_districts:
    st.info(
        "Showing activity for: "
        + ", ".join(selected_districts)
    )
else:
    st.info(
        "No district has been selected. "
        "The dashboard is displaying the aggregated "
        "activity of all available Uttarakhand districts."
    )

st.caption(
    "Activity values represent harmonized active grid-days, "
    "not individual fire incidents or burned area."
)

total_activity = data[
    "harmonized_activity"
].sum(min_count=1)

unusual_count = (
    data["status"] == "Unusual"
).sum()

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Districts Represented",
    data["district"].nunique()
)

col2.metric(
    "Weekly Records",
    len(data)
)

col3.metric(
    "Harmonized Activity",
    (
        f"{total_activity:,.2f}"
        if pd.notna(total_activity)
        else "No data"
    )
)

col4.metric(
    "Unusual Weeks",
    int(unusual_count)
)

st.divider()

# ============================================================
# 10. ANNUAL STATEWIDE ACTIVITY TREND
# ============================================================

st.header("Annual Fire Activity Trend - Uttarakhand")

annual_data = (
    regional_data.groupby("year", as_index=False)
    .agg(
        annual_activity=(
            "harmonized_activity",
            lambda x: x.sum(min_count=1)
        ),
        modis_activity=(
            "modis_activity",
            lambda x: x.sum(min_count=1)
        ),
        viirs_activity=(
            "viirs_activity",
            lambda x: x.sum(min_count=1)
        )
    )
)

annual_fig = px.bar(
    annual_data,
    x="year",
    y="annual_activity",
    title="Annual Harmonized Activity Across Uttarakhand (2012–2026)",
    labels={
        "year": "Year",
        "annual_activity": "Annual Active Grid-Days"
    },
    color="annual_activity",
    color_continuous_scale="YlOrRd"
)

annual_fig.update_layout(
    xaxis=dict(
        tickmode="linear",
        dtick=1
    )
)

st.plotly_chart(
    annual_fig,
    use_container_width=True
)

st.caption(
    "Annual values are sums of the available weekly "
    "district-level harmonized activity records."
)

st.divider()

# ============================================================
# 11. ACTIVITY SUMMARY
# ============================================================

if selected_districts:

    st.header("District-wise Activity Summary")

    district_summary = (
        data.groupby("district")
        .agg(
            weekly_records=("week", "count"),
            total_activity=(
                "harmonized_activity",
                lambda x: x.sum(min_count=1)
            ),
            average_activity=(
                "harmonized_activity",
                "mean"
            ),
            unusual_weeks=(
                "status",
                lambda x: (x == "Unusual").sum()
            )
        )
        .reset_index()
    )

    district_summary = district_summary.sort_values(
        "total_activity",
        ascending=False
    )

    st.dataframe(
        district_summary.round(2),
        use_container_width=True,
        hide_index=True
    )

    district_bar = px.bar(
        district_summary,
        x="district",
        y="total_activity",
        color="total_activity",
        color_continuous_scale="YlOrRd",
        title="Total Harmonized Activity by District",
        labels={
            "district": "District",
            "total_activity": "Total Active Grid-Days"
        }
    )

    district_bar.update_layout(
        xaxis_tickangle=-45
    )

    st.plotly_chart(
        district_bar,
        use_container_width=True
    )

else:

    st.header("Uttarakhand Regional Activity Summary")

    regional_summary = pd.DataFrame({
        "Indicator": [
            "Region",
            "Districts represented",
            "Selected year",
            "Weekly records",
            "Total harmonized activity",
            "Average weekly activity"
        ],
        "Value": [
            "Uttarakhand",
            13,
            selected_year,
            len(data),
            round(total_activity, 2)
            if pd.notna(total_activity) else "No data",
            round(data["harmonized_activity"].mean(), 2)
        ]
    })

    st.dataframe(
        regional_summary,
        use_container_width=True,
        hide_index=True
    )

st.divider()

# ============================================================
# 12. WEEKLY HARMONIZED ACTIVITY TREND
# ============================================================

st.header("Weekly Harmonized Activity Trend")

fig_weekly = px.line(
    data,
    x="week",
    y="harmonized_activity",
    color="district",
    markers=True,
    title=f"Weekly Activity - {comparison_title}",
    labels={
        "week": "Week of Year",
        "harmonized_activity": "Active Grid-Days",
        "district": "Region / District"
    },
    hover_data=[
        "modis_activity",
        "viirs_activity",
        "viirs_adjusted",
        "historical_median",
        "anomaly_percent"
    ]
)

fig_weekly.update_layout(
    hovermode="x unified"
)

st.plotly_chart(
    fig_weekly,
    use_container_width=True
)

st.divider()

# ============================================================
# 13. HISTORICAL ACTIVITY CALENDAR
# ============================================================

st.header("Historical Activity Calendar")

calendar_fig = px.density_heatmap(
    data,
    x="week",
    y="district",
    z="harmonized_activity",
    histfunc="avg",
    color_continuous_scale="YlOrRd",
    title=f"Weekly Activity Calendar - {selected_year}",
    labels={
        "week": "Week of Year",
        "district": "Region / District",
        "harmonized_activity": "Average Activity"
    }
)

calendar_fig.update_layout(
    height=500
)

st.plotly_chart(
    calendar_fig,
    use_container_width=True
)

st.divider()

# ============================================================
# 14. HISTORICAL BASELINE COMPARISON
# ============================================================

st.header("Current Activity vs Historical Baseline")

baseline_data = data.melt(
    id_vars=["district", "week"],
    value_vars=[
        "harmonized_activity",
        "historical_median"
    ],
    var_name="measurement",
    value_name="activity"
)

baseline_data["measurement"] = (
    baseline_data["measurement"].replace({
        "harmonized_activity": "Current Activity",
        "historical_median": "Historical Median"
    })
)

baseline_fig = px.line(
    baseline_data,
    x="week",
    y="activity",
    color="measurement",
    facet_row="district",
    markers=True,
    title="Weekly Activity Compared with Historical Median",
    labels={
        "week": "Week of Year",
        "activity": "Active Grid-Days",
        "measurement": "Measurement"
    }
)

baseline_fig.update_layout(
    height=max(
        450,
        300 * data["district"].nunique()
    )
)

st.plotly_chart(
    baseline_fig,
    use_container_width=True
)

if not selected_districts:
    st.caption(
        "The regional historical median is calculated by "
        "summing district-level historical medians. "
        "It is an aggregate baseline, not an independently "
        "estimated statewide statistical baseline."
    )

st.divider()

# ============================================================
# 15. UNUSUAL ACTIVITY PERIODS
# ============================================================

st.header("Unusual Activity Periods")

unusual = data[
    data["status"] == "Unusual"
].copy()

if not selected_districts:
    st.caption(regional_status_note)

if not unusual.empty:

    st.warning(
        f"{len(unusual)} unusual activity records identified."
    )

    unusual_columns = [
        "district",
        "year",
        "week",
        "harmonized_activity",
        "historical_median",
        "anomaly_percent",
        "status"
    ]

    st.dataframe(
        unusual[unusual_columns].round(2),
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "No unusual activity records identified "
        "using the available status calculation."
    )

st.divider()

# ============================================================
# 16. MODIS VS VIIRS SENSOR COMPARISON
# ============================================================

st.header("MODIS vs VIIRS Sensor Comparison")

sensor_data = data.melt(
    id_vars=["district", "week"],
    value_vars=[
        "modis_activity",
        "viirs_activity",
        "viirs_adjusted"
    ],
    var_name="sensor",
    value_name="activity"
)

sensor_data["sensor"] = (
    sensor_data["sensor"].replace({
        "modis_activity": "MODIS",
        "viirs_activity": "VIIRS Original",
        "viirs_adjusted": "VIIRS Adjusted"
    })
)

sensor_fig = px.line(
    sensor_data,
    x="week",
    y="activity",
    color="sensor",
    facet_row="district",
    markers=True,
    title="Weekly Satellite Activity Comparison",
    labels={
        "week": "Week of Year",
        "activity": "Activity",
        "sensor": "Satellite Dataset",
        "district": "Region / District"
    }
)

sensor_fig.update_layout(
    height=max(
        450,
        300 * data["district"].nunique()
    )
)

st.plotly_chart(
    sensor_fig,
    use_container_width=True
)

st.divider()

# ============================================================
# 17. SATELLITE OBSERVATION AVAILABILITY
# ============================================================

st.header("Satellite Observation Availability")

if "sensor_availability" in data.columns:

    availability_summary = (
        data.groupby(
            ["district", "sensor_availability"],
            dropna=False
        )
        .size()
        .reset_index(name="weekly_records")
    )

    st.dataframe(
        availability_summary,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "Sensor availability information is not present "
        "in the processed dataset."
    )

st.divider()

# ============================================================
# 18. DISTRICT-WISE CALIBRATION FACTORS
# ============================================================

if selected_districts:

    st.header("District-wise Sensor Calibration")

    calibration_data = (
        data.groupby("district")["calibration_factor"]
        .mean()
        .reset_index()
    )

    calibration_fig = px.bar(
        calibration_data,
        x="district",
        y="calibration_factor",
        color="calibration_factor",
        color_continuous_scale="Blues",
        title="District-wise MODIS–VIIRS Calibration Factors",
        labels={
            "district": "District",
            "calibration_factor": "Calibration Factor"
        }
    )

    calibration_fig.update_layout(
        xaxis_tickangle=-45
    )

    st.plotly_chart(
        calibration_fig,
        use_container_width=True
    )

else:

    st.header("Uttarakhand Sensor Calibration")

    regional_calibration = (
        df.groupby("district")["calibration_factor"]
        .mean()
        .reset_index()
    )

    st.dataframe(
        regional_calibration.round(4),
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "These are district-level calibration factors used "
        "in the statewide analysis. The regional activity "
        "is not recalibrated using a new statewide factor."
    )

st.divider()

# ============================================================
# 19. WEEKLY ACTIVITY RECORDS
# ============================================================

st.header("Weekly Activity Records")

st.dataframe(
    data.sort_values(
        ["district", "week"]
    ).round(3),
    use_container_width=True,
    hide_index=True
)

st.divider()

# ============================================================
# 20. DOWNLOAD PROCESSED DATA
# ============================================================

st.header("Download Processed Data")

csv_data = data.to_csv(
    index=False
).encode("utf-8")

if selected_districts:
    download_name = (
        f"FireWatch_{selected_year}_"
        f"{len(selected_districts)}_Districts.csv"
    )
else:
    download_name = (
        f"FireWatch_Uttarakhand_{selected_year}.csv"
    )

st.download_button(
    label="Download Current Analysis (CSV)",
    data=csv_data,
    file_name=download_name,
    mime="text/csv"
)

# Download all district records for selected year
all_year_data = df[
    df["year"] == selected_year
].copy()

all_csv = all_year_data.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    label="Download All District Records for Selected Year",
    data=all_csv,
    file_name=f"FireWatch_All_Districts_{selected_year}.csv",
    mime="text/csv"
)

# Download complete statewide annual data
annual_csv = annual_data.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    label="Download Uttarakhand Annual Trend (CSV)",
    data=annual_csv,
    file_name="FireWatch_Uttarakhand_Annual_Trend.csv",
    mime="text/csv"
)

st.divider()


# ============================================================
# 21. ADDITIONAL ANNUAL / MONTHLY SENSOR CHARTS AND MAPS
# ============================================================

st.header("Annual and Monthly Satellite Detection Analysis")
st.caption(
    "These charts use cleaned original MODIS and VIIRS hotspot records. "
    "They show satellite detections, not deduplicated unique fire incidents."
)

OUTPUT_DIR = BASE_DIR / "outputs"
MODIS_CLEAN_FILE = OUTPUT_DIR / "MODIS_Cleaned_Districts_2012_2026.csv"
VIIRS_CLEAN_FILE = OUTPUT_DIR / "VIIRS_Cleaned_Districts_2012_2026.csv"
BOUNDARY_FILE = BASE_DIR / "boundaries" / "uttarakhand_districts.geojson"

@st.cache_data
def load_sensor_csv(path, modified_time):
    return pd.read_csv(path, low_memory=False)

def locate_column(frame, possible_names):
    lookup = {str(col).strip().lower(): col for col in frame.columns}
    for name in possible_names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None

def standard_district(value):
    if pd.isna(value):
        return None
    value = re.sub(r"\s+", " ", str(value).strip()).title()
    return {
        "Hardwar": "Haridwar",
        "Garhwal": "Pauri Garhwal",
        "Pauri": "Pauri Garhwal",
        "Tehri": "Tehri Garhwal"
    }.get(value, value)

def prepare_sensor(path, sensor_name):
    if not path.exists():
        st.warning(f"{sensor_name} cleaned file not found: {path}")
        return None
    try:
        frame = load_sensor_csv(str(path), path.stat().st_mtime)
        date_col = locate_column(frame, ["acq_date", "date", "datetime", "observation_date", "acquisition_date", "timestamp"])
        lat_col = locate_column(frame, ["latitude", "lat"])
        lon_col = locate_column(frame, ["longitude", "lon", "long", "lng"])
        district_col = locate_column(frame, ["district", "dtname", "district_name"])
        if date_col is None:
            st.warning(f"{sensor_name}: date column not found. Available columns: {list(frame.columns)}")
            return None
        frame["_date"] = pd.to_datetime(frame[date_col], errors="coerce")
        frame = frame.dropna(subset=["_date"]).copy()
        frame["_year"] = frame["_date"].dt.year
        frame["_month"] = frame["_date"].dt.month
        frame["_district"] = frame[district_col].apply(standard_district) if district_col else None
        frame["_lat"] = pd.to_numeric(frame[lat_col], errors="coerce") if lat_col else np.nan
        frame["_lon"] = pd.to_numeric(frame[lon_col], errors="coerce") if lon_col else np.nan
        frame["_sensor"] = sensor_name
        return frame[frame["_year"].between(2012, 2026)].copy()
    except Exception as error:
        st.warning(f"Could not load {sensor_name} cleaned data: {error}")
        return None

modis_obs = prepare_sensor(MODIS_CLEAN_FILE, "MODIS")
viirs_obs = prepare_sensor(VIIRS_CLEAN_FILE, "VIIRS")

# Filter original detections by the same district selector as the main dashboard.
def sensor_filter(frame):
    if frame is None:
        return None
    out = frame.copy()
    if selected_districts and out["_district"].notna().any():
        out = out[out["_district"].isin(selected_districts)]
    return out

modis_view = sensor_filter(modis_obs)
viirs_view = sensor_filter(viirs_obs)

if modis_view is not None or viirs_view is not None:
    sensor_frames = [x for x in [modis_view, viirs_view] if x is not None]
    all_obs = pd.concat(sensor_frames, ignore_index=True)
    year_range = list(range(2012, 2027))
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # 21A-1. ANNUAL GRID DISTRIBUTION MAP (2012–2026)
    # Uses the cleaned MODIS + VIIRS point observations and a common 0.05° grid.
    # These are sensor detections per grid cell, not unique confirmed fires.
    st.subheader("Annual Fire Hotspot Distribution in Uttarakhand (2012–2026)")

    grid_observations = all_obs.dropna(
        subset=["_lat", "_lon", "_date", "_year"]
    ).copy()

    # Restrict to the approximate Uttarakhand geographic extent.
    grid_observations = grid_observations[
        grid_observations["_lat"].between(27.0, 32.0)
        & grid_observations["_lon"].between(77.0, 82.5)
    ].copy()

    # Common 0.05-degree grid; round to nearest grid-cell centre.
    grid_observations["lat_grid"] = (
        (grid_observations["_lat"] / 0.05).round() * 0.05
    ).round(3)
    grid_observations["lon_grid"] = (
        (grid_observations["_lon"] / 0.05).round() * 0.05
    ).round(3)

    annual_grid_counts = (
        grid_observations.groupby(["_year", "lat_grid", "lon_grid"])
        .size()
        .reset_index(name="detections")
    )

    annual_grid_counts = annual_grid_counts[
        annual_grid_counts["_year"].between(2012, 2026)
    ].copy()

    if not annual_grid_counts.empty:
        annual_years = list(range(2012, 2027))
        annual_titles = [
            f"{year}" if year < 2026 else "2026 (Partial Year)"
            for year in annual_years
        ]

        annual_map_fig = make_subplots(
            rows=3,
            cols=5,
            subplot_titles=annual_titles,
            horizontal_spacing=0.055,
            vertical_spacing=0.19
        )

        max_log = np.log10(max(1, annual_grid_counts["detections"].max()))
        for index, year in enumerate(annual_years):
            row = index // 5 + 1
            col = index % 5 + 1
            year_data = annual_grid_counts[
                annual_grid_counts["_year"] == year
            ]

            # Use log10(count) for marker colour so sparse and dense cells
            # remain visible on the same scale across all year panels.
            marker_values = np.log10(year_data["detections"].clip(lower=1))

            annual_map_fig.add_trace(
                go.Scatter(
                    x=year_data["lon_grid"],
                    y=year_data["lat_grid"],
                    mode="markers",
                    showlegend=False,
                    customdata=year_data["detections"],
                    marker=dict(
                        size=4.2,
                        color=marker_values,
                        colorscale="YlOrRd",
                        cmin=0,
                        cmax=max_log if max_log > 0 else 1,
                        opacity=0.88,
                        colorbar=dict(
                            title="Detections<br>per grid cell<br>(log scale)",
                            tickmode="array",
                            tickvals=[0, 1, 2],
                            ticktext=["1", "10", "100"],
                            len=0.78,
                            y=0.5
                        ) if index == 0 else None
                    ),
                    hovertemplate=(
                        "Longitude: %{x:.3f}<br>"
                        "Latitude: %{y:.3f}<br>"
                        "Detections: %{customdata:,}<extra></extra>"
                    )
                ),
                row=row,
                col=col
            )

            annual_map_fig.update_xaxes(
                range=[77.5, 81.5],
                title_text="Longitude",
                tickfont=dict(size=8),
                title_font=dict(size=9),
                row=row,
                col=col
            )
            annual_map_fig.update_yaxes(
                range=[28.5, 31.5],
                title_text="Latitude",
                tickfont=dict(size=8),
                title_font=dict(size=9),
                row=row,
                col=col
            )

        annual_map_fig.update_layout(
            height=1050,
            title=dict(
                text="Annual Fire Hotspot Distribution in Uttarakhand (2012–2026)",
                x=0.5,
                xanchor="center",
                font=dict(size=22)
            ),
            margin=dict(l=45, r=105, t=100, b=55),
            plot_bgcolor="white",
            paper_bgcolor="white"
        )
        annual_map_fig.update_annotations(font=dict(size=12, family="Arial"))
        st.plotly_chart(annual_map_fig, use_container_width=True)

        st.caption(
            "Source: Cleaned MODIS and VIIRS observations | 0.05° common grid. "
            "2026 represents a partial year based on the records currently available. "
            "Combined sensor detections may include overlapping observations."
        )
    else:
        st.info("No valid coordinates are available to build the annual grid distribution map.")

    # 21A-2. SEASONAL GRID DISTRIBUTION MAP
    st.subheader("Seasonal Fire Distribution in Uttarakhand")

    # Assign each detection to the month of its Monday week-start date.
    # This follows the seasonal convention stated in the figure reference.
    grid_observations["week_start"] = (
        grid_observations["_date"].dt.normalize()
        - pd.to_timedelta(grid_observations["_date"].dt.weekday, unit="D")
    )
    grid_observations["week_start_month"] = (
        grid_observations["week_start"].dt.month
    )

    def assign_fire_season(month):
        if month in [3, 4, 5]:
            return "Pre-Monsoon"
        if month in [6, 7, 8, 9]:
            return "Monsoon"
        if month in [10, 11]:
            return "Post-Monsoon"
        return "Winter"

    grid_observations["season"] = (
        grid_observations["week_start_month"].apply(assign_fire_season)
    )

    season_order = [
        "Pre-Monsoon", "Monsoon", "Post-Monsoon", "Winter"
    ]
    seasonal_grid_counts = (
        grid_observations.groupby(
            ["season", "lat_grid", "lon_grid"]
        )
        .size()
        .reset_index(name="detections")
    )

    if not seasonal_grid_counts.empty:
        seasonal_max = np.log10(
            max(1, seasonal_grid_counts["detections"].max())
        )

        seasonal_map_fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=season_order,
            horizontal_spacing=0.12,
            vertical_spacing=0.22
        )

        for index, season in enumerate(season_order):
            row = index // 2 + 1
            col = index % 2 + 1
            season_data = seasonal_grid_counts[
                seasonal_grid_counts["season"] == season
            ]
            marker_values = np.log10(
                season_data["detections"].clip(lower=1)
            )

            seasonal_map_fig.add_trace(
                go.Scatter(
                    x=season_data["lon_grid"],
                    y=season_data["lat_grid"],
                    mode="markers",
                    showlegend=False,
                    customdata=season_data["detections"],
                    marker=dict(
                        size=5.0,
                        color=marker_values,
                        colorscale="YlOrRd",
                        cmin=0,
                        cmax=seasonal_max if seasonal_max > 0 else 1,
                        opacity=0.9,
                        colorbar=dict(
                            title="Combined fire detections<br>per grid cell (log scale)",
                            tickmode="array",
                            tickvals=[0, 1, 2],
                            ticktext=["1", "10", "100"],
                            len=0.82,
                            y=0.5
                        ) if index == 0 else None
                    ),
                    hovertemplate=(
                        "Longitude: %{x:.3f}<br>"
                        "Latitude: %{y:.3f}<br>"
                        "Detections: %{customdata:,}<extra></extra>"
                    )
                ),
                row=row,
                col=col
            )

            seasonal_map_fig.update_xaxes(
                range=[77.5, 81.5],
                title_text="Longitude",
                row=row,
                col=col
            )
            seasonal_map_fig.update_yaxes(
                range=[28.5, 31.5],
                title_text="Latitude",
                row=row,
                col=col
            )

        seasonal_map_fig.update_layout(
            height=900,
            title=dict(
                text="Seasonal Fire Distribution in Uttarakhand",
                x=0.5,
                xanchor="center",
                font=dict(size=22)
            ),
            margin=dict(l=55, r=115, t=100, b=70),
            plot_bgcolor="white",
            paper_bgcolor="white"
        )
        seasonal_map_fig.update_annotations(font=dict(size=16, family="Arial"))
        st.plotly_chart(seasonal_map_fig, use_container_width=True)

        st.caption(
            "Source: Harmonized MODIS and VIIRS observations | 0.05° common grid | "
            "Seasons assigned using the month of each observation's Monday week-start. "
            "Combined counts may include overlapping detections from the two sensors."
        )
    else:
        st.info("No valid coordinates are available to build the seasonal grid distribution map.")

    # 21A. Annual detections: MODIS, VIIRS and their simple sum.
    st.subheader("Annual Wildfire Detection Trends (2012–2026)")
    annual_parts = []
    for frame, label in [(modis_view, "MODIS"), (viirs_view, "VIIRS")]:
        if frame is not None:
            annual_parts.append(frame.groupby("_year").size().rename(label))
    annual_detection = pd.concat(annual_parts, axis=1).fillna(0).reindex(year_range, fill_value=0)
    annual_detection.index.name = "Year"
    annual_detection["Combined"] = annual_detection.sum(axis=1)
    annual_long = annual_detection.reset_index().melt("Year", var_name="Sensor", value_name="Detections")
    annual_line = px.line(annual_long, x="Year", y="Detections", color="Sensor", markers=True,
                          title="Annual MODIS, VIIRS and Combined Detections")
    annual_line.update_layout(hovermode="x unified", xaxis=dict(tickmode="linear", dtick=1))
    st.plotly_chart(annual_line, use_container_width=True)
    st.caption("Combined = MODIS + VIIRS detections. It is not a deduplicated count of unique fires.")

    # 21B. Annual x month combined heatmap.
    def monthly_matrix(frame_a, frame_b=None):
        pieces = []
        for frame in [frame_a, frame_b]:
            if frame is not None:
                pieces.append(frame[["_year", "_month"]])
        if not pieces:
            return pd.DataFrame(0, index=year_range, columns=range(1, 13))
        stacked = pd.concat(pieces, ignore_index=True)
        return (stacked.groupby(["_year", "_month"]).size().unstack(fill_value=0)
                .reindex(index=year_range, columns=range(1, 13), fill_value=0))

    def make_month_heatmap(matrix, title):
        fig = px.imshow(matrix, x=month_names, y=matrix.index.astype(str), aspect="auto",
                        color_continuous_scale="YlOrRd", text_auto=",.0f", title=title,
                        labels={"x": "Month", "y": "Year", "color": "Detections"})
        fig.update_layout(height=560)
        return fig

    combined_monthly = monthly_matrix(modis_view, viirs_view)
    st.subheader("Annual × Monthly Fire Activity Heatmap — MODIS + VIIRS")
    st.plotly_chart(make_month_heatmap(combined_monthly, "Combined Monthly Hotspot Observations"), use_container_width=True)
    st.caption("Monthly combined values add both sensor detections and may include overlapping observations.")

    # 21C. Separate sensor heatmaps.
    st.subheader("MODIS and VIIRS Monthly Detection Comparison")
    left, right = st.columns(2)
    if modis_view is not None:
        with left:
            st.plotly_chart(make_month_heatmap(monthly_matrix(modis_view), "MODIS Monthly Detections"), use_container_width=True)
    if viirs_view is not None:
        with right:
            st.plotly_chart(make_month_heatmap(monthly_matrix(viirs_view), "VIIRS Monthly Detections"), use_container_width=True)

    # 21D. Calendar heatmap: months on vertical axis, years horizontal.
    st.subheader("Monthly Fire Occurrence Calendar")
    cal_long = combined_monthly.rename_axis("Year").reset_index().melt("Year", var_name="MonthNo", value_name="Detections")
    cal_long["Month"] = cal_long["MonthNo"].map(dict(enumerate(month_names, 1)))
    cal_fig = px.density_heatmap(cal_long, x="Year", y="Month", z="Detections", histfunc="avg",
                                 category_orders={"Month": month_names}, color_continuous_scale="YlOrRd",
                                 title="Monthly Fire Occurrence Heatmap",
                                 labels={"Detections": "Hotspot observations"})
    st.plotly_chart(cal_fig, use_container_width=True)

    # 21E. Month-by-month MODIS vs VIIRS comparison.
    st.subheader("MODIS vs VIIRS Monthly Fire Detection Comparison")
    compare_parts = []
    for frame, label in [(modis_view, "MODIS"), (viirs_view, "VIIRS")]:
        if frame is not None:
            compare_parts.append(frame.groupby(["_year", "_month"]).size().rename(label))
    if compare_parts:
        compare = pd.concat(compare_parts, axis=1).fillna(0).reset_index()
        compare["Period"] = compare["_year"].astype(str) + "-" + compare["_month"].astype(str).str.zfill(2)
        compare_long = compare.melt(id_vars=["_year", "_month", "Period"],
                                    value_vars=[c for c in ["MODIS", "VIIRS"] if c in compare.columns],
                                    var_name="Sensor", value_name="Detections")
        monthly_line = px.line(compare_long, x="Period", y="Detections", color="Sensor", markers=True,
                               title="Monthly MODIS vs VIIRS Detections")
        monthly_line.update_xaxes(tickangle=-45, nticks=20)
        st.plotly_chart(monthly_line, use_container_width=True)
else:
    st.warning("Annual/monthly detection charts need both or at least one cleaned sensor CSV in the outputs folder.")

st.divider()
st.header("Interactive Fire Observation Maps")
st.caption(
    "Satellite basemap and district boundaries with MODIS and VIIRS hotspot observations "
    "for Uttarakhand, 2012–2026."
)

if not MAPS_AVAILABLE:
    st.warning(
        "Map libraries are not installed. Install them with: "
        "python -m pip install geopandas folium"
    )
elif modis_view is None and viirs_view is None:
    st.warning(
        "Cleaned MODIS/VIIRS CSV files are required. Check the outputs folder."
    )
else:
    try:
        map_frames = [frame for frame in [modis_view, viirs_view] if frame is not None]
        map_points = (
            pd.concat(map_frames, ignore_index=True)
            .dropna(subset=["_lat", "_lon"])
            .copy()
        )

        if map_points.empty:
            st.info(
                "No valid latitude/longitude coordinates were found in the cleaned sensor files."
            )
        else:
            # Normalize coordinates and discard invalid locations.
            map_points["_lat"] = pd.to_numeric(map_points["_lat"], errors="coerce")
            map_points["_lon"] = pd.to_numeric(map_points["_lon"], errors="coerce")
            map_points = map_points.dropna(subset=["_lat", "_lon"])
            map_points = map_points[
                map_points["_lat"].between(27.0, 32.0)
                & map_points["_lon"].between(77.0, 82.5)
            ].copy()

            if map_points.empty:
                st.warning(
                    "No coordinates fall within the expected Uttarakhand map extent. "
                    "Please verify the latitude and longitude columns."
                )
            else:
                center = [
                    float(map_points["_lat"].mean()),
                    float(map_points["_lon"].mean())
                ]

                # Load district boundary file and normalize district names.
                boundary = None
                if BOUNDARY_FILE.exists():
                    boundary = gpd.read_file(BOUNDARY_FILE)
                    if boundary.crs is not None:
                        boundary = boundary.to_crs("EPSG:4326")
                    boundary_col = locate_column(
                        boundary,
                        ["dtname", "district", "district_name", "name"]
                    )
                    if boundary_col:
                        boundary["_district"] = boundary[boundary_col].apply(
                            standard_district
                        )
                        boundary = boundary[
                            boundary.geometry.notna()
                            & ~boundary.geometry.is_empty
                        ].copy()
                else:
                    st.warning(
                        "District boundary file not found: "
                        "boundaries/uttarakhand_districts.geojson"
                    )

                # Esri World Imagery is the default basemap. It does not require
                # a CARTO API key and removes the repeated 'API KEY REQUIRED' watermark.
                ESRI_IMAGERY = (
                    "https://server.arcgisonline.com/ArcGIS/rest/services/"
                    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
                )
                ESRI_ATTRIBUTION = (
                    "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, "
                    "and the GIS User Community"
                )

                def make_esri_map():
                    m = folium.Map(
                        location=center,
                        zoom_start=7,
                        tiles=None,
                        control_scale=True,
                        prefer_canvas=True
                    )
                    folium.TileLayer(
                        tiles=ESRI_IMAGERY,
                        attr=ESRI_ATTRIBUTION,
                        name="Satellite Imagery (Esri)",
                        overlay=False,
                        control=True,
                        show=True,
                        max_zoom=19
                    ).add_to(m)

                    # OpenStreetMap is an optional clean street-map alternative.
                    folium.TileLayer(
                        tiles="OpenStreetMap",
                        name="Street Map",
                        overlay=False,
                        control=True,
                        show=False
                    ).add_to(m)

                    # Title banner, similar to the requested reference map.
                    title_html = """
                    <div style="
                        position: fixed;
                        top: 12px;
                        left: 50%;
                        transform: translateX(-50%);
                        z-index: 9999;
                        background: rgba(255,255,255,0.96);
                        border: 2px solid #333;
                        border-radius: 7px;
                        padding: 9px 20px;
                        min-width: 360px;
                        text-align: center;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.25);
                        font-family: Arial, sans-serif;">
                        <div style="font-size: 16px; font-weight: 800; color: #222;">
                            UTTARAKHAND DISTRICT-WISE FOREST FIRE HOTSPOT MAP
                        </div>
                        <div style="font-size: 10px; color: #555; margin-top: 4px;">
                            MODIS AND VIIRS SATELLITE DATA | 2012–2026
                        </div>
                    </div>
                    """
                    m.get_root().html.add_child(folium.Element(title_html))

                    # North arrow.
                    north_html = """
                    <div style="
                        position: fixed; top: 95px; left: 18px; z-index: 9999;
                        background: white; border: 1px solid #555; border-radius: 5px;
                        padding: 7px 12px; text-align: center; font-weight: bold;
                        font-family: Arial; font-size: 18px;">
                        N<br>↑
                    </div>
                    """
                    m.get_root().html.add_child(folium.Element(north_html))
                    return m

                def add_district_boundaries(m):
                    if boundary is not None:
                        folium.GeoJson(
                            boundary.to_json(),
                            name="District Boundaries",
                            style_function=lambda feature: {
                                "color": "#202020",
                                "weight": 1.8,
                                "fillOpacity": 0.02
                            },
                            tooltip=folium.GeoJsonTooltip(
                                fields=["_district"],
                                aliases=["District:"],
                                sticky=True
                            )
                        ).add_to(m)

                # Use the same colors and labels as the reference map.
                intensity_colors = {
                    "Very Low": "#2878B5",
                    "Low": "#00A86B",
                    "Moderate": "#F2E500",
                    "High": "#F28C00",
                    "Very High": "#D7191C"
                }

                def add_intensity_legend(m):
                    legend_html = """
                    <div style="
                        position: fixed; bottom: 28px; left: 28px; z-index: 9999;
                        background: rgba(255,255,255,0.96); padding: 13px 15px;
                        border: 1px solid #555; border-radius: 6px;
                        box-shadow: 0 1px 6px rgba(0,0,0,0.25);
                        font-family: Arial; font-size: 12px; line-height: 1.8;">
                        <div style="font-weight:800; font-size:14px; margin-bottom:7px;">
                            FIRE DETECTION INTENSITY
                        </div>
                        <div><span style="display:inline-block;width:13px;height:13px;background:#2878B5;margin-right:8px;"></span>Very Low</div>
                        <div><span style="display:inline-block;width:13px;height:13px;background:#00A86B;margin-right:8px;"></span>Low</div>
                        <div><span style="display:inline-block;width:13px;height:13px;background:#F2E500;margin-right:8px;border:1px solid #999;"></span>Moderate</div>
                        <div><span style="display:inline-block;width:13px;height:13px;background:#F28C00;margin-right:8px;"></span>High</div>
                        <div><span style="display:inline-block;width:13px;height:13px;background:#D7191C;margin-right:8px;"></span>Very High</div>
                        <hr style="margin:7px 0;">
                        <div style="font-size:10px;max-width:190px;">
                            Classification based on relative district-wise detection counts.
                        </div>
                    </div>
                    """
                    m.get_root().html.add_child(folium.Element(legend_html))

                tab_density, tab_sensor, tab_district = st.tabs([
                    "Hotspot Density Map",
                    "MODIS vs VIIRS Grid Map",
                    "District-wise Intensity Map"
                ])

                # --------------------------------------------------------
                # MAP 1: HOTSPOT DENSITY ON ESRI SATELLITE IMAGERY
                # --------------------------------------------------------
                with tab_density:
                    fmap = make_esri_map()
                    add_district_boundaries(fmap)

                    # Density is calculated in rounded geographic cells.
                    density_source = map_points.copy()
                    density_source["lat_bin"] = density_source["_lat"].round(2)
                    density_source["lon_bin"] = density_source["_lon"].round(2)

                    density = (
                        density_source.groupby(["lat_bin", "lon_bin"])
                        .size()
                        .reset_index(name="count")
                    )
                    heat_data = density[
                        ["lat_bin", "lon_bin", "count"]
                    ].values.tolist()

                    if heat_data:
                        HeatMap(
                            heat_data,
                            name="Hotspot Density",
                            radius=17,
                            blur=13,
                            min_opacity=0.35,
                            max_zoom=12
                        ).add_to(fmap)

                    folium.LayerControl(collapsed=False).add_to(fmap)
                    add_intensity_legend(fmap)
                    st_html(
                        fmap.get_root().render(),
                        height=680,
                        scrolling=False
                    )

                # --------------------------------------------------------
                # MAP 2: MODIS VS VIIRS SPATIAL GRID COMPARISON
                # --------------------------------------------------------
                with tab_sensor:
                    fmap = make_esri_map()
                    add_district_boundaries(fmap)

                    cell_sets = {}
                    for label, frame in [
                        ("MODIS", modis_view),
                        ("VIIRS", viirs_view)
                    ]:
                        if frame is None:
                            cell_sets[label] = set()
                        else:
                            coords = frame.dropna(
                                subset=["_lat", "_lon"]
                            ).copy()
                            coords["grid_lat"] = (
                                coords["_lat"] / 0.05
                            ).round() * 0.05
                            coords["grid_lon"] = (
                                coords["_lon"] / 0.05
                            ).round() * 0.05
                            cell_sets[label] = set(
                                zip(coords["grid_lat"], coords["grid_lon"])
                            )

                    both_cells = cell_sets["MODIS"] & cell_sets["VIIRS"]
                    modis_only = cell_sets["MODIS"] - cell_sets["VIIRS"]
                    viirs_only = cell_sets["VIIRS"] - cell_sets["MODIS"]

                    for cells, color, label in [
                        (both_cells, "#8E44AD", "Both sensors"),
                        (modis_only, "#2878B5", "MODIS only"),
                        (viirs_only, "#F28C00", "VIIRS only")
                    ]:
                        layer = folium.FeatureGroup(
                            name=label,
                            show=True
                        )
                        for lat, lon in list(cells)[:15000]:
                            folium.CircleMarker(
                                location=[lat, lon],
                                radius=3,
                                color=color,
                                fill=True,
                                fill_color=color,
                                fill_opacity=0.78,
                                weight=0.5,
                                tooltip=label
                            ).add_to(layer)
                        layer.add_to(fmap)

                    folium.LayerControl(collapsed=False).add_to(fmap)
                    st_html(
                        fmap.get_root().render(),
                        height=680,
                        scrolling=False
                    )
                    st.caption(
                        f"Approximate 0.05° grid cells — MODIS only: "
                        f"{len(modis_only):,}; VIIRS only: {len(viirs_only):,}; "
                        f"both sensors: {len(both_cells):,}. "
                        "Shared cells do not prove the same fire or observation time."
                    )

                # --------------------------------------------------------
                # MAP 3: DISTRICT-WISE INTENSITY CHOROPLETH WITH LABELS
                # --------------------------------------------------------
                with tab_district:
                    if boundary is None or "_district" not in boundary.columns:
                        st.info(
                            "District boundary GeoJSON is missing or its district "
                            "name field could not be identified."
                        )
                    else:
                        counts = (
                            map_points.dropna(subset=["_district"])
                            .groupby("_district")
                            .size()
                            .rename("observations")
                            .reset_index()
                        )

                        choropleth = boundary.merge(
                            counts,
                            on="_district",
                            how="left"
                        )
                        choropleth["observations"] = (
                            choropleth["observations"].fillna(0).astype(int)
                        )

                        # Assign five relative intensity classes.
                        # Rank-based bins remain stable even when some counts tie.
                        if choropleth["observations"].nunique() > 1:
                            pct_rank = choropleth["observations"].rank(
                                method="average", pct=True
                            )
                            choropleth["intensity_class"] = pd.cut(
                                pct_rank,
                                bins=[0, 0.2, 0.4, 0.6, 0.8, 1.000001],
                                labels=[
                                    "Very Low", "Low", "Moderate",
                                    "High", "Very High"
                                ],
                                include_lowest=True
                            ).astype(str)
                        else:
                            choropleth["intensity_class"] = "Very Low"

                        choropleth["intensity_class"] = (
                            choropleth["intensity_class"]
                            .replace("nan", "Very Low")
                        )

                        fmap = make_esri_map()

                        def district_style(feature):
                            category = feature["properties"].get(
                                "intensity_class", "Very Low"
                            )
                            fill = intensity_colors.get(
                                category, "#2878B5"
                            )
                            return {
                                "fillColor": fill,
                                "color": "#202020",
                                "weight": 1.8,
                                "fillOpacity": 0.78
                            }

                        folium.GeoJson(
                            choropleth.to_json(),
                            name="District-wise Fire Intensity",
                            style_function=district_style,
                            highlight_function=lambda feature: {
                                "weight": 3,
                                "color": "#FFFFFF",
                                "fillOpacity": 0.9
                            },
                            tooltip=folium.GeoJsonTooltip(
                                fields=[
                                    "_district",
                                    "observations",
                                    "intensity_class"
                                ],
                                aliases=[
                                    "District:",
                                    "Hotspot detections:",
                                    "Intensity:"
                                ],
                                sticky=True
                            )
                        ).add_to(fmap)

                        # Add readable district labels and detection totals.
                        label_layer = folium.FeatureGroup(
                            name="District Names and Counts",
                            show=True
                        )
                        for _, row in choropleth.iterrows():
                            if row.geometry is None or row.geometry.is_empty:
                                continue
                            point = row.geometry.representative_point()
                            label_text = (
                                f"<div style='text-align:center;"
                                f"font-family:Arial,sans-serif;"
                                f"font-size:11px;font-weight:700;"
                                f"color:#fff;text-shadow:"
                                f"-1px -1px 2px #000,1px 1px 2px #000,"
                                f"-1px 1px 2px #000,1px -1px 2px #000;"
                                f"white-space:nowrap;'>"
                                f"{row['_district']}<br>"
                                f"{int(row['observations']):,}</div>"
                            )
                            folium.Marker(
                                location=[point.y, point.x],
                                icon=folium.DivIcon(
                                    html=label_text,
                                    icon_size=(120, 34),
                                    icon_anchor=(60, 17)
                                )
                            ).add_to(label_layer)
                        label_layer.add_to(fmap)

                        add_intensity_legend(fmap)
                        folium.LayerControl(collapsed=False).add_to(fmap)

                        # Fit the map to the full Uttarakhand boundary.
                        minx, miny, maxx, maxy = choropleth.total_bounds
                        fmap.fit_bounds([[miny, minx], [maxy, maxx]])

                        st_html(
                            fmap.get_root().render(),
                            height=720,
                            scrolling=False
                        )
                        st.caption(
                            "District colours show relative classes based on the number "
                            "of MODIS + VIIRS hotspot records in the selected dataset. "
                            "These are satellite detections, not unique confirmed fires."
                        )

    except Exception as map_error:
        st.error(f"Interactive map could not be generated: {map_error}")
        st.caption(
            "Check the cleaned sensor CSV files, coordinate columns, "
            "district GeoJSON and installed map libraries."
        )

st.divider()

# ============================================================
# 22. METHODOLOGY AND LIMITATIONS
# ============================================================

st.header("About FireWatch India")

st.markdown("""
**FireWatch India** is a research prototype developed to
harmonize NASA MODIS and VIIRS satellite hotspot observations
for Uttarakhand.

### Data Processing

- MODIS and VIIRS hotspot observations are cleaned.
- Observations are spatially assigned to 13 districts.
- A common spatial grid is used to calculate active grid-days.
- Weekly activity is calculated for each district.
- District-specific calibration factors are applied.
- Historical baselines and unusual activity periods are estimated.
- Statewide activity is aggregated from district-level records.

### Important Scientific Limitations

- MODIS and VIIRS have different spatial resolutions and
  satellite observation characteristics.
- Calibration factors require further validation.
- Satellite observation gaps must not be interpreted as
  zero fire activity.
- The current common grid is an approximate geographic grid.
- Historical administrative boundary changes may affect
  district-level comparisons.
- Regional historical medians are aggregated from
  district-level medians and are not independently
  estimated statewide statistical baselines.
- An unusual activity period is a statistical indication,
  not a confirmed fire warning.
- Hotspot activity is not equivalent to the number of
  individual fires or burned area.
""")

# ============================================================
# 23. FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div style="text-align:center; color:gray;">
        <b>🔥 FireWatch India</b><br>
        NASA MODIS & VIIRS Satellite Data<br>
        Uttarakhand | 2012–2026<br>
        Statewide and District-wise Analysis<br>
        Research Prototype
    </div>
    """,
    unsafe_allow_html=True
)
