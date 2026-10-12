# R13 physics review

Summary: (1) The canonical check now passes the bracket while its governing stress goes unchecked. `away_from([clamp, …], 2 * thickness)` measures 8 mm from the whole clamped bottom face, so it removes the rib-root fillet where the bending stress peaks. Under a lateral 1.2 kN load the root fails the 0.6·yield limit, but the remaining band passes (R13-01).
(2) No phase 1 release can meet the gate honestly. MEC and KLN say GP1's and GP2's proof loads supply model form, but those loads run on articles made from that same release, after it. Strain gauges also cannot measure the regularized fillet-peak class the checks decide on (R13-02).
(3) Goal checks have no goal-norm algebraic part, and the "Guaranteed" linear-goal bound leaves out the residual term that inexact solves create. Separately, phase prerequisites break outside 13.4 (rotordynamics, acoustics, weld phase transformation, allowables), and the spec checker that contract 13.4 says enforces them has no such rule (R13-03, R13-04).

### R13-01 · Critical · Targets: CONTRACT, ING, FLX
**Section:** Contract 6 (canonical example and its paragraph); ING "Canonical example" (ING-O-31); FLX "Regularized goals and singular points" (D-FLX-39)
**Problem:** The round 3 fix for R7-02 opened a new hole: the canonical check leaves out the region it most needs to judge. `clamp` is the base's `start_cap`, the whole bottom face at z = 0 (ANV's worked example puts the end cap at z = 4 mm). `away_from([clamp, …], 2 * thickness)` therefore removes everything below z = 8 mm, which takes in the rib root and its 2 mm fillet (z = 4 to 6 mm), where the rib's bending stress and the fillet concentration peak. FLX's own rule would exclude only the flagged *edges* (the clamp perimeter) by max(2ρ, t) = 4 mm, and that keeps the fillet, which lies about 5.7 mm from the perimeter edge. The load's direction is also never stated, so it is unclear what is being checked.
**Evidence:** Take a lateral 1.2 kN on the 20 mm rib (60 mm wide, 4 mm thick). The section modulus is 60·4²/6 = 160 mm³. The root moment of 1.2 kN × 20 mm gives 150 MPa nominal, about 210 MPa with a fillet Kt of about 1.4. In the band that remains (z = 8 to 16 mm) the stress is at most 1.2 kN × 16 mm / 160 mm³ = 120 MPa. The limit is 0.6 × 241 MPa = 145 MPa at the 6061-T6 specification yield that D-COV-13's default basis selects. So the check returns `Pass` on a bracket whose root fails, and ING-O-31 requires exactly this outcome ("its check decides at `SignOff`").
**Fix:** Write the check as `study.von_mises.max(over: p.regular())`. `regular()` is the Body minus each flagged set's default neighbourhood, taken from `flux::singular_sets` for this study, and never a whole face. State the load as a vector, for example `force: 1.2kN * dir(-x)`. Add a rule to D-FLX-39 and contract 7.1: when the maximizer of a regularized maximum lies on the boundary of an excluded neighbourhood, the result is `Undecided { reason: MaximumAtExclusion }` with the fix "model the support". Extend ING-O-31: the check region contains the rib-root fillet, and with a lateral load the canonical bracket `Fail`s at 4 mm and passes at 6 mm.

### R13-02 · Critical · Targets: CONTRACT, MEC, COV, KLN
**Section:** Contract 13.1 (validation paragraph), 13.2 (milestones 6 and 7); MEC "Design checks" (paragraph after D-MEC-30); KLN policy allowances; COV "Evidence levels" (D-COV-3)
**Problem:** MEC says "Phase 1 releases therefore need no allowance for those quantities", and KLN says the proof loads "supply their checks' model form". But the release comes first (milestone 6, run build tagged), the articles are made from it, and only then are they gauged (milestone 7). At release time the models are E2 at best, so every stress check is `Pass { conditional_on: [ModelForm] }`. D-COV-24 accepts only action-effect allowances that cover FE analysis, and no design code supplies one for a machined 6061 bracket or a printed lattice. That leaves a founder Waiver as the only route. Using the same article both to judge the design and to validate the model also breaks the held-out rule in 13.1. Finally, a strain gauge averages surface strain over a 1 to 6 mm grid. It cannot measure the class "regularized peak at a fillet" over ρ = 0.2 mm, so the gauged class never covers what the check decides on.
**Evidence:** MEC: "GP1's and GP2's strain-gauged proof loads validate immersed elasticity and the beam-lattice model to E3 … Phase 1 releases therefore need no allowance". Contract 5: a model-form bound applies "only when the validation plan lists that functional's response-quantity class (quantity, location type, regime)". Contract 13.2 milestones 6 and 7 put release before the physical runs.
**Fix:** Add a phase 1 validation campaign before milestone 6. Run it on separate validation specimens of the same alloy and process: notched and filleted plates, plus printed strut and lattice coupons. Measure surface strain with gauges and stereo DIC at the fillet roots, the DIC sampled at the regularization radius, with three or more replicates. Its response classes are "regularized surface peak at fillets, linear elastic" and "localized strut stress". Those E3 bounds then govern the GP1 and GP2 releases, and the GP proof loads become held-out confirmation. Delete MEC's and KLN's "need no allowance" sentences. Give the checks' predicted values in the gauge functional (a bounded linear functional with a `Guaranteed`-capable bound), so proof-load agreement is judged like for like.

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

### R13-07 · Major · Targets: COV, MFG, CONTRACT
**Section:** COV "Material databases and licensing" capability table (the Allowables row, phase 3); "Statistical basis" (phase 1); 13.4 as-built strut calibration (phase 1)
**Problem:** GP2's strut-scale Materials have no specification limit, so D-COV-13 falls back to B-basis, and computing B-basis values is a phase 3 capability. Every phase 1 GP2 strength read therefore fails with `MissingBasis`, or quietly uses typical values. MFG's bureau coupon plan also fixes no replicate count large enough for a one-sided tolerance limit.
**Evidence:** COV capability rows: "Allowables | Replicates to A- and B-basis values | `InsufficientSamples { needed }` | COV-O-MAT-4 | 3", and "Statistical basis | … | 1".
**Fix:** Move the normal and Weibull one-sided tolerance limits of CMH-17 and MMPDS to phase 1. These are closed-form k-factors on a coupon set, and COV-O-MAT-4's worked examples serve as the oracle. Keep the non-parametric and ANOVA (pooled-batch) methods in phase 3. MFG's as-built strut calibration then states a replicate count per diameter and angle large enough for a B-basis value (the CMH-17 minimum).

### R13-08 · Major · Targets: FLX, COV, MEC, CONTRACT
**Section:** FLX "Calibrated estimates" (D-FLX-40), FLX-O-ERR-3 and FLX-O-ERR-5; contract 13.2 build program, item 3
**Problem:** The η99 calibration that every phase 1 `SignOff` check relies on has no independent reference. References are "solves two degrees higher" in the same aggregated CutFEM code. They share its cut quadrature, Nitsche penalty, aggregation and geometry handling, so a bias common to the family never shows. They "count only when their own error is below 10% of the bound", but that error can only be measured by the estimator family being calibrated. That is circular. Fitted FEM arrives only in phase 2.
**Evidence:** D-FLX-40: "References are solves two degrees higher, or full-resolution solids for lattices, and count only when their own error is below 10% of the bound." Contract 13.2: corpora "must agree with an independent source (… MFEM or libCEED …)".
**Fix:** Take phase 1 references from an independent code on fitted, curved high-order meshes, used as an oracle only: MFEM (BSD) or deal.II (LGPL, allowed as an oracle). Accept a reference only when a p-sequence (p, p + 1, p + 2) in that code shows exponential convergence and its Richardson spread is below 10% of the bound. Record each reference's code and mesh hash in the corpus. Keep same-code p + 2 solves only as a cross-check.

### R13-09 · Major · Targets: COV, CONTRACT
**Section:** COV "Error budgets and model form" (D-COV-20); contract 5 `ErrorBudget` (union bound), 13.1 (V&V 20 metric)
**Problem:** The model-form part is "|E| + k·u_val … `Estimated` with coverage factor k", but nothing fixes k or the exceedance level α. The contract's union bound needs α. With the contract's minimum of three replicates, u_D has two degrees of freedom. A normal k = 2 then covers far less than 95%; V&V 20 uses an effective-degrees-of-freedom t factor. Converting an η99 bound to a standard uncertainty by B/z₁₋α/₂ treats a one-sided 99th-percentile factor as two-sided.
**Evidence:** D-COV-20: "Flux's bound B enters u_val as B/√3 when `Guaranteed` and B/z₁₋α/₂ when `Estimated` at level α." No passage in COV, MEC or contract 13.1 states k or the model-form α.
**Fix:** Fix α_mf = 0.05 and k = t_{1−α_mf/2, ν_eff}, with ν_eff from Welch–Satterthwaite over u_num, u_input and u_D. Record both in the part's `Estimated { calibration: VV20 { k, ν_eff, α } }`. Convert one-sided η99 bounds with z₁₋α. Extend COV-O-VAL-2 with three-replicate synthetic cases that check the stated coverage.

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

### R13-32 · Minor · Targets: COV
**Section:** COV "Solid mechanics" (linear elasticity envelope); the example `PhysicsModel` in "Adding new physics"
**Problem:** The calibrated envelope "strain ≤ 0.5%" exceeds the proportional strain of the golden alloys (6061-T6 at about 241 MPa / 69 GPa ≈ 0.35%), so it duplicates "below the proportional limit" and contradicts it. The example model then refuses only above 2% strain, well into plasticity.
**Evidence:** "Strain ≤ 0.5% calibrated, ≤ 2% extrapolated; below the proportional limit" and `bound(equivalent_strain, max) { calibrated: 0.0..=0.005, extrapolated: 0.0..=0.02, outside: refuse … }`.
**Fix:** Replace the strain bound with the regime variable σ_eq / σ_proportional(T) of the assigned Material: calibrated ≤ 0.9, extrapolated ≤ 1.0, `Refuse` above, escalating to plasticity. Keep the rotation bound for kinematics.

### R13-33 · Minor · Targets: COV
**Section:** COV "Extrapolated" row of "Policy by zone"
**Problem:** In an Extrapolated zone the model-form part is already quantified and inflated by g(d), yet a release gate still requires a Waiver. Either the inflation is trustworthy and the quantified budget decides, or it is not and should be `NotQuantified`. Requiring both adds a second, human mechanism for one fact.
**Evidence:** The policy table: "Extrapolated | … | Checks use the inflated part and name the zone | A Waiver (contract 2)".
**Fix:** Let quantified Extrapolated results meet the gate through the inflated budget. Require a Waiver only where d exceeds a declared d_max per package, beyond which g(d) is not fitted and the part is `NotQuantified { reason: BeyondInflationFit }`.

### R13-34 · Minor · Targets: FLX, COV
**Section:** FLX and COV, every decision *Why* and *Rejected* clause; both tabs' "Open questions"
**Problem:** Rationales cite review findings by id ("(R7-15)", "(R1-07, R7-01)", "(R7-35)") dozens of times, so a reader must open another document to follow an argument that one clause could state. FLX's and COV's Open questions are mostly ledgers of "findings applied in part", not open questions. That record belongs in the Adversarial review tab, and readers of these tabs lose the real open items among them.
**Evidence:** FLX Open questions item 2 has nine bullets of finding ids; COV item 4 has nine.
**Fix:** Drop finding ids from *Why* clauses and say the reason in words; the Decisions log and the Adversarial review tab keep the mapping. Move the "applied in part" ledgers to the Adversarial review tab, leaving only genuine open questions here (FLX 1; COV 1 to 3).

### R13-35 · Minor · Targets: COV
**Section:** COV lead and "Coverage model" (D-COV-21, the paragraph after D-COV-4)
**Problem:** COV uses η99, DWR, "calibration class", "regularized peak" and "refinement confirmation" before defining them; each is defined only in FLX. An engineer reading COV first meets "an η99 bound" in D-COV-21 with no explanation.
**Evidence:** D-COV-21: "an uncalibrated band means something different from an η99 bound". Neither η99 nor DWR is defined anywhere in COV.
**Fix:** Add one short paragraph before "Evidence levels": "Flux reports each estimated bound already multiplied by its class's η99, the 99th-percentile ratio of true to estimated error over a held-out corpus; a result outside the class's envelope is only an indicator (FLX)." Spell out DWR on first use.
