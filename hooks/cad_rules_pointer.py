"""SessionStart hook: point the agent at the handbuilt-cad CAD rules (Dan G9 a, 2026-11-25).

The plugin's rules live in AGENTS.md ("CAD and drawing rules" 1-30) and drawing/DRAWING-RULES.md. Nothing loaded
them on their own, so sessions doing CAD work in other repos never read them. This hook adds a short pointer to
every session's context:
- the working folder shows CAD work (model files, a cad/ or models folder, MADE-WITH.md, a Fusion build script):
  read the rules before any CAD change, and load the matching handbuilt-cad skill;
- otherwise (a project that has not decided it is a CAD project yet): one line saying to read them first if the
  session turns to CAD work.

Read-only, stdlib only, Linux / macOS / Windows. Prints one JSON object on stdout (Claude Code SessionStart
hookSpecificOutput.additionalContext) and exits 0. Any error still exits 0 with the short line, so a session
is never blocked.

    python3 hooks/cad_rules_pointer.py [folder]     (folder defaults to the payload's cwd, else the current folder)
"""
import json
import os
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
MODEL_EXT = {'.step', '.stp', '.f3d', '.f3z', '.fcstd', '.3mf', '.stl', '.iges', '.igs', '.dxf', '.sldprt', '.sldasm'}
MARKER_FILES = {'made-with.md', 'drawing-revs.md', 'build_fusion.py', 'revlog.md'}
CAD_DIRS = {'cad', 'models', 'cad-parts', 'drawings'}
SKIP_DIRS = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', '.claude', '.cursor', 'archives', '_archive'}
MAX_DEPTH = 3
MAX_ENTRIES = 5000


def cad_signals(root):
    """Return a short list of reasons the folder looks like CAD work (empty = none found)."""
    found = []
    seen = 0
    root = Path(root)
    if not root.is_dir():
        return found
    stack = [(root, 0)]
    while stack and len(found) < 3 and seen < MAX_ENTRIES:
        d, depth = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        for e in entries:
            seen += 1
            name = e.name.lower()
            try:
                is_dir = e.is_dir(follow_symlinks=False)
            except OSError:
                continue
            if is_dir:
                if name in SKIP_DIRS:
                    continue
                if name in CAD_DIRS and depth < 2:
                    found.append('folder ' + os.path.relpath(e.path, root))
                if depth + 1 <= MAX_DEPTH:
                    stack.append((Path(e.path), depth + 1))
            elif name in MARKER_FILES or os.path.splitext(name)[1] in MODEL_EXT:
                found.append('file ' + os.path.relpath(e.path, root))
            if len(found) >= 3:
                break
    return found


def message(signals):
    agents = PLUGIN / 'AGENTS.md'
    rules = PLUGIN / 'drawing' / 'DRAWING-RULES.md'
    if signals:
        return ('HANDBUILT-CAD RULES: this folder shows CAD work (%s). Before any CAD change (models, drawings, '
                'BOMs, fasteners, Fusion or script builds), read the CAD rules in %s ("CAD and drawing rules" 1-30) '
                'and %s, and load the matching handbuilt-cad skill (cad-drawing, cnc-part-check, '
                'primary-source-spec-check, publish-to-models, sim-stack ...). Key rules: 22 fasteners from SR '
                'Fasteners; 28 rebuild with the method that created the model; 30 BOMs and parts lists come from the '
                'model. The project\'s own rules still bind where they are stricter.' % (', '.join(signals), agents, rules))
    return ('HANDBUILT-CAD RULES: if this session turns to CAD work (models, drawings, STEP or Fusion files, '
            'fasteners, BOMs), read the CAD rules in %s ("CAD and drawing rules" 1-30) first.' % agents)


def main(argv):
    folder = argv[1] if len(argv) > 1 else None
    if folder is None:
        try:
            raw = '' if sys.stdin is None or sys.stdin.isatty() else sys.stdin.read()
            payload = json.loads(raw) if raw.strip() else {}
            folder = payload.get('cwd') if isinstance(payload, dict) else None
        except (ValueError, OSError):
            folder = None
    try:
        sig = cad_signals(folder or os.getcwd())
    except Exception:          # never block a session
        sig = []
    out = {'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': message(sig)}}
    sys.stdout.write(json.dumps(out) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
