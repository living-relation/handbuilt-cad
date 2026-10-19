"""Title-block defaults and the drawing initials rule for the drawing engine.

Project name, looked up per drawing, first match wins:
  1. the spec itself: spec['project']
  2. environment: DRAWING_PROJECT
  3. <repo>/local.toml  [drawing] project = "..."   (see local.toml.example)
  4. neutral default: "PROJECT"

Initials (DRAWN in the title block, BY in the rev log). The rule:
  - DRAWN = the initials on Rev A of that drawing's rev log. It never changes after Rev A.
  - BY    = the initials of the PERSON WHO REQUESTED that change. Never an agent or tool name.
  - Nobody's initials are hard-coded, and nothing is ever guessed.
The requester's initials come from, first match wins:
  1. environment: DRAWING_INITIALS
  2. the per-computer file ~/.drawing-initials (Windows: %USERPROFILE%\\.drawing-initials; one line, e.g. "DG")
  3. WSL only: the Windows profile's .drawing-initials (/mnt/c/Users/*/.drawing-initials, when exactly one value is found)
If none is set: a human at a terminal is asked once and the answer is saved to ~/.drawing-initials; with no
terminal (an agent, CI) the tool STOPS with InitialsMissing. A tool never invents a name.
"""
import glob
import os
import re
import sys

try:
    import tomllib
except ImportError:          # Python < 3.11
    tomllib = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULTS = {'project': 'PROJECT'}
ENV = {'project': 'DRAWING_PROJECT'}

INITIALS_ENV = 'DRAWING_INITIALS'
INITIALS_FILENAME = '.drawing-initials'
INITIALS_RE = re.compile(r'^[A-Z]{2,4}$')
# Names of agents and tools, and placeholders: never a valid DRAWN / BY (lower case; initials are compared upper-cased).
BANNED = frozenset(n.lower() for n in (
    'claude', 'stevecad', 'steve', 'sc', 'grok', 'grokbot', 'fairsolid', 'cursor', 'codex', 'gpt', 'gemini', 'copilot',
    'agent', 'bot', 'tool', 'system', 'auto', 'script', 'unknown', 'none', 'null', 'tbd', 'xx', 'xxx'))


class InitialsMissing(RuntimeError):
    """No requester initials configured and no human to ask."""


def bad_initials(s):
    """Why `s` is not valid DRAWN / BY initials, or None when it is fine."""
    s = (s or '').strip()
    if not s:
        return 'blank'
    if s.lower() in BANNED or re.sub(r'[^a-z]', '', s.lower()) in BANNED:
        return f'{s!r} is an agent / tool / placeholder name'
    if not INITIALS_RE.match(s.upper()):
        return f'{s!r} is not 2-4 letters (a person\'s initials)'
    return None


def check_initials(s):
    """Return `s` normalised (upper case) or raise ValueError."""
    why = bad_initials(s)
    if why:
        raise ValueError(f'bad initials: {why}')
    return s.strip().upper()


def initials_path(home=None):
    return os.path.join(home or os.path.expanduser('~'), INITIALS_FILENAME)


def _read_file(p):
    try:
        with open(p, encoding='utf-8') as f:
            return f.readline().strip()
    except OSError:
        return ''


def read_initials(environ=None, home=None, windows_homes=None):
    """The configured requester initials, or '' when none is set. Does not prompt and does not validate."""
    environ = os.environ if environ is None else environ
    v = (environ.get(INITIALS_ENV) or '').strip()
    if v:
        return v
    v = _read_file(initials_path(home))
    if v:
        return v
    if windows_homes is None:
        windows_homes = glob.glob('/mnt/c/Users/*') if os.path.isdir('/mnt/c/Users') else []
    found = {_read_file(os.path.join(h, INITIALS_FILENAME)) for h in windows_homes} - {''}
    return found.pop() if len(found) == 1 else ''


def requester_initials(environ=None, home=None, windows_homes=None, stdin=None, stdout=None, ask=input):
    """The initials of the person requesting this drawing change, validated.

    Missing + interactive terminal: ask once and save ~/.drawing-initials. Missing + no terminal: raise InitialsMissing."""
    v = read_initials(environ, home, windows_homes)
    if v:
        return check_initials(v)
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    p = initials_path(home)
    if not (stdin and stdout and stdin.isatty() and stdout.isatty()):
        raise InitialsMissing(
            f'No drawing initials set. Put the requesting person\'s initials (2-4 letters, e.g. DG) in {p} '
            f'or set {INITIALS_ENV}. Agents must not guess or use an agent / tool name: ask the person who is requesting '
            f'the change, or stop.')
    while True:
        a = ask('Drawing initials of the person requesting this change (2-4 letters, saved to %s): ' % p)
        why = bad_initials(a)
        if not why:
            break
        print('  ' + why, file=stdout)
    a = a.strip().upper()
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(a + '\n')
    return a


def read_local(root=ROOT):
    p = os.path.join(root, 'local.toml')
    if not os.path.isfile(p) or tomllib is None:
        return {}
    with open(p, 'rb') as f:
        return tomllib.load(f)


def title_defaults(root=ROOT, environ=None):
    """{'project': ...} from env, then local.toml [drawing], then the neutral default."""
    environ = os.environ if environ is None else environ
    sec = (read_local(root).get('drawing') or {})
    out = {}
    for k, d in DEFAULTS.items():
        out[k] = environ.get(ENV[k]) or sec.get(k) or d
    return out


def title_info(info, root=ROOT, environ=None):
    """Fill a missing / empty 'project' in a title-block info dict (spec values win). 'drawn' is never defaulted here:
    the caller sets it from Rev A of the rev log (dwg.resolve_drawn)."""
    d = title_defaults(root, environ)
    out = dict(info)
    for k in DEFAULTS:
        if not out.get(k):
            out[k] = d[k]
    return out
