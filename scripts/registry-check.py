#!/usr/bin/env python3
"""Automation registry check (read-only). Stdlib only.

Usage (repo root):
  registry-check.py                     full scan
  registry-check.py --all-scripts       list every unregistered script/output (no grouping)
  registry-check.py --diff BASE HEAD    also: changed generated files nobody declares
  registry-check.py --run-checks        also: run each enabled entry's check_cmd, flag writes outside its `writes`
  registry-check.py --enabled ID        print true/false (for a workflow's first step: exit early when paused)
  registry-check.py --not-declared      filter stdin paths: print those no entry declares in `writes` (hook uses it so
                                        declared outputs, e.g. an auto-committed dashboard, never trip the state check)
  registry-check.py --set ID on|off     pause/resume an entry (edits its `enabled:` line; commit via a PR)
Mode comes from .state-check-mode (comment = exit 0, block = exit 1 on any flag), same as state-check.sh.
Registry: automation.yml (simple YAML subset, or real YAML if PyYAML is installed) or automation.json.
Flags: STALE-OUTPUT, ORPHAN-SCRIPT, UNDECLARED-OUTPUT, DUPLICATE-OUTPUT. Declared auto-writers are allowed.
"""
import json, os, re, subprocess, sys

def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout

def glob_re(g):
    out, i = "", 0
    while i < len(g):
        if g.startswith("**/", i): out += "(?:.*/)?"; i += 3
        elif g.startswith("**", i): out += ".*"; i += 2
        elif g[i] == "*": out += "[^/]*"; i += 1
        elif g[i] == "?": out += "[^/]"; i += 1
        else: out += re.escape(g[i]); i += 1
    return re.compile(out + "$")

def matches(path, globs): return any(glob_re(g).match(path) for g in globs)

def scalar(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [scalar(x) for x in v[1:-1].split(",") if x.strip()]
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'": return v[1:-1]
    return {"true": True, "false": False, "yes": True, "no": False}.get(v.lower(), v)

def mini_yaml(text):
    """Subset: top-level keys; `automations:` list of flat maps; values scalar, [inline list] or '- item' lists."""
    data, cur, key, lst = {}, None, None, None
    for raw in text.splitlines():
        line = raw.split(" #")[0].rstrip()
        if not line.strip() or line.lstrip().startswith("#"): continue
        ind = len(line) - len(line.lstrip()); s = line.strip()
        if ind == 0:
            k, _, v = s.partition(":"); key = k.strip(); cur = None
            data[key] = scalar(v) if v.strip() else []
            continue
        if s.startswith("- ") and key and isinstance(data[key], list) and (cur is None or ind <= cur["_ind"]):
            item = s[2:]
            if ":" in item and not item.startswith(("'", '"')):
                cur = {"_ind": ind}; data[key].append(cur); k, _, v = item.partition(":")
                cur[k.strip()] = scalar(v) if v.strip() else []; lst = k.strip()
            else: data[key].append(scalar(item))
            continue
        if cur is not None:
            if s.startswith("- "): cur[lst].append(scalar(s[2:])); continue
            k, _, v = s.partition(":"); lst = k.strip(); cur[lst] = scalar(v) if v.strip() else []
    for e in data.get("automations", []):
        if isinstance(e, dict): e.pop("_ind", None)
    return data

def load(root):
    for n in ("automation.yml", "automation.yaml", "automation.json"):
        p = os.path.join(root, n)
        if os.path.exists(p):
            t = open(p).read()
            if n.endswith(".json"): return json.loads(t)
            try:
                import yaml; return yaml.safe_load(t)
            except ImportError: return mini_yaml(t)
    return None

def L(v): return v if isinstance(v, list) else ([v] if v else [])
def last_ct(globs, files):
    hit = [f for f in files if matches(f, globs)]
    if not hit: return 0
    out = git("log", "-1", "--format=%ct", "--", *hit).strip()
    return int(out or 0)

SCRIPT_EXT = (".py", ".sh", ".ps1", ".js", ".ts", ".rb", ".bat", ".cmd")
DEFAULT_GEN = ["**/*.checks.json", "**/*_report.json", "**/*.pdf", "**/*.html", "**/*.xlsx"]
# Folders that hold hand-made or third-party documents, never flagged (merged with the registry's own ignore/handmade lists).
DEFAULT_IGNORE = ["**/vendor/**", "**/third_party/**", "**/datasheets/**", "**/datasheet/**", "**/manuals/**",
                  "**/reference/**", "**/references/**", "**/handmade/**", "**/hand-made/**"]
DOC_EXT = (".pdf", ".html", ".htm", ".xlsx")
REV_DIR = re.compile(r"(^|/)[^/]*(-rev\d+|[-_]v\d+|-\d{4}-\d{2}-\d{2})(/|$)", re.I)

def main(argv):
    root = git("rev-parse", "--show-toplevel").strip() or "."
    os.chdir(root)
    reg = load(root)
    if "--enabled" in argv:
        i = argv.index("--enabled"); e = next((e for e in (reg or {}).get("automations", []) if isinstance(e, dict) and str(e.get("id")) == argv[i+1]), None)
        print("false" if not e or e.get("enabled") is False else "true"); return 0
    if "--set" in argv:
        i = argv.index("--set"); eid, val = argv[i+1], {"on": "true", "off": "false"}[argv[i+2]]
        p = next(n for n in ("automation.yml", "automation.yaml") if os.path.exists(n))
        lines, inside, done = open(p).read().split("\n"), False, False
        for j, l in enumerate(lines):
            m = re.match(r"\s*-\s*id:\s*(\S+)", l)
            if m: inside = m.group(1).strip("'\"") == eid
            elif inside and re.match(r"\s+enabled:", l):
                lines[j] = re.sub(r"enabled:\s*\S+", "enabled: " + val, l); done = True; inside = False
        if not done: print(f"no enabled: line for {eid}", file=sys.stderr); return 2
        open(p, "w").write("\n".join(lines)); print(f"{eid} enabled: {val} in {p} (commit it on a branch + PR)"); return 0
    if "--not-declared" in argv:
        globs = [g for e in (reg or {}).get("automations", []) if isinstance(e, dict) for g in L(e.get("writes"))]
        for line in sys.stdin.read().splitlines():
            if line and not matches(line, globs): print(line)
        return 0
    if reg is None: print("NOTE: no automation.yml; registry check skipped."); return 0
    entries = [e for e in reg.get("automations", []) if isinstance(e, dict)]
    ignore = L(reg.get("ignore")) + L(reg.get("handmade")) + DEFAULT_IGNORE; gen = L(reg.get("generated_patterns")) or DEFAULT_GEN
    files = [f for f in git("ls-files").splitlines() if f]
    flags = []
    declared_scripts = set()
    for e in entries:
        declared_scripts.update(L(e.get("script"))); declared_scripts.update(L(e.get("helpers")))
    # ORPHAN-SCRIPT: only things that run on their own need an entry: workflows, hooks, and scripts
    # those call. Plain scripts are summarised (list them with --all-scripts). A script named inside a
    # declared script/workflow counts as its helper.
    is_wf = lambda f: bool(re.match(r"\.github/workflows/.+\.ya?ml$", f)) or f.startswith(".githooks/")
    def text(f):
        try: return open(f, errors="ignore").read()
        except OSError: return ""
    runners = [f for f in files if is_wf(f)]
    run_txt = "\n".join(text(f) for f in runners)
    decl_txt = "\n".join(text(s) for s in declared_scripts if s in files)
    called = lambda f: f in run_txt or bool(re.search(r"(?<![\w.-])" + re.escape(os.path.basename(f)) + r"(?![\w.-])", run_txt))
    helper = lambda f: os.path.basename(f) in decl_txt or os.path.splitext(os.path.basename(f))[0] in re.findall(r"(?:import|from)\s+([\w.]+)", decl_txt)
    plain = []
    for f in files:
        if f in declared_scripts or matches(f, ignore): continue
        if is_wf(f) or (f.endswith(SCRIPT_EXT) and called(f)):
            if not helper(f): flags.append(f"ORPHAN-SCRIPT {f}: runs automatically but has no registry entry (add one or list it as a helper)")
        elif f.endswith(SCRIPT_EXT) and not helper(f): plain.append(f)
    if plain:
        if "--all-scripts" in argv:
            for f in plain: print(f"NOTE: script {f} not in registry (only needed if it writes committed outputs)")
        else: print(f"NOTE: {len(plain)} other scripts not in registry; only ones that write committed outputs need entries (--all-scripts lists them)")
    for e in entries:
        for s in L(e.get("script")):
            if s not in files: flags.append(f"ORPHAN-SCRIPT {e.get('id')}: entry's script {s} not in repo")
    # Undeclared writers: workflows that commit/push but aren't declared auto_commit
    for f in files:
        if re.match(r"\.github/workflows/.+\.ya?ml$", f) and re.search(r"git (commit|push)|git-auto-commit|create-pull-request", open(f, errors="ignore").read()):
            e = next((e for e in entries if f in L(e.get("script"))), None)
            if not e or not e.get("auto_commit"):
                flags.append(f"UNDECLARED-OUTPUT {f}: workflow commits/pushes but its entry doesn't declare auto_commit: true + writes")
    # UNDECLARED-OUTPUT: tracked generated-looking files nobody claims
    claimed = [g for e in entries for g in L(e.get("writes"))]
    und = [f for f in files if matches(f, gen) and not matches(f, claimed) and not matches(f, ignore)]
    # PDF/HTML/XLSX are often made by hand: flag one only if a writer script names it (or its stem), or a
    # writer script sits in its folder. Checkers/tests/linkers that only read or link a file don't count.
    WRITES = re.compile(r"""open\([^)]*['"][wa]b?['"]|\.write_(text|bytes)\(|savefig|to_excel|to_html|\.save\(|output_pdf|writeFileSync|Out-File|Set-Content""")
    is_checker = lambda f: re.match(r"(check|test|lint|verify)[_-]", os.path.basename(f)) is not None
    fileset = set(files)
    writers = {f: t for f in files if (f.endswith(SCRIPT_EXT) or is_wf(f)) and not is_checker(f) for t in [text(f)] if WRITES.search(t)}
    def made_by_script(f):
        b = os.path.basename(f); stem = os.path.splitext(b)[0]; d = os.path.dirname(f)
        if os.path.join(d, stem + ".checks.json").lstrip("/") in fileset: return True   # a generator's own check file sits beside it
        for w, t in writers.items():
            if b in t or (len(stem) > 3 and re.search(r"(?<![\w-])" + re.escape(stem) + r"(?![\w-])", t)): return True
            if d and os.path.dirname(w) == d: return True
        return False
    und = [f for f in und if not f.lower().endswith(DOC_EXT) or made_by_script(f)]
    by_dir = {}
    for f in und: by_dir.setdefault(os.path.dirname(f) or ".", []).append(f)
    for d, fs in sorted(by_dir.items()):   # group big folders so a real repo isn't 100+ lines
        if len(fs) > 3 and "--all-scripts" not in argv:
            flags.append(f"UNDECLARED-OUTPUT {d}/: {len(fs)} generated-looking files, no entry writes them (e.g. {os.path.basename(fs[0])})")
        else: flags += [f"UNDECLARED-OUTPUT {f}: looks generated, no entry writes it" for f in fs]
    # DUPLICATE-OUTPUT: two entries write the same file; revision/date-named output folders
    owners = {}
    for e in entries:
        for f in files:
            if matches(f, L(e.get("writes"))): owners.setdefault(f, []).append(str(e.get("id")))
    for f, ids in owners.items():
        if len(ids) > 1: flags.append(f"DUPLICATE-OUTPUT {f}: written by {', '.join(ids)}")
        if REV_DIR.search(f): flags.append(f"DUPLICATE-OUTPUT {f}: revision/date-named output folder (old revisions live in git history)")
    # STALE-OUTPUT: inputs or script committed after outputs
    for e in entries:
        w = L(e.get("writes")); r = L(e.get("reads")) + L(e.get("script"))
        if not w or e.get("committed") in ("gitignored", "artifact", False): continue
        tw, tr = last_ct(w, files), last_ct(r, files)
        if tr and tw and tr > tw:
            paused = " (paused: enabled false)" if e.get("enabled") is False else ""
            flags.append(f"STALE-OUTPUT {e.get('id')}: inputs/script changed after its outputs{paused}. Re-run: {e.get('run_cmd') or e.get('script')}")
    if "--diff" in argv:
        i = argv.index("--diff"); base, head = argv[i+1], argv[i+2]
        for f in git("diff", "--name-only", f"{base}...{head}").splitlines():
            if matches(f, gen) and not matches(f, claimed) and not matches(f, ignore) and not any(f" {f}:" in x for x in flags):
                flags.append(f"UNDECLARED-OUTPUT {f}: changed in this PR, no entry writes it")
    if "--run-checks" in argv:
        before = set(git("status", "--porcelain").splitlines())
        for e in entries:
            if e.get("enabled") is False or not e.get("check_cmd"): continue
            subprocess.run(e["check_cmd"], shell=True, capture_output=True)
            after = set(git("status", "--porcelain").splitlines())
            for line in sorted(after - before):
                p = line[3:]
                if not matches(p, L(e.get("writes"))):
                    flags.append(f"UNDECLARED-OUTPUT {p}: {e.get('id')} check_cmd wrote outside its declared writes")
            before = after
    for e in entries:
        if e.get("auto_commit") and e.get("bypass"):
            print(f"NOTE: {e.get('id')} auto-commits and bypasses protection: {e.get('bypass')} (declared, allowed){' - PAUSED' if e.get('enabled') is False else ''}")
    for f in flags: print("WARN:", f)
    mf = ".state-check-mode"; mode = open(mf).read().strip() if os.path.exists(mf) else "comment"
    if flags and mode == "block":
        print("BLOCK: mode=block (.state-check-mode). Fix the registry/outputs, or add the no-state-change label."); return 1
    return 0

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
