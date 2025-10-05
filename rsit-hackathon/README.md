# RSIT (Resource Stress Intelligence Thermometer)

## Overview
This project, codenamed RSIT, is an intelligence thermometer for resource pressure. It leverages NASA satellite data (ECOSTRESS, SMAP) and financial indicators to calculate a Resource Stress Index (RSI). The system includes a data pipeline to process and merge this data, an Elasticsearch backend for storage and machine learning, and a web frontend for visualization.

## Demo Guide for Judges

This guide provides step-by-step instructions to set up and run the project demo.

### Step 1: Prerequisites

- **Python:** Version 3.10 or higher must be installed.
- **Git:** Required for cloning the repository.

### Step 2: Clone the Repository

Open your terminal and clone the project from GitHub:

```bash
git clone https://github.com/L-house1/Rsit-hackathon.git
cd Rsit-hackathon
```

### Step 3: Configure Elasticsearch Credentials

The application requires credentials to connect to an Elasticsearch cluster.

1.  You should be in the `Rsit-hackathon` directory you just cloned.
2.  Create a new directory named `.secrets` in this location.
    ```bash
    mkdir .secrets
    ```
3.  Inside the `.secrets` directory, create two plain text files:
    -   `es_url`: This file should contain only the URL of your Elasticsearch endpoint.
    -   `es_key`: This file should contain only the API Key for authentication.

The final structure should look like this:
```
Rsit-hackathon/
├── .secrets/
│   ├── es_url
│   └── es_key
├── rsit-hackathon/
│   ├── scripts/
│   └── src/
└── ...
```

**WARNING:** Do not commit the `.secrets` directory to version control.

### Step 4: Run the Automated Demo Script

Navigate into the main application directory and run the demo script. This script will automate the entire backend process.

```bash
cd rsit-hackathon
bash scripts/run_demo.sh
```

This script performs the following actions:
1.  Creates a Python virtual environment (`.venv`).
2.  Installs all required packages from `requirements.txt`.
3.  Seeds the Elasticsearch index with 90 days of sample data.
4.  Processes the data and generates the final JSON file for the frontend.

### Step 5: View the Visualization

Once the script is complete, you need to start a local web server to view the interactive map and chart.

1.  Navigate to the `docs` directory:
    ```bash
    cd docs
    ```
2.  Start a simple Python web server:
    ```bash
    python3 -m http.server
    ```
3.  Open your web browser and go to the following address:
    [http://localhost:8000](http://localhost:8000)

### Troubleshooting

- **Chart is empty or not showing recent changes?** Your browser might be caching old files. Perform a **Hard Refresh**:
    - **Windows/Linux:** `Ctrl + Shift + R`
    - **Mac:** `Cmd + Shift + R`

## Architecture & Data Flow

1.  **Data Acquisition:** Satellite and financial data are fetched.
2.  **Data Processing:** A Python pipeline processes the raw data, calculates RSI, and merges it.
3.  **Storage & ML:** The processed data is stored in Elasticsearch. Anomaly detection and forecasting ML jobs are run on this data.
4.  **Data Serving:** A script (`merge_finance.py`) prepares the final data, including forecasts, and writes it to a JSON file.
5.  **Frontend:** A web interface reads the JSON file to display interactive maps and charts.

## Limitations and Next Steps
- The current forecast retrieval is a placeholder and should be extended to poll for the actual results from the forecast ID.
- The frontend is a basic demonstration and can be enhanced with more features.
- The project can be expanded to include more AOIs and more sophisticated prediction models as outlined in the research.
