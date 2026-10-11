# Crucible — Platform Spec

Crucible is one Rust platform where people and agents design, simulate, manufacture and release physical products from a single typed model. This tab summarizes the binding architecture contract (v5) and the twelve subsystem tabs on one page, and points to the tab that owns each fact. Crucible, Ingot, Anvil, Kiln and Flux are working names, and Flux is renamed in phase 0.

## What Crucible is

Four hard requirements from the founder shape every tab (contract section 1):

1. **Anything physical.** Every major physics domain and every scale, from MEMS to ships and building products. No software validly simulates everything, so every model states its validity envelope. The spec says plainly what is out of reach and defines how new physics and domains are added.
2. **State-of-the-art methods** in geometry, simulation and every other subsystem. Each tab names the best published method, the leading implementation to beat, Crucible's choice and how it is measured.
3. **Every major operating system, identical features.** Tier 1 platforms share features and canonical results; only capacity and speed differ.
4. **Coherence and taste.** One name per concept, the fewest concepts, typed errors that suggest a fix, and one calm voice.

"Fully specified" means every capability has a purpose, a contract (inputs, outputs, types), failure behavior, an oracle that verifies it, and a phase. The test is whether an engineering team, or agent swarms working against oracles, could start building from the spec alone.

The contract is binding: it holds the names, principles, core types, decided architecture, roadmap, program plan, performance targets and shared phases. The twelve subsystem tabs follow one skeleton, in which every design section ends with a capability table of contract, failure, oracle and phase. A tab that disagrees with the contract is wrong, and files a change request instead of working around it.

## Where the field stands

Each leading product wins one part of the problem. The State of the art section of each tab compares Crucible with them area by area.

- **Features in the user's language.** Onshape writes its standard features in FeatureScript, the language its users get, and `std::mech` follows that model (MEC).
- **Code as the model.** Zoo's KCL programs drive Zoo's hosted engine. KCL has no area or volume units, and FeatureScript raises unit errors when a program runs. CadQuery and build123d are Python libraries on OpenCascade, without units (ING).
- **Geometry kernels.** Parasolid, ACIS and CGM lead on B-rep Booleans with local tolerances. Parasolid's convergent modeling mixes facet and classic faces in one model. Open CASCADE 8.0 is the open reference; its fillet builder rejects contour ends where four or more edges meet. The Rust geometry kernel Fornjot was archived in June 2026 without reaching its goals (ANV).
- **Implicit geometry.** Fidget and nTop lead on implicit evaluation, and Anvil measures itself against the published Prospero results, Fidget and libfive (ANV).
- **Agents.** Fusion and Onshape expose MCP servers, and Zoo's Zookeeper works in code and reviews four views of its own work. NX Copilot answers with sources but does not act (AGT).

Crucible's answer is the principles below. The editable typed program is the model from the start, built-in features use only public mechanisms, and every result states its error and its evidence.

## Principles

The contract states seven principles that no tab may break (section 3).

1. **No privileged code.** Built-in features use only the public mechanisms anyone can use: Ingot for features, Wasm components for heavy algorithms, and versioned Anvil and Flux operations underneath. If a user or agent cannot build a feature, neither can the core team.
2. **One model, three editors.** The visual editor, the code editor and agents edit the same typed program. Nothing exists only in the GUI.
3. **Two universal types.** `Body` carries geometry and `Field` carries physics data. Models (weak forms, Networks) describe how Fields are computed; libraries consume and produce Bodies, Fields and plain values.
4. **Determinism is a feature.** The same inputs and versions give identical outputs per platform class, and other classes agree within declared tolerance or declared statistics. Problems with several solutions declare how a branch is selected. Evaluation never depends on clocks, randomness, thread order or names.
5. **The compiler checks physics.** Units, dimensions and tolerances are types, checked before anything runs. Every approximation carries its error, in a stated norm.
6. **Every claim has an oracle.** No capability ships without a machine-checkable test that agents cannot edit.
7. **Open core, interop first.** Kernel, language and standard library are open source. Open standards are first-class, and no design is ever trapped.

## Architecture

### Three tiers: operations, Wasm components, features

Every capability lives in one of three tiers (contract section 4, decision D-ARCH-1).

| Tier | Written in | What lives there | Rule |
| --- | --- | --- | --- |
| Operations | Native Rust, in Anvil and Flux | Geometry and physics primitives, a few hundred in all | Each version is frozen by content hash once released, and a design pins the versions it was built with |
| Wasm components | Rust or another language, compiled to Wasm | Heavy custom algorithms: nesting, CAM strategies, slicers, placers and routers, importers, specialist solvers | Sandboxed, determinized and portable to every OS and the browser; calls to operations go through the WIT package `crucible:ops` and are recorded as dependencies |
| Features | Ingot | Design intent, orchestration, entity selection and naming, checks and UI metadata | The default tier |

The tier rule (D-ECO-6) keeps code in Ingot unless it needs more than about 10⁶ primitive steps per call. An existing codebase in another language, or a data structure Ingot cannot express efficiently, also calls for a Wasm component. Features may be written in Rust as Wasm components through `#[ingot::feature]`, which generates the WIT world and a typed Ingot wrapper.

Code becomes an operation when at least three independent packages need it, it needs GPU or SIMD kernels, or it must be differentiable through Flux's form-level derivatives. Promotion happens in public, with oracles.

Retired operation versions stay executable from archived Wasm builds of their frozen source. Only versions that cannot compile to Wasm, the GPU `ClassExact` paths, fail with `OpVersionRetired`, whose fix is an upgrade Proposal.

### How a design flows

[[DIAGRAM diagrams/00-overview-architecture.jsx: Crucible architecture · clients, api, Kiln and the three tiers]]

People, agents and CI change a design only through `api`, whose methods fall into eight groups: Session, Read, Edit, Evaluate, Inspect, Compare, Propose and Act. Edits become immutable Changes to Ingot source in the design repository, and an Evaluation asks Kiln to compute nodes for a revision. Kiln runs features, Wasm components and operations as memoized nodes and stores every derived artifact in the CAS.

Anvil owns all mesh generation: Flux passes it sizing and metric Fields and solves on the Bodies and meshes it returns. Data made outside evaluation, such as a licensed translation or a supplier offer, enters only as a signed External input pinned in `ingot.lock`. Physical tests return as Evidence records signed by the rig's device key.

Hardware CI rebuilds every Change on a protected branch and evaluates its checks, and regression and golden-product simulations at `SignOff` run at least nightly. An Act, such as a release, an export or a transfer to a machine, leaves Crucible only after an assigned human approves its exact plan. Under everything, the platform layer runs one Rust core on every Tier 1 target (crate map: contract section 12).

### Core types

The contract fixes the types every subsystem shares (section 5). Rust names are canonical, and shared types live in the `base` crate unless another is named.

| Type | What it carries | Owner |
| --- | --- | --- |
| `Body` | Geometry as `BRep`, `Implicit`, `Mesh` or `SubD`; mixed operations return the least representation that holds both operands without approximating | ANV |
| `Field<D, V>` | Any quantity over a domain: stresses, loads, waveforms, sweeps, mode sets, ensembles and material curves; every result Field carries an `ErrorBudget` | FLX |
| `Network` | A lumped model of domain-typed ports, compiled into a DAE | ELX, FLX |
| `Material` | Property Fields over state domains, constitutive models, provenance, uncertainty and a `DataLicence` | COV |
| `Quantity<D>`, `Tol<T>`, `Approx<T>`, `Truth` | Dimensioned numbers, toleranced values with correlated worst-case arithmetic, values with error budgets, and three-valued comparisons | ING |
| `ErrorBound`, `ErrorBudget` | A bound with a norm and a kind (`Guaranteed`, `Estimated` or `Indicator`), and a budget with one part per error source | `base` |
| `CheckOutcome` | Verdict, fidelity, evidence, value, limit, margin, severity and source | ING, in `base` |
| `EntityId`, `Query` | Entity names hashed from text-derived call sites and roles; references resolved by provenance and role on every rebuild | ANV, ING |
| `Labels` | Level, export controls, scopes, integrity and licences, joined through every derivation | `base`, KLN, AGT |
| `ApprovalSubject` | What an Approval of a release or change order signs | KLN |

## The canonical example

The contract's bracket is the example every tab follows (section 6). ING owns refinements to the grammar and keeps this example valid.

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

Weak forms state physics in the same language:

```
let u = trial(Displacement, p)
let v = test(u)
let elasticity = inner(sigma(u, p.material), eps(v)) * dx(p)
              == dot(traction, v) * ds(web.face(role: end_cap))
let result = solve(elasticity, fixed: clamp)
result.von_mises  // Field<Part, Stress>
```

Ingot adds no keywords for domain concepts: constraints are ordinary functions, and interfaces are records marked `#[interface]`. Variants are parameters marked `#[configuration]`, and an Instance's existence depends only on them and constants, so Kiln computes the 150% BOM without enumeration. Builder blocks (`sketch { … }` and `network { … }`) are the only block sugar.

## Subsystems

Each subsystem tab owns one area of the design. The paragraphs below restate each tab's lead and link to it.

### Ingot language (ING)

[Ingot](01-ingot.md) is Crucible's design language: pure, strict and statically typed, with units, tolerances, approximation error and geometric references as types. A canonical-class interpreter runs it on every target, and each operation call becomes a Kiln node named from source text alone. The visual editor, the code editor and agents edit one lossless syntax tree, so every edit is a minimal, mergeable source change.

### Anvil geometry kernel (ANV)

[Anvil](02-anvil.md) is one geometry kernel over four representations (exact B-rep, implicit, mesh and subdivision surface) with one tolerance model, one provenance model and one operation contract. Linear decisions use exact predicates; decisions on curved geometry use certified enclosures, decided in rounds against frozen tolerances; constructions are floating point with per-entity tolerances and per-face error bounds. Every operation is versioned, deterministic and label-invariant, returns `HistoryRecord`s, and lets the GPU order, prune or preview work but never decide a result.

### Flux physics engine (FLX)

[Flux](03-flux.md) compiles weak forms written in Ingot through the shared kernel IR and solves them per region. All regions share matrix-free high-order FEM with p- and h-multigrid over deterministic AMG. Every result is a Field whose `ErrorBudget` states each bound's norm and guarantee, so a check decides only on bounds that hold for the quantity it reads.

Contract section 7.1 fixes the discretization per region:

| Region | Discretization |
| --- | --- |
| Members and struts | Timoshenko and Vlasov beams where a local slenderness criterion holds |
| Thin walls | Reissner–Mindlin shells on Anvil mid-surfaces where t/L_local ≤ 0.2 |
| Solids | An immersed adaptive octree: shifted boundary at `Interactive`, with at least four cells across any section and a surrogate-domain connectivity check; CutFEM at `SignOff`; finite cells for voxel data |
| Contact and boundary layers | Fitted meshes |
| Lattices | Beam-lattice models with node corrections and homogenization |

L_local is the smallest of the span between supports, the radius of curvature and the distance to the nearest load or feature. Reduced models couple to solids through rigid and Nitsche-based mixed-dimensional interfaces, and isogeometric shells are available too. A canonical linear-algebra crate gives `Portable` results, and unmodified faer serves only the `CpuIsa` class.

Peak and pointwise quantities are regularized goals with `Estimated` bounds: a p-norm or a local average over a stated region, never a raw maximum. A point quantity is `Undecided { SingularPoint }` near singular edges, such as where a clamped face meets a free face, unless the check excludes a stated distance. Surrogates may drive `Preview`, `Interactive` and exploration, but a `SignOff` check uses one only with a per-prediction bound or a confirming solve.

Flux also provides multibody dynamics, Cosserat rods, the Network compiler and DAE solver, and full-wave electromagnetics. GPL tools such as Meep, Elmer, OpenFOAM and LAMMPS run only as External Ops or oracles.

### Physics coverage and materials (COV)

[Crucible covers physics](04-coverage.md) through versioned physics packages whose models declare a model level, an evidence level and a `ValidityEnvelope` as data. Every result therefore carries a validity-zone Field and an `ErrorBudget` with a model-form part, and every gap is a named record. Materials are versioned records of property Fields over state domains, with statistical basis, typed uncertainty, provenance and a `DataLicence` that travels in the label lattice.

### Kiln, repository and PLM (KLN)

[Kiln](05-kiln-repo-plm.md) evaluates Ingot as a memoized graph keyed by content, call site and pinned operation versions, so an edit recomputes only what it affects, with identical bits within each platform class. The CAS stores every object under a SHA-256 identity, and `repo` records each edit as an immutable Change that merges only when source, checks, geometry and connectivity agree. Lifecycle, policy, signature and audit records share that signed store on a laptop, a team server, the cloud and an air-gapped site.

### Mechanical design (MEC)

[`std::mech`](06-mechanical.md) is the Ingot library for mechanical, industrial and structural design before manufacturing: sketches, part features, assemblies, surfaces, sheet metal, weldments, composites, molded parts, routing, tolerancing, drawings and design checks. Every feature is Ingot orchestrating versioned Anvil operations and a few Wasm components, and every result is a `Body`, `Part`, `Assembly` or `Field`. One constraint solver, one query vocabulary and one semantic tolerancing model serve them all.

### Manufacturing (MFG)

[`std::mfg`](07-manufacturing.md) turns a released design into made parts through one typed plan: Ingot intent, Wasm planning, Anvil geometry and Flux physics. Every toolpath, nest, mold, routing, cost and passport is a deterministic function of the design, checked by oracles. A person approves each program over its posted text and simulation evidence, and Crucible never starts a machine tool, robot, laser, press or furnace.

### Electronics and systems (ELX)

[Electrical intent](08-electronics-systems.md) in Crucible is a typed Ingot program: connectivity is a `Network` in code, a schematic is a stored drawing proved equal to it, and a board is a Part whose copper is integer layout data. Analyses return Fields with error budgets and checks with stated validity envelopes. One design repository holds schematic, board, enclosure, harness, firmware and requirements, so no exchange step can go stale.

### Agents (AGT)

[Agents](09-agents.md) use the same typed `api` as people: one catalog of API methods in eight groups, served over MCP 2026-07-28 and native Rust, Python and TypeScript SDKs. Agents edit only branches and deliver Proposals that build, pass every check, carry signed provenance and survive an independent verifier. The server, not the model, enforces safety: every model context carries a label, untrusted text never gains instruction authority, and every effect outside Crucible waits for an assigned human to approve its exact plan.

### UI and interaction (UIX)

[Crucible's interface](10-ui.md) is a GPU-rendered view of one typed Ingot program, and it changes the product only through `api`. One Rust toolkit and one wgpu renderer give every Tier 1 platform the same features on three declared GPU tiers, with a forward renderer in phase 1 and virtualized geometry from phase 2. Every result shows its status and error, review puts evidence before diffs, and agents work visibly on their own branches.

### Interop and ecosystem (ECO)

[Crucible reads and writes](11-interop-ecosystem.md) the open standards of every engineering domain through deterministic translators, and reaches proprietary formats only through licensed translators whose output is pinned. Everything anyone adds, the core team included, ships through one signed registry and behaves identically on every platform. Open formats, an open-source core and binding neutral stewardship keep every design and extension portable.

### Platform and performance (PLT)

[Crucible runs one Rust core](12-platform-performance.md) on every Tier 1 target behind one platform layer, so OS code lives in one crate. CPU results are bit-identical on every OS and browser through correctly rounded math, no implicit fused multiply-add and fixed reduction orders, while GPU paths are verified per compiled pipeline and keep a CPU path. PLT also owns the Wasm determinizer, packaging, reliability, CI and the performance targets of contract section 13.3, measured on one fixed reference laptop.

## Guarantees across every tab

### Fidelity, errors and checks

Every demanded result has a fidelity. `Preview` is fastest and approximate and never enters the shared cache, `Interactive` is approximate with an error estimate, and `SignOff` is converged or exact. A consumer holds each result as `Pending`, `Proxy`, `Ready(Fidelity)`, `Stale`, `Failed` or `Aborted`, and the UI shows that status on every value.

An error bound names its norm (`LInf`, `L2`, `Energy`, `Pointwise` or a goal functional) and its kind (`Guaranteed`, `Estimated` or `Indicator`). In an `ErrorBudget`, bounds in the same norm add, bounds in different norms never combine, and the total is as weak as its weakest part. Energy-norm bounds never certify a pointwise or extreme value.

Comparisons on approximate values return `Truth`: `True`, `False` or `Undecided`, decided only by disjoint enclosures. Below the Evaluation's fidelity ceiling, a branch on an `Undecided` value waits as `Pending` for a higher fidelity. At the ceiling it fails loudly with the margin and the accuracy needed.

A check's verdict is `Pass`, `Fail`, `Undecided`, `Error` or `Skipped`, and a `Pass` resting on unquantified budget components, typically model form, is conditional. It meets a release gate only under a repository policy that names a covering allowance with a citation, such as a design-code partial factor. Without that entry the verdict is `Undecided`.

Physics models declare a model level from L0 (analytic) to L3 (full 3D), an evidence level from E0 to E4 and a `ValidityEnvelope` (COV). The envelope evaluates to a zone Field (`Calibrated`, `Extrapolated`, `Invalid`, `Unassessed`) and to checks that flag or refuse. Only humans waive, and Crucible suggests a valid model but never switches models on its own.

### Determinism and caching

Results are bit-identical within a platform class (contract section 7.3), and the operating system is never part of a CPU class. The determinism suite runs on every merge on a representative set and nightly on every Tier 1 target. A nightly divergence bisects automatically and blocks promotion to beta.

| Platform class | What it covers |
| --- | --- |
| `CpuCanonical`, the canonical class | Every Tier 1 CPU target, browsers included, at any thread count and ISA level |
| `CpuIsa` | A native fast path for one ISA level, which may use fused multiply-add and native widths |
| `Gpu` | One compiled pipeline on one verified device class |
| `Unverified` | Unlisted devices and external hosts |

Each operation version declares a determinism grade: `Portable` (bit-identical across the canonical class, the only grade for geometry and oracle references), `ClassExact` or `Certified`. `detmath`, correctly rounded and ported from CORE-MATH, fixed reduction trees and no implicit fused multiply-add make `Portable` possible. Non-canonical results never substitute for canonical ones, but a check may rest on a pinned GPU Field whose residual and bound are computed canonically.

An `OpKey` hashes the operation and behavior version, the canonical arguments and resolved plan, and the input identities (section 7.2). It also hashes the platform class, the effective fidelity and, for External Ops, the host image digest, but never the lockfile as a whole. Entity-naming operations cache in two stages, so a geometric result is shared across designs and only the relabeling stage sees names.

A deterministic `Failure`, such as a fillet radius that is too large, is a value: catchable with `try`, cached and wrapped for dependents. An Abort, such as a cancellation, an exhausted budget or a lost device, is environmental: never caught, never cached.

### Trust, labels and Acts

Untrusted-evaluation workers run Proposal CI and every External Op in single-use microVMs that hold no attestation key (section 7.8). Trusted builders evaluate only merged revisions of protected branches. Release gates and `SignOff` checks accept a cached result only when two independent trusted builders produced the same `ObjectId`.

Every artifact, API response and model context carries `Labels`, and reading free text marks a model context `instruction_tainted` (section 7.6). Every write carries at least the context's label, and writing down needs a declassification record signed by two people, one an export officer. A human merge endorses structure and typed values, never free text.

An Act is two-phase: `act.prepare` produces a plan with a digest, and `act.commit` runs only after an assigned human approves that digest with phishing-resistant WebAuthn. No Act is approvable on a phone. Crucible never starts machine tools, robots, lasers, presses or furnaces: transfer Acts deliver programs, and a person starts the device.

### Platforms

Contract section 9 sets three tiers of support, plus servers.

| Tier | Targets | What it gets |
| --- | --- | --- |
| Tier 1 | Windows 11 on x86-64 and ARM64; macOS on Apple silicon (current release and two prior); Linux on x86-64 and ARM64; Chrome, Edge, Safari and Firefox through Wasm with WebGPU and a WebGL2 fallback | The full product, identical features, every golden product passing |
| Tier 2 | iPadOS and Android tablets; ChromeOS through the browser; phones | Viewing, review and light editing; phones are viewers that never approve Acts |
| Tier 3 | FreeBSD and other Unix systems | Community support; a target joins the canonical class only after it passes the determinism suite |
| Servers | Linux containers on x86-64 and ARM64 | Team servers and cloud workers, with optional GPU acceleration |

Phase 1 ships generally on Windows 11 x86-64, macOS, Linux x86-64, Chrome and Edge. Windows 11 ARM64, Linux ARM64 desktop, Safari and Firefox are Tier 1 preview targets in phase 1, generally available from the phase 2 gate. Parity means identical features and canonical results on every Tier 1 platform, local or remote; capacity and speed may differ and are declared.

### Openness, licensing and releases

Code is licensed Apache-2.0 WITH LLVM-exception, documentation CC-BY-4.0, and examples and templates MIT-0, with contributions under the DCO (section 7.7). LGPL, GPL and AGPL code is never linked; it runs only as an external tool, an External Op or a test oracle. A company stewards the project until a fixed trigger, then hands it to a foundation (ECO).

Open formats are Rust Wasm components generated from their schemas, one EXPRESS code generator serving every STEP application protocol and IFC. Licensed translators run outside evaluation, so their output enters builds only as External inputs and anyone can rebuild without the licence. Imports are Ingot expressions over Assets, and Crucible never replays proprietary feature history.

Releases ride a 6-week train, with one LTS release a year supported for 24 months. One LTS line every two years gets 10 years of regulated extended support. A regulated cloud mode serves defence and ITAR customers, and medical customers receive a Computer Software Assurance package.

## Roadmap

Phases close on gates (contract section 13.1). From phase 1, each gate is a set of golden products: reference products whose checks must pass and whose physical articles are made and measured.

[[DIAGRAM diagrams/00-overview-roadmap.jsx: Roadmap · eight phases, gated by golden products]]

The diagram reads top to bottom, one band per phase and one gate after it. Phases 0 to 4 carry durations and headcounts from the program plan; phases 5 to 7 are proposals.

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

Golden products 7 to 16 are proposals, each a separately funded program started only with a physical test partner and an approved plan.

Each physical gate states its replicates (at least three articles, or a GUM uncertainty budget for one article) and measures as-built geometry and same-lot material coupons. Validation data stays out of calibration, solid-mechanics validation follows ASME V&V 10, and the validation metric follows V&V 20. Extrapolation inflates the model-form bound by a declared function of normalized distance to the nearest validation point.

**Shared phases.** When several tabs phase one capability, contract section 13.4 gives it one phase and one owner, set by the first gate that needs it.

**Scope** (contract section 13.1):

- **In:** products made of parts, assemblies, boards, cables and software items, from MEMS to ships.
- **In:** building products and structures (prefabricated, steel, timber), exchanged with BIM tools through IFC 4.3.
- **In:** MEMS layout and chip-package design through GDSII and OASIS.
- **Out:** whole-building authoring (spaces, zones, whole-building energy), integrated-circuit logic layout, and film and animation.

## Program plan

Estimates are ±25% for phases 0 and 1 and ±50% beyond (contract section 13.2).

| Phase | Duration | People (start → end) | Engineer-years |
| --- | --- | --- | --- |
| 0 | 12 months | 20 → 59 | about 40 |
| 1 | 24 months (gate at month 36) | 59 → 100 | about 160 |
| 2 | 24 months | 100 → 140 | about 240 |
| 3 | 30 months | 140 → 200 | about 425 |
| 4 | 30 months | 200 → 250 | about 560 |
| 5 to 7 | about 3 years each | per program | 600 to 900 each |

Phase 4 lands near year 10 and phase 7 near years 17 to 19, about 3,500 to 4,000 engineer-years in total. Agent swarms count as at most a 1.5× productivity factor, applied only to oracle-covered, well-specified work: format codecs, function ports, widget sets and test corpora. They never count on research items: SSI topology, blends, cut-cell quadrature, AMG quality and GPU driver defects.

Adding more than 5 engineer-years of scope to an open phase needs the same approval as a gate change.

### Phase 1 scope

Phase 1 builds what GP1 and GP2 need. The rest is deferred to phase 2 or 1.x release trains, with contracts and oracles unchanged.

| Area | Deferred | Phase 1 ships instead |
| --- | --- | --- |
| Language | The Ingot code generator, Perceus and the state-machine transform | The interpreter executes Ingot |
| Rendering | Cluster-DAG streaming, visibility buffer, compute rasterization, k-buffer transparency, the variant grid, presence and follow mode | One forward renderer on every tier |
| Services | Cloud SaaS, live CRDT documents, encryption domains, transparency logs and the hardware runner | A single-node team server with branches, merge, Proposals, Cedar policies and a signed append-only audit log |
| Manufacturing | CAM, posts, stock simulation, slicing and nesting | DfAM checks, 3MF production output and cost |
| Ecosystem | The public registry and trusted publishing | A signed first-party package index |
| Agents | Bayesian exploration, the hosted crew, quarantined extraction and the TypeScript SDK | `api` over MCP, Rust and Python SDKs, Propose with a CI report, risk classes and three roles: detail designer, simulation engineer and verifier |
| Physics | Guaranteed estimators on cut cells, GPU paths for `SignOff` and CUDA back ends | Calibrated DWR on regularized goals; `SignOff` on CPU paths |
| Geometry | SubD, certified SSI for general NURBS–NURBS pairs, and free-form offsets | Certified SSI for what GP1 and the prismatic ABC corpus need |
| Distribution | TUF delta updates, Flatpak, AppImage, reproducible builds beyond Linux and wasm32, and telemetry | Full signed packages: MSIX, a notarized DMG, deb and rpm |

Electronics has no team before the phase 1 gate beyond a two-person circuit-simulation research track.

### Staffing and critical path

Staff grows from 59 to 100 between the ends of phases 0 and 1, across fourteen areas. The largest are toolkit, editor, accessibility, renderer and interaction (8 → 16) and the geometry kernel (10 → 14). First hires in months 0 to 4 include two computational geometers, a NURBS and topology lead, two correctly-rounded-math specialists and three kernel IR compiler engineers.

Outside engineering, the plan funds technical writing, security and compliance, and a physical-test program manager from month 12. It retains counsel for freedom-to-operate and trademark work and signs phase 0 agreements with a reference machine shop, a metrology lab and a print bureau.

Two chains set the phase 1 critical path:

1. **Chain A:** exact predicates → certified SSI on GP1's surface set → Booleans → fillets and shells → GP1 features and drawing → STEP AP242 → shop machining → metrology.
2. **Chain B:** kernel IR → CPU back ends → immersed elasticity with DWR → topology optimization and homogenization → implicit lattice → 3MF → print → measurement.

| Months | Milestones |
| --- | --- |
| 0–6 | `detmath` core functions; combinators; CAS and Kiln core; Ingot parser, types and interpreter; kernel IR v0 frozen at month 6; predicates, analytic geometry, topology and `EntityId`; CI on every Tier 1 CPU target |
| 6–12 | Analytic SSI and Booleans; tessellation and `DisplayPackage`; CPU kernel back ends; H¹ elements, CG and manufactured-solution tests; toolkit core and forward renderer; phase 0 gate at month 12, judged per crate on the corpus that exists |
| 12–24 | Fillets, chamfers, shells, holes, patterns, sketches; drawings and GD&T; immersed elasticity, DWR, p-multigrid; topology optimization, homogenization, implicit lattices; STEP AP242 and 3MF writers; team server; Propose and review |
| 20 | Physical dry run of both gates with interim outputs |
| 24–32 | Hardening, keyboard-complete workflows, accessibility, Tier 1 preview targets |
| 30–34 | GP1 and GP2 physical runs, with one re-run budgeted |
| 36 | Phase 1 gate |

### Performance targets

PLT owns the targets in contract section 13.3, each labelled as a target. They are measured on one reference laptop: an Intel Core Ultra 7 258V with 32 GB, on Windows 11 and Ubuntu LTS, at 1920×1080. Browsers have their own rows, and only the reference laptop blocks beta promotion.

| Row | Native target |
| --- | --- |
| Orbit | 60 fps at 5M visible triangles |
| Selection highlight | 16 ms |
| Rebuild after an early edit | 2 s at `SignOff` on a GP1-class benchmark of prismatic features |
| Interactive simulation update | 1 s for linear static elasticity up to 100,000 DOFs at p = 2 |

## Risks

Each risk has an owner tab that holds the detail.

| Risk | Why it is hard | How the plan contains it | Owner |
| --- | --- | --- | --- |
| Certified intersection and Booleans | SSI topology is open research, and the Rust kernel Fornjot was archived in June 2026 without reaching its goals | Phase 1 certifies only GP1's surface set and the prismatic ABC corpus; chain A starts at month 0; Open CASCADE serves as a differential oracle | ANV |
| Blends | Corners of valence four and above, Field-driven radii and G2 and G3 sections are research | A staged program with re-fillet targets of 95% at phase 1 and 97% at phase 2; an implicit fallback only on request, with stated deviation | ANV, MEC |
| Error bounds and solver quality | Guaranteed estimators on cut cells are research, and canonical AMG aggregation may cost iterations | Phase 1 uses calibrated DWR on regularized goals; guaranteed cut-cell estimators wait; phase 1 measures the AMG cost | FLX |
| Cross-platform determinism | Fused multiply-add, vector widths, browser engines and GPU drivers all change bits | `detmath`, fixed reduction trees, a known-answer test per GPU pipeline with CPU fallback, and the determinism suite on every merge | PLT |
| Program size | 3,500 to 4,000 engineer-years, with estimates ±50% past phase 1 | Gates on golden products, phase 1 deferrals, agent productivity capped at 1.5×, and gate-level approval for added scope | Contract section 13.2 |
| Physical validation | Gates need replicates, as-built measurement and held-out data, and GP7 to GP16 need test partners | Phase 0 agreements with a shop, a metrology lab and a print bureau; a physical dry run at month 20; one re-run budgeted for GP1 and GP2 | Contract section 13.1, COV |
| Agent safety | Models read untrusted text and can reach effects outside Crucible | Labels and write-down, free text never endorsed by merging, two-phase Acts with assigned Approvals, and no machine starts | AGT |
| Data, standards and tool licences | Standards tables, material databases, training data and translators carry their own terms | Legal review of standards tables before phase 1 and of material data before connectors ship; licences travel as `DataLicence` labels; GPL code runs only out of process | COV, MEC, ECO |
| iPadOS review | App Review may reject Wasm components downloaded as dependencies of a design | Wasm runs inside WebKit, std ships inside the app, and remote evaluation is the fallback | PLT, ECO |

## Patents, trademarks and freedom to operate

The phase 0 gate requires freedom-to-operate reviews commissioned and names cleared or replaced (contract section 13.1). The plan retains counsel for both (section 13.2).

| Item | What it covers | Crucible's position | Owner |
| --- | --- | --- | --- |
| US 12,229,885 B1 (inventor Alyn Rockwood; assignee an individual) | Intersection points formed from points of one surface within a threshold distance of the other; Zoo's engine overview describes a related method | Counsel reviews claims 1, 6, 11 and 16, the CPU and GPU paths and pending continuations; until the opinion arrives, SSI is a phase 1 release risk. The GPU only orders and prunes work, and every intersection point is a certified root of the exact equations (D-ANV-17) | ANV |
| US 9,164,503 (Boeing) | Claim 1 requires a pre-roughing slot and curves spiraling outward from it; expiry estimated for February 2034 | A clean-room spiral seeded by the medial axis (D-MFG-7). The review covers the family, its continuations, other vendors' engagement-control patents and every execution path, and adaptive clearing ships only after counsel's opinion | MFG |
| Placement and routing | An active patent area | A freedom-to-operate review precedes the placer and autorouter | ELX |
| The name Crucible | Full clearance in the US, EU, UK, China and Japan, in classes 9 and 42, assuming Atlassian's mark persists | A phase 0 gate | ECO |
| The name Flux | Collides with Siemens Simcenter Flux and with flux.ai, a PCB design tool | Renamed in phase 0, before any operation name or WIT package freezes | ECO |

Names enter `OpKey`s, lockfiles and WIT packages, so they clear before the first behavior version or `crucible:` package freezes. The registry has a legal-removal path for patent and copyright notices, with counter-notice and transparency-log entries.

## Open questions

1. **Flux's new name.** Contract section 2 renames Flux in phase 0 because it collides with Siemens Simcenter Flux and flux.ai; the new name is open. Until it is chosen, no `flux::` operation name or WIT package freezes, and this spec keeps "Flux".
2. **Freedom-to-operate opinions.** Counsel's opinions on US 12,229,885 B1 and on the adaptive-clearing families are outstanding, and other GPU geometry patents were not searched (ANV, MFG).
3. **Foundation.** A new foundation or an umbrella project, which decides trademark holding, registry operation and funding (ECO).
4. **Test partners.** GP7 to GP16 need physical test partners and data rights before any of them starts (COV).
5. **Calibration classes.** Whether the corpus supplies 300 held-out samples for every class the phase 1 checks need (FLX, with COV and MEC).
6. **Toolkit.** A month-3 bake-off chooses between Crucible's own toolkit and Masonry (UIX).
7. **Translator vendor.** CAD Exchanger, HOOPS Exchange or Datakit first; the deciding terms are not public (ECO).
8. **Hosted models and export control.** Whether a hosted model endpoint can meet the ITAR carve-out, which counsel decides before any controlled clearance (AGT).
9. **Licensed data.** Whether std may ship tabulated ISO, ASME, DIN and AISC values, and which material and reliability tables stay user-licensed (MEC, COV, ELX).
10. **iPadOS.** App Review's answer on downloaded Wasm components, and the WebKit executor shape, which a phase 3 spike chooses (PLT, ECO).

Each tab's Open questions section holds the rest.

## Sources

This tab cites only the contract and the subsystem tabs; the pages their research opened are listed in each tab's Sources section.

- Crucible architecture contract v5, `docs/contract.md`: mission (1), names (2), principles (3), layering (4), core types (5), the canonical example (6), decided architecture (7), platforms (9), crate map (12), roadmap, program plan, performance targets and shared phases (13), and the ruling logs (14 to 16).
- [Ingot language (ING)](01-ingot.md) · [Anvil geometry kernel (ANV)](02-anvil.md) · [Flux physics engine (FLX)](03-flux.md) · [Physics coverage and materials (COV)](04-coverage.md)
- [Kiln, repository and PLM (KLN)](05-kiln-repo-plm.md) · [Mechanical design (MEC)](06-mechanical.md) · [Manufacturing (MFG)](07-manufacturing.md) · [Electronics and systems (ELX)](08-electronics-systems.md)
- [Agents (AGT)](09-agents.md) · [UI and interaction (UIX)](10-ui.md) · [Interop and ecosystem (ECO)](11-interop-ecosystem.md) · [Platform and performance (PLT)](12-platform-performance.md)
