import os
import requests
import json
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import urllib3

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

class MOVEitTransferAPI:
    def __init__(self):
        self.server = os.getenv('TRANSFER_SERVER')
        self.username = os.getenv('TUSERNAME')
        self.password = os.getenv('TPASSWORD')
        self.access_token = None
        self.refresh_token = None

        if not all([self.server, self.username, self.password]):
            raise ValueError("Missing MOVEit Transfer credentials in .env file")

        self.server = self.server.strip().rstrip('/')
        if not self.server.startswith(('http://', 'https://')):
            self.server = f"https://{self.server}"
        self.base_url = f"{self.server}/api/v1"

    def get_access_token(self) -> bool:
        """Request an access token from MOVEit Transfer API"""
        try:
            token_url = f"{self.base_url}/token"

            payload = {
                "grant_type": "password",
                "username": self.username,
                "password": self.password
            }

            response = requests.post(
                token_url,
                data=payload,
                verify=False,  # Ignore SSL certificate warnings
                timeout=10
            )

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                print(f"✓ Access token obtained successfully")
                print(f"  Token expires in: {token_data.get('expires_in')} seconds")
                return True
            else:
                print(f"✗ Failed to get access token: {response.status_code}")
                print(f"  Response: {response.text}")
                return False

        except Exception as e:
            print(f"✗ Error requesting access token: {str(e)}")
            return False

    def get_files(self, page: int = 1, per_page: int = 25,
                  sort_field: str = "path", sort_direction: str = "asc") -> Optional[Dict[str, Any]]:
        """Get list of files current user can view"""
        if not self.access_token:
            print("✗ Not authenticated. Call get_access_token() first.")
            return None

        try:
            files_url = f"{self.base_url}/files"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            params = {
                "page": page,
                "perPage": per_page,
                "sortField": sort_field,
                "sortDirection": sort_direction
            }

            response = requests.get(
                files_url,
                headers=headers,
                params=params,
                verify=False,
                timeout=10
            )

            if response.status_code == 200:
                files_data = response.json()
                print(f"✓ Retrieved files successfully")
                return files_data
            elif response.status_code == 403:
                print(f"✗ Forbidden: You don't have permission to access files")
                return None
            else:
                print(f"✗ Failed to retrieve files: {response.status_code}")
                print(f"  Response: {response.text}")
                return None

        except Exception as e:
            print(f"✗ Error retrieving files: {str(e)}")
            return None

    def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            print("✗ No refresh token available. Request a new access token.")
            return False

        try:
            token_url = f"{self.base_url}/token"

            payload = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }

            response = requests.post(
                token_url,
                data=payload,
                verify=False,
                timeout=10
            )

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                print(f"✓ Token refreshed successfully")
                return True
            else:
                print(f"✗ Failed to refresh token: {response.status_code}")
                return False

        except Exception as e:
            print(f"✗ Error refreshing token: {str(e)}")
            return False

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current authenticated user"""
        if not self.access_token:
            print("✗ Not authenticated. Call get_access_token() first.")
            return None

        try:
            user_url = f"{self.base_url}/users/self"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            response = requests.get(
                user_url,
                headers=headers,
                verify=False,
                timeout=10
            )

            if response.status_code == 200:
                user_data = response.json()
                print(f"✓ Retrieved user info successfully")
                return user_data
            else:
                print(f"✗ Failed to retrieve user info: {response.status_code}")
                print(f"  Response: {response.text}")
                return None

        except Exception as e:
            print(f"✗ Error retrieving user info: {str(e)}")
            return None


def main():
    """Example usage of MOVEit Transfer API"""
    try:
        # Initialize API client
        api = MOVEitTransferAPI()
        print(f"Connected to MOVEit Transfer Server: {api.server}\n")

        # Step 1: Get access token
        print("Step 1: Requesting access token...")
        if not api.get_access_token():
            print("Failed to authenticate. Exiting.")
            return

        print()

        # Step 2: Get user information
        print("Step 2: Retrieving user information...")
        user_info = api.get_user_info()
        if user_info:
            print(f"  User ID: {user_info.get('id')}")
            print(f"  User Name: {user_info.get('name')}")
            print(f"  User Directory: {user_info.get('directory')}")

        print()

        # Step 3: Get files
        print("Step 3: Retrieving files...")
        files_data = api.get_files(per_page=10)
        if files_data:
            # Pretty print the response
            print(json.dumps(files_data, indent=2))

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
