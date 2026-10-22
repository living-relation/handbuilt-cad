"""Owner notes (README.md) for every folder the handbuilt-cad layout uses. Add-only: an existing README.md is never touched.

    .venv/bin/python tools/folder_notes.py [--parts-home DIR] [--models DIR] [--dry-run | --check]

--check writes nothing: it lists every layout folder with neither README.md nor AGENTS.md and exits 1 if any (CAD Seeker uses it).

Writes, from templates/notes/*.md:
  <parts_home>/<job>/README.md               the job: src/, runs/, paired models folder
  <parts_home>/_archive/README.md            what is archived; safe to prune
  <parts_home>/<job>/src/README.md           the build scripts, how to run, paired models folder
  <parts_home>/<job>/runs/README.md          working outputs only, cleanup rule
  <models>/<job>/README.md                   the part, its revs (one line each from SUMMARY.md), paired parts-home folder
setup.sh runs it; publish-to-models runs it after filing a new job.
"""
import argparse, os, re, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "templates" / "notes"
JOB_RE = re.compile(r"^[a-z0-9][a-z0-9_]*_\d{4,6}$")


def tpl(name, **kw):
    s = (TPL / name).read_text()
    for k, v in kw.items():
        s = s.replace("@" + k.upper() + "@", v)
    return s


def write_new(p: Path, text, dry, log):
    if p.exists():
        log.append(f"kept   {p}"); return False
    if not dry:
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
    log.append(f"added  {p}"); return True


def show(p) -> str:
    """Display a path without the user's home or Windows profile (no personal paths in notes)."""
    s = str(p)
    h = os.path.expanduser("~")
    if s.startswith(h):
        return "~" + s[len(h):]
    return re.sub(r"^(/mnt/[a-z]|[A-Za-z]:)[\\/]Users[\\/][^\\/]+[\\/](.*?)([\\/]Desktop[\\/])", r"<Desktop>/", s).replace("\\", "/")


def part_name(job):
    return re.sub(r"_\d{4,6}$", "", job)


def rev_line(rev: Path):
    """One line for a rev folder, from its SUMMARY.md: the heading after 'revX:', else a 'What changed' / 'Was' line, else the model files."""
    s = rev / "SUMMARY.md"
    steps = sorted(p.name for p in rev.glob("*.st*p"))
    if s.exists():
        lines = s.read_text(errors="replace").splitlines()
        h = next((l for l in lines if l.startswith("# ")), "")
        m = re.search(r"rev[\w.-]*(?::|\s+[-\u2013])\s*(.+)$", h)
        if m and m.group(1).strip():
            return m.group(1).strip()
        for l in lines:
            l2 = l.strip("- ").strip()
            if re.match(r"(What changed|Was |Status|Superseded)", l2, re.I):
                return l2[:160]
        txt = "\n".join(lines)
        bits = []
        if re.search(r"Shared / pre-version files", txt): bits.append("shared / pre-version files")
        m = re.search(r"Files \((\d+)\)", txt)
        if m: bits.append(m.group(1) + " files")
        if steps: bits.append("models: " + ", ".join(steps[:3]) + (" ..." if len(steps) > 3 else ""))
        m = re.search(r"Moved here (\d{4}-\d\d-\d\d)", txt)
        if m: bits.append("filed " + m.group(1))
        if bits: return "; ".join(bits)
    return ("model files: " + ", ".join(steps[:4]) + (" ..." if len(steps) > 4 else "")) if steps else "no SUMMARY.md / model file at top level"


def revs(job_dir: Path):
    rs = [d for d in job_dir.iterdir() if d.is_dir() and d.name.startswith("rev")]
    return sorted(rs, key=lambda d: d.name)


def run(parts_home: Path, models: Path | None, dry=False):
    log = []
    if parts_home.is_dir():
        write_new(parts_home / "_archive" / "README.md", tpl("archive.md"), dry, log)
        for job in sorted(d for d in parts_home.iterdir() if d.is_dir() and JOB_RE.match(d.name)):
            mpath = (show(models / job.name) + f" ($MODELS_DIR/{job.name})") if models else "$MODELS_DIR/" + job.name
            write_new(job / "README.md", tpl("job.md", job=job.name, models=mpath), dry, log)
            write_new(job / "src" / "README.md", tpl("src.md", job=job.name, models=mpath), dry, log)
            write_new(job / "runs" / "README.md", tpl("runs.md", job=job.name), dry, log)
    if models and models.is_dir():
        for job in sorted(d for d in models.iterdir() if d.is_dir() and JOB_RE.match(d.name)):
            rl = "\n".join(f"- `{r.name}`: {rev_line(r)}" for r in revs(job)) or "- (no rev folders yet)"
            ph = parts_home / job.name
            pair = f"`{show(ph)}`" if ph.is_dir() else f"none: this job has no parts-home folder (no build scripts were kept in `{show(parts_home)}`); its scripts, if any, are in the rev folders' `src/`"
            write_new(job / "README.md", tpl("models-job.md", job=job.name, part=part_name(job.name), revs=rl, pair=pair), dry, log)
    return log


def has_note(d: Path):
    return (d / "README.md").exists() or (d / "AGENTS.md").exists()


def layout_dirs(parts_home: Path, models: Path | None):
    out = []
    if parts_home.is_dir():
        out += [parts_home, parts_home / "_archive"]
        for job in sorted(d for d in parts_home.iterdir() if d.is_dir() and JOB_RE.match(d.name)):
            out += [job, job / "src", job / "runs"]
    if models and models.is_dir():
        out.append(models)
        out += sorted(d for d in models.iterdir() if d.is_dir() and JOB_RE.match(d.name))
    return [d for d in out if d.is_dir()]


def missing(parts_home: Path, models: Path | None):
    return [d for d in layout_dirs(parts_home, models) if not has_note(d)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parts-home"); ap.add_argument("--models"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    ph = Path(a.parts_home).expanduser() if a.parts_home else paths.parts_home()
    try:
        md = Path(a.models).expanduser() if a.models else paths.models_dir()
    except SystemExit:
        md = None
    if a.check:
        miss = missing(ph, md)
        print("\n".join(f"missing note: {d}" for d in miss) or "every layout folder has a README.md or AGENTS.md")
        sys.exit(1 if miss else 0)
    log = run(ph, md, a.dry_run)
    print("\n".join(log)); print(f"{sum(l.startswith('added') for l in log)} added, {sum(l.startswith('kept') for l in log)} kept")


if __name__ == "__main__":
    main()