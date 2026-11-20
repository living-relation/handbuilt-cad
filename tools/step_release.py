#!/usr/bin/env python3
"""Write a release assembly: one AP242 STEP that references part STEPs in Parts/.

OCCT's multifile writer (STEPCAFControl_Writer.Transfer theIsMulti) writes
AP242 external references. It first writes the part files as AP214; this
module rewrites those part files as AP242. Re-reading the root STEP resolves
the Parts/ files (build123d import_step).

    .venv/bin/python tools/step_release.py bracket.step leg.brep plate.brep

The part arguments are existing STEP files. Names become Parts/<stem>.stp.
Fusion's own STEP export is unverified and may bundle parts into one file;
convert that to this layout before filing.
"""
from __future__ import annotations

import sys
from pathlib import Path

from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Controller, STEPControl_Reader, STEPControl_Writer
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.gp import gp_Trsf

SCHEMA = "AP242DIS"


class StepReleaseError(RuntimeError):
    pass


def use_ap242() -> None:
    STEPControl_Controller.Init_s()
    if not Interface_Static.SetCVal_s("write.step.schema", SCHEMA):
        raise StepReleaseError("OCCT rejected write.step.schema AP242DIS")


def _wrapped(shape):
    return getattr(shape, "wrapped", shape)


def read_shape(path: Path):
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise StepReleaseError(f"cannot read {path}")
    reader.TransferRoots()
    return reader.OneShape()


def write_shape(shape, path: Path) -> None:
    """One solid (or compound) as a single AP242 STEP."""
    use_ap242()
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = STEPControl_Writer()
    if not writer.Transfer(_wrapped(shape), STEPControl_AsIs):
        raise StepReleaseError(f"cannot transfer {path.name}")
    if writer.Write(str(path)) != IFSelect_RetDone:
        raise StepReleaseError(f"cannot write {path}")


def write_assembly(root: Path, parts: list[tuple[str, object]]) -> list[Path]:
    """Write root AP242 STEP plus Parts/<stem>.stp for each (stem, shape).

    Stems are the external file names. Shapes may be OCCT shapes or build123d
    shapes. Part files are rewritten to AP242 after OCCT's multifile pass.
    """
    if len(parts) < 1:
        raise StepReleaseError("an assembly needs at least one external part")
    root = Path(root)
    root.parent.mkdir(parents=True, exist_ok=True)
    (root.parent / "Parts").mkdir(exist_ok=True)
    use_ap242()

    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))
    doc, = app.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    labels = []
    for stem, shape in parts:
        lab = tool.AddShape(_wrapped(shape), False)
        TDataStd_Name.Set_s(lab, TCollection_ExtendedString(stem))
        labels.append(lab)
    assembly = tool.NewShape()
    TDataStd_Name.Set_s(assembly, TCollection_ExtendedString(root.stem))
    for lab in labels:
        # Identity location: each part keeps the placement its shape already has.
        tool.AddComponent(assembly, lab, TopLoc_Location(gp_Trsf()))
    tool.UpdateAssemblies()

    writer = STEPCAFControl_Writer()
    if not writer.Transfer(doc, STEPControl_AsIs, "Parts/"):
        raise StepReleaseError("assembly transfer failed")
    if writer.Write(str(root)) != IFSelect_RetDone:
        raise StepReleaseError(f"cannot write {root} (Parts/ must exist)")

    written = []
    for stem, shape in parts:
        path = root.parent / "Parts" / f"{stem}.stp"
        if not path.is_file():
            raise StepReleaseError(f"writer did not emit {path}")
        write_shape(shape, path)  # replace the AP214 extern file with AP242
        written.append(path)
    return written


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        print("usage: step_release.py <assembly.step> <part.step> [<part.step> ...]", file=sys.stderr)
        return 2
    root = Path(args[0])
    parts = [(Path(p).stem, read_shape(Path(p))) for p in args[1:]]
    try:
        written = write_assembly(root, parts)
    except StepReleaseError as e:
        print(f"step_release.py: {e}", file=sys.stderr)
        return 1
    print(root)
    for p in written:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
