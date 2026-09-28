"""Start the File Lifecycle tracker (backend API + frontend) on http://127.0.0.1:8000

    python run.py              live status from every system
    python run.py --demo       captured sample responses, no connections made
    python run.py --port 8080  another port
"""

import argparse
import os
import socket
import sys
from pathlib import Path

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent


def port_in_use(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        return probe.connect_ex(("127.0.0.1" if host == "0.0.0.0" else host, port)) == 0


def main():
    parser = argparse.ArgumentParser(description="Data Lineage Tracker - File Lifecycle")
    parser.add_argument("--host", default="127.0.0.1",
                        help="interface to listen on (default 127.0.0.1; use 0.0.0.0 to share on your network)")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default 8000)")
    parser.add_argument("--demo", action="store_true",
                        help="serve captured sample responses instead of calling the live systems")
    parser.add_argument("--reload", action="store_true", help="restart automatically when backend code changes")
    args = parser.parse_args()

    if port_in_use(args.host, args.port):
        sys.exit(f"Port {args.port} is already in use (is the tracker already running?). "
                 f"Try another one: python run.py --port {args.port + 1}")

    if args.demo:
        os.environ["LIFECYCLE_DEMO"] = "1"

    host = "localhost" if args.host in ("127.0.0.1", "0.0.0.0") else args.host
    mode = "SAMPLE DATA (demo)" if args.demo else "live"
    print(f"\n  File Lifecycle tracker ({mode}) -> http://{host}:{args.port}\n  Press Ctrl+C to stop.\n")

    uvicorn.run("backend.main:app", host=args.host, port=args.port, app_dir=str(PROJECT_ROOT),
                reload=args.reload, reload_dirs=[str(PROJECT_ROOT / "backend")] if args.reload else None)


if __name__ == "__main__":
    main()
