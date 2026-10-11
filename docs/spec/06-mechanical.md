# Mechanical design (MEC)

`std::mech` is the Ingot library for everything a mechanical, industrial or structural designer does before manufacturing: sketches, part features, assemblies, surfaces, sheet metal, weldments, composites, molded parts, routing, tolerancing, drawings and design checks. Every feature is Ingot orchestrating versioned Anvil operations and a few Wasm components. One constraint solver, one query vocabulary and one semantic tolerancing model serve all of them.

## Library structure and shared conventions

### Packages

`std::mech` re-exports the everyday features, so `use std::mech::{sketch, extrude, rib, fillet}` works as in the overview. Specialist packages sit beneath it. Standards content (thread tables, profile catalogs, bend tables) lives in separate data packages, so a standard's edition is pinned in the lockfile like any other dependency.

| Package | Contents | First phase |
| --- | --- | --- |
| `std::mech::sketch` | 2D and 3D sketches, entities, constraints, solve reports | 1 |
| `std::mech::part` | Part features, holes, threads, patterns, direct edits, configurations | 1 |
| `std::mech::machine` | Machine elements: gears, shafts, keys, splines, springs; seals and bearings as catalog parts | 2 |
| `std::mech::asm` | Instances, mates, kinematics, interference, exploded views, fasteners | 1 (basic), 2 |
| `std::mech::surf` | Curves, freeform surfaces, continuity, SubD, Class-A analysis, scan-to-CAD | 3 |
| `std::mech::sheet` | Sheet metal features, bend tables, flat patterns | 2 |
| `std::mech::weld` | Structural members, trims, gussets, weld beads, cut lists | 2 |
| `std::mech::composite` | Plies, zones, rosettes, drape, ply books | 4 |
| `std::mech::mold` | Draft, parting, core and cavity, ribs, bosses, thickness | 3 |
| `std::mech::route` | Pipes, tubes, hoses, ducts, harness bundles | 3 (harness), 5 |
| `std::mech::tol` | GD&T, datum systems, stack-ups, 3D variation | 1 (basic), 2 |
| `std::mech::drawing` | Drawings, views, annotations, tables, model-based definition | 1 (basic), 2 |
| `std::mech::check` | Design-rule and standards-compliance checks | 1 onward |
| `std::mech::human` | Digital human models, reach, vision, posture checks | 5 |
| `std::standards::*` | Data packages: ISO, DIN, ANSI and ASME, EN, AISC tables | 1 onward |

### Shared types

MEC adds no geometry type. Every geometric output is a `Body`, `Part` or `Assembly`; every analysis result is a `Field`. The types below are plain Ingot records that reference core types.

| Type | What it is | Relation to core types |
| --- | --- | --- |
| `Sketch` | Planar or 3D wire and region geometry plus its constraint system and solve report | A `Body` (wires and planar faces) with constraint metadata |
| `Profile` | One or more closed regions of a sketch | A `Query` that resolves to planar faces of a `Sketch` |
| `Path` | A G0-connected chain of edges | A `Query` that resolves to edges of any `Body` |
| `CoordSys` | A right-handed coordinate system anchored to geometry | A `Transform` plus an anchor `Query`; re-resolved on rebuild (see contract change requests) |
| `Mate` | A typed constraint between two `CoordSys` values on two Instances | Stored in the `Assembly` |
| `HoleSpec`, `ThreadSpec`, `Weld`, `Ply` | Semantic records describing manufacturing intent | Metadata keyed by `EntityId` on a `Body` |
| `ShapeAspect` | An identified portion of a Body's boundary with a kind: a toleranced face set or feature of size in the GD&T sense, or a recognized hole, boss, pocket, fillet, chamfer or pattern | A `Query` over faces; named after AP242's `shape_aspect` (see contract change requests) |
| `GeometricTolerance`, `Datum`, `DatumSystem` | GD&T controls | Typed properties on entities, built from `Tol<T>` |
| `Drawing`, `Sheet`, `View` | 2D documentation | Plain values whose linework is 2D `Body` geometry |
| `Route` | A path with a specification and end ports | A `Path` plus a `RouteSpec` plus two `CoordSys` ports |

### Roles and queries

Every feature declares a role for each entity it creates: `extrude` creates `start_cap`, `end_cap` and `side(e)` for each profile edge `e`, and a hole creates `wall`, `floor`, `counterbore_wall` and `countersink`. Roles enter the `EntityId` hash as the contract's "role" input, so they survive parameter edits.

```
let lid  = sketch(plane.xy) { rect(80mm, 50mm) } |> extrude(6mm)
let rim  = lid.edges(created_by: lid, role: side(any)).adjacent(lid.face(role: end_cap))
let soft = lid |> fillet(rim, 1.5mm)
```

**Decision D-MEC-1:** Every `std::mech` feature declares typed roles for the entities it creates, and std queries select by provenance and role first, with geometric predicates (`longest`, `parallel_to`) only as filters. *Why:* provenance and roles are stable under parameter edits, while geometric predicates flip when dimensions change. *Rejected:* name matching heuristics (they rebind silently), persistent face ids stored in source (they break under semantic merge).

### Errors and approximations

Every failure is a `FeatureError { kind, why, fix: [Fix], at: [EntityId] }`. A `Fix` is a typed edit that the UI shows as a button and an agent can apply: change a parameter, delete a constraint, enable a fallback. Each section below lists its error kinds.

**Decision D-MEC-2:** Approximation is always opt-in through an explicit parameter, for example `fallback: Fallback::Implicit(max_deviation: 0.01mm)`. A feature that cannot produce an exact result fails and offers that fallback as a `Fix`. *Why:* the contract forbids silent fallbacks, and designers must see every deviation. *Rejected:* automatic fallback with a warning (warnings get ignored; released geometry would carry unseen error).

Several features have three representation levels, chosen by `repr: Repr`: `Cosmetic` stores intent only (a thread texture, a weld symbol), `Simplified` builds light geometry with a recorded `ErrorBound`, and `Exact` builds full geometry. Defaults are listed per feature.

## Sketching

A sketch is a set of entities, constraints and dimensions on a plane (2D) or in space (3D). The solver turns seed geometry plus constraints into solved geometry and a solve report.

### Entities

| Entity | Unknowns (2D) | Notes | Phase |
| --- | --- | --- | --- |
| `point` | x, y | 3D sketches add z | 1 |
| `line` | 2 end points | Infinite construction lines via `construction_line` | 1 |
| `arc`, `circle` | Center, radius, start and end angles | Three-point and tangent helpers | 1 |
| `ellipse`, `elliptical_arc` | Center, major axis vector, axis ratio, angles | | 2 |
| `conic` | Two ends, apex, rho | Rho in (0, 1) | 2 |
| `spline` (interpolating) | Through points, optional tangent and curvature handles | Curve-length and curvature-range dimensions | 1 |
| `nurbs` (control point) | Control points, weights; degree 2 to 7; fixed knots | Knot edits are explicit features, not solver unknowns | 2 |
| `offset` | Driven from a source chain | Re-offsets after every solve | 1 |
| `use_edges` | Driven by a `Query` on model edges, projected to the sketch | Fails with `ResolveError`, never rebinds | 1 |
| `intersection_curve` | Driven (3D sketch) | From `anvil::intersect` | 2 |
| `helix`, `spiral` | Axis coordinate system, pitch, turns, taper | 3D sketches and sweeps | 2 |
| `text` | Driven glyph outlines | Bundled fonts only (see platform notes) | 2 |
| `rect`, `slot`, `polygon` | Helpers that emit entities plus constraints | | 1 |

Any entity can be flagged `construction`. Construction geometry constrains but never forms profiles.

### Constraints and dimensions

| Constraint | Equations | Notes | Phase |
| --- | --- | --- | --- |
| `coincident`, `point_on` (curve or surface) | 2 or 1 | Point-on-NURBS adds the curve parameter as an unknown | 1 |
| `horizontal`, `vertical`, `parallel`, `perpendicular`, `collinear` | 1 each | Relative to the sketch plane's axes | 1 |
| `tangent` (G1), `curvature` (G2), `g3` | 1 to 3 at a contact | Contact parameters are unknowns; side qualifier stored | 1 (G1), 2 (G2, G3) |
| `concentric`, `midpoint`, `symmetric` | 2 each | Symmetric about a line or, in 3D, a plane | 1 |
| `equal` | 1 per pair | Mixed kinds (length, radius, curve length, pattern pitch) share one value, after 2D DCM v79 | 1 |
| `fix` | 2 or 3 | Fixes position only, or position and orientation | 1 |
| `dim` (distance, angle, radius, diameter, length, curve length) | 1 | Driving; signed variants carry half-space qualifiers | 1 |
| `dim_range` | Inequality | Min and max limits, solved by an active set | 2 |
| `pattern` (linear, circular) | Per instance | Keeps instances related while editing | 2 |
| `mirror` | Per entity | About a construction line | 1 |
| `on_plane`, `on_surface`, `along` | 1 or 2 | 3D sketches | 2 |
| `equation` | 1 | Custom Ingot residual (below) | 2 |

`dim(target, value)` is a driving dimension. `measure(target)` is a driven dimension and returns a `Quantity` that downstream features may read but never write. When a driving value is a `Tol<T>`, geometry uses the nominal and the tolerance becomes model PMI if the dimension is marked `pmi`.

```
use std::mech::{sketch, extrude}

pub feature plate(width: Length = 80mm, bore: Tol<Length> = 8.4mm ± 0.05mm) -> Part {
    let s = sketch(plane.xy) {
        let r = rect(point(0mm, 0mm), point(80mm, 50mm))   // seed corners
        let c = circle(point(15mm, 15mm), 4.2mm)            // seed circle
        fix(r.corner(0))
        dim(r.width, width)
        dim(r.height, 50mm)
        dim(c.diameter, bore, pmi: true)
        dim(distance(c.center, r.left), 15mm)
        dim(distance(c.center, r.bottom), 15mm)
        let diagonal = measure(distance(r.corner(0), r.corner(2)))   // driven
    }
    part(s |> extrude(6mm), name: "Plate")
}
```

Custom constraints are Ingot functions restricted to a differentiable expression subset:

```
constraint chord_ratio(a: Arc, k: Real) -> Residual {
    a.chord_length - k * a.radius
}
```

### Where the solver lives

**Decision D-MEC-3:** Geometric constraint solving is one Anvil operation family, `anvil::solve_constraints` and `anvil::analyze_constraints`, used by 2D and 3D sketches, assembly mates, direct-edit live rules, control-point surface edits, scan intent snapping, routing, tolerance completeness and posture prediction. The constraint vocabulary is Ingot: each built-in constraint has a reference residual written in Ingot, and the operation may use a hand-written native kernel only when an oracle proves it equal to that reference. Custom `constraint` functions are lowered by the Ingot compiler to the same kernel IR that Flux uses for weak forms, with forward-mode differentiation. *Why:* the solver is a general geometric primitive with nine clients in this tab alone; it runs at 60 Hz during drags; it needs Anvil's curve and surface evaluators inside every Newton iteration (point on NURBS, distance to surface); and sketch results must rebuild identically under a pinned behavior version. *Rejected:* a Wasm component (every Newton iteration would cross the component boundary to evaluate Anvil geometry, or duplicate the evaluators); Ingot (sparse factorization and per-iteration evaluation belong in native code per contract section 4); separate solvers for sketches and assemblies (two diagnosis models, two sets of oracles, inconsistent behavior).

### Solver method

**Decision D-MEC-4:** The solver decomposes the system structurally, solves well-determined blocks numerically, and resolves under-determined parts by minimum displacement from the seeds. *Why:* the Zou et al. review finds that under- and over-constrained parts "must be correctly detected and resolved before numerical solving can work", that Newton-Raphson "heavily relies on an appropriate initial guess" and needs a square Jacobian, and that optimization-based solving is "stable and less sensitive to the initial guess". *Rejected:* rule-based constructive decomposition as the primary method (the same review notes that rule repertoires must be complete and that not every system is ruler-and-compass constructible); one monolithic solve (one bad region stalls the whole sketch, and conflicts cannot be localized).

The pipeline:

1. **Lower.** Entities become unknowns on manifolds: angles as unit complex numbers, 3D rotations as unit quaternions with a three-dimensional tangent space (the Ceres `Manifold` pattern), curve parameters bounded to their domains. Residuals are made dimensionless: lengths divide by the sketch's characteristic length (seed bounding-box diagonal), angles stay in radians.
2. **Reduce.** Fixed and fastened groups collapse into rigid clusters by union-find. Equations that determine one unknown directly are eliminated by forward substitution, as SolveSpace does for equations "solvable alone".
3. **Decompose.** A maximum matching on the bipartite unknown-equation graph gives the Dulmage-Mendelsohn decomposition into over-, well- and under-determined parts. The well-determined part splits into strongly connected blocks, solved in topological order. Ties break by `EntityId`, so the decomposition is deterministic.
4. **Solve blocks.** Each block runs trust-region Levenberg-Marquardt with analytic or differentiated Jacobians. Blocks above 64 unknowns use sparse column-pivoted QR from faer; smaller blocks use dense QR. Convergence requires the scaled residual below one hundredth of the smallest Anvil entity tolerance involved.
5. **Under-determined part.** The solver minimizes the weighted displacement from the seeds subject to the constraints, so unconstrained geometry moves as little as possible. SolveSpace reports that least-squares solving of under-constrained sketches gives "less surprising" drag behavior than weak dimensions; Crucible adopts it with per-parameter metric weights.
6. **Drag mode.** The dragged entity gets a weighted soft target. Each display frame is one warm-started solve; on release, the editor writes the solved seeds back to source.
7. **Over-determined part.** Equations whose residuals vanish at the solution are redundant but consistent: allowed, reported as warnings, excluded from degree-of-freedom counts. Equations that cannot vanish are conflicts.

[[DIAGRAM: constraint solve pipeline. Boxes: Ingot sketch block (seeds, constraints) → Lower (unknowns on manifolds, scaled residuals) → Reduce (rigid clusters, forward substitution) → Dulmage-Mendelsohn decomposition → three branches: well-determined blocks (LM in topological order), under-determined part (minimum displacement from seeds), over-determined part (consistency test) → Diagnosis (rank, kernel, minimal conflict sets, generic vs accidental) → Solve report and solved Body. Side arrow from Anvil evaluators into the LM box.]]

### Determinism and stability under edits

**Decision D-MEC-5:** The coordinates written in a sketch block are seeds, and the solved sketch is a deterministic function of seeds, constraints and the pinned operation version. When driving values move far from the values measured at the seeds, the solver follows a predictor-corrector continuation path from the seed values to the targets instead of jumping, so it stays on the seeds' solution branch. Discrete qualifiers (angle orientation, tangency side, arc direction, side of a signed distance) are captured when a constraint is created and stored in source. *Why:* the result must not depend on edit history, only on source; continuation is the standard remedy for Newton's sensitivity to the initial guess that the Zou review notes; stored qualifiers make the intended branch explicit. *Rejected:* solving from the previous session's solution (history-dependent, breaks determinism and merges); homotopy that finds all solutions (complete but too slow for interactive use, per the same review).

If continuation cannot reach the targets, the solver returns `BranchFlip` or `NoConvergence` with the last reachable value. It never returns a solution on a different branch without saying so.

### Diagnosis

`anvil::analyze_constraints` returns a `SolveReport`:

| Item | Method | Output |
| --- | --- | --- |
| Degrees of freedom | Kernel of the scaled Jacobian at the solution, by rank-revealing QR, with SVD on ambiguous blocks | Total count; per entity free motions as basis vectors, shown as arrows |
| Fully constrained entities | An entity is fixed when no kernel vector moves its unknowns | Per-entity state for coloring |
| Redundant sets | Row dependencies of the Jacobian | Minimal dependent sets |
| Conflict sets | Deletion filter over the over-determined part, in creation order | An irreducible set; every member offered as a `Fix` |
| Generic or accidental | Rank recomputed at a witness configuration: incidence-type constraints (coincident, parallel, tangent and similar) hold, and metric values are fixed pseudo-random rationals derived from `EntityId`s | "Always dependent" (three triangle angles) versus "dependent at current values" |
| Certification | Witness coordinates are rational (angles use rational points on the unit circle), so polynomial constraints give a rational Jacobian whose rank is computed exactly for blocks up to 200 unknowns. A second witness guards against an unlucky first one. Other verdicts are numerical and count as certified only when the singular-value gap exceeds 10^6 | `certified: bool` per verdict |

The witness step follows the witness configuration method, which detects structural and non-structural dependencies that graph counting alone misses. Zou and Feng show that its greedy variants can return non-minimal dependent sets and depend on the seed equation. Crucible therefore runs a minimality pass after the greedy pass and fixes the scan order by `EntityId`.

Error kinds: `Conflict { set }`, `Redundant { set }` (warning), `NoConvergence { block, residual }`, `BranchFlip { qualifier }`, `Degenerate { entity }` (zero-length line, zero radius), `ResolveError` from `use_edges`.

### Splines

Interpolating splines solve through points with optional tangent direction, tangent magnitude and curvature handles; each handle is a constrainable entity. Control-point NURBS expose control points and weights as unknowns, while knots and degree are fixed parameters of the entity.

Curve-length dimensions use Gauss-Legendre quadrature with an adaptive error bound below the convergence tolerance. A `fair` option adds a curvature-variation energy to the under-determined objective, giving smooth shapes when a spline is not fully constrained.

### 3D sketches

3D sketches use the same entities with a z unknown, plus `on_plane`, `on_surface` and `along` constraints. They drive sweep paths, routes, weldment skeletons and wire frames. Surface-bound points add the two surface parameters as unknowns and keep them inside the trimmed domain through bound constraints.

### Sketching contract

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| 2D sketch solve | `sketch(plane) { … } -> Sketch` | Typed errors above; partial result with the failing block highlighted | MEC-O-SK-1 to 4 | 1 |
| Degree-of-freedom report | `s.report() -> SolveReport` | Uncertified verdicts flagged | MEC-O-SK-2 | 1 |
| Drag | `api` Edit stream; 60 Hz target | Drops to the last converged frame | MEC-O-SK-5 | 1 |
| Splines (interpolating) | `spline(points, handles)` | `Degenerate` on coincident through points | MEC-O-SK-6 | 1 |
| NURBS, conics, ellipses | Entities above | As above | MEC-O-SK-6 | 2 |
| 3D sketch | `sketch3d() { … }` | As 2D | MEC-O-SK-1 (3D set) | 2 |
| Inequalities | `dim_range(target, min, max)` | `Conflict` when infeasible | MEC-O-SK-3 | 2 |
| Custom constraints | `constraint f(…) -> Residual` | Compile error if outside the differentiable subset | MEC-O-SK-7 | 2 |

Operations used: `anvil::solve_constraints`, `anvil::analyze_constraints`, `anvil::evaluate_curve`, `anvil::closest_point`, `anvil::intersect`, `anvil::project_curve`, `anvil::offset_curve`, `anvil::make_regions` (planar arrangement into faces).

Targets: a 200-entity sketch re-solves in under 2 ms native; a 2,000-entity sketch drag step takes under 8 ms native and under 16 ms in the browser; a full diagnosis of 2,000 entities takes under 50 ms. All are targets on the phase 0 reference laptop.

## Part features

### Conventions

**Decision D-MEC-6:** Features that create material from profiles (`extrude`, `revolve`, `sweep`, `loft`, `boundary`, `rib`, `thicken`) return new tool bodies. Booleans are written only with the operators `+`, `-` and `&`, or with `combine` for n-ary cases. Features that dress existing geometry (`fillet`, `chamfer`, `shell`, `draft`, `hole`, `thread`, direct edits) take a body and return it modified. *Why:* one spelling per intent; the boolean is visible in history; Kiln caches the tool body apart from the boolean, so editing the target does not rebuild the tool. *Rejected:* an add, remove or intersect option on every feature, as Onshape's features have [unverified] (a second spelling of the same operator).

```
use std::mech::{sketch, extrude, hole, fillet, HoleSpec, ThreadSpec}

pub feature housing(depth: Length = 30mm) -> Part {
    let block  = sketch(plane.xy) { rect(center: origin, 90mm, 60mm) } |> extrude(depth)
    let pocket = sketch(block.face(role: end_cap)) { rect(center: origin, 70mm, 40mm) }
                 |> extrude(UpTo(depth - 4mm), dir: -normal)
    let body   = (block - pocket)
                 |> hole(at: block.face(role: end_cap).corners(inset: 8mm),
                         spec: HoleSpec::tapped(ThreadSpec::iso_metric("M5"), depth: 10mm))
                 |> fillet(block.edges(role: side(any), parallel_to: z), 5mm)
    part(body, name: "Housing").material(alu_6061_t6)
}
```

`Extent` is shared by every profile feature: `Blind(Length)`, `Symmetric(Length)`, `ThroughAll`, `UpTo(Query)`, `UpToNext(Body)`, `Offset(Query, Length)` and `UpToVertex(Query)`. `Repr` (`Cosmetic`, `Simplified`, `Exact`) selects the representation level where a feature offers one.

### Profile features

```
pub feature extrude(profile: Profile, extent: Extent = Blind(10mm), dir: Direction = normal,
                    end: Option<Extent> = none, draft: Angle = 0deg, thin: Option<Length> = none) -> Body
pub feature revolve(profile: Profile, axis: Axis, angle: Extent<Angle> = Full,
                    thin: Option<Length> = none) -> Body
pub feature sweep(profile: Profile, path: Path, frame: SweepFrame = RotationMinimizing,
                  guides: [Path] = [], twist: Option<Field<Path, Angle>> = none,
                  scale: Option<Field<Path, Real>> = none, solid: Bool = true) -> Body
pub feature loft(sections: [Profile], guides: [Path] = [], centerline: Option<Path> = none,
                 start: EndCondition = Free, end: EndCondition = Free,
                 connect: [VertexMatch] = auto, closed: Bool = false) -> Body
pub feature boundary(u: [Path], v: [Path] = [], conditions: [EdgeCondition] = []) -> Body
pub feature thicken(surface: Query<Face>, t: Length, side: Side = Outside) -> Body
pub feature rib(edges: Query<Edge>, t: Length, height: Option<Length> = none, side: Side = Both,
                draft: Angle = 0deg, normal_to_sketch: Bool = false) -> Body
pub feature helix(axis: Axis, pitch: Length, turns: Real, taper: Angle = 0deg, hand: Hand = Right) -> Path
```

`SweepFrame` is one of `RotationMinimizing` (the double-reflection method [unverified source]), `FixedNormal(Direction)`, `FollowSurface(Query<Face>)`, `GuideCurve(Path)` or `Frenet`. Rotation-minimizing is the default because Frenet frames flip at inflection points.

`EndCondition` is `Free`, `NormalToProfile(weight)`, `Tangent(Query<Face>, weight)` or `Curvature(Query<Face>)`. Variation along a path is a `Field` over the path, so twist and scale laws reuse the core type.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Extrude | Profile regions to a solid or sheet; caps and sides get roles | `ResolveError` on an `UpTo` target; `SelfIntersecting` when drafted sides cross, with the largest feasible draft as a `Fix` | MEC-O-PF-1 | 1 |
| Revolve | Profile about an axis; profile crossing the axis rejected | `CrossesAxis { segment }` with "trim at axis" as a `Fix` | MEC-O-PF-1 | 1 |
| Sweep | Profile along a G1 path with a frame rule | `PathNotG1 { vertex }`; `SelfIntersecting { parameter }` when the profile exceeds the path's curvature radius, reported as the minimum radius found | MEC-O-PF-2 | 1 (single path), 2 (guides, laws) |
| Loft | Sections with guides and end conditions; vertex matching automatic by arc length or explicit | `Twisted` when matching produces crossing rulings, with suggested matches; `SectionsNotClosed` | MEC-O-PF-2 | 1 (no guides), 2 |
| Boundary | Two-direction curve network with G0 to G2 edge conditions | `NetworkNotCompatible { curves }` when curves do not intersect within tolerance | MEC-O-SF-2 | 2 |
| Thicken | Offset a face set into a solid | `OffsetSelfIntersection { faces, max_t }` | MEC-O-PF-3 | 1 |
| Rib | Open profile extended to the bounding body, with draft | `NoBoundary` when the profile meets no material | MEC-O-PF-1 | 1 |
| Helix and spiral | Exact helices are B-splines with recorded `ErrorBound` from `anvil::approximate_curve` | `Degenerate` on zero pitch | MEC-O-PF-2 | 1 |

Operations: `anvil::extrude`, `anvil::revolve`, `anvil::sweep`, `anvil::loft`, `anvil::boundary_surface`, `anvil::offset_faces`, `anvil::boolean`, `anvil::extend_face`, `anvil::make_regions`.

### Holes and threads

```
pub feature hole(body: Body, at: Query<Point>, spec: HoleSpec, extent: HoleExtent = ThroughAll,
                 from: Query<Face> = auto, dir: Direction = auto) -> Body
pub feature thread(body: Body, faces: Query<Face>, spec: ThreadSpec, length: Extent = Full,
                   repr: Repr = Cosmetic) -> Body
```

`HoleSpec` is a semantic record: `simple(d)`, `counterbore(d, cb_d, cb_depth)`, `countersink(d, csk_d, angle)`, `counterdrill`, `spotface`, `tapped(thread, depth, drill: auto)`, `tapered_pipe(thread)` and `clearance(fastener, fit)`. Every diameter accepts a `Tol<Length>` or an ISO 286 fit class such as `H7`.

`HoleExtent` is `ThroughAll`, `Blind(depth, tip_angle: 118deg)` or `UpTo(Query)`. A hole that crosses several bodies records each segment, so a fastener stack can read the hole chain.

Standards ship as data packages pinned in the lockfile:

| Data package | Content | Phase |
| --- | --- | --- |
| `std::standards::iso_metric_thread` | Basic profile (ISO 68-1), general plan (ISO 261), tolerances and fits (ISO 965-1) [unverified editions] | 1 |
| `std::standards::unified_thread` | UN, UNC, UNF, UNEF series and classes (ASME B1.1) [unverified edition] | 1 |
| `std::standards::pipe_thread` | ISO 228-1, ISO 7-1, NPT (ASME B1.20.1) [unverified editions] | 2 |
| `std::standards::trapezoidal_thread` | ISO 2904 trapezoidal, ACME (ASME B1.5) [unverified editions] | 2 |
| `std::standards::clearance_holes` | Fine, medium and coarse series for metric fasteners (ISO 273 and its successor) and inch fasteners [unverified editions] | 1 |
| `std::standards::iso286` | Limits and fits, tolerance grades and fundamental deviations [unverified edition] | 1 |

**Decision D-MEC-7:** Holes and threads are semantic first. `hole` writes a `HoleSpec` record and `thread` writes a `ThreadSpec` record keyed by the created entity ids; geometry follows from the record. Threads default to `Repr::Cosmetic`: nominal geometry (minor diameter for internal threads, major for external) plus the record. `Repr::Exact` builds the helical flank by sweep and boolean. *Why:* drawings, AP242 PMI, CAM (MFG tab), fastener logic and inspection all need the semantics, not the helix; exact threads multiply face counts and slow every downstream operation. *Rejected:* geometry-only holes recognized later by feature recognition (recognition is lossy and cannot recover tolerance class or thread series).

Failure behavior: `UnknownSize { series, near: [sizes] }` when a size is not in the pinned table; `BreaksOut { faces }` when a blind hole exits the body, with "make through" as a `Fix`; `ThreadTooLong` when thread length exceeds hole depth minus the tap runout. Oracle: MEC-O-PF-4 checks every generated size against its table and the NIST hole test cases. Operations: `anvil::boolean`, `anvil::revolve`, `anvil::sweep`, `anvil::helix`.

### Dress-up features

```
pub feature fillet(body: Body, edges: Query<Edge>, r: Radius, profile: BlendProfile = Circular,
                   setback: Option<Setback> = none, overflow: Overflow = Auto,
                   fallback: Fallback = Fallback::None) -> Body
pub feature chamfer(body: Body, edges: Query<Edge>, spec: ChamferSpec = ChamferSpec::equal(1mm)) -> Body
pub feature face_fillet(body: Body, a: Query<Face>, b: Query<Face>, r: Radius,
                        hold_lines: [Query<Edge>] = []) -> Body
pub feature full_round(body: Body, side_a: Query<Face>, middle: Query<Face>, side_b: Query<Face>) -> Body
pub feature shell(body: Body, remove: Query<Face> = none, t: Thickness, side: Side = Inside) -> Body
pub feature draft(body: Body, faces: Query<Face>, pull: Direction, angle: Angle,
                  neutral: Neutral = Neutral::plane(auto)) -> Body
```

`Radius` is a `Length` or a `Field<Edge, Length>` for variable radius. `Thickness` is a `Length` or a `Field<Face, Length>`. `BlendProfile` is `Circular`, `Conic(rho)`, `ChordLength(Length)` or `Curvature` (G2 to both faces).

`ChamferSpec` is `equal(d)`, `two_distances(d1, d2)`, `distance_angle(d, a)` or `vertex(d1, d2, d3)`. `Neutral` is `plane(Query)`, `parting_line(Query<Edge>)` or `step(Query<Edge>)`.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Constant-radius fillet | Rolling-ball blend on edge chains; tangent chains propagate unless `propagate: false` | `BlendFailed { edges, reason }` with reasons `RadiusTooLarge(max)`, `VertexUnresolved`, `Overflow`; offers smaller radius, split chain, or `Fallback::Implicit(max_deviation)` | MEC-O-PF-5 | 1 |
| Chamfer | Equal, two-distance, distance-angle, vertex | As fillet | MEC-O-PF-5 | 1 |
| Variable radius | `Field<Edge, Length>` sampled at edge parameters | As fillet | MEC-O-PF-5 | 2 |
| Setback vertex blends | Corner patches at three or more edges | `VertexUnresolved` with implicit fallback offer | MEC-O-PF-5 | 2 |
| Conic and G2 blends | `Conic(rho)` and `Curvature` profiles | As fillet | MEC-O-SF-1 | 3 |
| Face fillet and full round | Blend between face sets with hold lines | `NoContact` when the ball cannot touch both sets | MEC-O-PF-5 | 2 |
| Shell | Uniform, per-face and `Field` thickness; inside, outside or mid | `OffsetSelfIntersection { faces, max_t }` with smaller thickness or implicit fallback | MEC-O-PF-3 | 1 (uniform), 2 (variable) |
| Draft | Neutral plane, parting line, step | `DraftFailed { faces }` when the drafted face cannot meet its neighbors | MEC-O-PF-6 | 1 (neutral plane), 3 (parting and step) |

The blend roadmap follows Anvil's research program from the contract. The implicit fallback is opt-in per D-MEC-2.

The returned `ErrorBound` is stored in the part's metadata and shown in its properties. Operations: `anvil::blend`, `anvil::chamfer`, `anvil::offset_body`, `anvil::draft_faces`, `anvil::implicit_from_brep`, `anvil::brep_from_implicit`.

### Patterns and mirror

```
pub feature pattern<T: Patternable>(seed: T, at: [Transform], mode: PatternMode = Geometry,
                                    skip: [Int] = []) -> T
pub fn linear(dir: Direction, count: Int, spacing: Length,
              dir2: Option<(Direction, Int, Length)> = none) -> [Transform]
pub fn circular(axis: Axis, count: Int, angle: Extent<Angle> = Full) -> [Transform]
pub fn along(path: Path, count: Int, spacing: Spacing = Equal, orient: Orient = Follow) -> [Transform]
pub fn at_points(points: Query<Point>) -> [Transform]
pub fn fill(region: Query<Face>, layout: Layout, spacing: Length, margin: Length = 0mm) -> [Transform]
pub fn by_density(region: Query<Face>, density: Field<Face, Density>, method: Sampler = Cvt) -> [Transform]
pub feature mirror<T: Mirrorable>(seed: T, plane: Plane) -> T
```

`Patternable` covers bodies, tool bodies, features and face sets. A pattern is one feature with a list of transforms, and every named pattern is a transform generator. Patterns whose parameters vary per instance are plain Ingot loops.

```
let vents = pattern(slot_tool, at: linear(dir: x, count: 8, spacing: 6mm))
let graded = for i in 0..8 { slot_tool(length: 10mm + i * 2mm) |> move(x: i * 6mm) }
cover - vents
```

**Decision D-MEC-8:** `PatternMode::Geometry` (default) evaluates the seed once and places transformed copies with one n-ary boolean. `PatternMode::Feature` re-evaluates the seed per instance, which is required when an instance depends on its location, for example `UpToNext`. *Why:* geometry mode is O(1) feature evaluations and lets Kiln cache one seed; feature mode keeps correctness when context matters. *Rejected:* always re-evaluating (slow on large patterns); always copying (wrong for location-dependent extents).

`by_density` samples a Field by a fixed number of Lloyd iterations toward a centroidal Voronoi tessellation, seeded from `EntityId`s, so it is deterministic. Failure behavior: `InstanceFailed { index, error }` reports per instance and the feature fails unless `skip_failed: true` is set, which lists the skipped indices. Oracle: MEC-O-PF-7 checks instance counts, transforms and volume additivity.

Phase: linear, circular and points in phase 1; along, fill and density in phase 2. Operations: `anvil::transform`, `anvil::boolean` (n-ary).

### Split and combine

```
pub feature split(body: Body, tool: SplitTool) -> [Body]
pub feature split_face(body: Body, faces: Query<Face>, by: FaceSplit) -> Body
pub fn combine(bodies: [Body], op: BoolOp, keep_tools: Bool = false) -> Body
```

`SplitTool` is a plane, a face set, a sheet body or a sketch. `FaceSplit` is `curves(Query)`, `isocline(dir, angle)` or `silhouette(dir)`; the last two serve molding. `combine` is an n-ary boolean over any representation; the contract decides that mixed-representation booleans need no conversion.

Failure behavior: `BooleanFailed { faces, reason }` with the coincident or tangent faces highlighted; `EmptyResult` is an error unless `allow_empty: true`. Oracle: MEC-O-PF-8 checks volume identities (`vol(a + b) + vol(a & b) = vol(a) + vol(b)`) on random pairs from the ABC dataset.

Phase 1. Operations: `anvil::boolean`, `anvil::split`, `anvil::imprint`.

### Direct edits

Direct edits apply to any B-rep, including imported geometry with no history. They are ordinary features recorded in history.

```
pub feature move_faces(body: Body, faces: Query<Face>, by: FaceMove,
                       rules: LiveRules = LiveRules::detect()) -> Body
pub feature replace_face(body: Body, faces: Query<Face>, with: Query<Face>) -> Body
pub feature delete_face(body: Body, faces: Query<Face>, heal: Heal = Heal::Extend) -> Body
pub feature edit_aspect(body: Body, target: ShapeAspect, set: AspectEdit) -> Body
pub feature drive(body: Body, between: (Query, Query), value: Length) -> Body
```

`FaceMove` is `offset(Length)`, `translate(Vector)` or `rotate(Axis, Angle)`. Recognized shape aspects come from `anvil::recognize_aspects`: holes, fillets, chamfers, bosses, pockets and patterns.

`edit_aspect` changes a recognized parameter such as a fillet radius or a hole diameter. `drive` places a 3D driving dimension between two entities of any B-rep.

Synchronous-style behavior comes from live rules. `LiveRules::detect()` asks `anvil::recognize_relations` for coplanar, coaxial, concentric, tangent, perpendicular, symmetric and equal-radius relations among the faces near the edit. The detected rules are written into source as an explicit list.

```
let edited = imported |> move_faces(imported.faces(near: p, role: any), by: offset(2mm),
    rules: [coaxial(f12, f31), coplanar(f4, f9), tangent(f12, f13)])  // written by detect(), editable
```

**Decision D-MEC-9:** Direct edits solve face motions with the shared constraint solver. Each moved or affected face gets a rigid motion or offset unknown; the edit and the live rules are constraints; `anvil::move_faces` then re-intersects neighbors and regrows or removes blends. The recognized rules are written to source. *Why:* Siemens describes synchronous technology as editing without a fixed history while related geometry adjusts "to maintain design intent", including on imported models; Crucible gets the same behavior from mechanisms it already has, and writing the rules to source keeps it explicit and reviewable. *Rejected:* a separate history-free modeling mode (two models of the same part); hidden rule inference at every rebuild (results would change when the recognizer improves).

| Capability | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- |
| Move, offset, rotate faces | `TopologyChange { faces }` when a neighbor would vanish, with "allow topology change" as a `Fix` | MEC-O-PF-9 | 2 |
| Replace face, delete face with heal | `HealFailed { loop }` when extended neighbors leave a gap | MEC-O-PF-9 | 2 |
| Recognized aspect edits | `NotRecognized` with the recognizer's best partial match | MEC-O-PF-9 | 2 |
| Live rules | `RuleConflict { set }` from the solver's conflict sets | MEC-O-PF-9 | 2 |

Operations: `anvil::move_faces`, `anvil::replace_face`, `anvil::delete_face`, `anvil::recognize_aspects`, `anvil::recognize_relations`, `anvil::solve_constraints`.

### Deform, wrap, emboss and engrave

```
pub feature deform(body: Body, map: DeformMap, tolerance: Length = body.tolerance) -> Body
pub feature wrap(curves: Sketch, onto: Query<Face>, method: WrapMethod = auto, anchor: CoordSys) -> Sketch
pub feature emboss(body: Body, curves: Sketch, onto: Query<Face>, height: Length,
                   mode: EmbossMode = Raise, draft: Angle = 0deg) -> Body
```

`DeformMap` is `bend(axis, angle, region)`, `twist(axis, angle, region)`, `taper(axis, factor)`, `stretch(axis, factor)`, `cage(lattice, moves)` or `field(Field<Body, Displacement>)`. The field variant closes a loop with Flux: a warpage or springback displacement can pre-compensate a mold insert or a die face.

`WrapMethod` is `Developable` (isometric and exact for planes, cylinders and cones), `Conformal` (Boundary First Flattening, below) or `Geodesic` (exponential map from the anchor). `EmbossMode` is `Raise`, `Engrave` or `Imprint` (split faces only).

Deformed B-rep surfaces cannot stay exact under general maps. `deform` refits every face within `tolerance` and returns the achieved `ErrorBound`; affine maps and tapers of planar faces stay exact. `wrap` onto a non-developable face returns a distortion `Field<Face, Real>` (area and angle ratios) alongside the wrapped curves.

Failure behavior: `FoldOver { region }` when the map is not injective; `ToleranceNotMet { achieved }` with a looser tolerance as a `Fix`; `WrapOutsideFace` when wrapped curves leave the trimmed face. Oracle: MEC-O-PF-10 checks deviation from the analytic map at sample points and exact arc-length preservation on developable wraps.

Phase 3. Operations: `anvil::deform`, `anvil::approximate_surface`, `anvil::parameterize`, `anvil::project_curve`, `anvil::extrude`, `anvil::boolean`.

### Derived parts and multi-body design

```
pub feature derive(source: PartRef, take: Take = Take::bodies(all), mirror: Option<Plane> = none,
                   scale: Scale = Scale::uniform(1.0), params: Params = default) -> [Body]
pub fn part(body: Body, name: String, item: Option<ItemNumber> = none) -> Part
pub fn parts(bodies: [(Body, String)]) -> [Part]
```

`PartRef` names a feature in this design repository or in a dependency pinned by the lockfile. `take` can select bodies, sketches, coordinate systems, interfaces and parameters. `Scale::anisotropic(x, y, z)` serves mold shrinkage.

A source file may return several Parts from shared sketches and skeletons; this is the multi-part, top-down workflow described under assemblies. A single Part may also hold several bodies, as a weldment does; each body is a cut-list item but not a BOM line.

Failure behavior: `SourceChanged { from, to }` is not an error. A dependency bump is a Proposal that shows the derived part's geometry diff, so upstream changes never silently alter released parts. `TakeMissing { name }` when the source no longer exports an item.

Oracle: MEC-O-PF-11 rebuilds derived parts against pinned and bumped sources. Phase 1 (same repository), 2 (cross-repository). Operations: `anvil::transform`, including mirror and anisotropic scale.

### Configurations, design tables and part families

**Decision D-MEC-10:** A configuration is a parameter record. A design table is a table of parameter records. A part family is a design table whose rows carry part identity. Suppression is a `Bool` parameter used in an `if`. There is no separate configuration mechanism. *Why:* Ingot features are already functions of typed parameters; a second mechanism (as in SOLIDWORKS configurations [unverified]) would duplicate parameters and break the one-model principle. *Rejected:* configuration-specific feature states stored beside the source (invisible in code review, hard to merge).

```
pub let brackets = family(bracket, key: "item", rows: [
    { item: "BR-060", width: 60mm, thickness: 4mm ± 0.1mm, load: 1.2kN },
    { item: "BR-080", width: 80mm, thickness: 5mm ± 0.1mm, load: 2.0kN },
])
pub let more = family(bracket, key: "item", rows: table("brackets.csv"))  // header: item, width [mm], …
```

`family` checks every row's types and units at compile time, including CSV headers with units. Each row is a Part with its own item number in the BOM. Kiln caches rows independently.

A family is green only when every row builds and passes every check, and CI reports failures per row. Failure behavior: `RowFailed { key, error }`; `DuplicateKey`; `UnitMismatch { column, expected }` at compile time. Oracle: MEC-O-PF-12.

Phase 1. The Ingot tab owns the final syntax of `family` and table literals. This group uses no operations of its own.

### Lattices and Field-driven geometry

Golden product 2 needs lattices driven by a Flux result.

```
pub feature lattice(region: Body, cell: Cell, size: Length,
                    thickness: Field<Body, Length>, skin: Option<Length> = none) -> Body
```

`Cell` covers strut cells (body-centered cubic, octet) and triply periodic minimal surfaces (gyroid, Schwarz P, diamond). Generation runs in a Wasm component that emits an `Implicit` body; Anvil combines it with B-rep skins by mixed-representation boolean. Thickness is usually derived from a Flux density or stress Field.

Failure behavior: `BelowMinFeature { region, min }` when local thickness falls below the minimum in the selected MFG process profile. Oracle: MEC-O-PF-13 compares relative density with analytic values for each cell type.

Phase 1. Operations: `anvil::boolean` (mixed representation), `anvil::offset_body` for skins.

### Machine elements

`std::mech::machine` supplies parametric machine elements for golden product 3 (gearbox) and beyond.

| Machine element | Contract | Standard | Phase |
| --- | --- | --- | --- |
| Involute spur and helical gears | Module, teeth, pressure angle, helix angle, profile shift, tip and root relief, crowning | ISO 21771-1:2024 geometry, which includes flank modifications | 2 |
| Bevel, worm, internal gears | As above | ISO and AGMA references [unverified] | 3 |
| Shafts | Stepped sections, shoulders, grooves, undercuts, keyways | Keyways and splines per DIN and ISO tables [unverified] | 2 |
| Bearings, seals, retaining rings | Catalog parts with mating coordinate systems and housing fits | Supplier data via the parts catalog | 2 |
| Springs | Compression, extension, torsion; exact helix or cosmetic | | 2 |

Involute flanks are not rational curves. Gear features approximate them with B-splines whose `ErrorBound` is below 0.1 µm (target) and record the exact parameters as semantics for MFG gear cutting and for Flux contact analysis. Gear rating is a Flux and check-library concern, not geometry.

Failure behavior: `Undercut { teeth, min_shift }` and `PointedTip` with profile shift as a `Fix`; `MeshMismatch` when mated gears differ in module or pressure angle. Oracle: MEC-O-PF-15 compares flank points with ISO 21771-1 formulas. Operations: `anvil::approximate_curve`, `anvil::extrude`, `anvil::sweep`, `anvil::boolean`.

### Performance budget

The contract sets an exact rebuild of a 200-feature part after an early edit under 2 s. MEC meets it through three rules. Every feature declares its read set (the queries it resolves), so Kiln re-runs only features whose inputs changed.

Tool bodies are cached separately from booleans (D-MEC-6). Cosmetic threads and geometry-mode patterns keep face counts low. Oracle MEC-O-PF-14 times rebuilds of the golden products after edits at the first, middle and last features.

## Assemblies

### Structure

An Assembly is a tree of Instances with placements and mates (contract section 5). An Instance references a Part or Assembly feature by `PartRef`, with parameter overrides, a `Transform` and a representation choice. The same Part with different parameters is a different family row or a different call, so it is a different BOM line.

```
use std::mech::asm::{assembly, instance, revolute, fastened, gear}

pub feature gearbox(ratio: Real = 3.0) -> Assembly {
    let housing = instance(housing(), fixed: true)
    let input   = instance(shaft(d: 12mm ± 0.005mm))
    let pinion  = instance(spur_gear(module: 1.5mm, teeth: 18))
    let wheel   = instance(spur_gear(module: 1.5mm, teeth: round(18 * ratio)))
    assembly([housing, input, pinion, wheel], mates: [
        revolute(input.csys("axis"), housing.csys("bore_in")),
        fastened(pinion.csys("bore"), input.csys("seat")),
        gear(pinion, wheel, ratio: wheel.teeth / pinion.teeth),
    ])
}
```

Coordinate systems are the only attachment points for mates, as Onshape's mate connectors are "local coordinate systems located on or between entities". A feature publishes named coordinate systems (`"axis"`, `"bore_in"`), and `csys(query)` derives one from geometry: the axis of a cylinder, the center of a circular edge, a planar face's centroid.

Onshape notes that implicit connectors move when part geometry changes; Crucible makes this a typed outcome. Each `CoordSys` re-resolves through its anchor `Query`, and a failed resolution is a `ResolveError` on the mate, never a silent move.

### Mates

| Mate | Remaining freedom (T = translation, R = rotation, in the second coordinate system) | Limits | Phase |
| --- | --- | --- | --- |
| `fastened` | 0 | none | 1 |
| `revolute` | 1R about z | angle | 1 |
| `slider` | 1T along z | distance | 1 |
| `cylindrical` | 1T along z, 1R about z | both | 1 |
| `pin_slot` | 1T along x, 1R about z | both | 2 |
| `planar` | 2T in xy, 1R about z | both | 2 |
| `ball` | 3R | cone angle | 1 |
| `parallel`, `perpendicular`, `coaxial` | Orientation or axis relations | angle | 1 |
| `distance`, `angle` | One equation each, driving or driven | range | 1 |
| `tangent` | Surface contact with surface parameters as unknowns | none | 2 |
| `symmetric` (width) | Centers one face pair between another | none | 2 |
| `gear`, `rack_pinion`, `screw`, `linear` | Couple two freedoms by a ratio or pitch | none | 2 |
| `cam` | Follower point or face kept on a cam surface | none | 3 |

**Decision D-MEC-11:** Assembly mates use the same `anvil::solve_constraints` operation as sketches, with one SE(3) unknown per rigid cluster (quaternion plus translation on a product manifold). Fastened instances merge into rigid clusters before solving. Joint limits are inequalities solved by an active set. *Why:* one solver gives one diagnosis model: degrees of freedom shown as motion arrows, minimal conflict sets and generic-versus-accidental redundancy, the same in sketches and assemblies. *Rejected:* a separate assembly solver, the split that D-Cubed's separate 2D DCM and 3D DCM products reflect (duplicate oracles, different failure semantics); positioning by sequential transforms only (cannot close kinematic loops).

The `SolveReport` from sketching applies unchanged. One addition matters for mechanisms: redundant but consistent mates (two coaxial hinges on one door) are normal in real designs. They are reported as `Redundant` warnings, never errors, and passed to Flux, because rigid-body dynamics with redundant joints needs either redundancy removal or joint compliance.

### Kinematics and motion

```
let study = motion(gearbox(), drive: [(input_rev, angle(t) = 360deg/s * t)],
                   t: 0s..2s, samples: 200)
study.pose(wheel)                        // Field<Instance, Transform, Time>
study.velocity(wheel.csys("axis"))      // Field<Instance, AngularVelocity, Time>
study.require(min_clearance(study, housing, wheel) > 0.5mm)
```

Position analysis tracks the drivers by predictor-corrector continuation, sample to sample. Velocity and acceleration solve the linear systems from the differentiated constraint equations (J·q̇ = −∂Φ/∂t and its time derivative), using the Jacobian the solver already factored.

A rank drop of J (a toggle position) returns `Singular { t, mates }`; a limit reached returns `LimitReached { mate, t }`. Motion studies are kinematic only. Results use Flux's Field axes (`Field<Instance, Transform, Time>`), so a motion study is an ordinary Field with a `Time` axis.

**Decision D-MEC-12:** Dynamics belong to Flux. `motion` handles prescribed-motion kinematics; anything with forces, masses, contact or compliance goes to Flux's multibody solver, which reads the same Assembly. MEC hands over each Instance's mass properties (from Body and Material, with integration `ErrorBound`), each mate as a typed joint, the redundancy report, flagged contact pairs and drivers. *Why:* kinematics reuses the constraint solver; dynamics needs integrators, contact and Flux's validity envelopes. *Rejected:* a dynamics engine inside the assembly library (a second physics engine beside Flux).

### Interference and clearance

```
let clashes = interference(asm, scope: all, classify: true, ignore: [fastener_threads])
asm.require(clashes.hard().is_empty())
asm.require(min_clearance(asm, between: (fan, harness)) >= 3mm)
```

The broad phase is a bounding-volume hierarchy over instance tessellations from CAS. The narrow phase runs `anvil::distance` and `anvil::boolean` on exact B-reps. Each `Clash` carries the pair, the interference volume and a class.

| Class | Meaning | Default treatment |
| --- | --- | --- |
| `Hard` | Positive interference volume | Error |
| `Touching` | Zero gap within the entity tolerance | Info |
| `IntendedThread` | Fastener thread inside a mating `ThreadSpec` | Ignored |
| `IntendedFit` | Interference within a declared ISO 286 interference fit | Ignored, reported to tolerancing |
| `Clearance` | Gap below a declared minimum | Error when declared |

Dynamic interference checks motion studies with adaptive sampling. The sample spacing keeps the maximum point displacement between samples below half the clearance threshold, using each body's bounding radius and a bound on driver and joint velocities over each interval.

Under that bound, no contact between samples is missed; when no bound can be computed (near a singular position), the report says so. Targets: static interference over 10,000 instances in under 60 s, and incremental re-check after moving one instance in under 1 s.

### Exploded views

```
let ex = explode(asm, steps: [
    step([cover], along: z, by: 60mm),
    step(asm.fasteners(of: cover), along: their_axes, by: 30mm, trails: true),
])
```

Exploded views are named, ordered data stored with the Assembly and consumed by drawings, technical illustration and UI animation. `explode_auto(asm)` proposes steps from a disassembly sequence. Removal directions come from contact normals through a non-directional blocking graph, with fasteners first [unverified source for the method].

Failure behavior: `CollidesDuringStep { step, pair }` when a requested path collides, as a warning. Oracle: MEC-O-AS-5.

Operations: `anvil::transform`, `anvil::distance`, `anvil::sweep` for swept-volume checks. Phase 2, automatic proposals in phase 3.

### Flexible subassemblies

A subassembly instance is rigid by default: its internal mates are solved once and frozen. `instance(sub, flexible: true)` exposes its free internal degrees of freedom to the parent solve, so a hinge inside a door subassembly can be driven from the parent. Rigid is the default because it keeps large assemblies decomposed into small independent solves.

Failure behavior: parent conflicts list mates inside flexible subassemblies with their full path. Oracle: MEC-O-AS-1 includes nested mechanisms solved rigid and flexible, with equal results where both apply. Phase 2.

### Top-down design: skeletons and interfaces

**Decision D-MEC-13:** Cross-part references go only through skeletons and declared interfaces, both ordinary Ingot values. A skeleton is a feature returning a record of coordinate systems, sketches, surfaces and parameters. An interface is a typed record that one part provides and another consumes, checked for compatibility at compile time and on every build. Implicit in-context references that silently capture geometry of another part are not supported. *Why:* explicit dependencies keep the dependency graph acyclic and visible in review, and semantic merge stays possible; a captured reference is a dependency that review cannot see. *Rejected:* edit-in-context with captured references, as in SOLIDWORKS [unverified] (hidden coupling; failures appear far from their cause).

```
pub interface MotorMount {
    pilot: CoordSys,
    pilot_d: Tol<Length>,
    bolts: [CoordSys],
    thread: ThreadSpec,
}

pub feature nema17_mount() -> MotorMount { … }          // provided by the motor catalog part

pub feature plate(m: MotorMount) -> Part {              // consumed by the plate
    let base = sketch(plane.xy) { rect(center: origin, 60mm, 60mm) } |> extrude(5mm)
    let pilot = hole(base, at: m.pilot.origin, spec: HoleSpec::simple(fit(m.pilot_d.nominal, H7)))
    hole(pilot, at: m.bolts.origins(), spec: HoleSpec::clearance(m.thread, fit: Medium))
        |> part(name: "Motor plate")
}
```

`require compatible(a: MotorMount, b: MotorMount)` checks coordinate system poses, fits and thread specs. In an assembly, `mate_interface(a, b)` places both sides with one fastened or joint mate and checks compatibility.

Electronics uses the same mechanism for board outlines and connector keep-outs (ELX tab). Failure behavior: `Incompatible { field, provided, required }` at compile time or build time, with the mismatched field highlighted on both parts.

Oracle: MEC-O-AS-8 builds provider and consumer pairs with seeded mismatches and requires each to be reported. Phase 1 for skeletons, phase 2 for interfaces.

### Large assemblies

Each Instance chooses a representation:

| `InstanceRepr` | Content | Error stated |
| --- | --- | --- |
| `Full` | Exact B-rep, loaded on demand | None |
| `Graphics` | Cached tessellation from CAS at several levels of detail | Chordal deviation per level |
| `Envelope` | Oriented bounding box or convex hull | Hull deviation |
| `Shrinkwrap(tol)` | Outer skin from `anvil::shrinkwrap`: implicit offset, morphological closing, internal detail removed | `ErrorBound` from the operation |
| `Defeatured(rules)` | Holes, fillets and other shape aspects below a size removed through `anvil::recognize_aspects` and `anvil::delete_face` | Removed aspect list and volume change |
| `Excluded` | Not loaded | Excluded from mass properties, with a warning |

Opening an assembly loads structure, transforms and cached tessellations first; B-reps load only for instances being edited, measured or checked. Mass properties of non-`Full` instances come from the cached values of the full body, never from the simplified body. Simplified representations are named sets (`repr_set("simulation")`), so Flux and drawings can request one.

Failure behavior: `ReprUnavailable { instance, repr }` when a simplified representation cannot be built, with the error from the operation; the instance falls back only to a representation the user listed. Oracle: MEC-O-AS-4.

Targets beyond the contract's 1,000-part assembly from warm cache in under 10 s: open a 100,000-instance assembly for viewing in under 15 s from warm cache, and orbit it at 60 fps using levels of detail, both on the reference laptop.

### Standard parts and fasteners

Fasteners are catalog parts generated from standards data packages. Each carries the standard's designation and links to supplier records in the parts catalog.

| Data package | Examples | Phase |
| --- | --- | --- |
| `std::standards::iso_fasteners` | ISO 4762 socket head cap screws, ISO 4014 and 4017 hexagon bolts and screws, ISO 4032 nuts, ISO 7089 washers, ISO 10642 countersunk screws | 2 |
| `std::standards::din_fasteners` | DIN 912, DIN 933, DIN 934 and other legacy designations, mapped to their ISO successors | 2 |
| `std::standards::ansi_fasteners` | ASME B18.3 socket cap screws, B18.2.1 hex bolts, B18.2.2 nuts | 2 |
| `std::standards::pins_rings` | Dowel pins, retaining rings, keys | 2 |

All edition years in this table are [unverified]; each data package records the edition it encodes, and the lockfile pins it.

```
let joint = fasten(cover_holes, spec: FastenerSpec::iso4762(class: "8.8", washer: iso7089, nut: none),
                   engagement: Engagement::diameters(1.5))
```

`fasten` reads the hole chain, computes grip length from the stacked `HoleSpec` segments, adds the minimum thread engagement, picks the shortest standard length that satisfies both, and places screws, washers and nuts with mates. Changing the cover thickness re-selects the length. The default engagement rule depends on the tapped material and is a parameter, never a hidden constant.

Failure behavior: `NoStandardLength { needed, nearest: [lengths] }`; `HoleMismatch { hole, fastener }` when the clearance class does not fit the fastener; `EngagementTooShort { have, need }`. Each fastener records preload and tightening intent for Flux bolted-joint analysis; the calculation method (for example VDI 2230 [unverified]) lives in a check library.

Oracle: MEC-O-AS-6 checks selected lengths against hand-computed cases and table values. Phase 2.

### Mate inference

`suggest_mates(a, b)` ranks candidate mates from interfaces, recognized shape aspects (cylinder pairs, hole and fastener pairs, coplanar faces) and an optional learned ranker in a Wasm component. It is an editing aid for people and agents; suggestions become mates only when accepted, as ordinary source edits. Benchmark: the Fusion 360 Gallery Assembly-Joint dataset, where JoinABLe reports 79.53% accuracy against a reported human level of 80%.

Target: top-1 accuracy of at least 80% on that test split. Phase 3.

### Assembly-level features

A cut or hole defined at assembly level must say what it is: `mode: DerivedParts` creates derived Parts with new item numbers.

`mode: AfterAssembly` makes it a manufacturing operation on the assembled product, recorded in the MBOM and handed to the MFG tab, while the EBOM Parts stay unchanged. Failure behavior: omitting `mode` is a compile error that offers both modes as fixes.

Oracle: MEC-O-AS-3 checks that derived Parts and after-assembly operations give the same assembled geometry. Phase 2.

### Assembly oracles and phases

| Capability | Oracle | Phase |
| --- | --- | --- |
| Mate solve and diagnosis | MEC-O-AS-1: mechanism suite with known mobility counts (Grübler-Kutzbach), including redundant and accidental cases | 1 |
| Kinematics | MEC-O-AS-2: slider-crank and four-bar positions, velocities and accelerations against closed forms | 2 |
| Interference | MEC-O-AS-3: analytic overlap volumes of primitive pairs; NIST CTC 02 and 04 assembly fit | 1 |
| Large assemblies | MEC-O-AS-4: synthetic 100,000-instance assembly timing | 2 |
| Exploded views | MEC-O-AS-5: collision-free automatic explosion on the golden gearbox | 3 |
| Fasteners | MEC-O-AS-6 | 2 |
| Mate inference | MEC-O-AS-7: Fusion 360 Gallery joint test split | 3 |
| Skeletons and interfaces | MEC-O-AS-8: seeded interface mismatches | 1, 2 |

Operations used: `anvil::solve_constraints`, `anvil::analyze_constraints`, `anvil::distance`, `anvil::boolean`, `anvil::mass_properties`, `anvil::shrinkwrap`, `anvil::recognize_aspects`, `anvil::tessellate`.

## Surfacing

### Continuity

`Continuity` is `G0`, `G1`, `G2` or `G3`, with the usual geometric meaning: shared position, then tangent plane, then normal curvature in every direction, then its derivative. Every surfacing feature takes target continuities per edge and returns a `ContinuityReport` measured by Anvil's built-in G2 and G3 analysis. The report gives, for each edge, the maximum position gap, the maximum normal angle, the maximum relative curvature difference and the location of each maximum.

Default thresholds are Crucible defaults, overridable per design: 0.001 mm position, 0.02 deg normal angle, 2% curvature. A feature that cannot meet its targets returns `ContinuityNotMet { edge, achieved }`. It never relabels the result at a lower continuity.

### Curves

| Feature | Contract | Phase |
| --- | --- | --- |
| `curve_cv(points, degree, weights)` | Control-point NURBS | 2 |
| `curve_through(points, tangents, fair: Bool)` | Interpolating spline with optional fairing energy | 1 |
| `blend_curve(a, b, start: Continuity, end: Continuity, shape)` | Bridge between curve ends, G0 to G3 | 2 |
| `offset_curve(c, d, on: Option<Query<Face>>)` | Planar, 3D or geodesic offset on a face | 2 |
| `iso_curve(face, u or v)`, `project(c, onto, dir)`, `intersect(a, b)` | Derived curves | 1 |
| `rebuild_curve(c, degree, spans, tol)` | Approximation with `ErrorBound` | 2 |
| Curve analysis | `curvature(c) -> Field<Edge, Curvature>`, inflection points, comb display | 1 |

Failure behavior: `Degenerate` on coincident points; `ToleranceNotMet { achieved }` from `rebuild_curve`. Oracle: MEC-O-SK-6. Operations: `anvil::evaluate_curve`, `anvil::offset_curve`, `anvil::project_curve`, `anvil::intersect`, `anvil::approximate_curve`.

### Surfaces

| Feature | Contract | Method | Phase |
| --- | --- | --- | --- |
| Extruded, revolved, ruled, swept surfaces | Profile features with `solid: false` | As part features | 1 |
| `boundary(u, v, conditions)` | Two to four sides or a two-direction network; G0 to G2 to adjacent faces per edge | Gordon-style network interpolation [unverified source] | 2 |
| `network(u, v, tol)` | Curve network that need not intersect exactly; gaps up to `tol` | Least-squares network fitting | 3 |
| `fill(boundary, conditions, guides, points)` | N-sided hole with G0 to G2 to neighbors | Multi-patch NURBS with internal G2 seams; transfinite construction [unverified source] | 3 |
| `blend_surface(e1, e2, c1, c2, shape)` | Bridge between two edges, G1 to G3 | Hermite construction along both edges | 3 |
| `match(face, edge_of, target, continuity, hold)` | Modify one face's control points to match a target edge | Constrained least squares on control points | 3 |
| `extend(face, by, mode)` | Natural, linear or curvature-continuous extension | | 2 |
| `offset_surface(face, d)` | Exact for analytic faces, approximated with `ErrorBound` otherwise | | 2 |
| `edit_cv(face, moves, symmetry)` | Direct control-point editing with constraints | Shared solver | 3 |
| `trim`, `untrim`, `sew`, `knit_to_solid` | Topology operations | | 1 |

Operations: `anvil::boundary_surface`, `anvil::fill_surface`, `anvil::blend_surface`, `anvil::match_surface`, `anvil::extend_face`, `anvil::offset_faces`, `anvil::approximate_surface`, `anvil::sew`, `anvil::analyze_continuity`, `anvil::curvature`. Failure behavior: `ContinuityNotMet { edge, achieved }`, `NetworkNotCompatible { curves }`, `BoundaryNotClosed { gap }`. Oracles: MEC-O-SF-1 (continuity) and MEC-O-SF-2 (interpolation).

### Class-A evaluation

All evaluation tools return `Field`s, so the UI paints them and checks constrain them.

| Tool | Output | Phase |
| --- | --- | --- |
| Gaussian, mean, minimum and maximum curvature | `Field<Face, Curvature>` | 2 |
| Zebra and reflection lines | `Field<Face, Real>` from a light setup; isophote lines extracted as curves | 2 |
| Highlight lines | Curves for a light line set, with continuity of the highlight across edges | 3 |
| Curvature combs on edges and section cuts | Curves with comb data | 2 |
| Edge continuity | `ContinuityReport` per edge | 2 |
| Draft angle | `Field<Face, Angle>` for a pull direction | 2 |
| Deviation | `Field<Face, Length>` between two bodies, or a body and a scan | 2 |
| Control-net quality | Control-point count, degree, knot uniformity, polygon kinks, curvature monotonicity on edge curves | 3 |

```
use std::mech::surf::{class_a}
hood.require(class_a(hood.faces(visible), edges: G2, monotone_edge_curvature: true,
                     max_degree: 7, max_spans: 3))
```

**Decision D-MEC-14:** Class-A quality is a check library over analysis Fields, not a mode. *Why:* one mechanism (checks) covers every quality gate; agents and CI enforce surface quality the same way they enforce stress limits. *Rejected:* a separate Class-A workbench (an island of features with its own rules).

Operations: `anvil::curvature`, `anvil::analyze_continuity`, `anvil::isophotes`, `anvil::section_body`, `anvil::distance`. Oracle: MEC-O-SF-1.

### SubD workflow

The SubD representation is part of Anvil's `Body` (contract section 7). Features:

| Feature | Contract | Phase |
| --- | --- | --- |
| `subd_box`, `subd_cylinder`, `subd_sphere`, `subd_from_mesh` | Control cages | 3 |
| `extrude_faces`, `insert_loop`, `bevel_edges`, `bridge`, `fill_hole`, `delete_faces` | Cage edits with stable roles | 3 |
| `crease(edges, sharpness)` | Sharp and semi-sharp creases | 3 |
| `symmetry(plane)`, `radial_symmetry(axis, n)` | Mirrored and radial cages | 3 |
| `cage_move(vertices, by)` | Recorded vertex moves; the gesture writes the vector to source | 3 |
| `to_nurbs(subd, at_extraordinary: Continuity = G1, packing: Packed)` | Conversion with `ErrorBound` | 3 |

Catmull-Clark limit surfaces are uniform bicubic B-splines away from extraordinary vertices and only tangent-continuous at them [unverified source]. Rhino 8's `ToNURBS` documents the resulting choice: the polysurface is "always G2 in smooth SubD regions"; at extraordinary vertices the user chooses G0, G1, G1x, G1xx or G2, and forcing G2 "adds bulges or dents". It also packs quad grids into larger NURBS surfaces.

**Decision D-MEC-15:** `to_nurbs` converts regular regions exactly, packs quad grids into larger patches by default, and at extraordinary vertices defaults to G1 with the deviation from the limit surface reported in the `ErrorBound`. G2 is an explicit option whose shape change is also reported. *Why:* manufacturing and STEP exchange need NURBS, and the conversion must state what it changed. *Rejected:* G2 by default (silently changes shape); keeping SubD only (no AP242 path; MFG needs exact surfaces). Mixed-representation booleans let a SubD body join a B-rep part directly while the design is in progress; release checks require conversion when the target process demands B-rep.

Pixar's OpenSubdiv evaluates limit surfaces that match RenderMan "to numerical precision" and serves as the reference for Anvil's evaluator in oracle MEC-O-SF-3 (reference only; it is not linked). Failure behavior: `NonManifoldCage { edges }` on invalid cage edits; `ConversionDeviation { max }` when `to_nurbs` exceeds a requested tolerance. Operations: `anvil::subd_edit`, `anvil::subd_limit`, `anvil::subd_to_brep`, `anvil::boolean`.

### Reverse engineering from scans

```
let scan  = import_mesh("housing_scan.3mf")                     // Body (Mesh)
let clean = scan |> denoise(sigma: 0.02mm) |> fill_holes(max: 2mm)
let fit   = scan_to_cad(clean, intent: [Intent::Orthogonal, Intent::Coaxial],
                        primitives: all, freeform: Freeform::Nurbs(tol: 0.05mm))
fit.body                                 // BRep Body
fit.deviation                            // Field<Body, Length> against the scan
```

The pipeline:

1. Registration of multiple scans: point-to-plane ICP with a robust loss (Huber or Cauchy, as in Ceres' loss functions), solved on the shared nonlinear least-squares core.
2. Segmentation into regions: curvature-based region growing natively; an optional learned segmenter as a Wasm component with fixed weights.
3. Primitive fitting: planes, cylinders, cones, spheres and tori by deterministic RANSAC (hash-seeded sampling) followed by robust least squares.
4. Design-intent snapping: detected near-relations (orthogonal, coaxial, equal radius, symmetric) become constraints in the shared solver; each snapped relation is written to source and can be removed.
5. Freeform fitting: NURBS fitting with fairing for regions no primitive explains.
6. Topology reconstruction: adjacent fitted surfaces are extended and intersected to form edges and corners, then sewn into a solid.

Point2CAD (CVPR 2024) combines analytic primitives with an implicit neural representation for freeform surfaces and reports a new state of the art on the ABC benchmark. Crucible uses the same analytic-first structure. Freeform regions end as NURBS so the result is a manufacturable B-rep.

Feature-based reverse engineering also works: `section(scan, plane)` returns mesh section polylines that sketches can trace with `fit` constraints. Failure behavior: `FitRejected { region, rms }` when no model fits within tolerance; `TopologyGap { edges }` when fitted surfaces do not close. Oracle MEC-O-SF-4 builds synthetic scans from ABC models with known noise and compares recovered primitive types, parameters and Chamfer distance.

Phase 4. Operations: `anvil::icp`, `anvil::fit_primitive`, `anvil::fit_nurbs`, `anvil::segment_mesh`, `anvil::intersect`, `anvil::sew`.

## Sheet metal

### Model

A sheet metal part is a `SheetBody` record: the folded `Body`, the flat `Body`, a bend table and `SheetParams { thickness, bend_radius, bend_rule, relief: ReliefRules, gap }`. Every sheet metal feature updates both states. This follows Onshape, where "all operations on active sheet metal models are automatically represented as a flat pattern" and the folded, flat and table views update together.

**Decision D-MEC-16:** The flat pattern is maintained by every sheet metal feature, not computed at the end. *Why:* designers see flat-pattern errors at the feature that causes them; a cut drawn in the flat view maps back to the folded state through the same fold map. *Rejected:* an unfold feature at the end of history (errors appear late and far from their cause).

### Bend rules

The neutral fiber lies at distance `K·t` from the inside surface. For bend angle θ, inside radius R and thickness t:

- Bend allowance: `BA = θ · (R + K·t)`.
- Outside setback: `OSSB = (R + t) · tan(θ/2)`.
- Bend deduction: `BD = 2·OSSB − BA`.

`BendRule` is `KFactor(k)`, `Allowance(table)`, `Deduction(table)` or `Table(BendTable)`. Onshape's documented defaults are a K factor of 0.45 for bends and 0.5 for rolled walls; Crucible uses the same values as defaults until a material or tooling table overrides them. A `BendTable` is keyed by material, thickness, inside radius and angle, and it interpolates linearly within its range.

Lookups outside the table fail with `OutsideBendTable { key, range }`; they never extrapolate. Each bend can override the rule, and the bend table shows the source of every value.

### Features

| Feature | Contract | Phase |
| --- | --- | --- |
| `sheet_from(profile, t, …)`, `contour_flange(path, t)` | Base from a closed profile or an open path | 2 |
| `convert_to_sheet(body, bends: Query<Edge>, rips: Query<Edge>)` | Convert a solid; unselected edges become rips, as in Onshape | 2 |
| `flange(edges, length, angle, position, relief)` | Edge flange; length measured inner, outer or tangent; position material-inside, outside or bend-outside | 2 |
| `miter_flange(path, edges)` | Contour along connected edges with mitered corners | 2 |
| `hem(edges, kind: Closed, Open(gap), Teardrop(r), Rolled(r, angle))` | Hems | 2 |
| `jog(line, offset, angle)` | Two bends from one sketch line | 2 |
| `sketched_bend(line, angle, radius)` | Bend along a line | 2 |
| `lofted_bend(a, b, method: Formed or Brake(segments))` | Transition between two profiles; `Brake` approximates with straight bends and states the deviation | 3 |
| `corner(edges, relief)` | Close corners and corner reliefs: square-sized, rectangle-scaled, round-sized, round-scaled, closed, simple | 2 |
| `bend_relief(kind)` | Rectangle-scaled, obround-scaled, tear | 2 |
| `in_flat { … }` | Features drawn on the flat state, mapped through the fold map | 2 |
| `form(tool, at, orient)` | Forming tools: louver, lance, dimple, bead, emboss, extruded hole, card guide, bridge; each is an Ingot feature with a flat footprint and an optional forming die body | 2 |
| `tab_slot(a, b, …)` | Tabs and slots between sheet parts for welded assemblies | 3 |
| `make_joint`, `make_rip` | Convert between bend and rip, as Onshape's joint tools do | 2 |

### Flat pattern and handoff

`flat(sheet) -> FlatPattern { outline: Body, bends: [BendLine], forms: [FormMark], grain: Option<Direction>, material, thickness }`. A `BendLine` records direction (up or down), angle, inside radius, rule and developed length. Forming tools appear as footprints with tool ids, because their stretched regions are not developable.

A `FlatPattern` is the input to MFG nesting and press-brake planning. MFG owns bend sequencing and tooling; MEC exposes `flange_min(material, t, tooling)` and related queries from MFG data so design checks can use them.

### Sheet metal checks

| Check | Rule source | Severity |
| --- | --- | --- |
| Minimum inside radius per material and thickness | `Material` record | Error |
| Minimum flange length per die opening | MFG tooling data | Error |
| Hole, slot or edge too close to a bend | Default `2·t + R`, overridable | Warning |
| Missing bend or corner relief | Geometry | Error |
| Flat pattern self-overlap | `anvil::boolean` on the flat outline | Error |
| Bend line across grain for anisotropic material | `Material` and grain direction | Warning |
| Forming tool too close to a bend | Tool record | Warning |

Failure behavior for features: `FlangeCollides { faces }`, `UnfoldFailed { bend, reason }`, `NotDevelopable { faces }` when a converted body has doubly curved regions. Oracles: MEC-O-SM-1 compares developed lengths with the formulas above for a sweep of angles, radii and K values; MEC-O-SM-2 refolds every flat pattern and compares it with the folded body; MEC-O-SM-3 runs the checks on seeded defects in golden product 4's guards.

Phase 2. Operations: `anvil::unfold`, `anvil::fold`, `anvil::offset_faces`, `anvil::boolean`, `anvil::extrude`, `anvil::sweep`.

## Weldments and structural frames

```
use std::mech::weld::{member, trim, gusset, end_cap, weld, cut_list}
use std::standards::{en10365, aisc}

pub feature base_frame() -> Part {
    let sk  = sketch3d() { … }                              // skeleton lines
    let m   = member(sk.edges(role: any), profile: en10365::section("HEA 120"), anchor: Anchor::Centroid)
    let t   = m |> trim(corners: Corner::Miter, gap: 1mm)
    let g   = gusset(t.joints(kind: Tee), size: 60mm, t: 6mm, chamfer: 10mm)
    let c   = end_cap(t.open_ends(), t: 5mm, inset: 2mm)
    let w   = weld(t.joints(any), Weld::fillet(a: 4mm, all_around: true))
    part(t + g + c, name: "Base frame").welds(w)
}
```

| Capability | Contract | Failure behavior | Phase |
| --- | --- | --- | --- |
| Structural members | Sweep a profile along each skeleton segment; anchor, rotation and mirror per member | `ProfileNotFound { designation, near }` | 2 |
| Profile catalogs | EN 10365 hot-rolled sections and EN 10210 and EN 10219 hollow sections [unverified editions]; AISC Shapes Database v16.0, which covers the 16th Edition Steel Construction Manual in US and metric units | Pinned data packages | 2 |
| Corner trims | Miter, butt (either member), coped; trim to member or face, planar or body cut; weld gap | `TrimAmbiguous { joint }` with options | 2 |
| Gussets, end caps, base plates | Parametric plates at recognized joints | `NoRoom { joint }` | 2 |
| Weld beads | `Weld` records with type (fillet, groove, plug, slot, spot, seam), size, length, pitch, all-around, field weld, process, contour and finish; `Repr::Cosmetic` by default, `Simplified` bead bodies for mass and interference | `WeldPathOpen`, `SizeExceedsThroat` | 2 |
| Weld symbols | Drawn per AWS A2.4:2020 or ISO 2553:2019 by the drawing standard; ISO 2553 offers system A (dual reference line) and system B (single reference line) | Symbol fields missing for the chosen standard are errors | 2 |
| Cut list | Groups identical bodies by profile, length, end angles and features; reports mass, quantity, stock length | Mixed materials in one group is an error | 2 |

Weld records carry semantics to MFG (weld paths and sequence) and to Flux (weld fatigue checks); the bead geometry is never needed for either. Oracles: MEC-O-WD-1 compares member section properties computed from geometry (area, second moments) with the pinned catalog values within 0.5% (target), which checks root radii and tapers; MEC-O-WD-2 checks cut-list lengths and end angles of mitered frames against closed forms; MEC-O-WD-3 parses rendered symbols back into records (round trip). Operations: `anvil::sweep`, `anvil::split`, `anvil::boolean`, `anvil::mass_properties`.

## Composites design

A composite Part is a tool surface plus a laminate definition. The laminate is data; the solid is derived from it.

```
use std::mech::composite::{laminate, ply, zone, rosette, drape}

let r   = rosette(origin: skin.csys("root"), zero: x, method: Rosette::Translation)
let lam = laminate(tool: skin.faces(role: outer_mold_line), rosette: r, plies: [
    ply("P1", carbon_t700_twill, 0deg,  boundary: full),
    ply("P2", carbon_t700_ud,    45deg, boundary: zone_a),
    ply("P3", carbon_t700_ud,   -45deg, boundary: zone_a, drop_off: 3mm),
    ply("P4", carbon_t700_twill, 0deg,  boundary: full),
], symmetric: true, core: some(core(foam_pmi, 8mm, chamfer: 20deg, region: zone_b)))
let d   = drape(lam, method: Drape::Kinematic { seed: p, step: 2mm })
```

| Capability | Contract | Phase |
| --- | --- | --- |
| Plies and sequences | `Ply { material, angle, boundary, step, splice, dart }`; sequence with symmetry and balance checks | 4 |
| Zones | Zone-based laminates with stacking rules; plies generated from zones and transition rules (ramp ratio, drop-off order) | 4 |
| Rosettes | Translation, rotation (radial), cylindrical and user-defined `Field<Face, Direction>` | 4 |
| Cores | Honeycomb and foam with chamfers and splices | 4 |
| Drape | Kinematic (fishnet) draping per ply; fiber directions and shear angles as Fields | 4 |
| Darts and splices | Cuts that relieve shear; recomputed drape | 4 |
| Flat patterns | Flattened ply outlines from drape; handoff to MFG cutting and nesting | 4 |
| Solid generation | Laminate to `Body` by offsetting the tool surface by cumulative ply thickness, with drop-offs | 4 |
| Ply book | Drawing set with per-ply views, sequence tables and laser-projector data | 4 |
| Laminate properties | Per-zone ABD matrices from classical laminate theory, exported as `Material` fields for Flux shells | 4 |

Kinematic draping follows the published method that Creo documents: drape points are warp-weft crossover points on the tool surface, fibers are inextensible so the step length is constant, a seed point and two fixed fibers make the solution unique, and each quadrant drapes independently. Crucible's kinematic drape runs in Anvil as `anvil::drape_kinematic`, deterministic by quadrant order. A mechanics-based drape (finite element forming simulation) is a Flux model with its own validity envelope.

**Decision D-MEC-17:** Kinematic draping is the default for design, labelled as a geometric approximation that ignores material mechanics. Ply checks flag shear above the material's locking angle, stored in the `Material` record. *Why:* kinematic draping is fast enough for interactive design and is the method Creo documents for composite design; forming simulation needs material models that many users do not have. *Rejected:* forming simulation by default (slow, needs calibrated material data).

Failure behavior: `ShearLimitExceeded { ply, region, max }` with "add dart" and "change seed" as fixes; `DrapeGap { ply }` when the fishnet cannot cover the boundary. Exchange: plies, sequences and rosettes go to STEP AP242 composite constructs; the CAx-IF composites recommended practice is the target [unverified title and version]. Oracles: MEC-O-CP-1 drapes onto a hemisphere and a cylinder with known analytic shear distributions; MEC-O-CP-2 checks ABD matrices against hand calculations.

Phase 4, ahead of golden product 6 (drone). Operations: `anvil::drape_kinematic`, `anvil::offset_faces`, `anvil::parameterize`, `anvil::boolean`.

## Molded and cast part design

| Capability | Contract | Phase |
| --- | --- | --- |
| Draft analysis | `draft_angle(body, pull) -> Field<Face, Angle>` with positive, negative, vertical and insufficient classes | 3 |
| Parting line | `parting_line(body, pull)` from silhouette edges; alternatives ranked by undercut area and line complexity | 3 |
| Parting surface | `parting_surface(line, method: Extend, Ruled or Sweep)` | 3 |
| Shut-offs | `shutoff(loops, method)` patches through-openings | 3 |
| Core and cavity | `split_mold(body, shrink: Scale, parting, block)` returns core, cavity and side-action bodies | 3 |
| Undercuts and side actions | Faces not reachable along the pull; candidate lifter and slide directions | 3 |
| Ribs, bosses, snap fits, gussets | Parametric features with ratio rules to the nominal wall | 3 |
| Wall thickness | `thickness(body, method) -> Field<Body, Length>` | 3 |
| Shrinkage | Anisotropic scale by material grade, or warpage compensation by `deform(field)` from a Flux result | 3 |
| Cast parts | Machining stock, cores for internal passages, draft and minimum section per casting process | 4 |

**Decision D-MEC-18:** Wall thickness is measured by two methods and both are Fields: ray thickness (inward normal ray to the opposite wall) and rolling-ball thickness (diameter of the largest inscribed sphere touching the point), computed on GPU with exact CPU refinement near threshold values. *Why:* a ray from a rib root can miss the thick junction where the rib meets the wall, while the inscribed sphere measures that junction directly; rays are cheaper and match caliper readings on plain walls; the CPU fallback is required by contract section 9. *Rejected:* a single method (each misleads in known cases).

Molding checks (defaults overridable by material and process data from MFG): nominal wall within the material's range, rib thickness at most 0.6 of the adjoining wall [unverified rule of thumb], boss outer diameter about twice the inner, no sharp internal corners, draft at least 0.5 deg on textured faces plus the texture supplier's allowance, and uniform thickness within a ratio. Fill, pack, cooling and warpage simulation belong to Flux; MEC passes the Part, gate candidates and material. Oracles: MEC-O-MD-1 checks thickness Fields on parts with analytic answers (plates, tubes, ribs); MEC-O-MD-2 checks that core plus cavity plus the part equal the mold block (volume identity) and that no core or cavity face has negative draft.

Golden product 5 (molded enclosure) gates this section. Operations: `anvil::silhouette`, `anvil::split`, `anvil::thickness_ray`, `anvil::medial_axis`, `anvil::boolean`, `anvil::fill_surface`.

## Routing

### Shared model

A `Route` is a 3D path between two ports, a `RouteSpec`, placed fittings and generated segment bodies. Ports are `CoordSys` values with a connection type, so routes attach to equipment through interfaces. Routing reuses the 3D sketch solver: route points are constrained to clearances, supports and orthogonal runs.

```
let r = route(from: pump.port("out"), to: manifold.port("in1"),
              spec: pipe_spec("ASME-B31.3-CS-150", nps: 2in),
              via: [clamp_a.csys("seat")], style: Orthogonal, min_clearance: 25mm)
r.require(r.bends().all(|b| b.radius >= 1.5 * r.od))
```

### Kinds

| Kind | Contract | Standards and data | Phase |
| --- | --- | --- | --- |
| Rigid pipe | Specification-driven: catalog fittings (elbows, tees, reducers, flanges, valves), wall schedules, insulation | ASME B36.10M and B36.19M schedules; EN 10220 [unverified editions]; spec files are data packages | 5 |
| Tube | Bent tube with bend radius, minimum straight length between bends, springback per material | Bend data per material and tooling | 3 |
| Hose | Flexible length with minimum bend radius; shape from minimum bending energy given end coordinate systems | Supplier catalog parts | 3 |
| HVAC duct | Rectangular, round and oval ducts, transitions, dampers | SMACNA references [unverified] | 5 |
| Cable and harness | Wires and cables in bundles, branches, clips, grommets; bend radius and fill ratio | Electrical data from ELX | 3 |

### Harness mechanics

The ELX tab owns connectivity: which pin connects to which. MEC owns the 3D path, bundle diameters and the formboard flattening.

| Capability | Contract | Phase |
| --- | --- | --- |
| Bundle diameter | Packing estimate from wire diameters with a fill factor | 3 |
| Bend radius check | Minimum bend radius as a multiple of bundle diameter, per cable spec | 3 |
| Clips and supports | Max spacing check between supports | 3 |
| Flexible shape | Bundle centerline as an elastic rod (Kirchhoff rod with bending and torsion) between constrained coordinate systems, solved by energy minimization in Flux's rod model | 4 |
| Formboard | `formboard(harness) -> Drawing`: branches flattened at true length with angles adjusted to fit the board | 3 |
| Length report | True 3D lengths plus service loops per wire, to ELX and MFG | 3 |

Failure behavior: `NoRoute { blocked_by }` when automatic routing finds no path within clearance; `BendTooTight { at, radius, min }`; `FittingNotInSpec { size }`. Automatic routing searches a voxel visibility graph with A* and then smooths the path into the spec's bend rules [unverified source for the method].

Oracles: MEC-O-RT-1 compares routed lengths and bend radii on known paths; MEC-O-RT-2 checks fitting selection against spec tables. Operations: `anvil::sweep`, `anvil::distance`, `anvil::solve_constraints`, `anvil::voxelize`.

## Large structures, micro scale and soft goods

The founder's scale requirement runs from MEMS to ships and buildings. The table states what is native, what is interop and in which phase.

| Domain | Native in std | Interop | Phase |
| --- | --- | --- | --- |
| Steel structures (frames, connections) | Weldment members at building scale; bolted connections with plates and fasteners; member Fields from Flux frame analysis | IFC 4.3 (ISO 16739-1:2024) export and import of members, plates, openings and assemblies | 5 |
| Plates and stiffened panels | Sheet bodies with thickness Fields; stiffeners as members on surfaces; cutouts | AP242 | 5 |
| Ship hulls and fairing | Surfacing with fairness checks (curvature monotonicity, rate of change); hydrostatic queries (displacement, centers, waterplane) from Anvil volumes cut by a plane | Offsets tables import | 5 |
| Building structure | Native for structural steel and timber members; not a BIM authoring tool | IFC exchange with BIM tools; IFC 4.3 is the latest official version and IFC 5 is in development | 5 |
| MEMS (layer-based) | `process_stack(layers)` where each layer is deposit, pattern (2D mask), etch (isotropic, anisotropic with angle) or release; the 3D Body is built by layer operations | GDSII and OASIS masks via the ELX tab [unverified] | 6 |
| Soft goods | Pattern pieces from surface panels by conformal flattening (Boundary First Flattening); seam lines with allowances, notches, grain lines and stretch ratios | DXF patterns | 6 |

Boundary First Flattening is a linear conformal method with direct control over boundary length or angle, support for cone singularities, and an amortized cost "about 50x less" than prior boundary-controlled conformal flattening, according to its authors. Soft-goods patterns and the `wrap` feature share it through `anvil::parameterize`. Fabric drape and fit simulation is a Flux shell problem with a stated validity envelope, not geometry.

**Decision D-MEC-19:** Large structures, MEMS and soft goods are phases 5 and 6. They reuse existing MEC mechanisms (members, sheets, surfacing checks, flattening, Field-driven geometry) plus a small number of domain features. *Why:* the founder's scale requirement is met by composition, not by separate products; golden products 1 to 6 do not need these domains. *Rejected:* dedicated workbenches per domain now (they would dilute phases 1 to 4).

Proposed later gates: golden product 7 (phase 5), a bolted steel platform exchanged through IFC 4.3 with a structural check; golden product 8 (phase 6), a MEMS accelerometer layer stack and a sewn bag pattern, each round-tripped and checked.

Oracles for these phases: MEC-O-LS-1 compares displacement, centers of buoyancy and waterplane properties of analytic hull forms (boxes, cylinders, parabolic sections) with closed forms; MEC-O-LS-2 round-trips IFC 4.3 members, plates and openings; MEC-O-LS-3 checks that flattened pattern seams match their 3D seam lengths within the declared stretch. Operations: those of weldments, sheet metal and surfacing, plus `anvil::section_body` and `anvil::mass_properties` for hydrostatics, `anvil::parameterize` for flattening, and `anvil::extrude`, `anvil::boolean` and `anvil::offset_faces` for MEMS layers.

Out of reach, stated plainly: Crucible does not replace naval architecture suites for stability rules and class approval, BIM authoring for architecture and building services, or process simulators (TCAD) for MEMS fabrication. It exchanges with them through open formats.

## Tolerancing

### Specification model

Size and dimension tolerances are `Tol<T>` values from the contract. ISO 286 fit codes produce them: `fit(10mm, H7)` returns a `Tol<Length>` with the tabulated limits. Geometric tolerances are typed properties on entities:

```
pub record GeometricTolerance {
    characteristic: Characteristic,
    zone: Zone,                       // width: Length; shape: Diameter, Sphere, Planes, Boundary
    modifiers: [Modifier],            // material condition, projected, free state, dynamic profile, …
    datums: Option<DatumSystem>,
    target: Query<ShapeAspect>,       // a face set, a feature of size, or a pattern
}
pub record Datum { label: String, aspect: Query<ShapeAspect>, targets: [DatumTarget] = [] }
pub record DatumSystem { primary: DatumRef, secondary: Option<DatumRef>, tertiary: Option<DatumRef>,
                         constrained: Option<DofSet> = none }   // customized datum reference frame
```

```
let a = datum("A", plate.face(role: start_cap))
let b = datum("B", plate.face(role: side(e_left)))
let c = datum("C", plate.face(role: side(e_bottom)))
let holes = plate.aspects(kind: Hole, created_by: mount_holes)
plate.tolerance(holes, size: fit(8mm, H8))
     .tolerance(holes, position(dia(0.1mm), mmc, datums: [a, b(mmb), c]))
     .tolerance(a.aspect, flatness(0.02mm))
     .tolerance(plate, general: iso22081(profile: 0.2mm, datums: [a, b, c]))
```

`Characteristic` covers straightness, flatness, circularity, cylindricity, line and surface profile, angularity, perpendicularity, parallelism, position, circular and total runout, and, in the ISO dialect only, concentricity, coaxiality and symmetry. ASME Y14.5-2018 deleted concentricity and symmetry and added the dynamic profile modifier, which controls form but not size.

### Two dialects, one model

**Decision D-MEC-20:** GD&T has one semantic model with two dialects: ASME (Y14.5-2018, reaffirmed in 2024 and on stabilized maintenance) and ISO GPS (ISO 1101:2017, ISO 5459:2024 for datums, ISO 14405-1:2025 for linear sizes, ISO 8015:2011 for fundamentals, ISO 22081:2021 for general specifications, which replaces ISO 2768-2). Each dialect is a validator and a renderer. A design declares its dialect explicitly; there is no default by locale. Translation between dialects produces a Proposal that flags every non-equivalent control. *Why:* the dialects differ in meaning, not just symbols; for example, ASME applies the envelope principle by default and ISO applies independency [unverified], and ASME no longer has concentricity. A neutral model with explicit dialect rules keeps meaning visible, and both dialects map to AP242 semantic PMI. *Rejected:* two separate models (every control written twice); silent conversion (parts made to the wrong requirement).

Each dialect validates every control: modifiers legal for the characteristic, material conditions only on aspects of kind `OfSize` (the standards' "features of size"), datum references compatible with the characteristic, deleted symbols rejected. A rejected control returns `InvalidControl { rule, clause }` with a fix such as "use position, profile or runout instead of concentricity".

### Completeness

**Decision D-MEC-21:** Specification completeness is a degree-of-freedom analysis, computed by the shared `anvil::analyze_constraints` operation. Each toleranced shape aspect gets six small-displacement unknowns relative to the datum reference frame, minus the motions under which its surface class is invariant (a plane is invariant under in-plane translations and rotation about its normal; a cylinder under translation along and rotation about its axis) [unverified source for the invariance classes]. Each tolerance constrains some of those unknowns. Free unknowns are under-specified directions, shown as arrows like sketch degrees of freedom. *Why:* one diagnosis model across sketches, assemblies and tolerancing; under-specified directions are found automatically instead of by drawing review. *Rejected:* rule lists per aspect type (incomplete, no geometric basis).

Faces covered by an ISO 22081 general specification or an ASME general profile note count as controlled. The report also flags redundant datum references and over-specification (two controls bounding the same unknown with conflicting values).

### Stack-up and variation analysis

| Method | Contract | Use | Phase |
| --- | --- | --- | --- |
| Worst case | Interval sum over a contributor chain with signs | Safety-critical fits | 1 |
| RSS | Root-sum-square of contributor standard deviations | Quick statistical estimate | 1 |
| Monte Carlo (1D) | Quasi-Monte Carlo over contributor distributions | Non-normal or bonus-tolerance contributors | 1 |
| 3D linear (Jacobian) | Sensitivities of measurements to every toleranced aspect's small displacements at nominal | Contribution ranking, fast iteration | 2 |
| 3D nonlinear sampling | Per sample: perturb toleranced aspects within their zones, assemble with the shared solver (contact, float in clearance holes, assembly order), measure | Sign-off | 2 |
| Skin model shapes | Form deviations as normal-displacement Fields on surface meshes, sampled from constrained random fields | Form-critical contacts, sealing faces | 4 |
| Tolerance allocation | Choose zone widths to minimize cost at a target yield, using sensitivities and MFG cost models | Cost reduction | 3 |

```
let gap = measure(asm, distance(cover.face("lip"), housing.face("seat")), along: z)
let v = variation(asm, measures: [gap], samples: 20_000, method: Variation::Nonlinear)
v.require(v.yield(gap, 0.1mm..0.6mm) >= 0.9973)
v.contributors(gap)                      // ranked tolerances with percent contribution
```

**Decision D-MEC-22:** 3D variation sampling uses scrambled Sobol quasi-Monte Carlo with the scramble seed derived from the design's `EntityId`s, so results are deterministic and reproducible. Results report the estimate with a confidence interval from repeated independent scrambles. Linear sensitivity analysis runs first and orders contributors. *Why:* determinism is a contract principle; quasi-Monte Carlo converges faster than pseudo-random sampling for smooth measurements [unverified]; one assembly solver gives float and contact behavior consistent with the assembly model. *Rejected:* Jacobian-only analysis (misses float, contact switching and bonus tolerance); unseeded Monte Carlo (non-deterministic). Skin model shapes, proposed by Anwer, Schleich, Mathieu and Wartzack (CIRP Annals, 2014), address form deviations that classical computer-aided tolerancing handles poorly; Crucible adds them in phase 4 for the joints that need them.

Contributor distributions default to normal with the zone limits at ±3σ. A distribution can come from measured process capability in an MFG process profile. `Tol<T>` arithmetic in plain Ingot expressions is worst case; statistical combination is always an explicit call (see interfaces).

### Tolerancing contract

| Capability | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- |
| GD&T model and dialect validation | `InvalidControl { rule, clause }` | MEC-O-TL-1 | 1 |
| Datum systems, targets, customized frames | `DatumUnderdefined { dof }` | MEC-O-TL-1 | 1 |
| Completeness analysis | Free directions listed per shape aspect | MEC-O-TL-2 | 2 |
| 1D stacks | `ChainOpen` when contributors do not close a loop | MEC-O-TL-3 | 1 |
| 3D variation | `AssemblyFailed { sample }` counted and reported, never dropped silently | MEC-O-TL-4 | 2 |
| Skin model shapes | `ContactUnresolved { sample }` | MEC-O-TL-5 | 4 |

Operations: `anvil::analyze_constraints`, `anvil::solve_constraints`, `anvil::distance`, `anvil::sample_surface`.

## Drawings and model-based definition

### One annotation model

**Decision D-MEC-23:** Semantic PMI lives on the model. Drawings and 3D saved views are two presentations of the same annotation items. Drawing-only annotations are allowed, marked non-semantic and excluded from semantic export. *Why:* one source of truth; ISO 16792:2021 supports both a model-only data set and a model plus a digital 2D drawing, and ASME Y14.41 covers annotated models with or without a drawing sheet. *Rejected:* drawing-first annotation (not machine-readable); separate MBD annotations (two truths that drift).

### Drawings

Drawings are Ingot programs, so they diff, merge and review like parts.

```
use std::mech::drawing::{drawing, sheet, view, section, detail, bom_table, Standard}

pub feature bracket_drawing() -> Drawing {
    let p = bracket()
    drawing(standard: Standard::iso(), title: "Bracket") {
        sheet(format: A3, scale: 1:1) {
            let front = view(p, orient: front, at: (120mm, 150mm))
            let top   = projected(front, dir: up)
            let aa    = section(front, cut: p.csys("mid").plane(yz), label: "A")
            detail(aa, around: p.faces(created_by: "slot"), scale: 4:1)
            show_pmi(p, in: [front, top, aa])
            bom_table(p, at: top_right)
        }
    }
}
```

| Capability | Contract | Phase |
| --- | --- | --- |
| Sheets and title blocks | Formats per standard; title blocks are Ingot templates whose fields read item, revision and approvals from `repo` | 1 |
| Base, projected, auxiliary views | First- or third-angle projection from the drafting standard | 1 |
| Sections | Full, half, offset, aligned, removed, revolved, broken-out; hatching from the `Material` record | 1 (full, half), 2 |
| Detail, broken, crop views | Scale and boundary per view | 1 (detail), 2 |
| Exploded, flat-pattern and ply views | From explode data, `FlatPattern` and laminates | 2, 4 for plies |
| Hidden line removal | Exact projection from `anvil::project_hlr`; lines and circles stay exact; freeform edges approximated with `ErrorBound` | 1 |
| Dimensions | Linear, aligned, angular, radial, diameter, ordinate, baseline, chain, arc length, chamfer; attached by `Query` | 1 |
| Generated callouts | Holes and threads from `HoleSpec` and `ThreadSpec`; welds from `Weld`; GD&T from the semantic model | 1, 2 for welds |
| Other symbols | Surface texture (ISO 21920-1 and ASME Y14.36 [unverified editions]), notes with live model values, balloons tied to BOM items, centerlines, center marks | 1 |
| Tables | BOM (a `repo` BOM query, EBOM or MBOM view), holes, bends, cut list, plies, revisions (from `repo` releases and change orders), general tolerances | 1 (BOM, holes), 2 |
| Drafting standards | Data packages: ISO (ISO 128 series and related) and ASME (Y14 series) with fonts, arrowheads, line weights and projection angle [unverified editions except Y14.5-2018] | 1 |
| Output | PDF, SVG and DXF from pure Rust writers; DWG only through a licensed translator plugin | 1 |

Associativity: every drawing item references model entities by `Query`. After a model change, an item that cannot re-resolve becomes a dangling item with a `ResolveError`; it is never re-attached to another entity. A release check forbids dangling items.

View and annotation positions are written to source as offsets from anchors when moved in the editor. Operations: `anvil::project_hlr`, `anvil::section_body`, `anvil::silhouette`, `anvil::tessellate`.

**Decision D-MEC-24:** Release drawings use exact hidden line removal; interactive editing uses a GPU visibility preview that is replaced when the exact result arrives. *Why:* drawings are contractual documents and must match the model exactly; the preview keeps editing responsive. *Rejected:* tessellation-based HLR for release (chordal error appears on the sheet).

### Automated drawing generation

`auto_drawing(part, template, rules)` writes an editable drawing program:

1. Select views: the fewest principal views that show every toleranced aspect, sections through aspects hidden in all principal views, details for aspects below a size threshold at sheet scale.
2. Place each semantic PMI item in the view where its target appears in true shape or as an edge.
3. Dimension untoleranced geometry from the datum system, using baseline or chain style per rules.
4. Lay out views and annotations by deterministic optimization that minimizes overlaps and leader crossings.
5. Check: every PMI item appears exactly once and every face is dimensioned or covered by a general specification.

Failure behavior: `UnplacedItems { items }` with the reason (no view shows the target). Oracle: MEC-O-DR-5.

Operations: those of drawings, plus the `mech-drawing-layout` Wasm component. Phase 3.

### Model-based definition

| Capability | Contract | Phase |
| --- | --- | --- |
| Saved model views | `model_view(name, camera, annotations, section, repr)`; a default view is required | 1 |
| AP242 semantic PMI export | Semantic representation linked to B-rep faces through `shape_aspect` and `geometric_item_specific_usage`, plus polyline or tessellated presentation, saved views and validation properties, per CAx-IF Recommended Practices for PMI v4.1 (June 2024) | 1 |
| AP242 semantic PMI import | Into the GD&T model; unmappable items kept as presentation with warnings | 2 |
| Non-B-rep bodies | Mesh, implicit and SubD bodies export presentation-only PMI, flagged; v4.1 places semantic PMI on tessellated geometry out of scope | 1 |
| Data set completeness | Checks for a model coordinate system, data set identification from the `repo` release, and required annotations per ASME Y14.41 (current edition listed by ASME as 2026 [unverified]) or ISO 16792:2021, which ISO lists as under revision | 2 |
| Inspection handoff | PMI to QIF 3.0 for inspection planning, through the MFG tab | 2 |

The AP242 reader and writer belong to the interop layer in `io/` (contract section 7). MEC supplies the semantic model and its mapping table, and owns the PMI oracles.

### Drawing and MBD oracles

- MEC-O-DR-1: exact HLR compared with high-resolution ray-cast visibility on ABC models.
- MEC-O-DR-2: associativity under edits; every item re-resolves or reports a `ResolveError`.
- MEC-O-DR-3: NIST MBE PMI test cases (CTC 01 to 05, FTC 06 to 11, the 2023 simplified cases and the 2024 hole test cases) rebuilt natively, exported to AP242 and compared item by item with NIST's STEP files. NIST permits use without restriction.
- MEC-O-DR-4: drafting-standard rule checks (line types, text heights, symbol forms) on held-out golden drawings.
- MEC-O-DR-5: automatic drawings show every PMI item exactly once.

Targets: drawing update after an edit to a 200-feature part in under 1 s; exact HLR of a 1,000-part assembly view in under 30 s.

## Design checks

Design checks are `require` predicates packaged as check libraries. Each result is a `Field` of severities painted on the geometry, plus typed fixes. Ownership follows the MFG tab's split: MFG owns process DFM, DFA and DfAM checks parameterized by machine, printer and shop profiles; MEC owns the checks for its own design domains and for standards compliance.

| Library | Owner | Example rules | Phase |
| --- | --- | --- | --- |
| `check::sheet` | MEC | The sheet metal checks listed under sheet metal, with tooling minimums read from MFG profiles | 2 |
| `check::weld` | MEC | Weld access, symbol completeness for the chosen standard, profile availability | 2 |
| `check::fastening` | MEC | Thread engagement, clearance class, preload range present, tool access (wrench swing as a swept body), hole alignment across parts, fasteners missing from hole chains | 2 |
| `check::assembly` | MEC | Clearance to moving parts over a motion study, interference classes, interface compatibility | 2 |
| `check::molding_design` | MEC | Draft, wall thickness, rib and boss ratios, undercuts, using material data | 3 |
| `check::standards` | MEC | Thread series and preferred sizes, GD&T dialect validity and completeness, drawing completeness, standard part designations | 1 |
| Machining, additive, casting and process-specific rules | MFG | Tool reach and corner radii, overhangs and powder escape, minimum sections, all against a named process profile | MFG phases |

MEC's design-domain checks and MFG's process checks share one result type, so the UI and agents treat them alike. A part can pass MEC's molding design check and still fail MFG's check for a specific press and mold steel.

**Decision D-MEC-25:** Design checks return graded Fields with numeric margins, not pass or fail flags. *Why:* agents optimize against margins, and people see where a rule nearly fails. *Rejected:* boolean rule results (no gradient for optimization, no early warning).

Operations: those of the analyses the rules read, mainly `anvil::thickness_ray`, `anvil::medial_axis`, `anvil::distance`, `anvil::curvature`, and `anvil::sweep` for tool-access bodies.

Oracle MEC-O-CK-1 seeds known defects into golden products 3 to 5 and requires every one to be found, with no false positives on the clean versions. Oracle MEC-O-CK-2 checks that every rule's fix, once applied, clears the finding.

## Human factors

```
use std::mech::human::{manikin, population, reach, vision}
let crew = population("example_survey", percentiles: [5, 50, 95], sex: [F, M])  // licensed data package
let m = manikin(crew.p5_female, posture: seated(seat.csys("h_point")))
cockpit.require(reach(m, hand: right, target: panel.port("switch_3")).within)
cockpit.require(vision(m, target: display.face("screen")).unobstructed)
```

| Capability | Contract | Phase |
| --- | --- | --- |
| Anthropometry | Body dimensions defined per ISO 7250-1:2017; population datasets are licensed data packages | 5 |
| Manikins | Kinematic chains with joint limits, scaled to a population percentile or a measured individual | 5 |
| Posture prediction | Inverse kinematics on the shared solver with a comfort cost and joint-limit inequalities | 5 |
| Reach and clearance | Reach envelopes as Bodies; hand and tool access checks | 5 |
| Vision | View cones, obscuration and legibility distance | 5 |
| Posture scores | Ergonomic scoring methods such as RULA [unverified] as check libraries | 5 |

Validity envelope: geometric reach, fit and vision only. Strength, fatigue and musculoskeletal loading need Flux biomechanics models with their own validity envelopes. Failure behavior: `PostureInfeasible { target, limit }` names the joint limit that blocks a reach; `DatasetMissing { population }` when the licensed package is absent.

Oracle MEC-O-HF-1 compares manikin segment lengths with the source dataset and checks reach envelopes against analytic chains. Operations: `anvil::solve_constraints` for posture, `anvil::sweep` and `anvil::boolean` for reach envelopes, `anvil::ray_cast` for obscuration.

## State of the art

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Feature language | Standard features written in the user-facing language, regenerated deterministically: Onshape defines its standard features in FeatureScript and publishes their source | Onshape FeatureScript | All `std::mech` features in Ingot with typed roles and units (D-MEC-1) | Golden products built only from std; rebuild timing MEC-O-PF-14 against the contract's 2 s target |
| Sketch constraint solving | Structural decomposition before numerical solving, then Newton-type or optimization solving (Zou et al. review, 2022); least-squares behavior for under-constrained drags (SolveSpace) | Siemens D-Cubed 2D DCM, which Siemens calls "the most widely adopted 2D geometric constraint solver"; FreeCAD planegcs (DogLeg and LM on Eigen sparse QR) | D-M decomposition, LM blocks on faer, Newton homotopy from seeds, minimum-displacement under-determined parts (D-MEC-3 to D-MEC-5) | SketchGraphs (15 million Onshape sketches) replay: target 99.5% of fully supported sketches re-solved to recorded geometry on the recorded branch; 2,000-entity drag step under 8 ms native (target) |
| Constraint diagnosis | Witness configuration method for structural and non-structural dependencies, with Zou and Feng's corrections for minimality | D-Cubed diagnostics (details not public) | Witness rank, deletion-filter minimal conflicts, exact rational certification up to 200 unknowns | Synthetic suite with known ranks: target 100% agreement with exact rank on certified blocks |
| Assembly solving and kinematics | One constraint system over SE(3) cluster unknowns on manifolds (Ceres manifold pattern); continuation for motion | Siemens D-Cubed 3D DCM ("most widely adopted 3D geometric constraint solver"); Onshape mates on mate connectors | Shared solver (D-MEC-11); kinematics by continuation; dynamics in Flux (D-MEC-12) | Mechanism suite mobility counts; closed-form linkages; target 1,000-mate solve under 100 ms |
| Blends | Rolling-ball constant and variable radius with vertex setbacks; G2 and conic profiles | Parasolid, used by Plasticity, which advertises fillets across complex geometry | Anvil blend program with opt-in implicit fallback (D-MEC-2) | Fixed sample of edge chains from ABC: success rate and rolling-ball error; target 97% success at phase 2 |
| Direct editing | Synchronous editing: history-free edits that keep related geometry consistent, including on imported models | Siemens synchronous technology in Solid Edge and NX | Solver-based face motions with live rules written to source (D-MEC-9) | Relation recognition precision and recall on ABC models; target 95% success on a held-out set of seeded edits |
| Sheet metal | Flat pattern maintained by every feature; per-bend rules in a table | Onshape sheet metal (simultaneous folded, flat and table views) | Same model with no extrapolation outside bend tables (D-MEC-16) | Developed lengths equal closed forms to 1e-9 relative (target); refold deviation under the entity tolerance |
| Surface continuity and Class-A | G2 and G3 analysis, zebra and highlight lines, control-net quality | CATIA and Alias-class tools [unverified]; Plasticity Studio xNURBS for G0 to G2 transitions | Analysis Fields plus Class-A check library (D-MEC-14) | Analytic surface pairs with known continuity orders; zero misclassifications (target) |
| SubD to NURBS | G2 conversion in regular regions with a choice at extraordinary vertices and quad-grid packing | Rhino 8 `ToNURBS`; OpenSubdiv limit evaluation | Exact regular regions, G1 default at extraordinary vertices with reported deviation (D-MEC-15) | Limit evaluation agrees with OpenSubdiv reference outputs to 1e-9 relative (target) |
| Scan to CAD | Hybrid analytic and neural fitting with topology reconstruction (Point2CAD, CVPR 2024) | Point2CAD on ABC | Analytic-first pipeline with intent snapping and NURBS freeform | Synthetic ABC scans: target at least Point2CAD's reported accuracy on its protocol |
| Draping | Kinematic fishnet draping from a seed and two fixed fibers | Creo Composite Design draping | Deterministic kinematic drape; forming simulation in Flux (D-MEC-17) | Hemisphere and cylinder analytic shear; target maximum shear-angle error under 0.5 deg |
| Flattening | Boundary First Flattening: linear, conformal, boundary control, cone singularities | BFF reference implementation | `anvil::parameterize` with BFF | Angle distortion and time on a fixed mesh set; target within 10% of the reference |
| Mate inference | Learned joint prediction on B-rep graphs (JoinABLe, 79.53% against reported human 80%) | JoinABLe | Optional ranker in a Wasm component | Fusion 360 Gallery joint test split; target 80% top-1 |
| 3D tolerance analysis | Nonlinear sampling with assembly behavior; skin model shapes for form deviation (Anwer et al. 2014; compared by Schleich and Wartzack 2016) | Commercial 3D variation tools such as 3DCS and Siemens VSA [unverified] | Linear sensitivities, then scrambled Sobol sampling through the assembly solver (D-MEC-22) | Literature benchmark assemblies with published results; target 20,000 samples of a 50-part stack in under 60 s |
| Semantic PMI exchange | AP242 semantic representation with linked presentation and validation properties (CAx-IF PMI v4.1) | CATIA, NX, Creo and SOLIDWORKS exports tested on NIST cases | Native AP242 PMI from the semantic GD&T model (D-MEC-23) | NIST CTC, FTC, STC and HTC round trip: target 100% of semantic items |
| Hidden line removal | Exact edge projection with visibility from exact geometry [unverified method attribution] | Drafting in NX and SOLIDWORKS [unverified] | Exact for release, GPU preview while editing (D-MEC-24) | Agreement with dense ray casting on ABC models; target zero visibility disagreements farther than 1 µm from silhouette and intersection edges |
| Wall thickness | Ray and inscribed-sphere thickness | Molding analysis tools in commercial CAD [unverified] | Both as Fields, GPU with exact CPU refinement (D-MEC-18) | Plates, tubes and ribs with analytic thickness; target error under 1% of thickness |
| Gear geometry | ISO 21771-1:2024 geometry with flank modifications | Specialist gear software [unverified] | Spline flanks with error under 0.1 µm (target) plus exact semantics | Flank points against ISO 21771-1 formulas |
| Solver linear algebra | Sparse QR for large blocks, column-pivoted QR and SVD for rank | Eigen, as used by FreeCAD planegcs | faer (MIT, pure Rust dependencies) | Rank agreement with exact arithmetic; target no slower than Eigen on the SketchGraphs set |

Deviation from the state of the art, stated: homotopy continuation finds all solutions but Crucible tracks only the seeds' branch, because the Zou review notes its heavy cost and interactive editing needs one predictable answer. OndselSolver, an open assembly and multibody solver, is LGPL-2.1 and was archived on 1 March 2025, so it serves as a reference only.

## Platform notes

- **Floating point.** Constraint residuals call trigonometric functions. Crucible uses one pinned pure-Rust math library for these on every target instead of the platform `libm`, because system libraries differ in the last bits. The PLT tab owns the choice of library. Fused multiply-add use is fixed per platform class.
- **Parallel solving.** Independent blocks solve in parallel, but results are assembled in topological order with `EntityId` tie-breaks. Thread count never changes results.
- **Browser.** Wasm threads need cross-origin isolation. Without it the solver runs blocks sequentially, and the browser drag target (16 ms for 2,000 entities) assumes a single thread. The 32-bit Wasm address space limits in-browser B-rep loading, so very large assemblies stream levels of detail and evaluate exact geometry on a team server.
- **Fonts.** Sketch text, drawing text and engraving use bundled fonts from pinned packages, never OS font lookup, so glyph outlines are identical everywhere.
- **Design tables.** CSV import never uses the OS locale. Decimals use a period and units come from column headers. A comma-decimal file needs an explicit `table(…, decimal: Comma)`.
- **Output.** PDF, SVG and DXF writers are pure Rust in `io/`. Printing goes through the platform layer in `apps/` shells. Paper sizes are data in drafting standard packages.
- **GPU paths.** Thickness Fields, zebra rendering, HLR preview and broad-phase interference have CPU fallbacks with identical results within a platform class.
- **Standards data offline.** Standards data packages and catalog part geometry are vendored into air-gapped installs with their licenses.
- **Tier 2 devices.** Tablets edit driving dimensions, parameters and mates and view all analysis Fields. Sketch dragging works with touch through the same `api` Edit stream.

## Interfaces with other subsystems

[[DIAGRAM: MEC data flow. Boxes: Skeleton and interfaces → Parts (sketches, part features, sheet metal, weldments, composites, molded parts) → Assembly (mates, fasteners, routes) → three outputs: Flux (joints, mass properties, laminates, contact pairs), MFG (FlatPattern, HoleSpec, ThreadSpec, Weld, plies, core and cavity, PMI), and Drawings and model views → AP242 and QIF in io/. Under all boxes, one bar labelled anvil::solve_constraints and analyze_constraints feeding sketches, mates, live rules, tolerancing completeness, routing and posture.]]

### Consumed

| From | What MEC needs |
| --- | --- |
| Anvil | The operations in the table below, each returning `HistoryRecord`s; per-entity tolerances; `ErrorBound` on every approximation; exact rational rank inside `analyze_constraints` |
| Ingot | `feature`, `record`, `interface`, the differentiable `constraint` subset lowered to the shared kernel IR, `family` and unit-checked `table()`, role syntax in `Query`, `Tol<T>` with fit codes, `require` with severities |
| Kiln | Per-feature read sets, separate caching of tool bodies and booleans, cancellation of superseded drag solves, background exact hidden line removal. Drag previews may warm-start; builds never do |
| Flux | Rigid and flexible multibody dynamics on an `Assembly` with typed joints and a redundancy report, and an elastic rod model (bending and torsion) for harnesses and hoses. Neither appears in the current Flux draft, so this is a request. Also shells with laminate ABD matrices, forming, molding and springback models, and result `Field`s that `deform` consumes |
| `repo` | BOM queries for tables and balloons; item numbers and family rows as BOM lines; release and change-order data for title blocks and revision tables; feature-level merge of sketch constraints and seeds |
| `api` and agents (AGT) | Inspect returns `SolveReport`, `ContinuityReport` and check Fields; Edit applies typed `Fix` values; Compare shows family and derived-part geometry diffs |
| UI (UIX) | Painted Fields, degree-of-freedom arrows, conflict highlighting, `Fix` buttons, drag streams that write seeds on release, a drawing editor that writes view offsets |
| MFG | Process profiles (machine, printer, press brake and shop capability data packages), tooling data (tool radii, drills, dies), material process windows, process cost models for tolerance allocation, process DFM checks |
| ELX | Harness connectivity, board outlines and connector coordinate systems as interfaces, MEMS masks |
| Package registry and parts catalog | Standards data packages with editions and licenses; catalog parts for fasteners, bearings and profiles with supplier records |

| Anvil operation group | Operations | First phase |
| --- | --- | --- |
| Constraints | `solve_constraints`, `analyze_constraints` | 1 |
| Curves | `evaluate_curve`, `closest_point`, `project_curve`, `offset_curve`, `intersect`, `helix`, `approximate_curve` | 1 |
| Solids | `extrude`, `revolve`, `sweep`, `loft`, `boolean`, `split`, `imprint`, `transform`, `make_regions`, `offset_faces`, `offset_body`, `extend_face`, `draft_faces`, `mass_properties`, `distance`, `tessellate`, `ray_cast` | 1 |
| Blends | `blend`, `chamfer`, `implicit_from_brep`, `brep_from_implicit` | 1 |
| Surfaces | `boundary_surface`, `fill_surface`, `blend_surface`, `match_surface`, `approximate_surface`, `sew`, `analyze_continuity`, `curvature`, `isophotes`, `silhouette`, `section_body` | 2 |
| SubD | `subd_edit`, `subd_limit`, `subd_to_brep` | 3 |
| Direct edits | `move_faces`, `replace_face`, `delete_face`, `recognize_aspects`, `recognize_relations` | 2 |
| Sheet and flattening | `unfold`, `fold`, `parameterize`, `drape_kinematic` | 2 |
| Analysis | `thickness_ray`, `medial_axis`, `sample_surface`, `project_hlr`, `shrinkwrap`, `voxelize` | 1 (`project_hlr`), 2, 3 |
| Scans and deformation | `icp`, `fit_primitive`, `fit_nurbs`, `segment_mesh`, `deform` | 3, 4 |

| Wasm component | Purpose | Phase |
| --- | --- | --- |
| `mech-lattice` | Strut and minimal-surface lattice fields | 1 |
| `mech-route-search` | Path search for routes | 3 |
| `mech-drawing-layout` | View and annotation placement | 3 |
| `mech-explode-planner` | Disassembly order and directions | 3 |
| `mech-mate-ranker` | Learned mate suggestions | 3 |
| `mech-scan-segmenter` | Learned point-cloud segmentation | 4 |

Learned Wasm components ship fixed weights and run deterministic CPU inference with a fixed operation order.

### Provided

| To | What MEC provides |
| --- | --- |
| Everyone | `std::mech` packages, the shared types table, check libraries, the constraint vocabulary |
| Flux | Assemblies with typed joints, mass properties with `ErrorBound`, contact candidates, bolt preload intent, laminates, route rods, drivers from motion studies |
| MFG | `FlatPattern`, `HoleSpec`, `ThreadSpec`, `Weld`, ply flat patterns, core and cavity bodies, gear semantics, semantic PMI for QIF |
| ELX | Enclosure interfaces, connector `CoordSys` values, harness 3D lengths and bundle diameters |
| `repo` | Parts with identity, family rows, cut lists, EBOM structure, after-assembly operations for MBOM |
| `io/` | The GD&T semantic model with its AP242 mapping table; weld, hole and composite semantics for AP242 |

## Oracles

All oracles live in the protected `oracles/mech/` directory. Held-out subsets (20% of each generated or replayed set, and every golden-product drawing) are never shown to agents.

| Oracle | What it checks |
| --- | --- |
| MEC-O-SK-1 | SketchGraphs replay in 2D and a synthetic 3D set: re-solve from perturbed seeds, residual under tolerance, recorded branch kept |
| MEC-O-SK-2 | Generated systems with known rank, structural and non-structural dependencies; diagnosis matches exact rational rank |
| MEC-O-SK-3 | Inequality systems with known feasibility |
| MEC-O-SK-4 | Determinism: same source gives bit-identical results within a platform class and agreement within 1e-12 relative across classes (target); 1,000 random dimension edits never change branch without `BranchFlip` |
| MEC-O-SK-5 | Drag latency on fixed sketches at 200 and 2,000 entities |
| MEC-O-SK-6 | Spline and NURBS evaluation, curve length against high-precision quadrature |
| MEC-O-SK-7 | Compiled custom constraints: values and derivatives against a reference interpreter and finite differences |
| MEC-O-PF-1 | Extrude, revolve and rib volumes, areas and face counts against closed forms; roles stable over 100 random parameter edits |
| MEC-O-PF-2 | Sweeps, lofts and helices against analytic surfaces (a circle swept along a helix is a tube); sweep-frame continuity |
| MEC-O-PF-3 | Offsets, shells and thickens: certified minimum distance equals the thickness |
| MEC-O-PF-4 | Holes and threads against standards tables and NIST hole test cases |
| MEC-O-PF-5 | Blends: rolling-ball distance at samples, G1 at contact edges, success rate on the ABC edge sample |
| MEC-O-PF-6 | Draft Fields meet targets on drafted faces |
| MEC-O-PF-7 | Pattern counts, transforms and volume additivity |
| MEC-O-PF-8 | Boolean volume identities on random ABC pairs |
| MEC-O-PF-9 | Direct edits keep declared relations; results match remodeled references |
| MEC-O-PF-10 | Deform and wrap against analytic maps; exact arc length on developable wraps |
| MEC-O-PF-11 | Derived parts rebuilt against pinned and bumped sources |
| MEC-O-PF-12 | Family rows type-check, build and report per row |
| MEC-O-PF-13 | Lattice relative density against analytic values |
| MEC-O-PF-14 | Rebuild timing of golden products after first, middle and last feature edits |
| MEC-O-PF-15 | Gear flank points against ISO 21771-1 formulas; undercut and tip-thickness limits |
| MEC-O-AS-1 to 8 | Listed in the assemblies section |
| MEC-O-SF-1 | Continuity classification on constructed surface pairs with known orders |
| MEC-O-SF-2 | Boundary, network and fill surfaces interpolate boundaries and meet edge targets |
| MEC-O-SF-3 | SubD limit evaluation against stored OpenSubdiv outputs; `to_nurbs` deviation and continuity |
| MEC-O-SF-4 | Scan to CAD on synthetic ABC scans |
| MEC-O-LS-1 to 3 | Listed under large structures, micro scale and soft goods |
| MEC-O-SM-1 to 3, WD-1 to 3, CP-1 to 2, MD-1 to 2, RT-1 to 2 | Listed in their sections |
| MEC-O-TL-1 | Dialect validation against rule suites built from Y14.5-2018 and ISO 1101 examples |
| MEC-O-TL-2 | Completeness analysis on parts with known free directions |
| MEC-O-TL-3 | 1D stacks against hand-computed worst case and RSS |
| MEC-O-TL-4 | 3D variation on benchmark assemblies; deterministic across runs; confidence intervals cover reference values |
| MEC-O-TL-5 | Skin model sampling statistics match the specified random fields |
| MEC-O-DR-1 to 5, CK-1 to 2, HF-1 | Listed in their sections |

## Phasing

| Phase | MEC scope | Gate |
| --- | --- | --- |
| 0 | Solver core (decomposition, LM, homotopy, diagnosis) with determinism tests; role conventions; standards data package format | Determinism suite includes MEC-O-SK-4 |
| 1 | 2D sketches; profile features; ISO metric and unified holes and threads; constant fillets and chamfers; uniform shell; neutral-plane draft; linear, circular and point patterns; mirror; split and combine; derived parts; families; lattices; basic mates and static interference; skeletons; GD&T model and 1D stacks; basic drawings, saved views and AP242 PMI export; standards checks | Golden products 1 and 2 |
| 2 | 3D sketches, NURBS, inequalities, custom constraints; variable and setback blends; direct edits; guided sweeps and lofts; machine elements; all mates, kinematics, flexible subassemblies, interfaces, large-assembly representations, fasteners, exploded views; sheet metal; weldments; completeness analysis and 3D variation; drawing depth and PMI import; curves and analysis Fields | Golden products 3 and 4 |
| 3 | Freeform surfacing, Class-A checks, SubD, G2 and conic blends; molded part design; deform, wrap and emboss; tube, hose and harness routing; automatic drawings and explosions; mate inference; tolerance allocation | Golden product 5 |
| 4 | Composites; scan to CAD; skin model shapes; cast parts; flexible harness shape | Golden product 6 |
| 5 (proposed) | Steel structures and IFC 4.3; plates; hull fairing and hydrostatics; pipe and HVAC routing; human factors | Golden product 7: bolted steel platform round-tripped through IFC with a structural check |
| 6 (proposed) | MEMS layer stacks; soft goods | Golden product 8: MEMS accelerometer stack and sewn bag pattern |

## Open questions

1. Seeds and diff noise. Writing solved seeds back after every drag changes many literals. Should seeds live in a separate layout section that merges by last writer, or stay inline at rounded precision? This needs ING and `repo` agreement.
2. Standards licensing. Can open-source std ship tabulated values from ISO, ASME, DIN and AISC sources, or must they be separate licensed data packages? This needs legal review before phase 1.
3. Release policy for implicit blend fallbacks. Which processes accept a released part with an implicit region? Proposal: MFG process rules decide, and a release check enforces them.
4. Benchmark access. Some kernel and CAD licenses restrict published benchmarks [unverified]. The blend and HLR comparisons may need to use Open CASCADE and exported results only.
5. Dataset terms. SketchGraphs states that the original sketch creators hold copyright, and the Fusion 360 Gallery data has its own license. Can the oracle directory vendor these sets, or must oracles fetch them by content hash?
6. Compliant variation. Should 3D variation include part compliance (sheet metal assemblies) in phase 2 using Flux influence coefficients, or wait for phase 3?
7. Drawing edits. Should editing a driving dimension on a drawing write the model source through its `Query`? It is convenient but makes drawings an editor of geometry.
8. GD&T dialect conversion. Is a proposal-based ASME to ISO translation worth building, given that many controls have no exact equivalent?

## Contract change requests

1. **Add `CoordSys` to the core types.** A `CoordSys` is a `Transform` plus an anchor `Query`, re-resolved on every rebuild. The AGT tab already uses `Frame` for API stream messages, so this draft does not. MEC mates, ELX connectors, MFG work coordinate systems and Flux boundary conditions all need one. Without it, each tab invents its own coordinate system type.
2. **Name the GD&T "feature" without colliding with Feature.** ASME and ISO call a toleranced face set a "feature" or "feature of size", and CAD calls recognized holes and bosses "form features". Proposal: one core type, `ShapeAspect` (after AP242's `shape_aspect`), for any identified portion of a Body's boundary, with a kind such as `OfSize`, `Hole` or `Pattern`. Flux already uses "element" for finite elements and "form" for weak forms, so neither word is free. This draft uses `ShapeAspect` throughout.
3. **State `Tol<T>` arithmetic semantics.** Proposal: plain expressions are worst case, statistical combination is always an explicit call, and each `Tol` value carries an identity so repeated uses stay correlated. Naive interval arithmetic gives `x − x` a nonzero width; affine arithmetic or sensitivities avoid that.
4. **Make Field axes and an Instance domain contract-level.** The Flux tab defines extra Field axes such as `Time` (`Field<Part, Temperature, Time>`); motion studies need the same with an `Instance` domain (`Field<Instance, Transform, Time>`). The contract still says Fields live "over a Body or region"; it should name axes and Instances explicitly.
5. **Feature-level roles in provenance.** Anvil roles describe operations, but designers select by feature roles such as `counterbore_wall`. Proposal: a feature may attach a role alias to an `EntityId` it returns, and Kiln records it with the provenance.

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
