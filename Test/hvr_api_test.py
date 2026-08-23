import json
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

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

print("=" * 80)
print("HVR API - Fetch Jobs and Display Status")
print("=" * 80)

if not HVR_URL or not HVR_USERNAME or not HVR_PASSWORD:
    print("❌ HVR credentials not found in .env file!")
    print("Required: HVR_URL, HVR_USERNAME, HVR_PASSWORD, HVR_HUB_NAME")
    exit(1)

print(f"\n📌 HVR Server: {HVR_URL}")
print(f"📌 Hub Name: {HVR_HUB_NAME}")
print(f"📌 API Version: {HVR_API_VERSION}")
print(f"📌 Username: {HVR_USERNAME}")


def get_access_token():
    """Authenticates credentials against the HVR token service."""
    auth_url = f"{HVR_URL}/auth/v1/password"
    headers = {"Content-Type": "application/json"}

    print("\n[1] Authenticating with HVR Hub Server...")
    print("-" * 80)
    print(f"🔑 Auth URL: {auth_url}")

    try:
        response = session.post(
            auth_url, headers=headers, json=USER_CREDENTIALS, timeout=15
        )

        if response.status_code == 200:
            auth_data = response.json()
            token = auth_data.get("access_token")
            print(f"✓ Authentication successful!")
            print(f"✓ Access Token: {token[:20]}..." if token else "No token received")
            return token
        else:
            print(f"❌ Authentication Failed ({response.status_code})")
            print(f"Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        print("⚠️  Make sure you have VDI connection to the HVR server")
        return None


def fetch_hub_jobs(token):
    """Retrieves jobs metadata using the authenticated bearer token."""
    jobs_url = f"{HVR_URL}/api/{HVR_API_VERSION}/hubs/{HVR_HUB_NAME}/jobs"

    # Inject the retrieved token into headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    # Optional query parameters
    query_params = {
        "fetch": "latency",
    }

    print("\n[2] Fetching all HVR jobs...")
    print("-" * 80)
    print(f"📡 Jobs URL: {jobs_url}")

    try:
        response = session.get(
            jobs_url, headers=headers, params=query_params, timeout=30
        )

        if response.status_code == 200:
            jobs_data = response.json()
            jobs = jobs_data.get("jobs", []) if isinstance(jobs_data, dict) else jobs_data

            if not jobs:
                print("❌ No jobs found!")
                return None

            print(f"✓ Found {len(jobs)} job(s)\n")

            print("Available Jobs:")
            print("-" * 80)
            for i, job in enumerate(jobs[:10], 1):
                job_name = job.get("name", "N/A")
                job_state = job.get("state", "unknown")
                print(f"{i}. Name: {job_name}")
                print(f"   State: {job_state}")
                if "latency" in job:
                    print(f"   Latency: {job.get('latency')}")
                print()

            return jobs

        elif response.status_code == 404:
            print(f"❌ Error: Hub '{HVR_HUB_NAME}' could not be found.")
            return None
        else:
            print(f"❌ Request failed ({response.status_code}): {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching jobs: {e}")
        return None


def fetch_job_details(token, job_name):
    """Fetch detailed status for a specific job."""
    detail_url = f"{HVR_URL}/api/{HVR_API_VERSION}/hubs/{HVR_HUB_NAME}/jobs/{job_name}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    print(f"\n[3] Fetching detailed status for job '{job_name}'...")
    print("-" * 80)
    print(f"📌 Detail URL: {detail_url}")

    try:
        response = session.get(detail_url, headers=headers, timeout=30)

        if response.status_code == 200:
            job_details = response.json()
            print("\n✓ Job Details Retrieved:")
            print("-" * 80)
            print(json.dumps(job_details, indent=2))

            # Extract key information
            print("\n📊 Job Status Summary:")
            print("-" * 80)

            # Display key fields
            key_fields = {
                "Name": job_details.get("name"),
                "State": job_details.get("state"),
                "Status": job_details.get("status"),
                "Enabled": job_details.get("enabled"),
                "Description": job_details.get("description"),
                "Latency": job_details.get("latency"),
                "Last Error": job_details.get("last_error"),
                "Created": job_details.get("created"),
                "Modified": job_details.get("modified"),
            }

            for field_name, value in key_fields.items():
                if value is not None:
                    print(f"{field_name}: {value}")

            return job_details

        else:
            print(f"❌ Request failed ({response.status_code}): {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching job details: {e}")
        return None


# --- Execution Flow ---
if __name__ == "__main__":
    # Step 1: Get access token
    access_token = get_access_token()

    if not access_token:
        print("\n❌ Failed to obtain access token. Exiting.")
        exit(1)

    # Step 2: Fetch all jobs
    jobs = fetch_hub_jobs(access_token)

    if jobs and len(jobs) > 0:
        # Step 3: Pick first job and fetch its details
        first_job = jobs[0]
        job_name = first_job.get("name")

        if job_name:
            job_details = fetch_job_details(access_token, job_name)
        else:
            print("❌ Could not extract job name")

print("\n" + "=" * 80)
print("✓ HVR API Test Complete")
print("=" * 80)
