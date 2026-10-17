import sys, FreeCAD, Fem, ObjectsFem
import femtools.ccxtools
open(r'C:\projects\active\handbuilt-models\sim-tools\smoke\freecad_check_result.txt','w').write('FreeCAD %s FEM workbench import OK\n' % '.'.join(FreeCAD.Version()[:3]))
sys.exit(0)
