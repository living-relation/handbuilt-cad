#Requires -Version 5.1
<#
.SYNOPSIS
  Copy handbuilt-cad for Cursor. It does not open a browser.
.DESCRIPTION
  Run this yourself. Double-click install-plugins.cmd, or run this file.
  A script cannot turn the plugin on at claude.ai. A real run prints the clicks
  and does not open a browser. It copies .cursor-plugin and skills to
  ~\.cursor\plugins\local\handbuilt-cad and replaces the old copy.
  It does not copy skills into ~\.claude\skills or ~\.cursor\skills.
  It does not create a scheduled task, a sign-in item, or a Run key.
  Turn Sync automatically on. Nothing runs in the background.
  -WhatIf prints the clicks and changes nothing.
  -UserHome is for tests: the Cursor copy goes under that folder, and the
  browser is not opened.
.PARAMETER UserHome
  Testing only. Cursor copy destination root. Also skips the browser.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [string]$UserHome
)

$ErrorActionPreference = 'Stop'
$catalog = 'living-relation/handbuilt-cad'
$url = 'https://claude.ai/customize/plugins'
$dry = [bool]$WhatIfPreference
$copyHome = $UserHome
if (-not $copyHome) {
  $copyHome = $env:USERPROFILE
  if (-not $copyHome) { $copyHome = $HOME }
}
if (-not $copyHome) {
  Write-Host 'No home folder found.'
  exit 1
}

function Get-HandbuiltClaudeAiLine {
  param([string]$HomeRoot)
  $id = 'handbuilt-cad@handbuilt-cad-plugins'
  $ok = 'The handbuilt-cad plugin is present on claude.ai.'
  $missing = 'WARN: handbuilt-cad plugin not added on claude.ai yet: add catalog living-relation/handbuilt-cad and turn on handbuilt-cad.'
  $settings = Join-Path $HomeRoot '.claude\settings.json'
  if (Test-Path -LiteralPath $settings) {
    try {
      $j = Get-Content -LiteralPath $settings -Raw -ErrorAction Stop | ConvertFrom-Json
      $ep = $j.enabledPlugins
      if ($null -ne $ep -and $ep.PSObject.Properties.Name -contains $id) {
        $val = $ep.PSObject.Properties[$id].Value
        if ($val -eq $true) { return $ok }
      }
    } catch {}
  }
  return $missing
}

Write-Host (Get-HandbuiltClaudeAiLine -HomeRoot $copyHome)
Write-Host ''
Write-Host 'handbuilt-cad on claude.ai'
Write-Host 'This script cannot add the plugin. Do these clicks yourself.'
Write-Host ''
Write-Host "Catalog to paste: $catalog"
Write-Host 'Catalog name: handbuilt-cad-plugins'
Write-Host ''
Write-Host '1. Sign in to the claude.ai account you use.'
Write-Host '2. Open Customize.'
Write-Host '3. Open Plugins.'
Write-Host '4. Choose Add.'
Write-Host '5. Choose Add marketplace.'
Write-Host "6. Paste $catalog."
Write-Host '7. Turn Sync automatically on. Where that switch sits on the page is unverified until someone clicks through Customize.'
Write-Host '8. Open handbuilt-cad and turn it on (Add).'
Write-Host '9. Chat, Cowork, and Claude Code signed in to this account all use that plugin.'
Write-Host ''
Write-Host 'Update: Turn Sync automatically on. Updates arrive automatically after merges to main. Check for updates in the catalog forces it sooner.'
Write-Host 'Remove: open handbuilt-cad, open its menu, choose Remove.'
Write-Host ''
Write-Host 'Cursor is separate. Leave Auto Refresh off.'
Write-Host 'This script copies .cursor-plugin and skills to ~/.cursor/plugins/local/handbuilt-cad and replaces the old copy. Fully quit and reopen Cursor. Open Customize and confirm the skills.'
Write-Host 'Update that copy: the Cursor local copy still updates by re-running this script (replace the copy, then reload).'
Write-Host 'Remove that copy: delete ~/.cursor/plugins/local/handbuilt-cad and reload.'
Write-Host 'It does not copy skills into ~/.claude/skills or ~/.cursor/skills.'
Write-Host 'Team or Enterprise account: Dashboard, Plugins & MCPs, Add Marketplace, Import from Repo. Paste https://github.com/living-relation/handbuilt-cad. Under Marketplace Settings, leave Enable Auto Refresh off. Then in Customize, install handbuilt-cad. Update: open the marketplace and choose Refresh.'
Write-Host ''

$src = $PSScriptRoot
if (-not $src) { $src = Split-Path -Parent $MyInvocation.MyCommand.Path }
$dest = Join-Path $copyHome '.cursor\plugins\local\handbuilt-cad'
$fullDest = [IO.Path]::GetFullPath($dest)
$fullSrc = [IO.Path]::GetFullPath($src)
$destTrim = $fullDest.TrimEnd('\', '/')
$srcTrim = $fullSrc.TrimEnd('\', '/')
$tail = [IO.Path]::Combine('.cursor', 'plugins', 'local', 'handbuilt-cad')
if (-not $destTrim.EndsWith($tail, [StringComparison]::OrdinalIgnoreCase)) {
  Write-Host 'Refusing to remove an unexpected folder.'
  exit 1
}
if ($destTrim.Equals($srcTrim, [StringComparison]::OrdinalIgnoreCase) -or
    $destTrim.StartsWith($srcTrim + '\', [StringComparison]::OrdinalIgnoreCase) -or
    $destTrim.StartsWith($srcTrim + '/', [StringComparison]::OrdinalIgnoreCase)) {
  Write-Host 'Refusing to copy the plugin into its own folder.'
  exit 1
}
Write-Host "Cursor copy: $fullDest"
if ($dry) {
  Write-Host 'WhatIf: browser was not opened. Nothing was copied. Nothing was scheduled.'
  exit 0
}

if (Test-Path -LiteralPath $fullDest) {
  Remove-Item -LiteralPath $fullDest -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $fullDest | Out-Null
foreach ($name in @('.cursor-plugin', 'skills')) {
  $from = Join-Path $fullSrc $name
  if (-not (Test-Path -LiteralPath $from -PathType Container)) {
    Write-Host "Missing $name in $fullSrc"
    exit 1
  }
  Copy-Item -LiteralPath $from -Destination (Join-Path $fullDest $name) -Recurse -Force
}
Write-Host "Copied handbuilt-cad to $fullDest. Fully quit and reopen Cursor."

if ($UserHome) {
  Write-Host 'browser was not opened (test home). Nothing was scheduled.'
  exit 0
}

Write-Host 'This script does not open a browser.'
Write-Host 'Nothing was scheduled.'
exit 0
