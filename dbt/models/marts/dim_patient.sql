-- Names and SSN are masked here, so analysts never see the full values.
select
    patient_id,
    birth_date,
    death_date,
    gender,
    race,
    city,
    state,
    death_date is null as is_alive,
    upper(substr(first_name, 1, 1)) || '***' as first_name_masked,
    upper(substr(last_name, 1, 1)) || '***' as last_name_masked,
    '***-**-' || right(ssn, 4) as ssn_masked
from {{ ref('stg_patients') }}
