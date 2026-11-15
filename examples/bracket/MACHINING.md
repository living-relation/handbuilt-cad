# Sample bracket - machining notes (example)

Shop rules for a CNC part like this one: [`docs/CNC-MACHINING-RULES.md`](../../docs/CNC-MACHINING-RULES.md). The notes below are this example's own plan.

- **Stock:** 6061-T6 bar, 50 x 65 x 50 mm (part is 60 x 40 x 45 plus clean-up).
- **Setups (3-axis):** 1) base bottom face down in a vise: face, profile, drill the two Ø6.6 holes; 2) on its side: drill/ream the Ø8.5 upright hole.
- **Tools:** 10 mm 3-flute end mill (the 6.5 mm inside corner is 1.3× the 5 mm tool radius ✓; not an exact standard size), Ø6.6 and Ø8.5 drills, 90° chamfer tool for the modeled 1 mm × 45° outside chamfer (dimensioned on the drawing; no general edge-break note).
- **Tolerances:** hole positions ±0.05 mm (checked by `tools/features.py` against `spec.json`), general ±0.1 mm. Both are tighter than the Xometry shop default of ±0.005" (±0.127 mm), so they stay on the drawing as a cost flag (`docs/CNC-MACHINING-RULES.md` CNC-TOL).
- **Strength:** see `bracket_fea/summary.json` (500 N side push). Use a safety factor of 2 or more on yield for real parts.
