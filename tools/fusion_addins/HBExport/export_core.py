"""Pure helpers for the HB Export add-in (no adsk import, unit-tested in tests/test_fusion_addins.py)."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from hbcad_fusion_common.names import safe_name  # noqa: E402

# key -> (label, extension). Order is the dialog order.
FORMATS = [
    ('step', 'STEP', '.step'),
    ('f3d', 'Fusion archive (F3D)', '.f3d'),
    ('stl', 'STL', '.stl'),
    ('3mf', '3MF', '.3mf'),
    ('iges', 'IGES', '.igs'),
    ('sat', 'SAT', '.sat'),
    ('dxf', 'DXF of selected face or sketch', '.dxf'),
]
FORMAT_KEYS = [k for k, _, _ in FORMATS]
EXT = {k: e for k, _, e in FORMATS}
DEFAULTS = {'folder': '', 'checked': ['step', 'f3d'], 'base_name': ''}

def target_paths(folder, base, keys):
    """Ordered {key: full path}. Same name every time, so exports overwrite in place."""
    base = safe_name(base)
    out = {}
    for k in FORMAT_KEYS:
        if k in keys:
            out[k] = os.path.join(folder, base + EXT[k])
    return out


def summarize(results):
    """results: {key: (ok, path_or_error)} -> human text."""
    lines = []
    for k in FORMAT_KEYS:
        if k not in results:
            continue
        ok, msg = results[k]
        lines.append(('OK      ' if ok else 'FAILED  ') + k.upper() + ': ' + msg)
    return '\n'.join(lines) if lines else 'Nothing selected.'
