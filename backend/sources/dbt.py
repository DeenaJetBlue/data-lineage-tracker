"""dbt Cloud job - same calls as Test/DBTJobsRuns.py.

Finds the job's latest run, then loads it with its job, trigger and steps.
"""

import re

import requests

from .base import (FAILED, RUNNING, SUCCESS, WARNING, SourceError, card, column, duration_text,
                   field, http_error, iso, link, pill, seconds_between, table)

# dbt Cloud run status codes
STATUS = {
    1: (RUNNING, "Queued"),
    2: (RUNNING, "Starting"),
    3: (RUNNING, "Running"),
    10: (SUCCESS, "Success"),
    20: (FAILED, "Error"),
    30: (WARNING, "Cancelled"),
}
LOG_FIELDS = ("logs", "debug_logs", "truncated_debug_logs")  # can be megabytes; never sent to the browser


def job_id(params):
    # Tolerates the .config style "70437463784804 #Triggered ADF - fuel_master".
    match = re.match(r"\s*(\d+)", params["Job_ID"])
    if not match:
        raise SourceError(f"Job_ID must be numeric, got '{params['Job_ID']}'")
    return match.group(1)


def fetch(params, env):
    host = env["DBT_ACCESS_URL"].replace("https://", "").replace("http://", "").rstrip("/")
    headers = {"Authorization": f"Bearer {env['DBT_SECRET']}", "Content-Type": "application/json"}
    runs_url = f"https://{host}/api/v2/accounts/{params['Account_ID']}/runs/"

    response = requests.get(runs_url, headers=headers, timeout=30, params={
        "job_definition_id": job_id(params),
        "limit": 1,
        "order_by": "-created_at",
    })
    if response.status_code != 200:
        raise http_error(response, "Listing runs")
    runs = response.json().get("data")
    if not runs:
        return {"run": None}

    response = requests.get(f"{runs_url}{runs[0]['id']}/", headers=headers, timeout=30,
                            params={"include_related": "job,trigger,run_steps"})
    if response.status_code != 200:
        raise http_error(response, "Fetching run details")

    run = response.json().get("data") or {}
    for step in run.get("run_steps") or []:
        for key in LOG_FIELDS:
            step.pop(key, None)
    return {"run": run}


def _step_row(step):
    tone, label = STATUS.get(step.get("status"), (WARNING, "Unknown"))
    return {
        "name": step.get("name"),
        "status": pill(step.get("status_humanized") or label, tone),
        "duration": step.get("duration_humanized"),
    }


def summarize(raw, params):
    run = raw.get("run")
    if not run:
        return card(WARNING, f"No runs found for job {job_id(params)}", status_label="No runs")

    tone, label = STATUS.get(run.get("status"), (WARNING, "Unknown"))
    job = run.get("job") or {}
    trigger = run.get("trigger") or {}
    job_name = job.get("name") or f"Job {run.get('job_definition_id') or job_id(params)}"
    started, finished = iso(run.get("started_at")), iso(run.get("finished_at"))
    duration = duration_text(seconds_between(started, finished)) or run.get("duration_humanized")
    sha = (run.get("git_sha") or "")[:7]
    git = " @ ".join(part for part in (run.get("git_branch"), sha) if part)
    href = run.get("href")

    steps = run.get("run_steps") or []
    if steps:
        succeeded = sum(1 for step in steps if step.get("status") == 10)
        steps_metric = field("Steps", f"{succeeded} of {len(steps)} succeeded")
        steps_table = table(
            f"Run steps ({len(steps)})",
            [column("name", "Step"), column("status", "Status", "pill"), column("duration", "Duration")],
            [_step_row(step) for step in steps],
            open_=tone == FAILED,
        )
    else:
        commands = job.get("execute_steps") or []
        steps_metric = field("Commands", len(commands), "number") if commands else None
        steps_table = table(
            f"Job commands ({len(commands)})",
            [column("command", "Command", "code")],
            [{"command": command} for command in commands],
        ) if commands else None

    return card(
        tone,
        f"{job_name} · run #{run.get('id')}",
        status_label=run.get("status_humanized") or label,
        metrics=[
            field("Finished", finished, "datetime") or field("Started", started, "datetime"),
            field("Duration", duration),
            steps_metric,
        ],
        details=[
            field("Job", job_name),
            field("Run", link(f"#{run.get('id')}", href), "link") if href else field("Run", run.get("id"), "code"),
            field("Status message", run.get("status_message")),
            field("Trigger", trigger.get("cause_humanized") or trigger.get("cause")),
            field("Started", started, "datetime"),
            field("Finished", finished, "datetime"),
            field("Git", git, "code"),
            field("Schedule (cron)", (job.get("schedule") or {}).get("cron"), "code"),
        ],
        tables=[steps_table],
        raw=run,
    )
