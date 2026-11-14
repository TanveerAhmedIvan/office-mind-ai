# OfficeMind AI - office PC setup (Windows, PowerShell). Run from the project folder:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_office_pc.ps1
# Safe to re-run. Prereqs (install first): Python 3.12 (py launcher), Ollama for Windows.
param([string]$Model = "qwen2.5:3b")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "== 1. Hardware report (send this back) ==" -ForegroundColor Cyan
Get-PhysicalDisk | Select-Object FriendlyName, MediaType, @{n='SizeGB';e={[math]::Round($_.Size/1GB)}} | Format-Table
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber | Format-List
Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, @{n='RAM_GB';e={[math]::Round($_.TotalPhysicalMemory/1GB,1)}} | Format-List
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors | Format-List
Get-PSDrive C | Select-Object @{n='FreeGB';e={[math]::Round($_.Free/1GB)}} | Format-List

Write-Host "== 2. Python venv + packages ==" -ForegroundColor Cyan
if (-not (Test-Path .venv)) { py -3.12 -m venv .venv }
.\.venv\Scripts\python -m pip install -q --upgrade pip
.\.venv\Scripts\pip install -q torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\pip install -q -r requirements.txt

Write-Host "== 3. Ollama model ($Model) ==" -ForegroundColor Cyan
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { throw "Install Ollama for Windows first: https://ollama.com/download" }
ollama pull $Model

Write-Host "== 4. Build search index (downloads bge-m3 + reranker, ~4.5GB, needs internet once) ==" -ForegroundColor Cyan
.\.venv\Scripts\python -m app.vector build

Write-Host "== 5. Tests ==" -ForegroundColor Cyan
.\.venv\Scripts\python -m pytest -q tests

Write-Host "`nDONE. Start with: scripts\run_server.ps1   Then open http://localhost:8000" -ForegroundColor Green
