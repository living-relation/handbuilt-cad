# Baseline FEA: knuckle v4b machined solid (estimates)

Mesh: 219516 nodes, 135887 C3D10 tets (CalculiX 2.23). Mass from the exact STEP volume 934,760 mm3: **6061-T6 2.524 kg, 7075-T6 2.627 kg**.

Columns: 'peak' is the max von Mises outside a 3 mm zone around the supports and the bearing ring. 'robust' is the 99.99th percentile, which drops the single-node spikes at sharp unfilleted corners of the scan-derived surface.

| case | peak MPa | robust MPa | max deflection mm 6061 / 7075 | SF yield 6061 peak / robust | SF yield 7075 peak / robust |
|---|---|---|---|---|---|
| bump | 61 | 46 | 0.046 / 0.044 | 4.54 / 6.04 | 8.27 / 11.00 |
| corner | 219 | 167 | 0.133 / 0.128 | 1.26 / 1.65 | 2.30 / 3.01 |
| brake | 373 | 141 | 0.256 / 0.246 | 0.74 / 1.95 | 1.35 / 3.56 |
| combined | 279 | 135 | 0.238 / 0.229 | 0.99 / 2.05 | 1.80 / 3.73 |
| fatigue | 35 | 26 | 0.020 / 0.019 | 7.80 / 10.67 | 14.22 / 19.45 |

Fatigue (1 g + 0.5 g lateral, 10^6 cycles, allowable 82 MPa 6061 / 135 MPa 7075):

- 6061-T6 peak: Goodman R=0 3.67, fully reversed 2.32
- 6061-T6 robust: Goodman R=0 5.02, fully reversed 3.17
- 7075-T6 peak: Goodman R=0 6.18, fully reversed 3.82
- 7075-T6 robust: Goodman R=0 8.46, fully reversed 5.23
