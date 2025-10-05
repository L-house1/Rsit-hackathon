#!/bin/bash
set -e

echo "--- Setting up Python virtual environment ---"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "--- Installing dependencies ---"
pip install -r requirements.txt

echo "--- Seeding Elasticsearch with initial data ---"
python src/seed_es.py

echo "--- Running data processing and forecasting pipeline ---"
python src/merge_finance.py

echo "--- Demo setup complete! ---"
echo "You can now serve the 'docs' directory with a local web server."
