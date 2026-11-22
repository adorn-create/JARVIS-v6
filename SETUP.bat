@echo off
setlocal
cd /d "%~dp0"
title JARVIS - Setup
color 0A
echo.
echo              .-""""""""-.
echo           .-'  .-====-.  '-.
echo         .'    /  ###   \    '.
echo        /     {  #####  }     \
echo       ;      { ##   ## }      ;
echo       ^|      {  #####  }      ^|
echo       ;       \ ## ## /       ;
echo        \       '-----'       /
echo         '.      _____      .'
echo           '-.___________.-'
echo.
echo ========================================
echo       JARVIS ORGANIZED INSTALLER
echo ========================================
where py >nul 2>&1
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.11 or 3.12 and enable PATH.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  py -3.12 --version >nul 2>&1
  if not errorlevel 1 (
    call :run_task "Creating Python 3.12 environment" "py" "-3.12 -m venv .venv" "venv"
  ) else (
    py -3.11 --version >nul 2>&1
    if errorlevel 1 (
      echo Python 3.11 or 3.12 is required to create the virtual environment.
      goto fail
    )
    call :run_task "Creating Python 3.11 environment" "py" "-3.11 -m venv .venv" "venv"
  )
)
if errorlevel 1 goto fail
call :run_task "Updating pip" ".venv\Scripts\python.exe" "-m pip install --upgrade pip" "pip"
if errorlevel 1 goto fail
call :run_task "Installing JARVIS packages" ".venv\Scripts\python.exe" "-m pip install -r requirements.txt" "requirements"
if errorlevel 1 goto fail
if not exist .env copy .env.example .env >nul
call :ollama_setup
echo.
set /p VOICE=Install optional Whisper, speech, and wake-word packages? (Y/N) [N]:
if /i "%VOICE%"=="Y" (
  call :run_task "Installing voice packages" ".venv\Scripts\python.exe" "-m pip install -r requirements-voice.txt" "voice"
  if errorlevel 1 echo Voice dependencies failed. Core JARVIS will still be installed.
)
echo.
set /p CONTROL=Install optional Windows desktop-control packages? (Y/N) [N]:
if /i "%CONTROL%"=="Y" (
  call :run_task "Installing desktop-control packages" ".venv\Scripts\python.exe" "-m pip install -r requirements-control.txt" "control"
  if errorlevel 1 echo Desktop-control dependencies failed. Chat and vision will still be available.
)
echo.
set /p FACE=Install optional local face-detection packages? (Y/N) [N]:
if /i "%FACE%"=="Y" (
  call :run_task "Installing face-detection packages" ".venv\Scripts\python.exe" "-m pip install -r requirements-face.txt" "face"
  if errorlevel 1 echo Face-detection dependencies failed. The camera feature will be unavailable.
)
echo.
echo Setup finished. Starting JARVIS...
call LAUNCH.bat
exit /b 0
:ollama_setup
where ollama >nul 2>&1
if errorlevel 1 (
  echo Ollama was not found. Install it from https://ollama.com/download.
  echo Then run: ollama pull hf.co/mradermacher/Qwen2.5-7B-Instruct-abliterated-GGUF:Q4_K_M
  echo For screen vision, also run: ollama pull qwen2.5vl:7b
  exit /b 0
)
echo.
echo JARVIS uses Ollama locally. Model downloads require several GB of disk space.
set /p PULL_CHAT=Pull the JARVIS chat model now? (Y/N) [N]:
if /i "%PULL_CHAT%"=="Y" (
  call :run_task "Downloading chat model" "ollama" "pull hf.co/mradermacher/Qwen2.5-7B-Instruct-abliterated-GGUF:Q4_K_M" "chat-model"
  if errorlevel 1 echo Chat model pull failed. Retry with: ollama run hf.co/mradermacher/Qwen2.5-7B-Instruct-abliterated-GGUF:Q4_K_M
)
echo.
set /p PULL_VISION=Pull the local screen-vision model qwen2.5vl:7b now? (Y/N) [N]:
if /i "%PULL_VISION%"=="Y" (
  call :run_task "Downloading vision model" "ollama" "pull qwen2.5vl:7b" "vision-model"
  if errorlevel 1 echo Vision model pull failed. You can retry with: ollama pull qwen2.5vl:7b
)
exit /b 0
:run_task
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_spinner.ps1" -Label "%~1" -FilePath "%~2" -ArgumentLine "%~3" -LogName "%~4"
exit /b %errorlevel%
:fail
echo Setup failed. See the error above.
pause
exit /b 1
