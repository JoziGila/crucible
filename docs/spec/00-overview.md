# Crucible — Platform Spec

Crucible is one Rust platform in which agents write physical products as typed programs and people steer, review, approve and present them, from the first sketch through simulation, manufacture and release. An engineer who leaves NX, SOLIDWORKS, Ansys or Teamcenter, or an AI-built clone of them, gains a product whose every number says how far to trust it and whose every change arrives built, checked and open to review before anything reaches a machine or a customer. One mechanism delivers this: the design is a single program in Crucible's typed language, Ingot, evaluated deterministically and incrementally, so geometry, physics, manufacturing plans and product records are all computed from one source and pinned by one set of content hashes.

## What Crucible is

This section says what using Crucible looks like, what the founder requires of it, and how this specification is organized.

### A session

An engineer opens a bracket in a browser tab. An agent has proposed widening it from 60 mm to 80 mm, and the review opens on evidence: the stress check still passes at full accuracy, its margin and error bar are shown, and the mass went up by about 20 g. The engineer circles the fillet, asks what happens at a 5 mm wall, and gets a second study back on the agent's branch. She approves the merge with a security key and sends the machine shop a read-only link whose figures follow the model as it changes.

Nobody modelled the bracket by hand. The agent edited a short Ingot program; the engine rebuilt only what the edit touched; the simulation reported which errors it counted and which it did not; and the merge refused nothing because nothing got worse. The rest of this page explains each of those steps and links to the tab that specifies it.

### The mission and five requirements

Crucible's mission is to be the one platform in which agents author physical products and people steer, review, approve and present them, specified completely enough that agents working against machine-checked tests, directed by one founder, can build it without further design work ([contract section 1](../contract.md#1-mission)). "Fully specified" means every capability has a purpose, a contract (inputs, outputs, types), failure behaviour, an oracle that verifies it, and a phase. An oracle is a machine-checkable test that the agents building the capability cannot edit.

The founder sets five hard requirements:

1. **Anything physical.** Every major physics domain and every scale, from MEMS (micro-electromechanical systems) to ships and building products, with every model stating where it is valid and the spec saying plainly what is out of reach.
2. **State-of-the-art methods** in every component, each compared with the best published method and the leading implementation to beat.
3. **Every major operating system, identical features,** with only capacity and speed allowed to differ.
4. **Coherence and taste,** in the design and in text an engineer reads with pleasure.
5. **Better than the incumbents and their clones:** nothing an incumbent's user relies on is missing by the phase the parity floor names, and the reasons to switch are ones a clone cannot copy in weeks.

### How the spec is organized

The [architecture contract](../contract.md) is binding. It fixes the names, principles, shared types, decided architecture, phases and performance targets, and a tab that disagrees with it is wrong. Twelve subsystem tabs specify the rest, each with the same skeleton: a guide-level walkthrough, design sections that each end in a capability table, then State of the art, Platform notes, Interfaces, Oracles, Phasing, Open questions and Sources. A tab that believes a contract rule is wrong files a change request; the contract changes only in a ruling.

Two summary tabs complete the set. The [Adversarial review](13-adversarial-review.md) records how independent reviewers attacked the spec and what changed, and the [Decisions log](14-decisions-log.md) lists every numbered decision in one line. Crucible, Ingot, Anvil, Flux and Kiln are working names; Flux is renamed in phase 0 and Kiln is cleared or renamed there too.

## Why Crucible, and why not a clone

An engineer who switches tools needs reasons that hold up in daily work, and a reason that an AI-built clone could add in a few weeks of agent time is no reason at all. This section compares what the incumbents and the clones give with what Crucible's one typed model gives.

### Where the field stands

Each incumbent leads in one part of the problem. Parasolid and ACIS lead on solid modelling; Ansys, Abaqus and COMSOL on simulation; Mastercam, hyperMILL and NX CAM on machining; Altium and KiCad on boards; Teamcenter and Windchill on product records. Onshape writes its own standard features in FeatureScript, the language its users get, and checks units in it at run time [Onshape FeatureScript variables]. Zoo's KCL and the Python libraries CadQuery and build123d make code the model. Fusion exposes a Model Context Protocol (MCP) server, the standard through which AI applications call tools [Autodesk Fusion MCP]. Onshape serves FeatureScript to agents the same way [Onshape FeatureScript MCP], and Zoo's Zookeeper writes KCL and reviews snapshots of its own work [Zoo Zookeeper].

AI-built clones now reproduce incumbent features quickly. SolidCraft, a Rust parametric CAD application, ships sketches with a solver, a feature timeline, sheet metal, assemblies with joints and motion studies, STEP and IGES exchange, and an MCP server [SolidCraft]. CADCraft, a clean-room reimplementation of AutoCAD, reads and writes DXF and DWG and edits sketches with trim, extend, fillet and chamfer [CADCraft]. Features alone, then, are not a moat.

What none of them does is make one typed program the model, with units, tolerances and error checked by the compiler, every result stating its trust, and every edit reviewable as text and checked before it merges. That is the gap Crucible fills.

### The comparison

| What an engineer relies on | What the incumbents give | What the AI-built clones give | What Crucible's one typed model gives | Owner |
| --- | --- | --- | --- | --- |
| The model itself | A feature tree inside the tool; FeatureScript as the open exception, with units checked at run time | A feature timeline saved as JSON (SolidCraft) | A pure Ingot program in which units, dimensions and tolerances are types, checked before anything runs | [ING](01-ingot.md) |
| Geometry that rebuilds | Local tolerances and a best guess near coincidence (Parasolid, ACIS) | Fillets, shells and Booleans on an open kernel without certified decisions (SolidCraft on Truck) | Every topological decision proved or refused, with the same faces, names and bits on every machine | [ANV](02-anvil.md) |
| References to faces and edges | Toponaming mitigation and positional fallbacks (FreeCAD, KCL) | None cited in the tabs | Names derived from source text and roles, never from position, with typed errors whose fixes compile | [ANV](02-anvil.md), [ING](01-ingot.md) |
| Simulation | The analyst meshes, defeatures and runs convergence studies (Ansys, Abaqus, COMSOL) | None cited in the tabs | A solve on the exact geometry with a stated bound on exactly the quantity each check reads | [FLX](03-flux.md) |
| Trust in a model | Credibility left to the analyst's judgement | None cited in the tabs | A validity zone, a credibility level and a model-form bound attached to every result as data from physical tests | [COV](04-coverage.md) |
| Branches and merges | Onshape merges whole tabs and cannot merge drawings [Onshape merging] | Undo and redo as the only recovery (SolidCraft) | Block-level merges, drawings included, that refuse a merge which worsens a check, adds interference or edits one entity from both sides | [KLN](05-kiln-repo-plm.md) |
| Design rules and stack-ups | Separate tools run on demand (Tecnomatix Variation Analysis) | None cited in the tabs | Fits, stack-ups and design rules as checks on every merge, on the drawing's own tolerances | [MEC](06-mechanical.md) |
| Agents | Copilots that answer questions or edit the open model; agents that review their own snapshots | An MCP command channel with no permission model described (SolidCraft) | The same typed `api` people use, work delivered as Proposals attacked by an independent verifier and classed by risk | [AGT](09-agents.md) |
| Machines and outside effects | Program verification as a separate step (VERICUT); approval of agent effects not described | None cited in the tabs | Approvals signed over content digests, a machine gateway that refuses anything else, and no remote cycle starts | [MFG](07-manufacturing.md), [AGT](09-agents.md) |
| Product records | Lifecycle records in a separate PLM system (Teamcenter, Windchill) | None cited in the tabs | Items, BOMs and change orders in the design repository; a release signs exactly the content its checks evaluated | [KLN](05-kiln-repo-plm.md) |
| Same answer everywhere | Bit reproducibility only at a fixed thread count (oneMKL) [Intel oneMKL reproducibility]; x86 Windows and Linux first (Ansys) | None cited in the tabs | Identical bits on every Tier 1 CPU target and browser, at any thread count | [PLT](12-platform-performance.md) |
| Presenting the product | Exploded views and reports built in a separate step (SOLIDWORKS Composer, Ansys Report Preview) | None cited in the tabs | Illustrations, animations, reports and web views computed from the live model, every number bound to it | [UIX](10-ui.md) |

### Why a clone cannot copy it in weeks

The right-hand column is not a list of features. Each entry rests on a mechanism with oracles and, for physics, on data from made and measured parts: certified geometric decisions, calibration corpora for error estimates, validation campaigns that set model-form bounds, a canonical arithmetic that every target reproduces, and a merge that evaluates checks. A clone can add a fillet dialog in a day; it cannot add a measured model-form bound without running the tests. Each tab's State of the art section holds a parity table that names the incumbent feature, Crucible's row and phase, and whether Crucible is ahead, equal or later, with a reason.

## Principles

Seven principles bind every tab ([contract section 3](../contract.md#3-principles-non-negotiable)); each is stated here in one line.

1. **No privileged code.** Built-in features use only the public mechanisms anyone can use, so whatever Crucible's builders can make, a user or agent can make too.
2. **Agents author; people steer, review and present.** Agents write the typed program; people point, mark up, ask, review every Proposal, approve every outside effect and present the result, and nothing exists only in the GUI.
3. **Two universal types.** `Body` carries geometry and `Field` carries physics data.
4. **Determinism is a feature.** The same inputs and versions give identical outputs per platform class, and evaluation never depends on clocks, randomness, thread order or names.
5. **The compiler checks physics.** Units, dimensions and tolerances are types, and every approximation carries its error in a stated norm.
6. **Every claim has an oracle,** with a held-out split the builders never see.
7. **Open core, interop first.** Kernel, language and standard library are open source, and no design is ever trapped.

## Architecture

Code sits in three tiers so that the core stays small and anyone can extend Crucible the way its own builders do ([contract section 4](../contract.md#4-layering-operations-wasm-components-features)).

| Tier | Written in | What lives there | Rule |
| --- | --- | --- | --- |
| Operations | Native Rust, in Anvil and Flux | A few hundred geometry and physics primitives behind versioned contracts | A released version is frozen by a hash of its source closure; a design pins the versions it was built with |
| Wasm components | Rust or another language, compiled to WebAssembly (Wasm) | Nesting, CAM strategies, slicers, placers and routers, importers, specialist solvers | Sandboxed and determinized; they reach operations only through the WIT package `crucible:ops`, where WIT is WebAssembly Interface Types |
| Features | Ingot | Design intent, orchestration, entity selection and naming, checks and dialog metadata | The default tier |

The tier rule keeps code in Ingot unless it needs more than about 10⁶ primitive steps per call, an existing codebase in another language, or a data structure Ingot cannot express. Code becomes an operation when three independent packages need it, it needs GPU or SIMD kernels, or it must be differentiable through Flux. Third-party Wasm components always run out of process, and they never get raw GPU, clock, file or network access.

[[DIAGRAM diagrams/00-overview-architecture.jsx: Crucible architecture · clients, api, Kiln and the three tiers]]

Read the diagram top to bottom. People, agents, scripts and hardware CI reach the design only through `api`, the one API whose methods fall into eight groups. Edits become Changes in the design repository; an Evaluation asks Kiln, the incremental engine, to compute nodes; Kiln runs features, Wasm components and operations as memoized nodes and stores every result in the CAS, the content-addressed store where each object is named by the SHA-256 hash of its bytes. Data made outside evaluation, such as a supplier offer or a lab measurement, enters only as a signed, pinned External input, and an Act, such as a release or a transfer to a machine, leaves Crucible only after a named person approves its exact plan.

The crates follow the same layering ([contract section 12](../contract.md#12-crate-map)): a platform row, the shared contract types in `base`, the engine core, geometry, physics, language, the product services `repo`, `plm` and `trust`, and the API surface. Domain crates never depend on Kiln, apps reach the engine only through `api`, and `cargo xtask check-layers` fails any other dependency.

## The canonical bracket

Every tab explains itself on one example, an L-shaped aluminium bracket with a stiffening web ([contract section 6](../contract.md#6-ingot-syntax-reference)). ING owns the grammar and keeps the example valid.

```
use std::mech::{sketch, rect, extrude, rib, fillet, part}
use std::materials::alu_6061_t6
use std::sim::quick::static_stress

/// L-bracket with a stiffening web.
#[toolbox(category: "Structure", icon: "bracket")]
pub feature bracket(
    #[ui(step: 5mm)]
    width: Length in 20mm..=400mm = 60mm,
    thickness: Length = 6mm ± 0.1mm,
    load: Force = 1.2kN,
) -> Part {
    let outline = rect(width, 40mm)
    let base = sketch(plane.xy) { outline } |> extrude(thickness)
    let web = base.edge(role: end(outline.top)) |> rib(height: 20mm, t: thickness)
    let body = base + web
    let solid = body |> fillet(body.edges(new), 2mm)
    let p = part(solid, name: "Bracket").material(alu_6061_t6)
    let clamp = base.face(role: start_cap)
    let tip = web.face(role: end_cap)
    let study = static_stress(p, fixed: clamp, force: load * dir(-y), on: tip)
    let stress = study.von_mises.max(over: study.regular())
    p.require(stress < 0.6 * p.material.yield_strength(at: 20degC), name: "static_margin")
}
// width + load  →  error ing/3001: cannot add Length and Force
```

Four things in it carry the whole platform.

- **Types catch physics mistakes.** `width + load` does not compile, and the tolerance on `thickness` travels to two independent PMI sites, one on the plate and one on the web. PMI, product and manufacturing information, is the dimensions, tolerances and notes attached to the 3D model ([ING](01-ingot.md), [MEC](06-mechanical.md)).
- **Nothing is picked by position.** The web stands on the edge whose role is `end(outline.top)`, so a dimension change never re-selects a different edge ([ANV](02-anvil.md)).
- **The check knows where the model lies.** Stress is infinite in the model at the clamp's edges and the loaded patch's edges, though not in the real part, so the check reads `study.regular()`, the part minus Flux's flagged neighbourhoods, which keeps the web-root fillet where bending peaks ([FLX](03-flux.md)).
- **The verdict is named and three-valued.** `static_margin` concludes `Pass`, `Fail` or `Undecided` with a reason, and its name keeps its identity when other checks are added. It passes at the default 6 mm and fails at 4 mm, where the web root's bending stress exceeds the limit.

## How far to trust a number

Every result Crucible shows answers ten questions, and each answer has one type and one owner ([contract section 5.2](../contract.md#52-how-far-to-trust-a-number)). This section walks the bracket's `static_margin` check through them at the default 6 mm plate. The stress figures are COV's worked illustration, not measurements: a regularized peak of 118 MPa at the web-root fillet, where a regularized peak is a stress averaged over a small stated region because a raw maximum depends on the discretization.

| Qualifier | Question it answers | What the bracket shows | Owner |
| --- | --- | --- | --- |
| Fidelity | How hard did we try? | `Preview` paints a picture and decides nothing. `Interactive` returns in about a second at polynomial degree 2 with a cheaper estimate, and its verdict is provisional. `SignOff` adapts until the bound is tight and confirms it by one further refinement | KLN |
| Result status | Is the value here and current? | While the width is dragged, the stress shows as `Proxy`, extrapolated from its last value; it becomes `Ready(Interactive)`, stays `Pending` for the `SignOff` node, then `Ready(SignOff)` | `base` |
| Error budget | Which errors were counted, and which were not? | Discretization ±1.5 MPa, plus small algebraic, regularization, floating-point and input parts. Model form is `NotQuantified` until the phase 1 validation campaign measures fillet strain; afterwards it is 10.2 MPa | `base`, FLX |
| Bound kind | How sure is each error bar? | Discretization is `Estimated`, multiplied by a calibrated class factor so that it undershoots in at most α = 0.01 of held-out cases; regularization and floating point are `Guaranteed`; model form is `Estimated { Statistical }` from ASME V&V 20 at α = 0.05 | `base`, FLX |
| Validity zone | Is the model inside the range where it was checked? | `Calibrated`: 20 °C and a stress ratio near 0.5 sit inside the tested range. At 120 °C the zone is `Extrapolated` and model form grows 1.6 times; at 3 kN the fillet yields and the envelope refuses the result | COV |
| Model level | What form of physics produced it? | L3, full 3D: neither the 6 mm plate nor the web is slender enough for a shell, so the whole Part is a solid on an immersed octree | COV |
| Credibility level | How well has this model been tested against reality? | C3, Validated, for the response quantity "regularized surface peak at a fillet, linear elastic"; the same model with an untested alloy is C2, Benchmarked | COV |
| Platform class | Where would the same bits come out again? | The `SignOff` value comes from the canonical class, so the designer's laptop, a reviewer's browser and two release builders produce the same `ObjectId`; the drag-time value may come from a faster native path cached only under that machine's class | PLT |
| Verdict | What does the check conclude? | `Pass`: 118 + 1.5 + 10.2 = 129.7 MPa against a limit of 144 MPa (0.6 × the 240 MPa specification minimum yield), at confidence at least 1 − (0.01 + 0.05) = 0.94. Before validation it is `Undecided { Unquantified([model form]) }` unless a pinned policy allowance covers model form. At 4 mm it is `Fail` | ING |
| Gate | May it merge or release? | A non-provisional `Pass` in a platform class the gate accepts meets the gate predicate, so the Proposal may merge; the release then needs a person's Approval of its subject digest, and two independent trusted builders must agree on the result | ING, KLN |

Two readings of this table matter. First, the numbers that decide come only from bounds that hold for the quantity the check reads: an error measured in one norm never certifies a peak, and a total with any uncounted part is `NotQuantified`, so the check says `Undecided` and names what is missing. Second, nothing switches silently: Crucible names a valid model or a missing test as a fix, and a person or agent edits the design.

The owners' sections hold the rules: fidelity and status in [KLN](05-kiln-repo-plm.md), budgets and bound kinds in [FLX](03-flux.md), zones, levels and model form in [COV](04-coverage.md), platform classes in [PLT](12-platform-performance.md), and the decision rule and gate predicate in [ING](01-ingot.md).

## The life of one change

Every tab assumes one story: an edit travels through the engine to a check, a review, a release and a measured part. Here it is in order, on the bracket, with the tab that specifies each step.

1. **Ask.** A designer asks an agent to widen the bracket to 80 mm. The agent opens a session on a new branch with a cost budget and scoped permissions, reads the bracket's typed outline, and sends one edit that sets `width` to 80 mm. The server turns it into a one-line source patch and records an immutable Change ([AGT](09-agents.md)).
2. **Recompute.** Kiln re-runs only the nodes downstream of that literal: the extrusion, the rib, the Boolean, the fillet, the solve and the check. The clamp face and the loaded face keep their entity names, because names never depend on argument values, so the study and the check keep their identities and history ([KLN](05-kiln-repo-plm.md), [ANV](02-anvil.md)).
3. **Simulate.** Flux warm-starts the solve. An `Interactive` value with an `Estimated` bound arrives in about a second; the `SignOff` node follows in the background ([FLX](03-flux.md)).
4. **Propose.** The agent opens a Proposal: a branch plus rationale plus CI report, the unit of agent work and of human review. The server refuses it unless the head builds, every check meets its gate, and rendered Snapshots exist ([AGT](09-agents.md)).
5. **Attack.** An independent verifier, which never sees the author's free text, thins the web and sees `static_margin` fail, so the check is not vacuous, then replays CI in a second platform class. The server computes the risk class from the semantic diff ([AGT](09-agents.md)).
6. **Review.** The owner opens the Proposal on evidence first: changed verdicts, margins and mass, then the geometry overlay and the source diff. She marks up the fillet and asks a question that reaches the agent as a request, then approves the merge with her security key ([UIX](10-ui.md)).
7. **Release.** A change order, which is a Proposal with lifecycle scope, prepares a release plan whose subject digests the Item's name-free definition, the verdicts and the cited records. The approver signs that digest; any later change to what is made voids the Approval, while a rebase that leaves it unchanged does not ([KLN](05-kiln-repo-plm.md)).
8. **Make and measure.** The shop machines the part from the released STEP AP242 file with semantic PMI. The external lab's signed measurements return as Evidence records, which a bot Proposal pins against the checks they serve ([MFG](07-manufacturing.md), [KLN](05-kiln-repo-plm.md)).

Everything the release depended on is pinned in `ingot.lock`: operation versions, packages, policy packages and Evidence records. One Change therefore fixes every outcome, on every machine, for as long as the records are kept.

## Discretization chosen per region

An incumbent analyst spends much of the day choosing elements, meshing and deciding which walls become shells. Flux makes that choice from the geometry and the study, records it as a pinned plan, and lets the engineer override any part in source ([contract section 7.1](../contract.md#71-engines), [FLX](03-flux.md)).

| Region | Model | When it applies |
| --- | --- | --- |
| Thin walls | Reissner–Mindlin shells on Anvil's mid-surfaces | Where the wall thickness t and the local length L_local satisfy t / L_local ≤ 0.2 |
| Members and struts | Timoshenko beams, with Vlasov warping for open thin-walled sections | Where a member is slender over its local length |
| Lattices | Beam-lattice models with node corrections, or homogenization | Strut graphs from Anvil's lattice operation |
| Solids | An immersed adaptive octree with aggregated CutFEM at `Interactive` and `SignOff`, at least four cells across any section | Everything the criteria above do not reduce |
| Contact and turbulent boundary layers | Fitted meshes, which Anvil generates | Where the immersed grid cannot resolve the layer |
| Revolved or prismatic bodies under matching loads | Axisymmetric or planar section models | When Anvil certifies the symmetry and the loads share it |

CutFEM is the finite element method on a background grid that the geometry cuts through, so nobody builds a fitted mesh; "aggregated" means tiny cut cells merge with their neighbours for stability. L_local is the smallest of the span between supports, the radius of curvature, the distance to the nearest concentrated load, patch edge, opening or feature, and the length over which a distributed load varies; a load that covers the whole wall does not shorten it.

Reduced regions join solid ones through rigid couplings at `Interactive` and Nitsche-based mixed-dimensional interfaces at `SignOff`, and junction zones stay solid. Every reduction by symmetry is checked: if a load or a face breaks the symmetry, the solve fails with `SymmetryBroken` instead of returning a confident wrong answer. The bracket itself is the simplest case, a solid on the octree, because neither its 6 mm plate nor its web is slender enough for a shell.

## Viewer first: review and presentation

Agents author, so the human interface is first a fast viewer, a review desk and a presentation studio, not a modelling workbench ([contract section 7.6](../contract.md#76-api-agents-acts-and-the-human-interface), [UIX](10-ui.md)). People inspect geometry and results, review agent Proposals, steer by pointing, marking up and asking, and present the product. Every product change still goes through `api`, so the UI holds no product state of its own.

### Viewing and reviewing

One Rust UI toolkit and one wgpu renderer serve every Tier 1 platform, native and in the browser, on three declared GPU tiers: G1 native, G2 WebGPU and G3 WebGL2. Display data are per-Body tessellations keyed by geometry identity and cached in the CAS, so equal geometry in two designs shares them. Fields paint on the true geometry with their stated error, and the legend names the fidelity.

Review opens on evidence: the checks whose verdict or margin changed, then mass and cost deltas with their bounds, then a geometry overlay of both sides, then the source diff. A circle drawn on a fillet becomes a comment anchored to that fillet's entities and the current view; a typed question becomes a request to the agent. Review, Present, Design, Simulate, Manufacture and Electronics are presets over one workspace, and Review is the default.

### Presenting

The presentation studio makes, from the live model, technical illustrations, exploded views, Field and deformed-shape animations, a view of how Flux discretized the part, shareable read-only web views and generated reports in phase 1; photoreal path-traced renders, animation of moving parts from mates and motion studies, and generated decks follow in phase 2 ([contract section 13.4](../contract.md#134-shared-phases-and-the-parity-floor)). Every output is a Snapshot, a rendered image of a saved view under a pinned render profile, or an ordered set of them. A presentation is therefore a file in the design repository that an agent can write, a reviewer can diff and a release can pin.

Every number in a figure or caption is a readout bound to the model, with its unit, bound and status. When a later Change edits the fillet, the report and the web view re-render and every number follows; a readout that is not current at the scene's fidelity carries a provisional badge, so a slide cannot quietly show a stale margin.

### The polish bar

The founder's reference for polish is Anatomy, an open project that builds explanatory figures of real objects and holds them to written rules [Anatomy skill]. Crucible meets that bar with its own Rust renderer, on real engineering geometry and simulation Fields: editorial serif typography on a calm canvas, fine-line isometric drawings with labelled callouts anchored to entities, real 3D motion with moving parts a viewer can rotate and inspect, and fluid, heat, flame and plasma effects drawn from computed Fields. An effect from an authored, not computed, Field is captioned "illustrative", so a viewer never mistakes decoration for a result, and every effect follows the reference's rule that nothing pops [Anatomy craft]. UIX's oracles measure the bar against path-traced references and the frame-time targets of contract 13.3.

## Subsystems

Each subsystem tab opens with a guide-level walkthrough on the bracket or a golden product; the paragraphs below say what each owns and link to it.

### Ingot language (ING)

[Ingot](01-ingot.md) is the language every design is written in: a part is a short, pure, statically typed program whose dimensions carry units and tolerances and whose requirements are named checks that say how sure they are. A length added to a force fails before anything runs, each tolerance reaches the drawing, and each error bar reaches the verdict. Every geometry or physics call becomes a named, cached Kiln node, so an edit is a small text change that rebuilds identically everywhere.

### Anvil geometry kernel (ANV)

[Anvil](02-anvil.md) holds one `Body` type over four representations: exact boundary representation (B-rep), implicit, mesh and subdivision surface, and mixing them never silently approximates. Where other kernels settle near-coincidences with one global tolerance and a best guess, Anvil proves each topological decision or says it cannot. Every operation is versioned and returns the history that keeps face and edge names stable when dimensions change.

### Flux physics engine (FLX)

[Flux](03-flux.md) poses physics as weak forms written in Ingot, the integral equations that finite elements solve, or as ready-made studies such as `static_stress`. It solves on the exact design geometry with a discretization chosen per region, recomputes only what an edit touches, and returns Fields that name each error source and how sure each bound is. It also provides multibody dynamics, the solver for lumped Networks (domain-typed ports compiled into a DAE, a system of differential-algebraic equations), full-wave electromagnetics and the operations non-variational methods need.

### Physics coverage and materials (COV)

[COV](04-coverage.md) decides which physics Crucible can honestly claim, as versioned physics packages, and keeps the versioned Material records every simulation reads. Each model carries a validity envelope, its record of where physical tests checked it, stored as data that compiles into checks on every result. Every gap is a named record, and Crucible names the valid model where one is needed but never switches models on its own.

### Kiln, repository and PLM (KLN)

[Kiln](05-kiln-repo-plm.md) re-runs only what an edit affects, and the product services `repo`, `plm` and `trust` keep history, Items, revisions, BOMs (bills of materials), change orders and signatures. A Crucible repository is an ordinary Git repository: every edit is an immutable Change stored as a commit on a cheap branch, people clone and push it with the tools they already use, and GitHub or GitLab can mirror it, with their pull requests arriving as Proposals ([contract section 7.1](../contract.md#71-engines)). Merges are by block, drawings included, and refuse a worse check, new interference or an entity edited from both sides; only Kiln's own Git server writes protected branches, so no mirror can skip a signature. Computed results stay out of Git in a content-addressed cache, and each commit carries Crucible's SHA-256 identity, so a cached result, a merge verdict and an Approval all name the same content, on a laptop, a team server, the cloud or an air-gapped site.

### Mechanical design (MEC)

[`std::mech`](06-mechanical.md) is the Ingot library for mechanical design, from sketch to released drawing: parts, assemblies, surfacing, sheet metal, weldments, composites, moulded parts, routing, tolerancing and model-based definition. Every domain shares one constraint solver, one way of naming faces by how they were made, and one tolerancing model. Fits, stack-ups and design rules are therefore checks on every merge, and drawings, stack-ups and inspection read the same tolerances.

### Manufacturing (MFG)

[`std::mfg`](07-manufacturing.md) turns a released design into made parts: machining, printing, moulding, welding, inspection, cost and factory records as one typed plan that regenerates when the design changes. A design change re-plans exactly the operations it touches and re-checks the posted program on a model of the real controller. A named person approves each program's digest with its setup sheet and simulation results, the machine gateway refuses anything else, and a person at the machine starts every cycle.

### Electronics and systems (ELX)

[ELX](08-electronics-systems.md) covers circuits, printed circuit boards, harnesses, motors, batteries, controllers and firmware, simulated inside the product they power. Connectivity is typed code, a `Network` of parts joined at typed ports, and the drawn schematic and board are data that checks prove equal to it. Board, enclosure, harness and firmware share one design repository, so no exchange step can go stale.

### Agents (AGT)

[Agents](09-agents.md) are colleagues on branches: they call the same typed `api` a person's clicks call and hand their work over as Proposals. Each agent Proposal arrives built, checked, attacked by an independent verifier and classed by risk, from R0 (no semantic change) to R4 (feeds an Act). Safety lives in the server, not the model: untrusted text never carries authority, and nothing leaves Crucible until a named person approves its exact plan.

### UI and interaction (UIX)

[UIX](10-ui.md) is where people inspect, review and present what agents design: a fast 3D viewer, a review desk and a studio for renders, animations, illustrations and reports. Every picture and number is computed from the live model with its status and error, so reviews, slides and reports stay checkable as the design changes. One Rust toolkit and one GPU renderer deliver it identically on every desktop system and browser.

### Interop and ecosystem (ECO)

[ECO](11-interop-ecosystem.md) owns everything that crosses Crucible's boundary: translators for other tools' files, sandboxed Wasm extensions, the registry, the SDKs (software development kits), connectors, licensing and compliance. Every translator and extension is a deterministic, signed package whose output is pinned like any input, and licensed translators that cannot be deterministic only hand the build signed, pinned files. Imports stay live in the design, and exports reproduce byte for byte years later.

### Platform and performance (PLT)

[PLT](12-platform-performance.md) runs Crucible on every machine: deterministic numerics, the compute and Wasm runtimes, the OS and browser layer, deployment, packaging, the build program and the performance targets. Its mechanism is one canonical platform class, whose arithmetic (correctly rounded math, no implicit fused multiply-add, fixed reduction trees) leaves nothing to the processor, OS or thread count. A Windows laptop, a Mac, a Linux server and a browser tab therefore produce identical results, so one computation serves the whole team and every later audit.

## Guarantees across every tab

Some rules hold in every subsystem; the contract states them once and each tab applies them. This section gives each in a few lines with its owner.

### Determinism and caching

Results are bit-identical within a platform class, and the operating system is never part of a CPU class ([contract section 7.3](../contract.md#73-determinism)). The canonical class covers every Tier 1 CPU target, browsers included, at any thread count; `CpuIsa` is a native fast path for one instruction-set level; `Gpu` is one compiled pipeline on one verified device class; `Unverified` covers everything else. Non-canonical results never substitute for canonical ones, except through a witness: a pinned GPU Field whose residual and error bound are computed canonically.

Kiln finds a result by its `NodeKey`, the hash of the code, arguments, input identities, platform class and fidelity that produced it, never of the lockfile as a whole ([contract section 7.2](../contract.md#72-keys-failures-and-aborts)). Geometric results are keyed by name-free geometry identities, so a standard feature called from two designs shares every geometric result. A `Failure`, such as a fillet radius too large, is a typed, cached value that `try` can catch; an Abort, such as a cancellation or a lost device, is environmental, never caught and never cached. The determinism suite runs on every merge on a representative set of targets and nightly on the rest, and a nightly divergence blocks promotion to beta ([PLT](12-platform-performance.md)).

### Trust in the shared cache

Proposal CI from agent and external branches, and every External Op, runs on untrusted-evaluation workers in single-use microVMs that hold no signing key ([contract section 7.8](../contract.md#78-trust-and-the-shared-cache)). Trusted builders evaluate only merged Changes of protected branches. Release gates and `SignOff` checks accept a cached result only when two independent trusted builders produced the same `ObjectId`; other cache hits are spot-checked, and every released revision is re-verified after a toolchain or math-library upgrade. Tool processes and External Op hosts run with network egress denied unless an administrator grants a named endpoint.

### Labels and agents

Every artifact, API response and model context carries labels with three parts, joined through every derivation ([contract section 5.3](../contract.md#53-labels)). Confidentiality (level, export controls, scopes) decides who may read; usage (data licences) is compared at exits; integrity (`instruction_tainted`, `data_untrusted`) never blocks anything but sets risk classes and auto-merge eligibility. Reading untrusted free text taints a model context, and every write carries at least the context's label, so a write to a lower confidentiality fails with `label/write_down` unless a declassification record signed by two people names it ([AGT](09-agents.md), [KLN](05-kiln-repo-plm.md)).

Agents work only on branches, with scoped permissions, cost budgets and clearances. A credential held on a device authenticates as a device agent, never as the person, so an agent with a shell cannot merge, endorse, waive or export as its human.

### Signatures, Acts and physical safety

Every human signature is one detached record whose meaning comes from one signature table, evaluated by Cedar policies; no agent signs any record in it ([contract section 5.4](../contract.md#54-signature-records-and-the-signature-table)). An Act is two-phase: `act.prepare` produces a plan with a digest, and `act.commit` runs only after an assigned person approves that digest with phishing-resistant WebAuthn and a device-bound credential. Synced passkeys sign in but never approve, and on a phone a person may approve only release and change-notice Acts that carry no export controls and no physical effect, in the browser, with a roaming security key.

Crucible never issues a cycle start, resume or jog to a device it transfers to; a person starts the machine at the machine ([contract section 7.6](../contract.md#76-api-agents-acts-and-the-human-interface)). The one restricted exception is `start_print` for material-extrusion printers covered by a site safety record, a record signed by a named safety officer, with a confirmation at the printer. Firmware flashing leaves the board halted or held in reset, and test rigs run unattended only under a site safety record backed by an ISO 12100 risk assessment; production equipment never receives one ([MFG](07-manufacturing.md), [ELX](08-electronics-systems.md)).

### Platforms

| Tier | Targets | What it gets |
| --- | --- | --- |
| Tier 1 | Windows 11 on x86-64 and ARM64; macOS on Apple silicon (current and two prior); Linux on x86-64 and ARM64; Chrome, Edge, Safari and Firefox through Wasm with WebGPU and a WebGL2 fallback | The full product, identical features, every golden product passing |
| Tier 2 | iPadOS and Android tablets; ChromeOS through the browser; phones as viewers | Viewing, review, presentation and light editing |
| Tier 3 | FreeBSD and other Unix systems | Community support; joins the canonical class only after passing the determinism suite |
| Servers | Linux containers on x86-64 and ARM64 | Team servers and cloud workers, with optional GPU acceleration |

Parity means identical features and identical canonical results on every Tier 1 platform, computed locally or remotely; capacity and speed differ and are declared ([contract section 9](../contract.md#9-platforms)). Phase 1 ships generally on Windows 11 x86-64, macOS, Linux x86-64, Chrome and Edge; the ARM64 desktops, Safari and Firefox are preview targets in phase 1 and generally available at the phase 2 gate.

### Openness, licensing and releases

Code is licensed Apache-2.0 WITH LLVM-exception, documentation CC-BY-4.0, and examples and templates MIT-0; external contributions come under the Developer Certificate of Origin ([contract section 7.7](../contract.md#77-interop-ecosystem-and-support)). GPL-family code is never linked: it runs only as an external tool, an External Op or a test oracle. Open formats are built in Rust from their schemas, licensed translators run outside evaluation so anyone can rebuild without the licence, and Crucible never replays proprietary feature history. Releases ride a 6-week train with a yearly LTS release, every stable line gets security fixes for at least five years, and one LTS line every two years gets 10 years of regulated support ([ECO](11-interop-ecosystem.md)).

## Roadmap

Crucible ships in phases, and each phase ends at a gate that real, made and measured products must pass, never on a date ([contract section 13.1](../contract.md#131-phases-and-golden-products)). A golden product is a reference product whose checks must pass and whose physical articles are made and measured to close a phase.

[[DIAGRAM diagrams/00-overview-roadmap.jsx: Roadmap · eight phases, gated by golden products]]

Read the diagram top to bottom: each band is a phase and what it adds, each diamond is the gate that closes it, and the dashed phases 5 to 7 are proposals.

| Phase | Theme | Golden products that close it |
| --- | --- | --- |
| 0 | Foundations | None; the phase 0 gate list below |
| 1 | Wedge: code-CAD and 3D printing | GP1 machined bracket; GP2 topology-optimized lattice bracket in metal laser powder bed fusion |
| 2 | Mechanical depth | GP3 gearbox with machined parts cut from Crucible's programs; GP4 welded frame with sheet-metal guards and measured weld distortion; one printed part sent to an open-firmware printer |
| 3 | Product breadth | GP5 moulded enclosure with its PCB, with measured warpage and drop response |
| 4 | Full multiphysics | GP6 drone, validated against flight, dynamometer and thermal data |
| 5 | Scale | GP7 MEMS accelerometer; GP8 bolted steel platform through IFC 4.3; GP9 crash box |
| 6 | Aerospace and electrification | GP10 composite wing box; GP11 CubeSat; GP12 EV battery sub-pack |
| 7 | Marine, buildings, medical and soft goods | GP13 workboat hull; GP14 timber pavilion; GP15 bone plate; GP16 sewn pack |

Contract 13.1 holds each gate's full text. Golden products 7 to 16 are proposals, each a separately funded program started only with a physical test partner and an approved plan.

### Gates, not dates

The phase 0 gate needs no physical article. It needs the determinism suite green, unit errors failing to compile, and the kernel intermediate representation (IR) frozen; every user-visible name cleared or replaced before any operation or interface name freezes; counsel's written opinions on the patent, authorship, standards-table and reverse-engineering questions; a freedom-to-operate search over every phase 1 code path; and GP2's alloy, machine, print bureau and build-preparation software fixed. The phase 1 gate adds counsel's product-liability assessment before general availability.

From phase 1, a gate is physical. GP1 is designed, toleranced, simulated and released in Crucible, machined by a reference shop from Crucible's STEP AP242 with semantic PMI, measured by an external lab and proof-loaded. GP2 is optimized and verified in Crucible, built from Crucible's 3MF by a bureau, measured and proof-loaded. Every physical gate states its replicate count, measures as-built geometry and same-lot coupons, keeps validation data out of calibration, and places sensors on exactly the quantities its checks decide.

Before the phase 1 run build is tagged, a validation campaign on separate specimens measures surface strain at fillets and in printed struts; its bounds govern the GP1 and GP2 releases, and the proof loads on every article then serve as held-out confirmation. The gate release must reproduce its STEP and 3MF exports bit for bit, or show equal geometry identities and definitional attributes with a reviewed diff; otherwise the physical run repeats.

### The parity floor

A capability an incumbent's user relies on has a latest phase, and a tab may phase it earlier but never later ([contract section 13.4](../contract.md#134-shared-phases-and-the-parity-floor)). Phase 1 already carries standard thread and clearance-hole designations computed from their formulas, DXF write and IGES read, sketch edits as source rewrites, Insert Instance and Add mate as generated dialogs, generative design for additive and unrestricted methods, analyst idealizations such as remote points and springs, and the presentation floor. Phase 2 brings photoreal rendering, motion studies and sheet metal, DXF and DWG read and write, toolpath editing, review routing and delegation, shape search, and bushings, connectors and submodeling. Later phases close the rest, from imported Nastran and Abaqus decks in phase 3 to ply optimization in phase 6.

A capability several tabs phase, such as modal analysis, inherent-strain distortion or battery cell models, has one phase and one owner in the same section, set by the first gate that needs it, and `check.py` fails a capability row phased earlier than a row it requires.

### Performance targets

PLT owns the targets, measured on one fixed reference laptop (Intel Core Ultra 7 258V, 32 GB, Windows 11 and Ubuntu LTS, at 1920×1080), and every figure is a target ([contract section 13.3](../contract.md#133-performance-targets)). A row blocks beta promotion from the phase in its last column. A few rows show the bar.

| Row | Native | Browser | Phase |
| --- | --- | --- | --- |
| Drag preview | The dragged feature and the dependents that fit, within 100 ms | Within 200 ms | 1 |
| Interactive simulation update | 1 s for linear elasticity up to 100,000 degrees of freedom, including the error estimates of up to five checked goals | 2 s with WebGPU | 1 |
| Orbit | 60 fps at 5M visible triangles | 30 fps at 5M with WebGPU | 1 |
| Shareable web view | None | A read-only GP1 view shades its first frame in 3 s at 50 Mbit/s | 1 |
| Photoreal still | Mean ꟻLIP error at most 0.05 against a converged reference within 30 s on G1 | Within 90 s with WebGPU | 2 |

## Program plan

Crucible is built by agents ([contract section 13.2](../contract.md#132-program-plan)). One human, the founder, directs the program; Claude orchestrates agent work against the oracles; outside firms make, measure and advise where the physical or legal world requires a person. Phases end at their gates, never on a date, and no plan figure counts people or engineer-years.

### Roles

| Role | What it does |
| --- | --- |
| Founder | Approves each phase's scope and budget at the previous gate, signs each golden product's pass and fail criteria before builders start on it, approves every Act and Waiver, and decides anything that changes money or scope |
| Orchestrator | Claude plans the work, opens work items, runs reviews and rulings, and keeps the contract and the tabs current |
| Oracle role | Writes a phase's contract crates and oracles and locks them before any builder works on what they verify |
| Builders | Implement against locked oracles and never write or edit `oracles/` or contract crates |
| Verifier | Independent of both: checks every oracle against its capability row and an independent source, and attacks every builder Proposal |
| Observer | Studies incumbents under the clean-room insight protocol, in a workspace builders never see |
| Outside firms | Counsel for freedom to operate, trademarks, authorship and reverse-engineering clearance; a reference machine shop, a metrology lab, a metal powder bed fusion bureau and a proof-load lab under signed phase 0 agreements |

Each phase carries one budget, approved by the founder at the previous gate: agent compute, cloud CI, rented GPU and device-farm time, physical runs with replicates and one re-run, validation specimens, metrology, proof loads and counsel. An adversarial review of the spec runs before each gate.

### How agents build against oracles

PLT owns the build program, and the contract fixes its rules ([PLT](12-platform-performance.md)).

1. **Interface first.** The oracle role writes a contract crate with the public types and signatures the oracles call; builders implement it and may not change it.
2. **Oracle first.** A work item opens only when its oracles exist as executable checks passed by the verifier, and each gate reports oracle coverage per crate.
3. **Held-out splits.** Every oracle that judges agent-built code keeps a split outside the agent-readable tree, chosen by a keyed hash or a seed drawn at CI time, and builders see held-out results only as one aggregate verdict per work item per day.
4. **Runner classes.** Each oracle names where it runs: CPU or browser CI, a rented GPU lab or device farm, a physical test by an outside firm, or a founder sign-off.
5. **Taint.** An agent context that reads third-party source, a web page or a paper is marked tainted, and its changes to core code, oracles, dependencies or CI need the founder's Approval with the taint sources listed.

Crucible's own repository runs in single-person mode: the founder signs each two-person record alone with the strongest credential and approves protected merges after the verifier's attested review, and each such record takes effect after 72 hours with notice to an out-of-band contact ([contract section 5.4](../contract.md#54-signature-records-and-the-signature-table)).

### Phase 1 and its critical path

Phase 1 builds only what GP1 and GP2 need, plus the presentation floor. It defers, with contracts and oracles unchanged, the Ingot code generator (the interpreter runs Ingot), the advanced renderer features and the GUI's own sketch tools, cloud SaaS and live sessions, CAM and slicing, the public registry, the hosted agent crew, guaranteed estimators on cut cells and GPU `SignOff` paths, and subdivision surfaces, lofts and other surfaces that need general NURBS (non-uniform rational B-spline) intersection. A desktop install without a team server designs, simulates, evaluates, presents and exports locally; Proposals, releases and every Act need a team server.

Four chains of work run in order:

1. **Chain A, geometry:** exact predicates, certified surface–surface intersection (SSI, computing the curves where two surfaces meet), Booleans, fillets and shells, GP1's features and drawing, STEP AP242, shop machining, metrology and proof load.
2. **Chain B, physics:** the kernel IR and its CPU back ends, immersed elasticity with dual-weighted residual (DWR) error estimation, topology optimization, implicit lattices, printed strut coupons, 3MF, the build, measurement and proof load.
3. **Chain C, interface:** the toolkit and renderer, then review (semantic diffs, anchored markup, sections and Field colour), then presentation (illustrations, exploded views, web views, reports), then steering, the drawing editor and keyboard-complete, accessible workflows.
4. **Chain D, release:** a single-node team server with Cedar policies and an audit log, microVM Proposal CI, the approval page and the release and export Acts.

The milestones are ordered, not dated: foundations and the phase 0 gate; phase 1 geometry, physics, interface and release; a physical dry run of both gates and the validation campaign; hardening; a tagged run build whose exports make the GP1 and GP2 articles; the physical runs with one re-run budgeted; and the phase 1 gate.

## The clean-room insight protocol

Crucible studies the incumbents to design something far better, never to copy them ([contract section 7.7](../contract.md#77-interop-ecosystem-and-support)). Its methods come from the published literature and first principles, and its code never reproduces an incumbent's code.

1. **Two roles.** An observer agent may study software the founder holds a licence to examine, including with the reverse-engineering tool REA [REA], in an isolated workspace with no network access. It writes only behavioural specifications of formats and protocols, test vectors made from Crucible-authored inputs, and analyses of what an incumbent does and where it falls short; never code, pseudocode or decompiled names. Implementers never see the observer's workspace.
2. **A gate between them.** The verifier reads each specification before release and rejects anything that copies expression. Released material enters the oracles or the spec through a Proposal with a signed provenance record, including counsel's clearance.
3. **An order of methods.** Published specifications first, then open readers, then analysis of sample files, then black-box observation of the running program. Decompilation serves only interoperability with a file format or protocol, never an incumbent's kernel, solver, mesher or CAM strategy, and licence checks are never circumvented.
4. **A legal boundary.** The EU Software Directive permits observing and testing a program to learn its ideas and decompiling only for interoperability; elsewhere, enforceable licence terms are respected. Counsel decides the governing jurisdiction and clears each engagement, and every resulting reader passes a freedom-to-operate review, because clean rooms do not avoid patents.

## Risks

Each risk below has a plain statement of how the plan contains it, then the mechanism and the owner that specifies it.

| Risk | Why it is hard | How the plan contains it | Owner |
| --- | --- | --- | --- |
| Certified intersections and Booleans | SSI topology is open research, and the Rust kernel Fornjot was archived without reaching its goals [Fornjot repository] | Start narrow and measure against the kernel users leave: phase 1 certifies only the surface classes its operations create, and whole parts rebuilt from public models must match their Parasolid originals at 98% at the phase 1 gate and 99.5% at phase 2 (targets) | ANV |
| Blends | Corners where four or more edges meet, variable radii and higher-continuity sections are research | Ship in stages: stage 1 covers sequential fillets, rolling overflow and mixed corners that GP1 needs, later stages add the rest, and an approximate fallback runs only when asked for, with its deviation stated | ANV, MEC |
| Error bounds | A calibrated bound can undershoot, and guaranteed bounds on cut cells are unsolved | Measure how often estimates undershoot on held-out cases and inflate them to cover all but 1%; re-check every `SignOff` pass with one finer solve; keep cut-cell bounds `Estimated` until a proof exists | FLX |
| Model form | No solver can say how wrong its equations are; only tests can | A check stays `Undecided` until a validation campaign or a cited policy allowance quantifies model form, and the phase 1 campaign runs before the run build | COV |
| Cross-platform determinism | Fused multiply-add, vector widths, browser engines and GPU drivers all change bits | One canonical arithmetic: correctly rounded math, fixed reduction trees, a known-answer test per GPU pipeline, and the determinism suite on every merge | PLT |
| Agent-built code | Builders see their inputs and can special-case them, and an oracle can be wrong | Oracles locked before builders start, held-out splits, an independent verifier, and corpora checked against independent sources | PLT, contract 13.2 |
| Physical validation | Gates need replicates, measured articles and proof loads, and later golden products need test partners | Signed phase 0 agreements with a shop, a lab, a bureau and a proof-load lab; a physical dry run; one re-run budgeted | COV, contract 13.1 |
| Agent and machine safety | Models read untrusted text, and transfers reach machines that cut, move or heat | Labels and write-down, two-phase Acts with assigned Approvals, no remote starts, allowlists inside the machine gateway | AGT, MFG |
| One approver | Every Act, Waiver and protected-path change in Crucible's own repository waits for the founder | Oracles and the verifier filter work before it reaches the founder, and single-person mode delays each record 72 hours with out-of-band notice | Contract 13.2 |
| Legal exposure | Patents, trademarks, standards tables, data licences and product liability each carry their own terms | Counsel's opinions before the work they cover, starting at the phase 0 gate; licences travel with data as labels | ECO, MEC, COV |

## Patents, trademarks and freedom to operate

Freedom to operate means the right to make and sell a product without infringing someone else's patent. Counsel's opinions and searches arrive before the work they cover, starting at the phase 0 gate ([contract section 13.1](../contract.md#131-phases-and-golden-products)).

| Item | What it covers | Crucible's position | Owner |
| --- | --- | --- | --- |
| US 12,229,885 B1 (inventor Alyn Rockwood) [US12229885B1] | Intersection points formed from points of one surface within a threshold distance of the other | Counsel's opinion on claims 1, 6, 11 and 16 is a phase 0 gate item. Every intersection point is a certified root of the exact equations; phase 1 SSI has no sampling stage, and GPU sampling joins in phase 2 only after a favourable opinion | ANV |
| US 9,164,503 (Boeing) [US 9,164,503] | Adaptive clearing that starts from a pre-roughing slot | A design-around spiral without that slot; counsel's opinion is a phase 1 gate item, and engagement-limited roughing ships in phase 2 whatever it says | MFG |
| Placement and routing | An active patent area | Placer and autorouter work opens only after counsel's search of its code paths | ELX |
| History and merge | Per-Change history and merge by provenance | Covered by the phase 0 search; a claim that reads on them changes the design before the phase 1 freeze | KLN |
| The name Crucible | Atlassian's Crucible code-review product [Atlassian Crucible] | Cleared in classes 9 and 42, or replaced, at the phase 0 gate | ECO |
| The name Flux | Siemens Simcenter Flux [Simcenter Flux] and flux.ai [flux.ai] | Renamed in phase 0, before any operation name or interface package freezes | ECO |
| The name Kiln | At risk | Cleared or replaced in phase 0 | ECO |
| Clean-room readers | Readers of proprietary formats built under the insight protocol | Each passes counsel's freedom-to-operate review and names formats only by what they are, with a non-affiliation line | ECO |

## Reading paths

The spec is long, and no reader needs all of it.

- **Mechanical engineer:** this page, ING's guide-level walkthrough, MEC through Tolerancing, then MFG's milling and inspection sections.
- **Simulation analyst:** this page, FLX's first study and weak-form language, COV's walkthrough of the bracket, then FLX's error budgets.
- **Security and compliance reviewer:** contract sections 5.3, 5.4, 7.6 and 7.8, then AGT's labels and Acts sections and KLN's signatures, identity and labels sections.
- **Builder agent:** the contract, then the owning tab's capability tables, Interfaces and Oracles.

## Open questions

About a dozen questions remain, each waiting on an outside input; the owning tab's Open questions section holds the detail.

1. **Flux's new name.** "Flux" collides with existing products, so no `flux::` operation name or WIT package freezes until the phase 0 rename; this spec keeps "Flux" until then ([FLX](03-flux.md), contract section 2).
2. **Freedom-to-operate opinions.** Counsel's opinions on US 12,229,885 B1 (GPU sampling for SSI), on adaptive clearing and trochoidal slotting, and the phase 0 search over history and merge are outstanding ([ANV](02-anvil.md), [MFG](07-manufacturing.md), [KLN](05-kiln-repo-plm.md)).
3. **GP2's process details.** The phase 0 gate fixes the bureau's build-preparation software and 3MF extensions, and whether GP2 uses sheet cells, which would bring shells for sheet lattices into phase 1 ([MFG](07-manufacturing.md), [COV](04-coverage.md)).
4. **GP1's receiver profile.** The tolerance and minimum feature of the shop's CAM and measuring software wait on the shop agreement ([ANV](02-anvil.md)).
5. **Strut waviness threshold.** It comes from the first as-built calibration build ([COV](04-coverage.md)).
6. **Guaranteed bounds on cut cells.** They wait on the research literature ([FLX](03-flux.md)).
7. **Standards content.** Which thread, hole and fastener tables std may ship, and the licensed editions that gear and bearing limits need, wait on counsel and the standards bodies ([MEC](06-mechanical.md), [COV](04-coverage.md)).
8. **Vendor controller kernels.** Whether a controller vendor licenses its virtual NC kernel for a customer-licensed host ([MFG](07-manufacturing.md)).
9. **Verilog-A front end.** Whether a clean-room front end covers the main transistor models in phase 3 waits on the research track's measurement ([ELX](08-electronics-systems.md)).
10. **Auto-merge thresholds.** The low-risk class defaults wait on review data from phase 2 ([AGT](09-agents.md)).
11. **Translator vendor, export-control and partnership terms.** The licensed translator vendor, the EU sector rules for open-source downloads, and the ODB++ partnership terms wait on negotiation and counsel ([ECO](11-interop-ecosystem.md)).
12. **Preset names and the iPadOS shell.** Counsel's review of "-like" preset names, and App Review of the iPadOS shell ([UIX](10-ui.md), [PLT](12-platform-performance.md)).
13. **Paywalled definitions.** A crash-test filter standard and the critical-distance definitions wait on an accessible primary source ([FLX](03-flux.md)).

## Glossary

Contract section 2 is the vocabulary of the whole spec: one name per component and one definition per shared concept, with the names never to use ([contract section 2](../contract.md#2-names-and-glossary)). The terms below are those this page uses; each tab spells out its own abbreviations at first use.

| Term | Meaning | Owner |
| --- | --- | --- |
| Act | An API method whose effect needs a person's Approval of an exact plan, because it reaches outside Crucible | AGT |
| Approval | A person's signature over the identity of an exact plan or release subject | KLN |
| B-rep | Boundary representation: a solid described by its faces, edges and vertices | ANV |
| BOM | Bill of materials | KLN |
| CAS | The content-addressed store, where each object is named by the hash of its bytes | KLN |
| Change | One immutable, fine-grained edit | KLN |
| Check | A predicate declared with `require`, concluded by a verdict | ING |
| CutFEM | Finite elements on a background grid that the geometry cuts through | FLX |
| DAE | Differential-algebraic equations, the form a Network compiles to | FLX |
| DWR | Dual-weighted residual: an error estimate for one goal quantity, computed with an adjoint solve | FLX |
| Evidence record | A signed measurement from a physical test, pinned against the check it serves | KLN |
| Fidelity | The accuracy demanded of a result: `Preview`, `Interactive` or `SignOff` | KLN |
| Field | A physical quantity distributed over a domain, carrying an error budget | FLX |
| Golden product | A reference product, GP1 to GP16, whose made and measured articles close a phase | Contract 13.1 |
| MCP | Model Context Protocol, the standard through which AI applications call tools | AGT |
| Oracle | A machine-checkable test that the agents building a capability cannot edit | Contract 3, 13.2 |
| PMI | Product and manufacturing information: dimensions, tolerances and notes on the 3D model | MEC |
| Proposal | A branch plus rationale plus CI report; the unit of agent work and human review | AGT |
| SSI | Surface–surface intersection: computing the curves where two surfaces meet | ANV |
| Waiver | A signed record that lets one named check count at a gate for named Items, with a reason and an expiry | KLN |
| WIT | WebAssembly Interface Types, the interface language of Wasm components | ECO |

## Sources

This page summarizes the [contract](../contract.md) and the twelve subsystem tabs, whose Sources sections list the pages their research opened. The pages below are cited here, each already cited by the contract or a tab.

| Key | Title | URL | Date opened |
| --- | --- | --- | --- |
| [Anatomy craft] | Anatomy, `references/craft.md` (MIT) | https://raw.githubusercontent.com/wheresryan22/anatomy/main/references/craft.md | 2026-10-12 |
| [Anatomy skill] | Anatomy, `SKILL.md` (MIT) | https://raw.githubusercontent.com/wheresryan22/anatomy/main/SKILL.md | 2026-10-12 |
| [Atlassian Crucible] | Atlassian Crucible product page | https://www.atlassian.com/software/crucible | 2026-10-11 |
| [Autodesk Fusion MCP] | Autodesk, "Introducing the Fusion MCP" | https://www.autodesk.com/products/fusion-360/blog/introducing-the-fusion-mcp-opening-fusion-to-ai-powered-workflows/ | By 2026-10-11 |
| [CADCraft] | CADCraft repository README | https://github.com/storytold/cadcraft | 2026-10-12 |
| [Fornjot repository] | Fornjot repository | https://github.com/hannobraun/fornjot | 2026-10-11 |
| [flux.ai] | Flux home page | https://www.flux.ai/ | 2026-10-12 |
| [Intel oneMKL reproducibility] | Intel oneMKL reproducibility conditions | https://www.intel.com/content/www/us/en/docs/onemkl/developer-guide-linux/2025-2/reproducibility-conditions.html | 2026-10-11 |
| [Onshape FeatureScript MCP] | Onshape, "FeatureScript MCP Server Enables Text Code CAD" | https://www.onshape.com/en/blog/featurescript-mcp-server-enables-text-code-cad | 2026-10-12 |
| [Onshape FeatureScript variables] | Onshape, FeatureScript variables and value semantics | https://cad.onshape.com/FsDoc/variables.html | 2026-10-11 |
| [Onshape merging] | Onshape Help, "Merging" | https://cad.onshape.com/help/Content/merge.htm | 2026-10-12 |
| [REA] | REA ("Reverse Engineer Anything") repository | https://github.com/morluto/rea | 2026-10-12 |
| [Simcenter Flux] | Siemens Simcenter Flux product page | https://www.siemens.com/en-us/products/simcenter/electromagnetics-simulation/flux/ | 2026-10-11 |
| [SolidCraft] | SolidCraft repository README | https://github.com/bherbruck/solvecraft | 2026-10-12 |
| [US 9,164,503] | Google Patents, US 9,164,503 B2 (The Boeing Company) | https://patents.google.com/patent/US9164503 | 2026-10-11 |
| [US12229885B1] | US 12,229,885 B1, Google Patents | https://patents.google.com/patent/US12229885 | 2026-10-11 |
| [Zoo Zookeeper] | Zoo, "Announcing Zookeeper, Our Conversational CAD Agent" | https://zoo.dev/blog/announcing-zookeeper | 2026-10-12 |
