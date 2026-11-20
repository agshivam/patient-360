#!/usr/bin/env python3
"""Export the small aggregate tables built by dbt to Parquet files for the Streamlit app.

Usage:
    python scripts/export_app_data.py
"""
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "patient360.duckdb"
APP_DATA = ROOT / "app_data"


def main() -> None:
    if not DB_PATH.exists():
        sys.exit("No database found. Run: python scripts/load_raw.py, then: cd dbt && dbt build")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    APP_DATA.mkdir(exist_ok=True)
    names = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'marts' AND (table_name LIKE 'agg_%' OR table_name LIKE 'masked_%') "
        "ORDER BY table_name"
    ).fetchall()
    if not names:
        sys.exit("No aggregate tables in the marts schema. Run: cd dbt && dbt build")
    for (name,) in names:
        target = (APP_DATA / f"{name}.parquet").as_posix()
        con.execute(f"COPY marts.{name} TO '{target}' (FORMAT PARQUET)")
        print(f"exported app_data/{name}.parquet")
    con.close()
    print("\nDone. Next: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()
