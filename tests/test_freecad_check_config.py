"""run_freecad_check finds FreeCAD from local.toml / env and fails clearly when it can't (no FreeCAD needed)."""
import importlib.util, os, pytest

_p = os.path.join(os.path.dirname(__file__), '..', 'sim', 'smoke', 'run_freecad_check.py')
_s = importlib.util.spec_from_file_location('run_freecad_check', _p)
R = importlib.util.module_from_spec(_s)
_s.loader.exec_module(R)


def _fake_freecad(tmp_path, name='freecadcmd'):
    d = tmp_path / 'FreeCAD'
    (d / 'bin').mkdir(parents=True)
    (d / 'bin' / name).write_text('')
    return d


def test_missing_local_toml_says_run_setup(tmp_path):
    with pytest.raises(R.SetupError, match='run setup'):
        R.find_freecadcmd(str(tmp_path), environ={})


def test_empty_key_is_a_clear_error(tmp_path):
    (tmp_path / 'local.toml').write_text('[paths]\nfreecad_dir = ""\n')
    with pytest.raises(R.SetupError, match='freecad_dir'):
        R.find_freecadcmd(str(tmp_path), environ={})


def test_bad_path_is_a_clear_error(tmp_path):
    (tmp_path / 'local.toml').write_text('[paths]\nfreecad_dir = "%s"\n' % (tmp_path / 'nope').as_posix())
    with pytest.raises(R.SetupError, match='does not exist'):
        R.find_freecadcmd(str(tmp_path), environ={})


def test_local_toml_and_env_override(tmp_path):
    d = _fake_freecad(tmp_path)
    (tmp_path / 'local.toml').write_text('[paths]\nfreecad_dir = "%s"\n' % d.as_posix())
    assert R.find_freecadcmd(str(tmp_path), environ={}).endswith('freecadcmd')
    d2 = _fake_freecad(tmp_path / 'other', 'freecadcmd.exe')
    assert R.find_freecadcmd(str(tmp_path), environ={'FREECAD_DIR': str(d2)}).endswith('freecadcmd.exe')


def test_windows_exe_from_wsl_needs_windows_staging(tmp_path, monkeypatch):
    monkeypatch.setattr(R.sys, 'platform', 'linux')
    with pytest.raises(R.SetupError, match='cad_staging'):
        R.result_path('/mnt/c/FreeCAD/bin/freecadcmd.exe', str(tmp_path), environ={'CAD_STAGING': str(tmp_path)})
