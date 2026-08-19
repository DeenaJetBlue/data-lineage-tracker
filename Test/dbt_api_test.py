"""
DBT API Test Script - Query Job Runs and Details
Reads credentials from backend/.env and queries DBT Cloud REST API
Gets list of runs for a job and retrieves the latest run details

Usage: python Test.py <account_id> <job_id>
Example: python Test.py 1644 70437463785258
"""

import requests
import json
import sys
import os
import csv
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from backend/.env
env_path = Path("backend/.env")
if not env_path.exists():
    print("❌ Error: backend/.env not found!")
    sys.exit(1)

load_dotenv(env_path)

# Get DBT credentials
DBT_SECRET = os.getenv("DBT_SECRET")
DBT_ACCESS_URL = os.getenv("DBT_ACCESS_URL")

if not DBT_SECRET or not DBT_ACCESS_URL:
    print("❌ Error: DBT_SECRET or DBT_ACCESS_URL not configured in .env")
    sys.exit(1)

# Load configuration from CSV
CONFIG_FILE = "ConfigurationFile.csv"
if not Path(CONFIG_FILE).exists():
    print(f"❌ Error: {CONFIG_FILE} not found!")
    sys.exit(1)

def load_table_config(table_name="Aerodata"):
    """Load table configuration from CSV"""
    with open(CONFIG_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('TableName') == table_name:
                return {
                    'table_name': row.get('TableName'),
                    'dbt_stage_account_id': row.get('DbtStageAccountId'),
                    'dbt_stage_job_id': row.get('DbtStageJobId'),
                    'dbt_star_account_id': row.get('DbtStarAccountId'),
                    'dbt_star_job_id': row.get('DbtStarJobId')
                }
    return None

# Get account_id and job_id from configuration
config = load_table_config("Aerodata")

if not config:
    print("❌ Error: Could not load configuration for table 'Aerodata'")
    sys.exit(1)

# Use stage job ID and account ID (modify if you prefer star)
account_id = config['dbt_stage_account_id']
job_id = config['dbt_stage_job_id']

if not account_id or not job_id:
    print("❌ Error: DBT account_id or job_id not configured in ConfigurationFile.csv")
    print("   Required: DbtStageAccountId and DbtStageJobId")
    sys.exit(1)

# Extract host from URL
host = DBT_ACCESS_URL.replace("https://", "").replace("http://", "").rstrip("/")

# Prepare headers
headers = {
    "Authorization": f"Bearer {DBT_SECRET}",
    "Content-Type": "application/json"
}


def get_job_runs(account_id: str, job_id: str):
    """Get list of runs for a specific job"""
    print("\n" + "="*70)
    print("🔹 STEP 1: FETCH JOB RUNS")
    print("="*70)

    url = f"https://{host}/api/v2/accounts/{account_id}/runs/"
    params = {
        "job_definition_id": job_id,
        "limit": 5,
        "offset": 0,
        "order_by": "-created_at"
    }

    print(f"\n📋 Configuration:")
    print(f"   DBT Host: {DBT_ACCESS_URL}")
    print(f"   Account ID: {account_id}")
    print(f"   Job ID: {job_id}")
    print(f"   DBT Token: {DBT_SECRET[:20]}...")

    print(f"\n🔐 Endpoint: {url}")
    print(f"📤 Query Params: {params}")
    print(f"📤 Sending GET request...\n")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response_json = response.json() if response.status_code == 200 else None

        print("="*70)
        print(f"📥 RESPONSE (Status: {response.status_code})")
        print("="*70)
        print(json.dumps(response_json, indent=2))
        print("="*70)

        if response.status_code == 200 and response_json:
            runs = response_json.get("data", [])
            if runs:
                print(f"\n✅ Found {len(runs)} runs for job {job_id}")
                latest_run = runs[0]
                print(f"\n   📊 Latest Run Summary:")
                print(f"   - Run ID: {latest_run.get('id')}")
                print(f"   - Status: {latest_run.get('status')} ({latest_run.get('status_humanized')})")
                print(f"   - Created At: {latest_run.get('created_at')}")
                print(f"   - Started At: {latest_run.get('started_at')}")
                print(f"   - Finished At: {latest_run.get('finished_at')}")

                return latest_run.get('id')
            else:
                print(f"\n⚠️  No runs found for job {job_id}")
                return None
        else:
            print(f"\n❌ Error: Status {response.status_code}")
            return None

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return None


def get_run_details(account_id: str, run_id: str):
    """Get detailed information about a specific run"""
    print("\n" + "="*70)
    print("🔹 STEP 2: FETCH RUN DETAILS")
    print("="*70)

    url = f"https://{host}/api/v2/accounts/{account_id}/runs/{run_id}/"
    params = {
        "include_related": "job,trigger,run_steps"
    }

    print(f"\n🔐 Endpoint: {url}")
    print(f"📤 Query Params: {params}")
    print(f"📤 Sending GET request...\n")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response_json = response.json() if response.status_code == 200 else None

        print("="*70)
        print(f"📥 RESPONSE (Status: {response.status_code})")
        print("="*70)
        print(json.dumps(response_json, indent=2))
        print("="*70)

        if response.status_code == 200 and response_json:
            run_data = response_json.get("data", {})
            print(f"\n✅ Run Details Retrieved!")
            print(f"\n   📊 Run Summary:")
            print(f"   - Run ID: {run_data.get('id')}")
            print(f"   - Job ID: {run_data.get('job_definition_id')}")
            print(f"   - Status: {run_data.get('status')} ({run_data.get('status_humanized')})")
            print(f"   - Created At: {run_data.get('created_at')}")
            print(f"   - Started At: {run_data.get('started_at')}")
            print(f"   - Finished At: {run_data.get('finished_at')}")
            print(f"   - Duration: {run_data.get('duration_humanized')}")
            print(f"   - Is Success: {run_data.get('is_success')}")
            print(f"   - Is Error: {run_data.get('is_error')}")

            if run_data.get('job'):
                job_info = run_data.get('job', {})
                print(f"\n   💼 Job Info:")
                print(f"   - Name: {job_info.get('name')}")
                print(f"   - Type: {job_info.get('job_type')}")

            return run_data
        else:
            print(f"\n❌ Error: Status {response.status_code}")
            return None

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return None


def main():
    """Main function to orchestrate API calls"""
    print("\n" + "="*70)
    print("🔹 DBT CLOUD RUNS API TEST")
    print("="*70)

    # Step 1: Get list of runs for the job
    run_id = get_job_runs(account_id, job_id)

    if run_id:
        # Step 2: Get detailed information about the latest run
        run_details = get_run_details(account_id, run_id)

        if run_details:
            # Save run details to JSON file
            output_data = {
                "run_id": run_details.get('id'),
                "job_id": run_details.get('job_definition_id'),
                "account_id": account_id,
                "status": run_details.get('status'),
                "status_humanized": run_details.get('status_humanized'),
                "created_at": run_details.get('created_at'),
                "started_at": run_details.get('started_at'),
                "finished_at": run_details.get('finished_at'),
                "duration_humanized": run_details.get('duration_humanized'),
                "is_success": run_details.get('is_success'),
                "is_error": run_details.get('is_error'),
                "job_name": run_details.get('job', {}).get('name') if run_details.get('job') else None,
                "timestamp": datetime.utcnow().isoformat()
            }

            output_filename = f"dbt_run_{run_id}.json"
            with open(output_filename, 'w') as f:
                json.dump(output_data, f, indent=2)

            print("\n" + "="*70)
            print("✅ Test Completed Successfully!")
            print("="*70)
            print(f"\n💾 Output saved to: {output_filename}")
        else:
            print("\n" + "="*70)
            print("❌ Test Failed: Could not retrieve run details")
            print("="*70)
    else:
        print("\n" + "="*70)
        print("❌ Test Failed: Could not retrieve run information")
        print("="*70)


# Run the function
if __name__ == "__main__":
    main()
