from pydantic import BaseModel, field_serializer, ConfigDict
from typing import Optional, List, Union
from datetime import datetime


class TableConfig(BaseModel):
    table_name: str
    adls_storage_rg: str
    adls_storage_name: str
    adls_path: str
    adf_resource_group: str
    adf_factory_name: str
    adf_pipeline: str
    dbt_stage_job_id: str
    dbt_stage_account_id: str
    dbt_star_job_id: str
    dbt_star_account_id: str
    fivetran_connection_id: Optional[str] = None


class ADLSNode(BaseModel):
    name: str
    path: str
    status: str = "unknown"
    last_modified: Optional[datetime] = None
    file_count: int = 0
    file_size: Optional[int] = None
    error: Optional[str] = None


class ADFNode(BaseModel):
    name: str
    pipeline_name: str
    status: str = "unknown"
    last_run: Optional[datetime] = None
    run_id: Optional[str] = None
    error: Optional[str] = None


class DBTNode(BaseModel):
    model_config = ConfigDict(ser_json_timedelta='float')

    name: str
    job_name: str
    job_id: Optional[Union[str, int]] = None
    status: str = "unknown"
    last_run: Optional[datetime] = None
    run_id: Optional[Union[str, int]] = None
    job_status: Optional[str] = None
    error: Optional[str] = None

    @field_serializer('job_id', when_used='json')
    def serialize_job_id(self, value: Optional[Union[str, int]]) -> Optional[str]:
        """Convert job_id to string for JSON output"""
        if value is None:
            return None
        return str(value)

    @field_serializer('run_id', when_used='json')
    def serialize_run_id(self, value: Optional[Union[str, int]]) -> Optional[str]:
        """Convert run_id to string for JSON output"""
        if value is None:
            return None
        return str(value)


class FivetranSyncRecord(BaseModel):
    sync_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    records_processed: Optional[int] = None
    error_message: Optional[str] = None


class FivetranNode(BaseModel):
    name: str
    connection_id: str
    connection_name: str
    service: str = "unknown"
    status: str = "unknown"
    last_sync: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    sync_history: List[FivetranSyncRecord] = []
    error: Optional[str] = None


class LineageEdge(BaseModel):
    source: str
    target: str
    label: str


class LineageData(BaseModel):
    table_name: str
    adls: Optional[ADLSNode] = None
    adf: Optional[ADFNode] = None
    snowflake_raw: Optional[ADFNode] = None
    dbt_stage: Optional[DBTNode] = None
    dbt_star: Optional[DBTNode] = None
    fivetran: Optional[FivetranNode] = None
    edges: List[LineageEdge] = []
    timestamp: datetime


class LineageResponse(BaseModel):
    success: bool
    data: Optional[LineageData] = None
    error: Optional[str] = None
