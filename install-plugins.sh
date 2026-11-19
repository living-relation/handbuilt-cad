#!/usr/bin/env bash
# Open the claude.ai Plugins page, print the clicks, and copy the Cursor plugin.
# It cannot add the plugin on claude.ai. It copies .cursor-plugin and skills to
# ~/.cursor/plugins/local/handbuilt-cad and replaces the old copy.
# It does not copy skills into ~/.claude/skills or ~/.cursor/skills.
# It does not schedule anything.
# --what-if prints the clicks and changes nothing.
# --user-home DIR is for tests: the Cursor copy goes under that folder, and the
# browser is not opened.
set -euo pipefail

USER_HOME=""
WHAT_IF=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --user-home)
      if [ "$#" -lt 2 ] || [ -z "${2:-}" ]; then
        echo "install-plugins.sh needs a folder after --user-home."
        exit 2
      fi
      USER_HOME=$2
      shift 2
      ;;
    --what-if)
      WHAT_IF=1
      shift
      ;;
    *)
      echo "install-plugins.sh takes no arguments."
      exit 2
      ;;
  esac
done

URL="https://claude.ai/customize/plugins"
CATALOG="living-relation/handbuilt-cad"
if [ -n "$USER_HOME" ]; then
  HOME_ROOT=$USER_HOME
else
  HOME_ROOT=${HOME:-}
fi
if [ -z "$HOME_ROOT" ]; then
  echo "No home folder found."
  exit 1
fi

plugin_on_claude_ai() {
  if ! python3 - "$1" <<'PY'
import json, os, sys
home = sys.argv[1]
plugin_id = "handbuilt-cad@handbuilt-cad-plugins"
ok = "The handbuilt-cad plugin is present on claude.ai."
missing = "WARN: handbuilt-cad plugin not added on claude.ai yet: add catalog living-relation/handbuilt-cad and turn on handbuilt-cad."
path = os.path.join(home, ".claude", "settings.json")
try:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    enabled = data.get("enabledPlugins")
    if isinstance(enabled, dict) and enabled.get(plugin_id) is True:
        print(ok)
        raise SystemExit(0)
except (OSError, json.JSONDecodeError, AttributeError, TypeError):
    pass
print(missing)
PY
  then
    echo "WARN: handbuilt-cad plugin not added on claude.ai yet: add catalog living-relation/handbuilt-cad and turn on handbuilt-cad."
  fi
}
plugin_on_claude_ai "$HOME_ROOT"

cat <<EOF

handbuilt-cad on claude.ai
This script cannot add the plugin. Do these clicks yourself.

Catalog to paste: ${CATALOG}
Catalog name: handbuilt-cad-plugins

1. Sign in to the claude.ai account you use.
2. Open Customize.
3. Open Plugins.
4. Choose Add.
5. Choose Add marketplace.
6. Paste ${CATALOG}.
7. Turn Sync automatically on. Where that switch sits on the page is unverified until someone clicks through Customize.
8. Open handbuilt-cad and turn it on (Add).
9. Chat, Cowork, and Claude Code signed in to this account all use that plugin.

Update: Turn Sync automatically on. Updates arrive automatically after merges to main. Check for updates in the catalog forces it sooner.
Remove: open handbuilt-cad, open its menu, choose Remove.

Cursor is separate. Leave Auto Refresh off.
This script copies .cursor-plugin and skills to ~/.cursor/plugins/local/handbuilt-cad and replaces the old copy. Fully quit and reopen Cursor. Open Customize and confirm the skills.
Update that copy: the Cursor local copy still updates by re-running this script (replace the copy, then reload).
Remove that copy: delete ~/.cursor/plugins/local/handbuilt-cad and reload.
It does not copy skills into ~/.claude/skills or ~/.cursor/skills.
Team or Enterprise account: Dashboard, Plugins & MCPs, Add Marketplace, Import from Repo. Paste https://github.com/living-relation/handbuilt-cad. Under Marketplace Settings, leave Enable Auto Refresh off. Then in Customize, install handbuilt-cad. Update: open the marketplace and choose Refresh.

EOF

src=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
case "$HOME_ROOT" in
  /*) ;;
  *) echo "Home must be an absolute path."; exit 1 ;;
esac
dest="$HOME_ROOT/.cursor/plugins/local/handbuilt-cad"
case "$dest" in
  */.cursor/plugins/local/handbuilt-cad) ;;
  *) echo "Refusing to remove an unexpected folder."; exit 1 ;;
esac
case "$dest/" in
  "$src/"*) echo "Refusing to copy the plugin into its own folder."; exit 1 ;;
esac
echo "Cursor copy: $dest"
if [ "$WHAT_IF" -eq 1 ]; then
  echo "WhatIf: browser was not opened. Nothing was copied. Nothing was scheduled."
  exit 0
fi
if [ ! -d "$src/.cursor-plugin" ] || [ ! -d "$src/skills" ]; then
  echo "Missing .cursor-plugin or skills in $src"
  exit 1
fi
rm -rf "$dest"
mkdir -p "$dest"
cp -a -- "$src/.cursor-plugin" "$src/skills" "$dest/"
echo "Copied handbuilt-cad to $dest. Fully quit and reopen Cursor."

if [ -n "$USER_HOME" ]; then
  echo "browser was not opened (test home). Nothing was scheduled."
  exit 0
fi

echo "Opening ${URL}"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" || echo "Could not open a browser. Open this page yourself: $URL"
elif command -v open >/dev/null 2>&1; then
  open "$URL" || echo "Could not open a browser. Open this page yourself: $URL"
else
  echo "Could not open a browser. Open this page yourself: $URL"
fi
echo "Nothing was scheduled."
