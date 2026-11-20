-- Fails if any encounter ends before it starts.
select encounter_id, started_at, stopped_at
from {{ ref('fact_encounter') }}
where stopped_at < started_at
