# Anvil geometry kernel (ANV)

Anvil is one kernel over four representations (exact B-rep, implicit, mesh and subdivision surface) that share one tolerance model, one provenance model and one operation contract. Topological decisions come from exact or certified predicates; constructions are floating point with per-entity tolerances and a reported `ErrorBound`. Every operation is versioned, returns `HistoryRecord`s and gives bit-identical results on every Tier 1 CPU; the GPU may prune, order and preview work but never decides a result.

## Scope and kernel structure

### What Anvil owns

| Anvil owns | Anvil does not own |
| --- | --- |
| Geometry types, evaluation and intersection for curves, surfaces, implicit expressions, meshes and subdivision cages | Physics, error estimation and refinement decisions (Flux) |
| The `Body` value in all four representations, its topology, tolerances, attributes and encoding | Design intent, feature semantics and entity selection syntax (Ingot, std) |
| `EntityId`, `HistoryRecord`, lineage and the resolution of provenance `Query`s against them | Caching, scheduling and cancellation policy (Kiln) |
| Every geometric operation, including volume meshing, mesh adaptation and geometric constraint solving | Sizing and metric Fields (Flux produces them; Anvil consumes them) |
| Representation conversions with `ErrorBound`s | File formats such as STEP AP242 and 3MF (`io/`), which call Anvil to build and heal Bodies |
| The `GeometryQuery` service for immersed and fitted simulation | Rendering (UIX); Anvil supplies display tessellations and GPU evaluation kernels |

The constraint solver sits here because the Mechanical tab decided it (D-MEC-3): it needs Anvil's evaluators inside every Newton iteration. Volume meshing sits here for the reasons in D-ANV-12.

### Crates and dependencies

| Crate | Contents | Depends on |
| --- | --- | --- |
| `anvil-geom` | Numbers and predicates (exact, filtered, interval, affine), `ErrorBound`, `Tolerance`, `EntityId`, curves and surfaces with evaluation, local intersection solvers, approximation and fitting | PLT `detmath`, `simd`, `gpu`, `runtime`; `sha2` |
| `anvil-topo` | Cellular B-rep topology, per-entity tolerances, attributes, `HistoryRecord`, lineage, `Query` resolution, the body checker, the Body encoding for B-reps | `anvil-geom` |
| `anvil-mesh` | Surface meshes, volume meshes (simplicial, hex-dominant, prismatic, curved high-order), subdivision cages and limit evaluation, mesh algorithms | `anvil-geom`, `anvil-topo`, `flux-field` |
| `anvil-implicit` | Expression DAG, tapes, interval, affine and gradient evaluators, sparse brick cache, the compiled path to Flux's kernel IR, implicit meshing | `anvil-geom`, `anvil-topo`, `anvil-mesh`, `flux-field` |
| `anvil-ops` | The `Body` enum, the operation registry and every operation contract, Booleans for every representation pair, conversions, `GeometryQuery` | all of the above |

**Decision D-ANV-1:** Anvil keeps the five contract crates in the order `anvil-geom` → `anvil-topo` → `anvil-mesh` → `anvil-implicit` → `anvil-ops`, places `flux-field` between `anvil-topo` and `anvil-mesh` as the Flux tab proposes, and compiles every Anvil crate with `forbid(unsafe_code)`. SIMD and GPU work goes through the PLT `simd` and `gpu` crates, and GPU kernels are WGSL or CubeCL sources passed to those crates. *Why:* subdivision cages are polygon meshes, so they live in `anvil-mesh` without a sixth crate; implicit expressions may reference meshes and B-reps as leaves, so `anvil-implicit` sits above both; the `ErrorBound` type must sit in the lowest crate so geometry-level code can report errors (CCR-ANV-1). *Rejected:* a separate `anvil-subd` crate (one more boundary for a type that shares the mesh half-edge structure); `unsafe` SIMD inside Anvil (the contract confines `unsafe` to SIMD, GPU and FFI crates, and PLT already owns them).

### Kernel rules

1. **Bodies are immutable values.** An operation reads Bodies and returns new Bodies. Unchanged storage is shared, so a local edit costs memory proportional to the change.
2. **Operations are pure.** Output depends only on arguments, input Bodies, Fields and the operation's behavior version. There are no clocks, no randomness and no dependence on thread count.
3. **Budgets are counted, never timed.** Each operation carries fuel limits in deterministic units (subdivision depth, iterations, element counts). Exhausted fuel returns `BudgetExceeded`; Kiln's cancellation returns no result rather than a different one.
4. **Decisions are certified.** A topological decision (which side, which order, coincident or not) comes from an exact predicate, or from a certified interval predicate resolved by the tolerance model. A floating-point guess never decides topology.
5. **Approximations state their error.** Every conversion, fit and approximate construction returns an `ErrorBound` with a guarantee kind.
6. **The GPU proposes; the CPU decides.** GPU results prune work with exact integer tests, order it, or feed previews. A canonical output is identical with and without a GPU.
7. **No silent fallbacks.** A fallback method (for example an implicit blend when the rolling-ball blend fails) runs only when the caller opted in, and the result says so.
8. **Each question is asked once.** Within an operation, every predicate about a pair of entities is computed once and memoized, so later phases cannot contradict earlier ones. Manifold's mesh Booleans follow the same rule: each computation builds on earlier ones instead of asking one question two ways [Manifold wiki].

## Body and representations

### The Body value

A `Body` is one immutable value with five parts:

| Part | Meaning |
| --- | --- |
| `repr` | One of `BRep`, `Implicit`, `Mesh`, `SubD` (shared, reference-counted storage) |
| `frame` | A translation on a fixed grid, near the Body's bounding-box center; coordinates are stored relative to it (rotations belong to Instance placements) |
| `resolution` | The Body's smallest meaningful length ρ, scale-relative by default (see the tolerance model) |
| `regions` | The 3-cells of the Body, each `Material` (with its material reference), `Void` or `Exterior`; a fluid domain is a material region whose material is a fluid |
| `meta` | Encoding version, lineage summary, per-face conversion error bounds (D-ANV-21), and representation-specific flags |

A Part wraps a Body with identity, as the contract states. Anvil never stores item numbers or names; it stores region material references and kernel attributes only.

### The four representations

| Representation | What is exact | Typical sources | Strengths | Limits |
| --- | --- | --- | --- | --- |
| `BRep` | Analytic and NURBS surfaces and curves, procedural surfaces (offset, swept, blend, subdivision limit), facet faces | Features, STEP import, conversions | Exact dimensions, faces and edges to select, GD&T, drawings, CAM | Intersections and blends are hard; imported data needs healing |
| `Implicit` | A typed expression DAG whose zero set is the boundary; leaves may be exact distances to B-reps and meshes, or Fields | Lattices, topology optimization, field-driven design, offsets, shrinkwraps | Booleans cannot fail and offsets are robust; lattices with millions of cells stay small | No explicit edges; distance may be a bound rather than exact; evaluation costs grow with expression size |
| `Mesh` | Combinatorial topology (manifold by construction); vertex coordinates carry a precision ε | Scans, 3D printing, tessellations, simulation | Fast, simple, universal exchange | Piecewise linear; curvature only approximated |
| `SubD` | A Catmull-Clark cage with semi-sharp creases; the limit surface is defined exactly | Industrial design, organic forms | Smooth freeform with few controls | G1 at extraordinary vertices; class-A work needs conversion |

### Representation lattice and mixed operations

The contract requires mixed-representation Booleans without conversion. Anvil achieves this with inclusions that lose nothing:

1. A Mesh is a B-rep whose faces are facet faces (one face per face group, triangles as geometry). Parasolid's Convergent Modeling already operates on "a mix of facet B-rep surfaces and classic B-rep surfaces" in one model [Parasolid convergent modeling].
2. A SubD is a B-rep whose faces carry exact subdivision-limit surfaces, one per cage face.
3. A B-rep or Mesh is an Implicit leaf: its exact signed distance, with sign from the generalized winding number so imperfect inputs still classify robustly [Jacobson et al. 2013; Spainhour and Weiss 2025].

The result of a mixed operation is the join of its operands in this lattice: Mesh ⊕ Mesh is a Mesh; Mesh ⊕ BRep, SubD ⊕ BRep and Mesh ⊕ SubD are B-reps whose faces keep their native geometry; anything ⊕ Implicit is an Implicit. The caller may request another output with `into:`, which runs an explicit conversion and returns its `ErrorBound`.

**Decision D-ANV-2:** Mixed-representation operations return the least representation in the lattice Mesh ⊂ BRep, SubD ⊂ BRep, BRep ⊂ Implicit that contains both operands without loss. *Why:* no operand is approximated, faces from exact operands stay exact and keep their EntityIds, and any later conversion is explicit and bounded. *Rejected:* converting everything to meshes first (destroys exact faces and dimensions); converting everything to implicits (loses edges and face identity for B-rep users); refusing mixed operations (violates the contract decision).

[[DIAGRAM: Representation lattice. Four boxes: Mesh, SubD, BRep (sub-labels: exact faces, facet faces, subdivision-limit faces), Implicit (sub-labels: expression DAG, B-rep leaves, mesh leaves, Field leaves). Solid arrows labelled "lossless inclusion": Mesh → BRep, SubD → BRep, BRep → Implicit, Mesh → Implicit. Dashed arrows labelled "convert with ErrorBound": BRep → Mesh (Guaranteed), Implicit → Mesh (Guaranteed), Implicit → BRep (Guaranteed for facets, Estimated for fitted faces), Mesh → BRep fitted (Estimated), BRep → SubD (Estimated), SubD → BRep NURBS (Guaranteed).]]

### Fidelity levels

Each operation runs at one of two fidelities, the geometry side of the contract's interactive and sign-off modes. `Exact` produces the canonical result that Kiln caches, checks consume and releases record.

`Preview` may use coarser tolerances, cheaper surrogates (for example an implicit offset in place of a blend) and the GPU; its outputs carry `Guarantee::Estimated`, are marked as previews, and never reach checks, exports or the shared cache. Flux's interactive mode may consume preview geometry for a sub-second update and then carries the preview's bound in its geometry error; sign-off consumes only `Exact` geometry.

Kiln streams previews first and replaces them with exact results, which serves the contract's coarse-drag-preview target of 100 ms. A preview never changes an exact result, because exact evaluation never reads preview outputs.

## Numbers, tolerances and predicates

### Number kinds

| Kind | Used for | Determinism |
| --- | --- | --- |
| `f64` | All stored coordinates and parameters; constructions | IEEE 754 basic operations are correctly rounded in Rust, and its strict IEEE semantics rule out implicit contraction and reassociation [RFC 3514] |
| Expansions (Shewchuk) | Exact signs of linear predicates | Exact |
| `Interval` | Certified enclosures for curved geometry and implicit evaluation | Exact rules, see below |
| `Affine` (reduced affine forms) | Tighter enclosures for correlated expressions (implicits, patch bounds) | Exact rules |
| Big integers and rationals | Exact rank in `analyze_constraints`, rare exact constructions in tests | Exact |
| `u32`/`u64` | Indices, counts, grid correlation (D-MFG-12) | Exact |

Lengths are meters and angles are radians inside Anvil. Ingot `Quantity` values are converted at the operation boundary, where the compiler has already checked dimensions.

### Resolution, frames and scale

Every Body has a resolution ρ, the smallest length the kernel distinguishes for that Body. It is scale-relative and a power of two:

ρ_scale(D) = 2^(⌈log₂ D⌉ − 30), where D is the diagonal of the Body's bounding box in meters.

Coordinates are stored relative to the Body frame, which sits on the frame-grid point nearest the bounding-box center. For any Body larger than 2 µm, coordinates stay below D in magnitude, so the spacing of `f64` values is at most 2^(⌈log₂ D⌉ − 53) and ρ is at least 2²³ times that spacing. That factor is the numeric headroom every construction may consume before it affects a decision. Below 2 µm the frame offset dominates the coordinates, so smaller Bodies lose one bit of headroom per halving of D (at least 2¹³ remain for a 1 nm Body).

Anvil's code contains no absolute length constant other than the frame grid, so a Body whose frame is at the origin behaves identically when scaled by any power of two (oracle ANV-O-SCALE-1).

An operation's result takes ρ_out = max(ρ of every input, ρ_scale(D_out)). An explicit `resolution:` argument may lower ρ to the floor 2^(⌈log₂ D⌉ − 40).

| Body | D | Default ρ | Growth cap τ_cap = 2¹⁰ρ | Floor |
| --- | --- | --- | --- | --- |
| MEMS accelerometer die | 0.5 mm | 2⁻⁴⁰ m ≈ 0.91 pm | ≈ 0.93 nm | 2⁻⁵⁰ m |
| Watch gear | 10 mm | 2⁻³⁶ m ≈ 15 pm | ≈ 15 nm | 2⁻⁴⁶ m |
| Machined bracket (golden product 1) | 0.1 m | 2⁻³³ m ≈ 0.12 nm | ≈ 0.12 µm | 2⁻⁴³ m |
| Drone (golden product 6) | 1 m | 2⁻³⁰ m ≈ 0.93 nm | ≈ 0.95 µm | 2⁻⁴⁰ m |
| Wind turbine blade | 100 m | 2⁻²³ m ≈ 0.12 µm | ≈ 0.12 mm | 2⁻³³ m |
| Ship hull | 300 m | 2⁻²¹ m ≈ 0.48 µm | ≈ 0.49 mm | 2⁻³¹ m ≈ 0.47 nm |

A Body frame is a translation whose coordinates are integer multiples of 2⁻²⁰ m (about 0.95 µm). Differences between two frame origins are then exact in `f64` while every coordinate satisfies |origin| < 2³² m, so rebasing a point from one frame to another costs one rounding. A part modeled at georeferenced coordinates 500 km from the origin keeps the precision of a part at the origin.

**Decision D-ANV-3:** Resolution is per Body, scale-relative (2⁻³⁰ of the bounding-box diagonal, rounded to a power of two) and stored with frames on a fixed 2⁻²⁰ m grid. *Why:* the contract requires nanometers to hundreds of meters with scale-relative tolerances; ρ is not a global tolerance but a per-Body floor, and every decision uses the tolerances of the entities involved; a fixed absolute value such as the default tolerance of about 5·10⁻⁹ m that Parasolid used in 1995 [Jackson 1995] is coarse for MEMS and wastes headroom for ships; power-of-two values keep scaling exact and make ρ change only when D crosses a power of two. *Rejected:* one global tolerance (forbidden by the contract and wrong across scales); ρ derived from the exact diagonal (changes with every edit and makes near-degenerate decisions flicker); per-assembly resolution (couples unrelated parts).

Operations across Bodies of very different scale follow three rules:

1. **Same Body.** A Boolean of a 1 µm comb drive tool with a 300 m plate takes the plate's ρ (0.48 µm). Features smaller than λ = 2⁴ρ fail with `BelowResolution { size, resolution, floor }`; the fix lowers the plate's resolution toward its floor (0.47 nm), where the headroom is still at least 2¹³.
2. **Across Instances.** Distance, clearance and interference between Instances run in the frame of the Instance with the smaller ρ, after world-space culling with conservative boxes. Decisions use max(ρ_a, ρ_b) plus entity tolerances.
3. **Never silently.** A result whose ρ exceeds an input's ρ reports `Note::ResolutionCoarsened { from, to }`.

### Per-entity tolerances

Each vertex, edge and face carries a tolerance τ ≥ ρ. Entities built exactly by Anvil have τ = ρ, which is not stored.

Imported, healed or approximated entities store τ explicitly. Following Parasolid's local-tolerance model [Jackson 1995], incident entities satisfy τ(vertex) ≥ τ(edge) ≥ τ(face), and a tolerant edge keeps the parameter-space curves of its faces inside a tube of radius τ around one master curve.

| Quantity | Symbol | Default | Rule |
| --- | --- | --- | --- |
| Resolution | ρ | 2^(⌈log₂ D⌉ − 30) | Per Body, see above |
| Entity tolerance | τ_x | ρ | Monotone along incidence; never below ρ |
| Growth cap | τ_cap | 2¹⁰ρ | An operation may raise a tolerance to at most max(τ of the involved input entities, τ_cap); beyond that it fails with `ToleranceGrowth { entity, needed, cap }` |
| Healing limit | τ_heal | max(10 × the file's declared uncertainty, 2¹⁰ρ) | Up to 2²⁰ρ with an explicit argument |
| Minimum size | λ | 2⁴ρ | Smaller slivers merge within tolerance or fail with `BelowResolution` |
| Mesh precision | ε | Accumulated rounding bound per Mesh | As in Manifold [Manifold wiki]; exceeding τ_cap triggers `PrecisionExhausted` with a remesh fix |

### Formal semantics of a toleranced Body

For an entity x with stored geometry G_x and tolerance τ_x, its tolerance region is N(x) = { p : dist(p, G_x) ≤ τ_x }. For a face, G_x is the trimmed surface; for an edge, its curve; for a vertex, its point. A Body is valid when four conditions hold:

1. **Incidence.** For each vertex v of edge e, the curve endpoint lies in N(v). For each edge e of face f, the image of the coedge's parameter curve on f's surface lies in N(e), and so does e's curve where e stores one.
2. **Separation.** For any two entities x and y, every point of G_x within τ_x + τ_y of G_y lies in the tolerance region of an entity in the shared closure of x and y. Entities with disjoint closures are therefore farther apart than τ_x + τ_y. This excludes self-intersection up to tolerance, including faces that share a ring edge but cross elsewhere.
3. **Combinatorics.** Loops are closed and consistently oriented; each bounded region is enclosed by closed shells; the radial order of faces around every edge agrees with the certified angular order; the Euler–Poincaré relation holds for every shell.
4. **Regularity.** Curves and surfaces are regular on the domains in use, except at declared surface singularities such as cone apexes; parameter curves stay in their surface's domain or its periodic cover.

The body checker (`anvil::check_body`) verifies all four with certified computations and returns every violation with the entities involved. Every operation's oracle runs it on outputs.

### Certified decisions

A topological question about curved geometry reduces to the sign or size of a quantity q, such as a distance or an oriented angle. Anvil computes an enclosure [lo, hi] of q and decides against the tolerance τ that applies (the sum of the entities' tolerances for coincidence, as in Jackson 1995):

1. If hi ≤ τ, the entities are **coincident** (or the point is **on**).
2. If lo > τ, they are **separated**, with a certified sign.
3. Otherwise Anvil refines the enclosure by subdivision or interval Newton steps, up to the operation's fuel.
4. If refinement reaches width below ρ/2⁸ and the enclosure still straddles τ, Anvil declares coincidence and grows the entities' tolerances to hi, within the growth cap. If the cap or the fuel is exhausted first, the operation fails with `Ambiguous { entities, enclosure }`.

Step 4 replaces a floating-point guess with a recorded tolerance growth (`Note::ToleranceGrown` on the result). It is deterministic because the enclosure computation has a fixed operation order. Merged entities take max(τ_x, τ_y, certified Hausdorff bound), which covers both, as Parasolid does when joining entities of different tolerance [Jackson 1995].

**Decision D-ANV-4:** Topological decisions on curved geometry use certified enclosures with a three-way tolerance rule and recorded tolerance growth; linear decisions use exact predicates. *Why:* the contract mandates adaptive exact predicates for topology and floating-point constructions; exact algebraic predicates on NURBS and procedural surfaces are impractical, while certified enclosures plus explicit tolerance growth never contradict themselves and leave an audit trail. *Rejected:* fixed epsilon comparisons (inconsistent decisions are the classic cause of invalid B-reps); exact algebraic arithmetic for curved geometry (degrees explode for blends and offsets); silent tolerance growth without a cap (tolerances creep until models break).

### Exact and filtered predicates

| Family | Inputs | Method | Used by |
| --- | --- | --- | --- |
| Linear predicates | `f64` points: orient2d, orient3d, incircle, insphere, comparisons of distances and dot products | Static filter, then interval filter, then exact expansion arithmetic [Shewchuk 1997] | Meshes, polygon arrangements, planar sketches, convex hulls |
| Indirect predicates | Implicit points: line-plane, three-plane and two-point linear-combination intersections | Filtered evaluation on the generating primitives, so the point is never rounded [Attene 2020; Diazzi et al. 2023] | Mesh arrangements, mesh Booleans, constrained Delaunay tetrahedrization |
| Certified curved predicates | Curves, surfaces, implicit expressions | Interval and affine enclosures, Bernstein bounds, Krawczyk or interval Newton, with the decision rule above | B-rep Booleans, blends, classification, intersections |

Shewchuk's adaptive predicates do only as much work as a correct sign needs, and his code is public domain [Shewchuk 1997]. Attene's indirect predicates take the primitives that define a constructed point and resolve the predicate exactly with filters and expansions, and he reports that they beat lazy exact representations [Attene 2020]. Anvil generates the filtered Rust code for both families from symbolic predicate descriptions at build time and checks the generated code into `anvil-geom`.

**Decision D-ANV-5:** Anvil implements its own predicate generator for linear and indirect predicates, porting Shewchuk's public-domain method and Attene's indirect-predicate scheme. *Why:* the generator emits safe Rust with canonical evaluation order, and the same source drives native and Wasm builds; indirect predicates make mesh arrangements exact without rational coordinates. *Rejected:* binding C++ libraries (FFI, platform variance, licenses: Attene's CDT code is GPL or LGPL by build option [MarcoAttene/CDT]); rational arithmetic throughout (on a 1.2-million-triangle Boolean, arbitrary-precision mesh arrangements took 141 s where EMBER took 34 ms [EMBER 2022]).

### Intervals without rounding modes

Rust treats inline assembly that changes the floating-point control state as undefined behavior [RFC 3514], so Anvil cannot switch rounding modes. Intervals use error-free transformations instead. TwoSum and TwoProduct compute the exact rounding error of a sum or product, and division and square root use the exact remainders a − q·b and a − s².

When the error is nonzero, the bound moves one step outward with `next_up` or `next_down` (stabilization release unverified). TwoProduct uses `mul_add` where the CPU has FMA and Dekker splitting elsewhere. Both give the exact error term, so the bits are identical on every target.

Transcendental functions come from the PLT `detmath` crate, which is correctly rounded on every Tier 1 target. Their interval extension widens the correctly rounded result by one ulp on each side. Rust's own `sin` and `exp` have "non-deterministic" precision by documentation [Rust f64 docs], so Anvil never calls them.

### Symbolic perturbation

Exact ties inside mesh algorithms, such as four cocircular points in a constrained Delaunay triangulation, are broken by Simulation of Simplicity [Edelsbrunner and Mücke], as Lévy does for unique triangulations [Lévy 2024]. The perturbation order is the canonical vertex order of the encoded Body (face-group EntityId, then local index), never memory order.

Boolean semantics of touching or coplanar faces are not left to perturbation. The cellular arrangement classifies coplanar facets explicitly, then regularizes.

The results match the cases Manifold documents for its perturbation rule: touching cubes merge in a union, an equal-height difference cuts through, and A − A is empty [Manifold wiki]. These three cases are Boolean oracles.

## B-rep data structures

### Cellular topology

Anvil uses one cellular boundary representation for manifold solids, sheets, wires, non-manifold bodies and multi-region bodies. A manifold solid is the common special case and gets fast paths, but it is not a separate type.

| Entity | Holds | Invariants |
| --- | --- | --- |
| Region | Role: `Exterior`, `Material(MaterialRef)` or `Void`; its shells | Exactly one `Exterior` region per Body; every bounded region is enclosed by shells |
| Shell | A connected set of face sides bounding one region | Closed for the outer boundary of a bounded region; open shells are sheets, free in `Exterior` or embedded in a region |
| Face | Surface reference, sense, loops, and two sides (front, back), each bounding one region | Front and back regions are equal only for sheet faces: a free sheet in `Exterior`, or an embedded sheet (a crack) inside a region |
| Loop | A cycle of coedges on one face | Outer loop first; material lies left of the loop in (u, v) when the sense is positive |
| Coedge | One use of an edge by a loop: next, previous, radial next, sense, parameter curve | Radial cycle ordered by certified dihedral angle around the edge |
| Edge | Curve reference, parameter interval, tolerance, start and end vertex (none for ring edges) | Every radial cycle alternates face sides consistently with the regions it separates |
| Vertex | Point and tolerance | τ(vertex) ≥ τ of every incident edge |

Radial cycles carry the non-manifold cases. An edge with four coedges joins two solids along a line; a wire edge has no coedges; an acorn vertex has no edges. A multi-material part is one Body with several `Material` regions that share internal faces, so the interface between a steel insert and its overmolded polymer is one face with steel on one side and polymer on the other.

**Decision D-ANV-6:** Anvil uses one cellular B-rep (regions, shells, faces with two sides, loops, coedges with radial cycles, edges, vertices) for all B-rep bodies, with material assigned per region. *Why:* multi-material parts, conformal multi-region meshing for Flux and mixed Booleans that keep internal interfaces all need shared faces between regions; one structure avoids converting between a manifold kernel and a non-manifold kernel. *Rejected:* a manifold-only half-edge B-rep with non-manifold cases in a side structure (two code paths and lossy conversions); a combinatorial 3-map for every Body (heavier for the common single-solid case).

Two topology rules reduce naming noise:

1. **No seam edges.** Loops on periodic surfaces live in the surface's universal cover, with an integer winding per loop. A full cylindrical face between two circular edges has two loops and no seam. STEP export inserts seams where the target schema requires them.
2. **No degenerate edges.** Surface singularities, such as a sphere pole or a cone apex, are interior singular points of the face, not edges. They remain selectable as points through `face.singular_points()`.

*Why:* seams and degenerate edges are artifacts of a parameterization. They create entities that users never modeled, and they move when parameters change, which breaks queries.

### Geometry types

Every geometry type implements exact evaluation with derivatives to third order (G3 analysis needs them), a certified bound over any parameter box, and conversion to NURBS with a stated error. Procedural types also keep a cached NURBS approximation with a certified `ErrorBound`. Algorithms use it for bounds and seeding, then refine on the exact definition.

| Curve | Exact definition | Phase |
| --- | --- | --- |
| Line | Point and unit direction | 0 |
| Circle, ellipse | Center, axes, radii | 0 (circle), 1 (ellipse) |
| Parabola, hyperbola | Vertex frame and focal parameters | 1 |
| Helix | Axis, radius, pitch, handedness, taper angle | 2 |
| NURBS | Degree ≤ 25 (a design limit; imports above it are approximated with a reported error), clamped or periodic knots, positive weights | 0 |
| Planar offset | Base curve, signed distance, plane normal | 1 |
| Intersection | Two surfaces and a branch; fitted B-spline and two parameter curves; refinement by projection onto the true intersection | 1 |
| Blend spine and contact | The spine is the intersection of two offset supports; each contact curve is the spine's foot-point curve on one support; both procedural with fitted B-splines | 1 |
| Curve on surface | Surface and a 2D curve in its parameter space | 0 |
| Polyline | Points; used by facet faces | 0 |

| Surface | Exact definition | Phase |
| --- | --- | --- |
| Plane | Frame | 0 |
| Cylinder, cone, sphere, torus | Frame and radii; self-intersecting tori (lemon and apple) allowed with their singular points marked | 0 |
| General quadric | Ellipsoid, elliptic paraboloid and hyperboloid, elliptic cylinder and cone | 2 |
| NURBS | Degree ≤ 25 in each direction, rational, periodic flags | 0 |
| Offset | Base surface and signed distance; invalid where the distance reaches a principal radius of curvature, which `check_body` reports | 1 |
| Linear extrusion, revolution | Curve and direction, curve and axis | 0 |
| General sweep | Profile, path, frame rule (fixed, Frenet, rotation-minimizing, guide curve, fixed binormal), scale and twist laws as Fields | 1 |
| Rolling-ball blend | Two supports, spine, radius law (constant or Field), cross-section (circular, conic with ρ value, curvature-continuous) | 1 (constant), 2 (variable) |
| Vertex blend | n-sided patch over a setback polygon [Várady publication list] | 1 (three edges, equal radii), 3 (any valence) |
| Subdivision limit | Cage face, its one-ring and crease data | 3 |
| Facet | A face group of triangles | 1 |

**Decision D-ANV-7:** Offset, intersection, sweep, blend and subdivision-limit geometry stays procedural, with exact evaluation plus a cached, certified NURBS approximation. *Why:* procedural geometry is exact, small and regenerates from its inputs, so a blend between an offset and a cylinder does not accumulate approximation error at each step; the cached approximation keeps the polynomial machinery (Bernstein bounds, subdivision) available. *Rejected:* converting every construction to NURBS immediately (error compounds across features and models grow); procedural-only geometry (no cheap bounds for intersection).

**Decision D-ANV-8:** B-rep face geometry is always parametric; implicit surfaces never appear as B-rep faces. *Why:* every B-rep algorithm (trimming, tessellation, blending, export) relies on (u, v) domains; mixed operations with implicits already produce `Implicit` Bodies by the representation lattice. *Rejected:* implicit face geometry (every surface-surface pair would need an implicit-parametric variant, and STEP cannot carry it).

### Parameter spaces and trimming

Each surface declares its domain, periodicity per direction and singular points. Each coedge stores a parameter curve on its face's surface.

Parameter curves are reparameterized to share the edge curve's parameter: for every t, |S(pc(t)) − C(t)| ≤ τ_edge. This "same parameter" rule lets tessellation place shared edge vertices at the same t from both sides, which makes the display mesh watertight by construction.

Point-in-face classification works in parameter space with exact predicates on polyline proxies and certified refinement near the boundary. On periodic surfaces it counts winding in the universal cover. Trimming loops must be closed within the vertex tolerances, non-self-intersecting beyond the edge tolerances, and nested consistently; `check_body` verifies all three.

### Attributes

Design attributes are typed plain values attached to entities by Ingot features, such as `HoleSpec`, `ThreadSpec`, `Weld` and surface finish (the Mechanical tab keys them by `EntityId` on a Body). Anvil stores them in a side table keyed by `EntityId`. Each attribute class declares how it propagates, and Anvil applies the policy inside every operation.

| Event | Policies | Default |
| --- | --- | --- |
| Split | `Copy`, `Drop`, `Divide(by: area or length)` | `Copy` |
| Merge | `KeepIfEqual`, `Union`, `Drop`, `Fail` | `KeepIfEqual` |
| Transform | `Transform` (for vector-valued attributes), `Keep` | `Keep` |
| Delete | Dropped, with the attribute listed in the `Deleted` record | — |

Attribute changes appear as `Modified { aspects: Attributes }` history. A `Fail` merge policy turns a merge into `AttributeConflict { entities, class }`, which suggests an explicit choice in the feature.

### Memory layout

| Layer | Layout | Why |
| --- | --- | --- |
| Builders inside an operation | Arenas with generational keys (slot index plus version), like `slotmap`, which prevents reuse of stale keys [slotmap docs] | Operations insert and delete freely without dangling handles |
| Finished Body | One persistent search tree per entity kind, keyed by row order; leaves hold up to 1,024 rows in structure-of-arrays layout, each leaf an `Arc` slice | SIMD-friendly scans; a new Body version shares every untouched leaf with its predecessor |
| Row order | Morton code of the entity's box center on the Body's grid of cell size 2¹⁰ρ (2²⁰ cells per axis), then `EntityId` | Spatial locality, and an order that depends only on content and scales with the Body |
| Leaf boundaries | Content-defined: a row ends a leaf when a hash of its EntityId has its low 8 bits zero, with minimum and maximum leaf sizes | The same content always produces the same leaves, whatever edit history led to it, so leaf hashes are canonical |
| Handles | (leaf, slot) pairs, valid only within one Body version | Cheap; never stored and never exposed through `api` |
| Geometry | One pool per geometry type; NURBS headers plus flat knot and homogeneous control-point buffers (x·w, y·w, z·w, w) | Batched evaluation; identical geometry is stored once |
| Acceleration | Per-face boxes and normal cones in columns; a bounding-volume hierarchy built on demand with binned surface-area heuristic, fixed bin count and `EntityId` tie-breaks | Deterministic culling for intersection, distance and classification |

A local edit, such as one fillet on a 10,000-face part, rewrites only the leaves it touches and their paths to the roots. Kiln can therefore keep many Body versions in memory, which the 2-second rebuild target relies on.

### Persistence and versioning

The Body encoding is a canonical binary form. Its content hash in the CAS is a SHA-256 Merkle hash: each leaf's canonical bytes are hashed, each section hashes its leaf hashes in row order, and the header hashes the section hashes. Re-hashing after a local edit therefore costs time proportional to the change, and equal content always gives equal hashes.

1. **Header.** An 8-byte magic number, encoding version (major, minor), representation, frame, resolution and a section table.
2. **Sections.** Topology tables, geometry pools, `EntityId`s, tolerances, attributes, lineage summary, accumulated `ErrorBound`, and representation-specific sections (mesh buffers, subdivision cage, implicit DAG). Each section has a type tag, a length and a required flag.
3. **Canonical values.** Little-endian fixed-width integers; IEEE binary64 floats with −0.0 normalized to +0.0; no NaN or infinity; rows in the canonical order above.
4. **Compression.** Storage may compress leaves; hashes cover uncompressed bytes, so compression settings never change identity.
5. **Text form.** A line-oriented canonical text form with hexadecimal floats, used by oracle golden files and review diffs.

Versioning follows four rules:

1. A minor version adds optional sections or columns with defaults. Older readers skip unknown optional sections.
2. An unknown required section fails with `EncodingError::Unsupported { needed }`, never a partial read.
3. A major version changes layout. Anvil keeps a reader for every major version ever released and upgrades on read in memory.
4. Writers write only the current version, except the adapter that feeds retired operation versions running as Wasm components, which writes the major version each component was built with.

Body encodings are derived artifacts, rebuilt from Ingot source and pinned operation versions, so readability is the only long-term duty. Releases may still embed encodings next to STEP AP242 files for long-term archiving and viewer-only access.

**Decision D-ANV-9:** The Body encoding is a canonical, sectioned binary form with content-defined leaves and a SHA-256 Merkle content hash, with read support for every major version forever. *Why:* Kiln and the CAS key on content hashes, so the encoding must be canonical; Merkle hashing over content-defined leaves keeps hashing and storage proportional to each edit; sections give additive evolution without breaking old readers; a text twin makes oracle goldens reviewable. *Rejected:* serializing in-memory structs directly (layout changes would change hashes); a self-describing generic format such as JSON for primary storage (slow, not canonical without extra rules); STEP as native storage (loses procedural geometry, tolerances, lineage and attributes).

## Implicit representation

An `Implicit` Body is a typed expression DAG f: ℝ³ → ℝ whose region f ≤ 0 is the solid. Implicits carry lattices, field-driven geometry, topology-optimized shapes, shrinkwraps and every mixed operation with an implicit operand. nTop shows the industrial value of this representation and calls it lightweight for fast iteration [nTop whitepaper].

It also shows the cost of changing a kernel's numerics: implicit geometry regenerated in its 5.0 kernel may differ slightly from earlier results [nTop 5.0 notice]. Anvil's behavior versions exist to prevent exactly that.

### Expression DAG

| Node family | Nodes | Lipschitz rule |
| --- | --- | --- |
| Coordinates and constants | x, y, z, typed constants with units | 1, 0 |
| Arithmetic | +, −, ×, ÷, neg, abs, sqrt, square, min, max, clamp, select | Interval bound of the local gradient |
| Transcendental | sin, cos, exp, ln, atan2, pow (from `detmath`) | Interval bound of the derivative |
| Primitives with exact distance | half-space, sphere, box, rounded box, cylinder, cone, torus, capsule, ellipsoid (bound only) | 1 |
| CSG | union (min), intersection (max), difference, smooth union and intersection (polynomial blend with radius k) | 1 if inputs are 1-Lipschitz |
| Transforms | rigid, uniform scale (exact), non-uniform scale, shear, twist, bend, taper, Field-driven warp | Product with the bound of the inverse Jacobian |
| Distance operators | offset (f − d), shell (\|f\| − t/2), round | Lipschitz constant unchanged; an offset of an `Exact` input is `Bound(1)` with the correct zero set; other kinds need redistancing (below) |
| Domain operators | linear and polar repetition with cell clamping, mirror, extrude and revolve of a 2D implicit | 1 for exact repetitions |
| Lattices | TPMS families (gyroid, Schwarz P, Schwarz D, diamond, Neovius, Lidinoid), strut graphs with node blends, stochastic foams | Bound per family |
| Leaves | B-rep or Mesh Body (exact signed distance), Field leaf (`Field<Body, Length>` or density), cached brick grid | 1 for distance leaves; from Field metadata otherwise |

The DAG is hash-consed: identical subexpressions are stored once, and the DAG's hash is its content hash. Constants are part of the hash, so a parameter edit produces a new DAG that shares every unchanged subgraph.

### Distance kinds and Lipschitz bounds

Every node carries a distance kind, propagated statically:

| Kind | Meaning | Allowed uses |
| --- | --- | --- |
| `Exact` | f equals the signed distance to the boundary | All operations, including offsets by any amount |
| `Bound(L)` | f has the correct sign and \|f(p)\| ≤ L·dist(p, boundary) | Classification, Booleans, sphere tracing with step \|f\|/L, meshing; offsets only after redistancing |
| `Lipschitz(L)` | f has the correct sign and \|f(p) − f(q)\| ≤ L·\|p − q\| | As `Bound(L)` |
| `SignOnly` | Correct sign; no slope bound (C0 warps that break Lipschitz continuity) | Classification by interval arithmetic only; slow queries are reported |

Min of exact distances is exact outside and a bound inside; max is the reverse. Smooth unions of 1-Lipschitz inputs remain 1-Lipschitz but not exact. A transform with Jacobian J has local Lipschitz constant bounded by the interval enclosure of ‖J⁻¹‖ over the query box.

Offsets need exact distance, because offsetting a bound moves the surface by the wrong amount. `anvil::offset` on a non-exact implicit therefore redistances first.

It builds the narrow band |f| < |d| + margin in the brick cache, computes exact distances to the certified zero set, and returns the offset with a `Guaranteed` bound equal to the zero-set certification error plus the band interpolation error. The caller may instead accept `approximate: true`, which offsets the bound directly and reports `Guarantee::Estimated`.

**Decision D-ANV-10:** Implicit nodes carry a statically propagated distance kind and Lipschitz constant, and operations that need exact distances redistance in a narrow band instead of trusting bounds. *Why:* lattices, smooth blends and warps rarely yield exact distances; tracking the kind lets classification and meshing stay certified while offsets stay correct; this is the condition Lipschitz pruning relies on [Barbier et al. 2025]. *Rejected:* assuming every implicit is a true SDF (offsets and clearances become silently wrong); restricting implicits to exact-distance constructions (excludes smooth blends, TPMS and Field-driven geometry).

### Evaluation

Expressions compile to a tape: a register-allocated linear program over the DAG, as in Fidget, which register-allocates its tape into bytecode with 256 registers [Fidget]. Anvil evaluates the same tape with four evaluators:

| Evaluator | Input | Output | Use |
| --- | --- | --- | --- |
| Point (batched) | Points in blocks of 8 lanes | f(p) | Sampling, ray stepping, meshing |
| Gradient | Points | f and ∇f by forward-mode differentiation | Normals, dual-contouring vertices, Newton steps |
| Interval | Boxes | Enclosure of f and, optionally, ∇f; min/max choices | Culling, classification, local Lipschitz bounds, pruning |
| Affine (reduced) | Boxes | Affine form of f | Tighter enclosures where intervals overestimate |

Interval evaluation records which branch of each min and max is active over the box, and the tape is then pruned to the active branches for that region. Keeter's renderer reports average tape length dropping about 17× for tiles and 216× for subtiles on a text benchmark [Keeter 2020]. Smooth blends defeat choice-based pruning, which made Keeter's bear-head sculpt the slowest case (about 88 ms per frame at 1024³) [Keeter 2020].

Anvil therefore also prunes smooth blends: in a polynomial smooth union with radius k, a branch whose lower bound exceeds the other branch's upper bound by at least k cannot affect the result in that region. Anvil bounds each branch over a cell from one evaluation at the cell center plus the branch's Lipschitz constant; Lipschitz pruning builds its region-equivalent pruned trees on the same property, for hard and smooth CSG [Barbier et al. 2025].

Interval bounds can be loose near surfaces, and Keeter suggests reduced affine arithmetic as the remedy [Keeter 2020]; Sharp and Jacobson report that variants of affine arithmetic are highly effective for range analysis [Sharp and Jacobson 2022]. Anvil runs interval arithmetic first and switches a box to reduced affine arithmetic when the interval is ambiguous and its width exceeds four times the box diameter times the node's Lipschitz bound.

**Decision D-ANV-11:** The canonical CPU evaluator is a SIMD bytecode interpreter with interval and Lipschitz tape pruning; a compiled path lowers tapes to the shared kernel IR that Flux uses and emits Wasm SIMD modules, with bit-identical results. *Why:* Fidget measures a 31× JIT advantage for brute-force evaluation but only about 25% (6 ms versus 4.6 ms) once pruning is used [Fidget], and the fastest Prospero result is a NEON interpreter at 0.29 ms [Prospero]; an interpreter runs where JIT is impossible (iPadOS) and inside the browser; reusing Flux's kernel IR gives one code generator with D-FLX-8's fixed operation order. *Rejected:* a native JIT per architecture (a second CPU code path, an attack surface, and no gain once pruned); per-expression shader compilation for the GPU (Keeter measures 1 to 7 ms of CPU tape generation per model change, while CUDA kernel generation in the Prospero challenge took about 2 seconds [Prospero]).

The compiled path compiles tapes at run time into Wasm SIMD modules, which the PLT Wasm runtime turns into native code where JIT is allowed and interprets with Pulley where it is not (iPadOS, per the PLT tab). GPU evaluation follows the massively parallel rendering scheme: a WGSL tape interpreter evaluates tiles hierarchically, splitting each into 64 children (two warps) with interval classification and per-tile pruning [Keeter 2020].

WGSL names three floating-point types, `f32`, `f16` (behind the `f16` extension) and AbstractFloat [WGSL]; it offers no runtime 64-bit float [unverified]. GPU results therefore serve previews, culling and work ordering only; certified answers come from CPU `f64` evaluation of the same tape.

### Sparse brick cache

Repeated queries on one implicit, such as meshing, slicing, simulation queries and clearance checks, share a sparse cache. The cache stores 8³ bricks of `f64` values and gradients at a power-of-two spacing h, only in the narrow band where interval evaluation cannot exclude the surface.

Each brick is keyed by (DAG hash, brick coordinate, h) and stored in the CAS, so a team shares it. Trilinear reads from the cache report an interpolation error bound from the node's Lipschitz constant and h, and callers that need more accuracy evaluate the tape directly.

### Field leaves

A Field leaf samples a Flux `Field` through its `Sampler` with a requested accuracy. The returned error adds to the implicit's `ErrorBound`, and the Field's representation supplies a Lipschitz bound (from element gradients for discrete Fields, or by interval evaluation for analytic Fields). `anvil::implicit_from_field` turns `Field<Body, Density>` into an implicit Body at an iso-value, which serves topology optimization and the Flux region extraction `f.region(where: f > 250MPa)`. Its distance kind is `Lipschitz(L)` from the Field's bound, and its `ErrorBound` is the Field's sampling error divided by a certified lower bound of the gradient magnitude near the iso-surface. Failure: `FieldOutOfRange`; `NoIsoSurface` when the Field never crosses the iso-value; `FlatIsoSurface { region }` where the gradient bound reaches zero, so the surface position cannot be bounded. Oracle: ANV-O-IMP-4 (analytic Fields with known iso-surfaces, such as a radial Field whose iso-surface is a sphere). Phase 1.

### Lattices from Fields

`anvil::lattice` builds lattice geometry inside a design region from Fields:

| Input | Type | Effect |
| --- | --- | --- |
| Region | Body | Where the lattice exists; trimmed exactly by intersection |
| Family | TPMS kind, strut topology (BCC, FCC, octet, Kelvin, custom graph) or stochastic Voronoi foam | Cell geometry |
| Cell size | `Field<Body, Length>` | Graded cell size |
| Thickness | `Field<Body, Length>` | Wall or strut thickness |
| Orientation | `Field<Body, Rotation>` or a conformal map from `anvil::parameterize` | Aligned and conformal lattices |
| Skin | Optional thickness and face selection | Lattice fused to a shell |

History: each lattice role (`wall`, `strut`, `node`, `skin`) is a DAG node with an EntityId, so faces of a converted lattice are selectable by role (`lattice.faces(role: skin)`).

`anvil::lattice` is the general primitive that the contract's section 4 leaves room for: the cell families above, graded and oriented by Fields. Specialized lattice generators, such as new cell families, stochastic or conformal design algorithms and vendor libraries, are Wasm components that emit strut graphs or implicit expressions and hand them to `anvil::lattice` or to implicit operations. Neither path is privileged.

A lattice with millions of cells stays an expression of a few hundred nodes, because domain repetition evaluates in constant time per point. Strut graphs above about 10⁴ struts use a spatial hash of struts as a leaf, so a point evaluates only nearby struts. Each strut lattice also exposes its graph (nodes, beams, radii) for export, for example to the 3MF Beam Lattice extension [3MF beam lattice repository; contents unverified].

Failure behavior: `BelowResolution { size }` when a wall or strut is thinner than 2λ (manufacturability limits such as printer resolution are checks in the Manufacturing tab, not kernel errors); `FieldOutOfRange` when a driving Field leaves its declared range; `TooManyCells { estimated, limit }` before evaluation when the estimated cell count exceeds the fuel. Oracle: volume fractions of uniform TPMS and strut lattices against closed-form or high-resolution reference values, minimum-thickness checks by certified interval evaluation, and determinism across platform classes. Phase 1, for golden product 2.

### Implicit meshing

`anvil::convert(implicit, into: Mesh)` uses adaptive dual contouring on an octree with certified cell classification:

1. **Classify.** Interval evaluation marks octree cells as inside, outside or ambiguous; ambiguous cells refine.
2. **Certify cells.** Refinement continues until each surface cell is monotone: the interval enclosure of one partial derivative excludes zero, so within the cell the surface is a graph over the other two axes, with no folds or small closed pieces. Cells that reach λ without this property are flagged `Uncertified` in the result.
3. **Place vertices.** Each surface cell gets one vertex per connected surface piece in the cell, placed by minimizing a quadric error function built from exact gradients, which keeps sharp edges and corners.
4. **Connect.** Manifold dual contouring connectivity guarantees a manifold output, as in Fidget's implementation [Fidget]; occupancy-based dual contouring shows the same structure parallelizes well on GPUs [Hwang and Sung 2024].
5. **Check.** An exact self-intersection test runs on the output; intersecting pairs are repaired locally by vertex relocation inside their cells.

The result's `ErrorBound` is a two-sided Hausdorff bound. Vertices are clamped to their cells, so every surface point is within one cell diagonal of the mesh, and every triangle, which spans adjacent surface cells, is within two cell diagonals of the surface. Where the ratio of max \|f\| over a triangle to a certified lower bound of \|∇f\| in its cells is smaller, that ratio is the bound.

The bound is `Guaranteed` in certified cells and `Estimated` in flagged ones, which are listed. Manifoldness is guaranteed; topological equivalence to the true surface is not claimed. Keeter notes that "good meshing of arbitrary implicit surfaces remains an unsolved problem" [Fidget], and Anvil claims no more than its certified cells allow.

## Mesh representation

### Surface meshes

A `Mesh` Body stores triangles with Manifold-style exact topology: an oriented, combinatorially 2-manifold half-edge structure, closed or with boundary. Manifold makes the same split, with exact topology, inexact geometry and a tracked precision ε that bounds accumulated rounding [Manifold wiki].

| Part | Layout |
| --- | --- |
| Positions | `f64` columns relative to the Body frame |
| Topology | Three half-edges per triangle (start vertex, paired half-edge); the pairing is a bijection |
| Face groups | A run of triangles that forms one selectable face, with its `EntityId`; tessellations of B-rep faces keep the face's EntityId |
| Crease edges | Half-edge flags marking sharp creases and face-group boundaries, each with an `EntityId` |
| Property channels | Typed per-vertex or per-corner channels: normals, UVs, colors, `(EntityId, u, v)` back-references, Field values |
| Regions | For closed meshes, which side is material and which material |
| Precision ε | The accumulated geometric error bound, as in Manifold |

Per-corner properties (a UV seam, a normal crease) use property indices separate from position indices, so seams never break topology. This mirrors Manifold's `MeshGL` merge vectors, which record vertex duplication for GPU buffers [Manifold wiki].

Triangle data that is not an oriented manifold does not become a `Mesh`. It enters through `anvil::mesh_from_triangles`, which either builds a valid `Mesh`, builds a cellular B-rep with facet faces when the data is non-manifold by intent (for example a T-junction of three sheets), or fails with `NotManifold { edges, vertices }` that suggests `anvil::repair_mesh`.

### Volume meshes

A `Mesh` Body may also carry volume cells. Volume meshes share the vertex and boundary-face structure of surface meshes and add:

| Part | Content |
| --- | --- |
| Cells | Tetrahedra, hexahedra, prisms, pyramids and general polyhedra (hex-dominant output), each with a region index |
| Order | Geometry order p_g from 1 to 4, with Bézier control nodes per element; Lagrange nodes derived on request |
| Boundary classification | Each boundary facet maps to the `EntityId` of the B-rep face or the internal interface it approximates; each crease edge maps to an edge `EntityId` |
| Quality | Per-element minimum scaled Jacobian, certified from Bernstein coefficients |
| Geometry error | Per-facet certified distance to the classified face, aggregated into the Body's `ErrorBound` |

Boundary classification is how Flux resolves `ds(part.face(q))` on fitted meshes: the query resolves to an `EntityId` on the B-rep, and the mesh's boundary facets carry that `EntityId`. Operations that expect a solid, such as Booleans, use a volume mesh's boundary and drop its cells with `Note::CellsDropped`; mesh operations keep the cells.

### Mesh repair

`anvil::repair_mesh` turns imported or scanned triangle data into a valid `Mesh`. Each step is reported in the result.

1. **Weld.** Merge vertices within the healing limit, using exact predicates on a fixed grid order so the result does not depend on input order.
2. **Remove degeneracies.** Collapse zero-area and needle triangles below λ.
3. **Resolve self-intersections.** Build the exact arrangement of all triangles with indirect predicates.
4. **Classify cells.** Assign inside or outside to each arrangement cell by the generalized winding number, which remains meaningful for self-intersecting, open and non-manifold inputs [Jacobson et al. 2013]; threshold 0.5.
5. **Extract.** Return the boundary of the inside cells as a manifold mesh, with holes smaller than a fill limit closed by minimal-area patches.

The `ErrorBound` reports the maximum displacement of any input point and the total area added or removed, with guarantee `Guaranteed` for displacement and `Estimated` for the winding-number decision near its threshold. Oracle: Thingi10K, whose models carry self-intersections and non-manifold geometry [Thingi10K 2016]; every repaired output must pass `check_body`, and the inside volume must match the reference winding-number volume within the reported bound.

### Where volume meshing lives

**Decision D-ANV-12:** Volume meshing (tetrahedral, hex-dominant, boundary layers, curved high-order elements), mesh adaptation and node optimization are Anvil operations; Flux decides what to mesh and how finely by passing sizing and metric Fields. *Why:* meshing consumes exact geometry, needs the same exact predicates, tolerance model and EntityIds for boundary classification, and its outputs are Bodies that other operations (Booleans, slicing, display) also consume; Flux's tab already assumes this split, with Anvil owning "all mesh generation and mesh modification" and Flux owning error estimation and marking. *Rejected:* meshing in Flux (would duplicate predicates, evaluators and naming, and mix geometry robustness into the solver); meshing as a Wasm component (it is a general operation used by every fitted discretization, which the contract assigns to native operations, and it needs Anvil's internal evaluators in every inner loop).

### Tetrahedral meshing

`anvil::tetrahedralize` has two strategies, chosen by input quality or explicitly:

| Strategy | When | Method | Boundary guarantee |
| --- | --- | --- | --- |
| `Conforming` (default for valid B-reps and valid meshes) | Input passes `check_body` | 1. Tessellate faces with the sizing Field, conforming at edges. 2. Constrained Delaunay tetrahedrization with Steiner points represented implicitly and indirect predicates [Diazzi et al. 2023]. 3. Quality improvement by local operations (split, collapse, swap, smoothing) that never move boundary vertices off their classified face. | Boundary facets subdivide the surface tessellation; Steiner points lie exactly on it until rounded to `f64`, then within one rounding of it; geometric error is the tessellation's certified error plus that rounding |
| `Envelope` | Imperfect input: soups, scans, healed imports | Incremental insertion into a floating-point background mesh with mesh optimization interleaved, keeping the boundary inside an envelope of width ε_env [fTetWild 2020] | Boundary within ε_env of the input (default τ_heal); every input triangle inserted, or the omitted ones reported |

Diazzi and colleagues report that the conforming CDT succeeds on all 4,408 valid Thingi10K models, averages 4.3 s per model with 76% under one second, and that TetGen fails on 378 of them. They also show that rounding Steiner points to floating point keeps the mesh valid in 93.22% of cases (99.77% after post-processing), and that some inputs admit no floating-point conforming mesh at all [Diazzi et al. 2023].

Anvil therefore rounds, checks every element with exact orientation predicates, and repairs inverted elements by local re-insertion. If any remain, it fails with `NotRepresentable { elements }` and suggests the `Envelope` strategy.

fTetWild guarantees a valid floating-point tetrahedral mesh but no longer guarantees that every input triangle is inserted; on Thingi10K it always inserted all of them [fTetWild 2020]. Anvil reports any omitted input triangle explicitly.

Multi-region bodies mesh conformally: every region of a cellular Body gets its own cells, and shared faces get shared facets. Contract: inputs `body: Body`, `sizing: &Field<Body, Length>`, `geometry_order: u8`, `strategy`, `quality: QualityTarget`; outputs a volume `Mesh` Body and an `ErrorBound` (Hausdorff distance between mesh boundary and Body boundary). Failure behavior: `InvalidInput` with `check_body` violations, `NotRepresentable`, `BudgetExceeded { elements }`, `QualityNotReached { worst, target }` (the mesh is still returned, marked).

Oracle: Thingi10K valid subset and ABC samples [ABC 2019] at fixed sizing; zero inverted elements; boundary error within the reported bound; region volumes within the bound. Phase 2 (`Conforming`, linear and curved by projection), phase 3 (`Envelope`).

### Curved high-order elements

`geometry_order > 1` curves the boundary elements onto the exact geometry:

1. Place Bézier control nodes of boundary facets by projecting onto the classified B-rep face in its parameter space, which keeps nodes on the face.
2. Certify validity: an element is valid when all Bernstein coefficients of its Jacobian determinant are positive, which is sufficient; the minimum coefficient bounds the scaled Jacobian from below.
3. Untangle invalid elements by optimizing interior nodes of a local patch, as `anvil::untangle`.
4. Refine (h) locally where untangling fails, up to the fuel.

Two published methods give stronger guarantees and set the state of the art. 3D Bézier Guarding covers polynomial boundary surfaces with a layer of curved elements that are "free of degeneracies and inversions" and conform exactly, at any polynomial order [Khanteimouri and Campen 2023]. Bijective coarse high-order meshing produces valid, non-flipped Bézier tetrahedra with a distance bound and a bijective map to the input surface; its code is MIT-licensed but depends on GPL CGAL [Jiang et al. 2021]. Anvil implements the guarding construction for faces whose geometry is polynomial or has an exact polynomial piece (planes, NURBS, cached approximations of procedural faces), and the project-certify-untangle pipeline for the rest.

Failure behavior: `InvalidElement { cell, jacobian_min }` when certification fails after untangling and refinement, matching the error Flux expects. Oracle: zero elements with a nonpositive Bernstein coefficient; boundary distance within the reported bound measured by dense sampling against the exact surface. Phase 2 (project, certify, untangle, for Flux's fitted contact in golden product 3), phase 3 (guarding).

### Hex-dominant meshing

`anvil::hex_dominant` converts a tetrahedral mesh into mostly hexahedra plus some irregular polyhedra by field-guided polyhedral agglomeration: orientation and position fields guide a simplification that keeps topological validity at every step, so the output is manifold [Gao et al. 2017]. The hex-meshing survey states that no known method combines robustness, quality and full automation, and that conforming high-quality hex meshing "remains a challenge" [hex survey 2022]. Anvil therefore promises hex-dominant output, not all-hex output, for arbitrary bodies.

All-hex meshes are offered only through `anvil::sweep_mesh` for bodies that are sweepable between a source and a target face, and through block-structured meshing of regions the user partitions. Failure behavior: `NotSweepable { reason, faces }`.

Oracle: element validity, hex fraction reported (no target promised), conformity across regions. Phase 3 (sweep meshing), phase 4 (hex-dominant).

### Boundary layers

`anvil::boundary_layer` grows prismatic layers from selected faces (a `Query`) for wall-resolved flow and thin-layer physics:

| Parameter | Type |
| --- | --- |
| First layer height | `Field<Faces, Length>` or a value |
| Growth ratio, layer count or total thickness | Values |
| Termination | Proximity, sharp-corner and collision rules |

Layers advance along smoothed normals with multiple normals at concave and convex edges. Collisions between fronts are found with exact predicates on the advancing faces, and layers terminate or compress locally with pyramids as transitions to the tetrahedral core. For curved high-order meshes, Anvil generates one thick curved layer and splits it isoparametrically into thin layers, the approach used for stretched curvilinear elements around streamlined bodies [Marcon et al. 2019].

Failure behavior: `LayerCollapsed { faces, achieved_layers }`, returning the partial mesh marked. Oracle: positive Jacobians, first-layer height within 5% of the request on 95% of faces (target), no layer intersections. Phase 4 (drone airflow).

### Adaptation and optimization

| Operation | Contract | Method | Phase |
| --- | --- | --- | --- |
| `anvil::refine_mesh` | `(mesh, marked: cells) -> (Body, HistoryRecords)` | Newest-vertex bisection of marked simplices with conforming closure, for the small adaptive steps Flux takes on fitted meshes; boundary midpoints projected onto classified faces | 2 |
| `anvil::adapt_mesh` | `(mesh, metric: &Field<Body, Metric>) -> (Body, HistoryRecords, ErrorBound)` | Local operations (split, collapse, swap, smoothing) driven by edge lengths in the metric, with boundary nodes kept on classified faces | 3 |
| `anvil::optimize_mesh` | `(mesh, target: &Field<Body, Metric>) -> Body` | Node relocation only, no topology change, for r-adaptivity | 3 |
| `anvil::untangle` | `(mesh) -> Body` | Local optimization of a barrier-free untangling energy, then quality optimization | 2 |

`anvil::polyhedral_mesh` builds the boundary-conforming polyhedral dual of a tetrahedral mesh for Flux's finite-volume method, with boundary-layer prisms kept as prisms. Each polyhedral cell records the tetrahedral cells it came from. Failure: `NonPlanarFace { cells, deviation }` when a dual face's planarity deviation exceeds the requested limit.

Oracle: closed cells, positive volumes, and face-area vectors summing to zero per cell. Phase 3.

Mesh adaptation history records map new cells to the cells they came from, so Flux can transfer solution Fields with its conservative or consistent rules. Volume cells are not named entities, so their parentage travels as a compact parent-index array in the output and expands to `Split` and `Merged` records only on request. Region and boundary face-group EntityIds follow the ordinary naming rules.

The Flux tab names Mmg as the reference implementation for anisotropic remeshing, used only as a reference. All three operations parallelize by deterministic independent sets, described under parallelism.

### Surface remeshing, decimation and smoothing

| Operation | Method | Guarantee | Phase |
| --- | --- | --- | --- |
| `anvil::remesh` | Isotropic or metric-driven local operations with crease edges fixed; optional quad-dominant mode by feature-line driven quad remeshing, which fails on fewer than 0.5% of Thingi10K models by its authors' report [Pietroni et al. 2021] | Hausdorff deviation from the input bounded and reported | 2 (triangles), 3 (quads) |
| `anvil::decimate` | Quadric error metric edge collapse [Garland and Heckbert], with feature and boundary preservation, a hard Hausdorff bound checked per collapse, and deterministic collapse order (cost, then EntityId-derived vertex order) | Reported Hausdorff bound is `Guaranteed`, because each collapse is verified, not estimated from the quadric | 1 |
| `anvil::smooth` | Taubin λ/μ smoothing, bilaplacian fairing with boundary and feature constraints | Displacement bound reported | 2 |

The quadric error metric is a heuristic that can overcount planes and grows unreliable away from the vertex [Garland and Heckbert], which is why Anvil verifies each collapse against the original surface instead of trusting the quadric.

All three keep face-group EntityIds and record `Split` and `Merged` for groups whose boundaries change. Failure behavior: `BudgetExceeded`; `FeatureConflict { edges }` when the target edge length or triangle budget cannot be met without crossing a fixed feature, with the closest feasible target as a fix. Oracle: ANV-O-REM-1.

## Subdivision surfaces

A `SubD` Body is a Catmull-Clark control cage: a polygon mesh with per-edge crease sharpness (real-valued semi-sharp creases plus infinitely sharp ones), per-vertex corner sharpness, boundary interpolation rules, and an `EntityId` per cage face, edge and vertex. Crease and boundary rules follow the conventions of OpenSubdiv, whose limit surface "matches Pixar's Renderman to numerical precision" [OpenSubdiv repository].

### Limit evaluation

| Region | Method | Exactness |
| --- | --- | --- |
| Regular faces (valence 4, no creases nearby) | Uniform bicubic B-spline patch | Exact |
| Faces near extraordinary vertices or semi-sharp creases | Feature-adaptive subdivision to a fixed depth, then patches; the exact limit at extraordinary vertices by eigen-analysis [Stam 1998] | The feature-adaptive method computes the "true limit surface up to machine precision" [Nießner et al. 2012] |

Stam's evaluation costs about as much as a bicubic patch but needs each face to contain at most one extraordinary vertex and does not address creases [Stam 1998]; Anvil uses it inside the adaptive scheme only for crease-free neighborhoods. Curvature at extraordinary vertices is in general not well defined, and `anvil::curvature` reports such points as singular instead of returning a number.

**Decision D-ANV-13:** Anvil implements Catmull-Clark subdivision with semi-sharp creases natively in Rust, following OpenSubdiv's rules and using OpenSubdiv as an oracle. *Why:* the limit surface must evaluate identically on CPU and in Wasm and feed exact B-rep faces; OpenSubdiv is C++ with GPU back ends in CUDA, Metal and OpenGL [OpenSubdiv repository], and its license is Apache 2.0 with a modified trademark section (the Tomorrow Open Source Technology License 1.0) [OpenSubdiv license], which permits use as a test oracle. *Rejected:* linking OpenSubdiv (C++ FFI, platform-specific GPU paths, no wgpu back end); Loop subdivision as the primary scheme (triangle cages suit meshes, not industrial design).

### SubD operations and conversions

| Operation | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| `anvil::convert` (Mesh → SubD) | Cage from a polygon mesh, with creases from crease edges | `NotManifold` | Limit of a regular cage equals its bicubic B-spline | 3 |
| `anvil::subd_edit` | Move, extrude, inset, bevel, crease, uncrease, insert edge loop, bridge; each keeps EntityIds of untouched cage elements | `NonManifoldResult`, `ZeroArea` | Euler characteristic and EntityId stability | 3 |
| `anvil::subd_limit` | Evaluate limit points, derivatives and normals at (face, u, v) | `SingularPoint` at extraordinary vertices for curvature | Agreement with OpenSubdiv within 10⁻¹² relative (target) | 3 |
| `anvil::convert` (SubD → BRep) | Exact mode: one subdivision-limit face per cage face (D-ANV-7); NURBS mode: exact bicubic patches on regular faces and certified approximations near extraordinary vertices | `ToleranceNotMet { achieved }` in NURBS mode | Deviation from the limit surface by dense certified sampling; G1 deviation across patch boundaries reported | 3 |
| `anvil::fit` (target SubD) | Fit a cage to a B-rep or mesh through feature-aligned quad remeshing, then least squares on cage positions | `FitFailed { residual }` | Hausdorff distance to the target, reported as `Estimated` | 4 |

## Naming: EntityId, HistoryRecord and Query resolution

### EntityId

The contract defines `EntityId` as a hash of (operation id, input entity ids, role). Anvil fixes each part:

EntityId = SHA-256₁₂₈( "anvil.eid.v1" ‖ kind ‖ site ‖ role ‖ inputs ‖ discriminator )

| Part | Definition |
| --- | --- |
| `kind` | Region, shell, face, loop, edge, vertex; for meshes, face group and crease edge; for SubD, cage face, edge and vertex; for implicits, DAG node |
| `site` | The `OpSite` of the Op node that created the entity: the feature instance path plus a call-site key supplied by Ingot and Kiln, plus loop and pattern indices. It excludes argument values, so editing a dimension keeps every site. |
| `role` | From the operation's role vocabulary, such as `start_cap`, `end_cap` and `side` for `extrude` (the Mechanical tab uses the same roles) |
| `inputs` | The EntityIds of the generating entities: the profile edge for an extruded side face, the two faces for an intersection edge, the edge for a blend face. Sorted, unless the operation declares their order meaningful. |
| `discriminator` | Present only when (kind, site, role, inputs) is not unique; see below |

`SHA-256₁₂₈` is the first 128 bits of SHA-256 over the canonical encoding. Within one Body, a duplicate EntityId fails the operation with `Internal::EntityIdCollision`. By the birthday bound the chance of an accidental collision is about n²/2¹²⁹, or 2⁻⁶⁵ for a Body with n = 2³² entities, and the check makes it loud if it ever happens.

Discriminators, in order of preference:

1. **`Bound(set)`**: the EntityIds of the cause entities that bound the piece, such as the tool faces that cut it. Stable under parameter edits that keep topology.
2. **`Side(cause, sense)`**: which side of a cutting entity the piece lies on.
3. **`Ordinal(k)`**: the k-th piece in a canonical order along a declared direction, used only when the first two cannot distinguish pieces (identical strips cut by one periodic tool). The EntityId carries a fragility flag, and any query anchored on it gets `Note::FragileAnchor`.

Entities that an operation leaves untouched keep their EntityId. Entities whose geometry, boundary, tolerance or attributes change also keep it and get a `Modified` record.

Pattern copies differ by the copy index inside `site`. An operation called from inside a Wasm component gets the site of the component's Op plus a call key that the component passes through its WIT interface; components are deterministic, so the key is too.

**Decision D-ANV-14:** `OpSite` excludes argument values and is keyed by the stable syntax-node identity that Ingot assigns to each call. *Why:* if the operation id included parameters, every dimension edit would rename every downstream face and break every query; call-site identity is the structural "operation id" the contract intends, and `repo`'s syntax-tree CRDT already gives syntax nodes stable identities. *Rejected:* the Op content hash (renames on every edit); sequence numbers of operations in evaluation order (shift when features are inserted); geometric signatures as primary names (geometry changes under exactly the edits that names must survive, and the 2018 review of persistent identification finds that topology-only and geometry-only schemes each have limits [persistent naming review 2018]; signatures are used only for imported geometry, below).

Because EntityIds depend on the site, `OpSite` is an input of every operation (CCR-ANV-5). To keep the cache shared across sites, each operation runs as a site-independent geometric core, cached without the site and labeled with provisional ids, followed by a relabeling pass that applies the site; the pass is linear in the number of new entities. A call that the editor moves keeps its syntax-node identity and therefore its site. A call that is deleted and retyped gets a new site; queries anchored on the old one fail with `ResolveError::Deleted`, and the fix re-anchors them to the new call.

### HistoryRecord

Every operation returns a list of records over the entities of its input and output Bodies:

| Record | Meaning | Lineage edge |
| --- | --- | --- |
| `Created { out, role, from }` | A new entity generated from `from` entities of other kinds, such as a blend face from an edge | Cross-kind ("generated by") |
| `Modified { id, aspects }` | Same entity, changed geometry, boundary, tolerance or attributes | Identity |
| `Split { from, into }` | One entity became several of the same kind | Parent to child |
| `Merged { from, into }` | Several entities of the same kind became one | Parent to child |
| `Deleted { id, by, reason }` | The entity no longer exists: consumed by `by` (a blend face consumes its edge), became internal, or was removed | None |

Records satisfy four properties that the history oracle checks on every operation:

1. **Coverage.** Every input entity is unchanged in the output, or is the subject of exactly one same-kind record (`Modified`, `Split`, `Merged` or `Deleted`); `Created` records may also name input entities as generators. Every output entity is an unchanged input, the `id` of a `Modified`, an `into` entry of a `Split` or `Merged`, or the `out` of exactly one `Created`.
2. **Kind.** `Split`, `Merged` and `Modified` relate entities of the same kind.
3. **Geometric soundness.** The pieces of a `Split` lie within the tolerance region of the parent, and the parents of a `Merged` lie within the merged entity's region, checked by certified sampling.
4. **Canonical order.** Records are sorted by (record kind, first EntityId), so the list is identical across thread counts and platforms.

### Lineage

Each Body stores, for every entity, its ancestor set: the EntityIds reachable backward through identity, `Split` and `Merged` edges. Sets are persistent and share structure with the input Bodies' sets, so storage grows with the number of records, not with model size. Cross-kind `Created` edges are stored separately as generator links.

The descendants of an anchor id a in Body B are D(a, B) = { e ∈ B : kind(e) = kind(a) and (e = a or a ∈ ancestors(e)) }. Generator queries such as `created_by` follow generator links instead.

### Query resolution

Ingot lowers every `Query` to a plan with three stages, and Anvil evaluates it against a Body:

1. **Anchor.** One or more EntityIds captured from feature results, such as `base.face(top)`, or a structural set, such as `created_by(feature)`.
2. **Lineage.** Map each anchor to D(a, B). An empty set yields `Deleted` information from the record that removed it.
3. **Filter and select.** Apply geometric predicates (normal direction, surface type, area or length range, convexity, adjacency, `bounded_by`, distance to a point) with certified evaluation, then the cardinality rule: `one`, `all`, `at_least(n)`, or a selector such as `largest` with a declared tie rule.

A geometric predicate near its threshold is decided by the certified rule of D-ANV-4. If the enclosure straddles the threshold, resolution fails with `ResolveError::Ambiguous { entity, predicate, margin }`; it never flips an entity in or out on rounding noise.

| Outcome | Result |
| --- | --- |
| The plan selects what the cardinality requires | `Resolved { entities, notes }` |
| Anchor was split and the query needs one entity | `ResolveError::Split { anchor, pieces, fixes }` |
| Anchor was merged | Resolves to the merged entity with `Note::Merged { with }`, unless the query sets `on_merge: fail` |
| Some descendants of the anchor were deleted later | Resolves to the surviving descendants with `Note::Partial { deleted }` |
| Anchor was deleted | `ResolveError::Deleted { anchor, by, site, fixes }` |
| Filters leave fewer entities than the cardinality requires (none, for `one`) | `ResolveError::NoMatch { stage, found, closest, fixes }` |
| Filters leave more than allowed | `ResolveError::TooMany { candidates, fixes }` |

Each fix is a typed source edit. Fixes are ranked by the stability test the agents tab specifies: resolve the fixed query under 16 seeded parameter perturbations and prefer the fix that resolves identically in all of them (D-AGT-8).

Ranking rebuilds the design 16 times, so it runs on demand, when the UI or an agent asks for fixes, and its rebuilds share the Kiln cache. Notes are visible in the UI and the CI report, and a check may forbid them, for example `require no_notes(part)` before release.

**Decision D-ANV-15:** Query resolution walks recorded lineage, then applies certified geometric filters, and treats splits, ambiguity and deletion as typed errors while accepting merges with a visible note. *Why:* the contract forbids silent re-selection; a merged entity still contains the referenced geometry, so resolving it changes extent but not meaning, whereas choosing one split piece would change meaning. *Rejected:* geometric matching as the primary mechanism (it re-identifies entities by geometry after the very edits that change geometry); failing on merges by default (common Boolean unions would break many queries for no gain).

[[DIAGRAM: Lineage of the worked examples. Left column "Example 1": box T (top face, site S₁ extrude, role end_cap) with an arrow labelled "Split at S₂ (union with rib)" to two boxes T₁ (Bound F_front) and T₂ (Bound F_back); a dashed arrow from a query box "part.face(base.face(top))" to both pieces, labelled "ResolveError::Split with 3 ranked fixes". Middle column "Example 2": boxes A_top and B_top with arrows labelled "Merged at S_union" into one box M; a query box "part.face(a.face(top))" with a solid arrow to M labelled "Resolved + Note::Merged". Right column "Example 3": T → T₁, T₂ (Split at S₂, slot) → M₃ (Merged at S₃, delete_faces); a query box on T with a solid arrow to M₃ labelled "Resolved, single descendant".]]

### Worked example 1: a face split by a rib

```
let base = sketch(plane.xy) { rect(60mm, 40mm) } |> extrude(4mm)        // top face at z = 4 mm
let rib  = sketch(plane.xz) { rect(60mm, 10mm, at: (0mm, 9mm)) }        // wall from z = 4 mm to 14 mm
           |> extrude(3mm, symmetric: true)                               // 3 mm thick, centered on y = 0
let part = base + rib
let top  = part.face(base.face(top))
```

1. `extrude` at site S₁ creates the top face T = EID(face, S₁, `end_cap`, [profile region]).
2. The rib spans the full 60 mm length, so the union at site S₂ cuts T along the rib's side faces F_front (y = −1.5 mm) and F_back (y = +1.5 mm). It returns `Split { from: T, into: [T₁, T₂] }` with T₁ = EID(face, S₂, `split`, [T], Bound{F_front}) and T₂ = EID(face, S₂, `split`, [T], Bound{F_back}). The strip under the rib becomes internal and is removed, so the split lists only the two surviving pieces. The rib's bottom face is entirely internal and gets `Deleted { reason: Internal }`. The rib's end faces are coplanar with the base's end faces at x = ±30 mm, so each pair also merges, as in example 2.
3. `part.face(base.face(top))` asks for one entity and finds two descendants, so it fails:

```
ResolveError::Split {                                              // stability counts illustrative
  anchor: base.top, pieces: [T₁, T₂],
  fixes: ["part.faces(base.face(top))",                                   // both pieces; stable 16/16
    "part.face(base.face(top), bounded_by: rib.face(side_front))",  // T₁; stable 16/16
    "part.face(base.face(top), nearest: point(0mm, -15mm, 4mm))",   // T₁; stable 13/16]
}
```

4. If the user shortens the rib to 40 mm, it no longer reaches the edges of T, so T is not split. T keeps its EntityId, gains an inner loop, and gets `Modified { aspects: Boundary }`; the original cardinality-one query now resolves to T without error. If the user instead lifts the rib 1 mm off the face, the `bounded_by` query fails with `NoMatch { stage: bounded_by }`, which explains that the rib no longer bounds the top face, instead of silently returning the whole face.

### Worked example 2: coplanar faces merge, then separate

```
let a = box(10mm, 10mm, 10mm)
let b = box(10mm, 10mm, h).translate(x: 10mm)
let part = a + b
let f = part.face(a.face(top))
```

1. With h = 10 mm the top faces A_top and B_top are coplanar and share an edge. The union returns `Merged { from: [A_top, B_top], into: M }` with M = EID(face, S_union, `merged`, sorted [A_top, B_top]). The front, back and bottom pairs merge the same way. The touching side faces become internal and are `Deleted { reason: Internal }`.
2. `f` resolves to M with `Note::Merged { with: [B_top] }`. A fillet on `f.edges()` now runs around the combined face, and the note shows why.
3. With h = 12 mm the faces are no longer coplanar. No merge happens, A_top keeps its EntityId with a `Modified { aspects: Boundary }` record, and `f` resolves to A_top alone.

### Worked example 3: split, then re-merged

A slot cuts face T into T₁ and T₂ at site S₂; a later `delete_faces` of the slot faces at site S₃ heals the gap and returns `Merged { from: [T₁, T₂], into: M₃ }`. For anchor T, D(T, B) = {M₃}, because both pieces descend into one entity, so a cardinality-one query on T resolves to M₃ without error. The same rule makes "cut, then fill" sequences behave as designers expect.

### Worked example 4: the contract's `joined` edges

The contract's bracket fillets `web.edges(joined)` after `base + web`. Ingot lowers `joined` to a generator query: the edges with `Created { role: intersection_edge }` at the union's site whose generating faces include a descendant of a `web` face. When an edit to `thickness` moves the web, the union re-runs at the same site, the intersection edges get the same EntityIds (same site, role and generating faces), and the fillet keeps its edges.

If an edit makes the web's end face flush with the base's end face, the intersection edge along that end is never created. The query then returns the remaining edges, unless it declared a count such as `at_least(3)`, in which case it fails with `NoMatch { found: 2 }`.

### Names for other representations

| Representation | Named entities | Rule |
| --- | --- | --- |
| Mesh | Face groups and crease edges | Tessellation keeps each B-rep face's EntityId on its face group; remeshing and decimation keep group ids and record splits and merges of groups |
| SubD | Cage faces, edges, vertices | `subd_edit` records `Created`, `Split` and `Merged` for cage elements; exact B-rep conversion gives each limit face its cage face's EntityId |
| Implicit | DAG nodes with roles | Converting an implicit to a Mesh or B-rep labels each output face group with the EntityId of the DAG leaf whose value is active at the surface, found from interval choices; `lattice.faces(role: skin)` works on the converted Body |
| Imported B-rep | Faces, edges, vertices | Site is the import Op; the discriminator is a geometric signature (surface type, quantized defining parameters and box at the face tolerance) |

Imported geometry has no history, so a revised STEP file is matched to the previous import with `anvil::match_bodies`. It pairs faces by certified Hausdorff distance and overlap in the shared coordinate frame and returns `HistoryRecord`s between the two imports. Queries on the old import then resolve on the new one through ordinary lineage, and unmatched faces fail with typed errors.

Oracle: edited copies of ABC models with known edits; matched pairs must equal the edit's ground truth. Phase 2.

### Feature-level roles

Features often name entities by intent, such as `counterbore_wall`, which operations do not know; the Mechanical tab raises this as an open question. Anvil answers it with an attribute: a feature attaches a `FeatureRole` attribute to EntityIds it returns, with the `Copy` split policy and `Union` merge policy. Queries match roles like any other attribute, and EntityIds stay purely structural.

## Intersections

Intersections are the core of Booleans, blends, trims, sections and classification. Anvil computes them with one certified framework: enclosures prune, interval Newton certifies, and the tolerance rule decides what remains.

### Building blocks

| Tool | Role |
| --- | --- |
| Bernstein enclosures | The convex hull of a Bézier piece's control points bounds the piece; subdivision tightens it. Procedural geometry uses its cached Bézier approximation plus the certified approximation error. |
| Normal and tangent cones | Interval enclosures of unit normals or tangents over a parameter box |
| Krawczyk operator (interval Newton) | Proves that a box contains exactly one regular root, or none, and contracts it |
| Distance enclosure | Interval bound on the distance between two pieces, used by the tolerance rule |
| Projected Polyhedron | Subdivision solver for polynomial systems in Bernstein form, with an interval variant, described in chapter 4 of Patrikalakis, Maekawa and Cho [Patrikalakis, Maekawa and Cho] |

### Curve-curve intersection

Inputs are two curves in 3D, or two parameter curves on one surface in 2D. Output is a sorted list of isolated points (t₁, t₂) with multiplicity class (transversal or tangent) and overlap intervals where the curves coincide within tolerance.

1. Exact special cases: line-line, line-circle and circle-circle with exact predicates and closed forms.
2. General case: recursive subdivision with Bernstein hulls, pruning disjoint pairs, with Krawczyk contraction once a pair is small enough to contain at most one transversal root.
3. In 2D, a pair is certified when the Krawczyk operator proves a unique transversal root inside it. Curves in 3D generically miss each other, so there Anvil certifies the pair's unique closest-approach point, a critical point of the distance, and decides intersection with the tolerance rule.
4. Tangent and overlapping pairs fall to the tolerance rule: a pair whose distance enclosure stays below τ over a parameter interval becomes an overlap; a pair whose closest approach is an isolated minimum below τ becomes a tangent point at the certified minimizer.

### Curve-surface intersection

The same scheme runs in three unknowns (t, u, v). Line and conic against plane and quadric use closed forms. Results are points with multiplicity class and overlap intervals (a curve lying on the surface within tolerance), trimmed against the face's loops by certified point-in-face classification.

### Surface-surface intersection

Surface-surface intersection (SSI) returns a branch graph: intersection curves between characteristic points, isolated contact points, and coincidence regions where the surfaces overlap within tolerance. Two recent papers set the bar for topological correctness.

Yang, Jia and Yan handle cross intersections, isolated contacts, boundary intersections, contacts across branches and high-order contacts along a curve, and report that OCCT and ACIS struggle with some of these cases [Yang et al. 2023]. Cheng and colleagues map SSI topology to the solutions of an algebraic system through 4D interval algebraic topology analysis [Cheng et al. 2023].

Anvil's algorithm:

1. **Analytic pairs.** Plane, quadric and torus pairs use closed forms where they exist, with exact detection of special positions (parallel, coaxial, tangent, coincident) on defining parameters within tolerance. Plane-cylinder gives lines or ellipses; coaxial surfaces of revolution give circles.
2. **Broad phase.** Hierarchies of conservative patch boxes for both surfaces, overlap culling, and candidate leaf pairs in canonical order.
3. **Loop exclusion.** For each candidate pair, Anvil looks for a vector v with v · (n₁ × n₂) bounded away from zero over the interval enclosures of both normal cones. A closed loop has a point where its tangent n₁ × n₂ is orthogonal to v (its extreme point in direction v), so such a v proves that the pair holds no closed loop. Because n₁ × n₂ is then nonzero throughout, the pair also holds no tangent or singular point, and every branch in it enters and leaves through the pair's boundary. Otherwise the pair subdivides.
4. **Characteristic points.** Pairs that still fail the tests at the subdivision floor are searched for tangent and singular points with the Krawczyk operator. The system describes critical points of the signed distance h from S₁ to S₂: S₁(u, v) − S₂(s, t) − h·n₂(s, t) = 0, n₂ · ∂S₁/∂u = 0 and n₂ · ∂S₁/∂v = 0, five equations in (u, v, s, t, h). A non-degenerate tangency or branch crossing is a regular root with h = 0, so it is certified even though the plain SSI system is singular there. Roots with 0 < |h| ≤ τ are near-misses for the tolerance rule; degenerate roots, such as contact along a curve, are handled under tangential cases below.
5. **Boundary points.** Each piece's boundary curves are intersected with the other surface by curve-surface intersection.
6. **Tracing.** Within each resolved pair, each branch piece is traced between its boundary or characteristic points by certified marching. A step is accepted only when an interval implicit-function test proves the step's box contains exactly one branch segment, so a tracer cannot jump between nearby branches. Each piece is traced from its smaller end point in canonical order, with a deterministic step rule, and pieces join at shared boundary points into branches. A closed loop inside one pair surrounds a certified critical point and is traced from its crossing with the parameter line through that point. Traced points therefore never depend on processing order.
7. **Coincidence.** Pairs whose distance enclosure stays below τ over a region become coincidence regions, bounded by their own curves.
8. **Output.** Each branch becomes an intersection curve: the two surfaces, a fitted B-spline within τ of the true curve, and two parameter curves, with the certified deviation stored.

A run is complete when every leaf pair is disjoint, passes the loop-exclusion test, or holds certified characteristic points. Fuel is local: a subdivision depth per pair and a step limit per branch piece, never a global count, so success and output do not depend on the order in which pairs are processed.

Pairs that reach the depth limit unresolved are decided by the tolerance rule, or the operation fails with `Ambiguous { faces, region }`. The result never contains a branch that was not certified or decided by the rule.

**Decision D-ANV-16:** SSI uses subdivision with Bernstein and interval enclosures, normal-cone loop exclusion, Krawczyk certification of characteristic points as critical points of signed distance, and certified marching, and it reports a topology certificate per pair. *Why:* this combination gives the branch-graph guarantees of the topology-guaranteed methods while staying in `f64` with interval rules, and every step parallelizes over pairs. *Rejected:* plain marching from sampled seeds (misses small loops and jumps branches near tangencies); purely algebraic methods (degrees explode for rational, offset and blend surfaces); lattice sampling as the decision method (no guarantee between samples).

### Tangential and degenerate cases

| Case | Detection | Result |
| --- | --- | --- |
| Transversal crossing | Disjoint normal cones along the branch | Curve, certified |
| Tangent contact point | Regular root of the critical-point system with h = 0 | Isolated point with contact order |
| Tangent contact along a curve (two fillets touching, a cylinder resting on a plane) | Distance and normal-difference enclosures both near zero along a branch | Curve classified `Tangential`; Booleans treat both sides with the tolerance rule |
| Overlap (coincident patches) | Distance enclosure below τ over a region | Coincidence region; Booleans merge the faces |
| Near-miss closer than τ | Distance enclosure below τ, normal cones separated | Treated as a touch; tolerance grows within the cap, recorded |
| Singular crossing (two branches cross) | Saddle-type regular root of the critical-point system with h = 0 | Branch graph vertex of degree 4 |
| Surface singularities (cone apex, sphere pole, lemon torus) | Declared singular points of the surface | Handled as characteristic points |

Tangential intersections are ill conditioned. For two curves that touch with normal curvatures differing by Δκ, a normal shift ε creates crossings at distance √(2ε/Δκ) from the contact, so a rounding-level change of 10⁻¹⁶ m with Δκ = 1 m⁻¹ moves them by about 10⁻⁸ m. The tolerance rule turns this into an explicit decision with a recorded tolerance instead of a random outcome.

### GPU strategy and freedom to operate

US patent 12,229,885 B1, "Surface-to-surface intersections in computer-aided graphics and modeling", was filed on 13 May 2024 as application 18/662,056 and granted on 18 February 2025. Google Patents lists the inventor as Alyn Rockwood and the assignee as an individual, and estimates expiration in 2044 [US12229885B1].

Zoo's engine overview cites the same application number as "recently allowed" [Zoo engine overview]. Claim 1 covers computing distances between points of a set representing the first surface and points of a set representing the second, forming intersection points from first-surface points within a threshold distance of a second-surface point, and outputting intersection curves; the system claim recites a "parallel computing processor" [US12229885B1 full text].

The contract decides "GPU sampling plus certified CPU refinement" for SSI. Anvil implements it in three parts, each with a fixed role:

1. **GPU sampling orders the work.** The GPU evaluates both surfaces on grids in `f32` and builds per-cell boxes and box hierarchies, the method Krishnamurthy and colleagues published in 2008 [Krishnamurthy et al. 2008]. Overlapping cells give the CPU a priority order: pairs likely to hold a branch are processed first, so exact branches stream to Kiln early, which serves the contract's coarse-results-first rule. Every candidate pair is still processed, with local fuel, so the order changes latency, never output.
2. **An exact integer broad phase prunes.** The CPU computes conservative `f64` boxes for patch pieces, faces and triangles, rounds them outward to integer coordinates on a grid of cell size 2⁸ρ in the Body frame, and uploads them. The GPU tests box overlaps and traverses hierarchies with integer comparisons only. Integer comparisons are exact on every GPU, so the candidate set equals the CPU fallback's.
3. **The CPU decides.** Every intersection point and curve comes from the certified subdivision of the previous section, which is complete on its own; the GPU order changes how fast it finishes, never what it returns. Anvil never forms intersection points from pairs of surface samples whose distance falls below a threshold.

`f32` GPU evaluation also feeds display tessellation and previews. Preview intersection curves come from triangle-triangle intersection of preview tessellations.

GPU acceleration of NURBS operations has a long published record. Krishnamurthy and colleagues evaluated NURBS surfaces into GPU textures, built curvature-inflated box hierarchies, tested box pairs on the GPU and intersected triangle pairs, reporting about 40× the speed of ACIS at its standard tolerance of 10⁻³, excluding curve fitting, in 2008 [Krishnamurthy et al. 2008]. ETER evaluates NURBS on uniform sampling grids with tensor-core acceleration, 2.9 to 16.2 times faster than evaluation based on hardware tessellation, and renders up to 3.7 million patches at 30 frames per second [ETER].

**Decision D-ANV-17:** In intersections the GPU samples surfaces to order CPU work and runs an exact integer broad phase to prune it; every intersection point comes from a CPU certified solve, and Anvil never thresholds distances between point samples of two surfaces. *Why:* this realizes the contract's "GPU sampling plus certified CPU refinement" with outputs that are bit-identical with and without a GPU; certified solves give guarantees that sampled thresholds cannot; the sampling step follows 2008 prior art, and no step performs the thresholding that claim 1 of US 12,229,885 B1 describes. *Rejected:* dense point-sample SSI on the GPU (uncertified, which Zoo's own overview concedes in calling SSI inherently approximate [Zoo engine overview], and within the patent's claims); no GPU use at all (gives up speed on large models and assemblies).

This is a technical design-around, not a legal opinion. Counsel must review it before any GPU intersection path ships in phase 1, as the contract requires. The CPU path is complete on its own, so an adverse opinion removes acceleration, never function.

### Intersections in other representations

| Pair | Method |
| --- | --- |
| Triangle-triangle (meshes, facet faces) | Exact arrangement with indirect predicates; intersection points stay implicit until output [Attene 2020; Cherchi et al. 2022] |
| Facet face with exact surface | Per-triangle plane against the surface (curve-surface on the triangle's edges, plane-surface SSI inside), certified |
| Subdivision-limit faces | Regular faces are exact bicubic patches and use SSI directly; faces near extraordinary vertices use adaptive patches with certified bounds |
| Implicit with anything | Zero-set classification by interval evaluation; intersection curves only on conversion |

## Operation contract and behavior versions

### What every operation guarantees

Every Anvil operation is a value of the same shape: a name, a behavior version, typed arguments, and a run function from a context and arguments to an output or a typed error.

| Element | Contract |
| --- | --- |
| Inputs | Bodies, plain values with units already converted, `Query` results as EntityId sets, Fields with a required accuracy |
| Output | Bodies or plain values (measurements are values, distributions are Fields), `HistoryRecord`s, one `ErrorBound` per output, notes |
| Errors | `OpError { kind, why, fixes, at: [EntityId], partial }`; `partial` is a marked diagnostic Body that Kiln never caches as a success |
| Fuel | Deterministic work limits (subdivision depth, iterations, element count), applied per unit of work (per pair, per element, per branch) so that success never depends on processing order; exhaustion gives `BudgetExceeded { resource, used, fix }` |
| Fidelity | `Exact` (canonical, cached, checkable) or `Preview` (marked, never cached in the shared store, never used by checks) |
| Determinism | Output bits depend only on the cache key of the contract's `Op`; thread count, GPU presence and memory addresses never matter |
| Validity | Every output Body is valid. Operations run `check_body` on the entities they created or modified and on their neighbors, which suffices because untouched entities were valid and did not change; oracle runs check whole Bodies. A violation is an internal error, never a returned Body |

`OpError` maps one-to-one onto the Mechanical tab's `FeatureError { kind, why, fix, at }`, so Ingot features pass Anvil errors through with their fixes.

### Behavior versions

A behavior version identifies the exact input-to-output function of an operation, written `anvil::blend@2`. Anything that can change the output bits of an `Exact` run, the history records, the EntityIds or the error kinds is a behavior change and needs a new version. A change that keeps every bit, such as a faster data structure with the same arithmetic, does not.

**Decision D-ANV-18:** Each operation version is an immutable source module; the code of `anvil::blend@2` and of every internal algorithm module it uses (for example `ssi@4`, `predicates@1`) is frozen by content hash once released, and changes go into new module versions. *Why:* old designs must rebuild identically, and a regression corpus cannot cover every input, whereas frozen source plus PLT's bit-reproducible toolchain makes old versions reproducible by construction. *Rejected:* versioning only the public operation while sharing mutable internals (a fix inside a shared intersection routine would silently change every old version); keeping old Crucible binaries around to rebuild old designs (no cross-platform guarantee, no shared cache, security fixes impossible).

Four mechanisms implement the policy:

1. **Freeze check.** CI hashes the source of every released module version. A change to a frozen module fails the merge queue unless a human approves a security exception, which must also show identical outputs on the full regression corpus.
2. **Behavior diff.** A new version runs beside its predecessor on the operation's corpus. The report lists output hash changes, history differences and new or removed error kinds, and it is attached to the change's Proposal.
3. **Toolchain guard.** A Rust toolchain or `detmath` upgrade must reproduce the golden output hashes of every active and deprecated version. A difference blocks the upgrade, because a toolchain must never change old behavior.
4. **Retired versions to Wasm.** A version leaving the native tree is compiled, together with the frozen sources of every module it depends on, into a Wasm component published in the package registry. The `cpu-f64` class spans native and Wasm targets (D-FLX-19), so the component reproduces the native bits, and it runs on every platform including the browser. The host passes Bodies to the component in the encoding major version it was built with; a Body that version cannot represent fails with `EncodingError::NotRepresentable`, which suggests upgrading the operation.

### How a design pins versions

| Mechanism | Where | Effect |
| --- | --- | --- |
| Lockfile pins | The design repository's lockfile, one line per operation: `anvil.blend = 2` | Every call of `blend` in the design uses version 2 |
| Call-site override | Ingot: `fillet(edges, 2mm, op: anvil::blend@1)` | One call uses an older version, for a feature that must not move while the rest upgrades |
| New designs | Lockfile created with the current version of each operation | Latest behavior by default |
| Upgrade | `crucible upgrade anvil::blend` | Creates a Proposal: rebuilds with the new version, attaches geometry overlay, metric deltas, changed checks and every `ResolveError` |

The Ingot tab owns lockfile syntax; Anvil supplies the registry of versions, their status and their migration notes.

### Version lifecycle

| Status | Meaning | Execution | Duration |
| --- | --- | --- | --- |
| `Current` | Default for new designs | Native | Until superseded |
| `Deprecated` | Superseded; pinned designs still use it | Native; every build emits `Note::DeprecatedBehavior { op, current, migration }` | At least 5 years after supersession [proposal] |
| `Retired` | Removed from the native tree | Wasm component from frozen source, same bits | Indefinitely; never deleted |
| `Yanked` | Known to produce wrong results | Runs for pinned designs with `Warning::YankedBehavior`; release checks fail until the design upgrades or a human waives | Never removed |

A yanked version stays executable because releases signed with it must rebuild bit-identically for audit. Only new pinning is blocked.

The Flux tab raises a 10-year retention window as an open question; Anvil's answer is that versions stay executable indefinitely, natively for at least 5 years and as Wasm components afterwards. The 5-year native window is a proposal for PLT and Kiln to confirm against CI cost.

### Versions and the cache

Kiln's cache key includes the operation name and behavior version, as the contract defines for `Op`. A Body decoded from an older encoding is re-encoded in the current version, so its content hash is an ordinary hash and needs no extra key. Deprecated and retired versions share the CAS with current ones, so a team that pins old versions still gets cache hits.

## Operations catalog

The catalog lists the operations std features call. Every row obeys the operation contract above: outputs pass `check_body`, carry an `ErrorBound`, return `HistoryRecord`s, and fail with a typed `OpError`. Read-only queries and analyses return values or Fields and emit no `HistoryRecord`s, so their tables omit the History column.

Columns give the specific inputs and outputs, the history the operation emits, its failure kinds, its oracle (listed under Oracles) and its phase. "Created(role)" means `Created` records with that role vocabulary.

### Canonical names

Other drafts in this round call some operations by different names. Anvil proposes one name per concept:

| Name used elsewhere | Canonical Anvil operation | Reason |
| --- | --- | --- |
| `section_body` (MEC), `slice` (MFG) | `anvil::section` | One plane, a stack of parallel planes or a surface; the stack form is the slicing case |
| `offset_curves_2d` (MFG) | `anvil::offset_curve` | Planar input keeps arcs exact; one operation for 2D and curves on surfaces |
| `medial_axis_2d` (MFG) | `anvil::medial_axis` | Planar regions get the exact segment-and-arc Voronoi skeleton; solids get the certified 3D approximation |
| `extend_face` (MEC), `extend_surface` (MFG) | `anvil::extend` | One concept |
| `implicit_from_brep`, `brep_from_implicit`, `subd_to_brep` (MEC) | `anvil::convert` | One conversion operation with a target representation and a required accuracy |
| `fit_nurbs`, `fit_primitive` (MEC), `fit` (MFG) | `anvil::fit` | The model kind is an argument |
| `icp` (MEC) | `anvil::align` | A plain name; iterative closest point is its method |
| `tool_drop`, `tool_push` (MFG) | `anvil::tool_contact` | Both find the first contact of a revolved tool moving along a direction |
| `collide` (MFG) | `anvil::interference` | Overlap, touch and clearance in one query |
| `thickness_ray` (MEC) | `anvil::thickness` with `method: Ray` | Ray and inscribed-sphere thickness are one analysis |
| `sample_surface`, `evaluate_curve` (MEC) | `anvil::sample`, `anvil::evaluate` | One evaluation operation for curves and surfaces, one sampling operation |
| `approximate_curve`, `approximate_surface` (MEC) | `anvil::approximate` | Exact geometry to NURBS within a tolerance, for curves and faces alike |
| `offset_body`, `draft_faces` (MEC) | `anvil::offset`, `anvil::draft` | Shorter names; `offset_faces` stays separate because it moves selected faces only |
| `delete_face`, `replace_face` (MEC) | `anvil::delete_faces`, `anvil::replace_faces` | Both take entity sets |
| `helix` (MEC) | `anvil::curve` with `Helix` | Curve constructors share one operation |

### Construction

| Operation | Contract | History | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- | --- |
| `anvil::primitive` | Box, wedge, cylinder, cone, sphere, torus, prism from a frame and dimensions → solid Body | Created(`top`, `bottom`, `side(i)`, `cap`) | `Degenerate { parameter }` for zero or negative sizes | ANV-O-OP-1 (exact volume, area, Euler characteristic) | 0 |
| `anvil::curve` | Line, arc, circle, ellipse, conic, helix, spiral, interpolating or approximating spline, curve on surface → wire Body | Created(constructor roles) | `Degenerate`, `ToleranceNotMet { achieved }` | ANV-O-GEOM-1 (closed-form evaluation) | 0; exact helix 2 |
| `anvil::make_regions` | Planar wire Bodies → sheet Body of faces from the planar arrangement, with nested loops; exact predicates for lines and arcs | Created faces, `Bound` discriminators by bounding curves | `OpenProfile { gaps }` with a close-gap fix; `SelfOverlap { curves }` | ANV-O-OP-2 (areas against exact polygon and sector formulas) | 1 |
| `anvil::extrude` | Faces or region sheet; direction; extent as a distance, a `Field`, or up to a face or Body; draft angle; symmetric flag → solid or sheet | Created(`start_cap`, `end_cap`, `side(e)` per profile edge, `lateral(v)` per profile vertex) | `SelfIntersecting` with the largest feasible draft as a fix; `UpToNotReached { target }` | ANV-O-OP-3 (prism and frustum volumes) | 0 |
| `anvil::revolve` | Faces or curves, axis, angle ≤ 2π → solid or sheet; a full revolution creates no seam | Created(`start_cap`, `end_cap`, `side(e)`) | `AxisCrossesProfile { points }`; `Degenerate` | ANV-O-OP-4 (Pappus volumes and areas) | 0 |
| `anvil::sweep` | Profiles, path, frame rule, scale and twist Fields, guide curves → solid or sheet with procedural swept faces | Created(`side(e)`, `start_cap`, `end_cap`, `between(k)`) | `SelfIntersecting { region }` when path curvature times profile extent reaches 1; `FrameUndefined` at Frenet inflections, with a rotation-minimizing-frame fix | ANV-O-OP-5 (torus and helical spring volumes) | 1 |
| `anvil::loft` | Ordered sections, guide curves, end tangency or curvature conditions, vertex correspondence (automatic minimal twist or explicit) → solid or sheet | Created(`side(e, k)` per span, caps) | `IncompatibleSections { loops }`; `Twisted` with a correspondence fix; `ContinuityNotMet` | ANV-O-OP-6 (sections interpolated within τ; ruled lofts equal ruled surfaces) | 1 |
| `anvil::boundary_surface` | Curve network in two directions with G0 to G2 conditions per boundary → face; Gordon surfaces for networks (OCCT 8.0 adds Gordon construction [OCCT 8.0]) | Created(`patch`) | `NetworkNotCompatible { curves }`; `ContinuityNotMet { edge, achieved }` | ANV-O-OP-7 (a network of isoparameter curves reproduces its surface) | 2 |
| `anvil::fill_surface` | Closed n-sided boundary with G0 to G2 per edge, optional interior points and curves → faces | Created(`fill`) | `BoundaryNotClosed { gap }`; `ContinuityNotMet` | ANV-O-OP-8 (continuity measured by `analyze_continuity`) | 2 |
| `anvil::blend_surface` | Two edges or curves on faces, G1 to G3 at each side, shape parameters → bridging face | Created(`bridge`) | `ContinuityNotMet` | ANV-O-OP-8 | 2 |
| `anvil::match_surface` | Face edge to a target edge, G0 to G3, region of influence → modified face | Modified | `CannotMatch { achieved }` | ANV-O-OP-8 | 2 |

### Booleans

All Booleans run on one engine, the cellular arrangement:

1. **Intersect.** Compute every intersection between faces of the operands that overlap in the broad phase: SSI for exact faces, exact arrangements for facets, mixed methods for mixed pairs.
2. **Imprint.** Split faces and edges of every operand along the intersection curves and points.
3. **Merge.** Identify coincident vertices, edges and faces across operands with the tolerance rule (D-ANV-4), growing tolerances within the cap where needed.
4. **Classify.** Assign each 3-cell of the arrangement its membership vector: inside or outside each operand. Membership comes from radial order around edges and one point classification per connected group of cells, as in Lévy's Weiler-model method [Lévy 2024]. Imperfect operands classify by the generalized winding number with threshold 0.5 [Spainhour and Weiss 2025].
5. **Select.** Evaluate the Boolean expression on each cell's membership vector. The expression may be any n-ary formula, not just binary union, subtraction or intersection.
6. **Regularize and simplify.** Remove faces with the same selected cell on both sides, unless the caller keeps internal faces. Merge adjacent faces that share the same surface within tolerance, and merge edges likewise.
7. **Name.** Emit `Split`, `Merged`, `Deleted` and `Created` records for the arrangement's pieces (D-ANV-14).

| Operation | Contract | History | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- | --- |
| `anvil::boolean` | Bodies and an expression (`union`, `subtract`, `intersect`, or an n-ary formula); `keep: Regularized` (default) or `keep: Cells` → one Body; `Cells` returns a cellular Body with every non-empty cell as a region labeled by its membership vector | Split, Merged, Deleted(`Internal`), Created(`intersection_edge`) | `Ambiguous { faces, region }`; `ToleranceGrowth`; `BelowResolution { size }` for slivers smaller than λ; `EmptyResult` only when the caller requires non-empty | ANV-O-BOOL-1 to 6 | 1 (all representations; B-rep on analytic, NURBS and blend surfaces), 2 (hardened on imports) |

`keep: Cells` serves multi-material parts and simulation. Overmolding an insert is `boolean([insert, shot], keep: Cells)` with materials assigned per region, and the result is the conformal multi-region Body that `tetrahedralize` meshes with shared interfaces.

**Decision D-ANV-19:** One cellular arrangement engine implements Booleans for every representation pair without an implicit operand, and the same engine serves n-ary expressions, cell-keeping results, `split`, `imprint` and `interference`. *Why:* these operations differ only in which cells they keep and report, so one tested engine replaces six special cases; cellular output is exactly what multi-material parts and conformal meshing need; Parasolid's Booleans already use imprint, join and select phases [Jackson 1995], and Lévy shows the same structure with an exact Weiler model and arbitrary expressions [Lévy 2024]. *Rejected:* separate union, subtract and intersect code paths (three times the special cases); binary-only Booleans (n-ary unions of many tools would take n − 1 full passes).

### Booleans for every representation pair

| Pair | Result | Method | Guarantee |
| --- | --- | --- | --- |
| B-rep × B-rep | B-rep | Cellular arrangement with certified SSI | Exact topology; geometry within the reported tolerances |
| Mesh × Mesh | Mesh | Exact triangle arrangement with indirect predicates, so constructed points are never rounded during the arrangement [Attene 2020; Cherchi et al. 2022]; exact cell classification; output rounding to `f64` with an exact re-check (below) | Manifold, intersection-free output from manifold input; ε grows by the rounding and repair displacements, which are reported |
| B-rep × Mesh | B-rep with facet faces | Mesh enters as a facet B-rep (D-ANV-2); facet-to-exact intersections certified | Exact faces stay exact |
| SubD × anything explicit | B-rep | SubD enters as subdivision-limit faces | Limit surface preserved where untouched |
| Implicit × anything | Implicit | min, max and negation over the DAG; explicit operands become exact-distance leaves | Exact zero set; distance kind follows D-ANV-10 |

Output rounding is where exact mesh Booleans usually lose their guarantees: Cherchi and colleagues note that converting exact results to floating point is an open problem and use snap-rounding heuristics [Cherchi et al. 2022], and EMBER's export can reintroduce small self-intersections [EMBER 2022]. Anvil rounds each implicit point to the nearest `f64`, then re-checks every triangle pair touched by a moved point with exact predicates. Each conflict (an intersecting or inverted pair) is repaired by collapsing the shortest edge involved, when the link condition allows, and the neighborhood is re-checked.

The loop stops when the exact check passes, so a returned mesh is valid by construction of the stopping rule. If the accumulated displacement would exceed τ_cap, the operation fails with `PrecisionExhausted` and suggests a coarser resolution or a remesh.

**Decision D-ANV-20:** Mesh Booleans use exact arrangements on unquantized `f64` inputs with indirect predicates, exact classification, and checked output rounding with an explicit precision ε. *Why:* inputs keep their full precision (EMBER's 26-bit integer inputs give about 15 nm in a 1 m³ scene [EMBER 2022], coarser than Anvil's 1.9 nm resolution for a Body of that size, whose diagonal is 1.73 m); topology decisions are exact; the output is valid and its rounding error is stated. *Rejected:* Manifold's floating-point method with symbolic perturbation (guaranteed manifold output, but ε-validity is only a goal, by its author's statement [Manifold wiki]); EMBER's integer plane-based representation (quantized input, T-junction polygon soup output that needs topology recovery [EMBER 2022]); linking Manifold or Geogram (C++ FFI; both remain oracles and benchmarks).

Performance targets for Booleans are in the State of the art section. The newest published claim, trueform (July 2026), reports up to two orders of magnitude speedups over prior art with exact predicates and no exact constructions [trueform 2026]; Anvil tracks it as a benchmark to measure, not yet as a method to adopt, because its license and full results were not available.

### Blends

Blending is a research program, as the contract states, and the stages below are its milestones. `anvil::blend` creates fillets on edge chains. `anvil::chamfer` uses the same engine with a ruled cross-section, sized by two distances or by a distance and an angle, and shares the blend's history roles and errors.

| Parameter | Type | Default |
| --- | --- | --- |
| `edges` | EntityId set from a `Query`; tangent-continuous chains are propagated automatically unless `propagate: false` | — |
| `radius` | Length, or `Field<Edges, Length>` for variable radius, or two lengths for asymmetric blends | — |
| `section` | `Circular`, `Conic { rho }`, `CurvatureContinuous { depth }` (G2 to both supports) | `Circular` |
| `corners` | Per vertex: `Auto`, `Setback { distances }`, `Sharp` | `Auto` |
| `overflow` | `RollOver` (ball rolls onto the next face), `KeepEdge` (blend trimmed by the neighboring face), `Fail` | `RollOver` |
| `fallback` | `None` or `Implicit { max_deviation }` | `None` |

The algorithm for each chain:

1. **Spine.** Offset both support surfaces by r toward the side where the ball rolls (into the material for convex edges, out of it for concave edges) and intersect the offsets with certified SSI. The intersection is the spine, the path of the ball's center.
2. **Contact curves.** Project the spine onto both supports to get the two contact curves.
3. **Surface.** Build a procedural rolling-ball blend surface (D-ANV-7), with a certified NURBS approximation within τ.
4. **Overflow.** Intersect the blend with neighboring faces; apply the overflow rule where the ball meets a third face.
5. **Corners.** Blend each vertex where three or more blends meet (below).
6. **Rebuild topology.** Trim supports at the contact curves, insert blend faces, and remove the blended edges.

Vertex blends use the setback split that Várady and Rockwood introduced ("Vertex blending based on the setback split", 1995; see also Várady and Hoffmann, "Vertex blending: problems and solutions", 1998) [Várady publication list]. Each incident blend stops a setback distance before the vertex, and Anvil fills the resulting polygon with an n-sided patch that is G1 to the blends and supports. `Auto` setbacks are the smallest that keep the patch's boundary curves free of self-intersection, found by certified checks on a fixed sequence of candidate values.

| Stage | Capability | Phase |
| --- | --- | --- |
| 1 | Constant-radius circular blends and chamfers on analytic and NURBS supports; edge-chain propagation; `KeepEdge` overflow; three-edge vertex blends with equal radii, because the fillets of golden product 1 meet at corners (general setback blends follow in stage 3, as the contract orders) | 1 |
| 2 | Variable radius from Fields; conic and G2 sections; `RollOver` overflow; asymmetric distances | 2 |
| 3 | Setback vertex blends for any valence and mixed convexity; blends across facet faces | 3 |
| 4 | Blends on blends (rolling over earlier blends), G3 sections for class-A surfacing | 4 |

Failure behavior:

| Error | Meaning | Fixes offered |
| --- | --- | --- |
| `RadiusTooLarge { edge, max_feasible }` | The ball cannot touch both supports | Use `max_feasible`; split the chain |
| `BlendOverflow { faces }` | Overflow rule cannot resolve the third-face contact | Switch overflow rule; reduce radius |
| `VertexBlendFailed { vertex, reason }` | No valid setback patch | Larger setbacks; `Sharp` corner; implicit fallback |
| `SelfIntersecting { region }` | The blend surface folds where the radius exceeds the supports' curvature radius | Reduce radius locally with a Field |

With `fallback: Implicit { max_deviation }`, a failed region is rebuilt as follows. The region is replaced by the zero set of a smooth implicit union of the support faces' exact distances, with blend radius matched to r. That zero set is converted to a B-rep patch, either facet faces or a fitted NURBS face, within `max_deviation` of the zero set.

The patch joins the exact blends with a G0 seam whose gap is measured. The result carries `Note::BlendFallback { region, deviation_from_rolling_ball, seam_gap }`, so the deviation is stated and never silent.

History: `Created { role: blend, from: [edge] }` for each blend face, `Created { role: vertex_blend, from: [vertex] }` for each corner patch, `Deleted { by: blend face }` for each blended edge, and `Modified { aspects: Boundary }` for the trimmed supports. Oracle: ANV-O-BLEND-1 to 4 (fillets on planes, cylinders and cones against closed-form toroidal and cylindrical blends; the spine at distance r from both supports within τ; G1, and G2 for `CurvatureContinuous`, measured by `analyze_continuity`; volume change against closed forms for straight edges).

### Offsets, shells and thickening

| Operation | Contract | History | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- | --- |
| `anvil::offset` | Body and signed distance (value or `Field<Faces, Length>`); corners `Round` (exact Minkowski sum with a ball) or `Natural` (offset surfaces extended and intersected) → Body. Implicit inputs: exact by D-ANV-10. Meshes: feature-preserving mitered offsets [Cao et al. 2024] or rounded offsets from exact distance meshing | Modified faces, Created(`edge_pipe(e)`, `vertex_ball(v)`), Deleted for faces that vanish | `OffsetCollapse { faces }` when a face vanishes and the caller forbade it; `FieldOutOfRange` | ANV-O-OFF-1 (offset sphere, cylinder, torus and box exact; Hausdorff distance from input equals \|d\| within τ) | 1 (B-rep and implicit), 2 (mesh) |
| `anvil::offset_faces` | Selected faces moved along their normals by a distance; neighbors extended or trimmed to keep a closed solid | Modified; Created where neighbors grow | `NeighborCannotExtend { face }` | ANV-O-OFF-2 | 1 |
| `anvil::shell` | Solid, faces to open, thickness (value or Field), inward or outward → hollow solid | Created(`inner(f)` for each offset face), Deleted for opened faces | `WallCollapse { region }` where the thickness exceeds the local inscribed radius | ANV-O-OFF-3 (shelled box and cylinder volumes exact) | 1 |
| `anvil::thicken` | Sheet, thickness (value or Field), side → solid | Created(`front`, `back`, `rim(e)`) | `SelfIntersecting` | ANV-O-OFF-3 | 1 |

`Round` offsets of a B-rep use the exact Minkowski construction. For d > 0, the candidate surfaces are the offset faces, pipe surfaces around convex edges and spheres around convex vertices.

One pass of the cellular engine builds their arrangement, and Anvil keeps the cells whose certified distance to the input is at most d; negative offsets apply the same rule to the complement. Regions where an offset surface folds fall outside the kept cells instead of producing invalid faces.

### Draft

`anvil::draft` tilts faces relative to a pull direction about a neutral element (plane, edges or a parting line), with angle as a value or `Field<Faces, Angle>`. Planes stay planes, cylinders become cones, and other faces become procedural drafted surfaces with certified approximations. Neighbors are extended and re-intersected.

History: `Modified` for drafted faces, `Created` for step faces at a parting line. Failure: `DraftNotPossible { face, reason }` (the face is parallel to the pull direction at the neutral element), `SelfIntersecting`.

Oracle: ANV-O-DRAFT-1 (drafted planar faces measured at the requested angle; analysis agrees with the input angle within 10⁻⁹ rad). Phase 2.

### Split, trim, extend, imprint

| Operation | Contract | History | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- | --- |
| `anvil::split` | Body and tool (plane, sheet, Body); `output: Bodies` (one Body per piece) or `Regions` (one cellular Body) | Split, Created(`cut_face`) | `ToolDoesNotCut`; `OpenTool { gaps }` | ANV-O-BOOL-5 (piece volumes sum to the input) | 1 |
| `anvil::trim` | Sheet and boundary curves or tool; keep side by a point or a `Query` | Split, Deleted | `KeepSideAmbiguous` | ANV-O-TRIM-1 | 1 |
| `anvil::extend` | Face edge, distance or target, mode `Natural` (surface extended analytically), `Linear` or `CurvatureContinuous` | Modified | `CannotExtend { reason }` (surface ends at a singularity) | ANV-O-TRIM-2 (continuity at the old edge) | 1 |
| `anvil::imprint` | Body and curves or another Body → same Body with split faces and edges; volume unchanged | Split, Created(`imprint_edge`) | `CurveNotOnFace { gap }` | ANV-O-BOOL-6 (volume and surface area unchanged) | 1 |

### Transform, pattern, mirror

| Operation | Contract | History | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- | --- |
| `anvil::transform` | Moves a Body: rigid motion, uniform or non-uniform scale, or reflection → the same Body, transformed | EntityIds kept: identity for rigid motions, `Modified { aspects: Geometry }` for scaling and reflection (orientation is restored by flipping senses) | `Degenerate` for zero scale | ANV-O-XF-1 (round trip within one ulp per coordinate) | 0 |
| `anvil::pattern` | Copies a Body or tool: placements (linear, circular, along a curve, mirror, table, or points sampled from a Field) and `combine: Separate`, `Union`, or `Subtract` from a target → Bodies or Body | Each copy's entities get the copy index in their site, so an original and its mirror copy never share EntityIds; Boolean records for combinations | `CopyFailed { index, error }` unless `skip_failed`; `Overlapping { pairs }` when `Separate` requires disjoint copies | ANV-O-PAT-1 (copy counts, transforms, volumes) | 1 |

Patterns combine in one n-ary Boolean, not a chain of binary ones. When copies overlap only the target, not each other, and each copy meets congruent target faces (checked exactly on the defining parameters), the first copy's intersection results are transformed and reused for the others. Reuse is part of the operation's defined behavior, so results stay deterministic.

Five thousand cooling holes in a plate then cost one hole's intersection work plus bookkeeping linear in the count. Implicit patterns use domain repetition and cost nothing per copy.

### Sew, heal and imported geometry

| Operation | Contract | History | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- | --- |
| `anvil::sew` | Sheets and faces, tolerance up to τ_heal → shells or solids; edge pairs matched by certified Hausdorff distance and merged into tolerant edges | Merged (edges, vertices), Modified (faces) | Returns the sewn Body plus `Note::FreeEdges { edges, gaps }`; fails only on `ToleranceGrowth` above the given limit | ANV-O-HEAL-1 (exploded solids re-sew exactly; ABC's STEP files close [STEP distribution unverified]) | 1 |
| `anvil::heal` | Imported Body → valid Body: rebuild parameter curves, close gaps, remove edges and faces below λ, fix orientation and loop nesting, replace degenerate geometry, split self-intersecting loops, recognize analytic surfaces stored as NURBS | Modified, Merged, Deleted with reason per fix; each fix listed with its tolerance change | `Unhealable { entities, reason }` listing what remains invalid; never returns an invalid Body | ANV-O-HEAL-2 (every healed body passes `check_body`; deviation from input within the reported bound) | 1 |
| `anvil::check_body` | Body → list of violations of the four validity conditions | None | — | Oracle of every operation | 0 |
| `anvil::match_bodies` | Old and new import → `HistoryRecord`s between them | As described under naming | `NoCorrespondence` | ANV-O-NAME-4 | 2 |

`anvil::sew` replaces the separate "knit" concept: one operation joins sheets along edges within tolerance. OCCT's 8.0 release notes list Shape Healing fixes for stack overflows and edge multiplication [OCCT 8.0], which shows where healing breaks in practice; Anvil's healing oracle includes those failure classes.

### Direct edits and defeaturing

| Operation | Contract | History | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- | --- |
| `anvil::move_faces` | Faces and a motion (offset, translate, rotate); neighbors re-intersected; used by the Mechanical tab's direct editing and live rules | Modified; Created and Deleted where topology changes | `TopologyChangeRejected` when the caller forbids it | ANV-O-DE-1 | 2 |
| `anvil::replace_faces` | Faces and replacement surfaces → Body with neighbors re-intersected | Modified (EntityIds kept) | `ReplacementDoesNotClose { gaps }` | ANV-O-DE-1 | 2 |
| `anvil::delete_faces` | Faces → Body healed by extending neighbors to close the gap, or a sheet when `heal: false` | Deleted; Merged where neighbors join | `CannotHeal { loop }` with a fill-surface fix | ANV-O-DE-2 (deleting a boss restores the base volume) | 2 |
| `anvil::recognize_aspects` | Body → holes, fillets, chamfers, bosses, pockets, ribs, patterns, each with faces, parameters and confidence | None (read-only) | Unrecognized faces listed | ANV-O-REC-1 (labeled ABC subset; target precision ≥ 0.98 on holes and fillets) | 2 |
| `anvil::recognize_relations` | Faces → coplanar, coaxial, concentric, tangent, perpendicular, symmetric and equal-radius relations decided by the tolerance rule | None | — | ANV-O-REC-2 | 2 |
| `anvil::defeature` | Body and rules (aspect kinds below sizes, or explicit faces) → simplified Body; recognize, then delete faces | Deleted with the aspect as reason | `CannotHeal` per aspect, other aspects still removed when `partial: true` | ANV-O-DE-3 (volume change equals removed aspect volumes) | 2 |

### Mid-surface extraction

`anvil::mid_surface` turns a thin-walled solid into a sheet Body plus a thickness `Field<Faces, Length>` for Flux shells:

1. Pair faces that are offsets of each other within a thickness range, using certified distance and normal tests.
2. Build each pair's mid-surface: exact for plane, cylinder and cone pairs; a procedural mid-surface with a certified approximation otherwise.
3. Extend mid-surfaces and intersect them at junctions (T-joints and corners); trim to the solid.
4. Treat unpaired regions, such as rib ends and bosses, by the 3D medial axis where it is thin, or report them.

History: `Created { role: mid(face_a, face_b) }`, so a shell boundary condition can still reference the solid's face. Failure: `UnpairedFaces { faces, reason }` with the partial sheet.

Oracle: ANV-O-MID-1 (sheet-metal and plate test bodies with known mid-surfaces; the thickness Field matches the paired distance within τ). Phase 2, for golden product 4.

### Section, project and wrap

| Operation | Contract | History | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- | --- |
| `anvil::section` | Body and a plane, a stack of parallel planes, or a surface → planar region Bodies per plane (sheets with loops) or curves; any representation | Created(`section_edge`) from faces | `NotClosed { gaps }` names the defective faces | ANV-O-SEC-1 (areas per plane equal the integrated cross-section within the bound; closed forms for quadrics) | 1 |
| `anvil::project_curve` | Curves onto faces along a direction or the surface normal → curves on surface | Created(`projection`) | `Misses { segments }` | ANV-O-PROJ-1 | 1 |
| `anvil::parameterize` | Faces or a mesh region → a (u, v) map: Boundary First Flattening with boundary length or angle control and cone singularities, as the Mechanical tab decided; or least-squares conformal; or isometric for developable faces | None | `NotDisk { genus }` with cut suggestions | ANV-O-PAR-1 (angle distortion within the method's reference value) | 2 |
| `anvil::wrap` | Planar curves or a planar sheet onto a target face through a map from `parameterize` → curves or faces on the target; emboss and deboss through `offset_faces` | Created(`wrapped`) | `OutOfDomain { curves }` | ANV-O-PROJ-2 (lengths on developable targets preserved within τ) | 2 |
| `anvil::unfold`, `anvil::fold` | Sheet-metal bodies with developable faces and a neutral-layer offset per bend (from the K-factor the feature supplies) → flat pattern, and back | Identity between folded and flat faces; Created(`bend_line`) | `NotDevelopable { faces, deviation }` | ANV-O-SM-1 (fold of unfold returns the input within τ) | 2 |

### Deform and morph

| Operation | Contract | History | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- | --- |
| `anvil::deform` | Body and a displacement `Field<Body, Displacement>` or a lattice (cage, radial basis, free-form deformation) → deformed Body in the same representation. B-rep: control points of NURBS faces move, and analytic faces are converted to NURBS only where the Field is non-rigid on them; meshes and SubD cages move vertices; implicits compose with the inverse map | Modified (EntityIds kept) | `FoldOver { region }` when the map's Jacobian determinant reaches zero; `ToleranceNotMet { achieved }` | ANV-O-DEF-1 (rigid Fields reproduce `transform` exactly; deviation from the exact deformed surface within the bound) | 2 |
| `anvil::morph` | Source Body, target Body or point correspondences → deformation Field that maps one onto the other, then `deform` | Modified | `NoCorrespondence` | ANV-O-DEF-2 | 3 |
| `anvil::shrinkwrap` | Bodies and a gap size → one closed outer skin: implicit union, closing by offset +g then −g on exact distances, mesh or B-rep output | Created(`skin`) | `BudgetExceeded` | ANV-O-OFF-4 (skin within g of the input everywhere outside; watertight) | 2 |

`deform` is how distortion compensation works in the Manufacturing tab (D-MFG-13): MFG inverts a predicted displacement Field and Anvil applies it. The deformed B-rep's error is the difference between the exact composed surface S(u, v) + d(S(u, v)) and the fitted NURBS, bounded by certified sampling plus the Field's reported sampling error.

### Mesh processing operations

Mesh operations not already described under the mesh representation:

| Operation | Contract | History | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- | --- |
| `anvil::mesh_from_triangles` | Triangle and index buffers → Mesh, or facet B-rep for intended non-manifold data | Created face groups | `NotManifold { edges, vertices }` | ANV-O-MESH-1 | 0 |
| `anvil::repair_mesh` | As described above | Modified, Deleted, Created(`fill`) | `Unrepairable { reason }` | ANV-O-MESH-2 (Thingi10K) | 1 |
| `anvil::segment_mesh` | Mesh → face groups by curvature and normal clustering, with crease edges | Split of face groups | — | ANV-O-MESH-3 (labeled segmentations) | 3 |
| `anvil::align` | Source and target Bodies, optional initial transform → rigid transform by point-to-plane iterative closest point with trimmed outliers; deterministic sample selection from a fixed sequence | None | `NotConverged { rms }` | ANV-O-FIT-1 (known transforms recovered within 10⁻⁶ of the Body diagonal) | 4 |
| `anvil::fit` | Points or a mesh region and a model kind (plane, sphere, cylinder, cone, torus, NURBS of given degree and knots, SubD cage) → geometry plus residual statistics | Created(`fitted`) | `FitFailed { residual }` | ANV-O-FIT-2 (exact recovery from exact samples; noise-level residuals) | 1 (primitives), 4 (freeform) |
| `anvil::voxelize` | Body and voxel size → occupancy grid or narrow-band distance grid; inside test by winding number | None | `BudgetExceeded { voxels }` | ANV-O-VOX-1 (voxel volume converges to the exact volume at first order in h) | 1 |
| `anvil::correlate_grids` | Two occupancy grids → exact integer correlation counts (FFT with a proven rounding bound below 0.5, otherwise direct integer correlation), as decided by MFG (D-MFG-12) | None | `BudgetExceeded` | ANV-O-VOX-2 (equality with direct integer correlation) | 2 |
| `anvil::common_refinement` | Two discretizations of one interface (meshes or faces) → their overlay, each piece mapped to its parent cell on both sides, built by exact arrangement in a shared parameterization; Flux uses it for conservative interface transfer | Created(`piece`) with both parents | `NotSameInterface { gap }` when the two sides deviate by more than their tolerances | ANV-O-MESH-4 (piece areas sum to each side's area within the bound) | 4 |

### Geometry access

| Operation | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| `anvil::evaluate` | Curve or face EntityIds and parameters → positions and derivatives to third order, exact | `OutOfDomain { parameters }` | ANV-O-GEOM-1 | 0 |
| `anvil::sample` | Faces or curves and a density or count → points with EntityId and (u, v), in a deterministic low-discrepancy pattern | — | ANV-O-GEOM-2 (coverage and determinism) | 1 |
| `anvil::intersect` | Two entity sets (curves, faces, Bodies) → points and curves as a new wire Body with `Created(intersection)` records, classified transversal, tangent or overlap | `Ambiguous { entities, region }` | ANV-O-SSI-1 to 3 | 1 |
| `anvil::approximate` | Curves or faces → NURBS within a tolerance, for export and downstream fitting | `ToleranceNotMet { achieved }` | ANV-O-GEOM-3 (certified deviation within the request) | 1 |

### Mass properties

`anvil::mass_properties` returns volume, area, mass, center of mass and the inertia tensor about the center and principal axes, with an `ErrorBound` per quantity.

| Representation | Method | Error |
| --- | --- | --- |
| B-rep | Divergence theorem: volume integrals become surface integrals of polynomial fields, and on each trimmed face the surface integral becomes a line integral over its loops in parameter space (Green's theorem), evaluated with adaptive Gauss-Legendre quadrature on exact geometry; each panel's remainder is bounded by interval enclosures of the integrand's derivatives | `Guaranteed` from the certified remainders plus the certified approximation of procedural faces |
| Mesh | Exact closed-form sums over signed tetrahedra from a frame-local origin, summed with a fixed-order compensated reduction | `Guaranteed` at the rounding level, plus the mesh's ε times surface area |
| SubD | Converted to exact B-rep faces internally | As B-rep |
| Implicit | Adaptive octree with interval classification: inside cells exactly, ambiguous cells by subdivision to λ, then the residual cells bounded by their volume | `Guaranteed` two-sided bounds |
| Multi-region | Per region with its material density; densities may be `Field`s, integrated with the region | Sum of parts |

Each quantity is computed in the Body frame, which keeps cancellation small for parts far from the world origin. Oracle: ANV-O-MP-1 (closed-form volumes, centroids and inertia of primitives, shelled primitives, tori, and Pappus solids; agreement between B-rep, mesh and implicit forms of the same body within their bounds). Phase 0 (meshes), 1 (all).

### Distance, clearance and interference

| Operation | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| `anvil::distance` | Two Bodies or entity sets, optional upper bound → minimum distance, witness points with EntityIds and (u, v), certified enclosure; `signed` for penetration depth | `NotSeparated` only when the caller requires positive distance | ANV-O-DIST-1 (closed forms for analytic pairs; agreement across representations) | 1 |
| `anvil::closest_point` | Points and a Body → closest point, EntityId, (u, v), signed distance with winding-number sign | — | ANV-O-DIST-2 | 0 |
| `anvil::interference` | Bodies (Instances with placements), clearance threshold → pairs classified as `Separated { distance }`, `Touching { region }`, `Clearance { min }` below threshold, or `Overlapping { volume, region }` | `BudgetExceeded` | ANV-O-DIST-3 (known assemblies; overlap volumes against Boolean intersection volume) | 1 |
| `anvil::ray_cast` | Rays and a Body → first hits with EntityId, (u, v), normal; certified for exact faces | — | ANV-O-DIST-4 | 1 |
| `anvil::deviation` | Two Bodies → signed deviation `Field<Faces, Length>` on each, with certified one-sided and two-sided Hausdorff bounds; serves proposal geometry overlays, scan-to-CAD inspection and conversion checks | `BudgetExceeded` | ANV-O-DIST-5 (offset copies deviate by exactly the offset) | 1 |

Distance uses branch-and-bound over both Bodies' hierarchies with conservative distance bounds, then a certified local solve for the closest pair (Krawczyk on the first-order optimality conditions). Signed distance to imperfect geometry takes its sign from the generalized winding number on trimmed surfaces [Spainhour and Weiss 2025], accelerated with the hierarchical far-field expansion that Spainhour, Whitlock and Weiss describe, which turns some 10³-second direct evaluations into sub-second ones [Spainhour, Whitlock and Weiss 2026].

Assembly interference runs in three steps: GPU integer box culling over all Instance pairs (D-ANV-17), CPU certified distance on surviving pairs, and Boolean intersection volume only for overlapping pairs. Pairs are processed in canonical Instance order, so results are deterministic.

### Analysis: curvature, continuity, draft and thickness

| Operation | Contract | Oracle | Phase |
| --- | --- | --- | --- |
| `anvil::curvature` | Faces or curves → Fields of principal, Gaussian and mean curvature (surfaces), curvature and torsion (curves), with certified extremes; singular points reported, not numbers | ANV-O-AN-1 (closed forms on quadrics and tori) | 1 |
| `anvil::analyze_continuity` | Edges between faces, or curve joins → G0 gap, G1 angle, G2 curvature mismatch, G3 rate-of-curvature mismatch, each as a certified maximum along the edge and as a Field for display | ANV-O-AN-2 (constructed G1, G2, G3 joins measured correctly; known discontinuities detected) | 1 (G0 to G2), 2 (G3) |
| `anvil::isophotes` | Faces, light direction, angles → curves on surface (isophote lines and reflection lines) | ANV-O-AN-2 | 2 |
| `anvil::draft_analysis` | Faces, pull direction, minimum angle → per-face `Field<Faces, Angle>` and regions classified as positive draft, negative draft, below minimum, or vertical; split curves certified | ANV-O-AN-3 (cones and drafted planes at known angles) | 2 |
| `anvil::thickness` | Body → local thickness `Field<Body, Length>` by `method: Sphere` (largest inscribed sphere touching the point, via the medial axis) or `Ray` (opposite-normal ray), with certified minimum location | ANV-O-AN-4 (plates, tubes and wedges with closed-form thickness) | 1 |
| `anvil::medial_axis` | Planar regions → segment Voronoi skeleton with exact predicates, arcs decided by certified interval predicates under the tolerance rule; solids → certified medial approximation from narrow-band distance with a stated Hausdorff bound | ANV-O-AN-5 (rectangles, discs, L-shapes against closed forms in 2D) | 1 (2D), 2 (3D) |
| `anvil::silhouette` | Body and view direction or eye point → silhouette curves on faces (where n · v = 0), certified | ANV-O-AN-6 | 1 |
| `anvil::project_hlr` | Body and a view → visible and hidden edges and silhouettes, projected; lines and circles exact, freeform edges approximated with bounds (drawings for golden product 1) | ANV-O-AN-6 (hidden-line results of reference views) | 1 |
| `anvil::visibility` | Body and directions → per-face visibility Fields for tool access or line of sight | ANV-O-AN-7 | 2 |
| `anvil::draft_map` | Body and direction set → per-face feasible draw directions, for mold parting search | ANV-O-AN-3 | 3 |

The UI tab owns how analyses look. Anvil returns them as Fields, which the UI paints on the exact geometry through the display tessellation's `(EntityId, u, v)` back-references.

### Manufacturing geometry

| Operation | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| `anvil::tool_contact` | Revolved tool profile (flat, ball, bull, taper, generic), positions and a motion direction, target Body → first-contact heights or distances with contact EntityId; exact contact classification against analytic and facet faces | `BudgetExceeded` | ANV-O-MFG-1 (drop and push cutter against analytic surfaces) | 1 |
| `anvil::swept_volume` | Body or tool profile and a motion (3-axis or 5-axis path with orientations) → narrow-band implicit envelope with an `ErrorBound` | `BudgetExceeded` | ANV-O-MFG-2 (swept spheres and cylinders along straight and circular paths exact) | 1 (3-axis), 2 (5-axis) |
| `anvil::offset_curve` | Planar curves, distance, corner rule; lines and arcs stay lines and arcs, as the Manufacturing tab requires; curves on surfaces offset geodesically | `Degenerate` | ANV-O-MFG-3 | 1 |

### Constraint solving and shape velocity

The Mechanical tab owns the semantics of `anvil::solve_constraints` and `anvil::analyze_constraints` (D-MEC-3, D-MEC-11, D-MEC-21). Anvil provides them as ordinary versioned operations with Anvil's evaluators, exact rational rank computations and canonical ordering. Their oracles and phases are those of the Mechanical tab.

`anvil::shape_velocity` gives Flux the derivative of geometry with respect to an Ingot parameter, as a `Field<Faces, Displacement>` per unit change. Anvil differentiates each operation's construction in forward mode: every geometry constructor has a tangent rule, so a parameter's tangent propagates through the operation sequence of the build. A tangent is defined only where topology is locally constant; at a topology change (a face appearing or vanishing) the velocity Field is marked `Singular` there, as Flux's `SampleFlags` allow.

Oracle: ANV-O-SV-1 (finite differences of rebuilt geometry agree with the velocity Field within the step-size error, on parameterized primitives, extrudes and fillets). Phase 2.

### Tessellation and level of detail

`anvil::tessellate` produces display and export meshes from any representation.

| Parameter | Meaning |
| --- | --- |
| `chord` | Maximum distance between mesh and surface |
| `angle` | Maximum normal deviation between mesh and surface |
| `edge_length` | Optional maximum edge length |
| `view` | Optional camera, for screen-space error |

Output: a Mesh Body whose face groups carry the source faces' EntityIds, with per-vertex `(EntityId, u, v)` back-references for painting Fields, and a `Guaranteed` chord bound per face from certified sampling. Shared edges are discretized once by edge parameter, so the mesh is watertight by construction (the same-parameter rule above).

Level of detail uses a per-face hierarchy: each face is tessellated at a geometric series of chord tolerances, and levels share boundary vertices on every edge, so neighboring faces at different levels never crack. The UI selects levels by screen-space error and streams changed triangles, as the contract requires. ETER shows that pixel-accurate tessellation of NURBS on the GPU can replace pre-tessellation [ETER]; Anvil adopts GPU tessellation for previews and interactive views only (phase 3), because the canonical exported mesh must be bit-identical.

Failure behavior: none for valid Bodies; `BudgetExceeded { triangles }` when a tolerance demands too many triangles. Oracle: ANV-O-TESS-1 (certified chord bound; watertightness; face-group EntityIds equal source faces). Phase 0.

### Point and solid classification

| Operation | Contract | Method | Oracle | Phase |
| --- | --- | --- | --- | --- |
| `anvil::classify_points` | Points → `Inside`, `Outside` or `On { entity }` per point, with the tolerance applied | Exact predicates for meshes; generalized winding number with certified near-surface correction for B-reps [Spainhour and Weiss 2025]; interval evaluation for implicits | ANV-O-CLS-1 (agreement across representations; points near faces at distances ±τ/2 and ±2τ) | 0 |
| `anvil::classify_box` | Box → `Inside`, `Outside` or `Cut`, certified, for Flux's immersed methods | Interval evaluation of the winding number or implicit; hierarchy culling | ANV-O-CLS-2 | 1 |
| `anvil::classify_body` | Body against Body → each face of A classified as inside, outside or on B | Arrangement-free: point classification of face samples plus SSI only where faces approach | ANV-O-CLS-3 | 1 |

### Geometry queries for simulation

Anvil implements the `GeometryQuery` trait that the Flux tab requires for every representation: `classify_box`, `closest_point`, certified `moments` over a box (by the divergence theorem on the trimmed surface, as for mass properties), `surface_quadrature` over a box, and `local_thickness`. Moments return a guaranteed error, which Flux uses to bound cut-cell quadrature error.

A cut that Anvil cannot certify within fuel returns `Uncertified { achieved }`, and Flux then subdivides or fails with `UncertifiedCut`, as its tab specifies. Phase 1.

### Draping

`anvil::drape_kinematic` maps a woven fabric onto a tool surface by the kinematic (pin-jointed net) method that the Mechanical tab specifies: inextensible fibers, constant step length, seed point and two fixed fibers, quadrants draped independently in a fixed order. Output: fiber curves on the surface and a shear-angle `Field<Faces, Angle>`. Failure: `ExcessiveShear { region, angle }` beyond the fabric's locking angle.

Oracle: ANV-O-DRAPE-1 (drape on a hemisphere against published shear patterns). Phase 4.

## Conversions

`anvil::convert(body, into: Repr, accuracy: Length, options) -> (Body, ErrorBound)` is the only conversion operation. The `ErrorBound` uses the shared type `{ value, norm, kind }` (CCR-ANV-1); for geometry the norm is the two-sided Hausdorff distance unless stated.

| From → To | Method | Error bound | Topology and names | Phase |
| --- | --- | --- | --- | --- |
| BRep → Mesh | Tessellation with certified chord control | `Guaranteed`, value ≤ requested chord | Watertight; face groups keep face EntityIds | 0 |
| BRep → Implicit | Exact signed distance leaf with winding-number sign | Zero: exact | Leaf references the B-rep's content hash | 1 |
| BRep → SubD | Feature-aligned quad remesh, then cage fit | `Estimated` (fit residual) | Cage faces get `Created { from: face }` | 4 |
| Mesh → BRep (facet) | Facet faces per face group | Zero: exact | Face groups become faces with the same EntityIds | 1 |
| Mesh → BRep (fitted) | Segment, fit primitives and NURBS per segment, intersect neighbors, sew | `Estimated` from residuals, `Guaranteed` after a certified Hausdorff check if requested | New faces `Created { from: face_group }` | 4 |
| Mesh → Implicit | Exact signed distance to triangles, winding-number sign | Zero: exact | Leaf references the mesh | 1 |
| Mesh → SubD | Mesh as cage | Not an approximation of the mesh: the limit surface differs, and the deviation is reported as `Estimated` | Cage elements keep group ids | 3 |
| Implicit → Mesh | Certified adaptive dual contouring | Two-sided, `Guaranteed` in certified cells and `Estimated` in flagged cells | Face groups labeled by active DAG leaves | 1 |
| Implicit → BRep | Mesh as above, then facet faces; or fitted NURBS per leaf region with exact analytic faces recovered where the active leaf is an analytic primitive | Facet path as Implicit → Mesh; fitted faces `Estimated` until a certified deviation check | Faces labeled by active leaves | 1 (facet), 3 (fitted) |
| SubD → BRep | Exact limit faces, or NURBS with bicubic patches and certified approximation near extraordinary vertices | Zero (exact mode); `Guaranteed` (NURBS mode) | Faces keep cage-face EntityIds | 3 |
| SubD → Mesh | Limit tessellation | `Guaranteed` chord bound | As B-rep tessellation | 3 |
| SubD → Implicit | Through exact B-rep faces | Zero | — | 3 |
| Implicit → SubD | Implicit → Mesh, then a cage fit as for BRep → SubD | `Estimated` (meshing bound plus fit residual) | Cage faces labeled by active DAG leaves | 4 |

Every conversion records its bound on each face it produces, and bounds compose by addition along a chain of conversions, since Hausdorff distance obeys the triangle inequality. Later operations keep each face's bound, because a trimmed face still deviates from its source surface by at most that amount, and faces derived from bounded faces (offsets, blends) inherit the largest bound of their sources.

A Body's bound is the maximum over its faces. A Check can therefore require `body.error() < 10µm` and fail with the contributing faces and conversions listed.

The bound describes geometry, not topology. A near-tangent configuration can resolve differently on converted inputs than on the originals, and the tolerance rule reports such cases as tolerance growth, not as part of the bound.

**Decision D-ANV-21:** Inclusions in the representation lattice are exact (zero error), and approximating conversions record Hausdorff bounds per face that compose along conversion chains and survive later operations. *Why:* mixed operations then never approximate, and a check can bound the geometric error of any Body regardless of how many conversions produced it. *Rejected:* per-call error reports only (lost after the next operation); one bound per Body (a local conversion would taint every face); RMS error metrics (hide the worst deviation, which is what tolerances and fits care about).

## Performance, parallelism and determinism

### Determinism rules

Anvil inherits the contract's determinism principle and the PLT and Flux mechanisms: the `cpu-f64` platform class spans every Tier 1 CPU target, native and Wasm (D-FLX-19), with correctly rounded math from `detmath` and no implicit FMA (Rust's strict IEEE semantics rule out implicit contraction [RFC 3514]). Anvil adds rules for its own code:

1. **Canonical order everywhere.** Every set that an algorithm iterates is sorted by a content-derived key (EntityId, Morton code, canonical vertex order). No `HashMap` iteration order, no pointer order and no thread arrival order reaches output.
2. **Fixed reduction trees.** Sums (volumes, moments, energies) use compensated summation over a fixed binary tree defined by the data's canonical order, not by the thread schedule.
3. **Explicit FMA only.** Anvil calls `mul_add` only where an algorithm states it, such as TwoProduct. Rust guarantees that `mul_add` returns the correctly rounded fused result, "guaranteed not to change", while its speed depends on hardware FMA [Rust f64 docs]. All targets therefore produce the same bits. This does not conflict with D-FLX-8, which forbids implicit fusion in generated kernels; on x86-64-v2 hardware without FMA, TwoProduct uses Dekker splitting, which yields the same exact error term.
4. **Deterministic parallel decomposition.** Parallel work splits by data (patch pairs, octree cells, independent sets), never by worker count. Each task's output has a canonical position, and results merge in canonical order.
5. **No GPU-defined answers.** GPU results are exact integer culls, work orderings or previews (D-ANV-17). Algorithms whose output could depend on work order, such as SSI tracing, start from canonical points. The one GPU computation with a canonical output, grid correlation, rounds to integers under a proven error bound.
6. **Counted fuel.** Budgets count work units, never time.
7. **NaN never leaks.** NaN bit patterns are non-deterministic in Rust and Wasm [RFC 3514; Wasm nondeterminism]. Anvil checks every construction result for finiteness and turns NaN or infinity into a typed error at the source, and the encoding rejects them.

Canonical Anvil results exist only in the `cpu-f64` platform class, which spans every Tier 1 CPU target. GPU platform classes never produce canonical Anvil outputs, so Anvil results agree exactly across platform classes, and the contract's "within declared tolerance" clause is needed only for Flux's GPU solves.

Parallel mesh algorithms (remeshing, adaptation, untangling, Delaunay refinement) use independent-set scheduling. Each round computes a maximal independent set of non-conflicting local operations by priority, where the priority is a hash of the element's deterministic id (derived from its parents' ids when it was created) and the round number.

The operations of a round apply in parallel; rounds repeat until no operation remains. The result is identical for any number of threads, because the set chosen in each round depends only on the mesh.

**Decision D-ANV-22:** Anvil achieves determinism under parallelism by data-defined decomposition, canonical merge order, fixed reduction trees and independent-set scheduling for mesh modification. *Why:* these give identical bits for any thread count without locks around floating-point state, and they parallelize well; graph-coloring or randomized schedules would tie output to thread count or random seeds. *Rejected:* single-threaded exact mode (wastes cores on the 2-second rebuild target); deterministic replay logs (heavy and fragile).

### Parallelism

| Level | Mechanism | Examples |
| --- | --- | --- |
| Across operations | Kiln schedules independent Ops in parallel | Features on separate Bodies, independent pattern copies, Instances in an assembly |
| Within an operation | Data-parallel tasks on the PLT `runtime` pool | SSI over candidate patch pairs, face-pair intersections in Booleans, tessellation per face, distance over hierarchy subtrees, octree cells in implicit meshing |
| SIMD | 8-lane `f64` and 16-lane `f32` batches through the PLT `simd` crate's canonical lanes | NURBS evaluation (de Boor in batches of parameters), interval arithmetic, implicit tapes, predicate filters, box tests |
| GPU | wgpu compute through the PLT `gpu` crate, with a CPU path for each kernel | Integer broad phase for intersections and interference; preview tessellation and NURBS evaluation; implicit preview rendering and culling; `correlate_grids` |

Predicate filters vectorize well because the static filter is a fixed sequence of multiplications and additions; only lanes that fail the filter fall to the scalar exact path.

### Performance targets

Targets are on the reference laptop that phase 0 fixes. All are targets, not measurements.

| Workload | Target |
| --- | --- |
| Rebuild of a 200-feature part after an early edit (contract) | Anvil share ≤ 1.2 s of the 2 s budget, with Kiln backdating unchanged features |
| B-rep Boolean, two bodies of 500 faces each, analytic and NURBS mix | ≤ 50 ms exact |
| Constant-radius fillet chain of 50 edges | ≤ 100 ms exact |
| Mesh Boolean, 1 million triangles total | ≤ 70 ms on 8 cores, 2× EMBER's reported 34 ms for 1.2 million triangles [EMBER 2022]. Deviation: unquantized `f64` input and a valid triangulated output cost more than EMBER's integer polygon soup |
| Implicit lattice bracket (golden product 2), 10⁵ cells, preview render | 60 fps at 1080p on the reference GPU; exact mesh at 50 µm chord in ≤ 10 s |
| Tessellation of a 10,000-face part at 0.01 mm chord | ≤ 200 ms |
| Interference of a 1,000-part assembly | ≤ 1 s from warm cache |
| Conforming tetrahedralization, 10⁶ elements | ≤ 10 s on 8 cores |
| Coarse drag preview (contract) | ≤ 100 ms including preview Booleans and tessellation |

### GPU use

The `gpu` crate gives Anvil one compute abstraction over wgpu and a CPU fallback for every kernel, per the contract. Anvil's GPU kernels:

| Kernel | Precision | Role | Canonical? |
| --- | --- | --- | --- |
| Integer box overlap and hierarchy traversal | Integer | Broad phase for intersection, interference, classification | Yes, bit-identical with CPU |
| NURBS and subdivision evaluation on grids, with per-cell boxes | `f32` | Preview tessellation, display level of detail, SSI work ordering (D-ANV-17) | No; affects speed only |
| Implicit tape interpreter with interval pruning | `f32` intervals with outward rounding by one ulp per operation | Preview rendering, culling in previews | No |
| Grid correlation | `f32` FFT with proven rounding bound, integer output | `correlate_grids` (D-MFG-12) | Yes, once WGSL accuracy is verified (open question 6); until then the CPU path (`f64` FFT with a proven bound, or direct integer correlation) is canonical and the GPU result only orders work |

GPU interval arithmetic cannot rely on rounding modes, so the interpreter widens every operation's result by one ulp on each side. That keeps enclosures conservative for basic operations under WGSL's accuracy rules, but those rules could not be verified for this draft [unverified: WGSL ulp bounds for `+`, `×`, `/`, `sqrt`]; until verified, GPU interval results only order and prune preview work.

## Rust API

The signatures below are illustrative but plausible; they fix names, ownership and error shapes. Units are SI `f64` inside Anvil; Ingot's `Quantity` checks happen before the call.

### Core values (`anvil-geom`, `anvil-topo`, `anvil-ops`)

```rust
/// 128-bit provenance id: SHA-256 prefix of (kind, site, role, inputs, discriminator).
#[derive(Copy, Clone, Eq, PartialEq, Ord, PartialOrd, Hash, Debug)]
pub struct EntityId(pub [u8; 16]);

#[derive(Copy, Clone, Eq, PartialEq, Ord, PartialOrd, Hash, Debug)]
pub enum EntityKind { Region, Shell, Face, Loop, Edge, Vertex, FaceGroup, CreaseEdge, CageFace, CageEdge, CageVertex, ExprNode }

/// Structural identity of an Op call: feature instance path, call-site key, loop and pattern indices.
/// Never contains argument values (D-ANV-14).
#[derive(Clone, Eq, PartialEq, Ord, PartialOrd, Hash, Debug)]
pub struct OpSite { pub path: Box<[SiteSegment]>, pub indices: Box<[u32]> }

#[derive(Clone, Eq, PartialEq, Ord, PartialOrd, Hash, Debug)]
pub enum Discriminator { Bound(Box<[EntityId]>), Side { cause: EntityId, sense: Sense }, Ordinal(u32) }

/// Shared with Flux (CCR-ANV-1, CCR-FLX-1); defined here, in the lowest crate that needs it.
#[derive(Copy, Clone, Debug, PartialEq)]
pub struct ErrorBound { pub value: f64, pub norm: Norm, pub kind: Guarantee }

#[derive(Clone, Debug)]
pub enum HistoryRecord {
    Created  { out: EntityId, role: Role, from: Box<[EntityId]> },
    Modified { id: EntityId, aspects: Aspects },               // Geometry | Boundary | Tolerance | Attributes
    Split    { from: EntityId, into: Box<[EntityId]> },
    Merged   { from: Box<[EntityId]>, into: EntityId },
    Deleted  { id: EntityId, by: Option<EntityId>, reason: DeleteReason },
}

/// Immutable, cheaply clonable; storage shared between versions.
#[derive(Clone)]
pub struct Body { repr: Repr, frame: Frame, resolution: Resolution, regions: Regions, meta: Arc<BodyMeta> }

#[derive(Clone)]
pub enum Repr { BRep(Arc<BRep>), Implicit(Arc<Implicit>), Mesh(Arc<Mesh>), SubD(Arc<SubD>) }

impl Body {
    pub fn content_hash(&self) -> Sha256;                    // over the canonical encoding
    pub fn error(&self) -> ErrorBound;                      // maximum of per-face conversion bounds (D-ANV-21)
    pub fn resolution(&self) -> Resolution;
    pub fn entity(&self, id: EntityId) -> Option<EntityRef<'_>>;
    pub fn lineage(&self) -> &Lineage;
    pub fn encode(&self, w: &mut impl io::Write) -> Result<(), EncodingError>;
    pub fn decode(r: &mut impl io::Read) -> Result<Body, EncodingError>;
}
```

### Geometry traits (`anvil-geom`)

```rust
pub trait Curve: Send + Sync {
    fn domain(&self) -> Interval;
    fn periodic(&self) -> Option<f64>;
    /// Position and derivatives up to `order` (≤ 3) at each parameter; fixed operation order.
    fn eval(&self, t: &[f64], order: u8, out: &mut CurveSamples);
    /// Certified enclosure of the curve and its tangent cone over a parameter interval.
    fn bound(&self, t: Interval) -> CurveBound;
    fn to_nurbs(&self, tol: f64) -> (NurbsCurve, ErrorBound);
}

pub trait Surface: Send + Sync {
    fn domain(&self) -> Box2;
    fn periodic(&self) -> [Option<f64>; 2];
    fn singular_points(&self) -> &[Point2];
    fn eval(&self, uv: &[Point2], order: u8, out: &mut SurfaceSamples);
    fn bound(&self, uv: Box2) -> SurfaceBound;               // box, normal cone, curvature bound
    fn closest(&self, p: Point3, seed: Option<Point2>) -> Result<SurfacePoint, GeomError>;
    fn to_nurbs(&self, tol: f64) -> (NurbsSurface, ErrorBound);
}

/// Exact and filtered predicates generated at build time (D-ANV-5).
pub mod predicates {
    pub fn orient3d(a: Point3, b: Point3, c: Point3, d: Point3) -> Sign;
    pub fn insphere(a: Point3, b: Point3, c: Point3, d: Point3, e: Point3) -> Sign;
    pub fn orient3d_implicit(a: ImplicitPoint, b: Point3, c: Point3, d: Point3) -> Sign;
}

/// The tolerance rule of D-ANV-4.
pub enum Decision { Coincident, Separated(Sign), Grown { new_tolerance: f64 } }
pub fn decide(enclosure: Interval, tol: f64, cap: f64, fuel: &mut Fuel,
              refine: impl FnMut(&mut Fuel) -> Option<Interval>) -> Result<Decision, Ambiguous>;
```

### Operations (`anvil-ops`)

```rust
pub trait Operation: Send + Sync + 'static {
    const NAME: &'static str;            // "blend"
    const VERSION: u32;                  // 2  => anvil::blend@2
    type Args: Canonical;                // hashed into the Op cache key
    type Output: Canonical;

    fn run(&self, cx: &mut OpContext<'_>, args: &Self::Args) -> Result<OpOutput<Self::Output>, OpError>;
}

pub struct OpContext<'a> {
    pub site: &'a OpSite,
    pub fidelity: Fidelity,              // Exact | Preview: geometry side of interactive and sign-off modes
    pub fuel: Fuel,                      // counted work units, never time
    pub fields: &'a FieldInputs,         // Kiln-supplied Flux `Sampler`s for the FieldRef arguments (D-FLX-1)
    pub gpu: Option<&'a gpu::Device>,    // proposals only; None gives identical Exact results
    pub cancel: &'a CancelToken,         // cancellation returns no result, never a different one
}

pub struct OpOutput<T> { pub value: T, pub history: Vec<HistoryRecord>, pub error: ErrorBound, pub notes: Vec<Note> }

/// Visible, non-fatal facts about a result; checks may forbid any of them.
#[non_exhaustive]
pub enum Note {
    Merged { with: Vec<EntityId> },              // query anchor merged (CCR-ANV-4)
    Partial { deleted: Vec<EntityId> },           // some descendants of an anchor were deleted
    FragileAnchor { id: EntityId },               // anchor uses an Ordinal discriminator
    ResolutionCoarsened { from: f64, to: f64 },
    ToleranceGrown { entity: EntityId, from: f64, to: f64 },
    BlendFallback { region: Vec<EntityId>, deviation_from_rolling_ball: f64, seam_gap: f64 },
    FreeEdges { edges: Vec<EntityId>, gaps: Vec<f64> },
    CellsDropped,                                 // a volume mesh entered a solid operation
    DeprecatedBehavior { op: OpName, current: u32, migration: String },
}

#[derive(Debug)]
pub struct OpError {
    pub kind: OpErrorKind,               // RadiusTooLarge { edge, max_feasible }, Ambiguous { .. }, ...
    pub why: String,                     // one calm sentence
    pub fixes: Vec<Fix>,                 // typed source edits, ranked
    pub at: Vec<EntityId>,
    pub partial: Option<Body>,           // diagnostic only; never cached as success
}

/// Registry consulted by Kiln when lowering Ingot calls with the lockfile's pins.
pub struct OperationRegistry { /* name -> versions */ }
pub enum VersionStatus { Current, Deprecated { since: ReleaseId }, Retired { wasm_component: PackageRef }, Yanked { reason: String } }

impl OperationRegistry {
    pub fn resolve(&self, name: &str, pinned: Option<u32>) -> Result<OpHandle, RegistryError>;
    pub fn status(&self, name: &str, version: u32) -> Option<VersionStatus>;
}
```

### Selected operation arguments

```rust
pub struct BooleanArgs { pub operands: Vec<Body>, pub expr: BoolExpr, pub keep: Keep }  // Keep::Regularized | Keep::Cells
pub enum BoolExpr { Operand(u16), Union(Vec<BoolExpr>), Intersect(Vec<BoolExpr>), Subtract(Box<BoolExpr>, Box<BoolExpr>) }

pub struct BlendArgs {
    pub body: Body,
    pub edges: Vec<EntityId>,
    pub radius: RadiusLaw,               // Constant(f64) | Field(FieldRef) | Asymmetric(f64, f64)
    pub section: Section,                // Circular | Conic { rho } | CurvatureContinuous { depth }
    pub corners: Vec<(EntityId, Corner)>,
    pub overflow: Overflow,
    pub fallback: BlendFallback,         // None | Implicit { max_deviation }
}

pub struct TetrahedralizeArgs {
    pub body: Body,
    pub sizing: FieldRef,                // Field<Body, Length>
    pub geometry_order: u8,              // 1..=4
    pub strategy: TetStrategy,           // Conforming | Envelope { epsilon }
    pub quality: QualityTarget,
}

pub struct ConvertArgs { pub body: Body, pub into: ReprKind, pub accuracy: f64, pub options: ConvertOptions }
```

### Query resolution (`anvil-topo`)

```rust
/// Ingot lowers a Query to a plan; Anvil evaluates it (D-ANV-15).
pub struct QueryPlan { pub anchors: Vec<Anchor>, pub filters: Vec<Filter>, pub cardinality: Cardinality, pub on_merge: OnMerge }

pub fn resolve(body: &Body, plan: &QueryPlan, fuel: &mut Fuel) -> Result<Resolved, ResolveError>;

pub struct Resolved { pub entities: Vec<EntityId>, pub notes: Vec<Note> }   // Note::Merged, Note::Partial, Note::FragileAnchor

#[derive(Debug)]
pub enum ResolveError {
    Split     { anchor: EntityId, pieces: Vec<EntityId>, fixes: Vec<Fix> },
    Deleted   { anchor: EntityId, by: Option<EntityId>, site: OpSite, fixes: Vec<Fix> },
    NoMatch   { stage: Stage, found: u32, closest: Vec<EntityId>, fixes: Vec<Fix> },
    TooMany   { candidates: Vec<EntityId>, fixes: Vec<Fix> },
    Ambiguous { entity: EntityId, predicate: Filter, margin: Interval },
}
```

### Services for Flux

```rust
/// Implemented for every representation (Flux tab, "Division of labor with Anvil").
pub trait GeometryQuery: Send + Sync {
    fn classify_box(&self, b: Aabb, tol: f64) -> BoxClass;                         // Inside | Outside | Cut | Uncertified
    fn closest_point(&self, p: Point3) -> SurfacePoint;                            // EntityId, (u, v), signed distance
    fn moments(&self, b: Aabb, degree: u8) -> Result<CertifiedMoments, Uncertified>;
    fn surface_quadrature(&self, b: Aabb, degree: u8) -> Result<SurfaceRule, Uncertified>;
    fn local_thickness(&self, p: Point3) -> (f64, ErrorBound);
}

/// Thin adapter that Kiln implements by issuing versioned Anvil Ops (tetrahedralize, refine_mesh,
/// adapt_mesh, optimize_mesh), so every mesh Flux receives is cached and pinned like any other Op result.
pub trait MeshService {
    fn tetrahedralize(&self, args: TetrahedralizeArgs) -> Result<(Body, ErrorBound), OpError>;
    fn refine_mesh(&self, mesh: &Body, marked: &[CellId]) -> Result<(Body, Vec<HistoryRecord>), OpError>;
    fn adapt_mesh(&self, mesh: &Body, metric: FieldRef) -> Result<(Body, Vec<HistoryRecord>, ErrorBound), OpError>;
    fn optimize_mesh(&self, mesh: &Body, target: FieldRef) -> Result<Body, OpError>;
}
```

`MeshService` is not a parallel abstraction: it names the subset of Anvil operations Flux's adaptive loop calls, and its only implementation routes through Kiln.

## Build, reuse or avoid

| Project | License | Decision | Reason |
| --- | --- | --- | --- |
| Parasolid, ACIS, CGM | Commercial | Learn from published papers only; benchmark through licensed translator plugins where customers own licenses | Closed source; the contract allows proprietary formats only through licensed plugins. Parasolid's local tolerances and Convergent Modeling, and ACIS and CGM's mixed polyhedral add-ons [ACIS Polyhedra; CGM Modeler], confirm the hybrid direction |
| Open CASCADE Technology 8.0 | LGPL 2.1 with an additional exception, or commercial [OCCT repository] | Avoid linking; use as a differential oracle in CI tooling outside the core | C++17 [OCCT 8.0]; LGPL linking conflicts with a statically linked Rust and Wasm core; valuable as a second opinion on Booleans, healing and STEP |
| Truck | Apache 2.0 [Truck repository] | Study; do not adopt | B-spline and NURBS topology in Rust with Booleans and WebGPU rendering; its README describes no per-entity tolerance or provenance model |
| Fornjot | Archived 19 June 2026; README: "This project has been shut down. Its goals were never reached." [Fornjot repository] | Lesson only | A code-first Rust kernel whose mainline code went over a year without development in favor of experiments, and which lacked "the features for anything more advanced". Anvil's phasing therefore ties every capability to a golden product |
| Manifold | Apache 2.0 [Manifold repository] | Benchmark and oracle for mesh Booleans and level sets | C++ with Thrust or TBB parallelism; ε-validity is a goal, not a guarantee [Manifold wiki] |
| Geogram | BSD-3-Clause [Geogram repository] | Oracle for exact mesh CSG, predicates and Delaunay; port ideas | Lévy's exact Weiler-model CSG lives there; C++ |
| Fidget | MPL 2.0 [Fidget] | Study and benchmark; MPL permits linking, but Anvil's evaluator must share Flux's kernel IR | Rust, Wasm-ready, JIT and interpreter, interval pruning |
| libfive | Core MPL 2.0; Studio GPL [libfive repository] | Benchmark for implicit meshing | Mature f-rep kernel; Studio's GPL excludes it from the core |
| OpenSubdiv | Tomorrow Open Source Technology License 1.0 (Apache 2.0 with a modified trademark section) [OpenSubdiv license] | Oracle for limit evaluation | C++ with CUDA, Metal, OpenGL back ends; no wgpu |
| fTetWild | MPL 2.0 [fTetWild repository] | Oracle and benchmark; port the method | C++ |
| Attene's CDT | GPL or LGPL by build option [MarcoAttene/CDT] | Port the published method; never link | License incompatible with the core |
| bichon | MIT, with GPL CGAL dependencies [Jiang et al. 2021] | Study the method | GPL dependency |
| Axom (winding numbers) | BSD [Spainhour and Weiss 2025] | Oracle for containment queries | C++ HPC library |
| nTop | Commercial | Learn from it | Field-driven implicit design and lattices at industrial scale [nTop whitepaper]; its 5.0 kernel change altered regenerated geometry slightly [nTop 5.0 notice], which Anvil's behavior versions prevent |
| Zoo's engine | Engine not stated as open source; the Design Studio app is open source [Zoo Design Studio v1] | Learn from published overview; respect the SSI patent | Zoo states it uses OpenNURBS and Vulkan [Zoo Design Studio v1] |
| `slotmap` | Zlib [slotmap docs] | Reuse for builder arenas | Generational keys, `no_std` with `alloc` |
| `inari` | MIT [inari docs] | Reference only | Implements a subset of IEEE 1788-2015 interval arithmetic; its documentation does not state bit-identical results on x86-64, ARM64 and Wasm, which Anvil gets from error-free transformations |

**Decision D-ANV-23:** Anvil builds its kernel natively in Rust and links no external geometry kernel; OCCT, Manifold, Geogram, OpenSubdiv, fTetWild, libfive and Axom serve as differential oracles and benchmarks in tooling outside the core. *Why:* the contract requires a Rust core with no GPL or AGPL linking, identical results in native and Wasm builds, and frozen behavior versions, which a C++ dependency cannot guarantee across platforms; oracles from independent implementations catch errors that self-consistent tests miss. *Rejected:* wrapping OCCT (LGPL linking, C++ toolchains in Wasm, no control of numerics or naming); adopting Truck as the base (its data model lacks cellular topology, per-entity tolerances and provenance, so the rewrite would touch every type).

## State of the art

Targets in this table are targets, measured on the phase-0 reference laptop unless stated.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Linear predicates | Adaptive expansion arithmetic [Shewchuk 1997]; indirect predicates for constructed points [Attene 2020] | Shewchuk's public-domain C; Geogram | Own build-time generator in safe Rust, both families (D-ANV-5) | Throughput on random and near-degenerate inputs; target within 1.2× of Shewchuk's C; exactness against rational arithmetic on 10⁸ fuzzed cases |
| Mesh Booleans | Exact local arrangements [EMBER 2022]; exact arrangements with indirect predicates [Cherchi et al. 2022]; exact Weiler model [Lévy 2024]; topological aggregation [trueform 2026] | Manifold; EMBER's reported 1.6 ms geometric mean on 1,000 Thingi10K pairs | Exact arrangement on unquantized `f64` with checked output rounding (D-ANV-20) | Thingi10K pairs and Lévy's thingiCSG; target 100% valid outputs, at most 2× EMBER's per-pair time (deviation reason as in the performance targets), and faster than the current Manifold release on the same pairs |
| B-rep Booleans | Imprint, join and select with local tolerances [Jackson 1995]; cellular arrangement | Parasolid, ACIS, CGM; OCCT 8.0 as the open reference | Cellular arrangement with certified SSI and tolerance rule (D-ANV-19) | Boolean pairs built from ABC models with rigid offsets, including coincident and tangent cases; target a success rate above OCCT 8.0's with 100% `check_body`-valid outputs; Parasolid compared through a licensed plugin where a partner holds a license |
| Surface-surface intersection | Topology-guaranteed B-spline SSI [Yang et al. 2023]; interval algebraic topology analysis [Cheng et al. 2023] | ACIS, OCCT, SISL as compared in Yang et al. | Subdivision, normal-cone loop exclusion, Krawczyk on the critical-point system, certified marching (D-ANV-16) | Reconstructed hard-case suites of both papers plus face pairs from ABC; target correct branch topology on every suite case and at most 2× OCCT time on transversal cases. Deviation: certification costs time, and correct topology comes first |
| GPU SSI acceleration | GPU box hierarchies with curvature-inflated bounds [Krishnamurthy et al. 2008]; dense sampling with distance thresholds (patented) [US12229885B1] | Zoo's engine | GPU sampling orders work, exact integer GPU culling prunes, CPU certified solves decide (D-ANV-17) | Output equality with and without GPU; candidate-set equality with CPU; speedup on ABC face pairs and 1,000-part assemblies; target ≥ 3× over the CPU-only path on the reference laptop |
| Tolerance model | Local tolerances on vertices and edges [Jackson 1995] | Parasolid; CGM's tolerant modeling [CGM Modeler] | Scale-relative resolution, per-entity tolerances, certified three-way decisions with capped growth (D-ANV-3, D-ANV-4) | Healing success and tolerance-growth statistics on ABC's STEP files [STEP distribution unverified]; MEMS and ship-scale suites |
| Implicit evaluation | Interval tape pruning on GPU [Keeter 2020]; Lipschitz pruning [Barbier et al. 2025]; affine range analysis [Sharp and Jacobson 2022] | Prospero challenge: a NEON interpreter at 0.29 ms on an M1 MacBook Air (bytecode generation excluded); Fidget at 6.3 ms on an M1 Max; MPR at 3.9 ms on a V100 [Prospero] | SIMD interpreter with interval, affine and Lipschitz pruning; shared kernel IR; WGSL interpreter for previews (D-ANV-11) | Prospero 1024² render; target within 2× of 0.29 ms on comparable CPU hardware with bytecode generation excluded, and total time including tape compilation reported |
| Implicit meshing | Manifold dual contouring; occupancy-based dual contouring [Hwang and Sung 2024] | libfive; Fidget | Certified adaptive dual contouring with monotone-cell certification | Hausdorff error to dense references, manifoldness 100%, time at fixed accuracy; target ≤ libfive time at equal accuracy |
| Tetrahedral meshing | Conforming CDT with indirect predicates [Diazzi et al. 2023]; envelope meshing [fTetWild 2020] | TetGen (378 failures of 4,408); fTetWild | Both strategies; exact validity check after rounding | The 4,408 valid Thingi10K models; target 100% success, with the conforming stage within the published 4.3 s single-core mean and quality improvement timed separately |
| Curved high-order meshing | 3D Bézier guarding [Khanteimouri and Campen 2023]; bijective coarse high-order meshes [Jiang et al. 2021] | bichon | Guarding on polynomial faces, project-certify-untangle elsewhere | 100% positive Bernstein Jacobian coefficients; boundary error; element count against bichon |
| Hex-dominant meshing | Field-guided polyhedral agglomeration [Gao et al. 2017] | The authors' implementation [license unverified] | Adopt the method; all-hex only by sweeping | Validity 100%; hex fraction reported on a Thingi10K subset, no promise |
| Boundary layers | Semi-structured curvilinear layers with isoparametric splitting [Marcon et al. 2019] | NekMesh [license unverified] | Advancing layers with exact collision tests; isoparametric splitting for curved layers | First-layer height within 5% on 95% of faces (target); validity 100% |
| Quad remeshing | Feature-line driven quad remeshing, under 0.5% failures on Thingi10K [Pietroni et al. 2021] | The authors' results | Adopt for quad mode | Failure rate on Thingi10K; target ≤ 0.5% |
| Decimation | Quadric error metrics [Garland and Heckbert] | Not verified for this draft; chosen in phase 1 [unverified] | QEM with verified Hausdorff bound per collapse | Hausdorff error at fixed triangle budgets on Thingi10K |
| Subdivision surfaces | Feature-adaptive limit evaluation [Nießner et al. 2012]; exact evaluation [Stam 1998] | OpenSubdiv | Native Rust implementation with OpenSubdiv rules (D-ANV-13) | Limit positions within 10⁻¹² relative of OpenSubdiv (target); evaluation throughput at least OpenSubdiv's CPU path |
| Containment and signed distance | Generalized winding numbers [Jacobson et al. 2013]; trimmed NURBS [Spainhour and Weiss 2025]; hierarchical acceleration [Spainhour, Whitlock and Weiss 2026] | Axom | Adopt all three, certified near-surface correction | Classification accuracy at ±τ/2 and ±2τ; time per query against Axom |
| GPU NURBS evaluation | Elastic tessellation with tensor-core evaluation [ETER] | ETER (CUDA; 3.7 million patches at 30 fps) | wgpu `f32` evaluation for previews and display; CPU canonical | Patches per second at one-pixel error; target 10⁶ patches at 30 fps on the reference GPU. Deviation: lower than ETER because the portable wgpu path cannot assume CUDA tensor cores |
| Mesh repair | Exact arrangement plus winding-number classification [Jacobson et al. 2013; Cherchi et al. 2022] | Geogram, whose exact pipeline Lévy evaluates for mesh repair on Thingi10K [Lévy 2024] | As described under mesh repair | All 10,000 Thingi10K models; target 100% valid outputs |
| Mesh offsets | Feature-preserving mitered offsets [Cao et al. 2024] | The methods Cao et al. compare against, including Zint et al. 2023 | Adopt the method for meshes; exact Minkowski construction for B-reps | Thingi10K subset: offset error, feature preservation, validity |
| Blends | Rolling-ball blends; setback vertex blends [Várady publication list] | Parasolid, ACIS, CGM | Staged program with stated implicit fallback | Success rate on fillet chains from ABC models; target above OCCT 8.0's at stage 1 |
| Persistent naming | Combined topology and geometry identification [persistent naming review 2018] | Commercial history-based systems [unverified] | Provenance hashes with lineage and typed resolution errors (D-ANV-14, D-ANV-15) | Query survival under 16 seeded perturbations (D-AGT-8) on golden products; target 100% resolve-or-typed-error, zero silent re-selections |
| Correctly rounded math | CORE-MATH (all C23 binary64 functions except compound) [correct rounding page] | LLVM libc | PLT `detmath` | Bit-identity across Tier 1 targets |

## Platform notes

| Risk | Platforms | Decision |
| --- | --- | --- |
| Transcendental functions differ across libm implementations | All | Only PLT `detmath`; Rust's `sin` and `exp` are banned in Anvil crates by a lint, since their precision "varies by platform" [Rust f64 docs] |
| Hardware FMA absent on the x86-64-v2 baseline | Windows and Linux x86-64 | TwoProduct uses Dekker splitting there and `mul_add` elsewhere; both give the exact error term, so bits match (D-PLT-2 dispatch) |
| Flush-to-zero or denormals-are-zero set by a foreign library | All native | Operation entry asserts the IEEE default control state, as Flux does; a violation is a typed internal error |
| NaN bit patterns non-deterministic | All, including Wasm | Finiteness checked at every construction; the encoding rejects NaN and infinity |
| Relaxed SIMD instructions may behave differently across platforms; Wasm 3.0 defines an optional deterministic profile [Wasm 3.0] | Browsers and Wasm components | Anvil never emits relaxed SIMD; canonical lanes use only deterministic SIMD128 operations |
| wasm32 memory ceiling of 4 GiB | Browsers | Body leaves stream from the CAS; operations whose fuel estimate exceeds the browser memory budget run on a team server or cloud worker with identical results, by the `cpu-f64` class |
| No JIT on iPadOS App Store builds, where Wasm runs on the Pulley interpreter (PLT tab) | Tier 2 | The tape interpreter is the canonical evaluator (D-ANV-11), so no feature depends on JIT |
| Wasm threads need cross-origin isolation | Browsers | Without it, operations run single-threaded with identical results, only slower |
| WebGPU missing or limited, for example Chrome on most Linux GPUs and Firefox on Linux (PLT tab) | Browsers | Every GPU kernel has a CPU path; integer culling falls back to CPU hierarchies, previews to CPU tessellation |
| GPU driver variance in `f32` math | All GPU | GPU results never define canonical outputs (D-ANV-17); preview differences across vendors are accepted and labeled |
| Long GPU dispatches reset by the OS (Windows timeout detection) | Windows | Dispatches split into chunks under the PLT time budget; a lost device falls back to CPU |
| SVE not yet usable from stable Rust | ARM64 servers | NEON paths with the same canonical lanes, per the PLT tab |
| 32-bit x87 rounding | Not Tier 1 | Unsupported; RFC 3514 lists it as a known violation |

All Anvil behavior is identical on Tier 1 desktops and browsers. Tier 2 devices run the same code; limits of memory and threads only lengthen times or move large operations to a server. Tier 3 platforms join the `cpu-f64` class only after the determinism suite passes, as the PLT tab requires.

## Interfaces with other subsystems

### Anvil provides

| To | What | Types |
| --- | --- | --- |
| Ingot and std | The operation catalog with behavior versions; role vocabularies per operation; query plan evaluation | `Body`, `EntityId`, `HistoryRecord`, `Query` resolution results and `ResolveError`, `OpError` with `Fix`es, `ErrorBound` |
| Kiln | Pure, deterministic operations with canonical argument hashing, fuel accounting and cancellation points; the operation registry with version status | `Op` cache-key inputs (name, version, argument hashes), `Canonical` encodings, Body content hashes |
| CAS | Canonical Body encodings; brick caches for implicits; tessellation levels | SHA-256 content hashes |
| Flux | `GeometryQuery` on all representations; `tetrahedralize`, `hex_dominant`, `boundary_layer`, `refine_mesh`, `adapt_mesh`, `optimize_mesh`, `untangle`, `polyhedral_mesh`; `shape_velocity`; `implicit_from_field`; `common_refinement`; display tessellation with `(EntityId, u, v)`; deterministic hierarchies | `Body`, `Field`, `ErrorBound`, `HistoryRecord` |
| Mechanical (MEC) | Every operation in its lists, under the canonical names above; `solve_constraints` and `analyze_constraints` as versioned operations; per-entity tolerances; recognition of aspects and relations | `Body`, `EntityId`, `Field` |
| Manufacturing (MFG) | `section`, `offset_curve`, `medial_axis`, `tool_contact`, `swept_volume`, `distance`, `interference`, `deform`, `split`, `extend`, `visibility`, `draft_map`, `voxelize`, `correlate_grids`, `fit`, `boolean` | `Body`, `Field`, `ErrorBound` |
| Electronics (ELX) | Extrusion of board outlines and copper as multi-region Bodies; imprint and conformal meshing for electro-thermal models | `Body` with regions |
| UI (UIX) | Display tessellations with levels of detail and back-references; GPU preview kernels for NURBS, SubD and implicits; analysis Fields | `Body` (Mesh), `Field` |
| Agents (AGT) and `api` | `inspect.entity` data (kind, geometry type, adjacency, provenance chain); query resolution with ranked fixes; deterministic perturbation runs for D-AGT-8 | `EntityId`, `HistoryRecord`, `ResolveError` |
| `io/` | Building, healing and matching imported Bodies; NURBS approximation for export; tessellation for 3MF, glTF, STL and OBJ | `Body`, `ErrorBound` |

### Anvil requires

| From | What | Canonical names and types |
| --- | --- | --- |
| Ingot (ING) | A stable syntax-node identity per call site, delivered as `OpSite`; lowering of `Query` to `QueryPlan`; lockfile entries for operation pins; dimension checking before operations run | `OpSite`, `Query`, lockfile |
| Kiln (KLN) | `OpSite` as an input of every Anvil Op, cached in two stages (CCR-ANV-5); fuel budgets per Op; cancellation that discards results; scheduling of independent Ops; storage of Preview results outside the shared cache | `Op`, CAS |
| Flux (FLX) | `flux-field` below `anvil-mesh` (CCR-FLX-6); `Sampler` with requested accuracy and error per sample; Lipschitz or gradient bounds per Field where known; Field domains `Body`, `Faces` and `Edges` | `Field`, `ErrorBound`, `Sampler` |
| Platform (PLT) | `detmath` correctly rounded functions with interval-friendly accuracy guarantees; `simd` canonical lanes; `gpu` with a CPU fallback per kernel; deterministic `runtime` combinators; toolchain archiving for frozen behavior versions | `PlatformClass` (`cpu-f64` for every canonical Anvil result) |
| `repo` | Syntax-tree CRDT node identities stable across merges, which `OpSite` depends on | Node ids |
| Mechanical (MEC) | Role vocabularies for features, delivered as `FeatureRole` attributes; constraint semantics for `solve_constraints` | `EntityId`, attributes |

## Oracles

Oracles live in the protected `oracles/anvil/` directory. Every operation's oracle also runs `check_body` on outputs, checks history coverage, and replays the run on every Tier 1 target for bit identity.

| Id | Verifies | Method | Phase |
| --- | --- | --- | --- |
| ANV-O-DET-1 | Determinism | Every corpus run repeated with 1, 2, 7 and 64 threads, with and without GPU, on all Tier 1 targets; output hashes identical | 0 |
| ANV-O-SCALE-1 | Scale invariance | Corpus models with their frame at the origin, scaled by 2⁻²⁰ to 2²⁰; outputs equal the scaled outputs bit for bit | 0 |
| ANV-O-PRED-1 | Exact predicates | 10⁸ random and adversarial near-degenerate cases against rational arithmetic | 0 |
| ANV-O-TOL-1 | Tolerance rule | Synthetic coincident, near-coincident and tangent pairs at distances τ/2, τ, 2τ; decisions and recorded growth match the specification | 1 |
| ANV-O-GEOM-1 to 3 | Evaluation, sampling, approximation | Closed forms for analytic geometry; NURBS against exact rational evaluation in big rationals; certified deviation of approximations | 0 |
| ANV-O-OP-1 to 8 | Construction operations | Closed-form volumes, areas, centroids (prisms, Pappus solids, tori, springs); interpolation of sections and networks; continuity | 0 to 2 |
| ANV-O-SSI-1 to 3 | Intersections | Closed-form quadric pairs; the hard-case families of Yang et al. and Cheng et al. reconstructed as test cases; branch counts and topology; random rigid perturbations below τ must not change topology | 1 |
| ANV-O-BOOL-1 | Boolean algebra | A ∪ A = A, A − A = ∅, A ∩ B ⊆ A, De Morgan identities; volumes satisfy inclusion-exclusion within bounds | 1 |
| ANV-O-BOOL-2 | Manifold's perturbation cases | Touching cubes merge in a union; an equal-height difference cuts through; self-difference is empty | 1 |
| ANV-O-BOOL-3 | Mesh Booleans at scale | Thingi10K pairs and thingiCSG: 100% valid outputs; volumes against exact rational references | 1 |
| ANV-O-BOOL-4 | B-rep Booleans on real models | ABC-derived pairs with coincident and tangent configurations; differential comparison with OCCT 8.0 where both succeed | 2 |
| ANV-O-BOOL-5, 6 | Split and imprint | Piece volumes sum to the input; imprint leaves volume and area unchanged | 1 |
| ANV-O-BLEND-1 to 4 | Blends | Closed-form toroidal and cylindrical blends; spine distance; G1 and G2 continuity; volume changes on straight edges | 1 to 4 |
| ANV-O-OFF-1 to 4 | Offsets, shells, thickening, shrinkwrap | Exact offsets of spheres, cylinders, tori and boxes; Hausdorff distance equals \|d\|; shelled volumes; skin containment | 1 to 2 |
| ANV-O-DRAFT-1 | Draft | Angles of drafted faces | 2 |
| ANV-O-TRIM-1, 2 | Trim and extend | Kept sides; continuity at extension | 1 |
| ANV-O-XF-1, ANV-O-PAT-1 | Transforms and patterns | Round trips; copy counts and placements | 0 to 1 |
| ANV-O-HEAL-1, 2 | Sewing and healing | Exploded solids re-sew; healed imports pass `check_body` within reported deviation | 1 |
| ANV-O-DE-1 to 3, ANV-O-REC-1, 2 | Direct edits and recognition | Volume identities; labeled aspect sets | 2 |
| ANV-O-MID-1 | Mid-surfaces | Known plate and sheet-metal mid-surfaces; thickness Fields | 2 |
| ANV-O-SEC-1, ANV-O-PROJ-1, 2, ANV-O-PAR-1, ANV-O-SM-1 | Sections, projection, wrap, flattening, unfold | Section areas against integrals; preserved lengths; fold of unfold equals input | 1 to 2 |
| ANV-O-DEF-1, 2 | Deform and morph | Rigid Fields equal `transform`; deviation bounds | 2 to 3 |
| ANV-O-MESH-1 to 4 | Mesh construction, repair, segmentation, common refinement | Thingi10K: all repaired outputs valid; volumes against winding-number references; overlay areas | 0 to 4 |
| ANV-O-TET-1 | Tetrahedralization | 4,408 valid Thingi10K models: no inverted elements, boundary conformity or envelope bound, region volumes | 2 |
| ANV-O-HO-1 | Curved elements | Positive Bernstein Jacobian coefficients; boundary error | 2 to 3 |
| ANV-O-HEX-1, ANV-O-BL-1 | Hex-dominant and boundary layers | Validity; conformity; first-layer heights | 3 to 4 |
| ANV-O-REM-1 | Remesh, decimate, smooth | Reported Hausdorff bounds hold under certified measurement | 1 to 3 |
| ANV-O-SUBD-1 | Subdivision | Limit positions against OpenSubdiv; regular cages equal bicubic B-splines | 3 |
| ANV-O-IMP-1 to 4 | Implicits | Interval enclosures contain sampled values; Lipschitz bounds hold on random segments; pruned tapes equal full tapes in each region; iso-surfaces of analytic Fields within the reported bound | 1 |
| ANV-O-LAT-1 | Lattices | Volume fractions of TPMS and strut lattices; minimum thickness | 1 |
| ANV-O-CONV-1 | Conversions | Every conversion's reported bound holds under independent certified Hausdorff measurement | 1 |
| ANV-O-MP-1 | Mass properties | Closed forms; agreement across representations within bounds | 0 to 1 |
| ANV-O-DIST-1 to 5 | Distance, closest point, interference, ray casting, deviation | Closed forms for analytic pairs; agreement across representations | 0 to 1 |
| ANV-O-AN-1 to 7 | Analyses | Closed-form curvature, continuity, draft, thickness, medial axes, silhouettes, visibility | 1 to 3 |
| ANV-O-CLS-1 to 3 | Classification | Points at ±τ/2 and ±2τ; agreement across representations | 0 to 1 |
| ANV-O-TESS-1 | Tessellation | Certified chord bounds; watertightness; EntityIds on face groups | 0 |
| ANV-O-NAME-1 | History coverage and soundness | The four properties of `HistoryRecord` on every operation in the corpus | 0 |
| ANV-O-NAME-2 | EntityId stability | For each golden product, 16 seeded parameter perturbations within declared ranges: every query resolves to the same lineage or returns a typed error; zero silent re-selections | 1 |
| ANV-O-NAME-3 | Worked examples | The four worked examples in this tab, as executable tests | 1 |
| ANV-O-NAME-4 | Import matching | Edited copies of ABC models with known edits, re-exported through STEP | 2 |
| ANV-O-VER-1 | Behavior versions | Frozen-module hashes; golden output hashes of every active, deprecated and retired version reproduced after toolchain upgrades | 0 |
| ANV-O-ENC-1 | Encoding | Round trip is bit-identical; every past major version decodes; canonical text form matches binary | 0 |
| ANV-O-SV-1 | Shape velocity | Finite differences agree within step-size error | 2 |
| ANV-O-FIT-1, 2, ANV-O-VOX-1, 2, ANV-O-MFG-1 to 3, ANV-O-DRAPE-1 | Fitting, voxels, manufacturing geometry, draping | As listed in the catalog | 1 to 4 |
| ANV-O-FUZZ-1 | Robustness under random use | Property-based generation of operation sequences (primitives, Booleans, blends, offsets, patterns, conversions) with random and near-degenerate placements; every result is valid, deterministic and consistent with the algebraic identities, or a typed error; failures are minimized automatically and added to the corpus | 0 onward |
| ANV-O-PERF-1 | Performance regressions | The State of the art benchmarks and the targets table, run per merge batch on the reference laptop; deterministic work counts (subdivisions, predicate escalations, allocations) block merges on regression, and wall-clock regressions above 10% are flagged for human review | 1 onward |

Held-out models never shown to agents include ABC and Thingi10K subsets selected by a fixed hash rule and stored outside the agent-readable tree, as the contract requires.

## Phasing

| Phase | Anvil deliverables | Gate contribution |
| --- | --- | --- |
| 0, foundations | Predicates and generator; intervals; resolution and tolerance types; geometry types (lines, conics, NURBS, planes, quadrics, tori, extrusion and revolution surfaces); cellular topology; `check_body`; encoding and text form; EntityId, history, lineage; `primitive`, `curve`, `extrude`, `revolve`, `transform`, `tessellate`, `mesh_from_triangles`, `classify_points`, `closest_point`, mass properties of meshes; operation registry and freeze check | Determinism suite (ANV-O-DET-1, SCALE-1, PRED-1, VER-1, ENC-1) green on all Tier 1 targets |
| 1, wedge (machined bracket; topology-optimized lattice bracket) | Certified intersections and SSI with GPU work ordering and broad phase; primitive fitting; voxelization; cellular Booleans for every representation pair; constant-radius blends and chamfers; offsets, shells, thickening; split, trim, extend, imprint; patterns and mirroring; sweep and loft; sew and heal; section and projection; `make_regions`; implicit DAG, evaluators, pruning, brick cache, Field leaves and `implicit_from_field`, lattices, implicit meshing; geometry access (`evaluate`, `sample`, `intersect`, `approximate`); `classify_box` and `classify_body`; mesh repair and decimation; conversions; mass properties for all; distance, interference, ray casting, deviation; curvature, continuity to G2, thickness, 2D medial axis, silhouettes and hidden lines; `GeometryQuery`; `offset_curve`, `tool_contact` and 3-axis `swept_volume` | Golden product 1: exact bracket with fillets, drawings, toleranced checks. Golden product 2: lattice bracket from Flux density Fields, meshed for printing with stated error |
| 2, mechanical depth (gearbox; welded frame with sheet-metal guards) | Variable-radius and conic blends; draft; helices; boundary, fill, blend and match surfaces; isophotes, draft analysis and visibility; shrinkwrap; triangle remeshing and smoothing; direct edits, recognition, defeaturing; mid-surfaces; unfold and fold; deform; parameterize and wrap; G3 analysis; conforming tetrahedralization with curved boundary elements by projection; `refine_mesh`; `untangle`; shape velocity; import matching; 3D medial axis; 5-axis swept volumes; grid correlation | Golden products 3 and 4: gears, shafts, housings, weldment mid-surfaces and sheet metal, contact meshes for Flux |
| 3, product breadth (molded enclosure with PCB) | Setback vertex blends of any valence; subdivision surfaces and conversions; envelope tetrahedralization; Bézier guarding; sweep meshing; mesh segmentation; metric adaptation and node optimization; polyhedral meshes; quad remeshing; morphing; draft maps; GPU preview tessellation | Golden product 5: drafted, shelled enclosure with blends; multi-region electro-thermal meshes with the PCB |
| 4, full multiphysics (drone) | Blends on blends and G3 sections; hex-dominant meshing; boundary layers; mesh-to-B-rep and subdivision-cage fitting; scan alignment; common refinement for interface transfer; kinematic draping | Golden product 6: airframe surfaces, boundary-layer meshes for airflow, composite plies |
| 5 and later (proposed) | Ship-scale models with block-structured hull meshing; MEMS process emulation (layer deposition and etch as implicit and cellular operations); trivariate spline volumes for isogeometric analysis | New golden products per domain, coordinated with Flux's proposals |

## Open questions

1. **Retention window.** D-ANV-18 keeps every behavior version executable forever, natively for at least 5 years and then as Wasm components. PLT and Kiln must confirm the CI cost of replaying deprecated versions and the toolchain archiving this needs.
2. **Freedom to operate.** D-ANV-17 needs counsel's review of US 12,229,885 B1 before the GPU work-ordering path ships in phase 1; other GPU geometry patents were not searched for this draft.
3. **Resolution default.** 2⁻³⁰ of the diagonal is a proposal. Phase 0 must measure tolerance-growth rates on ABC imports at 2⁻²⁶, 2⁻³⁰ and 2⁻³⁴ before freezing it.
4. **Implicit-to-B-rep fidelity.** Recovering exact analytic faces from implicit leaves (phase 3) has no published method with guarantees that this draft verified; the facet path is the fallback.
5. **Blend success targets.** No public benchmark of fillet success rates across kernels was found; Anvil must build one from ABC models and agree its target with MEC.
6. **WGSL accuracy.** The ulp bounds of WGSL arithmetic could not be verified; until they are, GPU interval results serve previews only.
7. **Feature roles.** The `FeatureRole` attribute answers MEC's open question 5 on feature-level roles; ING must confirm how Ingot features declare them.
8. **Hex-dominant license.** The license of the field-guided agglomeration reference code was not verified; the method is published, and Anvil implements it independently either way.
9. **trueform.** The July 2026 mesh-CSG paper claims large speedups with exact predicates; its license and full results must be reviewed before phase 1 locks the mesh Boolean design.

## Contract change requests

- **CCR-ANV-1. `ErrorBound` lives in `anvil-geom`.** Accept CCR-FLX-1's definition `{ value, norm, kind }` and place the type in `anvil-geom`, the lowest crate that reports geometric error, with `flux-field` depending on it. *Reason:* one type, and geometry-level code cannot depend on `flux-field`, which sits above `anvil-topo`.
- **CCR-ANV-2. `EntityId` formula.** Amend section 5 to "hash of (kind, operation site, role, generating entity ids, discriminator)", where the operation site is the call's structural identity and excludes argument values. *Reason:* hashing parameter values into the "operation id" would rename every downstream entity on every dimension edit (D-ANV-14).
- **CCR-ANV-3. Canonical operation names.** Adopt the canonical names in the operations catalog (for example `anvil::section` for `section_body` and `slice`, `anvil::convert` for the representation-specific conversions, `anvil::fit`, `anvil::interference`, `anvil::tool_contact`) across the MEC and MFG tabs. *Reason:* one name per concept.
- **CCR-ANV-4. `Query` outcomes.** Add `Note` outcomes to section 5's `Query`: a successful resolution may carry notes such as `Merged` and `FragileAnchor`, and checks may forbid notes. *Reason:* merges change an entity's extent without changing its meaning; users need to see this without the query failing.
- **CCR-ANV-5. `OpSite` as an Op input.** State in section 5 that an Anvil `Op`'s inputs include its operation site, so the site enters the cache key of the cheap relabeling step while the geometric core stays cached without it. *Reason:* EntityIds depend on the operation site (CCR-ANV-2), so two calls with identical inputs at different sites produce Bodies with different EntityIds.
- **CCR-ANV-6. Predicates for curved geometry.** Amend section 7's "adaptive exact predicates for topological decisions" to "exact adaptive predicates for linear decisions; certified enclosures with explicit, recorded tolerance rules for decisions on curved geometry". *Reason:* exact predicates on NURBS, offset and blend surfaces require algebraic degrees that are impractical, while certified enclosures give the same freedom from contradictory decisions (D-ANV-4).

## Sources

Each entry gives the citation key used in this tab, then the page opened.

| Key | Source |
| --- | --- |
| Shewchuk 1997 | [Shewchuk, robust predicates page (Discrete & Computational Geometry 18, 1997)](https://www.cs.cmu.edu/~quake/robust.html) |
| Attene 2020 | [Attene, "Indirect predicates for geometric constructions", arXiv 2105.09772](https://arxiv.org/abs/2105.09772v2) |
| Diazzi et al. 2023 | [Diazzi, Panozzo, Vaxman, Attene, "Constrained Delaunay Tetrahedrization: A Robust and Practical Approach", arXiv 2309.09805](https://arxiv.org/pdf/2309.09805) |
| MarcoAttene/CDT | [CDT repository](https://github.com/MarcoAttene/CDT) |
| Cherchi et al. 2022 | [Cherchi, Pellacini, Attene, Livesu, "Interactive and Robust Mesh Booleans", arXiv 2205.14151](https://ar5iv.arxiv.org/html/2205.14151) |
| EMBER 2022 | [Trettner, Nehring-Wirxel, Kobbelt, "EMBER: Exact Mesh Booleans via Efficient & Robust Local Arrangements", TOG 41(4)](https://www.graphics.rwth-aachen.de/media/papers/339/ember_exact_mesh_booleans_via_efficient_and_robust_local_arrangements.pdf) |
| Lévy 2024 | [Lévy, "Exact predicates, exact constructions and combinatorics for mesh CSG", arXiv 2405.12949](https://arxiv.org/html/2405.12949v2) |
| trueform 2026 | [Sajovic and Knez, "trueform: Fast And Robust Mesh CSG Via Topological Aggregation", arXiv 2607.15905](https://arxiv.org/abs/2607.15905) |
| Manifold wiki | [Manifold Library wiki](https://github.com/elalish/manifold/wiki/Manifold-Library) |
| Manifold repository | [Manifold repository](https://github.com/elalish/manifold) |
| Geogram repository | [Geogram repository](https://github.com/BrunoLevy/geogram) |
| fTetWild 2020 | [Hu, Schneider, Wang, Zorin, Panozzo, "Fast Tetrahedral Meshing in the Wild", arXiv 1908.03581](https://arxiv.org/abs/1908.03581v2) |
| fTetWild repository | [fTetWild repository](https://github.com/wildmeshing/fTetWild) |
| Jiang et al. 2021 | [bichon repository, "Bijective and Coarse High-Order Tetrahedral Meshes"](https://github.com/jiangzhongshi/bichon) |
| Khanteimouri and Campen 2023 | ["3D Bézier Guarding: Boundary-Conforming Curved Tetrahedral Meshing", SIGGRAPH history archive](https://history.siggraph.org/?p=214468) |
| Gao et al. 2017 | [Gao, Jakob, Tarini, Panozzo, "Robust hex-dominant mesh generation using field-guided polyhedral agglomeration"](https://rgl.epfl.ch/publications/Gao2017Robust) |
| hex survey 2022 | ["Hex-Mesh Generation and Processing: a Survey", arXiv 2202.12670](https://ar5iv.labs.arxiv.org/html/2202.12670) |
| Marcon et al. 2019 | [Marcon et al., "A semi-structured approach to curvilinear mesh generation around streamlined bodies", arXiv 1901.01968](https://arxiv.org/abs/1901.01968) |
| Pietroni et al. 2021 | [Pietroni, Nuvoli, Alderighi, Cignoni, Tarini, "Reliable feature-line driven quad-remeshing"](https://vcg.isti.cnr.it/publication/2021/PNACT21) |
| Garland and Heckbert | ["Surface Simplification Using Quadric Error Metrics"](https://www.cs.cmu.edu/~garland/Papers/quadrics.pdf) |
| Cao et al. 2024 | [Cao et al., "Robust and Feature-Preserving Offset Meshing", arXiv 2412.15564](https://arxiv.org/html/2412.15564v1) |
| Jacobson et al. 2013 | [Jacobson, Kavan, Sorkine-Hornung, "Robust Inside-Outside Segmentation using Generalized Winding Numbers"](https://igl.ethz.ch/projects/winding-number/) |
| Spainhour and Weiss 2025 | [Spainhour and Weiss, "Robust Containment Queries over Collections of Trimmed NURBS Surfaces via Generalized Winding Numbers", arXiv 2504.11435](https://arxiv.org/html/2504.11435v3) |
| Spainhour, Whitlock and Weiss 2026 | ["Spatially Accelerated Winding Numbers for Curved Geometry", arXiv 2605.19200](https://arxiv.org/pdf/2605.19200) |
| Fidget | [Keeter, Fidget project page](https://mattkeeter.com/projects/fidget) |
| Keeter 2020 | [Keeter, "Massively Parallel Rendering of Complex Closed-Form Implicit Surfaces", TOG 39(4)](https://www.mattkeeter.com/research/mpr/keeter_mpr20.pdf) |
| Prospero | [Keeter, The Prospero Challenge](https://mattkeeter.com/projects/prospero) |
| Barbier et al. 2025 | [Barbier, Sanchez, Paris, Michel, Lambert, Boubekeur, Paulin, Thonat, "Lipschitz Pruning: Hierarchical Simplification of Primitive-Based SDFs"](https://research.adobe.com/publication/lipschitz-pruning-hierarchical-simplification-of-primitive-based-sdfs) |
| Sharp and Jacobson 2022 | [Sharp and Jacobson, "Spelunking the Deep", arXiv 2202.02444](https://arxiv.org/abs/2202.02444v3) |
| Hwang and Sung 2024 | [Hwang and Sung, "Occupancy-Based Dual Contouring", arXiv 2409.13418](https://arxiv.org/html/2409.13418v1) |
| libfive repository | [libfive repository](https://github.com/libfive/libfive) |
| nTop whitepaper | [nTop, implicit modeling technology whitepaper page](https://www.ntop.com/resources/guides/whitepaper-implicit-modeling-technology/) |
| nTop 5.0 notice | [nTop 5.0 new implicit modeling kernel notice](https://docs.ntop.com/help-articles/whats-new/backwards-compatibility-notices/ntop-5-0-new-implicit-modeling-kernel) |
| Yang et al. 2023 | [Yang, Jia, Yan, "Topology Guaranteed B-Spline Surface/Surface Intersection", SIGGRAPH history archive](https://history.siggraph.org/?p=214449) |
| Cheng et al. 2023 | [Cheng, Zhang, Xiao, Li, "Topology Driven Approximation to Rational Surface-surface Intersection via Interval Algebraic Topology Analysis", SIGGRAPH history archive](https://history.siggraph.org/learning/topology-driven-approximation-to-rational-surface-surface-intersection-via-interval-algebraic-topology-analysis-by-cheng-zhang-xiao-and-li) |
| Patrikalakis, Maekawa and Cho | ["Shape Interrogation for Computer Aided Design and Manufacturing", MIT hyperbook](https://web.mit.edu/hyperbook/Patrikalakis-Maekawa-Cho/) |
| Krishnamurthy et al. 2008 | [Krishnamurthy, Khardekar, McMains, Haller, Elber, "Performing Efficient NURBS Modeling Operations on the GPU", SPM 2008](https://mcmains.me.berkeley.edu/pubs/SPM08gpuSSI.pdf) |
| ETER | ["ETER: Elastic Tessellation for Real-Time Pixel-Accurate Rendering of Large-Scale NURBS Models", SIGGRAPH history archive](https://history.siggraph.org/?p=132429) |
| US12229885B1 | [US 12,229,885 B1, Google Patents](https://patents.google.com/patent/US12229885) |
| US12229885B1 full text | [US 12,229,885 B1, USPTO full text](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12229885) |
| Zoo engine overview | [Zoo CAD engine overview](https://zoo.dev/research/zoo-cad-engine-overview) |
| Zoo Design Studio v1 | [Zoo Design Studio v1 announcement](https://zoo.dev/blog/zoo-design-studio-v1) |
| Jackson 1995 | [Jackson, "Boundary Representation Modelling with Local Tolerances", Solid Modeling '95](https://ftp1.cs.wisc.edu/pub/users/prem/jackson-SM-95.pdf) |
| Parasolid convergent modeling | [Siemens, Parasolid Convergent Modeling press release](https://news.siemens.com/en-gb/parasolid-convergent-modeling-mixed-models/) |
| ACIS Polyhedra | [Spatial, ACIS Polyhedra](https://www.spatial.com/products/acis-polyhedra?hsLang=ja) |
| CGM Modeler | [Spatial, CGM Modeler](https://www.spatial.com/solutions/3d-modeling/cgm-modeler) |
| OCCT 8.0 | [Open CASCADE Technology 8.0.0 release announcement](https://occt3d.com/dev/content/open-cascade-technology-800-release/index.html) |
| OCCT repository | [OCCT repository](https://github.com/Open-Cascade-SAS/OCCT) |
| Truck repository | [Truck repository](https://github.com/ricosjp/truck) |
| Fornjot repository | [Fornjot repository](https://github.com/hannobraun/fornjot) |
| Várady publication list | [Várady, publication list, SZTAKI](https://eprints.sztaki.hu/view/creators/V=E1rady=3AT=2E=3A=3A.html) |
| OpenSubdiv repository | [OpenSubdiv repository](https://github.com/PixarAnimationStudios/OpenSubdiv) |
| OpenSubdiv license | [OpenSubdiv license](https://raw.githubusercontent.com/PixarAnimationStudios/OpenSubdiv/release/LICENSE.txt) |
| Nießner et al. 2012 | [Nießner, Loop, Meyer, DeRose, "Feature Adaptive GPU Rendering of Catmull-Clark Subdivision Surfaces"](https://niessnerlab.org/projects/niessner2012feature.html) |
| Stam 1998 | [Stam, "Exact Evaluation of Catmull-Clark Subdivision Surfaces at Arbitrary Parameter Values"](https://www.dgp.toronto.edu/public_user/stam/reality/Research/pdf/sig98.pdf) |
| Edelsbrunner and Mücke | [Edelsbrunner and Mücke, "Simulation of Simplicity", arXiv math/9410209](https://arxiv.org/abs/math/9410209) |
| Thingi10K 2016 | [Zhou and Jacobson, "Thingi10K", arXiv 1605.04797](https://arxiv.org/abs/1605.04797) |
| ABC 2019 | [Koch et al., "ABC: A Big CAD Model Dataset for Geometric Deep Learning", CVPR 2019](https://openaccess.thecvf.com/content_CVPR_2019/html/Koch_ABC_A_Big_CAD_Model_Dataset_for_Geometric_Deep_Learning_CVPR_2019_paper.html) |
| persistent naming review 2018 | ["Mechanisms of Persistent Identification of Topological Entities in CAD Systems: A Review", Alexandria Engineering Journal](https://doaj.org/article/bf42fdae16584d0ba2d824137aba6599) |
| RFC 3514 | [Rust RFC 3514, float semantics](https://rust-lang.github.io/rfcs/3514-float-semantics.html) |
| Rust f64 docs | [Rust `f64` documentation](https://doc.rust-lang.org/std/primitive.f64.html) |
| correct rounding page | [Correct rounding of elementary functions in IEEE 754 formats](https://reliable-computing.org/correctrounding.html) |
| Wasm 3.0 | [WebAssembly 3.0 announcement](https://webassembly.org/news/2025-09-17-wasm-3.0) |
| Wasm nondeterminism | [WebAssembly nondeterminism](https://www.webassembly.org/docs/nondeterminism/) |
| WGSL | [WGSL specification](https://www.w3.org/TR/WGSL/) |
| slotmap docs | [slotmap documentation](https://docs.rs/slotmap/latest/slotmap/) |
| inari docs | [inari documentation](https://docs.rs/inari/latest/inari/) |
| 3MF beam lattice repository | [3MF Beam Lattice extension repository](https://github.com/3MFConsortium/spec_beamlattice) |
