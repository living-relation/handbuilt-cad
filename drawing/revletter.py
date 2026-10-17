"""Revision letters for models and drawings.

Rules (see AGENTS.md, CAD and drawing rules 1-2):
- Letters run A..Z skipping I, L, O and Q, then AA, AB, ... (same alphabet per position).
- Rev A is only for a brand-new model; an existing model's letter comes from counting
  its past releases (first release = A).
- Drawing-only clerical revs add a decimal: C -> C.01 -> C.02. A model change takes the
  next letter and resets the decimal: C.02 -> D.
"""
from __future__ import annotations

import re

ALPHABET = "ABCDEFGHJKMNPRSTUVWXYZ"  # no I, L, O, Q
_REV_RE = re.compile(r"^([A-Z]+)(?:\.(\d{2}))?$")


def letter_for_index(n: int) -> str:
    """0 -> A, 1 -> B, ..., 21 -> Z, 22 -> AA, 23 -> AB, ..."""
    if n < 0:
        raise ValueError("index must be >= 0")
    base = len(ALPHABET)
    out = ""
    n += 1
    while n > 0:
        n -= 1
        out = ALPHABET[n % base] + out
        n //= base
    return out


def index_for_letter(letter: str) -> int:
    """Inverse of letter_for_index. Raises ValueError for I, L, O, Q or bad input."""
    if not letter or any(c not in ALPHABET for c in letter):
        raise ValueError(f"not a valid rev letter: {letter!r}")
    base = len(ALPHABET)
    n = 0
    for c in letter:
        n = n * base + ALPHABET.index(c) + 1
    return n - 1


def letter_for_release_count(releases: int) -> str:
    """Letter for a model with `releases` counted releases (1 -> A). New model: 1."""
    if releases < 1:
        raise ValueError("a released model has at least 1 release")
    return letter_for_index(releases - 1)


def parse(rev: str) -> tuple[str, int]:
    """'C' -> ('C', 0); 'C.02' -> ('C', 2)."""
    m = _REV_RE.match(rev.strip())
    if not m:
        raise ValueError(f"not a valid rev: {rev!r}")
    letter, dec = m.group(1), int(m.group(2) or 0)
    index_for_letter(letter)
    return letter, dec


def fmt(letter: str, dec: int = 0) -> str:
    return letter if dec == 0 else f"{letter}.{dec:02d}"


def next_model_rev(rev: str) -> str:
    """Model change: next letter, decimal reset. 'C.02' -> 'D', 'Z' -> 'AA'."""
    letter, _ = parse(rev)
    return letter_for_index(index_for_letter(letter) + 1)


def next_clerical_rev(rev: str) -> str:
    """Drawing-only change: 'C' -> 'C.01', 'C.01' -> 'C.02'."""
    letter, dec = parse(rev)
    if dec >= 99:
        raise ValueError("clerical decimal would pass .99")
    return fmt(letter, dec + 1)


if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) == 3 and sys.argv[1] in {"model", "clerical"}:
        f = next_model_rev if sys.argv[1] == "model" else next_clerical_rev
        print(f(sys.argv[2]))
    elif len(sys.argv) == 3 and sys.argv[1] == "count":
        print(letter_for_release_count(int(sys.argv[2])))
    else:
        print("usage: revletter.py model C.02 | clerical C | count 7")
        sys.exit(2)
