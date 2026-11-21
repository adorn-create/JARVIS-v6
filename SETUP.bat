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
  echo Python launcher was not found. Install Python 3.11 or 3.12 and enable PATH.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  py -3.12 --version >nul 2>&1
  if not errorlevel 1 (
    py -3.12 -m venv .venv
  ) else (
    py -3.11 --version >nul 2>&1
    if errorlevel 1 (
      echo Python 3.11 or 3.12 is required to create the virtual environment.
      goto fail
    )
    py -3.11 -m venv .venv
  )
)
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
if not exist .env (
  copy .env.example .env >nul
  echo.
  echo Enter a NEW OpenRouter API key. The input is hidden.
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$key=Read-Host 'OpenRouter API key' -AsSecureString; $ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($key); try {$plain=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr); $p='.env'; $s=Get-Content $p -Raw; $s=$s.Replace('OPENROUTER_API_KEY=','OPENROUTER_API_KEY='+$plain); Set-Content $p $s} finally {[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)}"
)
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
echo Setup finished. Starting JARVIS...
call LAUNCH.bat
exit /b 0
:fail
echo Setup failed. See the error above.
pause
exit /b 1
