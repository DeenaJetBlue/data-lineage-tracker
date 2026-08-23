from fastapi import APIRouter, HTTPException
from datetime import datetime
from app.models import LineageData, LineageResponse, LineageEdge
from app.services import ConfigService, ADLSService, ADFService, DBTService, FivetranService
from app.config import settings

router = APIRouter(prefix="/api", tags=["lineage"])

# Initialize services
config_service = ConfigService(settings.config_file_path)
adls_service = ADLSService()
adf_service = ADFService()
dbt_service = DBTService()
fivetran_service = FivetranService()


@router.get("/tables")
async def get_all_tables():
    try:
        tables = config_service.list_table_names()
        return {
            "success": True,
            "data": {
                "total": len(tables),
                "tables": tables
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineage/{table_name}")
async def get_table_lineage(table_name: str, include_fivetran: bool = False):
    try:
        # Get table configuration
        print(f"\n📖 Loading configuration for table: {table_name}")
        table_config = config_service.get_table_config(table_name)
        if not table_config:
            print(f"❌ Table '{table_name}' not found in configuration")
            raise HTTPException(
                status_code=404,
                detail=f"Table '{table_name}' not found in configuration"
            )

        print(f"✅ Configuration loaded successfully!")
        print(f"\n📋 Configuration Details:")
        print(f"   Table Name: {table_config.table_name}")
        print(f"   ADLS Storage: {table_config.adls_storage_name}")
        print(f"   ADF Pipeline: {table_config.adf_pipeline}")
        print(f"   DBT Stage Job: {table_config.dbt_stage_job_id}")
        print(f"   DBT Star Job: {table_config.dbt_star_job_id}")
        if table_config.fivetran_connection_id:
            print(f"   Fivetran Connection: {table_config.fivetran_connection_id}")

        # Fetch data from each layer
        print(f"\n📥 Fetching lineage data from all layers...")

        print(f"   1️⃣ Querying ADLS...")
        adls_node = await adls_service.check_file_exists(table_config.adls_path, table_config.adls_storage_rg, table_config.adls_storage_name)
        print(f"      Status: {adls_node.status}")

        print(f"   2️⃣ Querying ADF Pipeline...")
        adf_node = await adf_service.get_latest_pipeline_run(table_config.adf_pipeline, table_config.adf_resource_group, table_config.adf_factory_name)
        print(f"      Status: {adf_node.status} | Run ID: {adf_node.run_id}")

        print(f"   3️⃣ Querying DBT Stage Layer...")
        dbt_stage_node = await dbt_service.get_latest_job_run(
            table_config.dbt_stage_account_id,
            table_config.dbt_stage_job_id
        )
        print(f"      Status: {dbt_stage_node.status} | Job Name: {dbt_stage_node.job_name}")

        print(f"   4️⃣ Querying DBT Star Layer...")
        dbt_star_node = await dbt_service.get_latest_job_run(
            table_config.dbt_star_account_id,
            table_config.dbt_star_job_id
        )
        print(f"      Status: {dbt_star_node.status} | Job Name: {dbt_star_node.job_name}")

        # Fetch Fivetran data if enabled
        fivetran_node = None
        if include_fivetran and table_config.fivetran_connection_id:
            print(f"   5️⃣ Querying Fivetran Connection...")
            fivetran_node = await fivetran_service.get_connection_by_id(table_config.fivetran_connection_id)
            print(f"      Status: {fivetran_node.status} | Syncs: {len(fivetran_node.sync_history)}")

        print(f"\n✅ All layers queried successfully!")

        # Create edges for lineage
        edges = [
            LineageEdge(source="ADLS", target="ADF", label="Load to Raw"),
            LineageEdge(source="ADF", target="DBT_Stage", label="Transform to STG"),
            LineageEdge(source="DBT_Stage", target="DBT_Star", label="Transform to Star")
        ]

        if fivetran_node:
            edges.insert(0, LineageEdge(source="Fivetran", target="ADLS", label="Ingest to Lake"))

        # Build response
        lineage = LineageData(
            table_name=table_name,
            adls=adls_node,
            adf=adf_node,
            dbt_stage=dbt_stage_node,
            dbt_star=dbt_star_node,
            fivetran=fivetran_node,
            edges=edges,
            timestamp=datetime.now()
        )

        print(f"\n📊 Lineage data prepared and ready to return")

        return LineageResponse(
            success=True,
            data=lineage
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return LineageResponse(
            success=False,
            error=str(e)
        )


@router.get("/fivetran/connections")
async def get_fivetran_connections():
    try:
        print("\n📥 Fetching all Fivetran connections...")
        connections = await fivetran_service.get_connections()

        if not connections:
            print("❌ No connections found!")
            return {
                "success": False,
                "error": "No connections found"
            }

        print(f"✓ Found {len(connections)} connection(s)")
        return {
            "success": True,
            "data": {
                "total": len(connections),
                "connections": connections
            }
        }
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fivetran/sync-history/{connection_id}")
async def get_fivetran_sync_history(connection_id: str):
    try:
        print(f"\n📥 Fetching sync history for connection: {connection_id}")
        fivetran_node = await fivetran_service.get_connection_by_id(connection_id)

        return {
            "success": True,
            "data": fivetran_node
        }
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineage/{table_name}/with-fivetran")
async def get_table_lineage_with_fivetran(table_name: str, fivetran_connection_id: str = None):
    try:
        # Get table configuration
        print(f"\n📖 Loading configuration for table: {table_name}")
        table_config = config_service.get_table_config(table_name)
        if not table_config:
            print(f"❌ Table '{table_name}' not found in configuration")
            raise HTTPException(
                status_code=404,
                detail=f"Table '{table_name}' not found in configuration"
            )

        print(f"✅ Configuration loaded successfully!")
        print(f"\n📋 Configuration Details:")
        print(f"   Table Name: {table_config.table_name}")
        print(f"   ADLS Storage: {table_config.adls_storage_name}")
        print(f"   ADF Pipeline: {table_config.adf_pipeline}")
        print(f"   DBT Stage Job: {table_config.dbt_stage_job_id}")
        print(f"   DBT Star Job: {table_config.dbt_star_job_id}")
        if table_config.fivetran_connection_id or fivetran_connection_id:
            print(f"   Fivetran Connection: {table_config.fivetran_connection_id or fivetran_connection_id}")

        # Fetch data from each layer
        print(f"\n📥 Fetching lineage data from all layers...")

        print(f"   1️⃣ Querying ADLS...")
        adls_node = await adls_service.check_file_exists(table_config.adls_path, table_config.adls_storage_rg, table_config.adls_storage_name)
        print(f"      Status: {adls_node.status}")

        print(f"   2️⃣ Querying ADF Pipeline...")
        adf_node = await adf_service.get_latest_pipeline_run(table_config.adf_pipeline, table_config.adf_resource_group, table_config.adf_factory_name)
        print(f"      Status: {adf_node.status} | Run ID: {adf_node.run_id}")

        print(f"   3️⃣ Querying DBT Stage Layer...")
        dbt_stage_node = await dbt_service.get_latest_job_run(
            table_config.dbt_stage_account_id,
            table_config.dbt_stage_job_id
        )
        print(f"      Status: {dbt_stage_node.status} | Job Name: {dbt_stage_node.job_name}")

        print(f"   4️⃣ Querying DBT Star Layer...")
        dbt_star_node = await dbt_service.get_latest_job_run(
            table_config.dbt_star_account_id,
            table_config.dbt_star_job_id
        )
        print(f"      Status: {dbt_star_node.status} | Job Name: {dbt_star_node.job_name}")

        # Fetch Fivetran data if connection ID is provided
        fivetran_node = None
        connection_to_use = fivetran_connection_id or table_config.fivetran_connection_id
        if connection_to_use:
            print(f"   5️⃣ Querying Fivetran Connection...")
            fivetran_node = await fivetran_service.get_connection_by_id(connection_to_use)
            print(f"      Status: {fivetran_node.status} | Syncs: {len(fivetran_node.sync_history)}")

        print(f"\n✅ All layers queried successfully!")

        # Create edges for lineage
        edges = [
            LineageEdge(source="ADLS", target="ADF", label="Load to Raw"),
            LineageEdge(source="ADF", target="DBT_Stage", label="Transform to STG"),
            LineageEdge(source="DBT_Stage", target="DBT_Star", label="Transform to Star")
        ]

        if fivetran_node:
            edges.insert(0, LineageEdge(source="Fivetran", target="ADLS", label="Ingest to Lake"))

        # Build response
        lineage = LineageData(
            table_name=table_name,
            adls=adls_node,
            adf=adf_node,
            dbt_stage=dbt_stage_node,
            dbt_star=dbt_star_node,
            fivetran=fivetran_node,
            edges=edges,
            timestamp=datetime.now()
        )

        print(f"\n📊 Lineage data prepared and ready to return")

        return LineageResponse(
            success=True,
            data=lineage
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return LineageResponse(
            success=False,
            error=str(e)
        )


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Data Lineage Tracker API"
    }
