import time
from elasticsearch import Elasticsearch

def ensure_job_open_and_running(es_client, job_id, datafeed_id, lookback="now-90d"):
    """Checks job and datafeed state, handles opening/stuck states, and starts datafeed."""
    try:
        job_stats = es_client.ml.get_job_stats(job_id=job_id)['jobs'][0]
        job_state = job_stats.get('state')
        print(f"Initial job '{job_id}' state: '{job_state}'.")

        if job_state != 'opened':
            if job_state == 'opening':
                explanation = job_stats.get('assignment_explanation', '')
                if any(r in explanation for r in ["no suitable nodes", "insufficient capacity", "max opening jobs"]):
                    print(f"Job stuck in opening: {explanation}. Please resolve in Elastic Cloud.")
                    return False
            
            try: 
                es_client.ml.close_job(job_id=job_id, force=True, timeout="2m")
                time.sleep(5)
            except Exception:
                pass

            print(f"Opening job '{job_id}'...")
            es_client.ml.open_job(job_id=job_id, timeout="2m")
            time.sleep(10)

        job_stats = es_client.ml.get_job_stats(job_id=job_id)['jobs'][0]
        if job_stats.get('state') != 'opened':
            print(f"Job '{job_id}' failed to open. Final state: {job_stats.get('state')}. Aborting.")
            return False

        datafeed_stats = es_client.ml.get_datafeed_stats(datafeed_id=datafeed_id)['datafeeds'][0]
        if datafeed_stats['state'] != 'started':
            print(f"Starting datafeed '{datafeed_id}'...")
            es_client.ml.start_datafeed(datafeed_id=datafeed_id, start=lookback)
            time.sleep(10)
        
        return True

    except Exception as e:
        print(f"Error ensuring job/datafeed is running: {e}")
        return False

def get_es_forecast(es_client, job_id, forecast_days):
    """Ensures ML job is running, generates a forecast, and retrieves the results."""
    datafeed_id = f"datafeed-{job_id}"
    
    if not ensure_job_open_and_running(es_client, job_id, datafeed_id):
        print("Could not prepare ML job for forecast. Aborting forecast.")
        return None

    try:
        print(f"Requesting {forecast_days}-day forecast from Elastic ML job: {job_id}")
        forecast_resp = es_client.ml.forecast(job_id=job_id, duration=f'{forecast_days}d')
        forecast_id = forecast_resp.get('forecast_id')
        print(f"Forecast requested. Forecast ID: {forecast_id}")

        if not forecast_id:
            raise ValueError("No forecast_id returned from forecast request.")

        print("Waiting for forecast results to be indexed...")
        time.sleep(20) # Wait for results to be indexed

        search_body = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"job_id": job_id}},
                        {"term": {"forecast_id": forecast_id}},
                        {"term": {"result_type": "model_forecast"}}
                    ]
                }
            },
            "sort": [{"timestamp": {"order": "asc"}}],
            "size": 10000
        }

        results_resp = es_client.search(index=".ml-anomalies-*", body=search_body)
        hits = results_resp.get("hits", {}).get("hits", [])
        
        if not hits:
            raise ValueError("Forecast results are not yet available or empty.")

        predictions = [hit["_source"]['forecast_prediction'] for hit in hits]
        print(f"Retrieved {len(predictions)} forecast points.")
        return predictions[:forecast_days]

    except Exception as e:
        print(f"Elastic ML forecast process failed: {e}")
        return None