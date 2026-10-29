#!/usr/bin/env bash
# handbuilt-cad setup for WSL/Linux. Safe to re-run. Touches only this repo, ~/.cache/uv,
# uv's Python store, and (unless --no-models) creates <Desktop>/models if it is missing. By default it also installs
# the sim tools (apt-sim.txt via sudo apt-get, the sim venv), uv in ~/.local/bin, and an env file loaded by login
# shells; then scripts/verify-install.sh checks everything and fails loudly if anything is missing.
#   bash setup.sh [--no-models] [--with-fairsolid] [--no-sim] [--no-profile] [--link-skills]
#   --link-skills is a no-op: skills are always linked into ~/.claude/skills.
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$PWD
# One clone: on Windows + WSL the repo lives on the Windows drive (/mnt/<x>/...) and WSL reaches it through a link
# (~/projects/handbuilt-cad). Its .venv is the Windows one, so the Linux venv goes outside the repo:
# $UV_PROJECT_ENVIRONMENT, default ~/.venvs/handbuilt-cad. Elsewhere (plain Linux) it stays <repo>/.venv.
case "$(pwd -P)" in /mnt/[a-z]/*) export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$HOME/.venvs/handbuilt-cad}";; esac
VENV="${UV_PROJECT_ENVIRONMENT:-$ROOT/.venv}"
case "$(pwd -P)" in /mnt/[a-z]/*)
  case "$(readlink -m "$VENV")" in "$(pwd -P)"/.venv|"$(pwd -P)"/.venv/*)
    echo "STOP: UV_PROJECT_ENVIRONMENT=$VENV is the Windows .venv inside this clone; a WSL uv sync would break it. Unset it or point it at ~/.venvs/handbuilt-cad." >&2; exit 2;; esac;;
esac
export UV_PROJECT_ENVIRONMENT="$VENV" CAD_PY="$VENV/bin/python"   # every uv call below (and child scripts) uses this venv
UV_VERSION=0.13.0
UV_SHA=1468ebd5a5541121837c5a2817b9972ba6090fa6caa3d142620850a47fb75154  # uv-x86_64-unknown-linux-gnu.tar.gz
NO_MODELS=0; WITH_FS=0; SIM=1; PROFILE=1; LINK_SKILLS=1
# --sim is the default now; still accepted so old commands keep working.
# --link-skills is a no-op (linking into ~/.claude/skills is the default).
for a in "$@"; do case $a in --no-models) NO_MODELS=1;; --with-fairsolid) WITH_FS=1;; --sim) SIM=1;; --no-sim) SIM=0;; --no-profile) PROFILE=0;; --link-skills) LINK_SKILLS=1;; *) echo "unknown option $a"; exit 2;; esac; done

# 1. pinned uv (use the one on PATH if it is the pinned version, else fetch into .tools/)
UV=$(command -v uv || true)
if [ -z "$UV" ] || [ "$("$UV" --version | awk '{print $2}')" != "$UV_VERSION" ]; then
  mkdir -p .tools; UV=$ROOT/.tools/uv
  if [ ! -x "$UV" ] || [ "$("$UV" --version | awk '{print $2}')" != "$UV_VERSION" ]; then
    curl -fsSL -o .tools/uv.tgz "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-unknown-linux-gnu.tar.gz"
    echo "$UV_SHA  .tools/uv.tgz" | sha256sum -c -
    tar xzf .tools/uv.tgz -C .tools --strip-components=1; rm .tools/uv.tgz
  fi
fi
echo "uv: $("$UV" --version)"

# 2. pinned Python + the venv ($VENV) from uv.lock (never touches any other venv)
echo "venv: $VENV"
"$UV" python install "$(cat .python-version)"
"$UV" sync --frozen
[ "$WITH_FS" = 1 ] && (cd pipelines/fairsolid && env -u UV_PROJECT_ENVIRONMENT "$UV" sync --frozen --extra test)

# 2b. uv on PATH for agents: copy the pinned uv into ~/.local/bin if no uv is there (never replaces one).
mkdir -p "$HOME/.local/bin"
for b in uv uvx; do
  if [ ! -e "$HOME/.local/bin/$b" ] && [ -x "$(dirname "$UV")/$b" ]; then install -m 755 "$(dirname "$UV")/$b" "$HOME/.local/bin/$b"; echo "uv: installed $HOME/.local/bin/$b"; fi
done

# 2c. sim tools (default; --no-sim skips). apt packages from apt-sim.txt (by name; the versions there are the
#     reference workstation's; setup.ps1 installs them first as root via wsl.exe, so no password), then the sim venv
#     ($SIM_VENV, default ~/simvenv, used by tools/quick_fea.py and examples/bracket) from requirements-sim.txt with
#     the pinned uv on the repo Python (.python-version; never the 3.14 system Python). A venv on another Python
#     (e.g. 3.12) is moved aside, not deleted.
SIM_VENV="${SIM_VENV:-$HOME/simvenv}"; APT_CMD=""
if [ "$SIM" = 1 ]; then
  # sim_apt_missing: apt-sim.txt package names that dpkg does not list as installed
  sim_apt_missing() {
    grep -v '^[[:space:]]*#' apt-sim.txt | sed 's/=.*//; s/[[:space:]]//g' | grep -v '^$' | while read -r p; do
      dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q 'install ok installed' || printf '%s ' "$p"
    done
  }
  # end sim_apt_missing
  need=$(sim_apt_missing)
  if [ -z "$need" ]; then echo "sim apt: all apt-sim.txt packages installed"
  else
    APT_CMD="sudo apt-get update && sudo apt-get install -y $need"
    export DEBIAN_FRONTEND=noninteractive
    if [ "$(id -u)" = 0 ]; then apt-get update && apt-get install -y $need
    elif sudo -n true 2>/dev/null; then sudo -n apt-get update && sudo -n apt-get install -y $need
    elif { : </dev/tty; } 2>/dev/null; then
      echo "sim apt: installing $need(sudo asks for your password)"
      sudo apt-get update && sudo apt-get install -y $need
    else
      echo "sim apt: STOP: no passwordless sudo and no terminal, so the sim tools were NOT installed." >&2
      echo "  On Windows + WSL, run setup.ps1 from Windows: it installs them as root through wsl.exe, no password." >&2
      echo "  Or paste in a terminal:  $APT_CMD" >&2
    fi
  fi
  SIM_PY="${SIM_PYTHON:-$(cat .python-version)}"
  if [ -x "$SIM_VENV/bin/python" ] && ! "$SIM_VENV/bin/python" -c "import sys; v='$SIM_PY'.split('.'); sys.exit(sys.version_info[:2] != (int(v[0]), int(v[1])))" 2>/dev/null; then
    old="$SIM_VENV.old-$(date +%Y%m%d-%H%M%S)"; mv "$SIM_VENV" "$old"; echo "sim venv: wrong Python, moved to $old (not deleted)"
  fi
  [ -x "$SIM_VENV/bin/python" ] || env -u UV_PROJECT_ENVIRONMENT "$UV" venv "$SIM_VENV" --python "$SIM_PY"
  env -u UV_PROJECT_ENVIRONMENT "$UV" pip install --python "$SIM_VENV/bin/python" -r requirements-sim.txt
  echo "sim venv: $SIM_VENV ($("$SIM_VENV/bin/python" -V))"
fi

# 3. hooks: pinned gitleaks + core.hooksPath so the hooks run on a fresh clone
sh scripts/fetch-gitleaks.sh
git config core.hooksPath .githooks

# 4. local settings
[ -f local.toml ] || cp local.toml.example local.toml

# toml_paths KEY: KEY's quoted value from the [paths] section of local.toml only (same rule as tools/paths.py).
toml_paths() {
  awk -v k="$1" -v sq="'" -v dq='"' '
    /^[[:space:]]*\[/ { s=$0; sub(/^[[:space:]]*\[/, "", s); sub(/\].*/, "", s); gsub(/[[:space:]]/, "", s); next }
    s == "paths" {
      l=$0; sub(/^[[:space:]]*/, "", l)
      if (substr(l, 1, length(k)) != k) next
      l=substr(l, length(k)+1); sub(/^[[:space:]]*/, "", l)
      if (substr(l, 1, 1) != "=") next
      l=substr(l, 2); sub(/^[[:space:]]*/, "", l); q=substr(l, 1, 1)
      if (q != sq && q != dq) next
      l=substr(l, 2); i=index(l, q); if (i) { print substr(l, 1, i-1); exit }
    }' local.toml 2>/dev/null || true
}
# end toml_paths

# 5. models folder. Order: $MODELS_DIR, then [paths] models_dir in local.toml, then <Desktop>/models.
#    On WSL, <Desktop> is the Windows OneDrive Desktop when OneDrive keeps one, else the Desktop known folder.
desktop=""
if command -v powershell.exe >/dev/null 2>&1; then
  win=$(powershell.exe -NoProfile -Command '$d=[Environment]::GetFolderPath("Desktop"); foreach($o in @($env:OneDriveConsumer,$env:OneDrive,$env:OneDriveCommercial)){ if($o -and -not $d.StartsWith($o,[StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath (Join-Path $o "Desktop") -PathType Container)){ $d=Join-Path $o "Desktop"; break } }; $d' | tr -d '\r')
  [ -n "$win" ] && desktop=$(wslpath -u "$win")
fi
[ -z "$desktop" ] && desktop=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
local_models=$(toml_paths models_dir)
case "$local_models" in [A-Za-z]:\\*|[A-Za-z]:/*) command -v wslpath >/dev/null 2>&1 && local_models=$(wslpath -u "$local_models");; esac
MODELS="${MODELS_DIR:-${local_models:-$desktop/models}}"
if [ "$NO_MODELS" = 1 ]; then echo "models folder: $MODELS (not created: --no-models)";
elif [ -d "$MODELS" ]; then echo "models folder: $MODELS (exists, left as is)";
elif [ -e "$MODELS" ] || [ -L "$MODELS" ]; then echo "models folder: STOP: $MODELS exists but is not a folder (a file or broken link). Nothing changed. Rename or remove it, or set MODELS_DIR / [paths] models_dir to a folder, then re-run." >&2; exit 3;
else mkdir -p "$MODELS"; echo "models folder: created $MODELS"; fi
# 5b. ownership notes in the models folder: written by tools/folder_notes.py in step 5d (single writer).

# 5c. part-scripts home (WSL/Linux only). Order: $HBCAD_PARTS_HOME, then [paths] parts_home in local.toml, then ~/cad-parts.
#     Creates <home>/ and <home>/_archive/ only when missing; step 5d adds the owner notes.
local_parts=$(toml_paths parts_home)
PARTS="${HBCAD_PARTS_HOME:-${local_parts:-$HOME/cad-parts}}"
for d in "$PARTS" "$PARTS/_archive"; do
  if [ -d "$d" ]; then echo "parts home: $d (exists, left as is)"; else mkdir -p "$d"; echo "parts home: created $d"; fi
done

# 5d. owner notes in every layout folder: parts home (AGENTS.md), _archive, each job/src/runs, the models folder
#     (AGENTS.md, README.md) and each models job. Add-only. A failure stops setup with folder_notes.py's exit status.
fn_args=(--quiet --parts-home "$PARTS")
if [ "$NO_MODELS" != 1 ] && [ -d "$MODELS" ]; then fn_args+=(--models "$MODELS"); else fn_args+=(--no-models); fi
HBCAD_PARTS_HOME="$PARTS" "$VENV/bin/python" tools/folder_notes.py "${fn_args[@]}"
# end 5d

# 6. skills: always symlink skills/<name> into ~/.claude/skills (Cursor reads that folder too;
#    do not also link into ~/.cursor/skills). --link-skills is a no-op kept for old commands.
#    A same-name entry is moved to ~/.skills-backup/<stamp>/ first. The only delete: a symlink
#    into this clone's skills/ whose skill is gone is removed (the link only). Old links this
#    repo made in ~/.cursor/skills are removed (the link only). On Windows, setup.ps1 does the
#    same with junctions (scripts/link-skills.ps1).
stamp=$(date +%Y%m%d-%H%M%S)
# Directories with SKILL.md only. Files (skills/<name>.zip, README.md) are not skills.
for s in "$ROOT"/skills/*/; do
  s=${s%/}; [ -f "$s/SKILL.md" ] || continue; name=$(basename "$s")
  t="$HOME/.claude/skills"
  mkdir -p "$t"; d="$t/$name"
  if [ -L "$d" ] && [ "$(readlink -f "$d")" = "$(readlink -f "$s")" ]; then continue; fi
  if [ -e "$d" ] || [ -L "$d" ]; then b="$HOME/.skills-backup/$stamp/$(basename "$(dirname "$t")")"; mkdir -p "$b"; mv "$d" "$b/"; echo "skill backed up: $b/$name"; fi
  ln -s "$s" "$d"; echo "skill linked: $d -> $s"
done
t="$HOME/.claude/skills"
for d in "$t"/*; do
  [ -L "$d" ] || continue; l=$(readlink "$d")
  case "$l" in "$ROOT"/skills/*) [ -f "$l/SKILL.md" ] || { rm "$d"; echo "skill link pruned: $d"; } ;;
    # stale link from an old handbuilt-cad clone (e.g. the retired ~/handbuilt-cad WSL clone): broken links only
    */handbuilt-cad/skills/*|*/handbuilt-cad-*/skills/*) [ -e "$d" ] || { rm "$d"; echo "stale skill link pruned: $d -> $l"; } ;;
  esac
done
# Unlink our old duplicates from ~/.cursor/skills (the link only, never the target).
t="$HOME/.cursor/skills"
for d in "$t"/*; do
  [ -L "$d" ] || continue; l=$(readlink "$d")
  case "$l" in "$ROOT"/skills/*) rm "$d"; echo "skill link unlinked: $d" ;;
  esac
done
# end 6

# 7. env file for every shell, including agents' non-interactive 'wsl bash -lc'. Setup rewrites
#    ~/.config/handbuilt-cad/env.sh each run and adds one marked line to the login file bash reads
#    (~/.bash_profile, else ~/.bash_login, else ~/.profile), backing that file up first. --no-profile skips the line.
ENVF="$HOME/.config/handbuilt-cad/env.sh"; mkdir -p "$(dirname "$ENVF")"
cat > "$ENVF" <<ENV
# Written by handbuilt-cad setup.sh (re-run it to update). Existing values win.
export CAD_HOME="\${CAD_HOME:-$ROOT}"
export CAD_PY="\${CAD_PY:-$VENV/bin/python}"
export UV_PROJECT_ENVIRONMENT="\${UV_PROJECT_ENVIRONMENT:-$VENV}"
export MODELS_DIR="\${MODELS_DIR:-$MODELS}"
export HBCAD_PARTS_HOME="\${HBCAD_PARTS_HOME:-$PARTS}"
export SIM_VENV="\${SIM_VENV:-$SIM_VENV}"
export FAIRSOLID_HOME="\${FAIRSOLID_HOME:-$ROOT/pipelines/fairsolid}"
case ":\$PATH:" in *":\$HOME/.local/bin:"*) ;; *) export PATH="\$HOME/.local/bin:\$PATH";; esac
ENV
echo "env file: $ENVF"
MARK='[ -f "$HOME/.config/handbuilt-cad/env.sh" ] && . "$HOME/.config/handbuilt-cad/env.sh"  # handbuilt-cad setup'
if [ "$PROFILE" = 1 ]; then
  for LF in "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile"; do [ -f "$LF" ] && break; done
  if grep -qF "$MARK" "$LF" 2>/dev/null; then echo "login file: $LF (already loads it)"
  else [ -f "$LF" ] && cp -p "$LF" "$LF.hbcad-bak-$(date +%Y%m%d-%H%M%S)"; printf '\n%s\n' "$MARK" >> "$LF"; echo "login file: added the env line to $LF"; fi
  # SIM_VENV in the login file too, unless some export SIM_VENV= line is already there (no duplicates).
  if [ "$SIM_VENV" = "$HOME/simvenv" ] && ! grep -qE '^[[:space:]]*export[[:space:]]+SIM_VENV=' "$LF" 2>/dev/null; then
    printf '%s\n' 'export SIM_VENV="$HOME/simvenv"' >> "$LF"; echo "login file: added SIM_VENV to $LF"; fi
else echo "login file: not changed (--no-profile). Add this line yourself: $MARK"; fi
# end 7

# 8. verify: fails (exit 1) with a list of anything missing.
v_args=(); [ "$SIM" = 1 ] || v_args+=(--no-sim)
if ! bash scripts/verify-install.sh "${v_args[@]}"; then
  [ -n "$APT_CMD" ] && echo "Missing sim tools: re-run setup.ps1 from Windows (no password), or paste:  $APT_CMD" >&2
  exit 1
fi
echo "Done."
