# Crucible architecture contract (v4.1)

Binding for every design agent and reviewer. Version 4 integrates the rulings on the first round's contract change requests (section 14) and on the adversarial review (section 15); version 4.1 rules on the change requests of the first revised tabs (section 16). Where a draft disagrees with this contract, the contract wins. If you believe a ruling is wrong, do not work around it: say so under "Contract change requests" with your reason.

## 1. Mission

Crucible is one Rust platform where people and agents design, simulate, manufacture and release physical products from a single typed model. Every subsystem must be specified completely enough that an engineering team, and agent swarms working against oracles, could start building. "Fully specified" means every capability has a purpose, a contract (inputs, outputs, types), failure behavior, an oracle that verifies it, and a phase.

Four hard requirements from the founder:

1. **Anything physical.** Every major physics domain and every scale from MEMS to ships and building products. Honesty rule: no software validly simulates literally everything, so every model states its validity envelope, the spec says plainly what is out of reach, and it defines how new physics and domains are added.
2. **State-of-the-art, optimized methods** for every component and every simulation (section 8).
3. **Every major operating system, identical features** (section 9).
4. **Supreme coherence and taste** across the whole design (section 10).

## 2. Canonical names and glossary

| Name | What it is |
| --- | --- |
| Crucible | The platform (working name; full trademark clearance in classes 9 and 42 is a phase 0 gate, assuming Atlassian's mark persists) |
| Ingot | The design language; source files end in `.ingot`; package manifest `ingot.toml`, lockfile `ingot.lock` |
| Anvil | The geometry kernel |
| Flux | The physics and simulation engine (working name; collides with Siemens Simcenter Flux and flux.ai, so it is renamed in phase 0 before any operation name or WIT package freezes) |
| Kiln | The incremental evaluation engine |
| CAS | The content-addressed store for all derived artifacts |
| `repo` | The repository crate: Changes, branches, merges, releases, change orders, BOM |
| `api` | The single API used by the UI, agents, CLI and CI, exposed over MCP and native SDKs |
| std | The standard library of Ingot packages |
| Golden products | Reference products whose passing checks close each phase |

No other codenames. One name per concept, one concept per name:

| Term | Definition | Never call it |
| --- | --- | --- |
| **Operation** | A versioned primitive implemented in native Rust inside Anvil or Flux (`anvil::blend@2`, `flux::solve_linear@1`). Pure; deterministic per its determinism grade. | "op" in prose, "kernel", "function" |
| **Feature** | An Ingot function that captures design intent by orchestrating operations; the unit people see in a design's history. | "macro", "script" |
| **Wasm component** | A sandboxed, native-speed extension with a WIT interface, determinized before it runs (section 7.4). | bare "component", "plugin" |
| **Node** | One memoized computation in Kiln's graph: a front-end stage, a feature call, an Op, a check, a query resolution or a derived view such as a BOM. | "job", "task" |
| **Op** | A node that calls one operation or one Wasm component; its cache key is an `OpKey`. | |
| **External Op** | An Op whose implementation runs outside the sandbox in an isolated host (a pinned container image for a copyleft solver, an FMU or IBIS-AMI host, a firmware emulator). Runs only on untrusted-evaluation workers (section 7.8). Cached by input hashes plus the host image digest; its results carry the host's platform class or `Unverified`. | "external tool run", "out-of-process result" |
| **External input** | Signed, content-addressed data produced outside evaluation (a licensed translation, a supplier offer, a catalog or regulation data package, a machine reading). Pinned in `ingot.lock` and read by Kiln as a leaf input; changes only through an explicit update. | "snapshot", "data package" for this meaning |
| **Evidence record** | A signed measurement from a physical test (a hardware rig, a CMM, a test lab), addressed by the check it serves and the `GeometryId`s of the inputs it tested. An evaluation reads the newest valid evidence record and stores its `ObjectId` in the `CheckOutcome`; releases and approvals pin the evidence ids they cite. | "measurement cell", "hardware result" |
| **Asset** | A non-source file stored in a design repository (a STEP file, a scan, a PDF datasheet), content-addressed and referenced from Ingot. | |
| **Evaluation** | One request to Kiln to compute a set of nodes for a revision, with a lifecycle (queued, running, done, aborted), streamed results and a report. | "job", "run", "build request" |
| **Check** | A predicate declared with `require`, evaluated as its own node; its result is a `CheckOutcome` (section 5). | "assertion", "rule result" |
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
| **Approval** | A human principal's signature over the `ObjectId` of an approval subject (section 5). Any change to the subject voids it; changes outside the subject (a rebase, a CI re-run, a refactor) do not. | "sign-off" as a noun for this |
| **Act** | An API method with an effect outside Crucible: release, yank, export, order, request a quote, send to a supplier, transfer a program or job to a device, start a print, publish a package or passport. Always two-phase: `act.prepare` produces a plan with a digest; `act.commit` runs only after an assigned human Approval of that digest (section 7.6). Physical-effect Acts are transfer Acts or the restricted `start_print`; Crucible never starts machine tools, robots, lasers, presses or furnaces (section 7.6). | "action" for this meaning |
| **API method** | An entry in the `api` catalog, named `<group>.<name>`. | "operation" |
| **Change** | One immutable fine-grained edit, like an Onshape microversion. "Revision" is reserved for PLM item revisions. | "commit" (except when comparing with Git) |
| **Design repository** | The repository holding one product's Ingot source, Assets, `ingot.lock` and history. | |
| **Snapshot** | A rendered image of a `ViewState` with structured marks, attached to Proposals and reviews. Never used for data. | |
| **Fidelity** | The accuracy a result is demanded at: `Preview` (fastest, approximate, never written to the shared cache), `Interactive` (approximate with an error estimate), `SignOff` (converged or exact). | "coarse", "exact" as fidelity names; "sign-off mode" |
| **Platform class** | The set of execution environments whose results are bit-identical (section 7.3). | |
| **Determinism grade** | What an operation version guarantees: `Portable`, `ClassExact` or `Certified` (section 7.3). | "execution mode" |
| **Labels** | The label lattice attached to every artifact, API response and model context (section 5). | "taint flags", "classification tags" as separate concepts |
| **Abort** | An environmental end to a computation (cancellation, resource exhaustion, device loss, budget exhaustion, worker loss, demand-depth or Evaluation fuel limit). Not a `Failure`: never catchable, never cached (section 7.2). | "error" for this meaning |
| **Service BOM** | The BOM view for service and spare parts. The abbreviation SBOM is never used; "software bill of materials" is always spelled out. | "SBOM" |

## 3. Principles (non-negotiable)

1. **No privileged code.** Built-in features use only the public mechanisms anyone can use: Ingot for features, Wasm components for heavy algorithms, and versioned Anvil and Flux operations underneath. If a user or agent cannot build a feature, neither can the core team.
2. **One model, three editors.** The visual editor, the code editor and agents edit the same typed program. Nothing exists only in the GUI.
3. **Two universal types.** `Body` carries geometry and `Field` carries physics data. Models (weak forms, Networks) describe how Fields are computed; libraries consume and produce Bodies, Fields and plain values.
4. **Determinism is a feature.** Same inputs and versions give identical outputs per platform class; cross-class results agree within declared tolerance, or, for chaotic problems, in declared statistics. Problems with bifurcations or multiple solutions declare branch selection explicitly (an imperfection or symmetry-breaking input) or declare agreement on branch-invariant quantities. Evaluation never depends on clocks, randomness, thread order or names (section 7.3).
5. **The compiler checks physics.** Units, dimensions and tolerances are types, checked before anything runs. Every approximation carries its error, in a stated norm.
6. **Every claim has an oracle.** No capability ships without a machine-checkable test that agents cannot edit.
7. **Open core, interop first.** Kernel, language and standard library are open source. Open standards are first-class; no design is ever trapped.

## 4. Layering: operations, Wasm components, features (D-ARCH-1)

- **Operations, in native Rust.** Geometry and physics algorithms live in Anvil and Flux crates behind stable, versioned contracts; a few hundred primitives. Each operation version is frozen by content hash once released. A design pins the versions it was built with. Retired versions stay executable from archived Wasm builds of their frozen source; only versions that cannot compile to Wasm (GPU `ClassExact` paths) fall back to an `OpVersionRetired` failure whose fix is an upgrade Proposal.
- **Wasm components, for heavy custom algorithms.** Nesting, CAM strategies, slicers, placers and routers, importers, specialist solvers. Sandboxed, determinized, portable to every OS and the browser, published in the registry. Evaluation-world Wasm components may import the WIT package `crucible:ops`, whose generated interfaces `crucible:ops/anvil` and `crucible:ops/flux` expose versioned operations, including GPU-backed ones; each call is a recorded Op dependency. They never get raw GPU, clock, file or network access.
- **Features, in Ingot.** Design intent, orchestration, entity selection and naming, checks and UI metadata.
- **Tier rule (D-ECO-6).** Use Ingot unless code needs more than about 10⁶ primitive steps per call, an existing codebase in another language, or a data structure Ingot cannot express efficiently; then a Wasm component. Promote to an operation when at least three independent packages need it, it needs GPU or SIMD kernels, or it must be differentiable through Flux's form-level derivatives. Promotion happens in public, with oracles.
- **Fallback.** Features may be authored in Rust as Wasm components through `#[ingot::feature]`, which generates the WIT world and a typed Ingot wrapper (D-ING-15).

## 5. Core cross-subsystem types

Rust names are canonical; shared types live in `base` unless another crate is named. Owners in brackets.

**Values**

- `Quantity<D>` [ING]: a number with dimension `D`. SI base dimensions plus plane angle as a base dimension (radian coherent, never cancelled implicitly). Rotational kinds use the strong angular system: `Torque` = J/rad, `MomentOfInertia` = kg·m²/rad², `RotationalStiffness` = J/rad²; std defines named units so datasheet literals stay short (`Nm` is newton metre per radian; energy is written `J` or `[N*m]`). Affine quantities: °C and °F are points, kelvin values are differences, `.absolute()` converts. Complex quantities. Every dimensional literal carries its unit; there are no default units; conversion is exact rational with one rounding. Checked at compile time, erased at runtime. ING publishes the consistent system and an oracle of at least 50 textbook rotational, electrical and thermal formulas that type-check without casts.
- `Tol<T>` [ING]: a toleranced value. Arithmetic is worst case by default, using affine forms over per-site noise symbols so repeated uses stay correlated; statistics (RSS, Monte Carlo, distributions, correlation groups) are explicit calls. A `Tol<T>` may be passed wherever `T` is declared: the body computes with the nominal and the tolerance's site is forwarded to the feature that realizes it, which attaches it as PMI.
- `ErrorBound<Q>` [`base`]: `{ value: Q, norm, kind }`; norm `LInf`, `L2`, `Energy`, `Pointwise` or `Goal(functional)`; kind `Guaranteed`, `Estimated { calibration }` or `Indicator`. A `Guaranteed` bound on a quantity requires a proof in that quantity's norm. Energy-norm bounds never certify pointwise or extremal quantities; `Guaranteed` goal bounds exist only for bounded linear functionals (regional averages over a stated volume, reaction resultants, compliance, mean temperature).
- `ErrorBudget<Q>` [`base`]: `{ parts: map ErrorSource → Component<Q>, total: Component<Q> }`, where `Component<Q>` is `Quantified(ErrorBound<Q>)` or `NotQuantified { reason }`. `ErrorSource` is one of: discretization, algebraic, temporal, quadrature, geometry, floating point, input and tolerance, statistical, model form, reduction or surrogate, interpolation, regularization. Composition: bounds in the same norm add; bounds in different norms never combine (the total is `NotQuantified`); components carrying a confidence (statistical, conformal, input distributions) become bounds at a stated per-component level and combine by a union bound, so the total carries confidence 1 − Σαᵢ; distributions are reported alongside and never summed with intervals. The total is `NotQuantified` if any part is, and its kind is the weakest part's.
- `Approx<T>` [ING]: a value with an `ErrorBudget<T::Delta>` restricted to `Pointwise` and `Goal` norms. Comparisons return `Truth`. A reduction of a Field (a maximum, an average) is `Quantified` only when Flux estimated that functional; otherwise it is `NotQuantified` and comparisons on it are `Undecided`.
- `Truth` [ING]: `True`, `False`, `Undecided`. One decision rule, owned by ING and used by `if`, `require` and query `where:`: disjoint enclosures decide, subject to the check's declared evidence; `if` on an `Undecided` fails loudly with the margin and the accuracy needed.
- `Money<C>` [std, with Rust `Money { amount: Decimal, currency }` in `base`]: a decimal amount with an ISO 4217 currency type parameter; not a `Quantity`; no implicit conversion.
- `ExternalText` [ING, AGT]: untrusted text with origin, written `external("...")`; never interpreted as instructions.
- `Labels` [`base`, KLN, AGT]: a product lattice `{ level, controls, scopes, integrity, licences }`: `level` is public < internal < confidential; `controls` is a set of (regime, classification) pairs such as (ITAR, category) or (EAR, ECCN); `scopes` is a set of organization-defined scopes such as `customer:<name>` or `program:<name>`; `integrity` is `{ instruction_tainted, data_untrusted }`; `licences` is a set of `DataLicence`. The join takes the maximum level and the union of each set. A principal may read a value only if it satisfies every element. Labels are joined through every derivation by Kiln, carried by every model context (section 7.6), and enforced by `api` at every boundary.
- `PrincipalId`, `Budget`, `PriorityClass`, `ResultStatus`, `CheckOutcome` and the `PlacementPolicy` trait (which `repo::policy` implements and Kiln calls) live in `base` so that `kiln` never depends on layers above it.

**Geometry and product structure**

- `Body` [ANV]: geometry in one of four representations: `BRep` (exact NURBS, analytic and procedural surfaces, cellular topology with regions), `Implicit`, `Mesh`, `SubD`. Representation lattice: Mesh ⊂ BRep, SubD ⊂ BRep, BRep ⊂ Implicit. Mixed operations return the least representation that holds both operands without approximating geometry or dropping B-rep faces that remain on the boundary (leaf-preserving conversion keeps exact faces, their `EntityId`s and attributes). Approximating conversions record per-face bounds `{ position: ErrorBound, normal: angle bound }`, which compose through stated propagation rules with certified conditioning (offsets, intersections, blend spines, Natural-offset corners) or become `NotQuantified`.
- Two identities for every named value: `GeometryId` hashes the canonical encoding with names, lineage and name-keyed attributes removed (entities numbered in a canonical geometric order); `ObjectId` hashes the full encoding with names. Caching, revision identity and approvals use them as section 7.2 says.
- `Part`, `Assembly`, `Instance` [MEC]; `Transform` (rigid placement); `CoordSys` (a `Transform` anchored by a `Query`, re-resolved on every rebuild) [MEC]; `ShapeAspect` (an identified portion of a Body's boundary for GD&T, kinds such as `OfSize`, `Hole`, `Pattern`; named after AP242's `shape_aspect`) [MEC].
- `OpSite` [ING]: the identity of a call site, derived from source text only. A `let` statement's identity is (item path, arm path, binding name). An unnamed statement's identity is (item path, arm path, nearest preceding binding name, ordinal after it). A call's identity inside a statement is its operation or feature name with its occurrence index among calls of that name. Iteration contributes keys, never positions: iteration over entity lists or resolved queries keys by `EntityId`; pattern generators return keyed lists (`linear` keys `(i, j)`, `circular` the angular index, `at_points` the anchor's `EntityId`, `fill` lattice coordinates from a declared origin, `by_density` each seed's initial key); only plain integer ranges keep integer keys. Renaming a binding is a refactor that writes `#[was(old_name)]` and preserves identity. CRDT block ids are never part of an `OpSite`; they map onto these identities for live collaboration only. Exporting to Git, re-importing and rebuilding leaves every `EntityId` unchanged.
- `EntityId` [ANV]: hash of (kind, `OpSite`, role, generating entity ids, discriminator). Argument values are excluded, so dimension edits never rename entities. Features may attach role aliases (`FeatureRole`) to entities they return.
- `HistoryRecord` [ANV]: created, modified, split from, merged from, deleted.
- `Query` [ING, ANV]: criteria over provenance and roles plus certified geometric filters, resolved by `anvil::resolve` as its own Op on every rebuild. No positional indexing. Rank selectors (`longest`, `largest`, `first(along:)`) are allowed only after a provenance anchor or role filter; elsewhere the language service raises `ING-L-FragileSelector`. Failure is a typed `ResolveError` with ranked fixes; success may carry Notes (`Merged`, `FragileAnchor`, `RankSwap`) that checks may forbid. Each operation declares per `Query` parameter whether it uses a surface (accepts a merge with a note) or an extent (edges of a face, areas, GD&T and PMI targets, drawing items), where a merge fails with `ResolveError::Merged` unless `on_merge: Accept` is written. Never silently picks another entity.
- `DisplayPackage` [ANV, UIX]: a per-Body cluster-DAG tessellation with stated chordal error and `EntityId` back-references, cached in CAS and consumed by every renderer.
- `ViewState` [UIX]: camera, visibility, sections and Field displays; stored as repository files; used by the UI, agents, snapshots and comments.

**Physics**

- `Field<D, V>` [`field`, FLX]: a quantity over a domain `D`. Domains are spatial or entity sets (`Body`, `Regions`, `Faces`, `Edges`, `Vertices`, `Points`, `Instances`, `Ports`), parameter domains named by a quantity type (`Time`, `Frequency`, `Temperature`, `AngularVelocity`, `StrainRate`, …), index sets (`Mode`, `LoadCase`, `Sample`, `Variant`), and products written as tuples. Examples: `Field<Body, Stress>`, `Field<(Body, Time), Temperature>`, `Field<Temperature, YoungsModulus>`, `Field<(Instances, Time), Transform>`, `Field<(Ports, Frequency), Complex<Impedance>>`, `Field<AngularVelocity, Length>` (a stability lobe), `Field<Body, ValidityZone>`. Values may be scalars, vectors, tensors, complex values or enums. Representations: `Analytic`, `Discrete`, `QuadraturePoint`, `SparseGrid`, `PerEntity`, `PointCloud`, `Reduced`, `Surrogate`. A `Part` is accepted wherever a `Body` domain is expected. Every result Field carries an `ErrorBudget`. Waveforms, spectra, sweeps, mode sets, load cases, ensembles, tables and material curves are all Fields, never separate types.
- `Network` [ELX, FLX]: see glossary. Each port type declares its power expression, and the compiler checks that it is a power.
- `Material` [COV]: properties as Fields over state domains (temperature, strain rate, direction), statistical basis per property, constitutive model ids, provenance, certification, uncertainty, `DataLicence`, environmental records and microstructure descriptors.
- `ValidityEnvelope` [COV]: declared conditions where a model is trusted. Evaluates to a zone Field (`Calibrated`, `Extrapolated`, `Invalid`, `Unassessed`) and to checks with disposition `Flag` or `Refuse`. Only humans waive. Crucible suggests escalation to a valid model but never switches models automatically.

**Evaluation and collaboration**

- `Feature` [ING]: an Ingot function from typed parameters to Parts, Bodies or plain values, with metadata that generates its dialog, docs and agent tool schema.
- `Op`, `OpKey`, `OpCx` [KLN, in `base`]; `ObjectId`: SHA-256 identity of a canonical CAS object, with a one-byte algorithm code reserved.
- `CheckOutcome` [ING, in `base`]: `{ verdict, fidelity, evidence, value, limit, margin, severity, source }`. `verdict` is `Pass { conditional_on }`, `Fail`, `Undecided { reason, needed }`, `Error(Failure)` or `Skipped { reason }`. A `Pass` whose `conditional_on` lists unquantified components (typically model form) is conditional: it meets a release gate only when repository policy names, for each listed component, a covering allowance with a citation (for example a design-code partial factor that the code states covers model uncertainty); the check is then re-evaluated with that allowance as a declared `Estimated` component, and without such a policy entry the verdict is `Undecided { reason: Unquantified(components) }`. "Provisional" is the derived predicate "fidelity below the declared one", never a verdict. `Severity` is `Error`, `Warning` or `Info`.
- `Fidelity` [KLN]: `Preview`, `Interactive`, `SignOff`.
- `ResultStatus` [`base`]: what a consumer holds for a demanded result: `Pending`, `Proxy`, `Ready(Fidelity)`, `Stale`, `Failed`, `Aborted`.
- `PlatformClass`, `DeterminismGrade` [PLT, KLN] (section 7.3).
- `Proposal` [AGT, `repo`]: branch, rationale, CI report, author, delegation chain, parent and plan, risk class, labels, snapshots, provenance.
- `ApprovalSubject` [KLN]: `{ base revisions, ItemDefinition GeometryIds with PMI attached by canonical entity number, check-verdict digest (check id, verdict, fidelity, platform class, value, limit), effectivity, evidence record ids }` for releases and change orders. Approvals sign its `ObjectId`; the `ChangeId` and the full CI report are unsigned provenance. Act plans and manufacturing programs have their own subjects (the plan digest; the posted program and its simulation evidence).

## 6. Ingot syntax reference

The canonical example. Every tab's examples follow Ingot's grammar; ING owns refinements and must keep this example valid.

```
use std::mech::{sketch, rect, extrude, rib, fillet, part}
use std::materials::alu_6061_t6
use std::sim::quick::static_stress

/// L-bracket with a stiffening web.
#[feature(category: "Structure", icon: "bracket")]
pub feature bracket(
    #[ui(step: 5mm)]
    width: Length in 20mm..=400mm = 60mm,
    thickness: Length = 4mm ± 0.1mm,
    load: Force = 1.2kN,
) -> Part {
    let outline = rect(width, 40mm)
    let base = sketch(plane.xy) { outline } |> extrude(thickness)
    let web = base.face(role: end_cap).edge(role: side(outline.top)) |> rib(height: 20mm, t: thickness)
    let body = base + web
    let solid = body |> fillet(body.edges(new), 2mm)
    let p = part(solid, name: "Bracket").material(alu_6061_t6)
    let clamp = base.face(role: start_cap)
    let study = static_stress(p, fixed: clamp, force: load, on: web.face(role: end_cap))
    let stress = study.von_mises.max(over: p.away_from(clamp, 2 * thickness))
    p.require(stress < 0.6 * p.material.yield_strength(at: 20degC))
}
// width + load  →  error ING3001: cannot add Length and Force
```

The edge is selected by the role its profile edge generates, never by rank. The stress check reads a regularized maximum over a region that excludes the clamp, because stress is singular where a clamped face meets a free face; the result is an `Approx<Stress>` with an `Estimated` bound, and the check is three-valued.

Weak forms:

```
let u = trial(Displacement, p)
let v = test(u)
let elasticity = inner(sigma(u, p.material), eps(v)) * dx(p)
              == dot(traction, v) * ds(web.face(role: end_cap))
let result = solve(elasticity, fixed: clamp)
result.von_mises  // Field<Part, Stress>
```

Language rules every tab follows: no new keywords for domain concepts. Constraints are ordinary functions over `Expr<T>`; interfaces are records marked `#[interface]`; variants are enum or record parameters marked `#[configuration]` on assembly features and selected with `if` and `match`; an Instance's existence may depend only on configuration parameters and constants (a compile error otherwise), so Kiln can compute the 150% BOM by abstract interpretation with SAT checks instead of enumeration; variant rules and requirements are `require` checks and `std::systems` records; builder blocks (`sketch { … }`, `network { … }`) are the only block sugar. Constitutive code never differentiates through loops: local Newton solves use the kernel IR's `local_solve(residual, x0)`, whose derivative comes from the implicit function theorem at the converged point.

**std package names.** `std::mech`, `std::mfg`, `std::electronics`, `std::systems`, `std::sim` (Flux building blocks: spaces, forms, `solve`, plans, quick studies), `std::physics` (physics models built on `std::sim`), `std::materials`, `std::opt`, `std::uq`, `std::agents`, `std::explore`. Sub-packages nest under these (`std::physics::regime`, `std::agents::proposal`). First-party packages outside std use `crucible::`; catalog parts use `parts::<manufacturer>::`; WIT packages use the `crucible:` namespace, one package per domain.

## 7. Decided architecture (do not contradict without a change request)

### 7.1 Engines

- **Anvil.** One Body type over four representations with the lattice above. Cellular B-rep with regions for multi-material parts and conformal meshing. Per-Body scale-relative resolution plus per-entity tolerances; no global tolerance. Exact adaptive predicates for linear decisions; certified enclosures with recorded, capped tolerance growth for decisions on curved geometry, made in rounds by dimension against tolerances frozen at each round's start, so outcomes never depend on pair order. Every operation checks separation of created and modified entities against the whole Body through the broad phase, not only against neighbours. Surface-surface intersection: GPU sampling orders CPU work and runs an exact integer broad phase; every intersection point is a certified root of the exact equations, never a point selected from a sample set by a distance threshold. Freedom-to-operate review of US 12,229,885 B1 (inventor Alyn Rockwood, assignee an individual; Zoo's engine overview describes a related method) covers claims 1, 6, 11 and 16, the CPU and GPU paths and pending continuations; until the opinion arrives, SSI itself is a phase 1 release risk. History records in every operation. Blends are a staged research program: stage 1 supports procedural blend, offset and swept supports (sequential fillets), `RollOver` overflow, valence-3 corners with unequal radii and mixed convexity by setbacks, chamfer–fillet corners, termination at smooth edges and linearly varying radius; later stages add valence four and above, Field-driven radii and G2 and G3 sections; an implicit fallback only when requested, with stated deviation. G2 and G3 analysis built in. Anvil owns all mesh generation, including volume meshing, adaptation and node optimization; Flux passes sizing and metric Fields. Anvil owns the geometric constraint solver (`anvil::solve_constraints`, `anvil::analyze_constraints`). Anvil owns `anvil-planar`: exact predicates on stored integer-coordinate 2D geometry with lines and arcs; constructions (offsets, Minkowski sums with a disc, arc intersections) snap to the grid in a declared conservative direction, so derived geometry passes the exact rule checks by construction (`anvil::planar::boolean`, `offset`, `distance`, `medial_axis`). Flex circuits bend with the sheet-metal `anvil::fold`. Anvil's operations catalog is the canonical list of operation names.
- **Label invariance.** An operation's geometry, connectivity, Field values and statistics are invariant under any injective renaming of input `EntityId`s and `OpSite`s; only name sections may change. Canonical orders, symbolic-perturbation indices, independent-set priorities and random seeds come from geometry, topology and argument values, never from names. Oracle: rebuild every golden product with every name re-randomized; geometry hashes and check values are identical.
- **Flux.** Physics stated as weak forms in Ingot, compiled through the shared kernel IR (7.5). Discretization is chosen per region: dimensionally reduced models where a local slenderness criterion holds (Timoshenko and Vlasov beams for members and struts; Reissner–Mindlin shells on Anvil mid-surfaces for thin walls, by a local criterion t/L_local ≤ 0.2, where L_local is the smallest of the span between supports, the radius of curvature and the distance to the nearest load or feature), coupled to solids through rigid and Nitsche-based mixed-dimensional interfaces; an immersed adaptive octree for solids (shifted boundary at `Interactive` with at least four cells across any section and a surrogate-domain connectivity check, CutFEM at `SignOff`, finite cell for voxel data); fitted meshes for contact and boundary layers; beam-lattice models with node corrections and homogenization for lattices; isogeometric shells. Matrix-free high-order FEM with sum factorization; own p- and h-multigrid and deterministic AMG; a canonical linear-algebra crate (fixed machine-independent blocking, canonical lane order, no FMA) for `Portable` results, with unmodified faer only in `CpuIsa`; optional PETSc and hypre bridges. Discrete-consistent adjoints from forms, chained through Kiln. The resolved `SolvePlan` (from a versioned `flux::plan` operation) is pinned and enters the cache key. Every result Field carries an `ErrorBudget`. Peak and pointwise quantities are regularized goals (a p-norm or a local average over a stated region, with the regularization error in the budget) and carry `Estimated` bounds; a raw maximum is never a goal. Singular points (re-entrant edges, edges where the boundary-condition type or material changes, contact boundaries, edges of fixed or loaded patches) make point quantities `Undecided { SingularPoint }` unless the check names a region excluding a stated distance from them. Interactive bounds are reported already multiplied by their calibrated factor and labelled `Estimated { calibration }`. Surrogate predictions are Fields with kind `Estimated { confidence, scope: Marginal }`; they may drive `Preview` and `Interactive` results and design exploration; a `SignOff` check may use one only with a per-prediction a posteriori bound or a confirming solve; inside optimization loops calibration uses weighted conformal prediction. Newton and arc-length solvers detect bifurcation points and return `Bifurcation { load, modes }` instead of silently choosing a branch. Flux also provides rigid and flexible multibody dynamics, Cosserat rods for cables and hoses, the Network compiler and DAE solver, block-triangular sparse LU, full-wave electromagnetics, magnetodynamics with motion, and the general operations non-variational methods need (BVH build and traversal, neighbour lists, segmented reductions, counter-based random streams, fast multipole and hierarchical matrices, FFT solves). GPL tools (Meep, Elmer, OpenFOAM, LAMMPS and others) run only as External Ops or oracles.
- **Kiln.** Suspending scheduler with dynamic dependencies, Salsa-style durability and backdating, verifying traces in memory and constructive traces in the shared cache. A node's label is a separate memo output with its own change marker: verification re-joins labels from current inputs even when the value backdates, and a shared-cache hit returns only the value, with the label recomputed locally. Interactive early cutoff compares values directly; hashing happens off the interactive path. Progressive refinement is a set of independent nodes keyed by fidelity. GreedyDual-Size eviction. A Derivatives section specifies `trait Differentiable: OpImpl { tangent, adjoint }` in `base`, reverse traversal from a scalar goal, and checkpoints keyed by (`OpKey`, step) in a `Checkpoint` retention class that eviction drops first. Kiln is generic: Anvil, Flux and Ingot register node kinds through the operation contract in `base`. Two evaluation-wide limits are enforced as Aborts: a demand-depth limit on nested node demands (default 10,000) and an aggregate fuel governor per Evaluation taken from its budget.
- **`repo`.** Every edit becomes an immutable Change; ref updates go through a Jujutsu-style transaction log; branches are cheap. A merge is clean only when the result compiles and resolves; no check's verdict on the merge is worse than its verdict on each parent that defines it (`Pass` > `Undecided` > `Fail` > `Error`); no interference appears that neither parent has; there is no provenance-level geometric conflict (both sides modify, split or delete the same base entity, or one side's new entity intersects the other side's modified region); and no connectivity conflict (a merged net, harness connection or interface connection that unions nets distinct in the base and in each side). Symmetric-difference regions appear in review but do not block. Live collaboration uses a Loro block tree with Fugue text leaves; the unit of live replication is (package, label set), so blocks labelled above a document's label live in a separate document that only cleared participants receive. On reconnection the relay fast-forwards when no other participant changed the package meanwhile, whatever the duration; otherwise, when the disconnection exceeded 60 s or concurrent edits touched blocks the client also edited, offline work rejoins as a branch. `repo` keeps span-level integrity provenance: each source span records the integrity of the context that wrote it, and merges preserve it. Releases are signed tags; change orders are Proposals whose approvals are the Approvals of the release Act's plan; revision identity uses `GeometryId`s plus PMI. The BOM is a derived view over the assembly graph with EBOM, MBOM and service BOM views. Authorization uses Cedar policies; audit, transaction logs and release tags live in per-tenant transparency logs (C2SP tlog-tiles).
- **Hardware CI.** Every Change on a protected branch rebuilds the design and evaluates its checks; regression and golden-product sign-off simulations run at least nightly. Physical tests are Acts that run on hardware rigs when their inputs change; rigs declared `unattended_safe` by a named safety officer (closed fixtures with interlocks) may run after an Approval without on-site confirmation. Their results are Evidence records signed with TPM-held device keys under measured boot.

### 7.2 Cache keys and failures

An `OpKey` is the SHA-256 of:

1. the operation name and behavior version, or for a Wasm component the SHA-256 of its determinized binary, or for Ingot code the code hashes of the modules actually used plus the language behavior version;
2. the canonical encoding of the arguments, including any resolved plan;
3. the identities of the inputs: `GeometryId`s for the geometric stage of an entity-naming Op and for Flux solves (plus the canonical numbers of the entities their conditions reference); `ObjectId`s otherwise;
4. the platform class of the result, which is `CpuCanonical` for `Portable` and `Certified` results;
5. the effective fidelity, which each operation version maps from the requested fidelity (an operation that ignores fidelity maps all three to one value);
6. for External Ops, the host image digest.

The lockfile as a whole never enters a key. Entity-naming Ops cache in two stages: the geometric stage, keyed by input `GeometryId`s, numbers new entities canonically and refers to input entities by canonical number, so std features called from different designs share every geometric result; the relabeling stage, keyed by the geometric output's id, the `OpSite` and the inputs' name maps, assigns `EntityId`s. Every node whose value carries `EntityId`s (feature calls, entity-naming Ops, query resolutions) includes its `OpSite` in its key. Random streams are keyed by the class-independent part of the key.

**Failures and Aborts.** A deterministic `Failure` (a fillet radius too large, a query split, `OpVersionRetired`) is a value: catchable with `try`, cached, and wrapped as `DependencyFailed` for dependents. An Abort is environmental: `try` cannot observe it, it propagates to every transitive dependent, and no node that observed one writes a memo entry, a CAS object or an attestation. Oracle: inject environmental faults at random Ops in 10,000 runs; every value that reaches the memo or the shared cache equals the fault-free run's value. Every node terminates with a value or a typed `Failure`; every Evaluation terminates or aborts.

### 7.3 Determinism

- `PlatformClass` [PLT]: `CpuCanonical { epoch }` (every Tier 1 CPU target, browsers included, at any thread count and ISA level), `CpuIsa { isa, epoch }` (a native fast path for one ISA level, which may use FMA and native widths), `Gpu(GpuClass)` (one compiled pipeline on one verified device class: driver and shader-compiler build plus pipeline hash, where on Apple platforms the shader compiler is the OS build), `Unverified` (unlisted devices and external hosts). The operating system is never part of a CPU class. In prose: "the canonical class".
- `DeterminismGrade` [KLN], declared per operation version: `Portable` (bit-identical across the canonical class; the only grade for geometry and oracle reference results), `ClassExact` (bit-identical within one class), `Certified` (output independent of the class that computed intermediates, for example GPU filtering with CPU decisions). Kiln selects the class an Op runs in; there is no separate execution-mode concept.
- Results from `CpuIsa`, `Gpu` and `Unverified` classes never substitute for canonical results. A check, release or Proposal that requires canonical results recomputes them in the canonical class, with one exception: a check may rest on a pinned non-canonical Field (GPU solves, CPU certifies) when its residual and error bound are computed canonically from that Field. A release pins the `ObjectId`s of every External Op result and Evidence record it relies on. `CpuIsa` variants with FMA may serve `Preview` and `Interactive` fidelity when a kernel family loses more than 1.3× without FMA; sign-off recomputes canonically, and Kiln's cost model counts the recompute.
- Mechanisms [PLT]: `detmath`, the only elementary-function library in `Portable` code (correctly rounded, ported from CORE-MATH); a canonical lane order for horizontal operations (every reduction, scan or cross-lane operation in `Portable` code follows the 8-lane f64 or 16-lane f32 tree of `det_sum`; element-wise code may use any native width); binned reproducible summation (`exact_sum`) where partitioning varies; on CPU classes no implicit FMA contraction anywhere and explicit `mul_add` only inside `detmath` and error-free transformations; on GPUs, integer arithmetic for everything that must be exact (integer-limb reductions), non-finite detection on the CPU after readback by integer inspection, and a known-answer test for each compiled pipeline at creation and after any driver or OS update, with CPU fallback on failure; the canonical linear-algebra crate.
- The determinism suite runs on every merge on a representative set (Linux x86-64 with forced v2, v3 and v4; Linux ARM64; macOS ARM64; wasm32 in Node and in headless Chrome, threaded and single-threaded) and on every other Tier 1 target and browser engine at least nightly. A nightly divergence bisects automatically, opens a severity-1 determinism incident and blocks promotion to beta.

### 7.4 Wasm execution

- One determinizer, versioned, in `wasm-host` [PLT]. The registry runs it at publish time; the local toolchain runs it at build time for unpublished Wasm components; hosts execute only determinized binaries. It validates the binary, rejects nondeterministic features, and injects fuel metering (with a check that also reads a host cancellation word, or yields to the host every fixed number of fuel units where shared memory is absent), stack-depth limits and NaN canonicalization only where NaN bits become observable (float stores, `reinterpret`, the sign operand of `copysign`, host-call arguments and results, and v128 values from float operations that reach bitwise, integer-lane, shuffle, store or extract-to-integer instructions). Cancellation lands only at fuel-check points; epoch interruption is never used. When verifying modules emitted by the Ingot code generator, it checks for forbidden instructions or imports, a fuel decrement dominating every loop back-edge and function entry, a non-finite check before every observable float use, and a depth counter in every prologue.
- Executors. Native: Wasmtime pinned to its LTS releases, with Cranelift. Browsers: registry-built bundles in the browser's engine. iPadOS: Wasm runs inside WebKit (a WKWebView worker, or the web build in a thin WKWebView shell), where JavaScriptCore compiles it; Pulley, Wasmtime's interpreter, is the fallback; std and first-party Wasm components ship inside the app binary; registry packages appear only as dependencies of an opened design, never as a browsable catalog, and the app meets App Review guidelines 2.5.2, 3.1, 3.2.2(i), 4.2.3(ii) and 4.7; remote evaluation is the path if review rejects downloaded components. On targets where Wasmtime is below its Tier 2 (Windows ARM64), third-party evaluation components run out of process until upstream coverage improves.
- Ingot executors. Until the Ingot code generator ships, the Ingot reference interpreter (written in Rust, in the canonical class) is the only Ingot executor on every target. The code generator to Wasm enters when `ingot-bench` shows Ingot above 2% of a golden-product rebuild; from then on, generated modules pass the determinizer's verification and run on the executors above, and the interpreter remains for cold start, debugging, replay and differential testing.
- Evaluation worlds are synchronous and import no WASI; they may import `crucible:ops`. Tool and connector worlds use WASI 0.3. A determinized Wasm component whose host calls are all `Portable` is itself `Portable`.
- Constitutive models use the `crucible:material/constitutive` world. Models expressed in the kernel IR get tangents by algorithmic differentiation (with `local_solve` for local Newton solves); opaque Wasm models must supply consistent tangents, verified by a Taylor-test oracle, and a plasticity benchmark must show quadratic global Newton convergence.
- PLT publishes one determinizer overhead table that ECO cites (targets: scalar-float components ≤ 10%, SIMD-float components ≤ 25%, fuel and stack metering ≤ 10%, per component class).

### 7.5 Shared kernel IR

One kernel IR, in the crate `kernels`, is the source of every compute kernel that affects results: weak forms, constitutive functions, analytic Fields, implicit tapes, constraint residuals, Network residuals and device models from Verilog-A. Hand-written kernels use the IR's Rust embedding. The IR fixes the order of every floating-point operation and reduction on CPU back ends. IR v0 freezes at month 6 with only the constructs phases 0 and 1 need (element kernels with sum factorization, pointwise constitutive functions with forward-mode derivatives, implicit tapes); Network, constraint and Verilog-A constructs join in the phases that need them. Back ends: ahead-of-time Rust with canonical SIMD and Wasm SIMD128 in phase 0; WGSL through wgpu in phase 1 for interactive elasticity and implicit preview; server f64 GPU paths use wgpu on Vulkan with `SHADER_F64` first; a CUDA or HIP back end (CubeCL or another) is reconsidered at the phase 4 gate. WGSL kernels never claim bit-identity with CPU kernels. Every GPU path has a registered CPU path. Render shaders are WGSL and never affect results. FLX owns a kernels team of three compiler engineers from month 0.

### 7.6 `api`, agents and UI

- One API over MCP and native SDKs (Rust, Python, TypeScript, plus a C ABI). Every method is `<group>.<name>` in eight groups: Session, Read, Edit, Evaluate, Inspect, Compare, Propose, Act. Registry, event and archive methods belong to these groups (search, fetch and subscribe are Read; publish, yank, export, release and deviation grants are Act classes). There is no other group.
- Agents work only on branches, with scoped permissions, cost budgets and clearances. They must build, pass every check and attach snapshots before proposing. Every agent Proposal is attacked by an independent verifier that reasons over a typed view (IR, semantic diff, check results) with the author's free text elided. Risk class is computed by the server from the semantic diff; auto-merge only for the two lowest classes.
- **Context labels and write-down.** Every model context carries a label: the join of the labels of every value returned to it, typed or textual. For the hosted crew the context is the conversation; for external MCP hosts it is the OAuth token family (client instance plus user), shared by every session that family opens. Reading free text or images marks the context `instruction_tainted`; reading any untrusted value marks it `data_untrusted`. Every write (edit, Proposal, comment, review, exploration record, Act payload) carries at least the context's label. A write to a destination with a lower label fails with `label.write_down` unless a declassification record signed by two people, one of them an export officer, names it. Untrusted typed values are returned by handle, and edits cite the handle.
- **Free text is never endorsed by merging.** Free-text spans (comments, doc comments, string literals, description templates, and identifiers neither produced by the compiler nor typed by a human) are returned as `ExternalText` handles when their author is outside the reader's delegation chain or their integrity is untrusted. A human merge endorses structure and typed values, never free text; free text becomes trusted only through an explicit per-span endorsement that shows it verbatim with invisible and bidirectional characters highlighted.
- **Act approvals.** An approval request is a server record assigned to named approvers by Cedar policy and delivered only to their Crucible inbox; push notifications carry no content; anyone else who opens it sees "not assigned to you". The approval URL is never returned to a model; `act.approval_pending` carries only a request id. The server generates the one approval page (desktop, web and tablet use the same page): file names from item number, revision, format and release tag; a server-rendered thumbnail; a content summary (Items, labels, bytes); the recipient's verification and screening dates; a diff against the last approved plan of the same class to the same recipient; and the session's purpose, marked as agent text. Approval requires phishing-resistant WebAuthn user verification; the highest risk classes and every physical-effect Act are approvable on desktops and tablets only, never on phones. At most three pending requests per session; a denial blocks re-preparing a plan to the same recipients for 24 h and offers "report as suspicious", which freezes the session. Plans containing invisible characters, Unicode tag characters (U+E0000 to U+E007F), bidirectional controls or zero-width characters are rejected.
- **Physical safety.** Physical-effect Acts are transfer Acts (send an NC program, print job or robot program to a device) or the restricted `start_print`. Crucible never issues cycle start, resume, jog, `Start` or `StoreAndStart` to machine tools, robots, lasers, presses or furnaces; a person starts them at the device. `start_print` exists only for printers whose profile declares thermal-runaway protection and enclosure or smoke detection, and needs an Approval of the job digest plus an on-site confirmation that the build plate is clear, given at the printer or with a site-bound key. Agents may prepare transfer Acts; only assigned humans approve them. Manufacturing programs are approved over the posted program and its simulation evidence.
- The UI holds no product state; every product change is an `api` Edit or Propose call. One Rust UI toolkit and wgpu renderer, native and Wasm; GPU tiers G1 (native), G2 (WebGPU), G3 (WebGL2), with identical features and declared capacity per tier. Display data are `DisplayPackage`s; camera, culling and selection run locally. Direct manipulation writes Ingot through ranked edit plans. Fields paint on the true geometry with stated error. Proposal review shows feature, geometry, metric and source diffs. Design, Simulate, Manufacture, Electronics (schematic and layout) and Review are presets over one workspace. A public `crucible:ui/canvas2d` world lets any package submit retained 2D primitive buffers (lines, arcs, polygons, text, with layer and net ids) that the renderer draws and hit-tests; tools that compute per pointer move (the router, placement drag with live rule checks) run in the engine process on an interactive edit lane and stream geometry each frame through `api`.

### 7.7 Interop, ecosystem and support

- Open formats are built in Rust as Wasm components generated from their schemas (one EXPRESS code generator for every STEP application protocol and IFC). Licensed translators for proprietary formats run as external tools outside evaluation, and their output enters builds only as External inputs, so anyone can rebuild without the licence.
- Imports are Ingot expressions over Assets; there is no imported state outside the program. Crucible never replays proprietary feature history; it imports geometry, structure, semantic PMI and metadata, and offers design-intent reconstruction as a reviewed Proposal.
- Registry: namespaces owned by verified publishers; trusted publishing only; Sigstore signatures and SLSA provenance; std and translators reproducibly built; yank but never delete; output-changing releases flagged; a legal-removal path for patent and copyright notices with counter-notice and transparency-log entries.
- Licensing: code under Apache-2.0 WITH LLVM-exception; documentation CC-BY-4.0; examples and templates MIT-0; contributions under the DCO; company stewardship until a fixed trigger, then a foundation. Linked dependencies may use MIT, Apache-2.0, BSD, ISC, Zlib or Unicode-3.0. MPL-2.0 files may be linked; every distribution (native, Wasm, browser bundle, container) ships MPL notices and a source offer for each MPL file, and modifications are published under MPL-2.0. LGPL, GPL and AGPL code is never linked; it runs only as an external tool, an External Op or a test oracle, and distributed GPL or AGPL container images ship with their corresponding-source offer.
- Releases ride a 6-week train (nightly, beta, stable) with one LTS release per year supported for 24 months, aligned with Wasmtime's LTS window. Regulated extended support: one LTS line every two years is supported for 10 years, with security backports by the steward or retired engines run in sandboxed processes. A regulated cloud deployment mode serves defence and ITAR customers (US-only regions, US-person operations staff for ITAR tenants, controls mapped to NIST SP 800-171 with evidence of FedRAMP Moderate equivalence, support for DFARS 252.204-7012 incident reporting, image retention and forensic access). Medical customers receive a Computer Software Assurance package (intended use and risk tier per capability, vendor oracle evidence, release impact notes, a supplier quality agreement template and audit rights).

### 7.8 Trust and the shared cache

- Two worker pools. Untrusted-evaluation workers run Proposal CI from agent and external branches and every External Op, in single-use microVMs (Firecracker- or gVisor-class); they hold no attestation key and write only to a per-Proposal namespace. Trusted builders evaluate only merged revisions of protected branches.
- A separate attestation service holds the signing keys and signs (`OpKey`, `ObjectId`) only for jobs dispatched to trusted builders, bound to workload identity; the host, not the guest, computes output `ObjectId`s.
- Release gates and every `SignOff` check accept a cached result only when two independent trusted builders produced the same `ObjectId` (different hosts; for `Portable` operations, different ISAs); otherwise they recompute.
- Only the operator's registry builders write the global public cache domain, with 2-of-n agreement; the default client trust policy is "own organization plus operator public signers".
- Spot re-execution of shared-cache hits is weighted by downstream fan-out and is 100% for nodes that feed released checks.
- Encryption domains are keyed by tenant and canonical label set; deduplication never crosses them.

## 8. State-of-the-art mandate

- For every major component, identify the best published method as of October 2026 (a paper, a standard or a leading implementation), cite it, and state Crucible's choice. The default is to adopt or beat the state of the art. Any deviation needs a stated reason: license, robustness, determinism, portability or maturity.
- Name the leading implementation to beat, the benchmark or dataset to measure on, and a performance or accuracy target, labelled as a target.
- Prefer methods that are robust, deterministic, parallel and SIMD- or GPU-friendly, and methods with provable guarantees where they exist.
- Every tab includes a `## State of the art` section with a table: Component · Best published method · Leading implementation to beat · Crucible's choice · How we measure.

## 9. Platforms

- **Tier 1** (full product, identical features, every golden product passes): Windows 11 on x86-64 and ARM64; macOS on Apple silicon (current release and two prior); Linux on x86-64 and ARM64 (glibc 2.34 or newer, Wayland and X11); desktop browsers (Chrome and Edge, Safari, Firefox) through Wasm with WebGPU and a WebGL2 fallback.
- **Tier 1 preview.** A Tier 1 target may be a preview target for at most one phase: it runs the same build with identical features, passes the determinism suite and the golden-product checks headless, and ships through the beta channel; installers, updater, accessibility certification and GPU-driver qualification complete by the next gate. Phase 1 general availability: Windows 11 x86-64, macOS, Linux x86-64, Chrome and Edge. Tier 1 preview in phase 1, general availability at the phase 2 gate: Windows 11 ARM64, Linux ARM64 desktop (a Snapdragon X or ARM64 workstation joins the mid band and GPU lab), Safari, Firefox.
- **Tier 2** (viewing, review and light editing; CI on every release): iPadOS and Android tablets, ChromeOS through the browser; phones as viewers that never approve Acts.
- **Tier 3** (community-supported): FreeBSD and other Unix systems. A Tier 3 target joins the canonical class only after it passes the determinism suite.
- **Servers**: Linux containers on x86-64 and ARM64 for team servers and cloud workers; optional GPU acceleration.
- **Parity** means identical features and identical canonical results on every Tier 1 platform, whether computed locally or through remote evaluation on a team server or cloud worker. Capacity and speed may differ and are declared per platform and GPU tier. External Ops run on hosts that support them and are reached remotely from every client; air-gapped installs need a local Linux worker.
- Core crates are OS-agnostic; OS services sit behind `platform-api` traits implemented once in `apps/platform`. The engine runs as a separate process on desktop, a worker in the browser, threads on tablets, or a remote server, and the UI always talks to it through `api`. Native x86-64 builds target x86-64-v2 with runtime dispatch to v3 and v4; ARM64 targets ARMv8 with NEON; SVE dispatch waits until Rust stabilizes scalable vectors. Accessibility goes through each OS's native accessibility API (AccessKit), plus a DOM mirror on the web.
- **Browser memory.** WebAssembly memory never shrinks, so the engine worker keeps a fixed linear-memory cap (proposed 1.5 GiB); evaluations whose estimated peak exceeds 512 MiB run in a disposable heavy worker that writes results to the OPFS CAS and terminates; above the measured kill thresholds, heavy evaluations go remote. PLT owns one browser memory table.
- Every tab includes a `## Platform notes` section.

## 10. Coherence and taste

- **Fewest concepts.** Use the core types. Never invent a parallel abstraction.
- **One name per concept.** Follow section 2 exactly, including the "never call it" column.
- **Common things simple, advanced things possible.** Sensible defaults for the usual case; power revealed progressively.
- **Explicit over magic.** No silent fallbacks. Every approximation states its error.
- **Composition over special cases.** One general mechanism (Fields driving geometry, queries over provenance, checks everywhere, Approvals over digests, labels through every derivation) beats many one-off features.
- **Errors are guidance.** Every failure is typed, explains why, and suggests a fix.
- **One voice.** Present tense, precise, calm. No hype words ("revolutionary", "seamless", "cutting-edge", "world-class", "powerful", "robust" as praise), no exclamation marks.
- **Say it once.** Each fact lives in the tab that owns it; other tabs state the consequence in one line and point to the owner.
- **One skeleton.** Every tab follows section 11.
- **Code style.** Ingot: `snake_case` for functions and features, `PascalCase` for types, units on every dimensional literal. Rust: the Rust API Guidelines.

## 11. Research and writing rules

Research:

- Cite only pages you actually opened with WebFetch; search snippets are not sources. Prefer primary sources. Mark anything unverified with [unverified]. Never invent version numbers, dates, statistics or customer names. Web search quota may be exhausted; use WebFetch on known primary URLs.

Every tab follows this skeleton, in this order:

1. A lead of one to three sentences under the tab title, stating the design in one breath (no heading).
2. Design sections (`##`, with `###` subsections). Each design section ends with one capability table: Capability · Contract · Failure · Oracle id · Phase. There are no separate catalog sections.
3. `## State of the art`
4. `## Platform notes`
5. `## Interfaces with other subsystems`
6. `## Oracles` (each oracle once: id · verifies · pass criterion; no phase column)
7. `## Phasing` (gate contributions only, consistent with section 13)
8. `## Open questions`
9. `## Contract change requests` ("None" if none)
10. `## Sources`

Style:

- Tables for items compared on several attributes; numbered lists for sequences; code blocks for Ingot and Rust. Sentences under 25 words where possible; paragraphs of at most three sentences; specifics over adjectives; no emoji.
- Decisions inline: `**Decision D-<TAB>-<n>:** <decision>. *Why:* <rationale>. *Rejected:* <alternatives and why>.` Tab codes: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT. Decision numbers are stable: never renumber; a reversed decision keeps its number, states the new decision and ends with "(revised in round 2)"; new decisions take the next free number.
- At most two diagrams per tab, marked `[[DIAGRAM: …]]` in drafts.
- Length after revision: 12,000 to 18,000 words per tab excluding Sources (Ingot and Anvil up to 20,000). Cut repetition, restated rationale, content another tab owns and prose that a table already says. Never cut a capability, decision, oracle or source. Targets are labelled as targets.

## 12. Crate map

Dependencies point down this list; apps talk to the engine only through `api`.

| Layer | Crates (all under `core/` unless noted) | Owner |
| --- | --- | --- |
| Platform | `platform-api`, `detmath`, `simd`, `runtime`, `gpu`, `wasm-host`, `linalg` (canonical linear algebra) | PLT (`linalg` with FLX) |
| Contracts | `base` (shared value types from section 5 and the operation contract `OpImpl`, `OpCx`, `Differentiable`, `DeterminismGrade`); `cas` | KLN, with every owner of a type |
| Engine core | `kernels` (shared kernel IR and back ends); `field` (`Field`, domains, representations, `Sampler`); `kiln` | FLX, KLN |
| Geometry | `anvil-geom`, `anvil-topo`, `anvil-planar`, `anvil-mesh`, `anvil-implicit`, `anvil-ops` | ANV |
| Physics | `flux-forms`, `flux-solve`, `flux-couple`, `flux-opt` | FLX |
| Language | `ingot-syntax`, `ingot-types`, `ingot-ir`, `ingot-codegen`, `ingot-bindgen` with `ingot-macros`, `ingot-service` | ING |
| Product services | `repo` | KLN |
| Surface | `api` | AGT |
| Outside `core/` | `bridges/` (optional FFI: PETSc, hypre, GPU vendor specifics); `io/` (translators as Wasm components); `std/` (Ingot packages and first-party Wasm components); `wit/` (`crucible:` packages); `apps/` (`platform`, `ui-toolkit`, `renderer`, `desktop`, `web`, `mobile`, `server`, `cli`, `ci-runner`, `registry`, `attestation`, `headless-render`); `oracles/` (protected) | per tab |

`unsafe` is allowed only in `simd`, `gpu`, `wasm-host`, the code-loading parts of `kernels`, `bridges/` and `apps/platform`. Everything else is `forbid(unsafe_code)`. PLT renames its pool priority to `PoolLane` and its file durability to `WriteDurability`, so `PriorityClass` and Kiln's durability keep their meanings.

## 13. Roadmap, program plan and performance targets

### 13.1 Phases and golden products

| Phase | Theme | Gate |
| --- | --- | --- |
| 0 | Foundations | Determinism suite green on the representative set and nightly on every Tier 1 target; unit errors fail to compile; names cleared (Crucible) or replaced (Flux) before any operation version or WIT package freezes; freedom-to-operate reviews commissioned |
| 1 | Wedge: code-CAD and 3D printing | GP1 machined bracket: designed, toleranced, simulated and released in Crucible; made by a reference shop from Crucible's STEP AP242 with semantic PMI and drawing, using the shop's own CAM; measured by external metrology against Crucible's tolerances. GP2 topology-optimized lattice bracket: optimized and verified in Crucible; printed from Crucible's 3MF with the printer vendor's slicer; measured externally |
| 2 | Mechanical depth | GP3 gearbox, including machined parts cut from Crucible-generated programs; GP4 welded frame with sheet-metal guards, including measured weld distortion; one additive part printed through Crucible's slicer |
| 3 | Product breadth | GP5 molded enclosure with its PCB, including measured warpage and drop response; the board fabricated and assembled from Crucible outputs alone |
| 4 | Full multiphysics | GP6 drone, validated against flight, dynamometer and thermal test data |
| 5 | Scale | GP7 MEMS accelerometer; GP8 bolted steel platform round-tripped through IFC 4.3 with a structural check; GP9 crash box |
| 6 | Aerospace and electrification | GP10 composite wing box; GP11 CubeSat; GP12 EV battery sub-pack with BMS, harness and charger |
| 7 | Marine, buildings, medical and soft goods | GP13 workboat hull; GP14 timber pavilion (building product, IFC export); GP15 bone plate (ASME V&V 40 credibility); GP16 sewn pack (soft goods) |

Every physical gate states its replicate count (at least three articles, or a GUM uncertainty budget for a single article), measures as-built geometry and material coupons from the same lot, and keeps validation data out of calibration. Solid-mechanics validation follows ASME V&V 10; the validation metric follows V&V 20 (comparison error E = S − D, validation uncertainty u_val = √(u_num² + u_input² + u_D²), model-form bound |E| + k·u_val at validation points), and extrapolation inflation is a declared function of normalized distance to the nearest validation point. Golden products 7 to 16 are proposals, each a separately funded program started only with a physical test partner and an approved plan.

**Scope.** In: products made of parts, assemblies, boards, cables and software items, from MEMS to ships; building products and structures (prefabricated, steel, timber), exchanged with BIM tools through IFC 4.3; MEMS layout and chip-package design through GDSII and OASIS. Out: whole-building authoring (spaces, zones, whole-building energy); integrated-circuit logic layout; film and animation.

### 13.2 Program plan

Estimates are ±25% for phases 0 and 1 and ±50% beyond. Agent swarms count as at most a 1.5× productivity factor, applied only to oracle-covered, well-specified work (format codecs, function ports, widget sets, test corpora) and never to research items (SSI topology, blends, cut-cell quadrature, AMG quality, GPU driver defects). A scope addition above 5 engineer-years to an open phase needs the same approval as a gate change.

| Phase | Duration | People (start → end) | Engineer-years |
| --- | --- | --- | --- |
| 0 | 12 months | 20 → 59 | about 40 |
| 1 | 24 months (gate at month 36) | 59 → 100 | about 160 |
| 2 | 24 months | 100 → 140 | about 240 |
| 3 | 30 months | 140 → 200 | about 425 |
| 4 | 30 months | 200 → 250 | about 560 |
| 5 to 7 | about 3 years each | per program | 600 to 900 each |

Phase 4 lands near year 10 and phase 7 near years 17 to 19, about 3,500 to 4,000 engineer-years in total.

**Phase 1 scope.** Deferred to phase 2 or 1.x release trains, with contracts and oracles unchanged: the Ingot code generator, Perceus and the state-machine transform (the interpreter executes Ingot); cluster-DAG streaming, the visibility buffer, compute rasterization, k-buffer transparency, the variant grid, presence and follow mode (one forward renderer on every tier); cloud SaaS, live CRDT documents, encryption domains, transparency logs and the hardware runner (a single-node team server with branches, merge, Proposals, Cedar policies and a signed append-only audit log); CAM, posts, stock simulation, slicing and nesting (phase 1 keeps DfAM checks, 3MF production output and cost); the public registry and trusted publishing (a signed first-party package index); Bayesian exploration, the hosted crew, quarantined extraction and the TypeScript SDK (phase 1 ships `api` over MCP, Rust and Python SDKs, Propose with CI report, risk classes and three roles: detail designer, simulation engineer and verifier); guaranteed estimators on cut cells, GPU sign-off paths and CUDA back ends; SubD, certified SSI for general NURBS–NURBS pairs beyond what GP1 and the prismatic ABC corpus need, and free-form offsets; TUF delta updates (full signed packages suffice), Flatpak, AppImage, reproducible builds beyond Linux and wasm32, and telemetry (phase 1 ships MSIX, a notarized DMG, deb and rpm). Electronics has no team before the phase 1 gate beyond a two-person circuit-simulation research track.

**Staffing, end of phase 0 → end of phase 1.** Geometry kernel 10 → 14; features, sketches, drawings and GD&T 2 → 6; physics and kernel IR 7 → 10; materials and validity 1 → 3; language and language server 5 → 6; Kiln, CAS, `repo` and team server 5 → 8; platform layers, numerics, runtime and browser 8 → 12; build, release, CI, GPU lab and SRE 4 → 5; toolkit, editor, accessibility, renderer and interaction 8 → 16; product design and UX research 2 → 4; `api` and agents 3 → 5; interop 2 → 4; DfAM and cost 0 → 2; oracles, corpora and QA 2 → 5 (total 59 → 100). First hires (months 0 to 4): two computational geometers, a NURBS and topology lead, two correctly-rounded-math specialists, three compiler engineers for the kernel IR, a compiler engineer for Ingot, an incremental-computation lead, two FEM and multigrid engineers, two GPU renderer engineers, two toolkit and text engineers, two build and CI engineers, a Wasm runtime and browser engineer (also funding upstream Wasmtime coverage), a product designer, an oracle and corpus engineer and a product manager. Outside engineering: technical writing, security and compliance, a physical-test program manager from month 12, retained counsel for freedom-to-operate and trademark work, and signed phase 0 agreements with a reference machine shop, a metrology lab and a print bureau.

**Critical path for phase 1.** Chain A: exact predicates → certified SSI on GP1's surface set → Booleans → fillets and shells → GP1 features and drawing → STEP AP242 → shop machining → metrology. Chain B: kernel IR → CPU back ends → immersed elasticity with DWR → topology optimization and homogenization → implicit lattice → 3MF → print → measurement.

| Months | Milestones |
| --- | --- |
| 0–6 | `detmath` core functions; combinators; CAS and Kiln core; Ingot parser, types and interpreter; kernel IR v0 frozen at month 6; predicates, analytic geometry, topology and `EntityId`; CI on every Tier 1 CPU target |
| 6–12 | Analytic SSI and Booleans; tessellation and `DisplayPackage`; CPU kernel back ends; H¹ elements, CG and manufactured-solution tests; toolkit core and forward renderer; phase 0 gate at month 12, judged per crate on the corpus that exists |
| 12–24 | Fillets, chamfers, shells, holes, patterns, sketches; drawings and GD&T; immersed elasticity, DWR, p-multigrid; topology optimization, homogenization, implicit lattices; STEP AP242 and 3MF writers; team server; Propose and review |
| 20 | Physical dry run of both gates with interim outputs |
| 24–32 | Hardening, keyboard-complete workflows, accessibility, Tier 1 preview targets |
| 30–34 | GP1 and GP2 physical runs, with one re-run budgeted |
| 36 | Phase 1 gate |

### 13.3 Performance targets

Owned by PLT. The reference laptop is fixed: Intel Core Ultra 7 258V (8 cores, 8 threads, AVX2, Arc 140V GPU), 32 GB, Windows 11 and Ubuntu LTS, measured at 1920×1080 render resolution. Each row names its benchmark file in `oracles/plt/`, cache state, render resolution and percentile. Other operating systems' mid machines land within 1.5× of each row; only the reference laptop blocks beta promotion. All figures are targets.

| Row | Native | Browser |
| --- | --- | --- |
| Cold start / warm start | 1.5 s / 0.6 s | warm 2.5 s |
| Selection highlight | 16 ms | 33 ms with WebGPU (asynchronous readback), or a CPU ray cast |
| Orbit | 60 fps at 5M visible triangles at up to 2.1 MP render resolution (upsampled during motion; edges, overlays and text at native resolution; still frames accumulate at native resolution); X-ray views 30 fps | WebGPU 30 fps at 5M or 60 fps at 2M visible triangles; WebGL2 30 fps at 2M visible triangles and at most 1,000 distinct Parts |
| Scene capacity at 60 fps | G1 100,000 Instances (1,000,000 on the high band) | G2 20,000 Instances; G3 10,000 Instances of at most 1,000 distinct Parts |
| Drag preview | The dragged feature plus as many dependents as Kiln's cost estimate fits in 80 ms (at least the next 10 when cheap) within 100 ms; later dependents show as `Proxy` where the change is affine on them, otherwise `Stale` | same rule, 200 ms |
| Rebuild after an early edit | `SignOff`: 2 s on a named GP1-class benchmark of prismatic features. `Interactive`: p90 ≤ 10 s on an ABC-derived 200-feature corpus | 3× native |
| `SignOff` recertification after an early edit | p90 ≤ 30 s on the same 200-feature corpus | 3× native |
| Interactive simulation update | 1 s for linear static elasticity up to 100,000 DOFs at p = 2, warm-started, on G1 | 2 s with WebGPU; 6 s CPU-only; remote above that |
| Open a 1,000-part assembly from warm cache | 10 s, with a coarse view in 2 s | 20 s |
| Input to photon, p99 | 50 ms at 60 Hz; 33 ms at 120 Hz | same |
| Memory | under 1 GiB with GP1 open; idle 300 MiB with the GPU device created lazily | per PLT's browser memory table |
| Installed size | 400 MiB | |
| Flux CPU throughput (CEED bake-off) | BP3 and BP5 at p ≥ 3: at least 50% of MFEM or libCEED; memory-bound cases (BP1, BP2, p ≤ 2): at least 80% | |

## 14. Ruling log, round 1 (contract change requests from the first drafts)

| CCR | Ruling |
| --- | --- |
| ING-1 three-valued checks; FLX-3 | Accepted; `Undecided`. COV's `Indeterminate` becomes `Undecided`. Extended in round 2 (section 5 `CheckOutcome`). |
| ING-2 `Approx<T>` | Accepted; carries an `ErrorBudget` (section 5). |
| ING-3 `Tol<T>` semantics; MEC-3 | Accepted (section 5). |
| ING-4 syntax reference | Accepted and revised in round 2 (section 6). |
| ING-5 crate list | Accepted (section 12). |
| ING-6 language behavior version | Accepted (section 7.2). |
| ING-7 angle base dimension, torque | Modified in round 2: strong angular system (section 5). |
| ING-8 one `Severity` | Accepted. |
| ING-9 MEC `constraint` and `interface` keywords | Accepted: `Expr<T>` functions and `#[interface]` records. |
| ING-10 `OpSite` in keys; ANV-5 | Modified: two-stage caching with `GeometryId` (section 7.2). |
| ANV-1 `ErrorBound` location | Modified: in `base`. |
| ANV-2 `EntityId` formula | Accepted (section 5), with text-derived `OpSite`. |
| ANV-3 canonical operation names | Accepted: Anvil's catalog is canonical. |
| ANV-4 `Query` notes | Accepted and extended (section 5). |
| ANV-6 predicates for curved geometry | Accepted (section 7.1). |
| FLX-1 `ErrorBound` | Accepted and revised (section 5). |
| FLX-2 Field axes; COV-8; MEC-4; MFG-1; ELX-1 | Modified: product domains, `Field<(Body, Time), V>`. `Field<D, V, A>` becomes `Field<(D, A…), V>`; `TimeSpan`, `FreqSpan`, `Sweep`, `Interval<Q>` and `StateDomain` become quantity-type domains. |
| FLX-4 platform classes; PLT-1 | Modified: PLT's enum (section 7.3). |
| FLX-5 Kiln derivative support | Accepted; KLN adds a Derivatives section. |
| FLX-6 crate list | Modified: `field` and `kernels` below Anvil; `bridges/` outside core. |
| FLX-7 statistical agreement for chaotic problems | Accepted (principle 4), extended to bifurcations. |
| COV-1 `ErrorBudget` | Accepted (section 5). |
| COV-2 external tools; ELX-2; MFG-2; ECO-1 | Modified: External Op, External input and Evidence record (section 2). |
| COV-3 Flux operations for non-variational methods | Accepted (section 7.1). |
| COV-4 `Material` extension | Accepted. |
| COV-5 envelope zones and dispositions | Accepted. |
| COV-6 scope | Accepted (section 13.1). |
| COV-7 physical tests in GP4 and GP5 gates | Accepted (section 13.1). |
| KLN-1 cache key by package closure | Accepted (section 7.2). |
| KLN-2 hardware CI | Accepted (section 7.1). |
| KLN-3 "node" | Accepted (section 2). |
| KLN-4 `DeterminismGrade` | Accepted. |
| KLN-5 service BOM | Accepted. |
| MEC-1 `CoordSys`; MEC-2 `ShapeAspect`; MEC-5 role aliases | Accepted. |
| MFG-3 approval bound to content | Accepted as `Approval` over an approval subject. |
| MFG-4 `Money<C>` | Accepted. |
| ELX-3 remote parity; ELX-4 Software item; ELX-6 interop list | Accepted. |
| ELX-5 `Circuit` as a core type | Modified: `Network`, builder `network { … }`. |
| ELX-7 Wasm components may call operations | Accepted: WIT package `crucible:ops`. |
| AGT-1 to AGT-6 | Accepted (sections 2, 5, 7.6). |
| UIX-1 to UIX-4 | Accepted (sections 5, 9). |
| ECO-2, ECO-3, ECO-4, ECO-6, ECO-7 | Accepted. |
| ECO-5 name clearance | Accepted and strengthened in round 2: Flux is renamed in phase 0. |
| PLT-2 SVE; PLT-3 crates | Accepted. |
| PLT-4 instrumentation version in key | Subsumed by the determinized binary's hash. |

Round 1 conflicts resolved without a CCR: GPU code generation (one kernel IR; section 7.5); `detmath` is PLT's and the only math library; retired versions run from archived Wasm builds; one determinizer at publish and local build; `Preview`, `Interactive`, `SignOff` everywhere; no keywords for variants or requirements; `anvil::fold` for flex circuits; `anvil-planar` owned by Anvil; lockfile `ingot.lock`; std names (section 6); golden products 7 to 16 (section 13.1); no `ExecMode`; Flux owns multibody and rod models; MFG owns cost models, product LCA and passports; COV owns material environmental records; ECO owns the package registry.

## 15. Ruling log, round 2 (adversarial review)

All review findings go to the owning tabs as revision packets. The rulings below change the contract itself; every tab conforms.

| Finding | Ruling |
| --- | --- |
| R2-02, R3-01, R2-10, R3-05, R3-06 identity and names | Accepted: label invariance (7.1), `GeometryId` beside `ObjectId` (5), text-derived `OpSite` (5), two-stage keys and `OpSite` in keys of every node carrying `EntityId`s (7.2). |
| R2-12 positional iteration; R2-22 rank selectors; R2-32 merged anchors | Accepted (section 5 `OpSite` and `Query`). |
| R3-02, R5-01 labels | Accepted: label lattice (5), label as separate memo output (7.1), replication by (package, label set) (7.1), context labels and write-down (7.6). |
| R5-02 free-text endorsement | Accepted (7.6, 7.1 `repo` span provenance). |
| R5-03, R3-20 cache poisoning | Accepted (7.8). |
| R5-04 Act approvals | Accepted (7.6). |
| R4-01 remote machine starts | Accepted (2 Act, 7.6 Physical safety, 7.1 Hardware CI). |
| R4-03 net merges | Accepted: connectivity merge condition (7.1). |
| R4-04 electronics editors | Accepted: Electronics preset and `crucible:ui/canvas2d` (7.6). |
| R3-03, R3-04 failures and termination | Accepted (2 Abort, 7.1 Kiln, 7.2). |
| R1-01, R1-03, R1-08, R3-07, R3-08 error bounds and outcomes | Accepted (5 `ErrorBound`, `ErrorBudget`, `Approx`, `Truth`, `CheckOutcome`). |
| R1-04 surrogates | Accepted (7.1 Flux). |
| R1-02 thin walls and frames | Accepted (7.1 Flux). |
| R1-05, R3-09 canonical check | Accepted (section 6 example; 7.1 singular points). |
| R1-09, R1-44 WGSL semantics; R1-10 faer blocking; R1-11 defect correction; R6-17 FMA; R6-18 vector width | Accepted (7.3, 7.1, 12 `linalg`). |
| R1-13 bifurcations | Accepted (principle 4, 7.1). |
| R1-25 consistent tangents | Accepted (section 6 `local_solve`, 7.4). |
| R1-29 validation and replicates | Accepted (13.1). |
| R2-03 error propagation; R2-14 lattice faces; R2-23 planar snapping; R2-04 patent claims; R2-07 blend stages | Accepted (5 `Body`, 7.1 Anvil). |
| R3-11 key completeness | Accepted (7.2). |
| R3-15 merge rule | Accepted (7.1 `repo`). |
| R3-16 approval subjects; R3-17 evidence | Accepted (5 `ApprovalSubject`, 2 Evidence record). |
| R3-18 variants | Accepted: `#[configuration]` (section 6). |
| R3-19 derivatives in Kiln | Accepted (7.1 Kiln). |
| R3-21 cancellation | Accepted (7.4). |
| R3-22 method naming | Accepted (7.6). |
| R3-26 `crucible:ops` | Accepted (4). |
| R3-27 base types; R3-29 rotational units | Accepted (5, 12). |
| R3-36 capability tables | Accepted (11). |
| R3-46 offline rejoin | Accepted (7.1 `repo`). |
| R3-47, R6-25 Ingot executor; R6-13 iPadOS; R6-12 Wasmtime tiers | Accepted (7.4). |
| R3-51 determinizer verification; R6-20 NaN canonicalization cost | Accepted (7.4). |
| R5-19 trademarks; R5-31 patent ownership | Accepted (2, 7.1). |
| R5-20 regulated support; R5-32 licence wording | Accepted (7.7). |
| R6-01 to R6-05, R6-34 program plan | Accepted (13.2), with three phase 1 agent roles instead of two. |
| R6-06, R6-31 Tier 1 preview | Accepted (9). |
| R6-07 to R6-11 performance targets | Accepted (13.3). |
| R6-14 browser memory | Accepted (9). |
| R6-22 kernel IR scope | Accepted (7.5). |
| R6-28 determinism suite cadence | Accepted (7.3). |

## 16. Ruling log, round 2 revisions (change requests from revised tabs)

Each revised tab files its change requests under "Contract change requests". The rulings below change the contract; tabs that cite an accepted request update the citation in the consistency pass.

| Request | Ruling |
| --- | --- |
| CCR-ANV-7 fidelity of the rebuild rows | Accepted (13.3): the rebuild row states its fidelity per benchmark, and a `SignOff` recertification row is added. |
| CCR-ANV-8 `Unknown` bounds | Accepted (5 `Body`): unpropagated bounds become `NotQuantified`. |
| CCR-FLX-8 `regularization` error source | Accepted (5 `ErrorBudget`), as 7.1 already requires the regularization error of peak and pointwise goals in the budget. |
| CCR-FLX-9 one physics phase table | Open. Ruled before the remaining tabs are revised, so each cites one table. |
