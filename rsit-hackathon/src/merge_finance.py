import json
import os
import pandas as pd
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from predict_model import get_es_forecast

# --- ES Connection --- 
def get_es_client():
    try:
        url_path = "../.secrets/es_url"
        key_path = "../.secrets/es_key"
        with open(url_path) as f: es_url = f.read().strip()
        with open(key_path) as f: es_key = f.read().strip()
        client = Elasticsearch(es_url, api_key=es_key)
        if client.ping():
            print("Successfully connected to Elasticsearch.")
            return client
    except Exception as e:
        print(f"Error connecting to ES: {e}")
    return None

def fetch_past_data_from_es(es_client, days_to_fetch):
    """Fetches the last N days of RSI data directly from Elasticsearch."""
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_to_fetch)
        search_body = {
            "size": 10000,
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": start_time.isoformat(),
                        "lte": end_time.isoformat()
                    }
                }
            },
            "sort": [{"@timestamp": "asc"}]
        }
        response = es_client.search(index="rsit-rsi-*", body=search_body)
        hits = response.get("hits", {}).get("hits", [])
        
        past_data = []
        for hit in hits:
            source = hit["_source"]
            past_data.append({
                "timestamp": source["@timestamp"],
                "aoi": source["aoi"],
                "rsi": source.get("rsi"),
                "price": source.get("price")
            })
        print(f"Fetched {len(past_data)} past records from Elasticsearch.")
        return past_data
    except Exception as e:
        print(f"Error fetching past data from ES: {e}")
        return []

# --- Main Script ---
os.makedirs("docs/data", exist_ok=True)
es_client = get_es_client()

# 1. Load data
# Fetch past 7 days of data from ES instead of local result.json
past_days = 7
forecast_days = 3
rsi_data = fetch_past_data_from_es(es_client, past_days) if es_client else []

if not rsi_data:
    print("No past data fetched from Elasticsearch. Aborting.")
    # Create an empty file to avoid breaking the frontend
    with open("docs/data/merged_from_es.json", "w") as f:
        json.dump([], f)
    exit()

# 2. Convert to DataFrame
rsi_df = pd.DataFrame(rsi_data)
rsi_df['date'] = pd.to_datetime(rsi_df['timestamp']).dt.normalize()
rsi_df = rsi_df.sort_values('date').drop_duplicates(subset=['date', 'aoi'], keep='last')

# 3. Determine date range
last_rsi_date = rsi_df['date'].max()
start_date = rsi_df['date'].min() # Start from the actual beginning of the fetched data
end_date = last_rsi_date + timedelta(days=forecast_days)
all_aois = rsi_df['aoi'].unique()

# 4. Create a complete date range DataFrame for merging
merged_df = pd.DataFrame({
    'date': pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq='D'))
}).merge(pd.DataFrame({'aoi': all_aois}), how='cross')

# Merge the historical data
merged_df = pd.merge(merged_df, rsi_df[['date', 'aoi', 'rsi', 'price']], on=['date', 'aoi'], how='left')

# 5. Forecasting
merged_df['kind'] = 'past'
merged_df.loc[merged_df['date'] > last_rsi_date, 'kind'] = 'forecast'

for aoi in all_aois:
    forecast_mask = (merged_df['aoi'] == aoi) & (merged_df['date'] > last_rsi_date)
    predictions = None
    
    if es_client:
        job_id = f'rsit-rsi-detector-{aoi}'
        predictions = get_es_forecast(es_client, job_id, forecast_days)

    if predictions is not None and len(predictions) == forecast_days:
        merged_df.loc[forecast_mask, 'rsi'] = predictions
    else:
        # Fallback if forecast fails
        last_known_rsi = merged_df.loc[(merged_df['aoi'] == aoi) & (merged_df['date'] <= last_rsi_date), 'rsi'].ffill().iloc[-1]
        merged_df.loc[forecast_mask, 'rsi'] = last_known_rsi

# Forward-fill gaps in historical data and price
merged_df['rsi'] = merged_df.groupby('aoi')['rsi'].ffill()
merged_df['price'] = merged_df.groupby('aoi')['price'].ffill().bfill()

# Create price_shift3 based on the available price data
merged_df['price_shift3'] = merged_df.groupby('aoi')['price'].shift(-3)
merged_df['price_shift3'] = merged_df.groupby('aoi')['price_shift3'].bfill()

# 6. Convert to final JSON
merged_df['date'] = merged_df['date'].dt.strftime('%Y-%m-%d')
output_filename = "docs/data/merged_with_forecast.json"

# Use pandas to_json which handles NaN correctly
merged_df.to_json(output_filename, orient='records', indent=2)

# Re-read for record count for the print statement
with open(output_filename, 'r') as f:
    num_records = len(json.load(f))
print(f"Wrote {num_records} records to {output_filename}")
