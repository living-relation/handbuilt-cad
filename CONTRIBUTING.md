# Contributing

- **PRs only.** Branch -> PR -> review -> merge. No commits on `main`, no force-push (the skill-zips bot may `--force-with-lease` only `chore/skill-zips`, which it resets to `origin/main`).
- **Follow this repo's own rules.** Read `AGENTS.md`, this file, the hooks (`.githooks/`, `.pre-commit-config.yaml`) and any CI before changing anything. Never bypass a hook or gate (`--no-verify`, skipping CI, pushing generated or bot-owned files by hand) without the maintainer's explicit yes.
- **No part files.** Build scripts, specs, small JSON/CSV summaries and review PNGs are fine; models go to `$MODELS_DIR`. The guard blocks model formats, archives, `.env` files and anything over 1 MB. A single allow-listed exception goes in `.guard-allow`, by exact path, in its own reviewed PR. Claude skill zips at `skills/<name>.zip` are allowed when `skills/<name>/SKILL.md` exists. CI rebuilds them on the PR branch (and opens a zip PR if main is stale); do not edit the zip bytes by hand. The local pack script is optional.
- **Skill-zip CI settings.** GITHUB_TOKEN commits and PRs do not start new workflow runs; `.github/workflows/skill-zips.yml` re-dispatches itself with `verify_only` on the new commit. The stale-main zip PR also needs the repo setting **Allow GitHub Actions to create and approve pull requests** (Settings → Actions → Workflow permissions).
- **No forks, patches only.** Upstream tools are pinned (see `docs/TOOLS.md`); a small upstream fix is a patch file, never a fork or vendored copy.
- **No batch shortcuts.** No scripts that pull, push, merge or commit across many repos at once.
- **No secrets, no personal data.** No tokens, credentials, personal paths, emails or names in code, docs or commit metadata. Commits use a GitHub noreply address.
- **Line endings:** `.gitattributes` keeps LF in the repo (CRLF for .bat/.ps1). Don't override it per clone.
- **Tests:** `$CAD_PY -m pytest -q` (`.venv/bin/python`, or `~/.venvs/handbuilt-cad/bin/python` in WSL with the one-clone layout) plus the checks for what you touched.
