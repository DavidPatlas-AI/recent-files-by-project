#!/usr/bin/env python3
"""בדיקת סטטוס מערכת שולחן העבודה — שרת, Tray, Rainmeter."""

import json
import re
import socket
import urllib.request
from pathlib import Path

HOME = Path.home()
PORT = 8082


def check_port() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
            return True
    except OSError:
        return False


def check_api() -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=3) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def check_rainmeter() -> bool:
    ini = HOME / "AppData/Roaming/Rainmeter/Rainmeter.ini"
    if not ini.exists():
        return False
    try:
        text = ini.read_text(encoding="utf-16")
        return "[RecentFiles\\RecentFiles]" in text and "Active=1" in text.split("[RecentFiles\\RecentFiles]")[1][:200]
    except OSError:
        return False


import os


def main():
    lines = ["═══ סטטוס שולחן עבודה ═══", ""]
    srv = check_port()
    lines.append(f"{'✓' if srv else '✗'} שרת קבצים (פורט {PORT})")
    if srv:
        h = check_api()
        if h:
            lines.append(f"  · {h.get('files_cached', 0)} קבצים במטמון")
    lines.append(f"{'✓' if check_rainmeter() else '✗'} Rainmeter RecentFiles")
    for lock, label in [
        ("recent_files_tray.lock", "System Tray"),
        ("recent_files_hotkey.lock", "קיצור Win+Shift+F"),
        ("yomi_widget.lock", "YomiWidget"),
    ]:
        p = Path(os.environ.get("TEMP", "")) / lock
        lines.append(f"{'✓' if p.exists() else '○'} {label}")
    lines += ["", "ממשק: http://localhost:8082/recent-files.html"]
    print("\n".join(lines))


if __name__ == "__main__":
    main()