import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

from azure.identity import ClientSecretCredential
from azure.mgmt.datafactory import DataFactoryManagementClient

env_path = Path(".env")
if not env_path.exists():
    print("Error: .env not found!")
    sys.exit(1)

load_dotenv(env_path)

ADF_TENANT_ID = os.getenv("ADF_TENANT_ID")
ADF_CLIENT_ID = os.getenv("ADF_CLIENT_ID")
ADF_CLIENT_SECRET = os.getenv("ADF_CLIENT_SECRET")
ADF_SUBSCRIPTION_ID = os.getenv("ADF_SUBSCRIPTION_ID")

if not all([ADF_TENANT_ID, ADF_CLIENT_ID, ADF_CLIENT_SECRET, ADF_SUBSCRIPTION_ID]):
    print("Error: Required ADF credentials not configured in .env")
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
        'adf_resource_group': config.get('ADF_Resource_Group'),
        'adf_factory_name': config.get('ADF_Factory_Name'),
        'adf_pipeline_name': config.get('ADF_Pipeline_Name')
    }


def get_client():
    credential = ClientSecretCredential(
        tenant_id=ADF_TENANT_ID,
        client_id=ADF_CLIENT_ID,
        client_secret=ADF_CLIENT_SECRET
    )
    return DataFactoryManagementClient(
        credential=credential,
        subscription_id=ADF_SUBSCRIPTION_ID
    )


def get_latest_run(client, pipeline_name, resource_group, factory_name):
    # Query all runs ordered by end time (descending)
    filter_params = {
        "orderBy": [{
            "orderBy": "RunEnd",
            "order": "DESC"
        }]
    }

    response = client.pipeline_runs.query_by_factory(
        resource_group_name=resource_group,
        factory_name=factory_name,
        filter_parameters=filter_params
    )

    print(f"\nDEBUG: Query all runs (no filter)")
    print(f"DEBUG: Total runs found: {len(response.value) if response.value else 0}")

    runs = response.value if hasattr(response, 'value') and response.value else []

    # Filter manually to find matching pipeline
    matching_runs = [run for run in runs if run.pipeline_name == pipeline_name]
    print(f"DEBUG: Runs matching pipeline '{pipeline_name}': {len(matching_runs)}")

    if matching_runs:
        print(f"DEBUG: Found {len(matching_runs)} matching runs. Returning latest...")

    return matching_runs[0] if matching_runs else None


def print_metrics(run):
    metrics = {
        "run_id": run.run_id,
        "pipeline_name": run.pipeline_name,
        "status": run.status,
        "run_start": str(run.run_start) if hasattr(run, 'run_start') and run.run_start else None,
        "run_end": str(run.run_end) if hasattr(run, 'run_end') and run.run_end else None,
    }
    print("Metrics:")
    print(json.dumps(metrics, indent=2))


def get_run_by_id(client, run_id, resource_group, factory_name):
    """Query a specific run by ID"""
    try:
        run = client.pipeline_runs.get(
            resource_group_name=resource_group,
            factory_name=factory_name,
            run_id=run_id
        )
        return run
    except Exception as e:
        print(f"Error querying run by ID: {e}")
        return None


def main():
    config = read_config()
    if not config:
        print("Error: Could not load configuration from .config")
        sys.exit(1)

    print("Pipeline Configuration:")
    print(json.dumps(config, indent=2))

    client = get_client()

    # Try to get run by specific ID first
    run_id = "c57901d9-ca68-4172-af9b-24e02d654432"
    print(f"\n=== Querying run by ID: {run_id} ===")
    run_by_id = get_run_by_id(
        client,
        run_id,
        config['adf_resource_group'],
        config['adf_factory_name']
    )

    if run_by_id:
        print("SUCCESS: Found run by ID!")
        print(f"Pipeline name: {run_by_id.pipeline_name}")
        print(f"Status: {run_by_id.status}")
        print("\nRun Details:")
        run_data = {
            "run_id": run_by_id.run_id,
            "pipeline_name": run_by_id.pipeline_name,
            "status": run_by_id.status,
            "run_start": str(run_by_id.run_start) if hasattr(run_by_id, 'run_start') and run_by_id.run_start else None,
            "run_end": str(run_by_id.run_end) if hasattr(run_by_id, 'run_end') and run_by_id.run_end else None,
        }
        print(json.dumps(run_data, indent=2))
        print_metrics(run_by_id)
    else:
        print("Error: Could not find run by ID")

    print("\n=== Now trying query by pipeline name ===")
    latest_run = get_latest_run(
        client,
        config['adf_pipeline_name'],
        config['adf_resource_group'],
        config['adf_factory_name']
    )

    if not latest_run:
        print("Error: No runs found for pipeline (via query)")
    else:
        print("SUCCESS: Found run by pipeline name query!")


if __name__ == "__main__":
    main()
