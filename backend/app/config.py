from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    adf_tenant_id: str
    adf_client_id: str
    adf_client_secret: str
    adf_subscription_id: str
    adf_resource_group: str
    adf_factory_name: str

    dbt_secret: str
    dbt_environment_id: int
    dbt_access_url: str

    adls_account_name: Optional[str] = None
    adls_account_key: Optional[str] = None

    adls_tenant_id: Optional[str] = None
    adls_client_id: Optional[str] = None
    adls_client_secret: Optional[str] = None
    blob_sas_token: Optional[str] = None

    server_port: int = 8000
    config_file_path: str = "../ConfigurationFile.csv"

    class Config:
        env_file = "../.env"
        case_sensitive = False


settings = Settings()
