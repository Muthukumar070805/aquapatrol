# Requires PowerShell 5.1+. Repo-root dev launcher: preflight, then start servers.
# Usage: powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 [-BackendOnly] [-FrontendOnly]
param([switch]$BackendOnly, [switch]$FrontendOnly)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

function Get-PortHolder($Port) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $conn) { return $null }
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $($conn.OwningProcess)" |
        Select-Object ProcessId, Name, CommandLine
    return $proc
}

function Assert-PortFreeOrOwn($Port, $OwnPattern) {
    $holder = Get-PortHolder $Port
    if (-not $holder) { return }
    if ($holder.CommandLine -match $OwnPattern) {
        Write-Host "Port $Port held by our own process ($($holder.Name) pid $($holder.ProcessId)) - stopping it."
        Stop-Process -Id $holder.ProcessId -Force
        return
    }
    Write-Host "Port $Port is held by an unrelated process: $($holder.Name) pid $($holder.ProcessId)."
    Write-Host "Refusing to kill it. Run this, then retry:"
    Write-Host "  taskkill /PID $($holder.ProcessId) /F"
    exit 1
}

if (-not $FrontendOnly) {
    Assert-PortFreeOrOwn 7860 "serve\.py|uvicorn"
    Start-Process -NoNewWindow uv -ArgumentList "run", "python", "scripts/serve.py"
    Write-Host "Backend starting on http://localhost:7860 (health: http://localhost:7860/healthz)"
}
if (-not $BackendOnly) {
    Assert-PortFreeOrOwn 5173 "vite|node"
}
