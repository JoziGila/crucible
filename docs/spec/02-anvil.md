# Anvil geometry kernel (ANV)

Anvil is one geometry kernel over four representations (exact B-rep, implicit, mesh and subdivision surface) with one tolerance model, one provenance model and one operation contract. Linear decisions use exact predicates; decisions on curved geometry use certified enclosures, decided in rounds against frozen tolerances; constructions are floating point with per-entity tolerances and per-face error bounds. Every operation is versioned, deterministic and label-invariant, returns `HistoryRecord`s, and lets the GPU order, prune or preview work but never decide a result.

## Kernel structure and operation contract

Anvil owns geometry types; the `Body` with its topology, tolerances, attributes, encoding and identities; naming, lineage and `anvil::resolve`; and every geometric operation, including conversions, meshing, constraint solving, `anvil-planar` and `DisplayPackage` production. Ingot owns `OpSite`s and queries, Kiln caching and Aborts, Flux physics and refinement decisions, MEC constraint semantics, `io/` formats and UIX rendering.

The capability tables closing each design section form the operations catalog and operation-to-phase table that contract 7.1 makes canonical; MEC, MFG and ELX copy their rows.

### Crates

| Crate | Contents | Depends on |
| --- | --- | --- |
| `anvil-geom` | Predicates, intervals, affine forms, tolerances, curves and surfaces with evaluation, local solvers, fitting | `base`, `detmath`, `simd`, `runtime`, `gpu`, `linalg`, `kernels` |
| `anvil-topo` | Cellular topology, attributes, certificates, `EntityId`, `HistoryRecord`, lineage, `anvil::resolve`, `check_body`, the encoding | `anvil-geom` |
| `anvil-planar` | Integer-coordinate 2D geometry with lines and arcs | `anvil-geom` |
| `anvil-mesh` | Surface, point-set and volume meshes, subdivision cages | `anvil-topo`, `field` |
| `anvil-implicit` | Expression DAG, tapes, evaluators, brick cache, implicit meshing | `anvil-mesh`, `field`, `kernels` |
| `anvil-ops` | The `Body` enum, every operation's `OpImpl`, Booleans, conversions, `GeometryQuery` | all of the above |

**Decision D-ANV-1:** Anvil has six crates in the order `anvil-geom` → `anvil-topo` → `anvil-planar` → `anvil-mesh` → `anvil-implicit` → `anvil-ops`, above `base`, `field` and `kernels`, all `forbid(unsafe_code)`, with SIMD and GPU work through PLT's crates and compute kernels in the shared kernel IR. *Why:* contract 12 places `base`, `field` and `kernels` below Anvil and confines `unsafe`; cages share the mesh half-edge structure. *Rejected:* a separate `anvil-subd` crate (a boundary with no new structure); `unsafe` SIMD inside Anvil. (revised in round 2)

### Kernel rules

1. **Bodies are immutable values**; unchanged storage is shared.
2. **Operations are pure and label-invariant**: results depend on arguments, input geometry and the version, never on clocks, randomness, thread order or names.
3. **Work limits are arguments** with per-version defaults; reaching one is the deterministic `Failure` `WorkLimit`, while cancellation, memory exhaustion and Evaluation fuel are Aborts.
4. **Decisions are certified**, by exact predicates or certified enclosures, never a floating-point guess.
5. **Approximations state their error** as per-face `{ position, normal }` bounds.
6. **The GPU orders, prunes and previews**; canonical results are identical without it.
7. **No silent fallbacks**: a fallback runs only on request and says so.
8. **Each question is asked once per tolerance epoch**: predicates are memoized by (pair, epoch).

### The operation contract

Every operation implements Kiln's `OpImpl` from `base` with grade `Portable`, except `thickness` and `correlate_grids` (`Certified`); GPU preview paths never produce canonical results.

| Element | Contract |
| --- | --- |
| Inputs | Bodies, plain values with units converted by Ingot, `Query` resolutions as `EntityId` sets with a declared use (`Surface` or `Extent`), Fields with a requested accuracy |
| Outputs | Bodies or values, `HistoryRecord`s, per-face bounds and `Note`s, canonical at the boundary (−0.0 becomes +0.0; no non-finite values), so decode(encode(v)) = v bit for bit |
| Stages | Entity-naming operations run a geometric stage and a relabeling stage (see Bodies, identities and encoding) |
| Failures | `OpError { kind, why, fixes, at, partial }` is a deterministic `Failure`, cached and catchable; `partial` is a diagnostic Body, never cached as a success; `OpError` maps one-to-one onto MEC's `FeatureError` |
| Fidelity | Each version maps `Preview`, `Interactive` and `SignOff` to its effective fidelity (see Fidelity, performance and determinism) |
| Validity | Incidence, combinatorics and regularity are checked on created and modified entities and their neighbours; their separation is checked against the whole Body through the broad phase, in O(m log n) for m such entities, and a clash fails with `SelfIntersecting { faces, at }` |

### Behavior versions

A behavior version (`anvil::blend@2`) fixes an operation's output for every input; any change to output bits, history, `EntityId`s or error kinds needs a new version.

**Decision D-ANV-18:** Each operation version, and every internal module it uses (for example `ssi@4`), is frozen by source hash once released; changes go into new module versions. *Why:* frozen source plus PLT's reproducible toolchain rebuilds old designs by construction, which no regression corpus can promise. *Rejected:* versioning only the public operation (a fix in shared intersection code would silently change every old version); keeping old binaries (no cross-platform guarantee, no shared cache).

CI blocks merges that change frozen modules (security exceptions need a human and identical corpus outputs), attaches each new version's behavior diff to its Proposal, and requires toolchain and `detmath` upgrades to reproduce every version's golden hashes.

A design pins versions in `ingot.lock` (`anvil.blend = 2`), a call may override with `op: anvil::blend@1`, and `crucible upgrade anvil::blend` produces a Proposal with geometry overlay, metric deltas, changed checks and every `ResolveError`. Versions go from `Current` to `Deprecated` (native for at least five years, noted on every build) to `Retired` (archived Wasm build, identical bits, contract 4); a `Yanked` version stays executable for audit, and release checks fail until the design upgrades or a human waives.

### Rust surface

```rust
/// SHA-256 prefix of (kind, OpSite, role, generating ids, discriminator).
#[derive(Copy, Clone, Eq, PartialEq, Ord, PartialOrd, Hash, Debug)]
pub struct EntityId(pub [u8; 16]);

/// Per-face representation error (contract 5).
pub struct FaceBound { pub position: Component<Length>, pub normal: Component<Angle> }

#[derive(Clone)]
pub struct Body { repr: Repr, frame: Frame, resolution: Length, regions: Regions, meta: Arc<BodyMeta> }
pub enum Repr { BRep(Arc<BRep>), Implicit(Arc<Implicit>), Mesh(Arc<Mesh>), SubD(Arc<SubD>) }

impl Body {
    pub fn geometry_id(&self) -> GeometryId;   // names, lineage and name-keyed attributes removed
    pub fn object_id(&self) -> ObjectId;       // full canonical encoding
    pub fn error(&self) -> Component<Length>;  // largest face position bound
    pub fn entity(&self, id: EntityId) -> Option<EntityRef<'_>>;
}

pub struct Blend;
impl OpImpl for Blend {
    const ID: OpId = OpId::new("anvil", "blend");
    const VERSION: u32 = 2;
    const GRADE: DeterminismGrade = DeterminismGrade::Portable;
    type Inputs = BlendArgs;      // body, edges (Query use: Extent), radius law, section, corners, overflow, variant
    type Outputs = BodyOutput;    // Body, HistoryRecords, Notes; FaceBounds live in the Body
    fn eval(&self, cx: &mut OpCx<'_>, args: BlendArgs) -> Result<BodyOutput, OpError> { /* … */ }
    fn cost(&self, sizes: &InputSizes) -> CostEstimate { /* … */ }
}
```

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Operation registry | Name and `ingot.lock` pin → `OpImpl`; status `Current`, `Deprecated`, `Retired`, `Yanked` | `UnknownOperation`; `Note::DeprecatedBehavior` | ANV-O-VER-1 | 0 |
| Frozen versions and toolchain guard | Source hashes and golden output hashes per version | Merge or upgrade blocked | ANV-O-VER-1 | 0 |
| Retired versions | Archived Wasm build of frozen source, identical bits | Never `OpVersionRetired`: Anvil has no `ClassExact` operation | ANV-O-VER-1 | 1 |
| `anvil::check_body` | Body → every violation of the four validity conditions | — | ANV-O-VALID-1 | 0 |
| Global separation check in every operation | Changed entities against the whole Body through the broad phase | `SelfIntersecting { faces, at }` | ANV-O-VALID-2 | 0 |
| Canonical outputs | decode(encode(v)) = v for every output | Internal error | ANV-O-ENC-1 | 0 |
| Robustness under random use | Property-based operation sequences with near-degenerate placements | Failures minimized into the corpus | ANV-O-FUZZ-1 | 0 |

## Bodies, identities and encoding

### The Body value

A `Body` holds its representation; a frame (a translation on a fixed 2⁻²⁰ m grid; rotations belong to Instance placements); its resolution ρ; regions, each `Material`, `Void` or `Exterior` (a fluid is a material region); and metadata with per-face bounds. Anvil stores no item numbers or names; Parts add identity.

| Representation | Exact content | Typical sources | Limits |
| --- | --- | --- | --- |
| `BRep` | Analytic, NURBS and procedural faces, facet faces, cellular topology with regions | Features, STEP, conversions | Blends and imports are the hard cases |
| `Implicit` | Expression DAG; exact faces of B-rep leaves that remain on the boundary | Lattices, topology optimization, field-driven design, shrinkwraps | Distance may be only a bound; cost grows with expression size |
| `Mesh` | Manifold triangle topology with precision ε; vertex-only point sets | Scans, printing, tessellation, simulation | Piecewise linear |
| `SubD` | Catmull-Clark cage with semi-sharp creases | Industrial design | G1 at extraordinary vertices |

### Representation lattice

Three inclusions lose no geometry: a Mesh is a B-rep with facet faces, as Parasolid's Convergent Modeling mixes facet and classic surfaces in one model [Parasolid convergent modeling]. A SubD is a B-rep with subdivision-limit faces, exact except near extraordinary vertices with semi-sharp creases, where a certified bound is recorded. A B-rep or Mesh is an implicit leaf, its exact signed distance with the sign from generalized winding numbers [Jacobson et al. 2013; Spainhour and Weiss 2025].

A mixed operation returns the join of its operands: Mesh with Mesh gives a Mesh, B-rep combinations a B-rep whose faces keep their native geometry, and anything with an implicit an implicit. The join is leaf-preserving: an `Implicit` Body keeps each B-rep leaf's exact faces that remain on its boundary, with their `EntityId`s and attributes, found by certified classification.

Queries, PMI and drawings use those faces directly, and `convert(into: BRep)` keeps them exact, trimmed by certified intersection, with facet faces only where other leaves are active. Golden product 2's mounting holes thus keep their `HoleSpec` and semantic PMI, which CAx-IF practice allows only on exact geometry [CAx-IF PMI 4.1].

**Decision D-ANV-2:** Mixed operations return the least representation in the lattice Mesh ⊂ BRep, SubD ⊂ BRep, BRep ⊂ Implicit that holds both operands without approximating geometry or dropping B-rep faces that remain on the boundary. *Why:* exact faces keep their names and attributes, and any later conversion is explicit and bounded. *Rejected:* converting to meshes first (destroys exact faces); a plain implicit result (loses faces, names and PMI, which golden product 2 needs); refusing mixed operations (contract 7.1). (revised in round 2)

[[DIAGRAM diagrams/02-anvil-representation-lattice.jsx: representation lattice · 4 representations, 3 inclusions]]

Mesh and SubD sit inside BRep and BRep inside Implicit, so a mixed operation takes the join; going back down is an explicit conversion that records per-face bounds.

### Two identities and two stages

`GeometryId` hashes the geometry part of a Body's encoding and `ObjectId` the whole encoding (contract 7.2), so only `ObjectId` sees names, lineage and name-keyed attributes.

An entity-naming operation runs in two stages. The geometric stage, keyed by input `GeometryId`s, arguments, version, class and effective fidelity, computes geometry and history over canonical entity numbers. The relabeling stage, keyed by the geometric output's id, the `OpSite` and the inputs' name maps, assigns `EntityId`s, lineage and name-keyed attributes in linear time.

`std` features called from different designs thus share every geometric result, a refactor that changes no geometry changes no `GeometryId`, and Flux keys solves on `GeometryId`s plus the canonical numbers of referenced entities.

**Decision D-ANV-24:** Every Body has a `GeometryId` beside its `ObjectId`, and entity-naming operations split into a geometric stage keyed by `GeometryId`s and a relabeling stage keyed by the `OpSite`. *Why:* names hash upstream sites transitively, so one named identity defeats cross-design caching, early cutoff after refactors and approvals over geometry. *Rejected:* removing sites from keys while the encoding holds names; caching only label-free operations (almost no sharing).

[[DIAGRAM diagrams/02-anvil-two-stage-operation.jsx: two-stage operation · one geometric result shared by two designs]]

Only the relabeling stage sees names, so a second design that builds the same geometry at another site reuses the geometric-stage result.

### Canonical geometric order

Every order Anvil computes with comes from geometry: kind, box minimum, box maximum, type and defining parameters, then a hash of the entity's full geometric content. Distinct entities of a valid Body never tie, since equal content would violate separation; during construction, coincident vertices break ties by their neighbours' sorted coordinates. The order sets storage rows, perturbation indices, pair order, hierarchy tie-breaks and independent-set priorities, and seeds hash argument values and input `GeometryId`s.

**Decision D-ANV-25:** Anvil is label-invariant: orders, perturbation indices, priorities and seeds come from geometry, topology and argument values, so renaming input `EntityId`s and `OpSite`s changes only name sections. *Why:* geometry must follow from source text alone, so Git round trips and published packages rebuild bit-identically (contract 7.1). *Rejected:* `EntityId` tie-breaks and seeds (names would steer geometry); memory or insertion order.

### Encoding and versioning

The geometry part holds topology tables, geometry pools, tolerances, per-face bounds and geometric attributes in canonical geometric order; the name part maps canonical numbers to `EntityId`s, lineage and name-keyed attributes. Each section is a persistent tree of structure-of-arrays leaves of at most 1,024 rows, and a row ends a leaf when a hash of its canonical key has its low 8 bits zero, so equal content gives equal leaves whatever the edit history. Identities are SHA-256 Merkle hashes over leaves; floats are binary64 with −0.0 normalized and no NaN or infinity; a text form with hexadecimal floats serves goldens and diffs.

A minor version adds optional sections or columns, and the hashed form omits optional values equal to their defaults, so a minor release never changes an identity; an unknown required section fails with `EncodingError::Unsupported { needed }`. A major version is a behavior change: it enters item 1 of the `OpKey` and is pinned in `ingot.lock`, with a reader kept for every major and a writer for every pinned one.

**Decision D-ANV-9:** The encoding is canonical, split into geometry and name parts with content-defined leaves and Merkle hashes, invariant across minor versions and readable for every major version forever. *Why:* the two identities need a separable name part, builders on different releases must agree on one `OpKey`, and hashing stays proportional to edits. *Rejected:* re-encoding in the current minor version (changes identities of identical geometry); serializing in-memory structs; STEP as native storage (loses procedural geometry, tolerances and lineage). (revised in round 2)

Operations build Bodies in arenas with generational keys [slotmap docs]; finished Bodies share untouched leaves between versions.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `GeometryId` and `ObjectId` | Body → two SHA-256 Merkle identities | — | ANV-O-CACHE-1, ANV-O-LABEL-1 | 0 |
| Two-stage operations | Geometric stage keyed by input `GeometryId`s; relabeling keyed by `OpSite` | `Internal::EntityIdCollision` | ANV-O-CACHE-1 | 0 |
| Canonical geometric order and seeds | Orders, perturbation indices, priorities and seeds from geometry and arguments | — | ANV-O-LABEL-1 | 0 |
| Encoding and text form | Body ↔ canonical bytes; hashes invariant across minor versions | `EncodingError::{Unsupported, NotRepresentable}` | ANV-O-ENC-1, ANV-O-ENC-2 | 0 |
| Leaf-preserving implicit faces | Exact faces of B-rep leaves kept with ids and attributes | `Ambiguous { faces }` near tangency | ANV-O-LEAF-1 | 1 |
| `anvil::build` | B-rep from topology and geometry records; point sets from buffers | `Invalid { violations }` with a heal fix | ANV-O-VALID-1 | 0 (B-rep), 1 (point sets) |

## Numbers, tolerances and decisions

Anvil computes with `f64`, Shewchuk expansions, intervals, reduced affine forms, integers and modular or rational arithmetic for ranks, in metres and radians; Ingot converts quantities at the boundary.

### Resolution, frames and scale

Every Body has a resolution ρ, the smallest length it distinguishes, where D is its box diagonal in metres:

```latex
\rho(D) = 2^{\lceil \log_2 D \rceil - 30}
```

Coordinates are frame-relative, so for any Body above 2 µm ρ is at least 2²³ times the local `f64` spacing (2¹³ for a 1 nm Body), headroom that constructions may consume before a decision changes. With no absolute length constant besides the frame grid, a Body framed at the origin behaves identically under power-of-two scaling. A result takes ρ_out = max(input ρ, ρ(D_out)), and `resolution:` may lower ρ to 2^(⌈log₂ D⌉ − 40).

| Body | D | Default ρ | Growth cap τ_cap = 2¹⁰ρ |
| --- | --- | --- | --- |
| MEMS accelerometer die | 0.5 mm | 2⁻⁴⁰ m ≈ 0.91 pm | ≈ 0.93 nm |
| Machined bracket (GP1) | 0.1 m | 2⁻³³ m ≈ 0.12 nm | ≈ 0.12 µm |
| Drone (GP6) | 1 m | 2⁻³⁰ m ≈ 0.93 nm | ≈ 0.95 µm |
| Ship hull | 300 m | 2⁻²¹ m ≈ 0.48 µm | ≈ 0.49 mm |

Frame offsets are multiples of 2⁻²⁰ m, so frame differences are exact below 2³² m and rebasing costs one rounding. Between Instances, decisions use the finer frame and max(ρ_a, ρ_b), and a coarsened result reports `Note::ResolutionCoarsened`.

**Decision D-ANV-3:** Resolution is per Body, scale-relative (2⁻³⁰ of the box diagonal, rounded to a power of two), with frames on a fixed 2⁻²⁰ m grid. *Why:* nanometres to hundreds of metres need scale-relative tolerances; a fixed value such as 1995 Parasolid's default of about 5·10⁻⁹ m [Jackson 1995] is coarse for MEMS and wasteful for ships; powers of two keep scaling exact. *Rejected:* a global tolerance (contract 7.1); ρ from the exact diagonal (changes with every edit); per-assembly resolution.

### Per-entity tolerances

Each vertex, edge and face carries a tolerance τ ≥ ρ, stored when it differs from ρ. As in Parasolid [Jackson 1995], τ(vertex) ≥ τ(edge) ≥ τ(face), and a tolerant edge keeps its faces' parameter curves within τ of one master curve.

| Quantity | Default | Rule |
| --- | --- | --- |
| Growth cap τ_cap | 2¹⁰ρ | An operation raises a tolerance to at most max(the involved inputs' tolerances, τ_cap), else `ToleranceGrowth { entity, needed, cap }` |
| Healing limit τ_heal | max(10 × the file's declared uncertainty, 2¹⁰ρ) | Up to 2²⁰ρ with an explicit argument |
| Minimum size λ | 2⁴ρ | Smaller slivers merge within tolerance or fail with `BelowResolution` |
| Mesh precision ε | Accumulated rounding bound per Mesh, as in Manifold [Manifold wiki] | Above τ_cap: `PrecisionExhausted` with a remesh fix |

### Validity

With tolerance regions N(x) = { p : dist(p, G_x) ≤ τ_x }, a Body is valid when four conditions hold; `anvil::check_body` reports every violation:

1. **Incidence.** Curve endpoints lie in their vertices' regions; parameter-curve images and edge curves lie in their edges' regions.
2. **Separation.** Every point of G_x within τ_x + τ_y of G_y lies in the region of an entity in the shared closure of x and y, so entities with disjoint closures are farther apart than τ_x + τ_y.
3. **Combinatorics.** Loops close and are oriented; bounded regions are enclosed by closed shells; radial order around each edge agrees with the certified angular order; Euler–Poincaré holds per shell.
4. **Regularity.** Curves and surfaces are regular where used, except at declared singular points; parameter curves stay in their domain or its periodic cover.

### Certified decisions in rounds

A topological question about curved geometry reduces to a quantity q (a distance, an oriented angle) whose certified enclosure [lo, hi] meets the applicable tolerance τ:

1. hi ≤ τ: **coincident**, or the point is **on**.
2. lo > τ: **separated**, with a certified sign.
3. Otherwise the enclosure is refined by subdivision or interval Newton steps, within the work limit.
4. If it narrows below ρ/2⁸ and still straddles τ, the decision is coincidence, with a request to grow the entities' tolerances to hi within the cap; if the cap or the limit is reached first, the operation fails with `Ambiguous { entities, enclosure }`.

Decisions run in rounds by dimension: vertex–vertex, vertex–edge, edge–edge, vertex–face, edge–face, face–face. Within a round every pair is decided in parallel against tolerances frozen at the round's start; growth requests are reduced per entity by maximum, which is order-free, and applied at the round's end as a new epoch. Pairs touching a grown entity are decided again until nothing grows; growth is monotone and capped, so this terminates, and too many repeats fail with `ToleranceCascade { entities, rounds }`.

Merged entities take max(τ_x, τ_y, certified Hausdorff distance), and each growth is reported as `Note::ToleranceGrown`; Parasolid likewise raises local tolerances where entities would otherwise collide [Jackson 1995].

**Decision D-ANV-4:** Linear decisions use exact predicates; decisions on curved geometry use certified enclosures under the three-way rule, made in rounds by dimension against tolerances frozen at each round's start, with growth reduced by maximum and capped. *Why:* exact algebraic predicates on NURBS, offset and blend geometry are impractical, and frozen tolerances make outcomes independent of pair order and thread count (contract 7.1). *Rejected:* epsilon comparisons (contradictory decisions); growth applied as pairs are decided (order-dependent results); uncapped growth (tolerances creep until models break). (revised in round 2)

### Predicates and intervals

| Family | Inputs | Method | Used by |
| --- | --- | --- | --- |
| Linear | `f64` points: orient2d, orient3d, incircle, insphere, distance comparisons | Static filter, interval filter, exact expansions [Shewchuk 1997] | Meshes, planar arrangements, hulls |
| Indirect | Implicit points from line–plane, three-plane and two-point combinations | Filters on the generating primitives, so points are never rounded [Attene 2020; Diazzi et al. 2023] | Mesh arrangements, Booleans, CDT |
| Certified curved | Curves, surfaces, implicits | Interval and affine enclosures, Bernstein bounds, Krawczyk, with the round rule | B-rep Booleans, blends, classification, intersections |

A build-time generator emits both families as safe Rust.

**Decision D-ANV-5:** Anvil generates its own linear and indirect predicates, porting Shewchuk's method and Attene's scheme. *Why:* safe Rust with canonical order runs identically in native and Wasm builds, and indirect predicates make mesh arrangements exact without rational coordinates. *Rejected:* binding C++ libraries (FFI and licences: Attene's CDT code is GPL or LGPL by build option [MarcoAttene/CDT]); rational arithmetic throughout (arbitrary-precision mesh arrangements took 141 s where EMBER took 34 ms on 1.2 million triangles [EMBER 2022]).

Intervals use error-free transformations, since Rust exposes no rounding modes: TwoSum, TwoProduct and the exact remainders a − q·b and a − s² give each rounding error exactly, and a nonzero error moves the bound outward with `next_up` or `next_down`, stable since Rust 1.86.0 [Rust 1.86.0 release]. TwoProduct uses Dekker splitting on wasm32 and `mul_add` by ISA level on native targets, with identical error terms (see Platform notes). Elementary functions come only from `detmath`, widened by one ulp.

Exact ties in mesh algorithms break by Simulation of Simplicity [Edelsbrunner and Mücke] in canonical geometric order, as Lévy does for unique triangulations [Lévy 2024]. Booleans classify touching and coplanar faces explicitly, and Manifold's documented cases are oracles: touching cubes merge, an equal-height difference cuts through, and A − A is empty [Manifold wiki].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Linear and indirect predicates | Points or implicit points → exact sign | — | ANV-O-PRED-1 | 0 |
| Certified decision rule in rounds | Enclosures and frozen tolerances → coincident, separated or grown | `Ambiguous`, `ToleranceGrowth`, `ToleranceCascade` | ANV-O-TOL-1, ANV-O-DET-2 | 0 |
| Interval and reduced affine arithmetic | Enclosures with identical bits on every target | — | ANV-O-IMP-1 | 0 |
| Scale-relative resolution and frames | ρ per Body, frames on the 2⁻²⁰ m grid | `BelowResolution { size, resolution, floor }` | ANV-O-SCALE-1 | 0 |
| Symbolic perturbation | Ties broken in canonical geometric order | — | ANV-O-LABEL-1 | 1 |

## B-rep topology, geometry and attributes

### Cellular topology

One cellular boundary representation serves solids, sheets, wires, non-manifold and multi-region Bodies; manifold solids get fast paths but no separate type.

| Entity | Holds | Invariant |
| --- | --- | --- |
| Region | Role `Exterior`, `Material(MaterialRef)` or `Void`; shells | One `Exterior` per Body; bounded regions are enclosed by closed shells |
| Shell | Connected face sides bounding one region | Open shells are sheets, free in `Exterior` or embedded in a region |
| Face | Surface, sense, loops, two sides each bounding a region | Both sides bound the same region only for sheets |
| Loop, coedge | Coedge cycle; next, previous, radial next, sense, parameter curve | Radial cycles ordered by certified dihedral angle |
| Edge, vertex | Curve or point, parameter interval, tolerance | τ(vertex) ≥ τ(edge) ≥ τ(face) |

Radial cycles carry non-manifold cases: four coedges join two solids along an edge, a wire edge has none, an acorn vertex has no edges. A multi-material part is one Body whose regions share internal faces, such as an overmolded insert's steel–polymer interface.

**Decision D-ANV-6:** One cellular B-rep (regions, shells, two-sided faces, loops, coedges with radial cycles, edges, vertices) serves every B-rep Body, with material per region. *Why:* multi-material parts, conformal meshing and Booleans that keep interfaces all need faces shared by regions. *Rejected:* a manifold half-edge B-rep with non-manifold side structures (two code paths); combinatorial 3-maps for every Body (heavier for the common case).

Loops on periodic surfaces live in the universal cover, so a full cylindrical face has no seam edge, and sphere poles and cone apexes are singular points of faces, not edges. For comparisons with other kernels, Anvil defines a topology normal form (seams and poles removed, periodic faces unsplit, their counts reported separately). `anvil::exchange_form` writes seam edges and pole vertices for a receiver profile, approximates procedural geometry by B-splines within a stored bound, and maps every new entity back to its `EntityId` for the translation report.

### Geometry types

Every type evaluates exactly with derivatives to third order, gives a certified bound over any parameter box and converts to NURBS with a stated error. Procedural types also cache a certified NURBS approximation for enclosures and seeding (D-ANV-7).

| Curves | Surfaces |
| --- | --- |
| Line; circle and ellipse; parabola and hyperbola | Plane; cylinder, cone, sphere, torus (self-intersecting tori allowed, singular points marked) |
| Helix (axis, radius, pitch, handedness, taper), exact and procedural | General quadrics (phase 2) |
| NURBS, degree ≤ 25 (higher-degree imports are approximated with a bound) | NURBS, degree ≤ 25 per direction |
| Law curve from an Ingot `Expr` evaluated through the kernel IR with interval bounds (phase 2) | Law surface (phase 2) |
| Planar offset; intersection curve; blend spine and contact curves | Offset; extrusion and revolution; general sweep with frame rules and scale and twist Fields |
| Curve on surface; polyline and arc-spline with per-vertex samples | Rolling-ball blend; setback vertex blend; subdivision limit (phase 2); facet |

Polyline and arc-spline edges carry toolpaths: one edge per run of one motion kind, with per-vertex Field samples, and single moves are addressed by (edge `EntityId`, vertex index), which is not a persistent name. A wire Body holds 10⁷ moves in under 400 MB (target).

**Decision D-ANV-7:** Offset, intersection, sweep, blend, helix and subdivision-limit geometry stays procedural, with exact evaluation and a cached NURBS approximation certified by Taylor models or interval Newton on its defining system; nesting stops at depth three per face, beyond which a construction uses its inputs' certified caches as exact, records their bounds by the propagation rules and reports `Note::ProceduralFlattened`. *Why:* procedural geometry does not accumulate approximation error across features, and the depth limit bounds evaluation cost and enclosure width on blend-heavy parts. *Rejected:* converting every construction to NURBS at once (error compounds); unlimited nesting (cost and enclosure width grow with depth). (revised in round 2)

**Decision D-ANV-8:** B-rep face geometry is always parametric; implicit surfaces never appear as B-rep faces. *Why:* trimming, tessellation, blending and export rely on (u, v) domains, and implicit operands already yield implicit Bodies. *Rejected:* implicit faces (every intersection pair would need an implicit–parametric variant, and STEP cannot carry them).

Parameter curves share their edge curve's parameter within τ_edge, so tessellation places shared edge vertices at the same parameter from both sides and display meshes are watertight by construction. Trimming loops must close within vertex tolerances, avoid self-intersection beyond edge tolerances and nest consistently.

### Attributes and certificates

Design attributes (`HoleSpec`, `ThreadSpec`, `Weld`, finish, the `FeatureRole` role aliases of contract 5) live in a side table keyed by `EntityId`. Each attribute class declares its split policy (`Copy`, `Drop`, `Divide`), merge policy (`KeepIfEqual`, `Union`, `Drop`, `Fail`) and transform policy; Anvil applies them in every operation, and a `Fail` merge returns `AttributeConflict { entities, class }`.

Edges carry construction certificates, `Continuity { order: G1 | G2, certified_by: (operation, OpSite) }`, on blend contact edges, offsets of smooth edges and sweep seams. Intersection and imprint read them (see Intersections).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::curve` | Line, arc, conic, helix, spline, curve on surface, Law curve → wire Body | `Degenerate { parameter }`, `ToleranceNotMet { achieved }` | ANV-O-GEOM-1, ANV-O-LAW-1 | 0 (analytic, NURBS), 1 (helix), 2 (Law) |
| `anvil::surface` | Law surface from an `Expr` → sheet Body | `Degenerate`, `NotRegular { region }` | ANV-O-LAW-1 | 2 |
| `anvil::evaluate` | Curve or face and parameters → points and derivatives to third order | `OutOfDomain { parameters }` | ANV-O-GEOM-1 | 0 |
| `anvil::sample` | Faces or curves, density → points with `EntityId` and (u, v), deterministic low-discrepancy | — | ANV-O-GEOM-2 | 1 |
| `anvil::approximate` | Curves or faces → NURBS within a tolerance | `ToleranceNotMet { achieved }` | ANV-O-GEOM-3 | 1 |
| Procedural nesting budget | Depth three per face; deeper inputs use certified caches | `Note::ProceduralFlattened` | ANV-O-PROC-1 | 1 |
| `anvil::exchange_form` | Body, receiver profile → seams, poles, B-spline approximations, id map | `NotRepresentable { faces }` | ANV-O-NF-1 | 1 |
| Attributes and certificates | Policies applied in every operation; `Continuity` certificates on constructed edges | `AttributeConflict { entities, class }` | ANV-O-NAME-1, ANV-O-CONTACT-1 | 0 (attributes), 1 (certificates) |
| `anvil::sew` | Sheets and faces, tolerance up to τ_heal → shells or solids with tolerant edges | `Note::FreeEdges { edges, gaps }`; `ToleranceGrowth` above the limit | ANV-O-HEAL-1 | 1 |
| `anvil::heal` | Imported Body → valid Body: parameter curves rebuilt, gaps closed, slivers removed, orientation fixed, analytic surfaces recognized; every fix listed with its tolerance change | `Unhealable { entities, reason }`, never an invalid Body | ANV-O-HEAL-2 | 1 (CAx-IF corpus), 2 (beyond) |

## Naming and queries

### EntityId

```
EntityId = SHA-256₁₂₈("anvil.eid.v1" ‖ kind ‖ OpSite ‖ role ‖ inputs ‖ discriminator)
```

The `OpSite` is contract 5's text-derived call identity, computed by Ingot; the role comes from the operation's vocabulary (`start_cap`, `end_cap`, `side(e)` for `extrude`); `inputs` are the generating entities' ids. A discriminator appears only when needed: `Bound(set)`, then `Side(cause, sense)`, then `Ordinal(k)`, which marks the id fragile (`Note::FragileAnchor`).

Untouched and modified entities keep their ids, the latter with a `Modified` record. Wasm components calling through `crucible:ops` pass a call key appended to their site. A duplicate id fails with `Internal::EntityIdCollision`, with accidental odds of about n²/2¹²⁹.

**Decision D-ANV-14:** `EntityId`s hash the text-derived `OpSite`, role, generating ids and discriminator, excluding argument values; names never feed geometric computation. *Why:* dimension edits must not rename entities, and text-derived identities survive Git round trips and publication. *Rejected:* the Op content hash (renames on every edit); evaluation sequence numbers; live-document block ids (not derivable from text); geometric signatures as primary names (geometry changes under the edits names must survive; topology-only and geometry-only schemes are each limited [persistent naming review 2018]). (revised in round 2)

### Copies and placements

A transform that replaces its source in the data flow keeps `EntityId`s. One whose source is used again, or written as `copy`, creates `EID(kind, site, copy, [source])` with `Created { role: copy, from: [source] }`, followed by lineage only on request (`.copies()`). Reflections add the aspect `Mirrored` in place or the role `mirror` on copies, and role queries accept `mirrored: true`; assembly-level features prefix ids with the Instance path.

**Decision D-ANV-30:** Placement keeps names; copying derives names from the source with role `copy` or `mirror`. *Why:* `half + mirror(half, plane.yz)` and features over two Instances of one Part would otherwise put identical ids into one Boolean. *Rejected:* keeping ids on every transform (collisions); renaming on every transform (breaks queries).

### HistoryRecord and lineage

| Record | Meaning |
| --- | --- |
| `Created { out, role, from }` | New entity generated from other entities, such as a blend face from an edge or a copy from its source |
| `Modified { id, aspects }` | Same entity with changed geometry, boundary, tolerance, attributes or `Mirrored` |
| `Split { from, into }` | One entity became several of its kind |
| `Merged { from, into }` | Several entities of one kind became one |
| `Deleted { id, by, reason }` | Consumed (a blend face consumes its edge), internal, or removed |

Records may name transient pieces that exist only inside one n-ary operation, such as two coplanar faces cut by one slot tool: `Split` into transient pieces, then `Merged` out of them. The history oracle checks coverage (each input entity unchanged or the subject of one same-kind record; each transient in one `into` and one `from`), kind, certified geometric soundness and canonical order.

Ancestor sets (through identity, `Split` and `Merged`) are persistent and shared with inputs; `Created` edges are generator links. The descendants of anchor a in Body B are D(a, B) = { e ∈ B : kind(e) = kind(a), and e = a or a is an ancestor of e }.

### Query resolution

`anvil::resolve` is its own Op (contract 5), evaluating Ingot's query plan in three stages:

1. **Anchor.** `EntityId`s captured from feature results (`base.face(role: end_cap)`) or a structural set (`created_by(feature)`).
2. **Lineage.** Each anchor maps to D(a, B), or to the `Deleted` record that removed it.
3. **Filter and select.** Certified geometric filters (normal, type, area, adjacency, `bounded_by`), then cardinality (`one`, `all`, `at_least(n)`). Rank selectors (`longest`, `largest`, `first(along:)`) are allowed only after an anchor or role filter; a winner whose lineage changes inside the declared parameter ranges is reported as `Note::RankSwap { at }`.

Filters near a threshold use Ingot's `Truth` rule on a certified enclosure, and `Undecided` fails with `ResolveError::Ambiguous`. Every operation declares per `Query` parameter whether it uses a surface (sketch planes, up-to faces, mate axes) or an extent (edges of a face, areas, GD&T and PMI targets, drawing items).

| Outcome | Result |
| --- | --- |
| Cardinality met | `Resolved { entities, notes }` |
| Anchor split, query needs one entity | `ResolveError::Split { anchor, pieces, fixes }` |
| Anchor merged, surface use | Resolves with `Note::Merged { with }` |
| Anchor merged, extent use | `ResolveError::Merged { anchor, with, fixes }`, unless `on_merge: Accept` is written |
| Some descendants deleted later | Resolves to the survivors with `Note::Partial { deleted }` |
| Anchor deleted | `ResolveError::Deleted { anchor, by, site, fixes }` |
| Too few or too many | `ResolveError::NoMatch { stage, found, closest, fixes }` or `TooMany { candidates, fixes }` |

Each fix is a typed source edit that compiles, ranked by stability over the full declared range of every parameter, endpoints included, plus ±10% around current values (D-AGT-8); ranking runs on demand and shares the Kiln cache.

**Decision D-ANV-15:** Resolution walks recorded lineage, then applies certified filters; splits, deletions and ambiguity are typed errors, and merges resolve with a note only for surface use. *Why:* contract 5 forbids silent re-selection; a merged face keeps the surface a sketch plane needs but changes the extent a fillet or GD&T target means. *Rejected:* geometric re-identification (fails after the edits that change geometry); accepting every merge (a fillet would silently run around both faces). (revised in round 2)

### Worked example: a face split by a rib

```
let outline = rect(60mm, 40mm)
let base = sketch(plane.xy) { outline } |> extrude(4mm)            // end_cap at z = 4 mm
let r = rect(60mm, 10mm, at: (0mm, 9mm))                           // rib profile on plane.xz
let rib = sketch(plane.xz) { r } |> extrude(3mm, symmetric: true)  // start_cap at y = −1.5 mm
let part = base + rib
let top = part.face(base.face(role: end_cap))
```

1. `extrude` at site `base` creates T = EID(face, base, `end_cap`, [profile region]).
2. The rib's caps at y = ±1.5 mm cut T: `Split { from: T, into: [T₁, T₂] }` with discriminators `Bound{rib start_cap}` and `Bound{rib end_cap}`; the rib's `side(r.bottom)` becomes internal (`Deleted`), and `side(r.left)` and `side(r.right)` merge with the base's coplanar side faces.
3. `top` needs one entity and finds two, so it fails:

```
ResolveError::Split {
  anchor: base.end_cap, pieces: [T₁, T₂],
  fixes: [
    "part.faces(base.face(role: end_cap))",                                     // both pieces
    "part.face(base.face(role: end_cap), bounded_by: rib.face(role: start_cap))", // T₁
    "part.face(base.face(role: end_cap), first(along: +y))",                     // T₁, rank after an anchor
  ]
}
```

Shortened to 40 mm, the rib no longer reaches T's edges: T keeps its id with a new inner loop (`Modified`), and the query resolves. Lifted 1 mm off the face, the `bounded_by` fix fails with `NoMatch` instead of returning the whole face.

### Imported and non-B-rep entities

An imported entity's id is EID(kind, import site, `imported`, [], discriminator), where the discriminator is the source's persistent id (AP242 persistent ids, IFC GlobalId, a translator's native ids), else the surface type with a hash of the exact defining parameters as written and an adjacency signature, never an ordinal. `anvil::match_bodies` aligns two imports rigidly (`anvil::align`), matches attributed face-adjacency graphs, and writes the confirmed mapping as a reviewed source artifact, `import_map(old, new, pairs)`, which later rebuilds reuse.

**Decision D-ANV-31:** Imported entities are named from source persistent ids, else from exact geometric and adjacency signatures, never ordinals, and revisions are matched into a reviewed `import_map`. *Why:* one rule for Anvil and ECO; ordinals change when a supplier re-exports, and quantized signatures flip at quantization boundaries. *Rejected:* ordinals; quantized signatures; unreviewed Hausdorff matching (fails exactly on the faces a supplier moved).

Tessellations keep each face's id on its face group; `subd_edit` records cage history and limit faces take cage-face ids; converted implicits label faces by the leaf active at the surface, and kept B-rep faces keep their ids.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `EntityId` and relabeling | Ids from `OpSite`, role, generating ids and discriminator | `Internal::EntityIdCollision` | ANV-O-SITE-1, ANV-O-LABEL-1 | 0 |
| History records and lineage | Five records with transient pieces; persistent ancestor sets | Internal error on a property violation | ANV-O-NAME-1 | 0 |
| Copies and reflections | Role `copy` or `mirror`; aspect `Mirrored`; Instance-path prefixes | — | ANV-O-COPY-1 | 1 |
| `anvil::resolve` | `QueryPlan`, Body, per-parameter use → entities and Notes, or ranked compiling fixes | `ResolveError::{Split, Merged, Deleted, NoMatch, TooMany, Ambiguous}` | ANV-O-NAME-2, ANV-O-NAME-3, ANV-O-NAME-5 | 0 |
| Imported entity ids | Persistent id, else exact signature | `Note::FragileAnchor` when only an adjacency signature distinguishes faces | ANV-O-NAME-4 | 1 |
| `anvil::match_bodies` | Old and new import → `import_map` with `HistoryRecord`s | `NoCorrespondence { faces }` | ANV-O-NAME-4 | 2 |

## Intersections

One certified framework serves every pair: Bernstein and interval enclosures prune, normal and tangent cones exclude loops, the Krawczyk operator (interval Newton) proves that a box holds exactly one regular root or none, and the round rule decides the rest; the Projected Polyhedron solver is the reference global method [Patrikalakis, Maekawa and Cho].

Curve–curve intersection uses closed forms for lines and circles and Bernstein subdivision otherwise; in 2D Krawczyk certifies unique transversal roots, and in 3D Anvil certifies the closest-approach point and decides contact by the round rule. Curve–surface intersection runs the same scheme in (t, u, v).

### Surface–surface intersection

Surface–surface intersection (SSI) returns a branch graph of curves, isolated contacts and coincidence regions.

1. **Analytic pairs** use closed forms, detecting special positions (parallel, coaxial, tangent, coincident) within tolerance.
2. **Broad phase.** Patch-box hierarchies give candidate pairs in canonical order.
3. **Loop exclusion.** A vector v with v · (n₁ × n₂) bounded away from zero over both normal cones proves the pair holds no closed loop, tangency or singular point, so every branch in it crosses its boundary; otherwise the pair subdivides.
4. **Characteristic points.** At the subdivision floor, Krawczyk searches for critical points of the signed distance h between the surfaces: S₁(u, v) − S₂(s, t) − h·n₂(s, t) = 0 with n₂ orthogonal to ∂S₁/∂u and ∂S₁/∂v. Tangencies and branch crossings are regular roots with h = 0; roots with 0 < |h| ≤ τ are near-misses for the round rule.
5. **Boundary points** come from curve–surface intersection of each piece's boundary.
6. **Tracing** starts from each piece's smaller endpoint; a step is accepted only when an interval implicit-function test proves its box holds one branch segment, and traced points are Krawczyk-certified roots of the exact equations.
7. **Coincidence.** Regions whose distance enclosure stays below τ become coincidence regions.
8. **Output.** Each branch becomes a curve with a fitted B-spline, two parameter curves and its certified deviation.

Work limits are local (a depth per pair, steps per piece), so output never depends on processing order; unresolved pairs go to the round rule or fail with `Ambiguous { faces, region }`.

**Decision D-ANV-16:** SSI uses subdivision with Bernstein and interval enclosures, normal-cone loop exclusion, Krawczyk certification of characteristic points as critical points of signed distance, and certified tracing, with a topology certificate per pair. *Why:* branch-graph guarantees in `f64` with interval rules, parallel over pairs. *Rejected:* marching from sampled seeds (misses loops, jumps branches); purely algebraic methods (degrees explode for offsets and blends); lattice sampling as the decision method.

Phase 1 certifies SSI among planes, quadrics, tori, extrusion and revolution surfaces, NURBS–analytic pairs and the NURBS pairs that GP1 and the prismatic ABC corpus need; general NURBS–NURBS pairs follow in phase 2 (contract 13.2).

### Tangential contact

Blends are tangent to their supports, so later operations near them meet tangential contact along curves on most real parts. Where curvatures differ by Δκ, a shift ε moves crossings by √(2ε/Δκ), about 10⁻⁸ m for ε = 10⁻¹⁶ m and Δκ = 1 m⁻¹, so naive tolerance decisions create spurious coincidence bands.

Faces sharing an edge with a `Continuity` certificate are not re-intersected along it. A new surface tangent to an existing face goes to the contact-curve algorithm, which traces the reduced system (the critical-point system without its rank-deficient direction, with h = 0), certifies it by an interval test and imprints one tangential edge with τ = max(ρ, certified contact deviation).

| Case | Detection | Result |
| --- | --- | --- |
| Transversal crossing | Disjoint normal cones along the branch | Certified curve |
| Tangent point | Regular root of the critical-point system with h = 0 | Isolated point with contact order |
| Tangent contact along a curve | Certificate, or rank-deficient critical-point system | One tangential edge from the contact-curve algorithm |
| Overlap | Distance enclosure below τ over a region | Coincidence region; Booleans merge the faces |
| Near-miss closer than τ | Enclosure below τ, normal cones separated | Touch, with growth recorded within the cap |
| Branch crossing | Saddle-type root with h = 0 | Branch-graph vertex of degree 4 |
| Surface singularity | Declared singular point | Characteristic point |

**Decision D-ANV-26:** Constructions record `Continuity` certificates on edges they make tangent, and tangential contact along curves uses a certified contact-curve algorithm on the reduced critical-point system. *Why:* blend tangency is the common case, the full system is singular along contact curves, and certificates keep tangency the construction already knows. *Rejected:* the coincidence rule for tangency (spurious bands about 2√(2τ/Δκ) wide); re-intersecting certified edges (ill-conditioned, no new information).

### GPU use and freedom to operate

The GPU evaluates both surfaces on `f32` grids with per-cell boxes, as published in 2008 [Krishnamurthy et al. 2008], to order pairs likely to hold a branch, and tests integer box overlaps whose candidate sets equal the CPU's (contract 7.1). Tolerance decisions classify certified enclosures of exact distances, never sampled points.

US 12,229,885 B1 (inventor Alyn Rockwood, assignee an individual; Zoo's engine overview describes a related method) claims intersection points formed from points of one surface within a threshold distance of the other; claims 1, 6 and 11 compare point sets, and claim 16 recites no GPU [US12229885B1; US12229885B1 full text; Zoo engine overview]. Counsel reviews claims 1, 6, 11 and 16 against the CPU and GPU paths and pending continuations, with an invalidity search from the 2008 work; until the opinion arrives, SSI itself is a phase 1 release risk.

**Decision D-ANV-17:** In intersections the GPU only orders CPU work by sampling and prunes it by exact integer box tests; every intersection point is a certified root of the exact equations, never a point selected from a sample set by a distance threshold. *Why:* outputs are identical with and without a GPU, certified roots carry guarantees thresholded samples cannot, and this is the distinction counsel assesses. *Rejected:* dense sampled SSI on the GPU (uncertified; Zoo's overview calls SSI inherently approximate [Zoo engine overview]); no GPU use. (revised in round 2)

Triangle pairs use exact arrangements with indirect predicates [Attene 2020; Cherchi et al. 2022]; facet faces meet exact surfaces through certified plane and edge intersections; regular subdivision-limit faces are bicubic patches; implicits produce curves only on conversion.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Curve–curve and curve–surface intersection | Certified points and overlaps, classified transversal or tangent | `Ambiguous { entities, region }` | ANV-O-SSI-1 | 0 (analytic), 1 |
| SSI, analytic and NURBS–analytic pairs | Certified branch graph with topology certificate | `Ambiguous`, `WorkLimit` | ANV-O-SSI-1, ANV-O-SSI-2 | 1 |
| SSI, general NURBS–NURBS pairs | As above | As above | ANV-O-SSI-3 | 2 |
| Contact curves and continuity certificates | Tangential edge with τ = max(ρ, certified deviation) | `ToleranceGrowth` | ANV-O-CONTACT-1 | 1 |
| `anvil::intersect` | Two entity sets → new wire Body with `Created(intersection)` records | `Ambiguous` | ANV-O-SSI-1 | 1 |
| GPU work ordering and integer broad phase | Same output with and without a GPU; CPU path registered for every GPU path | Device loss is an Abort; Kiln reruns on the CPU path | ANV-O-DET-1 | 1 |

## Booleans, splits and patterns

One cellular arrangement engine runs every Boolean:

1. Intersect the faces that overlap in the broad phase (SSI for exact faces, exact arrangements for facets).
2. Imprint the curves on every operand.
3. Merge coincident entities by the round rule.
4. Classify each 3-cell's membership vector by radial order and one point classification per connected group, as in Lévy's Weiler model [Lévy 2024], with generalized winding numbers for imperfect operands [Spainhour and Weiss 2025].
5. Select cells by the expression.
6. Regularize, merge same-surface faces and emit history.

Expressions are n-ary, and Kiln lowers a whole CSG tree to one arrangement, so rounding happens once per tree.

`keep: Cells` returns every non-empty cell as a region labelled by its membership vector. Overmolding an insert is `boolean([insert, shot], keep: Cells)` with materials per region, which is the conformal multi-region Body that `tetrahedralize` meshes with shared interfaces.

**Decision D-ANV-19:** One cellular arrangement engine implements Booleans for every representation pair without an implicit operand, and the same engine serves n-ary expressions, cell-keeping results, `split`, `imprint` and `interference`. *Why:* these operations differ only in which cells they keep and report, and Parasolid's Booleans already imprint, join and select [Jackson 1995]. *Rejected:* separate union, subtract and intersect paths (three times the special cases); binary-only Booleans (n − 1 passes for n tools).

| Pair | Result | Method |
| --- | --- | --- |
| B-rep × B-rep | B-rep | Arrangement with certified SSI |
| Mesh × Mesh | Mesh | Exact arrangement chosen by the bake-off below, with checked output rounding |
| B-rep × Mesh, SubD | B-rep with facet or limit faces | Operands enter through the lattice |
| Implicit × anything | Implicit with kept exact faces | min, max and negation; explicit operands become exact-distance leaves |

### Mesh Booleans

EMBER's exact plane-based local arrangements take 34 ms for 1.2 million triangles on 8 cores, from 26-bit integer input, but output a polygon soup that needs topology recovery [EMBER 2022]. Cherchi and colleagues' indirect-predicate arrangements take 0.14 s per frame at 200,000 triangles and leave exact-to-float output open [Cherchi et al. 2022]; trueform claims up to 100× speedups with watertight output [trueform 2026]. Manifold guarantees manifold output, while ε-validity is a goal [Manifold wiki].

A phase 0 bake-off on Thingi10K pairs and thingiCSG compares three candidates: (a) plane-based local arrangements on integer coordinates of the Body's ρ grid (2³⁰ to 2³¹ cells per diagonal, with wider fixed-width predicates) and topology recovery into the half-edge Mesh; (b) trueform's topological aggregation, once its licence is confirmed; (c) indirect predicates on `f64` input with checked rounding. The winner is chosen on validity first, then time, and sets the million-triangle target. Output rounding is checked exactly, repairs collapse only edges shorter than 2ε, at most three passes run, and a remaining conflict fails with `PrecisionExhausted`.

**Decision D-ANV-20:** The mesh Boolean method is chosen by a phase 0 bake-off among ρ-grid integer local arrangements, topological aggregation and indirect predicates, with exact classification, bounded output repair and one rounding per CSG tree. *Why:* published speeds differ by one to three orders of magnitude, and ρ-grid quantization keeps Anvil's resolution, which removes the round 1 objection to integer input. *Rejected:* fixing the indirect-predicate design without measurement; Manifold's method (ε-validity not guaranteed); linking a C++ library (FFI; kept as oracles). (revised in round 2)

### Patterns, hulls and Minkowski sums

`anvil::pattern` makes keyed copies (contract 5: `linear` keys (i, j), `circular` the angular index, `at_points` the anchor's id, `fill` lattice coordinates, `by_density` initial keys), combined in one n-ary Boolean. When copies overlap only the target and meet congruent target faces, decided by the round rule on the certified distance between transformed and actual faces, the first copy's intersections are transformed and reused, with one rotation rounding added to their bounds. Translational patterns on planes reuse fully; circular patterns reuse on surfaces of revolution about the pattern axis; mirror patterns reuse where the target is symmetric within τ.

`anvil::hull` computes convex hulls exactly with orientation predicates on meshes and facet faces; B-rep operands use support-function sampling with a stated bound. `anvil::minkowski` sums meshes and convex B-rep operands by convex decomposition and pairwise convex sums. OpenSCAD lists `hull()` and `minkowski()` among its core transformations [OpenSCAD cheat sheet].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::boolean` | Bodies, n-ary expression, `keep: Regularized` or `Cells` → Body; `Split`, `Merged`, `Deleted(Internal)`, `Created(intersection_edge)` | `Ambiguous`, `ToleranceGrowth`, `BelowResolution { size }`, `PrecisionExhausted` | ANV-O-BOOL-1 to ANV-O-BOOL-4 | 1 |
| `anvil::split` | Body, tool → pieces or one cellular Body | `ToolDoesNotCut`, `OpenTool { gaps }` | ANV-O-BOOL-5 | 1 |
| `anvil::imprint` | Body, curves or Body → split faces and edges, volume unchanged | `CurveNotOnFace { gap }` | ANV-O-BOOL-6 | 1 |
| `anvil::trim` | Sheet, boundary or tool, kept side | `KeepSideAmbiguous` | ANV-O-TRIM-1 | 1 |
| `anvil::extend` | Face edge, distance or target, `Natural`, `Linear` or `CurvatureContinuous` | `CannotExtend { reason }` | ANV-O-TRIM-2 | 1 |
| `anvil::transform` | Rigid motion, scale or reflection; keeps or derives ids per D-ANV-30 | `Degenerate` for zero scale | ANV-O-XF-1, ANV-O-COPY-1 | 0 |
| `anvil::pattern` | Keyed copies, `Separate`, `Union` or `Subtract`, with congruent reuse | `CopyFailed { key, error }` unless `skip`; `Overlapping { pairs }` | ANV-O-PAT-1, ANV-O-PAT-2 | 1 |
| `anvil::hull` | Meshes, facet faces → exact hull; B-rep operands with a stated bound | `Degenerate` (coplanar input) | ANV-O-HULL-1 | 1 (meshes, facets), 2 (B-rep) |
| `anvil::minkowski` | Meshes and convex B-rep operands | `NotConvex { operand }` for B-rep operands | ANV-O-HULL-1 | 2 |
| `anvil::convex_decompose` | Body → convex parts with a Hausdorff bound | `WorkLimit` | ANV-O-HULL-1 | 3 |

## Blends, offsets, draft and direct edits

### Blends

Blending is a staged research program (contract 7.1). `anvil::blend` takes edges (a `Query` with extent use, tangent chains propagated unless `propagate: false`), a radius law (`Constant`, `Linear(r0, r1)`, later a Field), a section (`Circular`, later `Conic { rho }` and `CurvatureContinuous`), corners (`Auto`, `Setback { distances }`, `Sharp`), an overflow rule (`RollOver` by default, `KeepEdge`, `Fail`), a variant (`EdgeChain` by default, later `FaceFace { a, b, hold_lines }`, `ThreeFace { a, middle, b }` and `ChordWidth`) and a fallback. `anvil::chamfer` uses the same engine with a ruled section sized by two distances or a distance and an angle.

For each chain, Anvil offsets both supports by r toward the side where the ball rolls, intersects the offsets with certified SSI to get the spine, projects it onto the supports for the contact curves, builds a procedural rolling-ball surface, resolves overflow against neighbouring faces, fills corners and rebuilds topology. Supports may be procedural blend, offset and swept faces, so sequential fillets work. Corners use the setback split of Várady and Rockwood (1995; with Hoffmann, 1998) [Várady publication list]: each blend stops a setback before the vertex, and an n-sided patch, G1 to its neighbours, fills the gap.

| Stage | Capabilities | Phase |
| --- | --- | --- |
| 1 | Constant and linearly varying radius; circular sections; procedural blend, offset and swept supports; `RollOver` and `KeepEdge`; valence-3 corners with unequal radii and mixed convexity by setbacks; chamfer–fillet corners; termination at smooth edges; chamfers | 1 |
| 2 | Conic and G2 sections; Field-driven radii; `FaceFace` with hold lines; `ThreeFace` (full round); `ChordWidth`; `edit_blend` | 2 |
| 3 | Corners of valence four and above; blends across facet faces | 3 |
| 4 | G3 sections | 4 |

**Decision D-ANV-29:** Stage 1 blends cover the cases above, and one re-fillet benchmark measures every stage: a phase 0 corpus of ABC parts whose fillets are recognized, removed and re-applied with their recorded radii. Targets: 95% success on stage-1 configurations at the phase 1 gate and 97% on all configurations at the phase 2 gate, with OCCT 8.0 measured on the same corpus; MEC states the same targets. *Why:* golden product 1 and everyday parts need sequential fillets, rolling overflow and mixed corners from the start; one benchmark keeps both tabs' claims comparable. *Rejected:* stage 1 limited to equal-radius corners and `KeepEdge` (fails on common parts); targets only relative to OCCT (no absolute floor).

Failures carry fixes: `RadiusTooLarge { edge, max_feasible }` (use the maximum, split the chain); `BlendOverflow { faces }` (other overflow rule, smaller radius); `VertexBlendFailed { vertex, reason }` (larger setbacks, a sharp corner, the fallback); `SelfIntersecting { region }` (a smaller local radius). With `fallback: Implicit { max_deviation }`, a failed region becomes the zero set of a smooth union of the supports' exact distances, fitted with G1 boundary constraints to the neighbouring exact faces by constrained least squares. Its seam is a tolerant edge with τ equal to the certified gap (`ToleranceGrowth` beyond τ_cap), and `Note::BlendFallback { region, deviation, seam_gap }` states its certified maximum deviation from the rolling-ball surface.

History: `Created { role: blend, from: [edge] }`, `Created { role: vertex_blend, from: [vertex] }`, `Deleted { by: blend face }` for each blended edge and `Modified` for trimmed supports; contact edges get `Continuity` certificates.

### Offsets, shells and draft

`Round` offsets of a B-rep are exact Minkowski sums with a ball: offset faces, pipes around convex edges and spheres around convex vertices form one arrangement, and Anvil keeps the cells within certified distance d of the input; negative offsets do the same for the complement. `Natural` offsets extend and re-intersect offset faces. Phase 1 offsets analytic and procedural faces; free-form (NURBS) offsets follow in phase 2 (contract 13.2), and meshes use feature-preserving mitered offsets [Cao et al. 2024].

`anvil::draft` tilts faces about a neutral element by an angle or a Field: planes stay planes, cylinders become cones, and free-form faces become procedural drafted surfaces.

### Direct edits and blend regrowth

`offset_faces`, `move_faces`, `replace_faces`, `delete_faces` and `draft` handle adjacent blends the same way. Blends next to the edited faces (Anvil-made blends carry supports, radius and section; imported ones come from `recognize_aspects`) are removed, the edit is applied, and the blends are rebuilt with the same parameters and ids (`Modified`), or the operation fails with `BlendRegrowFailed { blend, reason }` and the fixes "remove blend" and "reduce radius". UIX's phase 1 push-pull on non-cap faces uses `offset_faces`; `move_faces` arrives in phase 2.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::blend` | Edges (extent use), radius law, section, corners, overflow, variant → Body; certificates on contact edges | As listed above | ANV-O-BLEND-1 to ANV-O-BLEND-5 | 1 (stage 1) to 4 |
| `anvil::chamfer` | Edges, two distances or distance and angle | `RadiusTooLarge`, `VertexBlendFailed` | ANV-O-BLEND-1 | 1 |
| `anvil::edit_blend` | Anvil-made or recognized blend, new radius or section | `BlendRegrowFailed` | ANV-O-BLEND-6 | 2 |
| `anvil::offset` | Body, signed distance (value or `Field<Faces, Length>`), `Round` or `Natural` | `OffsetCollapse { faces }`, `FieldOutOfRange` | ANV-O-OFF-1 | 1 (analytic, procedural, implicit), 2 (NURBS, mesh) |
| `anvil::offset_faces` | Faces moved along normals; neighbours extended; blends regrown | `NeighborCannotExtend { face }`, `BlendRegrowFailed` | ANV-O-OFF-2, ANV-O-BLEND-6 | 1 |
| `anvil::shell` | Solid, faces to open, thickness (value or Field) | `WallCollapse { region }` | ANV-O-OFF-3 | 1 |
| `anvil::thicken` | Sheet, thickness, side → solid | `SelfIntersecting` | ANV-O-OFF-3 | 1 |
| `anvil::draft` | Faces, pull direction, neutral element, angle or Field; blends regrown | `DraftNotPossible { face, reason }`, `BlendRegrowFailed` | ANV-O-DRAFT-1 | 1 (analytic), 2 (free-form) |
| `anvil::move_faces`, `replace_faces`, `delete_faces` | Faces and a motion, replacement or removal; neighbours re-intersected; blends regrown | `TopologyChangeRejected`, `ReplacementDoesNotClose { gaps }`, `CannotHeal { loop }` | ANV-O-DE-1, ANV-O-DE-2 | 2 |
| `anvil::recognize_aspects`, `recognize_relations` | Holes, fillets, chamfers, bosses, pockets, ribs, patterns; coplanar, coaxial, tangent and other relations by the round rule | Unrecognized faces listed | ANV-O-REC-1, ANV-O-REC-2 | 2 |
| `anvil::defeature` | Aspect kinds below sizes, or faces → recognize, then delete | `CannotHeal` per aspect | ANV-O-DE-3 | 2 |

## Construction, surfacing and derived geometry

MEC's sketch `text` emits glyph outlines as exact Bézier curves, which `make_regions` turns into faces, so text, emboss and engrave on planar and cylindrical faces work in phase 1, as code-CAD users expect [OpenSCAD cheat sheet].

For Flux's shell and beam models (contract 7.1), `anvil::mid_surface` pairs offset faces, builds exact mid-surfaces for plane, cylinder and cone pairs and procedural ones otherwise, extends and intersects them at junctions, and returns a sheet with a thickness Field and junction curves. `anvil::member_axes` returns a wire Body of member axes and joints with each cross-section as a planar region and its area and second moments; Flux computes torsion and warping constants from the region.

For control-vertex drags, Anvil re-evaluates the edited patch on the GPU at `Preview` fidelity, with zebra and curvature Fields from the same evaluation, within 16 ms (target), and releasing the drag writes one Ingot edit. G3 `match_surface` and `blend_surface` ship in the same phase as MEC's control-vertex editing. Continuity analyses default to thresholds relative to the Body's resolution and size; designs may set absolute overrides.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::primitive` | Box, wedge, cylinder, cone, sphere, torus, prism → solid with roles | `Degenerate { parameter }` | ANV-O-OP-1 | 0 |
| `anvil::make_regions` | Planar wires (lines, arcs, Bézier glyph outlines) → faces with nested loops | `OpenProfile { gaps }`, `SelfOverlap { curves }` | ANV-O-OP-2 | 1 |
| `anvil::extrude` | Faces; direction; distance, Field or up-to target; draft; symmetric; twist and scale Fields → roles `start_cap`, `end_cap`, `side(e)` | `SelfIntersecting` with the largest feasible draft; `UpToNotReached { target }` | ANV-O-OP-3 | 0 (twist and scale 1) |
| `anvil::revolve` | Faces or curves, axis, angle ≤ 2π; no seam on a full turn | `AxisCrossesProfile { points }` | ANV-O-OP-4 | 0 |
| `anvil::sweep` | Profiles, path, frame rule, scale and twist Fields, guides; helical sweeps for threads | `SelfIntersecting { region }`, `FrameUndefined` with a rotation-minimizing fix | ANV-O-OP-5 | 1 |
| `anvil::loft` | Ordered sections, guides, end conditions, vertex correspondence | `IncompatibleSections`, `Twisted`, `ContinuityNotMet` | ANV-O-OP-6 | 1 |
| `anvil::boundary_surface`, `fill_surface`, `blend_surface`, `match_surface` | Curve networks, n-sided boundaries, bridges and matches with G0 to G3 conditions; Gordon surfaces for networks, which OCCT 8.0 also adds [OCCT 8.0] | `NetworkNotCompatible`, `BoundaryNotClosed { gap }`, `ContinuityNotMet { edge, achieved }` | ANV-O-OP-7, ANV-O-OP-8 | 2 (G0 to G2), 3 (G3) |
| Control-vertex drag preview | Patch, control-point change → preview patch, zebra and curvature Fields | Falls back to the Kiln rebuild | ANV-O-FID-1 | 3 |
| `anvil::project_curve` | Curves onto faces along a direction or normal | `Misses { segments }` | ANV-O-PROJ-1 | 1 |
| `anvil::wrap` | Planar curves or sheets onto developable faces (plane, cylinder, cone); any face through `parameterize`; emboss and engrave through `offset_faces` | `OutOfDomain { curves }` | ANV-O-PROJ-2 | 1 (developable), 3 (general) |
| `anvil::parameterize` | Faces or mesh region → (u, v) map by Boundary First Flattening (MEC's choice) or least-squares conformal | `NotDisk { genus }` with cut suggestions | ANV-O-PAR-1 | 3 |
| `anvil::unfold`, `anvil::fold` | Sheet metal and flex circuits with developable faces and a neutral-layer offset per bend | `NotDevelopable { faces, deviation }` | ANV-O-SM-1 | 2 |
| `anvil::drape_kinematic` | Woven fabric on a tool surface, pin-jointed net, quadrants in fixed order → fibre curves, shear Field | `ExcessiveShear { region, angle }` | ANV-O-DRAPE-1 | 4 |
| `anvil::mid_surface` | Thin-walled solid → sheet, thickness Field, junction curves; `Created { role: mid(a, b) }` | `UnpairedFaces { faces, reason }` with the partial sheet | ANV-O-MID-1 | 2 |
| `anvil::member_axes` | Lattice strut graph or swept members → axes, joints, cross-section regions, area and second moments | `NotPrismatic { region }` | ANV-O-AXIS-1 | 1 (lattices), 2 (swept members) |
| `anvil::section` | Body and a plane, a stack of planes or a surface → regions or curves, any representation | `NotClosed { gaps }` naming defective faces | ANV-O-SEC-1 | 1 |
| `anvil::deform` | Body, displacement Field or cage → same representation; ids kept | `FoldOver { region }`, `ToleranceNotMet { achieved }` | ANV-O-DEF-1 | 2 |
| `anvil::morph` | Source, target or correspondences → deformation Field, then `deform` | `NoCorrespondence` | ANV-O-DEF-2 | 3 |
| `anvil::shrinkwrap` | Bodies, gap g → one closed skin by closing on exact distances | `WorkLimit` | ANV-O-OFF-4 | 2 |

## Implicit representation

An `Implicit` Body is a hash-consed expression DAG f: ℝ³ → ℝ whose region f ≤ 0 is the solid, plus the exact faces its B-rep leaves keep. Nodes cover arithmetic, min, max, `detmath` functions, exact-distance primitives, hard and smooth CSG, warps (including Field-driven ones), offsets and shells, repetition, TPMS families and strut graphs, and leaves for B-rep or Mesh distances, Fields and cached bricks.

### Distance kinds

| Kind | Meaning | Allowed uses |
| --- | --- | --- |
| `Exact` | f is the signed distance | Everything, including offsets by any amount |
| `Bound(L)` | Correct sign and \|f(p)\| ≤ L·dist(p, boundary) | Classification, Booleans, sphere tracing with step \|f\|/L, meshing; offsets after redistancing |
| `Lipschitz(L)` | Correct sign and \|f(p) − f(q)\| ≤ L·\|p − q\| | As `Bound(L)` |
| `SignOnly` | Correct sign only (C0 warps) | Interval classification only |

Kinds propagate statically (min of exact distances is exact outside; a warp's constant is the enclosure of ‖J⁻¹‖), and offsetting a non-exact implicit first redistances a narrow band around the certified zero set, unless the caller accepts `approximate: true` with an `Estimated` bound.

**Decision D-ANV-10:** Implicit nodes carry a statically propagated distance kind and Lipschitz constant, and operations that need exact distances redistance in a narrow band. *Why:* lattices, smooth blends and warps rarely give exact distances, and Lipschitz pruning relies on the same property [Barbier et al. 2025]. *Rejected:* assuming every implicit is a signed distance (offsets and clearances become silently wrong); allowing only exact-distance constructions (excludes TPMS, smooth blends and Field-driven geometry).

### Evaluation

Expressions lower to register-allocated tapes in the shared kernel IR (contract 7.5), as Fidget's 256-register bytecode does [Fidget], run by point, gradient, interval and reduced-affine evaluators. Interval evaluation prunes inactive min and max branches per box, shortening tapes about 17× per tile and 216× per subtile in Keeter's measurements, though smooth blends defeat it [Keeter 2020]. Anvil also prunes smooth-union branches whose Lipschitz bound lies a blend radius above the other branch [Barbier et al. 2025], and switches ambiguous wide boxes to reduced affine arithmetic [Sharp and Jacobson 2022].

**Decision D-ANV-11:** Implicit tapes are kernel-IR programs, and the canonical CPU evaluator is a SIMD interpreter with interval, affine and Lipschitz pruning; compiled CPU paths (ahead-of-time and Wasm SIMD) keep the IR's operation order and give identical bits; a WGSL tape interpreter takes tapes as data for previews and for UIX's rendering during edits. *Why:* Fidget measures a 31× compiled advantage for brute force but about 25% once pruning runs, and the fastest Prospero entry is a NEON interpreter at 0.29 ms [Fidget; Prospero]; one IR keeps operation order fixed (contract 7.5); taking tapes as data avoids a shader compile per edit. *Rejected:* a native JIT per architecture (second code path, no gain once pruned); a WGSL shader compile per edit (lands inside the drag). (revised in round 2)

WGSL offers `f32`, `f16` and AbstractFloat [WGSL], with accuracy not yet verified for intervals [unverified], so GPU results only order, cull and preview. A CAS cache of 8³ bricks of values and gradients covers the narrow band, and its trilinear reads report a bound from the Lipschitz constant and spacing.

### Fields and lattices

Field leaves sample Flux `Field`s at a requested accuracy, adding the sampled error to the Body's bounds. `anvil::implicit_from_field` needs a continuous Field with a finite gradient bound; degree-0 and quadrature-point Fields fail with `NotContinuous`, whose fix is the filtered, projected density from Flux's topology optimization.

`anvil::lattice` fills a region from family, cell size, thickness, orientation and skin Fields; domain repetition keeps millions of cells to a few hundred nodes, and graphs above about 10⁴ struts use a spatial hash leaf. Strut lattices expose their graph for beam models and for the 3MF Beam Lattice extension 1.2.0, which stores beams by vertex indices with end radii, cap modes and balls [3MF beam lattice spec]. Cell-family generators such as MEC's are Wasm components that emit graphs or tapes.

### Implicit meshing

`convert(implicit, into: Mesh)` uses adaptive dual contouring on an octree:

1. Interval evaluation marks cells inside, outside or ambiguous; ambiguous cells refine.
2. A surface cell is certified when ∇f·d excludes zero for a direction d from the cell's gradient cone (the axes first, then the normalized sum of the active leaves' gradients), which certifies box corners and CSG edges; cells that reach λ uncertified are flagged.
3. Each cell places one vertex per surface piece by minimizing a quadric error function from exact gradients, keeping sharp features.
4. Manifold dual contouring connects the vertices [Fidget], a structure that parallelizes well on GPUs [Hwang and Sung 2024].
5. An exact self-intersection check repairs crossings by moving vertices within their cells.

Surface points lie within one cell diagonal of the mesh and triangles within two of the surface, or within max |f| over the triangle divided by a certified floor of |∇f| if smaller; the bound is `Guaranteed` in certified cells and `Estimated` in listed flagged ones. Keeter notes that good meshing of arbitrary implicit surfaces remains unsolved [Fidget].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::implicit` | Ingot expression → DAG with distance kind and Lipschitz constant | `SignOnly` uses reported as slow | ANV-O-IMP-1, ANV-O-IMP-2 | 1 |
| Tape evaluation and pruning | Point, gradient, interval, affine evaluators; pruned tapes equal full tapes per region | — | ANV-O-IMP-3 | 1 |
| WGSL tape interpreter | Tapes as data for previews and UIX rendering | Device loss is an Abort; CPU path | ANV-O-FID-1 | 1 |
| `anvil::implicit_from_field` | Continuous Field, iso-value → implicit, kind `Lipschitz(L)`, bound = sampling error / certified gradient floor | `NotContinuous`, `NoIsoSurface`, `FlatIsoSurface { region }` | ANV-O-IMP-4 | 1 |
| `anvil::lattice` | Region, family, cell size, thickness, orientation, skin Fields → implicit with roles `wall`, `strut`, `node`, `skin`, and the strut graph | `BelowResolution`, `FieldOutOfRange`, `TooManyCells { estimated, limit }` | ANV-O-LAT-1 | 1 |
| Implicit meshing | Implicit → manifold Mesh with two-sided bound | `Uncertified` cells listed | ANV-O-CONV-1 | 1 |

## Meshes and volume meshing

### Surface meshes and repair

A `Mesh` stores `f64` positions in the Body frame, three half-edges per triangle with a paired-half-edge bijection, face groups with `EntityId`s, crease edges, typed per-vertex or per-corner property channels (normals, UVs, colours, `(EntityId, u, v)` back-references, Field values), regions for closed meshes, and the precision ε. Per-corner properties use their own indices, so seams never break topology, as Manifold's `MeshGL` merge vectors do [Manifold wiki]. A Mesh with vertices and no triangles is a point set, used for scans.

`anvil::mesh_from_triangles` builds a valid Mesh, a facet B-rep when the data is non-manifold by intent, or fails with `NotManifold { edges, vertices }`. `anvil::repair_mesh` welds vertices within the healing limit in canonical order, collapses degenerate triangles, builds the exact arrangement of all triangles, keeps the cells whose generalized winding number exceeds 0.5, which stays meaningful for self-intersecting, open and non-manifold input [Jacobson et al. 2013], and closes holes below a fill limit. It reports the largest input displacement (`Guaranteed`) and the area changed.

### Volume meshes

A volume Mesh adds tetrahedra, hexahedra, prisms, pyramids and general polyhedra with region indices; geometry order up to 8 with Bézier control nodes, following Flux's solution degree; and boundary facets classified to the B-rep face or interface they approximate, so Flux resolves `ds(part.face(q))` through `EntityId`s. Element quality is the minimum scaled Jacobian, certified from Bernstein coefficients.

**Decision D-ANV-12:** Volume meshing, adaptation and node optimization are Anvil operations; Flux chooses what to mesh and how finely through sizing and metric Fields. *Why:* meshing needs exact geometry, the same predicates and tolerance model, and `EntityId`s for boundary classification, and its outputs are Bodies other operations consume (contract 7.1). *Rejected:* meshing in Flux (duplicates predicates and naming); meshing as a Wasm component (a general operation that needs Anvil's evaluators in every inner loop).

| Strategy | When | Method | Boundary |
| --- | --- | --- | --- |
| `Conforming` (default) | Valid input | Face tessellation by the sizing Field, constrained Delaunay tetrahedrization with implicit Steiner points and indirect predicates [Diazzi et al. 2023], local quality improvement | Facets subdivide the tessellation; Steiner points move by one rounding |
| `Envelope` | Soups, scans, healed imports | Incremental insertion into a floating-point mesh with optimization inside an envelope [fTetWild 2020] | Within ε_env of the input; omitted triangles reported |

Rounding the Steiner points of Diazzi and colleagues' conforming CDT keeps 93.22% of meshes valid (99.77% after post-processing), and some inputs have no floating-point conforming mesh [Diazzi et al. 2023]. Anvil checks every element with exact orientation predicates after rounding, re-inserts inverted ones locally and otherwise fails with `NotRepresentable { elements }`, suggesting `Envelope`. fTetWild inserts every Thingi10K input triangle in practice without guaranteeing it [fTetWild 2020]; Anvil reports omissions.

Curved elements place boundary control nodes on the classified face in its parameter space, certify validity by positive Bernstein coefficients of the Jacobian determinant, untangle interior nodes, then refine locally. 3D Bézier Guarding covers polynomial boundaries with curved elements free of inversions [Khanteimouri and Campen 2023], and bijective coarse high-order meshing adds a distance bound and a bijective map to the input [Jiang et al. 2021]; Anvil guards faces with polynomial geometry or caches and uses project, certify and untangle elsewhere.

Hex-dominant meshing converts tetrahedra by field-guided polyhedral agglomeration, which keeps topological validity at every step [Gao et al. 2017]; the hex-meshing survey finds no method that is robust, high-quality and automatic at once [hex survey 2022], so Anvil promises hex-dominant output, with all-hex meshes only for sweepable regions. `split_polyhedra` turns remaining polyhedra into tetrahedra and pyramids for FEM, keeping polyhedra for finite volume. Boundary layers advance prisms along smoothed normals with exact collision tests and pyramid transitions; curved layers split one thick curved layer isoparametrically, as for stretched elements around streamlined bodies [Marcon et al. 2019].

### Adaptation and surface remeshing

Adaptation history maps new cells to their parents as a compact parent-index array, expanded to records on request, so Flux transfers Fields by its own rules (Flux names Mmg as its anisotropic reference). Decimation uses quadric error metrics [Garland and Heckbert] but verifies each collapse against the original surface, since the quadric is a heuristic; parallel modification uses deterministic independent sets. Quad mode follows feature-line driven quad remeshing, which fails on under 0.5% of Thingi10K models [Pietroni et al. 2021].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::mesh_from_triangles` | Buffers → Mesh, facet B-rep or point set | `NotManifold { edges, vertices }` | ANV-O-MESH-1 | 0 |
| `anvil::repair_mesh` | Triangle data → valid Mesh with displacement and area report | `Unrepairable { reason }` | ANV-O-MESH-2 | 1 |
| `anvil::tetrahedralize` | Body, sizing `Field<Body, Length>`, geometry order, strategy, quality → volume Mesh, boundary bound | `InvalidInput`, `NotRepresentable`, `WorkLimit`, `QualityNotReached { worst, target }` | ANV-O-TET-1, ANV-O-HO-1 | 2 (`Conforming`, curved by projection), 3 (`Envelope`, guarding) |
| `anvil::untangle` | Mesh → valid curved mesh | `InvalidElement { cell, jacobian_min }` | ANV-O-HO-1 | 2 |
| `anvil::hex_dominant`, `sweep_mesh` | Tetrahedra → hex-dominant; sweepable region → all-hex; optional `split_polyhedra` | `NotSweepable { reason, faces }` | ANV-O-HEX-1 | 3 (sweep), 4 (hex-dominant) |
| `anvil::boundary_layer` | Faces (`Query`), first height Field, growth, layers | `LayerCollapsed { faces, achieved_layers }` with the partial mesh | ANV-O-BL-1 | 4 |
| `anvil::refine_mesh` | Marked simplices → newest-vertex bisection with closure | `InvalidElement` | ANV-O-ADAPT-1 | 2 |
| `anvil::adapt_mesh`, `optimize_mesh` | Metric `Field<Body, Metric>` → adapted mesh, parent map; node relocation | `QualityNotReached` | ANV-O-ADAPT-1 | 3 |
| `anvil::polyhedral_mesh` | Tetrahedra → boundary-conforming polyhedral dual, prisms kept | `NonPlanarFace { cells, deviation }` | ANV-O-POLY-1 | 3 |
| `anvil::common_refinement` | Two discretizations of one interface → overlay with both parents | `NotSameInterface { gap }` | ANV-O-MESH-4 | 4 |
| `anvil::remesh`, `decimate`, `smooth` | Isotropic, metric or quad remeshing; verified-bound decimation; Taubin and bilaplacian smoothing; face-group ids kept | `FeatureConflict { edges }` with the closest feasible target | ANV-O-REM-1 | 1 (decimate), 2, 3 (quads) |
| `anvil::segment_mesh` | Mesh → face groups by curvature and normals | — | ANV-O-MESH-3 | 3 |

## Subdivision surfaces

A `SubD` Body is a Catmull-Clark cage with real-valued semi-sharp and infinitely sharp edge creases, corner sharpness, boundary rules and an `EntityId` per cage element, following OpenSubdiv's conventions, whose limit surface matches RenderMan to numerical precision [OpenSubdiv repository]. Regular faces are bicubic B-spline patches. Faces near extraordinary vertices or creases use feature-adaptive subdivision, which computes the true limit up to machine precision [Nießner et al. 2012], and crease-free neighbourhoods may use Stam's eigen-analysis, which needs at most one extraordinary vertex per face and ignores creases [Stam 1998].

Where a fixed adaptive depth near creases and extraordinary vertices stops short of the limit, the geometric convergence of subdivision gives a certified bound per depth, recorded as that face's conversion bound. Curvature at extraordinary vertices is reported as singular.

**Decision D-ANV-13:** Anvil implements Catmull-Clark subdivision with semi-sharp creases natively in Rust, following OpenSubdiv's rules and using OpenSubdiv as an oracle. *Why:* limit surfaces must evaluate identically on CPU and in Wasm and feed exact B-rep faces; OpenSubdiv is C++ with CUDA, Metal and OpenGL back ends and licensed as Apache 2.0 with a modified trademark section [OpenSubdiv license]. *Rejected:* linking OpenSubdiv (FFI, no wgpu back end); Loop subdivision as the primary scheme (triangle cages suit meshes, not industrial design).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::subd_edit` | Move, extrude, inset, bevel, crease, insert loop, bridge; untouched cage ids kept | `NonManifoldResult`, `ZeroArea` | ANV-O-SUBD-1 | 2 |
| `anvil::subd_limit` | Limit points, derivatives and normals at (face, u, v), with the recorded bound near creases | `SingularPoint` for curvature | ANV-O-SUBD-1 | 2 |
| `anvil::convert` (Mesh → SubD, SubD → BRep, SubD → Mesh) | Cage from a mesh; exact limit faces or NURBS with certified bounds; limit tessellation | `ToleranceNotMet { achieved }` | ANV-O-SUBD-1, ANV-O-CONV-1 | 2 |
| `anvil::fit` (target SubD) | B-rep or mesh → cage by quad remeshing and least squares | `FitFailed { residual }` | ANV-O-FIT-2 | 4 |

## Planar integer geometry (`anvil-planar`)

`anvil-planar` stores 2D geometry on an integer grid declared per design (ELX uses nanometres): polygons with line and arc edges, an arc stored as three integer points. Predicates are exact in integer arithmetic: orientation, in-circle, and comparisons of segment, arc and polygon distances against squared integer thresholds.

Constructions (offsets, Minkowski sums with a disc, arc intersections) have irrational results, so they snap to the grid in a declared conservative direction: a region that must keep clearance (a copper fill) rounds inward, away from obstacles, and a keep-out or a region that must cover rounds outward. A reconstructed arc is kept only when the snapped arc passes the exact check; otherwise its polygonal approximation, snapped the same way, replaces it. Derived geometry therefore passes the exact rule checks by construction, with no hidden tolerance.

The same crate backs the Anvil operations and compiles into ELX's design-rule, fill and router Wasm components, so both paths give identical results. Flex circuits bend with the sheet-metal `anvil::fold`.

**Decision D-ANV-27:** `anvil-planar` makes predicates exact on stored integer geometry and snaps every construction conservatively in a declared direction, keeping arcs only when they pass the exact check. *Why:* offsets and arc intersections leave the integer grid, and rounding to nearest could place a fill up to about 0.7 grid units too close, so Crucible's own fills would fail its exact checks. *Rejected:* rounding to nearest with a hidden check tolerance (the rule check would no longer be exact); approximating every arc by segments (loses exact arcs that boards and masks use).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Exact planar predicates | Integer points, lines and arcs → exact signs and distance comparisons | `Overflow` above the declared coordinate range | ANV-O-PLANAR-1 | 3 |
| `anvil::planar::boolean` | Polygon sets with arcs, n-ary expression → exact result | — | ANV-O-PLANAR-1 | 3 |
| `anvil::planar::offset` | Polygons, distance (Minkowski sum with a disc), snap direction → conservative result | `Collapsed { regions }` | ANV-O-PLANAR-2 | 3 |
| `anvil::planar::distance` | Two polygon sets → exact minimum distance comparison and witnesses | — | ANV-O-PLANAR-1 | 3 |
| `anvil::planar::medial_axis` | Polygons with arcs → segment Voronoi skeleton, conservatively snapped | `WorkLimit` | ANV-O-PLANAR-2 | 3 |

## Conversions and error propagation

`anvil::convert(body, into, accuracy)` is the only conversion operation and returns a `Body`. Every approximating conversion and fit records on each face it produces a `FaceBound { position, normal }`: a two-sided Hausdorff bound on position and an angle bound on normals, each `Quantified` or `NotQuantified { reason }` (contract 5's `Unknown`; CCR-ANV-8). Fits certify both bounds by certified sampling of distance and normal deviation.

Bounds propagate through later operations by these rules, where θ_min is a certified lower bound of the angle between two surfaces along an edge:

| Construction from bounded faces | Position bound | Normal bound |
| --- | --- | --- |
| Trim, split, imprint, Boolean (face kept) | Unchanged | Unchanged |
| Normal offset by d | p + \|d\|·n | n |
| Intersection edge, blend spine, contact curve | max(p_a, p_b) / sin θ_min | — (edge) |
| Rolling-ball blend of radius r on a spine bounded by s | s | 2s / r |
| Natural-offset corner where faces meet at angle θ | p / sin(θ/2) | n |
| θ_min not certified above zero (near tangency) | `NotQuantified { NearTangent { edge } }` | `NotQuantified` |

`body.error()` is the largest face position bound, or `NotQuantified` if any face is, and Ingot's `Truth` makes comparisons on an unquantified bound `Undecided`. The bound describes representation error only: uncertainty of `Approx` arguments goes to Ingot's `InputSensitivity` record, never into `body.error()`, and near-tangent configurations that resolve differently after a conversion appear as tolerance growth, not as part of the bound.

**Decision D-ANV-21:** Inclusions in the representation lattice are exact; approximating conversions record per-face `{ position, normal }` bounds that propagate through stated rules with certified conditioning or become `NotQuantified`. *Why:* a Hausdorff bound alone says nothing about normals, so offsets, intersections and blends on approximated faces could otherwise report `Guaranteed` bounds that do not hold. *Rejected:* inheriting the largest source bound (false near tangency and after offsets); one bound per Body (a local conversion would taint every face); RMS metrics (hide the worst deviation). (revised in round 2)

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| BRep → Mesh | Tessellation with certified chord control; face groups keep ids | `WorkLimit { triangles }` | ANV-O-CONV-1, ANV-O-TESS-1 | 0 |
| BRep or Mesh → Implicit | Exact signed-distance leaf with winding-number sign; zero error | — | ANV-O-CONV-1 | 1 |
| Mesh → BRep (facet) | Facet faces per face group, ids kept; zero error | — | ANV-O-CONV-1 | 1 |
| Implicit → Mesh | Certified dual contouring (Implicit representation) | `Uncertified` cells listed | ANV-O-CONV-1 | 1 |
| Implicit → BRep | Leaf-preserving: kept exact faces trimmed by certified intersection; facet faces elsewhere; fitted NURBS faces `Estimated` until checked | `Ambiguous` near tangency | ANV-O-CONV-1, ANV-O-LEAF-1 | 1 (facet), 3 (fitted) |
| Mesh → BRep (fitted) | Segment, fit primitives and NURBS, intersect, sew; `Estimated`, or `Guaranteed` after a certified check | `FitFailed { residual }` | ANV-O-FIT-2 | 4 |
| BRep, Mesh or Implicit → SubD | Quad remesh and cage fit; `Estimated` | `FitFailed` | ANV-O-FIT-2 | 4 |
| Bound propagation | Rules above, applied by every operation | `NotQuantified` faces listed | ANV-O-CONV-2 | 1 |

## Measurement, analysis and simulation services

Mass properties integrate polynomial fields over trimmed faces by the divergence and Green theorems with adaptive Gauss–Legendre quadrature whose panel remainders are bounded by interval enclosures (B-rep), exact signed-tetrahedron sums with compensated fixed-order reduction (Mesh), and adaptive octrees with two-sided bounds (Implicit); densities may be Fields. Distance runs branch-and-bound over both hierarchies, then Krawczyk on the optimality conditions. Signs for imperfect geometry come from generalized winding numbers on trimmed surfaces [Spainhour and Weiss 2025], accelerated by a hierarchical far-field expansion that turns some 10³-second direct evaluations into sub-second ones [Spainhour, Whitlock and Weiss 2026].

Assembly interference culls Instance pairs with exact integer GPU tests, computes certified distances on the CPU, and computes Boolean volumes only for overlapping pairs, in canonical Instance order; `repo`'s merge rule uses it. Thickness is `Certified`: the GPU locates candidate thin regions, and the CPU computes every canonical value.

### Services for Flux

Anvil implements Flux's `GeometryQuery` for every representation: certified box classification, closest points (Newton on f inside an interval-certified basin for implicits), quadrature, local thickness and region, shell and genus counts for Flux's surrogate-domain connectivity checks. Cut-cell quadrature for implicit and polynomial geometry follows Saye's height-function methods, which give positive weights and high-order accuracy [Algoim]; Algoim states no licence, so Anvil implements the papers. Moment fitting is used only with non-negative least squares and a conditioning check.

After a local edit, classification is recomputed only for octree cells whose boxes meet the region the edit's `HistoryRecord`s changed. Anvil's shares of Flux's 1 s interactive update are performance targets, measured on GP1, GP2 and GP5 in phase 0. `anvil::shape_velocity` returns `TopologyChange { parameter, entities }` instead of a velocity when a parameter changes B-rep topology, so gradients stay derivatives at a frozen discretization; until it ships in phase 2, UIX ranks edit plans by provenance.

### Constraint solving

MEC owns constraint semantics; Anvil runs `solve_constraints` and `analyze_constraints` as `Portable` operations on the canonical `linalg` crate. Each decomposed block uses dense rank-revealing QR or SVD, or above a size cap sparse QR followed by a rank-revealing pass on R.

When a converged block passes a Krawczyk test on the scaled system, the proven box radius is its `Guaranteed` bound and certifies a unique solution on the chosen branch. Otherwise the bound is `Estimated` (residual over an estimated smallest singular value), and a radius above the smallest entity tolerance fails with `IllConditioned { block, condition }`. Ranks are computed modulo 61-bit primes, where full rank certifies full rank over the rationals, and an exact rational kernel vector certifies a deficiency.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::mass_properties` | Volume, area, mass, centroid, inertia, each with a bound | — | ANV-O-MP-1 | 0 (meshes), 1 |
| `anvil::distance`, `closest_point` | Minimum or signed distance, witnesses with `EntityId` and (u, v) | `NotSeparated` when positive distance is required | ANV-O-DIST-1, ANV-O-DIST-2 | 0 (points), 1 |
| `anvil::interference` | Instances, clearance → separated, touching, clearance or overlapping pairs | `WorkLimit` | ANV-O-DIST-3 | 1 |
| `anvil::ray_cast` | Rays → first hits with `EntityId`, (u, v), normal | — | ANV-O-DIST-4 | 1 |
| `anvil::deviation` | Two Bodies → signed deviation Fields, Hausdorff bounds, volumes added and removed | `WorkLimit` | ANV-O-DIST-5 | 1 |
| `anvil::classify_points`, `classify_box`, `classify_body` | Inside, outside, on or cut, certified with tolerances | — | ANV-O-CLS-1 to ANV-O-CLS-3 | 0 (points), 1 |
| `GeometryQuery` | Classification, closest point, positive-weight quadrature, thickness, topology counts | `Uncertified { achieved }` | ANV-O-QUAD-1 | 1 |
| `anvil::shape_velocity` | Parameter → `Field<Faces, Displacement>` per unit change | `TopologyChange { parameter, entities }` | ANV-O-SV-1 | 2 |
| `anvil::curvature`, `analyze_continuity`, `isophotes` | Curvature Fields; G0 to G3 mismatch along edges with scale-relative default thresholds; isophote and reflection lines | `SingularPoint` | ANV-O-AN-1, ANV-O-AN-2 | 1 (G0 to G2), 2 (G3, isophotes) |
| `anvil::draft_analysis`, `draft_map` | Draft-angle Fields and classified regions; feasible draw directions | — | ANV-O-AN-3 | 1, 3 (`draft_map`) |
| `anvil::thickness` | `Sphere` or `Ray` thickness Field, certified minimum location; `Certified` grade | — | ANV-O-AN-4 | 1 |
| `anvil::medial_axis` | Planar regions → exact segment Voronoi skeleton; solids → certified approximation | `WorkLimit` | ANV-O-AN-5 | 1 (2D), 2 (3D) |
| `anvil::silhouette`, `project_hlr`, `visibility` | Silhouette curves; visible and hidden edges for drawings; visibility Fields | — | ANV-O-AN-6, ANV-O-AN-7 | 1 (silhouette, hidden lines), 2 |
| `anvil::tessellate` | Body, chordal tolerance → `DisplayPackage` (faces, edges with continuity, cluster pages, `(EntityId, u, v)` back-references) | `WorkLimit { triangles }` | ANV-O-TESS-1 | 1 |
| `anvil::tool_contact`, `swept_volume` | First contact of revolved tools; exact per-move envelopes for certified gouge distance; narrow-band stock | `WorkLimit` | ANV-O-MFG-1, ANV-O-MFG-2 | 2 |
| `anvil::offset_curve` | Planar or on-surface curves; lines and arcs stay lines and arcs | `Degenerate` | ANV-O-MFG-3 | 1 |
| `anvil::voxelize`, `correlate_grids` | Occupancy or distance grids; exact integer correlation counts (`Certified`) | `WorkLimit { voxels }` | ANV-O-VOX-1, ANV-O-VOX-2 | 1, 2 |
| `anvil::align`, `fit` | Point-to-plane alignment with deterministic samples; primitive, NURBS or cage fits with residuals | `NotConverged { rms }`, `FitFailed { residual }` | ANV-O-FIT-1, ANV-O-FIT-2 | 1 (primitives), 4 |
| `anvil::solve_constraints`, `analyze_constraints` | MEC's constraint systems → certified solutions, degrees of freedom, conflicts | `IllConditioned`, MEC's kinds | ANV-O-SOLVE-1 | 1 |

## Fidelity, performance and determinism

### Fidelity

| Fidelity | Anvil's behaviour | Cache |
| --- | --- | --- |
| `Preview` | Looser tolerances, surrogates (an implicit offset for a blend), GPU `f32` evaluation; results may show as `Proxy` | Never written to the shared cache |
| `Interactive` | `Portable` floating-point topology decisions and sampled seeding, validated by `check_body` (whose global separation catches missed intersections) and Krawczyk checks of traced points; a failed validation recomputes at `SignOff` | Cached; never consumed by `SignOff` checks or releases |
| `SignOff` | Certified decisions in rounds | Cached; required by releases and `SignOff` checks, and recomputed in the background after `Interactive` results |

Operations without uncertain decisions (analytic constructions, tessellation) map `Interactive` and `SignOff` to one effective fidelity.

**Decision D-ANV-28:** Anvil maps the three fidelities to surrogates, validated floating-point decisions and certified decisions. *Why:* certified SSI and round decisions cost time that drags and early-edit rebuilds cannot spend, while validation keeps `Interactive` Bodies valid and `SignOff` keeps releases certified. *Rejected:* certified decisions at every fidelity (misses the rebuild targets); unvalidated floating-point results (invalid Bodies reach dependents).

### Determinism

Contract 7.3 and PLT's mechanism table own the general rules. Anvil adds: canonical geometric orders everywhere (D-ANV-25); decision rounds against frozen tolerances (D-ANV-4); reductions only through `det_sum` and `exact_sum`; local work limits; no NaN at any boundary; and mesh modification in rounds of maximal independent sets whose priority hashes the element's geometric key and the round number, so results are identical for any thread count.

**Decision D-ANV-22:** Anvil parallelizes by data-defined decomposition with canonical merge order, fixed reduction trees and geometric independent-set priorities. *Why:* identical bits for any thread count without locks around floating-point state. *Rejected:* single-threaded certified mode (misses the rebuild targets); colouring or randomized schedules (results would follow thread count or seeds). (revised in round 2)

Within an operation, work splits by data (patch pairs, octree cells, faces), SIMD uses PLT's canonical lanes, and the GPU runs integer broad phases, preview tessellation and evaluation, the WGSL tape interpreter and `correlate_grids`, each with a registered CPU path.

### Performance targets

PLT owns contract 13.3's rows, measured on the reference laptop (Intel Core Ultra 7 258V, 8 cores, AVX2). Anvil's shares and operation targets:

| Workload | Target |
| --- | --- |
| Rebuild after an early edit, GP1-class prismatic benchmark (2 s row) | Anvil share ≤ 1.2 s at `SignOff`, since analytic pairs certify in closed form |
| ABC-derived 200-feature corpus (p90 10 s row) | Anvil share ≤ 7 s p90 at `Interactive`; `SignOff` recertification p90 ≤ 30 s (CCR-ANV-7) |
| Drag preview | Contract 13.3's 80 ms row: Anvil supplies cost estimates and `Preview` paths; later dependents show `Proxy` or `Stale` |
| Boolean of two 500-face analytic and NURBS bodies | ≤ 200 ms at `Interactive` |
| 50-edge constant-radius fillet chain | ≤ 500 ms at `Interactive` |
| Tessellation of a 10,000-face part at 0.01 mm chord | ≤ 200 ms |
| Interference of a 1,000-part assembly from warm cache | ≤ 1 s |
| Conforming tetrahedralization of 10⁶ elements | ≤ 10 s on 8 cores |
| Flux interactive update, Anvil stages | Rebuild ≤ 150 ms; classification and distance ≤ 200 ms |
| GP2 lattice sections at 50 µm, no global mesh | ≤ 60 s, peak memory ≤ 2 GiB |
| GP2 lattice mesh export at 2 × 10⁷ triangles | ≤ 60 s on the high band |
| Million-triangle mesh Boolean | Set by the phase 0 bake-off |

A phase 0 spike measures certified SSI and Boolean costs on ABC face pairs and publishes the 200-feature benchmark's operation mix and per-operation budgets before these targets freeze.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `Preview` fidelity | Surrogates and GPU evaluation; never in the shared cache | — | ANV-O-FID-1 | 1 |
| `Interactive` fidelity | Floating-point decisions validated after the fact | Validation failure recomputes at `SignOff` | ANV-O-FID-1 | 1 |
| `SignOff` recertification | Certified results replace `Interactive` ones in the background | — | ANV-O-FID-1 | 1 |
| Deterministic parallel scheduling | Identical bits for any thread count, ISA level and GPU presence | — | ANV-O-DET-1 | 0 |
| Performance budgets | The targets above, per merge batch | Regressions in deterministic work counts block merges | ANV-O-PERF-1 | 1 |

## State of the art

Figures in the last column are targets unless quoted.

| Area | Best published method | Leading implementation to beat | Crucible's choice (build, reuse or avoid) | How we measure |
| --- | --- | --- | --- | --- |
| Predicates | Adaptive expansions [Shewchuk 1997]; indirect predicates [Attene 2020] | Shewchuk's public-domain C; Geogram, BSD-3-Clause [Geogram repository] | Build in Rust (D-ANV-5); Geogram as oracle | Throughput within 1.2× of Shewchuk's C; exactness against rationals |
| Mesh Booleans | Local arrangements [EMBER 2022]; indirect-predicate arrangements [Cherchi et al. 2022]; exact Weiler model [Lévy 2024]; topological aggregation [trueform 2026] | Manifold, Apache 2.0 [Manifold repository]; EMBER's 1.6 ms geometric mean on 1,000 Thingi10K pairs | Bake-off (D-ANV-20); Manifold and Geogram as oracles, never linked | Thingi10K [Thingi10K 2016] pairs and thingiCSG: 100% valid; time per pair set by the bake-off |
| B-rep Booleans and tolerances | Imprint, join and select with local tolerances [Jackson 1995] | Parasolid, ACIS and CGM, with mixed polyhedral add-ons [ACIS Polyhedra; CGM Modeler]; OCCT 8.0, LGPL 2.1 with an exception [OCCT repository; OCCT 8.0] | Build (D-ANV-4, D-ANV-19); OCCT as differential oracle outside the core | ABC-derived pairs [ABC 2019] with coincident and tangent cases: success above OCCT 8.0, 100% valid |
| Surface–surface intersection | Topology-guaranteed SSI [Yang et al. 2023]; interval algebraic topology [Cheng et al. 2023] | ACIS, OCCT and SISL as compared by Yang et al. | D-ANV-16 | Hard-case families and ABC face pairs: correct topology on every case; ≤ 2× OCCT time on transversal pairs (deviation: certification cost) |
| GPU acceleration of SSI | GPU box hierarchies [Krishnamurthy et al. 2008]; thresholded sampling, patented [US12229885B1] | Zoo's engine (its application is open source; the engine is not stated to be) [Zoo Design Studio v1] | D-ANV-17 | Identical output with and without a GPU; ≥ 3× over the CPU path on ABC face pairs |
| Blends | Rolling-ball and setback vertex blends [Várady publication list] | Parasolid, ACIS, CGM; OCCT's fillet builder, which rejects contour ends where four or more edges meet [OCCT MakeFillet] | Staged program (D-ANV-29) | Re-fillet benchmark: 95% at phase 1, 97% at phase 2; OCCT on the same corpus |
| Implicit evaluation | GPU interval pruning [Keeter 2020]; Lipschitz pruning [Barbier et al. 2025]; affine range analysis [Sharp and Jacobson 2022] | Prospero: a NEON interpreter at 0.29 ms (M1 Air), Fidget 6.3 ms (M1 Max), MPR 3.9 ms (V100) [Prospero]; Fidget, MPL 2.0 [Fidget]; nTop, whose 5.0 kernel may regenerate geometry slightly differently [nTop whitepaper; nTop 5.0 notice] | D-ANV-11; Fidget and libfive (MPL 2.0 core, GPL Studio) [libfive repository] as benchmarks | Prospero 1024²: within 2× of 0.29 ms on comparable hardware, tape generation reported separately |
| Implicit meshing | Manifold dual contouring; occupancy-based dual contouring [Hwang and Sung 2024] | libfive; Fidget | Certified adaptive dual contouring | Hausdorff error against dense references; 100% manifold; ≤ libfive time at equal accuracy |
| Tetrahedral meshing | Conforming CDT [Diazzi et al. 2023]; envelope meshing [fTetWild 2020] | TetGen (378 failures of 4,408); fTetWild, MPL 2.0 [fTetWild repository]; Attene's CDT, GPL or LGPL [MarcoAttene/CDT] | Build both; port methods, never link GPL code | 4,408 valid Thingi10K models: 100% success; conforming stage within the published 4.3 s single-core mean |
| Curved and hex-dominant meshes | 3D Bézier guarding [Khanteimouri and Campen 2023]; bijective coarse meshes [Jiang et al. 2021]; field-guided agglomeration [Gao et al. 2017; hex survey 2022] | bichon, MIT with GPL CGAL dependencies [Jiang et al. 2021]; Gao et al.'s code [licence unverified] | Build | 100% positive Jacobian coefficients; boundary error; element count against bichon; hex fraction reported |
| Boundary layers | Semi-structured curvilinear layers [Marcon et al. 2019] | NekMesh [licence unverified] | Build | First-layer height within 5% on 95% of faces |
| Remeshing and decimation | Feature-line driven quad remeshing [Pietroni et al. 2021]; quadric error metrics [Garland and Heckbert] | The authors' published results; decimator not selected [unverified] | Build with verified bounds | ≤ 0.5% quad failures on Thingi10K; Hausdorff error at fixed budgets |
| Subdivision | Feature-adaptive limits [Nießner et al. 2012]; exact evaluation [Stam 1998] | OpenSubdiv [OpenSubdiv repository] | Build (D-ANV-13); OpenSubdiv as oracle | Limits within 10⁻¹² relative of OpenSubdiv |
| Containment and signed distance | Generalized winding numbers [Jacobson et al. 2013; Spainhour and Weiss 2025; Spainhour, Whitlock and Weiss 2026] | Axom, BSD [Spainhour and Weiss 2025] | Adopt all three, certified near the surface | Classification at ±τ/2 and ±2τ; time per query against Axom |
| Cut-cell quadrature | Saye's height-function quadrature [Algoim] | Algoim, licence not stated | Implement from the papers | Positive weights; exact on polynomials to the rule's degree |
| GPU NURBS evaluation | Elastic tessellation [ETER] | ETER, CUDA, 3.7 million patches at 30 fps | wgpu `f32` for previews and display | 10⁶ patches at 30 fps on the reference GPU (deviation: no tensor cores through wgpu) |
| Mesh repair and offsets | Arrangements with winding numbers [Jacobson et al. 2013; Cherchi et al. 2022]; mitered offsets [Cao et al. 2024] | Geogram [Lévy 2024]; methods Cao et al. compare | Build | Every Thingi10K model repaired valid; offset error, feature preservation |
| Persistent naming | Combined topology and geometry identification [persistent naming review 2018] | Commercial history-based systems [unverified] | D-ANV-14, D-ANV-15, D-ANV-25 | Zero silent re-selections (ANV-O-NAME-2); Git round trips (ANV-O-SITE-1) |
| Rust kernels | NURBS topology with Booleans [Truck repository] | Truck, Apache 2.0; Fornjot, archived 19 June 2026, "goals were never reached" [Fornjot repository] | Not adopted; Fornjot's lesson ties every capability to a golden product | — |
| Supporting crates | Correctly rounded math [correct rounding page]; arenas [slotmap docs]; intervals [inari docs] | CORE-MATH; `slotmap`, Zlib; `inari`, MIT | `detmath` (PLT); reuse `slotmap`; `inari` as reference (no cross-target identity stated) | Bit identity on every Tier 1 target |

**Decision D-ANV-23:** Anvil builds its kernel natively in Rust and links no external geometry kernel; OCCT, Manifold, Geogram, OpenSubdiv, fTetWild, libfive and Axom serve as differential oracles and benchmarks outside the core. *Why:* the core must be Rust, free of GPL linking, identical in native and Wasm builds and frozen per version, which C++ dependencies cannot guarantee; independent implementations catch errors that self-consistent tests miss. *Rejected:* wrapping OCCT (LGPL linking, C++ in Wasm, no control of numerics or naming); building on Truck (no cellular topology, per-entity tolerances or provenance).

## Platform notes

| Risk | Platforms | Decision |
| --- | --- | --- |
| Elementary functions differ between libraries | All | Only `detmath`; a lint bans Rust's `sin` and `exp`, whose precision the documentation calls non-deterministic [Rust f64 docs] |
| No hardware FMA at x86-64-v2, and none deterministic in Wasm | x86-64 baseline, browsers | Dekker splitting (always on wasm32), `mul_add` by ISA level elsewhere; identical error terms |
| Flush-to-zero set by a foreign library | Native | Operation entry asserts the IEEE default state; a violation is a typed internal error |
| Non-deterministic NaN bits [RFC 3514; Wasm nondeterminism] | All | Finiteness checked at every construction; the encoding rejects NaN and infinity |
| Relaxed SIMD may differ across platforms; Wasm 3.0 offers an optional deterministic profile [Wasm 3.0] | Browsers, Wasm components | Never emitted |
| Browser memory | Browsers | Contract 9's tiers: estimates above 512 MiB run in a heavy worker, larger ones remotely, with identical canonical results |
| No JIT for App Store apps | iPadOS | Wasm runs in WebKit with Pulley as fallback (contract 7.4); the interpreter-first tape design needs no JIT |
| WebGPU missing or limited | Some Linux and Firefox configurations | Every GPU path has a CPU path |
| GPU driver variance and timeout resets | All GPUs, Windows | GPU results never canonical; known-answer tests per pipeline (contract 7.3); chunked dispatches; device loss is an Abort and reruns on the CPU |
| Tier 1 preview targets in phase 1 | Windows ARM64, Linux ARM64, Safari, Firefox | Same canonical bits, verified by the determinism suite before general availability |

## Interfaces with other subsystems

### Anvil provides

| To | What | Types |
| --- | --- | --- |
| Ingot and std | Operations with versions, role vocabularies and per-parameter `Query` use; `anvil::resolve` with ranked, compiling fixes; tangent rules and `shape_velocity`; `check_body` | `Body`, `EntityId`, `HistoryRecord`, `ResolveError`, `OpError` |
| Kiln | `OpImpl`s with grades, effective-fidelity maps, cost estimates and two-stage keys; `GeometryId` and `ObjectId`; `Failure` values only, never Aborts | `OpKey` inputs, `GeometryId`, `ObjectId` |
| `repo` | Interference and regional deviation for the merge rule; `GeometryId`s for revision identity | `Body`, `EntityId` |
| Flux | `GeometryQuery` with positive-weight quadrature; `mid_surface`, `member_axes`, lattice strut graphs; meshing and adaptation operations; `shape_velocity`; `implicit_from_field`; `common_refinement`; display tessellation with back-references | `Body`, `Field`, `FaceBound` |
| MEC | The operations catalog and phases in the capability tables, copied verbatim; blend targets of D-ANV-29; the constraint solver; per-entity tolerances | `Body`, `EntityId`, `Field` |
| MFG | Sections, offsets, tool contact, per-move envelopes, distance, interference, deform, visibility, voxels, grid correlation, toolpath wire Bodies | `Body`, `Field` |
| ELX | `anvil-planar` operations, `fold` for flex circuits, convex decomposition | `Body` |
| UIX | `DisplayPackage`; the WGSL tape interpreter for implicits during edits; control-vertex previews; exact measures, sections, silhouettes, ray casts | `DisplayPackage`, `Body` |
| AGT and `api` | Entity inspection with provenance; fixes; geometry diffs (volumes added and removed, Hausdorff deviation) | `EntityId`, `ResolveError` |
| ECO and `io/` | Builders, healing within the CAx-IF corpus in phase 1, the imported-id rule (D-ANV-31) and `import_map`, the topology normal form and `exchange_form`, tessellation for 3MF, including beam lattices [3MF beam lattice repository; 3MF beam lattice spec] | `Body`, `ErrorBound` |
| PLT | Per operation: grade, GPU paths with their roles, cross-class agreement and determinism-suite corpora | `DeterminismGrade` |

Canonical names for names used in round 1 (contract 7.1 makes this catalog canonical):

- MEC: `section_body` → `section`; `extend_face` → `extend`; `implicit_from_brep`, `brep_from_implicit`, `subd_to_brep` → `convert`; `fit_nurbs`, `fit_primitive` → `fit`; `icp` → `align`; `thickness_ray` → `thickness` with `method: Ray`; `sample_surface` → `sample`; `evaluate_curve` → `evaluate`; `approximate_curve`, `approximate_surface` → `approximate`; `offset_body` → `offset`; `draft_faces` → `draft`; `delete_face`, `replace_face` → `delete_faces`, `replace_faces`; `helix` → `curve` with `Helix`.
- MFG: `slice` → `section`; `offset_curves_2d` → `offset_curve`; `medial_axis_2d` → `medial_axis`; `extend_surface` → `extend`; `tool_drop`, `tool_push` → `tool_contact`; `collide` → `interference`.
- ELX: `planar_boolean`, `planar_offset` → `planar::boolean`, `planar::offset`; the proposed flex bend operation → `fold`.

### Anvil requires

| From | What |
| --- | --- |
| PLT | `detmath`, canonical `simd` lanes, `det_sum` and `exact_sum`, `gpu` with registered CPU paths and known-answer tests, `linalg`, toolchain archiving for frozen versions |
| Kiln | Two-stage keys, effective fidelity in keys, Aborts never cached, `Preview` results outside the shared cache, `rng` streams keyed without names |
| Flux | The `field` crate below Anvil; `Sampler`s with per-sample error and gradient bounds; the filtered, projected density for extraction; the shell and beam criterion that marks regions |
| Ingot | Text-derived `OpSite`s; `QueryPlan`s; named sub-entities of sketch helpers (`rect` gives `left`, `right`, `bottom`, `top`); `InputSensitivity` records; the `Truth` rule |
| MEC | Feature role vocabularies and `FeatureRole` attributes; constraint semantics; glyph outlines from `text` |

## Oracles

Oracles live in the protected `oracles/anvil/` directory. Held-out ABC and Thingi10K subsets, chosen by a fixed hash rule, stay outside the agent-readable tree.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| ANV-O-DET-1 | Determinism | The corpus at 1, 2, 7 and 64 threads, on forced x86-64 v2, v3 and v4, ARM64 and wasm32, with and without a GPU, gives identical output hashes |
| ANV-O-DET-2 | Order-free tolerance rounds | Chains of three or more entities spaced at τ ± ρ/2⁹, with shuffled pair orders and 1 to 64 threads, give identical bits |
| ANV-O-LABEL-1 | Label invariance | Golden products rebuilt with re-randomized `EntityId`s and `OpSite`s give identical `GeometryId`s and check values |
| ANV-O-SITE-1 | Text-derived names | Golden products exported to Git, re-imported and rebuilt keep every `EntityId` |
| ANV-O-CACHE-1 | Cross-design sharing | Two designs that build the same geometry at different sites share every geometric-stage entry along a 20-operation chain |
| ANV-O-SCALE-1 | Scale invariance | Bodies framed at the origin and scaled by 2⁻²⁰ to 2²⁰ give the scaled outputs bit for bit |
| ANV-O-PRED-1 | Predicates | 10⁸ random and near-degenerate cases give the signs of rational arithmetic |
| ANV-O-TOL-1 | Decision rule | Coincident, near-coincident and tangent pairs at τ/2, τ and 2τ give the specified decisions and recorded growth |
| ANV-O-VALID-1 | Body checker | Every planted violation of the four conditions is reported; valid Bodies give no report |
| ANV-O-VALID-2 | Global separation | Planted far-field clashes in `offset_faces`, `move_faces`, `draft`, `shell`, `thicken` and `blend` corpora all fail with `SelfIntersecting` |
| ANV-O-VER-1 | Frozen versions | Frozen module hashes are unchanged; every version's golden output hashes, retired ones from archived Wasm builds, reproduce after toolchain and `detmath` upgrades |
| ANV-O-ENC-1 | Encoding | Binary and text round trips are bit-identical; every past major version decodes; decode(encode(v)) = v for every operation output, signed zeros included |
| ANV-O-ENC-2 | Minor-version invariance | Golden-corpus identities are unchanged across minor encoding releases |
| ANV-O-GEOM-1 to ANV-O-GEOM-3 | Evaluation, sampling, approximation | Closed forms for analytic geometry and exact rational NURBS evaluation agree; samples are deterministic and cover; certified deviation stays within the request |
| ANV-O-LAW-1 | Law curves and surfaces | Interval enclosures contain dense samples; evaluation equals the kernel IR reference |
| ANV-O-PROC-1 | Procedural nesting | Flattened constructions stay within propagated bounds; cost on blend-heavy ABC parts is reported |
| ANV-O-NF-1 | Topology normal form | An `exchange_form` re-imported keeps analytic and NURBS geometry bit-identical, procedural geometry within its stored bound and topology equal in normal form |
| ANV-O-HEAL-1 | Sewing | Exploded solids re-sew exactly; ABC STEP files close, with free edges reported |
| ANV-O-HEAL-2 | Healing | Healed CAx-IF and ABC imports pass `check_body` within the reported deviation |
| ANV-O-NAME-1 | History | Coverage, kind, soundness and canonical order hold on every operation of the corpus, transient pieces included |
| ANV-O-NAME-2 | Query stability | Over full declared ranges, endpoints included, and ±10%, every golden-product query resolves to the same lineage, raises a typed error or reports `RankSwap`; zero silent re-selections |
| ANV-O-NAME-3 | Worked example | The worked example runs with the stated records, errors and fixes |
| ANV-O-NAME-4 | Imported names | Supplier re-exports keep ids where persistent ids exist; edited ABC copies re-exported through STEP match their ground-truth pairs |
| ANV-O-NAME-5 | Fixes | Every `Fix` on the golden products and the `ResolveError` corpus compiles, resolves and matches its description |
| ANV-O-COPY-1 | Copies | `half + mirror(half, plane.yz)` and two-Instance features give distinct ids; queries on the seed resolve to the seed only |
| ANV-O-SSI-1 to ANV-O-SSI-3 | Surface intersection | Closed-form quadric and NURBS–analytic pairs exact in branch count and topology; Yang et al.'s and Cheng et al.'s hard-case families topologically correct and stable under perturbations below τ; general ABC face pairs equal a high-precision reference |
| ANV-O-CONTACT-1 | Tangential contact | Fillet on fillet, cylinder on plane, sphere in cylinder and a blend face cut through its contact curve each give one tangential edge and no spurious coincidence region |
| ANV-O-BOOL-1 to ANV-O-BOOL-6 | Booleans, split, imprint | Algebraic identities and inclusion–exclusion within bounds; Manifold's three cases; Thingi10K and thingiCSG pairs 100% valid with exact reference volumes; ABC B-rep pairs differential against OCCT 8.0; split pieces sum to the input; imprint keeps volume and area |
| ANV-O-TRIM-1, ANV-O-TRIM-2 | Trim, extend | Kept sides as specified; continuity at extended edges |
| ANV-O-XF-1 | Transforms | Round trips within 8 ulp of the largest coordinate; exact for frame-grid translations and axis permutations |
| ANV-O-PAT-1, ANV-O-PAT-2 | Patterns | Copy counts, keys and placements; a circular pattern of holes in a cylinder with reuse equals the unreused result within the reported bound |
| ANV-O-HULL-1 | Hulls, Minkowski sums, decompositions | Hulls equal exact rational hulls; convex sums equal closed forms; decomposed parts are convex and their union lies within the bound |
| ANV-O-BLEND-1 to ANV-O-BLEND-4 | Blend geometry | Closed-form blends on planes, cylinders and cones; spines at distance r within τ; G1 and G2 continuity; volume change on straight edges |
| ANV-O-BLEND-5 | Blend benchmark | The re-fillet benchmark meets 95% on stage-1 configurations at phase 1 and 97% on all configurations at phase 2 |
| ANV-O-BLEND-6 | Blend regrowth | Edits next to blends rebuild them with the same parameters and ids, or fail with `BlendRegrowFailed` |
| ANV-O-OFF-1 to ANV-O-OFF-4 | Offsets, shells, thickening, shrinkwrap | Exact offsets of spheres, cylinders, tori and boxes at Hausdorff distance \|d\|; shelled volumes exact; skins within g |
| ANV-O-DRAFT-1 | Draft | Drafted faces measure the requested angle within 10⁻⁹ rad |
| ANV-O-DE-1 to ANV-O-DE-3, ANV-O-REC-1, ANV-O-REC-2 | Direct edits, recognition | Volume identities after moves and deletions; removed aspects' volumes; labelled ABC aspects with precision ≥ 0.98 on holes and fillets |
| ANV-O-OP-1 to ANV-O-OP-8 | Construction | Closed-form volumes, areas and centroids of primitives, prisms, Pappus solids and springs; region areas; interpolated sections; network continuity |
| ANV-O-MID-1, ANV-O-AXIS-1 | Dimensional reduction | Known mid-surfaces and thickness Fields of plates and sheet metal; axes, areas and second moments of rectangular, tube and I sections; strut graphs equal generator graphs |
| ANV-O-SEC-1, ANV-O-PROJ-1, ANV-O-PROJ-2, ANV-O-PAR-1, ANV-O-SM-1, ANV-O-DRAPE-1 | Sections, projection, wrap, flattening, folding, draping | Section areas against integrals; lengths kept on developable targets; angle distortion within the reference; fold of unfold within τ; hemisphere drapes against published shear patterns |
| ANV-O-DEF-1, ANV-O-DEF-2 | Deform, morph | Rigid Fields reproduce `transform`; deviation within bounds |
| ANV-O-IMP-1 to ANV-O-IMP-4 | Implicits | Enclosures contain samples; Lipschitz bounds hold on random segments; pruned tapes equal full tapes per region; analytic iso-surfaces within the bound |
| ANV-O-LAT-1 | Lattices | Volume fractions against closed forms or high-resolution references; certified minimum thickness |
| ANV-O-LEAF-1 | Leaf preservation | In a B-rep joined with a lattice, kept faces carry their ids, attributes and PMI, and conversion keeps them exact |
| ANV-O-MESH-1 to ANV-O-MESH-4 | Meshes | Builders reject non-manifold data; every Thingi10K model repairs valid with winding-number volumes; labelled segmentations; overlay areas sum to each side's |
| ANV-O-TET-1, ANV-O-HO-1 | Tetrahedra, curved elements | The 4,408 valid Thingi10K models mesh without inverted elements, conforming or within the envelope; every Jacobian Bernstein coefficient positive |
| ANV-O-HEX-1, ANV-O-BL-1 | Hex-dominant meshes, boundary layers | Valid and conforming; first-layer heights within 5% on 95% of faces |
| ANV-O-ADAPT-1, ANV-O-POLY-1 | Adaptation, polyhedral meshes | Positive Jacobians, edge lengths within the metric band, volume-conserving parent maps; closed cells with positive volumes and zero face-area sums |
| ANV-O-REM-1 | Remesh, decimate, smooth | Reported Hausdorff bounds hold under certified measurement |
| ANV-O-SUBD-1 | Subdivision | Limits within 10⁻¹² relative of OpenSubdiv; regular cages equal bicubic B-splines; recorded crease bounds hold |
| ANV-O-PLANAR-1, ANV-O-PLANAR-2 | Planar geometry | Predicates and distances equal rational references; every derived fill in the design-rule corpus passes the exact checker with zero tolerance |
| ANV-O-CONV-1, ANV-O-CONV-2 | Conversions, propagation | Every reported bound holds under independent certified measurement; supports perturbed within their bounds keep derived faces within propagated bounds, near-tangent blends included |
| ANV-O-MP-1 | Mass properties | Closed forms; agreement across representations within bounds |
| ANV-O-DIST-1 to ANV-O-DIST-5 | Distance, interference, ray casts, deviation | Closed forms for analytic pairs; overlap volumes equal Boolean volumes; offset copies deviate by exactly the offset |
| ANV-O-CLS-1 to ANV-O-CLS-3 | Classification | Correct at ±τ/2 and ±2τ; agreement across representations |
| ANV-O-QUAD-1 | Simulation queries | Quadrature weights positive and exact on polynomials to the rule's degree; implicit closest points converge inside certified basins |
| ANV-O-AN-1 to ANV-O-AN-7 | Analyses | Closed-form curvature, continuity, draft, thickness, medial axes, silhouettes and visibility |
| ANV-O-SV-1 | `shape_velocity` | Finite differences agree within the step error; topology changes return `TopologyChange` |
| ANV-O-TESS-1 | Tessellation | Certified chord bounds; watertight; face groups carry source ids |
| ANV-O-MFG-1 to ANV-O-MFG-3, ANV-O-VOX-1, ANV-O-VOX-2, ANV-O-FIT-1, ANV-O-FIT-2 | Manufacturing geometry, voxels, fitting | Cutters against analytic surfaces; planted gouges found by per-move distance; swept spheres and cylinders exact; voxel volumes converge at first order; correlation equals direct integer correlation; known transforms and primitives recovered |
| ANV-O-SOLVE-1 | Constraint solving | Blocks of 100 to 2,000 unknowns with known rank deficiencies diagnosed exactly; Krawczyk boxes contain reference solutions |
| ANV-O-FID-1 | Fidelity | Every `Interactive` result passes `check_body`; differing `SignOff` decisions lie within ambiguity bands; `Preview` results never reach the shared cache |
| ANV-O-FUZZ-1 | Random use | Property-based operation sequences give valid, deterministic results or typed errors; failures are minimized into the corpus |
| ANV-O-PERF-1 | Performance | Target benchmarks run per merge batch; work-count regressions block merges; wall-clock regressions above 10% go to review |

## Phasing

Gate contributions follow contract 13; the operation-to-phase detail is in the capability tables.

| Phase | Anvil's contribution to the gate |
| --- | --- |
| 0 | Predicates, analytic geometry, topology, `EntityId` and the encoding by month 6 (contract 13.2); Anvil's corpus green in the determinism suite (ANV-O-DET-1, ANV-O-SCALE-1, ANV-O-PRED-1, ANV-O-VER-1, ANV-O-ENC-1, ANV-O-LABEL-1, ANV-O-SITE-1); freedom-to-operate review commissioned; re-fillet benchmark built; mesh Boolean bake-off and certified SSI and Boolean cost spike run before targets freeze |
| 1 | Chain A for GP1: analytic and NURBS–analytic SSI and Booleans, tessellation and `DisplayPackage` (months 6 to 12), then stage 1 blends, chamfers, shells, holes, patterns, hidden lines and `exchange_form` for STEP AP242 (months 12 to 24). Chain B for GP2: implicit tapes on kernel IR v0, lattices from Flux Fields, leaf-preserving conversion, mesh and beam-lattice output for 3MF. Blend benchmark at 95% on stage 1. SSI stays a release risk until counsel's opinion arrives |
| 2 | GP3 and GP4: general NURBS SSI, free-form offsets, stage 2 blends, direct edits, recognition, mid-surfaces and member axes for frames and guards, sheet-metal unfolding, conforming tetrahedra with curved elements for contact, tool contact and per-move envelopes for machining, SubD, import matching; blend benchmark at 97% |
| 3 | GP5: corners of valence four and above, envelope meshing and guarding, adaptation and polyhedral meshes, `anvil-planar` for the board, draft maps, G3 surfaces, general wrap |
| 4 | GP6: G3 blend sections, hex-dominant meshes and boundary layers for airflow, scan fitting, common refinement, kinematic draping |
| 5 to 7 | GP7 masks and process emulation with `anvil-planar`, implicit and cellular operations; member axes for GP8 and GP14; block-structured hull meshing for GP13; flattening for GP16 |

## Open questions

1. **Retention cost.** D-ANV-18 keeps every version executable, natively for at least five years and then as archived Wasm builds; PLT and Kiln must confirm the CI cost.
2. **Freedom to operate.** Counsel's opinion on claims 1, 6, 11 and 16 of US 12,229,885 B1 and any continuations, for both paths, is pending; other GPU geometry patents were not searched.
3. **Resolution default.** Phase 0 measures tolerance growth on ABC imports at 2⁻²⁶, 2⁻³⁰ and 2⁻³⁴ of the diagonal before 2⁻³⁰ freezes.
4. **Mesh Boolean method.** The bake-off result and trueform's licence decide D-ANV-20's implementation.
5. **WGSL accuracy.** Until PLT verifies WGSL's error bounds, GPU intervals serve previews only.
6. **Fitted implicit-to-B-rep faces** have no verified guarantee; facet faces are the fallback until phase 3.
7. **Unverified licences.** Gao et al.'s hex-dominant code, NekMesh and Algoim; Anvil implements the published methods either way.
8. **R2-36, applied in part.** The implicit fallback states its deviation per instance by certified measurement, not as a closed form in r, since the smooth union's departure from a circular section depends on the dihedral angle.
9. **R1-16, applied in part.** Anvil states its two stage budgets; the other stages, and morphing versus `Proxy` for geometric drags, are Flux's.
10. **R6-32, applied in part.** Direct slicing is MFG's, whose slicer arrives in phase 2; Anvil keeps the section-stack target.
11. **Owned elsewhere.** R2-09 item 5 and R2-26's text layout belong to MEC; shared findings R1-02, R1-18, R1-19, R1-35, R1-38, R1-57, R2-15, R2-44 and R6-42 are applied to Anvil's part and left to the owning tabs otherwise.

## Contract change requests

- **CCR-ANV-7. Fidelity of the rebuild rows.** In contract 13.3, rename "Exact rebuild after an early edit" to "Rebuild after an early edit", state the GP1-class 2 s row at `SignOff` and the corpus p90 10 s row at `Interactive`, and add a `SignOff` recertification row (p90 ≤ 30 s, target). *Reason:* "exact" is not a fidelity name, and certified decisions on general NURBS cost more than an interactive rebuild can spend (R2-09).
- **CCR-ANV-8. `Unknown` bounds.** In contract 5 (`Body`), replace "become `Unknown`" with "become `NotQuantified`". *Reason:* one name per concept; `Component` already defines `NotQuantified { reason }`.

## Sources

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
| OCCT MakeFillet | [OCCT reference, BRepFilletAPI_MakeFillet](https://occt3d.com/dev/doc/refman/html/class_b_rep_fillet_a_p_i___make_fillet.html) |
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
| Algoim | [Algoim, high-order quadrature and closest points for implicitly defined geometry](https://algoim.github.io/) |
| CAx-IF PMI 4.1 | [CAx-IF Recommended Practices for PMI (AP242), version 4.1, 20 June 2024](https://www.mbx-if.org/home/wp-content/uploads/2024/06/rec_pracs_pmi_v41.pdf) |
| OpenSCAD cheat sheet | [OpenSCAD cheat sheet](https://openscad.org/cheatsheet/) |
| RFC 3514 | [Rust RFC 3514, float semantics](https://rust-lang.github.io/rfcs/3514-float-semantics.html) |
| Rust f64 docs | [Rust `f64` documentation](https://doc.rust-lang.org/std/primitive.f64.html) |
| Rust 1.86.0 release | [Rust 1.86.0 stabilized APIs, releases.rs](https://releases.rs/docs/1.86.0/) |
| correct rounding page | [Correct rounding of elementary functions in IEEE 754 formats](https://reliable-computing.org/correctrounding.html) |
| Wasm 3.0 | [WebAssembly 3.0 announcement](https://webassembly.org/news/2025-09-17-wasm-3.0) |
| Wasm nondeterminism | [WebAssembly nondeterminism](https://www.webassembly.org/docs/nondeterminism/) |
| WGSL | [WGSL specification](https://www.w3.org/TR/WGSL/) |
| slotmap docs | [slotmap documentation](https://docs.rs/slotmap/latest/slotmap/) |
| inari docs | [inari documentation](https://docs.rs/inari/latest/inari/) |
| 3MF beam lattice repository | [3MF Beam Lattice extension repository](https://github.com/3MFConsortium/spec_beamlattice) |
| 3MF beam lattice spec | [3MF Beam Lattice Extension specification 1.2.0](https://github.com/3MFConsortium/spec_beamlattice/blob/master/3MF%20Beam%20Lattice%20Extension.md) |
