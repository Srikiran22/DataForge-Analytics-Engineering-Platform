{% macro generate_surrogate_key(fields) -%}
  md5({{ fields | join(" || '_' || ") }})
{%- endmacro %}

{% macro cents_to_dollars(cents_column) -%}
  ({{ cents_column }} / 100.0)
{%- endmacro %}