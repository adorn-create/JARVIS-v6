@echo off
cd /d "%~dp0"
title JARVIS
if not exist .venv\Scripts\python.exe (
 echo Run SETUP.bat first.
 pause
 exit /b 1
)
.venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 13) else 1)"
if errorlevel 1 (
 echo JARVIS requires Python 3.11 or 3.12. This virtual environment uses:
 .venv\Scripts\python.exe --version
 echo Rename the .venv folder and run SETUP.bat again.
 pause
 exit /b 1
)
.venv\Scripts\python.exe src\main.py
