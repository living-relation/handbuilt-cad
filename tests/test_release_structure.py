"""tools/checks/release_structure.py: version folders, AP242 STEP only, one solid per made part, external parts."""
import os
import sys
from pathlib import Path

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


def _embedded(path, names=("leg", "SHCS M4")):
    """One assembly STEP with every body embedded (no external files)."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.Interface import Interface_Static
    from OCP.STEPCAFControl import STEPCAFControl_Writer
    from OCP.STEPControl import STEPControl_Controller
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDocStd import TDocStd_Document
    from OCP.TopLoc import TopLoc_Location
    from OCP.XCAFApp import XCAFApp_Application
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    from OCP.gp import gp_Trsf, gp_Vec

    STEPControl_Controller.Init_s()
    Interface_Static.SetCVal_s("write.step.schema", "AP242DIS")
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))
    doc, = app.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    assy = st.NewShape()
    for i, name in enumerate(names):
        lab = st.AddShape(BRepPrimAPI_MakeBox(4.0 + i, 4.0, 4.0).Shape(), False)
        TDataStd_Name.Set_s(lab, TCollection_ExtendedString(name))
        moved = gp_Trsf()
        moved.SetTranslation(gp_Vec(30 * i, 0, 0))
        st.AddComponent(assy, lab, TopLoc_Location(moved))
    TDataStd_Name.Set_s(assy, TCollection_ExtendedString("bracket"))
    st.UpdateAssemblies()
    w = STEPCAFControl_Writer()
    assert w.Transfer(doc)
    assert w.Write(str(path))


def _release(ver, parts=(("leg", 10.0), ("plate", 30.0))):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from step_release import write_assembly
    ver.mkdir(parents=True, exist_ok=True)
    write_assembly(ver / "bracket.step", [(n, BRepPrimAPI_MakeBox(x, 20.0, 5.0).Shape()) for n, x in parts])


def test_one_solid_part_passes_and_fused_part_fails(tmp_path):
    ver = tmp_path / "revA"
    ver.mkdir()
    _box(ver / "leg.step")
    assert rs.check_release(tmp_path) == []
    _two(ver / "leg.step")
    assert any("has 2 solids" in f for f in rs.check_release(tmp_path))


def test_external_release_passes(tmp_path):
    _release(tmp_path / "revA")
    assert rs.check_release(tmp_path) == []
    assert rs.check_release(tmp_path / "revA") == []


def test_embedded_parts_fail_fasteners_may_stay(tmp_path):
    ver = tmp_path / "revA"
    ver.mkdir()
    _embedded(ver / "bracket.step", names=("leg", "plate", "SHCS M4"))
    assert any("has 2 solids besides fasteners" in f for f in rs.check_release(tmp_path))
    _embedded(ver / "bracket.step", names=("leg", "SHCS M4", "washer M4"))
    assert rs.check_release(tmp_path) == []


def test_missing_and_unused_parts_fail(tmp_path):
    ver = tmp_path / "revA"
    _release(ver)
    (ver / "Parts" / "plate.stp").unlink()
    _box(ver / "Parts" / "spare.stp")
    fails = rs.check_release(tmp_path)
    assert any("plate.stp, which is missing" in f for f in fails)
    assert any("Parts/spare.stp: no assembly references it" in f for f in fails)


def test_bought_part_needs_a_maker_file_and_may_be_multi_body(tmp_path):
    ver = tmp_path / "revA"
    _release(ver, parts=(("leg", 10.0),))
    (ver / "SUMMARY.md").write_text("# bracket / revA\n## Bought parts\n- hinge\n")
    assert any("no maker model" in f for f in rs.check_release(tmp_path))
    _two(ver / "Parts" / "hinge-maker.stp")
    (ver / "SUMMARY.md").write_text("# bracket / revA\n## Bought parts\n- hinge: Parts/hinge-maker.stp\n")
    fails = rs.check_release(tmp_path)
    assert not any("hinge-maker.stp: made part" in f or "no maker model" in f for f in fails)


def test_more_than_two_versions_fail(tmp_path):
    for v in ("revA", "revB", "revB.01"):
        (tmp_path / v).mkdir()
    assert rs.check_release(tmp_path) == []
    (tmp_path / "revC").mkdir()
    assert any("3 model versions" in f for f in rs.check_release(tmp_path))


def test_clerical_version_with_drawings_only_passes(tmp_path):
    ver = tmp_path / "revD.01"
    (ver / "drawings").mkdir(parents=True)
    (ver / "SUMMARY.md").write_text("drawings only\n")
    (ver / "drawings" / "bracket-revD.01.pdf").write_bytes(b"%PDF")
    assert rs.check_release(tmp_path) == []


def test_other_model_formats_fail_but_f3d_is_allowed(tmp_path):
    # The user's F7 b (2026-11-23): a Fusion .f3d may be filed beside its STEP when needed.
    ver = tmp_path / "revA"
    ver.mkdir()
    (ver / "leg.f3d").write_bytes(b"fusion")
    (ver / "plate.stl").write_bytes(b"mesh")
    fails = rs.check_release(tmp_path)
    assert not any("leg.f3d" in f for f in fails)
    assert any("plate.stl" in f and "STEP only" in f for f in fails)


def test_duplicate_step_copies_fail(tmp_path):
    ver = tmp_path / "revA"
    (ver / "Parts").mkdir(parents=True)
    _box(ver / "leg.step")
    _box(ver / "Parts" / "leg.stp")
    assert any("duplicate" in f for f in rs.check_release(tmp_path))


def test_scripts_scans_and_notes_are_refused(tmp_path):
    ver = tmp_path / "revA"
    (ver / "src").mkdir(parents=True)
    (ver / "src" / "leg.py").write_text("print(1)\n")
    (ver / "scan.ply").write_text("cloud")
    (ver / "notes.md").write_text("todo")
    (ver / "REVLOG.md").write_text("| Rev |")
    fails = rs.check_release(tmp_path)
    assert any("src/" in f for f in fails)
    assert any("scan.ply" in f and "scan" in f for f in fails)
    assert any("notes.md" in f for f in fails)
    assert not any(f.startswith("revA/REVLOG.md") for f in fails)


def test_ap214_header_fails(tmp_path):
    path = tmp_path / "leg.step"
    path.write_text("ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n")
    assert any("not AP242" in f for f in rs.check_release(tmp_path))


def test_cli_exit_code(tmp_path):
    ver = tmp_path / "revA"
    ver.mkdir()
    _two(ver / "arm.step")
    assert rs.main([str(tmp_path)]) == 1
