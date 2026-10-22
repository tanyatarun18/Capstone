from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
GRAPHS = ROOT / "Graphs"
OUT.mkdir(exist_ok=True)
GRAPHS.mkdir(exist_ok=True)

df = pd.read_csv(OUT / "enriched_bookings.csv")
required = ["booking_date", "cancelled", "total_amount", "room_rate"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"UC2 missing required columns: {missing}")

try:
    df["booking_date"] = pd.to_datetime(df["booking_date"], format='mixed', errors="coerce")
except ValueError:
    df["booking_date"] = pd.to_datetime(df["booking_date"], errors="coerce")

for col in ["total_amount", "room_rate"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

cancel_map = {"true": True, "1": True, "yes": True,
              "false": False, "0": False, "no": False}
df["cancelled"] = (
    df["cancelled"].astype(str).str.strip().str.lower().map(cancel_map)
)
df["BookingDay"] = df["booking_date"].dt.strftime("%Y-%m-%d")

valid = df.loc[df["cancelled"].eq(False)].copy()
valid = valid.dropna(subset=["booking_date"])
valid["total_amount"] = pd.to_numeric(valid["total_amount"], errors="coerce")

channel_col = "channel_name" if "channel_name" in valid.columns else "channel_code"
room_col = "room_category" if "room_category" in valid.columns else "room_type_code"

if channel_col not in valid.columns:
    raise ValueError("UC2 needs channel_name or channel_code.")
if room_col not in valid.columns:
    raise ValueError("UC2 needs room_category or room_type_code.")

valid[channel_col] = valid[channel_col].fillna("Unknown").astype(str)
valid[room_col] = valid[room_col].fillna("Unknown").astype(str)

# 1. Revenue by booking day and channel
rev = valid.pivot_table(
    index="BookingDay", columns=channel_col, values="total_amount",
    aggfunc="sum", fill_value=0
).sort_index()

if not rev.empty:
    ax = rev.plot(kind="bar", stacked=True, figsize=(12, 6))
    ax.set_title("Realized Revenue by Booking Day and Channel")
    ax.set_xlabel("Booking day")
    ax.set_ylabel("Revenue")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(GRAPHS / "uc2_revenue_by_day_channel.png", dpi=160)
    plt.close()

# 2. Booking share by channel
share = valid[channel_col].value_counts()
if not share.empty:
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.pie(share.values, labels=share.index, autopct="%1.1f%%", startangle=90)
    ax.set_title("Non-cancelled Booking Share by Channel")
    ax.axis("equal")
    fig.tight_layout()
    fig.savefig(GRAPHS / "uc2_booking_share_channel.png", dpi=160)
    plt.close(fig)

# 3. Average room rate by booking day
adr = valid.dropna(subset=["room_rate"]).groupby("BookingDay")["room_rate"].mean().sort_index()
if not adr.empty:
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(adr.index, adr.values, marker="o")
    ax.set_title("Average Room Rate by Booking Day")
    ax.set_xlabel("Booking day")
    ax.set_ylabel("Average room rate")
    ax.tick_params(axis="x", labelrotation=45)
    fig.tight_layout()
    fig.savefig(GRAPHS / "uc2_adr_trend.png", dpi=160)
    plt.close(fig)

# 4. Total booking amount by room category
box_data = valid.dropna(subset=["total_amount"])
if not box_data.empty:
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(data=box_data, x=room_col, y="total_amount", ax=ax)
    ax.set_title("Booking Amount by Room Category")
    ax.set_xlabel("Room category")
    ax.set_ylabel("Booking amount")
    ax.tick_params(axis="x", labelrotation=25)
    fig.tight_layout()
    fig.savefig(GRAPHS / "uc2_room_category_boxplot.png", dpi=160)
    plt.close(fig)

channel_revenue = valid.groupby(channel_col)["total_amount"].sum().sort_values(ascending=False)
category_stats = valid.groupby(room_col)["total_amount"].agg(
    median="median",
    spread=lambda x: x.quantile(0.75) - x.quantile(0.25)
).dropna(how="all")

if len(adr) >= 2:
    adr_trend = "Upward" if adr.iloc[-1] > adr.iloc[0] else (
        "Downward" if adr.iloc[-1] < adr.iloc[0] else "Flat"
    )
else:
    adr_trend = "Insufficient data"

with open(OUT / "uc2_answers.txt", "w", encoding="utf-8") as f:
    f.write("USE CASE 2 - EXPLORATORY ANALYSIS\n")
    f.write(f"Non-cancelled bookings analyzed: {len(valid)}\n")
    f.write(f"Highest revenue channel: {channel_revenue.idxmax() if not channel_revenue.empty else 'Unavailable'}\n")
    f.write(
        f"Highest median room category: {category_stats['median'].idxmax() if not category_stats.empty and category_stats['median'].notna().any() else 'Unavailable'}\n"
    )
    f.write(
        f"Widest IQR room category: {category_stats['spread'].idxmax() if not category_stats.empty and category_stats['spread'].notna().any() else 'Unavailable'}\n"
    )
    f.write(f"Average room-rate trend (first vs last day): {adr_trend}\n\n")
    f.write("Revenue by channel:\n" + channel_revenue.to_string())
    f.write("\n\nRoom category statistics:\n" + category_stats.to_string())

print("UC2 completed.")