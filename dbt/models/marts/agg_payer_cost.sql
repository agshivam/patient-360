select
    coalesce(p.payer_name, 'Unknown') as payer,
    count(*) as encounters,
    round(sum(e.claim_cost), 0) as claim_cost,
    round(sum(e.payer_coverage), 0) as payer_paid
from {{ ref('fact_encounter') }} e
left join {{ ref('stg_payers') }} p on p.payer_id = e.payer_id
group by 1
order by claim_cost desc
