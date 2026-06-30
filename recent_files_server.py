#!/usr/bin/env python3
"""שרת מקומי — סריקת קבצים אחרונים ומיפוי לפרויקטים."""

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOME = Path.home()
BASE = Path(__file__).resolve().parent
DESKTOP = HOME / "Desktop"
REVIEW = BASE
PROJECTS = DESKTOP / "פרויקטים"
PORT = 8082

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    ".wwebjs_auth", ".netlify", "portfolio-git-temp",
    "AppData", "Application Data", "Local Settings",
    "Microsoft", "Windows", "Program Files", "Program Files (x86)",
    "ProgramData", "$Recycle.Bin", "System Volume Information",
    ".cursor", ".grok", "Cache", "Caches", "Temp", "tmp",
}
SKIP_FILE_RE = re.compile(
    r"(Thumbs\.db|desktop\.ini|\.DS_Store|\.lock$|\.tmp$|\.log$|deepseek_html_|deepseek_python_)",
    re.I,
)

PROJECT_ICONS = {
    "מתמטיקה לחרדים מוכן": "🎓", "מסלול רכב": "🔧",
    "האלגוריתום שחזר בתשובה": "📎", "יומי": "🕍",
    "ויג'דים לשולחן עבודה": "🕍", "רחפנים": "🔌",
    "etrog-ai-studio": "🍋", "green-tech-farm": "🌱",
    "mishnat-yosef": "📘", "YomiWidget": "🕍",
    "adhd_home": "🕍", "בודק אתרוגים": "🍋",
    "מזהה רגשות": "😊", "פוליגרף דיגיטלי": "🔍",
    "פטלס משחקים": "🎮", "משחקים לילדים": "👶",
    "הכל בכסף": "💰", "שופר": "📯", "משחק כבלים": "🔌",
    "בונה פארק שעשועים": "🎢", "יצירת תוכן ויראלי לפי טרנדים": "📈",
    "מבחן דפר": "📘", "ID מפענח ובודק": "🛡️",
    "חממה דיגיטלית": "🌿", "CyberOS": "💻", "CableVitality": "🔌",
    "BridgeOS": "🌉", "terminals": "💻",
}

MAX_DEPTH = 12
CONFIG_FILE = REVIEW / "recent_files_config.json"
DEFAULT_CONFIG = {
    "extra_folders": [],
    "exclude_folders": [],
    "project_aliases": {},
    "watch_interval_sec": 120,
    "notify_windows": True,
    "scan_limit": 500,
    "scan_days_default": 30,
}

STATE_FILE = REVIEW / ".recent_files_state.json"
_state_lock = threading.Lock()
_cache = {"files": [], "projects": [], "scanned_at": None, "scan_ms": 0, "new_files": []}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, json.JSONDecodeError):
        pass
    return cfg


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_state() -> float:
    with _state_lock:
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return float(json.load(f).get("last_scan_ts", 0))
        except (OSError, json.JSONDecodeError, ValueError):
            return 0.0


def save_state(ts: float) -> None:
    with _state_lock:
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_scan_ts": ts}, f)
        except OSError:
            pass


def file_times(path: Path) -> tuple[float, float]:
    st = path.stat()
    created = getattr(st, "st_birthtime", st.st_ctime)
    return created, st.st_mtime


def should_skip_dir(name: str, cfg: dict | None = None) -> bool:
    if name in SKIP_DIRS or name.startswith("."):
        return True
    if cfg and name in cfg.get("exclude_folders", []):
        return True
    return False


def discover_projects() -> list[dict]:
    cfg = load_config()
    roots: list[tuple[Path, str, str]] = []

    def add_root(path: Path, label: str | None = None):
        if path.exists() and path.is_dir():
            name = label or path.name
            roots.append((path.resolve(), name, PROJECT_ICONS.get(name, "📁")))

    if PROJECTS.exists():
        for d in sorted(PROJECTS.iterdir()):
            if d.is_dir() and not should_skip_dir(d.name, cfg):
                add_root(d)

    if REVIEW.exists():
        for d in sorted(REVIEW.iterdir()):
            if d.is_dir() and not should_skip_dir(d.name, cfg):
                add_root(d)

    add_root(DESKTOP / "mishnat-yosef")
    add_root(HOME / "Documents" / "Rainmeter" / "Skins" / "YomiWidget", "YomiWidget")
    for extra in cfg.get("extra_folders", []):
        add_root(Path(extra))

    aliases = {
        str((PROJECTS / "מתמטיקה לחרדים מוכן").resolve()): "מתמטיקה לחרדים",
        str((PROJECTS / "האלגוריתום שחזר בתשובה").resolve()): "האלגוריתם שחזר בתשובה",
        str((REVIEW / "adhd_home").resolve()): "YomiWidget",
    }
    for folder_name, display in cfg.get("project_aliases", {}).items():
        for base in (PROJECTS, REVIEW, DESKTOP):
            p = base / folder_name
            if p.exists():
                aliases[str(p.resolve())] = display

    projects = []
    for path, name, icon in sorted(roots, key=lambda x: len(str(x[0])), reverse=True):
        display = aliases.get(str(path), cfg.get("project_aliases", {}).get(name, name))
        projects.append({
            "id": name,
            "name": display,
            "icon": icon,
            "path": str(path),
        })
    return projects


def match_project(file_path: Path, projects: list[dict]) -> dict:
    resolved = str(file_path.resolve())
    for p in projects:
        root = p["path"]
        if resolved.startswith(root + os.sep) or resolved.startswith(root + "/"):
            return p

    parent = file_path.parent.name
    if file_path.parent == DESKTOP:
        return {"id": "desktop", "name": "שולחן עבודה", "icon": "🖥️", "path": str(DESKTOP)}
    if "Downloads" in str(file_path.parent):
        return {"id": "downloads", "name": "הורדות", "icon": "⬇️", "path": str(HOME / "Downloads")}
    if "Documents" in str(file_path.parent) and "Rainmeter" in str(file_path):
        return {"id": "rainmeter", "name": "Rainmeter", "icon": "🕍", "path": ""}
    return {"id": "other", "name": parent or "אחר", "icon": "📄", "path": str(file_path.parent)}


def build_scan_roots() -> list[Path]:
    cfg = load_config()
    roots: list[Path] = [DESKTOP / "mishnat-yosef", HOME / "Downloads"]
    rainmeter = HOME / "Documents" / "Rainmeter" / "Skins"
    if rainmeter.exists():
        roots.append(rainmeter)

    for base in (PROJECTS, REVIEW):
        if not base.exists():
            continue
        for d in base.iterdir():
            if d.is_dir() and not should_skip_dir(d.name, cfg):
                roots.append(d)

    docs = HOME / "Documents"
    docs_skip = {"Rainmeter", "Codex", "My Music", "My Pictures", "My Videos", "Zoom"}
    if docs.exists():
        for d in docs.iterdir():
            if d.is_dir() and d.name not in SKIP_DIRS and d.name not in docs_skip:
                if not d.name.startswith("."):
                    roots.append(d)

    if DESKTOP.exists():
        for item in DESKTOP.iterdir():
            if item.is_file():
                roots.append(item)
            elif item.is_dir() and item.name not in {
                "פרויקטים", "_לסקירה", "terminals", "node_modules",
            } and not should_skip_dir(item.name, cfg):
                roots.append(item)

    for extra in cfg.get("extra_folders", []):
        p = Path(extra)
        if p.exists():
            roots.append(p)

    seen: set[str] = set()
    unique: list[Path] = []
    for r in roots:
        key = str(r.resolve()) if r.exists() else str(r)
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def scan_files(days: int = 30, limit: int = 500) -> list[dict]:
    projects = discover_projects()
    cutoff = time.time() - days * 86400
    results: list[dict] = []
    cap = limit * 3

    def scan_file(fpath: Path):
        if not fpath.is_file() or SKIP_FILE_RE.search(fpath.name):
            return
        try:
            created, modified = file_times(fpath)
            st = fpath.stat()
        except (OSError, PermissionError):
            return
        if max(created, modified) < cutoff:
            return
        proj = match_project(fpath, projects)
        results.append({
            "name": fpath.name,
            "path": str(fpath),
            "folder": str(fpath.parent),
            "created": datetime.fromtimestamp(created).isoformat(),
            "modified": datetime.fromtimestamp(modified).isoformat(),
            "created_ts": created,
            "modified_ts": modified,
            "size": st.st_size,
            "ext": fpath.suffix.lower().lstrip(".") or "—",
            "project": proj["name"],
            "project_icon": proj["icon"],
            "project_id": proj["id"],
        })

    def walk(root: Path, depth: int = 0):
        if depth > MAX_DEPTH or len(results) >= cap:
            return
        if root.is_file():
            scan_file(root)
            return
        if not root.is_dir():
            return
        try:
            entries = list(root.iterdir())
        except (OSError, PermissionError):
            return
        for entry in entries:
            if len(results) >= cap:
                return
            if entry.is_file():
                scan_file(entry)
            elif entry.is_dir() and not should_skip_dir(entry.name):
                walk(entry, depth + 1)

    for root in build_scan_roots():
        walk(root)

    results.sort(key=lambda x: x["created_ts"], reverse=True)
    return results[:limit], projects


def watch_interval() -> int:
    return int(load_config().get("watch_interval_sec", 120))


def notify_windows(title: str, message: str) -> None:
    if not load_config().get("notify_windows", True):
        return
    if sys.platform != "win32":
        return
    t = title.replace("'", "''").replace("`", "``")
    m = message.replace("'", "''").replace("`", "``").replace("\n", " | ")
    ps = (
        f"$n=New-Object System.Windows.Forms.NotifyIcon;"
        f"$n.Icon=[System.Drawing.SystemIcons]::Information;"
        f"$n.Visible=$true;"
        f"$n.ShowBalloonTip(6000,'{t}','{m}',[System.Windows.Forms.ToolTipIcon]::Info);"
        f"Start-Sleep -Milliseconds 6500;$n.Dispose()"
    )
    try:
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-Command",
             "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; " + ps],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        pass


def run_background_watch() -> None:
    time.sleep(10)
    while True:
        try:
            last_scan_ts = load_state()
            scan_ts = time.time()
            files, projects = scan_files(days=7, limit=300)
            new_files = []
            if last_scan_ts > 0:
                new_files = [
                    f for f in files
                    if f["created_ts"] > last_scan_ts or f["modified_ts"] > last_scan_ts
                ]
            save_state(scan_ts)
            _cache.update({
                "files": files,
                "projects": projects,
                "scanned_at": datetime.now().isoformat(),
                "scan_ms": 0,
                "new_files": new_files,
            })
            if new_files:
                names = ", ".join(f["name"] for f in new_files[:3])
                extra = f" (+{len(new_files)-3})" if len(new_files) > 3 else ""
                notify_windows(
                    f"{len(new_files)} קבצים חדשים",
                    f"{names}{extra}",
                )
        except Exception:
            pass
        time.sleep(watch_interval())


def fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REVIEW), **kwargs)

    def log_message(self, fmt, *args):
        if "/api/" not in (args[0] if args else ""):
            super().log_message(fmt, *args)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/config":
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            cfg = load_config()
            cfg.update(data)
            save_config(cfg)
            body = json.dumps({"ok": True, "config": cfg}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/rainmeter":
            files = _cache["files"]
            if not files:
                files, _ = scan_files(days=1, limit=20)
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            today = [f for f in files if f["created_ts"] >= today_start]
            if today:
                f = today[0]
                text = f"{len(today)} קבצים היום · {f['name']} ({f['project']})"
            elif files:
                f = files[0]
                text = f"אחרון: {f['name']} ({f['project']})"
            else:
                text = "אין קבצים — הפעל שרת"
            body = text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/config":
            body = json.dumps(load_config(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/open":
            qs = parse_qs(parsed.query)
            target = qs.get("path", [""])[0]
            mode = qs.get("mode", ["file"])[0]
            ok, msg = self._open_path(target, mode)
            body = json.dumps({"ok": ok, "msg": msg}, ensure_ascii=False).encode("utf-8")
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/files":
            qs = parse_qs(parsed.query)
            days = int(qs.get("days", ["30"])[0])
            limit = int(qs.get("limit", ["500"])[0])
            force = qs.get("refresh", ["0"])[0] == "1"

            new_files: list[dict] = []
            if force or not _cache["files"]:
                t0 = time.time()
                last_scan_ts = load_state() if force else 0.0
                scan_ts = time.time()
                files, projects = scan_files(days=days, limit=limit)
                if last_scan_ts > 0:
                    new_files = [
                        f for f in files
                        if f["created_ts"] > last_scan_ts or f["modified_ts"] > last_scan_ts
                    ]
                    if new_files and qs.get("notify", ["0"])[0] == "1":
                        names = ", ".join(f["name"] for f in new_files[:3])
                        extra = f" (+{len(new_files)-3})" if len(new_files) > 3 else ""
                        notify_windows(f"{len(new_files)} קבצים חדשים", f"{names}{extra}")
                save_state(scan_ts)
                _cache.update({
                    "files": files,
                    "projects": projects,
                    "scanned_at": datetime.now().isoformat(),
                    "scan_ms": int((time.time() - t0) * 1000),
                    "new_files": new_files,
                })
            else:
                new_files = _cache.get("new_files", [])

            payload = {
                "files": _cache["files"],
                "projects": _cache["projects"],
                "scanned_at": _cache["scanned_at"],
                "scan_ms": _cache["scan_ms"],
                "total": len(_cache["files"]),
                "new_count": len(new_files),
                "new_files": new_files[:30],
            }
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path in ("/", "/recent-files", "/recent-files.html"):
            self.path = "/recent-files.html"
        return super().do_GET()

    def _open_path(self, target: str, mode: str) -> tuple[bool, str]:
        if not target:
            return False, "חסר נתיב"
        path = Path(target).resolve()
        home = HOME.resolve()
        if not str(path).startswith(str(home)):
            return False, "נתיב לא מורשה"
        try:
            if mode == "folder":
                folder = path if path.is_dir() else path.parent
                if sys.platform == "win32":
                    subprocess.Popen(["explorer", str(folder)])
                else:
                    subprocess.Popen(["xdg-open", str(folder)])
                return True, str(folder)
            if not path.is_file():
                return False, "קובץ לא נמצא"
            if sys.platform == "win32":
                os.startfile(str(path))
            else:
                subprocess.Popen(["xdg-open", str(path)])
            return True, str(path)
        except OSError as e:
            return False, str(e)


def main():
    os.chdir(REVIEW)
    threading.Thread(target=run_background_watch, daemon=True).start()
    print(f"קבצים אחרונים — http://localhost:{PORT}/recent-files.html")
    print(f"מעקב ברקע כל {watch_interval()} שניות + התראות Windows")
    print("Ctrl+C לעצירה")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()