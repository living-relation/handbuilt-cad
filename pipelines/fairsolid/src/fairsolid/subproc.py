"""Run stage bodies in isolated interpreters.

Two reasons stages are subprocesses rather than function calls:

1. Resumability - each stage's output lands on disk, so a run can restart
   mid-pipeline without redoing expensive work.
2. CadQuery's OCCT bindings segfault in their static destructors at
   interpreter shutdown. The geometry is fine and fully written by then;
   only the exit code is garbage (139). Any CadQuery body therefore ends
   with os._exit(0), which skips the C++ teardown. See CQ_EPILOGUE.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

# Appended to CadQuery snippets so a clean run reports exit 0 rather than
# SIGSEGV from OCCT teardown. Verified: without this every successful
# CadQuery stage returns 139.
CQ_EPILOGUE = textwrap.dedent(
    """
    import os as _os, sys as _sys
    _sys.stdout.flush()
    _sys.stderr.flush()
    _os._exit(0)
    """
)


class StageError(RuntimeError):
    """A stage subprocess failed."""


def run_python(
    body: str,
    *,
    cadquery: bool = False,
    cwd: Path | None = None,
    timeout: int = 900,
) -> str:
    """Execute `body` in a fresh interpreter, return its stdout.

    Set cadquery=True for any body that imports cadquery, so the OCCT
    teardown crash is bypassed instead of being read as a stage failure.
    """
    source = body + (CQ_EPILOGUE if cadquery else "")
    proc = subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise StageError(
            f"stage subprocess exited {proc.returncode}\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )
    return proc.stdout


def run_json(body: str, **kw) -> dict:
    """Run `body`, parse the last stdout line as JSON.

    Stages print human-readable progress freely and emit exactly one
    machine-readable line last, prefixed with RESULT:.
    """
    out = run_python(body, **kw)
    for line in reversed(out.strip().splitlines()):
        if line.startswith("RESULT:"):
            return json.loads(line[len("RESULT:"):])
    raise StageError(f"stage produced no RESULT: line\n{out}")


def run_module(module: str, args: list[str], *, timeout: int = 1800) -> dict:
    """Run `python -m module args...` in a fresh interpreter, parse RESULT:.

    Preferred over run_json for real stages: the stage stays an importable,
    testable module instead of a string blob.
    """
    proc = subprocess.run(
        [sys.executable, "-m", module, *args],
        capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise StageError(
            f"{module} exited {proc.returncode}\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )
    for line in reversed(proc.stdout.strip().splitlines()):
        if line.startswith("RESULT:"):
            return json.loads(line[len("RESULT:"):])
    raise StageError(f"{module} produced no RESULT: line\n{proc.stdout}")


def emit(payload: dict) -> None:
    """Hand a stage's result back to the pipeline, then exit hard.

    The hard exit is not an optimisation, it is the fix for OCCT teardown.
    Stages that touch CadQuery finish their work, write their files and print
    RESULT correctly, and then crash while C++ static destructors run - as a
    segfault (139) on some paths and as heap corruption (0xC0000374) on
    others. Either way the parent reads a non-zero exit code and throws away a
    perfectly good result.

    Exiting via os._exit skips interpreter shutdown entirely, so the
    destructors never run. That is safe here because a stage subprocess exists
    only to write files and print one line, and emit() is always its last act -
    there is nothing left to flush but stdout and stderr, which are flushed
    explicitly below.
    """
    print("RESULT:" + json.dumps(payload))
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
