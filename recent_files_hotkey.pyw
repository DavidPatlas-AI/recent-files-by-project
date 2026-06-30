#!/usr/bin/env python3
"""קיצור גלובלי Win+Shift+F — פתיחת ממשק קבצים אחרונים."""

import ctypes
import os
import socket
import subprocess
import sys
import webbrowser
from ctypes import wintypes
from pathlib import Path

BASE = Path(__file__).resolve().parent
SERVER = BASE / "recent_files_server.py"
URL = "http://localhost:8082/recent-files.html"
PORT = 8082
LOCK = os.path.join(os.environ.get("TEMP", "."), "recent_files_hotkey.lock")

MOD_WIN = 0x0008
MOD_SHIFT = 0x0004
VK_F = 0x46
WM_HOTKEY = 0x0312
HOTKEY_ID = 1


def single_instance() -> bool:
    if os.path.exists(LOCK):
        try:
            with open(LOCK) as f:
                os.kill(int(f.read().strip()), 0)
            return False
        except (ProcessLookupError, ValueError, OSError):
            pass
    with open(LOCK, "w") as f:
        f.write(str(os.getpid()))
    return True


def port_open() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.3):
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


def open_dashboard() -> None:
    ensure_server()
    webbrowser.open(URL)


def main() -> None:
    if not single_instance():
        return
    user32 = ctypes.windll.user32
    if not user32.RegisterHotKey(None, HOTKEY_ID, MOD_WIN | MOD_SHIFT, VK_F):
        return
    msg = wintypes.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                open_dashboard()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    finally:
        user32.UnregisterHotKey(None, HOTKEY_ID)
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()