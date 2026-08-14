@echo off
setlocal
cd /d "%~dp0"

set "STI_WEB=.venv\Scripts\sti-web.exe"
set "STI_URL=http://127.0.0.1:5000"

if not exist "%STI_WEB%" (
  echo Social Text Intelligence is not installed in this project environment.
  echo Expected launcher: %STI_WEB%
  echo Create the project .venv and install the web and model extras first.
  echo See README.md for setup instructions.
  pause
  exit /b 1
)

echo Starting Social Text Intelligence in offline mode...
echo The browser will open at %STI_URL%.
echo Keep this window open while using the application.
echo Press Ctrl+C in this window to stop the local server.

start "" powershell.exe -NoProfile -WindowStyle Hidden -Command ^
  "Start-Sleep -Seconds 2; Start-Process '%STI_URL%'"

"%STI_WEB%" --offline
set "STI_EXIT=%ERRORLEVEL%"

if not "%STI_EXIT%"=="0" (
  echo.
  echo Social Text Intelligence stopped with exit code %STI_EXIT%.
  echo Confirm that both pinned models are already cached for offline use.
  pause
)

exit /b %STI_EXIT%
