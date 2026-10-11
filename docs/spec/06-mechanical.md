# Mechanical design (MEC)

`std::mech` is the Ingot library for mechanical, industrial and structural design, from sketches to drawings and design checks. Every feature orchestrates versioned Anvil operations and a few Wasm components, and returns a `Body`, `Part`, `Assembly` or `Field`. One constraint solver, one query vocabulary and one semantic tolerancing model serve sheet metal, weldments, composites, molded parts, routing and the rest.

## Library structure and shared conventions

### Packages

`std::mech` re-exports the everyday features, so `use std::mech::{sketch, extrude, rib, fillet}` works as in contract section 6. Helpers follow ING's feature granularity rule.

| Package | Contents | First phase |
| --- | --- | --- |
| `std::mech::sketch` | 2D and 3D sketches, constraints, solve reports, text | 1 |
| `std::mech::part` | Part features, reference geometry, holes, patterns, direct edits, lattices | 1 |
| `std::mech::asm` | Instances and Instance sets, mates, kinematics, interference, fasteners | 1, 2 |
| `std::mech::gdt`, `std::mech::tol` | GD&T with dialects `asme` and `iso`; fits, general tolerances, stacks, variation | 1, 2 |
| `std::mech::drawing`, `std::mech::check` | Drawings and model-based definition; design and standards checks | 1 |
| `std::mech::machine`, `std::mech::surf` | Gears, shafts, springs; freeform surfaces, SubD, scan to CAD | 2 |
| `std::mech::sheet`, `std::mech::weld` | Sheet metal; members, trims, welds, cut lists | 2 |
| `std::mech::mold`, `std::mech::route` | Parting, core and cavity, ribs, bosses; tubes, hoses, harnesses, pipes | 3, 5 |
| `std::mech::composite`, `std::mech::human` | Plies, zones, drape; manikins, reach, vision, posture | 4, 5 |
| `std::standards::*` | Standard values computed from the standards' formulas | 1 |
| `crucible::standards::*` | Tabulated standard values under a `DataLicence` | 1 |

**Decision D-MEC-31:** std computes standard values from the formulas the standards define, citing clauses, and ships no transcribed tables. Values that exist only as tables ship as separate data packages carrying a `DataLicence`, from the standards body, a licensed distributor or the organization. Counsel reviews this split before phase 1. *Why:* ISO licenses its machine-readable files only "in their original format without any modifications" [ISO 10303 notice]. Extracting a substantial part of a database can infringe the EU database right [Directive 96/9/EC, Art. 7(1)]. *Rejected:* tables in Apache-2.0 std (rights Crucible does not hold); no standards content (every part needs fits and threads).

Thread plans, clearance holes, fasteners and steel sections are such tables, and each package records its edition.

### Shared types

MEC adds no geometry type. `Part`, `Assembly`, `Instance`, `Transform` and `CoordSys` live in the crate `mech-model` in the Geometry layer (contract 12).

| Type | What it is | Relation to core types |
| --- | --- | --- |
| `Sketch` | Wires and regions with constraints and a solve report | A `Body`; named entities are typed fields (D-ING-9) |
| `Profile`, `Path` | Closed sketch regions; a G0-connected edge chain | `Query`s over faces or edges |
| `CoordSys` | A right-handed frame anchored to geometry | A `Transform` plus an anchor `Query` |
| `Mate` | A typed constraint between frames on two Instances | Stored in the `Assembly` |
| `HoleSpec`, `ThreadSpec`, `Weld`, `Ply` | Manufacturing intent | Definitional attributes keyed by `EntityId` |
| `ShapeAspect` | A feature of size, face set, pattern or recognized aspect | A `Query` over faces, typed by kind (D-ING-6) |
| `GeometricTolerance`, `Datum`, `GeneralTolerance` | GD&T controls, datums with targets, a Part's general tolerance | Definitional attributes |
| `Drawing`, `Sheet`, `View` | 2D documentation | Linework is 2D `Body` geometry |
| `Route` | A path with a specification and end ports | A `Path`, a `RouteSpec` and two `CoordSys` |

Every MEC record that changes what is made is definitional (contract 5). That covers tolerances, datums and their targets, `HoleSpec`, `ThreadSpec`, `Weld` with its execution class, surface texture, edge callouts, plies and laminates. They enter the `ItemDefinition` by canonical entity number, so changing one marks the Item modified (KLN); `FeatureRole` aliases and display styles do not.

### Identity of Parts and Assemblies

**Decision D-MEC-32:** A Part's `GeometryId` hashes the canonically ordered `GeometryId`s of its Bodies, never its name or item number. An Assembly's `GeometryId` hashes its members sorted by (child `GeometryId`, placement), each with its mates by canonical entity number, without Instance names or paths. *Why:* renaming an Instance must not change a revision's definition, while moving one must. *Rejected:* the `ObjectId` (renames would modify Items); children without placements (a moved bearing would be no change).

A placement is a unit quaternion with non-negative scalar part plus a translation, in canonical f64 bits. A mate encodes its kind, limits and both frames as (member index, anchor's canonical entity number). An Instance set contributes one member per key, a flexible subassembly its placements as solved in the parent, and `InstanceRepr` nothing. KLN's `ItemDefinition` adds definitional attributes, Material and properties.

For KLN's definition tolerance, MEC confirms the default: the smaller of 0.1 µm and 1% of the Item's tightest tolerance, or of its general tolerance when nothing is tighter, never below 10ρ.

### Roles, queries and fixes

Every sweeping operation gives roles to the faces, edges and vertices it creates, and ANV owns the vocabulary (contract 6). For profile edges `e` and vertices `v`, `extrude` creates faces `start_cap`, `end_cap` and `side(e)`. It also creates edges `start(e)`, `end(e)` and `lateral(v)`, and vertices `start(v)` and `end(v)`. A role filter on the wrong entity kind fails to compile (ING).

Feature roles such as `hole`'s `wall`, `floor` and `countersink` are `FeatureRole` aliases. Queries match them, while `EntityId`s hash the operation's role (contract 5). A std feature that changes its internal operations therefore takes a major version (ING).

```
let lid  = sketch(plane.xy) { rect(80mm, 50mm) } |> extrude(6mm)
let soft = lid |> fillet(lid.edges(role: end(any)), 1.5mm)
```

**Decision D-MEC-1:** Every `std::mech` feature declares typed roles for the entities it creates. Queries in std select by provenance and role first, with geometric predicates (`longest`, `parallel_to`) only as filters. *Why:* provenance and roles are stable under parameter edits, while geometric predicates flip when dimensions change. *Rejected:* name-matching heuristics (they rebind silently); persistent face ids stored in source (they break under semantic merge).

MEC never orders, seeds or breaks ties by names (contract 7.1). Fillet edges, GD&T targets and drawing items are extent uses. A merge or partial deletion of their anchor fails unless the call writes `on_merge: Accept` or `on_partial: Accept` (contract 5).

Every failure is a `FeatureError { kind, why, fix: [Fix], at: [EntityId] }`, where a `Fix` is a compiling source edit.

**Decision D-MEC-2:** Approximation is always opt-in through an explicit parameter, for example `fallback: Fallback::Implicit(max_deviation: 0.01mm)`. A feature that cannot produce an exact result fails and offers that fallback as a `Fix`. *Why:* the contract forbids silent fallbacks, and designers must see every deviation. *Rejected:* automatic fallback with a warning (warnings get ignored, and released geometry would carry unseen error).

Some features take `repr: Repr`: `Cosmetic` stores intent only, `Simplified` builds light geometry with a recorded `ErrorBound`, and `Full` builds complete geometry.

### WIT interface

MEC owns the WIT package `crucible:product`, with KLN's Item metadata. It replaces `crucible:model`, since "model" means a physics model elsewhere, and stays at `@0.1.0` until the freeze in contract 13.1.

| Interface | Contents | Failures |
| --- | --- | --- |
| `types` | Records for Parts, Assemblies, Instances and sets, transforms, mates, aspects, PMI and intent attributes | — |
| `build` | `product-builder` over Anvil body handles; `finish` validates | `build-error`: unresolved reference, cycle, `invalid-control` |
| `read` | Structure, placements, PMI and definitional attributes for exporters | — |

### Third-party data and benchmarks

**Decision D-MEC-37:** Oracles never vendor third-party datasets; they fetch fixed lists by content hash at test time. Crucible redistributes only ABC and SketchGraphs items that contract 13.3's licence filter admits. The Fusion 360 Gallery serves no oracle, and published comparisons use only open implementations such as OCCT. *Why:* Onshape's grant covers only some public documents [Onshape terms 1(g)(ii)(2)], and ABC and SketchGraphs leave copyright with creators. The Fusion 360 Gallery licence allows only non-commercial research. *Rejected:* vendored datasets (redistribution Crucible may not do); published results against commercial kernels (their licences may forbid it).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Role vocabularies | Face, edge and vertex roles of every std feature; `FeatureRole` aliases | `ResolveError` with ranked fixes | MEC-O-PF-1 | 1 |
| Typed failures and fixes | `FeatureError { kind, why, fix, at }` | — | ANV-O-NAME-5, MEC-O-CK-2 | 1 |
| Opt-in approximation | `fallback:` and `repr:` with a recorded `ErrorBound` | The exact attempt fails and offers the fallback | MEC-O-PF-5 | 1 |
| Standards content | Formulas in std; licensed tables pinned in `ingot.lock` | `UnknownSize { series, near }` | MEC-O-PF-4 | 1 |
| Definitional attributes and identity | `ItemDefinition` inputs; Part and Assembly `GeometryId`s | — | MEC-O-AS-13 | 1 |
| `crucible:product` | `types`, `build` and `read` | `build-error` | MEC-O-WIT-1 | 1 |
| Label invariance | No order, seed or tie-break from names | — | ANV-O-LABEL-1 | 0 |

## Sketching

A sketch is a set of entities, constraints and dimensions, which the solver turns into solved geometry and a solve report.

### Entities and constraints

| Entity | Unknowns (2D) | Phase |
| --- | --- | --- |
| `point`, `line`, `construction_line` | Coordinates; two end points | 1 |
| `arc`, `circle` | Center, radius, start and end angles; three-point and tangent helpers | 1 |
| `spline` (interpolating) | Through points with optional tangent and curvature handles | 1 |
| `helix`, `spiral` | Axis frame, pitch, turns, taper (exact `anvil::curve` helices) | 1 |
| `offset`, `use_edges` | Driven by a source chain or a model-edge `Query`; `use_edges` never rebinds | 1 |
| `text` | Driven outlines from `anvil::text_outline` over a pinned font package (D-PLT-7) | 1 |
| `rect`, `rect_between`, `slot`, `polygon` | Helpers emitting entities, constraints and named sub-entities | 1 |
| `ellipse`, `elliptical_arc`, `conic`, `nurbs` | Axes and ratio; ends, apex and rho; control points and weights, degree 2 to 7 | 2 |
| `intersection_curve` | Driven, in 3D sketches | 2 |

Helpers name what they emit, such as `rect`'s lines `left` to `top` and corners `bottom_left` to `top_right`. The names reach solids as roles: an extrusion of `r` has the face `side(r.bottom)` and the edge `lateral(r.bottom_left)`.

| Constraint | Equations | Notes | Phase |
| --- | --- | --- | --- |
| `coincident`, `point_on` | 2 or 1 | Point-on-NURBS adds the curve parameter | 1 |
| `horizontal`, `vertical`, `parallel`, `perpendicular`, `collinear` | 1 each | | 1 |
| `tangent` (G1), `curvature` (G2), `g3` | 1 to 3 | Contact parameters are unknowns; side qualifier stored | 1 (G1), 2 |
| `concentric`, `midpoint`, `symmetric` | 2 each | About a line, or a plane in 3D | 1 |
| `equal` | 1 per pair | Mixed kinds share one value, as in 2D DCM v79 | 1 |
| `fix` | 2 or 3 | Position, or position and orientation | 1 |
| `dim` (distance, angle, radius, diameter, length, curve length) | 1 | Signed variants carry half-space qualifiers | 1 |
| `mirror` | Per entity | About a construction line | 1 |
| `dim_range` | Inequality | Solved by an active set | 2 |
| `pattern` (linear, circular) | Per instance | | 2 |
| `on_plane`, `on_surface`, `along` | 1 or 2 | 3D sketches | 2 |
| Custom equations | 1 | `e1 == e2` over `Expr<T>` (D-ING-9) | 2 |

`dim(target, value)` drives, while `measure(target)` is driven and never writable. A toleranced driving value drives the nominal, and its tolerance becomes PMI when the dimension is marked `pmi`.

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

### Solver

**Decision D-MEC-3:** Geometric constraint solving is one Anvil operation family, `anvil::solve_constraints` and `anvil::analyze_constraints`. It serves sketches, mates, live rules, control-point edits, scan snapping, routing, tolerance completeness and posture. Each built-in constraint has a reference residual in Ingot, which a native kernel replaces only when an oracle proves them equal. Custom constraints are `Expr<T>` functions lowered to Flux's kernel IR. *Why:* the solver has nine clients, runs at 60 Hz during drags and calls Anvil's evaluators in every iteration. *Rejected:* a Wasm component (every iteration would cross the boundary); Ingot (too slow for sparse factorization); separate sketch and assembly solvers (two diagnosis models); a `constraint` keyword. (revised in round 2)

**Decision D-MEC-4:** The solver decomposes the system structurally, solves well-determined blocks numerically on the canonical `linalg` crate, and resolves under-determined parts by minimum displacement from the seeds. A Krawczyk interval test certifies each well-determined block. Applied to the square KKT system of the minimum-displacement problem, which is regular at a strict minimizer, it certifies under-determined parts too. *Why:* the Zou et al. review finds that ill-constrained parts "must be correctly detected and resolved before numerical solving can work". Most sketches are under-constrained, and a residual bounds no error near tangency. *Rejected:* constructive decomposition first (rule repertoires are incomplete); one monolithic solve (conflicts cannot be localized); faer's sparse QR (runtime CPU dispatch, no rank-revealing mode). (revised in round 3)

1. **Lower.** Angles become unit complex numbers and rotations unit quaternions on manifolds (the Ceres `Manifold` pattern); lengths are scaled by the seed box.
2. **Reduce.** Fixed groups collapse into rigid clusters, and equations "solvable alone" substitute forward, as in SolveSpace.
3. **Decompose.** A maximum matching gives the Dulmage–Mendelsohn split into over-, well- and under-determined parts, solved in topological order.
4. **Solve.** Each block runs trust-region Levenberg–Marquardt with rank-revealing QR, or SVD on ambiguous blocks. Above 2,000 unknowns, sparse QR precedes a rank-revealing pass on R.
5. **Certify.** A Krawczyk box gives the `Guaranteed` bound and a unique solution on the branch. Otherwise the bound is `Estimated`, and one above the smallest entity tolerance fails with `IllConditioned`.
6. **Remainder.** Under-determined parts minimize weighted displacement from the seeds, which SolveSpace reports gives "less surprising" drags. Step 5 certifies their KKT system.

[[DIAGRAM diagrams/06-mechanical-constraint-solve-pipeline.jsx: constraint solve pipeline · six steps, three branches]]

Read the top row left to right, then follow each block down through its solve and certification to the result that features receive.

During a drag the moved entity gets a weighted soft target, and each frame is one warm-started solve. The UI streams literal overrides through AGT's `edit.stream` to PLT's `Interactive` lane, and Kiln never caches an overridden result in the shared cache (KLN). Overrides follow `#[was]`, so a concurrent rename does not end the drag.

Builds never warm-start, so results are bit-identical across the canonical class.

### Determinism and seeds

**Decision D-MEC-5:** The coordinates written in a sketch block are seeds, and the solved sketch is a deterministic function of seeds, constraints and the pinned operation version. When driving values move far from the seeds, a predictor-corrector continuation path keeps the solver on the seeds' branch. Discrete qualifiers (angle orientation, tangency side, arc direction) are stored in source when a constraint is created. *Why:* the result must depend on source only, and continuation is the standard remedy for Newton's sensitivity to its start. *Rejected:* solving from the previous session's solution (history-dependent, breaks merges); homotopy that finds all solutions (too slow for interactive use, per the same review).

If continuation cannot reach the targets, the solver returns `BranchFlip` or `NoConvergence` with the last reachable value, never a solution on another branch.

**Decision D-MEC-33:** Seeds stay inline, rounded to a quantum q: the larger of 2¹⁰ρ for the sketch and 10⁻⁶ of its diagonal, in decimal millimetres. Releasing a drag writes only entities that moved by more than q, with more digits wherever rounding would change the solution. *Why:* seeds decide under-determined parts, so they are intent and belong in the text that `crucible export git` carries. *Rejected:* a layout section merged by last writer (it drops one of two concurrent drags); full-precision seeds (many literals per drag, a conflict on every concurrent drag).

Seed literals merge as ordinary literals. Two sides that change the seeds of one under-determined block conflict for real.

### Diagnosis

| `SolveReport` item | Method |
| --- | --- |
| Degrees of freedom | Kernel of the scaled Jacobian, shown as arrows |
| Fully constrained entities | No kernel vector moves the entity's unknowns |
| Redundant and conflict sets | Row dependencies; a deletion filter in canonical order, then a minimality pass; every member offered as a `Fix` |
| Generic or accidental | Rank at a witness built in decomposition order with rational choices, so incidences and tangencies hold exactly |
| Certification | Modular rank and exact kernel vectors on a rational witness; otherwise a nonzero interval minor at a Krawczyk-certified witness, with deficiencies `Estimated` |

Zou and Feng show that the witness configuration method needs a witness satisfying every incidence exactly, and that greedy variants return non-minimal sets.

Curve lengths use Gauss–Legendre quadrature within the certified radius, and 3D sketches drive sweep paths, routes and skeletons. Targets: a 200-entity sketch re-solves in under 2 ms native. A 2,000-entity drag step takes under 8 ms native and 16 ms in the browser.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| 2D sketch solve | `sketch(plane) { … }` through `anvil::solve_constraints` | `Conflict`, `NoConvergence`, `BranchFlip`, `Degenerate`, with the failing block | MEC-O-SK-1, MEC-O-SK-4 | 1 |
| Certified positions | `Guaranteed` from a Krawczyk or KKT box, else `Estimated` | `IllConditioned { block, condition }` | MEC-O-SK-8 | 1 |
| Degree-of-freedom report | `SolveReport` on rational witnesses; modular or interval rank | Uncertified verdicts flagged | MEC-O-SK-2 | 1 |
| Drag | `edit.stream` at 60 Hz on the `Interactive` lane | Holds the last converged frame | MEC-O-SK-5 | 1 |
| Seeds in source | Inline seeds rounded to q | More digits where rounding would change the branch | MEC-O-SK-4 | 1 |
| Named helper entities | Sub-entities of helpers as roles | Unknown name fails to compile | MEC-O-SK-9 | 1 |
| Text | Shaped glyph outlines to regions | `FontMissing { font }` | MEC-O-PF-17 | 1 |
| Splines and helices | Interpolating splines; exact helices | `Degenerate` | MEC-O-SK-6 | 1 |
| NURBS, conics, ellipses | Entities above | `Degenerate` | MEC-O-SK-6 | 2 |
| 3D sketch | `sketch3d() { … }` | As 2D | MEC-O-SK-1 | 2 |
| Inequalities | `dim_range(target, min, max)` | `Conflict` when infeasible | MEC-O-SK-3 | 2 |
| Custom constraints | `Expr<T>` functions in the kernel IR | `ING2402` on branching over unknowns | MEC-O-SK-7 | 2 |

## Part features

### Conventions

**Decision D-MEC-6:** Features that create material from profiles (`extrude`, `revolve`, `sweep`, `loft`, `boundary`, `rib`, `thicken`) return new tool bodies. Booleans are written only with `+`, `-` and `&`, or `combine` for n-ary cases. Features that dress existing geometry (`fillet`, `chamfer`, `shell`, `draft`, `hole`, `thread`, direct edits) take a body and return it modified. *Why:* one spelling per intent; the Boolean is visible in history; Kiln caches the tool body apart from the Boolean. *Rejected:* a result option on every feature, as Onshape's extrude offers New, Add, Remove and Intersect (a second spelling of the same operator).

```
pub feature housing(depth: Length = 30mm) -> Part {
    let block  = sketch(plane.xy) { rect(90mm, 60mm, center: origin) } |> extrude(depth)
    let pocket = sketch(block.face(role: end_cap)) { rect(70mm, 40mm, center: origin) }
                 |> extrude(UpTo(depth - 4mm), dir: -normal)
    let body   = (block - pocket)
                 |> hole(at: block.face(role: end_cap).corners(inset: 8mm),
                         spec: HoleSpec::tapped(ThreadSpec::iso_metric("M5"), depth: 10mm))
                 |> fillet(block.edges(role: lateral(any)), 5mm)
    part(body, name: "Housing").material(alu_6061_t6)
}
```

`Extent` is shared by every profile feature: `Blind`, `Symmetric`, `ThroughAll`, `UpTo(Query)`, `UpToNext(Body)`, `Offset(Query, Length)` and `UpToVertex(Query)`.

`std::mech::refgeom` places sketches, mirrors and patterns with `plane.offset`, `plane.at_angle`, `plane.mid`, `plane.through`, `plane.tangent`, `axis.of`, `axis.through` and `point.on`. Each returns a `CoordSys`-anchored value that re-resolves through its queries. A frame derived from shape (a centroid, an edge midpoint) moves when the face changes shape and carries `Note::ShapeDerivedFrame`, which release checks may forbid.

### Profile features

```
pub feature extrude(profile: Profile, extent: Extent = Blind(10mm), dir: Direction = normal, draft: Angle = 0deg,
                    thin: Option<Length> = none, twist: Option<Field<Length, Angle>> = none,
                    scale: Option<Field<Length, Real>> = none) -> Body
```

`revolve`, `sweep`, `loft`, `boundary`, `thicken`, `rib` and `helix` follow the same pattern. `sweep` takes a path, guides and a `SweepFrame`, by default `RotationMinimizing`, since Frenet frames flip at inflections. `loft` takes sections, guides and end conditions, and twist and scale laws are Fields over distance or path edges.

### Holes and threads

```
pub feature hole(body: Body, at: Query<Point>, spec: HoleSpec, extent: HoleExtent = ThroughAll) -> Body
pub feature thread(body: Body, faces: Query<Face>, spec: ThreadSpec, repr: Repr = Cosmetic) -> Body
```

`HoleSpec` is `simple`, `counterbore`, `countersink`, `counterdrill`, `spotface`, `tapped`, `tapered_pipe` or `clearance`. Every diameter accepts a `Tol<Length>` or an ISO 286 fit code such as `H7`. A hole through several bodies records each segment for fastener stacks.

| Package | Content | Kind | Phase |
| --- | --- | --- | --- |
| `std::standards::iso286` | ISO 286-1:2010 tolerance grades and fundamental deviations | Formulas in std | 1 |
| `std::standards::iso_metric_thread` | ISO 68-1:2023 basic profile; ISO 965-1:2026 tolerance formulas | Formulas in std | 1 |
| `std::standards::unified_thread` | ASME B1.1-2024 profile and tolerance formulas | Formulas in std | 1 |
| `crucible::standards::thread_plans` | ISO 261:1998 and ASME B1.1-2024 diameter–pitch series | Licensed data | 1 |
| `crucible::standards::clearance_holes` | ISO 273:1979 series; inch series | Licensed data | 1 |
| `crucible::standards::pipe_thread` | ISO 228-1:2000, ISO 7-1:1994, ASME B1.20.1-2013 | Licensed data | 2 |
| `crucible::standards::trapezoidal_thread` | ISO 2904:2020, ASME B1.5-1997 | Licensed data | 2 |

**Decision D-MEC-7:** Holes and threads are semantic first: `hole` writes a `HoleSpec` and `thread` a `ThreadSpec` keyed by the created entity ids, and geometry follows from the record. Threads default to `Repr::Cosmetic`. `Repr::Full` builds printed flanks on the mesh path in phase 1, within the 3MF chord tolerance, and exact B-rep flanks from phase 2. *Why:* drawings, PMI, CAM and inspection need the semantics, phase 1 SSI has no helicoid pairs, and 3MF is a mesh anyway. *Rejected:* geometry-only holes recognized later (recognition cannot recover thread series); exact flanks in phase 1 (they need phase 2 intersection classes). (revised in round 3)

### Dress-up features

```
pub feature fillet(body: Body, edges: Query<Edge>, r: RadiusLaw, section: BlendSection = Circular,
                   corners: Corners = Auto, overflow: Overflow = RollOver, fallback: Fallback = Fallback::None) -> Body
```

`RadiusLaw` is a `Length`, `Linear(r0, r1)` or a `Field<Edges, Length>`. `fillet` maps to `anvil::blend`, `face_fillet` to its `FaceFace` variant and `full_round` to `ThreeFace`. ANV owns blend phases, the re-fillet corpus, its success criteria and the stage-1 rule (D-ANV-29). The benchmark must reach 95% on stage-1 configurations at the phase 1 gate and 97% on all configurations at phase 2.

| Blend stage | Capabilities | Phase |
| --- | --- | --- |
| 1 | Constant and linear radius; sequential fillets on blend, offset and swept supports in the phase 1 SSI classes; `RollOver` and `KeepEdge`; valence-3 corners with unequal radii and mixed convexity; chamfer–fillet corners; termination at smooth edges | 1 |
| 2 | Conic and G2 sections; Field radii; face fillets with hold lines; full rounds; chord width; radius edits | 2 |
| 3 | Corners of valence four and above; blends across facet faces | 3 |
| 4 | G3 sections | 4 |

With `fallback: Implicit { max_deviation }`, a failed region becomes an implicit patch fitted G1 to its neighbours. `Note::BlendFallback` states its certified deviation and seam gap.

**Decision D-MEC-34:** The release check `fallback_regions` passes only when three things hold for each implicit fallback region. Its certified deviation lies within the governing profile or general tolerance; no semantic PMI targets it; and the Part's process accepts it. Additive processes take implicit regions through 3MF, while a STEP hand-off (machining, moulding, sheet) needs the region converted to B-rep within the same tolerance. *Why:* the deviation is already certified, and shops' CAM and CMM software read B-rep. *Rejected:* no release check (an implicit region could reach a STEP-only shop); machining meshes with mesh-capable CAM (rare, and CMM programming still needs B-rep).

MFG's process rule names the hand-off, and `check::standards` enforces the decision.

### Patterns, mirror and hulls

```
pub feature pattern<T: Patternable>(seed: T, at: [Keyed<Transform>], mode: PatternMode = Geometry, skip: [Key] = []) -> T
```

The generators `linear`, `circular`, `along`, `at_points`, `fill` and `by_density` return keyed transforms (contract 5). `linear` keys `(i, j)`, `circular` the angular index and `at_points` the anchor's `EntityId`. `fill` keys lattice coordinates from a declared origin, and `by_density` each seed's initial key. Adding a point renames no other copy, and `skip:` lists keys, never positions.

**Decision D-MEC-8:** `pattern` places keyed copies. `PatternMode::Geometry` (default) evaluates the seed once and places copies with one n-ary Boolean; `PatternMode::Feature` re-evaluates the seed per copy, which an extent such as `UpToNext` requires. *Why:* geometry mode is one cached evaluation, and keys keep names and skip lists stable when generators gain or lose points. *Rejected:* always re-evaluating (slow); always copying (wrong for location-dependent extents); positional indices (positional naming under another name). (revised in round 2)

Transforms always keep names. When one operation receives two operands with the same `EntityId`s, as in `half + mirror(half, plane.yz)`, it relabels the later transform's operand with role `copy` or `mirror` (D-ANV-30). An explicit `copy(x)` always copies, and a read-only use of the source renames nothing.

`hull` is exact on meshes and facet faces in phase 1 and bounded on B-rep operands in phase 2, with `minkowski`. `split` cuts by a plane, face set, sheet or sketch, and `combine` is an n-ary Boolean over any representation.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Reference geometry | Planes, axes and points anchored as `CoordSys` | `ResolveError`; `Note::ShapeDerivedFrame` | MEC-O-PF-16 | 1 |
| Extrude | Profile to solid or sheet with roles, draft, twist and scale | `ResolveError` on `UpTo`; `SelfIntersecting` with the largest feasible draft | MEC-O-PF-1 | 1 |
| Revolve | Profile about an axis | `CrossesAxis { segment }` | MEC-O-PF-1 | 1 |
| Sweep | G1 path with a frame rule; exact helical sweeps | `PathNotG1 { vertex }`; `SelfIntersecting` | MEC-O-PF-2 | 1, 2 (guides, laws) |
| Loft | Sections, guides, end conditions, vertex matching | `Twisted` with suggested matches | MEC-O-PF-2 | 1 (no guides), 2 |
| Boundary | Curve network with G0 to G2 edge conditions | `NetworkNotCompatible { curves }` | MEC-O-SF-2 | 2 |
| Thicken, rib | Face set to solid; open profile extended to material | `OffsetSelfIntersection { faces, max_t }` | MEC-O-PF-3, MEC-O-PF-1 | 1 |
| Helix and spiral | Exact `anvil::curve` helices | `Degenerate` on zero pitch | MEC-O-PF-2 | 1 |
| Holes | `HoleSpec`, hole chains | `UnknownSize { series, near }`; `BreaksOut { faces }` | MEC-O-PF-4 | 1 |
| Threads | `Cosmetic`; `Full` on the mesh path, then exact | `ThreadTooLong` | MEC-O-PF-4 | 1, 2 (exact `Full`) |
| Fillets and chamfers, stage 1 | `anvil::blend`, `anvil::chamfer` | `RadiusTooLarge { max_feasible }`, `BlendOverflow`, `VertexBlendFailed` | MEC-O-PF-5 | 1 |
| Blends, stages 2 to 4 | Stage table above | `NoContact`; as above | MEC-O-PF-5, MEC-O-SF-1 | 2, 3, 4 |
| Fallback regions at release | `fallback_regions` (D-MEC-34) | Finding names region, deviation and process | MEC-O-PF-5 | 1 |
| Shell | Uniform or Field thickness | `WallCollapse { region }` | MEC-O-PF-3 | 1, 2 (Field) |
| Draft | Neutral plane on analytic faces; free-form; `anvil::draft`'s parting and step modes | `DraftNotPossible { face, reason }` | MEC-O-PF-6 | 1, 2 (free-form), 3 (parting, step) |
| Patterns | Keyed generators; `skip: [Key]` | `CopyFailed { key, error }` | MEC-O-PF-7 | 1, 2 (along, fill, density) |
| Mirror and copies | Relabeling of colliding operands; `copy(x)` | — | MEC-O-PF-7 | 1 |
| Hull and Minkowski sum | `hull`, then B-rep hulls and `minkowski` | `Degenerate`; `NotConvex { operand }` | MEC-O-PF-18 | 1, 2 |
| Split and combine | `split`, `split_face`, `combine` | `BooleanFailed { faces, reason }`; `EmptyResult` | MEC-O-PF-8 | 1 |

## Direct edits, reuse and generated geometry

### Direct edits and wraps

Direct edits apply to any B-rep, imported geometry included, and are ordinary features in history. `push_pull` offsets faces through `anvil::offset_faces`, and `move_faces` translates, rotates or offsets them under live rules. `replace_faces`, `delete_faces`, `edit_aspect` and `drive` complete the set. Adjacent blends are rebuilt with the same parameters and ids (ANV), or the edit fails with `BlendRegrowFailed` and its fixes.

**Decision D-MEC-9:** Direct edits solve face motions with the shared constraint solver. Each moved or affected face gets a rigid motion or offset unknown, and the edit and live rules are constraints. Anvil's face operations re-intersect neighbours and regrow blends, and recognized rules are written to source. *Why:* Siemens describes synchronous technology as editing while related geometry adjusts "to maintain design intent". Crucible gets that from mechanisms it already has, explicit in source. *Rejected:* a history-free mode (two models of one part); hidden rule inference at every rebuild (results would change with the recognizer). (revised in round 2)

Phase 1 offers push-pull; moves, replacements and rule detection follow in phase 2.

`emboss` raises, engraves or imprints curves on planar and cylindrical faces through the developable wrap, which is isometric and exact. It sweeps the imprinted region along the face normal and joins it by a union or difference. The normal-ruled walls meet the base face along the wrapped curves, so no new intersection class is needed (ANV).

`wrap` also offers `Conformal` and `Geodesic` methods with a distortion Field. `deform(body, map)` takes `bend`, `twist`, `taper`, `stretch`, `cage` or a displacement Field. The Field variant lets a warpage or springback result pre-compensate a tool face and returns the achieved bound.

### Derived parts and families

`derive(source, take, mirror, scale, params)` takes bodies, sketches, frames and parameters from a feature here or in a pinned dependency. A source bump is a Proposal showing the derived geometry diff. `part(body, name, item)` gives a Body identity, and item numbers stay in source.

**Decision D-MEC-10:** A configuration is a parameter record, and a design table is a table of them. A part family is a design table whose rows carry part identity, and suppression is a `Bool` parameter used in an `if`. Assembly variants mark their parameters `#[configuration]`. An Instance's or Instance set's existence depends only on those parameters and constants. An Instance set's member count and placements may depend on any value, keyed by its anchors (contract 6). *Why:* features are already functions of typed parameters, and the existence rule lets Kiln compute the 150% BOM by abstract interpretation. *Rejected:* configurations inside the document, as SOLIDWORKS keeps them (invisible in review); existence from any parameter (enumerated BOMs); a configured fastener count (a two-place edit per hole). (revised in round 3)

```
pub feature conveyor(#[configuration] drive: Drive = Belt, length: Length = 2m) -> Assembly {
    let frame = instance(frame(length), fixed: true)
    let motor = instance(gearmotor_m3())
    let belt  = if drive == Belt { [instance(belt_kit(length))] } else { [] }
    assembly([frame, motor] + belt, mates: [fastened(motor.csys("flange"), frame.csys("drive_end"))])
}
```

`family(f, key:, rows: table { … })` checks every row's types and units at compile time (ING owns the syntax). Each row is a Part with its own item number, and a family is green only when every row passes.

### Lattices

`lattice(region, cell, size, thickness, orientation, skin)` calls `anvil::lattice` and exposes the strut graph. `Cell` covers strut cells (body-centered cubic, octet) and sheet cells of minimal surfaces (gyroid, Schwarz P, diamond). Joining a lattice to a B-rep part keeps the part's exact faces, ids and attributes (D-ANV-2), so GP2's mounting holes keep their `HoleSpec` and GD&T.

Strut cells sign off on Flux's beam-lattice model. Its node-zone length and stiffness factor are calibration data per cell topology over a density range (FLX-O-COUP-2). Sheet cells sign off from phase 2 on shells over the cell field's zero set, from `anvil::mid_surface`'s implicit path. GP2 uses strut cells; a phase 1 sheet-cell lattice has no `SignOff` stress model.

### Machine elements

| Machine element | Contract | Standard | Phase |
| --- | --- | --- | --- |
| Involute spur and helical gears | Module, teeth, pressure and helix angles, profile shift, relief, crowning, accuracy grade | ISO 21771-1:2024 geometry; ISO 1328-1:2013 flank tolerance classes | 2 |
| Bevel, worm, internal gears | As above | ISO 23509-1:2025; ISO 10828:2024 | 3 |
| Shafts | Steps, shoulders, relief grooves, ring grooves, keyways | DIN 509:2022, DIN 471:2026 and DIN 6885-1:2021 forms as licensed data | 2 |
| Bearings, seals, retaining rings | Catalog parts with mating frames and housing fits | Supplier data | 2 |
| Springs | Compression, extension, torsion | | 2 |

Involute flanks are not rational, so gears use B-spline flanks within 0.1 µm (target) and record exact parameters. COV owns gear, bearing and shaft ratings and loaded tooth contact analysis, in phase 2 (contract 13.4). MEC's gear record supplies their inputs: geometry, modifications, accuracy grade and load spectrum. Smooth flank contact is not a singular set (contract 7.1), so root and flank checks can decide.

Drawings carry a gear data table with module, teeth, angles, profile shift, modifications, grade, and span or over-pins measurement. In phase 2 it is GP3's gear output to the shop's own gear process (MFG).

PLT owns contract 13.3's rebuild rows. MEC keeps features cheap: cosmetic threads and geometry-mode patterns keep face counts low, and each feature declares a cost estimate for Kiln's preview scheduler.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Push-pull | `offset_faces` on any B-rep with blend regrowth | `NeighborCannotExtend { face }`, `BlendRegrowFailed` | MEC-O-PF-9 | 1 |
| Move, replace and delete faces | Motions and live rules on the shared solver | `TopologyChange { faces }`; `RuleConflict { set }` | MEC-O-PF-9 | 2 |
| Recognized aspect edits | `edit_aspect` via `recognize_aspects` and `edit_blend` | `NotRecognized` with the best partial match | MEC-O-PF-9 | 2 |
| Emboss and engrave | Developable wrap; region swept along the normal | `WrapOutsideFace` | MEC-O-PF-17 | 1 |
| General wrap and deform | Conformal and geodesic wraps; maps with achieved bound | `FoldOver { region }`; `ToleranceNotMet { achieved }` | MEC-O-PF-10 | 3 |
| Derived parts | `derive` with take, mirror, scale and parameters | `TakeMissing { name }` | MEC-O-PF-11 | 1, 2 (cross-repository) |
| Configurations and families | Parameter records; `#[configuration]` variants; families | `RowFailed { key, error }`; `DuplicateKey` | MEC-O-PF-12 | 1 |
| Lattices | `anvil::lattice` from Flux Fields; leaf-preserving join; strut-cell checks | `BelowMinFeature { region, min }` | MEC-O-PF-13 | 1 |
| Sheet-cell lattice models | Shells on `anvil::mid_surface`'s implicit path | `UnpairedFaces` | MEC-O-PF-13 | 2 |
| Gears | B-spline flanks within 0.1 µm, semantics, accuracy grade, gear data table | `Undercut { teeth, min_shift }`, `PointedTip`, `MeshMismatch` | MEC-O-PF-15 | 2, 3 |
| Shafts and springs | Parametric sections; helical springs | `Degenerate` | MEC-O-PF-2 | 2 |
| Rebuild budget | Feature cost estimates; contract 13.3 rows | Regressions block merges | MEC-O-PF-14 | 1 |

## Assemblies

### Structure

An Assembly is a tree of Instances with placements and mates (contract 5). An Instance references a Part or Assembly feature with parameter overrides, a `Transform` and a representation. An Instance set is one BOM line whose members are keyed by anchors and counted by evaluation (contract 2).

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

Mates attach only to `CoordSys` values, as Onshape's mate connectors are "local coordinate systems located on or between entities". Features publish named frames, `csys(query)` derives one from geometry, and a frame that fails to re-resolve is a `ResolveError` on the mate. `bom_item(item, qty, applies_to)` adds a BOM line without geometry, such as thread-locker or wire sold by length.

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
| `tangent`, `symmetric` | Surface contact; one face pair centered between another | none | 2 |
| `gear`, `rack_pinion`, `screw`, `linear` | Two freedoms coupled by a ratio or pitch | none | 2 |
| `cam` | Follower kept on a cam surface | none | 3 |

**Decision D-MEC-11:** Assembly mates use the same `anvil::solve_constraints` operation as sketches, with one SE(3) unknown per rigid cluster on a product manifold. Fastened Instances merge into rigid clusters before solving, and joint limits are inequalities solved by an active set. *Why:* one solver gives one diagnosis model, with motion arrows, minimal conflict sets and redundancy alike in sketches and assemblies. *Rejected:* a separate assembly solver, the split that D-Cubed's 2D DCM and 3D DCM products reflect (duplicate oracles, different failure semantics); sequential transforms only (cannot close kinematic loops).

Redundant but consistent mates, such as two coaxial hinges on one door, are `Redundant` warnings, which Flux's multibody solver removes or complies.

### Kinematics and motion

```
let study = motion(gearbox(), drive: [(pinion_rev, angle(t) = 360deg/s * t)], t: 0s..2s, samples: 200)
study.require(min_clearance(study, housing, wheel) > 0.5mm)
```

Positions track the drivers by continuation and give `Field<(Instances, Time), Transform>`. Velocities and accelerations solve the differentiated constraints with the Jacobian already factored. A rank drop returns `Singular { t, mates }`, and a reached limit `LimitReached { mate, t }`.

**Decision D-MEC-12:** Dynamics belong to Flux. `motion` handles prescribed-motion kinematics; anything with forces, masses, contact or compliance goes to Flux's multibody solver, which reads the same Assembly. MEC hands over mass properties with their bounds, typed joints, the redundancy report, contact pairs and drivers. *Why:* kinematics reuses the constraint solver; dynamics needs integrators, contact and validity envelopes. *Rejected:* a dynamics engine inside the assembly library (a second physics engine beside Flux).

### Interference and clearance

`interference(asm, classify: true)` uses `anvil::interference`, which computes certified distances and overlap volumes on exact geometry.

| Class | Meaning | Default |
| --- | --- | --- |
| `Hard` | Positive interference volume | Error |
| `Touching` | Zero gap within the entity tolerance | Info |
| `IntendedThread` | Fastener thread inside a mating `ThreadSpec` | Ignored |
| `IntendedFit` | A touching cylindrical pair whose fit codes interfere | Interference from the `Tol` limits reported to tolerancing |
| `Clearance` | Gap below a declared minimum | Error when declared |

Geometry is built at nominal, so a 10 H7/p6 press fit touches, and only its fit codes make it `IntendedFit`. KLN's merge condition 5 reuses these classes. Contact explained by a mate, a `Weld`, a fastened joint or an `IntendedFit` never conflicts.

Motion studies sample adaptively. Between samples, a certified Taylor bound limits each body's displacement, from interval Newton on the differentiated constraints. Clearance is the interval [sampled minimum − that bound, sampled minimum], so `min_clearance` decides three-valued. Where the enclosure fails, the interval is `Estimated`, and a check that needs `Guaranteed` bounds returns `Undecided`.

`check::enclosure` checks clearance, keep-ins and connector cut-outs against boards from other ECAD tools. It reads STEP board assemblies in phase 1 and uses ECO's IDF and STEP board readers in phase 2.

### Exploded views, subassemblies and interfaces

`explode(asm, steps)` stores ordered steps; `explode_auto` proposes them from a non-directional blocking graph (Wilson and Latombe, 1994). A subassembly Instance is rigid by default; `instance(sub, flexible: true)` exposes its free internal freedoms.

**Decision D-MEC-13:** Cross-part references go only through skeletons and interface records, both ordinary Ingot values. A skeleton is a feature returning frames, sketches, surfaces and parameters. An interface is a record marked `#[interface]` that one part provides and another consumes, with a derived `compatible(a, b)` check. Implicit in-context references that capture another part's geometry are not supported. *Why:* explicit dependencies keep the graph acyclic and visible in review, and semantic merge stays possible. *Rejected:* edit-in-context with captured references, as in SOLIDWORKS (hidden coupling); an `interface` keyword (contract section 6). (revised in round 2)

```
#[interface]
pub record MotorMount { pilot: CoordSys, pilot_d: Tol<Length>, bolts: [CoordSys], thread: ThreadSpec }
```

`mate_interface(a, b)` places both sides with one mate and checks compatibility; electronics uses the same records for board outlines and keep-outs.

### Large assemblies

| `InstanceRepr` | Content | Error stated |
| --- | --- | --- |
| `Full` | Exact B-rep, loaded on demand | None |
| `Graphics` | Cached `DisplayPackage` levels of detail | Chordal deviation per level |
| `Envelope` | Oriented box or convex hull | Hull deviation |
| `Shrinkwrap(gap)` | One closed skin from `anvil::shrinkwrap` | Bound from the operation |
| `Defeatured(rules)` | Small aspects removed by `anvil::defeature` | Removed aspects and volume change |
| `Excluded` | Not loaded | Excluded from mass properties, with a warning |

Opening loads structure and cached tessellations first, and B-reps only for Instances being edited or checked. Contract 13.3 sets scene capacity from phase 2. MEC adds a target: a 100,000-Instance assembly opens for viewing in under 15 s, from phase 4.

### Standard parts and fasteners

| Data package | Examples | Phase |
| --- | --- | --- |
| `crucible::standards::iso_fasteners` | ISO 4762, 4014, 4017, 4032, 7089, 10642 | 2 |
| `crucible::standards::din_fasteners` | DIN 912, 933, 934 and other legacy designations mapped to ISO | 2 |
| `crucible::standards::ansi_fasteners` | ASME B18.3, B18.2.1, B18.2.2 | 2 |
| `crucible::standards::pins_rings` | Dowel pins, retaining rings, keys | 2 |
| `crucible::standards::self_clinching` | Self-clinching nuts, studs and standoffs | 2 |

Each package carries a `DataLicence` and records its edition (D-MEC-31).

`fasten(holes, spec)` returns an Instance set keyed by hole `EntityId`s, so adding a hole changes its quantity, never the BOM structure. Per hole it computes grip from the stacked `HoleSpec` segments, adds the minimum engagement and picks the shortest standard length. Each member records preload and tightening torque for Flux's bolted-joint forms.

Selection resolves over the organization's approved parts first (KLN). Reaching the open catalog needs a recorded Waiver, so design, ERP and shop BOMs agree.

### Mate inference and assembly-level features

`suggest_mates(a, b)` ranks candidates from interfaces, recognized aspects and an optional learned ranker. Suggestions become mates only when accepted. The ranker's benchmark comes from std assemblies and golden products (D-MEC-37); JoinABLe's reported 79.53% top-1 is literature only.

An assembly-level cut or hole states its mode. `DerivedParts` creates derived Parts with new item numbers, while `AfterAssembly` is a manufacturing operation in the MBOM (D-ANV-30).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Instances and structure | `instance`, `assembly`, Instance sets, `#[configuration]` existence | `ResolveError` on a mate frame; `ING2601` | MEC-O-AS-1 | 1 |
| BOM-only items | `bom_item` with the Item's unit | `UnitMismatch { item, unit }` | MEC-O-AS-9 | 1 |
| Mate solve and diagnosis | Mates above on the shared solver | `Conflict`, `Redundant` (warning) | MEC-O-AS-1 | 1, 2, 3 (cam) |
| Kinematics | `motion` → `Field<(Instances, Time), Transform>` | `Singular { t, mates }`, `LimitReached { mate, t }` | MEC-O-AS-2 | 2 |
| Static interference | Classified clashes; `IntendedFit` from fit codes | `WorkLimit` | MEC-O-AS-3 | 1 |
| Dynamic clearance | Taylor-bounded intervals; three-valued `min_clearance` | `Undecided` near singular positions | MEC-O-AS-10 | 2 |
| Enclosure checks | Clearance, keep-ins and cut-outs against imported boards | Findings as check Fields | MEC-O-AS-11 | 1, 2 (board readers) |
| Exploded views | Ordered steps; automatic proposals | `CollidesDuringStep { step, pair }` (warning) | MEC-O-AS-5 | 2, 3 (automatic) |
| Flexible subassemblies | `flexible: true` | Conflicts list inner mates by path | MEC-O-AS-1 | 2 |
| Skeletons and interfaces | Skeleton features; `#[interface]` records | `Incompatible { field, provided, required }` | MEC-O-AS-8 | 1 (skeletons), 2 |
| Large-assembly representations | `InstanceRepr`; 100,000-Instance open | `ReprUnavailable { instance, repr }` | MEC-O-AS-4 | 2, 4 (100,000-Instance open) |
| Fasteners | Instance sets keyed by holes; grip, engagement, length, preload | `NoStandardLength { needed, nearest }`, `EngagementTooShort` | MEC-O-AS-6 | 2 |
| Approved-parts selection | Approved parts first; open catalog only with a Waiver | `NotApproved { part }` | MEC-O-AS-9 | 2 |
| Mate inference | Ranked suggestions | — | MEC-O-AS-7 | 3 |
| Assembly-level features | `DerivedParts` or `AfterAssembly` | Omitting `mode` fails to compile | MEC-O-AS-12 | 2 |

## Surfacing

### Continuity and surfaces

`Continuity` is `G0` to `G3`: shared position, tangent plane, normal curvature, then its derivative. Surfacing features take target continuities per edge and return a `ContinuityReport` from `anvil::analyze_continuity`. Thresholds are relative to the Body's resolution and size by default, so hull fairing and MEMS share one rule. A feature that misses its targets returns `ContinuityNotMet { edge, achieved }` and never relabels the result.

| Feature | Contract | Phase |
| --- | --- | --- |
| `curve_through`, `iso_curve`, `project`, `intersect`; curvature combs | Derived curves | 1 |
| Extruded, revolved, ruled and swept surfaces; `trim`, `sew`, `knit_to_solid` | Profile features with `solid: false` | 1 |
| `curve_cv`, `blend_curve`, `offset_curve`, `rebuild_curve` | Control-point NURBS, G0 to G3 bridges, offsets, refits with a bound | 2 |
| `boundary`, `fill`, `blend_surface`, `match`, `extend`, `offset_surface` | Network and n-sided surfaces, bridges and matches to G2 | 2 |
| `network(u, v, tol)` | Least-squares fit to a curve network with gaps up to `tol` | 3 |
| `edit_cv` with the drag fast path; G3 `match` and `blend_surface` | Control-point editing on the shared solver | 3 |

### Surface-quality checks

Every analysis (curvature, zebra, highlight lines, continuity, draft, deviation, control-net quality) is a Field that the UI paints and checks constrain.

Class-A work is a loop of control-vertex edits under live zebra and curvature feedback. `edit_cv` therefore re-evaluates the dragged patch on the GPU at `Preview` fidelity within 16 ms (target). Release writes one Ingot edit that rebuilds normally.

**Decision D-MEC-14:** Surface quality is a check library over analysis Fields plus a control-vertex drag fast path, not a mode. Capability statements say "surface-quality checks" until control-vertex editing and G3 matching and blending ship together in phase 3. *Why:* checks let agents and CI enforce surface quality as they enforce stress limits; claiming Class-A before the modeling loop exists would overstate the product. *Rejected:* a separate Class-A workbench (an island with its own rules); edits only through full rebuilds (too slow). (revised in round 2)

### SubD and scans

SubD cages are a `Body` representation edited through `anvil::subd_edit`, with gestures written to source. Rhino 8's `ToNURBS` output is "always G2 in smooth SubD regions". It offers G0 to G2 at extraordinary vertices and warns that forcing G2 "adds bulges or dents".

**Decision D-MEC-15:** `to_nurbs` converts regular regions exactly, packs quad grids into larger patches by default, and defaults to G1 at extraordinary vertices with the deviation from the limit surface reported. G2 is an explicit option whose shape change is also reported. *Why:* manufacturing and STEP exchange need NURBS, and the conversion must state what it changed. *Rejected:* G2 by default (silently changes shape); SubD only (no AP242 path).

A SubD body may join a B-rep part during design, and release converts it where the process needs B-rep (D-MEC-34). `scan_to_cad` registers scans with `anvil::align` and segments them by curvature or a learned segmenter. It fits primitives by deterministic RANSAC and faired NURBS elsewhere, and sews a solid with a deviation Field. Point2CAD (CVPR 2024) reports a new state of the art on ABC with an implicit neural representation; Crucible stays analytic-first.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Continuity reports | Per-edge reports; scale-relative defaults | `ContinuityNotMet { edge, achieved }` | MEC-O-SF-1 | 1 (G0 to G2), 2 (G3) |
| Basic curves and surfaces | Derived curves, profile surfaces, trim and sew | `Degenerate`; `BoundaryNotClosed { gap }` | MEC-O-SK-6, MEC-O-SF-2 | 1 |
| Freeform curves and surfaces | Bridges, offsets, refits; boundary, fill, blend and match to G2 | `NetworkNotCompatible { curves }` | MEC-O-SF-2 | 2 |
| Network fitting | Least squares with gaps up to `tol` | `ToleranceNotMet` | MEC-O-SF-2 | 3 |
| Surface-quality checks | Analysis Fields as checks | — | MEC-O-SF-1 | 2, 3 (highlight lines, control net) |
| Control-vertex editing | `edit_cv` with the 16 ms fast path; G3 matches | Fast path falls back to the rebuild | MEC-O-SF-5 | 3 |
| SubD modeling and conversion | Cage edits with stable ids; `to_nurbs` | `NonManifoldCage { edges }`; `ConversionDeviation { max }` | MEC-O-SF-3 | 3 |
| Scan to CAD | Registration to sewn solid | `FitRejected { region, rms }` | MEC-O-SF-4 | 4 |

## Sheet metal

A sheet-metal part is a `SheetBody`: the folded `Body`, the flat `Body`, a bend table and `SheetParams`. Every feature updates both states, as in Onshape, where operations are "automatically represented as a flat pattern".

**Decision D-MEC-16:** The flat pattern is maintained by every sheet-metal feature, not computed at the end. *Why:* designers see flat-pattern errors at the feature that causes them, and a cut drawn flat maps back through the same fold map. *Rejected:* an unfold feature at the end of history (errors appear late and far from their cause).

The neutral fiber lies at K·t from the inside surface. For bend angle θ, inside radius R and thickness t, the bend allowance is BA = θ·(R + K·t). The outside setback is OSSB = (R + t)·tan(θ/2), and the bend deduction BD = 2·OSSB − BA. `BendRule` is `KFactor(k)`, `Allowance(table)`, `Deduction(table)` or `Table(BendTable)`.

The neutral fiber moves inward as R/t falls. The default rule therefore reads K from MFG's press-brake allowance data indexed by R/t, in phase 2 (contract 13.4). Onshape's constants (0.45 for bends, 0.5 for rolled walls) are only a labelled fallback, and the bend table prints each bend's K.

| Feature | Contract | Phase |
| --- | --- | --- |
| `sheet_from`, `contour_flange`, `convert_to_sheet` | Base from a profile or path; a converted solid with rips | 2 |
| `flange`, `miter_flange`, `hem`, `jog`, `sketched_bend` | Flanges with length and position rules; hems | 2 |
| `corner`, `bend_relief` | Closed corners; rectangular, obround and tear reliefs | 2 |
| `in_flat { … }` | Features drawn flat, mapped through the fold map | 2 |
| `form(tool, at, orient)` | Louvers, lances, dimples, beads, extruded holes | 2 |
| `make_joint`, `make_rip` | Convert between bend and rip | 2 |
| `lofted_bend`, `tab_slot` | Transitions with stated deviation; tabs and slots | 3 |

`flat(sheet)` returns a `FlatPattern` with outline, `BendLine`s, footprints and grain, which MFG's bend sheets read. `export_flat_dxf` maps it onto layer conventions held as data.

`check::sheet` checks inside radius and flange length against MFG tooling data. It flags features closer than 2·t + R to a bend, missing reliefs, flat self-overlap and bends across the grain.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Sheet model and bend rules | `SheetBody`; K factor, allowance, deduction and table rules; default K by R/t | `OutsideBendTable { key, range }` | MEC-O-SM-1 | 2 |
| Sheet features | Features above, both states updated | `FlangeCollides { faces }`, `UnfoldFailed { bend, reason }` | MEC-O-SM-2 | 2, 3 |
| Flat pattern | `flat(sheet)` through `anvil::unfold` | `NotDevelopable { faces, deviation }` | MEC-O-SM-2 | 2 |
| Flat DXF export | Layer conventions as data | `UnmappedLayer { kind }` | MEC-O-SM-4 | 2 |
| Self-clinching hardware | Catalog data and installation checks | `ClinchRuleViolated { rule, value, limit }` | MEC-O-SM-4 | 2 |
| Sheet checks | `check::sheet` | Findings with fixes | MEC-O-SM-3 | 2 |

## Weldments and structural frames

```
pub feature base_frame() -> Part {
    let sk = sketch3d() { … }                                   // skeleton lines
    let t  = member(sk.edges(role: any), profile: en10365::section("HEA 120")) |> trim(corners: Corner::Miter, gap: 1mm)
    let w  = weld(t.joints(any), Weld::fillet(a: 4mm, all_around: true, quality: Iso5817(C)))
    part(t, name: "Base frame", execution_class: Exc2).welds(w)
}
```

Members record profile, anchor and rotation, so Flux models them as beams on `anvil::member_axes`. Welds carry semantics to MFG and Flux, and neither needs bead geometry.

A `Weld` records type, size, length, pitch, process, contour, finish and the imperfection quality level. The level is ISO 5817 B, C or D or AWS D1.1 acceptance criteria, and it feeds inspection plans. A weldment Part records `execution_class: Exc1..Exc4` from EN 1090-2:2018+A1:2024. MFG derives quality levels, NDT extent and the ISO 3834 part from it, and enforces it for GP8 in phase 5.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Structural members | Profiles swept along skeleton segments; axes for Flux beams | `ProfileNotFound { designation, near }` | MEC-O-WD-1 | 2 |
| Profile catalogs | EN 10365:2026, EN 10210-2:2019, EN 10219-2:2019; AISC Shapes Database v16.0; licensed data | Pinned data packages | MEC-O-WD-1 | 2 |
| Trims, gussets, end caps | Miter, butt and coped trims with weld gap; plates at joints | `TrimAmbiguous { joint }`; `NoRoom { joint }` | MEC-O-WD-2 | 2 |
| Weld beads | `Weld` records; `Cosmetic` by default, `Simplified` beads for mass | `WeldPathOpen`, `SizeExceedsThroat` | MEC-O-WD-3 | 2 |
| Weld symbols | AWS A2.4:2020 or ISO 2553:2019 | Missing fields for the standard | MEC-O-WD-3 | 2 |
| Execution class | `execution_class` on weldment Parts | Missing class on a structural weldment (warning) | MEC-O-WD-3 | 2 |
| Cut list | Bodies grouped by profile, length, end angles and features | Mixed materials in one group | MEC-O-WD-2 | 2 |

## Composites design

A composite Part is a tool surface plus a laminate definition; the laminate is data, and the solid derives from it. MEC owns composite laminates in phase 4 (contract 13.4), and COV owns constitutive draping and cure simulation in phase 5.

```
let lam = laminate(tool: skin.faces(role: outer_mold_line), rosette: rosette(origin: skin.csys("root"), zero: x), plies: [
    ply("P1", carbon_t700_twill, 0deg,  boundary: full),
    ply("P2", carbon_t700_ud,    45deg, boundary: zone_a, drop_off: 3mm),
], symmetric: true)
```

Kinematic draping follows the method Creo documents. Inextensible fibres cross at drape points a constant step apart, and a seed point and two fixed fibres fix the solution.

**Decision D-MEC-17:** Kinematic draping is the default for design, labelled as a geometric approximation that ignores material mechanics. Ply checks flag shear above the locking angle stored in the `Material`. *Why:* it is fast enough for interactive design and is the method Creo documents; forming simulation needs calibrated material models many users lack. *Rejected:* forming simulation by default (slow, needs calibrated data).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Plies, sequences and zones | Plies with boundary, splice and dart; zones; symmetry and balance | `UnbalancedLaminate { zone }` (warning) | MEC-O-CP-2 | 4 |
| Rosettes and cores | Translation, radial, cylindrical or Field rosettes; honeycomb and foam cores | `ResolveError` on the rosette frame | MEC-O-CP-1 | 4 |
| Kinematic drape | Fibre directions and shear as Fields per ply | `ShearLimitExceeded { ply, region, max }` with "add dart" | MEC-O-CP-1 | 4 |
| Solids and ply flats | Tool surface offset by ply thickness with drop-offs; flat ply outlines | `OffsetSelfIntersection` | MEC-O-CP-1 | 4 |
| Laminate properties | Per-zone ABD matrices for Flux shells | — | MEC-O-CP-2 | 4 |
| Ply book and exchange | Per-ply views, sequence tables; AP242 composites per the CAx-IF Recommended Practices for Composite Materials v4.4 | Unmappable items reported | MEC-O-CP-2 | 4 |

## Molded and cast part design

**Decision D-MEC-18:** Wall thickness is measured by two methods, ray thickness and rolling-ball thickness (the largest inscribed sphere), and both are Fields. GPU results only order work and seed upper bounds, and the CPU proves the minimum by branch-and-bound with certified lower bounds, so the Fields have grade `Certified`. *Why:* a ray from a rib root can miss the thick junction that the sphere measures, while rays match caliper readings. A minimum is global, so GPU candidates alone could miss a region. *Rejected:* a single method (each misleads in known cases); GPU candidate sets as the search space (results would depend on the GPU). (revised in round 3)

The reported location is the canonically first point within the decision band, by canonical face number, then (u, v) on a fixed dyadic grid.

`check::molding_design` has defaults that MFG data override: ribs at most 60% of the adjoining wall (moulders' guides give 40 to 60%), bosses about twice the inner diameter, and 0.5° draft plus the texture allowance. Fill, pack, cooling and warpage are MFG's in phase 3, and casting simulation in phase 6 (contract 13.4).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Draft analysis | `draft_angle(body, pull) -> Field<Faces, Angle>` with classes | — | MEC-O-PF-6 | 1 |
| Wall thickness | `thickness(body, method) -> Field<Body, Length>`, `Certified` through `anvil::thickness` | — | MEC-O-MD-1 | 1 |
| Parting line and surface | Lines ranked by undercut area; extended, ruled or swept surfaces; shut-offs | `NoParting { reason }` | MEC-O-MD-2 | 3 |
| Core, cavity and side actions | `split_mold(body, shrink, parting, block)`; lifter and slide directions | `NegativeDraft { faces }` | MEC-O-MD-2 | 3 |
| Ribs, bosses, snap fits | Parametric features with ratio rules | `RatioExceeded { rule }` (warning) | MEC-O-MD-1 | 3 |
| Shrinkage and compensation | Anisotropic scale, or `deform(field)` from a warpage Field | `ToleranceNotMet { achieved }` | MEC-O-PF-10 | 3 |
| Cast parts | Machining stock, cores, draft and minimum section | `SectionTooThin { region }` | MEC-O-MD-1 | 4 |

## Routing

A `Route` is a 3D path between two ports, a `RouteSpec`, placed fittings and segment bodies. Ports are `CoordSys` values with a connection type, and route points are 3D-sketch unknowns constrained to clearances, supports and orthogonal runs. Automatic routing runs A* over a voxel grid of free space and smooths the path into the spec's bend rules.

**Decision D-MEC-26:** Harness work splits three ways: MEC owns 3D routing, bundle and formboard geometry, ELX owns connectivity and wire tables, and MFG owns the manufacturing package. Phase 3 routes use declared bundle diameters; from phase 4, diameters come from ELX's wire list. *Why:* each tab owns what it computes, and the round 1 drafts claimed the formboard twice. *Rejected:* MEC owning the formboard drawing (a manufacturing document); ELX flattening MEC's 3D topology (geometry belongs with the routes).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Route model and tubes | Ports, specs, fittings, segment bodies; bend radius, straights, springback | `NoRoute { blocked_by }`; `BendTooTight { at, radius, min }` | MEC-O-RT-1 | 3 |
| Hose | Minimum bend radius; free shape from Flux's rod statics | `BendTooTight` | MEC-O-RT-1 | 3, 4 (free shape) |
| Harness bundles | Branches, clips, grommets; declared diameters, then ELX wire lists | `SupportSpacingExceeded { span }` | MEC-O-RT-1 | 3, 4 |
| Bundle shape | Cosserat-rod centreline (`flux::solve_rod`) | `NonlinearDiverged` with the last state | MEC-O-RT-1 | 4 |
| Formboard geometry and lengths | Branches at true length; 3D lengths with service loops | `FormboardOverlap { branches }` | MEC-O-RT-3 | 4 |
| Rigid pipe and HVAC duct | Fittings and schedules from licensed data (ASME B36.10M and B36.19M, EN 10220, SMACNA), each package recording its edition | `FittingNotInSpec { size }` | MEC-O-RT-2 | 5 |

## Large structures, micro scale and soft goods

The scale requirement, from MEMS to ships, is met by composition: members, sheets, surfacing checks, flattening and Field-driven geometry.

| Domain | Native in std | Interop | Phase |
| --- | --- | --- | --- |
| Steel structures | Building-scale members, bolted plates, member Fields from Flux beams | IFC 4.3 (ISO 16739-1:2024) | 5 (GP8) |
| Plates and stiffened panels | Sheets with thickness Fields; stiffeners as members | AP242 | 5 |
| MEMS layer stacks | `process_stack(layers)`: deposit, pattern, etch, release | Masks on `anvil-planar`; GDSII and OASIS through ECO | 5 (GP7) |
| Ship hulls | Fairness checks; displacement, centres and waterplane | Offsets tables | 7 (GP13) |
| Building structure | Steel and timber members, not BIM authoring; IFC 4.3 is the latest official version | IFC exchange | 7 (GP14) |
| Soft goods | Flattened pattern pieces with seams, notches, grain lines and stretch ratios | DXF patterns | 7 (GP16) |

Patterns and `wrap` share Boundary First Flattening through `anvil::parameterize`; its authors report a cost "about 50x less" than prior boundary-controlled methods.

**Decision D-MEC-19:** Large structures, MEMS and soft goods arrive in phases 5 to 7 with GP7, GP8, GP13, GP14 and GP16, reusing MEC mechanisms plus a few domain features. *Why:* the scale requirement is met by composition, and golden products 1 to 6 need none of these domains. *Rejected:* dedicated workbenches per domain now (they would dilute phases 1 to 4). (revised in round 2)

Out of reach, stated plainly: Crucible does not replace naval architecture suites for class approval, BIM authoring or TCAD process simulators. It exchanges with them through open formats.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Steel structures and panels | Members, bolted plates, stiffened sheets; IFC 4.3 round trip | `UnmappedEntity { kind }` | MEC-O-LS-2 | 5 |
| MEMS layer stacks | `process_stack` builds Bodies from layer operations | `LayerUndercut { layer, region }` | MEC-O-LS-4 | 5 |
| Hull fairing and hydrostatics | Fairness checks; hydrostatic properties | `HullNotClosed { gaps }` | MEC-O-LS-1 | 7 |
| Soft-goods patterns | Flattened pieces with seams and stretch ratios | `NotDisk { genus }` with cut suggestions | MEC-O-LS-3 | 7 |

## Tolerancing

### Specification model

Size tolerances are `Tol<T>` values (contract 5), and `fit(10mm, H7)` returns one from `std::standards::iso286`. Geometric tolerances are records attached to shape aspects, one per feature control frame.

```
pub record GeometricTolerance {
    characteristic: Characteristic,
    zone: Zone,                       // width, shape, disposition
    segments: [Segment],              // composite and multi-segment frames
    modifiers: [Modifier],            // material condition, projected, free state, dynamic profile, statistical, …
    datums: Option<DatumSystem>,      // primary, secondary, tertiary; optional customized frame
    pattern: Option<PatternSpec>,     // CZ, CZR, SZ or SIM; ASME simultaneous unless separate: true
    indicators: [PlaneIndicator],     // intersection, orientation, direction-feature and collection planes
    size: Option<SizeSpec>,           // TwoPoint, LeastSquares, MaxInscribed, MinCircumscribed, Rank(..); envelope
    target: Query<ShapeAspect>,       // a face set, a feature of size, a pattern, or all over
}
```

```
let a = datum("A", plate.face(role: start_cap))
let b = datum("B", plate.face(role: side(outline.left)))
let c = datum("C", plate.aspect(created_by: locating_pin_hole))
plate.general_tolerance(GeneralTolerance::iso2768("m"))
     .tolerance(plate.aspects(created_by: mount_holes), position(dia(0.1mm), mmc, datums: [a, b, c.at(mmb)]))
     .tolerance(plate.faces(all), profile(0.2mm, datums: [a, b, c]))
```

`Characteristic` covers form, orientation, location, profile and runout, plus concentricity, coaxiality and symmetry in the ISO dialect only. ASME Y14.5-2018 deleted concentricity and symmetry and added the dynamic profile modifier, which controls form but not size. ING turns the commonest misuses into compile errors (D-ING-6).

A `Datum` may list `DatumTarget { kind: Point | Line | Area(shape), movable }` entries for castings and sheet metal. Edges of undefined shape carry ISO 13715:2017 callouts, which MFG reads for edge breaks.

A `Tol` forwarded into a feature becomes PMI as an anchored aspect query keyed by the feature's `CallSite`, re-resolved on the final Part (contract 5). For `extrude(4mm ± 0.1mm)` the query is `OfSize { faces: [start_cap, end_cap] }`.

**Decision D-MEC-27:** Every PMI item, forwarded or explicit, has an `Error`-severity check `pmi_target_resolved`, and GD&T and PMI attributes use Anvil's split policy `Fail`. When a later operation splits, merges or deletes a target, the check fails with `ToleranceTargetSplit { control, pieces }` or the `ResolveError`. Its fixes re-target the pieces as one pattern, select one piece, or insert an explicit `part.tolerance(…)` for a forwarded item. *Why:* `Copy` would silently turn one zone into several, and a forwarded tolerance has no control statement to fail instead. *Rejected:* `Copy` (silent change of meaning); `Drop` (loses the requirement); `Divide` (meaningless for zones); a Note for forwarded items (the tolerance would vanish from the drawing). (revised in round 3)

ANV keeps `Note::AttributeSplit` on the operation, and MEC owns the failure.

**Decision D-MEC-35:** A Part declares its general tolerance with `part.general_tolerance(spec)`: an ISO 2768-1:1989 class, an ISO 22081:2021 general specification, or ASME title-block decimal rules. Stacks, characteristic extraction, inspection plans, cost and KLN's definition tolerance read it for every untoleranced size, location and angle. Reports label those contributors "general", and a Part without one fails `check::standards` before release. *Why:* most dimensions carry no explicit tolerance, and counting them as exact understates every stack. *Rejected:* a drawing-only note (stacks and inspection never see it); a silent default class (the requirement must be written).

The record applies at the tolerancing layer, so Ingot arithmetic is unchanged; ISO 2768-2 is withdrawn in favour of ISO 22081.

### Two dialects, one model

**Decision D-MEC-20:** GD&T has one semantic model with two dialects, ASME and ISO GPS, each a validator, a renderer and a default specification operator; a design declares its dialect. `gdt::convert_dialect` translates only controls with an exact equivalent; every other control becomes a typed hole (`ING6001`) stating the reason and clause. *Why:* ASME's size tolerance also controls form, while ISO 8015 meets each tolerance independently [Keyence GD&T basics]. Approximate translation manufactures to the wrong requirement. *Rejected:* two models (every control written twice); approximate conversion; a default by locale. (revised in round 3)

| Dialect default | ASME | ISO |
| --- | --- | --- |
| Standards | Y14.5-2018, reaffirmed in 2024 and on stabilized maintenance | ISO 1101:2017, 5459:2024, 5458:2018, 2692:2021, 14405-1:2025, 8015:2011, 22081:2021 |
| Regular feature of size | Envelope at maximum material (Rule #1, Y14.5-2018 section 5.8.1, per GD&T Basics) unless independency is noted | Two-point size without form limitation unless Ⓔ |
| Material requirements | Modifiers on features of size | MMR, LMR and reciprocity (ISO 2692) |
| Pattern zones | Simultaneous unless `separate: true` | CZ, CZR or SIM only when written (ISO 5458) |

Validation checks modifiers, datum references and material conditions against the characteristic and the feature of size. A failure returns `InvalidControl { rule, clause }` with a fix such as "use position, profile or runout instead of concentricity".

ASME's mathematical definition, Y14.5.1-2019, is "consistent with the principles and practices of ASME Y14.5m-1994". `std::mech::gdt::asme` therefore defines zone mathematics for each 2018-only construct, citing ISO 17450-1 operators where they apply. Reports mark these definitions `CrucibleDefined`.

### Completeness

**Decision D-MEC-21:** Specification completeness is a degree-of-freedom analysis on `anvil::analyze_constraints` plus three coverage rules. Each toleranced aspect gets six small-displacement unknowns, minus those that leave its surface class invariant, including one for the helical class. Coverage needs a size control on every feature of size, a form control on every surface and a precedence-suited form control on every datum feature. *Why:* one diagnosis model finds under-specified directions automatically, and degrees of freedom alone call a cylinder with position but no size complete. *Rejected:* rule lists per aspect type (no geometric basis); degrees of freedom only. (revised in round 3)

The invariant counts are planar 3, cylindrical 2, spherical 3, helical 1 (a screw motion), prismatic and revolute 1, and complex 0 [Homri, Teissandier and Ballu, after Clément]. Free unknowns show as arrows, and faces under a general tolerance or general profile count as controlled. Sigmetrix GD&T Advisor shows "what features have been completely controlled, partially controlled, or not yet controlled at all"; MEC adds the geometric reason.

### Stack-up and variation analysis

| Method | Contract | Phase |
| --- | --- | --- |
| Worst case | Affine `Tol` sum over a closed, signed chain, general tolerances included | 1 |
| RSS | ING's `.rss(coverage:)`: the quantile of the linear combination, intersected with the worst case; Bender's 1.5 inflation as an option | 1 |
| 1D sampling | Randomized quasi-Monte Carlo over contributor distributions | 1 |
| 3D linear | Sensitivities of measurements to every aspect's small displacements | 2 |
| 3D zone path | Torsors per toleranced aspect, datums re-established, the mate system re-solved | 2 |
| 3D rebuild path | ING's `vary` over size tolerances that change topology or contact, rebuilt per sample | 2 |
| Compliant variation | The zone path plus Flux influence coefficients, for sheet-metal and welded assemblies | 2 |
| Tolerance allocation | Zone widths minimizing MFG cost at a target yield | 3 |
| Skin model shapes | Form deviations as `Field<Faces, Displacement>` | 4 |

**Decision D-MEC-28:** MEC owns the default distribution for every statistical call, `std::mech::tol::default_distribution`. It is uniform within the limits when no process data exist, and normal with the mean shift and spread from Cp and Cpk when an MFG process profile supplies them. For a zone with several parameters, uniform means uniform over the admissible torsor set. ING's `.rss()` and Flux's `std::uq::propagate` use it, and reports print what they assumed. *Why:* without data a uniform distribution assumes least, and process data bring mean shift, which makes plain RSS unconservative. *Rejected:* normal ±3σ without data (assumes a capable, centered process); one default per tab. (revised in round 3)

**Decision D-MEC-22:** 3D variation has two paths. The zone path, the default, samples small-displacement torsors per toleranced aspect and applies them to mating frames and contact features. It re-establishes datums by the dialect's rule (ASME datum feature simulators, ISO 5459 association) and re-solves only the mate system, warm-started from nominal. The rebuild path uses ING's `vary` for size tolerances that change topology or contact. *Why:* GD&T zones have no literal to override, and re-solving only mates meets the throughput target. *Rejected:* a rebuild per sample for every tolerance (too slow); Jacobian-only analysis (misses float and contact switching); unseeded Monte Carlo; orders from names. (revised in round 3)

Both paths draw scrambled Sobol points in ING's name-free symbol order, seeded from argument values and input `GeometryId`s. Yields use smoothed indicators, and repeated scrambles give the statistical part of the error budget. Symbols equal under every key of ING's order are exchangeable, so ties give identical bits. Targets on the reference laptop: 20,000 zone-path samples of a 50-part stack in under 60 s, and 1,000 rebuild-path samples of GP3 in under 10 minutes.

Skin model shapes (Anwer, Schleich, Mathieu and Wartzack, 2014) handle form deviations, and Flux consumes MEC's samples. Until phase 4, sampling displaces ideal features, with ASME's envelope bounding size and orientation jointly. Above 4,096 symbols, symbols below 10⁻⁶ of the form's radius fold into the remainder, and reports count them (ING). Physics quantities under tolerances use FLX's `std::uq::worst_case`, whose bound is `Estimated`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| GD&T record and validation | `GeometricTolerance`; datum systems and targets; dialect validators and renderers | `InvalidControl { rule, clause }`; `DatumUnderdefined { dof }` | MEC-O-TL-1, MEC-O-TL-6 | 1, 2 (datum targets) |
| PMI target check | `pmi_target_resolved` on forwarded and explicit PMI | `ToleranceTargetSplit { control, pieces }`; `ResolveError` | MEC-O-TL-6 | 1 |
| General tolerances and edge callouts | `general_tolerance`; ISO 13715 callouts | `check::standards` finding | MEC-O-TL-3, MEC-O-TL-7 | 1 |
| Dialect conversion | Exact equivalents; typed holes elsewhere; `CrucibleDefined` zones | `ING6001` per untranslated control | MEC-O-TL-1 | 2 |
| Completeness | Degrees of freedom plus coverage rules | Free directions and uncovered aspects listed | MEC-O-TL-2, MEC-O-TL-7 | 2 |
| 1D stacks | Worst case, RSS at a stated coverage, 1D sampling | `ChainOpen` | MEC-O-TL-3 | 1 |
| Default distributions | Process data or uniform, over torsor sets for zones | `ProcessDataStale { profile }` (warning) | MEC-O-TL-8 | 1 |
| 3D and compliant variation | Zone and rebuild paths with yields and contributors | `AssemblyFailed { sample }` counted, never dropped | MEC-O-TL-4 | 2 |
| Tolerance allocation | Zone widths at a target yield | `Infeasible { yield }` | MEC-O-TL-4 | 3 |
| Skin model shapes | Form samples as Fields | `ContactUnresolved { sample }` | MEC-O-TL-5 | 4 |

## Drawings and model-based definition

### One annotation model

**Decision D-MEC-23:** Semantic PMI lives on the model. Drawings and 3D saved views are two presentations of the same annotation items; drawing-only annotations are allowed, marked non-semantic and excluded from semantic export. *Why:* one source of truth. ISO 16792:2021 supports a model-only data set or a model plus a digital drawing, and ASME Y14.41 covers annotated models with or without a sheet. *Rejected:* drawing-first annotation (not machine-readable); separate MBD annotations (two truths that drift).

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

Title-block fields, revision text, dates and approvers are late-bound release fields, excluded from the Item's definition digest (KLN). Phase 1 reads item numbers and revision labels from release tags and the EBOM view.

**Decision D-MEC-24:** Release drawings use certified hidden-line removal. Projected silhouettes and visibility transitions lie within a stated bound, by default 1 µm at model scale and below 0.01 mm at sheet scale. Lines, circles and conics project exactly, and editing uses a GPU preview that the certified result replaces. *Why:* silhouettes of NURBS and procedural faces have no exact NURBS form, so a drawing can promise a certified bound but not exactness. *Rejected:* "exact" hidden lines (an undeliverable claim); tessellated hidden lines for release (chordal error on the sheet). (revised in round 3)

**Decision D-MEC-36:** Editing a driving dimension on a drawing writes model source through ING's edit plans. A dimension that traces by provenance to exactly one literal writes it directly, as an `api` Edit shown as a source diff; otherwise the UI offers ranked edit plans. Driven and reference dimensions refuse the edit and say why. *Why:* principle 2 makes every surface an editor of one program, and drawing items already reference the model by `Query`. *Rejected:* read-only drawings (users expect driving dimensions to edit); a separate drawing geometry editor (two truths).

### Revisions, balloons and generated drawings

`revision_markers(drawing, from, to)` diffs annotations and views between releases, marks each changed item and fills the revision block. Drafting packages carry ASME Y14.35-2025, which "defines the practices for revising drawings and associated documents", and ISO practice.

Release drawings are PDF/A-2, conformance level u (ISO 19005-2:2011), which current viewers and validators read. PDF/A-4 (ISO 19005-4:2020) is an option, and the drafting package pins the choice.

Characteristic balloons draw MFG's characteristic identities and labels (D-MFG-18, D-MFG-26), beside item balloons tied to BOM lines. From phase 1, size, location, orientation, form and profile controls on GP1 and GP2 get them. Each release produces the ballooned PDF that external metrology reports against (MFG).

**Decision D-MEC-29:** Revision markers are computed from the release diff, never placed by hand, and characteristic balloons draw the labels MFG allocates, never numbering on their own. *Why:* computed markers cannot miss a change, and one allocator keeps balloon numbers stable across revisions. *Rejected:* hand-placed revision clouds (miss changes); balloons numbered by sheet position (change with layout).

`auto_drawing(part, template, rules)` deterministically writes an editable drawing program:

1. Select the fewest views that show every toleranced aspect, plus sections and details.
2. Place each PMI item where its target appears in true shape or as an edge.
3. Dimension untoleranced geometry from the datum system.
4. Lay out views and annotations with the `mech-drawing-layout` Wasm component.
5. Check that every PMI item appears exactly once.

### Model-based definition

Semantic PMI exports to AP242 per the CAx-IF Recommended Practices for PMI v4.1 (June 2024), linked to B-rep faces through `shape_aspect`. The practice reserves semantic PMI for exact geometry, so a control on facet faces exports as presentation only. `check::standards` flags it at design time, and ECO owns the AP242 reader and writer.

Targets: a drawing updates in under 1 s after its model rebuild; certified hidden lines of a 1,000-part assembly view take under 30 s.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Sheets, title blocks and standards | Formats; late-bound fields; ISO 128 and ASME Y14 packages recording their editions; PDF, SVG and PDF/A-2u, then DXF (2) and DWG through a licensed translator (3) | `UnfilledField { field }` at output | MEC-O-DR-4 | 1 |
| Views and hidden lines | Base, projected, auxiliary and section views, details; certified `anvil::project_hlr` | `ResolveError` on a cut or detail anchor | MEC-O-DR-1 | 1 |
| More views | Offset, aligned, removed and broken-out sections; broken and crop views; exploded, flat and ply views | As above | MEC-O-DR-1 | 2, 4 (ply views) |
| Dimensions and references | All dimension kinds by `Query`; silhouettes and section edges | Dangling item with `ResolveError` | MEC-O-DR-2 | 1 |
| Drawing edits | Driving dimensions write source (D-MEC-36) | Driven and reference dimensions refuse with the reason | MEC-O-DR-2 | 1 |
| Callouts, symbols and tables | Holes, threads, GD&T, welds; surface texture (ISO 21920-1:2021, ASME Y14.36-2018); edge callouts; BOM, hole and general-tolerance tables | Missing fields for the standard | MEC-O-DR-4 | 1, 2 (welds) |
| Gear data tables | Gear record fields and measurement over pins or span | Missing record fields | MEC-O-PF-15 | 2 |
| Revision markers | `revision_markers` from release diffs | `NoBaseRelease` | MEC-O-DR-6 | 2 |
| Characteristic balloons | MFG's labels on D-MFG-18 identities; ballooned PDF per release | `UnmappedCharacteristic { id }` | MEC-O-DR-7 | 1 (size, location, orientation, form, profile), 2 |
| Tabulated drawings and more tables | Family rows; bends, cut lists, plies | `RowFailed { key, error }` | MEC-O-DR-4 | 2 |
| Automatic drawings | Deterministic `auto_drawing` | `UnplacedItems { items }` | MEC-O-DR-5 | 3 |
| Saved views and AP242 PMI export | `model_view(…)`; CAx-IF PMI v4.1; eligibility per face | Facet targets exported as presentation, reported | MEC-O-DR-3, MEC-O-DR-8 | 1 |
| PMI import, QIF and data-set completeness | AP242 PMI into the model; QIF 3.0 through MFG; ASME Y14.41-2026 or ISO 16792:2021 | Unmappable or missing items listed | MEC-O-DR-3, MEC-O-DR-4 | 2 |

## Design checks

Design checks are `require` predicates packaged as libraries, each returning a `Field` of margins with typed fixes. MFG owns process DFM, DFA and DfAM checks; MEC owns design-domain and standards checks, with one result type. Each check has a `CheckId` (contract 5), so editing a limit keeps its verdicts, Evidence records and Waivers.

| Library | Example rules | Phase |
| --- | --- | --- |
| `check::standards` | Thread series; general tolerance present; GD&T validity, completeness and PMI eligibility; fallback regions; drawing completeness | 1 |
| `check::enclosure` | Clearance to imported boards, keep-ins, connector cut-outs | 1, 2 |
| `check::sheet`, `check::weld` | Sheet rules with MFG tooling minimums; weld access, symbols, quality levels, execution class | 2 |
| `check::fastening` | Engagement, clearance class, preload range, wrench swing, approved parts | 2 |
| `check::assembly` | Clearance over motion, interference classes, interface compatibility | 2 |
| `check::molding_design` | Draft, wall thickness, rib and boss ratios, undercuts | 3 |

**Decision D-MEC-25:** Design checks return graded Fields with numeric margins, not pass or fail flags. *Why:* agents optimize against margins, and people see where a rule nearly fails. *Rejected:* boolean rule results (no gradient for optimization, no early warning).

**Decision D-MEC-30:** Every mechanical check declares `decides_on`, the weakest bound kind that may decide it. Geometric checks (fits, clearance, interference, thickness, mass) need `Guaranteed` bounds. Physics checks accept, at `SignOff`, calibrated `Estimated` bounds from a named FLX class whose applicability envelope contains the result, confirmed by one further refinement (contract 7.1). Outside the envelope the bound is `Indicator`, and the check returns `Undecided`. *Why:* Flux reports every estimate multiplied by its class factor (D-FLX-24), so MEC states which checks rest on which classes. *Rejected:* `Guaranteed` bounds everywhere (no immersed stress check could pass in phase 1); any `Estimated` bound everywhere (a clearance would pass on an estimate). (revised in round 3)

| Check family | `decides_on` | Calibration class (FLX) | Phase |
| --- | --- | --- | --- |
| Fits, clearance, interference, thickness, mass | `Guaranteed` | — | 1 |
| Static stress on regularized peaks in solids (GP1) | `Estimated` | Elasticity regularized peak, aggregated CutFEM, p = 2 to 6 | 1 |
| Strut stress in beam lattices (GP2) | `Estimated` | Beam-lattice localized strut stress | 1 |
| Buckling load factors | `Estimated`, on the unsafe side | Linear buckling factor, eigenvalue DWR, beam lattice; an octree variant | 1 |
| Bolted joints | `Estimated` plus a policy allowance | Bolted-joint forms | 2 |

FLX owns these classes: 300 held-out samples each, at least 20% from `std::opt` runs that minimize the check margin, and references whose own error is below 10% of the bound. Each `Estimated` part carries its exceedance level α, which joins the union bound, so every `Pass` reports its confidence (contract 5). Peaks smooth over FLX's default radius from local curvature and thickness, so a 2 mm fillet is never averaged away.

GP1's and GP2's strain-gauged proof loads validate immersed elasticity and the beam-lattice model to E3 in their calibrated zones (contract 13.1, COV). Phase 1 releases therefore need no allowance for those quantities. Phase 2 bolted-joint checks cite an allowance from COV's catalogue that covers action-effect model uncertainty, and return `Undecided` until one is verified.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Check libraries | Graded margin Fields with fixes; a `CheckId` per check | `Error(Failure)` on a missing input | MEC-O-CK-1, MEC-O-CK-2 | 1 to 3 |
| `decides_on` declarations | Bound kind and calibration class per check; envelope and refinement confirmation | `Undecided { needed }`; `Undecided { reason: CalibrationUnconfirmed }` | MEC-O-CK-3 | 1 |

## Human factors

The validity envelope is geometric reach, fit and vision only; strength and musculoskeletal loading need Flux biomechanics models. Anthropometry follows ISO 7250-1:2017, and population datasets are licensed data packages.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Manikins | Kinematic chains with joint limits, scaled to a percentile or an individual | `DatasetMissing { population }` | MEC-O-HF-1 | 5 |
| Posture | Inverse kinematics on the shared solver with a comfort cost | `PostureInfeasible { target, limit }` | MEC-O-HF-1 | 5 |
| Reach, clearance and vision | Reach envelopes as Bodies; tool access; view cones | — | MEC-O-HF-1 | 5 |
| Posture scores | Methods such as RULA (McAtamney and Corlett, 1993) as check libraries | — | MEC-O-HF-1 | 5 |

## State of the art

Figures in the last column are targets unless quoted.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Feature language | Standard features in the user-facing language | Onshape FeatureScript | All `std::mech` features in Ingot (D-MEC-1) | Golden products built from std only |
| Code-CAD idioms | Text, hull, Minkowski sum and twisted extrusion as core operations | OpenSCAD | All in phase 1 except Minkowski sums | Every cheat-sheet idiom expressible |
| Sketch solving | Structural decomposition before numerical solving (Zou et al. 2022) | Siemens D-Cubed 2D DCM, "the most widely adopted 2D geometric constraint solver"; FreeCAD planegcs | Decomposed blocks, LM on `linalg`, Krawczyk bounds (D-MEC-3 to D-MEC-5) | SketchGraphs replay: 99.5% on the recorded branch |
| Constraint diagnosis | Exact witness configurations with Zou and Feng's corrections | D-Cubed diagnostics (not public) | Modular rank on rational witnesses, interval minors otherwise | Known-rank suite: 100% correct |
| Assembly solving | One system over SE(3) cluster unknowns on manifolds | Siemens D-Cubed 3D DCM; Onshape mate connectors | Shared solver (D-MEC-11); dynamics in Flux (D-MEC-12) | Mobility counts; closed-form linkages; 1,000 mates in under 100 ms |
| Blends | Rolling-ball and setback vertex blends; law radii | Parasolid, used by Plasticity; OCCT's fillet builder | ANV's staged program, opt-in implicit fallback (D-MEC-2) | Re-fillet benchmark: 95% at phase 1, 97% at phase 2, OCCT on the same corpus |
| Direct editing | History-free edits keeping related geometry consistent | Siemens synchronous technology | Solver-based face motions, rules in source (D-MEC-9) | 95% of held-out seeded edits succeed |
| Sheet metal | Flat pattern maintained by every feature; per-bend tables | Onshape sheet metal | Same model, no extrapolation (D-MEC-16) | Developed lengths equal closed forms to 10⁻⁹ relative |
| Surface quality | G2 and G3 analysis, zebra and highlight lines, live control-vertex feedback | Autodesk Alias; CATIA ICEM Shape Design; Plasticity xNURBS | Analysis Fields, checks and the 16 ms drag path (D-MEC-14) | Known-order surface pairs: zero misclassifications |
| SubD to NURBS | G2 regular regions, a choice at extraordinary vertices | Rhino 8 `ToNURBS`; OpenSubdiv | G1 default with reported deviation (D-MEC-15) | Limits within 10⁻⁹ relative of OpenSubdiv |
| Scan to CAD | Hybrid analytic and neural fitting (Point2CAD, CVPR 2024) | Point2CAD | Analytic-first with intent snapping and NURBS | Synthetic scans: at least Point2CAD's reported accuracy |
| Draping | Kinematic fishnet draping | Creo Composite Design | Deterministic kinematic drape (D-MEC-17) | Hemisphere and cylinder shear within 0.5° |
| Flattening | Boundary First Flattening | BFF reference implementation | `anvil::parameterize` with BFF | Distortion and time within 10% of the reference |
| Mate inference | Learned joint prediction (JoinABLe, 79.53%, literature only) | JoinABLe | Optional Wasm ranker | Generated joint benchmark: 80% top-1 |
| GD&T coverage | Degrees of invariance per surface class (ISO 17450-1:2011) | Sigmetrix GD&T Advisor | DOF analysis plus coverage rules (D-MEC-21) | Seeded gaps: 100% found, no false findings |
| 3D tolerance analysis | Nonlinear sampling with assembly behaviour; skin model shapes (Anwer et al. 2014; Schleich and Wartzack 2016) | Siemens Tecnomatix Variation Analysis (formerly VSA) | Zone and rebuild paths (D-MEC-22) | 20,000 zone-path samples of 50 parts in under 60 s |
| Semantic PMI | AP242 semantic PMI with validation properties (CAx-IF PMI v4.1) | CATIA, NX, Creo and SOLIDWORKS on NIST cases | Native AP242 PMI, per-face eligibility (D-MEC-23) | NIST CTC, FTC, STC and HTC: 100% of semantic items |
| Hidden-line removal | B-rep hidden lines on exact geometry, with a polygonal variant for speed | Open CASCADE `HLRBRep_Algo` and `HLRBRep_PolyAlgo` | Certified for release, GPU preview (D-MEC-24) | Silhouettes within the stated bound of high-precision references |
| Wall thickness | Ray and inscribed-sphere thickness | Autodesk Moldflow thickness diagnostics; Materialise Magics | Both `Certified` by branch-and-bound (D-MEC-18) | Error under 1% on analytic parts; identical bits with or without a GPU |
| Gear geometry | ISO 21771-1:2024 with flank modifications | KISSsoft (ISO 21771 geometry, ISO 6336 ratings) | Spline flanks within 0.1 µm plus semantics | Flank points against ISO 21771-1 formulas |
| Solver linear algebra | Rank-revealing QR and SVD per block | Eigen in planegcs; faer | Canonical `linalg`; faer only in `CpuIsa` | Bit identity across the canonical class; no slower than Eigen |

Deviations, stated: homotopy continuation finds all solutions, but editing needs one answer, so Crucible tracks the seeds' branch. OndselSolver is LGPL-2.1 and was archived on 1 March 2025, so it is a reference only.

## Platform notes

- **Numerics.** Residuals use `detmath` and solver algebra uses `linalg` without FMA (contract 7.3), so solves are bit-identical across the canonical class.
- **Browser.** Without cross-origin isolation the solver runs blocks sequentially, and the 16 ms browser drag target assumes one thread.
- **Fonts and tables.** Text uses registry font packages pinned in `ingot.lock` and shaped by Parley (D-PLT-7), never OS lookup. CSV import ignores the OS locale; a comma-decimal file needs `table(…, decimal: Comma)`.
- **GPU paths.** Thickness search order, zebra, hidden-line and control-vertex previews and interference culling have CPU paths; GPU results never prune or decide.
- **Offline and Tier 2.** Standards, catalog and font packages are vendored into air-gapped installs with their licences. Tablets edit dimensions, parameters and mates and drag sketches by touch through the same `api` stream.

## Interfaces with other subsystems

[[DIAGRAM diagrams/06-mechanical-data-flow.jsx: MEC data flow · design to Flux, MFG and drawings on one solver]]

Read the diagram left to right, from skeletons to the three consumers; the shared solver along the bottom serves every stage.

MEC uses ANV's operations with ANV's names and phases, and no MEC feature ships before the operations it calls.

| Subsystem | MEC consumes | MEC provides |
| --- | --- | --- |
| ANV | Operations with full role vocabularies; constraint solving; blend stages; copy relabeling; certified thickness; `mid_surface` (implicit path); `text_outline`; `draft` parting and step modes (phase 3); split policies | Constraint semantics; definitional attribute classes |
| ING | Builder blocks, `Expr<T>`, `#[interface]`, `#[configuration]`, Instance sets, `family`; `Tol<T>` symbols in name-free order, `.rss(coverage:)`, `vary`, `fit`; edit plans; typed holes | GD&T records and validators; std features with roles and keyed generators; `std::standards::iso286`; `default_distribution`; general tolerances |
| KLN and `repo` | Item numbers, revision labels, EBOM; change orders (phase 2); overrides kept out of the shared cache; approved parts; merge condition 5 | Part and Assembly `GeometryId` encodings; definitional attributes; the definition tolerance confirmation; interference classes for merge exemptions; `bom_item` lines, revision markers, cut lists |
| FLX | Multibody and rod solvers; beams and shells; bolted-joint forms; calibration classes with envelopes; eigenvalue budgets; smoothing radii; `std::uq::worst_case`; influence coefficients | Typed joints, redundancy reports, mass properties, preload, member profiles, laminates, default distributions, skin-model samples, the class each check needs |
| COV | Materials; E3 validation of GP1 and GP2 models from proof loads; the policy-allowance catalogue; gear, bearing and shaft ratings and loaded tooth contact (phase 2); constitutive draping (phase 5) | Gear records with accuracy grades and load spectra; plies and kinematic draping; part data for envelopes |
| MFG | Process profiles, tooling and press-brake data, hand-offs, cost models, DFM, DFA and DfAM checks; characteristic labels from phase 1 | `FlatPattern`, `HoleSpec`, `ThreadSpec`, `Weld` with execution class; edge callouts; general tolerances; `split_mold`; lattices; gear data tables; plies; harness geometry; balloons |
| ELX | Boards and connector `CoordSys` values; harness connectivity and wire lists (phase 4) | Enclosure geometry and checks; mates; gear records; routes, bundle and formboard geometry; fastener selection |
| ECO | Board readers (phase 2); AP242 and QIF translators; PDF, SVG, PDF/A and DXF writers; GDSII and OASIS writers (phase 5); the standards licence rule | `crucible:product`; the GD&T model and its AP242 mapping; weld, hole and composite semantics; flat DXF conventions |
| UIX, AGT and `api` | Painted Fields, freedom arrows, `Fix` buttons, the drawing sheet editor; `edit.stream`; Inspect and Edit methods | Solver and motion; std features with doc metadata; stacks; `SolveReport`, `ContinuityReport`, check Fields, `auto_drawing`, revision markers |
| PLT | `linalg`, `detmath`, the `Interactive` pool lane, Parley shaping | — |

| Wasm component | Purpose | Phase |
| --- | --- | --- |
| `mech-lattice` | Cell-family generator emitting strut graphs or tapes for `anvil::lattice` | 1 |
| `mech-route-search`, `mech-drawing-layout`, `mech-explode-planner`, `mech-mate-ranker` | Route search, drawing layout, disassembly planning, learned mate ranking | 3 |
| `mech-scan-segmenter` | Learned point-cloud segmentation | 4 |

Learned Wasm components ship fixed weights and run deterministic CPU inference.

## Oracles

All oracles live in the protected `oracles/mech/` directory. Held-out subsets (20% of each generated or replayed set, and every golden-product drawing) are never shown to agents. Third-party sets are fetched by hash and filtered by licence (D-MEC-37).

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| MEC-O-SK-1 | Sketch solving | SketchGraphs 2D replay and a synthetic 3D set re-solve from perturbed seeds on the recorded branch |
| MEC-O-SK-2 | Diagnosis | Known-rank systems, irrational witnesses included, get the right rank and certification; conflict sets are minimal |
| MEC-O-SK-3 | Inequalities | Known-feasibility systems are classified correctly |
| MEC-O-SK-4 | Determinism and seeds | Identical bits across the canonical class and re-randomized names; no silent branch change in 1,000 edits; an idle drag writes nothing; rounded seeds rebuild bit-identically |
| MEC-O-SK-5 | Drag | 200- and 2,000-entity sketches meet the drag targets; an overridden result never answers a request without the override |
| MEC-O-SK-6 | Curves | Spline, NURBS and helix values and lengths match high-precision references |
| MEC-O-SK-7 | Custom constraints | Values and derivatives match a reference interpreter and finite differences |
| MEC-O-SK-8 | Certified positions | Near-singular and under-determined sketches give boxes containing high-precision references, or `IllConditioned` |
| MEC-O-SK-9 | Helper names | Every helper sub-entity resolves, in sketches and as a role on extrusions, over 100 random edits |
| MEC-O-PF-1 | Profile features and roles | Volumes equal closed forms; every role of every std sweeping feature resolves over 100 random edits |
| MEC-O-PF-2 | Sweeps, lofts, helices | A circle swept along a helix is a tube; frames continuous; springs and threads match analytic surfaces |
| MEC-O-PF-3 | Offsets and shells | Certified minimum wall distance equals the thickness |
| MEC-O-PF-4 | Holes, threads, standards | Sizes match formulas and licensed tables; NIST hole cases rebuild; `Full` mesh threads lie within the chord tolerance |
| MEC-O-PF-5 | Blends and fallbacks | G1 contact holds; the re-fillet benchmark meets ANV's targets; `fallback_regions` decides seeded cases correctly |
| MEC-O-PF-6 | Draft | Draft Fields meet targets on drafted faces |
| MEC-O-PF-7 | Patterns and copies | Keys and transforms correct; removing a point renames no other copy; a read-only use of a source changes no `EntityId` |
| MEC-O-PF-8 | Booleans | Volume identities hold on pairs from the licence-filtered ABC subset |
| MEC-O-PF-9 | Direct edits | Declared relations kept, adjacent blends regrown |
| MEC-O-PF-10 | Deform and wrap | Deviation from analytic maps within the reported bound; developable wraps keep arc length |
| MEC-O-PF-11 | Derived parts | Pinned and bumped sources give the expected diff Proposals |
| MEC-O-PF-12 | Families and configurations | Rows type-check and report per row; `#[configuration]` gives the expected 150% BOM |
| MEC-O-PF-13 | Lattices | Relative density matches analytic values; kept faces keep attributes; sheet-cell mid-surfaces lie on the field's zero set |
| MEC-O-PF-14 | Rebuild budget | Golden-product rebuilds after first, middle and last edits meet contract 13.3 |
| MEC-O-PF-15 | Gears | Flank points match ISO 21771-1; undercut and tip limits hold; gear data tables carry every record field |
| MEC-O-PF-16 | Reference geometry | Constructors re-resolve under edits; shape-derived frames carry their note |
| MEC-O-PF-17 | Text, emboss, engrave | Regions match shaped outlines; depth and arc length exact on planes and cylinders |
| MEC-O-PF-18 | Hull and Minkowski sum | Results equal exact rational hulls and closed-form convex sums |
| MEC-O-AS-1 | Mates | Known Grübler–Kutzbach mobility, redundant and accidental cases included; rigid and flexible subassemblies agree |
| MEC-O-AS-2 | Kinematics | Slider-crank and four-bar motion equals closed forms |
| MEC-O-AS-3 | Interference | Analytic overlap volumes; NIST CTC 02 and 04 fits classified; a press fit at nominal is `IntendedFit` |
| MEC-O-AS-4 | Large assemblies | A synthetic 100,000-Instance assembly meets the open and orbit targets |
| MEC-O-AS-5 | Exploded views | Automatic explosion of the golden gearbox is collision-free |
| MEC-O-AS-6 | Fasteners | Lengths equal hand-computed cases; adding a hole changes the set's quantity, not the BOM structure |
| MEC-O-AS-7 | Mate inference | Top-1 accuracy on the generated joint benchmark meets the target |
| MEC-O-AS-8 | Interfaces | Every seeded provider–consumer mismatch is reported |
| MEC-O-AS-9 | BOM-only items and approved parts | Lines carry the Item's unit; a non-approved part fails unless a Waiver names it |
| MEC-O-AS-10 | Dynamic clearance | Intervals contain the dense-sampling minimum, a cam with a short dwell between samples included |
| MEC-O-AS-11 | Enclosure checks | KiCad's STEP and IDF exports of an open board give the expected findings |
| MEC-O-AS-12 | Assembly-level features | Derived Parts and after-assembly operations give the same geometry |
| MEC-O-AS-13 | Identity and definitional attributes | Re-randomized Instance names keep Assembly `GeometryId`s, and moving an Instance changes them; a definitional change marks a released Item modified, a non-definitional one does not |
| MEC-O-WIT-1 | `crucible:product` | The published WIT matches the tabled interfaces; golden products round-trip through `build` and `read` with equal `GeometryId`s |
| MEC-O-SF-1 | Continuity | Surface pairs of known order are classified correctly |
| MEC-O-SF-2 | Surfaces | Boundary, network and fill surfaces interpolate boundaries and meet edge targets |
| MEC-O-SF-3 | SubD | Limits match stored OpenSubdiv outputs; `to_nurbs` deviation as reported |
| MEC-O-SF-4 | Scan to CAD | Synthetic scans recover primitive types, parameters and Chamfer distance |
| MEC-O-SF-5 | Control-vertex drags | Frames within 16 ms; the committed edit equals the full rebuild |
| MEC-O-SM-1 | Bend rules | Developed lengths equal the formulas; the default K follows the R/t data and prints per bend |
| MEC-O-SM-2 | Flat patterns | Every flat pattern refolds to the folded body within the entity tolerance |
| MEC-O-SM-3 | Sheet checks | Every seeded defect in GP4's guards is found |
| MEC-O-SM-4 | Flat DXF and clinch hardware | DXF re-imports with layers per convention; seeded clinch violations are found |
| MEC-O-WD-1 | Member sections | Area and second moments equal catalog values within 0.5% |
| MEC-O-WD-2 | Trims and cut lists | Mitered lengths and end angles equal closed forms |
| MEC-O-WD-3 | Weld records | Rendered symbols parse back into identical records; each execution class reaches MFG's derived quality levels |
| MEC-O-CP-1 | Draping | Hemisphere and cylinder drapes match analytic shear |
| MEC-O-CP-2 | Laminates | ABD matrices equal hand calculations; symmetry and balance checks correct |
| MEC-O-MD-1 | Thickness | Fields match analytic answers; bits are identical with the GPU off and with adversarial GPU candidates |
| MEC-O-MD-2 | Mould split | Core, cavity and part sum to the block; no negative draft |
| MEC-O-RT-1 | Routes | Lengths and bend radii on known paths equal closed forms |
| MEC-O-RT-2 | Fittings | Fitting selection matches spec tables |
| MEC-O-RT-3 | Formboards | Flattened branch lengths equal 3D lengths without overlaps |
| MEC-O-LS-1 | Hydrostatics | Analytic hull forms match closed-form hydrostatics |
| MEC-O-LS-2 | IFC structures | IFC 4.3 members, plates and openings round-trip |
| MEC-O-LS-3 | Soft goods | Flattened seams match 3D lengths within the declared stretch |
| MEC-O-LS-4 | MEMS stacks | Stacks with known etch geometry give the analytic Bodies |
| MEC-O-TL-1 | Dialects | Y14.5-2018 and ISO 1101 rule suites are judged correctly; conversion leaves one typed hole per non-equivalent control |
| MEC-O-TL-2 | Degrees of freedom | Known free directions are reported exactly, a threaded bore included |
| MEC-O-TL-3 | 1D stacks | Worst case and RSS at a stated coverage equal exact convolutions; untoleranced contributors take the general tolerance |
| MEC-O-TL-4 | 3D variation | Identical across runs, classes and renamings; intervals cover references; the zone path meets its target |
| MEC-O-TL-5 | Skin models | Sampling statistics match the specified random fields |
| MEC-O-TL-6 | GD&T record and PMI targets | NIST FTC controls, ISO 5458 examples and datum targets round-trip; a rib splitting a face with forwarded `4mm ± 0.1mm` fails `pmi_target_resolved` |
| MEC-O-TL-7 | Coverage rules | Seeded missing size, form, datum-form and general tolerances are all found |
| MEC-O-TL-8 | Default distributions | Reports print assumptions; process data set shift and spread; zone samples are uniform over the torsor set |
| MEC-O-DR-1 | Hidden lines | Certified hidden lines agree with high-resolution ray casting within the stated bound |
| MEC-O-DR-2 | Associativity and edits | Every item re-resolves or reports a `ResolveError`; editing a driving dimension writes exactly its literal |
| MEC-O-DR-3 | PMI exchange | NIST CTC, FTC and later test cases export to AP242 and match NIST's files item by item |
| MEC-O-DR-4 | Drafting rules | Line types, text, symbols and tables pass on held-out golden drawings |
| MEC-O-DR-5 | Automatic drawings | Every PMI item appears exactly once; reruns are bit-identical |
| MEC-O-DR-6 | Revision markers | Two changed dimensions give two markers and one revision row |
| MEC-O-DR-7 | Balloons | One changed dimension changes one balloon and no labels; GP1 and GP2 balloon every size, location, orientation, form and profile control |
| MEC-O-DR-8 | PMI eligibility | Controls on facet faces export as presentation and are reported |
| MEC-O-CK-1 | Check coverage | Every defect seeded into golden products 3 to 5 is found, none on clean versions |
| MEC-O-CK-2 | Fixes | Every fix compiles and clears its finding |
| MEC-O-CK-3 | Bound kinds | Bounds below `decides_on`, outside the class envelope or unconfirmed by refinement give `Undecided` |
| MEC-O-HF-1 | Human factors | Segment lengths match the dataset; reach envelopes match analytic chains |

## Phasing

Gate contributions follow contract 13; per-capability phases are in the capability tables, and shared physics phases follow contract 13.4.

| Phase | MEC's contribution to the gate |
| --- | --- |
| 0 | Certified solver core and modular-rank diagnosis on `linalg`; role conventions; data-package format; MEC corpus in the determinism suite |
| 1 | GP1: sketches, profile features with full role vocabularies, holes and threads, stage 1 blends, shells, draft, patterns, push-pull, basic mates, GD&T with PMI target checks, general tolerances, 1D stacks, drawings with characteristic balloons, AP242 PMI, identities, `crucible:product`. GP2: strut lattices, text, emboss, hull, printed threads on the mesh path, strut and buckling checks on their classes |
| 2 | GP3: gear records and data tables for COV's ratings, shafts, fastener Instance sets, kinematics, completeness, 3D variation. GP4: weldments with execution classes, sheet metal, compliant variation, revision markers. Also freeform surfaces, direct edits, stage 2 blends, exact threads, sheet-cell lattices, datum targets, dialect conversion |
| 3 | GP5: molded part design, control-vertex editing with G3 surfaces, SubD, routing, automatic drawings, mate inference, tolerance allocation |
| 4 | GP6: composite laminates, harness bundles from ELX wire lists, formboards, scan to CAD, skin model shapes, cast parts; the 100,000-Instance open target |
| 5 | GP7 MEMS layer stacks; GP8 steel structures through IFC 4.3, with execution classes enforced by MFG; pipe and duct routing; human factors |
| 7 | GP13 hull fairing and hydrostatics; GP14 timber members through IFC; GP16 soft-goods patterns |

## Open questions

Round 3 closed the earlier questions in D-MEC-20, D-MEC-30, D-MEC-31, D-MEC-33, D-MEC-34, D-MEC-36 and D-MEC-37.

1. **Standards data licences.** Which distributor terms let Crucible package tabulated values such as ISO 261 plans and ISO 273 clearance holes? Kept open for counsel's review before phase 1 (D-MEC-31); until then an organization supplies its own table packages.
2. **Findings declined or applied in part.**
    - R9-53: its 2¹⁰ρ floor is declined for R10-39's 10ρ, because 2¹⁰ρ would ignore changes of up to 0.49 mm on a 300 m hull.
    - R8-24: the seed quantum is scale-relative with no 1 µm floor, so MEMS sketches keep sub-micrometre seeds.
    - R8-44: machining implicit regions through mesh-capable CAM is declined; STEP hand-offs need B-rep (R10-37).
    - R10-36: dialect conversion ships in phase 2 as exact translation plus typed holes, which are the non-equivalence report; nothing is translated approximately.
    - R10-41: the DIN 6935 correction factor could not be verified, so the R/t-dependent default K comes from MFG's press-brake data.
    - Round 2 records: R1-10, R1-36, R2-09, R2-36, R6-11, R3-30, R3-31 and R4-29 stay applied in MEC's part only. R2-19, R4-14, R4-16 and R1-37 are now fully applied.

## Contract change requests

- **CCR-MEC-1.** Contract 5's list of definitional attributes adds general tolerances (D-MEC-35) and edge callouts to ISO 13715. Both change what is made, so changing either must mark the Item modified, and the contract's list is explicit.

## Sources

- SolveSpace, technical description: https://solvespace.com/tech.pl
- Siemens, D-Cubed 2D DCM: https://www.siemens.com/en-gb/products/plm-components/d-cubed/2d-dcm/
- Siemens, D-Cubed 3D DCM: https://www.siemens.com/en-gb/products/plm-components/d-cubed/3d-dcm/
- Siemens, D-Cubed 2D components version 79 release (3 December 2025): https://blogs.sw.siemens.com/plm-components/d-cubed-2d-components-version-79-release/
- FreeCAD planegcs solver source: https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/Sketcher/App/planegcs/GCS.cpp
- Zou et al., A review on geometric constraint solving: https://arxiv.org/abs/2202.13795 and https://arxiv.org/pdf/2202.13795v2
- Zou and Feng, On limitations of the witness configuration method: https://arxiv.org/pdf/1904.00526
- Seff et al., SketchGraphs: https://arxiv.org/abs/2007.08506 and https://github.com/PrincetonLIPS/SketchGraphs
- Koch et al., ABC dataset: https://openaccess.thecvf.com/content_CVPR_2019/html/Koch_ABC_A_Big_CAD_Model_Dataset_for_Geometric_Deep_Learning_CVPR_2019_paper.html and https://cims.nyu.edu/gcl/papers/2019-ABC-Dataset.pdf
- Autodesk, Fusion 360 Gallery dataset: https://github.com/AutodeskAILab/Fusion360GalleryDataset
- Willis et al., JoinABLe: https://arxiv.org/abs/2111.12772
- Onshape, FeatureScript introduction: https://cad.onshape.com/FsDoc/intro.html
- Onshape, mates: https://cad.onshape.com/help/Content/Assembly/mates.htm
- Onshape, sheet metal model: https://cad.onshape.com/help/Content/PartStudio/sheet_metal_model.htm
- Siemens, synchronous technology: https://www.siemens.com/en-us/technology/synchronous-technology/
- Plasticity, product tour: https://plasticity.xyz/product
- McNeel, Rhino 8 ToNURBS: https://docs.mcneel.com/rhino/8/help/en-us/commands/tonurbs.htm
- Pixar, OpenSubdiv: https://github.com/PixarAnimationStudios/OpenSubdiv
- Liu et al., Point2CAD: https://openaccess.thecvf.com/content/CVPR2024/html/Liu_Point2CAD_Reverse_Engineering_CAD_Models_from_3D_Point_Clouds_CVPR_2024_paper.html
- Sawhney and Crane, Boundary First Flattening: https://arxiv.org/abs/1704.06873
- Ceres Solver, modeling (manifolds and loss functions): http://ceres-solver.org/nnls_modeling.html
- faer documentation: https://docs.rs/faer/latest/faer/
- Ondsel, OndselSolver: https://github.com/Ondsel-Development/OndselSolver
- ASME Y14.5: https://www.asme.org/codes-standards/find-codes-standards/y14-5-dimensioning-tolerancing
- GD&T Seminars, the new ASME Y14.5-2018 standard: https://gdtseminars.com/2019/05/24/the-new-asme-y14-5-2018-standard/
- ASME Y14.41: https://www.asme.org/codes-standards/find-codes-standards/y14-41-digital-product-definition-data-practices
- ISO 1101:2017: https://www.iso.org/standard/66777.html
- ISO 16792:2021: https://www.iso.org/standard/73871.html
- ISO 5459:2024 (EVS listing): https://www.evs.ee/en/evs-en-iso-5459-2024
- ISO 14405-1:2025 (EVS listing): https://www.evs.ee/en/evs-en-iso-14405-1-2025
- ISO 8015:2011 (EVS listing): https://www.evs.ee/en/iso-8015-2011
- ISO 22081:2021 (SIS listing): https://www.sis.se/en/produkter/metrology-and-measurement-physical-phenomena/linear-and-angular-measurements/geometrical-product-specification-gps/ss-en-iso-220812021/
- ISO 2553:2019 (EVS listing): https://www.evs.ee/en/iso-2553-2019
- AWS A2.4:2020 (GlobalSpec listing): https://standards.globalspec.com/std/14204706/a2-4-2020
- ISO 21771-1:2024 (EVS listing): https://www.evs.ee/en/iso-21771-1-2024
- ISO 7250-1:2017: https://www.iso.org/standard/65246.html
- CAx-IF, Recommended Practices for PMI v4.1: https://www.mbx-if.org/home/wp-content/uploads/2024/06/rec_pracs_pmi_v41.pdf
- NIST, MBE PMI validation and conformance testing: https://www.nist.gov/ctl/smart-connected-systems-division/smart-connected-manufacturing-systems-group/mbe-pmi-0
- buildingSMART, Industry Foundation Classes: https://www.buildingsmart.org/standards/bsi-standards/industry-foundation-classes/
- AISC, Shapes Database v16.0: https://www.aisc.org/publications/steel-construction-manual-resources/16th-ed-steel-construction-manual/aisc-shapes-database-v16.0/
- PTC, Creo draping simulation: https://support.ptc.com/help/creo/creo_plus/usascii/composite_design/about_draping_simulation.html
- Anwer et al., From solid modelling to skin model shapes (2014): https://cris.fau.de/publications/111031184
- Schleich and Wartzack, A quantitative comparison of tolerance analysis approaches (2016): https://cris.fau.de/publications/122836164
- ISO 5458:2018, pattern and combined geometrical specification (EVS listing): https://www.evs.ee/en/iso-5458-2018
- ISO 2692:2021, maximum material, least material and reciprocity requirements (EVS listing): https://www.evs.ee/en/iso-2692-2021
- ISO 17450-1:2011, model for geometrical specification and verification (EVS listing): https://www.evs.ee/en/iso-17450-1-2011
- Homri, Teissandier and Ballu, Tolerance analysis by polytopes (classes of surface and degrees of invariance, Table 1): https://arxiv.org/pdf/1509.08763
- Keyence, international industrial standards and GD&T (independency and envelope principles): https://keyence.com/ss/products/measure-sys/gd-and-t/basic/international.jsp
- Sigmetrix, GD&T Advisor: https://www.sigmetrix.com/software/gdt-advisor
- ASME Y14.35, revision of engineering product definition datasets and associated documents: https://www.asme.org/codes-standards/find-codes-standards/y14-35-revision-engineering-drawings-associated-documents
- IAQG, 9102 summary of changes, revision B to C (11 July 2023): https://ma.iaqg.org/wp-content/uploads/2019/10/9102_Changes_07112023.pdf
- ISO 5817:2023, quality levels for imperfections in fusion-welded joints (EVS listing): https://www.evs.ee/en/iso-5817-2023
- OpenSCAD cheat sheet: https://openscad.org/cheatsheet/
- KiCad 9 PCB editor manual (STEP and IDF export): https://docs.kicad.org/9.0/en/pcbnew/pcbnew.html
- Open CASCADE, `BRepFilletAPI_MakeFillet` reference: https://occt3d.com/dev/doc/refman/html/class_b_rep_fillet_a_p_i___make_fillet.html
- faer 0.24.4, sparse QR module (simplicial and supernodal factorizations, no pivoting or rank mode listed): https://docs.rs/faer/latest/faer/sparse/linalg/qr/index.html
- ISO, notice on machine-readable files for ISO 10303: https://standards.iso.org/iso/10303/
- Directive 96/9/EC on the legal protection of databases, Article 7: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:31996L0009
- Onshape, terms of use, section 1(g)(ii): https://www.onshape.com/en/legal/terms-of-use
- Autodesk, Fusion 360 Gallery dataset licence: https://raw.githubusercontent.com/AutodeskAILab/Fusion360GalleryDataset/master/LICENSE.md
- ABC dataset site (copyright stays with the models' creators): https://deep-geometry.github.io/abc-dataset/
- Onshape, Extrude (New, Add, Remove, Intersect): https://cad.onshape.com/help/Content/extrude.htm
- SOLIDWORKS 2024 help, configurations overview: https://help.solidworks.com/2024/english/SolidWorks/sldworks/c_Configurations_Overview.htm
- SOLIDWORKS 2024 help, external references: https://help.solidworks.com/2024/english/SolidWorks/sldworks/c_external_references.htm
- Wilson and Latombe, Geometric reasoning about mechanical assembly, Artificial Intelligence 71 (1994): https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/0004-3702(94)90048-5?fields=title,authors,venue,year,abstract
- Scholz, Tolerance stack analysis methods (Boeing, 1995; Bender's 1.5 factor): https://faculty.washington.edu/fscholz/Reports/isstech-95-030.pdf
- GD&T Basics, Rule #1 (Y14.5-2018 section 5.8.1): https://www.gdandtbasics.com/?p=8382
- ASME Y14.5.1-2019, mathematical definition of dimensioning and tolerancing principles: https://www.asme.org/codes-standards/find-codes-standards/y14-5-1-mathematical-definition-dimensioning-tolerancing-principles
- McAtamney and Corlett, RULA, Applied Ergonomics 24(2), 1993 (PubMed record): https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=15676903
- Autodesk Alias tutorial on Class-A surfaces: https://help.autodesk.com/cloudhelp/2016/ENU/Alias-Tutorials-Legacy/files/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.htm
- Dassault Systèmes, CATIA ICEM Shape Design brochure: https://www.3ds.com/fileadmin/PRODUCTS-SERVICES/CATIA/PDF/CATIA-ICEM-Shape-Design-Brochure.pdf
- Siemens, Tecnomatix Variation Analysis (formerly VSA) fact sheet: https://www.plm.automation.siemens.com/en_us/Images/Siemens-PLM-Tecnomatix-Variation-Analysis-fs_tcm1023-120264.pdf
- Open CASCADE, modeling algorithms user guide (hidden line removal): https://occt3d.com/dev/doc/overview/html/occt_user_guides__modeling_algos.html
- Autodesk Moldflow Insight, thickness diagnostic: https://help.autodesk.com/cloudhelp/2026/ENU/MoldflowInsight-CLC-Troubleshoot/files/Error-and-warning-messages/MFLO_SOLVER_MESSAGE_702300.html
- Materialise, Magics 2025 release (wall thickness analysis): https://www.materialise.com/en/news/press-releases/magics-release-rapid-tct-2025
- KISSsoft product description 2024 (ISO 21771 geometry, ISO 6336 strength): https://www.kisssoft.com/files/aznw8h/KISSsoft-Productdescription-en-v2402.pdf
- RJC Mold, rib design guide (40% to 60% of the nominal wall): https://rjcmold.com/guides/rib-design-guide/
- FirstMold, rib design tips: https://firstmold.com/tips/rib-design/
- CAx-IF, Recommended Practices for Composite Materials v4.4: https://www.mbx-if.org/home/wp-content/uploads/2026/01/Rec_Pracs_Composites_V4.4.pdf
- CAx-IF recommended practices index: https://www.mbx-if.org/home/cax/recpractices/
- ISO 68-1:2023 (EVS listing): https://www.evs.ee/en/iso-68-1-2023
- ISO 261:1998 (EVS listing): https://www.evs.ee/en/iso-261-1998
- ISO 965-1:2026 (EVS listing): https://www.evs.ee/en/iso-965-1-2026
- ISO 286-1:2010 (EVS listing): https://www.evs.ee/en/iso-286-1-2010
- ISO 286-2:2010 (EVS listing): https://www.evs.ee/en/iso-286-2-2010
- ISO 273:1979, confirmed in 2024 (ISO committee page): https://committee.iso.org/standard/4183.html
- ISO 273:1979 (EVS listing): https://www.evs.ee/en/iso-273-1979
- ISO 228-1:2000 (EVS listing): https://www.evs.ee/en/iso-228-1-2000
- ISO 7-1:1994 (EVS listing): https://www.evs.ee/en/iso-7-1-1994
- ISO 2904:2020 (EVS listing): https://www.evs.ee/en/iso-2904-2020
- ASME B1.1-2024, unified inch screw threads: https://www.asme.org/products/codes-standards/unified-inch-screw-threads--un-and-unr-thread-form
- ASME B1.20.1-2013, pipe threads: https://www.asme.org/codes-standards/find-codes-standards/b1201-pipe-threads-general-purpose-inch
- ASME B1.5-1997, Acme screw threads: https://www.asme.org/codes-standards/find-codes-standards/b1-5-acme-screw-threads
- ASME Y14.36-2018, surface texture symbols: https://www.asme.org/codes-standards/find-codes-standards/y14-36-surface-texture-symbols
- ISO 21920-1:2021 (EVS listing): https://www.evs.ee/en/iso-21920-1-2021
- ISO 19005-2:2011, PDF/A-2 (EVS listing): https://www.evs.ee/en/iso-19005-2-2011
- ISO 19005-4:2020, PDF/A-4 (EVS listing): https://www.evs.ee/en/iso-19005-4-2020
- ISO 1328-1:2013 (EVS listing): https://www.evs.ee/en/iso-1328-1-2013
- ISO 23509-1:2025 (EVS listing): https://www.evs.ee/en/iso-23509-1-2025
- ISO 10828:2024 (EVS listing): https://www.evs.ee/en/iso-10828-2024
- DIN 509:2022-12, relief grooves (DIN Media): https://www.dinmedia.de/en/standard/din-509/359215693
- DIN 6885-1:2021-11, parallel keys and keyways (DIN Media): https://dinmedia.de/en/standard/din-6885-1/346315269
- DIN 471:2026-05, retaining rings for shafts (DIN Media): https://www.dinmedia.de/en/standard/din-471/399916408
- EN 10365:2026 (EVS listing): https://www.evs.ee/en/evs-en-10365-2026
- EN 10210-2:2019 (EVS listing): https://www.evs.ee/en/evs-en-10210-2-2019
- EN 10219-2:2019 (EVS listing): https://www.evs.ee/en/evs-en-10219-2-2019
- EN 1090-2:2018+A1:2024 (EVS listing): https://www.evs.ee/en/evs-en-1090-2-2018-a1-2024-consolidated
- ISO 2768-1:1989 (EVS listing): https://www.evs.ee/en/iso-2768-1-1989
- ISO 2768-2:1989, withdrawn (EVS listing): https://www.evs.ee/en/iso-2768-2-1989
- ISO 22081:2021 (EVS listing): https://www.evs.ee/en/iso-22081-2021
- ISO 13715:2017 (EVS listing): https://www.evs.ee/en/iso-13715-2017
