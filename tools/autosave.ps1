<#
.SYNOPSIS
    Auto-save snapshot for the Jacky project: stage everything, commit with a
    timestamp, and (by default) push to the current branch on GitHub.

.DESCRIPTION
    Designed to be run hourly by a Windows Scheduled Task (see
    Register_AutoSave_Task.ps1) and/or on demand via Save_Now.cmd.

    Behaviour:
      * No-op when the working tree is clean (nothing to commit).
      * Commits as:  chore(autosave): snapshot <ISO-8601 local time>
      * Pushes to the CURRENT branch (git push origin HEAD) unless -NoPush.
      * Uses a lock file so overlapping runs can't collide.
      * Appends a line to autosave.log (gitignored).

    Safe to run from anywhere; it operates on the repo this script lives in.

.PARAMETER NoPush
    Commit locally but do NOT push to GitHub.

.PARAMETER Message
    Override the commit message prefix (default: "chore(autosave): snapshot").

.EXAMPLE
    pwsh -File tools/autosave.ps1
    pwsh -File tools/autosave.ps1 -NoPush
#>

[CmdletBinding()]
param(
    [switch]$NoPush,
    [string]$Message = 'chore(autosave): snapshot'
)

$ErrorActionPreference = 'Stop'

# Resolve repo root = parent of this script's folder (tools/)
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

$logFile  = Join-Path $repoRoot 'autosave.log'
$lockFile = Join-Path $repoRoot '.autosave.lock'

function Write-Log {
    param([string]$Text)
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line  = "[$stamp] $Text"
    Write-Output $line
    try { Add-Content -Path $logFile -Value $line -Encoding utf8 } catch { }
}

# ---- Sanity: are we in a git repo? -------------------------------------
$inside = (& git rev-parse --is-inside-work-tree 2>$null)
if ($LASTEXITCODE -ne 0 -or $inside -ne 'true') {
    Write-Log "ERROR: not a git repository ($repoRoot). Aborting."
    exit 1
}

# ---- Lock: avoid overlapping runs --------------------------------------
if (Test-Path $lockFile) {
    $age = (Get-Date) - (Get-Item $lockFile).LastWriteTime
    if ($age.TotalMinutes -lt 30) {
        Write-Log "Another autosave run looks active (lock age $([int]$age.TotalMinutes)m). Skipping."
        exit 0
    } else {
        Write-Log "Stale lock found (age $([int]$age.TotalMinutes)m). Overriding."
    }
}
try { New-Item -ItemType File -Path $lockFile -Force | Out-Null } catch { }

try {
    $branch = (& git rev-parse --abbrev-ref HEAD).Trim()

    # ---- Anything to commit? -------------------------------------------
    $status = & git status --porcelain
    if ([string]::IsNullOrWhiteSpace($status)) {
        Write-Log "Clean tree on '$branch' - nothing to snapshot."
        exit 0
    }

    & git add -A
    if ($LASTEXITCODE -ne 0) { Write-Log "ERROR: git add failed."; exit 1 }

    $iso = Get-Date -Format 'yyyy-MM-ddTHH:mm:ssK'
    $commitMsg = "$Message $iso"
    & git commit -m $commitMsg | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Log "ERROR: git commit failed."; exit 1 }
    Write-Log "Committed on '$branch': $commitMsg"

    if ($NoPush) {
        Write-Log "Local-only (-NoPush). Skipping push."
        exit 0
    }

    # ---- Push to current branch ----------------------------------------
    $pushed = $false
    for ($i = 1; $i -le 4; $i++) {
        & git push origin HEAD 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { $pushed = $true; break }
        $wait = [math]::Pow(2, $i)   # 2,4,8,16s backoff for transient network errors
        Write-Log "Push attempt $i failed; retrying in ${wait}s..."
        Start-Sleep -Seconds $wait
    }
    if ($pushed) {
        Write-Log "Pushed '$branch' to origin."
    } else {
        Write-Log "WARNING: push failed after retries. Commit is saved locally; it will go up on the next successful push."
    }
}
finally {
    Remove-Item $lockFile -ErrorAction SilentlyContinue
}
