"""AP242 assembly STEP with external part files. Read-back resolves Parts/*.stp."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
sys.path.insert(0, os.path.join(HERE, "..", "tools", "checks"))

from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox  # noqa: E402
from build123d import import_step  # noqa: E402

import release_structure as rs  # noqa: E402
from step_release import write_assembly  # noqa: E402


def test_two_part_assembly_round_trips_external_refs(tmp_path):
    ver = tmp_path / "revA"
    ver.mkdir()
    root = ver / "bracket.step"
    write_assembly(root, [
        ("leg", BRepPrimAPI_MakeBox(10.0, 20.0, 5.0).Shape()),
        ("plate", BRepPrimAPI_MakeBox(30.0, 30.0, 4.0).Shape()),
    ])
    leg, plate = ver / "Parts" / "leg.stp", ver / "Parts" / "plate.stp"
    assert leg.is_file() and plate.is_file()
    text = root.read_text(errors="replace")
    assert "Parts/leg.stp" in text and "Parts/plate.stp" in text
    for p in (root, leg, plate):
        assert "AP242" in p.read_text(errors="replace").split("DATA;", 1)[0]
    solids = list(import_step(str(root)).solids())
    assert sorted(round(s.volume, 1) for s in solids) == [1000.0, 3600.0]
    assert [round(s.bounding_box().min.Z, 3) for s in solids] == [0.0, 0.0]   # parts keep their placement
    assert rs.check_release(tmp_path) == []
