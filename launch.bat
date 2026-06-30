@echo off
chcp 65001 >nul
cd /d "%~dp0"
netstat -ano 2>nul | findstr /C:":8082 " | findstr LISTENING >nul
if %errorlevel%==0 (
    start "" "http://localhost:8082/recent-files.html"
    exit /b 0
)
start "" "http://localhost:8082/recent-files.html"
python "%~dp0recent_files_server.py"
pause