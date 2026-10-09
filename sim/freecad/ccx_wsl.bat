@echo off
rem Runs CalculiX (ccx) inside WSL Ubuntu from the current Windows folder. Point FreeCAD FEM at this file.
wsl.exe -d Ubuntu --cd "%CD%" -- env OMP_NUM_THREADS=%NUMBER_OF_PROCESSORS% ccx %*
