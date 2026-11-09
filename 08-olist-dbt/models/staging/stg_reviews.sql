-- About 550 orders have more than one review: keep the most recently answered one.
select order_id, review_id, review_score
from (
    select
        order_id,
        review_id,
        cast(review_score as integer) as review_score,
        row_number() over (
            partition by order_id
            order by review_answer_timestamp desc, review_id
        ) as rn
    from {{ source('olist_raw', 'olist_order_reviews_dataset') }}
)
where rn = 1
