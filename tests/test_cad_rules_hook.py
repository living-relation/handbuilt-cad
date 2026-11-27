"""The SessionStart CAD rules pointer (hooks/cad_rules_pointer.py, the user's G9 a 2026-11-25)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / 'hooks' / 'cad_rules_pointer.py'


def run(folder=None, payload=None):
    args = [sys.executable, str(HOOK)] + ([str(folder)] if folder else [])
    p = subprocess.run(args, input=json.dumps(payload) if payload else '', capture_output=True, text=True, timeout=30)
    assert p.returncode == 0
    return json.loads(p.stdout)['hookSpecificOutput']


def test_cad_folder_gets_full_pointer(tmp_path):
    (tmp_path / 'cad' / 'box' / 'src').mkdir(parents=True)
    (tmp_path / 'cad' / 'box' / 'MADE-WITH.md').write_text('x')
    out = run(tmp_path)
    assert out['hookEventName'] == 'SessionStart'
    assert 'this folder shows CAD work' in out['additionalContext']
    assert 'AGENTS.md' in out['additionalContext'] and '22 fasteners' in out['additionalContext']


def test_model_file_counts(tmp_path):
    (tmp_path / 'part.step').write_text('x')
    assert 'shows CAD work' in run(tmp_path)['additionalContext']


def test_plain_folder_gets_short_line(tmp_path):
    (tmp_path / 'README.md').write_text('x')
    ctx = run(tmp_path)['additionalContext']
    assert ctx.startswith('HANDBUILT-CAD RULES: if this session turns to CAD work')


def test_cwd_from_payload(tmp_path):
    (tmp_path / 'models').mkdir()
    assert 'shows CAD work' in run(payload={'cwd': str(tmp_path), 'hook_event_name': 'SessionStart'})['additionalContext']


def test_skipped_dirs_do_not_count(tmp_path):
    (tmp_path / '.git' / 'x').mkdir(parents=True)
    (tmp_path / '.git' / 'x' / 'a.step').write_text('x')
    assert 'shows CAD work' not in run(tmp_path)['additionalContext']


def test_hooks_json_runs_the_script():
    cfg = json.loads((ROOT / 'hooks' / 'hooks.json').read_text())
    cmds = [h['command'] for g in cfg['hooks']['SessionStart'] for h in g['hooks']]
    assert any('cad_rules_pointer.py' in c and '${CLAUDE_PLUGIN_ROOT}' in c for c in cmds)
