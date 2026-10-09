# Removes the Windows-side sim tools (portable FreeCAD, download, wrappers). Nothing was installed system-wide.
$ST = 'C:\projects\active\handbuilt-models\sim-tools'
Remove-Item -Recurse -Force "$ST\FreeCAD", "$ST\downloads" -ErrorAction SilentlyContinue
Remove-Item -Force "$ST\ccx_wsl.bat", "$ST\gmsh_wsl.bat", "$ST\FreeCAD.bat" -ErrorAction SilentlyContinue
# FreeCAD keeps its settings in %APPDATA%\FreeCAD; remove only if you don't use another FreeCAD:
# Remove-Item -Recurse -Force "$env:APPDATA\FreeCAD"