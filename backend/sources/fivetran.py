"""Fivetran connection - same calls as Test/FivetranConnections.py.

Reads the connection's sync history for the lookback window.
"""

from base64 import b64encode
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests

from .base import (FAILED, RUNNING, SUCCESS, WARNING, card, column, duration_text, field, hours_text,
                   http_error, iso, lookback_hours, pill, seconds_between, table)

DEFAULT_LOOKBACK_HOURS = 3  # Test/FivetranConnections.py looks back three hours
RUNNING_STATES = {"RUNNING", "IN_PROGRESS", "SYNCING", "STARTED", "PENDING", "QUEUED", "SCHEDULED"}


def fetch(params, env):
    auth = b64encode(f"{env['FIVETRAN_API_KEY']}:{env['FIVETRAN_API_SECRET']}".encode("utf-8")).decode("utf-8")
    hours = lookback_hours(params, DEFAULT_LOOKBACK_HOURS)
    now = datetime.now(timezone.utc)
    time_format = "%Y-%m-%dT%H:%M:%SZ"

    response = requests.get(
        f"https://api.fivetran.com/v1/connections/{quote(params['Connection_ID'], safe='')}/sync-history",
        headers={"Accept": "application/json;version=2", "Authorization": f"Basic {auth}"},
        params={
            "start_time": (now - timedelta(hours=hours)).strftime(time_format),
            "end_time": now.strftime(time_format),
            "limit": "100",
        },
        timeout=60,
    )
    if response.status_code != 200:
        raise http_error(response, "Sync history request")
    return {"lookback_hours": hours, "syncs": (response.json().get("data") or {}).get("items") or []}


def sync_tone(status):
    status = (status or "").upper()
    if status in ("COMPLETED", "SUCCESS", "SUCCESSFUL", "SUCCEEDED"):
        return SUCCESS
    if "FAIL" in status or "ERROR" in status:
        return FAILED
    if status in RUNNING_STATES:
        return RUNNING
    return WARNING  # e.g. RESCHEDULED, CANCELED


def _status_text(status):
    return (status or "Unknown").replace("_", " ").title()


def _volume(sync, stage):
    return ((sync.get("stages") or {}).get(stage) or {}).get("volume")


def summarize(raw, params):
    hours = raw.get("lookback_hours", DEFAULT_LOOKBACK_HOURS)
    connection = params["Connection_ID"]
    syncs = sorted(raw.get("syncs") or [], key=lambda sync: sync.get("start") or "", reverse=True)
    if not syncs:
        return card(WARNING, f"{connection} · no syncs in the last {hours_text(hours)}", status_label="No syncs")

    latest = syncs[0]
    started, ended = iso(latest.get("start")), iso(latest.get("end"))
    succeeded = sum(1 for sync in syncs if sync_tone(sync.get("status")) == SUCCESS)

    return card(
        sync_tone(latest.get("status")),
        f"{connection} · {len(syncs)} sync{'s' if len(syncs) != 1 else ''} in the last {hours_text(hours)}",
        status_label=_status_text(latest.get("status")),
        metrics=[
            field("Last sync", ended or started, "datetime"),
            field("Succeeded", f"{succeeded} of {len(syncs)}"),
            field("Last load volume", _volume(latest, "load"), "compact"),
        ],
        details=[
            field("Connection ID", connection, "code"),
            field("Latest sync ID", latest.get("sync_id"), "code"),
            field("Started", started, "datetime"),
            field("Completed", ended, "datetime"),
            field("Duration", duration_text(seconds_between(started, ended))),
        ],
        tables=[
            table(
                f"Syncs ({len(syncs)})",
                [
                    column("start", "Started", "datetime"),
                    column("status", "Status", "pill"),
                    column("duration", "Duration"),
                    column("extract", "Extract", "compact"),
                    column("process", "Process", "compact"),
                    column("load", "Load", "compact"),
                ],
                [
                    {
                        "start": iso(sync.get("start")),
                        "status": pill(_status_text(sync.get("status")), sync_tone(sync.get("status"))),
                        "duration": duration_text(seconds_between(sync.get("start"), sync.get("end"))),
                        "extract": _volume(sync, "extract"),
                        "process": _volume(sync, "process"),
                        "load": _volume(sync, "load"),
                    }
                    for sync in syncs
                ],
                open_=True,
            )
        ],
        raw=latest,
    )
