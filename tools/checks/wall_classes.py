"""Structural-only minimum wall: sort every thin spot the wall check finds into a class, from a per-project config.

Rule: the minimum wall applies to critical or structural features only (load-bearing walls, outer skins behind pockets,
mounting / clip / retention features, walls that separate circuits or fluids, anything that seals). A thin spot there FAILS.
A thin spot anywhere else is not a failure, but it is FLAGGED for the user to change or approve. A spot the config can't
place is 'questionable' and flagged too - never passed silently. Spots the user already approved are listed as exemptions
in the config (with a note and date) and are reported as 'approved', not re-flagged.

Nothing project-specific lives here: the classes, the feature boxes and the exemptions come from the project's config
(see tools/checks/walls.example.toml). The project's own rules (AGENTS.md, decision log, register) win over these defaults.

A spot is (x0, x1, y0, y1, z0, z1) in the model's mm; kind 'W' (wall under min_wall) or 'A' (attached by under attach_min).
Classification order, first match wins:
  1. part exemptions   spot fully inside an approved box                       -> 'approved'
  2. part features     spot overlaps a named box                               -> that box's class
  3. A spots           attachment under attach_min = mounting / retention      -> classes.attach_class (default structural)
  4. outer band        within classes.outer_band of the part's x / y extent    -> 'structural' (outer skin); skipped if unset
  5. otherwise                                                                 -> classes.default (default questionable)
"""
import json, os

APPROVED = 'approved'
DEFAULT_CLASSES = dict(fail=['structural', 'critical'], flag=['non-structural', 'questionable'],
                       attach_class='structural', default='questionable', outer_band=None)


class ConfigError(ValueError):
    pass


def load_config(path):
    """Read a TOML (or JSON) wall-check config and fill in defaults. min_wall is required: there is no default wall."""
    with open(path, 'rb') as f:
        raw = f.read()
    if path.lower().endswith('.json'):
        cfg = json.loads(raw.decode('utf-8'))
    else:
        try:
            import tomllib
        except ImportError:              # Python < 3.11
            import tomli as tomllib
        cfg = tomllib.loads(raw.decode('utf-8'))
    cfg['_dir'] = os.path.dirname(os.path.abspath(path))
    return normalise(cfg)


def normalise(cfg):
    cfg = dict(cfg)
    if not isinstance(cfg.get('min_wall'), (int, float)) or cfg['min_wall'] <= 0:
        raise ConfigError('min_wall (mm) is required in the wall config and must be > 0; ask the user for it, never assume one')
    cl = dict(DEFAULT_CLASSES)
    cl.update(cfg.get('classes') or {})
    cl['fail'], cl['flag'] = list(cl['fail']), list(cl['flag'])
    if set(cl['fail']) & set(cl['flag']):
        raise ConfigError('a class cannot be both fail and flag: %s' % sorted(set(cl['fail']) & set(cl['flag'])))
    known = set(cl['fail']) | set(cl['flag'])
    for k in ('attach_class', 'default'):
        if cl[k] not in known:
            raise ConfigError('classes.%s = %r is not listed in classes.fail or classes.flag' % (k, cl[k]))
    parts = cfg.get('parts') or []
    if not parts:
        raise ConfigError('the wall config lists no [[parts]]')
    for p in parts:
        if not p.get('name'):
            raise ConfigError('every [[parts]] entry needs a name')
        for ft in p.get('features') or []:
            if ft.get('class') not in known:
                raise ConfigError('part %s feature %r: class %r is not in classes.fail or classes.flag'
                                  % (p['name'], ft.get('why', ''), ft.get('class')))
            _box(ft, p['name'])
        for ex in p.get('exempt') or []:
            _box(ex, p['name'])
            if not ex.get('why'):
                raise ConfigError('part %s: every exemption needs a why (the user\'s approval note)' % p['name'])
    cfg['classes'] = cl
    return cfg


def _box(entry, part):
    b = entry.get('box')
    if not (isinstance(b, (list, tuple)) and len(b) == 6 and all(isinstance(v, (int, float)) for v in b)):
        raise ConfigError('part %s: box must be [x0, x1, y0, y1, z0, z1] in mm (got %r)' % (part, b))
    return b


def _hit(a, b):
    """Boxes (x0, x1, y0, y1, z0, z1) overlap or touch."""
    return all(b[2 * d] <= a[2 * d + 1] and a[2 * d] <= b[2 * d + 1] for d in range(3))


def _inside(a, b):
    return all(b[2 * d] <= a[2 * d] and a[2 * d + 1] <= b[2 * d + 1] for d in range(3))


def classify(at, kind, part, cfg, bounds=None):
    """(class, why) for one spot. part = the config's [[parts]] entry; bounds = the part's (x0, x1, y0, y1, z0, z1)."""
    cl = cfg['classes']
    for ex in part.get('exempt') or []:
        if _inside(at, ex['box']):
            return APPROVED, 'approved: %s%s' % (ex['why'], (' (%s)' % ex['approved']) if ex.get('approved') else '')
    for ft in part.get('features') or []:
        if _hit(at, ft['box']):
            return ft['class'], ft.get('why', 'named feature')
    if kind == 'A':
        return cl['attach_class'], 'attached by less than %s mm: a mounting / clip / retention feature' % cfg.get('attach_min')
    band = cl.get('outer_band')
    if band and bounds:
        if min(at[0] - bounds[0], bounds[1] - at[1], at[2] - bounds[2], bounds[3] - at[3]) <= band:
            return 'structural', 'within %.1f mm of the part edge: outer skin / side wall' % band
    return cl['default'], 'not placed by the config - change or approve'


def verdict(cls, cfg):
    """'fail', 'flag' or 'approved' for a class."""
    if cls == APPROVED:
        return 'approved'
    return 'fail' if cls in cfg['classes']['fail'] else 'flag'


def classify_spots(part, cfg, walls=(), attach=(), bounds=None):
    """[(kind, at, extra, class, verdict, why)] for every W and A spot of one part."""
    out = []
    for kind, spots in (('W', walls), ('A', attach)):
        for s in spots:
            at, extra = list(s['at']), {k: v for k, v in s.items() if k != 'at'}
            c, why = classify(at, kind, part, cfg, bounds)
            out.append((kind, at, extra, c, verdict(c, cfg), why))
    return out


def flag_lines(rows_by_part, cfg):
    """Human-readable list of every flagged spot, for the user to change or approve one at a time."""
    lines = []
    for name in sorted(rows_by_part):
        for (kind, at, extra, c, v, why) in rows_by_part[name]:
            if v == 'flag':
                what = 'wall under %s mm' % cfg['min_wall'] if kind == 'W' else extra.get('kind', 'attachment under %s mm' % cfg.get('attach_min'))
                lines.append('%s  %s  %s at x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f  [%s] %s'
                             % (c.upper(), name, what, *at, c, why))
    return lines
