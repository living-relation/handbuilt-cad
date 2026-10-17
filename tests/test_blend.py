"""pytest for tools/blend.py on generic geometry (about 2-4 min):

    .venv/bin/python -m pytest -q tests/test_blend.py   (from the repo root; tests/conftest.py sets the import path)
"""
import math, pytest
import blend_cases as bc
import blend as bl

def _run(case):
    A, B, r = bc.CASES[case]()
    logs = []
    res = bl.blend(A, B, r, log=lambda *a: logs.append(" ".join(map(str, a))))
    part, rep = bl.fuse_blend(A + B, res, log=lambda *a: logs.append(" ".join(map(str, a))))
    return dict(A=A, B=B, r=r, res=res, part=part, rep=rep, logs=logs)

@pytest.fixture(scope="module")
def straight(): return _run("straight")

@pytest.fixture(scope="module")
def curved(): return _run("curved")

@pytest.fixture(scope="module")
def small_round(): return _run("small_round")

def _common(d):
    rep = d["rep"]
    assert rep["single_valid_solid"], rep
    assert rep["valid"] and rep["solids"] == 1
    assert rep["volume_check"] == "PASS", (rep["added_mm3"], rep["expected_mm3"])
    assert 0.9 <= rep["ratio"] <= 1.1
    assert rep["added_mm3"] > 0
    assert rep["ok"]

def test_straight_root(straight):
    _common(straight); res = straight["res"]
    assert not res.skipped
    assert len(res.loops) == 4                                   # wall corners split the crease into 4 straight runs
    # flat wedge: added volume close to the exact (1 - pi/4) r^2 per mm on the straight stretches
    per_mm = (1 - math.pi / 4) * straight["r"] ** 2
    L = sum(l["length"] for l in res.loops)
    assert straight["rep"]["added_mm3"] == pytest.approx(per_mm * L, rel=0.1)
    # straight root: adaptive spacing stays coarse (no refinement needed)
    assert all(l["probes"] <= l["samples"] for l in res.loops)
    dev = bc.surface_deviation(straight["A"], straight["B"], straight["r"], res.pieces)
    assert dev["max_abs"] < 0.02, dev

def test_curved_root(curved):
    _common(curved); res = curved["res"]
    assert not res.skipped
    assert res.loops[0]["closed"]
    dev = bc.surface_deviation(curved["A"], curved["B"], curved["r"], res.pieces)
    assert dev["max_abs"] < 0.03, dev                            # within ~0.01 of the true rolling-ball surface + trim
    assert dev["tooth"] < 0.02, dev                              # no visible serration along the root

def test_curved_root_adaptive_beats_uniform(curved):
    """Uniform coarse ruled sections leave teeth; the adaptive ones put sections where the strip error is large."""
    A, B, r = curved["A"], curved["B"], curved["r"]
    coarse = bl.blend(A, B, r, step=2.0, adaptive=False, loft="ruled", log=lambda *a: None)
    fine = bl.blend(A, B, r, step=2.0, adaptive=True, chord_tol=0.005, loft="ruled", log=lambda *a: None)
    truth = bc.truth_centres(A, B, r)
    d0 = bc.surface_deviation(A, B, r, coarse.pieces, truth); d1 = bc.surface_deviation(A, B, r, fine.pieces, truth)
    assert d1["tooth"] < 0.5 * d0["tooth"], (d0, d1)
    assert fine.loops[0]["samples"] > coarse.loops[0]["samples"]

def test_root_crossing_small_round(small_round):
    _common(small_round); res = small_round["res"]
    # nothing may disappear silently: every skipped section is in res.skipped, the notes and the log, with a position
    for s in res.skipped:
        assert len(s["xyz"]) == 3 and s["reason"]
    nskip = sum(int(n.split(": ")[1].split()[0]) for n in res.notes if n.startswith("WARNING loop") and "skipped" in n)
    assert nskip == len(res.skipped) == small_round["rep"]["skipped_sections"]
    if res.skipped: assert any("WARNING" in l for l in small_round["logs"])
    # the blend still runs over the step (sections on both sides of the r1 rounds, x < 0 and x > 0)
    xs = [s["q"].X for s in res.samples]
    assert min(xs) < -5 and max(xs) > 5

def test_failed_sections_are_reported_and_split(monkeypatch):
    """Force failures in a stretch: short gaps are bridged, a long gap splits the loft; all are listed with positions."""
    A, B, r = bc.curved_case()
    orig = bl._Sections.one
    def flaky(self, u, rr):
        uu = bl._uw(u)
        if 0.30 < uu < 0.40 or abs(uu - 0.7) < 0.004: return None, None, "forced failure (test)"
        return orig(self, u, rr)
    monkeypatch.setattr(bl._Sections, "one", flaky)
    logs = []
    res = bl.blend(A, B, r, adaptive=False, loft="ruled", log=lambda *a: logs.append(" ".join(map(str, a))))
    assert res.skipped and all(s["reason"].startswith("forced") or "probe" in s["reason"] for s in res.skipped)
    assert all(0.30 < s["u"] < 0.40 or abs(s["u"] - 0.7) < 0.004 for s in res.skipped)
    assert len(res.loops) == 1 and not res.loops[0]["closed"]   # the wide gap opened the closed loop into one run
    assert any("WARNING" in l and "skipped" in l for l in logs)
    assert any("1 split" in n for n in res.notes)

def test_strip_deviation_on_circle():
    """Ruled strip between two arc points on a ring vs the true torus: sagitta s^2 / (8 R)."""
    from build123d import Vector
    R, r, a = 20.0, 3.0, math.radians(4)
    def smp(ang):
        c = Vector(R * math.cos(ang), R * math.sin(ang), 0)
        out = Vector(math.cos(ang), math.sin(ang), 0)
        return dict(c=c, nA=out * -1, nB=Vector(0, 0, 1), r=r)
    d = bl.strip_deviation(smp(0), smp(a), smp(a / 2), fs=(0.0,))
    Rp = R + r
    assert d == pytest.approx(Rp * (1 - math.cos(a / 2)), rel=0.05)


def test_failed_refinement_probe_not_counted_as_skipped(monkeypatch):
    """A failed adaptive-refinement probe must not inflate skipped_sections / warnings."""
    A, B, r = bc.curved_case()
    orig_refine = bl._refine

    def wrap_refine(S, ok, bad, closed, L, tol, step_min, max_sections, tag, res):
        def one_fail(u, rr):
            return None, None, "forced refinement probe failure (test)"
        S.one = one_fail
        return orig_refine(S, ok, bad, closed, L, tol, step_min, max_sections, tag, res)

    monkeypatch.setattr(bl, "_refine", wrap_refine)
    res = bl.blend(A, B, r, adaptive=True, loft="ruled", log=lambda *a: None)
    assert any(l.get("probes", 0) > 0 for l in res.loops), "refine should have probed"
    assert not any("refinement probe" in s.get("reason", "") or "forced refinement" in s.get("reason", "")
                   for s in res.skipped), res.skipped


def test_fuse_blend_zero_expected_no_crash():
    """fuse_blend must not divide by zero when expected_mm3 is 0 and a smooth fallback exists."""
    from build123d import Box, Location
    base = Box(20, 20, 4, align=(bc.C, bc.C, bc.MAX))
    bump = Box(4, 4, 2, align=(bc.C, bc.C, bc.MIN)).moved(Location((0, 0, 0)))
    # Identical ruled fallback so the redo path is entered when expected volume is missing.
    res = bl.BlendResult(pieces=[bump], fallback=[bump], expected_mm3=0.0)
    part, rep = bl.fuse_blend(base, res, log=lambda *a: None)
    assert rep["expected_mm3"] == 0.0
    assert rep["volume_check"] == "no expected volume"
    assert rep["ratio"] is None
