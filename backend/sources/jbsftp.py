"""JbSftp (MOVEit Transfer) folder - same calls as Test/MoveIT_JbSftp.py.

Uses the curl binary rather than requests: jbsftp resets Python's TLS
connections on the AVD while Windows curl.exe works.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode

from .base import SUCCESS, WARNING, SourceError, card, column, field, table

RECENT_FILES = 10
# MOVEit spells the upload time differently across versions; take the first one present.
TIME_KEYS = ("uploadStamp", "uploadstamp", "modificationTime", "modificationtime")


def curl_binary():
    # Like the Test script's bare "curl.exe", which Windows resolves from System32 before PATH:
    # the built-in curl uses Windows TLS, while conda's or Git's OpenSSL build may hit the reset.
    if sys.platform == "win32":
        builtin = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "curl.exe"
        if builtin.exists():
            return str(builtin)
    return shutil.which("curl.exe") or shutil.which("curl")


def curl(method, url, headers=None, data=None):
    """Run curl and return (status_code, body)."""
    binary = curl_binary()
    if not binary:
        raise SourceError("curl was not found on PATH", hint="Windows 10+ ships curl.exe in C:\\Windows\\System32.")

    command = [binary, "--silent", "--show-error", "--insecure", "--max-time", "60",
               "--request", method, url, "--write-out", "\n%{http_code}"]
    for name, value in (headers or {}).items():
        command += ["--header", f"{name}: {value}"]
    for name, value in (data or {}).items():
        command += ["--data-urlencode", f"{name}={value}"]

    # Decode as UTF-8 ourselves: text=True would use the Windows ANSI code page and garble file names.
    result = subprocess.run(command, capture_output=True)
    if result.returncode:
        raise SourceError(f"curl failed: {result.stderr.decode('utf-8', errors='replace').strip()}",
                          hint="jbsftp is reachable only from the AVD network.")

    body, _, status = result.stdout.decode("utf-8", errors="replace").rpartition("\n")
    return int(status), body


def fetch(params, env):
    server = env["TRANSFER_SERVER"].strip().rstrip("/")
    if not server.startswith(("http://", "https://")):
        server = f"https://{server}"

    status, body = curl("POST", f"{server}/api/v1/token", data={
        "grant_type": "password",
        "username": env["TUSERNAME"],
        "password": env["TPASSWORD"],
    })
    if status != 200:
        raise SourceError(f"Access token request failed (HTTP {status})",
                          hint="Check TUSERNAME / TPASSWORD in .env.")
    token = json.loads(body).get("access_token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # /api/v1/files ignores folderPath and lists every folder the user can see, so list the folder itself.
    folder_id = find_folder_id(server, headers, params["Root_Folder"])
    query = urlencode({
        "page": 1,
        "perPage": 100,
        "sortField": "uploadstamp",
        "sortDirection": "desc",
    })
    status, body = curl("GET", f"{server}/api/v1/folders/{folder_id}/files?{query}", headers=headers)
    if status != 200:
        raise SourceError(f"File listing failed (HTTP {status}): {body[:300]}")

    data = json.loads(body)
    return {"items": data.get("items") or [], "paging": data.get("paging"), "totalCount": data.get("totalCount")}


def find_folder_id(server, headers, folder):
    """Look the folder up by its path, then by its name, and return the ID of the exact path match."""
    path = "/" + folder.replace("\\", "/").strip("/")
    for key, value in (("path", path), ("name", path.rsplit("/", 1)[-1])):
        status, body = curl("GET", f"{server}/api/v1/folders?{urlencode({key: value, 'perPage': 100})}", headers=headers)
        if status != 200:
            raise SourceError(f"Folder lookup failed (HTTP {status}): {body[:300]}")
        for item in json.loads(body).get("items") or []:
            if _normalise(item.get("path")) == _normalise(folder):
                return item["id"]
    raise SourceError(f"Folder {folder} was not found on the MOVEit server",
                      hint="Root_Folder must be the folder's full MOVEit path, and TUSERNAME must have access to it.")


def _normalise(path):
    return str(path or "").replace("\\", "/").strip("/").lower()


def _in_folder(item, folder):
    path, base = _normalise(item.get("path")), _normalise(folder)
    return path == base or path.startswith(base + "/")


def summarize(raw, params):
    folder = params["Root_Folder"]
    items = raw.get("items") or []
    total = (raw.get("paging") or {}).get("totalItems") or raw.get("totalCount") or len(items)

    # Items carry their full path; if the API returned files from other folders,
    # keep only this folder's and say so (the count then covers the latest 100 uploads only).
    outside = [item for item in items if item.get("path") and not _in_folder(item, folder)]
    if outside:
        items = [item for item in items if not item.get("path") or _in_folder(item, folder)]
        total = len(items)

    if not items:
        note = " (the API returned files from other folders only)" if outside else ""
        return card(WARNING, f"No files found in {folder}{note}", status_label="No files")

    files = [
        {
            "name": item.get("name"),
            "size": item.get("size"),
            "uploaded": next((item[key] for key in TIME_KEYS if item.get(key)), None),
            "path": item.get("path"),
            "id": item.get("id"),
        }
        for item in items[:RECENT_FILES]
    ]
    latest = files[0]
    count_text = f"{total:,} file{'s' if total != 1 else ''}"
    summary = f"{count_text} in {folder}"
    if outside:
        summary += f" (among the latest uploads; {len(outside)} from other folders hidden)"

    return card(
        SUCCESS,
        summary,
        status_label="Files found",
        metrics=[
            field("Files", total, "number"),
            field("Latest size", latest["size"], "bytes"),
            field("Latest upload", latest["uploaded"], "datetime"),
        ],
        details=[
            field("Most recent file", latest["name"], "code"),
            field("Path", latest["path"], "code"),
            field("Size", latest["size"], "bytes"),
            field("Uploaded", latest["uploaded"], "datetime"),
            field("File ID", latest["id"], "code"),
        ],
        tables=[
            table(
                f"Recent files ({len(files)})",
                [
                    column("name", "File", "code"),
                    column("size", "Size", "bytes"),
                    column("uploaded", "Uploaded", "datetime"),
                ],
                files,
            )
        ],
        raw={"total_files": total, "most_recent_file": items[0]},
    )
