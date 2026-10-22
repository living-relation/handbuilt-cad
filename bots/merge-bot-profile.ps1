# merge-bot-profile.ps1 - prepare a Grok Bot bot profile (*.profile.json, see PROFILE-FORMAT.md) for adding or merging.
# Generic: works on any profile file; not tied to any repo (other repos may vendor it).
#
# It never talks to Grok Bot and never touches any bot's memory, chats or routines. Grok Bot has no import API this
# script uses. It only WRITES FILES into -OutDir:
#   <slug>.<new|update|merged>.json   the profile to apply
#   <slug>.md                         a paste sheet: name, title, description and rules, plus how to apply them in Grok Bot
#   <slug>.conflicts.txt              conflicts it kept the existing value for (merge only)
#   backup\<time>\<slug>.existing.json  a copy of the existing bot's profile, made before any update or merge
#
# Existing bot detection (read-only), in this order:
#   -Existing <file>        a JSON copy of the current bot's profile (name/title/description/rules)
#   -ExistingDir <folder>   searched for *.json / */profile.json whose "name" matches (case-insensitive). No default:
#                           only the file or folder you pass is read.
#   otherwise (interactive) asks "Does a Grok Bot named X already exist?" and, if yes, for a JSON copy of its profile.
#   otherwise (non-interactive) it warns and SKIPS the bot (it can't tell whether one exists; never 'new' by guess).
#
# For an existing bot: -Mode merge (default) | update | skip | ask (interactive asks per bot, default merge).
#   merge  = keep the existing fields, append the repo rules it doesn't already have, and ask about each conflict
#            (non-interactive: keep the existing one and log it)
#   update = replace the profile and rules with the repo version
#   skip   = leave it
[CmdletBinding(SupportsShouldProcess = $true)]
param([Parameter(Mandatory = $true)][string]$ProfilePath,
      [string]$Existing,
      [string]$ExistingDir,
      [ValidateSet('ask', 'merge', 'update', 'skip')][string]$Mode = 'ask',
      [string]$OutDir = (Join-Path ([IO.Path]::GetTempPath()) 'bot-profiles'),
      [switch]$NonInteractive)
$ErrorActionPreference = 'Stop'
$Fields = 'name', 'title', 'description', 'avatarShape', 'avatarColor'
$Interactive = -not $NonInteractive -and [Environment]::UserInteractive -and -not $WhatIfPreference

function Read-Profile([string]$Path) {
  $o = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
  $p = [ordered]@{ schema = 1 }
  foreach ($f in $Fields) { $p[$f] = if ($null -ne $o.$f) { [string]$o.$f } else { '' } }
  $p.rules = @(if ($o.rules) { @($o.rules | ForEach-Object { [string]$_ }) })
  $extra = @($o.PSObject.Properties.Name | Where-Object { $_ -notin ($Fields + 'rules', 'schema') })
  if ($extra) { Write-Warning "$(Split-Path $Path -Leaf): dropped keys not in the profile format: $($extra -join ', ')" }
  return $p
}
function Norm([string]$t) { (($t.ToLowerInvariant() -replace '\s+', ' ').Trim()).TrimEnd('.', '!', ';', ',', ' ') }
function Label([string]$t) { $i = $t.IndexOf(':'); if ($i -gt 0 -and $i -le 40) { return (Norm $t.Substring(0, $i)) } return $null }
function Ask([string]$q, [string]$default) { if (-not $Interactive) { return $default }; $a = Read-Host $q; if ([string]::IsNullOrWhiteSpace($a)) { $default } else { $a.Trim().ToLowerInvariant() } }
function Find-Existing([string]$Name) {
  if ($Existing) { return (Read-Profile $Existing) }
  $dir = $ExistingDir
  if ($dir -and (Test-Path -LiteralPath $dir)) {
    foreach ($f in @(Get-ChildItem -LiteralPath $dir -Recurse -Depth 1 -File -Include '*.json' -ErrorAction SilentlyContinue)) {
      try { $o = Get-Content -LiteralPath $f.FullName -Raw | ConvertFrom-Json } catch { continue }
      if ($o.name -and ([string]$o.name).Trim() -ieq $Name.Trim()) { return (Read-Profile $f.FullName) }
    }
  }
  if ($Interactive -and ((Ask "Does a Grok Bot named '$Name' already exist? [y/N]" 'n') -match '^y')) {
    $p = Read-Host "Path to a JSON copy of its current profile (name, title, description, rules); blank = compare by hand"
    if ($p) { return (Read-Profile $p) }
    return 'unknown'
  }
  if (-not $Interactive -and -not $ExistingDir) { return 'unchecked' }
  return $null
}
function Write-Out($P, [string]$Kind, [string]$Note) {
  $slug = ($P.name.ToLowerInvariant() -replace '[^a-z0-9]+', '-').Trim('-')
  $json = Join-Path $OutDir "$slug.$Kind.json"; $md = Join-Path $OutDir "$slug.md"
  if (-not $PSCmdlet.ShouldProcess($json, "write $Kind profile for '$($P.name)'")) { return }
  New-Item -ItemType Directory -Force $OutDir | Out-Null
  [IO.File]::WriteAllText($json, ([pscustomobject]$P | ConvertTo-Json -Depth 4), (New-Object Text.UTF8Encoding($false)))
  $rules = if ($P.rules.Count) { ($P.rules | ForEach-Object { "- $_" }) -join "`n" } else { '(none)' }
  $sheet = @"
# $($P.name) ($Kind)

$Note

How to apply (by hand, in Grok Bot; this file does nothing by itself):
1. In Grok Bot, $(if ($Kind -eq 'new') { "first check that no bot named '$($P.name)' exists. If none does, create a new bot" } else { "open the existing bot '$($P.name)' and its profile/settings" }).
2. Copy the fields below into the bot's profile. Put the rules into the bot's description/instructions, one per line.
3. Don't change the bot's memory, chats or routines.

Name: $($P.name)
Title: $($P.title)
Avatar: $($P.avatarShape) $($P.avatarColor)
Description:
$($P.description)

Rules:
$rules
"@
  [IO.File]::WriteAllText($md, $sheet, (New-Object Text.UTF8Encoding($false)))
  [pscustomobject]@{ Bot = $P.name; Action = $Kind; File = $json; Sheet = $md }
}

$repo = Read-Profile $ProfilePath
$cur = Find-Existing $repo.name
if ($cur -eq 'unchecked') { Write-Warning "Bot '$($repo.name)': no -Existing/-ExistingDir given, so it can't be checked for an existing bot. Skipped; rerun with -ExistingDir or interactively."; return [pscustomobject]@{ Bot = $repo.name; Action = 'skip (not checked)'; File = $null; Sheet = $null } }
if (-not $cur) { return (Write-Out $repo 'new' 'No existing bot with this name was found.') }
if ($cur -eq 'unknown') { return (Write-Out $repo 'new' "A bot named '$($repo.name)' exists, but its profile wasn't given. Compare it by hand before changing anything.") }

$m = $Mode
if ($m -eq 'ask') { $a = Ask "Bot '$($repo.name)' already exists: [M]erge (default), [U]pdate profile and rules, or [S]kip (leave it)?" 'm'; $m = switch -regex ($a) { '^u' { 'update' } '^s' { 'skip' } default { 'merge' } } }
if ($m -eq 'skip') { return [pscustomobject]@{ Bot = $repo.name; Action = 'skip'; File = $null; Sheet = $null } }

$slug = ($repo.name.ToLowerInvariant() -replace '[^a-z0-9]+', '-').Trim('-')
$bk = Join-Path $OutDir ("backup\" + (Get-Date -Format yyyyMMdd-HHmmss) + "\$slug.existing.json")
if ($PSCmdlet.ShouldProcess($bk, "back up the existing profile of '$($repo.name)'")) {
  New-Item -ItemType Directory -Force (Split-Path $bk) | Out-Null
  [IO.File]::WriteAllText($bk, ([pscustomobject]$cur | ConvertTo-Json -Depth 4), (New-Object Text.UTF8Encoding($false)))
}
if ($m -eq 'update') { return (Write-Out $repo 'update' "Replaces the profile and rules of the existing bot. The old profile is backed up at $bk.") }

# merge
$out = [ordered]@{ schema = 1 }; $log = @()
foreach ($f in $Fields) {
  $e = $cur[$f]; $r = $repo[$f]
  if ([string]::IsNullOrWhiteSpace($e)) { $out[$f] = $r }
  elseif ([string]::IsNullOrWhiteSpace($r) -or (Norm $e) -eq (Norm $r)) { $out[$f] = $e }
  else {
    if ($Interactive) { Write-Host "`n$($repo.name) / $f`n  [E] existing: $e`n  [R] repo:     $r" }
    $out[$f] = if ((Ask "Keep [E]xisting (default) or [R]epo?" 'e') -match '^r') { $r } else { $e }
    if ($out[$f] -eq $e) { $log += "field ${f}: kept the existing value; repo value was: $r" }
  }
}
$rules = New-Object System.Collections.Generic.List[string]; foreach ($x in $cur.rules) { $rules.Add($x) }
foreach ($r in $repo.rules) {
  if (@($rules | Where-Object { (Norm $_) -eq (Norm $r) }).Count) { continue }
  $lab = Label $r; $clash = if ($lab) { @($rules | Where-Object { (Label $_) -eq $lab }) } else { @() }
  if ($clash.Count) {
    if ($Interactive) { Write-Host "`n$($repo.name) / rule '$lab'`n  [E] existing: $($clash[0])`n  [R] repo:     $r" }
    if ((Ask "Keep [E]xisting (default) or [R]epo?" 'e') -match '^r') { $rules[$rules.IndexOf($clash[0])] = $r } else { $log += "rule '$lab': kept the existing rule; repo rule was: $r" }
  } else { $rules.Add($r) }
}
$out.rules = @($rules)
$res = Write-Out $out 'merged' "Merged into the existing bot: existing fields kept, missing repo rules added. Old profile backed up at $bk."
if ($log.Count -and $res -and $PSCmdlet.ShouldProcess("$slug.conflicts.txt", 'write conflicts')) {
  [IO.File]::WriteAllLines((Join-Path $OutDir "$slug.conflicts.txt"), [string[]]$log)
}
$res
