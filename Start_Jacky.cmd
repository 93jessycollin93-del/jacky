@echo off
title JACKY - AI Operations Manager
color 0B

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║         JACKY - AI Operations Manager                    ║
echo ║         It's Jacky's PC. You learn from Jacky.           ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM Set environment variables
set PYTHONPATH=E:\AI\Jacky;%PYTHONPATH%
set JACKY_HOME=E:\AI\Jacky
set JACKY_DATA=E:\AI\Jacky\data

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python not found. Install Python 3.11+
  pause
  exit /b 1
)

REM Install dependencies if needed
if not exist "E:\AI\Jacky\venv" (
  echo Creating virtual environment...
  python -m venv E:\AI\Jacky\venv
  call E:\AI\Jacky\venv\Scripts\activate.bat
  pip install -q -r E:\AI\Jacky\requirements.txt
) else (
  call E:\AI\Jacky\venv\Scripts\activate.bat
)

echo.
echo ✓ Starting Jacky...
echo.
echo Access Jacky:
echo   SAS Dashboard: http://localhost:5000/dashboard
echo   REST API:      http://localhost:5000/api
echo   Health check:  http://localhost:5000/health
echo.
echo (Open these in your browser in a moment)
echo.

REM Start Jacky Core in background
start "" python E:\AI\Jacky\jacky_core.py
timeout /t 2 /nobreak

REM Start API server (foreground - shows logs)
echo.
echo Starting API server...
echo.
python E:\AI\Jacky\jacky_api.py

pause
