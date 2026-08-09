from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .core import SCOPES, Paths, configure_logging, daemon_lock, now, pid_alive, status, sync, write_status

TASK_NAME = "GenericChess Gmail Bridge"

def root() -> Path: return Path(__file__).resolve().parents[2]
def config_dir() -> Path: return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "GenericChessBridge"

def auth(args) -> int:
    from google_auth_oauthlib.flow import InstalledAppFlow
    cdir = config_dir(); cdir.mkdir(parents=True, exist_ok=True)
    client = Path(args.client).resolve() if args.client else cdir / "oauth-client.json"
    if not client.exists(): raise RuntimeError(f"OAuth client JSON not found: {client}")
    flow = InstalledAppFlow.from_client_secrets_file(str(client), SCOPES)
    creds = flow.run_local_server(port=0)
    (cdir / "token.json").write_text(creds.to_json(), encoding="utf-8")
    print(f"OAuth token saved in {cdir}"); return 0

def daemon(args) -> int:
    paths = Paths(root()); interval = args.interval
    configure_logging(paths)
    with daemon_lock(paths):
        write_status(paths, state="running", pid=os.getpid(), started_at=now(), last_poll_at=now(), last_success_at=None, last_error=None)
        stopping = False
        def stop_handler(*_):
            nonlocal stopping; stopping = True
        signal.signal(signal.SIGTERM, stop_handler); signal.signal(signal.SIGINT, stop_handler)
        while not stopping:
            write_status(paths, state="running", pid=os.getpid(), last_poll_at=now())
            try:
                sync(paths, config_dir()); write_status(paths, state="running", pid=os.getpid(), last_success_at=now(), last_error=None)
            except Exception as exc:
                logging.getLogger("gc_bridge").exception("courier poll failed")
                write_status(paths, state="running", pid=os.getpid(), last_error=str(exc))
            for _ in range(interval):
                if stopping: break
                time.sleep(1)
        write_status(paths, state="stopped", pid=os.getpid()); return 0

def ensure(args) -> int:
    paths = Paths(root()); current = status(paths, args.stale_seconds)
    if current["state"] == "HEALTHY": print("HEALTHY"); return 0
    pid = current.get("pid")
    if isinstance(pid, int):
        try: os.kill(pid, signal.SIGTERM)
        except OSError: pass
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and pid_alive(pid): time.sleep(0.1)
        if pid_alive(pid):
            raise RuntimeError("stale daemon did not stop safely")
    # Detach from the interactive command's process/job so ensure survives when
    # the invoking terminal exits (the normal Windows Agent workflow).
    flags = (getattr(subprocess, "CREATE_NO_WINDOW", 0) |
             getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) |
             getattr(subprocess, "DETACHED_PROCESS", 0))
    kwargs = {"creationflags": flags, "close_fds": True}
    subprocess.Popen([sys.executable, "-m", "generic_chess.bridge.cli", "run", "--interval", str(args.interval)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
    print("STARTED"); return 0

def stop(args) -> int:
    current = status(Paths(root()), args.stale_seconds); pid = current.get("pid")
    if not isinstance(pid, int): print("STOPPED"); return 0
    try: os.kill(pid, signal.SIGTERM); print("STOPPING")
    except OSError: print("STOPPED")
    return 0

def scheduler(args, uninstall=False) -> int:
    command = f'"{sys.executable}" -m generic_chess.bridge.cli run --interval {args.interval}'
    if uninstall:
        result = subprocess.run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"], capture_output=True, text=True)
    else:
        result = subprocess.run(["schtasks", "/Create", "/TN", TASK_NAME, "/SC", "ONLOGON", "/TR", command, "/RL", "LIMITED", "/F"], capture_output=True, text=True)
    if result.returncode: raise RuntimeError(result.stderr or result.stdout)
    print("UNINSTALLED" if uninstall else "INSTALLED"); return 0

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="gc-bridge"); parser.add_argument("--stale-seconds", type=int, default=90); parser.add_argument("--interval", type=int, default=20)
    sub = parser.add_subparsers(dest="command", required=True); auth_p = sub.add_parser("auth"); auth_p.add_argument("--client")
    for name in ("run", "status", "ensure", "sync", "stop", "install-autostart", "uninstall-autostart"): sub.add_parser(name)
    args = parser.parse_args(argv)
    try:
        if args.command == "auth": return auth(args)
        if args.command == "run": return daemon(args)
        if args.command == "status": print(json.dumps(status(Paths(root()), args.stale_seconds), indent=2)); return 0
        if args.command == "ensure": return ensure(args)
        if args.command == "sync": print(f"received={sync(Paths(root()), config_dir())}"); return 0
        if args.command == "stop": return stop(args)
        return scheduler(args, args.command == "uninstall-autostart")
    except Exception as exc:
        logging.basicConfig(level=logging.ERROR); logging.exception("gc-bridge failed"); write_status(Paths(root()), state="error", last_error=str(exc), last_poll_at=now()); return 1

if __name__ == "__main__": raise SystemExit(main())
