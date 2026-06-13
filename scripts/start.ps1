# One-command local launch — delegates to autonomous dev orchestrator
# Usage: .\scripts\start.ps1

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$py = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }
& $py scripts/dev.py start --wait --open
exit $LASTEXITCODE
