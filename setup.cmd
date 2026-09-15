@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python scripts\setup.py
) else (
  py -3.12 scripts\setup.py
)
if errorlevel 1 (
  echo Setup failed. Install Python 3.12 and FFmpeg, then try again. See README.md.
  pause
  exit /b 1
)
pause
