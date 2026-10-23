# Source this (". scripts/hbcad-env.sh") from ~/.profile or a script to get the handbuilt-cad env in
# non-interactive shells too. Keeps existing values. On a Windows drive (/mnt/<x>/) the Linux venv is
# ~/.venvs/handbuilt-cad so WSL uv never touches the Windows .venv.
_hb_root=$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd -P)
case "$_hb_root" in /mnt/[a-z]/*) _hb_venv="$HOME/.venvs/handbuilt-cad";; *) _hb_venv="$_hb_root/.venv";; esac
export CAD_HOME="${CAD_HOME:-$_hb_root}"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$_hb_venv}"
export CAD_PY="${CAD_PY:-$UV_PROJECT_ENVIRONMENT/bin/python}"
unset _hb_root _hb_venv
