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
function Test-Esbuild {
    # require() alone only loads the JS wrapper; transformSync spawns the
    # platform binary, which is the part that breaks cross-OS copies.
    # A failing probe must return $false, not trip $ErrorActionPreference=Stop.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        node -e "require('esbuild').transformSync('1+1',{loader:'js'})" >$null 2>&1
        return $?
    } finally {
        $ErrorActionPreference = $prev
    }
}

function Repair-NodeModules {
    Push-Location -LiteralPath (Join-Path $Root "web")
    try {
        if (Test-Esbuild) { Write-Host "esbuild OK."; return }
        Write-Host "esbuild binary broken (wrong platform) - reinstalling web/node_modules."
        Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force
        Start-Sleep -Seconds 2
        Remove-Item -Recurse -Force node_modules -ErrorAction Stop
        npm install
        if (-not (Test-Esbuild)) {
            Write-Host "Still broken after reinstall. Suspects: OneDrive on-demand sync or npm cache."
            Write-Host "Try: npm cache clean --force, then delete web/node_modules and retry."
            exit 1
        }
    } finally { Pop-Location }
}

if (-not $BackendOnly) {
    Repair-NodeModules
    Assert-PortFreeOrOwn 5173 "vite|node"
    Start-Process -NoNewWindow cmd -ArgumentList "/c", "npm", "run", "dev", "--", "--port", "5173", "--strictPort" `
        -WorkingDirectory (Join-Path $Root "web")
    Write-Host "Frontend starting on http://localhost:5173"
}
