@echo off
setlocal
rem Dev/acceptance helper, not part of the product: opens the native desktop on a
rem disposable demo folder (never the real application-data folder) holding an
rem invented CSV project. See tools\demo\launch_demo.py for the options.
cd /d "%~dp0..\.."
set "STI_PY=.venv\Scripts\python.exe"
if not exist "%STI_PY%" (
  echo The project environment was not found: %STI_PY%
  echo Create the .venv and install the desktop and model extras first.
  pause
  exit /b 1
)
echo Opening the native desktop with synthetic demo data.
echo The first run prepares the demo folder and can take a few minutes.
"%STI_PY%" tools\demo\launch_demo.py %*
if errorlevel 1 (
  echo.
  echo The demo stopped with an error.
  pause
)
