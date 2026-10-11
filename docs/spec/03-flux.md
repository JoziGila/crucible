# Flux physics engine core

Flux compiles physics written as weak forms in Ingot into deterministic CPU and GPU kernels, solves them with current best-practice discretizations and solvers, and returns Fields. A solve plan chooses the discretization (immersed by default, so most users never mesh), and every result Field carries an error estimate that lets each check pass, fail or report undecided.

## Scope and architecture

### What Flux core owns

Flux core is the machinery: the `Field` type, the weak-form language, the form compiler and kernels, discretizations, solvers, coupling, gradients, uncertainty quantification (UQ), fidelity modes, execution and post-processing. The physics coverage and materials tab (COV) builds physics domains, constitutive models and validity envelopes on this machinery. "Limits of the machinery" states plainly what Flux cannot do.

Flux follows the contract's layering (D-ARCH-1). Numerical primitives are versioned operations in native Rust. Orchestration, such as optimization loops, design of experiments and report assembly, lives in the Ingot packages `std::flux`, `std::opt` and `std::uq`; user solvers and constitutive models arrive as Wasm components.

### Crates

| Crate | Contents | `unsafe` | Depends on |
| --- | --- | --- | --- |
| `flux-field` | `Field`, representations, the `Sampler` trait, representation-independent operations, storage layout | forbidden | `ingot-types`, `anvil-geom`, `anvil-topo`, `cas` |
| `flux-forms` | Weak-form IR, typing, symbolic differentiation, element library, form compiler front and middle end | forbidden | `flux-field`, `ingot-ir` |
| `flux-kernels` | Kernel IR, CPU SIMD backend, wgpu backend, CubeCL backend, reproducible reductions, deterministic math library | allowed (SIMD, GPU) | `flux-forms` |
| `flux-solve` | Discretizations, assembly, linear, nonlinear, time and eigen solvers, estimators, adaptivity, `Sampler` implementations for solver-produced Fields | forbidden | `flux-kernels`, `anvil-ops`, `anvil-mesh`, `faer` |
| `flux-couple` | Partitioned coupling, homogenization, FMI and SSP co-simulation master | forbidden | `flux-solve` |
| `flux-opt` | Adjoints, checkpointing, topology and shape optimization, UQ, design of experiments, reduced-order models, surrogates | forbidden | `flux-solve`, `flux-couple` |
| `flux-bridges` | Optional FFI to PETSc, hypre and external direct solvers; never in Wasm builds | allowed (FFI) | `flux-solve` |

**Decision D-FLX-1:** Split Flux into seven crates, place `flux-field` below `anvil-ops`, `anvil-mesh` and `anvil-implicit`, and confine all `unsafe` code to `flux-kernels` and `flux-bridges`. *Why:* Anvil operations consume Fields, so the Field type must sit below them to avoid a dependency cycle, and the contract allows `unsafe` only in SIMD, GPU and FFI crates. `flux-solve` implements `Sampler` for the Fields it produces, and Kiln hands that implementation to Anvil operations, so Anvil never depends on the solver. *Rejected:* the two crates named in the contract alone, which would make Anvil depend on the solver or mix `unsafe` kernels into safe crates (CCR-FLX-6).

### Operations

Flux exposes about 55 operations, each with a behavior version written `flux::solve_linear@1`. Ingot features in `std` orchestrate them; nothing in the UI or `api` reaches Flux by another path.

| Group | Operations |
| --- | --- |
| Field | `field_sample`, `field_transfer`, `field_project`, `field_recover`, `field_reduce`, `field_region`, `field_compare` |
| Forms and plans | `compile_form`, `plan` |
| Discretization | `discretize`, `cut_quadrature`, `assemble`, `setup_preconditioner` |
| Solve | `solve_linear`, `solve_nonlinear`, `solve_transient`, `solve_eigen`, `solve_harmonic` |
| Error and adaptivity | `estimate_error`, `estimate_goal`, `mark`, `adapt` |
| Coupling | `couple`, `homogenize`, `cosimulate`, `fmu_export` |
| Gradients and optimization | `tangent`, `adjoint`, `shape_gradient`, `filter_density`, `project_density`, `mma_step`, `lbfgs_step`, `sqp_step`, `cmaes_step` |
| UQ and design of experiments | `sample_plan`, `pce_fit`, `sobol_indices`, `mlmc_estimate` |
| Reduced models and surrogates | `modal_basis`, `craig_bampton`, `pod_basis`, `hyperreduce`, `rom_build`, `rom_eval`, `surrogate_train`, `surrogate_calibrate`, `surrogate_eval` |
| Post-processing | `probe`, `reaction`, `isosurface`, `streamlines`, `display_tiles`, `report_data` |

[[DIAGRAM: Flux pipeline. Left to right: "Ingot weak form" → "flux-forms: typing, units, symbolic derivatives" → "plan: SolvePlan (method, spaces, quadrature, assembly level, solver stack, precision, determinism)" → "discretize: fitted mesh from Anvil or immersed octree with Anvil geometry queries" → "compile_form: kernel IR → CPU SIMD / WGSL / CubeCL" → "assemble + solve (Kiln Ops, cached in CAS)" → "estimate_error ⇄ adapt loop" → "Fields with ErrorBudget and ValidityReport". Outputs fan out to "checks: Pass / Fail / Undecided", "display_tiles → UI", "Field-driven Anvil operations". A dashed arrow labelled "adjoint" runs right to left along the solve Ops.]]

## The Field type

### Definition

A `Field<D, V, A>` is a physical quantity of value type `V` over a domain of kind `D`, with optional parameter axes `A`. The contract's `Field<Domain, V>` is the case `A = ()`. Fields are immutable values: every operation returns a new Field, and Kiln caches it by content hash.

| Domain kind `D` | Meaning | Example |
| --- | --- | --- |
| `Body` | Volume of a Body in any representation | Relative density of an implicit lattice |
| `Part` | Volume of a Part, with its boundary reachable by restriction | Von Mises stress |
| `Assembly` | Union of Instances; per-Instance data in each Instance's placement | Temperature across an enclosure |
| `Faces`, `Edges`, `Vertices` | B-rep entity sets resolved by a `Query` | Pressure load, weld heat input, bolt preload points |
| `Region` | A sub-volume given by a `Query` or an Implicit Body | Heated zone, design space |
| `Space` | A bounded box of ambient space, not attached to a Body | Wind field, imported CFD data |

A domain value references geometry by the Body's content hash plus `EntityId`s, never by pointer. A Field built on one version of a Part cannot be used on another version: the attempt returns `FieldError::StaleDomain { field_body, current_body }`, suggesting `field_transfer`.

### Value types and units

`V` is a `Quantity<D>` scalar, a 3-vector, a symmetric or full second-order tensor, a fourth-order tensor with declared symmetries, a complex variant of these for frequency-domain results, a `Rotation`, a `Label` (integer region or state), or `Validity`. Units are checked at compile time and erased at runtime, as the contract requires. Canonical values are stored as SI base-unit `f64`; `f32` copies exist only on GPUs and for display.

Every value type declares how it transforms under a rigid `Transform`: scalars are invariant, vectors rotate, tensors transform as R·T·Rᵀ, and pseudo-vectors pick up the determinant sign. Instance placement in an Assembly therefore applies the right rule without user code. A value type that cannot be transformed (for example a `Label`) is copied unchanged.

### Parameter axes

Results that vary over time, frequency, mode number, load case, random sample or design parameter are still Fields. They carry axes instead of being separate container types.

| Axis | Coordinates | Default interpolation between coordinates |
| --- | --- | --- |
| `Time` | Solver steps, adaptive | Dense output of the time integrator, with its temporal error estimate |
| `Frequency` | Sweep points, or a reduced frequency model | Krylov moment-matching reduced model when built, else interpolation with stated error |
| `Mode` | Mode index with eigenvalue | None (discrete) |
| `LoadCase` | Named cases | None; linear combinations allowed for linear problems |
| `Sample` | UQ samples with weights | None; statistics by reduction |
| `Parameter<P>` | Design-of-experiments points or a reduced-model parameter box | Reduced-model or surrogate evaluation when available, else none |

Ingot writes axes as extra type arguments: `Field<Part, Temperature, Time>`. Slicing and reductions keep everything a Field: `hist.temperature.at(t: 2.5s)`, `stress.max_over(LoadCase)`, `peak.quantile(0.99, over: Sample)`.

**Decision D-FLX-2:** Represent time series, frequency sweeps, mode sets, load cases, ensembles and parametric results as Fields with parameter axes. *Why:* one type keeps libraries consuming "only Body, Field and plain values" (principle 3), and axis reductions compose with every other Field operation. *Rejected:* separate `TimeSeries`, `ModeSet` and `Ensemble` types, which would be parallel abstractions with duplicated operations (CCR-FLX-2).

### Representations

| Representation | Holds | Sampling error reported | Typical producer |
| --- | --- | --- | --- |
| `Analytic` | A compiled Ingot expression of position, axes and other Fields | Zero beyond floating point | Loads, boundary data, user formulas, lazy Field arithmetic |
| `Discrete` | Coefficients in a function space: nodal Lagrange values, edge and face moments, modal DG coefficients, NURBS control values | None for the discrete function; discretization error is carried separately | FEM, IGA, DG and finite volume solves |
| `QuadraturePoint` | Values at the quadrature points of a discretization | Recovery error when sampled between points | Plasticity state, topology-optimization densities |
| `PerEntity` | One value per `EntityId` (face, edge, cell, Part) | None (piecewise constant by definition) | Per-face constants, contact status, Part-level results |
| `SparseGrid` | Values on an adaptive sparse block grid, with dense grids as a special case; trilinear or tricubic interpolation | Estimate from local second differences | Lattice Boltzmann, FDTD, CT scans, implicit geometry |
| `PointCloud` | Values at scattered points with a reconstruction rule (moving least squares, SPH kernel, radial basis functions) | Leave-one-out or kernel-moment estimate | DEM, SPH and MPM particles, sensor data |
| `Reduced` | A reduced basis (a `Discrete` Field with a `Mode` or `Parameter` axis) times a coefficient model | Certified or residual-based bound | Modal, POD and reduced-basis models |
| `Surrogate` | A trained model, its calibration set and its input envelope | Conformal bound plus residual check | Neural operators and other learned models |

`SparseGrid` means a sparse block grid in space, as in OpenVDB-style volumes. Smolyak sparse grids appear only along `Parameter` and `Sample` axes, as UQ quadrature.

**Decision D-FLX-3:** Generalize the contract's "nodal values" to `Discrete` and "per-face constants" to `PerEntity`, and add `PointCloud`, `Reduced` and `Surrogate`. *Why:* nodal values cannot hold Nédélec, Raviart-Thomas, DG or NURBS coefficients, and particle, reduced and learned results must be Fields to flow into checks and geometry. *Rejected:* separate result types per method, which would break "two universal types".

### Sampling, interpolation and error reporting

`field_sample` takes locations and a requested accuracy and returns values with per-sample errors. A location is a point in Part coordinates, a point on an entity given as `(EntityId, u, v)`, a reference-cell coordinate (the fast path), or an axis coordinate. Sampling on an entity is exact on the true surface, which matters for immersed solutions and display.

Each sample's error has up to three parts: representation error (interpolation or reconstruction), discretization error (the local estimate when the Field is a solution) and algebraic error. Each part carries a guarantee kind. Point location near boundaries uses Anvil's exact predicates, and ties break by cell index, so results are deterministic.

A sample outside the domain fails with `FieldError::OutsideDomain { distance }`. Extrapolation happens only when the caller passes `extrapolate: nearest`, and those samples report `Guarantee::Unknown`.

All Flux errors use one type, `ErrorBound { value, norm, kind }`. Here `norm` is L∞, L², energy, pointwise or a named goal quantity, and `kind` is `Guaranteed`, `Estimated`, `Indicator` or `Unknown`.

**Decision D-FLX-4:** Use one `ErrorBound` type, shared with Anvil, for geometry conversions and physics results, extended with a norm and a guarantee kind. *Why:* one name per concept, and a guaranteed L∞ bound on a length-valued Field then flows directly into an Anvil operation's bound. *Rejected:* a separate `ErrorEstimate` type, which would split one concept in two (CCR-FLX-1).

### Operations on Fields

| Operation | Ingot | Contract | Error behavior |
| --- | --- | --- | --- |
| Arithmetic and functions | `a + b`, `a * b`, `sqrt(a)` | Units checked at compile time; same domain required unless one side is restricted with `.on(...)` | Lazy `Analytic` composition; first-order error propagation from operand bounds |
| Differential operators | `grad(f)`, `div(f)`, `curl(f)`, `sym_grad(f)` | `Discrete` uses basis derivatives; `QuadraturePoint` and `PointCloud` need recovery first | Derivative error reported; `FieldError::NeedsRecovery` if not recoverable |
| Restriction and traces | `f.on(part.faces(q))` | Full trace for H¹, normal trace for H(div), tangential trace for H(curl) | No new error |
| Integration | `f.integrate(dx(region))` | Uses the Field's own quadrature, or adaptive quadrature for `Analytic` | Quadrature error estimate added |
| Extremes | `f.max()`, `f.argmax()` | Returns a `Quantity` with location and `ErrorBound` | Guaranteed for polynomial Fields via Bernstein bounds; plus discretization error |
| Statistics and norms | `f.mean()`, `f.l2_norm()`, `f.quantile(p, over: Sample)` | Over the domain or an axis | Statistical error separated from discretization error |
| Projection and transfer | `f.project(to: V)`, `f.transfer(to: body_v2)` | L² or H¹ projection; conservative transfer through a common refinement; consistent interpolation | Transfer error estimated and reported |
| Region extraction | `f.region(where: f > 250MPa)` | Returns an Implicit Body built by Anvil | Body `ErrorBound` from the Field error and its Lipschitz bound |
| Comparison | `compare(a, b)` | Difference Field plus a significance mask | Differences smaller than the combined bounds are reported as not significant |

Guaranteed extremes use the convex-hull property of the Bernstein basis: a polynomial on a cell lies within its Bernstein coefficients. Flux subdivides cells until the gap between the bound and the best sampled value is below the requested accuracy. This gives `max()` a guaranteed bound for the discrete Field, to which the discretization estimate is added.

### Fields that drive geometry

Anvil operations take Field arguments together with a required accuracy. Anvil samples through `field_sample` and adds the reported error to the `ErrorBound` of the Body it returns.

| Anvil use | Field type | Purpose |
| --- | --- | --- |
| Mesh sizing and anisotropic adaptation | `Field<Body, Length>`, `Field<Body, Metric>` | Adaptivity and user sizing |
| Deformed shape | `Field<Part, Displacement>` | Interference checks under load, springback compensation |
| Variable offset and shell thickness | `Field<Faces, Length>` | Thickness from optimization |
| Variable blend radius | `Field<Edges, Length>` | Stress-driven fillets |
| Implicit Body from a Field | `Field<Space, Length>` or any scalar Field with an iso-value | Topology optimization output, region extraction |
| Lattice grading and orientation | `Field<Body, Ratio>`, `Field<Body, Rotation>` | Graded lattices aligned with principal stress |
| Boundary morphing | `Field<Faces, Displacement>` | Free-form shape optimization |

If the Field cannot meet the requested accuracy, sampling fails with `FieldError::InsufficientAccuracy { achieved, required, producer }`. The error names the producing operation and the setting that would tighten it.

**Decision D-FLX-5:** A consumer's accuracy demand never triggers an automatic re-solve of the producer. *Why:* Kiln evaluates a dataflow graph, and a consumer silently changing its producer's inputs would be magic and would break caching. *Rejected:* automatic refinement on demand, which hides cost and makes results depend on who asked first.

### Storage

A stored Field is a header plus chunked arrays in the CAS. The header records type, domain hash, representation, axes, units, `ErrorBudget`, `ValidityReport` and provenance: the producing operation and behavior version plus the `PlatformClass`. Arrays are split into 1 MiB chunks aligned with the solver's virtual partitions and compressed losslessly with byte shuffling and zstd.

The content hash covers only canonical little-endian `f64` bytes, so identical results deduplicate across users and CI. Display copies are lossy (16-bit quantized values with the quantization error stated). They are derived artifacts, never inputs to checks.

## The weak-form language

### Design

Physics in Crucible is written as weak forms in Ingot, using notation modeled on UFL. UFL is the FEniCS language for declaring finite element discretizations of variational forms in notation close to the mathematics. Forms are typed Ingot values, so the Ingot compiler checks units, linearity and space conformity before anything runs.

A form names a continuous problem, not a mesh. The same form runs fitted, immersed, isogeometric, DG or reduced; the solve plan picks the method. The COV tab ships the std physics packages (`std::physics::solid`, `std::physics::thermal`, and so on) as ordinary Ingot written in this language. Users and agents get exactly the same power as the core team (principle 1).

```
use std::flux::{trial, test, dx, ds, inner, dot, sym_grad, solve}
use std::physics::solid::{sigma, eps}

let u = trial(Displacement, part)          // default space: H1 vector, degree chosen by the plan
let v = test(u)
let elasticity = inner(sigma(u, alu_6061_t6), eps(v)) * dx(part)
              == dot(traction, v) * ds(part.face(load_face))
let result = solve(elasticity, fixed: part.faces(bolt_holes))
result.von_mises                           // Field<Part, Stress>, with ErrorBudget
```

### Function spaces

| Space | Ingot constructor | Conformity | Elements available | Phase |
| --- | --- | --- | --- | --- |
| H¹ | `H1(domain, degree: p, shape: Scalar \| Vector3 \| Tensor)` | Continuous | Lagrange (any order) on all shapes, serendipity on quadrilaterals and hexahedra, hierarchical integrated-Legendre bases for p-adaptivity | 0 (p ≤ 4), 1 (any p) |
| H(curl) | `HCurl(domain, degree: p, kind: 1 \| 2)` | Tangential continuity | Nédélec first and second kind on simplices, hexahedra and prisms | 3 |
| H(div) | `HDiv(domain, degree: p, kind: rt \| bdm)` | Normal continuity | Raviart-Thomas and Brezzi-Douglas-Marini | 1 (needed by the equilibrated estimators), 3 (user-facing) |
| L² | `L2(domain, degree: p, basis: legendre \| nodal)` | None | Discontinuous Legendre and nodal bases; degree 0 is finite volume | 1 |
| Facet trace | `Trace(domain, degree: p)` | On facets only | Discontinuous polynomials on faces, for hybridizable DG and hybridized mixed methods | 3 |
| Global constants | `Real(n)` | n global unknowns | Lagrange multipliers, mean-value constraints, rigid-body variables | 1 |
| Spline | `Spline(body, degree: p, continuity: k, kind: nurbs \| thb)` | C^k inside patches | NURBS (from the B-rep), truncated hierarchical B-splines for local refinement | 2 |
| Mixed | `(V1, V2, ...)` | Per component | Any product, such as `taylor_hood(2)`, `mini()`, or `(HDiv, L2)` | 1 |
| Restricted | `V.restrict(region)` | As V | Any space on a subdomain or set of faces | 1 |

Elements are defined once, in the Rust element library in `flux-forms`, with all variants that matter for conditioning: equispaced, Gauss-Lobatto-Legendre (GLL) and warped GLL points, plus Legendre and Bernstein bases. Edge and face DOF orientation for H(curl) and H(div) is handled in the element restriction. Lowest order uses sign flips, as libCEED does; higher order uses small per-entity transformations, so meshes need no global orientation. Element shapes are interval, triangle, quadrilateral, tetrahedron, hexahedron, prism and pyramid; pyramids use rational bases [unverified: final pyramid basis].

### Measures

| Measure | Meaning | Fitted discretization | Immersed discretization |
| --- | --- | --- | --- |
| `dx(region?)` | Volume integral | Cells | Uncut cells plus cut-cell quadrature |
| `ds(faces?)` | Integral over the true boundary, or over B-rep faces selected by a `Query` | Boundary facets mapped to the `EntityId`s | Quadrature on the trimmed true surface |
| `dS(region?)` | Interior facets, for DG and HDG jumps | Interior facets | Interior facets plus cut facets |
| `dE(edges)` | Line integral on B-rep edges | Mesh edges on the B-rep edge | Quadrature on the true edge |
| `dP(points)` | Point evaluation (Dirac) | Point location | Point location |
| `dI(interface)` | Integral over an interface between two Instances (bonded, contact, thermal contact) | Mortar segments | Cut-surface quadrature on the common surface |

A measure may carry metadata such as `dx(degree: 8)` or `ds(faces, rule: gauss)`. Using `dP` or `dE` on a 3D solid makes the exact solution singular, so the compiler attaches a `Singular` flag to point values near the support (see "Honest reporting of singular quantities").

**Decision D-FLX-6:** Measures always refer to the true geometry, through `Query`s and `EntityId`s, never to mesh entities. *Why:* the same form then runs fitted or immersed, and boundary conditions survive remeshing and design edits through provenance. *Rejected:* mesh-tagged boundaries in the style of FEniCS and MFEM, which break on every geometry change.

### Operators and expressions

The language provides:

- Algebra: `+ - * /`, `inner`, `dot`, `outer`, `cross`, `tr`, `det`, `inv`, `dev`, `sym`, `skew`, `transpose`, and index notation `A[i, j] * B[j, k]`.
- Differential operators: `grad`, `div`, `curl`, `sym_grad`, `nabla_grad`.
- Facet operators: `jump`, `avg`, `n` (outward unit normal), `h` (local cell size).
- Functions: `exp`, `ln`, `sqrt`, `pow`, the trigonometric functions, `abs`, `sign`, `max_value`, `min_value`, `conditional(c, a, b)`.
- Pointwise eigen-decomposition for principal values, differentiable with a stated rule at repeated eigenvalues.
- Time derivatives: `dt(u)` and `dt(dt(u))`.
- Coefficients from other Fields, from Material property Fields, and from `Quantity` parameters.

Each operator has a symbolic derivative rule. Functions that are not smooth (`abs`, `max_value`, `conditional`) use a declared generalized derivative, and Newton solves report when iterates sit on a kink.

Constitutive models written in Ingot are ordinary functions returning expressions, such as `sigma(u, material)` in `std::physics::solid`. They compile into the same kernels and get derivatives for free. Constitutive models delivered as Wasm components run only on the CPU and must supply their own tangent ("Extending Flux").

### Problem kinds

| Kind | Ingot form | What Flux does |
| --- | --- | --- |
| Linear | `a == L`, with `a` bilinear in (trial, test) | Checks linearity, then compiles the operator and the right-hand side |
| Nonlinear residual | `F == 0`, where F is linear in the test function only | Derives the Jacobian `derivative(F, u)` symbolically; Newton by default |
| Energy minimization | `minimize(Pi, u)`, where `Pi` is a functional | Derives the residual and Hessian; uses trust-region Newton with symmetric solvers |
| Mixed | `let (u, p) = trial((Velocity, Pressure), part, element: taylor_hood(2))` | Block structure is kept for field-split preconditioners |
| Time-dependent | Terms containing `dt(u)` or `dt(dt(u))` | Builds a semi-discrete system `M(u) u̇ = f(u, t)`; the plan picks the time scheme; terms may be marked `implicit(...)` or `explicit(...)` for IMEX |
| Harmonic | `solve_harmonic(F, at: frequencies)` | Complex-valued forms; the plan picks direct sweeps or a reduced frequency model |
| Eigenvalue | `modes(a, m, count: 12, near: 0Hz)` | Generalized eigenproblem; sign and phase normalized deterministically |
| Constrained | `fixed:`, `constraints: [...]`, `Real` multipliers, `contact(...)` | Strong, Nitsche or multiplier enforcement chosen by the method (see "Contact and constraints") |
| Parametric | Forms depending on parameters marked `param` | Parameters become axes; reduced-model building and gradients are enabled |
| Functional | `J = f(u) * dx` | Used by goal-oriented estimation, gradients and checks |

More examples:

```
// Steady incompressible Stokes, mixed
let (u, p) = trial((Velocity, Pressure), channel, element: taylor_hood(2))
let (v, q) = test((u, p))
let stokes = 2 * mu * inner(sym_grad(u), sym_grad(v)) * dx(channel)
           - p * div(v) * dx(channel) - q * div(u) * dx(channel) == 0
let flow = solve(stokes, fixed: [channel.faces(walls) => 0m/s, channel.face(inlet) => inflow])

// Transient heat with a radiative boundary, implicit-explicit split
let T = trial(Temperature, housing)
let w = test(T)
let heat = rho * c_p * dt(T) * w * dx(housing)
         + inner(k * grad(T), grad(w)) * dx(housing)
         + explicit(emissivity * stefan_boltzmann * (pow(T.absolute(), 4) - pow(t_amb.absolute(), 4)))
             * w * ds(housing.faces(outer))     // affine Temperature must be made absolute before pow
         == q_chip * w * ds(housing.face(chip_pad))
let hist = solve(heat, initial: 20degC, over: 0s..600s)   // Field<Part, Temperature, Time>

// Time-harmonic magnetics in H(curl)
let a = trial(MagneticVectorPotential, HCurl(motor_region, degree: 2))
let v = test(a)
let eddy = inner(curl(a) / mu_r(material) / mu_0, curl(v)) * dx(motor_region)
         + I * omega * sigma_e * inner(a, v) * dx(motor_region.restrict(rotor))   // I: imaginary unit
        == inner(j_coil, v) * dx(coils)

// Constraints: a free-floating part, a periodic cell, a contact pair
let free  = solve(elasticity, constraints: [no_rigid_motion(part)])          // six Real multipliers
let cell  = solve(cell_form, constraints: [periodic(cell.face(x_min), cell.face(x_max))])
let gears = solve(mesh_form, contact: [contact(pinion.faces(teeth), wheel.faces(teeth), friction: 0.1)])
```

### What `solve` returns

`solve` returns a record of Fields, which is a plain Ingot value and not a new type. The record holds each trial unknown by its binding name, plus every derived output declared by the functions used in the form. For example, `std::physics::solid::sigma` declares the outputs `stress` and `von_mises`; Ingot owns the declaration syntax.

In the contract's example, `result.u` is the displacement and `result.von_mises` the von Mises stress, a `Field<Part, Stress>`. Derived outputs are computed lazily by Kiln and inherit the solve's `ErrorBudget`, plus the error from derivative evaluation or recovery. Path-dependent models compute derived outputs from the converged quadrature-point state.

### Static checks

The Ingot compiler runs these checks on every form before evaluation.

| Check | Rule | Error and suggested fix |
| --- | --- | --- |
| Units | Every term of a residual row has the same dimension; a test function carries the unit of its trial variation | `FormError::UnitMismatch { term, expected, found }`, which names the term and the likely missing factor (for example `k`) |
| Arity | Bilinear forms are linear in the trial and test functions | `FormError::NotLinear { term }`, suggesting `F == 0` |
| Conformity | `curl` needs H(curl) or H¹; `div` needs H(div) or H¹; `jump` and `avg` need `dS` | `FormError::Conformity`, suggesting the conforming space |
| Well-posedness hints | Saddle-point pairs that violate a known inf-sup condition (for example P1-P1 Stokes without stabilization) | A warning naming a stable pair, or `stabilize: pspg` |
| Quadrature | Estimated total degree is above 30, or the integrand is non-polynomial with no `degree` given | A warning stating the chosen degree and its quadrature error estimate |

Unit consistency gives a strong check for free. In elasticity, `inner(sigma, eps(v)) * dx` has units Pa · 1 · m³ = J, and `dot(traction, v) * ds` has Pa · m · m² = J. Dropping the thermal conductivity in a heat equation fails to compile, just as `width + load` does.

### Symbolic algorithms

The form IR is a hash-consed expression DAG; identical subexpressions are stored once.

1. **Lowering.** Compound operators expand to index notation, and units are erased after checking.
2. **Differentiation.** Gateaux derivatives (`derivative(F, u, du)`) are computed by forward-mode symbolic differentiation on the DAG, with chain rules through Ingot constitutive functions and Field coefficients. Adjoint forms (`adjoint(a)`) swap the trial and test arguments; `action(a, w)` replaces the trial function with a coefficient.
3. **Pullback.** Expressions map to the reference cell with the identity map for H¹ and L², the covariant Piola map for H(curl) and the contravariant Piola map for H(div).
4. **Degree estimation.** The total polynomial degree selects quadrature; non-polynomial integrands get degree `2p + 2` unless overridden, and the quadrature error is estimated by comparison with a rule one order higher on a sample of cells.
5. **Split.** Each integral is split into a basis action and a pointwise kernel, following libCEED's operator decomposition `Eᵀ Bᵀ D B E`. Here E restricts global DOFs to elements, B evaluates bases at quadrature points and D is the pointwise kernel.

**Decision D-FLX-7:** Write the form compiler natively in Rust, following the structure-preserving design of TSFC (which lowers finite element constructs to tensor algebra, then schedules the tensor operations) and libCEED's `Eᵀ Bᵀ D B E` operator split. *Why:* the compiler must run inside Kiln on every OS and in the browser, emit GPU kernels, and differentiate at the form level; no existing form compiler does all three in Rust. *Rejected:* embedding UFL with FFCx or TSFC through Python, which adds a Python runtime, cannot run in the browser sandbox, and emits C rather than GPU or SIMD Rust.

### Kernel generation

[[DIAGRAM: Form compiler pipeline. Boxes top to bottom: "Ingot form (typed, with units)" → "Form IR DAG (lowered, differentiated, pulled back)" → "Operator split Eᵀ Bᵀ D B E" → "Assembly level choice: full / element / partial / matrix-free" → "Kernel IR (loop nests, sum-factorization contractions, fixed operation order, no FMA on CPU and WGSL, 8-lane virtual vectors)" → three emitters side by side: "CPU: ahead-of-time Rust for std forms; run-time Wasm SIMD modules for user forms and in the browser" / "WGSL via naga for wgpu" / "CubeCL IR for CUDA and ROCm". All emitters → "Compiled kernel artifact in CAS, keyed by (kernel IR hash, emitter version, PlatformClass)".]]

| Assembly level | Stored | Memory per DOF | Work per DOF per application | Chosen when |
| --- | --- | --- | --- | --- |
| Full | Sparse matrix (CSR) | O(p^d) | O(p^d) | Degree ≤ 2 with a direct solver; AMG coarse levels; small problems |
| Element | Dense element matrices | O(p^d) | O(p^d) | Degree ≤ 2 on GPU, contact elements, cut cells |
| Partial | The pointwise kernel's linearization at quadrature points | O(1) | O(p) with sum factorization | Degree ≥ 2 on hexahedra and octree cells (default) |
| Matrix-free | Nothing; the linearization is recomputed | O(1) | O(p) plus the constitutive cost | Nonlinear Newton-Krylov with cheap constitutive laws; memory-bound GPUs |

deal.II's matrix-free documentation states the core trade-off. Work per DOF grows as O(k) for sum-factorized matrix-free evaluation, against O(k^d) for matrix-based evaluation. deal.II also reports matrix-free evaluation about eight times faster than a sparse matrix-vector product for quadratic elements on a 14-core Skylake server. Throughput is typically best at degrees three to six.

Tensor-product cells (hexahedra, quadrilaterals and all uncut octree cells) use sum factorization. Simplices use precomputed basis tables up to degree 3 and collapsed-coordinate sum factorization above that [unverified]. Cut cells use moment-fitted point sets that are not tensor products, and their basis values are evaluated directly. Cut cells are a lower-dimensional fraction of all cells, so they do not dominate cost.

**Decision D-FLX-8:** The kernel IR fixes the order of every floating-point operation and every reduction tree. It uses a virtual vector width of 8 lanes for `f64` and 16 for `f32`, and emits no fused multiply-add (FMA) for CPU or WGSL targets. *Why:* results then do not depend on SIMD width (SSE, AVX2, AVX-512, NEON, SVE, Wasm SIMD128) or on the code generator, so native, browser and user-form kernels share bits. Rust already forbids implicit FMA contraction and reassociation (RFC 3514), and WebAssembly SIMD128 has no deterministic FMA [unverified: relaxed-SIMD `relaxed_madd` may or may not fuse]. The cost of dropping FMA has a target below 1.3× on the CEED bake-off kernels. *Rejected:* letting each code generator vectorize freely, which makes bits depend on the CPU model. Using FMA on native CPUs only was also rejected, because it splits the CPU PlatformClass in two (open question 1).

Kernels come from four code generators that share one kernel IR:

| Code generator | Targets | Used for |
| --- | --- | --- |
| Ahead-of-time Rust | All native CPU targets, through runtime SIMD dispatch | std physics forms, which cover most solves |
| Wasm SIMD module generated at run time | Every CPU target: the platform's Wasm runtime natively, the browser's engine on the web | User-written forms everywhere; every form in the browser |
| WGSL through naga | wgpu (Vulkan, Metal, DX12, WebGPU) | Portable GPU baseline, for std and user forms |
| CubeCL IR | CUDA and ROCm | High-throughput `f64` GPU runs on servers and workstations |

**Decision D-FLX-9:** On the CPU, user-written forms compile to Wasm SIMD modules, never to native machine code; std forms are compiled ahead of time. *Why:* user forms get one CPU code path on every OS and in the browser. Generated code stays sandboxed even if the form compiler has a bug, and its bits match the ahead-of-time kernels because both obey D-FLX-8. The cost is speed: Wasm SIMD128 is narrower than AVX2 or AVX-512, so user forms on the CPU have a target of within 2× of ahead-of-time kernels on BP3. User forms still run at full speed on GPUs, and a hot user form can be promoted into std in public (D-ARCH-1). *Rejected:* a native JIT, which adds a second CPU backend and an attack surface; shipping LLVM in the desktop app, which is large and slow to compile.

**Decision D-FLX-10:** Ship two GPU code generators behind one `Backend` trait: Flux's own WGSL emitter as the portable baseline, and CubeCL for CUDA and ROCm. *Why:* the contract fixes wgpu and CubeCL behind a trait. WGSL alone has no `f64`, while CubeCL reaches CUDA and HIP but is alpha software whose README warns of breaking changes between minor versions. *Rejected:* CubeCL for every target, which ties the browser path to an unstable dependency; WGSL only, which leaves `f64` server GPUs unused.

Compiled kernels are CAS artifacts keyed by (kernel IR hash, code-generator behavior version, PlatformClass). A team or CI compiles each kernel once.

Transcendental functions (`exp`, `ln`, `pow`, trigonometric functions) come from Flux's own math library. It is written once in kernel IR from basic operations and emitted identically by every code generator. Platform `libm` and GPU built-ins are never used in solver kernels, because their accuracy differs by vendor.

**Decision D-FLX-11:** Flux owns its elementary-function library and never calls platform `libm` or GPU transcendental built-ins in solver kernels. *Why:* Rust's float RFC leaves transcendental functions unspecified, and WGSL gives only accuracy bounds. Identical inputs could otherwise give different bits on Windows, macOS and Linux. *Rejected:* platform math libraries, which are faster in some cases but non-deterministic across operating systems.

## Solve plans

`flux::plan` maps a problem to a `SolvePlan`. The problem is the forms, geometry, materials, boundary conditions and goals; the plan adds the fidelity, the placement class and the budget. The plan records the discretization, spaces and degrees, quadrature, assembly level, solver stack, precision, adaptivity loop and the error estimators to run.

Plans are deterministic functions of their inputs and never of the hardware found at run time. Users and agents can inspect, print, edit and pin them as Ingot.

```
let plan = flux::plan(elasticity, fidelity: signoff(goals: [peak_stress(part, load)], tol: 2%))
plan.explain()        // why each choice was made, with the alternatives considered
let result = solve(elasticity, fixed: part.faces(bolt_holes), plan: plan.with(method: fitted(p: 2)))
```

Goals come from the checks that read a result. When a check depends on `peak_stress(part, load)`, that functional becomes an adaptivity goal automatically.

**Decision D-FLX-12:** Default to immersed discretization on an adaptive octree for solids, heat and electrostatics. Fitted meshes are chosen automatically only for the cases in the table below, and isogeometric analysis only for shells and other thin NURBS-defined parts. *Why:* the contract asks that most users never mesh. An octree yields tensor-product cells that suit sum factorization and GPUs, and Anvil's certified queries on all four representations give the true boundary. *Rejected:* fitted tetrahedral meshing by default, which is fragile on real CAD and slower per DOF at high order; isogeometric analysis everywhere, which needs analysis-suitable volume parameterizations that general B-reps lack.

| Situation | Plan choice | Reason |
| --- | --- | --- |
| Solid, thermal or electrostatic problem on any Body | Immersed octree, CutFEM at sign-off, shifted boundary in interactive mode | No meshing; high-order; GPU-friendly |
| Contact between Instances (until immersed contact is validated in phase 3), sliding interfaces, boundary layers needing wall resolution (fluids above a Reynolds threshold set by the COV tab) | Fitted, with Anvil boundary-layer prisms where needed | Mortar contact needs matching surface meshes; immersed cells cannot resolve thin anisotropic layers efficiently |
| Shells, plates, sheet metal, thin walls with thickness below 5% of the bounding size | Isogeometric Kirchhoff-Love or Reissner-Mindlin shells on the B-rep NURBS faces | Exact geometry, C¹ continuity, no volume locking |
| Geometry known only as voxels, CT data or a density | Finite cell method | No sharp boundary exists |
| Wave propagation over many wavelengths (antennas, EMC) | FDTD or finite integration on a conformal grid; DG for curved high-order domains | Explicit time stepping, linear cost per step |
| Exterior radiation or scattering, electrostatics in open space | BEM with fast methods, or FEM-BEM coupling | Unbounded domains without truncation |
| Granular media, free-surface splashing, fragmentation | DEM, SPH, MPM or peridynamics | Topology changes beyond mesh-based methods |

## Discretizations

Every discretization implements the same `Discretization` trait (see "Rust API") and returns Fields with an `ErrorBudget`. Every method has convergence oracles. The table states when to use each, its contract and its phase; the subsections give details.

| Method | Use when | Contract | Error estimate | Phase |
| --- | --- | --- | --- | --- |
| Continuous FEM, fitted | Accurate boundary layers, contact, interfaces between Instances | Form + Anvil volume mesh → `Discrete` Fields | Equilibrated (guaranteed on simplices where proven) and dual-weighted residual (DWR) | 1 (p ≤ 4), 2 (any p, prisms, pyramids) |
| Immersed FEM: CutFEM, shifted boundary, finite cell | The default for solids, heat and electrostatics | Form + Body (any representation) → `Discrete` on an octree | Equilibrated (labelled `Estimated`, open question 11) and DWR, plus geometry and quadrature terms | 1 |
| Discontinuous Galerkin (interior penalty, upwind) | Advection-dominated and hyperbolic problems, high-order transient waves | Form with `dS` terms → `Discrete` L² Fields | Residual-based and DWR | 3 |
| Hybridizable DG | High-order elliptic and Stokes problems with fewer global unknowns, local conservation | Form + `Trace` space → statically condensed system | Postprocessing-based (superconvergent) | 3 |
| Isogeometric analysis | Shells, thin structures, exact NURBS geometry | Form + `Spline` space on B-rep patches → `Discrete` spline Fields | Residual-based and DWR on THB meshes | 2 |
| Finite volume (cell-centered) | Industrial CFD, conservation laws, mold filling | Conservation-law form or flux functions → `Discrete` degree-0 L² Fields | Gradient-jump indicators, DWR (phase 4) | 3 |
| FDTD and finite integration | Broadband electromagnetics, PCB EMC | Maxwell's equations + conformal grid → `SparseGrid` Fields with `Time` axis | Grid-dispersion estimate, Richardson extrapolation | 3 |
| Boundary elements with fast methods | Exterior acoustics, electrostatics, scattering | Boundary integral form → `Discrete` Fields on surfaces; `Analytic` far field | Residual-based | 3 |
| DEM | Granular flow, powder handling, hoppers | Particle shapes + contact law → `PointCloud` Fields | Time-step and contact-stiffness convergence; marked `Estimated` | 5 |
| SPH | Free surfaces, sloshing, splashing | Fluid model + Bodies as boundaries → `PointCloud` Fields | Resolution study only; `Unknown` unless a study is run | 5 |
| MPM | Large deformation, soil, snow, forming with topology change | Constitutive model + particles + background grid → `PointCloud` Fields | Resolution study; `Estimated` | 5 |
| Lattice Boltzmann | Transient low-Mach flow in complex geometry | Collision model + sparse grid → `SparseGrid` Fields | Richardson extrapolation over grid levels | 4 |
| Peridynamics | Fracture and fragmentation without crack tracking | Micromodulus or state model + horizon → `PointCloud` Fields | Horizon and grid convergence; `Estimated` | 5 |
| Reduced-order models | Repeated queries: design studies, controllers, FMUs, interactive drags | Basis + coefficient model → `Reduced` Fields | Certified (affine linear) or residual-based | 2 (modal, Craig-Bampton), 3 (POD, hyper-reduction) |
| ML surrogates | Very many queries where a reduced model is not possible | Trained model + calibration set + envelope → `Surrogate` Fields | Conformal bound plus weak-form residual check | 4 |

### Continuous FEM on fitted meshes

The fitted path uses Anvil volume meshes (tetrahedra, hexahedra, prisms, pyramids) with curved geometry of the same degree as the solution or higher. Each boundary facet is classified to the B-rep `EntityId` it approximates, so `ds(part.face(q))` resolves through provenance.

The geometry error between curved facets and the true surface comes from Anvil as an `ErrorBound` and enters the error budget. A mesh with inverted or near-degenerate curved elements fails with `DiscretizeError::InvalidElement { cell, jacobian_min }`, suggesting a higher geometry order or `anvil::untangle`.

### Immersed methods on octrees

The immersed path builds a 2:1-balanced octree over the Body's bounding box and classifies every cell as inside, outside or cut with Anvil's certified box classification. Uncut cells are standard tensor-product cells; hanging nodes are handled by constraints applied inside the kernels, as in deal.II's matrix-free framework. Three boundary treatments share this machinery.

| Treatment | How it works | Strengths | Limits | Used in |
| --- | --- | --- | --- | --- |
| CutFEM | Cut-cell quadrature on the true geometry; Nitsche's method for Dirichlet conditions; ghost-penalty stabilization on faces of cut cells, which keeps conditioning independent of how the boundary cuts the cells (Burman, Claus, Hansbo, Larson and Massing, 2014 [unverified: abstract not read]) | Optimal convergence at high order; boundary conditions on the true surface | Cut-cell quadrature cost; harder multigrid | Sign-off |
| Shifted boundary method | Integrates only over full interior cells (the surrogate domain) and shifts boundary values from the true to the surrogate boundary (Atallah, Canuto and Scovazzi) | No cut-cell quadrature, so all cells are uniform tensor-product cells that suit GPUs | The shift error grows with distance between boundaries; the cited analysis covers Dirichlet conditions for Poisson; Neumann data needs extra correction terms | Interactive mode; first iterations of sign-off |
| Finite cell method | Integrates over cells with a volume-fraction indicator and a small stiffness in the void region | Works on voxel, CT and density geometry | First-order boundary accuracy; parameter-dependent conditioning | Indicator-only geometry; density topology optimization |

Cut-cell quadrature uses moment fitting. Anvil supplies exact or certified integrals of monomials over the cut region (by the divergence theorem on the trimmed surface), and Flux solves for weights at fixed points. The residual of the moment equations gives the quadrature error bound. If Anvil cannot certify a cut, which happens with near-tangent surfaces, Flux subdivides the cell up to eight levels and then fails with `DiscretizeError::UncertifiedCut { cell, achieved }`.

The octree refines until every thin section has at least two cells across its thickness, using Anvil's local-thickness query. Sections thinner than the shell threshold go to isogeometric shells instead.

Small cut cells do not ruin conditioning because ghost penalty extends coercivity from neighbors. The plan also merges cut cells with a volume fraction below 1% into their neighbors, a variant called aggregated FEM [unverified]. Both are versioned behaviors.

**Decision D-FLX-13:** One octree machinery with three boundary treatments: shifted boundary for interactive mode, CutFEM for sign-off and finite cell for indicator-only geometry. *Why:* interactive mode needs uniform GPU-friendly cells, sign-off needs boundary conditions on the true surface, and both reuse one octree, one multigrid hierarchy and one kernel set. *Rejected:* one treatment for everything, which forces the cut-cell cost into the 1 s interactive budget or gives up sign-off accuracy.

### Discontinuous Galerkin and hybridizable DG

DG uses interior-penalty (symmetric and non-symmetric) forms for diffusion and upwind or Lax-Friedrichs fluxes for advection. It uses sum-factorized cell and face kernels on hexahedra. Explicit DG time stepping uses strong-stability-preserving Runge-Kutta schemes.

Hybridizable DG follows the unified hybridization framework of Cockburn, Gopalakrishnan and Lazarov. The only globally coupled unknowns are traces on element faces, giving a sparse symmetric positive definite system for elliptic problems. Cell unknowns are eliminated by static condensation in the kernels. Local postprocessing gives a superconvergent solution [unverified], which provides the error estimate.

### Isogeometric analysis

Isogeometric analysis uses the B-rep's NURBS directly as the basis: geometry stays exact under refinement, and k-refinement raises continuity above C⁰. Flux supports single and multi-patch spaces on trimmed faces, where trimming is handled by the same cut-cell quadrature as CutFEM. Patches are coupled with Nitsche's method, and truncated hierarchical B-splines give local refinement.

Isogeometric analysis is used first for Kirchhoff-Love and Reissner-Mindlin shells (welded frames and sheet-metal guards in golden product 4). Volumetric isogeometric analysis runs on Bodies that Anvil can parameterize as trivariate splines, which are few in practice. The plan uses it only when that parameterization exists.

### Finite volume

Cell-centered finite volume runs on octree cut cells and on fitted polyhedral meshes. It uses least-squares gradients, limited second-order reconstruction, and either a coupled pressure-velocity solver (default) or a segregated projection method for incompressible flow. It conserves mass, momentum and energy to solver tolerance per cell, and an oracle checks this. Flux supplies the machinery; the COV tab defines turbulence and multiphase models, such as k-ω SST and volume of fluid.

### FDTD and finite integration

FDTD uses the staggered Yee grid with convolutional perfectly matched layers. It handles curved surfaces with conformal cell corrections, models dispersive materials with auxiliary differential equations, and supports local subgridding. Finite integration is the same algorithm written in integral form on non-uniform grids, and Flux treats them as one method. Leapfrog time stepping runs at the CFL limit computed from the actual grid.

Meep (GPL per the contract) and openEMS (license [unverified]) are references only; GPL code is never linked.

### Boundary elements

Galerkin BEM covers Laplace, Helmholtz and Maxwell (combined-field) kernels and elastostatics. Singular integrals use Duffy-type and Sauter-Schwab regularized quadrature [unverified: final rule choice]. A kernel-independent fast multipole method or H²-matrix compression makes the cost near-linear. Calderón preconditioning keeps iteration counts bounded under refinement [unverified].

Flux wraps or contributes to bempp-rs, a BSD-3-Clause Rust library that assembles the standard Laplace and Helmholtz kernels, and builds Maxwell and fast-method parts natively if bempp-rs lacks them. FEM-BEM coupling (Johnson-Nédélec or symmetric) handles bounded interiors in open space.

### Particle methods

| Method | Variant | Contact and boundaries | Time stepping | Notes |
| --- | --- | --- | --- | --- |
| DEM | Spheres, clumped spheres, superquadrics; polyhedra through Anvil signed distance | Hertz-Mindlin with rolling resistance; Body walls through signed distance | Velocity Verlet with a critical-step check | Deterministic contact detection: cell lists with sorted neighbor order |
| SPH | Weakly compressible with density diffusion (δ-SPH); incompressible SPH for high accuracy [unverified: variant choice] | Bodies through signed distance with boundary particles or semi-analytic walls | Predictor-corrector or symplectic | Neighbor sums in fixed sorted order |
| MPM | MLS-MPM with APIC transfer [unverified: final variant choice] | Bodies as rigid or coupled grid boundaries | Explicit | Particle-to-grid transfer uses owner-computes gather, not atomics |
| Peridynamics | Bond-based and ordinary state-based | Bodies as boundary volumes; damage by bond breaking | Explicit, or quasi-static with Newton | Horizon chosen as m·Δx, with m = 3 by default |

All particle methods produce `PointCloud` Fields. They state their reconstruction rule and report `Estimated` or `Unknown` error unless a convergence study (an Ingot `std::flux::study` feature) was run. Particle results never pass a check whose error kind is `Unknown`.

### Lattice Boltzmann

Lattice Boltzmann uses D3Q19 and D3Q27 lattices with cumulant or regularized collision operators [unverified: cumulant stability claims] on sparse multi-level grids, with interpolated bounce-back boundaries on the true surface. It suits transient low-Mach flows such as drone wakes and cooling flow in complex enclosures. Grid levels give Richardson-based error estimates. Each lattice step is a pure gather, so GPU execution is deterministic without atomics.

### Reduced-order models

| Model | Build | Evaluate | Error | Phase |
| --- | --- | --- | --- | --- |
| Modal | `modal_basis` from `solve_eigen` | Modal superposition for linear dynamics and frequency response | Truncation estimate from residual mass and residual flexibility | 2 |
| Craig-Bampton component mode synthesis | Per Part: fixed-interface modes plus constraint modes | Assembly-level reduced model; Parts cached separately by Kiln | Interface truncation estimate | 2 |
| POD-Galerkin | `pod_basis` from snapshot Fields with `Time` or `Parameter` axes | Galerkin projection of the full form | Residual-based | 3 |
| Certified reduced basis | Greedy sampling for affinely parametrized linear forms | Online cost independent of the full model size | Guaranteed bound using a coercivity lower bound [unverified: method for the lower bound] | 3 |
| Hyper-reduction | DEIM (Chaturantabut and Sorensen [unverified]) or energy-conserving sampling and weighting for nonlinear forms | Reduced quadrature over sampled cells | Residual-based; `Estimated` | 3 |
| Krylov moment matching | Frequency-domain moment matching | Fast frequency sweeps; export as FMU | A posteriori residual over the band | 3 |

A reduced model records its parameter box. Evaluating outside it fails with `RomError::OutsideEnvelope { parameter, range }`, and the caller can explicitly request a full solve. A reduced model built from a pinned full model reproduces bit-identically like any operation.

### ML surrogates

Surrogates cover cases where reduced models cannot work, such as strong nonlinearity with topology change, or geometry families with no shared mesh. Supported architectures are Gaussian processes (small data, built-in variance), neural operators (Fourier and DeepONet types) and graph networks on meshes. Training data are Flux results, so every training sample carries provenance and its own error budget.

**Decision D-FLX-14:** A surrogate prediction is a Field only together with three things: a split-conformal error bound calibrated on held-out solver results, an input-envelope test, and a physics residual check. The residual check substitutes the prediction into the weak form and bounds the error with the same equilibrated estimator used for solver results. *Why:* conformal prediction gives distribution-free, non-asymptotic coverage guarantees (Angelopoulos and Bates), but the guarantee assumes new inputs are exchangeable with the calibration set [unverified: condition not in the abstract read]. The envelope test catches violations, and the residual check catches confident but wrong predictions. *Rejected:* uncalibrated surrogates, and physics-informed neural networks as a forward solver, because they offer no a posteriori bound comparable to the finite element estimators.

A surrogate that fails the envelope or residual test returns `SurrogateError::Untrusted { reason, residual_bound }`. It never silently falls back to a full solve; the Ingot feature decides, and std features fall back explicitly and say so in the report. Training runs deterministically, with seeded counter-based random numbers and fixed-order reductions, as a Flux operation. The trained weights are a CAS artifact.

## Meshing and adaptivity

### Division of labor with Anvil

Anvil owns all mesh generation and mesh modification; Flux owns error estimation, marking and the decision what to refine. The interface is Fields: Flux produces sizing and metric Fields, and Anvil consumes them.

| Flux needs from Anvil | Signature (Rust, illustrative) | Purpose |
| --- | --- | --- |
| Geometry queries on all four representations | `trait GeometryQuery { fn classify_box(&self, b: Aabb, tol: Length) -> BoxClass; fn closest_point(&self, p: Point3) -> SurfacePoint; fn moments(&self, b: Aabb, degree: u8) -> CertifiedMoments; fn surface_quadrature(&self, b: Aabb, degree: u8) -> SurfaceRule; fn local_thickness(&self, p: Point3) -> Length; }` | Immersed methods, shifted boundary, point location |
| Volume meshing | `anvil::tetrahedralize@n(body, sizing: &Field<Body, Length>, geometry_order: u8) -> (Body, ErrorBound)` and `anvil::hex_dominant@n`, `anvil::boundary_layer@n` | Fitted discretizations |
| Metric adaptation | `anvil::adapt_mesh@n(mesh, metric: &Field<Body, Metric>) -> (Body, HistoryRecords, ErrorBound)` | h- and anisotropic adaptivity on fitted meshes |
| Node relocation | `anvil::optimize_mesh@n(mesh, target: &Field<Body, Metric>) -> Body` | r-adaptivity |
| Shape velocity | `anvil::shape_velocity@n(body, param: ParamId) -> Field<Faces, Displacement>` per unit parameter change | Shape and parameter gradients |
| Display tessellation with parametric coordinates | Each display vertex carries `(EntityId, u, v)` | Painting Fields on the true geometry |
| Bounding-volume hierarchy | Deterministic traversal order | Contact search, point location |

### h-, p- and r-adaptivity

| Kind | Immersed octree | Fitted mesh | Isogeometric |
| --- | --- | --- | --- |
| h | Octree refinement and coarsening with 2:1 balance; hanging-node constraints | Newest-vertex bisection for small changes; metric-driven remeshing by Anvil for large changes | Truncated hierarchical B-spline refinement |
| p | Per-cell degree with hierarchical bases; conformity by minimum rule on shared faces | Same | k-refinement and degree elevation |
| hp decision | Smoothness estimate from the decay of Legendre coefficients: smooth cells get p+1, others are split | Same | Not applicable |
| r | Not used (the octree is fixed by the box) | Node relocation toward the metric through `anvil::optimize_mesh` | Control-point relocation, phase 5 |

The adaptive loop is SOLVE → ESTIMATE → MARK → REFINE, with Dörfler (bulk) marking at θ = 0.5 by default. Every iteration is a Kiln Op, so the loop is cached and resumable. It stops when the goal error is below tolerance, when the budget is spent (a typed error that keeps the last result), or when the estimate stagnates over two iterations. Stagnation usually means a singularity, which is reported as such.

Solution transfer between adapted discretizations uses conservative projection, so a transient run carries its state across remeshing. The transfer error is added to the temporal error budget.

## Error estimation and fidelity

### The error budget

Every result Field carries an `ErrorBudget`: one `ErrorBound` per source, plus a combined total.

| Component | Source | Estimator | Kind |
| --- | --- | --- | --- |
| Discretization | Spatial approximation | Equilibrated flux or stress reconstruction; DWR for goals; residual indicators in interactive mode | `Guaranteed` (equilibrated, energy norm, where proven), `Estimated` (DWR, and equilibrated where unproven), `Indicator` (residual) |
| Algebraic | Inexact linear and nonlinear solves | Equilibration of the algebraic residual; stopping criteria balance it below 10% of the discretization error | `Estimated` or `Guaranteed` |
| Temporal | Time stepping | Embedded-pair or BDF local truncation estimates, accumulated | `Estimated` |
| Geometry | Body conversion and curved-element mismatch | Anvil `ErrorBound` propagated through a shape-sensitivity estimate | `Guaranteed` or `Estimated` |
| Quadrature | Non-polynomial integrands and cut-cell moment fitting | Higher-order comparison; moment residuals | `Estimated` |
| Floating point | Rounding, mixed precision, GPU `f32` | Bound from the final `f64` residual | `Estimated` |
| Statistical | Monte Carlo, multilevel Monte Carlo, polynomial chaos | Confidence intervals and cross-validation | `Estimated` with a confidence level |
| Reduced model or surrogate | Reduction or learning | Certified bound, residual bound, conformal bound | Per method |
| Model | Physics model outside its validity envelope | Not an error number: a `ValidityReport` flag | Flag |

For energy norms, Flux uses equilibrated flux estimators, which give a guaranteed upper bound with no unknown constants and robust local efficiency. Smears and Vohralík (2020) prove this for arbitrary-order conforming approximations of reaction-diffusion problems on simplicial meshes, including the singularly perturbed case. Polynomial-degree-robust versions for pure diffusion also exist (Ern and Vohralík [unverified]). Flux uses equilibrated stress reconstruction for linear elasticity [unverified: guaranteed-bound theory for each element family].

The proofs cover fitted simplicial meshes. On octrees with hanging nodes and on cut cells, Flux runs the same construction but labels the bound `Estimated` until a proof and the effectivity oracle support `Guaranteed` (open question 11). A bound is never labelled `Guaranteed` without a proof for that method.

For goals, Flux uses the dual-weighted residual method of Becker and Rannacher (Acta Numerica, 2001). Local residuals are weighted by an adjoint solution for the goal functional. The adjoint comes from the same form-level differentiation used for optimization, so every functional a check reads can drive adaptivity at no extra modeling effort.

**Decision D-FLX-15:** Every result Field carries an `ErrorBudget`, and checks evaluate with three outcomes: `Pass` when value plus bound clears the limit, `Fail` when value minus bound violates it, and `Undecided` otherwise, with the accuracy needed to decide. *Why:* this is the only honest way to let approximate interactive results drive checks, and it turns the error estimate into a precise instruction for what to refine. *Rejected:* binary checks on point values, which silently pass designs whose margin is within numerical error (CCR-FLX-3).

### Fidelity modes

| Aspect | Interactive | Sign-off |
| --- | --- | --- |
| Purpose | Feedback during editing and dragging | Release gates, CI, reports |
| Latency target | Under 1 s for an update (contract target) on the reference laptop | None; bounded by the budget |
| Discretization | Shifted boundary on a coarse octree, p = 2, one adaptive pass | CutFEM or fitted, hp-adaptive to the goal tolerance |
| Precision | `f32` on GPU, with a final `f64` residual check | `f64` throughout; `f32` only inside preconditioners |
| Warm start | Previous result, recorded as an explicit Op input | Never; zero or deterministic initial guess |
| Estimators | Residual indicators scaled by calibrated safety factors; one cheap DWR pass for checked goals | Equilibrated (guaranteed where proven) and full DWR |
| Check outcomes | `Pass` or `Fail` only with a margin of at least 3× the estimate; else `Undecided` | `Pass`, `Fail`, `Undecided` on the stated bounds |
| UI | Results carry a visible interactive badge and an error overlay | Results carry the sign-off badge and full provenance |
| Usable for release | No | Yes |

Interactive mode stays honest in four ways:

1. **Explicit inputs.** A warm start is an explicit, recorded input, so the interactive result is still a pure function of its inputs.
2. **Calibrated safety factors.** For each problem class, the safety factor on the interactive estimator comes from the oracle corpus. It is the 99th percentile of the ratio of the sign-off error to the interactive estimate, so the interactive bound is wrong less than 1% of the time on known problem classes (target).
3. **Background audits.** When the machine is idle, Kiln runs the sign-off plan for the current design and records the interactive estimator's effectivity. If interactive mode undershoots, the safety factor for that problem class increases and the UI says so.
4. **Margin rule.** An interactive check that passes within its margin shows `Undecided`, never `Pass`.

Interactive updates within 1 s come from cached assembly structure, a reused multigrid hierarchy, `f32` GPU kernels, and coarse-first streaming through Kiln. When a drag moves only parameters inside a valid reduced-model box, the reduced model answers instead, carrying its own bound.

### Honest reporting of singular quantities

Point loads, point supports, re-entrant edges and corners, and bi-material corners make exact stresses infinite. Peak values at such locations depend on the mesh and are meaningless. Flux detects them in two ways: geometrically, by edges with dihedral angle above 180° and point measures, and numerically, by a local estimate that fails to decrease under refinement.

The affected quantities carry a `Singular` flag. A check on a flagged peak returns `Undecided` with reason `SingularPoint`. It suggests a fillet, a check at a stated distance from the singular point, or a stress-intensity criterion (`std::physics::solid::stress_intensity`).

### Validity envelopes

Flux evaluates the COV tab's `ValidityEnvelope` predicates on result Fields. For example, it checks strain magnitude against the small-strain limit, Mach number against the incompressible limit, and temperature against the Material data range. The output is a `ValidityReport`: a `Field<D, Validity>` marking the regions outside the envelope, plus a summary.

A check reading a quantity in a flagged region returns `Undecided` with reason `OutsideValidity` and names the model to switch to. The check never passes silently.

## Solvers

### Linear algebra layer

Flux distinguishes three vector layouts. Following libCEED's terms, a T-vector holds each true DOF once, an L-vector holds each DOF once per partition that touches it, and an E-vector holds one copy per element. All operators are `LinearOperator` trait objects, so matrix-free operators, assembled CSR matrices and block operators compose in one Krylov framework.

CPU dense and sparse factorization uses faer (MIT). faer 0.24.4 provides dense LLᵀ, LBLᵀ, LU with partial and full pivoting, QR with and without column pivoting, SVD and eigendecompositions, plus sparse LLᵀ, LU and QR. Sparse kernels that faer lacks or that need GPU execution live in `flux-solve`. That covers block CSR (BSR) storage, SpMV, the sparse triangular solves used by smoothers, and AMG setup.

### Sparse direct solvers

| Use | Method | Implementation | Phase |
| --- | --- | --- | --- |
| Small and medium problems (under about 2M DOFs, fits in memory), coarse grids, ROM bases | Supernodal Cholesky, LDLᵀ and LU with nested-dissection ordering (deterministic ordering, fixed seed) | faer [unverified: faer's supernodal and ordering support; Flux adds a deterministic nested-dissection ordering if needed] | 1 |
| Shift-invert eigen-solves, harmonic sweeps | Same, complex arithmetic | faer | 2 |
| Distributed and GPU direct solves | Multifrontal or supernodal distributed factorization | Optional bridge to MUMPS (CeCILL-C [unverified]), STRUMPACK or SuperLU_DIST (BSD [unverified]) through `flux-bridges` | 4 |
| Low-precision factorization with refinement | LU or LDLᵀ in `f32` with GMRES-based iterative refinement in `f64` (Carson and Higham) | faer + Flux | 2 |

Carson and Higham show that, with single as the working precision, half-precision LU plus double-precision residuals reaches full single accuracy for κ₂(A) ≤ 10⁴. GMRES preconditioned by the LU factors extends this to κ₂(A) ≤ 10⁸, and analogous results hold one precision level up. Flux therefore factorizes in `f32` with `f64` refinement only when a condition estimate is below 10⁷, so that κ times the `f32` unit roundoff stays below 1; otherwise it factorizes in `f64`.

### Krylov methods and preconditioners

Krylov methods: CG, pipelined CG, MINRES, GMRES and flexible GMRES with fixed restart, BiCGStab, and block variants for multiple right-hand sides. Every Krylov method uses the reproducible reductions described under "Determinism".

| Problem class | Default preconditioner | Alternatives | Phase |
| --- | --- | --- | --- |
| Scalar elliptic, high order (heat, potential) | p-multigrid with Chebyshev-Jacobi smoothing on the matrix-free operator, then h-multigrid on the octree, then AMG on the coarsest level | LOR-AMG (below) | 1 |
| Vector elliptic (elasticity) | Same, with rigid-body near-null space on the AMG level | Block-diagonal AMG; BDDC for distributed runs | 1 |
| Low order on fitted meshes | Smoothed-aggregation or classical AMG with near-null space | hypre BoomerAMG through the bridge | 1 |
| H(curl) (magnetics, eddy currents) | Auxiliary-space Maxwell solver (Hiptmair-Xu) built on Flux AMG | hypre AMS through the bridge | 3 |
| H(div) (mixed Darcy, flux reconstruction) | Auxiliary-space divergence solver | hypre ADS through the bridge | 3 |
| Saddle point (Stokes, incompressibility, contact multipliers) | Block-triangular field split with pressure-mass-matrix or least-squares commutator Schur approximations | Augmented Lagrangian preconditioning | 2 |
| High-order without good matrix-free smoothers | Low-order-refined (LOR) preconditioning: assemble the low-order operator on the refined mesh, apply AMG | Element-wise ILU for DG | 1 |
| DG and HDG | Static condensation, then AMG or p-multigrid on the trace system | Block Jacobi with exact local inverses | 3 |
| Distributed runs (above about 50M DOFs) | BDDC with deluxe scaling; FETI-DP as an alternative for contact-heavy problems | Additive Schwarz with coarse space (GenEO [unverified]) | 4 |
| Indefinite Helmholtz | Shifted-Laplacian multigrid | Sweeping preconditioners | 4 |

Pazner, Kolev and Dohrmann (2022) prove that low-order-refined preconditioners for the high-order de Rham complex (H¹, H(curl), H(div)) are spectrally equivalent independently of polynomial degree and mesh size. Their experiments use MFEM, and that result lets Flux reuse one AMG on every space.

Munch, Heister, Prieto Saavedra and Kronbichler compare local smoothing, geometric global coarsening and polynomial global coarsening in deal.II, on up to 147,456 cores. Global coarsening scales better under comparable smoothers because of load balance. Flux adopts global coarsening on octree hierarchies.

**Decision D-FLX-16:** Flux builds its own matrix-free p- and h-multigrid with global coarsening, plus its own AMG (smoothed aggregation first, classical later) with deterministic coarsening. hypre and PETSc are optional native bridges for scale-out and cross-validation. *Why:* AMG setup must be deterministic, run in Wasm and on wgpu, and coarsen the same way on every PlatformClass. hypre (Apache-2.0 OR MIT) and PETSc (BSD-2-Clause) are C libraries without a browser path. *Rejected:* making hypre or PETSc mandatory, which breaks browser parity and makes AMG setup order depend on MPI. LOR-AMG was also rejected as the universal default, because matrix-free p-multigrid avoids assembling and storing the refined operator. The phase 1 benchmark on CEED bake-off problems 3 and 5, with preconditioning, picks the default per problem class.

Deterministic AMG setup uses three rules:

- Strength-of-connection thresholds are exact comparisons.
- Aggregation visits nodes in a fixed order. In parallel, it uses a partition-independent maximal independent set with priorities from a hash of global DOF IDs, so aggregates do not depend on thread or rank count.
- Galerkin triple products accumulate in a fixed order.

### Nonlinear solvers

| Method | Use | Globalization | Phase |
| --- | --- | --- | --- |
| Newton-Krylov with exact Jacobian from form differentiation | Default for every nonlinear form | Backtracking line search with a cubic model and Armijo condition; critical-point line search for energy forms | 1 |
| Trust-region Newton (Steihaug-CG) | Energy-minimization forms (hyperelasticity, phase field) | Trust region | 2 |
| Arc-length continuation (Riks, Crisfield spherical) | Snap-through, buckling, limit points; produces load-displacement curves as Fields with a `Parameter` axis | Arc-length constraint with adaptive step | 2 |
| Pseudo-transient continuation | Steady flows, strongly nonlinear steady problems | Switched evolution relaxation | 3 |
| Nonlinear preconditioning (nonlinear elimination, additive Schwarz preconditioned inexact Newton [unverified]) | Localized nonlinearity: contact, plasticity fronts | Composition with Newton | 4 |
| Anderson acceleration | Fixed-point couplings (partitioned multiphysics) | Windowed least squares | 2 |
| Semismooth Newton | Contact and other complementarity conditions | Primal-dual active set | 2 |

Inexact Newton uses Eisenstat-Walker forcing terms. At sign-off, algebraic stopping balances the algebraic error estimate against the discretization estimate, so iterations stop when further work cannot reduce total error.

On failure, the solver returns `SolveError::NonlinearDiverged { iteration, residual_history, last_converged_state }`. The suggestions are specific: smaller load steps, arc-length continuation, or a check of the material model's validity envelope. The last converged state is returned as a Field, so the user sees how far the solve got.

### Time integration

| Family | Schemes | Use | Error control | Phase |
| --- | --- | --- | --- | --- |
| BDF (variable order 1 to 5) | Variable step, variable order | Stiff parabolic: heat, diffusion, chemistry | Local truncation error estimate; PI step control | 1 (BDF1-2), 2 (1-5) |
| Singly diagonally implicit Runge-Kutta (SDIRK) and ESDIRK | Embedded pairs, orders 2 to 5 | Stiff problems needing L-stability with high order | Embedded estimate | 2 |
| Additive Runge-Kutta (IMEX) | ARK orders 3 to 5 | Stiff-nonstiff splits: radiation, chemistry, convection-diffusion | Embedded estimate | 2 |
| Generalized-α | Second order, user spectral radius at infinity | Structural dynamics, fluid-structure interaction | Local error by Zienkiewicz-Xie estimate [unverified: exact estimator] | 2 |
| Newmark and central difference | Explicit and implicit | Explicit dynamics (crash, drop test), wave propagation | Energy balance check | 2 |
| Explicit Runge-Kutta, strong-stability-preserving | Low-storage SSP orders 2 to 4 | DG, finite volume, explicit waves | Embedded estimate or CFL control | 3 |
| Symplectic (velocity Verlet, leapfrog) | Fixed step | Particles, FDTD, molecular-type models | Energy drift monitor | 3 |
| Exponential integrators | Rosenbrock-exponential | Stiff linear-dominant problems | Embedded estimate | 5 |
| Parallel-in-time (Parareal, MGRIT) | Optional | Long horizons on large machines | Iteration residual | 5 |

Implicit methods share the nonlinear solver and preconditioner across steps. The preconditioner is rebuilt only when the step changes by more than a factor of 2 or the Newton iteration count doubles. Event detection (contact onset, threshold crossings) uses root-finding on dense output, so events happen at the same simulated time on every platform. Every transient result Field carries its `Time` axis with dense output and the accumulated temporal error.

SUNDIALS (BSD-3-Clause) is the reference implementation for these families. Flux reimplements the integrators natively, because each step must be a deterministic, differentiable Kiln Op with Flux's adjoint and checkpointing. SUNDIALS serves as the cross-check oracle in native CI.

### Eigenvalue problems

| Problem | Method | Phase |
| --- | --- | --- |
| Lowest modes of symmetric problems (vibration, buckling) | Shift-invert Lanczos with Krylov-Schur restarts, using a sparse direct factorization | 2 |
| Large symmetric problems without factorization | LOBPCG preconditioned by multigrid | 2 |
| Non-symmetric and quadratic (damped vibration, flutter, gyroscopic rotors) | Krylov-Schur on linearizations; companion forms for quadratic problems | 3 |
| Many modes in an interval | Contour-integral (FEAST-type) methods | 4 |
| Maxwell resonances in H(curl) | Shift-invert with deflation of the gradient null space | 3 |

Eigenvectors are normalized deterministically: mass-normalized, the largest-magnitude entry made positive, and ties broken by DOF index. Degenerate eigenspaces are reported as subspaces with an orthonormal basis, never as arbitrary vectors. Eigenvalue error bounds use the Kato-Temple inequality or residual norms with a gap estimate.

### Contact and constraints

| Mechanism | Enforcement | Use | Phase |
| --- | --- | --- | --- |
| Dirichlet conditions | Strong elimination on fitted meshes; Nitsche on immersed and IGA | All | 1 |
| Multi-point constraints (rigid links, RBE2 and RBE3-style couplings, periodicity, cyclic symmetry) | Elimination by a constraint matrix applied in the kernels; multipliers when elimination is not possible | Bolted joints, symmetric models | 1 |
| Bonded interfaces between Instances | Mortar (dual Lagrange multipliers) on fitted meshes; Nitsche on immersed | Assemblies with non-matching meshes | 2 |
| Frictionless and frictional contact | Mortar segment-to-segment with semismooth Newton; augmented Lagrangian (Uzawa-type); penalty as a fast interactive option | Gearboxes, press fits, snap fits | 2 |
| Large-sliding contact | Mortar with deterministic search (sorted bounding-volume hierarchy) | Drop tests, forming | 3 |
| Contact on immersed discretizations | Nitsche contact on cut surfaces [unverified: robustness at high order] | Immersed assemblies | 3 |
| Thermal contact, electrical contact | Interface conductance forms on `dI` | Electronics, motors | 3 |
| Integral constraints | `Real` space multipliers | Volume constraints, mean pressure | 1 |

A penalty result is never sign-off unless the penalty error is estimated. Flux estimates it from the gap or penetration Field, reports it in the budget, and refuses `Pass` while the penetration is above the stated tolerance. Contact status (open, stick, slip) is a `PerEntity` or quadrature-point Field the UI can paint.

### Fracture hooks

Flux provides the machinery for fracture; the COV tab supplies fracture models.

| Hook | Machinery | Phase |
| --- | --- | --- |
| Stress intensity and J-integral | Domain-integral evaluation on any discretization | 2 |
| Phase-field fracture | Staggered or monolithic solve with irreversibility (history field or bound-constrained Newton) | 4 |
| Cohesive zones | Interface elements on `dI` with traction-separation laws from COV | 3 |
| XFEM and cut-cell cracks | Crack surfaces as Implicit Bodies; enrichment through the immersed machinery | 5 |
| Peridynamic damage | Bond breaking (see particle methods) | 5 |

### Execution backends

| Backend | Targets | Precision | Used for |
| --- | --- | --- | --- |
| CPU | All Tier 1 native targets, the browser (Wasm SIMD128) and server Linux | `f64` (`f32` in preconditioners) | Everything; the reference backend |
| wgpu | Vulkan, Metal, DX12, WebGPU | `f32` only (WGSL has no `f64`; wgpu's `SHADER_F64` feature is native Vulkan only) | Interactive mode, `f32` preconditioners, mixed-precision Krylov with CPU `f64` residuals, display |
| CubeCL | CUDA, ROCm | `f64` and `f32` | High-throughput `f64` sign-off solves on workstations and cloud workers |
| Distributed | Server Linux clusters, multiple GPUs | As per node | Problems above one node's memory |

**Decision D-FLX-17:** Sign-off results on wgpu GPUs use `f32` kernels inside an `f64` defect-correction loop on the CPU. The outer residual is always computed in `f64` with reproducible reductions. The result's PlatformClass is that of the GPU, so a release whose results must replay on any machine pins `cpu-f64`. *Why:* the WebGPU path and Metal have no `f64`, yet sign-off needs `f64` accuracy on every Tier 1 platform. Defect correction attains the outer precision when the inner solver converges, by the same argument as iterative refinement. *Rejected:* emulated double-`f32` arithmetic in WGSL, which is 10 to 20 times slower [unverified: overhead figure], and forbidding GPUs for sign-off on Apple silicon and browsers, which breaks "identical features".

Distributed execution uses a Flux-owned message layer over TCP and QUIC on cloud workers, with an optional MPI transport where clusters provide MPI. Domain decomposition and BDDC run over this layer. Distributed execution is server-only; desktops and browsers use one node, with the CPU and one GPU.

### Determinism

Principle 4 requires identical outputs per PlatformClass and agreement within declared tolerance across classes. Flux meets this with six mechanisms.

1. **Fixed operation order.** The kernel IR fixes every floating-point operation and reduction order, with no FMA on CPU and WGSL targets (D-FLX-8). The same kernel gives the same bits on every SIMD width. Kernel entry asserts that the floating-point control state is IEEE default (no flush-to-zero or denormals-are-zero on x86 MXCSR or ARM FPCR); a library that changed it causes a typed error, not silent drift.
2. **Virtual partitions.** Work is split into a fixed number of virtual partitions (a function of problem size only, never of thread count). Rayon and GPU workgroups process partitions independently and combine them in partition order.
3. **Owner-computes assembly.** Scatter-add from E-vectors to L-vectors uses a precomputed transpose map. Each DOF gathers its element contributions in a fixed order, with no floating-point atomics on any backend.
4. **Reproducible reductions.** On CPUs, dot products and norms use binned accumulation as in ReproBLAS. Summands go into bins with fixed exponent boundaries, so the result depends only on the set of summands, never on order, thread count or rank count. ReproBLAS reports about 9n flops per reproducible sum: a dot product about 4× slower than an optimized one on one core, but less than 1.2× slower when summing 10⁶ doubles on more than 512 cores. Operator application dominates a CG iteration, so Flux targets under 1.3× slowdown per iteration. On GPUs, `f32` values are accumulated exactly in integer limbs (D-FLX-18).
5. **Deterministic graph algorithms.** Orderings, colorings, partitions and AMG aggregation use fixed seeds and hash-of-ID priorities.
6. **No hidden state.** No timing-dependent decisions: no wall-clock autotuning inside a solve and no run-time choice between algorithms based on hardware speed.

**Decision D-FLX-18:** GPU reductions use integer-only exact accumulation: bins of 32-bit integer limbs with explicit carry propagation, combined in fixed order. *Why:* wgpu offers 64-bit integer atomic add only on Vulkan and DX12 (Metal has 64-bit min and max only; WebGPU has none) and float atomics only on some Metal and Vulkan devices. Integer-limb bins need only 32-bit integer arithmetic, which every backend supports, and give identical bits on every GPU vendor. *Rejected:* floating-point atomics (order-dependent) and vendor reduction libraries (not reproducible across vendors).

CubeCL autotuning picks kernel configurations by run-time benchmarks, which would make bits depend on timing. Flux allows autotuning only over configurations proven to give bit-identical results, such as tile sizes that do not change the reduction tree. The chosen configuration is recorded in the Op's provenance.

Across PlatformClasses, results agree within a declared tolerance that is the larger of the final residual bound and 100 ulp per value (target). The cross-platform oracle enforces it. GPU and CPU differ in bits but agree within the solve tolerance, and the PlatformClass is part of the cache key.

| PlatformClass (proposed) | Members | Bit-identical by |
| --- | --- | --- |
| `cpu-f64` | Every Tier 1 CPU target, native and Wasm | Fixed operation order, no FMA, own math library, reproducible reductions; the only class used for oracle goldens |
| `wgpu-f32` | wgpu adapters, split by GPU vendor and driver major version until the phase 0 suite proves a wider class | Same kernel IR, integer-only reductions, subnormals flushed explicitly in kernels so the GPU's own flushing cannot change results |
| `cuda-f64`, `rocm-f64` | Per vendor | Same kernel IR, no float atomics, fixed reduction trees, FMA contraction disabled in the emitted code [unverified: CubeCL exposes this control] |

GPU driver compilers may apply their own floating-point optimizations to the shader that naga emits. Metal's fast-math default and the drivers' treatment of WGSL operations are the main risks [unverified: whether wgpu can disable each]. Until the determinism suite proves otherwise, `wgpu-f32` results are bit-identical only per vendor and driver line. That is acceptable because wgpu results feed interactive mode and `f64` defect correction, and release gates can pin `cpu-f64`.

**Decision D-FLX-19:** `cpu-f64` spans every Tier 1 operating system and CPU architecture, including the browser (CCR-FLX-4). *Why:* with Flux's own math library, no FMA and reproducible reductions, x86-64, ARM64 and Wasm produce identical `f64` bits. Rust's RFC 3514 specifies IEEE-754 results for basic operations, without flush-to-zero for scalars. 32-bit x87 targets are excluded and are not Tier 1. *Rejected:* one class per OS-architecture pair, which multiplies goldens and CI cost and weakens "identical features".

### Operation behavior versioning

Each Flux operation has a behavior version. A design's lockfile pins the versions, and Kiln dispatches to the pinned implementation, so old designs re-solve to identical bits on their PlatformClass.

| Change | Version effect |
| --- | --- |
| Any change to output bits on any PlatformClass: new default preconditioner, changed stopping rule, different quadrature, different AMG coarsening, new math-library polynomial | New behavior version (`@n+1`); the old version stays available |
| Performance-only change proven bit-identical by the determinism oracle on every PlatformClass | Same version |
| Bug fix that changes results | New version. The old version is marked `defective` with an advisory; designs pinned to it rebuild unchanged but show a warning with a one-click migration Proposal |
| New optional parameter with a default that reproduces old behavior | Same version |

Retention: every behavior version used by a signed release in the package registry stays executable for at least 10 years (target, to be confirmed with the PLT tab). Versions are retired only after migration tooling has offered an upgrade and no released design depends on them. A retired version can still run from an archived toolchain container in air-gapped installs.

A version upgrade is always a Proposal. Flux runs both versions and attaches a `compare` Field and the check deltas, so a human or agent sees what changed before accepting.

Solver configuration is part of the operation's inputs, not hidden defaults. `plan` resolves all defaults into an explicit `SolvePlan`, and the plan's hash enters the cache key. A future change to `plan`'s defaults is itself a new `flux::plan@n` version, so pinned designs keep their old plans.

**Decision D-FLX-20:** Pin the solve plan, not just the solver version. Defaults are resolved by a versioned `flux::plan` operation, and the resolved plan is a cache-key input. *Why:* most result drift comes from changed defaults, such as tolerances, preconditioners and estimators, not from changed algorithms. *Rejected:* versioning only the solver kernels, which lets default changes silently alter released results.

## Multiphysics coupling

### Monolithic and partitioned

A monolithic problem is one weak form over a product space: the sum of each physics' forms plus coupling terms. Flux compiles it into one block operator with one Newton solve and a field-split preconditioner that follows the block structure. Partitioned coupling runs each physics as its own solve and exchanges Fields at interfaces, iterating until the exchanged Fields agree.

| Coupling | Default | Reason | Phase |
| --- | --- | --- | --- |
| Thermo-mechanical, one-way (thermal stress) | Sequential: thermal solve, then structural solve reading `Field<Part, Temperature>` | No feedback; cheapest | 1 |
| Thermo-mechanical, two-way (contact conductance, large deformation, thermal softening) | Monolithic Newton with field-split preconditioning | Strong coupling; robust convergence | 2 |
| Electro-thermal (Joule heating, PCB traces, resistive heating) | Monolithic for steady; partitioned with quasi-Newton for transient with very different time scales | Temperature-dependent conductivity couples strongly | 3 |
| Electromagnetic-structural (motor forces, magnetostriction) | Partitioned: Maxwell stress or virtual work forces to the structure | Different spaces and time scales | 4 |
| Fluid-structure interaction, weak (light structure in heavy fluid excluded) | Partitioned with Aitken or IQN-ILS quasi-Newton | Separate solvers; good convergence when added-mass effects are small | 4 |
| Fluid-structure interaction, strong added mass (drone membranes, blood-like flows) | Monolithic arbitrary Lagrangian-Eulerian, or partitioned with Robin-Robin interface conditions | Partitioned Dirichlet-Neumann diverges when added mass dominates | 4 |
| Conjugate heat transfer | Partitioned with Robin conditions, or monolithic on a shared octree | Different solvers for fluid and solid | 4 |
| Piezoelectric, electrostatic MEMS | Monolithic | Strong two-way coupling at small scale | 5 |

Partitioned coupling uses a Flux implementation of the methods that preCICE offers [unverified: preCICE method list not on the page read]. Those are Gauss-Seidel and Jacobi coupling, Aitken relaxation, interface quasi-Newton (IQN-ILS and the multi-vector variant), and radial-basis-function data mapping. preCICE (LGPL-3.0) is linked only as an optional external adapter, running as a separate process, for users coupling external solvers.

Interface data transfer between non-matching discretizations is conservative for fluxes (forces, heat flow) and consistent for states (displacement, temperature). It uses Anvil's common-refinement intersection of the two interface representations. Each transfer reports its error.

Convergence of partitioned iteration is a stopping criterion with its own `ErrorBound` (the interface residual), which enters the algebraic part of the budget. Divergence returns `CouplingError::Diverged { residual_history }` and suggests the monolithic formulation or quasi-Newton acceleration.

```
use std::physics::{thermal, solid}

let T = thermal::steady(board, sources: [chip.power => chip_pad])
let u = solid::static(board, temperature: T, fixed: board.faces(screw_bosses))
// sequential coupling: u depends on T through Kiln, cached separately

let coupled = flux::couple([thermal::form(board), solid::form(board)], scheme: monolithic)
// two-way: one Newton solve, field-split preconditioner
```

### Multiscale homogenization

| Method | Use | Contract | Phase |
| --- | --- | --- | --- |
| First-order computational homogenization of periodic cells | Lattices, composites, foams | Unit cell (Body) + Material → effective tensor `Field<Body, Stiffness>` as a function of cell parameters | 1 (linear elastic, golden product 2), 3 (thermal, electrical) |
| Parametric homogenized material maps | Graded lattices in topology optimization | Cell parameter → effective properties as a `Reduced` or `Surrogate` Field with bound | 1 |
| FE² (concurrent two-scale) | Nonlinear microstructures | Each macro quadrature point runs a micro solve; micro solves batched on GPU; reduced micro models allowed with bounds | 5 |
| Dehomogenization | Turning a homogenized optimized Field into explicit lattice geometry | Orientation and density Fields → Implicit Body through Anvil | 2 |

Homogenized results carry a scale-separation validity flag: the ratio of cell size to the macroscopic gradient length scale. A check reading a homogenized stress where the ratio exceeds the envelope (default 0.1 [unverified: COV to confirm]) returns `Undecided` with reason `ScaleSeparation`.

### Co-simulation over FMI 3.0 and SSP

Flux implements an FMI 3.0.2 importer (Model Exchange, Co-Simulation and Scheduled Execution) and exporter, plus SSP 2.0.1 system descriptions.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Import FMU (Co-Simulation) | FMU archive → a Wasm-sandboxed or native-process co-simulation unit; variables become `Field<Space, V, Time>` or plain quantities | Unsupported binaries for the current OS → `FmuError::NoBinaryForPlatform` with the list available | Modelica Reference FMUs pass on every Tier 1 OS | 3 |
| Import FMU (Model Exchange) | Flux integrates the ODE with its own integrators, gaining event handling and adjoints from `fmi3GetDirectionalDerivative` and `fmi3GetAdjointDerivative` when provided | Missing derivatives → finite differences, stated in the budget | Reference FMUs; analytic test models | 3 |
| Export FMU | Any Flux model with ports (often a reduced model) → FMI 3.0 Co-Simulation FMU with Wasm or native binaries and state serialization | Model without a reduced form → large FMU warning | Round trip into a third-party importer [unverified: which] in CI | 3 |
| SSP system | SSP 2.0.1 `.ssp` archive ↔ Ingot co-simulation description (structure, connections, parameter sets) | Unknown layered standard → retained but ignored, reported | SSP examples from the standard round-trip | 3 |
| Master algorithm | Fixed-step Jacobi or Gauss-Seidel; variable-step with rollback using `fmi3GetFMUState` and `fmi3SetFMUState`; clocked partitions for Scheduled Execution | FMU without state rollback → fixed-step only, stated | Analytic coupled oscillators with known error order | 3 |

FMUs from outside Crucible are untrusted native code. Native-binary FMUs run in a separate sandboxed process with no file or network access beyond the FMU's resources, never inside the Kiln evaluation sandbox. Binaries are not portable, so an FMU without a binary for the current OS fails with a typed error. Crucible prefers FMUs with Wasm binaries (the FMI-LS-WASM layered standard is listed by the FMI project; its maturity is [unverified]).

Determinism for imported FMUs holds only if the FMU is deterministic. Flux runs each imported FMU twice in CI and marks it `NonDeterministic` if the outputs differ.

## Gradients and optimization

### Algorithmic differentiation at the form level

Flux differentiates the continuous problem, not low-level code. The approach follows Farrell, Ham, Funke and Rognes (dolfin-adjoint; its successor is pyadjoint [unverified]). They derive tangent linear and adjoint models from the high-level form representation, which they report is significantly more efficient and automatic than standard algorithmic differentiation of low-level code. Flux extends this to the whole Op graph:

1. **Form level.** For each form operation (`assemble`, `solve_linear`, `solve_nonlinear`, `solve_transient`, `solve_eigen`), Flux derives the tangent and adjoint forms symbolically and compiles them through the same pipeline.
2. **Operation level.** Every Flux operation registers a tangent and an adjoint rule, so Kiln can chain derivatives through an Ingot program that orchestrates many solves.
3. **Geometry level.** Anvil operations supply shape derivatives as velocity Fields on faces (`anvil::shape_velocity`). Flux combines them with the shape derivative of the physics, giving d(check)/d(Ingot parameter) for any parameter that moves geometry.

Gradients are exposed in Ingot as `grad(J, wrt: [p1, p2])` and `hessian_vector(J, wrt: p, v)`. The result is a plain `Quantity` or a Field over the design domain, with the gradient's own `ErrorBound`. That bound comes from the forward and adjoint algebraic errors and the discretization-consistency gap between discrete and continuous gradients.

**Decision D-FLX-21:** Compute discrete-consistent adjoints of the actual discretized problem, derived symbolically from forms and chained through Kiln's Op graph with registered tangent and adjoint rules. *Why:* discrete-consistent gradients converge optimizers to tight tolerances and pass Taylor tests exactly, and form-level derivation avoids taping millions of scalar operations. *Rejected:* operator-overloading algorithmic differentiation of the solver code (high memory, poor performance on matrix-free kernels), and continuous adjoints (inconsistent with the discrete objective, which stalls optimizers).

### Adjoints for steady and transient problems

| Problem | Adjoint | Cost | Phase |
| --- | --- | --- | --- |
| Linear steady | One transpose solve with the same preconditioner, transposed | About 1 forward solve | 1 |
| Nonlinear steady | One linear transpose solve at the converged state | Below 1 forward solve, since no Newton loop | 1 |
| Eigenvalue | Eigenvector-based derivative formula; repeated eigenvalues through the subspace formulation | Negligible | 2 |
| Transient | Backward-in-time adjoint with checkpointing | 2 to 5 forward-solve equivalents depending on storage | 2 |
| Coupled multiphysics | Block-transposed coupled adjoint, monolithic or partitioned in reverse | As forward | 4 |
| Contact | Adjoint of the active set at convergence; non-smooth points flagged | As forward | 3 |

Transient adjoints use checkpointing. Revolve (Griewank and Walther [unverified: attribution not read]) gives binomial checkpointing with the fewest recomputations for a fixed number of checkpoints. Zhang and Constantinescu extend Revolve to multistage time-stepping schemes and propose CAMS, which needs the fewest recomputations among the compared algorithms and was adopted by PETSc's TSAdjoint. Flux implements multistage optimal checkpointing natively.

Checkpoints live in a memory tier first and spill to disk. Checkpoints are CAS artifacts, so a re-run of the adjoint after an edit to the objective alone reuses the forward checkpoints.

Adjoint results pass Taylor tests in CI: for a random direction h, the remainder |J(p + εh) − J(p) − ε dJ·h| must decrease as O(ε²) over 5 halvings. The observed order must be within 0.1 of 2 (see "Oracles").

### Topology optimization

| Method | Formulation | Use | Phase |
| --- | --- | --- | --- |
| Density (SIMP) on the immersed octree | Densities as a quadrature-point or degree-0 L² Field; Helmholtz PDE filter; smoothed Heaviside projection; robust formulation with eroded, intermediate and dilated designs | Compliance, stress-constrained, thermal, multi-load | 1 (compliance and volume), 2 (stress, robust, manufacturing constraints) |
| Homogenization-based (graded lattice) | Lattice cell parameters with homogenized property maps; dehomogenization to geometry | Golden product 2 | 1 |
| Level-set | Implicit Body boundary evolved by shape derivatives; topological derivatives for hole nucleation; CutFEM analysis on the true boundary | Crisp boundaries, design-dependent loads (pressure, convection) | 3 |
| Multiphysics topology optimization | Any coupled form through the coupled adjoint | Heat sinks, compliant mechanisms, electromagnetic devices | 4 |

The optimizer is the method of moving asymptotes (MMA) or the globally convergent variant (GCMMA). Flux implements it natively as `flux::mma_step`, since Svanberg's reference code has a restrictive license [unverified: license terms]. The optimization loop is Ingot (`std::opt::topology`), so its iterations are visible as features and cached as Ops.

Aage, Andreassen, Lazarov and Sigmund (Nature, 2017) reached giga-voxel resolution for a full-scale aircraft wing on a supercomputer, citing PETSc and multigrid-preconditioned Krylov solvers. That sets the state of the art for scale. Flux's target is one billion density elements on a cloud cluster and 100 million on a single high-end GPU workstation (targets).

Manufacturing constraints are additional forms or projections that the MFG tab defines on top of this machinery: minimum feature size, overhang angle for additive builds, draw direction for casting and molding, and symmetry and pattern repetition. The result is a `Field<Body, Density>` or an Implicit Body. `anvil::implicit_from_field` turns it into geometry with a stated `ErrorBound`.

```
use std::opt::topology::{minimize, compliance, volume_fraction}

let design = minimize(
    compliance(bracket_space, loads: [load_case_a, load_case_b]),
    over: density(bracket_space, filter: 1.5mm, projection: robust),
    subject_to: [volume_fraction <= 0.3, overhang(build_dir: +z, max: 45deg)],
    fidelity: signoff(tol: 1%),
)
let part = anvil::implicit_from_field(design.density, iso: 0.5) |> lattice_infill(design.lattice_params)
```

### Shape and parameter optimization

Shape optimization works on Ingot parameters (dimensions, positions, spline control points) through the geometry-level chain rule, or on free-form boundary morphing Fields. Free-form morphing uses the Hilbertian (Sobolev) gradient: shape gradients are smoothed by an elliptic solve on the boundary, which keeps meshes valid. The approach follows Fireshape on Firedrake [unverified: Fireshape license].

| Optimizer | Problem class | Phase |
| --- | --- | --- |
| L-BFGS-B | Smooth, bound-constrained | 2 |
| Sequential quadratic programming and interior point | Smooth with nonlinear constraints | 2 |
| MMA and GCMMA | Many design variables with few constraints (topology) | 1 |
| Trust-region with exact Hessian-vector products | Small, high-accuracy problems | 3 |
| CMA-ES | Non-smooth, discrete or noisy objectives | 2 |
| Bayesian optimization on surrogates | Expensive black-box studies | 3 |
| Multi-objective (NSGA-II type) | Trade-off studies with Pareto fronts as Fields over a `Parameter` axis | 3 |

Stochastic optimizers use a counter-based random generator (Philox) seeded from the design repository's lockfile and the feature's `EntityId`. Re-runs are deterministic.

### Design of experiments

`std::flux::study` runs a design of experiments: full factorial, Latin hypercube with maximin optimization, Sobol and Halton sequences, and adaptive sampling on surrogate variance. Each point is a Kiln Op, so a study is cached point by point and resumes after interruption. The output is a Field with a `Parameter` axis, which feeds reduced models, surrogates, Sobol indices and Pareto plots in the UI.

## Uncertainty quantification

### Methods

| Method | Use | Contract | Error | Phase |
| --- | --- | --- | --- | --- |
| Monte Carlo and quasi-Monte Carlo | Any problem; reference method | Input distributions → result Field with `Sample` axis; mean, variance and quantile Fields | Confidence intervals; randomized QMC for error estimates | 2 |
| Multilevel Monte Carlo | Expensive problems with a discretization hierarchy | Levels from the adaptive hierarchy (octree levels or p); optimal sample allocation per level | Estimated mean-square error split into bias and variance | 3 |
| Multi-fidelity Monte Carlo | Reduced models or surrogates as control variates | Combines full and reduced models | Estimated variance | 3 |
| Polynomial chaos | Smooth dependence on few parameters (up to about 20) | Sparse regression or adaptive pseudo-spectral projection on Sobol or Gauss-Patterson points | Cross-validation error | 3 |
| Sobol sensitivity | Which tolerances and parameters matter | First-order and total indices from polynomial chaos coefficients, or Saltelli-Jansen estimators from Monte Carlo | Bootstrap confidence | 3 |
| First-order reliability (FORM), and importance sampling | Small failure probabilities | Most-probable-point search using adjoint gradients | Estimated | 4 |

Giles' review of multilevel Monte Carlo emphasizes the simplicity, flexibility and generality of the approach. Flux uses it whenever the plan already has a refinement hierarchy, which immersed octrees always provide.

### Propagating `Tol<T>`

Ingot tolerances (`4mm ± 0.1mm`, asymmetric limits, GD&T controls) are uncertain inputs. `std::uq` maps them to distributions: uniform within limits by default, normal with ±3σ at the limits when the process capability is declared, or a user distribution. They are propagated as follows.

1. **Parameter tolerances** become random parameters of the Ingot program. Kiln re-evaluates the geometry per sample and caches every sample. Geometry changes flow through `anvil::shape_velocity` for derivative-based methods.
2. **GD&T controls** (profile, flatness, position) become random boundary perturbation Fields on the toleranced faces. These are Karhunen-Loève expansions with correlation length from the MFG tab's process model [unverified: MFG to supply], bounded by the tolerance zone.
3. **Material uncertainty** comes from the Material record's uncertainty data as random property Fields.
4. **Load uncertainty** comes from distributions declared in Ingot.

| Method chosen by `std::uq::propagate` | Condition |
| --- | --- |
| First-order (linearized) moments using adjoint gradients | Default in interactive mode; reports the linearization error estimated from one second-order Hessian-vector check |
| Polynomial chaos | Up to about 20 effective parameters, smooth response |
| Multilevel Monte Carlo | Many parameters, non-smooth response, or sign-off reliability |

```
let thickness = 4mm ± 0.1mm
let result = solve(elasticity, fixed: part.faces(bolt_holes))
let stats = std::uq::propagate(result.von_mises.max(), inputs: tolerances(part), method: auto)
part.require(stats.quantile(0.999) < 0.6 * yield)   // Pass / Fail / Undecided, with statistical error
```

A UQ result is a Field with a `Sample` axis, or its moments and quantiles as Fields. The `ErrorBudget` separates statistical error from discretization error, so a check can say which one to reduce.

## Execution

### Every solve is an Op

A Flux solve is a Kiln Op graph, not a separate job concept. A "run" is the evaluation of the Ops a request depends on. `api` shows long evaluations as Op progress records, so there is no parallel "job" abstraction (contract section 10).

The cache key per Op follows the contract: hash of operation and behavior version, input hashes (forms, Fields, Bodies, resolved `SolvePlan`), library lockfile and PlatformClass. Placement is a PlatformClass choice made by the plan. It is part of the key, so a CUDA result and a CPU result are distinct cache entries, and a request pinned to `cpu-f64` is never satisfied by a GPU result.

### Placement and scheduling

| Placement | When | Notes |
| --- | --- | --- |
| Local CPU | Always available; default for small problems and the browser | Rayon thread pool; the virtual partition count is fixed by problem size |
| Local GPU (wgpu) | Interactive mode; `f32` preconditioners; display | Falls back to CPU explicitly, recorded in provenance, if the adapter lacks a required limit |
| Team server | Shared Kiln cache and medium-sized solves | Results shared through the CAS |
| Cloud burst | Above the local memory or time estimate, when the user or agent permits | CPU, CUDA or ROCm workers in Linux containers |

Scheduling follows three priorities: interactive solves for the active editor, then sign-off solves the user requested, then background audits and cache warming. A higher-priority request preempts lower-priority work at its next safe point, and the preempted work keeps its checkpoints. On a GPU shared with the renderer, solver dispatches stay under 4 ms while the camera moves, so orbit holds 60 fps (target, with UIX).

Team servers and cloud workers run a fair-share queue per user and per agent, bounded by each requester's budget. Scheduling changes only when work runs, never what it computes, because plans and partitions are fixed before execution.

The plan estimates memory, time and cost from problem size and the operator cost model. These are estimates with stated uncertainty, never promises. If the estimate exceeds the local machine, the request fails with `PlanError::ExceedsLocal { memory, time }`, suggesting cloud burst or a lower-fidelity plan. It never auto-bursts without permission.

### Cost caps and budgets

Every solve request carries a `ResourceBudget`: wall time, CPU core-hours, GPU hours and money. Agents always have caps from their scoped permissions (contract section 7). A budget breach stops at the next safe point, returns the last result with its error budget, and gives `SolveError::BudgetExhausted { spent, estimate_to_goal }`.

Cloud prices are fixed per quote: before a burst, Flux returns a quote with an upper bound, and the run never exceeds the accepted quote. Cost accounting is per Op and per Proposal, so a Proposal's CI report shows simulation cost.

### Checkpoint, restart and cancellation

Long solves (transient runs, adaptive loops, optimization) checkpoint at safe points: the end of a time step, an adaptive iteration or an optimizer iteration. Checkpoints are CAS artifacts keyed by the Op key plus a step index, so restart on any machine of the same PlatformClass continues to bit-identical results.

Cancellation, requested by Kiln when inputs change, stops at the next safe point within 100 ms (target) and keeps completed checkpoints. A later evaluation with the same inputs resumes from them.

### Result caching

Results are cached at three granularities: the final Fields, the reusable intermediates and the checkpoints. Reusable intermediates are assembled matrices, factorizations, AMG hierarchies and reduced bases. They are internal artifacts with their own keys; they are not Fields and are never exposed to features.

Early cutoff (Kiln backdating) means that an edit which does not change a solve's inputs reuses the solve. For example, a fillet radius far from the stress region still changes the geometry hash, so the solve re-runs. Flux therefore warm-starts the new solve from the old result as a recorded input in interactive mode, never at sign-off.

## Post-processing

### Probes and derived quantities

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Point probe | `f.at(point)` → `Quantity` with `ErrorBound` | `OutsideDomain`; `Singular` flag near singularities | Analytic Fields | 1 |
| Line and surface probes | `f.along(curve)` → `Field<Edges, V>`; `f.on(face)` | As point probe | Analytic Fields | 1 |
| Reaction forces and moments | `reaction(result, part.faces(q))` computed by the variationally consistent residual method (more accurate than integrated stresses) | None | Equilibrium: reactions balance applied loads to solver tolerance | 1 |
| Derived physics quantities | `von_mises`, `principal`, `tresca`, `heat_flux`, `safety_factor`, `fatigue_damage` (fatigue model from COV) | Undefined for value type → compile error | Analytic solutions | 1 to 3 |
| Recovered gradients | Superconvergent patch recovery or L² projection for smooth display stresses | Recovered Fields marked as `Indicator` accuracy for checks | MMS | 1 |
| Integrals and averages | Over volumes, faces, interfaces, time | Quadrature error added | Analytic | 1 |
| Isosurfaces, slices, streamlines | Display geometry for the UI, plus Implicit Bodies through Anvil for geometry use | Streamline integration error tolerance | Analytic flows | 2 |
| Frequency-response functions, mode shapes, animations | From Fields with `Frequency`, `Mode` and `Time` axes | None | NAFEMS free-vibration benchmarks | 2 |

### Reports

`std::flux::report` builds a report as Ingot data. The UI renders it and CI attaches it to Proposals. It contains:

- the plan and its explanation;
- the error budget per checked quantity;
- validity reports and the singularities found;
- convergence histories;
- mesh or octree statistics;
- check outcomes with margins;
- cost.

Export formats are the UI's concern. Flux provides the data through `flux::report_data` and the Field export formats (VTK-HDF for third-party viewers [unverified: format version], and CGNS for CFD exchange in phase 4).

### Data the UI paints on geometry

The UI paints Fields on the exact geometry, not on the analysis mesh. `flux::display_tiles` evaluates a Field at the vertices of Anvil's display tessellation, which carries `(EntityId, u, v)` per vertex, and adds an error overlay.

| Payload | Content |
| --- | --- |
| `DisplayTile` | Per display-tessellation tile: Field values (16-bit quantized with stated quantization error), per-vertex error magnitude, validity mask and singular mask |
| Colour map metadata | Range, units, quantization step, and whether the range is clipped |
| Level of detail | Coarse tiles first, refined values streamed as Kiln completes; matching the contract's "coarse results stream first" |
| Deformed shape | A displacement Field plus scale factor; the UI deforms the tessellation |
| Volume and slice data | `SparseGrid` bricks for volume rendering and section views |
| Particles and vectors | Point sets with values and glyph orientation |

Display data is derived and lossy, so it never feeds checks. Every displayed value can be traced to its source Field and position for "inspect" in the UI and `api`.

**Decision D-FLX-22:** Paint Fields by sampling them at the display tessellation's parametric coordinates on the true geometry, never by rendering the analysis mesh. *Why:* immersed and isogeometric solutions have no boundary mesh worth showing. Sampling on the true surface makes results look the same whatever method produced them, and display tiles are cacheable per Field and tessellation. *Rejected:* exporting analysis meshes to the renderer, which ties display to the discretization and shows octree artifacts.

## Rust API

The signatures below are illustrative but plausible, and follow the Rust API Guidelines. Kiln owns the generic operation-registration trait; Flux implements it and adds the `Differentiable` extension (CCR-FLX-5).

### Fields and errors (`flux-field`)

```rust
/// A physical quantity of value type `V` over a domain of kind `D`, with parameter axes `A`.
/// Immutable; cheap to clone (shared header and chunk references).
pub struct Field<D: DomainKind, V: Value, A: Axes = ()> {
    header: Arc<FieldHeader>,
    repr: Repr,
    _kind: PhantomData<(D, V, A)>,
}

pub struct FieldHeader {
    pub domain: DomainRef,          // Body content hash plus EntityIds; never a pointer
    pub unit: UnitTag,              // runtime tag for storage and inspection; checking is static
    pub axes: Vec<AxisSpec>,        // Time, Frequency, Mode, LoadCase, Sample, Parameter<P>
    pub budget: ErrorBudget,
    pub validity: ValidityReport,
    pub provenance: Provenance,     // operation@version, input hashes, resolved SolvePlan hash, PlatformClass
}

pub enum Repr {
    Analytic(CompiledExpr),
    Discrete { space: SpaceRef, coeffs: ChunkedArray<f64> },
    QuadraturePoint { rule: QuadratureRef, values: ChunkedArray<f64> },
    PerEntity(BTreeMap<EntityId, Box<[f64]>>),
    SparseGrid(SparseGrid),
    PointCloud { points: ChunkedArray<[f64; 3]>, values: ChunkedArray<f64>, rule: Reconstruction },
    Reduced { basis: FieldRef, model: ReducedModelRef },
    Surrogate(SurrogateRef),
}

/// Shared with Anvil (CCR-FLX-1).
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ErrorBound { pub value: f64, pub norm: Norm, pub kind: Guarantee }

pub enum Norm { LInf, L2, Energy, Pointwise, Goal(GoalId) }
pub enum Guarantee { Guaranteed, Estimated { confidence: Option<f64> }, Indicator, Unknown }

pub struct ErrorBudget {
    pub discretization: ErrorBound,
    pub algebraic: ErrorBound,
    pub temporal: Option<ErrorBound>,
    pub geometry: ErrorBound,
    pub quadrature: ErrorBound,
    pub floating_point: ErrorBound,
    pub statistical: Option<ErrorBound>,
    pub reduction: Option<ErrorBound>,
    pub local: Option<FieldRef>,    // per-cell indicator Field for display and marking
}

impl ErrorBudget {
    /// Combined bound in `norm`; the guarantee is the weakest of the parts.
    pub fn total(&self, norm: Norm) -> ErrorBound;
}

pub trait Sampler<V: Value> {
    fn sample(&self, at: &[Location], accuracy: Accuracy) -> Result<Vec<Sampled<V>>, FieldError>;
}

pub struct Sampled<V> { pub value: V, pub error: ErrorBound, pub flags: SampleFlags } // Singular, OutsideValidity, Extrapolated

#[non_exhaustive]
pub enum FieldError {
    StaleDomain { field_body: BodyHash, current_body: BodyHash },
    OutsideDomain { location: Location, distance: Length },
    InsufficientAccuracy { achieved: ErrorBound, required: ErrorBound, producer: OpRef },
    NeedsRecovery { representation: ReprKind },
    AxisMismatch { expected: AxisSpec, found: AxisSpec },
}
```

### Forms and elements (`flux-forms`)

```rust
pub struct Form { dag: ExprDag, arity: Arity, integrals: Vec<Integral> }

pub enum Arity { Functional, Linear, Bilinear }

pub struct Integral { pub measure: Measure, pub integrand: ExprId, pub quadrature: QuadratureSpec }

pub enum Measure { Dx(RegionRef), Ds(QueryRef), DS(RegionRef), DE(QueryRef), DP(PointSet), DI(InterfaceRef) }

pub trait Element: Send + Sync {
    fn shape(&self) -> CellShape;
    fn degree(&self) -> u8;
    fn map(&self) -> MapKind;                       // Identity, CovariantPiola, ContravariantPiola
    fn dof_layout(&self) -> &DofLayout;             // DOFs per vertex, edge, face, cell, with orientation rules
    fn tabulate(&self, points: &[RefPoint], derivatives: u8) -> Tabulation;
    fn tensor_factors(&self) -> Option<&[Basis1d]>; // Some for tensor-product elements: enables sum factorization
}

pub fn derivative(f: &Form, u: &Coefficient, du: &Argument) -> Result<Form, FormError>;
pub fn adjoint(a: &Form) -> Result<Form, FormError>;
pub fn action(a: &Form, w: &Coefficient) -> Result<Form, FormError>;
pub fn check_units(f: &Form) -> Result<(), FormError>;
```

### Kernels and backends (`flux-kernels`)

```rust
pub trait Backend: Send + Sync {
    fn platform_class(&self) -> PlatformClass;
    fn capabilities(&self) -> BackendCaps;          // f64 support, limits, subgroup support
    fn compile(&self, kernel: &KernelIr) -> Result<CompiledKernel, BackendError>;
    fn alloc(&self, len: usize, precision: Precision) -> Result<DeviceBuffer, BackendError>;
    fn launch(&self, kernel: &CompiledKernel, args: &KernelArgs) -> Result<(), BackendError>;
    /// Order-independent dot product; bit-identical within the PlatformClass.
    fn repro_dot(&self, x: &DeviceBuffer, y: &DeviceBuffer) -> Result<ReproSum, BackendError>;
}

/// Reproducible accumulator: binned on CPUs, exact integer limbs on GPUs.
/// Merging is associative and commutative, so the result depends only on the summands.
pub struct ReproSum { repr: ReproRepr }
impl ReproSum {
    pub fn merge(&mut self, other: &ReproSum);
    pub fn round(&self) -> f64;
}
```

### Solvers (`flux-solve`)

```rust
pub trait LinearOperator: Send + Sync {
    fn dims(&self) -> (usize, usize);
    fn apply(&self, x: VecRef<'_>, y: VecMut<'_>, ctx: &mut ExecCtx) -> Result<(), SolveError>;
    fn apply_transpose(&self, x: VecRef<'_>, y: VecMut<'_>, ctx: &mut ExecCtx) -> Result<(), SolveError>;
    fn diagonal(&self, ctx: &mut ExecCtx) -> Option<Vector>;
    fn assembly_level(&self) -> AssemblyLevel;      // Full, Element, Partial, MatrixFree
}

pub trait Preconditioner: LinearOperator {}

pub trait Discretization: Send + Sync {
    fn method(&self) -> Method;
    fn discretize(&self, problem: &Problem, geometry: &dyn GeometryQuery, plan: &SolvePlan)
        -> Result<DiscreteProblem, DiscretizeError>;
    fn estimate(&self, solution: &DiscreteSolution, goals: &[Goal]) -> Result<ErrorBudget, EstimateError>;
    fn adapt(&self, solution: &DiscreteSolution, marks: &Marking, anvil: &dyn MeshService)
        -> Result<DiscreteProblem, DiscretizeError>;
    fn to_fields(&self, solution: &DiscreteSolution) -> Result<FieldSet, FieldError>;
}

pub struct SolvePlan {
    pub method: Method,                     // Fitted, Immersed { boundary: Sbm | CutFem | FiniteCell }, Iga, Dg, Hdg, ...
    pub spaces: Vec<SpaceSpec>,
    pub quadrature: QuadratureSpec,
    pub assembly: AssemblyLevel,
    pub linear: LinearSolverSpec,           // Krylov method, preconditioner stack, tolerances
    pub nonlinear: Option<NonlinearSpec>,
    pub time: Option<TimeSpec>,
    pub precision: PrecisionSpec,
    pub adaptivity: AdaptSpec,
    pub estimators: Vec<EstimatorSpec>,
    pub placement: PlatformClass,
    pub fidelity: Fidelity,                 // Interactive { safety: f64 } | SignOff { goals, tol }
    pub resources: ResourceBudget,
}

#[non_exhaustive]
pub enum SolveError {
    LinearDiverged { iterations: u32, residual_history: Vec<f64> },
    NonlinearDiverged { iteration: u32, residual_history: Vec<f64>, last_converged: Option<FieldSet> },
    BudgetExhausted { spent: Cost, estimate_to_goal: Option<Cost>, last: FieldSet },
    SingularOperator { null_space_hint: NullSpaceHint },   // for example "no rigid-body constraint on Instance 3"
    Cancelled { checkpoint: Option<CheckpointRef> },
}
```

### Differentiable operations (`flux-opt`)

```rust
/// Extension Kiln calls when an evaluation requests derivatives (CCR-FLX-5).
pub trait Differentiable: Operation {
    fn tangent(&self, input: &Self::Input, d_input: &Tangents, ctx: &mut OpCtx) -> Result<Tangents, OpError>;
    fn adjoint(&self, input: &Self::Input, output: &Self::Output, d_output: &Cotangents, ctx: &mut OpCtx)
        -> Result<Cotangents, OpError>;
    fn checkpoint_policy(&self) -> CheckpointPolicy;   // Store, Recompute, MultistageOptimal { slots }
}
```

## Extending Flux

Flux follows the contract's three extension tiers.

| What | Tier | Mechanism | Runs on |
| --- | --- | --- | --- |
| New physics, such as a new PDE, boundary condition or coupling | Ingot package | Weak forms and std functions; full differentiation, GPU and estimators for free | CPU and GPU |
| Constitutive model in closed form | Ingot package | An Ingot function returning an expression; inlined into kernels | CPU and GPU |
| Constitutive model with internal iterations, lookup tables or legacy code (UMAT-style) | Wasm component | WIT interface `flux:constitutive`, batched over quadrature points; must supply its consistent tangent | CPU only |
| Specialist solver (a custom DEM contact law, an external code wrapper) | Wasm component | WIT interface `flux:solver` that consumes and produces Fields | CPU only |
| New discretization or core solver | In-tree operation | Promotion path with oracles, in public | All backends |

```wit
package flux:constitutive@0.1.0;

interface model {
    record point-input  { strain: list<f64>, temperature: f64, time-step: f64, state: list<f64> }
    record point-output { stress: list<f64>, tangent: list<f64>, new-state: list<f64> }
    variant model-error { outside-envelope(string), failed-to-converge(u32) }

    /// Batched over quadrature points to amortize the Wasm boundary.
    evaluate: func(params: list<f64>, inputs: list<point-input>) -> result<list<point-output>, model-error>;
    envelope: func() -> list<tuple<string, f64, f64>>;   // variable name, min, max
}
```

Wasm components in evaluation get no clocks, randomness, files or network (contract section 7). Flux also configures the Wasm runtime to canonicalize NaNs and to run relaxed-SIMD instructions with deterministic semantics, or to reject them [unverified: runtime option names]. Flux's own generated modules never emit relaxed-SIMD instructions. A Wasm constitutive model that omits a consistent tangent fails to register for Newton solves; it can still drive explicit dynamics.

## Limits of the machinery

Flux states plainly what it cannot do.

| Limit | Consequence | What Flux does |
| --- | --- | --- |
| Guaranteed error bounds exist only for some problem classes (linear elliptic, certain mixed problems) | Nonlinear, transient, contact and coupled results have estimated, not guaranteed, bounds | Labels every bound with its `Guarantee`; sign-off policy decides what is acceptable (open question 3) |
| Chaotic dynamics (turbulence, some multibody systems) amplify rounding differences exponentially | Pointwise results agree across PlatformClasses only over short times | Results are bit-identical within a class; across classes, agreement is declared on statistics such as time averages and spectra (CCR-FLX-7) |
| Singularities from idealized geometry or loads | Peak values do not converge | The `Singular` flag; checks report `Undecided` with fixes |
| Models outside their envelope | Results may be meaningless | `ValidityReport`; checks never pass silently |
| Direct numerical simulation of industrial turbulence, molecular and quantum scales, and full-vehicle crash with failure at production scale | Beyond desktop or practical cloud budgets, or outside continuum mechanics | Not offered by Flux core; COV defines model hierarchies (RANS, LES) with envelopes; external tools are reachable through FMI and Wasm components |
| Browser memory | Browser solves are limited by the 32-bit Wasm address space | The plan refuses oversize browser solves with `PlanError::ExceedsLocal`, suggesting a team server or cloud |
| Surrogates far from training data | No trustworthy prediction | Envelope test, conformal bound and residual check; `Untrusted` error |

## State of the art

Targets below are labelled as targets. They are measured on the reference laptop that phase 0 fixes, and on one reference server GPU per vendor.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Weak-form language | UFL: declarative variational forms close to mathematical notation | FEniCS/DOLFINx (LGPL-3.0 or later), Firedrake (license [unverified]) | UFL semantics embedded in Ingot, adding compile-time units, geometry-referenced measures and three-valued checks | Port the FEniCS and Firedrake demo corpora; every demo expressible (target 100%); form type-checking under 50 ms (target) |
| Form compilation | TSFC's structure-preserving two-stage compilation; libCEED's `Eᵀ Bᵀ D B E` split | FFCx, TSFC, MFEM partial-assembly kernels | Native Rust compiler, one kernel IR, four code generators | Compile time per form (target under 200 ms for p = 2 elasticity, cached thereafter); kernel throughput below |
| High-order operator evaluation | Sum-factorized partial assembly and matrix-free evaluation (CEED co-design: Kolev et al.; Fischer et al.; deal.II matrix-free) | MFEM (BSD) with libCEED (license [unverified]), deal.II matrix-free (license [unverified]) | Own kernels, fixed operation order, reproducible reductions | CEED bake-off problems BP1–BP6 on CPU and GPU, reporting DOFs per second and time per CG iteration (the metrics of Fischer et al.); target at least 80% of MFEM/libCEED throughput on the same hardware despite deterministic reductions and no FMA |
| Immersed discretization | CutFEM with ghost penalty (Burman et al. 2014); shifted boundary method (Atallah, Canuto, Scovazzi); aggregated FEM [unverified] | ngsxfem, GridapEmbedded, deal.II non-matching (all [unverified]) | Octree with shifted boundary (interactive), CutFEM (sign-off) and finite cell (indicator geometry) | MMS rates on curved cut geometries at p = 1 to 6; condition number independent of cut position (target: under 10× variation over 1,000 random shifts) |
| Isogeometric shells | Isogeometric analysis with k-refinement (Bazilevs, Beirão da Veiga, Cottrell, Hughes, Sangalli); truncated hierarchical B-splines | G+Smo, LS-DYNA IGA (both [unverified]) | Native Kirchhoff-Love and Reissner-Mindlin shells on B-rep NURBS | Shell obstacle course (Scordelis-Lo roof, pinched cylinder, pinched hemisphere [unverified: reference values]); target within 1% of reference displacement |
| Hybridizable DG | Unified hybridization (Cockburn, Gopalakrishnan, Lazarov) | NGSolve (LGPL) | Native HDG with static condensation in kernels | MMS rates including superconvergent postprocessing; global unknowns versus continuous FEM at equal accuracy |
| A posteriori estimation | Equilibrated flux estimators with guaranteed bounds (Smears and Vohralík 2020); dual-weighted residual (Becker and Rannacher 2001) | Research codes; residual estimators in deal.II and MFEM | Equilibrated (guaranteed where proven) plus DWR for every checked goal | Effectivity on the MMS corpus: equilibrated bound at least 1 always, at most 1.5 (target); DWR effectivity in [0.8, 1.25] (target) |
| Multigrid and preconditioning | Matrix-free global-coarsening h- and p-multigrid (Munch et al.); low-order-refined preconditioning of the de Rham complex (Pazner, Kolev, Dohrmann); BoomerAMG, AMS and ADS | hypre (Apache-2.0 OR MIT), deal.II, MFEM | Native p- and h-multigrid with global coarsening; native deterministic AMG; LOR-AMG; hypre and PETSc as bridges | Iterations independent of h and p on BP3 and BP5 with preconditioning; time to solution within 1.5× of MFEM+hypre (target) |
| Sparse direct | Supernodal and multifrontal factorization with nested dissection | MUMPS, PARDISO, CHOLMOD (licenses [unverified]) | faer, plus optional bridges | SuiteSparse Matrix Collection [unverified: subset to be fixed in phase 0]; within 2× of CHOLMOD on SPD matrices (target) |
| Mixed precision | Three-precision GMRES-based iterative refinement (Carson and Higham) | Mixed-precision solvers in MAGMA and vendor libraries [unverified] | `f32` factorization or GPU inner solves with `f64` outer correction | Full `f64` accuracy reached on conditioned test sets; speedup reported |
| Reproducible reductions | Binned reproducible summation (ReproBLAS: Ahrens, Nguyen, Demmel) | ReproBLAS (CPU, MPI) | Binned accumulation on CPUs, exact integer limbs on GPUs, in every reduction | Bit-identical across 1 to 128 threads, 1 to 64 ranks, all SIMD widths and Wasm; CG iteration overhead under 1.3× (target) |
| Time integration | Adaptive BDF and additive Runge-Kutta IMEX (SUNDIALS CVODE and ARKODE); generalized-α | SUNDIALS (BSD-3-Clause) | Native integrators as differentiable Ops | Order verification; work-precision diagrams on standard stiff problems within 1.5× of SUNDIALS (target) |
| Eigenvalues | Krylov-Schur, LOBPCG, contour integrals | SLEPc, ARPACK-ng (licenses [unverified]) | Native | NAFEMS free-vibration benchmarks (P18); time within 1.5× of SLEPc (target) |
| Nonlinear and contact | Newton-Krylov with exact Jacobians; mortar contact with semismooth Newton [unverified: Popp, Wohlmuth et al.] | PETSc SNES (BSD-2-Clause); 4C, MOOSE (licenses [unverified]) | Native | Hertz contact (analytic); Cook's membrane; iteration counts versus PETSc SNES |
| Adjoints | Form-level tangent and adjoint derivation (Farrell, Ham, Funke, Rognes); optimal multistage checkpointing (Zhang and Constantinescu, CAMS) | pyadjoint (license [unverified]); JAX-FEM (GPL-3.0) | Native form-level derivation chained through Kiln | Taylor test order 2 ± 0.1 for every Differentiable op; steady adjoint cost at most 1.2× a forward linear solve (target) |
| Topology optimization | Giga-voxel density-based optimization (Aage, Andreassen, Lazarov, Sigmund 2017) | The PETSc TopOpt code by Aage et al. [unverified: name and license]; commercial tools | Native on immersed octrees with MMA and robust projection | MBB beam and 3D cantilever compliance against published values; 10⁸ elements on one GPU workstation and 10⁹ on a cloud cluster (targets) |
| Boundary elements | Fast-multipole or H²-accelerated Galerkin BEM with Calderón preconditioning [unverified] | Bempp-cl (license [unverified]), bempp-rs (BSD-3-Clause) | Wrap or contribute to bempp-rs; native fast methods where missing | Sphere scattering against Mie series; near-linear time in surface DOFs |
| FDTD | Yee scheme with convolutional PML and conformal cells | Meep (GPL), openEMS (license [unverified]); references only | Native | Cavity resonances, Mie scattering, waveguide modes; cells per second throughput |
| Lattice Boltzmann | Cumulant or regularized collision on sparse GPU grids [unverified] | FluidX3D, waLBerla, Palabos (licenses [unverified]) | Native | Schäfer-Turek cylinder benchmark [unverified: reference values]; lattice updates per second |
| Particle methods | δ-SPH, MLS-MPM, Hertz-Mindlin DEM, state-based peridynamics [unverified] | DualSPHysics, LAMMPS, Peridigm (licenses [unverified]) | Native, phase 5 | Dam break and granular collapse against experiments [unverified: datasets] |
| Reduced-order models | POD-Galerkin with DEIM or ECSW hyper-reduction; certified reduced basis [unverified] | pyMOR, RBniCS (licenses [unverified]) | Native | Online speedup at most 1% error; target 100× on a parametric thermal benchmark |
| ML surrogates | Neural operators and graph networks with split-conformal calibration (Angelopoulos and Bates) | NVIDIA PhysicsNeMo (license [unverified]) | Native training and inference with conformal bounds and residual checks | Empirical coverage at least the nominal level on held-out data; residual check flags all deliberately out-of-envelope probes |
| Uncertainty quantification | Multilevel Monte Carlo (Giles); sparse polynomial chaos; Sobol indices | Dakota, OpenTURNS, UQLab (licenses [unverified]) | Native in `std::uq` plus Flux operations | Ishigami function analytic Sobol indices; MLMC cost scaling on a random-coefficient elliptic problem |
| Partitioned coupling | Interface quasi-Newton (IQN-ILS, IQN-IMVJ), RBF mapping | preCICE (LGPL-3.0) | Native methods; preCICE as an optional out-of-process adapter | Turek-Hron FSI benchmarks [unverified: reference values]; coupling iterations per step |
| Co-simulation | FMI 3.0.2 and SSP 2.0.1 | FMPy, OMSimulator (licenses [unverified]) | Native importer, exporter and master | Modelica Reference FMUs on every Tier 1 OS; SSP example round trips |
| Mesh adaptation (Anvil side) | Metric-based anisotropic remeshing | Mmg 5.7.0 (LGPL) | Anvil's own (ANV); Mmg as reference only | Anvil's oracles |

### Build, wrap or avoid

| Library | License (verified unless marked) | Decision | Reason |
| --- | --- | --- | --- |
| faer 0.24.4 | MIT | Depend | Contract choice; dense and sparse factorizations in Rust |
| wgpu 30.0.1 | MIT OR Apache-2.0 | Depend | Contract's single GPU abstraction |
| CubeCL | MIT OR Apache-2.0 | Depend, pinned exactly | Alpha; the README warns of breaking changes between minor versions |
| bempp-rs 0.2.0 | BSD-3-Clause | Wrap or contribute | Rust BEM assembly for Laplace and Helmholtz |
| hypre | Apache-2.0 OR MIT | Optional native bridge | Scale-out AMG and cross-validation; no browser path |
| PETSc | BSD-2-Clause | Optional native bridge | Cross-validation and distributed solves; no browser path |
| SUNDIALS | BSD-3-Clause | Oracle only | Native integrators must be differentiable Kiln Ops |
| MFEM, libCEED | BSD (libCEED [unverified]) | Reference and benchmark baseline | C++ and C; Flux needs Rust and determinism |
| MUMPS, STRUMPACK, SuperLU_DIST | [unverified] | Optional bridges after license review | Distributed direct solves |
| preCICE | LGPL-3.0 | Out-of-process adapter only | LGPL static linking risk in the core |
| DOLFINx, NGSolve, Mmg | LGPL | Avoid linking; reference only | LGPL linking risk; C++ |
| JAX-FEM, Meep, Elmer, openEMS | GPL-3.0 (JAX-FEM); GPL per the contract (Meep, Elmer); openEMS [unverified] | Reference only, never linked | Contract forbids GPL in the core |

## Platform notes

| Platform | Risk | Decision |
| --- | --- | --- |
| All Tier 1 CPUs | Different SIMD widths (AVX2, AVX-512, NEON, SVE) change summation order | Fixed virtual lane width, no FMA, reproducible reductions (D-FLX-8); one `cpu-f64` class |
| All CPUs | A linked native library (driver, bridge, plugin) changes floating-point control state (flush-to-zero, denormals-are-zero) | Kernels assert IEEE-default control state on entry; bridges save and restore it |
| Windows on ARM64, Linux ARM64, macOS | Platform `libm` differs | Flux's own math library in every kernel (D-FLX-11) |
| macOS (Metal) | No `f64` in wgpu; float atomics only on newer GPUs | `f32` kernels with `f64` CPU defect correction (D-FLX-17); integer-only reductions (D-FLX-18) |
| Browsers (WebGPU) | No `f64`; WGSL lets implementations flush subnormals and assume no infinities | Same as Metal; explicit flushing and finiteness guards in kernels; NaN and infinity checks after every solve |
| Browsers without WebGPU (WebGL2 fallback) | No compute shaders [unverified for every browser] | CPU Wasm path for all physics; WebGL2 used only for display; same features, slower |
| Browsers | 4 GiB address space of wasm32; threads need cross-origin isolation [unverified: hosting constraint] | Plan refuses oversize solves with a suggestion; single-thread fallback gives identical bits because partitions are fixed |
| Windows | GPU watchdog resets long dispatches [unverified: timeout value] | Dispatches split to under 100 ms each (target) |
| Linux servers | CUDA and ROCm only on servers and workstations that have them | Acceleration only: every CUDA or ROCm feature also runs on CPU and wgpu, so features stay identical |
| Air-gapped installs | No cloud burst; no remote kernel cache | std kernels ship compiled ahead of time; user-form Wasm modules compile locally; cloud placement disabled with a typed error |
| Tier 2 tablets and phones | Memory and thermal limits | Viewing of results and display tiles; solves run on a team server or cloud |

## Interfaces with other subsystems

### What Flux provides

| To | Provides | Canonical types |
| --- | --- | --- |
| Ingot (ING) | Form constructors, spaces, measures, `solve`, `modes`, `minimize`, `plan`, form checks called by the compiler | `Field<D, V, A>`, `Quantity<D>`, form values, `ErrorBound` |
| Anvil (ANV) | Fields for sizing, metrics, displacement, thickness, radius, density; `field_sample` with accuracy | `Field`, `ErrorBound` |
| Kiln (KLN) | Flux operations with behavior versions, tangent and adjoint rules, safe points, checkpoint step keys, cost estimates | `Op`, `Differentiable` |
| Physics coverage and materials (COV) | The weak-form language, discretizations, solvers, estimators, `ValidityReport` evaluation | `Field`, `Material`, `ValidityEnvelope` |
| Mechanical (MEC), electronics (ELX), manufacturing (MFG) | `std::flux`, `std::opt`, `std::uq` building blocks for their features | `Field`, `Body`, `Check` |
| `api` and agents (AGT) | Evaluate (solve, plan, estimate), Inspect (sample, probe, explain plan), Compare (`field_compare`), cost estimates and quotes | `Field`, `SolvePlan` as Ingot data |
| UI (UIX) | Display tiles, error overlays, validity and singular masks, plan explanations, report data | `Field`, display payloads |

### What Flux requires

| From | Requirement |
| --- | --- |
| Ingot (ING) | Generic `Field<D, V, A>` types with axes; affine temperature with `.absolute()`; complex quantities and an imaginary unit; record results from `solve`; declared derived outputs; `param` marking for parametric forms; access to `Tol<T>` limits and GD&T controls; three-valued check outcomes (`Pass`, `Fail`, `Undecided`) with reasons |
| Anvil (ANV) | `GeometryQuery` on all four representations with certified moments and surface quadrature; `tetrahedralize`, `hex_dominant`, `boundary_layer`, `adapt_mesh`, `optimize_mesh` consuming Fields; `shape_velocity`; `implicit_from_field`; display tessellation with `(EntityId, u, v)` per vertex; common-refinement intersection for interface transfer; deterministic bounding-volume hierarchies; the shared `ErrorBound` |
| Kiln (KLN) | Reverse traversal of Op graphs for adjoints; the `Differentiable` extension; cancellation at safe points; checkpoint artifacts keyed by Op key and step; explicit warm-start inputs; per-Op resource budgets and cost accounting; coarse-first streaming |
| CAS | Chunked array storage with deduplication; retention classes for checkpoints, intermediates and results |
| COV | Physics packages in Ingot; `ValidityEnvelope` predicates over Fields; constitutive models with consistent tangents; turbulence, fatigue and fracture models; scale-separation thresholds |
| MFG | Manufacturing-constraint forms for topology optimization; process-capability distributions for tolerances; GD&T correlation lengths |
| Platform (PLT) | PlatformClass definitions, the GPU and driver test matrix, toolchain archives for retired behavior versions, the reference laptop |
| Ecosystem (ECO) | Registry hosting for Wasm constitutive models and solvers (WIT `flux:constitutive`, `flux:solver`); FMU and SSP packaging rules |

## Oracles

All oracles live in the protected oracle directory. Held-out manufactured solutions and benchmark reference values are never shown to agents.

| Oracle | What it verifies | Pass criterion | Phase |
| --- | --- | --- | --- |
| MMS convergence suite | Every (method, element family, degree, cell shape) combination, with held-out manufactured solutions | Observed rate within 0.1 of theory over three refinements | 0 onward |
| CEED bake-off problems | Kernel correctness against an assembled reference, and throughput | Relative difference under 10⁻¹²; throughput targets above | 0 |
| NAFEMS P18 benchmarks | Linear static, thermal and free-vibration targets from "The Standard NAFEMS Benchmarks" | Within 1% of the NAFEMS target value at sign-off (target) | 1 (static, thermal), 2 (vibration) |
| Determinism suite | Same inputs give identical bits across threads, ranks, SIMD widths, ahead-of-time versus Wasm kernels, and Tier 1 operating systems; IEEE control-state assertion triggers on a planted flush-to-zero library | Bit-identical within each class; within declared tolerance across classes | 0 |
| Estimator effectivity | Equilibrated bounds and DWR on the MMS corpus | `Guaranteed` bounds never below the true error; effectivity targets above | 1 |
| Interactive honesty corpus | Interactive bounds against sign-off results on held-out designs | Undershoot rate under 1% per problem class (target) | 1 |
| Taylor tests | Every Differentiable operation and chained Ingot gradients | Order 2 ± 0.1 over five halvings | 1 |
| Patch tests | Linear patch tests for fitted, immersed and isogeometric discretizations | Exact to solver tolerance | 1 |
| Conservation | Finite volume per-cell conservation; reaction-force balance | To solver tolerance | 1 (reactions), 3 (finite volume) |
| Mechanics benchmarks | Hertz contact, Cook's membrane, shell obstacle course | Within published tolerances [unverified: reference values to be fixed in phase 2] | 2 |
| Coupling benchmarks | Turek-Hron FSI, analytic coupled oscillators for co-simulation | Within published bands [unverified] | 3–4 |
| UQ | Ishigami Sobol indices; MLMC complexity | Analytic indices within confidence intervals; observed cost exponent within 0.2 of theory | 3 |
| FMI | Modelica Reference FMUs import and export | All pass on every Tier 1 OS | 3 |
| Surrogates | Conformal coverage on held-out results; residual check on out-of-envelope probes | Coverage at least nominal; all probes flagged | 4 |
| Replay | Every released golden product's pinned results re-solved on each new build | Bit-identical on the recorded PlatformClass | 1 onward |
| Cancellation and restart | Cancel, resume and compare | Cancellation within 100 ms (target); resumed results bit-identical | 1 |

## Phasing

| Phase | Flux deliverables | Gate contribution |
| --- | --- | --- |
| 0, foundations | `flux-field` types and `ErrorBound`; kernel IR with the ahead-of-time CPU backend and Wasm SIMD modules; reproducible reductions; own math library; H¹ Lagrange up to p = 4 on hexahedra and tetrahedra; faer direct solves; CG with reproducible dots; unit-checked forms; symbolic form differentiation (Jacobians and adjoint forms) with Taylor tests, so differentiation exists from day one; MMS and determinism suites; FMA cost measurement (open question 1) | Determinism suite green on all Tier 1 targets; unit errors in forms fail to compile |
| 1, wedge (machined bracket, topology-optimized lattice bracket) | Immersed octree (shifted boundary, CutFEM); linear elasticity and steady heat; p-multigrid with AMG; equilibrated and DWR estimators; fidelity modes; wgpu `f32` interactive path; steady adjoints; density topology optimization with MMA; lattice homogenization; reactions, probes, display tiles; NAFEMS static and thermal subset | Golden product 1 checks decided at sign-off; golden product 2 optimized and verified; interactive update under 1 s (target) |
| 2, mechanical depth (gearbox, welded frame with sheet-metal guards) | Mortar contact with semismooth Newton; isogeometric shells; modal and Craig-Bampton reduction; eigen-solvers; BDF and generalized-α; arc-length; transient adjoints with checkpointing; Monte Carlo and first-order tolerance propagation; shape optimization; stress-constrained and robust topology optimization | Golden products 3 and 4 |
| 3, product breadth (molded enclosure with PCB) | H(curl) and H(div) user-facing; electro-thermal coupling; DG and HDG; finite volume; FDTD; BEM; POD, hyper-reduction and reduced basis; polynomial chaos, Sobol, MLMC; FMI 3.0 and SSP; level-set topology optimization; cohesive zones; CubeCL backend | Golden product 5 |
| 4, full multiphysics (drone validated against test data) | Fluid-structure interaction; lattice Boltzmann; electromagnetic-structural coupling; surrogates with conformal bounds; distributed BDDC and FETI-DP; multiphysics topology optimization; phase-field fracture; reliability methods | Golden product 6 |
| 5 and later (proposed) | DEM, SPH, MPM, peridynamics; FE² multiscale; XFEM cracks; parallel-in-time; exponential integrators; piezoelectric MEMS; marine and large-structure scale-out | New golden products per domain (MEMS resonator, ship hull section) [proposal] |

## Open questions

1. **FMA policy.** D-FLX-8 forbids FMA on CPU and WGSL to keep one `cpu-f64` class. Phase 0 must measure the throughput cost on BP3 and BP5; if it exceeds 1.3×, a separate native-FMA class may be better.
2. **Breadth of the `wgpu-f32` class.** Whether wgpu and the drivers allow disabling fast-math transformations (Metal especially) decides whether one class can span GPU vendors.
3. **Sign-off policy for `Estimated` bounds.** Nonlinear, transient and contact results rarely have guaranteed bounds. A human policy must say which checks may pass on `Estimated` bounds and with what safety factor; I propose a joint decision of FLX, COV and MEC.
4. **Interactive latency feasibility.** The 1 s update for a p = 2 shifted-boundary solve of about 200,000 DOFs on the reference laptop GPU is a target, not a measurement. Phase 0 must measure it.
5. **faer's sparse coverage.** Whether faer's sparse factorizations are supernodal, parallel and deterministic decides how much Flux builds itself.
6. **Partition-independent AMG quality.** Hash-priority aggregation may cost iterations against classical parallel AMG; phase 1 measures it.
7. **Behavior-version retention.** A 10-year retention window needs PLT to confirm toolchain archiving and CI cost.
8. **Deterministic surrogate training.** Training with reproducible reductions on GPUs may be too slow. The alternatives are CPU training or accepting per-class bits for training only.
9. **Ingot type-system load.** `Field<D, V, A>` with axis generics must stay readable in Ingot error messages; ING to confirm.
10. **Optional direct-solver bridges.** MUMPS and similar licenses need legal review before phase 4.
11. **Guaranteed bounds on octrees and cut cells.** Equilibrated estimators are proven on fitted simplicial meshes. Extending the guarantee to hanging nodes and cut cells is a research item; until then, immersed results carry `Estimated` bounds, which interacts with question 3.

## Contract change requests

- **CCR-FLX-1. `ErrorBound` definition.** Section 5 uses `ErrorBound` for Body conversions without defining it. Define it once, shared by Anvil and Flux, as `{ value, norm, kind }`, with norm (L∞, L², energy, pointwise, goal) and guarantee kind (`Guaranteed`, `Estimated`, `Indicator`, `Unknown`). *Reason:* one name per concept, and geometry and physics errors must compose.
- **CCR-FLX-2. `Field` axes and representations.** Extend `Field<Domain, V>` to `Field<D, V, A = ()>` with parameter axes (`Time`, `Frequency`, `Mode`, `LoadCase`, `Sample`, `Parameter`). Generalize "nodal values" to `Discrete`, "per-face constants" to `PerEntity`, and add `PointCloud`, `Reduced` and `Surrogate` representations. *Reason:* principle 3 and "fewest concepts".
- **CCR-FLX-3. Three-valued check outcomes.** Add an outcome type to `Check`: `Pass`, `Fail`, `Undecided { reason, required_accuracy }`. *Reason:* approximate results cannot honestly drive binary checks.
- **CCR-FLX-4. PlatformClass list.** Record `cpu-f64` (every Tier 1 CPU target including the browser), `wgpu-f32` (split by vendor and driver until proven wider), `cuda-f64` and `rocm-f64` as the initial classes, with PLT owning the list. *Reason:* determinism claims need named classes.
- **CCR-FLX-5. Kiln support for derivatives.** Add reverse traversal of the Op graph, a `Differentiable` extension of operation registration, and checkpoint artifacts keyed by step to Kiln's contract. *Reason:* section 7 requires algorithmic differentiation from day one, and adjoints across chained Ops need it.
- **CCR-FLX-6. Crate list.** Replace `flux-forms` and `flux-solve` in section 7 with `flux-field`, `flux-forms`, `flux-kernels`, `flux-solve`, `flux-couple`, `flux-opt` and `flux-bridges`, with `flux-field` below `anvil-ops`, `anvil-mesh` and `anvil-implicit`. Place `flux-bridges` outside `core/` because it is optional FFI. *Reason:* Anvil operations consume Fields, and `unsafe` must be confined to SIMD, GPU and FFI crates.
- **CCR-FLX-7. Statistical agreement for chaotic problems.** Let an operation declare cross-class agreement on statistics (time averages, spectra) instead of pointwise values. *Reason:* principle 4's "within declared tolerance" cannot hold pointwise for chaotic dynamics.

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
19. PETSc license: https://petsc.org/release/install/license/
20. hypre documentation: https://hypre.readthedocs.io/en/latest/
21. SUNDIALS license: https://computing.llnl.gov/projects/sundials/license
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
