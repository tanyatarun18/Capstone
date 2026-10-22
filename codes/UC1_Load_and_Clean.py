from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "Data"
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)

def read_csv(name):
    path = DATA / name
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    return pd.read_csv(path, low_memory=False)

bookings = read_csv("hotel_bookings_dataset.csv")
properties = read_csv("hotel_property_info.csv")
channels = read_csv("booking_channel_info.csv")
markets = read_csv("city_market_info.csv")
rooms = read_csv("room_type_codes.csv")
loyalty = read_csv("loyalty_tier_info.csv")

bookings.columns = bookings.columns.str.strip().str.lower()
lookups = [properties, channels, markets, rooms, loyalty]
for frame in lookups:
    frame.columns = frame.columns.str.strip().str.lower()

required = [
    "booking_id", "booking_date", "checkin_date", "checkout_date",
    "channel_code", "rate_plan", "property_code", "room_type_code",
    "market_code", "loyalty_tier", "nights", "adults", "children",
    "room_rate", "total_amount", "rating", "cancelled",
    "special_requests_desc", "date_of_update"
]
missing = [c for c in required if c not in bookings.columns]
if missing:
    raise ValueError(f"Booking dataset is missing required columns: {missing}")

original_rows, original_columns = bookings.shape

# Initial quality report, before cleaning.
quality = pd.DataFrame({
    "column": bookings.columns,
    "missing_count": bookings.isna().sum().values,
    "missing_percent": (bookings.isna().mean().values * 100).round(2),
    "data_type": bookings.dtypes.astype(str).values,
})
quality.to_csv(OUT / "data_quality_report.csv", index=False)

# Parse dates safely handling mixed formats across the dataset
for col in ["booking_date", "checkin_date", "checkout_date", "date_of_update"]:
    try:
        bookings[col] = pd.to_datetime(bookings[col], format='mixed', errors='coerce')
    except ValueError:
        bookings[col] = pd.to_datetime(bookings[col], errors='coerce')

# Standardize text and join keys.
uppercase_cols = [
    "channel_code", "rate_plan", "property_code",
    "room_type_code", "market_code"
]
for col in uppercase_cols:
    bookings[col] = bookings[col].astype("string").str.strip().str.upper()

bookings["loyalty_tier"] = (
    bookings["loyalty_tier"].astype("string").str.strip().str.title()
)

# Normalize common Boolean encodings; unknown values remain missing.
cancel_map = {
    "true": True, "1": True, "yes": True, "y": True,
    "false": False, "0": False, "no": False, "n": False
}
bookings["cancelled"] = (
    bookings["cancelled"].astype("string").str.strip().str.lower()
    .map(cancel_map).astype("boolean")
)

numeric_cols = [
    "nights", "adults", "children", "room_rate", "total_amount", "rating"
]
for col in numeric_cols:
    bookings[col] = pd.to_numeric(bookings[col], errors="coerce")

# Invalid values are marked missing rather than silently retained.
for col in ["nights", "adults", "children"]:
    bookings.loc[bookings[col] < 0, col] = np.nan

bookings.loc[bookings["room_rate"] < 0, "room_rate"] = np.nan
bookings.loc[bookings["total_amount"] < 0, "total_amount"] = np.nan
bookings.loc[~bookings["rating"].between(1, 5), "rating"] = np.nan

# Children can reasonably be zero when missing. Other fields are not
# automatically filled unless there is a defensible source value.
bookings["children"] = bookings["children"].fillna(0)

rate_median = bookings["room_rate"].median()
if pd.notna(rate_median):
    bookings["room_rate"] = bookings["room_rate"].fillna(rate_median)

if "special_requests_desc" in bookings.columns:
    bookings["special_requests_desc"] = (
        bookings["special_requests_desc"].fillna("No request recorded")
    )

# Derive nights from valid stay dates when the original value is absent.
derived_nights = (
    bookings["checkout_date"] - bookings["checkin_date"]
).dt.total_seconds() / 86400
missing_nights = bookings["nights"].isna() & derived_nights.ge(0)
bookings.loc[missing_nights, "nights"] = derived_nights[missing_nights]

# Recalculate total only when absent and sufficient inputs exist.
missing_total = bookings["total_amount"].isna()
can_calculate = (
    missing_total
    & bookings["room_rate"].notna()
    & bookings["nights"].notna()
)
bookings.loc[can_calculate, "total_amount"] = (
    bookings.loc[can_calculate, "room_rate"]
    * bookings.loc[can_calculate, "nights"]
)

bookings["BookingDay"] = bookings["booking_date"].dt.strftime("%Y-%m-%d")
bookings["BookingHour"] = bookings["booking_date"].dt.hour
bookings["LengthOfStay"] = derived_nights
bookings["LeadTimeDays"] = (
    bookings["checkin_date"] - bookings["booking_date"]
).dt.total_seconds() / 86400

# Flag suspicious date relationships for review.
bookings["date_validation_issue"] = (
    bookings["checkout_date"].lt(bookings["checkin_date"])
    | bookings["booking_date"].gt(bookings["checkin_date"])
)
bookings.loc[bookings["checkout_date"].lt(bookings["checkin_date"]),
             "LengthOfStay"] = np.nan

# Normalize lookup tables and reject duplicate keys that would multiply rows.
lookup_specs = [
    (properties, "property_code", ["property_code"]),
    (channels, "channel_code", ["channel_code"]),
    (markets, "market_code", ["market_code"]),
    (rooms, "room_type_code", ["room_type_code"]),
    (loyalty, "loyalty_tier", ["loyalty_tier"]),
]

for frame, key, _ in lookup_specs:
    if key not in frame.columns:
        raise ValueError(f"Lookup table is missing join key '{key}'")
    frame[key] = frame[key].astype("string").str.strip()
    if key != "loyalty_tier":
        frame[key] = frame[key].str.upper()
    else:
        frame[key] = frame[key].str.title()

    duplicates = frame[key].duplicated(keep=False) & frame[key].notna()
    if duplicates.any():
        values = frame.loc[duplicates, key].astype(str).unique()[:10].tolist()
        raise ValueError(
            f"Duplicate lookup keys in {key}: {values}. "
            "Resolve duplicates before enrichment."
        )

enriched = bookings.copy()
for frame, key, _ in lookup_specs:
    enriched = enriched.merge(
        frame, on=key, how="left", validate="many_to_one",
        suffixes=("", f"_{key.removesuffix('_code')}")
    )

# Save data.
bookings.to_csv(OUT / "cleaned_bookings.csv", index=False)
enriched.to_csv(OUT / "enriched_bookings.csv", index=False)

# Post-cleaning quality report.
post_quality = pd.DataFrame({
    "column": bookings.columns,
    "missing_count": bookings.isna().sum().values,
    "missing_percent": (bookings.isna().mean().values * 100).round(2),
    "data_type": bookings.dtypes.astype(str).values,
})
post_quality.to_csv(OUT / "data_quality_report_after_cleaning.csv", index=False)

db_path = OUT / "hotel_bookings.db"
with sqlite3.connect(db_path) as conn:
    bookings.to_sql("bookings", conn, if_exists="replace", index=False)
    enriched.to_sql("enriched_bookings", conn, if_exists="replace", index=False)
    properties.to_sql("hotel_properties", conn, if_exists="replace", index=False)
    channels.to_sql("booking_channels", conn, if_exists="replace", index=False)
    markets.to_sql("city_markets", conn, if_exists="replace", index=False)
    rooms.to_sql("room_types", conn, if_exists="replace", index=False)
    loyalty.to_sql("loyalty_tiers", conn, if_exists="replace", index=False)

known_cancel = bookings["cancelled"].dropna()
avg_lead = bookings["LeadTimeDays"].mean()

with open(OUT / "analysis_answers.txt", "w", encoding="utf-8") as f:
    f.write("USE CASE 1 - DATA CLEANING\n")
    f.write(f"Original rows: {original_rows}\n")
    f.write(f"Original columns: {original_columns}\n")
    f.write(f"Rows after cleaning: {len(bookings)}\n")
    f.write(f"Unique room type codes: {bookings['room_type_code'].nunique()}\n")
    f.write(f"Unique property codes: {bookings['property_code'].nunique()}\n")
    f.write(f"Average lead time (days): {avg_lead:.2f}\n" if pd.notna(avg_lead)
             else "Average lead time (days): unavailable\n")
    f.write(
        f"Cancellation rate (%): {known_cancel.mean() * 100:.2f}\n"
        if not known_cancel.empty else "Cancellation rate (%): unavailable\n"
    )
    f.write(
        f"Columns above 50% missing after cleaning: "
        f"{post_quality.loc[post_quality['missing_percent'] > 50, 'column'].tolist()}\n"
    )
    f.write(f"Rows with date validation issues: {int(bookings['date_validation_issue'].sum())}\n")

print(f"UC1 complete. Cleaned rows: {len(bookings)}; enriched rows: {len(enriched)}")
print(f"Database: {db_path}")