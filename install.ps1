# kairos installer (Windows PowerShell). Idempotent.
# Prefers `uv tool install`, then `pipx install`, then `pip install --user`.
$ErrorActionPreference = 'Stop'

$Pkg = 'kairos-agent'
$Bin = 'kairos'

function Write-Hi   { param($m) Write-Host "-> $m" -ForegroundColor Cyan }
function Write-Ok   { param($m) Write-Host "ok $m" -ForegroundColor Green }
function Write-Err  { param($m) Write-Host "!  $m" -ForegroundColor Red; exit 1 }

Write-Hi "kairos installer - picks the right Python tool for you"

$installer = $null
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Hi 'found uv, installing as a uv tool'
    & uv tool install $Pkg
    if ($LASTEXITCODE -ne 0) { Write-Err 'uv tool install failed' }
    Write-Ok 'installed via uv'
    $installer = 'uv'
}
elseif (Get-Command pipx -ErrorAction SilentlyContinue) {
    Write-Hi 'found pipx, installing as an isolated app'
    & pipx install $Pkg
    if ($LASTEXITCODE -ne 0) { Write-Err 'pipx install failed' }
    Write-Ok 'installed via pipx'
    $installer = 'pipx'
}
elseif ((Get-Command pip -ErrorAction SilentlyContinue) -or (Get-Command pip3 -ErrorAction SilentlyContinue)) {
    $pip = if (Get-Command pip3 -ErrorAction SilentlyContinue) { 'pip3' } else { 'pip' }
    Write-Hi "no uv or pipx, falling back to $pip --user"
    & $pip install --user --upgrade $Pkg
    if ($LASTEXITCODE -ne 0) { Write-Err 'pip install failed' }
    Write-Ok 'installed via pip --user'
    $installer = $pip
}
else {
    Write-Err 'no Python package manager found. Install uv (https://docs.astral.sh/uv/) or pipx and re-run.'
}

if (Get-Command $Bin -ErrorAction SilentlyContinue) {
    $vers = (& $Bin version 2>$null) -join ''
    if (-not $vers) { $vers = '?' }
    Write-Ok "$Bin on PATH: $vers"
    Write-Host ''
    Write-Host 'next:' -ForegroundColor DarkGray
    Write-Host "  $Bin init my-wiki; cd my-wiki"
    Write-Host "  $Bin run 'Search the docs for caching' --dry"
}
else {
    Write-Host ''
    Write-Host 'note: kairos installed but not on PATH yet.' -ForegroundColor DarkGray
    if ($installer -eq 'uv') {
        Write-Host '  Open a new terminal, or add `$HOME\.local\bin` to your PATH.'
    }
    elseif ($installer -eq 'pipx') {
        Write-Host '  Run `pipx ensurepath` and open a new terminal.'
    }
}
