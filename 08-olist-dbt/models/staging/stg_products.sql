-- Translate Portuguese category names; label missing ones.
select
    p.product_id,
    coalesce(t.product_category_name_english, nullif(p.product_category_name, ''), 'unknown') as category
from {{ source('olist_raw', 'olist_products_dataset') }} p
left join {{ source('olist_raw', 'product_category_name_translation') }} t
    on t.product_category_name = p.product_category_name
