# Anvil geometry kernel (ANV)

Anvil is Crucible's geometry kernel: one `Body` type holds exact boundary-representation (B-rep), implicit, mesh and subdivision geometry, and mixing them never silently approximates. Where other kernels settle near-coincidences with one global tolerance and a best guess, Anvil proves each topological decision or says that it cannot, so a part rebuilds with the same faces, names and bits on every machine. Every operation is versioned and returns the history that keeps face and edge names stable when dimensions change.

## One Body, four representations

This section shows the model a designer or agent meets when Anvil runs their features, before any rule is stated in full.

### A worked example: filleting the bracket

The canonical bracket (contract 6) ends its geometry with two lines:

```
let body = base + web
let solid = body |> fillet(body.edges(new), 2mm)
```

`base + web` is a Boolean union of two extruded solids. Its result, `body`, is a `Body`: an immutable value that holds the geometry in one representation. Here that is a B-rep, the faces, edges and vertices of the part's boundary with their exact surfaces and curves. `body.edges(new)` is a query: the edges the union created, where the web meets the plate. `fillet` calls `anvil::blend` on those edges with a 2 mm radius.

Anvil builds each fillet the way a rolling ball would. It offsets the two faces that meet at the edge by 2 mm and intersects the offsets to get the ball's centre line, the spine. Projecting the spine back onto the faces gives the two contact curves. Between them it places a rolling-ball surface, here a cylinder. Each contact edge receives a certificate that the fillet meets its face with tangent continuity, so no later operation has to rediscover that tangency numerically.

Every new face gets a name, its `EntityId`. A fillet face's name hashes four things: that it is a face, the source position of the `fillet` call, its role `blend`, and the name of the edge it rounds. That edge's name in turn hashes the union's source position, its role and the names of the two faces it joins. No dimension enters any name.

When an engineer changes `width` from 60 mm to 80 mm, every face moves and every name stays. The stress check's clamp face, the PMI (product and manufacturing information: the dimensions and tolerances on the model) and the drawing's balloons all still point at the right geometry. If the change splits or deletes a face a query relies on, the query fails with a typed error and fixes that compile, and never quietly picks another face.

Every decision behind the result is certified. The bracket's diagonal is about 77 mm, so its resolution ρ, the length below which Anvil treats two points as one, is 2⁻³³ m, about 0.12 nm.

Now suppose a later hole is placed so that it almost grazes the fillet, leaving a gap of a few hundredths of a nanometre. Anvil computes an enclosure, an interval guaranteed to contain the true gap, and compares it with the tolerances of the two faces.

If the enclosure lies inside them, the hole touches the fillet along a recorded edge. If it lies outside, they are separate. If it straddles the tolerance even after refinement, Anvil either merges them with a recorded, capped tolerance growth or fails with `Ambiguous { entities, enclosure }`. It never guesses, so the same source produces the same faces on a laptop, in a browser and on the build farm.

While an engineer drags `width`, the fillet is computed at `Interactive` fidelity, the fast setting with stated error. Releasing the drag demands `SignOff`, the setting that release checks use. Anvil does not compute the fillet again: a certification step confirms the result it already has, bit for bit, and only a failed confirmation recomputes.

### The Body value

A `Body` holds its representation, a frame, its resolution ρ, regions and metadata with per-face and per-edge error bounds. The frame is a translation on a fixed 2⁻²⁰ m grid; rotations belong to Instance placements. Regions are `Material`, `Void` or `Exterior`. Parts, not Bodies, carry item numbers and names.

| Representation | Exact content | Typical sources |
| --- | --- | --- |
| `BRep` | Analytic, NURBS (non-uniform rational B-spline), procedural and facet faces; cellular topology with regions | Features, STEP, conversions |
| `Implicit` | A function whose negative region is the solid; exact faces of B-rep leaves that remain on the boundary | Lattices, topology optimization, field-driven design |
| `Mesh` | Manifold triangle topology with precision ε; vertex-only point sets | Scans, printing, tessellation |
| `SubD` | Catmull-Clark subdivision cage with semi-sharp creases, G1 at extraordinary vertices | Industrial design |

### Representation lattice

Three inclusions lose no geometry. A Mesh is a B-rep with facet faces, as in Parasolid's Convergent Modeling [Parasolid convergent modeling]. A SubD is a B-rep with subdivision-limit faces, exact except near extraordinary vertices that carry semi-sharp creases, where the conversion records a certified bound.

A B-rep or Mesh is an implicit leaf: its exact signed distance, signed by generalized winding numbers [Jacobson et al. 2013]. A mixed operation returns the join of its operands. The join keeps each B-rep leaf's exact faces that stay on the boundary, with their `EntityId`s and attributes.

Queries, PMI and drawings use those faces directly, and `convert(into: BRep)` keeps them exact. GP2, the printed lattice bracket that closes phase 1, thus keeps its mounting holes' `HoleSpec` and semantic PMI. CAx Implementor Forum (CAx-IF) practice allows those only on exact geometry [CAx-IF PMI 4.1].

**Decision D-ANV-2:** Mixed operations return the least representation in the lattice Mesh ⊂ BRep, SubD ⊂ BRep, BRep ⊂ Implicit that holds both operands, and never approximate geometry or drop B-rep faces that remain on the boundary.
*Why:* exact faces keep their names and attributes, and later conversions are explicit and bounded.
*Rejected:* meshing first, which destroys exact faces; a plain implicit result, which loses faces, names and PMI; refusing mixed operations.

[[DIAGRAM diagrams/02-anvil-representation-lattice.jsx: representation lattice · 4 representations, 3 inclusions]]

Read the diagram from the bottom up. A solid arrow is a lossless inclusion into a containing representation; a dashed arrow is a conversion back down that records bounds.

### Kernel rules

Eight rules hold for every operation; later sections give the detail.

1. **Bodies are immutable values**, and unchanged storage is shared between them.
2. **Operations are pure and label-invariant:** results depend on arguments, input geometry and the operation version, never on clocks, randomness, thread order or names.
3. **Work limits are arguments** with per-version defaults. Reaching one is the `Failure` `kiln/work_limit { kind, limit }`, written `WorkLimit` in this tab's tables. Reaching the declared memory maximum is `kiln/memory_limit`. Either carries any best-so-far result beside it (contract 7.2). Cancellation and host memory exhaustion below that maximum are Aborts.
4. **Topological decisions are certified** at every fidelity, by exact predicates or certified enclosures ("Numbers, tolerances and decisions").
5. **Approximations state their error** as per-face and per-edge bounds ("Conversions, exchange and error propagation").
6. **The GPU orders work and previews,** and prunes only by exact integer tests; results are identical without it.
7. **No silent fallbacks:** a fallback runs only on request and says so.
8. **Each geometric question is decided once,** and its answer is reused until a tolerance it depends on grows.

### The operation contract

Every operation implements KLN's operation contract (`OpImpl`, returning `OpResult<T>`) with determinism grade `Portable`, except `thickness` and `correlate_grids`, which are `Certified` (their GPU candidates never change the result).

| Element | Contract |
| --- | --- |
| Inputs | Bodies; plain values with units converted by Ingot; `Query` resolutions with a declared use (`Surface` or `Extent`); Fields with a requested accuracy |
| Outputs | Bodies or values, `HistoryRecord`s, bounds and `Note`s, canonical at the boundary: −0.0 becomes +0.0 and no value is non-finite |
| Stages | Entity-naming operations run a geometric stage and a relabeling stage, for results, failures and notes alike ("Identities and encoding") |
| Failures | `OpError { kind, why, fixes, at, partial }` becomes a cached, catchable `Failure` with code `anvil/<kind>`; `partial` is a diagnostic Body. Anvil's kind names are canonical, and MEC's `FeatureError` uses them plus the feature-level kinds MEC lists |
| Fidelity | Each version maps `Preview`, `Interactive` and `SignOff` to its effective fidelity |
| Validity | Created and modified entities and their neighbours are checked for incidence, combinatorics and regularity. Separation is checked against the whole Body by a broad phase in O(m log n + k) for m entities and k pairs, cone and distance-bound exclusion, then certified distance |

A Body that violates a validity condition never leaves an operation: the operation fails with the violation instead. `anvil::check_body` runs the same checks on any Body, so a test or an import can ask for every violation at once.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::check_body` | Body → every violation of the four validity conditions | None: it reports violations as its value | ANV-O-VALID-1 | 0 |
| Global separation check | Changed entities against the whole Body | `SelfIntersecting { faces, at }`; `WorkLimit { kind: Pairs }` | ANV-O-VALID-2, ANV-O-PERF-1 | 0 |
| Canonical outputs | decode(encode(v)) = v for every output | `Internal::NonCanonical`, a defect report | ANV-O-ENC-1 | 0 |
| Robustness under random use | Property-based operation sequences with near-degenerate placements | Failures minimized into the corpus | ANV-O-FUZZ-1 | 0 |
| Typed failures shared with features | `OpError` kinds are canonical; `FeatureError` kinds of std features equal them plus MEC's feature-level kinds | A kind outside both lists fails the oracle | ANV-O-NAME-7 | 1 |
| Leaf-preserving implicit faces | Exact faces of B-rep leaves kept with ids and attributes | `Ambiguous { faces }` near tangency | ANV-O-LEAF-1 | 1 |

## Numbers, tolerances and decisions

Anvil turns floating-point geometry into consistent topology; this section states the numbers it uses and the one rule that decides every topological question. It computes in metres and radians with `f64`, error-free expansions, intervals, affine forms, integers and modular arithmetic.

### Resolution, frames and scale

Every Body has a resolution ρ, the smallest length it distinguishes, where D is its box diagonal in metres:

```latex
\rho(D) = 2^{\lceil \log_2 D \rceil - 30}
```

Coordinates are frame-relative, so above 2 µm ρ is at least 2²³ times the local `f64` spacing, headroom that constructions may consume. With no length constant besides the frame grid, a Body at the origin behaves identically under power-of-two scaling.

A result takes ρ(D) of its own diagonal, so a large tool never coarsens a part. An entity keeps a tolerance τ stored by growth or healing; an entity at its source's default takes the result's ρ. Bit-identical geometry therefore has one `GeometryId` however large the tools that produced it; geometry equal within tolerance is compared by `anvil::deviation`.

ρ doubles when D crosses a power of two, as at diagonals of 62.5, 125 and 250 mm in the canonical bracket's `width` range. A design may pin `resolution:` per Part for sweeps and optimization, down to 2^(⌈log₂ D⌉ − 40). A pin more than a factor 2 from ρ(D) reports `Note::ResolutionStep`.

| Body | D | Default ρ | Growth cap τ_cap = 2¹⁰ρ |
| --- | --- | --- | --- |
| MEMS accelerometer die | 0.5 mm | 2⁻⁴⁰ m ≈ 0.91 pm | ≈ 0.93 nm |
| Machined bracket (GP1) | 0.1 m | 2⁻³³ m ≈ 0.12 nm | ≈ 0.12 µm |
| Drone (GP6) | 1 m | 2⁻³⁰ m ≈ 0.93 nm | ≈ 0.95 µm |
| Ship hull | 300 m | 2⁻²¹ m ≈ 0.48 µm | ≈ 0.49 mm |

Frame offsets are multiples of 2⁻²⁰ m, so frame differences are exact below 2³² m. Between Instances, decisions use the finer frame and max(ρ_a, ρ_b) and report `Note::ResolutionCoarsened`.

**Decision D-ANV-3:** Resolution is 2⁻³⁰ of the result's diagonal, rounded to a power of two and pinnable per Part, on a 2⁻²⁰ m frame grid; the exponent is frozen now, and licence-filtered ABC imports in phase 0 set the growth cap's exponent and the healing default.
*Why:* a fixed value such as Parasolid's 1995 default of about 5·10⁻⁹ m [Jackson 1995] is coarse for MEMS and wasteful for ships.
*Rejected:* a global tolerance; the exact diagonal, which changes with every edit; the coarsest input's ρ, which lets tools coarsen parts.

### Per-entity tolerances

Each vertex, edge and face carries a tolerance τ ≥ ρ, stored when it differs from ρ. As in Parasolid [Jackson 1995], τ(vertex) ≥ τ(edge) ≥ τ(face), so a vertex's region always contains the ends of its edges.

| Quantity | Default | Rule |
| --- | --- | --- |
| Growth cap τ_cap | 2¹⁰ρ until the phase 0 measurement | A decision between entities x and y may raise either tolerance to at most max(τ_x⁰, τ_y⁰, τ_cap), where τ_x⁰ and τ_y⁰ are the tolerances of the input entities x and y descend from; otherwise `ToleranceGrowth { entity, needed, cap }` |
| Healing limit τ_heal | min(max(10 × the file's declared uncertainty, 2¹⁰ρ), λ_min/4), where λ_min is the smallest edge length or wall thickness measured on the import | Capping reports `Note::HealingCapped { declared, used }`; up to 2²⁰ρ with an explicit argument |
| Minimum size λ | 2⁴ρ | Smaller slivers merge within tolerance or fail with `BelowResolution` |
| Mesh precision ε | Accumulated rounding bound per Mesh [Manifold wiki] | Above τ_cap the entity becomes tolerant ("Booleans, splits and patterns") |

The cap is per decided pair so that an imported part cannot loosen native geometry. Take a Boolean of a native GP1 bracket, whose cap is about 0.12 µm, with a healed supplier part at τ = 10 µm. A native face may grow only where it is decided against an imported entity. Every other native entity keeps τ ≤ τ_cap, so its separation decisions, its PMI eligibility and its definition digest are unchanged.

The healing cap keeps healing from closing real features. An exporter that declares 0.1 mm uncertainty would otherwise license 1 mm healing, enough to close a slot or merge a thin wall. With the cap, healing stays below a quarter of the smallest feature it measured.

### Validity

With tolerance regions N(x) = { p : dist(p, G_x) ≤ τ_x }, where G_x is entity x's exact geometry, a Body is valid when four conditions hold:

1. **Incidence.** Curve endpoints lie in their vertices' regions; parameter-curve images and edge curves lie in their edges' regions.
2. **Separation.** Points of G_x within τ_x + τ_y of G_y lie in the region of an entity in their shared closure. Entities with disjoint closures are thus farther apart than τ_x + τ_y.
3. **Combinatorics.** Loops close and are oriented, and bounded regions are enclosed by closed shells. Radial order agrees with the certified angular order, and Euler–Poincaré holds per shell.
4. **Regularity.** Curves and surfaces are regular where used, except at declared singular points; parameter curves stay in their domain or its periodic cover.

### Certified decisions in rounds

Every topological question about curved geometry reduces to a quantity q, such as a distance or an oriented angle. Anvil computes a certified enclosure [lo, hi] of q and compares it with the applicable tolerance τ:

1. hi ≤ τ: **coincident**, or the point is **on**.
2. lo > τ: **separated**, with a certified sign.
3. Otherwise the enclosure is refined by subdivision or interval Newton steps, within the work limit.
4. Below ρ/2⁸ and still straddling τ, the decision is coincidence, growing the entities' tolerances to hi within the cap. If the cap or the limit comes first, the operation fails with `Ambiguous { entities, enclosure }`.

At every fidelity a floating-point filter runs first, as in Shewchuk's adaptive predicates [Shewchuk 1997]. It computes q in `f64` with a rigorous forward error bound e and decides when |q − τ| > e. Otherwise the rule above runs, so outcomes never depend on fidelity.

Order must not matter either. If one pair's decision grew a tolerance that another pair then read, the result would depend on which pair ran first. So decisions run in rounds by dimension: vertex–vertex, vertex–edge, edge–edge, vertex–face, edge–face, face–face. Within a round, pairs are decided in parallel against tolerances frozen at its start. Growth requests are reduced per entity by maximum and applied at the round's end; the new tolerances start an epoch.

Each epoch first restores τ(vertex) ≥ τ(edge) ≥ τ(face), raising the edges and vertices of a grown face. It then re-decides only the pairs that touch a grown or merged entity, plus the pairs that merges created, starting from the lowest dimension among them. Every decision is memoized by the pair and the two tolerances it read, (x, y, τ_x, τ_y), and depends on nothing else. An unchanged pair therefore returns its memoized answer, and the result equals a full re-run bit for bit. Growth is monotone and capped, so epochs terminate; too many fail with `ToleranceCascade { entities, rounds }`.

Merged entities take max(τ_x, τ_y, certified Hausdorff distance), reported as `Note::ToleranceGrown`.

**A worked example.** A Boolean on the GP1 bracket (ρ ≈ 0.12 nm) produces two vertices v and w 0.3ρ apart, both at τ = ρ.

1. *Filter.* The vertex–vertex round computes q = |v − w| ≈ 0.036 nm with forward error e ≈ 10⁻⁷ρ. Since |q − τ| ≈ 0.7ρ > e, the filter decides at once: coincident. No enclosure is needed.
2. *Merge.* At the round's end v and w merge into one vertex u with τ_u = max(ρ, ρ, 0.3ρ) = ρ. No tolerance grew, but a merge changes topology, so epoch 1 begins.
3. *Refinement.* Epoch 1 re-decides only pairs touching u. One of them is u against an edge c, the contact edge of a fillet. The filter gives q ≈ 0.98ρ with e ≈ 0.05ρ, so |q − τ| < e and the filter cannot decide. Interval subdivision of c near u narrows the enclosure to [0.9990ρ, 1.0011ρ].
4. *Decision.* The enclosure is narrower than ρ/2⁸ ≈ 0.0039ρ and still straddles τ = ρ, so the rule decides coincidence: u lies on c. Both tolerances grow to 1.0011ρ, far below the cap of 2¹⁰ρ. Growth starts epoch 2, which re-decides the few pairs touching u and c and finds nothing new.

Every pair not touching u or c was decided once, in epoch 0, and never again.

**Decision D-ANV-4:** Linear decisions use exact predicates; curved ones use a floating-point filter, then certified enclosures under the three-way rule; rounds by dimension run against frozen tolerances, growth is reduced by maximum and capped per decided pair, and each epoch re-decides only pairs touching a grown or merged entity, with decisions memoized by pair and tolerances.
*Why:* exact algebraic predicates on curved geometry are impractical, frozen tolerances make outcomes independent of pair order, and a decision depends only on its pair's geometry and tolerances, so re-deciding untouched pairs would recompute the same answers.
*Rejected:* epsilon comparisons; growth applied as pairs are decided, which depends on order; uncapped growth; a cap shared by the whole operation, which lets one imported entity loosen native ones; re-running every round of an epoch, which repeats the costly face–face round for one small growth.

### Predicates and intervals

| Family | Inputs | Method | Used by |
| --- | --- | --- | --- |
| Linear | `f64` points: orient2d, orient3d, incircle, insphere, distance comparisons | Static filter, interval filter, exact expansions [Shewchuk 1997] | Meshes, planar arrangements, hulls |
| Indirect | Implicit points from line–plane, three-plane and two-point combinations | Filters on the generating primitives, never rounding points [Attene 2020] | Mesh arrangements, Booleans, constrained Delaunay |
| Certified curved | Curves, surfaces, implicits | Interval and affine enclosures, Bernstein bounds, Krawczyk tests, with the round rule | B-rep Booleans, blends, classification, intersections |

A Krawczyk test is an interval form of Newton's method: applied to a box, it proves that the box holds exactly one root of a system of equations, or none.

**Decision D-ANV-5:** Anvil links the `robust` crate's port of Shewchuk's adaptive predicates [robust repository] as its linear predicates and bit-for-bit reference, extends it to orient3d, insphere and distance comparisons in the same style, and generates its own indirect predicates in safe Rust from Attene's scheme.
*Why:* canonical order runs identically in native and Wasm builds, a maintained permissive port saves rewriting Shewchuk's expansions, and indirect predicates make mesh arrangements exact without rational coordinates.
*Rejected:* binding C or C++ libraries, which needs FFI, and Attene's CDT is GPL or LGPL [MarcoAttene/CDT]; rational arithmetic throughout, which took 141 s where EMBER took 34 ms [EMBER 2022].

Intervals use error-free transformations, since Rust exposes no rounding modes: TwoSum, TwoProduct and exact remainders give each rounding error exactly. A nonzero error moves the bound outward with `next_up` or `next_down`, stable since Rust 1.86.0 [Rust 1.86.0 release]. Elementary functions come from `detmath`, PLT's correctly rounded library, widened by one ulp.

Exact ties in mesh algorithms break by Simulation of Simplicity [Edelsbrunner and Mücke] in canonical geometric order, as Lévy does [Lévy 2024]. Booleans classify touching and coplanar faces explicitly.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Linear and indirect predicates | Points or implicit points → exact sign | None: exact signs always exist | ANV-O-PRED-1 | 0 |
| Certified decision rule in rounds | Filter, enclosures and frozen tolerances → coincident, separated or grown; per-pair caps; epochs re-decide only touched pairs | `Ambiguous`, `ToleranceGrowth`, `ToleranceCascade` | ANV-O-TOL-1, ANV-O-DET-2 | 0 |
| Interval and reduced affine arithmetic | Enclosures with identical bits on every target | None: enclosures widen instead of failing | ANV-O-IMP-1 | 0 |
| Scale-relative resolution and frames | ρ from the result's diagonal; pins per Part; frames on the 2⁻²⁰ m grid | `BelowResolution { size, resolution, floor }`; `Note::ResolutionStep` | ANV-O-SCALE-1, ANV-O-SCALE-2 | 0 |
| Symbolic perturbation | Ties broken in canonical geometric order | None: every tie has a canonical order | ANV-O-LABEL-1 | 1 |

## Identities and encoding

Two designs that build the same geometry should share one computed result, yet each must see its own names; this section explains how Anvil's identities and encoding allow both.

### Two identities and two stages

`GeometryId` hashes the geometry part of a Body's encoding and `ObjectId` the whole encoding (contract 5), so only `ObjectId` sees names and lineage. The definition part, which holds the attributes that define the part for manufacture, has its own digest, which KLN's `ItemDefinition` records beside the `GeometryId`.

An entity-naming operation runs in two stages. The geometric stage, keyed by input `GeometryId`s, arguments, version, class and effective fidelity, computes geometry and history over canonical entity numbers. The relabeling stage, keyed by that output, the `CallSite` (the call's source position, contract 5), input name maps and definition digests, assigns `EntityId`s and attributes.

Failures and notes take the same path (contract 7.2). The geometric stage reports `OpError` and notes over canonical numbers with fix templates. Relabeling maps `at` to `EntityId`s and turns the templates into `SourcePatch`es that name the design's own bindings.

Derived artifacts (tessellation pages, cluster DAGs, volume meshes, adaptation maps, sample sets) refer to canonical numbers and are keyed by `GeometryId`. The consumer joins them with the name table from the Body's name part, keyed by `ObjectId`.

An Evaluation that realizes tolerances at another point of their zones (ING's `realize: Mid`, for example) changes only argument values. It therefore keeps every `EntityId`, while its Bodies have their own `GeometryId`s.

**Decision D-ANV-24:** Bodies carry a `GeometryId` beside the `ObjectId`, and derived artifacts carry canonical numbers only; entity-naming operations split into a geometric stage keyed by `GeometryId`s and a relabeling stage keyed by the `CallSite`.
*Why:* names hash upstream call sites transitively, so a named identity would defeat cross-design caching.
*Rejected:* caching only label-free operations, which shares almost nothing; names in shared failures or pages, which would hand one design another's names.

[[DIAGRAM diagrams/02-anvil-two-stage-operation.jsx: two-stage operation · one geometric result shared by two designs]]

Read the diagram left to right. Two designs feed one shaded geometric stage, the cache entry they share. Dashed lines carry each design's name maps to its own relabeling stage.

### Canonical geometric order

Every order Anvil uses comes from geometry: kind, box minimum, box maximum, type and defining parameters, then a hash of the geometric content. Distinct entities of a valid Body never tie; during construction, coincident vertices break ties by their neighbours' coordinates. The order sets storage rows, perturbation indices, pair order and priorities, and seeds hash argument values and input `GeometryId`s.

**Decision D-ANV-25:** Anvil is label-invariant: orders, perturbation indices, priorities and seeds come from geometry, topology and argument values, and renaming input `EntityId`s and `CallSite`s changes only name sections.
*Why:* geometry must follow from source text alone, so Git round trips rebuild bit-identically (contract 7.1).
*Rejected:* `EntityId` tie-breaks and seeds, which let names steer geometry; memory or insertion order.

### Encoding and versioning

The encoding has three parts. The geometry part holds topology, geometry, tolerances, bounds and geometric certificates in canonical order. The definition part holds definitional attributes by canonical number, and the name part holds `EntityId`s, lineage, other attributes and certificate provenance.

Each part is a persistent tree of structure-of-arrays leaves of at most 1,024 rows. A row ends a leaf when a hash of its key has its low 8 bits zero, so equal content gives equal leaves. Identities are SHA-256 Merkle hashes over leaves; floats are binary64 with −0.0 normalized, and a text form with hexadecimal floats serves golden files.

The leaf rule is part of the encoding's major version and is frozen with it. A minor version adds optional sections or columns, each a derived cache outside the hashed form or written only by operation versions released with that minor version or later. A minor release therefore never changes an identity. A major version enters the `NodeKey`, and a reader is kept for every major version.

**Decision D-ANV-9:** The encoding is canonical, with geometry, definition and name parts of content-defined leaves under Merkle hashes; the leaf rule is frozen with the major version, identities are invariant across minor versions, and every major version stays readable.
*Why:* identities need a separable name part, revisions need attributes without names, builders on different releases must agree, and a chunking change after release would change every stored identity.
*Rejected:* re-encoding in the current minor version; hashing non-default optional values, which lets a newer minor version change an unchanged output; a tunable leaf rule; STEP as native storage.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `GeometryId`, `ObjectId` and definition digest | Body → SHA-256 Merkle identities of its parts | None: every Body has identities | ANV-O-CACHE-1, ANV-O-LABEL-1, ANV-O-ATTR-1 | 0 |
| Two-stage operations | Geometric stage keyed by `GeometryId`s, relabeling by `CallSite`, for results, failures and notes | `Internal::EntityIdCollision` | ANV-O-CACHE-1 | 0 |
| Derived artifacts by canonical number | Keyed by `GeometryId`; names joined at the consumer | None: canonical numbers always exist | ANV-O-LABEL-1 | 1 |
| Canonical geometric order and seeds | Orders, perturbation indices, priorities and seeds from geometry and arguments | None: valid Bodies never tie | ANV-O-LABEL-1 | 0 |
| Encoding and text form | Body ↔ canonical bytes in three parts; leaf rule frozen per major version; identities invariant across minor versions | `EncodingError::{Unsupported, NotRepresentable}` | ANV-O-ENC-1, ANV-O-ENC-2 | 0 |
| `anvil::build` | B-rep from topology and geometry records; point sets from buffers | `Invalid { violations }` with a heal fix | ANV-O-VALID-1 | 0 (B-rep), 1 (point sets) |

## Naming and queries

Features select faces and edges by meaning, not by position, and those selections must survive edits; this section defines the names and how queries resolve them.

### EntityId

```
EntityId = SHA-256₁₂₈("anvil.eid.v1" ‖ kind ‖ CallSite ‖ role ‖ inputs ‖ discriminator)
```

The `CallSite` is contract 5's text-derived call identity, the role comes from the operation's vocabulary, and `inputs` are the generating entities' ids. Feature roles are `FeatureRole` aliases that queries match; `EntityId`s hash the operation's role.

A discriminator appears only when needed: `Bound(set)`, then `Side(cause, sense)`, then `Ordinal(k)`. An `Ordinal` follows the splitting tool's own order where one exists, such as a pattern's keys, else canonical order. It marks the id fragile (`Note::FragileAnchor`).

Untouched and modified entities keep their ids, so dimension edits that keep topology never rename entities (contract 5). Wasm components calling through `crucible:ops` append a call key to their site. A duplicate id fails with `Internal::EntityIdCollision`, with accidental odds of about n²/2¹²⁹.

**Decision D-ANV-14:** `EntityId`s hash the text-derived `CallSite`, role, generating ids and discriminator, excluding argument values, and names never feed geometric computation.
*Why:* dimension edits that keep topology must not rename entities, and text-derived identities survive Git round trips.
*Rejected:* the Op content hash, which renames on every edit; evaluation sequence numbers; live-document block ids; geometric signatures as names [persistent naming review 2018].

### Role vocabulary

Every entity-creating operation declares roles for the faces, edges and vertices it creates. ING's compiler rejects a role filter on the wrong entity kind (`ing/5002`). Sweeps share one pattern, where `e` is a profile edge and `v` a profile vertex:

| Operation | Faces | Edges | Vertices |
| --- | --- | --- | --- |
| `extrude`, `sweep` | `start_cap`, `end_cap`, `side(e)` | `start(e)`, `end(e)`, `lateral(v)` | `start(v)`, `end(v)` |
| `revolve` | As `extrude`; a full turn has no caps, and its `lateral(v)` edges are circles | As `extrude` | As `extrude` |
| `loft` | As `extrude`, keyed by the first section | As `extrude`, plus `section(i, e)` inside | As `extrude`, plus `section(i, v)` |
| `blend`, `chamfer` | `blend`, `vertex_blend` | `contact(f)` per support face | `setback(v)` |

The canonical example's `base.edge(role: end(outline.top))` is the end cap's edge from profile edge `outline.top` (contract 6). MEC's `block.edges(role: lateral(any))` selects the edges swept from profile vertices.

**Decision D-ANV-33:** Entity-creating operations give roles to the edges and vertices they create, with `start`, `end` and `lateral` for sweeps.
*Why:* the canonical example and MEC select edges by role, and ING defines a role filter as the entities created with that role.
*Rejected:* reading `role:` on edges as adjacency to faces of that role, which contradicts ING and is ambiguous at corners; rank selectors on caps, which are fragile.

### Copies and placements

Transforms always keep names. When two operands of a Boolean, `combine` or assembly feature share an `EntityId`, the operand from the later transform in ING's program order is relabeled. Its entities become EID(kind, that transform's site, `copy` or `mirror`, [source]), recorded as `Created { role: copy, from: [source] }`.

An explicit `copy(x)` always derives such ids, and lineage follows copies only on request (`.copies()`). Reflections add the aspect `Mirrored` in place, and assembly-level features prefix ids with the Instance path.

**Decision D-ANV-30:** Placement keeps names, and copying is decided where names would collide: the later transform's operand takes role `copy` or `mirror`.
*Why:* `half + mirror(half, plane.yz)` would otherwise put equal ids into one Boolean, and a rule based on reuse would let a read-only use of the source rename every downstream entity.
*Rejected:* copying whenever the source is used again; keeping ids everywhere, which collides; renaming on every transform, which breaks queries.

### HistoryRecord and lineage

| Record | Meaning |
| --- | --- |
| `Created { out, role, from }` | New entity generated from others, such as a blend face from an edge or a copy from its source |
| `Modified { id, aspects }` | Same entity with changed geometry, boundary, tolerance, attributes or `Mirrored` |
| `Split { from, into }` | One entity became several of its kind |
| `Merged { from, into }` | Several entities of one kind became one |
| `Deleted { id, by, reason }` | Consumed (a blend face consumes its edge), internal, or removed |

Records may name transient pieces inside one n-ary operation, such as coplanar faces split and then merged by one slot tool. Every input entity is unchanged or the subject of one same-kind record, and every transient appears in one `into` and one `from`.

Ancestor sets (through identity, `Split` and `Merged`) are persistent and shared with inputs; `Created` edges are generator links. The descendants D(a, B) of anchor a in Body B are the entities of a's kind that are a or descend from it.

For `repo`'s merge rule (KLN), a side's touched set is the base entities with topological records from Ops whose keys differ from the base. Topological records are `Split`, `Merged`, `Deleted`, and `Modified` in boundary or attributes. Geometry-only changes are excluded, so a width change and a new hole on one face touch disjoint sets.

### Query resolution

`anvil::resolve` is its own Op (contract 5), evaluating Ingot's query plan in three stages:

1. **Anchor.** `EntityId`s captured from feature results (`base.face(role: end_cap)`) or a structural set (`created_by(feature)`).
2. **Lineage.** Each anchor maps to D(a, B), or to the `Deleted` record that removed it.
3. **Filter and select.** Certified geometric filters (normal, type, area, adjacency, `bounded_by`), then cardinality (`one`, `all`, `at_least(n)`). Rank selectors (`longest`, `first(along:)`) follow only an anchor or role filter.

A rank winner carries `Note::NearTie { runner_up, margin }` when its certified margin is under 5% of the spread of the candidates' measures (largest minus smallest), or under 2¹⁰ρ for a position measure with two candidates. The spread, unlike the measure itself, does not change when the part moves away from the origin.

A `where:` filter follows ING's decision rule (contract 5 `Truth`). `Undecided` is a value at the node's fidelity, `Pending` while a higher fidelity is demanded, and `ResolveError::Ambiguous { entities, needed }` at the ceiling.

Each `Query` parameter declares a use: a surface (sketch planes, up-to faces, mate axes) or an extent (a face's edges, areas, PMI targets, drawing items). A surface tolerates a merge or a partial deletion; an extent changes meaning, so it fails unless the call accepts the change with `accept: [Merged, Partial, Fragile]` (default `[]`):

| Outcome | Surface use | Extent use |
| --- | --- | --- |
| Cardinality met | `Resolved { entities, notes }` | Same |
| Anchor split, one entity needed | `ResolveError::Split { anchor, pieces, fixes }` | Same |
| Anchor merged | `Note::Merged { with }` | `ResolveError::Merged { anchor, with, fixes }` unless `accept` holds `Merged` |
| Some descendants deleted | `Note::Partial { deleted }` | `ResolveError::Partial { anchor, deleted, fixes }` unless `accept` holds `Partial` |
| `Ordinal` id, or rank winner with `NearTie` | `Note::FragileAnchor` or `Note::NearTie` | `ResolveError::Fragile { reason, fixes }` unless `accept` holds `Fragile` |
| Anchor deleted | `ResolveError::Deleted { anchor, by, site, fixes }` | Same |
| Too few or too many | `ResolveError::NoMatch { stage, found, closest, fixes }` or `TooMany { candidates, fixes }` | Same |

Each fix is a typed source edit that compiles. A partial deletion offers "accept the survivors" and "anchor on the surviving pieces"; a fragile selection offers a role or `bounded_by` anchor. `query_stability` ranks the fixes, as it ranks the candidates of AGT's `inspect.suggest_query`.

`anvil::query_stability(query, ranges)` demands the query's Body through Kiln at a fixed, label-free sample set. The set holds each declared parameter at both endpoints, the current point ±10%, and 64 scrambled Sobol points seeded from argument values.

It reports `RankSwap { at }` at every sample where the winner's lineage changes and labels the report `Sampled`. Protected-branch CI runs it on every query that ends in a rank selector or reaches an `Ordinal` id.

**Decision D-ANV-15:** Resolution walks recorded lineage, then applies certified filters; splits, deletions and ambiguity are typed errors, and merges, partial deletions, `Ordinal` ids and near ties note for surface use and fail for extent use unless the call accepts them.
*Why:* contract 5 forbids silent re-selection, and each case keeps the surface a sketch needs but changes the extent a fillet or GD&T (geometric dimensioning and tolerancing) target means.
*Rejected:* geometric re-identification, which fails after geometry edits; accepting merges and partial deletions silently; three separate accept flags for one set of degradations.

**Decision D-ANV-34:** Range stability is the on-demand analysis `query_stability` over a fixed sample design, reported as sampled evidence, and `resolve` reports only local margins.
*Why:* a pure Op over one Body cannot know whether its winner changes elsewhere in the range.
*Rejected:* `RankSwap` from `resolve`, which is unknowable and uncacheable; corner enumeration, which needs 2ⁿ samples; stability claimed as a guarantee, since swaps between samples go unseen.

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
2. The rib's caps at y = ±1.5 mm cut T: `Split { from: T, into: [T₁, T₂] }` with discriminators `Bound{rib start_cap}` and `Bound{rib end_cap}`. The rib's `side(r.bottom)` becomes internal (`Deleted`), and its left and right sides merge with the base's coplanar sides.
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

Shortened to 40 mm, the rib no longer reaches T's edges: T keeps its id with a new inner loop (`Modified`), and the query resolves. Lifted 1 mm off the face, the `bounded_by` fix fails with `NoMatch`.

Written `extrude(4mm ± 0.1mm)`, the forwarded tolerance targets both caps through an anchored query. On the split part, MEC's `pmi_target_resolved` check fails with `ToleranceTargetSplit`, and its fix inserts an explicit `part.tolerance(…)` statement.

### Imported and non-B-rep entities

An imported entity's id is EID(kind, import site, `imported`, [], discriminator). The discriminator is the source's persistent id, such as an AP242 persistent id or IFC GlobalId. Otherwise it is the surface type with a hash of its exact parameters and an adjacency signature, never an ordinal.

A supplier's revised STEP file changes the parameters of every face the revision moved, and often of faces whose numbers the exporter rewrote, so their signatures change. Re-importing an Asset at the same import site therefore runs `anvil::match_bodies` at once. It pairs faces of equal surface type whose parameters agree within the import's healing tolerance and whose face-adjacency graphs agree, and writes the result as an `import_map(old, new, pairs)` Proposal with a geometry overlay. Later rebuilds reuse the reviewed map. Faces the match cannot pair keep failing with `ResolveError`, so the reviewer sees exactly which references need attention.

From phase 2, `match_bodies` also aligns two imports rigidly and matches attributed face-adjacency graphs, so faces the supplier moved are paired too.

**Decision D-ANV-31:** Imported entities are named from source persistent ids, else from exact geometric and adjacency signatures, never ordinals, and a re-import is matched into a reviewed `import_map`: by parameters within the healing tolerance from phase 1, and with alignment and graph matching from phase 2.
*Why:* one rule serves Anvil and ECO, ordinals change on re-export, quantized signatures flip at quantization boundaries, and updating a supplier's part is routine work that cannot wait for phase 2.
*Rejected:* ordinals; quantized signatures; unreviewed Hausdorff matching, which fails on the faces a supplier moved.

Tessellation face groups carry canonical numbers, SubD limit faces take cage-face ids, and converted implicits label faces by the leaf active at the surface.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `EntityId` and relabeling | Ids from `CallSite`, role, generating ids and discriminator | `Internal::EntityIdCollision` | ANV-O-SITE-1, ANV-O-LABEL-1 | 0 |
| Role vocabularies | Face, edge and vertex roles for every entity-creating operation | A wrong-kind role filter fails to compile with `ing/5002` (ING) | ANV-O-ROLE-1 | 0 |
| History records and lineage | Five records with transient pieces; persistent ancestor sets; touched sets for merges | `Internal::HistoryViolation`, a defect report | ANV-O-NAME-1 | 0 |
| Copies and reflections | Relabeling at id collisions with role `copy` or `mirror`; aspect `Mirrored`; Instance-path prefixes | None: relabeling always yields distinct ids | ANV-O-COPY-1 | 1 |
| `anvil::resolve` | `QueryPlan`, Body, per-parameter use and `accept` set → entities with notes, or ranked compiling fixes | `ResolveError::{Split, Merged, Partial, Fragile, Deleted, NoMatch, TooMany, Ambiguous}` | ANV-O-NAME-2, ANV-O-NAME-3, ANV-O-NAME-5 | 0 |
| `anvil::query_stability` | Query, declared ranges → `Sampled` report of `RankSwap { at }` | `WorkLimit { kind: Samples }` | ANV-O-NAME-6 | 1 |
| Imported entity ids | Persistent id, else exact signature | `Note::FragileAnchor` when only adjacency distinguishes faces | ANV-O-NAME-4 | 1 |
| `anvil::match_bodies` | Old and new import at one site → `import_map` Proposal with `HistoryRecord`s and an overlay; parameter match in phase 1, alignment and graph match in phase 2 | `NoCorrespondence { faces }` | ANV-O-NAME-4 | 1 (same site), 2 (moved faces) |

## B-rep topology, geometry and attributes

Every exact Body shares one boundary structure, one set of curve and surface types and one way to carry engineering attributes through operations; this section defines all three.

### Cellular topology

One cellular boundary representation serves solids, sheets, wires, non-manifold and multi-region Bodies; manifold solids get fast paths but no separate type.

| Entity | Holds | Invariant |
| --- | --- | --- |
| Region | Role `Exterior`, `Material(MaterialRef)` or `Void`; shells | One `Exterior` per Body; bounded regions are enclosed by closed shells |
| Shell | Connected face sides bounding one region | Open shells are sheets, free in `Exterior` or embedded in a region |
| Face | Surface, sense, loops, two sides each bounding a region | Both sides bound the same region only for sheets |
| Loop, coedge | Coedge cycle; next, previous, radial next, sense, parameter curve | Radial cycles ordered by certified dihedral angle |
| Edge, vertex | Curve or point, parameter interval, tolerance | τ(vertex) ≥ τ(edge) ≥ τ(face) |

Radial cycles carry non-manifold cases, and a multi-material part is one Body whose regions share internal faces, such as an insert's steel–polymer interface.

**Decision D-ANV-6:** One cellular B-rep (regions, shells, two-sided faces, loops, coedges with radial cycles, edges, vertices) serves every B-rep Body, with material per region.
*Why:* multi-material parts, conformal meshing and Booleans that keep interfaces all need faces shared by regions.
*Rejected:* a manifold half-edge B-rep with non-manifold side structures, which needs two code paths; combinatorial 3-maps everywhere, which are heavier for the common case.

Loops on periodic surfaces live in the universal cover, so a full cylinder has no seam, and poles are singular points of faces. Anvil's topology normal form removes seams and poles, keeps periodic faces unsplit and reports their counts apart. `anvil::exchange_form` adds them back for a receiver ("Conversions, exchange and error propagation").

### Geometry types

Every type evaluates exactly with derivatives to third order, gives a certified bound over any parameter box and converts to NURBS with a stated error.

| Curves | Surfaces |
| --- | --- |
| Line; circle and ellipse; parabola and hyperbola | Plane; cylinder, cone, sphere, torus (self-intersecting tori allowed, singular points marked) |
| Helix (axis, radius, pitch, handedness, taper), exact and procedural | General quadrics (phase 2) |
| NURBS, degree ≤ 25 (higher-degree imports are approximated with a bound) | NURBS, degree ≤ 25 per direction |
| Law curve from an Ingot expression through the kernel IR, with interval bounds (phase 2) | Law surface (phase 2), such as the involute gear flanks MEC defines |
| Planar offset; intersection curve; blend spine and contact curves | Offset; extrusion and revolution; helicoid (phase 2); general sweep with frame rules and scale and twist Fields (phase 2) |
| Curve on surface; polyline and arc-spline with per-vertex samples | Rolling-ball blend (a canal surface); setback vertex blend; subdivision limit (phase 3); facet |

Polyline and arc-spline edges carry toolpaths, one edge per run of one motion kind, with per-vertex Field samples. A wire Body holds 10⁷ moves in under 400 MB (target).

**Decision D-ANV-7:** Offset, intersection, sweep, blend, helix, Law and subdivision-limit geometry stays procedural, with exact evaluation and a certified cached NURBS approximation; nesting stops at depth three per face, and deeper constructions treat their inputs' caches as exact, propagate their bounds and report `Note::ProceduralFlattened`.
*Why:* procedural geometry does not accumulate approximation error, and the depth limit bounds cost and enclosure width.
*Rejected:* converting every construction to NURBS, where error compounds; unlimited nesting.

**Decision D-ANV-8:** B-rep face geometry is always parametric, and implicit surfaces never appear as B-rep faces.
*Why:* trimming, tessellation, blending and export rely on (u, v) domains, and implicit operands already yield implicit Bodies.
*Rejected:* implicit faces, since every intersection pair would need an implicit–parametric variant and STEP cannot carry them.

Two faces evaluated at an edge's shared parameter may still differ by τ_edge. Tessellation therefore samples each edge once from its 3D curve and shares those vertices with both faces. Each face's chordal bound includes τ_edge, so display meshes are watertight.

### Attributes and certificates

A design attribute is a typed record on entities: `HoleSpec`, `ThreadSpec`, `Weld`, finish, ply and laminate records, region materials, `FeatureRole` aliases. Each class declares whether it is definitional (contract 5) and its split, merge and transform policies. The relabeling stage applies them in every operation.

Split policies are `Copy`, `Drop`, `Divide` or `Fail`, and merge policies `KeepIfEqual`, `Union`, `Drop` or `Fail`. A `Fail` merge returns `AttributeConflict { entities, class }`. A `Fail` split leaves the pieces without the attribute and reports `Note::AttributeSplit { class, pieces }`.

Definitional attributes live in the definition part by canonical number, so they enter KLN's `ItemDefinition` without names. Role aliases and display styles live in the name part.

Size tolerances, GD&T and datums are not carried through operations. MEC records each, forwarded or explicit, as an anchored aspect query resolved on the final Part (contract 5 `Tol<T>`). Its `pmi_target_resolved` check fails when a target splits, merges or vanishes, and Anvil writes the resolved targets into the definition part.

Blend contact edges, offsets of smooth edges and sweep seams carry `ContinuityCertificate { order: Continuity, certified_by: (operation, version) }` in the geometry part, where `Continuity` is MEC's order enum (`G0` to `G3`). These certificates steer later intersections. The certifying `CallSite` goes to the name part, so certificates put no names into a `GeometryId`.

**Decision D-ANV-32:** Every attribute class declares whether it is definitional and how it splits, merges and transforms; definitional attributes go by canonical number into the definition part, PMI targets are anchored queries on the final Part, and certificates hold only geometry.
*Why:* a thread series or ply angle changes the part without changing its geometry, so revisions must see it without names entering geometric identity.
*Rejected:* attributes keyed by `EntityId` only, which makes edits look unmodified; attributes inside `GeometryId`, where a tolerance edit would invalidate solves; PMI copied through operations, which a split drops.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::curve` | Line, arc, conic, helix, spline, curve on surface, Law curve → wire Body | `Degenerate { parameter }`, `ToleranceNotMet { achieved }` | ANV-O-GEOM-1, ANV-O-LAW-1 | 0 (analytic, NURBS), 1 (helix), 2 (Law) |
| `anvil::surface` | Law surface from an expression → sheet Body | `Degenerate`, `NotRegular { region }` | ANV-O-LAW-1 | 2 |
| `anvil::evaluate` | Curve or face and parameters → points and derivatives to third order | `OutOfDomain { parameters }` | ANV-O-GEOM-1 | 0 |
| `anvil::sample` | Faces or curves, density → points with canonical number and (u, v), deterministic low-discrepancy | None: any density yields samples | ANV-O-GEOM-2 | 1 |
| `anvil::approximate` | Curves or faces → NURBS within a tolerance | `ToleranceNotMet { achieved }` | ANV-O-GEOM-3 | 1 |
| Procedural nesting budget | Depth three per face; deeper inputs use certified caches | `Note::ProceduralFlattened` | ANV-O-PROC-1 | 1 |
| Attributes | Definitional flag and policies in every operation; definitional attributes by canonical number | `AttributeConflict { entities, class }`; `Note::AttributeSplit` | ANV-O-NAME-1, ANV-O-ATTR-1 | 0 |
| Continuity certificates | `ContinuityCertificate` with geometric content in the geometry part, `CallSite` in the name part | None: certificates are recorded, not checked later | ANV-O-CONTACT-1, ANV-O-LABEL-1 | 1 |
| `anvil::sew` | Sheets and faces, tolerance up to τ_heal → shells or solids with tolerant edges | `Note::FreeEdges { edges, gaps }`; `ToleranceGrowth` above the limit | ANV-O-HEAL-1 | 1 |
| `anvil::heal` | Imported Body → valid Body: curves rebuilt, gaps closed, slivers removed, analytic surfaces recognized; each fix listed with its tolerance change; default limit capped at λ_min/4 | `Unhealable { entities, reason }`, never an invalid Body; `Note::HealingCapped` | ANV-O-HEAL-2 | 1 (CAx-IF corpus), 2 (beyond) |

## Intersections

Booleans, blends, shells and drawings all start by finding where two surfaces or curves meet, and a missed or invented intersection breaks the part; this section specifies how Anvil finds them with proof.

One certified framework serves every pair. Bernstein and interval enclosures prune regions that cannot meet, and normal and tangent cones exclude closed loops. The Krawczyk test proves that a box holds one regular root or none, and the round rule decides the rest, with the Projected Polyhedron solver as reference [Patrikalakis, Maekawa and Cho].

Curve–curve intersection uses closed forms for lines and circles and Bernstein subdivision otherwise; in 3D, contact is decided at the certified closest approach. Curve–surface intersection runs the same scheme in (t, u, v).

### Surface–surface intersection

Surface–surface intersection (SSI) computes the curves where two surfaces meet. It returns a branch graph of curves, isolated contacts and coincidence regions:

1. **Analytic pairs** use closed forms, detecting special positions (parallel, coaxial, tangent, coincident) within tolerance.
2. **Broad phase.** Patch-box hierarchies give candidate pairs in canonical order.
3. **Loop exclusion.** A vector v with v · (n₁ × n₂) bounded away from zero over both normal cones excludes loops and tangencies. Otherwise the pair subdivides.
4. **Characteristic points.** At the subdivision floor, Krawczyk tests find the critical points of the signed distance h. They solve S₁(u, v) − S₂(s, t) − h·n₂(s, t) = 0 with n₂ orthogonal to S₁'s tangents. Roots with h = 0 are tangencies and crossings; roots with 0 < |h| ≤ τ go to the round rule.
5. **Tangency detection.** When a box's Krawczyk test fails with a certified rank-one deficiency of the critical-point Jacobian, and the enclosure of h lies within τ_cap, the two surfaces touch along a curve. The pair switches to the contact-curve algorithm below.
6. **Boundary points** come from curve–surface intersection of each piece's boundary.
7. **Tracing.** Each branch is traced from its canonical start point, its least point in canonical order. A trace therefore depends on the branch, not on the seed that found it. A step is accepted only when an interval implicit-function test proves its box holds one branch segment.
8. **Coincidence.** Coincidence regions are created only where the distance enclosure stays below τ over a two-dimensional region.
9. **Output.** Each branch becomes a curve with a fitted B-spline, two parameter curves and its certified deviation.

Work limits are local (a depth per pair, steps per piece), so output never depends on processing order. Unresolved pairs go to the round rule or fail with `Ambiguous { faces, region }`.

**Decision D-ANV-16:** SSI uses subdivision with Bernstein and interval enclosures, normal-cone loop exclusion, Krawczyk-certified characteristic points, rank-deficiency tangency detection and certified tracing from canonical start points, with a topology certificate per pair.
*Why:* it gives branch-graph guarantees in `f64` with interval rules, runs in parallel over pairs, and makes every trace a function of its branch.
*Rejected:* marching from sampled seeds, which misses loops; purely algebraic methods, whose degrees explode for offsets and blends; sampling as the decision method.

### Phase closure

An operation must never create a surface that no available intersection class covers, or a later Boolean with a simple box would fail. Anvil therefore lists every pair of surface types that a phase's operations create as a class with a phase, and phases each operation no earlier than the classes its output needs (contract 7.1).

Phase 1 operations create these surfaces:

- planes, the quadrics of revolution (cylinder, cone, sphere) and tori;
- extrusion and revolution surfaces of any phase 1 curve (lines, conics, NURBS curves and glyph outlines);
- canal surfaces (rolling-ball blends and circular pipes) and setback vertex patches;
- offsets of all of these, and facets.

Every pair among them is a phase 1 class:

| Class | Pairs | Method | Phase |
| --- | --- | --- | --- |
| Analytic | Planes, quadrics of revolution and tori with each other | Closed forms | 1 |
| Swept | Extrusion and revolution surfaces with analytic surfaces and with each other | Certified subdivision | 1 |
| Blend and offset | Canal surfaces, vertex patches and offsets of phase 1 surfaces with analytic, swept, blend and offset surfaces | Certified subdivision | 1 |
| Imported free-form | NURBS faces from imports with planes, quadrics of revolution and tori | Certified subdivision | 1 |
| Facet | Facet faces with any surface | Certified plane and edge intersections | 1 |
| General free-form | NURBS with NURBS, swept and blend surfaces; general sweeps, loft and Law surfaces; offsets of NURBS faces; helicoids; general quadrics | Certified subdivision | 2 |
| Subdivision limit | Bicubic limit patches, as NURBS | Certified subdivision | 3 |

The prismatic subset of the ABC dataset (contract 13.3) holds only faces of the analytic and swept classes, so phase 1 covers it without exception. Lofts, sweeps of non-circular profiles, twisted or scaled extrusions and exact threads create general free-form surfaces, so they join in phase 2 with that class. A phase 1 operation that meets a later class, such as a fillet along an edge of an imported NURBS face, fails with `PairClassUnavailable { pair, phase }` naming the class and its phase.

Phase 1 SSI has no sampling stage on the CPU or the GPU (contract 7.1).

**Decision D-ANV-37:** SSI classes are listed as a closure: every pair of surface types that a phase's operations create is a class with a phase, an operation is phased with the classes its output needs, and a pair outside the phase's classes fails with a typed failure naming the class and its phase.
*Why:* an operation whose output no class covers fails on the next Boolean, and a closure is a definition an oracle can test, unlike a list of pairs a gate happens to need.
*Rejected:* a class list chosen by the needs of GP1 and a loosely defined dataset subset; keeping lofts and general sweeps in phase 1 with phase 1 NURBS offsets added, which pulls most of the free-form class forward for no phase 1 gate.

### Tangential contact

Blends are tangent to their supports, so later operations meet tangential contact along curves on most real parts. Where curvatures differ by Δκ, a shift ε moves crossings by √(2ε/Δκ). That is about 10⁻⁸ m for ε = 10⁻¹⁶ m and Δκ = 1 m⁻¹, so naive tolerance decisions create spurious coincidence bands.

Faces sharing an edge with a `ContinuityCertificate` are not re-intersected along it. The tangency detection step finds tangency made by design without a certificate: a slot sketched tangent to an edge, a hole tangent to a fillet, a boss tangent to a wall. Both cases go to the contact-curve algorithm, which traces and certifies the reduced critical-point system along the curve and imprints one tangential edge with τ = max(ρ, certified contact deviation).

Take a 3 mm hole tangent to a 5 mm fillet on the GP1 bracket, so Δκ ≈ 133 m⁻¹. Without detection it would leave a band about 2√(2τ/Δκ) ≈ 85 µm wide at the growth cap τ ≈ 0.12 µm. With it, the result is one edge.

Tangent points are regular roots with h = 0, and branch crossings are saddle roots that become degree-4 vertices. Near-misses closer than τ touch, with recorded growth.

**Decision D-ANV-26:** Constructions record `ContinuityCertificate`s on edges they make tangent, SSI detects uncertified tangency by a certified rank-one deficiency, and tangential contact along curves uses a certified contact-curve algorithm on the reduced system.
*Why:* blend tangency is the common case, tangency made by design is common too, and the full system is singular along contact curves.
*Rejected:* the coincidence rule for tangency, which leaves spurious bands about 2√(2τ/Δκ) wide; re-intersecting certified edges, which is ill-conditioned and adds no information.

### GPU use and freedom to operate

From phase 2, after a favourable opinion, the GPU evaluates both surfaces on `f32` grids with cell boxes [Krishnamurthy et al. 2008]. It orders pairs likely to hold a branch and runs integer box tests whose candidate sets equal the CPU's (contract 7.1).

US 12,229,885 B1 (inventor Alyn Rockwood) claims intersection points formed from points of one surface within a threshold distance of the other. Claims 1, 6 and 11 compare point sets, and claim 16 recites no GPU [US12229885B1 full text]. Zoo's engine overview describes a related method [Zoo engine overview].

Counsel's opinion on these claims and a search of the phase 1 code paths are phase 0 gate items (contract 13.1). Anvil describes each path, and counsel confirms that phase 1 SSI avoids the claimed comparison.

**Decision D-ANV-17:** Every transversal intersection point is a certified root of the exact equations, tangential contact curves and coincidence regions are certified enclosures within their recorded tolerance, and no point is ever selected from a sample set by a distance threshold; phase 1 SSI has no sampling stage, and from phase 2, after a favourable opinion, GPU sampling only orders CPU work.
*Why:* outputs are identical with and without a GPU, GP1's surface set needs no sampling, and the statement says exactly what the code does.
*Rejected:* sampled SSI on the GPU, which is uncertified, and Zoo calls its SSI approximate [Zoo engine overview]; GPU sampling in phase 1, where an adverse opinion would block release.

Triangle pairs use exact arrangements with indirect predicates [Cherchi et al. 2022]. Facet faces meet exact surfaces through certified plane and edge intersections, and regular subdivision-limit faces are bicubic patches.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Curve–curve and curve–surface intersection | Certified points and overlaps, classified transversal or tangent | `Ambiguous { entities, region }` | ANV-O-SSI-1 | 0 (analytic), 1 |
| SSI, phase 1 pair classes | Closed forms and certified subdivision over the closed phase 1 class list, no sampling stage → branch graph with topology certificate | `Ambiguous`, `WorkLimit`, `PairClassUnavailable { pair, phase }` | ANV-O-SSI-1, ANV-O-SSI-2, ANV-O-SSI-4, ANV-O-SSI-5 | 1 |
| SSI, general free-form pairs | As above, including helicoids and NURBS offsets | As above | ANV-O-SSI-3 | 2 |
| Contact curves and continuity certificates | Certified or detected tangency → one tangential edge with τ = max(ρ, certified deviation), no coincidence band | `ToleranceGrowth` | ANV-O-CONTACT-1 | 1 |
| `anvil::intersect` | Two entity sets → new wire Body with `Created(intersection)` records | `Ambiguous` | ANV-O-SSI-1 | 1 |
| GPU work ordering and integer broad phase | After a favourable opinion; same output with and without a GPU | Device loss is an Abort; Kiln reruns on the CPU path | ANV-O-DET-1 | 2 |

## Booleans, splits and patterns

Union, subtraction, intersection, splitting and interference are one computation that keeps different cells, so Anvil runs them through one engine. It works in six steps:

1. Intersect the faces that overlap in the broad phase (SSI for exact faces, exact arrangements for facets).
2. Imprint the curves on every operand.
3. Merge coincident entities by the round rule.
4. Classify each cell's membership vector by radial order and one point test per connected group, as in Lévy's Weiler model [Lévy 2024]. Imperfect operands use generalized winding numbers [Spainhour and Weiss 2025].
5. Select cells by the expression.
6. Regularize, merge same-surface faces and emit history.

Expressions are n-ary. Ingot lowers each Boolean expression without intermediate bindings to one n-ary operation (ING), so rounding happens once per expression. `keep: Cells` returns every non-empty cell as a region labelled by its membership vector, so an overmolded insert is `boolean([insert, shot], keep: Cells)` with materials per region.

**Decision D-ANV-19:** One cellular arrangement engine runs Booleans for every pair without an implicit operand, plus n-ary expressions, cell-keeping results, `split`, `imprint` and `interference`.
*Why:* these operations differ only in which cells they keep and report, and Parasolid's Booleans already imprint, join and select [Jackson 1995].
*Rejected:* separate union, subtract and intersect paths, with three times the special cases; binary-only Booleans, which need n − 1 passes for n tools.

B-rep pairs give a B-rep, and mesh pairs a mesh through the method the bake-off below chooses. B-rep with Mesh or SubD gives facet or limit faces, and an implicit operand gives an implicit. An empty result is an empty Body, not a failure; MEC's features decide whether emptiness is an error.

### Mesh Booleans

The phase 1 wedge competes with code-CAD tools whose mesh Booleans do not fail, so Anvil's must not fail either. EMBER's plane-based local arrangements take 34 ms for 1.2 million triangles on 8 cores, from 26-bit integer input, but output a polygon soup [EMBER 2022]. Indirect-predicate arrangements take 0.14 s at 200,000 triangles [Cherchi et al. 2022].

Topological aggregation claims up to 100× speedups with watertight output [trueform 2026]. Its library is PolyForm Noncommercial 1.0.0 or commercial [trueform repository], so Anvil implements the method from the paper.

A phase 0 bake-off on Thingi10K pairs and thingiCSG compares three Rust candidates: ρ-grid local arrangements, topological aggregation, and indirect predicates. It records each candidate's failure count and chooses by zero failures first, then validity, then time; the winner sets the million-triangle target.

Output rounding is checked exactly. Repairs collapse only edges shorter than 2ε in at most three passes. A conflict that survives them does not fail: the result is kept as a facet B-rep whose affected vertices and edges carry τ equal to the certified rounding displacement, with `Note::ToleranceGrown`. Only a displacement above τ_cap fails, with `PrecisionExhausted` and a remesh fix.

**Decision D-ANV-20:** A phase 0 bake-off chooses the mesh Boolean method among ρ-grid local arrangements, topological aggregation and indirect predicates, ranked by failures first, and every candidate has exact classification, bounded repair, one rounding per expression and tolerant facets in place of failure below τ_cap.
*Why:* published speeds differ by one to three orders of magnitude, ρ-grid quantization keeps Anvil's resolution, and Anvil's tolerant topology already expresses a certified rounding displacement, so a refusal would be a choice, not a necessity.
*Rejected:* choosing without measurement; ranking by validity then time, which scores a method that refuses hard cases like one that solves them; Manifold's method, whose ε-validity is not guaranteed [Manifold wiki]; linking a C++ library.

### Patterns, hulls and Minkowski sums

`anvil::pattern` makes keyed copies (contract 5 keys), combined in one n-ary Boolean. When copies overlap only the target and meet congruent faces, the first copy's intersections are transformed and reused, adding one rotation rounding to their bounds. Translational, circular and mirror patterns reuse where the target has the matching symmetry within τ.

`anvil::hull` computes convex hulls exactly with orientation predicates on meshes and facet faces, and B-rep operands by support-function sampling with a stated bound. `anvil::minkowski` sums meshes and convex B-rep operands by convex decomposition and pairwise sums.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::boolean` | Bodies, n-ary expression, `keep: Regularized` or `Cells` → Body; `Split`, `Merged`, `Deleted(Internal)`, `Created(intersection_edge)`; tolerant facets below τ_cap | `Ambiguous`, `ToleranceGrowth`, `BelowResolution { size }`, `PrecisionExhausted`, `PairClassUnavailable` | ANV-O-BOOL-1, ANV-O-BOOL-2, ANV-O-BOOL-3, ANV-O-BOOL-4 | 1 |
| `anvil::split` | Body, tool → pieces or one cellular Body | `ToolDoesNotCut`, `OpenTool { gaps }` | ANV-O-BOOL-5 | 1 |
| `anvil::imprint` | Body, curves or Body → split faces and edges, volume unchanged | `CurveNotOnFace { gap }` | ANV-O-BOOL-6 | 1 |
| `anvil::trim` | Sheet, boundary or tool, kept side | `KeepSideAmbiguous` | ANV-O-TRIM-1 | 1 |
| `anvil::extend` | Face edge, distance or target, `Natural`, `Linear` or `CurvatureContinuous` | `CannotExtend { reason }` | ANV-O-TRIM-2 | 1 |
| `anvil::transform` | Rigid motion, scale or reflection; ids kept | `Degenerate` for zero scale | ANV-O-XF-1, ANV-O-COPY-1 | 0 |
| `anvil::pattern` | Keyed copies, `Separate`, `Union` or `Subtract`, with congruent reuse | `CopyFailed { key, error }` unless `skip`; `Overlapping { pairs }` | ANV-O-PAT-1, ANV-O-PAT-2 | 1 |
| `anvil::hull` | Meshes, facet faces → exact hull; B-rep operands with a stated bound | `Degenerate` (coplanar input) | ANV-O-HULL-1 | 1 (meshes, facets), 2 (B-rep) |
| `anvil::minkowski` | Meshes and convex B-rep operands | `NotConvex { operand }` | ANV-O-HULL-1 | 2 |
| `anvil::convex_decompose` | Body → convex parts with a Hausdorff bound | `WorkLimit` | ANV-O-HULL-1 | 3 |

## Blends, offsets, draft and direct edits

Fillets, shells and face edits are where kernels most often fail an engineer. This section states what Anvil builds in each phase and how it is measured against the kernel the engineer is leaving.

### Blends

Blending is a staged program (contract 7.1). `anvil::blend` takes edges with extent use, a radius law (`Constant`, `Linear(r0, r1)`, later a Field) and a section (`Circular`, later `Conic` and `CurvatureContinuous`). Corners are `Auto`, `Setback { distances }` or `Sharp`; overflow is `RollOver` (default), `KeepEdge` or `Fail`; variants are `EdgeChain`, later `FaceFace`, `ThreeFace` and `ChordWidth`.

For each chain, Anvil offsets both supports by r and intersects the offsets with certified SSI for the spine. Projecting the spine onto the supports gives the contact curves, between which Anvil builds a procedural rolling-ball surface. Supports may be blend, offset and swept faces, so sequential fillets work; `anvil::chamfer` uses the same engine.

Corners use Várady and Rockwood's setback split [Várady publication list]: blends stop short of the vertex, and an n-sided G1 patch fills the gap.

| Stage | Capabilities | Phase |
| --- | --- | --- |
| 1 | Constant and linearly varying radius; circular sections; blend, offset and swept supports in the phase 1 classes; convexity change along an edge; `RollOver` and `KeepEdge`; valence-3 corners with unequal radii and mixed convexity; chamfer–fillet corners; termination at smooth edges; chamfers | 1 |
| 2 | Conic and G2 sections; Field-driven radii; `FaceFace` with hold lines; `ThreeFace` (full round); `ChordWidth`; partial-length blends with setback ends; capped and cliff ends; `edit_blend` | 2 |
| 3 | Corners of valence four and above; blends across facet faces | 3 |
| 4 | G3 sections | 4 |

Where a boss meets a curved wall, the edge's convexity can change along its length: the rolling ball crosses from one side to the other where the faces are tangent. Stage 1 splits the blend there into a convex and a concave run. A capped end stops a blend against a face it does not meet tangentially; a cliff end runs it off a face that drops away.

Failures carry fixes: `RadiusTooLarge { edge, max_feasible }` (use the maximum); `BlendOverflow { faces }` (another overflow rule); `VertexBlendFailed { vertex, reason }` (larger setbacks, or the fallback); `SelfIntersecting { region }` (a smaller radius); `NoContact { faces }` for a `FaceFace` blend whose ball cannot touch both face sets (a larger radius or other faces).

With `fallback: Implicit { max_deviation }`, a failed region becomes a smooth union of the supports' exact distances, fitted G1 to the neighbouring faces. Its seam is a tolerant edge with τ equal to the certified gap. `Note::BlendFallback { region, deviation, seam_gap }` states the certified deviation from the rolling-ball surface, per instance.

History: `Created { role: blend, from: [edge] }`, `Created { role: vertex_blend, from: [vertex] }`, `Deleted { by: blend face }` for each blended edge and `Modified` for trimmed supports; contact edges get certificates.

### Measuring against the kernel engineers leave

The ABC dataset is a large set of public Onshape models whose B-reps Parasolid built. Each model ships its native Parasolid file and its original FeatureScript, Onshape's feature language [ABC dataset page]. Every fillet in it is therefore a fillet Parasolid made. Anvil measures itself against those stored results, part by part, because an engineer leaving NX, SOLIDWORKS or Onshape judges a kernel by whole parts that rebuild, not by single fillets.

The part-level parity benchmark takes each licence-filtered ABC model (contract 13.3) whose FeatureScript uses only features in the phase's scope. Those are sketches with their solved geometry fixed, extrude, revolve, fillet, chamfer, shell, hole, pattern, mirror and Boolean. An oracle-side translator in `oracles/` writes an Ingot program for it; the translator is a test fixture and never an import path, so Crucible still never replays proprietary history (contract 7.7).

A case passes when the whole program rebuilds, `check_body` passes, and the result matches the stored Parasolid B-rep:

- **Edge blends and every other face** match the original's topology in normal form and lie within a certified Hausdorff distance of max(1 µm, 10⁻⁵ D).
- **Corners** are judged by shape, not by face count, since Anvil's setback patches need not copy Parasolid's corner faces. A corner passes when its patch is G1 to its neighbours within 10⁻⁶ rad and lies inside the convex hull of the original's corner region grown by the largest radius. Its volume must differ from the original corner region's by at most 1% of r³. Face-count differences are reported, never failed.

The fillet slice is the set of in-scope models whose last feature is a fillet or chamfer, classified by the stage its configuration needs. Each report lists the corpus share per stage, every per-feature-kind rate, and OCCT 8.0's rate on the same slice.

| Measure | Phase 1 gate | Phase 2 gate | Phase 3 gate |
| --- | --- | --- | --- |
| Whole in-scope parts | 98%, GP1-class parts (contract 13.1) | 99.5% | 99.5% |
| Fillet slice, stage 1 | 99% | 99.7% | 99.7% |
| Fillet slice, stages 1 and 2 | | 99.7% | 99.7% |
| Fillet slice, all stages | | | 99% |

These are targets. If valence-four corners exceed 3% of the slice, those with equal convexity come forward to phase 2 for the cast housing of GP3.

**Decision D-ANV-29:** Stage 1 blends cover the cases in the stage table, and their success is measured on the fillet slice of the part-level parity corpus with separate criteria for edge blends and corners and per-stage targets.
*Why:* GP1 needs sequential fillets, rolling overflow and mixed corners; the corpus originals are Parasolid's, so the slice measures parity with the kernel users switch from; and judging corners by shape keeps the benchmark from rewarding imitation of one vendor's corner faces.
*Rejected:* a corpus made by OCCT's defeaturing, which removes faces by extending and re-intersecting their neighbours and inherits `BOPAlgo_RemoveFeatures`' limitations [OCCT Defeaturing], so the hardest fillets never become cases; one target over all stages, which says nothing about stages a phase does not ship; targets relative to OCCT only, which set no floor; equal-radius corners only.

**Decision D-ANV-38:** Anvil's rebuild robustness is gated by the part-level parity benchmark: whole in-scope ABC parts rebuilt from their FeatureScript by an oracle-side translator and matched against their stored Parasolid B-reps, at 98% at the phase 1 gate and 99.5% at phase 2 (targets).
*Why:* with independent failures, a 95% per-fillet rate rebuilds a part with 20 fillets about 36% of the time, so only a part-level rate tells an engineer whether their parts survive.
*Rejected:* per-case rates alone; comparison with OCCT only, which is not the kernel users leave; importing FeatureScript as a product path, which contract 7.7 forbids.

### Offsets, shells and draft

`Round` offsets are exact Minkowski sums with a ball: offset faces, edge pipes and vertex spheres form one arrangement, cut at distance d. `Natural` offsets extend and re-intersect offset faces. Phase 1 offsets analytic and procedural faces, NURBS offsets follow in phase 2 with the general free-form class, and meshes use feature-preserving mitered offsets [Cao et al. 2024].

`anvil::shell` takes `mode: Round | Natural`, default `Natural`, because the commonest shell decides it: an inward shell of a filleted box whose fillet radius is below the wall. `Round` would erode the solid and keep rounded inner corners; `Natural` collapses the offset fillet. Anvil removes the collapsed blend faces and leaves the inner edge sharp, reporting `Note::BlendCollapsed { faces }`, which is what an engineer expects.

`anvil::draft` tilts faces about a neutral element by an angle or a Field; planes stay planes and cylinders become cones. Phase 3 adds `parting` and `step` modes, which draft about a parting line, for MEC's moulded parts.

### Direct edits and blend regrowth

Face edits (`offset_faces`, `move_faces`, `replace_faces`, `delete_faces`, `draft`) remove adjacent blends, apply the edit and rebuild the blends with the same parameters and ids. Imported blends come from `recognize_aspects`. A blend that cannot regrow fails with `BlendRegrowFailed { blend, reason }` and the fixes "remove blend" and "reduce radius".

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::blend` | Edges (extent use), radius law, section, corners, overflow, variant → Body; certificates on contact edges | `RadiusTooLarge`, `BlendOverflow`, `VertexBlendFailed`, `SelfIntersecting`, `NoContact`, `PairClassUnavailable` | ANV-O-BLEND-1, ANV-O-BLEND-2, ANV-O-BLEND-3, ANV-O-BLEND-4, ANV-O-BLEND-5 | 1 (stage 1) to 4 |
| Part-level rebuild parity | In-scope ABC parts rebuilt and matched against their Parasolid originals at the stated targets | A shortfall fails the gate | ANV-O-PARITY-1 | 1 |
| `anvil::chamfer` | Edges, two distances or distance and angle | `RadiusTooLarge`, `VertexBlendFailed` | ANV-O-BLEND-1 | 1 |
| `anvil::edit_blend` | Anvil-made or recognized blend, new radius or section | `BlendRegrowFailed` | ANV-O-BLEND-6 | 2 |
| `anvil::offset` | Body, signed distance (value or `Field<Faces, Length>`), `Round` or `Natural` | `OffsetCollapse { faces }`, `FieldOutOfRange` | ANV-O-OFF-1 | 1 (analytic, procedural, implicit), 2 (NURBS, mesh) |
| `anvil::offset_faces` | Faces moved along normals; neighbours extended; blends regrown | `NeighborCannotExtend { face }`, `BlendRegrowFailed` | ANV-O-OFF-2, ANV-O-BLEND-6 | 1 |
| `anvil::shell` | Solid, faces to open, thickness (a value; a Field from phase 2), `mode: Round` or `Natural` (default, collapsed blends removed) | `WallCollapse { region }`; `Note::BlendCollapsed { faces }` | ANV-O-OFF-3 | 1, 2 (Field) |
| `anvil::thicken` | Sheet, thickness, side → solid | `SelfIntersecting { region, max_thickness }` | ANV-O-OFF-3 | 1 |
| `anvil::draft` | Faces, pull direction, neutral element, angle or Field; `parting` and `step` modes; blends regrown | `DraftNotPossible { face, reason }`, `BlendRegrowFailed` | ANV-O-DRAFT-1 | 1 (analytic), 2 (free-form), 3 (parting, step) |
| `anvil::move_faces`, `replace_faces`, `delete_faces` | Faces and a motion, replacement or removal; neighbours re-intersected; blends regrown | `TopologyChangeRejected`, `ReplacementDoesNotClose { gaps }`, `CannotHeal { loop }` | ANV-O-DE-1, ANV-O-DE-2 | 2 |
| `anvil::recognize_aspects`, `recognize_relations` | Holes, fillets, chamfers, bosses, pockets, ribs, patterns; coplanar, coaxial, tangent and other relations by the round rule | `Note::Unrecognized { faces }` | ANV-O-REC-1, ANV-O-REC-2 | 2 |
| `anvil::defeature` | Aspect kinds below sizes, or faces → recognize, then delete | `CannotHeal` per aspect | ANV-O-DE-3 | 2 |

## Construction, surfacing and derived geometry

Features need primitives, sweeps, surfaces, text, flattening and the reduced geometry that simulation uses; this section lists the constructions Anvil provides and when each arrives.

Sweeping operations follow the phase closure. `extrude` of any phase 1 profile, `revolve`, and `sweep` of a circular profile (a pipe, which is a canal surface) are phase 1. Twisted or scaled extrusions, drafted extrusions of profiles other than lines and arcs, sweeps of other profiles, guided sweeps and lofts create general free-form surfaces and join in phase 2.

MEC's `text` calls `anvil::text_outline(font, string, layout)`, which shapes text with PLT's Parley stack from a font package pinned in `ingot.lock`. Its glyph outlines are exact Bézier curves that `make_regions` turns into faces, so text works in phase 1, as code-CAD users expect [OpenSCAD cheat sheet]. `make_regions` and the tessellation of planar faces triangulate with the `spade` crate's constrained Delaunay triangulation and exact predicates, inserting in canonical order [spade repository].

Emboss and engrave sweep the wrapped region along the face normal by the height, giving walls ruled by normals, then unite or subtract. The walls meet the base face along the wrapped curves, known by construction, so no new intersection class is needed.

Printed threads take the mesh path in phase 1: the helical sweep is tessellated within the 3MF chord tolerance and joined by the mesh Boolean. Exact B-rep threads follow in phase 2 with the helicoid class.

For Flux's shell models, `anvil::mid_surface` pairs offset faces, builds exact or procedural mid-surfaces, and joins them at junctions into a sheet with a thickness Field. For sheet lattices of minimal surfaces (gyroid, Schwarz P, diamond), it returns the TPMS (triply periodic minimal surface) zero set, the sheet's mid-surface by construction, trimmed by the part. `anvil::member_axes` returns member axes and joints, with each cross-section as a planar region with its area and second moments.

For control-vertex drags, Anvil re-evaluates the edited patch on the GPU at `Preview` fidelity within 16 ms (target); releasing the drag writes one Ingot edit.

Continuity analyses take one threshold per order, because only position scales with length. The defaults are G0 within the edge's τ, G1 within 10⁻⁶ rad, G2 within 10⁻⁴ relative curvature difference and G3 within 10⁻³ relative, each overridable per check.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::primitive` | Box, wedge, cylinder, cone, sphere, torus, prism → solid with roles | `Degenerate { parameter }` | ANV-O-OP-1 | 0 |
| `anvil::make_regions` | Planar wires (lines, arcs, Bézier glyph outlines) → faces with nested loops | `OpenProfile { gaps }`, `SelfOverlap { curves }` | ANV-O-OP-2 | 1 |
| `anvil::text_outline` | Font package, string, layout → shaped glyph outlines as Bézier wires | `FontMissing { font }`, `GlyphMissing { char }` | ANV-O-TEXT-1 | 1 |
| `anvil::extrude` | Faces; direction; distance, Field or up-to target; draft; symmetric; twist and scale Fields → the sweep roles | `SelfIntersecting` with the largest feasible draft; `UpToNotReached { target }` | ANV-O-OP-3, ANV-O-ROLE-1 | 0; 2 (twist, scale, draft of other than lines and arcs) |
| `anvil::revolve` | Faces or curves, axis, angle ≤ 2π; no seam on a full turn | `AxisCrossesProfile { points }` | ANV-O-OP-4 | 0 |
| `anvil::sweep` | Profiles, path, frame rule, scale and twist Fields; helical sweeps; guides | `SelfIntersecting { region }`, `FrameUndefined` with a rotation-minimizing fix | ANV-O-OP-5 | 1 (circular profiles), 2 (other profiles, guides) |
| `anvil::loft` | Ordered sections, end conditions, vertex correspondence; guides | `IncompatibleSections`, `Twisted`, `ContinuityNotMet` | ANV-O-OP-6 | 2 |
| `anvil::boundary_surface`, `fill_surface`, `blend_surface`, `match_surface` | Curve networks, n-sided boundaries, bridges and matches with G0 to G3 conditions; Gordon surfaces, which OCCT 8.0 also adds [OCCT 8.0] | `NetworkNotCompatible`, `BoundaryNotClosed { gap }`, `ContinuityNotMet { edge, achieved }` | ANV-O-OP-7, ANV-O-OP-8 | 2 (G0 to G2), 3 (G3) |
| Control-vertex drag preview | Patch, control-point change → preview patch, zebra and curvature Fields | `Note::PreviewUnavailable`; the Kiln rebuild shows the result | ANV-O-FID-1 | 3 |
| `anvil::project_curve` | Curves onto faces along a direction or normal | `Misses { segments }` | ANV-O-PROJ-1 | 1 |
| `anvil::wrap` | Planar curves or sheets onto developable faces, any face through `parameterize`; emboss and engrave | `OutOfDomain { curves }` | ANV-O-PROJ-2 | 1 (developable), 3 (general) |
| `anvil::parameterize` | Faces or mesh region → (u, v) map by Boundary First Flattening (MEC's choice) or least-squares conformal | `NotDisk { genus }` with cut suggestions | ANV-O-PAR-1 | 3 |
| `anvil::unfold`, `anvil::fold` | Sheet metal and flex circuits with developable faces and a neutral-layer offset per bend | `NotDevelopable { faces, deviation }` | ANV-O-SM-1 | 2 |
| `anvil::drape_kinematic` | Woven fabric on a tool surface, pin-jointed net, quadrants in fixed order → fibre curves, shear Field | `ExcessiveShear { region, angle }` | ANV-O-DRAPE-1 | 4 |
| `anvil::mid_surface` | Thin-walled solid → sheet, thickness Field, junction curves; sheet lattice → trimmed TPMS zero set; `Created { role: mid(a, b) }` | `UnpairedFaces { faces, reason }` with the partial sheet | ANV-O-MID-1 | 2 |
| `anvil::member_axes` | Lattice strut graph or swept members → axes, joints, cross-section regions, area and second moments | `NotPrismatic { region }` | ANV-O-AXIS-1 | 1 (lattices), 2 (swept members) |
| `anvil::section` | Body and a plane, a stack of planes or a surface → regions or curves, any representation, lattices included | `NotClosed { gaps }` naming defective faces | ANV-O-SEC-1 | 1 |
| `anvil::deform` | Body, displacement Field or cage → same representation; ids kept | `FoldOver { region }`, `ToleranceNotMet { achieved }` | ANV-O-DEF-1 | 2 |
| `anvil::morph` | Source, target or correspondences → deformation Field, then `deform` | `NoCorrespondence` | ANV-O-DEF-2 | 3 |
| `anvil::shrinkwrap` | Bodies, gap g → one closed skin by closing on exact distances | `WorkLimit` | ANV-O-OFF-4 | 2 |

## Implicit representation

Lattices, topology-optimized shapes and field-driven geometry have millions of features that no B-rep can hold efficiently; the implicit representation holds them as a function and keeps exact B-rep faces where they matter.

An `Implicit` Body is a function f whose region f ≤ 0 is the solid, plus the exact faces its B-rep leaves keep. f is an expression in `kernels::expr`, the shared symbolic type (contract 7.5). `anvil-implicit` extends it with an implicit node set. Nodes cover arithmetic, `detmath` functions, exact-distance primitives, hard and smooth CSG (constructive solid geometry), warps, offsets, repetition, TPMS families and strut graphs. Leaves hold B-rep or Mesh distances, Fields and cached bricks.

### Distance kinds

| Kind | Meaning | Allowed uses |
| --- | --- | --- |
| `Exact` | f is the signed distance | Everything, including offsets by any amount |
| `Bound(L)` | Correct sign and \|f(p)\| ≤ L·dist(p, boundary) | Classification, Booleans, sphere tracing with step \|f\|/L, meshing; offsets after redistancing |
| `Lipschitz(L)` | Correct sign and \|f(p) − f(q)\| ≤ L·\|p − q\| | As `Bound(L)` |
| `SignOnly` | Correct sign only (C0 warps) | Interval classification only |

Kinds propagate statically (min of exact distances is exact outside; a warp's constant is the enclosure of ‖J⁻¹‖). Offsetting a non-exact implicit first redistances a narrow band around the certified zero set, unless the caller accepts `approximate: true` with an `Estimated` bound.

**Decision D-ANV-10:** Implicit nodes carry a statically propagated distance kind and Lipschitz constant, and operations that need exact distances redistance in a narrow band.
*Why:* lattices, smooth blends and warps rarely give exact distances, and Lipschitz pruning relies on the same property [Barbier et al. 2025].
*Rejected:* assuming every implicit is a signed distance, which makes offsets and clearances silently wrong; only exact-distance constructions, which exclude TPMS, smooth blends and Field-driven geometry.

### Evaluation

Expressions lower to register-allocated tapes in the shared kernel IR (contract 7.5), like Fidget's bytecode [Fidget]. Point, gradient, interval and reduced-affine evaluators run them. One tape passes its oracle through both CPU back ends before the phase 0 gate, as a consumer that freezes IR v0.

Interval evaluation prunes inactive min and max branches per box, shortening tapes about 17× per tile in Keeter's measurements [Keeter 2020]. Anvil also prunes smooth unions by Lipschitz bounds [Barbier et al. 2025] and moves wide boxes to reduced affine arithmetic [Sharp and Jacobson 2022].

**Decision D-ANV-11:** Implicit tapes are kernel-IR programs; the canonical CPU evaluator is a pruning SIMD interpreter, compiled CPU paths keep the IR's operation order, and a WGSL interpreter runs previews.
*Why:* Fidget's 31× compiled advantage shrinks to about 25% once pruning runs, and the fastest Prospero entry is an interpreter [Prospero].
*Rejected:* a native JIT per architecture, a second code path; a WGSL shader compile per edit, which lands inside the drag.

WGSL fixes no rounding mode and lets implementations flush subnormals, reassociate and fuse operations, and assume no infinities or NaNs [WGSL]. GPU tape results therefore order work and preview, and never decide or prune. A CAS cache of 8³ bricks of values and gradients covers the narrow band, with read bounds from the Lipschitz constant and spacing.

### Fields and lattices

Field leaves sample Flux `Field`s at a requested accuracy, adding the sampled error to the Body's bounds. `anvil::implicit_from_field` needs a continuous Field with a finite gradient bound; degree-0 and quadrature-point Fields fail with `NotContinuous`, whose fix is Flux's filtered, projected density.

`anvil::lattice` fills a region from family, cell size, thickness, orientation and skin Fields; domain repetition keeps millions of cells to a few hundred nodes. Strut graphs serve beam models and the 3MF Beam Lattice extension 1.2.0, with end radii, caps and balls [3MF beam lattice spec]. Sheet lattices expose their TPMS field for `mid_surface`, and cell-family generators are Wasm components that emit graphs or tapes.

A drawing shows a lattice region as its boundary, never as millions of struts. `project_hlr` runs only on B-rep faces and the region boundary, and section views cut the lattice with `anvil::section` at the sheet's line resolution; MEC draws the zone symbol and note.

### Implicit meshing

`convert(implicit, into: Mesh)` uses adaptive dual contouring on an octree:

1. Interval evaluation marks cells inside, outside or ambiguous; ambiguous cells refine.
2. A surface cell is certified when ∇f·d excludes zero for a direction d from its gradient cone; cells that reach λ uncertified are flagged.
3. Each cell places one vertex per surface piece by minimizing a quadric error function from exact gradients, keeping sharp features.
4. Manifold dual contouring connects the vertices [Fidget], a structure that parallelizes well on GPUs [Hwang and Sung 2024].
5. An exact self-intersection check repairs crossings by moving vertices within their cells.

Surface points lie within one cell diagonal of the mesh; triangles lie within two, or within max |f| over a certified floor of |∇f|. The bound is `Guaranteed` in certified cells and `Estimated` in flagged ones.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::implicit` | Ingot expression → `kernels::expr` node with distance kind and Lipschitz constant | `Note::SignOnlyUse` reports slow uses | ANV-O-IMP-1, ANV-O-IMP-2 | 1 |
| Tape evaluation and pruning | Point, gradient, interval, affine evaluators; pruned tapes equal full tapes per region | None: evaluation is total over finite inputs | ANV-O-IMP-3 | 0 (one tape for the IR freeze), 1 |
| WGSL tape interpreter | Tapes as data for previews and UIX rendering | Device loss is an Abort; CPU path | ANV-O-FID-1 | 1 |
| `anvil::implicit_from_field` | Continuous Field, iso-value → implicit, `Lipschitz(L)`, bound from sampling error and gradient floor | `NotContinuous`, `NoIsoSurface`, `FlatIsoSurface { region }` | ANV-O-IMP-4 | 1 |
| `anvil::lattice` | Region, family, cell size, thickness, orientation, skin Fields → implicit with roles `wall`, `strut`, `node`, `skin`, and the strut graph or TPMS field | `BelowResolution`, `FieldOutOfRange`, `TooManyCells { estimated, limit }` | ANV-O-LAT-1 | 1 |
| Implicit meshing | Implicit → manifold Mesh with two-sided bound | `Uncertified` cells listed | ANV-O-CONV-1 | 1 |

## Meshes and volume meshing

Scans, prints and every simulation mesh are meshes, and Anvil owns all of them so that they share its predicates, tolerances and entity numbering (contract 7.1).

### Surface meshes and repair

A `Mesh` stores `f64` positions in the Body frame, three half-edges per triangle, face groups with canonical entity numbers, crease edges and the precision ε. Per-vertex or per-corner channels carry normals, UVs, colours, back-references and Field values, indexed apart so seams never break topology [Manifold wiki]. A Mesh with vertices and no triangles is a point set.

`anvil::mesh_from_triangles` builds a valid Mesh, a facet B-rep when the data is non-manifold by intent, or fails with `NotManifold { edges, vertices }`. `anvil::repair_mesh` welds vertices within the healing limit in canonical order and builds the exact arrangement of all triangles. It keeps cells whose generalized winding number exceeds 0.5, even for open input [Jacobson et al. 2013], and reports the largest displacement and area changed.

### Volume meshes

A volume Mesh adds tetrahedra, hexahedra, prisms, pyramids and general polyhedra with region indices, and geometry order up to 8 with Bézier control nodes. Boundary facets are classified by canonical number to the face or interface they approximate, and Flux resolves `ds(part.face(q))` by joining the Body's name table. Element quality is the minimum scaled Jacobian, certified from Bernstein coefficients.

**Decision D-ANV-12:** Volume meshing, adaptation and node optimization are Anvil operations, and Flux chooses what to mesh and how finely through sizing and metric Fields.
*Why:* meshing needs exact geometry, the same predicates and tolerances, and entity numbering for boundary classification, and its outputs are Bodies (contract 7.1).
*Rejected:* meshing in Flux, which duplicates predicates and naming; meshing as a Wasm component, which needs Anvil's evaluators in every inner loop.

`Conforming` meshing, the default, runs constrained Delaunay tetrahedrization with implicit Steiner points and indirect predicates [Diazzi et al. 2023]. Rounding Steiner points keeps 93.22% of meshes valid, so Anvil checks every element exactly after rounding. It re-inserts inverted elements locally, or fails with `NotRepresentable { elements }`.

`Envelope` meshing, for soups, scans and healed imports, optimizes a floating-point mesh inside an envelope [fTetWild 2020] and reports omitted input triangles.

Curved elements place boundary nodes on the classified face, certify validity by positive Bernstein coefficients of the Jacobian determinant, untangle interior nodes and refine locally. Polynomial faces use 3D Bézier Guarding [Khanteimouri and Campen 2023]; others project, certify and untangle, compared with bijective coarse meshes [Jiang et al. 2021].

Hex-dominant meshing agglomerates tetrahedra guided by fields, keeping topological validity at every step [Gao et al. 2017]. No hex method is robust, high-quality and automatic at once [hex survey 2022], so all-hex output is limited to sweepable regions.

Boundary layers advance prisms along smoothed normals with exact collision tests and split thick curved layers isoparametrically [Marcon et al. 2019]. They serve turbulent flow from phase 4 (contract 13.4); phase 3 laminar heat transfer and mould filling resolve walls by octree refinement under FLX's rules.

### Adaptation and surface remeshing

Adaptation maps new cells to their parents as a compact parent-index array, so Flux transfers Fields by its own rules. Decimation uses quadric error metrics [Garland and Heckbert] but verifies each collapse against the original surface, and parallel modification uses deterministic independent sets. Quad mode follows feature-line driven quad remeshing, which fails on under 0.5% of Thingi10K models [Pietroni et al. 2021].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::mesh_from_triangles` | Buffers → Mesh, facet B-rep or point set | `NotManifold { edges, vertices }` | ANV-O-MESH-1 | 0 |
| `anvil::repair_mesh` | Triangle data → valid Mesh with displacement and area report | `Unrepairable { reason }` | ANV-O-MESH-2 | 1 |
| `anvil::tetrahedralize` | Body, sizing `Field<Body, Length>`, order, strategy, quality → volume Mesh, boundary bound | `InvalidInput`, `NotRepresentable`, `WorkLimit`, `QualityNotReached { worst, target }` | ANV-O-TET-1, ANV-O-HO-1 | 2 (`Conforming`, projected curving), 3 (`Envelope`, guarding) |
| `anvil::untangle` | Mesh → valid curved mesh | `InvalidElement { cell, jacobian_min }` | ANV-O-HO-1 | 2 |
| `anvil::hex_dominant`, `sweep_mesh` | Tetrahedra → hex-dominant; sweepable region → all-hex; optional `split_polyhedra` | `NotSweepable { reason, faces }` | ANV-O-HEX-1 | 3 (sweep), 4 (hex-dominant) |
| `anvil::boundary_layer` | Faces (`Query`), first height Field, growth, layers | `LayerCollapsed { faces, achieved_layers }` with the partial mesh | ANV-O-BL-1 | 4 |
| `anvil::refine_mesh` | Marked simplices → newest-vertex bisection with closure | `InvalidElement` | ANV-O-ADAPT-1 | 2 |
| `anvil::adapt_mesh`, `optimize_mesh` | Metric `Field<Body, Metric>` → adapted mesh, parent map; node relocation | `QualityNotReached` | ANV-O-ADAPT-1 | 3 |
| `anvil::polyhedral_mesh` | Tetrahedra → boundary-conforming polyhedral dual | `NonPlanarFace { cells, deviation }` | ANV-O-POLY-1 | 3 |
| `anvil::common_refinement` | Two discretizations of one interface → overlay with both parents | `NotSameInterface { gap }` | ANV-O-MESH-4 | 4 |
| `anvil::remesh`, `decimate`, `smooth` | Isotropic, metric or quad remeshing; verified-bound decimation; Taubin and bilaplacian smoothing | `FeatureConflict { edges }` with the closest feasible target | ANV-O-REM-1 | 1 (decimate), 2, 3 (quads) |
| `anvil::segment_mesh` | Mesh → face groups by curvature and normals | None: every mesh segments, at worst into one group | ANV-O-MESH-3 | 3 |

## Subdivision surfaces

Industrial designers shape freeform parts with subdivision cages, and Anvil keeps those shapes exact as B-rep faces instead of fitting them.

A `SubD` Body is a Catmull-Clark cage with semi-sharp creases, corner sharpness, boundary rules and an `EntityId` per cage element. It follows OpenSubdiv's conventions, whose limit matches RenderMan [OpenSubdiv repository]. Regular faces are bicubic B-spline patches, and crease-free neighbourhoods of one extraordinary vertex use Stam's exact eigen-analysis [Stam 1998].

Near creased extraordinary vertices, feature-adaptive subdivision [Nießner et al. 2012] runs until the irregular region's certified bound falls below ρ/2⁸. At the depth cap it stops and records the bound. Curvature at extraordinary vertices is reported as singular.

**Decision D-ANV-13:** Anvil implements Catmull-Clark subdivision with semi-sharp creases natively in Rust, following OpenSubdiv's rules and using OpenSubdiv as an oracle.
*Why:* limit surfaces must evaluate identically on CPU and in Wasm, and OpenSubdiv is C++ under the Tomorrow Open Source Technology License 1.0, which is not on Crucible's allowlist [OpenSubdiv license].
*Rejected:* linking OpenSubdiv, which needs FFI and an RFC and has no wgpu back end; Loop subdivision as the primary scheme, since triangle cages suit meshes, not industrial design.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::subd_edit` | Move, extrude, inset, bevel, crease, insert loop, bridge; untouched cage ids kept | `NonManifoldResult`, `ZeroArea` | ANV-O-SUBD-1 | 3 |
| `anvil::subd_limit` | Limit points, derivatives and normals at (face, u, v), with recorded bounds near creased extraordinary vertices | `SingularPoint` for curvature | ANV-O-SUBD-1 | 3 |
| `anvil::convert` (Mesh → SubD, SubD → BRep, SubD → Mesh) | Cage from a mesh; exact limit faces, or NURBS with certified bounds; limit tessellation | `ToleranceNotMet { achieved }` | ANV-O-SUBD-1, ANV-O-CONV-1 | 3 |
| `anvil::fit` (target SubD) | B-rep or mesh → cage by quad remeshing and least squares | `FitFailed { residual }` | ANV-O-FIT-2 | 4 |

## Planar integer geometry (`anvil-planar`)

Board layout and MEMS masks are checked by exact design rules, so their 2D geometry must pass those checks by construction, with no hidden tolerance.

`anvil-planar` stores 2D geometry on an integer grid declared per design; ELX uses nanometres within ±2⁴⁰ nm. Polygons have line and arc edges; an arc is an integer centre, an integer radius and integer start and end ray directions. Circles and round pads are exact, and an arc offset by an integer distance keeps its centre and rays, so concentric clearances stay exact.

Predicates are exact in integer arithmetic behind a floating-point filter, with square roots eliminated by repeated squaring. Over ELX's range, orientation and point–circle tests fit in 128 bits and point–segment distances in 192 bits. Predicates on arc–arc intersection points need up to 1,024 bits.

Offset lines and arc intersections are irrational, so they snap conservatively: a fill keeping clearance rounds inward, and a keep-out rounds outward. A reconstructed arc is kept only when the snapped arc passes the exact check; otherwise its polygonal approximation, snapped the same way, stands in its place. Imported three-point arcs convert by the same rule, so derived geometry passes the exact rule checks with no hidden tolerance.

The same crate compiles into ELX's design-rule, fill and router Wasm components, so both agree. Flex circuits bend with `anvil::fold`.

**Decision D-ANV-27:** `anvil-planar` makes predicates exact on stored integer geometry, stores arcs as an integer centre, radius and rays, and snaps every irrational construction conservatively in a declared direction.
*Why:* rounding to nearest could place a fill 0.7 grid units too close and fail Crucible's own checks, while centre and radius keep concentric clearances exact.
*Rejected:* three-point arcs, where every clearance offset snaps; a hidden check tolerance; arcs as segments, which lose exact arcs.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Exact planar predicates | Integer points, lines and centre–radius arcs → exact signs and distance comparisons | `Overflow` above the declared range | ANV-O-PLANAR-1 | 3 |
| `anvil::planar::boolean` | Polygon sets with arcs, n-ary expression → exact result | `Overflow` above the declared range | ANV-O-PLANAR-1 | 3 |
| `anvil::planar::offset` | Polygons, distance, snap direction → arcs offset exactly, lines snapped conservatively | `Collapsed { regions }` | ANV-O-PLANAR-2 | 3 |
| `anvil::planar::distance` | Two polygon sets → exact minimum distance comparison and witnesses | `Overflow` above the declared range | ANV-O-PLANAR-1 | 3 |
| `anvil::planar::medial_axis` | Polygons with arcs → segment Voronoi skeleton, conservatively snapped | `WorkLimit` | ANV-O-PLANAR-2 | 3 |

## Conversions, exchange and error propagation

Moving geometry between representations, or out to another program, is where accuracy is usually lost without anyone noticing; this section makes every such loss a stated, propagated bound.

`anvil::convert(body, into, accuracy)` is the only conversion operation. Every approximating conversion and fit records a `FaceBound { position, normal }` per face and an `EdgeBound { position, tangent }` per edge. Each is a two-sided Hausdorff bound and an angle bound, `Quantified` or `NotQuantified { reason }`.

Fits certify both bounds by certified sampling of distance and direction deviation. Later operations propagate them by the rules below. The symbols are:

- p_a and p_b, the position bounds of two source faces a and b, and n_a and n_b their normal-angle bounds; p and n for a single source face;
- θ_min, a certified lower bound on the angle between the faces along the edge;
- κ̂, a certified bound on their principal curvatures;
- s and φ, a spine's position and tangent bounds.

| Construction from bounded entities | Position bound | Direction bound |
| --- | --- | --- |
| Trim, split, imprint, Boolean (entity kept) | Unchanged | Unchanged |
| Normal offset by d with \|d\|·κ̂ ≤ 1/2 | p + \|d\|·n | Normal n |
| Normal offset by d with \|d\|·κ̂ > 1/2 | `NotQuantified { OffsetNotRegular }` | `NotQuantified` |
| Intersection edge, blend spine, contact curve, where max(p_a, p_b)·κ̂ ≤ sin²θ_min / 4 | √(p_a² + p_b² + 2·p_a·p_b·\|cos θ_min\|) / sin θ_min | Tangent (n_a + n_b) / sin θ_min, to first order |
| Intersection edge, blend spine, contact curve, otherwise (near tangency) | `NotQuantified { NearTangent { edge } }` | `NotQuantified` |
| Rolling-ball blend of radius r on a spine bounded by s and φ | s | Normal min(π, s/r + φ + max(n_a, n_b)) |
| Natural-offset corner where faces meet at angle θ | p / sin(θ/2) | Normal n |

The intersection row is the exact worst case for two displaced faces. Two perpendicular faces each moved by p in opposite senses move their common edge by p·√2, the value the corner row gives at 90°. Curvature adds a second-order term, so the row holds only where its condition keeps that term below the first-order one. Nearer tangency, a shift ε moves the crossing by about √(2ε/Δκ), which no angle rule bounds, so the edge is `NotQuantified`.

Direction bounds travel with positions (contract 5): a spine within distance s can tilt far more than s/r, turning the blend's normal. Offsets need κ̂ because a fitted face's curvature wiggles can self-intersect where the exact offset does not.

`body.error()` is the largest face position bound, or `NotQuantified` if any face is, and comparisons on an unquantified bound are `Undecided`. The bound is representation error only: `Approx` argument uncertainty goes to Ingot's `InputSensitivity` record.

**Decision D-ANV-21:** Lattice inclusions are exact; approximating conversions record per-face `{ position, normal }` and per-edge `{ position, tangent }` bounds, which propagate by stated rules with stated validity conditions or become `NotQuantified`.
*Why:* a Hausdorff bound alone says nothing about directions, so offsets, intersections and blends on approximated faces could report `Guaranteed` bounds that do not hold, and an intersection rule without a curvature condition fails near tangency.
*Rejected:* the largest source bound, which is false near tangency; max(p_a, p_b)/sin θ_min, which understates displacements of opposite sign; one bound per Body; RMS metrics, which hide the worst deviation; position-only propagation, which understates blend error.

A face S fitted to an implicit's zero set is certified on (u, v) boxes. Interval evaluation of f∘S bounds |f|, and a certified lower bound m on |∇f| in the band gives the one-sided distance |f|/m. A normal-cone test proves the closest-point map from the zero set to S one-to-one, bounding the other side. The angle between ∇f and S's normal bounds the normal.

Fitted faces arrive in phase 2, so that generative-design outcomes for milling and casting release through STEP (contract 13.4). Until then a converted implicit uses facet faces wherever no exact leaf face survives, which mesh-based processes accept.

**Decision D-ANV-36:** A face fitted to an implicit zero set is `Guaranteed` where the box certification succeeds, else `Estimated`, with facet faces as fallback.
*Why:* it reuses the gradient-cone certification of implicit meshing and proves both sides of the Hausdorff bound.
*Rejected:* sampled deviation, which misses features between samples; a one-sided bound, with which a fitted face could skip a thin wall.

### Exchange form and receiver profiles

Anvil's internal geometry is finer than any receiving program's. On GP1 the minimum size λ = 2⁴ρ is about 1.9 nm. That is below Parasolid's default tolerance of about 5 nm [Jackson 1995] and far below the micrometre tolerances many CAM and inspection programs use. A tolerant edge from healing or a contact curve may also exceed a receiver's tolerance and arrive as a gap.

`anvil::exchange_form(body, profile)` therefore writes for a named receiver. A receiver profile states the receiver's `tolerance` and `min_feature`. Named profiles ship with Crucible (ECO's `parasolid`, at a tolerance of 5 × 10⁻⁹ m), and an organization declares others, such as its reference shop's CAM and coordinate-measuring software.

1. Seams and poles are added where the receiver needs them, and new entities map to `EntityId`s.
2. Entities below `min_feature` are merged within the profile's tolerance, or the operation fails with `NotRepresentable { entities, reason: BelowReceiverResolution }`.
3. Every edge whose τ exceeds the profile's tolerance is reported in `Note::ToleranceAboveReceiver { edges }`.
4. Procedural faces become B-splines within a default bound: the smaller of the profile's tolerance and 1% of the tightest tolerance whose target includes the face. A profile tolerance on a fillet is thus never checked against a coarser approximation.

MEC's `export_resolution` check runs this report before any export Act.

**Decision D-ANV-39:** Exports go through `exchange_form` with a receiver profile that states the receiver's tolerance and minimum feature, merging or refusing entities below it, reporting tolerant edges above it and tying each approximation bound to the tolerances on the face.
*Why:* a valid Anvil Body can hold slivers and gaps that a shop's software treats as degenerate, and only the receiver's numbers say which.
*Rejected:* exporting at Anvil's own resolution, which ships nanometre slivers; one global export tolerance, which suits no receiver; approximating procedural faces to a fixed bound unrelated to their tolerances.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| BRep → Mesh | Tessellation with certified chord control; face groups keep canonical numbers | `WorkLimit { kind: Triangles }` | ANV-O-CONV-1, ANV-O-TESS-1 | 0 |
| BRep or Mesh → Implicit | Exact signed-distance leaf with winding-number sign; zero error | None: every B-rep and Mesh has an exact distance | ANV-O-CONV-1 | 1 |
| Mesh → BRep (facet) | Facet faces per face group, ids kept; zero error | None: every valid Mesh is a facet B-rep | ANV-O-CONV-1 | 1 |
| Implicit → Mesh | Certified dual contouring | `Uncertified` cells listed | ANV-O-CONV-1 | 1 |
| Implicit → BRep | Kept exact faces trimmed by certified intersection; facet faces elsewhere; fitted faces certified on boxes | `Ambiguous` near tangency; uncertified boxes listed | ANV-O-CONV-1, ANV-O-LEAF-1 | 1 (facet), 2 (fitted) |
| Mesh → BRep (fitted) | Segment, fit primitives and NURBS, intersect, sew; `Estimated`, or `Guaranteed` after a certified check | `FitFailed { residual }` | ANV-O-FIT-2 | 4 |
| BRep, Mesh or Implicit → SubD | Quad remesh and cage fit; `Estimated` | `FitFailed` | ANV-O-FIT-2 | 4 |
| Bound propagation | Rules above with their validity conditions, applied by every operation | `NotQuantified` entities listed | ANV-O-CONV-2 | 1 |
| `anvil::exchange_form` | Body, receiver profile (`tolerance`, `min_feature`) → seams, poles, B-spline approximations within tolerance-tied bounds, id map, report of tolerant edges | `NotRepresentable { entities, reason }`; `Note::ToleranceAboveReceiver { edges }` | ANV-O-NF-1, ANV-O-NF-2 | 1 |

## Measurement, analysis and simulation services

Checks, drawings, simulation and manufacturing all ask Anvil questions about geometry; this section lists the answers it gives and how each is bounded.

Mass properties integrate over trimmed faces by the divergence theorem. B-reps use adaptive Gauss–Legendre quadrature with interval-bounded remainders, meshes exact tetrahedron sums, and implicits adaptive octrees. Distance runs branch-and-bound over both hierarchies, then a Krawczyk test on the optimality conditions.

Signs for imperfect geometry come from generalized winding numbers on trimmed surfaces [Spainhour and Weiss 2025], following Axom, whose BSD-licensed implementation Anvil ports [Axom repository]. A far-field expansion makes some 10³-second evaluations sub-second [Spainhour, Whitlock and Weiss 2026].

Assembly interference culls Instance pairs with exact integer GPU tests and computes certified distances on the CPU. Boolean volumes are computed only for overlapping pairs, in canonical Instance order.

`anvil::thickness` proves the minimum by CPU branch-and-bound over the whole Body with certified lower bounds. GPU candidates only order the search and seed upper bounds that the CPU certifies, so a GPU changes speed, never the result. It reports the canonically first location within the decision band of the minimum: lowest face number, then (u, v) on a fixed dyadic grid.

`anvil::classify_edges(body, angle_tol)` returns a `Field<Edges, EdgeClass>` of `Convex`, `Concave { interior_angle }`, `Smooth { order }` or `Undecided`, decided by the round rule on certified dihedral enclosures. An edge with a `ContinuityCertificate` or a certified G1 enclosure within `angle_tol` is `Smooth`, so tangent fillet edges of imports are not flagged. Flux decides which concave edges are singular.

Hidden-line views follow one rule. The bound is 0.01 mm on the sheet divided by the view scale, and never coarser at model scale than the drawing's tightest tolerance divided by 10. A MEMS die drawn at 100:1 thus gets 0.1 µm, and a hull at 1:200 gets 2 mm unless a tolerance asks for less.

### Services for Flux

Anvil implements Flux's `GeometryQuery` for every representation: certified box classification, closest points, quadrature, local thickness, and shell and genus counts. Cut-cell quadrature follows Saye's height-function methods, with positive weights and high-order accuracy [Algoim]. Algoim's BSD licence adds a clause granting LBNL a licence to published enhancements [Algoim licence]; Anvil ports it to Rust with notices, records that grant-back, and uses Algoim as the quadrature oracle's reference.

Moment fitting is used only with non-negative least squares and a conditioning check. After a local edit, classification is recomputed only for octree cells that meet the region the edit's `HistoryRecord`s changed. `anvil::shape_velocity` returns `TopologyChange { parameter, entities }` instead of a velocity when a parameter changes B-rep topology; until it ships in phase 2, UIX ranks edit plans by provenance.

### Constraint solving

MEC owns constraint semantics; Anvil runs `solve_constraints` and `analyze_constraints` as `Portable` operations on `linalg`. Dulmage–Mendelsohn decomposition orders the system into blocks. A block of up to 128 unknowns uses dense rank-revealing QR or SVD. A larger block uses sparse QR with a rank-revealing pass on R, since a dense factorization of 2,000 unknowns costs about a second without FMA.

Certification reports how far the solved coordinates may be from the true root, and never fails a solve. The coordinates are exact `f64` inputs to Anvil either way; only a check needs the bound.

- A converged square block of up to 128 unknowns that passes a Krawczyk test has a unique solution on its branch, with the box radius as its `Guaranteed` bound, whatever its size.
- An under-determined block, resolved by minimum displacement, is certified the same way on that problem's square KKT system, which is regular at a strict minimizer.
- Larger blocks, and blocks whose test fails, get an `Estimated` bound: the residual over an estimated smallest singular value, from the factorization.
- A solve fails only when the box admits a different discrete configuration, an incidence, orientation qualifier or tangency side it does not decide, as `Ambiguous { block, qualifier }`. A check that needs a tighter bound returns `Undecided { needed }` through the one decision rule.

Near-singular sketches thus solve with an honest bound: a 0.05 mm chamfer on a 400 mm profile, nearly parallel lines meeting far away, a short arc between long tangent lines.

During a drag, which runs at `Interactive` fidelity, only the dragged entity's block and the blocks after it in decomposition order re-solve, without certification; the build certifies.

Rank diagnosis needs a witness where incidences and tangencies hold exactly, because rounding makes a rank-deficient Jacobian generically full rank. Anvil builds witnesses in decomposition order from rational choices, tangent points first and centres along normals after. Rank is computed modulo 61-bit primes, and a rational kernel vector certifies a deficiency. Where no rational witness exists, a nonzero interval minor at a Krawczyk-certified witness certifies full rank, and a deficiency is `Estimated` with its singular-value gap.

**Decision D-ANV-40:** Constraint blocks of up to 128 unknowns factor densely and certify by Krawczyk tests, larger blocks factor sparsely with `Estimated` residual bounds, drags re-solve only downstream blocks without certification, and a solve fails only on an undecided discrete configuration, never on the width of its bound.
*Why:* bound width says how far coordinates are from the root, which matters to checks and not to geometry, and dense O(n³) work on large blocks misses the drag targets.
*Rejected:* failing when the bound exceeds the smallest entity tolerance, which refuses ordinary near-singular sketches; dense factorization up to 2,000 unknowns; certifying every block on every drag step.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `anvil::mass_properties` | Volume, area, mass, centroid, inertia, each with a bound | None: bounds widen instead of failing | ANV-O-MP-1 | 0 (meshes), 1 |
| `anvil::distance`, `closest_point` | Minimum or signed distance, witnesses with canonical number and (u, v) | `NotSeparated` when positive distance is required | ANV-O-DIST-1, ANV-O-DIST-2 | 0 (points), 1 |
| `anvil::interference` | Instances, clearance → separated, touching, clearance or overlapping pairs | `WorkLimit` | ANV-O-DIST-3 | 1 |
| `anvil::ray_cast` | Rays → first hits with canonical number, (u, v), normal | None: a ray that hits nothing returns no hit | ANV-O-DIST-4 | 1 |
| `anvil::deviation` | Two Bodies → signed deviation Fields, Hausdorff bounds, volumes added and removed, topology equality in normal form by `EntityId` | `WorkLimit` | ANV-O-DIST-5 | 1 |
| `anvil::classify_points`, `classify_box`, `classify_body` | Inside, outside, on or cut, certified with tolerances | None: every query has a certified class | ANV-O-CLS-1, ANV-O-CLS-2, ANV-O-CLS-3 | 0 (points), 1 |
| `anvil::classify_edges` | Body, angle tolerance → `Field<Edges, EdgeClass>` | None: `Undecided` is a class | ANV-O-EDGE-1 | 1 |
| `GeometryQuery` | Classification, closest point, positive-weight quadrature, thickness, topology counts | `Uncertified { achieved }` | ANV-O-QUAD-1 | 1 |
| `anvil::shape_velocity` | Parameter → `Field<Faces, Displacement>` per unit change | `TopologyChange { parameter, entities }` | ANV-O-SV-1 | 2 |
| `anvil::curvature`, `analyze_continuity`, `isophotes` | Curvature Fields; G0 to G3 mismatch along edges with per-order default thresholds; isophote and reflection lines | `SingularPoint` | ANV-O-AN-1, ANV-O-AN-2 | 1 (G0 to G2), 2 (G3, isophotes) |
| `anvil::draft_analysis`, `draft_map` | Draft-angle Fields and classified regions; feasible draw directions | None: every face has a draft angle | ANV-O-AN-3 | 1, 3 (`draft_map`) |
| `anvil::thickness` | `Sphere` or `Ray` thickness Field; minimum proved on the CPU at a canonical location; `Certified` | `WorkLimit` | ANV-O-AN-4, ANV-O-THK-1 | 1 |
| `anvil::medial_axis` | Planar regions → exact segment Voronoi skeleton; solids → certified approximation | `WorkLimit` | ANV-O-AN-5 | 1 (2D), 2 (3D) |
| `anvil::silhouette`, `project_hlr`, `visibility` | Silhouettes; certified hidden lines within 0.01 mm on the sheet divided by the view scale, never coarser than the tightest tolerance divided by 10; exact projection of lines, circles and conics; implicit regions drawn by their boundary; visibility Fields | `WorkLimit` | ANV-O-AN-6, ANV-O-AN-7 | 1 (silhouette, hidden lines), 2 |
| `anvil::tessellate` | Body, chordal tolerance → `DisplayPackage` identified by (`GeometryId`, chordal error, encoding version), with canonical-number back-references, each edge sampled once, and the face table from the name part; no status inside | `WorkLimit { kind: Triangles }` | ANV-O-TESS-1 | 1 |
| `anvil::cluster_dag` | Pages → deterministic cluster DAG with monotone error bounds | `WorkLimit { kind: Clusters }` | ANV-O-TESS-2 | 2 |
| `anvil::tool_contact`, `swept_volume` | First contact of revolved tools; exact per-move envelopes; narrow-band stock | `WorkLimit` | ANV-O-MFG-1, ANV-O-MFG-2 | 2 |
| `anvil::offset_curve` | Planar or on-surface curves; lines and arcs stay lines and arcs | `Degenerate` | ANV-O-MFG-3 | 1 |
| `anvil::voxelize`, `correlate_grids` | Occupancy or distance grids; exact integer correlation counts (`Certified`) | `WorkLimit { kind: Voxels }` | ANV-O-VOX-1, ANV-O-VOX-2 | 1, 2 |
| `anvil::align`, `fit` | Point-to-plane alignment with deterministic samples; primitive, NURBS or cage fits with residuals | `NotConverged { rms }`, `FitFailed { residual }` | ANV-O-FIT-1, ANV-O-FIT-2 | 1 (primitives), 4 |
| `anvil::solve_constraints`, `analyze_constraints` | MEC's systems → solved blocks with `Guaranteed` or `Estimated` bounds, degrees of freedom, exact or interval-certified ranks, conflicts | `Ambiguous { block, qualifier }`, MEC's kinds | ANV-O-SOLVE-1 | 1 |

## Fidelity, determinism and performance

An engineer should see geometry update while dragging and get release-quality geometry without waiting for a second computation; this section explains how one computation serves both, on every machine.

### Fidelity

| Fidelity | Anvil's behaviour | Cache |
| --- | --- | --- |
| `Preview` | Looser tolerances, surrogates (an implicit offset for a blend), GPU `f32` evaluation; results are `Ready(Preview)` | Never in the shared cache |
| `Interactive` and `SignOff` | One computation: certified decisions, certified seeding, branches traced from canonical start points with floating-point step validation, then `check_body` | Cached once for both fidelities |
| `SignOff` certification | A certification node per geometric result: certified seeding finds exactly the traced branches, and a Krawczyk test confirms each traced point | Cached; consumed only by `SignOff` demands |

Decisions never depend on fidelity, and traces depend only on the branch, so the only thing `SignOff` adds is proof that the traced points are right. A `SignOff` demand waits for the certification node. When it confirms, the value and its bits stand, and every dependent already computed stays valid. A failure is rare and deterministic for given inputs. The node then returns the operation recomputed with certified tracing, Kiln treats it as the operation's value at both fidelities from then on (KLN), and dependents recompute.

Geometry therefore has one identity across `Interactive` and `SignOff`, and Flux reuses meshes across fidelities. From phase 2, `Interactive` may also seed by GPU sampling after a favourable freedom-to-operate opinion; certification then checks those seeds too.

**Decision D-ANV-28:** `Preview` uses surrogates; `Interactive` and `SignOff` share one computation with certified decisions and canonical traces, and `SignOff` adds a certification node that confirms the result in place and recomputes only when confirmation fails.
*Why:* contract 7.1 allows no fidelity exception for decisions, a trace that depends only on its branch makes the fast result reproducible, and confirming it is far cheaper than computing every downstream mesh, solve and drawing twice.
*Rejected:* floating-point decisions at `Interactive`; a separate `SignOff` recomputation with different bits, which doubles the graph; certified tracing everywhere, which misses the rebuild targets; unvalidated results.

### Determinism

Beyond contract 7.3, Anvil uses canonical orders, decision rounds, `det_sum` and `exact_sum` reductions, local work limits and no NaN at any boundary. Mesh modification runs in rounds of independent sets prioritized by a hash of each element's geometric key and the round.

**Decision D-ANV-22:** Anvil parallelizes by data-defined decomposition with canonical merge order, fixed reduction trees and geometric independent-set priorities.
*Why:* it gives identical bits for any thread count without locks around floating-point state.
*Rejected:* a single-threaded certified mode, which misses the rebuild targets; colouring or randomized schedules, where results follow thread count or seeds.

Work splits by data (patch pairs, octree cells, faces), and SIMD uses PLT's canonical lanes. The GPU runs integer broad phases, preview tessellation and evaluation, the WGSL tape interpreter and `correlate_grids`, each with a registered CPU path.

**Decision D-ANV-35:** GPU floating-point results only order work, propose candidates that the CPU certifies, and preview, and only exact integer GPU tests prune.
*Why:* WGSL fixes no rounding mode and permits flushing and reassociation [WGSL], so GPU intervals cannot be proven conservative, and a missed candidate would change a global result such as a minimum thickness.
*Rejected:* widened GPU intervals, unproven on every driver; GPU pruning with CPU spot checks, which makes results depend on the GPU.

### Performance targets

PLT owns contract 13.3's rows, measured on the reference laptop. Anvil's shares and operation targets:

| Workload | Target |
| --- | --- |
| Rebuild after an early edit, GP1-class prismatic benchmark (2 s row) | Anvil share ≤ 1.2 s at `SignOff`, since analytic pairs certify in closed form |
| 200-feature corpus from the licence-filtered ABC subset (p90 10 s row) | Anvil share ≤ 7 s p90 at `Interactive`; certification nodes p90 ≤ 30 s |
| Boolean of two 500-face analytic and NURBS bodies | ≤ 200 ms at `Interactive` |
| 50-edge constant-radius fillet chain | ≤ 500 ms at `Interactive` |
| Global separation check after shelling a 500-face part to 1 mm walls | ≤ 200 ms at `Interactive` |
| Tessellation of a 10,000-face part at 0.01 mm chord | ≤ 200 ms |
| Interference of a 1,000-part assembly from warm cache | ≤ 1 s |
| Conforming tetrahedralization of 10⁶ elements | ≤ 10 s on 8 cores |
| Flux interactive update, Anvil stages | Rebuild ≤ 150 ms; classification and distance ≤ 200 ms |
| GP2 lattice sections at 50 µm, no global mesh | ≤ 60 s, peak memory ≤ 2 GiB |
| GP2 lattice mesh export at 2 × 10⁷ triangles | ≤ 60 s on the high band |
| Million-triangle mesh Boolean | Set by the phase 0 bake-off |

Before these targets freeze, a phase 0 spike measures certified SSI and Boolean costs on licence-filtered ABC face pairs and publishes per-operation budgets.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `Preview` fidelity | Surrogates and GPU evaluation; never in the shared cache | None: a `Preview` result that cannot form shows as `Stale` | ANV-O-FID-1 | 1 |
| `Interactive` fidelity | Certified decisions and canonical traces, validated by `check_body`; one effective fidelity with `SignOff` | Validation failure recomputes with certified tracing | ANV-O-FID-1 | 1 |
| `SignOff` certification in place | Certification node confirms seeding and traced points; success keeps the bits, failure recomputes | `Ambiguous` where certified tracing cannot decide | ANV-O-FID-1 | 1 |
| Deterministic parallel scheduling | Identical bits for any thread count, ISA level and GPU presence | None: schedules are data-defined | ANV-O-DET-1 | 0 |
| GPU roles | Ordering, CPU-certified candidates and previews; integer pruning only | Device loss is an Abort; Kiln reruns on the CPU path | ANV-O-DET-1, ANV-O-THK-1 | 1 |
| Performance budgets | The targets above, per merge batch | Regressions in deterministic work counts block merges | ANV-O-PERF-1 | 1 |

## Behavior versions

A design released today must rebuild with the same bits in ten years, after Anvil has changed many times; behavior versions make that true.

A behavior version (`anvil::blend@2`) fixes an operation's output for every input. Any change to output bits, history, `EntityId`s or error kinds needs a new version. A design pins versions in `ingot.lock` (`anvil.blend = 2`), and a call may override with `op: anvil::blend@1`.

Each operation family is its own crate (`anvil-op-blend`), and each released version is a frozen source directory inside it (`src/v2/`). That directory depends only on versioned first-party path dependencies (`anvil-geom-v5`, `linalg-v3`) and exact third-party versions, so Cargo computes everything the version depends on. Its closure hash covers the frozen directory, its first-party dependencies' frozen directories and the `Cargo.lock` checksums of its third-party dependencies (contract 4). KLN's registration refuses a version whose hash changed, so even a security fix ships as a new version.

Each family crate registers its versions with KLN's operation registry through an explicit `register` function, in canonical order. Versions go from `Current` to `Deprecated` (native for at least five years) to `Retired`. Retired versions run unchanged in archived engine builds compiled to Wasm, through the frozen world `crucible:archive/op@1` (KLN). No Anvil operation is `ClassExact`, so none ever fails with `OpVersionRetired`.

`crucible upgrade anvil::blend` produces a Proposal with a geometry overlay, metric deltas, changed checks and every `ResolveError`.

**Decision D-ANV-18:** Each Anvil operation family is its own crate, a released version is a frozen source directory depending only on versioned first-party crates and exact third-party versions, and its closure hash is computed from Cargo's metadata and lockfile (contract 4).
*Why:* frozen source rebuilds old designs by construction, which no regression corpus can promise, and Cargo already knows the full dependency closure that a module-level hash cannot enumerate through generics, trait impls and inlining.
*Rejected:* versioning only the public operation, where a shared fix changes old versions; a closure listing chosen modules, which misses `anvil-topo`, third-party crates and `std`; a corpus fingerprint alone, which misses changes outside the corpus; keeping old binaries.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Operation registry | Each family crate registers name and version with KLN's registry; status `Current`, `Deprecated`, `Retired` or `Yanked` (executable for audit, failing release checks) | `UnknownOperation`; `Note::DeprecatedBehavior` | ANV-O-VER-1 | 0 |
| Frozen versions and closure hashes | One crate per family; frozen version directories; closure hash and golden output hashes per version | Registration refused; merge blocked | ANV-O-VER-1 | 0 |
| Retired versions | Archived engine build compiled to Wasm, called through `crucible:archive/op@1`, identical bits | None: no Anvil operation is `ClassExact`, so none fails with `OpVersionRetired` | ANV-O-VER-1 | 1 |
| `crucible:geom/types` | `body` and `entity` handles, `geometry-id`, `error-bound`, `face-bound`, `edge-bound`, `heal-policy`, `history-record` | None: type definitions cannot fail | ANV-O-WIT-1 | 1 |
| `crucible:geom/build` | Builders validated by `anvil::build`; measures through `crucible:ops/anvil` (contract 4) | `invalid(violations)`, `work-limit` | ANV-O-WIT-1 | 1 |
| `crucible:ops/anvil` | One generated function per operation version | That operation's `OpError` kinds | ANV-O-WIT-1 | 1 |

## Reference

### Crates

| Crate | Contents | Depends on |
| --- | --- | --- |
| `anvil-geom` | Predicates, intervals, affine forms, tolerances, curves and surfaces, local solvers, fitting | `base-id`, `base-value`, `detmath`, `simd`, `runtime`, `gpu`, `linalg`, `kernels` |
| `anvil-topo` | Cellular topology, attributes, certificates, `HistoryRecord`, lineage, `anvil::resolve`, `check_body`, the encoding | `anvil-geom` |
| `anvil-planar` | Integer-coordinate 2D geometry with lines and arcs | `anvil-geom` |
| `anvil-mesh` | Surface, point-set and volume meshes, subdivision cages | `anvil-topo`, `field` |
| `anvil-implicit` | The implicit node set over `kernels::expr`, tapes, evaluators, brick cache, implicit meshing | `anvil-mesh`, `field`, `kernels` |
| `anvil-ops` | The `Body` enum and dispatch, `GeometryQuery`, the `Classify` implementation | the crates above |
| `anvil-op-<family>` | One crate per operation family (`anvil-op-boolean`, `anvil-op-blend`, `anvil-op-shell`, `anvil-op-ssi`, …), each holding its frozen version directories and a `register` function | `anvil-ops`, `base-op`, versioned first-party crates |

`base-id` holds the identity and handle types (`GeometryId`, `EntityId`, `BodyHandle`, `InstancePath`), `base-value` the `Classify` trait that `anvil-ops` implements for `field`'s `Sampler`, and `base-op` the operation contract (contract 12).

**Decision D-ANV-1:** Anvil's crates are `anvil-geom`, `anvil-topo`, `anvil-planar`, `anvil-mesh`, `anvil-implicit`, `anvil-ops` for the `Body` enum and dispatch only, and one `anvil-op-<family>` crate per operation family, all above `base-*`, `field` and `kernels` and all `forbid(unsafe_code)`.
*Why:* contract 12 orders the layers and confines `unsafe`, handles let `field` sample Bodies without an upward dependency, and a crate per family lets parallel builders work on blends, Booleans and shells without editing one crate, and gives each released version a Cargo-level closure.
*Rejected:* one `anvil-ops` crate holding every operation, a hot spot whose edit-and-test loop grows with every family; an `anvil-subd` crate, which adds no structure; `unsafe` SIMD in Anvil; `Body` in `base`, which would need every representation.

### Rust surface

```rust
pub struct FaceBound { pub position: Component<Length>, pub normal: Component<Angle> }
pub struct EdgeBound { pub position: Component<Length>, pub tangent: Component<Angle> }
pub struct Body { repr: BodyRepr, frame: Frame, resolution: Length, regions: Regions, meta: Arc<BodyMeta> }
pub enum BodyRepr { BRep(Arc<BRep>), Implicit(Arc<Implicit>), Mesh(Arc<Mesh>), SubD(Arc<SubD>) }
pub struct ContinuityCertificate { pub order: Continuity, pub certified_by: (OpId, u32) }

impl Body {
    pub fn geometry_id(&self) -> GeometryId;     // geometry part only
    pub fn definition_digest(&self) -> Digest;   // definitional attributes by canonical number
    pub fn object_id(&self) -> ObjectId;         // full canonical encoding
    pub fn error(&self) -> Component<Length>;    // largest face position bound
}

pub struct OpError {
    pub kind: OpErrorKind,          // canonical kind names; MEC's FeatureError cites them
    pub why: String,
    pub fixes: Vec<FixTemplate>,    // SourcePatches after relabeling
    pub at: Vec<EntityRef>,         // canonical numbers, then EntityIds after relabeling
    pub partial: Option<Body>,      // diagnostic only
}
impl From<OpError> for Failure { /* code "anvil/<kind in snake_case>" */ }
// Every operation: fn eval(&self, cx: &OpCx, inputs: Self::Inputs) -> OpResult<Self::Outputs>;
```

`Length` and `Angle` are the typed views generated from ING's kind table over the erased `DynQuantity` (contract 5). `Failure`, `Abort`, `Stop` and `OpResult` are KLN's, in `base-op`; Anvil never converts an Abort into a `Failure`.

### WIT packages and contract crates

Anvil owns the WIT (WebAssembly Interface Types) package `crucible:geom` and the generated interface `crucible:ops/anvil`; ECO keeps the index. Examples use `@0.1.0` until names clear and packages freeze (contract 13.1).

For each work item, the oracle role writes `anvil-op-<family>-contract` from this Rust surface, with `unimplemented!()` bodies (contract 13.2). Anvil's oracles bind, in order of preference, to `api` methods and file formats, then to `crucible:ops/anvil`, then to contract crates.

## State of the art

Figures in the last column are targets unless quoted, and ABC data means the licence-filtered subset (contract 13.3). Benchmarks run only open implementations, such as OCCT, Manifold, Geogram and fTetWild. The part-level parity corpus compares Anvil's results with stored Parasolid results that the ABC dataset publishes, and the parity table compares documented features; neither runs a commercial kernel. Incumbent behaviour beyond documentation is studied only through the clean-room insight protocol (contract 7.7).

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Predicates | Adaptive expansions [Shewchuk 1997]; indirect predicates [Attene 2020] | Shewchuk's public-domain C; Geogram, BSD-3-Clause [Geogram repository] | Link `robust`, generate indirect predicates (D-ANV-5); Geogram as oracle | Bit-identical to `robust` and within 1.2× of Shewchuk's C; exact against rationals |
| Mesh Booleans | Local arrangements [EMBER 2022]; indirect-predicate arrangements [Cherchi et al. 2022]; exact Weiler model [Lévy 2024]; topological aggregation [trueform 2026] | Manifold, Apache 2.0 [Manifold repository]; EMBER's 1.6 ms geometric mean on 1,000 Thingi10K pairs | Bake-off ranked by failures (D-ANV-20); Manifold and Geogram as oracles | Thingi10K [Thingi10K 2016] pairs and thingiCSG with zero failures and 100% valid; time set by the bake-off |
| B-rep Booleans and tolerances | Imprint, join and select with local tolerances [Jackson 1995] | Parasolid, ACIS, CGM with polyhedral add-ons [ACIS Polyhedra; CGM Modeler]; OCCT 8.0, LGPL 2.1 with an exception [OCCT repository; OCCT 8.0] | Build (D-ANV-4, D-ANV-19); OCCT as differential oracle | Part-level parity against Parasolid's stored results [ABC dataset page]: 98% at phase 1, 99.5% at phase 2; ABC pairs [ABC 2019] with coincident and tangent cases 100% valid |
| Surface–surface intersection | Topology-guaranteed SSI [Yang et al. 2023]; interval algebraic topology [Cheng et al. 2023] | ACIS, OCCT and SISL as compared by Yang et al. | D-ANV-16, closed class list (D-ANV-37) | Correct topology on hard-case families and ABC face pairs; ≤ 2× OCCT time on transversal pairs |
| GPU acceleration of SSI | GPU box hierarchies [Krishnamurthy et al. 2008]; thresholded sampling, patented [US12229885B1] | Zoo's engine (its application is open source; the engine is not stated to be) [Zoo Design Studio v1] | D-ANV-17, from phase 2 | Identical output with and without a GPU; ≥ 3× over the CPU path |
| Blends | Rolling-ball and setback vertex blends [Várady publication list] | Parasolid, whose results are the corpus originals [ABC dataset page]; OCCT's fillet builder, which rejects contour ends where four or more edges meet [OCCT MakeFillet] | Staged program (D-ANV-29) | Fillet slice of the parity corpus: stage 1 at 99% (phase 1), stages 1 and 2 at 99.7% (phase 2), all stages at 99% (phase 3) |
| Implicit evaluation | GPU interval pruning [Keeter 2020]; Lipschitz pruning [Barbier et al. 2025]; affine range analysis [Sharp and Jacobson 2022] | Prospero's NEON interpreter at 0.29 ms [Prospero]; Fidget, MPL 2.0 [Fidget]; nTop, whose 5.0 kernel may regenerate geometry differently [nTop whitepaper; nTop 5.0 notice] | D-ANV-11; Fidget and libfive [libfive repository] as benchmarks | Prospero 1024² within 2× of 0.29 ms |
| Implicit meshing | Manifold dual contouring; occupancy-based dual contouring [Hwang and Sung 2024] | libfive; Fidget | Certified adaptive dual contouring | Hausdorff error against dense references; 100% manifold |
| Tetrahedral meshing | Conforming CDT [Diazzi et al. 2023]; envelope meshing [fTetWild 2020] | TetGen (378 failures of 4,408); fTetWild, MPL 2.0 [fTetWild repository]; Attene's CDT [MarcoAttene/CDT] | Build both | 4,408 valid Thingi10K models: 100% success, within the published 4.3 s mean |
| Curved and hex-dominant meshes | 3D Bézier guarding [Khanteimouri and Campen 2023]; bijective coarse meshes [Jiang et al. 2021]; field-guided agglomeration [Gao et al. 2017; hex survey 2022] | bichon, MIT with GPL CGAL dependencies [Jiang et al. 2021]; Gao et al.'s code, MIT [Gao et al. code] | Build | 100% positive Jacobian coefficients; element count against bichon; hex fraction |
| Boundary layers | Semi-structured curvilinear layers [Marcon et al. 2019] | NekMesh in Nektar++, MIT [Nektar++ licence] | Build | First-layer height within 5% on 95% of faces |
| Remeshing and decimation | Feature-line driven quad remeshing [Pietroni et al. 2021]; quadric error metrics [Garland and Heckbert] | The authors' published results; meshoptimizer's simplifier, MIT [meshoptimizer repository] | Build with verified bounds | ≤ 0.5% quad failures on Thingi10K; Hausdorff error at fixed budgets |
| Subdivision | Feature-adaptive limits [Nießner et al. 2012]; exact evaluation [Stam 1998] | OpenSubdiv, under TOST-1.0 [OpenSubdiv repository; OpenSubdiv license] | Build (D-ANV-13) | Limits within 10⁻¹² relative of OpenSubdiv |
| Containment and signed distance | Generalized winding numbers [Jacobson et al. 2013; Spainhour and Weiss 2025; Spainhour, Whitlock and Weiss 2026] | Axom, BSD-3-Clause [Axom repository] | Port, certified near the surface | Classification at ±τ/2 and ±2τ; time per query against Axom |
| Cut-cell quadrature | Saye's height-function quadrature [Algoim] | Algoim, BSD with a grant-back clause [Algoim licence] | Port to Rust, recording the grant-back; Algoim as oracle | Positive weights; exact on polynomials to the rule's degree |
| 2D triangulation | Constrained Delaunay with exact predicates | `spade`, MIT or Apache-2.0 [spade repository] | Link for planar faces and regions | Valid, deterministic triangulations in canonical order |
| GPU NURBS evaluation | Elastic tessellation [ETER] | ETER, CUDA, 3.7 million patches at 30 fps | wgpu `f32` for previews and display | 10⁶ patches at 30 fps (no tensor cores through wgpu) |
| Mesh repair and offsets | Arrangements with winding numbers [Jacobson et al. 2013; Cherchi et al. 2022]; mitered offsets [Cao et al. 2024] | Geogram [Lévy 2024]; methods Cao et al. compare | Build | Every Thingi10K model repaired valid; offset error |
| Persistent naming | Combined topology and geometry identification [persistent naming review 2018] | FreeCAD 1.0's toponaming mitigation [FreeCAD 1.0 release] | D-ANV-14, D-ANV-15, D-ANV-34 | Zero silent re-selections (ANV-O-NAME-2); Git round trips (ANV-O-SITE-1) |
| Rust kernels | NURBS topology with Booleans [Truck repository] | Truck, Apache 2.0; Fornjot, archived 19 June 2026, "goals were never reached" [Fornjot repository] | Not adopted; Truck as test vectors and a benchmark | Every capability tied to a golden product and an oracle |
| Supporting crates | Correctly rounded math [correct rounding page]; arenas [slotmap docs]; intervals [inari docs] | CORE-MATH; `slotmap`, Zlib; `inari`, MIT | `detmath` (PLT); reuse `slotmap`; `inari` as reference | Bit identity on every Tier 1 target |

**Decision D-ANV-23:** Anvil builds its kernel natively in Rust and links no external geometry kernel; it links the permissive `robust` and `spade` crates, ports from Axom, Geogram and Algoim with notices, and uses OCCT, Manifold, Truck, Geogram, OpenSubdiv, fTetWild, Gmsh, libfive, Fidget and Axom as oracles and benchmarks outside the core.
*Why:* the core must be Rust, GPL-free and identical in native and Wasm builds, small permissive crates save work without giving up control of numerics, and independent oracles catch errors that self-tests miss.
*Rejected:* wrapping OCCT, with LGPL linking and no control of numerics or naming; building on Truck, which has no cellular topology, tolerances or provenance; linking OpenSubdiv, whose licence needs an RFC.

**Parity with incumbents.** An engineer leaving an incumbent should find each kernel capability they rely on, by the phase the parity floor names (contract 13.4).

| Capability | Incumbent and its documented feature | Crucible's capability row and phase | Status |
| --- | --- | --- | --- |
| Solid modelling with Booleans and local tolerances | Parasolid: local tolerances [Jackson 1995]; ACIS: "Boolean, Blending, Direct Editing, Thickening, Offsetting" [ACIS product page] | `anvil::boolean`, phase 1 | Ahead: every decision certified and order-free, the same bits on every machine |
| Rebuilding the parts users already have | Parasolid built every model of the ABC dataset [ABC dataset page] | Part-level rebuild parity, phase 1 | Equal by target: 98% of in-scope parts at phase 1 and 99.5% at phase 2, measured on Parasolid's own results |
| Fillets, chamfers and vertex blends | Onshape's `fillet` and `chamfer` features [Onshape FeatureScript library]; ACIS blending [ACIS product page] | `anvil::blend`, stages 1 to 4, phases 1 to 4 | Equal for stages 1 and 2 at phase 2; Later for corners of valence four and above (phase 3) |
| Shell, thicken, draft and offset | Onshape's `shell`, `thicken` and `draft` features [Onshape FeatureScript library] | `anvil::shell`, `thicken`, `draft`, `offset`, phase 1 | Equal, with a stated default for shells past a fillet radius |
| Lofts, sweeps and free-form surfaces | Onshape's `loft` and `sweep` features [Onshape FeatureScript library] | `anvil::loft`, `sweep`, surfaces, phase 2 | Later: phase 1 serves prismatic and printed parts, and these need the free-form intersection class |
| Direct editing | Parasolid: "solid modeling, direct editing and free-form surface/sheet modeling" [Parasolid product page] | `anvil::move_faces` and related edits, phase 2 | Later: phase 1 edits go through source, which agents author |
| Mixed exact and facet models | Parasolid Convergent Modeling [Parasolid convergent modeling]; ACIS Polyhedra [ACIS Polyhedra] | Representation lattice, phase 1 | Ahead: implicit is a fourth representation, and exact faces keep their names and PMI inside lattices |
| Lattices | Parasolid editing of "lattices" [Parasolid product page]; nTop implicit modelling [nTop whitepaper] | `anvil::lattice`, phase 1 | Ahead: certified meshing and leaf-preserving exact faces |
| Healing and sewing | ACIS "verifying, and healing" [ACIS product page] | `anvil::heal`, `sew`, phase 1 | Equal, with every fix listed and healing capped below the smallest feature |
| Hidden lines and tessellation | Parasolid: "precise hidden line" and "versatile tessellation" [Parasolid product page] | `project_hlr`, `tessellate`, phase 1 | Equal, with a certified line bound and watertight display meshes |
| Subdivision modelling | Fusion's Form workspace [unverified] | `anvil::subd_edit`, phase 3 | Later: no phase 1 or 2 gate needs freeform styling |
| Generative-design outcomes as exact solids | Fusion: milling on "2.5-, 3- or 5-axis", 2-axis cutting and casting [Fusion GD methods] | Fitted Implicit → BRep, phase 2 | Equal at phase 2, with kept interfaces exact and named |
| Finding duplicate parts | Teamcenter's Geolus finds "similar parts even if one person calls it a fastener while another person calls it a clip" [Geolus shape search] | `GeometryId`, phase 0; KLN's duplicate and similarity search, phase 2 | Ahead for exact duplicates across every repository; Equal for similarity at phase 2 |
| Persistent naming | FreeCAD 1.0's toponaming mitigation [FreeCAD 1.0 release] | `EntityId`, `anvil::resolve`, phase 0 | Ahead: names from source text, typed errors with compiling fixes, no silent re-selection |
| Parametric solids in AI-built clones | SolidCraft, on Truck, ships fillet and chamfer, shell, draft, combine and split, and STEP and IGES exchange [SolidCraft repository] | The phase 1 rows above | Ahead: certified decisions, per-entity tolerances, stable names and oracles that a clone on Truck lacks |

## Platform notes

| Risk | Platforms | Decision |
| --- | --- | --- |
| Elementary functions differ between libraries | All | Only `detmath`; a lint bans Rust's `sin` and `exp`, whose precision the documentation calls non-deterministic [Rust f64 docs] |
| No hardware FMA at x86-64-v2, none deterministic in Wasm | x86-64 baseline, browsers | Dekker splitting on wasm32, `mul_add` by ISA level elsewhere; identical error terms |
| Flush-to-zero set by a foreign library | Native | Operation entry asserts the IEEE default state |
| Non-deterministic NaN bits [RFC 3514; Wasm nondeterminism] | All | Finiteness checked at every construction; the encoding rejects NaN and infinity |
| Relaxed SIMD may differ; Wasm 3.0 offers an optional deterministic profile [Wasm 3.0] | Browsers, Wasm components | Never emitted |
| No JIT for downloaded code | iPadOS | The web build runs in WKWebView (contract 7.4); interpreted tapes need no JIT |
| GPU driver variance and timeout resets | All GPUs, Windows | GPU results never canonical; known-answer tests per pipeline (contract 7.3); chunked dispatches; device loss is an Abort |
| Browser engine module size | Browsers | Operation families that golden-product traces touch land in the primary module; the others load as secondary modules on first use (contract 9) |

## Interfaces with other subsystems

| To | What | Types | Phase |
| --- | --- | --- | --- |
| ING | Versioned operations with roles and `Query` uses; `resolve` with the `accept` set and `query_stability`; `EntityId`s unchanged across `realize` points; constraint solves; `text_outline` | `Body`, `EntityId`, `HistoryRecord`, `ResolveError`, `OpError` | 0; 1 (`query_stability`, constraint solves, `text_outline`) |
| KLN (Kiln) | Operation implementations per family crate with grades, fidelity maps, cost estimates, closure hashes and explicit registration; two-stage keys; certification nodes; deterministic outcomes as `Failure`s | `GeometryId`, `ObjectId`, `OpResult` | 0 |
| KLN (`repo`, `plm`) | Interference, touched sets and deviation for merges; `GeometryId`s and definition digests for `ItemDefinition`s; `GeometryId`s for exact-duplicate search | `Body`, `EntityId`, `GeometryId` | 1; 2 (duplicate search) |
| FLX | `GeometryQuery`; `classify_edges`; mid-surfaces, member axes and strut graphs; meshing and adaptation by canonical number; `shape_velocity`; `implicit_from_field`; `common_refinement`; the implicit node set over `kernels::expr` | `Body`, `Field`, `FaceBound`, `EdgeBound` | 1; 2 (mid-surfaces, swept-member axes, meshing, `shape_velocity`); 3 (metric adaptation); 4 (`common_refinement`) |
| COV | Implicit and lattice Bodies; mid-surfaces and member axes; per-entity tolerances; curvature and thickness queries | `Body` | 1 |
| MEC | The operations catalog with roles, phases and canonical `OpError` kinds; blend stages and parity targets; attribute classes; constraint solving with bounds; `exchange_form` reports for `export_resolution`; lattice regions for drawings; control-vertex previews | `Body`, `EntityId`, `Field`, `OpError` | 1; 3 (previews) |
| MFG | Sections, offset curves, medial axes, tool contact, swept volumes, interference, draft maps, thickness, voxels, fitting; toolpath wire Bodies | `Body`, `Field` | 1; 2 (tool contact, swept volumes) |
| ELX | `anvil::planar` with centre–radius arcs and conservative snapping; `fold`; `convex_decompose`; `text_outline` | `Body` | 1 (`text_outline`); 3 |
| UIX | `DisplayPackage` pages and face table, identified without status; `cluster_dag`; measures, sections, ray casts; face edits; the WGSL tape interpreter | `DisplayPackage`, `Body` | 1; 2 (`cluster_dag`, face edits other than `offset_faces`) |
| AGT | Entity inspection with provenance; resolution with ranked fixes; `query_stability` reports; measures, sections and geometry diffs | `EntityId`, `ResolveError` | 1 |
| ECO | `crucible:geom`, `crucible:ops/anvil`; builders and healing; imported ids, `match_bodies` and `import_map`; `exchange_form` with receiver profiles; 3MF meshes and beam lattices [3MF beam lattice repository; 3MF beam lattice spec] | `Body`, `ErrorBound` | 1 |
| PLT | Per operation: grade, GPU paths and their roles, determinism-suite corpora, and each family crate's size for the engine module split | `DeterminismGrade` | 0 |

## Oracles

Oracles live in the protected `oracles/anvil/` workspace, written and locked by the oracle role before builders start (contract 13.2). They never vendor third-party datasets but fetch fixed lists by content hash at test time.

ABC cases come only from the licence-filtered subset (contract 13.3), with ECO's licence evidence per model. Thingi10K cases come only from models whose `license` field permits commercial use and modification [Thingi10K repository]. Held-out splits are chosen by a keyed hash under the oracle role's key, rotated at each gate (contract 3, principle 6).

Every oracle runs on `cpu-ci`. ANV-O-DET-1 and ANV-O-FID-1 also run on `browser-ci`, their GPU cases and ANV-O-THK-1 on `gpu-lab`, and ANV-O-PERF-1 on `device-farm` (the reference laptop).

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| ANV-O-DET-1 | Determinism | Identical output hashes at 1, 2, 7 and 64 threads, on forced x86-64 v2, v3 and v4, ARM64 and wasm32, with and without a GPU |
| ANV-O-DET-2 | Order-free rounds | Chains spaced at τ ± ρ/2⁹ give identical bits under shuffled pair orders and 1 to 64 threads; face growth that forces a vertex merge re-decides the vertex round; re-deciding only touched pairs gives the same bits as a full re-run of every round |
| ANV-O-LABEL-1 | Label invariance | Golden products and blended corpora with re-randomized `EntityId`s, `CallSite`s and Instance names keep `GeometryId`s, Assembly identities and check values; renamed equal geometry shares pages, and picks return each design's ids |
| ANV-O-SITE-1 | Text-derived names | Golden products cloned, pushed and mirrored through a second Git host and rebuilt keep every `EntityId` |
| ANV-O-CACHE-1 | Cross-design sharing | Two designs share every geometric-stage entry of a 20-operation chain; a shared failing stage gives each design fixes naming its own bindings |
| ANV-O-SCALE-1 | Scale invariance | Bodies framed at the origin and scaled by 2⁻²⁰ to 2²⁰ give the scaled outputs bit for bit |
| ANV-O-SCALE-2 | Resolution from the result | Bit-identical final geometry built with different-sized tools has one `GeometryId`; a pin far from ρ(D) reports `ResolutionStep` |
| ANV-O-PRED-1 | Predicates | 10⁸ random and near-degenerate cases give the signs of rational arithmetic, and orient2d and incircle agree bit for bit with `robust` |
| ANV-O-TOL-1 | Decision rule | Pairs at τ/2, τ and 2τ give the specified decisions and growth, with and without the filter; a Boolean of a native block with a healed import at τ = 10 µm leaves every native entity not decided against an imported one at or below τ_cap; an import declaring 0.1 mm uncertainty heals at most λ_min/4 |
| ANV-O-VALID-1 | Body checker | Every planted violation of the four conditions is reported; valid Bodies give none |
| ANV-O-VALID-2 | Global separation | Planted far-field clashes in face-edit, draft, shell, thicken and blend corpora fail with `SelfIntersecting` |
| ANV-O-VER-1 | Frozen versions | Closure hashes unchanged; pinned versions reproduce golden hashes natively and retired ones through `crucible:archive/op@1`; an edit in `anvil-topo` and a bumped third-party patch version are each refused at registration |
| ANV-O-ENC-1 | Encoding | Binary and text round trips bit-identical; every past major version decodes; decode(encode(v)) = v for every output |
| ANV-O-ENC-2 | Minor-version invariance | The golden corpus built with the previous and the new minor release has identical identities |
| ANV-O-ATTR-1 | Definitional attributes | Changing one attribute of each definitional class changes the definition digest, not the `GeometryId`; a role alias or display style changes neither |
| ANV-O-WIT-1 | WIT interfaces | Published `crucible:geom` and `crucible:ops/anvil` WIT equals the WIT generated from this catalog and the Rust types |
| ANV-O-GEOM-1 to ANV-O-GEOM-3 | Evaluation, sampling, approximation | Agreement with closed forms and rational NURBS; deterministic covering samples; deviation within the request |
| ANV-O-LAW-1 | Law curves and surfaces | Enclosures contain dense samples; evaluation equals the kernel IR reference |
| ANV-O-PROC-1 | Procedural nesting | Flattened constructions stay within propagated bounds |
| ANV-O-NF-1 | Normal form | Re-imported `exchange_form` output keeps exact geometry bit-identical and topology equal |
| ANV-O-NF-2 | Receiver profiles | A part with a 3 nm sliver and a 10 µm tolerant edge, exported under the `parasolid` profile, reports both; approximation bounds follow the tightest tolerance on each face |
| ANV-O-HEAL-1, ANV-O-HEAL-2 | Sewing, healing | Exploded solids re-sew; healed CAx-IF and ABC imports pass `check_body` within the reported deviation |
| ANV-O-NAME-1 | History | Coverage, kind, soundness and canonical order on every operation; a width change and a new hole on one face touch disjoint sets |
| ANV-O-NAME-2 | Query resolution | Zero silent re-selections at the evaluated configuration on golden products; a pocket removing part of a profile target and a fillet chain fails both with `Partial`; extent use of `Ordinal` ids or near ties fails with `Fragile`; a copy translated 1 m from the origin reports the same near ties as the original |
| ANV-O-NAME-3 | Worked example | Runs with the stated records, errors and fixes; with `4mm ± 0.1mm`, `pmi_target_resolved` fails and its fix inserts an explicit tolerance |
| ANV-O-NAME-4 | Imported names | Re-exports keep ids where persistent ids exist; a board re-exported with one connector moved keeps every other reference through the phase 1 match; edited ABC copies match their ground-truth pairs |
| ANV-O-NAME-5 | Fixes | Every fix on the golden products and the `ResolveError` corpus compiles, resolves and matches its description |
| ANV-O-NAME-6 | Range stability | `query_stability` reports every rank swap planted at one of its samples, labels the report `Sampled`, and draws the same samples under renaming |
| ANV-O-NAME-7 | Shared failure kinds | The set of `FeatureError` kinds of std features equals Anvil's `OpError` kinds plus the feature-level kinds MEC lists |
| ANV-O-ROLE-1 | Role vocabularies | Every face, edge and vertex role of every std sweeping feature resolves as specified, `end(outline.top)` and `lateral(any)` included |
| ANV-O-COPY-1 | Copies | `half + mirror(half, plane.yz)` and two-Instance features give distinct ids; adding a read-only use of a transform's source changes no `EntityId` |
| ANV-O-SSI-1 to ANV-O-SSI-3 | Surface intersection | Quadric and NURBS–analytic pairs exact in topology; Yang et al.'s and Cheng et al.'s hard cases correct and stable; general ABC pairs equal a high-precision reference |
| ANV-O-SSI-4 | Phase 1 classes | Swept, canal-surface, vertex-patch and offset pairs match high-precision references; phase 1 SSI built without any sampling module passes ANV-O-SSI-1, ANV-O-SSI-2 and this oracle |
| ANV-O-SSI-5 | Phase closure | Every phase 1 operation's output, combined with a box, a cylinder and a fillet face, gives a valid Body or `PairClassUnavailable` naming a class and its phase |
| ANV-O-CONTACT-1 | Tangential contact | Fillet on fillet, cylinder on plane and sphere in cylinder, and the uncertified cases of a cylinder Boolean tangent to a canal-surface fillet, a sketched slot tangent to an edge and a NURBS face tangent to a plane, each give one tangential edge and no coincidence region |
| ANV-O-BOOL-1 to ANV-O-BOOL-6 | Booleans, split, imprint | Algebraic identities; Manifold's three cases; Thingi10K and thingiCSG pairs with zero failures and 100% valid, tolerant facets carrying their certified displacement; ABC B-rep pairs against OCCT 8.0; split pieces sum to the input; imprint keeps volume |
| ANV-O-TRIM-1, ANV-O-TRIM-2 | Trim, extend | Kept sides as specified; continuity at extended edges |
| ANV-O-XF-1 | Transforms | Round trips within 8 ulp; exact for frame-grid translations and axis permutations |
| ANV-O-PAT-1, ANV-O-PAT-2 | Patterns | Counts, keys and placements; reuse matches unreused results within the bound |
| ANV-O-HULL-1 | Hulls, sums, decompositions | Exact rational hulls; closed-form convex sums; convex parts within the bound |
| ANV-O-BLEND-1 to ANV-O-BLEND-4 | Blend geometry | Closed-form blends on planes, cylinders and cones; spines at distance r; G1 and G2 continuity; volume change on straight edges; a boss on a curved wall blends through its convexity change |
| ANV-O-BLEND-5 | Fillet slice | The fillet slice meets the per-stage targets of the blends section under its edge-blend and corner criteria, with corpus shares per stage and OCCT 8.0's rate reported |
| ANV-O-PARITY-1 | Part-level rebuild parity | In-scope licence-filtered ABC parts, translated from their FeatureScript by the oracle-side translator, rebuild, pass `check_body` and match their Parasolid B-reps at 98% at phase 1 (GP1-class parts) and 99.5% at phase 2, with per-feature-kind rates reported |
| ANV-O-BLEND-6 | Blend regrowth | Edits next to blends rebuild them with the same parameters and ids, or fail with `BlendRegrowFailed` |
| ANV-O-OFF-1 to ANV-O-OFF-4 | Offsets, shells, shrinkwrap | Exact offsets of spheres, cylinders, tori and boxes; exact shelled volumes; a filleted box shelled inward past its fillet radius gives sharp inner edges and `BlendCollapsed`; skins within g |
| ANV-O-DRAFT-1 | Draft | Drafted faces measure the requested angle within 10⁻⁹ rad in every mode |
| ANV-O-DE-1 to ANV-O-DE-3, ANV-O-REC-1, ANV-O-REC-2 | Direct edits, recognition | Volume identities after edits; precision ≥ 0.98 on labelled ABC holes and fillets |
| ANV-O-OP-1 to ANV-O-OP-8 | Construction | Closed-form volumes and centroids of primitives, prisms, Pappus solids and springs; interpolated sections; network continuity |
| ANV-O-TEXT-1 | Text outlines | Outlines equal the font's glyphs at the reference layout, bit-identical everywhere; an unpinned font fails with `FontMissing` |
| ANV-O-MID-1, ANV-O-AXIS-1 | Dimensional reduction | Known mid-surfaces of plates, sheet metal and gyroid sheets; section properties of standard sections; strut graphs equal generator graphs |
| ANV-O-SEC-1, ANV-O-PROJ-1, ANV-O-PROJ-2, ANV-O-PAR-1, ANV-O-SM-1, ANV-O-DRAPE-1 | Sections, projection, wrap, flattening, folding, draping | Section areas against integrals, lattice sections included; lengths kept by wraps; embossed walls meet wrapped curves; fold of unfold within τ; drapes against published shear |
| ANV-O-DEF-1, ANV-O-DEF-2 | Deform, morph | Rigid Fields reproduce `transform`; deviation within bounds |
| ANV-O-IMP-1 to ANV-O-IMP-4 | Implicits | Enclosures contain samples; Lipschitz bounds hold; pruned tapes equal full tapes; iso-surfaces within the bound |
| ANV-O-LAT-1 | Lattices | Volume fractions against closed forms or references; certified minimum thickness |
| ANV-O-LEAF-1 | Leaf preservation | Faces kept from a B-rep joined with a lattice carry their ids, attributes and PMI, and stay exact on conversion |
| ANV-O-MESH-1 to ANV-O-MESH-4 | Meshes | Non-manifold data rejected; every Thingi10K model repairs valid; labelled segmentations; overlay areas sum |
| ANV-O-TET-1, ANV-O-HO-1 | Tetrahedra, curved elements | The 4,408 valid Thingi10K models mesh without inverted elements; every Jacobian Bernstein coefficient positive |
| ANV-O-HEX-1, ANV-O-BL-1 | Hex-dominant meshes, boundary layers | Valid and conforming; first-layer heights within 5% on 95% of faces |
| ANV-O-ADAPT-1, ANV-O-POLY-1 | Adaptation, polyhedral meshes | Positive Jacobians, edges within the metric band, volume-conserving parent maps; closed polyhedra |
| ANV-O-REM-1 | Remesh, decimate, smooth | Reported Hausdorff bounds hold under certified measurement |
| ANV-O-SUBD-1 | Subdivision | Limits within 10⁻¹² relative of OpenSubdiv; regular cages equal bicubic B-splines; recorded crease bounds hold |
| ANV-O-PLANAR-1, ANV-O-PLANAR-2 | Planar geometry | Predicates equal rational references; concentric clearances around arcs and pads stay exact; every derived fill passes the exact checker with zero tolerance |
| ANV-O-CONV-1, ANV-O-CONV-2 | Conversions, propagation | Every reported bound holds under independent measurement; supports perturbed in position and direction, tilted spines included, stay within propagated bounds; perpendicular planes displaced by ±p in opposite senses move their edge by p·√2, and two cylinders with curvature difference Δκ at angles from 1° to 90° match the rule or report `NearTangent`, each checked by exact recomputation; over-curved offsets report `OffsetNotRegular` |
| ANV-O-MP-1 | Mass properties | Closed forms; agreement across representations within bounds |
| ANV-O-DIST-1 to ANV-O-DIST-5 | Distance, interference, ray casts, deviation | Closed forms for analytic pairs; overlap volumes equal Boolean volumes; offset copies deviate by exactly the offset |
| ANV-O-CLS-1 to ANV-O-CLS-3 | Classification | Correct at ±τ/2 and ±2τ; agreement across representations |
| ANV-O-EDGE-1 | Edge classes | On an imported filleted bracket, fillet edges are `Smooth`, re-entrant edges `Concave`, and the stress check decides |
| ANV-O-QUAD-1 | Simulation queries | Positive weights, exact on polynomials to the rule's degree, agreeing with Algoim; closest points converge |
| ANV-O-AN-1 to ANV-O-AN-7 | Analyses | Closed-form curvature, continuity at the per-order defaults, draft, thickness, medial axes and silhouettes; hidden lines within the scale rule's bound at 100:1 and 1:200 |
| ANV-O-THK-1 | Thickness without GPU decisions | GPU disabled and adversarial GPU candidates give identical bits; symmetric walls report the canonically first location |
| ANV-O-SV-1 | `shape_velocity` | Finite differences agree within the step error; topology changes return `TopologyChange` |
| ANV-O-TESS-1 | Tessellation | Chord bounds including τ_edge hold; watertight on healed imports with large edge tolerances; equal geometry, chordal error and encoding version give one `DisplayPackage` identity |
| ANV-O-TESS-2 | Cluster DAG | Error bounds monotone from leaves to root and certified; bit-identical across targets |
| ANV-O-MFG-1 to ANV-O-MFG-3, ANV-O-VOX-1, ANV-O-VOX-2, ANV-O-FIT-1, ANV-O-FIT-2 | Manufacturing geometry, voxels, fitting | Planted gouges found; swept spheres and cylinders exact; voxel volumes converge; correlation equals direct integer correlation; known primitives recovered |
| ANV-O-SOLVE-1 | Constraint solving | Known rank deficiencies in blocks of 100 to 2,000 unknowns, irrational tangency witnesses included, diagnosed correctly; near-singular sketches give boxes containing the reference, and only qualifier-ambiguous ones fail; a 2,000-entity sketch with one block of at least 1,000 unknowns solves within MEC's drag target |
| ANV-O-FID-1 | Fidelity | `Interactive` and `SignOff` give bit-identical geometry when certification succeeds; a planted missed branch fails certification and recomputes; `Interactive` results pass `check_body`; `Preview` never reaches the shared cache |
| ANV-O-FUZZ-1 | Random use | Property-based sequences give valid, deterministic results or typed errors; failures are minimized into the corpus |
| ANV-O-PERF-1 | Performance | Target benchmarks, the thin-wall shell included, run per merge batch; work-count regressions block merges |

## Phasing

Gate contributions follow contract 13, in milestone order. Shared capabilities take their phases from contract 13.4: conforming curved tetrahedra and fitted implicit-to-B-rep conversion in phase 2, and kinematic draping in phase 4. Boundary layers serve 13.4's turbulent heat transfer row in phase 4.

| Phase | Anvil's contribution to the gate |
| --- | --- |
| 0 | Predicates, analytic geometry, topology, `EntityId`, the encoding; one implicit tape for the IR freeze; the determinism suite green; path descriptions for counsel; the part-level parity corpus and its translator; the mesh Boolean bake-off and SSI cost spike |
| 1 | GP1 (chain A): the closed phase 1 SSI classes without sampling, Booleans, tessellation, stage 1 blends, shells, patterns, hidden lines, `exchange_form` with receiver profiles, re-import matching, constraint solving. GP2 (chain B): implicit tapes, lattices, leaf-preserving conversion, 3MF data, mesh-path threads, `text_outline`. Part-level parity at 98% on GP1-class parts and the fillet slice at 99% on stage 1 |
| 2 | GP3 and GP4: general free-form SSI with lofts, general sweeps, twisted and scaled extrusions, helicoids and NURBS offsets; GPU SSI sampling after a favourable opinion; stage 2 blends; Field shells; direct edits; mid-surfaces; unfolding; fitted implicit-to-B-rep conversion; curved tetrahedra; tool contact; `cluster_dag`. Part-level parity at 99.5% and the fillet slice at 99.7% on stages 1 and 2 |
| 3 | GP5: SubD; corners of valence four and above; envelope meshing; adaptation; `anvil-planar`; parting draft; G3 surfaces; the fillet slice at 99% over all stages. Laminar heat transfer and mould filling need no fitted layers |
| 4 | GP6: G3 blend sections, hex-dominant meshes, turbulent boundary layers, scan fitting, common refinement, kinematic draping |
| 5 to 7 | GP7 masks with `anvil-planar` and cellular operations; member axes for GP8 and GP14; hull meshing for GP13; flattening for GP16 |

## Open questions

1. **GPU sampling for SSI.** Whether GPU sampling orders SSI work from phase 2 waits on counsel's freedom-to-operate opinion on US 12,229,885 B1 (contract 13.1). Without a favourable opinion, `Interactive` keeps certified CPU seeding.
2. **GP1's receiver profile.** The tolerance and minimum feature of the reference shop's CAM and coordinate-measuring software wait on the phase 0 shop agreement; until then GP1 exports under the `parasolid` profile.

## Contract change requests

None.

## Sources

| Key | Title | URL | Date opened |
| --- | --- | --- | --- |
| Shewchuk 1997 | Shewchuk, robust predicates page (Discrete & Computational Geometry 18, 1997) | https://www.cs.cmu.edu/~quake/robust.html | 2026-10-11 |
| Attene 2020 | Attene, "Indirect predicates for geometric constructions", arXiv 2105.09772 | https://arxiv.org/abs/2105.09772v2 | 2026-10-11 |
| Diazzi et al. 2023 | Diazzi, Panozzo, Vaxman, Attene, "Constrained Delaunay Tetrahedrization: A Robust and Practical Approach", arXiv 2309.09805 | https://arxiv.org/pdf/2309.09805 | 2026-10-11 |
| MarcoAttene/CDT | CDT repository | https://github.com/MarcoAttene/CDT | 2026-10-11 |
| Cherchi et al. 2022 | Cherchi, Pellacini, Attene, Livesu, "Interactive and Robust Mesh Booleans", arXiv 2205.14151 | https://ar5iv.arxiv.org/html/2205.14151 | 2026-10-11 |
| EMBER 2022 | Trettner, Nehring-Wirxel, Kobbelt, "EMBER: Exact Mesh Booleans via Efficient & Robust Local Arrangements", TOG 41(4) | https://www.graphics.rwth-aachen.de/media/papers/339/ember_exact_mesh_booleans_via_efficient_and_robust_local_arrangements.pdf | 2026-10-11 |
| Lévy 2024 | Lévy, "Exact predicates, exact constructions and combinatorics for mesh CSG", arXiv 2405.12949 | https://arxiv.org/html/2405.12949v2 | 2026-10-11 |
| trueform 2026 | Sajovic and Knez, "trueform: Fast And Robust Mesh CSG Via Topological Aggregation", arXiv 2607.15905 | https://arxiv.org/abs/2607.15905 | 2026-10-11 |
| Manifold wiki | Manifold Library wiki | https://github.com/elalish/manifold/wiki/Manifold-Library | 2026-10-11 |
| Manifold repository | Manifold repository | https://github.com/elalish/manifold | 2026-10-11 |
| Geogram repository | Geogram repository | https://github.com/BrunoLevy/geogram | 2026-10-11 |
| fTetWild 2020 | Hu, Schneider, Wang, Zorin, Panozzo, "Fast Tetrahedral Meshing in the Wild", arXiv 1908.03581 | https://arxiv.org/abs/1908.03581v2 | 2026-10-11 |
| fTetWild repository | fTetWild repository | https://github.com/wildmeshing/fTetWild | 2026-10-11 |
| Jiang et al. 2021 | bichon repository, "Bijective and Coarse High-Order Tetrahedral Meshes" | https://github.com/jiangzhongshi/bichon | 2026-10-11 |
| Khanteimouri and Campen 2023 | "3D Bézier Guarding: Boundary-Conforming Curved Tetrahedral Meshing", SIGGRAPH history archive | https://history.siggraph.org/?p=214468 | 2026-10-11 |
| Gao et al. 2017 | Gao, Jakob, Tarini, Panozzo, "Robust hex-dominant mesh generation using field-guided polyhedral agglomeration" | https://rgl.epfl.ch/publications/Gao2017Robust | 2026-10-11 |
| hex survey 2022 | "Hex-Mesh Generation and Processing: a Survey", arXiv 2202.12670 | https://ar5iv.labs.arxiv.org/html/2202.12670 | 2026-10-11 |
| Marcon et al. 2019 | Marcon et al., "A semi-structured approach to curvilinear mesh generation around streamlined bodies", arXiv 1901.01968 | https://arxiv.org/abs/1901.01968 | 2026-10-11 |
| Pietroni et al. 2021 | Pietroni, Nuvoli, Alderighi, Cignoni, Tarini, "Reliable feature-line driven quad-remeshing" | https://vcg.isti.cnr.it/publication/2021/PNACT21 | 2026-10-11 |
| Garland and Heckbert | "Surface Simplification Using Quadric Error Metrics" | https://www.cs.cmu.edu/~garland/Papers/quadrics.pdf | 2026-10-11 |
| Cao et al. 2024 | Cao et al., "Robust and Feature-Preserving Offset Meshing", arXiv 2412.15564 | https://arxiv.org/html/2412.15564v1 | 2026-10-11 |
| Jacobson et al. 2013 | Jacobson, Kavan, Sorkine-Hornung, "Robust Inside-Outside Segmentation using Generalized Winding Numbers" | https://igl.ethz.ch/projects/winding-number/ | 2026-10-11 |
| Spainhour and Weiss 2025 | Spainhour and Weiss, "Robust Containment Queries over Collections of Trimmed NURBS Surfaces via Generalized Winding Numbers", arXiv 2504.11435 | https://arxiv.org/html/2504.11435v3 | 2026-10-11 |
| Spainhour, Whitlock and Weiss 2026 | "Spatially Accelerated Winding Numbers for Curved Geometry", arXiv 2605.19200 | https://arxiv.org/pdf/2605.19200 | 2026-10-11 |
| Fidget | Keeter, Fidget project page | https://mattkeeter.com/projects/fidget | 2026-10-11 |
| Keeter 2020 | Keeter, "Massively Parallel Rendering of Complex Closed-Form Implicit Surfaces", TOG 39(4) | https://www.mattkeeter.com/research/mpr/keeter_mpr20.pdf | 2026-10-11 |
| Prospero | Keeter, The Prospero Challenge | https://mattkeeter.com/projects/prospero | 2026-10-11 |
| Barbier et al. 2025 | Barbier, Sanchez, Paris, Michel, Lambert, Boubekeur, Paulin, Thonat, "Lipschitz Pruning: Hierarchical Simplification of Primitive-Based SDFs" | https://research.adobe.com/publication/lipschitz-pruning-hierarchical-simplification-of-primitive-based-sdfs | 2026-10-11 |
| Sharp and Jacobson 2022 | Sharp and Jacobson, "Spelunking the Deep", arXiv 2202.02444 | https://arxiv.org/abs/2202.02444v3 | 2026-10-11 |
| Hwang and Sung 2024 | Hwang and Sung, "Occupancy-Based Dual Contouring", arXiv 2409.13418 | https://arxiv.org/html/2409.13418v1 | 2026-10-11 |
| libfive repository | libfive repository | https://github.com/libfive/libfive | 2026-10-11 |
| nTop whitepaper | nTop, implicit modeling technology whitepaper page | https://www.ntop.com/resources/guides/whitepaper-implicit-modeling-technology/ | 2026-10-11 |
| nTop 5.0 notice | nTop 5.0 new implicit modeling kernel notice | https://docs.ntop.com/help-articles/whats-new/backwards-compatibility-notices/ntop-5-0-new-implicit-modeling-kernel | 2026-10-11 |
| Yang et al. 2023 | Yang, Jia, Yan, "Topology Guaranteed B-Spline Surface/Surface Intersection", SIGGRAPH history archive | https://history.siggraph.org/?p=214449 | 2026-10-11 |
| Cheng et al. 2023 | Cheng, Zhang, Xiao, Li, "Topology Driven Approximation to Rational Surface-surface Intersection via Interval Algebraic Topology Analysis", SIGGRAPH history archive | https://history.siggraph.org/learning/topology-driven-approximation-to-rational-surface-surface-intersection-via-interval-algebraic-topology-analysis-by-cheng-zhang-xiao-and-li | 2026-10-11 |
| Patrikalakis, Maekawa and Cho | "Shape Interrogation for Computer Aided Design and Manufacturing", MIT hyperbook | https://web.mit.edu/hyperbook/Patrikalakis-Maekawa-Cho/ | 2026-10-11 |
| Krishnamurthy et al. 2008 | Krishnamurthy, Khardekar, McMains, Haller, Elber, "Performing Efficient NURBS Modeling Operations on the GPU", SPM 2008 | https://mcmains.me.berkeley.edu/pubs/SPM08gpuSSI.pdf | 2026-10-11 |
| ETER | "ETER: Elastic Tessellation for Real-Time Pixel-Accurate Rendering of Large-Scale NURBS Models", SIGGRAPH history archive | https://history.siggraph.org/?p=132429 | 2026-10-11 |
| US12229885B1 | US 12,229,885 B1, Google Patents | https://patents.google.com/patent/US12229885 | 2026-10-11 |
| US12229885B1 full text | US 12,229,885 B1, USPTO full text | https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12229885 | 2026-10-11 |
| Zoo engine overview | Zoo CAD engine overview | https://zoo.dev/research/zoo-cad-engine-overview | 2026-10-11 |
| Zoo Design Studio v1 | Zoo Design Studio v1 announcement | https://zoo.dev/blog/zoo-design-studio-v1 | 2026-10-11 |
| Jackson 1995 | Jackson, "Boundary Representation Modelling with Local Tolerances", Solid Modeling '95 | https://ftp1.cs.wisc.edu/pub/users/prem/jackson-SM-95.pdf | 2026-10-11 |
| Parasolid convergent modeling | Siemens, Parasolid Convergent Modeling press release | https://news.siemens.com/en-gb/parasolid-convergent-modeling-mixed-models/ | 2026-10-11 |
| ACIS Polyhedra | Spatial, ACIS Polyhedra | https://www.spatial.com/products/acis-polyhedra?hsLang=ja | 2026-10-11 |
| CGM Modeler | Spatial, CGM Modeler | https://www.spatial.com/solutions/3d-modeling/cgm-modeler | 2026-10-11 |
| OCCT 8.0 | Open CASCADE Technology 8.0.0 release announcement | https://occt3d.com/dev/content/open-cascade-technology-800-release/index.html | 2026-10-11 |
| OCCT repository | OCCT repository | https://github.com/Open-Cascade-SAS/OCCT | 2026-10-11 |
| OCCT MakeFillet | OCCT reference, BRepFilletAPI_MakeFillet | https://occt3d.com/dev/doc/refman/html/class_b_rep_fillet_a_p_i___make_fillet.html | 2026-10-11 |
| Truck repository | Truck repository | https://github.com/ricosjp/truck | 2026-10-11 |
| Fornjot repository | Fornjot repository | https://github.com/hannobraun/fornjot | 2026-10-11 |
| Várady publication list | Várady, publication list, SZTAKI | https://eprints.sztaki.hu/view/creators/V=E1rady=3AT=2E=3A=3A.html | 2026-10-11 |
| OpenSubdiv repository | OpenSubdiv repository | https://github.com/PixarAnimationStudios/OpenSubdiv | 2026-10-11 |
| OpenSubdiv license | OpenSubdiv license | https://raw.githubusercontent.com/PixarAnimationStudios/OpenSubdiv/release/LICENSE.txt | 2026-10-12 |
| Nießner et al. 2012 | Nießner, Loop, Meyer, DeRose, "Feature Adaptive GPU Rendering of Catmull-Clark Subdivision Surfaces" | https://niessnerlab.org/projects/niessner2012feature.html | 2026-10-11 |
| Stam 1998 | Stam, "Exact Evaluation of Catmull-Clark Subdivision Surfaces at Arbitrary Parameter Values" | https://www.dgp.toronto.edu/public_user/stam/reality/Research/pdf/sig98.pdf | 2026-10-11 |
| Edelsbrunner and Mücke | Edelsbrunner and Mücke, "Simulation of Simplicity", arXiv math/9410209 | https://arxiv.org/abs/math/9410209 | 2026-10-11 |
| Thingi10K 2016 | Zhou and Jacobson, "Thingi10K", arXiv 1605.04797 | https://arxiv.org/abs/1605.04797 | 2026-10-11 |
| ABC 2019 | Koch et al., "ABC: A Big CAD Model Dataset for Geometric Deep Learning", CVPR 2019 | https://openaccess.thecvf.com/content_CVPR_2019/html/Koch_ABC_A_Big_CAD_Model_Dataset_for_Geometric_Deep_Learning_CVPR_2019_paper.html | 2026-10-11 |
| persistent naming review 2018 | "Mechanisms of Persistent Identification of Topological Entities in CAD Systems: A Review", Alexandria Engineering Journal | https://doaj.org/article/bf42fdae16584d0ba2d824137aba6599 | 2026-10-11 |
| Algoim | Algoim, high-order quadrature and closest points for implicitly defined geometry | https://algoim.github.io/ | 2026-10-11 |
| CAx-IF PMI 4.1 | CAx-IF Recommended Practices for PMI (AP242), version 4.1, 20 June 2024 | https://www.mbx-if.org/home/wp-content/uploads/2024/06/rec_pracs_pmi_v41.pdf | 2026-10-11 |
| OpenSCAD cheat sheet | OpenSCAD cheat sheet | https://openscad.org/cheatsheet/ | 2026-10-11 |
| RFC 3514 | Rust RFC 3514, float semantics | https://rust-lang.github.io/rfcs/3514-float-semantics.html | 2026-10-11 |
| Rust f64 docs | Rust `f64` documentation | https://doc.rust-lang.org/std/primitive.f64.html | 2026-10-11 |
| Rust 1.86.0 release | Rust 1.86.0 stabilized APIs, releases.rs | https://releases.rs/docs/1.86.0/ | 2026-10-11 |
| correct rounding page | Correct rounding of elementary functions in IEEE 754 formats | https://reliable-computing.org/correctrounding.html | 2026-10-11 |
| Wasm 3.0 | WebAssembly 3.0 announcement | https://webassembly.org/news/2025-09-17-wasm-3.0 | 2026-10-11 |
| Wasm nondeterminism | WebAssembly nondeterminism | https://www.webassembly.org/docs/nondeterminism/ | 2026-10-11 |
| WGSL | WGSL specification | https://www.w3.org/TR/WGSL/ | 2026-10-11 |
| slotmap docs | slotmap documentation | https://docs.rs/slotmap/latest/slotmap/ | 2026-10-11 |
| inari docs | inari documentation | https://docs.rs/inari/latest/inari/ | 2026-10-11 |
| 3MF beam lattice repository | 3MF Beam Lattice extension repository | https://github.com/3MFConsortium/spec_beamlattice | 2026-10-11 |
| 3MF beam lattice spec | 3MF Beam Lattice Extension specification 1.2.0 | https://github.com/3MFConsortium/spec_beamlattice/blob/master/3MF%20Beam%20Lattice%20Extension.md | 2026-10-11 |
| Algoim licence | Algoim LICENSE | https://raw.githubusercontent.com/algoim/algoim/master/LICENSE | 2026-10-11 |
| Gao et al. code | Robust hex-dominant meshing repository | https://github.com/gaoxifeng/robust_hex_dominant_meshing | 2026-10-11 |
| Nektar++ licence | Nektar++ LICENSE | https://gitlab.nektar.info/nektar/nektar/-/blob/master/LICENSE.txt | 2026-10-11 |
| OCCT Defeaturing | OCCT reference, BRepAlgoAPI_Defeaturing | https://occt3d.com/dev/doc/refman/html/class_b_rep_algo_a_p_i___defeaturing.html | 2026-10-11 |
| Thingi10K repository | Thingi10K repository | https://github.com/Thingi10K/Thingi10K | 2026-10-11 |
| meshoptimizer repository | meshoptimizer repository | https://github.com/zeux/meshoptimizer | 2026-10-11 |
| FreeCAD 1.0 release | FreeCAD 1.0 release announcement | https://blog.freecad.org/2024/11/19/freecad-version-1-0-released/ | 2026-10-11 |
| trueform repository | trueform repository | https://github.com/polydera/trueform | 2026-10-11 |
| ABC dataset page | ABC dataset project page: file formats and provenance | https://deep-geometry.github.io/abc-dataset/ | 2026-10-12 |
| robust repository | georust `robust`: robust adaptive floating-point predicates | https://github.com/georust/robust | 2026-10-12 |
| spade repository | `spade`: Delaunay triangulations for Rust | https://github.com/Stoeoef/spade | 2026-10-12 |
| Axom repository | LLNL Axom repository | https://github.com/LLNL/axom | 2026-10-12 |
| SolidCraft repository | SolidCraft repository README | https://github.com/bherbruck/solvecraft | 2026-10-12 |
| Parasolid product page | Siemens, Parasolid product page | https://www.siemens.com/en-us/products/plm-components/parasolid/ | 2026-10-12 |
| ACIS product page | Spatial, 3D ACIS Modeler | https://www.spatial.com/products/3d-acis-modeling | 2026-10-12 |
| Geolus shape search | Siemens, "How Geolus 3D shape search drives part re-use" | https://blogs.sw.siemens.com/teamcenter/how-geolus-3d-shape-search-drives-part-re-use/ | 2026-10-12 |
| Fusion GD methods | Autodesk Fusion, generative design: specify manufacturing methods | https://help.autodesk.com/cloudhelp/ENU/Fusion-GenerativeDesign/files/GD-SPECIFY-MFG-METHOD.htm | 2026-10-12 |
| Onshape FeatureScript library | Onshape, FeatureScript standard library documentation | https://cad.onshape.com/FsDoc/library.html | 2026-10-12 |
