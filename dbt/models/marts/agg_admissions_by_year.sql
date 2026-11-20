select
    year(started_at) as year,
    count(*) as admissions,
    sum(case when readmitted_30d then 1 else 0 end) as readmissions,
    round(100.0 * avg(case when readmitted_30d then 1 else 0 end), 1) as readmission_rate_pct,
    round(avg(length_days), 2) as avg_stay_days
from {{ ref('fact_admission') }}
group by 1
order by 1
