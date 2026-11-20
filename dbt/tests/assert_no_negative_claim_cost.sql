-- Fails if any encounter has a negative claim cost.
select encounter_id, claim_cost
from {{ ref('fact_encounter') }}
where claim_cost < 0
