from pathlib import Path
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
GRAPHS = ROOT / "Graphs"
DB_PATH = OUT / "hotel_bookings.db"

OUT.mkdir(parents=True, exist_ok=True)
GRAPHS.mkdir(parents=True, exist_ok=True)

if not DB_PATH.exists():
    raise FileNotFoundError(f"Database not found: {DB_PATH}. Run UC1 first.")

with sqlite3.connect(DB_PATH) as conn:
    df = pd.read_sql_query("SELECT * FROM enriched_bookings", conn)

if df.empty:
    raise ValueError("The enriched_bookings table is empty.")

for col in ["cancelled", "total_amount"]:
    if col not in df.columns:
        raise ValueError(f"UC5 requires column '{col}'.")

cancel_map = {
    "true": True, "1": True, "yes": True, "y": True,
    "false": False, "0": False, "no": False, "n": False
}
df["cancelled"] = (
    df["cancelled"].astype(str).str.strip().str.lower().map(cancel_map)
)
df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce")

def first_available(candidates):
    return next((c for c in candidates if c in df.columns), None)

channel_col = first_available(["channel_name", "channel_code"])
room_col = first_available(["room_category", "room_type", "room_type_code"])
property_col = first_available(["property_name", "hotel_name", "property_code"])

# Only confirmed non-cancelled bookings count toward realized revenue.
valid = df.loc[
    df["cancelled"].eq(False) & df["total_amount"].notna()
].copy()

# 1. Top five room types by realized revenue (Pie Chart implementation)
if room_col:
    room_data = valid.copy()
    room_data["_room"] = (
        room_data[room_col].fillna("Unknown").astype(str)
        .str.strip().replace("", "Unknown")
    )
    room_summary = (
        room_data.groupby("_room")["total_amount"].sum()
        .sort_values(ascending=False).head(5)
        .rename_axis("room_type").reset_index(name="revenue")
    )

    if not room_summary.empty:
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.pie(room_summary["revenue"], labels=room_summary["room_type"], autopct="%1.1f%%", startangle=90)
        ax.set_title("Top Five Room Types by Realized Revenue")
        ax.axis('equal') 
        fig.tight_layout()
        fig.savefig(GRAPHS / "uc5_top5_room_revenue.png", dpi=160, bbox_inches="tight")
        plt.close(fig)

        room_summary.to_csv(OUT / "summary_top5_room_types.csv", index=False)
else:
    room_summary = pd.DataFrame()
    print("Skipping room revenue chart: no room-type column found.")

# 2. Cancellation rate by booking channel.
if channel_col:
    known = df.dropna(subset=["cancelled"]).copy()
    known["_channel"] = (
        known[channel_col].fillna("Unknown").astype(str)
        .str.strip().replace("", "Unknown")
    )

    channel_summary = (
        known.groupby("_channel")
        .agg(
            booking_count=("cancelled", "size"),
            cancellations=("cancelled", "sum"),
            cancellation_rate=("cancelled", "mean"),
        )
        .reset_index()
        .rename(columns={"_channel": "channel_name"}) # ENFORCE "channel_name" for Flask
    )
    channel_summary["cancellation_rate"] *= 100

    if not valid.empty:
        valid["_channel"] = (
            valid[channel_col].fillna("Unknown").astype(str)
            .str.strip().replace("", "Unknown")
        )
        revenue_by_channel = valid.groupby("_channel")["total_amount"].sum()
        channel_summary["revenue"] = (
            channel_summary["channel_name"].map(revenue_by_channel).fillna(0) # MAP CORRECTLY
        )
    else:
        channel_summary["revenue"] = 0.0

    channel_summary = channel_summary.sort_values(
        "cancellation_rate", ascending=False
    )

    if not channel_summary.empty:
        fig, ax = plt.subplots(figsize=(10, max(5, len(channel_summary) * 0.55)))
        bars = ax.barh(
            channel_summary["channel_name"],
            channel_summary["cancellation_rate"]
        )
        ax.invert_yaxis()
        ax.set_title("Cancellation Rate by Booking Channel")
        ax.set_xlabel("Cancellation rate (%)")
        ax.set_ylabel("Booking channel")
        ax.grid(axis="x", alpha=0.25)
        ax.set_axisbelow(True)

        max_rate = channel_summary["cancellation_rate"].max()
        ax.set_xlim(0, max(5, max_rate * 1.2))
        for bar, value in zip(bars, channel_summary["cancellation_rate"]):
            ax.text(
                bar.get_width() + 0.1,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.1f}%",
                va="center",
                fontsize=9
            )

        fig.tight_layout()
        fig.savefig(GRAPHS / "uc5_channel_cancellation.png", dpi=160, bbox_inches="tight")
        plt.close(fig)

    channel_summary.to_csv(OUT / "summary_by_channel.csv", index=False)
else:
    channel_summary = pd.DataFrame()
    print("Skipping channel chart: no channel column found.")

# 3. Regional/property report.
if property_col:
    property_data = df.copy()
    property_data["_property"] = (
        property_data[property_col].fillna("Unknown").astype(str)
        .str.strip().replace("", "Unknown")
    )
    property_data["_realized_revenue"] = property_data["total_amount"].where(
        property_data["cancelled"].eq(False), 0
    )
    property_data["_realized_revenue"] = property_data[
        "_realized_revenue"
    ].fillna(0)

    regional_report = (
        property_data.groupby("_property")
        .agg(
            booking_count=("total_amount", "size"),
            revenue=("_realized_revenue", "sum")
        )
        .reset_index()
        .rename(columns={"_property": "property_name"})
        .sort_values("revenue", ascending=False)
    )
    regional_report.to_csv(OUT / "regional_property_report.csv", index=False)
else:
    regional_report = pd.DataFrame()
    print("Skipping property report: no property column found.")

# Write summaries to SQLite.
with sqlite3.connect(DB_PATH) as conn:
    if not regional_report.empty:
        regional_report.to_sql(
            "summary_by_property", conn, if_exists="replace", index=False
        )
    if not channel_summary.empty:
        channel_summary.to_sql(
            "summary_by_channel", conn, if_exists="replace", index=False
        )
    if not room_summary.empty:
        room_summary.to_sql(
            "summary_top5_room_types", conn, if_exists="replace", index=False
        )

with open(OUT / "uc5_answers.txt", "w", encoding="utf-8") as f:
    f.write("USE CASE 5 - BUSINESS SUMMARIES\n")
    f.write(f"Bookings in source data: {len(df)}\n")
    f.write(f"Non-cancelled bookings with valid revenue: {len(valid)}\n")

    if not room_summary.empty:
        f.write(f"Top room type by realized revenue: {room_summary.iloc[0]['room_type']}\n")
        f.write(f"Top room type revenue: {room_summary.iloc[0]['revenue']:.2f}\n")
    else:
        f.write("Top room type by realized revenue: unavailable\n")

    if not channel_summary.empty:
        f.write(
            "Highest cancellation rate channel: "
            f"{channel_summary.iloc[0]['channel_name']}\n"
        )
        f.write(
            f"Highest cancellation rate (%): "
            f"{channel_summary.iloc[0]['cancellation_rate']:.2f}\n"
        )
    else:
        f.write("Cancellation rate by channel: unavailable\n")

    if not regional_report.empty:
        f.write(
            f"Highest revenue property: "
            f"{regional_report.iloc[0]['property_name']}\n"
        )
        f.write(f"Highest property revenue: {regional_report.iloc[0]['revenue']:.2f}\n")
    else:
        f.write("Highest revenue property: unavailable\n")

print("UC5 completed.")