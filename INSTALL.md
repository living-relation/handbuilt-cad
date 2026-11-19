# Install handbuilt-cad

Skills reach Claude Chat, Cowork, Claude Code, and Cursor only by installing the **handbuilt-cad** plugin. Setup does not link skills. There is no zip upload. Nothing here installs or updates the plugin in the background.

The catalog is not in this repo. Do not add `.claude-plugin/marketplace.json` here, and do not add a Cursor marketplace that lists other repos. The catalog is the marketplace named `living-relation-plugins` in [living-relation/workstation](https://github.com/living-relation/workstation). It lists `workstation-core` at `./` and handbuilt-cad as `{"source":"github","repo":"living-relation/handbuilt-cad"}`. This repo's `.cursor-plugin/marketplace.json` lists only this plugin (`"source": "."`).

Pick **one** Claude route. A plugin turned on for a claude.ai account also shows up in Claude Code signed in to that account. Installing it again on that machine loads the skills twice.

`<projects>` means your Projects folder.

## 1. Installer or shortcut

Windows only. This installs the toolkit (Python, checks, sim tools, git hooks). It does not install the plugin and it does not link skills.

**Install.** In File Explorer, double-click `install.cmd` in the clone. That opens a normal window (not Administrator), runs `setup.ps1` with no extra flags, and waits.

**Update the toolkit.** Double-click `install.cmd` again. That is a full re-run of setup. It still does not install or update the plugin.

**Update or remove the plugin.** The shortcut cannot do that. Use the Plugins menu in section 4.

There is no uninstall shortcut. Removing the toolkit is at the bottom of this page.

## 2. README commands

Each block is one command. The clone, toolkit, and plugin-install commands are also in [README.md](README.md). Update and uninstall commands are on this page.

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

On Windows, do not also clone inside WSL. `setup.ps1` links the Windows clone to `~/projects/handbuilt-cad` and runs `setup.sh` there. Do not pass `-LinkSkills` or `--link-skills`.

**Update the toolkit.** Run the same `setup.ps1` or `bash setup.sh` command again. That refreshes the toolkit. It does not update the plugin.

### Plugin (Claude Code shell)

**Normal terminal (not Administrator, not root).** Run these only if this machine does not already get the plugin from your claude.ai account. User scope is the default.

```bash
claude plugin marketplace add living-relation/workstation
```

```bash
claude plugin install handbuilt-cad@living-relation-plugins
```

**Update the plugin.** Plugins menu, or this command. Do not turn marketplace auto-update on.

```bash
claude plugin update handbuilt-cad@living-relation-plugins
```

**Remove the plugin.** This removes only handbuilt-cad. It does not remove the workstation catalog or workstation-core.

```bash
claude plugin uninstall handbuilt-cad@living-relation-plugins
```

If `marketplace add` fails because `living-relation-plugins` is not in the workstation repo yet, stop. Do not create a catalog in this repo.

## 3. Agent prompt

Copy all of [SETUP-PROMPT.txt](SETUP-PROMPT.txt) into a new agent chat. The agent may run the toolkit setup. It must wait for your yes before any plugin command, and it must not link skills or upload zips.

```prompt
Set up handbuilt-cad on this PC, then stop for the plugin steps. Skills come only from the handbuilt-cad plugin. Do not link skills. Do not upload skill zips. Do not turn on Sync automatically, Claude Code marketplace auto-update, or Cursor Auto Refresh. Do not add a catalog or marketplace file to this repo. Do not create a CLAUDE.md. Do not edit Claude memory files. Do not touch st185-link-ecu-config. Do not add a scheduled task, a startup task, or any background sync.

1. Find the clone. On Windows it is <projects>\active\handbuilt-cad (one clone, in Windows). On plain Linux it is ~/projects/handbuilt-cad. If it is missing, clone it in a normal terminal (not Administrator, not root). On Windows the last argument is <projects>\active\handbuilt-cad. On plain Linux the last argument is ~/projects/handbuilt-cad. The URL is https://github.com/living-relation/handbuilt-cad.git. Do not make a second WSL clone. WSL uses the Windows clone through ~/projects/handbuilt-cad.

2. Read README.md and INSTALL.md in that folder before you change anything.

3. Install the toolkit. Do not pass -LinkSkills or --link-skills. From the clone: on Windows, a normal PowerShell window (not Administrator), run powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1. On plain Linux, a normal terminal (not root), run bash setup.sh. Double-click install.cmd is the same Windows setup and adds no flags. Show the exit code. If it fails, stop. This step does not install the plugin.

4. Do not install the plugin until I say yes. When I say yes, pick ONE Claude route so the skills do not load twice. If the plugin is already on for a claude.ai account, Claude Code signed in to that account already receives it. Do not also install it locally for that account.
   Route A, normal terminal (not Administrator), one command at a time, only after I say yes:
   claude plugin marketplace add living-relation/workstation
   claude plugin install handbuilt-cad@living-relation-plugins
   Then in Claude Code open /plugin, go to Marketplaces, select living-relation-plugins, and confirm auto-update is off.
   Route B, I click it: Customize, Plugins, Add, Add marketplace, living-relation/workstation. Leave Sync automatically off. Add handbuilt-cad. Do not also run the Route A commands for that account.
   The catalog name is living-relation-plugins. It lives in living-relation/workstation, not in this repo. workstation-core is source ./ . handbuilt-cad is {"source":"github","repo":"living-relation/handbuilt-cad"}. If the add fails because that catalog file is not there yet, stop. Do not create a marketplace file in this repo.

5. Cursor is separate. Give me the click steps in INSTALL.md and wait. Leave Auto Refresh off. Do not copy or link skills into ~/.cursor/skills or ~/.claude/skills.

6. Updates: re-run the same setup command for the toolkit. That is a full reinstall of the toolkit pieces setup manages, and it still must not link skills. Update the plugin only from the Plugins menu (Claude Code: Update now. claude.ai: Check for updates. Cursor: Refresh). Never turn a sync or auto-update on.

7. Finish with a short report: what you ran, the exit code, which plugin clicks are still mine, and anything you could not run.
```

## 4. Manual steps

### Claude Code session

**Normal terminal (not Administrator).** Start `claude` in the clone.

1. Add the catalog. In the session, run the next line, then confirm the add.

```text
/plugin marketplace add living-relation/workstation
```

2. Open the plugin. This does not install by itself. It opens the plugin so you can choose a scope.

```text
/plugin install handbuilt-cad@living-relation-plugins
```

3. Choose **Install for you** (user scope). Do not choose the project scope. That would commit an enable line into this repo.
4. Open `/plugin`, Marketplaces, `living-relation-plugins`. Confirm auto-update is **off**.
5. **Update:** Installed tab, open handbuilt-cad, choose **Update now**.
6. **Remove:** Installed tab, open handbuilt-cad, choose **Uninstall**.

### claude.ai and the Claude desktop app

1. Open **Customize**, then **Plugins**.
2. Choose **Add**, then **Add marketplace**.
3. Enter `living-relation/workstation`.
4. Leave **Sync automatically** off.
5. Open **handbuilt-cad** and choose **Add**.
6. **Update:** on Plugins, choose **Check for updates**. Leave Sync automatically off.
7. **Remove:** open handbuilt-cad, open its menu, choose **Remove**.

### Cursor

Cursor does not use the Claude catalog. Leave **Auto Refresh** off. Updates are the **Refresh** button, not a background sync.

**If handbuilt-cad is already listed** under Customize, choose **Install**. To remove it, open it in Customize and disable or uninstall it there.

**Team or Enterprise account.** Dashboard, **Plugins & MCPs**, **Add Marketplace**, **Import from Repo**. Paste `https://github.com/living-relation/handbuilt-cad`. That repo's marketplace lists only this plugin. Do not import a marketplace that lists other repos from this repo. Under Marketplace Settings, leave **Enable Auto Refresh** off. Then in Customize, install **handbuilt-cad**. **Update:** open the marketplace and choose **Refresh**.

**Individual account.** Team import is not available. Copy the plugin into `~/.cursor/plugins/local/handbuilt-cad` (a real copy, not a shortcut to the clone). Include `.cursor-plugin/plugin.json` and `skills/`. Restart Cursor or run **Developer: Reload Window**. Open Customize and confirm the skills. **Update:** replace that copy, then reload. **Remove:** delete `~/.cursor/plugins/local/handbuilt-cad` and reload.

Do not link `skills/` into `~/.claude/skills` or `~/.cursor/skills`.

## Remove the toolkit

There is no toolkit uninstall shortcut. Removing the plugin does not delete the clone, the Python env, or your models.

- **Sim tools only.** See [sim/SIM_TOOLS.md](sim/SIM_TOOLS.md). The rollback scripts are `sim/rollback/uninstall_wsl_sim_tools.sh` and `sim/rollback/uninstall_windows_sim_tools.ps1`.
- **Python env.** On Windows the env is `<repo>\.venv`. On WSL and Linux it is `~/.venvs/handbuilt-cad`. Deleting that folder removes the env. Your models folder and `~/cad-parts` stay.
- **This guide does not delete** `~/.claude/skills`. Setup does not put skills there unless someone passed `-LinkSkills` or `--link-skills`.
