@echo off
REM One-click: snapshot the project right now (stage, commit, push to GitHub).
REM Double-click before you stop working, or anytime you want an instant save.
cd /d "%~dp0"
where pwsh >nul 2>nul
if %ERRORLEVEL%==0 (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\autosave.ps1"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\autosave.ps1"
)
pause
