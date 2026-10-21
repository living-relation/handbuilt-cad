# ST185 rear knuckle: load cases (ESTIMATES)

Every number here is an engineering estimate for sizing a billet part. None of it is Toyota data, and none of it replaces a proper engineering review of a suspension part. The car is a 1993 Celica GT-Four / All-Trac Turbo (ST185), driven fast on the road on slicks, with coilovers and solid (spherical/rigid) joints everywhere. The numbers are produced by `loads.py` and saved in `loads.json`.


> **Correction (chunk 16, from owner):** this is the **RIGHT (passenger) rear** knuckle. The two side eyes are the **control (lateral) arms**; the 40 mm bottom eye (called 'top eye' / EYET in the scripts, axis ~Z = lateral bolt) is the **TRAILING ARM**, not a strut rod. The CalculiX support was checked: EYET is fixed in X only (DOF 1), and X is the fore-aft axis of the knuckle frame, i.e. along the trailing arm. That matches a two-force trailing arm, so no load-case or support change was needed and earlier results stand. Chunk 17: +X is forward (right-handed frame with -Y up and +Z inboard on a RH part), so braking was not mirrored.

## Vehicle data

| Item | Value | Source / assumption |
|---|---|---|
| Curb weight | 1460 kg | turbocelica.nl ST185 spec (AU/EU/US GT-Four); [1] |
| Design mass | **1560 kg** | curb + ~100 kg driver and gear (estimate) |
| Gross vehicle weight, axle split | 1890 kg (1015 front / 875 rear) | turbocelica.nl, CS/EU; shows the rear axle is rated for 875 kg [1] |
| Rear share of mass | **40 %** | estimate (transverse engine, nose-heavy AWD; the GVW split is 46 % rear with a full load) |
| Static rear corner load Fz0 | **3.06 kN** (312 kg) | 1560 x 0.40 / 2 x 9.81 |
| Wheelbase | 2525 mm | [1] |
| Rear track | 1445 mm | [1] (wide-body export cars) |
| CG height | **500 mm** | estimate for a lowered 1300 mm-tall coupe |
| OE wheel / tyre | 15x6.5JJ +39, 215/50R15 | [1] |
| Slick loaded radius | **285 mm** | estimate for a ~23 in diameter 15 in slick |
| Contact-patch lateral position | **z = +20 mm** in the knuckle frame | estimate: ET+39 puts the wheel centre plane ~39 mm inboard of the hub face, close to the bearing centre (z 29.75). Needs the real hub face and wheel offset. |

## Rear suspension layout and how sure I am

The ST185 rear is a MacPherson strut on a one-piece "rear axle carrier" (this knuckle). It carries two lateral suspension arms (No.1, the front arm, and No.2, the rear arm with the toe cam) and a strut rod (trailing rod) [2][3]. The parts list shows 2 carrier-to-strut bolts with nuts (90105-15001 / 90179-15001), M14 nuts on the arms (90170-14006) and M12 strut-rod bolts (90119-12131) [2].

Knuckle frame (from v4b): Z is the hub axis (+Z inboard, z = 0 is the outboard hub face). -Y points up (strut side) and +X points FORWARD (proved for the RH part in chunk 17, see below).

| v4b feature | Assigned to | Confidence |
|---|---|---|
| 2 X-axis holes 14.3 / 14.0 mm at y -147.5 / -79 (68.5 mm apart, above the hub) | **Strut / coilover clamp bolts** (strut bracket clamps the carrier, 2 bolts) | medium-high: 2 parallel bolts above the hub, matches the 2 carrier bolts in the parts list |
| Left eye (axis X, OD 46, bore 35, len 26) and right eye (axis tilted 13.6 deg, OD 46.5, bore 35.5) at the bottom | **No.1 and No.2 lateral arms** (bushing eyes, bolt axis fore-aft) | medium-high on "lateral arms"; which eye is No.1 vs No.2 is unknown |
| Top eye (axis ~Z, OD 52, bore 40, len 40) at the very bottom (y +138) | **Trailing arm** (confirmed by owner, bolt axis lateral) | medium: the only eye with a lateral axis. Named "top eye" only because of the scan view. |
| 2 ear holes 10 / 9 mm, axis Z, both at r = 105 mm from the hub axis | **Brake caliper bracket bolts** | low-medium: same radius suggests a caliper, but the hole sizes differ and the spacing (140 mm chord) is wide. owner to confirm. |
| 4 flange holes 10.5 mm at r ~ 58 mm | Backing plate / parking-brake (drum-in-hat) / dust shield | medium |
| Side boss hole 17 mm, axis X, at hub height | ABS speed sensor bore (aims radially at the tone ring) | low-medium |

## Supports (how the knuckle is held in the FEA)

Solid joints mean no bushing compliance, so the supports are treated as rigid:

- **Strut clamp holes: fixed in all 3 directions.** A coilover strut with a solid top mount is a stiff cantilever. It carries the spring and damper force and the strut bending.
- **Lateral-arm eyes: fixed in Z only (along the arm).** With spherical joints at both ends each arm is a two-force member.
- **Trailing-arm eye: fixed in X only (along the trailing arm, fore-aft).** Same two-force reasoning.
- **Load path:** loads go in at the tyre contact patch and pass through a rigid ring on the bearing seat (74 mm, z 13.5-46), which stands in for the steel bearing outer race. The ring gets the contact-patch force plus its moment about the hub centre.
- **Brake torque** goes rotor, caliper, ear holes. It shows up as tangential forces on the two ear holes (half each), not through the bearing.

## Load cases

Forces act on the tyre from the ground: Fz up, Fy toward the car centre (outer wheel), Fx rearward under braking. Fz0 = 3.06 kN.

| Case | Definition | Fz kN | Fy kN | Fx kN | Brake torque Nm |
|---|---|---|---|---|---|
| 1 Bump | 4.0 g x 1.25 impact factor | 15.30 | 0 | 0 | 0 |
| 2 Cornering | 1.8 g, outer wheel incl. lateral load transfer (+3.81 kN); Fy = 1.8 x Fz | 6.87 | 12.37 | 0 | 0 |
| 3 Braking | 1.7 g x static corner load | 3.06 | 0 | 5.20 | 1483 |
| 4 Combined | 1.5 g bump + 1.5 g lateral (outer wheel, +3.18 kN transfer) + 1.2 g braking | 7.77 | 9.36 | 3.67 | 1047 |
| 5 Fatigue | 1 g + 0.5 g lateral, outer wheel, ~10^6 cycles | 4.12 | 2.06 | 0 | 0 |

Reasoning:

- **Bump 3.5-4 g plus impact.** Solid joints and a stiff slick sidewall remove most of the compliance that softens a pothole or kerb strike, so I used the top of the range (4 g) and a 1.25 impact factor, giving 5.0 x Fz0. The **coilover damper spike** (estimated ~6 kN at ~3 m/s shaft speed with stiff valving) comes into the knuckle through the strut clamp. In this model the clamp is a support, so the spike is part of that support reaction, and the 15.3 kN vertical case already exceeds the static spring load plus the spike (3.1 + 6 kN).
- **Cornering 1.7-1.8 g on slicks.** I used 1.8 g. The whole rear-axle mass transfers to the outer wheel through the CG height (conservative: it ignores roll-stiffness split and unsprung mass). The outer tyre then makes 1.8 x its own load sideways.
- **Braking 1.5-1.7 g.** I used 1.7 g on the *static* rear load. Under real hard braking the rear unloads (about -2.6 kN per corner at 1.7 g), so this is conservative. It also covers braking over bumps and trail-braking.
- **Combined.** This is as specified (1.5 / 1.5 / 1.2 g), applied to the outer wheel with the lateral load transfer of 1.5 g.
- **Fatigue.** With solid joints, the bump and corner cycles go straight into the part. I treated the 1 g + 0.5 g lateral case as a 0 -> peak cycle (R = 0) repeated 10^6 times, checked with Goodman. Fully reversed is shown too, as a worst-case bound.
- **Not modelled:** drive torque (AWD; the rear diff torque passes through the CV joint and the hub, not the knuckle, apart from bearing friction), stabilizer-bar link loads (on the No.1 arm, not the knuckle), unsprung-mass inertia, and thermal loads from the brakes.

## Materials

| Alloy | E GPa | Yield MPa | UTS MPa | Density g/cm3 | Fatigue strength MPa (R=-1, 5x10^8, RR Moore) | Design fatigue allowable at 10^6 (x 0.85 machined surface / size) |
|---|---|---|---|---|---|---|
| 6061-T6 | 68.9 | 276 | 310 | 2.70 | 96.5 | **82** |
| 7075-T6 | 71.7 | 503 | 572 | 2.81 | 159 | **135** |

Values are typical ASM / MatWeb handbook numbers [4]. Aluminium has no true endurance limit. Using the 5x10^8 strength as the 10^6 allowable, with a surface/size knock-down, is a deliberately conservative estimate. Plate properties fall in thick sections (7075-T651 short-transverse yield is lower), so order plate with certified properties.

## Sources

1. turbocelica.nl, ST185 specifications: http://www.turbocelica.nl/st185specifications.htm
2. ToyoDIY parts catalogue, 1990/1991 Celica ST185 48-04 rear spring and shock absorber: https://www.toyodiy.com/parts/p_E_1991_TOYOTA_CELICA_ST185L-BLMVZG_4804.html
3. Toyota IRS rear suspension service article (Celica: one-piece axle carrier, 2 arms, strut rod, stabilizer): https://www.shoarmateam.nl/upload/Celica%20turbo/ST165/Toyota%20Celica%201989/suspension%20rear.pdf
4. ASM Aerospace Specification Metals / MatWeb data sheets for 6061-T6 and 7075-T6.

## Strut clamp extent (owner, 2026-10-09)
The strut clamp bracket covers only the 2 strut bolt holes (y -147.5 and -79, axis X) and reaches 12 mm below the bottom bolt toward the hub (y ≈ -67 from the bolt centre). Clamp load goes into the tongue's x = ±15 faces only over that zone. The tongue between the clamp zone and the flange carries the strut moment unsupported.

## Chunk 17 load geometry: 9 in ET-35 wheel, RH frame, suspension positions (ESTIMATES)

**Frame / forward direction (RH knuckle).** The scan/CAD frame is right-handed. -Y is up (strut on top), and +Z is inboard (hub face outboard at z = 0). On a RIGHT knuckle inboard means toward the car's left. A right-handed frame then forces X = Y x Z = down x left = **forward**. So +X is forward, and the trailing rod 48780A runs from the bottom eye toward +X (EPC 480442-E). Braking ground force on the tyre = -X, and the brake torque on the knuckle is reacted at the caliper ears with the matching sign. That is what the scripts already did, so **nothing was mirrored and there is no fix**. The caliper ears sit at -X (behind the axle), which is consistent.

**Moment sign check (chunk 16 "stress went down when the load moved outboard").** This is not a bug. In the y-z plane the moment of the contact-patch force about the hub centre is Mx = R*Fy_lat + (zp - zc)*Fz. The lateral force at the ground (inboard, +Z, at y = +R) and the vertical load outboard of the bearing (zp < zc) give **opposite** moments, the usual bearing-moment term Fz*a - Fy*R. Moving the tyre outboard therefore *reduces* the net moment in cornering and the corner-heavy combined case, and *increases* it in pure bump and braking. The chunk-16 bump "drop" (713 to 236 MPa) was a raw singular peak at stock; the 99.9th percentile actually rose from 46 to 88 MPa. Only robust (singular-excluded) values are compared from now on.

**Hub mounting face (picked: z = -42 mm, i.e. 42 mm outboard of the knuckle outboard face).**
- Toyota-based estimate: stock ST185 wheel 15x6.5 ET39 (turbocelica.nl spec table; alltrac.net wheel FAQ), rear track 1445 mm. The earlier contact patch at z = +20 (an estimate) puts the hub face at 20 - 39 = **-19 mm**.
- Strut-clearance calibration (owner: a 9.5 in ET-20 wheel leaves about 3 mm to the strut). Rim overall width = nominal + 25 mm for the bead flanges (assumption), so 266.3 mm for a 9.5 in rim. The inner rim edge is W/2 + ET = 133.2 - 20 = 113.2 mm inboard of the hub face. The strut tube sits on top of the clamp tongue (tongue z 72..116, clamp bolts at z 94-96), so its centreline is taken at z = 94. With an assumed tube OD of about 52 mm, its outboard surface is at z = 68. Hub face = 68 + 3 - 113.2 = **-42 mm**.
- The two disagree by 23 mm. I use the **calibration value (-42 mm)**: it rests on owner's measured clearance and is also the conservative one for bump and braking (longer arm). With -19 mm instead, the design load point would move 23 mm inboard.
- Design wheel 9 in ET-35: wheel centre = tyre centre = hub face - 35 (negative ET is outboard) = **z = -77 mm** (stock was +20, so 97 mm outboard). Moment arm from the bearing centre (z = 29.75) is 107 mm (was 10 mm). The track grows by about 2 x (39 + 35) = 148 mm relative to stock (about 1593 mm). Load transfer is kept at the stock track (conservative). Loaded radius is kept at 285 mm (tyre size not given).
- Inner-rim clearance of the design wheel: (228.6 + 25)/2 - 35 = 91.8 mm inboard of the hub face, versus 113.2 mm for the 9.5 in ET-20. So the 9 in ET-35 clears the strut by about **24 mm** (3 + 21.4).

**Suspension positions (POS in fea_iter.py).** Each two-force link is rotated about its inboard pivot. Assumptions: wheel travel +/-55 mm from ride height; lateral arms about 400 mm long, trailing rod about 450 mm long.
| Position | Lateral arms (rise toward inboard pivot) | Trailing rod (toward front pivot) | Cases run |
|---|---|---|---|
| full bump | 0 deg (horizontal, the old model) | 7 deg down to the pivot | bump |
| mid (outer wheel, partly compressed) | 5 deg | 3.5 deg down | cornering, combined |
| ride height | 9 deg (photos of the arms show 8-10 deg) | level | cornering, braking, combined, fatigue |
| full droop | 17 deg | 7 deg up | braking (rear lifts under braking) |
The strut clamp stays fully fixed in all positions, so the change in strut axis angle (about 1-2 deg) does not change the support. Damper top-out at droop is not modelled separately; the droop braking check stands in for it.
