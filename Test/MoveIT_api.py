r"""
MOVEit Automation API - Task Lister

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

warnings.simplefilter('ignore', InsecureRequestWarning)

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package is not installed.")
    print("\nInstall it with:")
    print("    pip install requests")
    sys.exit(1)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

WEBADMIN_SERVER = os.getenv("WEBADMIN_SERVER")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

BASE_URL = f"https://{WEBADMIN_SERVER}/api/v1"

print(f"Connecting to MOVEit API...")
print(f"  Server: {WEBADMIN_SERVER}")
print(f"  Base URL: {BASE_URL}\n")

def get_access_token():
    """Request an access token from MOVEit Automation API"""
    url = f"{BASE_URL}/token"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD
    }

    try:
        print(f"DEBUG: POST request to {url}")
        response = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        print(f"DEBUG: Response status: {response.status_code}")
        response.raise_for_status()
        token_data = response.json()
        return token_data["access_token"]
    except requests.exceptions.Timeout:
        print(f"✗ Error: Request timed out after 10 seconds. Check if server is reachable.")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"✗ Connection error: {e}")
        print(f"   Check if {WEBADMIN_SERVER} is reachable")
        return None
    except requests.exceptions.RequestException as e:
        print(f"✗ Error requesting token: {e}")
        return None

def list_tasks(access_token):
    """List all tasks using the access token"""
    url = f"{BASE_URL}/tasks"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    try:
        print(f"DEBUG: GET request to {url}")
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        print(f"DEBUG: Response status: {response.status_code}")
        response.raise_for_status()
        tasks = response.json()
        return tasks
    except requests.exceptions.Timeout:
        print(f"✗ Error: Request timed out after 10 seconds")
        return None
    except requests.exceptions.RequestException as e:
        print(f"✗ Error listing tasks: {e}")
        return None

def main():
    print("Requesting access token...")
    token = get_access_token()

    if token:
        print(f"✓ Token received: {token[:20]}...")
        print(f"✓ Token expires in 900 seconds\n")

        print("Fetching tasks list...")
        tasks = list_tasks(token)

        if tasks:
            print(f"✓ Retrieved {len(tasks)} tasks:\n")
            print(json.dumps(tasks, indent=2))
        else:
            print("✗ Failed to retrieve tasks")
    else:
        print("✗ Failed to get access token")

if __name__ == "__main__":
    main()
