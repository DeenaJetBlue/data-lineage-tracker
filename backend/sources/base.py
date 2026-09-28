"""Building blocks every source collector uses to describe its result.

A collector returns one JSON "card" per source. The frontend renders cards
generically, so each value carries a `format` telling it how to display:
text, code, number, compact, bytes, datetime, link, pill, json.
"""

import re
from datetime import datetime, timezone

# Card statuses (the frontend maps each to a colour, icon and label)
SUCCESS = "success"                # healthy: files found / latest run succeeded
RUNNING = "running"                # a run is in progress
WARNING = "warning"                # reachable, but needs a look (no data, cancelled, some jobs down)
FAILED = "failed"                  # the pipeline itself failed
ERROR = "error"                    # the tracker could not check (auth, network, bad config)
NOT_CONFIGURED = "not_configured"  # this table has no rows for the source


class SourceError(Exception):
    """A readable failure to show on the card, with an optional hint for fixing it."""

    def __init__(self, message: str, hint: str = None):
        super().__init__(message)
        self.hint = hint


def card(status, summary, status_label=None, metrics=(), details=(), tables=(), raw=None):
    return {
        "status": status,
        "status_label": status_label,
        "summary": summary,
        "metrics": [m for m in metrics if m],
        "details": [d for d in details if d],
        "tables": [t for t in tables if t],
        "raw": raw,
        "error": None,  # set, with a hint, when the source could not be checked
        "hint": None,
    }


def field(label, value, fmt="text"):
    """One labelled value: used for stat tiles (metrics) and detail rows alike.

    Returns None for empty values so callers can list optional fields freely.
    """
    if value is None or value == "":
        return None
    return {"label": label, "value": value, "format": fmt}


def column(key, label, fmt="text"):
    return {"key": key, "label": label, "format": fmt}


def table(title, columns, rows, open_=False):
    return {"title": title, "columns": columns, "rows": rows, "open": open_}


def pill(text, tone):
    return {"text": text, "tone": tone}


def link(text, href):
    return {"text": text, "href": href}


def iso(value):
    """Normalise a datetime (or datetime string) to ISO-8601 with millisecond precision.

    Timezone-aware inputs keep their offset; naive ones stay naive, and the
    frontend labels those as server time instead of guessing a zone.
    """
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip().replace(" ", "T", 1)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        # Python < 3.11 only parses 3 or 6 fractional digits; .NET emits 7.
        text = re.sub(r"(\.\d{6})\d+", r"\1", text)
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return str(value)
    return dt.isoformat(timespec="milliseconds")


def epoch_to_iso(seconds):
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat(timespec="milliseconds")


def parse_time(value):
    """Parse an ISO string back to a datetime for arithmetic; None if impossible."""
    normalised = iso(value)
    try:
        return datetime.fromisoformat(normalised) if normalised else None
    except ValueError:
        return None


def duration_text(seconds):
    if seconds is None:
        return None
    seconds = int(seconds)  # truncate, as dbt Cloud and the ADF portal do
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def seconds_between(start, end):
    start_dt, end_dt = parse_time(start), parse_time(end)
    if not start_dt or not end_dt or (start_dt.tzinfo is None) != (end_dt.tzinfo is None):
        return None
    return (end_dt - start_dt).total_seconds()


def lookback_hours(params, default):
    value = params.get("Lookback_Hours")
    if not value:
        return default
    try:
        hours = float(value)
    except ValueError:
        raise SourceError(f"Lookback_Hours must be a number, got '{value}'")
    if hours <= 0:
        raise SourceError(f"Lookback_Hours must be greater than 0, got '{value}'")
    return hours


def hours_text(hours):
    return f"{hours:g} hour" + ("" if hours == 1 else "s")


def http_error(response, action):
    """SourceError for a non-success HTTP response, with a short body excerpt."""
    body = (response.text or "").strip().replace("\n", " ")
    excerpt = f": {body[:300]}" if body else ""
    return SourceError(f"{action} failed (HTTP {response.status_code}){excerpt}")
