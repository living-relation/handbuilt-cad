"""tools/checks/release_structure.py: one solid per made part, maker models, STEP tree, stale rev paths."""
import os
import sys
from pathlib import Path

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
sys.path.insert(0, os.path.join(HERE, "..", "tools", "checks"))
import release_structure as rs  # noqa: E402


def _box(path, dx=10.0, dy=20.0, dz=5.0):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from step_release import write_shape
    write_shape(BRepPrimAPI_MakeBox(float(dx), float(dy), float(dz)).Shape(), Path(path))


def _two(path):
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Compound
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.gp import gp_Trsf, gp_Vec
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from step_release import write_shape
    comp = TopoDS_Compound()
    b = BRep_Builder()
    b.MakeCompound(comp)
    b.Add(comp, BRepPrimAPI_MakeBox(1.0, 1.0, 1.0).Shape())
    tr = gp_Trsf()
    tr.SetTranslation(gp_Vec(5, 0, 0))
    b.Add(comp, BRepBuilderAPI_Transform(BRepPrimAPI_MakeBox(2.0, 2.0, 2.0).Shape(), tr, True).Shape())
    write_shape(comp, Path(path))


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
    job = tmp_path / "job_1017"
    job.mkdir()
    _box(job / "leg-revA.step")
    assert rs.check_release(job) == []
    _two(job / "leg-revA.step")
    fails = rs.check_release(job)
    assert any("2 solids" in f for f in fails)


def test_embedded_assembly_does_not_count_as_external_refs(tmp_path):
    job = tmp_path / "job_1017"
    (job / "Parts").mkdir(parents=True)
    _assembly(job / "bracket-revB.step")
    _box(job / "Parts" / "leg-revC.stp")
    fails = rs.check_release(job)
    assert any("does not reference external STEP" in f for f in fails)


def test_unnamed_compound_does_not_match_parts_folder(tmp_path):
    job = tmp_path / "job_1017"
    (job / "Parts").mkdir(parents=True)
    _two(job / "bracket-revB.step")
    _box(job / "Parts" / "leg-revA.step")
    _box(job / "Parts" / "plate-revA.step", 8, 8, 8)
    fails = rs.check_release(job)
    assert any("does not reference external STEP" in f for f in fails)


def test_bought_part_needs_a_maker_file(tmp_path):
    job = tmp_path / "job_1017"
    job.mkdir()
    _box(job / "bracket-revA.step")
    card = job / "bracket-revA.md"
    card.write_text("# bracket / revA\n## Bought parts\n- hinge\n")
    assert any("no maker model" in f for f in rs.check_release(job))
    (job / "reference").mkdir()
    (job / "reference" / "hinge-maker.step").write_bytes(b"step")
    card.write_text("# bracket / revA\n## Bought parts\n- hinge: reference/hinge-maker.step\n")
    assert rs.check_release(job) == []
    (job / "reference" / "hinge-maker.step").write_bytes(b"")
    assert any("no maker model" in f for f in rs.check_release(job))


def test_older_rev_of_that_part_fails(tmp_path):
    job = tmp_path / "job_1017"
    (job / "Parts").mkdir(parents=True)
    _assembly(job / "bracket-revD.step")
    _box(job / "Parts" / "leg-revC.step")
    _box(job / "Parts" / "leg-revA.step")
    text = (job / "bracket-revD.step").read_text(errors="replace")
    text = text.replace("ENDSEC;", "/* 'Parts/leg-revA.step' */\nENDSEC;", 1)
    (job / "bracket-revD.step").write_text(text)
    fails = rs.check_release(job)
    assert any("leg newest is revC" in f for f in fails)


def test_fastener_file_must_be_named_in_the_card(tmp_path):
    job = tmp_path / "job_1017"
    (job / "Parts").mkdir(parents=True)
    _assembly(job / "bracket-revC.step")
    _box(job / "Parts" / "leg-revA.step")
    _box(job / "Parts" / "SHCS_M4.step", 4, 4, 4)
    fails = rs.check_release(job)
    assert any("does not reference external STEP" in f and "leg-revA.step" in f for f in fails)
    assert not any("SHCS_M4" in f and "does not reference" in f for f in fails)


def test_clerical_card_with_no_step_passes(tmp_path):
    job = tmp_path / "job_1017"
    job.mkdir()
    (job / "bracket-revD.01.md").write_text("drawings only\n")
    (job / "bracket-revD.01.pdf").write_bytes(b"%PDF")
    assert rs.check_release(job) == []


def test_f3d_and_other_model_formats_fail(tmp_path):
    job = tmp_path / "job_1017"
    job.mkdir()
    (job / "leg-revA.f3d").write_bytes(b"fusion")
    (job / "plate-revA.stl").write_bytes(b"mesh")
    fails = rs.check_release(job)
    assert any("leg-revA.f3d" in f and "STEP only" in f for f in fails)
    assert any("plate-revA.stl" in f and "STEP only" in f for f in fails)
    (job / "leg-revA.f3d").unlink()
    (job / "plate-revA.stl").unlink()
    _box(job / "leg-revA.step")
    (job / "leg-revA.pdf").write_bytes(b"%PDF")
    assert rs.check_release(job) == []


def test_duplicate_step_copies_fail(tmp_path):
    job = tmp_path / "job_1017"
    (job / "Parts").mkdir(parents=True)
    _box(job / "leg-revA.step")
    _box(job / "Parts" / "leg-revA.step")
    fails = rs.check_release(job)
    assert any("duplicate STEP" in f for f in fails)


def test_scripts_and_scans_are_refused(tmp_path):
    job = tmp_path / "job_1017"
    (job / "src").mkdir(parents=True)
    (job / "src" / "leg.py").write_text("print(1)\n")
    _box(job / "leg-revA.step")
    fails = rs.check_release(job)
    assert any("source file" in f or "src/" in f for f in fails)


def test_cli_exit_code(tmp_path):
    job = tmp_path / "job_1017"
    job.mkdir()
    _two(job / "arm-revA.step")
    assert rs.main([str(job)]) == 1
