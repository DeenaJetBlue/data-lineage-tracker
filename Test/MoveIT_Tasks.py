import os
import sys
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

env_path = Path(".env")
if not env_path.exists():
    print("Error: .env not found!")
    sys.exit(1)

def read_env():
    """Read .env file manually to preserve backslashes in usernames"""
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

env_vars = read_env()
WEBADMIN_SERVER = env_vars.get("WEBADMIN_SERVER")
USERNAME = env_vars.get("USERNAME")
PASSWORD = env_vars.get("PASSWORD")

if not all([WEBADMIN_SERVER, USERNAME, PASSWORD]):
    print("Error: MOVEit credentials not configured in .env")
    print("Required: WEBADMIN_SERVER, USERNAME, PASSWORD")
    sys.exit(1)

CONFIG_FILE = ".config"
REQUEST_ATTEMPTS = 3
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
    server_host = server.split('://', 1)[-1]

    print(f"DEBUG: Connecting to: {token_url}")
    print(f"DEBUG: Username: {USERNAME}")
    print(f"DEBUG: Username length: {len(USERNAME)}")

    request_data = {
        "grant_type": "password",
        "server_host": server_host,
        "username": USERNAME,
        "password": PASSWORD
    }

    try:
        for attempt in range(1, REQUEST_ATTEMPTS + 1):
            try:
                response = requests.post(
                    token_url,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    data=request_data,
                    verify=False,
                    timeout=60,
                    allow_redirects=True
                )
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                if attempt == REQUEST_ATTEMPTS:
                    raise
                print(f"DEBUG: Token request failed ({attempt}/{REQUEST_ATTEMPTS}); retrying...")
                time.sleep(attempt)

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
        if "10013" in str(e):
            print("Connection Error: Windows denied the outbound socket")
            print("Details: A local firewall, VPN policy, or endpoint security rule blocked the connection")
            print("Action: Reconnect to the VPN or ask IT to allow Python/python.exe to reach 10.204.124.216:443")
            return None
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

    # Get the latest task log entry
    url = f"{server}/api/v1/tasks/{task_id}/log"
    params = {
        "page": 1,
        "perPage": 50
    }

    print(f"DEBUG: Fetching latest task log from: {url}")

    try:
        for attempt in range(1, REQUEST_ATTEMPTS + 1):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    verify=False,
                    timeout=60,
                    allow_redirects=True
                )
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                if attempt == REQUEST_ATTEMPTS:
                    raise
                print(f"DEBUG: Task log request failed ({attempt}/{REQUEST_ATTEMPTS}); retrying...")
                time.sleep(attempt)

        print(f"DEBUG: Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"DEBUG: Task log data received: {json.dumps(data)}...")
            items = data.get("items", []) if isinstance(data, dict) else []
            if items:
                latest = max(items, key=lambda item: item.get("startTime", ""))
                data["items"] = [latest]
            return data
        else:
            print(f"Error: Failed to get task runs (Status: {response.status_code})")
            print(f"Response: {response.text[:200]}")
            return None

    except requests.exceptions.ConnectionError as e:
        if "10013" in str(e):
            print("Connection Error: Windows denied the outbound socket")
            print("Details: A local firewall, VPN policy, or endpoint security rule blocked the connection")
            print("Action: Reconnect to the VPN or ask IT to allow Python/python.exe to reach 10.204.124.216:443")
            return None
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
