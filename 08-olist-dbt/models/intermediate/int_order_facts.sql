-- One row per order with value, delivery and review fields. GMV = item price + freight.
with items as (
    select order_id, count(*) as n_items, sum(price) as item_value, sum(freight) as freight_value
    from {{ ref('stg_order_items') }}
    group by order_id
)
select
    o.order_id,
    c.customer_unique_id,
    c.state                                                   as customer_state,
    o.status,
    o.purchased_at,
    date_trunc('month', o.purchased_at)::date                 as purchase_month,
    i.n_items,
    round(i.item_value + i.freight_value, 2)                  as gmv,
    o.delivered_at,
    date_diff('day', o.estimated_delivery_date, o.delivered_at::date) as days_vs_promise,
    case when o.delivered_at is null then null
         when o.delivered_at::date > o.estimated_delivery_date then 1 else 0 end as is_late,
    r.review_score
from {{ ref('stg_orders') }} o
join {{ ref('stg_customers') }} c using (customer_id)
left join items i using (order_id)
left join {{ ref('stg_reviews') }} r using (order_id)
