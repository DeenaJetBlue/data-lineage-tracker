"""Source registry: every system the tracker checks, the lifecycle class it belongs
to, the config-table parameters it takes and the .env credentials it needs."""

from dataclasses import dataclass
from types import ModuleType

from . import adf, adls, dbt, fivetran, hvr, jbsftp, moveit_tasks, nas

LANDING_SPACE = "Landing Space"
PROCESS = "Process"
HVR_JOBS = "HVR Jobs"

CLASSES = (
    {"name": LANDING_SPACE, "description": "Where files first arrive: cloud storage, the network share and the partner SFTP."},
    {"name": PROCESS, "description": "Jobs that transform, load, move and sync the data."},
    {"name": HVR_JOBS, "description": "Replication jobs on the HVR hub, and whether each one is running."},
)

AVD_HINT = "This system is reachable only from the AVD network. Run the tracker on the AVD."


@dataclass(frozen=True)
class Source:
    key: str          # id used in API URLs
    name: str         # value for the config table's Source column
    label: str        # card title
    subtitle: str
    class_name: str
    test_script: str  # the Test/ script whose calls the collector mirrors
    module: ModuleType
    required: tuple = ()
    optional: tuple = ()
    env_keys: tuple = ()
    hint: str = ""    # shown when the system cannot be reached
    literal_env: bool = False  # read .env line by line, as the MOVEit Test scripts do

    @property
    def parameters(self):
        return self.required + self.optional


SOURCES = (
    Source("adls", "ADLS", "ADLS", "Azure Data Lake Storage", LANDING_SPACE, "Test/AdlsFileStatus.py", adls,
           required=("Storage_Account_Name", "Container_Name", "Root_Folder"), optional=("Resource_Group",),
           env_keys=("ADLS_TENANT_ID", "ADLS_CLIENT_ID", "ADLS_CLIENT_SECRET"), hint=AVD_HINT),
    Source("nas", "NAS", "NAS", "Network file share", LANDING_SPACE, "Test/NASFileStatus.py", nas,
           required=("Root_Folder",), hint=AVD_HINT),
    Source("jbsftp", "JbSftp", "JbSftp", "MOVEit Transfer SFTP", LANDING_SPACE, "Test/MoveIT_JbSftp.py", jbsftp,
           required=("Root_Folder",), env_keys=("TRANSFER_SERVER", "TUSERNAME", "TPASSWORD"), hint=AVD_HINT,
           literal_env=True),
    Source("dbt", "DBT", "DBT", "dbt Cloud job runs", PROCESS, "Test/DBTJobsRuns.py", dbt,
           required=("Account_ID", "Job_ID"), env_keys=("DBT_SECRET", "DBT_ACCESS_URL")),
    Source("adf", "ADF", "Azure Data Factory", "Pipeline runs", PROCESS, "Test/AdfPipelineRuns.py", adf,
           required=("Resource_Group", "Factory_Name", "Pipeline_Name"), optional=("Lookback_Hours",),
           env_keys=("ADF_TENANT_ID", "ADF_CLIENT_ID", "ADF_CLIENT_SECRET", "ADF_SUBSCRIPTION_ID")),
    Source("moveit_tasks", "MoveIT_Tasks", "MOVEit Tasks", "MOVEit Automation task runs", PROCESS,
           "Test/MoveIT_Tasks.py", moveit_tasks,
           required=("Task_ID",), env_keys=("WEBADMIN_SERVER", "USERNAME", "PASSWORD"), hint=AVD_HINT,
           literal_env=True),
    Source("fivetran", "Fivetran", "Fivetran", "Connector sync history", PROCESS, "Test/FivetranConnections.py",
           fivetran, required=("Connection_ID",), optional=("Lookback_Hours",),
           env_keys=("FIVETRAN_API_KEY", "FIVETRAN_API_SECRET")),
    Source("hvr", "HVR", "HVR Jobs", "Replication jobs on the HVR hub", HVR_JOBS, "Test/HVR_Jobs.py", hvr,
           optional=("Hub_Name", "Job_Filter"), env_keys=("HVR_URL", "HVR_USERNAME", "HVR_PASSWORD"), hint=AVD_HINT),
)

SOURCES_BY_KEY = {source.key: source for source in SOURCES}
# The config table may name a source by its short name or its card title, in any case.
SOURCES_BY_NAME = {alias.lower(): source for source in SOURCES for alias in (source.name, source.label)}
