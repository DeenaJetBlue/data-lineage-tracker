"""Azure Data Factory pipeline - same calls as Test/AdfPipelineRuns.py.

Queries the pipeline's runs in the lookback window, then loads the latest one
in full (status, timings, parameters, who invoked it).
"""

import json
from datetime import datetime, timedelta, timezone

from .base import (FAILED, RUNNING, SUCCESS, WARNING, card, column, duration_text, field, hours_text,
                   iso, lookback_hours, pill, table)

DEFAULT_LOOKBACK_HOURS = 24  # Test/AdfPipelineRuns.py looks back one day
RECENT_RUNS = 10
STATUS = {
    "Succeeded": SUCCESS,
    "Failed": FAILED,
    "InProgress": RUNNING,
    "Queued": RUNNING,
    "Canceling": RUNNING,
    "Cancelled": WARNING,
}


def _run_dict(run):
    invoked_by = getattr(run, "invoked_by", None)
    return {
        "runId": run.run_id,
        "pipelineName": run.pipeline_name,
        "status": run.status,
        "runStart": iso(run.run_start),
        "runEnd": iso(run.run_end),
        "durationInMs": run.duration_in_ms,
        "lastUpdated": iso(run.last_updated),
        "message": run.message,
        "parameters": run.parameters or {},
        "invokedBy": {
            "name": invoked_by.name,
            "id": invoked_by.id,
            "type": getattr(invoked_by, "invoked_by_type", None),
            "pipelineName": getattr(invoked_by, "pipeline_name", None),
        } if invoked_by else None,
    }


def fetch(params, env):
    # Imported here so a missing Azure package only breaks this card, not the app.
    from azure.identity import ClientSecretCredential
    from azure.mgmt.datafactory import DataFactoryManagementClient

    client = DataFactoryManagementClient(
        credential=ClientSecretCredential(
            tenant_id=env["ADF_TENANT_ID"],
            client_id=env["ADF_CLIENT_ID"],
            client_secret=env["ADF_CLIENT_SECRET"],
        ),
        subscription_id=env["ADF_SUBSCRIPTION_ID"],
    )
    hours = lookback_hours(params, DEFAULT_LOOKBACK_HOURS)
    now = datetime.now(timezone.utc)
    time_format = "%Y-%m-%dT%H:%M:%S.%fZ"

    response = client.pipeline_runs.query_by_factory(
        resource_group_name=params["Resource_Group"],
        factory_name=params["Factory_Name"],
        filter_parameters={
            "filters": [{"operand": "PipelineName", "operator": "Equals", "values": [params["Pipeline_Name"]]}],
            "lastUpdatedAfter": (now - timedelta(hours=hours)).strftime(time_format),
            "lastUpdatedBefore": now.strftime(time_format),
            # Newest start first, so a run still in progress (no RunEnd yet) counts as the latest.
            "orderBy": [{"orderBy": "RunStart", "order": "DESC"}],
        },
    )
    runs = response.value or []
    if not runs:
        return {"lookback_hours": hours, "run": None, "recent_runs": [], "runs_in_window": 0}

    latest = client.pipeline_runs.get(
        resource_group_name=params["Resource_Group"],
        factory_name=params["Factory_Name"],
        run_id=runs[0].run_id,
    )
    recent = []
    for run in runs[:RECENT_RUNS]:
        details = _run_dict(run)
        recent.append({key: details[key] for key in ("runId", "status", "runStart", "runEnd", "durationInMs")})
    return {
        "lookback_hours": hours,
        "run": _run_dict(latest),
        "recent_runs": recent,
        "runs_in_window": len(runs),
        "more_runs": bool(getattr(response, "continuation_token", None)),
    }


def _parse_json(value):
    if not isinstance(value, str) or not value.strip().startswith(("{", "[")):
        return None
    try:
        return json.loads(value)
    except ValueError:
        return None


def files_in_parameters(parameters):
    """File names inside JSON parameters, e.g. a Filter activity's output passed in as list_of_files."""
    files = []
    for name, value in parameters.items():
        parsed = _parse_json(value)
        if isinstance(parsed, dict):
            output = parsed.get("Output") or parsed.get("output") or parsed
            items = output.get("Value") or output.get("value") if isinstance(output, dict) else None
        else:
            items = parsed
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and item.get("name"):
                files.append({"name": item["name"], "type": item.get("type"), "parameter": name})
    return files


def summarize(raw, params):
    hours = raw.get("lookback_hours", DEFAULT_LOOKBACK_HOURS)
    pipeline = params["Pipeline_Name"]
    run = raw.get("run")
    if not run:
        return card(WARNING, f"No runs of {pipeline} in the last {hours_text(hours)}", status_label="No runs")

    status = run.get("status") or "Unknown"
    parameters = run.get("parameters") or {}
    files = files_in_parameters(parameters)
    duration = duration_text(run["durationInMs"] / 1000) if run.get("durationInMs") is not None else None
    count = raw.get("runs_in_window", 1)
    count_text = f"{count}+" if raw.get("more_runs") else f"{count:,}"
    invoked = run.get("invokedBy") or {}
    invoked_text = " · ".join(str(part) for part in (invoked.get("pipelineName") or invoked.get("name"), invoked.get("type")) if part)

    return card(
        STATUS.get(status, WARNING),
        f"{pipeline} · latest of {count_text} run{'s' if count != 1 else ''} in the last {hours_text(hours)}",
        status_label=status,
        metrics=[
            field(f"Runs ({hours_text(hours)})", count_text),
            field("Started", run.get("runStart"), "datetime"),
            field("Duration", duration),
        ],
        details=[
            field("Run ID", run.get("runId"), "code"),
            field("Message", run.get("message")),
            field("Started", run.get("runStart"), "datetime"),
            field("Ended", run.get("runEnd"), "datetime"),
            field("Invoked by", invoked_text),
            field("Files in this run", ", ".join(f["name"] for f in files), "code"),
        ],
        tables=[
            table(
                f"Parameters ({len(parameters)})",
                [column("name", "Parameter", "code"), column("value", "Value", "json")],
                [{"name": name, "value": _parse_json(value) or value} for name, value in parameters.items()],
            ) if parameters else None,
            table(
                f"Recent runs ({len(raw.get('recent_runs') or [])})",
                [
                    column("runStart", "Started", "datetime"),
                    column("status", "Status", "pill"),
                    column("duration", "Duration"),
                    column("runId", "Run ID", "code"),
                ],
                [
                    {
                        "runStart": item.get("runStart"),
                        "status": pill(item.get("status") or "Unknown", STATUS.get(item.get("status"), WARNING)),
                        "duration": duration_text(item["durationInMs"] / 1000) if item.get("durationInMs") is not None else None,
                        "runId": item.get("runId"),
                    }
                    for item in raw.get("recent_runs") or []
                ],
            ) if raw.get("recent_runs") else None,
        ],
        raw=run,
    )
