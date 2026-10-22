# 🏨 Grand Horizon Hotels Analytics Platform
### *An End-to-End Python Full-Stack Data Pipeline & Business Intelligence Web Application*

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Web%20Framework-green.svg)](https://flask.palletsprojects.com/)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-orange.svg)](https://pandas.pydata.org/)
[![SQLite](https://img.shields.io/badge/SQLite-Database-lightgrey.svg)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## 📌 Table of Contents
* [Overview](#-overview)
* [System Architecture & Workflow](#-system-architecture--workflow)
* [Key Features & Modules](#-key-features--modules)
* [Tech Stack](#-tech-stack)
* [Project Directory Structure](#-project-directory-structure)
* [Getting Started & Installation](#-getting-started--installation)
* [Execution Guide](#-execution-guide)
* [Key Business Insights & Findings](#-key-business-insights--findings)

---

## 📖 Overview
The **Grand Horizon Hotels Analytics Platform** is a full-stack data intelligence system built as an Accenture Capstone project. It transforms raw, inconsistent hospitality reservation logs across **8 premier U.S. properties** (spanning New York, Chicago, Miami, Las Vegas, San Francisco, Orlando, Dallas, and Seattle) into a polished, production-ready web application.

The platform automates the entire data lifecycle: ingesting 5-day booking snapshots, performing rigorous cleaning and feature engineering, storing relational entities in an SQLite warehouse, generating advanced Matplotlib/Seaborn visualizations, and serving interactive dashboards via Flask.

---

## 🔄 System Architecture & Workflow
The platform processes data through a multi-stage automated pipeline:

```text
 ┌────────────────────────┐       ┌────────────────────────┐       ┌────────────────────────┐
 │   Raw CSV Data Feeds   │ ----> │  UC1: Data Cleaning &  │ ----> │    Relational SQLite   │
 │ (Bookings & Metadata)  │       │  Feature Engineering   │       │   Data Warehouse (DB)  │
 └────────────────────────>       └────────────────────────┘       └────────────────────────┘
                                                                                │
                                                                                ▼
 ┌────────────────────────┐       ┌────────────────────────┐       ┌────────────────────────┐
 │  Flask Web Application │ <---- │  UC4/UC5: SQL Views &  │ <---- │  UC2/UC3: Statistical  │
 │ & Executive Dashboard  │       │   Business Reporting   │       │  Analysis & Graphics   │
 └────────────────────────┘       └────────────────────────┘       └────────────────────────┘

```

---

## 🚀 Key Features & Modules

### 1️⃣ Data Ingestion & Cleaning (`UC1`)

* **Robust Parsing:** Handles mixed raw date formats (`m/d/Y` vs `YYYY-mm-dd`) across legacy system logs.
* **Feature Engineering:** Automatically computes `BookingDay`, `BookingHour`, `LengthOfStay`, and `LeadTimeDays`.
* **Data Quality Audits:** Employs NumPy to check missing value percentages per column and enforce strict schema rules.

### 2️⃣ Exploratory Data Analysis & Visuals (`UC2`)

* **Channel Revenue Mix:** Evaluates revenue distribution across Direct Website, OTAs (Expedia, Booking.com), Corporate Portals, Travel Agents, and Call Centers.
* **ADR Trends:** Maps Average Daily Rate fluctuations across the 5-day booking window.
* **Room Tier Spreads:** Analyzes median pricing and interquartile ranges (IQR) across Standard, Deluxe, Executive, and Suite categories.

### 3️⃣ Statistical Insights & Pattern Detection (`UC3`)

* **Loyalty Behavioral Modeling:** Analyzes cancellation rates across Non-Member, Silver, Gold, and Platinum tiers.
* **Correlation Analysis:** Evaluates linear relationships between lead time and total booking spend ($r = -0.0165$).
* **IQR Outlier Detection:** Implements Tukey's fences to identify rating anomalies across properties (flagging *Grand Horizon South Beach* at a 4.45 average rating).

### 4️⃣ Relational Database Reporting & SQL Views (`UC4`)

* **Custom SQLite Views:** Establishes persistent views (`vw_revenue_by_property`, `vw_channel_performance`) for fast retrieval.
* **Advanced Matrices:** Generates property booking velocity heatmaps and hierarchical correlation clustermaps.

### 5️⃣ Executive Business Summaries & Web UI (`UC5` & `app.py`)

* **Flask Dashboard:** Real-time metrics tracking chain-wide occupancy, total revenue (`₹288,063.91`), and cancellation counts.
* **Dynamic Report Builder:** Interactive regional filtering and CSV export capabilities for hotel managers.

---

## 🛠️ Tech Stack

* **Core Language:** Python 3.x
* **Data Engineering:** Pandas, NumPy
* **Data Visualization:** Matplotlib, Seaborn
* **Database Management:** SQLite3, SQLAlchemy
* **Web Framework:** Flask, Jinja2, HTML5, CSS3
* **Environment & Version Control:** PyCharm, VS Code, Git & GitHub

---

## 📂 Project Directory Structure

```text
Grand_Horizon_Hotels/
│
├── Data/                              # Raw CSV datasets & lookup reference tables
│   ├── hotel_bookings_dataset.csv
│   ├── hotel_property_info.csv
│   ├── booking_channel_info.csv
│   ├── city_market_info.csv
│   ├── room_type_codes.csv
│   └── loyalty_tier_info.csv
│
├── output/                            # Cleaned data extracts, CSV summaries, and database
│   ├── hotel_bookings.db
│   ├── enriched_bookings.csv
│   └── summary_*.csv
│
├── Graphs/                            # Generated analytical charts & visualizations
│   ├── uc2_*.png
│   ├── uc3_*.png
│   ├── uc4_*.png
│   └── uc5_*.png
│
├── app.py                             # Main Flask Web Application & Dashboard
├── UC1_Load_and_Clean.py              # Ingestion, cleaning, and schema loading
├── UC2_EDA_Visualization.py           # EDA script & exploratory charts
├── UC3_Statistical_Insights.py        # Statistical models, loyalty trends, and IQR outliers
├── UC4_SQLite_Reporting.py            # Property rankings, heatmaps, and SQL views
├── UC5_Database_Reporting.py          # Executive business summaries & export builder
└── README.md                          # Project documentation

```

---

## ⚙️ Getting Started & Installation

1. **Clone the Repository:**
```bash
git clone [https://github.com/your-username/Grand_Horizon_Hotels.git](https://github.com/your-username/Grand_Horizon_Hotels.git)
cd Grand_Horizon_Hotels

```


2. **Install Dependencies:**
```bash
pip install pandas numpy matplotlib seaborn flask sqlalchemy

```



---

## 🏃 Execution Guide

Execute the pipeline scripts sequentially to build the data warehouse and generate all reports:

```bash
# Step 1: Ingest, clean, and build database
python UC1_Load_and_Clean.py

# Step 2: Run exploratory data analysis
python UC2_EDA_Visualization.py

# Step 3: Compute statistical insights & outlier detection
python UC3_Statistical_Insights.py

# Step 4: Build SQLite reporting views & heatmaps
python UC4_SQLite_Reporting.py

# Step 5: Compile executive business summaries
python UC5_Database_Reporting.py

# Step 6: Launch the Flask Web Application
python app.py

```

*Once running, open your web browser and go to **`http://127.0.0.1:5000`** to access the dashboard.*

---

## 💡 Key Business Insights & Findings

* **Top Revenue Channel:** **Direct Website** leads all booking avenues with **$69,982.87** in realized revenue (28.7% booking share).
* **Top Revenue Room Type:** **Suites** dominate chain earnings, generating **$115,393.19** (46.4% of top room revenue) with a median booking amount of $1,335.39.
* **Rating Outlier:** **Grand Horizon South Beach** identified as a statistical outlier with an exceptional average guest rating of **4.45**.
* **Top Revenue Property:** **Grand Horizon Manhattan** leads property performance with **$40,018.04** in realized revenue.
* **Channel Risk:** **Call Center** and **Travel Agent** channels carry the highest cancellation velocity at **19.05%**.

---