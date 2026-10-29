# skill-upload-popup.ps1 - after install, remind the user to upload CAD skill zips in Claude desktop.
# setup.ps1 (and so double-click install.cmd) runs this at the end.
# Skip the GUI with -NoPopup / -Quiet, or when CI / GITHUB_ACTIONS / TF_BUILD is set.
[CmdletBinding()]
param(
  [switch]$NoPopup,
  [switch]$Quiet,
  [string]$SkillsDir = (Join-Path (Split-Path $PSScriptRoot -Parent) 'skills')
)
$ErrorActionPreference = 'Stop'

function Test-SkipSkillPopup {
  if ($NoPopup -or $Quiet) { return $true }
  foreach ($n in @('CI', 'GITHUB_ACTIONS', 'TF_BUILD')) {
    $v = [Environment]::GetEnvironmentVariable($n)
    if ($v -and $v -notin @('0', 'false', 'False', 'no', 'No')) { return $true }
  }
  return $false
}

function Get-SkillUploadNames([string]$Dir) {
  $zips = @(Get-ChildItem -LiteralPath $Dir -File -Filter '*.zip' -ErrorAction SilentlyContinue |
    Sort-Object Name | ForEach-Object { $_.Name })
  if ($zips.Count) {
    return [pscustomobject]@{ Kind = 'zip'; Names = $zips; Folder = $Dir }
  }
  $folders = @(Get-ChildItem -LiteralPath $Dir -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') } |
    Sort-Object Name | ForEach-Object { $_.Name })
  return [pscustomobject]@{ Kind = 'folder'; Names = $folders; Folder = $Dir }
}

$info = Get-SkillUploadNames $SkillsDir
$names = @($info.Names)
$list = if ($names.Count) { ($names | ForEach-Object { "  $_" }) -join [Environment]::NewLine } else { '  (none found)' }
$kind = if ($info.Kind -eq 'zip') { 'Skill zips:' } else { 'Skill folders (no zips found):' }
$nl = [Environment]::NewLine
$reminder = 'Upload new or changed CAD skill zips to the Claude desktop app for each Claude account (Skills settings).'
$msg = $reminder + $nl + $nl + $kind + $nl + $list + $nl + $nl + 'Open this folder in Explorer?' + $nl + [string]$info.Folder

Write-Host $reminder
Write-Host $kind
Write-Host $list

if (Test-SkipSkillPopup) {
  Write-Host 'skills popup: skipped (-NoPopup/-Quiet/CI)'
  return
}

$title = 'handbuilt-cad - Claude skills'
$open = $false
try {
  Add-Type -AssemblyName System.Windows.Forms | Out-Null
  $r = [System.Windows.Forms.MessageBox]::Show(
    $msg,
    $title,
    [System.Windows.Forms.MessageBoxButtons]::YesNo,
    [System.Windows.Forms.MessageBoxIcon]::Information)
  $open = ($r -eq [System.Windows.Forms.DialogResult]::Yes)
} catch {
  try {
    $w = New-Object -ComObject WScript.Shell
    # 4 = Yes/No, 64 = Information. 6 = Yes.
    $open = ($w.Popup($msg, 0, $title, 4 + 64) -eq 6)
  } catch {
    Write-Host 'skills popup: GUI not available; printed the reminder above.'
    return
  }
}

if ($open) {
  Start-Process explorer.exe -ArgumentList ([string]$info.Folder)
}
