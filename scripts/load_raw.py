#!/usr/bin/env python3
"""Load the Synthea CSV files into the DuckDB raw layer (every column as text).

Usage:
    python scripts/load_raw.py

This is the only step that touches the CSV files. dbt builds everything else from the raw schema:
    raw      files loaded as-is, every column as text (this script)
    staging  typed and renamed views (dbt)
    marts    dimension, fact and aggregate tables (dbt)
Then scripts/export_app_data.py writes the small Parquet files the Streamlit app reads.
"""
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "csv"
DB_PATH = ROOT / "data" / "patient360.duckdb"

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

    con.close()
    print("\nDone. Next: cd dbt && dbt build")


if __name__ == "__main__":
    main()
