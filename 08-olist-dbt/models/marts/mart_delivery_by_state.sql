select
    customer_state,
    count(*)                                                       as delivered_orders,
    median(date_diff('day', purchased_at::date, delivered_at::date)) as median_days_to_deliver,
    round(avg(is_late), 4)                                         as late_rate,
    round(avg(review_score), 2)                                    as avg_review
from {{ ref('fct_orders') }}
where delivered_at is not null
group by customer_state
order by late_rate desc
