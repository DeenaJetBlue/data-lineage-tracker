# Fivetran Integration with Data Lineage Tracker

## Overview

The Fivetran API has been successfully integrated into the Data Lineage Tracker system. This enables end-to-end data lineage tracking from data ingestion (Fivetran) through transformation (DBT) and storage (ADLS/ADF).

## Architecture

```
Fivetran (Ingestion)
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

### 1. Fivetran Service (`backend/app/services/fivetran_service.py`)

**Purpose**: Handles all interactions with the Fivetran API

**Key Methods**:

```python
# Get list of all connections
await fivetran_service.get_connections(limit=100)

# Get sync history for a specific connection
await fivetran_service.get_sync_history(connection_id, limit=20)

# Get full connection details with sync history
await fivetran_service.get_connection_by_id(connection_id)
```

**Authentication**:
- Uses Basic Auth with base64-encoded API key and secret
- Credentials loaded from `.env` file:
  - `FIVETRAN_API_KEY`
  - `FIVETRAN_API_SECRET`
  - `FIVETRAN_SYSTEM_KEY` (pre-encoded)

### 2. Data Models (`backend/app/models.py`)

```python
class FivetranSyncRecord(BaseModel):
    """Individual sync record"""
    sync_id: str
    status: str  # e.g., "success", "failure"
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    records_processed: Optional[int]
    error_message: Optional[str]

class FivetranNode(BaseModel):
    """Connection-level data"""
    name: str
    connection_id: str
    connection_name: str
    service: str  # e.g., "postgres", "salesforce"
    status: str
    last_sync: Optional[datetime]
    last_sync_status: Optional[str]
    sync_history: List[FivetranSyncRecord]
    error: Optional[str]

class LineageData(BaseModel):
    # ... existing fields ...
    fivetran: Optional[FivetranNode] = None
    # ... existing fields ...
```

## API Endpoints

### 1. List All Fivetran Connections

```http
GET /api/fivetran/connections
```

**Response**:
```json
{
  "success": true,
  "data": {
    "total": 5,
    "connections": [
      {
        "id": "late_ordinary",
        "name": "Sales Database",
        "service": "postgres",
        "status": "active"
      },
      ...
    ]
  }
}
```

### 2. Get Sync History for a Connection

```http
GET /api/fivetran/sync-history/{connection_id}
```

**Example**:
```http
GET /api/fivetran/sync-history/late_ordinary
```

**Response**:
```json
{
  "success": true,
  "data": {
    "name": "late_ordinary",
    "connection_id": "late_ordinary",
    "connection_name": "late_ordinary",
    "service": "unknown",
    "status": "success",
    "last_sync": "2026-08-24T10:30:45.123456",
    "last_sync_status": "success",
    "sync_history": [
      {
        "sync_id": "sync_001",
        "status": "success",
        "started_at": "2026-08-24T10:30:45.123456",
        "completed_at": "2026-08-24T10:45:22.654321",
        "records_processed": 15000,
        "error_message": null
      },
      ...
    ]
  }
}
```

### 3. Get Lineage with Fivetran Data

#### Option A: With Fivetran (Optional)

```http
GET /api/lineage/{table_name}?include_fivetran=true
```

#### Option B: Full Lineage with Fivetran

```http
GET /api/lineage/{table_name}/with-fivetran
```

**Example**:
```http
GET /api/lineage/customer_fact?include_fivetran=true
```

**Response**:
```json
{
  "success": true,
  "data": {
    "table_name": "customer_fact",
    "fivetran": {
      "name": "late_ordinary",
      "connection_id": "late_ordinary",
      "status": "success",
      "last_sync": "2026-08-24T10:30:45.123456",
      "sync_history": [...]
    },
    "adls": { ... },
    "adf": { ... },
    "dbt_stage": { ... },
    "dbt_star": { ... },
    "edges": [
      {
        "source": "Fivetran",
        "target": "ADLS",
        "label": "Ingest to Lake"
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
# Fivetran API Credentials
FIVETRAN_API_KEY=ft_xxxxxxxxxx
FIVETRAN_API_SECRET=xxxxxxxxxxxxxxxx
FIVETRAN_SYSTEM_KEY=xxxxxxxxxxxxxxxx  # Pre-encoded base64
```

### Table Configuration (ConfigurationFile.csv)

Add optional `fivetran_connection_id` column to your CSV:

```csv
table_name,adls_storage_rg,adls_storage_name,...,fivetran_connection_id
customer_fact,JB-RG-Analytics-Prd,jbadls,...,late_ordinary
```

## Usage Examples

### Example 1: Get Sync History for a Connection

```python
import asyncio
from app.services import FivetranService

async def example():
    service = FivetranService()
    
    # Get connection details with sync history
    connection = await service.get_connection_by_id("late_ordinary")
    
    print(f"Connection: {connection.connection_name}")
    print(f"Status: {connection.status}")
    print(f"Last Sync: {connection.last_sync}")
    print(f"Sync History: {len(connection.sync_history)} records")
    
    for sync in connection.sync_history[:5]:
        print(f"  - {sync.sync_id}: {sync.status}")

asyncio.run(example())
```

### Example 2: Get Complete Lineage with Fivetran

```python
import requests

response = requests.get(
    "http://localhost:8000/api/lineage/customer_fact?include_fivetran=true"
)

lineage = response.json()["data"]

# Trace the data flow
print(f"Table: {lineage['table_name']}")
print(f"Fivetran Status: {lineage['fivetran']['status']}")
print(f"ADLS Status: {lineage['adls']['status']}")
print(f"ADF Status: {lineage['adf']['status']}")
print(f"DBT Stage Status: {lineage['dbt_stage']['status']}")
print(f"DBT Star Status: {lineage['dbt_star']['status']}")

# View the edges
for edge in lineage['edges']:
    print(f"{edge['source']} → {edge['target']} ({edge['label']})")
```

### Example 3: Monitor Data Quality

```python
import requests

response = requests.get(
    "http://localhost:8000/api/fivetran/sync-history/late_ordinary"
)

data = response.json()["data"]

# Check sync status
for sync in data["sync_history"]:
    if sync["status"] != "success":
        print(f"⚠️  Sync {sync['sync_id']} failed!")
        print(f"   Error: {sync['error_message']}")
    else:
        print(f"✓ Sync {sync['sync_id']}: {sync['records_processed']} records")
```

## Backtracking Data Issues

The integrated lineage system allows you to backtrack data issues from the final table:

### Step 1: Identify Problem Table
```bash
GET /api/lineage/customer_fact?include_fivetran=true
```

### Step 2: Check Each Layer
- **Fivetran**: Are records being ingested? Check `sync_history`
- **ADLS**: Are files present in data lake? Check `adls.status`
- **ADF**: Did pipeline execute successfully? Check `adf.status` and `adf.run_id`
- **DBT Stage**: Did staging models compile? Check `dbt_stage.status` and `dbt_stage.run_id`
- **DBT Star**: Did final models build? Check `dbt_star.status` and `dbt_star.run_id`

### Step 3: Root Cause Analysis
Starting from Fivetran:
1. If Fivetran syncs fail → Check source database connection
2. If ADLS missing → Check ADF pipeline logs
3. If ADF fails → Check transformation logic
4. If DBT fails → Check dbt run logs
5. If Star schema has issues → Check data validation rules

## Testing

### Run the Integration Test

```bash
python Test/fivetran_lineage_integration_test.py
```

This test will:
1. ✓ Fetch all Fivetran connections
2. ✓ Get sync history for `late_ordinary` connection
3. ✓ Test the local API endpoints
4. ✓ Verify integrated lineage

### Manual API Testing

```bash
# 1. Start the backend
python backend/run.py

# 2. In another terminal, test endpoints
curl http://localhost:8000/api/fivetran/connections
curl http://localhost:8000/api/fivetran/sync-history/late_ordinary
curl http://localhost:8000/api/lineage/customer_fact?include_fivetran=true
```

## Error Handling

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `Fivetran API credentials not configured` | Missing .env variables | Set `FIVETRAN_API_KEY` and `FIVETRAN_API_SECRET` |
| `No sync history found` | Connection has no syncs | Verify connection ID exists |
| `Authorization failed` | Invalid credentials | Regenerate API key in Fivetran |
| `Connection timeout` | Network issue | Check internet connection and Fivetran API status |

## Future Enhancements

1. **Incremental Sync Tracking**: Track delta changes from Fivetran
2. **Data Quality Metrics**: Capture record counts and data quality scores
3. **Alerting**: Notify on sync failures
4. **Historical Analysis**: Compare sync performance over time
5. **Destination Tracking**: Track which warehouse each connector syncs to

## References

- [Fivetran API Documentation](https://fivetran.com/docs/rest-api/)
- [Data Lineage Tracker Architecture](./README.md)
- [DBT Integration](./backend/app/services/dbt_service.py)
- [ADF Integration](./backend/app/services/adf_service.py)
