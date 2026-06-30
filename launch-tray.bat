@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" pythonw "%~dp0recent_files_tray.pyw"