import os
import json
import subprocess
import sys

def main():
    es_url = os.environ.get("ELASTICSEARCH_URL")
    api_key = os.environ.get("ELASTIC_API_KEY")

    if not es_url or not api_key:
        print("Error: ELASTICSEARCH_URL and ELASTIC_API_KEY environment variables must be set.")
        sys.exit(1)

    query = {
        "size": 200,
        "sort": [{"@timestamp": "asc"}],
        "query": {
            "bool": {
                "filter": [
                    {"term": {"aoi": "ashburn"}},
                    {"range": {"@timestamp": {"gte": "now-30d"}}}
                ]
            }
        },
        "_source": ["@timestamp", "rsi", "price", "price_shift3"]
    }

    try:
        res = subprocess.check_output([
            "curl", "-sS", "-X", "POST", f"{es_url}/rsit-rsi/_search",
            "-H", f"Authorization: ApiKey {api_key}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(query)
        ])
        
        hits = json.loads(res).get("hits", {}).get("hits", [])
        arr = []
        for h in hits:
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

    except subprocess.CalledProcessError as e:
        print(f"Curl command failed: {e}")
        print(f"Response: {e.output.decode()}")
    except json.JSONDecodeError:
        print(f"Error decoding JSON from Elasticsearch. Response: {res.decode()}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
