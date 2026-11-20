-- Marts built on top of the raw layer. Every raw column is text, so each cast is explicit and safe.
-- Do not put semicolons inside comments or strings: scripts/build_duckdb.py splits this file on them.

CREATE SCHEMA IF NOT EXISTS marts;

-- Patients, with names and SSN masked for analysts.
CREATE OR REPLACE TABLE marts.dim_patient AS
SELECT
    Id AS patient_id,
    TRY_CAST(BIRTHDATE AS DATE) AS birth_date,
    TRY_CAST(DEATHDATE AS DATE) AS death_date,
    GENDER AS gender,
    RACE AS race,
    CITY AS city,
    STATE AS state,
    DEATHDATE IS NULL AS is_alive,
    upper(substr(FIRST, 1, 1)) || '***' AS first_name_masked,
    upper(substr(LAST, 1, 1)) || '***' AS last_name_masked,
    '***-**-' || right(SSN, 4) AS ssn_masked
FROM raw.patients;

-- One row per encounter.
CREATE OR REPLACE TABLE marts.fact_encounter AS
SELECT
    Id AS encounter_id,
    PATIENT AS patient_id,
    ORGANIZATION AS organization_id,
    PROVIDER AS provider_id,
    PAYER AS payer_id,
    ENCOUNTERCLASS AS encounter_class,
    TRY_CAST(replace(START, 'Z', '') AS TIMESTAMP) AS started_at,
    TRY_CAST(replace(STOP, 'Z', '') AS TIMESTAMP) AS stopped_at,
    date_diff('minute',
              TRY_CAST(replace(START, 'Z', '') AS TIMESTAMP),
              TRY_CAST(replace(STOP, 'Z', '') AS TIMESTAMP)) / 1440.0 AS length_days,
    TRY_CAST(BASE_ENCOUNTER_COST AS DOUBLE) AS base_cost,
    TRY_CAST(TOTAL_CLAIM_COST AS DOUBLE) AS claim_cost,
    TRY_CAST(PAYER_COVERAGE AS DOUBLE) AS payer_coverage,
    DESCRIPTION AS description,
    REASONDESCRIPTION AS reason
FROM raw.encounters;

-- One row per diagnosis.
CREATE OR REPLACE TABLE marts.fact_condition AS
SELECT
    PATIENT AS patient_id,
    ENCOUNTER AS encounter_id,
    CODE AS code,
    DESCRIPTION AS description,
    TRY_CAST(START AS DATE) AS started_on,
    TRY_CAST(STOP AS DATE) AS stopped_on
FROM raw.conditions;

-- Hospital stays, flagged when the same patient is admitted again within 30 days of discharge.
CREATE OR REPLACE TABLE marts.fact_admission AS
WITH stays AS (
    SELECT encounter_id, patient_id, started_at, stopped_at, length_days
    FROM marts.fact_encounter
    WHERE encounter_class = 'inpatient'
),
with_next AS (
    SELECT *,
           lead(started_at) OVER (PARTITION BY patient_id ORDER BY started_at) AS next_admit_at
    FROM stays
)
SELECT *,
       next_admit_at IS NOT NULL
         AND date_diff('day', stopped_at, next_admit_at) <= 30 AS readmitted_30d
FROM with_next;

-- Aggregates below feed the Streamlit app.
CREATE OR REPLACE TABLE marts.agg_kpis AS
SELECT
    (SELECT count(*) FROM marts.dim_patient) AS patients,
    (SELECT count(*) FROM marts.dim_patient WHERE is_alive) AS living_patients,
    (SELECT count(*) FROM marts.fact_encounter) AS encounters,
    (SELECT count(*) FROM marts.fact_condition) AS conditions,
    (SELECT count(*) FROM raw.observations) AS observations,
    (SELECT count(*) FROM marts.fact_admission) AS admissions,
    (SELECT round(100.0 * avg(CASE WHEN readmitted_30d THEN 1 ELSE 0 END), 1) FROM marts.fact_admission) AS readmission_rate_pct,
    (SELECT round(avg(length_days), 1) FROM marts.fact_admission) AS avg_stay_days;

CREATE OR REPLACE TABLE marts.agg_encounters_by_year_class AS
SELECT year(started_at) AS year, encounter_class, count(*) AS encounters
FROM marts.fact_encounter
WHERE started_at IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2;

CREATE OR REPLACE TABLE marts.agg_admissions_by_year AS
SELECT
    year(started_at) AS year,
    count(*) AS admissions,
    sum(CASE WHEN readmitted_30d THEN 1 ELSE 0 END) AS readmissions,
    round(100.0 * avg(CASE WHEN readmitted_30d THEN 1 ELSE 0 END), 1) AS readmission_rate_pct,
    round(avg(length_days), 2) AS avg_stay_days
FROM marts.fact_admission
GROUP BY 1
ORDER BY 1;

CREATE OR REPLACE TABLE marts.agg_top_disorders AS
SELECT
    regexp_replace(description, ' \(disorder\)$', '') AS disorder,
    count(DISTINCT patient_id) AS patients
FROM marts.fact_condition
WHERE description LIKE '%(disorder)'
GROUP BY 1
ORDER BY patients DESC
LIMIT 15;

CREATE OR REPLACE TABLE marts.agg_age_gender AS
WITH ages AS (
    SELECT gender, date_diff('year', birth_date, current_date) AS age
    FROM marts.dim_patient
    WHERE is_alive AND birth_date IS NOT NULL
)
SELECT
    CASE WHEN age < 18 THEN '0-17'
         WHEN age < 40 THEN '18-39'
         WHEN age < 65 THEN '40-64'
         ELSE '65+' END AS age_band,
    gender,
    count(*) AS patients
FROM ages
GROUP BY 1, 2
ORDER BY 1, 2;

CREATE OR REPLACE TABLE marts.agg_payer_cost AS
SELECT
    coalesce(p.NAME, 'Unknown') AS payer,
    count(*) AS encounters,
    round(sum(e.claim_cost), 0) AS claim_cost,
    round(sum(e.payer_coverage), 0) AS payer_paid
FROM marts.fact_encounter e
LEFT JOIN raw.payers p ON p.Id = e.payer_id
GROUP BY 1
ORDER BY claim_cost DESC;

CREATE OR REPLACE TABLE marts.agg_quality_checks AS
SELECT check_name, failures, CASE WHEN failures = 0 THEN 'Passed' ELSE 'Failed' END AS status
FROM (
    SELECT 'Encounters with no matching patient' AS check_name, count(*) AS failures
    FROM marts.fact_encounter e
    LEFT JOIN marts.dim_patient p ON p.patient_id = e.patient_id
    WHERE p.patient_id IS NULL
    UNION ALL
    SELECT 'Conditions with no matching encounter', count(*)
    FROM marts.fact_condition c
    LEFT JOIN marts.fact_encounter e ON e.encounter_id = c.encounter_id
    WHERE e.encounter_id IS NULL
    UNION ALL
    SELECT 'Encounters that end before they start', count(*)
    FROM marts.fact_encounter
    WHERE stopped_at < started_at
    UNION ALL
    SELECT 'Patients with no birth date', count(*)
    FROM marts.dim_patient
    WHERE birth_date IS NULL
    UNION ALL
    SELECT 'Possible duplicate patients (same name and birth date)', count(*)
    FROM (
        SELECT lower(FIRST), lower(LAST), BIRTHDATE
        FROM raw.patients
        GROUP BY 1, 2, 3
        HAVING count(*) > 1
    )
    UNION ALL
    SELECT 'Hospital stays longer than one year', count(*)
    FROM marts.fact_admission
    WHERE length_days > 365
    UNION ALL
    SELECT 'Encounters with a negative cost', count(*)
    FROM marts.fact_encounter
    WHERE claim_cost < 0
);

CREATE OR REPLACE TABLE marts.masked_patients AS
SELECT
    left(patient_id, 8) AS patient_ref,
    first_name_masked,
    last_name_masked,
    ssn_masked,
    gender,
    year(birth_date) AS birth_year,
    city,
    state
FROM marts.dim_patient
ORDER BY patient_id
LIMIT 50;
