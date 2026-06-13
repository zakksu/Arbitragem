# Start Arbitragem locally (Windows) — use scripts/dev.ps1 or scripts/start.ps1
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
& "$Root\scripts\dev.ps1" -Wait -Open
