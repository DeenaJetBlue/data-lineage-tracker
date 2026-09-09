import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(ENV_PATH)

# HVR Configuration from .env
HVR_URL = os.getenv("HVR_URL")
HVR_API_VERSION = os.getenv("HVR_API_VERSION", "v6.1.0.6")
HVR_HUB_NAME = os.getenv("HVR_HUB_NAME", "hvrhub")
HVR_USERNAME = os.getenv("HVR_USERNAME")
HVR_PASSWORD = os.getenv("HVR_PASSWORD")

# User Credentials
USER_CREDENTIALS = {
    "username": HVR_USERNAME,
    "password": HVR_PASSWORD,
}

# Define session to persist connection settings
session = requests.Session()

if not HVR_URL or not HVR_USERNAME or not HVR_PASSWORD:
    print("Error: HVR credentials not found in .env file!")
    exit(1)


def get_access_token():
    auth_url = f"{HVR_URL}/auth/v1/password"
    headers = {"Content-Type": "application/json"}

    try:
        response = session.post(
            auth_url, headers=headers, json=USER_CREDENTIALS, timeout=15
        )

        if response.status_code == 200:
            auth_data = response.json()
            return auth_data.get("access_token")
        else:
            print(f"Error: Authentication Failed ({response.status_code})")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


def fetch_hub_jobs(token):
    jobs_url = f"{HVR_URL}/api/{HVR_API_VERSION}/hubs/{HVR_HUB_NAME}/jobs"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    query_params = {
        "fetch": "latency",
    }

    try:
        response = session.get(
            jobs_url, headers=headers, params=query_params, timeout=30
        )

        if response.status_code == 200:
            jobs_data = response.json()

            if isinstance(jobs_data, list):
                jobs = jobs_data
            elif isinstance(jobs_data, dict) and "jobs" in jobs_data:
                jobs = jobs_data.get("jobs", [])
            elif isinstance(jobs_data, dict):
                jobs = [{"name": name, **details} for name, details in jobs_data.items()]
            else:
                jobs = []

            running_jobs = [job for job in jobs if isinstance(job, dict) and job.get("state") == "RUNNING"]

            print(f"Total Jobs: {len(jobs)}")
            print(f"Running Jobs: {len(running_jobs)}\n")

            for job in running_jobs:
                print(f"Job Name: {job.get('name', 'N/A')}")
                for key, value in job.items():
                    if key != 'name':
                        print(f"  {key}: {value}")
                print()

            return running_jobs

        else:
            print(f"Error: Request failed ({response.status_code})")
            return []

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return []


if __name__ == "__main__":
    access_token = get_access_token()

    if not access_token:
        print("Error: Failed to obtain access token")
        exit(1)

    fetch_hub_jobs(access_token)
