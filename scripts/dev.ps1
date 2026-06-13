# Arbitragem — autonomous dev launcher (Windows)
# Usage: .\scripts\dev.ps1
#        .\scripts\dev.ps1 -Wait -Open

param(
    [switch]$Wait,
    [switch]$Open,
    [switch]$Stop,
    [switch]$Status
)

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$py = "python"
if (Test-Path ".venv\Scripts\python.exe") { $py = ".\.venv\Scripts\python.exe" }

if ($Stop) {
    & $py scripts/dev.py stop
    exit $LASTEXITCODE
}
if ($Status) {
    & $py scripts/dev.py status
    exit $LASTEXITCODE
}

$args = @("scripts/dev.py", "start")
if ($Wait) { $args += "--wait" }
if ($Open) { $args += "--open" }
& $py @args
exit $LASTEXITCODE
