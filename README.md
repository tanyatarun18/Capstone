# Hotel Booking Data Analysis Project

## Project Overview

The **Hotel Booking Data Analysis Project** focuses on cleaning, processing, analyzing, and visualizing hotel booking data to identify useful insights into booking patterns, cancellations, revenue performance, customer loyalty, and property performance.

The project uses Python, Pandas, NumPy, Matplotlib, Seaborn, and SQLite to process booking records, enrich them with reference data, generate analytical reports, and create visualizations to support data-driven decision-making.

## Objectives

- Clean and validate hotel booking data.
- Handle missing values, invalid records, inconsistent formats, and data types.
- Enrich booking records using property, booking channel, city market, room type, and loyalty tier reference tables.
- Analyze booking trends and cancellation patterns.
- Evaluate the relationship between customer loyalty, booking behavior, and ratings.
- Compare revenue and performance across hotel properties and booking channels.
- Identify room types that contribute the most realized revenue.
- Store cleaned and enriched data in a SQLite database.
- Generate CSV reports, text summaries, and graphs for further analysis.

## Technologies Used

- **Python** – Data processing and analysis
- **Pandas** – Data cleaning, transformation, aggregation, and analysis
- **NumPy** – Numerical operations and data validation
- **Matplotlib** – Data visualization
- **Seaborn** – Statistical visualization and heatmaps
- **SQLite** – Storage and querying of cleaned and enriched data
- **Pathlib** – File and directory management

## Project Structure

```text
Hotel-Booking-Data-Analysis/
│
├── Data/
│   ├── hotel_bookings_dataset.csv
│   ├── hotel_property_info.csv
│   ├── booking_channel_info.csv
│   ├── city_market_info.csv
│   ├── room_type_codes.csv
│   └── loyalty_tier_info.csv
│
├── output/
│   ├── cleaned_bookings.csv
│   ├── enriched_bookings.csv
│   ├── data_quality_report.csv
│   ├── data_quality_report_after_cleaning.csv
│   ├── analysis_answers.txt
│   └── hotel_bookings.db
│
├── Graphs/
│   └── Generated charts and visualizations
│
├── UC1/
│   └── Data cleaning and enrichment script
│
├── UC2/
│   └── Booking trend analysis script
│
├── UC3/
│   └── Customer loyalty and rating analysis script
│
├── UC4/
│   └── Property performance and correlation analysis script
│
├── UC5/
│   └── Revenue and booking channel analysis script
│
└── README.md
```

*Note: Adjust the folder and script names above to match your actual project directory.*

## Use Cases

### UC1 – Data Cleaning and Data Enrichment

**Purpose:** Prepare reliable booking data for subsequent analysis.

Key operations:
- Load the booking dataset and reference tables.
- Standardize column names, text fields, and lookup keys.
- Convert booking, check-in, check-out, and update dates into datetime format.
- Convert numeric fields such as room rate, nights, guest counts, total amount, and rating.
- Normalize cancellation values into Boolean values.
- Handle missing values and mark invalid values for review.
- Derive features such as booking day, booking hour, length of stay, and lead time.
- Merge reference tables into the booking dataset.
- Generate pre-cleaning and post-cleaning data quality reports.
- Export cleaned and enriched CSV files and store them in SQLite.

**Main outputs:**
- `cleaned_bookings.csv`
- `enriched_bookings.csv`
- `data_quality_report.csv`
- `data_quality_report_after_cleaning.csv`
- `hotel_bookings.db`
- `analysis_answers.txt`

### UC2 – Booking Trend and Cancellation Analysis

**Purpose:** Examine booking patterns over time and understand cancellation behavior.

Key operations:
- Analyze booking volume by booking date.
- Compare cancelled and non-cancelled bookings.
- Identify daily or periodic booking trends.
- Examine cancellation patterns across properties or booking categories.
- Generate time-based visualizations and summary statistics.

**Typical outputs:**
- Booking trend summaries
- Cancellation summaries
- Booking volume charts
- Cancellation trend visualizations

### UC3 – Customer Loyalty and Rating Analysis

**Purpose:** Understand how customer loyalty and booking characteristics relate to ratings and cancellation behavior.

Key operations:
- Compare cancellation rates across loyalty tiers.
- Analyze guest ratings by loyalty category or property.
- Examine lead time and length of stay.
- Calculate correlations between relevant numerical booking metrics.
- Generate summary tables and charts to identify patterns.

**Typical outputs:**
- Loyalty-tier cancellation summaries
- Guest rating comparisons
- Lead-time and stay-length analysis
- Correlation summaries and visualizations

### UC4 – Property Performance and Booking Metric Analysis

**Purpose:** Compare hotel property performance and explore relationships between booking metrics.

Key operations:
- Calculate realized revenue by property.
- Compare booking volumes across properties and dates.
- Analyze guest ratings across markets.
- Examine relationships among lead time, room rate, total amount, number of nights, and guest counts.
- Generate heatmaps and comparison charts.

**Typical outputs:**
- Realized revenue by property
- Non-cancelled booking volume by property and booking day
- Average guest rating by market
- Correlation heatmap of booking metrics

### UC5 – Revenue and Booking Channel Analysis

**Purpose:** Evaluate revenue contribution and cancellation behavior across booking channels and room types.

Key operations:
- Calculate cancellation rates by booking channel.
- Compare revenue generated by booking channels.
- Rank room types by realized revenue.
- Compare property-level revenue and booking counts.
- Generate charts to highlight revenue distribution and channel performance.

**Typical outputs:**
- Cancellation rate by booking channel
- Revenue by property
- Top room types by realized revenue
- Booking channel and property summary CSV files

## Data Processing Methodology

The project follows a sequential workflow:

1. **Data ingestion:** Load the booking dataset and all reference tables from the `Data/` directory.
2. **Data profiling:** Generate an initial report showing missing values, percentages, and data types.
3. **Data cleaning:** Standardize fields, convert data types, validate numeric values, and handle missing data.
4. **Feature engineering:** Derive booking day, booking hour, length of stay, and lead time.
5. **Data enrichment:** Join bookings with reference tables using their corresponding codes.
6. **Data storage:** Save cleaned and enriched data to CSV files and SQLite.
7. **Analysis:** Run UC2–UC5 using the cleaned or enriched dataset.
8. **Visualization:** Save charts in the `Graphs/` directory.
9. **Reporting:** Export summary tables and written analytical results to the `output/` directory.

## Installation and Requirements

Python 3.10 or later is recommended.

Install the required libraries:

```bash
pip install pandas numpy matplotlib seaborn
```

SQLite support is included with Python's standard library through `sqlite3`.

## How to Run the Project

Run the scripts from the project environment after placing the input CSV files in the `Data/` directory.

**Step 1 – Run UC1**

```bash
python UC1/uc1.py
```

This creates the cleaned and enriched datasets, data quality reports, and SQLite database.

**Step 2 – Run UC2**

```bash
python UC2/uc2.py
```

**Step 3 – Run UC3**

```bash
python UC3/uc3.py
```

**Step 4 – Run UC4**

```bash
python UC4/uc4.py
```

**Step 5 – Run UC5**

```bash
python UC5/uc5.py
```

*Important:* Change the script paths and filenames in these commands to match your actual files. Run UC1 before UC2–UC5 because the later scripts depend on the cleaned or enriched data.

## Visualization and Interpretation

The generated charts help investigate:

- Changes in booking volume over time.
- Differences between cancelled and non-cancelled bookings.
- Guest rating differences across markets.
- Revenue differences across properties.
- Cancellation rates across booking channels.
- Revenue contributions of different room types.
- Correlations between numerical booking variables.

Visual patterns should be interpreted alongside the underlying summary tables and record counts. Correlation indicates association, not necessarily causation.

For revenue comparisons, cancelled bookings should be excluded from realized revenue. Cancellation rates should be calculated only from records with a known cancellation status. Charts should also clearly identify their time period, units, and population.

## Data Quality and Limitations

- Missing values may affect summary statistics and visualizations.
- Invalid dates and inconsistent booking fields should be investigated before drawing conclusions.
- Imputed values should be documented so they are not mistaken for original observations.
- Revenue calculations depend on the meaning and reliability of `total_amount`, `room_rate`, and `nights`.
- Reference-table joins should preserve the original booking row count.
- Correlation results can be influenced by missing values, outliers, and the distribution of the data.
- Findings describe patterns in the supplied dataset and should not automatically be generalized to all hotels or customers.

## Expected Deliverables

The project produces:

- Cleaned booking data
- Enriched booking data
- Data quality reports before and after cleaning
- SQLite database containing booking and reference data
- CSV analytical summaries
- Text-based analysis results
- Graphs and charts for all five use cases

## Conclusion

The Hotel Booking Data Analysis Project provides an end-to-end workflow for transforming raw hotel booking records into structured, analyzable data. The five use cases cover data preparation, booking trends, customer loyalty and ratings, property performance, and revenue and channel analysis.

Together, these analyses can help identify booking patterns, evaluate cancellation behavior, compare property performance, and understand revenue contribution. The reliability of the conclusions depends on correct data cleaning, consistent metric definitions, valid reference-table joins, and appropriate interpretation of the generated charts.

## Author

**Project:** Hotel Booking Data Analysis  
**Tools:** Python, Pandas, NumPy, Matplotlib, Seaborn, SQLite
