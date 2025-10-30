# 🐟 Fish of Fortune — Macro Economy Analysis (Oct 2025)

Google Colab–optimized analysis for tracking **macro-economic trends** in *Fish of Fortune (FOF)* — focusing on **energy balance** (stored energy) and **energy out** (spent energy).  
Designed to surface inflationary pressure (production > consumption), detect anomalies, and support balancing decisions in live-ops.

---

## 🎯 Objectives
- Measure daily/weekly changes in **energy balance** and **energy out**.
- Detect **inflation** and **sink saturation**.
- Attribute shifts to events/config changes (mission bars, puzzles, dice, etc.).
- Produce fast, repeatable visualizations for stakeholder review.

---

## ⚙️ Platform & Workflow (Colab-First)
- Runs entirely in **Google Colab** (zero local setup).
- Uses **Google Drive** for **Parquet caching**:
  - **First run**: query **Snowflake**, clean data, **save to Drive as `.parquet`**.
  - **Subsequent runs**: **load from Parquet** for 10× faster analysis when fresh SQL isn’t required.
- Optional Google Sheets export for sharing summaries.

---

## 📁 Repository Structure

| File | Purpose |
|------|--------|
| `energy-balance-trends.py` | Time-series & cumulative trends for **energy balance** (hoarding/accumulation). |
| `energy-out-trends.py` | Time-series trends for **energy out** (spend/drain rate). |
| `dice-user-distribution.py` | Cohort/distribution analysis for dice-related users or similar cohorts. |
| `missionbar-trends.py` | Trend analysis around mission-bar configurations and pacing. |
| `missionbar-scatter.py` | Scatter views to spot outliers and segment differences for mission bars. |
| `puzzle-progression.py` | Progression/throughput analysis across puzzle-style mechanics. |
| `read-data-from-snowflake.py` | Pulls data from **Snowflake**, cleans it, **writes `.parquet` to Google Drive** (with timestamped filenames). |
| `read-data-from-parquet.py` | Loads **cached Parquet** datasets from Drive for fast re-runs (skips SQL entirely). |
| `snowflake-connector.py` | Helper for Snowflake auth/connection handling (env vars/secure config recommended). |

---

## 🧠 Analysis Flow
1. **Ingest**  
   - Fresh: `read-data-from-snowflake.py` → DataFrames → **save to Drive (.parquet)**  
   - Cached: `read-data-from-parquet.py` → **load from Drive**  
2. **Transform**  
   - Aggregate daily & cumulative metrics, add ratios (balance/out), compute deltas (DoD/WoW).  
3. **Visualize**  
   - Trend lines for balance & out, ratio charts, scatter plots for anomalies/segments.  
4. **Interpret**  
   - Flag inflation (balance growth >> out), hoarding/dumping patterns, sink efficacy.  

---

## 🚀 Quickstart (Colab)
1. Open the notebook/session in **Google Colab**.  
2. Mount Drive:
   ```python
   from google.colab import drive
   drive.mount('/content/drive')

(First run) Set Snowflake credentials (env vars or a secrets cell) and run read-data-from-snowflake.py.

Outputs timestamped .parquet files in your Drive (e.g., /content/drive/MyDrive/fof/parquet/...).

(Later runs) Use read-data-from-parquet.py to load cached data instantly.

Run energy-balance-trends.py / energy-out-trends.py (and other scripts) to generate plots and tables.


## **📊 Typical Outputs**

Energy Balance Trendline — stored energy over time (inflation/hoarding).

Energy Out Trendline — spend rate and sink effectiveness.

Scatter Diagnostics — for dice and missionbar live ops events.

Distribution Diagnostics - Puzzle and Dice live ops events progression tracking.


## **🔐 Credentials & Data Hygiene**

Never commit secrets. Use environment variables/Colab secrets.

Keep Drive paths configurable.

Only aggregated/anonymized data should be exported or shared.


## **🧰 Dependencies**

Colab covers most needs; for local runs:

pip install pandas numpy matplotlib seaborn snowflake-connector-python gspread


## **🗺️ Roadmap**

Automated daily/weekly refresh with versioned Parquet.

Anomaly detection (Z-score/MAD), alerting on sudden ratio shifts.

Link trends to specific event/config IDs and release notes.

Optional Streamlit dashboard for interactive slicing.


## **👤 Author**

Guy Lamdan — Game Economy Manager & Data Analyst
Issues/feedback: open a GitHub Issue in this repo.


## **🛡️ Disclaimer**

Analysis code only. No production data or credentials are stored here.
Fish of Fortune is the property of Whalo Games.


## **Output Examples - No real data shared**

<img width="1479" height="455" alt="image" src="https://github.com/user-attachments/assets/dfbf32c2-398d-4e36-ad92-96cdf643a612" />

<img width="1511" height="529" alt="image" src="https://github.com/user-attachments/assets/af6415b0-1953-40bd-88fd-09d7a7bfc9d3" />

<img width="1290" height="338" alt="image" src="https://github.com/user-attachments/assets/5432105c-531d-4bb9-b0e7-4548e8280beb" />

<img width="1601" height="267" alt="image" src="https://github.com/user-attachments/assets/310038f1-8e7b-4eae-9e51-cdf081008a04" />




