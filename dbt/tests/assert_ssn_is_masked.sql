-- Fails if any SSN in the masked table shows more than the last four digits.
select patient_id, ssn_masked
from {{ ref('dim_patient') }}
where not regexp_matches(ssn_masked, '^\*\*\*-\*\*-[0-9]{4}$')
