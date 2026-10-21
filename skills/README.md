# skills/

Agent skills for CAD work. Claude, Cursor and bots install them from here
(`sync-skills.ps1 -From <this repo>\skills -From <workstation repo>\skills`).

| Skill | Owner |
|---|---|
| cnc-part-check | SteveCAD |
| publish-to-models | SteveCAD |
| scan-to-parametric | SteveCAD |
| toolkit-patch-handoff | Grok Bot |
| cad-drawing | SteveCAD (draft) |
| blend-fillet | SteveCAD (draft) |
| quick-fea | SteveCAD (draft) |
| sim-stack | SteveCAD (draft) |

The first four are the generic versions (paths come from `local.toml`, no project examples), taken from stevecad-tools `7688e33`.

The four marked (draft) were drafted by Grok Bot from the repo code and docs; SteveCAD owns them and will refine them.

Every CAD skill follows the repo rules on capped sections (AGENTS.md rule 15) and lettered revs (rule 16).

Changes go through a PR reviewed by the owner.

## Installing

handbuilt-cad's setup owns the skill links: `setup.ps1` junctions each `skills\<name>` into `~\.claude\skills` and `~\.cursor\skills` (`scripts\link-skills.ps1`; `-NoSkills` skips it), and `setup.sh` symlinks them into the WSL `~/.claude/skills` and `~/.cursor/skills` (`NO_SKILLS=1` skips it). A same-name folder is backed up to `~/.skills-backup` first; nothing is deleted. No other repo installs these skills.
