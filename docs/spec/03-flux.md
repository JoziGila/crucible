# Flux physics engine (FLX)

Flux is Crucible's simulation engine: physics is posed as weak forms (the integral equations that finite elements solve) written in Ingot, or called as ready-made studies such as `static_stress`, and every result is a Field (a physical quantity over the part) that carries a stated bound on its error. Where Ansys, Abaqus and COMSOL leave meshing, defeaturing and convergence to the analyst, Flux solves on the exact design geometry, recomputes only what an edit touches, and names each error source and how sure each bound is, with identical results on every platform. It does this by choosing a discretization per region (shells for thin walls, beams for struts, an immersed grid for solids) and by estimating the error of exactly the quantity each check reads, so a check decides only when the bound supports it.

## A first study on the bracket

This section follows one simulation from source to verdict, so that the rest of the tab has a picture to build on. The canonical bracket of [contract section 6](../contract.md) ends with three lines of physics:

```
let study = static_stress(p, fixed: clamp, force: load * dir(-y), on: tip)
let stress = study.von_mises.max(over: study.regular())
p.require(stress < 0.6 * p.material.yield_strength(at: 20degC), name: "static_margin")
```

### What the study does

`static_stress` is an ordinary Ingot feature in `std::sim::quick`. It writes the weak form of linear elasticity on the Part, attaches the clamp and the 1.2 kN load along −y on the web's end cap, and calls `solve`. Nothing in it is privileged: an engineer can open it, copy it and change it, and a fork gets the same kernels, derivatives and estimators (principle 1).

`solve` first asks `flux::plan` for a `SolvePlan`, the resolved list of every numerical choice. For the bracket the plan is simple. Neither the 6 mm plate nor the 6 mm web is slender enough for a shell, so the whole Part is a solid on an immersed octree. That is a grid of cubes laid over the true B-rep (boundary representation) geometry, with each cube the surface cuts integrated exactly on the cut. Nobody meshes or suppresses a feature, and the plan is pinned and printed by `plan.explain()`.

The solve returns a record of Fields, such as `study.von_mises`, a `Field<Part, Stress>` keyed by the Part's geometry identity.

### Why the check reads `study.regular()`

The exact stress in this model is infinite at two places: along the edges of the clamped face, where a rigid support meets free material, and along the edges of the loaded patch. Those infinities belong to the model, not to the part, so a raw maximum would grow without limit as the solver refines.

Flux flags such places as singular sets and gives each a default neighbourhood. `study.regular()` is the Part minus those neighbourhoods. For the bracket it removes a band of one wall thickness, 6 mm, around the clamp's edges and around the end cap's edges. It keeps the web root and its 2 mm fillet, about 8 mm from the nearest clamp edge, which is where the bending stress peaks.

The maximum itself is regularized: Flux maximizes a local average over a small radius ρ, and adds the gap to the raw maximum of the computed Field to the budget. If the regularized maximum lands on the boundary of an excluded neighbourhood, the check returns `Undecided { MaximumAtExclusion }` with the fix "model the support", because the answer then depends on what the model left out.

### The answer and its budget

`stress` is an `Approx<Stress>`: a value with an `ErrorBudget`, one part per error source, each in its own norm and with its own kind (contract section 5.1). An illustrative `SignOff` budget for the bracket looks like this:

| Error source | Illustrative size | How Flux obtained it | Kind |
| --- | --- | --- | --- |
| Discretization | ± 1.5 MPa | Dual-weighted residual estimate for this peak, times its class factor, confirmed by one refinement | `Estimated { Class elasticity.peak }` |
| Algebraic | ± 0.02 MPa | Residual of the iterative solve, weighted by the adjoint | `Estimated` in the same class |
| Regularization | ± 0.3 MPa | Enclosed gap to the raw maximum of the computed Field | `Guaranteed` |
| Floating point | below 10⁻⁹ MPa | Rounding bound of the canonical evaluation | `Guaranteed` |
| Input and tolerance | ± 0.4 MPa | Poisson's ratio enclosure propagated by the adjoint | `Estimated { Statistical }` |
| Model form | not counted | Linear elasticity has not been validated for this response yet | `NotQuantified` |

A dual-weighted residual (DWR) estimate is an error estimate for one goal quantity, computed by solving an adjoint problem whose source is that goal. The class factor comes from a calibration corpus: Flux multiplies the raw estimate by the 99th-percentile underestimate it measured on hundreds of held-out cases, and labels the bound with that class.

ING's decision rule reads this budget against the limit, 0.6 times the specification yield. The value sits far below the limit, but the model-form part is not counted, so the verdict is `Undecided { reason: Unquantified([ModelForm]) }`. It becomes `Pass` when a pinned policy allowance quantifies model form for this check kind. It also becomes `Pass` once the phase 1 validation campaign of [contract section 13.1](../contract.md) has measured strain at fillets and turned model form into an `Estimated` part. The report then states the confidence: at least 1 − Σα, at 95% confidence, for the α of each calibrated part.

### What happens while the engineer works

At `Interactive` fidelity the same study runs in about a second on the reference laptop, at polynomial degree 2 with one adaptive pass and a cheaper estimate. The verdict is provisional until `SignOff` recomputes it with hp-adaptivity and a confirming refinement. At `Preview` a coarse or reduced solve paints a picture but never decides.

When the engineer drags `width` from 60 mm to 80 mm, Kiln re-runs only the nodes downstream of that literal: the octree reclassifies the cells the new faces cut, and the solve warm-starts. During the drag, results show as `Proxy` where the change is affine on them, otherwise `Stale`.

What the engineer gains over an incumbent is visible here. There is no mesh to build or repair, no submodel to set up around the fillet, and no convergence study to run by hand. The number on screen says which errors were counted and which were not, and the same Change gives the same bits on a laptop, in a browser and on the build farm. A study wrapped as a feature is also a simulation app: its parameters generate a dialog, its checks travel with it, and an agent can call it with the same schema.

### Fields

Every physical quantity in Crucible is a `Field<D, V>`, a value type `V` over a domain `D` ([contract section 5.6](../contract.md)). Domains are entities, parameters such as `Time`, or indices such as `Mode` and `LoadCase`, combined as tuples. Each value type declares how it transforms under a rigid motion, so placing an Instance needs no user code.

**Decision D-FLX-2:** Time series, sweeps, mode sets, load cases, ensembles and parametric results are Fields over product domains such as `Field<(Body, Time), Temperature>`, and slicing and reductions return Fields.
*Why:* libraries then exchange only Bodies, Fields and plain values, so one function signature serves every analysis type (principle 3).
*Rejected:* separate container types per analysis; a third type parameter for extra axes, which product domains express without a new concept.

Canonical storage is SI `f64`; `f32` copies exist only on GPUs and for display. A Field's domain is the Body's `GeometryId` plus canonical entity numbers, reached through handles and never through a name or an `EntityId`, so values survive renaming. A Field used on other geometry fails with `DomainMismatch`, whose fix is `field_transfer`.

Fields come in eight representations, from `Analytic` kernel-IR expressions to trained `Surrogate` models, each with its own sampling error; [Reference](#field-representations-and-operations) lists them.

**Decision D-FLX-3:** The representations are `Discrete` for any finite element coefficients, `PerEntity` for one value per entity, and `PointCloud`, `Reduced` and `Surrogate` for particle, reduced and learned results, beside `Analytic`, `QuadraturePoint` and `SparseGrid`.
*Why:* plain nodal values cannot hold Nédélec, discontinuous or NURBS coefficients, and particle, reduced and learned results must reach checks through the same type.
*Rejected:* separate result types per method; nodal values and per-face constants as the only stored forms.

`Sampler::sample` takes Part, surface, reference-cell or parameter coordinates and a requested accuracy, and returns values with a pointwise budget and, where known, a gradient bound. Point location uses Anvil's certified classification; outside the domain it fails with `OutsideDomain { distance }`.

Arithmetic on Fields stays lazy and propagates error in one norm; reductions, traces, projections, transfers and region extraction each add their own part to the budget, as the operations table in [Reference](#field-representations-and-operations) states.

### Fields that drive geometry

Anvil samples Fields (sizing, metric, displacement, thickness, radius, density, orientation) at a required accuracy and adds the sampled error to the Body's bounds. `anvil::implicit_from_field` needs a continuous Field with a gradient bound, which topology optimization supplies as `geometry_density`. A Field that misses the accuracy fails with `InsufficientAccuracy { achieved, required, producer }`.

**Decision D-FLX-5:** A consumer never changes its producer: adaptivity goals are explicit study inputs (`goals: [...]`), and a reduction that a check reads is estimated by a separate `flux::estimate_goal` node over the frozen solution, which never re-solves.
*Why:* adding a check must never change a design or the result another check reads.
*Rejected:* deriving goals from the checks that read a result, which reverses the dependency graph; refinement on demand from a consumer.

A check that cannot decide returns `Undecided { needed }` with an edit that adds its functional to the study's goals.

A stored Field is a header plus 1 MiB chunks, byte-shuffled, zstd-compressed and hashed over canonical little-endian `f64` bytes. Storing −0.0 as +0.0 makes a value reloaded from the CAS equal to the value in memory.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Quick studies | `std::sim::quick` features (`static_stress`, `steady_thermal`, `modes`, `buckling`) over ordinary forms, with regularized check regions | `StudyError { missing, fix }` for an unconstrained or unloaded study | FLX-O-ARCH-1 | 1 |
| Field types and product domains | `Field<D, V>` keyed by `GeometryId` and canonical entity numbers | `DomainMismatch` with a `field_transfer` fix | FLX-O-FIELD-1 | 0 |
| Sampling | `Sampler` with pointwise budget and gradient bound, located through Anvil's classification | `OutsideDomain`, `InsufficientAccuracy` | FLX-O-FIELD-1 | 0 (`Analytic`, `Discrete`), 1 |
| Transfer and projection | Conservative for fluxes, consistent for states | `NotSameInterface` from Anvil | FLX-O-FIELD-2 | 1, 4 (interface overlays) |
| Extremum enclosure and region extraction | Bernstein subdivision; Implicit Bodies from scalar Fields | `kiln/work_limit` with the achieved gap beside it; `NotContinuous` | FLX-O-FIELD-3 | 1 |
| Geometry-driving Fields | Sizing, metric, displacement, thickness, radius, density, orientation | `InsufficientAccuracy` naming the producer | FLX-O-FIELD-4 | 1 (density), 2 |
| Storage and canonical form | Chunked CAS arrays over canonical bytes | None: encoding is total over finite values, and non-finite values never reach storage | FLX-O-FIELD-5 | 0 |
| Label invariance | Field values unchanged under renaming | `LabelVariance` raised by the rename oracle on any difference | FLX-O-FIELD-6 | 1 |

## Error budgets, goals and checks

This section exists because a number without a stated error cannot decide anything, and incumbents leave that judgement to the analyst. Flux produces every part of every budget except model form; ING turns budgets into verdicts by one rule; COV supplies validation and validity envelopes.

### Budgets and guarantees

Every result Field and every estimated reduction carries an `ErrorBudget<Q>` ([contract section 5.1](../contract.md)). Each part is stated in the norm of the quantity it bounds, and parts in different norms never combine.

Each `Estimated` part names its calibration: a `Class`, measured on a held-out corpus, or a `Statistical` method with a stated α. An `Estimated` bound without either is an `Indicator`, and an `Indicator` never decides. Proofs exist only for energy norms on fitted simplices and for bounded linear goals built on them. Peaks, point values and eigenvalues get calibrated DWR estimates, and methods without an estimator get calibrated solution verification. [Reference](#estimators-by-error-source) lists the estimator, norm and kind for every source.

**Decision D-FLX-4:** Flux reports every error through `ErrorBound<Q>` and `ErrorBudget<Q>`, one bound per source in its own norm, never converted; a bound is `Guaranteed` only when a proof for that method covers that norm, and the estimator's metadata names the theorem.
*Why:* in three dimensions the energy space does not embed in the space of bounded functions, so energy bounds cannot certify peak stresses, and a total across norms would claim exactly that.
*Rejected:* totals across norms; an `Unknown` kind, which says less than `NotQuantified { reason }`.

A total takes its weakest part's kind. It is `Guaranteed` only on fitted simplices with polynomial data and planar faces, and only with a `Guaranteed` algebraic part.

For a bounded linear functional J with adjoint z, an iterative solve leaves a residual r, so J(u) − J(u_h) = a(u − u_h, z − z_h) + r(z_h). Flux bounds |J(u) − J(u_h) − r(z_h)| by the product of the primal and adjoint energy bounds, and files |r(z_h)| ≤ η_alg · ‖z_h‖_A, with η_alg the energy-norm algebraic bound, under the algebraic part. The floating-point part of a goal follows the same rule. After a direct factorization the energy-norm algebraic part is ‖r‖_{M⁻¹}/√σ, where a canonical LDLᵀ inertia count of A − σM certifies A ≥ σM, with σ lowered by the backward-error bound.

Material properties enter in two ways, and Flux treats them differently. A limit written against a basis value, such as `0.6 * yield_strength`, reads its basis as an exact interval, holds at both ends and adds no budget part (COV owns this rule). A property that drives the solve, such as Young's modulus or conductivity, arrives as its basis interval. Its input part is `Estimated { Statistical { method: ToleranceLimit, α } }`, with α the basis's non-content fraction (0.10 for a B-basis value, 0.01 for an A-basis value), and the union bound includes it.

Flux propagates a property enclosure by the sign of the adjoint sensitivity. It first checks that the response is monotone: one derivative sign at both ends, and no interior extremum by a midpoint second-order test. Where that fails, as near a resonance, it subdivides the interval or marks the part `NotQuantified { NonMonotone }`.

### Regularized goals and singular sets

Peak and point quantities are well posed only after regularization, so the rules below fix the radius and the excluded regions, and two engineers checking one part read the same functional.

**Decision D-FLX-23:** Peak and pointwise quantities are regularized goals: `f.max(over: R, smooth: ρ)` maximizes a Gaussian local average of radius ρ, `f.at(x, smooth: ρ)` evaluates it at x, boundary points average over a geodesic disc, and `pnorm` serves optimization; the default ρ is 0.1 times the smallest radius of curvature over the smooth faces and fillets in R, or 0.1 times the local wall thickness at a sharp convex edge with compatible conditions, floored at the larger of the drawing's edge-break size and the Material's microstructural length, and the report shows ρ and its source.
*Why:* raw maxima diverge at singular points, a part-size radius hides fillet peaks, and taking curvature at an unbroken machined edge would drive ρ to zero.
*Rejected:* raw maxima; p-norms for checks; 1% of the region's diameter; curvature over every edge, which makes sharp edges undecidable.

The regularization part is the enclosed gap between the regularized goal and the raw maximum of the computed Field. `flux::estimate_goal` estimates the goal over the frozen solution; it never re-solves the primal.

Two further goals serve validation and fatigue. `f.gauge(at:, length:, direction:)` averages strain over a gauge's grid area, so a check predicts exactly what a bonded gauge or an image-correlation subset measures. `f.tcd(method: point | line | area | volume, L)` evaluates the theory of critical distances by that method's own operator, along the inward normal from the hot spot. The operators are the stress at L/2, the average over 2L, and the area and volume averages [Taylor 2008] [unverified]. Each Material records which method calibrated its L, and a mismatch fails with `CriticalDistanceMismatch { calibrated, requested }`.

**Decision D-FLX-39:** `flux::singular_sets` flags only conditions that make the exact stress unbounded: a concave edge from `anvil::classify_edges` whose leading Williams exponent λ₁ is below 0.9 [Williams 1952], ambiguous edges, re-entrant corners, material interfaces meeting the boundary, point and line measures, estimates that stagnate under refinement, and conditions that are incompatible where they meet; each flagged set has a default neighbourhood of max(2ρ, local wall thickness), `study.regular()` is the domain minus those neighbourhoods, and a regularized maximum attained on a neighbourhood's boundary is `Undecided { MaximumAtExclusion }` with the fix "model the support".
*Why:* blanket flags left ordinary checks undecidable although Hertzian contact is bounded, a whole-face exclusion removed the fillet the canonical check exists to judge, and a maximum on an exclusion boundary depends on what the model left out.
*Rejected:* flagging every patch edge and contact boundary; one fixed angle for concave edges; exclusions by whole faces.

Incompatible conditions are a clamped face meeting a free face, a patch edge inside a face, a traction along a free neighbour's normal, and an edge or corner inside a contact zone. Edges with λ₁ between 0.9 and 1 carry `Note::WeakSingularity`. Smooth contact boundaries only guide hp refinement. A point quantity whose region meets a flagged set is `Undecided { SingularPoint }`, and a check may override a default neighbourhood in source.

### Calibrated estimates

A DWR estimate is not a proof, so Flux measures how often it underestimates and reports every bound already multiplied by that measured factor. The rules below make calibration a reproducible, reviewable input like any other.

**Decision D-FLX-24:** Every `Estimated { Class }` bound is reported multiplied by its class's η99, the 99th-percentile underestimate factor measured on held-out cases, and labelled with the class and α; each class declares an envelope over degree p, minimum cut fraction, ρ/h, distance to flagged sets, cells across the thinnest section in the goal's region, smallest feature or fillet radius over h, load type, Poisson's ratio and material contrast, and a result outside the envelope, or without a class, is `Indicator`.
*Why:* one decision rule then serves both fidelities, every outcome states its confidence, and class membership is computable from the result.
*Rejected:* a margin added at the consumer; machine-local factors; classes as bare labels without envelopes.

Calibration tables live in `std::sim::calibration`, pinned in `ingot.lock` and part of every key that reads them. One rule states α everywhere: an entry is accepted only with zero undershoots in at least 300 held-out cases, and is recorded as α = 0.01 at 95% confidence. Reports print the total as "confidence ≥ 1 − Σα at 95%".

**Decision D-FLX-40:** A calibration entry changes only through a reviewed Proposal with at least 300 held-out samples and zero undershoots, at least 20% of them from `std::opt` runs that minimize the check margin inside the envelope; references come from an independent code on fitted, curved high-order meshes (MFEM or deal.II as oracles), accepted only when a p-sequence p, p + 1, p + 2 shows exponential convergence and its Richardson spread is below 10% of the bound, and each reference records its code and mesh hash.
*Why:* optimizers seek exactly the designs where an estimator undershoots, and a reference from the same immersed code shares its cut quadrature, penalty and aggregation, so a common bias would never show.
*Rejected:* parametric samples only; same-code solves two degrees higher as references, kept only as a cross-check.

An Ingot generator under `oracles/flux/` produces the corpus, from L-brackets and sharp-edged machined brackets to lattice blocks with skins and inserts. `flux::confirm_refinement` checks a `SignOff` `Pass` that rests on an `Estimated` discretization part one level finer, at h/2 or p + 1. The refined value must lie inside the first bound and carry a smaller bound, or the verdict is `Undecided { reason: CalibrationUnconfirmed }`.

| Phase 1 class | Quantity | Model and discretization | Gates |
| --- | --- | --- | --- |
| `elasticity.peak` | Regularized stress peak, gauge and critical-distance goals | Linear elasticity, aggregated CutFEM, p = 2 to 6, adjoint at p + 1 | GP1, GP2 |
| `elasticity.peak.interactive` | The same goals at `Interactive` | Adjoint at p with reconstructed weights | GP1, GP2 |
| `elasticity.frequency` | Natural frequency | Eigenvalue DWR, two-sided | GP1, GP2 |
| `elasticity.buckling` | Buckling factor | Coupled DWR with the prestress adjoint | GP2 |
| `lattice.strut_stress` | Localized strut stress | Beam lattice with CT-fitted joints | GP2 |
| `lattice.buckling` | Lattice buckling factor | Coupled DWR on the beam lattice | GP2 |

MEC assigns classes to its check families. Later phases add classes for reduction, step halving, modal truncation, bolted joints, solution verification and circuit Newton residuals (`mna_newton`, on ELX's corpus).

**Decision D-FLX-15:** Flux produces budgets and ING decides checks by one rule (disjoint enclosures decide, subject to the check's `decides_on`), returning `CheckOutcome`; Flux adds no margin rule of its own.
*Why:* a second rule in the physics engine would let two tabs disagree about one verdict.
*Rejected:* binary checks on point values; a fixed safety multiple on bounds at `Interactive`.

### Fidelities

| Aspect | `Preview` | `Interactive` | `SignOff` |
| --- | --- | --- | --- |
| Methods | Reduced, surrogate, coarsest or shifted-boundary solves | Aggregated CutFEM at p = 2, one adaptive pass, goal adjoints at p | hp-adaptive, goal adjoints at p + 1, refinement confirmation |
| Platform class | Any | CPU, or `Gpu` in `f32` with estimation on the CPU | The canonical class, or a GPU solve certified on the CPU |
| Bounds | `Indicator` | Calibrated `Estimated` | `Guaranteed` where proven, else calibrated `Estimated` |
| Checks | Always `Undecided` | ING's rule; verdicts are provisional | ING's rule |
| Shared cache | Never written | Written | Written once two trusted builders agree |

On a GPU class at `Interactive`, Flux evaluates the read-back Field's residual and estimator on the CPU in `f64`, as COV's `F32Safe` rule requires; GPU-evaluated estimators are `Indicator` only. Nodes record the fidelity of the bounds they observed, so a branch on `Undecided` below its ceiling waits as `Pending`.

### Solution verification for methods without an estimator

Finite-volume flow, lattice Boltzmann, FDTD, particles and explicit dynamics have no a posteriori estimator, so their results stay `Indicator` unless a solution-verification study, cheaper than the solve it checks, turns them into calibrated bounds.

**Decision D-FLX-34:** `std::sim::solution_verification` treats the production discretization as the finest of three grids, builds the two coarser ones by octree coarsening at ratio 2 (a re-rooted octree when the ratio is not an integer) or by p-coarsening for high-order solves, freezes adaptivity, and applies Roache's grid convergence index (GCI) with safety factor 1.25 [NASA GCI tutorial]; each method family's band is a calibration class with its own η99.
*Why:* refining upward from a production mesh multiplies the cost of a large transient solve many times over and needs non-nested octrees, while coarsening keeps verification cheaper than the solve it checks; uncalibrated bands would mean something different from every other `Estimated` bound.
*Rejected:* single-grid trust; uniform upward refinement; uncalibrated bands; GCI on adapted meshes.

Adapted runs and oscillatory convergence stay `Indicator`, and a non-monotone triple returns `NotAsymptotic { ratio }`. LES and DDES stay `Indicator` without a fixed explicit filter width and a batch-means statistical part. Moulding warpage is verified by calibrated GCI at the measured points that MFG's validation uses.

### Validity zones and cross-class agreement

`flux::validity_zones` evaluates COV's regime functions into a `Field<Body, ValidityZone>` and `Flag` or `Refuse` checks, under COV's zone semantics. `Refuse` yields `Error(Failure)` with `ValidityError::OutsideEnvelope { variable, bound, escalate_to }`, and Flux never switches models. Transient solves keep running extrema per accepted step through `segmented_reduce` and write zone Fields at output steps.

Results from different platform classes agree by PLT's rule: with equal resolved plans, adaptive marks and steps, only the algebraic and floating-point parts plus a floor may differ.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Error budgets | `ErrorBudget<Q>` on every result; one producer per source; every `Estimated` part names a class or a statistical method | `NotQuantified { reason }` names each uncounted part | FLX-O-ERR-1 | 1 |
| Guaranteed energy bounds | Equilibrated flux on fitted simplices; strongly symmetric stress | `Estimated` or `Indicator` where no theorem applies | FLX-O-ERR-1 | 2 (diffusion), 3 (elasticity) |
| Guaranteed algebraic parts | Multilevel bound; certified spectral bound after factorization; goal part through ‖z_h‖ | Elsewhere `Estimated`, so the total is too | FLX-O-ERR-2 | 2 |
| Guaranteed linear goals | Primal–dual product with the residual term r(z_h) | `NotQuantified` if a factor is unguaranteed | FLX-O-ERR-2 | 2 |
| Regularized goals | `max`, `at`, `pnorm` and `gauge` through `estimate_goal`, with ρ and its source reported | `Undecided { needed }` with a goals fix | FLX-O-ERR-3 | 1 |
| Critical-distance goals | `tcd` by point, line, area or volume operator, matched to the Material's calibration | `CriticalDistanceMismatch { calibrated, requested }` | FLX-O-ERR-12 | 1 |
| Eigenvalue estimates | Two-sided DWR for frequencies; coupled DWR for buckling factors; Kato–Temple or Lehmann algebraic bounds | `Indicator` without a class | FLX-O-SOLVE-6 | 1 |
| Singular sets | `singular_sets` by edge class and compatibility; `study.regular()` | `Undecided { SingularPoint }`; `Undecided { MaximumAtExclusion }` | FLX-O-ERR-4 | 1. Requires: ANV `anvil::classify_edges` |
| Calibration | η99 tables with envelopes; one α rule; independent references | `Indicator` outside the envelope | FLX-O-ERR-5 | 1 |
| Refinement confirmation | `confirm_refinement` one level finer | `Undecided { reason: CalibrationUnconfirmed }` | FLX-O-ERR-3 | 1 |
| Property-basis propagation | Basis intervals into the input part with a monotonicity test | `NotQuantified { NonMonotone }`; `NotQuantified` without both basis values | FLX-O-ERR-11 | 1 |
| Temporal goal estimates | Adjoint-weighted residual and step halving, each its own class | Summed local estimates stay `Indicator` | FLX-O-ERR-6 | 2 |
| GPU-solved `Interactive` results | CPU `f64` estimation of the read-back Field | GPU-evaluated estimators stay `Indicator` | FLX-O-KER-4 | 2 |
| `Preview` fidelity | Reduced, surrogate, coarsest or shifted-boundary solves | `Undecided { Indicator }` for every check | FLX-O-ERR-7 | 1, 2 (shifted boundary) |
| Solution verification | Calibrated three-level GCI by coarsening from the production grid | `NotAsymptotic { ratio }` keeps `Indicator` | FLX-O-ERR-8 | 3 |
| Validity zones | `validity_zones` with running extrema | `ValidityError::OutsideEnvelope` inside `Error(Failure)` | FLX-O-ERR-9 | 1 |
| Cross-class agreement | PLT's rule on resolved plans and marks | `ClassDisagreement` opens PLT's determinism incident | FLX-O-ERR-10 | 1 |
## The weak-form language

Quick studies cover the common cases, but an engineer who needs a different physics writes it directly, in the same notation std uses. This section shows a complete problem first and then the spaces, measures, operators and checks it rests on.

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

Four things happen before anything runs. The compiler checks that both sides of `heat` have one dimension, power per unit temperature times temperature, so a missing conductivity or a wrong unit is a compile error. `solve` asks `flux::plan` for a discretization per region, exactly as `static_stress` did. The goal tells the adaptive loop to refine for the pad's mean temperature and not for anything else. And because a regional mean is a bounded linear functional, its bound may be `Guaranteed` on a fitted discretization, unlike the bracket's stress peak.

A transient version adds heat capacity and a time derivative, and the plan picks the time integrator:

```
let rho_c = p.material.density() * p.material.specific_heat(at: 20degC)
let warm = rho_c * dt(t) * v * dx(p) + inner(k * grad(t), grad(v)) * dx(p) == q * v * ds(pad)
let history = solve(warm, fixed: [(clamp, 40degC)], initial: 20degC, until: 600s,
                    goals: [t.mean(over: pad).max(over: time)])
history.t  // Field<(Part, Time), Temperature>
```

Forms follow the semantics of UFL, the Unified Form Language of FEniCS, extended with units ([contract section 6](../contract.md)). They are staged `Expr` values, lowered to the shared symbolic layer and checked for units, linearity and conformity before anything runs. `std::sim` holds the building blocks and `std::physics` the models built on them (principle 1).

### Spaces, elements and measures

Flux offers H¹, H(curl), H(div), L², trace, spline, manifold, section and parameter-domain spaces, with elements of any order on every cell shape; [Reference](#spaces-problem-kinds-and-form-checks) gives their constructors, elements and phases.

One Rust element library defines every element and orients H(curl) and H(div) bases in the restriction, so meshes need no global orientation. Cells run from interval to pyramid, with exact-sequence pyramid bases [Fuentes et al. 2015].

Measures are `dx` (volume, sheet or wire), `ds` (true or queried faces), `dS` (interior facets), and `dE` and `dP` (true edges and points). `dI` integrates over interfaces between Instances or between solids, shells and beams, and `dξ` over parameter domains.

**Decision D-FLX-6:** Measures refer to true-geometry entities selected by `Query`, and solves receive them as canonical entity numbers of the Body's `GeometryId`, never as mesh entities or names.
*Why:* one form then runs fitted, immersed or reduced, conditions survive remeshing, and renaming never changes a result.
*Rejected:* mesh-tagged boundaries as in FEniCS and MFEM, which break on every geometry change.

### Operators, problem kinds and checks

Operators cover algebra, calculus, facet terms (`jump`, `avg`), `dt`, pointwise eigen-decomposition, `select`, `im` and `.absolute()`. Non-smooth functions declare generalized derivatives.

Linear, nonlinear, energy, mixed, time-dependent, harmonic, eigenvalue, constrained and continuation problems are all written this way. Before anything runs, every form passes four static checks (units, arity, conformity, and inf-sup stability with quadrature degree), each failing with a typed `FormError` and a fix; Reference tabulates both.

### One symbolic layer and compilation

Forms, constraints, analytic Fields and implicit functions are all symbolic expressions, so Crucible keeps one hash-consed expression type, `kernels::expr`, with typed node sets per use and symbolic differentiation written once ([contract section 7.5](../contract.md)). Ingot's `Expr<T>` lowers to it, `flux-forms` adds the form node set, and Anvil's implicit functions add theirs.

The compiler lowers checked forms to index notation and erases units. It takes forward symbolic Gateaux derivatives on the expression graph, with `adjoint` and `action`, and applies Piola pullbacks for H(curl) and H(div). Non-polynomial integrands get degree 2p + 2 with an estimate one order higher, and kernels split into libCEED's `Eᵀ Bᵀ D B E` form: element restriction, basis evaluation and a pointwise operator [libCEED API].

**Decision D-FLX-7:** The form compiler is written natively in Rust, following TSFC's structure-preserving design [Homolya et al. 2017] and libCEED's operator split.
*Why:* it runs inside Kiln on every operating system and in browsers, emits the kernel IR and differentiates at the form level; no existing compiler does all three in Rust.
*Rejected:* UFL with FFCx or TSFC through Python, which cannot run in the browser sandbox.

A local Newton solve is `local_solve(residual, x0)`, differentiated by the implicit function theorem at convergence. Its tolerance follows the global Newton tolerance, so return mapping keeps quadratic convergence. Constitutive models are Ingot functions or `crucible:material/constitutive` Wasm components with consistent tangents.

`solve` returns a record of Fields: each unknown, plus declared outputs such as `stress` and `von_mises`, which add a recovery part to the budget.

**Decision D-FLX-38:** Nested and phase-space models are forms over product spaces with a parameter measure `dξ` (particle diffusion in battery electrodes, FE² micro problems, discrete-ordinates radiation, population balances), compiled into batched local problems, one per macro quadrature point.
*Why:* battery cell models (the single-particle model with electrolyte, SPMe, and the Doyle–Fuller–Newman model, DFN) and COV's radiation models then get form-level derivatives and GPU kernels like any other form.
*Rejected:* special-purpose solvers that lose derivatives and estimators.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| H¹, L², real, mixed and restricted spaces | Elements of any order on every cell shape | `FormError::Conformity` | FLX-O-DISC-1 | 0 (H¹, p ≤ 4), 1 |
| Planar and axisymmetric spaces | Plane stress, plane strain, generalized plane strain and axisymmetric sections, with or without twist | `SymmetryBroken { entity }` | FLX-O-SYM-1 | 1 |
| H(curl), H(div), trace spaces | Nédélec, Raviart–Thomas, BDM, facet spaces | `FormError::Conformity` | FLX-O-DISC-1 | 3 |
| Spline and manifold spaces | NURBS and THB spaces; sheet and wire spaces | `UnpairedFaces` or `NotPrismatic` from Anvil | FLX-O-DISC-6 | 1 (wires), 2 |
| Parameter-domain spaces | `Interval`, `Sphere`, products, `dξ` | `FormError::Conformity` | FLX-O-FORM-5 | 4, 5 (DFN) |
| Static form checks | Units, arity, conformity, inf-sup, quadrature | Typed `FormError` with a fix | FLX-O-FORM-1 | 0 |
| Symbolic layer | One hash-consed `kernels::expr` for forms, constraints, analytic Fields and implicit functions | `ExprError::IllTyped { node }` | FLX-O-FORM-2 | 0 |
| Symbolic derivatives | Gateaux derivative, `adjoint`, `action` | `NotDifferentiable { op }` | FLX-O-FORM-2 | 0 |
| `local_solve` | Implicit-function derivative at convergence | `LocalSolveDiverged { point }` | FLX-O-FORM-3 | 1 |
| UFL coverage | FEniCS and Firedrake demos expressible | `FormError::Unsupported { construct }` | FLX-O-FORM-4 | 3 |

## Kernels, back ends and determinism

Every result-affecting number passes through one kernel intermediate representation (IR), so one place fixes the order of every floating-point operation; this section states how it becomes CPU, Wasm and GPU code.

FLX owns the kernel IR in `kernels` and its back ends ([contract section 7.5](../contract.md)). IR v0 holds element kernels with sum factorization, constitutive functions with forward-mode derivatives, implicit tapes and `local_solve`. It is additive-only once a consumer compiles against it, and freezes at the phase 0 gate once one kernel of each kind passes its oracles on both CPU back ends. `kernels` emits code and asks `wasm-host` to load generated modules, and holds no `unsafe` code.

Network residuals join the IR in phase 2 and Verilog-A device models in phase 3. Assembly is full, element-level, partial with sum factorization or matrix-free, by degree and device. Throughput peaks at degrees three to six [deal.II matrix-free], and simplices use collapsed-coordinate bases above degree 3 [Moxey et al. 2020].

**Decision D-FLX-9:** On CPUs, user forms compile at run time to Wasm SIMD128 modules and std forms ahead of time; user forms target 1.5 times the ahead-of-time time for memory-bound operators (p ≤ 2), and 2.5 times on AVX2 and 5 times on AVX-512 for compute-bound sum factorization (p ≥ 3).
*Why:* one sandboxed path gives canonical bits everywhere, and SIMD128 is half as wide as AVX2, so compute-bound kernels pay more for it than memory-bound ones.
*Rejected:* a native just-in-time compiler; shipping LLVM; one speed target for every kernel family.

**Decision D-FLX-10:** GPU kernels come from the kernel IR through WGSL on wgpu: implicit preview ships in phase 1 and `f64` server paths on Vulkan `SHADER_F64` in phase 3, `Interactive` elasticity ships in phase 2 (or in phase 1 if phase 0 measures `CpuIsa` kernels missing the interactive simulation row of contract section 13.3), and a CUDA or HIP back end is reconsidered at the phase 4 gate.
*Why:* WGSL lacks `f64`, wgpu offers `SHADER_F64` only on Vulkan [wgpu Features], CubeCL changes its interface between minor versions [CubeCL repository], and CPU kernels may meet the interactive row alone.
*Rejected:* CubeCL in phase 1; unconditional WGSL elasticity in phase 1.

**Decision D-FLX-8:** On CPU back ends the kernel IR fixes every floating-point operation and reduction order, with contract section 7.3's canonical lane order for horizontal operations (the 8-lane f64 or 16-lane f32 tree of `det_sum`) and any native width for element-wise code, and no FMA in the canonical class; `CpuIsa` FMA variants serve `Preview` and `Interactive` for sum factorization at p ≥ 3, dense GEMM and LU, and NURBS evaluation from phase 0, other families only after phase 0 measures a loss above 1.3 times, memory-bound operators never.
*Why:* x86-64-v2 and wasm32 lack FMA, compute-bound kernels lose most without it, and wide virtual vectors for all code would spill registers on x86-64-v2 and SIMD128.
*Rejected:* FMA in the canonical class; FMA for memory-bound kernels; 512-bit virtual vectors for every kernel.

WGSL kernels never claim bit-identity with CPU kernels [WGSL specification]. Throughput targets are contract section 13.3's two CEED bake-off rows (the CEED benchmark problems BP1 to BP6 [CEED bake-off]), plus immersed elasticity kernels.

**Decision D-FLX-11:** `Portable` code computes elementary functions only with PLT's correctly rounded `detmath`, and GPU kernels use fixed-sequence approximations with documented ulp bounds, never vendor built-ins.
*Why:* platform and vendor libraries differ in their last bits, and correct rounding on GPUs needs precision WGSL cannot guarantee.
*Rejected:* a separate Flux math library; the platform `libm`.

### Determinism

Contract section 7.3 and PLT own the mechanisms. Flux adds six rules:

1. DOFs (degrees of freedom), cells and partitions follow canonical geometric order (Morton order, canonical entity numbers), never names.
2. Work splits into virtual partitions fixed by problem size and combined in partition order.
3. Assembly gathers contributions in a fixed order, without floating-point atomics.
4. Node-local reductions use `det_sum` and `det_reduce`, and `exact_sum` only across ranks; conjugate-gradient overhead targets 1.05 times.
5. A floating-point control state changed during an operation aborts it for a rerun.
6. GPU paths use integer-limb reductions, CPU non-finite checks after readback, and per-pipeline known-answer tests run before a pipeline's first result-affecting dispatch.

**Decision D-FLX-18:** GPU reductions use integer-only exact accumulation: bins of 32-bit limbs with explicit carries, combined in fixed order.
*Why:* wgpu offers 64-bit integer atomic add only on Vulkan and DX12 and float atomics only on some devices, while 32-bit integer arithmetic is exact everywhere.
*Rejected:* floating-point atomics; vendor reduction libraries.

**Decision D-FLX-19:** Canonical CPU solves, estimators and `flux::certify` are `Portable` in the canonical class; GPU solves are `ClassExact` in their `Gpu` class, and a `SignOff` check on one rests on the pinned Field plus `certify`.
*Why:* release gates need canonical outcomes, while GPUs pay off at `Interactive` and as solvers whose answers the CPU certifies.
*Rejected:* Flux-specific class names beside PLT's `PlatformClass`.

Each Flux operation family is its own `flux-op-<family>` crate, and each released version is a frozen source directory with a closure hash ([contract section 4](../contract.md)). A changed `flux::plan` default therefore needs a new behaviour version.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Kernel IR v0 | Element, constitutive and implicit-tape constructs; forward derivatives; `local_solve` | IR validation error naming the construct | FLX-O-KER-1 | 0 |
| Canonical CPU back end | Ahead-of-time Rust with canonical SIMD from x86-64-v2 and ARMv8; `Portable` | None: kernels are validated at build time and cannot fail at run time | FLX-O-KER-3 | 0 |
| Wasm SIMD128 back end | Generated at run time: user forms everywhere, all forms in browsers | Determinizer rejection | FLX-O-KER-6 | 0 |
| WGSL back end | wgpu on Vulkan, Metal, DX12 and WebGPU: implicit preview, `Interactive` elasticity; `ClassExact` | A failed known-answer test falls back to the CPU, reported | FLX-O-KER-4 | 1 (preview), 2 (elasticity, or 1 by phase 0's measurement) |
| `f64` GPU server path | Vulkan `SHADER_F64`, certified on the CPU | A missing feature takes the CPU path, reported | FLX-O-KER-4 | 3 |
| FMA variants | `CpuIsa` kernels for compute-bound families | `FmaAtSignOff` refused by the registry | FLX-O-KER-2 | 0 |
| Floating-point environment guard | Checked at operation start and end | Abort and rerun | FLX-O-KER-5 | 0 |
| Throughput | Both CEED rows plus immersed elasticity kernels | A regression blocks beta promotion | FLX-O-KER-1 | 0 |
| Solves at scale | `SignOff` linear static at 10M DOFs on the reference workstation, 50M on the server class; incompressible flow throughput rows | A miss blocks beta promotion from the row's phase | FLX-O-KER-7 | 2, 3 (server and flow), 4 (GPU flow) |

## Solve plans and per-region discretization

An incumbent's analyst spends most of the day choosing elements, meshing and deciding which walls become shells. Flux makes that choice from the geometry and the study, records it as data, and lets the engineer override any part in source.

`flux::plan` maps a problem, fidelity, platform class and `Budget` to a `SolvePlan`: per-region models, spaces, quadrature, assembly, solvers, precision, adaptivity and estimators. Plans depend only on their inputs, never on the hardware they run on, and print, edit and pin as Ingot.

```
let plan = std::sim::plan(elasticity, fidelity: SignOff, goals: [stress_goal], tol: 2%)
plan.explain()   // each choice with the alternatives considered
let result = solve(elasticity, fixed: clamp, plan: plan.with(region: p.regions(role: web), model: Solid))
```

**Decision D-FLX-20:** The resolved plan is pinned, not just the solver version: a versioned `flux::plan` resolves every default, and the resolved plan enters the cache key.
*Why:* most result drift comes from changed defaults, not changed algorithms.
*Rejected:* versioning only the solver kernels.

### Per-region models

`flux::mark_reduction` returns a `Field<Body, ReductionKind>` from the study's conditions and Anvil's thickness, curvature and distance queries. The slenderness test uses L_local, the smallest of four lengths: the span between supports, the radius of curvature, |q|/|∇q| for a distributed load q, and the distance to the nearest concentrated condition. Concentrated conditions are point or line loads, patch edges inside the wall, openings, features and welded joints; distributed loads, body forces and inertia do not shorten L_local ([contract section 7.1](../contract.md)).

| Region | Criterion | Model | Geometry from Anvil |
| --- | --- | --- | --- |
| Thin wall | t / L_local ≤ 0.2 | Reissner–Mindlin shell; laminates by ABD matrices (the laminate stiffness matrices) | `anvil::mid_surface` sheet, thickness Field, junction curves |
| Very thin smooth wall | t / L_local ≤ 0.05 on a NURBS mid-surface | Kirchhoff–Love isogeometric shell | Same, NURBS faces |
| Member or strut | Prismatic over L_local, d / L_local ≤ 0.2 | Timoshenko beam; Vlasov warping for open thin-walled sections | `anvil::member_axes` axes, joints, sections |
| Strut lattice | Strut graph from `anvil::lattice` | Beam lattice with calibrated joints, or homogenized | Strut graph |
| Sheet lattice | Minimal-surface cell from `anvil::lattice` | Shell on the cell's mid-surface, or homogenized | `mid_surface` implicit path |
| Revolved or prismatic Body under conditions that share its symmetry | Certified revolution or extrusion, symmetric conditions | Axisymmetric or planar section model | MEC's declared symmetry; `anvil::section` |
| Everything else | Fails the criteria above | Solid on the immersed octree, or fitted where required | The Body |

**Decision D-FLX-12:** Discretization is chosen per region: shells and beams where the local slenderness criterion holds, the immersed octree for solids, fitted meshes for contact and turbulent boundary layers, beam lattices, sheet shells or homogenization for lattices, and isogeometric shells for very thin NURBS walls; junction zones stay solid for two wall thicknesses, three for a junction class that fails its coupling oracle.
*Why:* a volumetric octree on thin-walled golden products needs 10⁶ to 10⁸ DOFs where reduced models need 10⁴ to 10⁵.
*Rejected:* immersed solids everywhere; an untested junction length.

Reduced regions couple to solids through `dI` interfaces [Nguyen et al. 2013]: rigid at `Interactive`, and Nitsche continuity of displacement and rotation at `SignOff`, because rigid coupling stiffens the junction.

### Reduction by symmetry

Incumbents solve an O-ring groove, a pressure vessel or a coil in two dimensions at a hundredth of the 3D cost, and a bladed disc on one sector. Flux offers the same reductions and checks that they are valid.

**Decision D-FLX-48:** Plane stress, plane strain, generalized plane strain and axisymmetric models (with or without twist), and mirror symmetry, antisymmetry and cyclic-sector reductions with harmonic indices, are detected by `mark_reduction` from MEC's declared symmetries or declared with `std::sim::symmetry(planes:, kind:)` and `cyclic(sector:, count:, harmonics:)`; every reduction checks that loads, conditions and geometry share the symmetry and fails with `SymmetryBroken { entity }` otherwise.
*Why:* a silent reduction of a non-symmetric load gives a confident wrong answer, while a checked one gives the incumbent's speed with no new risk.
*Rejected:* declared reductions without a check; reductions only by analyst declaration.

Axisymmetric spaces use the r-weighted measure, and non-axisymmetric loads on an axisymmetric Body expand in Fourier modes from phase 3. Cyclic modal analysis solves complex Bloch-periodic sector problems per harmonic index and returns a `Field<(Body, Mode, HarmonicIndex), Displacement>`; the full-model view is a display operation.

### Reduction error

**Decision D-FLX-26:** Dimensional-reduction error files under `reduction or surrogate` and has two terms: a local term from 3D patches extending max(3t, 2√(R·t)) beyond each goal region, R the local radius of curvature, re-solved with boundary data from the reduced model; and a global term, the 3D residual of the reconstructed field (shell and beam kinematics expanded through the thickness) weighted by the reduced adjoint at every junction and wherever t/L_local exceeds 0.1 [Oden and Prudhomme 2002]; the sum is `Estimated { Class }` in a reduction class, else `NotQuantified`.
*Why:* shell and beam theories carry an error refinement never removes, a patch catches only local 3D effects, and in statically indeterminate frames and shell assemblies the omitted joint flexibility and transverse shear redistribute forces globally.
*Rejected:* reduction error as model form; reduced models treated as exact; the patch term alone.

### Submodeling

Goal-oriented adaptivity refines where a check needs accuracy, so routine submodeling is unnecessary. `std::sim::submodel(global: Field, region:, model:)` serves the cases that remain, such as a shell frame with a solid weld detail or a supplier's global loads on a local part, reusing the patch machinery above. The cut-boundary transfer error enters the budget under `interpolation`, and a global Field from outside Crucible enters as an External input.

### Wall resolution in flow and moulding

**Decision D-FLX-45:** Laminar thermal and moulding frozen layers are resolved by octree wall refinement: heated walls get at least five cells at p = 2 across δ_T = H·Ra_H^(−1/4), and 3D fill and pack get eight across the cavity half-thickness; both counts are COV regime variables, under-resolved zones are `Extrapolated`, and `SignOff` fill-pressure and warpage goals need an estimator or solution verification.
*Why:* the four-cells rule comes from elasticity and does not resolve a thermal boundary layer, and fitted layers arrive only in phase 4, after GP5.
*Rejected:* fitted layers in phase 3; an unstated resolution.

[Reference](#plan-defaults) lists the plan's default model for each situation, from compact solids to lumped systems.

[[DIAGRAM diagrams/03-flux-per-region-discretization.jsx: per-region discretization · 4 models, 2 dI couplings]]

Read it top down: `mark_reduction` sorts each region of a Part into one of four models, and `dI` couplings join neighbours into one plan with one error budget per goal.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `flux::plan` | Problem, fidelity, class and `Budget` to a pinned `SolvePlan` with `explain()` | `PlanError::ExceedsLocal { memory, time }`; `NoValidMethod { region, reason }` | FLX-O-PLAN-1 | 1 |
| `flux::mark_reduction` | `Field<Body, ReductionKind>` from local criteria | `UnpairedFaces` from `mid_surface` keeps the region solid, with a note | FLX-O-PLAN-2 | 1 (lattices), 2 |
| Planar and axisymmetric models | Detected or declared section models for elasticity and heat, with a symmetry check | `SymmetryBroken { entity }` | FLX-O-SYM-1 | 1 |
| Symmetry and cyclic-sector reductions | Mirror, antisymmetric and cyclic reductions; cyclic modal analysis by harmonic index | `SymmetryBroken { entity }` | FLX-O-SYM-1 | 2 |
| Mixed-dimensional couplings | Rigid and Nitsche `dI` interfaces; tested junction zones | `IncompatibleInterface { region }` | FLX-O-PLAN-3 | 2 |
| Reduction error | Local patch re-solves plus the global modelling-error term, calibrated per class | `NotQuantified`, so a check reading it is `Undecided` | FLX-O-PLAN-4 | 2 |
| Submodeling | `submodel(global:, region:, model:)` with the transfer error in the budget | `RegionOutsideGlobal { region }` | FLX-O-PLAN-6 | 2 |
| Wall-resolution rules | Octree refinement across laminar and frozen layers | Under-resolved zones `Extrapolated` | FLX-O-PLAN-5 | 3 |
| Region overrides | `plan.with(region:, model:)` in source | `UnsuitableOverride { criterion, value }` as a warning | FLX-O-PLAN-1 | 1 |
## Discretizations for solids and structures

The plan names a model per region; this section specifies how each model is discretized. The immersed octree is the default because it removes meshing from the engineer's path, and the other discretizations exist where the octree is the wrong tool.

### Immersed octree

A 2:1-balanced octree covers the Body. Anvil's `GeometryQuery` classifies cells incrementally after local edits, and uncut cells are tensor-product cells with hanging-node constraints in the kernels.

- **Aggregated CutFEM.** CutFEM is the finite element method on a background grid that the geometry cuts through; cut cells integrate on the true geometry with Nitsche conditions and ghost-penalty stabilization [Burman et al. CutFEM]. Cut quadrature follows Saye's positive-weight methods, with Algoim as reference oracle [Algoim], and moment fitting only with non-negative least squares. Cells below a 1% volume fraction aggregate with neighbours (a smooth weight in optimization); an uncertified cut subdivides up to eight levels, then fails with `UncertifiedCut { cell, achieved }`.
- **Shifted boundary.** Full interior cells only, with boundary data shifted along the closest-point vector [Atallah et al. 2020]; `Preview` only.
- **Finite cell.** A volume-fraction indicator with void stiffness α, for voxel, CT and density geometry; patch tolerance O(α).

**Decision D-FLX-13:** One octree serves three treatments, with at least four cells across any section: aggregated CutFEM at `Interactive` (p = 2, one adaptive pass, cached cut quadrature) and `SignOff` (hp-adaptive), the finite cell method for voxel data, and the shifted boundary method for `Preview` only.
*Why:* stress checks sit on the true boundary, and one treatment for both deciding fidelities means one estimator family, one set of calibration classes and one singular-set logic.
*Rejected:* the shifted boundary method at `Interactive`, which extrapolates boundary stresses; two cells across a section.

### Fitted meshes

Fitted continuous finite elements run on curved Anvil meshes up to p = 8, and hex-dominant meshes from phase 4. They serve frictional contact, turbulent boundary layers, imported solver decks, and the one-sided eigenvalue bounds that need strong Dirichlet conditions. An invalid curved element fails with `InvalidElement { cell, jacobian_min }`, whose fix is Anvil's `untangle`.

### Shells, beams and lattices

Reissner–Mindlin shells use MITC-type elements at p ≤ 2 [Dvorkin and Bathe 1984] and hierarchic elements above, with locking measured by their oracle. Laminates use MEC's ABD matrices from phase 4. Kirchhoff–Love shells use C¹ NURBS spaces with Nitsche patch coupling and cut-cell trims [Bazilevs et al. 2006]. Beams are Timoshenko, with a Vlasov warping unknown for open thin-walled sections and constants from a 2D warping solve.

**Decision D-FLX-44:** Beam lattices place Timoshenko struts on `anvil::lattice` strut graphs, with joint-zone length and stiffness fitted per cell topology on MFG's CT scans of as-built unit cells, solved at full resolution as implicit Bodies with the finite cell method and held out by build plate; sheet lattices sign off on Reissner–Mindlin shells on the zero set of the cell's level-set field, and homogenization stays the continuum rung.
*Why:* in laser powder bed fusion, nodes gather material and adhered powder and down-skin struts grow, so joints fitted to nominal CAD cells miss the node stiffness and stress concentration where cracks start, and a full-resolution gyroid of 5 mm cells in a 100 mm cube needs about 4 × 10⁸ cells.
*Rejected:* a fixed one-radius joint zone; joint fits on nominal geometry; full-resolution sheet lattices.

For each member Flux evaluates COV's regime variables, among them the inelasticity ratio σ_cr,Euler / σ_proportional. Most struts in a metal lattice are stocky: a 1 mm strut four diameters long has an Euler stress far above any proportional limit, so compressive yield, not buckling, governs it. Flux therefore supplies two quantities per member. The localized axial stress, from `lattice.strut_stress`, feeds MEC's strut-strength check against the as-built compressive strength, reduced by a Johnson–Perry–Robertson factor computed from MFG's measured waviness. Eigen-buckling, from `lattice.buckling`, runs only over members whose ratio is below 1, where it governs global lattice instability.

### Explicit dynamics

Explicit dynamics serves drop tests (GP5) and crash boxes (GP9) with diagonal mass: spectral hexahedra, lumped B-spline shells and 15-node mass-lumped tetrahedra [Geevers et al. 2018]. Shells report hourglass energy, contact is penalty contact with `bvh_build` search, and COV's damage models drive erosion. Targets are 10⁷ element cycles per second on the reference CPU and 5 × 10⁷ on its GPU at `Interactive`. That makes production models such as CCSA's 2015 Camry model (2,277,283 elements) practical [CCSA Camry].

**Decision D-FLX-31:** Explicit dynamics on cut cells uses the discrete-extension CutFEM of Burman, Hansbo and Larson, whose extended-space mass lumps for leapfrog stepping [Burman et al. 2020], or aggregated cells with lumped mass; it stays disabled until its oracle shows a cut-independent critical step, and runs fitted or isogeometric meanwhile, canonically at `SignOff`.
*Why:* lumped mass scales with the cut fraction while stiffness does not, so tiny cut cells collapse the stable step, and ghost-penalty mass is not diagonal.
*Rejected:* ghost-penalty mass stabilization; unstated mass scaling.

Raw peak accelerations depend on sampling rate and mesh, so they are not well-posed goals, and a crash box folds through a sequence of bifurcations. Explicit dynamics therefore decides checks only on regularized functionals.

**Decision D-FLX-50:** Explicit-dynamics goals are regularized functionals (acceleration through a declared channel filter, energy absorbed, mean crush force over a displacement window, and the maximum of a time-averaged strain); buckling-sensitive cases run an ensemble over seeded geometric imperfections whose statistics form the statistical part, and coarsened GCI on each functional forms the discretization part, calibrated per family (`dynamics.drop`, `dynamics.crash`).
*Why:* these are the quantities the GP5 and GP9 gates compare, they converge where raw peaks do not, and ensemble statistics are branch-invariant, which principle 4 requires for a bifurcating problem.
*Rejected:* raw peak accelerations; a single deterministic crush run; uncalibrated GCI bands.

Channel filters follow the SAE J211 channel frequency classes [unverified], declared per check with the filter class recorded in the report.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Fitted continuous FEM | Curved Anvil meshes to p ≤ 8; hex-dominant | `InvalidElement { cell, jacobian_min }` with an `untangle` fix | FLX-O-DISC-1 | 2, 4 (hex-dominant). Requires: ANV `anvil::tetrahedralize` |
| Aggregated CutFEM | `Interactive` and `SignOff` solids; Nitsche, ghost penalty, positive weights | `UncertifiedCut { cell, achieved }` | FLX-O-DISC-2, FLX-O-DISC-5 | 1 |
| Shifted boundary method | `Preview` solids | `Undecided { Indicator }` for any check | FLX-O-DISC-3 | 2 |
| Finite cell method | Voxel, CT and density geometry | `PatchErrorAboveTolerance { alpha }` | FLX-O-DISC-4 | 2 |
| Reissner–Mindlin and Kirchhoff–Love shells | Mid-surface sheets, thickness Fields, laminates | `UnpairedFaces` keeps the region solid | FLX-O-DISC-6 | 2, 4 (laminates). Requires: ANV `anvil::mid_surface` |
| Timoshenko and Vlasov beams | Member axes and section regions | `NotPrismatic` keeps the region solid | FLX-O-DISC-6 | 1 (struts), 2. Requires: ANV `anvil::member_axes` |
| Beam-lattice models | CT-fitted joints; per-member regime variables; localized strut stress for strut-strength checks; buckling only below ratio 1 | `Indicator` outside the joint envelope | FLX-O-COUP-2 | 1. Requires: ANV `anvil::lattice`; MFG As-built strut calibration (metal powder bed) |
| Sheet-lattice shells | Shells on minimal-surface mid-surfaces | `UnpairedFaces` falls back to homogenization, stated | FLX-O-COUP-2 | 2 |
| Explicit dynamics | Diagonal mass, penalty contact, erosion; cut cells after the critical-step oracle | `StepCollapsed { element }` | FLX-O-DISC-7 | 3 (drop), 5 (erosion) |
| Explicit-dynamics goals | Filtered acceleration, energy absorbed, mean crush force, time-averaged strain; imperfection ensembles; calibrated coarsened GCI | `NotAsymptotic { ratio }` keeps `Indicator` | FLX-O-DYN-4 | 3, 5 (crash) |

## Discretizations for waves, flows and particles

Electromagnetics, flow and particle methods need discretizations that elasticity does not, and each brings its own route to an error bound. This section states them, and where they meet the incumbents' everyday workflows: wave ports, unit cells, parasitic extraction, rotating machinery and flow adjoints.

### Electromagnetics

**Decision D-FLX-32:** Resonant and narrowband problems use frequency-domain Nédélec FEM and broadband and EMC problems use FDTD (the finite-difference time-domain method); ports come from 2D eigenmode solves (`port_modes`), PML (the perfectly matched layer) is a complex coordinate stretch, an adaptive rational fast sweep (`fast_sweep`) carries a residual bound, and each port's S-parameters at declared frequencies are DWR goals in class `em.sparam`, with adaptivity stopping when every goal's bound is below the requested |ΔS|.
*Why:* ELX requires the capability of Palace [Palace documentation], lumped and numeric wave ports with an adaptive fast sweep, and an S-parameter without a stopping rule has no defined error at `SignOff`.
*Rejected:* routing every antenna problem to FDTD; a stopping rule on the change between passes, which bounds nothing.

FDTD uses the Yee grid with convolutional PML and auxiliary differential equations for dispersive materials. Conformal cells use the uniformly stable conformal update [Zagorodnov et al. 2003], or a stated cut-fraction cap with its accuracy cost. Magnetostatics and eddy currents use A–φ and T–Ω formulations with tree–cotree gauging or divergence-free coil currents. Motion uses a sliding interface on a cylindrical air gap or mortar coupling, for ELX's loss maps.

Boards use two models. Layered sheets are per-layer thin-sheet conduction coupled through-plane by `dI` conductances, for DC drop and current density. The plane-pair cavity model solves the 2D Helmholtz equation on sheet Bodies with port and via elements and complex LDLᵀ, for the power-distribution impedance ELX's power-integrity checks read.

Phased arrays, frequency-selective surfaces and radomes are designed as unit cells and then as finite arrays, as HFSS users do [PADT HFSS arrays]. Flux adds Bloch-periodic boundary pairs with a scan-angle phase, Floquet ports with an evanescent-mode attenuation check, and finite-array assembly from a cached unit-cell discretization.

Power electronics needs the partial inductance, resistance and capacitance of busbars, modules and hot loops. `flux::extract_rlcg(bodies, terminals, band)` solves magnetoquasistatic A–φ with terminal currents for partial inductance and AC resistance, and electrostatic boundary elements (through bempp-rs) or FEM for capacitance. It returns a `Field<(Ports, Ports, Frequency), Complex<Impedance>>` with its budget, from which ELX fits a passive SPICE subcircuit; unlike Ansys Q3D [Ansys Q3D], the extraction carries a bound and stays linked to the design.

### Fluids and free surfaces

Flow solvers must have adjoints, or Crucible's associative optimization stops at structures, so finite volume lives inside the form language.

**Decision D-FLX-51:** Cell-centred finite volume is the lowest-order discontinuous Galerkin form, DG(0), written in the form language: numerical fluxes are facet terms, and second-order reconstruction and limiters are facet-state operators in the kernel IR with generalized derivatives, so the compiler derives the discrete adjoint of every flow solver like any other form.
*Why:* a separate finite-volume code would have no adjoint, while STAR-CCM+ and Fluent users run adjoint shape optimization of ducts, heat sinks and aerodynamic surfaces [Siemens adjoint blog].
*Rejected:* a hand-written finite-volume solver beside the form language; finite volume only at `Preview` with stabilized FEM for every production flow.

Finite volume runs on cut cells and polyhedra with coupled pressure–velocity solves. Discontinuous Galerkin (DG) uses interior-penalty and upwind fluxes, and hybridizable DG couples only facet traces [Cockburn et al. 2009]. Mould filling uses a level set or volume of fluid, Hele-Shaw forms at `Interactive` and the wall resolution of the previous section. Flux provides wall-model interfaces, and COV the turbulence models (RANS, Reynolds-averaged Navier–Stokes; LES, large-eddy simulation).

Rotating machinery and electronics cooling need zone models. Rotating-frame source terms enter the flow forms (multiple reference frames: laminar in phase 3, RANS in phase 4), and sliding interfaces on the octree reuse the electromagnetic sliding interface in phase 4. Mixing-plane interfaces follow in phase 5. These are the three zone models Fluent offers [Fluent rotating zones]. `fan(face, curve: Field<VolumeFlowRate, Pressure>, swirl:)` and `resistance(region, K:)` are Network-coupled boundary and volume models, in phase 3 for GP5's enclosure.

Rotors, as on GP6's drone, have a three-rung ladder. Blade-element momentum theory with Prandtl tip losses is an Ingot package in `std::physics::rotor`. A vortex particle method runs on `fmm_apply` as a std Wasm component, with regularized particles and a stated core size. Rotating-domain flow uses the moving reference frame and sliding interface above. All three arrive in phase 4, and COV records their envelopes.

**Decision D-FLX-55:** Rotating machinery is served by one zone mechanism (rotating-frame source terms, sliding interfaces shared with electromagnetics, and mixing planes) plus a rotor ladder of blade-element momentum theory, a vortex particle method and rotating-domain flow.
*Why:* GP6 validates rotor thrust and torque, a drone engineer otherwise needs a second tool on day one, and sharing the sliding interface with motors avoids a second implementation.
*Rejected:* rotor aerodynamics only through External Op codes; a separate sliding-mesh implementation for flow.

### Lubrication

Gears and bearings need elastohydrodynamic lubrication (EHL): the Reynolds equation for film pressure with pressure-dependent viscosity, elastic deflection of the surfaces as a dense integral operator, and a cavitation complementarity condition. Flux solves it on a contact-surface Field, with deflection by `fft_solve` on the half-space or `hmatrix_apply`, and cavitation by semismooth Newton. COV keeps the Hamrock–Dowson film formulas as the phase 2 rung.

### General operations for non-variational methods

Flux's general operations serve COV's particle methods, ray tracing, boundary elements and ELX's placer through `crucible:ops/flux`, each with a canonical CPU path and, where it pays, a WGSL path. Random streams come from Kiln's `OpCx::rng`, keyed without class, fidelity or names ([contract section 7.2](../contract.md)).

Particle methods (DEM, the discrete element method; SPH, smoothed-particle hydrodynamics; MPM, the material point method; peridynamics) and lattice Boltzmann build on them, with errors from solution verification. Boundary elements build on bempp-rs, with fast multipole or H² compression and Calderón preconditioning for Maxwell [Scroggs et al. 2017].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Frequency-domain electromagnetics | Nédélec, ports, PML, bounded fast sweep | `SweepNotConverged { band }` | FLX-O-DISC-8 | 4 |
| S-parameter goals | Port S-parameters as DWR goals in class `em.sparam`, adaptive stopping on \|ΔS\| | `Undecided { needed }` when the requested \|ΔS\| is not reached | FLX-O-DISC-8 | 4 |
| FDTD | Conformal Yee with CPML | `CutFractionCapped { cells }` reported with its error | FLX-O-DISC-8 | 3 |
| Magnetodynamics with motion | A–φ and T–Ω; sliding interface or mortar | `SourceNotSolenoidal { coil }` | FLX-O-DISC-9 | 4 |
| Layered sheets | Thin-sheet conduction with through-plane `dI` | `SheetNotConnected { layer }` | FLX-O-DISC-6 | 3 |
| Plane-pair cavity model | 2D Helmholtz on sheet Bodies with port and via elements; complex LDLᵀ | `SingularOperator` at an unloaded cavity resonance | FLX-O-EM-3 | 4 |
| Periodic structures and arrays | Bloch-periodic pairs with scan phase; Floquet ports; finite arrays by domain decomposition | `EvanescentModeUnresolved { port }` | FLX-O-EM-1 | 5 |
| RLCG extraction | `extract_rlcg`: partial inductance, AC resistance, capacitance and conductance over a band, with budgets | `TerminalNotClosed { terminal }` | FLX-O-EM-2 | 4 |
| Boundary elements | Laplace, Helmholtz, Maxwell kernels with fast methods | `NotClosed { gaps }` from Anvil | FLX-O-DISC-12 | 3 |
| DG and hybridizable DG | Advection-dominated and high-order problems | `CflViolated { cell }` | FLX-O-DISC-1 | 3 |
| Finite volume and free surfaces | DG(0) forms for flow, filling and heat transfer, with derived adjoints | `NotConservative { cell, imbalance }` | FLX-O-DISC-10 | 3, 4, 5 (beyond filling) |
| Rotating zones, fans and resistances | Rotating-frame terms; sliding interfaces; mixing planes; `fan` and `resistance` models | `ZoneInterfaceMismatch { interface }` | FLX-O-FLOW-1 | 3 (laminar frames, fans), 4 (RANS frames, sliding), 5 (mixing plane) |
| Rotor aerodynamics | Blade-element momentum package; vortex particle method; rotating-domain flow | `OutsideEnvelope` per COV's rotor envelopes | FLX-O-FLOW-2 | 4 |
| Elastohydrodynamic lubrication | Reynolds equation with pressure–viscosity, FFT or H-matrix deflection, semismooth cavitation | `NonlinearDiverged` with the last film state | FLX-O-EHL-1 | 3 |
| General operations | BVH, neighbours, reductions, random streams, FMM, H-matrices, FFT | `kiln/work_limit` | FLX-O-DISC-11 | 2, 3 (FMM, FFT) |
| Lattice Boltzmann | D3Q19 and D3Q27 on sparse grids | `Unstable { step }` | FLX-O-DISC-11 | 4 |
| Particles and peridynamics | DEM, SPH, MPM, peridynamics | `Indicator` without solution verification | FLX-O-DISC-11 | 5 |

## Meshing and adaptivity

Anvil owns every mesh operation; Flux owns what drives them: sizing and metric Fields, estimation, marking and solution transfer. This section states that split and the interactive time budget an edit must meet.

Meshes, cut-cell sets and adaptation maps arrive keyed by `GeometryId` and canonical entity numbers, and `EntityId`s join only at the consumer.

[Reference](#what-flux-needs-from-anvil) lists the Anvil operations Flux calls and the phase of each.

Refinement is h (balanced octree, bisection, metric remeshing, hierarchical B-splines), hp (smooth cells raise p by Legendre decay, others split) or r (fitted meshes). The loop solve, estimate, mark, refine runs on declared goals with Dörfler marking at θ = 0.5, one node per iteration. Two stagnant iterations report a probable singularity.

### Interactive latency

Contract section 13.3 sets 1 s on the reference laptop for warm-started elasticity up to 100,000 DOFs at p = 2, including the estimates of up to five checked goals. The stage budgets below are targets.

| Stage | Owner | Budget |
| --- | --- | --- |
| Rebuild | Anvil | 150 ms |
| Queries and cell classification | Anvil | 200 ms |
| Setup | Flux | 80 ms |
| Solve | Flux | 300 ms |
| Goal estimates | Flux | 100 ms for the first goal, 20 ms for each further goal |
| Display | Flux | 80 ms |

Five goals therefore take 180 ms, and the total stays at 990 ms. That works because at `Interactive` Flux solves all goal adjoints at the primal degree p in one block-Krylov solve sharing the primal's preconditioner. It gets the DWR weights by patchwise higher-order reconstruction [Becker and Rannacher 2001]. Phase 0 measures the stages on GP1, GP2 and a named thin-walled part from the licence-filtered ABC subset, which GP5 takes over at the phase 3 gate.

**Decision D-FLX-56:** At `Interactive`, goal adjoints are solved at the primal degree in one block-Krylov solve sharing the primal's preconditioner, with weights from patchwise higher-order reconstruction, as their own calibration class; `SignOff` keeps adjoints one degree higher.
*Why:* one adjoint per goal at p + 1 costs more than the primal solve itself, so a part with several checks would miss the one-second target on every edit and fall back to `Proxy` or `Stale`.
*Rejected:* p + 1 adjoints at both fidelities; estimating only the first goal at `Interactive`.

**Decision D-FLX-37:** During a geometric drag, physics results show as `Proxy` where the change is affine on them, otherwise `Stale`, until the full update arrives in phases 1 and 2; from phase 3, reduced models on a fixed background discretization answer parametric geometric drags through a morphing map from `anvil::shape_velocity`.
*Why:* cell classification changes with geometry, so a reduced model built on one discretization needs a morph to answer for another.
*Rejected:* reduced-model answers for geometric drags in phase 1.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Sizing and metric Fields | `Field<Body, Length>`, `Field<Body, Metric>` from estimators | Anvil's `QualityNotReached { worst, target }` reported upward | FLX-O-MESH-1 | 2 |
| h-, p- and hp-adaptivity | Octree, fitted and spline refinement on declared goals | `ProbableSingularity { region }` on stagnation | FLX-O-MESH-1 | 1 (octree), 2, 3 (metric) |
| Solution transfer | Conservative projection, its error in the temporal part | `TransferAboveTolerance` refines the transfer | FLX-O-MESH-2 | 2 |
| Interactive stage budgets | Six stages within 1 s with five goals; block adjoints at p | A budget miss shows dependents as `Proxy` or `Stale` until the update arrives (KLN) | FLX-O-MESH-3 | 1 |
| Geometric drags | `Proxy`, then morphing reduced models | `TopologyChange` ends the morph | FLX-O-ROM-1 | 1, 3 (morphing) |
| Discretization Fields | Octree cells, cut and aggregated cells, polynomial degree and `ReductionKind` as `PerEntity` Fields for UIX's discretization view | None: the Fields are read from the plan and discretization that already exist | FLX-O-POST-2 | 1 |

## Solvers

Every discretization ends in linear, nonlinear, transient or eigenvalue problems, which Flux solves with its own deterministic solvers so the same bits come out in every class.

### Linear algebra

Matrix-free, sparse and block operators compose as `LinearOperator`s over libCEED's vector layouts, solved by fixed-restart Krylov methods.

**Decision D-FLX-36:** `Portable` linear algebra runs on the canonical `linalg` crate (machine-independent blocking, canonical lane order, no FMA, index-ordered pivot ties), and unmodified faer runs only in `CpuIsa`; FLX owns sparse factorization in `linalg`: supernodal elimination with tree-level parallelism and a fixed child order, independent of thread count and of upstream acceptance.
*Why:* faer sizes blocks from detected caches and uses FMA [faer documentation], so its bits differ by machine, and phase 1 cannot wait on an upstream review.
*Rejected:* unmodified faer in the canonical class; single-threaded canonical factorization.

Supernodal Cholesky and LDLᵀ factorizations serve symmetric problems to about 2M DOFs from phase 1. Block-triangular LU for Networks and mixed-precision `f32` factors with `f64` GMRES refinement follow in phase 2, complex LDLᵀ for indefinite Helmholtz and Maxwell problems in phase 3, and distributed direct solvers in phase 4 ([Reference](#solver-catalog)).

GMRES refinement extends LU refinement from κ₂ ≤ 10⁴ to 10⁸ for half-precision factors [Carson and Higham 2018]; the 10⁷ cutoff keeps κ · u_f32 below 1.

The DOF ceiling grows per phase. Phase 1 reaches 2M DOFs direct and several million matrix-free. Phase 2 meets contract section 13.3's `SignOff` row of 10M DOFs at p = 2 in under 10 minutes on the reference workstation, and phase 3 meets 50M DOFs on the 64-core server class. Distributed solves above about 5 × 10⁷ DOFs arrive in phase 4.

### Krylov methods and preconditioners

High-order elliptic problems on the octree use p-multigrid, then h-multigrid, then deterministic algebraic multigrid (AMG), with Schwarz smoothing on cut cells, from phase 1. Shells, H(curl) and H(div), Stokes and Navier–Stokes, DG transport, Helmholtz and distributed problems each get their own preconditioner in the phase listed in [Reference](#solver-catalog).

Low-order-refined de Rham preconditioners are spectrally equivalent independently of degree and mesh size [Pazner et al. 2022]. Global coarsening scales to 147,456 cores [Munch et al. 2022], and Schwarz-type smoothers handle small cut cells [de Prenter et al. 2019].

**Decision D-FLX-16:** Flux builds its own matrix-free p- and h-multigrid with global coarsening and deterministic AMG, with Schwarz smoothers and aggregation at cut cells, and keeps hypre and PETSc as optional bridges; AMG uses exact strength comparisons, fixed-order Galerkin products and independent-set priorities hashed from canonical DOF numbers through `random_stream`.
*Why:* AMG must coarsen identically in every class and run in Wasm, point smoothers fail on cut cells, and hashed priorities stay well mixed.
*Rejected:* mandatory hypre or PETSc; Jacobi smoothing on cut cells; priorities from names, threads or ranks.

**Decision D-FLX-33:** Navier–Stokes uses PCD (pressure convection–diffusion) or least-squares commutators at moderate Reynolds numbers, an augmented Lagrangian preconditioner at high ones, and dual splitting for high-order transients.
*Why:* pressure-mass Schur approximations suit only Stokes, and the augmented Lagrangian needs about 3 Krylov iterations per Newton step at Re = 1,000 and 5 at Re = 5,000 on a 10⁹-DOF cavity [Farrell et al. 2019].
*Rejected:* SIMPLE-type segregation as the only option.

### Nonlinear solvers and bifurcations

Newton–Krylov with exact Jacobians serves convex forms in phase 1 and every nonlinear form from phase 2. Trust-region Newton, arc length, semismooth Newton and Anderson acceleration arrive in phase 2, and pseudo-transient continuation in phase 3. ASPIN (additive Schwarz preconditioned inexact Newton) handles localized nonlinearity from phase 4 [Hwang and Cai 2005].

**Decision D-FLX-25:** From phase 2, Newton and arc-length solvers monitor the tangent's inertia (LDLᵀ inertia under a direct solver, else a warm-started LOBPCG estimate of the smallest eigenvalue per converged step) and return `Bifurcation { load, modes }` at a sign change instead of choosing a branch; in phase 1, Newton accepts only forms declared convex, verifies the declaration at every converged step by the same test, fails with `ConvexityViolated { step }` when it does not hold, and returns `Unsupported { reason: NoBifurcationMonitor }` for forms not declared convex; branches follow only an explicit imperfection or `branch: follow(mode: k, sign: +)`.
*Why:* rounding decides which branch Newton follows, and an unchecked convexity declaration would let a wrong one choose a branch silently.
*Rejected:* silent branch choice; unchecked declarations; an eigensolve per load step.

Limit points are reported likewise, and electro-thermal runaway returns `Runaway { power }`.

### Time integration

Backward differentiation formulas, SDIRK and IMEX Runge–Kutta schemes and generalized-α arrive in phase 2; explicit central-difference, SSP Runge–Kutta and symplectic schemes in phase 3; exponential and parallel-in-time integrators in phase 5 ([Reference](#solver-catalog)).

Temporal goal error is the adjoint-weighted residual in time. Summed local estimates are `Indicator`, because phase error accumulates in oscillatory problems; step halving with frozen breakpoints is the calibrated alternative, also for ELX's circuit transients. Events are root-found on dense output.

### Eigenvalue problems

Shift-invert Lanczos with Krylov–Schur restarts and LOBPCG ship in phase 1 for modal analysis and buckling ([contract section 13.4](../contract.md)). Prestressed, damped and gyroscopic eigenproblems follow in phase 2 with linear dynamics, flutter linearizations in phase 3, and contour-integral solvers in phase 4. Eigenvectors are mass-normalized with the largest entry positive, and degenerate eigenspaces are returned as subspaces.

**Decision D-FLX-41:** Frequency checks rest on a DWR eigenvalue estimate [Heuveline and Rannacher 2001] applied two-sided (λ_h − η for lower limits, λ_h + η for upper limits and resonance-avoidance bands) and calibrated on |λ_h − λ|, with the one-sided reading only on fitted conforming discretizations with strong Dirichlet conditions; buckling factors are coupled goals whose estimate adds the static adjoint driven by ∂μ/∂u = φᵀ(∂K_G/∂u)φ; K_G is assembled so that compressive prestress contributes a negative-semidefinite term, Flux solves −K_G φ = μ K φ, and λ₁ = 1/μ_max over μ > 0; the algebraic part comes from Kato–Temple or Lehmann bounds with the gap from the next Ritz value.
*Why:* Nitsche conditions, ghost penalties and calibrated beam joints are not a conforming Ritz method, so discrete eigenvalues can fall below the exact ones; the geometric stiffness depends on the static solution, whose error a fixed-operator estimate leaves out; and an unstated sign convention lets two implementations compute different modes.
*Rejected:* a one-sided bound everywhere; a solver name as a calibration class; `Guaranteed` eigenvalue bounds on cut cells.

`Guaranteed` lower bounds exist for the Laplacian on fitted simplices with the nonconforming Crouzeix–Raviart element [Carstensen and Gedicke 2014]. Flux ships them in phase 3 for acoustic-cavity eigenvalues, which MEC's resonance-avoidance checks for enclosures and COV's linear acoustics read. `flux::koiter_coefficient` computes a shell buckling mode's initial post-buckling coefficient for COV's imperfection-sensitivity variable, in phase 2 with nonlinear shells.

### GPU solves, CPU certifies

**Decision D-FLX-17:** A GPU solve produces a Field pinned by `ObjectId`, and the `Portable` `flux::certify` recomputes its residual and budget in the canonical class in `f64`, so the outcome is canonical although the Field's bits are not; `f32` inner solves run in defect correction on the CPU residual and fall back to a canonical CPU solve after two cycles that contract by less than 2.
*Why:* Metal and WebGPU lack `f64`, and defect correction stalls as κ(A) · u_f32 approaches 1.
*Rejected:* uncertified `f32` results; forbidding GPUs at `SignOff`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Canonical direct solvers | Supernodal LLᵀ and LDLᵀ, block-triangular LU, complex LDLᵀ | `SingularOperator { null_space_hint }` | FLX-O-SOLVE-1 | 1, 2 (LU), 3 (complex) |
| Multigrid and AMG | p- and h-multigrid, Schwarz smoothers on cut cells, deterministic AMG | `LinearDiverged { residual_history }` | FLX-O-SOLVE-2 | 1 |
| Navier–Stokes preconditioners | PCD, LSC, augmented Lagrangian, dual splitting, AIR | `LinearDiverged`, preconditioner named | FLX-O-SOLVE-3 | 3, 4 |
| Electromagnetic and Helmholtz solvers | Auxiliary-space AMG, complex LDLᵀ, optimized Schwarz, shifted-Laplacian multigrid | `LinearDiverged` | FLX-O-DISC-8 | 3 |
| Nonlinear solvers | Newton, trust region, arc length, semismooth Newton, ASPIN; convexity verified in phase 1 | `NonlinearDiverged` with the last state; `ConvexityViolated { step }`; `Unsupported { reason: NoBifurcationMonitor }` | FLX-O-SOLVE-4 | 1 (convex forms), 2, 4 (ASPIN) |
| Bifurcation detection | LDLᵀ inertia or warm-started LOBPCG | `Bifurcation { load, modes }`; `Runaway { power }` | FLX-O-SOLVE-4 | 2 |
| Time integrators | Implicit, IMEX and explicit schemes with events | `StepTooSmall { t }` | FLX-O-SOLVE-5 | 2, 3 |
| Eigen-solvers | Lanczos and LOBPCG with the stated buckling convention; Krylov–Schur; contour integrals | `NotConverged { found, wanted }` | FLX-O-SOLVE-6 | 1, 2 (prestressed, damped, gyroscopic), 4 (contour) |
| Eigenvalue lower bounds | Crouzeix–Raviart lower bounds for acoustic cavities | `NotConverged { found, wanted }` | FLX-O-SOLVE-6 | 3 |
| Koiter coefficient | Post-buckling coefficient of a shell mode | `NotConverged { found, wanted }` | FLX-O-SOLVE-6 | 2 |
| GPU solve with CPU certification | Pinned GPU Field; canonical residual and budget | A stall falls back to the canonical CPU solve | FLX-O-SOLVE-8 | 2 |
## Idealizations, contact and constraints

An analyst rarely models every part as a solid. A motor on a bracket becomes a point mass on a remote point, a clevis becomes a load through a rigid coupling, and a board on standoffs becomes springs. This section gives Flux those idealizations, with the same associativity and error accounting as everything else, and then the contact and constraint machinery beneath them.

### Idealizations

Each idealization is an Ingot function over `Query` targets, so it follows the design through every edit and appears in the study's source like a load or a support.

```
let motor = remote_point(p.faces(role: mount_pads), at: motor_frame, behavior: Distributing { weight: Area })
let m = point_mass(at: motor, m: 1.8kg, J: motor_inertia)
let feet = spring(p.faces(role: feet), ground, k: mount_stiffness, c: mount_damping)
let study = modes(p, fixed: [], idealizations: [m, feet], count: 12)
```

- `remote_point(faces, at: CoordSys, behavior:)` couples faces to a reference point with six degrees of freedom. `Rigid` keeps the faces' shape, like Nastran's RBE2; `Distributing { weight: Uniform | Area | Distance }` transfers load without adding stiffness, like RBE3. It takes forces, moments, displacements, masses and springs.
- `point_mass(at:, m:, J:)` places a mass with a rotary inertia tensor at a remote point or vertex. MEC's mass-property checks include it.
- `spring(a, b, k:, c:)` connects two points, or a point and ground, with six-by-six stiffness and damping tensors.
- `bushing(a, b, curves:)` adds nonlinear force–deflection and moment–rotation curves per axis, in phase 2.
- `fastener(holes, spec)` builds a beam connector with distributing couplings at each hole from MEC's fastener Instance sets, with VDI 2230 preload, and `spot_weld(points, d:)` a short beam of the nugget diameter; both in phase 2.

These are the objects an Ansys or Nastran user reaches for. Ansys documents rigid and deformable remote points as like the CERIG and RBE3 constraints [Ansys remote points]. It exports remote points, bushings and point masses as RBE2, RBE3, CBUSH and CONM2 cards [Ansys Nastran export].

**Decision D-FLX-47:** Idealizations (remote points with rigid or distributing behaviour, point masses with rotary inertia, grounded and two-point springs and dampers, bushings, fasteners and spot welds) are Ingot functions over `Query` targets, enforced by multipliers on fitted meshes and by Nitsche terms on the octree, and a distributing coupling adds no stiffness.
*Why:* analysts model attached equipment and unmodelled parts this way in nearly every incumbent model, and modelling them as solids is slower, changes the answer at the attachment and breaks modal mass.
*Rejected:* modelling every attachment as a solid; idealizations as mesh-node objects that break when the geometry changes.

Rigid couplings stiffen thin walls they attach to. COV therefore carries a regime variable, coupling-region diameter over local wall thickness, that flags a rigid coupling on a thin wall.

### Tied interfaces in assemblies

The commonest analyst task is a static or modal solve of an assembly with bonded and sliding interfaces. Flux gives it a path on the immersed octree from phase 2, so assemblies keep the no-meshing advantage.

**Decision D-FLX-52:** Touching faces between Instances, found from MEC's interference classes within the definition tolerance, become `dI` interfaces tied by Nitsche terms on the octree: `Bonded` by default for welded or glued joints and `NoSeparation` (tangential sliding with normal contact held) for other touching pairs, each listed for confirmation in UIX's pre-flight; frictionless and frictional contact with separation use mortar on fitted meshes from phase 2 and Nitsche on the octree from phase 3.
*Why:* bonded and no-separation ties are linear, so they keep a static or modal assembly solve linear and immersed, while separation and friction need the nonlinear contact machinery; Abaqus users expect automatic interface detection of this kind [Abaqus general contact].
*Rejected:* fitted meshes for every assembly before phase 3; silent interface choices without confirmation.

### Contact, constraints and fracture

Constraints are strong on fitted meshes and Nitsche-imposed on immersed and spline discretizations from phase 1. Mortar contact on fitted meshes arrives in phase 2, immersed and large-sliding contact in phase 3, and Incremental Potential Contact for GP16's soft goods in phase 5 [Li et al. 2020]; [Reference](#method-catalogs) gives each enforcement.

Penalty results support `SignOff` only with an estimated penetration below tolerance. Bolted-joint forms (preloaded bolt elements and joint springs) serve COV's VDI 2230 model in phase 2. Fracture hooks carry COV's models: J-integrals in phase 2, cohesive zones in phase 3, phase field in phase 4, and cut-cell cracks and peridynamics in phase 5.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Remote points | `remote_point` with `Rigid` or `Distributing` behaviour; six-DOF reference point | `CouplingOnFlaggedSet { faces }` when the coupled region meets a singular set | FLX-O-IDEAL-1 | 1 |
| Point masses | `point_mass` with rotary inertia at a remote point or vertex | `NotPositiveDefinite { inertia }` | FLX-O-IDEAL-1 | 1 |
| Springs and dampers | Grounded and two-point six-by-six stiffness and damping | `NotPositiveSemidefinite { stiffness }` | FLX-O-IDEAL-1 | 1 |
| Bushings | Six-DOF connectors with nonlinear curves per axis | `CurveOutOfRange { axis, value }` | FLX-O-IDEAL-2 | 2 |
| Fastener and spot-weld connectors | Beam connectors with distributing couplings from MEC's fastener Instance sets; VDI 2230 preload; spot welds | `JointOpened { bolt }`, with mortar contact as the fix | FLX-O-IDEAL-2 | 2. Requires: MEC Fasteners |
| Immersed tied interfaces | Automatic detection; `Bonded` and `NoSeparation` Nitsche ties on the octree, confirmed in pre-flight | `UnconfirmedInterface { pair }` blocks `SignOff` | FLX-O-IDEAL-2 | 2. Requires: MEC Static interference |
| Contact and constraints | Mortar, Nitsche, augmented Lagrangian, estimated penalty; IPC | `PenetrationAboveTolerance` blocks `SignOff` | FLX-O-SOLVE-7 | 1 (constraints), 2, 3, 5 (IPC) |
| Bolted-joint forms | Preloaded bolt elements and joint springs for COV's VDI 2230 model | `JointOpened { bolt }`, with mortar contact as the fix | FLX-O-SOLVE-9 | 2 |
| Fracture hooks | J-integrals, cohesive zones, phase field, cut-cell cracks, carrying COV's models | `CrackPathOutsideDomain { front }` | FLX-O-SOLVE-10 | 2, 3, 4, 5 |

## Linear dynamics

Sine sweeps, random vibration on a shaker, shock spectra and prestressed modes are the daily work of Nastran and Ansys users [Ansys Mechanical]. This section gives Flux that workflow, with damping as data and with the error a near-resonant response amplifies stated in the budget.

### Prestress, damping and gyroscopic terms

A linear perturbation starts from a converged static or nonlinear state: modes and buckling factors then include stress stiffening from preload or pressure, spin softening, and pressure load stiffness. Damped and gyroscopic eigenproblems serve COV's rotordynamics (Campbell diagrams) and vibration rows. A base state that has not converged fails with `BaseStateNotConverged`.

Damping is data on Materials and joints: `Damping::Modal(ζ)`, `Rayleigh { alpha, beta }`, `Structural(η)` for hysteretic loss, and `Viscoelastic(Field<Frequency, Complex<YoungsModulus>>)` for frequency-dependent materials.

### Frequency, random and shock response

- **Frequency response.** Direct, or by mode superposition with residual vectors, returning `Field<(Body, Frequency), Complex<V>>`.
- **Base excitation.** Enforced base motion by the large-mass method or by Lagrange multipliers.
- **Random vibration.** Power spectral density (PSD) inputs at one or several points with their correlation, returning 1σ and 3σ Fields and spectral moments; a Miles-equation check guards single-mode cases.
- **Response spectrum.** Single- and multi-point spectra, combined by SRSS (square root of the sum of squares), CQC (complete quadratic combination) or NRL rules, with a missing-mass correction.

**Decision D-FLX-49:** Linear dynamics is mode superposition with residual vectors or a direct solve, with damping as typed Material and joint data; modal truncation files under `reduction or surrogate` with a residual-flexibility estimate in class `dynamics.modal`, and the discretization part is propagated through the frequency-response function from the eigenvalue estimates and inflated by 1/(2ζ) inside each half-power band.
*Why:* near resonance a small frequency error becomes a large amplitude error, which a budget that ignored damping would hide, and missing mass is the error analysts check by hand.
*Rejected:* undamped harmonic response by default; truncation without a residual correction; damping as untyped analyst input.

A response whose band holds an undamped resonance fails with `UndampedResonance { mode, frequency }`. Missing mass above 10% fails with `ModalTruncation { missing_mass }`, whose fix adds modes or residual vectors. COV's vibration fatigue rows read the PSD outputs.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Linear perturbation | Modal and buckling about a converged state, with stress stiffening, spin softening and pressure load stiffness | `BaseStateNotConverged` | FLX-O-DYN-1 | 2 |
| Damped and gyroscopic eigenproblems | Quadratic eigenproblems with damping and gyroscopic terms, for Campbell diagrams | `NotConverged { found, wanted }` | FLX-O-DYN-1 | 2 |
| Frequency response | Direct and mode-superposition response with residual vectors; truncation part in the budget | `ModalTruncation { missing_mass }` above 10% | FLX-O-DYN-2 | 2 |
| Enforced base motion | Large-mass and Lagrange-multiplier methods | `BaseNotConstrained { dofs }` | FLX-O-DYN-2 | 2 |
| Random vibration | PSD inputs at one or several points with correlation; 1σ and 3σ Fields; spectral moments | `ModalTruncation { missing_mass }` above 10% | FLX-O-DYN-2 | 2 |
| Response spectrum | Single- and multi-point; SRSS, CQC and NRL combination; missing-mass correction | `ModalTruncation { missing_mass }` above 10% | FLX-O-DYN-3 | 2 |
| Damping models | Modal, Rayleigh, structural and viscoelastic damping on Materials and joints | `UndampedResonance { mode, frequency }` inside a response band | FLX-O-DYN-2 | 2 |

## Networks, multibody dynamics and rods

Many systems are best modelled as lumped elements or moving rigid and flexible bodies rather than fields. This section states how Flux compiles and integrates them, in every physical domain, with the same derivatives and determinism as its field solvers.

### Networks

ELX owns the `network { … }` builder, the element libraries and the electrical fast path; Flux compiles and integrates Networks in every domain. `flux::compile_network` flattens the hierarchy, applies index reduction, compiles each reachable mode of a switched network once and emits residuals and Jacobians in the kernel IR. Because Kiln caches each per-mode compilation, an edit of one parameter or one element re-translates only what it touches.

`flux::solve_dae` integrates the resulting differential-algebraic equations (DAE) with variable-order backward differentiation formulas and trapezoidal rules, events, consistent reinitialization and adjoints on the block-triangular LU. Network solves are `F64Required`, Monte Carlo batches run one sample per SIMD lane, and results are Fields over `(Ports, Time)` or `(Ports, Frequency)`.

**Decision D-FLX-27:** Networks compile to index-1 DAEs by Pantelides reduction with static dummy-derivative selection per mode, BLT ordering, tearing and cached per-mode compilations, and states are re-selected only at a deterministic event, when a pivot test shows the selected block singular.
*Why:* one structural analysis is invalid after a mode change, and re-selection between events would make results depend on solver history.
*Rejected:* Pantelides without dummy derivatives [OpenModelica flags]; one analysis for a switched network.

Targets: re-translation of a 50,000-equation Network after a one-parameter or one-element edit under 1 s, and full translation within 2 times of OpenModelica.

### Multibody dynamics

MEC hands over an Assembly with typed joints, a redundancy report, bounded mass properties, contact pairs and drivers, and `flux::solve_multibody` integrates it [Brüls et al. 2012].

- Joint axes expose ports, so a motor drive's Network drives a joint directly.
- Contact is compliant with regularized Coulomb friction until phase 4 brings the nonsmooth generalized-α scheme [Brüls et al. 2014].
- Flexible bodies are Craig–Bampton reduced Parts or exact beams; results are `Field<(Instances, Time), Transform>`, joint loads and an energy balance.
- `flux::linearize_multibody` returns exact plant Jacobians at an operating point for ELX's control design.

MFG's assembly planner uses the same solver's quasi-static contact equilibrium.

**Decision D-FLX-28:** Multibody dynamics is an index-3 DAE on the Lie group of rigid motions, integrated by Lie group generalized-α with scaled constraints, with redundancy removed by rank-revealing QR.
*Why:* no rotation parameterization means no singular configurations, and the method is second-order in every unknown without index reduction.
*Rejected:* Euler-angle or quaternion coordinates, which bring singularities or normalization drift; Baumgarte-stabilized ODEs, which drift and need tuning.

### Cosserat rods

`flux::solve_rod` serves cables, harnesses and hoses [Gazzola et al. PyElastica] with trust-region Newton statics, Lie group generalized-α dynamics and contact through Anvil distance queries. MEC's harness model uses the Kirchhoff limit.

**Decision D-FLX-29:** Cables and hoses are geometrically exact Cosserat rods sharing the multibody integrator, with Kirchhoff behaviour as the stiff-shear limit.
*Why:* hoses stretch and shear under pressure and clamping, and one integrator couples rods to joints and contact.
*Rejected:* inextensible Kirchhoff rods only; spring–mass chains, which converge poorly in bending and torsion.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `flux::compile_network` | Flattening, index reduction with dummy derivatives, BLT, tearing, per-mode compilation, incremental re-translation | `StructurallySingular { equations }`; `HighIndexAfterReduction` | FLX-O-NET-1 | 2 |
| `flux::solve_dae` | Index-1 DAE: backward differentiation, trapezoidal rule, events, reinitialization, adjoints | `ReinitFailed { event }`; `StepTooSmall { t }` | FLX-O-NET-2 | 2 (mechanical, thermal), 3 (electrical) |
| Block-triangular sparse LU | Per-block ordering; numeric refactorization; complex arithmetic | `SingularOperator { block }` | FLX-O-NET-3 | 2 |
| `flux::solve_multibody` | Typed joints, redundancy handling, compliant contact, Network-driven joints | `InconsistentRedundancy { joints }`; `Bifurcation` at toggle points | FLX-O-MBD-1 | 2 (rigid), 3 (flexible), 4 (nonsmooth) |
| `flux::linearize_multibody` | Exact plant Jacobians at an operating point; `Differentiable` | `NotDifferentiable { op }` at contact events | FLX-O-OPT-1 | 4 |
| `flux::solve_rod` | Cosserat statics and dynamics with contact | `NonlinearDiverged` with the last state | FLX-O-MBD-2 | 4 |

## Coupling, homogenization and co-simulation

Real products couple physics (heat bends a part, current heats a conductor) and exchange models with other tools, so Flux couples Fields, scales between lattice and part, and co-simulates through open standards.

Monolithic coupling solves one product-space form by Newton with field-split preconditioning; partitioned coupling exchanges interface Fields until they agree. One-way thermal stress ships in phase 1, two-way thermo-mechanics in phase 2 and laminar conjugate heat transfer in phase 3. Electro-thermal, turbulent conjugate heat transfer, electromagnetic–structural and fluid–structure coupling follow in phase 4 ([Reference](#method-catalogs)).

Element activation switches cells on by layer group (additive manufacturing) or weld group, both in phase 2 ([contract section 13.4](../contract.md)), and transiently for joint-scale welding in phase 4. Interface transfer is conservative for fluxes and consistent for states, the interface residual joins the algebraic budget, and preCICE serves only as an external tool [preCICE].

**Decision D-FLX-42:** Additive distortion by inherent strain is a declared sequence (layer-group activation of part and supports, baseplate cut, support removal and optional stress relief), with stress relief scaling the strain by a calibrated relaxation factor, supports as a homogenized lattice of calibrated stiffness, and every step's data from MFG's coupons, such as cantilevers cut from the plate.
*Why:* the measured shape of a printed part follows cutting, support removal and stress relief, not the build alone.
*Rejected:* activating the part alone; inherent strain in phase 1, before Crucible models supports.

**Decision D-FLX-43:** On beam-modelled frames, weld shrinkage enters as equivalent joint loads per weld (longitudinal force, transverse shrinkage and angular distortion), computed by inherent strain on a local shell or solid joint model that `mark_reduction` keeps at each welded joint, from MFG's coupon strains per joint type, thickness, process and heat input, enveloped by heat input per length and plate thickness.
*Why:* inherent strain is undefined on a beam, and GP4's welds sit at joints that a beam model reduces to nodes.
*Rejected:* solid frames; macrograph-calibrated heat sources, which belong to the phase 4 transient model.

### Homogenization and lattices

`flux::homogenize` solves periodic unit cells and returns effective tensors as `Reduced` or `Surrogate` Fields with bounds, and `flux::localize` rebuilds the strut stresses that lattice checks read. For COV's lattice envelope Flux computes cell size over gradient length, boundary distance in cells, and strut slenderness times compressive strain against a Bloch-wave bound. Critical lattice regions sign off on beam lattices or sheet shells; dehomogenization runs through Anvil in phase 2, and FE² batches micro solves in phase 5.

### Co-simulation over FMI and SSP

**Decision D-FLX-30:** Flux owns the runtime of FMI 3.0.2 (the Functional Mock-up Interface) and SSP 2.0.1 (System Structure and Parameterization): import, export, master algorithms and Model Exchange integration; native-binary FMUs (Functional Mock-up Units) run as External Ops on untrusted-evaluation workers, and FMUs with determinized Wasm binaries run in the sandbox as ordinary Ops.
*Why:* native FMUs are untrusted code ([contract section 7.8](../contract.md)), and one runtime avoids duplicate FMI implementations across tabs [FMI 3.0.2].
*Rejected:* native FMUs in the sandbox; per-tab FMI runtimes.

ELX keeps FMU elements and the FMI layered bus standard, and ECO keeps packaging [SSP standard]. Flux runs each imported FMU twice in CI; one whose outputs differ is `NonDeterministic` and never shared.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Monolithic and partitioned coupling | Product-space forms; Aitken and interface quasi-Newton; conservative transfer | `CouplingDiverged { residual_history }` | FLX-O-COUP-1 | 1 (one way), 2, 3, 4, 5 per coupling |
| Conjugate heat transfer | Robin partitioned, or monolithic on a shared octree with wall refinement | `CouplingDiverged { residual_history }` | FLX-O-COUP-1 | 3 (laminar, natural convection), 4 (turbulent) |
| Electro-thermal coupling | Joule heating with temperature-dependent resistivity; monolithic Newton with continuation | `Runaway { power }` at the turning point | FLX-O-COUP-1 | 4 |
| Element activation | Cells activated by a layer or time Field | `ActivationGap { layer }` | FLX-O-COUP-1 | 2 (layer and weld groups), 4 (transient) |
| Additive distortion sequence | Activation with supports, baseplate cut, support removal, stress relief | `OutsideEnvelope` outside the coupon data | FLX-O-COUP-4 | 2 |
| Weld joint loads on frames | Joint loads from local joint models and coupon inherent strains | `OutsideEnvelope` outside the coupon envelope | FLX-O-COUP-4 | 2 |
| Homogenization | Unit-cell solves to effective-tensor Fields | `NotPeriodic { faces }` | FLX-O-COUP-2 | 1 (elastic), 3 |
| Localization and lattice regimes | Micro stresses; scale, boundary-distance and buckling regime Fields | Zones `Invalid` or `Flag` per COV | FLX-O-COUP-2 | 1 |
| FE² | Batched micro solves per macro quadrature point | `MicroDiverged { point }` | FLX-O-COUP-2 | 5 |
| FMU import (all three interface types) | External Op or sandboxed Wasm; provided directional and adjoint derivatives | `NoBinaryForPlatform { available }`; stated finite differences otherwise | FLX-O-COUP-3 | 3 |
| FMU export and SSP | Co-simulation FMUs with state serialization; SSP archives to and from Ingot | `UnknownLayeredStandard { name }` kept and reported | FLX-O-COUP-3 | 4 |
| Master algorithms | Jacobi, Gauss–Seidel, variable step with rollback, clocked partitions | `NoRollback { fmu }` runs that FMU fixed-step, stated | FLX-O-COUP-3 | 3 |

## Gradients and optimization

Every Flux solve is differentiable, so a design parameter, a density Field or a shape can be optimized against any check. This section states how gradients are formed, what they are exact for, and the optimizers built on them.

Flux differentiates the discretized problem from its forms [Farrell et al. 2013]. Kiln chains `Differentiable` operations backward from a scalar goal, and geometry enters through `anvil::shape_velocity`, which returns `TopologyChange` where the topology would change. `grad(J, wrt: [p1, p2])` and `hessian_vector(J, wrt: p, v)` return values bounded by the forward and adjoint algebraic parts and the discretization-consistency gap.

**Decision D-FLX-21:** Gradients are derivatives at a frozen discretization (cells, aggregation map, adaptive marks and time steps); the bound says so, Taylor tests that straddle a discretization change are flagged, and optimization plans use a smooth aggregation weight instead of the hard switch.
*Why:* the discrete objective is not differentiable where the discretization changes, and pretending otherwise produces gradients an optimizer cannot trust.
*Rejected:* exact gradients across discretization changes; operator-overloading differentiation of solver code; continuous adjoints.

A steady adjoint costs at most one forward solve and ships in phase 1. Eigenvalue and transient adjoints follow in phase 2, laminar flow adjoints in phase 3, and turbulent, contact and coupled adjoints in phases 3 and 4 ([Reference](#method-catalogs)).

Transient adjoints use the CAMS checkpointing of Zhang and Constantinescu [Zhang and Constantinescu 2021], stored in Kiln's `StepState` retention tier by (`NodeKey`, step), so an objective-only change reuses them.

### Topology optimization

Density methods by SIMP (solid isotropic material with penalization) on the immersed octree ship in phase 1 for compliance and volume, under additive and unrestricted constraints. Stress, robust designs and the other manufacturing methods follow in phase 2. Graded lattices, shell sizing, level sets, multiphysics and laminate optimization follow in the phases [Reference](#method-catalogs) lists.

The optimizer is the method of moving asymptotes (MMA) [Svanberg 1987] with a globally convergent variant, implemented natively from the papers as `flux::mma_step`. The loop is Ingot (`std::opt::topology`), so iterations are cached nodes. Results include `design.geometry_density`, the filtered, projected H¹ density with the gradient bound `anvil::implicit_from_field` requires. Stress constraints aggregate regularized stresses by p-norms, and manufacturing constraints take their limits as arguments, read from MFG's process profiles from phase 2.

```
use std::opt::topology::{minimize, compliance, volume_fraction, density, overhang}

let design = minimize(
    compliance(space, loads: [case_a, case_b]),
    over: density(space, filter: 1.5mm, projection: robust),
    subject_to: [volume_fraction <= 0.3, overhang(build_dir: +z, max: 45deg)],
    fidelity: SignOff,
)
let lattice_part = anvil::implicit_from_field(design.geometry_density, iso: 0.5)
```

MEC's `std::mech::generate` turns this machinery into the generative-design workflow Fusion users know, with one outcome per manufacturing method [Fusion manufacturing methods]. Flux supplies each method's constraint. Additive limits overhang and feature size, milling requires tool access along declared axes, two-axis cutting keeps a constant cross-section along the cut, and casting forbids undercuts along the draw direction. Kept interfaces stay exact, named and toleranced B-rep faces in every outcome.

Released geometry must be `Portable`, so `SignOff` optimization runs in the canonical class and GPUs accelerate only `Interactive` exploration. Targets are 10⁸ density elements on a 64-core server and 10⁹ on a cluster [Aage et al. 2017].

### Shape, parameter and experimental design

Shape optimization works on feature parameters through the geometry chain rule, or on boundary-morphing Fields by the moving-mesh method [Paganini and Wechsung 2021]. Optimizers are L-BFGS-B, SQP (sequential quadratic programming), interior point, MMA, trust region, CMA-ES (covariance matrix adaptation) and NSGA-II-type search, drawing randomness from Kiln's `OpCx::rng`; Bayesian optimization belongs to AGT. `std::sim::study` runs designs of experiments, one node per point.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Form- and operation-level derivatives | `Differentiable` tangents and adjoints chained by Kiln; `grad`, `hessian_vector` | `NotDifferentiable { op }`; straddling tests flagged | FLX-O-OPT-1 | 0 (forms), 1 |
| Adjoints | Steady, eigen, transient with checkpointing, contact, coupled | None: missing step state is recomputed (KLN) | FLX-O-OPT-3 | 1, 2, 3, 4 per problem |
| Flow adjoints | Laminar steady adjoint from DG(0) and DG forms; frozen-turbulence and full RANS adjoints | `NotDifferentiable { op }` at a limiter switch, flagged in the Taylor test | FLX-O-OPT-4 | 3 (laminar), 4 (RANS) |
| Shape gradients | Chain rule through `anvil::shape_velocity` | `TopologyChange { parameter, entities }` | FLX-O-OPT-1 | 2. Requires: ANV `anvil::shape_velocity` |
| Density topology optimization | SIMP, filters, projection, MMA; `geometry_density` | `Infeasible { constraints }` with the closest feasible design | FLX-O-OPT-2 | 1. Requires: ANV `anvil::implicit_from_field` |
| Manufacturing constraints | Additive and unrestricted; milling access by axes and tool, two-axis cutting and casting draw | `Infeasible { constraints }` with the closest feasible design | FLX-O-OPT-6 | 1 (additive, unrestricted), 2 |
| Shell sizing and laminate optimization | Thickness Fields on shells; ply shape, ply drops and stacking under MEC's ply rules | `Infeasible { constraints }` with the closest feasible design | FLX-O-OPT-5 | 2 (sizing), 6 (plies) |
| Level-set and multiphysics topology optimization | Shape and topological derivatives; coupled adjoints | `Infeasible { constraints }` with the closest feasible design | FLX-O-OPT-2 | 3, 4 |
| Optimizers and experimental designs | Gradient, evolutionary and multi-objective optimizers; designs of experiments | `NotConverged { iterations }` with the best design | FLX-O-OPT-2 | 1 (MMA), 2 |
## Uncertainty quantification

Tolerances, scatter in material data and uncertain loads move every result, and a check that ignores them passes parts that fail in service. This section states how Flux propagates `Tol<T>` worst case by default and how statistical methods run when asked for.

Sampling methods arrive in phase 2. Multilevel Monte Carlo (MLMC), sparse polynomial chaos (PCE), Sobol and Shapley sensitivity [Song et al. 2016], rare-event methods with FORM (the first-order reliability method) and probability boxes arrive in phase 3 ([Reference](#method-catalogs)).

Multilevel Monte Carlo fits immersed plans, which already have level hierarchies [Giles 2015].

**Decision D-FLX-35:** Propagating `Tol<T>` through physics is worst case by default: `std::uq::worst_case` sums half-widths times absolute adjoint sensitivities over correlated noise symbols, confirms the result with one solve at the vertex the signed sensitivities select, and estimates curvature by Lanczos with a random start on the Hessian over the scaled box; when the confirmed value minus the linear prediction stays within the remainder estimate, the bound is `Estimated { Statistical { method: lanczos_random_start, α: 0.01 } }` with the probabilistic Lanczos bound [Kuczyński and Woźniakowski 1992], and otherwise the result is `NonlinearResponse { ratio }`.
*Why:* a few Lanczos steps give Ritz values inside the spectrum, so a remainder from them underestimates; a stationary response has a zero linear term that one Hessian-vector product misses; and the confirming solve tests the linear prediction where it matters most.
*Rejected:* a uniform-distribution default; Monte Carlo for worst cases; a curvature remainder labelled `Estimated` without a method or α.

Statistical propagation is an explicit `std::uq::propagate` call, with MEC's default distribution and skin-model samples. Flux supplies influence coefficients for MEC's compliant variation analysis in phase 2.

```
let stress = study.von_mises.max(over: study.regular())
let worst = std::uq::worst_case(stress, inputs: tolerances(p))              // Approx<Stress>
let stats = std::uq::propagate(stress, inputs: tolerances(p), method: mlmc)
p.require(stats.quantile(0.999) < 0.6 * p.material.yield_strength(at: 20degC), name: "static_quantile")
```

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Worst-case tolerance propagation | Adjoint-linearized affine bounds, a confirming vertex solve and a probabilistic Lanczos remainder | `NonlinearResponse { ratio }` asks for a statistical method | FLX-O-UQ-3 | 2 |
| Sampling methods | Monte Carlo, randomized QMC, MLMC, multi-model | `BudgetTooSmall { samples }` before running | FLX-O-UQ-2 | 2, 3 |
| Polynomial chaos and sensitivity | Sparse PCE; grouped Sobol indices; Shapley effects | `DependentInputs` for plain Sobol on correlated inputs | FLX-O-UQ-1 | 3 |
| Rare events and reliability | Subset simulation, cross-entropy sampling, confirmed FORM | `NotConverged { cov }` | FLX-O-UQ-1 | 3, 4 |
| Epistemic inputs | Probability boxes by nested sampling | `MixedUncertaintyKinds` when a caller sums an interval with a distribution | FLX-O-UQ-1 | 3 |
| Influence coefficients | Compliance at measurement points for MEC | `SingularOperator` without supports | FLX-O-UQ-3 | 2 |

## Reduced models and surrogates

A full solve per query is too slow for drags, sweeps, system models and design exploration. Reduced models and surrogates answer faster, and this section states how far each may be trusted: a surrogate never decides a `SignOff` check without a bound in the check's norm or a confirming solve.

Modal and Craig–Bampton models arrive in phase 2. POD (proper orthogonal decomposition) with DEIM hyper-reduction [Chaturantabut and Sorensen 2010], certified reduced bases [Huynh et al. 2007], Krylov moment matching and morphing models follow in phase 3 ([Reference](#method-catalogs)).

A reduced model records its parameter box, and a query outside it fails with `OutsideParameterBox { parameter, range }` unless the caller requests a full solve.

### Surrogates

Surrogates cover strong nonlinearity and geometry families without a shared discretization: Gaussian processes for small data, neural operators and mesh graph networks for large data. Ansys SimAI predicts fields for new geometry and reports a confidence level with each result [Ansys SimAI], and Luminary advertises prediction errors below 2% at more than a thousand times simulation speed [Luminary]. Flux's difference is not speed: its surrogate predictions carry a stated statistical bound, can never alone decide a `SignOff` check, and are reproducible because their weights are pinned and labelled.

**Decision D-FLX-14:** A surrogate prediction is a Field of kind `Estimated { Statistical { method: conformal, α }, scope: Marginal }` that may drive `Preview`, `Interactive` and exploration; a `SignOff` check uses it only with a per-prediction bound in the check's norm or a confirming solve, and optimization loops calibrate by weighted conformal prediction.
*Why:* conformal coverage is marginal, not per prediction [Barber et al. 2019], optimizers steer toward a surrogate's errors, and energy bounds never certify peaks.
*Rejected:* split-conformal intervals as `SignOff` grounds; physics-informed networks as unbounded solvers.

The per-prediction bound projects the prediction onto the plan's finite element space. Energy, compliance and bounded linear functionals get an equilibrated estimate with a global coarse solve; regularized peaks get a DWR estimate costing one adjoint solve, priced beside the confirming solve so the plan picks the cheaper. Weighted conformal calibration weights points by an estimated likelihood ratio [Tibshirani et al. 2019] and reports the effective calibration size.

Kiln's cache already holds every `Interactive` result a repository has computed, so `Preview` geometry surrogates trained on a repository's own results arrive in phase 2. They paint a picture during exploration and never decide a check.

**Decision D-FLX-46:** Surrogate training may run in any class; the trained weights are a CAS artifact pinned by `ObjectId` in `ingot.lock` and labelled by their training data, and inference that feeds a check runs canonically.
*Why:* deterministic GPU training may be too slow to be practical, and pinned weights make every prediction reproducible.
*Rejected:* canonical-only training; retraining inside an Evaluation.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Modal and Craig–Bampton models | Eigen-solve bases; assembly-level reduction | `OutsideParameterBox` beyond the band | FLX-O-ROM-1 | 2 |
| POD, reduced basis, hyper-reduction, morphing models | Bases from solution samples; certified or residual bounds | `OutsideParameterBox { parameter, range }`; `TopologyChange` | FLX-O-ROM-1 | 3 |
| `Preview` geometry surrogates | Trained on a repository's own cached results; labelled with that repository's labels | `Untrusted { reason }` outside the training envelope | FLX-O-ROM-3 | 2 |
| Surrogate training | Any class; pinned weights; stored calibration set and envelope | `CalibrationTooSmall { n }` | FLX-O-ROM-2 | 4 |
| Surrogate prediction | `Estimated { Statistical { method: conformal } }` with `scope: Marginal`; weighted conformal in loops | `Untrusted { reason }` outside the envelope | FLX-O-ROM-2 | 4 |
| Per-prediction bound | Equilibrated for energy and linear goals; DWR for peaks; priced against a confirming solve | `NotQuantified`, so `SignOff` needs a confirming solve | FLX-O-ROM-2 | 4 |

## Execution and extension

A solve can take seconds or hours, run locally or remotely, be cancelled at any time, and call code that Crucible's builders did not write. This section states what Flux gives Kiln so that scheduling, cancellation and resumption keep determinism, and how others extend Flux through the same mechanisms std uses.

A solve is a set of Kiln nodes demanded by an Evaluation. Kiln owns scheduling, caching and AGT's `Budget`; Flux supplies cost models, safe points and step state.

- **Placement.** The plan picks class and place (local CPU or GPU, team server, cloud) from memory and time estimates, and never moves work to the cloud without permission. Browser evaluations follow PLT's heavy-worker rule.
- **Cost models.** They price refinement confirmation, per-prediction bounds, confirming solves and second trusted builders, so a plan compares them before running.
- **Aborts.** Aborts are never cached; completed adaptive iterations stay valid.
- **Step state.** The state of a transient solve at an accepted step is stored in Kiln's `StepState` retention tier by (`NodeKey`, step), so a resumed solve continues bit-identically.
- **Safe points.** Ends of time steps, adaptive and optimizer iterations, and Krylov restarts; `OpCx::safe_point` is polled at least every 10 ms of monotonic time.

### Extending Flux

About a hundred operations, each `flux::name@version` with a determinism grade, sit under `std::sim`, `std::physics`, `std::opt` and `std::uq` ([Reference](#operations)). Wasm components call them through `crucible:ops/flux`, and every call is a recorded dependency. A constitutive model can be a Wasm component in the `crucible:material/constitutive` world, with consistent tangents; a specialist solver can be one in the `crucible:physics/solver` world, taking and returning Fields. GPL reference codes (Elmer, OpenFOAM, CalculiX and others) run only as External Ops in pinned images on untrusted-evaluation workers, and their results carry the host's platform class or `Unverified` ([contract section 7.8](../contract.md)).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Operation registration | `OpImpl` with grade, effective-fidelity map and cost model; `Differentiable` where derivatives exist | `RegistryRejected { missing }` for a missing grade or cost model | FLX-O-OPT-1 | 0 |
| Physics packages in Ingot | User-namespace forms get std's kernels, derivatives, GPU paths and estimators | `FormError` at compile time | FLX-O-ARCH-1 | 1 |
| `crucible:field` WIT package | `types` and `build`, generated from the Rust types | `WitMismatch`: CI fails when published and generated WIT differ | FLX-O-ARCH-4 | 2 |
| Constitutive Wasm components | `crucible:material/constitutive`, batched, with consistent tangents | `TangentInconsistent`; the component cannot register for Newton | FLX-O-FORM-3 | 2 |
| Solver Wasm components | `crucible:physics/solver`, Fields in and out, may call `crucible:ops/flux` | Determinizer rejection | FLX-O-ARCH-1 | 2 |
| Flux operations from Wasm | `crucible:ops/flux`, GPU-backed ones included; recorded dependencies | `OpVersionRetired` with an upgrade Proposal | FLX-O-ARCH-2 | 2 |
| External Op solvers | GPL references in pinned images on untrusted-evaluation workers; host class or `Unverified` | A host failure is a `Failure`; worker loss an Abort | FLX-O-ARCH-3 | 3 |
| Placement and cost models | Plan-chosen class and place; `OpImpl` cost estimates | `PlanError::ExceedsLocal { memory, time }` | FLX-O-EXEC-1 | 1 |
| Aborts and resumption | Aborts never cached; step state resumes bit-identically | The Abort propagates to dependents | FLX-O-EXEC-1 | 1 |
| Cancellation latency | Safe points polled every 10 ms; 100 ms (target) | A missed latency fails the oracle | FLX-O-EXEC-2 | 1 |
| Remote and browser execution | Heavy worker above 512 MiB; remote above measured thresholds | `PlanError::ExceedsLocal` suggests remote evaluation | FLX-O-EXEC-1 | 1 |

## Results, reports and solver decks

Results are useful only once an engineer can probe them, combine load cases, classify stresses, send a report and hand the model to another tool, including the solver decks an incumbent's user already owns.

### Probes and derived quantities

Probes are regularized goals (`f.at(x, smooth: ρ)`), and line and surface probes return Fields. Reactions use the variationally consistent residual method and, as bounded linear functionals, can carry `Guaranteed` bounds. Derived quantities include von Mises, principal and Tresca stresses, heat flux, safety factor and COV's fatigue damage; recovered display stresses are `Indicator` and serve display only.

### Load-case combination

**Decision D-FLX-54:** `std::sim::combine(cases, factors)` forms factored linear combinations and `envelope(cases, by: Max | Min | AbsMax)` forms envelopes with a governing-case Field, both over the `LoadCase` domain; superposition requires every case from one linear solve with one operator and fails with `NonlinearSuperposition` otherwise, and budgets combine by the factors' absolute values in each norm.
*Why:* Nastran subcases and Ansys solution combinations do this routinely, GP8's structural check needs it, and an unchecked superposition of nonlinear cases gives a confident wrong answer.
*Rejected:* a separate combination domain beside `LoadCase`; superposition without the linearity check.

Code combinations (Eurocode ultimate and serviceability states, AISC LRFD) are `std::systems` packages per standard edition, which COV's structural rows cite.

### Stress linearization

Pressure-vessel and piping engineers classify stress through a wall into membrane, bending and peak parts; Ansys computes them along a straight path [Ansys linearized stress]. `f.linearize(along: segment or Query, curvature: Auto)` returns membrane, bending and peak tensors. Flux averages over a thin tube of radius ρ around the classification line, not over the line itself. A line integral of stress is not a bounded functional in three dimensions, while a tube average is. Membrane and bending parts therefore carry goal-oriented bounds: `Guaranteed` on fitted simplices with polynomial data, calibrated `Estimated` elsewhere.

### Reports

`std::sim::report` builds reports as Ingot data: plan explanation, budgets with confidence, validity zones, singular sets, convergence histories, margins and cost. They render through UIX's generated reports to PDF/A and HTML, with figures as Snapshots under a pinned `RenderProfile`, so a stored report re-renders identically.

### Display

**Decision D-FLX-22:** Fields paint on the true geometry: per-pixel WGSL evaluators read coefficient buffers on the UI process's device where the GPU tier allows, elsewhere refined vertex samples carry a stated interpolation error, probes always sample exactly on the CPU, and display data never feed checks.
*Why:* linear interpolation misplaces high-order peaks, and display work on the UI's device avoids a host round trip.
*Rejected:* rendering the analysis mesh.

Evaluators cover every `Discrete` element family, splines, `SparseGrid`, `Analytic` and `Reduced` Fields; other representations use vertex samples. Payloads carry quantized values with error, masks, deformations and glyphs.

### Solver decks

Many companies own validated Nastran and Abaqus models, and aerospace customers deliver reduced models as Nastran matrices for coupled loads analysis. Flux runs imported decks and writes its studies back out, so nothing is trapped on either side.

**Decision D-FLX-53:** An imported Nastran bulk data file (BDF) or Abaqus input deck, read by ECO, becomes a `Mesh` Body plus a study whose cards map to Flux forms and idealizations (shell, solid and beam elements, RBE2 and RBE3 to remote points, CBUSH to bushings, CONM2 to point masses, MPC and SPC to constraints); a card family is enabled only once its oracle passes, and any other card fails with `UnmappedCard { card, line }`, never dropped; export writes a study as a BDF for SOL 101, 103, 111 and 112 and a Craig–Bampton reduction as DMIG or OP4 matrices.
*Why:* a company's validated legacy models must run and compare, not only display, and a customer or regulator may require the incumbent to re-run a Crucible model.
*Rejected:* viewing imported decks without running them; silently dropping unknown cards; a parallel element library for imported meshes.

LS-DYNA keyword decks, read by ECO, map meshes, parts, materials and contacts onto explicit dynamics in phase 3.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Probes and derived quantities | Regularized point, line and surface probes; stress, thermal and fatigue quantities | `Undecided { SingularPoint }` near flagged sets | FLX-O-POST-1 | 1 |
| Reactions | Residual reactions with `Guaranteed` resultant bounds where proven | `Unbalanced { residual }` when reactions and loads disagree beyond the algebraic part | FLX-O-POST-1 | 1 |
| Load-case combination and envelopes | `combine` and `envelope` over `LoadCase` with governing cases; budgets by factor | `NonlinearSuperposition` | FLX-O-POST-3 | 2 |
| Stress linearization | Membrane, bending and peak over a regularized classification line, with goal bounds | `LineOutsideWall { segment }` | FLX-O-POST-4 | 2 |
| Reports | `std::sim::report` data for UI and CI, rendered through UIX's generated reports | `IncompleteReport { missing }` lists missing budgets | FLX-O-POST-1 | 1 |
| Display evaluators | WGSL per-pixel evaluators on the UI's device | A tier without compute uses vertex samples, stated | FLX-O-POST-2 | 1 |
| Display samples | Adaptive vertex samples with interpolation error | None: refinement continues until the stated interpolation error holds | FLX-O-POST-2 | 1 |
| Mode shapes | Modal and buckling eigenvector displays | Degenerate eigenspaces shown as subspaces | FLX-O-POST-2 | 1 |
| Isosurfaces, slices, streamlines, response functions | Display geometry, plus Implicit Bodies for geometry use | `StreamlineErrorAboveTolerance` refines the step | FLX-O-POST-1 | 2 |
| Imported solver decks | BDF and Abaqus decks run as studies, card family by card family | `UnmappedCard { card, line }` | FLX-O-DECK-1 | 3 |
| Solver deck export | BDF for SOL 101, 103, 111 and 112; Craig–Bampton reductions as DMIG and OP4 | `NotExportable { idealization }` | FLX-O-DECK-2 | 3 |
| LS-DYNA keyword mapping | Meshes, parts, materials and contacts onto explicit dynamics | `UnmappedCard { card, line }` | FLX-O-DECK-1 | 3 |

## Reference

### Crates

| Crate | Layer | Contents |
| --- | --- | --- |
| `field` | Engine core | `Field` views over `DynField`, domains, representations, `Sampler`, storage layout |
| `kernels` | Engine core | `kernels::expr`, the kernel IR, its back ends and `local_solve`; no `unsafe` code |
| `flux-forms` | Physics | Form node set, typing, symbolic differentiation, elements, form-compiler front end |
| `flux-solve` | Physics | Plans, discretizations, solvers, estimators, Networks, multibody |
| `flux-couple` | Physics | Coupling, homogenization, FMI and SSP runtime |
| `flux-opt` | Physics | Adjoints, optimization, uncertainty, reduced models, surrogates |
| `flux-op-<family>` | Physics | One crate per operation family, each released version a frozen source directory |
| `linalg` | Platform (PLT with FLX) | Canonical dense and sparse linear algebra |
| `bridges/` | Outside `core/` | Optional PETSc and hypre bindings, never in Wasm builds |

**Decision D-FLX-1:** Flux owns two engine-core crates below Anvil (`field` and `kernels`), four physics crates and one `flux-op-<family>` crate per operation family; optional native bindings live in `bridges/`, and `linalg` is shared with PLT.
*Why:* Anvil operations consume Fields and implicit tapes compile through the kernel IR, so those two crates must sit below Anvil, and one crate per operation family is the unit of a frozen closure hash ([contract section 4](../contract.md)).
*Rejected:* a seven-crate split with Flux-prefixed engine crates; every operation in one crate, which makes every builder edit one hot spot.

### Operations

| Group | Operations |
| --- | --- |
| Fields | `field_sample`, `field_transfer`, `field_project`, `field_recover`, `field_reduce`, `field_region`, `field_compare`, `field_linearize` |
| Forms and plans | `compile_form`, `plan`, `mark_reduction` |
| Discretization and solve | `discretize`, `cut_quadrature`, `assemble`, `setup_preconditioner`, `solve_linear`, `solve_nonlinear`, `solve_transient`, `solve_eigen`, `solve_harmonic`, `solve_explicit`, `solve_ehl`, `koiter_coefficient` |
| Linear dynamics | `modal_response`, `random_response`, `spectrum_response` |
| Electromagnetics | `port_modes`, `fast_sweep`, `floquet_modes`, `extract_rlcg` |
| Lumped and multibody | `compile_network`, `solve_dae`, `solve_periodic`, `solve_multibody`, `linearize_multibody`, `solve_rod`; circuit analyses use `solve_nonlinear` (operating point, DC sweep), `solve_harmonic` (AC, noise), `solve_eigen` (pole-zero), `solve_dae` (transient) and `solve_periodic` (periodic steady state, harmonic balance) |
| Error and adaptivity | `estimate_error`, `estimate_goal`, `singular_sets`, `confirm_refinement`, `validity_zones`, `certify`, `mark`, `adapt` |
| Coupling | `couple`, `homogenize`, `localize`, `cosimulate`, `fmu_import`, `fmu_export`, `ssp_import`, `ssp_export` |
| Gradients and optimization | `tangent`, `adjoint`, `shape_gradient`, `filter_density`, `project_density`, `mma_step`, `lbfgs_step`, `sqp_step`, `cmaes_step` |
| Uncertainty | `sample_plan`, `pce_fit`, `sobol_indices`, `shapley_effects`, `mlmc_estimate`, `subset_simulation` |
| Reduced models and surrogates | `modal_basis`, `craig_bampton`, `pod_basis`, `hyperreduce`, `rom_build`, `rom_eval`, `surrogate_train`, `surrogate_calibrate`, `surrogate_eval` |
| General methods | `bvh_build`, `bvh_query`, `neighbor_list`, `segmented_reduce`, `random_stream`, `fmm_apply`, `hmatrix_build`, `hmatrix_apply`, `fft_solve` |
| Solver decks | `deck_import`, `deck_export` |
| Post-processing | `probe`, `reaction`, `isosurface`, `streamlines`, `display_evaluator`, `display_samples`, `report_data` |

[[DIAGRAM diagrams/03-flux-pipeline.jsx: Flux pipeline · 7 stages, 1 adaptive loop, 3 consumers]]

Read it top to bottom: boxes are stages, the side loop repeats until the estimate meets its tolerance, and the dashed path carries adjoint gradients back.

### Rust surface

Kiln calls every operation through `OpImpl`, `OpCx` and, where derivatives exist, `Differentiable` from `base-op`; operations return `OpResult<T> = Result<T, Stop>`, so a typed `Failure` and an environmental Abort never convert into each other ([contract section 7.2](../contract.md)). `OpCx` is a shared, cloneable handle, and every Flux signature takes `&OpCx`. The erased `DynField` is canonical: Kiln memoizes it, the CAS stores it and `crucible:ops` carries it, and `Field<D, V>` is a generated, checked view over it.

```rust
/// A typed view: Field<Body, Stress>, Field<(Body, Time), Temperature>.
pub struct Field<D: Domain, V: FieldValue> {
    inner: DynField,            // { domain: DomainDesc, value: ValueDesc, header, repr: FieldRepr }
    _kind: PhantomData<(D, V)>,
}
impl<D: Domain, V: FieldValue> TryFrom<DynField> for Field<D, V> {
    type Error = Failure;       // flux/domain_mismatch or flux/value_mismatch
}

pub enum FieldRepr { Analytic, Discrete, QuadraturePoint, SparseGrid, PerEntity, PointCloud, Reduced, Surrogate }

pub trait Sampler {
    /// Values with a pointwise ErrorBudget and, where known, a gradient bound.
    /// Point location calls base-value's `Classify` trait, which Anvil implements.
    fn sample(&self, cx: &OpCx, at: &[Location], accuracy: Accuracy) -> OpResult<Vec<Sampled>>;
}
```

Flux's typed failures are variants of `base-op`'s extensible `Failure`, rendered `flux/<snake_case>`: among them `flux/linear_diverged { iterations, residual_history }`, `flux/nonlinear_diverged { iteration, residual_history, last_converged }`, `flux/bifurcation { load, modes }`, `flux/convexity_violated { step }`, `flux/unsupported { reason }`, `flux/singular_operator { null_space_hint }`, `flux/outside_parameter_box { parameter, range }` and `flux/unmapped_card { card, line }`.

### WIT interfaces

Flux owns `crucible:field` (interfaces `types` and `build`; sampling is `flux::field_sample` through `crucible:ops/flux`) and, with COV, the `crucible:physics` `solver` and `crucible:material` `constitutive` worlds; ECO keeps the index. The WIT is generated from the Rust types, and examples import `@0.1.0` until the packages freeze after the rename.

### Estimators by error source

| Source | Estimator | Norm | Kind |
| --- | --- | --- | --- |
| Discretization, scalar diffusion, fitted simplices | Equilibrated flux [Smears and Vohralík 2020] | Energy | `Guaranteed` |
| Discretization, elasticity, fitted simplices | Strongly symmetric equilibrated stress [Arnold and Winther 2002; Hu and Zhang 2015] | Energy | `Guaranteed` with polynomial data |
| Discretization, weakly symmetric elasticity | Equilibration with a shape-regularity constant [Bertrand et al. 2019] | Energy | `Estimated { Class elasticity.energy }` |
| Discretization, hanging nodes or cut cells, energy norm | The constructions above, without a proof on cut cells | Energy | `Indicator` until a class or a proof exists |
| Bounded linear goals (regional averages, gauge averages, resultants, compliance, mean temperature) | Primal–dual product of energy bounds, with the residual term | Goal | `Guaranteed` when both factors and the algebraic part are |
| Regularized peaks, point values, critical-distance goals at `SignOff` | DWR with the adjoint one degree higher | Goal | `Estimated { Class elasticity.peak }` |
| The same goals at `Interactive` | DWR at the primal degree with reconstructed weights | Goal | `Estimated { Class elasticity.peak.interactive }` |
| Frequencies | Eigenvalue DWR, two-sided on non-conforming discretizations | Goal | `Estimated { Class elasticity.frequency }` |
| Buckling factors | Coupled DWR with the prestress adjoint | Goal | `Estimated { Class elasticity.buckling }` or `lattice.buckling` |
| Algebraic, energy norm | Multilevel bound on fitted hierarchies [Papež et al. 2020]; certified spectral bound after a factorization | Energy | `Guaranteed` |
| Algebraic, goal norm | \|r(z_h)\| ≤ η_alg · ‖z_h‖_A | Goal | `Guaranteed` when η_alg is; otherwise `Estimated` in the accompanying discretization class |
| Temporal, adjoint-weighted residual | Residual in time weighted by the temporal adjoint | Goal | `Estimated { Class temporal.awr }` |
| Temporal, step halving | Comparison with frozen breakpoints | Goal | `Estimated { Class temporal.halving }` |
| Temporal, summed local errors | Sum of local error estimates | Goal | `Indicator` |
| Quadrature and geometry | Rule-order comparison; Anvil face bounds through shape sensitivity | Goal or energy | Zero for polynomial data on planar faces; otherwise `Estimated` in the accompanying discretization class |
| Regularization | Enclosed gap between the regularized goal and the raw maximum of the computed Field | Goal | `Guaranteed` |
| Floating point | Bound γ_k of the canonical evaluation, k the reduction-tree depth; through ‖z_h‖ for goals | As the covered part | `Guaranteed` |
| Reduction or surrogate | Shell and beam patches plus a global modelling-error term; modal truncation; reduced-model, conformal and per-prediction bounds | Goal | Per method, each naming its class or statistical method |
| Statistical | Confidence intervals, sampling estimators | Goal | `Estimated { Statistical { method, α } }` |
| Input and tolerance | Property bases; worst-case tolerance propagation | Goal | `Estimated { Statistical { method, α } }` |
| Model form | COV's validation, or a pinned policy allowance | Goal | From COV or the allowance, else `NotQuantified` |

### Field representations and operations

| Representation | Holds | Sampling error |
| --- | --- | --- |
| `Analytic` | Kernel-IR expression (loads, boundary data) | Floating point only |
| `Discrete` | Lagrange, edge, face, discontinuous or NURBS coefficients | Discretization part carried separately |
| `QuadraturePoint` | Values at quadrature points (plastic state, densities) | Recovery error |
| `SparseGrid` | Adaptive block grid (lattice Boltzmann, FDTD, CT data) | Local second differences |
| `PerEntity` | One value per entity | None |
| `PointCloud` | Points with a reconstruction rule | Leave-one-out estimate |
| `Reduced` | Basis Field times coefficient model | Certified or residual bound |
| `Surrogate` | Trained model, calibration set, envelope | Conformal bound, `scope: Marginal` |

| Ingot | Error behaviour |
| --- | --- |
| `a + b`, `sqrt(a)` | Lazy `Analytic`; first-order propagation in one norm |
| `grad`, `div`, `curl`, `sym_grad` | Basis derivatives, or `NeedsRecovery` |
| `f.on(p.faces(q))` | Full, normal or tangential trace; nothing added |
| `f.integrate(dx(region))` | Quadrature part added |
| `f.max(over: R)`, `f.at(x)`, `f.mean(over: R)`, `f.gauge(...)`, `f.tcd(...)` | Goals estimated by `estimate_goal` (next section) |
| `f.project(to: V)`, `f.transfer(to: body)` | Conservative or consistent; transfer part estimated |
| `f.region(where: f > 250MPa)` | Implicit Body bounded from the Field and its gradient |
| `compare(a, b)` | Differences inside combined bounds are not significant |

### Spaces, problem kinds and form checks

| Space | Constructor | Elements | Phase |
| --- | --- | --- | --- |
| H¹ | `H1(domain, degree: p, shape: …)` | Lagrange of any order, serendipity, hierarchical Legendre | 0 (p ≤ 4), 1 |
| H¹ on a section | `H1(domain: section, kind: planar(…) or axisymmetric(twist: bool))` | The H¹ elements in two dimensions, with the r-weighted measure for axisymmetry | 1 |
| H(curl), H(div) | `HCurl(domain, degree: p, kind: 1 \| 2)`, `HDiv(domain, degree: p, kind: rt \| bdm)` | Nédélec, Raviart–Thomas, Brezzi–Douglas–Marini | 1 (H(div) in estimators), 3 |
| L², trace, real | `L2`, `Trace`, `Real(n)` | Discontinuous bases, facet spaces, global multipliers | 1, 3 (trace) |
| Spline | `Spline(body, degree: p, continuity: k, kind: nurbs \| thb)` | B-rep NURBS, truncated hierarchical B-splines | 2 |
| Manifold | Sheet and wire Bodies with director or section unknowns | Shells, beams, rods | 1 (wires), 2 (sheets) |
| Parameter domain | `Interval(Radius, n)`, `Sphere(directions: n)`, products `V ⊗ W` | Batched local problems | 4 |
| Mixed, restricted | `(V1, V2)`, `V.restrict(region)` | Taylor–Hood, MINI, (H(div), L²) | 1 |

| Kind | Ingot | What Flux does |
| --- | --- | --- |
| Linear, nonlinear, energy | `a == L`; `F == 0`; `minimize(Pi, u)` | Arity check; symbolic Jacobian or Hessian |
| Mixed | `trial((Velocity, Pressure), p, element: taylor_hood(2))` | Blocks kept for field-split preconditioners |
| Time-dependent | `dt(u)`; `implicit(…)`, `explicit(…)` marks | Semi-discrete system; the plan picks the scheme |
| Harmonic, eigen, constrained | `solve_harmonic`, `modes`, `fixed:`, `contact(...)` | Complex forms; strong, Nitsche or multiplier constraints |
| Continuation, goals | `continue_in(load, to: 2kN)`; `goals: [...]` | Arc length with bifurcation detection; goal-oriented adaptivity |

| Check | Rule | Error and fix |
| --- | --- | --- |
| Units | One dimension per residual row | `FormError::UnitMismatch { term, expected, found }` |
| Arity | Bilinear forms linear in trial and test | `NotLinear { term }`, suggesting `F == 0` |
| Conformity | `curl` needs H(curl) or H¹, `div` H(div) or H¹ | `Conformity`, naming the conforming space |
| Inf-sup, quadrature | Unstable pairs such as P1–P1 Stokes; degree above 30 | Warning naming a stable pair |

### Plan defaults

| Situation | Plan default |
| --- | --- |
| Compact solids, heat, electrostatics | Immersed octree, aggregated CutFEM; shifted boundary at `Preview` |
| Thin walls, members, struts, lattices | Shells, beams, beam lattices and sheet shells per `mark_reduction` |
| Revolved or prismatic Bodies with symmetric conditions | Axisymmetric or planar section models |
| Contact, sliding interfaces; turbulent layers needing y⁺ resolution | Fitted meshes, boundary layers from phase 4 |
| Laminar thermal layers; frozen layers in moulding | Octree wall refinement |
| Voxel and CT data | Finite cell |
| Resonant or narrowband radiation | Frequency-domain Nédélec FEM |
| Broadband transients and EMC | FDTD |
| Exterior acoustics and electrostatics | Boundary elements, or FEM–BEM coupling |
| Granular flow, splashing, fragmentation | DEM, SPH, MPM or peridynamics |
| Lumped systems | Network compiler and DAE solver |

### What Flux needs from Anvil

| Flux need | Anvil operation | Anvil phase |
| --- | --- | --- |
| Classification, closest points, cut quadrature, thickness, topology counts | `GeometryQuery` | 1 |
| Edge classes by certified dihedral angle | `anvil::classify_edges` | 1 |
| Mid-surfaces, member axes; minimal-surface mid-surfaces | `mid_surface`, `member_axes`; `mid_surface`'s implicit path | 2 (1 for struts); 2 |
| Curved conforming tetrahedra; bisection | `tetrahedralize`, `untangle`, `refine_mesh` | 2 |
| Metric adaptation and node relocation | `adapt_mesh`, `optimize_mesh` | 3 |
| Hex-dominant and swept meshes | `hex_dominant`, `sweep_mesh`, `split_polyhedra` | 3 (sweep), 4 |
| Boundary layers; interface overlays | `boundary_layer`; `common_refinement` | 4 |
| Shape sensitivities | `shape_velocity` | 2 |

### Solver catalog

| Use | Method | Phase |
| --- | --- | --- |
| Symmetric problems to about 2M DOFs; coarse grids | Supernodal LLᵀ and LDLᵀ, nested dissection | 1, 2 (parallel) |
| Networks and circuits | Block-triangular LU with refactorization, in KLU's scheme | 2 |
| Indefinite Helmholtz and Maxwell | Complex symmetric LDLᵀ to its memory limit | 3 |
| Mixed precision | `f32` factors with `f64` GMRES refinement when the condition estimate is below 10⁷ | 2 |
| Distributed | STRUMPACK or SuperLU_DIST through `bridges/`; MUMPS as an External Op | 4 |

| Problem | Default | Phase |
| --- | --- | --- |
| Elliptic, high order, octree | p-, then h-multigrid, then deterministic AMG (algebraic multigrid); Schwarz smoothing on cut cells | 1 |
| Low order and fitted | Smoothed-aggregation AMG; hypre BoomerAMG as a bridge | 1 |
| Shells and beams | Same hierarchy with rotational near-null modes | 2 |
| H(curl), H(div) | Auxiliary-space AMG (Hiptmair–Xu); hypre AMS and ADS as bridges | 3 |
| Stokes and Oseen | Block-triangular field split with PCD (pressure convection–diffusion) or a least-squares commutator | 3 |
| Upwind DG transport | Approximate-ideal-restriction AMG | 3 |
| Indefinite Helmholtz and Maxwell | Complex LDLᵀ; optimized Schwarz; shifted-Laplacian multigrid | 3 |
| High-Reynolds steady Navier–Stokes | Augmented Lagrangian with patch smoothers | 4 |
| Transient high-order flow | Dual splitting with matrix-free pressure p-multigrid | 4 |
| Distributed, above about 5 × 10⁷ DOFs | BDDC with deluxe scaling; FETI-DP for contact | 4 |

BDDC is balancing domain decomposition by constraints and FETI-DP the dual–primal finite element tearing and interconnecting method.

| Method | Use | Phase |
| --- | --- | --- |
| Newton–Krylov, exact Jacobians, backtracking, Eisenstat–Walker forcing | Convex forms in phase 1; every nonlinear form from phase 2 | 1, 2 |
| Trust-region Newton; arc length; semismooth Newton; Anderson acceleration | Energy forms; load paths; contact; partitioned coupling | 2 |
| Pseudo-transient continuation | Strongly nonlinear steady flows | 3 |
| Nonlinear preconditioning | ASPIN, additive Schwarz preconditioned inexact Newton, for localized nonlinearity [Hwang and Cai 2005] | 4 |

| Family | Use | Phase |
| --- | --- | --- |
| Backward differentiation formulas, orders 1 to 5; SDIRK, ESDIRK; additive Runge–Kutta IMEX | Stiff and stiff–nonstiff problems | 2 |
| Generalized-α, Lie group generalized-α | Structural and multibody dynamics | 2 |
| Central difference; SSP Runge–Kutta; symplectic schemes | Explicit dynamics, DG, finite volume, particles, FDTD | 3 |
| Exponential integrators; Parareal and MGRIT | Stiff linear-dominated problems; long horizons | 5 |

### Method catalogs

| Mechanism | Enforcement | Phase |
| --- | --- | --- |
| Dirichlet; multi-point, periodic, cyclic and integral constraints | Strong on fitted meshes, Nitsche on immersed and spline discretizations; elimination or `Real` multipliers | 1 |
| Bonded and no-separation ties on the octree | Nitsche across `dI` | 2 |
| Bonded interfaces and frictional contact on fitted meshes | Mortar with dual multipliers and semismooth Newton; augmented Lagrangian; penalty at `Interactive` | 2 |
| Large sliding; immersed contact; thermal and electrical contact | Sorted deterministic search; Nitsche on cut surfaces, at p > 2 only after the immersed Hertz case passes; conductance on `dI` | 3 |
| Incremental Potential Contact, for GP16's soft goods | Barrier distance d̂ and friction smoothing ε_v reported as `regularization` [Li et al. 2020] | 5 |

| Coupling | Default | Phase |
| --- | --- | --- |
| Thermal stress, one way | Sequential solves joined through Kiln | 1 |
| Two-way thermo-mechanics; transient activation for joint-scale welding | Monolithic Newton with field split | 2, 4 (welding) |
| Electro-thermal Joule heating | Monolithic Newton with continuation; `Runaway { power }` | 4 |
| Conjugate heat transfer | Robin partitioned, or monolithic on a shared octree with wall refinement | 3 (laminar, natural convection), 4 (turbulent) |
| Electromagnetic–structural | Partitioned: Maxwell stress or virtual work | 4 |
| Fluid–structure | Aitken or interface quasi-Newton (IQN-ILS, IQN-IMVJ); monolithic ALE (arbitrary Lagrangian–Eulerian) or Robin–Robin for strong added mass | 4 |
| Piezoelectric and electrostatic MEMS | Monolithic; pull-in reported as a bifurcation | 5 |

| Problem | Adjoint | Cost | Phase |
| --- | --- | --- | --- |
| Linear and nonlinear steady | One transposed solve at the converged state | At most one forward solve | 1 |
| Eigenvalue | Eigenvector formula; subspace form for repeated eigenvalues | Small | 2 |
| Transient | Backward in time with multistage checkpointing | Two to five forward solves | 2 |
| Steady laminar flow | Derived from the DG(0) and DG forms | About one forward solve | 3 |
| Turbulent flow | Frozen-turbulence, then full RANS adjoint | One to two forward solves | 4 |
| Contact; coupled | Converged active set, changes flagged; block-transposed | As forward | 3; 4 |

| Method | Formulation | Phase |
| --- | --- | --- |
| Density | SIMP (solid isotropic material with penalization) on the immersed octree; Helmholtz filter; Heaviside projection; robust eroded, intermediate and dilated designs; manufacturing constraints | 1 (compliance, volume, additive and unrestricted), 2 (stress, robust, milling, two-axis cutting, casting) |
| Graded lattice | Homogenized cell-parameter maps, then dehomogenization | 1, 2 |
| Shell sizing | Thickness Fields on mid-surface shells with adjoints | 2 |
| Level set | Shape and topological derivatives with CutFEM | 3 |
| Multiphysics | Any coupled form through the coupled adjoint | 4 |
| Laminates | Ply-shape, ply-drop and stacking optimization under MEC's ply rules | 6 |

| Method | Use | Error part | Phase |
| --- | --- | --- | --- |
| Monte Carlo, randomized quasi-Monte Carlo | Reference method, yields | Confidence or repeated-scramble interval | 2 |
| Multilevel and multi-model Monte Carlo (MLMC) | Refinement hierarchies; reduced models as control variates | Bias and variance parts | 3 |
| Sparse polynomial chaos (PCE) | Smooth dependence on up to about 20 parameters | Cross-validation | 3 |
| Grouped Sobol indices; Shapley effects [Song et al. 2016] | Sensitivity with independent or dependent inputs | Bootstrap interval | 3 |
| Subset simulation, cross-entropy sampling; FORM (first-order reliability) | Failure probabilities below 10⁻³ | Coefficient of variation; FORM `Indicator` unless importance sampling confirms it | 3; 4 |
| Probability boxes | Epistemic intervals by nested sampling, never summed with distributions | Interval bounds reported beside the distribution | 3 |

| Model | Build | Error | Phase |
| --- | --- | --- | --- |
| Modal superposition; Craig–Bampton | Lanczos modes; fixed-interface and constraint modes per Part | Truncation estimates | 2 |
| POD–Galerkin; hyper-reduction | Solution samples (proper orthogonal decomposition); DEIM [Chaturantabut and Sorensen 2010] or energy-conserving sampling | Residual-based, `Estimated` in a reduction class | 3 |
| Certified reduced basis | Greedy sampling of affinely parametrized linear forms | `Guaranteed`, coercivity bound by the successive constraint method [Huynh et al. 2007] | 3 |
| Krylov moment matching | Frequency-domain reduction for sweeps and FMU export | Residual over the band | 3 |
| Morphing reduced models | Fixed background discretization plus `shape_velocity` morphs | Residual-based | 3 |

## State of the art

Figures are targets, measured on contract section 13.3's reference machines. The incumbent named in each row is the product an engineer would otherwise use.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Static analysis workflow | Goal-oriented hp-adaptivity on the design geometry | Ansys Mechanical, Abaqus, Simcenter Nastran, with meshing and defeaturing by the analyst | Immersed octree, per-region models, calibrated goal bounds | Time from STEP import to a decided stress check on 20 parts, meshing and defeaturing included, against an analyst using Ansys Mechanical |
| Weak-form language | UFL | COMSOL Weak Form PDE; DOLFINx and Firedrake | UFL semantics with units and form-level derivatives | FEniCS and Firedrake demos |
| Form compilation | TSFC; libCEED operator split | FFCx, TSFC, MFEM | Native, to the kernel IR | 200 ms for p = 2 elasticity |
| High-order operators | Sum-factorized partial assembly [Kolev et al. 2021; Fischer et al. 2020] | MFEM, libCEED, deal.II | Own canonical kernels | The two CEED rows of 13.3 |
| Immersed discretization | Aggregated CutFEM, Saye quadrature | ngsxfem, GridapEmbedded | One octree, one treatment | Manufactured-solution rates; 1,000 shifts |
| Dimensional reduction | Nitsche mixed-dimensional coupling; goal-oriented modelling error [Oden and Prudhomme 2002] | Ansys Mechanical and Abaqus shell and beam models, chosen by the analyst | Per-region marking, local and global reduction error | 3D references on held-out frames and shells |
| Symmetry reductions | Axisymmetric, planar and cyclic models | Abaqus axisymmetric elements; Ansys cyclic regions | Detected or declared, always checked | Lamé cylinder, NAFEMS axisymmetric cases, bladed-disc modes |
| A posteriori estimation | Equilibrated flux; DWR [Becker and Rannacher 2001]; multilevel algebraic bounds [Papež et al. 2020] | deal.II, MFEM; incumbents report no bound | `Guaranteed` where proven; calibrated DWR elsewhere | Effectivity; zero undershoots in held-out sets |
| Solution verification | Grid convergence index [NASA GCI tutorial] | Manual convergence studies in every incumbent | Calibrated GCI by coarsening | Band coverage on benchmark flows |
| Multigrid | Global coarsening [Munch et al. 2022]; low-order-refined de Rham [Pazner et al. 2022] | hypre, MFEM | Own multigrid and AMG | 1.5 times of MFEM with hypre |
| Navier–Stokes preconditioning | Augmented Lagrangian [Farrell et al. 2019]; PCD | Their published iteration counts | PCD, LSC, augmented Lagrangian | Cavity iterations within 2 times |
| Sparse direct | Supernodal nested dissection; block-triangular LU | CHOLMOD and KLU [SuiteSparse]; MUMPS | Canonical `linalg` | 2 times of CHOLMOD |
| Mixed precision | GMRES refinement [Carson and Higham 2018] | Vendor mixed-precision solvers | `f32` factors, `f64` refinement | Full `f64` accuracy |
| Reproducible reductions | Binned summation [ReproBLAS] | ReproBLAS | `det_sum`, `exact_sum` | Conjugate-gradient overhead 1.05 times |
| Time integration | Adaptive BDF, IMEX Runge–Kutta, generalized-α | SUNDIALS [SUNDIALS licence] | Native, differentiable | 1.5 times of SUNDIALS |
| Eigenvalues | Krylov–Schur, LOBPCG, contour integrals; DWR [Heuveline and Rannacher 2001] | SLEPc, ARPACK-ng; Ansys and Nastran modal solvers | Native, calibrated, two-sided | NAFEMS; 1.5 times of SLEPc |
| Linear dynamics | Mode superposition with residual vectors; CQC | Ansys Mechanical, Simcenter Nastran | Native, with truncation and resonance error in the budget | NAFEMS forced vibration; SDOF and two-DOF cases |
| Lumped networks | Pantelides with dummy derivatives | Dymola; OpenModelica [OpenModelica flags]; SUNDIALS IDA | Native, incremental per mode | 2 times of IDA; re-translation under 1 s |
| Multibody dynamics | Lie group and nonsmooth generalized-α [Brüls et al. 2012; Brüls et al. 2014] | Project Chrono [Project Chrono]; Adams | Native | 1.5 times of Chrono |
| Rods | Cosserat rods [Gazzola et al. PyElastica] | PyElastica | Native | Elastica, helical buckling |
| Explicit dynamics | Spectral, spline and mass-lumped tetrahedral elements [Geevers et al. 2018] | LS-DYNA [Ansys LS-DYNA] | Native; GPU at `Interactive` | 10⁷ element cycles per second |
| Full-wave electromagnetics | Nédélec FEM, wave ports, fast sweep, goal-oriented S-parameters | HFSS [Ansys HFSS]; Palace [Palace documentation] | Native, with S-parameter bounds | S-parameters against Palace |
| Parasitic extraction | Partial-element quasi-static extraction | Ansys Q3D [Ansys Q3D] | `extract_rlcg` with budgets | Parallel bars, coaxial line, a busbar |
| FDTD; boundary elements | Stable conformal Yee [Zagorodnov et al. 2003]; Calderón-preconditioned BEM [Scroggs et al. 2017] | Meep, openEMS; Bempp-cl, bempp-rs | Native FDTD; bempp-rs | Cavity and Mie |
| Flow | Finite volume and DG with derived adjoints | Fluent, STAR-CCM+ [Siemens adjoint blog]; OpenFOAM | DG(0) and DG forms with adjoints | 13.3's flow throughput row; duct adjoint against finite differences |
| GPU flow | Native GPU finite volume | Fluent's GPU solver [Ansys Fluent GPU] | `Gpu` class certified on the CPU | At least half the published speed-up on the same case family |
| Lattice Boltzmann, particles | Cumulant collision [Geier et al. 2015]; δ-SPH [Marrone et al. 2011]; MLS-MPM [Hu et al. 2018] | XLB [XLB repository]; DualSPHysics; LAMMPS | Native on general operations | Schäfer–Turek [Schäfer et al. 1996]; SPHERIC dam break [SPHERIC test 2] |
| Adjoints | Form-level derivation [Farrell et al. 2013]; CAMS [Zhang and Constantinescu 2021] | pyadjoint; JAX-FEM [JAX-FEM repository]; STAR-CCM+ adjoint | Native through Kiln | Taylor order 2 |
| Topology optimization | Giga-voxel density methods [Aage et al. 2017]; MMA | Fusion generative design; nTop; TopOpt_in_PETSc | Native, canonical at `SignOff`, exact kept interfaces | 10⁸ elements on 64 cores |
| Reduced models | POD with DEIM; reduced basis with SCM | pyMOR, RBniCS | Native | 100 times faster at 1% error |
| Surrogates | Weighted conformal [Tibshirani et al. 2019]; coverage limits [Barber et al. 2019] | Ansys SimAI [Ansys SimAI]; Luminary [Luminary]; PhysicsNeMo | Bounds in the check's norm; pinned weights | No false `SignOff` `Pass` in 10⁴ adversarial evaluations, with competitors' confidence indicators measured on the same held-out set |
| Uncertainty | MLMC [Giles 2015]; sparse PCE; Shapley effects | Dakota, OpenTURNS | Native `std::uq` | Ishigami; MLMC exponent |
| Batteries | Doyle–Fuller–Newman | PyBaMM [PyBaMM repository] | Parameter-domain forms | PyBaMM agreement |
| Co-simulation | FMI 3.0.2, SSP 2.0.1 | FMPy, OMSimulator | Native runtime | Reference FMUs |

Linked dependencies are faer (`CpuIsa` only), wgpu, bempp-rs, and hypre and PETSc as bridges, each under contract section 7.7's licence list; deal.II, libCEED, MFEM, SUNDIALS and SLEPc may be ported with their notices, and Algoim is ported with its LBNL grant-back recorded. LGPL code (preCICE, DOLFINx, NGSolve, Mmg) serves only as external tools or references, and GPL code (JAX-FEM, Meep, Elmer, OpenFOAM, CalculiX, LAMMPS) only as External Ops or oracles. FluidX3D forbids commercial use, so Crucible never runs it [FluidX3D licence]. Incumbent behaviour is studied only under contract section 7.7's clean-room insight protocol.

| Capability | Incumbent and its documented feature | Crucible's capability row and phase | Standing |
| --- | --- | --- | --- |
| Linear static, modal and buckling on a part | Ansys Mechanical's modal and structural analyses [Ansys Mechanical] | Aggregated CutFEM; Eigen-solvers; 1 | Ahead: no meshing or defeaturing, and every checked goal carries a bound |
| Remote points | Rigid and deformable remote points, like CERIG and RBE3 [Ansys remote points] | Remote points; 1 | Equal: the same behaviours, attached by query so they follow the design |
| Point masses, springs, bushings | Point masses and bushings exported as CONM2 and CBUSH [Ansys Nastran export] | Point masses; Springs and dampers, 1; Bushings, 2 | Equal for masses and springs; Later for bushings, which follow the nonlinear curves of phase 2 |
| Axisymmetric and planar models | Axisymmetric elements with and without twist [Abaqus axisymmetric elements] | Planar and axisymmetric models; 1 | Ahead: detected from certified geometry and checked for symmetry |
| Symmetry and cyclic reductions | Symmetry and cyclic regions [Ansys Mechanical]; symmetry and antisymmetry planes [COMSOL symmetry] | Symmetry and cyclic-sector reductions; 2 | Ahead: a broken symmetry fails instead of giving a wrong answer |
| Harmonic, random and spectrum response with prestress | Modal, harmonic, spectrum and random vibration with pre-stress [Ansys Mechanical]; prestressed SOL 103 [Ansys Nastran export] | Linear perturbation; Frequency response; Random vibration; Response spectrum; 2 | Equal, with truncation and near-resonance error stated |
| Assemblies with automatic contact | General contact with an automated definition [Abaqus general contact] | Immersed tied interfaces; 2 | Equal on detection; Ahead on meshing, which bonded assemblies never need |
| Load-case combination | Solution combinations and envelopes [Ansys solution combination] | Load-case combination and envelopes; 2 | Ahead: superposition of nonlinear cases is refused |
| Stress linearization | Membrane, bending and peak along a path [Ansys linearized stress] | Stress linearization; 2 | Ahead: membrane and bending parts carry goal bounds |
| Submodeling | Results of a source analysis applied to a smaller model [Ansys submodeling] | Submodeling; 2 | Equal; goal-oriented adaptivity makes routine use unnecessary |
| Solver deck exchange | Export of a Mechanical model to Nastran cards [Ansys Nastran export] | Imported solver decks; Solver deck export; 3 | Equal: decks run, and unknown cards fail by name |
| Mesh quality inspection | Mesh Quality Worksheet [Ansys Mechanical] | Discretization Fields; 1 | Ahead: there is no user mesh to repair; the discretization view shows what the plan chose |
| Weak-form modelling | Weak Form PDE interfaces [COMSOL weak form] | Static form checks; Symbolic derivatives; 0 | Ahead: units are checked at compile time and derivatives come from the form |
| Simulation apps | Application Builder apps for non-experts [COMSOL Multiphysics] | Quick studies; 1 | Ahead: a study published as a feature is versioned, checked and callable by agents |
| Rotating zones | Multiple reference frames, mixing plane and sliding mesh [Fluent rotating zones] | Rotating zones, fans and resistances; 3 to 5 | Later: laminar frames in phase 3, RANS frames and sliding interfaces in 4, mixing planes in 5 |
| Flow adjoint | Adjoint surface sensitivities driving shape changes [Siemens adjoint blog] | Flow adjoints; 3, 4 | Later, then Ahead: every flow form has a derived adjoint |
| GPU flow throughput | Single-GPU speed-ups of 8 to 15 times over CPU cores [Ansys Fluent GPU] | Solves at scale; 4 | Later: target half the published speed-up, with CPU certification |
| Antenna arrays | Unit cells with paired boundaries, Floquet ports and finite-array decomposition [PADT HFSS arrays] | Periodic structures and arrays; 5 | Later |
| Adaptive full-wave meshing | Automatic adaptive meshing [Ansys HFSS] | S-parameter goals; 4 | Equal, with a stated bound on each S-parameter |
| Parasitic extraction | RLCG extraction with SPICE model output [Ansys Q3D] | RLCG extraction; 4 | Equal, with budgets |
| Generative design by manufacturing method | Unrestricted, additive, milling, two-axis cutting and casting [Fusion manufacturing methods] | Manufacturing constraints; 1, 2 | Equal on methods; Ahead on kept interfaces, which stay exact and toleranced |
| Field surrogates | Field predictions with a confidence level [Ansys SimAI]; sub-second predictions [Luminary] | `Preview` geometry surrogates, 2; Surrogate prediction, 4 | Later on breadth; Ahead on trust, since no surrogate alone decides `SignOff` |

## Platform notes

| Platform | Risk | Decision |
| --- | --- | --- |
| Every Tier 1 CPU | SIMD width and FMA availability differ | Canonical lane order for horizontal operations, no FMA in the canonical class; FMA `CpuIsa` variants below `SignOff` |
| Every CPU | Foreign code changes the floating-point state | Checked at operation start and end; Abort and rerun |
| macOS (Metal), browsers (WebGPU) | No `f64`; WGSL may fuse, reassociate and flush | `f32` `ClassExact` at `Interactive` with CPU `f64` estimation; CPU certification for `SignOff` |
| Every GPU | Pipeline creation and known-answer tests cost start-up time | Known-answer tests run lazily before a pipeline's first result-affecting dispatch, cached per class and pipeline; until then Ops take the CPU path |
| Browsers on G3 (WebGL2) | No compute shaders | Every solve on the Wasm CPU path, declared slower |
| Browsers | Memory never shrinks; one engine module grows each phase | Heavy worker above 512 MiB and remote beyond; operation families beyond phase 1 load as lazily fetched secondary modules under PLT's module split; `Interactive` 2 s with WebGPU, 6 s CPU-only |
| Browsers | User forms compile to Wasm at run time | The engine worker needs the app origin's `'wasm-unsafe-eval'`, which PLT's content policy grants |
| Linux servers | `f64` GPUs | Vulkan `SHADER_F64` from phase 3 |
| iPadOS and Android tablets (Tier 2) | Memory, thermals, Wasm in WebKit | `Preview` and small `Interactive` solves locally; the rest remote |
| Air-gapped installs | No cloud workers | User forms compile locally; External Ops need a local Linux worker |

## Interfaces with other subsystems

| To | What | Types | Phase |
| --- | --- | --- | --- |
| ING | Spaces, measures, `solve`, `modes`, `minimize`, `continue_in`, plans and form checks; the `kernels::expr` symbolic layer | `Expr<T>`, `SolvePlan` | 0; 1 (plans, `modes`); 2 (`continue_in`) |
| ING | Budgeted regularized, gauge and critical-distance goals; property-basis propagation; singular sets and `study.regular()` | `Field<D, V>`, `ErrorBudget`, `Approx` | 1 |
| ANV | `field` and `kernels`; `Sampler`s with error and gradient bounds; `geometry_density`; reduction marking; sizing and metric Fields | `Field` | 0 (`field`, `kernels`); 1; 2 (sizing and metric Fields) |
| KLN | Operations with grades, fidelity maps, safe points, derivatives, step state and cost models; pinned calibration tables | `OpImpl`, `Differentiable` | 0 |
| COV | Forms, solvers and estimators; calibration classes, corpus and independent references; calibrated solution verification; reduction and localization; `validity_zones`; strut regime variables; `koiter_coefficient`; `std::uq`; the general operations | `Field`, `ValidityEnvelope` | 1 |
| COV | Linear dynamics outputs for vibration fatigue; EHL film Fields; rotor ladder; explicit-dynamics functionals and ensembles | `Field` | 2; 3 (EHL, drop functionals); 4 (rotor ladder); 5 (crash ensembles) |
| MEC | Phase 1 classes, two-sided eigenvalue and coupled buckling estimates, strut stress for strut-strength checks; idealizations; density topology optimization with additive and unrestricted constraints for `std::mech::generate` | `Field` | 1 |
| MEC | Multibody and rod solvers; beams and laminated shells; bolted-joint and fastener forms; tied interfaces; influence coefficients; milling, two-axis cutting and casting constraints for `std::mech::generate`; shell and ply optimization | `Field`, `Assembly` | 2; 4 (rods); 6 (ply optimization) |
| MFG | Modal analysis; topology optimization with manufacturing constraints; additive distortion and weld joint loads; thermo-elasto-plasticity; rigid multibody contact for assembly stability; filling flow with wall resolution; GCI on warpage | `Field`, `Body` | 1 (modal, topology optimization); 2; 3 (filling, GCI) |
| ELX | Network compiler and DAE solver with the temporal rule; block-triangular LU; Verilog-A constructs | `Network`, `Field` | 2 |
| ELX | Layered sheets; conjugate heat transfer; FMI and SSP runtime; `fft_solve` | `Field` | 3 |
| ELX | Electromagnetic solvers with S-parameter goals; plane-pair cavity model; RLCG extraction; electro-thermal coupling; parameter-domain battery forms; `linearize_multibody` | `Field` | 4 |
| AGT | Study Evaluations, budgets, validity zones, plan explanations, cost estimates | `SolvePlan`, `Field` | 1 |
| UIX | WGSL evaluators; vertex samples with error; singular and validity masks; exact probes; discretization Fields; `Proxy` during drags; report data | `Field` | 1 |
| ECO | `crucible:field` and, with COV, the solver and constitutive worlds; Field encodings for AP209, CGNS, Exodus, VTK and OpenFOAM; deck mapping and export for BDF, Abaqus, DMIG, OP4 and LS-DYNA keywords | `Field` | 2 |
| PLT | Grades, GPU roles, determinism corpora, resolved plans and marks for cross-class agreement; the kernel IR; sparse factorization; no-FMA penalties | `GpuPath` | 0 |

## Oracles

Oracles live in `oracles/flux/`, a separate Cargo workspace written by the oracle role, and bind first to `api` methods, the CLI and file formats, then to WIT worlds, then to the `flux-*-contract` crates ([contract section 13.2](../contract.md)). Held-out splits are chosen by a keyed hash under a key only the oracle role holds, or generated from seeds drawn at CI time, and builders see held-out results only as one aggregate verdict per work item per day. Runners are `cpu-ci` except: FLX-O-KER-4, FLX-O-SOLVE-8 and FLX-O-POST-2 in `gpu-lab`; FLX-O-KER-1, FLX-O-KER-7 and FLX-O-MESH-3 in `device-farm` on the reference machines; the browser halves of FLX-O-KER-3, FLX-O-KER-6 and FLX-O-EXEC-1 in `browser-ci`; and FLX-O-COUP-2's and FLX-O-COUP-4's coupon data from `physical` runs.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| FLX-O-ARCH-1 | std physics in a user namespace; a solver Wasm component; quick studies | Bit-identical to std; an unconstrained study fails with `StudyError` |
| FLX-O-ARCH-2 | Wasm calls to operations | Recorded: a version change invalidates the caller; replay identical |
| FLX-O-ARCH-3 | External Op solvers | Host class or `Unverified`; no attestation; outputs equal pinned references on the same image |
| FLX-O-ARCH-4 | WIT packages | Published WIT equals the WIT generated from the Rust types |
| FLX-O-FIELD-1 | Sampling | Reported bound at least the true error at every sample; gradient bounds hold |
| FLX-O-FIELD-2 | Transfer and projection | Integrals conserved to solver tolerance; reported error at least the measured one |
| FLX-O-FIELD-3 | Extremum enclosures, region extraction | Enclosures contain the true extremum; extracted bounds hold under dense sampling |
| FLX-O-FIELD-4 | Geometry-driving Fields | Anvil's bound at least the measured deviation |
| FLX-O-FIELD-5 | Canonical storage | decode(encode(v)) equals v bit for bit; reloads give identical dependents |
| FLX-O-FIELD-6 | Label invariance | Re-randomized names leave every golden product's Fields and checks identical |
| FLX-O-ERR-1 | Equilibrated energy bounds | Effectivity between 1 and 2 in every case, ν = 0.49 and 0.4999 included; 1.5 (target) |
| FLX-O-ERR-2 | Linear goals, `Guaranteed` algebraic parts | Bound at least the true error in every case, including runs with deliberately loose solver tolerances; totals `Estimated` wherever a part is |
| FLX-O-ERR-3 | Calibrated DWR at both fidelities; refinement confirmation | Zero undershoots in at least 300 held-out cases per class; 10⁴ CMA-ES evaluations (fixed seeds) find no undershoot in an envelope; a fillet-radius sweep's budget covers the converged raw peak; a sharp-edged machined bracket decides with ρ from wall thickness; under-calibrated entries yield `CalibrationUnconfirmed`; the canonical bracket's check region contains the web-root fillet |
| FLX-O-ERR-4 | Singular sets | Seeded singular edges flagged, smooth controls not; a 90° corner flagged under shear traction only; Hertz contact unflagged, a flat punch flagged; a maximum placed on an exclusion boundary yields `MaximumAtExclusion`; an imported filleted bracket's check decides |
| FLX-O-ERR-5 | Calibration tables | Each entry: 300 held-out samples, 20% optimizer-generated, zero undershoots, coverage reported per envelope feature bin; every reference from an independent fitted code with an exponentially converging p-sequence and recorded code and mesh hash |
| FLX-O-ERR-6 | Temporal estimates, 100 periods of an oscillator and a wave | Zero undershoots in 300 held-out cases per class |
| FLX-O-ERR-7 | `Preview` results | Never `Pass` or `Fail`; never shared |
| FLX-O-ERR-8 | Solution verification on benchmark flows and moulding warpage | Calibrated GCI bands by coarsening cover the reference with zero undershoots in 300 held-out cases per family; verification costs less than the production solve; adapted runs `Indicator` |
| FLX-O-ERR-9 | Validity zones (COV's zone-semantics row cites it) | Match COV's labelled cases; `Refuse` yields `ValidityError::OutsideEnvelope`; excursions between output steps caught |
| FLX-O-ERR-10 | Cross-class agreement | PLT's tolerances hold on the determinism corpus |
| FLX-O-ERR-11 | Property-basis propagation | Enclosures contain 50 sampled-property solves on each of 20 cases, sign changes and a resonance-crossing case included; non-monotone cases subdivide or report `NonMonotone` |
| FLX-O-ERR-12 | Critical-distance goals | Point, line, area and volume operators reproduce analytic notch-field values within 1%; a mismatched method fails with `CriticalDistanceMismatch` |
| FLX-O-FORM-1 | Static form checks | 100 textbook forms pass; seeded errors fail with the right code |
| FLX-O-FORM-2 | Symbolic layer and derivatives | Taylor order 2 ± 0.1 for every operator; equal expressions hash-cons to one node |
| FLX-O-FORM-3 | `local_solve`, Wasm tangents | Taylor tests pass; quadratic Newton convergence on a plasticity benchmark |
| FLX-O-FORM-4 | UFL coverage | Every demo of the pinned FEniCS and Firedrake releases expressible |
| FLX-O-FORM-5 | Parameter-domain forms | SPMe and DFN voltage within 1 mV of PyBaMM on shared parameter sets |
| FLX-O-KER-1 | CEED problems plus immersed elasticity | Under 10⁻¹² from assembled references; both CEED rows of contract section 13.3 |
| FLX-O-KER-2 | No-FMA penalty, `CpuIsa` variants | Penalty published per degree and ISA; variants within 10⁻¹² of canonical |
| FLX-O-KER-3 | CPU kernel determinism | Bit-identical across threads, ISAs and targets |
| FLX-O-KER-4 | GPU paths | Known-answer tests run before first use; injected NaN detected; CPU budgets cover the gap to canonical solves |
| FLX-O-KER-5 | Floating-point environment | A planted flush-to-zero library causes Abort and rerun |
| FLX-O-KER-6 | User-form speed | 1.5 times memory-bound, 2.5 times (AVX2) and 5 times (AVX-512) compute-bound (targets); a 20% regression blocks |
| FLX-O-KER-7 | Solves at scale | Contract section 13.3's `SignOff` linear static and flow throughput rows on their named machines |
| FLX-O-PLAN-1 | Plans and overrides | Same plan in every class; old plan versions reproduce old results |
| FLX-O-PLAN-2 | Reduction marking | Known cases marked as expected; plates under pressure, pressurized cylinders and a free plate in modal analysis mark `Shell` |
| FLX-O-PLAN-3 | Mixed-dimensional couplings | Patch tests pass; a welded T-joint, a cylinder-to-flange junction and a gusseted node stay inside the reduction part |
| FLX-O-PLAN-4 | Reduction error | Zero undershoots against 3D references on 300 held-out frames and shells, an indeterminate portal frame with semi-rigid joints included |
| FLX-O-PLAN-5 | Wall-resolution rules | On a heated cavity and a 3D fill, one more refinement moves the quantity less than its budget |
| FLX-O-PLAN-6 | Submodeling | A shell frame with a solid weld detail and a supplier-load case match full 3D solves within the reported budget |
| FLX-O-SYM-1 | Planar, axisymmetric, symmetry and cyclic reductions | Lamé thick cylinder, NAFEMS axisymmetric cases and a cyclic bladed-disc modal case agree with full 3D models within the 3D budget; a non-symmetric load fails with `SymmetryBroken` |
| FLX-O-DISC-1 | Manufactured solutions | Rate within 0.1 of theory over three refinements, above 10³ times round-off |
| FLX-O-DISC-2 | Immersed iterations, cut quadrature | Iterations within 1.5 times over 1,000 shifts for p = 1 to 4; quadrature within 10⁻¹² of Algoim |
| FLX-O-DISC-3 | Shifted boundary | Interior rates within 0.1 of theory; never decides a check |
| FLX-O-DISC-4 | Patch tests | Fitted, immersed and spline exact to solver tolerance; finite cell within O(α) |
| FLX-O-DISC-5 | NAFEMS P18 static, thermal and free vibration [NAFEMS benchmarks] | Within 1% at `SignOff` |
| FLX-O-DISC-6 | Shells, beams, layered sheets | Within 1% of converged references at p ≥ 3 and 2% at p ≤ 2, on 20 cases |
| FLX-O-DISC-7 | Explicit dynamics | Energy error under 1%; cut-cell step within 10% of uncut over 1,000 shifts; regime extrema under 2% of solve time |
| FLX-O-DISC-8 | Electromagnetics | Cavity modes within 0.1%; S-parameters within 0.01 of Palace; S-parameter bounds with zero undershoots on 300 held-out cases; Mie within 1%; cut-independent FDTD step |
| FLX-O-DISC-9 | Magnetodynamics with motion | Torque and loss within 5% on TEAM problems 24 and 30a [TEAM problems]; solenoidal sources |
| FLX-O-DISC-10 | Finite volume, free surfaces | Cell and filled-volume conservation to solver tolerance |
| FLX-O-DISC-11 | General operations, particles | Thread-count independence; Philox vectors; SPHERIC 3D dam break and granular collapse within 10% |
| FLX-O-DISC-12 | Boundary elements | Sphere scattering within 1% of Mie; cost below N^1.2 from 10⁴ to 10⁶ unknowns |
| FLX-O-EM-1 | Periodic structures and arrays | Infinite dipole array active reflection and an FSS transmission curve against published references within 2% |
| FLX-O-EM-2 | RLCG extraction | Partial inductance of parallel bars and a coaxial line within 1% of analytic values; a busbar within the stated budget of a published case |
| FLX-O-EM-3 | Plane-pair cavity model | Rectangular plane-pair resonances within 0.5% of analytic values; port impedance against a 3D full-wave reference within budget |
| FLX-O-FLOW-1 | Rotating zones, fans and resistances | Rotating-frame cases match rotating-domain transients in the mean within 2%; fan operating points on the declared curve |
| FLX-O-FLOW-2 | Rotor aerodynamics | Thrust and torque against published propeller data within each rung's envelope |
| FLX-O-EHL-1 | Elastohydrodynamic lubrication | Central and minimum film thickness within 5% of published EHL benchmarks; the cavitation condition holds at convergence |
| FLX-O-MESH-1 | Adaptivity | Optimal rates on L-shape and Fichera corners; stagnation reported |
| FLX-O-MESH-2 | Solution transfer | Conservation to solver tolerance; reported error at least the measured one |
| FLX-O-MESH-3 | `Interactive` stage budgets | Within budget on the three benchmarks with five checked goals (targets); 1.5 times a budget blocks |
| FLX-O-SOLVE-1 | Direct solvers | Round-off backward error; identical under two cache settings and any thread count |
| FLX-O-SOLVE-2 | Multigrid and AMG | h- and p-independent iterations on BP3 and BP5; thread-independent aggregates; iterations against hypre |
| FLX-O-SOLVE-3 | Navier–Stokes preconditioners | Cavity iterations within 2 times from Re = 10 to 1,000 |
| FLX-O-SOLVE-4 | Nonlinear solvers, bifurcations | Perfect column bifurcates at the Euler load, imperfect one follows its branch; phase 1 non-convex forms `Unsupported`; a wrongly declared convex form fails with `ConvexityViolated` |
| FLX-O-SOLVE-5 | Time integrators | Observed orders match theory; events at identical times across classes |
| FLX-O-SOLVE-6 | Eigen-solvers and estimates | NAFEMS free vibration within 0.5%; two-sided estimates cover Nitsche-clamped plate frequencies that fall below the reference; coupled buckling estimates cover a notched plate under compression; estimates on Euler columns cover 300 held-out cases with zero undershoots; Koiter coefficients within 2%; Crouzeix–Raviart bounds lie below reference cavity eigenvalues |
| FLX-O-SOLVE-7 | Contact | Hertz peak pressure within 1%, immersed at p > 2 included; unestimated penalty never supports `SignOff` |
| FLX-O-SOLVE-8 | GPU solves, CPU certification | Certified verdicts equal canonical verdicts; stalls fall back |
| FLX-O-SOLVE-9 | Bolted-joint forms | Bolt forces inside their bounds against 3D mortar-contact models in 300 held-out joints; opening yields `JointOpened` |
| FLX-O-SOLVE-10 | Fracture hooks | J-integral of a centre-cracked plate within 1% of the analytic value; cohesive-zone peel within 5% of a published case |
| FLX-O-IDEAL-1 | Remote points, point masses, springs | Reactions and displacements equal a fitted RBE2 or RBE3 reference on 20 cases; a distributing coupling leaves a free plate's eigenvalues unchanged within 10⁻⁸; modal mass with point masses matches the analytic value |
| FLX-O-IDEAL-2 | Bushings, fasteners, spot welds, tied interfaces | A two-block tied patch test passes; a bolted lap joint and a spot-welded hat section match fitted mortar references within the fitted budget; unconfirmed interfaces block `SignOff` |
| FLX-O-DYN-1 | Linear perturbation; damped and gyroscopic modes | Spinning-disc and pressurized-shell frequencies within 1% of references; a rotor's Campbell diagram matches a published case |
| FLX-O-DYN-2 | Frequency response, base motion, random vibration, damping | NAFEMS forced-vibration cases within 1%; SDOF closed forms within 10⁻⁶; undamped resonance in a band fails |
| FLX-O-DYN-3 | Response spectrum | Two-DOF SRSS and CQC cases equal hand combinations; missing-mass correction recovers the static response |
| FLX-O-DYN-4 | Explicit-dynamics goals | Filtered acceleration and crush-force functionals converge under coarsened GCI on drop and crush benchmarks; ensemble statistics stable to their stated interval under reseeding |
| FLX-O-NET-1 | Network compilation | Index-3 pendulum reduced; clutch and diode bridge reinitialize consistently; re-translation after a one-parameter edit of a 50,000-equation Network under 1 s (target) |
| FLX-O-NET-2 | DAE integration | Analytic RLC and drivetrain within 10⁻⁶; ngspice references within 0.1% |
| FLX-O-NET-3 | Block-triangular LU | Refactorization bit-identical to fresh factorization |
| FLX-O-MBD-1 | Multibody dynamics | Order within 0.1 of 2 on heavy top and slider–crank; redundancy reported |
| FLX-O-MBD-2 | Rods | Elastica, helical buckling and hanging cable within 1% |
| FLX-O-COUP-1 | Coupling and activation | Partitioned and monolithic agree within budgets; Turek–Hron within 5% [Turek and Hron 2006]; a conjugate-heat case agrees across both forms; a self-heating strip returns `Runaway` at its turning point |
| FLX-O-COUP-2 | Homogenization and lattices | Tensors within 1% of full unit cells; strut peaks inside budget on 20 held-out lattices; CT-fitted joints hold on cells from a held-out build plate; sheet shells inside their envelopes |
| FLX-O-COUP-3 | FMI and SSP | Reference FMUs on every Tier 1 OS; SSP round trips; master error order |
| FLX-O-COUP-4 | Additive and weld distortion | Coupon distortion within coupon scatter on held-out coupons; joint loads within 5% of 3D joint models |
| FLX-O-OPT-1 | Derivatives | Taylor order 2 ± 0.1 for every `Differentiable` operation |
| FLX-O-OPT-2 | Topology optimization | MBB beam and 3D cantilever within 2% of published compliance |
| FLX-O-OPT-3 | Adjoints and step state | Steady adjoint 1.2 times a forward solve (target), 2 times blocks; resumes bit-identical |
| FLX-O-OPT-4 | Flow adjoints | Taylor order 2 on a duct pressure-drop goal; agreement with finite-difference sensitivities on a backward-facing step within 2% |
| FLX-O-OPT-5 | Shell sizing and laminate optimization | A thickness-sized plate matches a published optimum within 2%; ply rules hold in every optimized laminate |
| FLX-O-OPT-6 | Manufacturing constraints | Outcomes for each method pass the method's own geometric test (overhang, tool access, extrusion, draw) on 20 cases |
| FLX-O-UQ-1 | Sensitivity and rare events | Ishigami indices; correlated Shapley case; known failure probabilities |
| FLX-O-UQ-2 | Multilevel Monte Carlo | Cost exponent within 0.2 of theory |
| FLX-O-UQ-3 | Worst-case propagation | On 20 analytic responses, stationary ones included, the bound contains the maximum found by interval branch-and-bound over the box, or the result is `NonlinearResponse` |
| FLX-O-ROM-1 | Reduced models | Certified bounds hold; 100 times faster at under 1% error (target), 10 times blocks |
| FLX-O-ROM-2 | Surrogates | Nominal coverage held out; 10⁴ CMA-ES evaluations per surrogate find no false `SignOff` `Pass`; both bound costs reported |
| FLX-O-ROM-3 | `Preview` geometry surrogates | Never decide a check; never cross a repository's labels |
| FLX-O-EXEC-1 | Aborts and resumption | Injected faults never change cached values; resumes bit-identical |
| FLX-O-EXEC-2 | Cancellation | 100 ms (target); 250 ms blocks |
| FLX-O-POST-1 | Post-processing and reports | Reactions balance loads; probes exact on analytic Fields; reports complete and re-rendered identically |
| FLX-O-POST-2 | Display and discretization Fields | Within the stated interpolation error of exact CPU samples; discretization Fields match the plan |
| FLX-O-POST-3 | Load-case combination | Hand-combined frame cases equal `combine` and `envelope`; a nonlinear case fails with `NonlinearSuperposition` |
| FLX-O-POST-4 | Stress linearization | Membrane and bending of a thick cylinder within their bounds of the analytic values |
| FLX-O-DECK-1 | Imported solver decks | The pinned NAFEMS verification decks run within 1% of their reference values, card family by card family; an unknown card fails with `UnmappedCard` |
| FLX-O-DECK-2 | Solver deck export | Exported decks read back through pyNastran and re-imported reproduce the study within its budget |

## Phasing

Capabilities that several tabs phase, and the parity floor, take their phase from [contract section 13.4](../contract.md).

| Phase | Flux contribution to the gate |
| --- | --- |
| 0 | Determinism suite green for Flux kernels; unit errors in forms fail to compile; kernel IR v0 and `kernels::expr` frozen; H¹ elements and manufactured solutions; CEED baselines and no-FMA penalties; the measurement that decides WGSL elasticity; nothing frozen before the Flux rename |
| 1 | GP1: aggregated CutFEM, calibrated DWR at both fidelities with refinement confirmation, singular sets and `study.regular()`, gauge goals, eigen-solvers with two-sided and coupled estimates, verified convex Newton, planar and axisymmetric models, remote points, point masses and springs. GP2: density topology optimization, steady adjoints, homogenization, beam lattices with CT-fitted joints, strut stress and lattice buckling. The six calibration classes |
| 2 | GP3: fitted tetrahedra with mortar contact, rigid multibody, drivetrain Networks, transient solvers and adjoints. GP4: beams, shells, reduction error, thermo-elasto-plasticity, weld joint loads, load-case combination. Also the phase 2 parity floor: bushings, fasteners and spot welds, tied interfaces, stress linearization, submodeling, `Preview` surrogates and shell sizing; linear dynamics and cyclic modal analysis; additive distortion; 10M-DOF `SignOff` solves |
| 3 | GP5: filling with wall resolution, warpage by calibrated GCI, explicit drop functionals, laminar conjugate heat transfer, fans, laminar rotating frames and flow adjoints, layered sheets, circuit DAEs, FDTD, FMU import, 50M-DOF and flow throughput rows. Also Helmholtz solvers, solver decks and EHL |
| 4 | GP6: turbulent conjugate heat transfer, RANS rotating frames, sliding interfaces and adjoints, the rotor ladder, electro-thermal coupling, RLCG extraction, S-parameter goals, FMU export and SSP, SPMe forms, fluid–structure interaction, magnetodynamics with motion, rods, nonsmooth multibody, surrogates with per-prediction bounds, GPU flow certified on the CPU. Also the plane-pair cavity model |
| 5 and later | GP7 MEMS pull-in; GP8 frames with code combinations; GP9 crash with erosion and imperfection ensembles; DFN cells; Floquet arrays and mixing planes; ply optimization (6); free surfaces beyond filling; particles; FE²; IPC for GP16 |

## Open questions

1. **Guaranteed bounds on cut cells.** Equilibrated a posteriori proofs on hanging nodes and cut cells are open research, which contract section 13.2 defers past phase 1. Until a published proof covers aggregated CutFEM, energy parts on cut cells stay `Indicator` and goal checks rest on calibrated DWR. Waits on: the research literature.
2. **Flux's name.** "Flux" collides with existing products, so `flux::` names and WIT packages freeze only after the phase 0 rename. Waits on: trademark clearance at the phase 0 gate.
3. **Paywalled definitions.** The channel frequency classes of SAE J211 and the distances of the theory of critical distances' point and line methods are stated from secondary knowledge and marked unverified. Checks declare their filter class and method explicitly meanwhile. Waits on: the SAE J211 text and an accessible primary source for the critical-distance operators.

## Contract change requests

None.

## Sources

| Key | Title | URL | Date opened |
| --- | --- | --- | --- |
| CEED bake-off | CEED, "CEED Bake-off Problems (Benchmarks)" | https://ceed.exascaleproject.org/bps/ | by 2026-10-11 |
| MFEM features | MFEM, "Features" | https://mfem.org/features/ | by 2026-10-11 |
| faer documentation | faer 0.24.4 documentation | https://docs.rs/faer/latest/faer/ | by 2026-10-11 |
| CubeCL repository | CubeCL repository | https://github.com/tracel-ai/cubecl | by 2026-10-11 |
| UFL documentation | UFL documentation | https://docs.fenicsproject.org/ufl/main/ | by 2026-10-11 |
| FMI standard | FMI Standard home page | https://fmi-standard.org/ | by 2026-10-11 |
| FMI 3.0.2 | FMI 3.0.2 specification | https://fmi-standard.org/docs/3.0.2/ | by 2026-10-11 |
| SSP standard | SSP Standard home page | https://ssp-standard.org/ | by 2026-10-11 |
| libCEED API | libCEED API documentation | https://libceed.org/en/latest/libCEEDapi/ | by 2026-10-11 |
| Kolev et al. 2021 | Kolev et al., "Efficient Exascale Discretizations: High-Order Finite Element Methods" | https://arxiv.org/abs/2109.04996 | by 2026-10-11 |
| Fischer et al. 2020 | Fischer et al., "Scalability of High-Performance PDE Solvers" | https://arxiv.org/abs/2004.06722 | by 2026-10-11 |
| deal.II matrix-free | deal.II matrix-free module documentation | https://www.dealii.org/current/doxygen/deal.II/group__matrixfree.html | by 2026-10-11 |
| WGSL specification | W3C, WGSL specification (partially read) | https://www.w3.org/TR/WGSL/ | by 2026-10-11 |
| WebGPU floating-point primer | WebGPU conformance test suite, floating-point primer | https://kdab.searchfox.org/firefox-main/source/dom/webgpu/tests/cts/checkout/docs/fp_primer.md | by 2026-10-11 |
| wgpu Features | wgpu `Features` documentation | https://wgpu.rs/doc/wgpu/struct.Features.html | by 2026-10-11 |
| wgpu 30.0.1 | wgpu 30.0.1 documentation | https://docs.rs/wgpu/latest/ | by 2026-10-11 |
| Rust RFC 3514 | Rust RFC 3514, "Float semantics" | https://rust-lang.github.io/rfcs/3514-float-semantics.html | by 2026-10-11 |
| ReproBLAS | ReproBLAS | https://bebop.cs.berkeley.edu/reproblas/ | by 2026-10-11 |
| PETSc licence | PETSc licence | https://petsc.org/release/install/license/ | by 2026-10-11 |
| hypre documentation | hypre documentation | https://hypre.readthedocs.io/en/latest/ | by 2026-10-11 |
| SUNDIALS licence | SUNDIALS licence | https://computing.llnl.gov/projects/sundials/license | by 2026-10-11 |
| Smears and Vohralík 2020 | Smears and Vohralík, "Simple and robust equilibrated flux a posteriori estimates for singularly perturbed reaction–diffusion problems", ESAIM: M2AN 54(6), 2020 | https://www.numdam.org/item/M2AN_2020__54_6_1951_0 | by 2026-10-11 |
| Becker and Rannacher 2001 | Becker and Rannacher, "An optimal control approach to a posteriori error estimation in finite element methods", Acta Numerica 10, 2001 | https://www.cambridge.org/core/journals/acta-numerica/article/abs/an-optimal-control-approach-to-a-posteriori-error-estimation-in-finite-element-methods/5C67A03F528C6FA69F37A97DF5C3BE19 | by 2026-10-11 |
| Munch et al. 2022 | Munch, Heister, Prieto Saavedra, Kronbichler, "Efficient distributed matrix-free multigrid methods on locally refined meshes for FEM computations" | https://arxiv.org/abs/2203.12292 | by 2026-10-11 |
| Pazner et al. 2022 | Pazner, Kolev, Dohrmann, "Low-order preconditioning for the high-order finite element de Rham complex" | https://arxiv.org/abs/2203.02465 | by 2026-10-11 |
| Atallah et al. 2020 | Atallah, Canuto, Scovazzi, "Analysis of the Shifted Boundary Method for the Poisson Problem in General Domains" | https://arxiv.org/abs/2006.00872 | by 2026-10-11 |
| Burman et al. CutFEM | Burman, Claus, Hansbo, Larson, Massing, "CutFEM: Discretizing Geometry and Partial Differential Equations" (record) | https://www.simula.no/research/cutfem-discretizing-geometry-and-partial-differential-equations | by 2026-10-11 |
| Cockburn et al. 2009 | Cockburn, Gopalakrishnan, Lazarov, "Unified hybridization of discontinuous Galerkin, mixed and continuous Galerkin methods for second order elliptic problems" | https://conservancy.umn.edu/items/c0fca618-a7ca-40d0-b701-7c94235cd97b | by 2026-10-11 |
| Bazilevs et al. 2006 | Bazilevs, Beirão da Veiga, Cottrell, Hughes, Sangalli, "Isogeometric Analysis: Approximation, stability and error estimates for h-refined meshes" (report) | https://www.oden.utexas.edu/media/reports/2006/0604.pdf | by 2026-10-11 |
| Homolya et al. 2017 | Homolya, Mitchell, Luporini, Ham, "TSFC: a structure-preserving form compiler" | https://arxiv.org/abs/1705.03667 | by 2026-10-11 |
| Farrell et al. 2013 | Farrell, Ham, Funke, Rognes, "Automated derivation of the adjoint of high-level transient finite element programs" | https://arxiv.org/abs/1204.5577 | by 2026-10-11 |
| Zhang and Constantinescu 2021 | Zhang and Constantinescu, "Optimal Checkpointing for Adjoint Multistage Time-Stepping Schemes" | https://arxiv.org/abs/2106.13879 | by 2026-10-11 |
| Aage et al. 2017 | Aage, Andreassen, Lazarov, Sigmund, "Giga-voxel computational morphogenesis for structural design", Nature 550, 2017 | https://www.nature.com/articles/nature23911 | by 2026-10-11 |
| Giles 2015 | Giles, "Multilevel Monte Carlo methods" | https://arxiv.org/abs/1304.5472 | by 2026-10-11 |
| Angelopoulos and Bates 2021 | Angelopoulos and Bates, "A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification" | https://arxiv.org/abs/2107.07511 | by 2026-10-11 |
| Carson and Higham 2018 | Carson and Higham, "Accelerating the Solution of Linear Systems by Iterative Refinement in Three Precisions" | https://eprints.maths.manchester.ac.uk/2629/ | by 2026-10-11 |
| NAFEMS benchmarks | NAFEMS, "The Standard NAFEMS Benchmarks" (P18) | https://www.nafems.org/publications/resource_center/p18/ | by 2026-10-11 |
| JAX-FEM repository | JAX-FEM repository | https://github.com/deepmodeling/jax-fem | by 2026-10-11 |
| DOLFINx repository | DOLFINx repository | https://github.com/FEniCS/dolfinx | by 2026-10-11 |
| preCICE | preCICE documentation | https://precice.org/docs.html | by 2026-10-11 |
| Mmg | Mmg home page | https://www.mmgtools.org/ | by 2026-10-11 |
| NGSolve | NGSolve home page | https://www.ngsolve.org/ | by 2026-10-11 |
| bempp-rs repository | bempp-rs repository | https://github.com/bempp/bempp-rs | by 2026-10-11 |
| Algoim | Algoim (Saye's quadrature and closest-point methods) | https://algoim.github.io/ | by 2026-10-11 |
| Palace documentation | Palace documentation | https://awslabs.github.io/palace/stable/ | by 2026-10-11 |
| Barber et al. 2019 | Barber, Candès, Ramdas, Tibshirani, "The limits of distribution-free conditional predictive inference" | https://arxiv.org/abs/1903.04684 | by 2026-10-11 |
| Tibshirani et al. 2019 | Tibshirani, Barber, Candès, Ramdas, "Conformal Prediction Under Covariate Shift" | https://arxiv.org/abs/1904.06019 | by 2026-10-11 |
| CCSA Camry | CCSA, 2015 Toyota Camry finite element model | https://www.ccsa.gmu.edu/models/2015-toyota-camry/ | by 2026-10-11 |
| Farrell et al. 2019 | Farrell, Mitchell, Wechsung, "An augmented Lagrangian preconditioner for the 3D stationary incompressible Navier-Stokes equations at high Reynolds number" | https://arxiv.org/abs/1810.03315 | by 2026-10-11 |
| Project Chrono | Project Chrono repository | https://github.com/projectchrono/chrono | by 2026-10-11 |
| Gazzola et al. PyElastica | PyElastica repository | https://github.com/GazzolaLab/PyElastica | by 2026-10-11 |
| NASA GCI tutorial | NASA Glenn, "Examining Spatial (Grid) Convergence" (Roache's grid convergence index) | https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html | by 2026-10-11 |
| OpenModelica flags | OpenModelica compiler flags (index reduction methods) | https://openmodelica.org/doc/OpenModelicaUsersGuide/latest/omchelptext.html | by 2026-10-11 |
| SuiteSparse | SuiteSparse repository | https://github.com/DrTimothyAldenDavis/SuiteSparse | by 2026-10-11 |
| PyBaMM repository | PyBaMM repository | https://github.com/pybamm-team/PyBaMM | by 2026-10-11 |
| Brüls et al. 2012 | Brüls, Cardona, Arnold, "Lie Group Generalized-α Time Integration of Constrained Flexible Multibody Systems", Mechanism and Machine Theory 48, 2012 | https://ri.conicet.gov.ar/handle/11336/18837 | by 2026-10-11 |
| Bertrand et al. 2019 | Bertrand, Kober, Moldenhauer, Starke, "Weakly symmetric stress equilibration and a posteriori error estimation for linear elasticity" | https://arxiv.org/abs/1808.02655 | by 2026-10-11 |
| Papež et al. 2020 | Papež, Rüde, Vohralík, Wohlmuth, "Sharp algebraic and total a posteriori error bounds for h and p finite elements via a multilevel approach", CMAME 371, 2020 (record) | https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.cma.2020.113243?fields=title,abstract,year,authors | by 2026-10-11 |
| Arnold and Winther 2002 | Arnold and Winther, "Mixed finite elements for elasticity", Numerische Mathematik 92, 2002 (Crossref record) | https://api.crossref.org/works?query.bibliographic=Arnold+Winther+Mixed+finite+elements+for+elasticity+Numerische+Mathematik&rows=2 | by 2026-10-11 |
| Hu and Zhang 2015 | Hu and Zhang, "A family of symmetric mixed finite elements for linear elasticity on tetrahedral grids", Science China Mathematics 58, 2015 (Crossref record) | https://api.crossref.org/works?query.bibliographic=Hu+Zhang+family+of+conforming+mixed+finite+elements+for+linear+elasticity+on+tetrahedral+grids&rows=2 | by 2026-10-11 |
| Heuveline and Rannacher 2001 | Heuveline and Rannacher, "A posteriori error control for finite element approximations of elliptic eigenvalue problems", Advances in Computational Mathematics 15, 2001 (Crossref record) | https://api.crossref.org/works?query.bibliographic=Heuveline+Rannacher+posteriori+error+control+eigenvalue+problems&rows=3 | by 2026-10-11 |
| Carstensen and Gedicke 2014 | Carstensen and Gedicke, "Guaranteed lower bounds for eigenvalues", Mathematics of Computation 83, 2014 (Crossref record) | https://api.crossref.org/works?query.bibliographic=Guaranteed+lower+bounds+for+eigenvalues+Carstensen+Gedicke&rows=2 | by 2026-10-11 |
| Williams 1952 | Williams, "Stress Singularities Resulting From Various Boundary Conditions in Angular Corners of Plates in Extension", Journal of Applied Mechanics 19, 1952 (Crossref record) | https://api.crossref.org/works?query.bibliographic=Stress+singularities+resulting+from+various+boundary+conditions+in+angular+corners+of+plates+in+extension&rows=2 | by 2026-10-11 |
| Burman et al. 2020 | Burman, Hansbo, Larson, "Explicit Time Stepping for the Wave Equation using CutFEM with Discrete Extension" | https://arxiv.org/abs/2011.05386 | by 2026-10-11 |
| de Prenter et al. 2019 | de Prenter et al., "Scalable multigrid methods for immersed finite element methods and immersed isogeometric analysis", Computational Mechanics, 2019 | https://arxiv.org/abs/1903.10977 | by 2026-10-11 |
| Zagorodnov et al. 2003 | Zagorodnov, Schuhmann, Weiland, "A uniformly stable conformal FDTD-method in Cartesian grids", 2003 (Crossref record) | https://api.crossref.org/works?query.bibliographic=A+uniformly+stable+conformal+FDTD-method+in+Cartesian+grids&rows=2 | by 2026-10-11 |
| Brüls et al. 2014 | Brüls, Acary, Cardona, "Simultaneous enforcement of constraints at position and velocity levels in the nonsmooth generalized-α scheme", CMAME 281, 2014 (Crossref record) | https://api.crossref.org/works?query.bibliographic=Simultaneous+enforcement+of+constraints+at+position+and+velocity+levels+in+the+nonsmooth+generalized-alpha+scheme&rows=2 | by 2026-10-11 |
| Hwang and Cai 2005 | Hwang and Cai, "A parallel nonlinear additive Schwarz preconditioned inexact Newton algorithm for incompressible Navier–Stokes equations", JCP 204, 2005 (Crossref record) | https://api.crossref.org/works?query.bibliographic=Additive+Schwarz+preconditioned+inexact+Newton+methods+for+nonlinear+partial+differential+equations+Cai+Keyes&rows=2 | by 2026-10-11 |
| Algoim licence | Algoim licence | https://raw.githubusercontent.com/algoim/algoim/master/LICENSE | by 2026-10-11 |
| FluidX3D licence | FluidX3D licence | https://raw.githubusercontent.com/ProjectPhysX/FluidX3D/master/LICENSE.md | by 2026-10-11 |
| XLB repository | XLB repository | https://github.com/Autodesk/XLB | by 2026-10-11 |
| Li et al. 2020 | Li et al., "Incremental Potential Contact", ACM Transactions on Graphics, 2020 | https://ipc-sim.github.io/ | by 2026-10-11 |
| ngsxfem repository | ngsxfem repository | https://github.com/ngsxfem/ngsxfem | by 2026-10-11 |
| GridapEmbedded licence | GridapEmbedded.jl licence | https://raw.githubusercontent.com/gridap/GridapEmbedded.jl/master/LICENSE.md | by 2026-10-11 |
| TopOpt_in_PETSc | TopOpt_in_PETSc repository | https://github.com/topopt/TopOpt_in_PETSc | by 2026-10-11 |
| pyMOR repository | pyMOR repository | https://github.com/pymor/pymor | by 2026-10-11 |
| RBniCS repository | RBniCS repository | https://github.com/RBniCS/RBniCS | by 2026-10-11 |
| OpenTURNS repository | OpenTURNS repository | https://github.com/openturns/openturns | by 2026-10-11 |
| Dakota repository | Dakota repository | https://github.com/snl-dakota/dakota | by 2026-10-11 |
| OMSimulator repository | OMSimulator repository | https://github.com/OpenModelica/OMSimulator | by 2026-10-11 |
| Meep repository | Meep repository | https://github.com/NanoComp/meep | by 2026-10-11 |
| openEMS repository | openEMS repository | https://github.com/thliebig/openEMS | by 2026-10-11 |
| Bempp-cl repository | Bempp-cl repository | https://github.com/bempp/bempp-cl | by 2026-10-11 |
| Scroggs et al. 2017 | Scroggs, Betcke, Burman, Śmigaj, van 't Wout, "Software frameworks for integral equations in electromagnetic scattering based on Calderón identities" | https://arxiv.org/abs/1703.10900 | by 2026-10-11 |
| Ansys remote points | Ansys Mechanical User's Guide 2024 R2, "Geometry Behavior" (remote point behaviors) | https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_Geometry_Behavior.html | 2026-10-12 |
| Ansys Nastran export | Ansys Mechanical User's Guide 2024 R2, "NASTRAN export supported features" | https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_NASTRAN_export_supported_features.html | 2026-10-12 |
| Ansys Mechanical | Ansys Mechanical product page | https://ansys.synopsys.com/products/structures/ansys-mechanical | 2026-10-12 |
| Abaqus axisymmetric elements | Abaqus Analysis User's Guide 2016, "Axisymmetric solid element library" | https://ceae-server.colorado.edu/v2016/books/usb/pt06ch28s01ael05.html | 2026-10-12 |
| COMSOL symmetry | COMSOL blog, "Exploiting symmetry to simplify magnetic field modeling" | https://www.comsol.com/blogs/exploiting-symmetry-simplify-magnetic-field-modeling | 2026-10-12 |
| Ansys linearized stress | Ansys Mechanical User's Guide 2024 R2, "Linearized Stresses" | https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_linearized_stresses.html | 2026-10-12 |
| Ansys submodeling | Ansys Mechanical User's Guide 2024 R2, "Submodeling" | https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_submodeling.html | 2026-10-12 |
| Ansys solution combination | Ansys Mechanical User's Guide 2024 R2, "Solution Combinations" | https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_Solution_Combinations.html | 2026-10-12 |
| Fluent rotating zones | Ansys Fluent Theory Guide 2024 R2, flows using multiple reference frames | https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/flu_th/flu_th_sec_mzrrf.html | 2026-10-12 |
| Abaqus general contact | Abaqus/CAE User's Guide 2017, "Understanding general contact" | https://abaqus-docs.mit.edu/2017/English/SIMACAEGSARefMap/simagsa-c-cntgeneral.htm | 2026-10-12 |
| Siemens adjoint blog | Siemens Simcenter blog, "Adjoint shape optimization for improved car aerodynamics" | https://blogs.sw.siemens.com/simcenter/adjoint-shape-optimization-for-improved-car-aerodynamics/ | 2026-10-12 |
| PADT HFSS arrays | PADT blog, "Efficient and accurate simulation of antenna arrays in HFSS" (third party) | https://www.padtinc.com/blog/efficient-and-accurate-simulation-of-antenna-arrays-in-hfss/ | 2026-10-12 |
| Ansys Q3D | Ansys Q3D Extractor product page | https://ansys.synopsys.com/products/electronics/ansys-q3d-extractor | 2026-10-12 |
| Ansys HFSS | Ansys HFSS product page | https://ansys.synopsys.com/products/electronics/ansys-hfss | 2026-10-12 |
| Ansys SimAI | Ansys SimAI product page | https://ansys.synopsys.com/products/simai | 2026-10-12 |
| Luminary | Luminary Cloud home page | https://luminary.ai/ | 2026-10-12 |
| COMSOL weak form | COMSOL 6.4 Reference Manual, "The Weak Form PDE Interface" | https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_ref_equationbased.32.023.html | 2026-10-12 |
| COMSOL Multiphysics | COMSOL Multiphysics product page (Application Builder) | https://www.comsol.com/comsol-multiphysics | 2026-10-12 |
| Ansys Fluent GPU | Ansys blog, "Unleashing the full power of GPUs for Ansys Fluent, part 2" (vendor-stated figures) | https://ansys.synopsys.com/blog/unleashing-the-full-power-of-gpus-for-ansys-fluent-part-2 | 2026-10-12 |
| Fusion manufacturing methods | Autodesk Fusion help, "Specify manufacturing methods" (generative design) | https://help.autodesk.com/cloudhelp/ENU/Fusion-GenerativeDesign/files/GD-SPECIFY-MFG-METHOD.htm | 2026-10-12 |
| Kuczyński and Woźniakowski 1992 | Kuczyński and Woźniakowski, "Estimating the Largest Eigenvalue by the Power and Lanczos Algorithms with a Random Start", SIAM J. Matrix Anal. Appl. 13(4), 1992 (Crossref record) | https://api.crossref.org/works?query.bibliographic=Kuczynski+Wozniakowski+Estimating+the+largest+eigenvalue+by+the+power+and+Lanczos+algorithms+with+a+random+start&rows=2 | 2026-10-12 |
| Oden and Prudhomme 2002 | Oden and Prudhomme, "Estimation of Modeling Error in Computational Mechanics", Journal of Computational Physics 182(2), 2002 (Crossref record) | https://api.crossref.org/works?query.bibliographic=Oden+Prudhomme+Estimation+of+modeling+error+in+computational+mechanics&rows=2 | 2026-10-12 |
| Taylor 2008 | Taylor, "The theory of critical distances", Engineering Fracture Mechanics 75(7), 2008 (Crossref record, no abstract) | https://api.crossref.org/works?query.bibliographic=Taylor+The+theory+of+critical+distances+Engineering+Fracture+Mechanics+2008&rows=3 | 2026-10-12 |
| Geevers et al. 2018 | Geevers, Mulder, van der Vegt, "New Higher-Order Mass-Lumped Tetrahedral Elements for Wave Propagation Modelling" | https://arxiv.org/abs/1803.10065 | by 2026-10-11 |
| Fuentes et al. 2015 | Fuentes, Keith, Demkowicz, Nagaraj, "Orientation Embedded High Order Shape Functions for the Exact Sequence Elements of All Shapes" | https://arxiv.org/abs/1504.03025 | by 2026-10-11 |
| Moxey et al. 2020 | Moxey, Amici, Kirby, "Efficient Matrix-Free High-Order Finite Element Evaluation for Simplicial Elements", SIAM J. Sci. Comput. 42, 2020 (Crossref record) | https://api.crossref.org/works?query.bibliographic=Efficient+matrix-free+high-order+finite+element+evaluation+for+simplicial+elements&rows=2 | by 2026-10-11 |
| Firedrake licence | Firedrake licence | https://raw.githubusercontent.com/firedrakeproject/firedrake/master/LICENSE | by 2026-10-11 |
| TEAM problems | COMPUMAG, TEAM problems | https://www.compumag.org/wp/team/ | by 2026-10-11 |
| LAMMPS repository | LAMMPS repository | https://github.com/lammps/lammps | by 2026-10-11 |
| Geier et al. 2015 | Geier, Schönherr, Pasquali, Krafczyk, "The cumulant lattice Boltzmann equation in three dimensions: Theory and validation", 2015 (Crossref record) | https://api.crossref.org/works?query.bibliographic=The+cumulant+lattice+Boltzmann+equation+in+three+dimensions+Geier&rows=2 | by 2026-10-11 |
| Hu et al. 2018 | Hu et al., "A moving least squares material point method with displacement discontinuity and two-way rigid body coupling", ACM TOG 37, 2018 (Crossref record) | https://api.crossref.org/works?query.bibliographic=A+moving+least+squares+material+point+method+with+displacement+discontinuity+and+two-way+rigid+body+coupling&rows=2 | by 2026-10-11 |
| Marrone et al. 2011 | Marrone et al., "δ-SPH model for simulating violent impact flows", CMAME 200, 2011 (Crossref record) | https://api.crossref.org/works?query.bibliographic=delta-SPH+model+for+simulating+violent+impact+flows+Marrone+Antuono+Colagrossi&rows=3 | by 2026-10-11 |
| DualSPHysics repository | DualSPHysics repository | https://github.com/DualSPHysics/DualSPHysics | by 2026-10-11 |
| Paganini and Wechsung 2021 | Paganini and Wechsung, "Fireshape: a shape optimization toolbox for Firedrake" | https://arxiv.org/abs/2005.07264 | by 2026-10-11 |
| Fireshape repository | Fireshape repository | https://github.com/fireshape/fireshape | by 2026-10-11 |
| STRUMPACK licence | STRUMPACK licence | https://raw.githubusercontent.com/pghysels/STRUMPACK/master/LICENSE | by 2026-10-11 |
| SuperLU_DIST licence | SuperLU_DIST licence | https://raw.githubusercontent.com/xiaoyeli/superlu_dist/master/License.txt | by 2026-10-11 |
| MUMPS licence | MUMPS download and licence page | https://mumps-solver.org/index.php?page=dwnld | by 2026-10-11 |
| libCEED licence | libCEED licence | https://raw.githubusercontent.com/CEED/libCEED/main/LICENSE | by 2026-10-11 |
| SuiteSparse licence | SuiteSparse licence summary | https://raw.githubusercontent.com/DrTimothyAldenDavis/SuiteSparse/dev/LICENSE.txt | by 2026-10-11 |
| SLEPc licence | SLEPc licence | https://gitlab.com/slepc/slepc/-/raw/main/LICENSE.md | by 2026-10-11 |
| ARPACK-ng licence | ARPACK-ng licence | https://raw.githubusercontent.com/opencollab/arpack-ng/master/COPYING | by 2026-10-11 |
| OSMC licence | OpenModelica OSMC licence | https://github.com/OpenModelica/OpenModelica/blob/master/OSMC-License.txt | by 2026-10-11 |
| pyadjoint licence | pyadjoint licence | https://raw.githubusercontent.com/dolfin-adjoint/pyadjoint/master/LICENSE | by 2026-10-11 |
| PhysicsNeMo licence | PhysicsNeMo licence | https://raw.githubusercontent.com/NVIDIA/physicsnemo/main/LICENSE.txt | by 2026-10-11 |
| FMPy licence | FMPy licence | https://raw.githubusercontent.com/CATIA-Systems/FMPy/main/LICENSE.txt | by 2026-10-11 |
| Palace repository | Palace repository | https://github.com/awslabs/palace | by 2026-10-11 |
| Ansys LS-DYNA | Ansys LS-DYNA product page | https://ansys.synopsys.com/products/structures/ansys-ls-dyna | by 2026-10-11 |
| Turek and Hron 2006 | Turek and Hron, "Proposal for Numerical Benchmarking of Fluid-Structure Interaction between an Elastic Object and Laminar Incompressible Flow" (Crossref record) | https://api.crossref.org/works?query.bibliographic=Proposal+for+numerical+benchmarking+of+fluid-structure+interaction+between+an+elastic+object+and+laminar+incompressible+flow&rows=3 | by 2026-10-11 |
| Chaturantabut and Sorensen 2010 | Chaturantabut and Sorensen, "Nonlinear Model Reduction via Discrete Empirical Interpolation", SIAM J. Sci. Comput. 32(5), 2010 (Crossref record) | https://api.crossref.org/works?query.bibliographic=Nonlinear+model+reduction+via+discrete+empirical+interpolation+Chaturantabut+Sorensen&rows=2 | by 2026-10-11 |
| Huynh et al. 2007 | Huynh, Rozza, Sen, Patera, "A successive constraint linear optimization method for lower bounds of parametric coercivity and inf–sup stability constants", 2007 (Crossref record) | https://api.crossref.org/works?query.bibliographic=A+successive+constraint+linear+optimization+method+for+lower+bounds+of+parametric+coercivity+and+inf-sup+stability+constants&rows=2 | by 2026-10-11 |
| Song et al. 2016 | Song, Nelson, Staum, "Shapley Effects for Global Sensitivity Analysis: Theory and Computation", SIAM/ASA JUQ 4, 2016 (Crossref record) | https://api.crossref.org/works?query.bibliographic=Shapley+effects+for+global+sensitivity+analysis+theory+and+computation&rows=2 | by 2026-10-11 |
| Dvorkin and Bathe 1984 | Dvorkin and Bathe, "A continuum mechanics based four-node shell element for general non-linear analysis", Engineering Computations 1, 1984 (Crossref record) | https://api.crossref.org/works?query.bibliographic=A+continuum+mechanics+based+four-node+shell+element+for+general+non-linear+analysis+Dvorkin+Bathe&rows=2 | by 2026-10-11 |
| Svanberg 1987 | Svanberg, "The method of moving asymptotes", IJNME 24, 1987, and Zillober, "A globally convergent version of the method of moving asymptotes", 1993 (Crossref record) | https://api.crossref.org/works?query.bibliographic=The+method+of+moving+asymptotes+a+new+method+for+structural+optimization+Svanberg&rows=3 | by 2026-10-11 |
| Schäfer et al. 1996 | Schäfer, Turek, Durst, Krause, Rannacher, "Benchmark Computations of Laminar Flow Around a Cylinder", 1996 (Crossref record) | https://api.crossref.org/works?query.bibliographic=Schafer+Turek+benchmark+computations+laminar+flow+around+cylinder+1996&rows=3 | by 2026-10-11 |
| Nguyen et al. 2013 | Nguyen, Kerfriden, Claus, Bordas, "Nitsche's method for mixed dimensional analysis: conforming and non-conforming continuum-beam and continuum-plate coupling" | https://arxiv.org/abs/1308.2910 | by 2026-10-11 |
| SPHERIC test 2 | SPHERIC, validation test 2, "3-D schematic dam break and evolution of the free surface" | https://www.spheric-sph.org/tests/test-02 | by 2026-10-11 |
