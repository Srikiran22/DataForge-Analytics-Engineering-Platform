import pathlib

import yaml

p = pathlib.Path(r"C:\Users\Srikiran\DataForge — Analytics Engineering Platform\dbt\models\core\schema.yml")
data = yaml.safe_load(p.read_text(encoding="utf-8"))
missing = {
    "dim_date": [
        ("day","SMALLINT"),("day_of_week","SMALLINT"),("day_name","VARCHAR"),("week_of_year","SMALLINT"),
        ("is_weekend","BOOLEAN"),("is_holiday","BOOLEAN"),("fiscal_year","SMALLINT"),("fiscal_quarter","SMALLINT"),
        ("month_name","VARCHAR"),("quarter","SMALLINT"),
    ],
    "dim_product": [("brand","VARCHAR")],
    "dim_customer": [("city","VARCHAR"),("dbt_valid_to","TIMESTAMP")],
}
for m in data["models"]:
    if m["name"] in missing:
        existing = {c["name"] for c in m.get("columns",[])}
        for name, dtype in missing[m["name"]]:
            if name not in existing:
                m["columns"].append({"name": name, "data_type": dtype})
                print(f'added {m["name"]}.{name}')
p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
print("patched core missing cols")
