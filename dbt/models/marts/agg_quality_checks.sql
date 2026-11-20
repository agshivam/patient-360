-- A summary of data quality for the report. The same rules also run as dbt tests (see _marts.yml and tests/).
select check_name, failures, case when failures = 0 then 'Passed' else 'Failed' end as status
from (
    select 'Encounters with no matching patient' as check_name, count(*) as failures
    from {{ ref('fact_encounter') }} e
    left join {{ ref('dim_patient') }} p on p.patient_id = e.patient_id
    where p.patient_id is null
    union all
    select 'Conditions with no matching encounter', count(*)
    from {{ ref('fact_condition') }} c
    left join {{ ref('fact_encounter') }} e on e.encounter_id = c.encounter_id
    where e.encounter_id is null
    union all
    select 'Encounters that end before they start', count(*)
    from {{ ref('fact_encounter') }}
    where stopped_at < started_at
    union all
    select 'Patients with no birth date', count(*)
    from {{ ref('dim_patient') }}
    where birth_date is null
    union all
    select 'Possible duplicate patients (same name and birth date)', count(*)
    from (
        select lower(first_name), lower(last_name), birth_date
        from {{ ref('stg_patients') }}
        group by 1, 2, 3
        having count(*) > 1
    )
    union all
    select 'Hospital stays longer than one year', count(*)
    from {{ ref('fact_admission') }}
    where length_days > 365
    union all
    select 'Encounters with a negative cost', count(*)
    from {{ ref('fact_encounter') }}
    where claim_cost < 0
)
