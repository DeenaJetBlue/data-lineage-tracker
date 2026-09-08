import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

env_path = Path(".env")
if not env_path.exists():
    print("Error: .env not found!")
    sys.exit(1)

load_dotenv(env_path)

WEBADMIN_SERVER = os.getenv("WEBADMIN_SERVER")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

if not all([WEBADMIN_SERVER, USERNAME, PASSWORD]):
    print("Error: MOVEit credentials not configured in .env")
    print("Required: WEBADMIN_SERVER, USERNAME, PASSWORD")
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

    return {'task_id': config.get('TaskID')}


def get_access_token():
    """Get access token from MOVEit Transfer API"""
    server = WEBADMIN_SERVER.strip().rstrip('/')
    if not server.startswith(('http://', 'https://')):
        server = f"https://{server}"

    token_url = f"{server}/api/v1/token"

    print(f"DEBUG: Connecting to: {token_url}")
    print(f"DEBUG: Username: {USERNAME}")

    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "password",
                "username": USERNAME,
                "password": PASSWORD
            },
            verify=False,
            timeout=60,
            allow_redirects=True
        )

        print(f"DEBUG: Response Status: {response.status_code}")

        if response.status_code == 200:
            token = response.json().get('access_token')
            print(f"DEBUG: Got access token: {token[:20] if token else 'None'}...")
            return token
        else:
            print(f"Error: Failed to get access token (Status: {response.status_code})")
            print(f"Response: {response.text[:200]}")
            return None

    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: Could not connect to {server}")
        print(f"Details: {str(e)}")
        print(f"Possible causes: VPN not connected, firewall blocking, server unreachable")
        return None
    except requests.exceptions.Timeout as e:
        print(f"Timeout Error: Server took too long to respond")
        print(f"Details: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
        return None


def get_task_runs(task_id):
    """Get latest runs for a MOVEit task"""
    server = WEBADMIN_SERVER.strip().rstrip('/')
    if not server.startswith(('http://', 'https://')):
        server = f"https://{server}"

    print(f"DEBUG: Authenticating...")
    access_token = get_access_token()
    if not access_token:
        print("Error: Could not authenticate")
        return None

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Get task run history
    url = f"{server}/api/v1/tasks/{task_id}/history"
    params = {"limit": 1}

    print(f"DEBUG: Fetching task history from: {url}")

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            verify=False,
            timeout=60,
            allow_redirects=True
        )

        print(f"DEBUG: Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Error: Failed to get task runs (Status: {response.status_code})")
            print(f"Response: {response.text[:200]}")
            return None

    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: Could not connect to MOVEit server")
        print(f"Details: {str(e)}")
        print(f"Possible causes: VPN not connected, firewall blocking, server unreachable")
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None


def main():
    config = read_config()

    if not config['task_id']:
        print("Error: MoveIT_TaskID not configured in .config")
        sys.exit(1)

    task_id = config['task_id']

    print("MOVEit Task Configuration:")
    print(json.dumps(config, indent=2))

    print(f"\nFetching latest run for task {task_id}...")

    task_runs = get_task_runs(task_id)

    if not task_runs:
        print("Error: Could not retrieve task runs")
        sys.exit(1)

    print("\n=== LATEST TASK RUN DETAILS ===")
    print(json.dumps(task_runs, indent=2))


if __name__ == "__main__":
    main()
