# Optional: rebuild Claude-importable zips in skills\<name>.zip (CI does this on PRs).
# Usage: powershell -NoProfile -File scripts\pack-skill-zips.ps1 [--no-check]
[CmdletBinding()]
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$PackArgs)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$py = if ($env:CAD_PY) { $env:CAD_PY } elseif (Test-Path -LiteralPath (Join-Path $Root '.venv\Scripts\python.exe')) { Join-Path $Root '.venv\Scripts\python.exe' } else { 'python' }
& $py (Join-Path $PSScriptRoot 'pack_skill_zips.py') @PackArgs
exit $LASTEXITCODE
