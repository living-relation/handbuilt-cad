"""Drawing initials rule: DRAWN = Rev A BY, BY = the requester, never an agent / tool name, never guessed."""
import importlib.util, io, os, sys
import pytest

_d = os.path.join(os.path.dirname(__file__), '..', 'drawing')
sys.path.insert(0, _d)
import settings as S  # noqa: E402
import revs as R  # noqa: E402


class Tty(io.StringIO):
    def isatty(self):
        return True


def test_env_wins_then_file(tmp_path):
    (tmp_path / '.drawing-initials').write_text('dg\n')
    assert S.requester_initials(environ={}, home=str(tmp_path), windows_homes=[]) == 'DG'
    assert S.requester_initials(environ={'DRAWING_INITIALS': 'jd'}, home=str(tmp_path), windows_homes=[]) == 'JD'


def test_wsl_windows_profile_fallback(tmp_path):
    w = tmp_path / 'win'; w.mkdir(); (w / '.drawing-initials').write_text('DG\n')
    assert S.requester_initials(environ={}, home=str(tmp_path / 'empty'), windows_homes=[str(w)]) == 'DG'
    w2 = tmp_path / 'win2'; w2.mkdir(); (w2 / '.drawing-initials').write_text('JD\n')
    with pytest.raises(S.InitialsMissing):          # two different people on the Windows side: do not pick one
        S.requester_initials(environ={}, home=str(tmp_path / 'empty'), windows_homes=[str(w), str(w2)],
                             stdin=io.StringIO(), stdout=io.StringIO())


def test_missing_without_terminal_stops(tmp_path):
    with pytest.raises(S.InitialsMissing) as e:
        S.requester_initials(environ={}, home=str(tmp_path), windows_homes=[], stdin=io.StringIO(), stdout=io.StringIO())
    assert 'Agents must not guess' in str(e.value)
    assert not (tmp_path / '.drawing-initials').exists()


def test_missing_with_terminal_prompts_and_saves(tmp_path):
    answers = iter(['Claude', 'x', 'dg'])            # an agent name and junk are refused, then a person
    out = Tty()
    got = S.requester_initials(environ={}, home=str(tmp_path), windows_homes=[], stdin=Tty(), stdout=out,
                               ask=lambda _p: next(answers))
    assert got == 'DG' and (tmp_path / '.drawing-initials').read_text().strip() == 'DG'
    assert 'agent / tool' in out.getvalue()


@pytest.mark.parametrize('bad', ['', ' ', 'Claude', 'SteveCAD', 'Grok', 'Grok Bot', 'unknown', 'Fairsolid', 'SC', 'D', 'DGDGD', 'D1'])
def test_bad_initials_refused(bad):
    assert S.bad_initials(bad)
    with pytest.raises(ValueError):
        S.check_initials(bad)


def test_good_initials():
    assert S.check_initials(' dg ') == 'DG'


def test_add_release_default_is_requester_and_refuses_agents(tmp_path, monkeypatch):
    monkeypatch.setenv('DRAWING_INITIALS', 'DG')
    p = str(tmp_path / 'REVLOG.md')
    R.add_release(p, 'A', 'x', date='2026-10-19')
    assert R.read_revlog(p)[0].by == 'DG'
    with pytest.raises(ValueError):
        R.add_release(p, 'B', 'x', 'Claude')


def test_drawn_by_is_rev_a_and_problems():
    e = [R.RevEntry('A', 'Initial', 'DG', '01/10/26'), R.RevEntry('B', 'b', 'JD', '02/10/26')]
    assert R.drawn_by(e) == 'DG' and R.initials_problems(e) == []
    e2 = [R.RevEntry('A', 'Initial', 'Claude', '01/10/26'), R.RevEntry('B', 'b', '', '02/10/26')]
    assert len(R.initials_problems(e2)) == 2
    assert R.initials_problems([R.RevEntry('B', 'b', 'DG', '02/10/26')]) == ['no Rev A row, so DRAWN is unknown']
