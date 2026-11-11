-- Share of each monthly cohort that ordered again N months after their first purchase month.
with activity as (
    select distinct
        d.cohort_month,
        f.customer_unique_id,
        date_diff('month', d.cohort_month, f.purchase_month) as months_since_first
    from {{ ref('fct_orders') }} f
    join {{ ref('dim_customers') }} d using (customer_unique_id)
),
cohort_size as (
    select cohort_month, count(*) as customers
    from {{ ref('dim_customers') }}
    group by cohort_month
)
select
    a.cohort_month,
    s.customers                                  as cohort_customers,
    a.months_since_first,
    count(*)                                     as active_customers,
    round(count(*) * 1.0 / s.customers, 4)       as retention_rate
from activity a
join cohort_size s using (cohort_month)
group by a.cohort_month, s.customers, a.months_since_first
order by a.cohort_month, a.months_since_first
