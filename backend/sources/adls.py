"""ADLS landing folder - same calls as Test/AdlsFileStatus.py.

Service principal + Blob API, list every blob under Root_Folder, report the
file count and the most recent file.
"""

import heapq

from .base import SUCCESS, WARNING, card, column, field, table

RECENT_FILES = 10


def fetch(params, env):
    # Imported here so a missing Azure package only breaks this card, not the app.
    from azure.identity import ClientSecretCredential
    from azure.storage.blob import BlobServiceClient

    credential = ClientSecretCredential(
        tenant_id=env["ADLS_TENANT_ID"],
        client_id=env["ADLS_CLIENT_ID"],
        client_secret=env["ADLS_CLIENT_SECRET"],
    )
    account_url = f"https://{params['Storage_Account_Name']}.blob.core.windows.net"
    container = BlobServiceClient(account_url=account_url, credential=credential).get_container_client(
        params["Container_Name"]
    )

    total_files = 0
    total_bytes = 0
    newest = []  # min-heap of (last_modified, name, size), keeps the newest RECENT_FILES
    for blob in container.list_blobs(name_starts_with=params["Root_Folder"], include=["metadata"]):
        # Skip folder entries: "dir/" markers and, on hierarchical-namespace accounts,
        # zero-byte blobs flagged hdi_isfolder (their timestamps would pose as "latest file").
        if blob.name.endswith("/") or (blob.metadata or {}).get("hdi_isfolder") == "true":
            continue
        total_files += 1
        total_bytes += blob.size or 0
        entry = (blob.last_modified, blob.name, blob.size or 0)
        if len(newest) < RECENT_FILES:
            heapq.heappush(newest, entry)
        else:
            heapq.heappushpop(newest, entry)

    return {
        "total_files": total_files,
        "total_bytes": total_bytes,
        "recent_files": [
            {
                "name": name.split("/")[-1],
                "full_path": name,
                "size": size,
                "last_modified": modified.isoformat(timespec="milliseconds"),
            }
            for modified, name, size in sorted(newest, reverse=True)
        ],
    }


def summarize(raw, params):
    location = f"{params['Container_Name']}/{params['Root_Folder']}"
    files = raw.get("recent_files") or []
    if not files:
        return card(WARNING, f"No files found in {location}", status_label="No files")

    latest = files[0]
    total = raw.get("total_files", len(files))
    return card(
        SUCCESS,
        f"{total:,} file{'s' if total != 1 else ''} in {location}",
        status_label="Files found",
        metrics=[
            field("Files", total, "number"),
            field("Total size", raw.get("total_bytes"), "bytes"),
            field("Latest file", latest["last_modified"], "datetime"),
        ],
        details=[
            field("Most recent file", latest["name"], "code"),
            field("Full path", latest["full_path"], "code"),
            field("Size", latest["size"], "bytes"),
            field("Last modified", latest["last_modified"], "datetime"),
        ],
        tables=[
            table(
                f"Recent files ({len(files)})",
                [
                    column("name", "File", "code"),
                    column("size", "Size", "bytes"),
                    column("last_modified", "Modified", "datetime"),
                ],
                files,
            )
        ],
        raw={"total_files": total, "total_bytes": raw.get("total_bytes"), "most_recent_file": latest},
    )
