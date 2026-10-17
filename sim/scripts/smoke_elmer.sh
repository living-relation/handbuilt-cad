#!/bin/bash
REPO="${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"; export REPO
# Elmer steady heat: Al block 50x20x20 mm, both x-ends at 20 C, uniform heat generation 1e7 W/m^3.
# Exact 1-D answer: Tmax = 20 + Q L^2 / (8 k) = 20 + 1e7*0.05^2/(8*167) = 38.71 C
D=$REPO/sim/smoke/elmer; mkdir -p $D
W=$HOME/sim-runs/elmer-heat; rm -rf $W; mkdir -p $W; cd $W
cat > block.geo <<'EOF'
SetFactory("OpenCASCADE");
Box(1) = {0, 0, 0, 0.05, 0.02, 0.02};
Physical Volume(1) = {1};
Physical Surface(1) = {1};
Physical Surface(2) = {2};
Physical Surface(3) = {3,4,5,6};
Mesh.CharacteristicLengthMax = 0.002;
EOF
gmsh block.geo -3 -format msh2 -o block.msh > gmsh.log 2>&1 && ElmerGrid 14 2 block.msh -autoclean > elmergrid.log 2>&1; echo "mesh exit $?"
cat > case.sif <<'EOF'
Header
  Mesh DB "." "block"
End
Simulation
  Coordinate System = Cartesian
  Simulation Type = Steady state
  Steady State Max Iterations = 1
  Output Intervals = 1
End
Constants
  Stefan Boltzmann = 5.67e-08
End
Body 1
  Target Bodies(1) = 1
  Equation = 1
  Material = 1
  Body Force = 1
End
Material 1
  Heat Conductivity = 167.0
  Density = 2700.0
End
Body Force 1
  Heat Source = 3703.7037
End
Equation 1
  Active Solvers(3) = 1 2 3
End
Solver 1
  Equation = Heat Equation
  Procedure = "HeatSolve" "HeatSolver"
  Variable = Temperature
  Linear System Solver = Iterative
  Linear System Iterative Method = BiCGStab
  Linear System Preconditioning = ILU0
  Linear System Max Iterations = 2000
  Linear System Convergence Tolerance = 1.0e-10
  Steady State Convergence Tolerance = 1.0e-6
End
Solver 2
  Exec Solver = After Simulation
  Equation = SaveScalars
  Procedure = "SaveData" "SaveScalars"
  Filename = "scalars.dat"
  Variable 1 = Temperature
  Operator 1 = max
  Operator 2 = min
End
Solver 3
  Exec Solver = After Simulation
  Equation = ResultOutput
  Procedure = "ResultOutputSolve" "ResultOutputSolver"
  Output File Name = "heat"
  Vtu Format = True
End
Boundary Condition 1
  Target Boundaries(2) = 1 2
  Temperature = 20.0
End
EOF
echo case.sif > ELMERSOLVER_STARTINFO
ElmerSolver case.sif > solver.log 2>&1; echo "ElmerSolver exit $?"
ElmerSolver -v 2>/dev/null | grep -i version | head -1 || grep -i 'version' solver.log | head -2
grep -iE 'ELMER SOLVER|Version' solver.log | head -2
echo "scalars (max, min):"; cat scalars.dat
python3 -c "v=[float(x) for x in open('scalars.dat').read().split()]; print(f'Elmer Tmax={v[0]:.3f} C, Tmin={v[1]:.3f} C; exact Tmax=38.713 C; error {100*(v[0]-38.713)/38.713:+.2f}%')" | tee $D/RESULT.txt
cp case.sif block.geo *.log scalars.dat* $D/ 2>/dev/null; cp -r block/*.vtu $D/ 2>/dev/null; ls block | head