<# 
  Swire PMP Agent Demo - Start All Services
  Run from the project root: .\start-all.ps1
#>

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Ensure a modern Node.js is on PATH. The system Node on some Windows
# machines is too old for the ES module frontend.
$localNode = Resolve-Path (Join-Path $root ".tools\node-v*-win-x64\node.exe") -ErrorAction SilentlyContinue |
    Select-Object -First 1
$codexNode = Resolve-Path "$env:ProgramFiles\WindowsApps\OpenAI.Codex_*\app\resources\node.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($localNode) {
    $env:PATH = "$([System.IO.Path]::GetDirectoryName($localNode.Path));$env:PATH"
} elseif ($codexNode) {
    $env:PATH = "$([System.IO.Path]::GetDirectoryName($codexNode.Path));$env:PATH"
} elseif (Test-Path "$env:LOCALAPPDATA\nodejs\node.exe") {
    $env:PATH = "$env:LOCALAPPDATA\nodejs;$env:PATH"
}

# Check prerequisites
if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found. Install Python 3.10+ first."
    exit 1
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js not found. Install Node.js 18+ first."
    exit 1
}

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    py -3 -m venv (Join-Path $root ".venv")
    & $venvPython -m pip install -q -r (Join-Path $root "backend\requirements.txt")
}

# Seed database
Write-Host "Seeding demo database..." -ForegroundColor Yellow
& $venvPython (Join-Path $root "backend\data\seed_demo_db.py")

# Install frontend deps if needed
$frontendDir = Join-Path $root "frontend"
if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $frontendDir
    npm install --silent
    Pop-Location
}

# Kill any existing processes on our ports
foreach ($port in @(8001, 8000, 3001, 5173)) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conn) {
        $conn | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
        Write-Host "Freed port $port" -ForegroundColor DarkGray
    }
}

Start-Sleep -Seconds 1

# Start Mock PMP API (port 8001)
Write-Host "Starting Mock PMP API on :8001..." -ForegroundColor Cyan
$mockPmp = Start-Process -FilePath $venvPython -ArgumentList "-m uvicorn backend.mock_pmp_api.main:app --port 8001" -WorkingDirectory $root -PassThru -WindowStyle Minimized
Start-Sleep -Seconds 2

# Start Agent API (port 8000)
Write-Host "Starting Agent API on :8000..." -ForegroundColor Cyan
$agentApi = Start-Process -FilePath $venvPython -ArgumentList "-m uvicorn backend.agent_api.main:app --port 8000" -WorkingDirectory $root -PassThru -WindowStyle Minimized
Start-Sleep -Seconds 2

# Start Frontend Express server (port 3001)
Write-Host "Starting Frontend server on :3001..." -ForegroundColor Cyan
$nodeBin = (Get-Command node).Source
$feServer = Start-Process -FilePath $nodeBin -ArgumentList "server.js" -WorkingDirectory $frontendDir -PassThru -WindowStyle Minimized
Start-Sleep -Seconds 2

# Start Vite dev server (port 5173)
Write-Host "Starting Vite dev server on :5173..." -ForegroundColor Cyan
$viteBin = Join-Path $frontendDir "node_modules\vite\bin\vite.js"
$feVite = Start-Process -FilePath $nodeBin -ArgumentList "`"$viteBin`" --port 5173" -WorkingDirectory $frontendDir -PassThru -WindowStyle Minimized
Start-Sleep -Seconds 3

# Health checks
Write-Host "`n--- Health Checks ---" -ForegroundColor Green
foreach ($svc in @(
    @{ Name = "Mock PMP API"; Url = "http://127.0.0.1:8001/health" },
    @{ Name = "Agent API";    Url = "http://127.0.0.1:8000/api/health" },
    @{ Name = "Frontend Server"; Url = "http://127.0.0.1:3001/api/me" },
    @{ Name = "Vite Dev Server"; Url = "http://127.0.0.1:5173" }
)) {
    try {
        Invoke-WebRequest -Uri $svc.Url -TimeoutSec 3 -UseBasicParsing | Out-Null
        Write-Host "  $($svc.Name): OK" -ForegroundColor Green
    } catch {
        Write-Host "  $($svc.Name): FAILED" -ForegroundColor Red
    }
}

Write-Host "`n============================================" -ForegroundColor Green
Write-Host "  All services started!" -ForegroundColor Green
Write-Host "  Open: http://localhost:5173" -ForegroundColor Yellow
Write-Host "  Login: alice / password123" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Green
Write-Host "`nProcess IDs (use to stop later):"
Write-Host "  Mock PMP API : $($mockPmp.Id)"
Write-Host "  Agent API    : $($agentApi.Id)"
Write-Host "  FE Server    : $($feServer.Id)"
Write-Host "  Vite Dev     : $($feVite.Id)"
Write-Host "`nTo stop all: .\stop-all.ps1"
Write-Host ""

# Save PIDs for stop script
@($mockPmp.Id, $agentApi.Id, $feServer.Id, $feVite.Id) | Set-Content (Join-Path $root ".service-pids")
