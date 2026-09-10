import os
import json
import subprocess
import sys
from urllib.parse import urlencode
from typing import Optional, Dict, Any
import urllib3
from pathlib import Path

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CurlResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self) -> Dict[str, Any]:
        return json.loads(self.text)


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


def read_config(config_file: str = ".config") -> str:
    """Read root folder from .config file"""
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

    print("⚠ Warning: Could not find JbSftp_Root_Folder in .config file, using default")
    return "/Home/Qualtrics/QualtricsSend/"


class MOVEitTransferAPI:
    def __init__(self):
        env_vars = read_env()
        self.server = env_vars.get('TRANSFER_SERVER')
        self.username = env_vars.get('TUSERNAME')
        self.password = env_vars.get('TPASSWORD')
        self.access_token = None
        self.root_folder = read_config()

        if not all([self.server, self.username, self.password]):
            raise ValueError("Missing MOVEit credentials (TRANSFER_SERVER, TUSERNAME, TPASSWORD) in .env file")

        self.server = self.server.strip().rstrip('/')
        if not self.server.startswith(('http://', 'https://')):
            self.server = f"https://{self.server}"
        self.base_url = f"{self.server}/api/v1"

    @staticmethod
    def _request(method: str, url: str, headers: Optional[Dict[str, str]] = None,
                 data: Optional[Dict[str, Any]] = None,
                 params: Optional[Dict[str, Any]] = None) -> CurlResponse:
        if params:
            url = f"{url}?{urlencode(params)}"

        command = [
            "curl.exe", "--silent", "--show-error", "--insecure",
            "--request", method, url,
            "--write-out", "\n__HTTP_STATUS__:%{http_code}"
        ]
        for name, value in (headers or {}).items():
            command.extend(["--header", f"{name}: {value}"])
        for name, value in (data or {}).items():
            command.extend(["--data-urlencode", f"{name}={value}"])

        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode:
            raise Exception(result.stderr.strip())

        body, marker, status = result.stdout.rpartition("\n__HTTP_STATUS__:")
        if not marker:
            raise Exception("curl returned no HTTP status")
        return CurlResponse(int(status), body)

    def get_access_token(self) -> bool:
        """Generate access token using credentials"""
        try:
            token_url = f"{self.base_url}/token"
            payload = {
                "grant_type": "password",
                "username": self.username,
                "password": self.password
            }

            response = self._request("POST", token_url, data=payload)

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                print(f"✓ Access token generated successfully")
                return True
            else:
                print(f"✗ Failed to get access token: {response.status_code}")
                print(f"  Response: {response.text}")
                return False

        except Exception as e:
            print(f"✗ Error generating access token: {str(e)}")
            return False

    def get_files_in_folder(self, folder_path: str = None, page: int = 1, per_page: int = 100) -> Optional[Dict[str, Any]]:
        """Get list of files in specific folder"""
        if not self.access_token:
            print("✗ Not authenticated. Ensure MOVEIT_ACCESS_TOKEN is set in .env")
            return None

        folder = folder_path or self.root_folder
        try:
            files_url = f"{self.base_url}/files"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            params = {
                "page": page,
                "perPage": per_page,
                "sortField": "uploadstamp",
                "sortDirection": "desc",
                "folderPath": folder
            }

            response = self._request("GET", files_url, headers=headers, params=params)

            if response.status_code == 200:
                files_data = response.json()
                print(f"✓ Retrieved files from {folder} successfully")
                return files_data
            elif response.status_code == 403:
                print(f"✗ Forbidden: You don't have permission to access folder: {folder}")
                return None
            else:
                print(f"✗ Failed to retrieve files: {response.status_code}")
                print(f"  Response: {response.text}")
                return None

        except Exception as e:
            print(f"✗ Error retrieving files: {str(e)}")
            return None



def format_size(size: int) -> str:
    """Format file size in human-readable format"""
    if size >= 1024**3:
        return f"{size / (1024**3):.2f} GB"
    elif size >= 1024**2:
        return f"{size / (1024**2):.2f} MB"
    elif size >= 1024:
        return f"{size / 1024:.2f} KB"
    else:
        return f"{size} B"

def main():
    """Main function to get files from MOVEit root folder"""
    try:
        # Initialize API client
        api = MOVEitTransferAPI()
        print(f"Connected to MOVEit Transfer Server: {api.server}")
        print(f"Root Folder: {api.root_folder}\n")

        # Step 1: Generate access token
        print("Step 1: Generating access token...")
        if not api.get_access_token():
            print("Failed to generate token. Exiting.")
            return

        print()

        # Step 2: Get files from root folder
        print("Step 2: Retrieving files from root folder...")
        files_data = api.get_files_in_folder()
        if files_data:
            files_list = files_data.get('items', [])
            total_count = files_data.get('totalCount', len(files_list))

            print(f"\n📊 Total files in folder: {total_count}")
            print(f"Files retrieved: {len(files_list)}\n")

            # Display most recent file details
            if files_list:
                most_recent = files_list[0]
                print("📄 Most Recent File Details:")
                print(f"  Name: {most_recent.get('name', 'N/A')}")
                print(f"  Size: {format_size(most_recent.get('size', 0))}")
                print(f"  Upload Time: {most_recent.get('uploadstamp', 'N/A')}")
                print(f"  Modified Time: {most_recent.get('modificationtime', 'N/A')}")
                print(f"  ID: {most_recent.get('id', 'N/A')}")

            # Display file list table
            print(f"\n{'File Name':<50} {'Size':<15} {'Upload Timestamp':<25}")
            print("-" * 90)

            for file in files_list[:20]:
                name = file.get('name', 'N/A')[:50]
                size_str = format_size(file.get('size', 0))
                upload_stamp = file.get('uploadstamp', 'N/A')
                print(f"{name:<50} {size_str:<15} {str(upload_stamp):<25}")

            if len(files_list) > 20:
                print(f"\n... and {len(files_list) - 20} more files")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
