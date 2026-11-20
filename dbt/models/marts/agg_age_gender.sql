with ages as (
    select gender, date_diff('year', birth_date, current_date) as age
    from {{ ref('dim_patient') }}
    where is_alive and birth_date is not null
)

select
    case when age < 18 then '0-17'
         when age < 40 then '18-39'
         when age < 65 then '40-64'
         else '65+' end as age_band,
    gender,
    count(*) as patients
from ages
group by 1, 2
order by 1, 2
