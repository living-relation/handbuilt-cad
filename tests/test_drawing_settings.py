"""Title-block project comes from the spec, env or local.toml [drawing], with a neutral default. DRAWN is never defaulted here."""
import importlib.util, os

_p = os.path.join(os.path.dirname(__file__), '..', 'drawing', 'settings.py')
_s = importlib.util.spec_from_file_location('drawing_settings', _p)
S = importlib.util.module_from_spec(_s)
_s.loader.exec_module(S)


def test_neutral_defaults_without_local_toml(tmp_path):
    assert S.title_defaults(str(tmp_path), environ={}) == {'project': 'PROJECT'}


def test_local_toml_then_env(tmp_path):
    (tmp_path / 'local.toml').write_text('[drawing]\nproject = "ACME RIG"\n')
    assert S.title_defaults(str(tmp_path), environ={}) == {'project': 'ACME RIG'}
    d = S.title_defaults(str(tmp_path), environ={'DRAWING_PROJECT': 'OTHER'})
    assert d == {'project': 'OTHER'}


def test_spec_values_win(tmp_path):
    (tmp_path / 'local.toml').write_text('[drawing]\nproject = "ACME RIG"\n')
    i = S.title_info({'title': 'T', 'project': 'JOB X', 'drawn': None}, str(tmp_path), environ={})
    assert i['project'] == 'JOB X' and 'drawn' not in i or not i['drawn'] and i['title'] == 'T'


def test_engine_has_no_hardcoded_names():
    root = os.path.join(os.path.dirname(__file__), '..', 'drawing')
    for f in ('dwg.py', 'part.py', 'asm.py'):
        src = open(os.path.join(root, f), encoding='utf-8').read()
        assert 'SteveCAD' not in src and 'ST185' not in src, f
