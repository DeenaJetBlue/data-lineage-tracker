import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(".env")
if not env_path.exists():
    print("Error: .env not found!")
    sys.exit(1)

load_dotenv(env_path)

DBT_SECRET = os.getenv("DBT_SECRET")
DBT_ACCESS_URL = os.getenv("DBT_ACCESS_URL")

if not DBT_SECRET or not DBT_ACCESS_URL:
    print("Error: DBT_SECRET or DBT_ACCESS_URL not configured in .env")
    sys.exit(1)

CONFIG_FILE = ".config"
if not Path(CONFIG_FILE).exists():
    print(f"Error: {CONFIG_FILE} not found!")
    sys.exit(1)


def read_config():
    config = {}
    with open(CONFIG_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()

    return {
        'account_id': config.get('DBT_AccountID'),
        'job_id': config.get('DBT_JobID')
    }


def get_latest_run(account_id, job_id):
    """Get latest run details for a job"""
    host = DBT_ACCESS_URL.replace("https://", "").replace("http://", "").rstrip("/")

    headers = {
        "Authorization": f"Bearer {DBT_SECRET}",
        "Content-Type": "application/json"
    }

    # Get latest run
    url = f"https://{host}/api/v2/accounts/{account_id}/runs/"
    params = {
        "job_definition_id": job_id,
        "limit": 1,
        "order_by": "-created_at"
    }

    response = requests.get(url, headers=headers, params=params, timeout=30)

    if response.status_code != 200:
        print(f"Error: Failed to get runs (Status: {response.status_code})")
        return None

    runs = response.json().get("data", [])
    if not runs:
        print("Error: No runs found for job")
        return None

    run_id = runs[0].get('id')

    # Get detailed run information
    detail_url = f"https://{host}/api/v2/accounts/{account_id}/runs/{run_id}/"
    detail_params = {
        "include_related": "job,trigger,run_steps"
    }

    detail_response = requests.get(detail_url, headers=headers, params=detail_params, timeout=30)

    if detail_response.status_code != 200:
        print(f"Error: Failed to get run details (Status: {detail_response.status_code})")
        return None

    return detail_response.json().get("data", {})


def main():
    config = read_config()

    if not config['account_id'] or not config['job_id']:
        print("Error: DBT_AccountID or DBT_JobID not configured in .config")
        sys.exit(1)

    print("DBT Configuration:")
    print(json.dumps(config, indent=2))

    account_id = config['account_id']
    job_id = config['job_id']

    print(f"\nFetching latest run for job {job_id}...")

    run_details = get_latest_run(account_id, job_id)

    if not run_details:
        print("Error: Could not retrieve run details")
        sys.exit(1)

    print("\n=== LATEST RUN DETAILS ===")
    print(json.dumps(run_details, indent=2))


if __name__ == "__main__":
    main()
