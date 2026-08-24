r"""
MOVEit Automation API - Task Logs Viewer

REQUIRED PACKAGES:
    pip install requests

RUN INSTRUCTIONS:
    1. Connect to JetBlue VPN
    2. Open PowerShell/Command Prompt
    3. Navigate to: c:\Users\DeenaNath\data-lineage-tracker\Test
    4. Run: python MoveIT_api.py

If you get 'ModuleNotFoundError', run:
    pip install requests
"""

import sys
import os
import requests
import json
import warnings
from urllib3.exceptions import InsecureRequestWarning
from dotenv import load_dotenv
from dotenv import dotenv_values

warnings.simplefilter('ignore', InsecureRequestWarning)

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package is not installed.")
    print("\nInstall it with:")
    print("    pip install requests")
    sys.exit(1)

ENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=ENV_PATH)
DOTENV_VALUES = dotenv_values(ENV_PATH)

WEBADMIN_SERVER = os.getenv("MOVEIT_SERVER") or os.getenv("WEBADMIN_SERVER") or DOTENV_VALUES.get("WEBADMIN_SERVER")
USERNAME = os.getenv("MOVEIT_USERNAME") or DOTENV_VALUES.get("MOVEIT_USERNAME") or DOTENV_VALUES.get("USERNAME") or os.getenv("USERNAME")
PASSWORD = os.getenv("MOVEIT_PASSWORD") or DOTENV_VALUES.get("MOVEIT_PASSWORD") or DOTENV_VALUES.get("PASSWORD") or os.getenv("PASSWORD")

# Target Task ID
TARGET_TASK_ID = "243149144"

BASE_URL = f"https://{WEBADMIN_SERVER}/api/v1"

print("=" * 80)
print("MOVEit Automation API - Task Logs Viewer")
print("=" * 80)
print(f"\n📌 Connecting to MOVEit API...")
print(f"   Server: {WEBADMIN_SERVER}")
print(f"   Base URL: {BASE_URL}")
print(f"   Target Task ID: {TARGET_TASK_ID}\n")

def get_access_token():
    """Request an access token from MOVEit Automation API"""
    url = f"{BASE_URL}/token"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "password",
        "server_host": WEBADMIN_SERVER,
        "username": USERNAME,
        "password": PASSWORD
    }

    response = None
    try:
        print("[1] Authenticating with MOVEit API...")
        print("-" * 80)
        print(f"POST: {url}")
        response = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        print(f"Status: {response.status_code}")
        response.raise_for_status()
        token_data = response.json()
        token = token_data["access_token"]
        print(f"✓ Authentication successful!")
        print(f"✓ Token: {token[:30]}...")
        return token
    except requests.exceptions.Timeout:
        print(f"✗ Error: Request timed out after 10 seconds. Check if server is reachable.")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"✗ Connection error: {e}")
        print(f"   Check if {WEBADMIN_SERVER} is reachable (VDI connection required)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"✗ Error requesting token: {e}")
        if response is not None and response.text:
            print(f"   API response: {response.text}")
        return None

def get_task_details(access_token, task_id):
    """Get details for a specific task"""
    url = f"{BASE_URL}/tasks/{task_id}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    try:
        print(f"\n[2] Fetching Task Details...")
        print("-" * 80)
        print(f"GET: {url}")
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            task_details = response.json()
            print(f"✓ Task details retrieved!")
            return task_details
        else:
            print(f"✗ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.Timeout:
        print(f"✗ Error: Request timed out after 10 seconds")
        return None
    except requests.exceptions.RequestException as e:
        print(f"✗ Error fetching task details: {e}")
        return None

def get_task_logs(access_token, task_id, page=1, per_page=50):
    """Get logs for a specific task"""
    url = f"{BASE_URL}/tasks/{task_id}/log"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "page": page,
        "perPage": per_page
    }

    try:
        print(f"\n[3] Fetching Task Logs...")
        print("-" * 80)
        print(f"GET: {url}")
        print(f"Parameters: page={page}, perPage={per_page}")
        response = requests.get(url, headers=headers, params=params, verify=False, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            logs_data = response.json()
            print(f"✓ Task logs retrieved!")
            return logs_data
        elif response.status_code == 404:
            print(f"✗ Error: Task ID {task_id} not found")
            return None
        else:
            print(f"✗ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.Timeout:
        print(f"✗ Error: Request timed out after 10 seconds")
        return None
    except requests.exceptions.RequestException as e:
        print(f"✗ Error fetching task logs: {e}")
        return None

def main():
    print("Requesting access token...\n")
    token = get_access_token()

    if not token:
        print("\n✗ Failed to get access token")
        return

    # Get task details
    task_details = get_task_details(token, TARGET_TASK_ID)

    if task_details:
        print("\n📋 Task Details:")
        print("-" * 80)
        print(json.dumps(task_details, indent=2))

    # Get task logs
    logs_data = get_task_logs(token, TARGET_TASK_ID)

    if logs_data:
        print("\n📊 Task Logs Summary:")
        print("-" * 80)

        # Extract logs and pagination info
        if isinstance(logs_data, dict):
            logs = logs_data.get("logs", []) or logs_data.get("items", []) or [logs_data]
            total = logs_data.get("totalCount", len(logs))
            page = logs_data.get("page", 1)
            per_page = logs_data.get("perPage", 50)

            print(f"Total Logs: {total}")
            print(f"Page: {page}")
            print(f"Per Page: {per_page}")
            print(f"Logs Retrieved: {len(logs)}\n")
        else:
            logs = logs_data if isinstance(logs_data, list) else [logs_data]

        if logs:
            print("Log Entries:")
            print("-" * 80)
            for i, log_entry in enumerate(logs[:10], 1):  # Show first 10
                print(f"\n{i}. {json.dumps(log_entry, indent=2)}")

            if len(logs) > 10:
                print(f"\n... and {len(logs) - 10} more log entries")

            # Show full JSON
            print("\n\n📄 Full Logs Response (JSON):")
            print("-" * 80)
            print(json.dumps(logs_data, indent=2))
        else:
            print("No log entries found")
    else:
        print("\n✗ Failed to retrieve task logs")

    print("\n" + "=" * 80)
    print("✓ MOVEit API Task Logs Viewer Complete")
    print("=" * 80)

if __name__ == "__main__":
    main()
