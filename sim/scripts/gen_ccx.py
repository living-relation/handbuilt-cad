# Generates two tiny CalculiX decks: cantilever (C3D8I hexes) and steady heat block (DC3D8).
import sys, os
out = sys.argv[1]
def grid(L, b, h, nx, ny, nz):
    nodes = {}; nid = 0; idx = {}
    for k in range(nz+1):
        for j in range(ny+1):
            for i in range(nx+1):
                nid += 1; idx[(i,j,k)] = nid; nodes[nid] = (L*i/nx, b*j/ny, h*k/nz)
    els = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                els.append([idx[(i,j,k)], idx[(i+1,j,k)], idx[(i+1,j+1,k)], idx[(i,j+1,k)],
                            idx[(i,j,k+1)], idx[(i+1,j,k+1)], idx[(i+1,j+1,k+1)], idx[(i,j+1,k+1)]])
    return nodes, els, idx
def write(path, etype, nodes, els, idx, nx, ny, nz, body):
    with open(path, 'w') as f:
        f.write('*NODE, NSET=NALL\n')
        for n, (x,y,z) in nodes.items(): f.write(f'{n}, {x:.6f}, {y:.6f}, {z:.6f}\n')
        f.write(f'*ELEMENT, TYPE={etype}, ELSET=EALL\n')
        for e, c in enumerate(els, 1): f.write(f'{e}, ' + ', '.join(map(str, c)) + '\n')
        def nset(name, sel):
            ids = [idx[(i,j,k)] for k in range(nz+1) for j in range(ny+1) for i in range(nx+1) if sel(i,j,k)]
            f.write(f'*NSET, NSET={name}\n'); [f.write(f'{n},\n') for n in ids]; return ids
        fixed = nset('FIX', lambda i,j,k: i == 0)
        tip = nset('TIP', lambda i,j,k: i == nx)
        body(f, tip)
# Cantilever 100 x 10 x 10 mm steel, 100 N tip load in -Z
L, b, h, P, E, nu = 100.0, 10.0, 10.0, 100.0, 210000.0, 0.3
nx, ny, nz = 40, 4, 4
nodes, els, idx = grid(L, b, h, nx, ny, nz)
def beam(f, tip):
    f.write(f'*MATERIAL, NAME=STEEL\n*ELASTIC\n{E}, {nu}\n*SOLID SECTION, ELSET=EALL, MATERIAL=STEEL\n')
    f.write('*BOUNDARY\nFIX, 1, 3\n*STEP\n*STATIC\n*CLOAD\n')
    # consistent-ish: equal share per tip node (fine for a smoke test)
    for n in tip: f.write(f'{n}, 3, {-P/len(tip):.8f}\n')
    f.write('*NODE PRINT, NSET=TIP\nU\n*NODE FILE\nU\n*EL FILE\nS\n*END STEP\n')
write(os.path.join(out, 'beam.inp'), 'C3D8I', nodes, els, idx, nx, ny, nz, beam)
I = b*h**3/12; d = P*L**3/(3*E*I); G = E/(2*(1+nu)); ds = P*L/((5/6)*G*b*h)
open(os.path.join(out, 'beam_handcalc.txt'), 'w').write(f'Euler-Bernoulli tip deflection PL^3/3EI = {d:.5f} mm\nwith Timoshenko shear term = {d+ds:.5f} mm\n')
# Heat: aluminium block 50 x 20 x 20, T=100 C at x=0, T=20 C at x=50, k=0.167 W/mm.K
Lh, nxh = 50.0, 10
nodes, els, idx = grid(Lh, 20.0, 20.0, nxh, 2, 2)
def heat(f, tip):
    f.write('*MATERIAL, NAME=AL\n*CONDUCTIVITY\n0.167\n*SOLID SECTION, ELSET=EALL, MATERIAL=AL\n')
    f.write('*INITIAL CONDITIONS, TYPE=TEMPERATURE\nNALL, 20.\n')
    f.write('*STEP\n*HEAT TRANSFER, STEADY STATE\n*BOUNDARY\nFIX, 11, 11, 100.\nTIP, 11, 11, 20.\n')
    f.write('*NODE PRINT, NSET=NALL\nNT\n*NODE FILE\nNT\n*EL FILE\nHFL\n*END STEP\n')
write(os.path.join(out, 'heat.inp'), 'DC3D8', nodes, els, idx, nxh, 2, 2, heat)
print('decks written')