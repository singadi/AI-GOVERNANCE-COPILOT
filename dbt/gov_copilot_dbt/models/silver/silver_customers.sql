{{ config(
  materialized='table',
  meta={
    'owner': 'data-platform',
    'domain': 'commerce',
    'layer': 'silver',
    'sensitivity': 'internal'
  }
) }}

select
  cast(customer_id as integer) as customer_id,
  lower(trim(email)) as email,
  regexp_replace(phone, '[^0-9]', '', 'g') as phone,
  region
from {{ ref('customers') }}
