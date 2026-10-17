# Fairsolid plan: scans to smooth solids

App name: **Fairsolid** (chosen by the user 2026-10-08; "fairing" is the CAD word for smoothing
curves and surfaces). It replaces the project's original working name, which is already taken elsewhere. Web check
found no software, company, package or CAD add-on using it (not a legal trademark search).

Status: in progress. Decisions are added here as the user approves each part.
Branch: `surface-fit`

## Why
Scanned meshes carry scan texture and noise. A workable model must be a smooth solid that
never inherits that texture. Instead of copying the mesh, Fairsolid will fit clean surfaces
(planes, cylinders, cones, spheres and smooth freeform patches) to the scan, then trim and
knit them into one closed solid.

## Plan outline
1. Goal and pass test - DECIDED (below)
2. Splitting the scan into faces (walls, holes, shells, curved areas) - DECIDED (below)
3. Fitting flat and round surfaces (planes, cylinders, cones, spheres) - DECIDED (below)
4. Fitting curved freeform surfaces (smooth patches) - DECIDED (below)
5. Slices: section cuts to measure curvature and guide the patches - DECIDED (below)
6. Trim and knit into one closed smooth solid - DECIDED (below)
7. Output: STEP, optionally pushed into Fusion as editable surfaces - DECIDED (below)
8. User interface and workflow - DECIDED (below, the user left the UI to Grok Bot)
9. Test parts and order - DECIDED (below, the user left the order to Grok Bot)
10. Reference scan mode (open surfaces for designing new parts) - DECIDED (below)
11. Assistant (built-in helper, MCP server for agent apps, optional chat) - DECIDED (below)

## 1. Goal and pass test (decided 2026-10-08)
A result passes when all of these hold:
- It is one closed, smooth solid. No scan texture or faceting is carried into the model.
- Every fitted surface is within the size-based tolerance below.
- Overall dimensions match the scan within the same tolerance.

Tolerance by part size (starting values, to be tuned on real scans):

| Part type | Tolerance |
|---|---|
| Small machined parts | 0.02 to 0.1 mm |
| Large objects | 0.1 to 0.2 mm |

Notes:
- Small machined parts are rarely scanned; they are usually measured with calipers and modeled
  by hand. The tight band applies when one is scanned.
- These bands are targets, not hard limits. If real scans can't reach them, loosen them as needed and record the value actually used per part.
- The old pass bar (0.5 mm against raw scan points) is retired.
- Tolerance is measured as the fitted surface against the averaged scan surface, not against
  every raw scan point (confirmed in part 3). The user can set and adjust the range.

## 2. Splitting the scan into faces (decided 2026-10-08)
- Automatic by default. When it guesses wrong, the user can fix areas by hand (merge two areas,
  split one, or change an area's label). Manual fixes are saved with the run so a re-run keeps them.
- The mesh is grouped into areas by surface direction and how sharply it bends.
- Each area is labeled flat, round (hole, boss, shaft) or freeform. Outer walls, inner walls,
  shells and holes are all found this way.
- A colored preview image shows every area before fitting, for a quick visual check.
- Small details (fillets, chamfers, text, logos) are ignored at first. They are bridged over
  by the neighbouring surfaces, and can be added in a later pass.

## 3. Fitting flat and round surfaces (decided 2026-10-08)
- Snapping is on: angles and hole sizes snap to clean values when within tolerance.
- Hole sizes can snap to metric or inch standard sizes. Which one is an option: the process
  makes a guess, but the user makes the final pick based on the model's units and the CAD
  space they are working in.
- Concern raised by the user: the unit choice must not rescale the scan. It should only decide
  which standard sizes are used for snapping.
- Non-planar faces (cylinders, cones, spheres) that are nearly concentric or nearly collinear
  are made exactly concentric or collinear, or otherwise constrained to each other.
- Planar faces that are nearly parallel or nearly square are made exactly parallel or square.
- Guards against rescaling:
  - The scan is read once at its true size and that scale is locked, separate from the unit
    choice. (Scan files like STL carry no units, so this is where a 25.4x error would start.)
  - The unit choice only changes which standard sizes are used for snapping and how numbers
    are shown. It never scales geometry.
  - The finished model's overall size is checked against the scan. If it is off, especially
    by about 25.4x, the run stops with a warning.
- Each area is fitted with a best-fit regression. The user decides how many points, or which
  regression settings, to use per surface, based on how noisy the scan is or where the
  trouble spots are.
- Tolerance is measured against the averaged scan surface, not raw points.
- The user sets the tolerance range and can adjust it as needed if a fit doesn't resolve or
  work out well.

## 4. Fitting curved freeform surfaces (decided 2026-10-08)
Approach: each freeform area gets a smooth spline patch fitted to the averaged scan. The patch
has a limited number of control points, so it cannot follow scan bumps, which keeps texture out.

- Patch stiffness is user selectable, as a slider or a range.
- Joints between patches that are more than a certain distance from a good fit are flagged.
  For flagged joints, the user picks the joint type (tangent: no crease, may show a faint
  line in reflections; curvature: no visible line, harder to fit).
- Joints that are not flagged start with the suggested default (tangent). After seeing the
  model and how the patches fit, the user can switch any joint individually as needed, or
  leave them as is.
- The flag distance is tied to the user's tolerance range: a joint is flagged when its gap is
  bigger than that range. The user can still change it.

## 5. Slices (decided 2026-10-08)
Approach: the scan is cut into thin cross sections. Each one is smoothed into a clean 2D
curve, and those curves are used to estimate overall curvature and guide the part 4 patches.

- Slice direction and spacing are set with sliders. The starting values are the tool's own
  best-fit choice; the user approves them or adjusts.
- The smoothed slice curves guide the patch fitting and are also kept as editable sketches.
  In Fusion they are hidden at first.

## 6. Trim and knit (decided 2026-10-08)
Approach: each fitted surface is trimmed where it meets its neighbours, and the pieces are
stitched into one closed solid.

- Gaps are filled automatically first. The user can choose how a gap is filled afterwards,
  or when it can't be filled automatically.
- If the solid still won't close, the user gets the open surface body plus a list of problem
  spots, with several options to rough-fill the gaps before modifying it.
- the user's idea for finishing in Fusion: use Fusion's newer sketch-based surface fitting tool.
  Likely candidates are Create Mesh Section Sketch with Fit Curves To Mesh Section (built in),
  to be confirmed.

## 7. Output (decided 2026-10-08)
- A STEP file of the solid, always.
- Optionally, an STL of the smooth result (for printing).
- Optionally, a push into Fusion as editable bodies, with the slice sketches hidden.
- A short report: the user's settings, every snap, flagged joints, and how far each surface
  ended up from the scan.

## 8. User interface and workflow (decided 2026-10-08, UI design left to Grok Bot)
- Runs locally on the PC as a page in the browser with a 3D view, started from a desktop
  shortcut. No internet needed.
- One screen per step, with Back and Next, in this order:
  1. Load scan (true size locked).
  2. Units and tolerance (tool suggests, user confirms or changes).
  3. Split check (colored 3D preview; click areas to merge, split or relabel).
  4. Slices (direction and spacing sliders, starting at the tool's best guess).
  5. Fit (points, regression settings and stiffness per surface; trouble spots highlighted).
  6. Joints and gaps (flagged items listed and highlighted; pick joint type or fill method).
  7. Export (STEP, optional STL, optional Fusion push, report).
- Every setting and manual fix is saved with the run, so reopening or re-running keeps them.
- A color map on the model shows how far each surface is from the scan at every step.
- Mockup approved by the user on 2026-10-08: `docs/ui-mockup/` (open `index.html`, or see the PNGs).
  The app name in the mockup is a placeholder; the app is now named Fairsolid.

## 9. Test parts and order (decided 2026-10-08, order left to Grok Bot)
Picked from earlier Fairsolid runs (made under the original name), simplest first, so each step adds one new challenge:
1. Pedal adapter: lots of flat faces and holes (about 23 flat, 9 round). Tests flat and round
   fitting, snapping, concentric holes and knitting. Its earlier crash must be fixed first.
2. Knuckle: many round features (about 35) mixed with cast curves. Tests round faces together
   with freeform patches.
3. Bezel: large and mostly curved. Tests freeform patches, slices and joints.
4. Oil catch bracket scan: not a part. It is a scan of the space between the firewall and
   engine, used to design a bracket. It is the test for reference scan mode (part 10).
Dash housing and fuel pump are extra tests once these pass.

## 10. Reference scan mode (decided 2026-10-08)
Some scans are not parts. Example: the oil catch bracket scan is the volume of space between
the firewall and engine, scanned so a new bracket can be modeled to fit that space.

- A setting picks how the scan is processed: solid part (parts 1 to 7) or reference scan.
- In reference scan mode the result stays an open surface or separate (fractured) surfaces.
  It is not forced into a closed solid.
- It still gets reference geometry for modeling: planes, origin, orientation, points, and
  similar datums.
- It offers to knit or patch surfaces in a region, to make modeling there easier.
- Orientation of the scan is part of the process every time, in both modes. It is automatic
  (for example, the biggest flat face to the ground and the main directions to X, Y and Z),
  and the user can edit it by hand, such as picking a face like the firewall as the
  reference plane or moving the origin.

Built (2026-10-09), stage 40, `fairsolid refscan --run DIR`:
- Runs after orientation. The scan is moved into the frame by rotation and translation only and
  the stage checks edge lengths to prove nothing was scaled.
- Floating scraps are dropped. The surface is split into smooth patches (a face joins when it
  bends less than 12 deg from its neighbour and stays within 50 deg of the patch's mean
  direction). Patches under 1.5% of the area (hoses, clips, clutter) are left out on purpose.
- Each patch becomes one smooth B-spline surface (smoothing cubic spline over a 2.5 mm grid on
  the patch's own plane, written out exactly as an OpenCascade surface), trimmed to the patch
  outline. Outlines are resampled and smoothed so the edges are tidy, not grid stair steps.
- Reference geometry: origin and X/Y/Z axes from the frame, a datum plane for each patch flat
  within 0.5 mm rms, and a point plus direction for every curved patch.
- `--knit` sews the surfaces into one open shell; `--patch-box x0,y0,z0,x1,y1,z1` fits one
  bridging surface over everything in a box, to model across a gap.
- Writes 40_ref_surfaces.step (+ .stl), 40_ref_datums.step, 40_ref.json and 40_ref_render.png
  (grey scan above, shaded surfaces below, same cameras).
- oil_catch: 9 surfaces from 9 patches, 72% of the area. On the panels (77% of scan points)
  median 0.07 mm, p95 0.79 mm, 92% within 0.5 mm. Outline turning fell from 12.1 to 2.0 full
  turns per patch (1.0 = a smooth convex loop).
- Not yet: picking a face (such as the firewall) as the reference plane from the UI. The frame
  can already be edited by hand in 20_frame.json.

## 11. Assistant (decided 2026-10-08)
Fairsolid gets an assistant in three parts. All three are built. AI is optional: the app works
fully without it, offline, and every step can be done by hand.

Decided:
1. Built-in helper (no AI, works offline).
   - Hints and one-click fixes that come from the app's own geometry checks, for example
     "these two areas are nearly the same plane, merge them?" or "this patch is 0.3 mm off,
     add points or lower the stiffness?".
   - Every fix shows a preview first, needs the user to confirm, and can be undone.
   - Tutorials for each of the 7 steps.
2. MCP server on the same internal action API.
   - The UI buttons, the helper's fixes and the MCP tools all call one internal action API,
     so they behave the same.
   - Installed agent apps (Claude Code, Cursor agent, Gemini CLI, Copilot CLI) can drive
     Fairsolid through it. The user confirms each action.
3. Optional in-app chat.
   - Local Ollama is the primary option.
   - Free API keys (Groq, OpenRouter, Gemini) are options when the user's GPU can't run a local
     model or the user simply prefers them. Gemini is shown with a warning: its free tier may
     use prompts and answers to improve Google products, and people may read them.
- The old WSL neural AI stage (stage 40: CADReasoner, cadrille, CAD-Recode run in WSL from
  `~/cadenv`) is removed from the code. It measured worse than the deterministic path on every
  real scan tested (see `docs/AI_METHODS_REPORT.md`, kept as history only), and it does not fit
  the surface-fitting approach in this plan.

PROPOSED (suggested by Grok Bot, not decided yet):
- One OpenAI-compatible client for the chat, which covers Ollama, Groq and OpenRouter (Gemini
  also offers an OpenAI-compatible endpoint).
- API keys are entered by the user and stored outside the repo (Windows Credential Manager, or
  a settings file under `%APPDATA%\Fairsolid`). Never committed, never written to run folders
  or reports.
- The chat gets summaries (area list, settings, deviation numbers, flagged joints), not the
  scan mesh.
- Example local model: `qwen3:8b` in Ollama (about 5 GB at 4-bit, supports tool calling; fits a
  12 GB GPU such as an RTX 3060 with a larger context than Ollama's default).
- A GPU check on first use of the chat: if the GPU is too small for a local model, suggest a
  free API key instead.
