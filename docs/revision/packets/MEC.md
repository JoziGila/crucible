# MEC round 4 packet

Your tab is `docs/spec/06-mechanical.md` at v3 (tag `round-3`). Round 4 fixes, in one pass: the 80 third-review findings that target it (5 Critical, 42 Major, 33 Minor), its 0 `[unverified]` claims, its open questions and the known items below. Contract v7 is binding; its section 18 lists the rulings on this review, and many findings below are already settled there.

## Third-review findings

### R13-02 · Critical · Targets: CONTRACT, MEC, COV, KLN
**Section:** Contract 13.1 (validation paragraph), 13.2 (milestones 6 and 7); MEC "Design checks" (paragraph after D-MEC-30); KLN policy allowances; COV "Evidence levels" (D-COV-3)
**Problem:** MEC says "Phase 1 releases therefore need no allowance for those quantities", and KLN says the proof loads "supply their checks' model form". But the release comes first (milestone 6, run build tagged), the articles are made from it, and only then are they gauged (milestone 7). At release time the models are E2 at best, so every stress check is `Pass { conditional_on: [ModelForm] }`. D-COV-24 accepts only action-effect allowances that cover FE analysis, and no design code supplies one for a machined 6061 bracket or a printed lattice. That leaves a founder Waiver as the only route. Using the same article both to judge the design and to validate the model also breaks the held-out rule in 13.1. Finally, a strain gauge averages surface strain over a 1 to 6 mm grid. It cannot measure the class "regularized peak at a fillet" over ρ = 0.2 mm, so the gauged class never covers what the check decides on.
**Evidence:** MEC: "GP1's and GP2's strain-gauged proof loads validate immersed elasticity and the beam-lattice model to E3 … Phase 1 releases therefore need no allowance". Contract 5: a model-form bound applies "only when the validation plan lists that functional's response-quantity class (quantity, location type, regime)". Contract 13.2 milestones 6 and 7 put release before the physical runs.
**Fix:** Add a phase 1 validation campaign before milestone 6. Run it on separate validation specimens of the same alloy and process: notched and filleted plates, plus printed strut and lattice coupons. Measure surface strain with gauges and stereo DIC at the fillet roots, the DIC sampled at the regularization radius, with three or more replicates. Its response classes are "regularized surface peak at fillets, linear elastic" and "localized strut stress". Those E3 bounds then govern the GP1 and GP2 releases, and the GP proof loads become held-out confirmation. Delete MEC's and KLN's "need no allowance" sentences. Give the checks' predicted values in the gauge functional (a bounded linear functional with a `Guaranteed`-capable bound), so proof-load agreement is judged like for like.

### R13-05 · Major · Targets: COV, FLX, MEC, MFG
**Section:** COV "Dynamics and stability" (D-COV-30); FLX "Calibrated estimates" (`lattice.buckling`); MEC "Design checks" table
**Problem:** Almost every GP2 strut lands in D-COV-30's `Refuse` zone, so the phase 1 `lattice.buckling` class decides almost nothing. The escalation rungs (Johnson, tangent modulus, Perry–Robertson) have no FLX capability, calibration class or MEC check family in phase 1. An LPBF strut of about 1 mm with L/d ≈ 4 has slenderness 4L/d ≈ 16, so σ_cr,Euler = π²E/λ² ≈ 2,700 MPa for AlSi10Mg (E ≈ 70 GPa). That is far above any proportional limit, so the ratio is about 10 or more against D-COV-30's `Refuse` threshold of 1. For such stocky struts, compressive yield and plastic collapse govern, not buckling.
**Evidence:** D-COV-30: "Calibrated while the inelasticity ratio … stays below 0.5, Extrapolated to 1 and `Refuse` beyond." MEC's table names only `lattice.buckling` and `elasticity.eigen` for buckling.
**Fix:** In phase 1, decide strut compression with a strut-strength check: the localized axial stress against the as-built compressive strength, reduced by a Johnson–Perry–Robertson factor computed from the measured waviness. It reads `lattice.strut_stress`, so it needs no new class. Run eigen-buckling (`lattice.buckling`) only on members with ratio below 1, where it governs global lattice instability. Add the strength check to MEC's table and FLX's beam-lattice row. Have MFG's coupons include compression tests of single struts at the GP2 diameters.

### R13-08 · Major · Targets: FLX, COV, MEC, CONTRACT
**Section:** FLX "Calibrated estimates" (D-FLX-40), FLX-O-ERR-3 and FLX-O-ERR-5; contract 13.2 build program, item 3
**Problem:** The η99 calibration that every phase 1 `SignOff` check relies on has no independent reference. References are "solves two degrees higher" in the same aggregated CutFEM code. They share its cut quadrature, Nitsche penalty, aggregation and geometry handling, so a bias common to the family never shows. They "count only when their own error is below 10% of the bound", but that error can only be measured by the estimator family being calibrated. That is circular. Fitted FEM arrives only in phase 2.
**Evidence:** D-FLX-40: "References are solves two degrees higher, or full-resolution solids for lattices, and count only when their own error is below 10% of the bound." Contract 13.2: corpora "must agree with an independent source (… MFEM or libCEED …)".
**Fix:** Take phase 1 references from an independent code on fitted, curved high-order meshes, used as an oracle only: MFEM (BSD) or deal.II (LGPL, allowed as an oracle). Accept a reference only when a p-sequence (p, p + 1, p + 2) in that code shows exponential convergence and its Richardson spread is below 10% of the bound. Record each reference's code and mesh hash in the corpus. Keep same-code p + 2 solves only as a cross-check.

### R13-11 · Major · Targets: FLX, MEC
**Section:** FLX "Eigenvalue problems" (D-FLX-41); "Calibrated estimates" (`elasticity.eigen`, `lattice.buckling`)
**Problem:** Linear buckling solves K_G(u_h) φ = μ K φ, where the geometric stiffness depends on the prestress from the static solution u_h. Heuveline–Rannacher's DWR covers an eigenproblem with a fixed operator, so it leaves out the first-order contribution of the static solution's error through K_G. In stocky or stress-concentrated lattices that term can dominate. Calibration hides it only for the geometries in the corpus.
**Evidence:** D-FLX-41 cites only the eigenvalue DWR, plus Kato–Temple or Lehmann for the algebraic part; nothing estimates the prestress error. The buckling formula is "Buckling solves K_G φ = μ K φ with the positive definite K as B".
**Fix:** Treat the buckling factor as a coupled goal. Add the static adjoint driven by ∂μ/∂u = φᵀ(∂K_G/∂u)φ (one extra linear solve with the factored or preconditioned K) and include its DWR term in the discretization part. Give `lattice.buckling` and `elasticity.eigen` separate entries for frequencies (fixed operator) and buckling factors (coupled). Add a prestress-error case to FLX-O-SOLVE-6: a notched plate under compression.

### R13-12 · Major · Targets: FLX, MEC
**Section:** FLX "Eigenvalue problems" (D-FLX-41: "Conforming Ritz values bound the lowest eigenvalues from above, so a check reads λ_h − η")
**Problem:** The "unsafe side" argument rests on a conforming Ritz method, but Flux's phase 1 eigen-solves are not conforming. Aggregated CutFEM imposes Dirichlet conditions by Nitsche, so discrete functions do not vanish on the clamped boundary and the min–max upper-bound property is lost. Ghost-penalty terms then shift the spectrum, and eigenvalues can land below the exact ones. Beam lattices with calibrated joint stiffness are not a Ritz subspace of the solid either. A check that assumes λ_h ≥ λ may subtract η on the wrong premise, and calibration samples only the corpus's sign behaviour.
**Evidence:** D-FLX-13 (Nitsche, ghost penalty, aggregation) and D-FLX-44 (calibrated joints), against D-FLX-41's upper-bound premise.
**Fix:** Apply the bound two-sided: the check reads λ_h − η for lower limits and λ_h + η for upper limits (resonance avoidance bands). Calibrate η on |λ_h − λ| rather than on the one-sided gap. Keep the one-sided reading only for fitted conforming discretizations with strong Dirichlet conditions (phase 2). Add a case to FLX-O-SOLVE-6 where Nitsche-clamped plate frequencies fall below the reference.

### R13-13 · Major · Targets: FLX, COV, MEC
**Section:** FLX "Uncertainty quantification" (D-FLX-35); COV "Uncertainty"; MEC "Stack-up and variation analysis"
**Problem:** The worst-case remainder is not a bound. It has three flaws:
- k = 5 Lanczos steps give Ritz values inside the spectrum, so |θ|max ≤ |λ|max and the remainder ½·|λ|max·‖h‖² is underestimated.
- The Hessian is taken at the nominal point, while a Taylor remainder needs the curvature over the whole tolerance box.
- The result is labelled `Estimated` with no class or α (R13-10), yet MEC routes physics checks under tolerances through it.

A design whose worst corner sits in a direction Lanczos has not explored passes on an underestimate.
**Evidence:** D-FLX-35 says the method "runs k Lanczos steps on the Hessian over the scaled box (default k = 5) and adds the remainder ½·|λ|max·‖h‖². The result is `Estimated`". FLX-O-UQ-3 checks only "sampled extremes", which are not extremes over the box.
**Fix:** Keep the affine part, then confirm with one solve at the linear worst-case vertex. Run the solve at the vertex the signed sensitivities select. If the confirmed value minus the linear prediction stays within the remainder estimate, report the bound as `Estimated { Statistical { method: lanczos_random_start, α } }` with the probabilistic Lanczos bound at α = 0.01; otherwise raise `NonlinearResponse`. Change FLX-O-UQ-3 to compare against a certified optimizer (interval branch-and-bound) over the box on 20 analytic responses, stationary ones included.

### R13-16 · Major · Targets: FLX, COV, MEC
**Section:** FLX "Solvers" (no row for `solve_harmonic`), "Reduced models and surrogates"; COV "Dynamics and stability" (vibration and shock row, phase 2; launch environments row, phase 6)
**Problem:** Flux has no structural frequency-response, random-vibration or response-spectrum capability, and no damping model at all. Nastran, Ansys and Abaqus users rely on these every day (sine sweeps, PSD base excitation, shock response spectra). `solve_harmonic` appears only in the operation list and the problem-kind table: no capability row, failure, oracle, phase or error estimate. COV's phase 2 row ("Direct frequency response; PSD response") rests on nothing. COV also lists random vibration twice, in phase 2 and phase 6. Near resonance the error is amplified by about 1/(2ζ), which no budget row covers.
**Evidence:** In FLX, `solve_harmonic` occurs only at lines 28, 29 and 283. A search for "PSD", "random vibration", "Rayleigh damping" and "response spectrum" finds nothing in FLX. COV lists "Vibration and shock … PSD response … 2" and "Launch environments … Random vibration … 6".
**Fix:** Add an FLX capability section "Frequency and random response" in phase 2, owner FLX, and add it to contract 13.4. It covers:
- direct and modal frequency response with residual vectors;
- enforced base motion (large-mass and Lagrange methods);
- PSD response with spectral moments and Miles-equation checks;
- response spectrum combination (SRSS, CQC);
- damping as data: modal ζ, Rayleigh, hysteretic and frequency-dependent viscoelastic.

The error parts are modal truncation under `reduction` (residual-flexibility bound) and the discretization part propagated through the frequency-response function by the eigenvalue estimate, inflated by 1/(2ζ) within the half-power band. Oracles are NAFEMS R0016 cases and an SDOF closed form. Delete COV's phase 6 duplicate and point the launch row at this one.

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

### R14-23 · Minor · Targets: ANV, MEC
**Section:** ANV `anvil::silhouette`, `project_hlr`; MEC D-MEC-24
**Problem:** "Default 1 µm at model scale, under 0.01 mm at sheet scale" is two bounds that conflict on enlarged views: a MEMS die drawn at 100:1 has 1 µm at model scale equal to 0.1 mm on the sheet, above the sheet bound. On a 1:200 hull view the 1 µm model bound is far tighter than the sheet needs and costs certification time.
**Evidence:** ANV and MEC: "default 1 µm at model scale, under 0.01 mm at sheet scale".
**Fix:** One rule: the bound is 0.01 mm on the sheet divided by the view scale, and never coarser than the drawing's tightest tolerance divided by 10 at model scale.

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

### R15-11 · Major · Targets: ING, MEC
**Section:** ING "Inference and scalar flavors" (flavor table), D-ING-4, D-ING-20
**Problem:** Inside a body, a `Tol` argument is its nominal and the result is "Exact, unless returned itself". So `rib(t: 2 * thickness)` silently forwards no tolerance, while the same arithmetic on a `Tol` binding outside a parameter slot is affine and keeps it. One expression has two meanings depending on where the value came from, and the tolerance vanishes without a diagnostic, against contract 10's "Explicit over magic. No silent fallbacks."
**Evidence:** ING flavor table: "`Tol<Quantity<D>>` | The nominal; passing it on forwards the tolerance (D-ING-4) | Exact, unless returned itself"; Arithmetic on tolerances: "`a ± b`, `k * a` … | Exact affine combination".
**Fix:** Pick one meaning: arithmetic on a forwarded `Tol` stays an affine `Tol` (the monomorphized flavor carries through), and a slot declared `T` takes the nominal and forwards the whole form. If the founder keeps the nominal rule for cost, add the deny-by-default lint `ING-L-ToleranceDropped` when a `Tol`-flavoured value enters arithmetic whose result is neither forwarded nor returned, with fixes `.nominal` (explicit drop) or a `Tol` binding.

### R15-14 · Major · Targets: KLN, MEC
**Section:** KLN "Items" (Item record, D-KLN-45)
**Problem:** The Item record holds "number, kind, name, classification, home repository and path, make or buy, unit of measure and labels", while D-KLN-45 puts the number in source through `part(…, item:)` and the name is `part(…, name:)`. Number and name now live in two places that can disagree, and make-or-buy and unit of measure have no stated source.
**Evidence:** KLN: "An Item record holds number, kind, name, classification…"; D-KLN-45: "Item numbers live in source through `part(…, item:)` … where BOM nodes read them".
**Fix:** The Item record holds only lifecycle facts (revisions, states, effectivity, signatures, system of record) and is keyed by the item number. Identity attributes (number, name, kind, classification, make or buy, unit of measure) are evaluated from source (`part`, `bom_item`, MEC's equivalents) and read by BOM nodes. A changed name is then a source change reviewed like any other.

### R16-09 · Major · Targets: MEC, UIX
**Section:** MEC "Sketching: Entities and constraints"; UIX "Handles, push-pull and sketching"
**Problem:** The sketch entity and constraint tables have no trim, extend, split, sketch fillet, sketch chamfer, silhouette projection or DXF import. UIX says only "the usual drawing and editing tools". In a constraint-first source model, trim is a design question, not a UI detail. It turns a circle into an arc, splits a line into two entities with new helper names, and must decide what happens to constraints and dimensions on the removed span. Those choices change `EntityId` roles downstream.
**Evidence:** MEC's entity table (lines 106 to 116) and constraint table (lines 120 to 133); `rect` names its sub-entities, but nothing names the pieces of a split line. UIX line 449: "with the usual drawing and editing tools".
**Fix:** MEC specifies sketch edits that rewrite source. `trim(entity, at: point)`, `extend(entity, to: entity)` and `split_at(entity, point)` name their pieces `.a` and `.b` in curve direction. `corner_fillet(v, r)` and `corner_chamfer(v, d)` create a named entity `fillet(v)`. The constraint-transfer rule:
- Coincidence and tangency move to the surviving endpoint.
- Dimensions on a removed span are deleted, and the source diff lists them.
- Seeds of new points come from the solved geometry.

`import_dxf(asset, layers:)` writes entities with inferred coincidences within a stated tolerance and `fix` constraints, in phase 2 with ECO's DXF reader. Add oracle MEC-O-SK-10: trims on held-out sketches keep the solve report's freedom count and every surviving role.

### R16-10 · Major · Targets: MEC, UIX
**Section:** MEC D-MEC-13; "Derived parts and families"
**Problem:** D-MEC-13 rejects captured in-context references and requires skeletons and interface records. That is defensible, but no gesture or feature turns the commonest machinery-design act into an explicit reference: designing a bracket in the assembly by picking edges of the frame it bolts to. Without one, designers must stop, refactor the frame into a skeleton and come back. Many will instead copy dimensions by hand, which loses the very associativity the rule protects.
**Evidence:** D-MEC-13: "Implicit in-context references that capture another part's geometry are not supported." `derive(source, take, …)` takes outputs from "a feature here or in a pinned dependency", with no placement from an assembly path. Neither MEC nor UIX defines an in-assembly pick.
**Fix:** Add the gesture "Reference from assembly". It writes two explicit, reviewable edits:
1. If the provider's source is writable, a named output added to the provider feature's returned record (`mount_face`), with no new keyword. Otherwise a `derive(take:)` of the picked entity.
2. In the consumer, `context_ref(asm.path("frame/rail_2"), provider.mount_face)`, which carries the placement from that Instance path.

Cycles fail at compile time with the loop listed. The Proposal review shows the new cross-part edge in the dependency view, and moving the provider updates the consumer on rebuild. Phase 2, with oracle MEC-O-AS-14.

### R16-11 · Major · Targets: MEC, ECO
**Section:** MEC D-MEC-31; "Holes and threads"; "Standard parts and fasteners"; Open question 1
**Problem:** Thread diameter–pitch series, clearance holes and fastener dimensions are licensed data packages awaiting counsel, and "until then an organization supplies its own table packages". `ThreadSpec::iso_metric("M5")`, the tab's own example, needs ISO 261's coarse pitch, so a new user's first tapped hole can fail `UnknownSize`. Standard fasteners arrive only in phase 2, and only as licensed packages. Engineers used to free toolbox libraries and supplier catalogues would meet a paywall or an error on their first day.
**Evidence:** D-MEC-31; MEC's "Holes and threads" table marks `crucible::standards::thread_plans` and `clearance_holes` as "Licensed data"; Open question 1. The formula packages (`iso_metric_thread`, `unified_thread`) already compute profile and tolerance once diameter and pitch are given.
**Fix:**
1. Designations that carry their pitch (`M5x0.8`, `1/4-20 UNC`) resolve from the formula packages with no table. The UI always writes the explicit form, so source never depends on a series table.
2. The coarse-pitch lookup stays a data package, decided with counsel.
3. Clearance holes default to a Crucible-defined rule (nominal plus a class allowance), labelled `CrucibleDefined` and checked, until ISO 273 data can ship.
4. Fastener geometry defaults to manufacturers' `parts::` packages published under their own terms (D-ECO-18), the model supplier catalogues use. Standard-dimension packages stay optional.

State in the phase 1 row that a design compiles with no licensed package installed.

### R16-16 · Major · Targets: KLN, MEC, AGT
**Section:** KLN "Items"; MEC "Standard parts and fasteners"
**Problem:** The Item record has a "classification" field but no classification scheme, attribute search or shape search. Part proliferation is one of the costs enterprise PLM is bought to cut. Engineers search by class and attributes ("M6 standoff, 20 mm, aluminium") or by shape before creating a new item number. Crucible already computes name-free `GeometryId`s and certified mass properties, so it could do this better than incumbents, but the spec never asks it to.
**Evidence:** KLN line 509 lists "classification" among Item record fields; nothing defines it. No `api` Read method searches Items by attributes or shape.
**Fix:**
- A classification schema in the policy package: classes with typed attributes, so units check.
- A Read method `read.search_items(class, where:, shape_like: Body, tol)`, ranked by name-free shape descriptors cached per `GeometryId`.
- A new-part Proposal that shows the five most similar released Items.
- An `Info` check, `duplicate_candidate`, above a similarity threshold.

Phase 3, with oracle KLN-O-PLM-13: seeded duplicates in a 10,000-Item corpus rank first.

### R16-20 · Minor · Targets: MEC
**Section:** MEC "Direct edits and wraps"; Phasing
**Problem:** Phase 1 offers only push-pull on imported B-reps, while delete, move and replace of faces wait for phase 2. Removing fillets, logos and holes from a supplier's STEP file is the most frequent direct edit. Phase 1 needs it, because its enclosure checks run against imported boards and its assemblies use supplier models.
**Evidence:** MEC: "Phase 1 offers push-pull; moves, replacements and rule detection follow in phase 2." `anvil::defeature` already exists for `InstanceRepr::Defeatured`.
**Fix:** Move `delete_faces` with neighbour healing, and `defeature(body, rules)` as a feature, to phase 1, both using MEC-O-PF-9. Keep moves, replacements and rule detection in phase 2.

### R16-21 · Minor · Targets: MEC, KLN, ELX
**Section:** MEC "Design checks" (`decides_on` table: mass); MEC "Standard parts and fasteners"; ELX "Electrical facets"
**Problem:** Mass checks need `Guaranteed` bounds, and mass properties come from geometry and `Material` density. Purchased parts arrive as simplified or hollow STEP bodies: a motor, a battery, a populated board. Their computed mass and centre of gravity are therefore wrong by large factors, yet they carry certified-looking bounds. No record lets a datasheet mass override the computed one.
**Evidence:** MEC: "Fits, clearance, interference, thickness, mass | `Guaranteed`". ELX's catalog facets list a "3D body" and "Specifications" but no mass. MEC hands Flux "mass properties with their bounds" (D-MEC-12).
**Fix:** Add `part.mass_properties(declared: { mass: Tol<Mass>, cg: Tol<Point>, inertia: Option<…> }, source: Datasheet | Measured(Evidence))`. It replaces computed values in roll-ups, and reports label it "declared". Catalog parts carry a mass facet. A `Warning` check flags purchased Instances whose computed mass is used without a declaration.

### R16-23 · Minor · Targets: MFG, MEC
**Section:** MFG "Tools, stock, setups and workholding" (setup sheet, blank and hand-off)
**Problem:** Multi-operation parts need in-process drawings: the shape and dimensions after setup N, with grinding or heat-treat allowances. Machinists and inspectors work to them between operations. MFG already computes setup N's output stock as setup N+1's blank, but only the setup sheet is a drawing, and it shows offsets and tools rather than in-process dimensions.
**Evidence:** "Blank and hand-off | … setup N's stock is setup N+1's blank". `setup_sheet` lists offsets, fixtures, tools and workingsteps.
**Fix:** Add `in_process_drawing(program, after: SetupRef, template)`, built from the hand-off Body. It is dimensioned from the setup's datums, lists allowances per face, and carries characteristics that MFG's allocator labels as in-process. Phase 2, with MFG-O-SETUP-1.

### R16-28 · Minor · Targets: MEC, MFG, ELX
**Section:** Sources and in-text citations
**Problem:** The three primary tabs use three citation styles: MEC quotes inline and lists URLs, MFG uses bracketed labels (`[Haas G-codes]`), and ELX uses numbers (`[85]`). A reader moving between tabs cannot tell at a glance what `[85]` is, while `[IPC store]` is self-describing.
**Evidence:** ELX: "IPC-6012F, IPC-A-610J and IPC J-STD-001J … [85][86]". MFG: "[IPC store]". MEC: "[ISO 10303 notice]", plus unlabelled lists.
**Fix:** Adopt MFG's bracketed short labels in every tab, and add the rule to contract 11's style list.

### R16-29 · Minor · Targets: ELX, MEC, MFG
**Section:** ELX "Wire harnesses"; MEC "Routing"; MFG "Electronics and harness manufacturing handoff"
**Problem:** A harness engineer's work is split three ways by D-MEC-26: connectivity and wire tables in ELX, 3D routes and formboard geometry in MEC, and the manufacturing package in MFG. No tab walks through one harness from connector selection to formboard. The phases also differ (MEC 3, ELX 4, MFG 4), and the reader has to assemble that order alone.
**Evidence:** D-MEC-26; ELX: "ELX's part lands in phase 4 … MEC's phase 3 routing uses declared bundle diameters until then"; MFG's harness row in phase 4.
**Fix:** Open ELX's "Wire harnesses" with a five-step numbered walkthrough: connectivity, route, lengths, checks, package. Each step names its owner and phase in one line, which "say it once" permits because the step only points to the owner.

### R16-31 · Minor · Targets: MEC
**Section:** MEC "Sheet metal"
**Problem:** `SheetParams` is named but never defined. Sheet-metal designers work from gauge or style tables, per material and thickness, that set the default inside radius, relief type and size, and K factor or bend table. Without such a record, every part restates them, and `check::sheet` cannot say which shop standard a part follows.
**Evidence:** "A sheet-metal part is a `SheetBody`: the folded `Body`, the flat `Body`, a bend table and `SheetParams`." No other mention appears.
**Fix:** Define `SheetParams { material, thickness: Tol<Length>, inside_radius, relief: ReliefRule, bend_rule: BendRule, min_flange }` and `SheetStyle`, a shop data package of `SheetParams` rows keyed by (material, gauge). `sheet_from(…, style: shop::al5052_2mm)` reads it, and `check::sheet` reports the style it applied. Phase 2, with MEC-O-SM-1.

### R19-01 · Critical · Targets: OVERVIEW, MEC, MFG, KLN, UIX, ANV
**Section:** OVERVIEW "Where the field stands"; the lead of each primary tab
**Problem:** The bar is that Crucible wins on what AI-built clones cannot copy quickly, yet no tab names a clone except Zoo, and no page states the advantages in a user's terms. SolidCraft already ships, under MIT or Apache-2.0, much of MEC's phase 1 and 2 surface: sketches with a solver, a timeline of features, sheet metal, assemblies with joints and motion studies, STEP, IGES, 3MF, STL and OBJ, and MCP control. CADCraft is a clean-room AutoCAD with DWG read and write, and it plans its own gaps in agent-hours. Against this, Crucible's phase 1 has no sheet metal, kinematics, IGES or DXF (MEC Phasing; ECO formats), and the Overview's comparison bullets cover languages, kernels and agents only.
**Evidence:** SolidCraft README (https://github.com/bherbruck/solvecraft): "An open-source parametric 3D CAD application built in pure Rust", with "Assemblies with nested components and occurrences, joints, motion studies, contact sets, interference and material-aware mass properties". CADCraft README (https://github.com/storytold/cadcraft): "a clean-room reimplementation of Autodesk AutoCAD"; its docs/gaps.md (https://github.com/storytold/cadcraft/blob/main/docs/gaps.md) costs work in agent-hours. Zoo Design Studio (https://zoo.dev/design-studio): Zookeeper is "built into Zoo Design Studio". Grep of `docs/spec/` finds no mention of SolidCraft or CADCraft.
**Fix:** Add an Overview section "Why Crucible, and why not a clone" with one table: capability · what incumbents give · what the clones give · Crucible's mechanism · why it cannot be copied in weeks. Its rows: certified geometry with stated error and oracles (ANV); `GeometryId` identity that makes approvals, the shared cache and duplicate detection exact (KLN, ANV); merges that refuse broken checks, new interference and touched-entity conflicts (KLN, see R19-12); units and tolerances as types (ING); every check gating every merge with verdict history (MEC, KLN); validated physics with evidence levels (COV); approvals over content digests and the machine gateway (MFG, AGT); PLM records in the design repository (KLN). Each primary tab's lead gains one sentence naming its advantage over incumbents. State a phase 1 parity floor: DXF write and IGES read join phase 1 (both are formats an AI clone already ships), and say plainly that sheet metal and kinematics arrive in phase 2.

### R19-02 · Critical · Targets: MEC, KLN, UIX
**Section:** MEC Exploded views, subassemblies and interfaces (D-MEC-13); MEC Derived parts and families
**Problem:** D-MEC-13 forbids every reference to another part's geometry except through skeletons and interface records planned in advance. Designing a cover to fit a housing, a bracket to clear a cable run or a guard around a mechanism in its assembly position is the daily work of machine designers, and every incumbent supports it. Onshape does it without hidden coupling: an in-context reference is a snapshot of the assembly, never updated automatically, so the graph stays acyclic. Crucible already has every piece needed (pinned references in `ingot.lock`, `derive`, Proposals). The tab also never says that one feature may return several Parts designed together, Onshape's Part Studio pattern, or how their identities work.
**Evidence:** MEC D-MEC-13: "Implicit in-context references that capture another part's geometry are not supported"; *Rejected:* "edit-in-context with captured references, as in SOLIDWORKS". Onshape, Modeling in context (https://cad.onshape.com/help/Content/Assembly/modeling_in_context.htm): "An Assembly context (snapshot) is created", "Updates are never applied automatically", "These references are never lost or broken". Creo (https://support.ptc.com/help/creo/creo_plus/usascii/assembly/asm/About_Copy_and_Publish_Geom_Feat.html): Copy and Publish Geometry "are top-down design tools to associatively communicate design criteria".
**Fix:** Revise D-MEC-13: cross-part references go through skeletons, interface records or context pins. Add `context(of: assembly_feature, at: Pin, take: [Query]) -> Context` to `std::mech::asm` (phase 2, for GP3's covers and GP4's guards). A context is a past evaluation of the assembly at a pinned `ChangeId`, recorded in `ingot.lock` as `{ source, selector: Change, resolved }`, and returns the taken Bodies, frames and sketches transformed into the consuming Part's frame by its Instance placement at that Change. Because the pin names a past Change, the consuming Part may sit inside that assembly without a cycle. "Update context" is a Proposal that moves the pin and shows the geometry diff; a lost reference is a typed `ResolveError`; two branches that move one pin differently give `Conflict::Lockfile`. UIX adds "Edit in context": the assembly drawn transparent, selections becoming context `Query`s. State that a feature may return a record of Parts (`-> (Housing: Part, Cover: Part)`), each with its own item number and `GeometryId`, as the multi-part design pattern.

### R19-03 · Major · Targets: MEC, CONTRACT, ECO
**Section:** MEC Packages (D-MEC-31); Holes and threads; Open questions 1
**Problem:** R11-30's fix created a new problem: thread series, clearance holes and fasteners are now licensed tables, and until counsel rules "an organization supplies its own table packages". The tab's own example, `ThreadSpec::iso_metric("M5")`, then fails with `UnknownSize`, since the coarse pitch of M5 comes from ISO 261. Every incumbent and the SolidCraft clone ship holes and threads that work on first use; Crucible's GP1, a machined bracket, needs them in phase 1, yet the decision waits until "before phase 1".
**Evidence:** MEC: "Thread plans, clearance holes, fasteners and steel sections are such tables"; Open question 1: "Kept open for counsel's review before phase 1 (D-MEC-31); until then an organization supplies its own table packages." MEC housing example: `HoleSpec::tapped(ThreadSpec::iso_metric("M5"), depth: 10mm)`. SolidCraft README lists "holes, threads" among its features.
**Fix:** (1) `std::standards::iso_metric_thread` and `unified_thread` accept full designations that carry the pitch (`"M5x0.8"`, `"1/4-20 UNC-2B"`) and compute every diameter and limit from the ISO 68-1, ISO 965-1 and ASME B1.1 formulas, with no table; a designation without pitch resolves through the series package, and its `UnknownSize` fix rewrites the call to the explicit form. (2) Clearance holes accept an explicit diameter or fit (`clearance(5.5mm)`, `H13`) without a table. (3) Make counsel's ruling on the series and fastener tables a phase 0 gate item in contract 13.1, beside the freedom-to-operate opinion, so GP1 never depends on a customer's tables.

### R19-04 · Major · Targets: CONTRACT, MEC, MFG, KLN, UIX, ANV
**Section:** Contract 8 (the State of the art table); State of the art in MEC, KLN and UIX
**Problem:** Contract 8's table compares methods with "the leading implementation to beat", so whole areas of incumbent capability never appear. MEC's table has no row for weldments, mould tooling, routing, configurations, top-down design or rendering, names Onshape alone for sheet metal and OCCT for drawings, and D-MEC-37 limits published comparisons to open implementations. KLN has two PLM rows, and UIX compares its renderer with Nanite and Bevy, not with CAD products. Gaps such as R19-02, R19-05, R19-09 and R19-10 therefore pass every tab's own check.
**Evidence:** MEC State of the art rows "Sheet metal … Onshape sheet metal" and "Hidden-line removal … Open CASCADE `HLRBRep_Algo`"; MEC D-MEC-37: "published comparisons use only open implementations such as OCCT"; KLN State of the art: only "PLM change control" and "Variant management" concern PLM.
**Fix:** Add to contract 8 a second required table in the primary tabs (MEC, MFG, KLN, UIX, ANV), "Parity with incumbents": capability · incumbent and its documented feature (cited from vendor documentation) · Crucible's capability row and phase · Ahead, Equal, Later or Out of scope, with one reason. Comparing documented features is not a benchmark of a commercial kernel, so D-MEC-37 still holds. The spec check counts one row per incumbent feature listed in this review and fails a tab that omits one without an Out-of-scope reason.

### R19-09 · Major · Targets: UIX, MEC
**Section:** UIX Styles, appearance and color; Phasing
**Problem:** Photorealistic rendering arrives in phase 5, though industrial designers, marketing and design reviews use it from the first concept, and Onshape builds it into its browser product linked to the live model. The stated reason, experimental ray queries in wgpu, does not require the delay: a path tracer can traverse a BVH in compute shaders on G1 and G2, or on the CPU in `apps/headless-render`, and its images are non-canonical Snapshots anyway (D-UIX-26).
**Evidence:** UIX: "A path-traced Realistic preview arrives in phase 5, since wgpu's ray queries are experimental." Onshape Render Studio (https://cad.onshape.com/help/Content/render-studio.htm): it "allows the creation of photorealistic scenes from imported Part Studios or Assemblies", scenes are "linked to their part, Part Studio, or Assembly", and output is JPG or PNG.
**Fix:** Move a progressive path tracer to phase 3 (GP5's moulded enclosure is the first consumer product): compute-shader BVH traversal over `DisplayPackage` clusters on G1 and G2, a CPU path in `apps/headless-render` for G3 and servers, the OpenPBR appearances already specified, HDR environments as packages, and render scenes as shared `ViewState` files so they update with the model. Output is a Snapshot with `PlatformClass::Unverified`. Until then, state glTF (phase 2) and OpenUSD (phase 3) export to external renderers as the supported path.

### R19-10 · Major · Targets: ECO, MEC, UIX
**Section:** ECO Mechanical CAD and product data (DXF; DWG); MEC Drawings capability table
**Problem:** DXF waits for phase 2 and DWG for a licensed translator in phase 3, though shops quote, cut and archive from DXF and DWG every day. An open path exists: the acadrust crate reads and writes DXF R12 to 2018 and DWG R13 to 2018 under MPL-2.0, which contract 7.7 allows to link, and CADCraft already ships DWG through it. Crucible also has no stated way to make a 2D-only document (a layout, a plate drawn flat, an edited supplier DWG), which AutoCAD users and the CADCraft clone treat as basic.
**Evidence:** ECO: "DXF; DWG | DXF at phase 2 | R/W | … | Build; License | 2; 3"; MEC drawings row: "then DXF (2) and DWG through a licensed translator (3)". acadrust 0.4.1 (https://docs.rs/crate/acadrust/0.4.1): "MPL-2.0", "DWG Read/Write — Native binary, R13–R2018". Contract 7.7: "MPL-2.0 files may be linked" with notices and a source offer.
**Fix:** Move DXF write of drawing sheets and planar sections to phase 1, and DXF and DWG read and write to phase 2 through acadrust (linked under 7.7) or an own codec with acadrust as the oracle; the licensed translator becomes the fallback for versions acadrust lacks. In MEC, state that a drawing may hold 2D-only sheets: sketch geometry, layers as attributes, blocks as Ingot functions, hatches and dimensions, with an imported DWG becoming an editable drawing program through an import expression, as for 3D Assets.

### R19-11 · Major · Targets: MEC, FLX, ANV
**Section:** MEC Lattices; FLX Topology optimization; ANV Conversions and error propagation
**Problem:** Generative design with manufacturing methods is a standard Fusion workspace, and in Crucible it exists only as FLX building blocks: no MEC feature takes a design space, preserved regions, load cases and manufacturing methods and returns outcomes to compare. Phase 1 serves additive parts only. Milling and casting constraints arrive in FLX's phase 2, but a machined or cast outcome needs fitted B-rep faces, which ANV ships in phase 3, so generative design for subtractive parts is phase 3 without anyone saying so. Crucible's real advantage, that preserved interfaces keep their exact faces, `HoleSpec`s and GD&T through leaf-preserving conversion, is stated only for GP2's lattice.
**Evidence:** Fusion, Specify manufacturing methods (https://help.autodesk.com/cloudhelp/ENU/Fusion-GenerativeDesign/files/GD-SPECIFY-MFG-METHOD.htm): Unrestricted, Additive, Milling on "2.5-, 3-, or 5-axis" configurations, 2-axis cutting and casting. FLX density method: "1 (compliance, volume), 2 (stress, robust, manufacturing)". ANV: "Implicit → BRep … 1 (facet), 3 (fitted)". MEC D-MEC-34: a STEP hand-off "needs the region converted to B-rep within the same tolerance".
**Fix:** Add `std::mech::generate(space: Body, keep: [Query], avoid: [Body], cases, methods: [Method], objectives) -> [Outcome]` to MEC: phase 1 for `Additive` and `Unrestricted`, phase 2 for `Milling { axes, tool }`, `TwoAxisCutting` and `Casting { pull }` with FLX's manufacturing constraints. Outcomes are variants for UIX's variant grid, each carrying mass, margins and MFG's planned cost. Move ANV's fitted Implicit → BRep row (D-ANV-36) to phase 2 so subtractive outcomes release through STEP; until it ships, state that phase 2 outcomes for milling release as facet B-rep only to mesh-capable processes. Add one line to MEC's lead: kept interfaces stay exact, named and toleranced in every outcome.

### R19-13 · Major · Targets: ANV, MEC
**Section:** ANV Blends (D-ANV-29); MEC Dress-up features; ANV-O-BLEND-5
**Problem:** The phase 2 gate target is "97% of all cases", but corners of valence four and above and blends across facet faces are stage 3 (phase 3), and G3 sections stage 4 (phase 4). Either the corpus holds almost none of those configurations, and the target says nothing about them, or the target cannot be met by the phase 2 engine. Valence-four corners are routine where four filleted edges meet on castings and moulded ribs, and the tab's only named comparison, OCCT, is the builder that fails there, so the target says nothing about parity with the commercial kernels users switch from.
**Evidence:** ANV D-ANV-29: "Targets are 95% of stage-1 cases at the phase 1 gate and 97% of all cases at phase 2"; stage table: "3 | Corners of valence four and above; blends across facet faces | 3". ANV State of the art: OCCT's builder "rejects contour ends where four or more edges meet".
**Fix:** Restate the targets per stage: 95% of stage-1 cases at phase 1, 97% of stage-1 and stage-2 cases at phase 2, 95% of all cases at phase 3, each report listing the corpus share per stage. If the corpus share of valence-four corners exceeds 3%, bring valence-four corners with equal convexity forward to phase 2 for GP3's cast housing.

### R19-14 · Major · Targets: MEC, UIX
**Section:** MEC Entities and constraints; UIX Handles, push-pull and sketching
**Problem:** Sketching is the most-used tool in every CAD system, and its editing operations are unspecified: trim, extend, split, sketch fillet and chamfer at a corner, offset of a chain in the GUI, and convert entities. UIX promises "the usual drawing and editing tools", but principle 2 requires each gesture to become a defined source edit, and MEC defines none. CADCraft lists trim, offset, fillet and arrays, and SolidCraft lists its sketch tools.
**Evidence:** UIX: "Sketches start on a plane … with the usual drawing and editing tools and construction geometry." MEC's entity and constraint tables list no trim, extend, split or corner operation. CADCraft README (https://github.com/storytold/cadcraft): "modify tools such as trim, offset, fillet, and arrays".
**Fix:** Add a "Sketch edits" table to MEC (phase 1) mapping each tool to its source rewrite: `trim` deletes the selected segment and writes `split_at` points with `point_on` constraints on the kept pieces (or, for profiles, selects regions of `make_regions` so no geometry is deleted); `extend` adds `point_on` to the target; `sketch_fillet(corner, r)` inserts an `arc` with two `tangent` constraints and moves the endpoints; `sketch_chamfer` likewise with a line; `offset` and `use_edges` as today. Each edit is one Change, keeps the `CallSite`s of untouched entities, and has an oracle on the SketchGraphs replay corpus.

### R19-18 · Minor · Targets: ANV, MEC
**Section:** ANV Blends (D-ANV-29); ANV and MEC State of the art, Blends rows
**Problem:** The re-fillet benchmark's originals come from public Onshape documents, and Onshape runs on Parasolid, so every case is a fillet Parasolid made. The benchmark already measures parity with the commercial kernel users switch from, but both tabs name OCCT as the implementation to beat and report only OCCT's rate.
**Evidence:** Contract 13.3: the ABC subset holds documents "for which the Onshape API shows a Free Plan owner". engineering.com (https://www.engineering.com/parasolid-d-cubed-and-siemens-the-heart-of-your-cad-software-belongs-to-another/): "SOLIDWORKS and Onshape, arch-competitors to Solid Edge, both use the Parasolid kernel." ANV-O-BLEND-5: "OCCT 8.0's rate reported".
**Fix:** In both Blends rows, name Parasolid as the reference ("the corpus originals are Parasolid results") and state the targets as "95% and 97% of the fillets Parasolid made in the corpus". This uses stored public results only, so D-MEC-37 holds.

### R19-19 · Minor · Targets: UIX, MEC
**Section:** UIX Handles, push-pull and sketching; MEC Assemblies capability table
**Problem:** MEC ships mates in phase 1, but UIX puts mate glyphs and Instance dragging in phase 2 and never says how a phase 1 user places an Instance or adds a mate without typing Ingot. The SolidCraft clone offers joints in its GUI today.
**Evidence:** MEC: "Mate solve and diagnosis | … | 1, 2, 3 (cam)". UIX: "In assemblies (phase 2), mates draw as glyphs and Instances drag within their degrees of freedom"; "Assembly drag and motion | … | 2".
**Fix:** State the phase 1 path in UIX: Insert Instance and Add mate are generated feature dialogs (from `instance` and the mate functions' metadata) whose two frame fields take selections as `CoordSys` queries, with the solved placement previewed; glyphs and dragging stay phase 2.

### R19-20 · Minor · Targets: MEC, UIX
**Section:** MEC Reference geometry (`std::mech::refgeom`); UIX Handles, push-pull and sketching
**Problem:** There is no reference image: designers trace concept sketches, photos and scanned legacy drawings on a scaled image in a sketch plane.
**Evidence:** Fusion, Insert canvas (https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-INSERT-CANVAS.htm): "insert an image onto a planar face, plane, or sketch plane to use as a reference". No MEC or UIX row places an image.
**Fix:** Add `canvas(image: Asset, on: CoordSys, calibrate: (Point, Point, Length), opacity)` to `refgeom` (phase 2): display-only, non-definitional, outside the `ItemDefinition`, and an instruction-capable image for agents (AGT's rule). UIX traces sketch entities over it with the usual inference.

### R19-21 · Minor · Targets: MEC
**Section:** MEC Mates
**Problem:** The mate table has no path mate (a frame constrained to follow a curve, for carriages on curved tracks and cable carriers) and no belt or chain coupling between pulleys, both common in conveyor and machine design, which MEC's own conveyor example belongs to.
**Evidence:** MEC Mates table ends with `gear`, `rack_pinion`, `screw`, `linear` and `cam`. SOLIDWORKS offers path, belt and chain tools [unverified].
**Fix:** Add `path(frame, curve: Query, along: Tangent | Fixed)` (phase 2) and `belt(pulleys: [Instance], ratio from pitch diameters)` (phase 3) as constraints on the shared solver, with `belt` also creating a belt Body of evaluated length and an Instance-set count for chain links.

### R19-22 · Minor · Targets: MEC
**Section:** MEC lead; Tolerancing; Design checks; State of the art
**Problem:** MEC's strongest user-visible wins are buried: 1D and 3D stacks, completeness and design checks run as checks in CI on every merge with verdict history, where MEC's own table names a separate product (Tecnomatix Variation Analysis) as the leader. Interface records give matched clearance and tapped holes in mating parts from one record, the job of an incumbent hole-series tool, without the tab saying so.
**Evidence:** MEC State of the art: "3D tolerance analysis | … | Siemens Tecnomatix Variation Analysis (formerly VSA)". MEC's lead describes the library, not what a SOLIDWORKS or NX user gains.
**Fix:** Add one sentence to MEC's lead: "Tolerances, stacks, completeness and design checks are checks that every merge evaluates, so a change that breaks a stack cannot reach `main`." In State of the art, add a reason column entry per row naming what an incumbent user gains. Under Skeletons and interfaces, add an example in which `MotorMount` drives a clearance hole in one part and a tapped hole in the other.

### R19-27 · Minor · Targets: UIX, MEC
**Section:** MEC Derived parts and families; UIX Model tree, dialogs and version history
**Problem:** Part families are `family(f, key:, rows: table { … })`, and UIX gives no table editor, so a designer who maintains a 200-row family, as incumbents' design tables allow, edits text.
**Evidence:** MEC: "`family(f, key:, rows: table { … })` checks every row's types and units at compile time". UIX's variant grid shows variants but edits no rows.
**Fix:** Add a family table editor to UIX (phase 2): a grid over the `table { … }` literal with typed, unit-aware cells, paste from spreadsheets, per-row build status from `RowFailed`, and each edit one Change.

### R20-01 · Critical · Targets: FLX, COV, MEC, UIX
**Section:** FLX "Contact, constraints and fracture"; FLX "Operators, problem kinds and checks"; COV "Solid mechanics"; UIX "Studies and results"
**Problem:** Flux has no remote point (a rigid or a distributing coupling from a face to a reference point), no point mass with rotary inertia, no grounded or two-point spring and damper, no six-DOF bushing and no fastener or spot-weld connector. FLX's constraint row lists "multi-point, periodic, cyclic and integral constraints" generically, and UIX's study setup offers only "fixed, force, pressure, preload, temperature, convection". An analyst who models a motor on a bracket, a load through an unmodelled clevis, or a PCB on standoffs uses these primitives in nearly every Ansys or Nastran model; in Crucible they must model the motor and clevis as solids, which is slower, changes the answer at the attachment and breaks modal mass.
**Evidence:** Ansys Mechanical's remote point behaviors: Deformable is "similar to the Mechanical APDL constraint defined by the RBE3 command", Rigid "similar to ... the CERIG command" (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_Geometry_Behavior.html). Ansys's Nastran export maps rigid and deformable remote points to RBE2 and RBE3, bushings to CBUSH and point masses to CONM2 (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_NASTRAN_export_supported_features.html). FLX line 593 and UIX line 591 name none of them.
**Fix:** Add an FLX subsection "Idealizations" under "Contact, constraints and fracture" with one capability row each, phase 1 for the first three and phase 2 for the rest:
- `remote_point(faces, at: CoordSys, behavior: Rigid | Distributing { weight: Uniform | Area | Distance })`, enforced by multipliers on fitted meshes and Nitsche on the octree, returning a point whose six DOFs take forces, moments, displacements, masses and springs. Oracle FLX-O-IDEAL-1: reactions and displacements equal a fitted RBE2/RBE3 reference on 20 cases; a distributing coupling adds no stiffness (eigenvalues of a free plate unchanged within 10⁻⁸).
- `point_mass(at: remote_point or vertex, m, J: Tensor)`; checks of mass properties include it (MEC).
- `spring(a, b, k: Tensor6, c: Tensor6)` and `bushing(...)` with grounded variants.
- Phase 2: `fastener(holes, spec)` from MEC's `fasten` Instance sets, as a beam-plus-distributing-coupling connector with VDI 2230 preload, and `spot_weld(points, d)`.
Each primitive is an Ingot function over `Query` targets, so it stays associative; UIX's study template adds them to the condition list. COV adds a regime variable "coupling region diameter over local wall thickness" so a rigid coupling on a thin wall is `Flag`, since rigid couplings stiffen thin walls.

### R20-08 · Major · Targets: FLX, MEC
**Section:** FLX "Contact, constraints and fracture"; MEC "Interference and clearance"
**Problem:** The commonest analyst task, a static or modal solve of a multi-part assembly with bonded and frictionless interfaces, has no defined path before phase 3 on the immersed octree: bonded interfaces use mortar on fitted tetrahedra in phase 2, and immersed Nitsche contact waits for phase 3. Phase 2 users therefore mesh, losing Crucible's no-meshing advantage exactly where assemblies begin. Automatic interface detection, which Abaqus offers as general contact over an "all-inclusive" surface, is only implied by MEC's "contact candidates" and UIX's "unconfirmed contacts".
**Evidence:** FLX lines 594 and 595; Abaqus's general contact "allows for a highly automated contact definition" (https://abaqus-docs.mit.edu/2017/English/SIMACAEGSARefMap/simagsa-c-cntgeneral.htm).
**Fix:** Add to FLX a phase 2 row "Immersed tied interfaces": Nitsche tie across `dI` between Instances on the octree, with interfaces found by MEC's interference classes (touching faces within the definition tolerance), default `Bonded` for welded or glued contact and `Frictionless` otherwise, each listed for confirmation in UIX's pre-flight. Oracle: a two-block tied patch test and a bolted lap joint against fitted mortar, inside the fitted model's budget. Keep mortar on fitted meshes for frictional contact as now.

### R20-09 · Major · Targets: FLX, COV, MEC
**Section:** FLX "Domains and values" (`LoadCase` index set), "Post-processing and display"
**Problem:** `LoadCase` is an index domain, but nothing defines load-case combination: factored linear superposition, envelopes (max and min over cases with the governing case recorded), and code combinations (Eurocode ULS and SLS, AISC LRFD). Nastran subcases and Ansys solution combinations do this routinely, GP8's structural check needs it, and the error budget of a combined result (bounds add only in one norm; superposition is valid only for linear solves) is unspecified.
**Evidence:** Contract section 5 lists `LoadCase` among `Field` index sets; `grep -i "load combination"` over `docs/spec` returns nothing.
**Fix:** FLX adds `std::sim::combine(cases, factors)` and `envelope(cases, by: Max | Min | AbsMax)` returning Fields over `(Body, Combination)` plus a `PerEntity` governing-case Field. Superposition requires every case from one linear solve and fails with `NonlinearSuperposition` otherwise; budgets combine by the factors' absolute values per norm. COV's civil rows cite a `std::systems` code-combination package per standard edition (licensed data, D-ELX-30's rule). Phase 2; oracle: hand-combined frame cases.

### R20-24 · Minor · Targets: ELX, MEC
**Section:** ELX "Hierarchy, buses and ports", "Wire harnesses"
**Problem:** Altium sells multi-board design: a system schematic of board modules, board-to-board connectivity checks and a multi-board assembly in an enclosure with collision checks. Crucible does more by construction, with one Network across boards, harnesses and enclosure. But ELX never says so, and it has no check for directly mated board-to-board connectors (pin 1 to pin 1 mirrored across a mezzanine), the commonest multi-board error.
**Evidence:** Altium's multi-board ERC "will detect net-to-pin assignment errors and pin-to-pin interconnection wiring errors", and its assembly checks collisions (https://altium.com/documentation/altium-designer/multi-board-design).
**Fix:** Add `mate(connector_a, connector_b)` to ELX, deriving pin correspondence from the catalog parts' mating facet and the Assembly placement. Rule `mated_pinout` fails on mirrored or role-incompatible pairs (phase 3, ELX-O-NET-2). Add one sentence under D-ELX-7 stating that multi-board systems are one Network and one Assembly with no system-level sync step.

### R20-32 · Minor · Targets: FLX, MEC
**Section:** FLX "Shape, parameter and experimental design"
**Problem:** Structural optimizers in OptiStruct and Nastran SOL 200 size shell thicknesses (free-size) and optimize composite ply shapes, counts and stacking under manufacturing rules. Flux offers density topology optimization and shape optimization, but no shell-thickness or ply optimization, which GP10's wing box will need.
**Evidence:** FLX "Topology optimization" table, with density, graded lattice, level set and multiphysics rows only.
**Fix:** Add "Shell sizing and laminate optimization" rows: thickness Fields on mid-surface shells with adjoints (phase 2), and ply-shape, ply-drop and stacking optimization with MEC's ply rules (phase 6, GP10).

### R21-02 · Major · Targets: ING, FLX, COV, KLN, MFG, ELX, AGT, UIX, PLT, MEC, ANV, ECO, CONTRACT
**Section:** Every design section's decisions; "Open questions"; "Contract change requests"; contract lead
**Problem:** The tabs read as the minutes of their own revision. Review finding ids appear as evidence inside running prose, decisions end in "(revised in round N)", "Rejected" clauses name "the round 2 rule", and "Open questions" sections list declined findings rather than open questions. A reader who was not in the review cannot use any of it, and the Adversarial review tab already owns this history.
**Evidence:** Counted before each tab's "Open questions": finding ids such as "(R3-37, R9-40)" appear 112 times in PLT, 62 in FLX, 56 in MFG and AGT, 48 in ELX, 45 in UIX, 43 in KLN, 34 in COV and 26 in ING (482 in all), while ANV, MEC and ECO show that a tab reads well without any. "(revised in round N)" appears 235 times across twelve tabs. Examples: D-ING-7 "*Rejected:* … `Pending` and `ING6401` as node values, the round 2 rule. (revised in round 3)"; D-MEC-26 "*Why:* … the round 1 drafts claimed the formboard twice"; D-FLX-1 "*Rejected:* the round 1 seven-crate split"; MEC "It replaces `crucible:model`"; KLN "`crucible:product`, formerly `crucible:model`". ING's "Open questions" opens "This revision decides all nine round 2 questions" and then lists ten bullets of declined findings; MEC's question 2 and AGT's question 2 are titled "Findings declined…". The contract's lead is a version history.
**Fix:** One mechanical pass, then a rule. (1) Delete every finding id from text above "Open questions"; where the id stood in for a reason, write the reason ("a policy-clamped limit made two organizations cache different results for one key" stays, "(R3-12)" goes). (2) Delete every "(revised in round N)"; the Decisions log and `git log` keep revision history. (3) Delete "the round N rule", "formerly", "replaces" and similar history from decisions and names; a rejected alternative is described by what it is. (4) "Open questions" holds only unresolved questions; move every "Findings declined or applied in part" list to the Adversarial review tab under that tab's code. (5) "Contract change requests" holds only open requests or "None"; accepted ones are recorded in the contract's ruling log. (6) The contract's lead is one sentence: "Binding for every design agent and reviewer; where a tab disagrees with it, the contract wins." Add to `check.py` a rule that fails on `\bR\d{1,2}-\d{2}\b`, "revised in round" and "round \d" outside the Adversarial review and Decisions log tabs.

### R21-07 · Major · Targets: ANV, FLX, COV, KLN, MEC, AGT, MFG
**Section:** The lead of each tab (and the Overview's "Subsystems" paragraphs, which restate them)
**Problem:** Leads follow the "design in one breath" rule literally: they list mechanisms in terms the lead does not define, and none says what the engineer gains. ANV's lead uses "decisions", "rounds", "frozen tolerances", "fidelity" and "label-invariant" without definition; FLX's names "aggregated CutFEM on an immersed octree" before saying what Flux gives a user; COV's uses "model level" and "evidence level" undefined. Because the Overview copies the leads, the weakest prose in the spec appears twice.
**Evidence:** ANV: "Decisions use exact predicates on linear geometry and certified enclosures on curved geometry, in rounds against frozen tolerances, identically at every fidelity." FLX: "Solids use aggregated CutFEM on an immersed octree, slender walls and members use shells and beams, and contact uses fitted meshes." COV: "…whose models declare a model level, an evidence level and a `ValidityEnvelope` as data."
**Fix:** Adopt the three-sentence lead of R21-03 and replace these leads:
- ANV: "Anvil is Crucible's geometry kernel: one `Body` type holds exact B-rep, implicit, mesh and subdivision geometry, and mixing them never silently approximates. Where other kernels settle near-coincidences with a global tolerance and a best guess, Anvil proves each topological decision or reports that it cannot, so a model builds the same way on every machine. Every operation is versioned and returns the history that keeps face and edge names stable when dimensions change."
- FLX: "Flux is Crucible's simulation engine: physics is written as weak forms in Ingot, or called as std studies such as `static_stress`, and every result is a Field with a stated bound on its error. Where incumbents report a number and leave convergence to the analyst, Flux names each error source, its norm and how sure the bound is, so a check decides only when the bound supports it. It chooses the discretization per region (shells for thin walls, beams for struts, an immersed grid for solids), so nobody meshes by hand."
- COV: "COV decides which physics Crucible can honestly claim. Every physics model is a package that states where it is valid and how well it has been tested, every material is a versioned record with its statistical basis and licence, and every gap is a named record that points to a tool that covers it. A result outside its model's validated range is flagged or refused, never quietly trusted."
- KLN: "Kiln, `repo` and PLM keep a design's history and compute its results. Kiln re-runs only what an edit affects and shares results across designs by content; `repo` records every edit as an immutable Change on cheap branches and merges only when geometry, checks and connectivity still agree; PLM turns merged Changes into Items, revisions, BOMs and signed releases. The same signed store runs on a laptop, a team server, the cloud or an air-gapped site."
- MEC: "`std::mech` is everything a mechanical designer does in Crucible, from sketch to drawing, written as ordinary Ingot features anyone can read, fork or replace. Where incumbents add sheet metal, weldments and composites as separate workbenches, every domain here shares one constraint solver, one way of naming faces and one semantic tolerancing model, so the drawing, the stack-up and the inspection plan read the same tolerances. Every feature fails with a typed reason and a fix that compiles."
- AGT: "Agents in Crucible are colleagues on branches: they call the same `api` a person's clicks call, and hand their work over as Proposals that a human reviews like a pull request. An independent verifier attacks every Proposal before review. Safety lives in the server, not in the model: untrusted text never carries authority, and nothing leaves Crucible, from a release to a program sent to a machine, until a named human approves its exact plan."
- MFG: keep its third sentence, and replace "through one typed plan: Ingot intent, Wasm planning, Anvil geometry and Flux physics" with "as one typed plan that regenerates when the design changes".

### R21-09 · Major · Targets: ING, MEC, KLN, ANV, AGT
**Section:** D-ING-26 and D-MEC-33; D-ING-11 and D-KLN-6; D-ING-22 and D-MEC-10; D-ANV-18, D-KLN-2 and D-KLN-4; D-AGT-31
**Problem:** Several facts are decided twice, in two tabs, with two rationales, against "Say it once". A reader meets the same rule again and has to check whether the two copies differ, and the copies already drift in detail.
**Evidence:** Sketch seeds: D-ING-26 ("Sketch seeds are inline literals rounded to a quantum") and D-MEC-33 ("Seeds stay inline, rounded to a quantum q"), each with its own rejected list. Failures and Aborts: D-ING-11 and D-KLN-6 both justify themselves with the out-of-memory fallback example. Instance existence: D-ING-22 and D-MEC-10 both decide that existence depends only on `#[configuration]` parameters. Version freezing: contract 4, D-ANV-18, D-KLN-2 and D-KLN-4, with near-identical paragraphs in ANV ("Per-merge CI reproduces golden hashes of `Current` and `Deprecated` versions pinned by a golden product or registry package … weekly in shards") and KLN ("Per-merge CI reproduces golden hashes only for `Current` and `Deprecated` versions that a golden product or registry package pins … weekly in shards"). D-AGT-31 opens "Physical-effect Acts follow contract section 7.6", restating a contract rule as a decision.
**Fix:** Keep one decision per fact, in the owner's tab: seeds in MEC (D-MEC-33); Failure and Abort semantics in KLN (D-KLN-6), with ING keeping only the language rule that `try` cannot observe an Abort; existence in ING (D-ING-22); version freezing in ANV for operations, KLN for registration. In the other tab, replace the decision with one sentence and a link ("Sketch seeds are inline literals rounded to MEC's quantum; see MEC 'Determinism and seeds'"). Decision numbers stay reserved, so mark the removed ones in the Decisions log as "merged into D-MEC-33". D-AGT-31 keeps only what AGT adds (plan schemas and AGT-O-21).

### R21-10 · Major · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT
**Section:** Running prose and table cells in every tab
**Problem:** Cross-references use decision numbers as nouns: "MEC's Part-level `part.general_tolerance(spec)` record (D-MEC-35)", "the default distribution (D-MEC-28)", "standing releases (D-AGT-33)". A reader cannot tell what D-KLN-41 is without leaving the page, and a sentence carrying three such ids reads as a lookup table. Decision numbers are stable ids for logs and reviews, not prose.
**Evidence:** Decision ids before "Open questions", per tab: AGT 101, MFG 95, ECO 90, FLX 87, KLN 86, PLT 83, ELX 77, COV 76, MEC 75, ANV 58, UIX 58, ING 51, about 940 in all. Example from AGT: "`api` enforces KLN's one two-person list (D-KLN-41), which includes this tab's items"; from KLN's interface row: "`release_data` and standing releases (D-AGT-30, D-AGT-33)".
**Fix:** Refer to facts by name and link the owning section: "KLN's two-person list ([KLN, Change control](05-kiln-repo-plm.md#change-control-signatures-and-compliance))". Keep a decision id only where the decision itself is the subject ("D-MEC-33 is merged into …") and in the Decisions log. Add a `check.py` warning for more than one decision id in a sentence outside decision blocks.

### R21-11 · Major · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, CONTRACT
**Section:** "Interfaces with other subsystems" in every tab; contract section 11, item 5
**Problem:** The Interfaces sections use at least six formats, and every interface is written four times (A provides it to B, A requires it from B, and both again from B's side), which is why the plan needs `extract.py` to reconcile rows. A reader comparing two tabs finds the same edge described in different words and cannot tell which wording is binding.
**Evidence:** Formats: ING, FLX, COV, AGT and UIX use "provides" (To · Provides · Types) plus "requires" (From · Requirement); ANV uses "Anvil provides" with columns To · What · Types; MEC one table Subsystem · MEC consumes · MEC provides; ECO Tab · ECO requires · ECO provides; MFG "What MFG consumes" with From · Canonical name or type · Used for; PLT "Provided by PLT" and "Consumed by PLT". The repository's working notes list "make each row of 'Interfaces with other subsystems' match the other tab's row" as a standing consistency task.
**Fix:** Each tab writes only what it provides, in one format: `| To | What | Types | Phase |`. `extract.py` generates the "requires" view per tab and one interface matrix (twelve by twelve, linking cells to rows) for the Overview. Change contract 11 item 5 to: "`## Interfaces with other subsystems`: one table of what this tab provides (To · What · Types · Phase); what it requires is generated from the other tabs." A requirement nobody provides then shows up as an empty cell instead of a mismatch hunt.

### R21-12 · Major · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, CONTRACT
**Section:** Inline citations and "Sources" in every tab
**Problem:** The tabs use four inline citation systems, so a reader re-learns how to follow a reference in each tab, and in two of them the markers crowd the prose. COV and AGT tag almost every sentence with `[Sn]`, ELX with `[n]`, ANV and MFG use readable keys, and ING, KLN, UIX and PLT name sources in prose with no marker at all.
**Evidence:** `[Sn]` markers: COV 384, AGT 239; bare numeric `[n]`: ELX 177; bracketed keys such as `[Parasolid convergent modeling]` and `[Gardeyn et al. 2025]` in ANV, MEC and MFG; none in ING, KLN, UIX and PLT. One AGT table row carries `[S2][S4][S8]`. ELX's Sources opens "[65] to [69] were opened in round 2".
**Fix:** One style in contract section 11: readable keys `[Author Year]` or `[Organization short title]`, defined in Sources as "key · title · URL · date opened", and at most one marker per sentence. Convert COV, AGT and ELX mechanically from their source lists; add markers in ING, KLN, UIX and PLT where a sentence states a sourced fact. Remove round history from Sources headers.

### R21-14 · Major · Targets: OVERVIEW, ING, ANV, FLX, COV, MEC, AGT, CONTRACT
**Section:** Overview "Program plan", "Phase 1 scope", "Roadmap"; tab-local terms throughout
**Problem:** Terms and abbreviations appear before any definition, and some are never defined in the tab that uses them. The Overview, the page meant for every reader, uses DWR, SSI, CutFEM, PMI, WIT, MCP and DAE without expanding them, and refers to "chains A and B" and "GP2's alloy, machine, bureau and build-preparation software" in the Roadmap table, sixty lines before "Critical path" defines the chains. The contract glossary covers platform concepts but not the technical vocabulary the tabs share.
**Evidence:** First Overview uses: "WIT package" (line 51), "compiled into a DAE" (77), "aggregated CutFEM" (145), "chains A and B searched" (282), "semantic PMI" (283), "Aggregated CutFEM with calibrated DWR" (333), "Certified SSI without sampling for GP1 and the prismatic ABC subset" (334); none is expanded. η99 is used in COV and MEC and defined only in FLX D-FLX-24; ρ appears in MEC's D-MEC-33 ("2¹⁰ρ") with no definition in MEC; "torsor", "Krawczyk test", "pass^4", "MRTR" and "Rule of Two" appear without a gloss at first use.
**Fix:** Add a generated "Glossary" at the end of the Overview, listing each term once with a one-line meaning and its owner, and require first-use expansion in every tab (contract 11). Entries to add:

| Term | Meaning | Owner |
| --- | --- | --- |
| SSI | Surface–surface intersection: computing the curves where two surfaces meet, the core of every Boolean | ANV |
| CutFEM (aggregated) | Finite elements on a background grid that the geometry cuts through, so no fitted mesh is needed; "aggregated" merges tiny cut cells with neighbours for stability | FLX |
| DWR | Dual-weighted residual: an error estimate for one goal quantity, such as a regional stress average, computed with an adjoint solve | FLX |
| η99 | A calibration class's 99th-percentile underestimate factor; every `Estimated` bound is reported already multiplied by it | FLX |
| ρ | A Body's resolution: the scale-relative length below which Anvil treats geometry as coincident | ANV |
| PMI | Product and manufacturing information: dimensions, tolerances and notes attached to the 3D model; "semantic" PMI is machine-readable | MEC |
| Torsor | The small rigid displacement (three rotations, three translations) by which a toleranced feature may deviate from nominal | MEC |
| Krawczyk test | An interval-arithmetic test that proves a system of equations has exactly one solution in a box | ANV, MEC |
| DAE | Differential-algebraic equations, the form a Network compiles to | FLX |
| WIT | WebAssembly Interface Types, the interface language of the Wasm Component Model | ECO |
| MCP | Model Context Protocol, the standard through which AI hosts call tools | AGT |
| IIR; kernel IR | The Ingot IR, Ingot's dataflow form after lowering; FLX's intermediate form for every result-affecting numeric kernel | ING; FLX |
| Golden product (GP1 to GP16) | A reference product whose checks, and whose made and measured articles, close a phase | Contract 13.1 |
| Chains A to D | The four sequences of work on phase 1's critical path: geometry, physics, interface, release | Contract 13.2 |
| ABC subset | The licence-filtered part of the ABC dataset of public Onshape models used for benchmarks | Contract 13.3, ECO |
| R0 to R4 | Risk classes of a Proposal, from no semantic change to changes that feed an Act | AGT |
| pass^k | The share of tasks an agent completes in every one of k independent trials | AGT |
| UFL | Unified Form Language, FEniCS's notation for weak forms, whose semantics Flux's forms follow | FLX |

In the Overview, move the Roadmap's phase 0 gate details on chains and GP2 behind a link to "Critical path", or define the chains before the table.

### R21-18 · Major · Targets: MEC
**Section:** "Library structure and shared conventions"
**Problem:** MEC opens with a legal decision on standards tables (D-MEC-31), the hash encoding of Part and Assembly identity down to quaternion sign conventions (D-MEC-32), the definition-tolerance default, a WIT package, and a dataset-licensing decision (D-MEC-37), before the reader sees one feature. The tab's best teaching example, `housing`, which shows sketch, extrude, pocket, tapped holes and fillets in ten lines, waits in the third section.
**Evidence:** The first decision a reader meets is D-MEC-31 ("std computes standard values from the formulas the standards define … Counsel reviews this split before phase 1"); the next section is "Identity of Parts and Assemblies" ("A placement is a unit quaternion with non-negative scalar part plus a translation, in canonical f64 bits"); "Third-party data and benchmarks" closes the section.
**Fix:** Reorder to: (1) a short opening with the `housing` example and the `lid` roles example, explaining roles, queries and typed failures (today's "Roles, queries and fixes" and D-MEC-1, D-MEC-2); (2) Sketching; (3) Part features; and onward. Move "Packages" and D-MEC-31 into a "Standards content" subsection beside "Holes and threads", where the thread and clearance tables first matter; move "Identity of Parts and Assemblies" and "WIT interface" to the Reference section; move D-MEC-37 to the preamble of "Oracles", where datasets are used.

### R21-21 · Minor · Targets: CONTRACT, AGT, COV, KLN, MEC, MFG
**Section:** Contract section 2; uses of "class"
**Problem:** "Class" carries eleven meanings: platform, calibration, risk, Act, machine, execution (EN 1090), device, response-quantity, precision, retention and priority class. Several meet in one sentence ("a non-provisional `Pass` in a platform class the gate accepts … calibration class … risk class"), and "the canonical class" appears bare.
**Evidence:** Occurrences: risk class 15, calibration class 14, platform class 13, Act class 12, machine class 10, execution class 8, device class 8, response-quantity class 7, precision class 6, retention class 3, priority class 3.
**Fix:** Keep platform, calibration, risk, machine and execution class (core terms or industry usage). Rename Act class to **Act kind**, precision class to **precision tier**, retention class to **retention tier**, and say "response quantity" (the V&V term) instead of "response-quantity class" where the set is meant. In each tab, write "the canonical platform class" at first use.

### R21-22 · Minor · Targets: CONTRACT, ING, MEC, AGT
**Section:** Contract sections 9 and 11, "Platform notes"
**Problem:** Every tab must have a "Platform notes" section, so tabs with no platform-specific behaviour fill it with restatements, which a reader skims and learns to ignore.
**Evidence:** ING: "Accessibility | Diagnostics are plain text with spans"; "Air-gapped installs | Compiler and interpreter ship in every build; no network is needed"; "Every target | One canonical-class interpreter, so a divergence is a platform defect".
**Fix:** In contract 9 and 11, allow "Platform notes: none beyond PLT's rules" as a complete section, and require a row only for behaviour that differs by target (capacity, a missing capability in a tier, a browser limit).

### R21-24 · Minor · Targets: ING, AGT, FLX, MEC, ANV, KLN
**Section:** "Oracles"
**Problem:** Oracle ids follow different schemes: flat numbers (ING-O-1 to ING-O-38, AGT-O-1 to AGT-O-24) and area-prefixed ids (MEC-O-PF-1, ANV-O-VER-1, KLN-O-FPRINT-1, FLX-O-OPT-1). A flat id says nothing about what it verifies, so a capability row citing "ING-O-8" or "AGT-O-17" sends the reader to the Oracles table every time.
**Evidence:** ING capability rows cite "ING-O-1, ING-O-13, ING-O-27"; MEC rows cite "MEC-O-TL-6", whose area (tolerancing) is readable in place.
**Fix:** Adopt `<TAB>-O-<AREA>-<n>` in ING and AGT now, while `oracles/` holds no executable oracles and renaming costs one search-and-replace across tabs.

### R21-25 · Minor · Targets: MEC, KLN, ELX
**Section:** MEC "Interference and clearance" and Interfaces; KLN "Scope and the operation contract"
**Problem:** Some references point at an item number in another place's list, so the reader must open that list to learn what is meant, and the reference breaks if the list is reordered.
**Evidence:** MEC: "KLN's merge condition 4 reuses these classes"; MEC Interfaces: "merge conditions 4 and 5"; KLN's `OpCx` comment: "keyed by rule 2 under Keys"; KLN: "`OpKey(ObjectId)` // contract 7.2, items 1 to 6".
**Fix:** Name the rule: "KLN's no-new-interference merge condition"; "the interference and connectivity merge conditions"; "keyed as Kiln's random-stream rule says"; "the six `OpKey` inputs of contract 7.2".

### R21-26 · Minor · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, CONTRACT
**Section:** Capability tables at the end of each design section
**Problem:** Capability tables are the build contract, but in reading order they arrive as a dense block after every section, and many cells add nothing: "Failure: —" and "Not expressible" stand where the reader expects a typed failure. The published doc gives them the same weight as explanation.
**Evidence:** ING "Purity | … | Not expressible"; MEC "Typed failures and fixes | `FeatureError { kind, why, fix, at }` | —"; AGT "Priority classes | … | — ".
**Fix:** Replace "—" with "None: cannot fail" or the actual failure, and "Not expressible" with "None: the language cannot express a violation". In the published doc, render capability tables as a visually distinct, collapsible "Build contract" block under each section, so a reader can follow the prose without the tables breaking it.

### R21-32 · Minor · Targets: MEC
**Section:** "Identity of Parts and Assemblies"; D-MEC-33; "Open questions"
**Problem:** One passage reads as correspondence ("MEC confirms the default"), and two different thresholds in units of ρ, never defined in MEC, are discussed by finding id, so a reader cannot tell which number governs what.
**Evidence:** "For KLN's definition tolerance, MEC confirms the default: the smaller of 0.1 µm and 1% of the Item's tightest tolerance, … never below 10ρ." D-MEC-33: the seed quantum is "the larger of 2¹⁰ρ for the sketch and 10⁻⁶ of its diagonal". Open questions: "R9-53: its 2¹⁰ρ floor is declined for R10-39's 10ρ".
**Fix:** "KLN's definition tolerance, the geometry change below which an Item keeps its revision, is the smaller of 0.1 µm and 1% of the Item's tightest tolerance (or general tolerance), and never below 10ρ, where ρ is the Body's resolution (ANV)." In D-MEC-33 add "(ρ as above)". Delete the Open questions bullet (R21-02).

## Claims the reviewers verified

Drop the `[unverified]` marker on these and cite the URL in Sources.

- Plasticity integrates Parasolid | https://plasticity.xyz/product (R14)
- ASME Y14.5-2018 (R2024) is on stabilized maintenance | https://www.asme.org/codes-standards/find-codes-standards/y14-5-dimensioning-tolerancing (R14)
- ASME Y14.41-2026 is listed and on stabilized maintenance | https://www.asme.org/codes-standards/find-codes-standards/y14-41-digital-product-definition-data-practices (R14)
- the CAx-IF PMI practice for AP242 is still version 4.1 of 20 June 2024 | https://www.mbx-if.org/home/cax/recpractices/ (R14)

## Unverified claims in your tab

Verify each with WebFetch on a primary source and drop the marker, correct it, or cut the claim if nothing supports it. Line numbers are at tag `round-3`.

None.

## Your open questions

Close each: decide it (the reviewers propose answers above), move it to a contract change request, or keep it with the reason it cannot be decided yet.

Round 3 closed the earlier questions in D-MEC-20, D-MEC-30, D-MEC-31, D-MEC-33, D-MEC-34, D-MEC-36 and D-MEC-37.

1. **Standards data licences.** Which distributor terms let Crucible package tabulated values such as ISO 261 plans and ISO 273 clearance holes? Kept open for counsel's review before phase 1 (D-MEC-31); until then an organization supplies its own table packages.
2. **Findings declined or applied in part.**
    - R9-53: its 2¹⁰ρ floor is declined for R10-39's 10ρ, because 2¹⁰ρ would ignore changes of up to 0.49 mm on a 300 m hull.
    - R8-24: the seed quantum is scale-relative with no 1 µm floor, so MEMS sketches keep sub-micrometre seeds.
    - R8-44: machining implicit regions through mesh-capable CAM is declined; STEP hand-offs need B-rep (R10-37).
    - R10-36: dialect conversion ships in phase 2 as exact translation plus typed holes, which are the non-equivalence report; nothing is translated approximately.
    - R10-41: the DIN 6935 correction factor could not be verified, so the R/t-dependent default K comes from MFG's press-brake data.
    - Round 2 records: R1-10, R1-36, R2-09, R2-36, R6-11, R3-30, R3-31 and R4-29 stay applied in MEC's part only. R2-19, R4-14, R4-16 and R1-37 are now fully applied.

## Known items

- Read `docs/revision/digest.md`: adopt the permissive libraries that serve your tab, name copyleft tools only as oracles, and use the clean-room insight protocol of contract 7.7 for incumbent behaviour.
- Add one sentence under each drawn diagram that tells the reader how to read it (`diagrams/06-mechanical-constraint-solve-pipeline.jsx`, `diagrams/06-mechanical-data-flow.jsx`).
