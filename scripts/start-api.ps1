# Start the FastAPI backend on port 7860 (Vite dev proxy target).
# Safe to run from any directory; idempotent if healthz already responds.
# Usage: powershell -ExecutionPolicy Bypass -File scripts/start-api.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

function Test-ApiHealthy {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:7860/healthz" -UseBasicParsing -TimeoutSec 3
        return $response.Content -match '"status"\s*:\s*"ok"'
    } catch {
        return $false
    }
}

if (Test-ApiHealthy) {
    Write-Host "API already running: http://localhost:7860 (healthz ok). No second server needed."
    exit 0
}

$conn = Get-NetTCPConnection -LocalPort 7860 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($conn) {
    $pid = $conn.OwningProcess
    Write-Host "Port 7860 is in use (PID $pid) but /healthz did not respond."
    Write-Host "Stop the stale process, then run this script again:"
    Write-Host "  taskkill /PID $pid /F"
    exit 1
}

Write-Host "Starting API from repo root on http://localhost:7860 ..."
Write-Host "(Do not run 'uv run python scripts/serve.py' from the scripts folder; that doubles the path.)"
& uv run python scripts/serve.py
