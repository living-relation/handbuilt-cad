# Install handbuilt-cad

Claude Chat, Cowork, and Claude Code get the skills when you add this repo's catalog on claude.ai and turn on **handbuilt-cad**. That is the only Claude route. Cursor is separate. Setup does not copy skills onto this machine. There is no zip upload. Nothing here adds or updates the plugin in the background, and nothing is scheduled.

The Claude catalog is in this repo: `.claude-plugin/marketplace.json`, named `handbuilt-cad-plugins`. It lists only handbuilt-cad, with source `./` (this repo). On claude.ai you paste `living-relation/handbuilt-cad`. Do not add another plugin to that file. The Cursor marketplace at `.cursor-plugin/marketplace.json` also lists only this plugin (`"source": "."`). Do not add a marketplace here that lists other repos.

`<projects>` means your Projects folder.

## 1. Installer or shortcut

Windows only. Two shortcuts. Neither one adds the plugin by itself.

**Toolkit.** In File Explorer, double-click `install.cmd` in the clone. That opens a normal window (not Administrator), runs `setup.ps1` with no extra flags, and waits. It does not open a browser and it does not copy skills onto this machine.

**Plugin page.** Double-click `install-plugins.cmd` when you want the claude.ai steps. That runs only because you started it. It opens the Plugins page and prints the clicks, including Turn Sync automatically on. It cannot turn the plugin on. You still click. It does not schedule anything.

**Update the toolkit.** Double-click `install.cmd` again. That is a full re-run of setup. It still does not add or update the plugin.

**Update or remove the plugin.** On claude.ai, Turn Sync automatically on. Updates arrive automatically after merges to main. Check for updates in the catalog forces it sooner. To remove it, open handbuilt-cad, open its menu, choose Remove.

There is no uninstall shortcut for the toolkit. Removing the toolkit is at the bottom of this page.

## 2. README commands

Each block is one command. The clone, toolkit, and plugin-page commands are also in [README.md](README.md). Update and uninstall notes for the toolkit are on this page.

### Toolkit

**Windows PowerShell, normal window (not Administrator).**

```powershell
git clone https://github.com/living-relation/handbuilt-cad.git <projects>\active\handbuilt-cad
```

```powershell
cd <projects>\active\handbuilt-cad
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
```

**Plain Linux, normal terminal (not root).**

```bash
git clone https://github.com/living-relation/handbuilt-cad.git ~/projects/handbuilt-cad
```

```bash
cd ~/projects/handbuilt-cad
```

```bash
bash setup.sh
```

On Windows, do not also clone inside WSL. `setup.ps1` points WSL at the Windows clone through `~/projects/handbuilt-cad` and runs `setup.sh` there. Setup does not copy skills onto this machine.

**Update the toolkit.** Run the same `setup.ps1` or `bash setup.sh` command again. That refreshes the toolkit. It does not update the plugin.

### Plugin (claude.ai)

The script opens https://claude.ai/customize/plugins and prints the clicks. It cannot add the plugin. Paste `living-relation/handbuilt-cad`. Turn Sync automatically on. Then turn on handbuilt-cad. One account covers chat, Cowork, and Claude Code. Updates arrive automatically after merges to main. Check for updates in the catalog forces it sooner.

**Windows PowerShell, normal window (not Administrator).**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-plugins.ps1
```

**Plain Linux, normal terminal (not root).**

```bash
bash install-plugins.sh
```

**Update the plugin.** On claude.ai, Turn Sync automatically on. Updates arrive automatically after merges to main. Check for updates in the catalog forces it sooner.

**Remove the plugin.** Open handbuilt-cad, open its menu, choose Remove. That does not delete the clone.

## 3. Agent prompt

Copy all of [SETUP-PROMPT.txt](SETUP-PROMPT.txt) into a new agent chat. The agent may run the toolkit setup. It must wait for your yes before it opens the plugin page. It must not copy skills onto this machine or upload zips.

```prompt
Set up handbuilt-cad on this PC, then stop for the plugin steps. Skills come only from the handbuilt-cad plugin on claude.ai. Do not copy skills into ~/.claude/skills or ~/.cursor/skills. Do not upload skill zips. Turn Sync automatically on. Leave Cursor Auto Refresh off. Do not create a CLAUDE.md. Do not edit Claude memory files. Do not touch st185-link-ecu-config. Do not add a scheduled task or a startup task. The catalog is already in this repo. Do not add a second catalog file, and do not add another plugin to it. Do not use the Claude Code command line to add or install a plugin. claude.ai is the only Claude route. Cursor is separate.

1. Find the clone. On Windows it is <projects>\active\handbuilt-cad (one clone, in Windows). On plain Linux it is ~/projects/handbuilt-cad. If it is missing, clone it in a normal terminal (not Administrator, not root). On Windows the last argument is <projects>\active\handbuilt-cad. On plain Linux the last argument is ~/projects/handbuilt-cad. The URL is https://github.com/living-relation/handbuilt-cad.git. Do not make a second WSL clone. WSL uses the Windows clone through ~/projects/handbuilt-cad.

2. Read README.md and INSTALL.md in that folder before you change anything.

3. Install the toolkit. From the clone: on Windows, a normal PowerShell window (not Administrator), run powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1. On plain Linux, a normal terminal (not root), run bash setup.sh. Double-click install.cmd is the same Windows setup and adds no flags. Show the exit code. If it fails, stop. This step does not add the plugin and does not open a browser.

4. Do not open the plugin page until I say yes. When I say yes, claude.ai is the only Claude route. It covers chat, Cowork, and Claude Code signed in to that account. On Windows, a normal PowerShell window (not Administrator), run powershell -NoProfile -ExecutionPolicy Bypass -File .\install-plugins.ps1. On plain Linux, a normal terminal (not root), run bash install-plugins.sh. That opens https://claude.ai/customize/plugins and prints the clicks. It cannot add the plugin. I still do the clicks: Customize, Plugins, Add, Add marketplace, paste living-relation/handbuilt-cad, Turn Sync automatically on, then turn on handbuilt-cad. The catalog name is handbuilt-cad-plugins. It is .claude-plugin/marketplace.json in this repo. It lists only handbuilt-cad, source ./. Do not add a second catalog file and do not add another plugin to it.

5. Cursor is separate. Give me the click steps in INSTALL.md and wait. For an individual account, copy the plugin to ~/.cursor/plugins/local/handbuilt-cad. The Cursor local copy still updates by re-running the install-plugins script. Leave Auto Refresh off. Do not copy skills into ~/.cursor/skills or ~/.claude/skills.

6. Updates: re-run the same setup command for the toolkit. That is a full reinstall of the toolkit pieces setup manages, and it still must not copy skills onto this machine. On claude.ai, Turn Sync automatically on. Updates arrive automatically after merges to main. Check for updates in the catalog forces it sooner. The Cursor local copy still updates by re-running the install-plugins script. Leave Cursor Auto Refresh off.

7. Finish with a short report: what you ran, the exit code, which plugin clicks are still mine, and anything you could not run.
```

## 4. Manual steps

Do these clicks yourself. A script cannot do them.

### claude.ai (chat, Cowork, and Claude Code on that account)

1. Sign in to the claude.ai account you use.
2. Open **Customize**, then **Plugins**. The page is https://claude.ai/customize/plugins.
3. Choose **Add**, then **Add marketplace**.
4. Paste `living-relation/handbuilt-cad`. The catalog name is `handbuilt-cad-plugins`.
5. Turn Sync automatically on. Where that switch sits on the page is unverified until someone clicks through Customize.
6. Open **handbuilt-cad** and turn it on (**Add**).
7. **Update:** updates arrive automatically after merges to main. Check for updates in the catalog forces it sooner.
8. **Remove:** open handbuilt-cad, open its menu, choose **Remove**.

### Cursor

Cursor does not use the Claude catalog. Leave **Auto Refresh** off. Updates are the **Refresh** button, not a background sync.

**If handbuilt-cad is already listed** under Customize, choose **Install**. To remove it, open it in Customize and disable or uninstall it there.

**Team or Enterprise account.** Dashboard, **Plugins & MCPs**, **Add Marketplace**, **Import from Repo**. Paste `https://github.com/living-relation/handbuilt-cad`. That repo's marketplace lists only this plugin. Do not import a marketplace that lists other repos from this repo. Under Marketplace Settings, leave **Enable Auto Refresh** off. Then in Customize, install **handbuilt-cad**. **Update:** open the marketplace and choose **Refresh**.

**Individual account.** Team import is not available. Copy the plugin into `~/.cursor/plugins/local/handbuilt-cad` (a real copy, not a shortcut to the clone). Include `.cursor-plugin/plugin.json` and `skills/`. Restart Cursor or run **Developer: Reload Window**. Open Customize and confirm the skills. **Update:** the Cursor local copy still updates by re-running `install-plugins.ps1` or `bash install-plugins.sh` (replace that copy, then reload). **Remove:** delete `~/.cursor/plugins/local/handbuilt-cad` and reload.

Do not copy `skills/` into `~/.claude/skills` or `~/.cursor/skills`.

## Remove the toolkit

There is no toolkit uninstall shortcut. Removing the plugin does not delete the clone, the Python env, or your models.

- **Sim tools only.** See [sim/SIM_TOOLS.md](sim/SIM_TOOLS.md). The rollback scripts are `sim/rollback/uninstall_wsl_sim_tools.sh` and `sim/rollback/uninstall_windows_sim_tools.ps1`.
- **Python env.** On Windows the env is `<repo>\.venv`. On WSL and Linux it is `~/.venvs/handbuilt-cad`. Deleting that folder removes the env. Your models folder and `~/cad-parts` stay.
- **This guide does not delete** `~/.claude/skills`. Setup does not copy skills there.
