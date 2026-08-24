# MOVEit Integration with Data Lineage Tracker

## Overview

The MOVEit Automation API has been successfully integrated into the Data Lineage Tracker system. This enables file transfer monitoring and task status tracking as part of your data lineage.

## Architecture

```
MOVEit Task (File Transfer)
    ↓
ADLS (Data Lake)
    ↓
ADF (Pipeline Orchestration)
    ↓
DBT Stage Layer (STG Models)
    ↓
DBT Star Layer (Fact/Dimension Tables)
```

## New Components

### 1. MOVEit Service (`backend/app/services/moveit_service.py`)

**Purpose**: Handles all interactions with MOVEit Automation API

**Key Methods**:

```python
# Authenticate and get access token
await moveit_service.get_access_token()

# Get task details
await moveit_service.get_task_details(task_id, token)

# Get task logs with pagination
await moveit_service.get_task_logs(task_id, token, page=1, per_page=50)

# Get full task information with logs
await moveit_service.get_task_by_id(task_id)
```

**Authentication**:
- Uses OAuth 2.0 with password grant type
- Credentials loaded from `.env` file:
  - `WEBADMIN_SERVER` - MOVEit server IP/hostname
  - `USERNAME` - MOVEit username
  - `PASSWORD` - MOVEit password

### 2. Data Models (`backend/app/models.py`)

```python
class MOVEitLogEntry(BaseModel):
    """Individual task log entry"""
    timestamp: Optional[datetime]
    level: Optional[str]  # e.g., "INFO", "ERROR", "WARNING"
    message: Optional[str]
    details: Optional[dict]

class MOVEitNode(BaseModel):
    """Task-level data"""
    name: str
    task_id: str
    task_name: str
    status: str  # e.g., "Completed", "Running", "Failed"
    created: Optional[datetime]
    modified: Optional[datetime]
    logs: List[MOVEitLogEntry]  # First 20 logs
    total_logs: int  # Total available logs
    error: Optional[str]
```

## API Endpoints

### 1. Get MOVEit Task Details and Logs

```http
GET /api/moveit/task/{task_id}
```

**Example**:
```http
GET /api/moveit/task/243149144
```

**Response**:
```json
{
  "success": true,
  "data": {
    "name": "Daily File Transfer",
    "task_id": "243149144",
    "task_name": "Daily File Transfer",
    "status": "Completed",
    "created": "2026-08-24T09:00:00.000000",
    "modified": "2026-08-24T10:30:00.000000",
    "total_logs": 25,
    "logs": [
      {
        "timestamp": "2026-08-24T09:00:00.000000",
        "level": "INFO",
        "message": "Task started",
        "details": null
      },
      {
        "timestamp": "2026-08-24T09:15:00.000000",
        "level": "INFO",
        "message": "Files transferred successfully",
        "details": null
      }
    ]
  }
}
```

### 2. Get Lineage with MOVEit Data

#### Option A: With MOVEit (Optional)

```http
GET /api/lineage/{table_name}?include_moveit=true
```

#### Option B: Full Lineage with MOVEit

```http
GET /api/lineage/{table_name}/with-moveit
```

**Example**:
```http
GET /api/lineage/customer_fact?include_moveit=true
```

**Response**:
```json
{
  "success": true,
  "data": {
    "table_name": "customer_fact",
    "moveit": {
      "name": "Daily File Transfer",
      "task_id": "243149144",
      "status": "Completed",
      "created": "2026-08-24T09:00:00.000000",
      "logs": [...]
    },
    "adls": { ... },
    "adf": { ... },
    "dbt_stage": { ... },
    "dbt_star": { ... },
    "edges": [
      {
        "source": "MOVEit",
        "target": "ADLS",
        "label": "Transfer to Lake"
      },
      {
        "source": "ADLS",
        "target": "ADF",
        "label": "Load to Raw"
      },
      ...
    ]
  }
}
```

## Configuration

### Environment Variables (.env)

```bash
# MOVEit Configuration
WEBADMIN_SERVER=10.204.124.216
USERNAME=Jetblue\bpdn90003280
PASSWORD=Ramayan@1993
```

### Table Configuration (ConfigurationFile.csv)

Add optional `moveit_task_id` column to your CSV:

```csv
table_name,adls_storage_rg,adls_storage_name,...,moveit_task_id
customer_fact,JB-RG-Analytics-Prd,jbadls,...,243149144
```

## Usage Examples

### Example 1: Get Task Logs

```python
import asyncio
from app.services import MOVEitService

async def example():
    service = MOVEitService()
    
    # Get task details with logs
    task = await service.get_task_by_id("243149144")
    
    print(f"Task: {task.task_name}")
    print(f"Status: {task.status}")
    print(f"Created: {task.created}")
    print(f"Total Logs: {task.total_logs}")
    print(f"Logs Retrieved: {len(task.logs)}")
    
    for log in task.logs[:5]:
        print(f"  - [{log.level}] {log.timestamp}: {log.message}")

asyncio.run(example())
```

### Example 2: Get Complete Lineage with MOVEit

```python
import requests

response = requests.get(
    "http://localhost:8000/api/lineage/customer_fact?include_moveit=true"
)

lineage = response.json()["data"]

# Trace the data flow
print(f"Table: {lineage['table_name']}")
print(f"MOVEit Task: {lineage['moveit']['task_name']}")
print(f"MOVEit Status: {lineage['moveit']['status']}")
print(f"ADLS Status: {lineage['adls']['status']}")
print(f"ADF Status: {lineage['adf']['status']}")
print(f"DBT Stage Status: {lineage['dbt_stage']['status']}")
print(f"DBT Star Status: {lineage['dbt_star']['status']}")

# View the edges
for edge in lineage['edges']:
    print(f"{edge['source']} → {edge['target']} ({edge['label']})")
```

### Example 3: Monitor File Transfer Status

```python
import requests

response = requests.get(
    "http://localhost:8000/api/moveit/task/243149144"
)

task_data = response.json()["data"]

print(f"Task: {task_data['task_name']}")
print(f"Status: {task_data['status']}")
print(f"Created: {task_data['created']}")
print(f"Modified: {task_data['modified']}")
print(f"Total Logs: {task_data['total_logs']}")

# Check for errors
for log in task_data['logs']:
    if log['level'] == 'ERROR':
        print(f"⚠️  Error at {log['timestamp']}: {log['message']}")
    elif log['level'] == 'WARNING':
        print(f"⚠️  Warning at {log['timestamp']}: {log['message']}")
```

## Backtracking Data Issues

The integrated lineage system allows you to backtrack from final table to file transfer:

### Step 1: Identify Problem Table
```bash
GET /api/lineage/customer_fact?include_moveit=true
```

### Step 2: Check Each Layer
- **MOVEit**: Did files transfer successfully? Check `moveit.status` and `logs`
- **ADLS**: Are files present in data lake? Check `adls.status`
- **ADF**: Did pipeline execute? Check `adf.status` and `adf.run_id`
- **DBT Stage**: Did staging models compile? Check `dbt_stage.status`
- **DBT Star**: Did final models build? Check `dbt_star.status`

### Step 3: Root Cause Analysis
Starting from MOVEit:
1. If MOVEit task fails → Check source files and network connectivity
2. If MOVEit succeeds but ADLS missing → Check ADF pipeline logs
3. If ADLS present but ADF fails → Check data transformation logic
4. If ADF succeeds but DBT fails → Check dbt run logs
5. If DBT succeeds but Star schema has issues → Check data validation

## Error Handling

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `Authentication failed` | Invalid MOVEit credentials | Verify `WEBADMIN_SERVER`, `USERNAME`, `PASSWORD` in `.env` |
| `Task not found (404)` | Wrong task ID | Verify task ID exists in MOVEit |
| `Connection error` | Server unreachable | Check VDI connection and firewall |
| `Request timeout` | Slow network | Check network connectivity to MOVEit server |

## Future Enhancements

1. **Task Execution History**: Track multiple task runs over time
2. **File Metrics**: Capture file count, size, and transfer speed
3. **Error Tracking**: Automatic alerting on task failures
4. **Schedule Monitoring**: Track scheduled vs actual task execution
5. **Performance Analytics**: Compare transfer times across runs

## References

- [MOVEit Automation API Documentation](https://www.ipswitch.com/products/moveit)
- [Data Lineage Tracker Architecture](./README.md)
- [Fivetran Integration](./FIVETRAN_INTEGRATION.md)
- [HVR Integration](./backend/app/services/hvr_service.py)
