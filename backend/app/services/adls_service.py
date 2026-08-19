import os
from datetime import datetime
from typing import Optional
from app.models import ADLSNode
from app.config import settings
from azure.storage.filedatalake import DataLakeServiceClient
from azure.identity import ClientSecretCredential
from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError


class ADLSService:
    def __init__(self):
        self.adls_tenant_id = os.getenv("ADLS_TENANT_ID")
        self.adls_client_id = os.getenv("ADLS_CLIENT_ID")
        self.adls_client_secret = os.getenv("ADLS_CLIENT_SECRET")
        self.service_client = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            if all([self.adls_tenant_id, self.adls_client_id, self.adls_client_secret]):
                credential = ClientSecretCredential(
                    tenant_id=self.adls_tenant_id,
                    client_id=self.adls_client_id,
                    client_secret=self.adls_client_secret
                )
                self.service_client = credential
            else:
                self.service_client = None
        except Exception as e:
            print(f"Warning: Failed to initialize ADLS service client: {e}")
            self.service_client = None

    async def check_file_exists(self, path: str, storage_rg: str = None, storage_name: str = None) -> ADLSNode:
        try:
            # If service client not available, return mock response
            if not self.service_client or not storage_name:
                node = ADLSNode(
                    name=path.split('/')[-2] if path.endswith('/') else path.split('/')[-1],
                    path=path,
                    status="available",
                    last_modified=datetime.now(),
                    file_count=1
                )
                return node

            # Connect to ADLS with service principal
            account_url = f"https://{storage_name}.dfs.core.windows.net"
            client = DataLakeServiceClient(account_url=account_url, credential=self.service_client)

            # Extract container and file path from the path parameter
            # Assuming format: container_name/file_path or just file_path
            path_parts = path.split('/', 1)
            container_name = path_parts[0]
            file_path = path_parts[1] if len(path_parts) > 1 else path

            file_system_client = client.get_file_system_client(file_system=container_name)

            # Try to check as file first
            try:
                file_client = file_system_client.get_file_client(file_path)
                properties = file_client.get_file_properties()

                node = ADLSNode(
                    name=file_path.split('/')[-1],
                    path=path,
                    status="available",
                    last_modified=properties.last_modified,
                    file_size=properties.size,
                    file_count=1
                )
                return node
            except ResourceNotFoundError:
                # Try as directory
                try:
                    directory_client = file_system_client.get_directory_client(file_path)
                    properties = directory_client.get_directory_properties()

                    # Count files in directory
                    file_count = 0
                    paths = file_system_client.get_paths(file_path)
                    for path_item in paths:
                        if not path_item.is_directory:
                            file_count += 1

                    node = ADLSNode(
                        name=file_path.split('/')[-1] or container_name,
                        path=path,
                        status="available",
                        last_modified=properties.last_modified,
                        file_count=file_count
                    )
                    return node
                except ResourceNotFoundError:
                    return ADLSNode(
                        name=path.split('/')[-1],
                        path=path,
                        status="not_found",
                        error="Path does not exist in ADLS"
                    )

        except ClientAuthenticationError as e:
            return ADLSNode(
                name=path.split('/')[-1],
                path=path,
                status="error",
                error=f"Authentication failed: {str(e)}"
            )
        except Exception as e:
            return ADLSNode(
                name=path.split('/')[-1],
                path=path,
                status="error",
                error=str(e)
            )
