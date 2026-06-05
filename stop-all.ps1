<#
  Swire PMP Agent Demo - Stop All Services
  Run from the project root: .\stop-all.ps1
#>

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$pidFile = Join-Path $root ".service-pids"

if (Test-Path $pidFile) {
    $pids = Get-Content $pidFile
    foreach ($procId in $pids) {
        $procId = $procId.Trim()
        if ($procId -and $procId -match '^\d+$') {
            try {
                Stop-Process -Id ([int]$procId) -Force -ErrorAction Stop
                Write-Host "Stopped process $procId" -ForegroundColor Yellow
            } catch {
                Write-Host "Process $procId already stopped" -ForegroundColor DarkGray
            }
        }
    }
    Remove-Item $pidFile -Force
    Write-Host "`nAll services stopped." -ForegroundColor Green
} else {
    Write-Host "No .service-pids file found. Services may not have been started with start-all.ps1" -ForegroundColor Yellow
    Write-Host "Checking ports manually..." -ForegroundColor Yellow
    foreach ($port in @(8001, 8000, 3001, 5173)) {
        $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($conn) {
            $conn | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
            Write-Host "  Freed port $port" -ForegroundColor Yellow
        }
    }
    Write-Host "Done." -ForegroundColor Green
}
