# Flux physics engine (FLX)

Flux compiles weak forms written in Ingot through the shared kernel IR and solves them per region with matrix-free multigrid. Solids use aggregated CutFEM on an immersed octree, slender walls and members use shells and beams, and contact uses fitted meshes. Every result is a Field whose `ErrorBudget` states each bound's norm, kind and confidence, so a check decides only on bounds that hold for its quantity.

## Scope and architecture

Flux is the machinery: Fields, the weak-form language, the kernel IR, discretizations, solvers, Networks, multibody dynamics, coupling, gradients, uncertainty, execution and display data. COV owns the physics models, materials and validity envelopes built on it. "Flux" is a working name, so `flux::` names and WIT packages freeze only after the phase 0 rename.

| Crate | Layer | Contents |
| --- | --- | --- |
| `field` | Engine core | `Field`, domains, representations, `Sampler`, storage layout |
| `kernels` | Engine core | Shared kernel IR, back ends, `local_solve`; the only Flux code allowed `unsafe` |
| `flux-forms` | Physics | Form IR, typing, symbolic differentiation, elements, form-compiler front end |
| `flux-solve` | Physics | Plans, discretizations, solvers, estimators, Networks, multibody |
| `flux-couple` | Physics | Coupling, homogenization, FMI and SSP runtime |
| `flux-opt` | Physics | Adjoints, optimization, uncertainty, reduced models, surrogates |
| `linalg` | Platform (PLT with FLX) | Canonical dense and sparse linear algebra |
| `bridges/` | Outside `core/` | Optional PETSc and hypre FFI, never in Wasm builds |

**Decision D-FLX-1:** Flux owns two engine-core crates below Anvil, `field` and `kernels`, and four physics crates; optional FFI lives in `bridges/`, and `linalg` is shared with PLT. *Why:* Anvil operations consume Fields, and implicit tapes compile through the kernel IR (contract section 12). *Rejected:* the round 1 seven-crate split with Flux-prefixed engine crates. (revised in round 2)

About 80 operations, each `flux::name@version` with a determinism grade, are orchestrated by `std::sim`, `std::physics`, `std::opt` and `std::uq`. Wasm components call them through `crucible:ops/flux` as recorded Op dependencies.

| Group | Operations |
| --- | --- |
| Fields | `field_sample`, `field_transfer`, `field_project`, `field_recover`, `field_reduce`, `field_region`, `field_compare` |
| Forms and plans | `compile_form`, `plan`, `mark_reduction` |
| Discretization and solve | `discretize`, `cut_quadrature`, `assemble`, `setup_preconditioner`, `solve_linear`, `solve_nonlinear`, `solve_transient`, `solve_eigen`, `solve_harmonic`, `solve_explicit`, `koiter_coefficient` |
| Lumped and multibody | `compile_network`, `solve_dae`, `solve_periodic`, `solve_multibody`, `linearize_multibody`, `solve_rod`; circuit analyses use `solve_nonlinear` (operating point, DC sweep), `solve_harmonic` (AC, noise), `solve_eigen` (pole-zero), `solve_dae` (transient) and `solve_periodic` (periodic steady state, harmonic balance) |
| Error and adaptivity | `estimate_error`, `estimate_goal`, `singular_sets`, `confirm_refinement`, `validity_zones`, `certify`, `mark`, `adapt` |
| Coupling | `couple`, `homogenize`, `localize`, `cosimulate`, `fmu_import`, `fmu_export`, `ssp_import`, `ssp_export` |
| Gradients and optimization | `tangent`, `adjoint`, `shape_gradient`, `filter_density`, `project_density`, `mma_step`, `lbfgs_step`, `sqp_step`, `cmaes_step` |
| Uncertainty | `sample_plan`, `pce_fit`, `sobol_indices`, `shapley_effects`, `mlmc_estimate`, `subset_simulation` |
| Reduced models and surrogates | `modal_basis`, `craig_bampton`, `pod_basis`, `hyperreduce`, `rom_build`, `rom_eval`, `surrogate_train`, `surrogate_calibrate`, `surrogate_eval` |
| General methods (D-COV-11) | `bvh_build`, `bvh_query`, `neighbor_list`, `segmented_reduce`, `random_stream`, `fmm_apply`, `hmatrix_build`, `hmatrix_apply`, `fft_solve`, `port_modes`, `fast_sweep` |
| Post-processing | `probe`, `reaction`, `isosurface`, `streamlines`, `display_evaluator`, `display_samples`, `report_data` |

[[DIAGRAM diagrams/03-flux-pipeline.jsx: Flux pipeline · 7 stages, 1 adaptive loop, 3 consumers]]

Read it top to bottom: boxes are stages, the side loop repeats until the estimate meets tolerance, and the dashed path carries adjoint gradients back.

### Rust API

Kiln calls every operation through `OpImpl`, `OpCx` and, where derivatives exist, `Differentiable` in `base`. Every discretization method implements a `Discretization` trait: discretize, estimate, produce Fields.

```rust
/// A quantity over a domain: Field<Body, Stress>, Field<(Body, Time), Temperature>.
pub struct Field<D: Domain, V: Value> {
    header: Arc<FieldHeader>, // GeometryId + entity numbers, unit, budget, zones, provenance
    repr: Repr,               // the eight representations
    _kind: PhantomData<(D, V)>,
}

pub trait Sampler<D: Domain, V: Value> {
    /// Values with a pointwise ErrorBudget and, where known, a gradient bound.
    /// Point location calls `base`'s `Classify` trait, which Anvil implements.
    fn sample(&self, cx: &mut OpCx<'_>, at: &[Location], accuracy: Accuracy)
        -> Result<Vec<Sampled<V>>, FieldError>;
}

/// Deterministic failures are values; environmental faults are Aborts.
#[non_exhaustive]
pub enum SolveFailure {
    LinearDiverged { iterations: u32, residual_history: Vec<f64> },
    NonlinearDiverged { iteration: u32, residual_history: Vec<f64>, last_converged: Option<FieldSet> },
    Bifurcation { load: f64, modes: FieldSet },          // D-FLX-25
    Unsupported { reason: UnsupportedReason },           // NoBifurcationMonitor in phase 1
    SingularOperator { null_space_hint: NullSpaceHint },
    OutsideParameterBox { parameter: ParamId, range: (f64, f64) },
}
```

### WIT interfaces

Flux owns `crucible:field` (interfaces `types` and `build`; sampling is `flux::field_sample` through `crucible:ops/flux`) and, with COV, the `crucible:physics` `solver` and `crucible:material` `constitutive` worlds; ECO keeps the index. The WIT is generated from the Rust types, and examples import `@0.1.0` until the packages freeze after the rename.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Operation registration | `OpImpl` with grade, effective-fidelity map and cost model; `Differentiable` where derivatives exist | Missing grade or cost model fails the registry check | FLX-O-OPT-1 | 0 |
| Physics packages in Ingot | User-namespace forms get std's kernels, derivatives, GPU paths and estimators | `FormError` at compile time | FLX-O-ARCH-1 | 1 |
| `crucible:field` WIT package | `types` and `build`, generated from the Rust types | Generated and published WIT differ: CI fails | FLX-O-ARCH-4 | 2 |
| Constitutive Wasm components | `crucible:material/constitutive`, batched, with consistent tangents | `TangentInconsistent`; cannot register for Newton | FLX-O-FORM-3 | 2 |
| Solver Wasm components | `crucible:physics/solver`, Fields in and out, may call `crucible:ops/flux` | Determinizer rejection | FLX-O-ARCH-1 | 2 |
| Flux operations from Wasm | `crucible:ops/flux`, GPU-backed ones included; recorded dependencies | `OpVersionRetired` with an upgrade Proposal | FLX-O-ARCH-2 | 2 |
| External Op solvers | GPL references in pinned images on untrusted-evaluation workers; host class or `Unverified` | Host failure is a `Failure`; worker loss an Abort | FLX-O-ARCH-3 | 3 |

## Fields

### Domains and values

`Field<D, V>` follows contract section 5: entity-set, parameter and index domains and their tuples. Values are scalars, vectors, tensors, complex values, `Transform`s and enums such as `ValidityZone`. Each value type declares its rigid-transform rule, so Instance placement needs no user code.

Canonical storage is SI `f64`; `f32` copies exist only on GPUs and for display. A Field's domain is the Body's `GeometryId` plus canonical entity numbers, reached through `base`'s handles and never through a name or `EntityId`, so values survive renaming. A Field used on other geometry fails with `DomainMismatch`, suggesting `field_transfer`.

**Decision D-FLX-2:** Time series, sweeps, mode sets, load cases, ensembles and parametric results are Fields over product domains such as `Field<(Body, Time), Temperature>`, and slicing and reductions return Fields. *Why:* libraries then exchange only Bodies, Fields and plain values (principle 3). *Rejected:* separate container types; a third type parameter for axes, replaced by product domains (ruling FLX-2). (revised in round 2)

### Representations

| Representation | Holds | Sampling error |
| --- | --- | --- |
| `Analytic` | Kernel-IR expression (loads, boundary data) | Floating point only |
| `Discrete` | Lagrange, edge, face, DG or NURBS coefficients | Discretization part carried separately |
| `QuadraturePoint` | Values at quadrature points (plastic state, densities) | Recovery error |
| `SparseGrid` | Adaptive block grid (lattice Boltzmann, FDTD, CT) | Local second differences |
| `PerEntity` | One value per entity | None |
| `PointCloud` | Points with a reconstruction rule | Leave-one-out estimate |
| `Reduced` | Basis Field times coefficient model | Certified or residual bound |
| `Surrogate` | Trained model, calibration set, envelope | Conformal bound, `scope: Marginal` |

**Decision D-FLX-3:** Generalize "nodal values" to `Discrete` and "per-face constants" to `PerEntity`, and add `PointCloud`, `Reduced` and `Surrogate`. *Why:* nodal values cannot hold Nédélec, DG or NURBS coefficients, and particle, reduced and learned results must reach checks. *Rejected:* separate result types per method.

### Sampling and operations

`Sampler::sample` takes Part, surface `(entity number, u, v)`, reference-cell or parameter coordinates and a requested accuracy. It returns values with a pointwise budget and, where known, a gradient bound for Anvil's extraction. Point location uses Anvil's certified classification through `Classify`, ties broken by canonical cell number; outside the domain it fails with `OutsideDomain { distance }`, and requested extrapolation is `NotQuantified`.

| Ingot | Error behavior |
| --- | --- |
| `a + b`, `sqrt(a)` | Lazy `Analytic`; first-order propagation in one norm |
| `grad`, `div`, `curl`, `sym_grad` | Basis derivatives, or `NeedsRecovery` |
| `f.on(p.faces(q))` | Full, normal or tangential trace; none added |
| `f.integrate(dx(region))` | Quadrature part added |
| `f.max(over: R)`, `f.at(x)`, `f.mean(over: R)` | Regularized goals (D-FLX-23) from `estimate_goal` |
| `f.project(to: V)`, `f.transfer(to: body)` | Conservative or consistent; transfer part estimated |
| `f.region(where: f > 250MPa)` | Implicit Body bounded from Field and gradient |
| `compare(a, b)` | Differences inside combined bounds not significant |

### Fields that drive geometry

Anvil samples Fields (sizing, metric, displacement, thickness, radius, density, orientation) at a required accuracy and adds the sampled error to the Body's bounds. `anvil::implicit_from_field` needs a continuous Field with a gradient bound, which topology optimization supplies as `geometry_density`; a Field that misses the accuracy fails with `InsufficientAccuracy { achieved, required, producer }`.

**Decision D-FLX-5:** A consumer never changes its producer. Adaptivity goals are explicit study inputs (`goals: [...]`), and a reduction a check reads is estimated by a separate `flux::estimate_goal` node over the frozen solution, which never re-solves. *Why:* adding a check must never change a design (D-ING-12). *Rejected:* deriving goals from the checks that read a result, which reverses the graph (R3-10); refinement on demand. (revised in round 2)

An undecidable check returns `Undecided { needed }` with an edit adding its functional to the goals.

### Storage

A stored Field is a header plus 1 MiB chunks, byte-shuffled, zstd-compressed and hashed over canonical little-endian `f64` bytes. Storing −0.0 as +0.0 makes CAS reloads equal in-memory values.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Field types and product domains | `Field<D, V>` keyed by `GeometryId` and canonical entity numbers | `DomainMismatch` with a `field_transfer` fix | FLX-O-FIELD-1 | 0 |
| Sampling | `Sampler` with pointwise budget and gradient bound, located through `Classify` | `OutsideDomain`, `InsufficientAccuracy` | FLX-O-FIELD-1 | 0 (`Analytic`, `Discrete`), 1 |
| Transfer and projection | Conservative for fluxes, consistent for states | `NotSameInterface` from Anvil | FLX-O-FIELD-2 | 1, 4 (interface overlays) |
| Extremum enclosure and region extraction | Bernstein subdivision; Implicit Bodies from scalar Fields | Work limit with the achieved gap; `NotContinuous` | FLX-O-FIELD-3 | 1 |
| Geometry-driving Fields | Sizing, metric, displacement, thickness, radius, density, orientation | `InsufficientAccuracy` naming the producer | FLX-O-FIELD-4 | 1 (density), 2 |
| Storage and canonical form | Chunked CAS arrays; canonical bytes | None | FLX-O-FIELD-5 | 0 |
| Label invariance | Field values unchanged under renaming | Any difference fails the rename oracle | FLX-O-FIELD-6 | 1 |

## Error budgets, goals and checks

### Budgets and guarantees

Every result Field and estimated reduction carries an `ErrorBudget<Q>` (contract section 5). Flux produces every part except model form, which comes only from COV's validation.

| Source | Estimator | Norm | Kind |
| --- | --- | --- | --- |
| Discretization, scalar diffusion, fitted simplices | Equilibrated flux [Smears and Vohralík] | Energy | `Guaranteed` |
| Discretization, elasticity, fitted simplices | Strongly symmetric equilibrated stress [Arnold and Winther; Hu and Zhang] | Energy | `Guaranteed` with polynomial data |
| Discretization, weakly symmetric elasticity | Bound with a shape-regularity constant [Bertrand et al.] | Energy | `Estimated` |
| Discretization, hanging nodes or cut cells | Same constructions | Energy | `Estimated` (open question 1) |
| Bounded linear goals (regional averages, resultants, compliance, mean temperature) | Primal–dual product of energy bounds | Goal | `Guaranteed` when both factors are |
| Regularized peaks and point values | Dual-weighted residual (DWR) | Goal | `Estimated { calibration }` |
| Eigenvalues | DWR eigenvalue estimate on the unsafe side (D-FLX-41) | Goal | `Estimated { calibration }` |
| Algebraic | Multilevel bound on fitted simplices [Papež et al.] or a certified spectral bound after factorization; else equilibrated residual | As discretization | `Guaranteed`; else `Estimated` |
| Temporal | Adjoint-weighted residual; step halving with frozen breakpoints; summed local errors | Goal | `Estimated`, calibrated, `Indicator` |
| Quadrature, geometry | Rule-order comparison; Anvil face bounds through shape sensitivity | Goal or energy | `Estimated`; zero for polynomial data on planar faces |
| Floating point | Bound γₖ of the canonical CPU evaluation, k the reduction-tree depth | As covered part | `Guaranteed` |
| Reduction or surrogate | Shell and beam patches (D-FLX-26); reduced-model, conformal, per-prediction bounds | Goal | Per method |
| Statistical, input and tolerance | Confidence intervals; `std::uq` bounds; property-basis enclosures | Goal | Per method |
| Model form | COV's validation only | Goal | From COV, else `NotQuantified` |

**Decision D-FLX-4:** Flux reports every error through the contract's `ErrorBound<Q>` and `ErrorBudget<Q>`, one bound per source in its own norm, never converted. A bound is `Guaranteed` only when a proof for that method covers that norm, and the estimator's metadata names the theorem. *Why:* in 3D, H¹ does not embed in L∞, so energy bounds cannot certify peak stresses (R1-01). *Rejected:* totals across norms; the round 1 `Unknown` kind, replaced by `NotQuantified { reason }`. (revised in round 2)

A total takes its weakest part's kind, so it is `Guaranteed` only on fitted simplices with polynomial data, planar faces and a `Guaranteed` algebraic part. Guaranteed goal bounds rest on |J(u) − J(u_h)| ≤ ‖u − u_h‖_E · ‖z − z_h‖_E for a bounded linear functional J with adjoint z.

After a direct factorization the algebraic part is ‖r‖_{M⁻¹}/√σ. A canonical LDLᵀ inertia count of A − σM certifies A ≥ σM, with σ lowered by the backward-error bound.

Property reads arrive as `Approx<Q>` enclosures between basis values (ING, COV). A solve propagates them into its input part by the adjoint sensitivity's sign, or solves at both ends where the sign varies.

### Regularized goals and singular points

**Decision D-FLX-23:** Peak and pointwise quantities are regularized goals. `f.max(over: R, smooth: ρ)` maximizes a Gaussian local average of radius ρ, `f.at(x, smooth: ρ)` evaluates it at x, and `pnorm` serves optimization; boundary points average over a geodesic disc. The default ρ is min(0.1 × the smallest curvature or fillet radius in R, 0.1 × local wall thickness), or the Material's critical distance for fatigue and fracture. *Why:* raw maxima diverge at singular points, and a part-size radius hides fillet peaks (R7-15). *Rejected:* raw maxima; p-norms for checks; 1% of the region's diameter. (revised in round 3)

The regularization part is the gap to the discrete Field's enclosed raw maximum. `flux::estimate_goal` solves the adjoint one degree higher on the frozen discretization and reports the largest calibrated estimate among near-maximal locations.

**Decision D-FLX-39:** `flux::singular_sets` flags only conditions that make the exact stress unbounded (contract section 7.1). A `Concave` edge from `anvil::classify_edges` is flagged when its leading Williams exponent λ₁ is below 0.9 [Williams], and noted as `Note::WeakSingularity` below 1. `Ambiguous` edges are flagged, with `recognize_aspects` as fix from phase 2. Conditions are flagged where incompatible: clamped meeting free, a patch edge inside a face, traction along a free neighbour's normal, an edge inside a contact zone. *Why:* blanket flags left the canonical check `Undecided`, yet Hertzian contact is bounded (R7-02, R7-18, R8-05, R8-17). *Rejected:* flagging every patch edge and contact boundary; one fixed angle.

Re-entrant corners, material interfaces meeting the boundary, point and line measures, and estimates that stagnate under refinement are flagged too; smooth contact edges only guide hp refinement. Each flagged set has a default exclusion distance of max(2ρ, local wall thickness), which a check may override.

A point quantity whose region does not exclude a flagged set by that distance is `Undecided { SingularPoint }`. The canonical check excludes the clamp and the loaded end cap, so it decides for any load direction.

### Calibrated estimates

**Decision D-FLX-24:** Every `Estimated` bound is reported multiplied by its class's η99, the 99th-percentile underestimate factor, and labelled `Estimated { calibration }` with α = 0.01 in the union bound. Each class declares an envelope over degree p, minimum cut fraction, ρ/h, distance to flagged sets, Poisson's ratio and material contrast. Outside it, or without an entry, a result is `Indicator`. *Why:* one decision rule serves both fidelities, outcomes state their confidence, and membership becomes computable (R1-07, R7-01). *Rejected:* a margin at the consumer; machine-local factors (R1-14); classes as bare labels. (revised in round 3)

Tables live in `std::sim::calibration`, pinned in `ingot.lock` and every key that reads them. `flux::confirm_refinement` checks a `SignOff` `Pass` on an `Estimated` discretization part one level finer, h/2 or p + 1. The refined value must lie inside the first bound with a smaller bound, or the verdict is `Undecided { reason: CalibrationUnconfirmed }`.

**Decision D-FLX-40:** A calibration entry changes only through a reviewed Proposal with at least 300 held-out samples and zero undershoots (one-sided 95% exceedance bound below 1%). An Ingot generator under `oracles/flux/` produces L-brackets, filleted plates with holes, gusseted brackets and lattice blocks with skins and inserts. At least 20% of samples come from `std::opt` runs minimizing the check margin inside the envelope. References are solves two degrees higher, or full-resolution solids for lattices, and count only when their own error is below 10% of the bound. *Why:* optimizers seek the designs where an estimator undershoots, and weak references certify false zeros (R7-01, R7-16). *Rejected:* parametric samples only.

| Phase 1 class | Quantity | Model and discretization | Gates |
| --- | --- | --- | --- |
| `elasticity.peak` | Regularized stress peak | Linear elasticity, aggregated CutFEM, p = 2 to 6, both fidelities | GP1, GP2 |
| `elasticity.eigen` | Frequency or buckling factor | Eigenvalue DWR on aggregated CutFEM | GP1, GP2 |
| `lattice.strut_stress` | Localized strut stress | Beam lattice with calibrated joints | GP2 |
| `lattice.buckling` | Strut buckling factor | Eigenvalue DWR on the beam lattice | GP2 |

MEC assigns classes to checks (D-MEC-30) and COV maps model classes. Reduction patches, step halving and bolted-joint forms add classes in phase 2, GCI bands in phase 3, and each class records whether its samples were GPU-solved.

### Fidelities

| Aspect | `Preview` | `Interactive` | `SignOff` |
| --- | --- | --- | --- |
| Methods | Reduced, surrogate, coarsest or shifted boundary | Aggregated CutFEM at p = 2, one pass | hp-adaptive, with refinement confirmation |
| Class | Any | CPU, or `Gpu(…)` in `f32` with CPU estimation | `CpuCanonical`, or GPU certified on the CPU |
| Bounds | `Indicator` | Calibrated `Estimated` | `Guaranteed` where proven, else calibrated `Estimated` |
| Checks | Always `Undecided` | ING's rule | ING's rule; `Pass { conditional_on }` for unquantified parts |
| Cache | Never shared | Shared | Shared once two trusted builders agree |

**Decision D-FLX-15:** Flux produces budgets; ING decides checks by one rule (disjoint enclosures decide, subject to the check's `decides_on`), returning `base`'s `CheckOutcome`. Flux adds no margin rule. *Why:* four tabs had four rules (R3-07). *Rejected:* binary checks on point values; the round 1 three-times margin at `Interactive`. (revised in round 2)

On a GPU class at `Interactive`, Flux evaluates the read-back Field's residual and estimator on the CPU in `f64`, as `F32Safe` requires (D-COV-23); GPU-evaluated estimators are `Indicator` only. Nodes record the fidelity of the bounds they observed, so a branch on `Undecided` below its ceiling waits as `Pending` (R3-14).

### Verification, validity and agreement

**Decision D-FLX-34:** Methods without an a posteriori estimator (finite-volume RANS and LES, lattice Boltzmann, FDTD, particles) report `Indicator` discretization parts unless `std::sim::solution_verification` runs. It refines the final mesh uniformly three times by r ≥ 1.3, adaptivity frozen, and applies Roache's grid convergence index with safety factor 1.25 [NASA]. Each method family's band is a calibration class with its own η99. *Why:* code verification does not verify an application result, and uncalibrated bands differ in meaning from other `Estimated` bounds (R1-28, R7-21). *Rejected:* single-grid trust; uncalibrated bands; adapted meshes. (revised in round 3)

Adapted runs and oscillatory convergence stay `Indicator`, and so do LES and DDES without a fixed explicit filter width and a batch-means statistical part.

`flux::validity_zones` evaluates COV's regime functions into a `Field<Body, ValidityZone>` and `Flag` or `Refuse` checks, under COV's zone semantics. `Refuse` yields `Error(Failure)` with `ValidityError::OutsideEnvelope { variable, bound, escalate_to }`, and Flux never switches models. Transient solves keep running extrema per accepted step through `segmented_reduce` and write zone Fields at output steps.

Classes agree by PLT's rule (D-PLT-35): with equal resolved plans, adaptive marks and steps, only the algebraic and floating-point parts plus a floor count.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Error budgets | `ErrorBudget<Q>` on every result; one producer per source | Unquantified parts named | FLX-O-ERR-1 | 1 |
| Guaranteed energy bounds | Equilibrated flux on fitted simplices; strongly symmetric stress | `Estimated` where no theorem applies | FLX-O-ERR-1 | 2 (diffusion), 3 (elasticity) |
| Guaranteed algebraic parts | Multilevel bound; certified spectral bound after factorization | Elsewhere `Estimated`, so the total is too | FLX-O-ERR-2 | 2 |
| Guaranteed linear goals | Primal–dual product | `NotQuantified` if a factor is unguaranteed | FLX-O-ERR-2 | 2 |
| Regularized goals | `max`, `at` and `pnorm` via `estimate_goal` | `Undecided { needed }` with a goals fix | FLX-O-ERR-3 | 1 |
| Eigenvalue estimates | DWR on the unsafe side; Kato–Temple or Lehmann algebraic bounds | `Indicator` without a class | FLX-O-SOLVE-6 | 1 |
| Singular sets | `singular_sets` by edge class and compatibility | `Undecided { SingularPoint }` | FLX-O-ERR-4 | 1 |
| Calibration | η99 tables with envelopes; α in the union bound | `Indicator` outside the envelope | FLX-O-ERR-5 | 1 |
| Refinement confirmation | `confirm_refinement` one level finer | `Undecided { reason: CalibrationUnconfirmed }` | FLX-O-ERR-3 | 1 |
| Property-basis propagation | Basis enclosures into the input part | `NotQuantified` without both basis values | FLX-O-ERR-11 | 1 |
| Temporal goal estimates | Adjoint-weighted residual; step halving as a calibrated class | Summed local estimates `Indicator` | FLX-O-ERR-6 | 2 |
| GPU-solved `Interactive` results | CPU `f64` estimation of the read-back Field | GPU estimators `Indicator` | FLX-O-KER-4 | 2 |
| `Preview` fidelity | Reduced, surrogate, coarsest or shifted-boundary solves | Never decides | FLX-O-ERR-7 | 1, 2 (shifted boundary) |
| Solution verification | Calibrated three-level GCI at r ≥ 1.3 | `NotAsymptotic { ratio }` keeps `Indicator` | FLX-O-ERR-8 | 3 |
| Validity zones | `validity_zones` with running extrema | `ValidityError::OutsideEnvelope` inside `Error(Failure)` | FLX-O-ERR-9 | 1 |
| Cross-class agreement | PLT's rule on resolved plans and marks | Incidents as PLT states | FLX-O-ERR-10 | 1 |

## The weak-form language

Physics is written as weak forms in Ingot with UFL's semantics (contract section 6). Forms are staged `Expr` values (D-ING-9), checked for units, linearity and conformity before anything runs; `std::sim` holds the building blocks and `std::physics` the models (principle 1).

### Spaces, elements and measures

| Space | Constructor | Elements | Phase |
| --- | --- | --- | --- |
| H¹ | `H1(domain, degree: p, shape: …)` | Lagrange of any order, serendipity, hierarchical Legendre | 0 (p ≤ 4), 1 |
| H(curl), H(div) | `HCurl(domain, degree: p, kind: 1 \| 2)`, `HDiv(domain, degree: p, kind: rt \| bdm)` | Nédélec, Raviart–Thomas, Brezzi–Douglas–Marini | 1 (H(div) in estimators), 3 |
| L², trace, real | `L2`, `Trace`, `Real(n)` | Discontinuous bases, facet spaces, global multipliers | 1, 3 (trace) |
| Spline | `Spline(body, degree: p, continuity: k, kind: nurbs \| thb)` | B-rep NURBS, truncated hierarchical B-splines | 2 |
| Manifold | Sheet and wire Bodies with director or section unknowns | Shells, beams, rods | 1 (wires), 2 (sheets) |
| Parameter domain | `Interval(Radius, n)`, `Sphere(directions: n)`, products `V ⊗ W` | Batched local problems (D-FLX-38) | 4 |
| Mixed, restricted | `(V1, V2)`, `V.restrict(region)` | Taylor–Hood, MINI, (H(div), L²) | 1 |

One Rust element library defines every element and orients H(curl) and H(div) in the restriction, so meshes need no global orientation. Cells run from interval to pyramid, with exact-sequence pyramid bases [Fuentes et al.].

Measures are `dx` (volume, sheet or wire), `ds` (true or queried faces), `dS` (interior facets), and `dE` and `dP` (true edges and points). `dI` integrates over interfaces between Instances or between solids, shells and beams, and `dξ` over parameter domains.

**Decision D-FLX-6:** Measures refer to true-geometry entities selected by `Query`; solves receive them as canonical entity numbers of the Body's `GeometryId`, never as mesh entities or names. *Why:* one form runs fitted, immersed or reduced, conditions survive remeshing, and renaming never changes a result. *Rejected:* mesh-tagged boundaries as in FEniCS and MFEM, which break on every geometry change. (revised in round 2)

### Operators, problem kinds and checks

Operators cover algebra, calculus, facet terms (`jump`, `avg`), `dt`, pointwise eigen-decomposition, `select`, `im` and `.absolute()`; non-smooth functions declare generalized derivatives.

| Kind | Ingot | What Flux does |
| --- | --- | --- |
| Linear, nonlinear, energy | `a == L`; `F == 0`; `minimize(Pi, u)` | Arity check; symbolic Jacobian or Hessian |
| Mixed | `trial((Velocity, Pressure), p, element: taylor_hood(2))` | Blocks kept for field-split preconditioners |
| Time-dependent | `dt(u)`; `implicit(…)`, `explicit(…)` marks | Semi-discrete system; the plan picks the scheme |
| Harmonic, eigen, constrained | `solve_harmonic`, `modes`, `fixed:`, `contact(...)` | Complex forms; strong, Nitsche or multiplier constraints |
| Continuation, goals | `continue_in(load, to: 2kN)`; `study(..., goals: [...])` | Arc length with bifurcation detection; goal-oriented adaptivity |

| Check | Rule | Error and fix |
| --- | --- | --- |
| Units | One dimension per residual row | `FormError::UnitMismatch { term, expected, found }` |
| Arity | Bilinear forms linear in trial and test | `NotLinear { term }`, suggesting `F == 0` |
| Conformity | `curl` needs H(curl) or H¹, `div` H(div) or H¹ | `Conformity`, naming the conforming space |
| Inf-sup, quadrature | Unstable pairs such as P1–P1 Stokes; degree above 30 | Warning naming a stable pair |

### Compilation and `local_solve`

The compiler lowers checked forms to index notation and erases units. It takes forward symbolic Gateaux derivatives on the hash-consed DAG, with `adjoint` and `action`, and applies Piola pullbacks for H(curl) and H(div). Non-polynomial integrands get degree 2p + 2 with an estimate one order higher, and kernels split into libCEED's `Eᵀ Bᵀ D B E`.

**Decision D-FLX-7:** Write the form compiler natively in Rust, following TSFC's structure-preserving design and libCEED's `Eᵀ Bᵀ D B E` split. *Why:* it runs inside Kiln on every OS and in browsers, emits the kernel IR and differentiates at the form level; no existing compiler does all three in Rust. *Rejected:* UFL with FFCx or TSFC through Python, which cannot run in the browser sandbox.

A local Newton solve is `local_solve(residual, x0)`, differentiated by the implicit function theorem at convergence (contract section 6). Its tolerance follows the global Newton tolerance, so return mapping keeps quadratic convergence. Constitutive models are Ingot functions or `crucible:material/constitutive` Wasm components with consistent tangents.

`solve` returns a record of Fields: each unknown, plus declared outputs such as `stress` and `von_mises`, which add a recovery part to the budget.

**Decision D-FLX-38:** Nested and phase-space models are forms over product spaces with a parameter measure `dξ`: particle diffusion in battery electrodes, FE² micro problems, discrete-ordinates radiation, population balances. They compile into batched local problems, one per macro quadrature point. *Why:* battery cells (SPMe, DFN) and COV's radiation models then get form-level derivatives and GPU kernels (R1-24). *Rejected:* special-purpose solvers that lose derivatives and estimators.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| H¹, L², real, mixed and restricted spaces | Elements of any order on every cell shape | `FormError::Conformity` | FLX-O-DISC-1 | 0 (H¹, p ≤ 4), 1 |
| H(curl), H(div), trace spaces | Nédélec, Raviart–Thomas, BDM, facet spaces | As above | FLX-O-DISC-1 | 3 |
| Spline and manifold spaces | NURBS and THB spaces; sheet and wire spaces | `UnpairedFaces` or `NotPrismatic` from Anvil | FLX-O-DISC-6 | 1 (wires), 2 |
| Parameter-domain spaces | `Interval`, `Sphere`, products, `dξ` | `FormError::Conformity` | FLX-O-FORM-5 | 4, 5 (DFN) |
| Static form checks | Units, arity, conformity, inf-sup, quadrature | Typed `FormError` with a fix | FLX-O-FORM-1 | 0 |
| Symbolic derivatives | Gateaux derivative, `adjoint`, `action` | `NotDifferentiable { op }` | FLX-O-FORM-2 | 0 |
| `local_solve` | Implicit-function derivative at convergence | `LocalSolveDiverged { point }` | FLX-O-FORM-3 | 1 |
| UFL coverage | FEniCS and Firedrake demos expressible | Unsupported construct named | FLX-O-FORM-4 | 3 |

## Kernels, back ends and determinism

FLX owns the kernel IR in `kernels`, the source of every result-affecting kernel, and its back ends (contract section 7.5). IR v0 holds element kernels with sum factorization, constitutive functions with forward derivatives, implicit tapes and `local_solve`. It is additive-only once a consumer compiles, and freezes at the phase 0 gate once one kernel of each kind passes its oracles on both CPU back ends.

Network residuals join in phase 2 and Verilog-A models in phase 3. Assembly is full (p ≤ 2), element-level (GPUs, contact, cut cells), partial with sum factorization (p ≥ 2) or matrix-free. Throughput peaks at degrees three to six [deal.II], and simplices use collapsed-coordinate bases above degree 3 [Moxey, Amici, Kirby].

**Decision D-FLX-9:** On CPUs, user forms compile to Wasm SIMD128 modules and std forms ahead of time. User forms target 1.5× the ahead-of-time time for memory-bound operators (p ≤ 2), and 2.5× on AVX2 and 5× on AVX-512 for compute-bound sum factorization (p ≥ 3). *Why:* one sandboxed path gives canonical bits everywhere, and SIMD128 is half as wide as AVX2 (R7-38). *Rejected:* a native JIT; shipping LLVM; one target for every kernel family. (revised in round 3)

**Decision D-FLX-10:** GPU kernels come from the kernel IR through WGSL on wgpu. Implicit preview ships in phase 1 and `f64` server paths on Vulkan `SHADER_F64` in phase 3. `Interactive` elasticity ships in phase 2, or in phase 1 if phase 0 measures `CpuIsa` kernels missing contract section 13.3's interactive row. CUDA or HIP is reconsidered at the phase 4 gate. *Why:* WGSL lacks `f64`, wgpu offers `SHADER_F64` only on Vulkan, CubeCL is alpha with breaking changes between minor versions, and CPU kernels may meet the row alone (R7-27). *Rejected:* CubeCL in phase 1; unconditional WGSL elasticity in phase 1. (revised in round 3)

**Decision D-FLX-8:** On CPU back ends the kernel IR fixes every floating-point operation and reduction order, with the 512-bit canonical lane order and no FMA in the canonical class. `CpuIsa` FMA variants serve `Preview` and `Interactive` for sum factorization at p ≥ 3, dense GEMM and LU, and NURBS evaluation from phase 0. Memory-bound operators never get them, other families only after phase 0 measures a loss above 1.3×, and WGSL kernels never claim bit-identity. *Why:* x86-64-v2 and wasm32 lack FMA, compute-bound kernels lose most without it, and WGSL may fuse and flush (R1-09, R6-17, R7-35). *Rejected:* FMA in the canonical class; FMA for memory-bound kernels. (revised in round 3)

Throughput targets are contract section 13.3's two CEED rows, `CpuIsa { X86_64V3 }` and canonical, plus immersed elasticity kernels.

**Decision D-FLX-11:** `Portable` code computes elementary functions only with PLT's correctly rounded `detmath`; GPU kernels use fixed-sequence approximations with documented ulp bounds, never vendor built-ins. *Why:* platform and vendor libraries differ, and correct rounding on GPUs needs precision WGSL cannot guarantee (R1-43). *Rejected:* a separate Flux math library; platform `libm`. (revised in round 2)

### Determinism

Contract section 7.3 and PLT own the mechanisms. Flux adds six rules:

1. DOFs, cells and partitions follow canonical geometric order (Morton order, canonical entity numbers), never names.
2. Work splits into virtual partitions fixed by problem size, combined in partition order.
3. Assembly gathers contributions in a fixed order, without floating-point atomics.
4. Node-local reductions use `det_sum` and `det_reduce`, and `exact_sum` only across ranks; CG overhead targets 1.05×.
5. A floating-point control state changed during an operation aborts it for a rerun.
6. GPU paths use integer-limb reductions, CPU non-finite checks after readback and per-pipeline known-answer tests.

**Decision D-FLX-18:** GPU reductions use integer-only exact accumulation: bins of 32-bit limbs with explicit carries, combined in fixed order. *Why:* wgpu offers 64-bit integer atomic add only on Vulkan and DX12 and float atomics only on some devices, while 32-bit integer arithmetic is exact everywhere. *Rejected:* floating-point atomics; vendor reduction libraries.

**Decision D-FLX-19:** Canonical CPU solves, estimators and `flux::certify` are `Portable` in `CpuCanonical`. GPU solves are `ClassExact` in `Gpu(GpuClass)`, and a `SignOff` check on one rests on the pinned Field plus `certify` (D-FLX-17). *Why:* release gates need canonical outcomes, while GPUs pay off at `Interactive` and as solvers the CPU certifies. *Rejected:* the round 1 Flux class names, superseded by PLT's enum. (revised in round 2)

A released operation version freezes its source closure, `linalg` and the `kernels` back ends included (contract section 4). A changed `flux::plan` default therefore needs a new behavior version.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Kernel IR v0 | Element, constitutive and implicit-tape constructs; forward derivatives; `local_solve` | IR validation error naming the construct | FLX-O-KER-1 | 0 |
| Canonical CPU back end | Ahead-of-time Rust with canonical SIMD from x86-64-v2 and ARMv8; `Portable` | None at run time | FLX-O-KER-3 | 0 |
| Wasm SIMD128 back end | Generated at run time: user forms everywhere, all forms in browsers | Determinizer rejection | FLX-O-KER-6 | 0 |
| WGSL back end | wgpu on Vulkan, Metal, DX12 and WebGPU: implicit preview, `Interactive` elasticity; `ClassExact` | Failed known-answer test falls back to the CPU, reported | FLX-O-KER-4 | 1 (preview), 2 (elasticity, or 1 by phase 0's measurement) |
| `f64` GPU server path | Vulkan `SHADER_F64`, certified on the CPU | Missing feature: CPU path, reported | FLX-O-KER-4 | 3 |
| FMA variants | `CpuIsa` kernels for compute-bound families | Never used at `SignOff` | FLX-O-KER-2 | 0 |
| Floating-point environment guard | Checked at operation start and end | Abort and rerun | FLX-O-KER-5 | 0 |
| Throughput | Both CEED rows plus immersed elasticity kernels | Regression blocks beta promotion | FLX-O-KER-1 | 0 |

## Solve plans and per-region discretization

`flux::plan` maps a problem, fidelity, class and `Budget` to a `SolvePlan`: per-region models, spaces, quadrature, assembly, solvers, precision, adaptivity and estimators. Plans depend only on their inputs, never on hardware, and print, edit and pin as Ingot.

```
let plan = std::sim::plan(elasticity, fidelity: SignOff, goals: [stress_goal], tol: 2%)
plan.explain()   // each choice with the alternatives considered
let result = solve(elasticity, fixed: clamp, plan: plan.with(region: p.regions(role: web), model: Solid))
```

**Decision D-FLX-20:** Pin the resolved plan, not just the solver version: a versioned `flux::plan` resolves every default, and the resolved plan enters the cache key. *Why:* most result drift comes from changed defaults, not changed algorithms. *Rejected:* versioning only solver kernels.

### Per-region models

`flux::mark_reduction` returns a `Field<Body, ReductionKind>` from the study's conditions and Anvil's thickness, curvature and distance queries. L_local is the smallest of the span between supports, the radius of curvature, |q|/|∇q| for a distributed load q, and the distance to the nearest concentrated condition. Those are point or line loads, patch edges inside the wall, openings, features and welded joints; distributed loads, body forces and inertia do not shorten L_local (contract section 7.1).

| Region | Criterion | Model | Geometry from Anvil |
| --- | --- | --- | --- |
| Thin wall | t / L_local ≤ 0.2 | Reissner–Mindlin shell; laminates by ABD matrices | `anvil::mid_surface` sheet, thickness Field, junction curves |
| Very thin smooth wall | t / L_local ≤ 0.05 on a NURBS mid-surface | Kirchhoff–Love isogeometric shell | Same, NURBS faces |
| Member or strut | Prismatic over L_local, d / L_local ≤ 0.2 | Timoshenko beam; Vlasov warping for open thin-walled sections | `anvil::member_axes` axes, joints, sections |
| Strut lattice | Strut graph from `anvil::lattice` | Beam lattice with calibrated joints, or homogenized (D-FLX-44) | Strut graph |
| Sheet lattice | Minimal-surface cell from `anvil::lattice` | Shell on the cell's mid-surface, or homogenized (D-FLX-44) | `mid_surface` implicit path |
| Everything else | Fails the criteria above | Solid on the immersed octree, or fitted where required | The Body |

**Decision D-FLX-12:** Discretization is chosen per region (contract section 7.1). Shells and beams serve where the local slenderness criterion holds, the immersed octree serves solids, and fitted meshes serve contact and turbulent boundary layers. Lattices get beam lattices, sheet shells or homogenization, and very thin NURBS walls get isogeometric shells. Junction zones stay solid for two wall thicknesses, three for a junction class that fails FLX-O-PLAN-3. *Why:* a volumetric octree on golden products 2, 4, 5 and 8 needs 10⁶ to 10⁸ DOFs where reduced models need 10⁴ to 10⁵ (R1-02). *Rejected:* immersed solids everywhere; an untested junction length (R7-34). (revised in round 3)

Reduced regions couple through `dI` interfaces [Nguyen et al.]: rigid at `Interactive`, and Nitsche continuity of displacement and rotation at `SignOff`, because rigid coupling stiffens the junction.

**Decision D-FLX-26:** Dimensional-reduction error files under `reduction or surrogate`. Flux re-solves a 3D patch extending max(3t, 2√(R·t)) beyond each goal region, R the local radius of curvature, with boundary data from the reduced model. The estimate is `Estimated { calibration }` in its own class, else `NotQuantified`, making a `Pass` conditional. *Why:* shell and beam theories carry error refinement never removes, the patch must pass their boundary layers, and model form belongs to COV (R7-11). *Rejected:* reduction error as model form; reduced models as exact. (revised in round 3)

| Situation | Plan default |
| --- | --- |
| Compact solids, heat, electrostatics | Immersed octree, aggregated CutFEM; shifted boundary at `Preview` |
| Thin walls, members, struts, lattices | Shells, beams, beam lattices and sheet shells per `mark_reduction` |
| Contact, sliding interfaces; turbulent layers needing y⁺ resolution | Fitted meshes, layers from phase 4 |
| Laminar thermal layers; frozen layers in moulding | Octree wall refinement (D-FLX-45) |
| Voxel and CT data | Finite cell |
| Resonant or narrowband radiation | Frequency-domain Nédélec FEM (D-FLX-32) |
| Broadband transients and EMC | FDTD |
| Exterior acoustics and electrostatics | Boundary elements, or FEM–BEM coupling |
| Granular flow, splashing, fragmentation | DEM, SPH, MPM or peridynamics |
| Lumped systems | Network compiler and DAE solver |

**Decision D-FLX-45:** Laminar thermal and moulding frozen layers are resolved by octree wall refinement. Heated walls get at least five cells at p = 2 across δ_T = H·Ra_H^(−1/4), and 3D fill and pack get eight across the cavity half-thickness. Both counts are COV regime variables, under-resolved zones are Extrapolated, and `SignOff` fill-pressure and warpage goals need an estimator or solution verification. *Why:* the four-cells rule comes from elasticity, and fitted layers arrive in phase 4, after GP5 (R7-09). *Rejected:* fitted layers in phase 3; an unstated resolution.

[[DIAGRAM diagrams/03-flux-per-region-discretization.jsx: per-region discretization · 4 models, 2 dI couplings]]

Read it top down: `mark_reduction` sorts each region into one of four models, and `dI` couplings join neighbours into one plan.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `flux::plan` | Problem, fidelity, class and `Budget` to a pinned `SolvePlan` with `explain()` | `PlanError::ExceedsLocal { memory, time }`; `NoValidMethod { region, reason }` | FLX-O-PLAN-1 | 1 |
| `flux::mark_reduction` | `Field<Body, ReductionKind>` from local criteria | `UnpairedFaces` from `mid_surface` keeps the region solid, with a note | FLX-O-PLAN-2 | 1 (lattices), 2 |
| Mixed-dimensional couplings | Rigid and Nitsche `dI` interfaces; tested junction zones | `IncompatibleInterface { region }` | FLX-O-PLAN-3 | 2 |
| Reduction error | 3D patch re-solves, calibrated per class | `NotQuantified`, making a `Pass` conditional | FLX-O-PLAN-4 | 2 |
| Wall-resolution rules | Octree refinement across laminar and frozen layers | Under-resolved zones Extrapolated | FLX-O-PLAN-5 | 3 |
| Region overrides | `plan.with(region:, model:)` in source | Unsuitable override warns with the criterion value | FLX-O-PLAN-1 | 1 |

## Discretizations

### Immersed octree

A 2:1-balanced octree covers the Body. Anvil's `GeometryQuery` classifies cells incrementally after local edits, and uncut cells are tensor-product cells with hanging-node constraints in the kernels.

- **Aggregated CutFEM.** Cut cells integrate on the true geometry with Nitsche conditions and ghost-penalty stabilization [Burman et al.]. Cut quadrature follows Saye's positive-weight methods, with Algoim (BSD-3-Clause-LBNL) as reference oracle, and moment fitting only with non-negative least squares. Cells below a 1% volume fraction aggregate with neighbours (a smooth weight in optimization, D-FLX-21); an uncertified cut subdivides up to eight levels, then fails with `UncertifiedCut { cell, achieved }`.
- **Shifted boundary.** Full interior cells only, with boundary data shifted along the closest-point vector [Atallah, Canuto, Scovazzi]; `Preview` only.
- **Finite cell.** A volume-fraction indicator with void stiffness α, for voxel, CT and density geometry; patch tolerance O(α).

**Decision D-FLX-13:** One octree serves three treatments, with at least four cells across any section. Aggregated CutFEM runs at `Interactive` (p = 2, one adaptive pass, cached cut quadrature) and `SignOff` (hp-adaptive). Finite cell serves voxel data, and the shifted boundary method serves `Preview` only. *Why:* stress checks sit on the true boundary, and one treatment means one estimator family, one set of classes and one singular-set logic (R7-17). *Rejected:* shifted boundary at `Interactive`, which extrapolates boundary stresses; two cells across a section (R1-02). (revised in round 3)

### Shells, beams and lattices

Reissner–Mindlin shells use MITC-type elements at p ≤ 2 [Dvorkin and Bathe] and hierarchic elements above, with locking measured by FLX-O-DISC-6; laminates use MEC's ABD matrices from phase 4. Kirchhoff–Love shells use C¹ NURBS spaces with Nitsche patch coupling and cut-cell trims [Bazilevs et al.]. Beams are Timoshenko, with a Vlasov warping unknown for open thin-walled sections and constants from a 2D warping solve.

**Decision D-FLX-44:** Beam lattices place Timoshenko struts on `anvil::lattice` strut graphs. Joint-zone length and stiffness are fitted per cell topology against full-resolution unit cells over a relative-density range, their envelope. Sheet lattices sign off on Reissner–Mindlin shells on the zero set of the cell's level-set field, from `anvil::mid_surface`; homogenization stays the continuum rung. *Why:* a fixed joint rule has no calibration route, and a full-resolution gyroid of 5 mm cells in a 100 mm cube needs about 4 × 10⁸ cells (R7-25). *Rejected:* a fixed one-radius joint zone; full-resolution sheet lattices.

Beam-lattice buckling factors come from D-FLX-41's estimates. Flux evaluates each member's regime variables for COV's envelopes, among them σ_cr,Euler / σ_proportional, which sends stocky struts to COV's Johnson or tangent-modulus rung.

### Explicit dynamics

Explicit dynamics serves drop tests (GP5) and crash boxes (GP9) with diagonal mass: spectral hexahedra, lumped B-spline shells and 15-node mass-lumped tetrahedra [Geevers, Mulder, van der Vegt]. Shells report hourglass energy, contact is penalty contact with `bvh_build` search, and COV's damage models drive erosion.

Targets are 10⁷ element cycles per second on the reference CPU and 5 × 10⁷ on its GPU at `Interactive`. Production models such as CCSA's 2015 Camry (2,277,283 elements) are then practical.

**Decision D-FLX-31:** Explicit dynamics on cut cells uses the discrete-extension CutFEM of Burman, Hansbo and Larson, whose extended-space mass lumps for leapfrog stepping, or aggregated cells with lumped mass. It stays disabled until FLX-O-DISC-7 shows a cut-independent critical step, and runs fitted or isogeometric meanwhile, canonically at `SignOff`. *Why:* lumped mass scales with the cut fraction while stiffness does not (R1-21), and ghost-penalty mass is not diagonal (R7-30). *Rejected:* ghost-penalty mass stabilization; unstated mass scaling. (revised in round 3)

### Electromagnetics

**Decision D-FLX-32:** Resonant and narrowband problems use frequency-domain Nédélec FEM; broadband and EMC problems use FDTD. Ports come from 2D eigenmode solves (`port_modes`), PML is a complex coordinate stretch, and an adaptive rational fast sweep (`fast_sweep`) carries a residual bound. *Why:* ELX requires Palace-level capability: lumped and numeric wave ports and an adaptive fast sweep (R1-22). *Rejected:* routing every antenna problem to FDTD.

FDTD uses the Yee grid with convolutional PML and auxiliary differential equations for dispersive materials. Conformal cells use the uniformly stable conformal update [Zagorodnov, Schuhmann, Weiland], or a stated cut-fraction cap with its accuracy cost. Magnetostatics and eddy currents use A–φ and T–Ω formulations with tree–cotree gauging or divergence-free coil currents.

Motion uses a sliding interface on a cylindrical air gap or mortar coupling, for ELX's loss maps (D-ELX-16). Boards use layered sheets: per-layer thin-sheet conduction coupled through-plane by `dI` conductances (R1-49).

### Fluids and free surfaces

Cell-centred finite volume runs on cut cells and polyhedra with coupled pressure–velocity solves. Mould filling uses a level set or volume of fluid, Hele-Shaw forms at `Interactive` (D-MFG-15) and D-FLX-45's wall resolution; Flux provides wall-model interfaces and COV the turbulence models. DG uses interior-penalty and upwind fluxes, and hybridizable DG couples only facet traces [Cockburn, Gopalakrishnan, Lazarov].

### General operations for non-variational methods

D-COV-11's operations serve particles, ray tracing, boundary elements and ELX's placer through `crucible:ops/flux`, each with a canonical CPU path and, where it pays, a WGSL path. Random streams come from KLN's `OpCx::rng`, keyed without class, fidelity or names (contract section 7.2).

Particle methods and lattice Boltzmann build on them, with errors from solution verification. Boundary elements build on bempp-rs, with fast multipole or H² compression and Calderón preconditioning for Maxwell [Scroggs et al.].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Fitted continuous FEM | Curved Anvil meshes to p ≤ 8; hex-dominant | `InvalidElement { cell, jacobian_min }` with an `untangle` fix | FLX-O-DISC-1 | 2, 4 (hex-dominant) |
| Aggregated CutFEM | `Interactive` and `SignOff` solids; Nitsche, ghost penalty, positive weights | `UncertifiedCut { cell, achieved }` | FLX-O-DISC-2, FLX-O-DISC-5 | 1 |
| Shifted boundary method | `Preview` solids | Never decides a check | FLX-O-DISC-3 | 2 |
| Finite cell method | Voxel, CT and density geometry | Patch error above O(α) | FLX-O-DISC-4 | 2 |
| Reissner–Mindlin and Kirchhoff–Love shells | Mid-surface sheets, thickness Fields, laminates | `UnpairedFaces` keeps the region solid | FLX-O-DISC-6 | 2, 4 (laminates) |
| Timoshenko and Vlasov beams | Member axes and section regions | `NotPrismatic` keeps the region solid | FLX-O-DISC-6 | 1 (struts), 2 |
| Beam-lattice models | Calibrated joints; per-member regime variables | `Indicator` outside the joint envelope | FLX-O-COUP-2 | 1 |
| Sheet-lattice shells | Shells on minimal-surface mid-surfaces | `UnpairedFaces` falls back to homogenization, stated | FLX-O-COUP-2 | 2 |
| DG and hybridizable DG | Advection-dominated and high-order problems | `CflViolated { cell }` | FLX-O-DISC-1 | 3 |
| Finite volume and free surfaces | Flow, filling, heat transfer | `NotConservative { cell, imbalance }` | FLX-O-DISC-10 | 3, 4, 5 (beyond filling) |
| Explicit dynamics | Diagonal mass, penalty contact, erosion; cut cells after FLX-O-DISC-7 | `StepCollapsed { element }` | FLX-O-DISC-7 | 3 (drop), 5 (erosion) |
| Frequency-domain electromagnetics | Nédélec, ports, PML, bounded fast sweep | `SweepNotConverged { band }` | FLX-O-DISC-8 | 4 |
| FDTD | Conformal Yee with CPML | Cut-fraction cap reported with its error | FLX-O-DISC-8 | 3 |
| Magnetodynamics with motion | A–φ and T–Ω; sliding interface or mortar | `SourceNotSolenoidal { coil }` | FLX-O-DISC-9 | 4 |
| Layered sheets | Thin-sheet conduction with through-plane `dI` | None beyond the solver's | FLX-O-DISC-6 | 3 |
| Boundary elements | Laplace, Helmholtz, Maxwell kernels with fast methods | `NotClosed { gaps }` from Anvil | FLX-O-DISC-12 | 3 |
| General operations | BVH, neighbours, reductions, random streams, FMM, H-matrices, FFT | `WorkLimit` | FLX-O-DISC-11 | 2, 3 (FMM, FFT) |
| Lattice Boltzmann | D3Q19 and D3Q27 on sparse grids | Instability reported with the step | FLX-O-DISC-11 | 4 |
| Particles and peridynamics | DEM, SPH, MPM, peridynamics | `Indicator` without solution verification | FLX-O-DISC-11 | 5 |

## Meshing and adaptivity

Anvil owns every mesh operation (D-ANV-12); Flux owns sizing and metric Fields, estimation, marking and transfer. Meshes, cut-cell sets and adaptation maps arrive keyed by `GeometryId` and canonical entity numbers, and `EntityId`s join only at the consumer.

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

Refinement is h (balanced octree, bisection, metric remeshing, hierarchical B-splines), hp (smooth cells by Legendre decay raise p, others split) or r (fitted meshes). The loop SOLVE → ESTIMATE → MARK → REFINE runs on declared goals with Dörfler marking at θ = 0.5, one node per iteration. Two stagnant iterations report a probable singularity.

### Interactive latency

Contract section 13.3 sets 1 s on G1 for warm-started elasticity up to 100,000 DOFs at p = 2. Stage budgets are targets: rebuild 150 ms and queries 200 ms (Anvil's), then setup 100 ms, solve 350 ms, estimate 100 ms and display 100 ms. The estimate stage includes CPU evaluation of GPU-solved Fields. Phase 0 measures them on GP1, GP2 and a named thin-walled part from the licence-filtered ABC subset, which GP5 replaces at the phase 3 gate.

**Decision D-FLX-37:** During a geometric drag, physics results show as `Proxy` until the full update arrives (phases 1 and 2). From phase 3, reduced models on a fixed background discretization answer parametric geometric drags through a morphing map from `anvil::shape_velocity`. *Why:* cell classification changes with geometry, so a reduced model on one discretization needs a morph (R1-16). *Rejected:* reduced-model answers for geometric drags in phase 1.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Sizing and metric Fields | `Field<Body, Length>`, `Field<Body, Metric>` from estimators | Anvil's `QualityNotReached { worst, target }` reported upward | FLX-O-MESH-1 | 2 |
| h-, p- and hp-adaptivity | Octree, fitted and spline refinement on declared goals | `ProbableSingularity { region }` on stagnation | FLX-O-MESH-1 | 1 (octree), 2, 3 (metric) |
| Solution transfer | Conservative projection, its error in the temporal part | Transfer error above tolerance refines the transfer | FLX-O-MESH-2 | 2 |
| Interactive stage budgets | Six stages within 1 s on G1 | A budget miss streams the coarse result as `Proxy` | FLX-O-MESH-3 | 1 |
| Geometric drags | `Proxy`, then morphing reduced models | `TopologyChange` ends the morph | FLX-O-ROM-1 | 1, 3 (morphing) |

## Solvers

### Linear algebra

Matrix-free, sparse and block operators compose as `LinearOperator`s over libCEED's vector layouts, solved by fixed-restart Krylov methods.

**Decision D-FLX-36:** `Portable` linear algebra runs on the canonical `linalg` crate: machine-independent blocking, canonical lane order, no FMA, index-ordered pivot ties. Unmodified faer runs only in `CpuIsa`. FLX owns sparse factorization in `linalg` (D-PLT-34): supernodal elimination with tree-level parallelism and a fixed child order, independent of thread count and of upstream acceptance. *Why:* faer sizes blocks from detected caches and uses FMA (R1-10, R6-21), and phase 1 cannot wait on upstream review (R7-35). *Rejected:* unmodified faer in the canonical class; single-threaded canonical factorization. (revised in round 3)

| Use | Method | Phase |
| --- | --- | --- |
| Symmetric problems to about 2M DOFs, coarse grids | Supernodal LLᵀ and LDLᵀ, nested dissection | 1, 2 (parallel) |
| Networks and circuits | Block-triangular LU with refactorization (KLU's scheme) | 2 |
| Indefinite Maxwell | Complex symmetric LDLᵀ to its memory limit | 4 |
| Mixed precision | `f32` factors with `f64` GMRES refinement when the condition estimate is below 10⁷ | 2 |
| Distributed | STRUMPACK (BSD-3-Clause-LBNL) or SuperLU_DIST (BSD-3-Clause) through `bridges/`; MUMPS (CeCILL-C) as an External Op | 4 |

GMRES refinement extends LU refinement from κ₂ ≤ 10⁴ to 10⁸ for half-precision factors [Carson and Higham]; the 10⁷ cutoff keeps κ · u_f32 below 1.

### Krylov methods and preconditioners

| Problem | Default | Phase |
| --- | --- | --- |
| Elliptic, high order, octree | p-, then h-multigrid, then deterministic AMG; Schwarz smoothing on cut cells | 1 |
| Low order and fitted | Smoothed-aggregation AMG; hypre BoomerAMG as a bridge | 1 |
| Shells and beams | Same hierarchy with rotational near-null modes | 2 |
| H(curl), H(div) | Auxiliary-space AMG (Hiptmair–Xu); hypre AMS and ADS as bridges | 3 |
| Stokes and Oseen | Block-triangular field split with PCD or a least-squares commutator | 3 |
| High-Reynolds steady Navier–Stokes | Augmented Lagrangian with patch smoothers | 4 |
| Transient high-order flow | Dual splitting with matrix-free pressure p-multigrid | 4 |
| Upwind DG transport | Approximate-ideal-restriction AMG | 3 |
| Indefinite Maxwell and Helmholtz | Complex LDLᵀ; optimized Schwarz; shifted-Laplacian multigrid | 4 |
| Distributed, above about 5 × 10⁷ DOFs | BDDC with deluxe scaling; FETI-DP for contact | 4 |

Low-order-refined de Rham preconditioners are spectrally equivalent independently of degree and mesh size [Pazner, Kolev, Dohrmann]. Global coarsening scales to 147,456 cores [Munch et al.], and Schwarz-type smoothers handle small cut cells [de Prenter et al., 2019].

**Decision D-FLX-16:** Flux builds its own matrix-free p- and h-multigrid with global coarsening and deterministic AMG, with Schwarz smoothers and aggregation at cut cells. hypre and PETSc are optional bridges. AMG uses exact strength comparisons, fixed-order Galerkin products and independent-set priorities hashed from canonical DOF numbers through `random_stream`. *Why:* AMG must coarsen identically in every class and run in Wasm, cut cells defeat point smoothers (R1-17), and hashed priorities stay well mixed (R7-35). *Rejected:* mandatory hypre or PETSc; Jacobi on cut cells; priorities from names, threads or ranks. (revised in round 3)

**Decision D-FLX-33:** Navier–Stokes uses PCD or least-squares commutators at moderate Reynolds numbers, an augmented Lagrangian preconditioner at high ones, and dual splitting for high-order transients. *Why:* pressure-mass Schur approximations suit only Stokes (R1-23). The augmented Lagrangian needs about 3 Krylov iterations per Newton step at Re = 1,000 and 5 at Re = 5,000 on a 10⁹-DOF cavity [Farrell, Mitchell, Wechsung]. *Rejected:* SIMPLE-type segregation as the only option.

### Nonlinear solvers and bifurcations

| Method | Use | Phase |
| --- | --- | --- |
| Newton–Krylov, exact Jacobians, backtracking, Eisenstat–Walker forcing | Convex forms in phase 1; every nonlinear form from phase 2 | 1, 2 |
| Trust-region Newton; arc length; semismooth Newton; Anderson acceleration | Energy forms; load paths; contact; partitioned coupling | 2 |
| Pseudo-transient continuation | Strongly nonlinear steady flows | 3 |
| Nonlinear preconditioning | ASPIN for localized nonlinearity [Hwang and Cai] | 4 |

**Decision D-FLX-25:** From phase 2, Newton and arc-length solvers monitor the tangent's inertia and return `Bifurcation { load, modes }` at a sign change instead of choosing a branch. The monitor is the LDLᵀ inertia under a direct solver, else a warm-started LOBPCG estimate of the smallest eigenvalue per converged step. In phase 1, Newton accepts only forms declared convex and otherwise returns `Unsupported { reason: NoBifurcationMonitor }`. Branches follow only an explicit imperfection or `branch: follow(mode: k, sign: +)`. *Why:* rounding picks Newton's branch (R1-13), and inertia exists only with a direct solver (R7-31). *Rejected:* silent branch choice; an eigensolve per load step. (revised in round 3)

Limit points are reported likewise, and electro-thermal runaway returns `Runaway { power }` (R1-49).

### Time integration

| Family | Use | Phase |
| --- | --- | --- |
| BDF orders 1 to 5; SDIRK, ESDIRK; additive Runge–Kutta IMEX | Stiff and stiff–nonstiff problems | 2 |
| Generalized-α, Lie group generalized-α | Structural and multibody dynamics | 2 |
| Central difference; SSP Runge–Kutta; symplectic schemes | Explicit dynamics, DG, finite volume, particles, FDTD | 3 |
| Exponential integrators; Parareal and MGRIT | Stiff linear-dominated problems; long horizons | 5 |

Temporal goal error is the adjoint-weighted residual in time. Summed local estimates are `Indicator`, because phase error accumulates in oscillatory problems (R1-20); step halving with frozen breakpoints is the calibrated alternative, also for ELX's circuit transients. Events are root-found on dense output.

### Eigenvalue problems

Shift-invert Lanczos with Krylov–Schur restarts and LOBPCG ship in phase 1 for modal analysis and buckling (contract section 13.4). Damping and flutter linearizations follow in phase 3, contour integrals in phase 4. Eigenvectors are mass-normalized, largest entry positive, and degenerate eigenspaces are subspaces.

**Decision D-FLX-41:** Eigenvalue checks rest on a DWR eigenvalue estimate [Heuveline and Rannacher], calibrated per class and applied on the unsafe side. Conforming Ritz values bound the lowest eigenvalues from above, so a check reads λ_h − η. The algebraic part comes from Kato–Temple or Lehmann bounds, the gap from the next Ritz value. Buckling solves K_G φ = μ K φ with the positive definite K as B and λ₁ = 1/μ_max. *Why:* without an estimator, frequencies and buckling factors never decide `SignOff`, and K_G is indefinite (R7-05). *Rejected:* a solver name as a calibration class; `Guaranteed` bounds on cut cells.

`Guaranteed` lower bounds exist for scalar diffusion on fitted simplices [Carstensen and Gedicke] and contract section 5 now admits them as `Guaranteed` bounds (CCR-FLX-11). Flux ships them in phase 2, with fitted tetrahedra. `flux::koiter_coefficient` computes a shell buckling mode's initial post-buckling coefficient for COV's imperfection-sensitivity variable, in phase 2 with nonlinear shells.

### Contact, constraints and fracture

| Mechanism | Enforcement | Phase |
| --- | --- | --- |
| Dirichlet; multi-point, periodic, cyclic and integral constraints | Strong on fitted meshes, Nitsche on immersed and spline; elimination or `Real` multipliers | 1 |
| Bonded interfaces; frictional contact | Mortar with dual multipliers and semismooth Newton; augmented Lagrangian; penalty at `Interactive` | 2 |
| Large sliding; immersed contact; thermal and electrical contact | Sorted deterministic search; Nitsche on cut surfaces, at p > 2 only after FLX-O-SOLVE-7's immersed case passes; conductance on `dI` | 3 |
| Incremental Potential Contact, for GP16's soft goods | Barrier distance d̂ and friction smoothing ε_v reported as `regularization` [Li et al.] | 5 |

Penalty results support `SignOff` only with estimated penetration below tolerance. Fracture hooks carry COV's models: J-integrals (phase 2), cohesive zones (3), phase field (4), cut-cell cracks and peridynamics (5).

### GPU solves, CPU certifies

**Decision D-FLX-17:** A GPU solve produces a Field pinned by `ObjectId`. The `Portable` `flux::certify` recomputes its residual and budget in `CpuCanonical` with `f64` evaluation, so the outcome is canonical although the Field's bits are not (contract section 7.3). `f32` inner solves run in defect correction on the CPU residual, and fall back to a canonical CPU solve after two cycles contracting by less than 2. *Why:* Metal and WebGPU lack `f64`, and defect correction stalls as κ(A)·u_f32 approaches 1 (R1-11). *Rejected:* uncertified `f32` results; forbidding GPUs at `SignOff`. (revised in round 2)

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Canonical direct solvers | Supernodal LLᵀ and LDLᵀ, block-triangular LU, complex LDLᵀ | `SingularOperator { null_space_hint }` | FLX-O-SOLVE-1 | 1 to 4 per row |
| Multigrid and AMG | p- and h-multigrid, Schwarz smoothers on cut cells, deterministic AMG | `LinearDiverged { residual_history }` | FLX-O-SOLVE-2 | 1 |
| Navier–Stokes preconditioners | PCD, LSC, augmented Lagrangian, dual splitting, AIR | `LinearDiverged`, preconditioner named | FLX-O-SOLVE-3 | 3, 4 |
| Electromagnetic solvers | Auxiliary-space AMG, complex LDLᵀ, optimized Schwarz | `LinearDiverged` | FLX-O-DISC-8 | 3, 4 |
| Nonlinear solvers | Newton, trust region, arc length, semismooth Newton, ASPIN | `NonlinearDiverged` with the last state; `Unsupported { reason: NoBifurcationMonitor }` | FLX-O-SOLVE-4 | 1 (convex forms), 2, 4 (ASPIN) |
| Bifurcation detection | LDLᵀ inertia or warm-started LOBPCG | `Bifurcation { load, modes }`; `Runaway { power }` | FLX-O-SOLVE-4 | 2 |
| Time integrators | Implicit, IMEX and explicit schemes with events | `StepTooSmall { t }` | FLX-O-SOLVE-5 | 2, 3 |
| Eigen-solvers | Lanczos and LOBPCG with K-weighted buckling; Krylov–Schur; contour integrals | `NotConverged { found, wanted }` | FLX-O-SOLVE-6 | 1, 3, 4 |
| Koiter coefficient | Post-buckling coefficient of a shell mode | `NotConverged { found, wanted }` | FLX-O-SOLVE-6 | 2 |
| Contact and constraints | Mortar, Nitsche, augmented Lagrangian, estimated penalty; IPC | `PenetrationAboveTolerance` blocks `SignOff` | FLX-O-SOLVE-7 | 1 to 3, 5 (IPC) |
| Bolted-joint forms | Preloaded bolt elements and joint springs for COV's VDI 2230 model | `JointOpened { bolt }`, with mortar contact as fix | FLX-O-SOLVE-9 | 2 |
| GPU solve with CPU certification | Pinned GPU Field; canonical residual and budget | Stall falls back to the canonical CPU solve | FLX-O-SOLVE-8 | 2 |

## Networks, multibody dynamics and rods

### Networks

ELX owns the `network { … }` builder, element libraries and the electrical fast path; Flux compiles and integrates Networks in every domain.

`flux::compile_network` flattens the hierarchy and applies D-FLX-27's reduction. It compiles each reachable mode of a switched network once and emits residuals and Jacobians in the kernel IR.

`flux::solve_dae` integrates with variable-order BDF and trapezoidal rules, events, consistent reinitialization and adjoints on the block-triangular LU. Network solves are `F64Required`, Monte Carlo batches run one sample per SIMD lane (R1-39), and results are Fields over `(Ports, Time)` or `(Ports, Frequency)`.

**Decision D-FLX-27:** Networks compile to index-1 DAEs by Pantelides reduction with static dummy-derivative selection per mode, BLT ordering, tearing and cached per-mode compilations. States are re-selected only at a deterministic event, when a pivot test shows the selected block singular. *Why:* one structural analysis is invalid after a mode change (R1-50), and selection between events would depend on solver history. *Rejected:* Pantelides without dummy derivatives; one analysis for switched networks.

### Multibody dynamics

MEC hands over an Assembly with typed joints, redundancy report, bounded mass properties, contact pairs and drivers (D-MEC-12), and `flux::solve_multibody` integrates it [Brüls, Cardona, Arnold].

- Joint axes expose ports, so a motor drive's Network drives a joint directly.
- Contact is compliant with regularized Coulomb friction until phase 4 brings the nonsmooth generalized-α scheme [Brüls, Acary, Cardona].
- Flexible bodies are Craig–Bampton reduced Parts or exact beams; results are `Field<(Instances, Time), Transform>`, joint loads and an energy balance.
- `flux::linearize_multibody` returns exact plant Jacobians at an operating point for ELX's control design.

MFG's assembly planner uses the same solver's quasi-static contact equilibrium (D-MFG-17).

**Decision D-FLX-28:** Multibody dynamics is an index-3 DAE on the Lie group of rigid motions, integrated by Lie group generalized-α with scaled constraints, with redundancy removed by rank-revealing QR. *Why:* no parameterization means no singular configurations, and the method is second-order in every unknown without index reduction. *Rejected:* Euler-angle or quaternion coordinates (singularities, normalization drift); Baumgarte-stabilized ODEs, which drift and need tuning.

### Cosserat rods

`flux::solve_rod` serves cables, harnesses and hoses [Gazzola et al.] with trust-region Newton statics, Lie group generalized-α dynamics and contact through Anvil distance queries. MEC's harness model uses the Kirchhoff limit.

**Decision D-FLX-29:** Cables and hoses are geometrically exact Cosserat rods sharing the multibody integrator, with Kirchhoff behaviour as the stiff-shear limit. *Why:* hoses stretch and shear under pressure and clamping, and one integrator couples rods to joints and contact. *Rejected:* inextensible Kirchhoff rods only; spring–mass chains, which converge poorly in bending and torsion.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `flux::compile_network` | Flattening, index reduction with dummy derivatives, BLT, tearing, per-mode compilation | `StructurallySingular { equations }`; `HighIndexAfterReduction` | FLX-O-NET-1 | 2 |
| `flux::solve_dae` | Index-1 DAE: BDF, trapezoidal rule, events, reinitialization, adjoints | `ReinitFailed { event }`; `StepTooSmall { t }` | FLX-O-NET-2 | 2 (mechanical, thermal), 3 (electrical) |
| Block-triangular sparse LU | Per-block ordering; numeric refactorization; complex arithmetic | `SingularOperator { block }` | FLX-O-NET-3 | 2 |
| `flux::solve_multibody` | Typed joints, redundancy handling, compliant contact, Network-driven joints | `InconsistentRedundancy { joints }`; `Bifurcation` at toggle points | FLX-O-MBD-1 | 2 (rigid), 3 (flexible), 4 (nonsmooth) |
| `flux::linearize_multibody` | Exact plant Jacobians at an operating point; `Differentiable` | `NotDifferentiable { op }` at contact events | FLX-O-OPT-1 | 4 |
| `flux::solve_rod` | Cosserat statics and dynamics with contact | `NonlinearDiverged` with the last state | FLX-O-MBD-2 | 4 |

## Coupling, homogenization and co-simulation

Monolithic coupling solves one product-space form by Newton with field-split preconditioning; partitioned coupling exchanges interface Fields until they agree.

| Coupling | Default | Phase |
| --- | --- | --- |
| Thermal stress, one way | Sequential solves joined through Kiln | 1 |
| Two-way thermo-mechanics; transient activation for joint-scale welding | Monolithic Newton with field split | 2, 4 (welding) |
| Electro-thermal Joule heating | Monolithic Newton with continuation; `Runaway { power }` | 4 |
| Conjugate heat transfer | Robin partitioned, or monolithic on a shared octree with D-FLX-45's wall refinement | 3 (laminar, natural convection), 4 (turbulent) |
| Electromagnetic–structural | Partitioned: Maxwell stress or virtual work | 4 |
| Fluid–structure | Aitken or interface quasi-Newton (IQN-ILS, IQN-IMVJ); monolithic ALE or Robin–Robin for strong added mass | 4 |
| Piezoelectric and electrostatic MEMS | Monolithic; pull-in reported as a bifurcation | 5 |

Element activation switches cells on by layer group (additive) or weld group (both phase 2, contract section 13.4), and transiently for joint-scale welding (phase 4). Interface transfer is conservative for fluxes and consistent for states, the interface residual joins the algebraic budget, and preCICE (LGPL-3.0) serves only as an external tool.

**Decision D-FLX-42:** Additive distortion by inherent strain is a declared sequence: layer-group activation of part and supports, baseplate cut, support removal and optional stress relief. Stress relief scales the strain by a calibrated relaxation factor. Supports are a homogenized lattice of calibrated stiffness, and every step's data comes from MFG's coupons, such as cantilevers cut from the plate. *Why:* the measured shape follows cutting, support removal and stress relief (R7-07). *Rejected:* activating the part alone; inherent strain in phase 1, before Crucible sees supports.

**Decision D-FLX-43:** On beam-modelled frames, weld shrinkage enters as equivalent joint loads per weld: longitudinal force, transverse shrinkage and angular distortion. They come from inherent strain on a local shell or solid joint model that `mark_reduction` keeps at each welded joint. The strains are MFG's coupon values per joint type, thickness, process and heat input (MFG-O-JOIN-2), enveloped by heat input per length and plate thickness. *Why:* inherent strain is undefined on a beam, and GP4's welds sit at joints a beam reduces to nodes (R7-20). *Rejected:* solid frames; macrograph-calibrated sources, which belong to the phase 4 transient model.

### Homogenization and lattices

`flux::homogenize` solves periodic unit cells and returns effective tensors as `Reduced` or `Surrogate` Fields with bounds, and `flux::localize` rebuilds the strut stresses that lattice checks read (R1-26). For COV's lattice envelope Flux computes cell size over gradient length, boundary distance in cells, and strut slenderness times compressive strain against a Bloch-wave bound.

Critical lattice regions sign off on beam lattices or sheet shells (D-FLX-44); dehomogenization runs through Anvil in phase 2, and FE² batches micro solves (D-FLX-38) in phase 5.

### Co-simulation over FMI and SSP

**Decision D-FLX-30:** Flux owns the FMI 3.0.2 and SSP 2.0.1 runtime: import, export, master algorithms and Model Exchange integration. Native-binary FMUs run as External Ops on untrusted-evaluation workers; FMUs with determinized Wasm binaries run in the sandbox as ordinary Ops. *Why:* native FMUs are untrusted code (contract section 7.8), and one runtime ends duplicate FMI specifications (R3-24). *Rejected:* native FMUs in the sandbox; per-tab FMI runtimes.

ELX keeps FMU elements and FMI-LS-BUS, and ECO keeps packaging. Flux runs each imported FMU twice in CI; one whose outputs differ is `NonDeterministic` and never shared.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Monolithic and partitioned coupling | Product-space forms; Aitken and interface quasi-Newton; conservative transfer | `CouplingDiverged { residual_history }` | FLX-O-COUP-1 | 1 to 5 per row |
| Element activation | Cells activated by a layer or time Field | `ActivationGap { layer }` | FLX-O-COUP-1 | 2 (layer and weld groups), 4 (transient) |
| Additive distortion sequence | Activation with supports, baseplate cut, support removal, stress relief | `OutsideEnvelope` outside the coupon data | FLX-O-COUP-4 | 2 |
| Weld joint loads on frames | Joint loads from local joint models and coupon inherent strains | `OutsideEnvelope` outside the coupon envelope | FLX-O-COUP-4 | 2 |
| Homogenization | Unit-cell solves to effective-tensor Fields | `NotPeriodic { faces }` | FLX-O-COUP-2 | 1 (elastic), 3 |
| Localization and lattice regimes | Micro stresses; scale, boundary-distance and buckling regime Fields | Zones `Invalid` or `Flag` per COV | FLX-O-COUP-2 | 1 |
| FE² | Batched micro solves per macro quadrature point | `MicroDiverged { point }` | FLX-O-COUP-2 | 5 |
| FMU import (all three interface types) | External Op or sandboxed Wasm; provided directional and adjoint derivatives | `NoBinaryForPlatform { available }`; stated finite differences otherwise | FLX-O-COUP-3 | 3 |
| FMU export and SSP | Co-Simulation FMUs with state serialization; SSP archives to and from Ingot | Size warning; unknown layered standards kept and reported | FLX-O-COUP-3 | 4 |
| Master algorithms | Jacobi, Gauss–Seidel, variable step with rollback, clocked partitions | FMUs without rollback run fixed-step, stated | FLX-O-COUP-3 | 3 |

## Gradients and optimization

Flux differentiates the discretized problem from its forms [Farrell et al.]. Kiln chains `Differentiable` operations backward from a scalar goal, and geometry enters through `anvil::shape_velocity`, which returns `TopologyChange`. `grad(J, wrt: [p1, p2])` and `hessian_vector(J, wrt: p, v)` return values bounded by the forward and adjoint algebraic parts and the discretization-consistency gap.

**Decision D-FLX-21:** Gradients are derivatives at a frozen discretization: cells, aggregation map, adaptive marks and time steps. The bound says so, Taylor tests straddling a discretization change are flagged, and optimization plans replace the hard aggregation switch with a smooth weight. *Why:* the discrete objective is not differentiable where the discretization changes (R1-19). *Rejected:* exact gradients across changes; operator-overloading AD of solver code; continuous adjoints. (revised in round 2)

| Problem | Adjoint | Cost | Phase |
| --- | --- | --- | --- |
| Linear and nonlinear steady | One transposed solve at the converged state | At most one forward solve | 1 |
| Eigenvalue | Eigenvector formula; subspace form for repeated eigenvalues | Small | 2 |
| Transient | Backward in time with multistage checkpointing | Two to five forward solves | 2 |
| Contact; coupled | Converged active set, changes flagged; block-transposed | As forward | 3; 4 |

Transient adjoints use the CAMS checkpointing of Zhang and Constantinescu, stored in Kiln's `Checkpoint` class by (`OpKey`, step), so an objective-only change reuses them.

### Topology optimization

| Method | Formulation | Phase |
| --- | --- | --- |
| Density | SIMP on the immersed octree; Helmholtz filter; Heaviside projection; robust eroded, intermediate and dilated designs; manufacturing constraints | 1 (compliance, volume), 2 (stress, robust, manufacturing) |
| Graded lattice | Homogenized cell-parameter maps, then dehomogenization | 1, 2 |
| Level set | Shape and topological derivatives with CutFEM | 3 |
| Multiphysics | Any coupled form through the coupled adjoint | 4 |

The optimizer is the method of moving asymptotes [Svanberg] with a globally convergent variant [Zillober], implemented natively from the papers as `flux::mma_step`. The loop is Ingot (`std::opt::topology`), so iterations are cached nodes. Results include `design.geometry_density`, the filtered, projected H¹ density with the gradient bound `anvil::implicit_from_field` requires (R1-57). Stress constraints aggregate regularized stresses by p-norms, and MFG's profiles parameterize manufacturing constraints.

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

Released geometry must be `Portable`, so `SignOff` optimization runs in `CpuCanonical` and GPUs accelerate only `Interactive` exploration. Targets are 10⁸ density elements on a 64-core server and 10⁹ on a cluster [Aage et al.].

### Shape, parameter and experimental design

Shape optimization works on feature parameters through the geometry chain rule, or on boundary-morphing Fields by the moving-mesh method [Paganini and Wechsung]. Optimizers are L-BFGS-B, SQP, interior point, MMA, trust region, CMA-ES and NSGA-II-type search, drawing randomness from KLN's `OpCx::rng`; Bayesian optimization is AGT's (D-AGT-15). `std::sim::study` runs designs of experiments, one node per point.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Form- and operation-level derivatives | `Differentiable` tangents and adjoints chained by Kiln; `grad`, `hessian_vector` | `NotDifferentiable { op }`; straddling tests flagged | FLX-O-OPT-1 | 0 (forms), 1 |
| Adjoints | Steady, eigen, transient with checkpointing, contact, coupled | `CheckpointMissing` triggers recomputation | FLX-O-OPT-3 | 1, 2 to 4 per row |
| Shape gradients | Chain rule through `anvil::shape_velocity` | `TopologyChange { parameter, entities }` | FLX-O-OPT-1 | 2 |
| Density topology optimization | SIMP, filters, projection, MMA; `geometry_density` | `Infeasible { constraints }` with the closest feasible design | FLX-O-OPT-2 | 1 |
| Level-set and multiphysics topology optimization | Shape and topological derivatives; coupled adjoints | As above | FLX-O-OPT-2 | 3, 4 |
| Optimizers and experimental designs | Gradient, evolutionary and multi-objective optimizers; designs of experiments | `NotConverged { iterations }` with the best design | FLX-O-OPT-2 | 1 (MMA), 2 |

## Uncertainty quantification

| Method | Use | Error part | Phase |
| --- | --- | --- | --- |
| Monte Carlo, randomized quasi-Monte Carlo | Reference method, yields | Confidence or repeated-scramble interval | 2 |
| Multilevel and multi-model Monte Carlo | Refinement hierarchies; reduced models as control variates | Bias and variance parts | 3 |
| Sparse polynomial chaos | Smooth dependence on up to about 20 parameters | Cross-validation | 3 |
| Grouped Sobol indices; Shapley effects [Song, Nelson, Staum] | Sensitivity with independent or dependent inputs | Bootstrap interval | 3 |
| Subset simulation, cross-entropy sampling; FORM | Failure probabilities below 10⁻³ | Coefficient of variation; FORM `Indicator` unless importance sampling confirms it | 3; 4 |
| Probability boxes | Epistemic intervals by nested sampling, never summed with distributions | — | 3 |

Multilevel Monte Carlo fits immersed plans, which already have level hierarchies [Giles].

**Decision D-FLX-35:** Propagating `Tol<T>` through physics is worst case by default (contract section 5). `std::uq::worst_case` sums half-widths times absolute adjoint sensitivities over correlated noise symbols. It then runs k Lanczos steps on the Hessian over the scaled box (default k = 5) and adds the remainder ½·|λ|max·‖h‖². The result is `Estimated`, and `NonlinearResponse` fires when the remainder exceeds 20% of the linear term. *Why:* a stationary response has a zero linear term that one Hessian-vector product misses (R7-23). *Rejected:* a uniform-distribution default; Monte Carlo for worst cases; a one-direction curvature check. (revised in round 3)

Statistical propagation is an explicit `std::uq::propagate` call, with MEC's default distribution (D-MEC-28) and skin-model samples. Flux supplies influence coefficients for MEC's compliant variation analysis in phase 2.

```
let stress = study.von_mises.max(over: p.away_from([clamp, web.face(role: end_cap)], 2 * thickness))
let worst = std::uq::worst_case(stress, inputs: tolerances(p))              // Approx<Stress>
let stats = std::uq::propagate(stress, inputs: tolerances(p), method: mlmc)
p.require(stats.quantile(0.999) < 0.6 * p.material.yield_strength(at: 20degC))
```

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Worst-case tolerance propagation | Adjoint-linearized affine bounds plus a Lanczos remainder; `Estimated` | `NonlinearResponse { ratio }` asks for a statistical method | FLX-O-UQ-3 | 2 |
| Sampling methods | Monte Carlo, randomized QMC, MLMC, multi-model | `BudgetTooSmall { samples }` before running | FLX-O-UQ-2 | 2, 3 |
| Polynomial chaos and sensitivity | Sparse PCE; grouped Sobol indices; Shapley effects | `DependentInputs` for plain Sobol on correlated inputs | FLX-O-UQ-1 | 3 |
| Rare events and reliability | Subset simulation, cross-entropy sampling, confirmed FORM | `NotConverged { cov }` | FLX-O-UQ-1 | 3, 4 |
| Epistemic inputs | Probability boxes by nested sampling | None | FLX-O-UQ-1 | 3 |
| Influence coefficients | Compliance at measurement points for MEC | `SingularOperator` without supports | FLX-O-UQ-3 | 2 |

## Reduced models and surrogates

| Model | Build | Error | Phase |
| --- | --- | --- | --- |
| Modal superposition; Craig–Bampton | Lanczos modes; fixed-interface and constraint modes per Part | Truncation estimates | 2 |
| POD–Galerkin; hyper-reduction | Snapshots; DEIM [Chaturantabut and Sorensen] or energy-conserving sampling | Residual-based, `Estimated` | 3 |
| Certified reduced basis | Greedy sampling of affinely parametrized linear forms | `Guaranteed`, coercivity bound by the successive constraint method [Huynh et al.] | 3 |
| Krylov moment matching | Frequency-domain reduction for sweeps and FMU export | Residual over the band | 3 |
| Morphing reduced models | Fixed background discretization plus `shape_velocity` morphs (D-FLX-37) | Residual-based | 3 |

A reduced model records its parameter box, and queries outside it fail with `OutsideParameterBox { parameter, range }` unless the caller requests a full solve.

### Surrogates

Surrogates cover strong nonlinearity and geometry families without a shared discretization: Gaussian processes for small data, neural operators and mesh graph networks for large data.

**Decision D-FLX-14:** A surrogate prediction is a Field of kind `Estimated { confidence, scope: Marginal }`. It drives `Preview`, `Interactive` and exploration. A `SignOff` check uses it only with a per-prediction bound in the check's norm or a confirming solve, and optimization loops calibrate by weighted conformal prediction. *Why:* conformal coverage is marginal [Barber et al.], optimizers steer toward a surrogate's errors, and energy bounds never certify peaks (R7-24). *Rejected:* split-conformal intervals as `SignOff` evidence; physics-informed networks as unbounded solvers. (revised in round 3)

The per-prediction bound projects the prediction onto the plan's finite element space. Energy, compliance and bounded linear functionals get an equilibrated estimate with a global coarse solve. Regularized peaks get a DWR estimate costing one adjoint solve, priced beside the confirming solve so the plan picks the cheaper. Weighted conformal calibration weights points by an estimated likelihood ratio [Tibshirani et al.] and reports the effective calibration size.

**Decision D-FLX-46:** Surrogate training may run in any class. The trained weights are a CAS artifact pinned by `ObjectId` in `ingot.lock`, labelled by their training data, and inference that feeds a check runs canonically. *Why:* deterministic GPU training may be too slow, and pinned weights make every prediction reproducible (R7-35). *Rejected:* canonical-only training; retraining inside an Evaluation.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Modal and Craig–Bampton models | Eigen-solve bases; assembly-level reduction | `OutsideParameterBox` beyond the band | FLX-O-ROM-1 | 2 |
| POD, reduced basis, hyper-reduction, morphing models | Snapshot bases; certified or residual bounds | `OutsideParameterBox { parameter, range }`; `TopologyChange` | FLX-O-ROM-1 | 3 |
| Surrogate training | Any class; pinned weights; stored calibration set and envelope | `CalibrationTooSmall { n }` | FLX-O-ROM-2 | 4 |
| Surrogate prediction | `Estimated { confidence, scope: Marginal }`; weighted conformal in loops | `Untrusted { reason }` outside the envelope | FLX-O-ROM-2 | 4 |
| Per-prediction bound | Equilibrated for energy and linear goals; DWR for peaks; priced against a confirming solve | `NotQuantified`, so `SignOff` needs a confirming solve | FLX-O-ROM-2 | 4 |

## Execution

A solve is a set of Kiln nodes demanded by an Evaluation. Kiln owns scheduling, caching and AGT's `Budget`; Flux supplies cost models, safe points and step checkpoints.

- **Placement.** The plan picks class and place (local CPU or GPU, team server, cloud) from memory and time estimates, never moving work to the cloud without permission. Browser evaluations follow PLT's heavy-worker rule (D-PLT-30).
- **Cost models.** They price refinement confirmation, per-prediction bounds, confirming solves and second trusted builders, so a plan compares them before running.
- **Aborts.** Aborts are never cached; completed adaptive iterations stay valid, and step checkpoints resume bit-identically.
- **Safe points.** Ends of time steps, adaptive and optimizer iterations, and Krylov restarts; `OpCx::checkpoint` is polled at least every 10 ms.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Placement and cost models | Plan-chosen class and place; `OpImpl::cost` estimates | `PlanError::ExceedsLocal { memory, time }` | FLX-O-EXEC-1 | 1 |
| Aborts and resumption | Aborts never cached; step checkpoints resume | Abort propagates to dependents | FLX-O-EXEC-1 | 1 |
| Cancellation latency | Safe points polled every 10 ms; 100 ms (target) | Missed latency fails the oracle | FLX-O-EXEC-2 | 1 |
| Remote and browser execution | Heavy worker above 512 MiB; remote above measured thresholds | `PlanError::ExceedsLocal` suggests remote evaluation | FLX-O-EXEC-1 | 1 |

## Post-processing and display

Probes are regularized goals (`f.at(x, smooth: ρ)`), and line and surface probes return Fields. Reactions use the variationally consistent residual method and, as bounded linear functionals, can carry `Guaranteed` bounds. Derived quantities include von Mises, principal and Tresca stresses, heat flux, safety factor and COV's fatigue damage; recovered display stresses are `Indicator`, for display only.

`std::sim::report` builds reports as Ingot data: plan explanation, budgets with confidence, validity zones, singular sets, convergence histories, margins and cost.

**Decision D-FLX-22:** Fields paint on the true geometry. Per-pixel WGSL evaluators read coefficient buffers on the UI process's device where the GPU tier allows; elsewhere refined vertex samples carry a stated interpolation error. Probes always sample exactly on the CPU, and display data never feed checks. *Why:* linear interpolation misplaces high-order peaks (D-UIX-13), and display work on the UI's device avoids a host round trip (R6-16). *Rejected:* rendering the analysis mesh. (revised in round 2)

Evaluators cover every `Discrete` element family, splines, `SparseGrid`, `Analytic` and `Reduced` Fields; other representations use vertex samples. Payloads carry quantized values with error, masks, deformations and glyphs.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Probes and derived quantities | Regularized point, line and surface probes; stress, thermal and fatigue quantities | `Undecided { SingularPoint }` near flagged sets | FLX-O-POST-1 | 1 |
| Reactions | Residual reactions with `Guaranteed` resultant bounds where proven | None | FLX-O-POST-1 | 1 |
| Reports | `std::sim::report` data for UI and CI | Missing budgets listed | FLX-O-POST-1 | 1 |
| Display evaluators | WGSL per-pixel evaluators on the UI's device | Tier without compute uses vertex samples, stated | FLX-O-POST-2 | 1 |
| Display samples | Adaptive vertex samples with interpolation error | None | FLX-O-POST-2 | 1 |
| Mode shapes | Modal and buckling eigenvector displays | Degenerate eigenspaces shown as subspaces | FLX-O-POST-2 | 1 |
| Isosurfaces, slices, streamlines, response functions | Display geometry, plus Implicit Bodies for geometry use | Streamline error above tolerance refines the step | FLX-O-POST-1 | 2 |

## State of the art

Figures are targets on contract section 13.3's reference laptop and one server per GPU vendor.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Weak-form language | UFL | DOLFINx, Firedrake (LGPL-3.0 or later) | UFL semantics with units | FEniCS and Firedrake demos |
| Form compilation | TSFC; libCEED operator split | FFCx, TSFC, MFEM | Native, to the kernel IR | 200 ms for p = 2 elasticity |
| High-order operators | Sum-factorized partial assembly [Kolev et al.; Fischer et al.; deal.II] | MFEM (BSD), libCEED (BSD-2-Clause) | Own canonical kernels | CEED rows |
| Immersed discretization | Aggregated CutFEM, Saye quadrature | ngsxfem (LGPL-3.0), GridapEmbedded (MIT) | One octree, one treatment | MMS rates; 1,000 shifts |
| Dimensional reduction | Nitsche mixed-dimensional coupling [Nguyen et al.] | — | Per-region marking, calibrated patches | 3D references |
| A posteriori estimation | Equilibrated flux [Smears and Vohralík]; DWR [Becker and Rannacher]; multilevel algebraic bounds [Papež et al.] | deal.II, MFEM | `Guaranteed` where proven; calibrated DWR | Effectivity; 1% undershoot |
| Solution verification | Grid convergence index [Roache, via NASA] | — | Calibrated GCI classes | 99% coverage |
| Multigrid | Global coarsening [Munch et al.]; low-order-refined de Rham [Pazner et al.] | hypre (Apache-2.0 OR MIT), MFEM | Own multigrid and AMG | 1.5× of MFEM with hypre |
| Navier–Stokes preconditioning | Augmented Lagrangian [Farrell, Mitchell, Wechsung]; PCD | Their published iteration counts | PCD, LSC, augmented Lagrangian | Cavity iterations within 2× |
| Sparse direct | Supernodal nested dissection; block-triangular LU | CHOLMOD (Supernodal GPL-2.0 or later), KLU (LGPL-2.1 or later), SuiteSparse 7.14.1; MUMPS (CeCILL-C) | Canonical `linalg` | 2× of CHOLMOD |
| Mixed precision | GMRES refinement [Carson and Higham] | — | `f32` factors, `f64` refinement | Full `f64` accuracy |
| Reproducible reductions | Binned summation [ReproBLAS] | ReproBLAS | `det_sum`, `exact_sum` | CG overhead 1.05× |
| Time integration | Adaptive BDF, IMEX Runge–Kutta, generalized-α | SUNDIALS (BSD-3-Clause) | Native, differentiable | 1.5× of SUNDIALS |
| Eigenvalues | Krylov–Schur, LOBPCG, contour integrals; DWR [Heuveline and Rannacher] | SLEPc (BSD-2-Clause), ARPACK-ng (BSD-3-Clause) | Native, calibrated | NAFEMS; 1.5× of SLEPc |
| Lumped networks | Pantelides with dummy derivatives | OpenModelica (AGPL-3.0, or OSMC-EPL for members); SUNDIALS IDA | Native | 2× of IDA |
| Multibody dynamics | Lie group and nonsmooth generalized-α [Brüls, Cardona, Arnold; Brüls, Acary, Cardona] | Project Chrono (BSD-3-Clause) | Native | 1.5× of Chrono |
| Rods | Cosserat rods [Gazzola et al.] | PyElastica (MIT) | Native | Elastica, helical buckling |
| Explicit dynamics | Spectral, spline and mass-lumped tetrahedral elements [Geevers et al.] | LS-DYNA (commercial) | Native; GPU at `Interactive` | 10⁷ element cycles per second |
| Full-wave electromagnetics | Nédélec FEM, wave ports, fast sweep | Palace (Apache-2.0) | Native | S-parameters against Palace |
| FDTD; boundary elements | Stable conformal Yee [Zagorodnov et al.]; Calderón-preconditioned BEM [Scroggs et al.] | Meep (GPL-2.0), openEMS (GPL-3.0); Bempp-cl (MIT), bempp-rs (BSD-3-Clause) | Native FDTD; bempp-rs | Cavity and Mie |
| Lattice Boltzmann, particles | Cumulant collision [Geier et al.]; δ-SPH [Marrone et al.]; MLS-MPM [Hu et al.] | XLB (Apache-2.0), run; FluidX3D, published figures only; DualSPHysics (LGPL-2.1); LAMMPS (GPL-2.0) | Native on general operations | Schäfer–Turek [Schäfer et al.]; SPHERIC dam break |
| Adjoints | Form-level derivation [Farrell et al.]; CAMS [Zhang and Constantinescu] | pyadjoint (LGPL-3.0); JAX-FEM (GPL-3.0) | Native through Kiln | Taylor order 2 |
| Topology optimization | Giga-voxel density methods [Aage et al.]; MMA [Svanberg] | TopOpt_in_PETSc | Native, canonical at `SignOff` | 10⁸ elements on 64 cores |
| Reduced models | POD with DEIM [Chaturantabut and Sorensen]; reduced basis with SCM [Huynh et al.] | pyMOR (BSD-2-Clause), RBniCS (LGPL-3.0) | Native | 100× at 1% error |
| Surrogates | Weighted conformal [Tibshirani et al.]; coverage limits [Barber et al.] | PhysicsNeMo (Apache-2.0) | Bounds in the check's norm | No false pass in 10⁴ evaluations |
| Uncertainty | MLMC [Giles]; sparse PCE; Shapley effects [Song, Nelson, Staum] | Dakota (LGPL-2.1 or later), OpenTURNS (LGPL-3.0 or later) | Native `std::uq` | Ishigami; MLMC exponent |
| Batteries | Doyle–Fuller–Newman | PyBaMM (BSD-3-Clause) | Parameter-domain forms | PyBaMM agreement |
| Co-simulation | FMI 3.0.2, SSP 2.0.1 | FMPy (BSD-2-Clause), OMSimulator (OSMC Public License) | Native runtime | Reference FMUs |

Linked dependencies are faer 0.24.4 (MIT, `CpuIsa` only), wgpu 30.0.1 (MIT OR Apache-2.0), bempp-rs 0.2.0 (BSD-3-Clause), hypre and PETSc as bridges, and CubeCL (MIT OR Apache-2.0) if adopted. LGPL code (preCICE, DOLFINx, NGSolve, Mmg) serves only as external tools or references, and GPL code (JAX-FEM, Meep, Elmer, OpenFOAM, LAMMPS) only as External Ops or oracles (contract section 7.7). FluidX3D forbids commercial use, so Crucible never runs it.

Algoim is BSD-3-Clause-LBNL, which contract section 7.7 permits, so Anvil ports or reimplements it on effort alone. PLT's register names fork plans for faer, wgpu and CubeCL (R6-30) and lists Algoim as reference oracle for FLX-O-DISC-2 and ANV-O-QUAD-1 (R7-36).

## Platform notes

| Platform | Risk | Decision |
| --- | --- | --- |
| Every Tier 1 CPU | SIMD width and FMA availability differ | Canonical lane order, no FMA in `CpuCanonical`; FMA `CpuIsa` variants below `SignOff` |
| Every CPU | Foreign code changes the floating-point state | Checked at start and end; Abort and rerun |
| macOS (Metal), browsers (WebGPU) | No `f64`; WGSL may fuse, reassociate and flush | `f32` `ClassExact` at `Interactive` with CPU `f64` estimation; CPU certification for `SignOff` |
| Browsers on G3 (WebGL2) | No compute shaders | Every solve on the Wasm CPU path, declared slower |
| Browsers | Memory never shrinks | Heavy worker above 512 MiB, remote beyond (D-PLT-30); `Interactive` 2 s with WebGPU, 6 s CPU-only |
| Linux servers | `f64` GPUs | Vulkan `SHADER_F64` from phase 3 |
| iPadOS and Android tablets (Tier 2) | Memory, thermals, Wasm in WebKit | `Preview` and small `Interactive` solves locally; the rest remote |
| Air-gapped installs | No cloud workers | User forms compile locally; External Ops need a local Linux worker |

## Interfaces with other subsystems

### What Flux provides

| To | Provides | Types |
| --- | --- | --- |
| ING | Spaces, measures, `solve`, `modes`, `minimize`, `continue_in`, plans, form checks; budgeted regularized reductions; property-basis propagation; singular sets; tangent and adjoint rules | `Field<D, V>`, `Expr<T>`, `ErrorBudget`, `Approx` |
| ANV | `field` and `kernels`; `Sampler`s with error and gradient bounds; `geometry_density`; reduction marking; sizing and metric Fields | `Field` |
| KLN | Operations with grades, fidelity maps, safe points, derivatives, checkpoints and cost models; pinned calibration tables | `OpImpl`, `Differentiable` |
| COV | Forms, solvers and estimators; calibration classes and corpus; calibrated solution verification; reduction and localization; `validity_zones`; strut regime variables; `koiter_coefficient`; `std::uq`; D-COV-11 operations | `Field`, `ValidityEnvelope` |
| MEC | Multibody and rod solvers; beams and laminated shells; bolted-joint forms; phase 1 classes and eigenvalue estimates; influence coefficients | `Field`, `Assembly` |
| MFG | Modal analysis; additive distortion and weld joint loads; thermo-elasto-plasticity; filling flow with wall resolution; topology optimization with manufacturing constraints | `Field`, `Body` |
| ELX | Network compiler and DAE solver with the temporal rule; block-triangular LU; layered sheets; electromagnetic solvers; conjugate heat transfer; electro-thermal coupling; parameter-domain forms; `fft_solve`; `linearize_multibody`; Verilog-A constructs; the FMI and SSP runtime | `Network`, `Field` |
| AGT | Study Evaluations, budgets, validity zones, plan explanations, cost estimates | `SolvePlan`, `Field` |
| UIX | WGSL evaluators; vertex samples with error; singular and validity masks; exact probes; streamlines; `Proxy` during drags; reports | `Field` |
| ECO | `crucible:field` and, with COV, the solver and constitutive worlds; Field encodings for AP209, CGNS, Exodus, VTK, BDF, Abaqus and OpenFOAM | `Field` |
| PLT | Grades, GPU roles, determinism corpora, resolved plans and marks for D-PLT-35; the kernel IR; sparse factorization; no-FMA penalties | `GpuPath` |

### What Flux requires

| From | Requirement |
| --- | --- |
| ING | Product-domain `Field` types; `Complex<Q>`, `select`; `Expr<T, Out>` and record results; `Approx`, `Truth` and the rule with `decides_on`; property reads as basis enclosures |
| ANV | `GeometryQuery` with positive-weight quadrature; `classify_edges` (phase 1); `mid_surface` with its implicit path, `member_axes`, strut graphs; meshes and adaptation keyed by `GeometryId`; `shape_velocity`; `implicit_from_field`; `common_refinement`; `DisplayPackage` back-references; its two stage budgets |
| KLN | `OpCx`, `OpCx::rng`, effective fidelity; reverse traversal; the `Checkpoint` class; Aborts; source-closure hashes; two trusted builders |
| PLT | `detmath`; `det_sum`, `exact_sum`; `linalg` (joint); `gpu` with known-answer tests; the dispatch rule; D-PLT-35's tolerances (R7-12); the browser memory table |
| COV | Physics and constitutive models with tangents; envelope records and zone semantics; regime functions, including σ_cr,Euler / σ_proportional per member and wall-resolution counts; the calibration-class map; turbulence, fatigue, fracture and damage models |
| MEC | Typed joints, drivers, preload, redundancy reports, bounded mass properties, contact candidates, member profiles, ABD matrices, distributions (D-MEC-28); classes per check |
| MFG | Process profiles with overhang angle, build and draw direction and minimum feature size; coupons for inherent strain, support stiffness, relaxation and weld joints; as-built strut calibration (phase 1) |
| ELX | The `network { … }` builder, port types, element libraries, the Verilog-A front end, board excitations and layered-sheet geometry; Flux's temporal rule in its transient checks |
| ECO | `crucible:ops/flux` generated from the catalog; the WIT index; registry hosting; FMU packaging; Field format readers and writers |

## Oracles

Oracles live in `oracles/flux/`, written by the oracle role. Held-out splits are chosen by a fixed hash rule outside the agent-readable tree, and corpus generators also run with CI-time seeds (contract principle 6). Runners are `cpu-ci` except: FLX-O-KER-4, FLX-O-SOLVE-8 and FLX-O-POST-2 in `gpu-lab`; FLX-O-KER-1 and FLX-O-MESH-3 in `device-farm` on the reference laptop; browser halves of FLX-O-KER-3, FLX-O-KER-6 and FLX-O-EXEC-1 in `browser-ci`.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| FLX-O-ARCH-1 | std physics in a user namespace; a solver Wasm component | Bit-identical to std |
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
| FLX-O-ERR-2 | Linear goals, `Guaranteed` algebraic parts | Bound at least the true error in every case; totals `Estimated` wherever a part is |
| FLX-O-ERR-3 | Calibrated DWR; refinement confirmation | Bound covers the true error in 99% of held-out cases per class; 10⁴ CMA-ES evaluations (fixed seeds) find no undershoot in an envelope; a fillet-radius sweep's budget covers the converged raw peak; under-calibrated entries yield `CalibrationUnconfirmed` |
| FLX-O-ERR-4 | Singular sets | Seeded singular edges flagged, smooth controls not; a 90° corner flagged under shear traction only; Hertz contact unflagged, a flat punch flagged; an imported filleted bracket's check decides |
| FLX-O-ERR-5 | Calibration tables | Each entry: 300 held-out samples, 20% optimizer-generated, zero undershoots, discard rate reported |
| FLX-O-ERR-6 | Temporal estimates, 100 periods of an oscillator and a wave | Estimates cover the true error in 99% of held-out cases |
| FLX-O-ERR-7 | `Preview` results | Never `Pass` or `Fail`; never shared |
| FLX-O-ERR-8 | Solution verification on benchmark flows | Calibrated GCI bands cover the reference in 99% of held-out cases per family; adapted runs `Indicator` |
| FLX-O-ERR-9 | Validity zones (COV's zone-semantics row cites it) | Match COV's labelled cases; `Refuse` yields `ValidityError::OutsideEnvelope`; excursions between output steps caught |
| FLX-O-ERR-10 | Cross-class agreement | D-PLT-35's tolerances hold on the determinism corpus |
| FLX-O-ERR-11 | Property-basis propagation | Enclosures contain 50 sampled-property solves on each of 20 cases, sign changes included |
| FLX-O-FORM-1 | Static form checks | 100 textbook forms pass; seeded errors fail with the right code |
| FLX-O-FORM-2 | Symbolic derivatives | Taylor order 2 ± 0.1 for every operator |
| FLX-O-FORM-3 | `local_solve`, Wasm tangents | Taylor tests pass; quadratic Newton convergence on a plasticity benchmark |
| FLX-O-FORM-4 | UFL coverage | Every demo of the pinned FEniCS and Firedrake releases expressible |
| FLX-O-FORM-5 | Parameter-domain forms | SPMe and P2D DFN voltage within 1 mV of PyBaMM on shared parameter sets |
| FLX-O-KER-1 | CEED problems plus immersed elasticity | Under 10⁻¹² from assembled references; both CEED rows of contract section 13.3 |
| FLX-O-KER-2 | No-FMA penalty, `CpuIsa` variants | Penalty published per degree and ISA; variants within 10⁻¹² of canonical |
| FLX-O-KER-3 | CPU kernel determinism | Bit-identical across threads, ISAs and targets |
| FLX-O-KER-4 | GPU paths | Known-answer tests run; injected NaN detected; CPU budgets cover the gap to canonical solves |
| FLX-O-KER-5 | Floating-point environment | A planted flush-to-zero library causes Abort and rerun |
| FLX-O-KER-6 | User-form speed | 1.5× memory-bound, 2.5× (AVX2) and 5× (AVX-512) compute-bound (targets); a 20% regression blocks |
| FLX-O-PLAN-1 | Plans and overrides | Same plan in every class; old plan versions reproduce old results |
| FLX-O-PLAN-2 | Reduction marking | Known cases marked as expected; plates under pressure, pressurized cylinders and a free plate in modal analysis mark `Shell` |
| FLX-O-PLAN-3 | Mixed-dimensional couplings | Patch tests pass; a welded T-joint, a cylinder-to-flange junction and a gusseted node stay inside the reduction part |
| FLX-O-PLAN-4 | Reduction error | Estimate covers the 3D-versus-reduced difference in 99% of held-out frames and shells |
| FLX-O-PLAN-5 | Wall-resolution rules | On a heated cavity and a 3D fill, one more refinement moves the quantity less than its budget |
| FLX-O-DISC-1 | Manufactured solutions | Rate within 0.1 of theory over three refinements, above 10³ times round-off |
| FLX-O-DISC-2 | Immersed iterations, cut quadrature | Iterations within 1.5× over 1,000 shifts for p = 1 to 4; quadrature within 10⁻¹² of Algoim |
| FLX-O-DISC-3 | Shifted boundary | Interior rates within 0.1 of theory; never decides a check |
| FLX-O-DISC-4 | Patch tests | Fitted, immersed and spline exact to solver tolerance; finite cell within O(α) |
| FLX-O-DISC-5 | NAFEMS P18 static, thermal and free vibration | Within 1% at `SignOff` |
| FLX-O-DISC-6 | Shells, beams, layered sheets | Within 1% of converged references at p ≥ 3 and 2% at p ≤ 2, on 20 cases |
| FLX-O-DISC-7 | Explicit dynamics | Energy error under 1%; cut-cell step within 10% of uncut over 1,000 shifts; regime extrema under 2% of solve time |
| FLX-O-DISC-8 | Electromagnetics | Cavity modes within 0.1%; S-parameters within 0.01 of Palace; Mie within 1%; cut-independent FDTD step |
| FLX-O-DISC-9 | Magnetodynamics with motion | Torque and loss within 5% on TEAM problems 24 and 30a; solenoidal sources |
| FLX-O-DISC-10 | Finite volume, free surfaces | Cell and filled-volume conservation to solver tolerance |
| FLX-O-DISC-11 | General operations, particles | Thread-count independence; Philox vectors; SPHERIC 3D dam break and granular collapse within 10% |
| FLX-O-DISC-12 | Boundary elements | Sphere scattering within 1% of Mie; cost below N^1.2 from 10⁴ to 10⁶ unknowns |
| FLX-O-MESH-1 | Adaptivity | Optimal rates on L-shape and Fichera corners; stagnation reported |
| FLX-O-MESH-2 | Solution transfer | Conservation to solver tolerance; reported error at least the measured one |
| FLX-O-MESH-3 | `Interactive` stage budgets | Within budget on the three benchmarks (targets); 1.5× a budget blocks |
| FLX-O-SOLVE-1 | Direct solvers | Round-off backward error; identical under two cache settings and any thread count |
| FLX-O-SOLVE-2 | Multigrid and AMG | h- and p-independent iterations on BP3 and BP5; thread-independent aggregates; iterations against hypre |
| FLX-O-SOLVE-3 | Navier–Stokes preconditioners | Cavity iterations within 2× from Re = 10 to 1,000 |
| FLX-O-SOLVE-4 | Nonlinear solvers, bifurcations | Perfect column bifurcates at the Euler load, imperfect one follows its branch; phase 1 non-convex forms `Unsupported` |
| FLX-O-SOLVE-5 | Time integrators | Observed orders match theory; events at identical times across classes |
| FLX-O-SOLVE-6 | Eigen-solvers and estimates | NAFEMS free vibration within 0.5%; estimates on it and Euler columns cover 99% of held-out cases; Koiter coefficients within 2% |
| FLX-O-SOLVE-7 | Contact | Hertz peak pressure within 1%, immersed at p > 2 included; unestimated penalty never supports `SignOff` |
| FLX-O-SOLVE-8 | GPU solves, CPU certification | Certified verdicts equal canonical verdicts; stalls fall back |
| FLX-O-SOLVE-9 | Bolted-joint forms | Bolt forces inside their bounds against 3D mortar-contact models in 99% of held-out joints; opening yields `JointOpened` |
| FLX-O-NET-1 | Network compilation | Index-3 pendulum reduced; clutch and diode bridge reinitialize consistently |
| FLX-O-NET-2 | DAE integration | Analytic RLC and drivetrain within 10⁻⁶; ngspice references within 0.1% |
| FLX-O-NET-3 | Block-triangular LU | Refactorization bit-identical to fresh factorization |
| FLX-O-MBD-1 | Multibody dynamics | Order within 0.1 of 2 on heavy top and slider–crank; redundancy reported |
| FLX-O-MBD-2 | Rods | Elastica, helical buckling and hanging cable within 1% |
| FLX-O-COUP-1 | Coupling and activation | Partitioned and monolithic agree within budgets; Turek–Hron within 5% |
| FLX-O-COUP-2 | Homogenization and lattices | Tensors within 1% of full unit cells; strut peaks inside budget on 20 held-out lattices; joints and sheet shells inside their envelopes |
| FLX-O-COUP-3 | FMI and SSP | Reference FMUs on every Tier 1 OS; SSP round trips; master error order |
| FLX-O-COUP-4 | Additive and weld distortion | Coupon distortion within coupon scatter on held-out coupons; joint loads within 5% of 3D joint models |
| FLX-O-OPT-1 | Derivatives | Taylor order 2 ± 0.1 for every `Differentiable` operation |
| FLX-O-OPT-2 | Topology optimization | MBB beam and 3D cantilever within 2% of published compliance |
| FLX-O-OPT-3 | Adjoints and checkpoints | Steady adjoint 1.2× a forward solve (target), 2× blocks; resumes bit-identical |
| FLX-O-UQ-1 | Sensitivity and rare events | Ishigami indices; correlated Shapley case; known failure probabilities |
| FLX-O-UQ-2 | Multilevel Monte Carlo | Cost exponent within 0.2 of theory |
| FLX-O-UQ-3 | Worst-case propagation | Bounds contain sampled extremes when the remainder is under 20% of the linear term; a stationary gap is caught |
| FLX-O-ROM-1 | Reduced models | Certified bounds hold; 100× speedup at under 1% error (target), 10× blocks |
| FLX-O-ROM-2 | Surrogates | Nominal coverage held out; 10⁴ CMA-ES evaluations per surrogate find no false `SignOff` `Pass`; both bound costs reported |
| FLX-O-EXEC-1 | Aborts and resumption | Injected faults never change cached values; resumes bit-identical |
| FLX-O-EXEC-2 | Cancellation | 100 ms (target); 250 ms blocks |
| FLX-O-POST-1 | Post-processing | Reactions balance loads; probes exact on analytic Fields; reports complete |
| FLX-O-POST-2 | Display | Within the stated interpolation error of exact CPU samples |

## Phasing

Capabilities that several tabs phase take their phase from contract section 13.4.

| Phase | Flux contribution to the gate |
| --- | --- |
| 0 | Determinism suite green for Flux kernels; unit errors in forms fail to compile; kernel IR v0 frozen after its three consumers pass; H¹ elements, CG and manufactured solutions; CEED baselines and no-FMA penalties; the `CpuIsa` measurement that decides WGSL elasticity; nothing frozen before the Flux rename |
| 1 | GP1: aggregated CutFEM, calibrated DWR with envelopes and refinement confirmation, singular sets, p-multigrid over AMG, eigen-solvers with estimates and mode shapes, convex Newton. GP2: density topology optimization, steady adjoints, homogenization, beam lattices with strut buckling, `geometry_density`. The four calibration classes. Deferred (contract section 13.2): cut-cell guaranteed estimators, the shifted boundary method, GPU `SignOff`, CUDA or HIP, and WGSL elasticity unless phase 0 needs it |
| 2 | GP3: fitted tetrahedra with mortar contact, rigid multibody, drivetrain Networks, transient solvers and adjoints, modal reduction. GP4: beams, shells, couplings, thermo-elasto-plasticity, weld joint loads. Also additive distortion, bolted-joint forms, sheet-lattice shells, bifurcation monitors, Koiter coefficients, GPU solves certified on the CPU, worst-case tolerances |
| 3 | GP5: filling with fibre orientation, warpage and wall resolution, explicit drop dynamics, laminar conjugate heat transfer, layered sheets, circuit DAEs, FDTD, flexible multibody, FMU import, statistical uncertainty, calibrated solution verification, UFL coverage |
| 4 | GP6: turbulent conjugate heat transfer, electro-thermal coupling, FMU export and SSP, SPMe forms, cell swelling and stack pressure, Navier–Stokes preconditioners, lattice Boltzmann, fluid–structure interaction, magnetodynamics with motion, full-wave FEM, rods, nonsmooth multibody and its linearization, surrogates, ASPIN, BDDC, laminated shells; CUDA or HIP reconsidered |
| 5 and later | GP7 MEMS (piezoelectric coupling, pull-in); GP8 steel frames; GP9 crash with erosion; DFN cells; battery abuse mechanics (6); circuit harmonic balance; free surfaces beyond filling; particles; FE²; IPC for GP16 |

## Open questions

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

## Contract change requests

- CCR-FLX-8, a `regularization` error source: accepted in contract v4.1, section 5.
- CCR-FLX-9, one physics phase table: accepted in contract v4.2, section 13.4.
- CCR-FLX-10, boundary layers: accepted in contract v6.1 (section 7.1).
- CCR-FLX-11, eigenvalue bounds: accepted in contract v6.1 (section 5, `ErrorBound`).

## Sources

1. CEED, "CEED Bake-off Problems (Benchmarks)": https://ceed.exascaleproject.org/bps/
2. MFEM, "Features": https://mfem.org/features/
3. faer 0.24.4 documentation: https://docs.rs/faer/latest/faer/
4. CubeCL repository: https://github.com/tracel-ai/cubecl
5. UFL documentation: https://docs.fenicsproject.org/ufl/main/
6. FMI Standard home page: https://fmi-standard.org/
7. FMI 3.0.2 specification: https://fmi-standard.org/docs/3.0.2/
8. SSP Standard home page: https://ssp-standard.org/
9. libCEED API documentation: https://libceed.org/en/latest/libCEEDapi/
10. Kolev et al., "Efficient Exascale Discretizations: High-Order Finite Element Methods": https://arxiv.org/abs/2109.04996
11. Fischer et al., "Scalability of High-Performance PDE Solvers": https://arxiv.org/abs/2004.06722
12. deal.II matrix-free module documentation: https://www.dealii.org/current/doxygen/deal.II/group__matrixfree.html
13. W3C, WGSL specification (partially read): https://www.w3.org/TR/WGSL/
14. WebGPU conformance test suite, floating-point primer: https://kdab.searchfox.org/firefox-main/source/dom/webgpu/tests/cts/checkout/docs/fp_primer.md
15. wgpu `Features` documentation: https://wgpu.rs/doc/wgpu/struct.Features.html
16. wgpu 30.0.1 documentation: https://docs.rs/wgpu/latest/
17. Rust RFC 3514, "Float semantics": https://rust-lang.github.io/rfcs/3514-float-semantics.html
18. ReproBLAS: https://bebop.cs.berkeley.edu/reproblas/
19. PETSc licence: https://petsc.org/release/install/license/
20. hypre documentation: https://hypre.readthedocs.io/en/latest/
21. SUNDIALS licence: https://computing.llnl.gov/projects/sundials/license
22. Smears and Vohralík, "Simple and robust equilibrated flux a posteriori estimates for singularly perturbed reaction–diffusion problems", ESAIM: M2AN 54(6), 2020: https://www.numdam.org/item/M2AN_2020__54_6_1951_0
23. Becker and Rannacher, "An optimal control approach to a posteriori error estimation in finite element methods", Acta Numerica 10, 2001: https://www.cambridge.org/core/journals/acta-numerica/article/abs/an-optimal-control-approach-to-a-posteriori-error-estimation-in-finite-element-methods/5C67A03F528C6FA69F37A97DF5C3BE19
24. Munch, Heister, Prieto Saavedra, Kronbichler, "Efficient distributed matrix-free multigrid methods on locally refined meshes for FEM computations": https://arxiv.org/abs/2203.12292
25. Pazner, Kolev, Dohrmann, "Low-order preconditioning for the high-order finite element de Rham complex": https://arxiv.org/abs/2203.02465
26. Atallah, Canuto, Scovazzi, "Analysis of the Shifted Boundary Method for the Poisson Problem in General Domains": https://arxiv.org/abs/2006.00872
27. Burman, Claus, Hansbo, Larson, Massing, "CutFEM: Discretizing Geometry and Partial Differential Equations" (record): https://www.simula.no/research/cutfem-discretizing-geometry-and-partial-differential-equations
28. Cockburn, Gopalakrishnan, Lazarov, "Unified hybridization of discontinuous Galerkin, mixed and continuous Galerkin methods for second order elliptic problems": https://conservancy.umn.edu/items/c0fca618-a7ca-40d0-b701-7c94235cd97b
29. Bazilevs, Beirão da Veiga, Cottrell, Hughes, Sangalli, "Isogeometric Analysis: Approximation, stability and error estimates for h-refined meshes" (report): https://www.oden.utexas.edu/media/reports/2006/0604.pdf
30. Homolya, Mitchell, Luporini, Ham, "TSFC: a structure-preserving form compiler": https://arxiv.org/abs/1705.03667
31. Farrell, Ham, Funke, Rognes, "Automated derivation of the adjoint of high-level transient finite element programs": https://arxiv.org/abs/1204.5577
32. Zhang and Constantinescu, "Optimal Checkpointing for Adjoint Multistage Time-Stepping Schemes": https://arxiv.org/abs/2106.13879
33. Aage, Andreassen, Lazarov, Sigmund, "Giga-voxel computational morphogenesis for structural design", Nature 550, 2017: https://www.nature.com/articles/nature23911
34. Giles, "Multilevel Monte Carlo methods": https://arxiv.org/abs/1304.5472
35. Angelopoulos and Bates, "A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification": https://arxiv.org/abs/2107.07511
36. Carson and Higham, "Accelerating the Solution of Linear Systems by Iterative Refinement in Three Precisions": https://eprints.maths.manchester.ac.uk/2629/
37. NAFEMS, "The Standard NAFEMS Benchmarks" (P18): https://www.nafems.org/publications/resource_center/p18/
38. JAX-FEM repository: https://github.com/deepmodeling/jax-fem
39. DOLFINx repository: https://github.com/FEniCS/dolfinx
40. preCICE documentation: https://precice.org/docs.html
41. Mmg home page: https://www.mmgtools.org/
42. NGSolve home page: https://www.ngsolve.org/
43. bempp-rs repository: https://github.com/bempp/bempp-rs
44. Algoim (Saye's quadrature and closest-point methods): https://algoim.github.io/
45. Palace documentation: https://awslabs.github.io/palace/stable/
46. Barber, Candès, Ramdas, Tibshirani, "The limits of distribution-free conditional predictive inference": https://arxiv.org/abs/1903.04684
47. Tibshirani, Barber, Candès, Ramdas, "Conformal Prediction Under Covariate Shift": https://arxiv.org/abs/1904.06019
48. CCSA, 2015 Toyota Camry finite element model: https://www.ccsa.gmu.edu/models/2015-toyota-camry/
49. Farrell, Mitchell, Wechsung, "An augmented Lagrangian preconditioner for the 3D stationary incompressible Navier-Stokes equations at high Reynolds number": https://arxiv.org/abs/1810.03315
50. Project Chrono repository: https://github.com/projectchrono/chrono
51. PyElastica repository: https://github.com/GazzolaLab/PyElastica
52. NASA Glenn, "Examining Spatial (Grid) Convergence" (Roache's grid convergence index): https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html
53. OpenModelica compiler flags (index reduction methods): https://openmodelica.org/doc/OpenModelicaUsersGuide/latest/omchelptext.html
54. SuiteSparse repository: https://github.com/DrTimothyAldenDavis/SuiteSparse
55. PyBaMM repository: https://github.com/pybamm-team/PyBaMM
56. Brüls, Cardona, Arnold, "Lie Group Generalized-α Time Integration of Constrained Flexible Multibody Systems", Mechanism and Machine Theory 48, 2012: https://ri.conicet.gov.ar/handle/11336/18837
57. Bertrand, Kober, Moldenhauer, Starke, "Weakly symmetric stress equilibration and a posteriori error estimation for linear elasticity": https://arxiv.org/abs/1808.02655
58. Papež, Rüde, Vohralík, Wohlmuth, "Sharp algebraic and total a posteriori error bounds for h and p finite elements via a multilevel approach", CMAME 371, 2020 (record): https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.cma.2020.113243?fields=title,abstract,year,authors
59. Arnold and Winther, "Mixed finite elements for elasticity", Numerische Mathematik 92, 2002 (Crossref record): https://api.crossref.org/works?query.bibliographic=Arnold+Winther+Mixed+finite+elements+for+elasticity+Numerische+Mathematik&rows=2
60. Hu and Zhang, "A family of symmetric mixed finite elements for linear elasticity on tetrahedral grids", Science China Mathematics 58, 2015 (Crossref record): https://api.crossref.org/works?query.bibliographic=Hu+Zhang+family+of+conforming+mixed+finite+elements+for+linear+elasticity+on+tetrahedral+grids&rows=2
61. Heuveline and Rannacher, "A posteriori error control for finite element approximations of elliptic eigenvalue problems", Advances in Computational Mathematics 15, 2001 (Crossref record): https://api.crossref.org/works?query.bibliographic=Heuveline+Rannacher+posteriori+error+control+eigenvalue+problems&rows=3
62. Carstensen and Gedicke, "Guaranteed lower bounds for eigenvalues", Mathematics of Computation 83, 2014 (Crossref record): https://api.crossref.org/works?query.bibliographic=Guaranteed+lower+bounds+for+eigenvalues+Carstensen+Gedicke&rows=2
63. Williams, "Stress Singularities Resulting From Various Boundary Conditions in Angular Corners of Plates in Extension", Journal of Applied Mechanics 19, 1952 (Crossref record): https://api.crossref.org/works?query.bibliographic=Stress+singularities+resulting+from+various+boundary+conditions+in+angular+corners+of+plates+in+extension&rows=2
64. Burman, Hansbo, Larson, "Explicit Time Stepping for the Wave Equation using CutFEM with Discrete Extension": https://arxiv.org/abs/2011.05386
65. de Prenter et al., "Scalable multigrid methods for immersed finite element methods and immersed isogeometric analysis", Computational Mechanics, 2019: https://arxiv.org/abs/1903.10977
66. Zagorodnov, Schuhmann, Weiland, "A uniformly stable conformal FDTD-method in Cartesian grids", 2003 (Crossref record): https://api.crossref.org/works?query.bibliographic=A+uniformly+stable+conformal+FDTD-method+in+Cartesian+grids&rows=2
67. Brüls, Acary, Cardona, "Simultaneous enforcement of constraints at position and velocity levels in the nonsmooth generalized-α scheme", CMAME 281, 2014 (Crossref record): https://api.crossref.org/works?query.bibliographic=Simultaneous+enforcement+of+constraints+at+position+and+velocity+levels+in+the+nonsmooth+generalized-alpha+scheme&rows=2
68. Hwang and Cai, "A parallel nonlinear additive Schwarz preconditioned inexact Newton algorithm for incompressible Navier–Stokes equations", JCP 204, 2005 (Crossref record): https://api.crossref.org/works?query.bibliographic=Additive+Schwarz+preconditioned+inexact+Newton+methods+for+nonlinear+partial+differential+equations+Cai+Keyes&rows=2
69. Algoim licence: https://raw.githubusercontent.com/algoim/algoim/master/LICENSE
70. FluidX3D licence: https://raw.githubusercontent.com/ProjectPhysX/FluidX3D/master/LICENSE.md
71. XLB repository: https://github.com/Autodesk/XLB
72. Li et al., "Incremental Potential Contact", ACM Transactions on Graphics, 2020: https://ipc-sim.github.io/
73. ngsxfem repository: https://github.com/ngsxfem/ngsxfem
74. GridapEmbedded.jl licence: https://raw.githubusercontent.com/gridap/GridapEmbedded.jl/master/LICENSE.md
75. TopOpt_in_PETSc repository: https://github.com/topopt/TopOpt_in_PETSc
76. pyMOR repository: https://github.com/pymor/pymor
77. RBniCS repository: https://github.com/RBniCS/RBniCS
78. OpenTURNS repository: https://github.com/openturns/openturns
79. Dakota repository: https://github.com/snl-dakota/dakota
80. OMSimulator repository: https://github.com/OpenModelica/OMSimulator
81. Meep repository: https://github.com/NanoComp/meep
82. openEMS repository: https://github.com/thliebig/openEMS
83. Bempp-cl repository: https://github.com/bempp/bempp-cl
84. Scroggs, Betcke, Burman, Śmigaj, van 't Wout, "Software frameworks for integral equations in electromagnetic scattering based on Calderón identities": https://arxiv.org/abs/1703.10900
85. Geevers, Mulder, van der Vegt, "New Higher-Order Mass-Lumped Tetrahedral Elements for Wave Propagation Modelling": https://arxiv.org/abs/1803.10065
86. Fuentes, Keith, Demkowicz, Nagaraj, "Orientation Embedded High Order Shape Functions for the Exact Sequence Elements of All Shapes": https://arxiv.org/abs/1504.03025
87. Moxey, Amici, Kirby, "Efficient Matrix-Free High-Order Finite Element Evaluation for Simplicial Elements", SIAM J. Sci. Comput. 42, 2020 (Crossref record): https://api.crossref.org/works?query.bibliographic=Efficient+matrix-free+high-order+finite+element+evaluation+for+simplicial+elements&rows=2
88. Firedrake licence: https://raw.githubusercontent.com/firedrakeproject/firedrake/master/LICENSE
89. COMPUMAG, TEAM problems: https://www.compumag.org/wp/team/
90. LAMMPS repository: https://github.com/lammps/lammps
91. Geier, Schönherr, Pasquali, Krafczyk, "The cumulant lattice Boltzmann equation in three dimensions: Theory and validation", 2015 (Crossref record): https://api.crossref.org/works?query.bibliographic=The+cumulant+lattice+Boltzmann+equation+in+three+dimensions+Geier&rows=2
92. Hu et al., "A moving least squares material point method with displacement discontinuity and two-way rigid body coupling", ACM TOG 37, 2018 (Crossref record): https://api.crossref.org/works?query.bibliographic=A+moving+least+squares+material+point+method+with+displacement+discontinuity+and+two-way+rigid+body+coupling&rows=2
93. Marrone et al., "δ-SPH model for simulating violent impact flows", CMAME 200, 2011 (Crossref record): https://api.crossref.org/works?query.bibliographic=delta-SPH+model+for+simulating+violent+impact+flows+Marrone+Antuono+Colagrossi&rows=3
94. DualSPHysics repository: https://github.com/DualSPHysics/DualSPHysics
95. Paganini and Wechsung, "Fireshape: a shape optimization toolbox for Firedrake": https://arxiv.org/abs/2005.07264
96. Fireshape repository: https://github.com/fireshape/fireshape
97. STRUMPACK licence: https://raw.githubusercontent.com/pghysels/STRUMPACK/master/LICENSE
98. SuperLU_DIST licence: https://raw.githubusercontent.com/xiaoyeli/superlu_dist/master/License.txt
99. MUMPS download and licence page: https://mumps-solver.org/index.php?page=dwnld
100. libCEED licence: https://raw.githubusercontent.com/CEED/libCEED/main/LICENSE
101. SuiteSparse licence summary: https://raw.githubusercontent.com/DrTimothyAldenDavis/SuiteSparse/dev/LICENSE.txt
102. SLEPc licence: https://gitlab.com/slepc/slepc/-/raw/main/LICENSE.md
103. ARPACK-ng licence: https://raw.githubusercontent.com/opencollab/arpack-ng/master/COPYING
104. OpenModelica OSMC licence: https://github.com/OpenModelica/OpenModelica/blob/master/OSMC-License.txt
105. pyadjoint licence: https://raw.githubusercontent.com/dolfin-adjoint/pyadjoint/master/LICENSE
106. PhysicsNeMo licence: https://raw.githubusercontent.com/NVIDIA/physicsnemo/main/LICENSE.txt
107. FMPy licence: https://raw.githubusercontent.com/CATIA-Systems/FMPy/main/LICENSE.txt
108. Palace repository: https://github.com/awslabs/palace
109. Ansys LS-DYNA product page: https://ansys.synopsys.com/products/structures/ansys-ls-dyna
110. Turek and Hron, "Proposal for Numerical Benchmarking of Fluid-Structure Interaction between an Elastic Object and Laminar Incompressible Flow" (Crossref record): https://api.crossref.org/works?query.bibliographic=Proposal+for+numerical+benchmarking+of+fluid-structure+interaction+between+an+elastic+object+and+laminar+incompressible+flow&rows=3
111. Chaturantabut and Sorensen, "Nonlinear Model Reduction via Discrete Empirical Interpolation", SIAM J. Sci. Comput. 32(5), 2010 (Crossref record): https://api.crossref.org/works?query.bibliographic=Nonlinear+model+reduction+via+discrete+empirical+interpolation+Chaturantabut+Sorensen&rows=2
112. Huynh, Rozza, Sen, Patera, "A successive constraint linear optimization method for lower bounds of parametric coercivity and inf–sup stability constants", 2007 (Crossref record): https://api.crossref.org/works?query.bibliographic=A+successive+constraint+linear+optimization+method+for+lower+bounds+of+parametric+coercivity+and+inf-sup+stability+constants&rows=2
113. Song, Nelson, Staum, "Shapley Effects for Global Sensitivity Analysis: Theory and Computation", SIAM/ASA JUQ 4, 2016 (Crossref record): https://api.crossref.org/works?query.bibliographic=Shapley+effects+for+global+sensitivity+analysis+theory+and+computation&rows=2
114. Dvorkin and Bathe, "A continuum mechanics based four-node shell element for general non-linear analysis", Engineering Computations 1, 1984 (Crossref record): https://api.crossref.org/works?query.bibliographic=A+continuum+mechanics+based+four-node+shell+element+for+general+non-linear+analysis+Dvorkin+Bathe&rows=2
115. Svanberg, "The method of moving asymptotes", IJNME 24, 1987, and Zillober, "A globally convergent version of the method of moving asymptotes", 1993 (Crossref record): https://api.crossref.org/works?query.bibliographic=The+method+of+moving+asymptotes+a+new+method+for+structural+optimization+Svanberg&rows=3
116. Schäfer, Turek, Durst, Krause, Rannacher, "Benchmark Computations of Laminar Flow Around a Cylinder", 1996 (Crossref record): https://api.crossref.org/works?query.bibliographic=Schafer+Turek+benchmark+computations+laminar+flow+around+cylinder+1996&rows=3
117. Nguyen, Kerfriden, Claus, Bordas, "Nitsche's method for mixed dimensional analysis: conforming and non-conforming continuum-beam and continuum-plate coupling": https://arxiv.org/abs/1308.2910
118. SPHERIC, validation test 2, "3-D schematic dam break and evolution of the free surface": https://www.spheric-sph.org/tests/test-02

