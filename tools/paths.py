"""Where part sources and working outputs live. No hardcoded paths.

    parts_home()     $HBCAD_PARTS_HOME, else [paths] parts_home in local.toml, else ~/cad-parts
    job_src(job)     <parts_home>/<job>/src     build scripts, inputs, params, notes
    run_dir(job)     <parts_home>/<job>/runs/<YYYYMMDD-HHMM>/  (created) working outputs: meshes, solver files, renders
    models_dir()     $MODELS_DIR, else [paths] models_dir in local.toml (finished deliverables, via publish-to-models)

Working outputs never go inside a git repo; run_dir refuses a parts home inside one.
"""
import os, re, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _local(key, toml=None):
    p = Path(toml) if toml else ROOT / "local.toml"
    if not p.exists():
        return ""
    section = ""
    for line in p.read_text().splitlines():
        h = re.match(r"\s*\[([^\]]*)\]", line)
        if h:
            section = h.group(1).strip(); continue
        if section != "paths":
            continue
        m = re.match(r"\s*" + re.escape(key) + r"\s*=\s*['\"]([^'\"]*)['\"]", line)
        if m:
            return m.group(1)
    return ""


def parts_home(env=None, toml=None) -> Path:
    env = os.environ if env is None else env
    return Path(os.path.expanduser(env.get("HBCAD_PARTS_HOME") or _local("parts_home", toml) or "~/cad-parts"))


def job_src(job, env=None, toml=None) -> Path:
    return parts_home(env, toml) / job / "src"


def in_git(p) -> bool:
    q = Path(p)
    while not q.exists():
        q = q.parent
    try:
        r = subprocess.run(["git", "-C", str(q), "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
    except OSError:  # git not installed: fall back to looking for a .git entry
        return any((d / ".git").exists() for d in (q.resolve(), *q.resolve().parents))
    return r.returncode == 0 and r.stdout.strip() == "true"


def run_dir(job, stamp=None, env=None, toml=None, create=True) -> Path:
    home = parts_home(env, toml)
    if in_git(home):
        raise SystemExit(f"paths.py: parts home {home} is inside a git repo; set HBCAD_PARTS_HOME outside it")
    d = home / job / "runs" / (stamp or time.strftime("%Y%m%d-%H%M"))
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def models_dir(env=None, toml=None) -> Path:
    env = os.environ if env is None else env
    v = env.get("MODELS_DIR") or _local("models_dir", toml)
    if not v:
        raise SystemExit("paths.py: MODELS_DIR is not set (setup.sh prints it)")
    return Path(os.path.expanduser(v))


if __name__ == "__main__":
    print("parts_home", parts_home())
