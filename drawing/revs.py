"""Rev letters, clerical decimals and the per-model rev log (REVLOG.md).

Daniel's rules (2026-10-17), see DRAWING-RULES.md:
- Letters run A..Z skipping I, L, O, Q, then AA, AB ... (same skips), like spreadsheet columns.
- A model change bumps the letter and resets the decimal (C.02 -> D).
- A drawing-only change that doesn't affect fit, form or function is a clerical rev: C -> C.01 -> C.02.
- The rev log lists one row per PR / release. Clerical revs are never listed. Rev A is always "Initial".
- Dates are dd/mm/yy.
"""
import os, re, datetime
from collections import namedtuple

LETTERS = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if c not in "ILOQ"]   # 22 usable letters
_IDX = {c: i for i, c in enumerate(LETTERS)}
N = len(LETTERS)

RevEntry = namedtuple("RevEntry", "rev desc by date")
REVLOG_NAME = "REVLOG.md"
REVLOG_MAX_ROWS = 6          # rows shown on the drawing; oldest dropped first


# ---------------- letters ----------------
def index_to_letter(n):
    """0 -> A, 21 -> Z, 22 -> AA, 23 -> AB ... (bijective base 22 over the allowed letters)."""
    if n < 0: raise ValueError("rev index must be >= 0")
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, N)
        s = LETTERS[r] + s
    return s

def letter_to_index(s):
    s = s.strip().upper()
    if not is_valid_letter(s): raise ValueError(f"not a valid rev letter: {s!r} (A-Z, no I/L/O/Q)")
    n = 0
    for c in s: n = n * N + _IDX[c] + 1
    return n - 1

def is_valid_letter(s):
    return bool(s) and all(c in _IDX for c in s.strip().upper())

def next_letter(s):
    return index_to_letter(letter_to_index(s) + 1)

def letter_from_release_count(n):
    """1 release -> A, 2 -> B ... (for back-filling letters by counting past releases)."""
    if n < 1: raise ValueError("release count must be >= 1")
    return index_to_letter(n - 1)


# ---------------- full revs (letter + clerical decimal) ----------------
_REV_RE = re.compile(r"^\s*([A-Za-z]+)(?:\.(\d{1,3}))?\s*$")

def parse_rev(rev):
    """'C' -> ('C', 0); 'C.01' -> ('C', 1)."""
    m = _REV_RE.match(str(rev))
    if not m or not is_valid_letter(m.group(1)): raise ValueError(f"bad rev {rev!r}")
    return m.group(1).upper(), int(m.group(2) or 0)

def format_rev(letter, clerical=0):
    return letter.upper() if not clerical else f"{letter.upper()}.{clerical:02d}"

def is_clerical(rev):
    try: return parse_rev(rev)[1] > 0
    except ValueError: return False

def base_letter(rev):
    return parse_rev(rev)[0]

def bump_clerical(rev):
    """Drawing-only change (no fit/form/function impact): C -> C.01, C.01 -> C.02."""
    l, c = parse_rev(rev); return format_rev(l, c + 1)

def bump_model(rev):
    """Model change: next letter, decimal reset. C.02 -> D, Z -> AA."""
    return next_letter(parse_rev(rev)[0])

def rev_key(rev):
    l, c = parse_rev(rev); return (letter_to_index(l), c)


# ---------------- dates ----------------
def to_ddmmyy(d):
    """date / datetime / 'YYYY-MM-DD' / 'dd/mm/yy' / 'dd/mm/yyyy' -> 'dd/mm/yy'."""
    if d is None or d == "": return ""
    if isinstance(d, (datetime.date, datetime.datetime)): return d.strftime("%d/%m/%y")
    s = str(d).strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m: return datetime.date(int(m[1]), int(m[2]), int(m[3])).strftime("%d/%m/%y")
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})$", s)
    if m:
        y = int(m[3]); y = y + 2000 if y < 100 else y
        return datetime.date(y, int(m[2]), int(m[1])).strftime("%d/%m/%y")
    raise ValueError(f"unrecognised date {d!r} (use dd/mm/yy)")


# ---------------- REVLOG.md ----------------
HEADER = """# REVLOG{title}

Rev log for this model and its drawing. One row per PR or release, never per edit.
Clerical revs (C.01, C.02 ...) are not listed. Rev A is always "Initial". Date is dd/mm/yy.
The drawing's rev log table (sheet 1, top right) is generated from this file.

| Rev | Description | By | Date |
|-----|-------------|----|------|
"""

def revlog_candidates(step_path, pn=None):
    """Where a model's rev log may live, in order: <step stem>.REVLOG.md, <part no>.REVLOG.md
    (both work in folders holding several models), then REVLOG.md when the folder holds only this one STEP."""
    d = os.path.dirname(os.path.abspath(step_path)); stem = os.path.splitext(os.path.basename(step_path))[0]
    c = [os.path.join(d, f"{stem}.{REVLOG_NAME}")]
    if pn: c.append(os.path.join(d, f"{pn}.{REVLOG_NAME}"))
    steps = [f for f in os.listdir(d) if f.lower().endswith((".step", ".stp"))] if os.path.isdir(d) else []
    if len(steps) <= 1: c.append(os.path.join(d, REVLOG_NAME))
    return c

def find_revlog(step_path, explicit=None, pn=None):
    """Explicit path, else the first existing revlog_candidates(). Returns path or None."""
    if explicit: return explicit if os.path.exists(explicit) else None
    if not step_path: return None
    for p in revlog_candidates(step_path, pn):
        if os.path.exists(p): return p
    return None

def read_revlog(path):
    """All rows in file order (oldest first). Example/header/separator rows are skipped."""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s.startswith("|"): continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) < 4: continue
            if cells[0].lower() == "rev" or set(cells[0]) <= set("-: "): continue
            out.append(RevEntry(cells[0].upper(), cells[1], cells[2], cells[3]))
    return out

def write_revlog(path, entries, title=""):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(HEADER.format(title=f" - {title}" if title else ""))
        for e in entries:
            f.write(f"| {e.rev} | {e.desc.replace('|', '/')} | {e.by} | {to_ddmmyy(e.date)} |\n")

def add_release(path, rev, desc, by, date=None, title=""):
    """Record one release. Clerical revs are refused (not logged). If the letter is already logged
    (several edits in one PR / session), the existing row is updated instead of adding a new one."""
    l, c = parse_rev(rev)
    if c: raise ValueError(f"{rev} is a clerical rev; clerical revs are not listed in the rev log")
    entries = read_revlog(path) if os.path.exists(path) else []
    if l == "A": desc = "Initial"
    date = to_ddmmyy(date or datetime.date.today())
    e = RevEntry(l, desc, by, date)
    logged = [x.rev for x in entries if not is_clerical(x.rev)]
    latest = max(logged, key=letter_to_index) if logged else None
    if latest and letter_to_index(l) < letter_to_index(latest):
        raise ValueError(f"rev {l} is older than the latest logged rev {latest}")
    if l == latest:                       # same release (several edits in one PR / session): update its row
        i = max(k for k, x in enumerate(entries) if x.rev == l); entries[i] = e
    else:
        entries.append(e)
    write_revlog(path, entries, title)
    return entries

def table_rows(entries, max_rows=REVLOG_MAX_ROWS):
    """Rows for the drawing table: clerical revs dropped, one row per letter (latest wins),
    sorted oldest -> newest, Rev A forced to 'Initial', dates normalised, only the newest max_rows kept."""
    by_letter = {}
    for e in entries:
        try: l, c = parse_rev(e.rev)
        except ValueError: continue
        if c: continue
        by_letter[l] = RevEntry(l, "Initial" if l == "A" else e.desc, e.by, to_ddmmyy(e.date))
    rows = sorted(by_letter.values(), key=lambda e: letter_to_index(e.rev))
    return rows[-max_rows:] if max_rows else rows

def from_spec_revs(revs):
    """Legacy spec 'revs' tuples (rev, desc, date, by) -> RevEntry list."""
    return [RevEntry(r[0], r[1], r[3] if len(r) > 3 else "", r[2] if len(r) > 2 else "") for r in (revs or [])]

def check_letter_matches(drawing_rev, rows):
    """The model drives the letter and the drawing matches: the title-block rev letter (ignoring any
    clerical decimal) must equal the newest rev-log letter."""
    if not rows or drawing_rev in (None, ""): return
    dl = base_letter(drawing_rev); ml = rows[-1].rev
    if dl != ml:
        raise ValueError(f"title block rev {drawing_rev} does not match the newest rev log entry {ml}; "
                         "the model drives the letter - update REVLOG.md or the spec rev")
