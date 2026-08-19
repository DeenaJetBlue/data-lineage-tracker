import csv
import os
from pathlib import Path
from typing import Dict, Optional
from app.models import TableConfig


class ConfigService:
    def __init__(self, config_file_path: str):
        path = Path(config_file_path)
        if not path.is_absolute():
            project_root = Path(__file__).resolve().parents[3]
            backend_root = project_root / "backend"
            candidates = (
                Path.cwd() / path,
                project_root / path,
                backend_root / path,
            )
            path = next((candidate for candidate in candidates if candidate.exists()), path)
        self.config_file_path = str(path)
        self.tables: Dict[str, TableConfig] = {}
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_file_path):
            raise FileNotFoundError(f"Config file not found: {self.config_file_path}")

        with open(self.config_file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row and row.get('TableName') and row['TableName'].strip():
                    table_name = row['TableName'].strip()
                    config = TableConfig(
                        table_name=table_name,
                        adls_storage_rg=row.get('ADLSStorageRG', '').strip(),
                        adls_storage_name=row.get('ADLSStorageName', '').strip(),
                        adls_path=row.get('ADLSPath', '').strip(),
                        adf_resource_group=row.get('ADFResourceGroup', '').strip(),
                        adf_factory_name=row.get('ADFFactoryName', '').strip(),
                        adf_pipeline=row.get('ADFPipelineName', '').strip(),
                        dbt_stage_job_id=row.get('DbtStageJobId', '').strip(),
                        dbt_stage_account_id=row.get('DbtStageAccountId', '').strip(),
                        dbt_star_job_id=row.get('DbtStarJobId', '').strip(),
                        dbt_star_account_id=row.get('DbtStarAccountId', '').strip()
                    )
                    self.tables[table_name] = config

    def get_table_config(self, table_name: str) -> Optional[TableConfig]:
        return self.tables.get(table_name)

    def get_all_tables(self) -> Dict[str, TableConfig]:
        return self.tables

    def list_table_names(self) -> list:
        return list(self.tables.keys())
