@echo off
REM Start Jacky AI engine on GODZILLA
REM Sets up environment and launches jacky_core.py

SET JACKY_DIR=E:\superagent\jacky
SET OLLAMA=http://localhost:11434

echo Checking Ollama...
curl -s %OLLAMA%/api/tags > NUL 2>&1
IF ERRORLEVEL 1 (
  echo [WARNING] Ollama not running. Starting...
  start /B ollama serve
  timeout /t 3 > NUL
)

echo Starting Jacky...
cd /d %JACKY_DIR%

IF NOT EXIST .env (
  copy .env.template .env
  echo Created .env from template. Edit it if needed.
)

python jacky_core.py
pause
