@echo off
REM One-click launcher: starts Ollama + SAS server + Cloudflare tunnel.
REM Double-click this file to put SAS on the internet.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0Start_SAS_Public.ps1"
pause
