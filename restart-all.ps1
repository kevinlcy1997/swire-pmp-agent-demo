<#
  Swire PMP Agent Demo - Restart All Services
  Run from the project root: .\restart-all.ps1
#>

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host "Stopping services..." -ForegroundColor Yellow
& "$root\stop-all.ps1"

Start-Sleep -Seconds 2

Write-Host "`nStarting services..." -ForegroundColor Cyan
& "$root\start-all.ps1"
