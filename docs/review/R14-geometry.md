# R14 geometry review

Summary: (1) Anvil's error-propagation table gives intersection edges and blend spines a bound that is false for every edge sharper than 120°, including a plain box edge, and it has no curvature term, so `Guaranteed` checks rest on bounds that do not hold (R14-01).
(2) Anvil's robustness bar is OCCT and a per-case blend rate, measured on a corpus that Parasolid built and that OCCT filtered: 95% per fillet means a 20-fillet part rebuilds about one time in three, on geometry Parasolid made every time (R14-02).
(3) Phase 1 ships operations (loft, general sweep, twisted extrude) whose surfaces fall outside the phase 1 intersection classes, uncertified tangency falls back to the coincidence bands D-ANV-26 rejects, and a canonical-example tolerance is shared between two independently made features (R14-03, R14-04, R14-07).

### R14-01 · Critical · Targets: ANV
**Section:** Conversions and error propagation (propagation table, D-ANV-21)
**Problem:** The rows "Intersection edge, blend spine, contact curve: max(p_a, p_b) / sin θ_min" understate the position bound. Two faces each displaced by up to p move their common edge by up to p/sin(θ/2) when the displacements have opposite signs relative to the edge, which exceeds p/sin θ for every θ below 120°: at a 90° box edge the edge moves p·√2, not p, and near tangency it moves about 2p/θ, twice the table's figure. The row is also first-order: for curved faces near tangency, a shift ε moves the crossing by √(2ε/Δκ), as ANV's own Tangential contact section says, which no 1/sin θ rule bounds. The table's own Natural-offset corner row already uses p/sin(θ/2), so the two rows disagree. Every blend spine inherits the error, and ANV-O-CONV-2 ("supports perturbed in position ... stay within propagated bounds") would fail on a correct implementation of this rule.
**Evidence:** In the plane normal to the edge, faces n₁·x = a and n₂·x = b with |a| ≤ p_a, |b| ≤ p_b and n₁·n₂ = cos θ give |x|² = (a² + b² − 2ab cos θ)/sin²θ, maximized at (p_a² + p_b² + 2p_a·p_b·|cos θ|)/sin²θ. For p_a = p_b = p and θ = 90° this is 2p², so |x| = p√2. ANV: "Where curvatures differ by Δκ, a shift ε moves crossings by √(2ε/Δκ)."
**Fix:** Replace the row with: position `√(p_a² + p_b² + 2·p_a·p_b·|cos θ_min|) / sin θ_min`, valid only where a certified curvature bound κ̂ on both faces gives `max(p_a, p_b)·κ̂ ≤ sin²θ_min / 4`; otherwise `NotQuantified { NearTangent { edge } }`. Keep the tangent row but state it as first-order with the same validity condition. Add to ANV-O-CONV-2: perpendicular planes displaced by ±p in opposite senses, and two cylinders of curvature difference Δκ at angles from 1° to 90°, each checked against the rule by exact recomputation.

### R14-02 · Critical · Targets: ANV, MEC, CONTRACT
**Section:** ANV Blends (D-ANV-29), State of the art (B-rep Booleans, Blends), Oracles (ANV-O-BLEND-5, ANV-O-BOOL-4); MEC Dress-up features; contract 13.1 GP1 gate
**Problem:** Anvil's robustness is measured per case and against OCCT, never per part and never against the kernel the corpus came from. The ABC models are Onshape documents whose native geometry is Parasolid, so Parasolid built every fillet in the re-fillet corpus. A 95% stage-1 rate therefore means Anvil fails one fillet in twenty that Parasolid made, and with independent cases a part with 20 fillet features rebuilds with probability 0.95²⁰ ≈ 0.36. The corpus is also filtered by OCCT's `BRepAlgoAPI_Defeaturing`, which removes faces by extending and re-intersecting their neighbours; the fillets OCCT cannot remove (corners, fillets on fillets, overflow) never become cases, so the measured rate is biased toward easy fillets. Booleans are judged "success above OCCT 8.0". An engineer who leaves NX or SOLIDWORKS judges Anvil by whole parts that rebuild, and this bar does not measure that.
**Evidence:** ABC dataset page: STEP is a "Parametric boundary representation converted from Parasolid", the `para` file is "The parametric boundary representation in Parasolid format", and the `ofs` file is "The original Onshape FeatureScript definition of the model" (https://deep-geometry.github.io/abc-dataset/). ANV: "Phase 0 builds the re-fillet benchmark's corpus offline from the licence-filtered ABC subset with OCCT's `BRepAlgoAPI_Defeaturing`"; "Targets are 95% of stage-1 cases at the phase 1 gate". OCCT's reference says the algorithm "has the same limitations as" `BOPAlgo_RemoveFeatures` (https://occt3d.com/dev/doc/refman/html/class_b_rep_algo_a_p_i___defeaturing.html).
**Fix:** Replace the per-case gate with a part-level parity benchmark, ANV-O-PARITY-1, owned by ANV with ECO's licence evidence. (a) For each licence-filtered ABC model whose `ofs` uses only standard features in the phase's scope (sketch with solved geometry fixed, extrude, revolve, fillet, chamfer, shell, hole, pattern, mirror, Boolean), an oracle-side translator writes an Ingot program; it lives in `oracles/` and is not an import path, so contract 7.7's rule on proprietary history is untouched. (b) A case passes when the whole program rebuilds, `check_body` passes, and the result matches the `para` B-rep by D-ANV-29's criteria as revised in R14-12. (c) Targets: 98% of in-scope parts at the phase 1 gate and 99.5% at phase 2, with per-feature-kind rates reported. The re-fillet benchmark becomes the fillet slice of this corpus, with cases chosen from FeatureScript fillet features instead of OCCT defeaturing, and per-case targets of 99% (phase 1, stage 1) and 99.7% (phase 2). Report OCCT 8.0's rate on the same corpus, and add one line to contract 13.1's GP1 gate: "GP1-class parts in the parity corpus meet ANV-O-PARITY-1's phase 1 target."

### R14-03 · Major · Targets: ANV, MEC, CONTRACT
**Section:** ANV Surface–surface intersection (phase 1 class list), Blends (stage 1), Construction (`anvil::sweep`, `anvil::loft`, `anvil::extrude` twist and scale); MEC Part features; contract 7.1, 13.2
**Problem:** R8-15's fix does not hold: phase 1 operations still create surfaces that no phase 1 intersection class covers. `anvil::loft` (phase 1) makes NURBS faces, and a stage-1 fillet on a loft edge needs the spine `offset(NURBS) ∩ offset(neighbour)`, but phase 1 offsets only analytic and procedural faces and lists offsets only for canal surfaces. `anvil::sweep` with a non-circular profile and `extrude` with twist or scale Fields (phase 1) make general sweep surfaces, which appear in no class at all, so a Boolean with a box fails. Shelling a lofted body needs the NURBS offset deferred to phase 2. The class "the NURBS pairs that GP1 and the licence-filtered prismatic ABC subset need" is not a definition an agent can build or an oracle can test, because no tab defines the prismatic subset.
**Evidence:** ANV: "Phase 1 offsets analytic and procedural faces, NURBS offsets follow in phase 2"; stage 1 needs "supports in the phase 1 SSI classes"; capability rows `anvil::loft` phase 1, `anvil::sweep` phase 1, `anvil::extrude` "twist and scale 1". MEC: "Loft ... 1 (no guides)"; contract 13.2 defers "free-form offsets".
**Fix:** Define the phase 1 class list as a closure. Let S₁ be the surface types phase 1 operations create; ANV lists every pair in S₁ × S₁ as a class with a phase, and an operation whose output type lies outside the phase's covered set is phased with the classes it needs. Concretely, either add "offsets of NURBS faces, and general sweep surfaces, against planes, quadrics and tori" to phase 1, or move `loft`, non-circular `sweep` and twisted or scaled `extrude` to phase 2 in ANV and MEC. Define the prismatic subset by rule: "models all of whose faces are planes, quadrics, tori, extrusion or revolution surfaces of lines, arcs and conics", which makes the NURBS clause empty, and delete it from ANV and contract 7.1. Add ANV-O-SSI-5: every phase 1 operation's output, combined with a box, a cylinder and a fillet face, gives a valid Body or a typed failure naming a class and its phase.

### R14-04 · Major · Targets: ANV
**Section:** Tangential contact (D-ANV-26), Surface–surface intersection steps 4 and 7
**Problem:** The contact-curve algorithm runs when "a new surface tangent to an existing face" is known, but tangency made by design without a `Continuity` certificate is never detected. A slot sketched tangent to an edge, a hole tangent to an earlier fillet, or a boss tangent to a wall reaches SSI as an unrelated pair. Along a tangency curve the critical-point system has a non-isolated root set, so Krawczyk cannot prove uniqueness, the enclosures straddle τ, and step 7 makes a coincidence region with growth up to τ_cap. That is the spurious band D-ANV-26 rejects: for a 3 mm hole tangent to a 5 mm fillet (Δκ ≈ 133 m⁻¹) at τ = 0.12 µm, the band is about 2√(2τ/Δκ) ≈ 85 µm wide.
**Evidence:** ANV: "A new surface tangent to an existing face goes to the contact-curve algorithm"; "Regions whose distance enclosure stays below τ become coincidence regions"; D-ANV-26 rejects "the coincidence rule for tangency (spurious bands about 2√(2τ/Δκ) wide)". ANV-O-CONTACT-1 tests only fillet on fillet, cylinder on plane and sphere in cylinder, two of which are analytic pairs solved in closed form.
**Fix:** Add a detection step between steps 4 and 7: when a box's Krawczyk test fails with a certified rank-one deficiency of the critical-point Jacobian and the enclosure of h lies within τ_cap, switch the pair to the contact-curve algorithm, which traces the reduced system along the curve and imprints one tangential edge. State that coincidence regions are created only where the distance enclosure stays below τ over a two-dimensional region. Extend ANV-O-CONTACT-1 with uncertified cases: a cylinder Boolean tangent to a canal-surface fillet, a sketched slot tangent to an edge, and a NURBS face tangent to a plane, each giving one tangential edge and no coincidence region.

### R14-05 · Major · Targets: ANV
**Section:** Per-entity tolerances (growth cap τ_cap)
**Problem:** "An operation raises a tolerance to at most max(the inputs' tolerances, τ_cap)" lets one imported edge at τ = 10 µm license growth to 10 µm on every native entity of the same operation. A Boolean of a native GP1 bracket (τ_cap ≈ 0.12 µm) with one healed supplier part can then grow tolerances on faces the import never touched, which changes separation decisions, PMI eligibility and the definition digest of native geometry, with only a `Note::ToleranceGrown`.
**Evidence:** ANV table, "Growth cap τ_cap ... An operation raises a tolerance to at most max(the inputs' tolerances, τ_cap)". Healing allows "max(10 × the file's declared uncertainty, 2¹⁰ρ)".
**Fix:** Make the cap per decided pair: "A decision between entities x and y may raise either tolerance to at most max(τ_x, τ_y, τ_cap) of the inputs those entities descend from." Add to ANV-O-TOL-1: a Boolean of a native block with a healed import at τ = 10 µm leaves every native entity not decided against an imported one at or below τ_cap.

### R14-06 · Major · Targets: ANV, MEC, ECO
**Section:** ANV Per-entity tolerances (λ), Cellular topology (`anvil::exchange_form`); MEC Model-based definition, `check::standards`
**Problem:** Anvil's minimum size λ = 2⁴ρ is about 1.9 nm on the GP1 bracket, below Parasolid's 5 nm default tolerance and far below the micrometre tolerances many receivers use, so Anvil can legally export edges and sliver faces that the shop's CAM or CMM software treats as degenerate. Tolerant edges from healing or contact curves can also exceed a receiver's tolerance and arrive as gaps. `exchange_form` adds seams and approximates procedural faces "within a stored bound", but no profile states the receiver's tolerance or minimum feature, and the bound is not tied to the tolerances on the face, although a profile tolerance on a fillet is then checked against the approximation.
**Evidence:** ANV: "Minimum size λ: 2⁴ρ"; GP1's ρ ≈ 0.12 nm. Jackson 1995 gives Parasolid's default tolerance as "normally 5.0e-9 metres" (https://ftp1.cs.wisc.edu/pub/users/prem/jackson-SM-95.pdf). Contract 13.1: GP1 is "made by a reference shop from Crucible's STEP AP242 ... using the shop's own CAM".
**Fix:** Give `exchange_form`'s receiver profile `tolerance` and `min_feature` fields, with named profiles (Parasolid-based receivers at 5 × 10⁻⁹ m by default, others declared by the organization). `exchange_form` merges entities below `min_feature` within tolerance or fails with `NotRepresentable { entities, reason: BelowReceiverResolution }`, and reports every edge whose τ exceeds the profile's tolerance. Set the default approximation bound for each procedural face to min(1% of the tightest tolerance whose target includes the face, the profile tolerance). Add `export_resolution` to MEC's `check::standards`, run before any export Act, and an oracle that exports a part with a 3 nm sliver and a 10 µm tolerant edge under the Parasolid profile and expects both reported.

### R14-07 · Major · Targets: CONTRACT, ING, MEC
**Section:** Contract 5 `Tol<T>`, 6 (canonical example); ING Arithmetic on tolerances (symbol rule 2), D-ING-4
**Problem:** In the canonical example `thickness = 4mm ± 0.1mm` is forwarded into `extrude(thickness)` and into `rib(t: thickness)`. ING keys a forwarded symbol by (site, realizing Part), so the plate thickness and the web thickness, made by separate machining operations, share one noise symbol and are perfectly correlated: a stack containing their difference gets zero width. The same rule that makes "two parts made from one specification vary independently" is missing for two features of one Part. The example also passes `2 * thickness`, a `Tol`, to `away_from`, which realizes no geometry, and no tab says whether that site becomes PMI, is dropped, or fails (query filters reject a `Tol` with `ING4103`, but `away_from` is not a filter).
**Evidence:** Contract 6: `extrude(thickness)`, `rib(height: 20mm, t: thickness)`, `p.away_from([...], 2 * thickness)`. ING: "A tolerance forwarded into a Part is keyed by (site, realizing Part or Instance path), so two parts made from one specification vary independently."
**Fix:** Key a forwarded symbol by (site, realizing feature `CallSite`, Part or Instance path), in contract 5 and ING rule 2. Std features mark the parameters whose value they realize as an aspect (`#[realizes(OfSize)]` on `extrude`'s distance and `rib`'s `t`); a `Tol` passed to any other parameter fails with a new `ING4104 ToleranceNotRealized` whose fixes are `.nominal` or an explicit `part.tolerance(…)`. Change the canonical example to `2 * thickness.nominal`, and add to ING-O-7 that the canonical bracket has two independent thickness symbols.

### R14-08 · Major · Targets: ING, MEC, ANV
**Section:** ING `Tol<T>`, D-ING-4; MEC Interference and clearance, Model-based definition
**Problem:** Geometry is always built at nominal, and nothing builds it at another point of the tolerance zones. An H7 bore is modelled at its lower limit and a g6 pin above its upper limit, so the STEP file the GP1 shop programs from puts every fitted hole at the edge of its zone, and interference reports a press fit as touching. Creo, which engineers moving to Crucible know, regenerates a model at the upper, middle or lower bound of every dimension for exactly this purpose; Crucible has the information (every site's limits) but no way to use it for geometry.
**Evidence:** MEC: "Geometry is built at nominal, so a 10 H7/p6 press fit touches". ING: "`fit(10mm, H7)` ... the slot holds the nominal". Creo's Dimension Boundaries: "Middle: Sets the dimension value to the nominal value plus the mean of the upper and lower tolerance values" and "the system generates geometry based on new dimensions" (https://support.ptc.com/help/creo/creo_plus/usascii/model-based_definition/to_set_the_dimension_bounds_1.html).
**Fix:** Add an Evaluation parameter `realize: Nominal | Mid | Upper | Lower | Mmc | Lmc` (default `Nominal`), applied to every `Tol` site through ING's literal overrides, the mechanism `vary` already uses; `Mmc` and `Lmc` take the feature-of-size side from the site's `ShapeAspect` kind. PMI and `ItemDefinition`s always come from the nominal Evaluation. Exports take `realize:` (MFG's process hand-off chooses `Mid` for machining by default and states it in the export record), and `interference` and `min_clearance` accept it, so a press fit at `Mmc` reports its true overlap. Oracle ING-O-36: the bracket exported at `Mid` has every fitted diameter at its mid-limit and the same `EntityId`s as at `Nominal`.

### R14-09 · Major · Targets: MEC, ING
**Section:** MEC Stack-up and variation analysis (1D methods), Design checks (`check::fastening`); ING Arithmetic on tolerances
**Problem:** Phase 1 has GD&T on GP1 but no analysis that reads it: the 1D stack sums size `Tol`s and general tolerances only, and geometric zones, bonus tolerance from MMC and virtual conditions first enter in phase 2's 3D zone path. The everyday check on a bolted bracket, whether positional tolerances of clearance and tapped holes let the fasteners assemble (the fixed and floating fastener formulas, with a projected zone for tapped holes), sits in `check::fastening`, phase 2. A GP1 engineer therefore cannot verify in Crucible the assemblability that the GD&T on GP1's drawing exists to guarantee.
**Evidence:** MEC 1D table: "Worst case: Affine `Tol` sum over a closed, signed chain, general tolerances included", phase 1; "3D zone path" phase 2; `check::fastening` phase 2. The fixed fastener formula is T₁ + T₂ = H − F with H "MMC size of the through hole" and F "MMC size of the fastener thread" (https://www.gdandtbasics.com/?p=9816).
**Fix:** In phase 1, let a 1D chain take a `GeometricTolerance` contributor: a position or profile zone of width t contributes ±t/2 along the chain direction, and an MMC or LMC modifier adds the bonus as an affine term in the feature's own size symbol (bonus = |size − MMC size|, linear in that symbol, so ING's affine forms keep its correlation with the size contributor exactly). Move `check::fastening`'s fixed and floating fastener checks, with projected zones, to phase 1, and add MEC-O-TL-9: GP1's bolt pattern gives the hand-computed T₁ + T₂ = H − F margin.

### R14-10 · Major · Targets: ANV, MEC
**Section:** ANV Constraint solving; MEC Solver (D-MEC-4, step 5), Diagnosis
**Problem:** "A radius above the smallest entity tolerance fails with `IllConditioned`" turns numerical conditioning into user-visible failures on ordinary sketches. The smallest entity tolerance defaults to ρ = 2⁻³⁰ of the diagonal, and a Krawczyk box in `f64` has a radius of roughly κ·2⁻⁵² of the diagonal, so any block with condition number above about 2²² (4 × 10⁶) fails: a 0.05 mm chamfer on a 400 mm profile, nearly parallel lines with a far intersection, or a short arc between long tangent lines. The solved coordinates are exact `f64` inputs to Anvil either way; a wide bound says only how far they are from the true root of the equations, which matters to a check, not to the geometry. D-Cubed and planegcs return these sketches.
**Evidence:** ANV: "a radius above the smallest entity tolerance fails with `IllConditioned { block, condition }`"; MEC step 5: "one above the smallest entity tolerance fails with `IllConditioned`". ANV: "ρ(D) = 2^(⌈log₂ D⌉ − 30)".
**Fix:** Never fail on bound width. Report the Krawczyk radius as the `Guaranteed` bound, whatever its size, or an `Estimated` bound where the test fails, and fail only when the box admits a different discrete configuration: an incidence, an orientation qualifier or a tangency side that the box does not decide, as `Ambiguous { block, qualifier }`. Checks that need a tighter bound return `Undecided { needed }` through the normal decision rule. Change MEC-O-SK-8 to: near-singular sketches give boxes containing the reference, and only qualifier-ambiguous ones fail.

### R14-11 · Major · Targets: MEC, ANV
**Section:** MEC Solver (step 4), Diagnosis (targets); ANV Constraint solving
**Problem:** Blocks up to 2,000 unknowns use dense rank-revealing QR, and every block is Krawczyk-certified. Dense Householder QR of a 2,000 × 2,000 Jacobian costs about 2n²(m − n/3) ≈ 10¹⁰ floating-point operations, about one second per factorization in the canonical class without FMA, and Krawczyk needs an approximate inverse and an interval matrix product, both O(n³), on top. The targets (200 entities in 2 ms, a 2,000-entity drag step in 8 ms native and 16 ms in the browser on one thread) cannot hold for any sketch whose decomposition leaves one large block, which is common for profiles closed by many equal and tangent constraints.
**Evidence:** MEC: "Above 2,000 unknowns, sparse QR precedes a rank-revealing pass on R"; "A 2,000-entity drag step takes under 8 ms native and 16 ms in the browser"; Platform notes: "the 16 ms browser drag target assumes one thread". Contract 7.3 forbids FMA in canonical code.
**Fix:** Set the dense cap at 128 unknowns and use sparse QR with a rank-revealing pass above it, in ANV and MEC alike. During a drag, re-solve only the blocks at or after the dragged entity's block in Dulmage–Mendelsohn order and skip certification (the drag is `Interactive`; the build certifies). Certify blocks up to the cap by Krawczyk and larger blocks by a sparse residual bound from the factorization, labelled `Estimated`. Add to MEC-O-SK-5 a 2,000-entity sketch whose decomposition leaves one block of at least 1,000 unknowns.

### R14-12 · Major · Targets: ANV, MEC
**Section:** ANV Blends (re-fillet benchmark criteria, D-ANV-29)
**Problem:** A case succeeds only when "topology equals the original's in normal form" and the Hausdorff distance is at most max(1 µm, 10⁻⁵ D). Both criteria compare Anvil's corners with Parasolid's: Anvil fills valence-3 corners with Várady–Rockwood setback patches, while the originals carry whatever corner faces Parasolid made, so a valid, smooth, well-placed Anvil corner fails on face count or on a corner deviation above 1 µm. The benchmark then measures agreement with one vendor's corner shapes, not success, and pushes builders to imitate them.
**Evidence:** ANV: "A case succeeds when `check_body` passes and topology equals the original's in normal form. The certified Hausdorff distance to the original must be at most max(1 µm, 10⁻⁵ D)"; "Corners use Várady and Rockwood's setback split ... an n-sided G1 patch fills the gap." ABC's B-reps are Parasolid's (https://deep-geometry.github.io/abc-dataset/).
**Fix:** Judge edge blends and corners separately. Edge-blend faces must match the original in topology and within max(1 µm, 10⁻⁵ D). A corner passes when its patch is G1 to its neighbours within 10⁻⁶ rad, lies inside the convex hull of the original's corner region grown by the largest radius, and the volume differs from the original's corner region by at most 1% of r³. Report corner face-count differences without failing on them. Apply the same rule to R14-02's parity benchmark.

### R14-13 · Major · Targets: MEC
**Section:** Drawings (capability table: sheets, views, dimensions, callouts)
**Problem:** The drawing library names views, dimensions, GD&T, welds, texture and tables, but not the drafting content every machined-part drawing carries: centre marks and centre lines on holes and axes, conventional thread representation (the thin line at the thread root and the three-quarter circle in end views) for cosmetic threads, section hatching by material, break lines, and dimension arrangements (ordinate, baseline, chain) with their tolerance display forms. GP1's shop works from this drawing, and its cosmetic tapped holes are invisible on a drawing that has no thread convention.
**Evidence:** MEC capability rows list "Base, projected, auxiliary and section views", "All dimension kinds by `Query`", "Holes, threads, GD&T, welds; surface texture" callouts, and D-MEC-7 makes threads `Repr::Cosmetic` by default; no row names centre lines, thread representation, hatching or dimension arrangements.
**Fix:** Add a phase 1 row "Drafting conventions": centre marks and centre lines generated from coaxial and cylindrical aspects; conventional thread representation from `ThreadSpec` records in every view and section (the ISO 6410 and ASME Y14.6 conventions in the dialect's drafting package [unverified edition]); hatching from the region's `Material` class with a per-drawing override; break lines; ordinate, baseline and chain dimension sets with limit, plus–minus and basic display forms. Extend MEC-O-DR-4 with a GP1 drawing showing each.

### R14-14 · Major · Targets: MEC, ANV
**Section:** MEC Drawings, Lattices; ANV Measurement services (`project_hlr`)
**Problem:** GP2 is a lattice part with a released, ballooned drawing, but no tab says how a drawing shows an implicit lattice region. Certified hidden lines are specified for lines, circles, conics and B-rep faces; run on a strut graph of millions of struts they would be unreadable and far beyond the 30 s assembly-view target. Drafting practice shows a lattice as a bounded zone with a note, and sections show cut struts.
**Evidence:** MEC: "From phase 1, size, location, orientation, form and profile controls on GP1 and GP2 get" balloons, and "Each release produces the ballooned PDF". ANV `project_hlr`: "certified hidden lines within a stated bound ..., exact projection of lines, circles and conics". ANV: GP2's lattice export reaches "2 × 10⁷ triangles".
**Fix:** In MEC Drawings, add: "A view draws an implicit lattice region as its boundary (the region and the skin, computed exactly where they are B-rep leaves) with a lattice zone symbol and a note naming the cell family, size and thickness Field; hidden lines run only on B-rep faces and the region boundary. Section views cut the lattice with `anvil::section` at the sheet's line resolution." Add the capability row (phase 1) and an MEC-O-DR case on GP2's drawing.

### R14-15 · Major · Targets: ANV, ECO, MEC
**Section:** ANV Imported and non-B-rep entities (D-ANV-31), capability `anvil::match_bodies` (phase 2)
**Problem:** Without persistent ids, an imported face is named by "a hash of its exact parameters and an adjacency signature". A supplier's revised STEP file changes the parameters of every face the revision moved and of any face whose numbers the exporter rewrote, so every mate, PMI target and drawing item on those faces fails with a `ResolveError`. Updating a supplier's part is routine work, and `match_bodies`, the only remedy, arrives in phase 2, after the phase 1 enclosure checks against imported boards.
**Evidence:** ANV: "Otherwise it is the surface type with a hash of its exact parameters and an adjacency signature"; `anvil::match_bodies` phase 2. MEC: `check::enclosure` "reads STEP board assemblies in phase 1".
**Fix:** Move a minimal `match_bodies` to phase 1: on re-import of an Asset at the same import site, match faces of equal surface type whose parameters agree within the import's healing tolerance and whose adjacency graphs agree, and write the result as an `import_map` Proposal with a geometry overlay. Faces the match cannot pair keep failing with `ResolveError`, and the reviewer sees exactly which. Add an ANV-O-NAME-4 case: a board re-exported with one connector moved keeps every other reference.

### R14-16 · Major · Targets: ANV
**Section:** Mesh Booleans (D-ANV-20)
**Problem:** The phase 1 wedge competes with OpenSCAD on Manifold, where mesh Booleans do not fail, yet every Anvil candidate may end in `PrecisionExhausted` when rounding conflicts survive three repair passes. The bake-off chooses "on validity first, then time", so a method that refuses hard cases scores as well as one that solves them.
**Evidence:** ANV: "repairs collapse only edges shorter than 2ε in at most three passes, and a remaining conflict fails with `PrecisionExhausted`"; "The winner is chosen on validity first, then time."
**Fix:** Use Anvil's own tolerant topology instead of failing: when rounding cannot be repaired, keep the result as a facet B-rep whose affected vertices and edges carry τ equal to the certified rounding displacement, within τ_cap, and report `Note::ToleranceGrown`. Fail only above τ_cap. Add the bake-off criterion "zero failures on Thingi10K and thingiCSG pairs" ahead of time, and record each candidate's failure count.

### R14-17 · Major · Targets: ANV
**Section:** Kernel rules (rule 8), Certified decisions in rounds (D-ANV-4)
**Problem:** Predicates are memoized by (pair, epoch), and each epoch re-runs every round from the lowest affected dimension, so one tiny growth re-decides every pair of those rounds, including the face–face round, the expensive one. A decision is a function of the two entities' geometry and tolerances only, so a pair whose tolerances did not change gives the same answer in the new epoch. D-ANV-4 rejects "re-deciding only pairs that touch a grown entity" without a reason, and the simpler rule is exact.
**Evidence:** ANV rule 8: "predicates are memoized by (pair, epoch)"; "It then re-runs every round from the lowest dimension with a pair touching a grown entity."
**Fix:** Memoize decisions by (pair, τ_x, τ_y). An epoch re-decides only pairs that touch a grown or merged entity, plus pairs created by merges, which yields the same bits as a full re-run because unchanged pairs return their memoized answers. Revise D-ANV-4's rejected list, and keep ANV-O-DET-2 as the proof, adding a comparison against a full re-run on the same inputs.

### R14-18 · Major · Targets: MEC, ING
**Section:** MEC Specification model (`GeometricTolerance`), Two dialects, one model
**Problem:** The record's `modifiers` field ends in "…", so agents cannot build validators, renderers, the AP242 mapping or QIF output against it. ISO GPS form, orientation and location specifications also carry elements the record has no field for: the association criterion for the toleranced feature, filter specifications, and the parameter evaluated (peak to valley and others) [unverified: the exact ISO 1101:2017 symbols]. These matter at the CMM, where ISO 8015's independency makes the specification operator decide the measured value.
**Evidence:** MEC: `modifiers: [Modifier], // material condition, projected, free state, dynamic profile, statistical, …`; `Zone // width, shape, disposition`; QIF 3.0 output through MFG (capability row "PMI import, QIF and data-set completeness").
**Fix:** Replace "…" with a closed `Modifier` enum per dialect, listed in a table with the clause that defines each and its AP242 and QIF mapping. Add `association: Option<Association>`, `filter: Option<FilterSpec>` and `parameter: Option<Parameter>` to the ISO dialect's form, orientation, location and profile records, defaulting to the dialect's default specification operator, and make MEC-O-TL-1 check that every enum value round-trips through AP242 and QIF.

### R14-19 · Major · Targets: MEC, ANV
**Section:** MEC Shared conventions (`FeatureError`), capability tables; ANV The operation contract
**Problem:** ANV says `OpError` "maps one-to-one onto MEC's `FeatureError`", but the two tabs name the same failures differently, so neither table can be built against the other. Revolve fails with `CrossesAxis { segment }` in MEC and `AxisCrossesProfile { points }` in ANV; thicken with `OffsetSelfIntersection { faces, max_t }` against `SelfIntersecting`; sweep with `PathNotG1 { vertex }` against `FrameUndefined`; split and combine with `BooleanFailed { faces, reason }` and `EmptyResult`, which ANV's Boolean never returns; blends stages 2 to 4 with `NoContact`, absent from ANV.
**Evidence:** MEC capability rows Revolve, Thicken and rib, Sweep, Split and combine, Blends stages 2 to 4; ANV rows `anvil::revolve`, `anvil::thicken`, `anvil::sweep`, `anvil::boolean`, `anvil::blend`.
**Fix:** Make ANV's kind names canonical and have MEC's tables cite them; where a feature adds its own failure (`PathNotG1` is a feature-level precondition), MEC marks it feature-level. Add ANV-O-NAME-7: the set of `FeatureError` kinds of std features equals ANV's `OpError` kinds plus the feature-level kinds MEC lists.

### R14-20 · Minor · Targets: MEC, ANV
**Section:** MEC Holes and threads (D-MEC-7); ANV Surface–surface intersection (phase 1 classes)
**Problem:** The tabs contradict each other on helicoids, and the phase 1 class serves no gate. MEC defers exact thread flanks because "phase 1 SSI has no helicoid pairs", while ANV lists "helicoids against planes, cylinders and cones" in phase 1. GP1 uses cosmetic threads and GP2 mesh threads, so by contract 13.4's rule (a capability lands at the first gate that needs it) no phase 1 gate needs the helicoid class.
**Evidence:** MEC D-MEC-7 "phase 1 SSI has no helicoid pairs"; ANV phase 1 list "helicoids against planes, cylinders and cones".
**Fix:** Move the helicoid class to phase 2 in ANV, beside exact `Full` threads, and keep D-MEC-7's reason as written. This removes one certified pair class from chain A.

### R14-21 · Minor · Targets: MEC
**Section:** Identity of Parts and Assemblies (placement encoding)
**Problem:** "A unit quaternion with non-negative scalar part" does not fix the sign of a half-turn: when the scalar part is zero, q and −q both qualify, so two encodings of one placement give two Assembly `GeometryId`s. Half-turns are among the commonest placements (a flipped part, a mirrored pair). −0.0 needs the same rule.
**Evidence:** MEC: "A placement is a unit quaternion with non-negative scalar part plus a translation, in canonical f64 bits."
**Fix:** "The quaternion's first nonzero component in (w, x, y, z) order is positive, and −0.0 is written as +0.0." Add a half-turn case to MEC-O-AS-13.

### R14-22 · Minor · Targets: ANV, ING
**Section:** ANV Query resolution (stage 3, `Note::NearTie`)
**Problem:** "A winner whose certified margin is under 5% of the ranked measure" is not translation-invariant for position ranks: for `first(along: +x)` the measure is a coordinate, so a part 1 m from the origin gets a 50 mm near-tie band and the same part at the origin almost none.
**Evidence:** ANV: "A winner whose certified margin is under 5% of the ranked measure carries `Note::NearTie`"; ING lists `first(along: d)` and `nearest: p` as rank selectors.
**Fix:** Define the margin relative to the spread of the candidates: "under 5% of (largest − smallest measure among the candidates), or under 2¹⁰ρ for position measures with two candidates". Add a translated copy to ANV-O-NAME-2.

### R14-23 · Minor · Targets: ANV, MEC
**Section:** ANV `anvil::silhouette`, `project_hlr`; MEC D-MEC-24
**Problem:** "Default 1 µm at model scale, under 0.01 mm at sheet scale" is two bounds that conflict on enlarged views: a MEMS die drawn at 100:1 has 1 µm at model scale equal to 0.1 mm on the sheet, above the sheet bound. On a 1:200 hull view the 1 µm model bound is far tighter than the sheet needs and costs certification time.
**Evidence:** ANV and MEC: "default 1 µm at model scale, under 0.01 mm at sheet scale".
**Fix:** One rule: the bound is 0.01 mm on the sheet divided by the view scale, and never coarser than the drawing's tightest tolerance divided by 10 at model scale.

### R14-24 · Minor · Targets: CONTRACT, ANV
**Section:** Contract 7.1 (Anvil, SSI sentence); ANV Tangential contact, Surface–surface intersection step 7
**Problem:** Contract 7.1 says "every intersection point is a certified root of the exact equations", but tangential edges are imprinted with τ equal to a certified contact deviation and coincidence regions are decided by the round rule; neither consists of certified roots. The sentence matters for freedom to operate, so it should say exactly what the code does.
**Evidence:** Contract 7.1; ANV: "imprints one tangential edge with τ = max(ρ, certified contact deviation)"; "Regions whose distance enclosure stays below τ become coincidence regions."
**Fix:** Contract 7.1: "Every transversal intersection point is a certified root of the exact equations; tangential contact curves and coincidence regions are certified enclosures within their recorded tolerance; no point is ever selected from a sample set by a distance threshold."

### R14-25 · Minor · Targets: ANV, ING
**Section:** ANV Booleans, splits and patterns; ING Kiln-held values
**Problem:** ANV says "Kiln lowers a whole CSG tree to one arrangement", but Kiln never rewrites Op graphs, and ING lowers only "a chain such as `a + b + c`" by a syntactic rule. A tree whose intermediate results are bound (`let ab = a + b`) and reused cannot fuse without changing `CallSite`s, keys and `EntityId`s.
**Evidence:** ANV: "Kiln lowers a whole CSG tree to one arrangement, so rounding happens once per tree". ING: "A chain such as `a + b + c` lowers to one n-ary `anvil::boolean` by a fixed rule".
**Fix:** ANV: "Ingot lowers each Boolean expression without intermediate bindings to one n-ary operation (ING), so rounding happens once per expression."

### R14-26 · Minor · Targets: MEC
**Section:** Part features (Conventions, `housing` example)
**Problem:** The example does not compile and would drill into its own pocket. `extrude(UpTo(depth - 4mm), dir: -normal)` passes a `Length` where `Extent::UpTo` takes a `Query`. `block.face(role: end_cap).corners(inset: 8mm)` resolves on `block - pocket`, whose end cap now has the pocket rim as an inner loop, so "corners" includes four rim corners inside the pocket unless `corners` means outer-loop convex corners, which no tab defines.
**Evidence:** MEC: "`Extent` is shared by every profile feature: `Blind`, `Symmetric`, `ThroughAll`, `UpTo(Query)`, …"; the `housing` example.
**Fix:** Write `extrude(Blind(depth - 4mm), dir: -normal)`, and define `face.corners(inset:)` in `std::mech::refgeom` as the convex vertices of the outer loop, inset along the bisector. Add the example to MEC-O-PF-16.

### R14-27 · Minor · Targets: MEC, ANV
**Section:** MEC Shared conventions (`repr: Repr`), Large assemblies (`InstanceRepr`), Surfacing (`Continuity`); ANV Rust surface (`enum Repr`), Attributes and certificates (`Continuity`), failures (`Ambiguous`)
**Problem:** Three names each carry two concepts, against contract 10's "one name per concept". `Repr` is Anvil's representation (`BRep`, `Implicit`, `Mesh`, `SubD`) and MEC's level of detail (`Cosmetic`, `Simplified`, `Full`). `Continuity` is MEC's order enum (`G0` to `G3`) and Anvil's certificate attribute. `Ambiguous` is an `OpError`, a `ResolveError` and an `EdgeClass` value.
**Evidence:** ANV `pub enum Repr { BRep(…), Implicit(…), Mesh(…), SubD(…) }`; MEC "`Cosmetic` stores intent only, `Simplified` …, `Full` …"; ANV `Continuity { order: G1 | G2, certified_by }`; MEC "`Continuity` is `G0` to `G3`".
**Fix:** Rename MEC's to `Detail::{Cosmetic, Simplified, Full}` and `InstanceDetail`; Anvil's certificate to `ContinuityCertificate { order: Continuity, certified_by }`, reusing MEC's enum; and the edge class to `EdgeClass::Undecided`.

### R14-28 · Minor · Targets: CONTRACT, ING, MEC
**Section:** Contract 5 `ShapeAspect`; ING GD&T controls as types; MEC Shared types
**Problem:** The aspect kinds differ in every place they are listed: the contract names `OfSize`, `Hole`, `Pattern`; ING uses `OfSize`, `Planar`, `Any`; MEC says "a feature of size, face set, pattern or recognized aspect". The type parameter of `Query<ShapeAspect<K>>` drives ING's compile errors, so one closed list is needed.
**Evidence:** Contract 5: "kinds such as `OfSize`, `Hole`, `Pattern`"; ING: "`hole(…)` gives `ShapeAspect<OfSize>`, extrude caps `ShapeAspect<Planar>`, recognized imports `ShapeAspect<Any>`".
**Fix:** MEC owns one enum, by Clément's invariance classes plus size: `Planar`, `Cylindrical`, `Spherical`, `Helical`, `Prismatic`, `Revolute`, `Complex`, each with an `OfSize` marker trait where a size applies, plus `Pattern<K>` and `Any`. The contract cites MEC instead of listing kinds.

### R14-29 · Minor · Targets: MEC, ANV
**Section:** MEC Machine elements (gear flanks)
**Problem:** "Involute flanks are not rational, so gears use B-spline flanks within 0.1 µm" contradicts D-ANV-7's rule that constructions stay procedural with exact evaluation. An involute is a closed-form curve, and a helical involute flank is a developable ruled surface, both expressible as Law geometry, which arrives in the same phase as gears. Exact flanks remove the 0.1 µm approximation from GP3's loaded tooth contact and from the gear data table's over-pins value.
**Evidence:** MEC: "Involute flanks are not rational, so gears use B-spline flanks within 0.1 µm (target)"; ANV: Law curves and surfaces phase 2; gears phase 2.
**Fix:** Build flanks as procedural Law surfaces through the kernel IR (`std::mech::machine` defines them), with `exchange_form` approximating them only for export within R14-06's bound.

### R14-30 · Minor · Targets: ANV, MEC
**Section:** ANV Construction (continuity analyses); MEC Continuity and surfaces
**Problem:** "Thresholds relative to the Body's resolution and size" cannot define G1 to G3 thresholds: G1 is an angle and G2 a curvature ratio, neither of which scales with length. Only G0 has a length threshold.
**Evidence:** ANV: "Continuity analyses default to thresholds relative to the Body's resolution and size"; MEC repeats it. ANV's blend benchmark already uses "G1 within 10⁻⁶ rad".
**Fix:** Defaults: G0 within the edge's τ; G1 within 10⁻⁶ rad; G2 within 10⁻⁴ relative curvature difference; G3 within 10⁻³ relative; each overridable per check.

### R14-31 · Minor · Targets: ANV
**Section:** Per-entity tolerances (healing limit τ_heal)
**Problem:** τ_heal = max(10 × the file's declared uncertainty, 2¹⁰ρ) has no upper bound tied to the part: an exporter that declares 0.1 mm uncertainty licenses 1 mm healing, which closes real slots and merges real thin walls without a failure.
**Evidence:** ANV: "Healing limit τ_heal: max(10 × the file's declared uncertainty, 2¹⁰ρ)".
**Fix:** Cap the default at λ_min/4, where λ_min is the smallest edge length or wall thickness measured on the import, and report `Note::HealingCapped { declared, used }`; larger healing needs the explicit argument.

### R14-32 · Minor · Targets: MEC, ING
**Section:** MEC Determinism and seeds (D-MEC-33)
**Problem:** The seed quantum "the larger of 2¹⁰ρ for the sketch and 10⁻⁶ of its diagonal" has a redundant term: 2¹⁰ρ lies between 0.95 × 10⁻⁶ D and 1.9 × 10⁻⁶ D, so the second term binds only when D is within 5% below a power of two.
**Evidence:** ANV: ρ(D) = 2^(⌈log₂ D⌉ − 30), so 2¹⁰ρ = 2^(⌈log₂ D⌉ − 20).
**Fix:** q = 2¹⁰ρ of the sketch, in ING and MEC.

### R14-33 · Minor · Targets: CONTRACT, ANV, ING, MEC
**Section:** Contract 5 `Query`; ANV Query resolution; ING The query language
**Problem:** Three Boolean parameters, `on_merge: Accept`, `on_partial: Accept` and `on_fragile: Accept`, express one idea: which degradations an extent use accepts. Three names, three dialog fields and three agent tool parameters for one set.
**Evidence:** Contract 5: "unless the call writes `on_merge: Accept`, `on_partial: Accept` or `on_fragile: Accept`".
**Fix:** One parameter `accept: [Merged, Partial, Fragile]`, default `[]`, in the contract, ANV, ING and MEC.

### R14-34 · Minor · Targets: ANV
**Section:** Lead; Kernel rules (rule 6); D-ANV-35
**Problem:** The lead says Anvil "never lets the GPU decide or prune", while rule 6 and D-ANV-35 let exact integer GPU tests prune.
**Evidence:** Lead; rule 6: "only its exact integer tests prune".
**Fix:** Lead: "lets the GPU order work, preview and prune only by exact integer tests".

### R14-35 · Minor · Targets: ANV
**Section:** Conversions and error propagation; Kernel structure and operation contract
**Problem:** Two readability gaps. The propagation table uses p and n without defining them (presumably the source face's position and normal bounds), beside θ_min, φ and κ̂ that are defined. The tab opens with crates and dependency rows before the reader knows what a Body, a tolerance or a decision is, and the round rule, the heart of the kernel, has no worked example with numbers.
**Evidence:** ANV: "Here θ_min bounds the angle ..., φ is a spine's tangent bound, and κ̂ bounds principal curvatures"; the first section is "Crates".
**Fix:** Define p, n, s and the subscripts a and b above the table. Move the crate table to the end of the first section, after the operation contract. Add a worked example to "Certified decisions in rounds": two vertices 0.3ρ apart on a GP1 part, the filter, the refinement, the coincidence decision and the epoch it starts.

### R14-36 · Minor · Targets: CONTRACT, ANV
**Section:** Contract 5 `Body` (representation lattice); ANV Representation lattice, Subdivision surfaces
**Problem:** The contract says SubD ⊂ BRep is inexact "near extraordinary vertices and semi-sharp creases", ANV says "near extraordinary vertices with semi-sharp creases" and evaluates crease-free extraordinary vertices exactly by Stam's method. The contract claims an approximation the kernel does not make.
**Evidence:** Contract 5; ANV: "crease-free neighbourhoods of one extraordinary vertex use Stam's exact eigen-analysis".
**Fix:** Contract 5: "exact except near extraordinary vertices that carry semi-sharp creases, where the conversion records a bound".

### R14-37 · Minor · Targets: ANV, MEC
**Section:** ANV Blends (stage table); MEC Dress-up features
**Problem:** The stage table omits three cases common on cast and moulded parts: an edge whose convexity changes along its length (a boss meeting a curved wall), a fillet over part of an edge's length, and blend ends that cap or cliff against a non-tangent face. Mixed convexity is listed only at corners.
**Evidence:** ANV stage 1: "valence-3 corners with unequal radii and mixed convexity ... termination at smooth edges".
**Fix:** Add "convexity change along an edge" to stage 1, and "partial-length blends with setback ends" and "capped and cliff ends" to stage 2, with re-fillet slices for each.

### R14-38 · Minor · Targets: ANV, MEC
**Section:** ANV Offsets, shells and draft (`anvil::shell`); MEC Part features (Shell)
**Problem:** `anvil::shell` does not say whether it offsets by `Round` or `Natural`, which decides the commonest shell outcome: an inward shell of a filleted box whose fillet radius is below the wall. `Round` erodes the solid and turns small inner fillets into sharp edges; `Natural` collapses the offset fillet and fails with `WallCollapse`.
**Evidence:** ANV: "`Round` offsets are exact Minkowski sums with a ball ... `Natural` offsets extend and re-intersect offset faces"; `anvil::shell` "Solid, faces to open, thickness".
**Fix:** `anvil::shell` takes `mode: Round | Natural`, default `Natural` with collapsed blend faces removed and the inner edge left sharp (`Note::BlendCollapsed { faces }`), and ANV-O-OFF-3 adds a filleted box shelled inward past its fillet radius.

### R14-39 · Minor · Targets: MEC
**Section:** Direct edits, reuse and generated geometry (Machine elements)
**Problem:** The paragraph "PLT owns contract 13.3's rebuild rows. MEC keeps features cheap ..." sits under Machine elements, between the gear data table and the capability table, where it has nothing to do with gears.
**Evidence:** MEC, Machine elements, final paragraph.
**Fix:** Move it to "Conventions" under Part features, next to D-MEC-6.

### R14-40 · Minor · Targets: ANV
**Section:** Resolution, frames and scale; Oracles (ANV-O-SCALE-2)
**Problem:** "Identical geometry built two ways therefore has one `GeometryId`" overstates the tolerance rule. Two constructions of one shape rarely produce equal bits (a fillet built before or after a Boolean, a face cut by different tools at different angles); the rule only removes tolerance and resolution differences.
**Evidence:** ANV: "Identical geometry built two ways therefore has one `GeometryId`."
**Fix:** "Bit-identical geometry therefore has one `GeometryId` however large the tools that produced it; geometry equal within tolerance is compared by `anvil::deviation`."

## Verified claims

- ANV, MEC: ABC models come from Onshape, with STEP converted from Parasolid, native Parasolid files and the original FeatureScript | https://deep-geometry.github.io/abc-dataset/
- ANV: Parasolid's default tolerance is "normally 5.0e-9 metres" (Jackson 1995) | https://ftp1.cs.wisc.edu/pub/users/prem/jackson-SM-95.pdf
- ANV: Diazzi et al. report 100% success on 4,408 valid Thingi10K models, a 4.3 s mean, TetGen failing on 378, and 93.22% of meshes valid after rounding | https://arxiv.org/pdf/2309.09805
- ANV: Fornjot was archived on 19 June 2026 and says "Its goals were never reached" | https://github.com/hannobraun/fornjot
- ANV: OCCT's defeaturing reference defers its limitations to `BOPAlgo_RemoveFeatures` and removes only faces of solids | https://occt3d.com/dev/doc/refman/html/class_b_rep_algo_a_p_i___defeaturing.html
- MEC: Plasticity integrates Parasolid | https://plasticity.xyz/product
- MEC: ASME Y14.5-2018 (R2024) is on stabilized maintenance | https://www.asme.org/codes-standards/find-codes-standards/y14-5-dimensioning-tolerancing
- MEC: ASME Y14.41-2026 is listed and on stabilized maintenance | https://www.asme.org/codes-standards/find-codes-standards/y14-41-digital-product-definition-data-practices
- MEC: the CAx-IF PMI practice for AP242 is still version 4.1 of 20 June 2024 | https://www.mbx-if.org/home/cax/recpractices/
- MEC (R14-08): Creo regenerates geometry at the upper, middle or lower dimension bound | https://support.ptc.com/help/creo/creo_plus/usascii/model-based_definition/to_set_the_dimension_bounds_1.html
- MEC (R14-09): the fixed fastener formula T₁ + T₂ = H − F | https://www.gdandtbasics.com/?p=9816
