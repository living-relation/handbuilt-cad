"""Build the self-contained Fairsolid handoff zip for Grok Bot.

  python pipelines/fairsolid/scripts/make_handoff.py --job <job> --rules-repo <project checkout> [--rules-file PATH]
         [--date 2026-10-15] [--runs DIR] [--root <handbuilt-cad>/pipelines/fairsolid]
         [--out DIR] [--copy-to DIR]

Ported on 2026-10-17 from the old fairsolid checkout (handoff/tool/, outside git) into handbuilt-cad.

Run it with any Python 3.9+ (standard library only). It collects:
  * the docs and tools in scripts/handoff_templates/ (HANDOFF, RULES, TASK-TEMPLATE, tools/, env/)
  * the Fairsolid source (git-tracked src, tests/*.py, recipes, plan doc, pyproject, README, AGENTS)
  * the newest revN folder of one finished job from the runs folder: --runs, else FAIRSOLID_RUNS, else
    <root>/runs (older runs: the archived fairsolid checkout, see docs/FAIRSOLID.md)
  * the owner's CAD rules (numbered "- **R<n>**" lines of --rules-file) and the CAD index from the project repo's
    origin/main (git show)
and writes MANIFEST.md, then the zip. It refuses to write a zip that is over the size limit or that
contains anything that looks like a secret or a path from the user profile.
The zip is never committed (handoff/ is git-ignored).
"""
import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "handoff_templates"
MAX_MB = 50
SKIP_PARTS = {"__pycache__", ".venv", ".venv-cad", ".pytest_cache", "out", ".git", "work"}
# DECISIONS rules that bind CAD work (see reference/ in the zip)
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY|(api[_-]?key|secret|passwd|password|bearer)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,})",
    re.I)
PROFILE_RE = re.compile(r"C:[\\/]+Users[\\/]|/Users/[A-Za-z]|/home/[a-z]+/\.", re.I)
TEXT_EXT = {".md", ".txt", ".py", ".json", ".csv", ".toml", ".sh", ".html", ".cfg", ".log", ".yml", ".yaml"}


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError(f"{' '.join(cmd)} failed: {r.stderr.strip()}")
    return r.stdout


def main_checkout(start):
    common = Path(run(["git", "rev-parse", "--git-common-dir"], cwd=start).strip())
    if not common.is_absolute():
        common = (Path(start) / common).resolve()
    top = common.parent
    fs = top / "pipelines" / "fairsolid"
    return fs if fs.is_dir() else top


def newest_rev(job_dir):
    revs = [(int(m.group(1)), p) for p in job_dir.iterdir() if p.is_dir() and (m := re.fullmatch(r"rev(\d+)", p.name))]
    if not revs:
        raise SystemExit(f"no revN folder in {job_dir}")
    return max(revs)[1]


def repo_show(repo, path):
    for ref in ("origin/main", "HEAD"):
        try:
            return run(["git", "show", f"{ref}:{path}"], cwd=repo), ref
        except RuntimeError:
            continue
    raise SystemExit(f"cannot read {path} from {repo}")


def rules_excerpt(repo, rules_file, numbers):
    text, ref = repo_show(repo, rules_file)
    sha = run(["git", "rev-parse", "--short", ref], cwd=repo).strip()
    lines = text.splitlines()
    out = [
        "# Project decision log: the CAD-related binding rules, verbatim",
        "",
        f"Excerpt of `{rules_file}` in the project repo, from `{ref}` at commit `{sha}`. Only the lines that bind CAD "
        f"work are kept (R{', R'.join(map(str, numbers))}). "
        "The text is the owner's; nothing is paraphrased below this line.",
        "",
    ]
    found = set()
    for line in lines:
        m = re.match(r"- \*\*R(\d+)\*\*", line)
        if m and int(m.group(1)) in numbers:
            out += [line, ""]
            found.add(int(m.group(1)))
    missing = set(numbers) - found
    if missing:
        raise SystemExit(f"rules not found in {rules_file}: {sorted(missing)}")
    return "\n".join(out)


DESCRIBE = [
    ("HANDOFF.md", "Start here: what Fairsolid is, install, run, runs layout, render, export, verify."),
    ("RULES.md", "The owner's binding CAD rules, numbered, with the source of each."),
    ("TASK-TEMPLATE.md", "Blank job form the owner fills in for each new CAD job."),
    ("MANIFEST.md", "This file: every file in the zip and why it is there."),
    ("env/requirements-fairsolid-lock.txt", "Exact package versions of the Fairsolid venv (Python 3.13)."),
    ("env/requirements-build123d-lock.txt", "Exact package versions of the build123d venv that built and rendered the example (Python 3.13)."),
    ("tools/check_step.py", "Checks each STEP: one solid, valid, volume, bounding box (no floating pieces)."),
    ("tools/render_views.py", "Renders the 2D bottom view and trimetric view PNGs from STEP / STL files."),
    ("reference/project-DECISIONS-cad-rules.md", "Verbatim text of the owner's CAD rules from the project repo's decision log."),
    ("reference/project-cad-README.md", "The project's CAD index: how models, trimetrics and 'selected for build' are recorded."),
    ("reference/project-render_trimetric.py", "The project's headless trimetric renderer: shows the camera and style (needs OCP + VTK)."),
    ("fairsolid/pyproject.toml", "Fairsolid package definition: Python >=3.13, dependencies, `fairsolid` command."),
    ("fairsolid/README.md", "What Fairsolid does and its commands."),
    ("fairsolid/AGENTS.md", "Fairsolid working rules for AI assistants."),
    ("fairsolid/.gitignore", "What the source repo keeps out of git (runs, venv, out, work)."),
    ("fairsolid/docs/SURFACE_FIT_PLAN.md", "Design plan and decisions behind the surface-fit stages."),
    ("fairsolid/recipes/*", "Verified command recipes for CadQuery and MeshLab (and what is not yet written)."),
    ("fairsolid/src/*", "Fairsolid source code (pipeline, stages, CLI)."),
    ("fairsolid/tests/make_fixture.py", "Creates the test scan and nominal part in tests/data."),
    ("fairsolid/tests/*", "Fairsolid test suite (about 8 minutes in full)."),
    ("worked-example/*/scan_canon.ply", "The original part's scan in its canonical frame (rotated / moved only, never scaled); the overlay drawing reads it."),
    ("worked-example/*/SUMMARY.md", "Rev notes: the owner's answers, what changed, 2 g stress table, checks, open items."),
    ("worked-example/*/cnc_*.txt", "Manufacturing check output (sharp corners, thin walls) for one part."),
    ("worked-example/*/cnc_*.json", "The same manufacturing check as data."),
    ("worked-example/*/2d_bottom_view.png", "Deliverable: bottom view render."),
    ("worked-example/*/2d_trimetric.png", "Deliverable: trimetric render."),
    ("worked-example/*/2d_*.png", "Extra 2D drawing for the owner (dimensions, section, side view, scan overlay)."),
    ("worked-example/*/*_ports.*", "Machinist hole drawing of a <part>."),
    ("worked-example/*/renders_2d.py", "Makes the six 2D drawings from the STLs and drawing_geom.json."),
    ("worked-example/*/port_drawing.py", "Makes the machinist hole drawing from drawing_geom.json."),
    ("worked-example/*/dump_geom.py", "Writes drawing_geom.json from the model numbers."),
    ("worked-example/*/drawing_geom.json", "Model numbers the drawing scripts read."),
    ("worked-example/*/place.py", "Optimiser that placed the pass-throughs; wrote placement.json."),
    ("worked-example/*/placement.json", "Result of place.py."),
    ("worked-example/*/envelope.py", "Computes the in-tank envelope used for fit checks."),
    ("worked-example/*/render.py", "Fairsolid render_pair picture (scan above, shaded result below)."),
    ("worked-example/*/*.sh", "the owner's WSL command sequence (build, check, view); paths do not apply, the order does."),
    ("worked-example/*/build.log", "Output of the last successful build."),
    # Generic <part> files, after the named helpers above (first match wins):
    ("worked-example/*/*_assembly.*", "Whole assembly (STEP exact, STL mesh)."),
    ("worked-example/*/*_with_*.stl", "Display mesh: the parts with the envelopes of what fits on them."),
    ("worked-example/*/*_report.json", "Script output: mass, clearances and overlaps between parts."),
    ("worked-example/*/*.step", "One <part>, exact geometry (what gets built from)."),
    ("worked-example/*/*.stl", "The same <part> as a mesh."),
    ("worked-example/*/*.py", "THE RECIPE: the <part> build123d script (named numbers at the top) that makes every part."),
]


def describe(arc):
    rel = arc.split("/", 1)[1] if "/" in arc else arc
    for pat, text in DESCRIBE:
        if fnmatch.fnmatch(rel, pat):
            return text
    return "Supporting file."


def keep_source(rel):
    """Which git-tracked Fairsolid files go in the zip."""
    parts = Path(rel).parts
    if SKIP_PARTS & set(parts) or rel.endswith(".local.md"):
        return False
    top = parts[0]
    if top in {".cursor", "mcp", "addins"}:
        return False
    if top == "docs":
        return rel == "docs/SURFACE_FIT_PLAN.md"
    if top == "tests":
        return len(parts) == 2 and rel.endswith(".py")
    if top == "scripts":
        return False          # batch_eval.py holds paths into the user profile
    return True


def collect(root, repo, job, date_str, workdir, runs=None, rules_file=None, numbers=()):
    items = {}  # arcname -> source Path or bytes

    def add(arc, src):
        items[arc] = src

    for name in ("HANDOFF.md", "RULES.md", "TASK-TEMPLATE.md"):
        add(name, TEMPLATES / name)
    for sub in ("tools", "env"):
        for f in sorted((TEMPLATES / sub).iterdir()):
            add(f"{sub}/{f.name}", f)

    # Fairsolid source: only git-tracked files, minus tests/data and caches
    tracked = run(["git", "ls-files"], cwd=root).splitlines()
    for rel in tracked:
        if keep_source(rel):
            add(f"fairsolid/{rel}", root / rel)

    # worked example: newest rev only
    job_dir = Path(runs or root / "runs") / job
    rev = newest_rev(job_dir)
    scan = job_dir / "scan_canon.ply"
    if scan.exists():
        add(f"worked-example/{job}/scan_canon.ply", scan)
    for f in sorted(rev.rglob("*")):
        if f.is_file() and not (SKIP_PARTS & set(f.relative_to(rev).parts)):
            add(f"worked-example/{job}/{rev.name}/{f.relative_to(rev).as_posix()}", f)

    # project references (from origin/main)
    (workdir / "rules.md").write_text(rules_excerpt(repo, rules_file, numbers), encoding="utf-8")
    add("reference/project-DECISIONS-cad-rules.md", workdir / "rules.md")
    for src_path, arc in (("cad/README.md", "reference/project-cad-README.md"),
                          ("cad/render_trimetric.py", "reference/project-render_trimetric.py")):
        try:
            text, _ = repo_show(repo, src_path)
        except SystemExit:
            print(f"note: {src_path} not in the project repo; {arc} skipped")
            continue
        p = workdir / Path(arc).name
        p.write_text(text, encoding="utf-8")
        add(arc, p)
    return items, rev.name


def manifest(items, date_str, job, rev_name):
    rows = []
    for arc in sorted(items):
        src = items[arc]
        size = "(this file)" if arc == "MANIFEST.md" else f"{Path(src).stat().st_size:,}"
        rows.append((arc, size, describe(f"x/{arc}")))
    lines = [
        f"# MANIFEST: fairsolid-grok-handoff-{date_str}",
        "",
        f"Every file in this zip and why it is here. {len(rows)} files. Worked example: `{job}`, latest revision `{rev_name}` only.",
        "",
        "Not included on purpose: virtual environments, caches, the `out\\` folder, scan run folders under `runs\\` "
        "(90 to 190 MB each), earlier revisions of the example, test data (made by `tests\\make_fixture.py`), "
        "and anything from a user profile or any secret.",
        "",
        "| File | Bytes | Why it is here |",
        "|---|---:|---|",
    ]
    lines += [f"| `{a}` | {s} | {d} |" for a, s, d in rows]
    lines.append("")
    return "\n".join(lines)


def check_clean(items):
    problems = []
    for arc, src in items.items():
        p = Path(src)
        if p.suffix.lower() in TEXT_EXT and p.stat().st_size < 5_000_000:
            txt = p.read_text(encoding="utf-8", errors="replace")
            for rx, kind in ((SECRET_RE, "secret-like text"), (PROFILE_RE, "user-profile path")):
                m = rx.search(txt)
                if m:
                    problems.append(f"{arc}: {kind}: {m.group(0)[:60]!r}")
        if SKIP_PARTS & set(Path(arc).parts):
            problems.append(f"{arc}: excluded folder")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--job", required=True, help="run folder name of the finished job to include")
    ap.add_argument("--root", type=Path, default=None, help="fairsolid folder (default: <main checkout>/pipelines/fairsolid)")
    ap.add_argument("--runs", type=Path, default=os.environ.get("FAIRSOLID_RUNS") or None,
                    help="folder holding the run folders (default: FAIRSOLID_RUNS, else <root>/runs)")
    ap.add_argument("--rules-repo", type=Path, default=os.environ.get("RULES_REPO") or None,
                    help="project repo checkout whose CAD rules go in the zip (default: RULES_REPO)")
    ap.add_argument("--rules-file", required=True, help="decision log path inside --rules-repo (no default)")
    ap.add_argument("--rule-numbers", required=True, help="comma-separated R-numbers of the CAD rules to copy (no default)")
    ap.add_argument("--out", type=Path, default=None, help="output folder (default: <root>/handoff)")
    ap.add_argument("--copy-to", type=Path, default=None)
    a = ap.parse_args()

    if a.rules_repo is None:
        raise SystemExit("set --rules-repo or RULES_REPO to the project checkout (no machine path is assumed)")
    numbers = [int(x) for x in a.rule_numbers.split(",") if x.strip()]
    root = (a.root or main_checkout(HERE)).resolve()
    out = (a.out or root / "handoff").resolve()
    out.mkdir(parents=True, exist_ok=True)
    name = f"fairsolid-grok-handoff-{a.date}"
    zip_path = out / f"{name}.zip"
    work = out / "_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()
    try:
        items, rev_name = collect(root, a.rules_repo, a.job, a.date, work, a.runs, a.rules_file, numbers)
        items["MANIFEST.md"] = work / "MANIFEST.md"
        (work / "MANIFEST.md").write_text(manifest(items, a.date, a.job, rev_name), encoding="utf-8")
        problems = check_clean(items)
        if problems:
            raise SystemExit("refusing to build, found:\n  " + "\n  ".join(problems))
        tmp = zip_path.with_suffix(".zip.tmp")
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for arc in sorted(items):
                z.write(items[arc], f"{name}/{arc}")
        size = tmp.stat().st_size
        if size > MAX_MB * 1024 * 1024:
            tmp.unlink()
            raise SystemExit(f"zip is {size / 1e6:.1f} MB, over the {MAX_MB} MB limit")
        tmp.replace(zip_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"zip:   {zip_path}")
    print(f"size:  {zip_path.stat().st_size:,} bytes ({zip_path.stat().st_size / 1e6:.1f} MB)")
    print(f"files: {len(items)}")
    if a.copy_to:
        a.copy_to.mkdir(parents=True, exist_ok=True)
        shutil.copy2(zip_path, a.copy_to / zip_path.name)
        print(f"copy:  {a.copy_to / zip_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
