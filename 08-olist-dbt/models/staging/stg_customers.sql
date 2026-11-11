-- Olist issues a new customer_id for every order; customer_unique_id is the actual person.
select
    customer_id,
    customer_unique_id,
    customer_state as state
from {{ source('olist_raw', 'olist_customers_dataset') }}
