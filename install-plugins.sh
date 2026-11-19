#!/usr/bin/env bash
# Open the claude.ai Plugins page and print the clicks. Run this yourself.
# It cannot add the plugin. It does not copy skills, and it does not schedule anything.
set -euo pipefail
if [ "$#" -ne 0 ]; then echo "install-plugins.sh takes no arguments."; exit 2; fi
URL="https://claude.ai/customize/plugins"
CATALOG="living-relation/handbuilt-cad"

plugin_on_claude_ai() {
  if ! python3 - "$HOME" <<'PY'
import json, os, sys
home = sys.argv[1]
plugin_id = "handbuilt-cad@handbuilt-cad-plugins"
ok = "The handbuilt-cad plugin is present on claude.ai."
missing = "WARN: The handbuilt-cad plugin is not added on claude.ai yet. Add catalog living-relation/handbuilt-cad and turn on handbuilt-cad."
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
    echo "WARN: The handbuilt-cad plugin is not added on claude.ai yet. Add catalog living-relation/handbuilt-cad and turn on handbuilt-cad."
  fi
}
plugin_on_claude_ai

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
Individual account: copy the plugin to ~/.cursor/plugins/local/handbuilt-cad (a real copy, not a shortcut to the clone). Include .cursor-plugin/plugin.json and skills/. Restart Cursor or run Developer: Reload Window. Open Customize and confirm the skills.
Update that copy: the Cursor local copy still updates by re-running this script (replace the copy, then reload).
Remove that copy: delete ~/.cursor/plugins/local/handbuilt-cad and reload.
Team or Enterprise account: Dashboard, Plugins & MCPs, Add Marketplace, Import from Repo. Paste https://github.com/living-relation/handbuilt-cad. Under Marketplace Settings, leave Enable Auto Refresh off. Then in Customize, install handbuilt-cad. Update: open the marketplace and choose Refresh.

Opening ${URL}
EOF

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" || echo "Could not open a browser. Open this page yourself: $URL"
elif command -v open >/dev/null 2>&1; then
  open "$URL" || echo "Could not open a browser. Open this page yourself: $URL"
else
  echo "Could not open a browser. Open this page yourself: $URL"
fi
