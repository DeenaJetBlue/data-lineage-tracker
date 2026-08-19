from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import lineage
from app.config import settings

app = FastAPI(
    title="Data Lineage Tracker API",
    description="Track data flow: ADLS → ADF → Snowflake Raw → DBT STG → DBT Star",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(lineage.router)


@app.get("/")
async def root():
    return {
        "message": "Data Lineage Tracker API",
        "version": "1.0.0",
        "docs": "/docs"
    }
