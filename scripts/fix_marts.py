import pathlib

import yaml

p = pathlib.Path(r"C:\Users\Srikiran\DataForge — Analytics Engineering Platform\dbt\models\marts\schema.yml")
data = yaml.safe_load(p.read_text(encoding="utf-8"))
missing = {
    "mart_customer_retention": [
        ("cohort_revenue","DOUBLE"),("first_order","TIMESTAMP"),("last_order","TIMESTAMP"),
        ("order_month","DATE"),("repeat_orders","BIGINT"),
    ],
    "mart_inventory": [
        ("avg_daily_units_sold","DOUBLE"),("brand","VARCHAR"),("category","VARCHAR"),
        ("name","VARCHAR"),("product_id","VARCHAR"),("reorder_point","BIGINT"),("snapshot_date","TIMESTAMP"),
    ],
}
for m in data["models"]:
    if m["name"] in missing:
        existing = {c["name"] for c in m.get("columns",[])}
        for name, dtype in missing[m["name"]]:
            if name not in existing:
                m["columns"].append({"name": name, "data_type": dtype})
                print(f"added {m['name']}.{name} {dtype}")
        for c in m["columns"]:
            if m["name"]=="mart_customer_retention" and c["name"]=="retention_rate":
                if c.get("data_type")=="DOUBLE":
                    c["data_type"]="FLOAT"
                    print("fixed retention_rate to FLOAT")
            if m["name"]=="mart_inventory" and c["name"]=="days_of_cover":
                if c.get("data_type")=="BIGINT":
                    c["data_type"]="DOUBLE"
                    print("fixed days_of_cover to DOUBLE")
p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
print("done")
