@echo off
setlocal
cd /d "%~dp0"
title JARVIS - Setup
color 0B
echo ========================================
echo       JARVIS ORGANIZED INSTALLER
echo ========================================
where py >nul 2>&1
if errorlevel 1 (
  where uv >nul 2>&1
  if errorlevel 1 (
    echo Python launcher or uv was not found. Install Python 3.11 or 3.12 and enable PATH.
    pause
    exit /b 1
  )
)
if not exist .venv\Scripts\python.exe call :create_venv
if errorlevel 1 goto fail
if not exist .venv\Scripts\python.exe goto fail
.venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 13) else 1)"
if errorlevel 1 (
  echo This virtual environment uses an unsupported Python version:
  .venv\Scripts\python.exe --version
  echo JARVIS requires Python 3.11 or 3.12.
  echo Rename the .venv folder and run SETUP.bat again.
  goto fail
)
echo Setup directory: %CD%
echo Virtual environment:
.venv\Scripts\python.exe -c "import sys, platform; print(sys.executable); print(sys.version); print(platform.machine())"
.venv\Scripts\python.exe -m pip --version
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
if not exist .env copy .env.example .env >nul
call :ollama_setup
echo.
set /p VOICE=Install optional Whisper, speech, and wake-word packages? (Y/N) [N]:
if /i "%VOICE%"=="Y" (
  .venv\Scripts\python.exe -m pip install -r requirements-voice.txt
  if errorlevel 1 echo Voice dependencies failed. Core JARVIS will still be installed.
)
echo.
set /p CONTROL=Install optional Windows desktop-control packages? (Y/N) [N]:
if /i "%CONTROL%"=="Y" (
  .venv\Scripts\python.exe -m pip install -r requirements-control.txt
  if errorlevel 1 echo Desktop-control dependencies failed. Chat and vision will still be available.
)
echo.
set /p FACE=Install optional local face-detection packages? (Y/N) [N]:
if /i "%FACE%"=="Y" (
  .venv\Scripts\python.exe -m pip install -r requirements-face.txt
  if errorlevel 1 echo Face-detection dependencies failed. The camera feature will be unavailable.
)
echo.
echo.
set /p GESTURES=Install optional hand-gesture recognition? (Y/N) [N]:
if /i "%GESTURES%"=="Y" (
  .venv\Scripts\python.exe -m pip install -r requirements-gestures.txt
  if errorlevel 1 echo Gesture dependencies failed. Gestures will be unavailable until installed.
)
echo.
set /p FACEAUTH=Install face-unlock dependencies and enroll Owner face? (Y/N) [N]:
if /i "%FACEAUTH%"=="Y" (
  .venv\Scripts\python.exe -m pip install -r requirements-face.txt
  if errorlevel 1 echo Face-unlock dependency installation failed.
  if not errorlevel 1 .venv\Scripts\python.exe src\main.py --enroll-face Owner
)
echo Setup finished. Starting JARVIS...
call LAUNCH.bat
exit /b 0
:create_venv
set "PYTHON_EXE="
where py >nul 2>&1
if not errorlevel 1 (
  py -3.12 --version >nul 2>&1
  if not errorlevel 1 (
    for /f "delims=" %%P in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
  ) else (
    py -3.11 --version >nul 2>&1
    if not errorlevel 1 for /f "delims=" %%P in ('py -3.11 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
  )
)
if not defined PYTHON_EXE (
  where uv >nul 2>&1
  if not errorlevel 1 (
    for /f "delims=" %%P in ('uv python find 3.12 2^>nul') do set "PYTHON_EXE=%%P"
    if not defined PYTHON_EXE for /f "delims=" %%P in ('uv python find 3.11 2^>nul') do set "PYTHON_EXE=%%P"
  )
)
if not defined PYTHON_EXE (
  echo Python 3.11 or 3.12 is required to create the virtual environment.
  exit /b 1
)
"%PYTHON_EXE%" -m venv .venv
exit /b %errorlevel%
:ollama_setup
where ollama >nul 2>&1
if errorlevel 1 (
  echo Ollama was not found. Install it from https://ollama.com/download.
  echo Then run: ollama run hf.co/mradermacher/Qwen2.5-7B-Instruct-abliterated-GGUF:Q4_K_M
  echo For screen vision, also run: ollama pull qwen2.5vl:7b
  exit /b 0
)
echo.
echo JARVIS uses Ollama locally. Model downloads require several GB of disk space.
set /p PULL_CHAT=Pull the JARVIS chat model now? (Y/N) [N]:
if /i "%PULL_CHAT%"=="Y" (
  ollama pull hf.co/mradermacher/Qwen2.5-7B-Instruct-abliterated-GGUF:Q4_K_M
  if errorlevel 1 echo Chat model pull failed. Retry with: ollama run hf.co/mradermacher/Qwen2.5-7B-Instruct-abliterated-GGUF:Q4_K_M
)
echo.
set /p PULL_VISION=Pull the local screen-vision model qwen2.5vl:7b now? (Y/N) [N]:
if /i "%PULL_VISION%"=="Y" (
  ollama pull qwen2.5vl:7b
  if errorlevel 1 echo Vision model pull failed. You can retry with: ollama pull qwen2.5vl:7b
)
exit /b 0
:fail
echo Setup failed. See the error above.
pause
exit /b 1
