{{ config(
  materialized='table',
  meta={
    'owner': 'data-platform',
    'domain': 'commerce',
    'layer': 'gold',
    'sensitivity': 'public'
  }
) }}

select
  cast(o.order_id as integer) as order_id,
  cast(o.customer_id as integer) as customer_id,
  cast(o.amount as numeric(12,2)) as amount,
  cast(o.order_ts as date) as order_date
  lower(trim(c.email)) as email
from {{ ref('orders') }} o
join {{ ref('customers') }} c on o.customer_id = c.customer_id 
