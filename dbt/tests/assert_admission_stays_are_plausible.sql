-- Fails if a hospital stay is longer than one year, which usually means a bad timestamp.
select encounter_id, length_days
from {{ ref('fact_admission') }}
where length_days > 365
