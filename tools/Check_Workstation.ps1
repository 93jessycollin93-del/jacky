<#
.SYNOPSIS
    Workstation hardware + drive report for the Jacky project.

.DESCRIPTION
    Read-only. Gathers CPU, RAM, GPU (via nvidia-smi) and every drive's free
    space (including the project drives G: and H:), prints a summary, and writes
    a full report to workstation_report.txt next to the repo.

    No admin rights required. Nothing is changed on the machine.

.NOTES
    Part of the AI Foundry "manual-start only" tooling. Run it yourself:
        pwsh -File tools/Check_Workstation.ps1
    Then paste the printed summary back to Claude for the "assess my PC" step.
#>

[CmdletBinding()]
param(
    # Where to write the report. Defaults to repo root.
    [string]$OutFile = (Join-Path (Split-Path $PSScriptRoot -Parent) 'workstation_report.txt')
)

$ErrorActionPreference = 'Stop'
$lines = New-Object System.Collections.Generic.List[string]

function Add-Line { param([string]$Text = '') $lines.Add($Text) }

Add-Line "=================================================="
Add-Line " Jacky Workstation Report"
Add-Line " Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Add-Line " Host:      $env:COMPUTERNAME   User: $env:USERNAME"
Add-Line "=================================================="
Add-Line ""

# ---- OS ----------------------------------------------------------------
try {
    $os = Get-CimInstance Win32_OperatingSystem
    Add-Line "[ OS ]"
    Add-Line ("  {0}  (build {1})" -f $os.Caption.Trim(), $os.BuildNumber)
    Add-Line ("  Total RAM: {0:N1} GB   Free: {1:N1} GB" -f `
        ($os.TotalVisibleMemorySize / 1MB), ($os.FreePhysicalMemory / 1MB))
} catch {
    Add-Line "[ OS ]  (could not read: $($_.Exception.Message))"
}
Add-Line ""

# ---- CPU ---------------------------------------------------------------
try {
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    Add-Line "[ CPU ]"
    Add-Line ("  {0}" -f $cpu.Name.Trim())
    Add-Line ("  Cores: {0}   Logical: {1}   Max clock: {2} MHz" -f `
        $cpu.NumberOfCores, $cpu.NumberOfLogicalProcessors, $cpu.MaxClockSpeed)
} catch {
    Add-Line "[ CPU ]  (could not read: $($_.Exception.Message))"
}
Add-Line ""

# ---- GPU ---------------------------------------------------------------
# Reuse Foundry thermal framing: 70 C = warm, 75 C = stop (see CODING_AGENT_TIER.md)
Add-Line "[ GPU ]"
$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidiaSmi) {
    try {
        $q = & nvidia-smi --query-gpu=name,temperature.gpu,memory.total,memory.used,utilization.gpu `
                          --format=csv,noheader,nounits 2>$null
        foreach ($row in $q) {
            $f = $row -split '\s*,\s*'
            if ($f.Count -ge 5) {
                $name = $f[0]; $temp = [int]$f[1]
                $gate = if ($temp -ge 75) { 'STOP (>=75C)' }
                        elseif ($temp -ge 70) { 'WARM (>=70C)' }
                        else { 'OK (<70C)' }
                Add-Line ("  {0}" -f $name)
                Add-Line ("  Temp: {0} C  -> {1}" -f $temp, $gate)
                Add-Line ("  VRAM: {0} / {1} MB used   GPU util: {2}%" -f $f[3], $f[2], $f[4])
            }
        }
    } catch {
        Add-Line "  nvidia-smi present but query failed: $($_.Exception.Message)"
    }
} else {
    Add-Line "  nvidia-smi not found on PATH (no NVIDIA driver, or not installed)."
    try {
        Get-CimInstance Win32_VideoController | ForEach-Object {
            Add-Line ("  Video controller: {0}" -f $_.Name)
        }
    } catch { }
}
Add-Line ""

# ---- Drives ------------------------------------------------------------
# Highlight the project drives the user called out: G: (backups) and H: (bot farm)
Add-Line "[ DRIVES ]"
$projectDrives = @('G', 'H')
try {
    $drives = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" |
              Sort-Object DeviceID
    foreach ($d in $drives) {
        $letter = $d.DeviceID.TrimEnd(':')
        $sizeGB = [math]::Round($d.Size / 1GB, 1)
        $freeGB = [math]::Round($d.FreeSpace / 1GB, 1)
        $pctFree = if ($d.Size) { [math]::Round(($d.FreeSpace / $d.Size) * 100, 0) } else { 0 }
        $tag = if ($projectDrives -contains $letter) { '  <-- project drive' } else { '' }
        $label = if ($d.VolumeName) { " `"$($d.VolumeName)`"" } else { '' }
        Add-Line ("  {0}:{1,-16} {2,7:N1} GB total   {3,7:N1} GB free ({4}%) {5}" -f `
            $letter, $label, $sizeGB, $freeGB, $pctFree, $tag)
    }
    foreach ($pd in $projectDrives) {
        if (-not ($drives.DeviceID -contains "$($pd):")) {
            Add-Line ("  {0}: NOT PRESENT (expected project drive)" -f $pd)
        }
    }
} catch {
    Add-Line "  (could not enumerate drives: $($_.Exception.Message))"
}
Add-Line ""
Add-Line "=================================================="
Add-Line " End of report"
Add-Line "=================================================="

$report = ($lines -join [Environment]::NewLine)

# Print to console
Write-Output $report

# Write to file
try {
    $report | Out-File -FilePath $OutFile -Encoding utf8
    Write-Output ""
    Write-Output "Full report written to: $OutFile"
    Write-Output "(Paste the summary above back to Claude for the assessment step.)"
} catch {
    Write-Warning "Could not write report file ($OutFile): $($_.Exception.Message)"
}
