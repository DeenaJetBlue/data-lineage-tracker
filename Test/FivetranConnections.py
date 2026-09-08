import requests
import os
import json
from dotenv import load_dotenv
from base64 import b64encode

# Load environment variables from .env file
load_dotenv()

# Get Fivetran credentials from .env
FIVETRAN_API_KEY = os.getenv("FIVETRAN_API_KEY")
FIVETRAN_API_SECRET = os.getenv("FIVETRAN_API_SECRET")
FIVETRAN_SYSTEM_KEY = os.getenv("FIVETRAN_SYSTEM_KEY")

# Create the authorization header using base64 encoding
auth_string = f"{FIVETRAN_API_KEY}:{FIVETRAN_API_SECRET}"
auth_bytes = auth_string.encode("utf-8")
auth_b64 = b64encode(auth_bytes).decode("utf-8")

headers = {
    "Accept": "application/json;version=2",
    "Authorization": f"Basic {auth_b64}"
}

print("=" * 80)
print("FIVETRAN API - List Connections and Sync History")
print("=" * 80)

# Step 1: List all connections
print("\n[1] Fetching all connections...")
url = "https://api.fivetran.com/v1/connections"
querystring = {"limit": "100"}

try:
    response = requests.get(url, headers=headers, params=querystring)
    response.raise_for_status()
    connections_data = response.json()

    connections = connections_data.get("data", {}).get("items", [])

    if not connections:
        print("❌ No connections found!")
    else:
        print(f"✓ Found {len(connections)} connection(s)")

        # Display all connections
        print("\nAvailable Connections:")
        print("-" * 80)
        for i, conn in enumerate(connections, 1):
            print(f"{i}. ID: {conn.get('id')}")
            print(f"   Name: {conn.get('name')}")
            print(f"   Service: {conn.get('service')}")
            print(f"   Status: {conn.get('status')}")
            print()

        # Step 2: Pick the connection with ID "late_ordinary"
        target_connection_id = "late_ordinary"
        selected_connection = next((conn for conn in connections if conn.get("id") == target_connection_id), None)

        if not selected_connection:
            print(f"❌ Connection with ID '{target_connection_id}' not found!")
            print("Available connection IDs:")
            for conn in connections:
                print(f"  - {conn.get('id')}")
        else:
            connection_id = selected_connection.get("id")
            connection_name = selected_connection.get("name")

            print("-" * 80)
            print(f"📌 Selected Connection: {connection_name} (ID: {connection_id})")
            print("-" * 80)

            # Step 3: Get sync history for the selected connection
            print(f"\n[2] Fetching sync history for '{connection_name}'...")
            sync_history_url = f"https://api.fivetran.com/v1/connections/{connection_id}/sync-history"
            sync_querystring = {"limit": "20"}  # Get last 20 syncs

            try:
                sync_response = requests.get(sync_history_url, headers=headers, params=sync_querystring)
                sync_response.raise_for_status()
                sync_data = sync_response.json()

                syncs = sync_data.get("data", {}).get("items", [])

                if not syncs:
                    print("❌ No sync history found!")
                else:
                    print(f"✓ Found {len(syncs)} sync record(s)")

                    # Display sync history
                    print("\nSync History:")
                    print("-" * 80)
                    for i, sync in enumerate(syncs, 1):
                        print(f"{i}. Sync ID: {sync.get('id')}")
                        print(f"   Status: {sync.get('status')}")
                        print(f"   Started: {sync.get('started_at')}")
                        print(f"   Completed: {sync.get('completed_at')}")
                        print(f"   Records Processed: {sync.get('transformed_rows_count')}")
                        print()

                    # Print raw JSON for reference
                    print("-" * 80)
                    print("Raw Sync History (JSON):")
                    print(json.dumps(syncs, indent=2))

            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching sync history: {e}")
                print(f"Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")

except requests.exceptions.RequestException as e:
    print(f"❌ Error fetching connections: {e}")
    print(f"Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")

print("\n" + "=" * 80)
