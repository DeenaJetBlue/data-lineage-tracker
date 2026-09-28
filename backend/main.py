"""FastAPI app: the config-table API, per-source status checks and the frontend.

    GET /api/tables                                 tables in the config table
    GET /api/tables/{table}                         one table's configuration, by class
    GET /api/tables/{table}/sources/{source_key}    live status card for one source
"""

import logging
import mimetypes

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from . import settings
from .config_table import ConfigError, load_config_table
from .runner import run_source
from .sources import CLASSES, SOURCES, SOURCES_BY_KEY

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Data Lineage Tracker - File Lifecycle",
    description="Landing Space, Process and HVR Jobs status for each table in the config table.",
    version="1.0.0",
)

CONFIG_TABLE_NAME = settings.CONFIG_TABLE_FILE.relative_to(settings.PROJECT_ROOT).as_posix()


def _tables():
    try:
        return load_config_table()
    except ConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _table(name):
    tables = _tables()
    table = tables.get(name) or next((t for key, t in tables.items() if key.lower() == name.lower()), None)
    if not table:
        raise HTTPException(status_code=404, detail=f"Table '{name}' is not in {CONFIG_TABLE_NAME}")
    return table


def _classes(table, with_params):
    classes = []
    for cls in CLASSES:
        sources = []
        for source in SOURCES:
            if source.class_name != cls["name"]:
                continue
            entry = {
                "key": source.key,
                "name": source.name,
                "label": source.label,
                "subtitle": source.subtitle,
                "test_script": source.test_script,
                "configured": source.key in table.sources,
            }
            if with_params:
                entry["params"] = table.sources.get(source.key, {})
            sources.append(entry)
        classes.append({**cls, "sources": sources})
    return classes


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "demo_mode": settings.DEMO_MODE,
        "config_table": CONFIG_TABLE_NAME,
        "env_file_found": settings.ENV_FILE.exists(),
    }


@app.get("/api/tables")
def list_tables():
    return {
        "demo_mode": settings.DEMO_MODE,
        "config_table": CONFIG_TABLE_NAME,
        "tables": [{"name": t.name, "classes": _classes(t, with_params=False)} for t in _tables().values()],
    }


@app.get("/api/tables/{table_name}")
def get_table(table_name: str):
    table = _table(table_name)
    return {
        "name": table.name,
        "demo_mode": settings.DEMO_MODE,
        "config_table": CONFIG_TABLE_NAME,
        "classes": _classes(table, with_params=True),
        "rows": table.rows,
    }


@app.get("/api/tables/{table_name}/sources/{source_key}")
def check_source(table_name: str, source_key: str):
    source = SOURCES_BY_KEY.get(source_key.lower())
    if not source:
        raise HTTPException(status_code=404,
                            detail=f"Unknown source '{source_key}'. Use one of: {', '.join(SOURCES_BY_KEY)}")
    table = _table(table_name)
    return run_source(source, table.sources.get(source.key))


# On Windows, Python takes MIME types from the registry, which sometimes maps .js to text/plain;
# browsers refuse to run module scripts served that way, and the pages would never load.
for extension, mime_type in ((".html", "text/html"), (".js", "text/javascript"),
                             (".css", "text/css"), (".svg", "image/svg+xml")):
    mimetypes.add_type(mime_type, extension)


class Frontend(StaticFiles):
    """Static files the browser revalidates on every load, so an updated frontend is never served stale."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


# Mounted last so the /api routes above take precedence.
app.mount("/", Frontend(directory=settings.FRONTEND_DIR, html=True), name="frontend")
