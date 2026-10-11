# Crucible architecture contract (v3)

Binding for every design agent and reviewer. Version 3 integrates the rulings on all contract change requests (CCRs) and cross-tab conflicts from the first draft round; section 14 is the ruling log and lists the edits each tab must make. Where a draft disagrees with this contract, the contract wins. If you believe a ruling is wrong, do not work around it: say so under "Contract change requests" with your reason.

## 1. Mission

Crucible is one Rust platform where people and agents design, simulate, manufacture and release physical products from a single typed model. Every subsystem must be specified completely enough that an engineering team, and agent swarms working against oracles, could start building. "Fully specified" means every feature has a purpose, a contract (inputs, outputs, types), failure behavior, an oracle that verifies it, and a phase.

Four hard requirements from the founder:

1. **Anything physical.** Every major physics domain and every scale from MEMS to ships and building products. Honesty rule: no software validly simulates literally everything, so every model states its validity envelope, the spec says plainly what is out of reach, and it defines how new physics and domains are added.
2. **State-of-the-art, optimized methods** for every component and every simulation (section 8).
3. **Every major operating system, identical features** (section 9).
4. **Supreme coherence and taste** across the whole design (section 10).

## 2. Canonical names and glossary

| Name | What it is |
| --- | --- |
| Crucible | The platform (working name; trademark clearance is a phase 0 gate) |
| Ingot | The design language; source files end in `.ingot`; package manifest `ingot.toml`, lockfile `ingot.lock` |
| Anvil | The geometry kernel |
| Flux | The physics and simulation engine |
| Kiln | The incremental evaluation engine |
| CAS | The content-addressed store for all derived artifacts |
| `repo` | The repository crate: Changes, branches, merges, releases, change orders, BOM |
| `api` | The single API used by the UI, agents, CLI and CI, exposed over MCP and native SDKs |
| std | The standard library of Ingot packages |
| Golden products | Reference products whose passing checks close each phase |

No other codenames. Everything else gets a plain descriptive name. One name per concept, one concept per name:

| Term | Definition | Never call it |
| --- | --- | --- |
| **Operation** | A versioned primitive implemented in native Rust inside Anvil or Flux (`anvil::blend@2`, `flux::solve_linear@1`). Pure; deterministic per its determinism grade. | "op" in prose, "kernel", "function" |
| **Feature** | An Ingot function that captures design intent by orchestrating operations; the unit people see in a design's history. | "macro", "script" |
| **Wasm component** | A sandboxed, native-speed extension with a WIT interface, determinized before it runs (section 7.4). | bare "component", "plugin" |
| **Node** | One memoized computation in Kiln's graph: a front-end stage, a feature call, an Op, a check, a query resolution or a derived view such as a BOM. | "job", "task" |
| **Op** | A node that calls one operation or one Wasm component; its cache key is an `OpKey`. | |
| **External Op** | An Op whose implementation runs outside the sandbox in an isolated host (a pinned container image for a copyleft solver, an FMU or IBIS-AMI host, a firmware emulator). Cached by input hashes plus the host image digest; its results carry the host's platform class or `Unverified`. | "external tool run", "out-of-process result" |
| **External input** | Signed, content-addressed data produced outside evaluation (a licensed translation, a supplier offer, a machine reading, a physical measurement, a datasheet extraction), pinned in `ingot.lock` and read by Kiln as a leaf input. Changes only through an explicit update. | "snapshot", "data package" for this meaning |
| **Asset** | A non-source file stored in a design repository (a STEP file, a scan, a PDF datasheet), content-addressed and referenced from Ingot. | |
| **Evaluation** | One request to Kiln to compute a set of nodes for a revision, with a lifecycle (queued, running, done, cancelled), streamed results and a report. | "job", "run", "build request" |
| **Check** | A predicate declared with `require`, evaluated as its own node. Outcome `Pass`, `Fail` or `Undecided`; severity `Error`, `Warning` or `Info`. | "assertion", "rule result" |
| **Package** | A versioned unit in the package registry holding Ingot source, Wasm components, data (standards tables, catalog-part definitions, templates, tutorials, themes) or any combination. | |
| **Catalog part** | A purchasable item (bearing, motor, chip, fastener). Its definition is a data package under `parts::<manufacturer>::…`; its offers (price, stock, lead time) are External inputs. | "component" |
| **Body** | Geometry in any representation. | "Shape", "Solid" as a type |
| **Part** | A Body with identity (item number, name, material, properties) that appears in a BOM. | |
| **Assembly** | A tree of Instances with placements and mates. | |
| **Instance** | One occurrence of a Part or Assembly inside an Assembly. | "occurrence", "component" |
| **Software item** | A versioned binary with identity (firmware, bitstream, application) that appears in a BOM and is bound to a programmable Instance. | |
| **Field** | A physical quantity distributed over a domain (section 5). | "result", "map", "curve", "waveform" as types |
| **Network** | A lumped model: elements connected through domain-typed ports (electrical, magnetic, thermal, rotational, translational, fluid, signal), compiled by Flux into a DAE. Results are Fields over time or frequency on its ports. | "Circuit" as the type name |
| **Material** | A versioned record of properties and constitutive models. | |
| **Proposal** | A branch plus rationale plus CI report; the unit of agent work and of human review. | "PR", "merge request" |
| **Approval** | A human principal's signature over a content digest (an `ObjectId`). Any change to that content voids it. | "sign-off" as a noun for this |
| **Act** | An API method with an effect outside Crucible (release, order, send to a supplier or machine, start a build, publish a package or passport). Always two-phase: prepare a plan, commit only after an Approval of the plan's digest. | "action" for this meaning |
| **API method** | An entry in the `api` catalog. | "operation" |
| **Change** | One immutable fine-grained edit, like an Onshape microversion. "Revision" is reserved for PLM item revisions. | "commit" (except when comparing with Git) |
| **Design repository** | The repository holding one product's Ingot source, Assets, `ingot.lock` and history. | |
| **Snapshot** | A rendered image of a `ViewState` with structured marks, attached to Proposals and reviews. Never used for data. | |
| **Fidelity** | The accuracy a result is demanded at: `Preview` (fastest, approximate, never written to the shared cache), `Interactive` (approximate with an error estimate), `SignOff` (converged or exact). Flux study settings and Anvil previews use these names. | "coarse", "exact" as fidelity names; "sign-off mode" |
| **Platform class** | The set of execution environments whose results are bit-identical (section 7.3). | |
| **Determinism grade** | What an operation version guarantees: `Portable`, `ClassExact` or `Certified` (section 7.3). | "execution mode" |
| **Labels** | Data class (confidentiality, export control), integrity (trusted, untrusted) and data licences, attached to every artifact and API response and propagated by Kiln. | "taint flags", "classification tags" as separate concepts |
| **Service BOM** | The BOM view for service and spare parts. The abbreviation SBOM is never used; "software bill of materials" is always spelled out. | "SBOM" |

## 3. Principles (non-negotiable)

1. **No privileged code.** Built-in features use only the public mechanisms anyone can use: Ingot for features, Wasm components for heavy algorithms, and versioned Anvil and Flux operations underneath. If a user or agent cannot build a feature, neither can the core team.
2. **One model, three editors.** The visual editor, the code editor and agents edit the same typed program. Nothing exists only in the GUI.
3. **Two universal types.** `Body` carries geometry and `Field` carries physics data. Models (weak forms, Networks) describe how Fields are computed; libraries consume and produce Bodies, Fields and plain values.
4. **Determinism is a feature.** Same inputs and versions give identical outputs per platform class; cross-class results agree within declared tolerance (or, for chaotic problems, in declared statistics). Evaluation never depends on clocks, randomness or thread order.
5. **The compiler checks physics.** Units, dimensions and tolerances are types, checked before anything runs. Every approximation carries its error.
6. **Every claim has an oracle.** No feature ships without a machine-checkable test that agents cannot edit.
7. **Open core, interop first.** Kernel, language and standard library are open source. Open standards are first-class; no design is ever trapped.

## 4. Layering: operations, Wasm components, features (D-ARCH-1)

- **Operations, in native Rust.** Geometry and physics algorithms live in Anvil and Flux crates behind stable, versioned contracts; a few hundred primitives. Each operation version is frozen by content hash once released (D-ANV-18). A design pins the versions it was built with. Retired versions stay executable from archived Wasm builds of their frozen source; only versions that cannot compile to Wasm (GPU `ClassExact` paths) fall back to an `OpVersionRetired` error whose fix is an upgrade Proposal.
- **Wasm components, for heavy custom algorithms.** Nesting, CAM strategies, slicers, placers and routers, importers, specialist solvers. Sandboxed, determinized, portable to every OS and the browser, published in the registry. Evaluation-world Wasm components may import the host interface `crucible:ops` to call versioned operations, including GPU-backed ones; each call is a recorded Op dependency. They never get raw GPU, clock, file or network access.
- **Features, in Ingot.** Design intent, orchestration, entity selection and naming, checks and UI metadata. Ingot compiles to determinized Wasm (D-ING-13).
- **Tier rule (D-ECO-6).** Use Ingot unless code needs more than about 10⁶ primitive steps per call, an existing codebase in another language, or a data structure Ingot cannot express efficiently; then a Wasm component. Promote to an operation when at least three independent packages need it, it needs GPU or SIMD kernels, or it must be differentiable through Flux's form-level derivatives. Promotion happens in public, with oracles.
- **Fallback.** Features may be authored in Rust as Wasm components through `#[ingot::feature]`, which generates the WIT world and a typed Ingot wrapper (D-ING-15).

## 5. Core cross-subsystem types

Rust names are canonical. Owners in brackets.

**Values**

- `Quantity<D>` [ING]: a number with dimension `D`. SI base dimensions plus plane angle as a base dimension (radian coherent, never cancelled implicitly); torque in newton metres is a kind distinct from energy; affine quantities (°C and °F are points, kelvin values are differences, `.absolute()` converts); complex quantities. Every dimensional literal carries its unit; there are no default units; conversion is exact rational with one rounding. Checked at compile time, erased at runtime.
- `Tol<T>` [ING]: a toleranced value. Arithmetic is worst case by default, using affine forms over per-site noise symbols so repeated uses stay correlated; statistics (RSS, Monte Carlo, distributions, correlation groups) are explicit calls. A `Tol<T>` may be passed wherever `T` is declared: the body computes with the nominal and the tolerance's site is forwarded to the feature that realizes it, which attaches it as PMI.
- `Approx<T>` [ING]: a value with an `ErrorBudget`. Comparisons return `Truth`.
- `Truth` [ING]: `True`, `False`, `Undecided`. `if` on an `Undecided` fails loudly with the margin and the accuracy needed.
- `ErrorBound` [FLX, ANV]: `{ value, norm, kind }`; norm `LInf`, `L2`, `Energy`, `Pointwise` or `Goal`; kind `Guaranteed`, `Estimated`, `Indicator` or `Unknown`. `Guaranteed` only where a proof exists for that method.
- `ErrorBudget` [FLX, COV]: named components (discretization, solver, geometry conversion, input and tolerance, model form, surrogate, interpolation), each an `ErrorBound` or "not quantified", plus a total. A not-quantified component is never treated as zero.
- `Money<C>` [std]: a decimal amount with an ISO 4217 currency type parameter; not a `Quantity`; no implicit conversion.
- `ExternalText` [ING, AGT]: untrusted text with origin, written `external("...")`; never interpreted as instructions.
- `Labels` [KLN, AGT]: `DataClass` (public, internal, confidential, export-controlled with regime and classification), `Integrity` (trusted or untrusted), data licences (`DataLicence`). Joined through every derivation by Kiln and enforced by `api` at every boundary.

**Geometry and product structure**

- `Body` [ANV]: geometry in one of four representations: `BRep` (exact NURBS and analytic surfaces, cellular topology with regions), `Implicit`, `Mesh`, `SubD`. Representation lattice: Mesh ⊂ BRep, SubD ⊂ BRep, BRep ⊂ Implicit. Mixed operations return the least representation that holds both operands without approximation. Approximating conversions record per-face Hausdorff bounds that compose and survive later operations.
- `Part`, `Assembly`, `Instance` [MEC]; `Transform` (rigid placement); `CoordSys` (a `Transform` anchored by a `Query`, re-resolved on every rebuild) [MEC]; `ShapeAspect` (an identified portion of a Body's boundary for GD&T, kinds such as `OfSize`, `Hole`, `Pattern`; named after AP242's `shape_aspect`) [MEC].
- `EntityId` [ANV]: hash of (kind, `OpSite`, role, generating entity ids, discriminator). `OpSite` is the stable syntax-node identity of the call that ran the operation and excludes argument values, so dimension edits never rename entities. Features may attach role aliases (`FeatureRole`) to entities they return.
- `HistoryRecord` [ANV]: created, modified, split from, merged from, deleted.
- `Query` [ING, ANV]: criteria over provenance and roles plus certified geometric filters, resolved by `anvil::resolve` as its own Op on every rebuild. No positional indexing. Failure is a typed `ResolveError` with ranked fixes; success may carry Notes (`Merged`, `FragileAnchor`) that checks may forbid. Never silently picks another entity.
- `DisplayPackage` [ANV, UIX]: a per-Body cluster-DAG tessellation with stated chordal error and `EntityId` back-references, cached in CAS and consumed by every renderer.
- `ViewState` [UIX]: camera, visibility, sections and Field displays; stored as repository files; used by the UI, agents, snapshots and comments.

**Physics**

- `Field<D, V>` [FLX]: a quantity over a domain `D`. Domains are spatial or entity sets (`Body`, `Regions`, `Faces`, `Edges`, `Vertices`, `Points`, `Instances`, `Ports`), parameter domains named by a quantity type (`Time`, `Frequency`, `Temperature`, `AngularVelocity`, `StrainRate`, …), index sets (`Mode`, `LoadCase`, `Sample`, `Variant`), and products written as tuples. Examples: `Field<Body, Stress>`, `Field<(Body, Time), Temperature>`, `Field<Temperature, YoungsModulus>`, `Field<(Instances, Time), Transform>`, `Field<(Ports, Frequency), Complex<Impedance>>`, `Field<AngularVelocity, Length>` (a stability lobe), `Field<Body, ValidityZone>`. Values may be scalars, vectors, tensors, complex values or enums. Representations: `Analytic`, `Discrete`, `QuadraturePoint`, `SparseGrid`, `PerEntity`, `PointCloud`, `Reduced`, `Surrogate`. A `Part` is accepted wherever a `Body` domain is expected. Every result Field carries an `ErrorBudget`. Sampling reports interpolation error. Waveforms, spectra, sweeps, mode sets, load cases, ensembles, tables and material curves are all Fields; never separate types.
- `Network` [ELX, FLX]: see glossary.
- `Material` [COV]: properties as Fields over state domains (temperature, strain rate, direction), statistical basis per property, constitutive model ids, provenance, certification, uncertainty, `DataLicence`, environmental records and microstructure descriptors.
- `ValidityEnvelope` [COV]: declared conditions where a model is trusted. Evaluates to a zone Field (`Calibrated`, `Extrapolated`, `Invalid`, `Unassessed`) and to checks with disposition `Flag` or `Refuse`. Only humans waive. Crucible suggests escalation to a valid model but never switches models automatically.

**Evaluation and collaboration**

- `Feature` [ING]: an Ingot function from typed parameters to Parts, Bodies or plain values, with metadata that generates its dialog, docs and agent tool schema.
- `Op`, `OpKey` [KLN] (section 7.2); `ObjectId` [KLN]: SHA-256 identity of a canonical CAS object, with a one-byte algorithm code reserved.
- `Check`, `CheckOutcome` (`Pass`, `Fail`, `Undecided { reason, needed }`), `Severity` (`Error`, `Warning`, `Info`) [ING].
- `Fidelity` [KLN]: `Preview`, `Interactive`, `SignOff`.
- `ResultStatus` [api]: what a consumer currently holds for a demanded result: `Pending`, `Proxy`, `Ready(Fidelity)`, `Stale`, `Failed`.
- `PlatformClass`, `DeterminismGrade` [PLT, KLN] (section 7.3).
- `Proposal` [AGT, `repo`]: branch, rationale, CI report, author, delegation chain, parent and plan, risk class, labels, snapshots, provenance.
- `Approval` [KLN]: see glossary.

## 6. Ingot syntax reference

The canonical example (from the Ingot tab, with v3 std names). Every tab's examples follow Ingot's grammar.

```
use std::mech::{sketch, rect, extrude, rib, fillet, part}
use std::materials::alu_6061_t6
use std::sim::quick::peak_stress

/// L-bracket with a stiffening web.
#[feature(category: "Structure", icon: "bracket")]
pub feature bracket(
    #[ui(step: 5mm)]
    width: Length in 20mm..=400mm = 60mm,
    thickness: Length = 4mm ± 0.1mm,
    load: Force = 1.2kN,
) -> Part {
    let base = sketch(plane.xy) { rect(width, 40mm) } |> extrude(thickness)
    let web = base.face(role: end_cap).edge(longest, last(along: +y)) |> rib(height: 20mm, t: thickness)
    let body = base + web
    let solid = body |> fillet(body.edges(new), 2mm)
    let p = part(solid, name: "Bracket").material(alu_6061_t6)
    let stress = peak_stress(p, load, fixed: base.face(role: start_cap))
    p.require(stress < 0.6 * p.material.yield_strength(at: 20degC))
}
// width + load  →  error ING3001: cannot add Length and Force
```

Weak forms:

```
let u = trial(Displacement, p)
let v = test(u)
let elasticity = inner(sigma(u, p.material), eps(v)) * dx(p)
              == dot(traction, v) * ds(p.face(role: end_cap))
let result = solve(elasticity, fixed: p.faces(role: start_cap))
result.von_mises  // Field<Part, Stress>
```

Language rules every tab follows: no new keywords for domain concepts. Constraints are ordinary functions over `Expr<T>`; interfaces are records marked `#[interface]`; variants are enum or record parameters selected with `if` and `match`; variant rules and requirements are `require` checks and `std::systems` records; builder blocks (`sketch { … }`, `network { … }`) are the only block sugar.

**std package names.** `std::mech`, `std::mfg`, `std::electronics`, `std::systems`, `std::sim` (Flux building blocks: spaces, forms, `solve`, plans, quick studies), `std::physics` (physics models built on `std::sim`), `std::materials`, `std::opt`, `std::uq`, `std::agents`, `std::explore`. Sub-packages nest under these (`std::physics::regime`, `std::agents::proposal`). First-party packages outside std use `crucible::`; catalog parts use `parts::<manufacturer>::`; WIT packages use the `crucible:` namespace, one package per domain.

## 7. Decided architecture (do not contradict without a change request)

### 7.1 Engines

- **Anvil.** One Body type over four representations with the lattice above. Cellular B-rep with regions for multi-material parts and conformal meshing. Per-Body scale-relative resolution plus per-entity tolerances; no global tolerance. Exact adaptive predicates for linear decisions; certified enclosures with recorded, capped tolerance growth for decisions on curved geometry. Surface-surface intersection: GPU sampling orders CPU work and runs an exact integer broad phase; every intersection point comes from a certified CPU solve; distances between point samples are never thresholded (freedom-to-operate review of Zoo's patent US 12,229,885 B1 required). History records in every operation. Blends are a research program (constant radius, then variable, then vertex blends with setbacks; implicit fallback only when requested, with stated deviation). G2 and G3 analysis built in. Anvil owns all mesh generation, including volume meshing, adaptation and node optimization; Flux passes sizing and metric Fields. Anvil owns the geometric constraint solver (`anvil::solve_constraints`, `anvil::analyze_constraints`) used by sketches, mates, direct edits, routing and tolerance completeness. Anvil owns `anvil-planar`: exact integer-coordinate 2D geometry with lines and arcs (`anvil::planar::boolean`, `offset`, `distance`, `medial_axis`, Minkowski with a disc), used by electronics layout, design-rule checks and fills, 2D cutting toolpaths, nesting, MEMS masks and flat-pattern export. Flex circuits bend with the sheet-metal `anvil::fold`; there is no separate bend operation. Anvil's operations catalog is the canonical list of operation names.
- **Flux.** Physics stated as weak forms in Ingot (UFL-like), compiled through the shared kernel IR (7.5). Default discretization: immersed adaptive octree (shifted boundary at `Interactive`, CutFEM at `SignOff`, finite cell for voxel data); fitted meshes for contact and boundary layers; isogeometric shells. Matrix-free high-order FEM with sum factorization; own p- and h-multigrid and deterministic AMG; faer for CPU linear algebra; optional PETSc and hypre bridges. Discrete-consistent adjoints from forms, chained through Kiln. The resolved `SolvePlan` (from a versioned `flux::plan` operation) is pinned and enters the cache key. Every result Field carries an `ErrorBudget`; checks are three-valued. Surrogates count as Fields only with split-conformal bounds, an envelope test and a physics residual check. Flux also provides: rigid and flexible multibody dynamics, Cosserat rods for cables and hoses, the Network compiler and DAE solver, block-triangular sparse LU, full-wave electromagnetics, magnetodynamics with motion, and the general operations non-variational methods need (BVH build and traversal, neighbour lists, segmented reductions, counter-based random streams, fast multipole and hierarchical matrices, FFT solves). GPL tools (Meep, Elmer, OpenFOAM, LAMMPS and others) run only as External Ops or oracles.
- **Kiln.** Suspending scheduler with dynamic dependencies, Salsa-style durability and backdating, verifying traces in memory and constructive traces in the shared cache. Interactive early cutoff compares values directly; hashing happens off the interactive path. Progressive refinement is a set of independent nodes keyed by fidelity. Only trusted builders (CI and organization workers) write the shared cache. GreedyDual-Size eviction. Reverse traversal for adjoints, a `Differentiable` registration extension and checkpoints keyed by step. Kiln is generic: Anvil, Flux and Ingot register node kinds through the operation contract in `base`.
- **`repo`.** Every edit becomes an immutable Change; ref updates go through a Jujutsu-style transaction log; branches are cheap; a merge is clean only when the result compiles, resolves, passes every check both parents passed and shows no new geometric overlap or interference. Live collaboration uses a Loro block tree with Fugue text leaves; offline work longer than 60 s rejoins as a branch through the merge driver. Releases are signed tags; change orders are Proposals; approvals sign exact content; revision identity is content-based. The BOM is a query over the assembly graph with EBOM, MBOM and service BOM views. Authorization uses Cedar policies; audit, transaction logs and release tags live in per-tenant transparency logs (C2SP tlog-tiles).
- **Hardware CI.** Every commit rebuilds the design and evaluates its checks and regression simulations. Physical tests run on hardware rigs when their inputs change; their results enter Kiln as measured input cells.

### 7.2 Cache keys

An `OpKey` is the SHA-256 of:

1. the operation name and behavior version, or for a Wasm component the SHA-256 of its determinized binary, or for Ingot code the code hashes of the modules actually used plus the language behavior version;
2. the canonical encoding of the arguments, including any resolved plan;
3. the `ObjectId`s of the inputs;
4. the platform class, when the operation's grade is `ClassExact` or it ran in a class other than `CpuCanonical`;
5. for External Ops, the host image digest.

The lockfile as a whole never enters a key. Entity-naming Ops cache in two stages: the geometric result is keyed without `OpSite` and shared across designs, and a cheap relabeling stage is keyed with it. Deterministic errors are cached; environmental errors (cancellation, out of memory, device loss) never are.

### 7.3 Determinism

- `PlatformClass` [PLT]: `CpuCanonical { epoch }` (every Tier 1 CPU target, browsers included, at any thread count and ISA level), `CpuIsa { isa, epoch }` (a native fast path for one ISA level), `Gpu(GpuClass)` (one verified GPU device class with an epoch), `Unverified` (unlisted devices and external hosts). The operating system is never part of a class. In prose: "the canonical class".
- `DeterminismGrade` [KLN], declared per operation version: `Portable` (bit-identical across the canonical class; the only grade for geometry and oracle reference results), `ClassExact` (bit-identical within one class), `Certified` (output independent of the class that computed intermediates, for example GPU filtering with CPU decisions). Kiln selects the class an Op runs in; there is no separate execution-mode concept.
- Results from `CpuIsa`, `Gpu` and `Unverified` classes never substitute for canonical results. A check, release or Proposal that requires canonical results recomputes them in the canonical class. A release pins the `ObjectId`s of every External Op result it relies on.
- Mechanisms [PLT]: `detmath`, the only elementary-function library in `Portable` code (correctly rounded, ported from CORE-MATH); fixed 512-bit virtual vectors (8 × f64, 16 × f32) mapped onto NEON, SSE, AVX2, AVX-512 and SIMD128; fixed reduction trees (`det_sum`, `det_reduce`) and binned reproducible summation (`exact_sum`) where partitioning varies; no implicit FMA contraction anywhere, explicit `mul_add` only inside `detmath` and error-free transformations; exact integer-limb reductions on GPUs; NaN canonicalization.
- Determinism is verified continuously by a cross-platform determinism suite on every commit and by spot re-execution of shared-cache entries.

### 7.4 Wasm execution

- One determinizer, versioned, in `wasm-host` [PLT]. The registry runs it at publish time; the local toolchain runs it at build time for unpublished Wasm components; the Ingot compiler emits code that already satisfies its rules, and the determinizer verifies such modules instead of rewriting them. It validates the binary, rejects nondeterministic features, and injects NaN canonicalization, fuel metering and stack limits as ordinary Wasm instructions. Hosts execute only determinized binaries.
- Wasmtime (pinned to its LTS releases) runs Wasm natively with Cranelift; Pulley, Wasmtime's interpreter, runs all Wasm, Ingot included, on targets without JIT (iPadOS); browsers run registry-built bundles in their own engines. Fuel, never wall-clock time, bounds work; epoch interruption is never used.
- Evaluation worlds are synchronous and import no WASI; they may import `crucible:ops`. Tool and connector worlds (importers' file access, supplier connectors) use WASI 0.3. A determinized Wasm component whose host calls are all `Portable` is itself `Portable`.
- Constitutive models use the `crucible:material/constitutive` world. Models expressed in the kernel IR get tangents by algorithmic differentiation; opaque Wasm models must supply consistent tangents, verified by a Taylor-test oracle.

### 7.5 Shared kernel IR

One kernel IR, in the crate `kernels`, is the source of every compute kernel that affects results: weak forms, constitutive functions, analytic Fields, implicit tapes, constraint residuals, Network residuals and device models from Verilog-A. Hand-written kernels use the IR's Rust embedding. The IR fixes the order of every floating-point operation and reduction. Back ends: ahead-of-time Rust with canonical SIMD for std kernels; Wasm SIMD128 for user code compiled at run time; WGSL for GPUs through wgpu on every Tier 1 platform; CubeCL as an optional back end for CUDA and ROCm on servers. Every GPU path has a registered CPU path. Render shaders are WGSL and never affect results.

### 7.6 `api`, agents and UI

- One API over MCP and native SDKs (Rust, Python, TypeScript, plus a C ABI). Method groups: Session, Read, Edit, Evaluate, Inspect, Compare, Propose, Act. Registry, event and archive methods belong to these groups (search, fetch and subscribe are Read; publish, yank and export are Acts).
- Agents work only on branches, with scoped permissions, cost budgets and clearances. They must build, pass every check and attach snapshots before proposing. Untrusted content is labeled at ingestion and returned only as `ExternalText`; a session that reads its raw text becomes tainted and cannot merge or commit Acts without fresh human approval. Every agent Proposal is attacked by an independent verifier. Risk class is computed by the server from the semantic diff; auto-merge only for the two lowest classes.
- The UI holds no product state; every product change is an `api` Edit or Propose call. One Rust UI toolkit and wgpu renderer, native and Wasm; GPU tiers G1 (native), G2 (WebGPU), G3 (WebGL2), with identical features and declared capacity per tier. Display data are `DisplayPackage`s; camera, culling and selection run locally. Direct manipulation writes Ingot through ranked edit plans. Fields paint on the true geometry with stated error. Proposal review shows feature, geometry, metric and source diffs.

### 7.7 Interop and ecosystem

- Open formats are built in Rust as Wasm components generated from their schemas (one EXPRESS code generator for every STEP application protocol and IFC). Licensed translators for proprietary formats run as external tools outside evaluation, and their output enters builds only as External inputs, so anyone can rebuild without the licence.
- Imports are Ingot expressions over Assets; there is no imported state outside the program. Crucible never replays proprietary feature history; it imports geometry, structure, semantic PMI and metadata, and offers design-intent reconstruction as a reviewed Proposal.
- Registry: namespaces owned by verified publishers; trusted publishing only; Sigstore signatures and SLSA provenance; std and translators reproducibly built; yank but never delete; output-changing releases flagged.
- Licensing: code under Apache-2.0 WITH LLVM-exception; documentation CC-BY-4.0; examples and templates MIT-0; contributions under the DCO; company stewardship until a fixed trigger, then a foundation. Linked dependencies may use MIT, Apache-2.0, BSD, ISC, Zlib, Unicode-3.0 or MPL-2.0 (unmodified, or with changes published upstream). LGPL, GPL and AGPL code is never linked; it runs only as an external tool, an External Op or a test oracle.
- Releases ride a 6-week train (nightly, beta, stable) with one LTS release per year supported for 24 months, aligned with Wasmtime's LTS window.

## 8. State-of-the-art mandate

- For every major component, identify the best published method as of October 2026 (a paper, a standard or a leading implementation), cite it, and state Crucible's choice. The default is to adopt or beat the state of the art. Any deviation needs a stated reason: license, robustness, determinism, portability or maturity.
- Name the leading implementation to beat, the benchmark or dataset to measure on, and a performance or accuracy target, labelled as a target.
- Prefer methods that are robust, deterministic, parallel and SIMD- or GPU-friendly, and methods with provable guarantees where they exist.
- Every tab includes a `## State of the art` section with a table: Component · Best published method · Leading implementation to beat · Crucible's choice · How we measure.

## 9. Platforms

- **Tier 1** (full product, identical features, CI on every commit, every golden product passes): Windows 11 on x86-64 and ARM64; macOS on Apple silicon (current release and two prior); Linux on x86-64 and ARM64 (glibc 2.34 or newer, Wayland and X11); desktop browsers (Chrome and Edge, Safari, Firefox) through Wasm with WebGPU and a WebGL2 fallback.
- **Tier 2** (viewing, review and light editing; CI on every release): iPadOS and Android tablets, ChromeOS through the browser; phones as viewers.
- **Tier 3** (community-supported): FreeBSD and other Unix systems. A Tier 3 target joins the canonical class only after it passes the determinism suite.
- **Servers**: Linux containers on x86-64 and ARM64 for team servers and cloud workers; optional CUDA and ROCm acceleration.
- **Parity** means identical features and identical canonical results on every Tier 1 platform, whether computed locally or through remote evaluation on a team server or cloud worker. Capacity and speed may differ and are declared per platform and GPU tier. External Ops (native third-party binaries) run on hosts that support them and are reached remotely from every client; air-gapped installs need a local Linux worker.
- Core crates are OS-agnostic; OS services sit behind `platform-api` traits implemented once in `apps/platform`. The engine runs as a separate process on desktop, a worker in the browser, threads on tablets, or a remote server, and the UI always talks to it through `api`. Native x86-64 builds target x86-64-v2 with runtime dispatch to v3 and v4; ARM64 targets ARMv8 with NEON; SVE dispatch waits until Rust stabilizes scalable vectors. Accessibility goes through each OS's native accessibility API (AccessKit), plus a DOM mirror on the web.
- Every tab includes a `## Platform notes` section.

## 10. Coherence and taste

- **Fewest concepts.** Use the core types. Never invent a parallel abstraction.
- **One name per concept.** Follow section 2 exactly, including the "never call it" column.
- **Common things simple, advanced things possible.** Sensible defaults for the usual case; power revealed progressively.
- **Explicit over magic.** No silent fallbacks. Every approximation states its error.
- **Composition over special cases.** One general mechanism (Fields driving geometry, queries over provenance, checks everywhere, Approvals over digests) beats many one-off features.
- **Errors are guidance.** Every failure is typed, explains why, and suggests a fix.
- **One voice.** Present tense, precise, calm. No hype words ("revolutionary", "seamless", "cutting-edge", "world-class", "powerful"), no exclamation marks.
- **Say it once.** Each fact lives in the tab that owns it; other tabs state the consequence in one line and point to the owner.
- **One skeleton.** Every tab follows section 11.
- **Code style.** Ingot: `snake_case` for functions and features, `PascalCase` for types, units on every dimensional literal. Rust: the Rust API Guidelines.

## 11. Research and writing rules

Research:

- Cite only pages you actually opened with WebFetch; search snippets are not sources. Prefer primary sources. Mark anything unverified with [unverified]. Never invent version numbers, dates, statistics or customer names. Web search quota may be exhausted; use WebFetch on known primary URLs.

Every tab follows this skeleton, in this order:

1. A lead of one to three sentences under the tab title, stating the design in one breath (no heading).
2. Design sections (`##`, with `###` subsections).
3. `## State of the art`
4. `## Platform notes`
5. `## Interfaces with other subsystems`
6. `## Oracles`
7. `## Phasing`
8. `## Open questions`
9. `## Contract change requests` ("None" if none)
10. `## Sources`

Style:

- Tables for items compared on several attributes; numbered lists for sequences; code blocks for Ingot and Rust. Sentences under 25 words where possible; paragraphs of at most three sentences; specifics over adjectives; no emoji.
- For every capability: what it does, its contract, failure behavior, oracle and phase.
- Decisions inline: `**Decision D-<TAB>-<n>:** <decision>. *Why:* <rationale>. *Rejected:* <alternatives and why>.` Tab codes: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT. Decision numbers are stable: never renumber; a reversed decision keeps its number, states the new decision and ends with "(revised in round 2)".
- At most two diagrams per tab, marked `[[DIAGRAM: …]]` in drafts.
- Length after revision: 12,000 to 18,000 words per tab excluding Sources (Ingot and Anvil up to 20,000). Cut repetition, restated rationale, content another tab owns and prose that a table already says. Never cut a capability, decision, oracle or source. Targets are labelled as targets.

## 12. Crate map

Dependencies point down this list; apps talk to the engine only through `api`.

| Layer | Crates (all under `core/` unless noted) | Owner |
| --- | --- | --- |
| Platform | `platform-api`, `detmath`, `simd`, `runtime`, `gpu`, `wasm-host` | PLT |
| Contracts | `base` (shared value types from section 5 and the operation contract `OpImpl`, `OpCx`, `DeterminismGrade`); `cas` | KLN, with every owner of a type |
| Engine core | `kernels` (shared kernel IR and back ends); `field` (`Field`, domains, representations, `Sampler`); `kiln` | FLX, KLN |
| Geometry | `anvil-geom`, `anvil-topo`, `anvil-planar`, `anvil-mesh`, `anvil-implicit`, `anvil-ops` | ANV |
| Physics | `flux-forms`, `flux-solve`, `flux-couple`, `flux-opt` | FLX |
| Language | `ingot-syntax`, `ingot-types`, `ingot-ir`, `ingot-codegen`, `ingot-bindgen` with `ingot-macros`, `ingot-service` | ING |
| Product services | `repo` | KLN |
| Surface | `api` | AGT |
| Outside `core/` | `bridges/` (optional FFI: PETSc, hypre, CUDA specifics); `io/` (translators as Wasm components); `std/` (Ingot packages and first-party Wasm components); `wit/` (`crucible:` packages); `apps/` (`platform`, `ui-toolkit`, `renderer`, `desktop`, `web`, `mobile`, `server`, `cli`, `ci-runner`, `registry`, `headless-render`); `oracles/` (protected) | per tab |

`unsafe` is allowed only in `simd`, `gpu`, `wasm-host`, the code-loading parts of `kernels`, `bridges/` and `apps/platform`. Everything else is `forbid(unsafe_code)`.

## 13. Roadmap and golden products

| Phase | Theme | Gate |
| --- | --- | --- |
| 0 | Foundations | Determinism suite green on every Tier 1 target including browsers; unit errors fail to compile; trademark clearance with fallback names; freedom-to-operate reviews commissioned |
| 1 | Wedge: code-CAD and 3D printing | GP1 machined bracket (cut at a reference shop, measured by external metrology); GP2 topology-optimized lattice bracket (printed and measured) |
| 2 | Mechanical depth | GP3 gearbox; GP4 welded frame with sheet-metal guards, including measured weld distortion |
| 3 | Product breadth | GP5 molded enclosure with its PCB, including measured warpage and drop response; the board fabricated and assembled from Crucible outputs alone |
| 4 | Full multiphysics | GP6 drone, validated against flight, dynamometer and thermal test data |
| 5 | Scale | GP7 MEMS accelerometer; GP8 bolted steel platform round-tripped through IFC 4.3 with a structural check; GP9 crash box |
| 6 | Aerospace and electrification | GP10 composite wing box; GP11 CubeSat; GP12 EV battery sub-pack with BMS, harness and charger |
| 7 | Marine, buildings, medical and soft goods | GP13 workboat hull; GP14 timber pavilion (building product, IFC export); GP15 bone plate (ASME V&V 40 credibility); GP16 sewn pack (soft goods) |

Golden products 7 to 16 are proposals; each needs a physical test partner before its gate is fixed.

**Scope.** In: products made of parts, assemblies, boards, cables and software items, from MEMS to ships; building products and structures (prefabricated, steel, timber), exchanged with BIM tools through IFC 4.3; MEMS layout and chip-package design through GDSII and OASIS. Out: whole-building authoring (spaces, zones, whole-building energy); integrated-circuit logic layout; film and animation.

## 14. Ruling log

Status: Accepted, Modified (accepted with the change shown) or Rejected.

| CCR | Ruling |
| --- | --- |
| ING-1 three-valued checks; FLX-3 | Accepted. Name: `Undecided`. COV's `Indeterminate` becomes `Undecided`. |
| ING-2 `Approx<T>` | Accepted; carries an `ErrorBudget`. |
| ING-3 `Tol<T>` semantics; MEC-3 | Accepted as written in section 5. |
| ING-4 syntax reference | Accepted (section 6), with std names `std::materials` and `std::sim`. |
| ING-5 crate list | Accepted (section 12). |
| ING-6 language behavior version | Accepted (section 7.2). |
| ING-7 angle base dimension, torque | Accepted (section 5). |
| ING-8 one `Severity` | Accepted. |
| ING-9 MEC `constraint` and `interface` keywords | Accepted: `Expr<T>` functions and `#[interface]` records. |
| ING-10 `OpSite` in keys; ANV-5 | Modified: two-stage caching (section 7.2). |
| ANV-1 `ErrorBound` location | Modified: in `base`, not `anvil-geom`. |
| ANV-2 `EntityId` formula | Accepted (section 5). |
| ANV-3 canonical operation names | Accepted: Anvil's catalog is canonical; MEC, MFG and ELX adopt it. |
| ANV-4 `Query` notes | Accepted. |
| ANV-6 predicates for curved geometry | Accepted (section 7.1). |
| FLX-1 `ErrorBound` | Accepted. |
| FLX-2 Field axes; COV-8; MEC-4; MFG-1; ELX-1 | Modified: product domains, `Field<(Body, Time), V>`, instead of a third type parameter. `Field<D, V, A>` becomes `Field<(D, A…), V>`; `TimeSpan`, `FreqSpan`, `Sweep`, `Interval<Q>` and `StateDomain` become quantity-type domains. |
| FLX-4 platform classes; PLT-1 | Modified: PLT's enum (section 7.3). `cpu-f64` becomes `CpuCanonical`; `wgpu-f32`, `cuda-f64` and `rocm-f64` become `Gpu(GpuClass)` classes. |
| FLX-5 Kiln derivative support | Accepted. |
| FLX-6 crate list | Modified: `flux-field` becomes `field` and `flux-kernels` becomes `kernels`, both below Anvil; `flux-bridges` moves to `bridges/`. |
| FLX-7 statistical agreement for chaotic problems | Accepted (principle 4). |
| COV-1 `ErrorBudget` | Accepted. |
| COV-2 external tools; ELX-2; MFG-2; ECO-1 | Modified: two concepts. External Op (automatic, cached, host-labelled) for copyleft solvers, FMUs, IBIS-AMI, emulators; External input (pinned, explicit refresh) for translations, offers, machine data, measurements. |
| COV-3 Flux operations for non-variational methods | Accepted (section 7.1). |
| COV-4 `Material` extension | Accepted. |
| COV-5 envelope zones and dispositions | Accepted. |
| COV-6 scope | Accepted (section 13). |
| COV-7 physical tests in GP4 and GP5 gates | Accepted (section 13). |
| KLN-1 cache key by package closure | Accepted (section 7.2). |
| KLN-2 hardware CI | Accepted (section 7.1). |
| KLN-3 "node" | Accepted: node is any memoized computation; an Op is the node kind that calls an operation or Wasm component. |
| KLN-4 `DeterminismGrade` | Accepted. |
| KLN-5 service BOM | Accepted; "SBOM" is not used. |
| MEC-1 `CoordSys` | Accepted. |
| MEC-2 `ShapeAspect` | Accepted. |
| MEC-5 feature-level role aliases | Accepted (`FeatureRole`). |
| MFG-3 approval bound to content hashes | Accepted as the `Approval` concept. |
| MFG-4 `Money<C>` | Accepted as a std type. |
| ELX-3 remote execution counts as parity | Accepted (section 9). |
| ELX-4 Software item | Accepted. |
| ELX-5 `Circuit` as a core type | Modified: the type is `Network` (lumped models in every domain); builder `network { … }`. |
| ELX-6 interop list | Accepted; ECO's standards catalog is canonical. |
| ELX-7 Wasm components may call operations | Accepted: `crucible:ops`. |
| AGT-1 Session and Act groups | Accepted (section 7.6). |
| AGT-2 "Evaluation" | Accepted. |
| AGT-3 "API method" | Accepted. |
| AGT-4 `Labels` and `DataClass` | Accepted, unified with licences and integrity (section 5). |
| AGT-5 `Proposal` fields | Accepted. |
| AGT-6 `ExternalText` | Accepted. |
| UIX-1 `ResultStatus` | Accepted as an `api` type over Kiln's `Fidelity`. |
| UIX-2 parity definition | Accepted (section 9). |
| UIX-3 `DisplayPackage` | Accepted. |
| UIX-4 `ViewState` | Accepted. |
| ECO-2 translators outside evaluation | Accepted. |
| ECO-3 evaluation worlds import no WASI | Accepted. |
| ECO-4 determinized Wasm keys | Accepted: `Portable` when all host calls are `Portable`. |
| ECO-5 name clearance | Accepted as a phase 0 gate. Flux (flux.ai, a PCB tool) and Crucible (Atlassian, until 2028) need fallback names. |
| ECO-6 one WIT namespace | Accepted; tangent policy in section 7.4. |
| ECO-7 packages hold data | Accepted. |
| PLT-2 SVE deferred | Accepted. |
| PLT-3 crate list | Accepted (section 12). |
| PLT-4 instrumentation version in key | Subsumed: the determinized binary's hash is the key. |

Conflicts resolved without a CCR:

| Conflict | Ruling |
| --- | --- |
| GPU code generation (FLX D-FLX-10 vs PLT D-PLT-16) | One shared kernel IR with WGSL and optional CubeCL back ends (section 7.5). PLT's `gpu` owns devices, buffers, exact reductions and the CPU-fallback registry, not a kernel language. |
| Math library ownership (FLX D-FLX-11 vs PLT D-PLT-17) | `detmath` is PLT's and is the only one; Flux uses it. |
| Retired operation versions (ANV D-ANV-18 vs KLN D-KLN-4) | Archived Wasm builds first; `OpVersionRetired` only where impossible (section 4). |
| No-JIT execution (ING D-ING-13 vs PLT) | Pulley runs all Wasm on no-JIT targets. Ingot's reference interpreter serves cold start, debugging, replay and differential testing. |
| Determinizer location (ECO D-ECO-8 vs PLT D-PLT-22) | One versioned determinizer at publish and at local build; hosts verify (section 7.4). |
| Fidelity vocabulary (KLN, FLX, ANV, UIX) | `Preview`, `Interactive`, `SignOff` everywhere; "exact" keeps its geometric meaning only. |
| Variant and requirement syntax (KLN) | No new keywords (section 6). |
| Flex PCB bend (ELX `anvil::bend`) | `anvil::fold`. |
| Planar geometry (ELX request) | `anvil-planar` owned by Anvil (section 7.1). |
| Lockfile name (`crucible.lock` in KLN) | `ingot.lock`. |
| std path names | Section 6. |
| Golden products beyond 6 (COV, MEC, ELX, FLX, ECO, UIX disagreed) | Section 13. |
| Execution mode (PLT `ExecMode`) | Removed; Kiln selects the platform class. |
| Multibody and rod models (MEC request, missing from FLX) | Flux owns them (section 7.1). |
| Cost ownership | MFG owns cost models; ECO owns quoting connectors and the marketplace; agent budgets are compute budgets owned by AGT. |
| Life-cycle assessment ownership | MFG owns product LCA and passports; COV owns material environmental records. |
| Package registry ownership | ECO. |

### Required edits by tab

- **ING:** std names; `Field<(D, …), V>` syntax; Pulley on no-JIT targets (reference interpreter keeps its other roles); determinizer verification of Ingot modules; `Undecided`; `Network` builder; `ExternalText`; no keywords for variants or requirements.
- **ANV:** `ErrorBound` in `base`; `field` and `kernels` crate names; add `anvil-planar` with its operations and the constraint solver to the catalog if missing; `anvil::fold` serves flex circuits; retired versions as archived Wasm; `CpuCanonical`; `Fidelity` names; publish the canonical name mapping for MEC, MFG and ELX.
- **FLX:** `Field<(D, …), V>`; crates `field` and `kernels`; WGSL and optional CubeCL back ends from the shared IR; `detmath`; class names; add multibody, Cosserat rods, Network compiler and DAE solver, block-triangular LU, full-wave EM, magnetodynamics with motion and the COV-11 operations; `std::sim`; constitutive tangent policy.
- **COV:** `Undecided`; External Op (replacing "external tool Op"); product-domain Fields for properties; GP numbering per section 13; `std::physics` and `std::materials`.
- **KLN:** node and Op definitions; `ingot.lock`; `CpuCanonical`; retired versions via archived Wasm; service BOM; no `options`, `when`, `requirement` or `verifies` keywords; `Labels`; External input and External Op as Kiln inputs and nodes; drop `ExecMode` references.
- **MEC:** Anvil canonical operation names; `Expr<T>` constraints and `#[interface]` records; product-domain Fields (`Field<(Instances, Time), Transform>`); flex and rod models from Flux; GP numbering.
- **MFG:** Anvil canonical names (`section` for slice, `offset_curve`, `medial_axis`, `tool_contact` for tool drop and push, `interference` and `swept_volume` for collision); `anvil::planar` for 2D cutting where integer exactness helps; External input for signed data packages; `Approval`; `Money<C>`; service BOM; GP numbering.
- **ELX:** `Network` and `network { … }` instead of `Circuit`; `anvil::fold`; `anvil::planar::*`; External Op for FMUs, IBIS-AMI and emulators; product-domain Fields (`Field<(Ports, Time), Voltage>`); `std::electronics` and `std::systems`; Software item; GP numbering.
- **AGT:** method groups and Act semantics as in section 7.6; `Labels`; `ResultStatus`; Evaluation; API method naming.
- **UIX:** `Fidelity` and `ResultStatus` names; `DisplayPackage` and `ViewState` as core types; GP numbering.
- **ECO:** External input and External Op definitions; WIT namespace; dependency license policy (section 7.7); GP numbering; determinizer at publish and local build.
- **PLT:** remove `ExecMode`; `gpu` owns devices, buffers and exact reductions rather than a CubeCL kernel language; one determinizer at publish and local build; crate map (section 12); Pulley runs Ingot too.
