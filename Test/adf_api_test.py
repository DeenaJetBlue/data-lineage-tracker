"""
Azure Data Factory Pipeline Runs Test
Reads ADF configuration from ConfigurationFile.csv and credentials from backend/.env
Gets the latest run for the configured pipeline and displays its status

PREREQUISITES:
    pip install azure-identity
    pip install azure-mgmt-datafactory
    pip install python-dotenv
"""

import os
import sys
import csv
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Import Azure libraries
from azure.identity import ClientSecretCredential
from azure.mgmt.datafactory import DataFactoryManagementClient

# Load environment variables from backend/.env
env_path = Path(".env")
if not env_path.exists():
    print("❌ Error: .env not found!")
    sys.exit(1)

load_dotenv(env_path)

# Get ADF credentials from .env
ADF_TENANT_ID = os.getenv("ADF_TENANT_ID")
ADF_CLIENT_ID = os.getenv("ADF_CLIENT_ID")
ADF_CLIENT_SECRET = os.getenv("ADF_CLIENT_SECRET")
ADF_SUBSCRIPTION_ID = os.getenv("ADF_SUBSCRIPTION_ID")

if not all([ADF_TENANT_ID, ADF_CLIENT_ID, ADF_CLIENT_SECRET, ADF_SUBSCRIPTION_ID]):
    print("❌ Error: Required ADF credentials not configured in .env")
    print("   Required: ADF_TENANT_ID, ADF_CLIENT_ID, ADF_CLIENT_SECRET, ADF_SUBSCRIPTION_ID")
    sys.exit(1)

# Read configuration from CSV
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
                    'adls_storage_rg': row.get('ADLSStorageRG'),
                    'adls_path': row.get('ADLSPath'),
                    'adf_resource_group': row.get('ADFResourceGroup'),
                    'adf_factory_name': row.get('ADFFactoryName'),
                    'adf_pipeline_name': row.get('ADFPipelineName'),
                    'dbt_stage_job_id': row.get('DbtStageJobId'),
                    'dbt_stage_account_id': row.get('DbtStageAccountId'),
                    'dbt_star_job_id': row.get('DbtStarJobId'),
                    'dbt_star_account_id': row.get('DbtStarAccountId')
                }
    return None


def get_client():
    """Create DataFactory Management Client"""
    credential = ClientSecretCredential(
        tenant_id=ADF_TENANT_ID,
        client_id=ADF_CLIENT_ID,
        client_secret=ADF_CLIENT_SECRET
    )

    client = DataFactoryManagementClient(
        credential=credential,
        subscription_id=ADF_SUBSCRIPTION_ID
    )

    return client




def get_runs_for_pipeline(client, pipeline_name, resource_group, factory_name):
    """Get runs for a specific pipeline"""
    print("\n" + "="*70)
    print(f"🔷 STEP 1: GET RUNS FOR PIPELINE: {pipeline_name}")
    print("="*70)

    print(f"\n📋 Configuration:")
    print(f"   Factory Name: {factory_name}")
    print(f"   Resource Group: {resource_group}")
    print(f"   Pipeline Name: {pipeline_name}")

    print(f"\n🔐 Fetching pipeline runs...")

    try:
        from datetime import datetime, timedelta

        print("   (Querying factory runs from last 24 hours in UTC timezone...)")

        # Use UTC timezone
        now = datetime.utcnow()
        last_24_hours_ago = now - timedelta(hours=24)

        # Format dates as ISO 8601 strings with Z suffix
        last_updated_after = last_24_hours_ago.isoformat() + "Z"
        last_updated_before = now.isoformat() + "Z"

        print(f"   UTC time: {last_24_hours_ago.isoformat()[:16]} to {now.isoformat()[:16]}")

        # Query using the SDK with date range filter and order by RunEnd descending
        filter_params = {
            "filters": [
                {
                    "operand": "PipelineName",
                    "operator": "Equals",
                    "values": [pipeline_name]
                }
            ],
            "lastUpdatedAfter": last_updated_after,
            "lastUpdatedBefore": last_updated_before,
            "orderBy": [
                {
                    "orderBy": "RunEnd",
                    "order": "DESC"
                }
            ]
        }

        response = client.pipeline_runs.query_by_factory(
            resource_group_name=resource_group,
            factory_name=factory_name,
            filter_parameters=filter_params
        )

        # Get all runs
        all_runs = response.value if hasattr(response, 'value') and response.value else []
        print(f"   Found {len(all_runs)} runs for '{pipeline_name}' in last 7 days")

        if all_runs:
            # Sort by runEnd descending to get the latest completed run
            # For debugging, show first and last runs
            print(f"\n   📊 Run time details:")
            print(f"      First run: {all_runs[0].run_id} | Start: {all_runs[0].run_start} | End: {all_runs[0].run_end}")
            print(f"      Last run: {all_runs[-1].run_id} | Start: {all_runs[-1].run_start} | End: {all_runs[-1].run_end}")

            # Sort by runEnd descending, treating None as older
            def get_sort_key(r):
                if r.run_end:
                    return r.run_end
                else:
                    # For runs without end time, use run_start
                    return r.run_start if r.run_start else ""

            sorted_runs = sorted(all_runs, key=get_sort_key, reverse=True)
            pipeline_runs = sorted_runs

        print("\n✅ Pipeline runs retrieved successfully!")

        total_runs = len(pipeline_runs)
        print(f"   Total runs found for '{pipeline_name}': {total_runs}")

        if pipeline_runs:
            # Show date distribution
            from collections import Counter
            run_dates = [str(r.run_end.date()) if r.run_end else str(r.run_start.date()) for r in pipeline_runs]
            date_counts = Counter(run_dates)
            print(f"\n   📅 Runs by date: {dict(sorted(date_counts.items(), reverse=True))}")

            print(f"\n   📌 Latest 10 Runs (sorted by runEnd):")
            for i, run in enumerate(pipeline_runs[:10], 1):
                end_time = run.run_end if run.run_end else "Still running"
                print(f"   {i}. Run ID: {run.run_id} | Status: {run.status} | End: {end_time}")

            latest_run = pipeline_runs[0]
            run_id = latest_run.run_id
            print(f"\n   🎯 Using Latest Run ID: {run_id}")
            return run_id
        else:
            print(f"\n⚠️  No runs found for pipeline '{pipeline_name}'")
            return None

    except Exception as e:
        print(f"\n❌ Error fetching pipeline runs: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def get_pipeline_run_status(client, run_id, resource_group, factory_name):
    """Get status of a specific pipeline run"""
    print("\n" + "="*70)
    print("🔍 STEP 2: GET RUN STATUS")
    print("="*70)

    print(f"\n📋 Configuration:")
    print(f"   Factory Name: {factory_name}")
    print(f"   Resource Group: {resource_group}")
    print(f"   Run ID: {run_id}")

    print(f"\n🔐 Fetching run status...")

    try:
        response = client.pipeline_runs.get(
            resource_group_name=resource_group,
            factory_name=factory_name,
            run_id=run_id
        )

        print("\n✅ Run status retrieved successfully!")
        print(f"\n   📊 RUN STATUS:")
        print(f"   ================================")
        print(f"   - Run ID: {response.run_id}")
        print(f"   - Pipeline Name: {response.pipeline_name}")
        print(f"   - Status: {response.status}")
        if hasattr(response, 'run_start') and response.run_start:
            print(f"   - Run Start: {response.run_start}")
        if hasattr(response, 'run_end') and response.run_end:
            print(f"   - Run End: {response.run_end}")
        if hasattr(response, 'message') and response.message:
            print(f"   - Message: {response.message}")
        if hasattr(response, 'invoke_by') and response.invoke_by:
            print(f"   - Invoke By: {response.invoke_by}")
        print(f"   ================================")

        return response

    except Exception as e:
        print(f"\n❌ Error getting run status: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function to orchestrate API calls"""
    print("\n" + "="*70)
    print("🔷 AZURE DATA FACTORY PIPELINE RUNS - FROM CONFIGURATION")
    print("="*70)

    # Load configuration from CSV
    print("\n📖 Loading configuration from ConfigurationFile.csv...")
    config = load_table_config("Aerodata")

    if not config:
        print("❌ Error: Could not load configuration for table 'Aerodata'")
        sys.exit(1)

    print("✅ Configuration loaded successfully!")
    print(f"\n📋 Table Configuration:")
    print(f"   Table Name: {config['table_name']}")
    print(f"   ADF Resource Group: {config['adf_resource_group']}")
    print(f"   ADF Factory Name: {config['adf_factory_name']}")
    print(f"   ADF Pipeline Name: {config['adf_pipeline_name']}")

    # Create client
    print("\n🔐 Authenticating with Azure...")
    try:
        client = get_client()
        print("✅ Authentication successful!")
    except Exception as e:
        print(f"❌ Authentication failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 1: Get runs for the configured pipeline
    run_id = get_runs_for_pipeline(
        client,
        config['adf_pipeline_name'],
        config['adf_resource_group'],
        config['adf_factory_name']
    )

    if not run_id:
        print("\n❌ No runs found for pipeline. Exiting.")
        sys.exit(1)

    # Step 2: Get run status
    run_status = get_pipeline_run_status(
        client,
        run_id,
        config['adf_resource_group'],
        config['adf_factory_name']
    )

    if run_status:
        # Save run status to JSON file
        output_data = {
            "run_id": run_status.run_id,
            "pipeline_name": run_status.pipeline_name,
            "status": run_status.status,
            "run_start": str(run_status.run_start) if hasattr(run_status, 'run_start') and run_status.run_start else None,
            "run_end": str(run_status.run_end) if hasattr(run_status, 'run_end') and run_status.run_end else None,
            "message": run_status.message if hasattr(run_status, 'message') and run_status.message else None,
            "invoke_by": run_status.invoke_by if hasattr(run_status, 'invoke_by') and run_status.invoke_by else None,
            "timestamp": datetime.utcnow().isoformat()
        }

        output_filename = f"run_{run_id}.json"
        with open(output_filename, 'w') as f:
            json.dump(output_data, f, indent=2)

        print("\n" + "="*70)
        print("✅ Test Completed Successfully!")
        print("="*70)
        print(f"\n💾 Output saved to: {output_filename}")
    else:
        print("\n" + "="*70)
        print("❌ Test Failed - Could not retrieve run status")
        print("="*70)
        sys.exit(1)


if __name__ == "__main__":
    main()
