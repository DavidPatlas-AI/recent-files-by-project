#!/usr/bin/env python3
"""מיקום סקין RecentFiles ליד YomiWidget ב-Rainmeter.ini"""

import re
import subprocess
from pathlib import Path

RAINMETER_INI = Path.home() / "AppData/Roaming/Rainmeter/Rainmeter.ini"
RAINMETER_EXE = Path(r"C:\Program Files\Rainmeter\Rainmeter.exe")
SKIN_W, SKIN_H = 440, 56
GAP = 10


def read_ini() -> str:
    return RAINMETER_INI.read_text(encoding="utf-16")


def write_ini(text: str) -> None:
    RAINMETER_INI.write_text(text, encoding="utf-16")


def get_yomi_pos(text: str) -> tuple[int, int]:
    m = re.search(r"\[YomiWidget\\YomiWidget\]\s*\n(.*?)((?:\n\[)|\Z)", text, re.S)
    x, y = 20, 20
    if m:
        block = m.group(1)
        xm = re.search(r"WindowX=(-?\d+)", block)
        ym = re.search(r"WindowY=(-?\d+)", block)
        if xm:
            x = int(xm.group(1))
        if ym:
            y = int(ym.group(1))
    return x, y + 600 + GAP


def ensure_recent_section(text: str) -> str:
    x, y = get_yomi_pos(text)
    section = (
        f"[RecentFiles\\RecentFiles]\n"
        f"Active=1\n"
        f"WindowX={x}\n"
        f"WindowY={y}\n"
        f"ClickThrough=0\n"
        f"Draggable=1\n"
        f"SnapEdges=1\n"
        f"KeepOnScreen=1\n"
        f"AlwaysOnTop=0\n"
    )
    if "[RecentFiles\\RecentFiles]" in text:
        text = re.sub(
            r"\[RecentFiles\\RecentFiles\].*?(?=\n\[|\Z)",
            section.strip(),
            text,
            flags=re.S,
        )
    else:
        text = text.rstrip() + "\n\n" + section
    return text


def activate_skin() -> None:
    if not RAINMETER_EXE.exists():
        return
    subprocess.run(
        [str(RAINMETER_EXE), "!ActivateConfig", "RecentFiles", "RecentFiles.ini"],
        check=False,
    )
    subprocess.run([str(RAINMETER_EXE), "!RefreshApp"], check=False)


def main():
    if not RAINMETER_INI.exists():
        print("Rainmeter.ini לא נמצא")
        return
    text = read_ini()
    text = ensure_recent_section(text)
    write_ini(text)
    x, y = get_yomi_pos(text)
    print(f"RecentFiles → X={x} Y={y} (מתחת ל-YomiWidget)")
    activate_skin()
    print("הופעל ב-Rainmeter")


if __name__ == "__main__":
    main()