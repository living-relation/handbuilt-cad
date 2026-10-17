#!/bin/bash
set -x
python3 -m venv $HOME/simvenv && $HOME/simvenv/bin/pip install -q --upgrade pip && \
$HOME/simvenv/bin/pip install -q meshio gmsh pygmsh numpy matplotlib vtk ccx2paraview
echo EXIT=$?
$HOME/simvenv/bin/pip list 2>/dev/null | grep -iE 'meshio|gmsh|numpy|matplotlib|ccx2paraview'