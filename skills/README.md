# skills/

Agent skills for CAD work. Claude, Cursor and bots install them from here
(`sync-skills.ps1 -From <this repo>\skills -From <workstation repo>\skills`).

| Skill | Owner |
|---|---|
| cnc-part-check | SteveCAD |
| publish-to-models | SteveCAD |
| scan-to-parametric | SteveCAD |
| toolkit-patch-handoff | Grok Bot |
| primary-source-spec-check | SteveCAD |
| cad-drawing | SteveCAD |
| blend-fillet | SteveCAD |
| sim-stack | SteveCAD |

The first four are the generic versions (paths come from `local.toml`, no project examples), taken from stevecad-tools `7688e33`.

cad-drawing, blend-fillet and sim-stack were drafted by Grok Bot and refined by SteveCAD. sim-stack covers both the quick single-load-case check (`tools/quick_fea.py`, formerly the quick-fea skill) and full studies.

Every CAD skill follows the repo rules on capped sections (AGENTS.md "Capped sections only") and lettered revs ("Rev folders are lettered").

Changes go through a PR reviewed by the owner.

## Installing

handbuilt-cad's setup owns the skill links: `setup.ps1` junctions each `skills\<name>` into `~\.claude\skills` and `~\.cursor\skills` (`scripts\link-skills.ps1`; `-NoSkills` skips it), and `setup.sh` symlinks them into the WSL `~/.claude/skills` and `~/.cursor/skills` (`NO_SKILLS=1` skips it). A same-name folder is backed up to `~/.skills-backup` first; nothing is deleted. No other repo installs these skills.
