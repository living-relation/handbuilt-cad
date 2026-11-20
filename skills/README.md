# skills/

Agent skills for CAD work. Claude Chat, Cowork, and Claude Code get them when handbuilt-cad is turned on for the claude.ai account. Cursor gets its own copy of the plugin. See [INSTALL.md](../INSTALL.md). There is no zip upload.

- cnc-part-check
- publish-to-models
- scan-to-parametric
- toolkit-patch-handoff
- cad-drawing
- blend-fillet
- sim-stack
- primary-source-spec-check

The first four are the generic versions (paths come from `local.toml`, no project examples), taken from stevecad-tools `7688e33`.

sim-stack covers both the quick single-load-case check (`tools/quick_fea.py`, formerly the quick-fea skill) and full studies.

Every CAD skill follows the repo rules on capped sections (AGENTS.md "Capped sections only") and lettered revs ("Version folders"). Electrical and plan rules are in AGENTS.md "Electrical and design plans". Questions to the maintainer are multiple choice (a1, a2).

**Single home.** This folder is the only place CAD skills are edited. Agents load the installed plugin, not a second copy. They never edit a copy kept anywhere else. A change to a CAD skill is a PR to this folder.

Changes go through a PR reviewed by the maintainer.

## Claude import zips

CI still builds a sibling zip `skills/<skill-name>.zip` for each skill. The zip is one top folder named after the skill, with `SKILL.md` directly inside. Only directories that contain `SKILL.md` are packed; the zips themselves, `README.md`, and folders without `SKILL.md` are ignored. Do not upload these zips. Install the plugin instead ([INSTALL.md](../INSTALL.md)).

CI rebuilds them on a same-repo pull request whose head is not `main` and commits any changed zips back onto that PR branch (never onto `main`). Actor guard + `[skip ci]` + zip path filter prevent a loop. If `main` is stale, CI resets `chore/skill-zips` to `origin/main` and opens or updates a zip-only PR. That needs **Allow GitHub Actions to create and approve pull requests**. GITHUB_TOKEN commits do not start checks; the workflow re-dispatches a verify run on the new commit. The local pack script is optional:

```powershell
powershell -NoProfile -File scripts\pack-skill-zips.ps1
```

```bash
bash scripts/pack-skill-zips.sh
```

Do not edit the zip bytes. The packer reports Claude name/description limit violations and does not rewrite `SKILL.md`. A description over 200 characters warns only and does not fail.

## Installing

Turn on the handbuilt-cad plugin on claude.ai. Turn Sync automatically on. Updates arrive automatically after merges to main. Check for updates in the catalog forces it sooner. The install-plugins script copies `.cursor-plugin` and `skills` to `~/.cursor/plugins/local/handbuilt-cad` and replaces the old copy. The Cursor local copy still updates by re-running the install-plugins script. The four ways are in [INSTALL.md](../INSTALL.md). Setup does not copy these skills into `~/.claude/skills` or `~/.cursor/skills`. Skills listed in `EXCLUDE.txt` stay untouched. Do not upload the zips. Where the Sync automatically switch sits on the page is unverified until someone clicks through Customize.

