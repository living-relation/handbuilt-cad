import re

_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_name(name):
    """File-safe base name. Strips Fusion's ' v12' version suffix and illegal characters."""
    name = re.sub(r'\s+v\d+$', '', (name or '').strip())
    name = _BAD.sub('_', name).strip(' .')
    return name or 'export'
