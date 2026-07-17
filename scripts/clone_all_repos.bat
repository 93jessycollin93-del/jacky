@echo off
REM Thin wrapper around sync_repos.py — kept for double-click convenience.
REM The repo list now lives in repos.json (single source of truth); see
REM REPO_MIRROR_GUIDE.md for the full cross-platform workflow.

IF "%JACKY_REPOS_DIR%"=="" SET JACKY_REPOS_DIR=E:\superagent\condensers

echo Syncing repos into %JACKY_REPOS_DIR% (set JACKY_REPOS_DIR to change this)...
python "%~dp0sync_repos.py" --base-dir "%JACKY_REPOS_DIR%"

echo.
echo Done. Run: python E:\superagent\scripts\godzilla_dataset_downloader.py
pause
