select year(started_at) as year, encounter_class, count(*) as encounters
from {{ ref('fact_encounter') }}
where started_at is not null
group by 1, 2
order by 1, 2
