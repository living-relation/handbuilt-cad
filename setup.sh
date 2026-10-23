#!/usr/bin/env bash
# handbuilt-cad setup for WSL/Linux. Safe to re-run. Touches only this repo, ~/.cache/uv,
# uv's Python store, and (unless --no-models) creates <Desktop>/models if it is missing.
#   bash setup.sh [--no-models] [--with-fairsolid] [--sim] [--link-skills]
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
NO_MODELS=0; WITH_FS=0; SIM=0; LINK_SKILLS=${LINK_SKILLS:-0}
for a in "$@"; do case $a in --no-models) NO_MODELS=1;; --with-fairsolid) WITH_FS=1;; --sim) SIM=1;; --link-skills) LINK_SKILLS=1;; *) echo "unknown option $a"; exit 2;; esac; done

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
if [ "$SIM" = 1 ]; then
  echo "Sim venv: $UV venv .venv-sim --python 3.14 && $UV pip install --python .venv-sim -r requirements-sim.txt"
  echo "Apt packages (needs sudo, run by hand): sudo apt install \$(grep -v '^#' apt-sim.txt)"
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

# 6. skills: off by default. Only with --link-skills (or LINK_SKILLS=1): symlink skills/<name> into ~/.claude/skills
#    and ~/.cursor/skills (a same-name entry is moved to ~/.skills-backup/<stamp>/ first). The only delete: a symlink
#    into this clone's skills/ whose skill is gone is removed (the link only). On Windows, setup.ps1 -LinkSkills does
#    the same with junctions.
if [ "$LINK_SKILLS" != 1 ]; then
  echo "skills: not linked (opt in with --link-skills)"
else
  stamp=$(date +%Y%m%d-%H%M%S)
  for s in "$ROOT"/skills/*/; do
    s=${s%/}; [ -f "$s/SKILL.md" ] || continue; name=$(basename "$s")
    for t in "$HOME/.claude/skills" "$HOME/.cursor/skills"; do
      mkdir -p "$t"; d="$t/$name"
      if [ -L "$d" ] && [ "$(readlink -f "$d")" = "$(readlink -f "$s")" ]; then continue; fi
      if [ -e "$d" ] || [ -L "$d" ]; then b="$HOME/.skills-backup/$stamp/$(basename "$(dirname "$t")")"; mkdir -p "$b"; mv "$d" "$b/"; echo "skill backed up: $b/$name"; fi
      ln -s "$s" "$d"; echo "skill linked: $d -> $s"
    done
  done
  for t in "$HOME/.claude/skills" "$HOME/.cursor/skills"; do
    for d in "$t"/*; do
      [ -L "$d" ] || continue; l=$(readlink "$d")
      case "$l" in "$ROOT"/skills/*) [ -f "$l/SKILL.md" ] || { rm "$d"; echo "skill link pruned: $d"; } ;;
        # stale link from an old handbuilt-cad clone (e.g. the retired ~/handbuilt-cad WSL clone): broken links only
        */handbuilt-cad/skills/*|*/handbuilt-cad-*/skills/*) [ -e "$d" ] || { rm "$d"; echo "stale skill link pruned: $d -> $l"; } ;;
      esac
    done
  done
fi
# end 6

cat <<MSG

Done. Add these to ~/.profile (read by login shells, including 'wsl -e bash -lc' and setup.ps1), not only
~/.bashrc (interactive shells only), or source scripts/hbcad-env.sh from scripts. Setup does not edit dotfiles:
  export CAD_HOME="$ROOT"
  export CAD_PY="$VENV/bin/python"
  export UV_PROJECT_ENVIRONMENT="$VENV"   # so uv run / uv sync use this venv
  export MODELS_DIR="$MODELS"
  export HBCAD_PARTS_HOME="$PARTS"   # part build scripts and run outputs (tools/paths.py)
  export FAIRSOLID_HOME="$ROOT/pipelines/fairsolid"   # optional: scan_helper falls back to it (docs/FAIRSOLID.md)
MSG
