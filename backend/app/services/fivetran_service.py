import aiohttp
from datetime import datetime
from typing import Optional, List
from base64 import b64encode
from app.models import FivetranNode, FivetranSyncRecord
from app.config import settings


class FivetranService:
    def __init__(self):
        self.fivetran_api_key = settings.fivetran_api_key
        self.fivetran_api_secret = settings.fivetran_api_secret
        self.base_url = "https://api.fivetran.com/v1"

    def _get_auth_header(self) -> str:
        """Create Basic auth header from API key and secret"""
        if not self.fivetran_api_key or not self.fivetran_api_secret:
            raise ValueError("Fivetran API credentials not configured")

        auth_string = f"{self.fivetran_api_key}:{self.fivetran_api_secret}"
        auth_bytes = auth_string.encode("utf-8")
        auth_b64 = b64encode(auth_bytes).decode("utf-8")
        return f"Basic {auth_b64}"

    async def get_connections(self, limit: int = 100) -> List[dict]:
        """Get list of all Fivetran connections"""
        try:
            url = f"{self.base_url}/connections"
            headers = {
                "Accept": "application/json;version=2",
                "Authorization": self._get_auth_header()
            }
            params = {"limit": limit}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("data", {}).get("items", [])
                    else:
                        print(f"Error fetching connections: {response.status}")
                        return []

        except Exception as e:
            print(f"Error fetching connections: {str(e)}")
            return []

    async def get_sync_history(self, connection_id: str, limit: int = 20) -> List[dict]:
        """Get sync history for a specific connection"""
        try:
            url = f"{self.base_url}/connections/{connection_id}/sync-history"
            headers = {
                "Accept": "application/json;version=2",
                "Authorization": self._get_auth_header()
            }
            params = {"limit": limit}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("data", {}).get("items", [])
                    else:
                        print(f"Error fetching sync history: {response.status}")
                        return []

        except Exception as e:
            print(f"Error fetching sync history: {str(e)}")
            return []

    async def get_connection_by_id(self, connection_id: str) -> FivetranNode:
        """Get connection details and sync history by connection ID"""
        print(f"\n[Fivetran Service] Fetching connection details for {connection_id}...")

        try:
            # Fetch sync history
            print(f"[Fivetran Service] Fetching sync history...")
            syncs = await self.get_sync_history(connection_id, limit=20)

            if not syncs:
                print(f"[Fivetran Service] ❌ No sync history found for connection {connection_id}")
                return FivetranNode(
                    name=connection_id,
                    connection_id=connection_id,
                    connection_name=connection_id,
                    status="no_syncs",
                    error="No sync history found"
                )

            print(f"[Fivetran Service] ✅ Found {len(syncs)} sync record(s)")

            # Parse sync records
            sync_records = []
            for sync in syncs:
                record = FivetranSyncRecord(
                    sync_id=sync.get("id", "unknown"),
                    status=sync.get("status", "unknown"),
                    started_at=self._parse_datetime(sync.get("started_at")),
                    completed_at=self._parse_datetime(sync.get("completed_at")),
                    records_processed=sync.get("transformed_rows_count"),
                    error_message=sync.get("error", {}).get("message") if sync.get("error") else None
                )
                sync_records.append(record)

            # Get latest sync info
            latest_sync = sync_records[0] if sync_records else None
            last_sync_time = latest_sync.started_at if latest_sync else None
            last_sync_status = latest_sync.status if latest_sync else None

            print(f"[Fivetran Service] 📊 Sync Summary:")
            print(f"[Fivetran Service]    - Latest Sync Status: {last_sync_status}")
            print(f"[Fivetran Service]    - Latest Sync Time: {last_sync_time}")
            print(f"[Fivetran Service]    - Total Syncs Fetched: {len(sync_records)}")

            return FivetranNode(
                name=connection_id,
                connection_id=connection_id,
                connection_name=connection_id,
                status=last_sync_status or "unknown",
                last_sync=last_sync_time,
                last_sync_status=last_sync_status,
                sync_history=sync_records
            )

        except Exception as e:
            print(f"[Fivetran Service] ❌ Error: {str(e)}")
            return FivetranNode(
                name=connection_id,
                connection_id=connection_id,
                connection_name=connection_id,
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
