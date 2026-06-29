<#
.SYNOPSIS
    Remove the JackyAutoSave scheduled task (stop hourly auto-saves).

.DESCRIPTION
    Stops and unregisters the task created by Register_AutoSave_Task.ps1.
    Your existing commits are untouched - this only stops future auto-saves.

.EXAMPLE
    pwsh -File tools/Unregister_AutoSave_Task.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$taskName = 'JackyAutoSave'

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    try { Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue } catch { }
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Output "Removed scheduled task '$taskName'. Hourly auto-save is OFF."
} else {
    Write-Output "No scheduled task named '$taskName' found. Nothing to remove."
}
