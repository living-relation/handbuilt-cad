# models-folder-notes.ps1 - add handbuilt-cad's ownership notes (AGENTS.md, README.md) to the models folder.
# Add-only: a file that already exists is left exactly as it is. Called by setup.ps1; safe to run by hand.
# Usage: .\scripts\models-folder-notes.ps1 -Models <models folder> [-WhatIf]
[CmdletBinding(SupportsShouldProcess = $true)]
param([Parameter(Mandatory = $true)][string]$Models)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path -LiteralPath $Models -PathType Container)) { Write-Host "models notes: $Models does not exist, skipped"; return }
foreach ($n in 'AGENTS.md', 'README.md') {
  $dst = Join-Path $Models $n
  if (Test-Path -LiteralPath $dst) { Write-Host "models notes: $dst exists, left as is"; continue }
  $text = [IO.File]::ReadAllText((Join-Path $Root "templates\models-folder\$n")).Replace('@CLONE@', $Root)
  if ($PSCmdlet.ShouldProcess($dst, 'add ownership note')) {
    [IO.File]::WriteAllText($dst, $text, (New-Object Text.UTF8Encoding($false)))
    Write-Host "models notes: added $dst"
  }
}
