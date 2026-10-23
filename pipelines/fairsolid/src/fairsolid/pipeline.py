"""Orchestration: scan file in, parametric STEP out.

The pipeline is split at the one point that genuinely needs a human. Stage 20
can rank orientations but cannot know which one the user considers "the
bottom", so `prepare()` stops there and renders the options, and `finish()`
carries on once a choice exists.

Everything is written into a run directory and every stage is skipped if its
output is already present and newer than its input, so answering the
orientation question does not re-run the 60-second Poisson reconstruction.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from .subproc import StageError, run_module


@dataclass
class Run:
    """A single scan's working directory."""

    root: Path

    @property
    def scan(self) -> Path:
        """The copied source scan, keeping its ORIGINAL extension.

        Hard-coding .stl here silently renamed every .ply/.obj/.xyz input,
        and loaders dispatch on extension - a PLY copied to 00_scan.stl is
        parsed as ASCII STL and dies somewhere unhelpful.
        """
        recorded = self.state().get("scan_suffix")
        if recorded:
            return self.root / f"00_scan{recorded}"
        hits = sorted(self.root.glob("00_scan.*"))
        return hits[0] if hits else self.root / "00_scan.stl"
    @property
    def clean(self) -> Path: return self.root / "10_clean.ply"
    @property
    def ideal(self) -> Path: return self.root / "15_ideal.ply"

    @property
    def modelling(self) -> Path:
        """The mesh everything downstream measures and reconstructs from.

        The idealised mesh when stage 15 ran, otherwise the cleaned one. A
        textured cast surface is a poor thing to model from: the roughness was
        never part of the design, and carrying it forward forces every
        downstream tolerance to be loosened to accommodate it.
        """
        return self.ideal if self.ideal.exists() else self.clean
    @property
    def frame(self) -> Path: return self.root / "20_frame.json"
    @property
    def previews(self) -> Path: return self.root / "20_previews"
    @property
    def step_param(self) -> Path: return self.root / "50_part.step"
    @property
    def step_faceted(self) -> Path: return self.root / "80_part_faceted.step"
    @property
    def fit_report(self) -> Path: return self.root / "30_fit.json"
    @property
    def review(self) -> Path:
        """Pictures of anything that failed or came out marginal."""
        return self.root / "review"
    @property
    def state_file(self) -> Path: return self.root / "state.json"

    def state(self) -> dict:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {}

    def save(self, **kw) -> dict:
        st = self.state()
        st.update(kw)
        self.state_file.write_text(json.dumps(st, indent=2))
        return st


def _clip_error(exc: Exception, limit: int = 4000) -> str:
    """Error text for state.json, keeping the END where the traceback is.

    Keeping the first 2000 characters stored the stage's header and a run of
    deprecation warnings, and cut off the exception that actually killed it -
    the pedal adapter run recorded nothing but warnings for its crash.
    """
    text = str(exc)
    if len(text) <= limit:
        return text
    head = text.splitlines()[0] if text else ""
    return f"{head}\n...[{len(text) - limit} chars cut]...\n{text[-limit:]}"


def _fresh(out: Path, src: Path) -> bool:
    """True when `out` already reflects `src` and can be reused."""
    return out.exists() and src.exists() and out.stat().st_mtime >= src.stat().st_mtime


def prepare(
    scan_path: Path,
    run_dir: Path,
    *,
    target_faces: int = 200_000,
    poisson_depth: int = 10,
    idealize: bool = True,
    smooth_iters: int = 0,
    texture_mm: float | None = None,
    force: bool = False,
) -> dict:
    """Ingest, sanitise, measure, and render the orientation options.

    Stops before committing to a frame. Returns the preview paths and the
    measured features so a human (or Claude) can choose.
    """
    from .stages import s00_ingest

    run = Run(run_dir)
    run.root.mkdir(parents=True, exist_ok=True)

    scan_path = Path(scan_path)
    run.save(scan_suffix=scan_path.suffix.lower())
    if force or not _fresh(run.scan, scan_path):
        shutil.copy2(scan_path, run.scan)

    obj = s00_ingest.load(run.scan)
    info = s00_ingest.describe(obj)

    if force or not _fresh(run.clean, run.scan):
        clean = run_module("fairsolid.stages.s10_sanitize", [
            str(run.scan), str(run.clean),
            "--target-faces", str(target_faces),
            "--poisson-depth", str(poisson_depth),
        ])
    else:
        clean = {"output": str(run.clean), "cached": True}

    ideal = None
    if idealize:
        args = [str(run.clean), str(run.ideal),
                "--smooth-iters", str(smooth_iters)]
        if texture_mm is not None:
            args += ["--texture-mm", str(texture_mm)]
        ideal = run_module("fairsolid.stages.s15_idealize", args)
    elif run.ideal.exists():
        run.ideal.unlink()

    frame = run_module("fairsolid.stages.s20_frame", [
        str(run.modelling), str(run.frame),
        "--choice", "0", "--previews", str(run.previews),
    ])

    return run.save(
        source=str(scan_path), stage="prepared",
        ingest=info, sanitize=clean, idealize=ideal, frame=frame,
    )


def finish(
    run_dir: Path,
    *,
    choice: int = 0,
    tol: float = 0.15,
    faceted: bool = True,
    facet_budget: int = 8_000,
) -> dict:
    """Commit to an orientation, reconstruct, export, and grade the result."""
    run = Run(run_dir)
    if not run.clean.exists():
        raise FileNotFoundError(f"run {run_dir} not prepared yet")
    mesh = run.modelling

    frame = run_module("fairsolid.stages.s20_frame", [
        str(mesh), str(run.frame),
        "--choice", str(choice), "--previews", str(run.previews),
    ])

    out: dict = {"stage": "finished", "choice": choice, "frame": frame}

    # The parametric route is the deliverable, but it assumes a prismatic
    # part. Record why it failed rather than losing the run - the faceted
    # export below still produces a usable solid body.
    try:
        recon = run_module("fairsolid.stages.s50_reconstruct", [
            str(mesh), str(run.frame), str(run.step_param),
        ])
        out["reconstruct"] = recon
        # Deviation is measured against the CLEANED scan, never the idealised
        # one. Grading a model against a mesh we already smoothed to match it
        # would be marking our own homework.
        dev = run_module("fairsolid.stages.s70_deviate", [
            str(run.step_param), str(run.clean), str(run.frame),
            "--tol", str(tol),
        ])
        out["deviation"] = dev
        if dev["verdict"] != "PASS":
            out.update(_review_step(run, run.step_param, tol, "50", dev["verdict"]))
        # Only promote the parametric result if it actually matches the scan.
        # Previously `primary` was set whenever reconstruct did not THROW, so
        # a FAIL verdict still shipped: on a real casting that delivered a
        # 7%-accurate sliver while reporting success. Not raising is not the
        # same as being right.
        if dev["verdict"] in ("PASS", "MARGINAL"):
            out["primary"] = str(run.step_param)
        else:
            out["rejected_parametric"] = (
                f"verdict {dev['verdict']}: only "
                f"{dev['fraction_within_tol'] * 100:.1f}% of the surface within "
                f"{dev['tolerance_mm']} mm (median {dev['median_mm']:.3f} mm)"
            )
    except Exception as exc:
        out["reconstruct_error"] = _clip_error(exc)

    if faceted or "primary" not in out:
        fac = run_module("fairsolid.stages.s80_export", [
            str(mesh), str(run.frame), str(run.step_faceted),
            "--faces", str(facet_budget),
        ])
        out["faceted"] = fac
        if fac.get("fragment_warning"):
            out["faceted_warning"] = (
                f"sewn solid spans only {fac['size_ratio'] * 100:.0f}% of the "
                f"input in its smallest dimension across {fac.get('n_shells')} "
                f"shells - likely a fragment, not the whole part"
            )
            rv = _review_step(run, run.step_faceted, tol, "80", "FRAGMENT")
            out["review_faceted"] = rv.get("review", rv.get("review_error"))
        out.setdefault("primary", str(run.step_faceted))

    return run.save(**out)


def _review_step(run: Run, step: Path, tol: float, tag: str, verdict: str) -> dict:
    """Render pictures of a STEP that did not pass (the user's standing request).

    Never allowed to sink the run: a failure to draw is recorded, not raised.
    """
    try:
        rv = run_module("fairsolid.stages.s75_review", [
            str(step), str(run.clean), str(run.frame), str(run.review),
            "--tol", str(tol), "--tag", tag, "--verdict", verdict,
        ])
        return {"review": rv["images"]}
    except Exception as exc:
        return {"review_error": _clip_error(exc)}


def review(run_dir: Path, *, tol: float | None = None) -> dict:
    """Pictures for an existing run's reconstruction, after the fact."""
    run = Run(run_dir)
    st = run.state()
    dev = st.get("deviation", {})
    tol = tol if tol is not None else dev.get("tolerance_mm", 0.15)
    if not run.step_param.exists():
        raise FileNotFoundError(f"no {run.step_param.name} in {run_dir}")
    out = _review_step(run, run.step_param, tol, "50", dev.get("verdict", ""))
    if "review_error" in out:
        raise RuntimeError(out["review_error"])
    run.save(review=out["review"])
    return out


class FitStopped(RuntimeError):
    """Stage 30's overall size check stopped the run."""


def fit(run_dir: Path, *, tol: float | None = None, units: str = "auto") -> dict:
    """Stage 30: area map, least-squares fits, snapping, size check, report.

    Runs after orientation (needs 20_frame.json) and measures only - no
    trimming or knitting. The unit setting picks the hole-size table and
    nothing else. Raises FitStopped when the size check fails; the report
    and review pictures are written first.
    """
    run = Run(run_dir)
    if not run.clean.exists() or not run.frame.exists():
        raise FileNotFoundError(f"run {run_dir} needs prepare (and an orientation) first")
    args = [str(run.clean), str(run.frame), str(run.root), "--units", units]
    if tol is not None:
        args += ["--tol", str(tol)]
    if run.fit_report.exists():
        run.fit_report.unlink()     # never read a stale report as this run's
    try:
        res = run_module("fairsolid.stages.s30_fit", args)
    except StageError as exc:
        if "SIZE CHECK FAILED" in str(exc) and run.fit_report.exists():
            rep = json.loads(run.fit_report.read_text())
            run.save(fit={"status": "STOPPED", "report": str(run.fit_report),
                          "size_check": rep["size_check"],
                          "review": rep.get("review", [])})
            raise FitStopped(rep["size_check"]["message"]) from None
        raise
    run.save(fit=res)
    return res


def refscan(run_dir: Path, *, cell: float | None = None, knit: bool = False,
            knit_tol: float = 1.0, patch_boxes: list | None = None,
            tidy: bool = True) -> dict:
    """Stage 40, reference scan mode (plan part 10).

    For scans that are not parts (the space a new part has to fit into). Keeps
    open, separate surfaces - never forced into a solid - and adds reference
    geometry. Needs an orientation (20_frame.json) like every other mode; the
    scan is moved into that frame rigidly and never scaled.
    """
    run = Run(Path(run_dir))
    if not run.scan.exists():
        raise FileNotFoundError(f"run {run_dir} has no 00_scan.* - prepare it first")
    if not run.frame.exists():
        raise FileNotFoundError(f"run {run_dir} needs an orientation (20_frame.json) first")
    args = [str(run.scan), str(run.frame), str(run.root)]
    noise = run.state().get("frame", {}).get("noise_floor")
    if noise:
        args += ["--noise", str(noise)]
    if cell is not None:
        args += ["--cell", str(cell)]
    if knit:
        args += ["--knit", "--knit-tol", str(knit_tol)]
    for b in patch_boxes or []:
        args += ["--patch-box", *[str(float(x)) for x in b]]
    if not tidy:
        args += ["--no-tidy"]
    res = run_module("fairsolid.stages.s40_refscan", args, timeout=3600)
    run.save(mode="reference", refscan=res)
    return res
