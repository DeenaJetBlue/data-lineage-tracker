import json
import requests
from pathlib import Path
import urllib3
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from requests.packages.urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT for compatibility
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

def get_session():
    """Create requests session with custom SSL handling and retries"""
    session = requests.Session()

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )

    adapter = SSLAdapter(max_retries=retry_strategy)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session

def read_env():
    """Read .env file to get configuration"""
    env_vars = {}
    env_path = Path(".env")
    if not env_path.exists():
        raise FileNotFoundError(".env file not found")

    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

def read_config():
    """Read TaskID from .config file"""
    config_file = ".config"
    if not Path(config_file).exists():
        raise FileNotFoundError(f"{config_file} file not found")

    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() == 'TaskID':
                        task_id = value.strip()
                        print(f"✓ TaskID loaded from config: {task_id}")
                        return task_id

    raise ValueError("TaskID not found in .config file")

env_vars = read_env()
WEBADMIN_SERVER = env_vars.get("WEBADMIN_SERVER")
USERNAME = env_vars.get("USERNAME")
PASSWORD = env_vars.get("PASSWORD")

if not all([WEBADMIN_SERVER, USERNAME, PASSWORD]):
    raise ValueError("Missing MOVEit credentials (WEBADMIN_SERVER, USERNAME, PASSWORD) in .env file")


def get_access_token():
    """Generate access token using credentials"""
    server = WEBADMIN_SERVER.strip().rstrip('/')
    if not server.startswith(('http://', 'https://')):
        server = f"https://{server}"

    token_url = f"{server}/api/v1/token"
    server_host = server.split('://', 1)[-1]

    request_data = {
        "grant_type": "password",
        "server_host": server_host,
        "username": USERNAME,
        "password": PASSWORD
    }

    try:
        session = get_session()
        response = session.post(
            token_url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data=request_data,
            timeout=60,
            allow_redirects=True
        )

        if response.status_code == 200:
            token = response.json().get('access_token')
            print(f"✓ Access token generated successfully")
            return token
        else:
            print(f"✗ Failed to get access token: {response.status_code}")
            return None

    except Exception as e:
        print(f"✗ Error generating access token: {str(e)}")
        return None


def get_task_details(task_id):
    """Get details for a MOVEit task"""
    server = WEBADMIN_SERVER.strip().rstrip('/')
    if not server.startswith(('http://', 'https://')):
        server = f"https://{server}"

    access_token = get_access_token()
    if not access_token:
        print("✗ Could not authenticate")
        return None

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    url = f"{server}/api/v1/tasks/{task_id}/log"
    params = {
        "page": 1,
        "perPage": 50
    }

    try:
        session = get_session()
        response = session.get(
            url,
            headers=headers,
            params=params,
            timeout=60,
            allow_redirects=True
        )

        if response.status_code == 200:
            data = response.json()
            items = data.get("items", []) if isinstance(data, dict) else []
            if items:
                latest = max(items, key=lambda item: item.get("startTime", ""))
                print(f"✓ Retrieved task details successfully")
                return latest
            else:
                print(f"⚠ No task runs found")
                return data
        else:
            print(f"✗ Failed to get task details: {response.status_code}")
            return None

    except Exception as e:
        print(f"✗ Error retrieving task details: {str(e)}")
        return None


def main():
    try:
        print(f"Connected to MOVEit WebAdmin Server: {WEBADMIN_SERVER}\n")

        task_id = read_config()
        print(f"Fetching task details for Task ID: {task_id}\n")

        task_details = get_task_details(task_id)

        if not task_details:
            print("✗ Could not retrieve task details")
            return

        print("\n📋 TASK DETAILS:")
        print(json.dumps(task_details, indent=2))

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
