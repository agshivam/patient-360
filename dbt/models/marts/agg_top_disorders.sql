select
    regexp_replace(description, ' \(disorder\)$', '') as disorder,
    count(distinct patient_id) as patients
from {{ ref('fact_condition') }}
where description like '%(disorder)'
group by 1
order by patients desc
limit 15
