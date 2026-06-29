# =====================================================================
#  Start SAS Public — Ollama + waitress server + Cloudflare quick tunnel
#  One command to put SAS on the internet. Prints the public URL.
#
#  Run:  right-click -> Run with PowerShell   (or)   .\Start_SAS_Public.ps1
# =====================================================================
$ErrorActionPreference = "SilentlyContinue"
$Home2 = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Home2

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SAS PUBLIC LAUNCHER — Jacky's PC" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Ollama -----------------------------------------------------------
if (-not (Get-Process ollama -ErrorAction SilentlyContinue)) {
    Write-Host "[1/3] Starting Ollama..." -ForegroundColor Yellow
    Start-Process -WindowStyle Hidden ollama -ArgumentList "serve"
    Start-Sleep 3
} else {
    Write-Host "[1/3] Ollama already running." -ForegroundColor Green
}

# 2. SAS server (waitress) -------------------------------------------
# Free port 5000 of any stale Flask debug reloaders first.
Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
Start-Sleep 1
Write-Host "[2/3] Starting SAS server (waitress, port 5000)..." -ForegroundColor Yellow
Start-Process -WindowStyle Minimized python -ArgumentList "serve.py" -WorkingDirectory $Home2
Start-Sleep 4

# Confirm it's up
$health = $null
try { $health = Invoke-RestMethod -Uri "http://localhost:5000/health" -TimeoutSec 5 } catch {}
if ($health) {
    Write-Host "      Server up. Auth: $($health.auth)" -ForegroundColor Green
    if ($health.auth -ne "enabled") {
        Write-Host "      WARNING: auth is DISABLED. Set SAS_ACCESS_TOKEN in secrets\secrets.env!" -ForegroundColor Red
    }
} else {
    Write-Host "      Server not responding yet — check sas_serve.log" -ForegroundColor Red
}

# 3. Cloudflare quick tunnel -----------------------------------------
Write-Host "[3/3] Opening Cloudflare tunnel (public URL)..." -ForegroundColor Yellow
$tlog = Join-Path $Home2 "tunnel.log"
Remove-Item $tlog -ErrorAction SilentlyContinue
Start-Process -WindowStyle Minimized -FilePath (Join-Path $Home2 "bin\cloudflared.exe") `
    -ArgumentList "tunnel --url http://localhost:5000 --no-autoupdate" `
    -RedirectStandardOutput $tlog -RedirectStandardError "$tlog.err"

# Wait for the public URL to appear in the log
$publicUrl = $null
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep 1
    $match = Select-String -Path $tlog,"$tlog.err" -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($match) { $publicUrl = $match.Matches[0].Value; break }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
if ($publicUrl) {
    Write-Host "  SAS IS LIVE ON THE INTERNET" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Public URL:  $publicUrl/dashboard" -ForegroundColor White
    Write-Host "  Local URL:   http://localhost:5000/dashboard" -ForegroundColor White
    Write-Host ""
    Write-Host "  Open the public URL on your phone, log in, then" -ForegroundColor Gray
    Write-Host "  use 'Add to Home Screen' to install it as an app." -ForegroundColor Gray
    $publicUrl | Set-Content (Join-Path $Home2 "CURRENT_PUBLIC_URL.txt")
} else {
    Write-Host "  Tunnel started but URL not detected yet." -ForegroundColor Yellow
    Write-Host "  Check tunnel.log for the https://...trycloudflare.com link." -ForegroundColor Yellow
}
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  NOTE: this quick-tunnel URL changes every restart." -ForegroundColor DarkGray
Write-Host "  For a permanent sas.cybernetic67.com, see TUNNEL_SETUP.md" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Leave this window open. Close it to take SAS offline." -ForegroundColor DarkGray
Write-Host "  Press Ctrl+C to stop." -ForegroundColor DarkGray

# Keep the launcher alive so closing it is an intentional "go offline"
while ($true) { Start-Sleep 60 }
