# handbuilt-cad setup for the one Windows clone (the only clone; WSL reaches it through a link). Safe to re-run.
#   powershell -NoProfile -ExecutionPolicy Bypass -File setup.ps1 [-NoModels] [-NoVenv] [-LinkSkills] [-NoWsl] [-WslDistro Ubuntu] [-WslLink <wsl path>] [-FreeCADDir <dir>]
#   Also links this clone into WSL (~/projects/handbuilt-cad) and runs the WSL half (setup.sh) there, so this one command
#   does the whole install. -NoWsl skips it.
param([switch]$NoModels, [switch]$NoVenv, [switch]$LinkSkills, [switch]$NoWsl, [string]$WslDistro = 'Ubuntu', [string]$WslLink = '', [string]$FreeCADDir = '')
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

# 2. Windows venv (<repo>\.venv, optional). The WSL half keeps its Linux venv outside the repo (~/.venvs/handbuilt-cad).
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
Write-Host "parts home: created by setup.sh in WSL (~/cad-parts, step 6 below), not on Windows"
# 4b. folder notes (models folder and parts home) have one writer, tools/folder_notes.py, run by setup.sh step 5d in WSL.
if (-not $NoModels) { Write-Host "models notes: added by setup.sh in WSL (tools/folder_notes.py, step 6 below), not on Windows" }

# 4c. skills: off by default. Only with -LinkSkills: junction skills\<name> into ~\.claude\skills and ~\.cursor\skills
#     (a same-name folder is backed up to ~\.skills-backup first; nothing is deleted).
if (-not $LinkSkills) { Write-Host 'skills: not linked (opt in with -LinkSkills)' }
else { & "$Root\scripts\link-skills.ps1" | ForEach-Object { Write-Host "skill $($_.Action): $($_.Path)" } }

# 5. FreeCAD launcher wrappers (only into an existing FreeCAD folder you name; never overwrites)
if ($FreeCADDir) {
  foreach ($b in Get-ChildItem "$Root\sim\freecad\*.bat" -ErrorAction SilentlyContinue) {
    $dst = Join-Path $FreeCADDir $b.Name
    if (Test-Path $dst) { Write-Host "skip $dst (exists)" } else { Copy-Item $b.FullName $dst; Write-Host "added $dst" }
  }
}
# 6. WSL half: one clone only. Link this Windows clone into WSL (default ~/projects/handbuilt-cad, or -WslLink, or
#    [paths] wsl_link in local.toml) and run setup.sh through the link. Never clones in WSL. Idempotent: a link that
#    already points here is left as is. Never overwrites: if the path is a real folder/file (an old WSL clone?) or a
#    link to somewhere else, it stops and changes nothing. The Linux venv goes to $UV_PROJECT_ENVIRONMENT
#    (default ~/.venvs/handbuilt-cad), so it never clashes with the Windows .venv. Passes -NoModels -> --no-models,
#    -LinkSkills -> --link-skills. Skip with -NoWsl. Fails clearly if WSL or the distro is missing.
if ($NoWsl) { Write-Host "WSL setup: skipped (-NoWsl). Link this clone into WSL and run 'bash setup.sh' there yourself." }
else {
  if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { throw "WSL setup: wsl.exe not found. Install WSL ('wsl --install -d $WslDistro'), or re-run with -NoWsl." }
  $distros = (& wsl.exe --list --quiet 2>$null) -replace "`0", '' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
  if ($distros -notcontains $WslDistro) { throw "WSL setup: distro '$WslDistro' not found (have: $($distros -join ', ')). Install it ('wsl --install -d $WslDistro'), pass -WslDistro <name>, or re-run with -NoWsl." }
  $shArgs = @()
  if ($NoModels) { $shArgs += '--no-models' }
  if ($LinkSkills) { $shArgs += '--link-skills' }
  $envPrefix = if ($env:MODELS_DIR) { "MODELS_DIR=`"`$(wslpath -u '$($env:MODELS_DIR)')`" " } else { '' }
  $lc = ''
  foreach ($line in (Get-Content "$Root\local.toml" -ErrorAction SilentlyContinue)) {
    if ($line -match '^\s*\[([^\]]*)\]') { $sec = $Matches[1].Trim(); continue }
    if ($sec -eq 'paths' -and $line -match "^\s*wsl_link\s*=\s*['`"]([^'`"]*)['`"]") { $lc = $Matches[1]; break }
  }
  $link = @($WslLink, $lc, '~/projects/handbuilt-cad') | Where-Object { $_ } | Select-Object -First 1
  $q = { param($x) if ($x -like '~/*') { '"$HOME/' + $x.Substring(2) + '"' } else { "'" + $x + "'" } }
  $cmd = "set -e; t=`$(wslpath -u '$Root'); l=$(& $q $link); " +
         "if [ -L `"`$l`" ]; then " +
           "if [ `"`$(readlink -f `"`$l`")`" = `"`$(readlink -f `"`$t`")`" ]; then echo `"WSL setup: link `$l -> `$t (exists, left as is)`"; " +
           "else echo `"WSL setup: STOP: `$l is a link to `$(readlink `"`$l`"), not this clone (`$t). Nothing changed. Fix or remove that link yourself, then re-run.`"; exit 3; fi; " +
         "elif [ -e `"`$l`" ]; then echo `"WSL setup: STOP: `$l is a real folder or file (an old WSL clone?). Nothing changed. Move it to an archive yourself (e.g. ~/cad-parts/_archive/handbuilt-cad-wsl-<date>), then re-run.`"; exit 3; " +
         "else mkdir -p `"`$(dirname `"`$l`")`"; ln -s `"`$t`" `"`$l`"; echo `"WSL setup: linked `$l -> `$t`"; fi; " +
         "export UV_PROJECT_ENVIRONMENT=`"`${UV_PROJECT_ENVIRONMENT:-`$HOME/.venvs/handbuilt-cad}`"; " +
         "cd `"`$l`"; ${envPrefix}bash setup.sh $($shArgs -join ' ')"
  Write-Host "WSL setup: wsl -d $WslDistro (link $link, setup.sh $($shArgs -join ' '))"
  & wsl.exe -d $WslDistro -- bash -lc $cmd
  if ($LASTEXITCODE -ne 0) { throw "WSL setup: failed in $WslDistro (exit $LASTEXITCODE). Fix the error above and re-run, or use -NoWsl." }
}
Write-Host "Optional: setx MODELS_DIR `"$models`"  (setup does not change user env vars)"
