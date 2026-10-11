# Flux physics engine (FLX)

Flux compiles weak forms written in Ingot through the shared kernel IR and solves them per region. Solids use matrix-free high-order FEM on an immersed adaptive octree; Reissner–Mindlin shells and Timoshenko or Vlasov beams cover regions that meet a local slenderness criterion; contact and boundary layers use fitted meshes. All share matrix-free p- and h-multigrid over deterministic AMG. Every result is a Field whose `ErrorBudget` states each bound's norm and guarantee, so a check decides only on bounds that hold for the quantity it reads.

## Scope and architecture

Flux is the machinery: Fields, the weak-form language, the kernel IR, discretizations, solvers, Networks, multibody dynamics, coupling, gradients, uncertainty, execution and display data. COV owns the physics models, materials, validity envelopes and out-of-reach list built on it. "Flux" is a working name, so `flux::` operation names and WIT packages freeze only after the phase 0 rename.

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

**Decision D-FLX-1:** Flux owns two engine-core crates below Anvil, `field` and `kernels`, and four physics crates. Optional FFI lives in `bridges/`, and `linalg` is shared with PLT. *Why:* Anvil operations consume Fields, and implicit tapes compile through the kernel IR (contract section 12). *Rejected:* the round 1 seven-crate split with Flux-prefixed engine crates. (revised in round 2)

About 80 operations, each `flux::name@version` with a determinism grade, are orchestrated by `std::sim`, `std::physics`, `std::opt` and `std::uq`. Wasm components call them through `crucible:ops/flux`, and every call is a recorded Op dependency.

| Group | Operations |
| --- | --- |
| Fields | `field_sample`, `field_transfer`, `field_project`, `field_recover`, `field_reduce`, `field_region`, `field_compare` |
| Forms and plans | `compile_form`, `plan`, `mark_reduction` |
| Discretization and solve | `discretize`, `cut_quadrature`, `assemble`, `setup_preconditioner`, `solve_linear`, `solve_nonlinear`, `solve_transient`, `solve_eigen`, `solve_harmonic`, `solve_explicit` |
| Lumped and multibody | `compile_network`, `solve_dae`, `solve_multibody`, `solve_rod` |
| Error and adaptivity | `estimate_error`, `estimate_goal`, `certify`, `mark`, `adapt` |
| Coupling | `couple`, `homogenize`, `localize`, `cosimulate`, `fmu_import`, `fmu_export`, `ssp_import`, `ssp_export` |
| Gradients and optimization | `tangent`, `adjoint`, `shape_gradient`, `filter_density`, `project_density`, `mma_step`, `lbfgs_step`, `sqp_step`, `cmaes_step` |
| Uncertainty | `sample_plan`, `pce_fit`, `sobol_indices`, `shapley_effects`, `mlmc_estimate`, `subset_simulation` |
| Reduced models and surrogates | `modal_basis`, `craig_bampton`, `pod_basis`, `hyperreduce`, `rom_build`, `rom_eval`, `surrogate_train`, `surrogate_calibrate`, `surrogate_eval` |
| General methods (D-COV-11) | `bvh_build`, `bvh_query`, `neighbor_list`, `segmented_reduce`, `random_stream`, `fmm_apply`, `hmatrix_build`, `hmatrix_apply`, `fft_solve`, `port_modes`, `fast_sweep` |
| Post-processing | `probe`, `reaction`, `isosurface`, `streamlines`, `display_evaluator`, `display_samples`, `report_data` |

[[DIAGRAM: Flux pipeline, left to right: Ingot form or Network → flux-forms (types, units, derivatives) → plan and mark_reduction (SolvePlan per region) → kernels (canonical CPU, Wasm SIMD, WGSL) → assemble and solve (Kiln Ops, CAS) → estimate ⇄ adapt → Fields with ErrorBudget and validity zones. Outputs: checks (Pass, Fail, Undecided), display evaluators, Field-driven Anvil operations. A dashed adjoint arrow runs right to left under the solve boxes.]]

### Rust API

Kiln calls every operation through `OpImpl` and `OpCx` in `base`, plus `Differentiable` where derivatives exist; Flux fills `base`'s `ErrorBound<Q>`, `ErrorBudget<Q>` and `CheckOutcome`. Every discretization method implements a `Discretization` trait: discretize, estimate, produce Fields.

```rust
/// A quantity over a domain: Field<Body, Stress>, Field<(Body, Time), Temperature>.
pub struct Field<D: Domain, V: Value> {
    header: Arc<FieldHeader>, // GeometryId + entity numbers, unit, budget, zones, provenance
    repr: Repr,               // the eight representations
    _kind: PhantomData<(D, V)>,
}

pub trait Sampler<D: Domain, V: Value> {
    /// Values with a pointwise ErrorBudget and, where known, a gradient bound.
    fn sample(&self, cx: &mut OpCx<'_>, at: &[Location], accuracy: Accuracy)
        -> Result<Vec<Sampled<V>>, FieldError>;
}

/// Deterministic failures are values; cancellation, budget, device loss and
/// floating-point environment faults are Aborts that Kiln raises.
#[non_exhaustive]
pub enum SolveFailure {
    LinearDiverged { iterations: u32, residual_history: Vec<f64> },
    NonlinearDiverged { iteration: u32, residual_history: Vec<f64>, last_converged: Option<FieldSet> },
    Bifurcation { load: f64, modes: FieldSet },          // D-FLX-25
    SingularOperator { null_space_hint: NullSpaceHint },  // "no rigid-body constraint on Instance 3"
    OutsideEnvelope { parameter: ParamId, range: (f64, f64) },
}
```

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Operation registration | `OpImpl` with grade, effective-fidelity map and cost model; `Differentiable` where derivatives exist | Missing grade or cost model fails the registry check | FLX-O-OPT-1 | 0 |
| Physics packages in Ingot | User-namespace forms get std's kernels, derivatives, GPU paths and estimators | `FormError` at compile time | FLX-O-ARCH-1 | 1 |
| Constitutive Wasm components | `crucible:material/constitutive`, batched, with consistent tangents | `TangentInconsistent`; cannot register for Newton | FLX-O-FORM-3 | 2 |
| Solver Wasm components | `crucible:physics/solver`, Fields in and out, may call `crucible:ops/flux` | Determinizer rejection | FLX-O-ARCH-1 | 2 |
| Flux operations from Wasm | `crucible:ops/flux`, GPU-backed ones included; recorded dependencies | `OpVersionRetired` with an upgrade Proposal | FLX-O-ARCH-2 | 2 |
| External Op solvers | GPL references (Meep, Elmer, OpenFOAM, LAMMPS) in pinned images on untrusted-evaluation workers; host class or `Unverified` | Host failure is a `Failure`; worker loss an Abort | FLX-O-ARCH-3 | 3 |

## Fields

### Domains and values

`Field<D, V>` lives in the `field` crate and follows contract section 5. Domains are entity sets (`Body`, `Regions`, `Faces`, `Edges`, `Vertices`, `Points`, `Instances`, `Ports`), quantity-named parameter domains (`Time`, `Frequency`, `Temperature`), index sets (`Mode`, `LoadCase`, `Sample`, `Variant`) and tuples of these. Values are scalars, vectors, tensors with declared symmetries, complex values, `Transform`s and enums such as `ValidityZone` and `ReductionKind`. Each value type declares its rigid-transform rule (vectors rotate, tensors as R·T·Rᵀ, pseudo-vectors take the determinant's sign), so Instance placement needs no user code.

Canonical storage is SI `f64`; `f32` copies exist only on GPUs and for display. A Field's domain is the Body's `GeometryId` plus canonical entity numbers, never a pointer, name or `EntityId`. Field values therefore survive renaming and geometry-free refactors (contract section 7.1). A `Query` resolves to canonical numbers through the Body's name section; a Field used on other geometry fails with `DomainMismatch`, suggesting `field_transfer`.

**Decision D-FLX-2:** Time series, sweeps, mode sets, load cases, ensembles and parametric results are Fields over product domains such as `Field<(Body, Time), Temperature>`, and slicing and reductions return Fields. *Why:* libraries then exchange only Bodies, Fields and plain values (principle 3). *Rejected:* separate container types; a third type parameter for axes, replaced by product domains (ruling FLX-2). (revised in round 2)

### Representations

| Representation | Holds | Sampling error | Typical producer |
| --- | --- | --- | --- |
| `Analytic` | Kernel-IR expression | Floating point only | Loads, boundary data, lazy arithmetic |
| `Discrete` | Function-space coefficients (Lagrange, edge and face moments, DG modes, NURBS) | Discretization part carried separately | FEM, IGA, DG, finite volume |
| `QuadraturePoint` | Values at quadrature points | Recovery error | Plastic state, element densities |
| `SparseGrid` | Adaptive spatial block grid | Local second differences | Lattice Boltzmann, FDTD, CT data |
| `PerEntity` | One value per entity | None | Contact status, Part-level results |
| `PointCloud` | Points with a reconstruction rule | Leave-one-out estimate | Particles, sensors |
| `Reduced` | Basis Field times coefficient model | Certified or residual bound | Modal, POD, reduced basis |
| `Surrogate` | Trained model, calibration set, envelope | Conformal bound, `scope: Marginal` | Neural operators, Gaussian processes |

**Decision D-FLX-3:** Generalize "nodal values" to `Discrete` and "per-face constants" to `PerEntity`, and add `PointCloud`, `Reduced` and `Surrogate`. *Why:* nodal values cannot hold Nédélec, DG or NURBS coefficients, and particle, reduced and learned results must reach checks. *Rejected:* separate result types per method.

### Sampling and operations

`Sampler::sample` takes locations (Part coordinates, `(entity number, u, v)` on the true surface, reference-cell or parameter coordinates) and a requested accuracy. It returns values with a pointwise budget (interpolation, discretization and algebraic parts) and, where known, a gradient bound that Anvil uses for extraction. Point location uses Anvil's certified classification, with ties broken by canonical cell number. Outside the domain it fails with `OutsideDomain { distance }`; extrapolation happens only on request and is `NotQuantified { reason: Extrapolated }`.

| Operation | Ingot | Error behavior |
| --- | --- | --- |
| Arithmetic | `a + b`, `sqrt(a)` | Lazy `Analytic`; first-order propagation in one norm |
| Differential operators | `grad`, `div`, `curl`, `sym_grad` | Basis derivatives, or `NeedsRecovery` |
| Restriction and traces | `f.on(p.faces(q))` | Full, normal or tangential trace; none added |
| Integration | `f.integrate(dx(region))` | Quadrature part added |
| Reductions | `f.max(over: R)`, `f.at(x)`, `f.mean(over: R)` | Regularized goals (D-FLX-23) from `estimate_goal` |
| Projection and transfer | `f.project(to: V)`, `f.transfer(to: body)` | Conservative or consistent; transfer part estimated |
| Region extraction | `f.region(where: f > 250MPa)` | Implicit Body with a bound from Field and gradient |
| Comparison | `compare(a, b)` | Differences inside combined bounds not significant |

Bernstein enclosures of a discrete Field's extremum feed a reduction's regularization part and are never check values.

### Fields that drive geometry

Anvil samples Fields (sizing, metric, displacement, thickness, radius, density, orientation) at a required accuracy and adds the sampled error to the Body's bounds. `anvil::implicit_from_field` needs a continuous Field with a gradient bound, so topology optimization supplies `geometry_density`. A Field that cannot meet the accuracy fails with `InsufficientAccuracy { achieved, required, producer }`.

**Decision D-FLX-5:** A consumer never changes its producer. Adaptivity goals are explicit study inputs (`goals: [...]`), and a reduction a check reads is estimated by a separate `flux::estimate_goal` node over the frozen solution, which never re-solves. *Why:* adding a check must never change a design (D-ING-12). *Rejected:* deriving goals from the checks that read a result, which reverses the graph (R3-10); refinement on demand. (revised in round 2)

An undecidable check returns `Undecided { needed }`, and the language service offers an edit adding its functional to the goals.

### Storage

A stored Field is a header plus 1 MiB partition-aligned chunks, byte-shuffled and zstd-compressed, hashed over canonical little-endian `f64` bytes. Outputs are canonical at the operation boundary (−0.0 stored as +0.0), so CAS reloads equal in-memory values.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Field types and product domains | `Field<D, V>` keyed by `GeometryId` and canonical entity numbers | `DomainMismatch` with a `field_transfer` fix | FLX-O-FIELD-1 | 0 |
| Sampling | `Sampler` with pointwise budget and gradient bound | `OutsideDomain`, `InsufficientAccuracy` | FLX-O-FIELD-1 | 0 (`Analytic`, `Discrete`), 1 |
| Transfer and projection | Conservative for fluxes, consistent for states | `NotSameInterface` from Anvil | FLX-O-FIELD-2 | 1 |
| Extremum enclosure and region extraction | Bernstein subdivision; Implicit Bodies from scalar Fields | Work limit with the achieved gap; `NotContinuous` | FLX-O-FIELD-3 | 1 |
| Geometry-driving Fields | Sizing, metric, displacement, thickness, radius, density, orientation | `InsufficientAccuracy` naming the producer | FLX-O-FIELD-4 | 1 (density, sizing), 2 |
| Storage and canonical form | Chunked CAS arrays; canonical bytes | None | FLX-O-FIELD-5 | 0 |
| Label invariance | Field values unchanged under renaming | Any difference fails the rename oracle | FLX-O-FIELD-6 | 1 |

## Error budgets, goals and checks

### Budgets and guarantees

Every result Field and every estimated reduction carries an `ErrorBudget<Q>` whose parts are `Quantified(ErrorBound<Q>)` or `NotQuantified { reason }` and compose as contract section 5 states.

| Source | Estimator | Norm | Kind |
| --- | --- | --- | --- |
| Discretization, scalar diffusion on fitted simplices | Equilibrated flux, plus oscillation and geometry terms | Energy | `Guaranteed` [Smears and Vohralík] |
| Discretization, linear elasticity | Equilibrated stress; mixed u–p reconstruction near incompressibility | Energy | `Guaranteed` only with strongly symmetric stress elements and polynomial data, else `Estimated` |
| Discretization on hanging nodes or cut cells | Same constructions | Energy | `Estimated` until proven (open question 3) |
| Bounded linear goals: regional averages over a stated volume, reaction resultants, compliance, mean temperature | Primal–dual product of two energy bounds, plus algebraic and oscillation terms | Goal | `Guaranteed` when both factors are |
| Regularized peaks and point values | Dual-weighted residual (DWR) | Goal | `Estimated { calibration }` |
| `Interactive` indicators | Element residuals | Energy or goal | `Estimated { calibration }`, else `Indicator` |
| Algebraic | Equilibrated algebraic residual; solves stop below 10% of the discretization part | As discretization | `Estimated` |
| Temporal | Adjoint-weighted residual in time; summed local truncation errors | Goal; energy | `Estimated`; `Indicator` |
| Quadrature, geometry | Rule-order comparison; Anvil face bounds through adjoint shape sensitivity | Goal or energy | `Estimated` |
| Floating point | A priori rounding bound γₖ of the canonical residual and estimator evaluation, k the reduction-tree depth | As covered part | `Guaranteed` |
| Statistical, reduction, surrogate, input and tolerance | Confidence intervals; reduced-model, conformal and `std::uq` bounds | Goal | Per method |
| Model form | COV records; dimensional-reduction estimate (D-FLX-26) | Goal | `NotQuantified` unless estimated |

**Decision D-FLX-4:** Flux reports every error through the contract's `ErrorBound<Q>` and `ErrorBudget<Q>`, one bound per source in its own norm, never converted. A bound is `Guaranteed` only when a proof for that method covers that norm, and the estimator's metadata names the theorem. *Why:* in 3D, H¹ does not embed in L∞, so energy bounds cannot certify peak stresses (R1-01). *Rejected:* totals across norms; the round 1 `Unknown` kind, replaced by `NotQuantified { reason }`. (revised in round 2)

Guaranteed goal bounds rest on |J(u) − J(u_h)| ≤ ‖u − u_h‖_E · ‖z − z_h‖_E for a bounded linear functional J with adjoint z. Elasticity bounds need a stress that is equilibrated and symmetric, since weak symmetry leaves an unknown Korn constant [unverified: Arnold–Winther or Hu–Zhang choice]; effectivity oracles run at ν = 0.49 and 0.4999.

### Regularized goals and singular points

**Decision D-FLX-23:** Peak and pointwise quantities are regularized goals. `f.max(over: R, smooth: ρ)` is the maximum over R of the Gaussian local average of radius ρ; `f.at(x, smooth: ρ)` is the local average at x; `pnorm(f, p, over: R)` serves optimization. The regularization part is the gap to the enclosed raw maximum of the discrete Field. *Why:* a raw maximum is not differentiable, so DWR cannot estimate it, and it diverges at singular points (contract section 7.1). *Rejected:* raw maxima as goals; p-norms for checks, which underestimate a sharp peak in a large region by tens of percent.

The default ρ is 1% of the region's diameter or a critical distance the check names; CCR-FLX-8 asks for a `regularization` source. `flux::estimate_goal` solves the adjoint one degree higher on the frozen discretization, weights local residuals, applies the calibration factor, and reports the largest estimate among near-maximal locations.

Flux flags singular sets from the Body and the study's conditions: re-entrant edges and corners; edges where the boundary-condition type changes (a clamped face meeting a free face); material interfaces meeting the boundary; contact boundaries; edges of fixed or loaded patches; point and line measures. Estimates that fail to decrease under refinement flag more. A peak or point quantity within the stated exclusion distance of a flagged set is `Undecided { SingularPoint }`, hence the canonical check's `p.away_from(clamp, 2 * thickness)`.

### Calibrated estimates

**Decision D-FLX-24:** Every `Estimated` bound is reported already multiplied by its calibration factor η99, the 99th-percentile underestimate of that estimator on its problem class, and labelled `Estimated { calibration }`. Tables live in `std::sim::calibration`, pinned in `ingot.lock` and in every key that reads them; a class without an entry reports `Indicator`. *Why:* ING's single decision rule then works unchanged at `Interactive` and `SignOff` (R1-07, R3-07), and bounds never depend on the machine. *Rejected:* a three-times margin at the consumer; machine-local safety factors raised by audits, which are hidden state (R1-14).

An entry changes only through a reviewed Proposal with at least 300 held-out samples and zero undershoots (one-sided 95% exceedance bound below 1%); local audits only record samples. FLX keeps the corpus, COV maps model classes, and MEC decides which checks need which classes.

### Fidelities

| Aspect | `Preview` | `Interactive` | `SignOff` |
| --- | --- | --- | --- |
| Methods | Reduced model, surrogate or coarsest level | Shifted boundary at p = 2, one adaptive pass; shells and beams per region | CutFEM, fitted or reduced per region, hp-adaptive to tolerance |
| Class | Any | `Gpu(…)` in `f32` or `CpuIsa`; explicit warm start | `CpuCanonical`, or GPU certified on CPU (D-FLX-17) |
| Bounds | `Indicator` | Calibrated `Estimated` | `Guaranteed` where proven, else calibrated `Estimated` |
| Checks | Always `Undecided` | ING's rule | ING's rule; `Pass { conditional_on }` for unquantified parts |
| Cache | Never shared | Shared | Shared once two trusted builders agree |

**Decision D-FLX-15:** Flux produces budgets; ING decides checks by one rule (disjoint enclosures decide, subject to declared evidence), returning `base`'s `CheckOutcome`. Flux adds no margin rule. *Why:* four tabs had four rules (R3-07). *Rejected:* binary checks on point values; the round 1 three-times margin at `Interactive`. (revised in round 2)

Nodes record the fidelity of the bounds they observed, so a branch on `Undecided` below its ceiling waits as `Pending` (R3-14).

### Verification, validity and agreement

**Decision D-FLX-34:** Methods without an a posteriori estimator (finite-volume RANS and LES, lattice Boltzmann, FDTD, particles) report `Indicator` discretization bounds unless `std::sim::solution_verification` runs. It refines three levels, computes the observed order and applies Roache's grid convergence index, with a safety factor of 1.25 when the observed order is within 0.5 of the formal order and 3 otherwise. *Why:* code verification does not verify an application result, and `Indicator` bounds never support `SignOff` (R1-28). *Rejected:* single-grid trust; extrapolation without a safety factor.

Flux evaluates COV's regime functions into a `Field<Body, ValidityZone>` and `Flag` or `Refuse` checks; it never switches models, only suggests escalation.

Classes A and B agree when |q_A − q_B| ≤ E_A + E_B for every checked quantity, E being the budget total in q's norm plus a floor scaled by the Field norm (PLT's rule too). Bifurcating problems compare branch-invariant quantities and chaotic ones declared statistics (principle 4).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Error budgets | `ErrorBudget<Q>` on every result and estimated reduction | Unquantified parts named | FLX-O-ERR-1 | 1 |
| Guaranteed energy bounds | Equilibrated flux on fitted simplices; symmetric stress for elasticity | `Estimated` where no theorem applies | FLX-O-ERR-1 | 2 (diffusion), 3 (elasticity) |
| Guaranteed linear goals | Primal–dual product | `NotQuantified` if a factor is not guaranteed | FLX-O-ERR-2 | 2 |
| Regularized goals | `max(over:, smooth:)`, `at(x, smooth:)`, `pnorm`, via `estimate_goal` | `Undecided { needed }` with an "add to goals" fix | FLX-O-ERR-3 | 1 |
| Singular sets | Geometric and numerical detection | `Undecided { SingularPoint }` | FLX-O-ERR-4 | 1 |
| Calibration | η99 tables in `std::sim::calibration` | `Indicator` without an entry | FLX-O-ERR-5 | 1 |
| Temporal goal estimates | Adjoint-weighted residual in time | Summed local estimates `Indicator` | FLX-O-ERR-6 | 2 |
| `Preview` fidelity | Reduced, surrogate or coarsest solves | Never decides a check | FLX-O-ERR-7 | 1 |
| Solution verification | Three-level GCI | `NotAsymptotic { ratio }` keeps `Indicator` | FLX-O-ERR-8 | 3 |
| Validity zones | Zone Field and `Flag` or `Refuse` checks | `Refuse` gives `Error(Failure)` | FLX-O-ERR-9 | 1 |
| Cross-class agreement | \|q_A − q_B\| ≤ E_A + E_B | Ratio above 1 opens a determinism incident | FLX-O-ERR-10 | 1 |

## The weak-form language

Physics is written as weak forms in Ingot with UFL's semantics (contract section 6 shows elasticity). Forms are staged `Expr` values (D-ING-9), so units, linearity and conformity are checked before anything runs; the plan picks the method. `std::sim` holds the building blocks and `std::physics` the models, in the language anyone can use (principle 1).

### Spaces, elements and measures

| Space | Constructor | Elements | Phase |
| --- | --- | --- | --- |
| H¹ | `H1(domain, degree: p, shape: …)` | Lagrange of any order, serendipity, hierarchical Legendre | 0 (p ≤ 4), 1 |
| H(curl), H(div) | `HCurl(domain, degree: p, kind: 1 \| 2)`, `HDiv(domain, degree: p, kind: rt \| bdm)` | Nédélec, Raviart–Thomas, Brezzi–Douglas–Marini | 1 (H(div) in estimators), 3 |
| L², trace, real | `L2`, `Trace`, `Real(n)` | Discontinuous bases, facet spaces, global multipliers | 1, 3 (trace) |
| Spline | `Spline(body, degree: p, continuity: k, kind: nurbs \| thb)` | B-rep NURBS, truncated hierarchical B-splines | 2 |
| Manifold | Spaces on sheet and wire Bodies with director or section unknowns | Shells, beams, rods | 1 (wires), 2 (sheets) |
| Parameter domain | `Interval(Radius, n)`, `Sphere(directions: n)`, products `V ⊗ W` | Batched local problems (D-FLX-38) | 4 |
| Mixed, restricted | `(V1, V2)`, `V.restrict(region)` | Taylor–Hood, MINI, (H(div), L²) | 1 |

One Rust element library defines every element (equispaced, Gauss–Lobatto–Legendre or warped points; Legendre or Bernstein bases), handling H(curl) and H(div) orientation in the restriction so meshes need no global orientation. Cell shapes run from interval to pyramid [unverified: pyramid basis]; fitted curved boundaries use p ≤ 8 with geometry order p.

| Measure | Meaning |
| --- | --- |
| `dx(region?)` | Volume, or a sheet or wire domain |
| `ds(faces?)` | The true boundary or faces selected by a `Query` |
| `dS(region?)` | Interior facets, for DG jumps |
| `dE(edges)`, `dP(points)` | Edges and points of the true geometry |
| `dI(interface)` | Interfaces between Instances, or between solids, shells and beams |
| `dξ(domain)` | A parameter domain such as particle radius or direction |

**Decision D-FLX-6:** Measures refer to true-geometry entities selected by `Query`; solves receive them as canonical entity numbers of the Body's `GeometryId`, never as mesh entities or names. *Why:* one form runs fitted, immersed or reduced, conditions survive remeshing, and renaming never changes a result. *Rejected:* mesh-tagged boundaries as in FEniCS and MFEM, which break on every geometry change. (revised in round 2)

### Operators, problem kinds and checks

Operators cover algebra (`inner`, `dot`, `cross`, `tr`, `det`, `inv`, `dev`, `sym`, index notation), calculus (`grad`, `div`, `curl`, `sym_grad`), facet terms (`jump`, `avg`, `n`, `h`), `dt`, pointwise eigen-decomposition, `select(cond, a, b)`, `im` and `.absolute()`. Non-smooth functions carry declared generalized derivatives.

| Kind | Ingot | What Flux does |
| --- | --- | --- |
| Linear, nonlinear, energy | `a == L`; `F == 0`; `minimize(Pi, u)` | Arity check; symbolic Jacobian or Hessian |
| Mixed | `trial((Velocity, Pressure), p, element: taylor_hood(2))` | Keeps blocks for field-split preconditioners |
| Time-dependent | `dt(u)` terms; `implicit(…)`, `explicit(…)` marks | Semi-discrete system; plan picks the scheme |
| Harmonic, eigen, constrained | `solve_harmonic`, `modes`, `fixed:`, `contact(...)` | Complex forms; strong, Nitsche or multiplier constraints |
| Continuation | `continue_in(load, to: 2kN)` | Arc length with bifurcation detection (D-FLX-25) |
| Goals | `study(..., goals: [...])` | Goal-oriented adaptivity (D-FLX-5) |

```
// Transient heat with an implicit-explicit radiative boundary
let heat = rho * c_p * dt(T) * w * dx(housing) + inner(k * grad(T), grad(w)) * dx(housing)
         + explicit(emissivity * stefan_boltzmann * (pow(T.absolute(), 4) - pow(t_amb.absolute(), 4)))
             * w * ds(housing.faces(role: outer))
        == q_chip * w * ds(housing.face(role: chip_pad))
let hist = solve(heat, initial: 20degC, over: 0s..600s)       // Field<(Part, Time), Temperature>
```

| Check | Rule | Error and fix |
| --- | --- | --- |
| Units | Every term of a residual row has one dimension | `FormError::UnitMismatch { term, expected, found }`, naming the likely missing factor |
| Arity | Bilinear forms are linear in trial and test | `NotLinear { term }`, suggesting `F == 0` |
| Conformity | `curl` needs H(curl) or H¹, `div` H(div) or H¹, jumps `dS` | `Conformity`, suggesting the conforming space |
| Inf-sup and quadrature hints | Unstable pairs such as P1–P1 Stokes; degree above 30 | Warning naming a stable pair or the chosen degree |

### Compilation and `local_solve`

1. **Lowering** to index notation, erasing units after checking.
2. **Differentiation:** forward symbolic Gateaux derivatives on the hash-consed DAG; `adjoint` swaps arguments, `action` substitutes a coefficient.
3. **Pullback:** identity for H¹ and L², covariant Piola for H(curl), contravariant Piola for H(div).
4. **Degree estimation:** non-polynomial integrands get 2p + 2 unless stated, with an error estimate from one order higher.
5. **Split** into libCEED's `Eᵀ Bᵀ D B E`: element restriction, basis evaluation at quadrature points, pointwise kernel.

**Decision D-FLX-7:** Write the form compiler natively in Rust, following TSFC's structure-preserving design (lower to tensor algebra, then schedule) and libCEED's `Eᵀ Bᵀ D B E` split. *Why:* it runs inside Kiln on every OS and in browsers, emits the kernel IR and differentiates at the form level; no existing compiler does all three in Rust. *Rejected:* UFL with FFCx or TSFC through Python, which cannot run in the browser sandbox and emits C.

Constitutive code never differentiates through loops (contract section 6). A local Newton solve is `local_solve(residual, x0)`, whose derivative at the converged point is dx/dp = −(∂R/∂x)⁻¹ ∂R/∂p by the implicit function theorem. Its tolerance is tied to the global Newton tolerance, so return mapping, viscoelastic and creep updates keep global quadratic convergence. Constitutive models are Ingot functions compiled into the same kernels, or `crucible:material/constitutive` Wasm components that supply consistent tangents (contract section 7.4).

`solve` returns a record of Fields: each unknown by binding name plus derived outputs declared by the form's functions (`sigma` declares `stress` and `von_mises`), which inherit the budget plus a recovery part.

**Decision D-FLX-38:** Nested and phase-space models are forms over product spaces with a parameter measure `dξ`: particle diffusion in battery electrodes, FE² micro problems, discrete-ordinates radiation, population balances. They compile into batched local problems, one per macro quadrature point. *Why:* COV's DFN batteries and radiation models then get form-level derivatives and GPU kernels (R1-24). *Rejected:* special-purpose solvers that lose derivatives and estimators.

A DFN particle concentration is a `Field<(Body, ParticleRadius), Concentration>`; ING owns the syntax.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| H¹, L², real, mixed and restricted spaces | Elements of any order on every cell shape | `FormError::Conformity` | FLX-O-DISC-1 | 0 (H¹, p ≤ 4), 1 |
| H(curl), H(div), trace spaces | Nédélec, Raviart–Thomas, BDM, facet spaces | As above | FLX-O-DISC-1 | 3 |
| Spline and manifold spaces | NURBS and THB spaces; sheet and wire spaces | `NotParameterizable` from Anvil | FLX-O-DISC-6 | 1 (wires), 2 |
| Parameter-domain spaces | `Interval`, `Sphere`, products, `dξ` | `FormError::Conformity` | FLX-O-FORM-5 | 4 |
| Static form checks | Units, arity, conformity, inf-sup hints, quadrature | Typed `FormError` with a fix | FLX-O-FORM-1 | 0 |
| Symbolic derivatives | Gateaux derivative, `adjoint`, `action` for every operator | `NotDifferentiable { op }` | FLX-O-FORM-2 | 0 |
| `local_solve` | Implicit-function derivative at convergence | `LocalSolveDiverged { point }` | FLX-O-FORM-3 | 1 |
| UFL coverage | FEniCS and Firedrake demos expressible | Unsupported construct named | FLX-O-FORM-4 | 1 |

## Kernels, back ends and determinism

The kernel IR in `kernels` is the source of every compute kernel that affects results (contract section 7.5); FLX owns it with three compiler engineers from month 0. IR v0 freezes at month 6 with element kernels using sum factorization, pointwise constitutive functions with forward derivatives, implicit tapes and `local_solve`. Network residuals join in phase 2 and Verilog-A device models in phase 3; constraint residuals use the IR's Rust embedding until MEC needs a construct.

Assembly is full (sparse matrices, for p ≤ 2 with direct solvers and AMG levels), element-level (GPUs at p ≤ 2, contact, cut cells), partial (quadrature-point linearizations with sum factorization, the default for p ≥ 2, O(p) work per DOF) or matrix-free. Throughput is typically best at degrees three to six [deal.II]. Simplices use basis tables up to degree 3 and collapsed coordinates above [unverified]; cut cells evaluate bases at their quadrature points.

| Back end | Targets | Use | Phase |
| --- | --- | --- | --- |
| Ahead-of-time Rust, canonical SIMD | Native CPUs from x86-64-v2 and ARMv8 | std forms in `CpuCanonical` | 0 |
| Wasm SIMD128, generated at run time | Wasmtime; browser engines | User forms; all forms in browsers | 0 |
| WGSL through wgpu | Vulkan, Metal, DX12, WebGPU | `Interactive` elasticity, implicit preview | 1 |
| wgpu Vulkan with `SHADER_F64` | Linux servers and workstations | `f64` GPU solves certified on the CPU | 3 |
| CUDA or HIP (CubeCL or another) | NVIDIA and AMD servers | Reconsidered at the phase 4 gate | 4 |

**Decision D-FLX-9:** On CPUs, user forms compile to Wasm SIMD128 modules and std forms ahead of time; user forms target at most 2× the ahead-of-time time on AVX2 and 4× on AVX-512. *Why:* one sandboxed path with canonical bits everywhere. *Rejected:* a native JIT; shipping LLVM. (revised in round 2)

**Decision D-FLX-10:** GPU kernels come from the kernel IR through WGSL on wgpu, for `Interactive` paths in phase 1 and `f64` server paths on Vulkan with `SHADER_F64` in phase 3; a CUDA or HIP back end is reconsidered at the phase 4 gate. *Why:* WGSL has no `f64`, wgpu offers `SHADER_F64` only on Vulkan, and CubeCL is alpha with breaking changes between minor versions. *Rejected:* CubeCL in phase 1; a hand-written CUDA path before measured need. (revised in round 2)

**Decision D-FLX-8:** On CPU back ends the kernel IR fixes every floating-point operation and reduction order, with the 512-bit canonical lane order and no FMA in the canonical class. `CpuIsa` variants with FMA serve `Preview` and `Interactive` for kernel families that lose more than 1.3× without it. WGSL kernels never claim bit-identity with CPU kernels. *Why:* x86-64-v2 and wasm32 lack FMA, and WGSL may reassociate, fuse and flush subnormals (R1-09, R6-17). *Rejected:* one no-FMA rule on GPUs too; FMA in the canonical class. (revised in round 2)

Phase 0 measures the no-FMA penalty per degree and ISA for sum factorization, dense LU, NURBS evaluation and implicit tapes. Throughput targets are contract section 13.3's CEED rows, and the bake-off suite adds immersed elasticity kernels, which BP1 to BP6 do not exercise.

**Decision D-FLX-11:** `Portable` code computes elementary functions only with PLT's correctly rounded `detmath`; GPU kernels use fixed-sequence approximations with documented ulp bounds, never vendor built-ins. *Why:* platform and vendor libraries differ, and correct rounding on GPUs needs precision WGSL cannot guarantee (R1-43). *Rejected:* a separate Flux math library; platform `libm`. (revised in round 2)

### Determinism

Contract section 7.3 and PLT own the mechanisms. Flux adds six rules:

1. DOFs, cells and partitions are numbered in canonical geometric order (octree Morton order, canonical entity numbers), never by name.
2. Work splits into virtual partitions fixed by problem size, combined in partition order.
3. Assembly gathers each DOF's element contributions in a fixed order; no back end uses floating-point atomics.
4. Node-local reductions use `det_sum` and `det_reduce`, and `exact_sum` is used only across ranks; the target is a CG overhead of at most 1.05× per iteration on one node.
5. The floating-point control state is checked at operation start and end; a change at the end aborts the operation, which reruns.
6. GPU paths use integer-limb reductions, non-finite detection on the CPU after readback, and PLT's known-answer test per pipeline.

**Decision D-FLX-18:** GPU reductions use integer-only exact accumulation: bins of 32-bit limbs with explicit carries, combined in fixed order. *Why:* wgpu offers 64-bit integer atomic add only on Vulkan and DX12 and float atomics only on some devices, while 32-bit integer arithmetic is exact everywhere. *Rejected:* floating-point atomics; vendor reduction libraries.

**Decision D-FLX-19:** Canonical CPU solves, estimators and `flux::certify` are `Portable` in `CpuCanonical`. GPU solves are `ClassExact` in `Gpu(GpuClass)`, and a `SignOff` check on one rests on the pinned Field plus `certify` (D-FLX-17). *Why:* release gates need canonical outcomes, while GPUs pay off at `Interactive` and as solvers the CPU certifies. *Rejected:* the round 1 Flux class names, superseded by PLT's enum. (revised in round 2)

Behavior versioning follows contract section 4 and the ANV and KLN policies: any output-bit change is a new version, including changed `flux::plan` defaults (D-FLX-20).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Kernel IR v0 | Element, constitutive and implicit-tape constructs; forward derivatives; `local_solve` | IR validation error naming the construct | FLX-O-KER-1 | 0 |
| Canonical CPU back end | Ahead-of-time Rust with canonical SIMD; `Portable` | None at run time | FLX-O-KER-3 | 0 |
| Wasm SIMD128 back end | User forms on every CPU; all forms in browsers | Determinizer rejection | FLX-O-KER-6 | 0 |
| WGSL back end | `Interactive` elasticity and implicit preview; `ClassExact` | Failed known-answer test falls back to the CPU, reported in `RanOn` | FLX-O-KER-4 | 1 |
| `f64` GPU server path | Vulkan `SHADER_F64`, certified on the CPU | Missing feature: CPU path, reported | FLX-O-KER-4 | 3 |
| FMA variants | `CpuIsa` kernels for families losing more than 1.3× | Never used at `SignOff` | FLX-O-KER-2 | 1 |
| Floating-point environment guard | Checked at operation start and end | Abort and rerun | FLX-O-KER-5 | 0 |
| Throughput | Contract section 13.3 targets plus immersed elasticity kernels | Regression blocks beta promotion | FLX-O-KER-1 | 0 |

## Solve plans and per-region discretization

`flux::plan` maps a problem (forms, geometry, materials, conditions, goals), fidelity, class and budget to a `SolvePlan` recording per-region models, spaces, quadrature, assembly, solvers, precision, adaptivity and estimators. Plans depend only on their inputs, never on hardware, and can be printed, edited and pinned as Ingot.

```
let plan = std::sim::plan(elasticity, fidelity: SignOff, goals: [stress_goal], tol: 2%)
plan.explain()   // each choice with the alternatives considered
let result = solve(elasticity, fixed: clamp, plan: plan.with(region: p.regions(role: web), model: Solid))
```

**Decision D-FLX-20:** Pin the resolved plan, not just the solver version: a versioned `flux::plan` resolves every default, and the resolved plan enters the cache key. *Why:* most result drift comes from changed defaults, not changed algorithms. *Rejected:* versioning only solver kernels.

### Per-region models

`flux::mark_reduction` returns a `Field<Body, ReductionKind>` (`Solid`, `Shell`, `Beam`, `Lattice`). L_local is the smallest of the span between supports, the radius of curvature and the distance to the nearest load or feature, computed from the study's conditions and Anvil's thickness, curvature and distance queries.

| Region | Criterion | Model | Geometry from Anvil |
| --- | --- | --- | --- |
| Thin wall | t / L_local ≤ 0.2 | Reissner–Mindlin shell; laminates by ABD matrices | `anvil::mid_surface` sheet, thickness Field, junction curves |
| Very thin smooth wall | t / L_local ≤ 0.05 on a NURBS mid-surface | Kirchhoff–Love isogeometric shell | Same, NURBS faces |
| Member or strut | Prismatic over L_local, section size d / L_local ≤ 0.2 | Timoshenko beam; Vlasov warping for open thin-walled sections | `anvil::member_axes` axes, joints, sections |
| Lattice | Strut graph from `anvil::lattice` | Beam-lattice model with joint corrections, or homogenized continuum | Strut graph |
| Everything else | Fails the criteria above | Solid on the immersed octree, or fitted where required | The Body |

Junction zones stay solid for two wall thicknesses [unverified: transition length]; source may override any region.

**Decision D-FLX-12:** Discretization is chosen per region (contract section 7.1): shells and beams where the local slenderness criterion holds, the immersed octree for solids, fitted meshes for contact and boundary layers, beam lattices and homogenization for lattices, isogeometric shells for very thin NURBS walls. *Why:* a volumetric octree on golden products 2, 4, 5 and 8 needs 10⁶ to 10⁸ DOFs where reduced models need 10⁴ to 10⁵ (R1-02). *Rejected:* immersed solids everywhere, with shells only below 5% of the bounding size. (revised in round 2)

Reduced regions couple to solids and each other through `dI` interfaces. Rigid couplings tie a shell edge or beam end to a solid face; Nitsche couplings enforce displacement and rotation continuity weakly, with a penalty from the trace inequality. Rigid is the `Interactive` default and Nitsche the `SignOff` default, because rigid coupling stiffens the junction.

**Decision D-FLX-26:** Dimensional-reduction error is a model-form part, estimated by re-solving 3D patches around each goal region with boundary data from the reduced model, and otherwise `NotQuantified`, which makes a `Pass` there conditional (contract section 5). *Why:* shell and beam theories carry modelling error that refinement never removes. *Rejected:* treating reduced models as exact; solids everywhere, infeasible on thin products.

| Situation | Plan default |
| --- | --- |
| Compact solids, heat, electrostatics | Immersed octree: shifted boundary at `Interactive`, CutFEM at `SignOff` |
| Thin walls, members, struts, lattices | Shells, beams and beam lattices per `mark_reduction` |
| Contact, sliding interfaces, boundary layers; voxel data | Fitted meshes; finite cell |
| Resonant or narrowband radiation | Frequency-domain Nédélec FEM (D-FLX-32) |
| Broadband transients and EMC | FDTD |
| Exterior acoustics and electrostatics | Boundary elements, or FEM–BEM coupling |
| Granular flow, splashing, fragmentation | DEM, SPH, MPM or peridynamics |
| Lumped systems | Network compiler and DAE solver |

[[DIAGRAM: Per-region discretization: a Part (bolted block, thin wall, swept member, lattice zone) → flux::mark_reduction (t/L_local ≤ 0.2, d/L_local ≤ 0.2) → four boxes: Solid (immersed octree), Shell (Reissner–Mindlin on mid_surface), Beam (Timoshenko or Vlasov on member_axes), Lattice (beam lattice + homogenization). Double arrows labelled dI (rigid at Interactive, Nitsche at SignOff) join Solid to Shell and to Beam. A base bar: one SolvePlan, one multigrid hierarchy, one ErrorBudget per goal; side note: model-form part from 3D patch re-solves.]]

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `flux::plan` | Problem, fidelity, class and budget to a pinned `SolvePlan` with `explain()` | `PlanError::ExceedsLocal { memory, time }`; `NoValidMethod { region, reason }` | FLX-O-PLAN-1 | 1 |
| `flux::mark_reduction` | `Field<Body, ReductionKind>` from local criteria | `UnpairedFaces` from `mid_surface` keeps the region solid, with a note | FLX-O-PLAN-2 | 1 (lattices), 2 |
| Mixed-dimensional couplings | Rigid and Nitsche `dI` interfaces | `IncompatibleInterface { region }` | FLX-O-PLAN-3 | 2 |
| Reduction model error | 3D patch re-solves around goal regions | `NotQuantified`, making a `Pass` conditional | FLX-O-PLAN-4 | 2 |
| Region overrides | `plan.with(region:, model:)` in source | Unsuitable override warns with the criterion value | FLX-O-PLAN-1 | 1 |

## Discretizations

### Immersed octree

A 2:1-balanced octree covers the Body; Anvil's `GeometryQuery` classifies cells (incrementally after local edits), and uncut cells are tensor-product cells with hanging-node constraints in the kernels.

- **Shifted boundary.** Integrates over full interior cells only. Dirichlet data shift from the true boundary by a Taylor expansion along the closest-point vector [Atallah, Canuto, Scovazzi], and traction data with a normal correction and second-order terms at p = 2. The plan refines to at least four cells across every section, then compares the surrogate domain's connectivity and genus with the Body's (Anvil topology counts); a mismatch moves the region to aggregated cut cells with the note `SurrogateMismatch`.
- **CutFEM.** Integrates cut cells on the true geometry, with Nitsche conditions and ghost-penalty stabilization [Burman et al.]. Cut quadrature from `GeometryQuery` follows Saye's methods, which give positive weights and high-order accuracy [Algoim]; moment fitting is used only with non-negative least squares and a conditioning check. Cells below a 1% volume fraction merge with neighbours (a smooth weight in optimization plans, D-FLX-21). An uncertified cut subdivides up to eight levels, then fails with `UncertifiedCut { cell, achieved }`.
- **Finite cell.** Integrates with a volume-fraction indicator and void stiffness α for voxel, CT and density geometry; its patch tolerance is O(α).

**Decision D-FLX-13:** One octree serves three treatments: shifted boundary at `Interactive` (four cells across every section, connectivity check), CutFEM at `SignOff`, and finite cell for voxel data. Shifted boundary stays the `Interactive` default only if its boundary-stress order at p = 2 reaches 2 on the traction oracle (FLX-O-DISC-3); otherwise cut cells run at `Interactive`, reusing cached cut quadrature while classification is unchanged. *Why:* uniform cells suit GPUs within 1 s, while `SignOff` needs conditions on the true surface. *Rejected:* two cells across, which disconnects inclined thin walls (R1-02); an untested default for traction-dominated problems (R1-15). (revised in round 2)

### Shells, beams and lattices

Reissner–Mindlin shells use high-order hierarchic elements, free of shear locking at high p, and MITC-type elements at low order [unverified: element choice], with laminates through MEC's ABD matrices. Kirchhoff–Love shells use C¹ NURBS spaces with Nitsche patch coupling and cut-cell trims [Bazilevs et al.].

Beams use Timoshenko kinematics, with a Vlasov warping unknown for open thin-walled sections; torsion and warping constants come from a 2D warping solve on Anvil's section region. Beam-lattice models place Timoshenko struts on `anvil::lattice` strut graphs, with a stiffened zone one strut radius long at each joint so short, thick struts are not overly compliant [unverified: correction model].

### Explicit dynamics

Explicit dynamics serves drop tests (GP5) and crash boxes (GP9). Mass is diagonal by construction: spectral Gauss–Lobatto–Legendre hexahedra, row-sum lumping on non-negative B-spline shells, and bubble-enriched quadratic tetrahedra, because row-sum lumping gives zero or negative masses on quadratic simplices [unverified: enrichment family]. One-point shells report hourglass energy in the energy balance; contact is penalty segment contact with deterministic `bvh_build` search; COV's damage models drive erosion.

Targets: 10⁷ element cycles per second on the reference laptop CPU in `CpuCanonical` and 5 × 10⁷ on its GPU at `Interactive`. Production-scale crash models are practical (CCSA's 2015 Camry model has 2,277,283 elements); predictive failure is outside the envelope (COV).

**Decision D-FLX-31:** On cut cells, explicit dynamics runs only with ghost-penalty mass stabilization whose stable step is proven independent of the cut fraction; until FLX-O-DISC-7 confirms it, explicit dynamics uses fitted and isogeometric discretizations only, and runs canonically on the CPU at `SignOff`. *Why:* lumped mass scales with the cut fraction while stiffness does not, so the critical step tends to zero (R1-21), and a transient trajectory has no cheap canonical certificate. *Rejected:* mass scaling without a stated error; raw cut cells.

### Electromagnetics

**Decision D-FLX-32:** Resonant and narrowband problems (antennas, filters, cavities) use frequency-domain Nédélec FEM, with ports from a 2D port eigenmode solve (`port_modes`), PML as a complex coordinate stretch in forms, and an adaptive rational fast sweep (`fast_sweep`) with a residual bound; broadband and EMC problems use FDTD. *Why:* ELX requires Palace-level capability, which offers lumped and numeric wave ports and an adaptive fast sweep (R1-22). *Rejected:* routing every antenna problem to FDTD.

FDTD uses the Yee grid with convolutional PML and auxiliary differential equations for dispersive materials. Conformal cells use an update whose stable step is independent of the cut fraction, with cell borrowing [unverified: scheme], or else a stated cut-fraction cap with its accuracy cost. Magnetostatics and eddy currents use A–φ and T–Ω formulations with tree–cotree gauging or discretely divergence-free coil currents. Motion uses a sliding interface on a cylindrical air gap or mortar coupling, as ELX's loss maps need (D-ELX-16). Boards use layered sheets: per-layer thin-sheet conduction coupled through-plane by `dI` conductances (R1-49).

### Fluids and free surfaces

Cell-centred finite volume runs on cut cells and polyhedral meshes with limited least-squares reconstruction and coupled pressure–velocity solves; FEM uses Anvil's `split_polyhedra` output. Free surfaces use a level set with reinitialization (FEM, DG) or volume of fluid (finite volume) for mold filling, with mid-surface Hele-Shaw forms at `Interactive` (D-MFG-15). Flux provides equilibrium wall functions and an immersed wall-model interface for octree RANS and wall-modelled LES; COV owns the turbulence models.

DG uses interior-penalty and upwind fluxes with sum-factorized face kernels; hybridizable DG couples only facet traces [Cockburn, Gopalakrishnan, Lazarov].

### General operations for non-variational methods

D-COV-11's operations serve particles, ray tracing, boundary elements and ELX's placer through `crucible:ops/flux`: BVH build and traversal, neighbour lists by spatial hashing, segmented reductions, counter-based random streams (Philox, keyed by the Op key), fast multipole and hierarchical matrices, and FFT solves including ELX's 2D Poisson solve. Each has a canonical CPU path and, where it pays, a WGSL path. DEM, SPH, MPM, peridynamics and lattice Boltzmann build on them, with errors from solution verification. Boundary elements wrap or contribute to bempp-rs (BSD-3-Clause), with fast multipole or H² compression [unverified: Calderón preconditioning].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Fitted continuous FEM | Anvil volume meshes curved to p ≤ 8; hex-dominant through `split_polyhedra` | `InvalidElement { cell, jacobian_min }`, suggesting `anvil::untangle` | FLX-O-DISC-1 | 2 |
| Shifted boundary method | `Interactive` solids; four cells across; connectivity check | `SurrogateMismatch` note; aggregated cut cells | FLX-O-DISC-3 | 1 |
| CutFEM | `SignOff` solids; Nitsche, ghost penalty, positive-weight quadrature | `UncertifiedCut { cell, achieved }` | FLX-O-DISC-2, FLX-O-DISC-5 | 1 |
| Finite cell method | Voxel, CT and density geometry | Patch error above O(α) | FLX-O-DISC-4 | 2 |
| Reissner–Mindlin and Kirchhoff–Love shells | Mid-surface sheets, thickness Fields, laminates | `UnpairedFaces` keeps the region solid | FLX-O-DISC-6 | 2 |
| Timoshenko and Vlasov beams | Member axes and section regions | `NotPrismatic` keeps the region solid | FLX-O-DISC-6 | 1 (struts), 2 |
| Beam-lattice models | Strut graphs with joint corrections | Graph over budget falls back to homogenization, stated | FLX-O-COUP-2 | 1 |
| DG and hybridizable DG | Advection-dominated and high-order problems | `CflViolated { cell }` | FLX-O-DISC-1 | 3 |
| Finite volume and free surfaces | Flow, filling, conjugate heat transfer | `NotConservative { cell, imbalance }` | FLX-O-DISC-10 | 3 |
| Explicit dynamics | Diagonal mass, under-integrated shells, penalty contact, erosion | `StepCollapsed { element }` | FLX-O-DISC-7 | 3 |
| Frequency-domain electromagnetics | Nédélec, ports, PML, fast sweep with bound | `SweepNotConverged { band }` | FLX-O-DISC-8 | 4 |
| FDTD | Conformal Yee with CPML | Cut-fraction cap reported with its error | FLX-O-DISC-8 | 3 |
| Magnetodynamics with motion | A–φ and T–Ω; sliding interface or mortar | `SourceNotSolenoidal { coil }` | FLX-O-DISC-9 | 4 |
| Layered sheets | Thin-sheet conduction with through-plane `dI` | None beyond the solver's | FLX-O-DISC-6 | 3 |
| Boundary elements | Laplace, Helmholtz, Maxwell kernels with fast methods | `NotClosed { gaps }` from Anvil | FLX-O-DISC-12 | 3 |
| General operations | BVH, neighbour lists, reductions, random streams, FMM, H-matrices, FFT | `WorkLimit` with the achieved size | FLX-O-DISC-11 | 2, 3 (FMM, FFT) |
| Lattice Boltzmann | D3Q19 and D3Q27 on sparse grids | Instability reported with the step | FLX-O-DISC-11 | 4 |
| Particles and peridynamics | DEM, SPH, MPM, peridynamics | `Indicator` bounds without solution verification | FLX-O-DISC-11 | 5 |

## Meshing and adaptivity

Anvil owns every mesh operation (D-ANV-12). Flux decides what to mesh and how finely through sizing and metric Fields, and owns estimation, marking and solution transfer.

| Flux need | Anvil operation | Anvil phase |
| --- | --- | --- |
| Classification, closest points, cut quadrature, thickness, topology counts | `GeometryQuery` | 1 |
| Mid-surfaces and member axes | `anvil::mid_surface`, `anvil::member_axes` | 2 (1 for lattice struts) |
| Curved conforming tetrahedra; bisection | `anvil::tetrahedralize`, `anvil::untangle`, `anvil::refine_mesh` | 2 |
| Metric adaptation and node relocation | `anvil::adapt_mesh`, `anvil::optimize_mesh` | 3 |
| Hex-dominant and swept meshes | `anvil::hex_dominant`, `anvil::sweep_mesh`, `split_polyhedra` | 3 (sweep), 4 |
| Boundary layers; interface overlays | `anvil::boundary_layer`; `anvil::common_refinement` | 4 |
| Shape sensitivities | `anvil::shape_velocity` | 2 |

| Kind | Immersed octree | Fitted mesh | Isogeometric |
| --- | --- | --- | --- |
| h | Octree refinement with 2:1 balance | Bisection; metric remeshing for large changes | Truncated hierarchical B-splines |
| p, hp | Per-cell degree, minimum rule on shared faces; smooth cells (Legendre decay) raise p, others split | Same | Degree elevation, k-refinement |
| r | Not used | `optimize_mesh` | Control points (phase 5) |

The adaptive loop is SOLVE → ESTIMATE → MARK → REFINE on declared goals with Dörfler marking at θ = 0.5. Each iteration is its own node, so a budget Abort stops only the iteration in flight; stagnation over two iterations reports a probable singularity. Solution transfer is a conservative projection whose error joins the temporal part.

### Interactive latency

Contract section 13.3 sets the target: 1 s for linear static elasticity up to 100,000 DOFs at p = 2, warm-started, on G1; in browsers 2 s with WebGPU and 6 s CPU-only, remote above that. Stage budgets, measured on GP1, GP2 and GP5 in phase 0 (targets; Anvil owns the first two): Anvil rebuild 150 ms; classification and distance queries, incremental after local edits, 200 ms; setup 100 ms; solve 350 ms; estimate 100 ms; display 100 ms.

**Decision D-FLX-37:** During a geometric drag, physics results show as `Proxy` until the full update arrives (phases 1 and 2). From phase 3, reduced models on a fixed background discretization answer parametric geometric drags, with geometry entering through a morphing map from `anvil::shape_velocity`. *Why:* cell classification changes with geometry, so a reduced model on one discretization cannot serve geometric parameters without a morph (R1-16). *Rejected:* reduced-model answers for geometric drags in phase 1.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Sizing and metric Fields | `Field<Body, Length>`, `Field<Body, Metric>` from estimators | Anvil's `QualityNotReached { worst, target }` reported upward | FLX-O-MESH-1 | 2 |
| h-, p- and hp-adaptivity | Octree, fitted and spline refinement on declared goals | `ProbableSingularity { region }` on stagnation | FLX-O-MESH-1 | 1 (octree), 2, 3 (metric) |
| Solution transfer | Conservative projection | Transfer error above tolerance refines the transfer | FLX-O-MESH-2 | 2 |
| Interactive stage budgets | Six stages within 1 s on G1 | Budget miss streams the coarse result as `Proxy` | FLX-O-MESH-3 | 1 |
| Geometric drags | `Proxy`, then morphing reduced models | `TopologyChange` ends the morph | FLX-O-ROM-1 | 1, 3 (morphing) |

## Solvers

### Linear algebra

Matrix-free operators, sparse matrices and block operators compose as `LinearOperator`s over libCEED's T-, L- and E-vector layouts.

**Decision D-FLX-36:** `Portable` linear algebra runs on the canonical `linalg` crate: machine-independent blocking, canonical lane order, no FMA, pivot ties broken by index. Unmodified faer runs only in `CpuIsa`, with cache detection pinned. Sparse factorization is canonical supernodal elimination with tree-level parallelism and a fixed child order, independent of thread count, offered to faer upstream as a deterministic mode. *Why:* faer's dense kernels size reduction blocks from detected caches and use FMA microkernels, so sums depend on the machine (R1-10, R6-21). *Rejected:* unmodified faer in the canonical class; permanent single-threaded canonical factorization.

| Use | Method | Phase |
| --- | --- | --- |
| Symmetric problems up to about 2M DOFs, coarse grids, reduced bases | Supernodal LLᵀ and LDLᵀ with deterministic nested dissection | 1 (sequential), 2 (parallel) |
| Networks and circuits | Block-triangular sparse LU with per-block ordering and numeric refactorization (the KLU scheme, reimplemented) | 2 |
| Indefinite Maxwell | Complex symmetric LDLᵀ up to its memory limit | 4 |
| Mixed precision | `f32` factorization with `f64` GMRES refinement when a condition estimate is below 10⁷ | 2 |
| Distributed | STRUMPACK or SuperLU_DIST through `bridges/` [unverified: licences]; MUMPS only as an External Op [unverified: CeCILL-C] | 4 |

Carson and Higham show GMRES refinement extends LU refinement from κ₂ ≤ 10⁴ to 10⁸ for half-precision factors; the 10⁷ cutoff keeps κ · u_f32 below 1.

### Krylov methods and preconditioners

Krylov methods: CG, pipelined CG, MINRES, GMRES and FGMRES with fixed restart, BiCGStab, block variants.

| Problem | Default | Phase |
| --- | --- | --- |
| Elliptic, high order, octree | p-multigrid, then h-multigrid with global coarsening, then deterministic AMG; Chebyshev–Jacobi on uncut cells, additive Schwarz on cut-cell patches; low-order-refined AMG as alternative | 1 |
| Low order and fitted | Smoothed-aggregation AMG with rigid-body near-null space; hypre BoomerAMG through `bridges/` | 1 |
| Shells and beams | Same hierarchy with rotational near-null modes | 2 |
| H(curl), H(div) | Auxiliary-space AMG (Hiptmair–Xu) on Flux AMG; hypre AMS and ADS as bridges | 3 |
| Stokes and Oseen | Block-triangular field split with pressure convection–diffusion (PCD) or scaled least-squares commutator | 3 |
| High-Reynolds steady Navier–Stokes | Augmented Lagrangian with vertex-star patch smoothers and kernel-capturing prolongation | 4 |
| Transient high-order flow | Dual splitting with matrix-free pressure p-multigrid | 4 |
| Upwind DG transport | Approximate-ideal-restriction AMG | 3 |
| Indefinite Maxwell and Helmholtz | Complex LDLᵀ up to memory; optimized Schwarz with impedance transmission beyond; shifted-Laplacian multigrid | 4 |
| Distributed, above about 5 × 10⁷ DOFs | BDDC with deluxe scaling; FETI-DP for contact | 4 |

Low-order-refined preconditioners for the high-order de Rham complex are spectrally equivalent independently of degree and mesh size [Pazner, Kolev, Dohrmann]. Global coarsening scales better than local smoothing on up to 147,456 cores [Munch et al.]. Small cut cells create eigenvalues that Jacobi smoothing does not damp, so cut-cell patches get Schwarz smoothers [unverified: de Prenter et al. 2020].

**Decision D-FLX-16:** Flux builds its own matrix-free p- and h-multigrid with global coarsening and its own deterministic AMG, with additive Schwarz patch smoothers and aggregation around cut cells and Chebyshev–Jacobi elsewhere; hypre and PETSc are optional bridges. *Why:* AMG setup must coarsen identically in every class and run in Wasm, and cut cells defeat point smoothers (R1-17). *Rejected:* mandatory hypre or PETSc, which have no browser path; Jacobi smoothing on cut cells. (revised in round 2)

**Decision D-FLX-33:** Navier–Stokes uses PCD or scaled least-squares commutators for Oseen problems up to moderate Reynolds numbers, an augmented Lagrangian preconditioner with its specialized multigrid at high Reynolds numbers, and dual splitting with matrix-free pressure multigrid for high-order transients. *Why:* pressure-mass Schur approximations suit only Stokes (R1-23); Farrell, Mitchell and Wechsung report about 3 Krylov iterations per Newton step at Re = 1,000 and 5 at Re = 5,000 on a 3D cavity with about 10⁹ DOFs. *Rejected:* SIMPLE-type segregation as the only option.

AMG setup is deterministic: exact strength comparisons, aggregation priorities from canonical DOF numbers (never names, threads or ranks), fixed-order Galerkin products.

### Nonlinear solvers and bifurcations

| Method | Use | Phase |
| --- | --- | --- |
| Newton–Krylov, exact Jacobians, backtracking, Eisenstat–Walker forcing | Every nonlinear form | 1 |
| Trust-region Newton; arc length (Riks, Crisfield); semismooth Newton; Anderson acceleration | Energy forms; limit points and load paths; contact; partitioned coupling | 2 |
| Pseudo-transient continuation | Strongly nonlinear steady flows | 3 |
| Nonlinear preconditioning | Localized nonlinearity [unverified: method] | 4 |

**Decision D-FLX-25:** Newton and arc-length solvers monitor the tangent's inertia (LDLᵀ pivot signs or smallest Lanczos eigenvalues) and, at a sign change, return `Bifurcation { load, modes }` instead of choosing a branch. A study picks a branch only through an explicit imperfection or `branch: follow(mode: k, sign: +)` in source. *Why:* rounding decides which branch Newton follows, so a silent choice breaks cross-class agreement (principle 4, R1-13). *Rejected:* silent branch choice; automatic imperfections.

Limit points are reported likewise; electro-thermal runaway returns `Runaway { power }` at the turning point (R1-49). `NonlinearDiverged` returns the last converged state and suggests smaller steps, continuation or an envelope check.

### Time integration

| Family | Use | Phase |
| --- | --- | --- |
| BDF orders 1 to 5; SDIRK and ESDIRK; additive Runge–Kutta IMEX | Stiff parabolic and stiff–nonstiff problems | 2 |
| Generalized-α, Lie group generalized-α | Structural and multibody dynamics | 2 |
| Central difference; SSP Runge–Kutta; symplectic schemes | Explicit dynamics, DG, finite volume, particles, FDTD | 3 |
| Exponential integrators; Parareal and MGRIT | Stiff linear-dominated problems; long horizons | 5 |

Temporal goal error is the adjoint-weighted residual in time; summed local estimates are `Indicator`, because phase error accumulates in oscillatory problems (R1-20). Events are found by root-finding on dense output. SUNDIALS (BSD-3-Clause) is a cross-check oracle; Flux reimplements the integrators so each step is a deterministic, differentiable node.

### Eigenvalue problems

Shift-invert Lanczos with Krylov–Schur restarts and LOBPCG ship in phase 1 for modal analysis and buckling, including lattice struts (R1-35); Krylov–Schur on linearizations (damping, gyroscopic, flutter) and Maxwell deflation follow in phase 3, contour integrals in phase 4. Eigenvectors are mass-normalized, largest entry positive, ties broken by DOF number; degenerate eigenspaces are reported as subspaces with Kato–Temple bounds.

### Contact, constraints and fracture

| Mechanism | Enforcement | Phase |
| --- | --- | --- |
| Dirichlet; multi-point, periodic, cyclic and integral constraints | Strong on fitted meshes, Nitsche on immersed and spline; elimination in kernels or `Real` multipliers | 1 |
| Bonded interfaces; frictional contact | Mortar with dual multipliers and semismooth Newton; augmented Lagrangian; penalty at `Interactive` | 2 |
| Large sliding; immersed contact; thermal and electrical contact | Sorted deterministic search; Nitsche on cut surfaces [unverified: high-order robustness]; conductance on `dI` | 3 |

Penalty results support `SignOff` only with penetration error estimated and below tolerance. Fracture hooks carry COV's models: J-integrals (phase 2), cohesive zones on `dI` (3), phase field (4), cut-cell cracks and peridynamic damage (5).

### GPU solves, CPU certifies

**Decision D-FLX-17:** A GPU solve produces a Field pinned by `ObjectId`; the `Portable` `flux::certify` recomputes its residual and budget in `CpuCanonical` with `f64` operator and constitutive evaluation, so the check outcome is canonical although the Field's bits are not (contract section 7.3). `f32` inner solves run inside defect correction on the CPU residual, which falls back to a canonical CPU solve whenever the outer residual contracts by less than a factor of 2 per cycle for two cycles. *Why:* Metal and WebGPU lack `f64`, yet `SignOff` needs canonical outcomes everywhere, and defect correction stalls as κ(A)·u_f32 approaches 1 (R1-11). *Rejected:* uncertified `f32` results; forbidding GPUs at `SignOff`. (revised in round 2)

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Canonical direct solvers | Supernodal LLᵀ and LDLᵀ, block-triangular LU, complex LDLᵀ | `SingularOperator { null_space_hint }` | FLX-O-SOLVE-1 | 1 to 4 per row |
| Multigrid and AMG | p- and h-multigrid, Schwarz smoothers on cut cells, deterministic AMG | `LinearDiverged { residual_history }` | FLX-O-SOLVE-2 | 1 |
| Navier–Stokes preconditioners | PCD, LSC, augmented Lagrangian, dual splitting, AIR | `LinearDiverged`, preconditioner named | FLX-O-SOLVE-3 | 3, 4 |
| Electromagnetic solvers | Auxiliary-space AMG, complex LDLᵀ, optimized Schwarz | `LinearDiverged` | FLX-O-DISC-8 | 3, 4 |
| Nonlinear solvers | Newton, trust region, arc length, semismooth Newton | `NonlinearDiverged` with the last converged state | FLX-O-SOLVE-4 | 1, 2 |
| Bifurcation detection | Tangent inertia monitoring | `Bifurcation { load, modes }`; `Runaway { power }` | FLX-O-SOLVE-4 | 2 |
| Time integrators | Implicit, IMEX and explicit schemes with events | `StepTooSmall { t }` | FLX-O-SOLVE-5 | 2, 3 |
| Eigen-solvers | Lanczos and LOBPCG; Krylov–Schur; contour integrals | `NotConverged { found, wanted }` | FLX-O-SOLVE-6 | 1, 3, 4 |
| Contact and constraints | Mortar, Nitsche, augmented Lagrangian, estimated penalty | `PenetrationAboveTolerance` blocks `SignOff` | FLX-O-SOLVE-7 | 1 to 3 |
| GPU solve with CPU certification | Pinned GPU Field; canonical residual and budget | Stall falls back to the canonical CPU solve | FLX-O-SOLVE-8 | 2 |

## Networks, multibody dynamics and rods

### Networks

A Network is a lumped model of elements joined through domain-typed ports (contract section 2). ELX owns the `network { … }` builder, element libraries and the electrical fast path; Flux owns compilation and integration for every domain.

1. `flux::compile_network` flattens the hierarchy. The Ingot compiler has already checked each port type's power expression; under the strong angular system, torque (J/rad) times angular velocity is a power.
2. It applies Pantelides index reduction with dummy-derivative selection, block lower-triangular ordering and tearing.
3. It compiles each reachable mode of networks with switches, diodes, clutches or backlash once, cached by mode key.
4. It emits residuals and Jacobians in the kernel IR.

`flux::solve_dae` integrates the index-1 result with variable-order BDF and trapezoidal rules, events, breakpoints and adjoint sensitivities, on the block-triangular LU. Events reinitialize consistently, including impulsive jumps such as a locking clutch. Network solves are `F64Required`: no `f32` GPU path, and Monte Carlo batches run one sample per CPU SIMD lane (R1-39). Results are `Field<(Ports, Time), V>`, or `Field<(Ports, Frequency), Complex<V>>` for small-signal analysis; FMU instances join as elements through the FMI runtime.

**Decision D-FLX-27:** Networks compile to index-1 DAEs by Pantelides reduction with static dummy-derivative selection per mode, BLT ordering, tearing and cached per-mode compilations; states are re-selected only at a deterministic event, when a pivot test shows the selected block singular. *Why:* one structural analysis is invalid after a mode change (R1-50), and run-time state selection between events would make results depend on solver history. *Rejected:* Pantelides without dummy derivatives; one structural analysis for switched networks.

### Multibody dynamics

MEC hands over an Assembly with typed joints, the redundancy report, mass properties with bounds, contact pairs and drivers (D-MEC-12). `flux::solve_multibody` writes the motion as an index-3 DAE on the Lie group of rigid motions and integrates it with Lie group generalized-α, which needs no rotation parameterization and is globally second-order accurate for translations, rotations and multipliers [Brüls, Cardona, Arnold].

- Redundant but consistent joints are removed by rank-revealing QR in `linalg` and reported, or replaced by declared compliance.
- Joint axes expose rotational and translational ports, so a motor drive's Network drives a joint directly.
- Contact is compliant with regularized Coulomb friction, using Anvil distance queries and `bvh_build`; nonsmooth contact arrives in phase 4 [unverified: method].
- Flexible bodies are Craig–Bampton reduced Parts in a floating frame, or exact beams; results are `Field<(Instances, Time), Transform>`, joint loads over `(Ports, Time)` and an energy balance.

Project Chrono (BSD-3-Clause) is the implementation to beat. MFG's assembly planner checks sub-assembly stability with the same solver's quasi-static contact equilibrium (D-MFG-17).

**Decision D-FLX-28:** Multibody dynamics is an index-3 DAE on the Lie group of rigid motions, integrated by Lie group generalized-α with scaled constraints, with redundancy removed by rank-revealing QR. *Why:* no parameterization means no singular configurations, and the method is second-order in every unknown without index reduction. *Rejected:* Euler-angle or quaternion-coordinate formulations (singularities, normalization drift); Baumgarte-stabilized ODEs, which drift and need tuning.

### Cosserat rods

`flux::solve_rod` models cables, harnesses and hoses as geometrically exact Cosserat rods: a centreline with a director frame, with bending, torsion, shear and extension. Kirchhoff rods, which MEC's harness model asks for, are the stiff-shear limit. Statics minimize energy by trust-region Newton; dynamics use Lie group generalized-α. Contact with Bodies uses Anvil distance queries and self-contact `bvh_build`, and results are Fields on the rod's wire Body. PyElastica (MIT) is the reference implementation [Gazzola et al.].

**Decision D-FLX-29:** Cables and hoses are geometrically exact Cosserat rods sharing the multibody integrator, with Kirchhoff behaviour as the stiff-shear limit. *Why:* hoses stretch and shear under pressure and clamping, and one integrator couples rods to joints and contact. *Rejected:* inextensible Kirchhoff rods only; spring–mass chains, which converge poorly in bending and torsion.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `flux::compile_network` | Flattening, index reduction with dummy derivatives, BLT, tearing, per-mode compilation, kernel-IR residuals | `StructurallySingular { equations }`; `HighIndexAfterReduction` | FLX-O-NET-1 | 2 |
| `flux::solve_dae` | Index-1 DAE: BDF, trapezoidal rule, events, consistent reinitialization, adjoints | `ReinitFailed { event }`; `StepTooSmall { t }` | FLX-O-NET-2 | 2 (mechanical, thermal), 3 (electrical) |
| Block-triangular sparse LU | Per-block ordering; numeric refactorization; complex arithmetic | `SingularOperator { block }` | FLX-O-NET-3 | 2 |
| `flux::solve_multibody` | Rigid bodies, typed joints, redundancy handling, compliant contact, Network-driven joints | `InconsistentRedundancy { joints }`; `Bifurcation` at toggle points | FLX-O-MBD-1 | 2 (rigid), 3 (flexible), 4 (nonsmooth) |
| `flux::solve_rod` | Cosserat statics and dynamics with contact | `NonlinearDiverged` with the last state | FLX-O-MBD-2 | 4 |

## Coupling, homogenization and co-simulation

Monolithic coupling solves one product-space form by Newton with field-split preconditioning; partitioned coupling exchanges interface Fields until they agree.

| Coupling | Default | Phase |
| --- | --- | --- |
| Thermal stress, one way | Sequential solves joined through Kiln | 1 |
| Two-way thermo-mechanics; element activation for welding and additive processes | Monolithic Newton with field split | 2 |
| Electro-thermal | Monolithic Newton with continuation; `Runaway { power }` at turning points | 3 |
| Conjugate heat transfer | Partitioned with Robin conditions, or monolithic on a shared octree | 3 |
| Electromagnetic–structural | Partitioned: Maxwell stress or virtual work | 4 |
| Fluid–structure, weak or strong added mass | Partitioned with Aitken or interface quasi-Newton (IQN-ILS, IQN-IMVJ); monolithic ALE or Robin–Robin for strong added mass | 4 |
| Piezoelectric and electrostatic MEMS | Monolithic; pull-in reported as a bifurcation | 5 |

Element activation switches cells on by a layer or time Field: per layer group for MFG's inherent-strain model in phase 1, transiently for weld distortion in phase 2. Interface transfer is conservative for fluxes and consistent for states, through `anvil::common_refinement` from phase 4. A partitioned iteration's interface residual is part of the algebraic budget; divergence returns `CouplingDiverged { residual_history }`, suggesting the monolithic form or quasi-Newton. preCICE (LGPL-3.0) serves only as an external tool for coupling external solvers.

### Homogenization and lattices

`flux::homogenize` solves periodic unit-cell problems and returns effective tensors as `Reduced` or `Surrogate` Fields over cell parameters, with bounds. `flux::localize` rebuilds micro stresses from a macro strain and the unit-cell solutions, and lattice strength checks read these localized strut stresses (R1-26). For COV's lattice envelope Flux computes three regime variables: the ratio of cell size to macroscopic gradient length; distance to the boundary in cells (`Invalid` within two cells unless a boundary-layer correction applies); and strut slenderness times compressive macro strain (`Flag` above a Bloch-wave buckling bound from the unit cell).

A lattice part's critical region signs off with a full-resolution beam-lattice model. Dehomogenization to explicit geometry runs through Anvil in phase 2, and concurrent FE² batches micro solves through the parameter-domain machinery (D-FLX-38) in phase 5.

### Co-simulation over FMI and SSP

**Decision D-FLX-30:** Flux owns the FMI 3.0.2 and SSP 2.0.1 runtime: import, export, master algorithms and Model Exchange integration. Native-binary FMUs run as External Ops on untrusted-evaluation workers, with the host's class or `Unverified`; FMUs with determinized Wasm binaries run in the sandbox as ordinary Ops. *Why:* native FMUs are untrusted code (contract section 7.8), and one runtime ends duplicate FMI specifications in FLX and ELX (R3-24). *Rejected:* native FMUs in the evaluation sandbox; per-tab FMI runtimes.

ELX keeps FMU instances as Network elements and FMI-LS-BUS; ECO keeps FMU packaging, including FMI-LS-WASM. Flux runs each imported FMU twice in CI; one whose outputs differ is marked `NonDeterministic`, and its results never reach the shared cache.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Monolithic and partitioned coupling | Product-space forms; Aitken and interface quasi-Newton; conservative transfer | `CouplingDiverged { residual_history }` | FLX-O-COUP-1 | 1 to 5 per row |
| Element activation | Cells activated by a layer or time Field | `ActivationGap { layer }` | FLX-O-COUP-1 | 1 (layer groups), 2 |
| Homogenization | Unit-cell solves to effective-tensor Fields | `NotPeriodic { faces }` | FLX-O-COUP-2 | 1 (elastic), 3 |
| Localization and lattice regimes | Micro stresses; scale, boundary-distance and buckling regime Fields | Zones `Invalid` or `Flag` per COV | FLX-O-COUP-2 | 1 |
| FE² | Batched micro solves per macro quadrature point | `MicroDiverged { point }` | FLX-O-COUP-2 | 5 |
| FMU import (all three interface types) | External Op or sandboxed Wasm; Model Exchange uses provided directional and adjoint derivatives | `NoBinaryForPlatform { available }`; stated finite differences otherwise | FLX-O-COUP-3 | 3 |
| FMU export and SSP | Ported models to Co-Simulation FMUs with state serialization; SSP archives to and from Ingot | Size warning; unknown layered standards kept and reported | FLX-O-COUP-3 | 3 |
| Master algorithms | Jacobi, Gauss–Seidel, variable step with rollback, clocked partitions | FMUs without rollback run fixed-step, stated | FLX-O-COUP-3 | 3 |

## Gradients and optimization

Flux differentiates the discretized problem from its forms, following Farrell, Ham, Funke and Rognes, who report this more efficient and automatic than differentiating low-level code. Derivatives work at three levels: forms (tangent and adjoint forms compiled through the same pipeline); operations (each differentiable operation implements `Differentiable` in `base`, and Kiln chains them by reverse traversal from a scalar goal); and geometry (`anvil::shape_velocity` supplies face velocities and returns `TopologyChange` when topology changes). `grad(J, wrt: [p1, p2])` and `hessian_vector(J, wrt: p, v)` return values with bounds from the forward and adjoint algebraic parts and the discretization-consistency gap.

**Decision D-FLX-21:** Gradients are derivatives at a frozen discretization (cells, aggregation map, adaptive marks, time steps). The gradient's bound says so, Taylor tests straddling a discretization change are flagged rather than failed, and optimization plans replace the hard aggregation switch with a smooth weight. *Why:* the discrete objective is not differentiable where the discretization changes with the design (R1-19). *Rejected:* claiming exact gradients across changes; operator-overloading AD of solver code; continuous adjoints, inconsistent with the discrete objective. (revised in round 2)

| Problem | Adjoint | Cost | Phase |
| --- | --- | --- | --- |
| Linear and nonlinear steady | One transposed linear solve at the converged state | At most one forward solve | 1 |
| Eigenvalue | Eigenvector formula; subspace form for repeated eigenvalues | Small | 2 |
| Transient | Backward in time with optimal multistage checkpointing | Two to five forward solves | 2 |
| Contact; coupled | Converged active set (changes flagged); block-transposed | As forward | 3; 4 |

Transient adjoints use Revolve-style checkpointing extended to multistage schemes by Zhang and Constantinescu, whose CAMS algorithm needs the fewest recomputations among those compared and is used in PETSc's TSAdjoint. Checkpoints live in Kiln's `Checkpoint` retention class keyed by (`OpKey`, step), so an adjoint re-run after an objective-only change reuses them.

### Topology optimization

| Method | Formulation | Phase |
| --- | --- | --- |
| Density | SIMP on the immersed octree; Helmholtz filter; smoothed Heaviside projection; robust eroded, intermediate and dilated designs; MFG's manufacturing constraints | 1 (compliance, volume), 2 (stress, robust, manufacturing) |
| Graded lattice | Homogenized cell-parameter maps, then dehomogenization | 1, 2 |
| Level set | Shape and topological derivatives with CutFEM analysis | 3 |
| Multiphysics | Any coupled form through the coupled adjoint | 4 |

The optimizer is the method of moving asymptotes and its globally convergent variant, implemented natively as `flux::mma_step` [unverified: licence of Svanberg's reference code]; the loop is Ingot (`std::opt::topology`), so iterations are cached nodes. Results include `design.density` and `design.geometry_density`, the filtered, projected H¹ density with a gradient bound that `anvil::implicit_from_field` requires (R1-57). Stress constraints aggregate regularized stresses by p-norms (D-FLX-23).

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

Aage, Andreassen, Lazarov and Sigmund reached giga-voxel resolution for a full aircraft wing. Released geometry must be `Portable`, so `SignOff` optimization runs in `CpuCanonical`, with targets of 10⁸ density elements on a 64-core server and 10⁹ on a cloud cluster; GPU paths accelerate `Interactive` exploration only.

### Shape, parameter and experimental design

Shape optimization works on Ingot parameters through the geometry chain rule, or on boundary-morphing Fields with Hilbertian gradients [unverified: Fireshape licence]. Optimizers: L-BFGS-B, SQP, interior point, MMA, trust region with Hessian-vector products, CMA-ES, and NSGA-II-type search giving Pareto fronts as Fields. Bayesian optimization belongs to AGT's `std::explore` (D-AGT-15), which consumes Flux gradients and surrogates. Stochastic optimizers use counter-based random streams keyed by the Op key. `std::sim::study` runs full factorial, maximin Latin hypercube, Sobol, Halton and adaptive designs; each point is a node, so a study caches per point and resumes after an Abort.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Form- and operation-level derivatives | `Differentiable` tangents and adjoints chained by Kiln; `grad`, `hessian_vector` | `NotDifferentiable { op }`; straddling tests flagged | FLX-O-OPT-1 | 0 (forms), 1 |
| Adjoints | Steady, eigen, transient with multistage checkpointing, contact, coupled | `CheckpointMissing` triggers recomputation | FLX-O-OPT-3 | 1, 2 to 4 per row |
| Shape gradients | Chain rule through `anvil::shape_velocity` | `TopologyChange { parameter, entities }` | FLX-O-OPT-1 | 2 |
| Density topology optimization | SIMP, filters, projection, MMA; `geometry_density` | `Infeasible { constraints }` with the closest feasible design | FLX-O-OPT-2 | 1 |
| Level-set and multiphysics topology optimization | Shape and topological derivatives; coupled adjoints | As above | FLX-O-OPT-2 | 3, 4 |
| Optimizers and experimental designs | Gradient, evolutionary and multi-objective optimizers; factorial, Latin hypercube, Sobol designs | `NotConverged { iterations }` with the best design | FLX-O-OPT-2 | 1 (MMA), 2 |

## Uncertainty quantification

| Method | Use | Error part | Phase |
| --- | --- | --- | --- |
| Monte Carlo, randomized quasi-Monte Carlo | Reference method, yields | Confidence or repeated-scramble interval | 2 |
| Multilevel and multi-fidelity Monte Carlo | Refinement hierarchies, with tolerance-based levels when plans adapt per sample; reduced models as control variates | Bias and variance parts | 3 |
| Sparse polynomial chaos | Smooth dependence on up to about 20 parameters | Cross-validation | 3 |
| Sobol indices grouped by correlation group; Shapley effects | Sensitivity with independent or dependent inputs | Bootstrap interval | 3 |
| Subset simulation, cross-entropy importance sampling; first-order reliability | Failure probabilities below 10⁻³; most-probable points by adjoint gradients | Coefficient of variation; `Estimated` | 3; 4 |
| Probability boxes | Epistemic intervals by nested sampling, never summed with distributions | — | 3 |

Multilevel Monte Carlo fits immersed plans, which already have level hierarchies [Giles]. With `Tol<T>` correlation groups or Material correlations, Flux reports grouped Sobol indices and Shapley effects (R1-36) [unverified: Shapley estimator].

**Decision D-FLX-35:** Propagating `Tol<T>` through physics is worst case by default, matching `Tol<T>` arithmetic (contract section 5). `std::uq::worst_case` linearizes the quantity with adjoint gradients, sums half-widths times absolute sensitivities over correlated affine noise symbols, and checks the linearization with one Hessian-vector product; statistical propagation is an explicit `std::uq::propagate` call. *Why:* one adjoint per goal, and one semantics for tolerances everywhere. *Rejected:* a silent uniform-distribution default (round 1), contradicting the contract; Monte Carlo for worst cases.

MEC owns default distributions for statistical calls (R1-37): uniform within limits without process data, normal with mean shift and spread from Cp and Cpk with MFG process profiles. GD&T controls enter as MEC's skin-model samples, `Field<Faces, Displacement>`. Yields use smoothed indicators or conditional sampling, with the repeated-scramble interval in the statistical part. For MEC's compliant variation analysis, Flux supplies influence coefficients (compliance at measurement points by static condensation) in phase 2.

```
let stress = study.von_mises.max(over: p.away_from(clamp, 2 * thickness))
let worst  = std::uq::worst_case(stress, inputs: tolerances(p))              // Approx<Stress>
let stats  = std::uq::propagate(stress, inputs: tolerances(p), method: mlmc)
p.require(stats.quantile(0.999) < 0.6 * p.material.yield_strength(at: 20degC))
```

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Worst-case tolerance propagation | Adjoint-linearized affine bounds with a second-order check | `NonlinearResponse { ratio }` asks for a statistical method | FLX-O-UQ-3 | 2 |
| Sampling methods | Monte Carlo, randomized QMC, MLMC, multi-fidelity | `BudgetTooSmall { samples }` before running | FLX-O-UQ-2 | 2, 3 |
| Polynomial chaos and sensitivity | Sparse PCE; grouped Sobol indices; Shapley effects | `DependentInputs` for plain Sobol on correlated inputs | FLX-O-UQ-1 | 3 |
| Rare events and reliability | Subset simulation, cross-entropy sampling, FORM | `NotConverged { cov }` | FLX-O-UQ-1 | 3, 4 |
| Epistemic inputs | Probability boxes by nested sampling | None | FLX-O-UQ-1 | 3 |
| Influence coefficients | Compliance at measurement points for MEC | `SingularOperator` without supports | FLX-O-UQ-3 | 2 |

## Reduced models and surrogates

| Model | Build | Error | Phase |
| --- | --- | --- | --- |
| Modal superposition; Craig–Bampton synthesis | Lanczos modes; fixed-interface and constraint modes per Part, cached separately | Truncation estimates from residual mass and interface modes | 2 |
| POD–Galerkin; hyper-reduction | Snapshots over time or parameters; DEIM or energy-conserving sampling and weighting [unverified: DEIM attribution] | Residual-based, `Estimated` | 3 |
| Certified reduced basis | Greedy sampling for affinely parametrized linear forms | `Guaranteed` with a coercivity lower bound [unverified: lower-bound method] | 3 |
| Krylov moment matching | Frequency-domain reduction for fast sweeps and FMU export | Residual over the band | 3 |
| Morphing reduced models | Fixed background discretization plus `shape_velocity` morphs (D-FLX-37) | Residual-based | 3 |

A reduced model records its parameter box; queries outside it fail with `OutsideEnvelope { parameter, range }` unless the caller requests a full solve.

### Surrogates

Surrogates cover strong nonlinearity and geometry families without a shared discretization: Gaussian processes for small data, neural operators and mesh graph networks for large data. Training on Flux results is a deterministic operation (counter-based random streams, fixed-order reductions); its weights are a CAS artifact whose labels join those of the training data.

**Decision D-FLX-14:** A surrogate prediction is a Field of kind `Estimated { confidence, scope: Marginal }`. It may drive `Preview` and `Interactive` results and design exploration; a `SignOff` check may use it only with a per-prediction a posteriori bound or a confirming solve; inside optimization loops, calibration uses weighted conformal prediction. *Why:* split-conformal coverage is marginal, averaged over test points, exact conditional guarantees are impossible without assumptions [Barber et al.], and optimizers steer queries toward a surrogate's errors. *Rejected:* split-conformal intervals as `SignOff` evidence; physics-informed networks as forward solvers without a posteriori bounds. (revised in round 2)

The per-prediction bound projects the prediction onto the plan's finite element space and bounds its error with an equilibrated estimator, using a global coarse solve to restore the patch compatibility that Galerkin orthogonality usually provides. Weighted conformal calibration weights points by an estimated likelihood ratio between query and training inputs [Tibshirani et al.], uses locally adaptive scores, and reports the effective calibration size.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Modal and Craig–Bampton models | Eigen-solve bases; assembly-level reduction | `OutsideEnvelope` beyond the band | FLX-O-ROM-1 | 2 |
| POD, reduced basis, hyper-reduction, morphing models | Snapshot bases; certified or residual bounds | `OutsideEnvelope { parameter, range }`; `TopologyChange` | FLX-O-ROM-1 | 3 |
| Surrogate training | Deterministic training; stored calibration set and envelope | `CalibrationTooSmall { n }` | FLX-O-ROM-2 | 4 |
| Surrogate prediction | `Estimated { confidence, scope: Marginal }`; weighted conformal in loops | `Untrusted { reason }` outside the envelope | FLX-O-ROM-2 | 4 |
| Per-prediction bound | Projection, residual, equilibrated estimate | `NotQuantified`, so `SignOff` needs a confirming solve | FLX-O-ROM-2 | 4 |

## Execution

A solve is a set of Kiln nodes demanded by an Evaluation. Kiln owns scheduling, caching and budgets; Flux supplies cost models, safe points and step checkpoints.

- **Placement.** The plan picks class and place (local CPU or GPU, team server, cloud) from memory and time estimates, never moving work to the cloud without permission; `PlanError::ExceedsLocal { memory, time }` suggests remote evaluation or lower fidelity. Browser evaluations above 512 MiB run in a heavy worker, larger ones remotely.
- **Aborts.** Budget exhaustion, cancellation and device loss are Aborts, never cached. Completed adaptive iterations remain valid results, and step checkpoints, keyed by (`OpKey`, step), let a later Evaluation resume to bit-identical results.
- **Safe points.** Ends of time steps, adaptive and optimizer iterations, and Krylov restarts; `OpCx::checkpoint` is polled at least every 10 ms, so cancellation lands within 100 ms (target).
- **GPU dispatch.** PLT's rule applies: at most 4 ms per dispatch while any window renders interactively, 16 ms while views are idle, and 100 ms only in headless processes.
- **Trust.** Native FMUs and GPL tools run as External Ops on untrusted-evaluation workers. A `SignOff` check accepts a cached solve only when two trusted builders produced the same `ObjectId`, and Kiln's cost model counts the second solve (contract section 7.8).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Placement and cost models | Plan-chosen class and place; `OpImpl::cost` estimates | `PlanError::ExceedsLocal { memory, time }` | FLX-O-EXEC-1 | 1 |
| Aborts and resumption | Budget, cancellation and device loss abort without caching; step checkpoints resume | Abort propagates to dependents | FLX-O-EXEC-1 | 1 |
| Cancellation latency | Safe points polled every 10 ms | Missed latency target fails the oracle | FLX-O-EXEC-2 | 1 |
| Remote and browser execution | Heavy worker above 512 MiB; remote above measured thresholds | `PlanError::ExceedsLocal` in the browser suggests remote evaluation | FLX-O-EXEC-1 | 1 |

## Post-processing and display

Probes are regularized goals (`f.at(x, smooth: ρ)`); line and surface probes return Fields. Reactions use the variationally consistent residual method; as bounded linear functionals they can carry `Guaranteed` bounds. Derived quantities are von Mises, principal and Tresca stresses, heat flux, safety factor, and fatigue damage from COV's models. Recovered display stresses use patch recovery or L² projection and are `Indicator`, for display only.

`std::sim::report` builds reports as Ingot data: plan explanation, budgets per checked quantity, validity zones, singular sets, convergence histories, outcomes with margins and cost. ECO's `io/` owns Field export encodings.

**Decision D-FLX-22:** Fields paint on the true geometry. Where the GPU tier allows, per-pixel WGSL evaluators read coefficient buffers on the UI process's device. Elsewhere, adaptively refined vertex samples on the `DisplayPackage` carry a stated interpolation error. Probes always sample exactly on the CPU, and display data never feed checks. *Why:* linear interpolation of high-order solutions misplaces peaks (D-UIX-13), and display-only GPU work on the UI's device avoids a round trip through host memory (R6-16). *Rejected:* rendering the analysis mesh, which shows octree artifacts and ties display to the discretization. (revised in round 2)

Evaluators cover `Discrete` Fields of every element family, splines, `SparseGrid`, `Analytic` and `Reduced` Fields; `PointCloud` and `Surrogate` Fields use vertex samples. Payloads carry quantized values with their error, error magnitudes, validity and singular masks, deformations, volume bricks and glyphs.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Probes and derived quantities | Regularized point, line and surface probes; standard stress, thermal and fatigue quantities | `Undecided { SingularPoint }` near flagged sets | FLX-O-POST-1 | 1 |
| Reactions | Variationally consistent residual reactions with `Guaranteed` resultant bounds where proven | None | FLX-O-POST-1 | 1 |
| Reports | `std::sim::report` data for UI and CI | Missing budgets are listed in the report | FLX-O-POST-1 | 1 |
| Display evaluators | WGSL per-pixel evaluators on the UI's device | Tier without compute uses vertex samples, stated | FLX-O-POST-2 | 1 |
| Display samples | Adaptive vertex samples on `DisplayPackage` with interpolation error | None | FLX-O-POST-2 | 1 |
| Isosurfaces, slices, streamlines, response functions, mode shapes | Display geometry, plus Implicit Bodies for geometry use | Streamline error above tolerance refines the step | FLX-O-POST-1 | 2 |

## State of the art

Figures are targets on contract section 13.3's reference laptop and one server per GPU vendor.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Weak-form language | UFL | DOLFINx (LGPL-3.0 or later); Firedrake [unverified: licence] | UFL semantics in Ingot with units and geometry measures | Every FEniCS and Firedrake demo expressible |
| Form compilation | TSFC; libCEED operator split | FFCx, TSFC, MFEM | Native compiler to the kernel IR | Under 200 ms for p = 2 elasticity |
| High-order operators | Sum-factorized partial assembly [Kolev et al.; Fischer et al.; deal.II] | MFEM (BSD) with libCEED [unverified: licence] | Own canonical kernels | Contract section 13.3 CEED rows |
| Immersed discretization | CutFEM, shifted boundary, Saye quadrature | ngsxfem, GridapEmbedded [unverified] | Octree with three treatments | MMS rates p = 1 to 6; 1,000-shift iterations |
| Dimensional reduction | Shells, Timoshenko and Vlasov beams, Nitsche coupling [unverified: reference] | Commercial shell and beam solvers [unverified] | Per-region marking, patch model error | Frames and shells against 3D references |
| A posteriori estimation | Equilibrated flux [Smears and Vohralík]; DWR [Becker and Rannacher] | deal.II and MFEM residual estimators | `Guaranteed` where proven; calibrated DWR | Effectivity; undershoot at most 1% |
| Solution verification | Grid convergence index [Roache, via NASA] | — | `std::sim::solution_verification` | GCI bands on benchmark flows |
| Multigrid | Global coarsening [Munch et al.]; low-order-refined de Rham [Pazner et al.] | hypre (Apache-2.0 OR MIT), MFEM | Own multigrid and deterministic AMG | Within 1.5× of MFEM with hypre |
| Navier–Stokes preconditioning | Augmented Lagrangian [Farrell, Mitchell, Wechsung]; PCD | Firedrake [unverified] | PCD, LSC, augmented Lagrangian, dual splitting | Cavity iterations within 2× for Re = 10 to 1,000 |
| Sparse direct | Supernodal with nested dissection; block-triangular LU | CHOLMOD, KLU (SuiteSparse 7.14.1) [unverified: licences]; MUMPS | Canonical solvers in `linalg` | Within 2× of single-threaded CHOLMOD (canonical), multithreaded (`CpuIsa`) |
| Mixed precision | GMRES refinement [Carson and Higham] | — | `f32` factors, `f64` refinement; CPU certification | Full `f64` accuracy |
| Reproducible reductions | Binned summation [ReproBLAS] | ReproBLAS | `det_sum`, `exact_sum` across ranks | CG overhead at most 1.05× |
| Time integration | Adaptive BDF, IMEX Runge–Kutta, generalized-α | SUNDIALS (BSD-3-Clause) | Native differentiable integrators | Within 1.5× of SUNDIALS |
| Eigenvalues | Krylov–Schur, LOBPCG, contour integrals | SLEPc, ARPACK-ng [unverified: licences] | Native | NAFEMS free vibration; within 1.5× of SLEPc |
| Lumped networks | Pantelides with dummy derivatives | OpenModelica [unverified: licence]; SUNDIALS IDA | Native compiler and DAE solver | Pendulum, clutch, diode bridge; within 2× of IDA |
| Multibody dynamics | Lie group generalized-α [Brüls, Cardona, Arnold] | Project Chrono (BSD-3-Clause) | Native, Network-driven joints | Second-order convergence; within 1.5× of Chrono |
| Rods | Cosserat rods [Gazzola et al.] | PyElastica (MIT) | Native | Elastica and helical buckling |
| Explicit dynamics | Diagonal-mass spectral and spline elements | LS-DYNA [unverified] | Native; GPU at `Interactive` | 10⁷ element cycles per second on the reference CPU |
| Full-wave electromagnetics | Nédélec FEM, wave ports, fast sweep | Palace [unverified: licence] | Native, PML in forms | S-parameters against Palace |
| FDTD; boundary elements | Conformal Yee; fast-multipole Galerkin BEM | Meep (GPL), openEMS; Bempp-cl, bempp-rs (BSD-3-Clause) [unverified except bempp-rs] | Native FDTD; bempp-rs | Cavity and Mie benchmarks |
| Lattice Boltzmann, particles | Cumulant collision; δ-SPH, MLS-MPM, DEM, peridynamics [unverified] | FluidX3D, DualSPHysics; LAMMPS (GPL) [unverified] | Native on general operations | Schäfer–Turek, dam break [unverified: references] |
| Adjoints | Form-level derivation [Farrell et al.]; CAMS [Zhang and Constantinescu] | pyadjoint [unverified: licence]; JAX-FEM (GPL-3.0) | Native through Kiln | Taylor order 2; steady adjoint at most 1.2× forward |
| Topology optimization | Giga-voxel density methods [Aage et al.] | PETSc-based TopOpt [unverified] | Native, canonical at `SignOff` | 10⁸ elements on a 64-core server |
| Reduced models | POD with hyper-reduction; certified reduced basis [unverified] | pyMOR, RBniCS [unverified] | Native | 100× speedup at under 1% error |
| Surrogates | Weighted conformal [Tibshirani et al.]; coverage limits [Barber et al.] | PhysicsNeMo [unverified: licence] | Marginal coverage; per-prediction bounds | No adversarial false `SignOff` pass |
| Uncertainty | MLMC [Giles]; sparse PCE; Shapley effects | Dakota, OpenTURNS [unverified] | Native `std::uq` | Ishigami; MLMC cost exponent |
| Batteries | Doyle–Fuller–Newman | PyBaMM (BSD-3-Clause) | Parameter-domain forms | Agreement with PyBaMM |
| Co-simulation | FMI 3.0.2, SSP 2.0.1 | FMPy, OMSimulator [unverified] | Native runtime | Reference FMUs on every Tier 1 OS |

Linked dependencies are MIT, Apache-2.0 or BSD: faer 0.24.4 (MIT, `CpuIsa` only), wgpu 30.0.1 (MIT OR Apache-2.0), bempp-rs 0.2.0 (BSD-3-Clause), hypre and PETSc as bridges, and CubeCL (MIT OR Apache-2.0) if adopted at the phase 4 gate. LGPL code (preCICE, DOLFINx, NGSolve, Mmg) serves only as external tools or references, and GPL code (JAX-FEM, Meep, Elmer, OpenFOAM, LAMMPS) only as External Ops or oracles (contract section 7.7). Algoim states no licence, so Anvil implements Saye's papers. PLT's dependency register names an owner and a fork plan for faer, wgpu and CubeCL (R6-30).

## Platform notes

| Platform | Risk | Decision |
| --- | --- | --- |
| Every Tier 1 CPU | SIMD width and FMA availability differ | Canonical lane order and no FMA in `CpuCanonical`; FMA `CpuIsa` variants for `Preview` and `Interactive` |
| Every CPU | Foreign code changes the floating-point state | Checked at start and end; Abort and rerun |
| macOS (Metal), browsers (WebGPU) | No `f64`; WGSL may fuse, reassociate, flush and assume finite values | `f32` `ClassExact` at `Interactive`; CPU certification for `SignOff`; non-finite detection after readback |
| Browsers on G3 (WebGL2) | No compute shaders | Every solve on the Wasm CPU path; same features, declared slower |
| Browsers | Memory never shrinks; 1.5 GiB worker cap | Heavy worker above 512 MiB, remote beyond; `Interactive` targets 2 s (WebGPU) and 6 s (CPU-only) |
| Desktops sharing one GPU with the renderer | Watchdog resets and renderer stalls | PLT's dispatch rule (4 ms, 16 ms, 100 ms) |
| Linux servers | `f64` GPUs | Vulkan `SHADER_F64` from phase 3; CUDA or HIP reconsidered at the phase 4 gate |
| Tier 1 preview targets | Preview in phase 1 | Determinism and golden checks run headless |
| iPadOS and Android tablets (Tier 2) | Memory, thermals, Wasm in WebKit | `Preview` and small `Interactive` solves locally; the rest remote |
| Air-gapped installs | No cloud workers | User forms compile locally; External Ops need a local Linux worker |

## Interfaces with other subsystems

### What Flux provides

| To | Provides | Types |
| --- | --- | --- |
| ING | Spaces, measures, `solve`, `modes`, `minimize`, `continue_in`, plans, form checks, regularized reductions | `Field<D, V>`, `Expr<T>`, `ErrorBudget`, `Approx` |
| ANV | `field` and `kernels` below Anvil; `Sampler`s with gradient bounds; `geometry_density`; marking, sizing and metric Fields | `Field` |
| KLN | Operations with grades, fidelity maps, cost models, safe points, derivatives, step checkpoints | `OpImpl`, `Differentiable` |
| COV | Forms, solvers, estimators, regime-variable Fields, zone evaluation, D-COV-11 operations, calibration corpus | `Field`, `ValidityEnvelope` |
| MEC | Multibody, rods, laminated shells, bolted-joint forms, influence coefficients, deformed-shape Fields | `Field`, `Assembly` |
| MFG | Element activation, free-surface flow, Hele-Shaw, thermo-elasto-plasticity, constrained topology optimization | `Field`, `Body` |
| ELX | Network compiler, DAE solver, block-triangular LU, electromagnetic solvers, layered sheets, FFT Poisson, kernel IR for Verilog-A, FMI runtime | `Network`, `Field` |
| AGT and `api` | Evaluate and Inspect methods; plan explanations; cost estimates | `SolvePlan` |
| UIX | WGSL evaluators, vertex samples with error, masks, reports | `Field` |
| PLT | No-FMA penalties per kernel family; GPU paths; determinism corpora | `GpuPath` |

### What Flux requires

| From | Requirement |
| --- | --- |
| ING | Product-domain `Field` types; `Complex<Q>`, `im`, `.absolute()`, `select`; record results; `Approx`, `Truth` and the decision rule; `goals:`; parameter-domain syntax; `param` marks |
| ANV | `GeometryQuery`; `mid_surface`, `member_axes`, strut graphs; meshing and adaptation; `shape_velocity` with `TopologyChange`; `implicit_from_field`; `common_refinement`; `DisplayPackage` back-references; its two stage budgets |
| KLN | `Differentiable` in `base`; reverse traversal; the `Checkpoint` retention class keyed by (`OpKey`, step); fidelity-keyed nodes; Aborts; `OpCx`; two trusted builders at `SignOff` |
| PLT | `detmath`; `det_sum`, `det_reduce`, `exact_sum`; `linalg` (joint); `gpu` with known-answer tests and CPU fallbacks; the dispatch rule; the class enum; the browser memory table |
| COV | Regime functions and envelopes; constitutive models with tangents; turbulence, fatigue, fracture and damage models; model-class to calibration-class mapping |
| MEC | Typed joints, redundancy reports, bounded mass properties, contact candidates, preload, laminates, default distributions, skin-model samples |
| MFG | Manufacturing-constraint forms; process profiles with Cp and Cpk; inherent-strain data |
| ELX | The `network { … }` builder, element libraries, the Verilog-A front end |
| ECO | Registry hosting for `crucible:material/constitutive` and `crucible:physics/solver`; FMU and SSP packaging; Field encodings in `io/` |

## Oracles

Oracles live in `oracles/flux/`; held-out solutions, calibration samples and references stay outside the agent-readable tree.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| FLX-O-ARCH-1 | std physics rebuilt in a user namespace; a solver Wasm component | Bit-identical to std |
| FLX-O-ARCH-2 | Operations called from Wasm are recorded dependencies | A version change invalidates the caller; replay identical |
| FLX-O-ARCH-3 | External Op solvers | Host class or `Unverified`; no attestation; references matched |
| FLX-O-FIELD-1 | Sampling across representations | Reported bound at least the true error at every sample; gradient bounds hold |
| FLX-O-FIELD-2 | Transfer and projection | Integrals conserved to solver tolerance; reported transfer error at least the measured one |
| FLX-O-FIELD-3 | Extremum enclosures, region extraction | Enclosures contain the true extremum; extracted Body bounds hold under dense sampling |
| FLX-O-FIELD-4 | Geometry-driving Fields | Anvil's reported bound at least the measured deviation |
| FLX-O-FIELD-5 | Canonical storage | decode(encode(v)) equals v bit for bit; reloaded inputs give identical dependents |
| FLX-O-FIELD-6 | Label invariance | Re-randomized names leave every Field and check value identical on every golden product |
| FLX-O-ERR-1 | Equilibrated energy bounds | `Guaranteed` effectivity never below 1, at most 1.5 (target) |
| FLX-O-ERR-2 | Bounded linear goal bounds | Bound at least the true error in every case |
| FLX-O-ERR-3 | Calibrated DWR on regularized goals | Bound at least the true error in at least 99% of held-out cases per class |
| FLX-O-ERR-4 | Singular-set detection | Seeded singular edges all flagged, smooth controls none |
| FLX-O-ERR-5 | Calibration tables | Every entry has at least 300 held-out samples, zero undershoots |
| FLX-O-ERR-6 | Temporal estimates over 100 periods of an undamped oscillator and a wave | Adjoint-weighted estimate at least the true error |
| FLX-O-ERR-7 | `Preview` results | Never `Pass` or `Fail`; never in the shared cache |
| FLX-O-ERR-8 | Solution verification on benchmark flows | GCI bands contain the reference in at least 95% of cases (target) |
| FLX-O-ERR-9 | Validity zones | Match COV's labelled cases; `Refuse` yields `Error(Failure)` |
| FLX-O-ERR-10 | Cross-class agreement | \|q_A − q_B\| ≤ E_A + E_B on the determinism corpus, ratio reported |
| FLX-O-FORM-1 | Static form checks | 100 textbook forms pass; seeded errors fail with the right code |
| FLX-O-FORM-2 | Symbolic derivatives | Taylor order 2 ± 0.1 for every operator |
| FLX-O-FORM-3 | `local_solve` and Wasm constitutive tangents | Taylor tests pass; quadratic global Newton convergence on a plasticity benchmark |
| FLX-O-FORM-4 | UFL coverage | Every FEniCS and Firedrake demo expressible (target 100%) |
| FLX-O-FORM-5 | Parameter-domain forms | P2D DFN agrees with PyBaMM within stated tolerance on shared parameter sets |
| FLX-O-KER-1 | CEED bake-off problems plus immersed elasticity | Under 10⁻¹² from assembled references; section 13.3 throughput |
| FLX-O-KER-2 | No-FMA penalty, `CpuIsa` variants | Penalty published per degree (p = 1 to 8) and ISA; variants within declared tolerance of canonical |
| FLX-O-KER-3 | CPU kernel determinism | Ahead-of-time and Wasm kernels bit-identical across threads, ISAs and targets |
| FLX-O-KER-4 | GPU paths | Known-answer tests run; injected NaN detected; CPU agreement within tolerance |
| FLX-O-KER-5 | Floating-point environment | A planted flush-to-zero library causes Abort and rerun |
| FLX-O-KER-6 | User-form speed | Within 2× of ahead-of-time kernels on AVX2, 4× on AVX-512 (targets) |
| FLX-O-PLAN-1 | Plans and overrides | Same plan in every class; old plan versions reproduce old results |
| FLX-O-PLAN-2 | Reduction marking | Known plates, frames and lattices marked as expected |
| FLX-O-PLAN-3 | Mixed-dimensional couplings | Patch tests pass; coupled models match 3D references within the reported budget |
| FLX-O-PLAN-4 | Reduction model error | Estimate at least the measured 3D-versus-reduced difference on held-out frames and shells |
| FLX-O-DISC-1 | Manufactured solutions for every method, element, degree and shape | Rate within 0.1 of theory over three refinements, stopping below 10³ times round-off |
| FLX-O-DISC-2 | Immersed iterations | Within 1.5× across 1,000 random geometry shifts for p = 1 to 4 |
| FLX-O-DISC-3 | Shifted boundary with traction on curved elasticity | Boundary-stress order at least 2 at p = 2, else cut cells at `Interactive` |
| FLX-O-DISC-4 | Patch tests | Fitted, immersed and spline tests exact to solver tolerance; finite cell within O(α) |
| FLX-O-DISC-5 | NAFEMS P18 static, thermal and free-vibration benchmarks | Within 1% of the target value at `SignOff` |
| FLX-O-DISC-6 | Shells, beams, layered sheets | Within published tolerance of converged references per theory |
| FLX-O-DISC-7 | Explicit dynamics | Energy error under 1%; step independent of cut fraction where enabled |
| FLX-O-DISC-8 | Electromagnetics | Cavity modes, S-parameters against Palace, Mie scattering, cut-independent FDTD step |
| FLX-O-DISC-9 | Magnetodynamics with motion | Torque and loss against benchmark machines [unverified: set]; divergence-free source currents |
| FLX-O-DISC-10 | Finite volume and free surfaces | Per-cell and filled-volume conservation to solver tolerance |
| FLX-O-DISC-11 | General operations and particles | Thread-count independence; Philox references; dam break and granular collapse |
| FLX-O-DISC-12 | Boundary elements | Sphere scattering against the Mie series; near-linear scaling |
| FLX-O-MESH-1 | Adaptivity | Optimal rates on L-shape and Fichera-corner problems; stagnation reported near singularities |
| FLX-O-MESH-2 | Solution transfer | Conservation to solver tolerance; reported error at least the measured one |
| FLX-O-MESH-3 | `Interactive` stage budgets | Each stage within budget on GP1, GP2 and GP5 benchmarks (targets) |
| FLX-O-SOLVE-1 | Direct solvers | Round-off backward error; identical results under two cache-size settings and any thread count |
| FLX-O-SOLVE-2 | Multigrid and AMG | h- and p-independent iterations on BP3 and BP5; aggregates independent of threads and ranks |
| FLX-O-SOLVE-3 | Navier–Stokes preconditioners | Cavity iterations within 2× from Re = 10 to 1,000 |
| FLX-O-SOLVE-4 | Nonlinear solvers and bifurcations | Perfect column returns `Bifurcation` at the Euler load; imperfect one follows its branch |
| FLX-O-SOLVE-5 | Time integrators | Observed orders match theory; events at identical simulated times across classes |
| FLX-O-SOLVE-6 | Eigen-solvers | NAFEMS free vibration; identical degenerate-subspace normalization |
| FLX-O-SOLVE-7 | Contact | Hertz contact against the analytic solution; unestimated penalty results never support `SignOff` |
| FLX-O-SOLVE-8 | GPU solves with CPU certification | Certified verdicts equal canonical verdicts; stalls fall back |
| FLX-O-NET-1 | Network compilation | Index-3 pendulum reduced; clutch and ideal-diode bridge reinitialize consistently |
| FLX-O-NET-2 | DAE integration | RLC and drivetrain analytic solutions; circuit references from ngspice as an External Op |
| FLX-O-NET-3 | Block-triangular LU | Refactorization bit-identical to fresh factorization; round-off backward error |
| FLX-O-MBD-1 | Multibody dynamics | Second-order convergence on heavy top and slider–crank; redundancy reported |
| FLX-O-MBD-2 | Rods | Elastica, helical buckling and hanging-cable references |
| FLX-O-COUP-1 | Coupling and activation | Partitioned and monolithic agree within combined budgets; Turek–Hron FSI benchmarks [unverified: references] |
| FLX-O-COUP-2 | Homogenization and lattices | Laminate bounds and known tensors; beam-lattice and localized stresses against full-resolution solids |
| FLX-O-COUP-3 | FMI and SSP | Reference FMUs on every Tier 1 OS; SSP round trips; master error order |
| FLX-O-OPT-1 | Derivatives | Taylor order 2 ± 0.1 on frozen discretizations for every `Differentiable` operation |
| FLX-O-OPT-2 | Topology optimization | MBB beam and 3D cantilever compliance within 2% of published values (target) |
| FLX-O-OPT-3 | Adjoints and checkpoints | Steady adjoint at most 1.2× a forward solve (target); resumed adjoints bit-identical |
| FLX-O-UQ-1 | Sensitivity and rare events | Ishigami indices; correlated Shapley benchmark; known failure probabilities |
| FLX-O-UQ-2 | Multilevel Monte Carlo | Cost exponent within 0.2 of theory |
| FLX-O-UQ-3 | Worst-case propagation | Bounds contain sampled extremes on mildly nonlinear cases; `NonlinearResponse` on strongly nonlinear ones |
| FLX-O-ROM-1 | Reduced models | Certified bounds hold; 100× online speedup at under 1% error (target); outside-envelope queries fail |
| FLX-O-ROM-2 | Surrogates | Coverage at least nominal; an adversarial optimizer finds no `SignOff` `Pass` the full solve fails |
| FLX-O-EXEC-1 | Aborts and resumption | Injected faults never change cached values; resumed solves bit-identical |
| FLX-O-EXEC-2 | Cancellation | Within 100 ms (target) |
| FLX-O-POST-1 | Post-processing | Reactions balance loads to solver tolerance; probes exact on analytic Fields; reports complete |
| FLX-O-POST-2 | Display | Values within the stated interpolation error of exact CPU samples |

## Phasing

| Phase | Flux contribution to the gate |
| --- | --- |
| 0 | Determinism suite green for Flux kernels on the representative set; unit errors in forms fail to compile; kernel IR v0 frozen at month 6; H¹ elements, CG and manufactured-solution tests by month 12; CEED baselines, no-FMA penalties and the calibration rule published; no operation name or WIT package frozen before the Flux rename |
| 1 | GP1: immersed elasticity (shifted boundary at `Interactive`, CutFEM at `SignOff`), calibrated DWR on regularized goals, singular sets, p-multigrid over AMG, Lanczos and LOBPCG. GP2: density topology optimization, steady adjoints, homogenization, beam-lattice verification with strut buckling, `geometry_density`, inherent-strain activation. WGSL `Interactive` elasticity within stage budgets. Deferred per contract section 13.2: guaranteed estimators on cut cells, GPU `SignOff` paths, CUDA or HIP |
| 2 | GP3: fitted tetrahedra with mortar contact, rigid multibody, drivetrain Networks, transient solvers and adjoints, modal reduction. GP4: beams, shells, mixed-dimensional couplings, thermo-elasto-plasticity with activation for weld distortion. Also GPU solves certified on the CPU and worst-case tolerance propagation |
| 3 | GP5: free-surface filling with fibre-orientation transport, warpage, explicit dynamics for the drop test, conjugate heat transfer, electro-thermal boards, circuit DAEs, FDTD, FMI and SSP, statistical uncertainty |
| 4 | GP6: Navier–Stokes preconditioners and lattice Boltzmann, fluid–structure interaction, magnetodynamics with motion, full-wave antenna FEM, DFN batteries, flexible multibody and rods, surrogates with per-prediction bounds, and distributed BDDC. A CUDA or HIP back end is reconsidered at this gate |
| 5 and later | GP7 MEMS (piezoelectric coupling, pull-in bifurcations); GP8 steel platform (frames and the IFC structural check); GP9 crash box (explicit dynamics with erosion); particle methods; FE² |

## Open questions

1. **Calibration classes.** Can the corpus supply 300 held-out samples for every class the phase 1 checks need? FLX proposes classes; COV and MEC confirm.
2. **`Interactive` boundary treatment.** FLX-O-DISC-3 decides it in phase 1.
3. **Guaranteed bounds on cut cells.** Extending equilibrated proofs to hanging nodes and cut cells is research, deferred past phase 1.
4. **No-FMA penalties.** Phase 0 measurements decide which kernel families ship `CpuIsa` variants.
5. **Geometry-priority AMG.** Canonical-number aggregation may cost iterations; phase 1 measures it.
6. **Canonical parallel factorization.** Upstream acceptance by faer; distance to CHOLMOD.
7. **Surrogate training on GPUs.** Deterministic GPU training may be too slow; the fallback is CPU training.
8. **Smoothing radius.** The default ρ (1% of region diameter) needs review with COV and MEC against critical-distance practice.
9. **Junction length.** The two-thickness solid zone at mixed-dimensional junctions needs validation (FLX-O-PLAN-3).
10. **Findings declined in part.**
    - R1-43: routine `SignOff` in `CpuIsa` with FMA is declined, because contract section 7.3 requires canonical recomputation for `SignOff`.
    - R1-21: GPU element-cycle targets apply at `Interactive` only, because explicit trajectories have no cheap canonical certificate.
    - R1-16: morphing reduced models arrive in phase 3, with `Proxy` results before then.

## Contract change requests

- **CCR-FLX-8. A `regularization` error source.** Add `regularization` to `ErrorSource` in contract section 5. *Reason:* section 7.1 requires the regularization error of peak and pointwise goals in the budget, and no listed source fits it.
- **CCR-FLX-9. One physics phase table.** Add a contract-owned table of phases for capabilities that several tabs share, which each tab cites (R1-35). *Reason:* phases for modal analysis, inherent strain, DFN, fibre orientation, fill tracking, high-pressure die casting, stability lobes and fitted tetrahedra drifted across tabs. This tab uses phase 1 for Lanczos, LOBPCG and inherent-strain activation; phase 2 for fitted tetrahedral FEM; phase 3 for level-set filling and fibre-orientation transport; and phase 4 for DFN.

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
