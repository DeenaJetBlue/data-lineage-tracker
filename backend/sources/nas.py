"""NAS share - same walk as Test/NASFileStatus.py.

Walks Root_Folder (a Windows UNC path) with the logged-in user's access and
reports the file count and the most recent file.
"""

import heapq
import os
import sys

from .base import SUCCESS, WARNING, SourceError, card, column, epoch_to_iso, field, table

RECENT_FILES = 10


def fetch(params, env):
    folder = params["Root_Folder"]
    if not os.path.isdir(folder):
        hint = "Check the path and that your Windows account can open it in File Explorer."
        if sys.platform != "win32" and folder.startswith("\\\\"):
            hint = "UNC paths (\\\\server\\share) only resolve on Windows - run the tracker on the AVD."
        raise SourceError(f"Folder does not exist or is not accessible: {folder}", hint=hint)

    total_files = 0
    newest = []  # min-heap of (mtime, name, path, size), keeps the newest RECENT_FILES
    for root, _dirs, files in os.walk(folder):
        for name in files:
            total_files += 1
            path = os.path.join(root, name)
            try:
                stat = os.stat(path)
            except OSError:
                continue
            entry = (stat.st_mtime, name, path, stat.st_size)
            if len(newest) < RECENT_FILES:
                heapq.heappush(newest, entry)
            else:
                heapq.heappushpop(newest, entry)

    return {
        "total_files": total_files,
        "recent_files": [
            {"name": name, "path": path, "size": size, "modified": epoch_to_iso(mtime)}
            for mtime, name, path, size in sorted(newest, reverse=True)
        ],
    }


def summarize(raw, params):
    folder = params["Root_Folder"]
    files = raw.get("recent_files") or []
    if not files:
        return card(WARNING, f"No files found in {folder}", status_label="No files")

    latest = files[0]
    total = raw.get("total_files", len(files))
    return card(
        SUCCESS,
        f"{total:,} file{'s' if total != 1 else ''} in {folder}",
        status_label="Files found",
        metrics=[
            field("Files", total, "number"),
            field("Latest file", latest["modified"], "datetime"),
        ],
        details=[
            field("Most recent file", latest["name"], "code"),
            field("Path", latest["path"], "code"),
            field("Size", latest.get("size"), "bytes"),
            field("Modified", latest["modified"], "datetime"),
        ],
        tables=[
            table(
                f"Recent files ({len(files)})",
                [
                    column("name", "File", "code"),
                    column("size", "Size", "bytes"),
                    column("modified", "Modified", "datetime"),
                ],
                files,
            )
        ],
        raw={"folder_path": folder, "total_files": total, "most_recent_file": latest},
    )
