"""HVR hub jobs - same calls as Test/HVR_Jobs.py.

The Test script prints only RUNNING jobs; here every job is listed with its
state so stopped or failed ones stand out.
"""

import fnmatch
from collections import Counter

import requests

from .base import FAILED, SUCCESS, WARNING, card, column, field, http_error, pill, table

DEFAULT_API_VERSION = "v6.1.0.6"  # same defaults as Test/HVR_Jobs.py
DEFAULT_HUB = "hvrhub"
# Optional columns, shown when at least one job reports one of the keys.
OPTIONAL_COLUMNS = (
    ("channel", "Channel", ("channel", "chn")),
    ("location", "Location", ("location", "loc")),
    ("type", "Type", ("type", "job_type", "job_group")),
)
TONE_ORDER = {FAILED: 0, WARNING: 1, SUCCESS: 2}


def fetch(params, env):
    url = env["HVR_URL"].rstrip("/")
    session = requests.Session()

    response = session.post(f"{url}/auth/v1/password", headers={"Content-Type": "application/json"},
                            json={"username": env["HVR_USERNAME"], "password": env["HVR_PASSWORD"]}, timeout=15)
    if response.status_code != 200:
        raise http_error(response, "Authentication")
    token = response.json().get("access_token")

    version = env.get("HVR_API_VERSION") or DEFAULT_API_VERSION
    hub = params.get("Hub_Name") or env.get("HVR_HUB_NAME") or DEFAULT_HUB
    response = session.get(f"{url}/api/{version}/hubs/{hub}/jobs",
                           headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                           params={"fetch": "latency"}, timeout=30)
    if response.status_code != 200:
        raise http_error(response, "Jobs request")

    data = response.json()
    if isinstance(data, list):
        jobs = data
    elif isinstance(data, dict) and "jobs" in data:
        jobs = data.get("jobs") or []
    elif isinstance(data, dict):
        jobs = [{"name": name, **details} for name, details in data.items() if isinstance(details, dict)]
    else:
        jobs = []
    return {"hub": hub, "jobs": [job for job in jobs if isinstance(job, dict)]}


def state_tone(state):
    state = (state or "").upper()
    if state == "RUNNING":
        return SUCCESS
    if "FAIL" in state or "ERROR" in state:
        return FAILED
    return WARNING  # SUSPEND, PENDING, RETRY, ...


def _first(job, keys):
    return next((job[key] for key in keys if job.get(key) not in (None, "")), None)


def _latency(job):
    key = next((key for key in job if "latency" in key.lower()), None)
    value = job.get(key) if key else None
    if isinstance(value, dict):
        return ", ".join(f"{name} {amount}" for name, amount in value.items())
    return value


def summarize(raw, params):
    hub = raw.get("hub")
    pattern = params.get("Job_Filter") or "*"
    scope = "jobs" if pattern == "*" else f"jobs matching {pattern}"
    jobs = [job for job in raw.get("jobs") or []
            if fnmatch.fnmatchcase(str(job.get("name", "")).lower(), pattern.lower())]
    if not jobs:
        return card(WARNING, f"No {scope} on hub {hub}", status_label="No jobs")

    states = Counter(str(job.get("state") or "UNKNOWN").upper() for job in jobs)
    running = states.get("RUNNING", 0)
    failed = sum(count for state, count in states.items() if state_tone(state) == FAILED)
    if failed:
        tone, label = FAILED, f"{failed} failed"
    elif running == len(jobs):
        tone, label = SUCCESS, "All running"
    else:
        tone, label = WARNING, f"{len(jobs) - running} not running"

    rows = []
    for job in jobs:
        state = str(job.get("state") or "UNKNOWN").upper()
        row = {"name": job.get("name"), "state": pill(state, state_tone(state)), "latency": _latency(job)}
        for key, _label, keys in OPTIONAL_COLUMNS:
            row[key] = _first(job, keys)
        rows.append(row)
    # Problems first, then alphabetical
    rows.sort(key=lambda row: (TONE_ORDER[row["state"]["tone"]], str(row["name"])))

    columns = [column("name", "Job", "code"), column("state", "State", "pill")]
    columns += [column(key, label) for key, label, _keys in OPTIONAL_COLUMNS if any(row[key] for row in rows)]
    if any(row["latency"] not in (None, "") for row in rows):
        columns.append(column("latency", "Latency"))

    return card(
        tone,
        f"{running} of {len(jobs)} {scope} running on hub {hub}",
        status_label=label,
        metrics=[
            field("Jobs", len(jobs), "number"),
            field("Running", running, "number"),
            field("Not running", len(jobs) - running, "number"),
        ],
        details=[
            field("Hub", hub, "code"),
            field("Job filter", pattern, "code"),
            field("States", " · ".join(f"{state} {count}" for state, count in states.most_common())),
        ],
        tables=[table(f"Jobs ({len(jobs)})", columns, rows, open_=True)],
        raw={"hub": hub, "jobs": jobs},
    )
