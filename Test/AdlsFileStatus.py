"""
ADLS File Existence Check
Reads configuration from ConfigurationFile.csv and credentials from .env
Checks if a particular file/path exists in Azure Data Lake Storage Gen2
Uses Service Principal authentication

PREREQUISITES:
    pip install azure-storage-file-datalake
    pip install azure-identity
    pip install python-dotenv

REQUIRED .env variables:
    ADLS_TENANT_ID=<your-tenant-id>
    ADLS_CLIENT_ID=<your-client-id>
    ADLS_CLIENT_SECRET=<your-client-secret>

"""

import os
import csv
import sys
from pathlib import Path
from dotenv import load_dotenv
from azure.storage.filedatalake import DataLakeServiceClient
from azure.identity import ClientSecretCredential
from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError

# Load environment variables from .env
env_path = Path(__file__).parent.parent / ".env"
if not env_path.exists():
    print("❌ Error: .env not found in project root!")
    sys.exit(1)

load_dotenv(env_path)

# Get service principal credentials from .env
ADLS_TENANT_ID = os.getenv("ADLS_TENANT_ID")
ADLS_CLIENT_ID = os.getenv("ADLS_CLIENT_ID")
ADLS_CLIENT_SECRET = os.getenv("ADLS_CLIENT_SECRET")

if not all([ADLS_TENANT_ID, ADLS_CLIENT_ID, ADLS_CLIENT_SECRET]):
    print("❌ Error: Missing required credentials in .env")
    print("   Required: ADLS_TENANT_ID, ADLS_CLIENT_ID, ADLS_CLIENT_SECRET")
    sys.exit(1)

# Service Principal Details
APPLICATION_ID = ADLS_CLIENT_ID

def load_config(table_name: str = "Aerodata") -> dict:
    """Load configuration from ConfigurationFile.csv"""
    config_file = "ConfigurationFile.csv"

    if not Path(config_file).exists():
        print(f"❌ Error: {config_file} not found!")
        return None

    with open(config_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('TableName') == table_name:
                return {
                    'table_name': row.get('TableName'),
                    'adls_storage_rg': row.get('ADLSStorageRG'),
                    'adls_storage_name': row.get('ADLSStorageName'),
                    'adls_container_name': row.get('ADLSContainerName'),
                    'adls_path': row.get('ADLSPath'),
                    'adf_resource_group': row.get('ADFResourceGroup'),
                    'adf_factory_name': row.get('ADFFactoryName'),
                    'adf_pipeline': row.get('ADFPipelineName')
                }

    print(f"❌ Error: Table '{table_name}' not found in {config_file}")
    return None


def check_file_exists(storage_account: str, container_name: str, file_path: str) -> dict:
    """
    Check if a file/directory exists in ADLS using Service Principal authentication

    Args:
        storage_account: ADLS storage account name
        container_name: Container name (e.g., "dataforrag")
        file_path: File path within container (e.g., "FolderTest/Demo.txt")
    """
    try:

        print(f"\n📋 ADLS File Existence Check (Service Principal Authentication)")
        print("=" * 70)
        print(f"Storage Account: {storage_account}")
        print(f"Container: {container_name}")
        print(f"File Path: {file_path}")
        print(f"Client ID: {APPLICATION_ID}")

        # Create DataLakeServiceClient using Service Principal
        print(f"\n🔐 Connecting with Service Principal...")

        account_url = f"https://{storage_account}.dfs.core.windows.net"
        print(f"   Account URL: {account_url}")

        # Create ClientSecretCredential using service principal
        print(f"   Using Service Principal authentication...")
        credential = ClientSecretCredential(
            tenant_id=ADLS_TENANT_ID,
            client_id=ADLS_CLIENT_ID,
            client_secret=ADLS_CLIENT_SECRET
        )

        service_client = DataLakeServiceClient(account_url=account_url, credential=credential)
        print(f"✅ Connected successfully with Service Principal!")

        file_system_client = service_client.get_file_system_client(file_system=container_name)

        print(f"\n🔍 Checking if path exists...")

        # Try to get file properties first
        try:
            file_client = file_system_client.get_file_client(file_path)
            properties = file_client.get_file_properties()
            print(f"\n✅ File EXISTS!")
            print(f"\n📊 Properties:")
            print(f"   - Size: {properties.size} bytes")
            print(f"   - Last Modified: {properties.last_modified}")
            return {"status": "exists", "message": "File found in ADLS", "container": container_name, "path": file_path, "type": "file"}
        except ResourceNotFoundError:
            # If file not found, try directory
            try:
                directory_client = file_system_client.get_directory_client(file_path)
                properties = directory_client.get_directory_properties()
                print(f"\n✅ Directory EXISTS!")
                print(f"\n📊 Properties:")
                print(f"   - Last Modified: {properties.last_modified}")
                return {"status": "exists", "message": "Directory found in ADLS", "container": container_name, "path": file_path, "type": "directory"}
            except ResourceNotFoundError:
                raise

    except ResourceNotFoundError:
        print(f"\n⚠️  Path NOT FOUND")
        return {"status": "not_found", "message": "Path does not exist in ADLS"}
    except ClientAuthenticationError as e:
        error_message = str(e)
        print(f"\n⚠️  Authentication Error")
        print(f"\n❌ Error: {error_message}")
        print(f"\n💡 Troubleshooting:")
        print(f"   1. Verify credentials in .env:")
        print(f"      - ADLS_TENANT_ID")
        print(f"      - ADLS_CLIENT_ID")
        print(f"      - ADLS_CLIENT_SECRET")
        print(f"   2. Check if Service Principal is valid and not expired")
        print(f"   3. Verify RBAC roles assigned to the Service Principal on storage account:")
        print(f"      - 'Storage Blob Data Reader' (read-only)")
        print(f"      - 'Storage Blob Data Contributor' (read/write)")
        print(f"   4. Ensure Service Principal has access to the specific container")
        return {"status": "error", "message": f"Authentication failed: {error_message}"}
    except Exception as e:
        error_message = str(e)
        print(f"\n❌ Error: {error_message}")
        print(f"\n💡 Troubleshooting:")
        print(f"   1. Check if the path/container exists in the storage account")
        print(f"   2. Verify Managed Identity has the correct RBAC role assignments")
        print(f"   3. Ensure proper network connectivity to the storage account")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Error checking path: {error_message}"}


def main():
    """Main function"""
    print("\n" + "="*70)
    print("🔷 ADLS FILE EXISTENCE CHECK (Service Principal)")
    print("="*70)
    print(f"\n🔑 Using Service Principal Authentication:")
    print(f"   Client ID: {APPLICATION_ID}")
    print(f"   Tenant ID: {ADLS_TENANT_ID}")

    print("\n📖 Loading configuration from ConfigurationFile.csv...")
    config = load_config("Aerodata")

    if not config:
        sys.exit(1)

    print("✅ Configuration loaded successfully!")
    print(f"\n📋 Configuration Details:")
    print(f"   Table Name: {config['table_name']}")
    print(f"   Storage RG: {config['adls_storage_rg']}")
    print(f"   Storage Name: {config['adls_storage_name']}")
    print(f"   Container Name: {config['adls_container_name']}")
    print(f"   Full Path: {config['adls_path']}")

    print("\n\n🧪 TEST: Check if path exists using Service Principal")
    result = check_file_exists(
        storage_account=config['adls_storage_name'],
        container_name=config['adls_container_name'],
        file_path=config['adls_path']
    )
    print(f"\n📌 Result: {result['status'].upper()}")
    print(f"   {result['message']}")

    print("\n" + "="*70)
    print("✅ Test completed!")
    print("="*70)


if __name__ == "__main__":
    main()
 