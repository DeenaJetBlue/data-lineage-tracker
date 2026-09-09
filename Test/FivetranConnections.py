import requests
import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from base64 import b64encode
from datetime import datetime, timedelta

load_dotenv()

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
    return config

config = read_config()
connection_id = config.get('ConnectionID')

if not connection_id:
    print("Error: ConnectionID not found in .config")
    sys.exit(1)

FIVETRAN_API_KEY = os.getenv("FIVETRAN_API_KEY")
FIVETRAN_API_SECRET = os.getenv("FIVETRAN_API_SECRET")

if not FIVETRAN_API_KEY or not FIVETRAN_API_SECRET:
    print("Error: Fivetran credentials not found in .env")
    exit()

auth_string = f"{FIVETRAN_API_KEY}:{FIVETRAN_API_SECRET}"
auth_b64 = b64encode(auth_string.encode("utf-8")).decode("utf-8")

headers = {
    "Accept": "application/json;version=2",
    "Authorization": f"Basic {auth_b64}"
}

now = datetime.utcnow()
three_hours_ago = now - timedelta(hours=3)

start_time = three_hours_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
end_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

url = f"https://api.fivetran.com/v1/connections/{connection_id}/sync-history"
params = {
    "start_time": start_time,
    "end_time": end_time,
    "limit": "100"
}

try:
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    data = response.json().get("data", {}).get("items", [])

    print(f"Sync History for {connection_id} (Last 3 hours):\n")
    print(f"Total syncs: {len(data)}\n")

    for sync in data:
        print(f"Sync ID: {sync.get('sync_id')}")
        print(f"  Status: {sync.get('status')}")
        print(f"  Started: {sync.get('start')}")
        print(f"  Completed: {sync.get('end')}")
        stages = sync.get('stages', {})
        print(f"  Stages:")
        print(f"    Extract Volume: {stages.get('extract', {}).get('volume')}")
        print(f"    Process Volume: {stages.get('process', {}).get('volume')}")
        print(f"    Load Volume: {stages.get('load', {}).get('volume')}")
        print()

except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
    if hasattr(e, 'response'):
        print(f"Response: {e.response.text}")
