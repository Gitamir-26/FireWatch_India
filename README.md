# 🔥 FireWatch India
### An Interactive Forest Fire Monitoring, Harmonization and Early-Warning Dashboard for Uttarakhand (2012–2026)

**Project:** NASA Space Apps Challenge 2026  
**Challenge:** Harmonization of MODIS and VIIRS Hot Spots  
**Study Area:** Uttarakhand, India  
**Study Period:** 2012–2026  
**Platform:** Python & Streamlit

🌐 **Live Dashboard:** https://firewatch-india-uttarakhand.streamlit.app  
💻 **GitHub Repository:** https://github.com/Gitamir-26/FireWatch_India

▶️ **Demo Video Link:** https://drive.google.com/file/d/1LcsG_dhdnlhk1GXHmX6lT5nTQJorwxpx/view?usp=drive_link  

---

## 1. Project Overview

FireWatch India is an interactive forest fire monitoring and visualization platform developed to analyse satellite-based fire hotspot observations across Uttarakhand, India.

The project uses NASA's MODIS and VIIRS satellite hotspot datasets to explore the spatial and temporal distribution of fire activity between 2012 and 2026.

The platform focuses on harmonizing observations from two different satellite sensors and presenting the results through interactive maps, historical analysis, seasonal patterns, district-wise comparisons and unusual fire activity alerts.

FireWatch India aims to make satellite-based fire information easier to understand and support data-driven forest fire monitoring and awareness.

## 2. Problem Statement

MODIS and VIIRS satellites have different spatial resolutions and observation characteristics. Their hotspot observations cannot be directly combined without considering these differences.

This creates challenges in:
- Comparing fire activity across different years.
- Understanding spatial and temporal fire patterns.
- Combining observations from different satellite sensors.
- Identifying unusual increases in fire activity.
- Presenting consistent information at district and state levels.

FireWatch India addresses these challenges through a common spatial and temporal analysis framework.

## 3. Project Objectives

1. Analyse MODIS and VIIRS fire hotspot observations for Uttarakhand from 2012 to 2026.
2. Harmonize satellite observations using a common spatial and temporal framework.
3. Examine annual, monthly, seasonal and district-wise fire activity.
4. Compare MODIS and VIIRS observations.
5. Identify unusual increases in historical fire activity.
6. Develop an interactive dashboard for visualizing fire activity.
7. Provide early-warning indicators through visual alerts and alarm notifications.

## 4. Key Features

### A. Interactive Fire Observation Maps
- Hotspot density visualization.
- MODIS vs VIIRS spatial comparison.
- District-wise fire intensity mapping.
- Uttarakhand district boundaries.
- Interactive map navigation and visualization.

### B. Annual Fire Hotspot Distribution
- Year-wise hotspot distribution from 2012 to 2026.
- Spatial comparison of annual fire activity.
- Identification of years with relatively higher hotspot activity.

### C. Seasonal Fire Distribution
The dashboard analyses fire activity across four seasons:

- Pre-Monsoon
- Monsoon
- Post-Monsoon
- Winter

Seasonal maps help visualize geographical variations in fire activity.

### D. Monthly and Annual Analysis
- Annual fire hotspot trends.
- Monthly fire activity heatmaps.
- MODIS and VIIRS comparison.
- Historical fire activity visualization.

### E. District-wise Analysis
- Analysis of all 13 districts of Uttarakhand.
- District-level fire activity comparisons.
- Historical activity summaries.
- Sensor-wise observations.

### F. Anomaly Detection and Early-Warning Alerts

FireWatch India includes a historical range-based unusual activity detection system.

The system:
- Uses historical harmonized activity observations.
- Calculates district-specific historical reference ranges.
- Establishes early-warning, alert and critical levels.
- Compares selected-year activity with historical patterns.
- Displays unusual activity messages.
- Uses blinking visual warnings and an automatic alarm playback attempt when unusual activity is detected.

**Note:** These are statistical early-warning indicators, not confirmed fire reports or predictions of future fires. Automatic audio playback depends on browser permissions and autoplay policies.

## 5. Data Sources

The project uses satellite-based fire hotspot observations from:

| Satellite Sensor | Description |
|---|---|
| MODIS | Moderate Resolution Imaging Spectroradiometer |
| VIIRS | Visible Infrared Imaging Radiometer Suite |

**Data period:** 2012–2026  
**Geographical coverage:** Uttarakhand, India

The project also uses Uttarakhand district boundary data in GeoJSON format for spatial visualization and district-level analysis.

## 6. Methodology

The project follows these major processing stages:

1. **Data Collection:** Collection of MODIS and VIIRS hotspot observations.
2. **Data Cleaning:** Preparation of satellite datasets and removal of unsuitable records.
3. **Spatial Processing:** Assignment of hotspot observations to geographical locations and district boundaries.
4. **Harmonization:** Conversion of observations into a common spatial and temporal framework.
5. **Sensor Comparison:** Comparison of MODIS and VIIRS activity.
6. **Historical Analysis:** Examination of annual, monthly, seasonal and district-wise activity.
7. **Anomaly Detection:** Calculation of historical reference ranges and identification of unusual activity.
8. **Visualization:** Presentation of findings through an interactive Streamlit dashboard.

## 7. Technology Stack

| Technology | Application |
|---|---|
| Python | Main programming language |
| Pandas | Data processing and analysis |
| NumPy | Numerical calculations |
| GeoPandas | Geospatial data processing |
| Shapely | Spatial operations |
| Plotly | Interactive charts |
| Matplotlib | Statistical visualizations |
| Folium | Interactive maps |
| Streamlit | Web dashboard |
| GeoJSON | District boundary representation |
| GitHub | Version control and source code hosting |
| Streamlit Community Cloud | Web application deployment |

## 8. Project Structure

```text
FireWatch_India/
│
├── app.py
├── pipeline.py
├── requirements.txt
│
├── boundaries/
│   ├── README.md
│   └── uttarakhand_districts.geojson
│
└── outputs/
    ├── Harmonized_Weekly_Activity.csv
    ├── District_Summary.csv
    ├── District_Sensor_Overlap_Comparison.csv
    ├── MODIS_Cleaned_Districts_2012_2026.csv
    ├── VIIRS_Cleaned_Districts_2012_2026.csv
    └── Other processed CSV datasets
```

## 9. Installation and Local Setup

To run FireWatch India locally:

**Step 1: Clone the repository**

```bash
git clone https://github.com/Gitamir-26/FireWatch_India.git
```

**Step 2: Open the project directory**

```bash
cd FireWatch_India
```

**Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

**Step 4: Run the Streamlit application**

```bash
python -m streamlit run app.py
```

The application will open in your browser.

## 10. Limitations

- Satellite hotspot detections do not represent the exact number of individual fires.
- MODIS and VIIRS have different spatial resolutions and observation characteristics.
- Harmonized activity values are analytical indicators and should not be interpreted as exact burned area.
- Satellite observations may be affected by cloud cover, observation timing and sensor availability.
- Historical anomaly levels indicate unusual activity relative to the selected reference period; they do not confirm an active fire.
- The 2026 dataset represents a partial year.
- District boundaries and spatial assignments may contain administrative or geographical limitations.

## 11. Expected Impact

FireWatch India aims to:

- Improve understanding of forest fire activity in Uttarakhand.
- Support district-level historical fire analysis.
- Make satellite observations accessible through interactive visualizations.
- Highlight unusual increases in fire activity.
- Support researchers, students, forest departments and environmental stakeholders with data-driven insights.

## 12. Future Scope

Potential future improvements include:

- Integration of near-real-time satellite hotspot feeds.
- Weather and vegetation information integration.
- Improved fire risk modelling.
- Mobile-friendly alert notifications.
- Integration of additional satellite datasets.
- Validation of anomaly indicators using independent fire records.

## 13. Acknowledgements

We acknowledge NASA and the relevant satellite data providers for making MODIS and VIIRS fire hotspot observations available for research and analysis.

We also acknowledge the open-source Python community and the developers of the geospatial and data visualization libraries used in this project.

---

## 14. Project Access

🌐 **Live Website:** https://firewatch-india-uttarakhand.streamlit.app

💻 **Source Code:** https://github.com/Gitamir-26/FireWatch_India

**FireWatch India – Turning Satellite Data into Meaningful Fire Activity Insights.**

*Developed for NASA Space Apps Challenge 2026.*
