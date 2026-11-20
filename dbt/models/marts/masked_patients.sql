select
    left(patient_id, 8) as patient_ref,
    first_name_masked,
    last_name_masked,
    ssn_masked,
    gender,
    year(birth_date) as birth_year,
    city,
    state
from {{ ref('dim_patient') }}
order by patient_id
limit 50
