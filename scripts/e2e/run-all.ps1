# Run all 5 kairos e2e scripts in order on Windows. Uses sh.exe under the hood
# (Git for Windows ships one), so install Git or use WSL/Cygwin.
$ErrorActionPreference = 'Stop'

$dir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Invoke-E2EScript {
    param([string]$Name)
    Write-Host ""
    Write-Host ("#" * 60)
    Write-Host "# $Name"
    Write-Host ("#" * 60)
    & sh.exe "$dir\$Name"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "!! $Name failed (exit $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host ("=" * 60)
Write-Host " kairos e2e suite"
Write-Host ("=" * 60)

Invoke-E2EScript '01_init.sh'
Invoke-E2EScript '02_ingest.sh'
Invoke-E2EScript '03_query.sh'
Invoke-E2EScript '04_lint.sh'
Invoke-E2EScript '05_run.sh'

Write-Host ""
Write-Host ("=" * 60)
Write-Host " ALL E2E PASSED" -ForegroundColor Green
Write-Host ("=" * 60)
