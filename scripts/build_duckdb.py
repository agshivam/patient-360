#!/usr/bin/env python3
"""Load the Synthea CSV files into DuckDB, build the report tables, export small Parquet files.

Usage:
    python scripts/build_duckdb.py

Layers (the same idea as Epic's Clarity and Caboodle, kept small for now):
    raw     files loaded as-is, every column as text
    marts   cleaned dimension and fact tables, plus small aggregates for the Streamlit app
The Streamlit app reads only the aggregates in app_data/, so it can be deployed without the raw data.
"""
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "csv"
DB_PATH = ROOT / "data" / "patient360.duckdb"
APP_DATA = ROOT / "app_data"
SQL_FILE = ROOT / "sql" / "marts.sql"

RAW_TABLES = ["patients", "encounters", "conditions", "observations", "payers", "organizations", "providers"]


def main() -> None:
    if not RAW_DIR.exists():
        sys.exit("No CSV files found in data/raw/csv. Run: python scripts/generate_synthea.py")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))

    con.execute("CREATE SCHEMA raw")
    for table in RAW_TABLES:
        csv_path = (RAW_DIR / f"{table}.csv").as_posix()
        con.execute(
            f"CREATE TABLE raw.{table} AS "
            f"SELECT * FROM read_csv('{csv_path}', header = true, all_varchar = true)"
        )
        count = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
        print(f"raw.{table:<14} {count:>9,} rows")

    for statement in SQL_FILE.read_text().split(";"):
        if statement.strip():
            con.execute(statement)

    APP_DATA.mkdir(exist_ok=True)
    exported = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'marts' AND (table_name LIKE 'agg_%' OR table_name LIKE 'masked_%') "
        "ORDER BY table_name"
    ).fetchall()
    for (name,) in exported:
        target = (APP_DATA / f"{name}.parquet").as_posix()
        con.execute(f"COPY marts.{name} TO '{target}' (FORMAT PARQUET)")
        print(f"exported app_data/{name}.parquet")

    con.close()
    print("\nDone. Next: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()
