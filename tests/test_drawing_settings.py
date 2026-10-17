"""Title-block project / drawn-by come from the spec, env or local.toml [drawing], with neutral defaults."""
import importlib.util, os

_p = os.path.join(os.path.dirname(__file__), '..', 'drawing', 'settings.py')
_s = importlib.util.spec_from_file_location('drawing_settings', _p)
S = importlib.util.module_from_spec(_s)
_s.loader.exec_module(S)


def test_neutral_defaults_without_local_toml(tmp_path):
    assert S.title_defaults(str(tmp_path), environ={}) == {'project': 'PROJECT', 'drawn': '-'}


def test_local_toml_then_env(tmp_path):
    (tmp_path / 'local.toml').write_text('[drawing]\nproject = "ACME RIG"\ndrawn = "JD"\n')
    assert S.title_defaults(str(tmp_path), environ={}) == {'project': 'ACME RIG', 'drawn': 'JD'}
    d = S.title_defaults(str(tmp_path), environ={'DRAWING_DRAWN': 'bot'})
    assert d == {'project': 'ACME RIG', 'drawn': 'bot'}


def test_spec_values_win(tmp_path):
    (tmp_path / 'local.toml').write_text('[drawing]\nproject = "ACME RIG"\n')
    i = S.title_info({'title': 'T', 'project': 'JOB X', 'drawn': None}, str(tmp_path), environ={})
    assert i['project'] == 'JOB X' and i['drawn'] == '-' and i['title'] == 'T'


def test_engine_has_no_hardcoded_names():
    root = os.path.join(os.path.dirname(__file__), '..', 'drawing')
    for f in ('dwg.py', 'part.py', 'asm.py'):
        src = open(os.path.join(root, f), encoding='utf-8').read()
        assert 'SteveCAD' not in src and 'ST185' not in src, f
