import aiohttp
from datetime import datetime
from typing import Optional
from app.models import DBTNode
from app.config import settings


class DBTService:
    def __init__(self):
        self.dbt_secret = settings.dbt_secret
        self.dbt_environment_id = settings.dbt_environment_id
        self.dbt_access_url = settings.dbt_access_url
        # Extract host from URL (e.g., "https://mt384.us1.dbt.com/" -> "mt384.us1.dbt.com")
        self.dbt_host = self.dbt_access_url.replace("https://", "").replace("http://", "").rstrip("/")

    async def get_job_runs(self, account_id: str, job_id: str) -> list:
        """Get list of runs for a specific job"""
        job_id_str = str(job_id)

        try:
            url = f"https://{self.dbt_host}/api/v2/accounts/{account_id}/runs/"
            params = {
                "job_definition_id": job_id_str,
                "limit": 5,
                "offset": 0,
                "order_by": "-created_at"
            }

            headers = {
                "Authorization": f"Bearer {self.dbt_secret}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("data", [])
                    else:
                        return []

        except Exception as e:
            print(f"Error fetching runs: {str(e)}")
            return []

    async def get_run_details(self, account_id: str, run_id: str) -> dict:
        """Get detailed information about a specific run"""
        try:
            url = f"https://{self.dbt_host}/api/v2/accounts/{account_id}/runs/{run_id}/"
            params = {
                "include_related": "job,trigger,run_steps"
            }

            headers = {
                "Authorization": f"Bearer {self.dbt_secret}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("data", {})
                    else:
                        return {}

        except Exception as e:
            print(f"Error fetching run details: {str(e)}")
            return {}

    async def get_latest_job_run(self, account_id: str, job_id: str) -> DBTNode:
        """Get latest job run details using the Runs API"""
        job_id_str = str(job_id)

        print(f"\n[DBT Service] Fetching latest run for Job {job_id_str}...")

        try:
            # Step 1: Get list of runs for this job
            print(f"[DBT Service] Step 1: Fetching runs from /api/v2/accounts/{account_id}/runs/?job_definition_id={job_id_str}")
            runs = await self.get_job_runs(account_id, job_id_str)

            if not runs:
                print(f"[DBT Service] ❌ No runs found for job {job_id_str}")
                return DBTNode(
                    name=f"Job {job_id_str}",
                    job_name=f"Job {job_id_str}",
                    job_id=job_id_str,
                    status="no_runs",
                    error="No runs found for this job"
                )

            # Step 2: Get details of the latest run
            print(f"[DBT Service] ✅ Found {len(runs)} run(s)")
            latest_run = runs[0]
            run_id = latest_run.get("id")
            print(f"[DBT Service] Latest run ID: {run_id}")

            if not run_id:
                print(f"[DBT Service] ❌ Could not extract run ID")
                return DBTNode(
                    name=f"Job {job_id_str}",
                    job_name=f"Job {job_id_str}",
                    job_id=job_id_str,
                    status="no_runs",
                    error="Could not extract run ID"
                )

            print(f"[DBT Service] Step 2: Fetching run details from /api/v2/accounts/{account_id}/runs/{run_id}/")
            run_details = await self.get_run_details(account_id, str(run_id))

            if not run_details:
                print(f"[DBT Service] ❌ Could not fetch run details")
                return DBTNode(
                    name=f"Job {job_id_str}",
                    job_name=f"Job {job_id_str}",
                    job_id=job_id_str,
                    status="unknown",
                    error="Could not fetch run details"
                )

            print(f"[DBT Service] ✅ Run details retrieved")

            # Extract run information
            run_status = run_details.get("status", 0)
            status_humanized = run_details.get("status_humanized", "unknown").lower()

            # Map DBT status codes to human-readable format
            status_map = {
                1: "queued",
                2: "starting",
                3: "running",
                10: "success",
                20: "error",
                30: "cancelled"
            }
            status = status_map.get(run_status, status_humanized)

            # Extract job name from run details
            job_info = run_details.get("job", {})
            job_name = job_info.get("name", f"Job {job_id_str}")

            # Parse timestamps
            last_run_time = None
            started_at = run_details.get("started_at")
            if started_at:
                try:
                    last_run_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                except:
                    last_run_time = None

            print(f"[DBT Service] 📊 Run Summary:")
            print(f"[DBT Service]    - Job Name: {job_name}")
            print(f"[DBT Service]    - Run Status: {status}")
            print(f"[DBT Service]    - Run ID: {run_id}")
            print(f"[DBT Service]    - Started At: {started_at}")

            return DBTNode(
                name=job_name,
                job_name=job_name,
                job_id=job_id_str,
                status=status,
                last_run=last_run_time,
                run_id=str(run_id),
                job_status=status
            )

        except Exception as e:
            print(f"[DBT Service] ❌ Error: {str(e)}")
            return DBTNode(
                name=f"Job {job_id_str}",
                job_name=f"Job {job_id_str}",
                job_id=job_id_str,
                status="error",
                error=str(e)
            )
