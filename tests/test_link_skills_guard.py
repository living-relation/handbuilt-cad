"""Guard: scripts/link-skills.ps1 never touches Claude-app-owned (EXCLUDE.txt or marked) skills.
Needs PowerShell (pwsh or Windows powershell); skipped otherwise."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "link-skills.ps1"
PS = shutil.which("pwsh") or shutil.which("powershell")


def _skill(d: Path, name: str, extra: str = ""):
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n{extra}---\nbody\n", encoding="utf-8")


@pytest.mark.skipif(not PS, reason="PowerShell not installed")
def test_app_skills_never_touched(tmp_path):
    src, t1, t2, bak = tmp_path / "src", tmp_path / "claude", tmp_path / "cursor", tmp_path / "bak"
    _skill(src / "harness-design", "harness-design")
    _skill(src / "marked-skill", "marked-skill", "source: harness-design-app\n")
    (src / "EXCLUDE.txt").write_text("harness-design\nst185-pick-parts\n", encoding="utf-8")
    _skill(t1 / "harness-design", "harness-design")
    (t1 / "harness-design" / "today.md").write_text("app edit\n", encoding="utf-8")
    _skill(t2 / "st185-pick-parts", "st185-pick-parts")
    cmd = (f"& '{SCRIPT}' -From '{src}' -Targets '{t1}','{t2}' -BackupRoot '{bak}' "
           "| Format-Table -AutoSize | Out-String -Width 400")
    r = subprocess.run([PS, "-NoProfile", "-NonInteractive", "-Command", cmd], capture_output=True, text=True)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "SKIP harness app skill" in out
    assert (t1 / "harness-design" / "today.md").read_text(encoding="utf-8") == "app edit\n"
    assert (t2 / "st185-pick-parts" / "SKILL.md").is_file()
    assert not (t1 / "marked-skill").exists() and not (t2 / "marked-skill").exists()
    assert not (t2 / "harness-design").exists()
    assert not bak.exists(), out
