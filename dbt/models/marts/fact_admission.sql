-- Hospital stays. A stay is flagged when the same patient is admitted again within 30 days of discharge.
with stays as (
    select encounter_id, patient_id, started_at, stopped_at, length_days
    from {{ ref('fact_encounter') }}
    where encounter_class = 'inpatient'
),

with_next as (
    select
        *,
        lead(started_at) over (partition by patient_id order by started_at) as next_admit_at
    from stays
)

select
    *,
    next_admit_at is not null
        and date_diff('day', stopped_at, next_admit_at) <= 30 as readmitted_30d
from with_next
