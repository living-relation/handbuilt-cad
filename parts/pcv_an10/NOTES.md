# PCV tube, -10 AN angled variants (pcv_an10)

Built 2026-10-10 from `pcv_adapter/pcv_adapter.py` v3 (Audi 06H103223A, EA888 2.0T). Script: `pcv_an10.py`
(parametric, `build(angle_deg)`; run `../.venv/bin/python pcv_an10.py [angles]`, default 45 and 35).

## Layout
- Stock end unchanged: imported straight from pcv_adapter v3 (z = 0 face .. 18.9 mm, two O-ring grooves,
  21.8 land, 20.4 ball flare). Ball-to-tube 1.5 mm fillet kept, 0.8 mm bore chamfer kept.
- 16.4 mm OD tube bends at 18.9 mm, centreline radius 14 mm (inside radius 5.8 mm).
- Straight AN leg (24.7 mm): 1" hex x 7 mm (30 deg chamfered corners), 19.63 mm thread relief x 1.8 mm,
  7/8-14 UNF cosmetic thread (22.225 mm cylinder, 1 mm lead chamfer), 37 deg flare cone 18.47 -> 16.28 mm nose.
- Bore 13.0 mm constant through the whole part (straight, bend, leg). AS4395 nominal bore is 12.7 mm; 13.0 leaves
  1.64 mm wall at the flare nose (>= 1.5 mm). 0.3 mm chamfer at nose bore.
- Threads are cosmetic: cut/roll 7/8-14 UNF-2A (or UNJF-3A for aerospace) on the 22.225 mm cylinder.

## Results (both one valid solid)
| | 45 deg | 35 deg |
|---|---|---|
| Axial length along stock axis (face -> farthest point) | 52.00 mm | 51.81 mm |
| Limit | 53.0 | 53.0 |
| Side offset (X span) | 38.2 mm | 34.8 mm |
| Volume | 10849 mm3 | 10657 mm3 |
| Mass 6061 / PA12 | 29.3 g / 11.0 g | 28.8 g / 10.8 g |

## -10 AN male spec used (sources)
- SAE AS4395 (supersedes MS33656 / AND10056) Table 1, size 10: tube 0.625, thread .8750-14 UNJF-3A,
  A .500 (bore), B .686 (gauge dia), C .727 (ref, cone max dia), D .641 (nose dia), F .773 (relief dia),
  H .350, J .625 (taken as thread length nose -> relief). https://cmsimg01.71360.com/data/u20631/file/2024041320513429033.pdf
  (letter meanings inferred from the table without the drawing - D/C/F/J interpretation is my best read; verify
  against a real fitting or the AS4395 drawing before machining).
- 37 deg flare (74 included), 7/8-14 UNF = -10 / 5/8 tube: SAE J514 summary, Hoseflex
  https://hoseflex.com/wp-content/uploads/2023/07/Thread-Specification-JIC-37-FLARE-UNO-SAE-J514.pdf
- Hex 1" A/F, min bore .50: Hoke Gyrolok 10AAN10 (-10 AN adapter) table http://mvif.ru/assets/files/pdf/Hoke/GyrolokCW_LW.pdf
- 7/8-14 UNF thread data (major 0.8647-0.8750 in for 3A, minor 0.7899): https://www.machiningdoctor.com/threadinfo/?tid=96

## Open items
- Hex inside corner sits ~4 mm radially clear of the stock ball flare; wrench access is fine but tight on the inside of the bend.
- Bend radius could go up to ~14.9 (45) / ~16.6 (35) mm before hitting the 53 mm limit.
