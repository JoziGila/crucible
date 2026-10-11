# Crucible — Platform Spec

Crucible is one Rust platform where people and agents design, simulate, manufacture and release physical products from a single typed model. This tab summarizes the binding architecture contract (v6.1) and the twelve subsystem tabs on one page, and points to the tab that owns each fact. Crucible, Ingot, Anvil, Kiln and Flux are working names, and Flux is renamed in phase 0.

## What Crucible is

Four hard requirements from the founder shape every tab (contract section 1):

1. **Anything physical.** Every major physics domain and every scale, from MEMS to ships and building products. No software validly simulates everything, so every model states its validity envelope, and the spec says plainly what is out of reach.
2. **State-of-the-art methods** in every subsystem. Each tab names the best published method, the leading implementation to beat, Crucible's choice and how it is measured.
3. **Every major operating system, identical features.** Tier 1 platforms share features and canonical results; only capacity and speed differ.
4. **Coherence and taste.** One name per concept, the fewest concepts, typed errors that suggest a fix, and one calm voice.

"Fully specified" means every capability has a purpose, a contract (inputs, outputs, types), failure behavior, an oracle that verifies it, and a phase. The test is whether agent swarms working against oracles, directed by one founder, can build each subsystem without further design work.

The contract is binding. The twelve subsystem tabs follow one skeleton, in which every design section ends with a capability table, and a tab that disagrees with the contract files a change request instead of working around it. The [Adversarial review](13-adversarial-review.md) records how the spec was attacked and what changed, and the [Decisions log](14-decisions-log.md) lists every decision in one line.

## Where the field stands

Each leading product wins one part of the problem; each tab's State of the art section has the detail.

- **Features in the user's language.** Onshape writes its standard features in FeatureScript, the language its users get, and `std::mech` follows that model ([MEC](06-mechanical.md)).
- **Code as the model.** Zoo's KCL programs drive Zoo's hosted engine, but KCL has no area or volume units, and FeatureScript checks dimensions only at run time. CadQuery and build123d are Python libraries on Open CASCADE, without units ([ING](01-ingot.md)).
- **Geometry kernels.** Parasolid, ACIS and CGM lead on B-rep Booleans with local tolerances. Open CASCADE 8.0 is the open reference, and its fillet builder rejects contour ends where four or more edges meet. The Rust kernel Fornjot was archived in June 2026 without reaching its goals ([ANV](02-anvil.md)).
- **Implicit geometry.** Fidget and nTop lead on implicit evaluation; Anvil measures itself against Prospero, Fidget and libfive ([ANV](02-anvil.md)).
- **Agents.** Fusion and Onshape expose MCP servers, and Zoo's Zookeeper works in code and reviews four views of its own work. NX Copilot answers with sources but does not act ([AGT](09-agents.md)).

Crucible's answer is the principles below: the typed program is the model, and every result states its error and its evidence.

## Principles

The contract states seven principles that no tab may break (section 3).

1. **No privileged code.** Built-in features use only the public mechanisms anyone can use: Ingot for features, Wasm components for heavy algorithms, and versioned Anvil and Flux operations underneath. If a user or agent cannot build a feature, neither can the core team. The one permitted difference is process isolation of third-party Wasm components, within PLT's call-overhead targets.
2. **One model, three editors.** The visual editor, the code editor and agents edit the same typed program. Nothing exists only in the GUI.
3. **Two universal types.** `Body` carries geometry and `Field` carries physics data. Models (weak forms, Networks) describe how Fields are computed.
4. **Determinism is a feature.** The same inputs and versions give identical outputs per platform class; other classes agree within declared tolerance, or in declared statistics for chaotic problems. Problems with several solutions declare how a branch is selected. Evaluation never depends on clocks, randomness, thread order or names.
5. **The compiler checks physics.** Units, dimensions and tolerances are types, checked before anything runs. Every approximation carries its error, in a stated norm.
6. **Every claim has an oracle.** No capability ships without a machine-checkable test that the agents building it cannot edit. Oracles that judge agent-built code also keep a held-out split outside the agent-readable tree, and a held-out failure fails the oracle.
7. **Open core, interop first.** Kernel, language and standard library are open source. Open standards are first-class, and no design is ever trapped.

## Architecture

### Three tiers: operations, Wasm components, features

Every capability lives in one of three tiers (contract section 4, decision D-ARCH-1).

| Tier | Written in | What lives there | Rule |
| --- | --- | --- | --- |
| Operations | Native Rust, in Anvil and Flux | Geometry and physics primitives, a few hundred in all | A released version freezes its source closure by hash, and a design pins the versions it was built with |
| Wasm components | Rust or another language, compiled to Wasm | Nesting, CAM strategies, slicers, placers and routers, importers, specialist solvers | Sandboxed and determinized; operations and engine data are reached only through the WIT package `crucible:ops`, each call a recorded Op dependency |
| Features | Ingot | Design intent, orchestration, entity selection and naming, checks and UI metadata | The default tier |

The tier rule (D-ECO-6) keeps code in Ingot unless it needs more than about 10⁶ primitive steps per call, an existing codebase in another language, or a data structure Ingot cannot express efficiently. Code becomes an operation when three independent packages need it, it needs GPU or SIMD kernels, or it must be differentiable through Flux's form-level derivatives.

A Wasm component never gets raw GPU, clock, file or network access, and reads engine data only through `crucible:ops` and handles derived from its inputs. Only first-party Wasm components run in the engine process. Every third-party Wasm component runs out of process on every target, and browsers evaluate third-party ones remotely until the asynchronous bridge passes PLT's executor oracle. Until the Ingot code generator ships, Ingot's reference interpreter, written in Rust, is its only executor on every target (contract 7.4).

### How a design flows

[[DIAGRAM diagrams/00-overview-architecture.jsx: Crucible architecture · clients, api, Kiln and the three tiers]]

Read top to bottom: every editor reaches the design only through `api`, Kiln runs features, Wasm components and operations as nodes, Wasm components reach Anvil and Flux only through `crucible:ops`, and only Acts leave Crucible.

People, agents and CI change a design only through `api`, whose methods fall into eight groups: Session, Read, Edit, Evaluate, Inspect, Compare, Propose and Act. Every edit becomes an immutable Change in the design repository, and an Evaluation asks Kiln to compute a set of nodes for a Change. Kiln runs features, Wasm components and operations as memoized nodes and stores every derived artifact in the CAS.

Anvil owns all mesh generation; Flux passes it sizing Fields and solves on the meshes it returns. Data made outside evaluation, such as a licensed translation or a supplier offer, enters only as a signed External input pinned in `ingot.lock`, and physical tests return as signed Evidence records. Hardware CI rebuilds every Change on a protected branch and evaluates its checks, and an Act, such as a release or a transfer to a machine, leaves Crucible only after an assigned human approves its exact plan.

### Core types

The contract fixes the types every subsystem shares (section 5); Rust names are canonical.

| Type | What it carries | Owner |
| --- | --- | --- |
| `Body` | Geometry as `BRep`, `Implicit`, `Mesh` or `SubD`; mixed operations return the least representation that holds both operands without approximating | ANV |
| `CallSite`, `EntityId`, `Query` | Call identity from source text alone; entity names hashed from call sites and roles; references resolved by provenance and role, never by position | ING, ANV |
| `Field<D, V>` | Any quantity over a domain, from stresses to waveforms, mode sets and material curves, with an `ErrorBudget` on every result | FLX |
| `Network` | A lumped model of domain-typed ports, compiled into a DAE | ELX, FLX |
| `Material`, `ValidityEnvelope` | Property Fields with constitutive models, provenance and a `DataLicence`; the conditions where a model is trusted | COV |
| `Quantity<D>`, `Tol<T>`, `Approx<T>`, `Truth` | Dimensioned numbers, toleranced values, values with error budgets, and three-valued comparisons | ING |
| `ErrorBound`, `ErrorBudget` | A bound with a norm and a kind (`Guaranteed`, `Estimated` or `Indicator`); a budget with one part per error source | `base` |
| `CheckId`, `CheckOutcome` | A check identity that survives edits to its limit; verdict, fidelity, evidence, value, limit, margin and severity | ING, in `base` |
| `Labels` | A confidentiality part and an integrity part, joined through every derivation | `base`, KLN, AGT |
| `ItemDefinition`, `ApprovalSubject` | The name-free definition of an Item revision, and what an Approval of a release or change order signs | KLN |

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
    let web = base.edge(role: end(outline.top)) |> rib(height: 20mm, t: thickness)
    let body = base + web
    let solid = body |> fillet(body.edges(new), 2mm)
    let p = part(solid, name: "Bracket").material(alu_6061_t6)
    let clamp = base.face(role: start_cap)
    let study = static_stress(p, fixed: clamp, force: load, on: web.face(role: end_cap))
    let stress = study.von_mises.max(over: p.away_from([clamp, web.face(role: end_cap)], 2 * thickness))
    p.require(stress < 0.6 * p.material.yield_strength(at: 20degC))
}
// width + load  →  error ING3001: cannot add Length and Force
```

The edge is selected by its role, `end(e)`: the edge the end cap gets from profile edge `outline.top`, never a rank. Every sweeping feature gives its faces, edges and vertices roles (ANV owns the vocabulary). The stress check reads a regularized maximum over a region that excludes the clamp and the loaded face by twice the wall thickness, because stress is singular where a clamped face meets a free face and may be singular at a loaded patch's edges (contract 7.1). The result is an `Approx<Stress>` with an `Estimated` bound, the check is three-valued, and an ING oracle shows that it decides at `SignOff`.

Weak forms:

```
let u = trial(Displacement, p)
let v = test(u)
let elasticity = inner(sigma(u, p.material), eps(v)) * dx(p)
              == dot(traction, v) * ds(web.face(role: end_cap))
let result = solve(elasticity, fixed: clamp)
result.von_mises  // Field<Part, Stress>
```

Ingot adds no keywords for domain concepts: constraints are ordinary functions, interfaces are records marked `#[interface]`, and variants are parameters marked `#[configuration]`. An Instance's existence depends only on configuration parameters and constants, so Kiln computes the 150% BOM without enumeration, while an Instance set's member count may depend on any value. Builder blocks (`sketch { … }` and `network { … }`) are the only block sugar.

## Subsystems

Each paragraph restates the owning tab's lead and links to it.

### Ingot language (ING)

[Ingot](01-ingot.md) is Crucible's design language: pure, strict and statically typed, with units, tolerances, approximation error and geometric references as types. A canonical-class interpreter runs it on every target, and each operation call becomes a Kiln node named from source text alone. The visual editor, the code editor and agents edit one lossless syntax tree, so every edit is a minimal, mergeable source change.

### Anvil geometry kernel (ANV)

[Anvil](02-anvil.md) is one kernel over four representations (exact B-rep, implicit, mesh and subdivision surface), with one tolerance model, one provenance model and one operation contract. Decisions use exact predicates on linear geometry and certified enclosures on curved geometry, in rounds against frozen tolerances, identically at every fidelity. Every operation is versioned, deterministic and label-invariant, returns history and error bounds, and never lets the GPU decide or prune.

### Flux physics engine (FLX)

[Flux](03-flux.md) compiles weak forms written in Ingot through the shared kernel IR and solves them per region with matrix-free multigrid. Solids use aggregated CutFEM on an immersed octree, slender walls and members use shells and beams, and contact uses fitted meshes. Every result is a Field whose `ErrorBudget` states each bound's norm, kind and confidence, so a check decides only on bounds that hold for its quantity.

Contract section 7.1 fixes the discretization per region:

| Region | Discretization |
| --- | --- |
| Members and struts | Timoshenko and Vlasov beams where a local slenderness criterion holds |
| Thin walls | Reissner–Mindlin shells on Anvil mid-surfaces where t/L_local ≤ 0.2 |
| Solids | An immersed adaptive octree: aggregated CutFEM at `Interactive` and `SignOff`, with at least four cells across any section; finite cells for voxel data; the shifted boundary method at most at `Preview` |
| Contact and turbulent boundary layers | Fitted meshes |
| Laminar thermal and frozen boundary layers | Octree wall refinement |
| Lattices | Beam-lattice models with node corrections and homogenization |

L_local is the smallest of the span between supports, the radius of curvature and the distance to the nearest concentrated condition or feature; loads that cover the wall do not shorten it. Peak and pointwise quantities are regularized goals with `Estimated` bounds, never a raw maximum. Near a flagged singular set, such as an edge where a clamped face meets a free face, a point quantity is `Undecided { SingularPoint }` unless the check's region excludes it by a stated distance.

A `SignOff` `Pass` resting on an `Estimated` discretization part is confirmed by one further refinement, or becomes `Undecided`. A `SignOff` check uses a surrogate only with a per-prediction bound or a confirming solve.

### Physics coverage and materials (COV)

[Crucible covers physics](04-coverage.md) through versioned physics packages whose models declare a model level, an evidence level and a `ValidityEnvelope` as data. Every result carries a validity-zone Field and an `ErrorBudget` whose model-form part comes from validation, and every gap is a named record. Materials are versioned records of property Fields over state domains, with statistical basis, typed uncertainty, provenance and a `DataLicence` that travels in the label lattice.

### Kiln, repository and PLM (KLN)

[Kiln](05-kiln-repo-plm.md) evaluates Ingot as a memoized graph keyed by content, call site and pinned operation versions, so an edit recomputes only what it affects. Each edit becomes an immutable Change in the CAS, a SHA-256 content-addressed store; a merge is clean only when source, checks, geometry and connectivity agree. Lifecycle, policy, signature and audit records live in the same signed store on a laptop, a team server, the cloud or an air-gapped site.

### Mechanical design (MEC)

[`std::mech`](06-mechanical.md) is the Ingot library for mechanical, industrial and structural design, from sketches to drawings and design checks. Every feature orchestrates versioned Anvil operations and a few Wasm components, and returns a `Body`, `Part`, `Assembly` or `Field`. One constraint solver, one query vocabulary and one semantic tolerancing model serve sheet metal, weldments, composites, molded parts, routing and the rest.

### Manufacturing (MFG)

[`std::mfg`](07-manufacturing.md) turns a released design into made parts through one typed plan: Ingot intent, Wasm planning, Anvil geometry and Flux physics. Every toolpath, nest, mold, routing, cost and passport is a deterministic function of the design, checked by oracles. A person approves each program, the machine gateway checks that Approval, and a person at the device starts it.

### Electronics and systems (ELX)

[Electrical intent](08-electronics-systems.md) in Crucible is a typed Ingot program: connectivity is a `Network` in code, and a schematic is a drawing proved equal to it. A board is a Part whose copper is integer layout data, and analyses return Fields with error budgets and checks with stated validity envelopes. Schematic, board, enclosure, harness, firmware and requirements share one design repository, so no exchange step can go stale.

### Agents (AGT)

[Agents](09-agents.md) use the same typed `api` as people: one catalog of methods in eight groups, served over MCP 2026-07-28, native SDKs and WIT. Agents edit only branches and deliver Proposals that build, meet every check's gate, carry signed provenance and survive an independent verifier. The server, not the model, enforces safety: labels on every context, no authority for untrusted text, and human approval of every outside effect's exact plan.

### UI and interaction (UIX)

[Crucible's interface](10-ui.md) is a GPU-rendered view of one typed Ingot program, and it changes the product only through `api`. One Rust toolkit and one wgpu renderer give every Tier 1 platform the same features on three declared GPU tiers. Every result shows its status and error, review puts evidence before diffs, and agents work visibly on their own branches.

### Interop and ecosystem (ECO)

[Crucible reads and writes](11-interop-ecosystem.md) the open standards of every engineering domain through deterministic translators. Proprietary formats arrive only through licensed translators whose output is pinned. Everything anyone adds, the core team included, ships through one signed registry under an open licence and binding stewardship.

### Platform and performance (PLT)

[Crucible runs one Rust core](12-platform-performance.md) on every Tier 1 target behind one platform layer, so OS code lives in one crate. Correctly rounded math, no implicit fused multiply-add and fixed reduction orders make CPU results bit-identical everywhere; each GPU pipeline is verified alone. PLT also owns the Wasm runtime, packaging, reliability, CI, the build program and the performance targets of contract 13.3.

## Guarantees across every tab

### Fidelity, errors and checks

Every demanded result has a fidelity. `Preview` is fastest and approximate and never enters the shared cache, `Interactive` is approximate with an error estimate, and `SignOff` is converged or exact. A consumer holds each result as `Pending`, `Proxy`, `Ready(Fidelity)`, `Stale`, `Failed` or `Aborted`, and the UI shows that status on every value.

An error bound names its norm and its kind: `Guaranteed` needs a proof in the quantity's norm, `Estimated` names its calibration class and exceedance level α, and `Indicator` is the weakest. Bounds in the same norm add, bounds in different norms never combine, and calibrated parts combine by a union bound, so a total carries confidence 1 − Σαᵢ. Model form comes only from validation (COV), and it applies to a check only when the validation plan covers that quantity's response-quantity class.

Comparisons on approximate values return `Truth`: `True`, `False` or `Undecided`, decided only by disjoint enclosures. Control flow on `Undecided` yields an `Undecided` value that is cached like any value and that `try` cannot catch. The Evaluation's fidelity ceiling changes only reporting: while a higher-fidelity node is demanded the consumer holds `Pending`, and at the ceiling the report states the margin and the accuracy needed.

A check is a `require` predicate identified by its `CheckId`, which derives from its call site and never from its predicate text, so editing a limit keeps the check's history and evidence. Its verdict is `Pass`, `Fail`, `Undecided`, `Error` or `Skipped`. A `Pass` resting on unquantified parts, typically model form, counts only under a policy allowance: a signed record with a citation, such as a design-code partial factor, changed only through a Proposal with two signers.

One gate predicate serves protected merges, Proposals and releases: a check meets a gate when its severity is below `Error`, its verdict is a non-provisional `Pass` in an accepted platform class, or a Waiver covers it. Only an authorized human signs a Waiver, with an expiry; agents never sign one, and protected checks and `Refuse` envelopes accept none. An Evaluation reads Evidence records up to its evidence watermark, so one Change at one watermark fixes every outcome.

Each physics model declares a model level, an evidence level and a `ValidityEnvelope` whose zone Field and checks flag or refuse results outside it (COV). Crucible suggests a valid model but never switches models on its own.

### Determinism and caching

Results are bit-identical within a platform class (contract section 7.3), and the operating system is never part of a CPU class. The determinism suite runs on every merge on a representative set and nightly on every other Tier 1 target and browser engine; a nightly divergence bisects automatically and blocks promotion to beta.

| Platform class | What it covers |
| --- | --- |
| `CpuCanonical`, the canonical class | Every Tier 1 CPU target, browsers included, at any thread count and ISA level |
| `CpuIsa` | A native fast path for one ISA level, which may use fused multiply-add and native widths |
| `Gpu` | One compiled pipeline on one verified device class |
| `Unverified` | Unlisted devices and external hosts |

Each operation version declares a determinism grade: `Portable` (bit-identical across the canonical class, the only grade for geometry and oracle references), `ClassExact` or `Certified`. Non-canonical results never substitute for canonical ones, but a check may rest on a pinned GPU Field whose residual and bound are computed canonically. Operations are label-invariant: renaming every input entity and call site changes no geometry, Field value or statistic.

An `OpKey` hashes the operation version, the canonical arguments, the input identities, the platform class, the effective fidelity and, for External Ops, the host image digest, but never the lockfile as a whole (section 7.2). Entity-naming Ops cache in two stages, so a geometric result is shared across designs and only the relabeling stage sees names. A deterministic `Failure` is a catchable, cached value; an Abort, such as a cancellation, an exhausted budget or a lost device, is environmental and is never caught or cached.

### Trust and the shared cache

Untrusted-evaluation workers run Proposal CI from agent and external branches, and every External Op, in single-use microVMs that hold no attestation key (section 7.8). Trusted builders evaluate only merged Changes of protected branches, and run third-party code only in single-use microVMs. Release gates and `SignOff` checks accept a cached result only when two independent trusted builders produced the same `ObjectId`.

An External Op result counts at a gate when two single-use runs on different hosts agree, each recorded in a signed execution receipt. Spawned tools and External Op hosts run with network egress denied unless an administrator grants a named endpoint. The phase 1 single-node team server serves both pools, offers no External Ops and records "single host" in every release's provenance.

### Labels and agents

`Labels` have two parts, joined through every derivation and carried by every model context (sections 5 and 7.6). The confidentiality part, a lattice of level, export controls, scopes and data licences, decides who may read a value; a control is satisfied only through a `ControlAuthorization` that an export officer creates with a second person. The integrity part, `instruction_tainted` and `data_untrusted`, never blocks anything; it sets risk classes and auto-merge eligibility.

Reading untrusted free text marks a model context `instruction_tainted`, and every write carries at least the context's label. Writing to a lower confidentiality label fails with `label/write_down` unless a declassification record signed by two people, one an export officer, names it. A human merge endorses structure and typed values, never free text, which needs a per-span endorsement.

Agents work only on branches, with scoped permissions, cost budgets and clearances, and propose only after building, meeting the gate on every check and attaching Snapshots. An independent verifier attacks every agent Proposal with the author's free text elided, and auto-merge applies only to the two lowest risk classes.

### Acts and physical safety

An Act is two-phase: `act.prepare` produces a plan with a digest, and `act.commit` runs only after an assigned human approves that digest. One plan may carry several effects under one Approval, and a human's export of an uncontrolled `public` or `internal` payload to a local folder is an audited local write, not an Act. Approvals need phishing-resistant WebAuthn with a device-bound credential, synced passkeys never approve, and phones offer no approval.

Crucible never issues a start, resume or jog to a device it transfers to; a person starts it at the device. The one exception is the restricted `start_print`, for material-extrusion printers under a safety officer's site policy, with a confirmation at the printer. Device programs pass through the machine gateway, whose core enforces each connector's allowlist, and `flash_device` leaves its board halted or held in reset.

A manufacturing program is approved over its posted text and simulation evidence and bound to a machine class, never to a serial. Test rigs run unattended only under an `unattended_safe` site policy that a named safety officer signs, and production equipment never receives one.

### Platforms

| Tier | Targets | What it gets |
| --- | --- | --- |
| Tier 1 | Windows 11 on x86-64 and ARM64; macOS on Apple silicon (current release and two prior); Linux on x86-64 and ARM64; Chrome, Edge, Safari and Firefox through Wasm with WebGPU and a WebGL2 fallback | The full product, identical features, every golden product passing |
| Tier 2 | iPadOS and Android tablets; ChromeOS through the browser; phones | Viewing, review and light editing; phones are viewers and offer no approval |
| Tier 3 | FreeBSD and other Unix systems | Community support; a target joins the canonical class only after it passes the determinism suite |
| Servers | Linux containers on x86-64 and ARM64 | Team servers and cloud workers, with optional GPU acceleration |

Phase 1 ships generally on Windows 11 x86-64, macOS, Linux x86-64, Chrome and Edge. Windows 11 ARM64, Linux ARM64 desktop, Safari and Firefox are Tier 1 preview targets in phase 1, generally available at the phase 2 gate.

Parity (contract section 9) means identical features and canonical results on every Tier 1 platform, local or remote; capacity and speed may differ and are declared.

### Openness, licensing and releases

Code is licensed Apache-2.0 WITH LLVM-exception, documentation CC-BY-4.0, and examples MIT-0, with contributions under the DCO (section 7.7). LGPL, GPL and AGPL code is never linked; it runs only as an external tool, an External Op or a test oracle. The founding company stewards the project until a fixed trigger, then transfers it to an existing foundation that holds a trademark option from phase 0 ([ECO](11-interop-ecosystem.md)).

One EXPRESS code generator builds the translators for every STEP application protocol and IFC. Licensed translators run outside evaluation, so anyone can rebuild without the licence, and Crucible never replays proprietary feature history. The registry admits verified publishers through trusted publishing, with Sigstore signatures and SLSA provenance.

Releases ride a 6-week train, with one LTS release a year supported for 24 months. Every stable release line gets security fixes for at least five years, and one LTS line every two years gets 10 years of regulated support. A regulated cloud mode serves defence and ITAR customers, and medical customers receive a Computer Software Assurance package.

## Roadmap

Phases close on gates, never on dates (contract section 13.1). From phase 1, each gate is a set of golden products: reference products whose checks must pass and whose physical articles are made and measured.

[[DIAGRAM diagrams/00-overview-roadmap.jsx: Roadmap · eight phases, gated by golden products]]

Read top to bottom: each band is a phase and what it adds, each diamond is the gate that closes it with its golden products, and the dashed phases 5 to 7 are proposals.

| Phase | Theme | Gate |
| --- | --- | --- |
| 0 | Foundations | Determinism suite green; unit errors fail to compile; Crucible cleared, Flux replaced and the SDK names reserved before any operation version or WIT package freezes; counsel's opinion on US 12,229,885 B1 delivered and chains A and B searched; GP2's alloy, machine, bureau and build-preparation software fixed; kernel IR v0 frozen |
| 1 | Wedge: code-CAD and 3D printing | GP1 machined bracket: designed, toleranced, simulated and released in Crucible; made by a reference shop from Crucible's STEP AP242 with semantic PMI and drawing; measured by external metrology; proof-loaded. GP2 topology-optimized lattice bracket in metal laser powder bed fusion: built from Crucible's 3MF with the bureau's build-preparation software; measured externally; proof-loaded |
| 2 | Mechanical depth | GP3 gearbox, including machined parts cut from Crucible-generated programs; GP4 welded frame with sheet-metal guards, including measured weld distortion; one material-extrusion part sliced by Crucible and sent through `send_print_job` to an open-firmware printer |
| 3 | Product breadth | GP5 molded enclosure with its PCB, including measured warpage and drop response; the board fabricated and assembled from Crucible outputs alone |
| 4 | Full multiphysics | GP6 drone, validated against flight, dynamometer and thermal test data |
| 5 | Scale | GP7 MEMS accelerometer; GP8 bolted steel platform round-tripped through IFC 4.3 with a structural check; GP9 crash box |
| 6 | Aerospace and electrification | GP10 composite wing box; GP11 CubeSat; GP12 EV battery sub-pack with BMS, harness and charger |
| 7 | Marine, buildings, medical and soft goods | GP13 workboat hull; GP14 timber pavilion (building product, IFC export); GP15 bone plate (ASME V&V 40 credibility); GP16 sewn pack (soft goods) |

Golden products 7 to 16 are proposals, each a separately funded program started only with a physical test partner and an approved plan. Each physical gate states its replicates, measures as-built geometry and same-lot coupons, keeps validation data out of calibration, and places sensors on the quantities its checks decide. GP1 and GP2 add a strain-gauged proof-load test on every article. The phase 1 gate release must reproduce the tagged run build's STEP and 3MF exports, or show equal geometry and definitional attributes; otherwise the physical run repeats.

**Shared phases.** A capability that several tabs phase, such as modal analysis, inherent strain or battery cell models, has one phase and one owner in contract section 13.4, set by the first gate that needs it; every other tab cites that row.

**Scope.** In: products made of parts, assemblies, boards, cables and software items, from MEMS to ships; building products and structures exchanged with BIM tools through IFC 4.3; MEMS layout and chip-package design through GDSII and OASIS. Out: whole-building authoring, integrated-circuit logic layout, film and animation, and classified information (contract section 13.1).

## Program plan

Crucible is built by agents (contract section 13.2). One human, the founder, directs the program; Claude orchestrates agent work against the oracles; and outside firms make, measure and advise where the physical or legal world requires a person. Phases end at their gates, never on a date, and no plan figure counts people or engineer-years.

| Role | What it does |
| --- | --- |
| Founder | Approves each phase's scope and budget at the previous gate, signs each golden product's pass/fail criteria before builders start on it, approves every Act and Waiver, and decides anything that changes money or scope |
| Orchestrator | Claude plans the work, opens work items, runs reviews and rulings, and keeps the contract and the tabs current |
| Oracle role | Writes and locks a phase's oracles before any builder works on the capabilities they verify |
| Builders | Build against locked oracles and never write or edit `oracles/` |
| Verifier role | Independent of both: checks every oracle against its capability row and an independent source, and attacks every builder Proposal |
| Outside firms | Counsel for freedom-to-operate and trademark work; a reference machine shop, a metrology lab, a metal powder bed fusion bureau and a proof-load test lab, under signed phase 0 agreements |

An adversarial review of the spec runs before each gate. Each phase carries one budget, approved by the founder at the previous gate: agent compute, cloud CI, rented GPU and device-farm time, physical runs with replicates and one re-run, metrology, proof loads and counsel.

### Build program

PLT owns how Crucible itself is built against its oracles ([PLT](12-platform-performance.md), D-PLT-45).

1. **Oracle first.** A work item opens only when its oracle ids exist in `oracles/` as executable checks written by the oracle role and passed by the verifier; each gate reports oracle coverage per crate.
2. **Runner classes.** Every oracle declares `cpu-ci`, `browser-ci`, `gpu-lab`, `device-farm`, `physical` or `founder`. Agents run every class except `physical` (outside firms) and `founder` (the founder's signatures), the GPU lab and device farm on rented hardware.
3. **Corpora.** Agent-built corpora enter `oracles/` only through a Proposal the verifier passes, and must agree with an independent source such as MPFR, Open CASCADE, lib3mf, MFEM or libCEED.
4. **Work items.** A work item names its crate, capability row, oracle ids, held-out split and budget. It runs through AGT's Proposal machinery, and until that machinery ships in phase 2, through the same `WorkItem` record over Git.

### Phase 1 scope

Phase 1 builds what GP1 and GP2 need. The rest is deferred to phase 2 or 1.x release trains, with contracts and oracles unchanged.

| Area | Deferred | Phase 1 ships instead |
| --- | --- | --- |
| Language | The Ingot code generator | The interpreter executes Ingot |
| Rendering | Cluster-DAG streaming, visibility buffer, compute rasterization, the variant grid, presence | One forward renderer on every tier |
| Services | Cloud SaaS, live CRDT documents, encryption domains, transparency logs, the hardware runner | A single-node team server with branches, merge, Proposals, Cedar policies and a signed audit log |
| Manufacturing | CAM, posts, stock simulation, slicing and nesting | DfAM checks, 3MF production output and cost |
| Ecosystem | The public registry and trusted publishing | A signed first-party package index |
| Agents | Bayesian exploration, the hosted crew, the TypeScript SDK | `api` over MCP, Rust and Python SDKs, Propose with a CI report, and three roles: detail designer, simulation engineer and verifier |
| Physics | Cut-cell guaranteed estimators, GPU `SignOff`, CUDA, inherent strain, the shifted boundary method | Aggregated CutFEM with calibrated DWR on CPU paths |
| Geometry | SubD, general NURBS–NURBS SSI, GPU sampling for SSI, free-form offsets | Certified SSI without sampling for GP1 and the prismatic ABC subset |
| Wasm and recipients | The browser sandbox for third-party Wasm components; screening of recipients inside the organization | Remote evaluation of those Wasm components; screening of other organizations |

Electronics before the phase 1 gate is a circuit-simulation research track. A desktop install without a team server designs, simulates, evaluates and exports locally; Proposals, releases and every Act need a team server.

### Critical path and milestones

Four chains set the phase 1 critical path, each run in order:

1. **Chain A, geometry:** exact predicates, certified SSI on GP1's surface set, Booleans, fillets and shells, GP1 features and drawing, STEP AP242, shop machining, metrology and proof load.
2. **Chain B, physics:** kernel IR, CPU back ends, immersed elasticity with DWR, topology optimization, implicit lattice, strut calibration coupons, 3MF, build, measurement and proof load.
3. **Chain C, interface:** toolkit, forward renderer and picking, feature dialogs and drag preview, drawing editor and review diffs, keyboard-complete workflows with accessibility oracles green.
4. **Chain D, release:** single-node team server with Cedar and the audit log, microVM Proposal CI, the approval page with WebAuthn and the release Acts, used end to end in the physical dry run.

The milestones are ordered, not dated: foundations and the phase 0 gate; phase 1 features, physics and the release path; a physical dry run of both gates; hardening and Tier 1 preview targets; a tagged run build whose exports make the GP1 and GP2 articles; the physical runs with one re-run budgeted; and the phase 1 gate.

### Performance targets

PLT owns the targets in contract section 13.3, and every figure is a target. They are measured on one reference laptop with an Intel Core Ultra 7 258V and 32 GB, on Windows 11 and Ubuntu LTS, at 1920×1080; PLT names the exact model and its measurement conditions at the phase 0 gate. A row blocks beta promotion from the phase in its last column.

| Row | Native | Browser | Phase |
| --- | --- | --- | --- |
| Selection highlight | 16 ms | 33 ms with WebGPU | 1 |
| Orbit | 60 fps at 5M visible triangles | WebGPU 30 fps at 5M visible triangles | 1 |
| Rebuild after an early edit | `SignOff`: 2 s on a GP1-class benchmark | 3× native | 1 |
| Interactive simulation update | 1 s for linear elasticity up to 100,000 DOFs at p = 2 | 2 s with WebGPU | 1 |
| Open a 1,000-part assembly from warm cache | 10 s | 20 s | 2 |

## Risks

| Risk | Why it is hard | How the plan contains it | Owner |
| --- | --- | --- | --- |
| Certified intersection and Booleans | SSI topology is open research, and the Rust kernel Fornjot was archived without reaching its goals | Phase 1 certifies only GP1's surface set and the prismatic ABC subset; chain A heads the critical path; Open CASCADE is a differential oracle | ANV |
| Blends | Corners of valence four and above, Field-driven radii and G2 and G3 sections are research | A staged program with re-fillet targets of 95% of stage-1 cases at phase 1 and 97% of all cases at phase 2 | ANV, MEC |
| Error bounds | Guaranteed estimators on cut cells are research, and a calibrated bound can undershoot | Calibration classes with envelopes and held-out samples, refinement confirmation at `SignOff`, cut-cell totals kept `Estimated` | FLX |
| Cross-platform determinism | Fused multiply-add, vector widths, browser engines and GPU drivers all change bits | `detmath`, fixed reduction trees, a known-answer test per GPU pipeline, and the determinism suite on every merge | PLT |
| Agent-built code | Builders see every visible input and can special-case it, and an oracle can be wrong | Oracles locked before builders start, held-out splits, an independent verifier, corpora checked against independent sources | Contract section 13.2, PLT |
| Physical validation | Gates need replicates, as-built measurement and proof loads, and GP7 to GP16 need test partners | Signed phase 0 agreements with a shop, a metrology lab, a bureau and a proof-load lab; a physical dry run; one re-run budgeted | Contract section 13, COV |
| Freedom to operate | SSI, adaptive clearing, placement and routing sit near active patent families | Opinions and searches before the work they cover, starting at the phase 0 gate | ANV, MFG, ELX |
| Agent and physical safety | Models read untrusted text, and transfers reach machines that cut, move or heat | Labels and write-down, two-phase Acts with assigned Approvals, no device starts, allowlists in the gateway's core | AGT, MFG |
| Data and tool licences | Standards tables, material databases and translators carry their own terms | Counsel's reviews before std's tables and each material connector ship; licences travel as `DataLicence` labels | MEC, COV, ECO |

## Patents, trademarks and freedom to operate

Counsel's opinion on US 12,229,885 B1, a freedom-to-operate search of chains A and B, and cleared names are phase 0 gate items (contract section 13.1).

| Item | What it covers | Crucible's position | Owner |
| --- | --- | --- | --- |
| US 12,229,885 B1 (inventor Alyn Rockwood) | Intersection points formed from points of one surface within a threshold distance of the other | Counsel's opinion covers claims 1, 6, 11 and 16 and pending continuations. Every intersection point is a certified root of the exact equations; phase 1 SSI has no sampling stage, and GPU sampling joins in phase 2 only after a favourable opinion (D-ANV-17) | ANV |
| US 9,164,503 (Boeing) | A pre-roughing slot with curves spiraling out of it | A clean-room spiral seeded by the medial axis (D-MFG-7); adaptive clearing ships only after counsel's opinion | MFG |
| Placement and routing | An active patent area | Placer and autorouter work opens only after counsel's search of their code paths (D-ELX-31) | ELX |
| The name Crucible | Clearance in classes 9 and 42 in the US, EU, UK, China and Japan, assuming Atlassian's mark persists | A phase 0 gate | ECO |
| The name Flux | Collides with Siemens Simcenter Flux and with flux.ai | Renamed in phase 0, before any operation name or WIT package freezes | ECO |

## Open questions

Each tab's Open questions section holds the detail.

1. **Flux's new name.** Until it is chosen, no `flux::` operation name or WIT package freezes, and this spec keeps "Flux" (contract section 2).
2. **Freedom-to-operate opinions.** Counsel's opinions on US 12,229,885 B1 and on the adaptive-clearing families are outstanding ([ANV](02-anvil.md), [MFG](07-manufacturing.md)).
3. **GP2's details.** The phase 0 gate fixes the bureau's build-preparation software and 3MF extensions, and sheet cells would bring sheet-lattice shells into phase 1 ([MFG](07-manufacturing.md), [COV](04-coverage.md)).
4. **Strut waviness threshold.** It comes from the first as-built calibration build ([COV](04-coverage.md)).
5. **Guaranteed bounds on cut cells.** Research deferred past phase 1 ([FLX](03-flux.md)).
6. **Mesh Boolean method.** Chosen by the phase 0 bake-off (D-ANV-20).
7. **Licensed standards data.** Which terms let std package tabulated values, and the licensed editions that gear and bearing envelopes need ([MEC](06-mechanical.md), [COV](04-coverage.md)).
8. **Translator vendor.** CAD Exchanger, HOOPS Exchange or Datakit, signed by the founder before the phase 2 gate ([ECO](11-interop-ecosystem.md)).
9. **Verilog-A front end.** Whether a clean-room front end fits phase 3 ([ELX](08-electronics-systems.md)).
10. **GPU back ends.** CUDA or HIP is reconsidered at the phase 4 gate (contract section 7.5).
11. **Auto-merge thresholds.** Defaults until phase 2 review data can set them ([AGT](09-agents.md)).

## Sources

This tab cites only the contract and the subsystem tabs; the pages their research opened are listed in each tab's Sources section.

- Crucible architecture contract v6.1, `docs/contract.md`: mission (1), names (2), principles (3), layering (4), core types (5), the canonical example (6), decided architecture (7), platforms (9), crate map (12), roadmap, program plan, performance targets and shared phases (13), and the ruling logs (14 to 17).
- [Ingot language (ING)](01-ingot.md) · [Anvil geometry kernel (ANV)](02-anvil.md) · [Flux physics engine (FLX)](03-flux.md) · [Physics coverage and materials (COV)](04-coverage.md)
- [Kiln, repository and PLM (KLN)](05-kiln-repo-plm.md) · [Mechanical design (MEC)](06-mechanical.md) · [Manufacturing (MFG)](07-manufacturing.md) · [Electronics and systems (ELX)](08-electronics-systems.md)
- [Agents (AGT)](09-agents.md) · [UI and interaction (UIX)](10-ui.md) · [Interop and ecosystem (ECO)](11-interop-ecosystem.md) · [Platform and performance (PLT)](12-platform-performance.md)
- [Adversarial review](13-adversarial-review.md) · [Decisions log](14-decisions-log.md)
