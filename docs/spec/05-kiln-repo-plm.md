# Kiln, repository and PLM (KLN)

Kiln evaluates Ingot as a memoized graph keyed by content, call site and pinned operation versions, so an edit recomputes only what it affects, with identical bits within each platform class. The CAS stores every object under a SHA-256 identity, and `repo` records each edit as an immutable Change that merges only when source, checks, geometry and connectivity agree. Lifecycle, policy, signature and audit records share that signed store on a laptop, a team server, the cloud and an air-gapped site.

## Scope and the operation contract

This tab owns evaluation, caching, the determinism policy, the CAS, `repo`, collaboration, product lifecycle management (PLM), security, compliance records and deployment. ING owns compilation and `OpSite`s, ANV and FLX own operations, PLT owns the mechanisms of contract 7.3, AGT owns the `api` catalog and agent safety, and ECO owns the registry, events and connectors. The crates are `kiln`, `cas` and `repo`; shared types live in `base` (contract 12).

Kiln calls every operation and Wasm component through `OpImpl`, with the identities contract 7.2 gives them; Ingot feature calls are nodes keyed by module code hashes.

```rust
pub trait OpImpl: Send + Sync + 'static {
    const ID: OpId;                    // OpId::new("anvil", "blend")
    const VERSION: u32;                // behavior version, pinned in ingot.lock
    const GRADE: DeterminismGrade;
    type Inputs: OpInputs;             // each input exposes its GeometryId or ObjectId
    type Outputs: OpOutputs;           // canonical: decode(encode(v)) == v
    fn effective_fidelity(&self, requested: Fidelity) -> Fidelity;
    fn cost(&self, sizes: &InputSizes) -> CostEstimate;   // priced upper bound
    fn eval(&self, cx: &mut OpCx<'_>, inputs: Self::Inputs) -> Result<Self::Outputs, Failure>;
}

/// Everything an operation may use: no clocks, ambient randomness or I/O.
impl OpCx<'_> {
    pub fn checkpoint(&mut self) -> Result<(), Abort>;   // safe point, every 10 ms of CPU
    pub fn rng(&self, stream: u64) -> Philox4x32;       // keyed without class, fidelity or names
    pub fn det(&self) -> &runtime::Det;                 // det_sum, det_reduce, exact_sum
    pub fn work_budget(&self) -> Option<WorkBudget>;
    pub fn fidelity(&self) -> Fidelity;                 // effective fidelity
}

pub struct OpKey(ObjectId);                             // contract 7.2, items 1 to 6
pub enum Fidelity { Preview, Interactive, SignOff }
pub enum DeterminismGrade { Portable, ClassExact, Certified }
```

**Decision D-KLN-2:** The engine build is never part of a key; a behavior fingerprint makes that safe. Each operation version registers a digest of its outputs over a conformance corpus, and CI fails when code changes the digest without a version bump. *Why:* keying on the build empties every cache at each release, and version-only keys are unsafe unless bumps are enforced. *Rejected:* the build id in the key; trusting developers to bump versions (silent cache poisoning).

`ingot.lock` pins every operation version a design uses. Upgrading is an explicit Proposal showing the geometric and metric diff, never a side effect of installing an engine; a major Body encoding version is a behavior change (D-ANV-9).

**Decision D-KLN-4:** A pinned operation version is never substituted. Retired versions run from archived Wasm builds of their frozen source; a version without a Wasm build (a GPU `ClassExact` path) returns the `Failure` `OpVersionRetired`, whose fix is an upgrade Proposal. *Why:* old designs must rebuild identically (contract 4), and archived Wasm needs no fleet of old engines. *Rejected:* silent fallback to the newest version; compatibility workers running old native builds (a second fleet to secure). (revised in round 2)

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Operation contract | `OpImpl` and `OpCx` in `base`; canonical outputs; effective-fidelity map | Missing grade, cost model or fidelity map fails registration | KLN-O-FPRINT-1 | 0 |
| Behavior fingerprints | Corpus digest per operation version | CI fails on a changed digest without a version bump | KLN-O-FPRINT-1 | 0 |
| Pinned versions and upgrades | `ingot.lock` pins; upgrade Proposals with diffs | An unknown pin fails resolution, naming the pin | KLN-O-EQUIV-1 | 0 |
| Retired versions | Archived Wasm builds of frozen source | `OpVersionRetired` only for paths without a Wasm build | KLN-O-RETIRE-1 | 1 |

## Kiln: graph, keys and memoization

### Graph model

Kiln evaluates a graph of input cells and derived nodes. Input cells hold what the outside world sets: source, `ingot.lock`, packages, External inputs, Evidence records and configuration points. Nodes are pure functions of what they read, recorded as they read it, and evaluation is demand-driven as in Adapton.

| Node kind | Key | Value |
| --- | --- | --- |
| Front-end stage | Module code hash, language behavior version | IR and diagnostics |
| Feature call | Code hashes of the modules used, argument identities, `OpSite` | Parts, Bodies, Fields or plain values, with `HistoryRecord`s |
| Op | `OpKey`; entity-naming Ops in two stages | Canonical outputs with `ErrorBudget`s |
| Query resolution | Query, input identities, `OpSite` | Entities with Notes, or a `ResolveError` |
| Check | Predicate, subject identities, fidelity | `CheckOutcome` |
| Derived view | View kind and inputs | A BOM, diff, traceability matrix or where-used result |

Every node whose value carries `EntityId`s includes its `OpSite` in its key, so equal calls at different sites never share names; cross-site sharing happens only in the geometric stage of Ops (R3-05). Checks read results and never feed them, so adding a `require` changes no other key. Kiln prefetches the static Op calls the IR exposes and suspends only on data-dependent ones.

**Decision D-KLN-1:** Kiln uses a suspending scheduler with dynamic dependency recording, verifying traces in memory and constructive traces in the shared cache. *Why:* Mokhov, Mitchell and Peyton Jones show that dynamic dependencies need a restarting or suspending scheduler, and suspending with constructive traces gives minimal, shareable rebuilds. *Rejected:* topological scheduling (needs static dependencies); restarting as in Bazel (wastes interactive work); deep constructive traces as in Nix (no early cutoff on intermediates).

### Keys

An `OpKey` is the SHA-256 of contract 7.2's six items in deterministic CBOR under the domain tag `crucible/opkey/1`. Kiln applies four rules.

1. Entity-naming Ops key their geometric stage by input `GeometryId`s and their relabeling stage by the output id, the `OpSite` and the inputs' name maps (D-ANV-24); Flux solves key on `GeometryId`s plus referenced canonical entity numbers.
2. The class item is `CpuCanonical` for `Portable` and `Certified` results even when a GPU assisted. Random streams are keyed without class, fidelity or names (by `GeometryId`s and argument values), so every class draws the same samples and renames change none (contract 7.1).
3. Pinned data a node reads (calibration tables, regulation packages, supplier offers) enters its key by identity; the lockfile as a whole never does.
4. Limits that can change a value, such as a `#[fuel]` set in source, enter the key; organization ceilings never do.

**Decision D-KLN-3:** Keys include the code hashes of the Ingot modules a node actually used plus the language behavior version, never the whole lockfile. *Why:* a whole-lockfile key invalidates every result when a package is added and blocks sharing std results; contract 7.2 adopted this form (KLN-1). *Rejected:* the whole lockfile; the round 1 package closure, which misses whenever an unused module changes. (revised in round 2)

### Memo entries and backdating

A memo entry stores, per output, a value handle, a lazy identity and a `changed_at` generation, plus `verified_at`, the ordered dependencies read, the minimum input durability and a cost record. Durabilities follow Salsa: `High` for std, packages, Materials and catalog data, `Medium` for closed files, `Low` for open documents.

**Decision D-KLN-36:** A node has four kinds of output, each with its own `changed_at`: its value; one accumulator per kind (checks, notes, tolerance sites, PMI); metadata (fuel, cost); and its label. Dependents record which outputs they read, metadata never takes part in backdating, and verification re-joins labels from current inputs even when the value backdates. *Why:* a fuel-only edit would otherwise re-execute every dependent (R3-13), and an input relabelled with unchanged bytes would never relabel its dependents (R3-02). *Rejected:* one combined value; labels inside the value (a shared-cache hit would import a foreign label).

Kiln bumps the generation once per batch of input changes and verifies as Salsa does. A memo already verified at the generation returns at once; one whose durability class saw no change revalidates in constant time; otherwise Kiln checks recorded dependencies in order and re-executes only if one changed. Each re-executed output equal to its old value keeps its `changed_at` (backdating), so a comment edit lowers to equal IR and re-executes no feature.

**Decision D-KLN-5:** Early cutoff on the interactive path compares values directly; hashing happens off it. Values are canonical at the operation boundary (−0.0 becomes +0.0, no non-finite values), so in-memory equality equals encoded equality and reloads are bit-identical. Kiln consults the shared cache only when an Op's estimated cost exceeds computing its key plus one lookup (default 200 ms). *Why:* hashing a 100 MB mesh inside a 100 ms drag spends the budget, and non-canonical values make results depend on eviction (R3-34). *Rejected:* eager hashing; equality that distinguishes signed zeros. (revised in round 2)

A node's label is the join of its inputs' labels in contract 5's lattice, recomputed locally on every shared-cache hit.

### Failures and Aborts

A `Failure` is a property of the inputs: coplanar Boolean faces, a `ResolveError`, a diverged solve, `OpVersionRetired`. Kiln memoizes it, `try` catches it, and dependents see `DependencyFailed`, which wraps only Failures. An Abort is a property of the Evaluation: cancellation, resource exhaustion, device loss, budget exhaustion, worker loss or a limit below.

**Decision D-KLN-6:** Failures are cached values; Aborts are invisible to Ingot and never cached. An Abort propagates to every transitive dependent, no node that observed one writes a memo entry, CAS object or attestation, and Kiln retries worker or device loss once elsewhere before reporting it. *Why:* cached Failures keep editing fast while a feature is broken, and a fallback taken because a worker ran out of memory must never become a cached fact (R3-03). *Rejected:* caching nothing that fails; one failure type with an environmental flag (`try` could observe it). (revised in round 2)

Two evaluation-wide limits are Aborts (contract 7.1): a demand-depth limit on nested demands (default 10,000), which stops `f(n) = f(n + 1)` with `DemandDepthExhausted`, and a fuel governor summing fuel across an Evaluation against its budget. An organization ceiling below a limit set in source refuses the Evaluation at admission with `FuelCeilingExceeded`, never a cached `FuelExhausted` (R3-12). A node demanding a node on its own active stack fails with `Cycle` and the path of spans.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Memoized evaluation with backdating | `Kiln::demand(EvalRequest) -> ResultStream` | Typed `Failure`s memoized | KLN-O-MIN-1, KLN-O-EQUIV-1 | 0 |
| Durabilities | `High`, `Medium` and `Low` inputs | — | KLN-O-MIN-1 | 0 |
| Site-keyed and two-stage nodes | `OpSite` in every key whose value carries `EntityId`s; `GeometryId` geometric stage | `Internal::EntityIdCollision` is never reachable | KLN-O-SITE-1 | 0 |
| Multi-output memo entries | Value, accumulator, metadata and label outputs | — | KLN-O-MIN-1 | 0 |
| Canonical round trip | decode(encode(v)) = v for every Op output | Registration fails for non-canonical outputs | KLN-O-ROUNDTRIP-1 | 0 |
| Label propagation | Join per node; shared-cache hits return values only | `label.write_down` at `api` | KLN-O-LABEL-1 | 1 |
| Failures and Aborts | `Failure` cached and catchable; Abort propagates uncached | Abort reported with its cause | KLN-O-ABORT-1 | 0 |
| Evaluation limits | Demand depth 10,000; fuel governor; admission ceilings | `DemandDepthExhausted`, `FuelCeilingExceeded` | KLN-O-LIMIT-1 | 0 |

## Kiln: scheduling, budgets and results

### Scheduling and cancellation

Scheduling never changes a result: nodes share no mutable state, concurrent demands share one execution, and collections such as diagnostics merge in canonical order. Kiln runs nodes on PLT's pools, by the request's `PriorityClass` from `base`.

| Class | Demand source | Pool | Preemption |
| --- | --- | --- | --- |
| `Interactive` | A person waiting: viewport, selection, drag, own rebuild | Interactive | Never |
| `Agent` | Agent sessions | Background | By `Interactive`, at node boundaries |
| `Ci` | Proposal CI, merge queue, releases | Background | By `Interactive` |
| `Batch` | Explorations, benchmarks, prefetch, background `SignOff` | Background | By all; resumes from cached nodes |

A background node that an interactive node awaits is promoted. A drag lane holds one request in flight and one pending; within 100 ms it recomputes the dragged feature plus the dependents that fit an 80 ms estimate, at least ten when cheap. Later dependents show `Proxy` where the change is affine on them, else `Stale` (contract 13.3).

A node runs only while demanded, and a new generation cancels in-flight nodes whose reads changed. Native operations poll `OpCx::checkpoint` every 10 ms of CPU time, Wasm stops at the determinizer's fuel checks (contract 7.4), and GPU dispatches follow PLT's rule. Cancellation is an Abort; completed lower-fidelity results stay valid.

### Memory and eviction

Values are immutable, reference-counted buffers, and large ones are memory-mapped from the local CAS. An evicted value keeps its memo metadata and is reloaded by `ObjectId` or recomputed. Values on screen, in an open review or feeding running nodes are pinned, and budgets per target come from PLT's memory tables (contract 9).

**Decision D-KLN-7:** Kiln evicts values by GreedyDual-Size, with cost the cheaper of recomputing and reloading: priority `H = L + cost / size`, evict the lowest `H`, raise the floor `L` to it [formula from the paper's standard statement; the abstract page opened does not show it]. *Why:* the algorithm combines recency, cost and size without tuning, and CAD values span nine orders of magnitude in both. *Rejected:* plain LRU (evicts an hour-long solve to keep cheap sketches); manual pinning only.

Kiln writes its memo table (edges and identities, not values) to the local CAS every 60 s and on exit, so a restart revalidates instead of recomputing.

### Progressive results

Each demanded output exists at up to three fidelities, each a separate node.

| Fidelity | Geometry (ANV) | Physics (FLX) | Shared cache |
| --- | --- | --- | --- |
| `Preview` | Surrogates, looser tolerances, often GPU | Reduced or surrogate solves, `Indicator` bounds | Never written |
| `Interactive` | Floating-point decisions validated after the fact | Calibrated `Estimated` bounds | Written; never used by `SignOff` checks or releases |
| `SignOff` | Certified decisions | Converged, `Guaranteed` where proven | Used by releases after two-builder agreement |

Each operation maps the requested fidelity to an effective one, so one that ignores fidelity is one node for all three. A subscription names targets, a fidelity ceiling and a priority, and Kiln streams `ResultEvent`s with generation, fidelity, `ResultStatus`, value or `Failure`, budget and label. A published frame holds one generation; older results appear only as `Stale`.

An outcome is provisional when its fidelity is below the check's declared one (default `SignOff`), and only non-provisional outcomes count for CI, Proposals and releases. An `if`, `match` or `where:` on `Undecided` below the ceiling yields `Pending` until the next fidelity's node, already demanded, arrives; it fails with `ING6401` only at the ceiling (R3-14). A release demands every node at `SignOff`, geometry included.

**Decision D-KLN-8:** Progressive refinement is a set of independent nodes keyed by fidelity, not a stateful process. *Why:* each tier is then cacheable, cancellable and shareable, and a lower-fidelity result can never pass for a `SignOff` one. *Rejected:* in-place refinement of one value (not cacheable, invisible to the key).

### Cost and budgets

Every node records CPU and GPU time, memory, bytes moved and remote price, attributed to principal, repository, branch and Proposal. Requests carry `base`'s `Budget`. Kiln returns a priced upper bound from per-operation cost models, `api` reserves it, and metering charges actual use (AGT); an estimate above what remains returns `BudgetExceeded` with cheaper options.

An Op estimated above 10 core-seconds receives a work budget (fuel or an iteration cap) from the reserved amount and reaches a safe point at least every 10 core-seconds. Exhausting it is the Abort `BudgetExhausted`, reported with the last step checkpoint, so a cap is exceeded by at most one safe-point interval (R6-29). The work budget never enters a key, because a value either completes or is not written.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Priority classes | `PriorityClass` per request; promotion of awaited nodes | — | KLN-O-SIM-1 | 0 |
| Drag lane | One request in flight, one pending; dependents fitted to 80 ms | Later dependents `Proxy` or `Stale` | KLN-O-PROG-1 | 1 |
| Cancellation | Safe points every 10 ms; determinizer fuel checks | Cancelled nodes leave no memo entry or CAS write | KLN-O-CANCEL-1 | 0 |
| Eviction | GreedyDual-Size within PLT's budgets | Reload or recompute | KLN-O-EVICT-1 | 1 |
| Progressive results | `ResultEvent` with `ResultStatus`; one generation per frame | `Stale` marked; `Pending` on `Undecided` below the ceiling | KLN-O-PROG-1 | 1 |
| Budgets and work budgets | Priced upper bound reserved; safe points every 10 core-seconds | `BudgetExceeded` at admission; `BudgetExhausted` Abort | KLN-O-BUDGET-1 | 1 |

## Derivatives

ING's `grad`, FLX's adjoints and topology optimization chain derivatives across features through Kiln (contract 7.1).

```rust
pub trait Differentiable: OpImpl {
    fn tangent(&self, cx: &mut OpCx<'_>, inputs: &Self::Inputs, dx: &Tangents)
        -> Result<Tangents, Failure>;
    fn adjoint(&self, cx: &mut OpCx<'_>, inputs: &Self::Inputs, y_bar: &Cotangents)
        -> Result<Cotangents, Failure>;
}
```

Forward mode composes tangents along the recorded graph. Reverse mode walks the dependencies of a scalar goal in reverse topological order, calls each `adjoint` once and sums cotangents in canonical order; an Op without `Differentiable` fails with `NotDifferentiable { op }`. Derivative nodes are keyed by the primal key plus the goal's, so an objective-only change reuses every primal result.

Step checkpoints of transient solves are CAS objects keyed by (`OpKey`, step) in the `Checkpoint` retention class, which eviction drops first. A resumed solve or adjoint is bit-identical whether its checkpoints were kept, reloaded or recomputed.

**Decision D-KLN-37:** Derivatives are a Kiln traversal over `Differentiable` operations, with step checkpoints in their own retention class. *Why:* adjoints that cross features need one recorded graph, and large, cheaply recomputed checkpoints must yield to ordinary values. *Rejected:* a tape per engine (cannot chain through features); checkpoints as ordinary values (GreedyDual-Size would keep them over hour-long solves).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `Differentiable` operations | `tangent` and `adjoint` in `base` | `NotDifferentiable { op }` | KLN-O-DERIV-1 | 0 |
| Reverse traversal | From a scalar goal; canonical cotangent sums | Aborts propagate as for primal nodes | KLN-O-DERIV-1 | 1 |
| Step checkpoints | `Checkpoint` class keyed by (`OpKey`, step) | Evicted first; recomputed on demand | KLN-O-DERIV-1 | 1 |

## Shared cache and remote evaluation

Kiln runs one engine everywhere. Workers advertise classes, operation versions, GPU back ends, region, operator attributes and price; Kiln offloads a costly node when transfer and remote time beat local time, and outputs stay remote until needed.

| Role (contract 7.8) | Runs | Holds | Writes |
| --- | --- | --- | --- |
| Untrusted-evaluation worker | Every Proposal's CI and every External Op, each in a single-use microVM | No attestation key | A per-Proposal namespace |
| Trusted builder | Merged Changes of protected branches | Workload identity | Results for attestation |
| Attestation service | — | Signing keys | Attestations (`OpKey`, `ObjectId`) for work sent to trusted builders, with output ids computed by the host |
| Operator registry builders | std and public packages | Operator keys | The global public domain, with 2-of-n agreement |

Release gates and `SignOff` checks accept a cached result only when two trusted builders on different hosts, and different ISAs for `Portable` operations, produced the same `ObjectId`; otherwise they recompute. Clients trust their organization plus operator public signers by default. Spot re-execution of shared-cache hits is weighted by downstream fan-out and is 100% for nodes feeding released checks; a mismatch quarantines the attestation and opens a determinism incident.

Objects and attestations live in the encryption domain of their labels, so lookups never cross tenants or label sets. On servers each worker process serves one (tenant, label set), `export_controlled` sets get dedicated VMs, and Wasm pooling slots are never reused across them (R5-09). Placement calls `base`'s `PlacementPolicy`, implemented by `repo::policy`; a node whose label requires a region or operator attributes runs only where they hold, or aborts with `ResidencyDenied`.

**Decision D-KLN-9:** Only trusted builders evaluating merged protected Changes produce attestations, which a separate service signs; untrusted code runs in single-use microVMs that hold no key; release gates and `SignOff` checks require two-builder agreement. *Why:* round 1 let CI runners that execute agent Proposals and native External Ops sign results, so one sandbox escape could poison every tenant, and uniform 1% sampling rarely catches a targeted entry (R5-03, R3-20). *Rejected:* trusting machines instead of the inputs they ran; uniform spot checks; tenant builders writing the global domain. (revised in round 2)

In phase 1 the single-node team server is the only trusted builder, so release gates and `SignOff` checks recompute, and Proposal CI runs in microVMs on its host. Kiln's remote protocol is its own: Bazel's Remote Execution API models command lines over materialized trees, too heavy for in-process calls. An adapter lets a Remote Execution API v2 server act as a storage tier [unverified: adapter fit per server].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Remote evaluation | Worker advertisement; cost-based placement | Worker loss is an Abort, retried once elsewhere | KLN-O-REMOTE-1 | 1 (team server), 2 (cloud) |
| Worker pools and attestation | Contract 7.8 roles | Unsigned or untrusted entries ignored | KLN-O-TRUST-1 | 2 |
| Two-builder agreement | Same `ObjectId` from two trusted hosts | Recompute | KLN-O-TRUST-1 | 2 |
| Fan-out-weighted spot checks | 100% for nodes feeding released checks | Quarantine and determinism incident | KLN-O-TRUST-1 | 2 |
| Label-aware placement | `PlacementPolicy`; one worker process per (tenant, label set) | `ResidencyDenied` | KLN-O-LABEL-1 | 2 |

## Determinism policy

Contract 7.3 sets the rules and PLT owns the mechanism table; this section owns the policy: which grade each result needs and where each class is accepted.

| Grade | Meaning | Class in the key | Shared within |
| --- | --- | --- | --- |
| `Portable` | Bit-identical across the canonical class | `CpuCanonical` | Every Tier 1 CPU target, browsers and cloud workers included |
| `ClassExact` | Bit-identical within one class | `CpuIsa` or `Gpu` | That class |
| `Certified` | Independent of the class that computed intermediates | `CpuCanonical` | As `Portable`, even when a GPU assisted |

| Result | Grade required | Accepted by release gates |
| --- | --- | --- |
| Geometry and oracle reference results | `Portable` or `Certified` | Yes |
| Flux `SignOff` results | `Portable`, or a pinned non-canonical Field whose residual and bound are computed canonically | Yes |
| `Interactive` results, `CpuIsa` variants with FMA | Any | No; `SignOff` recomputes canonically |
| External Op results | The host's class or `Unverified` | Only as `ObjectId`s the release pins |

**Decision D-KLN-10:** `Portable` means bit-identical across `CpuCanonical { epoch }`, every Tier 1 CPU target, browsers included, at any thread count and ISA level. It is the only grade for geometry and oracle reference results. *Why:* a cache shared by every OS, browsers and cloud workers works only if their results are the same bits. *Rejected:* one class per OS and architecture (fragments the cache about eightfold); the round 1 class names, replaced by PLT's enum. (revised in round 2)

**Decision D-KLN-11:** Every `Portable` operation computes elementary functions with `detmath`, PLT's correctly rounded library ported from CORE-MATH. *Why:* a correctly rounded function has one right answer on every target, while Rust documents its own as non-deterministic across platforms. *Rejected:* one pinned libm everywhere (each bug fix changes results); the host libm (differs by OS).

**Decision D-KLN-12:** GPU floating-point results are `ClassExact` on their class, or they feed a `Certified` computation whose output is independent of them. *Why:* WGSL lets implementations reassociate, fuse and flush subnormals, so no shader can force identical bits across drivers. *Rejected:* claiming cross-vendor GPU determinism (false); banning GPUs from `SignOff` work (wastes the hardware that makes large solves practical).

**Decision D-KLN-13:** Reductions in `Portable` code use a canonical order: fixed blocks by element index combined by PLT's `det_sum` and `det_reduce` trees. Where partitioning varies between runs, as across ranks of a distributed solve, operations use binned reproducible summation (`exact_sum`) in the style of ReproBLAS. *Why:* a fixed tree costs nothing in arithmetic, while ReproBLAS reports a dot product about 4× slower than an optimized one on one core. *Rejected:* atomics or completion-order reduction; binned summation everywhere (pays where a fixed tree is free).

A request that pins no class gets the class of an existing cached result, else the local one; CI pins one class per repository. A release records the class of every result it cites and pins the `ObjectId`s of External Op results and Evidence records.

The determinism suite runs on every merge on contract 7.3's representative set and nightly elsewhere, perturbing threads, ISA level, allocator, hash seeds, memory budget and cancellation. A nightly divergence bisects automatically, opens a severity-1 incident, quarantines affected attestations and blocks beta promotion. Kiln, sync, the collector and the server also run under seeded deterministic simulation as FoundationDB does: 1,000 simulated hours per night in phase 0 and 10,000 by phase 2 (targets).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Determinism grades | `DeterminismGrade` per operation version | Undeclared grade fails registration | KLN-O-DET-1 | 0 |
| Release acceptance | Grade and class rules above | Non-canonical inputs recomputed canonically | KLN-O-DET-1 | 1 |
| Determinism suite | Every merge on the representative set; nightly elsewhere | Severity-1 incident; beta promotion blocked | KLN-O-DET-1 | 0 |
| Deterministic simulation | Seeded scheduling order, time, network and faults | A failing seed replays exactly | KLN-O-SIM-1 | 0 |

## The CAS

### Object model

| Kind | Content | Typical size |
| --- | --- | --- |
| `Blob` | Opaque bytes: an imported STEP file, an image, a Wasm component | Bytes to gigabytes |
| `Record` | Deterministic CBOR: a Change, a tree, a `Material`, a signature, an attestation | Under 64 KiB |
| `Segmented` | A large typed array (mesh, Field values, sparse matrix) in keyed segments | Megabytes to terabytes |
| `Index` | Child `ObjectId`s with lengths and keys | About 16 KiB |

Records use RFC 8949's core deterministic encoding (shortest numbers, definite lengths, bytewise-sorted keys), one canonical quiet NaN and NFC text; large numeric arrays are little-endian typed arrays. An `ObjectId` is `SHA-256(domain tag ‖ type tag ‖ canonical bytes)` behind a one-byte algorithm code, computed before compression and encryption, so tiers may recompress or re-encrypt freely. A large value's identity is its root `Index` node's, and chunking parameters belong to the type tag, so changing them is a versioned format change.

Equal identities imply equal values but not the converse, so producers emit canonical forms, and Bodies carry a name-free second identity, the `GeometryId` (contract 5).

```rust
pub struct ObjectId { alg: HashAlg, digest: [u8; 32] }   // in base
#[non_exhaustive] pub enum HashAlg { Sha256 = 1 }

pub trait CasStore: Send + Sync {
    async fn get(&self, id: ObjectId) -> Result<Bytes, CasError>;   // verified; mismatch is Corrupt
    async fn has_many(&self, ids: &[ObjectId]) -> Result<BitVec, CasError>;
    async fn put(&self, kind: ObjectKind, canonical: Bytes, domain: &EncryptionDomain)
        -> Result<ObjectId, CasError>;
    async fn lease(&self, ids: &[ObjectId], ttl: Duration) -> Result<LeaseId, CasError>;
}
```

### Hashing, chunking and compression

**Decision D-KLN-14:** The CAS identity hash is SHA-256, with a one-byte algorithm code reserved for migration. *Why:* SHA-256 is approved under FIPS 180-4, is the digest of RFC 6962 logs, C2SP tiles and Git's SHA-256 format, and has instructions on most Tier 1 CPUs [unverified for every Tier 1 CPU]; Git's transition shows the cost of a hash without an agility field. *Rejected:* BLAKE3 (faster, but not NIST-approved, and chunk-parallel hashing recovers most of the gap); SHA-3 (slower in software).

BLAKE3's authors call `b3sum` "an order of magnitude faster" than `sha256sum`; Crucible hashes chunks in parallel, off the interactive path, and verifies large values chunk by chunk through `Index` nodes. Browsers hash each chunk (at most 1 MiB) with `crypto.subtle.digest` in engine workers, which supports SHA-256 but not streaming input, and keep the Wasm SHA-256 for small synchronous objects (R6-44). Targets: 1 GiB in under 150 ms natively on the reference laptop and under 1 s in a browser with 8 workers.

**Decision D-KLN-15:** Chunking is structure-aware first and byte-level second. Segmented values split into typed segments keyed by geometric content or space, never by names, grouped into chunks by a content-defined rule over their keys as in a prolly tree; opaque Blobs use FastCDC with normalized chunking. *Why:* byte-level chunking shifts every boundary when vertices renumber; Dolt's prolly trees make boundaries independent of insertion order; FastCDC is about 10× faster than the best open-source Rabin-based chunker at nearly equal deduplication. *Rejected:* fixed-size chunks; Rabin fingerprints; `EntityId` segment keys (a rename would re-chunk geometry). (revised in round 2)

| Value | Segment key and content |
| --- | --- |
| Body | Anvil's content-defined encoding leaves of at most 1,024 rows (D-ANV-9) |
| Mesh and `DisplayPackage` clusters | Morton code of a spatial cell; up to 4,096 triangles |
| Field values | Flux virtual partition, in 1 MiB chunks (FLX) |
| Sparse matrix | Row block |
| Opaque Blob | FastCDC: minimum 16 KiB, average 64 KiB, maximum 256 KiB |

A chunk ends after a segment whose key hash falls below a threshold (about 64 KiB chunks); `Index` nodes hold up to 512 children. Gregoriadis and colleagues found no impartial comparison of chunking algorithms before their 2024 study, so phase 1 benchmarks their alternatives on Crucible data.

**Decision D-KLN-16:** Each stored chunk names its codec, and tiers may recompress without changing identity. Fields use Flux's byte shuffling plus zstd, with pcodec as a measured alternative; other chunks use zstd at level 3 in hot tiers and 19 in the archive; display meshes on the wire use meshoptimizer's lossless vertex codec. *Why:* named codecs allow better ones later without a format break, and pcodec's authors chart better ratios than zstd on numeric data. *Rejected:* one codec for everything; lossy quantization in storage (changes identity); meshoptimizer's index codec for canonical data (it may rotate triangles).

A reader that does not know a chunk's codec fails with `CasError::UnknownCodec`; every codec in use decodes in every Tier 1 build.

### Encryption at rest

Desktops use OS disk encryption plus CAS encryption for labelled repositories, keyed in the OS keystore or a non-extractable WebCrypto key. Servers use envelope encryption per domain under KMS or HSM keys, customer-managed if wanted; end-to-end mode encrypts on clients under the customer's key service. An encryption domain is one tenant and one canonical label set. An object's key is `HKDF-SHA-256(domain key, ObjectId)`, chunks are sealed with AES-256-GCM under random 96-bit nonces, and the storage name is `HMAC-SHA-256(domain key, ObjectId)`, so plaintext `ObjectId`s never leave the domain's principals.

**Decision D-KLN-17:** Deduplication happens only within an encryption domain, using keys derived from a domain secret. *Why:* plain convergent encryption lets anyone confirm a guessed file, and DupLESS shows the remedy is a secret held by the authorized side; AES-GCM and HKDF are FIPS-approved [unverified: NIST SP 800-38D and SP 800-56C not opened]. *Rejected:* deduplication across tenants (reveals which designs exist); random per-write keys (no deduplication).

Deleting a domain key destroys the whole domain, which purges a contaminated label set, subject to retention locks.

### Collection, tiers and replication

Source history is never collected; derived values are cache. Roots are refs, the transaction log, releases with their cited results, open Proposals, legal holds and in-flight uploads. Writers upload objects before updating a ref, the server accepts a ref only over a present closure, and deduplicating writers take a 24-hour lease. The collector marks from the roots in a consistent view and sweeps unmarked, unleased objects older than 48 h; derived values outside the roots are evicted by GreedyDual-Size.

**Decision D-KLN-18:** Removing source history requires a purge: a record signed by two people and audited, listing the removed `ObjectId`s and the authority, which history verification treats as known-missing. Records under a Part 11 or legal-hold retention lock cannot be purged or crypto-shredded before retention ends, except by a deviation two people sign. *Why:* spills and court orders require deletion, while Part 11 requires retrieval throughout retention (R5-21). *Rejected:* history rewriting (breaks signatures); no deletion (cannot remediate a spill); single-administrator purges. (revised in round 2)

| Tier | Store | Contents | Eviction |
| --- | --- | --- | --- |
| 0 | Process memory | Kiln values | GreedyDual-Size |
| 1 | Local disk: 64 MiB append-only packs with an index; OPFS in browsers | Working set, unpushed Changes | Budget (default 20% of free disk); unpushed Changes never |
| 2 | Team server or cloud region: object storage plus a metadata store | All source, shared results, attestations | Collector plus budget |
| 3 | Archive object storage | Releases and their cited results | Retention policy only |

Refs and the transaction log live in SQLite on desktops and single-node team servers, PostgreSQL on larger team servers and FoundationDB in the cloud. Ref updates are compare-and-swap transactions; on bare object storage they use conditional writes, which S3 documents as failing with 412 when a concurrent writer wins. Cloud regions keep three synchronous metadata copies, replicate objects within the residency zone, and reconcile tiers by range-based set reconciliation [unverified: the abstract opened states no complexity bound].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Put and get by `ObjectId` | `CasStore::get`, `has_many`, `put`, `lease` | `CasError::Corrupt`; heal from another tier and quarantine | KLN-O-CAS-1 | 0 |
| Hashing | SHA-256 per chunk; `crypto.subtle.digest` in browsers | — | KLN-O-CAS-4 | 0 |
| Structure-aware chunking | Name-free segment keys; FastCDC for Blobs | Unkeyed values fall back to FastCDC with a warning | KLN-O-CAS-4 | 1 |
| Per-chunk codecs | Codec named per chunk | `CasError::UnknownCodec` | KLN-O-CAS-1 | 1 |
| Encryption domains | Tenant plus canonical label set; keys in a KMS | `CasError::KeyUnavailable`, never plaintext | KLN-O-CAS-3 | 2 |
| Collection | Mark, lease, sweep | The collector stops on any inconsistency | KLN-O-CAS-2 | 1 |
| Purge and retention locks | Two-person signed purge; retention locks | Purge refused under a lock | KLN-O-PURGE-1 | 2 |
| Tier replication | Residency-aware; range-based reconciliation | Residency violations blocked at write | KLN-O-REPL-1 | 2 |

## `repo`

### Changes and refs

| Object | Content |
| --- | --- |
| `Change` | Parents, tree, author, `on_behalf_of`, contributors, hybrid logical clock time, description, conflicts, signature; `ChangeId` is its `ObjectId` |
| `Tree` | Prolly-tree map from normalized path to file, `ingot.lock` included |
| `SourceFile` | Canonical Ingot text, a block map (block id to span) and span integrity provenance; segmented by top-level block above 64 KiB |
| `Tag` | Name and target Change; release tags add the release record and signatures |
| `RefTransaction` | Predecessors, the resulting view of all refs, principal, `api` call |
| Lifecycle records | Items, revisions, change orders, signatures, Evidence records, compliance records |

Time and authorship are history metadata that evaluation never reads; `ChangeId` wraps the Change's `ObjectId`.

**Decision D-KLN-19:** Edits become immutable Changes, as in Onshape's microversions: one per completed GUI action, per `edit.apply`, after 2 s without typing, at least every 60 s of continuous editing, and whenever something references the current state. *Why:* anyone can inspect, diff or branch from any state without a manual step, and Onshape shows the model works for CAD. *Rejected:* explicit commits only (loses states reviewers and agents need); one Change per keystroke (the live document keeps keystrokes for undo).

Refs are branch heads (`branches/<name>`), immutable tags (`tags/<name>`), Proposal heads (`proposals/<id>`) and agent branches (`agents/<agent>/<branch>`).

**Decision D-KLN-20:** Ref updates are recorded in a transaction log, as in Jujutsu. Each `RefTransaction` names its predecessors and the full resulting view of refs; concurrent transactions merge by a three-way merge of views, and a ref moved two ways becomes a conflicted ref. *Why:* full views give lock-free sync of clones, make undoing any repository action one new transaction, and double as the audit trail. *Rejected:* Git-style reflogs (per clone, unmerged); server locks (break offline work).

### Storage, Git export and span provenance

Objects live locally in append-only packs of up to 64 MiB with a sorted index, under a header naming format, hash algorithm and encoding versions. Git is an export, not the storage format: `crucible export git` writes Ingot text and `ingot.lock`, and because `OpSite`s derive from text alone (contract 5), re-importing and rebuilding leaves every `EntityId` unchanged.

Each source span records the integrity of the context that wrote it: trusted when a person typed it or the compiler produced it, otherwise the writer's integrity flags. Merges, rebases and moves preserve it, and `read` methods return untrusted free-text spans as `ExternalText` handles (contract 7.6). A merge endorses structure and typed values; free text becomes trusted only through a per-span endorsement record naming its bytes.

### Proposals and merge

A Proposal is a branch, a rationale and a CI report; CI evaluates the head and the would-be merge on untrusted-evaluation workers, and protected branches merge through a merge queue. A merge is clean only when every condition holds, and the driver records each failure as a typed conflict.

1. **Source.** Files merge three ways over their block trees: blocks match by block id, or by GumTree for files edited outside Crucible; child order merges by Parent-Child-Successor triples as in Mergiraf; order-insensitive lists merge as sets; text merges on tokens. `ingot.lock` merges per entry, and different pins of one package or operation conflict.
2. **Compilation and resolution.** The merge compiles and every `Query` resolves; a failure on neither parent is `Conflict::Semantic`.
3. **Verdicts.** No check's verdict on the merge is worse than on each parent that defines it, ordered `Pass` > `Undecided` > `Fail` > `Error`, at the declared fidelity on protected branches and `Interactive` elsewhere. `Skipped` counts as undefined, and a `Pass` whose `conditional_on` gains components ranks below one without them (CCR-KLN-8). A worse verdict is `Conflict::Check`.
4. **Interference.** Interference between Instances that neither parent has is `Conflict::Interference`.
5. **Geometric provenance.** Both sides modify, split or delete the same base entity, or one side's new entity intersects the other side's modified region at or below the merge clearance (default 0 mm): `Conflict::Geometric`.
6. **Connectivity.** A merged net that unions nets distinct in the base and in each side is `Conflict::NetMerge`, naming pins, nets and Changes; renamed nets match by provenance. The rule covers circuit nets, harness connections and `std::systems` interface connections (R4-03).

Symmetric-difference regions of base and side Bodies appear in review with Anvil's bound but never block.

**Decision D-KLN-21:** A merge is clean only when the merged design compiles and resolves, keeps every check's verdict, adds no interference, and has no provenance-level geometric or connectivity conflict. *Why:* a compiling text merge can still break a part or short two nets, and ordering verdicts covers checks defined on one side only (R3-15). *Rejected:* line-based merge; overlap of changed regions (flags the commonest pair of edits: a dimension change beside a new feature); last-writer-wins on features. (revised in round 2)

Conflicts are first-class, as in Jujutsu: a conflicted block holds base and side alternatives, simplifies when rebased, and evaluates as a `Failure` with three fixes (take one side, take both, edit). Several merge bases merge recursively into a virtual base, as Git's recursive strategy does [unverified: Git documentation not opened].

```rust
pub trait MergeDriver: Send + Sync {
    /// Checks the merge conditions in order; never writes refs.
    async fn merge(&self, kiln: &Kiln, base: ChangeId, left: ChangeId, right: ChangeId)
        -> Result<MergeOutcome, RepoError>;
}

#[non_exhaustive]
pub enum Conflict {
    Text { path: RepoPath, block: BlockId, alternatives: Alternatives },
    Lockfile { entry: LockEntryId, left: Pin, right: Pin },
    Semantic { diagnostics: Vec<Diagnostic>, from: [ChangeId; 2] },
    Check { check: CheckId, merged: CheckOutcome, parents: [Option<CheckOutcome>; 2] },
    Interference { assembly: EntityRef, a: InstancePath, b: InstancePath, volume: Quantity<Volume> },
    Geometric { base_entity: EntityId, left: HistoryRecord, right: HistoryRecord },
    NetMerge { pins: Vec<PinRef>, nets: [NetId; 2], from: [ChangeId; 2] },
}
```

### Diff, large assemblies and references

| Diff | Content | Matching |
| --- | --- | --- |
| Source | Block insertions, deletions, moves, token edits | Block id, else GumTree |
| Feature | Features added, removed, moved; parameter deltas with units | Feature block |
| Geometry | Changed regions per Part; volume, mass and box deltas; Hausdorff distance with its bound | `EntityId` provenance, then geometry |
| Metric | Every check's value and margin before and after | Check identity |
| BOM and lifecycle | Items added, removed or re-revised; quantity, effectivity, state and compliance changes | Item number and record identity |

Diffs are Kiln nodes, so source and feature diffs appear in milliseconds and geometry refines afterwards.

Products may hold 100,000 Instances of 10,000 unique Parts (phase 4 target). Partial clones name a filter (`source-only`, `paths(<pattern>)`, `depth(<n>)`, `display(<lod>)`) and fetch missing objects in batches, as Git's promisor remotes do. Envelope Bodies let large assemblies check clearance without B-reps. Target: a cold partial clone to an interactive view in under 15 s on the reference laptop over 100 Mbit/s.

References to packages, catalog parts and other repositories are pinned in `ingot.lock` as `{ source, selector, resolved }`; a selector is a release tag, a `ChangeId`, a followed branch that moves only on refresh, or a derived view. An unreadable reference resolves to its derived view for holders of `read_derived`, else fails with `AccessDenied`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Changes and transaction log | `Repo::record`, `update_ref`, `edit.undo` | Concurrent ref moves become conflicted refs | KLN-O-SIM-1 | 0 |
| Git export | Ingot text and `ingot.lock`; text-derived `OpSite`s | — | KLN-O-GIT-1 | 1 |
| Span integrity provenance | Per-span integrity; per-span endorsement | Untrusted spans returned as `ExternalText` | KLN-O-SPAN-1 | 1 |
| Source, compilation and verdict conditions | `MergeDriver::merge` | `Conflict::Text`, `Lockfile`, `Semantic`, `Check` | KLN-O-MERGE-1 | 1 |
| Geometric provenance conflicts | `HistoryRecord`s of both sides | `Conflict::Geometric` | KLN-O-MERGE-1 | 1 |
| Interference conflicts | Assembly interference on the merge | `Conflict::Interference` | KLN-O-MERGE-1 | 2 |
| Connectivity conflicts | Net partitions of base, sides and merge | `Conflict::NetMerge` | KLN-O-MERGE-1 | 3 |
| Semantic and geometric diff | `compare.diff` | Partial diff flagged when a side fails to build | KLN-O-DIFF-1 | 1 |
| Partial clone and lazy loading | Clone filters; batched promisor fetch | `RepoError::NotLocal` with a fetch fix | KLN-O-LARGE-1 | 2 |
| Cross-repository references | Pinned in `ingot.lock` | `AccessDenied`, `RefMissing` | KLN-O-XREF-1 | 2 |

## Collaboration

### Live documents

Each participant (visual editor, code editor, language server, agent) edits a branch's live document locally and syncs through a relay; the document is a movable tree of blocks (at least items, statements and parameters) whose heads, children and tails own every byte. Literals are last-writer-wins registers, so concurrent `65mm` and `70mm` never give `6570mm`. Other text is a sequence CRDT, and moves use the move operation of Kleppmann and colleagues, proved convergent in Isabelle/HOL.

Block ids are Loro tree node ids, mapped onto contract 5's text-derived identities for collaboration only; they never enter an `OpSite`. Each block parses under its own production (ING), so a block that stops parsing after concurrent edits keeps its kind and position, and Kiln serves its last good result as `Stale`.

**Decision D-KLN-22:** The live-document CRDT is Loro: a movable tree of blocks with Fugue text leaves. The unit of replication is (package, label set): blocks labelled above a document's label live in a separate document that only cleared participants receive, and the relay refuses moves into a lower-labelled document. *Why:* Loro has both structures with a stable format since 1.0, Fugue minimizes interleaving, import is fast (1.15 ms for a 1,659,541-operation document), and a replica must hold every causally prior operation, so one document cannot be filtered per recipient (R3-02). *Rejected:* a text-only CRDT with reparsing (moved features duplicate); Automerge 3 (Crucible would build the move layer [unverified that Automerge lacks native move]); operational transformation (central server); one document per package. (revised in round 2)

Every edit passes one reconcile step on the editing client, so it needs no coordination. An edit inside one block applies to its text, which covers nearly all typing; a structural edit reparses the range and matches blocks by GumTree, and visual-editor reorders emit tree operations. A delete concurrent with an edit inside the block wins, and both authors are offered a restore.

### Attribution, presence and locks

The relay checks every update against the sender's permissions and enforced locks, and records the document as a Change on the triggers of D-KLN-19. Device keys sign update batches, a Change lists its contributors, and the relay keeps the signed update log; undo is per principal. The language server joins as its user, and agents join only branches their scope allows.

Presence (cursor, selection, camera, drag ghost, an agent's current step) has a 30 s time to live and is never stored; presence and follow mode are organization settings (Deployment).

| Lock | Scope | Enforcement | Typical use |
| --- | --- | --- | --- |
| Advisory | Block, file or Item | Presence shows the holder; agents' edits fail with `LockHeld` | Busy documents |
| Enforced | Path, block or Item | Relay and merge reject others' changes; expiry default 8 h; administrators break it with an audited record | Unmergeable Blobs; regulated Items |

**Decision D-KLN-23:** Locks are optional and scoped; enforced locks exist for content that cannot merge and for regulated Items. *Why:* structural merge makes pessimistic locking unnecessary for Ingot, but an imported binary cannot merge and some quality systems require exclusive checkout. *Rejected:* mandatory check-out as PLM vaults use (serializes teams); no locks (unmergeable files lose work).

### Offline work and sync

**Decision D-KLN-24:** On reconnection the relay fast-forwards when no other participant changed the package meanwhile, whatever the duration. Otherwise, when the disconnection exceeded 60 s or concurrent edits touched blocks the client also edited, offline work rejoins as a branch through the merge driver; shorter, disjoint divergences merge as CRDT updates. *Why:* the hazard is unseen concurrent edits, not elapsed time (R3-46), and a CRDT guarantees convergence, not correctness. *Rejected:* a pure 60 s rule (sends a lone engineer through a branch); CRDT merge of every divergence; forbidding offline work. (revised in round 2)

One TLS 1.3 connection (WebSocket, or WebTransport where available) carries three protocols. Live sync sends signed update batches every 30 ms after version-vector catch-up. Object sync fetches missing closures as packs and pushes missing objects (`has_many`) before a compare-and-swap ref update. Events stream ref moves, CI results and review activity with resumable cursors.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Live co-editing | Loro document per (package, label set); signed updates | Unauthorized updates rejected with `AccessDenied` | KLN-O-COLLAB-2 | 2 |
| Reconcile step | Text and structural edits to tree operations | A block that stops parsing keeps its kind, position and last good result | KLN-O-COLLAB-1 | 2 |
| Labelled replication | Separate documents above a document's label | Moves into a lower-labelled document refused | KLN-O-LABEL-1 | 2 |
| Presence and locks | Ephemeral presence; advisory or enforced locks | `LockHeld` with holder and expiry | KLN-O-COLLAB-2 | 2 |
| Offline rejoin | Fast-forward, CRDT merge or branch | Conflicts become a Proposal to resolve | KLN-O-COLLAB-3 | 1 (branches), 2 (live) |

## Items, revisions and BOMs

PLM is not a separate vault: lifecycle records are signed CAS records in the design repository, BOMs are Kiln nodes, and gates are checks. SAE EIA-649's configuration management functions [unverified] map onto Items, orders, nodes over records and checks.

### Items

An Item is the lifecycle identity of something releasable: a `Part`, `Assembly`, `Document`, `Software` item, `Purchased` catalog part under an internal number, or `Program` (NC program, routing, work instruction or inspection plan). A Part carries its number in Ingot through MEC's `part(…, item:)`, while revisions, states, effectivity and signatures live in records, because releasing must not edit what it releases. An Item record holds number, kind, name, classification, home repository and path, make or buy, unit of measure and labels.

A numbering policy sets the format and whether gaps are allowed. The server leases clients blocks of 20 numbers for offline work; unused numbers return as void records after 30 days, and where gaps are forbidden the server replaces provisional numbers at first push.

**Decision D-KLN-39:** Each record type (item number, revision label, lifecycle state, change order, BOM, approvals) has a system of record, `Crucible` or `External(connector)`. Under `External`, numbers come through ECO's connector, the release Act publishes a release package (STEP AP242 with PMI, PDF drawings, BOM, NC programs, a source archive with its digest) into the external item revision, and external approvals return as signed External inputs naming the Crucible approval subject. *Why:* most adopters keep an enterprise PLM authoritative for years (R4-19), and binding approvals to the subject keeps D-KLN-28. *Rejected:* Crucible as the only system of record; one-way export.

An organization parts-policy package lists approved `Purchased` Items with approved manufacturers and their part numbers, lifecycle (`Preliminary`, `Approved`, `NotRecommended`, `Obsolete`) and preferred flags. ELX selections and MEC's `fasten` resolve over approved parts first and reach the open catalog only with a recorded waiver, so an unapproved part fails the policy check (R4-20). A new-part request is one Proposal creating the number, catalog facets and approved manufacturers.

**Decision D-KLN-25:** Interchangeability decides between a new revision and a new item number, and Crucible computes it by comparing two definitions at their interfaces: mating faces and mates, envelope, mass properties within tolerance, and declared fit and function checks. A person confirms either verdict. *Why:* form-fit-function judgment is the most error-prone step of change control, and Crucible holds the data. *Rejected:* human judgment alone (inconsistent); a fully automatic verdict (some functions are not modelled).

Phase 2 change orders take a human interchangeability verdict; the computed check arrives in phase 3.

### Revisions and lifecycle states

A revision's `ItemDefinition` holds the `GeometryId`s of the Part or Assembly with PMI attached by canonical entity number, the `Material` version, properties, the BOM by value and documents by semantic content (views, annotations, notes). The revision record adds the label, source `ChangeId`, release tag, classes of cited results and signatures.

**Decision D-KLN-26:** Revision identity is content-based: an Item is modified since release exactly when its `ItemDefinition` differs from every definition its revision records. An engine or std upgrade that keeps topology, PMI, properties and document content, and moves geometry only within the definition tolerance (default the smaller of 0.1 µm and 1% of the Item's tightest tolerance), adds its definition to the revision through the upgrade Proposal. Lifecycle-bound text (revision label, dates, approvers, serials, MEC's revision markers, ELX silkscreen revisions) is filled at output time and excluded from the definition. *Why:* refactors change no `GeometryId` (R3-01), bit-level upgrades must not mark released Items modified (R4-17), and a title block cannot be part of the revision it prints. *Rejected:* revision on any source change; `ObjectId` identity (renames would void releases); PDF bytes in the definition. (revised in round 2)

Revision labels are letters skipping I, O, Q, S, X and Z, as ASME Y14.35 practice recommends [unverified], or numbers; in-work iterations are Changes and need none.

| State | Meaning | Entered by |
| --- | --- | --- |
| `InWork` | Being designed | Creation; a Change altering a released definition |
| `InReview` | Frozen candidate in an open order | Submission |
| `Prototype` | Released for prototype builds | An order with prototype scope |
| `Released` | Approved for production at its effectivity | The release Act |
| `Superseded` | Replaced, valid within its effectivity | The next revision's release |
| `Obsolete` | Not for new builds | An order with obsolescence disposition |

Entering `Released` requires every check to hold a non-provisional `Pass` on a release-accepted class or a signed waiver, every child Item released already or in the same order, the required Approvals and no open conflicts. A policy package may replace the state machine. Phase 1 ships GP1's minimal lifecycle: item numbers, revision labels on release tags, `InWork` and `Released`, and the EBOM.

### Effectivity and variants

Windchill supports Serial, MSN, Block, Lot and Date effectivity; Crucible has one record with four kinds (`Date`, `Serial`, `Lot`, `Block`; an MSN is a `Serial`) in an end-item context. A configuration point (an end item and a value) is an input cell: Kiln picks the effective release, resolves each usage to the child revision effective there and assembles released `ItemDefinition`s without re-evaluating source. Substitution needs interchangeable revisions and exactly one applicable revision per usage and point; MFG's as-built records link to their point.

**Decision D-KLN-27:** Variants are `#[configuration]` parameters of assembly features (contract 6), and Kiln computes the 150% BOM by abstract interpretation of the IIR with configuration parameters symbolic. Instances inside a variant region carry its condition, ING rejects an Instance whose existence depends on computed values, and SAT checks over conditions and `require` rules report dead usages, slot collisions and unbuildable configurations. *Why:* variants stay in the one model and a solver proves rule consistency (R3-18). *Rejected:* variant BOM tables (drift); enumerating configurations (exponential); round 1's `options` and `when` keywords (contract 6). (revised in round 2)

```
pub feature drone(#[configuration] cfg: DroneConfig) -> Assembly {
    let asm = assembly(frame(cfg.frame))
    if cfg.camera { asm.add(camera_mount(), at: asm.port(role: nose)) }
    asm.require(cfg.battery != Battery.extended or cfg.frame == Frame.long)
}
```

A 100% BOM is the 150% BOM under one assignment, itself a configuration point. CI builds the declared sellable configurations plus a pairwise covering set and evaluates the rest symbolically (R4-21).

### BOM views and where-used

| View | Content | Source |
| --- | --- | --- |
| EBOM | Items, quantities with units, find numbers, reference designators, variant conditions, effectivity; lines without geometry from MEC's `bom_item` | Assembly graph at a Change or configuration point |
| MBOM | Phantoms, kits, raw stock, consumables, manufacturing-only Items | MFG packages referencing EBOM Items |
| Service BOM | Field-replaceable units, spare kits, service effectivity | EBOM plus service annotations |

Views are Kiln nodes, never edited directly. The MBOM reconciliation check verifies that every EBOM Item and quantity is consumed exactly once per configuration or marked as not manufactured. BOMs export as CSV, as STEP AP242 product structure and through ECO's ERP connector.

The where-used index gains usage edges (parent revision, child Item, quantity, effectivity, condition) at each release and protected Change, across repositories and through `Purchased` Items. Lookups return parents up to end items, and usages the caller cannot read appear only as a count. Where-used drives change impact, end-of-life notices and vulnerability response.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Items and numbering | Item records; leased number blocks | Duplicate number rejected at push, naming the owner | KLN-O-PLM-2 | 1 |
| System of record | `Crucible` or `External(connector)` per record type | The release Act fails at commit while the connector is unreachable | KLN-O-PLM-10 | 2 |
| Parts policy | Approved `Purchased` Items; recorded waivers | Policy check fails without a waiver | KLN-O-PLM-11 | 2 |
| Interchangeability | Interface comparison | Unmodelled interfaces need a human verdict | KLN-O-PLM-3 | 3 |
| Revisions and states | Revision records; policy state machine | Guard failures name every unmet condition | KLN-O-PLM-1 | 1 (`InWork`, `Released`), 2 |
| Definition equivalence | Definition tolerance; late-bound fields | Out-of-tolerance upgrades mark Items modified | KLN-O-PLM-9 | 2 |
| Effectivity | Records and configuration points | Gaps and overlaps fail the consistency check | KLN-O-PLM-4 | 3 |
| Variants and 150% BOM | `#[configuration]`; abstract interpretation; SAT checks | Dead usages, collisions and unbuildable configurations reported | KLN-O-PLM-5 | 3 |
| BOM views | EBOM, MBOM and service BOM nodes | Reconciliation failure is a check failure | KLN-O-PLM-6 | 1 (EBOM), 2 |
| Where-used | Indexed and access-filtered | Restricted usages counted, never named | KLN-O-PLM-7 | 2 |

## Change control, signatures and compliance

### Change orders

| Record | Purpose and mechanism |
| --- | --- |
| Change request (ECR) | A problem or improvement with evidence; linked from nonconformances, complaints, CAPAs, field failures or agent findings |
| Engineering change order (ECO) | A Proposal with lifecycle scope: affected Items with from and to revisions, effectivity, stock disposition, plan |
| Manufacturing change order (MCO) | A Proposal under the MCO policy class (D-KLN-38) |
| Change notice (ECN) | A signed record created by the release, delivered as an event, with acknowledgements |
| Deviation | A temporary departure for given serials or lots, with expiry; granted by the `deviation` Act |

An order starts from requests on a branch from the named release; agents prepare work as Proposals under it. Impact analysis covers where-used, open orders on the same Items, interchangeability, MBOM reconciliation, compliance and dispositions. Submission moves affected Items to `InReview` and freezes the branch. Release goes through the release Act. `act.prepare` produces a plan whose subject is the order's `ApprovalSubject`, and the order's approvals are that plan's Approvals, so one signature serves both (R3-22); the merge, tag, revision records, effectivity and notice commit in one metadata transaction. Downstream acknowledgements are tracked until the order closes.

[[DIAGRAM: Change order lifecycle: request → order (branch + Proposal) → impact analysis → submitted (Items InReview) → act.prepare (plan over the ApprovalSubject) → Approvals of the plan digest → act.commit (merge, tag, revisions, effectivity, notice) → closed; back-arrow from Approvals to the order: "subject changed: approvals void".]]

**Decision D-KLN-28:** An approval signs the `ObjectId` of the order's `ApprovalSubject` (contract 5): base revisions, `ItemDefinition` `GeometryId`s with PMI, the check-verdict digest, effectivity and Evidence record ids. The head `ChangeId` and the full CI report are unsigned provenance, so a rebase or CI re-run keeps approvals exactly when the subject is unchanged, and any change to the subject voids them. *Why:* a hash makes a post-approval edit impossible to miss, while signing the `ChangeId` and CI report voided approvals of identical content (R3-16). *Rejected:* approvals by reference to a branch; signing the head `ChangeId` and CI report (round 1). (revised in round 2)

An order's author cannot be its only approver, and agents never sign; they attach analysis as evidence. Approval requests are server records assigned by Cedar policy (contract 7.6), and concurrent orders on one Item serialize at release.

**Decision D-KLN-38:** Manufacturing change orders form their own policy class: limited to MBOM, routings, programs, fixtures, work instructions and inspection plans, approved by manufacturing roles, and rejected if they touch an EBOM Item definition. `Program` Items carry their own revisions, effectivity by work order or lot, and states `Prototype` (first article under a deviation), `Proven` (after a passing first-article record) and `Released`; program approvals sign the posted program and its simulation evidence. *Why:* shops change feeds and tools daily without touching the part (R4-11). *Rejected:* every shop edit as an engineering order; untracked program edits.

An engineering order that changes a part returns exactly its dependent programs to `Prototype`.

### Electronic signatures

A signature record holds signer, printed name, server time (no offline signing), meaning (`Authored`, `Reviewed`, `Approved`, `Released`, `Verified` or a policy meaning), the signed `ObjectId`, the authentication event, an algorithm id and the signature. People sign with ECDSA P-256 keys in platform keystores or WebAuthn authenticators [unverified: FIPS 186-5 and keystore documentation not opened]. Every Approval of a release or of the highest Act risk class is a signature record (R5-21).

**Decision D-KLN-42:** Every signature record carries an algorithm id. By phase 2, release tags, transparency checkpoints and provenance are dual-signed with the current algorithm plus ML-DSA-87 from FIPS 204 (final on 13 August 2024), or plus LMS for release signing, and long-retention records are re-timestamped into an evidence chain before an algorithm retires. *Why:* records must verify for decades, and national-security customers will require CNSA 2.0 algorithms [unverified: the CNSA 2.0 FAQ could not be opened]. *Rejected:* classical signatures only; replacing algorithms in place (old records stop verifying).

| 21 CFR Part 11 | Crucible mechanism |
| --- | --- |
| 11.10(a) validation | Validation package from this tab's oracles; hash-verified records |
| 11.10(b) complete copies | Signed records exported as PDF/A plus JSON, with an offline verifier |
| 11.10(c) retrieval through retention | Retention locks against purge and crypto-shredding (D-KLN-18) |
| 11.10(e) audit trails | Transaction and audit logs in the transparency log |
| 11.10(f), (g), (h) system checks | Lifecycle guards; Cedar on every request; device-signed Changes and Evidence records |
| 11.10(i), (k) personnel and documentation | Vendor training records; controlled release documentation with change notices |
| 11.30 open systems | Cloud mode treated as open: domain encryption, signed records, end-to-end mode |
| 11.50, 11.70 manifestation, no excision | Printed name, time and meaning on every rendering; a signature covers one `ObjectId` |
| 11.100 to 11.300 | One principal per person, never reassigned; re-authentication per signing |

The 11.100 certification to FDA is the customer's act. FDA's QMSR, effective 2 February 2026, incorporates ISO 13485:2016, and 820.10(c) applies its design and development clause 7.3 to class II and III devices, to class I devices automated with computer software and to listed class I types. Orders, checks and reports supply the design history. AS9100 configuration management and first article inspection [unverified] map onto Items, orders, effectivity and MFG's QIF 3.0 results.

### Traceability and compliance

Requirements are `std::systems` records in source or imported (ReqIF import is planned [unverified that ReqIF suits every source tool]); a `require` names those it verifies, in syntax ING owns. The traceability matrix is a Kiln node from requirement to check to outcome to evidence. Coverage is a check: each requirement needs a verifying check of its method (`Analysis`, `Test`, `Inspection` or `Demonstration`), each `Test` requirement an Evidence record on the released revision, and a changed requirement's links stay suspect until a person signs them.

Compliance is a check over data. MFG owns the substance rules (RoHS, REACH and SCIP, conflict minerals); this tab owns compositions rolled up from `Material` versions, signed supplier declarations, regulation packages pinned as External inputs, exemptions signed by `quality`, and verdicts per revision (`Compliant`, `NonCompliant`, `Unknown`). Missing data is `Unknown` and blocks releases that require compliance, and a new regulation version re-evaluates released revisions and opens change requests through where-used.

Products with firmware fall under the EU Cyber Resilience Act, whose reporting duties for actively exploited vulnerabilities apply from 11 September 2026: an early warning within 24 hours and a notification within 72. `Software` Items carry a CycloneDX 1.7 software bill of materials per release, and where-used lists affected shipped serials within minutes (target).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Approval subjects | Approvals sign the subject's `ObjectId` | A changed subject voids approvals | KLN-O-CHG-1 | 1 |
| Change requests, orders and notices | Records plus Proposal; release Act | Guard failures name unmet conditions | KLN-O-CHG-1 | 2 |
| Manufacturing change orders | MCO class; `Program` Items | An MCO touching an EBOM definition is rejected | KLN-O-PLM-8 | 2 |
| Electronic signatures | Signature records; re-authentication; Part 11 mode | Failed re-authentication blocks signing and is audited | KLN-O-SIG-1 | 2 |
| Signature agility | Algorithm ids; dual signatures | An unknown algorithm fails verification, naming its id | KLN-O-SIG-2 | 2 |
| Requirements traceability | Requirement records; `verifies` links | Uncovered or suspect requirements block release | KLN-O-TRACE-1 | 2 |
| Compliance checks | Regulation packages, declarations | Missing data yields `Unknown` | KLN-O-COMPL-1 | 3 |
| Vulnerability where-used | `Software` Items with software bills of materials | Unknown contents flagged | KLN-O-VULN-1 | 3 |

## Supplier collaboration and data release

### Data leaving a tenant

**Decision D-KLN-40:** Every Act that moves bytes out of a tenant runs one commit-time stage, `release_data { recipient, payload, purpose, authorization }`. It checks labels against the recipient's attributes, restricted-party screening and, for `export_controlled` payloads, an export authorization record (licence, exception or exemption); it writes a deterministic watermark, an expiry and an audit entry. The family covers sending to a supplier, requesting a quote, export, Git mirror pushes, archive export and passport publication; agent writes to a branch shared with another organization run the same checks, need `share_external` and are refused to tainted contexts. *Why:* six exit paths had six sets of controls (R5-06). *Rejected:* per-path controls; exports as plain methods.

A `RecipientRecord` holds the organization, endpoints (email domains, API hosts, connector ids), verification by out-of-band callback to a known contact with its date, screening result and date, clearance attributes (US-person status, country) and expiry. Recipient records are policy data: a change needs `policy:admin` plus a second person, is refused from a context with `instruction_tainted` or `data_untrusted`, and takes effect after 24 h with notice to the previous contact. The approval page flags recipients changed in the last 7 days (R5-05).

Watermarking is a recorded deterministic transform: the data-package record stores the release file's hash, the recipient, the watermark parameters and the recipient file's hash, so a verifier ties any returned or leaked file to its release (R5-40).

### Supplier packages and derived views

Suppliers are external organizations with their own principals and never browse a design repository. They receive signed data packages listing contents, source revisions, recipient, labels and expiry: STEP AP242 with PMI, 3MF or glTF, PDF drawings with QIF 3.0 inspection plans, requirements and derived models.

Suppliers return quotes, feedback (comments or Proposals on a shared branch), QIF results, certificates of conformance and material declarations, signed by their principals and read by agents as `ExternalText`. Expiry revokes access but cannot recall downloads; the audit log records what each supplier received.

| Derived view | Recipient gets | Stays private |
| --- | --- | --- |
| Frozen geometry | Released Bodies at fixed parameters, with PMI | Source, history, parameters |
| Envelope and interfaces | An offset hull at a declared clearance, interface faces, mates, mass properties | Internal geometry |
| Behavioral model | An FMI 3.0 FMU or reduced model with its `ValidityEnvelope` | Geometry and source |
| Remote parametric model | A feature callable with parameters, evaluated on the owner's workers | Source and intermediate values |

**Decision D-KLN-31:** Parametric sharing without source uses remote evaluation on the owner's workers, never shipped compiled code. *Why:* code on the recipient's machine, Wasm included, can be decompiled, while remote evaluation keeps source with its owner and still caches by `OpKey`. *Rejected:* obfuscated Wasm components (false security); encrypted packages (the key must reach the recipient).

Each remote parametric share declares per-recipient query budgets, parameter ranges and steps, and optional output simplification; every query is audited, and one over budget fails with `ShareQuotaExceeded` (R5-41). Redaction replaces `confidential` features by Anvil's defeaturing or envelopes within a declared deviation and strips names, comments, provenance ids and history. A redaction check verifies before signing that no source object or string leaks.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Data-release stage | `release_data` checks at `act.commit` | Commit refused, naming the failed check | KLN-O-RELEASE-1 | 1 |
| Recipient records | Two-person changes; 24 h delay | Changes from tainted contexts refused | KLN-O-RELEASE-1 | 1 |
| Supplier packages and watermarks | Signed packages with expiry; recorded transform | Expired or label-mismatched access denied | KLN-O-SHARE-2 | 3 |
| Derived views and redaction | Signed packages; redaction check | A leak refuses signing | KLN-O-SHARE-1 | 3 |
| Remote parametric shares | Budgets, ranges, steps, audit | `ShareQuotaExceeded` | KLN-O-SHARE-3 | 3 |

## Security

### Identity and authorization

| Principal | Authentication | Keys |
| --- | --- | --- |
| Person | SSO over OpenID Connect or SAML 2.0; local accounts only on desktop and air-gapped installs; WebAuthn second factor | Hardware-backed device key per device |
| Agent | Registered by an owner; short-lived tokens by token exchange (AGT) | Ephemeral key bound to the token |
| Service | Workers, builders, runners, integrations | Workload identity or mTLS certificates |
| External organization | Its identity provider, or invited accounts with WebAuthn | As for persons |

SCIM 2.0 provisions users, sessions last 12 h, signing always re-authenticates, and offline desktops hold a 7-day refresh grant before losing push and labelled reads.

**Decision D-KLN-43:** Logs, records, transcripts and API logs hold pseudonymous principal ids. An identity directory maps ids to names under a per-person key that can be crypto-shredded, except under documented legal holds such as Part 11 retention or litigation, which keep the key so signatures still render names. *Why:* append-only, decades-long records otherwise hold personal data that GDPR Article 17 lets people erase unless needed "for compliance with a legal obligation" (R5-27). *Rejected:* names in records; pruning logs (breaks verification).

**Decision D-KLN-29:** Authorization uses Cedar policies, evaluated in process on every request, including live-document updates at the relay. *Why:* Cedar covers role- and attribute-based access in one language, is implemented in Rust with a Lean model, and its analysis proves that a policy change grants no unintended access. *Rejected:* Open Policy Agent with Rego (Cedar's authors report better performance and readability); hand-written role checks.

Roles come from identity-provider groups (`viewer`, `commenter`, `editor`, `maintainer`, `approver`, `release_manager`, `export_officer`, `quality`, `admin`). Attributes describe principals (organization, US-person status, location, training, licences, clearances) and resources (labels, Item state, repository, path). Actions are `read_source`, `read_derived`, `evaluate`, `edit`, `push`, `merge`, `approve`, `sign`, `release`, `purge` and `manage_policy`; deny overrides allow, the default is deny, and policy changes are `propose.policy` Proposals whose access changes Cedar lists before merge.

**Decision D-KLN-41:** Two distinct people approve each of: clearing an endpoint or recipient for `confidential` or `export_controlled` data; declassification; Cedar changes that widen access; auto-merge policy; recipient-record changes; oracle and protected-path changes; and purges. For label-related items one holds `export_officer`. *Why:* one phished or coerced administrator could otherwise export a whole ITAR program (R5-15). *Rejected:* single approvers with audit only. Policy Proposals from contexts holding untrusted data are refused, and break-glass access alerts every administrator and requires review afterwards.

Protected refs take rules per pattern: no direct pushes, required checks and reviews without self-approval, signed Changes, forward-only refs and immovable tags, change orders for `Released` Items, and no agent ref updates, approvals or signatures. Agents follow AGT's label and taint model, in which a tainted session holds all three Rule of Two properties in a narrow form, supervised by review and Act approval. `repo` enforces the boundary: agents write only `agents/*` refs with the intersection of their scope and their owner's permissions, and never sign, approve, release, change policy or edit `oracles/`.

### Labels and export control

Labels follow contract 5's lattice (`level`, `controls` such as (ITAR, category) or (EAR, ECCN), organization `scopes`, `integrity`, `licences`) and attach to repositories, paths, Items, records, CAS objects and API responses. Kiln joins them through every derivation, and every write carries at least its context's label (contract 7.6). Lowering a label needs a declassification record signed by two people, one an export officer, naming the derived view and the reason.

**Decision D-KLN-32:** Export-controlled data is handled by labels that propagate through Kiln and model contexts, policies over principal attributes, residency-bound storage and compute, and an optional end-to-end mode. *Why:* 22 CFR 120.56(a)(1) counts as a release "Visual or other inspection by foreign persons of a defense article that reveals technical data to a foreign person", so every path to the data needs a check, derived values included. *Rejected:* air-gapped installations as the only option (they stay available but isolate teams); repository flags without propagation (derived values leak). (revised in round 2)

Residency can require storage and compute in named regions under staff with named attributes, and the scheduler refuses other placements with `ResidencyDenied`. Notifications, emails, crash reports, reproduction bundles, OS backup and clipboard follow PLT's and UIX's label-aware egress rule above `internal` (R5-16).

End-to-end mode keeps plaintext off Crucible's cloud. 22 CFR 120.54(a)(5) treats as not exported unclassified technical data end-to-end encrypted with FIPS 140-2 or successor modules, neither stored in nor sent to or from a §126.1 country; EAR 15 CFR 734.18(a)(5) is similar. Keys stay in the customer's key service, evaluation runs on customer workers, and keys go only to the originator, U.S. persons in the United States or others authorized (120.54(b)(2)); qualification is the customer's legal determination.

### Audit and encryption

Every write, read of labelled data, policy decision, signature, login, Act and administrative action is an audit entry (pseudonymous principal, action, resource ids, decision and policy ids, device, server time, request id), never labelled content. AGT's audit records are entries in the same log, with one retention rule and one verifier (R5-39).

**Decision D-KLN-30:** The audit log, repository transaction logs and release tags are entries in per-tenant transparency logs served in the C2SP tlog-tiles format, with checkpoints signed by the deployment and optionally cosigned by customer witnesses. *Why:* a Merkle log following RFC 6962 makes any rewrite or fork detectable by anyone holding an earlier checkpoint, static tiles make verification cheap, and witnesses keep the cloud operator honest. *Rejected:* an append-only database table (rewritable undetectably); a public blockchain (cost, latency, metadata leakage).

Clients keep the last checkpoint seen and verify consistency on every sync. Checkpoints carry Ed25519, as tlog-tiles requires for the public witness network, ECDSA P-256 in FIPS mode and ML-DSA by phase 2 (D-KLN-42). Release records keep the longest retention configured, transcripts and API logs 12 months by default, and phase 1's signed append-only audit log already uses the tlog-tiles layout, without witnesses.

Transport is TLS 1.3, mutual between servers, workers and runners. FIPS mode routes all cryptography through a FIPS 140-3 module from PLT's provider, AWS-LC through aws-lc-rs being the leading candidate [unverified: current certificate status]; NIST moves FIPS 140-2 modules to the historical list after 21 September 2026. Release and checkpoint keys live in HSMs and are never exported.

ECO owns the software supply chain (reproducible builds, SLSA provenance, Sigstore, The Update Framework, namespaces and package policy), and AGT owns prompt injection and exfiltration by agents.

| Threat | Controls | Residual risk |
| --- | --- | --- |
| Malicious package | No ambient I/O in evaluation; fuel and memory limits; ECO's publisher controls | Inputs encoded into outputs, which leave only through `release_data` |
| Cache poisoning | Contract 7.8 pools, attestation, two-builder agreement | Two colluding trusted builders |
| Malicious insider | Least privilege, labels, two-person rules, witnessed audit | Authorized reads by a cleared insider |
| Cloud operator | Customer keys, end-to-end mode, witnessed logs | Object sizes and timing |
| Network attacker or stolen device | TLS 1.3, mTLS, signed updates; disk encryption, hardware keys, revocation | Data cached on the device |

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Identity | OIDC or SAML, SCIM, WebAuthn, device keys | Failed authentication audited | KLN-O-POLICY-1 | 1 |
| Pseudonymous records | Identity directory with per-person keys | Erasure refused under a legal hold | KLN-O-AUDIT-2 | 2 |
| Authorization and branch protection | Cedar on every request and relay update; rules per ref pattern | `AccessDenied` naming the missing permission | KLN-O-POLICY-1 | 1 |
| Two-person rule | Listed changes need two people | One approval leaves the change pending | KLN-O-POLICY-1 | 1 |
| Labels and declassification | Lattice labels; two-person declassification | `label.write_down` | KLN-O-LABEL-1 | 1 |
| Residency | Region and operator constraints | `ResidencyDenied` | KLN-O-LABEL-1 | 2 |
| End-to-end mode | Customer keys; recipient eligibility | Key release refused to an ineligible recipient | KLN-O-LABEL-2 | 3 |
| Tamper-evident audit | tlog-tiles logs; witnesses | A fork is detected at the next sync | KLN-O-AUDIT-1 | 1 (signed log), 2 (witnesses) |
| FIPS mode | FIPS 140-3 provider | Non-approved algorithms refused | KLN-O-SIG-2 | 2 |

## Deployment

### Modes

Modes differ in services and data location, never in features.

| Mode | Services | Metadata store | Phase |
| --- | --- | --- | --- |
| Desktop | Kiln, local CAS and repository, local relay | SQLite | 1 |
| Browser | The engine in a worker, one engine per origin | SQLite on OPFS (`opfs-sahpool`) | 1 |
| Team server | One container: repository server, CI coordinator, microVM CI, optional workers; relay and runner gateway from phase 2 | SQLite, or PostgreSQL for larger teams | 1 |
| Cloud | Regional cells: gateways, relays, repository servers, worker fleets, per-tenant logs | FoundationDB | 2 |
| Regulated cloud | US-only regions; US-person operations staff for ITAR tenants; NIST SP 800-171 controls with FedRAMP Moderate equivalence evidence; DFARS 252.204-7012 support (72-hour reporting, 90-day image retention, forensic access) | FoundationDB | 3 |
| On-premises and air-gapped | The cloud stack on the customer's Kubernetes, or a team server; air-gapped adds no external network and an offline licence | PostgreSQL or FoundationDB | 2, 3 |

A desktop is a full peer that works offline and connects to any number of remotes as a Git clone does. Medical customers receive contract 7.7's Computer Software Assurance package, built from this tab's oracle results and release notes.

**Decision D-KLN-33:** The desktop is local-first: the local repository is authoritative for unpushed work, and everything except remote services (shared cache, cloud workers, relays for other machines) works offline. *Why:* engineers work on aircraft, at plants and on secure networks, and local-first makes interactive latency independent of the network. *Rejected:* a thin client over a cloud model (fails offline and air-gapped).

**Decision D-KLN-44:** A browser origin runs one engine. The first tab's engine worker takes a Web Lock and owns every OPFS write handle (CAS packs, journal, SQLite on `opfs-sahpool`); other tabs run the UI only and reach that engine through a `MessagePort` brokered by a `SharedWorker`, and when the owner closes, the next tab takes the lock and replays the journal. *Why:* sync access handles lock files exclusively and `opfs-sahpool` fails in a second tab, so two engines would fail or corrupt state (R6-15). *Rejected:* one engine per tab; the `opfs` VFS (needs `SharedArrayBuffer`).

### Sync, scale and recovery

Mirrors keep label-filtered read replicas at sites; federation joins two organizations' servers through signed packages and shared branches, each enforcing its own policy. Air-gapped sites exchange signed bundles: `crucible bundle create --since <checkpoint>` writes objects, ref updates and log proofs, and `crucible bundle import` verifies signatures, closure, labels and log consistency first, after the receiving domain's review step.

| Scope | Target (phase 4 unless marked) |
| --- | --- |
| Desktop | Local CAS up to 2 TiB; 10 million Changes per repository; contract 13.3's open and rebuild rows |
| Team server, 16 cores, 64 GiB | 200 active users, 50 live documents, 1,000 Changes per minute, 20 TiB (phase 2) |
| Cloud cell | 50,000 active users; ref update p99 under 200 ms; 10 GB/s object fetch; 100 participants per document |
| Cloud workers | 10,000 cores per tenant within 5 minutes; first remote result for cached inputs under 1 s |
| Repository | 100 TiB of results; 10⁹ objects; where-used over 10⁶ Items under 1 s |

A restore is correct when every ref's closure is present with matching hashes and every log matches checkpoints held by clients and witnesses; the restore verifier checks both. Team servers target 5 minutes of data loss and 4 hours to recover, through log shipping, object versioning and nightly test restores. The cloud targets no loss within a region, 15 minutes across regions and 1 hour to fail over, with write-once backups kept 35 days.

### Privacy

Deployments ship records-of-processing entries, a DPIA template and the list of hosted model providers as sub-processors (AGT). Presence, follow mode and approval tab-view recording are organization settings, and works-council mode disables per-person activity analytics, since BetrVG §87(1) item 6 gives German works councils co-determination over "technical devices designed to monitor the behaviour or performance of the employees".

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Desktop offline | Full local repository and Kiln | Remote services report `Offline` with the queued step | KLN-O-DEPLOY-1 | 1 |
| Browser engine ownership | Web Lock; brokered `MessagePort`; journal replay | A second engine refuses to start | KLN-O-DEPLOY-1 | 1 |
| Team server and on-premises | One container; Kubernetes package | Refuses a schema mismatch with a migration hint; preflight names missing prerequisites | KLN-O-DEPLOY-2 | 1, 2 |
| Cloud and regulated cloud | Regional cells; regulated controls | Cell failover | KLN-O-DEPLOY-3 | 2 (cloud), 3 (regulated) |
| Air-gapped bundles | Signed bundles | Rejected on any verification failure, with the reason | KLN-O-DEPLOY-4 | 3 |
| Restore verifier | Closure and log consistency | Lists missing or inconsistent objects | KLN-O-RESTORE-1 | 2 |
| Privacy controls | Pseudonymous ids; activity settings; works-council mode | — | KLN-O-AUDIT-2 | 2 |

## External interfaces and physical tests

### `api` methods and events

AGT owns the method catalog; this tab supplies repository behavior within contract 7.6's eight groups, and every response carries its `ChangeId`, generation and labels.

| Methods | Group | Agents |
| --- | --- | --- |
| `read.tree`, `read.source`, `read.history`, `read.audit`, `read.where_used`, `read.bom` | Read | Access-filtered; untrusted free text by handle |
| `edit.apply`, `edit.revert`, `edit.create_branch`, `edit.undo` | Edit | Own branches only |
| `evaluate.*`, `evaluate.cancel` | Evaluate | Within budget |
| `compare.diff`, `compare.merge_preview` | Compare | Allowed |
| `propose.*`, `propose.change_request`, `propose.change_order`, `propose.policy` | Propose | Drafts only; a person submits; never `propose.policy` |
| Act classes `release`, `deviation`, `declassify`, `purge` and the `release_data` family | Act | May prepare `release` and data-release plans; never approve |

**Decision D-KLN-34:** Events carry identifiers and states, never design content; receivers fetch content through `api` with their own credentials. ECO owns the envelope (CloudEvents), delivery and signing (D-ECO-12); this tab defines its event types and carries a per-repository sequence number in the CloudEvents `sequence` extension attribute. *Why:* thin events keep policy, labels and audit in one place, and one envelope serves every tab (R3-23). *Rejected:* full payloads (bypass policy); this tab's round 1 envelope and HMAC signing. (revised in round 2)

Event types: `change.created`, `ref.updated`, `ref.conflicted`, `tag.created`; `proposal.opened`, `proposal.updated`, `proposal.merged`, `ci.completed`, `check.failed`, `evidence.recorded`; `change_request.created`, `change_order.submitted`, `change_order.approved`, `change_order.rejected`, `release.created`, `change_notice.issued`, `item.state_changed`, `deviation.granted`; `compliance.alert`, `vulnerability.affected`, `policy.changed`, `audit.anomaly`, `budget.threshold`.

ECO's ERP and PLM connectors send Items, EBOM lines with reference designators and effectivity, routings and change notices with dispositions, and return costs, prices, lead times and inventory as External inputs under ECO's field-ownership table (R4-18).

### Physical tests and Evidence records

**Decision D-KLN-35:** Physical tests are Acts that run on hardware rigs when their inputs change, and their only product is an Evidence record, signed with a TPM-held device key under measured boot and addressed by the check it serves and the identities of the inputs it tested. An evaluation reads the newest valid record for a check and stores its `ObjectId` in the `CheckOutcome`; releases and approvals pin the ids they cite. A check declares whether evidence stays valid while its inputs are unchanged (a fit check) or repeats per lot or build (a fatigue test). *Why:* physical results are not pure functions, and a check must name the measurement it read so a release can reproduce it (R3-17). *Rejected:* cached derived values; lockfile pins (measurements arrive automatically); tests on every Change (rig time). (revised in round 2)

1. A runner registers as a service principal with a TPM-held key and advertises rigs, instruments, consumables and its safety envelope.
2. It pulls requests over an outbound connection, so factory networks need no inbound ports.
3. A request names its artifacts (programs, print jobs, firmware), its procedure (Ingot, or a Wasm component in a tool world with instrument access granted as a capability, never during evaluation) and its budget in rig minutes.
4. Crucible transfers programs and never issues cycle start, resume, jog, `Start` or `StoreAndStart`; a person starts machine tools, robots, lasers, presses and furnaces at the device (contract 7.6). The runner enforces its envelope locally, and emergency stops are hardware.
5. Only rigs a named safety officer declares `unattended_safe` in a signed site policy (closed fixtures with interlocks) run after an Approval without on-site confirmation. Runners never self-declare it, machine tools, robots and lasers never receive it, and every test from an agent branch needs an Approval of its program digest (R4-01).
6. The runner returns the Evidence record: raw data in the CAS, instruments with calibration records, environment, operator and procedure version. A record from an instrument past calibration is invalid, and checks over it fail with `CalibrationExpired`.

Checks use the measurement uncertainty MFG and FLX define, and Evidence records feed traceability and the physical gates, kept out of calibration (contract 13.1). In phase 1, external metrology for GP1 and GP2 enters as Evidence records signed by the lab's principal.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `api` methods | Eight groups; labels on every response | Denials name the missing permission | KLN-O-API-1 | 1 |
| Events | Event types; ECO's envelope; `sequence` attribute | Retries, then dead letter (ECO) | KLN-O-EVENT-1 | 2 |
| Evidence records | Signed; newest valid record per check; pinned by releases | `CalibrationExpired`; without a record the check stays `Undecided` | KLN-O-HW-1 | 1 (lab records), 2 |
| Physical test Acts | Pull-based requests; transfer only; site safety policy | Envelope violations abort and are recorded | KLN-O-HW-1 | 2 |

## State of the art

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Incremental evaluation | Suspending scheduler with constructive traces (Mokhov, Mitchell and Peyton Jones, JFP 2020); Adapton (PLDI 2014) | Salsa; Buck2's DICE | Adopt, with multi-output memo entries (D-KLN-1, D-KLN-36) | Re-executed set on 500 edits; contract 13.3 rebuild rows |
| Early cutoff | Value equality with lazy content identity | Salsa; Nix content-addressed derivations | Equality interactively, `ObjectId` for sharing (D-KLN-5) | Dependents covered by the 100 ms drag preview |
| Shared build cache | CAS plus action cache (Bazel Remote Execution API v2); signed realisations (Nix RFC 62) | Bazel with Buildbarn or EngFlow | Adopt, with attestation service and two-builder agreement (D-KLN-9) | Hit rate for 20 people on GP3 and GP4; target 90% |
| Eviction | GreedyDual-Size (Cao and Irani, USITS 1997) | LRU in build caches | Adopt (D-KLN-7) | Rebuild under a 256 MiB budget; target within 2× |
| Deterministic testing | Whole-system deterministic simulation (FoundationDB) | FoundationDB | Adopt for Kiln, sync, collector, server | Simulated hours per night (targets in Determinism policy) |
| Content hashing | SHA-256 (FIPS 180-4) against BLAKE3 | BLAKE3 | SHA-256 per chunk (D-KLN-14); deviation for FIPS approval and interoperability | KLN-O-CAS-4 throughput targets |
| Chunking | FastCDC (USENIX ATC 2016); prolly trees (Noms, Dolt) | Rabin-based chunkers; Dolt | Name-free segments; FastCDC for Blobs (D-KLN-15) | Deduplication between successive Changes; target 95% |
| Numeric compression | pcodec; byte shuffling plus zstd; meshoptimizer codecs | zstd on raw arrays | Per-chunk codecs (D-KLN-16) | Ratio and decode speed against zstd level 3 |
| Encrypted deduplication | Server-aided message-locked encryption (DupLESS, USENIX Security 2013) | Convergent encryption in backup tools | Domain-keyed derivation (D-KLN-17) | Cross-domain confirmation test |
| Version control | Git's SHA-256 objects; Jujutsu's operation log and first-class conflicts | Git, Jujutsu | Changes, transaction log, first-class conflicts (D-KLN-19, D-KLN-20) | No lost Change under simulation |
| CAD history and merge | Onshape microversions; GumTree; Spork and Mergiraf triple merge | Onshape; Mergiraf | Microversions plus verdict, geometric and connectivity conditions (D-KLN-21) | KLN-O-MERGE-1 |
| Live collaboration | Movable tree CRDT (Kleppmann et al.); Fugue; Eg-walker | Loro; Automerge 3 | Loro per (package, label set) (D-KLN-22) | KLN-O-COLLAB-2 |
| Set reconciliation | Range-based set reconciliation (Meyer 2022) | rsync-style full listings | Adopt for tier anti-entropy | Bytes exchanged against the size of the difference |
| Authorization | Cedar (OOPSLA 2024) | Open Policy Agent (Rego) | Adopt (D-KLN-29) | p99 decision under 1 ms (target) |
| Tamper-evident logs | RFC 6962 Merkle logs as C2SP tlog-tiles with witnesses | Certificate Transparency; Sigstore Rekor | Adopt (D-KLN-30) | Fork detection under fault injection |
| Long-lived signatures | ML-DSA (FIPS 204); LMS | Classical-only release signing | Dual signatures by phase 2 (D-KLN-42) | Verification under each algorithm alone |
| PLM change control | ECR, ECO and ECN workflows with effectivity | Windchill, Teamcenter, Arena, Fusion Manage | Orders as Proposals; approvals over subjects (D-KLN-28) | Scripted-order cycle time; third-party Part 11 audit in phase 3 |
| Variant management | 150% BOM with variant conditions | Teamcenter configurator [unverified] | `#[configuration]`, abstract interpretation, SAT (D-KLN-27) | KLN-O-PLM-5; solver time on 200 parameters |
| Browser persistence | OPFS sync access handles; SQLite's `opfs-sahpool` VFS | Per-tab engines | One engine per origin (D-KLN-44) | KLN-O-DEPLOY-1 |

Vendor pages for the PLM rows gave only general claims, except Windchill's effectivity types, so those targets come from Crucible's oracles.

## Platform notes

| Platform | Risk | Decision |
| --- | --- | --- |
| Windows | Open pack files cannot be replaced; long paths; case-insensitive names | Packs replaced by rename after close; long-path APIs; paths differing only by case or normalization rejected |
| macOS | Case- and normalization-insensitive file system; App Sandbox | The same path rule; security-scoped bookmarks (PLT) |
| Linux | Weak `fsync` on some configurations | Write-then-rename with `fsync` on file and directory; simulation injects torn writes |
| Browsers | Storage eviction; exclusive OPFS handles; no guaranteed SHA instructions; threads only under cross-origin isolation | Persistent storage and eager pushes; one engine per origin (D-KLN-44); `crypto.subtle` hashing; without isolation headers the engine runs on one worker and says so |
| Browsers | Origin-bound WebCrypto keys | WebAuthn device keys where possible, re-enrolled when storage is cleared |
| iPadOS and Android (Tier 2) | Memory pressure kills; on iPadOS Wasm runs inside WebKit (contract 7.4) | PLT's memory budget; heavy Evaluations run remotely |
| Servers | FoundationDB operations burden; uneven conditional writes on S3-compatible stores | SQLite or PostgreSQL on team servers; ref updates through the metadata store where conditional writes are missing |
| Air-gapped | No federation, time source of record or updates | Local identity provider; signed bundles; server clock audited against a site time source |
| FIPS mode | Validated modules differ by platform | PLT's provider on servers and desktops; FIPS-required signing on desktop or server clients |

## Interfaces with other subsystems

### What this tab provides

| To | Provides | Types |
| --- | --- | --- |
| ANV, FLX, Wasm components | Operation contract, effective fidelity, two-stage keys, Aborts, derivatives, `Checkpoint` retention | `OpImpl`, `OpCx`, `OpKey`, `Differentiable` |
| Every tab | Memoized, progressive evaluation with cost estimates; the CAS | `Kiln::demand`, `ResultEvent`, `ResultStatus`, `CasStore`, `ObjectId` |
| ING | Demand-depth and fuel limits; `Pending` on `Undecided` below the ceiling; block maps | `Abort`, `ResultStatus` |
| UIX, AGT, CI | Changes, merge, diffs, Proposals, live documents, presence, locks, span provenance | `ChangeId`, `MergeDriver`, `Conflict` |
| MEC, MFG, ELX | Items, revisions, late-bound fields, effectivity, BOM views, where-used, orders, MCOs, parts policy | Item and revision records |
| AGT | Labels and write-down at `repo`; signature records for Act approvals; the audit log; `release_data` | `Labels`, signature records |
| ECO, UIX | Event types with sequence numbers; connector mappings; data for UIX's Item place (R4-31) | Event types, Item records |

### What this tab requires

| From | Requirement |
| --- | --- |
| ING | Text-derived `OpSite`s; block-local parsing; dependency recording; `#[configuration]` regions; `ING6401` only at the ceiling |
| ANV | Graded `OpImpl`s with fidelity maps and two-stage keys; `GeometryId`; canonical outputs; interference and history for merge; defeaturing and envelopes |
| FLX | Cost models, safe points, step checkpoints; `Differentiable` operations; Fields by virtual partition; calibration tables as pinned data |
| PLT | Pools; `det_sum`, `det_reduce`, `exact_sum`; `detmath`; the mechanism table; the dispatch rule; memory tables; the crypto provider; label-aware egress |
| AGT | Method catalog; context labels; the approval page; budgets and admission |
| MEC, MFG, ELX, COV | `part(…, item:)`, `bom_item`, revision markers; MBOM rules, programs with simulation evidence, as-built and QIF records, substance rules; net partitions and firmware Items; `Material` composition |
| ECO | Event envelope and signing; ERP and PLM connectors; the supply chain; data packages as External inputs |

## Oracles

Oracles live in `oracles/kln/`, which agents can read but not write; held-out sets stay outside the agent-readable tree. Round 1's `kiln/`, `cas/` and `repo/` oracles keep their substance under these ids.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| KLN-O-FPRINT-1 | Registration and fingerprints | Corpus digests match; a changed digest without a version bump fails CI |
| KLN-O-RETIRE-1 | Retired versions | A golden product pinned to a retired version rebuilds bit-identically from archived Wasm |
| KLN-O-MIN-1 | Minimal re-execution | On 500 scripted edits, comment-only and fuel-only included, the re-executed set equals the reference set |
| KLN-O-EQUIV-1 | Incremental equals from-scratch | After every edit and upgrade, output identities equal a cold build's |
| KLN-O-SITE-1 | Site keys | Equal calls at two sites give distinct `EntityId`s, and their union succeeds |
| KLN-O-ROUNDTRIP-1 | Canonical values | Op outputs from memory and reloaded from the CAS give identical dependents |
| KLN-O-ABORT-1 | Aborts | Faults at random Ops in 10,000 Evaluations; every memo entry and CAS object equals the fault-free value |
| KLN-O-LIMIT-1 | Evaluation limits | `f(n) = f(n + 1)` aborts with `DemandDepthExhausted` on every Tier 1 target, leaving no memo entry; low ceilings refuse at admission |
| KLN-O-SIM-1 | Kiln, sync, collector, server | Seeded fault simulation loses no Change and caches no wrong value; failing seeds replay |
| KLN-O-PROG-1 | Progressive results, drag lane | One generation per frame; `Pending` resolves at the next fidelity; early- and late-edit drags report dependents covered |
| KLN-O-CANCEL-1 | Cancellation | 10,000 Evaluations with random cancellation and restart end equal to clean ones |
| KLN-O-EVICT-1 | Eviction | A 256 MiB budget never changes results; rebuild within 2× of unbounded (target) |
| KLN-O-BUDGET-1 | Budgets | Caps exceeded by at most one safe-point interval; `BudgetExhausted` never cached |
| KLN-O-DERIV-1 | Derivatives | Taylor test of a three-Op chain gives order 2 ± 0.1; adjoints resumed from evicted checkpoints are bit-identical |
| KLN-O-REMOTE-1 | Remote evaluation | Local and remote golden-product Evaluations give identical `ObjectId`s |
| KLN-O-TRUST-1 (held-out) | Shared-cache integrity | Forged, replayed, cross-tenant and single-builder attestations refused at gates; untrusted workers get no signature; planted mismatches on released checks caught |
| KLN-O-LABEL-1 | Labels | Labels reach every derived value; relabelling unchanged bytes re-executes nothing; uncleared participants get zero labelled operations; write-down and out-of-region placement refused |
| KLN-O-LABEL-2 | End-to-end mode | Servers hold no plaintext; keys reach only eligible recipients |
| KLN-O-DET-1 | Bit equality per class | Every operation's corpus on every Tier 1 target, under perturbations, gives one identity per class |
| KLN-O-CAS-1 | Integrity and codecs | Bit flips and truncation fail with `Corrupt` and heal from another tier; unknown codecs never decode |
| KLN-O-CAS-2 | Collection | Concurrent writers, leases and crashes lose zero reachable objects |
| KLN-O-CAS-3 | Encryption domains | No decryption or storage-name correlation across domains |
| KLN-O-CAS-4 | Hashing and deduplication | Throughput targets met; browser and native ids equal; 95% deduplication between successive Changes (target); renames re-chunk no geometry |
| KLN-O-PURGE-1 | Purge and retention locks | Purged bytes unrecoverable from every tier and backup; locked records refuse purge and crypto-shredding |
| KLN-O-REPL-1 | Replication | Fault-injected replication converges with no residency breach |
| KLN-O-GIT-1 | Git round trip | Export, re-import and rebuild keep every `EntityId` and `GeometryId` on every golden product |
| KLN-O-SPAN-1 | Span provenance | Instructions planted in merged comments, identifiers and templates return as `ExternalText`; trust needs per-span endorsement |
| KLN-O-MERGE-1 (held-out) | Merge | Seeded semantic, one-sided check, interference, provenance and net-merge conflicts all found; zero silent wrong merges; 90% of reference-clean merges clean (target) |
| KLN-O-DIFF-1 | Diffs | Identical Changes diff empty; geometric deviation within its bound of a reference |
| KLN-O-LARGE-1 | Large assemblies | The 100,000-Instance benchmark meets its target |
| KLN-O-XREF-1 | References | Rebuilding from `ingot.lock` reproduces every `ObjectId` |
| KLN-O-COLLAB-1 | Reconcile | Text to block tree to text is byte-identical under random edits; unparseable blocks keep kind and position |
| KLN-O-COLLAB-2 | Convergence, presence, locks | 50 peers with partitions converge; p95 keystroke-to-remote under 100 ms on one continent (target); presence never stored; enforced locks never bypassed |
| KLN-O-COLLAB-3 | Offline rejoin | No Change lost; seeded conflicts found; fast-forward only without concurrent changes |
| KLN-O-PLM-1 | Lifecycle guards | A Part with an unreleased child cannot release; every unmet guard named |
| KLN-O-PLM-2 | Numbering | Concurrent allocation yields no duplicates |
| KLN-O-PLM-3 | Interchangeability | Seeded form-fit-function breaks all flagged |
| KLN-O-PLM-4 | Effectivity | Configured BOMs equal references at 1,000 random points; gaps and overlaps found |
| KLN-O-PLM-5 | Variants | Each valid configuration's 100% BOM equals brute force on small products |
| KLN-O-PLM-6 | BOM views | GP3's MBOM reconciles with matching quantities |
| KLN-O-PLM-7 | Where-used | The index equals full recomputation nightly |
| KLN-O-PLM-8 | Manufacturing changes | MCOs touching EBOM definitions rejected; a part change returns exactly its dependent programs to `Prototype` |
| KLN-O-PLM-9 | Definition equivalence | A bit-level engine upgrade marks zero Items modified; a seeded out-of-tolerance change marks exactly its Item |
| KLN-O-PLM-10 | System of record | A release and an external approval round trip through a mock PLM without changing digests |
| KLN-O-PLM-11 | Parts policy | Unapproved parts fail unless a waiver names them |
| KLN-O-CHG-1 | Approval subjects | Stale content cannot be approved; rebase or CI re-run with an unchanged subject keeps approvals |
| KLN-O-SIG-1 | Part 11 controls | Excised and transferred signatures fail; re-authentication required; exports verify offline |
| KLN-O-SIG-2 | Signature agility, FIPS mode | Dual-signed records verify under each algorithm alone and after re-timestamping; FIPS mode refuses non-approved algorithms |
| KLN-O-TRACE-1 | Traceability | The matrix equals the reference on GP1 to GP4 |
| KLN-O-COMPL-1 | Compliance | Seeded restricted substances all found; missing data never compliant |
| KLN-O-VULN-1 | Vulnerability where-used | A seeded vulnerable library traced to every affected serial |
| KLN-O-RELEASE-1 | Data release | Every exit path runs `release_data`; failed checks refuse commit; recipient changes from tainted contexts or within 24 h never take effect |
| KLN-O-SHARE-1 (held-out) | Redaction | Planted strings, features and provenance ids never reach a package |
| KLN-O-SHARE-2 | Supplier packages, watermarks | Suppliers read nothing outside their packages; every recipient file traces to its release |
| KLN-O-SHARE-3 | Parametric quotas | Out-of-range or over-budget queries fail with `ShareQuotaExceeded` and are audited |
| KLN-O-POLICY-1 | Identity and authorization | Fuzzing against a reference model; Cedar analysis on every change; agents never sign, approve or release; listed changes need two people |
| KLN-O-AUDIT-1 | Tamper evidence | Rewritten and forked logs detected by clients and witnesses |
| KLN-O-AUDIT-2 | Pseudonymity | After erasure names are unrecoverable while logs and signatures verify; held records keep names |
| KLN-O-DEPLOY-1 | Offline, browser ownership | Airplane-mode suite of every API method; two-tab edits with the owner closed lose no Change |
| KLN-O-DEPLOY-2 | Team server, on-premises | Install to first Proposal under 15 minutes; installs on reference clusters |
| KLN-O-DEPLOY-3 | Cloud | Zone-loss chaos tests lose no acknowledged write |
| KLN-O-DEPLOY-4 | Air-gapped | Bundle round trip between two isolated sites |
| KLN-O-RESTORE-1 | Restore | The verifier finds every fault in seeded corrupt backups |
| KLN-O-API-1 | `api` behavior | Conformance suite shared with AGT |
| KLN-O-EVENT-1 | Events | Receiver outages cause no loss or reordering per repository |
| KLN-O-HW-1 | Evidence and safety | Spoofed, replayed and expired-calibration records rejected; envelope violations abort in the rig simulator; no start command reaches a device |

## Phasing

| Phase | KLN contribution to the gate |
| --- | --- |
| 0 | Kiln core: memoization with multi-output entries, durability, cancellation, Aborts and limits, priority classes, `Differentiable` registration; local CAS with SHA-256 and canonical CBOR; Kiln's corpus green in the determinism suite; deterministic simulation; Changes and transaction log on the desktop |
| 1 | GP1 and GP2: progressive results, drag lane, eviction and budgets; a single-node team server (SQLite or PostgreSQL) with branches, merge by source, verdicts and provenance, microVM Proposal CI, Cedar, two-person rules and a signed append-only audit log; labels and write-down; span provenance; Git export; the minimal lifecycle and EBOM; the release Act over approval subjects; `release_data` for STEP and 3MF exports; lab Evidence records; browser engine ownership. Deferred per contract 13.2: cloud SaaS and FoundationDB, live documents, encryption domains, witnessed transparency logs, the hardware runner |
| 2 | GP3 and GP4: live documents, presence and locks; attested shared cache; cloud workers and residency; encryption domains; interference conflicts; change orders, MCOs, Part 11 signatures and dual signing; traceability; MBOM and service BOM; where-used; system-of-record connectors and parts policy; events; the hardware runner; partial clone and references; on-premises; restore verifier; privacy controls |
| 3 | GP5: connectivity conflicts; effectivity; variants and the 150% BOM; the interchangeability check; compliance records; vulnerability where-used; supplier packages, derived views, redaction and quotas; end-to-end mode; regulated cloud; air-gapped bundles; third-party Part 11 assessment |
| 4 | GP6: scale targets (100,000-Instance assemblies, cloud cells); evidence as Flux validation data; multi-region replication |
| 5 and later | Certification evidence packages (DO-178C and DO-254 style traceability [unverified scope]); program-scale effectivity; federation between primes and suppliers at scale |

## Open questions

1. **Hashing large values.** If browsers miss 1 s per GiB, should derived values, which need no FIPS approval, use BLAKE3's tree mode?
2. **Sibling order.** Loro's fractional indices can interleave concurrent sibling inserts; does that misorder features often enough to matter?
3. **Designed contact.** Welded members in GP4 touch by design, so a 0 mm merge clearance flags them; per-mate exemptions may be needed.
4. **Revision rules.** Revision letters and markers need confirmation against ASME Y14.35-2025 and customer rules before phase 2.
5. **Item numbers in source.** Keep them in Ingot, so renumbering is a Change, or only in records keyed by lineage?
6. **Part 11 and AS9100 assessment.** Which assessor and package format customers expect.
7. **End-to-end mode and caching.** Should a customer-hosted cache tier inside the boundary restore sharing?
8. **Definition tolerance.** MEC should confirm the default of the smaller of 0.1 µm and 1% of the tightest tolerance.
9. **`SharedWorker` coverage** on every Tier 1 browser [unverified]; the fallback is a lock-holder handoff over `BroadcastChannel`.
10. **Findings declined in part.**
    - R3-03: an unavailable retired version stays a `Failure`, not an Abort, because contract 7.2 rules so and archived Wasm builds make retired versions available everywhere.
    - R2-06: calls do not become CRDT blocks inside `OpSite`; contract 5's text-derived `OpSite` already names calls by operation and occurrence index, stable when stages are appended or wrapped.
    - R3-20: per-build signing keys give way to contract 7.8's attestation service bound to workload identity.

## Contract change requests

- **CCR-KLN-6. Evidence records for inputs without geometry.** Contract 2 addresses an Evidence record by "the `GeometryId`s of the inputs it tested". Proposed: "by the check it serves and the identities of the inputs it tested (`GeometryId`s for geometric inputs, `ObjectId`s otherwise, as in 7.2 item 3)". *Reason:* firmware, Material coupon and electrical tests test inputs that have no `GeometryId`.
- **CCR-KLN-7. Add Item to the glossary.** "Item: the lifecycle identity of a releasable thing (Part, Assembly, Document, Software item, Purchased catalog part, Program) with an item number; its revisions are the only meaning of revision." *Reason:* section 5 uses `ItemDefinition` and approval pages list Items, but the glossary does not define the term.
- **CCR-KLN-8. Complete the merge verdict order.** Add to 7.1: "`Skipped` counts as undefined; a `Pass` whose `conditional_on` gains components ranks below a `Pass` without them." *Reason:* the order covers four of five verdicts and would let a merge make a release-ready check conditional without a conflict.

## Sources

- Salsa, "The red-green algorithm": https://salsa-rs.github.io/salsa/reference/algorithm.html
- Salsa, "Durability": https://salsa-rs.github.io/salsa/reference/durability.html
- Buck2, "Modern DICE": https://buck2.build/docs/insights_and_knowledge/modern_dice/
- Mokhov, Mitchell and Peyton Jones, "Build systems à la carte: theory and practice" (JFP 2020), publication page: https://www.microsoft.com/en-us/research/publication/build-systems-a-la-carte/
- Same authors, "Build systems à la carte" (PDF hosted by Microsoft Research, 2018): https://www.microsoft.com/en-us/research/wp-content/uploads/2018/03/build-systems.pdf
- Adapton project page (PLDI 2014): https://www.cs.umd.edu/~hammer/adapton/
- Bazel Remote APIs: https://github.com/bazelbuild/remote-apis
- Nix RFC 62, content-addressed paths: https://github.com/NixOS/rfcs/blob/master/rfcs/0062-content-addressed-paths.md
- Cao and Irani, "Cost-Aware WWW Proxy Caching Algorithms" (USITS 1997): https://www.usenix.org/conference/usits-97/cost-aware-www-proxy-caching-algorithms
- Rust RFC 3514, float semantics: https://rust-lang.github.io/rfcs/3514-float-semantics.html
- Rust standard library, `f64`: https://doc.rust-lang.org/std/primitive.f64.html
- WGSL specification (W3C): https://www.w3.org/TR/WGSL/ (the fetched page was truncated before section 15.7, so sections "Differences from IEEE-754" and "Reassociation and Fusion" were read in the specification source, wgsl/index.bs, cloned with git from https://github.com/gpuweb/gpuweb)
- WebAssembly relaxed SIMD proposal: https://github.com/WebAssembly/relaxed-simd/blob/main/proposals/relaxed-simd/Overview.md
- Wasmtime `Config` documentation: https://docs.rs/wasmtime/latest/wasmtime/struct.Config.html
- CORE-MATH project: https://core-math.gitlabpages.inria.fr/
- ReproBLAS: https://bebop.cs.berkeley.edu/reproblas/
- Random123: https://www.thesalmons.org/john/random123/
- FoundationDB, "Simulation and testing": https://apple.github.io/foundationdb/testing.html
- Xia et al., "FastCDC" (USENIX ATC 2016): https://www.usenix.org/conference/atc16/technical-sessions/presentation/xia
- Gregoriadis et al., "A Thorough Investigation of Content-Defined Chunking Algorithms for Data Deduplication" (arXiv 2409.06066): https://arxiv.org/abs/2409.06066
- Dolt, "Prolly trees": https://www.dolthub.com/docs/architecture/storage-engine/prolly-tree/
- BLAKE3 repository: https://github.com/BLAKE3-team/BLAKE3
- NIST hash functions: https://csrc.nist.gov/projects/hash-functions
- Git, hash function transition: https://git-scm.com/docs/hash-function-transition
- Git, partial clone: https://git-scm.com/docs/partial-clone
- RFC 8949 (CBOR), section 4.2: https://www.rfc-editor.org/rfc/rfc8949.html#section-4.2
- pcodec: https://github.com/pcodec/pcodec
- meshoptimizer: https://github.com/zeux/meshoptimizer
- Bellare, Keelveedhi and Ristenpart, "DupLESS" (USENIX Security 2013): https://www.usenix.org/conference/usenixsecurity13/technical-sessions/presentation/bellare
- Amazon S3 conditional writes: https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html
- Meyer, "Range-Based Set Reconciliation" (arXiv 2212.13567): https://arxiv.org/abs/2212.13567
- Jujutsu, concurrency: https://docs.jj-vcs.dev/latest/technical/concurrency/
- Jujutsu, first-class conflicts: https://docs.jj-vcs.dev/latest/technical/conflicts/
- Onshape API introduction (documents, workspaces, versions, microversions): https://onshape-public.github.io/docs/api-intro/
- Mergiraf architecture: https://mergiraf.org/architecture.html
- Loro, movable tree: https://loro.dev/docs/tutorial/tree
- Loro 1.0 announcement: https://loro.dev/blog/v1.0
- Automerge 3.0 announcement: https://automerge.org/blog/automerge-3/
- Gentle and Kleppmann, "Eg-walker" (arXiv 2409.14252): https://arxiv.org/abs/2409.14252
- Weidner and Kleppmann, "The Art of the Fugue" (arXiv 2305.00583): https://arxiv.org/abs/2305.00583
- Kleppmann et al., "A highly-available move operation for replicated trees": https://martin.kleppmann.com/papers/move-op.pdf
- Zed, "How CRDTs make multiplayer text editing part of Zed's DNA": https://zed.dev/blog/crdts
- Cedar documentation: https://docs.cedarpolicy.com/
- Cutler et al., "Cedar" (OOPSLA 2024): https://www.amazon.science/publications/cedar-a-new-language-for-expressive-fast-safe-and-analyzable-authorization
- C2SP tlog-tiles: https://github.com/C2SP/C2SP/blob/main/tlog-tiles.md
- SLSA v1.1 build levels: https://slsa.dev/spec/v1.1/levels
- Sigstore overview: https://docs.sigstore.dev/about/overview/
- The Update Framework overview: https://theupdateframework.io/docs/overview/
- Debenedetti et al., "Defeating Prompt Injections by Design" (CaMeL, arXiv 2503.18813): https://arxiv.org/abs/2503.18813
- Willison, "The lethal trifecta for AI agents": https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/
- NIST Cryptographic Module Validation Program: https://csrc.nist.gov/projects/cryptographic-module-validation-program
- aws-lc-rs: https://github.com/aws/aws-lc-rs
- 21 CFR Part 11 (eCFR): https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11
- 21 CFR Part 820 (eCFR): https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-820
- FDA, Quality Management System Regulation: https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-system-qs-regulationmedical-device-good-manufacturing-practices
- 22 CFR 120.54 (eCFR): https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120/subpart-C/section-120.54
- 22 CFR 120.56 (eCFR): https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120/subpart-C/section-120.56
- 15 CFR 734.18 (eCFR): https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-734/section-734.18
- European Commission, RoHS Directive: https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en
- European Commission, Cyber Resilience Act reporting: https://digital-strategy.ec.europa.eu/en/policies/cra-reporting
- CycloneDX specification overview: https://cyclonedx.org/specification/overview/
- PTC Windchill Help Center, "Adding Effectivity": https://support.ptc.com/help/wnc/r11.2.1.0/en/Windchill_Help_Center/ChgMgmtEffectivityAdd.html
- Arena, change management overview: https://www.arenasolutions.com/products/plm/change-management/
- Siemens Teamcenter product page: https://www.siemens.com/en-us/products/teamcenter/
- MDN, `SharedArrayBuffer`: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer
- 22 CFR 120.56 (Cornell LII copy, opened because eCFR refused the fetcher): https://www.law.cornell.edu/cfr/text/22/120.56
- 22 CFR 120.54 (Cornell LII copy): https://www.law.cornell.edu/cfr/text/22/120.54
- 21 CFR 11.10 (Cornell LII copy): https://www.law.cornell.edu/cfr/text/21/11.10
- 21 CFR 11.30 (Cornell LII copy): https://www.law.cornell.edu/cfr/text/21/11.30
- 21 CFR 820.10 (Cornell LII copy): https://www.law.cornell.edu/cfr/text/21/820.10
- NIST, FIPS 204, "Module-Lattice-Based Digital Signature Standard": https://csrc.nist.gov/pubs/fips/204/final
- DFARS 252.204-7012: https://www.acquisition.gov/dfars/252.204-7012-safeguarding-covered-defense-information-and-cyber-incident-reporting.
- GDPR Article 17: https://gdpr-info.eu/art-17-gdpr/
- Works Constitution Act (BetrVG), English translation: https://www.gesetze-im-internet.de/englisch_betrvg/englisch_betrvg.html
- MDN, `FileSystemFileHandle.createSyncAccessHandle()`: https://developer.mozilla.org/en-US/docs/Web/API/FileSystemFileHandle/createSyncAccessHandle
- MDN, Web Locks API: https://developer.mozilla.org/en-US/docs/Web/API/Web_Locks_API
- MDN, `SubtleCrypto.digest()`: https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest
- SQLite, "Persistent storage options" for Wasm: https://sqlite.org/wasm/doc/trunk/persistence.md
- CloudEvents, sequence extension: https://github.com/cloudevents/spec/blob/main/cloudevents/extensions/sequence.md
