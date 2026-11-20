select
    Id as patient_id,
    try_cast(BIRTHDATE as date) as birth_date,
    try_cast(DEATHDATE as date) as death_date,
    GENDER as gender,
    RACE as race,
    CITY as city,
    STATE as state,
    FIRST as first_name,
    LAST as last_name,
    SSN as ssn
from {{ source('raw', 'patients') }}
