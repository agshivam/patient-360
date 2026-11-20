select
    (select count(*) from {{ ref('dim_patient') }}) as patients,
    (select count(*) from {{ ref('dim_patient') }} where is_alive) as living_patients,
    (select count(*) from {{ ref('fact_encounter') }}) as encounters,
    (select count(*) from {{ ref('fact_condition') }}) as conditions,
    (select count(*) from {{ source('raw', 'observations') }}) as observations,
    (select count(*) from {{ ref('fact_admission') }}) as admissions,
    (select round(100.0 * avg(case when readmitted_30d then 1 else 0 end), 1) from {{ ref('fact_admission') }}) as readmission_rate_pct,
    (select round(avg(length_days), 1) from {{ ref('fact_admission') }}) as avg_stay_days
