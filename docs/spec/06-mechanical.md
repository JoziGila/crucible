# Mechanical design (MEC)

`std::mech` is the Ingot library for mechanical, industrial and structural design before manufacturing: sketches, part features, assemblies, surfaces, sheet metal, weldments, composites, molded parts, routing, tolerancing, drawings and design checks. Every feature is Ingot orchestrating versioned Anvil operations and a few Wasm components, and every result is a `Body`, `Part`, `Assembly` or `Field`. One constraint solver, one query vocabulary and one semantic tolerancing model serve them all.

## Library structure and shared conventions

### Packages

`std::mech` re-exports the everyday features, so `use std::mech::{sketch, extrude, rib, fillet}` works as in contract section 6. Standards content lives in data packages, so an edition is pinned in `ingot.lock` like any other dependency.

| Package | Contents | First phase |
| --- | --- | --- |
| `std::mech::sketch` | 2D and 3D sketches, constraints, solve reports, text | 1 |
| `std::mech::part` | Part features, reference geometry, holes, patterns, direct edits, lattices | 1 |
| `std::mech::asm` | Instances, mates, kinematics, interference, fasteners, BOM-only items | 1, 2 |
| `std::mech::gdt` | GD&T model with dialect modules `asme` and `iso` | 1 |
| `std::mech::tol` | Fits, stacks, variation, default distributions | 1, 2 |
| `std::mech::drawing` | Drawings, views, annotations, tables, model-based definition | 1, 2 |
| `std::mech::check` | Design-rule and standards checks | 1 |
| `std::mech::machine` | Gears, shafts, keys, springs | 2 |
| `std::mech::surf` | Freeform curves and surfaces, surface-quality checks, SubD, scan to CAD | 2 |
| `std::mech::sheet`, `std::mech::weld` | Sheet metal; members, trims, welds, cut lists | 2 |
| `std::mech::mold` | Parting, core and cavity, ribs, bosses | 3 |
| `std::mech::route` | Tubes, hoses, harness bundles; pipes and ducts | 3, 5 |
| `std::mech::composite` | Plies, zones, rosettes, drape, ply books | 4 |
| `std::mech::human` | Manikins, reach, vision, posture | 5 |
| `std::standards::*` | ISO, DIN, ASME, EN and AISC tables | 1 |

### Shared types

MEC adds no geometry type. `CoordSys` and `ShapeAspect` are contract types that MEC owns; the rest are Ingot records over core types.

| Type | What it is | Relation to core types |
| --- | --- | --- |
| `Sketch` | Wires and regions with a constraint system and solve report | A `Body`; named entities are typed fields (D-ING-9) |
| `Profile`, `Path` | Closed sketch regions; a G0-connected edge chain | `Query`s over faces or edges |
| `CoordSys` | A right-handed frame anchored to geometry | A `Transform` plus an anchor `Query`, re-resolved every rebuild |
| `Mate` | A typed constraint between frames on two Instances | Stored in the `Assembly` |
| `HoleSpec`, `ThreadSpec`, `Weld`, `Ply` | Manufacturing intent | Attributes keyed by `EntityId` |
| `ShapeAspect` | A feature of size, face set, pattern, or recognized hole, boss, pocket or fillet | A `Query` over faces, typed by kind in Ingot (D-ING-6) |
| `GeometricTolerance`, `Datum`, `DatumSystem` | GD&T controls | Attributes on `ShapeAspect`s |
| `Drawing`, `Sheet`, `View` | 2D documentation | Linework is 2D `Body` geometry |
| `Route` | A path with a specification and end ports | A `Path`, a `RouteSpec` and two `CoordSys` |

### Roles, queries and fixes

Every feature declares a role for each entity it creates: `extrude` creates `start_cap`, `end_cap` and `side(e)` per profile edge, and `hole` creates `wall`, `floor`, `counterbore_wall` and `countersink`. Roles enter the `EntityId` (contract section 5), so they survive parameter edits, and features may attach `FeatureRole` aliases.

```
let lid  = sketch(plane.xy) { rect(80mm, 50mm) } |> extrude(6mm)
let soft = lid |> fillet(lid.face(role: end_cap).edges(), 1.5mm)
```

**Decision D-MEC-1:** Every `std::mech` feature declares typed roles for the entities it creates, and std queries select by provenance and role first, with geometric predicates (`longest`, `parallel_to`) only as filters. *Why:* provenance and roles are stable under parameter edits, while geometric predicates flip when dimensions change. *Rejected:* name-matching heuristics (they rebind silently); persistent face ids stored in source (they break under semantic merge).

MEC never orders, seeds or breaks ties by `EntityId`. Decomposition orders, pattern seeds, scramble seeds and witness values come from geometry and argument values, so renaming a binding changes no geometry and no check value (D-ANV-25).

Every failure is a `FeatureError { kind, why, fix: [Fix], at: [EntityId] }`, where a `Fix` is a compiling source edit that a person clicks or an agent applies.

**Decision D-MEC-2:** Approximation is always opt-in through an explicit parameter, for example `fallback: Fallback::Implicit(max_deviation: 0.01mm)`. A feature that cannot produce an exact result fails and offers that fallback as a `Fix`. *Why:* the contract forbids silent fallbacks, and designers must see every deviation. *Rejected:* automatic fallback with a warning (warnings get ignored, and released geometry would carry unseen error).

Some features take `repr: Repr`: `Cosmetic` stores intent only, `Simplified` builds light geometry with a recorded `ErrorBound`, and `Full` builds complete geometry.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Role vocabularies | Roles on every created entity; `FeatureRole` aliases | `ResolveError` with ranked, compiling fixes | MEC-O-PF-1 | 1 |
| Typed failures and fixes | `FeatureError { kind, why, fix, at }` | — | ANV-O-NAME-5, MEC-O-CK-2 | 1 |
| Opt-in approximation | `fallback:` and `repr:`; deviation recorded as an `ErrorBound` | The exact attempt fails and offers the fallback | MEC-O-PF-5 | 1 |
| Standards data packages | Editions and licences pinned in `ingot.lock` | `UnknownSize { series, near }` | MEC-O-PF-4 | 1 |
| Label invariance | No order, seed or tie-break from names | — | ANV-O-LABEL-1 | 0 |

## Sketching

A sketch is a set of entities, constraints and dimensions on a plane or in space, which the solver turns into solved geometry and a solve report.

### Entities and helpers

| Entity | Unknowns (2D) | Phase |
| --- | --- | --- |
| `point`, `line`, `construction_line` | Coordinates; two end points | 1 |
| `arc`, `circle` | Center, radius, start and end angles; three-point and tangent helpers | 1 |
| `spline` (interpolating) | Through points with optional tangent and curvature handles | 1 |
| `helix`, `spiral` | Axis frame, pitch, turns, taper (exact `anvil::curve` helices) | 1 |
| `offset`, `use_edges` | Driven by a source chain or a model-edge `Query`; `use_edges` never rebinds | 1 |
| `text` | Driven glyph outlines from bundled fonts | 1 |
| `rect`, `rect_between`, `slot`, `polygon` | Helpers emitting entities, constraints and named sub-entities | 1 |
| `ellipse`, `elliptical_arc`, `conic`, `nurbs` | Axes and ratio; ends, apex and rho; control points and weights, degree 2 to 7, fixed knots | 2 |
| `intersection_curve` | Driven, in 3D sketches | 2 |

Helpers name what they emit, in the sketch frame. `rect` emits `left`, `right`, `bottom` and `top` lines and `bottom_left`, `bottom_right`, `top_right` and `top_left` corners. `slot` emits `start_arc`, `end_arc`, `side_a` and `side_b`, and `polygon` emits `edge(k)` and `vertex(k)` keyed from a declared start vertex.

These names reach solids as roles: an extrusion of `r` has faces `side(r.bottom)` and `side(r.left)`, so "the rib's front side" is written, not measured. `text(string, font:, size:, anchor:)` emits glyph outlines as exact Bézier curves for `anvil::make_regions`, and construction geometry constrains but never forms profiles.

### Constraints and dimensions

| Constraint | Equations | Notes | Phase |
| --- | --- | --- | --- |
| `coincident`, `point_on` | 2 or 1 | Point-on-NURBS adds the curve parameter | 1 |
| `horizontal`, `vertical`, `parallel`, `perpendicular`, `collinear` | 1 each | Relative to the sketch axes | 1 |
| `tangent` (G1), `curvature` (G2), `g3` | 1 to 3 | Contact parameters are unknowns; side qualifier stored | 1 (G1), 2 |
| `concentric`, `midpoint`, `symmetric` | 2 each | About a line, or a plane in 3D | 1 |
| `equal` | 1 per pair | Mixed kinds share one value, as in 2D DCM v79 | 1 |
| `fix` | 2 or 3 | Position, or position and orientation | 1 |
| `dim` (distance, angle, radius, diameter, length, curve length) | 1 | Signed variants carry half-space qualifiers | 1 |
| `mirror` | Per entity | About a construction line | 1 |
| `dim_range` | Inequality | Solved by an active set | 2 |
| `pattern` (linear, circular) | Per instance | Keeps instances related while editing | 2 |
| `on_plane`, `on_surface`, `along` | 1 or 2 | 3D sketches | 2 |
| Custom equations | 1 | `e1 == e2` over `Expr<T>` | 2 |

`dim(target, value)` drives; `measure(target)` is driven, readable downstream but never writable. A driving value that carries a tolerance drives the nominal, and the tolerance becomes PMI when the dimension is marked `pmi`. Helper and feature parameters are plain quantities, so they accept every `Scalar` flavor: exact values, tolerances, bounded measurements and symbolic expressions (D-ING-20).

```
use std::mech::{sketch, extrude, part}

pub feature plate(width: Length = 80mm, bore: Length = 8.4mm ± 0.05mm) -> Part {
    let s = sketch(plane.xy) {
        let r = rect(80mm, 50mm, center: point(40mm, 25mm))   // seeds
        let c = circle(point(15mm, 15mm), 4.2mm)
        fix(r.bottom_left)
        dim(r.width, width)
        dim(r.height, 50mm)
        dim(c.diameter, bore, pmi: true)
        dim(distance(c.center, r.left), 15mm)
        dim(distance(c.center, r.bottom), 15mm)
        let diagonal = measure(distance(r.bottom_left, r.top_right))   // driven
    }
    part(s |> extrude(6mm), name: "Plate")
}
```

Custom constraints are ordinary functions returning `Expr<T>`, and comparing two expressions builds an `Equation` item, as in ING's `chord_ratio(fan, 0.8) == 0mm` (D-ING-9).

### Where the solver lives

**Decision D-MEC-3:** Geometric constraint solving is one Anvil operation family, `anvil::solve_constraints` and `anvil::analyze_constraints`, serving sketches, mates, live rules, control-point edits, scan snapping, routing, tolerance completeness and posture. Each built-in constraint has a reference residual in Ingot, and a native kernel replaces it only when an oracle proves them equal. Custom constraints are `Expr<T>` functions, lowered with forward-mode derivatives to Flux's kernel IR. *Why:* the solver has nine clients, runs at 60 Hz during drags, needs Anvil's evaluators in every Newton iteration and must rebuild identically under a pinned version. *Rejected:* a Wasm component (every iteration would cross the boundary); Ingot (sparse factorization belongs in native code); separate sketch and assembly solvers (two diagnosis models); a `constraint` keyword (contract section 6). (revised in round 2)

### Solver method

**Decision D-MEC-4:** The solver decomposes the system structurally, solves well-determined blocks numerically on the canonical `linalg` crate, certifies each converged block by an interval test, and resolves under-determined parts by minimum displacement from the seeds. *Why:* the Zou et al. review finds that under- and over-constrained parts "must be correctly detected and resolved before numerical solving can work". A converged residual is not a forward error bound near tangency, so only a proven box may carry a `Guaranteed` bound. *Rejected:* constructive decomposition as the primary method (rule repertoires are incomplete); one monolithic solve (conflicts cannot be localized); faer's sparse QR (runtime CPU dispatch, no rank-revealing mode). (revised in round 2)

1. **Lower.** Angles become unit complex numbers and rotations unit quaternions on manifolds (the Ceres `Manifold` pattern); lengths divide by the seed box diagonal.
2. **Reduce.** Fixed groups collapse into rigid clusters, and equations "solvable alone" substitute forward, as in SolveSpace.
3. **Decompose.** A maximum matching gives the Dulmage–Mendelsohn split into over-, well- and under-determined parts. Well-determined blocks solve in topological order, with ties broken by the canonical order of seed geometry and constraint kind.
4. **Solve.** Each block runs trust-region Levenberg–Marquardt with dense rank-revealing QR, or SVD on ambiguous blocks. Above 2,000 unknowns, sparse QR is followed by a rank-revealing pass on R.
5. **Certify.** A Krawczyk test on the scaled system proves a box whose radius is the `Guaranteed` bound and certifies a unique solution on the branch. Otherwise the bound is `Estimated` (residual over an estimated smallest singular value), and one above the smallest entity tolerance fails with `IllConditioned { block, condition }`.
6. **Remainder.** Under-determined parts minimize weighted displacement from the seeds, which SolveSpace reports gives "less surprising" drags. Redundant but consistent equations are warnings; equations that cannot vanish are conflicts.

[[DIAGRAM: constraint solve pipeline. Boxes: Ingot sketch block (seeds, constraints) → Lower (unknowns on manifolds, scaled residuals) → Reduce (rigid clusters, forward substitution) → Dulmage–Mendelsohn decomposition → three branches: well-determined blocks (LM on canonical linalg, then Krawczyk certification), under-determined part (minimum displacement from seeds), over-determined part (consistency test) → Diagnosis (modular rank, kernel, minimal conflict sets, generic vs accidental) → Solve report and solved Body with Approx bounds. Side arrow from Anvil evaluators into the LM box.]]

During a drag the moved entity gets a weighted soft target, each frame is one warm-started solve, and release writes the solved seeds to source. Builds never warm-start, and `linalg` fixes blocking, lane order and reduction trees without FMA, so results are bit-identical across the canonical class at any thread count.

### Determinism and stability under edits

**Decision D-MEC-5:** The coordinates written in a sketch block are seeds, and the solved sketch is a deterministic function of seeds, constraints and the pinned operation version. When driving values move far from their values at the seeds, the solver follows a predictor-corrector continuation path from seed values to targets, so it stays on the seeds' branch. Discrete qualifiers (angle orientation, tangency side, arc direction, side of a signed distance) are captured when a constraint is created and stored in source. *Why:* the result must depend on source only; continuation is the standard remedy for Newton's sensitivity to the initial guess; stored qualifiers make the intended branch explicit. *Rejected:* solving from the previous session's solution (history-dependent, breaks merges); homotopy that finds all solutions (too slow for interactive use, per the same review).

If continuation cannot reach the targets, the solver returns `BranchFlip` or `NoConvergence` with the last reachable value, never a solution on another branch.

### Diagnosis

| `SolveReport` item | Method |
| --- | --- |
| Degrees of freedom | Kernel of the scaled Jacobian from the block's rank-revealing factorization; free motions shown as arrows |
| Fully constrained entities | No kernel vector moves the entity's unknowns |
| Redundant and conflict sets | Row dependencies; a deletion filter in canonical order, then a minimality pass; every conflict member offered as a `Fix` |
| Generic or accidental | Rank at a witness configuration whose metric values are rationals hashed from arguments and seed geometry |
| Certification | Rank modulo one or two 61-bit primes certifies full rank; an exact rational kernel vector certifies a deficiency |

The witness configuration method finds dependencies that graph counting misses. Zou and Feng show its greedy variants can return non-minimal sets that depend on the seed equation, hence the minimality pass.

Spline handles are constrainable entities, and curve lengths use Gauss–Legendre quadrature within the block's certified radius. 3D sketches add z and drive sweep paths, routes and weldment skeletons.

Targets on the reference laptop (contract 13.3): a 200-entity sketch re-solves in under 2 ms native. A 2,000-entity drag step takes under 8 ms native and 16 ms in the browser, and its full diagnosis under 50 ms.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| 2D sketch solve | `sketch(plane) { … } -> Sketch<…>` through `anvil::solve_constraints` | `Conflict`, `NoConvergence`, `BranchFlip`, `Degenerate`; partial result with the failing block | MEC-O-SK-1, MEC-O-SK-4 | 1 |
| Certified positions | Solved values as `Approx`: `Guaranteed` from a Krawczyk box, else `Estimated` | `IllConditioned { block, condition }` | MEC-O-SK-8 | 1 |
| Degree-of-freedom report | `s.report() -> SolveReport` with modular-rank certification | Uncertified verdicts flagged | MEC-O-SK-2 | 1 |
| Drag | `api` Edit stream at 60 Hz; seeds written on release | Holds the last converged frame | MEC-O-SK-5 | 1 |
| Named helper entities | Sub-entities of helpers; roles such as `side(r.bottom)` | Unknown name is a compile error | MEC-O-SK-9 | 1 |
| Text | Exact glyph outlines to regions | `FontMissing { font }` | MEC-O-PF-17 | 1 |
| Splines and helices | Interpolating splines; exact helices | `Degenerate` | MEC-O-SK-6 | 1 |
| NURBS, conics, ellipses | Entities above | `Degenerate` | MEC-O-SK-6 | 2 |
| 3D sketch | `sketch3d() { … }` | As 2D | MEC-O-SK-1 | 2 |
| Inequalities | `dim_range(target, min, max)` | `Conflict` when infeasible | MEC-O-SK-3 | 2 |
| Custom constraints | `Expr<T>` functions lowered to the kernel IR | `ING2402` on branching over unknowns | MEC-O-SK-7 | 2 |

## Part features

### Conventions

**Decision D-MEC-6:** Features that create material from profiles (`extrude`, `revolve`, `sweep`, `loft`, `boundary`, `rib`, `thicken`) return new tool bodies. Booleans are written only with `+`, `-` and `&`, or `combine` for n-ary cases. Features that dress existing geometry (`fillet`, `chamfer`, `shell`, `draft`, `hole`, `thread`, direct edits) take a body and return it modified. *Why:* one spelling per intent; the Boolean is visible in history; Kiln caches the tool body apart from the Boolean. *Rejected:* an add, remove or intersect option on every feature, as Onshape's features have [unverified] (a second spelling of the same operator).

```
use std::mech::{sketch, extrude, hole, fillet, HoleSpec, ThreadSpec}

pub feature housing(depth: Length = 30mm) -> Part {
    let block  = sketch(plane.xy) { rect(90mm, 60mm, center: origin) } |> extrude(depth)
    let pocket = sketch(block.face(role: end_cap)) { rect(70mm, 40mm, center: origin) }
                 |> extrude(UpTo(depth - 4mm), dir: -normal)
    let body   = (block - pocket)
                 |> hole(at: block.face(role: end_cap).corners(inset: 8mm),
                         spec: HoleSpec::tapped(ThreadSpec::iso_metric("M5"), depth: 10mm))
                 |> fillet(block.edges(role: side(any), parallel_to: z), 5mm)
    part(body, name: "Housing").material(alu_6061_t6)
}
```

`Extent` is shared by every profile feature: `Blind(Length)`, `Symmetric(Length)`, `ThroughAll`, `UpTo(Query)`, `UpToNext(Body)`, `Offset(Query, Length)` and `UpToVertex(Query)`.

### Reference geometry

`std::mech::refgeom` places sketches, mirrors and patterns: `plane.offset(from, d)`, `plane.at_angle(about: axis, angle)`, `plane.mid(a, b)`, `plane.through(p1, p2, p3)`, `plane.tangent(face, at:)`, `axis.of(face)`, `axis.through(p1, p2)` and `point.on(curve, at:)`. Each returns a `CoordSys`-anchored value that re-resolves through its queries, with handles for direct manipulation.

A frame on stable geometry (an axis, a circle center, a vertex) moves only when that entity moves. A frame derived from shape (a centroid, an edge midpoint, a box center) moves when the face changes shape, so it carries `Note::ShapeDerivedFrame`, which release checks may forbid.

### Profile features

```
pub feature extrude(profile: Profile, extent: Extent = Blind(10mm), dir: Direction = normal, draft: Angle = 0deg,
                    thin: Option<Length> = none, twist: Option<Field<Length, Angle>> = none,
                    scale: Option<Field<Length, Real>> = none) -> Body
pub feature sweep(profile: Profile, path: Path, frame: SweepFrame = RotationMinimizing, guides: [Path] = [],
                  twist: Option<Field<Edges, Angle>> = none, scale: Option<Field<Edges, Real>> = none) -> Body
pub feature loft(sections: [Profile], guides: [Path] = [], start: EndCondition = Free, end: EndCondition = Free) -> Body
```

`revolve`, `boundary`, `thicken`, `rib` and `helix` follow the same pattern. `SweepFrame` is `RotationMinimizing` (the default, since Frenet frames flip at inflections), `FixedNormal`, `FollowSurface`, `GuideCurve` or `Frenet`; `EndCondition` is `Free`, `NormalToProfile`, `Tangent` or `Curvature`. Twist and scale laws are Fields over the extrusion distance or the path's edges.

### Holes and threads

```
pub feature hole(body: Body, at: Query<Point>, spec: HoleSpec, extent: HoleExtent = ThroughAll) -> Body
pub feature thread(body: Body, faces: Query<Face>, spec: ThreadSpec, repr: Repr = Cosmetic) -> Body
```

`HoleSpec` is `simple`, `counterbore`, `countersink`, `counterdrill`, `spotface`, `tapped(thread, depth)`, `tapered_pipe(thread)` or `clearance(fastener, fit)`. Every diameter accepts a `Tol<Length>` or an ISO 286 fit code such as `H7`, and a hole through several bodies records each segment for fastener stacks.

| Data package | Content | Phase |
| --- | --- | --- |
| `std::standards::iso_metric_thread` | ISO 68-1 profile, ISO 261 plan, ISO 965-1 tolerances [unverified editions] | 1 |
| `std::standards::unified_thread` | UN, UNC, UNF, UNEF, ASME B1.1 [unverified edition] | 1 |
| `std::standards::clearance_holes` | Fine, medium and coarse series, metric (ISO 273 and its successor) and inch [unverified editions] | 1 |
| `std::standards::iso286` | Limits and fits [unverified edition] | 1 |
| `std::standards::pipe_thread` | ISO 228-1, ISO 7-1, NPT (ASME B1.20.1) [unverified editions] | 2 |
| `std::standards::trapezoidal_thread` | ISO 2904, ACME (ASME B1.5) [unverified editions] | 2 |

**Decision D-MEC-7:** Holes and threads are semantic first: `hole` writes a `HoleSpec` and `thread` a `ThreadSpec` keyed by the created entity ids, and geometry follows from the record. Threads default to `Repr::Cosmetic`, nominal geometry plus the record; `Repr::Full` builds the flank by an exact helical sweep and Boolean, from phase 1, for printed threads. *Why:* drawings, AP242 PMI, CAM, fastener logic and inspection need the semantics; modeled threads multiply face counts; printed parts need real flanks. *Rejected:* geometry-only holes recognized later (recognition cannot recover tolerance class or thread series). (revised in round 2)

### Dress-up features

```
pub feature fillet(body: Body, edges: Query<Edge>, r: RadiusLaw, section: BlendSection = Circular,
                   corners: Corners = Auto, overflow: Overflow = RollOver, fallback: Fallback = Fallback::None) -> Body
```

`RadiusLaw` is a `Length`, `Linear(r0, r1)` or a `Field<Edges, Length>`; `BlendSection` is `Circular`, `Conic(rho)`, `ChordWidth(Length)` or `CurvatureContinuous`. `fillet` maps to `anvil::blend` with the `EdgeChain` variant, `face_fillet(a, b, r, hold_lines)` to `FaceFace` and `full_round(a, middle, b)` to `ThreeFace`; `chamfer`, `shell` and `draft` map to their namesakes.

Blend phases and targets are ANV's (D-ANV-29). The re-fillet benchmark must reach 95% success on stage-1 configurations at the phase 1 gate and 97% on all configurations at phase 2.

| Blend stage | Capabilities | Phase |
| --- | --- | --- |
| 1 | Constant and linear radius; sequential fillets on blend, offset and swept supports; `RollOver` and `KeepEdge`; valence-3 corners with unequal radii and mixed convexity; chamfer–fillet corners; termination at smooth edges | 1 |
| 2 | Conic and G2 sections; Field radii; face fillets with hold lines; full rounds; chord width; radius edits | 2 |
| 3 | Corners of valence four and above; blends across facet faces | 3 |
| 4 | G3 sections | 4 |

With `fallback: Implicit { max_deviation }`, a failed region becomes an implicit patch fitted G1 to its neighbours, and `Note::BlendFallback` states its certified deviation and seam gap.

### Patterns, mirror and hulls

```
pub feature pattern<T: Patternable>(seed: T, at: [Keyed<Transform>], mode: PatternMode = Geometry, skip: [Key] = []) -> T
```

The generators are `linear`, `circular`, `along`, `at_points`, `fill(region, layout, spacing, origin)` and `by_density(region, density)`. Each returns keyed transforms (contract section 5). `linear` keys `(i, j)` from the seed, `circular` the angular index and `along` the arc-length index; `at_points` keys by the anchor's `EntityId`, `fill` by lattice coordinates from the declared origin, and `by_density` by each seed's initial key.

Adding or removing a point renames no other copy, and `skip:` lists keys, never positions.

```
let vents  = pattern(vent_slot(length: 10mm), at: linear(dir: +x, count: 8, spacing: 6mm), skip: [(3, 0)])
let graded = for i in 0..8 { vent_slot(length: 10mm + i * 2mm) |> move(x: i * 6mm) }
cover - vents - graded
```

**Decision D-MEC-8:** `pattern` places keyed copies. `PatternMode::Geometry` (default) evaluates the seed once and places copies with one n-ary Boolean; `PatternMode::Feature` re-evaluates the seed per copy, which an extent such as `UpToNext` requires. *Why:* geometry mode is one cached evaluation, and keys keep names and skip lists stable when generators gain or lose points. *Rejected:* always re-evaluating (slow); always copying (wrong for location-dependent extents); positional indices (positional naming under another name). (revised in round 2)

`by_density` runs a fixed number of Lloyd iterations seeded from a hash of its arguments and the region's `GeometryId`. A transform whose source is used again, as in `half + mirror(half, plane.yz)`, creates copies with role `copy` or `mirror`, and role queries accept `mirrored: true` (D-ANV-30).

`hull(bodies)` is exact on meshes and facet faces in phase 1 and bounded on B-rep operands in phase 2; `minkowski(a, b)` follows in phase 2. `split(body, tool)` cuts by a plane, face set, sheet or sketch; `split_face` takes curves, isoclines or silhouettes; `combine` is an n-ary Boolean over any representation.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Reference geometry | Planes, axes and points anchored as `CoordSys` | `ResolveError`; `Note::ShapeDerivedFrame` | MEC-O-PF-16 | 1 |
| Extrude | Profile to solid or sheet with roles, draft, twist and scale | `ResolveError` on `UpTo`; `SelfIntersecting` with the largest feasible draft | MEC-O-PF-1 | 1 |
| Revolve | Profile about an axis | `CrossesAxis { segment }` with "trim at axis" | MEC-O-PF-1 | 1 |
| Sweep | G1 path with a frame rule; exact helical sweeps | `PathNotG1 { vertex }`; `SelfIntersecting { parameter }` | MEC-O-PF-2 | 1, 2 (guides, laws) |
| Loft | Sections, guides, end conditions, vertex matching | `Twisted` with suggested matches; `SectionsNotClosed` | MEC-O-PF-2 | 1 (no guides), 2 |
| Boundary | Curve network with G0 to G2 edge conditions | `NetworkNotCompatible { curves }` | MEC-O-SF-2 | 2 |
| Thicken, rib | Face set to solid; open profile extended to material | `OffsetSelfIntersection { faces, max_t }`; `NoBoundary` | MEC-O-PF-3, MEC-O-PF-1 | 1 |
| Helix and spiral | Exact `anvil::curve` helices | `Degenerate` on zero pitch | MEC-O-PF-2 | 1 |
| Holes | `HoleSpec`, hole chains | `UnknownSize { series, near }`; `BreaksOut { faces }` with "make through" | MEC-O-PF-4 | 1 |
| Threads | `ThreadSpec`, `Cosmetic` or `Full` | `ThreadTooLong` | MEC-O-PF-4 | 1 |
| Fillets and chamfers, stage 1 | `anvil::blend`, `anvil::chamfer` | `RadiusTooLarge { max_feasible }`, `BlendOverflow`, `VertexBlendFailed` with fixes | MEC-O-PF-5 | 1 |
| Blends, stages 2 to 4 | Stage table above | `NoContact`; as above | MEC-O-PF-5, MEC-O-SF-1 | 2, 3, 4 |
| Shell | Uniform or Field thickness | `WallCollapse { region }` | MEC-O-PF-3 | 1, 2 (Field) |
| Draft | Neutral plane on analytic faces; free-form; parting line and step | `DraftNotPossible { face, reason }`, `BlendRegrowFailed` | MEC-O-PF-6 | 1, 2 (free-form), 3 (parting, step) |
| Patterns | Keyed generators; `skip: [Key]` | `CopyFailed { key, error }` unless `skip_failed: true` | MEC-O-PF-7 | 1, 2 (along, fill, density) |
| Mirror and copies | Roles `copy` and `mirror`; `mirrored: true` | — | MEC-O-PF-7 | 1 |
| Hull and Minkowski sum | `hull`, then B-rep hulls and `minkowski` | `Degenerate`; `NotConvex { operand }` | MEC-O-PF-18 | 1, 2 |
| Split and combine | `split`, `split_face`, `combine` | `BooleanFailed { faces, reason }`; `EmptyResult` | MEC-O-PF-8 | 1 |

## Direct edits, reuse and generated geometry

### Direct edits

Direct edits apply to any B-rep, imported geometry included, and are ordinary features in history. `push_pull(body, faces, by)` offsets faces through `anvil::offset_faces`, and `move_faces(body, faces, by, rules)` translates, rotates or offsets them. `replace_face`, `delete_face`, `edit_aspect` (a hole diameter, or a fillet radius through `anvil::edit_blend`) and `drive` (a 3D driving dimension) complete the set.

Blends next to edited faces are removed, the edit applied and the blends rebuilt with the same parameters and ids (ANV). Otherwise the edit fails with `BlendRegrowFailed { blend, reason }` and the fixes "remove blend" and "reduce radius". Live rules from `anvil::recognize_relations` (coplanar, coaxial, tangent, symmetric, equal radius) are written into source as an editable list.

```
let edited = imported |> move_faces(imported.faces(near: p), by: offset(2mm),
    rules: [coaxial(f12, f31), coplanar(f4, f9), tangent(f12, f13)])  // written by detect()
```

**Decision D-MEC-9:** Direct edits solve face motions with the shared constraint solver: each moved or affected face gets a rigid motion or offset unknown, and the edit and live rules are constraints. Anvil's face operations re-intersect neighbours and regrow adjacent blends, and the recognized rules are written to source. Phase 1 offers push-pull; moves, replacements and rule detection arrive with their Anvil operations in phase 2. *Why:* Siemens describes synchronous technology as editing without a fixed history while related geometry adjusts "to maintain design intent"; Crucible gets that from mechanisms it already has, explicit in source. *Rejected:* a separate history-free mode (two models of one part); hidden rule inference at every rebuild (results would change with the recognizer). (revised in round 2)

### Deform, wrap, emboss and engrave

`emboss(body, curves, onto, height, mode)` raises, engraves or imprints sketch curves on planar and cylindrical faces. It uses the developable wrap, which is isometric and exact, so part numbers and logos work in phase 1. Embossed text may be a late-bound release field such as the revision label (Drawings).

`wrap` also offers `Conformal` (Boundary First Flattening) and `Geodesic` methods, returning a distortion `Field<Faces, Real>` on non-developable faces. `deform(body, map)` takes `bend`, `twist`, `taper`, `stretch`, `cage` or `field(Field<Body, Displacement>)`; the Field variant lets a warpage or springback result pre-compensate an insert or die face, with the achieved bound returned.

### Derived parts and families

`derive(source, take, mirror, scale, params)` takes bodies, sketches, frames, interfaces and parameters from a feature in this repository or in a dependency pinned by `ingot.lock`; `Scale::anisotropic` serves mould shrinkage. A source bump is a Proposal showing the derived geometry diff, so released parts never change silently. `part(body, name, item)` gives a Body identity; a weldment Part may hold several bodies, each a cut-list item but not a BOM line.

**Decision D-MEC-10:** A configuration is a parameter record, a design table is a table of parameter records, a part family is a design table whose rows carry part identity, and suppression is a `Bool` parameter used in an `if`. Assembly variants mark their parameters `#[configuration]`, and an Instance's existence may depend only on those parameters and constants. *Why:* features are already functions of typed parameters (ING's `Params<f>`), and the existence rule lets Kiln compute the 150% BOM by abstract interpretation (contract section 6). *Rejected:* configuration states stored beside the source, as SOLIDWORKS configurations are [unverified] (invisible in review, hard to merge); existence driven by any parameter (the 150% BOM would need enumeration). (revised in round 2)

```
pub enum Drive { Belt, Direct }

pub feature conveyor(#[configuration] drive: Drive = Belt, length: Length = 2m) -> Assembly {
    let frame = instance(frame(length), fixed: true)
    let motor = instance(gearmotor_m3())
    let belt  = if drive == Belt { [instance(belt_kit(length))] } else { [] }
    assembly([frame, motor] + belt, mates: [fastened(motor.csys("flange"), frame.csys("drive_end"))])
}
```

`family(f, key:, rows: table { … })` checks every row's types and units at compile time, CSV headers included (ING owns the syntax). Each row is a Part with its own item number, and a family is green only when every row builds and passes every check.

### Lattices and machine elements

`lattice(region, cell, size, thickness: Field<Body, Length>, orientation, skin)` calls `anvil::lattice` and exposes the strut graph. `Cell` covers strut cells (body-centered cubic, octet) and minimal surfaces (gyroid, Schwarz P, diamond), and the `mech-lattice` Wasm component generates further families as graphs or tapes.

Joining a lattice to a B-rep part keeps the part's exact faces with their ids and attributes (D-ANV-2), so golden product 2's mounting holes keep their `HoleSpec`, GD&T and drawing dimensions. Thickness usually comes from Flux's filtered density, and Flux analyses strut lattices as beam lattices.

| Machine element | Contract | Standard | Phase |
| --- | --- | --- | --- |
| Involute spur and helical gears | Module, teeth, pressure and helix angles, profile shift, relief, crowning | ISO 21771-1:2024 | 2 |
| Bevel, worm, internal gears | As above | ISO and AGMA references [unverified] | 3 |
| Shafts | Steps, shoulders, grooves, undercuts, keyways | DIN and ISO tables [unverified] | 2 |
| Bearings, seals, retaining rings | Catalog parts with mating frames and housing fits | Supplier data | 2 |
| Springs | Compression, extension, torsion | | 2 |

Involute flanks are not rational, so gears use B-spline flanks within 0.1 µm (target) and record exact parameters for gear cutting and contact analysis. Torques are `Torque` values, J/rad in the strong angular system, written with the named unit `Nm` (contract section 5).

### Rebuild performance

PLT owns contract 13.3's rows: a `SignOff` rebuild of a GP1-class benchmark in 2 s, `Interactive` p90 ≤ 10 s on the 200-feature corpus, recertification p90 ≤ 30 s, and the drag-preview rule. After an early edit every downstream input changes, so MEC's share is keeping features cheap. Cosmetic threads and geometry-mode patterns keep face counts low, tool bodies cache apart from Booleans, and each feature declares a cost estimate for Kiln's preview scheduler.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Push-pull | `offset_faces` on any B-rep with blend regrowth | `NeighborCannotExtend { face }`, `BlendRegrowFailed` | MEC-O-PF-9 | 1 |
| Move, replace and delete faces | Motions and live rules on the shared solver | `TopologyChange { faces }`; `HealFailed { loop }`; `RuleConflict { set }` | MEC-O-PF-9 | 2 |
| Recognized aspect edits | `edit_aspect` via `recognize_aspects` and `edit_blend` | `NotRecognized` with the best partial match | MEC-O-PF-9 | 2 |
| Emboss and engrave | Planar and cylindrical faces by developable wrap | `WrapOutsideFace` | MEC-O-PF-17 | 1 |
| General wrap and deform | Conformal and geodesic wraps; deformation maps with achieved bound | `FoldOver { region }`; `ToleranceNotMet { achieved }` | MEC-O-PF-10 | 3 |
| Derived parts | `derive` with take, mirror, scale and parameters | `TakeMissing { name }` | MEC-O-PF-11 | 1, 2 (cross-repository) |
| Configurations and families | Parameter records; `#[configuration]` variants; families | `RowFailed { key, error }`; `DuplicateKey`; `ING3501 UnitMismatch` | MEC-O-PF-12 | 1 |
| Lattices | `anvil::lattice` from Flux Fields; leaf-preserving join | `BelowMinFeature { region, min }` per MFG process profile | MEC-O-PF-13 | 1 |
| Gears | B-spline flanks within 0.1 µm plus exact semantics | `Undercut { teeth, min_shift }`, `PointedTip`, `MeshMismatch` | MEC-O-PF-15 | 2, 3 |
| Shafts and springs | Parametric sections; helical springs | `Degenerate` | MEC-O-PF-2 | 2 |
| Rebuild budget | Feature cost estimates; contract 13.3 rows | Regressions block merges | MEC-O-PF-14 | 1 |

## Assemblies

### Structure

An Assembly is a tree of Instances with placements and mates (contract section 5). An Instance references a Part or Assembly feature with parameter overrides, a `Transform` and a representation. The same Part with other parameters is another call or family row, hence another BOM line.

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

Mates attach only to `CoordSys` values, as Onshape's mate connectors are "local coordinate systems located on or between entities". Features publish named frames, `csys(query)` derives one from geometry, and a frame that fails to re-resolve is a `ResolveError` on the mate; shape-derived frames carry `Note::ShapeDerivedFrame`.

`bom_item(item, qty: Quantity | AsRequired, applies_to: Option<Query>)` adds a BOM line without geometry, such as thread-locker, labels, packaging, potting compound or wire sold by length. Its unit comes from the Item (each, length, mass, volume).

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

**Decision D-MEC-11:** Assembly mates use the same `anvil::solve_constraints` operation as sketches, with one SE(3) unknown per rigid cluster (quaternion plus translation on a product manifold). Fastened Instances merge into rigid clusters before solving, and joint limits are inequalities solved by an active set. *Why:* one solver gives one diagnosis model, with motion arrows, minimal conflict sets and generic-versus-accidental redundancy alike in sketches and assemblies. *Rejected:* a separate assembly solver, the split that D-Cubed's separate 2D DCM and 3D DCM products reflect (duplicate oracles, different failure semantics); sequential transforms only (cannot close kinematic loops).

Redundant but consistent mates, such as two coaxial hinges on one door, are `Redundant` warnings, never errors, and Flux's multibody solver removes or complies them.

### Kinematics and motion

```
let study = motion(gearbox(), drive: [(input_rev, angle(t) = 360deg/s * t)], t: 0s..2s, samples: 200)
study.pose(wheel)                        // Field<(Instances, Time), Transform>
study.require(min_clearance(study, housing, wheel) > 0.5mm)
```

Positions track the drivers by predictor-corrector continuation; velocities and accelerations solve the differentiated constraints with the Jacobian already factored. A rank drop returns `Singular { t, mates }`, and a reached limit `LimitReached { mate, t }`.

**Decision D-MEC-12:** Dynamics belong to Flux. `motion` handles prescribed-motion kinematics; anything with forces, masses, contact or compliance goes to Flux's multibody solver, which reads the same Assembly. MEC hands over each Instance's mass properties with their bounds, each mate as a typed joint, the redundancy report, flagged contact pairs and drivers. *Why:* kinematics reuses the constraint solver; dynamics needs integrators, contact and validity envelopes. *Rejected:* a dynamics engine inside the assembly library (a second physics engine beside Flux).

### Interference and clearance

`interference(asm, classify: true)` uses `anvil::interference`, which computes certified distances and overlap volumes on exact geometry.

| Class | Meaning | Default |
| --- | --- | --- |
| `Hard` | Positive interference volume | Error |
| `Touching` | Zero gap within the entity tolerance | Info |
| `IntendedThread` | Fastener thread inside a mating `ThreadSpec` | Ignored |
| `IntendedFit` | Overlap within a declared ISO 286 interference fit | Ignored, reported to tolerancing |
| `Clearance` | Gap below a declared minimum | Error when declared |

Motion studies sample adaptively, keeping each body's displacement between samples below a fraction of the clearance threshold. Sampled clearance is the interval [sampled minimum − maximum relative displacement, sampled minimum], so `min_clearance` checks decide three-valued, and near a singular position they are `Undecided`.

`check::enclosure` runs clearance, keep-in and connector cut-out checks against boards from other ECAD tools. In phase 1 it reads boards imported as STEP assemblies; ECO's IDF and STEP board readers add reference designators and keep-outs.

### Exploded views, subassemblies and interfaces

`explode(asm, steps)` stores named, ordered steps that drawings, illustrations and UI animation consume. `explode_auto` proposes steps from removal directions found through a non-directional blocking graph, fasteners first [unverified source for the method].

A subassembly Instance is rigid by default: its mates are solved once and frozen, keeping large assemblies in small solves. `instance(sub, flexible: true)` exposes its free internal freedoms to the parent.

**Decision D-MEC-13:** Cross-part references go only through skeletons and interface records, both ordinary Ingot values. A skeleton is a feature returning frames, sketches, surfaces and parameters; an interface is a record marked `#[interface]` that one part provides and another consumes, with a derived `compatible(a, b)` check at compile and build time. Implicit in-context references that capture another part's geometry are not supported. *Why:* explicit dependencies keep the graph acyclic and visible in review, and semantic merge stays possible. *Rejected:* edit-in-context with captured references, as in SOLIDWORKS [unverified] (hidden coupling, failures far from their cause); an `interface` keyword (contract section 6). (revised in round 2)

```
#[interface]
pub record MotorMount { pilot: CoordSys, pilot_d: Tol<Length>, bolts: [CoordSys], thread: ThreadSpec }

pub feature plate(m: MotorMount) -> Part {
    let base = sketch(plane.xy) { rect(60mm, 60mm, center: origin) } |> extrude(5mm)
    hole(base, at: m.pilot.origin, spec: HoleSpec::simple(fit(m.pilot_d.nominal, H7)))
        |> hole(at: m.bolts.origins(), spec: HoleSpec::clearance(m.thread, fit: Medium))
        |> part(name: "Motor plate")
}
```

`mate_interface(a, b)` places both sides with one mate and checks compatibility; electronics uses the same records for board outlines and connector keep-outs.

### Large assemblies

| `InstanceRepr` | Content | Error stated |
| --- | --- | --- |
| `Full` | Exact B-rep, loaded on demand | None |
| `Graphics` | Cached `DisplayPackage` levels of detail | Chordal deviation per level |
| `Envelope` | Oriented box or convex hull | Hull deviation |
| `Shrinkwrap(gap)` | One closed skin from `anvil::shrinkwrap` | Bound from the operation |
| `Defeatured(rules)` | Aspects below a size removed by `anvil::defeature` | Removed aspects and volume change |
| `Excluded` | Not loaded | Excluded from mass properties, with a warning |

Opening loads structure, transforms and cached tessellations first; B-reps load only for Instances being edited, measured or checked. Mass properties always come from the full body's cached values, and named representation sets (`repr_set("simulation")`) serve Flux and drawings.

Contract 13.3 sets capacity: 100,000 Instances at 60 fps on G1 (1,000,000 on the high band), 20,000 on G2, and a 1,000-part assembly opened from warm cache in 10 s. MEC adds one target: a 100,000-Instance assembly opens for viewing in under 15 s.

### Standard parts and fasteners

| Data package | Examples | Phase |
| --- | --- | --- |
| `std::standards::iso_fasteners` | ISO 4762, 4014, 4017, 4032, 7089, 10642 | 2 |
| `std::standards::din_fasteners` | DIN 912, 933, 934 and other legacy designations mapped to ISO | 2 |
| `std::standards::ansi_fasteners` | ASME B18.3, B18.2.1, B18.2.2 | 2 |
| `std::standards::pins_rings` | Dowel pins, retaining rings, keys | 2 |
| `std::standards::self_clinching` | Self-clinching nuts, studs and standoffs with installation limits | 2 |

All editions in this table are [unverified]; each package records the edition it encodes.

```
let joint = fasten(cover_holes, spec: FastenerSpec::iso4762(class: "8.8", washer: iso7089, nut: none),
                   engagement: Engagement::diameters(1.5))
```

`fasten` reads the hole chain, computes grip from the stacked `HoleSpec` segments, adds the minimum engagement for the tapped material and picks the shortest standard length that satisfies both. Each fastener records preload and tightening torque for Flux's bolted-joint forms.

Selection resolves over the organization's approved parts first: `Purchased` Items with internal numbers, approved manufacturers and lifecycle states (KLN). A `FastenerSpec` may name an internal number, and reaching the open catalog needs a recorded waiver, so design, ERP and shop BOMs agree.

### Mate inference and assembly-level features

`suggest_mates(a, b)` ranks candidates from interfaces, recognized aspects and an optional learned Wasm ranker; suggestions become mates only when accepted as source edits. On the Fusion 360 Gallery Assembly-Joint dataset, JoinABLe reports 79.53% accuracy against a reported human level of 80%.

An assembly-level cut or hole states its mode: `DerivedParts` creates derived Parts with new item numbers, while `AfterAssembly` is a manufacturing operation recorded in the MBOM, leaving EBOM Parts unchanged. Assembly-level features prefix created ids with the Instance path (D-ANV-30).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Instances and structure | `instance`, `assembly`, representations, `#[configuration]` existence | `ResolveError` on a mate frame | MEC-O-AS-1 | 1 |
| BOM-only items | `bom_item` with the Item's unit | `UnitMismatch { item, unit }` | MEC-O-AS-9 | 1 |
| Mate solve and diagnosis | Mates tabled above on the shared solver | `Conflict`, `Redundant` (warning) | MEC-O-AS-1 | 1, 2, 3 (cam) |
| Kinematics | `motion` → `Field<(Instances, Time), Transform>` and derivatives | `Singular { t, mates }`, `LimitReached { mate, t }` | MEC-O-AS-2 | 2 |
| Static interference | Classified clashes | `WorkLimit` | MEC-O-AS-3 | 1 |
| Dynamic clearance | Clearance intervals; three-valued `min_clearance` | `Undecided` near singular positions | MEC-O-AS-10 | 2 |
| Enclosure checks | Clearance, keep-ins and cut-outs against imported boards | Findings as check Fields | MEC-O-AS-11 | 1 (STEP assemblies), 2 (board readers) |
| Exploded views | Ordered steps; automatic proposals | `CollidesDuringStep { step, pair }` (warning) | MEC-O-AS-5 | 2, 3 (automatic) |
| Flexible subassemblies | `flexible: true` | Conflicts list inner mates by path | MEC-O-AS-1 | 2 |
| Skeletons and interfaces | Skeleton features; `#[interface]` records | `Incompatible { field, provided, required }` | MEC-O-AS-8 | 1 (skeletons), 2 |
| Large-assembly representations | `InstanceRepr`, named sets, contract 13.3 capacity | `ReprUnavailable { instance, repr }` | MEC-O-AS-4 | 2 |
| Fasteners | Grip, engagement, length selection, preload intent | `NoStandardLength { needed, nearest }`, `HoleMismatch`, `EngagementTooShort` | MEC-O-AS-6 | 2 |
| Approved-parts selection | Approved parts first; open catalog only with a waiver | `NotApproved { part }` | MEC-O-AS-9 | 2 |
| Mate inference | Ranked suggestions | — | MEC-O-AS-7 | 3 |
| Assembly-level features | `DerivedParts` or `AfterAssembly` | Omitting `mode` is a compile error offering both | MEC-O-AS-12 | 2 |

## Surfacing

### Continuity

`Continuity` is `G0` to `G3`: shared position, tangent plane, normal curvature in every direction, then its derivative. Surfacing features take target continuities per edge and return a `ContinuityReport` from `anvil::analyze_continuity` with each edge's largest position gap, normal angle and relative curvature difference and their locations.

Thresholds are relative to the Body's resolution and size by default, so hull fairing and MEMS share one rule, with absolute overrides per design. A feature that misses its targets returns `ContinuityNotMet { edge, achieved }` and never relabels the result at a lower continuity.

### Curves and surfaces

| Feature | Contract | Phase |
| --- | --- | --- |
| `curve_through`, `iso_curve`, `project`, `intersect`; curvature combs | Interpolating and derived curves; `Field<Edges, Curvature>` | 1 |
| Extruded, revolved, ruled and swept surfaces; `trim`, `untrim`, `sew`, `knit_to_solid` | Profile features with `solid: false`; topology operations | 1 |
| `curve_cv`, `blend_curve`, `offset_curve`, `rebuild_curve` | Control-point NURBS, G0 to G3 bridges, offsets, refits with a bound | 2 |
| `boundary`, `fill`, `blend_surface`, `match`, `extend`, `offset_surface` | Network and n-sided surfaces, bridges and matches to G2; extensions; offsets | 2 |
| `network(u, v, tol)` | Least-squares fit to a curve network with gaps up to `tol` | 3 |
| `edit_cv` with the drag fast path; G3 `match` and `blend_surface` | Control-point editing on the shared solver | 3 |

### Surface-quality checks

Every analysis is a Field that the UI paints and checks constrain. The set covers curvature, zebra, reflection and highlight lines, combs, edge continuity, draft and deviation from another body or a scan. Control-net quality adds degree, spans, knot uniformity, kinks and edge-curvature monotonicity.

```
hood.require(surface_quality(hood.faces(visible), edges: G2, monotone_edge_curvature: true, max_degree: 7))
```

Class-A work is an interactive loop of control-vertex edits under live zebra and curvature feedback. `edit_cv` therefore has a fast path: the dragged patch re-evaluates on the GPU at `Preview` fidelity, with zebra and curvature Fields, within 16 ms (target). Release writes one Ingot edit that rebuilds normally (ANV).

**Decision D-MEC-14:** Surface quality is a check library over analysis Fields plus a control-vertex drag fast path, not a mode. Capability statements say "surface-quality checks" until control-vertex editing and G3 matching and blending ship together in phase 3. *Why:* checks cover every quality gate, so agents and CI enforce surface quality as they enforce stress limits; claiming Class-A before the modeling loop exists would overstate the product. *Rejected:* a separate Class-A workbench (an island with its own rules); edits only through full rebuilds (too slow for the feedback loop). (revised in round 2)

### SubD and scans

SubD cages are a `Body` representation edited through `anvil::subd_edit`. Features cover primitives, `subd_from_mesh`, face extrusion, loop insertion, bevels, bridges, semi-sharp creases, symmetry and `cage_move` gestures written to source. Rhino 8's `ToNURBS` output is "always G2 in smooth SubD regions", the command lets the user pick G0 to G2 at extraordinary vertices, and warns that forcing G2 "adds bulges or dents".

**Decision D-MEC-15:** `to_nurbs` converts regular regions exactly, packs quad grids into larger patches by default, and defaults to G1 at extraordinary vertices with the deviation from the limit surface reported in the bound. G2 is an explicit option whose shape change is also reported. *Why:* manufacturing and STEP exchange need NURBS, and the conversion must state what it changed. *Rejected:* G2 by default (silently changes shape); SubD only (no AP242 path; MFG needs exact surfaces).

Mixed-representation Booleans let a SubD body join a B-rep part during design, and release checks require conversion when the process demands B-rep.

`scan_to_cad(mesh, intent, freeform)` registers scans with `anvil::align` under a robust loss and segments them by curvature or an optional learned Wasm segmenter. It fits primitives by deterministic RANSAC, writes detected relations as solver constraints, fits faired NURBS elsewhere, and sews a solid with a deviation `Field<Body, Length>`.

Point2CAD (CVPR 2024) reports a new state of the art on ABC with primitives plus an implicit neural representation. Crucible keeps the analytic-first structure and ends freeform regions as NURBS.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Continuity reports | Per-edge reports; scale-relative defaults | `ContinuityNotMet { edge, achieved }` | MEC-O-SF-1 | 1 (G0 to G2), 2 (G3) |
| Basic curves and surfaces | Interpolating and derived curves, profile surfaces, trim and sew | `Degenerate`; `BoundaryNotClosed { gap }` | MEC-O-SK-6, MEC-O-SF-2 | 1 |
| Freeform curves and surfaces | Curves, bridges, offsets, refits; boundary, fill, blend and match to G2 | `NetworkNotCompatible { curves }`, `ToleranceNotMet { achieved }` | MEC-O-SF-2 | 2 |
| Network fitting | Least squares with gaps up to `tol` | `ToleranceNotMet` | MEC-O-SF-2 | 3 |
| Surface-quality checks | Analysis Fields as checks | — | MEC-O-SF-1 | 2, 3 (highlight lines, control net) |
| Control-vertex editing | `edit_cv` with the 16 ms fast path; G3 `match` and `blend_surface` | Fast path falls back to the rebuild | MEC-O-SF-5 | 3 |
| SubD modeling and conversion | Cage edits with stable ids; `to_nurbs` | `NonManifoldCage { edges }`; `ConversionDeviation { max }` | MEC-O-SF-3 | 3 |
| Scan to CAD | Registration to sewn solid | `FitRejected { region, rms }`, `TopologyGap { edges }` | MEC-O-SF-4 | 4 |

## Sheet metal

A sheet-metal part is a `SheetBody`: the folded `Body`, the flat `Body`, a bend table and `SheetParams { thickness, bend_radius, bend_rule, relief, gap }`. Every feature updates both states, as in Onshape, where operations are "automatically represented as a flat pattern".

**Decision D-MEC-16:** The flat pattern is maintained by every sheet-metal feature, not computed at the end. *Why:* designers see flat-pattern errors at the feature that causes them, and a cut drawn in the flat view maps back through the same fold map. *Rejected:* an unfold feature at the end of history (errors appear late and far from their cause).

The neutral fiber lies at K·t from the inside surface. For bend angle θ, inside radius R and thickness t, the bend allowance is BA = θ·(R + K·t), the outside setback OSSB = (R + t)·tan(θ/2) and the bend deduction BD = 2·OSSB − BA. `BendRule` is `KFactor(k)`, `Allowance(table)`, `Deduction(table)` or `Table(BendTable)`; Onshape's documented K factors (0.45 for bends, 0.5 for rolled walls) are defaults until a table overrides them.

A `BendTable` interpolates linearly within its range of material, thickness, radius and angle, and a lookup outside fails with `OutsideBendTable { key, range }`. Press-brake allowance data stays MFG's and COV's in phase 2 (contract 13.4).

| Feature | Contract | Phase |
| --- | --- | --- |
| `sheet_from`, `contour_flange`, `convert_to_sheet` | Base from a profile or path; a converted solid with rips | 2 |
| `flange`, `miter_flange`, `hem`, `jog`, `sketched_bend` | Flanges with length and position rules; closed, open, teardrop and rolled hems | 2 |
| `corner`, `bend_relief` | Closed corners; rectangular, obround and tear reliefs | 2 |
| `in_flat { … }` | Features drawn on the flat state, mapped through the fold map | 2 |
| `form(tool, at, orient)` | Louvers, lances, dimples, beads, extruded holes, bridges with flat footprints | 2 |
| `make_joint`, `make_rip` | Convert between bend and rip | 2 |
| `lofted_bend`, `tab_slot` | Formed or brake transitions with stated deviation; tabs and slots for welded assemblies | 3 |

`flat(sheet)` returns a `FlatPattern` with the outline, `BendLine`s (direction, angle, radius, rule, developed length), forming-tool footprints, grain, material and thickness. Shops mostly program lasers and punches in the machine builder's CAM. `export_flat_dxf(flat, convention)` therefore writes layer conventions as data (cut, bend up, bend down, etch, form marks) with the bend table on the sheet.

Self-clinching nuts, studs and standoffs come with checks on hole size, edge distance, sheet thickness and hardness from the maker's data.

`check::sheet` covers minimum inside radius per material and minimum flange length per die opening from MFG tooling data. It also flags features closer than 2·t + R to a bend, missing reliefs, flat-pattern self-overlap, bends across the grain and forming tools near bends.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Sheet model and bend rules | `SheetBody`; K factor, allowance, deduction and table rules | `OutsideBendTable { key, range }` | MEC-O-SM-1 | 2 |
| Sheet features | Features tabled above, both states updated | `FlangeCollides { faces }`, `UnfoldFailed { bend, reason }` | MEC-O-SM-2 | 2, 3 |
| Flat pattern | `flat(sheet)` through `anvil::unfold` | `NotDevelopable { faces, deviation }` | MEC-O-SM-2 | 2 |
| Flat DXF export | Layer conventions as data | `UnmappedLayer { kind }` | MEC-O-SM-4 | 2 |
| Self-clinching hardware | Catalog data and installation checks | `ClinchRuleViolated { rule, value, limit }` | MEC-O-SM-4 | 2 |
| Sheet checks | `check::sheet` | Findings with fixes | MEC-O-SM-3 | 2 |

## Weldments and structural frames

```
pub feature base_frame() -> Part {
    let sk = sketch3d() { … }                                   // skeleton lines
    let m  = member(sk.edges(role: any), profile: en10365::section("HEA 120"), anchor: Anchor::Centroid)
    let t  = m |> trim(corners: Corner::Miter, gap: 1mm)
    let g  = gusset(t.joints(kind: Tee), size: 60mm, t: 6mm, chamfer: 10mm)
    let w  = weld(t.joints(any), Weld::fillet(a: 4mm, all_around: true, quality: Iso5817(C)))
    part(t + g + end_cap(t.open_ends(), t: 5mm), name: "Base frame").welds(w)
}
```

Members record profile designation, anchor and rotation. Flux therefore models them as Timoshenko or Vlasov beams on `anvil::member_axes`, and sheet guards as shells, instead of meshing the frame as a solid (contract 7.1). Welds carry semantics to MFG (paths, sequence, procedures) and to Flux (fatigue checks); bead geometry is never needed for either.

A `Weld` records type, size, length, pitch, all-around, field weld, process, contour, finish and the imperfection quality level: ISO 5817 level B, C or D, or AWS D1.1 acceptance criteria. The level appears in the symbol's tail and feeds inspection plans; procedure and welder qualifications are MFG's records.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Structural members | Profiles swept along skeleton segments; axes for Flux beams | `ProfileNotFound { designation, near }` | MEC-O-WD-1 | 2 |
| Profile catalogs | EN 10365, EN 10210 and EN 10219 sections [unverified editions]; AISC Shapes Database v16.0 | Pinned data packages | MEC-O-WD-1 | 2 |
| Trims, gussets, end caps | Miter, butt and coped trims with weld gap; plates at recognized joints | `TrimAmbiguous { joint }`; `NoRoom { joint }` | MEC-O-WD-2 | 2 |
| Weld beads | `Weld` records with quality level; `Cosmetic` by default, `Simplified` beads for mass | `WeldPathOpen`, `SizeExceedsThroat` | MEC-O-WD-3 | 2 |
| Weld symbols | AWS A2.4:2020 or ISO 2553:2019 (system A or B) | Missing fields for the standard | MEC-O-WD-3 | 2 |
| Cut list | Bodies grouped by profile, length, end angles and features | Mixed materials in one group | MEC-O-WD-2 | 2 |

## Composites design

A composite Part is a tool surface plus a laminate definition; the laminate is data, and the solid derives from it. MEC owns composite laminates in phase 4 (contract 13.4); constitutive draping and cure simulation are COV's, in phase 5.

```
let lam = laminate(tool: skin.faces(role: outer_mold_line), rosette: rosette(origin: skin.csys("root"), zero: x), plies: [
    ply("P1", carbon_t700_twill, 0deg,   boundary: full),
    ply("P2", carbon_t700_ud,    45deg,  boundary: zone_a, drop_off: 3mm),
], symmetric: true, core: some(core(foam_pmi, 8mm, chamfer: 20deg, region: zone_b)))
let d = drape(lam, method: Drape::Kinematic { seed: p, step: 2mm })
```

Kinematic draping follows the method Creo documents. Drape points are warp–weft crossings on the tool surface, fibres are inextensible so the step is constant, and a seed point and two fixed fibres make the solution unique. Each quadrant drapes independently, and `anvil::drape_kinematic` runs them in fixed order.

**Decision D-MEC-17:** Kinematic draping is the default for design, labelled as a geometric approximation that ignores material mechanics, and ply checks flag shear above the locking angle stored in the `Material`. *Why:* it is fast enough for interactive design and is the method Creo documents; forming simulation needs calibrated material models many users lack. *Rejected:* forming simulation by default (slow, needs calibrated data).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Plies, sequences and zones | Plies with boundary, step, splice and dart; zone stacking with ramp ratios; symmetry and balance checks | `UnbalancedLaminate { zone }` (warning) | MEC-O-CP-2 | 4 |
| Rosettes and cores | Translation, radial, cylindrical or `Field<Faces, Direction>` rosettes; honeycomb and foam cores | `ResolveError` on the rosette frame | MEC-O-CP-1 | 4 |
| Kinematic drape | Fibre directions and shear as Fields per ply; darts and splices | `ShearLimitExceeded { ply, region, max }` with "add dart"; `DrapeGap { ply }` | MEC-O-CP-1 | 4 |
| Solids and ply flats | Tool surface offset by ply thickness with drop-offs; flat ply outlines for MFG | `OffsetSelfIntersection` | MEC-O-CP-1 | 4 |
| Laminate properties | Per-zone ABD matrices for Flux shells | — | MEC-O-CP-2 | 4 |
| Ply book and exchange | Per-ply views, sequence tables, projector data; AP242 composites per the CAx-IF practice [unverified title and version] | Unmappable items reported | MEC-O-CP-2 | 4 |

## Molded and cast part design

**Decision D-MEC-18:** Wall thickness is measured by two methods and both are Fields: ray thickness (inward normal ray to the opposite wall) and rolling-ball thickness (diameter of the largest inscribed sphere touching the point). The GPU only locates candidate regions; the CPU computes every canonical value, so the Fields have grade `Certified`. *Why:* a ray from a rib root can miss the thick junction that the inscribed sphere measures, while rays are cheaper and match caliper readings on plain walls; geometric Fields must not differ by GPU (contract 7.3). *Rejected:* a single method (each misleads in known cases); GPU values refined only near thresholds (bits would differ by device). (revised in round 2)

`check::molding_design` has defaults that MFG material and process data override. Nominal walls stay within the material's range, ribs at most 0.6 of the adjoining wall [unverified rule of thumb], and boss outer diameters about twice the inner. Sharp internal corners are flagged, textured faces need at least 0.5° draft plus the texture allowance, and thickness ratios are bounded.

Fill, pack, cooling and warpage are MFG's in phase 3, and casting simulation in phase 6 (contract 13.4). MEC passes the Part, gate candidates and material.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Draft analysis | `draft_angle(body, pull) -> Field<Faces, Angle>` with positive, negative, vertical and insufficient classes | — | MEC-O-PF-6 | 1 |
| Wall thickness | `thickness(body, method) -> Field<Body, Length>`, ray or sphere, `Certified` | — | MEC-O-MD-1 | 1 |
| Parting line and surface | Lines ranked by undercut area and complexity; extended, ruled or swept surfaces; shut-offs | `NoParting { reason }` | MEC-O-MD-2 | 3 |
| Core, cavity and side actions | `split_mold(body, shrink, parting, block)`; lifter and slide directions | `NegativeDraft { faces }` | MEC-O-MD-2 | 3 |
| Ribs, bosses, snap fits | Parametric features with ratio rules to the nominal wall | `RatioExceeded { rule }` (warning) | MEC-O-MD-1 | 3 |
| Shrinkage and compensation | Anisotropic scale by grade, or `deform(field)` from a warpage Field | `ToleranceNotMet { achieved }` | MEC-O-PF-10 | 3 |
| Cast parts | Machining stock, cores, draft and minimum section per process | `SectionTooThin { region }` | MEC-O-MD-1 | 4 |

## Routing

A `Route` is a 3D path between two ports, a `RouteSpec`, placed fittings and segment bodies. Ports are `CoordSys` values with a connection type, and route points are 3D-sketch unknowns constrained to clearances, supports and orthogonal runs.

```
let r = route(from: pump.port("out"), to: manifold.port("in1"), spec: pipe_spec("ASME-B31.3-CS-150", nps: 2in),
              via: [clamp_a.csys("seat")], style: Orthogonal, min_clearance: 25mm)
r.require(r.bends().all(|b| b.radius >= 1.5 * r.od))
```

Automatic routing searches a voxel visibility graph with A* and smooths the path into the spec's bend rules [unverified source for the method].

**Decision D-MEC-26:** Harness work splits three ways. MEC owns 3D routing, bundle geometry and formboard geometry; ELX owns connectivity, wire tables and electrical checks; MFG owns the harness manufacturing package (formboard drawing, connector face views, cut and strip lists, terminals with crimp data, splices, test netlist, workmanship class). Phase 3 routes use declared bundle diameters, and from phase 4, when GP6 needs connectivity, diameters come from ELX's wire list. *Why:* each tab owns what it computes, and the round 1 drafts claimed the formboard twice and phased it before the wires that size it. *Rejected:* MEC owning the formboard drawing (a manufacturing document); ELX flattening MEC's 3D topology (geometry belongs with the routes).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Route model and tubes | Ports, specs, fittings, segment bodies; bend radius, straights between bends, springback | `NoRoute { blocked_by }`; `BendTooTight { at, radius, min }` | MEC-O-RT-1 | 3 |
| Hose | Minimum bend radius on a routed path; free shape from Flux's rod statics | `BendTooTight` | MEC-O-RT-1 | 3, 4 (free shape) |
| Harness bundles | Branches, clips, grommets; declared diameters, then ELX wire lists; bend radius and clip spacing | `BendTooTight`; `SupportSpacingExceeded { span }` | MEC-O-RT-1 | 3, 4 |
| Bundle shape | Cosserat-rod centreline between frames (`flux::solve_rod`) | `NonlinearDiverged` with the last state | MEC-O-RT-1 | 4 |
| Formboard geometry and lengths | Branches at true length, angles fitted to the board; 3D lengths with service loops | `FormboardOverlap { branches }` | MEC-O-RT-3 | 4 |
| Rigid pipe and HVAC duct | Spec-driven fittings and schedules (ASME B36.10M and B36.19M, EN 10220, SMACNA [unverified editions]) | `FittingNotInSpec { size }` | MEC-O-RT-2 | 5 |

## Large structures, micro scale and soft goods

The scale requirement runs from MEMS to ships and buildings and is met by composition: members, sheets, surfacing checks, flattening and Field-driven geometry, plus a few domain features.

| Domain | Native in std | Interop | Phase |
| --- | --- | --- | --- |
| Steel structures | Building-scale members, bolted plates and fasteners, member Fields from Flux beams | IFC 4.3 (ISO 16739-1:2024) | 5 (GP8) |
| Plates and stiffened panels | Sheets with thickness Fields; stiffeners as members on surfaces | AP242 | 5 |
| MEMS layer stacks | `process_stack(layers)`: deposit, pattern, isotropic or angled etch, release | GDSII and OASIS masks through ELX and `anvil-planar` | 5 (GP7) |
| Ship hulls | Fairness checks; displacement, centres and waterplane from volumes cut by a plane | Offsets tables | 7 (GP13) |
| Building structure | Steel and timber members, not BIM authoring; IFC 4.3 is the latest official version and IFC 5 is in development | IFC exchange with BIM tools | 7 (GP14) |
| Soft goods | Flattened pattern pieces with seams, notches, grain lines and stretch ratios | DXF patterns | 7 (GP16) |

Boundary First Flattening is linear and conformal, with control over boundary length or angle, cone singularities and a cost "about 50x less" than prior boundary-controlled methods, according to its authors. Patterns and `wrap` share it through `anvil::parameterize`, and fabric drape is a Flux shell problem.

**Decision D-MEC-19:** Large structures, MEMS and soft goods arrive in phases 5 to 7 with their golden products (GP7 and GP8 in phase 5, GP13, GP14 and GP16 in phase 7), reusing existing MEC mechanisms plus a few domain features. *Why:* the scale requirement is met by composition, and golden products 1 to 6 need none of these domains. *Rejected:* dedicated workbenches per domain now (they would dilute phases 1 to 4). (revised in round 2)

Out of reach, stated plainly: Crucible does not replace naval architecture suites for stability rules and class approval, BIM authoring for architecture and building services, or TCAD process simulators for MEMS. It exchanges with them through open formats.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Steel structures and panels | Members, bolted plates, stiffened sheets; IFC 4.3 round trip | `UnmappedEntity { kind }` in the translation report | MEC-O-LS-2 | 5 |
| MEMS layer stacks | `process_stack` builds Bodies from layer operations | `LayerUndercut { layer, region }` | MEC-O-LS-4 | 5 |
| Hull fairing and hydrostatics | Fairness checks; hydrostatic properties | `HullNotClosed { gaps }` | MEC-O-LS-1 | 7 |
| Soft-goods patterns | Flattened pieces with seams and stretch ratios | `NotDisk { genus }` with cut suggestions | MEC-O-LS-3 | 7 |

## Tolerancing

### Specification model

Size tolerances are `Tol<T>` values (contract section 5), and `fit(10mm, H7)` returns one from `std::standards::iso286`. Geometric tolerances are records attached to shape aspects, one record per feature control frame.

```
pub record GeometricTolerance {
    characteristic: Characteristic,
    zone: Zone,                       // width, shape, disposition: Symmetric | Unequal(Length) | Offset(Length)
    segments: [Segment],              // composite and multi-segment frames
    modifiers: [Modifier],            // material condition, projected, free state, dynamic profile, translation, statistical, …
    datums: Option<DatumSystem>,      // primary, secondary, tertiary; optional customized frame
    pattern: Option<PatternSpec>,     // CZ, CZR, SZ or SIM with constraints; ASME simultaneous unless separate: true
    indicators: [PlaneIndicator],     // intersection, orientation, direction-feature and collection planes
    size: Option<SizeSpec>,           // TwoPoint, LeastSquares, MaxInscribed, MinCircumscribed, Rank(..); envelope
    target: Query<ShapeAspect>,       // a face set, a feature of size, a pattern, or all over
}
```

```
let a = datum("A", plate.face(role: start_cap))
let b = datum("B", plate.face(role: side(outline.left)))
let c = datum("C", plate.aspect(created_by: locating_pin_hole))
let holes = plate.aspects(created_by: mount_holes)
plate.tolerance(holes, size: fit(8mm, H8))
     .tolerance(holes, position(dia(0.1mm), mmc, datums: [a, b, c.at(mmb)]))
     .tolerance(plate.faces(all), profile(0.2mm, datums: [a, b, c]))
```

`Characteristic` covers the form, orientation, location, profile and runout controls, plus concentricity, coaxiality and symmetry in the ISO dialect only. ASME Y14.5-2018 deleted concentricity and symmetry and added the dynamic profile modifier, which controls form but not size. The record also holds irregular features of size, all-over profiles and statistical tolerancing, and ING turns the commonest misuses into compile errors (D-ING-6).

**Decision D-MEC-27:** GD&T and PMI attributes use Anvil's split policy `Fail`. When a later operation splits a toleranced face, the control fails with `ToleranceTargetSplit { control, pieces }` and offers two fixes: re-target the pieces as one pattern with a combined zone, or select one piece. *Why:* the default `Copy` would silently turn one zone into separate zones, which changes the requirement. *Rejected:* `Copy` (silent change of meaning); `Drop` (silently loses the requirement); `Divide` (meaningless for zones).

### Two dialects, one model

**Decision D-MEC-20:** GD&T has one semantic model with two dialects: ASME (Y14.5-2018, reaffirmed in 2024 and on stabilized maintenance) and ISO GPS (ISO 1101:2017, ISO 5459:2024 for datums, ISO 5458:2018 for pattern and combined zones, ISO 2692:2021 for material requirements, ISO 14405-1:2025 for linear sizes, ISO 8015:2011 for fundamentals, ISO 22081:2021 for general specifications). Each dialect is a validator, a renderer and a default specification operator; a design declares its dialect, and translation produces a Proposal that flags every non-equivalent control. *Why:* the dialects differ in meaning: ASME's size tolerance also controls form, while ISO 8015 meets each tolerance independently unless a relationship is stated [Keyence GD&T basics]. *Rejected:* two separate models (every control written twice); silent conversion (parts made to the wrong requirement); a default by locale. (revised in round 2)

| Dialect default | ASME | ISO |
| --- | --- | --- |
| Regular feature of size | Envelope at maximum material unless independency is noted [unverified: unchanged in Y14.5-2018] | Two-point size without form limitation unless Ⓔ |
| Material requirements | Modifiers on features of size | MMR, LMR and reciprocity on cylinders and parallel plane pairs (ISO 2692) |
| Pattern zones | Simultaneous unless `separate: true` | CZ, CZR or SIM only when written (ISO 5458) |

Validation checks modifiers and datum references against the characteristic and material conditions against features of size. A failure, deleted symbols included, returns `InvalidControl { rule, clause }` with a fix such as "use position, profile or runout instead of concentricity". Stacks and variation read size and envelope from the dialect's default operator.

### Completeness

**Decision D-MEC-21:** Specification completeness is a degree-of-freedom analysis on `anvil::analyze_constraints` plus three coverage rules. Each toleranced aspect gets six small-displacement unknowns relative to its datum frame, minus the displacements that leave its surface class invariant (planar 3, cylindrical 2, spherical 3, prismatic and revolute 1, complex 0) [Homri, Teissandier and Ballu, after Clément's TTRS model], and each control constrains some of the rest. Coverage requires a size control on every feature of size, a form control on every surface (direct, general specification or envelope) and a form control suited to precedence on every datum feature. *Why:* one diagnosis model across sketches, assemblies and tolerancing finds under-specified directions automatically, and degrees of freedom alone call a cylinder with position but no size complete. *Rejected:* rule lists per aspect type (incomplete, no geometric basis); degrees of freedom only. (revised in round 2)

Free unknowns show as arrows, and faces under an ISO 22081 general specification or an ASME general profile note count as controlled. Redundant datum references and conflicting controls are flagged. Sigmetrix GD&T Advisor shows "what features have been completely controlled, partially controlled, or not yet controlled at all"; MEC matches that view and adds the geometric reason.

### Stack-up and variation analysis

| Method | Contract | Phase |
| --- | --- | --- |
| Worst case | Affine `Tol` sum over a closed, signed contributor chain | 1 |
| RSS | Root-sum-square from default or declared distributions, with a Bender-type inflation variant [unverified: factor source] | 1 |
| 1D sampling | Randomized quasi-Monte Carlo over contributor distributions | 1 |
| 3D linear | Sensitivities of measurements to every aspect's small displacements | 2 |
| 3D nonlinear | Per sample: displace aspects within zones, assemble with the shared solver (contact, float, order), measure | 2 |
| Compliant variation | 3D nonlinear plus part compliance from Flux influence coefficients, for sheet-metal and welded assemblies | 2 |
| Tolerance allocation | Zone widths minimizing MFG cost at a target yield | 3 |
| Skin model shapes | Form deviations as `Field<Faces, Displacement>` sampled from constrained random fields | 4 |

```
let gap = measure(asm, distance(cover.face(role: lip), housing.face(role: seat)), along: z)
let v = variation(asm, measures: [gap], samples: 20_000, method: Variation::Nonlinear)
v.require(v.yield(gap, 0.1mm..0.6mm) >= 0.9973)
v.contributors(gap)                      // ranked; grouped where tolerances correlate
```

**Decision D-MEC-28:** MEC owns the default distribution for every statistical call, `std::mech::tol::default_distribution`: uniform within the limits when no process data exist, and normal with the mean shift and spread from Cp and Cpk when an MFG process profile supplies them. ING's `.rss()` and Flux's `std::uq::propagate` use it, and every report prints what it assumed. *Why:* without data a uniform distribution assumes least, while the round 1 drafts used normal ±3σ and uniform for one design, 73% apart in standard deviation; process data bring mean shift, which makes plain RSS unconservative. *Rejected:* normal ±3σ without data (assumes a capable, centered process); one default per tab.

**Decision D-MEC-22:** 3D variation sampling uses scrambled Sobol sequences whose scramble seed hashes the analysis arguments and the input `GeometryId`s, so results are reproducible and independent of names. Yields use smoothed indicators or conditional sampling, and the interval from repeated independent scrambles enters the statistical part of the error budget; linear sensitivities run first and order contributors. *Why:* determinism is a contract principle; quasi-Monte Carlo loses most of its advantage on raw indicator functions, which smoothing restores; one solver keeps float and contact consistent with the assembly model. *Rejected:* Jacobian-only analysis (misses float, contact switching and bonus tolerance); unseeded Monte Carlo; seeds from `EntityId`s (names would steer statistics). (revised in round 2)

Skin model shapes, proposed by Anwer, Schleich, Mathieu and Wartzack (CIRP Annals, 2014), handle form deviations that classical tolerancing handles poorly. Flux consumes MEC's samples as `Field<Faces, Displacement>`.

A tolerance forwarded into two Parts varies independently in each, while code-level stacks keep one symbol per site (ING). With correlation groups, `contributors` reports grouped Sobol indices and Shapley effects from Flux.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| GD&T record and validation | Extended `GeometricTolerance`; datum systems; dialect validators and renderers | `InvalidControl { rule, clause }`; `DatumUnderdefined { dof }` | MEC-O-TL-1, MEC-O-TL-6 | 1 |
| Split targets | Policy `Fail` on GD&T and PMI attributes | `ToleranceTargetSplit { control, pieces }` | MEC-O-TL-6 | 1 |
| Completeness | Degrees of freedom plus size, form and datum-form coverage | Free directions and uncovered aspects listed | MEC-O-TL-2, MEC-O-TL-7 | 2 |
| 1D stacks | Worst case, RSS with inflation variant, 1D sampling | `ChainOpen` | MEC-O-TL-3 | 1 |
| Default distributions | Process data or uniform | `ProcessDataStale { profile }` (warning) | MEC-O-TL-8 | 1 |
| 3D and compliant variation | Sampling with yields and contributors; Flux influence coefficients | `AssemblyFailed { sample }` counted, never dropped | MEC-O-TL-4 | 2 |
| Tolerance allocation | Zone widths at a target yield | `Infeasible { yield }` | MEC-O-TL-4 | 3 |
| Skin model shapes | Form samples as `Field<Faces, Displacement>` | `ContactUnresolved { sample }` | MEC-O-TL-5 | 4 |

## Drawings and model-based definition

### One annotation model

**Decision D-MEC-23:** Semantic PMI lives on the model. Drawings and 3D saved views are two presentations of the same annotation items, and drawing-only annotations are allowed, marked non-semantic and excluded from semantic export. *Why:* one source of truth; ISO 16792:2021 supports a model-only data set or a model plus a digital 2D drawing, and ASME Y14.41 covers annotated models with or without a drawing sheet. *Rejected:* drawing-first annotation (not machine-readable); separate MBD annotations (two truths that drift).

### Drawings

Drawings are Ingot programs, so they diff, merge and review like parts.

```
pub feature bracket_drawing() -> Drawing {
    let p = bracket()
    drawing(standard: Standard::iso(), title: "Bracket") {
        sheet(format: A3, scale: 1:1) {
            let front = view(p, orient: front, at: (120mm, 150mm))
            let aa    = section(front, cut: plane.offset(from: plane.yz, 30mm), label: "A")
            detail(aa, around: circle(point(30mm, 4mm), 6mm), scale: 4:1)
            show_pmi(p, in: [front, aa])
            bom_table(p, at: top_right)
        }
    }
}
```

Every drawing item references model entities by `Query`; an item that cannot re-resolve dangles with a `ResolveError`, never re-attaching elsewhere, and a release check forbids dangling items. Dimensions to view-dependent curves use `view.silhouette(face_query, side: Min | Max, along: dir)` and `view.section_edge(cut, face_query)`, which resolve through the view's projection and fail when the silhouette disappears.

Title-block fields, revision text, release dates and approvers are late-bound release fields: placeholders filled at output and excluded from the Item's definition digest (KLN). Phase 1 reads item numbers and revision labels from release tags and the EBOM view; change-order data joins in phase 2.

**Decision D-MEC-24:** Release drawings use exact hidden-line removal; editing uses a GPU visibility preview that the exact result replaces. *Why:* drawings are contractual documents and must match the model exactly, while the preview keeps editing responsive. *Rejected:* tessellation-based hidden lines for release (chordal error appears on the sheet).

### Revisions, balloons and generated drawings

`revision_markers(drawing, from: Release, to: Release, style: Delta | Cloud)` diffs annotations and views between releases, places a symbol beside each changed item and fills the revision block with change-order number, description and zone. Drafting packages carry ASME Y14.35-2025, which "defines the practices for revising drawings and associated documents", and ISO practice; release drawings are also written as PDF/A [unverified: ISO 19005 part].

Characteristic balloons are an annotation kind that draws MFG's characteristic identities and labels (D-MFG-18, D-MFG-26), beside item balloons tied to BOM lines; IAQG's 9102 revision C added definitions for ballooned design characteristics and ballooned documents. Each release produces the ballooned PDF that inspection plans and first-article reports cite, and tabulated drawings document dash-number families from `family` rows.

**Decision D-MEC-29:** Revision markers are computed from the release diff, never placed by hand, and characteristic balloons draw the labels MFG allocates per characteristic identity, never numbering on their own. *Why:* computed markers cannot miss a change, and one allocator keeps the balloon numbers that inspection reports and supplier records cite stable across revisions. *Rejected:* hand-placed revision clouds (miss changes); balloons numbered by sheet position (change with layout).

`auto_drawing(part, template, rules)` is a deterministic function that writes an editable drawing program:

1. Select the fewest principal views that show every toleranced aspect, plus sections and details where needed.
2. Place each PMI item where its target appears in true shape or as an edge.
3. Dimension untoleranced geometry from the datum system.
4. Lay out views and annotations by deterministic optimization (the `mech-drawing-layout` Wasm component).
5. Check that every PMI item appears exactly once.

The UI shows the output as an edit-plan preview, and agents refine it only in a separate Proposal (UIX).

### Model-based definition

Semantic PMI exports to AP242, linked to B-rep faces through `shape_aspect` and `geometric_item_specific_usage`, per the CAx-IF Recommended Practices for PMI v4.1 (June 2024). The practice reserves semantic PMI for exact geometry, so eligibility is decided per target face. A control on facet faces exports as presentation only, with a translation-report entry, and `check::standards` flags it at design time.

ECO owns the AP242 reader and writer; MEC supplies the model, its mapping table and the PMI oracles.

Targets: a drawing updates in under 1 s after its model rebuild completes; exact hidden lines of a 1,000-part assembly view take under 30 s.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Sheets, title blocks and standards | Formats; late-bound fields; ISO 128 and ASME Y14 packages [unverified editions except Y14.5-2018]; PDF, SVG, DXF, PDF/A; DWG only through a licensed translator | `UnfilledField { field }` at output | MEC-O-DR-4 | 1 |
| Views and hidden lines | Base, projected, auxiliary, full and half sections, details; exact `anvil::project_hlr` with GPU preview | `ResolveError` on a cut or detail anchor | MEC-O-DR-1 | 1 |
| More views | Offset, aligned, removed, revolved and broken-out sections; broken and crop views; exploded, flat and ply views | As above | MEC-O-DR-1 | 2, 4 (ply views) |
| Dimensions and references | All dimension kinds by `Query`; silhouettes and section edges | Dangling item with `ResolveError` | MEC-O-DR-2 | 1 |
| Callouts, symbols and tables | Holes, threads, GD&T, welds; surface texture (ISO 21920-1, ASME Y14.36 [unverified editions]); item balloons; BOM from the EBOM view; hole and general-tolerance tables | Missing fields for the standard | MEC-O-DR-4 | 1, 2 (welds) |
| Revision markers | `revision_markers` from release diffs | `NoBaseRelease` | MEC-O-DR-6 | 2 |
| Characteristic balloons | Labels bound to D-MFG-18 identities; ballooned PDF per release | `UnmappedCharacteristic { id }` | MEC-O-DR-7 | 2 |
| Tabulated drawings and more tables | Family rows; bends, cut lists, plies | `RowFailed { key, error }` | MEC-O-DR-4 | 2 |
| Automatic drawings | Deterministic `auto_drawing` | `UnplacedItems { items }` with reasons | MEC-O-DR-5 | 3 |
| Saved views and AP242 PMI export | `model_view(…)` with a required default; CAx-IF PMI v4.1; eligibility per face | Facet targets exported as presentation, reported | MEC-O-DR-3, MEC-O-DR-8 | 1 |
| PMI import, QIF and data-set completeness | AP242 PMI into the model; QIF 3.0 through MFG; ASME Y14.41 (a 2026 edition listed [unverified]) or ISO 16792:2021, which ISO lists as under revision | Unmappable or missing items listed | MEC-O-DR-3, MEC-O-DR-4 | 2 |

## Design checks

Design checks are `require` predicates packaged as libraries, each returning a `Field` of margins painted on the geometry with typed fixes. MFG owns process DFM, DFA and DfAM checks against machine, printer and shop profiles; MEC owns design-domain and standards checks, with one shared result type.

| Library | Example rules | Phase |
| --- | --- | --- |
| `check::standards` | Thread series and preferred sizes; GD&T validity, completeness and per-face PMI eligibility; drawing completeness; part designations | 1 |
| `check::enclosure` | Clearance to imported boards, keep-ins, connector cut-outs | 1, 2 |
| `check::sheet`, `check::weld` | Sheet rules with MFG tooling minimums; weld access, symbols, quality levels, profile availability | 2 |
| `check::fastening` | Engagement, clearance class, preload range, wrench swing, hole alignment, approved parts | 2 |
| `check::assembly` | Clearance over motion, interference classes, interface compatibility | 2 |
| `check::molding_design` | Draft, wall thickness, rib and boss ratios, undercuts | 3 |

**Decision D-MEC-25:** Design checks return graded Fields with numeric margins, not pass or fail flags. *Why:* agents optimize against margins, and people see where a rule nearly fails. *Rejected:* boolean rule results (no gradient for optimization, no early warning).

**Decision D-MEC-30:** Every mechanical check declares the evidence it accepts. Geometric checks (fits, clearance, interference, thickness, mass) require `Guaranteed` bounds; physics checks accept, at `SignOff`, calibrated `Estimated` bounds from the calibration class they name, and otherwise return `Undecided`. *Why:* Flux reports estimates already multiplied by their class's η99 (D-FLX-24), so what remains is which checks may rest on which classes, and MEC owns the mechanical ones. *Rejected:* `Guaranteed` evidence everywhere (no immersed stress check could pass in phase 1); any `Estimated` bound everywhere (a clearance would pass on an estimate).

| Check family | Evidence | Calibration class |
| --- | --- | --- |
| Fits, clearance, interference, thickness, mass | `Guaranteed` | — |
| Static stress on regularized peaks (GP1, GP2) | Calibrated `Estimated` | Linear elasticity, regularized peak, immersed octree |
| Buckling load factors | Calibrated `Estimated` | Linear buckling, Lanczos or LOBPCG |
| Bolted joints | Calibrated `Estimated`, with the design code's factors as a covering allowance | Bolted-joint forms |

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Check libraries | Graded margin Fields with fixes | `Error(Failure)` on a missing input | MEC-O-CK-1, MEC-O-CK-2 | 1 to 3 |
| Evidence declarations | Evidence and calibration class per check | `Undecided { needed }` | MEC-O-CK-3 | 1 |

## Human factors

The validity envelope is geometric reach, fit and vision only; strength, fatigue and musculoskeletal loading need Flux biomechanics models with their own envelopes. Anthropometry follows ISO 7250-1:2017, and population datasets are licensed data packages.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Manikins | Kinematic chains with joint limits, scaled to a percentile or an individual | `DatasetMissing { population }` | MEC-O-HF-1 | 5 |
| Posture | Inverse kinematics on the shared solver with a comfort cost | `PostureInfeasible { target, limit }` | MEC-O-HF-1 | 5 |
| Reach, clearance and vision | Reach envelopes as Bodies; tool access; view cones, obscuration, legibility | — | MEC-O-HF-1 | 5 |
| Posture scores | Methods such as RULA [unverified] as check libraries | — | MEC-O-HF-1 | 5 |

## State of the art

Figures in the last column are targets unless quoted.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Feature language | Standard features in the user-facing language, with published source | Onshape FeatureScript | All `std::mech` features in Ingot with typed roles (D-MEC-1) | Golden products built from std only; contract 13.3 rebuild rows |
| Code-CAD idioms | Text, hull, Minkowski sum, offset and twisted extrusion as core operations | OpenSCAD (`text`, `hull()`, `minkowski()`, `linear_extrude(…, twist, …)`) | All in phase 1 except Minkowski sums (phase 2) | Every cheat-sheet idiom expressible and exact |
| Sketch solving | Structural decomposition before numerical solving (Zou et al. 2022); least-squares drags (SolveSpace) | Siemens D-Cubed 2D DCM, "the most widely adopted 2D geometric constraint solver"; FreeCAD planegcs on Eigen | Dulmage–Mendelsohn blocks, LM on `linalg`, Krawczyk bounds, continuation (D-MEC-3 to D-MEC-5) | SketchGraphs replay: 99.5% re-solved on the recorded branch; 2,000-entity drag step under 8 ms |
| Constraint diagnosis | Witness configurations with Zou and Feng's minimality corrections | D-Cubed diagnostics (not public) | Modular rank, rational kernel vectors, minimal conflicts | Known-rank suite of 100 to 2,000 unknowns: 100% exact |
| Assembly solving | One system over SE(3) cluster unknowns on manifolds; continuation for motion | Siemens D-Cubed 3D DCM; Onshape mate connectors | Shared solver (D-MEC-11); dynamics in Flux (D-MEC-12) | Mobility counts; closed-form linkages; 1,000 mates in under 100 ms |
| Blends | Rolling-ball and setback vertex blends; law radii on tangent chains | Parasolid, used by Plasticity; OCCT's fillet builder, with linear and law radii and per-vertex failures | ANV's staged program, opt-in implicit fallback (D-MEC-2) | Re-fillet benchmark: 95% at phase 1, 97% at phase 2, OCCT on the same corpus |
| Direct editing | Synchronous, history-free edits that keep related geometry consistent | Siemens synchronous technology in Solid Edge and NX | Solver-based face motions, rules in source, blend regrowth (D-MEC-9) | Relation recognition precision and recall on ABC; 95% of held-out seeded edits succeed |
| Sheet metal | Flat pattern maintained by every feature; per-bend tables | Onshape sheet metal | Same model, no extrapolation (D-MEC-16); flat DXF | Developed lengths equal closed forms to 10⁻⁹ relative |
| Surface quality | G2 and G3 analysis, zebra and highlight lines, live control-vertex feedback | CATIA and Alias-class tools [unverified]; Plasticity Studio xNURBS | Analysis Fields, checks and the 16 ms drag path (D-MEC-14) | Known-order surface pairs: zero misclassifications |
| SubD to NURBS | G2 regular regions, a choice at extraordinary vertices, packing | Rhino 8 `ToNURBS`; OpenSubdiv | G1 default with reported deviation (D-MEC-15) | Limits within 10⁻⁹ relative of OpenSubdiv |
| Scan to CAD | Hybrid analytic and neural fitting (Point2CAD, CVPR 2024) | Point2CAD on ABC | Analytic-first with intent snapping and NURBS | Synthetic ABC scans: at least Point2CAD's reported accuracy |
| Draping | Kinematic fishnet draping | Creo Composite Design | Deterministic kinematic drape (D-MEC-17) | Hemisphere and cylinder shear within 0.5° |
| Flattening | Boundary First Flattening | BFF reference implementation | `anvil::parameterize` with BFF | Distortion and time within 10% of the reference |
| Mate inference | Learned joint prediction (JoinABLe, 79.53% against a reported human 80%) | JoinABLe | Optional Wasm ranker | Fusion 360 Gallery joint split: 80% top-1 |
| GD&T coverage | Degrees of invariance per surface class in the GPS model (ISO 17450-1:2011) | Sigmetrix GD&T Advisor's coverage view | DOF analysis plus coverage rules (D-MEC-21) | Known free directions and seeded gaps: 100% found, no false findings |
| 3D tolerance analysis | Nonlinear sampling with assembly behaviour; skin model shapes (Anwer et al. 2014; Schleich and Wartzack 2016) | 3DCS and Siemens VSA [unverified] | Sensitivities, then scrambled Sobol through the solver (D-MEC-22) | Literature assemblies; 20,000 samples of a 50-part stack in under 60 s |
| Semantic PMI | AP242 semantic PMI with validation properties (CAx-IF PMI v4.1) | CATIA, NX, Creo and SOLIDWORKS on NIST cases | Native AP242 PMI, per-face eligibility (D-MEC-23) | NIST CTC, FTC, STC and HTC: 100% of semantic items |
| Hidden-line removal | Exact projection with visibility from exact geometry [unverified attribution] | Drafting in NX and SOLIDWORKS [unverified] | Exact for release, GPU preview (D-MEC-24) | No disagreement with dense ray casting farther than 1 µm from silhouettes |
| Wall thickness | Ray and inscribed-sphere thickness | Commercial molding analysis [unverified] | Both as `Certified` Fields (D-MEC-18) | Error under 1% on analytic parts; identical bits with and without a GPU |
| Gear geometry | ISO 21771-1:2024 with flank modifications | Specialist gear software [unverified] | Spline flanks within 0.1 µm plus semantics | Flank points against ISO 21771-1 formulas |
| Solver linear algebra | Rank-revealing QR and SVD per block | Eigen in planegcs; faer (runtime dispatch, no rank-revealing sparse mode) | Canonical `linalg`; faer only in `CpuIsa` | Bit identity across the canonical class; no slower than Eigen on SketchGraphs |

Deviations, stated: homotopy continuation finds all solutions, but Crucible tracks only the seeds' branch, because the Zou review notes its cost and editing needs one predictable answer. OndselSolver, an open assembly and multibody solver, is LGPL-2.1 and was archived on 1 March 2025, so it serves as a reference only.

## Platform notes

- **Numerics.** Residuals use `detmath`, and solver algebra uses `linalg` without FMA (contract 7.3), so sketches, mates and thickness Fields are bit-identical across the canonical class at any thread count.
- **Browser.** Without cross-origin isolation the solver runs blocks sequentially, and the 16 ms browser drag target assumes one thread; heavy evaluations follow contract 9's browser memory rules.
- **Fonts and tables.** Text and engraving use bundled fonts, never OS lookup. CSV import never uses the OS locale; a comma-decimal file needs `table(…, decimal: Comma)`.
- **Output.** PDF, SVG, DXF and PDF/A writers are pure Rust in `io/`; printing goes through `apps/platform`.
- **GPU paths.** Thickness candidates, zebra, hidden-line and control-vertex previews and interference culling have CPU paths; canonical values never come from the GPU.
- **Offline and Tier 2.** Standards and catalog data are vendored into air-gapped installs with their licences. Tablets edit dimensions, parameters and mates, view every Field and drag sketches by touch through the same `api` stream.

## Interfaces with other subsystems

[[DIAGRAM: MEC data flow. Boxes: Skeletons and interface records → Parts (sketches, part features, sheet metal, weldments, composites, molded parts, lattices) → Assembly (mates, fasteners, routes, BOM-only items) → three outputs: Flux (typed joints, mass properties, member axes and mid-surfaces, laminates, skin-model samples), MFG (FlatPattern, HoleSpec, ThreadSpec, Weld, plies, core and cavity, characteristics, harness geometry), and Drawings and model views → AP242 and QIF in io/. Under all boxes, one bar labelled anvil::solve_constraints and analyze_constraints feeding sketches, mates, live rules, completeness, routing and posture.]]

MEC uses the operations that ANV's capability tables mark for it, with ANV's names and phases, and no MEC feature ships before the operations it calls.

| Subsystem | MEC consumes | MEC provides |
| --- | --- | --- |
| ANV | Operations with roles and `Query` use; certified constraint solving; blend stages and targets; leaf-preserving joins; `member_axes`, `mid_surface`; control-vertex previews; attribute split policies | Role vocabularies and `FeatureRole` attributes; constraint semantics; glyph outlines |
| ING | Builder blocks and `Expr<T>`; `#[interface]`, `#[configuration]`; `family`; keyed iteration; `Tol<T>` symbols; typed aspects. ING's `std::mech::fits` and `std::tol::default_distribution` are `std::standards::iso286` and `std::mech::tol::default_distribution` here | Sketch, GD&T and pattern semantics; the default distribution |
| KLN and `repo` | Phase 1 item numbers, revision labels, `InWork` and `Released`, EBOM; phase 2 change orders; the definition digest without late-bound fields; approved-parts policy; cost-driven drag previews | Parts with item numbers, family rows, BOM-only items, cut lists, after-assembly operations for the MBOM |
| FLX | Multibody and rod solvers; beams and laminated shells; calibrated estimates (D-FLX-24); influence coefficients; deformed-shape Fields | Typed joints, bounded mass properties, contact candidates, preload, member profiles, ABD matrices, drivers, skin-model samples |
| COV | Materials with yield, locking angle and process windows; constitutive draping in phase 5 | Laminate and part data for envelopes |
| MFG | Process profiles, tooling, process capability, cost models, characteristic identities (D-MFG-18), the harness package, process checks | `FlatPattern`, hole, thread and weld semantics with quality levels, ply flats, core and cavity, gears, PMI, balloons, harness geometry |
| ELX | Harness connectivity and wire lists (phase 4); board outlines and connector frames; MEMS masks | Enclosure interfaces and checks, connector frames, routes, bundle geometry and lengths |
| ECO | IDF and STEP board readers; AP242 and QIF translators; data packages | GD&T mapping for AP242; weld, hole and composite semantics; flat DXF conventions |
| UIX, AGT and `api` | Painted Fields, freedom arrows, `Fix` buttons, drag streams that write seeds; Inspect and Edit methods | `SolveReport`, `ContinuityReport`, check Fields, `auto_drawing`, view-scoped references, revision markers |

| Wasm component | Purpose | Phase |
| --- | --- | --- |
| `mech-lattice` | Cell-family generator emitting strut graphs or tapes for `anvil::lattice` | 1 |
| `mech-route-search`, `mech-drawing-layout`, `mech-explode-planner`, `mech-mate-ranker` | Route search, drawing layout, disassembly planning, learned mate ranking | 3 |
| `mech-scan-segmenter` | Learned point-cloud segmentation | 4 |

Learned Wasm components ship fixed weights and run deterministic CPU inference.

## Oracles

All oracles live in the protected `oracles/mech/` directory. Held-out subsets (20% of each generated or replayed set, and every golden-product drawing) are never shown to agents.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| MEC-O-SK-1 | Sketch solving | SketchGraphs replay in 2D and a synthetic 3D set re-solve from perturbed seeds within the certified bound, on the recorded branch |
| MEC-O-SK-2 | Diagnosis | Systems of 100 to 2,000 unknowns with known dependencies match exact rational rank; conflict sets are minimal |
| MEC-O-SK-3 | Inequalities | Systems with known feasibility are classified correctly |
| MEC-O-SK-4 | Determinism | Identical bits across the canonical class and with re-randomized names; 1,000 random edits never change branch without `BranchFlip` |
| MEC-O-SK-5 | Drag latency | Sketches of 200 and 2,000 entities meet the drag targets |
| MEC-O-SK-6 | Curves | Spline, NURBS and helix evaluation and curve length match high-precision references |
| MEC-O-SK-7 | Custom constraints | Values and derivatives match a reference interpreter and finite differences |
| MEC-O-SK-8 | Certified positions | Near-tangent and near-singular sketches give `Guaranteed` boxes containing high-precision references, or `IllConditioned` |
| MEC-O-SK-9 | Helper names | Every helper sub-entity resolves in sketches and as a role on extrusions over 100 random edits |
| MEC-O-PF-1 | Profile features | Volumes, areas and face counts equal closed forms; roles stable over 100 random edits |
| MEC-O-PF-2 | Sweeps, lofts, helices | A circle swept along a helix is a tube; frames continuous; springs and threads match analytic surfaces |
| MEC-O-PF-3 | Offsets and shells | Certified minimum wall distance equals the thickness |
| MEC-O-PF-4 | Holes and threads | Sizes match their tables; NIST hole test cases rebuild |
| MEC-O-PF-5 | Blends | Rolling-ball distance and G1 at contact edges hold; the re-fillet benchmark meets ANV's targets |
| MEC-O-PF-6 | Draft | Draft Fields meet targets on drafted faces |
| MEC-O-PF-7 | Patterns and copies | Counts, keys and transforms correct; removing one point renames no other copy; mirrored copies have distinct ids |
| MEC-O-PF-8 | Booleans | Volume identities hold on random ABC pairs |
| MEC-O-PF-9 | Direct edits | Declared relations kept, adjacent blends regrown, remodeled references matched |
| MEC-O-PF-10 | Deform and wrap | Deviation from analytic maps within the reported bound; developable wraps keep arc length exactly |
| MEC-O-PF-11 | Derived parts | Pinned and bumped sources give the expected diff Proposals |
| MEC-O-PF-12 | Families and configurations | Rows type-check and report per row; `#[configuration]` gives the expected 150% BOM |
| MEC-O-PF-13 | Lattices | Relative density matches analytic values; kept B-rep faces keep their attributes |
| MEC-O-PF-14 | Rebuild budget | Golden-product rebuilds after first, middle and last edits meet contract 13.3's rows |
| MEC-O-PF-15 | Gears | Flank points match ISO 21771-1; undercut and tip-thickness limits hold |
| MEC-O-PF-16 | Reference geometry | Constructors re-resolve under edits; shape-derived frames carry their note |
| MEC-O-PF-17 | Text, emboss, engrave | Regions match font outlines; depth and arc length exact on planes and cylinders |
| MEC-O-PF-18 | Hull and Minkowski sum | Results equal exact rational hulls and closed-form convex sums |
| MEC-O-AS-1 | Mates | Known Grübler–Kutzbach mobility, redundant and accidental cases included; rigid and flexible subassemblies agree where both apply |
| MEC-O-AS-2 | Kinematics | Slider-crank and four-bar positions, velocities and accelerations equal closed forms |
| MEC-O-AS-3 | Interference | Analytic overlap volumes; NIST CTC 02 and 04 fits classified correctly |
| MEC-O-AS-4 | Large assemblies | A synthetic 100,000-Instance assembly meets the open and orbit targets |
| MEC-O-AS-5 | Exploded views | Automatic explosion of the golden gearbox is collision-free |
| MEC-O-AS-6 | Fasteners | Selected lengths equal hand-computed cases and table values |
| MEC-O-AS-7 | Mate inference | Top-1 accuracy on the Fusion 360 Gallery joint split meets the target |
| MEC-O-AS-8 | Interfaces | Every seeded provider–consumer mismatch is reported |
| MEC-O-AS-9 | BOM-only items and approved parts | BOM lines carry the Item's unit; a non-approved part fails unless a waiver names it |
| MEC-O-AS-10 | Dynamic clearance | Intervals contain the minimum from dense sampling of closed-form mechanisms |
| MEC-O-AS-11 | Enclosure checks | KiCad's STEP export of an open board, and its IDF export once ECO's reader ships, give the expected findings |
| MEC-O-AS-12 | Assembly-level features | Derived Parts and after-assembly operations give the same assembled geometry |
| MEC-O-SF-1 | Continuity | Surface pairs of known order are classified correctly at scale-relative thresholds |
| MEC-O-SF-2 | Surfaces | Boundary, network and fill surfaces interpolate boundaries and meet edge targets |
| MEC-O-SF-3 | SubD | Limits match stored OpenSubdiv outputs; `to_nurbs` deviation and continuity as reported |
| MEC-O-SF-4 | Scan to CAD | Synthetic ABC scans recover primitive types, parameters and Chamfer distance |
| MEC-O-SF-5 | Control-vertex drags | Frames within 16 ms; the committed edit equals the full rebuild |
| MEC-O-SM-1 | Bend rules | Developed lengths equal the formulas across angles, radii and K factors |
| MEC-O-SM-2 | Flat patterns | Every flat pattern refolds to the folded body within the entity tolerance |
| MEC-O-SM-3 | Sheet checks | Every seeded defect in GP4's guards is found |
| MEC-O-SM-4 | Flat DXF and clinch hardware | DXF re-imports with layers per convention; seeded clinch violations are found |
| MEC-O-WD-1 | Member sections | Area and second moments from geometry equal catalog values within 0.5% |
| MEC-O-WD-2 | Trims and cut lists | Mitered lengths and end angles equal closed forms |
| MEC-O-WD-3 | Weld symbols | Rendered symbols, quality level included, parse back into identical records |
| MEC-O-CP-1 | Draping | Hemisphere and cylinder drapes match analytic shear |
| MEC-O-CP-2 | Laminates | ABD matrices equal hand calculations; symmetry and balance checks correct |
| MEC-O-MD-1 | Thickness | Fields on plates, tubes and ribs match analytic answers |
| MEC-O-MD-2 | Mould split | Core, cavity and part sum to the block; no negative draft |
| MEC-O-RT-1 | Routes | Lengths and bend radii on known paths equal closed forms |
| MEC-O-RT-2 | Fittings | Fitting selection matches spec tables |
| MEC-O-RT-3 | Formboards | Flattened branch lengths equal 3D lengths without overlaps |
| MEC-O-LS-1 | Hydrostatics | Analytic hull forms match closed-form displacement, centres and waterplane properties |
| MEC-O-LS-2 | IFC structures | IFC 4.3 members, plates and openings round-trip |
| MEC-O-LS-3 | Soft goods | Flattened seams match 3D lengths within the declared stretch |
| MEC-O-LS-4 | MEMS stacks | Stacks with known etch geometry give the analytic Bodies |
| MEC-O-TL-1 | Dialect validation | Rule suites from Y14.5-2018 and ISO 1101 examples are judged correctly |
| MEC-O-TL-2 | Degrees of freedom | Known free directions are reported exactly |
| MEC-O-TL-3 | 1D stacks | Worst case and RSS equal hand-computed values |
| MEC-O-TL-4 | 3D variation | Deterministic across runs and classes; intervals cover reference values |
| MEC-O-TL-5 | Skin models | Sampling statistics match the specified random fields |
| MEC-O-TL-6 | Extended GD&T record | Every NIST FTC control and ISO 5458 example is expressible and round-trips; split targets fail with both fixes |
| MEC-O-TL-7 | Coverage rules | Seeded missing size, form and datum-form controls are all found |
| MEC-O-TL-8 | Default distributions | Reports print assumptions; with process data, shift and spread follow Cp and Cpk |
| MEC-O-DR-1 | Views and hidden lines | Exact hidden lines agree with high-resolution ray casting on ABC |
| MEC-O-DR-2 | Associativity | Under edits every item, silhouette dimensions included, re-resolves or reports a `ResolveError` |
| MEC-O-DR-3 | PMI exchange | NIST CTC 01 to 05, FTC 06 to 11, the 2023 simplified and 2024 hole cases rebuild, export to AP242 and match NIST's files item by item |
| MEC-O-DR-4 | Drafting rules | Line types, text, symbols and tables pass on held-out golden drawings |
| MEC-O-DR-5 | Automatic drawings | Every PMI item appears exactly once; reruns are bit-identical |
| MEC-O-DR-6 | Revision markers | Two changed dimensions give exactly two markers and one revision row |
| MEC-O-DR-7 | Balloons | One changed dimension changes one balloon's content and no labels; first-article rows equal the balloon set |
| MEC-O-DR-8 | PMI eligibility | Controls on facet faces export as presentation and are reported |
| MEC-O-CK-1 | Check coverage | Every defect seeded into golden products 3 to 5 is found, none on clean versions |
| MEC-O-CK-2 | Fixes | Every fix compiles and clears its finding |
| MEC-O-CK-3 | Evidence | Checks given evidence below their declaration return `Undecided` with the needed bound |
| MEC-O-HF-1 | Human factors | Segment lengths match the dataset; reach envelopes match analytic chains |

## Phasing

Gate contributions follow contract 13; per-capability phases are in the capability tables, and shared physics phases follow contract 13.4.

| Phase | MEC's contribution to the gate |
| --- | --- |
| 0 | Certified solver core and modular-rank diagnosis on `linalg`; role conventions; data-package format; MEC corpus in the determinism suite (MEC-O-SK-4) |
| 1 | GP1: named sketch helpers, profile features, holes and threads, stage 1 blends, shells, draft, keyed patterns, reference geometry, push-pull, basic mates and interference, GD&T with split policy, 1D stacks, drawings from release tags and the EBOM view, AP242 PMI. GP2: lattices joined leaf-preserving, text, emboss, hull, printed threads |
| 2 | GP3: gears, shafts, fasteners with approved parts, kinematics, 3D variation and completeness. GP4: weldments with quality levels, sheet metal with flat DXF, compliant variation, revision markers and balloons. Also freeform surfaces to G2, direct edits, stage 2 blends |
| 3 | GP5: molded part design, control-vertex editing with G3 surfaces, SubD, routing on declared diameters, automatic drawings, mate inference, tolerance allocation |
| 4 | GP6: composite laminates (contract 13.4), harness bundles from ELX wire lists, formboard geometry, scan to CAD, skin model shapes, cast parts |
| 5 | GP7 MEMS layer stacks; GP8 steel structures through IFC 4.3; pipe and duct routing; human factors |
| 7 | GP13 hull fairing and hydrostatics; GP14 timber members through IFC; GP16 soft-goods patterns |

## Open questions

1. **Seeds and diff noise.** Writing solved seeds back after a drag changes many literals. Should seeds live in a layout section merged by last writer, or stay inline at rounded precision? ING and KLN must agree.
2. **Standards licensing.** Can open-source std ship tabulated ISO, ASME, DIN and AISC values, or must they be separately licensed data packages? Legal review is due before phase 1.
3. **Implicit blend fallbacks at release.** Which processes accept a released part with an implicit region? Proposal: MFG process rules decide, and a release check enforces them.
4. **Benchmark access.** Some kernel and CAD licences restrict published benchmarks [unverified]; blend and hidden-line comparisons may need Open CASCADE and exported results only.
5. **Dataset terms.** SketchGraphs states that sketch creators hold copyright, and the Fusion 360 Gallery data has its own licence. Can oracles vendor these sets, or must they fetch them by content hash?
6. **Drawing edits.** Should editing a driving dimension on a drawing write model source through its `Query`? It is convenient but makes drawings a geometry editor.
7. **Dialect conversion.** Is a Proposal-based ASME-to-ISO translation worth building, given that many controls have no exact equivalent?
8. **Calibration classes.** D-MEC-30 names two physics classes for phase 1 (regularized stress, buckling) and bolted joints for phase 2; FLX must confirm 300 held-out samples for each (FLX open question 1).
9. **Findings applied in part.**
    - R2-19: form sampling per dialect needs skin model shapes (phase 4); until then sampling displaces ideal features, with ASME's envelope bounding size and orientation jointly.
    - R4-14: characteristic balloons follow MFG's characteristic extraction into phase 2; phase 1 drawings carry item balloons only.
    - R1-10, R1-36, R2-09, R2-36, R6-11: MEC applies its part (canonical solver algebra, grouped contributors, the drawing target after rebuild, fallback notes, contract capacity rows); ANV, PLT, FLX and UIX own the rest.
    - R3-30, R3-31: ING owns `Tol<T>` symbol keying and the `Scalar` flavors (D-ING-20); MEC states the consequences in Tolerancing and Sketching.
    - R4-29: ELX phases IDF and STEP board import in phase 1, while ECO's revision puts the readers on an early 1.x train in phase 2. `check::enclosure` runs in phase 1 against boards imported as STEP assemblies either way; the consistency pass should settle the reader phase.
    - R4-16, R1-37: the ISO 19005 part for PDF/A and the source of the Bender inflation factor are unverified.

## Contract change requests

None.

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
