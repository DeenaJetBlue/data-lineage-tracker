"""
ADLS File Listing and Status Check
Reads ADLS configuration from .config and credentials from .env
Lists all files in ADLS root folder and shows details of the most recent file
Uses Service Principal authentication

PREREQUISITES:
    pip install azure-storage-file-datalake
    pip install azure-identity
    pip install python-dotenv

REQUIRED .env variables:
    ADLS_TENANT_ID=<your-tenant-id>
    ADLS_CLIENT_ID=<your-client-id>
    ADLS_CLIENT_SECRET=<your-client-secret>

REQUIRED .config variables:
    ADLS_Storage_Account_Name=<storage-account>
    ADLS_Container_Name=<container-name>
    ADLS_Root_Folder=<root-folder-path>

"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from azure.storage.filedatalake import DataLakeServiceClient
from azure.identity import ClientSecretCredential
from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError
from datetime import datetime

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

APPLICATION_ID = ADLS_CLIENT_ID

def load_config_file() -> dict:
    """Load ADLS configuration from .config file"""
    config_path = Path(__file__).parent.parent / ".config"

    if not config_path.exists():
        print(f"❌ Error: .config not found in project root!")
        return None

    config = {}
    try:
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()

        # Extract ADLS configuration
        adls_config = {
            'adls_storage_name': config.get('ADLS_Storage_Account_Name'),
            'adls_container_name': config.get('ADLS_Container_Name'),
            'adls_root_folder': config.get('ADLS_Root_Folder'),
            'adls_resource_group': config.get('ADLS_Resource_Group')
        }

        if not all([adls_config['adls_storage_name'], adls_config['adls_container_name'], adls_config['adls_root_folder']]):
            print("❌ Error: Missing required ADLS configuration in .config")
            print("   Required: ADLS_Storage_Account_Name, ADLS_Container_Name, ADLS_Root_Folder")
            return None

        return adls_config
    except Exception as e:
        print(f"❌ Error reading .config: {e}")
        return None


def list_files_in_folder(storage_account: str, container_name: str, folder_path: str) -> list:
    """
    List all files in a folder in ADLS and return details

    Args:
        storage_account: ADLS storage account name
        container_name: Container name
        folder_path: Folder path within container

    Returns:
        List of file details sorted by modification time (newest first)
    """
    try:
        print(f"\n📂 Listing Files in ADLS Folder")
        print("=" * 70)
        print(f"Storage Account: {storage_account}")
        print(f"Container: {container_name}")
        print(f"Folder Path: {folder_path}")

        print(f"\n🔐 Connecting with Service Principal...")
        account_url = f"https://{storage_account}.dfs.core.windows.net"

        credential = ClientSecretCredential(
            tenant_id=ADLS_TENANT_ID,
            client_id=ADLS_CLIENT_ID,
            client_secret=ADLS_CLIENT_SECRET
        )

        service_client = DataLakeServiceClient(account_url=account_url, credential=credential)
        print(f"✅ Connected successfully!")

        file_system_client = service_client.get_file_system_client(file_system=container_name)
        directory_client = file_system_client.get_directory_client(folder_path)

        print(f"\n🔍 Scanning folder for files...")
        files = []

        try:
            paths = directory_client.get_paths(recursive=True)
            for path in paths:
                if not path.is_directory:
                    file_details = {
                        'name': path.name,
                        'full_path': path.name,
                        'size': path.content_length,
                        'last_modified': path.last_modified,
                    }
                    files.append(file_details)

            if not files:
                print(f"⚠️  No files found in folder")
                return []

            # Sort by last_modified (newest first)
            files.sort(key=lambda x: x['last_modified'], reverse=True)
            print(f"✅ Found {len(files)} file(s)")
            return files

        except ResourceNotFoundError:
            print(f"⚠️  Folder not found: {folder_path}")
            return []

    except ClientAuthenticationError as e:
        error_message = str(e)
        print(f"\n❌ Authentication Error: {error_message}")
        print(f"\n💡 Verify credentials in .env:")
        print(f"   - ADLS_TENANT_ID")
        print(f"   - ADLS_CLIENT_ID")
        print(f"   - ADLS_CLIENT_SECRET")
        return []
    except Exception as e:
        error_message = str(e)
        print(f"\n❌ Error: {error_message}")
        import traceback
        traceback.print_exc()
        return []


def main():
    """Main function"""
    print("\n" + "="*70)
    print("🔷 ADLS FILE LISTING AND STATUS (Service Principal)")
    print("="*70)
    print(f"\n🔑 Using Service Principal Authentication:")
    print(f"   Client ID: {APPLICATION_ID}")
    print(f"   Tenant ID: {ADLS_TENANT_ID}")

    print("\n📖 Loading configuration from .config...")
    config = load_config_file()

    if not config:
        sys.exit(1)

    print("✅ Configuration loaded successfully!")
    print(f"\n📋 ADLS Configuration:")
    print(f"   Storage Account: {config['adls_storage_name']}")
    print(f"   Container: {config['adls_container_name']}")
    print(f"   Resource Group: {config['adls_resource_group']}")
    print(f"   Root Folder: {config['adls_root_folder']}")

    # List all files in the root folder
    files = list_files_in_folder(
        storage_account=config['adls_storage_name'],
        container_name=config['adls_container_name'],
        folder_path=config['adls_root_folder']
    )

    if files:
        print(f"\n📊 Files Found (sorted by most recent):")
        print("=" * 70)
        for i, file in enumerate(files, 1):
            print(f"\n{i}. File: {file['name']}")
            print(f"   Path: {file['full_path']}")
            print(f"   Size: {file['size']:,} bytes")
            print(f"   Last Modified: {file['last_modified']}")

        # Show most recent file details
        most_recent = files[0]
        print(f"\n\n⭐ MOST RECENT FILE:")
        print("=" * 70)
        print(f"Name: {most_recent['name']}")
        print(f"Full Path: {most_recent['full_path']}")
        print(f"Size: {most_recent['size']:,} bytes ({most_recent['size'] / (1024*1024):.2f} MB)")
        print(f"Last Modified: {most_recent['last_modified']}")

    print("\n" + "="*70)
    print("✅ Operation completed!")
    print("="*70)


if __name__ == "__main__":
    main()
 