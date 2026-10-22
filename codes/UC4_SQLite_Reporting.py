from pathlib import Path
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
GRAPHS = ROOT / "Graphs"
DB_PATH = OUT / "hotel_bookings.db"
CSV_PATH = OUT / "enriched_bookings.csv"

OUT.mkdir(exist_ok=True)
GRAPHS.mkdir(exist_ok=True)

if not CSV_PATH.exists() or not DB_PATH.exists():
    raise FileNotFoundError("Run UC1 first to create the enriched CSV and database.")

df = pd.read_csv(CSV_PATH)
required = ["booking_id", "property_code", "cancelled", "total_amount"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"UC4 missing required columns: {missing}")

cancel_map = {"true": True, "1": True, "yes": True,
              "false": False, "0": False, "no": False}
df["cancelled"] = (
    df["cancelled"].astype(str).str.strip().str.lower().map(cancel_map)
)
df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce")

for col in ["room_rate", "rating", "nights", "adults", "children", "LeadTimeDays"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

def first_available(candidates):
    return next((c for c in candidates if c in df.columns), None)

property_col = first_available(["property_name", "hotel_name", "property_code"])
city_col = first_available(["city_name", "city", "market_name", "market_code"])
channel_col = first_available(["channel_name", "channel_code"])
room_col = first_available(["room_category", "room_type", "room_type_code"])
date_col = first_available(["booking_date", "date", "booking_day"])
rating_col = first_available(["rating", "guest_rating", "review_score"])

def labels(series):
    return series.fillna("Unknown").astype(str).str.strip().replace("", "Unknown")

df[property_col] = labels(df[property_col])
valid = df.loc[df["cancelled"].eq(False)].dropna(subset=["total_amount"]).copy()

if valid.empty:
    raise ValueError("No non-cancelled bookings with valid revenue are available.")

# 1. Revenue by property
revenue = valid.groupby(property_col)["total_amount"].sum().sort_values()
fig, ax = plt.subplots(figsize=(11, max(5, len(revenue) * 0.45)))
revenue.plot(kind="barh", ax=ax)
ax.set_title("Realized Revenue by Property")
ax.set_xlabel("Revenue")
ax.set_ylabel("Property")
ax.grid(axis="x", alpha=0.25)
fig.tight_layout()
fig.savefig(GRAPHS / "uc4_revenue_by_property.png", dpi=160, bbox_inches="tight")
plt.close(fig)

# 2. Booking volume by property and booking date
if date_col:
    dated = valid.copy()
    try:
        dated["_date"] = pd.to_datetime(dated[date_col], format='mixed', errors="coerce")
    except ValueError:
        dated["_date"] = pd.to_datetime(dated[date_col], errors="coerce")

    dated = dated.dropna(subset=["_date"])
    dated["_day"] = dated["_date"].dt.strftime("%Y-%m-%d")
    volume = dated.pivot_table(
        index=property_col, columns="_day", values="booking_id",
        aggfunc="count", fill_value=0
    )
    if not volume.empty:
        fig, ax = plt.subplots(figsize=(min(18, max(10, len(volume.columns) * 0.5)),
                                       max(5, len(volume.index) * 0.45)))
        sns.heatmap(volume, cmap="Blues", annot=volume.size <= 120, fmt="g", ax=ax)
        ax.set_title("Non-cancelled Booking Volume by Property and Booking Day")
        ax.set_xlabel("Booking day")
        ax.set_ylabel("Property")
        ax.tick_params(axis="x", labelrotation=45)
        fig.tight_layout()
        fig.savefig(GRAPHS / "uc4_property_day_heatmap.png", dpi=160, bbox_inches="tight")
        plt.close(fig)

# 3. Correlation clustermap
candidate_numeric = [
    c for c in ["nights", "adults", "children", "room_rate",
                "total_amount", "LeadTimeDays", "rating"]
    if c in df.columns
]
numeric = df[candidate_numeric].apply(pd.to_numeric, errors="coerce")
useful = [c for c in numeric if numeric[c].nunique(dropna=True) > 1]
if len(useful) >= 2:
    corr = numeric[useful].corr(min_periods=2)
    corr = corr.dropna(axis=0, how="all").dropna(axis=1, how="all")
    if corr.shape[0] >= 2:
        grid = sns.clustermap(
            corr, annot=True, fmt=".2f", cmap="vlag",
            center=0, vmin=-1, vmax=1, figsize=(9, 9)
        )
        grid.fig.suptitle("Correlation Between Booking Metrics", y=1.02)
        grid.savefig(GRAPHS / "uc4_correlation_clustermap.png", dpi=160, bbox_inches="tight")
        plt.close(grid.fig)

# 4. Average guest rating by market
if city_col and rating_col:
    ratings = df[[city_col, rating_col]].copy()
    ratings[city_col] = labels(ratings[city_col])
    ratings[rating_col] = pd.to_numeric(ratings[rating_col], errors="coerce")
    city_rating = ratings.dropna(subset=[rating_col]).groupby(city_col)[rating_col].mean().sort_values()
    if not city_rating.empty:
        fig, ax = plt.subplots(figsize=(11, max(5, len(city_rating) * 0.45)))
        city_rating.plot(kind="bar", ax=ax)
        ax.set_title("Average Guest Rating by Market")
        ax.set_xlabel("Market")
        ax.set_ylabel("Average rating")
        ax.tick_params(axis="x", labelrotation=35)
        fig.tight_layout()
        fig.savefig(GRAPHS / "uc4_rating_by_market.png", dpi=160, bbox_inches="tight")
        plt.close(fig)
else:
    city_rating = pd.Series(dtype=float)

# 5. Summary tables and views (Forcing correct schema names for the Flask App)
property_summary = (
    valid.groupby("property_name", dropna=False)
    .agg(booking_count=("booking_id", "count"),
         revenue=("total_amount", "sum"))
    .reset_index()
)
if rating_col:
    rating_summary = (
        df.groupby("property_name")[rating_col].mean()
        .rename("avg_rating").reset_index()
    )
    property_summary = property_summary.merge(rating_summary, on="property_name", how="left")

if channel_col:
    channel_data = df.dropna(subset=["cancelled"]).copy()
    channel_summary = (
        channel_data.groupby(channel_col, dropna=False)
        .agg(booking_count=("booking_id", "size"),
             cancellation_rate=("cancelled", "mean"))
        .reset_index()
    )
    channel_summary["cancellation_rate"] *= 100
    channel_revenue = valid.groupby(channel_col)["total_amount"].sum()
    channel_summary["revenue"] = channel_summary[channel_col].map(channel_revenue).fillna(0)
    
    # ENFORCE "channel_name" string for Flask backend
    channel_summary = channel_summary.rename(columns={channel_col: "channel_name"})
else:
    channel_summary = pd.DataFrame()

if room_col:
    room_summary = (
        valid.assign(_room=labels(valid[room_col]))
        .groupby("_room")["total_amount"].sum()
        .sort_values(ascending=False).head(5)
        .rename_axis("room_type").reset_index(name="revenue")
    )
else:
    room_summary = pd.DataFrame()

with sqlite3.connect(DB_PATH) as conn:
    property_summary.to_sql("summary_by_property", conn, if_exists="replace", index=False)
    if not channel_summary.empty:
        channel_summary.to_sql("summary_by_channel", conn, if_exists="replace", index=False)
    if not room_summary.empty:
        room_summary.to_sql("summary_top5_room_types", conn, if_exists="replace", index=False)

    conn.execute("DROP VIEW IF EXISTS vw_revenue_by_property")
    conn.execute("""
        CREATE VIEW vw_revenue_by_property AS
        SELECT property_code,
               SUM(CASE WHEN LOWER(TRIM(CAST(cancelled AS TEXT))) IN ('false','0','no')
                        THEN COALESCE(total_amount,0) ELSE 0 END) AS revenue,
               SUM(CASE WHEN LOWER(TRIM(CAST(cancelled AS TEXT))) IN ('false','0','no')
                        THEN 1 ELSE 0 END) AS booking_count
        FROM enriched_bookings
        GROUP BY property_code
    """)

    # ENFORCE "channel_name" selection
    conn.execute("DROP VIEW IF EXISTS vw_channel_performance")
    conn.execute("""
        CREATE VIEW vw_channel_performance AS
        SELECT channel_name,
               COUNT(*) AS booking_count,
               AVG(CASE
                   WHEN LOWER(TRIM(CAST(cancelled AS TEXT))) IN ('true','1','yes') THEN 1.0
                   WHEN LOWER(TRIM(CAST(cancelled AS TEXT))) IN ('false','0','no') THEN 0.0
                   ELSE NULL END) * 100 AS cancellation_rate
        FROM enriched_bookings
        GROUP BY channel_name
    """)

property_summary.to_csv(OUT / "summary_by_property.csv", index=False)
if not channel_summary.empty:
    channel_summary.to_csv(OUT / "summary_by_channel.csv", index=False)
if not room_summary.empty:
    room_summary.to_csv(OUT / "summary_top5_room_types.csv", index=False)

with open(OUT / "uc4_answers.txt", "w", encoding="utf-8") as f:
    f.write("USE CASE 4 - PROPERTY AND MARKET REPORTING\n")
    if not revenue.empty:
        f.write(f"Highest revenue property: {revenue.idxmax()}\n")
        f.write(f"Highest realized revenue: {revenue.max():.2f}\n")
    if not city_rating.empty:
        f.write(f"Highest average rating market: {city_rating.idxmax()}\n")
        f.write(f"Highest average rating: {city_rating.max():.2f}\n")

print("UC4 completed.")