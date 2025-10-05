import json
import os

json_input = '''{"took":1,"timed_out":false,"_shards":{"total":1,"successful":1,"skipped":0,"failed":0},"hits":{"total":{"value":3,"relation":"eq"},"max_score":null,"hits":[{"_index":"rsit-rsi","_id":"Mrgrr5kBf6QHQ2vzQoZQ","_score":null,"_source":{"@timestamp":"2025-10-04T00:00:00Z","rsi":0.78,"price":131.8},"sort":[1759536000000]},{"_index":"rsit-rsi","_id":"Lbi8rpkBf6QHQ2vzaoYA","_score":null,"_source":{"@timestamp":"2025-10-04T00:00:00Z","rsi":0.5,"price":134.68},"sort":[1759536000000]},{"_index":"rsit-rsi","_id":"M7grr5kBf6QHQ2vzQoZR","_score":null,"_source":{"@timestamp":"2025-10-04T03:00:00Z","rsi":0.88,"price":131.2,"price_shift3":129.9},"sort":[1759546800000]}]}}'''

res = json.loads(json_input)
arr = []
for h in res.get("hits", {}).get("hits", []):
    s = h.get("_source", {})
    ts = s.get("@timestamp", "")
    date = ts[:10] if len(ts) >= 10 else ts
    arr.append({
        "date": date,
        "rsi": s.get("rsi"),
        "price": s.get("price"),
        "price_shift3": s.get("price_shift3")
    })

output_path = "docs/data/merged_from_es.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w") as f:
    f.write(json.dumps(arr, indent=2))

print(f"Wrote {len(arr)} records to {output_path}")
