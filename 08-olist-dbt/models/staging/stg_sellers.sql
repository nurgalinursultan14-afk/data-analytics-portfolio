select seller_id, seller_state as state
from {{ source('olist_raw', 'olist_sellers_dataset') }}
