@echo off
rem Runs CalculiX (ccx) inside WSL Ubuntu from the current Windows folder. Point FreeCAD FEM at this file.
rem Working copy used by FreeCAD: C:\projects\_tools\FreeCAD\ccx_wsl.bat (this repo copy is the reference).
wsl.exe -d Ubuntu --cd "%CD%" -- env OMP_NUM_THREADS=%NUMBER_OF_PROCESSORS% ccx %*
