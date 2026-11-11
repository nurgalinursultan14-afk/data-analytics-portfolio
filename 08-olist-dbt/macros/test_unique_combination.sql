-- Generic test: no two rows share the same combination of `columns` (a composite primary key).
-- Written by hand so the project needs no dbt packages.
{% test unique_combination_of_columns(model, columns) %}
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
