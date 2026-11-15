select
    purchase_month,
    count(*)                         as orders,
    count(distinct customer_unique_id) as customers,
    round(sum(gmv), 2)               as gmv,
    round(avg(gmv), 2)               as avg_order_value,
    round(avg(is_late), 4)           as late_rate,
    round(avg(review_score), 2)      as avg_review
from {{ ref('fct_orders') }}
group by purchase_month
order by purchase_month
