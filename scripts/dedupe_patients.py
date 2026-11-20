#!/usr/bin/env python3
"""Find duplicate patient records with fuzzy matching (Splink) and measure how well it works.

Usage (after scripts/inject_dirty_data.py):
    python scripts/dedupe_patients.py

How it works:
    1. Names are cleaned: Synthea adds digits to names (Jacinto644), which are removed before matching.
    2. Candidate pairs come from two blocking rules (same birth date, or same SSN), so we never compare all pairs.
    3. Each pair is scored on name similarity (Jaro-Winkler), birth date, gender, city and SSN.
       Splink learns how much each field should count from the data itself (no labels needed).
    4. Pairs above the match threshold are grouped into clusters, one cluster per real person.
    5. The result is compared with truth.injected_duplicates to report precision and recall.
Output: dedupe.patient_clusters in DuckDB and app_data/agg_dedupe_metrics.parquet for the report.
"""
import sys
from pathlib import Path

import duckdb
import pandas as pd
import splink.comparison_library as cl
from splink import DuckDBAPI, Linker, SettingsCreator, block_on

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "patient360.duckdb"
APP_DATA = ROOT / "app_data"
THRESHOLD = 0.9


def main() -> None:
    if not DB_PATH.exists():
        sys.exit("No database found. Run: python scripts/load_raw.py")
    con = duckdb.connect(str(DB_PATH))
    has_truth = con.execute(
        "SELECT count(*) FROM information_schema.schemata WHERE schema_name = 'truth'"
    ).fetchone()[0]
    if not has_truth:
        sys.exit("No injected duplicates found. Run: python scripts/inject_dirty_data.py")

    people = con.execute("""
        SELECT Id AS patient_id,
               lower(regexp_replace(FIRST, '[0-9]+', '', 'g')) AS first_name,
               lower(regexp_replace(LAST, '[0-9]+', '', 'g')) AS last_name,
               BIRTHDATE AS birth_date,
               GENDER AS gender,
               lower(CITY) AS city,
               SSN AS ssn
        FROM raw.patients
    """).df()

    settings = SettingsCreator(
        link_type="dedupe_only",
        unique_id_column_name="patient_id",
        comparisons=[
            cl.JaroWinklerAtThresholds("first_name", [0.92, 0.8]),
            cl.JaroWinklerAtThresholds("last_name", [0.92, 0.8]),
            cl.ExactMatch("birth_date"),
            cl.ExactMatch("gender"),
            cl.JaroWinklerAtThresholds("city", [0.9]),
            cl.ExactMatch("ssn"),
        ],
        blocking_rules_to_generate_predictions=[block_on("birth_date"), block_on("ssn")],
    )
    db_api = DuckDBAPI()
    people_sdf = db_api.register(people)
    linker = Linker(people_sdf, settings)
    linker.training.estimate_probability_two_random_records_match(
        [block_on("first_name", "last_name", "birth_date")], recall=0.7
    )
    linker.training.estimate_u_using_random_sampling(max_pairs=1_000_000)
    linker.training.estimate_parameters_using_expectation_maximisation(block_on("birth_date"))
    linker.training.estimate_parameters_using_expectation_maximisation(block_on("last_name"))

    pairs = linker.inference.predict(threshold_match_probability=0.5)
    pairs_df = pairs.as_pandas_dataframe()
    clusters = linker.clustering.cluster_pairwise_predictions_at_threshold(pairs, THRESHOLD).as_pandas_dataframe()

    con.execute("CREATE SCHEMA IF NOT EXISTS dedupe")
    con.register("clusters_df", clusters[["patient_id", "cluster_id"]])
    con.execute("CREATE OR REPLACE TABLE dedupe.patient_clusters AS SELECT * FROM clusters_df")

    truth = con.execute("SELECT duplicate_id, original_id FROM truth.injected_duplicates").df()
    true_pairs = {frozenset(p) for p in zip(truth.duplicate_id, truth.original_id)}
    hits = pairs_df[pairs_df.match_probability >= THRESHOLD]
    found_pairs = {frozenset(p) for p in zip(hits.patient_id_l, hits.patient_id_r)}
    true_found = len(found_pairs & true_pairs)
    precision = true_found / len(found_pairs) if found_pairs else 0.0
    recall = true_found / len(true_pairs) if true_pairs else 0.0

    exact = con.execute("""
        SELECT count(*) FROM (SELECT 1 FROM raw.patients
        GROUP BY lower(regexp_replace(FIRST, '[0-9]+', '', 'g')), lower(regexp_replace(LAST, '[0-9]+', '', 'g')), BIRTHDATE
        HAVING count(*) > 1)
    """).fetchone()[0]

    metrics = pd.DataFrame(
        [
            ("Patient records", len(people)),
            ("Duplicates injected", len(true_pairs)),
            ("Found by exact name and birth date", exact),
            ("Found by fuzzy matching", true_found),
            ("Wrong matches", len(found_pairs) - true_found),
            ("Precision (%)", round(100 * precision, 1)),
            ("Recall (%)", round(100 * recall, 1)),
            ("Unique people after merging", clusters.cluster_id.nunique()),
        ],
        columns=["metric", "value"],
    )
    APP_DATA.mkdir(exist_ok=True)
    metrics.to_parquet(APP_DATA / "agg_dedupe_metrics.parquet", index=False)
    print(metrics.to_string(index=False))
    print("\nWrote dedupe.patient_clusters and app_data/agg_dedupe_metrics.parquet")


if __name__ == "__main__":
    main()
