@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Local Workbench

rem ---- Find Python ----
set PY=
where python >nul 2>nul && set PY=python
if not defined PY (
  where py >nul 2>nul && set PY=py
)
if not defined PY (
  echo [ERROR] Python not found. Please install Python 3.8+ from https://www.python.org/downloads/
  echo         Check "Add Python to PATH" during install.
  pause
  exit /b 1
)

echo Starting Local Workbench ...
%PY% app.py
pause
