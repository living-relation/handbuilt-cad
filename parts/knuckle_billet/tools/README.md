# knuckle_billet/tools (generic, reusable)
- `render_views.py` (pvpython): 6 labelled orthographic plain-grey views (front/back/left/right/top/bottom) + a sheet. `xvfb-run -a pvpython tools/render_views.py part.stl out/prefix "Title"`
- `sheet.py`: rebuild the 6-view sheet from the PNGs.
- `make_viewer.py`: STL -> `model.glb` + a single-file offline `viewer.html` (three.js and OrbitControls inlined via an import map of data: URLs, mesh embedded as base64; rotate/zoom/pan). `python tools/make_viewer.py part.stl out_dir "Title"`
- `../tools_vendor/`: three.js r160 `three.module.min.js` + `OrbitControls.js` (MIT licence, (c) three.js authors), used by make_viewer.py.
- `../check_interface.py` now also has `MINWALL` minimum-material rules (bearing bore 6, eye bosses 5, strut clamp bolts 8, caliper ears 6, ABS boss 6, ABS screw 4, flange bolts 4 mm). Set `TAP_PILOT_EAR=8.8` when the caliper ears are modelled as M10x1.25 tap-drill pilots.
