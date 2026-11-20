select
    Id as encounter_id,
    PATIENT as patient_id,
    ORGANIZATION as organization_id,
    PROVIDER as provider_id,
    PAYER as payer_id,
    ENCOUNTERCLASS as encounter_class,
    try_cast(replace(START, 'Z', '') as timestamp) as started_at,
    try_cast(replace(STOP, 'Z', '') as timestamp) as stopped_at,
    try_cast(BASE_ENCOUNTER_COST as double) as base_cost,
    try_cast(TOTAL_CLAIM_COST as double) as claim_cost,
    try_cast(PAYER_COVERAGE as double) as payer_coverage,
    DESCRIPTION as description,
    REASONDESCRIPTION as reason
from {{ source('raw', 'encounters') }}
