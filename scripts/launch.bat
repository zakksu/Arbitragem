@echo off
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" (
  echo [launch] Creating environment...
  python scripts\dev.py setup
)
.venv\Scripts\python.exe scripts\launch.py
pause
