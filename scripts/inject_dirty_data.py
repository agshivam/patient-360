#!/usr/bin/env python3
"""Inject realistic faults into the raw layer, on purpose, so the checks can prove they catch them.

Usage (after scripts/load_raw.py):
    python scripts/inject_dirty_data.py                  # duplicates, bad dates, negative cost
    python scripts/inject_dirty_data.py --break-schema   # also rename a source column
Undo everything by running scripts/load_raw.py again (it rebuilds the raw layer from the CSV files).

Faults injected into raw (a fixed seed, so every run is the same):
    1. Duplicate patients: the same person registered twice, with a typo in the name,
       sometimes a missing SSN and sometimes a different city. The ground truth is written to
       truth.injected_duplicates so the matching quality can be measured.
    2. Encounters that end before they start.
    3. Encounters with a negative claim cost.
    4. Optional: a renamed source column (BIRTHDATE becomes DOB), which must fail the build loudly.
"""
import argparse
import random
import sys
import uuid
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "patient360.duckdb"


def typo(word: str, rng: random.Random) -> str:
    """Return the word with one realistic data entry error."""
    if len(word) < 3:
        return word
    kind = rng.choice(["drop", "swap", "double", "case"])
    i = rng.randrange(1, len(word) - 1)
    if kind == "drop":
        return word[:i] + word[i + 1:]
    if kind == "swap":
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if kind == "double":
        return word[:i] + word[i] + word[i:]
    return word.upper()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duplicate-rate", type=float, default=0.05, help="share of patients duplicated")
    parser.add_argument("--break-schema", action="store_true", help="rename raw.patients.BIRTHDATE to DOB")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not DB_PATH.exists():
        sys.exit("No database found. Run: python scripts/load_raw.py")
    rng = random.Random(args.seed)
    con = duckdb.connect(str(DB_PATH))

    if con.execute("SELECT count(*) FROM information_schema.schemata WHERE schema_name = 'truth'").fetchone()[0]:
        sys.exit("Dirty data is already injected. Run scripts/load_raw.py to start from clean data.")

    cols = [r[0] for r in con.execute("DESCRIBE raw.patients").fetchall()]
    originals = con.execute("SELECT * FROM raw.patients").fetchall()
    count = max(5, int(len(originals) * args.duplicate_rate))
    chosen = rng.sample(originals, count)

    new_rows, truth = [], []
    for row in chosen:
        rec = dict(zip(cols, row))
        orig_id = rec["Id"]
        rec["Id"] = str(uuid.UUID(int=rng.getrandbits(128)))
        if rng.random() < 0.6:
            rec["FIRST"] = typo(rec["FIRST"] or "", rng)
        if rng.random() < 0.6:
            rec["LAST"] = typo(rec["LAST"] or "", rng)
        if rng.random() < 0.4:
            rec["SSN"] = None
        if rng.random() < 0.3:
            rec["CITY"] = typo(rec["CITY"] or "", rng)
        new_rows.append([rec[c] for c in cols])
        truth.append((rec["Id"], orig_id))

    placeholders = ", ".join("?" for _ in cols)
    con.executemany(f"INSERT INTO raw.patients VALUES ({placeholders})", new_rows)
    con.execute("CREATE SCHEMA truth")
    con.execute("CREATE TABLE truth.injected_duplicates (duplicate_id VARCHAR, original_id VARCHAR)")
    con.executemany("INSERT INTO truth.injected_duplicates VALUES (?, ?)", truth)
    print(f"Injected {count} duplicate patients (raw.patients is now {len(originals) + count} rows)")

    n_bad = max(3, count // 2)
    con.execute(f"""
        UPDATE raw.encounters SET STOP = START
        WHERE Id IN (SELECT Id FROM raw.encounters WHERE TRY_CAST(replace(START, 'Z', '') AS TIMESTAMP) IS NOT NULL
                     ORDER BY hash(Id) LIMIT {n_bad})
    """)
    con.execute(f"""
        UPDATE raw.encounters
        SET STOP = strftime(TRY_CAST(replace(START, 'Z', '') AS TIMESTAMP) - INTERVAL 2 DAY, '%Y-%m-%dT%H:%M:%SZ')
        WHERE Id IN (SELECT Id FROM raw.encounters WHERE TRY_CAST(replace(START, 'Z', '') AS TIMESTAMP) IS NOT NULL
                     ORDER BY hash(Id) LIMIT {n_bad})
    """)
    con.execute(f"""
        UPDATE raw.encounters SET TOTAL_CLAIM_COST = '-250.00'
        WHERE Id IN (SELECT Id FROM raw.encounters ORDER BY hash(Id || 'cost') LIMIT {n_bad})
    """)
    print(f"Broke {n_bad} encounters (end before start) and set {n_bad} claim costs negative")

    if args.break_schema:
        con.execute("ALTER TABLE raw.patients RENAME COLUMN BIRTHDATE TO DOB")
        print("Renamed raw.patients.BIRTHDATE to DOB. dbt build should now fail loudly.")

    con.close()
    print("\nNext: cd dbt && dbt build   (tests should fail)   then: python scripts/dedupe_patients.py")


if __name__ == "__main__":
    main()
