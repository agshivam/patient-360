select
    PATIENT as patient_id,
    ENCOUNTER as encounter_id,
    CODE as code,
    DESCRIPTION as description,
    try_cast(START as date) as started_on,
    try_cast(STOP as date) as stopped_on
from {{ source('raw', 'conditions') }}
