"""tools/checks/release_structure.py: one solid per made part, maker models, STEP tree, stale rev paths."""
import os
import sys
from pathlib import Path

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools", "checks"))
import release_structure as rs  # noqa: E402
from build123d import Box, Compound, Pos, export_step  # noqa: E402


def _box(path, dx=10.0, dy=20.0, dz=5.0):
    export_step(Box(dx, dy, dz), str(path))


def _two(path):
    export_step(Compound(children=[Box(1, 1, 1), Pos(5, 0, 0) * Box(2, 2, 2)]), str(path))


def _assembly(path):
    """One assembly STEP: a part named leg and a fastener body named SHCS M4."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.STEPCAFControl import STEPCAFControl_Writer
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDocStd import TDocStd_Document
    from OCP.TopLoc import TopLoc_Location
    from OCP.XCAFApp import XCAFApp_Application
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    from OCP.gp import gp_Trsf, gp_Vec

    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))
    doc, = app.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    leg = st.AddShape(BRepPrimAPI_MakeBox(10.0, 20.0, 5.0).Shape(), False)
    screw = st.AddShape(BRepPrimAPI_MakeBox(4.0, 4.0, 4.0).Shape(), False)
    TDataStd_Name.Set_s(leg, TCollection_ExtendedString("leg"))
    TDataStd_Name.Set_s(screw, TCollection_ExtendedString("SHCS M4"))
    assy = st.NewShape()
    st.AddComponent(assy, leg, TopLoc_Location(gp_Trsf()))
    moved = gp_Trsf()
    moved.SetTranslation(gp_Vec(30, 0, 0))
    st.AddComponent(assy, screw, TopLoc_Location(moved))
    TDataStd_Name.Set_s(assy, TCollection_ExtendedString("bracket"))
    st.UpdateAssemblies()
    w = STEPCAFControl_Writer()
    assert w.Transfer(doc)
    assert w.Write(str(path))


def test_one_solid_part_passes_and_fused_part_fails(tmp_path):
    rev = tmp_path / "revA"
    rev.mkdir()
    _box(rev / "leg.step")
    assert rs.check_release(rev) == []
    _two(rev / "leg.step")
    fails = rs.check_release(rev)
    assert any("2 solids" in f for f in fails)


def test_assembly_tree_matches_parts_and_ignores_fastener_body(tmp_path):
    rev = tmp_path / "revB"
    (rev / "Parts").mkdir(parents=True)
    _assembly(rev / "bracket.step")
    _box(rev / "Parts" / "leg.step")
    assert rs.check_release(rev) == []


def test_unnamed_compound_does_not_match_parts_folder(tmp_path):
    rev = tmp_path / "revB"
    (rev / "Parts").mkdir(parents=True)
    _two(rev / "bracket.step")
    _box(rev / "Parts" / "leg.step")
    _box(rev / "Parts" / "plate.step", 8, 8, 8)
    fails = rs.check_release(rev)
    assert any("does not match Parts" in f for f in fails)


def test_bought_part_needs_a_maker_file(tmp_path):
    rev = tmp_path / "revA"
    rev.mkdir()
    _box(rev / "hinge.step")
    (rev / "SUMMARY.md").write_text("# x\n## Bought parts\n- hinge\n")
    assert any("no maker model" in f for f in rs.check_release(rev))
    (rev / "reference").mkdir()
    (rev / "reference" / "hinge-maker.step").write_bytes(b"step")
    (rev / "SUMMARY.md").write_text("# x\n## Bought parts\n- hinge: reference/hinge-maker.step\n")
    assert rs.check_release(rev) == []
    (rev / "reference" / "hinge-maker.step").write_bytes(b"")
    assert any("no maker model" in f for f in rs.check_release(rev))


def test_older_rev_path_in_the_step_fails(tmp_path):
    rev = tmp_path / "revD"
    (rev / "Parts").mkdir(parents=True)
    _assembly(rev / "bracket.step")
    _box(rev / "Parts" / "leg.step")
    text = (rev / "bracket.step").read_text(errors="replace")
    text = text.replace("ENDSEC;", "/* '../revC/Parts/leg.step' */\nENDSEC;", 1)
    (rev / "bracket.step").write_text(text)
    fails = rs.check_release(rev)
    assert any("older than revD" in f for f in fails)


def test_fastener_file_must_be_named_in_summary(tmp_path):
    rev = tmp_path / "revC"
    (rev / "Parts").mkdir(parents=True)
    _assembly(rev / "bracket.step")
    _box(rev / "Parts" / "leg.step")
    _box(rev / "Parts" / "SHCS_M4.step", 4, 4, 4)
    fails = rs.check_release(rev)
    assert any("separate files" in f for f in fails)
    (rev / "SUMMARY.md").write_text("SR fastener bodies are separate files in this STEP copy.\n")
    assert rs.check_release(rev) == []


def test_clerical_rev_with_no_step_passes(tmp_path):
    rev = tmp_path / "revD.01"
    rev.mkdir()
    (rev / "SUMMARY.md").write_text("drawings only\n")
    assert rs.check_release(rev) == []


def test_cli_exit_code(tmp_path):
    rev = tmp_path / "revA"
    rev.mkdir()
    _two(rev / "arm.step")
    assert rs.main([str(rev)]) == 1
