# FreeCAD FEM smoke check. Runs inside FreeCAD's own Python (freecadcmd), not the repo venv.
# Start it with sim/smoke/run_freecad_check.py: that finds freecadcmd from local.toml [paths] freecad_dir (or FREECAD_DIR)
# and chooses where the result goes (FREECAD_CHECK_OUT). Run by hand, the result lands next to this file.
import os, sys
import FreeCAD, Fem, ObjectsFem  # noqa: F401
import femtools.ccxtools  # noqa: F401

out = os.environ.get('FREECAD_CHECK_OUT', '')
if not out:
    here = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    out = os.path.join(here, 'freecad_check_result.txt')
msg = 'FreeCAD %s FEM workbench import OK\n' % '.'.join(FreeCAD.Version()[:3])
with open(out, 'w') as f:
    f.write(msg)
print(msg.strip() + ' -> ' + out)
sys.exit(0)
