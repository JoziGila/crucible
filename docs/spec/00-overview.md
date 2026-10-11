# Crucible — Platform Spec

## Summary

Crucible is one Rust platform where people and agents design, simulate, manufacture and release physical products from a single typed model. It unifies what today is split across five products: programmable features (Onshape), code as the model (Zoo), unbreakable implicit geometry (nTop), mixed mesh and exact geometry with synchronous editing (Siemens NX), and the design-to-CAM-to-PCB breadth of Fusion.

Three bets carry the design:

- **One language is the source of truth.** The visual editor, the code editor and agents all edit the same typed program. Every built-in feature, from extrude to toolpath to PCB router, is ordinary library code: Ingot orchestrating versioned Rust operations, with heavy algorithms in Wasm components anyone can publish.
- **Two universal types carry everything.** Body holds all geometry in any representation; Field holds all physics data. Mechanical, electronics, manufacturing and simulation compose through these two types, with no translation layers.
- **A design builds like software.** Every result is a deterministic, cached function of versioned inputs, stored in a design repository and checked by hardware CI on every commit.

The first market is engineers who design parts in code and for 3D printing. Breadth then grows as libraries, which agents can write and verify against test oracles. Crucible is a working name.

## State of the art

No product today combines programmability, robust geometry, simulation-driven design, breadth and an open core. Each leader wins one axis and is locked out of the others by a kernel or architecture chosen decades ago.

| Product | Kernel | Leads on | Falls short on |
| --- | --- | --- | --- |
| [Onshape](https://cad.onshape.com/FsDoc/index.html) | [Parasolid](https://forum.onshape.com/discussion/comment/94341/) | Built-in features are written in FeatureScript, the same language users get; query-based references | Closed licensed kernel; no implicit geometry |
| [Zoo Design Studio](https://zoo.dev/blog/zoo-design-studio-v1) | Own GPU engine | KCL code is the model, versioned in git; built-in design agent | Engine is [closed and cloud-hosted](https://zoo.dev/docs/faq); young feature set |
| [nTop](https://www.ntop.com/resources/blog/implicit-modeling-for-mechanical-design/) | Implicit fields | Booleans, offsets and rounds that never fail; fields drive geometry | [B-rep export is beta](https://docs.ntop.com/help-articles/knowledge-base/interop/how-to-export-geometry-as-a-cad-part-step-or-parasolid) and its surfaces are messy |
| [Siemens NX](https://blogs.sw.siemens.com/additive/siemensconvergentvision/) | [Parasolid](https://www.siemens.com/en-us/products/plm-components/parasolid/) | Depth: mesh and B-rep in one model, synchronous editing, CAM, molds, PLM | Desktop-era architecture; closed and costly |
| [Autodesk Fusion](https://www.autodesk.com/solutions/what-is-fusion-360) | [ShapeManager](https://www.autodesk.com/products/fusion-360/blog/?p=56002) | Breadth: CAD, CAM, CAE, PCB and data in one cloud product | Most new AI is [still roadmap](https://all3dp.com/6/autodesk-announces-the-ai-future-of-fusion-emphasis-on-future/); extensions are API add-ins |
| CATIA | [CGM](https://www.spatial.com/products/cgm) | High-end surfacing and aerospace and automotive programs | Closed, expensive, complex |
| [Rhino](https://docs.mcneel.com/rhino/8/help/en-us/commands/tonurbs.htm) | McNeel's own | Freeform NURBS and SubD surfaces; visual programming | SubD converts to NURBS only approximately |
| [Plasticity](https://www.plasticity.xyz/) | Parasolid + xNURBS | Fast direct modeling with G2 blends | Artist-focused; no engineering stack |
| [FreeCAD 1.0](https://blog.freecad.org/2024/11/19/freecad-version-1-0-released/) | OpenCascade | Open source; topological naming fix landed in 2024 | Fix is unfinished; inherits OpenCascade's Boolean and fillet failures |

The kernel layer is where the gap is widest. The last mainstream kernels date from 1988 (Parasolid) and 1989 (ACIS), and [Zoo](https://zoo.dev/blog/zoo-design-studio-v1) calls its engine the first new entry in over a decade. The open options are weak: [OpenCascade 8.0.1](https://github.com/Open-Cascade-SAS/OCCT/releases) is still fixing Boolean hangs, and the Rust kernel Fornjot [shut down in June 2026](https://www.fornjot.app/blog/shutting-down-fornjot/) after its author hit a wall on B-rep.

The incumbents are adding AI on top of feature trees stored in proprietary databases. Fusion's AutoTimeline [rebuilds editable history from dumb geometry](https://www.autodesk.com/products/fusion-360/blog/ai-powered-workflows-coming-to-autodesk-fusion/) after the fact. Crucible makes the editable program the model from the start.

## Design principles

Every layer obeys seven rules. Breaking one requires a written architecture decision record.

1. **No privileged code.** Built-in features use only the public mechanisms anyone can use: Ingot for features, Wasm components for heavy algorithms, and versioned Anvil and Flux operations underneath. If a user or agent cannot build a feature, neither can the core team.
2. **One model, three editors.** The visual editor, the code editor and agents edit the same typed program. Nothing exists only in the GUI.
3. **Two universal types.** Body carries geometry and Field carries physics data. Libraries consume and produce only these plus plain values.
4. **Determinism is a feature.** The same inputs and kernel version give identical outputs. Evaluation never depends on clocks, randomness or thread order; cross-platform results agree within the declared tolerance.
5. **The compiler checks physics.** Units, dimensions and tolerances are types, checked before anything runs. Conversions between geometry representations carry their error bounds.
6. **Every claim has an oracle.** No feature ships without a machine-checkable test that agents cannot edit.
7. **Open core, interop first.** The kernel, language and standard library are open source. STEP AP242, 3MF and FMI are first-class, so a design is never trapped.

## Architecture overview

People, agents and CI all change the design through one API, and the API changes only the Ingot model. The engines below evaluate that model; the source lives in the design repository, and every computed result lands in the shared content-addressed store.

[[DIAGRAM diagrams/00-overview-architecture.jsx: Crucible architecture · six layers]]

The core is the API, Ingot, the three engines and the stores. Everything in the dashed band is replaceable library code, written in the same language users and agents get.

## Design language and IR

Ingot is Crucible's design language: statically typed, pure and deterministic, with units and tolerances checked at compile time. Every design is Ingot source in text files, and every editor, human or agent, changes the design by changing that source.

```
use std::mech::{sketch, extrude, rib, fillet}

pub feature bracket(
    width: Length = 60mm,
    thickness: Length = 4mm ± 0.1mm,
    load: Force = 1.2kN,
) -> Part {
    let base = sketch(plane.xy) { rect(width, 40mm) } |> extrude(thickness)
    let web  = base.face(top).edge(longest) |> rib(height: 20mm, t: thickness)
    let part = (base + web) |> fillet(web.edges(joined), 2mm)
    part.material(alu_6061_t6)
        .require(peak_stress(part, load) < 0.6 * yield)
}
// width + load  →  compile error: cannot add Length and Force
```

**Types and units**

- Quantities carry dimensions in the type, as in [F# units of measure](https://learn.microsoft.com/en-us/dotnet/fsharp/language-reference/units-of-measure) and Rust's [uom](https://docs.rs/uom/latest/uom/): checked at compile time, erased at runtime.
- Derived dimensions are complete: area, volume, stress, density, heat flux. Zoo's KCL has [no area or volume units](https://zoo.dev/docs/kcl-lang/numeric), and FeatureScript [throws unit errors at runtime](https://cad.onshape.com/FsDoc/intro.html).
- A toleranced value (`4mm ± 0.1mm`) is its own type. GD&T controls attach to faces as typed properties, so stack-up analysis is a library function, not a separate tool.
- Values are immutable and functions are pure. The only effects are engine calls (build geometry, run a solve), and those are deterministic.

**References that survive edits**

- Every entity an operation creates gets a provenance ID: a hash of the operation, its input entities and the entity's role ("top cap of extrude 3").
- References are queries over provenance, re-resolved on every rebuild, following [Onshape's query model](https://cad.onshape.com/FsDoc/library.html). Positional selectors like CadQuery's [centre-of-mass rules](https://cadquery.readthedocs.io/en/latest/selectors.html) are not allowed.
- When a face splits or vanishes, resolution fails loudly with a suggested fix. It never silently picks a different face.

**Features, packages and source**

- A feature is a function from parameters to Bodies. Parameter metadata (ranges, UI hints) lets the visual editor generate each feature's dialog automatically.
- Packages carry semantic versions and a lockfile. A design pins its kernel and library versions so it rebuilds identically years later.
- A lossless syntax tree and a canonical formatter mean a GUI edit produces a minimal, reviewable diff and keeps comments intact.
- An LSP server gives completion, inline errors and hover previews of geometry in any code editor.

**The IR**

Ingot compiles to a typed dataflow graph. Each node is an engine operation keyed by the hash of its inputs, which is exactly what the incremental engine caches. Field expressions (lattices, gradings, implicit shapes) compile further to SIMD and GPU kernels, the approach [Fidget](https://github.com/mkeeter/fidget) uses for implicit surfaces.

## Geometry kernel

Anvil, the kernel, gives one Body type over four representations. Each operation runs in the representation where it is robust, and every conversion reports its error bound instead of hiding it.

| Representation | Used for | Robustness strategy | Converts to |
| --- | --- | --- | --- |
| Exact B-rep (NURBS and analytic surfaces) | Mating faces, machining, drawings, STEP exchange | Local per-entity tolerances, as [Parasolid has used since 1995](https://ftp1.cs.wisc.edu/pub/users/prem/jackson-SM-95.pdf); exact predicates for every topological decision | Mesh with a chordal error bound; implicit by distance evaluation |
| Implicit field | Lattices, shells, offsets, gradings, organic and optimized shapes | Min/max set operations that cannot fail; interval pruning as in [Fidget](https://github.com/mkeeter/fidget) | Mesh by dual contouring; B-rep by surface fitting (research grade, as nTop's is [still beta](https://docs.ntop.com/help-articles/knowledge-base/interop/how-to-export-geometry-as-a-cad-part-step-or-parasolid)) |
| Mesh | Scans, 3D printing, simulation meshes, STL and 3MF imports | Exact topology with inexact geometry and symbolic perturbation, the [Manifold](https://github.com/elalish/manifold/wiki/Manifold-Library) method | B-rep by feature recognition and region fitting; implicit by winding numbers |
| Subdivision surface | Concept and freeform shells | Authored as a control cage | B-rep with a stated deviation; Rhino notes [extraordinary vertices convert only approximately](https://docs.mcneel.com/rhino/8/help/en-us/commands/tonurbs.htm) |

**Mixed operations.** A Boolean between a B-rep and a mesh runs without converting either, as Parasolid's [convergent modeling](https://blogs.sw.siemens.com/additive/siemensconvergentvision/) does today. Siemens is [extending this to implicit geometry](https://www.cimdata.com/en/resources/complimentary-reports-research/commentaries/item/30193-siemens-plm-components-2026-commentary); Anvil starts with all four.

**Robustness rules**

- No global tolerance. Truck's Booleans take [one global tolerance](https://docs.rs/truck-shapeops/latest/truck_shapeops/fn.and.html), the pattern Parasolid abandoned three decades ago; Anvil stores tolerances per vertex and edge.
- Topological decisions use adaptive exact predicates ([Shewchuk](https://www.cs.cmu.edu/~quake/robust.html), via the Rust [robust](https://github.com/georust/robust) crate) and filtered interval arithmetic, as [CGAL](https://doc.cgal.org/latest/Kernel_23/index.html) does. Constructions stay in floating point.
- Surface-surface intersection runs as parallel sampling on the GPU with certified refinement on the CPU. Zoo [patented its sampling method](https://zoo.dev/research/zoo-cad-engine-overview), so this needs a freedom-to-operate review before design is fixed.
- Imported geometry passes through tolerant healing before any operation touches it.

**Naming in the kernel API.** Every operation returns history records: which output entities were created, modified, split or merged from which inputs. Ingot's reference resolver reads these directly. FreeCAD had to [retrofit naming on top of OpenCascade](https://github.com/realthunder/FreeCAD_assembly3/wiki/Topological-Naming-Algorithm), and its results still depend on the order OpenCascade reports split faces.

**Blends and surfacing**

- Fillets and blends are a research program, not a feature. Their topology [lacks a clean semantic foundation](https://www.cs.purdue.edu/cgvlab/www/resources/papers/Hoffmann-Workshop_on_App_Comp_geo-1996-How_SolidIs_Solid_Modeling.pdf), and even Rhino 9's new corner blends [still fail at large radii](https://discourse.mcneel.com/t/rhino-beta-feature-filletedge-and-blendedge-corners/213727).
- The order: constant-radius rolling-ball, then variable radius, then vertex blends with setbacks. Where a B-rep blend fails, an implicit blend is offered with its deviation shown.
- Class-A work needs G2 and G3 continuity, because [tangency alone breaks highlights](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-9DD73E22-A5EF-4952-BB84-2CEE2109993C.htm). Curvature combs, zebra stripes and highlight lines are built in.

**Starting point.** Anvil is a new kernel, written to learn from Fornjot, which [shut down after hitting a B-rep cliff](https://www.fornjot.app/blog/shutting-down-fornjot/). It may reuse Apache-licensed pieces of [Truck](https://github.com/ricosjp/truck) for NURBS evaluation and adopt Manifold's mesh algorithm, but owns its topology, tolerances and naming from the first commit.

## Physics and fields

Physics in Crucible is stated, not configured. A problem is a weak form plus boundary conditions over Fields, written in Ingot, compiled to CPU and GPU kernels, and differentiable end to end.

**The Field type.** `Field<Domain, Value>` is a scalar, vector or tensor quantity over a Body or region. Materials, loads, temperatures, fiber directions and every solver result are Fields. Geometry operations read Fields too, so a stress result can grade a lattice's density directly, as nTop's [field-driven design](https://www.ntop.com/resources/blog/implicit-modeling-for-mechanical-design/) does.

**Weak forms as the physics API.** The model is FEniCS's [UFL](https://docs.fenicsproject.org/ufl/main/), compiled to kernels the way [FFCx](https://github.com/FEniCS/ffcx) compiles UFL to C. Rust has no equivalent today; the only Rust FEM crate found, fenris, is [not recommended for general use](https://github.com/InteractiveComputerGraphics/fenris). This is the largest engineering risk in the physics stack and its biggest differentiator.

```
let u = trial(Displacement, part)
let v = test(u)
let elasticity = inner(sigma(u, alu_6061_t6), eps(v)) * dx(part)
              == dot(traction, v) * ds(part.face(load_face))
let result = solve(elasticity, fixed: part.faces(bolt_holes))
result.von_mises  // Field<Part, Stress>
```

**Analysis without a meshing step.** Most users should never see a mesh.

- Isogeometric analysis runs directly on B-rep NURBS. LS-DYNA already does this for [industrial shell models](https://www.dynamore.de/en/training/seminars/iga/isogeometric-analysis-in-ls-dyna), and Coreform claims it [removes meshing and defeaturing](https://coreform.com/products/coreform-iga/).
- Immersed methods run on implicit and mesh Bodies. Intact Solutions simulates [implicit, B-rep, mesh and CT data with no meshing](https://intact-solutions.com/).
- Classic high-order FEM stays available, with matrix-free partial assembly because [GPU FEM is memory-bound](https://mfem.org/gpu-support/).

| Physics | Method | Learn from or wrap | Phase |
| --- | --- | --- | --- |
| Structural, linear and nonlinear | FEM, IGA | [MFEM](https://mfem.org/features/), [deal.II](https://www.dealii.org/) | 1 |
| Thermal | FEM | [DOLFINx](https://docs.fenicsproject.org/dolfinx/main/python/demos/demo_poisson.html) | 1 |
| Multibody dynamics | Wrap | [Project Chrono](https://projectchrono.org/) (BSD-3), [MuJoCo](https://github.com/google-deepmind/mujoco) (Apache-2.0), [Rapier](https://rapier.rs/) for interactive rigid bodies | 2 |
| Fluids, conjugate heat | FVM | [Simcenter FLOEFD](https://www.siemens.com/en-us/products/simcenter/fluids-thermal-simulation/floefd/) as the workflow benchmark | 3 |
| System level | FMI 3.0 co-simulation, Modelica via FMUs | [FMI 3.0.2](https://fmi-standard.org/docs/3.0.2/), [SSP 2.0.1](https://ssp-standard.org/) | 3 |
| Electromagnetics, optics | FDTD | [openEMS](https://www.openems.de/), [Meep](https://meep.readthedocs.io/en/latest/) | 4 |
| Acoustics | FEM | [Elmer](https://github.com/ElmerCSC/elmerfem) | 4 |

Meep and Elmer are GPL, so they serve as references and external tools, never linked into the open core.

**Numerics stack.** CPU linear algebra uses [faer](https://docs.rs/faer/latest/faer/), pure Rust under MIT with dense and sparse factorizations. GPU kernels target [wgpu](https://github.com/gfx-rs/wgpu) and [CubeCL](https://github.com/tracel-ai/cubecl), which calls itself alpha, so versions are pinned behind an internal backend trait. An optional bridge to PETSc covers HPC clusters.

**Gradients everywhere.** Algorithmic differentiation lives at the form level, as [pyadjoint](https://www.dolfin-adjoint.org/en/latest/) does for FEniCS. Any objective gets gradients with respect to any Ingot parameter, which powers topology optimization, shape optimization and inverse design. It is built in from day one: MuJoCo's most complete GPU variant [ships without differentiation](https://mujoco.readthedocs.io/en/latest/mjx.html), which shows how hard retrofitting is.

**Two fidelity modes.** Interactive mode gives instant, coarse GPU results while the user edits. Sign-off mode runs converged solves. Ansys Discovery's live solver publishes [no accuracy figures](https://ansys.synopsys.com/products/3d-design/ansys-discovery); Crucible labels interactive results as approximate and always shows an error estimate.

## Incremental engine and design repository

A Crucible design builds like software. Only what changed recomputes, results are shared across the team by content hash, and branches, releases and BOMs are native to the repository instead of living in a separate PLM database.

**Incremental engine**

- In-process evaluation follows [Salsa](https://salsa-rs.github.io/salsa/overview.html) (0.28, the engine under rust-analyzer): memoized functions over tracked inputs, with [durability levels and fixpoint cycle handling](https://github.com/salsa-rs/salsa/releases).
- Backdating: when a recomputed operation produces the same output hash as before, nothing downstream reruns.
- Every operation's cache key is the hash of the operation, its input hashes, the kernel version and the library lockfile. Outputs live in a SHA-256 content-addressed store, like [Bazel's remote cache](https://bazel.build/remote/caching), shared by the team and CI.
- Cache hits depend on reproducible builds. Bazel loses hits to leaked environment variables; Crucible's evaluation sandbox exposes none.
- Independent branches of the graph evaluate in parallel. An edit cancels in-flight work that depends on it.
- Results stream coarse-first: a rough tessellation or an interactive solve reaches the screen before the exact result.

**What lives where**

| Artifact | Stored as | Rebuilt from |
| --- | --- | --- |
| Ingot source and parameters | Text files in the repository | Never; this is the design |
| Lockfile with kernel and library versions | Text in the repository | Never |
| Geometry, meshes, Fields, solver results | Objects in the content-addressed store | Source plus lockfile |
| Version history | Immutable chain of deltas | Never |
| Releases | Signed tags on a version | Never |
| BOM, drawings, exports | Derived views | Source plus lockfile |

**History, branches and collaboration**

- Every edit, including one made in the visual editor, is a fine-grained immutable change pointing at its parent, as in [Onshape's microversions](https://www.onshape.com/en/blog/under-the-hood-how-collaboration-works). Named versions group them.
- Branches are cheap pointers, not copies. Merges are semantic at the feature level, as in [Onshape's branch and merge](https://www.onshape.com/en/features/branch-merge-cad), backed by a structural merge of Ingot source and a geometry overlay of the result.
- Several people and agents can edit one branch live through a CRDT over the syntax tree. [Loro](https://github.com/loro-dev/loro) (1.16, with a movable tree and time travel) is the leading candidate.

**Releases, change orders and BOMs**

- A release is a signed tag that pins an immutable version. States follow [Onshape's release flow](https://cad.onshape.com/help/Content/Release/release_management.htm): in progress, pending, then released, rejected or obsolete. Releasing never blocks editing.
- A change order is a pull request: affected items, approvers and the hardware CI report. As in [Fusion Manage](https://help.autodesk.com/cloudhelp/ENU/Fusion-Manage/files/MNG-COS-OVERVIEW.htm), an item can sit in only one open change order at a time.
- The BOM is a query over the assembly graph. Engineering, manufacturing and service BOMs are [three views of one product structure](https://www.autodesk.com/products/fusion-360/blog/bom-management-autodesk-fusion/); the manufacturing view adds process and routing from the manufacturing library.

**Hardware CI.** Every commit rebuilds the design, evaluates every `require` check in the model, reruns regression simulations and manufacturability checks, recomputes mass and cost, and attaches a visual diff to the proposal. A red check blocks the merge.

## Domain libraries

Every domain is an Ingot package on top of Body and Field, with optional native kernels compiled to Wasm. Each library ships with its own oracles (see Verification) and can be replaced or forked by anyone.

| Library | Covers | Benchmark to beat | Phase |
| --- | --- | --- | --- |
| Mechanical | Sketches with a constraint solver, parts, assemblies, mates, kinematics, patterns, configurations | Onshape, NX | 1 |
| Additive | Lattices, gradings, conformal channels, slicing to [3MF with the Toolpath extension](https://3mf.io/spec/) | nTop; [PrusaSlicer](https://blog.prusa3d.com/prusaslicer-2-9-whats-new_107659/) and [OrcaSlicer](https://github.com/SoftFever/OrcaSlicer) (AGPL, reference only) | 1 |
| Documentation | Drawings, model-based definition, GD&T, STEP AP242 with PMI, [QIF](https://qifstandards.org/) inspection plans | NX model-based definition | 2 |
| Sheet metal and weldments | Flanges, bends, flat patterns; structural members from profile libraries, corner treatments, [cut lists with lengths and mass](https://www.javelin-tech.com/blog/2024/05/solidworks-weldments/) | SOLIDWORKS | 2 |
| CAM | 2.5- to 5-axis milling and turning; toolpaths as functions of geometry, machine and tool; recognized features proposed as editable operations | Fusion; [CloudNC CAM Assist](https://www.cloudnc.com/blog/what-to-see-at-imts-2026-ai-assisted-cnc-programming-and-where-to-find-cloudnc); [OpenCAMLib](https://github.com/aewallin/opencamlib) (LGPL) | 2 |
| Components and cost | A registry of real parts with geometry, specs and supplier data; live cost estimates | McMaster-Carr, Octopart | 2 |
| Electronics | Schematics and PCBs where the board is a Body with nets; routing, DRC, ECAD-MCAD exchange via [IDX V6](https://www.prostep.org/en/projects/ecad/mcad-collaboration-implementor-forum) | [KiCad 10](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/), [Fusion Electronics](https://www.autodesk.com/products/fusion-360/blog/eagle-to-autodesk-fusion-transition/), [Altium CoDesigner](https://altium.com/mcadplugins) | 3 |
| Surfacing | NURBS and SubD freeform, G2 and G3 continuity analysis | Alias, Rhino, Plasticity | 3 |
| Molding | Draft and undercut analysis, parting lines, fill, pack, cool and warp simulation | [Moldflow](https://www.autodesk.com/products/moldflow/overview) | 3 |
| Cables and harnesses | Routed flexible Bodies, bend-radius and clash checks, cut lengths | [Zuken E3 3D routing](https://www.zuken.com/en/product/e3series/ecad-mcad), [Siemens Capital](https://www.siemens.com/en-us/products/capital/ee-systems-electrical/wiring-harness-design-engineering/) | 3 |
| Composites | Ply layups and drape, with fiber direction as a Field | STEP AP242 composites | 4 |

**Why electronics belongs in the core model.** Fusion keeps board and enclosure in [associative sync](https://www.autodesk.com/products/fusion-360/blog/eagle-to-autodesk-fusion-transition/); Altium syncs through a [proprietary push and pull](https://altium.com/mcadplugins). In Crucible there is nothing to sync: the board is a Body in the same assembly, and its heat output is a Field the thermal solver reads.

**Catalogs are plugins, not core.** Supplier data is gated: McMaster-Carr's API is for [approved customers only](https://www.mcmaster.com/help/api/), Nexar's free tier covers [100 matched parts](https://nexar.com/api), and Xometry offers [no public quote API](https://www.xometry.com/get-started/). The registry holds open part definitions; supplier adapters are optional plugins.

## Agent-first interfaces and UI

Agents get every capability the UI has, through typed and validated engine operations rather than scripts or clicks. The UI is where humans see and steer, and it is a client of the same API, never a privileged one.

**Where agents stand today.** Fusion's local MCP server mostly [runs Python inside a live session](https://www.autodesk.com/products/fusion-360/blog/?p=87994); its cloud Data MCP [manages files, not geometry](https://www.autodesk.com/products/fusion-360/blog/introducing-the-autodesk-fusion-data-mcp-server/). Onshape's MCP server [writes FeatureScript features](https://www.onshape.com/en/blog/featurescript-mcp-server-enables-text-code-cad), and Zoo's Zookeeper [edits KCL and snapshots its own work](https://zoo.dev/blog/announcing-zookeeper) to check it. NX Design Copilot is a [question-and-answer assistant](https://news.siemens.com/de-ch/siemens-designcenter-nx-summer-2025/).

**The agent API.** One API, exposed over MCP and as a native SDK.

| Group | Operations | Returns |
| --- | --- | --- |
| Read | Query geometry, measure, list features, explain an entity's provenance | Typed values with units |
| Edit | Add or change a feature, set a parameter, refactor Ingot source | A compiled diff, rejected before it lands if it fails to type-check |
| Evaluate | Build, simulate at a chosen fidelity, run checks, estimate cost | Results, error estimates, failed checks |
| Inspect | Render views and sections, paint Fields onto geometry | Images for vision models plus the data behind them |
| Compare | Diff two versions semantically | Feature changes, geometry delta, metric deltas |
| Propose | Open a proposal on a branch with a rationale | A reviewable proposal with its CI report |

- Every agent action is a transaction on a branch. Agents never write to a protected branch; people or policies merge.
- Errors are typed and carry suggested fixes, so agents correct themselves instead of guessing.
- Each agent runs with scoped permissions: read-only, edit a branch, or run expensive solves under a cost cap.
- Before proposing, an agent must build, pass every `require` check and attach rendered snapshots.

**Data for design models.** Licensing limits the public datasets. The [ABC dataset](https://deep-geometry.github.io/abc-dataset/)'s 1M models remain their creators' copyright, and the [Fusion 360 Gallery](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/LICENSE.md) is non-commercial only. Crucible generates procedural training data, as [CAD-Recode](https://arxiv.org/abs/2412.14042v2) did with 1M sequences, and measures agents on [Text2CAD-Bench](https://arxiv.org/abs/2605.18430) and [CADPrompt](https://arxiv.org/abs/2410.05340v1). Text2CAD-Bench finds today's models degrade sharply on complex topology and freeform surfaces.

**The UI**

- One Rust core runs natively and in the browser via Wasm, rendering through [wgpu](https://github.com/gfx-rs/wgpu). WebGPU ships in Chrome, Safari 26 and Firefox on Windows and macOS, but [Linux browsers still lag](https://github.com/gpuweb/gpuweb/wiki/Implementation-Status), so a WebGL2 fallback stays.
- Like [Onshape](https://cad.onshape.com/help/Content/Home/hardware_and_graphics_performance_recommendations.htm), the engine (local or cloud) ships only changed triangles; orbit, selection and sectioning run locally on the GPU.
- Direct manipulation writes code. Dragging a face edits a parameter in the source, and each feature's dialog is generated from its parameter metadata.
- Fields paint straight onto geometry: stress, temperature, draft angle, or the deviation a conversion introduced.
- Reviewing a proposal shows a feature-list diff, a geometry overlay with a slider in the style of [Onshape Compare](https://cad.onshape.com/help/Content/Document/compare.htm), metric deltas and the source diff, with accept or reject per change.
- Widgets are context-sensitive and uncluttered, as in [Plasticity](https://cgchannel.com/2026/04/plasticity-2026-1-is-out/), keyboard-first, with pen and touch support.

## Interoperability and extensibility

Crucible reads and writes the open standards natively, so no design is ever trapped, and it is extended in three tiers that all keep evaluation deterministic.

| Standard | Version | What Crucible uses it for | Direction |
| --- | --- | --- | --- |
| [STEP AP242](https://www.iso.org/standard/84300.html) | ISO 10303-242:2025, edition 4 | Exact geometry, assemblies, GD&T and PMI, kinematics, composites, harnesses | Read and write |
| [3MF](https://3mf.io/spec/) | ISO/IEC 25422:2025, core 1.4.0 | Additive parts: meshes, beam lattices, materials, toolpaths | Read and write |
| [IDX](https://www.prostep.org/en/projects/ecad/mcad-collaboration-implementor-forum) | V6.0, December 2025 | Incremental ECAD-MCAD exchange with other tools | Read and write |
| [FMI](https://fmi-standard.org/docs/3.0.2/) | 3.0.2 | Co-simulation units for system models | Import and export |
| [SSP](https://ssp-standard.org/) | 2.0.1 | Whole systems of FMUs with parameters | Import and export |
| [QIF](https://qifstandards.org/) | 3.0 | Inspection plans out, measurement results back in | Write plans, read results |
| [glTF](https://www.khronos.org/gltf/) | 2.0 | Web, AR and marketing visuals | Export |
| STL, OBJ | Legacy | Old mesh workflows | Read and write |

Proprietary native formats (Parasolid, CATIA, NX) come through licensed translators as optional plugins, never in the open core.

**STEP is a core project.** The Rust STEP ecosystem cannot carry production work: ruststep is [marked experimental](https://github.com/ricosjp/ruststep) and cannot serialize, and truck-stepio [writes but cannot read](https://docs.rs/truck-stepio/latest/truck_stepio/). Crucible generates its AP242 reader and writer from the EXPRESS schemas and tests them against files from the major CAD systems.

**Three extension tiers**

1. **Ingot packages.** Features, checks, workflows and most domain logic. This tier covers the vast majority of extensions and needs no native code.
2. **Wasm components.** Native-speed kernels such as solvers, importers and CAM strategies, built on the WebAssembly Component Model. [WASI 0.3](https://wasi.dev/releases/wasi-p3) shipped in June 2026 with native async and streams, and Wasmtime 46 was its first implementation.
3. **Engine backends.** In-tree Rust crates behind traits, such as GPU backends and linear solvers, reviewed as core contributions.

**Sandboxing keeps determinism.** A component gets only the capabilities it is granted. Components that run during evaluation are never granted clocks, randomness, files or network, so they cannot break caching. WASI has [no 1.0 date](https://wasi.dev/roadmap) and Wasmtime ships [frequent security fixes](https://github.com/bytecodealliance/wasmtime/releases), so the runtime is pinned and patched on a fixed cadence. Published packages and components are signed.

## Engineering standards in Rust

Crucible is one Cargo workspace of small crates with a strict dependency direction, `unsafe` confined to a few audited crates, and a test suite anchored by invariants, fuzzing and deterministic simulation.

**Workspace layout**

```
crucible/
  core/
    ingot-syntax     lossless parser, formatter
    ingot-types      type checker, units, tolerances
    ingot-ir         dataflow IR and lowering
    kiln             incremental engine, scheduler
    cas              content-addressed store, remote cache
    anvil-geom       curves, surfaces, NURBS evaluation
    anvil-topo       B-rep topology, tolerances, history records
    anvil-ops        Booleans, blends, offsets, healing
    anvil-implicit   field expressions, interval pruning, JIT
    anvil-mesh       manifold mesh operations, tessellation
    flux-forms       weak-form compiler, differentiation
    flux-solve       discretizations, solvers, GPU backends
    repo             versions, branches, merge, releases
    api              the one API for agents and the UI, MCP server
  io/       step-ap242  3mf  idx  fmi  gltf
  std/      Ingot packages: mech  additive  docs  sheet  cam  electronics
  apps/     desktop  web  cli  ci-runner
  oracles/  golden-products  nafems  mms  step-corpus
```

Dependencies only point down: `core` never depends on `std` or `apps`, the kernel never depends on the solvers, and apps talk only to `api`.

**Code rules**

- `#![forbid(unsafe_code)]` everywhere except SIMD, GPU and FFI crates. Every `unsafe` block carries a safety comment, runs under Miri in CI and has a fuzz target.
- Edition 2024, rustfmt and Clippy pedantic as merge gates; `cargo-semver-checks` on every public crate.
- `cargo-deny` enforces licenses: no GPL or AGPL code links into the core.

**Testing strategy**

- **Invariants.** Property tests check every geometric operation: watertight output, the Euler-Poincaré formula, and volume identities such as V(A∪B) = V(A) + V(B) − V(A∩B).
- **Fuzzing.** Random solids feed the Boolean and blend code; random bytes feed the Ingot and STEP parsers.
- **Differential tests.** Results are compared against OpenCascade on generated models and on corpora whose licenses allow it.
- **Determinism.** CI evaluates every golden product twice, with different thread counts, and fails on any hash difference.
- **Deterministic simulation.** Sync, collaboration and the remote cache run inside a simulator that owns time, network and disk, injecting crashes and partitions from a replayable seed.
- **Benchmarks.** Performance regressions beyond 5% block merges.

**Performance budgets (targets, on a reference laptop fixed in phase 0)**

| Interaction | Budget |
| --- | --- |
| Orbit and zoom on a 5M-triangle assembly | 60 fps minimum |
| Selection highlight | Under 16 ms |
| Coarse preview while dragging a parameter | Under 100 ms |
| Exact rebuild of a 200-feature part after an early edit | Under 2 s |
| Interactive simulation update with error estimate | Under 1 s |
| Opening a 1,000-part assembly from a warm remote cache | Under 10 s |

## Verification, validation and golden products

Every feature is done only when a machine-checkable oracle says so, and the oracles live outside the agents' write access. Verification proves the software solves its equations correctly; validation against physical test data proves the equations fit reality.

**Oracles per layer**

| Layer | Oracle |
| --- | --- |
| Language | Negative tests: unit and tolerance errors must fail to compile; type-checker conformance suite |
| Kernel | Watertight output, Euler-Poincaré, volume identities; Boolean success rate on a fixed corpus; differential runs against OpenCascade |
| Physics | [Method of manufactured solutions](https://www.osti.gov/biblio/759450) at the expected convergence order; [NAFEMS benchmarks](https://www.nafems.org/publications/code-verification/); conservation of mass and energy |
| Interop | STEP AP242 and 3MF round trips preserve geometry and PMI within tolerance, using files from the major CAD systems |
| Engine | Two evaluations give identical hashes; a cached result always equals a fresh one |
| Agents | [Text2CAD-Bench](https://arxiv.org/abs/2605.18430), [CADPrompt](https://arxiv.org/abs/2410.05340v1) and a held-out internal task set |

**Rules that keep oracles honest**

- Oracles and held-out models sit in a protected directory that agents can read but never write. Held-out models are never shown to agents at all.
- Loosening any tolerance needs a human approval with a written reason.
- A feature without an oracle cannot merge, however good it looks.

**Validation against reality**

- Each solver declares its validity envelope, such as linear elasticity at small strains or incompressible flow below about Mach 0.3. Outside it, results are flagged and never shown as confident.
- Physical test results come back in as Fields attached to the exact version tested, for example through [QIF](https://qifstandards.org/) measurement files. Crucible reports the deviation between simulation and test.
- The vocabulary and process follow [ASME V&V 10](https://www.asme.org/codes-standards/find-codes-standards/standard-for-verification-and-validation-in-computational-solid-mechanics) for solid mechanics and [V&V 20](https://sandia.gov/research/publications/details/overview-of-asme-vv-20-2009-standard-for-verification-and-validation-in-com-2010-03-01) for quantifying accuracy against experiments.

**Golden products.** Milestones are reference products, not feature lists. Each has a reference design with expected mass, stresses, frequencies and outputs, and a milestone closes when its product passes every check.

| # | Golden product | What it proves | Phase |
| --- | --- | --- | --- |
| 1 | Machined bracket | Sketch, extrude, fillet, linear static FEA, drawing with GD&T, 3-axis CAM, STEP round trip | 1 |
| 2 | Topology-optimized lattice bracket | Fields drive geometry, adjoint gradients, implicit-to-mesh conversion, printable 3MF | 1 |
| 3 | Gearbox | Assemblies, mates, kinematics, contact, multibody dynamics | 2 |
| 4 | Welded frame with sheet-metal guards | Weldments, cut lists, flat patterns, bend allowances | 2 |
| 5 | Molded enclosure with its PCB | Shells, draft, ribs, the board as a Body, board heat as a Field in the thermal solve | 3 |
| 6 | Drone | Fluids for the propellers, structure, battery thermal, flight controller co-simulation over FMI, harness routing | 3 to 4 |

## Roadmap

Crucible enters through engineers who design in code and for 3D printing, then widens one golden product at a time. Code-CAD tools such as CadQuery and build123d sit on OpenCascade and inherit its failures, and additive engineers need Fields and lattices that B-rep tools handle badly; both groups value the language and the kernel most.

[[DIAGRAM diagrams/00-overview-roadmap.jsx: Roadmap · five phases, gated by golden products]]

Phases close on oracles, not dates; durations depend on team size and stay open until phase 0 ends. From phase 2 on, most new breadth is library code, which agents can build in parallel against each library's oracles.

## Scope, risks and open questions

Crucible covers products made of parts, assemblies, boards and cables, from a bracket to a drone. Buildings (BIM and IFC), chip layout and film animation are out of scope: each is a separate world with its own standards.

**Hardest risks**

| Risk | Why it is hard | Mitigation |
| --- | --- | --- |
| B-rep Booleans and blends | Fornjot [shut down on this cliff](https://www.fornjot.app/blog/shutting-down-fornjot/); OpenCascade 8.0.1 is [still fixing Boolean hangs](https://github.com/Open-Cascade-SAS/OCCT/releases) | Tight scope per phase; implicit and mesh fallbacks with stated deviation; Boolean success rate as a tracked metric |
| Weak-form compiler in Rust | No Rust equivalent of UFL and FFCx exists; GPU FEM is memory-bound | Start with structural and thermal; matrix-free kernels; optional PETSc bridge |
| Determinism across platforms | Floating-point results differ across CPUs and GPUs | Identical results per platform class; cross-platform agreement within tolerance; cache keys include the platform class |
| Patents | Zoo's surface-intersection sampling method has an [allowed patent](https://zoo.dev/research/zoo-cad-engine-overview) | Freedom-to-operate review before the intersection design is fixed |
| STEP fidelity | No production-grade Rust STEP library; real-world files vary widely | A dedicated interop team testing against files from the major CAD systems |
| Breadth versus incumbents | Fusion's and NX's integrated workflows are the moat | A narrow wedge market first; clean interop; breadth through libraries |
| Agent quality | Models [degrade on complex topology and freeform surfaces](https://arxiv.org/abs/2605.18430) | Typed operations, mandatory self-checks, branch-only edits, human review |
| Training data | ABC models stay [their creators' copyright](https://deep-geometry.github.io/abc-dataset/); Fusion 360 Gallery is [non-commercial](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/LICENSE.md) | Procedurally generated data |
| GPU stack churn | CubeCL calls itself alpha; WebGPU lags on Linux browsers | Backends behind a trait, pinned versions, WebGL2 fallback |

**Open questions**

- [ ] Core license: Apache-2.0 or MPL-2.0, and what the business sells (hosted compute, enterprise features, support)
- [ ] Build Ingot from scratch, or start from Zoo's MIT-licensed [KCL library](https://lib.rs/crates/kcl-lib) and add static units
- [ ] Local-first or cloud-first default for evaluation
- [ ] Which reference laptop the performance budgets are measured on
- [ ] First wedge: code-CAD users or 3D-printing engineers
- [ ] Trademark checks for Crucible, Ingot, Anvil, Kiln and Flux, which are working names

## Sources

Pages opened while researching this spec, checked October 2026.

**Kernels and geometry**

- [Parasolid](https://www.siemens.com/en-us/products/plm-components/parasolid/) · [Siemens PLM Components 2026 commentary](https://www.cimdata.com/en/resources/complimentary-reports-research/commentaries/item/30193-siemens-plm-components-2026-commentary) · [Jackson, tolerant modeling (1995)](https://ftp1.cs.wisc.edu/pub/users/prem/jackson-SM-95.pdf)
- [ACIS](https://www.spatial.com/products/3d-acis-modeling) · [CGM](https://www.spatial.com/products/cgm) · [ShapeManager in Fusion](https://www.autodesk.com/products/fusion-360/blog/?p=56002)
- [OpenCascade releases](https://github.com/Open-Cascade-SAS/OCCT/releases) · [OpenCascade Boolean specification](https://occt3d.com/dev/doc/overview/html/specification__boolean_operations.html)
- [Truck](https://github.com/ricosjp/truck) · [Fornjot shutdown](https://www.fornjot.app/blog/shutting-down-fornjot/) · [Fidget](https://github.com/mkeeter/fidget) · [Manifold](https://github.com/elalish/manifold/wiki/Manifold-Library)
- [Zoo Design Studio v1](https://zoo.dev/blog/zoo-design-studio-v1) · [Zoo engine overview](https://zoo.dev/research/zoo-cad-engine-overview) · [Zoo FAQ](https://zoo.dev/docs/faq)
- [nTop implicit modeling](https://www.ntop.com/resources/blog/implicit-modeling-for-mechanical-design/) · [nTop B-rep export](https://docs.ntop.com/help-articles/knowledge-base/interop/how-to-export-geometry-as-a-cad-part-step-or-parasolid)
- [Shewchuk robust predicates](https://www.cs.cmu.edu/~quake/robust.html) · [CGAL kernels](https://doc.cgal.org/latest/Kernel_23/index.html) · [Hoffmann, How solid is solid modeling](https://www.cs.purdue.edu/cgvlab/www/resources/papers/Hoffmann-Workshop_on_App_Comp_geo-1996-How_SolidIs_Solid_Modeling.pdf)
- [FreeCAD 1.0](https://blog.freecad.org/2024/11/19/freecad-version-1-0-released/) · [FreeCAD naming algorithm](https://github.com/realthunder/FreeCAD_assembly3/wiki/Topological-Naming-Algorithm) · [Rhino SubD to NURBS](https://docs.mcneel.com/rhino/8/help/en-us/commands/tonurbs.htm) · [Plasticity](https://www.plasticity.xyz/)

**Language, engine and repository**

- [FeatureScript](https://cad.onshape.com/FsDoc/intro.html) · [KCL numeric types](https://zoo.dev/docs/kcl-lang/numeric) · [CadQuery selectors](https://cadquery.readthedocs.io/en/latest/selectors.html) · [F# units of measure](https://learn.microsoft.com/en-us/dotnet/fsharp/language-reference/units-of-measure) · [uom](https://docs.rs/uom/latest/uom/)
- [Salsa](https://salsa-rs.github.io/salsa/overview.html) · [Bazel remote caching](https://bazel.build/remote/caching) · [Loro](https://github.com/loro-dev/loro)
- [Onshape collaboration internals](https://www.onshape.com/en/blog/under-the-hood-how-collaboration-works) · [Onshape branch and merge](https://www.onshape.com/en/features/branch-merge-cad) · [Onshape release management](https://cad.onshape.com/help/Content/Release/release_management.htm) · [Fusion Manage change orders](https://help.autodesk.com/cloudhelp/ENU/Fusion-Manage/files/MNG-COS-OVERVIEW.htm)
- [WASI 0.3](https://wasi.dev/releases/wasi-p3) · [WASI roadmap](https://wasi.dev/roadmap) · [wgpu](https://github.com/gfx-rs/wgpu) · [WebGPU implementation status](https://github.com/gpuweb/gpuweb/wiki/Implementation-Status)

**Simulation**

- [UFL](https://docs.fenicsproject.org/ufl/main/) · [FFCx](https://github.com/FEniCS/ffcx) · [MFEM GPU support](https://mfem.org/gpu-support/) · [deal.II](https://www.dealii.org/) · [faer](https://docs.rs/faer/latest/faer/) · [CubeCL](https://github.com/tracel-ai/cubecl)
- [LS-DYNA IGA](https://www.dynamore.de/en/training/seminars/iga/isogeometric-analysis-in-ls-dyna) · [Coreform IGA](https://coreform.com/products/coreform-iga/) · [Intact Solutions](https://intact-solutions.com/) · [pyadjoint](https://www.dolfin-adjoint.org/en/latest/)
- [FMI 3.0.2](https://fmi-standard.org/docs/3.0.2/) · [SSP](https://ssp-standard.org/) · [Project Chrono](https://projectchrono.org/) · [MuJoCo MJX](https://mujoco.readthedocs.io/en/latest/mjx.html)
- [Method of manufactured solutions (Sandia)](https://www.osti.gov/biblio/759450) · [NAFEMS code verification](https://www.nafems.org/publications/code-verification/) · [ASME V&V 10](https://www.asme.org/codes-standards/find-codes-standards/standard-for-verification-and-validation-in-computational-solid-mechanics)

**Agents, UI and domains**

- [Zookeeper](https://zoo.dev/blog/announcing-zookeeper) · [Fusion MCP](https://www.autodesk.com/products/fusion-360/blog/?p=87994) · [Fusion AU 2026 AI features](https://www.autodesk.com/products/fusion-360/blog/ai-powered-workflows-coming-to-autodesk-fusion/) · [Onshape FeatureScript MCP](https://www.onshape.com/en/blog/featurescript-mcp-server-enables-text-code-cad)
- [Text2CAD-Bench](https://arxiv.org/abs/2605.18430) · [CAD-Recode](https://arxiv.org/abs/2412.14042v2) · [ABC dataset](https://deep-geometry.github.io/abc-dataset/) · [Fusion 360 Gallery license](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/LICENSE.md)
- [Onshape graphics architecture](https://cad.onshape.com/help/Content/Home/hardware_and_graphics_performance_recommendations.htm) · [Onshape Compare](https://cad.onshape.com/help/Content/Document/compare.htm)
- [KiCad 10](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/) · [IDX implementor forum](https://www.prostep.org/en/projects/ecad/mcad-collaboration-implementor-forum) · [CloudNC](https://www.cloudnc.com/blog/what-to-see-at-imts-2026-ai-assisted-cnc-programming-and-where-to-find-cloudnc) · [Zuken E3 routing](https://www.zuken.com/en/product/e3series/ecad-mcad)
- [STEP AP242 edition 4](https://www.iso.org/standard/84300.html) · [3MF](https://3mf.io/spec/) · [QIF](https://qifstandards.org/) · [Nexar API](https://nexar.com/api) · [McMaster-Carr API](https://www.mcmaster.com/help/api/)
