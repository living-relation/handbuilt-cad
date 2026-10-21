"""Structural-only minimum-wall check for printed (or any thin-walled) parts, driven by a per-project config.

Rule: the minimum wall applies to critical or structural features only. A thin spot on one of those FAILS; any other thin spot
is FLAGGED for the user to change or approve; a spot the config can't place is 'questionable' and flagged too, never passed
silently. Approved spots are listed in the config as exemptions. Classes, feature boxes and exemptions live in the config
(tools/checks/walls.example.toml); classification is in tools/checks/wall_classes.py. The project's own rules win over the defaults.

Detection (mesh based, STL or any trimesh-readable file):
  W  walls under min_wall: the part is cut in planes every `step` mm along x, y and z; in every section the material thinner than
     min_wall is what an opening (shrink by min_wall/2, grow back, mitred corners) takes away. Sections through the same spot
     merge into one 3-D spot; a spot seen in one section only is a plane grazing a curved face and is dropped.
  A  attached by >= attach_min (optional): voxels of `pitch` mm, opened with a cube of ~attach_min. Material that survives is
     the "body". A thin piece that meets the body in ONE place only is a cantilever attached by less than attach_min; a thick
     piece that meets the main body only through thin material is attached by less than attach_min too.
There is no default minimum wall: min_wall must be in the config (ask the user once; never assume one).
Detection settings (step, pitch, snap, despike, sliver, graze_sections, skin, cluster_tol, min_area, min_vol) have defaults that
came from st185's R127 sweep on real MJF parts; a config can override any of them. Projects with their own report format (st185)
import walls() / attachments() / section() from here and keep only their project glue.

Usage (the project's Python environment: trimesh, shapely, scipy, Pillow):
    python tools/checks/check_printed_walls.py --config path/to/walls.toml [--only PartA,PartB]
Writes the config's `output` JSON (and `flags_md` if set). Exit 0 = no structural fail, 1 = a structural / critical fail or a
missing model file, 2 = config error.
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wall_classes as WC  # noqa: E402
import numpy as np
import trimesh
from shapely.geometry import LineString, Polygon, box as sbox
from shapely.ops import polygonize, unary_union

STEP, PITCH = 0.5, 0.2            # mm: default section spacing (W), voxel size (A); the config can override
MIN_AREA = 0.3                    # mm2: smaller W pieces in a section are tessellation noise on curved faces
MIN_VOL = 2.0                     # mm3: smaller A pieces are voxel noise
# Detection settings (config keys of the same name override them). Ported from st185's cad/check_printed_walls.py
# (R127 sweep, 2026-10-16/17), where they were found on real MJF parts; they hold for any mesh:
SNAP = 1e-4                       # mm: section segment ends closer than this are one point (rounding alone left rings open, and
                                  #     polygonize then dropped whole outlines from a section)
DESPIKE = 0.02                    # mm: open + close a section by this to drop spikes / slits where two cut faces meet (0 = off)
SLIVER = 0.01                     # mm: drop round-off slivers along shared edges of a thin piece (0 = off)
GRAZE = 4                         # a W spot seen by ONE axis family in fewer sections than this is planes grazing a square edge (0 = off)
SKIN = 1.5                        # mm: a thin piece must stand at least this far out of the body to count as a cantilever (0 = off)
CLUSTER_TOL = 0.6                 # mm: section pieces closer than this merge into one 3-D spot


def opts_from(cfg):
    """Detection settings from a config dict (missing keys = the module defaults)."""
    g = lambda k, d: cfg.get(k, d) if cfg else d   # noqa: E731
    return dict(step=g('step', STEP), pitch=g('pitch', PITCH), min_area=g('min_area', MIN_AREA), min_vol=g('min_vol', MIN_VOL),
                snap=g('snap', SNAP), despike=g('despike', DESPIKE), sliver=g('sliver', SLIVER), graze=g('graze_sections', GRAZE),
                skin=g('skin', SKIN), cluster_tol=g('cluster_tol', CLUSTER_TOL))


def _snap_points(pts, tol):
    """Union points closer than tol (union-find over KD-tree pairs) to one representative each."""
    from scipy.spatial import cKDTree
    par = np.arange(len(pts))
    for i, j in sorted(cKDTree(pts).query_pairs(tol)):
        ri, rj = i, j
        while par[ri] != ri:
            ri = par[ri]
        while par[rj] != rj:
            rj = par[rj]
        if ri != rj:
            par[max(ri, rj)] = min(ri, rj)
    for i in range(len(par)):
        r = i
        while par[r] != r:
            r = par[r]
        par[i] = r
    return pts[par]


def section(m, axis, c, snap=SNAP, despike=DESPIKE):
    """Material polygon of the section of mesh m by the plane axis = c, in the plane's (u, v) coordinates."""
    n = np.zeros(3)
    n[axis] = 1.0
    o = np.zeros(3)
    o[axis] = c
    segs = trimesh.intersections.mesh_plane(m, n, o)
    if len(segs) == 0:
        return None
    k = [i for i in range(3) if i != axis]
    if snap:
        pts = _snap_points(segs[:, :, k].reshape(-1, 2), snap).reshape(-1, 2, 2)
        lines = [LineString(q) for q in pts if np.linalg.norm(q[0] - q[1]) > 1e-9]
    else:
        lines = [LineString(s[:, k].round(5)) for s in segs if np.linalg.norm(s[0] - s[1]) > 1e-7]
    region = None
    for p in polygonize(lines):
        p = Polygon(p.exterior)
        region = p if region is None else region.symmetric_difference(p)      # even-odd: holes come out
    if region is None or region.is_empty:
        return None
    if despike:
        return region.buffer(0).buffer(-despike, join_style=2).buffer(despike * 2, join_style=2).buffer(-despike, join_style=2)
    return region.buffer(0)


def thin_pieces(region, wall, min_area=MIN_AREA, sliver=SLIVER):
    r = wall / 2
    opened = region.buffer(-r, join_style=2, mitre_limit=2.0).buffer(r, join_style=2, mitre_limit=2.0)
    thin = region.difference(opened)
    if sliver:
        thin = thin.buffer(-sliver, join_style=2).buffer(sliver, join_style=2)
    return [g for g in getattr(thin, 'geoms', [thin]) if g.geom_type == 'Polygon' and g.area >= min_area]


def inside(g, b, tol=0.0):
    """Box g = [x0, x1, y0, y1, z0, z1, ...] lies inside box b (with tol of slack)."""
    return all(b[2 * d] - tol <= g[2 * d] and g[2 * d + 1] <= b[2 * d + 1] + tol for d in range(3))


def walls(m, wall, step=STEP, allow=(), seen=None, opts=None):
    """W: [(x0, x1, y0, y1, z0, z1, n sections)] 3-D spots thinner than wall (mm).
    allow = [(key, box)]: a section piece inside a box is left out and counted in seen[key] (spots that must stay thin)."""
    o = dict(opts_from(None), **(opts or {}))
    lo, hi = m.bounds
    pcs = []
    for axis in range(3):
        k = [i for i in range(3) if i != axis]
        for c in np.arange(lo[axis] + step / 2 + 0.0137, hi[axis], step):
            reg = section(m, axis, c, o['snap'], o['despike'])
            if reg is None:
                continue
            for g in thin_pieces(reg, wall, o['min_area'], o['sliver']):
                b = g.bounds
                bb = [0.0] * 6
                bb[2 * k[0]], bb[2 * k[0] + 1], bb[2 * k[1]], bb[2 * k[1] + 1] = b[0], b[2], b[1], b[3]
                bb[2 * axis], bb[2 * axis + 1] = c - step / 2, c + step / 2
                bb.append(axis)
                key = next((kk for (kk, bx) in allow if inside(bb, bx)), None)
                if key is not None:
                    if seen is not None:
                        seen[key] = seen.get(key, 0) + 1
                    continue
                pcs.append(bb)
    # a real wall shows in 2+ sections; 1 = a plane grazing a curved face. A spot seen by ONE axis family only, in under GRAZE
    # sections, is planes grazing a square edge whose other face is nearly parallel to them - sections along the other axes see solid
    return [g[:7] for g in cluster(pcs, o['cluster_tol']) if g[6] >= 2 and not (o['graze'] and len(g[7]) == 1 and g[6] < o['graze'])]


def cluster(boxes, tol=CLUSTER_TOL):
    """Merge overlapping boxes (within tol): [x0, x1, y0, y1, z0, z1, n boxes, {section axes}], biggest first."""
    par = list(range(len(boxes)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if all(a[2 * d] - tol <= b[2 * d + 1] and b[2 * d] - tol <= a[2 * d + 1] for d in range(3)):
                par[f(i)] = f(j)
    out = {}
    for i, b in enumerate(boxes):
        g = out.setdefault(f(i), [1e9, -1e9, 1e9, -1e9, 1e9, -1e9, 0, set()])
        for d in range(3):
            g[2 * d] = min(g[2 * d], b[2 * d])
            g[2 * d + 1] = max(g[2 * d + 1], b[2 * d + 1])
        g[6] += 1
        if len(b) > 6:
            g[7].add(b[6])
    return sorted(out.values(), key=lambda g: -g[6])


def voxels(m, pitch=PITCH, opts=None):
    """Solid occupancy at pitch (z layers rasterised from the sections) and the grid origin."""
    o = dict(opts_from(None), **(opts or {}))
    PITCH = pitch
    from PIL import Image, ImageDraw
    lo, hi = m.bounds
    nx, ny, nz = (np.ceil((hi - lo) / PITCH).astype(int) + 2)
    org = lo - PITCH
    vol = np.zeros((nx, ny, nz), bool)
    for iz in range(nz):
        z = org[2] + (iz + 0.5) * PITCH
        if z <= lo[2] or z >= hi[2]:
            continue
        reg = section(m, 2, z, o['snap'], o['despike'])
        if reg is None:
            continue
        im = Image.new('1', (nx, ny), 0)
        dr = ImageDraw.Draw(im)
        for g in getattr(reg, 'geoms', [reg]):
            if g.geom_type != 'Polygon':
                continue
            dr.polygon([((x - org[0]) / PITCH - 0.5, (y - org[1]) / PITCH - 0.5) for x, y in g.exterior.coords], fill=1)
            for h in g.interiors:
                dr.polygon([((x - org[0]) / PITCH - 0.5, (y - org[1]) / PITCH - 0.5) for x, y in h.coords], fill=0)
        vol[:, :, iz] = np.array(im, bool).T
    return vol, org


def attachments(m, attach, pitch=PITCH, opts=None, stats=None):
    """A: [(kind, x0, x1, y0, y1, z0, z1, volume mm3)] features attached by less than attach (mm); None = the part is all thin
    (a cover, a pan, a clip: no body to hang anything from, W checks it). stats['skin'] = thin pieces standing less than `skin`
    out of the body (the voxel skin of a sloped or tapered face, not cantilevers), counted but not listed."""
    from scipy import ndimage
    o = dict(opts_from(None), **(opts or {}))
    PITCH, MINV, SK = pitch, o['min_vol'], o['skin']
    vol, org = voxels(m, pitch, o)
    k = int(round(attach / PITCH)) - 1          # e.g. 3.0 / 0.2 -> 14 voxels = 2.8: a 3.0 wall survives, a 2.5 one does not
    core = vol.astype(np.uint8)
    for ax in range(3):
        core = ndimage.minimum_filter1d(core, k, axis=ax, mode='constant', cval=0)
    for ax in range(3):
        core = ndimage.maximum_filter1d(core, k, axis=ax, mode='constant', cval=0)
    core = core.astype(bool) & vol
    thin = vol & ~core
    out = []
    if stats is not None:
        stats['skin'] = 0

    def bbox(sl):
        return [float(org[d] + sl[d].start * PITCH) for d in range(3)], [float(org[d] + sl[d].stop * PITCH) for d in range(3)]
    if core.sum() < 0.1 * vol.sum():                         # all thin (a cover, a pan, a clip): walls only, W checks them
        return None
    if core.any():
        cl, nc = ndimage.label(core)
        sizes = np.bincount(cl.ravel())
        sizes[0] = 0
        main = int(np.argmax(sizes))
        for i, sl in enumerate(ndimage.find_objects(cl), 1):
            v = sizes[i] * PITCH ** 3
            if i != main and v >= MINV:
                a, b = bbox(sl)
                out.append(('thick piece held only by thin material', a[0], b[0], a[1], b[1], a[2], b[2], round(v, 1)))
        tl, nt = ndimage.label(thin)
        edge = ndimage.binary_dilation(thin) & core             # body voxels a thin piece touches
        pl, npl = ndimage.label(edge, structure=np.ones((3, 3, 3), bool))
        pairs = set()
        for ax in range(3):
            for sh in (1, -1):
                t2 = np.roll(tl, sh, axis=ax)
                hit = (pl > 0) & (t2 > 0)
                pairs.update(zip(t2[hit].tolist(), pl[hit].tolist()))
        patches = {}
        for t, p in pairs:
            patches.setdefault(t, set()).add(p)
        tsz = np.bincount(tl.ravel())
        objs = ndimage.find_objects(tl)
        pad = int(SK / PITCH) + 2

        def proud(t):           # the parts of thin piece t standing >= SK out of the body: [(slices, volume mm3)]
            sl = tuple(slice(max(0, q.start - pad), q.stop + pad) for q in objs[t - 1])
            pm = (tl[sl] == t) & (ndimage.distance_transform_edt(~core[sl]) * PITCH >= SK)
            lab, n = ndimage.label(pm)
            szs = np.bincount(lab.ravel())
            return [(tuple(slice(sl[d].start + q[d].start, sl[d].start + q[d].stop) for d in range(3)), szs[i] * PITCH ** 3)
                    for i, q in enumerate(ndimage.find_objects(lab), 1) if szs[i] * PITCH ** 3 >= MINV]
        for t, ps in patches.items():
            v = tsz[t] * PITCH ** 3
            if len(ps) != 1 or v < MINV:
                continue
            if not SK:
                a, b = bbox(objs[t - 1])
                out.append(('thin piece held at one place (cantilever)', a[0], b[0], a[1], b[1], a[2], b[2], round(v, 1)))
                continue
            pr = proud(t)
            if not pr:
                if stats is not None:
                    stats['skin'] += 1
                continue
            for (q, pv) in pr:       # each proud part on its own (a long skin piece is located by the bits that stand out)
                a, b = bbox(q)
                out.append(('thin piece held at one place (cantilever)', a[0], b[0], a[1], b[1], a[2], b[2], round(pv, 1)))
    return out


def check_part(m, cfg, part):
    """W / A spots of one mesh, classified by the config: dict for the JSON report."""
    o = opts_from(cfg)
    stats = {}
    w = walls(m, cfg['min_wall'], o['step'], opts=o)
    at = attachments(m, cfg['attach_min'], o['pitch'], o, stats) if cfg.get('attach_min') else None
    lo, hi = m.bounds
    bounds = [float(lo[0]), float(hi[0]), float(lo[1]), float(hi[1]), float(lo[2]), float(hi[2])]
    ws = [dict(at=[round(float(v), 1) for v in g[:6]], sections=int(g[6])) for g in w]
    ats = [dict(kind=x[0], at=[round(float(v), 1) for v in x[1:7]], vol_mm3=x[7]) for x in (at or [])]
    rows = WC.classify_spots(part, cfg, ws, ats, bounds)
    for (kind, a, extra, c, v, why), spot in zip(rows, ws + ats):
        spot.update({'class': c, 'result': v, 'why': why})
    return dict(volume_cm3=round(float(m.volume) / 1000, 1), bounds=[round(b, 1) for b in bounds],
                attach_checked=bool(cfg.get('attach_min')) and at is not None, attach_skin=stats.get('skin', 0), walls=ws, attach=ats,
                fail=sum(1 for r in rows if r[4] == 'fail'), flag=sum(1 for r in rows if r[4] == 'flag'),
                approved=sum(1 for r in rows if r[4] == 'approved')), rows


def write_flags_md(path, lines, cfg):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('# Thin spots flagged for change or approval\n\n')
        f.write('Generated by `tools/checks/check_printed_walls.py` - do not hand-edit. The minimum wall (%s mm) applies to critical or\n'
                'structural features only; those fail the check. The spots below are thin but not structural (or not placed):\n'
                '**change or approve** each one. Approve = an `[[parts.exempt]]` box (or a non-structural feature box) in the wall\n'
                'config, with the user\'s words and the date.\n\n' % cfg['min_wall'])
        f.write('Flagged: %d\n\n' % len(lines))
        f.write(''.join('- %s\n' % l for l in lines) if lines else '- none\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description='Structural-only minimum-wall check for printed / thin parts (per-project config).')
    ap.add_argument('--config', required=True, help='wall-check config (TOML or JSON); see tools/checks/walls.example.toml')
    ap.add_argument('--only', default='', help='comma-separated part names to re-check (others kept from the last report)')
    a = ap.parse_args(argv)
    try:
        cfg = WC.load_config(a.config)
    except (OSError, WC.ConfigError) as e:
        print('config error: %s' % e)
        return 2
    base = cfg['_dir']
    outp = os.path.join(base, cfg.get('output', 'wall_check.json'))
    res = {'rule': 'minimum wall %s mm on structural / critical features (fail); other thin spots flagged%s'
                   % (cfg['min_wall'], '; attachments >= %s mm' % cfg['attach_min'] if cfg.get('attach_min') else ''),
           'parts': {}}
    if a.only and os.path.isfile(outp):
        res = json.load(open(outp))
    only = [x for x in a.only.split(',') if x]
    all_rows, missing = {}, []
    for part in cfg['parts']:
        name = part['name']
        if only and name not in only:
            continue
        p = os.path.join(base, part.get('file', name + '.stl'))
        if not os.path.isfile(p):
            print('%s: model file not found: %s' % (name, p))
            missing.append(name)
            continue
        t0 = time.time()
        m = trimesh.load(p, force='mesh')
        res['parts'][name], all_rows[name] = check_part(m, cfg, part)
        r = res['parts'][name]
        print('%s (%.0f s): %d fail, %d flagged, %d approved' % (name, time.time() - t0, r['fail'], r['flag'], r['approved']))
        for (kind, at, extra, c, v, why) in all_rows[name]:
            if v != 'approved':
                print('   %s %s  x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f  [%s] %s' % (v.upper(), kind, *at, c, why))
    with open(outp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(res, f, indent=1)
    print('wrote', outp)
    if cfg.get('flags_md'):
        lines = []
        for name, r in sorted(res['parts'].items()):
            for kind, key in (('W', 'walls'), ('A', 'attach')):
                for s in r.get(key) or []:
                    if s.get('result') == 'flag':
                        what = 'wall under %s mm' % cfg['min_wall'] if kind == 'W' else s.get('kind', 'attachment')
                        lines.append('%s  %s  %s at x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f  [%s] %s'
                                     % (s['class'].upper(), name, what, *s['at'], s['class'], s['why']))
        write_flags_md(os.path.join(base, cfg['flags_md']), lines, cfg)
    fails = sum(r.get('fail', 0) for r in res['parts'].values())
    return 1 if fails or missing else 0


if __name__ == '__main__':
    sys.exit(main())
