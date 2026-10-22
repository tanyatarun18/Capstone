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

for col in ["LengthOfStay", "LeadTimeDays", "total_amount", "rating"]:
    if col not in df.columns:
        raise ValueError(f"UC3 requires column '{col}'.")
    df[col] = pd.to_numeric(df[col], errors="coerce")

cancel_map = {"true": True, "1": True, "yes": True,
              "false": False, "0": False, "no": False}
df["cancelled"] = (
    df["cancelled"].astype(str).str.strip().str.lower().map(cancel_map)
)

loyalty_col = "loyalty_tier" if "loyalty_tier" in df.columns else None
property_col = next(
    (c for c in ["property_name", "hotel_name", "property_code"] if c in df.columns),
    None
)

# 1. Cancellation rate by loyalty tier
if loyalty_col:
    known = df.dropna(subset=["cancelled"]).copy()
    known[loyalty_col] = known[loyalty_col].fillna("Unknown")
    cancel_rate = known.groupby(loyalty_col)["cancelled"].mean() * 100

    if not cancel_rate.empty:
        fig, ax = plt.subplots(figsize=(9, 5))
        cancel_rate.sort_values().plot(kind="bar", ax=ax)
        ax.set_title("Cancellation Rate by Loyalty Tier")
        ax.set_xlabel("Loyalty tier")
        ax.set_ylabel("Cancellation rate (%)")
        ax.tick_params(axis="x", labelrotation=20)
        fig.tight_layout()
        fig.savefig(GRAPHS / "uc3_cancellation_by_loyalty.png", dpi=160)
        plt.close(fig)
else:
    cancel_rate = pd.Series(dtype=float)

# 2. Length-of-stay distribution
stay = df.loc[df["LengthOfStay"].ge(0), "LengthOfStay"].dropna()
if not stay.empty:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(stay, bins=15, edgecolor="black")
    ax.set_title("Length of Stay Distribution")
    ax.set_xlabel("Length of stay (nights)")
    ax.set_ylabel("Number of bookings")
    fig.tight_layout()
    fig.savefig(GRAPHS / "uc3_length_of_stay.png", dpi=160)
    plt.close(fig)

# 3. Lead time vs booking amount
scatter = df.dropna(subset=["LeadTimeDays", "total_amount"]).copy()
scatter = scatter.loc[scatter["LeadTimeDays"].ge(0)]
if not scatter.empty:
    fig, ax = plt.subplots(figsize=(10, 6))
    if loyalty_col:
        sns.scatterplot(
            data=scatter, x="LeadTimeDays", y="total_amount",
            hue=loyalty_col, ax=ax
        )
    else:
        sns.scatterplot(
            data=scatter, x="LeadTimeDays", y="total_amount", ax=ax
        )
    ax.set_title("Lead Time vs Total Booking Amount")
    ax.set_xlabel("Lead time (days)")
    ax.set_ylabel("Total booking amount")
    fig.tight_layout()
    fig.savefig(GRAPHS / "uc3_lead_time_vs_amount.png", dpi=160)
    plt.close(fig)

# 4. Ratings by property and IQR outliers
if property_col:
    rating_means = df.groupby(property_col)["rating"].mean().dropna()
else:
    rating_means = pd.Series(dtype=float)

if not rating_means.empty:
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.boxplot(x=rating_means.values, ax=ax)
    ax.set_title("Distribution of Mean Guest Ratings by Property")
    ax.set_xlabel("Mean guest rating")
    fig.tight_layout()
    fig.savefig(GRAPHS / "uc3_property_rating_boxplot.png", dpi=160)
    plt.close(fig)

    q1 = rating_means.quantile(0.25)
    q3 = rating_means.quantile(0.75)
    iqr = q3 - q1
    low = q1 - 1.5 * iqr
    high = q3 + 1.5 * iqr
    outliers = rating_means[(rating_means < low) | (rating_means > high)]
else:
    q1 = q3 = iqr = low = high = float("nan")
    outliers = pd.Series(dtype=float)

corr_data = df[["LeadTimeDays", "total_amount"]].dropna()
corr_data = corr_data.loc[corr_data["LeadTimeDays"].ge(0)]
corr = corr_data["LeadTimeDays"].corr(corr_data["total_amount"]) if len(corr_data) >= 2 else float("nan")

with open(OUT / "uc3_answers.txt", "w", encoding="utf-8") as f:
    f.write("USE CASE 3 - STATISTICAL ANALYSIS\n")
    f.write(f"Lowest cancellation rate tier: {cancel_rate.idxmin() if not cancel_rate.empty else 'Unavailable'}\n")
    f.write(f"Lowest cancellation rate (%): {cancel_rate.min():.2f}\n" if not cancel_rate.empty else "Lowest cancellation rate (%): unavailable\n")
    f.write(f"Lead time vs amount correlation: {corr:.4f}\n" if pd.notna(corr) else "Lead time vs amount correlation: unavailable\n")
    f.write(f"Rating IQR lower boundary: {low:.3f}\n")
    f.write(f"Rating IQR upper boundary: {high:.3f}\n")
    f.write("Rating outlier properties:\n")
    f.write(outliers.to_string() if not outliers.empty else "None detected or insufficient data")
    f.write("\n\nMean rating by property:\n")
    f.write(rating_means.to_string() if not rating_means.empty else "No valid property ratings")

print("UC3 completed.")