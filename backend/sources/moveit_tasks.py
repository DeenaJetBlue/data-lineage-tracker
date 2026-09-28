"""MOVEit Automation task - same calls as Test/MoveIT_Tasks.py.

Reads the task's run log and reports the latest run's exit status.
"""

import re

import requests
import urllib3

from .base import FAILED, RUNNING, SUCCESS, WARNING, card, column, field, http_error, iso, pill, table

# The WebAdmin server presents a self-signed certificate; the Test script also calls it with verify=False.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RECENT_RUNS = 10
SHOWN_KEYS = ("id", "taskId", "startTime", "exitStatus")


def fetch(params, env):
    server = env["WEBADMIN_SERVER"].strip().rstrip("/")
    if not server.startswith(("http://", "https://")):
        server = f"https://{server}"

    response = requests.post(
        f"{server}/api/v1/token",
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "password",
            "server_host": server.split("://", 1)[-1],
            "username": env["USERNAME"],
            "password": env["PASSWORD"],
        },
        verify=False,
        timeout=60,
        allow_redirects=True,
    )
    if response.status_code != 200:
        raise http_error(response, "Access token request")
    token = response.json().get("access_token")

    response = requests.get(
        f"{server}/api/v1/tasks/{params['Task_ID']}/log",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        params={"page": 1, "perPage": 50},
        verify=False,
        timeout=60,
        allow_redirects=True,
    )
    if response.status_code != 200:
        raise http_error(response, "Task log request")

    data = response.json()
    items = (data.get("items") or []) if isinstance(data, dict) else []
    items.sort(key=lambda item: item.get("startTime") or "", reverse=True)
    return {"runs": items[:RECENT_RUNS]}


def exit_tone(exit_status):
    text = (exit_status or "").lower()
    if "success" in text:
        return SUCCESS
    if "fail" in text or "error" in text:
        return FAILED
    if "running" in text or "progress" in text:
        return RUNNING
    return WARNING  # e.g. "No xfer": the task ran but moved no files


def _label(key):
    return re.sub(r"(?<!^)(?=[A-Z])", " ", key).capitalize()


def summarize(raw, params):
    task = params["Task_ID"]
    runs = raw.get("runs") or []
    if not runs:
        return card(WARNING, f"No runs logged for task {task}", status_label="No runs")

    latest = runs[0]
    exit_status = latest.get("exitStatus") or "Unknown"
    succeeded = sum(1 for run in runs if exit_tone(run.get("exitStatus")) == SUCCESS)
    extra = [
        field(_label(key), iso(value) if key.lower().endswith("time") else value,
              "datetime" if key.lower().endswith("time") else "text")
        for key, value in latest.items()
        if key not in SHOWN_KEYS and isinstance(value, (str, int, float))
    ]

    return card(
        exit_tone(exit_status),
        f"Task {task} · latest run: {exit_status}",
        status_label=exit_status,
        metrics=[
            field("Last run", iso(latest.get("startTime")), "datetime"),
            field("Recent successes", f"{succeeded} of {len(runs)}"),
        ],
        details=[
            field("Task ID", task, "code"),
            field("Started", iso(latest.get("startTime")), "datetime"),
            field("Exit status", exit_status),
            field("Log entry", latest.get("id"), "code"),
            *extra,
        ],
        tables=[
            table(
                f"Recent runs ({len(runs)})",
                [column("startTime", "Started", "datetime"), column("exitStatus", "Exit status", "pill"),
                 column("id", "Log entry", "code")],
                [
                    {
                        "startTime": iso(run.get("startTime")),
                        "exitStatus": pill(run.get("exitStatus") or "Unknown", exit_tone(run.get("exitStatus"))),
                        "id": run.get("id"),
                    }
                    for run in runs
                ],
            )
        ],
        raw=latest,
    )
