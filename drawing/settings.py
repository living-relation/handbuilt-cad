"""Title-block defaults for the drawing engine (company / project name, drawn-by).

Looked up per drawing, first match wins:
  1. the spec itself: spec['project'], spec['drawn']
  2. environment: DRAWING_PROJECT, DRAWING_DRAWN
  3. <repo>/local.toml  [drawing] project = "...", drawn = "..."   (see local.toml.example)
  4. neutral defaults: project "PROJECT", drawn "-"
Nothing project- or person-specific is hard-coded here.
"""
import os

try:
    import tomllib
except ImportError:          # Python < 3.11
    tomllib = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULTS = {'project': 'PROJECT', 'drawn': '-'}
ENV = {'project': 'DRAWING_PROJECT', 'drawn': 'DRAWING_DRAWN'}


def read_local(root=ROOT):
    p = os.path.join(root, 'local.toml')
    if not os.path.isfile(p) or tomllib is None:
        return {}
    with open(p, 'rb') as f:
        return tomllib.load(f)


def title_defaults(root=ROOT, environ=None):
    """{'project': ..., 'drawn': ...} from env, then local.toml [drawing], then neutral defaults."""
    environ = os.environ if environ is None else environ
    sec = (read_local(root).get('drawing') or {})
    out = {}
    for k, d in DEFAULTS.items():
        out[k] = environ.get(ENV[k]) or sec.get(k) or d
    return out


def title_info(info, root=ROOT, environ=None):
    """Fill missing / empty 'project' and 'drawn' in a title-block info dict (spec values win)."""
    d = title_defaults(root, environ)
    out = dict(info)
    for k in DEFAULTS:
        if not out.get(k):
            out[k] = d[k]
    return out
