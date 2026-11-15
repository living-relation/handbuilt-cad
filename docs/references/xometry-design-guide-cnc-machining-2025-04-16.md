# Design Guide: CNC Machining (text conversion)

**Source:** Xometry, *Design Guide: CNC Machining*, 38 pages, PDF dated 16 April 2025 (created Wednesday, 16 April 2025, 14:34:46 America/New_York).

**This file:** a faithful, cleaned Markdown conversion of the full 38-page guide for agent use. Section headings, all numeric values, and tables are kept. Page markers (`<!-- pN -->`) match the guide's own "N of 38" pagination so page cites in `docs/CNC-MACHINING-RULES.md` resolve here. Images and marketing or boilerplate (cover art, "Did you know?" ads, "See more of…", "Other Xometry Capabilities," quoting-engine pitches) are omitted. Where a figure carries information that is not already in the text, it is described briefly.

**Full PDF:** not in this repo (files over 1 MB are blocked). It lives on DansPC in the models folder: `models\references\xometry-design-guide-cnc-machining-2025-04-16.pdf`.

---

<!-- p1 -->
## p1 — Cover

Title: **Design Guide: CNC Machining**. Authored by the Xometry Team. (Cover artwork only; no numeric design data.)

<!-- p2 -->
## p2 — Table of Contents

| Section | Page |
|---|---|
| Introduction | 3 |
| What is CNC Machining? | 4 |
| CNC Manufacturing Standards | 7 |
| General Manufacturing Standards | 8 |
| General Tolerances | 9 |
| Tight Tolerances | 10 |
| Size Limitations | 11 |
| Design Guidelines | 12 |
| Part Complexity | 13 |
| Fillets | 14 |
| Holes | 16 |
| Pockets & Cavities | 19 |
| Threads & Tapped Holes | 20 |
| Wall Thickness | 21 |
| Embossed & Engraved Text | 22 |
| Undercuts | 23 |
| Materials and Post-Processing | 24 |
| Material Selection | 25 |
| Inserts | 29 |
| Part Markings | 31 |
| Finishes | 32 |
| Additional Resources | 35 |
| Design Quick Reference Poster | 36 |
| Additional Xometry Resources | 37 |

<!-- p3 -->
## p3 — Introduction to CNC Machining

Section divider page. (Title artwork only; no numeric design data.)

<!-- p4 -->
## p4 — What is CNC Machining?

CNC (Computer Numerical Controlled) Machining is a means to remove material using high speed, precision machines that use a wide variety of cutting tools to create the final design. CAM (computer aided manufacturing) software, in conjunction with the CAD (computer aided design) model provided by the customer, is used to program the instructions the machines will use to produce parts.

Because a computer controls the machine's movement, the horizontal, vertical, and rotational axes can all move simultaneously to create everything from simple straight lines to complex geometric shapes. However, despite advancements in tooling and CNC controls, some limitations still exist in CNC machining, and not all profiles and features can be created. These limitations will be discussed later in this guide.

*Figure (p4): a photograph of a vertical CNC mill; no unique dimensions.*

<!-- p5 -->
## p5 — CNC Milling

With CNC mills, parts are manufactured by holding down the stock material or workpiece to the machine bed while a fast-turning spindle holding the cutting tool removes material. Horizontal and vertical movements of the spindle and bed are used to manipulate the workpiece position, allowing various shapes and depths to be cut. In machines with an additional axis of control, such as the rotary axis in 5-axis machines, the tooling can access multiple faces and hard-to-reach areas to create complex features with reduced setups.

*Figure (p5): a photograph of a machining center / mill; no unique dimensions.*

<!-- p6 -->
## p6 — CNC Turning

Complex cylindrical shapes can be manufactured more cost effectively using a CNC lathe versus a 3 or 5-axis CNC milling machine. With a CNC lathe, the part stock turns while the cutting tools remain stationary. To create the geometry of a part, the CNC computer controls the rotational speed of the stock, as well as the movement and feed rates of the stationary tools. If square features are required on an otherwise round part, typically, the round geometry is created first using a lathe, then the part is moved to a milling machine to create the square features. Lathes with live or driven tools take exception to this and can perform certain milling operations such as drilling, slotting, and tapping within the lathe itself.

*Figure (p6): a photograph of a CNC lathe; no unique dimensions.*

<!-- p7 -->
## p7 — CNC Machining Standards

Section divider page. Title: **CNC Machining Standards**. (No numeric design data.)

<!-- p8 -->
## p8 — General Manufacturing Standards

Unless otherwise specified, Xometry manufactures CNC machined components to the following standards:

- As-machined surface finish is **125 Ra or better**.
  - Machine tool marks may leave a swirl-like pattern.
- Sharp edges will be broken and deburred by default.
  - Critical edges that must be left sharp should be noted and specified on a print.
- Clear or transparent plastics will be matte or have translucent swirl marks on any machined face.
  - Bead blasting will leave a frosted finish on clear plastics.
- Tolerances on foam or similar compressible materials cannot be guaranteed.

<!-- p9 -->
## p9 — General Tolerances

Tolerance is the acceptable range for a dimension which is determined by the designer based on the form, fit, and function of a part. Unless specifically called out by the designer, Xometry will follow industry standard ISO 2768 tolerances listed below:

**Dimensional tolerance.** For features of size (length, width, height, diameter) and location (position, concentricity, symmetry): **+/- 0.005"**.

For features of orientation (parallelism and perpendicularity) and form (cylindrical, flatness, circularity, and straightness), apply tolerances as follows:

### Orientation and form

| Part length | Tolerance | Angularity tolerance |
|---|---|---|
| 0"–12" | ± 0.005" | ± 0.5 Degree |
| 12"–24" | ± 0.010" | ± 0.5 Degree |
| 24"–36" | ± 0.016" (1/64") | ± 1.0 Degree |
| 36"–60" | ± 0.031" (1/32") | ± 1.0 Degree |
| Over 60" | ± 0.063" (1/16") | ± 1.0 Degree |

Note: These tolerances apply to machined metal components. The tolerance for plastic and composite materials is typically double that of metal.

If tighter tolerances (less than the standard, e.g. +/-.002") are required, information regarding which dimensions require tighter tolerances must be communicated. A technical drawing or specification sheet is the best way to share this information.

*Note for agents: the guide labels this table "ISO 2768," but the printed values are a flat ±0.005" size/location tolerance plus a length-based form table. That is not ISO 2768-1 medium. See `docs/CNC-MACHINING-RULES.md`.*

<!-- p10 -->
## p10 — Tight Tolerances

General CNC machining tolerances are typically **±0.005"**, with tight tolerances being smaller. With CNC machining we can readily achieve tolerances of **±0.001"**, and even tighter with specialized setups like reaming or grinding, depending on material and geometry. GD&T can be applied but may increase inspection time due to required tools and checks.

While tighter tolerances can improve a part's form, fit, and function, they can also raise scrap rates, require special fixturing and measurement tools, and slow cycle times, leading to higher costs and longer lead times. Depending on the tolerance and geometry, part costs can more than double compared to those with standard tolerances.

**Pro tip:** To help minimize cost and lead time, apply tight or geometric tolerances exclusively to critical areas and only specify what is required to meet your part's form, fit, and function.

<!-- p11 -->
## p11 — Size Limitations

**Milled parts.** Part size is limited to the machine's capabilities and depth of cut required by a part's features. Xometry can typically mill parts up to **80" x 48" x 24"**. The features and size of each unique part will determine that part's machinable height. If your part goes beyond **24"** in machinable height, it will require an additional manual review for manufacturability.

**Turned parts.** Xometry's capabilities allow for turned parts up to **32" in diameter and 62" in length**. In addition to standard 2-axis lathes, Xometry's manufacturing facilities utilize specialized equipment such as live tooling systems, multi-spindle machines, and swiss lathes, which are great for producing lathe parts with milled features or small, delicate features.

**Material blank.** "Material blank" or simply "blank" refers to the size of the raw material used to create the finished part. Blanks typically need to be slightly larger than the finished part's measurements to allow for variations in the raw material and to cut away the rough faces of the raw material. For example, if the final dimensions are to be **1"x1"x1"**, then a suitable blank for the part would be a **1.125" cube**.

**Pro tip:** Optimize your design for smaller and standardized blank sizes to reduce cost and waste. Remember that some blank sizes and shapes are more common in particular materials than others.

<!-- p12 -->
## p12 — Design Guidelines for CNC Machining

Section divider page. (Title artwork only; no numeric design data.)

<!-- p13 -->
## p13 — Part Complexity

CNC machining can effectively produce highly complex designs; however, that does not mean you should not strive to simplify your designs. A part with contoured geometry or multiple faces that need to be cut will typically take longer to machine and thus have a higher cost when compared to a piece that only requires one setup and three axes (X, Y, and the tool movement of the Z). Tiny cuts are made with small tools to create a complex curved surface with a suitable surface finish. These type of cuts take significantly longer to machine than the larger cuts that can be made on broader or planar geometries, increasing the cost.

To minimize cost and cycle times, simplify your design by:

- Designing features on-axis planes.
- Avoiding unnecessary draft angles.
- Avoiding contoured or organically shaped geometry.
- Minimizing feature variations, such as internal corner radii.
- Minimizing thread size variation.

*Figure (p13): a comparison of a simple on-axis 3-axis part with a multi-face or contoured part; no unique numeric limits.*

<!-- p14 -->
## p14 — Fillets (inside corner)

When using a CNC vertical or horizontal milling machine, interior vertical walls cannot be left sharp and will be machined with a radius. Radii must be present because the material is removed using a round tool spinning at high RPMs. Part designers must consider where radii will occur due to this limitation.

### Inside corner fillets

Sizing corner radii appropriately can not only improve cutting efficiency and cost, but quality as well.

Consider the following for internal corner radii in your designs:

- Use radii that do not correlate with standard tool sizes
- Radii should be above **1/32"**
- Radii should be as large as possible
- Avoid small, deep radii

We recommend avoiding standard tool sizes (e.g., **1/4", 1/8"**) for corner fillets because when tool and corner radii match, the tool lacks clearance, forcing abrupt stops and pivots that reduce efficiency and cause chatter.

**Pro tip:** Use a radius **1.3 times** the radius of the closest standard tool size and aim for a radii-to-depth ratio of **1:4** for pocket radii.

*Figure (p14): an inside corner with a tool in the fillet; the recommended corner is labeled 1.3× the nearest standard tool radius, with a pocket radii-to-depth ratio of 1:4. Those values are already in the text.*

<!-- p15 -->
## p15 — Fillets (floor) and tool depth

Larger radii allow for bigger tools that remove more material per cut, reducing machine time and cost. When cut depth exceeds **twice the tool diameter**, feed rates slow, increasing cycle time. While small-radius tools (as low as **.015"**) exist, the required cut depths may exceed tool length, making machining impractical or significantly more expensive due to increased processing time.

### Floor fillets

Generally speaking, floor fillets can be time consuming and difficult to machine and thus should be avoided unless vital to your part's form and function. When creating a floor radius that meets a corner, it is much easier to machine if the floor radius is smaller than the wall radius.

By making the floor radii smaller than wall radii, the same tool can be used to remove the material, increasing efficiency and cutting smoothness.

**Pro tip:** For better manufacturability of floor fillets, use a standard bull-nose end mill radius.

*Figure (p15): a pocket section showing a floor fillet smaller than the wall radius, with a bull-nose tool in the floor corner. No unique numbers beyond the text.*

<!-- p16 -->
## p16 — Holes (standard drill sizes)

Holes are typically created using drill bits that plunge into the workpiece to remove material. Drilling is a fast and efficient method of creating holes and is what most machinists will defer to when they can. Larger or oddly sized holes can be made via helical milling with an endmill, but this is slower and less efficient than drilling methods. In either case, designers should make a few considerations when designing holes in their parts.

### Standard drill sizes

Designers should familiarize themselves with standard drill bit sizes and design holes accordingly to allow for fast drilling and accurate hole sizes. Non-standard hole sizes may require expensive custom tooling or additional passes with end mills and reamers to achieve the dimension, which increases cycle time. Drills are usually sized in conventional fractions of an inch, such as **1/8", 1/4"**, or whole numbers of millimeters.

**Pro tip:** Pick hole sizes that work universally. Lowering hole size variation means the same tool can be used for multiple features, reducing cycle time and cost.

<!-- p17 -->
## p17 — Hole depth to diameter ratio

As the depth of a hole increases, so does the manufacturing difficulty. Excessively deep and narrow holes can lead to manufacturing issues such as tool breakage, drill walking, and chip evacuation issues, among others.

Hole depth to diameter should be kept as low as possible. Holes with significant depth-to-diameter ratios may require specialized tooling, such as gun drilling, to achieve the geometry.

**Pro tip:** Keep your drill hole diameter-to-depth ratio below **1:10** for manufacturability. A time and cost-saving ratio of **1:4** is even better. For example, a **0.250" diameter** drilled hole at **1" deep** is optimal, while a depth of **2.5"** is achievable.

*Figure (p17): a side view of a Ø0.250" hole with 1" (optimal) and 2.5" (achievable) depths marked — the same numbers as the text. The printed "diameter-to-depth 1:10" wording is inverted relative to that example; the example is the authority (depth:diameter under 10:1).*

<!-- p18 -->
## p18 — Other hole design tips

Here are some other quick tips and considerations you can follow to improve hole manufacturability of your parts:

- Avoid partial holes; keep at least **75%** of the hole inside the part edge.
- Keep holes and pockets at least **1/32" (0.030")** from walls to avoid defects in metal parts. Double this value for milled plastic or composite materials.
- Design holes perpendicular to the surface; incorporate flats on curved surfaces to ensure proper drill entry.
- Use through holes over blind holes when possible; they are more accessible to machine, ream, and tap.
- If you need to use blind holes, add **25%** additional depth than you require to account for drill points and chip evacuation.
- Avoid hole-cavity intersections; if unavoidable, try offsetting the drill axis from the cavity center.

*Figures (p18): plan views of a partial hole (≥75% inside the edge) and of a hole offset ≥0.030" from a wall — values already in the text.*

<!-- p19 -->
## p19 — Pockets and cavities

Pockets and excessively deep cavities can pose manufacturing issues such as tool deflection, chip evacuation problems, and tool breakage. Cavities greater than **six times** deep than they are wide are considered too deep; the ideal width-to-depth ratio is **D < 4*W**.

If you require deeper cavities, consider using a variable cavity width that is wider at the top allowing for better tool access at the bottom.

**Pro tip:** When a straight rectangular part will be assembled into a cavity, and a sharp corner is desired, adding corner reliefs or dog bone cuts is better than using a small radius.

*Figures (p19): a cavity depth-vs-width sketch, and a dog-bone / corner-relief at a square-in-pocket corner. Limits already in the text.*

<!-- p20 -->
## p20 — Threads and tapped holes

There are several ways to create threads in a part: cut taps, form taps, or thread mills. All of these methods are effective, but designers should keep the following in mind:

- Thread only as deep as necessary, usually no more than **twice the hole diameter** in metals. Going deeper can increase costs due to the need for specialized tooling.
- Consider using threaded inserts for softer materials such as aluminum or plastics.
- Choose the largest thread size allowable by your design for easier manufacturing.
- Smaller taps are more likely to break, especially below **M2 or #0-80 UNC**.
- Avoid uncommon or custom threads, as they may require expensive tooling.
- For blind holes, add an unthreaded length at least **half the hole diameter** for tap lead and chip removal. While drill relief is not necessary in the 3D model, it should be indicated as allowable on the technical drawing.
- During quoting, specify the thread count and attach a drawing detailing thread type, hole size, depth, and any blending treatments like countersinks.

*Figure (p20): a blind-tap section showing thread length ≤ 2× diameter and unthreaded relief ≥ 0.5× diameter — values already in the text.*

<!-- p21 -->
## p21 — Wall thickness

Walls should be kept thick enough to ensure strength and rigidity. When thicknesses become excessively thin, they are prone to warping, breakthrough, and general failure when under stress. Additionally, as rigidity is lost, vibrations from the machining process can result in chatter, forcing the machinist to slow things down to mitigate this issue. It is also more difficult to maintain accuracy when cutting walls that are not rigid enough due to being too thin.

Minimum wall thickness should correspond with the following:

| Material | Minimum wall thickness |
|---|---|
| Metal materials | **0.030" (0.762 mm)** |
| Plastic & composite materials | **0.060" (1.52 mm)** |

*Figure (p21): thin-wall vs adequate-wall examples at the published minima. Values already in the table.*

<!-- p22 -->
## p22 — Machined text (embossed and engraved)

Machined text can be designed in one of two ways: embossed text that rises above the surface or engraved text that sits below the surface. Of these methods, we recommend creating text as engraved instead of embossed.

Engraving requires minimal material removal, unlike embossing, which involves a large amount of material removal adjacent to the text to create the raised marking. If you do not require machined markings, consider laser marking as an alternative method for adding text to your part.

**Pro tip:** Use **20-point sans serif** fonts and remember any sharp internal edges of characters will be machined with a radius.

<!-- p23 -->
## p23 — Undercuts

Undercuts are geometric features that standard axial tools (e.g., end mills) cannot access due to their orientation or position, such as grooves perpendicular to the tool axis. When designing undercuts, consider the following:

**Tooling limitations:** Non-standard undercut dimensions may require custom keyseat or form tools, increasing cost and lead time, particularly for low-volume production. Aligning features with standard cutter sizes (e.g., standard radii) enables use of off-the-shelf tooling and minimizes expense.

**Cut depth constraints:** Tool geometry (typically a horizontally-mounted cutting blade on a vertical shaft) limits achievable depth. Shallower cuts are preferred to maintain rigidity and avoid tool deflection.

Undercuts should also be located in areas accessible to the tool. If positioned incorrectly, the feature may not be machinable through conventional CNC processes.

<!-- p24 -->
## p24 — Materials and Post-Processing

Section divider page. (Title artwork only; no numeric design data.)

<!-- p25 -->
## p25 — Material selection

Material selection is critical in determining a part's overall functionality and cost. The designer must determine the material characteristics key to the part's design, such as hardness, rigidity, chemical resistance, heat treatability, thermal stability, etc. Xometry is capable of machining a wide variety of metal, plastic, and composite materials.

A key takeaway with choosing a material is that material can significantly impact part cost. Plastics and softer metals like aluminum and brass machine quickly, reducing cycle time and expense. Harder materials (e.g., stainless and carbon steel) require slower spindle speeds and feed rates, increasing machining time.

Consider this when picking materials for your project:

- Stainless steel machines at **~1/2 the rate** of carbon steel.
- Aluminum machines **~4× faster** than carbon steel.
- Plastics machine even faster and are comparable or less than the cost of 6061 aluminum, making them cost-effective when high rigidity isn't required.

**Note:** Depending on a part's geometry, tight tolerances can be harder to hold with plastics. Parts may also warp after machining due to the stress created when material is removed.

<!-- p26 -->
## p26 — Popular metal materials

Below you will find some of the most commonly picked metal materials offered at Xometry for CNC machining projects:

| Material | Notes |
|---|---|
| Aluminum 6061-T6 | A versatile, heat-treatable aluminum alloy with excellent corrosion resistance and a good strength-to-weight ratio. |
| Stainless Steel 304 | A widely used stainless steel with good corrosion resistance and formability, commonly used in food, medical, and industrial applications. |
| C360 Brass | A brass alloy with excellent machinability, moderate strength, and corrosion resistance, widely used in precision components. |

<!-- p27 -->
## p27 — Popular plastic and composite materials

Likewise, here are some of the popular plastic and composite CNC material options:

| Material | Notes |
|---|---|
| Acetal (POM) | A low-friction engineering plastic with high impact resistance and excellent dimensional stability; ideal for gears, bearings, and precision parts. Acetal is the generic version of Delrin®. |
| HDPE (High-Density Polyethylene) | A lightweight, impact-resistant plastic with good chemical resistance, used in industrial, outdoor, marine, and food applications. |
| Garolite G10 (FR4) | A fiberglass-reinforced epoxy laminate that is electrically insulating, mechanically strong, and flame resistant; commonly used in electrical and structural applications. |

<!-- p28 -->
## p28 — Other CNC materials

Below you will find other materials that Xometry offers as a standard selection when you configure your quote. Custom material requests are also accepted.

| Other metals | Other plastics & composites |
|---|---|
| Aluminum alloys (e.g., 2024, 6063, 7050, 7075, MIC-6) | ABS |
| Brass | Acrylic |
| Bronze | Delrin® |
| Copper | Nylon |
| Carbon steel | PEEK |
| Nitronic 60 | Polycarbonate |
| Stainless steel (e.g., 15-5, 17-4, 316, 410, 416, 420, 440C) | Polypropylene |
| Titanium Grade 2 | PTFE |
| Titanium Grade 5 | PVC |
| Tool Steel A2 | UHMW PE |
| Tool Steel O1 | ULTEM |
| Other custom metals | Other custom plastics |

<!-- p29 -->
## p29 — Inserts

Inserts are a common method for creating strong, reliable threads in parts. They are especially useful in softer materials such as aluminum or plastics, where tapped threads are more prone to wear and tear. If you require inserts, be sure to list the number of inserts required per part on your quote.

When designing for inserts, follow the guidelines specified by the instructions included with the off-the-shelf inserts. The insert SKU or part number, installation orientation, depth, and part install face should be clearly defined in an accompanying print for reference.

**Pro tip:** Do not upload your CAD model with inserts included as an assembly; instead, include and call out inserts on a technical drawing. CAD files with embedded inserts can complicate programming and quoting.

<!-- p30 -->
## p30 — Standard inserts

Xometry and its manufacturing suppliers can install a wide variety of inserts. Some types of inserts are better suited for particular applications or materials. Below are some commonly utilized inserts for CNC machined components.

| Type | Notes |
|---|---|
| Helical inserts | Also known as Heli-Coils, these stainless steel inserts reinforce threads in soft materials, like aluminum or plastics. They are used in aerospace, automotive, and electronics for durability and vibration resistance. |
| Key-locking inserts | Sometimes referred to as Keenserts, these solid metal inserts lock into place with keys for high-strength, torque-resistant threads; ideal for heavy-duty applications in aerospace, defense, and industrial machinery. |
| Press-fit inserts | Commonly used in plastics and soft metals, press-fit inserts are designed to be forced into a pre-drilled hole, creating a secure, friction-based hold; ideal for consumer electronics, enclosures, and lightweight assemblies. |
| Heat-set inserts | Heat-set inserts are installed by heating and pressing them into thermoplastics, causing the material to melt and re-solidify around the insert, securing it; often used in enclosures and mechanical assemblies. |

<!-- p31 -->
## p31 — Part markings

Part marking is a great way to add high-contrast markings, part numbers, logos, and more. The table below compares the different types of marking methods offered.

| Marking method | Common uses | Pros | Cons |
|---|---|---|---|
| Silk screen | Graphics; logos; text; multi-color markings | Color variety; crisp detail; works on a variety of materials | More costly at lower quantities; susceptible to wear/fading over time |
| Ink stamp | Part numbers; serialization | Low cost; little to no impact on lead time | Limited to characters and numbers; generally less crisp |
| Laser marking and engraving | Graphics; part numbers; text | Extremely durable markings; crisp detail | Cannot produce colored markings |
| Bag and tag | Serialization; part numbers; bulk packaging | Very low cost; can speed up inventory and receiving processes | Non-permanent solution |

**Note:** For markings with special font, graphics or logos, please provide artwork files in the form of a vector file such as a DXF. Pixelated or rasterized files (e.g., JPEG, PNG, etc.) are not suitable.

<!-- p32 -->
## p32 — Finishes

Applying a finish to your CNC machined parts can not only improve their cosmetic appeal but also provide surface protection and increased performance, such as improved corrosion resistance, wear resistance, smoother surfaces, enhanced electrical properties, and more.

When adding finishes to a part, it is important to clearly communicate the requirements to the finisher. Consider following these best practices:

- Use industry standards to specify the type, class, thickness, and color where applicable.
  - Example: **"Anodize per MIL-A-8625, Type II, Class 2, Black, 0.0002" thick"**
- For thick finishes like platings, specify if tolerances are before or after finish.
- If threads or other surfaces shouldn't be finished, call out masking clearly.
  - Including a color-coded image or model in your drawing can be helpful for more complex mixed finishes and masking scenarios.

<!-- p33 -->
## p33 — Popular metal finishes

Below are a few common finishes for metal CNC machined components offered at Xometry.

**Anodizing.** An electrochemical process that strengthens surfaces, adds corrosion resistance, and allows for coloring to enhance appearance. **Type II** is typically **0.0002"–0.0012"** in thickness, where **Type III (hardcoat anodize)** is roughly **0.002"** thick for extra wear protection.

**Chromate conversion (chem film).** A chemical treatment that enhances corrosion resistance while maintaining conductivity. Thickness is low at **0.00001"–0.00004"**. Type I coatings use hexavalent chromium, giving a gold or brown tint; Type II is colorless, preserving the metal's appearance.

**Electroless nickel plating.** Creates a tough, bright, uniform coating that protects complex surfaces from corrosion, oxidation, and wear. Xometry's standard offering is a thickness starting at **.0001"** and conforming to **ASTM-B733, TYPE IV, SC1, CLASS 1**.

<!-- p34 -->
## p34 — All standard finishing options

The chart below showcases all of Xometry's standard finishing options that can be found in the instant quoting menu. Custom finishing requests can also be accommodated.

| Anodizing | Metal plating | Surface coatings | Conversion coatings | Mechanical & pre-treatments |
|---|---|---|---|---|
| Type II, Class 1 Clear | Electroless nickel | Black oxide | Clear chem film (Type II) | Bead blasting |
| Type II, Class 2 Colored | Zinc | Dry film lubricants | Gold chem film (Type I) | Case hardening & heat treating |
| Type III, Class 1 Clear hardcoat | Gold | Powder coating | Etching | Electropolishing |
| Type III, Class 2 Colored hardcoat | Silver | Wet paint | Passivation | Media tumbling |
| PTFE impregnated hardcoat | Other metals | Specialty coatings | Other conversion coatings | Pickle and oil |

<!-- p35 -->
## p35 — Additional Resources

Section divider page. Title: **Additional Resources**. (No numeric design data.)

<!-- p36 -->
## p36 — CNC design quick reference poster

A one-page poster restating the numeric rules above.

| Topic | Rule |
|---|---|
| Interior corner fillets | **R depth ÷ R edge ≤ 4**. **R edge = 1.3 * R tool**. The larger the radii, the lower the cost. |
| Floor fillets | Keep smaller than wall radii. Standard ball nose mill sizes increase manufacturability. |
| Cavity depth ratio | Keep depth **< 4 * Width**. Use corner reliefs for tight assembly fits. |
| Hole size depth ratio | Keep less than **1:10**. A ratio of **1:4** is optimal and increases manufacturability. |
| Wall thickness | Metals **≥ 0.030"**. Plastics **≥ 0.060"**. Avoid designing to minimum thickness; thicker is better. |
| Thread depth | Length **< 2 * Diameter**. Consider using inserts for softer materials, like plastics. |
| Machined text | **20pt + Sans-Serif**. Use machine engraved text instead of embossed text for lower costs. |
| Additional hole depth | Add unthreaded depth, **50% of diameter**, after threads. Allows for tool leads and chip evacuation. |
| Edge breaks | Use **45° chamfers**. Use chamfers, not fillets, for cost-effective edge breaks. |

*Note: p15 says "bull-nose" for floor fillets; this poster says "ball nose." The guide is inconsistent on that wording.*

<!-- p37 -->
## p37 — Additional Xometry resources

**Online resources** (titles as printed):

- How to Create A Good Technical Drawing
- Standard Thread Sizes
- Standard Insert Sizes
- Xometry's Manufacturing Standards
- Metal Finishes Photo Gallery
- CNC Services Page

**Accepted file types** for upload: STEP (.step, .stp), SOLIDWORKS (.sldprt), Parasolid (.x_t, .x_b), Autodesk Inventor (.ipt), Dassault Systems (.3dxml, .catpart), PTC, Siemens (.prt), ACIS (.sat), and more.

<!-- p38 -->
## p38

Blank back page in the source PDF. No design data.
