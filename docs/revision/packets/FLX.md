# FLX round 4 packet

Your tab is `docs/spec/03-flux.md` at v3 (tag `round-3`). Round 4 fixes, in one pass: the 82 third-review findings that target it (7 Critical, 52 Major, 23 Minor), its 0 `[unverified]` claims, its open questions and the known items below. Contract v7 is binding; its section 18 lists the rulings on this review, and many findings below are already settled there.

## Third-review findings

### R13-01 · Critical · Targets: CONTRACT, ING, FLX
**Section:** Contract 6 (canonical example and its paragraph); ING "Canonical example" (ING-O-31); FLX "Regularized goals and singular points" (D-FLX-39)
**Problem:** The round 3 fix for R7-02 opened a new hole: the canonical check leaves out the region it most needs to judge. `clamp` is the base's `start_cap`, the whole bottom face at z = 0 (ANV's worked example puts the end cap at z = 4 mm). `away_from([clamp, …], 2 * thickness)` therefore removes everything below z = 8 mm, which takes in the rib root and its 2 mm fillet (z = 4 to 6 mm), where the rib's bending stress and the fillet concentration peak. FLX's own rule would exclude only the flagged *edges* (the clamp perimeter) by max(2ρ, t) = 4 mm, and that keeps the fillet, which lies about 5.7 mm from the perimeter edge. The load's direction is also never stated, so it is unclear what is being checked.
**Evidence:** Take a lateral 1.2 kN on the 20 mm rib (60 mm wide, 4 mm thick). The section modulus is 60·4²/6 = 160 mm³. The root moment of 1.2 kN × 20 mm gives 150 MPa nominal, about 210 MPa with a fillet Kt of about 1.4. In the band that remains (z = 8 to 16 mm) the stress is at most 1.2 kN × 16 mm / 160 mm³ = 120 MPa. The limit is 0.6 × 241 MPa = 145 MPa at the 6061-T6 specification yield that D-COV-13's default basis selects. So the check returns `Pass` on a bracket whose root fails, and ING-O-31 requires exactly this outcome ("its check decides at `SignOff`").
**Fix:** Write the check as `study.von_mises.max(over: p.regular())`. `regular()` is the Body minus each flagged set's default neighbourhood, taken from `flux::singular_sets` for this study, and never a whole face. State the load as a vector, for example `force: 1.2kN * dir(-x)`. Add a rule to D-FLX-39 and contract 7.1: when the maximizer of a regularized maximum lies on the boundary of an excluded neighbourhood, the result is `Undecided { reason: MaximumAtExclusion }` with the fix "model the support". Extend ING-O-31: the check region contains the rib-root fillet, and with a lateral load the canonical bracket `Fail`s at 4 mm and passes at 6 mm.

### R13-03 · Major · Targets: FLX, CONTRACT, ING
**Section:** FLX "Budgets and guarantees" (the algebraic and bounded-linear-goal rows; the paragraph that says guaranteed goal bounds rest on |J(u) − J(u_h)| ≤ ‖e‖·‖z − z_h‖); contract 5 `ErrorBudget`
**Problem:** For a goal check, the algebraic row's norm is "As discretization", which means the goal norm. But both listed estimators (Papež's multilevel bound and ‖r‖_{M⁻¹}/√σ) give energy-norm values, and contract 5 forbids combining norms. As written, every regularized-peak and eigenvalue budget is therefore `NotQuantified`, and ING turns that into a conditional `Pass` that no allowance will cover. Second, the product bound holds only under Galerkin orthogonality. With an iterative solve, J(u) − J(u_h) = a(u − u_h, z − z_h) + r(z_h), and r(z_h) ≠ 0, so the "Guaranteed" linear-goal bound is false without that term.
**Evidence:** The FLX table row reads "Algebraic | Multilevel bound … or a certified spectral bound after factorization; else equilibrated residual | As discretization | `Guaranteed`; else `Estimated`". The guarantee is stated as resting on "|J(u) − J(u_h)| ≤ ‖u − u_h‖_E · ‖z − z_h‖_E".
**Fix:** Define the goal-norm algebraic part as |r(z_h)| ≤ η_alg,E · ‖z_h‖_A (Cauchy–Schwarz on the discrete residual). It is `Guaranteed` when η_alg,E is, and the adjoint solve already gives ‖z_h‖_A. Restate the linear-goal bound as |J(u) − J(u_h) − r(z_h)| ≤ η_E(u_h)·η_E(z_h), and add r(z_h) to the algebraic part. Give the floating-point row the same goal-norm rule. Extend FLX-O-ERR-2 with deliberately loose solver tolerances.

### R13-04 · Major · Targets: CONTRACT, COV, FLX, MFG, ELX
**Section:** Contract 13.4 (prerequisite rule, "the spec check enforces this across tabs"); COV coverage matrix rows; FLX "Eigenvalue problems", "Krylov methods and preconditioners"
**Problem:** Contract 13.4 says nothing is phased before its prerequisites and that the spec check enforces this. The checker has no such rule, and rows outside 13.4 break it: (a) COV rotordynamics is phase 2 (Campbell diagrams, rotating-frame FEM), but the gyroscopic and damped eigenproblems arrive in FLX phase 3 ("Damping and flutter linearizations follow in phase 3"). (b) COV linear acoustics FEM with PML is phase 3, but FLX's indefinite Helmholtz solvers (complex LDLᵀ, shifted-Laplacian multigrid) are phase 4. (c) COV's signal and power integrity row is phase 3 with full-wave extraction, but FLX full-wave FEM is phase 4 and ELX's own post-layout extraction is phase 4. (d) COV's welding row puts the phase 4 transient model "with phase transformation", while JMAK and Koistinen–Marburger arrive in phase 6 (heat treatment, ICME). (e) R13-07: allowables in phase 3 against phase 1 strut basis values.
**Evidence:** `docs/tools/check.py` only checks that each capability row has a phase (line 298, "has no phase"); it never compares phases across tabs or against 13.4. FLX's linear-algebra table lists "Indefinite Maxwell and Helmholtz | Complex LDLᵀ; optimized Schwarz; shifted-Laplacian multigrid | 4".
**Fix:** Add a "Requires" field to every capability row that names another tab's capability, and have `check.py` compare phases. Contract 13.4 can stay a table without a Needs column, because the field lives in the tabs. Add 13.4 rows: structural frequency response and damped or gyroscopic eigenproblems at phase 2 (owner FLX; also COV and MEC), and Helmholtz FEM solvers at phase 3 (owner FLX; also COV and ELX). Drop "with phase transformation" from COV's phase 4 weld row, or move JMAK and Koistinen–Marburger to phase 4. Make COV's signal and power integrity row "3 quasi-static, 4 full-wave".

### R13-05 · Major · Targets: COV, FLX, MEC, MFG
**Section:** COV "Dynamics and stability" (D-COV-30); FLX "Calibrated estimates" (`lattice.buckling`); MEC "Design checks" table
**Problem:** Almost every GP2 strut lands in D-COV-30's `Refuse` zone, so the phase 1 `lattice.buckling` class decides almost nothing. The escalation rungs (Johnson, tangent modulus, Perry–Robertson) have no FLX capability, calibration class or MEC check family in phase 1. An LPBF strut of about 1 mm with L/d ≈ 4 has slenderness 4L/d ≈ 16, so σ_cr,Euler = π²E/λ² ≈ 2,700 MPa for AlSi10Mg (E ≈ 70 GPa). That is far above any proportional limit, so the ratio is about 10 or more against D-COV-30's `Refuse` threshold of 1. For such stocky struts, compressive yield and plastic collapse govern, not buckling.
**Evidence:** D-COV-30: "Calibrated while the inelasticity ratio … stays below 0.5, Extrapolated to 1 and `Refuse` beyond." MEC's table names only `lattice.buckling` and `elasticity.eigen` for buckling.
**Fix:** In phase 1, decide strut compression with a strut-strength check: the localized axial stress against the as-built compressive strength, reduced by a Johnson–Perry–Robertson factor computed from the measured waviness. It reads `lattice.strut_stress`, so it needs no new class. Run eigen-buckling (`lattice.buckling`) only on members with ratio below 1, where it governs global lattice instability. Add the strength check to MEC's table and FLX's beam-lattice row. Have MFG's coupons include compression tests of single struts at the GP2 diameters.

### R13-06 · Major · Targets: COV, ING, FLX
**Section:** COV "Materials system", "Data model" (D-COV-13); FLX "Budgets and guarantees" (property reads)
**Problem:** D-COV-13 calls the basis enclosure a `Guaranteed` input part. A B-basis value is a statistical tolerance bound: 90% content at 95% confidence, so by construction about 10% of the population lies below it. Contract 5 reserves `Guaranteed` for proofs, and the union bound then misstates every check's confidence. The label is right only when the check's limit is defined by the basis value (a design value), not when the property drives the solve (modulus, conductivity, CTE).
**Evidence:** D-COV-13: "A property read returns `Approx<Q>` whose `input and tolerance` part is a `Guaranteed` basis enclosure". COV quotes 14 CFR 25.613: design values cover "99% of the population with 95% confidence … and 90% for redundant structure".
**Fix:** Split the two uses. (a) A limit written against a basis (`0.6 * yield_strength`) reads the basis value as an exact definitional number, with no budget part. (b) A property that enters a solve carries an input part of kind `Estimated` with α equal to the basis's non-content (0.10 for B, 0.01 for A), and the union bound includes it. Update FLX-O-ERR-11 and COV-O-MAT-6.

### R13-08 · Major · Targets: FLX, COV, MEC, CONTRACT
**Section:** FLX "Calibrated estimates" (D-FLX-40), FLX-O-ERR-3 and FLX-O-ERR-5; contract 13.2 build program, item 3
**Problem:** The η99 calibration that every phase 1 `SignOff` check relies on has no independent reference. References are "solves two degrees higher" in the same aggregated CutFEM code. They share its cut quadrature, Nitsche penalty, aggregation and geometry handling, so a bias common to the family never shows. They "count only when their own error is below 10% of the bound", but that error can only be measured by the estimator family being calibrated. That is circular. Fitted FEM arrives only in phase 2.
**Evidence:** D-FLX-40: "References are solves two degrees higher, or full-resolution solids for lattices, and count only when their own error is below 10% of the bound." Contract 13.2: corpora "must agree with an independent source (… MFEM or libCEED …)".
**Fix:** Take phase 1 references from an independent code on fitted, curved high-order meshes, used as an oracle only: MFEM (BSD) or deal.II (LGPL, allowed as an oracle). Accept a reference only when a p-sequence (p, p + 1, p + 2) in that code shows exponential convergence and its Richardson spread is below 10% of the bound. Record each reference's code and mesh hash in the corpus. Keep same-code p + 2 solves only as a cross-check.

### R13-10 · Major · Targets: CONTRACT, FLX, COV, ELX
**Section:** Contract 5 `ErrorBound` kinds; contract 7.1 ("Every `Estimated` bound is reported already multiplied by its calibrated factor … outside it reports `Indicator`"); FLX budget table; D-FLX-35; ELX "Analyses and results"; D-COV-17
**Problem:** Contract 7.1 and D-COV-17 make every `Estimated` bound a calibrated class member, and anything outside a class is `Indicator`. Yet several `Estimated` bounds have no class. These are FLX's cut-cell energy bounds ("`Estimated` (open question 1)"), D-FLX-35's worst-case remainder, ELX's "Algebraic error is `Estimated` from residuals", COV's V&V 20 model-form part, and confidence intervals from sampling. Read literally, all of them are `Indicator` and can never decide. Read loosely, some uncalibrated estimates decide `SignOff`. The mechanism mixes two different guarantees: empirical calibration against a corpus, and a statistical interval with a stated α.
**Evidence:** The quoted contract sentence, against "Algebraic error is `Estimated` from residuals" (ELX) and "The result is `Estimated`" (D-FLX-35), neither naming a class.
**Fix:** Make the calibration field one enum in contract 5: `Class { id, α }` (η99 tables) or `Statistical { method, α }` (confidence intervals, V&V 20, conformal, probabilistic Lanczos bounds). Then state: an `Estimated` bound without either is `Indicator`. List every current `Estimated` source in FLX's table with its variant, and have ELX name the class or method for circuit algebraic parts.

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

### R13-14 · Major · Targets: FLX, COV, MFG
**Section:** FLX "Verification, validity and agreement" (D-FLX-34), "Per-region models" (D-FLX-45); MFG "Molds and injection molding" (D-MFG-15)
**Problem:** D-FLX-34 refines the production mesh three times by r ≥ 1.3. Roache's procedure goes the other way: it coarsens from the production grid, so the cost of solution verification stays below that of the production solve. Refining upward makes `SignOff` impossible on large models. GP5's 3D fill already needs about 5 × 10⁷ cells (MFG's own estimate), and three upward levels of a transient 3D solve multiply that cost about 2.9 times per level, to roughly 25 times. The octree also refines only by r = 2, so r = 1.3 needs new, non-nested octrees, which the text never states. And D-MFG-15 promises "a warpage estimator" that no FLX row defines for the fill–pack–cool–warp chain.
**Evidence:** D-FLX-34: "It refines the final mesh uniformly three times by r ≥ 1.3". NASA Glenn's GCI tutorial (opened) builds the coarser grids by "removing every other grid line", recommends r ≥ 1.1, and uses Fs = 1.25 for three grids.
**Fix:** Change D-FLX-34 so the production mesh is the finest of three grids, with the two coarser ones built by r = 2 octree coarsening, or by a re-rooted octree when r is not an integer. Use p-coarsening for high-order solves. Replace "a warpage estimator" in D-MFG-15 with "calibrated GCI on warpage at measured points (FLX-O-ERR-8)", and cost it in the plan.

### R13-15 · Major · Targets: FLX, PLT, CONTRACT
**Section:** FLX "Interactive latency" (stage budgets), "Regularized goals and singular points"; contract 13.3 "Interactive simulation update"
**Problem:** The 1 s budget gives the estimate 100 ms, but `estimate_goal` "solves the adjoint one degree higher" and reports "the largest calibrated estimate among near-maximal locations". That means one p = 3 adjoint per checked goal and candidate location, each larger than the 350 ms p = 2 primal solve. A part with several regularized-peak checks therefore misses the row by a multiple, and the stage budget falls back to `Proxy` on every edit.
**Evidence:** The FLX text gives these stage budgets: "setup 100 ms, solve 350 ms, estimate 100 ms". The adjoint wording is quoted above.
**Fix:** At `Interactive`, solve all goal adjoints at the primal degree p in one block-Krylov solve that shares the primal's preconditioner. Get the weights by patchwise higher-order reconstruction (Becker and Rannacher's interpolation weights), as its own calibration class `elasticity.peak.interactive`. Keep p + 1 adjoints for `SignOff`. State the budget per goal: 100 ms for the first goal and 30 ms for each further one (targets). Make FLX-O-MESH-3 measure a part with five checks.

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

### R13-17 · Major · Targets: FLX, COV, CONTRACT
**Section:** FLX "Explicit dynamics" (D-FLX-31), D-FLX-34; COV "Explicit dynamics, impact, crash"; contract 13.1 (GP5 drop response, GP9)
**Problem:** GP5's drop response and GP9's crash box are gate quantities, but explicit dynamics has no route to a decided check. It has no a posteriori estimator. GCI on contact-impact histories is rarely monotone, so it ends `NotAsymptotic` and leaves the result `Indicator`. And crash-box folding is a bifurcation sequence that principle 4 requires to declare branch selection or branch-invariant quantities. Neither tab names the quantities: raw peak accelerations depend on sampling rate and mesh and are not well-posed goals.
**Evidence:** FLX: methods without an estimator "report `Indicator` discretization parts unless `std::sim::solution_verification` runs", and "oscillatory convergence stay `Indicator`". COV's row states mass-scaling and hourglass limits but no checked functional.
**Fix:** Define the explicit-dynamics goals as regularized functionals:
- acceleration filtered by a declared channel filter (SAE J211 channel frequency classes [unverified]);
- energy absorbed;
- mean crush force over a displacement window;
- maximum of a time-averaged strain.

Fold buckling-sensitive cases into an ensemble over seeded geometric imperfections and use its statistics (principle 4) as the statistical part. Use coarsened GCI on these functionals (R13-14) as the discretization part, with one calibration class per family (drop, crash). State in contract 13.1 that the GP5 and GP9 gates compare these functionals.

### R13-18 · Major · Targets: FLX, COV, ELX
**Section:** COV "Aerospace" (low-speed aerodynamics and rotors, phase 4, benchmark "GP6 rotor thrust and torque"); FLX (no rotor or rotating-domain capability)
**Problem:** GP6's gate validates rotor thrust and torque, but no tab owns a rotor-aerodynamics method. COV names vortex particle methods and RANS or DDES. FLX lists no vortex-particle method, no rotating reference frame, and no sliding or overset mesh for flow; its sliding interface serves magnetics only. Blade-element momentum theory (the L1 rung) has no package owner either. A drone engineer would reach for a separate tool on day one.
**Evidence:** In FLX and ELX a search finds no "rotor", "vortex", "blade-element" or "rotating frame". The only sliding interface is FLX's: "Motion uses a sliding interface on a cylindrical air gap or mortar coupling, for ELX's loss maps".
**Fix:** Add three phase 4 rows to 13.4, all owned by FLX with COV and ELX also phasing them:
- blade-element momentum with tip losses as an Ingot package (L1);
- a vortex particle method on `fmm_apply` as a std Wasm component (D-COV-11's route), with regularized particles and a stated core size;
- rotating-domain flow by a moving reference frame and a sliding interface reusing the magnetics machinery, with an oracle against published propeller data.

### R13-19 · Major · Targets: FLX, CONTRACT
**Section:** FLX "Regularized goals and singular points" (D-FLX-23)
**Problem:** The default ρ is "min(0.1 × the smallest curvature or fillet radius in R, 0.1 × local wall thickness)". Machined parts have sharp convex edges (ISO 13715 breaks of a few tenths of a millimetre, or none), and their curvature radius is zero. So ρ → 0, the regularized maximum becomes a point value, its DWR estimate is unbounded below h, and GP1's checks either never decide or cost a refinement to the edge.
**Evidence:** The D-FLX-23 formula quoted above. Contract 7.1 treats convex edges with compatible conditions as non-singular, so they are never excluded.
**Fix:** Take curvature only over smooth faces and fillets. For sharp convex edges with compatible conditions, use ρ = 0.1 × local wall thickness. Floor ρ at the larger of the drawing's edge-break size and the Material's microstructural length (grain or strut scale). Show the chosen ρ and its source in the report. Add a sharp-edged bracket to FLX-O-ERR-3.

### R13-20 · Major · Targets: FLX, COV
**Section:** FLX D-FLX-23 ("or the Material's critical distance for fatigue and fracture"); COV "Statistical basis" paragraph (critical distance)
**Problem:** The theory of critical distances calibrates its length L to a specific evaluation: the point method at L/2 or the line method over 2L [unverified; Taylor 2008, doi 10.1016/j.engfracmech.2007.04.007, record opened without abstract]. A Gaussian volume average of radius L is a different operator. Read with a Material's published L, it gives a lower stress than the point method, so fatigue predictions are unconservative by an amount that depends on the stress gradient.
**Evidence:** D-FLX-23 uses "a Gaussian local average of radius ρ" with ρ equal to "the Material's critical distance for fatigue and fracture".
**Fix:** Add `f.tcd(method: point | line | area | volume, L)` as a regularized goal. It evaluates the method's own operator along the inward normal from the hot spot, and its estimate comes from the same DWR machinery (it is a linear functional of the stress). Record in each Material which method calibrated its L, and refuse a mismatch with a typed error.

### R13-21 · Major · Targets: FLX, COV
**Section:** FLX "Per-region models" (D-FLX-26)
**Problem:** The reduction-error estimate re-solves 3D patches "with boundary data from the reduced model", so it captures only local 3D effects at each goal. In statically indeterminate frames and shell assemblies (GP4, GP8), joint flexibility and transverse shear left out of the reduced model redistribute forces globally. The patch boundary data carry that error unchecked. The state of the art is goal-oriented modelling-error estimation, which weights the 3D residual of the reconstructed reduced solution by the adjoint over the whole domain [unverified; Oden and Prudhomme, "Estimation of modeling error in computational mechanics", 2002].
**Evidence:** D-FLX-26: "Flux re-solves a 3D patch extending max(3t, 2√(R·t)) beyond each goal region … with boundary data from the reduced model."
**Fix:** Add a global term to the reduction part: the 3D residual of the reconstructed field (shell and beam kinematics expanded through the thickness), weighted by the reduced adjoint at every junction and at regions with t/L_local above 0.1. Keep the patch re-solve for local stress. Add an indeterminate portal frame with semi-rigid joints to FLX-O-PLAN-4.

### R13-22 · Major · Targets: FLX, MFG, COV
**Section:** FLX "Shells, beams and lattices" (D-FLX-44); MFG as-built strut calibration; COV lattice row
**Problem:** Joint-zone length and stiffness are fitted "against full-resolution unit cells", meaning nominal CAD cells. In laser powder bed fusion, nodes accumulate material and adhered powder, and down-skin struts are oversized, so as-built node stiffness and node stress concentration differ systematically from the nominal geometry. MFG's calibration supplies strut diameter and waviness but not node geometry. Yet GP2's localized strut stress, where cracks start, sits at the nodes.
**Evidence:** D-FLX-44: "Joint-zone length and stiffness are fitted per cell topology against full-resolution unit cells over a relative-density range". MFG lists "diameter and scatter, waviness … and strut-specimen data".
**Fix:** Add CT scans of as-built unit cells from the bureau's phase 1 coupons to MFG's calibration, and fit the node corrections on the CT geometry, with full-resolution immersed solves on the voxel Bodies (finite cell). Fix the oracle split so CT cells from one build plate are held out.

### R13-23 · Minor · Targets: CONTRACT, FLX
**Section:** Contract 5 `ErrorBound` ("a guaranteed lower bound for scalar diffusion on fitted simplices, for example"); FLX "Eigenvalue problems"
**Problem:** Carstensen and Gedicke's guaranteed lower bounds need the nonconforming Crouzeix–Raviart element and apply to the Laplacian. FLX promises them "in phase 2, with fitted tetrahedra" without naming the element, and no check in any tab decides on a scalar-diffusion eigenvalue (frequencies and buckling factors are elasticity eigenvalues). This is a mechanism with no consumer.
**Evidence:** The Crossref record for Carstensen and Gedicke, Math. Comp. 83 (2014), doi 10.1090/s0025-5718-2014-02833-0 (opened): its abstract places the eigenfunction approximation in "the nonconforming Crouzeix-Raviart finite element space".
**Fix:** Cut the example from contract 5 and the phase 2 promise from FLX, or restate it as "acoustic-cavity eigenvalue lower bounds by Crouzeix–Raviart elements (Carstensen–Gedicke), phase 3", and add a consumer (MEC's resonance-avoidance check for enclosures).

### R13-24 · Minor · Targets: FLX
**Section:** FLX "Nonlinear solvers and bifurcations" (D-FLX-25)
**Problem:** In phase 1, Newton "accepts only forms declared convex", but nothing checks the declaration, so a wrongly declared form silently picks a branch. The *Why* says "inertia exists only with a direct solver", yet phase 1 ships supernodal LDLᵀ up to about 2 million DOFs.
**Evidence:** The linear-algebra table: "Symmetric problems to about 2M DOFs … Supernodal LLᵀ and LDLᵀ … 1".
**Fix:** In phase 1, verify the convexity declaration at every converged step: by LDLᵀ inertia when the plan used a direct solver, otherwise by checking λ_min > 0 with one warm-started LOBPCG step. Fail with `ConvexityViolated { step }` and do not choose a branch.

### R13-25 · Minor · Targets: FLX, CONTRACT
**Section:** FLX "Calibrated estimates" (D-FLX-24, D-FLX-40); FLX-O-ERR-3 and FLX-O-ERR-5; contract 5 (`ErrorBound`, α)
**Problem:** The calibration rules state α in three ways:
- D-FLX-40 requires zero undershoots in 300 samples (a one-sided 95% bound below 1%).
- FLX-O-ERR-3 passes at "99% of held-out cases" (3 misses in 300).
- Contract 5 treats α = 0.01 as exact.

The verified claim is α ≤ 0.01 at 95% confidence, a nested statement that the union bound reports as a plain 99%.
**Evidence:** FLX-O-ERR-3: "Bound covers the true error in 99% of held-out cases per class". FLX-O-ERR-5: "zero undershoots".
**Fix:** Use one rule: zero undershoots in n ≥ 300, recorded as `α_U = 0.01 (95%)`. Have reports print "confidence ≥ 1 − Σα_U at 95%". Align FLX-O-ERR-3 with FLX-O-ERR-5.

### R13-26 · Minor · Targets: FLX
**Section:** FLX D-FLX-24 (class envelope features)
**Problem:** A class envelope covers "degree p, minimum cut fraction, ρ/h, distance to flagged sets, Poisson's ratio and material contrast". It leaves out the features that most drive estimator reliability on immersed meshes: the number of cells across the thinnest section (contract 7.1 requires four), the ratio of the smallest feature or fillet radius to h, and the type of load (pressure patch, body force, thermal strain). A thin wall with three cells across can fall inside the envelope.
**Evidence:** The D-FLX-24 feature list quoted above.
**Fix:** Add "cells across the thinnest section in the goal's region", "min feature radius / h" and "load type" to the envelope, and make FLX-O-ERR-5 report the coverage per feature bin.

### R13-27 · Minor · Targets: FLX, COV
**Section:** FLX "Budgets and guarantees" (property reads, last paragraph); COV D-COV-13
**Problem:** "A solve propagates them into its input part by the adjoint sensitivity's sign, or solves at both ends where the sign varies." Evaluating both ends bounds the response only if it is monotone in the property across the interval. Responses near a resonance, or where a buckling factor depends non-monotonically on a stiffness ratio, have interior extrema. FLX-O-ERR-11 tests sign changes but not non-monotone responses.
**Evidence:** The quoted sentence; FLX-O-ERR-11: "sign changes included".
**Fix:** Check monotonicity by the sign of the derivative at both ends plus a midpoint second-order test. Where it fails, subdivide the interval, or mark the input part `NotQuantified { NonMonotone }`. Add a resonance-crossing case to FLX-O-ERR-11.

### R13-28 · Minor · Targets: FLX
**Section:** FLX "Budgets and guarantees" (temporal row)
**Problem:** The temporal row gives its kind as "`Estimated`, calibrated, `Indicator`" for three estimators in one cell, so a reader cannot tell which estimator yields which kind. The cut-cell energy row says "`Estimated` (open question 1)" with no class, which by contract 7.1 is `Indicator`.
**Evidence:** The rows "Temporal | Adjoint-weighted residual; step halving with frozen breakpoints; summed local errors | Goal | `Estimated`, calibrated, `Indicator`" and "Discretization, hanging nodes or cut cells | … | `Estimated` (open question 1)".
**Fix:** Split the temporal row into three rows: adjoint-weighted residual (`Estimated`, class `temporal.awr`), step halving (`Estimated`, class `temporal.halving`) and summed local errors (`Indicator`). Mark cut-cell energy bounds `Indicator` until a class exists.

### R13-29 · Minor · Targets: COV, FLX
**Section:** COV "Durability" (lubrication and rolling-contact fatigue, phase 2)
**Problem:** COV schedules elastohydrodynamic Reynolds solves with pressure–viscosity and elastic deflection for phase 2. FLX has no EHL capability, and this tightly coupled problem (exponential viscosity, a cavitation complementarity condition, elastic deflection as a dense integral operator) does not converge with the generic Newton–Krylov FLX ships in phase 2.
**Evidence:** COV: "Elastohydrodynamic Reynolds equation with pressure–viscosity and elastic deflection … 2 · Nat". FLX has no EHL, Reynolds-equation or complementarity row.
**Fix:** Move L3 EHL to phase 3 on FLX's FFT or H-matrix deflection operators (`fft_solve`, `hmatrix_apply`, phase 3), with a semismooth Newton for the cavitation condition. Keep Hamrock–Dowson (L0) as the phase 2 rung. Add the capability row in FLX.

### R13-30 · Minor · Targets: ELX, FLX
**Section:** ELX "Power integrity"; FLX "Electromagnetics" (layered sheets)
**Problem:** ELX solves the PDN by "Flux's layered sheets solving the Helmholtz equation per plane pair", but FLX defines layered sheets as "thin-sheet conduction coupled through-plane by `dI` conductances", which is a diffusion form. A plane-pair cavity Helmholtz model with complex wave numbers and ports is a different form and needs the indefinite solvers of R13-04.
**Evidence:** ELX: "PDN impedance comes from Flux's layered sheets solving the Helmholtz equation per plane pair". FLX capability row: "Layered sheets | Thin-sheet conduction with through-plane `dI` | … | 3".
**Fix:** Add a "plane-pair cavity model" row to FLX in phase 4 (2D Helmholtz on sheet Bodies with port and via elements, complex LDLᵀ) and point ELX at it.

### R13-31 · Minor · Targets: FLX
**Section:** FLX D-FLX-41 ("Buckling solves K_G φ = μ K φ … λ₁ = 1/μ_max")
**Problem:** The text gives no sign convention. With the usual (K + λK_G)φ = 0 and compressive prestress, μ = −1/λ, so the critical factor comes from the most negative μ, not μ_max. Implementers who choose different conventions will compute different modes.
**Evidence:** The quoted sentence; K_G is called "indefinite" in the *Why* without its sign stated.
**Fix:** State it: "K_G is assembled so that compressive prestress gives a negative-semidefinite contribution; solve −K_G φ = μ K φ, and λ₁ = 1/μ_max over μ > 0."

### R13-34 · Minor · Targets: FLX, COV
**Section:** FLX and COV, every decision *Why* and *Rejected* clause; both tabs' "Open questions"
**Problem:** Rationales cite review findings by id ("(R7-15)", "(R1-07, R7-01)", "(R7-35)") dozens of times, so a reader must open another document to follow an argument that one clause could state. FLX's and COV's Open questions are mostly ledgers of "findings applied in part", not open questions. That record belongs in the Adversarial review tab, and readers of these tabs lose the real open items among them.
**Evidence:** FLX Open questions item 2 has nine bullets of finding ids; COV item 4 has nine.
**Fix:** Drop finding ids from *Why* clauses and say the reason in words; the Decisions log and the Adversarial review tab keep the mapping. Move the "applied in part" ledgers to the Adversarial review tab, leaving only genuine open questions here (FLX 1; COV 1 to 3).

### R15-12 · Major · Targets: CONTRACT, ING, FLX, ANV
**Section:** Contract 7.5, 12 (crate map); ING D-ING-9; FLX "Forms" (`flux-forms`); ANV `anvil-implicit`
**Problem:** D-ING-9 promises "one mechanism" (a hash-consed expression DAG) for constraints, analytic Fields and weak forms, but the spec has three symbolic layers above the kernel IR: Ingot's `Expr` DAG, `flux-forms`' "Form IR", and `anvil-implicit`'s "Expression DAG, tapes". The crate map also forbids the handover: `flux-forms` (Physics row) and `anvil-*` (Geometry row) sit above `ingot-*` (Language row), so they cannot depend on the type Ingot hands them.
**Evidence:** ING D-ING-9: "handed over as a hash-consed expression DAG". FLX crate table: "`flux-forms` | Physics | Form IR, typing, symbolic differentiation". ANV: "`anvil-implicit` | Expression DAG, tapes, evaluators". Contract 12: "Each crate depends only on crates in its own or earlier rows".
**Fix:** Put one hash-consed symbolic expression type in `kernels` (module `kernels::expr`), with typed node sets for forms, implicit functions and residuals, and symbolic differentiation once. Ingot's `Expr<T>` lowers to it, `flux-forms` and `anvil-implicit` extend it, and the kernel IR compiles from it. Name it in contract 7.5 and FLX owns it. This removes two DAG implementations and makes D-ING-9 true.

### R15-17 · Major · Targets: CONTRACT, KLN, ING, ANV, FLX
**Section:** Contract 2 (Op, Node), 7.2; KLN "Keys"
**Problem:** `OpKey` keys more than Op nodes. Contract 7.2 item 1 covers "for Ingot code the code hashes of the modules actually used", so feature nodes key by the `OpKey` formula, and every node with `EntityId`s adds its `CallSite`. Meanwhile the glossary needs an exception to explain the name ("Rust types with the `Op` prefix name operations … except `OpKey`, which keys an Op node"). The name tells a reader the wrong scope, and the exception exists only to excuse it.
**Evidence:** Contract 2, Op: "Rust types with the `Op` prefix name operations (`OpImpl`, `OpCx`), except `OpKey`, which keys an Op node." Contract 7.2 item 1 as quoted; KLN node table.
**Fix:** Rename `OpKey` to `NodeKey` and define it once in 7.2 for every node kind, with per-kind items (operation identity and version, code hashes, `CallSite`, fidelity, host digest). The `Op` prefix then means "operation" without exception, and the glossary entry for Op shrinks to "a node that calls one operation, Wasm component or External Op". Do it before `base` freezes.

### R15-25 · Minor · Targets: KLN, PLT, FLX
**Section:** KLN operation contract (`OpCx::checkpoint`), "Derivatives" (step checkpoints), "Audit and encryption" (log checkpoints), "Sync, scale and recovery" (`--since <checkpoint>`)
**Problem:** "Checkpoint" names a cancellation poll, saved solver state and a signed log head.
**Evidence:** KLN: "`pub fn checkpoint(&mut self) -> Result<(), Abort>; // safe point, every 10 ms of CPU`"; "Step checkpoints of transient solves are CAS objects"; "Checkpoints carry Ed25519".
**Fix:** Rename `OpCx::checkpoint` to `OpCx::safe_point`, which matches KLN's own prose ("reaches a safe point"). Keep "checkpoint" for transparency-log checkpoints (C2SP's term), and call saved transient-solve state "step state", in a `StepState` retention class.

### R18-01 · Critical · Targets: KLN, PLT, FLX, ANV, CONTRACT
**Section:** KLN "Scope and the operation contract" (`OpImpl`, `OpCx`); PLT "GPU dispatch and resource usage", "GPU compute" (`det_sum`, `MemoryBudget::reserve`, `GpuPath`); contract 2 Abort, 7.2
**Problem:** `OpImpl::eval` returns `Result<Self::Outputs, Failure>`, while the calls an operation makes inside `eval` return `Result<_, Abort>` (`OpCx::checkpoint`, `det_sum`, `MemoryBudget::reserve`, `GpuPath::cpu`). The only way to propagate them with `?` is `impl From<Abort> for Failure`, which makes every Abort a catchable, memoized `Failure`. That breaks contract 7.2's central invariant at the type level. Conversely `GpuPath::cpu` returns only `Abort`, so a CPU path cannot report the typed numerical `Failure` PLT's own table promises ("Typed numerical `Failure` naming the kernel"). Neither `Failure` nor `Abort` has a Rust definition in any tab.
**Evidence:** KLN: `fn eval(&self, cx: &mut OpCx<'_>, inputs: Self::Inputs) -> Result<Self::Outputs, Failure>;` and `pub fn checkpoint(&mut self) -> Result<(), Abort>;`. PLT: `pub fn det_sum(cx: &OpCx, xs: &[f64]) -> Result<f64, Abort>;`, `pub cpu: fn(&OpCx, &I) -> Result<O, Abort>,`. Contract 7.2: an Abort "`try` cannot observe … and no node that observed one writes a memo entry". A grep of all tabs finds no `enum Failure`, `enum Abort` or conversion rule.
**Fix:** KLN defines in `base`, beside `OpImpl`:
```rust
pub enum Stop { Failure(Failure), Abort(Abort) }   // what an operation returns when it produces no value
impl From<Failure> for Stop { … }  impl From<Abort> for Stop { … }
pub type OpResult<T> = Result<T, Stop>;
fn eval(&self, cx: &OpCx, inputs: Self::Inputs) -> OpResult<Self::Outputs>;
```
`Failure` and `Abort` are defined there (`Failure` an extensible typed union with `code`, `why`, `fixes`; `Abort` a closed enum matching contract 2's list). There is no conversion between `Failure` and `Abort`, and a `trybuild` compile-fail oracle (KLN-O-ABORT-2) proves `Failure: From<Abort>` does not exist. Kiln memoizes only `Stop::Failure`. `GpuPath` becomes `gpu: fn(&OpCx, &dyn GpuCompute, &I) -> Result<O, GpuStop>` (where `GpuStop` is `Fallback(GpuError)` or `Stop`) and `cpu: fn(&OpCx, &I) -> OpResult<O>`. `Differentiable::{tangent, adjoint}` and FLX's `Sampler::sample` return `OpResult` too.

### R18-02 · Critical · Targets: CONTRACT, ANV, KLN, FLX, PLT
**Section:** Contract 4 (source closure); ANV "Behavior versions" (D-ANV-18); KLN D-KLN-2; PLT D-PLT-34
**Problem:** R9-06's fix does not hold, because a "source closure" of Rust modules has no mechanical definition. A Rust operation's behaviour depends on code reached through generics, trait impls, macros and inlining in other modules and crates, which no module-level hash can enumerate without compiler support. The closure lists only `linalg`, `kernels` back ends and `simd` reductions. It leaves out `anvil-geom` predicates and NURBS evaluation, `anvil-topo`'s encoding and canonical order, `field`, and every third-party crate an operation calls (sorts, small-vector and spatial-index crates, `std` itself). A `cargo update` or a refactor in `anvil-topo` can change released bits that only the corpus fingerprint might catch, the weaker check R9-06 set out to replace.
**Evidence:** D-ANV-18: "The closure is its own modules (such as `ssi@4`) plus the versioned modules of the result-affecting crates it calls: `linalg`, `kernels` back ends, `simd` reductions." No tab says how the hash is computed. D-KLN-2 keeps "a corpus fingerprint as a second check", which R9-06 called the weakest mechanism.
**Fix:** Define the closure at the Cargo level, where standard tools compute it. Each released operation family is its own crate (`anvil-op-blend`, `flux-op-solve-linear`; see R18-13), and a released version is a frozen source directory inside it (`src/v2/`) that may depend only on versioned path dependencies (`linalg-v3`, `anvil-geom-v5`) and exact third-party versions. The closure hash is SHA-256 over: the frozen directory's files; for each first-party dependency, its frozen version directory; for each third-party dependency, the `Cargo.lock` checksum; the `rust-toolchain.toml` pin and the `detmath` epoch. `cargo xtask closure-hash` computes it from `cargo metadata` and the lockfile. KLN-O-FPRINT-1 adds two planted cases: a bumped third-party patch version and an edit in `anvil-topo`, each refused.

### R18-03 · Critical · Targets: CONTRACT, PLT, ANV, FLX, UIX
**Section:** Contract 13.2 "Build program" items 1 and 4; PLT "The build program" (D-PLT-45)
**Problem:** A work item opens only when its oracles exist "as executable checks", and builders never edit `oracles/`. An executable Rust oracle must compile against the crate's API, which does not exist before the builder writes it. So either the oracle role invents signatures the builder must match exactly (nowhere specified), or the builder changes a signature and breaks a locked oracle it cannot fix. In one Cargo workspace, a builder's API change also breaks the workspace build through `oracles/`, which CI then blames on the builder. No tab says whether oracles bind to crate APIs, to `api` methods, to the CLI or to files.
**Evidence:** Contract 13.2: "A work item opens only when its oracle ids exist in `oracles/` as executable checks written by the oracle role and passed by the verifier." D-PLT-45: "Policy refuses builder Changes under `oracles/`." The Rust signatures in the tabs are fragments (R18-01, R18-06, R18-07 show they do not compile together).
**Fix:** Contract 13.2 adds a step before item 1: "**Interface first.** For each work item the oracle role writes a contract crate, `<crate>-contract`, with the public types and signatures the oracles call and bodies of `unimplemented!()`. The verifier checks it against the tab's Rust surface. Builders implement it and may not change it; a signature change is a Proposal by the oracle role." Oracles bind in this order of preference: `api` methods, CLI and file formats (black box); WIT worlds; contract crates. `oracles/` is a separate Cargo workspace that depends on contract crates by path, so builder code never breaks its build. PLT-O-BLD-4 adds: a builder Change that alters a contract crate is refused.

### R18-05 · Major · Targets: CONTRACT, PLT, ANV, UIX, FLX, KLN
**Section:** Contract 3 principle 6; PLT D-PLT-45, PLT-O-BLD-5; ANV and UIX Oracles
**Problem:** R12-13's held-out fix does not hold against agent builders, for three reasons. A "fixed hash rule" over a public corpus (the ABC subset, Thingi10K) lets a builder compute which case ids are held out and fetch those models from the public dataset. Unlimited CI runs return a pass or fail on held-out cases, which leaks them by adaptive querying, the known failure of reused holdouts. And nothing stops builder code from detecting the held-out harness (paths, environment, case counts) and behaving differently there.
**Evidence:** ANV: "ABC cases come only from the licence-filtered subset … Held-out splits follow a fixed hash rule outside the agent-readable tree." UIX: held-out scenes are "picked by a fixed hash rule from perturbed golden-product parameters and the licence-filtered ABC subset." D-PLT-45 limits only reading: "Held-out splits … are unreadable to builders." No tab limits held-out queries.
**Fix:** Principle 6 replaces "chosen by a fixed hash rule" with "chosen by a keyed hash (HMAC-SHA-256 under a key held only by the oracle role, rotated at each gate) or generated from a seed drawn at CI time". D-PLT-45 adds three rules. Builders' sandboxes have no network route to public corpora. Held-out results reach a builder only as one aggregate pass or fail per work item per day, with no per-case detail. Visible and held-out runs execute in byte-identical harnesses, with case order and count padded to a fixed size. PLT-O-BLD-5 adds a planted builder that probes held-out results case by case and must fail to identify more than chance.

### R18-06 · Major · Targets: KLN, PLT, FLX
**Section:** KLN "Scope and the operation contract"; PLT "GPU dispatch and resource usage" (`ComputePool::spawn`, `det_sum`); FLX "Rust API" (`Sampler`)
**Problem:** Three tabs give `OpCx` three incompatible shapes. KLN and FLX take `&mut OpCx<'_>`, a borrowed type with a lifetime. PLT moves an `OpCx` by value into a `'static` closure, which a borrowed type cannot satisfy, and its combinators take `&OpCx`. `checkpoint(&mut self)` cannot be called from rayon chunks, which hold only a shared reference, yet PLT says "`OpCx` checks cancellation at every chunk boundary". An agent implementing any one tab breaks the other two.
**Evidence:** KLN: `impl OpCx<'_> { pub fn checkpoint(&mut self) -> Result<(), Abort>; … }`. FLX: `fn sample(&self, cx: &mut OpCx<'_>, …)`. PLT: `pub fn spawn<R: Send + 'static>(&self, lane: PoolLane, cx: OpCx, f: impl FnOnce(&OpCx) -> R + Send + 'static)`; `pub fn det_sum(cx: &OpCx, xs: &[f64])`.
**Fix:** KLN states one shape: `OpCx` is an owned, cheaply cloneable handle (`#[derive(Clone)] pub struct OpCx(Arc<OpCxInner>)`), `Send + Sync`, with every method taking `&self`. Cancellation is an atomic flag read by `checkpoint(&self)`; the 10 ms cadence is a per-thread counter. Every signature in KLN, FLX, ANV and PLT takes `&OpCx`, and `ComputePool::spawn` takes `cx: OpCx` by value. PLT-O-RT-1's harness compiles the four tabs' signatures together.

### R18-07 · Major · Targets: KLN, ANV, FLX
**Section:** KLN "Scope and the operation contract"; ANV "Rust surface and WIT interfaces" (operation registry row)
**Problem:** `OpImpl` has associated constants and associated types, so it is not dyn-compatible. Kiln, which is generic and sits below Anvil and Flux in contract 12, cannot hold a registry "name and `ingot.lock` pin → `OpImpl`" of hundreds of operations or call one by name from the Ingot interpreter, `crucible:ops` or an archived build. The type-erasure layer every caller needs is unspecified, so each consumer would invent its own.
**Evidence:** KLN: `pub trait OpImpl: Send + Sync + 'static { const ID: OpId; const VERSION: u32; const GRADE: DeterminismGrade; type Inputs: OpInputs; type Outputs: OpOutputs; … }`. ANV's operation registry row: "Name and `ingot.lock` pin → `OpImpl`".
**Fix:** KLN adds the erased trait and its blanket impl in `base`:
```rust
pub trait DynOp: Send + Sync {
    fn id(&self) -> OpId; fn version(&self) -> u32; fn grade(&self) -> DeterminismGrade;
    fn closure_hash(&self) -> ClosureHash;
    fn eval_dyn(&self, cx: &OpCx, inputs: &[Value]) -> OpResult<Vec<Value>>;
}
impl<T: OpImpl> DynOp for T { … }        // decode Inputs from Values, encode Outputs
pub struct OpRegistry { ops: BTreeMap<(OpId, u32), Arc<dyn DynOp>> }
```
`Value` is the erased representation from R18-09. Registration uses `inventory`-free explicit lists per crate (`anvil_op_blend::register(&mut OpRegistry)`), so registration order is deterministic.

### R18-09 · Major · Targets: ING, FLX, KLN, ANV, UIX, CONTRACT
**Section:** Contract 5 `Quantity<D>`, `Field<D, V>`; ING "Types and dimensions"; FLX "Rust API"; UIX "From gesture to Ingot edit"
**Problem:** The contract names Rust types canonical, but no tab says how Ingot's types exist in Rust. Stable Rust cannot compute `Quantity<D1·D2>` from const generics (`generic_const_exprs` is unstable), and the strong angular system with rational powers rules out simple marker types. Ingot also creates domains and value types at run time (user enums, tuple domains), so `Field<D: Domain, V: Value>` with `PhantomData` cannot be the representation Kiln stores or `crucible:ops` passes. Tabs already improvise: ANV uses `Length` and `Angle`, UIX `Quantity<Dyn>`, and FLX a generic `Field<D, V>`.
**Evidence:** ING: "`Quantity<D>` | A `Real` in coherent SI units with dimension `D`; checked at compile time, erased at run time" (true of Ingot, silent on Rust). UIX: `SetMeasure { target: Query, measure: Measure, to: Quantity<Dyn> }`. FLX: `pub struct Field<D: Domain, V: Value> { header, repr, _kind: PhantomData<(D, V)> }`.
**Fix:** ING and FLX state one rule in their Rust surfaces. The erased forms are canonical: `Value` (an enum over scalars, `DynQuantity { si: f64, dim: Dim }` with `Dim` a vector of rational exponents over the eight base dimensions plus a kind id, records, lists, handles) and `DynField { domain: DomainDesc, value: ValueDesc, header, repr }`. These are what Kiln memoizes, the CAS encodes and `crucible:ops` carries. Typed views are generated, not hand-written: `base` generates newtypes (`Length`, `Stress`, `Torque`) and the `Mul`/`Div` impls the prelude kind table lists, from that table, plus `Field<D, V>` as a checked view over `DynField` (`TryFrom<DynField>`). Rust code never uses `uom` or `typenum`.

### R18-11 · Major · Targets: PLT, CONTRACT, FLX, ANV
**Section:** Contract 13.3 (browser cold start); PLT "The browser target", D-PLT-9
**Problem:** Rust has no dynamic linking between Rust modules on `wasm32-unknown-unknown`, so every operation, solver and translator-host path of the engine lands in one engine module. Phase 1's engine may fit 25 MiB brotli. But every later phase adds Flux discretizations, CFD, electromagnetics, explicit dynamics, battery models and MFG operations to the same module, and the first-visit row never relaxes. No tab measures the module size or plans a split, so the row fails late and expensively.
**Evidence:** Contract 13.3: "first visit 8 s at 50 Mbit/s, with at most 25 MiB of brotli-compressed initial Wasm". PLT names two web builds "from one source" and no size budget per crate. Binaryen's `wasm-split` splits one module "in two or instrument[s] a module to inform future splitting", keeping one memory and table (https://raw.githubusercontent.com/WebAssembly/binaryen/main/src/tools/wasm-split/wasm-split.cpp).
**Fix:** PLT adds D-PLT-48: the engine module is split by profile-guided `wasm-split` into a primary module (Kiln, CAS, `repo`, the interpreter, the operations golden-product traces touch) and lazily fetched secondary modules sharing its memory. The profile comes from instrumented golden-product sessions. Whether the threaded build splits with shared memory is a phase 0 spike [unverified]; if it cannot, operation families above a size threshold become first-party Wasm components loaded on first use. PLT's table gains a row per phase for the primary module's brotli size, gated by PLT-O-PERF-1, and `cargo xtask wasm-size` reports each crate's contribution on every merge.

### R18-13 · Major · Targets: CONTRACT, ANV, FLX, PLT, KLN
**Section:** Contract 12; ANV "Crates" (D-ANV-1); PLT "Build, release and CI" targets; D-PLT-1
**Problem:** The crate map gives agents few, large hot spots. `anvil-ops` holds "every operation's `OpImpl`", so parallel builders on blends, Booleans, shells and conversions edit one crate, and its frozen versioned modules accumulate there. That defeats PLT's "`anvil-ops` edit-and-test loop under 20 s". `base` holds every shared type from every tab, so each owner's edit rebuilds the whole workspace and invalidates the shared sccache for every agent. `apps/platform` is one crate binding Windows, macOS, Linux, web, iPadOS and Android.
**Evidence:** ANV crate table: "`anvil-ops` | The `Body` enum, every operation's `OpImpl`, Booleans, conversions, `GeometryQuery`, the `Classify` implementation". PLT: "Targets: a no-op `cargo check` under 2 s, an `anvil-ops` edit-and-test loop under 20 s and a warm-cache CI build under 6 minutes." Contract 12 puts every shared value, identity, handle and operation-contract type in `base`.
**Fix:** Contract 12 sets crate granularity rules. Anvil keeps `anvil-ops` for the `Body` enum and dispatch only, and puts each operation family in its own crate (`anvil-op-boolean`, `anvil-op-blend`, `anvil-op-shell`), which is also R18-02's closure unit; Flux does the same. `base` splits into `base-id` (identities and handles), `base-value` (section 5 values) and `base-op` (operation contract), and after the phase 0 gate each changes only by a contract ruling. `apps/platform` becomes one crate per OS family (`platform-windows`, `platform-apple`, `platform-linux`, `platform-web`, `platform-android`) behind the same traits; D-PLT-1's "exactly one crate" becomes "only `apps/platform-*`".

### R18-14 · Major · Targets: CONTRACT, PLT, UIX, FLX
**Section:** Contract 12 (`unsafe` and `bridges/`); PLT "Crates", D-PLT-14, D-PLT-17, `CryptoProvider`; UIX "Display data"
**Problem:** The `unsafe` rule names crates, but the build links C and C++ through ordinary crates.io dependencies that the rule never mentions. mimalloc and CORE-MATH are C, and aws-lc-rs is C and assembly that needs CMake. meshoptimizer, whose codecs UIX adopts for every page, is C++. Each needs a C toolchain in the hermetic, reproducible builders and `-ffp-contract=off` where it affects results. Each needs a stated `wasm32-unknown-unknown` story, since `detmath` must be canonical in browsers and meshoptimizer decoding runs in the browser renderer. Meanwhile `kernels` is granted `unsafe` for "code-loading", though runtime-generated modules load through Wasmtime, whose unsafe deserialization belongs in `wasm-host`.
**Evidence:** Contract 12: "`unsafe` is allowed only in `simd`, `gpu`, `wasm-host`, the code-loading parts of `kernels`, `bridges/` and `apps/platform`." `bridges/` holds "optional FFI: PETSc, hypre, GPU vendor specifics". PLT: "linked C and C++ use `-ffp-contract=off`, checked in CI". UIX: "Pages use meshoptimizer's codecs".
**Fix:** PLT adds a native-code register to `deps/approved.toml`. Each C or C++ dependency records why no Rust crate serves, its targets including wasm32 (built with clang and a pinned wasi-libc sysroot, or excluded with the Rust fallback named), its compile flags, whether it affects results (only CORE-MATH may), and its fuzzing. Only register entries may build C. Contract 12 drops "the code-loading parts of `kernels`": `kernels` emits Wasm bytes and asks `wasm-host` to load them. The browser `CryptoProvider` is WebCrypto in `apps/platform-web`, stated in PLT.

### R18-27 · Minor · Targets: ANV, FLX
**Section:** ANV "Rust surface and WIT interfaces"; FLX "Rust API"
**Problem:** Two public Rust types share the name `Repr`: Anvil's enum of Body representations and Flux's enum of Field representations. Both appear in signatures that agents will import together in `anvil-implicit` and every Flux crate.
**Evidence:** ANV: `pub enum Repr { BRep(Arc<BRep>), Implicit(Arc<Implicit>), Mesh(Arc<Mesh>), SubD(Arc<SubD>) }`. FLX: `repr: Repr, // the eight representations`.
**Fix:** Rename them `BodyRepr` and `FieldRepr`.

### R18-30 · Minor · Targets: FLX, PLT
**Section:** FLX D-FLX-8; PLT D-PLT-15; contract 7.3
**Problem:** D-FLX-8 still says "the 512-bit canonical lane order", while contract 7.3 and D-PLT-15 define the rule as the 8-lane f64 or 16-lane f32 tree of `det_sum` for horizontal operations only, and D-PLT-15 rejects 512-bit virtual vectors. An agent reading FLX can build 512-bit virtual vectors for all kernel code, which spills on x86-64-v2 and SIMD128.
**Evidence:** D-FLX-8: "with the 512-bit canonical lane order and no FMA in the canonical class". D-PLT-15: "*Rejected:* 512-bit virtual vectors for all code (round 1)".
**Fix:** D-FLX-8 reads "with contract 7.3's canonical lane order for horizontal operations (the 8-lane f64 or 16-lane f32 tree of `det_sum`); element-wise code uses any native width".

### R18-31 · Minor · Targets: PLT, FLX, ECO
**Section:** PLT "Isolation and sign-in"; FLX D-FLX-9
**Problem:** From phase 1 the engine worker compiles Wasm at run time: user forms "compile to Wasm SIMD128 modules", and the first-party component runtime instantiates translator modules. Under any content security policy this needs `'wasm-unsafe-eval'` on the app origin, but PLT states CSPs only for the sandbox site, and ING mentions the need only for the phase 2 code generator.
**Evidence:** ING Platform notes: "pages allow `'wasm-unsafe-eval'`, without which 'WebAssembly is blocked'". D-PLT-42 gives the sandbox site's CSP; no row gives the main origin's.
**Fix:** PLT adds the app origin's policy: `default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self' <team server>; frame-src <sandbox site>; object-src 'none'`. PLT-O-WEB-1 checks the served headers and that the engine worker compiles a user-form module under them.

### R18-33 · Minor · Targets: PLT, FLX, UIX
**Section:** PLT "GPU compute" (known-answer tests); contract 13.3 cold start
**Problem:** Every compute pipeline runs a known-answer test "at creation and after driver or OS updates", and wgpu's `PIPELINE_CACHE` exists only on Vulkan. Run eagerly at start-up on DX12 and Metal, pipeline creation plus tests compete with the 1.5 s cold-start row, which the tab does not budget.
**Evidence:** PLT: "Each pipeline reproduces its class's recorded outputs at creation and after driver or OS updates." wgpu 30.0.1 `PIPELINE_CACHE`: "Supported platforms: Vulkan"; "Unimplemented Platforms: DX12, Metal" (https://docs.rs/wgpu/latest/wgpu/struct.Features.html).
**Fix:** Run known-answer tests lazily, before a pipeline's first result-affecting dispatch, and persist each pass keyed by (`GpuClass`, pipeline hash) in the local CAS until the driver or OS build changes. Until a pipeline passes, its Ops run on the CPU path. The cold-start row excludes compute pipelines, which PLT-O-PERF-1 states.

### R19-11 · Major · Targets: MEC, FLX, ANV
**Section:** MEC Lattices; FLX Topology optimization; ANV Conversions and error propagation
**Problem:** Generative design with manufacturing methods is a standard Fusion workspace, and in Crucible it exists only as FLX building blocks: no MEC feature takes a design space, preserved regions, load cases and manufacturing methods and returns outcomes to compare. Phase 1 serves additive parts only. Milling and casting constraints arrive in FLX's phase 2, but a machined or cast outcome needs fitted B-rep faces, which ANV ships in phase 3, so generative design for subtractive parts is phase 3 without anyone saying so. Crucible's real advantage, that preserved interfaces keep their exact faces, `HoleSpec`s and GD&T through leaf-preserving conversion, is stated only for GP2's lattice.
**Evidence:** Fusion, Specify manufacturing methods (https://help.autodesk.com/cloudhelp/ENU/Fusion-GenerativeDesign/files/GD-SPECIFY-MFG-METHOD.htm): Unrestricted, Additive, Milling on "2.5-, 3-, or 5-axis" configurations, 2-axis cutting and casting. FLX density method: "1 (compliance, volume), 2 (stress, robust, manufacturing)". ANV: "Implicit → BRep … 1 (facet), 3 (fitted)". MEC D-MEC-34: a STEP hand-off "needs the region converted to B-rep within the same tolerance".
**Fix:** Add `std::mech::generate(space: Body, keep: [Query], avoid: [Body], cases, methods: [Method], objectives) -> [Outcome]` to MEC: phase 1 for `Additive` and `Unrestricted`, phase 2 for `Milling { axes, tool }`, `TwoAxisCutting` and `Casting { pull }` with FLX's manufacturing constraints. Outcomes are variants for UIX's variant grid, each carrying mass, margins and MFG's planned cost. Move ANV's fitted Implicit → BRep row (D-ANV-36) to phase 2 so subtractive outcomes release through STEP; until it ships, state that phase 2 outcomes for milling release as facet B-rep only to mesh-capable processes. Add one line to MEC's lead: kept interfaces stay exact, named and toleranced in every outcome.

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

### R20-02 · Critical · Targets: FLX, COV, CONTRACT
**Section:** Contract 7.1 Flux (per-region discretization); FLX "Per-region models", "Spaces, elements and measures"; COV "Solid mechanics", "Electromagnetics"
**Problem:** No tab offers plane stress, plane strain, generalized plane strain, axisymmetric (with or without torsion) models, mirror-symmetry or antisymmetry reduction, or cyclic symmetry with harmonic indices (nodal diameters) for modal and static solves. Contract 7.1's per-region list reduces only to shells and beams. O-ring and lip seals, pressure vessels, flanges, rotating discs, bolts, solenoids and coils are routinely solved as axisymmetric models in Abaqus, Ansys and COMSOL at one hundredth of the 3D cost; bladed discs and fans use cyclic sectors. A hyperelastic seal with contact in 3D on an octree is impractical where the incumbent solves it in seconds.
**Evidence:** Abaqus's axisymmetric library has CAX, CGAX "Generalized axisymmetric elements with twist", thermally coupled, pore-pressure, acoustic and piezoelectric variants (https://ceae-server.colorado.edu/v2016/books/usb/pt06ch28s01ael05.html). Ansys Mechanical lists "symmetry region" and "cyclic region" objects (https://ansys.synopsys.com/products/structures/ansys-mechanical). COMSOL documents symmetry, antisymmetry and periodic conditions to reduce a coil "to a one-eighth model" (https://www.comsol.com/blogs/exploiting-symmetry-simplify-magnetic-field-modeling). `grep -i "axisymm\|plane strain\|harmonic index\|nodal diameter"` over `docs/spec` returns nothing; FLX line 593 names "cyclic constraints" only as a constraint type.
**Fix:** Contract change request (FLX files it): extend 7.1's per-region rule with "dimensional reduction by symmetry: plane stress, plane strain, generalized plane strain and axisymmetric models, detected or declared, and symmetry, antisymmetry and cyclic-sector reductions, each with a check that loads and geometry satisfy the symmetry". In FLX:
- `flux::mark_reduction` gains `ReductionKind::Axisymmetric { axis }` and `Planar { kind }`, detected when Anvil's certified analysis shows a revolved or prismatic Body and the study's conditions share the symmetry; `std::sim::symmetry(planes:, kind: Symmetric | Antisymmetric)` and `cyclic(sector:, count:, harmonics: 0..=N/2)` are explicit.
- Spaces: `H1(domain: section, kind: axisymmetric(twist: bool))` with the r-weighted measure, Fourier-mode extension for non-axisymmetric loads in phase 3.
- Cyclic modal analysis solves complex Bloch-periodic sector problems per harmonic index and returns a `Field<(Body, Mode, HarmonicIndex), Displacement>`; the full-model expansion is a display operation.
- A violated symmetry (a non-symmetric load, a feature off the plane) returns `SymmetryBroken { entity }`, never a silent wrong answer.
Phase 1 for planar and axisymmetric elasticity and thermal (they reuse H¹ kernels in 2D), phase 2 for symmetry with contact and hyperelasticity, phase 2 for cyclic modal (fans and gear blanks in GP3). Oracle FLX-O-SYM-1: axisymmetric thick cylinder (Lamé), NAFEMS axisymmetric cases and a cyclic bladed-disc modal benchmark agree with the full 3D model within the 3D model's budget. COV adds the axisymmetric and planar rungs to the solid, thermal and magnetostatic ladders (D-COV-2).

### R20-03 · Major · Targets: FLX, COV
**Section:** COV "Dynamics and stability"; FLX "Eigenvalue problems", "Reduced models and surrogates"
**Problem:** The linear dynamics workflow analysts rely on is incomplete and has no owner. Prestressed modal and buckling (stress stiffening from preload, pressure or spin, and spin softening) appear nowhere. Mode-superposition harmonic response, PSD random response and response spectrum are listed only in COV's "Vibration and shock" row with no FLX operation, capability row or oracle; response-spectrum analysis appears only as a civil L1 rung in phase 7. Damping models (Rayleigh, modal, structural hysteretic, frequency-dependent viscoelastic) are "declared" without a type. Vibration fatigue from PSD (Dirlik, narrow band) is missing from the durability rows.
**Evidence:** Ansys Mechanical names "modal, harmonic, spectrum response and random vibration" (https://ansys.synopsys.com/products/structures/ansys-mechanical); its Nastran export lists "Modal (Pre-Stressed): SOL103, STATSUB" (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_NASTRAN_export_supported_features.html). COV line 268 ("Direct frequency response; PSD response") cites no FLX oracle; COV line 449 phases response spectrum at 7.
**Fix:** FLX adds a "Linear dynamics" subsection with these rows:

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Linear perturbation | Modal and buckling about a converged nonlinear state, with stress stiffening, spin softening and pressure load stiffness | `BaseStateNotConverged` | FLX-O-DYN-1 | 2 |
| Mode-superposition harmonic | Modes plus residual vectors; `Field<(Body, Frequency), Complex<V>>`; truncation part in the budget | `ModalTruncation { missing_mass }` above 10% | FLX-O-DYN-2 | 2 |
| Random vibration | PSD inputs, one- and multi-point, 1σ and 3σ Fields, correlation | As above | FLX-O-DYN-2 | 2 |
| Response spectrum | Single- and multi-point; SRSS, CQC, NRL and DDAM combination; missing-mass correction | As above | FLX-O-DYN-3 | 2 |
| Damping | `Damping::Rayleigh`, `Modal`, `Structural`, `Viscoelastic(Field<Frequency, ...>)` on Materials and joints | Undamped resonance in a harmonic band fails | FLX-O-DYN-2 | 2 |

COV moves response spectrum to phase 2 in its "Vibration and shock" row, adds Dirlik and narrow-band PSD fatigue to "Stress-life" (phase 2), and points rotordynamics' rotating-frame rung at FLX-O-DYN-1. Oracles: NAFEMS forced-vibration benchmarks and an analytic SDOF and two-DOF spectrum case.

### R20-05 · Major · Targets: FLX, COV
**Section:** FLX lead, "Scope and architecture", "State of the art"; COV "State of the art"
**Problem:** FLX never says why an Ansys, Abaqus or COMSOL user is better off. Its lead names methods; its State of the art table names only open-source leaders (DOLFINx, MFEM, deal.II, SLEPc, Palace) and LS-DYNA once. The advantages that incumbents cannot copy quickly are scattered and unstated as advantages: solves on the exact B-rep with no meshing or defeaturing step; results that stay associative with the design and recompute incrementally; every result with a bound in a stated norm, a validity zone and a confidence; bit-identical results across platforms for audit; weak forms with compile-time dimensions and form-level derivatives (COMSOL offers a Weak Form PDE interface, so "weak forms" alone is not a difference); and agents that run studies under the same checks.
**Evidence:** COMSOL documents "Weak Form PDE (w)", with boundary, edge and point variants (https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_ref_equationbased.32.023.html), and its Application Builder (https://www.comsol.com/comsol-multiphysics). FLX lines 860 to 889 name no commercial code except LS-DYNA. Ansys Mechanical advertises "Mesh Quality Worksheet" and automated meshing (https://ansys.synopsys.com/products/structures/ansys-mechanical), which Crucible makes unnecessary but never says so.
**Fix:** Rewrite FLX's lead's last sentence as: "Unlike Ansys, Abaqus and COMSOL, Flux solves on the exact design geometry without a meshing or defeaturing step, recomputes only what an edit touches, and reports every result with a bound, a validity zone and a confidence, identically on every platform." Add a column "Incumbent reference" to FLX's and COV's State of the art tables (Ansys Mechanical, Abaqus, Simcenter Nastran, COMSOL, Fluent, STAR-CCM+, HFSS per row) and state the measured difference in "How we measure" (for example, "time from STEP import to a decided stress check, against Ansys Mechanical on the same 20 parts, including meshing and defeaturing").

### R20-06 · Major · Targets: ECO, FLX, COV
**Section:** ECO format catalog ("Nastran BDF; Abaqus input"); FLX "Interfaces with other subsystems"
**Problem:** ECO reads and writes Nastran BDF and Abaqus input at phase 3 as "FE models; OP2 results as Fields", but no tab says what Crucible does with an imported deck: Flux has no element semantics for CQUAD4, CBUSH, RBE3, CONM2, PCOMP, MPCs or SPCs on grid ids, so a company's validated legacy models can be viewed but not run or compared. The export direction matters as much: aerospace and defence customers deliver Craig–Bampton models as Nastran DMIG or OP4 for coupled loads analysis, and some regulators expect the qualified incumbent's run. LS-DYNA keyword decks, the crash and drop lingua franca, are absent.
**Evidence:** ECO line 224; Ansys documents a mapping of its own model to SOL101, SOL103, SOL109, RBE2, RBE3, CBUSH and CONM2 (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_NASTRAN_export_supported_features.html), showing that deck export with idealizations is what users expect.
**Fix:** FLX adds "Imported FE models" with a contract: an imported deck becomes a `Mesh` Body plus a study whose cards map to Flux forms and R20-01's idealizations; unmapped cards fail with `UnmappedCard { card, line }`, never dropped. Oracle FLX-O-DECK-1: the NAFEMS decks distributed for Nastran verification run in Crucible within 1% of their reference values. Add export of a study to BDF (SOL 101, 103, 111, 112) and of Craig–Bampton reductions as DMIG and OP4, phase 3, so an incumbent can re-run a Crucible model. ECO adds LS-DYNA keyword read for meshes, parts, materials and contacts at phase 3 with GP5's drop model. The deck route is labelled `Unverified` until its oracle passes per card family.

### R20-07 · Major · Targets: CONTRACT, FLX, PLT
**Section:** Contract 13.3; FLX "Interactive latency", "Linear algebra", "State of the art"
**Problem:** The only solve-size target is `Interactive` elasticity up to 100,000 DOFs; there is no target for a `SignOff` solve of the size analysts run daily (5 to 50 million DOFs on a workstation), and none for CFD throughput. Phase 1's canonical direct solver reaches "about 2M DOFs" and distributed solves wait for phase 4. Meanwhile Fluent's native GPU solver reports single-GPU speed-ups of 8 to 15 times over 8 to 32 CPU cores, and Crucible's canonical class runs CPU-only with no flow target at all.
**Evidence:** Contract 13.3 row "Interactive simulation update"; FLX lines 528 and 549. Ansys reports "8.32X for an air intake system" and "8.6X for a traction inverter" on one A100 (https://ansys.synopsys.com/blog/unleashing-the-full-power-of-gpus-for-ansys-fluent-part-2), vendor-stated.
**Fix:** File a change request adding two 13.3 rows, both targets: "`SignOff` linear static, 10M DOFs at p = 2 on an immersed GP1-class part, recertified, under 10 minutes on the reference workstation (phase 2) and 50M DOFs on a 64-core server (phase 3)"; "incompressible flow, 10M cells laminar steady to residual 10⁻⁶, time per iteration within 2× of OpenFOAM on the same CPU (phase 3) and, on a `Gpu` class with CPU certification, within 2× of Fluent's published GPU speed-up shape on the same case family (phase 4)". FLX states the per-phase DOF ceiling in "Linear algebra" and adds FLX-O-KER-7 for both rows.

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

### R20-10 · Major · Targets: FLX, COV
**Section:** FLX "Post-processing and display"; COV "Civil structures and geomechanics"
**Problem:** Pressure-vessel and piping engineers classify stress by linearizing it through the wall into membrane, bending and peak parts (ASME Section VIII Division 2 Part 5, EN 13445). No tab offers stress linearization. This is also a missed advantage: membrane and bending stresses are bounded linear functionals of the stress over a stress classification line, so Flux could report them with `Guaranteed` goal bounds where the incumbent reports unbounded numbers.
**Evidence:** Ansys's Linearized Stress results "calculate membrane, bending, peak, and total stress along a straight line path" (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_linearized_stresses.html). Contract 5 admits `Guaranteed` goal bounds for "bounded linear functionals".
**Fix:** Add `f.linearize(along: Query or segment, curvature: Auto)` returning membrane, bending and peak tensors with goal-oriented bounds (`Guaranteed` on fitted simplices with polynomial data, calibrated `Estimated` elsewhere), phase 2. COV adds a pressure-equipment row (ASME VIII-2 Part 5 and EN 13445-3 design-by-analysis, licensed data packages) in phase 5 with GP8's structural checks, with ratcheting and plastic-collapse routes on FLX's plasticity rows.

### R20-11 · Major · Targets: FLX, COV
**Section:** FLX "Fluids and free surfaces"; COV "Fluids", "Aerospace", "Heat transfer"
**Problem:** No tab offers rotating-machinery CFD: a moving reference frame, a mixing plane or a sliding mesh. Nor does it offer the macro models electronics cooling relies on: a fan as a pressure jump with a P–Q curve, perforated plates, heat-exchanger and porous-resistance blocks. GP6's propellers and motor cooling, GP5's enclosure if it gets a fan, and every pump, blower and compressor need them. COV routes rotors to blade-element and vortex methods only.
**Evidence:** Fluent offers the Multiple Reference Frame model, the Mixing Plane Model and the Sliding Mesh Model; the first two are "steady-state approximations" (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/flu_th/flu_th_sec_mzrrf.html). `grep -i "overset\|MRF\|turbomach\|fan curve"` over `docs/spec` returns nothing.
**Fix:** FLX adds a "Rotating and moving zones" row: rotating-frame source terms in the flow forms (phase 3, laminar; phase 4, RANS), mixing-plane interfaces (phase 5), and sliding interfaces on the octree reusing the electromagnetic sliding interface (phase 4, for GP6). Add `fan(face, curve: Field<VolumeFlow, Pressure>, swirl:)` and `resistance(region, K: Tensor)` as Network-coupled boundary and volume models in phase 3 with GP5. COV adds a "Turbomachinery and fans" row with envelopes (frozen-rotor validity: blade-row interaction `Flag`) and the NASA Rotor 37 or a fan-curve benchmark.

### R20-12 · Major · Targets: FLX, COV
**Section:** FLX "Gradients and optimization", "Fluids and free surfaces"
**Problem:** Flux's adjoints come "from forms", but its production flow path for RANS and conjugate heat transfer is cell-centred finite volume, which is not a weak form. So it is unspecified whether the flow solver GP6 uses has an adjoint at all. STAR-CCM+ and Fluent sell adjoint shape optimization of ducts, manifolds, heat sinks and aerodynamic surfaces. Without a flow adjoint, Crucible's associative optimization (its strongest argument) stops at structures.
**Evidence:** FLX line 457 ("Cell-centred finite volume runs on cut cells and polyhedra") against FLX line 706 ("Flux differentiates the discretized problem from its forms"). Siemens shows STAR-CCM+'s adjoint-derived "surface sensitivity of drag" driving shape changes (https://blogs.sw.siemens.com/simcenter/adjoint-shape-optimization-for-improved-car-aerodynamics/).
**Fix:** Decide in FLX: either express finite volume as a DG(0) weak form in the form language, so the compiler derives its discrete adjoint like any form, or state that RANS ships as stabilized FEM or DG forms with FV only for `Preview`. Add capability rows "Steady flow adjoint (laminar, phase 3; frozen-turbulence and full RANS adjoint, phase 4)" with oracle FLX-O-OPT-4: Taylor order 2 on a duct pressure-drop goal and agreement with a finite-difference sensitivity on a backward-facing step.

### R20-13 · Major · Targets: FLX, ELX, COV
**Section:** FLX "Electromagnetics"; ELX "RF: antennas and matching networks"; COV "Electromagnetics"
**Problem:** Phased arrays, frequency-selective surfaces, metasurfaces and radomes are designed as unit cells with Bloch-periodic (phase-shifted) boundaries and Floquet ports, then as finite arrays by domain decomposition. FLX's ports come only from 2D eigenmode solves, its periodic constraints are structural, and no tab mentions arrays beyond ELX's antenna feature list. GP11's CubeSat antennas, and any 5G or radar customer, would stay in HFSS.
**Evidence:** PADT, an Ansys channel partner, describes HFSS unit cells in which "Master/Slave boundaries are always paired" and a Floquet port that is "always linked to P/S boundaries", plus finite array domain decomposition (third-party, https://www.padtinc.com/blog/efficient-and-accurate-simulation-of-antenna-arrays-in-hfss/). FLX D-FLX-32 lists wave and lumped ports only.
**Fix:** FLX adds to frequency-domain Nédélec FEM: Bloch-periodic boundary pairs with scan-angle phase, Floquet ports with a computed mode set and evanescent-mode attenuation check, and finite-array assembly from a cached unit-cell discretization by domain decomposition (phase 5). Oracles: an infinite dipole array's active reflection against an analytic or published reference, and an FSS transmission curve. ELX adds `array(element, lattice, taper)` returning embedded patterns as `Field<(Ports, Direction, Frequency), Complex<...>>`; COV moves "RF and antennas" general rows to state the periodic rung.

### R20-14 · Major · Targets: ELX, FLX
**Section:** ELX "Power converters and magnetics", "Signal integrity"; FLX "Electromagnetics"
**Problem:** Power-electronics design depends on 3D quasi-static RLC extraction: partial self and mutual inductances, resistance and capacitance of busbars, power modules, connectors, packages and hot loops, frequency-dependent and exported as SPICE subcircuits. ELX says hot-loop inductance comes "from Flux extraction" and lists "quasi-static and full-wave extraction" without a method, port definition, frequency treatment or output type. GP6's ESC and GP12's charger need it.
**Evidence:** Ansys Q3D "extracts resistance, partial inductance and capacitance parasitics from high-power" bus bars, cables and inverter modules and generates "an equivalent SPICE model" (https://ansys.synopsys.com/products/electronics/ansys-q3d-extractor). ELX line 756; COV line 354.
**Fix:** FLX adds `flux::extract_rlcg(bodies, terminals, band)`: magnetoquasistatic A–φ with terminal currents for partial inductance and AC resistance, electrostatic BEM or FEM for capacitance (bempp-rs path), returning `Field<(Ports, Ports, Frequency), Complex<Impedance>>` with error budgets, plus a passive SPICE subcircuit by ELX's vector fitting. Phase 4 with GP6. Oracle: analytic partial inductance of parallel bars and a coaxial line, and a busbar against a published Q3D-class or measured case. ELX's "Losses and parasitics" row cites it.

### R20-15 · Major · Targets: ELX, FLX, ECO
**Section:** ELX "Co-simulation"; FLX "Networks"
**Problem:** Modelica users bring their models as source: the Modelica Standard Library and commercial libraries. ELX accepts Modelica only as compiled FMUs and leaves Rumoca as a phase 5 option. So a Dymola user cannot edit, version, diff or optimize their models in Crucible, cannot use Crucible's adjoints through them, and needs a second tool to build each FMU. Since Crucible's Network compiler already does Pantelides with dummy derivatives, BLT and tearing, the missing piece is a front end, not a solver.
**Evidence:** ELX line 681 ("Modelica arrives through FMUs"). Dymola is built on "an object-oriented language for physical modeling" with multi-domain libraries (https://www.3ds.com/products/catia/dymola). The Modelica Standard Library is v4.1.0 and spans mechanical, electrical, magnetic, thermal, fluid and control components plus state machines (https://github.com/modelica/ModelicaStandardLibrary).
**Fix:** ECO adds a Modelica reader as an `io/` Wasm component (Rumoca or a clean-room parser) that translates a declared subset (equation sections, connectors with flow and stream variables, `inner` and `outer`, records, replaceable classes) into `network { … }` Ingot, phase 4 for GP6. Unsupported constructs stay as an FMU fallback with `Untranslated { construct }`. Oracle: the MSL's `Modelica.Electrical`, `Mechanics.Rotational`, `Mechanics.Translational` and `Thermal.HeatTransfer` examples translate and match MSL reference results within their tolerances. ELX states the translation coverage as a percentage of MSL example models (target: 80% by phase 5).

### R20-16 · Major · Targets: ELX, COV, FLX
**Section:** ELX "Networks in every domain"; COV "Fluids", "Heat transfer"
**Problem:** `Network` declares fluid ports, but no tab ships the element libraries that system engineers use: hydraulic pumps, valves (spool, poppet, check, relief), accumulators, cylinders, pipes with compressibility and cavitation; pneumatics; thermofluid components with real-fluid media (refrigerant loops, coolant circuits, heat exchangers with effectiveness-NTU). GP12's pack coolant loop and every actuation system need them, and Amesim or Modelica.Fluid users would stay put.
**Evidence:** Amesim's libraries address "hydraulic, pneumatic, thermal, electrical, mechanical" domains, with thermal-hydraulic libraries for "heat exchangers, and refrigerant loops" (https://blogs.sw.siemens.com/simcenter/many-physical-domains-and-applications-in-one-system-simulation-tool/). `grep -i "valve\|accumulator\|pneumatic"` over FLX, COV and ELX returns nothing.
**Fix:** ELX adds `std::systems::fluid` element libraries: incompressible and compressible hydraulic elements, pneumatic elements and two-phase thermofluid elements with stream connectors (balanced across and through variables per D-ELX-15, plus enthalpy transport), media from CoolProp. Phase 4 for single-phase coolant and hydraulics (GP6 and GP12 cooling), phase 5 for two-phase and pneumatics. COV adds envelopes (cavitation and choking `Flag`) and a ladder link from 1D pipes to FLX's 3D flow. Oracle: Modelica.Fluid example agreement and analytic water-hammer wave speed.

### R20-19 · Major · Targets: FLX, COV
**Section:** FLX "Surrogates"; COV "Surrogates and learned models"
**Problem:** Geometry-agnostic AI surrogates are the fastest-moving competitor in simulation, and FLX ships surrogates only in phase 4 without naming them or stating the difference. Ansys SimAI predicts 3D fields from unparametrized geometry and returns a "confidence level"; Luminary sells "Large Physics Models" with "<2% prediction error". Crucible's real difference is that a surrogate prediction can never decide a `SignOff` check without a bound in the check's norm or a confirming solve, and that weights are pinned and labelled. Neither tab says so against these products, and phase 4 leaves three phases with no learned acceleration.
**Evidence:** SimAI "always returns a result", and each prediction carries "a confidence level indicating whether it can be trusted" (https://ansys.synopsys.com/products/simai). Luminary claims ">1K faster than simulation" (https://luminary.ai/). FLX D-FLX-14, phase 4 rows FLX-O-ROM-2.
**Fix:** Add SimAI, Luminary and PhysicsNeMo-based tools to FLX's surrogate State of the art row, with the measurement "no false `SignOff` `Pass` in 10⁴ adversarial evaluations, where their confidence indicators are measured on the same held-out set". Move `Preview`-only geometry surrogates (trained on Crucible's own cached `Interactive` results per design repository) to phase 2, since they never decide checks and Kiln's cache already holds the training data; keep `Interactive` and per-prediction bounds in phase 4.

### R20-21 · Major · Targets: FLX, UIX
**Section:** FLX "Per-region models" (D-FLX-26), "Meshing and adaptivity"
**Problem:** Incumbent users run submodeling: a coarse global model (often shells and beams) drives cut-boundary conditions on a refined local solid. Crucible makes routine submodeling unnecessary through goal-oriented hp-adaptivity, and D-FLX-26 already re-solves a 3D patch from a reduced model. But the tabs neither state the replacement nor expose the patch to users for the cases where it is still the workflow: a shell-modelled frame with a solid weld detail, or a supplier's global loads applied to a local part.
**Evidence:** Ansys Mechanical's submodeling "takes the results of a broader upstream analysis and applies them as boundary conditions to a smaller downstream model" (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_submodeling.html). FLX D-FLX-26 builds that patch internally for error estimation only.
**Fix:** Add one sentence to FLX "Meshing and adaptivity": "Goal-oriented adaptivity refines where a check needs accuracy, so routine submodeling is unnecessary." Add `std::sim::submodel(global: Field, region:, model:)` reusing D-FLX-26's patch with the transfer error in the budget, phase 2, and a UIX study template for it.

### R20-26 · Minor · Targets: UIX, FLX
**Section:** UIX "Studies and results"; FLX "Scope and architecture"
**Problem:** COMSOL's Application Builder turns an expert's model into "a simulation application with a dedicated user interface" for non-experts, and companies buy it for that. In Crucible, any study wrapped as a `#[feature]` already generates its dialog, docs and agent tool schema and stays checked and versioned, which is a stronger form of the same thing. No tab says so.
**Evidence:** https://www.comsol.com/comsol-multiphysics; contract section 5 `Feature` ("metadata that generates its dialog, docs and agent tool schema").
**Fix:** Add one paragraph to UIX "Studies and results" stating that a study published as a feature is a simulation app, with locked inputs, typed ranges and checks. Add an example in which a sizing feature wraps `static_stress` for a sales engineer.

### R20-27 · Minor · Targets: FLX, UIX
**Section:** FLX "Post-processing and display" (`std::sim::report`)
**Problem:** `std::sim::report` builds report data, but no tab renders it as a document an analyst can send or archive (PDF/A, HTML, DOCX). Ansys Mechanical and COMSOL generate reports, and certification and customer reviews consume documents.
**Evidence:** FLX line 840; no report-document writer in ECO's catalog for simulation reports.
**Fix:** Name the output: report data renders through MEC's drawing and document pipeline to PDF/A-2u and HTML, with figures from Snapshots under a pinned `RenderProfile`, phase 2. Oracle: re-rendering a stored report is byte-identical.

### R20-28 · Minor · Targets: FLX
**Section:** FLX "Electromagnetics", Oracles FLX-O-DISC-8
**Problem:** HFSS users judge an EM solver by its adaptive convergence on S-parameters (a maximum ΔS between passes). FLX's electromagnetic oracle checks accuracy at fixed cases but states no adaptive stopping rule or goal, so an S-parameter's error budget is undefined at `SignOff`.
**Evidence:** FLX D-FLX-32 and FLX-O-DISC-8 ("S-parameters within 0.01 of Palace").
**Fix:** State that each port's S-parameters at declared frequencies are DWR goals of `solve_harmonic`, with a calibrated class `em.sparam` (phase 4), and that adaptivity stops when every goal's bound is below the requested |ΔS|. Extend FLX-O-DISC-8 with coverage of held-out cases at 99%.

### R20-30 · Minor · Targets: FLX, ELX
**Section:** FLX "Networks"; ELX "Co-simulation"
**Problem:** Modelica users wait on model translation for large systems, and Crucible's per-mode compilation cached by Kiln could recompile only the changed part. FLX gives only a run-time target ("2× of IDA") and no compile-time target, so the advantage over Dymola is neither stated nor measured.
**Evidence:** FLX line 876.
**Fix:** Add a target row: "re-translation after a one-parameter or one-element edit of a 50,000-equation Network under 1 s (incremental), full translation within 2× of OpenModelica", with FLX-O-NET-1 measuring it. State the incremental compile in one sentence under D-FLX-27.

### R20-32 · Minor · Targets: FLX, MEC
**Section:** FLX "Shape, parameter and experimental design"
**Problem:** Structural optimizers in OptiStruct and Nastran SOL 200 size shell thicknesses (free-size) and optimize composite ply shapes, counts and stacking under manufacturing rules. Flux offers density topology optimization and shape optimization, but no shell-thickness or ply optimization, which GP10's wing box will need.
**Evidence:** FLX "Topology optimization" table, with density, graded lattice, level set and multiphysics rows only.
**Fix:** Add "Shell sizing and laminate optimization" rows: thickness Fields on mid-surface shells with adjoints (phase 2), and ply-shape, ply-drop and stacking optimization with MEC's ply rules (phase 6, GP10).

### R20-33 · Minor · Targets: UIX, FLX
**Section:** UIX "Field views"
**Problem:** Analysts trust a solve partly by inspecting its discretization. Without a mesh, they will ask where the octree refined, which cells are cut and aggregated, and where shells and beams replaced solids. UIX shows an error overlay but no discretization view.
**Evidence:** UIX "Field views" capability table has no row for the discretization; FLX's `mark_reduction` produces a `Field<Body, ReductionKind>` that is never displayed.
**Fix:** Add a "Discretization" `VisualizationSpec` showing octree cells, cut and aggregated cells, polynomial degree and `ReductionKind` regions, phase 1. A one-line legend states that the model was not meshed by the user.

## Appendix: parity checklist

The checklist below drove the findings. "Covered" means a capability row with a phase exists; the phase is the earliest at which the incumbent workflow works.

| Incumbent capability (source) | Crucible | Phase | Finding |
| --- | --- | --- | --- |
| Linear static, modal, linear buckling of a part (Ansys, Abaqus, Nastran) | Covered (FLX, contract 13.4) | 1 | — |
| Remote points, point masses, springs, bushings, fastener connectors (Ansys, Nastran) | Missing | — | R20-01 |
| 2D, axisymmetric, symmetry, cyclic symmetry (Abaqus, Ansys, COMSOL) | Missing | — | R20-02 |
| Prestressed modal, harmonic, PSD, response spectrum, damping (Ansys, Nastran) | Partial, no owner | 2 to 7 | R20-03 |
| Assembly with bonded and frictionless contact, automatic detection (Abaqus, Ansys) | Fitted only | 2 (fitted), 3 (immersed) | R20-08 |
| Nonlinear materials, large deformation, frictional contact (Abaqus) | Covered | 2 | — |
| Load-case combination and envelopes (Nastran, Ansys) | Missing | — | R20-09 |
| Stress linearization (Ansys) | Missing | — | R20-10 |
| Submodeling (Ansys) | Internal only | — | R20-21 |
| Solver-deck exchange that runs (Nastran, Abaqus, LS-DYNA) | Read and write without execution | 3 | R20-06 |
| Topology and lattice optimization (Ansys, nTop) | Covered; stronger | 1 | — |
| Fatigue, gear and bearing ratings (nCode, KISSsoft) | Covered | 1 to 2 | — |
| Explicit drop and crash (LS-DYNA) | Covered | 3, 5 | — |
| Laminar and natural-convection CFD, conjugate heat transfer (Fluent) | Covered | 3 | — |
| RANS, LES, multiphase (Fluent, STAR-CCM+) | Covered | 4, 5 | — |
| Rotating frames, mixing plane, sliding mesh, fan models (Fluent) | Missing | — | R20-11 |
| Flow adjoint (STAR-CCM+, Fluent) | Unspecified | — | R20-12 |
| GPU CFD throughput (Fluent) | No target | — | R20-07 |
| Full-wave FEM with wave ports and fast sweep (HFSS) | Covered | 4 | — |
| Floquet ports and array domain decomposition (HFSS) | Missing | — | R20-13 |
| 3D partial-inductance RLC extraction (Q3D) | Unspecified | — | R20-14 |
| Weak-form equation modelling (COMSOL) | Covered; typed and differentiable | 0 to 1 | R20-05 |
| Simulation apps (COMSOL Application Builder) | Covered by features; unstated | 1 | R20-26 |
| Charged-particle tracing, molecular flow (COMSOL) | Missing, no limit record | — | R20-20 |
| AI field surrogates (SimAI, Luminary) | Bounded; late | 4 | R20-19 |
| Acausal multi-domain system models (Dymola) | Covered as `Network` | 2 | — |
| Modelica source and MSL (Dymola) | FMU only | 3 (FMU) | R20-15 |
| Hydraulic, pneumatic, thermofluid libraries (Amesim) | Missing | — | R20-16 |
| Schematic, ERC, layout, DRC, routing (Altium, KiCad) | Covered | 3 | — |
| Multi-board systems (Altium) | Covered by construction; unstated | 3 | R20-24 |
| Vendor SPICE models locally (LTspice, PSpice) | Remote External Op only | 3 | R20-17 |
| Ideal-switch converter simulation (PLECS) | Missing | — | R20-25 |
| Allegro and PADS migration (KiCad 10) | Not named | 3 | R20-23 |
| Code-first and AI PCB design (JITX, tscircuit, flux.ai) | Covered; differences unstated | 3 | R20-18 |

### R21-01 · Critical · Targets: OVERVIEW, CONTRACT, ING, FLX, COV, KLN
**Section:** Overview "Guarantees across every tab"; contract sections 2, 5 and 7.1; ING "Tolerances, approximations and truth"; FLX "Error budgets, goals and checks"; COV "Coverage model"
**Problem:** Crucible's headline claim is that every result states its error and evidence, yet a reader meets eleven separate qualifiers on one number: fidelity, `ResultStatus`, bound kind, `ErrorBudget` parts, validity zone, model level, evidence level, solution-verification status, platform class with determinism grade, verdict with `conditional_on`, and the gate predicate with policy allowances and Waivers. They are defined in four tabs and three contract sections, each in terms of the others, and no page shows them working together. A careful engineer cannot answer the first question they will ask: "does the bracket pass, and how sure are we?"
**Evidence:** The Overview's "Fidelity, errors and checks" compresses six of the axes into five paragraphs with no example ("calibrated parts combine by a union bound, so a total carries confidence 1 − Σαᵢ"). Solution-verification status (`Estimator`, `Gci`, `None`) appears only in COV D-COV-21; η99 appears in COV and MEC without definition and is defined only in FLX D-FLX-24. The best partial treatment, ING's `static_margin` outcome table, sits at line 900 of a language tab and omits zone, evidence level and platform class.
**Fix:** Add one Overview section, "How far to trust a number", right after the canonical example, and make every tab cite it instead of re-explaining. Its core is this table:

| Qualifier | Question it answers | Values | Owner |
| --- | --- | --- | --- |
| Fidelity | How hard did we try? | `Preview`, `Interactive`, `SignOff` | KLN |
| Result status | Is the value here and current? | `Pending`, `Proxy`, `Ready(Fidelity)`, `Stale`, `Failed`, `Aborted` | `base` |
| Error budget | Which errors were counted, and which were not? | One part per error source, each quantified or `NotQuantified` | `base`, FLX |
| Bound kind | How sure is each error bar? | `Guaranteed`, `Estimated { calibration }`, `Indicator` | `base`, FLX |
| Validity zone | Is the model inside the range where it was checked? | `Calibrated`, `Extrapolated`, `Invalid`, `Unassessed` | COV |
| Model level | What form of physics produced it? | L0 analytic to L3 full 3D | COV |
| Credibility level (today "evidence level") | How well has this model been tested against reality? | E0 declared to E4 context-qualified | COV |
| Solution verification | Was this particular solve checked for convergence? | `Estimator`, `Gci`, `None` | COV, FLX |
| Platform class | Where would the same bits come out again? | Canonical class, `CpuIsa`, `Gpu`, `Unverified` | PLT |
| Verdict | What does the check conclude? | `Pass { conditional_on }`, `Fail`, `Undecided { reason }`, `Error`, `Skipped` | ING |
| Gate | May it merge or release? | Severity below `Error`, a covered non-provisional `Pass`, or a Waiver | ING, KLN |

Follow it with the bracket traced through every row in about 250 words, reusing ING's numbers: at `Interactive` the regularized peak is 112 MPa ± 20 MPa `Estimated` against a limit of 144 MPa to 165.6 MPa (0.6 × the 240 MPa to 276 MPa yield enclosure), status `Ready(Interactive)`, model form `NotQuantified`, so the verdict is a provisional `Pass { conditional_on: [model form] }`; at `SignOff` the value is 118 MPa ± 1.5 MPa, confirmed by one refinement, in the canonical class, zone `Calibrated`, confidence 0.99; after GP1's strain-gauged proof loads lift immersed elasticity to E3 for this response-quantity class, the model-form part becomes `Estimated` and the `Pass` meets the gate with no allowance. Then trim the Overview's "Fidelity, errors and checks" to a pointer, and give contract section 2 one row, "Trust qualifiers: see Overview".

### R21-02 · Major · Targets: ING, FLX, COV, KLN, MFG, ELX, AGT, UIX, PLT, MEC, ANV, ECO, CONTRACT
**Section:** Every design section's decisions; "Open questions"; "Contract change requests"; contract lead
**Problem:** The tabs read as the minutes of their own revision. Review finding ids appear as evidence inside running prose, decisions end in "(revised in round N)", "Rejected" clauses name "the round 2 rule", and "Open questions" sections list declined findings rather than open questions. A reader who was not in the review cannot use any of it, and the Adversarial review tab already owns this history.
**Evidence:** Counted before each tab's "Open questions": finding ids such as "(R3-37, R9-40)" appear 112 times in PLT, 62 in FLX, 56 in MFG and AGT, 48 in ELX, 45 in UIX, 43 in KLN, 34 in COV and 26 in ING (482 in all), while ANV, MEC and ECO show that a tab reads well without any. "(revised in round N)" appears 235 times across twelve tabs. Examples: D-ING-7 "*Rejected:* … `Pending` and `ING6401` as node values, the round 2 rule. (revised in round 3)"; D-MEC-26 "*Why:* … the round 1 drafts claimed the formboard twice"; D-FLX-1 "*Rejected:* the round 1 seven-crate split"; MEC "It replaces `crucible:model`"; KLN "`crucible:product`, formerly `crucible:model`". ING's "Open questions" opens "This revision decides all nine round 2 questions" and then lists ten bullets of declined findings; MEC's question 2 and AGT's question 2 are titled "Findings declined…". The contract's lead is a version history.
**Fix:** One mechanical pass, then a rule. (1) Delete every finding id from text above "Open questions"; where the id stood in for a reason, write the reason ("a policy-clamped limit made two organizations cache different results for one key" stays, "(R3-12)" goes). (2) Delete every "(revised in round N)"; the Decisions log and `git log` keep revision history. (3) Delete "the round N rule", "formerly", "replaces" and similar history from decisions and names; a rejected alternative is described by what it is. (4) "Open questions" holds only unresolved questions; move every "Findings declined or applied in part" list to the Adversarial review tab under that tab's code. (5) "Contract change requests" holds only open requests or "None"; accepted ones are recorded in the contract's ruling log. (6) The contract's lead is one sentence: "Binding for every design agent and reviewer; where a tab disagrees with it, the contract wins." Add to `check.py` a rule that fails on `\bR\d{1,2}-\d{2}\b`, "revised in round" and "round \d" outside the Adversarial review and Decisions log tabs.

### R21-04 · Major · Targets: ANV, FLX, KLN, PLT
**Section:** ANV "Kernel structure and operation contract"; FLX "Scope and architecture"; KLN "Scope and the operation contract"; PLT "Scope, crates and the platform layer"
**Problem:** Four core tabs open with build infrastructure: crate tables with dependency lists, crate-layout decisions, operation registries, behavior-version freezing, `OpImpl` signatures and WIT package names. The reader learns which crate depends on `simd` before learning what a Body is, what a Field is or what Kiln does for an edit. The ideas these tabs are proud of (certified decisions, stable names, error-bounded Fields, minimal rebuilds) start in section two or three.
**Evidence:** ANV's first decision, D-ANV-1, is about six crates and `forbid(unsafe_code)`; its first section continues with closure hashes and `Current`, `Deprecated`, `Retired` statuses. FLX's first section is a crate table, D-FLX-1 on crate splits, and an 11-row table naming about 80 operations, before "Fields". KLN's first code block is the `OpImpl` trait, followed by D-KLN-2 and D-KLN-4 on closure hashes and retired versions. PLT's first sentence cites two finding ids and its first table lists crates and `unsafe` permissions.
**Fix:** In each tab, move crates, crate decisions, WIT packages, operation registries and version freezing into the closing `## Reference` section (R21-03), and open with the domain:
- ANV: open with "Bodies, identities and encoding" retitled "One Body, four representations", starting from the bracket's `fillet(body.edges(new), 2mm)`: what the Body is, why the edge keeps its name when `width` changes, and what happens at a near-tangency. "Kernel rules" follows as a summary list.
- FLX: open with "Fields" and a short tour: `static_stress` on the bracket returns a `Field<Part, Stress>`; `.max(over:)` returns an `Approx<Stress>`; here is its budget. The operation catalog moves to Reference.
- KLN: open with "Kiln: graph, keys and memoization", leading with the story of one edit: changing `width` re-runs the bracket feature, reuses the cached clamp face resolution, and backdates the unchanged IIR.
- PLT: open with "Numerical determinism" ("the same bracket gives the same bits on a laptop, in Safari and on the build farm; here is what that takes"), then the platform layer.

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

### R21-13 · Major · Targets: PLT, FLX, MFG, AGT
**Section:** PLT "Targets" and "The browser target"; body prose of the tabs with finding ids
**Problem:** Some quotations from primary sources are attributed to review finding ids instead of the page that was opened, so the reader cannot follow the citation and the research rule ("cite only pages you opened") is met only in the Sources list. The finding id is not a source; it is the reason the sentence was added.
**Evidence:** PLT: "Wasmtime rates Windows ARM64 Tier 3, lacking 'CI testing, full-time maintainer', and aarch64 macOS and Linux Tier 2, lacking 'Continuous fuzzing' (R6-12)." PLT D-PLT-33: "Pulley carries 'a ~10x order-of-magnitude slowdown' (R6-13)". PLT's Sources do list the pages ("67. Wasmtime stability tiers. https://docs.wasmtime.dev/stability-tiers.html"; "68. Pulley, Wasmtime documentation"), but the prose never points to them.
**Fix:** Replace each finding id that follows a quotation or a sourced fact with the source key (R21-12): "(R6-12)" becomes "[Wasmtime stability tiers]", "(R6-13)" becomes "[Wasmtime Pulley]". Do this as part of R21-02's pass: where an id follows a quote, swap it for the source; elsewhere, delete it.

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

### R21-16 · Major · Targets: FLX
**Section:** "The weak-form language"
**Problem:** Flux's input language is weak forms in Ingot, yet the tab never shows a complete one. The section lists spaces, measures and operators in tables, and the only full form in the spec is the contract's three-line elasticity fragment. A simulation engineer cannot see how a problem is posed, solved, given a goal and checked end to end, which is the first thing they would try.
**Evidence:** FLX has three plain code blocks in about 18,000 words (ING has nineteen, MEC sixteen). "The weak-form language" consists of a spaces table, a measures paragraph, a problem-kinds table, a checks table and two decisions; the problem-kinds table gives forms only as fragments (`a == L`; `dt(u)`; `continue_in(load, to: 2kN)`).
**Fix:** Open the section with a complete, short example, with the syntax for prescribed values fixed by FLX:

```
use std::sim::{trial, test, dx, ds, solve}

/// Steady conduction: 5 W into the web's end cap, the clamp held at 40 degC.
pub feature bracket_thermal(p: Part, clamp: Query<Face>, pad: Query<Face>) -> Part {
    let t = trial(Temperature, p)
    let v = test(t)
    let k = p.material.conductivity(at: 20degC)
    let q = 5W / pad.area()
    let heat = inner(k * grad(t), grad(v)) * dx(p) == q * v * ds(pad)
    let result = solve(heat, fixed: [(clamp, 40degC)], goals: [t.mean(over: pad)])
    p.require(result.t.mean(over: pad) < 85degC, name: "pad_temperature")
}
```

Follow it with four sentences: the compiler checks that every term of `heat` has one dimension; `solve` picks a plan per region; the goal makes the adaptive loop refine for the pad's mean temperature; and because a regional mean is a bounded linear functional, its bound may be `Guaranteed` (contract 5), unlike the bracket's stress peak. Then add a five-line time-dependent variant using `dt(t)`.

### R21-24 · Minor · Targets: ING, AGT, FLX, MEC, ANV, KLN
**Section:** "Oracles"
**Problem:** Oracle ids follow different schemes: flat numbers (ING-O-1 to ING-O-38, AGT-O-1 to AGT-O-24) and area-prefixed ids (MEC-O-PF-1, ANV-O-VER-1, KLN-O-FPRINT-1, FLX-O-OPT-1). A flat id says nothing about what it verifies, so a capability row citing "ING-O-8" or "AGT-O-17" sends the reader to the Oracles table every time.
**Evidence:** ING capability rows cite "ING-O-1, ING-O-13, ING-O-27"; MEC rows cite "MEC-O-TL-6", whose area (tolerancing) is readable in place.
**Fix:** Adopt `<TAB>-O-<AREA>-<n>` in ING and AGT now, while `oracles/` holds no executable oracles and renaming costs one search-and-replace across tabs.

### R21-26 · Minor · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, CONTRACT
**Section:** Capability tables at the end of each design section
**Problem:** Capability tables are the build contract, but in reading order they arrive as a dense block after every section, and many cells add nothing: "Failure: —" and "Not expressible" stand where the reader expects a typed failure. The published doc gives them the same weight as explanation.
**Evidence:** ING "Purity | … | Not expressible"; MEC "Typed failures and fixes | `FeatureError { kind, why, fix, at }` | —"; AGT "Priority classes | … | — ".
**Fix:** Replace "—" with "None: cannot fail" or the actual failure, and "Not expressible" with "None: the language cannot express a violation". In the published doc, render capability tables as a visually distinct, collapsible "Build contract" block under each section, so a reader can follow the prose without the tables breaking it.

## Claims the reviewers verified

Drop the `[unverified]` marker on these and cite the URL in Sources.

None in this review.

## Unverified claims in your tab

Verify each with WebFetch on a primary source and drop the marker, correct it, or cut the claim if nothing supports it. Line numbers are at tag `round-3`.

None.

## Your open questions

Close each: decide it (the reviewers propose answers above), move it to a contract change request, or keep it with the reason it cannot be decided yet.

1. **Guaranteed bounds on cut cells.** Equilibrated proofs on hanging nodes and cut cells are research that contract section 13.2 defers past phase 1; cut-cell totals stay `Estimated` until then.
2. **Findings declined or applied in part.**
    - R7-02, part 3, the near-maximal-set rule, and R7-08's "Needs" column: declined in contract section 17.
    - R7-16: phase 1 has four classes, not five, because one treatment serves both fidelities (R7-17) and inherent strain moved to phase 2.
    - R7-25: sheet lattices land in phase 2, because GP2 uses strut lattices.
    - R7-05: `Guaranteed` eigenvalue lower bounds are admitted by contract section 5 (CCR-FLX-11).
    - R7-27: the staffing alternative is moot under contract section 13.2; the scope cuts apply.
    - R7-06, R7-12, R7-20, R7-22, R9-29, R12-19: FLX's parts are applied, and COV, MFG, PLT and ELX own the rest.
    - R9-50: no FLX change; ING owns those questions.
    - Round 2: routine `SignOff` in `CpuIsa` (R1-43) is declined, because contract section 7.3 requires canonical recomputation.
    - Round 2: GPU element-cycle targets apply at `Interactive` only (R1-21), and morphing reduced models arrive in phase 3 (R1-16).

## Known items

- Read `docs/revision/digest.md`: adopt the permissive libraries that serve your tab, name copyleft tools only as oracles, and use the clean-room insight protocol of contract 7.7 for incumbent behaviour.
- Add one sentence under each drawn diagram that tells the reader how to read it (`diagrams/03-flux-pipeline.jsx`, `diagrams/03-flux-per-region-discretization.jsx`).
