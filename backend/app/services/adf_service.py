import aiohttp
from datetime import datetime, timedelta
from typing import Optional
from app.models import ADFNode
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class ADFService:
    def __init__(self):
        self.tenant_id = settings.adf_tenant_id
        self.client_id = settings.adf_client_id
        self.client_secret = settings.adf_client_secret
        self.subscription_id = settings.adf_subscription_id
        self.resource_group = settings.adf_resource_group
        self.factory_name = settings.adf_factory_name
        self.token = None
        self.token_expires = None

    async def get_auth_token(self) -> str:
        if self.token and self.token_expires and datetime.now() < self.token_expires:
            return self.token

        try:
            url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://management.azure.com/.default",
                "grant_type": "client_credentials"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.token = data["access_token"]
                        self.token_expires = datetime.now() + timedelta(seconds=data.get("expires_in", 3600) - 60)
                        return self.token
                    else:
                        raise Exception(f"Failed to get token: {response.status}")
        except Exception as e:
            print(f"Error getting auth token: {e}")
            raise

    async def get_latest_pipeline_run(self, pipeline_name: str, resource_group: str = None, factory_name: str = None) -> ADFNode:
        try:
            token = await self.get_auth_token()
            rg = resource_group if resource_group else self.resource_group
            fn = factory_name if factory_name else self.factory_name

            # Calculate date range: last 24 hours in UTC
            now = datetime.utcnow()
            last_24_hours_ago = now - timedelta(hours=24)

            # Format dates as ISO 8601 strings with Z suffix
            last_updated_after = last_24_hours_ago.isoformat() + "Z"
            last_updated_before = now.isoformat() + "Z"

            logger.info(f"[ADF Service] Querying {pipeline_name} - UTC: {last_24_hours_ago.isoformat()[:16]} to {now.isoformat()[:16]}")

            url = (
                f"https://management.azure.com/subscriptions/{self.subscription_id}/"
                f"resourceGroups/{rg}/providers/Microsoft.DataFactory/"
                f"factories/{fn}/queryPipelineRuns"
                f"?api-version=2018-06-01"
            )

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            # Query with date range filter and order by RunEnd descending
            payload = {
                "filters": [
                    {
                        "operand": "PipelineName",
                        "operator": "Equals",
                        "values": [pipeline_name]
                    }
                ],
                "lastUpdatedAfter": last_updated_after,
                "lastUpdatedBefore": last_updated_before,
                "orderBy": [
                    {
                        "orderBy": "RunEnd",
                        "order": "DESC"
                    }
                ]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        data = await response.json()
                        runs = data.get("value", [])
                        logger.info(f"[ADF Service] Found {len(runs)} runs for {pipeline_name}")

                        if runs:
                            # Sort by runEnd descending to get the latest run
                            # If runEnd is None, use runStart
                            runs_sorted = sorted(
                                runs,
                                key=lambda r: r.get("runEnd") or r.get("runStart", ""),
                                reverse=True
                            )
                            latest_run = runs_sorted[0]

                            run_start = latest_run.get("runStart", "")
                            run_end = latest_run.get("runEnd", "")
                            logger.info(f"[ADF Service] Latest run: {latest_run.get('runId')} | Status: {latest_run.get('status')} | End: {run_end}")

                            return ADFNode(
                                name=pipeline_name,
                                pipeline_name=pipeline_name,
                                status=latest_run.get("status", "unknown").lower(),
                                last_run=datetime.fromisoformat(run_start.replace("Z", "+00:00")) if run_start else None,
                                run_id=latest_run.get("runId")
                            )
                        else:
                            logger.warning(f"[ADF Service] No runs found for {pipeline_name}")
                            return ADFNode(
                                name=pipeline_name,
                                pipeline_name=pipeline_name,
                                status="no_runs",
                                error="No runs found in last 7 days"
                            )
                    else:
                        error_text = await response.text()
                        raise Exception(f"Status {response.status}: {error_text[:200]}")
        except Exception as e:
            logger.error(f"[ADF Service] Error: {str(e)}")
            return ADFNode(
                name=pipeline_name,
                pipeline_name=pipeline_name,
                status="error",
                error=str(e)
            )
