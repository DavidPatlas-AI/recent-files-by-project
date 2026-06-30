#!/usr/bin/env python3
"""אייקון System Tray — פתיחה מהירה, קבצים אחרונים בתפריט."""

import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

from PIL import Image, ImageDraw
import pystray

BASE = Path(__file__).resolve().parent
SERVER = BASE / "recent_files_server.py"
URL = "http://localhost:8082/recent-files.html"
PORT = 8082
_icon_ref = None
LOCK_FILE = os.path.join(os.environ.get("TEMP", "."), "recent_files_tray.lock")


def single_instance() -> bool:
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                os.kill(int(f.read().strip()), 0)
            return False
        except (ProcessLookupError, ValueError, OSError):
            pass
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    return True


def port_open() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.4):
            return True
    except OSError:
        return False


def ensure_server() -> None:
    if port_open():
        return
    subprocess.Popen(
        [sys.executable, str(SERVER)],
        cwd=str(BASE),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    for _ in range(20):
        if port_open():
            return
        time.sleep(0.3)


def api_get(path: str) -> dict | list | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def api_open_file(path: str) -> None:
    q = urllib.parse.urlencode({"mode": "file", "path": path})
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/open?{q}", timeout=10)
    except Exception:
        pass


def fetch_recent() -> list[dict]:
    data = api_get("/api/files?days=3&limit=6&refresh=0")
    return (data or {}).get("files", []) if isinstance(data, dict) else []


def make_icon() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 4, 60, 60), radius=12, fill=(124, 106, 245, 255))
    d.rounded_rectangle((14, 18, 50, 46), radius=4, fill=(245, 200, 66, 255))
    d.rectangle((20, 26, 44, 30), fill=(20, 20, 30, 255))
    d.rectangle((20, 34, 38, 38), fill=(20, 20, 30, 180))
    return img


def open_dashboard(_icon=None, _item=None) -> None:
    ensure_server()
    threading.Thread(target=lambda: webbrowser.open(URL), daemon=True).start()


def refresh_scan(_icon=None, _item=None) -> None:
    ensure_server()
    threading.Thread(
        target=lambda: api_get("/api/files?days=7&limit=300&refresh=1"),
        daemon=True,
    ).start()
    update_tooltip()


def open_path(path: str):
    def handler(_i, _m):
        ensure_server()
        threading.Thread(target=lambda: api_open_file(path), daemon=True).start()
    return handler


def build_menu() -> pystray.Menu:
    files = fetch_recent()
    items = [
        pystray.MenuItem("פתח ממשק קבצים", open_dashboard, default=True),
        pystray.MenuItem("רענון סריקה", refresh_scan),
    ]
    if files:
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("אחרונים", pystray.Menu(*[
            pystray.MenuItem(
                f"{f.get('project_icon','')} {f['name'][:28]}",
                open_path(f["path"]),
            )
            for f in files[:6]
        ])))
    items.extend([pystray.Menu.SEPARATOR, pystray.MenuItem("יציאה", quit_app)])
    return pystray.Menu(*items)


def update_tooltip() -> None:
    global _icon_ref
    if not _icon_ref:
        return
    files = fetch_recent()
    if files:
        f = files[0]
        _icon_ref.title = f"קבצים אחרונים\n{f.get('project_icon','')} {f['name']}\n{f.get('project','')}"
    else:
        _icon_ref.title = "קבצים אחרונים — אין נתונים"
    _icon_ref.menu = build_menu()


def tooltip_loop() -> None:
    while True:
        time.sleep(60)
        try:
            update_tooltip()
        except Exception:
            pass


def quit_app(icon, _item=None) -> None:
    try:
        os.remove(LOCK_FILE)
    except OSError:
        pass
    icon.stop()


def main() -> None:
    global _icon_ref
    if not single_instance():
        return
    os.chdir(BASE)
    ensure_server()
    _icon_ref = pystray.Icon("recent_files", make_icon(), "קבצים אחרונים", build_menu())
    threading.Thread(target=tooltip_loop, daemon=True).start()
    _icon_ref.run()


if __name__ == "__main__":
    main()