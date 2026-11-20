-- Fails if two patients share the same name and birth date after lower-casing.
-- This catches exact duplicates only. Duplicates with typos need fuzzy matching: see scripts/dedupe_patients.py.
select lower(first_name) as first_name, lower(last_name) as last_name, birth_date, count(*) as copies
from {{ ref('stg_patients') }}
group by 1, 2, 3
having count(*) > 1
