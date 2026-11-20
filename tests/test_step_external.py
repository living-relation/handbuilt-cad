"""AP242 assembly STEP with external part files. Read-back resolves Parts/*.stp."""
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
sys.path.insert(0, os.path.join(HERE, "..", "tools", "checks"))

from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox  # noqa: E402
from build123d import import_step  # noqa: E402

import release_structure as rs  # noqa: E402
from step_release import write_assembly  # noqa: E402


def test_two_part_assembly_round_trips_external_refs(tmp_path):
    root = tmp_path / "bracket-revA.step"
    write_assembly(root, [
        ("leg-revA", BRepPrimAPI_MakeBox(10.0, 20.0, 5.0).Shape()),
        ("plate-revA", BRepPrimAPI_MakeBox(30.0, 30.0, 4.0).Shape()),
    ])
    leg = tmp_path / "Parts" / "leg-revA.stp"
    plate = tmp_path / "Parts" / "plate-revA.stp"
    assert leg.is_file() and plate.is_file()
    text = root.read_text(errors="replace")
    assert "Parts/leg-revA.stp" in text and "Parts/plate-revA.stp" in text
    for p in (root, leg, plate):
        assert "AP242" in p.read_text(errors="replace").split("DATA;", 1)[0]
    solids = list(import_step(str(root)).solids())
    assert len(solids) == 2
    assert sorted(round(s.volume, 1) for s in solids) == [1000.0, 3600.0]
    assert rs.check_release(tmp_path) == []


def test_ap214_header_fails(tmp_path):
    path = tmp_path / "leg-revA.step"
    path.write_text("ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n")
    fails = rs.check_release(tmp_path)
    assert any("not AP242" in f for f in fails)
