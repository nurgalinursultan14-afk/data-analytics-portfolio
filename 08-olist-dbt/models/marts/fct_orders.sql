-- Completed sales in the analysis window, with each customer's order sequence.
select
    *,
    row_number() over (partition by customer_unique_id order by purchased_at, order_id) as customer_order_number
from {{ ref('int_order_facts') }}
where status not in ('canceled', 'unavailable')
  and gmv is not null
  and purchase_month between '{{ var("start_month") }}' and '{{ var("end_month") }}'
