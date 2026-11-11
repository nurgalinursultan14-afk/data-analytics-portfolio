-- Singular test: total GMV in fct_orders equals price + freight of those orders' items.
with f as (select sum(gmv) as gmv from {{ ref('fct_orders') }}),
     i as (
        select sum(price + freight) as gmv
        from {{ ref('stg_order_items') }}
        where order_id in (select order_id from {{ ref('fct_orders') }})
     )
select * from f, i where abs(f.gmv - i.gmv) > 1
