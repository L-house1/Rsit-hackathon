import yfinance as yf
import json
import os
import datetime as dt

# Part 1: Download financial data
print("--- Downloading financial data ---")
os.makedirs("docs/data", exist_ok=True)
end = dt.date.today()
start = end - dt.timedelta(days=30)
df = yf.download("AMZN", start=start.isoformat(), end=end.isoformat(), progress=False)
rows = [{"date": i.strftime("%Y-%m-%d"), "close": float(r["Close"])} for i, r in df.iterrows()]
finance_file = "docs/data/finance_amzn_recent.json"
with open(finance_file, "w") as f:
    json.dump({"symbol": "AMZN", "daily": rows}, f, indent=2)
print(f"Wrote {finance_file}", len(rows))

# Part 2: Merge RSI and financial data
print("\n--- Merging RSI and financial data ---")
result_file = "docs/data/result.json"
merged_file = "docs/data/merged.json"

# Ensure result.json exists and is valid JSON, even if empty
if not os.path.exists(result_file):
    with open(result_file, "w") as f:
        json.dump([], f)

try:
    with open(result_file) as f:
        rsi_data = json.load(f)
except json.JSONDecodeError:
    rsi_data = []

with open(finance_file) as f:
    fin_data = json.load(f)

price_map = {r["date"]: r["close"] for r in fin_data["daily"]}
output_data = []

for r in rsi_data:
    d = (r.get("timestamp") or r.get("date") or "")[:10]
    if d in price_map and r.get("rsi") is not None:
        output_data.append({"date": d, "rsi": float(r["rsi"]), "price": float(price_map[d])})

# Apply 3-day shift
for i in range(len(output_data)):
    j = i + 3
    output_data[i]["price_shift3"] = output_data[j]["price"] if j < len(output_data) else None

with open(merged_file, "w") as f:
    json.dump(output_data, f, indent=2)
print(f"Wrote {merged_file}", len(output_data))