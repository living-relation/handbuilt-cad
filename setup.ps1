# handbuilt-cad setup for the one Windows clone (the only clone; WSL reaches it through a link). Safe to re-run.
#   powershell -NoProfile -ExecutionPolicy Bypass -File setup.ps1 [-NoModels] [-NoVenv] [-LinkSkills] [-NoSim] [-NoWsl] [-NoPopup] [-Quiet] [-WslDistro Ubuntu] [-WslLink <wsl path>] [-FreeCADDir <dir>]
#   Also links this clone into WSL (~/projects/handbuilt-cad) and runs the WSL half (setup.sh) there, so this one command
#   does the whole install. -NoWsl skips it. -LinkSkills is a no-op (skills always go into ~\.claude\skills).
#   -NoPopup / -Quiet skip the Claude skill-zip upload popup (also skipped in CI).
param([switch]$NoModels, [switch]$NoVenv, [switch]$LinkSkills, [switch]$NoSim, [switch]$NoWsl, [switch]$NoPopup, [switch]$Quiet, [string]$WslDistro = 'Ubuntu', [string]$WslLink = '', [string]$FreeCADDir = '')
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
elseif (Test-Path -LiteralPath $models -PathType Container) { Write-Host "models folder: $models (exists, left as is)" }
elseif (Test-Path -LiteralPath $models) { throw "models folder: STOP: $models exists but is not a folder (a file?). Nothing changed. Rename or remove it, or set MODELS_DIR / [paths] models_dir to a folder, then re-run." }
else { New-Item -ItemType Directory -Path $models | Out-Null; Write-Host "models folder: created $models" }
# Part build scripts and their run outputs live in WSL/Linux (~/cad-parts, HBCAD_PARTS_HOME); setup.sh in WSL creates that folder.
Write-Host "parts home: created by setup.sh in WSL (~/cad-parts, step 6 below), not on Windows"
# 4b. folder notes (models folder and parts home) have one writer, tools/folder_notes.py, run by setup.sh step 5d in WSL.
if (-not $NoModels) { Write-Host "models notes: added by setup.sh in WSL (tools/folder_notes.py, step 6 below), not on Windows" }

# 4c. skills: always junction skills\<name> into ~\.claude\skills (Cursor reads that folder too;
#     do not also link into ~\.cursor\skills). -LinkSkills is a no-op kept for old commands.
#     A same-name folder is backed up to ~\.skills-backup first; nothing is deleted.
if ($LinkSkills) { Write-Host 'skills: -LinkSkills is a no-op (already linked into ~/.claude/skills)' }
& "$Root\scripts\link-skills.ps1" | ForEach-Object { Write-Host "skill $($_.Action): $($_.Path)" }

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
#    -NoSim -> --no-sim. Skip with -NoWsl. Fails clearly if WSL or the distro is missing.
#    Skills are always linked (WSL setup.sh does the same); -LinkSkills is a no-op.
if ($NoWsl) { Write-Host "WSL setup: skipped (-NoWsl). Link this clone into WSL and run 'bash setup.sh' there yourself." }
else {
  if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { throw "WSL setup: wsl.exe not found. Install WSL ('wsl --install -d $WslDistro'), or re-run with -NoWsl." }
  $distros = (& wsl.exe --list --quiet 2>$null) -replace "`0", '' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
  if ($distros -notcontains $WslDistro) { throw "WSL setup: distro '$WslDistro' not found (have: $($distros -join ', ')). Install it ('wsl --install -d $WslDistro'), pass -WslDistro <name>, or re-run with -NoWsl." }
  $shArgs = @()
  if ($NoModels) { $shArgs += '--no-models' }
  if ($NoSim) { $shArgs += '--no-sim' }   # sim tools (apt, sim venv) install by default; apt runs as root via wsl.exe, no password
  # bash single-quote a value: ' -> '\'' (so paths with spaces, $, quotes or backticks pass through literally)
  $sq = { param($x) "'" + ($x -replace "'", "'\''") + "'" }
  $envPrefix = if ($env:MODELS_DIR) { "MODELS_DIR=`"`$(wslpath -u $(& $sq $env:MODELS_DIR))`" " } else { '' }
  $lc = ''
  foreach ($line in (Get-Content "$Root\local.toml" -ErrorAction SilentlyContinue)) {
    if ($line -match '^\s*\[([^\]]*)\]') { $sec = $Matches[1].Trim(); continue }
    if ($sec -eq 'paths' -and $line -match "^\s*wsl_link\s*=\s*['`"]([^'`"]*)['`"]") { $lc = $Matches[1]; break }
  }
  $link = @($WslLink, $lc, '~/projects/handbuilt-cad') | Where-Object { $_ } | Select-Object -First 1
  # wsl_link / -WslLink must be a Linux path: ~/... or /..., no '..' parts, no control characters, not a Windows path.
  if ($link -notmatch '^(~/|/)[^\x00-\x1f]+$' -or $link -match '(^|/)\.\.(/|$)' -or $link -match '\\' -or $link -match '^/mnt/[a-z]/') {
    throw "WSL setup: wsl_link '$link' is not valid. Use a Linux path such as ~/projects/handbuilt-cad (not a Windows or /mnt path, no '..'). Nothing changed."
  }
  $q = { param($x) if ($x -like '~/*') { '"$HOME"/' + (& $sq $x.Substring(2)) } else { & $sq $x } }
  $cmd = "set -e; t=`$(wslpath -u $(& $sq $Root)); l=$(& $q $link); " +
         "if [ -L `"`$l`" ]; then " +
           "if [ `"`$(readlink -f `"`$l`")`" = `"`$(readlink -f `"`$t`")`" ]; then echo `"WSL setup: link `$l -> `$t (exists, left as is)`"; " +
           "else echo `"WSL setup: STOP: `$l is a link to `$(readlink `"`$l`"), not this clone (`$t). Nothing changed. Fix or remove that link yourself, then re-run.`"; exit 3; fi; " +
         "elif [ -e `"`$l`" ]; then echo `"WSL setup: STOP: `$l is a real folder or file (an old WSL clone?). Nothing changed. Move it to an archive yourself (e.g. ~/cad-parts/_archive/handbuilt-cad-wsl-<date>), then re-run.`"; exit 3; " +
         "else mkdir -p `"`$(dirname `"`$l`")`"; ln -s `"`$t`" `"`$l`"; echo `"WSL setup: linked `$l -> `$t`"; fi; " +
         "export UV_PROJECT_ENVIRONMENT=`"`${UV_PROJECT_ENVIRONMENT:-`$HOME/.venvs/handbuilt-cad}`"; " +
         "cd `"`$l`"; ${envPrefix}bash setup.sh $($shArgs -join ' ')"
  # Sim apt packages as root through wsl.exe (no WSL password needed). Pins and CRLF stripped: pins may not match a newer Ubuntu.
  if (-not $NoSim) {
    $pkgs = (Get-Content "$Root\apt-sim.txt") | ForEach-Object { ($_ -replace "`r", '' -replace '#.*$', '' -replace '=.*$', '').Trim() } | Where-Object { $_ }
    Write-Host "WSL sim apt (as root): $($pkgs -join ' ')"
    & wsl.exe -d $WslDistro -u root -e bash -c "DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y $($pkgs -join ' ')"
    if ($LASTEXITCODE -ne 0) { throw "WSL sim apt: failed in $WslDistro (exit $LASTEXITCODE). Fix the error above and re-run, or use -NoSim." }
  }
  Write-Host "WSL setup: wsl -d $WslDistro (link $link, setup.sh $($shArgs -join ' '))"
  # Windows PowerShell 5.1 does not escape the double quotes inside $cmd when it builds wsl.exe's command line, so
  # bash got a broken script ("syntax error near unexpected token"). Pass it base64-encoded instead: the encoded
  # text has no quotes or spaces, so it survives 5.1 and 7.x alike. The script is one line, so bash has read all of
  # it before it runs; stdin is then pointed at /dev/null so nothing in setup.sh can read the rest of the pipe.
  $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("exec </dev/null; $cmd"))
  & wsl.exe -d $WslDistro -- bash -lc "echo $b64 | base64 -d | bash"
  if ($LASTEXITCODE -ne 0) { throw "WSL setup: failed in $WslDistro (exit $LASTEXITCODE). Fix the error above and re-run, or use -NoWsl." }
}
Write-Host "Optional: setx MODELS_DIR `"$models`"  (setup does not change user env vars)"
# 7. Claude desktop skill-zip reminder (separate Windows popup). install.cmd runs this script, so
#    double-click install and `setup.ps1` both show it. Skip with -NoPopup / -Quiet or when CI is set.
#    A GUI failure must not fail the install.
try { & "$Root\scripts\skill-upload-popup.ps1" -NoPopup:$NoPopup -Quiet:$Quiet }
catch { Write-Host "skills popup: skipped ($($_.Exception.Message))" }
