@echo off
cd /d "%~dp0"
title JARVIS
if not exist .venv\Scripts\python.exe (
 echo Run SETUP.bat first.
 pause
 exit /b 1
)
.venv\Scripts\python.exe src\main.py
