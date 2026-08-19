from datetime import datetime
from typing import Optional
from app.models import ADLSNode
from app.config import settings


class ADLSService:
    def __init__(self):
        self.account_name = settings.adls_account_name
        self.account_key = settings.adls_account_key

    async def check_file_exists(self, path: str, storage_rg: str = None, storage_name: str = None) -> ADLSNode:
        try:
            node = ADLSNode(
                name=path.split('/')[-2] if path.endswith('/') else path.split('/')[-1],
                path=path,
                status="available",
                last_modified=datetime.now(),
                file_count=1
            )
            return node
        except Exception as e:
            return ADLSNode(
                name=path,
                path=path,
                status="error",
                error=str(e)
            )
