-- Singular test: the repeat-purchase rate should reproduce project 06's 2.2%.
select avg(case when returned then 1.0 else 0 end) as repeat_rate
from {{ ref('dim_customers') }}
having abs(avg(case when returned then 1.0 else 0 end) - 0.022) > 0.001
