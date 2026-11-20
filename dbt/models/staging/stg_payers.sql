select
    Id as payer_id,
    NAME as payer_name
from {{ source('raw', 'payers') }}
