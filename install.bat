@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Environment Check

echo ============================================
echo   Local Workbench - Environment Check
echo ============================================
echo.

set OK=1

where python >nul 2>nul
if %errorlevel%==0 (
  echo [OK] python found:
  python --version
) else (
  where py >nul 2>nul
  if %errorlevel%==0 (
    echo [OK] py launcher found:
    py --version
  ) else (
    echo [MISS] Python 3.8+ not found. Install from https://www.python.org/downloads/
    echo        and CHECK "Add Python to PATH".
    set OK=0
  )
)

echo.
if "%OK%"=="1" (
  echo All dependencies satisfied. Zero third-party packages needed.
  echo Double-click start.bat to launch the workbench.
) else (
  echo Please install Python first, then run this check again.
)
echo.
pause
