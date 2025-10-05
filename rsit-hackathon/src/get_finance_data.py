import os
import json
import requests
import csv
import io

output_path = "docs/data/finance_amzn_2023-07.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

url = "https://stooq.com/q/d/l/?s=amzn.us&i=d"

try:
    print(f"Fetching data from {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    csv_bytes = response.content

    rows = []
    # Use StringIO to treat the byte string as a file
    csv_file = io.StringIO(csv_bytes.decode("utf-8"))
    reader = csv.reader(csv_file)
    
    for i, r in enumerate(reader):
        if i == 0 or not r or r[0] < "2023-07-01" or r[0] > "2023-07-31":
            continue
        # Date,Open,High,Low,Close,Volume format
        rows.append({"date": r[0], "close": float(r[4]), "volume": int(r[5])})
    
    rows.sort(key=lambda x: x["date"])
    
    with open(output_path, "w") as f:
        json.dump({"symbol": "AMZN", "daily": rows}, f, indent=2)
        
    print(f"Wrote {len(rows)} rows to {output_path}")

except requests.exceptions.RequestException as e:
    print(f"Error fetching data from Stooq: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
