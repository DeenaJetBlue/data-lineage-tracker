import aiohttp
from datetime import datetime
from typing import Optional, List
import json
from app.models import MOVEitNode, MOVEitLogEntry
from app.config import settings


class MOVEitService:
    def __init__(self):
        self.webadmin_server = settings.webadmin_server
        self.username = settings.username
        self.password = settings.password
        self.base_url = f"https://{self.webadmin_server}/api/v1"

    async def get_access_token(self) -> Optional[str]:
        """Request an access token from MOVEit Automation API"""
        url = f"{self.base_url}/token"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "password",
            "server_host": self.webadmin_server,
            "username": self.username,
            "password": self.password
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    data=data,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        return token_data.get("access_token")
                    else:
                        print(f"Error getting token: {response.status}")
                        return None

        except Exception as e:
            print(f"Error requesting token: {str(e)}")
            return None

    async def get_task_details(self, task_id: str, token: str) -> Optional[dict]:
        """Get details for a specific task"""
        url = f"{self.base_url}/tasks/{task_id}"
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"Error getting task details: {response.status}")
                        return None

        except Exception as e:
            print(f"Error fetching task details: {str(e)}")
            return None

    async def get_task_logs(self, task_id: str, token: str, page: int = 1, per_page: int = 50) -> Optional[dict]:
        """Get logs for a specific task"""
        url = f"{self.base_url}/tasks/{task_id}/log"
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        params = {
            "page": page,
            "perPage": per_page
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        print(f"Task {task_id} not found")
                        return None
                    else:
                        print(f"Error getting task logs: {response.status}")
                        return None

        except Exception as e:
            print(f"Error fetching task logs: {str(e)}")
            return None

    async def get_task_by_id(self, task_id: str) -> MOVEitNode:
        """Get complete task information with logs by task ID"""
        print(f"\n[MOVEit Service] Fetching task {task_id}...")

        try:
            # Get access token
            print(f"[MOVEit Service] Authenticating...")
            token = await self.get_access_token()

            if not token:
                print(f"[MOVEit Service] ❌ Failed to authenticate")
                return MOVEitNode(
                    name=task_id,
                    task_id=task_id,
                    task_name=task_id,
                    status="authentication_failed",
                    error="Could not authenticate with MOVEit"
                )

            # Get task details
            print(f"[MOVEit Service] Fetching task details...")
            task_details = await self.get_task_details(task_id, token)

            if not task_details:
                print(f"[MOVEit Service] ❌ Task not found")
                return MOVEitNode(
                    name=task_id,
                    task_id=task_id,
                    task_name=task_id,
                    status="not_found",
                    error=f"Task {task_id} not found"
                )

            # Get task logs
            print(f"[MOVEit Service] Fetching task logs...")
            logs_data = await self.get_task_logs(task_id, token, page=1, per_page=50)

            # Parse logs
            log_entries = []
            total_logs = 0

            if logs_data:
                if isinstance(logs_data, dict):
                    logs_list = logs_data.get("logs", []) or logs_data.get("items", [])
                    total_logs = logs_data.get("totalCount", len(logs_list))
                else:
                    logs_list = logs_data if isinstance(logs_data, list) else []
                    total_logs = len(logs_list)

                for log in logs_list[:20]:  # Get first 20 logs
                    entry = MOVEitLogEntry(
                        timestamp=self._parse_datetime(log.get("timestamp")),
                        level=log.get("level"),
                        message=log.get("message"),
                        details=log.get("details")
                    )
                    log_entries.append(entry)

            # Extract task info
            task_name = task_details.get("name", task_id)
            task_status = task_details.get("status", "unknown")
            created = self._parse_datetime(task_details.get("created"))
            modified = self._parse_datetime(task_details.get("modified"))

            print(f"[MOVEit Service] ✓ Task retrieved successfully")
            print(f"[MOVEit Service]    - Name: {task_name}")
            print(f"[MOVEit Service]    - Status: {task_status}")
            print(f"[MOVEit Service]    - Logs: {len(log_entries)} (Total: {total_logs})")

            return MOVEitNode(
                name=task_name,
                task_id=task_id,
                task_name=task_name,
                status=task_status,
                created=created,
                modified=modified,
                logs=log_entries,
                total_logs=total_logs
            )

        except Exception as e:
            print(f"[MOVEit Service] ❌ Error: {str(e)}")
            return MOVEitNode(
                name=task_id,
                task_id=task_id,
                task_name=task_id,
                status="error",
                error=str(e)
            )

    @staticmethod
    def _parse_datetime(date_string: Optional[str]) -> Optional[datetime]:
        """Parse ISO format datetime string"""
        if not date_string:
            return None
        try:
            return datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        except:
            return None
