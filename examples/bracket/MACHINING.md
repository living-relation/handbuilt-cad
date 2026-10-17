# Sample bracket - machining notes (example)

- **Stock:** 6061-T6 bar, 50 x 65 x 50 mm (part is 60 x 40 x 45 plus clean-up).
- **Setups (3-axis):** 1) base bottom face down in a vise: face, profile, drill the two Ø6.6 holes; 2) on its side: drill/ream the Ø8.5 upright hole.
- **Tools:** 10 mm 3-flute end mill (the 6 mm inside fillet must be ≥ the tool radius: 5 mm ✓), Ø6.6 and Ø8.5 drills, 90° chamfer tool for the 1 mm edge break.
- **Tolerances:** hole positions ±0.05 mm (checked by `tools/features.py` against `spec.json`), general ±0.1 mm.
- **Strength:** see `bracket_fea/summary.json` (500 N side push). Use a safety factor of 2 or more on yield for real parts.
