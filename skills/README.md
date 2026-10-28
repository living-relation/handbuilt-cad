# skills/

Agent skills for CAD work. Claude, Cursor and bots install them from here
(opt-in: `setup.ps1 -LinkSkills` or `bash setup.sh --link-skills`, see below).

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

Every CAD skill follows the repo rules on capped sections (AGENTS.md "Capped sections only") and lettered revs ("Rev folders are lettered").

**Single home.** This folder is the only place CAD skills are edited. Agents (Claude, Cursor, Grok Bot and any other) load them from here or link to them (see Installing); they never edit a copy kept anywhere else. A change to a CAD skill is a PR to this folder.

Changes go through a PR reviewed by the maintainer.

## Claude import zips

Each skill folder has a sibling zip `skills/<skill-name>.zip` for import into Claude. The zip is one top folder named after the skill, with `SKILL.md` directly inside. Only directories that contain `SKILL.md` are packed; the zips themselves, `README.md`, and folders without `SKILL.md` are ignored.

CI rebuilds them on a same-repo pull request whose head is not `main` and commits any changed zips back onto that PR branch (never onto `main`). Actor guard + `[skip ci]` + zip path filter prevent a loop. If `main` is stale, CI resets `chore/skill-zips` to `origin/main` and opens or updates a zip-only PR. That needs **Allow GitHub Actions to create and approve pull requests**. GITHUB_TOKEN commits do not start checks; the workflow re-dispatches a verify run on the new commit. The local pack script is optional:

```powershell
powershell -NoProfile -File scripts\pack-skill-zips.ps1
```

```bash
bash scripts/pack-skill-zips.sh
```

Do not edit the zip bytes. The packer reports Claude name/description limit violations and does not rewrite `SKILL.md`. A description over 200 characters warns only and does not fail.

## Installing

handbuilt-cad's setup owns the skill links, and linking is off by default. Opt in with `setup.ps1 -LinkSkills`, which junctions each `skills\<name>` into `~\.claude\skills` and `~\.cursor\skills` (`scripts\link-skills.ps1`), or `bash setup.sh --link-skills` (or `LINK_SKILLS=1`), which symlinks them into the WSL `~/.claude/skills` and `~/.cursor/skills`. A same-name folder is backed up to `~/.skills-backup` first. Re-running it also removes links it made whose skill was renamed or removed (the link only); nothing else is deleted. No other repo installs these skills.
