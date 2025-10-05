import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

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
        print(f"Error connecting to Elasticsearch: {e}")
    return None

def create_time_series_data(days, points_per_day, aois):
    docs = []
    base_time = datetime.now()
    for aoi in aois:
        for day in range(days):
            for point in range(points_per_day):
                timestamp = base_time - timedelta(days=day, hours=point)
                # Simulate some seasonality and noise
                rsi_base = 0.5 + 0.2 * np.sin(2 * np.pi * (day * 24 + point) / (24 * 7)) # Weekly seasonality
                rsi = rsi_base + random.uniform(-0.05, 0.05)
                price = 150 + 20 * np.sin(2 * np.pi * day / 30) + random.uniform(-5, 5) # Monthly seasonality
                
                doc = {
                    "_index": "rsit-rsi-000001",
                    "_source": {
                        "@timestamp": timestamp.isoformat(),
                        "aoi": aoi,
                        "rsi": round(np.clip(rsi, 0, 1), 4),
                        "price": round(price, 2),
                        "price_shift3": round(price * (1 + random.uniform(-0.05, 0.05)), 2)
                    }
                }
                docs.append(doc)
    return docs

def seed_elasticsearch(client):
    template_name = "rsit-rsi-template"
    template_body = {
        "index_patterns": ["rsit-rsi-*"],
        "template": {
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "aoi": {"type": "keyword"},
                    "rsi": {"type": "float"},
                    "price": {"type": "float"},
                    "price_shift3": {"type": "float"}
                }
            }
        },
        "priority": 100
    }
    index_name = "rsit-rsi-000001"

    try:
        client.indices.put_index_template(name=template_name, body=template_body)
        print(f"Index template '{template_name}' created/updated.")
    except Exception as e:
        print(f"Error creating template: {e}")
        return

    if client.indices.exists(index=index_name):
        print(f"Deleting existing index '{index_name}' to re-seed...")
        client.indices.delete(index=index_name)
    
    print(f"Creating index '{index_name}'...")
    client.indices.create(index=index_name)

    print("Generating 90 days of sample time series data...")
    aois = ["ashburn", "phoenix", "dallas"]
    # Generate data for 90 days, with one point per hour
    documents = create_time_series_data(days=90, points_per_day=24, aois=aois)
    
    try:
        print(f"Bulk indexing {len(documents)} documents...")
        success, _ = bulk(client, documents, index=index_name, raise_on_error=True)
        print(f"Successfully indexed {success} documents.")
        client.indices.refresh(index=index_name)
    except Exception as e:
        print(f"Error bulk indexing documents: {e}")

if __name__ == "__main__":
    es = get_es_client()
    if es:
        seed_elasticsearch(es)
