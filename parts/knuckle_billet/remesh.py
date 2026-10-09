import pymeshlab, trimesh, sys
L = float(sys.argv[1])
ms = pymeshlab.MeshSet(); ms.load_new_mesh('baseline/v4b_fixed.stl')
ms.meshing_isotropic_explicit_remeshing(targetlen=pymeshlab.PureValue(L), iterations=6, featuredeg=35, adaptive=True)
ms.meshing_repair_non_manifold_edges(); ms.meshing_close_holes(maxholesize=30)
ms.save_current_mesh('baseline/v4b_remesh.stl')
m = trimesh.load('baseline/v4b_remesh.stl'); print('remeshed', len(m.faces), m.is_watertight, round(m.volume))
