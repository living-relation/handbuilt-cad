"""Run the FreeCAD FEM smoke check with the FreeCAD named in local.toml.

    python sim/smoke/run_freecad_check.py            (repo venv: Python 3.11+, no extra packages)

Looks up, environment variable first, then the repo's local.toml (created by setup.sh / setup.ps1 from local.toml.example):
  [paths] freecad_dir  (FREECAD_DIR)  folder that holds bin/freecadcmd(.exe)                 required
  [paths] cad_staging  (CAD_STAGING)  where the result file goes; empty = next to this script  optional
Under WSL with a Windows FreeCAD (freecadcmd.exe) the result must go to a Windows folder (/mnt/<drive>/...): a Windows
program never writes into the WSL filesystem. Exit 0 = OK, 1 = FreeCAD ran but the check failed, 2 = setup/config problem.
"""
import os, shutil, subprocess, sys, tempfile

try:
    import tomllib
except ImportError:          # Python < 3.11
    tomllib = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'freecad_check.py')


class SetupError(RuntimeError):
    pass


def read_local(root=ROOT):
    p = os.path.join(root, 'local.toml')
    if not os.path.isfile(p):
        return None
    if tomllib is None:
        raise SetupError('Python 3.11+ is needed to read local.toml (use the repo venv)')
    with open(p, 'rb') as f:
        return tomllib.load(f)


def setting(section, key, env, root=ROOT, environ=None):
    """Environment variable first, then local.toml [section] key. '' when unset."""
    environ = os.environ if environ is None else environ
    if environ.get(env):
        return environ[env]
    cfg = read_local(root)
    return ((cfg or {}).get(section) or {}).get(key, '') or ''


def find_freecadcmd(root=ROOT, environ=None):
    d = setting('paths', 'freecad_dir', 'FREECAD_DIR', root, environ)
    if not d:
        where = 'local.toml' if os.path.isfile(os.path.join(root, 'local.toml')) else \
            'local.toml (missing: run setup.sh or setup.ps1 to create it from local.toml.example)'
        raise SetupError('FreeCAD folder not set. Put it in %s as [paths] freecad_dir = "<folder with bin/freecadcmd>", '
                         'or set FREECAD_DIR.' % where)
    d = os.path.expanduser(d)
    if not os.path.isdir(d):
        raise SetupError('[paths] freecad_dir / FREECAD_DIR points to %r, which does not exist. Fix the path in local.toml.' % d)
    for name in ('freecadcmd.exe', 'FreeCADCmd.exe', 'freecadcmd', 'FreeCADCmd'):
        p = os.path.join(d, 'bin', name)
        if os.path.isfile(p):
            return p
    raise SetupError('no bin/freecadcmd(.exe) under %r. [paths] freecad_dir must be the FreeCAD folder that holds bin/.' % d)


def result_path(exe, root=ROOT, environ=None):
    stage = setting('paths', 'cad_staging', 'CAD_STAGING', root, environ)
    windows_exe = exe.lower().endswith('.exe') and not sys.platform.startswith('win')
    if stage:
        stage = os.path.expanduser(stage)
        if not os.path.isdir(stage):
            raise SetupError('[paths] cad_staging / CAD_STAGING points to %r, which does not exist.' % stage)
        out = os.path.join(stage, 'freecad_check_result.txt')
    else:
        out = os.path.join(os.path.dirname(CHECK), 'freecad_check_result.txt')
    if windows_exe and not os.path.abspath(out).startswith('/mnt/'):
        raise SetupError('Windows FreeCAD from WSL: set [paths] cad_staging to a Windows folder (/mnt/<drive>/...) so the result '
                         'is not written into the WSL filesystem.')
    return out


def main():
    try:
        exe = find_freecadcmd()
        out = result_path(exe)
    except SetupError as e:
        print('freecad_check: ' + str(e), file=sys.stderr)
        return 2
    env = dict(os.environ)
    script = CHECK
    if exe.lower().endswith('.exe') and not sys.platform.startswith('win'):
        # Windows program: hand it Windows paths; copy the check next to the result so nothing reads from the WSL share.
        stage = os.path.dirname(out)
        script = os.path.join(stage, 'freecad_check.py')
        shutil.copyfile(CHECK, script)
        win = lambda p: subprocess.check_output(['wslpath', '-w', p], text=True).strip()  # noqa: E731
        env['FREECAD_CHECK_OUT'] = win(out)
        env['WSLENV'] = (env.get('WSLENV', '') + ':FREECAD_CHECK_OUT').lstrip(':')
        args = [exe, win(script)]
    else:
        env['FREECAD_CHECK_OUT'] = out
        args = [exe, script]
    if os.path.exists(out):
        os.remove(out)
    r = subprocess.run(args, env=env, capture_output=True, text=True, timeout=600)
    text = open(out).read().strip() if os.path.isfile(out) else ''
    if 'OK' not in text:
        print('freecad_check: FAIL (exit %s)\n%s\n%s' % (r.returncode, r.stdout[-2000:], r.stderr[-2000:]), file=sys.stderr)
        return 1
    print('freecad_check: %s  (%s)' % (text, out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
