import requests
import os
import json
from dotenv import load_dotenv
from datetime import datetime
import urllib3

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# HVR Credentials
HVR_URL = os.getenv("HVR_URL")
HVR_USERNAME = os.getenv("HVR_USERNAME")
HVR_PASSWORD = os.getenv("HVR_PASSWORD")

print("=" * 80)
print("HVR API - Fetch Jobs and Display Status")
print("=" * 80)

if not HVR_URL or not HVR_USERNAME or not HVR_PASSWORD:
    print("❌ HVR credentials not found in .env file!")
    exit(1)

print(f"\n📌 HVR Server: {HVR_URL}")
print(f"📌 Username: {HVR_USERNAME}")

# Step 1: Authenticate and get session
print("\n[1] Authenticating to HVR API...")
print("-" * 80)

session = requests.Session()
session.verify = False  # Disable SSL verification for self-signed certs

auth = (HVR_USERNAME, HVR_PASSWORD)

# Build the API base URL
hvr_base_url = HVR_URL.rstrip('/') + '/hvr6/api'

try:
    # Test connection with a simple health check
    test_url = f"{hvr_base_url}/jobs"
    print(f"Connecting to: {test_url}")

    response = session.get(test_url, auth=auth, timeout=10)

    if response.status_code == 401:
        print("❌ Authentication failed! Invalid credentials.")
        print(f"Response: {response.text}")
        exit(1)
    elif response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        exit(1)

    print("✓ Authentication successful!")

except requests.exceptions.RequestException as e:
    print(f"❌ Connection error: {e}")
    print("⚠️  Make sure you have VDI connection to the HVR server")
    exit(1)

# Step 2: Fetch all jobs
print("\n[2] Fetching all HVR jobs...")
print("-" * 80)

try:
    response = session.get(test_url, auth=auth, timeout=15)
    response.raise_for_status()

    jobs_data = response.json()

    # Handle different response formats
    if isinstance(jobs_data, dict):
        jobs = jobs_data.get("jobs", []) or jobs_data.get("data", []) or [jobs_data]
    else:
        jobs = jobs_data if isinstance(jobs_data, list) else []

    if not jobs:
        print("❌ No jobs found!")
        print(f"Response: {json.dumps(jobs_data, indent=2)}")
    else:
        print(f"✓ Found {len(jobs)} job(s)\n")

        print("Available Jobs:")
        print("-" * 80)
        for i, job in enumerate(jobs[:10], 1):  # Show first 10
            job_id = job.get('id') or job.get('name') or job.get('job_id') or f"Job {i}"
            job_name = job.get('name') or job.get('job_name') or "N/A"
            job_status = job.get('status') or job.get('state') or "unknown"

            print(f"{i}. ID: {job_id}")
            print(f"   Name: {job_name}")
            print(f"   Status: {job_status}")
            if 'last_run' in job:
                print(f"   Last Run: {job.get('last_run')}")
            if 'created_at' in job:
                print(f"   Created: {job.get('created_at')}")
            print()

        # Step 3: Pick the first job and show its status
        selected_job = jobs[0]
        job_id = selected_job.get('id') or selected_job.get('name') or selected_job.get('job_id')

        if job_id:
            print("-" * 80)
            print(f"📌 Selected Job: {job_id}")
            print("-" * 80)

            # Fetch detailed job status
            print(f"\n[3] Fetching status for job '{job_id}'...")
            print("-" * 80)

            try:
                # Try different API endpoints for job details
                detail_url = f"{hvr_base_url}/jobs/{job_id}"
                print(f"Querying: {detail_url}")

                response = session.get(detail_url, auth=auth, timeout=15)

                if response.status_code == 200:
                    job_details = response.json()

                    print("\n✓ Job Details Retrieved:")
                    print("-" * 80)
                    print(json.dumps(job_details, indent=2, default=str))

                    # Extract key information
                    print("\n📊 Job Status Summary:")
                    print("-" * 80)

                    # Try common field names
                    fields = {
                        'name': ['name', 'job_name'],
                        'status': ['status', 'state', 'job_status'],
                        'last_run': ['last_run', 'lastRun', 'last_run_time'],
                        'last_result': ['last_result', 'lastResult', 'result'],
                        'enabled': ['enabled', 'is_enabled', 'active'],
                        'description': ['description', 'desc'],
                        'created': ['created', 'created_at', 'createdAt'],
                        'modified': ['modified', 'modified_at', 'modifiedAt'],
                    }

                    for field_name, possible_keys in fields.items():
                        for key in possible_keys:
                            if key in job_details:
                                value = job_details[key]
                                print(f"{field_name.replace('_', ' ').title()}: {value}")
                                break

                else:
                    print(f"❌ Could not fetch job details: {response.status_code}")
                    print(f"Response: {response.text}")

                    # Show what we have from the list
                    print("\n📊 Job Information (from list):")
                    print("-" * 80)
                    print(json.dumps(selected_job, indent=2, default=str))

            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching job details: {e}")
                print("\nShowing job info from list:")
                print(json.dumps(selected_job, indent=2, default=str))

        else:
            print("❌ Could not extract job ID")

except requests.exceptions.RequestException as e:
    print(f"❌ Error fetching jobs: {e}")
except json.JSONDecodeError as e:
    print(f"❌ Error parsing response: {e}")
    print(f"Raw response: {response.text}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

print("\n" + "=" * 80)
print("✓ HVR API Test Complete")
print("=" * 80)
