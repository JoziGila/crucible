# Mechanical design (MEC)

`std::mech` is Crucible's mechanical design library, written in its design language Ingot, and it covers everything from a sketch to a released drawing. Over incumbent design tools and their AI-built clones, an engineer gains this: fits, stack-ups and design rules are checks on every merge, so a change that breaks one never reaches the main branch. One mechanism delivers it: every domain shares one constraint solver, one way of naming faces by how they were made, and one tolerancing model, so drawings, stack-ups and inspection read the same tolerances.

## Designing a part

This section follows one part from source to a released Item, so the model a designer meets is clear before the details that later sections specify.

### A housing in ten lines

The housing below is a machined part like GP1, the golden product whose made and measured brackets close phase 1. It has a block, a pocket, four tapped holes and rounded corners.

```
pub feature housing(depth: Length = 30mm) -> Part {
    let block  = sketch(plane.xy) { rect(90mm, 60mm, center: origin) } |> extrude(depth)
    let top    = block.face(role: end_cap)
    let pocket = sketch(top) { rect(64mm, 34mm, center: origin) }
                 |> extrude(Blind(depth - 4mm), dir: -normal)
    let body   = (block - pocket)
                 |> hole(at: top.corners(inset: 7mm),
                         spec: HoleSpec::tapped(ThreadSpec::iso_metric("M5x0.8"), depth: 10mm))
                 |> fillet(block.edges(role: lateral(any)), 5mm)
    part(body, name: "Housing", item: "HSG-0100").material(alu_6061_t6)
}
```

Read it top to bottom. `extrude` turns a sketched rectangle into a block and returns a new body; the pocket is a second body, and the minus sign is the Boolean that removes it. Features that dress existing geometry, such as `hole` and `fillet`, take a body and return it changed.

Nothing is picked by position. `top` is the face the extrusion made at its far end, the face with role `end_cap`. `top.corners(inset: 7mm)` places a point 7 mm from both edges at each convex corner of that face's outer boundary. The pocket's rim is an inner boundary, so it adds no corners.

`ThreadSpec::iso_metric("M5x0.8")` names diameter and pitch, so std computes every thread diameter and limit from the formulas of ISO 68-1 and ISO 965-1 with no licensed table installed. The `hole` call writes a `HoleSpec` record on the created faces; drawings, inspection plans and machining read that record, not the geometry.

`part` gives the body identity: a name and an item number, both in source. Changing `depth` from 30 mm to 40 mm rebuilds everything and renames nothing, because entity names never include argument values ([ANV](02-anvil.md)).

### Roles and queries

Every feature that sweeps geometry gives its new faces, edges and vertices roles, and ANV owns that vocabulary. For profile edges `e` and vertices `v`, `extrude` creates faces `start_cap`, `end_cap` and `side(e)`, edges `start(e)`, `end(e)` and `lateral(v)`, and vertices `start(v)` and `end(v)`. A role filter on the wrong kind of entity fails to compile.

```
let lid  = sketch(plane.xy) { rect(80mm, 50mm) } |> extrude(6mm)
let soft = lid |> fillet(lid.edges(role: end(any)), 1.5mm)
```

Features add their own role names as aliases: `hole` names its `wall`, `floor` and `countersink`. Queries match the aliases, while entity identities hash the operation's role, so a std feature that changes its internal operations releases as a labelled, output-changing version.

**Decision D-MEC-1:** Every `std::mech` feature declares typed roles for the entities it creates, and queries in std select by provenance and role first, with geometric predicates (`longest`, `parallel_to`) only as filters after them.
*Why:* provenance and roles survive parameter edits, while a geometric predicate flips when a dimension changes.
*Rejected:* matching faces by name heuristics (they rebind silently); persistent face ids stored in source (they break under semantic merge).

MEC never orders, seeds or breaks a tie by a name, so renaming a binding changes no geometry and no check value. Fillet edges, GD&T (geometric dimensioning and tolerancing) targets and drawing items are extent uses: they need the whole entity. If an edit merges or partly deletes such a target, resolution fails with a typed `ResolveError` unless the call accepts the change with `accept: [Merged, Partial, Fragile]`, which defaults to empty ([contract 5.5](../contract.md)).

### Failures that carry their fix

Every failure is a `FeatureError { kind, why, fix: [Fix], at: [EntityId] }`, where each `Fix` is a source edit that compiles. A fillet radius too large for its edge fails with `RadiusTooLarge { max_feasible }`, and its first fix rewrites the radius to the largest feasible value.

Failure kinds use ANV's names, since most features fail where an Anvil operation fails. A feature adds a kind of its own only for a precondition it checks before calling Anvil, such as `PathNotG1 { vertex }` on a kinked sweep path. The capability tables mark those kinds "feature-level".

**Decision D-MEC-2:** Approximation is always opt-in through an explicit parameter, for example `fallback: Fallback::Implicit(max_deviation: 0.01mm)`, and a feature that cannot produce an exact result fails and offers that fallback as a `Fix`.
*Why:* the contract forbids silent fallbacks, and a designer must see every deviation before it reaches a released part.
*Rejected:* automatic fallback with a warning (warnings get ignored, and released geometry would carry unseen error).

Some features build less than full geometry on request, through `detail: Detail`. `Cosmetic` stores intent only (a thread's specification without flanks), `Simplified` builds light geometry with a recorded error bound, and `Full` builds complete geometry. Threads default to `Cosmetic`.

### Tolerances travel with the design

The canonical bracket of [contract section 6](../contract.md) declares `thickness: Length = 6mm ± 0.1mm` and passes it to `extrude` and to `rib`. Each of those features marks the parameter whose value it realizes, here a feature of size. Each therefore records its own PMI (product and manufacturing information: the dimensions, tolerances and notes attached to the 3D model). So the plate and the web carry independent tolerances, as two machining operations would make them.

A tolerance passed to a parameter that realizes nothing, such as a clearance distance, fails to compile with `ing/4104 ToleranceNotRealized`, whose fixes are `.nominal` or an explicit `part.tolerance(…)`. Every dimension without an explicit tolerance takes the Part's declared general tolerance, so a stack-up never counts it as exact.

GD&T zones bound the form, orientation and location of faces. They attach to the same faces through records, and a check fails if a later edit splits a toleranced face. The Tolerancing section specifies the model; here it is enough that every tolerance lives in source, travels with the geometry and is checked on every merge.

### Parts, Items and multi-part features

`part(body, name:, item:)` turns a body into a Part with identity, and `material`, `make_or_buy`, `unit` and `classification` complete it. These identity attributes are evaluated from source, so a renamed part is a reviewed source change. KLN's Item record holds only lifecycle facts: revisions, states, effectivity and signatures ([KLN](05-kiln-repo-plm.md)).

A feature may return several Parts designed together, as a record: `-> (housing: Part, cover: Part)`. Each Part keeps its own item number and its own `GeometryId`, the name-free hash of its geometry, so editing the cover never revises the housing.

Every record that changes what is made is definitional: tolerances, datums, `HoleSpec`, `ThreadSpec`, welds, surface texture, edge callouts and plies. These enter the Item's definition by canonical entity number, so changing one marks the released Item modified, while a role alias or a display style does not ([contract 5.5](../contract.md)).

### Who writes the source

Agents write most of this source, and people steer, review and approve it. Every gesture in the interface writes the same Ingot an agent would: dragging a sketch point, trimming a line, Insert Instance, Add mate, editing a dimension on a drawing. Each arrives as a ranked edit plan the person can read before applying it ([UIX](10-ui.md)). Nothing exists only in the graphical interface, so a review sees every change as a source diff with its geometry and check results.

[[DIAGRAM diagrams/06-mechanical-data-flow.jsx: MEC data flow · design to Flux, MFG and drawings on one solver]]

Read the diagram left to right, from skeletons through Parts and Assemblies to the three consumers; the shared solver along the bottom serves every stage.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Role vocabularies | Face, edge and vertex roles of every std feature; `FeatureRole` aliases | `ResolveError` with ranked fixes | MEC-O-PF-1 | 1 |
| Typed failures and fixes | `FeatureError { kind, why, fix, at }` with ANV's kind names plus marked feature-level kinds | None: the failure is itself the typed value | ANV-O-NAME-5, ANV-O-NAME-7, MEC-O-CK-2 | 1 |
| Opt-in approximation | `fallback:` and `detail:` with a recorded `ErrorBound` | The exact attempt fails and offers the fallback as a `Fix` | MEC-O-PF-5 | 1 |
| Identity attributes from source | `part(body, name, item, …)`; material, make or buy, unit, classification | `DuplicateItem { item }`; `UnitMismatch { item, unit }` | MEC-O-AS-13 | 1 |
| Multi-part features | A feature returns a record of Parts, each with its own item and `GeometryId` | `DuplicateItem { item }` | MEC-O-AS-13 | 1 |
| Definitional attributes and identity | `ItemDefinition` inputs; Part and Assembly `GeometryId`s (Reference) | None: every attribute class declares whether it is definitional | MEC-O-AS-13 | 1 |
| Label invariance | No order, seed or tie-break from names | None: names never enter a decision | ANV-O-LABEL-1 | 0 |

## Sketching

Sketches carry most design intent in a mechanical part, so they are solved, diagnosed and edited with the same care as solids.

A sketch is a set of entities, constraints and dimensions, which the solver turns into solved geometry and a solve report.

### Entities and constraints

| Entity | Unknowns (2D) | Phase |
| --- | --- | --- |
| `point`, `line`, `construction_line` | Coordinates; two end points | 1 |
| `arc`, `circle` | Center, radius, start and end angles; three-point and tangent helpers | 1 |
| `spline` (interpolating) | Through points with optional tangent and curvature handles | 1 |
| `helix`, `spiral` | Axis frame, pitch, turns, taper (exact `anvil::curve` helices) | 1 |
| `offset`, `use_edges` | Driven by a source chain or a model-edge `Query`; `use_edges` never rebinds | 1 |
| `text` | Driven outlines from `anvil::text_outline` over a pinned font package | 1 |
| `rect`, `rect_between`, `slot`, `polygon` | Helpers emitting entities, constraints and named sub-entities | 1 |
| `ellipse`, `elliptical_arc`, `conic`, `nurbs` | Axes and ratio; ends, apex and rho; control points and weights, degree 2 to 7 | 2 |
| `intersection_curve` | Driven, in 3D sketches | 2 |

G1, G2 and G3 name continuity of tangent, curvature and curvature derivative across a joint. Helpers name what they emit, such as `rect`'s lines `left` to `top` and corners `bottom_left` to `top_right`. The names reach solids as roles: an extrusion of `r` has the face `side(r.bottom)` and the edge `lateral(r.bottom_left)`.

| Constraint | Equations | Notes | Phase |
| --- | --- | --- | --- |
| `coincident`, `point_on` | 2 or 1 | On a NURBS (non-uniform rational B-spline) curve, adds the curve parameter | 1 |
| `horizontal`, `vertical`, `parallel`, `perpendicular`, `collinear` | 1 each | | 1 |
| `tangent` (G1), `curvature` (G2), `g3` | 1 to 3 | Contact parameters are unknowns; side qualifier stored | 1 (G1), 2 |
| `concentric`, `midpoint`, `symmetric` | 2 each | About a line, or a plane in 3D | 1 |
| `equal` | 1 per pair | Mixed kinds share one value, as in D-Cubed's 2D DCM v79 [Siemens 2D DCM v79] | 1 |
| `fix` | 2 or 3 | Position, or position and orientation | 1 |
| `dim` (distance, angle, radius, diameter, length, curve length) | 1 | Signed variants carry half-space qualifiers | 1 |
| `mirror` | Per entity | About a construction line | 1 |
| `dim_range` | Inequality | Solved by an active set | 2 |
| `pattern` (linear, circular) | Per instance | | 2 |
| `on_plane`, `on_surface`, `along` | 1 or 2 | 3D sketches | 2 |
| Custom equations | 1 | `e1 == e2` over symbolic `Expr<T>` values ([ING](01-ingot.md)) | 2 |

`dim(target, value)` drives a value, while `measure(target)` is driven and never writable. A toleranced driving value drives the nominal, and its tolerance becomes PMI when the dimension is marked `pmi`.

```
let s = sketch(plane.xy) {
    let r = rect(80mm, 50mm, center: point(40mm, 25mm))   // seeds
    let c = circle(point(15mm, 15mm), 4.2mm)
    fix(r.bottom_left)
    dim(r.width, 80mm)
    dim(c.diameter, 8.4mm ± 0.05mm, pmi: true)
    dim(distance(c.center, r.left), 15mm)
}
```

### Sketch edits

Trimming, extending and filleting in a sketch look like drawing operations, but in a constraint-first model each one changes which entities exist and which constraints hold. Each edit tool therefore writes a defined source rewrite, so an agent and a person produce the same text and a review sees exactly what changed.

| Tool | Source rewrite | Phase |
| --- | --- | --- |
| `split_at(e, p)` | Two pieces named `e.a` and `e.b` in curve direction, coincident at `p` | 1 |
| `trim(e, at: p)` | `split_at` at the neighbouring intersections, then `remove` of the piece containing `p`; a trimmed circle becomes an arc | 1 |
| `extend(e, to: target)` | A `point_on` constraint from the extended end to the target | 1 |
| `corner_fillet(v, r)` | An arc named `fillet(v)` with two `tangent` constraints; the two ends move to the tangent points | 1 |
| `corner_chamfer(v, d)` | A line named `chamfer(v)`, with a distance or a distance and an angle | 1 |
| `offset(chain, d)`, `use_edges(query)` | Driven entities, as in the entity table | 1 |
| Region selection | Picking regions of `make_regions` for a profile, so no geometry is deleted | 1 |
| `import_dxf(asset, layers:)` | Entities with coincidences inferred within a stated tolerance and `fix` constraints; reading DXF (AutoCAD's drawing exchange format) is ECO's | 2 |

**Decision D-MEC-38:** Sketch edits are source rewrites that add statements referring to existing entities by name; they never expand a helper call or delete text that another entity uses. Constraints on a removed span transfer by one rule: coincidence and tangency move to the surviving endpoint, dimensions on the removed span are deleted and listed in the diff, and new points take their seeds from the solved geometry.
*Why:* a trim changes entity identity and constraints, so it is a design decision that must be visible in review, and keeping helper calls intact keeps every downstream role.
*Rejected:* rewriting a helper into raw entities on the first edit (every downstream role would be renamed); deleting a span's dimensions without listing them (constraints would vanish unseen); a trim stored as geometry outside source (two truths).

Each edit is one Change, one immutable edit in the design's history, and keeps the `CallSite`, the source-derived identity, of every untouched entity. The solve report after an edit shows the same degrees of freedom except where the edit removed or added one, and the diff says which.

### Reference images

`canvas(image: Asset, on: CoordSys, calibrate: (Point, Point, Length), opacity:)` places a scaled image on a plane for tracing a concept sketch, a photo or a scanned legacy drawing, in phase 2. Two picked points and their known distance set the scale, as Fusion's calibrated canvas does [Fusion canvas]. A canvas is display-only and outside the Item's definition. An agent that reads it treats it as an instruction-capable image, which sets its context `instruction_tainted` ([AGT](09-agents.md)).

### Solver

**Decision D-MEC-3:** Geometric constraint solving is one Anvil operation family, `anvil::solve_constraints` and `anvil::analyze_constraints`, serving sketches, mates, live rules, control-point edits, scan snapping, routing, tolerance completeness and posture. Each built-in constraint has a reference residual in Ingot, which a native kernel stands in for only when an oracle proves them equal, and custom constraints are `Expr<T>` functions lowered to Flux's kernel IR (intermediate representation).
*Why:* the solver has nine clients, runs at 60 Hz during drags and calls Anvil's evaluators in every iteration.
*Rejected:* a Wasm (WebAssembly) component (every iteration would cross the sandbox boundary); Ingot (too slow for sparse factorization); separate sketch and assembly solvers (two diagnosis models); a `constraint` keyword.

**Decision D-MEC-4:** The solver decomposes the system structurally, solves well-determined blocks numerically on the canonical `linalg` crate, and resolves under-determined parts by minimum displacement from the seeds. Blocks of up to 128 unknowns are factored densely and certified by a Krawczyk test, and larger blocks use sparse QR (orthogonal-triangular) factorization with a rank-revealing pass and report an `Estimated` bound from the factorization's residual; a wide bound never fails a solve, and only a discrete qualifier the box leaves undecided fails, with `Ambiguous { block, qualifier }`.
*Why:* Zou et al. find that ill-constrained parts must be detected before numerical solving can work [Zou 2022], most sketches are under-constrained, a residual alone bounds no error near tangency, and dense cubic work above about a hundred unknowns breaks the drag budget.
*Rejected:* constructive decomposition first (rule repertoires are incomplete); one monolithic solve (conflicts cannot be localized); failing on a wide bound (a 0.05 mm chamfer on a 400 mm profile would fail); faer's sparse QR (runtime CPU dispatch and no rank-revealing mode).

A Krawczyk test is an interval-arithmetic test that proves a system has exactly one solution in a box; the box radius becomes the `Guaranteed` bound. The solve runs in six steps:

1. **Lower.** Angles become unit complex numbers and rotations unit quaternions on manifolds, the Ceres `Manifold` pattern [Ceres modeling]; lengths are scaled by the seed box.
2. **Reduce.** Fixed groups collapse into rigid clusters, and equations solvable alone substitute forward, as in SolveSpace [SolveSpace].
3. **Decompose.** A maximum matching gives the Dulmage–Mendelsohn split into over-, well- and under-determined parts, solved in topological order.
4. **Solve.** Each block runs trust-region Levenberg–Marquardt with rank-revealing QR, or SVD (singular value decomposition) on ambiguous blocks; above 128 unknowns, sparse QR precedes a rank-revealing pass on R.
5. **Certify.** A block of up to 128 unknowns gets a Krawczyk box and its `Guaranteed` bound; a larger block, or one whose test fails, gets an `Estimated` bound. A check that needs a tighter bound returns `Undecided { needed }` through the ordinary decision rule.
6. **Remainder.** Under-determined parts minimize weighted displacement from the seeds, which SolveSpace reports gives less surprising drags. Step 5 certifies their KKT (Karush–Kuhn–Tucker) system, which is square and regular at a strict minimizer.

[[DIAGRAM diagrams/06-mechanical-constraint-solve-pipeline.jsx: constraint solve pipeline · six steps, three branches]]

Read the top row left to right, then follow each block down through its solve and certification to the result that features receive.

During a drag, the moved entity gets a weighted soft target, and each frame re-solves only the blocks at or after the dragged entity's block in Dulmage–Mendelsohn order. Those frames are warm-started and uncertified, since a drag is `Interactive`; the build that follows certifies. The user interface streams literal overrides through AGT's `edit.stream` at the `Drag` priority class, on PLT's `Drag` lane, and Kiln never writes an overridden result to the shared cache. Overrides follow `#[was]` renames, so a concurrent rename does not end the drag.

Builds never warm-start, so their results are bit-identical across the canonical platform class, the set of machines whose results must match bit for bit.

### Determinism and seeds

**Decision D-MEC-5:** The coordinates written in a sketch block are seeds, and the solved sketch is a deterministic function of seeds, constraints and the pinned operation version; when driving values move far from the seeds, a predictor-corrector continuation path keeps the solver on the seeds' branch, and discrete qualifiers (angle orientation, tangency side, arc direction) are stored in source when a constraint is created.
*Why:* the result must depend on source only, and continuation is the standard remedy for Newton's sensitivity to its start point.
*Rejected:* solving from the previous session's solution (history-dependent, breaks merges); homotopy that finds all solutions (too slow for interactive use [Zou 2022]).

If continuation cannot reach the targets, the solver returns `BranchFlip` or `NoConvergence` with the last reachable value, never a solution on another branch.

**Decision D-MEC-33:** Seeds stay inline in source, rounded to a quantum q = 2¹⁰ρ of the sketch, where ρ is the sketch's resolution, the scale-relative length below which Anvil treats geometry as coincident; releasing a drag writes only entities that moved by more than q, with more digits wherever rounding would change the solution.
*Why:* seeds decide under-determined parts, so they are intent and belong in the text Git stores; a scale-relative quantum keeps MEMS (micro-electromechanical systems) sketches at sub-micrometre seeds and ship sketches short.
*Rejected:* a layout section merged by last writer (it drops one of two concurrent drags); full-precision seeds (many literals per drag and a conflict on every concurrent drag); a fixed 1 µm floor (it would round away MEMS geometry).

Seed literals merge as ordinary literals. Two sides that change the seeds of one under-determined block conflict for real, and ING states the merge rule.

### Diagnosis

| `SolveReport` item | Method |
| --- | --- |
| Degrees of freedom | Kernel of the scaled Jacobian, shown as arrows |
| Fully constrained entities | No kernel vector moves the entity's unknowns |
| Redundant and conflict sets | Row dependencies; a deletion filter in canonical order, then a minimality pass; every member offered as a `Fix` |
| Generic or accidental | Rank at a witness built in decomposition order with rational choices, so incidences and tangencies hold exactly |
| Certification | Modular rank and exact kernel vectors on a rational witness; otherwise a nonzero interval minor at a Krawczyk-certified witness, with deficiencies `Estimated` |

A witness is a configuration of the sketch at which rank is computed. Zou and Feng show that the witness method needs a witness that satisfies every incidence exactly, and that greedy variants return non-minimal sets [Zou and Feng 2019].

Curve lengths use Gauss–Legendre quadrature within the certified radius, and 3D sketches drive sweep paths, routes and skeletons. Targets: a 200-entity sketch re-solves in under 2 ms native. A 2,000-entity drag step takes under 8 ms native and 16 ms in the browser, even when one block holds 1,000 unknowns.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| 2D sketch solve | `sketch(plane) { … }` through `anvil::solve_constraints`. Requires: ANV `anvil::solve_constraints`, `analyze_constraints` | `Conflict`, `NoConvergence`, `BranchFlip`, `Degenerate`, with the failing block | MEC-O-SK-1, MEC-O-SK-4 | 1 |
| Certified positions | `Guaranteed` from a Krawczyk or KKT box up to 128 unknowns, else `Estimated`; never failing on width | `Ambiguous { block, qualifier }` | MEC-O-SK-8 | 1 |
| Degree-of-freedom report | `SolveReport` on rational witnesses; modular or interval rank | Uncertified verdicts flagged | MEC-O-SK-2 | 1 |
| Drag | `edit.stream` at 60 Hz at `Drag` priority; downstream blocks only, uncertified | Holds the last converged frame | MEC-O-SK-5 | 1 |
| Seeds in source | Inline seeds rounded to q | More digits where rounding would change the branch | MEC-O-SK-4 | 1 |
| Named helper entities | Sub-entities of helpers as roles | Unknown name fails to compile | MEC-O-SK-9 | 1 |
| Sketch edits | Split, trim, extend, corner fillet and chamfer, offset, use edges and region selection as source rewrites | `NoIntersection { entity }`; `WouldOrphan { entities }` | MEC-O-SK-10 | 1 |
| DXF import to sketches | `import_dxf(asset, layers:)` with inferred coincidences | `UnmappedEntity { kind }` | MEC-O-SK-10 | 2 |
| Text | Shaped glyph outlines to regions | `FontMissing { font }` | MEC-O-PF-17 | 1 |
| Splines and helices | Interpolating splines; exact helices | `Degenerate` | MEC-O-SK-6 | 1 |
| NURBS, conics, ellipses | Entities above | `Degenerate` | MEC-O-SK-6 | 2 |
| 3D sketch | `sketch3d() { … }` | As 2D | MEC-O-SK-1 | 2 |
| Inequalities | `dim_range(target, min, max)` | `Conflict` when infeasible | MEC-O-SK-3 | 2 |
| Custom constraints | `Expr<T>` functions in the kernel IR | `ing/2402` on branching over unknowns | MEC-O-SK-7 | 2 |
| Reference images | `canvas` with two-point calibration; display-only | `AssetUnreadable { asset }` | MEC-O-PF-16 | 2 |

## Part features

Part features turn sketches into solids and dress them, and their shared conventions keep every part's history readable as a sequence of intents.

### Conventions

**Decision D-MEC-6:** Features that create material from profiles (`extrude`, `revolve`, `sweep`, `loft`, `boundary`, `rib`, `thicken`) return new tool bodies, and Booleans are written only with `+`, `-` and `&`, or `combine` for n-ary cases; features that dress existing geometry (`fillet`, `chamfer`, `shell`, `draft`, `hole`, `thread`, direct edits) take a body and return it changed.
*Why:* one spelling per intent, the Boolean is visible in history, and Kiln caches the tool body apart from the Boolean.
*Rejected:* a result option on every feature, as Onshape's extrude offers New, Add, Remove and Intersect [Onshape extrude] (a second spelling of the same operator).

The housing in "Designing a part" shows the pattern. `Extent` is shared by every profile feature: `Blind`, `Symmetric`, `ThroughAll`, `UpTo(Query)`, `UpToNext(Body)`, `Offset(Query, Length)` and `UpToVertex(Query)`.

`std::mech::refgeom` places sketches, mirrors and patterns with `plane.offset`, `plane.at_angle`, `plane.mid`, `plane.through`, `plane.tangent`, `axis.of`, `axis.through` and `point.on`. Each returns a value anchored by queries, which re-resolves on every rebuild. `face.corners(inset:)` returns the convex vertices of a face's outer loop, each moved inward along its corner bisector to the stated distance from both edges.

A frame derived from shape (a centroid, an edge midpoint) moves when the face changes shape. It carries `Note::ShapeDerivedFrame`, which release checks may forbid.

PLT owns contract 13.3's rebuild targets, and MEC keeps features cheap enough to meet them. Cosmetic threads and geometry-mode patterns keep face counts low, and each feature declares a cost estimate that Kiln's preview scheduler reads.

### Profile features

```
pub feature extrude(profile: Profile, #[realizes(OfSize)] extent: Extent = Blind(10mm),
                    dir: Direction = normal, draft: Angle = 0deg, thin: Option<Length> = none,
                    twist: Option<Field<Length, Angle>> = none, scale: Option<Field<Length, Real>> = none) -> Body
```

A plain `Length` converts to `Blind`, so `extrude(thickness)` in the canonical bracket reads as written.

`revolve`, `sweep`, `loft`, `boundary`, `thicken`, `rib` and `helix` follow the same pattern, and each marks the parameters whose value it realizes. `sweep` takes a path, guides and a `SweepFrame`, by default `RotationMinimizing`, since Frenet frames flip at inflections. `loft` takes sections, guides and end conditions.

A feature ships no earlier than the intersection classes its output surfaces need ([contract 7.1](../contract.md)). Phase 1 therefore has extrusions without twist or scale, revolutions, and sweeps of circular profiles along line and arc paths. Lofts, other sweeps, helical sweeps, and twisted or scaled extrusions join in phase 2 with general NURBS intersections and offsets.

### Holes and threads

```
pub feature hole(body: Body, at: Query<Point>, spec: HoleSpec, extent: HoleExtent = ThroughAll) -> Body
pub feature thread(body: Body, faces: Query<Face>, spec: ThreadSpec, detail: Detail = Cosmetic) -> Body
```

`HoleSpec` is `simple`, `counterbore`, `countersink`, `counterdrill`, `spotface`, `tapped`, `tapered_pipe` or `clearance`. Every diameter accepts a `Tol<Length>` or an ISO 286 fit code such as `H7`, and `clearance(5.5mm)` or `clearance(5mm, fit: H13)` needs no series table. A hole through several bodies records each segment, which fastener stacks read.

**Decision D-MEC-7:** Holes and threads are semantic first: `hole` writes a `HoleSpec` and `thread` a `ThreadSpec` keyed by the created entity ids, and geometry follows from the record; threads default to `Detail::Cosmetic`, `Detail::Full` builds printed flanks on the mesh path in phase 1 within the chord tolerance of 3MF (the 3D Manufacturing Format), and exact B-rep (boundary representation) flanks arrive in phase 2.
*Why:* drawings, PMI, CAM (computer-aided manufacturing) and inspection need the semantics, phase 1 surface–surface intersection has no helicoid pairs, and 3MF is a mesh anyway.
*Rejected:* geometry-only holes recognized later (recognition cannot recover a thread series); exact flanks in phase 1 (they need phase 2 intersection classes).

#### Standards content

Every machined part needs thread profiles, fits and clearance holes, but standards bodies license their tables. MEC separates what a formula computes from what only a table holds.

**Decision D-MEC-31:** std computes standard values from the formulas the standards define, citing clauses, and ships no transcribed tables; a designation that carries its own values (`M5x0.8`, `1/4-20 UNC-2B`, an explicit clearance diameter or fit code) resolves with no table, and the UI always writes that explicit form. Values that exist only as tables (series pitches, clearance-hole series, fastener dimensions, steel sections) ship as separate data packages carrying a `DataLicence`, from the standards body, a licensed distributor, a manufacturer or the organization.
*Why:* ISO licenses its machine-readable files only "in their original format without any modifications" [ISO 10303 notice], extracting a substantial part of a database can infringe the EU database right [Directive 96/9/EC], and a designer's first tapped hole must work with nothing licensed installed.
*Rejected:* tables in Apache-2.0 std (rights Crucible does not hold); no standards content (every part needs fits and threads); a Crucible-defined clearance-hole series (it would read as a standard and drift from ISO 273 in the shop).

| Package | Content | Kind | Phase |
| --- | --- | --- | --- |
| `std::standards::iso286` | ISO 286-1:2010 tolerance grades and fundamental deviations | Formulas in std | 1 |
| `std::standards::iso_metric_thread` | ISO 68-1:2023 basic profile; ISO 965-1:2026 tolerance formulas | Formulas in std | 1 |
| `std::standards::unified_thread` | ASME B1.1-2024 profile and tolerance formulas | Formulas in std | 1 |
| `crucible::standards::thread_plans` | ISO 261:1998 and ASME B1.1-2024 diameter–pitch series | Licensed data | 1 |
| `crucible::standards::clearance_holes` | ISO 273:1979 series; inch series | Licensed data | 1 |
| `crucible::standards::pipe_thread` | ISO 228-1:2000, ISO 7-1:1994, ASME B1.20.1-2013 | Licensed data | 2 |
| `crucible::standards::trapezoidal_thread` | ISO 2904:2020, ASME B1.5-1997 | Licensed data | 2 |

A designation without its pitch, such as `"M5"`, resolves through the series package when one is pinned. Without it, the call fails with `UnknownSize { series, near }`, whose fix rewrites the call to the explicit form. A design therefore compiles with no licensed package installed, and every package records its edition. Counsel's opinion on which tables std may ship is a phase 0 gate item ([contract 13.1](../contract.md)).

### Dress-up features

```
pub feature fillet(body: Body, edges: Query<Edge>, r: RadiusLaw, section: BlendSection = Circular,
                   corners: Corners = Auto, overflow: Overflow = RollOver, fallback: Fallback = Fallback::None) -> Body
```

`RadiusLaw` is a `Length`, `Linear(r0, r1)` or a `Field<Edges, Length>`. `fillet` maps to `anvil::blend`, `face_fillet` to its face-to-face variant and `full_round` to its three-face variant. ANV owns the blend stages, the configurations each stage covers and the part-level benchmark that judges them ([ANV](02-anvil.md)).

That benchmark rebuilds whole public parts whose originals Parasolid made, the kernel inside SOLIDWORKS and Onshape [engineering.com Parasolid], so its targets measure parity with the kernels users leave [ABC dataset]. Stage 1 covers what GP1 needs: constant and linear radii, sequential fillets, mixed-convexity corners and edges whose convexity changes along their length. Partial-length blends, capped and cliff ends, conic sections and Field radii follow in stage 2, and corners of valence four and above in stage 3.

With `fallback: Implicit { max_deviation }`, a failed region becomes an implicit patch fitted G1 to its neighbours. `Note::BlendFallback` states its certified deviation and seam gap.

**Decision D-MEC-34:** The release check `fallback_regions` passes only when, for each implicit fallback region, its certified deviation lies within the governing profile or general tolerance, no semantic PMI targets it, and the Part's process accepts it; additive processes take implicit regions through 3MF, while a hand-off in STEP (ISO 10303, the exchange format for exact product geometry) for machining, moulding or sheet needs the region converted to B-rep within the same tolerance.
*Why:* the deviation is already certified, and shops' CAM and coordinate-measuring software read B-rep.
*Rejected:* no release check (an implicit region could reach a STEP-only shop); machining meshes with mesh-capable CAM (rare, and measurement programming still needs B-rep).

MFG's process rule names the hand-off, and `check::standards` enforces the decision.

`shell` takes `mode: Natural | Round`, defaulting to `Natural`. An inward shell of a filleted box whose fillet radius is below the wall then removes the collapsed blend faces, leaves the inner edge sharp and reports `Note::BlendCollapsed { faces }`. `Round` offsets by an exact rolling ball, which erodes the solid and turns small inner fillets into sharp edges.

### Patterns, mirror and hulls

```
pub feature pattern<T: Patternable>(seed: T, at: [Keyed<Transform>], mode: PatternMode = Geometry, skip: [Key] = []) -> T
```

The generators `linear`, `circular`, `along`, `at_points`, `fill` and `by_density` return keyed transforms. `linear` keys `(i, j)`, `circular` the angular index and `at_points` the anchor's `EntityId`; `fill` keys lattice coordinates from a declared origin, and `by_density` each seed's initial key. Adding a point renames no other copy, and `skip:` lists keys, never positions.

**Decision D-MEC-8:** `pattern` places keyed copies: `PatternMode::Geometry` (the default) evaluates the seed once and places copies with one n-ary Boolean, while `PatternMode::Feature` re-evaluates the seed per copy, which an extent such as `UpToNext` requires.
*Why:* geometry mode is one cached evaluation, and keys keep names and skip lists stable when generators gain or lose points.
*Rejected:* always re-evaluating (slow); always copying (wrong for location-dependent extents); positional indices (positional naming under another name).

Transforms always keep names. When one operation receives two operands with the same entity names, as in `half + mirror(half, plane.yz)`, Anvil relabels the later transform's operand with role `copy` or `mirror`. An explicit `copy(x)` always copies, and a read-only use of the source renames nothing.

A `mirror` and a complete `circular` pattern record their plane or axis as a declared symmetry. Flux may use it for symmetric, antisymmetric and cyclic-sector reductions from phase 2 (contract 13.4), after checking that the loads respect it ([FLX](03-flux.md)).

`hull` is exact on meshes and facet faces in phase 1 and bounded on B-rep operands in phase 2, with `minkowski`. `split` cuts by a plane, face set, sheet or sketch, and `combine` is an n-ary Boolean over any representation.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Reference geometry | Planes, axes and points anchored by queries; `face.corners(inset:)` on outer-loop convex vertices | `ResolveError`; `Note::ShapeDerivedFrame` | MEC-O-PF-16 | 1 |
| Extrude | Profile to solid or sheet with roles and draft; `#[realizes(OfSize)]` distance | `SelfIntersecting` with the largest feasible draft; `UpToNotReached { target }` | MEC-O-PF-1 | 1 |
| Twisted and scaled extrude | `twist` and `scale` Fields | `SelfIntersecting` | MEC-O-PF-2 | 2 |
| Revolve | Profile about an axis | `AxisCrossesProfile { points }` | MEC-O-PF-1 | 1 |
| Sweep | Circular profiles along G1 line and arc paths; other profiles, helical sweeps, guides and laws | `PathNotG1 { vertex }` (feature-level); `SelfIntersecting { region }`; `FrameUndefined` | MEC-O-PF-2 | 1, 2 (other profiles, helical, guides) |
| Loft | Sections, guides, end conditions, vertex matching. Requires: ANV `anvil::loft` | `IncompatibleSections`; `Twisted` with suggested matches | MEC-O-PF-2 | 2 |
| Boundary | Curve network with G0 to G2 edge conditions | `NetworkNotCompatible { curves }` | MEC-O-SF-2 | 2 |
| Thicken, rib | Face set to solid; open profile extended to material; `#[realizes(OfSize)]` thickness | `SelfIntersecting` | MEC-O-PF-3, MEC-O-PF-1 | 1 |
| Helix and spiral | Exact `anvil::curve` helices | `Degenerate` on zero pitch | MEC-O-PF-2 | 1 |
| Holes | `HoleSpec`, hole chains; explicit clearance diameters and fits | `UnknownSize { series, near }`; `BreaksOut { faces }` (feature-level) | MEC-O-PF-4 | 1 |
| Threads | `Cosmetic`; `Full` on the mesh path, then exact | `ThreadTooLong` (feature-level) | MEC-O-PF-4 | 1, 2 (exact `Full`) |
| Standards content | Formulas in std with no table; licensed tables pinned in `ingot.lock`; designations with pitch need no package | `UnknownSize { series, near }` | MEC-O-PF-4 | 1 |
| Fillets and chamfers, stage 1 | `anvil::blend`, `anvil::chamfer`. Requires: ANV `anvil::blend` | `RadiusTooLarge { max_feasible }`, `BlendOverflow`, `VertexBlendFailed` | MEC-O-PF-5 | 1 |
| Blends, stages 2 to 4 | ANV's stage table | As stage 1; `SelfIntersecting { region }` | MEC-O-PF-5, MEC-O-SF-1 | 2, 3, 4 |
| Fallback regions at release | `fallback_regions` | Finding names region, deviation and process | MEC-O-PF-5 | 1 |
| Shell | Uniform or Field thickness; `Natural` or `Round` mode | `WallCollapse { region }`; `Note::BlendCollapsed { faces }` | MEC-O-PF-3 | 1, 2 (Field) |
| Draft | Neutral plane on analytic faces; free-form; `anvil::draft`'s parting and step modes | `DraftNotPossible { face, reason }` | MEC-O-PF-6 | 1, 2 (free-form), 3 (parting, step) |
| Patterns | Keyed generators; `skip: [Key]` | `CopyFailed { key, error }` | MEC-O-PF-7 | 1, 2 (along, fill, density) |
| Mirror and copies | Relabeling of colliding operands; `copy(x)`; declared symmetry for Flux | None: relabeling always succeeds | MEC-O-PF-7 | 1 |
| Hull and Minkowski sum | `hull`, then B-rep hulls and `minkowski` | `Degenerate`; `NotConvex { operand }` | MEC-O-PF-18 | 1, 2 |
| Split and combine | `split`, `split_face`, `combine` | `ToolDoesNotCut`; `Ambiguous`; `BelowResolution { size }`; `EmptyResult` (feature-level) | MEC-O-PF-8 | 1 |
| Rebuild budget | Feature cost estimates; contract 13.3 rows | Regressions block merges | MEC-O-PF-14 | 1 |

## Direct edits, reuse and generative design

Designers change geometry they did not model, reuse what they did, and ask the computer to propose shapes; these features do all three without leaving the program.

### Direct edits and wraps

Direct edits apply to any B-rep, imported geometry included, and are ordinary features in history. `push_pull` offsets faces through `anvil::offset_faces`, and `move_faces` translates, rotates or offsets them under live rules. `replace_faces`, `delete_faces`, `defeature`, `edit_aspect` and `drive` complete the set. Adjacent blends are rebuilt with the same parameters and names, or the edit fails with `BlendRegrowFailed` and its fixes.

**Decision D-MEC-9:** Direct edits solve face motions with the shared constraint solver: each moved or affected face gets a rigid motion or offset unknown, the edit and live rules are constraints, Anvil's face operations re-intersect neighbours and regrow blends, and recognized rules are written to source.
*Why:* Siemens describes synchronous technology as editing while related geometry adjusts "to maintain design intent" [Siemens synchronous technology], and Crucible gets that from mechanisms it already has, explicit in source.
*Rejected:* a history-free mode (two models of one part); hidden rule inference at every rebuild (results would change with the recognizer).

Phase 1 offers push-pull. Moving, replacing and deleting faces, defeaturing a supplier's model and rule detection follow in phase 2, with Anvil's face operations.

`emboss` raises, engraves or imprints curves on planar and cylindrical faces through the developable wrap, which is isometric and exact. It sweeps the imprinted region along the face normal and joins it by a union or difference. The walls meet the base face along the wrapped curves, so no new intersection class is needed.

`wrap` also offers `Conformal` and `Geodesic` methods with a distortion Field. `deform(body, map)` takes `bend`, `twist`, `taper`, `stretch`, `cage` or a displacement Field. The Field variant lets a warpage or springback result pre-compensate a tool face and returns the achieved bound.

### Derived parts and families

`derive(source, take, mirror, scale, params)` takes bodies, sketches, frames and parameters from a feature here or in a pinned dependency. Bumping the source is a Proposal that shows the derived geometry diff.

**Decision D-MEC-10:** A configuration is a parameter record, a design table is a table of them, and a part family is a design table whose rows carry part identity; suppression is a `Bool` parameter used in an `if`, and assembly variants mark their parameters `#[configuration]`.
*Why:* features are already functions of typed parameters, so configurations need no second mechanism, and review sees every variant as source.
*Rejected:* configurations inside the document, as SOLIDWORKS keeps them [SOLIDWORKS configurations] (invisible in review); a configured fastener count (a two-place edit per hole).

ING decides which values an Instance's existence may depend on: only configuration parameters and constants ([ING](01-ingot.md)). Kiln therefore computes the 150% BOM, the bill of materials of every variant at once, without enumerating variants.

```
pub feature conveyor(#[configuration] drive: Drive = Belt, length: Length = 2m) -> Assembly {
    let frame = instance(frame(length), fixed: true)
    let motor = instance(gearmotor_m3())
    let belt  = if drive == Belt { [instance(belt_kit(length))] } else { [] }
    assembly([frame, motor] + belt, mates: [fastened(motor.csys("flange"), frame.csys("drive_end"))])
}
```

`family(f, key:, rows: table { … })` checks every row's types and units at compile time, and ING owns the syntax. Each row is a Part with its own item number, and a family is green only when every row passes. UIX's family table editor edits the rows as a typed grid, each edit one Change ([UIX](10-ui.md)).

### Lattices

`lattice(region, cell, size, thickness, orientation, skin)` calls `anvil::lattice` and exposes the strut graph. `Cell` covers strut cells (body-centred cubic, octet) and sheet cells of triply periodic minimal surfaces (gyroid, Schwarz P, diamond). Joining a lattice to a B-rep part keeps the part's exact faces, names and attributes, so GP2's mounting holes keep their `HoleSpec` and GD&T.

Strut cells are checked at `SignOff` with Flux's beam-lattice model, whose joint-zone length and stiffness factor are calibration data per cell topology over a density range ([FLX](03-flux.md)). Sheet cells are checked from phase 2 on shells over the cell field's zero set. GP2 uses strut cells; a phase 1 sheet-cell lattice has no `SignOff` stress model.

### Generative design

Fusion users expect a workspace that takes a design space, kept regions, loads and manufacturing methods and returns outcomes to compare [Fusion generative methods]. In Crucible this is one feature over Flux's topology optimization, and its outcomes are ordinary Parts with checks.

```
let outcomes = generate(
    space: envelope,
    keep: [mount.aspects(created_by: bolt_holes), mount.face(role: start_cap)],
    avoid: [cable_clearance],
    cases: [load_case(fixed: clamp, force: 1.2kN * dir(-y), on: tip)],
    methods: [Method::Additive(build: dir(z)), Method::Unrestricted],
    objective: Objective::MinMass(subject_to: ["static_margin"]),
)
```

`generate` returns outcomes keyed by method and objective weight. Each outcome is a Part with its mass, its check margins and MFG's planned cost, so choosing one is a one-line edit that selects its key. UIX shows outcomes side by side, in a generated report in phase 1 and in its variant grid from phase 2.

**Decision D-MEC-39:** Kept regions enter every outcome as B-rep leaves of the optimized implicit body, so their faces, names, `HoleSpec`s and GD&T survive exactly, and every outcome must pass the checks the design already declares before it is offered.
*Why:* an engineer releases the interfaces, not the organic shape between them, and an outcome that loses its toleranced bolt holes cannot be made from a drawing.
*Rejected:* outcomes as meshes only (no PMI on interfaces and no STEP); a single best outcome (designers compare trade-offs); automatic selection of an outcome (people choose).

| Method | Constraints on the shape | Release path | Phase |
| --- | --- | --- | --- |
| `Additive { build, overhang }` | Overhang angle and minimum feature from MFG's process profile | 3MF with implicit regions | 1 |
| `Unrestricted` | None; a concept for comparison | Additive only, or after a method is chosen | 1 |
| `Milling { axes, tool }` | Tool access along 2.5-, 3- or 5-axis directions | STEP after fitted implicit-to-B-rep conversion | 2 |
| `TwoAxisCutting { direction }` | Constant section along one direction | STEP, DXF of the section | 2 |
| `Casting { pull }` | Draft and no undercuts along the pull | STEP after fitted conversion | 2 |

Phase 2 methods use FLX's manufacturing constraints and ANV's fitted implicit-to-B-rep conversion, which the parity floor puts in the same phase ([contract 13.4](../contract.md)).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Push-pull | `offset_faces` on any B-rep with blend regrowth. Requires: ANV `anvil::offset_faces` | `NeighborCannotExtend { face }`, `BlendRegrowFailed` | MEC-O-PF-9 | 1 |
| Move, replace and delete faces; defeature | Motions and live rules on the shared solver; aspect removal on imports. Requires: ANV `anvil::move_faces`, `replace_faces`, `delete_faces` | `TopologyChangeRejected`; `RuleConflict { set }`; `CannotHeal { loop }` | MEC-O-PF-9 | 2 |
| Recognized aspect edits | `edit_aspect` via `recognize_aspects` and `edit_blend` | `NotRecognized` with the best partial match | MEC-O-PF-9 | 2 |
| Emboss and engrave | Developable wrap; region swept along the normal | `OutOfDomain { curves }` | MEC-O-PF-17 | 1 |
| General wrap and deform | Conformal and geodesic wraps; maps with achieved bound | `FoldOver { region }`; `ToleranceNotMet { achieved }` | MEC-O-PF-10 | 3 |
| Derived parts | `derive` with take, mirror, scale and parameters | `TakeMissing { name }` | MEC-O-PF-11 | 1, 2 (cross-repository) |
| Configurations and families | Parameter records; `#[configuration]` variants; families | `RowFailed { key, error }`; `DuplicateKey` | MEC-O-PF-12 | 1 |
| Lattices | `anvil::lattice` from Flux Fields; leaf-preserving join; strut-cell checks. Requires: ANV `anvil::lattice` | `BelowMinFeature { region, min }` | MEC-O-PF-13 | 1 |
| Sheet-cell lattice models | Shells on `anvil::mid_surface`'s implicit path | `UnpairedFaces` | MEC-O-PF-13 | 2 |
| Generative design, additive and unrestricted | `generate` with kept regions as exact leaves; outcomes keyed and checked. Requires: FLX Density topology optimization | `Infeasible { case, reason }`; `KeepRegionViolated { aspect }` | MEC-O-PF-19 | 1 |
| Generative design, milling, two-axis cutting and casting | Method constraints from FLX; fitted conversion for STEP release. Requires: ANV Implicit → BRep | `Infeasible { case, reason }`; `NotManufacturable { method, region }` | MEC-O-PF-19 | 2 |

## Assemblies

Assemblies place Parts relative to each other, and everything checked about a product as a whole (motion, clearance, fasteners, mass) reads them.

### Structure

An Assembly is a tree of Instances with placements and mates. An Instance references a Part or Assembly feature with parameter overrides, a `Transform` and a level of detail. An Instance set is one BOM line whose members are keyed by anchors and counted by evaluation, such as one bolt per resolved hole.

```
pub feature gearbox(ratio: Real = 3.0) -> Assembly {
    let housing = instance(housing(), fixed: true)
    let pinion  = instance(spur_gear(module: 1.5mm, teeth: 18))
    let wheel   = instance(spur_gear(module: 1.5mm, teeth: round(18 * ratio)))
    assembly([housing, pinion, wheel], mates: [
        revolute(pinion.csys("axis"), housing.csys("bore_in")),
        gear(pinion, wheel, ratio: wheel.teeth / pinion.teeth),
    ])
}
```

Mates attach only to `CoordSys` values (frames anchored to geometry), as Onshape's mate connectors are local coordinate systems on or between entities [Onshape mates]. Features publish named frames, `csys(query)` derives one from geometry, and a frame that fails to re-resolve is a `ResolveError` on the mate. `bom_item(item, qty, applies_to)` adds a BOM line without geometry, such as thread-locker or wire sold by length.

In phase 1, a person places Instances and adds mates through Insert Instance and Add mate. UIX generates these dialogs from `instance` and the mate functions, and their frame fields take selections ([UIX](10-ui.md)).

### Mates

| Mate | Remaining freedom (T translation, R rotation, in the second frame) | Limits | Phase |
| --- | --- | --- | --- |
| `fastened` | 0 | none | 1 |
| `revolute` | 1R about z | angle | 1 |
| `slider` | 1T along z | distance | 1 |
| `cylindrical` | 1T along z, 1R about z | both | 1 |
| `ball` | 3R | cone angle | 1 |
| `parallel`, `perpendicular`, `coaxial` | Orientation or axis relations | angle | 1 |
| `distance`, `angle` | One equation each, driving or driven | range | 1 |
| `pin_slot` | 1T along x, 1R about z | both | 2 |
| `planar` | 2T in xy, 1R about z | both | 2 |
| `tangent`, `symmetric` | Surface contact; one face pair centred between another | none | 2 |
| `gear`, `rack_pinion`, `screw`, `linear` | Two freedoms coupled by a ratio or pitch | none | 2 |
| `path(frame, curve, along: Tangent \| Fixed)` | A frame's origin follows a curve; orientation follows its tangent or stays fixed | position along the curve | 2 |
| `belt(pulleys: [Instance])` | Pulley rotations coupled by ratios from pitch diameters | none | 3 |
| `cam` | Follower kept on a cam surface | none | 3 |

A `path` mate carries a carriage along a curved track or a cable carrier along its run. A `belt` mate also creates a belt Body of evaluated pitch length, and for a chain an Instance set of links whose count is evaluated.

**Decision D-MEC-11:** Assembly mates use the same `anvil::solve_constraints` operation as sketches, with one SE(3) unknown (a rigid placement) per rigid cluster on a product manifold; fastened Instances merge into rigid clusters before solving, and joint limits are inequalities solved by an active set.
*Why:* one solver gives one diagnosis model, with motion arrows, minimal conflict sets and redundancy alike in sketches and assemblies.
*Rejected:* a separate assembly solver, the split that D-Cubed's 2D DCM and 3D DCM products reflect [Siemens 3D DCM] (duplicate oracles, different failure semantics); sequential transforms only (they cannot close kinematic loops).

Redundant but consistent mates, such as two coaxial hinges on one door, are `Redundant` warnings, which Flux's multibody solver removes or makes compliant.

### Kinematics and motion

```
let study = motion(gearbox(), drive: [(pinion_rev, angle(t) = 360deg/s * t)], t: 0s..2s, samples: 200)
study.require(min_clearance(study, housing, wheel) > 0.5mm, name: "wheel_clearance")
```

Positions track the drivers by continuation and give `Field<(Instances, Time), Transform>`. Velocities and accelerations solve the differentiated constraints with the Jacobian already factored. A rank drop returns `Singular { t, mates }`, and a reached limit `LimitReached { mate, t }`. UIX animates the result as moving parts.

**Decision D-MEC-12:** Dynamics belong to Flux: `motion` handles prescribed-motion kinematics, and anything with forces, masses, contact or compliance goes to Flux's multibody solver, which reads the same Assembly with its typed joints, redundancy report, bounded mass properties, contact pairs and drivers.
*Why:* kinematics reuses the constraint solver, while dynamics needs integrators, contact and validity envelopes.
*Rejected:* a dynamics engine inside the assembly library (a second physics engine beside Flux).

### Interference and clearance

`interference(asm, classify: true)` uses `anvil::interference`, which computes certified distances and overlap volumes on exact geometry.

| Class | Meaning | Default |
| --- | --- | --- |
| `Hard` | Positive interference volume | Error |
| `Touching` | Zero gap within the entity tolerance | Info |
| `IntendedThread` | Fastener thread inside a mating `ThreadSpec` | Ignored |
| `IntendedFit` | A touching cylindrical pair whose fit codes interfere | Interference from the `Tol` limits reported to tolerancing |
| `Clearance` | Gap below a declared minimum | Error when declared |

Geometry is built at nominal by default, so a 10 H7/p6 press fit touches, and its fit codes make it `IntendedFit`. `interference(asm, realize: Mmc)` builds every toleranced size at its maximum-material limit (Tolerancing, "Geometry at a point of the zone"), so the same press fit reports its true overlap. Contact explained by a mate, a `Weld`, a fastened joint or an `IntendedFit` never conflicts.

KLN's no-new-interference merge condition uses these classes ([KLN](05-kiln-repo-plm.md)). Flux's immersed tied interfaces start from the `Touching` pairs, each listed for confirmation as `Bonded` or `NoSeparation` ([FLX](03-flux.md)).

Motion studies sample adaptively. Between samples, a certified Taylor bound limits each body's displacement, from interval Newton on the differentiated constraints. Clearance is the interval [sampled minimum − that bound, sampled minimum], so `min_clearance` decides three-valued. Where the enclosure fails, the interval is `Estimated`, and a check that needs `Guaranteed` bounds returns `Undecided`.

`check::enclosure` checks clearance, keep-ins and connector cut-outs against boards from other electronics tools. It reads STEP board assemblies in phase 1 and ECO's readers for IDF (Intermediate Data Format) and STEP boards in phase 2. A re-exported board matches its earlier import through ANV's `match_bodies`, so every mate and check on unchanged faces survives the update.

### Designing across parts

Machine design is mostly done in the assembly: a cover drawn to fit its housing, a bracket to clear a cable run, a guard around a mechanism. Crucible offers three explicit ways to reference another part.

**Decision D-MEC-13:** Cross-part references go through three explicit mechanisms: skeletons (features returning frames, sketches, surfaces and parameters), interface records marked `#[interface]` that one part provides and another consumes, and context pins that read a past evaluation of the assembly at a pinned Change; geometry is never captured from another part implicitly.
*Why:* explicit dependencies keep the graph acyclic and visible in review, and a context pinned to a past Change lets a part be designed in its assembly position without a cycle, as Onshape's context snapshot does [Onshape in context].
*Rejected:* edit-in-context with live captured references, as SOLIDWORKS external references work [SOLIDWORKS external references] (hidden coupling and update cycles); live references with compile-time cycle detection (the commonest case, a part designed inside its own assembly, is a cycle); an `interface` keyword (no new keywords for domain concepts).

An interface record lets one source drive matching features in two parts, the job an incumbent's hole-series tool does. Here the motor mount drives clearance holes in the plate and tapped holes in the gearbox face:

```
#[interface]
pub record MotorMount { pilot: CoordSys, pilot_d: Tol<Length>, bolts: [CoordSys], thread: ThreadSpec }

let plate_body = plate |> hole(at: m.bolts, spec: HoleSpec::clearance(m.thread.major_d, fit: H13))
let face_body  = face  |> hole(at: m.bolts, spec: HoleSpec::tapped(m.thread, depth: 12mm))
```

`mate_interface(a, b)` places both sides with one mate and runs the derived `compatible(a, b)` check. Electronics uses the same records for board outlines and keep-outs.

A context pin serves the cover-on-housing case, in phase 2 for GP3's covers and GP4's guards. `context(of: assembly_feature, at: Pin, take: [Query]) -> Context` evaluates the assembly at a pinned Change and returns the taken bodies, frames and sketches, moved into the consuming Part's frame by its placement at that Change. The pin is recorded in `ingot.lock` as `{ source, selector: Change, resolved }`, like any pinned input.

Because the pin names a past Change, the consuming Part may sit inside that same assembly. "Update context" is a Proposal that moves the pin and shows the geometry diff. A lost reference is a typed `ResolveError`, and two branches that move one pin differently give `Conflict::Lockfile`. UIX's Edit in context draws the assembly transparent and turns selections into context queries.

`explode(asm, steps)` stores ordered steps, and `explode_auto` proposes them from a non-directional blocking graph [Wilson and Latombe 1994]. A subassembly Instance is rigid by default; `instance(sub, flexible: true)` exposes its free internal freedoms.

### Large assemblies

| `InstanceDetail` | Content | Error stated |
| --- | --- | --- |
| `Full` | Exact B-rep, loaded on demand | None |
| `Graphics` | Cached display tessellation levels | Chordal deviation per level |
| `Envelope` | Oriented box or convex hull | Hull deviation |
| `Shrinkwrap(gap)` | One closed skin from `anvil::shrinkwrap` | Bound from the operation |
| `Defeatured(rules)` | Small aspects removed by `anvil::defeature` | Removed aspects and volume change |
| `Excluded` | Not loaded | Excluded from mass properties, with a warning |

Opening loads structure and cached tessellations first, and B-reps only for Instances being edited or checked. Contract 13.3 sets scene capacity from phase 2. MEC adds a target: a 100,000-Instance assembly opens for viewing in under 15 s, from phase 4.

### Standard parts and fasteners

Fastener geometry comes first from manufacturers' catalog packages under `parts::<manufacturer>::`, published under the manufacturer's own terms, as supplier catalogues already work ([ECO](11-interop-ecosystem.md)). Standard-dimension packages are optional, each carrying a `DataLicence` and its edition.

| Data package | Examples | Phase |
| --- | --- | --- |
| `crucible::standards::iso_fasteners` | ISO 4762, 4014, 4017, 4032, 7089, 10642 | 2 |
| `crucible::standards::din_fasteners` | DIN 912, 933, 934 and other legacy designations mapped to ISO | 2 |
| `crucible::standards::ansi_fasteners` | ASME B18.3, B18.2.1, B18.2.2 | 2 |
| `crucible::standards::pins_rings` | Dowel pins, retaining rings, keys | 2 |
| `crucible::standards::self_clinching` | Self-clinching nuts, studs and standoffs | 2 |

`fasten(holes, spec)` returns an Instance set keyed by hole `EntityId`s, so adding a hole changes its quantity, never the BOM structure. Per hole it computes grip from the stacked `HoleSpec` segments, adds the minimum engagement and picks the shortest standard length. Each member records preload and tightening torque, which Flux's bolted-joint forms and fastener connectors read.

Selection resolves over the organization's approved parts first ([KLN](05-kiln-repo-plm.md)). Reaching the open catalog needs a recorded Waiver, so design, ERP (enterprise resource planning) and shop BOMs agree. Before a new Part is created, KLN's shape-similarity search shows the most similar released Items.

**Decision D-MEC-41:** A Part or catalog part may declare its mass properties with `part.mass_properties(declared: { mass, cg, inertia }, source: Datasheet(doc) | Measured(evidence))`, which stand in for computed values in every roll-up and are labelled "declared" in reports; a `Warning` check flags purchased Instances whose computed mass is used without a declaration.
*Why:* purchased parts arrive as simplified or hollow bodies, so their computed mass carries a certified bound on the wrong geometry.
*Rejected:* computed mass always (a hollow motor model weighs a fraction of the motor); a density correction factor (it leaves the centre of gravity and inertia wrong).

Flux's point masses with rotary inertia, used to stand in for a motor on a bracket, join the same mass-property roll-ups and checks.

### Mate inference and assembly-level features

`suggest_mates(a, b)` ranks candidates from interfaces, recognized aspects and an optional learned ranker, and suggestions become mates only when accepted. The ranker's benchmark comes from std assemblies and golden products; JoinABLe's reported 79.53% top-1 accuracy is literature only [JoinABLe].

An assembly-level cut or hole states its mode. `DerivedParts` creates derived Parts with new item numbers, while `AfterAssembly` is a manufacturing operation in the manufacturing BOM; created names carry the Instance path.

### Machine elements

| Machine element | Contract | Standard | Phase |
| --- | --- | --- | --- |
| Involute spur and helical gears | Module, teeth, pressure and helix angles, profile shift, relief, crowning, accuracy grade | ISO 21771-1:2024 geometry; ISO 1328-1:2013 flank tolerance classes | 2 |
| Bevel, worm, internal gears | As above | ISO 23509-1:2025; ISO 10828:2024 | 3 |
| Shafts | Steps, shoulders, relief grooves, ring grooves, keyways | DIN 509:2022, DIN 471:2026 and DIN 6885-1:2021 forms as licensed data | 2 |
| Bearings, seals, retaining rings | Catalog parts with mating frames and housing fits | Supplier data | 2 |
| Springs | Compression, extension, torsion | | 2 |
| Belts and chains | Pulleys and sprockets with pitch diameters; `belt` mates | Supplier data | 3 |

An involute is a closed-form curve, and a helical involute flank is a developable ruled surface. `std::mech::machine` therefore builds flanks as exact procedural Law surfaces through the kernel IR, and only an export approximates them, within the receiver profile's bound ([ANV](02-anvil.md)). GP3's loaded tooth contact and the over-pins value in the gear data table then carry no approximation.

COV owns gear, bearing and shaft ratings and loaded tooth contact analysis, in phase 2 ([contract 13.4](../contract.md)). MEC's gear record supplies their inputs: geometry, modifications, accuracy grade and load spectrum. Smooth flank contact is not a singular set, so root and flank checks can decide.

Drawings carry a gear data table with module, teeth, angles, profile shift, modifications, grade, and span or over-pins measurement. In phase 2 it is GP3's gear output to the shop's own gear process (MFG).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Instances and structure | `instance`, `assembly`, Instance sets, `#[configuration]` existence | `ResolveError` on a mate frame; `ing/2601` | MEC-O-AS-1 | 1, 2 (Instance sets) |
| BOM-only items | `bom_item` with the Item's unit | `UnitMismatch { item, unit }` | MEC-O-AS-9 | 1 |
| Mate solve and diagnosis | Mates above on the shared solver | `Conflict`; `Redundant` (warning) | MEC-O-AS-1 | 1, 2, 3 (cam) |
| Path mates | `path(frame, curve, along)` | `OffCurve { at }`; `Conflict` | MEC-O-AS-15 | 2 |
| Belt and chain couplings | `belt` mates; belt Bodies of evaluated length; link Instance sets | `PulleysNotCoplanar { pulleys }`; `Conflict` | MEC-O-AS-15 | 3 |
| Kinematics and motion studies | `motion` → `Field<(Instances, Time), Transform>` | `Singular { t, mates }`, `LimitReached { mate, t }` | MEC-O-AS-2 | 2 |
| Static interference | Classified clashes; `IntendedFit` from fit codes; `realize:` point. Requires: ANV `anvil::interference` | `WorkLimit` | MEC-O-AS-3 | 1 |
| Dynamic clearance | Taylor-bounded intervals; three-valued `min_clearance` | `Undecided` near singular positions | MEC-O-AS-10 | 2 |
| Enclosure checks | Clearance, keep-ins and cut-outs against imported boards | Findings as check Fields | MEC-O-AS-11 | 1, 2 (board readers) |
| Skeletons and interfaces | Skeleton features; `#[interface]` records; `mate_interface` | `Incompatible { field, provided, required }` | MEC-O-AS-8 | 1 (skeletons), 2 |
| In-context design | `context(of, at: Pin, take)` pinned in `ingot.lock`; update as a Proposal | `ResolveError`; `Conflict::Lockfile` | MEC-O-AS-14 | 2 |
| Exploded views | Ordered steps; automatic proposals | `CollidesDuringStep { step, pair }` (warning) | MEC-O-AS-5 | 1, 3 (automatic) |
| Flexible subassemblies | `flexible: true` | Conflicts list inner mates by path | MEC-O-AS-1 | 2 |
| Large-assembly detail levels | `InstanceDetail`; 100,000-Instance open | `DetailUnavailable { instance, detail }` | MEC-O-AS-4 | 2, 4 (100,000-Instance open) |
| Fasteners | Instance sets keyed by holes; grip, engagement, length, preload; manufacturer packages first | `NoStandardLength { needed, nearest }`, `EngagementTooShort` | MEC-O-AS-6 | 2 |
| Approved-parts selection | Approved parts first; open catalog only with a Waiver | `NotApproved { part }` | MEC-O-AS-9 | 2 |
| Declared mass properties | `part.mass_properties(declared:, source:)`; undeclared purchased mass flagged | `UndeclaredPurchasedMass { instance }` (warning) | MEC-O-AS-16 | 1 |
| Mate inference | Ranked suggestions | None: suggestions never change the design until accepted | MEC-O-AS-7 | 3 |
| Assembly-level features | `DerivedParts` or `AfterAssembly` | Omitting `mode` fails to compile | MEC-O-AS-12 | 2 |
| Gears | Exact Law flanks, semantics, accuracy grade, gear data table | `Undercut { teeth, min_shift }`, `PointedTip`, `MeshMismatch` | MEC-O-PF-15 | 2, 3 |
| Shafts and springs | Parametric sections; helical springs | `Degenerate` | MEC-O-PF-2 | 2 |

## Surfacing

Consumer products, castings and hulls need surfaces controlled beyond what profile features give, so surfacing adds freeform construction and quality checks to the same model.

### Continuity and surfaces

`Continuity` is `G0` to `G3`: shared position, then tangent plane, then normal curvature, then its derivative. Surfacing features take target continuities per edge and return a `ContinuityReport` from `anvil::analyze_continuity`, and Anvil's continuity certificates use the same enum. A feature that misses its targets returns `ContinuityNotMet { edge, achieved }` and never relabels the result.

The default threshold per order is ANV's, and each check may override it.

| Feature | Contract | Phase |
| --- | --- | --- |
| `curve_through`, `iso_curve`, `project`, `intersect`; curvature combs | Derived curves | 1 |
| Extruded, revolved, ruled and swept surfaces; `trim`, `sew`, `knit_to_solid` | Profile features with `solid: false` | 1 |
| `curve_cv`, `blend_curve`, `offset_curve`, `rebuild_curve` | Control-point NURBS, G0 to G3 bridges, offsets, refits with a bound | 2 |
| `boundary`, `fill`, `blend_surface`, `match`, `extend`, `offset_surface` | Network and n-sided surfaces, bridges and matches to G2 | 2 |
| `network(u, v, tol)` | Least-squares fit to a curve network with gaps up to `tol` | 3 |
| `edit_cv` with the drag fast path; G3 `match` and `blend_surface` | Control-point editing on the shared solver | 3 |

### Surface-quality checks

Every analysis (curvature, zebra stripes, highlight lines, continuity, draft, deviation, control-net quality) is a Field that the UI paints and checks constrain.

Class-A surfacing, the fairest visible surfaces of a product, is a loop of control-vertex edits under live zebra and curvature feedback. `edit_cv` therefore re-evaluates the dragged patch on the GPU at `Preview` fidelity within 16 ms (target), and the release of the drag writes one Ingot edit that rebuilds normally.

**Decision D-MEC-14:** Surface quality is a check library over analysis Fields plus a control-vertex drag fast path, not a mode, and capability statements say "surface-quality checks" until control-vertex editing and G3 matching and blending ship together in phase 3.
*Why:* checks let agents and continuous integration (CI) enforce surface quality as they enforce stress limits, and claiming Class-A before the modelling loop exists would overstate the product.
*Rejected:* a separate Class-A workbench (an island with its own rules); edits only through full rebuilds (too slow).

### SubD and scans

SubD cages (subdivision surfaces, smooth limit surfaces of a coarse polygon cage) are a `Body` representation edited through `anvil::subd_edit`, with gestures written to source. Rhino 8's `ToNURBS` output is G2 in smooth SubD regions and offers G0 to G2 at extraordinary vertices, warning that forcing G2 adds bulges or dents [Rhino ToNURBS].

**Decision D-MEC-15:** `to_nurbs` converts regular regions exactly, packs quad grids into larger patches by default, and defaults to G1 at extraordinary vertices with the deviation from the limit surface reported; G2 is an explicit option whose shape change is also reported.
*Why:* manufacturing and STEP exchange need NURBS, and the conversion must state what it changed.
*Rejected:* G2 by default (silently changes shape); SubD only (no path to AP242, the STEP protocol for exact geometry with semantic PMI).

A SubD body may join a B-rep part during design, and release converts it where the process needs B-rep. `scan_to_cad` registers scans with `anvil::align` and segments them by curvature or a learned segmenter. It fits primitives by deterministic RANSAC (random sample consensus) and faired NURBS elsewhere, and sews a solid with a deviation Field. Point2CAD reports a new state of the art on ABC with an implicit neural representation [Point2CAD]; Crucible stays analytic-first.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Continuity reports | Per-edge reports; G0 by edge tolerance, G1 to G3 by angle and relative curvature | `ContinuityNotMet { edge, achieved }` | MEC-O-SF-1 | 1 (G0 to G2), 2 (G3) |
| Basic curves and surfaces | Derived curves, profile surfaces, trim and sew | `Degenerate`; `BoundaryNotClosed { gap }` | MEC-O-SK-6, MEC-O-SF-2 | 1 |
| Freeform curves and surfaces | Bridges, offsets, refits; boundary, fill, blend and match to G2 | `NetworkNotCompatible { curves }` | MEC-O-SF-2 | 2 |
| Network fitting | Least squares with gaps up to `tol` | `ToleranceNotMet` | MEC-O-SF-2 | 3 |
| Surface-quality checks | Analysis Fields as checks | `Error(Failure)` on a missing analysis input | MEC-O-SF-1 | 2, 3 (highlight lines, control net) |
| Control-vertex editing | `edit_cv` with the 16 ms fast path; G3 matches | Fast path falls back to the rebuild | MEC-O-SF-5 | 3 |
| SubD modelling and conversion | Cage edits with stable names; `to_nurbs`. Requires: ANV `anvil::subd_edit` | `NonManifoldResult`; `ConversionDeviation { max }` | MEC-O-SF-3 | 3 |
| Scan to CAD | Registration to sewn solid | `FitFailed { residual }`; `NotConverged { rms }` | MEC-O-SF-4 | 4 |

## Sheet metal

Sheet-metal parts are designed folded and made flat, so the model keeps both states and the shop's bending rules in one record.

A sheet-metal part is a `SheetBody`: the folded `Body`, the flat `Body`, a bend table and its `SheetParams`. Every feature updates both states, as in Onshape, where sheet-metal operations are automatically represented as a flat pattern [Onshape sheet metal].

**Decision D-MEC-16:** The flat pattern is maintained by every sheet-metal feature, not computed at the end.
*Why:* designers see flat-pattern errors at the feature that causes them, and a cut drawn flat maps back through the same fold map.
*Rejected:* an unfold feature at the end of history (errors appear late and far from their cause).

```
pub record SheetParams {
    material: Material, thickness: Tol<Length>, inside_radius: Length,
    relief: ReliefRule, bend_rule: BendRule, min_flange: Length,
}
```

A `SheetStyle` is a shop's data package of `SheetParams` rows keyed by material and gauge. `sheet_from(profile, style: shop::al5052_2mm)` reads its row, so a part never restates its shop's radius, relief and bend rule. `check::sheet` reports the style it applied.

The neutral fibre lies at K·t from the inside surface. For bend angle θ, inside radius R and thickness t, the bend allowance is BA = θ·(R + K·t). The outside setback is OSSB = (R + t)·tan(θ/2), and the bend deduction BD = 2·OSSB − BA. `BendRule` is `KFactor(k)`, `Allowance(table)`, `Deduction(table)` or `Table(BendTable)`.

The neutral fibre moves inward as R/t falls. The default rule therefore reads K from MFG's press-brake allowance data indexed by R/t, in phase 2 ([contract 13.4](../contract.md)). Onshape's constants (0.45 for bends, 0.5 for rolled walls) are only a labelled fallback, and the bend table prints each bend's K.

| Feature | Contract | Phase |
| --- | --- | --- |
| `sheet_from`, `contour_flange`, `convert_to_sheet` | Base from a profile or path; a converted solid with rips | 2 |
| `flange`, `miter_flange`, `hem`, `jog`, `sketched_bend` | Flanges with length and position rules; hems | 2 |
| `corner`, `bend_relief` | Closed corners; rectangular, obround and tear reliefs | 2 |
| `in_flat { … }` | Features drawn flat, mapped through the fold map | 2 |
| `form(tool, at, orient)` | Louvres, lances, dimples, beads, extruded holes | 2 |
| `make_joint`, `make_rip` | Convert between bend and rip | 2 |
| `lofted_bend`, `tab_slot` | Transitions with stated deviation; tabs and slots | 3 |

`flat(sheet)` returns a `FlatPattern` with outline, `BendLine`s, footprints and grain, which MFG's bend sheets read. `export_flat_dxf` maps it onto layer conventions held as data, through ECO's DXF writer.

`check::sheet` checks inside radius and flange length against MFG tooling data. It flags features closer than 2·t + R to a bend, missing reliefs, flat self-overlap and bends across the grain.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Sheet model and bend rules | `SheetBody`; K factor, allowance, deduction and table rules; default K by R/t | `OutsideBendTable { key, range }` | MEC-O-SM-1 | 2 |
| Sheet styles | `SheetParams` and `SheetStyle` rows by material and gauge | `StyleRowMissing { material, gauge }` | MEC-O-SM-1 | 2 |
| Sheet features | Features above, both states updated | `FlangeCollides { faces }`, `UnfoldFailed { bend, reason }` | MEC-O-SM-2 | 2, 3 |
| Flat pattern | `flat(sheet)` through `anvil::unfold`. Requires: ANV `anvil::unfold`, `anvil::fold` | `NotDevelopable { faces, deviation }` | MEC-O-SM-2 | 2 |
| Flat DXF export | Layer conventions as data | `UnmappedLayer { kind }` | MEC-O-SM-4 | 2 |
| Self-clinching hardware | Catalog data and installation checks | `ClinchRuleViolated { rule, value, limit }` | MEC-O-SM-4 | 2 |
| Sheet checks | `check::sheet` with the applied style | Findings with fixes | MEC-O-SM-3 | 2 |

## Weldments and structural frames

Welded frames are built from standard sections along a skeleton, and their welds carry the quality requirements that inspection and structural checks read.

```
pub feature base_frame() -> Part {
    let sk = sketch3d() { … }                                   // skeleton lines
    let t  = member(sk.edges(role: any), profile: en10365::section("HEA 120")) |> trim(corners: Corner::Miter, gap: 1mm)
    let w  = weld(t.joints(any), Weld::fillet(a: 4mm, all_around: true, quality: Iso5817(C)))
    part(t, name: "Base frame", item: "FRM-0300", execution_class: Exc2).welds(w)
}
```

Members record profile, anchor and rotation, so Flux models them as beams on `anvil::member_axes`. Welds carry semantics to MFG and Flux, and neither needs bead geometry. Onshape's Frame feature offers the same skeleton approach with miter, butt and coped corners and a cut list [Onshape frame]. Crucible adds weld quality levels and execution classes that inspection reads.

A `Weld` records type, size, length, pitch, process, contour, finish and the imperfection quality level. The level is ISO 5817 B, C or D or the AWS D1.1 acceptance criteria, and it feeds inspection plans. A weldment Part records `execution_class: Exc1..Exc4` from EN 1090-2:2018+A1:2024. MFG derives the extent of non-destructive testing and the applicable part of ISO 3834 from it. It checks each `Weld`'s quality level against the class and enforces it for GP8 in phase 5.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Structural members | Profiles swept along skeleton segments; axes for Flux beams | `ProfileNotFound { designation, near }` | MEC-O-WD-1 | 2 |
| Profile catalogs | EN 10365:2026, EN 10210-2:2019, EN 10219-2:2019; AISC Shapes Database v16.0; licensed data | `UnknownSize { series, near }` when no package is pinned | MEC-O-WD-1 | 2 |
| Trims, gussets, end caps | Miter, butt and coped trims with weld gap; plates at joints | `TrimAmbiguous { joint }`; `NoRoom { joint }` | MEC-O-WD-2 | 2 |
| Weld beads | `Weld` records; `Cosmetic` by default, `Simplified` beads for mass | `WeldPathOpen`, `SizeExceedsThroat` | MEC-O-WD-3 | 2 |
| Weld symbols | AWS A2.4:2020 or ISO 2553:2019 | Missing fields for the standard | MEC-O-WD-3 | 2 |
| Execution class | `execution_class` on weldment Parts | Missing class on a structural weldment (warning) | MEC-O-WD-3 | 2 |
| Cut list | Bodies grouped by profile, length, end angles and features | Mixed materials in one group | MEC-O-WD-2 | 2 |

## Composites design

Laminated parts are defined by their plies rather than by a solid, so the laminate is the design and the solid derives from it.

A composite Part is a tool surface plus a laminate definition. MEC owns composite laminates in phase 4: zone-based plies, kinematic draping and laminate properties ([contract 13.4](../contract.md)). COV owns constitutive draping and cure simulation in phase 5.

```
let lam = laminate(tool: skin.faces(role: outer_mold_line), rosette: rosette(origin: skin.csys("root"), zero: x), plies: [
    ply("P1", carbon_t700_twill, 0deg,  boundary: full),
    ply("P2", carbon_t700_ud,    45deg, boundary: zone_a, drop_off: 3mm),
], symmetric: true)
```

Kinematic draping follows the method Creo documents [Creo draping]. Inextensible fibres cross at drape points a constant step apart, and a seed point and two fixed fibres fix the solution.

**Decision D-MEC-17:** Kinematic draping is the default for design, labelled as a geometric approximation that ignores material mechanics, and ply checks flag shear above the locking angle stored in the `Material`.
*Why:* it is fast enough for interactive design and is the method Creo documents, while forming simulation needs calibrated material models many users lack.
*Rejected:* forming simulation by default (slow, and it needs calibrated data).

Laminate rules are checks on the laminate: symmetry and balance, drop-off spacing, and the largest number of consecutive plies at one angle. Flux's ply-shape, ply-drop and stacking optimization reads the same rules as its constraints, in phase 6 for GP10's wing box. An optimized laminate therefore passes the checks a hand-written one must ([FLX](03-flux.md)).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Plies, sequences and zones | Plies with boundary, splice and dart; zones; symmetry and balance | `UnbalancedLaminate { zone }` (warning) | MEC-O-CP-2 | 4 |
| Rosettes and cores | Translation, radial, cylindrical or Field rosettes; honeycomb and foam cores | `ResolveError` on the rosette frame | MEC-O-CP-1 | 4 |
| Kinematic drape | Fibre directions and shear as Fields per ply. Requires: ANV `anvil::drape_kinematic` | `ExcessiveShear { region, angle }` with "add dart" | MEC-O-CP-1 | 4 |
| Solids and ply flats | Tool surface offset by ply thickness with drop-offs; flat ply outlines | `SelfIntersecting` | MEC-O-CP-1 | 4 |
| Laminate properties | Per-zone ABD matrices (the laminate's in-plane, coupling and bending stiffness) for Flux shells | `UndefinedZone { region }` | MEC-O-CP-2 | 4 |
| Laminate rules | Drop-off spacing, consecutive plies, symmetry and balance as checks read by ply optimization | Findings with the offending plies | MEC-O-CP-2 | 4 |
| Ply book and exchange | Per-ply views, sequence tables; AP242 composites per the CAx Implementor Forum (CAx-IF) Recommended Practices for Composite Materials v4.4 | Unmappable items reported | MEC-O-CP-2 | 4 |

## Molded and cast part design

Moulded and cast parts fail on wall thickness, draft and undercuts long before simulation, so their design rules are checks that run on every edit.

**Decision D-MEC-18:** Wall thickness is measured by two methods, ray thickness and rolling-ball thickness (the largest inscribed sphere), both as Fields; GPU results only order work and seed upper bounds, and the CPU proves the minimum by branch-and-bound with certified lower bounds, so the Fields have grade `Certified`.
*Why:* a ray from a rib root can miss the thick junction that the sphere measures, while rays match caliper readings, and a minimum is global, so GPU candidates alone could miss a region.
*Rejected:* a single method (each misleads in known cases); GPU candidate sets as the search space (results would depend on the GPU).

The reported location is the canonically first point within the decision band, by canonical face number, then (u, v) on a fixed dyadic grid.

`check::molding_design` has defaults that MFG data override. Ribs are at most 60% of the adjoining wall, where moulders' guides give 40 to 60% [RJC Mold ribs]; bosses are about twice the inner diameter; draft is 0.5° plus the texture allowance. Fill, pack, cooling and warpage are MFG's in phase 3, and casting simulation in phase 6 ([contract 13.4](../contract.md)).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Draft analysis | `draft_angle(body, pull) -> Field<Faces, Angle>` with classes | `SingularPoint` where the normal is undefined | MEC-O-PF-6 | 1 |
| Wall thickness | `thickness(body, method) -> Field<Body, Length>`, `Certified`. Requires: ANV `anvil::thickness` | `WorkLimit` | MEC-O-MD-1 | 1 |
| Parting line and surface | Lines ranked by undercut area; extended, ruled or swept surfaces; shut-offs | `NoParting { reason }` | MEC-O-MD-2 | 3 |
| Core, cavity and side actions | `split_mold(body, shrink, parting, block)`; lifter and slide directions | `NegativeDraft { faces }` | MEC-O-MD-2 | 3 |
| Ribs, bosses, snap fits | Parametric features with ratio rules | `RatioExceeded { rule }` (warning) | MEC-O-MD-1 | 3 |
| Shrinkage and compensation | Anisotropic scale, or `deform(field)` from a warpage Field | `ToleranceNotMet { achieved }` | MEC-O-PF-10 | 3 |
| Cast parts | Machining stock, cores, draft and minimum section | `SectionTooThin { region }` | MEC-O-MD-1 | 4 |

## Routing

Tubes, hoses, harnesses and pipes run through the space between parts, so routing is 3D geometry constrained by the assembly around it.

A `Route` is a 3D path between two ports, a `RouteSpec`, placed fittings and segment bodies. Ports are `CoordSys` values with a connection type, and route points are 3D-sketch unknowns constrained to clearances, supports and orthogonal runs. Automatic routing runs A* search over a voxel grid of free space and smooths the path into the specification's bend rules.

**Decision D-MEC-26:** Harness work splits three ways: MEC owns 3D routing, bundle and formboard geometry, ELX owns connectivity and wire tables, and MFG owns the manufacturing package; phase 3 routes use declared bundle diameters, and from phase 4 diameters come from ELX's wire list.
*Why:* each tab owns what it computes, and one owner for the formboard geometry keeps a single source for branch lengths.
*Rejected:* MEC owning the formboard drawing (a manufacturing document); ELX flattening MEC's 3D topology (geometry belongs with the routes).

ELX's harness section walks one harness through all five steps, from connectivity to the manufacturing package ([ELX](08-electronics-systems.md)).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Route model and tubes | Ports, specs, fittings, segment bodies; bend radius, straights, springback | `NoRoute { blocked_by }`; `BendTooTight { at, radius, min }` | MEC-O-RT-1 | 3 |
| Hose | Minimum bend radius; free shape from Flux's rod statics | `BendTooTight` | MEC-O-RT-1 | 3, 4 (free shape) |
| Harness bundles | Branches, clips, grommets; declared diameters, then ELX wire lists | `SupportSpacingExceeded { span }` | MEC-O-RT-1 | 3, 4 |
| Bundle shape | Cosserat-rod centreline (`flux::solve_rod`) | `NonlinearDiverged` with the last state | MEC-O-RT-1 | 4 |
| Formboard geometry and lengths | Branches at true length; 3D lengths with service loops | `FormboardOverlap { branches }` | MEC-O-RT-3 | 4 |
| Rigid pipe and heating, ventilation and air-conditioning duct | Fittings and schedules from licensed data (ASME B36.10M and B36.19M, EN 10220, SMACNA), each package recording its edition | `FittingNotInSpec { size }` | MEC-O-RT-2 | 5 |

## Large structures, micro scale and soft goods

The scale requirement, from MEMS to ships, is met by composition: members, sheets, surfacing checks, flattening and Field-driven geometry.

Building products exchange with building information modelling (BIM) tools through IFC, the Industry Foundation Classes.

| Domain | Native in std | Interop | Phase |
| --- | --- | --- | --- |
| Steel structures | Building-scale members, bolted plates, member Fields from Flux beams | IFC 4.3 (ISO 16739-1:2024) | 5 (GP8) |
| Plates and stiffened panels | Sheets with thickness Fields; stiffeners as members | AP242 | 5 |
| MEMS layer stacks | `process_stack(layers)`: deposit, pattern, etch, release | Masks on `anvil-planar`; the chip-layout formats GDSII and OASIS through ECO | 5 (GP7) |
| Ship hulls | Fairness checks; displacement, centres and waterplane | Offsets tables | 7 (GP13) |
| Building structure | Steel and timber members, not BIM authoring; IFC 4.3 is the latest official version | IFC exchange | 7 (GP14) |
| Soft goods | Flattened pattern pieces with seams, notches, grain lines and stretch ratios | DXF patterns | 7 (GP16) |

Patterns and `wrap` share Boundary First Flattening through `anvil::parameterize`, whose authors report a cost about 50 times lower than prior boundary-controlled methods [Sawhney and Crane 2017].

**Decision D-MEC-19:** Large structures, MEMS and soft goods arrive in phases 5 to 7 with GP7, GP8, GP13, GP14 and GP16, reusing MEC mechanisms plus a few domain features.
*Why:* the scale requirement is met by composition, and golden products 1 to 6 need none of these domains.
*Rejected:* dedicated workbenches per domain now (they would dilute phases 1 to 4).

Out of reach, stated plainly: Crucible does not replace naval architecture suites for class approval, BIM authoring or technology computer-aided design (TCAD) process simulators. It exchanges with them through open formats.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Steel structures and panels | Members, bolted plates, stiffened sheets; IFC 4.3 round trip | `UnmappedEntity { kind }` | MEC-O-LS-2 | 5 |
| MEMS layer stacks | `process_stack` builds Bodies from layer operations | `LayerUndercut { layer, region }` | MEC-O-LS-4 | 5 |
| Hull fairing and hydrostatics | Fairness checks; hydrostatic properties | `HullNotClosed { gaps }` | MEC-O-LS-1 | 7 |
| Soft-goods patterns | Flattened pieces with seams and stretch ratios | `NotDisk { genus }` with cut suggestions | MEC-O-LS-3 | 7 |

## Tolerancing

A part is made to its tolerances, not to its nominal shape, so tolerances are typed values in source that drawings, stack-ups, inspection and manufacturing all read.

### Specification model

Size tolerances are `Tol<T>` values, and `fit(10mm, H7)` returns one from `std::standards::iso286`. Geometric tolerances are records attached to shape aspects, one per feature control frame, and both dialects share them.

```
pub record GeometricTolerance {
    characteristic: Characteristic,
    zone: Zone,                        // width, shape, disposition: uniform, unequal or projected
    segments: [Segment],               // composite and multi-segment frames
    modifiers: [Modifier],             // a closed list per dialect (Reference)
    datums: Option<DatumSystem>,       // primary, secondary, tertiary; optional customized frame
    pattern: Option<PatternSpec>,      // CZ, CZR, SZ or SIM; ASME simultaneous unless separate: true
    indicators: [PlaneIndicator],      // intersection, orientation, direction-feature and collection planes
    size: Option<SizeSpec>,            // TwoPoint, LeastSquares, MaxInscribed, MinCircumscribed, Rank(..); envelope
    association: Option<Association>,  // ISO: how the toleranced feature is fitted before evaluation
    filter: Option<FilterSpec>,        // ISO: filter type and cut-off
    parameter: Option<Parameter>,      // ISO: total, peak, valley or standard deviation
    target: Query<ShapeAspect<Any>>,   // a face set, a feature of size, a pattern, or all over
}
```

The last three fields matter at the measuring machine. Under ISO 8015's independency principle, the specification operator decides what value is measured, so the ISO dialect records the association, filter and parameter, each defaulting to the dialect's default operator. The Reference section lists every `Modifier` with its AP242 value.

A shape aspect is an identified portion of a Body's boundary, named after AP242's `shape_aspect`. MEC owns the one closed list of kinds, by the surface classes that classify how many rigid motions leave a surface unchanged [Homri, Teissandier and Ballu 2015]:

| Kind | Motions that leave it unchanged | Size applies | Typical source |
| --- | --- | --- | --- |
| `Planar` | 3 | Two opposed planes (a width) | Extrusion caps, milled faces |
| `Cylindrical` | 2 | Diameter | Holes, pins, bores |
| `Spherical` | 3 | Diameter | Ball ends |
| `Helical` | 1 (a screw motion) | No | Threads |
| `Prismatic` | 1 | No | Sides of an extruded profile |
| `Revolute` | 1 | No | Revolved profiles |
| `Complex` | 0 | No | Freeform faces |
| `Pattern<K>` | As its members | As its members | Hole patterns |
| `Any` | Unknown until classified | No | Recognized imports |

Kinds with a size carry the `OfSize` marker, which ING's compile-time GD&T rules read, so a size control on a `Prismatic` aspect fails to compile ([ING](01-ingot.md)).

```
let a = datum("A", plate.face(role: start_cap))
let b = datum("B", plate.face(role: side(outline.left)))
let c = datum("C", plate.aspect(created_by: locating_pin_hole))
plate.general_tolerance(GeneralTolerance::iso2768("m"))
     .tolerance(plate.aspects(created_by: mount_holes), position(dia(0.1mm), mmc, datums: [a, b, c.at(mmb)]))
     .tolerance(plate.faces(all), profile(0.2mm, datums: [a, b, c]))
```

`Characteristic` covers form, orientation, location, profile and runout, plus concentricity, coaxiality and symmetry in the ISO dialect only. ASME Y14.5-2018 deleted concentricity and symmetry and added the dynamic profile modifier, which controls form but not size [GD&T Seminars Y14.5-2018]. ING turns the commonest misuses into compile errors.

A `Datum` may list `DatumTarget { kind: Point | Line | Area(shape), movable }` entries for castings and sheet metal. Edges of undefined shape carry ISO 13715:2017 callouts, which MFG reads for edge breaks.

A `Tol` forwarded into a feature becomes PMI as an anchored aspect query keyed by the realizing feature's `CallSite`, re-resolved on the final Part ([contract 5.1](../contract.md)). For `extrude(4mm ± 0.1mm)` the query is `OfSize { faces: [start_cap, end_cap] }`. ING decides how arithmetic on a forwarded `Tol` behaves before it reaches the realizing feature.

**Decision D-MEC-27:** Every PMI item, forwarded or explicit, has an `Error`-severity check `pmi_target_resolved`, and no GD&T or PMI item travels through operations as an attribute; when a later operation splits, merges or deletes a target, the check fails with `ToleranceTargetSplit { control, pieces }` or the `ResolveError`, and its fixes re-target the pieces as one pattern, select one piece, or insert an explicit `part.tolerance(…)` for a forwarded item.
*Why:* copying the control would silently turn one zone into several, and a forwarded tolerance has no control statement that could fail instead.
*Rejected:* copying the control to every piece (silent change of meaning); dropping it (loses the requirement); dividing the zone (meaningless for zones); a Note for forwarded items (the tolerance would vanish from the drawing).

ANV writes the resolved targets into the definition, and MEC owns the failure.

**Decision D-MEC-35:** A Part declares its general tolerance with `part.general_tolerance(spec)`: an ISO 2768-1:1989 class, an ISO 22081:2021 general specification, or ASME title-block decimal rules; stack-ups, characteristic extraction, inspection plans, cost and KLN's definition tolerance read it for every untoleranced size, location and angle, reports label those contributors "general", and a Part without one fails `check::standards` before release.
*Why:* most dimensions carry no explicit tolerance, and counting them as exact understates every stack.
*Rejected:* a drawing-only note (stacks and inspection never see it); a silent default class (the requirement must be written).

The record applies at the tolerancing layer, so Ingot arithmetic is unchanged. ISO 2768-2 is withdrawn in favour of ISO 22081.

### Geometry at a point of the zone

Geometry is built at nominal, but a shop machines to the middle of a fit's zone, and a press fit only interferes away from nominal. An Evaluation can therefore build every size at a stated point of its zone.

**Decision D-MEC-40:** An Evaluation may build geometry at a stated point of every size tolerance, `realize: Nominal | Mid | Upper | Lower | Mmc | Lmc` (default `Nominal`, with `Mmc` and `Lmc` the maximum and least material conditions), through ING's literal overrides of every `Tol` site; `Mmc` and `Lmc` take their side from the site's aspect kind, PMI, Item definitions and released check verdicts always come from the nominal Evaluation, and every export records the point it used.
*Why:* a fitted hole built at nominal puts the shop's STEP file at the edge of its zone, and interference at nominal reads a press fit as touching; Creo regenerates a model at upper, middle or lower bounds for the same reason [Creo dimension bounds].
*Rejected:* geometry always at nominal (an H7 bore exported at its lower limit); a separate manufacturing model (two geometries that drift); bound settings stored in the model outside source (state a review cannot see).

At `Mmc` a hole is built at its smallest size and a pin at its largest. Entity names exclude argument values, so every face keeps its name at every point of the zone. MFG's process hand-off chooses the point, `Mid` for machining by default, and `interference` and `min_clearance` accept it.

### Two dialects, one model

**Decision D-MEC-20:** GD&T has one semantic model with two dialects, ASME and ISO GPS (geometrical product specification), each a validator, a renderer and a default specification operator, and a design declares its dialect; `gdt::convert_dialect` translates only controls with an exact equivalent, and every other control becomes a typed hole (`ing/6001`) stating the reason and clause.
*Why:* ASME's size tolerance also controls form, while ISO 8015 meets each tolerance independently [Keyence GD&T basics], so approximate translation would manufacture to the wrong requirement.
*Rejected:* two models (every control written twice); approximate conversion; a default dialect by locale.

| Dialect default | ASME | ISO |
| --- | --- | --- |
| Standards | Y14.5-2018, reaffirmed in 2024 and on stabilized maintenance [ASME Y14.5] | ISO 1101:2017, 5459:2024, 5458:2018, 2692:2021, 14405-1:2025, 8015:2011, 22081:2021 |
| Regular feature of size | Envelope at maximum material (Rule #1, Y14.5-2018 section 5.8.1 [GD&T Basics Rule 1]) unless independency is noted | Two-point size without form limitation unless Ⓔ |
| Material requirements | Modifiers on features of size | Maximum and least material requirements and reciprocity (ISO 2692) |
| Pattern zones | Simultaneous unless `separate: true` | Combined (CZ) or simultaneous (SIM) zones only when written (ISO 5458) |

Validation checks modifiers, datum references and material conditions against the characteristic and the feature of size. A failure returns `InvalidControl { rule, clause }` with a fix such as "use position, profile or runout instead of concentricity".

ASME's mathematical definition, Y14.5.1-2019, is stated as consistent with the 1994 edition of Y14.5 [ASME Y14.5.1]. `std::mech::gdt::asme` therefore defines zone mathematics for each 2018-only construct, citing ISO 17450-1 operators where they apply, and reports mark these definitions `CrucibleDefined`.

### Completeness

**Decision D-MEC-21:** Specification completeness is a degree-of-freedom analysis on `anvil::analyze_constraints` plus three coverage rules: each toleranced aspect gets six small-displacement unknowns, minus those that leave its surface class unchanged, and coverage needs a size control on every feature of size, a form control on every surface and a precedence-suited form control on every datum feature.
*Why:* one diagnosis model finds under-specified directions automatically, and degrees of freedom alone would call a cylinder with position but no size complete.
*Rejected:* rule lists per aspect type (no geometric basis); degrees of freedom only.

Free unknowns show as arrows, and faces under a general tolerance or general profile count as controlled. Sigmetrix GD&T Advisor shows which features are completely, partially or not yet controlled [Sigmetrix GD&T Advisor]; MEC adds the geometric reason.

### Stack-up and variation analysis

A stack-up asks whether the variation of many dimensions still lets the assembly work. MEC runs stack-ups as checks, so a change that breaks one fails its merge.

| Method | Contract | Phase |
| --- | --- | --- |
| Worst case | Affine `Tol` sum over a closed, signed chain, general tolerances and GD&T zones included | 1 |
| RSS | ING's `.rss(coverage:)`, root sum of squares: the quantile of the linear combination, intersected with the worst case; Bender's 1.5 inflation as an option [Scholz 1995] | 1 |
| 1D sampling | Randomized quasi-Monte Carlo over contributor distributions | 1 |
| Fastener assemblability | Fixed and floating fastener conditions, with projected zones for tapped holes | 1 |
| 3D linear | Sensitivities of measurements to every aspect's small displacements | 2 |
| 3D zone path | Torsors per toleranced aspect, datums re-established, the mate system re-solved | 2 |
| 3D rebuild path | ING's `vary` over size tolerances that change topology or contact, rebuilt per sample | 2 |
| Compliant variation | The zone path plus Flux influence coefficients, for sheet-metal and welded assemblies | 2 |
| Tolerance allocation | Zone widths minimizing MFG cost at a target yield | 3 |
| Skin model shapes | Form deviations as `Field<Faces, Displacement>` | 4 |

A 1D chain takes GD&T directly. A position or profile zone of width t contributes ±t/2 along the chain direction. A maximum or least material condition (MMC, LMC) modifier adds the bonus tolerance, |size − MMC size|, as an affine term in the feature's own size symbol. The bonus then stays exactly correlated with the size contributor.

GP1's bolted joints need the everyday assemblability check in phase 1. Let H be the clearance hole's MMC size and F the fastener's MMC size. With clearance holes in both parts, the floating fastener condition gives each hole a position tolerance T = H − F [Open Exam Prep fasteners]. With a tapped hole in one part, the fixed fastener condition shares T₁ + T₂ = H − F between the two parts [GD&T Basics fixed fastener]. The tapped hole's zone is then projected through the mating part's thickness.

`check::fastening` computes both margins from the `HoleSpec`, `ThreadSpec` and position controls.

A torsor is the small rigid displacement (three rotations, three translations) by which a toleranced feature may deviate from nominal.

**Decision D-MEC-28:** MEC owns the default distribution for every statistical call, `std::mech::tol::default_distribution`: uniform within the limits when no process data exist, and normal with the mean shift and spread from Cp and Cpk (process capability indices) when an MFG process profile supplies them; for a zone with several parameters, uniform means uniform over the admissible torsor set, ING's `.rss()` and Flux's `std::uq::propagate` use it, and reports print what they assumed.
*Why:* without data a uniform distribution assumes least, and process data bring mean shift, which makes plain RSS unconservative.
*Rejected:* normal ±3σ without data (assumes a capable, centred process); one default per tab.

**Decision D-MEC-22:** 3D variation has two paths: the zone path, the default, samples small-displacement torsors per toleranced aspect, applies them to mating frames and contact features, re-establishes datums by the dialect's rule (ASME datum feature simulators, ISO 5459 association) and re-solves only the mate system, warm-started from nominal; the rebuild path uses ING's `vary` for size tolerances that change topology or contact.
*Why:* GD&T zones have no literal to override, and re-solving only mates meets the throughput target.
*Rejected:* a rebuild per sample for every tolerance (too slow); Jacobian-only analysis (misses float and contact switching); unseeded Monte Carlo; orders from names.

Both paths draw scrambled Sobol points in ING's name-free symbol order, seeded from argument values and input `GeometryId`s. Yields use smoothed indicators, and repeated scrambles give the statistical part of the error budget. Symbols that ING's order cannot tell apart are exchangeable, so ties give identical bits. Targets on the reference laptop: 20,000 zone-path samples of a 50-part stack in under 60 s, and 1,000 rebuild-path samples of GP3 in under 10 minutes.

Skin model shapes [Anwer et al. 2014] handle form deviations, and Flux consumes MEC's samples. Until phase 4, sampling displaces ideal features, with ASME's envelope bounding size and orientation jointly. Above 4,096 symbols, symbols below 10⁻⁶ of the form's radius fold into the remainder, and reports count them. Physics quantities under tolerances use FLX's `std::uq::worst_case`, which confirms its linear prediction with a solve at the worst vertex and states its bound and failure ([FLX](03-flux.md)).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| GD&T record and validation | `GeometricTolerance` with closed `Modifier` lists and ISO association, filter and parameter; datum systems and targets; dialect validators and renderers | `InvalidControl { rule, clause }`; `DatumUnderdefined { dof }` | MEC-O-TL-1, MEC-O-TL-6 | 1, 2 (datum targets) |
| Shape aspect kinds | One closed list with the `OfSize` marker | A control on the wrong kind fails to compile | MEC-O-TL-1 | 1 |
| PMI target check | `pmi_target_resolved` on forwarded and explicit PMI | `ToleranceTargetSplit { control, pieces }`; `ResolveError` | MEC-O-TL-6 | 1 |
| General tolerances and edge callouts | `general_tolerance`; ISO 13715 callouts | `check::standards` finding | MEC-O-TL-3, MEC-O-TL-7 | 1 |
| Geometry at a tolerance point | `realize:` on Evaluations, exports, `interference` and `min_clearance` | Non-size sites keep their nominal under `Mmc` and `Lmc` and are listed in the report (ING) | MEC-O-AS-3 | 1 |
| Dialect conversion | Exact equivalents; typed holes elsewhere; `CrucibleDefined` zones | `ing/6001` per untranslated control | MEC-O-TL-1 | 2 |
| Completeness | Degrees of freedom plus coverage rules | Free directions and uncovered aspects listed | MEC-O-TL-2, MEC-O-TL-7 | 2 |
| 1D stacks | Worst case, RSS at a stated coverage, 1D sampling; GD&T zones and MMC bonus as contributors | `ChainOpen` | MEC-O-TL-3, MEC-O-TL-9 | 1 |
| Fastener assemblability | Fixed and floating fastener margins; projected zones | Negative margin as a check finding | MEC-O-TL-9 | 1 |
| Default distributions | Process data or uniform, over torsor sets for zones | `ProcessDataStale { profile }` (warning) | MEC-O-TL-8 | 1 |
| 3D and compliant variation | Zone and rebuild paths with yields and contributors | `AssemblyFailed { sample }` counted, never dropped | MEC-O-TL-4 | 2 |
| Tolerance allocation | Zone widths at a target yield | `Infeasible { yield }` | MEC-O-TL-4 | 3 |
| Skin model shapes | Form samples as Fields | `ContactUnresolved { sample }` | MEC-O-TL-5 | 4 |

## Drawings and model-based definition

Shops still quote, machine and inspect from drawings, so drawings are generated from the same model and annotations as the 3D definition and can never disagree with it.

### One annotation model

**Decision D-MEC-23:** Semantic PMI lives on the model, and drawings and 3D saved views are two presentations of the same annotation items; drawing-only annotations are allowed, marked non-semantic and excluded from semantic export.
*Why:* one source of truth, and the standards allow both a model-only data set and a model plus a digital drawing [ISO 16792], with ASME Y14.41 covering annotated models with or without a sheet [ASME Y14.41].
*Rejected:* drawing-first annotation (not machine-readable); separate model-based annotations (two truths that drift).

Model-based definition (MBD) means the annotated 3D model is the authority, and a drawing is one view of it.

### Drawings

Drawings are Ingot programs, so they diff, merge and review like parts.

```
drawing(standard: Standard::iso(), title: "Bracket") {
    sheet(format: A3, scale: 1:1) {
        let front = view(p, orient: front, at: (120mm, 150mm))
        let aa    = section(front, cut: plane.offset(from: plane.yz, 30mm), label: "A")
        show_pmi(p, in: [front, aa])
        bom_table(p, at: top_right)
    }
}
```

Every drawing item references model entities by `Query`, as an extent use. An item that cannot re-resolve dangles with a `ResolveError` and never re-attaches elsewhere, and a release check forbids dangling items. `view.silhouette` and `view.section_edge` resolve view-dependent curves through the view's projection and fail when the silhouette disappears.

Title-block fields, revision text, dates and approvers are late-bound release fields, which enter the Item's definition digest only as placeholders ([KLN](05-kiln-repo-plm.md)). Phase 1 reads item numbers and revision labels from release tags and the engineering BOM.

**Drafting conventions.** Every machined-part drawing carries the same conventions, and GP1's shop works from them. From phase 1, std generates:

- centre marks and centre lines from coaxial and cylindrical aspects;
- the conventional thread representation from `ThreadSpec` records in every view and section, per ISO 6410 and ASME Y14.6 in the dialect's drafting package [unverified: current editions];
- section hatching from the region's `Material` class, with a per-drawing override;
- break lines on broken views;
- ordinate, baseline and chain dimension sets, each in limit, plus–minus or basic display form.

**Lattice regions.** A view draws an implicit lattice region as its boundary, the region and its skin, computed exactly where they are B-rep leaves. It adds a lattice zone symbol and a note naming the cell family, cell size and thickness Field. Hidden lines run only on B-rep faces and the region boundary, and section views cut the lattice with `anvil::section` at the sheet's line resolution, so GP2's drawing stays readable.

**Two-dimensional sheets.** A drawing may hold 2D-only sheets: sketch geometry, layers as attributes, blocks as Ingot functions, hatches and dimensions. An imported DWG or DXF file becomes an editable drawing program through an import expression, as a STEP file does for 3D. DXF write of sheets and sections is phase 1, and DXF and DWG (AutoCAD's native drawing format) read and write are phase 2, through ECO's codecs ([ECO](11-interop-ecosystem.md)).

**Decision D-MEC-24:** Release drawings use certified hidden-line removal: projected silhouettes and visibility transitions lie within 0.01 mm on the sheet divided by the view scale, never coarser than a tenth of the drawing's tightest tolerance at model scale, and lines, circles and conics project exactly; editing shows a GPU preview that the certified result supersedes.
*Why:* silhouettes of NURBS and procedural faces have no exact NURBS form, so a drawing can promise a certified bound but not exactness, and one rule in sheet units serves a MEMS die at 100:1 and a hull at 1:200.
*Rejected:* "exact" hidden lines (an undeliverable claim); tessellated hidden lines for release (chordal error on the sheet); separate model-scale and sheet-scale bounds (they conflict on enlarged views).

**Decision D-MEC-36:** Editing a driving dimension on a drawing writes model source through UIX's ranked edit plans: a dimension that traces by provenance to exactly one literal writes it directly, as an `api` edit shown as a source diff, otherwise the UI offers ranked edit plans, and driven and reference dimensions refuse the edit and say why.
*Why:* every surface edits one program, and drawing items already reference the model by `Query`.
*Rejected:* read-only drawings (users expect driving dimensions to edit); a separate drawing geometry editor (two truths).

MFG's in-process drawings, the shape after each machining setup with its allowances, use this drawing library on the setup's hand-off body ([MFG](07-manufacturing.md)).

### Revisions, balloons and generated drawings

`revision_markers(drawing, from, to)` diffs annotations and views between releases, marks each changed item and fills the revision block. Drafting packages carry ASME Y14.35-2025, which defines the practices for revising drawings and associated documents [ASME Y14.35], and ISO practice.

Release drawings are PDF/A-2, conformance level u (ISO 19005-2:2011), which current viewers and validators read. PDF/A-4 (ISO 19005-4:2020) is an option, and the drafting package pins the choice.

Characteristic balloons draw the characteristic identities and labels that MFG allocates, beside item balloons tied to BOM lines. From phase 1, size, location, orientation, form and profile controls on GP1 and GP2 get them. Each release produces the ballooned PDF that external metrology reports against.

**Decision D-MEC-29:** Revision markers are computed from the release diff, never placed by hand, and characteristic balloons draw the labels MFG allocates, never numbering on their own.
*Why:* computed markers cannot miss a change, and one allocator keeps balloon numbers stable across revisions.
*Rejected:* hand-placed revision clouds (they miss changes); balloons numbered by sheet position (they change with layout).

`auto_drawing(part, template, rules)` deterministically writes an editable drawing program:

1. Select the fewest views that show every toleranced aspect, plus sections and details.
2. Place each PMI item where its target appears in true shape or as an edge.
3. Dimension untoleranced geometry from the datum system.
4. Lay out views and annotations with the `mech-drawing-layout` Wasm component.
5. Check that every PMI item appears exactly once.

### Model-based definition

Semantic PMI exports to STEP AP242 per the CAx-IF Recommended Practices for PMI v4.1 of June 2024, still the current version [CAx-IF practices]. Each item links to B-rep faces through `shape_aspect`. The practice reserves semantic PMI for exact geometry, so a control on facet faces exports as presentation only. `check::standards` flags it at design time, and ECO owns the AP242 reader and writer.

Before any export, `check::standards` runs `export_resolution` against the receiver profile that ANV's `exchange_form` uses: the receiver's tolerance and minimum feature size. It reports every entity below the minimum feature and every tolerant edge above the receiver's tolerance, so a shop's CAM never meets a sliver it treats as degenerate.

Targets: a drawing updates in under 1 s after its model rebuild, and certified hidden lines of a 1,000-part assembly view take under 30 s.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Sheets, title blocks and standards | Formats; late-bound fields; ISO 128 and ASME Y14 packages recording their editions; PDF, SVG and PDF/A-2u; DXF write of sheets and sections through ECO | `UnfilledField { field }` at output | MEC-O-DR-4 | 1 |
| Drafting conventions | Centre marks and lines; thread representation; hatching by material; break lines; ordinate, baseline and chain sets | Missing fields for the standard | MEC-O-DR-4 | 1 |
| Views and hidden lines | Base, projected, auxiliary and section views, details; certified hidden lines by the sheet-unit rule. Requires: ANV `anvil::silhouette`, `project_hlr`, `visibility` | `ResolveError` on a cut or detail anchor | MEC-O-DR-1 | 1 |
| Lattice regions in views | Boundary, zone symbol and note; struts cut in sections | `ResolveError` on the region | MEC-O-DR-9 | 1 |
| More views | Offset, aligned, removed and broken-out sections; broken and crop views; exploded, flat and ply views | As above | MEC-O-DR-1 | 2, 4 (ply views) |
| Dimensions and references | All dimension kinds by `Query`; silhouettes and section edges | Dangling item with `ResolveError` | MEC-O-DR-2 | 1 |
| Drawing edits | Driving dimensions write source | Driven and reference dimensions refuse with the reason | MEC-O-DR-2 | 1 |
| Callouts, symbols and tables | Holes, threads, GD&T, welds; surface texture (ISO 21920-1:2021, ASME Y14.36-2018); edge callouts; BOM, hole and general-tolerance tables | Missing fields for the standard | MEC-O-DR-4 | 1, 2 (welds) |
| Two-dimensional sheets | Sketch geometry, layers, blocks as functions, hatches; DWG and DXF imports as drawing programs | `UnmappedEntity { kind }` | MEC-O-DR-11 | 2 |
| Gear data tables | Gear record fields and measurement over pins or span | Missing record fields | MEC-O-PF-15 | 2 |
| Revision markers | `revision_markers` from release diffs | `NoBaseRelease` | MEC-O-DR-6 | 2 |
| Characteristic balloons | MFG's labels on its characteristic identities; ballooned PDF per release | `UnmappedCharacteristic { id }` | MEC-O-DR-7 | 1 (size, location, orientation, form, profile), 2 |
| Tabulated drawings and more tables | Family rows; bends, cut lists, plies | `RowFailed { key, error }` | MEC-O-DR-4 | 2 |
| Automatic drawings | Deterministic `auto_drawing` | `UnplacedItems { items }` | MEC-O-DR-5 | 3 |
| Saved views and AP242 PMI export | `model_view(…)`; CAx-IF PMI v4.1; eligibility per face | Facet targets exported as presentation, reported | MEC-O-DR-3, MEC-O-DR-8 | 1 |
| Export resolution | `export_resolution` against the receiver profile before any export | `NotRepresentable { entities, reason: BelowReceiverResolution }`; `Note::ToleranceAboveReceiver { edges }` | MEC-O-DR-10 | 1 |
| PMI import, QIF and data-set completeness | AP242 PMI into the model; QIF 3.0 (Quality Information Framework) through MFG; ASME Y14.41-2026 or ISO 16792:2021 | Unmappable or missing items listed | MEC-O-DR-3, MEC-O-DR-4 | 2 |

## Design checks

Design rules catch most defects before any simulation runs, so MEC packages them as checks that every merge evaluates and that agents optimize against.

Design checks are `require` predicates packaged as libraries, each returning a `Field` of margins with typed fixes. MFG owns process checks (design for manufacture, assembly and additive manufacture); MEC owns design-domain and standards checks, with one result type. Each check has a `CheckId`, so editing a limit keeps its verdict history, Evidence records and Waivers.

| Library | Example rules | Phase |
| --- | --- | --- |
| `check::standards` | Thread series; general tolerance present; GD&T validity, completeness and PMI eligibility; fallback regions; export resolution; drawing completeness | 1 |
| `check::enclosure` | Clearance to imported boards, keep-ins, connector cut-outs | 1, 2 |
| `check::fastening` | Fixed and floating fastener assemblability (phase 1); engagement, clearance class, preload range, wrench swing, approved parts (phase 2) | 1, 2 |
| `check::sheet`, `check::weld` | Sheet rules with MFG tooling minimums; weld access, symbols, quality levels, execution class | 2 |
| `check::assembly` | Clearance over motion, interference classes, interface compatibility, undeclared purchased mass | 1, 2 |
| `check::molding_design` | Draft, wall thickness, rib and boss ratios, undercuts | 3 |

**Decision D-MEC-25:** Design checks return graded Fields with numeric margins, not pass or fail flags.
*Why:* agents optimize against margins, and people see where a rule nearly fails.
*Rejected:* boolean rule results (no gradient for optimization and no early warning).

### What may decide a check

A check's verdict is only as good as the bound on the number it reads. Each mechanical check therefore states the weakest kind of bound it accepts.

**Decision D-MEC-30:** Every mechanical check declares `decides_on`, the weakest bound kind that may decide it: geometric checks (fits, clearance, interference, thickness, mass) need `Guaranteed` bounds, and physics checks accept at `SignOff` calibrated `Estimated` bounds from a named FLX class whose applicability envelope contains the result, confirmed by one further refinement; eigenvalue checks apply their bound on both sides, λ − η for lower limits and λ + η for upper limits and avoidance bands, except on fitted conforming discretizations with strongly imposed supports.
*Why:* Flux reports every estimate already multiplied by its class factor, so MEC states which checks rest on which classes, and an immersed discretization with weakly imposed supports can put an eigenvalue on either side of the exact one.
*Rejected:* `Guaranteed` bounds everywhere (no immersed stress check could pass in phase 1); any `Estimated` bound everywhere (a clearance would pass on an estimate); one-sided eigenvalue bounds on immersed models (a frequency could pass below its limit on a false premise).

Here η is the calibrated error bound Flux reports with an eigenvalue λ.

| Check family | `decides_on` | Calibration class (FLX) | Phase |
| --- | --- | --- | --- |
| Fits, clearance, interference, thickness, mass | `Guaranteed` | None needed | 1 |
| Static stress on regularized peaks in solids (GP1) | `Estimated` | `elasticity.peak`; `elasticity.peak.interactive` at `Interactive` | 1 |
| Strut strength in beam lattices (GP2) | `Estimated` | `lattice.strut_stress` | 1 |
| Buckling factors where elastic buckling governs | `Estimated`, two-sided, prestress error included | `lattice.buckling`; `elasticity.buckling` | 1 |
| Natural frequencies and avoidance bands | `Estimated`, two-sided | `elasticity.frequency` | 1 |
| Bolted joints | `Estimated` plus a policy allowance | Bolted-joint forms | 2 |

FLX owns these classes ([FLX](03-flux.md)). Each has 300 held-out samples, at least 20% from `std::opt` runs that minimize the check margin. Its references come from an independent code on fitted, curved high-order meshes ([contract 13.2](../contract.md)). Each `Estimated` part carries its exceedance level α, which joins the union bound, so every `Pass` reports its confidence. Peaks smooth over FLX's default radius from local curvature and thickness, so a 2 mm fillet is never averaged away.

A buckling factor depends on the prestress from the static solution. FLX therefore estimates it as a coupled goal, adding the static solve's error through the geometric stiffness with one extra adjoint solve. Frequencies, whose operator is fixed, use their own class, `elasticity.frequency`.

**Strut strength.** GP2's struts are stocky. A strut about 1 mm across and four diameters long has a slenderness λ near 16. For an aluminium alloy with E ≈ 70 GPa, its elastic buckling stress π²E/λ² is then near 2,700 MPa, far above any proportional limit. Compressive yield and plastic collapse govern, and an elastic eigenvalue decides almost nothing.

The strut-strength check compares each strut's localized axial stress with the as-built compressive strength, reduced by a Johnson–Perry–Robertson factor computed from the strut's measured waviness. It reads the `lattice.strut_stress` class, so it needs no new calibration. MFG's strut calibration coupons include compression tests of single struts at GP2's diameters, which supply the as-built strength ([MFG](07-manufacturing.md)). Eigen-buckling then runs only on members where elastic buckling governs, by COV's inelasticity ratio, and decides global lattice instability.

**Model form.** Discretization error is only one part of a check's budget; the other is how well the physics model matches the real part. Before the phase 1 run build is tagged, a validation campaign on separate specimens bounds the model-form error of two models ([contract 13.1](../contract.md)). They are immersed elasticity at regularized fillet peaks and the beam-lattice model for localized strut stress. Those bounds govern GP1's and GP2's releases.

Each GP1 and GP2 stress check also predicts its gauge functional, the strain averaged over the strain-gauge grid at the checked region. That is a bounded linear functional, whose bound can be `Guaranteed`. The proof loads on the made articles are then held-out confirmation, judged like for like. A check whose response quantity the campaign did not validate has a `NotQuantified` model-form part and returns `Undecided`, unless a policy allowance covers it. Phase 2 bolted-joint checks cite such an allowance from COV's catalogue.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Check libraries | Graded margin Fields with fixes; a `CheckId` per check | `Error(Failure)` on a missing input | MEC-O-CK-1, MEC-O-CK-2 | 1 to 3 |
| `decides_on` declarations | Bound kind and calibration class per check; envelope and refinement confirmation; two-sided eigenvalue bounds | `Undecided { needed }`; `Undecided { reason: CalibrationUnconfirmed }` | MEC-O-CK-3 | 1 |
| Strut strength and gauge functionals | Localized strut stress against as-built strength with a Johnson–Perry–Robertson factor; each stress check's gauge functional with its bound. Requires: FLX Beam-lattice models | `Undecided { reason: Unquantified(sources) }` | MEC-O-CK-4 | 1 |

## Human factors

Products are used by people, so std checks geometric reach, fit and vision against human models, and leaves strength and musculoskeletal loading to COV's biomechanics models.

Anthropometry follows ISO 7250-1:2017, and population datasets are licensed data packages.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Manikins | Kinematic chains with joint limits, scaled to a percentile or an individual | `DatasetMissing { population }` | MEC-O-HF-1 | 5 |
| Posture | Inverse kinematics on the shared solver with a comfort cost | `PostureInfeasible { target, limit }` | MEC-O-HF-1 | 5 |
| Reach, clearance and vision | Reach envelopes as Bodies; tool access; view cones | `TargetUnreachable { target }` | MEC-O-HF-1 | 5 |
| Posture scores | Methods such as RULA [McAtamney and Corlett 1993] as check libraries | `DatasetMissing { population }` | MEC-O-HF-1 | 5 |

## Reference

### Packages

`std::mech` re-exports the everyday features, so `use std::mech::{sketch, extrude, rib, fillet}` works as in contract section 6. Helpers follow ING's feature granularity rule.

| Package | Contents | First phase |
| --- | --- | --- |
| `std::mech::sketch` | 2D and 3D sketches, constraints, sketch edits, solve reports, text | 1 |
| `std::mech::part` | Part features, reference geometry, holes, patterns, direct edits, lattices, generative design | 1 |
| `std::mech::asm` | Instances and Instance sets, mates, kinematics, interference, contexts, fasteners | 1, 2 |
| `std::mech::gdt`, `std::mech::tol` | GD&T with dialects `asme` and `iso`; fits, general tolerances, stacks, variation | 1, 2 |
| `std::mech::drawing`, `std::mech::check` | Drawings and model-based definition; design and standards checks | 1 |
| `std::mech::machine`, `std::mech::surf` | Gears, shafts, springs, belts; freeform surfaces, SubD, scan to CAD | 2 |
| `std::mech::sheet`, `std::mech::weld` | Sheet metal and styles; members, trims, welds, cut lists | 2 |
| `std::mech::mold`, `std::mech::route` | Parting, core and cavity, ribs, bosses; tubes, hoses, harnesses, pipes | 3, 5 |
| `std::mech::composite`, `std::mech::human` | Plies, zones, drape, laminate rules; manikins, reach, vision, posture | 4, 5 |
| `std::standards::*` | Standard values computed from the standards' formulas | 1 |
| `crucible::standards::*` | Tabulated standard values under a `DataLicence` | 1 |

MEC adds no geometry type. `Part`, `Assembly`, `Instance`, `Transform` and `CoordSys` live in the crate `mech-model` in the geometry layer ([contract 12](../contract.md)).

| Type | What it is | Relation to core types |
| --- | --- | --- |
| `Sketch` | Wires and regions with constraints and a solve report | A `Body`; named entities are typed fields |
| `Profile`, `Path` | Closed sketch regions; a G0-connected edge chain | `Query`s over faces or edges |
| `CoordSys` | A right-handed frame anchored to geometry | A `Transform` plus an anchor `Query` |
| `Mate` | A typed constraint between frames on two Instances | Stored in the `Assembly` |
| `Context` | A past evaluation of an assembly at a pinned Change | Taken Bodies, frames and sketches in the consumer's frame |
| `HoleSpec`, `ThreadSpec`, `Weld`, `Ply` | Manufacturing intent | Definitional attributes by canonical entity number |
| `ShapeAspect<K>` | A portion of a Body's boundary for GD&T, of one closed kind | A `Query` over faces, typed by kind |
| `GeometricTolerance`, `Datum`, `GeneralTolerance` | GD&T controls, datums with targets, a Part's general tolerance | Definitional attributes |
| `Drawing`, `Sheet`, `View` | 2D documentation | Linework is 2D `Body` geometry |
| `Route` | A path with a specification and end ports | A `Path`, a `RouteSpec` and two `CoordSys` |
| `Detail`, `InstanceDetail` | How much geometry a feature or an Instance builds | A choice with a recorded `ErrorBound` |

### Identity of Parts and Assemblies

**Decision D-MEC-32:** A Part's `GeometryId` hashes the canonically ordered `GeometryId`s of its Bodies, never its name or item number, and an Assembly's `GeometryId` hashes its members sorted by (child `GeometryId`, placement), each with its mates by canonical entity number, without Instance names or paths.
*Why:* renaming an Instance must not change a revision's definition, while moving one must.
*Rejected:* the `ObjectId`, which includes names (renames would modify Items); children without placements (a moved bearing would be no change).

A placement is a unit quaternion plus a translation, in canonical f64 bits. The quaternion's first nonzero component in (w, x, y, z) order is positive, and −0.0 is written as +0.0, so a half-turn has one encoding. A mate encodes its kind, limits and both frames as (member index, anchor's canonical entity number). An Instance set contributes one member per key, a flexible subassembly its placements as solved in the parent, and `InstanceDetail` nothing.

KLN's definition tolerance, the geometry change below which an Item keeps its revision, reads the Part's tightest or general tolerance and its resolution ρ ([KLN](05-kiln-repo-plm.md)).

### WIT interface

MEC owns the WIT (WebAssembly Interface Types) package `crucible:product`, with KLN's Item metadata; it stays at `@0.1.0` until the freeze of contract 13.1.

| Interface | Contents | Failures |
| --- | --- | --- |
| `types` | Records for Parts, Assemblies, Instances and sets, transforms, mates, contexts, aspects, PMI and intent attributes | None: records only |
| `build` | `product-builder` over Anvil body handles; `finish` validates | `build-error`: unresolved reference, cycle, `invalid-control` |
| `read` | Structure, placements, PMI and definitional attributes for exporters | None: reads of a validated product |

### GD&T modifiers

Each `Modifier` is a closed enum per dialect. The AP242 column names the value of AP242's `geometric_tolerance_modifier` enumeration, or the entity that carries the concept [STEP Tools AP242 modifiers]. MFG maps the same values to QIF 3.0, and MEC-O-TL-1 checks that every value round-trips through both. The symbols follow ISO 1101:2017 and ASME Y14.5-2018 [unverified: the exact ISO 1101:2017 symbols].

| `Modifier` | Dialects | Meaning | AP242 |
| --- | --- | --- | --- |
| `Mmc` (Ⓜ) | Both | Maximum material requirement | `maximum_material_requirement` |
| `Lmc` (Ⓛ) | Both | Least material requirement | `least_material_requirement` |
| `Reciprocity` (Ⓡ) | ISO | Reciprocity requirement with Ⓜ or Ⓛ | `reciprocity_requirement` |
| `Projected { height }` (Ⓟ) | Both | Zone projected beyond the feature | `projected_zone_definition` on the zone [STEP Tools projected zone] |
| `Unequal { displacement }` (UZ) | Both | Zone offset from the true profile | `unequally_disposed_geometric_tolerance` [STEP Tools unequal zone] |
| `FreeState` (Ⓕ) | Both | Applies in the free state | `free_state` |
| `TangentPlane` (Ⓣ) | Both | Applies to the tangent plane | `tangent_plane` |
| `Statistical` (ST) | ASME | Statistical tolerance | `statistical_tolerance` |
| `DynamicProfile` (▷) | ASME | Controls form, not size | No enumeration value; ECO's mapping |
| `CommonZone` (CZ), `SeparateZones` (SZ) | ISO, with `pattern` | Combined or separate zones of a pattern | `common_zone`; `separate_requirement` |
| `UnitedFeature` (UF) | ISO | Several features treated as one | `united_feature` |
| `LineElement` (LE), `AnyCrossSection` (ACS) | ISO | Applies per line element or per cross-section | `line_element`; `any_cross_section` |
| `NotConvex` (NC) | ISO | Form zone without a convexity limit | `not_convex` |
| `EachRadialElement` | ASME | Applies to each radial element | `each_radial_element` |
| `MajorDiameter` (MD), `MinorDiameter` (LD), `PitchDiameter` (PD) | Both | Which thread diameter a control applies to | `major_diameter`; `minor_diameter`; `pitch_diameter` |
| `association` of the toleranced feature (minimax, least squares, maximum inscribed, minimum circumscribed, tangent) | ISO | How the feature is fitted before evaluation | `associated_minmax_feature`; `associated_least_square_feature`; `associated_maximum_inscribed_feature`; `associated_minimum_inscribed_feature`; `associated_tangent_feature` |
| Reference-feature association (minimax, least squares, inscribed, circumscribed, with or without material constraints) | ISO | How the reference feature is fitted | The eight `reference_…` values |
| `parameter` (total, peak, valley, standard deviation) | ISO | Which deviation value is evaluated | `total_range_deviations`; `peak_height`; `valley_depth`; `standard_deviation` |
| `filter` | ISO | Filter type and cut-off | No enumeration value; ECO's mapping |

### Wasm components

| Wasm component | Purpose | Phase |
| --- | --- | --- |
| `mech-lattice` | Cell-family generator emitting strut graphs or tapes for `anvil::lattice` | 1 |
| `mech-route-search`, `mech-drawing-layout`, `mech-explode-planner`, `mech-mate-ranker` | Route search, drawing layout, disassembly planning, learned mate ranking | 3 |
| `mech-scan-segmenter` | Learned point-cloud segmentation | 4 |

Learned Wasm components ship fixed weights and run deterministic CPU inference.

## State of the art

Figures in the last column are targets unless quoted.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Feature language | Standard features in the user-facing language | Onshape FeatureScript [Onshape FeatureScript] | All `std::mech` features in Ingot, by roles and provenance | Golden products built from std only |
| Code-CAD idioms | Text, hull, Minkowski sum and twisted extrusion as core operations | OpenSCAD [OpenSCAD cheat sheet] | Text and hull in phase 1; Minkowski sums and twisted extrusion in phase 2 | Every cheat-sheet idiom expressible |
| Sketch solving | Structural decomposition before numerical solving [Zou 2022] | Siemens D-Cubed 2D DCM, which Siemens calls the most widely adopted 2D constraint solver [Siemens 2D DCM]; FreeCAD planegcs [FreeCAD planegcs] | Decomposed blocks, Levenberg–Marquardt on `linalg`, Krawczyk bounds up to 128 unknowns | SketchGraphs replay [SketchGraphs]: 99.5% on the recorded branch |
| Sketch editing | Edits as constraint-aware rewrites | CADCraft's trim, extend, fillet and chamfer [CADCraft]; D-Cubed 2D DCM | Source rewrites that keep every untouched name | Held-out SketchGraphs edits keep freedom counts and roles |
| Constraint diagnosis | Exact witness configurations with Zou and Feng's corrections [Zou and Feng 2019] | D-Cubed diagnostics (not public) | Modular rank on rational witnesses, interval minors otherwise | Known-rank suite: 100% correct |
| Assembly solving | One system over SE(3) cluster unknowns on manifolds | Siemens D-Cubed 3D DCM [Siemens 3D DCM]; Onshape mate connectors | Shared solver; dynamics in Flux | Mobility counts; closed-form linkages; 1,000 mates in under 100 ms |
| Blends | Rolling-ball and setback vertex blends; law radii | Parasolid, which made every original in the corpus [ABC dataset]; OCCT's fillet builder [OCCT fillet] | ANV's staged program, with an opt-in implicit fallback | ANV's part-level benchmark per stage, with OCCT's rate on the same corpus |
| Direct editing | History-free edits keeping related geometry consistent | Siemens synchronous technology [Siemens synchronous technology] | Solver-based face motions, rules in source | 95% of held-out seeded edits succeed |
| Generative design | Density topology optimization with manufacturing constraints | Fusion generative design [Fusion generative methods] | `generate` with kept regions as exact B-rep leaves | Kept faces keep names, `HoleSpec`s and GD&T in every outcome |
| Sheet metal | Flat pattern maintained by every feature; per-bend tables | Onshape sheet metal [Onshape sheet metal] | Same model, K from R/t press-brake data, shop styles | Developed lengths equal closed forms to 10⁻⁹ relative |
| Surface quality | G2 and G3 analysis, zebra and highlight lines, live control-vertex feedback | Autodesk Alias [Alias Class-A]; CATIA ICEM Shape Design [ICEM brochure]; Plasticity xNURBS [Plasticity] | Analysis Fields, checks and the 16 ms drag path | Known-order surface pairs: zero misclassifications |
| SubD to NURBS | G2 regular regions, a choice at extraordinary vertices | Rhino 8 `ToNURBS` [Rhino ToNURBS]; OpenSubdiv [OpenSubdiv] | G1 default with reported deviation | Limits within 10⁻⁹ relative of OpenSubdiv |
| Scan to CAD | Hybrid analytic and neural fitting [Point2CAD] | Point2CAD | Analytic-first with intent snapping and NURBS | Synthetic scans: at least Point2CAD's reported accuracy |
| Draping | Kinematic fishnet draping | Creo Composite Design [Creo draping] | Deterministic kinematic drape | Hemisphere and cylinder shear within 0.5° |
| Flattening | Boundary First Flattening [Sawhney and Crane 2017] | BFF reference implementation | `anvil::parameterize` with BFF | Distortion and time within 10% of the reference |
| Mate inference | Learned joint prediction (JoinABLe, 79.53%, literature only) [JoinABLe] | JoinABLe | Optional Wasm ranker | Generated joint benchmark: 80% top-1 |
| GD&T coverage | Degrees of invariance per surface class (ISO 17450-1:2011) | Sigmetrix GD&T Advisor [Sigmetrix GD&T Advisor] | Degree-of-freedom analysis plus coverage rules | Seeded gaps: 100% found, no false findings |
| 3D tolerance analysis | Nonlinear sampling with assembly behaviour; skin model shapes [Anwer et al. 2014] [Schleich and Wartzack 2016] | Siemens Tecnomatix Variation Analysis [Tecnomatix VA] | Zone and rebuild paths, run as checks on every merge | 20,000 zone-path samples of 50 parts in under 60 s |
| Semantic PMI | AP242 semantic PMI with validation properties [CAx-IF PMI v4.1] | CATIA, NX, Creo and SOLIDWORKS on NIST test cases [NIST MBE PMI] | Native AP242 PMI, per-face eligibility | NIST CTC, FTC, STC and HTC: 100% of semantic items |
| Hidden-line removal | B-rep hidden lines on exact geometry, with a polygonal variant for speed | Open CASCADE `HLRBRep_Algo` and `HLRBRep_PolyAlgo` [OCCT modeling algorithms] | Certified for release by a sheet-unit bound, GPU preview | Silhouettes within the stated bound of high-precision references |
| Wall thickness | Ray and inscribed-sphere thickness | Autodesk Moldflow thickness diagnostics [Moldflow thickness]; Materialise Magics [Magics 2025] | Both `Certified` by branch-and-bound | Error under 1% on analytic parts; identical bits with or without a GPU |
| Gear geometry | ISO 21771-1:2024 with flank modifications | KISSsoft (ISO 21771 geometry, ISO 6336 ratings) [KISSsoft] | Exact Law-surface flanks plus semantics | Flank points against ISO 21771-1 formulas |
| Solver linear algebra | Rank-revealing QR and SVD per block | Eigen in planegcs; faer [faer] | Canonical `linalg`; faer only in `CpuIsa` | Bit identity across the canonical class; no slower than Eigen |

Deviations, stated: homotopy continuation finds all solutions, but editing needs one answer, so Crucible tracks the seeds' branch. OndselSolver is LGPL-2.1 and was archived on 1 March 2025, so it is a reference only [OndselSolver].

The parity table compares documented features, cited from vendor documentation, and is not a benchmark of any commercial product. AI-built clones appear where they ship a capability first.

| Capability | Incumbent and its documented feature | Crucible's capability row and phase | Verdict |
| --- | --- | --- | --- |
| Sketch solving and diagnosis | D-Cubed 2D DCM in many CAD systems [Siemens 2D DCM]; SolidCraft's own sketch solver [SolidCraft] | 2D sketch solve; Degree-of-freedom report; 1 | Ahead: certified positions and minimal conflict sets, with every edit in source |
| Sketch edits | CADCraft: trim, offset, fillet, chamfer, extend, arrays [CADCraft] | Sketch edits; 1 | Equal in tools; ahead because each edit is a reviewed rewrite that keeps names |
| Parametric part features | SolidCraft: extrude, revolve, sweep, loft, fillet, shell, draft, holes, threads, patterns [SolidCraft] | Profile features, dress-up features; 1, 2 (loft, general sweeps) | Later for lofts, which wait for general NURBS intersection; equal otherwise, with every fillet judged against Parasolid's results |
| Standard holes and threads | Onshape Hole: tapped, counterbore, countersink, fits Close, Free and Normal [Onshape hole] | Holes; Standards content; 1 | Equal: designations computed from formulas with nothing licensed installed |
| Configurations and families | Onshape configuration tables [Onshape configurations]; SOLIDWORKS configurations [SOLIDWORKS configurations] | Configurations and families; 1 | Ahead: variants are typed source that review diffs, and every row must pass |
| In-context design | Onshape context snapshots, updated only on request [Onshape in context]; Creo Copy and Publish Geometry [Creo copy geometry] | In-context design; 2 | Equal at phase 2: pinned snapshots, plus a Proposal diff whenever a pin moves |
| Mates and relations | Onshape mates with gear and rack-and-pinion relations [Onshape mates] | Mate solve and diagnosis; 1, 2 | Ahead in diagnosis: one solver for sketches and mates with minimal conflict sets |
| Path mates, belts and chains | SOLIDWORKS path mate and belt/chain assembly feature [unverified] | Path mates; 2. Belt and chain couplings; 3 | Later; closed-form oracles from the first release |
| Motion studies | SolidCraft joints and motion studies [SolidCraft] | Kinematics and motion studies; 2 | Later than the clone; ahead because clearance between samples is bounded, not sampled |
| Direct editing | Siemens synchronous technology [Siemens synchronous technology] | Push-pull; 1. Move, replace and delete faces; 2 | Equal at phase 2, with every recognized rule written to source |
| Sheet metal | Onshape sheet metal with a maintained flat [Onshape sheet metal]; SolidCraft flanges and flat patterns [SolidCraft] | Sheet features; Sheet styles; 2 | Later than the clone; ahead in K from R/t data and shop styles checked on every merge |
| Weldments and frames | Onshape Frame: miter, butt and coped corners, cut list [Onshape frame] | Structural members; Trims; Cut list; 2 | Equal, plus weld quality levels and execution classes that inspection reads |
| Generative design | Fusion: unrestricted, additive, 2.5- to 5-axis milling, 2-axis cutting, casting [Fusion generative methods] | Generative design; 1 (additive, unrestricted), 2 (milling, cutting, casting) | Ahead: kept interfaces stay exact and toleranced, and every outcome passes the design's checks |
| Reference images | Fusion canvas with calibration [Fusion canvas] | Reference images; 2 | Later |
| Geometry at tolerance bounds | Creo dimension bounds: upper, middle, lower, nominal [Creo dimension bounds] | Geometry at a tolerance point; 1 | Equal, plus `Mmc` and `Lmc` by aspect kind and the point recorded in every export |
| Tolerancing completeness | Sigmetrix GD&T Advisor [Sigmetrix GD&T Advisor] | Completeness; 2 | Equal, plus the geometric reason for each free direction |
| 3D tolerance analysis | Tecnomatix Variation Analysis [Tecnomatix VA] | 3D and compliant variation; 2 | Ahead: stack-ups are checks on every merge, on the drawing's own tolerances |
| Semantic PMI export | Major CAD systems on NIST PMI test cases [NIST MBE PMI] | Saved views and AP242 PMI export; 1 | Equal (target: 100% of semantic items) |
| Class-A surfacing | Alias and ICEM control-vertex modelling [Alias Class-A] [ICEM brochure] | Control-vertex editing; 3 | Later |
| SubD | Rhino `ToNURBS` [Rhino ToNURBS] | SubD modelling and conversion; 3 | Later; every conversion states its deviation |
| Composite plies | Creo draping simulation [Creo draping] | Kinematic drape; Plies; 4 | Equal |
| Moulded part thickness | Moldflow thickness diagnostics [Moldflow thickness] | Wall thickness; 1 | Ahead: the minimum is certified, identical with or without a GPU |
| Gear geometry | KISSsoft gear geometry [KISSsoft] | Gears; 2 | Equal geometry with exact flanks; ratings are COV's |
| 2D drafting and DWG | CADCraft DWG and DXF through acadrust [CADCraft] | Two-dimensional sheets; 2 | Equal at phase 2; DXF write of sheets from phase 1 |
| Agent control | SolidCraft's Model Context Protocol (MCP) server [SolidCraft] | Typed failures and fixes; std features as agent tools; 1 | Ahead: every agent edit is a Proposal that passes the design's checks before review |

## Platform notes

- **Numerics.** Residuals use `detmath` and solver algebra uses `linalg` without FMA (fused multiply-add) ([contract 7.3](../contract.md)), so solves are bit-identical across the canonical platform class.
- **Browser.** Without cross-origin isolation the solver runs blocks sequentially, and the 16 ms browser drag target assumes one thread.
- **Fonts and tables.** Text uses registry font packages pinned in `ingot.lock` and shaped by Parley, never OS lookup ([PLT](12-platform-performance.md)). CSV import ignores the OS locale; a comma-decimal file needs `table(…, decimal: Comma)`.
- **GPU paths.** Thickness search order, zebra, hidden-line and control-vertex previews and interference culling have CPU paths; GPU results never prune or decide.
- **Offline and Tier 2.** Standards, catalog and font packages are vendored into air-gapped installs with their licences. Tablets edit dimensions, parameters and mates and drag sketches by touch through the same `api` stream.

## Interfaces with other subsystems

MEC uses ANV's operations with ANV's names and phases, and no MEC feature ships before the operations it calls. What MEC requires is generated from the other tabs' tables.

| To | What | Types | Phase |
| --- | --- | --- | --- |
| ANV | Constraint systems and their semantics for `solve_constraints`; definitional attribute classes; `FeatureRole` aliases; feature-level failure kinds; the Assembly `GeometryId` encoding; the `Continuity` enum | `FeatureError`, `HoleSpec`, `ThreadSpec`, `CoordSys`, `Continuity` | 1 |
| ING | GD&T records and dialect validators; the closed `ShapeAspect` kinds; std features with roles, `#[realizes]` markings and keyed generators; `std::standards::iso286`; the default distribution; general tolerances; the sketch-seed quantum | `GeometricTolerance`, `ShapeAspect<K>`, `Tol<T>` | 1 |
| KLN | Part and Assembly `GeometryId` encodings; identity attributes evaluated from source; definitional attributes; interference classes for the no-new-interference merge condition; `bom_item` lines; revision markers; cut lists | `ItemDefinition` inputs, `GeometryId` | 1 |
| KLN | Context pins recorded in `ingot.lock` and moved by Proposal | `Context`, lockfile entries | 2 |
| FLX | Typed joints, redundancy reports and drivers; bounded mass properties with declared masses; preload and fastener Instance sets for connectors; member profiles and axes; `Touching` pairs for tied interfaces; declared symmetries; the calibration class each check needs | `Assembly`, `Field`, `Mate` | 1, 2 |
| FLX | ABD matrices and laminate rules for shells and ply optimization; default distributions and skin-model samples | `Ply`, `Field` | 2, 4 |
| COV | Gear records with accuracy grade and load spectrum; plies and kinematic drape; part data for validity envelopes | `Field`, `Ply` | 2, 4 |
| MFG | `FlatPattern`, `HoleSpec`, `ThreadSpec`, `Weld` with quality level, `execution_class`, edge callouts, general tolerances, `split_mold`, lattices, gear data tables, plies, harness geometry, balloons, `BendRule` and `BendTable`, preload ranges, mates for machine, robot and fixture Assemblies; the drawing library for in-process drawings; the `realize` point of each export | `Body`, `Drawing`, definitional attributes | 1, 2, 3 |
| ELX | Enclosure geometry and checks; mates; gear records for drivetrain elements; interface records for board outlines and keep-outs; routes, bundle and formboard geometry; fastener selection | `Assembly`, `Route`, `CoordSys` | 1, 2 (gear records), 3, 4 (formboard) |
| ECO | `crucible:product`; the GD&T model with its AP242 modifier mapping; weld, hole and composite semantics; flat DXF layer conventions; drawing sheets for the DXF and DWG writers; the `export_resolution` check | WIT records, `Drawing` | 1, 2 |
| UIX | Solver and motion streams; `SolveReport`, `ContinuityReport` and check Fields; sketch-edit rewrites; metadata for Insert Instance and Add mate; `generate` outcomes as variants; context queries for Edit in context; exploded-view steps; `auto_drawing`; revision markers | `Field`, `Sketch`, `Context` | 1, 2 |
| AGT | Every std feature with its doc metadata as an agent tool; typed failures with compiling fixes | `FeatureError` | 1 |

## Oracles

All oracles live in the protected `oracles/mech/` directory. Held-out subsets (20% of each generated or replayed set, and every golden-product drawing) are never shown to agents.

**Decision D-MEC-37:** Oracles never vendor third-party datasets; they fetch fixed lists by content hash at test time, Crucible redistributes only ABC and SketchGraphs items that contract 13.3's licence filter admits, the Fusion 360 Gallery serves no oracle, and published benchmark comparisons use only open implementations such as OCCT.
*Why:* Onshape's grant covers only some public documents [Onshape terms], ABC and SketchGraphs leave copyright with creators [ABC dataset], and the Fusion 360 Gallery licence allows only non-commercial research [Fusion 360 Gallery licence].
*Rejected:* vendored datasets (redistribution Crucible may not do); published results against commercial kernels (their licences may forbid it).

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| MEC-O-SK-1 | Sketch solving | SketchGraphs 2D replay and a synthetic 3D set re-solve from perturbed seeds on the recorded branch |
| MEC-O-SK-2 | Diagnosis | Known-rank systems, irrational witnesses included, get the right rank and certification; conflict sets are minimal |
| MEC-O-SK-3 | Inequalities | Known-feasibility systems are classified correctly |
| MEC-O-SK-4 | Determinism and seeds | Identical bits across the canonical class and re-randomized names; no silent branch change in 1,000 edits; an idle drag writes nothing; rounded seeds rebuild bit-identically |
| MEC-O-SK-5 | Drag | 200- and 2,000-entity sketches meet the drag targets, a 2,000-entity sketch with one block of at least 1,000 unknowns included; a drag re-solves only downstream blocks; an overridden result never answers a request without the override |
| MEC-O-SK-6 | Curves | Spline, NURBS and helix values and lengths match high-precision references |
| MEC-O-SK-7 | Custom constraints | Values and derivatives match a reference interpreter and finite differences |
| MEC-O-SK-8 | Certified positions | Near-singular and under-determined sketches give boxes containing high-precision references, whatever their width; only sketches whose qualifiers the box leaves undecided fail, with `Ambiguous` |
| MEC-O-SK-9 | Helper names | Every helper sub-entity resolves, in sketches and as a role on extrusions, over 100 random edits |
| MEC-O-SK-10 | Sketch edits | Trims, splits, extends and corner fillets on held-out SketchGraphs sketches keep the solve report's freedom count except as the diff states, and every surviving entity keeps its role; DXF imports re-export with identical entities |
| MEC-O-PF-1 | Profile features and roles | Volumes equal closed forms; every role of every std sweeping feature resolves over 100 random edits |
| MEC-O-PF-2 | Sweeps, lofts, helices | A circle swept along a helix is a tube; frames continuous; springs and threads match analytic surfaces; twisted extrusions match closed forms |
| MEC-O-PF-3 | Offsets and shells | Certified minimum wall distance equals the thickness; a filleted box shelled inward past its fillet radius in `Natural` mode reports `BlendCollapsed` with sharp inner edges |
| MEC-O-PF-4 | Holes, threads, standards | Sizes match formulas and licensed tables; designations with pitch resolve with no licensed package installed; NIST hole cases rebuild; `Full` mesh threads lie within the chord tolerance |
| MEC-O-PF-5 | Blends and fallbacks | G1 contact holds; ANV's part-level benchmark meets its targets; `fallback_regions` decides seeded cases correctly |
| MEC-O-PF-6 | Draft | Draft Fields meet targets on drafted faces |
| MEC-O-PF-7 | Patterns and copies | Keys and transforms correct; removing a point renames no other copy; a read-only use of a source changes no `EntityId`; mirrors declare their plane |
| MEC-O-PF-8 | Booleans | Volume identities hold on pairs from the licence-filtered ABC subset |
| MEC-O-PF-9 | Direct edits | Declared relations kept, adjacent blends regrown |
| MEC-O-PF-10 | Deform and wrap | Deviation from analytic maps within the reported bound; developable wraps keep arc length |
| MEC-O-PF-11 | Derived parts | Pinned and bumped sources give the expected diff Proposals |
| MEC-O-PF-12 | Families and configurations | Rows type-check and report per row; each `#[configuration]` variant builds as declared; KLN-O-PLM-5 checks the 150% BOM |
| MEC-O-PF-13 | Lattices | Relative density matches analytic values; kept faces keep attributes; sheet-cell mid-surfaces lie on the field's zero set |
| MEC-O-PF-14 | Rebuild budget | Golden-product rebuilds after first, middle and last edits meet contract 13.3 |
| MEC-O-PF-15 | Gears | Flank points match ISO 21771-1 exactly; undercut and tip limits hold; gear data tables carry every record field |
| MEC-O-PF-16 | Reference geometry | Constructors re-resolve under edits; shape-derived frames carry their note; the housing example builds with four holes on the outer corners; a canvas leaves the `ItemDefinition` unchanged |
| MEC-O-PF-17 | Text, emboss, engrave | Regions match shaped outlines; depth and arc length exact on planes and cylinders |
| MEC-O-PF-18 | Hull and Minkowski sum | Results equal exact rational hulls and closed-form convex sums |
| MEC-O-PF-19 | Generative design | On held-out design spaces, every outcome keeps each kept face's name, `HoleSpec` and GD&T identical, passes the design's checks, and meets its method's constraints |
| MEC-O-AS-1 | Mates | Known Grübler–Kutzbach mobility, redundant and accidental cases included; rigid and flexible subassemblies agree |
| MEC-O-AS-2 | Kinematics | Slider-crank and four-bar motion equals closed forms |
| MEC-O-AS-3 | Interference and tolerance points | Analytic overlap volumes; NIST CTC 02 and 04 fits classified; a press fit at nominal is `IntendedFit` and at `Mmc` reports its true overlap; a part built at `Mid` has every fitted size at its mid-limit and the same `EntityId`s as at `Nominal` |
| MEC-O-AS-4 | Large assemblies | A synthetic 100,000-Instance assembly meets the open and orbit targets |
| MEC-O-AS-5 | Exploded views | Automatic explosion of the golden gearbox is collision-free |
| MEC-O-AS-6 | Fasteners | Lengths equal hand-computed cases; adding a hole changes the set's quantity, not the BOM structure |
| MEC-O-AS-7 | Mate inference | Top-1 accuracy on the generated joint benchmark meets the target |
| MEC-O-AS-8 | Interfaces | Every seeded provider–consumer mismatch is reported |
| MEC-O-AS-9 | BOM-only items and approved parts | Lines carry the Item's unit; a non-approved part fails unless a Waiver names it |
| MEC-O-AS-10 | Dynamic clearance | Intervals contain the dense-sampling minimum, a cam with a short dwell between samples included |
| MEC-O-AS-11 | Enclosure checks | KiCad's STEP and IDF exports of an open board give the expected findings [KiCad PCB editor] |
| MEC-O-AS-12 | Assembly-level features | Derived Parts and after-assembly operations give the same geometry |
| MEC-O-AS-13 | Identity and definitional attributes | Re-randomized Instance names keep Assembly `GeometryId`s, and moving an Instance changes them; a half-turn has one encoding; a definitional change marks a released Item modified, a non-definitional one does not; renaming a Part is a source change |
| MEC-O-AS-14 | In-context design | A cover designed in its housing's context at a pinned Change builds without a cycle; moving the pin gives a diff Proposal; a lost reference is a typed `ResolveError`; diverging pins conflict |
| MEC-O-AS-15 | Path and belt couplings | A carriage on a circular track follows the closed form; belt pitch length and pulley ratios equal closed forms for two- and three-pulley drives |
| MEC-O-AS-16 | Declared mass properties | Roll-ups use declared values and label them; an undeclared purchased Instance raises the warning |
| MEC-O-WIT-1 | `crucible:product` | The published WIT matches the tabled interfaces; golden products round-trip through `build` and `read` with equal `GeometryId`s |
| MEC-O-SF-1 | Continuity | Surface pairs of known order are classified correctly under the default thresholds |
| MEC-O-SF-2 | Surfaces | Boundary, network and fill surfaces interpolate boundaries and meet edge targets |
| MEC-O-SF-3 | SubD | Limits match stored OpenSubdiv outputs; `to_nurbs` deviation as reported |
| MEC-O-SF-4 | Scan to CAD | Synthetic scans recover primitive types, parameters and Chamfer distance |
| MEC-O-SF-5 | Control-vertex drags | Frames within 16 ms; the committed edit equals the full rebuild |
| MEC-O-SM-1 | Bend rules and styles | Developed lengths equal the formulas; the default K follows the R/t data and prints per bend; `check::sheet` reports the applied style |
| MEC-O-SM-2 | Flat patterns | Every flat pattern refolds to the folded body within the entity tolerance |
| MEC-O-SM-3 | Sheet checks | Every seeded defect in GP4's guards is found |
| MEC-O-SM-4 | Flat DXF and clinch hardware | DXF re-imports with layers per convention; seeded clinch violations are found |
| MEC-O-WD-1 | Member sections | Area and second moments equal catalog values within 0.5% |
| MEC-O-WD-2 | Trims and cut lists | Mitred lengths and end angles equal closed forms |
| MEC-O-WD-3 | Weld records | Rendered symbols parse back into identical records; each execution class reaches MFG's quality-level check |
| MEC-O-CP-1 | Draping | Hemisphere and cylinder drapes match analytic shear |
| MEC-O-CP-2 | Laminates | ABD matrices equal hand calculations; symmetry, balance, drop-off and consecutive-ply checks correct |
| MEC-O-MD-1 | Thickness | Fields match analytic answers; bits are identical with the GPU off and with adversarial GPU candidates |
| MEC-O-MD-2 | Mould split | Core, cavity and part sum to the block; no negative draft |
| MEC-O-RT-1 | Routes | Lengths and bend radii on known paths equal closed forms |
| MEC-O-RT-2 | Fittings | Fitting selection matches specification tables |
| MEC-O-RT-3 | Formboards | Flattened branch lengths equal 3D lengths without overlaps |
| MEC-O-LS-1 | Hydrostatics | Analytic hull forms match closed-form hydrostatics |
| MEC-O-LS-2 | IFC structures | IFC 4.3 members, plates and openings round-trip |
| MEC-O-LS-3 | Soft goods | Flattened seams match 3D lengths within the declared stretch |
| MEC-O-LS-4 | MEMS stacks | Stacks with known etch geometry give the analytic Bodies |
| MEC-O-TL-1 | Dialects and modifiers | Y14.5-2018 and ISO 1101 rule suites are judged correctly; every `Modifier` value round-trips through AP242 and QIF; conversion leaves one typed hole per non-equivalent control; a control on the wrong aspect kind fails to compile |
| MEC-O-TL-2 | Degrees of freedom | Known free directions are reported exactly, a threaded bore included |
| MEC-O-TL-3 | 1D stacks | Worst case and RSS at a stated coverage equal exact convolutions; untoleranced contributors take the general tolerance |
| MEC-O-TL-4 | 3D variation | Identical across runs, classes and renamings; intervals cover references; the zone path meets its target |
| MEC-O-TL-5 | Skin models | Sampling statistics match the specified random fields |
| MEC-O-TL-6 | GD&T record and PMI targets | NIST FTC controls, ISO 5458 examples and datum targets round-trip; a rib splitting a face with forwarded `4mm ± 0.1mm` fails `pmi_target_resolved`; the canonical bracket has two independent thickness sites |
| MEC-O-TL-7 | Coverage rules | Seeded missing size, form, datum-form and general tolerances are all found |
| MEC-O-TL-8 | Default distributions | Reports print assumptions; process data set shift and spread; zone samples are uniform over the torsor set |
| MEC-O-TL-9 | GD&T in 1D chains and fasteners | GP1's bolt pattern gives the hand-computed fixed-fastener margin T₁ + T₂ = H − F and floating margins T = H − F; an MMC bonus stays correlated with its size contributor in worst case and RSS |
| MEC-O-DR-1 | Hidden lines | Certified hidden lines agree with high-resolution ray casting within the sheet-unit bound at 100:1 and 1:200 |
| MEC-O-DR-2 | Associativity and edits | Every item re-resolves or reports a `ResolveError`; editing a driving dimension writes exactly its literal |
| MEC-O-DR-3 | PMI exchange | NIST CTC, FTC and later test cases export to AP242 and match NIST's files item by item |
| MEC-O-DR-4 | Drafting rules | Line types, text, symbols and tables pass on held-out golden drawings; GP1's drawing shows centre marks, thread representation, material hatching, a break line and ordinate, baseline and chain sets |
| MEC-O-DR-5 | Automatic drawings | Every PMI item appears exactly once; reruns are bit-identical |
| MEC-O-DR-6 | Revision markers | Two changed dimensions give two markers and one revision row |
| MEC-O-DR-7 | Balloons | One changed dimension changes one balloon and no labels; GP1 and GP2 balloon every size, location, orientation, form and profile control |
| MEC-O-DR-8 | PMI eligibility | Controls on facet faces export as presentation and are reported |
| MEC-O-DR-9 | Lattice regions in drawings | GP2's drawing shows the lattice zone with its note, hidden lines only on B-rep faces and the region boundary, and cut struts in sections |
| MEC-O-DR-10 | Export resolution | A part with a 3 nm sliver and a 10 µm tolerant edge, exported under a Parasolid-based receiver profile, reports both |
| MEC-O-DR-11 | Two-dimensional sheets | An imported DXF and DWG become drawing programs that re-export with identical entities, layers and blocks |
| MEC-O-CK-1 | Check coverage | Every defect seeded into golden products 3 to 5 is found, none on clean versions |
| MEC-O-CK-2 | Fixes and failure kinds | Every fix compiles and clears its finding; the set of `FeatureError` kinds of std features equals ANV's failure kinds plus the feature-level kinds MEC lists |
| MEC-O-CK-3 | Bound kinds | Bounds below `decides_on`, outside the class envelope or unconfirmed by refinement give `Undecided`; Nitsche-clamped plate frequencies below the reference are caught by the two-sided bound |
| MEC-O-CK-4 | Strut strength and gauge functionals | Johnson–Perry–Robertson factors equal hand calculations from measured waviness; eigen-buckling runs only where elastic buckling governs; every GP1 and GP2 stress check reports its gauge functional with a bound |
| MEC-O-HF-1 | Human factors | Segment lengths match the dataset; reach envelopes match analytic chains |

## Phasing

Gate contributions follow contract 13; per-capability phases are in the capability tables, and shared and parity-floor phases follow contract 13.4.

| Phase | MEC's contribution to the gate |
| --- | --- |
| 0 | Certified solver core and modular-rank diagnosis on `linalg`; role conventions; data-package format; MEC corpus in the determinism suite |
| 1 | GP1: sketches and sketch edits, extrusions, revolutions and circular sweeps with full role vocabularies, holes and threads from formulas with no licensed table, stage 1 blends, shells, draft, patterns, push-pull, basic mates, explode steps, GD&T with closed modifier lists and PMI target checks, general tolerances, geometry at tolerance points, 1D stacks with GD&T contributors and fastener assemblability, drawings with drafting conventions and characteristic balloons, DXF write of sheets, AP242 PMI with export resolution, identities, declared mass properties, `crucible:product`. GP2: strut lattices, generative design for additive and unrestricted methods, text, emboss, hull, printed threads on the mesh path, lattice zones on drawings, strut-strength and buckling checks on their classes with gauge functionals |
| 2 | GP3: gear records with exact flanks and data tables for COV's ratings, shafts, fastener Instance sets, kinematics and motion studies, path mates, in-context design through context pins, completeness, 3D variation. GP4: weldments with execution classes, sheet metal with shop styles, compliant variation, revision markers. Also lofts and general sweeps, freeform surfaces, moving, replacing and deleting faces, stage 2 blends, exact threads, sheet-cell lattices, datum targets, dialect conversion, generative design for milling, two-axis cutting and casting, reference images, 2D-only sheets with DXF and DWG, DXF import to sketches |
| 3 | GP5: moulded part design, control-vertex editing with G3 surfaces, SubD, routing, automatic drawings, mate inference, tolerance allocation; belt and chain couplings |
| 4 | GP6: composite laminates with laminate rules, harness bundles from ELX wire lists, formboards, scan to CAD, skin model shapes, cast parts; the 100,000-Instance open target |
| 5 | GP7 MEMS layer stacks; GP8 steel structures through IFC 4.3, with execution classes enforced by MFG; pipe and duct routing; human factors |
| 6 | GP10: laminate rules as constraints of Flux's ply-shape, ply-drop and stacking optimization |
| 7 | GP13 hull fairing and hydrostatics; GP14 timber members through IFC; GP16 soft-goods patterns |

## Open questions

1. **Standards tables std may ship.** Which thread-series, clearance-hole and fastener tables may std ship, and on which distributor terms? This waits on counsel's opinion, a phase 0 gate item ([contract 13.1](../contract.md)). Nothing in the design waits on the answer, because designations that carry their values compile with no table. The answer only decides whether the series packages ship with std or come from the organization.

## Contract change requests

None.

## Sources

| Key | Title | URL | Date opened |
| --- | --- | --- | --- |
| [SolveSpace] | SolveSpace, technical description | https://solvespace.com/tech.pl | 2026-10-11 |
| [Siemens 2D DCM] | Siemens, D-Cubed 2D DCM | https://www.siemens.com/en-gb/products/plm-components/d-cubed/2d-dcm/ | 2026-10-11 |
| [Siemens 3D DCM] | Siemens, D-Cubed 3D DCM | https://www.siemens.com/en-gb/products/plm-components/d-cubed/3d-dcm/ | 2026-10-11 |
| [Siemens 2D DCM v79] | Siemens, D-Cubed 2D components version 79 release (3 December 2025) | https://blogs.sw.siemens.com/plm-components/d-cubed-2d-components-version-79-release/ | 2026-10-11 |
| [FreeCAD planegcs] | FreeCAD planegcs solver source | https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/Sketcher/App/planegcs/GCS.cpp | 2026-10-11 |
| [Zou 2022] | Zou et al., A review on geometric constraint solving | https://arxiv.org/abs/2202.13795 and https://arxiv.org/pdf/2202.13795v2 | 2026-10-11 |
| [Zou and Feng 2019] | Zou and Feng, On limitations of the witness configuration method | https://arxiv.org/pdf/1904.00526 | 2026-10-11 |
| [SketchGraphs] | Seff et al., SketchGraphs | https://arxiv.org/abs/2007.08506 and https://github.com/PrincetonLIPS/SketchGraphs | 2026-10-11 |
| [Koch et al. 2019] | Koch et al., ABC dataset | https://openaccess.thecvf.com/content_CVPR_2019/html/Koch_ABC_A_Big_CAD_Model_Dataset_for_Geometric_Deep_Learning_CVPR_2019_paper.html and https://cims.nyu.edu/gcl/papers/2019-ABC-Dataset.pdf | 2026-10-11 |
| [Fusion 360 Gallery] | Autodesk, Fusion 360 Gallery dataset | https://github.com/AutodeskAILab/Fusion360GalleryDataset | 2026-10-11 |
| [JoinABLe] | Willis et al., JoinABLe | https://arxiv.org/abs/2111.12772 | 2026-10-11 |
| [Onshape FeatureScript] | Onshape, FeatureScript introduction | https://cad.onshape.com/FsDoc/intro.html | 2026-10-11 |
| [Onshape mates] | Onshape, mates | https://cad.onshape.com/help/Content/Assembly/mates.htm | 2026-10-11 |
| [Onshape sheet metal] | Onshape, sheet metal model | https://cad.onshape.com/help/Content/PartStudio/sheet_metal_model.htm | 2026-10-11 |
| [Siemens synchronous technology] | Siemens, synchronous technology | https://www.siemens.com/en-us/technology/synchronous-technology/ | 2026-10-11 |
| [Plasticity] | Plasticity, product tour | https://plasticity.xyz/product | 2026-10-11 |
| [Rhino ToNURBS] | McNeel, Rhino 8 ToNURBS | https://docs.mcneel.com/rhino/8/help/en-us/commands/tonurbs.htm | 2026-10-11 |
| [OpenSubdiv] | Pixar, OpenSubdiv | https://github.com/PixarAnimationStudios/OpenSubdiv | 2026-10-11 |
| [Point2CAD] | Liu et al., Point2CAD | https://openaccess.thecvf.com/content/CVPR2024/html/Liu_Point2CAD_Reverse_Engineering_CAD_Models_from_3D_Point_Clouds_CVPR_2024_paper.html | 2026-10-11 |
| [Sawhney and Crane 2017] | Sawhney and Crane, Boundary First Flattening | https://arxiv.org/abs/1704.06873 | 2026-10-11 |
| [Ceres modeling] | Ceres Solver, modeling (manifolds and loss functions) | http://ceres-solver.org/nnls_modeling.html | 2026-10-11 |
| [faer] | faer documentation | https://docs.rs/faer/latest/faer/ | 2026-10-11 |
| [OndselSolver] | Ondsel, OndselSolver | https://github.com/Ondsel-Development/OndselSolver | 2026-10-11 |
| [ASME Y14.5] | ASME Y14.5 | https://www.asme.org/codes-standards/find-codes-standards/y14-5-dimensioning-tolerancing | 2026-10-11 |
| [GD&T Seminars Y14.5-2018] | GD&T Seminars, the new ASME Y14.5-2018 standard | https://gdtseminars.com/2019/05/24/the-new-asme-y14-5-2018-standard/ | 2026-10-11 |
| [ASME Y14.41] | ASME Y14.41 | https://www.asme.org/codes-standards/find-codes-standards/y14-41-digital-product-definition-data-practices | 2026-10-11 |
| [ISO 1101] | ISO 1101:2017 | https://www.iso.org/standard/66777.html | 2026-10-11 |
| [ISO 16792] | ISO 16792:2021 | https://www.iso.org/standard/73871.html | 2026-10-11 |
| [ISO 5459] | ISO 5459:2024 (EVS listing) | https://www.evs.ee/en/evs-en-iso-5459-2024 | 2026-10-11 |
| [ISO 14405-1] | ISO 14405-1:2025 (EVS listing) | https://www.evs.ee/en/evs-en-iso-14405-1-2025 | 2026-10-11 |
| [ISO 8015] | ISO 8015:2011 (EVS listing) | https://www.evs.ee/en/iso-8015-2011 | 2026-10-11 |
| [ISO 22081 (SIS)] | ISO 22081:2021 (SIS listing) | https://www.sis.se/en/produkter/metrology-and-measurement-physical-phenomena/linear-and-angular-measurements/geometrical-product-specification-gps/ss-en-iso-220812021/ | 2026-10-11 |
| [ISO 2553] | ISO 2553:2019 (EVS listing) | https://www.evs.ee/en/iso-2553-2019 | 2026-10-11 |
| [AWS A2.4] | AWS A2.4:2020 (GlobalSpec listing) | https://standards.globalspec.com/std/14204706/a2-4-2020 | 2026-10-11 |
| [ISO 21771-1] | ISO 21771-1:2024 (EVS listing) | https://www.evs.ee/en/iso-21771-1-2024 | 2026-10-11 |
| [ISO 7250-1] | ISO 7250-1:2017 | https://www.iso.org/standard/65246.html | 2026-10-11 |
| [CAx-IF PMI v4.1] | CAx-IF, Recommended Practices for PMI v4.1 | https://www.mbx-if.org/home/wp-content/uploads/2024/06/rec_pracs_pmi_v41.pdf | 2026-10-11 |
| [NIST MBE PMI] | NIST, MBE PMI validation and conformance testing | https://www.nist.gov/ctl/smart-connected-systems-division/smart-connected-manufacturing-systems-group/mbe-pmi-0 | 2026-10-11 |
| [buildingSMART IFC] | buildingSMART, Industry Foundation Classes | https://www.buildingsmart.org/standards/bsi-standards/industry-foundation-classes/ | 2026-10-11 |
| [AISC Shapes v16.0] | AISC, Shapes Database v16.0 | https://www.aisc.org/publications/steel-construction-manual-resources/16th-ed-steel-construction-manual/aisc-shapes-database-v16.0/ | 2026-10-11 |
| [Creo draping] | PTC, Creo draping simulation | https://support.ptc.com/help/creo/creo_plus/usascii/composite_design/about_draping_simulation.html | 2026-10-11 |
| [Anwer et al. 2014] | Anwer et al., From solid modelling to skin model shapes (2014) | https://cris.fau.de/publications/111031184 | 2026-10-11 |
| [Schleich and Wartzack 2016] | Schleich and Wartzack, A quantitative comparison of tolerance analysis approaches (2016) | https://cris.fau.de/publications/122836164 | 2026-10-11 |
| [ISO 5458] | ISO 5458:2018, pattern and combined geometrical specification (EVS listing) | https://www.evs.ee/en/iso-5458-2018 | 2026-10-11 |
| [ISO 2692] | ISO 2692:2021, maximum material, least material and reciprocity requirements (EVS listing) | https://www.evs.ee/en/iso-2692-2021 | 2026-10-11 |
| [ISO 17450-1] | ISO 17450-1:2011, model for geometrical specification and verification (EVS listing) | https://www.evs.ee/en/iso-17450-1-2011 | 2026-10-11 |
| [Homri, Teissandier and Ballu 2015] | Homri, Teissandier and Ballu, Tolerance analysis by polytopes (classes of surface and degrees of invariance, Table 1) | https://arxiv.org/pdf/1509.08763 | 2026-10-11 |
| [Keyence GD&T basics] | Keyence, international industrial standards and GD&T (independency and envelope principles) | https://keyence.com/ss/products/measure-sys/gd-and-t/basic/international.jsp | 2026-10-11 |
| [Sigmetrix GD&T Advisor] | Sigmetrix, GD&T Advisor | https://www.sigmetrix.com/software/gdt-advisor | 2026-10-11 |
| [ASME Y14.35] | ASME Y14.35, revision of engineering product definition datasets and associated documents | https://www.asme.org/codes-standards/find-codes-standards/y14-35-revision-engineering-drawings-associated-documents | 2026-10-11 |
| [IAQG 9102] | IAQG, 9102 summary of changes, revision B to C (11 July 2023) | https://ma.iaqg.org/wp-content/uploads/2019/10/9102_Changes_07112023.pdf | 2026-10-11 |
| [ISO 5817] | ISO 5817:2023, quality levels for imperfections in fusion-welded joints (EVS listing) | https://www.evs.ee/en/iso-5817-2023 | 2026-10-11 |
| [OpenSCAD cheat sheet] | OpenSCAD cheat sheet | https://openscad.org/cheatsheet/ | 2026-10-11 |
| [KiCad PCB editor] | KiCad 9 PCB editor manual (STEP and IDF export) | https://docs.kicad.org/9.0/en/pcbnew/pcbnew.html | 2026-10-11 |
| [OCCT fillet] | Open CASCADE, `BRepFilletAPI_MakeFillet` reference | https://occt3d.com/dev/doc/refman/html/class_b_rep_fillet_a_p_i___make_fillet.html | 2026-10-11 |
| [faer sparse QR] | faer 0.24.4, sparse QR module (simplicial and supernodal factorizations, no pivoting or rank mode listed) | https://docs.rs/faer/latest/faer/sparse/linalg/qr/index.html | 2026-10-11 |
| [ISO 10303 notice] | ISO, notice on machine-readable files for ISO 10303 | https://standards.iso.org/iso/10303/ | 2026-10-11 |
| [Directive 96/9/EC] | Directive 96/9/EC on the legal protection of databases, Article 7 | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:31996L0009 | 2026-10-11 |
| [Onshape terms] | Onshape, terms of use, section 1(g)(ii) | https://www.onshape.com/en/legal/terms-of-use | 2026-10-11 |
| [Fusion 360 Gallery licence] | Autodesk, Fusion 360 Gallery dataset licence | https://raw.githubusercontent.com/AutodeskAILab/Fusion360GalleryDataset/master/LICENSE.md | 2026-10-11 |
| [ABC dataset] | ABC dataset site (copyright stays with the models' creators) | https://deep-geometry.github.io/abc-dataset/ | 2026-10-11 |
| [Onshape extrude] | Onshape, Extrude (New, Add, Remove, Intersect) | https://cad.onshape.com/help/Content/extrude.htm | 2026-10-11 |
| [SOLIDWORKS configurations] | SOLIDWORKS 2024 help, configurations overview | https://help.solidworks.com/2024/english/SolidWorks/sldworks/c_Configurations_Overview.htm | 2026-10-11 |
| [SOLIDWORKS external references] | SOLIDWORKS 2024 help, external references | https://help.solidworks.com/2024/english/SolidWorks/sldworks/c_external_references.htm | 2026-10-11 |
| [Wilson and Latombe 1994] | Wilson and Latombe, Geometric reasoning about mechanical assembly, Artificial Intelligence 71 (1994) | https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/0004-3702(94)90048-5?fields=title,authors,venue,year,abstract | 2026-10-11 |
| [Scholz 1995] | Scholz, Tolerance stack analysis methods (Boeing, 1995; Bender's 1.5 factor) | https://faculty.washington.edu/fscholz/Reports/isstech-95-030.pdf | 2026-10-11 |
| [GD&T Basics Rule 1] | GD&T Basics, Rule #1 (Y14.5-2018 section 5.8.1) | https://www.gdandtbasics.com/?p=8382 | 2026-10-11 |
| [ASME Y14.5.1] | ASME Y14.5.1-2019, mathematical definition of dimensioning and tolerancing principles | https://www.asme.org/codes-standards/find-codes-standards/y14-5-1-mathematical-definition-dimensioning-tolerancing-principles | 2026-10-11 |
| [McAtamney and Corlett 1993] | McAtamney and Corlett, RULA, Applied Ergonomics 24(2), 1993 (PubMed record) | https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=15676903 | 2026-10-11 |
| [Alias Class-A] | Autodesk Alias tutorial on Class-A surfaces | https://help.autodesk.com/cloudhelp/2016/ENU/Alias-Tutorials-Legacy/files/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.htm | 2026-10-11 |
| [ICEM brochure] | Dassault Systèmes, CATIA ICEM Shape Design brochure | https://www.3ds.com/fileadmin/PRODUCTS-SERVICES/CATIA/PDF/CATIA-ICEM-Shape-Design-Brochure.pdf | 2026-10-11 |
| [Tecnomatix VA] | Siemens, Tecnomatix Variation Analysis (formerly VSA) fact sheet | https://www.plm.automation.siemens.com/en_us/Images/Siemens-PLM-Tecnomatix-Variation-Analysis-fs_tcm1023-120264.pdf | 2026-10-11 |
| [OCCT modeling algorithms] | Open CASCADE, modeling algorithms user guide (hidden line removal) | https://occt3d.com/dev/doc/overview/html/occt_user_guides__modeling_algos.html | 2026-10-11 |
| [Moldflow thickness] | Autodesk Moldflow Insight, thickness diagnostic | https://help.autodesk.com/cloudhelp/2026/ENU/MoldflowInsight-CLC-Troubleshoot/files/Error-and-warning-messages/MFLO_SOLVER_MESSAGE_702300.html | 2026-10-11 |
| [Magics 2025] | Materialise, Magics 2025 release (wall thickness analysis) | https://www.materialise.com/en/news/press-releases/magics-release-rapid-tct-2025 | 2026-10-11 |
| [KISSsoft] | KISSsoft product description 2024 (ISO 21771 geometry, ISO 6336 strength) | https://www.kisssoft.com/files/aznw8h/KISSsoft-Productdescription-en-v2402.pdf | 2026-10-11 |
| [RJC Mold ribs] | RJC Mold, rib design guide (40% to 60% of the nominal wall) | https://rjcmold.com/guides/rib-design-guide/ | 2026-10-11 |
| [FirstMold ribs] | FirstMold, rib design tips | https://firstmold.com/tips/rib-design/ | 2026-10-11 |
| [CAx-IF composites v4.4] | CAx-IF, Recommended Practices for Composite Materials v4.4 | https://www.mbx-if.org/home/wp-content/uploads/2026/01/Rec_Pracs_Composites_V4.4.pdf | 2026-10-11 |
| [CAx-IF practices] | CAx-IF recommended practices index | https://www.mbx-if.org/home/cax/recpractices/ | 2026-10-11 |
| [ISO 68-1] | ISO 68-1:2023 (EVS listing) | https://www.evs.ee/en/iso-68-1-2023 | 2026-10-11 |
| [ISO 261] | ISO 261:1998 (EVS listing) | https://www.evs.ee/en/iso-261-1998 | 2026-10-11 |
| [ISO 965-1] | ISO 965-1:2026 (EVS listing) | https://www.evs.ee/en/iso-965-1-2026 | 2026-10-11 |
| [ISO 286-1] | ISO 286-1:2010 (EVS listing) | https://www.evs.ee/en/iso-286-1-2010 | 2026-10-11 |
| [ISO 286-2] | ISO 286-2:2010 (EVS listing) | https://www.evs.ee/en/iso-286-2-2010 | 2026-10-11 |
| [ISO 273 committee] | ISO 273:1979, confirmed in 2024 (ISO committee page) | https://committee.iso.org/standard/4183.html | 2026-10-11 |
| [ISO 273] | ISO 273:1979 (EVS listing) | https://www.evs.ee/en/iso-273-1979 | 2026-10-11 |
| [ISO 228-1] | ISO 228-1:2000 (EVS listing) | https://www.evs.ee/en/iso-228-1-2000 | 2026-10-11 |
| [ISO 7-1] | ISO 7-1:1994 (EVS listing) | https://www.evs.ee/en/iso-7-1-1994 | 2026-10-11 |
| [ISO 2904] | ISO 2904:2020 (EVS listing) | https://www.evs.ee/en/iso-2904-2020 | 2026-10-11 |
| [ASME B1.1] | ASME B1.1-2024, unified inch screw threads | https://www.asme.org/products/codes-standards/unified-inch-screw-threads--un-and-unr-thread-form | 2026-10-11 |
| [ASME B1.20.1] | ASME B1.20.1-2013, pipe threads | https://www.asme.org/codes-standards/find-codes-standards/b1201-pipe-threads-general-purpose-inch | 2026-10-11 |
| [ASME B1.5] | ASME B1.5-1997, Acme screw threads | https://www.asme.org/codes-standards/find-codes-standards/b1-5-acme-screw-threads | 2026-10-11 |
| [ASME Y14.36] | ASME Y14.36-2018, surface texture symbols | https://www.asme.org/codes-standards/find-codes-standards/y14-36-surface-texture-symbols | 2026-10-11 |
| [ISO 21920-1] | ISO 21920-1:2021 (EVS listing) | https://www.evs.ee/en/iso-21920-1-2021 | 2026-10-11 |
| [ISO 19005-2] | ISO 19005-2:2011, PDF/A-2 (EVS listing) | https://www.evs.ee/en/iso-19005-2-2011 | 2026-10-11 |
| [ISO 19005-4] | ISO 19005-4:2020, PDF/A-4 (EVS listing) | https://www.evs.ee/en/iso-19005-4-2020 | 2026-10-11 |
| [ISO 1328-1] | ISO 1328-1:2013 (EVS listing) | https://www.evs.ee/en/iso-1328-1-2013 | 2026-10-11 |
| [ISO 23509-1] | ISO 23509-1:2025 (EVS listing) | https://www.evs.ee/en/iso-23509-1-2025 | 2026-10-11 |
| [ISO 10828] | ISO 10828:2024 (EVS listing) | https://www.evs.ee/en/iso-10828-2024 | 2026-10-11 |
| [DIN 509] | DIN 509:2022-12, relief grooves (DIN Media) | https://www.dinmedia.de/en/standard/din-509/359215693 | 2026-10-11 |
| [DIN 6885-1] | DIN 6885-1:2021-11, parallel keys and keyways (DIN Media) | https://dinmedia.de/en/standard/din-6885-1/346315269 | 2026-10-11 |
| [DIN 471] | DIN 471:2026-05, retaining rings for shafts (DIN Media) | https://www.dinmedia.de/en/standard/din-471/399916408 | 2026-10-11 |
| [EN 10365] | EN 10365:2026 (EVS listing) | https://www.evs.ee/en/evs-en-10365-2026 | 2026-10-11 |
| [EN 10210-2] | EN 10210-2:2019 (EVS listing) | https://www.evs.ee/en/evs-en-10210-2-2019 | 2026-10-11 |
| [EN 10219-2] | EN 10219-2:2019 (EVS listing) | https://www.evs.ee/en/evs-en-10219-2-2019 | 2026-10-11 |
| [EN 1090-2] | EN 1090-2:2018+A1:2024 (EVS listing) | https://www.evs.ee/en/evs-en-1090-2-2018-a1-2024-consolidated | 2026-10-11 |
| [ISO 2768-1] | ISO 2768-1:1989 (EVS listing) | https://www.evs.ee/en/iso-2768-1-1989 | 2026-10-11 |
| [ISO 2768-2] | ISO 2768-2:1989, withdrawn (EVS listing) | https://www.evs.ee/en/iso-2768-2-1989 | 2026-10-11 |
| [ISO 22081] | ISO 22081:2021 (EVS listing) | https://www.evs.ee/en/iso-22081-2021 | 2026-10-11 |
| [ISO 13715] | ISO 13715:2017 (EVS listing) | https://www.evs.ee/en/iso-13715-2017 | 2026-10-11 |
| [Onshape in context] | Onshape, Modeling in context | https://cad.onshape.com/help/Content/Assembly/modeling_in_context.htm | 2026-10-12 |
| [Onshape hole] | Onshape, Hole feature | https://cad.onshape.com/help/Content/hole.htm | 2026-10-12 |
| [Onshape configurations] | Onshape, Configurations | https://cad.onshape.com/help/Content/configurations.htm | 2026-10-12 |
| [Onshape frame] | Onshape, Frame feature | https://cad.onshape.com/help/Content/frame.htm | 2026-10-12 |
| [Fusion generative methods] | Autodesk Fusion, Specify manufacturing methods (Generative Design) | https://help.autodesk.com/cloudhelp/ENU/Fusion-GenerativeDesign/files/GD-SPECIFY-MFG-METHOD.htm | 2026-10-12 |
| [Fusion canvas] | Autodesk Fusion, Insert canvas | https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-INSERT-CANVAS.htm | 2026-10-12 |
| [Creo dimension bounds] | PTC Creo, To set the dimension bounds | https://support.ptc.com/help/creo/creo_plus/usascii/model-based_definition/to_set_the_dimension_bounds_1.html | 2026-10-12 |
| [Creo copy geometry] | PTC Creo, About Copy Geometry and Publish Geometry features | https://support.ptc.com/help/creo/creo_plus/usascii/assembly/asm/About_Copy_and_Publish_Geom_Feat.html | 2026-10-12 |
| [SolidCraft] | SolidCraft README | https://github.com/bherbruck/solvecraft | 2026-10-12 |
| [CADCraft] | CADCraft README | https://github.com/storytold/cadcraft | 2026-10-12 |
| [engineering.com Parasolid] | engineering.com, Parasolid, D-Cubed and Siemens | https://www.engineering.com/parasolid-d-cubed-and-siemens-the-heart-of-your-cad-software-belongs-to-another/ | 2026-10-12 |
| [GD&T Basics fixed fastener] | GD&T Basics, fixed fastener formula | https://www.gdandtbasics.com/?p=9816 | 2026-10-12 |
| [Open Exam Prep fasteners] | Open Exam Prep, projected tolerance zones and fixed and floating fastener formulas | https://open-exam-prep.com/study-guides/asme-gdtp-technologist/ch8/projected-zones-fasteners | 2026-10-12 |
| [STEP Tools AP242 modifiers] | STEP Tools, geometric_tolerance_modifier (AP242 schema) | https://www.steptools.com/stds/stp_aim/html/t_geometric_tolerance_modifier.html | 2026-10-12 |
| [STEP Tools projected zone] | STEP Tools, projected_zone_definition | https://www.steptools.com/stds/stp_aim/html/t_projected_zone_definition.html | 2026-10-12 |
| [STEP Tools unequal zone] | STEP Tools, unequally_disposed_geometric_tolerance | https://www.steptools.com/stds/stp_aim/html/t_unequally_disposed_geometric_tolerance.html | 2026-10-12 |
