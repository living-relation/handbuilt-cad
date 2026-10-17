SetFactory("OpenCASCADE");
Box(1) = {0, 0, 0, 0.05, 0.02, 0.02};
Physical Volume(1) = {1};
Physical Surface(1) = {1};
Physical Surface(2) = {2};
Physical Surface(3) = {3,4,5,6};
Mesh.CharacteristicLengthMax = 0.002;
