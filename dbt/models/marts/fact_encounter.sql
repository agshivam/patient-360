select
    encounter_id,
    patient_id,
    organization_id,
    provider_id,
    payer_id,
    encounter_class,
    started_at,
    stopped_at,
    date_diff('minute', started_at, stopped_at) / 1440.0 as length_days,
    base_cost,
    claim_cost,
    payer_coverage,
    description,
    reason
from {{ ref('stg_encounters') }}
