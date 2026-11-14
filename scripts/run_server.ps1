# Start OfficeMind AI. LAN access: run once as Administrator:
#   New-NetFirewallRule -DisplayName "OfficeMind AI" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
param([string]$Model = "qwen2.5:3b", [string]$Bind = "0.0.0.0", [int]$Port = 8000)
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:LLM_MODEL = $Model
Write-Host "Model: $Model | http://localhost:$Port | LAN: http://$((Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -like '192.168.*' -or $_.IPAddress -like '10.*' } | Select-Object -First 1).IPAddress):$Port"
.\.venv\Scripts\uvicorn app.server:app --host $Bind --port $Port
