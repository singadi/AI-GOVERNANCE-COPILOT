{{ config(
  materialized='table',
  meta={
    'owner': 'data-platform',
    'domain': 'commerce',
    'layer': 'gold_restricted',
    'sensitivity': 'restricted'
  }
) }}

select
  customer_id,
  email,
  phone,
  region
from {{ ref('silver_customers') }}
