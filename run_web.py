"""Launch the local browser game; Node is needed only to build the frontend."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent


def running_game(url, state_dir):
    """Only reuse the same checkout and save directory, with a bounded probe."""
    from generic_chess.ui.web.identity import APPLICATION, instance_id
    try:
        with urllib.request.urlopen(url + "/api/health", timeout=.5) as response:
            health = json.loads(response.read(4096))
            return (response.status == 200 and isinstance(health, dict)
                    and health.get("ok") is True
                    and health.get("application") == APPLICATION
                    and health.get("instance_id") == instance_id(state_dir))
    except (OSError, ValueError):
        return False


def main():
    web_venv = ROOT / ".web-venv/Scripts/python.exe"
    venv = web_venv if web_venv.exists() else ROOT / ".venv/Scripts/python.exe"
    if importlib.util.find_spec("uvicorn") is None:
        if venv.exists() and Path(sys.executable).resolve() != venv.resolve():
            os.execv(str(venv), [str(venv), str(Path(__file__).resolve()), *sys.argv[1:]])
        print('请先安装 Web 依赖：python -m pip install -e ".[web]"', file=sys.stderr)
        return 1
    parser = argparse.ArgumentParser(description="GenericChess 本机网页游戏")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--state-dir", type=Path, default=ROOT / ".web_state")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("端口必须在 1–65535 之间")
    if not (ROOT / "web/dist/index.html").is_file():
        print("缺少前端构建。请在 web 目录运行 npm ci 和 npm run build。", file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{args.port}"
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", args.port))
        except OSError:
            if running_game(url, args.state_dir):
                print(f"游戏已经运行：{url}（使用已有服务）", flush=True)
                if not args.no_browser:
                    webbrowser.open(url)
                return 0
            print(f"端口 {args.port} 被其他服务或不同存档的游戏占用，请使用 --port 指定其他端口。", file=sys.stderr)
            return 1
    if not args.no_browser:
        def open_when_ready():
            for _ in range(100):
                try:
                    with urllib.request.urlopen(url + "/api/health", timeout=.2) as response:
                        if response.status == 200:
                            webbrowser.open(url)
                            return
                except OSError:
                    time.sleep(.1)
        threading.Thread(target=open_when_ready, daemon=True).start()
    import uvicorn
    from generic_chess.ui.web.app import create_app
    print(f"GenericChess 网页小游戏：{url}（Ctrl+C 停止）", flush=True)
    uvicorn.run(create_app(state_dir=args.state_dir), host="127.0.0.1", port=args.port, access_log=False)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
