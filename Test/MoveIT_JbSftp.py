import json
import subprocess
from pathlib import Path
from urllib.parse import urlencode


# Python requests gets its connection reset by jbsftp on AVD; Windows curl.exe works.
def curl(method, url, headers=None, data=None):
    """Run curl.exe and return (status_code, body)"""
    command = ["curl.exe", "--silent", "--show-error", "--insecure", "--max-time", "60",
               "--request", method, url, "--write-out", "\n%{http_code}"]
    for name, value in (headers or {}).items():
        command += ["--header", f"{name}: {value}"]
    for name, value in (data or {}).items():
        command += ["--data-urlencode", f"{name}={value}"]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise Exception(result.stderr.strip())

    body, _, status = result.stdout.rpartition("\n")
    return int(status), body


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
    """Read JbSftp root folder from .config file"""
    config_file = ".config"
    if not Path(config_file).exists():
        raise FileNotFoundError(f"{config_file} file not found")

    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() == 'JbSftp_Root_Folder':
                        folder = value.strip()
                        print(f"✓ Root folder loaded from config: {folder}")
                        return folder

    raise ValueError("JbSftp_Root_Folder not found in .config file")


env_vars = read_env()
TRANSFER_SERVER = env_vars.get("TRANSFER_SERVER")
TUSERNAME = env_vars.get("TUSERNAME")
TPASSWORD = env_vars.get("TPASSWORD")

if not all([TRANSFER_SERVER, TUSERNAME, TPASSWORD]):
    raise ValueError("Missing MOVEit credentials (TRANSFER_SERVER, TUSERNAME, TPASSWORD) in .env file")


def get_access_token():
    """Generate access token using credentials"""
    server = TRANSFER_SERVER.strip().rstrip('/')
    if not server.startswith(('http://', 'https://')):
        server = f"https://{server}"

    token_url = f"{server}/api/v1/token"
    request_data = {
        "grant_type": "password",
        "username": TUSERNAME,
        "password": TPASSWORD
    }

    try:
        status, body = curl("POST", token_url, data=request_data)

        if status == 200:
            print(f"✓ Access token generated successfully")
            return json.loads(body).get('access_token')
        else:
            print(f"✗ Failed to get access token: {status}")
            print(f"  Response: {body}")
            return None

    except Exception as e:
        print(f"✗ Error generating access token: {str(e)}")
        return None


def get_files_in_folder(access_token, folder_path):
    """Get files in a folder, sorted by most recent upload first"""
    server = TRANSFER_SERVER.strip().rstrip('/')
    if not server.startswith(('http://', 'https://')):
        server = f"https://{server}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    params = {
        "page": 1,
        "perPage": 100,
        "sortField": "uploadstamp",
        "sortDirection": "desc",
        "folderPath": folder_path
    }

    try:
        status, body = curl("GET", f"{server}/api/v1/files?{urlencode(params)}", headers=headers)

        if status == 200:
            print(f"✓ Retrieved files from {folder_path} successfully")
            return json.loads(body)
        else:
            print(f"✗ Failed to retrieve files: {status}")
            print(f"  Response: {body}")
            return None

    except Exception as e:
        print(f"✗ Error retrieving files: {str(e)}")
        return None


def format_size(size: int) -> str:
    """Format file size in human-readable format"""
    if size >= 1024 ** 3:
        return f"{size / (1024 ** 3):.2f} GB"
    elif size >= 1024 ** 2:
        return f"{size / (1024 ** 2):.2f} MB"
    elif size >= 1024:
        return f"{size / 1024:.2f} KB"
    return f"{size} B"


def main():
    try:
        print(f"Connected to MOVEit Transfer Server: {TRANSFER_SERVER}\n")

        root_folder = read_config()

        access_token = get_access_token()
        if not access_token:
            print("✗ Could not authenticate")
            return

        files_data = get_files_in_folder(access_token, root_folder)
        if not files_data:
            print("✗ Could not retrieve files")
            return

        files_list = files_data.get('items', [])
        total_count = files_data.get('totalCount', len(files_list))
        print(f"\n📊 Total files in folder: {total_count}")

        if not files_list:
            print("⚠ No files found in folder")
            return

        latest = files_list[0]
        print("\n📄 Most Recent File Details:")
        print(f"  Name: {latest.get('name', 'N/A')}")
        print(f"  Size: {format_size(latest.get('size', 0))}")
        print(f"  Upload Time: {latest.get('uploadstamp', 'N/A')}")
        print(f"  Modified Time: {latest.get('modificationtime', 'N/A')}")
        print(f"  ID: {latest.get('id', 'N/A')}")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
