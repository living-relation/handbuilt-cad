# link-skills.ps1 - link handbuilt-cad's skills (skills\<name>\SKILL.md) into ~\.claude\skills and ~\.cursor\skills as junctions,
# so a git pull here updates them. handbuilt-cad's setup.ps1 runs it; it owns these links (no other repo installs them).
# Usage: .\scripts\link-skills.ps1 [-From <dir>] [-WhatIf]  (default -From = this clone's skills\)
# A same-name skill that is not already this link is moved to -BackupRoot first; never touches other skills.
# The only delete: a junction into -From whose skill is gone (renamed or removed) is removed - the link only.
# -Unlink: folders (default none) where an old junction into -From is removed (the link only, never its target);
# anything else there is never touched. A folder that is also in -Targets is never unlinked.
[CmdletBinding(SupportsShouldProcess = $true)]
param([string[]]$From = @((Join-Path (Split-Path $PSScriptRoot -Parent) 'skills')),
      [string[]]$Targets = @("$env:USERPROFILE\.claude\skills", "$env:USERPROFILE\.cursor\skills"),
      [string[]]$Unlink = @(),
      [string]$BackupRoot = "$env:USERPROFILE\.skills-backup")
$ErrorActionPreference = 'Stop'
$stamp = Get-Date -Format yyyyMMdd-HHmmss
$seen = @{}
$plan = @()
foreach ($src in $From) {
  $src = (Resolve-Path -LiteralPath $src).Path
  foreach ($skill in Get-ChildItem -LiteralPath $src -Directory) {
    if (-not (Test-Path -LiteralPath (Join-Path $skill.FullName 'SKILL.md'))) { continue }
    if ($seen.ContainsKey($skill.Name)) { throw "skill '$($skill.Name)' is in both $($seen[$skill.Name]) and $src; fix one source first" }
    $seen[$skill.Name] = $src
    $plan += $skill
  }
}
foreach ($s in $plan) {
  $want = $s.FullName.TrimEnd('\')
  foreach ($t in $Targets) {
    $dest = Join-Path $t $s.Name
    $item = Get-Item -LiteralPath $dest -Force -ErrorAction SilentlyContinue
    if ($item -and $item.LinkType -eq 'Junction' -and (@($item.Target | ForEach-Object { $_.TrimEnd('\') }) -icontains $want)) {
      [pscustomobject]@{ Path = $dest; Target = $want; Action = 'ok' }; continue
    }
    if (-not $PSCmdlet.ShouldProcess($dest, "link -> $want")) { [pscustomobject]@{ Path = $dest; Target = $want; Action = 'would-link' }; continue }
    New-Item -ItemType Directory -Force $t | Out-Null
    $backup = $null
    if ($item) {
      $backup = Join-Path $BackupRoot "$stamp\$(Split-Path (Split-Path $t) -Leaf)\$($s.Name)"
      New-Item -ItemType Directory -Force (Split-Path $backup) | Out-Null
      Move-Item -LiteralPath $dest $backup
    }
    New-Item -ItemType Junction -Path $dest -Target $want | Out-Null
    [pscustomobject]@{ Path = $dest; Target = $want; Action = $(if ($backup) { "relinked; the old one is backed up at $backup" } else { 'linked' }) }
  }
}
# Prune: remove only junctions in -Targets that point into a -From folder at a skill that is gone (the link only, never
# its target). Links to anything else, and real folders, are never touched.
$roots = @($From | ForEach-Object { (Resolve-Path -LiteralPath $_).Path.TrimEnd('\') + '\' })
foreach ($t in $Targets) {
  foreach ($item in @(Get-ChildItem -LiteralPath $t -Force -ErrorAction SilentlyContinue | Where-Object { $_.LinkType -eq 'Junction' })) {
    $tgt = "$(@($item.Target)[0])".TrimEnd('\')
    if (-not @($roots | Where-Object { $tgt.StartsWith($_, [StringComparison]::OrdinalIgnoreCase) }).Count) { continue }
    if (Test-Path -LiteralPath (Join-Path $tgt 'SKILL.md')) { continue }
    if (-not $PSCmdlet.ShouldProcess($item.FullName, "remove dead skill link -> $tgt")) { [pscustomobject]@{ Path = $item.FullName; Target = $tgt; Action = 'would-prune' }; continue }
    [IO.Directory]::Delete($item.FullName, $false)
    [pscustomobject]@{ Path = $item.FullName; Target = $tgt; Action = 'pruned' }
  }
}
# Unlink: remove only junctions in -Unlink folders that point into a -From folder (the link only, never its target),
# e.g. to retire an old link folder. Real folders and links to anything else are never touched.
foreach ($u in @($Unlink | Where-Object { $_ -and ($Targets -notcontains $_) })) {
  foreach ($item in @(Get-ChildItem -LiteralPath $u -Force -ErrorAction SilentlyContinue | Where-Object { $_.LinkType -eq 'Junction' })) {
    $tgt = "$(@($item.Target)[0])".TrimEnd('\')
    if (-not @($roots | Where-Object { ($tgt + '\').StartsWith($_, [StringComparison]::OrdinalIgnoreCase) }).Count) { continue }
    if (-not $PSCmdlet.ShouldProcess($item.FullName, "remove duplicate skill link -> $tgt")) { [pscustomobject]@{ Path = $item.FullName; Target = $tgt; Action = 'would-unlink' }; continue }
    [IO.Directory]::Delete($item.FullName, $false)
    [pscustomobject]@{ Path = $item.FullName; Target = $tgt; Action = 'unlinked' }
  }
}
