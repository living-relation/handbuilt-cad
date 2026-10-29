"""Tiny JSON settings store shared by the handbuilt-cad Fusion add-ins (no adsk import, testable)."""
import json
import os


def settings_dir():
    base = os.environ.get('APPDATA') or os.path.expanduser('~')
    return os.path.join(base, 'HandbuiltCAD', 'fusion-addins')


def load(name, defaults, folder=None):
    path = os.path.join(folder or settings_dir(), name + '.json')
    data = dict(defaults)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        if isinstance(saved, dict):
            data.update({k: v for k, v in saved.items() if k in defaults})
    except (OSError, ValueError):
        pass
    return data


def save(name, data, folder=None):
    folder = folder or settings_dir()
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name + '.json')
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)
    return path
