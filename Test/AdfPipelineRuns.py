import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta

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
    # Calculate time range: last 24 hours
    now = datetime.utcnow()
    one_day_ago = now - timedelta(days=1)

    # Format timestamps as ISO 8601
    last_updated_before = now.isoformat() + "Z"
    last_updated_after = one_day_ago.isoformat() + "Z"

    filter_params = {
        "filters": [{
            "operand": "PipelineName",
            "operator": "Equals",
            "values": [pipeline_name]
        }],
        "lastUpdatedAfter": last_updated_after,
        "lastUpdatedBefore": last_updated_before,
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

    runs = response.value if hasattr(response, 'value') and response.value else []
    return runs[0] if runs else None




def main():
    config = read_config()
    if not config:
        print("Error: Could not load configuration from .config")
        sys.exit(1)

    print("Pipeline Configuration:")
    print(json.dumps(config, indent=2))

    client = get_client()

    # Get latest run
    latest_run = get_latest_run(
        client,
        config['adf_pipeline_name'],
        config['adf_resource_group'],
        config['adf_factory_name']
    )

    if not latest_run:
        print("Error: No runs found for pipeline")
        sys.exit(1)

    run_id = latest_run.run_id
    print(f"\nLatest Run ID: {run_id}")

    # Get full details of the run
    full_run_details = client.pipeline_runs.get(
        resource_group_name=config['adf_resource_group'],
        factory_name=config['adf_factory_name'],
        run_id=run_id
    )

    print("\n=== FULL RUN DETAILS ===")

    # Extract all available attributes
    run_details = {
        "runId": full_run_details.run_id,
        "pipelineName": full_run_details.pipeline_name,
        "status": full_run_details.status,
        "runStart": str(full_run_details.run_start) if hasattr(full_run_details, 'run_start') and full_run_details.run_start else None,
        "runEnd": str(full_run_details.run_end) if hasattr(full_run_details, 'run_end') and full_run_details.run_end else None,
        "durationInMs": full_run_details.duration_in_ms if hasattr(full_run_details, 'duration_in_ms') else None,
        "lastUpdated": str(full_run_details.last_updated) if hasattr(full_run_details, 'last_updated') and full_run_details.last_updated else None,
        "message": full_run_details.message if hasattr(full_run_details, 'message') else None,
        "annotations": full_run_details.annotations if hasattr(full_run_details, 'annotations') else [],
        "parameters": full_run_details.parameters if hasattr(full_run_details, 'parameters') else {},
        "invokedBy": {
            "name": full_run_details.invoked_by.name if hasattr(full_run_details, 'invoked_by') and full_run_details.invoked_by and hasattr(full_run_details.invoked_by, 'name') else None,
            "id": full_run_details.invoked_by.id if hasattr(full_run_details, 'invoked_by') and full_run_details.invoked_by and hasattr(full_run_details.invoked_by, 'id') else None,
        } if hasattr(full_run_details, 'invoked_by') and full_run_details.invoked_by else None,
    }

    print(json.dumps(run_details, indent=2))


if __name__ == "__main__":
    main()
