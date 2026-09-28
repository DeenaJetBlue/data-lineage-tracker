"""Runs one source's collector for one table and wraps the outcome in a status card."""

import json
import logging
import re
import time
from datetime import datetime, timezone
from functools import lru_cache
from urllib.parse import urlparse

import requests

from . import settings
from .sources.base import ERROR, NOT_CONFIGURED, SourceError, card

log = logging.getLogger(__name__)

# Most specific first: ConnectTimeout and SSLError are also ConnectionErrors.
NETWORK_ERRORS = (
    (requests.exceptions.ConnectTimeout, "Timed out connecting to {host}"),
    (requests.exceptions.ReadTimeout, "{host} did not respond in time"),
    (requests.exceptions.SSLError, "TLS/SSL error talking to {host}"),
    (requests.exceptions.ConnectionError, "Could not connect to {host}"),
)


@lru_cache(maxsize=1)
def sample_data():
    return json.loads(settings.SAMPLE_DATA_FILE.read_text(encoding="utf-8"))


def run_source(source, params):
    """Check `source` with this table's `params` (None when the table doesn't configure it)."""
    started = time.perf_counter()
    try:
        result = _collect(source, params)
    except SourceError as exc:
        log.warning("%s check failed: %s", source.label, exc)
        result = _error_card(str(exc), exc.hint)
    except Exception as exc:  # whatever the SDKs raise: auth, DNS, timeouts, unexpected payloads
        message = _network_message(exc)
        if message:
            log.warning("%s check failed: %s", source.label, message)
        else:
            log.exception("%s check failed", source.label)
            first_line = (str(exc).strip().splitlines() or [""])[0][:400]
            message = f"{type(exc).__name__}: {first_line}" if first_line else type(exc).__name__
        result = _error_card(message, source.hint)

    result.update(
        source=source.key,
        name=source.label,
        subtitle=source.subtitle,
        class_name=source.class_name,
        test_script=source.test_script,
        config=params or {},
        demo=settings.DEMO_MODE,
        checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        elapsed_ms=round((time.perf_counter() - started) * 1000),
    )
    return result


def _collect(source, params):
    if params is None:
        return card(NOT_CONFIGURED, "This table has no rows for this source in the config table.",
                    status_label="Not configured")

    missing = [name for name in source.required if not params.get(name)]
    if missing:
        raise SourceError(f"Config table has no value for {', '.join(missing)}",
                          hint=f"Add the {source.name} rows to config/ConfigurationFile.csv.")

    if settings.DEMO_MODE:
        return source.module.summarize(sample_data()[source.key], params)

    env = settings.read_env(literal=source.literal_env)
    missing = [key for key in source.env_keys if not env.get(key)]
    if missing:
        raise SourceError(f"Missing in .env: {', '.join(missing)}",
                          hint="Add these credentials to the .env file in the project root.")
    return source.module.summarize(source.module.fetch(params, env), params)


def _network_message(exc):
    """One-line message for common requests failures; None for anything else."""
    for error_type, template in NETWORK_ERRORS:
        if isinstance(exc, error_type):
            url = getattr(getattr(exc, "request", None), "url", None)
            message = template.format(host=urlparse(url).hostname if url else "the server")
            # Keep the reason for TLS failures, e.g. "certificate verify failed: ..."
            reason = re.search(r"\] ([^\]]+?) \(_ssl", str(exc))
            return f"{message}: {reason.group(1)}" if reason else message
    return None


def _error_card(message, hint):
    result = card(ERROR, "The tracker could not check this source.", status_label="Couldn't check")
    result.update(error=message, hint=hint)
    return result
