"""Fairsolid command line.

Three commands, matching how the work actually splits:

    fairsolid prepare SCAN [--run DIR]   clean, measure, render orientations
    fairsolid choose  N    [--run DIR]   commit and produce the STEP
    fairsolid run     SCAN [--run DIR]   both, taking the automatic orientation

`prepare` then `choose` is the normal path: it stops to show you the rendered
orientation options and waits for a pick. `run` is for batch use.
"""
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .pipeline import FitStopped, Run, finish, fit, prepare, refscan, review

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()

DEFAULT_RUN = Path("runs/current")


def _show_features(state: dict) -> None:
    frame = state.get("frame", {})
    feats = frame.get("features", {}).get("cylinders", [])
    if not feats:
        return
    t = Table(title="Measured round features", title_style="bold")
    t.add_column("diameter (mm)", justify="right")
    t.add_column("support (points)", justify="right")
    for f in feats:
        t.add_row(f"{f['diameter']:.4f}", str(f["n_points"]))
    console.print(t)


def _show_deviation(dev: dict) -> None:
    colour = {"PASS": "green", "MARGINAL": "yellow", "FAIL": "red"}
    v = dev["verdict"]
    console.print(f"\n[bold {colour.get(v, 'white')}]{v}[/] "
                  f"- {dev['fraction_within_tol'] * 100:.1f}% of the surface "
                  f"within {dev['tolerance_mm']} mm of the scan")
    console.print(f"  median {dev['median_mm']:.4f} mm   "
                  f"p95 {dev['p95_mm']:.4f} mm   max {dev['max_mm']:.4f} mm")
    if v != "PASS":
        console.print("  [dim]large deviations usually mean occluded regions "
                      "the scan never captured, not reconstruction error[/]")


@app.command()
def prepare_cmd(
    scan: Path = typer.Argument(..., help="scan mesh or point cloud"),
    run: Path = typer.Option(DEFAULT_RUN, "--run", help="working directory"),
    target_faces: int = typer.Option(200_000, help="decimation target"),
    poisson_depth: int = typer.Option(10, help="Poisson octree depth"),
    idealize: bool = typer.Option(True, help="remove casting texture / flatten faces"),
    smooth_iters: int = typer.Option(0, help="Taubin iterations; 0 = snap only (default)"),
    texture_mm: float = typer.Option(None, help="texture amplitude to erase"),
    force: bool = typer.Option(False, help="ignore cached stage outputs"),
) -> None:
    """Clean the scan, idealise it, measure it, render orientation options."""
    console.print(f"[bold]Preparing[/] {scan}")
    state = prepare(scan, run, target_faces=target_faces,
                    poisson_depth=poisson_depth, idealize=idealize,
                    smooth_iters=smooth_iters, texture_mm=texture_mm,
                    force=force)

    ing, frame = state["ingest"], state["frame"]
    console.print(f"  {ing['kind']}, {ing['faces']} faces, "
                  f"longest extent {ing['longest_extent']:.2f} mm")
    for w in ing["warnings"]:
        console.print(f"  [yellow]warning:[/] {w}")
    idl = state.get("idealize")
    if idl:
        console.print(
            f"  idealised: flat regions {idl['flatness_before']:.4f} -> "
            f"{idl['flatness_after']:.4f} mm rms "
            f"({idl['flatness_gain'] * 100:.0f}% flatter); "
            f"{idl['snapped_to_planes']:,} verts snapped to planes/edges, "
            f"{idl['snapped_to_cylinders']:,} onto bores")
    console.print(f"  noise floor {frame['noise_floor']:.4f} mm  |  "
                  f"{frame['n_planes']} planes  |  "
                  f"{frame['n_cylinders']} cylinders")
    _show_features(state)

    console.print("\n[bold]Orientation options rendered:[/]")
    for i, p in enumerate(frame["previews"]):
        console.print(f"  [{i}] {p}" + ("   (auto pick)" if i == 0 else ""))
    console.print(f"\nPick one:  [bold]fairsolid choose N --run {run}[/]")


@app.command()
def choose(
    n: int = typer.Argument(0, help="orientation option index"),
    run: Path = typer.Option(DEFAULT_RUN, "--run"),
    tol: float = typer.Option(0.15, help="deviation tolerance, mm"),
    out: Path = typer.Option(None, "--out", help="copy the STEP here"),
    facet_budget: int = typer.Option(8_000, help="faces in the fallback STEP"),
) -> None:
    """Commit to an orientation and produce the STEP."""
    console.print(f"[bold]Reconstructing[/] with orientation {n}")
    state = finish(run, choice=n, tol=tol, facet_budget=facet_budget)

    if "reconstruct" in state:
        r = state["reconstruct"]
        t = Table(title="Parametric layers", title_style="bold")
        for c in ("z0", "z1", "thickness", "outer profile", "holes"):
            t.add_column(c, justify="right" if c != "outer profile" else "left")
        for layer in r["layers"]:
            t.add_row(f"{layer['z0']:.3f}", f"{layer['z1']:.3f}",
                      f"{layer['thickness']:.3f}", layer["outer"],
                      str(len(layer["holes"])))
        console.print(t)
        console.print(f"  volume {r['volume_mm3']:.1f} mm^3   "
                      f"bbox {r['bbox_mm'][0]:.3f} x {r['bbox_mm'][1]:.3f} "
                      f"x {r['bbox_mm'][2]:.3f} mm   {r['bytes'] / 1000:.0f} kB")
    else:
        console.print(f"[yellow]parametric reconstruction failed:[/] "
                      f"{state.get('reconstruct_error', '')[:300]}")
        console.print("[dim]falling back to the sewn faceted solid[/]")

    if "deviation" in state:
        _show_deviation(state["deviation"])

    primary = Path(state["primary"])
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(primary.read_bytes())
        primary = out
    console.print(f"\n[bold green]STEP:[/] {primary}")


@app.command()
def run_cmd(
    scan: Path = typer.Argument(...),
    run: Path = typer.Option(DEFAULT_RUN, "--run"),
    tol: float = typer.Option(0.15),
    out: Path = typer.Option(None, "--out"),
) -> None:
    """Prepare and finish in one go, taking the automatic orientation.

    Prefer `prepare` then `choose`: the orientation options are worth looking
    at. This exists for batch use.
    """
    # Keyword args deliberately. This was a positional call, and when
    # `idealize` was inserted into prepare_cmd's signature it silently began
    # receiving `False` from the argument meant for `force`.
    prepare_cmd(scan=scan, run=run, target_faces=200_000, poisson_depth=10,
                idealize=True, smooth_iters=0, texture_mm=None, force=False)
    choose(n=0, run=run, tol=tol, out=out, facet_budget=8_000)


@app.command("fit")
def fit_cmd(
    run: Path = typer.Option(DEFAULT_RUN, "--run"),
    tol: float = typer.Option(None, help="tolerance, mm (default: from part size and noise)"),
    units: str = typer.Option("auto", help="hole-size table: auto, metric or inch (never rescales)"),
) -> None:
    """Fit flat and round areas, snap them, check overall size, write a report.

    Runs after orientation. Measures only - no trimming or knitting yet.
    """
    if units not in ("auto", "metric", "inch"):
        raise typer.BadParameter("units must be auto, metric or inch")
    try:
        res = fit(run, tol=tol, units=units)
    except FitStopped as exc:
        console.print(f"[bold red]STOPPED:[/] {exc}")
        st = Run(run).state().get("fit", {})
        for p in st.get("review", []):
            console.print(f"  review: {p}")
        raise typer.Exit(1)
    s, t = res["summary"], res["tolerance"]
    console.print(f"tolerance {t['value_mm']} mm ({t['band']}, {t['set_by']})  |  "
                  f"hole table {res['units']['table']} (guess {res['units']['guess']})")
    console.print(f"{s['n_areas']} areas: {s['n_flat']} flat, {s['n_round']} round "
                  f"({s['n_holes']} holes), {s.get('n_freeform', 0)} freeform; {s['n_areas_snapped']} snapped; "
                  f"{s['n_within_tol']} within tolerance "
                  f"({s.get('n_within_tol_raw', '?')} before texture smoothing)")
    w = s.get("worst_area_judged") or s["worst_area"]
    if w:
        console.print(f"worst area {w['area']} ({w['kind']}): smoothed p95 "
                      f"{w.get('judged_p95_mm', w['p95_mm']):.3f} mm, raw p95 "
                      f"{w['p95_mm']:.3f} mm, max {w['max_mm']:.3f} mm")
    if "covered_area_frac" in s:
        console.print(f"surface covered by a fitted surface {s['covered_area_frac'] * 100:.1f}%, "
                      f"still uncovered {s['uncovered_area_frac'] * 100:.1f}%")
    sc = res["size_check"]
    console.print(f"size check {sc['status']}: diff {sc['diff_mm']} mm")
    console.print(f"report  {res['report']}\narea map {res['preview']}")
    for p in res.get("review", []):
        console.print(f"  review: {p}")


@app.command("refscan")
def refscan_cmd(
    run: Path = typer.Option(DEFAULT_RUN, "--run"),
    cell: float = typer.Option(None, help="surface grid step, mm (default 2.5)"),
    knit: bool = typer.Option(False, help="sew the surfaces into one open shell"),
    knit_tol: float = typer.Option(1.0, help="sewing tolerance, mm"),
    patch_box: list[str] = typer.Option(None, "--patch-box",
                                        help="x0,y0,z0,x1,y1,z1: fit one bridging surface over the scan in this box (repeatable)"),
    tidy: bool = typer.Option(True, help="smooth the trimmed edges"),
) -> None:
    """Reference scan mode: open surfaces + datums for designing a part to fit.

    For scans that are not parts. Runs after orientation. Never builds a solid
    and never rescales.
    """
    boxes = []
    for b in patch_box or []:
        vals = [float(x) for x in b.split(",")]
        if len(vals) != 6:
            raise typer.BadParameter("--patch-box needs 6 numbers: x0,y0,z0,x1,y1,z1")
        boxes.append(vals)
    res = refscan(run, cell=cell, knit=knit, knit_tol=knit_tol, patch_boxes=boxes, tidy=tidy)
    m = res["metrics"]["on_panels"]
    console.print(f"{res['n_surfaces']} surfaces from {res['n_patches_found']} patches, "
                  f"covering {res['covered_area_frac'] * 100:.0f}% of the scan")
    console.print(f"on the panels ({m['share_of_scan_pct']:.0f}% of scan points): median "
                  f"{m['median_mm']:.3f} mm, p95 {m['p95_mm']:.3f} mm, "
                  f"{m['pct_within_0.5mm']:.0f}% within 0.5 mm")
    d = res["datums"]
    console.print(f"datums: origin + XYZ axes, {len(d['planes'])} planes, {len(d['points'])} points")
    if res.get("knit"):
        k = res["knit"]
        console.print(f"knit at {k['tolerance_mm']} mm: {k['free_edges']} open edges left")
    for k, v in res["files"].items():
        console.print(f"  {k}: {v}")


@app.command("review")
def review_cmd(
    run: Path = typer.Option(DEFAULT_RUN, "--run"),
    tol: float = typer.Option(None, help="tolerance, mm (default: the run's)"),
) -> None:
    """Render pictures of a run's reconstruction against the scan."""
    out = review(run, tol=tol)
    for p in out["review"]:
        console.print(f"  {p}")


@app.command()
def status(run: Path = typer.Option(DEFAULT_RUN, "--run")) -> None:
    """Show what a run directory currently holds."""
    st = Run(run).state()
    if not st:
        console.print(f"[yellow]no run at {run}[/]")
        raise typer.Exit(1)
    console.print_json(json.dumps(st))


@app.command()
def licenses() -> None:
    """License of every component this pipeline invokes."""
    t = Table(title="Fairsolid component licenses", title_style="bold")
    t.add_column("component"); t.add_column("license"); t.add_column("commercial use")
    rows = [
        ("pymeshlab / MeshLab", "GPL-3.0", "yes, with GPL obligations"),
        ("trimesh", "MIT", "yes"),
        ("CadQuery / OCCT", "Apache-2.0 / LGPL-2.1", "yes"),
        ("shapely, scipy, numpy", "BSD-3", "yes"),
        ("pyransac3d", "Apache-2.0", "yes"),
    ]
    for r in rows:
        t.add_row(*r)
    console.print(t)


app.command("prepare")(prepare_cmd)
app.command("run")(run_cmd)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
