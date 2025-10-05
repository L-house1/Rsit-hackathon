import json
import os

print("--- Creating NDJSON for bulk upload ---")
merged_file = "docs/data/merged.json"
ndjson_file = "/tmp/rsit_live.ndjson"

try:
    with open(merged_file) as f:
        arr = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    arr = []

out = []
for r in arr:
    ts = r["date"] + "T00:00:00Z"
    # The guide specifies aoi="ashburn"
    doc = {"@timestamp": ts, "aoi": "ashburn", "rsi": r["rsi"], "price": r.get("price"), "price_shift3": r.get("price_shift3")}
    out.append('{"index":{"_index":"rsit-rsi"}}')
    out.append(json.dumps({k: v for k, v in doc.items() if v is not None}))

with open(ndjson_file, "w") as f:
    f.write("\n".join(out) + "\n")

print(f"Wrote NDJSON to {ndjson_file}", len(arr))

