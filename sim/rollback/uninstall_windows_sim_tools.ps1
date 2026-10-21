# Removes the Windows-side sim tools (portable FreeCAD, its download and the wrapper .bat files). Nothing was installed system-wide.
$T = if ($env:FREECAD_DIR) { $env:FREECAD_DIR } else { throw 'set FREECAD_DIR to the FreeCAD folder' }          # FreeCAD app, _download\ (7z), FreeCAD.bat, ccx_wsl.bat, gmsh_wsl.bat
Remove-Item -Recurse -Force $T -ErrorAction SilentlyContinue
# FreeCAD keeps its settings in %APPDATA%\FreeCAD; remove only if you don't use another FreeCAD:
# Remove-Item -Recurse -Force "$env:APPDATA\FreeCAD"