"""Generic: STL -> GLB + self-contained offline HTML viewer (three.js + OrbitControls inlined, mesh embedded as base64).
Usage: python tools/make_viewer.py <in.stl> <out_dir> [title]   (writes <out_dir>/model.glb and <out_dir>/viewer.html)"""
import sys, os, base64, json, numpy as np, trimesh
stl, out, title = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else 'model')
V = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools_vendor')
m = trimesh.load(stl); m.merge_vertices()
os.makedirs(out, exist_ok=True)
g = m.copy(); g.visual = trimesh.visual.ColorVisuals(g, face_colors=[184, 189, 196, 255]); g.export(os.path.join(out, 'model.glb'))
c = m.bounds.mean(0); v = (m.vertices - c).astype(np.float32); f = m.faces.astype(np.uint32)
b64 = lambda a: base64.b64encode(a.tobytes()).decode()
three = open(os.path.join(V, 'three.module.min.js')).read()
orbit = open(os.path.join(V, 'OrbitControls.js')).read()
d64 = lambda s: 'data:text/javascript;base64,' + base64.b64encode(s.encode()).decode()
html = f"""<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>
<style>html,body{{margin:0;height:100%;background:#fff;font-family:sans-serif}}#t{{position:absolute;left:10px;top:8px;color:#222}}</style>
<script type="importmap">{json.dumps({"imports": {"three": d64(three), "three/addons/OrbitControls.js": d64(orbit)}})}</script></head>
<body><div id="t">{title} - drag to rotate, wheel to zoom, right-drag to pan. Dimensions mm. {len(f)} triangles.</div>
<script type="module">
import * as THREE from 'three'; import {{ OrbitControls }} from 'three/addons/OrbitControls.js';
const dec = s => Uint8Array.from(atob(s), c => c.charCodeAt(0)).buffer;
const pos = new Float32Array(dec("{b64(v)}")), idx = new Uint32Array(dec("{b64(f)}"));
const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setIndex(new THREE.BufferAttribute(idx, 1)); geo.computeVertexNormals();
const scene = new THREE.Scene(); scene.background = new THREE.Color(0xffffff);
const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({{color: 0xb8bdc4, metalness: 0.25, roughness: 0.55}})); scene.add(mesh);
scene.add(new THREE.HemisphereLight(0xffffff, 0x777777, 1.6)); const dl = new THREE.DirectionalLight(0xffffff, 1.6); dl.position.set(300, -400, 500); scene.add(dl);
const r = geo.boundingSphere ? geo.boundingSphere.radius : (geo.computeBoundingSphere(), geo.boundingSphere.radius);
const cam = new THREE.PerspectiveCamera(35, innerWidth / innerHeight, 1, 10000); cam.position.set(r * 1.8, -r * 1.6, r * 2.2); cam.up.set(0, -1, 0);
const ren = new THREE.WebGLRenderer({{antialias: true}}); ren.setSize(innerWidth, innerHeight); document.body.appendChild(ren.domElement);
const ctl = new OrbitControls(cam, ren.domElement); ctl.target.set(0, 0, 0); ctl.update();
addEventListener('resize', () => {{ cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix(); ren.setSize(innerWidth, innerHeight); }});
(function loop() {{ requestAnimationFrame(loop); dl.position.copy(cam.position); ren.render(scene, cam); }})();
</script></body></html>"""
open(os.path.join(out, 'viewer.html'), 'w').write(html); print('viewer', os.path.getsize(os.path.join(out, 'viewer.html')) // 1024, 'KB')
