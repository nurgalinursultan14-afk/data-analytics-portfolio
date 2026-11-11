-- One row per real customer. "Returned" means a second order on a LATER day:
-- same-day split checkouts are not repeat purchases.
select
    customer_unique_id,
    min(purchased_at)                           as first_purchased_at,
    date_trunc('month', min(purchased_at))::date as cohort_month,
    count(*)                                    as orders,
    round(sum(gmv), 2)                          as lifetime_gmv,
    count(distinct purchased_at::date) > 1      as returned
from {{ ref('fct_orders') }}
group by customer_unique_id
