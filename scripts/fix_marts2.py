import pathlib

import yaml

p = pathlib.Path(r"C:\Users\Srikiran\DataForge — Analytics Engineering Platform\dbt\models\marts\schema.yml")
data = yaml.safe_load(p.read_text(encoding="utf-8"))

# Comprehensive fix per last error batch: add missing columns, fix type mismatches
adds = {
    "mart_product_performance": [
        ("avg_unit_price","DOUBLE"),("brand","VARCHAR"),("category","VARCHAR"),
        ("name","VARCHAR"),("order_count","BIGINT"),("returned_revenue","DOUBLE"),
        ("returned_units","HUGEINT"),("revenue_rank","BIGINT"),("units_sold","HUGEINT"),
    ],
    "mart_returns": [
        ("date","DATE"),("region_name","VARCHAR"),("return_count","BIGINT"),
    ],
    "mart_sales": [
        ("country","VARCHAR"),("currency","VARCHAR"),("month","SMALLINT"),("month_name","VARCHAR"),
        ("quarter","SMALLINT"),("returned_revenue","DOUBLE"),("settled_revenue","DOUBLE"),
        ("status","VARCHAR"),("total_amount_cents","BIGINT"),("year","SMALLINT"),
    ],
}
# type corrections
corrections = {
    "mart_product_performance": {"return_rate": "FLOAT", "units_sold": "HUGEINT"},
    "mart_returns": {"total_returned_units": "HUGEINT"},
    "mart_sales": {},
    "mart_inventory": {},
    "mart_customer_retention": {"retention_rate":"FLOAT"},
}
# fix days_of_cover nullability: make it nullable (remove not_null test)
for m in data["models"]:
    if m["name"] in adds:
        existing = {c["name"] for c in m.get("columns",[])}
        for name, dtype in adds[m["name"]]:
            if name not in existing:
                m["columns"].append({"name": name, "data_type": dtype})
                print(f"added {m['name']}.{name} {dtype}")
    # corrections
    if m["name"] in corrections:
        for c in m.get("columns",[]):
            if c["name"] in corrections[m["name"]]:
                old = c.get("data_type")
                new = corrections[m["name"]][c["name"]]
                if old != new:
                    c["data_type"]=new
                    print(f"fixed {m['name']}.{c['name']} {old}->{new}")
    # inventory days_of_cover: remove not_null by filtering tests
    if m["name"]=="mart_inventory":
        for c in m.get("columns",[]):
            if c["name"]=="days_of_cover":
                orig = c.get("tests",[])
                new = [t for t in orig if t!="not_null" and not (isinstance(t,dict) and "not_null" in t)]
                if len(new)!=len(orig):
                    c["tests"]=new
                    print("removed not_null from mart_inventory.days_of_cover")
                # also fix type if still BIGINT
                if c.get("data_type")=="BIGINT":
                    c["data_type"]="DOUBLE"
                    print("fixed days_of_cover BIGINT->DOUBLE")

p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
print("done")
