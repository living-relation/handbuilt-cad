# handbuilt-cad setup for a Windows clone (pull-only copy). Safe to re-run.
#   powershell -NoProfile -ExecutionPolicy Bypass -File setup.ps1 [-NoModels] [-NoVenv] [-NoSkills] [-FreeCADDir <dir>]
param([switch]$NoModels, [switch]$NoVenv, [switch]$NoSkills, [string]$FreeCADDir = '')
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
Set-Location $Root
$GlVer = (Get-Content "$Root\.gitleaks-version" -Raw).Trim()
$GlSha = 'd29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e'  # gitleaks_8.30.1_windows_x64.zip
$UvVer = '0.13.0'
$UvSha = '088962f9e7b7bd9ea740c04c650b2a21c8928c345bd99ac24350dc924dba656c'  # uv-x86_64-pc-windows-msvc.zip
$Tools = Join-Path $Root '.tools'
New-Item -ItemType Directory -Force $Tools | Out-Null

function Get-Pinned($url, $sha, $zip) {
  Invoke-WebRequest -UseBasicParsing $url -OutFile $zip
  $h = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
  if ($h -ne $sha) { Remove-Item $zip; throw "sha256 mismatch for $url" }
  Expand-Archive $zip -DestinationPath $Tools -Force; Remove-Item $zip
}

# 1. pinned gitleaks + hooks path
$gl = Join-Path $Tools 'gitleaks.exe'
if (-not (Test-Path $gl) -or ((& $gl version) -replace 'v','') -ne $GlVer) {
  Get-Pinned "https://github.com/gitleaks/gitleaks/releases/download/v$GlVer/gitleaks_${GlVer}_windows_x64.zip" $GlSha "$Tools\gl.zip"
}
git config core.hooksPath .githooks
Write-Host "gitleaks $(& $gl version); hooks path set"

# 2. venv (optional on Windows; WSL is the working copy)
if (-not $NoVenv) {
  $uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
  if (-not $uv -or ((& $uv --version).Split(' ')[1]) -ne $UvVer) {
    $uv = Join-Path $Tools 'uv.exe'
    if (-not (Test-Path $uv)) { Get-Pinned "https://github.com/astral-sh/uv/releases/download/$UvVer/uv-x86_64-pc-windows-msvc.zip" $UvSha "$Tools\uv.zip" }
  }
  & $uv python install (Get-Content "$Root\.python-version" -Raw).Trim()
  & $uv sync --frozen
}

# 3. local settings
if (-not (Test-Path "$Root\local.toml")) { Copy-Item "$Root\local.toml.example" "$Root\local.toml" }

# 4. models folder. Order: $env:MODELS_DIR, then [paths] models_dir in local.toml, then <Desktop>\models.
#    <Desktop> is the OneDrive Desktop when OneDrive keeps one (even if the Windows Desktop known folder
#    was not redirected to it), else [Environment]::GetFolderPath('Desktop'). An existing folder is never touched.
function Get-RealDesktop {
  $d = [Environment]::GetFolderPath('Desktop')
  foreach ($o in @($env:OneDriveConsumer, $env:OneDrive, $env:OneDriveCommercial)) {
    if ($o -and -not $d.StartsWith($o, [StringComparison]::OrdinalIgnoreCase)) {
      $od = Join-Path $o 'Desktop'
      if (Test-Path -LiteralPath $od -PathType Container) { return $od }
    }
  }
  return $d
}
function Get-LocalModelsDir {
  $f = Join-Path $Root 'local.toml'
  if (-not (Test-Path -LiteralPath $f)) { return '' }
  foreach ($line in Get-Content -LiteralPath $f) {
    if ($line -match "^\s*models_dir\s*=\s*'([^']*)'") { return $Matches[1] }
    if ($line -match '^\s*models_dir\s*=\s*"((?:[^"\\]|\\.)*)"') { return ($Matches[1] -replace '\\\\', '\') }
  }
  return ''
}
$models = if ($env:MODELS_DIR) { $env:MODELS_DIR }
          elseif ($lm = Get-LocalModelsDir) { $lm }
          else { Join-Path (Get-RealDesktop) 'models' }
if ($NoModels) { Write-Host "models folder: $models (not created: -NoModels)" }
elseif (Test-Path -LiteralPath $models) { Write-Host "models folder: $models (exists, left as is)" }
else { New-Item -ItemType Directory -Path $models | Out-Null; Write-Host "models folder: created $models" }
# Part build scripts and their run outputs live in WSL/Linux (~/cad-parts, HBCAD_PARTS_HOME); setup.sh in WSL creates that folder.
Write-Host "parts home: created by setup.sh in WSL (~/cad-parts), not on Windows"
# 4b. folder notes (models folder and parts home) have one writer, tools/folder_notes.py, run by setup.sh step 5d in WSL.
if (-not $NoModels) { Write-Host "models notes: added by 'bash setup.sh' in WSL (tools/folder_notes.py), not on Windows" }

# 4c. skills: handbuilt-cad owns its skill links. Junction skills\<name> into ~\.claude\skills and ~\.cursor\skills
#     (a same-name folder is backed up to ~\.skills-backup first; nothing is deleted). Skip with -NoSkills.
if ($NoSkills) { Write-Host 'skills: not linked (-NoSkills)' }
else { & "$Root\scripts\link-skills.ps1" | ForEach-Object { Write-Host "skill $($_.Action): $($_.Path)" } }

# 5. FreeCAD launcher wrappers (only into an existing FreeCAD folder you name; never overwrites)
if ($FreeCADDir) {
  foreach ($b in Get-ChildItem "$Root\sim\freecad\*.bat" -ErrorAction SilentlyContinue) {
    $dst = Join-Path $FreeCADDir $b.Name
    if (Test-Path $dst) { Write-Host "skip $dst (exists)" } else { Copy-Item $b.FullName $dst; Write-Host "added $dst" }
  }
}
Write-Host "Optional: setx MODELS_DIR `"$models`"  (setup does not change user env vars)"
