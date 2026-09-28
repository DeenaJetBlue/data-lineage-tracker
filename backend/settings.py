"""Paths and credentials shared by the backend."""

import os
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
CONFIG_TABLE_FILE = PROJECT_ROOT / "config" / "ConfigurationFile.csv"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
SAMPLE_DATA_FILE = Path(__file__).resolve().parent / "sample_data.json"

# `python run.py --demo` sets this: every source then returns captured sample responses.
DEMO_MODE = os.getenv("LIFECYCLE_DEMO", "").strip().lower() in ("1", "true", "yes")


def read_env(literal=False) -> dict:
    """Credentials from .env, read straight from the file (never os.environ).

    On Windows the OS already defines USERNAME, which would shadow the MOVEit
    USERNAME from .env if we went through os.environ.

    literal=False parses like python-dotenv (quotes, inline comments, ${VAR}), as the
    load_dotenv-based Test scripts do. literal=True keeps everything after the first
    '=' as-is, exactly like the MOVEit Test scripts, so a password containing ' #'
    or '${' reaches MOVEit unchanged.
    """
    if not ENV_FILE.exists():
        return {}
    if not literal:
        return {key: (value or "").strip() for key, value in dotenv_values(ENV_FILE).items()}

    values = {}
    with open(ENV_FILE) as handle:  # default encoding, as in the Test scripts
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values
