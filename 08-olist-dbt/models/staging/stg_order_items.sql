select
    order_id,
    cast(order_item_id as integer) as order_item_id,
    product_id,
    seller_id,
    cast(price as double)          as price,
    cast(freight_value as double)  as freight
from {{ source('olist_raw', 'olist_order_items_dataset') }}
