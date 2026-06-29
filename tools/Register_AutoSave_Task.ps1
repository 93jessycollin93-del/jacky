<#
.SYNOPSIS
    Register a Windows Scheduled Task that runs the Jacky autosave hourly.

.DESCRIPTION
    Opt-in: nothing runs automatically until you run this once. Honors the
    Foundry "manual-start only" spirit - YOU decide when to turn it on, and
    Unregister_AutoSave_Task.ps1 turns it back off.

    The task:
      * Name:    JackyAutoSave
      * Runs:    pwsh -File <repo>\tools\autosave.ps1
      * Trigger: every 1 hour, indefinitely (also ~2 min after you log on)
      * Account: the current user (no admin/SYSTEM needed)

.PARAMETER IntervalMinutes
    Snapshot interval in minutes (default 60).

.PARAMETER NoPush
    Register the task to commit locally only (passes -NoPush to autosave.ps1).

.EXAMPLE
    pwsh -File tools/Register_AutoSave_Task.ps1
    pwsh -File tools/Register_AutoSave_Task.ps1 -IntervalMinutes 30
#>

[CmdletBinding()]
param(
    [int]$IntervalMinutes = 60,
    [switch]$NoPush
)

$ErrorActionPreference = 'Stop'
$taskName   = 'JackyAutoSave'
$repoRoot   = Split-Path $PSScriptRoot -Parent
$scriptPath = Join-Path $repoRoot 'tools\autosave.ps1'

# Prefer PowerShell 7 (pwsh) if available, else Windows PowerShell.
$pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue)?.Source
if (-not $pwsh) { $pwsh = (Get-Command powershell -ErrorAction SilentlyContinue)?.Source }
if (-not $pwsh) { throw "Neither pwsh nor powershell found on PATH." }

$argLine = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
if ($NoPush) { $argLine += " -NoPush" }

$action = New-ScheduledTaskAction -Execute $pwsh -Argument $argLine -WorkingDirectory $repoRoot

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) `
            -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
            -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

# Replace any existing task of the same name.
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal `
    -Description "Jacky hourly auto-save: commit + push project snapshots." | Out-Null

Write-Output "Registered scheduled task '$taskName'."
Write-Output "  Interval : every $IntervalMinutes minute(s)"
Write-Output "  Runs     : $pwsh $argLine"
Write-Output "  Push     : $([bool](-not $NoPush))"
Write-Output ""
Write-Output "Verify in Task Scheduler, or force one run now with:"
Write-Output "  Start-ScheduledTask -TaskName $taskName"
Write-Output "Turn it off anytime with:"
Write-Output "  pwsh -File tools/Unregister_AutoSave_Task.ps1"
