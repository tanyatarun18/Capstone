
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import (
    Flask, flash, make_response, redirect, render_template,
    request, send_from_directory, session, url_for
)
from werkzeug.utils import secure_filename


# =========================================================
# CONFIGURATION
# =========================================================

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
GRAPHS = ROOT / "Graphs"
DATA_DIR = Path(__file__).resolve().parent / "data"
UPLOADS = DATA_DIR / "uploads"
DB_PATH = OUT / "hotel_bookings.db"

for folder in (OUT, GRAPHS, DATA_DIR, UPLOADS):
    folder.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = "grand-horizon-local-change-before-deployment"
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def table_exists(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def initialize_database():
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingested_bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_data TEXT NOT NULL,
                property_name TEXT,
                region TEXT,
                booking_date TEXT,
                revenue REAL,
                adr REAL,
                is_cancelled INTEGER NOT NULL DEFAULT 0,
                source_file TEXT,
                imported_at TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT,
                rows_received INTEGER DEFAULT 0,
                rows_imported INTEGER DEFAULT 0,
                rows_rejected INTEGER DEFAULT 0,
                imported_at TEXT,
                status TEXT,
                details TEXT
            )
        """)

        # Add columns if this database was created by an older version.
        columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(ingestion_history)"
            ).fetchall()
        }
        for name in ("duplicate_rows", "missing_cells"):
            if name not in columns:
                conn.execute(
                    f"ALTER TABLE ingestion_history ADD COLUMN {name} "
                    "INTEGER DEFAULT 0"
                )

        conn.commit()
    finally:
        conn.close()


def as_number(value):
    try:
        if value is None or pd.isna(value):
            return None
        number = float(value)
        return number if number == number else None
    except (ValueError, TypeError):
        return None


def parse_cancelled(value):
    return int(
        str(value).strip().lower()
        in {"1", "true", "yes", "y", "cancelled", "canceled", "cancel"}
    )


def seed_existing_data():
    """Load the existing enriched table into the active dataset once."""
    conn = get_db()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM ingested_bookings"
        ).fetchone()[0]

        if count or not table_exists(conn, "enriched_bookings"):
            return

        rows = conn.execute("SELECT * FROM enriched_bookings").fetchall()
        if not rows:
            return

        imported_at = datetime.now().astimezone().isoformat(timespec="seconds")
        records = []

        for row in rows:
            data = dict(row)
            records.append((
                json.dumps(data, default=str, ensure_ascii=False),
                str(data.get("property_name") or data.get("property_code") or "Unknown"),
                str(
                    data.get("region") or data.get("state")
                    or data.get("city") or data.get("country") or "Unknown"
                ),
                str(data.get("booking_date") or ""),
                as_number(data.get("total_amount")),
                as_number(data.get("room_rate")),
                parse_cancelled(data.get("cancelled")),
                "existing_database",
                imported_at,
            ))

        conn.executemany("""
            INSERT INTO ingested_bookings (
                booking_data, property_name, region, booking_date,
                revenue, adr, is_cancelled, source_file, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

        conn.execute("""
            INSERT INTO ingestion_history (
                source_file, rows_received, rows_imported, rows_rejected,
                imported_at, status, details, duplicate_rows, missing_cells
            ) VALUES (?, ?, ?, 0, ?, 'success', ?, 0, 0)
        """, (
            "existing_database", len(records), len(records), imported_at,
            "Initialized from existing enriched_bookings table."
        ))
        conn.commit()
    finally:
        conn.close()


initialize_database()
seed_existing_data()


# =========================================================
# DASHBOARD DATA
# =========================================================

def get_dashboard_metrics():
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT COUNT(*) AS bookings,
                   COUNT(DISTINCT NULLIF(property_name, '')) AS properties,
                   SUM(is_cancelled) AS cancellations,
                   SUM(revenue) AS revenue,
                   AVG(adr) AS adr
            FROM ingested_bookings
        """).fetchone()

        bookings = int(row["bookings"] or 0)
        cancelled = int(row["cancellations"] or 0)

        room_types = 0
        if table_exists(conn, "enriched_bookings"):
            room_types = conn.execute("""
                SELECT COUNT(DISTINCT room_type_code)
                FROM enriched_bookings
                WHERE room_type_code IS NOT NULL
            """).fetchone()[0] or 0

        if not room_types and bookings:
            room_types = conn.execute("""
                SELECT COUNT(DISTINCT
                    json_extract(booking_data, '$.room_type_code'))
                FROM ingested_bookings
            """).fetchone()[0] or 0

        revenue = row["revenue"]
        adr = row["adr"]

        # Supply BOTH naming conventions so existing templates work.
        return {
            "total": bookings,
            "bookings": bookings,
            "total_bookings": bookings,
            "properties": int(row["properties"] or 0),
            "rooms": int(room_types),
            "room_types": int(room_types),
            "cancelled": cancelled,
            "cancellations": cancelled,
            "cancel_rate": cancelled * 100 / bookings if bookings else 0,
            "cancellation_rate": cancelled * 100 / bookings if bookings else 0,
            "revenue": float(revenue) if revenue is not None else None,
            "total_revenue": float(revenue) if revenue is not None else None,
            "adr": float(adr) if adr is not None else None,
            "average_adr": float(adr) if adr is not None else None,
        }
    finally:
        conn.close()


def get_top_properties(limit=5):
    conn = get_db()
    try:
        return [
            dict(row)
            for row in conn.execute("""
                SELECT property_name AS name,
                       property_name,
                       COUNT(*) AS bookings,
                       COUNT(*) AS booking_count,
                       SUM(revenue) AS revenue
                FROM ingested_bookings
                GROUP BY property_name
                ORDER BY bookings DESC
                LIMIT ?
            """, (limit,)).fetchall()
        ]
    finally:
        conn.close()


def get_import_history(limit=10):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT * FROM ingestion_history
            ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()

        result = []
        for row in rows:
            item = dict(row)
            item.setdefault("duplicate_rows", 0)
            item.setdefault("missing_cells", 0)
            result.append(item)
        return result
    finally:
        conn.close()


# =========================================================
# CSV COLUMN RECOGNITION AND DATA QUALITY
# =========================================================

def normalize_name(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


ALIASES = {
    "property_name": {
        "property_name", "hotel_name", "property", "hotel",
        "property_code", "hotel_id", "hotel_code",
    },
    "region": {
        "region", "market", "area", "state", "city", "country",
        "market_name", "city_name",
    },
    "booking_date": {
        "booking_date", "bookingday", "booking_day", "date",
        "date_of_booking", "created_date",
    },
    "revenue": {
        "revenue", "total_amount", "total_revenue", "booking_value",
        "amount", "total_price",
    },
    "adr": {
        "adr", "room_rate", "average_daily_rate", "daily_rate",
        "average_rate",
    },
    "is_cancelled": {
        "is_cancelled", "cancelled", "canceled", "is_canceled",
        "cancellation_status", "booking_status",
    },
}

def find_column(df, target):
    lookup = {normalize_name(col): col for col in df.columns}
    for alias in ALIASES[target]:
        if alias in lookup:
            return lookup[alias]
    return None


def parse_csv(file_storage):
    if not file_storage or not file_storage.filename:
        raise ValueError("Choose a CSV file before importing.")

    filename = secure_filename(file_storage.filename)
    if not filename.lower().endswith(".csv"):
        raise ValueError("Only CSV files are supported.")

    try:
        df = pd.read_csv(file_storage, encoding="utf-8-sig")
    except UnicodeDecodeError:
        file_storage.stream.seek(0)
        df = pd.read_csv(file_storage, encoding="latin-1")
    except pd.errors.EmptyDataError:
        raise ValueError("The selected CSV file is empty.")

    if df.empty:
        raise ValueError("The CSV has no data rows.")

    df.columns = [str(col).strip() for col in df.columns]
    if len(set(df.columns)) != len(df.columns):
        raise ValueError("The CSV contains duplicate column names.")

    received = len(df)
    duplicate_mask = df.duplicated()
    duplicate_count = int(duplicate_mask.sum())
    df = df.loc[~duplicate_mask].copy()

    found = {}
    for field in ALIASES:
        found[field] = find_column(df, field)

    prop_col = found["property_name"]
    region_col = found["region"]
    date_col = found["booking_date"]
    revenue_col = found["revenue"]
    adr_col = found["adr"]
    cancelled_col = found["is_cancelled"]

    df["_app_property"] = (
        df[prop_col].fillna("Unknown").astype(str)
        if prop_col else "Unknown"
    )
    df["_app_region"] = (
        df[region_col].fillna("Unknown").astype(str)
        if region_col else "Unknown"
    )
    df["_app_date"] = df[date_col].astype(str) if date_col else ""

    df["_app_revenue"] = (
        pd.to_numeric(
            df[revenue_col].astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        ) if revenue_col else pd.NA
    )
    df["_app_adr"] = (
        pd.to_numeric(
            df[adr_col].astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        ) if adr_col else pd.NA
    )
    df["_app_cancelled"] = (
        df[cancelled_col].map(parse_cancelled)
        if cancelled_col else 0
    )

    invalid = pd.Series(False, index=df.index)
    if revenue_col:
        invalid |= df["_app_revenue"].notna() & (df["_app_revenue"] < 0)
    if adr_col:
        invalid |= df["_app_adr"].notna() & (df["_app_adr"] < 0)

    rejected = int(invalid.sum())
    df = df.loc[~invalid].copy()

    if df.empty:
        raise ValueError("No valid rows remain. The previous dataset is unchanged.")

    helper_cols = [
        "_app_property", "_app_region", "_app_date",
        "_app_revenue", "_app_adr", "_app_cancelled",
    ]
    raw_df = df.drop(columns=helper_cols, errors="ignore")
    missing_by_column = {
        str(col): int(raw_df[col].isna().sum())
        for col in raw_df.columns
    }
    missing_cells = sum(missing_by_column.values())

    quality = {
        "filename": filename,
        "source_file": filename,
        "rows_received": received,
        "rows_imported": len(df),
        "rows_rejected": rejected,
        "duplicate_rows": duplicate_count,
        "missing_cells": missing_cells,
        "missing_values": missing_cells,
        "missing_by_column": missing_by_column,
        "columns_recognised": [
            key for key, value in found.items() if value
        ],
        "columns_missing": [
            key for key, value in found.items() if not value
        ],
        "columns": len(raw_df.columns),
        "quality_score": round(
            100 * (1 - missing_cells / (len(raw_df) * len(raw_df.columns))),
            2,
        ) if len(raw_df) and len(raw_df.columns) else 100,
        "imported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    return filename, df, quality


def save_import(filename, df, quality):
    """Replace the active dataset atomically; preserve original tables."""
    imported_at = quality["imported_at"]
    helper_cols = {
        "_app_property", "_app_region", "_app_date",
        "_app_revenue", "_app_adr", "_app_cancelled",
    }
    records = []

    for _, row in df.iterrows():
        raw = {}
        for key, value in row.items():
            if key in helper_cols:
                continue
            raw[str(key)] = None if pd.isna(value) else value

        records.append((
            json.dumps(raw, ensure_ascii=False, default=str),
            str(row["_app_property"]),
            str(row["_app_region"]),
            str(row["_app_date"]),
            as_number(row["_app_revenue"]),
            as_number(row["_app_adr"]),
            int(row["_app_cancelled"]),
            filename,
            imported_at,
        ))

    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM ingested_bookings")
        conn.executemany("""
            INSERT INTO ingested_bookings (
                booking_data, property_name, region, booking_date,
                revenue, adr, is_cancelled, source_file, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

        conn.execute("""
            INSERT INTO ingestion_history (
                source_file, rows_received, rows_imported, rows_rejected,
                imported_at, status, details, duplicate_rows, missing_cells
            ) VALUES (?, ?, ?, ?, ?, 'success', ?, ?, ?)
        """, (
            filename,
            quality["rows_received"],
            len(records),
            quality["rows_rejected"],
            imported_at,
            json.dumps(quality, ensure_ascii=False, default=str),
            quality["duplicate_rows"],
            quality["missing_cells"],
        ))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =========================================================
# DASHBOARD
# =========================================================

@app.context_processor
def inject_template_globals():
    return {"current_year": datetime.now().year}


@app.route("/")
@app.route("/dashboard")
def dashboard():
    metrics = get_dashboard_metrics()
    charts = sorted(p.name for p in GRAPHS.glob("*.png") if p.is_file())
    recent = get_import_history(5)
    top = get_top_properties(5)

    conn = get_db()
    try:
        channels = []
        if table_exists(conn, "summary_by_channel"):
            for row in conn.execute("""
                SELECT channel_name AS name, booking_count AS bookings
                FROM summary_by_channel ORDER BY booking_count DESC
            """).fetchall():
                channels.append(dict(row))
    finally:
        conn.close()

    return render_template(
        "index.html",
        stats=metrics,
        metrics=metrics,
        charts=charts,
        graphs=charts,
        top=top,
        top_properties=top,
        recent=recent,
        recent_imports=recent,
        channels=channels,
    )


# =========================================================
# DATA INGESTION
# =========================================================

@app.route("/ingestion", methods=["GET", "POST"])
def ingestion():
    if request.method == "POST":
        file_storage = request.files.get("file")
        try:
            filename, df, quality = parse_csv(file_storage)

            # Store the upload copy. The active dataset is updated only
            # after validation succeeds and the database transaction commits.
            file_storage.stream.seek(0)
            file_storage.save(str(UPLOADS / filename))

            save_import(filename, df, quality)
            session["last_quality"] = quality

            flash(
                f"Import successful: {quality['rows_imported']} records loaded; "
                f"{quality['duplicate_rows']} duplicates removed and "
                f"{quality['rows_rejected']} invalid rows rejected.",
                "success",
            )
            return redirect(url_for("quality"))

        except (ValueError, pd.errors.ParserError) as exc:
            flash(str(exc), "error")
        except Exception:
            app.logger.exception("CSV import failed")
            flash(
                "Import failed. The previous active dataset was preserved. "
                "Check the terminal for technical details.",
                "error",
            )
        return redirect(url_for("ingestion"))

    conn = get_db()
    try:
        current_count = conn.execute(
            "SELECT COUNT(*) FROM ingested_bookings"
        ).fetchone()[0]
    finally:
        conn.close()

    return render_template(
        "ingestion.html",
        current_count=current_count,
        import_history=get_import_history(5),
        recent_imports=get_import_history(5),
    )


# =========================================================
# DATA QUALITY
# =========================================================

@app.route("/quality")
def quality():
    latest = session.get("last_quality")
    history = get_import_history(20)

    # Recover the latest report from the database after a server restart.
    if not latest:
        for item in history:
            if item.get("status") == "success":
                try:
                    details = json.loads(item.get("details") or "{}")
                    if details:
                        latest = details
                        break
                except (json.JSONDecodeError, TypeError):
                    pass

    return render_template(
        "quality.html",
        latest=latest,
        quality=latest,
        report=latest,
        quality_report=latest,
        history=history,
        imports=history,
    )


# =========================================================
# BUSINESS REPORTS
# =========================================================

def get_filter_options():
    conn = get_db()
    try:
        regions = [
            row[0] for row in conn.execute("""
                SELECT DISTINCT region FROM ingested_bookings
                WHERE region IS NOT NULL AND TRIM(region) <> ''
                ORDER BY region
            """).fetchall()
        ]
        properties = [
            row[0] for row in conn.execute("""
                SELECT DISTINCT property_name FROM ingested_bookings
                WHERE property_name IS NOT NULL AND TRIM(property_name) <> ''
                ORDER BY property_name
            """).fetchall()
        ]
        return regions, properties
    finally:
        conn.close()


def query_summary(region="", property_name=""):
    conn = get_db()
    try:
        conditions = []
        params = []

        if region:
            conditions.append("region = ?")
            params.append(region)
        if property_name:
            conditions.append("property_name = ?")
            params.append(property_name)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        rows = [
            dict(row) for row in conn.execute(f"""
                SELECT
                    COALESCE(region, 'Unknown') AS region,
                    COALESCE(property_name, 'Unknown') AS property_name,
                    COUNT(*) AS bookings,
                    SUM(is_cancelled) AS cancellations,
                    ROUND(
                        100.0 * SUM(is_cancelled) / NULLIF(COUNT(*), 0), 2
                    ) AS cancellation_rate,
                    SUM(revenue) AS revenue,
                    AVG(adr) AS average_adr
                FROM ingested_bookings
                {where}
                GROUP BY region, property_name
                ORDER BY bookings DESC, region, property_name
            """, params).fetchall()
        ]

        total_bookings = sum(int(row["bookings"] or 0) for row in rows)
        total_cancelled = sum(int(row["cancellations"] or 0) for row in rows)
        total_revenue = sum(float(row["revenue"] or 0) for row in rows)

        totals = {
            "bookings": total_bookings,
            "cancellations": total_cancelled,
            "revenue": total_revenue,
            "cancellation_rate": (
                total_cancelled * 100 / total_bookings if total_bookings else 0
            ),
        }
        return rows, totals
    finally:
        conn.close()


@app.route("/reports", methods=["GET", "POST"])
def reports():
    selected_region = request.values.get("region", "").strip()
    selected_property = request.values.get("property", "").strip()
    regions, properties = get_filter_options()
    rows, totals = query_summary(selected_region, selected_property)

    return render_template(
        "reports.html",
        regions=regions,
        properties=properties,
        selected_region=selected_region,
        selected_property=selected_property,
        rows=rows,
        results=rows,
        summary=rows,
        totals=totals,
        total_bookings=totals["bookings"],
        total_cancellations=totals["cancellations"],
        total_revenue=totals["revenue"],
        cancellation_rate=totals["cancellation_rate"],
    )


@app.route("/export/regional.csv")
def export_regional():
    region = request.args.get("region", "").strip()
    property_name = request.args.get("property", "").strip()
    rows, _ = query_summary(region, property_name)

    response = make_response(pd.DataFrame(rows).to_csv(index=False))
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = (
        'attachment; filename="regional_performance_summary.csv"'
    )
    return response


# =========================================================
# CHARTS, OUTPUT DOWNLOADS AND HEALTH CHECK
# =========================================================

@app.route("/graphs/<path:filename>")
def graph(filename):
    return send_from_directory(str(GRAPHS), filename)


# Keep the older endpoint name available for compatibility.
@app.route("/graphs-legacy/<path:filename>")
def show_graph(filename):
    return send_from_directory(str(GRAPHS), filename)


@app.route("/output/<path:filename>")
def download_output(filename):
    return send_from_directory(str(OUT), filename, as_attachment=True)


@app.route("/health")
def health():
    metrics = get_dashboard_metrics()
    return {
        "status": "ok",
        "database": str(DB_PATH),
        "active_bookings": metrics["bookings"],
    }


@app.errorhandler(413)
def file_too_large(_error):
    flash("The file exceeds the 25 MB upload limit.", "error")
    return redirect(url_for("ingestion"))


if __name__ == "__main__":
    app.run(debug=True)
