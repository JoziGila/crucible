# Kiln, repository and PLM (KLN)

Kiln evaluates Ingot as a memoized graph keyed by content, call site and pinned operation versions, so an edit recomputes only what it affects. Each edit becomes an immutable Change in the CAS, a SHA-256 content-addressed store; a merge is clean only when source, checks, geometry and connectivity agree. Lifecycle, policy, signature and audit records live in the same signed store on a laptop, a team server, the cloud or an air-gapped site.

## Scope and the operation contract

This tab owns evaluation, caching, the determinism policy, the CAS, `repo`, collaboration, product lifecycle management (PLM), security, compliance records and deployment. ING owns compilation and `CallSite`s, ANV and FLX own operations, PLT owns the mechanisms of contract 7.3, AGT owns the `api` catalog and agent safety, and ECO owns the registry, events and connectors.

The crates are `kiln`, `cas` and `repo`. Shared types and handles live in `base` (contract 12), so Kiln reaches Bodies only through `BodyHandle` and calls every operation and Wasm component through `OpImpl`.

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

/// What a native operation may use: no clocks, ambient randomness or I/O.
/// Reductions are PLT's free functions: det_sum(cx, …), det_reduce, exact_sum.
impl OpCx<'_> {
    pub fn checkpoint(&mut self) -> Result<(), Abort>;   // safe point, every 10 ms of CPU
    pub fn rng(&self, stream: u64) -> Philox4x32;       // keyed by rule 2 under Keys
    pub fn work_budget(&self) -> Option<WorkBudget>;
    pub fn fidelity(&self) -> Fidelity;                 // effective fidelity
}

pub struct OpKey(ObjectId);                             // contract 7.2, items 1 to 6
pub enum Fidelity { Preview, Interactive, SignOff }
pub enum DeterminismGrade { Portable, ClassExact, Certified }
```

`OpCx` is native only; a Wasm component receives ING's guest context, generated over its WIT imports.

**Decision D-KLN-2:** The engine build is never part of a key; registration records each released version's source-closure hash (contract 4) and refuses a changed one, with a corpus fingerprint as a second check. *Why:* a build key empties every cache at each release, and a corpus misses shared-crate changes outside it (R9-06). *Rejected:* the build id in the key; the corpus fingerprint alone. (revised in round 3)

`ingot.lock` pins every operation version a design uses. Upgrading is an explicit Proposal with the geometric and metric diff, never a side effect of installing an engine.

**Decision D-KLN-4:** A pinned operation version is never substituted: retired versions run from archived Wasm builds, and one without a Wasm build (a GPU `ClassExact` path) returns `OpVersionRetired`, a catchable `Failure` never memoized or shared. *Why:* old designs must rebuild identically without old engines, and that failure depends on the engine release, not the inputs. *Rejected:* fallback to the newest version; caching `OpVersionRetired`. (revised in round 3)

Per-merge CI reproduces golden hashes only for `Current` and `Deprecated` versions that a golden product or registry package pins. `Retired` versions depend only on the archive and the runtime, so they are re-verified on every toolchain, `detmath` or Wasmtime upgrade and weekly in shards.

### WIT interfaces

KLN owns `crucible:host`, which evaluation-world Wasm components import beside `crucible:ops`, at `@0.1.0` until the freeze in contract 13.1. Its `diagnostics` and `progress` interfaces are write-only and never keyed, and `parallel` offers `map-chunks`, a deterministic map with outputs in input order (PLT).

`crucible:host/cas` reads only objects reachable from the call's input handles, failing otherwise with `unreachable-handle`, and records each read as a dependency whose label joins the node's. Measuring and sampling go through `crucible:ops` (contract 4). MEC owns `crucible:product`, formerly `crucible:model`, whose `read` interface returns this tab's Item and BOM records.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Operation contract | `OpImpl`, `OpCx` in `base`; canonical outputs | Missing grade, cost model or fidelity map fails registration | KLN-O-FPRINT-1 | 0 |
| Closure freeze and fingerprints | Closure hash and corpus digest per version | Changed closure refused; changed digest without a bump fails CI | KLN-O-FPRINT-1 | 0 |
| Pinned versions and upgrades | `ingot.lock` pins; upgrade Proposals | An unknown pin fails resolution | KLN-O-EQUIV-1 | 0 |
| Retired versions | Archived Wasm builds; sharded re-verification | `OpVersionRetired`, never cached | KLN-O-RETIRE-1 | 1 |
| `crucible:host` | Write-only diagnostics; handle-scoped reads; deterministic parallelism | `unreachable-handle` | KLN-O-WIT-1 | 1 |

## Kiln: graph, keys and memoization

### Graph model

Kiln evaluates a demand-driven graph of input cells and derived nodes, as Adapton does. Input cells hold what the outside world sets: source, `ingot.lock`, packages, External inputs, the evidence watermark, configuration points and a request's literal overrides. Nodes are pure functions of what they read, recorded as they read it.

| Node kind | Key | Value |
| --- | --- | --- |
| Front-end stage | Source content hash, language behavior version, imported interface hashes; diagnostics add the compiler release (ING) | The IIR, named by its module code hash, and diagnostics as separate outputs |
| Feature call | Code hashes of modules used, argument identities, `CallSite`, overrides in its code | Parts, Bodies, Fields or plain values, with `HistoryRecord`s |
| Op | `OpKey`; entity-naming Ops in two stages | Canonical outputs with `ErrorBudget`s, or a `Failure` |
| Query resolution | Query, input identities, `CallSite` | Entities with Notes, or a `ResolveError` |
| Check | `CheckId`, predicate code, subject identities, fidelity | `CheckOutcome` |
| Derived view | View kind and inputs | A BOM, diff, traceability matrix or where-used result |

Only the IIR output is shared across compiler releases, which never change IIR semantics. Every node whose value carries `EntityId`s includes its `CallSite` in its key, so equal calls at different sites share only the geometric stage of Ops. Checks read results and never feed them, so adding a `require` changes no other key, and Kiln prefetches the static Op calls the IIR exposes.

**Decision D-KLN-1:** Kiln uses a suspending scheduler with dynamic dependency recording, verifying traces in memory and constructive traces in the shared cache. *Why:* Mokhov, Mitchell and Peyton Jones show that dynamic dependencies need a restarting or suspending scheduler, and suspending with constructive traces gives minimal, shareable rebuilds. *Rejected:* topological scheduling (needs static dependencies); restarting as in Bazel; deep constructive traces as in Nix (no early cutoff).

### Keys

An `OpKey` is the SHA-256 of contract 7.2's six items in deterministic CBOR under the domain tag `crucible/opkey/1`. Kiln applies five rules.

1. Entity-naming Ops key in contract 7.2's two stages (D-ANV-24), Failures and Notes included, so designs sharing a failing geometric stage each get fixes naming their own bindings.
2. The class item is `CpuCanonical` for `Portable` and `Certified` results, even when a GPU assisted. `OpCx::rng` keys streams by operation identity, argument values and input `GeometryId`s or name-free hashes, never by class, fidelity, named `ObjectId`s or `CallSite`s.
3. Pinned data a node reads (calibration tables, regulation packages, supplier offers) enters its key by identity; the lockfile as a whole never does.
4. Limits that can change a value, such as a `#[fuel]` set in source, enter the key; organization ceilings never do.
5. A node's key includes the overrides whose `LiteralSite` lies in its own code (ING), and results under overrides never enter the shared cache.

**Decision D-KLN-3:** Keys include the code hashes of the Ingot modules a node actually used plus the language behavior version, never the whole lockfile. *Why:* a lockfile key invalidates every result when a package is added and blocks sharing std results. *Rejected:* the whole lockfile; the round 1 package closure (misses when an unused module changes). (revised in round 2)

### Memo entries and backdating

A memo entry stores, per output, a value handle, a lazy identity and a `changed_at` generation, plus `verified_at`, the ordered dependencies read, the minimum input durability and a cost record. Durabilities follow Salsa: `High` for std, packages, Materials and catalog data, `Medium` for closed files, `Low` for open documents.

**Decision D-KLN-36:** A node has four kinds of output with their own `changed_at` (value, per-kind accumulators, metadata, label); metadata never backdates, and labels re-join from current inputs even when the value backdates. *Why:* a fuel-only edit would otherwise re-execute every dependent (R3-13), and a relabelled input with unchanged bytes would never relabel its dependents (R3-02). *Rejected:* one combined value; labels inside the value.

Kiln bumps the generation once per batch of input changes and verifies as Salsa does. A memo whose durability class saw no change revalidates in constant time; otherwise Kiln checks recorded dependencies in order. An output equal to its old value keeps its `changed_at`, so a comment edit lowers to equal IR and re-executes no feature.

**Decision D-KLN-5:** Early cutoff on the interactive path compares canonical values directly (−0.0 becomes +0.0, no non-finite values), and Kiln consults the shared cache only when an Op's estimated cost exceeds a key plus one lookup (default 200 ms). *Why:* hashing a 100 MB mesh inside a 100 ms drag spends the budget, and non-canonical values make results depend on eviction (R3-34). *Rejected:* eager hashing; equality that distinguishes signed zeros. (revised in round 2)

A node's label is the join of its inputs' labels (contract 5), recomputed locally on every shared-cache hit. Integrity joins from each input cell's current endorsement state (Labels and export control).

### Failures and Aborts

A `Failure` is a property of the inputs: coplanar Boolean faces, a `ResolveError`, a diverged solve. Kiln memoizes it, `try` catches it, and dependents see `DependencyFailed`. An Abort is a property of the Evaluation: cancellation, resource exhaustion, device loss, budget exhaustion, worker loss or an evaluation limit.

**Decision D-KLN-6:** Failures are cached values; Aborts are invisible to Ingot, propagate to every dependent and leave no memo entry, CAS object or attestation, and worker or device loss retries once elsewhere. *Why:* cached Failures keep editing fast while a feature is broken, and an out-of-memory fallback must never become a cached fact (R3-03). *Rejected:* caching nothing that fails; one failure type with an environmental flag. (revised in round 2)

`base` holds one catalog of limit outcomes, owned here and cited by every tab.

| Outcome | Kind | Meaning |
| --- | --- | --- |
| `WorkLimit { kind, limit }` | `Failure` | An operation's declared search or work limit |
| `FuelExhausted { used, limit }` | `Failure` | The fuel a key declares |
| `StackExhausted { limit }` | `Failure` | The declared stack depth |
| `MemoryLimit { limit }` | `Failure` | The declared memory maximum; host failure below it is `ResourceExhausted` |
| `BudgetExhausted` | Abort | A work budget or the Evaluation's fuel governor |
| `DemandDepthExhausted` | Abort | Nested demands past 10,000 (default) |
| `FuelCeilingExceeded` | Abort | An organization ceiling below a source limit, at admission |
| `ResourceExhausted` | Abort | Host memory, disk or device capacity |

The demand-depth limit stops `f(n) = f(n + 1)`, and the fuel governor sums fuel across an Evaluation (contract 7.1). A node demanding a node on its own active stack fails with `Cycle` and the path of spans.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Memoized evaluation with backdating | `Kiln::demand(EvalRequest) -> ResultStream` | Typed `Failure`s memoized | KLN-O-MIN-1, KLN-O-EQUIV-1 | 0 |
| Durabilities | `High`, `Medium`, `Low` inputs | — | KLN-O-MIN-1 | 0 |
| Site-keyed and two-stage nodes | `CallSite` in keys; geometric stage for values, Failures, Notes | `Internal::EntityIdCollision` unreachable | KLN-O-SITE-1 | 0 |
| Literal overrides | In keys of nodes holding the site; never shared | — | KLN-O-PROG-1 | 1 |
| Multi-output memo entries | Value, accumulator, metadata, label | — | KLN-O-MIN-1 | 0 |
| Canonical round trip | decode(encode(v)) = v | Non-canonical outputs fail registration | KLN-O-ROUNDTRIP-1 | 0 |
| Label propagation | Join per node; hits return values only | `label/write_down` at `api` | KLN-O-LABEL-1 | 1 |
| Failures and Aborts | `Failure` cached; Abort uncached | Abort reported with its cause | KLN-O-ABORT-1 | 0 |
| Limit outcomes | One catalog; demand depth; fuel governor; ceilings | The catalog's outcomes | KLN-O-LIMIT-1 | 0 |

## Kiln: scheduling, budgets and results

### Scheduling and cancellation

Scheduling never changes a result: nodes share no mutable state, concurrent demands share one execution, and collections such as diagnostics merge in canonical order. Kiln chooses PLT's `PoolLane` from the request's `PriorityClass` (AGT's).

| Class | Demand source | Lane | Preempted by |
| --- | --- | --- | --- |
| `Interactive`, drag | A drag, edit stream or per-pointer tool | `Interactive` | Nothing |
| `Interactive` | A person waiting: viewport, selection, own rebuild | `Foreground` | Drags, at node boundaries |
| `Agent` | Agent sessions | `Background` | Both above, at node boundaries |
| `Ci` | Proposal CI, merge queue, releases | `Background` | Both above |
| `Batch` | Explorations, benchmarks, prefetch, background `SignOff` | `Background` | All; resumes from cached nodes |

An awaited background node is promoted. The drag lane serves AGT's `evaluate.subscribe` and `edit.stream` with one request in flight and one pending. Within 100 ms it recomputes the dragged feature plus the dependents that fit an 80 ms estimate, and later dependents show `Proxy` where the change is affine on them, else `Stale` (contract 13.3).

A node runs only while demanded, and a new generation cancels in-flight nodes whose reads changed. Native operations poll `OpCx::checkpoint` every 10 ms of CPU time, Wasm stops at fuel checks, and GPU dispatches follow PLT's rule. Without shared memory, Kiln runs every Op estimated above 100 ms in a disposable worker and cancels it by terminating the worker (contract 7.4).

### Memory and eviction

Values are immutable, reference-counted buffers; large ones are memory-mapped from the local CAS. An evicted value keeps its memo metadata and is reloaded or recomputed. Values on screen, in an open review or feeding running nodes are pinned, within PLT's memory budgets.

**Decision D-KLN-7:** Kiln evicts by GreedyDual-Size: each access sets `H = L + cost / size`, cost being the cheaper of recomputing and reloading, and eviction takes the lowest `H` and raises the inflation value `L` to it. *Why:* it weighs recency, cost and size without tuning, and CAD values span nine orders of magnitude in both. *Rejected:* plain LRU (evicts an hour-long solve to keep cheap sketches).

Kiln writes its memo table (edges and identities, not values) to the local CAS every 60 s and on exit, so a restart revalidates instead of recomputing.

### Progressive results

| Fidelity | Geometry (ANV) | Physics (FLX) | Shared cache |
| --- | --- | --- | --- |
| `Preview` | Surrogates, looser tolerances | Reduced or surrogate solves, `Indicator` bounds | Never written |
| `Interactive` | Filtered decisions, equal to `SignOff`'s wherever it decides; uncertified seeding and tracing | Calibrated `Estimated` bounds | Written; never used by `SignOff` checks or releases |
| `SignOff` | Certified decisions, seeding and tracing | `Guaranteed` where proven, else calibrated `Estimated` | Used after two-builder agreement |

A subscription names targets, a fidelity ceiling, overrides and a priority, and Kiln streams `ResultEvent`s with generation, fidelity, `ResultStatus`, value or `Failure`, budget and label. A published frame holds one generation; older results appear only as `Stale`.

An outcome below the check's declared fidelity (default `SignOff`) is provisional and never counts for CI, Proposals or releases. Control flow on `Undecided` yields the cached value `Undecided { needed, fidelity }` whatever the ceiling, and dependents receive `DependencyUndecided` (contract 5). The ceiling changes only reporting: a consumer shows `Pending` while a higher fidelity is demanded, and at the ceiling the report raises `ING6401`.

**Decision D-KLN-8:** Progressive refinement is a set of independent nodes keyed by fidelity, not a stateful process. *Why:* each tier is then cacheable, cancellable and shareable, and a lower-fidelity result can never pass for a `SignOff` one. *Rejected:* in-place refinement of one value (invisible to the key).

A release demands every node at `SignOff`, geometry included.

### Cost and budgets

Every node records CPU and GPU time, memory, bytes moved and remote price, attributed to principal, repository, branch and Proposal. Kiln returns a priced upper bound from per-operation cost models, counting confirming refinements, canonical recomputes and heavy-worker pool start-up. `api` reserves it against AGT's `Budget`, and an estimate above what remains returns `budget/exceeded` with cheaper options.

An Op estimated above 10 core-seconds gets a work budget from the reservation and reaches a safe point at least every 10 core-seconds. Exhausting it is the Abort `BudgetExhausted`, reported with the last checkpoint, and the budget never enters a key.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Priority classes | `PriorityClass` per request; promotion | — | KLN-O-SIM-1 | 0 |
| Drag lane | PLT's `Interactive` lane; dependents fitted to 80 ms | Later dependents `Proxy` or `Stale` | KLN-O-PROG-1 | 1 |
| Cancellation | Safe points; fuel checks; disposable workers without shared memory | No memo entry or CAS write | KLN-O-CANCEL-1 | 0 |
| Eviction | GreedyDual-Size | Reload or recompute | KLN-O-EVICT-1 | 1 |
| Progressive results | `ResultEvent`; one generation per frame; ceiling-free `Undecided` | `Stale`; `Pending` while higher fidelity runs | KLN-O-PROG-1 | 1 |
| Budgets | Priced bound reserved; safe points | `budget/exceeded`; `BudgetExhausted` | KLN-O-BUDGET-1 | 1 |

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

Forward mode composes tangents along the recorded graph. Reverse mode walks a scalar goal's dependencies in reverse topological order, calls each `adjoint` once and sums cotangents in canonical order; an Op without `Differentiable` fails with `NotDifferentiable { op }`. Derivative nodes are keyed by the primal key plus the goal's, so an objective-only change reuses every primal result.

Step checkpoints of transient solves are CAS objects keyed by (`OpKey`, step) in the `Checkpoint` retention class, which eviction drops first. A resumed solve or adjoint is bit-identical whether its checkpoints were kept, reloaded or recomputed.

**Decision D-KLN-37:** Derivatives are a Kiln traversal over `Differentiable` operations, with step checkpoints in their own retention class. *Why:* adjoints that cross features need one recorded graph, and cheaply recomputed checkpoints must yield to ordinary values. *Rejected:* a tape per engine (cannot chain through features); checkpoints as ordinary values.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `Differentiable` operations | `tangent`, `adjoint` in `base` | `NotDifferentiable { op }` | KLN-O-DERIV-1 | 0 |
| Reverse traversal | From a scalar goal; canonical sums | Aborts propagate | KLN-O-DERIV-1 | 1 |
| Step checkpoints | `Checkpoint` class by (`OpKey`, step) | Evicted first; recomputed | KLN-O-DERIV-1 | 1 |
## Shared cache and remote evaluation

Kiln runs one engine everywhere. Workers advertise classes, operation versions, GPU back ends, region, operator attributes and price; Kiln offloads a node when transfer and remote time beat local time, and outputs stay remote until needed.

| Role (contract 7.8) | Runs | Holds | Writes |
| --- | --- | --- | --- |
| Untrusted-evaluation worker | Proposal CI, External Ops, tests of third-party packages, each in a single-use microVM | A receipt key only | A per-Proposal namespace; execution receipts |
| Trusted builder | Merged Changes of protected branches; third-party code only in microVMs | Workload identity | Results for attestation |
| Attestation service | — | Signing keys | Attestations (`OpKey`, `ObjectId`) over host-computed ids |
| Operator registry builders | First-party packages only | Operator keys | The global public domain, 2-of-n |

Gates accept a cached result only under two-builder agreement (contract 7.8), which guards against faults, not a deterministic exploit. A node whose closure holds third-party code is therefore attested only into its tenant's domain, by builders serving that tenant alone.

An External Op result meets a gate when two single-use runs on different hosts agree in signed execution receipts; otherwise it stays `Unverified` and needs a policy allowance. Hosts of External Ops, translators, spawned tools and stdio MCP servers run with egress denied except named grants (contract 7.8, enforced by PLT).

Spot re-execution follows contract 7.8; a mismatch quarantines the attestation and opens a determinism incident.

Objects and attestations live in the encryption domain of their confidentiality label. On servers each worker process serves one (tenant, confidentiality label), controlled labels get dedicated VMs, and Wasm pooling slots are never reused across them. Placement calls `base`'s `PlacementPolicy`, implemented by `repo::policy`, and refuses a region or operator outside the label's terms with `ResidencyDenied`.

**Decision D-KLN-9:** Only trusted builders evaluating merged protected Changes produce attestations, signed by a separate service; untrusted and third-party code runs in single-use microVMs, third-party closures are attested per tenant, and gates require two-builder agreement. *Why:* runners executing agent Proposals must never sign (R5-03), and one deterministic escape compromises every builder running the package (R11-03). *Rejected:* trusting machines instead of their inputs; OS-process sandboxes as an attestation boundary. (revised in round 3)

In phase 1 the single-node team server is the only trusted builder, so gates recompute. Its signing service serves only the trusted-builder process, it offers no External Ops, and each release records "single host" (Deployment). Kiln's remote protocol is its own, since Bazel's Remote Execution API models command lines over materialized trees, though a Remote Execution API v2 server's content-addressable storage can serve as a storage tier.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Remote evaluation | Worker advertisement; cost-based placement | Worker loss aborts, retried once | KLN-O-REMOTE-1 | 1 (team server), 2 (cloud) |
| Worker pools and attestation | Contract 7.8 roles; microVMs; per-tenant third-party attestation | Untrusted entries ignored | KLN-O-TRUST-1 | 2 |
| Two-builder agreement | Same `ObjectId` from two trusted hosts | Recompute | KLN-O-TRUST-1 | 2 |
| External Op receipts | Two agreeing single-use runs | `Unverified` | KLN-O-TRUST-1 | 2 |
| Fan-out-weighted spot checks | 100% for released checks | Quarantine; determinism incident | KLN-O-TRUST-1 | 2 |
| Label-aware placement | `PlacementPolicy`; one process per (tenant, label) | `ResidencyDenied` | KLN-O-LABEL-1 | 2 |

## Determinism policy

Contract 7.3 defines grades and classes, and PLT owns the mechanisms; this section owns which grade each result needs and where each class is accepted.

| Result | Grade required | Accepted by release gates |
| --- | --- | --- |
| Geometry and oracle reference results | `Portable` or `Certified`, keyed `CpuCanonical` | Yes |
| Flux `SignOff` results | `Portable`, or a pinned non-canonical Field with canonical residual and bound | Yes |
| `Interactive` results, `CpuIsa` variants with FMA | Any, keyed by class | No; `SignOff` recomputes canonically |
| External Op results | The host's class or `Unverified` | When two runs agree, pinned by `ObjectId` |

**Decision D-KLN-10:** `Portable` means bit-identical across `CpuCanonical { epoch }`, every Tier 1 CPU target and browser at any thread count and ISA level, and is the only grade for geometry and oracle reference results. *Why:* a cache shared by every OS, browser and cloud worker needs the same bits from each. *Rejected:* one class per OS and architecture (fragments the cache about eightfold). (revised in round 2)

**Decision D-KLN-11:** `Portable` operations compute elementary functions with `detmath`, as contract 7.3 and D-PLT-17 decide. *Why:* one owner per mechanism (R9-40). *Rejected:* a second rationale here. (revised in round 3)

**Decision D-KLN-12:** GPU floating-point results are `ClassExact` or feed a `Certified` computation, as contract 7.3 and D-PLT-16 decide. *Why:* one owner per mechanism. *Rejected:* a second rationale here. (revised in round 3)

**Decision D-KLN-13:** `Portable` reductions follow `det_sum`'s canonical tree, or `exact_sum` where partitioning varies, as contract 7.3 and D-PLT-15 decide. *Why:* one owner per mechanism. *Rejected:* a second rationale here. (revised in round 3)

A request that pins no class gets the class of a cached result, else the local one; CI pins one class per repository. A release records the class of every result it cites.

The determinism suite (contract 7.3) also perturbs threads, allocator, hash seeds, memory budget and cancellation, and a divergence quarantines affected attestations. Kiln, sync, the collector and the server also run under seeded deterministic simulation, as FoundationDB does: 1,000 simulated hours per night in phase 0 and 10,000 by phase 2 (targets).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Determinism grades | Grade per operation version | Undeclared grade fails registration | KLN-O-DET-1 | 0 |
| Release acceptance | The acceptance table | Non-canonical inputs recomputed | KLN-O-DET-1 | 1 |
| Determinism suite | Every merge; nightly elsewhere | Severity-1 incident; beta blocked | KLN-O-DET-1 | 0 |
| Deterministic simulation | Seeded order, time, network, faults | Failing seeds replay | KLN-O-SIM-1 | 0 |

## The CAS

### Object model

| Kind | Content | Typical size |
| --- | --- | --- |
| `Blob` | Opaque bytes: an imported STEP file, an image, a Wasm component | Bytes to gigabytes |
| `Record` | Deterministic CBOR: a Change, a tree, a `Material`, a signature, an attestation | Under 64 KiB |
| `Segmented` | A large typed array (mesh, Field values, sparse matrix) in keyed segments | Megabytes to terabytes |
| `Index` | Child `ObjectId`s with lengths and keys | About 16 KiB |

Records use RFC 8949's core deterministic encoding, one canonical quiet NaN and NFC text; large numeric arrays are little-endian typed arrays. An `ObjectId` is `SHA-256(domain tag ‖ type tag ‖ canonical bytes)` behind a one-byte algorithm code, computed before compression and encryption, so tiers may recompress or re-encrypt freely. A large value's identity is its root `Index` node's, and chunking parameters belong to the type tag.

Producers emit canonical forms, since equal values need not have equal encodings, and Bodies also carry the name-free `GeometryId`.

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

**Decision D-KLN-14:** The CAS identity hash is SHA-256, with a one-byte algorithm code reserved for migration. *Why:* SHA-256 is approved under FIPS 180-4 and is the digest of RFC 6962 logs, C2SP tiles and Git's SHA-256 format, and Git's transition shows the cost of a hash without an agility field. *Rejected:* BLAKE3 (not NIST-approved; chunk-parallel hashing recovers most of its speed); SHA-3 (slower in software).

**Decision D-KLN-46:** Derived values use the same hash as every other object, and a browser that misses the hashing target gets a relaxed target, never a second algorithm. *Why:* a second hash would give one value two `ObjectId`s across deduplication and two-builder agreement (R9-51). *Rejected:* BLAKE3's tree mode for derived values.

BLAKE3's authors call `b3sum` "an order of magnitude faster" than `sha256sum`, so Crucible hashes chunks in parallel, off the interactive path, and verifies large values chunk by chunk. Browsers hash chunks of at most 1 MiB with `crypto.subtle.digest` across engine workers, since it takes no streaming input, and use a Wasm SHA-256 for small synchronous objects. Targets: 1 GiB in under 150 ms natively on the reference laptop and under 1 s in a browser with 8 workers.

**Decision D-KLN-15:** Chunking is structure-aware first: segmented values split into typed segments keyed by geometric content or space, never names, grouped by a content-defined rule over their keys as in a prolly tree, and opaque Blobs use FastCDC. *Why:* byte-level chunking shifts every boundary when vertices renumber, and FastCDC is about 10× faster than the best open-source Rabin chunker at nearly equal deduplication. *Rejected:* fixed-size chunks; `EntityId` segment keys (a rename would re-chunk geometry). (revised in round 2)

| Value | Segment key and content |
| --- | --- |
| Body | Anvil's content-defined encoding leaves of at most 1,024 rows (D-ANV-9) |
| Mesh and `DisplayPackage` clusters | Morton code of a spatial cell; up to 4,096 triangles |
| Field values | Flux virtual partition, in 1 MiB chunks |
| Sparse matrix | Row block |
| Opaque Blob | FastCDC: minimum 16 KiB, average 64 KiB, maximum 256 KiB |

A chunk ends after a segment whose key hash falls below a threshold (about 64 KiB chunks), and `Index` nodes hold up to 512 children. Gregoriadis and colleagues found no impartial comparison of chunking algorithms before their 2024 study, so phase 1 benchmarks their alternatives on Crucible data.

**Decision D-KLN-16:** Each stored chunk names its codec: Fields use byte shuffling plus zstd, with pcodec measured as an alternative, other chunks zstd (level 3 hot, 19 archived), and display meshes on the wire meshoptimizer's lossless vertex codec. *Why:* named codecs allow better ones without a format break, and pcodec's authors chart better ratios than zstd on numeric data. *Rejected:* one codec for everything; lossy quantization in storage (changes identity).

A reader that does not know a chunk's codec fails with `CasError::UnknownCodec`; every codec in use decodes in every Tier 1 build.

### Encryption at rest

Desktops add CAS encryption for labelled repositories, keyed in the OS keystore or a non-extractable WebCrypto key. Servers use envelope encryption per domain under KMS or HSM keys, customer-managed if wanted.

An encryption domain is one tenant and one canonical confidentiality label; integrity never splits domains. An object's key is `HKDF-SHA-256(domain key, ObjectId)`, chunks are sealed with AES-256-GCM under random 96-bit nonces, and the storage name is `HMAC-SHA-256(domain key, ObjectId)`, so plaintext `ObjectId`s never leave the domain's principals.

**Decision D-KLN-17:** Deduplication happens only within an encryption domain, using keys derived from a domain secret. *Why:* convergent encryption lets anyone confirm a guessed file, DupLESS shows the remedy is a secret held by the authorized side, and GCM (SP 800-38D) and extract-then-expand derivation (SP 800-56C; HKDF, RFC 5869) are NIST-specified. *Rejected:* deduplication across tenants (reveals which designs exist).

Deleting a domain key purges a contaminated label, subject to retention locks.

### Collection, tiers and replication

Source history is never collected; derived values are cache. Roots are refs, the transaction log, releases with their cited results, open Proposals, legal holds and in-flight uploads. Writers upload objects before updating a ref, the server accepts a ref only over a present closure, and deduplicating writers take a 24-hour lease; the collector sweeps unmarked, unleased objects older than 48 h.

**Decision D-KLN-18:** Removing source history requires a purge, a record signed by two people listing the removed `ObjectId`s and the authority, which verification treats as known-missing; locked records cannot be purged before retention ends without a deviation two people sign. *Why:* spills and court orders require deletion, while Part 11 requires retrieval throughout retention (R5-21). *Rejected:* history rewriting (breaks signatures); single-administrator purges. (revised in round 2)

| Tier | Store | Contents | Eviction |
| --- | --- | --- | --- |
| 0 | Process memory | Kiln values | GreedyDual-Size |
| 1 | Local disk: 64 MiB append-only packs; OPFS in browsers | Working set, unpushed Changes | Budget (default 20% of free disk); unpushed Changes never |
| 2 | Team server or cloud region: object storage plus a metadata store | All source, shared results, attestations | Collector plus budget |
| 3 | Archive object storage | Releases and their cited results | Retention policy only |

Refs and the transaction log live in SQLite on desktops and single-node team servers, PostgreSQL on larger team servers and FoundationDB in the cloud. Ref updates are compare-and-swap transactions, or conditional writes on bare object storage, which S3 documents as failing with 412 when a concurrent writer wins. Cloud regions keep three synchronous metadata copies, replicate objects within the residency zone, and reconcile tiers by range-based set reconciliation, which recursively splits ranges and compares fingerprints.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Put and get by `ObjectId` | `CasStore` | `CasError::Corrupt`; heal and quarantine | KLN-O-CAS-1 | 0 |
| Hashing | SHA-256 per chunk; `crypto.subtle` in browsers | — | KLN-O-CAS-4 | 0 |
| Structure-aware chunking | Name-free segment keys; FastCDC for Blobs | Unkeyed values fall back to FastCDC | KLN-O-CAS-4 | 1 |
| Per-chunk codecs | Codec named per chunk | `CasError::UnknownCodec` | KLN-O-CAS-1 | 1 |
| Encryption domains | Tenant and confidentiality label; KMS keys | `CasError::KeyUnavailable` | KLN-O-CAS-3 | 2 |
| Collection | Mark, lease, sweep | Stops on any inconsistency | KLN-O-CAS-2 | 1 |
| Purge and retention locks | Two-person purge; locks with a basis | Purge refused under a lock | KLN-O-PURGE-1 | 2 |
| Tier replication | Residency-aware reconciliation | Residency violations blocked | KLN-O-REPL-1 | 2 |
## `repo`

### Changes and refs

| Object | Content |
| --- | --- |
| `Change` | Parents, tree, author, `on_behalf_of`, contributors, hybrid logical clock time, description, conflicts; `ChangeId` hashes the unsigned Change |
| `Tree` | Prolly-tree map from normalized path to file, `ingot.lock` included |
| `SourceFile` | Canonical Ingot text, a block map (block id to span) and span integrity provenance; segmented by top-level block above 64 KiB |
| `Tag` | Name and target Change; a release tag adds the release record |
| `RefTransaction` | Predecessors, the resulting view of all refs, principal, `api` call |
| Signature records | Detached records naming the `ObjectId` they sign (Electronic signatures) |
| `Comment`, `ReviewVerdict` | Review records on a Proposal or order: author, target Change and UIX's `CommentAnchor`, text as an integrity-tracked span; a verdict adds `Accept` or `RequestChanges` |
| Lifecycle records | Items, revisions, change orders, Evidence records, compliance records |

Evaluation never reads time or authorship, and adding a signature or timestamp never changes an identity (contract 7.8).

**Decision D-KLN-19:** Edits become immutable Changes, as in Onshape's microversions: one per completed GUI action, per `edit.apply`, after 2 s without typing, at least every 60 s of editing, and whenever something references the current state. *Why:* anyone can inspect, diff or branch from any state without a manual step. *Rejected:* explicit commits only (loses states reviewers need); one Change per keystroke.

Refs are branch heads (`branches/<name>`), immutable tags (`tags/<name>`), Proposal heads (`proposals/<id>`) and agent branches (`agents/<agent>/<branch>`). Personal views and layouts live in a per-user store outside Changes (UIX).

**Decision D-KLN-20:** Ref updates are recorded in a transaction log, as in Jujutsu: each `RefTransaction` names its predecessors and the full resulting view of refs. Concurrent transactions merge three ways, and a ref moved two ways becomes a conflicted ref. *Why:* full views give lock-free sync, make undoing any repository action one transaction, and double as the audit trail. *Rejected:* Git-style reflogs (per clone); server locks (break offline work).

### Storage, Git export and span provenance

Git is an export, not the storage format: `crucible export git` writes Ingot text and `ingot.lock`, and since `CallSite`s derive from text alone, re-importing leaves every `EntityId` unchanged.

Each source span records the integrity of the context that wrote it: trusted when a person typed it or the compiler produced it, otherwise the writer's flags. Merges, rebases and moves preserve it, and every value evaluated from a free-text span (a part name, a BOM description, embossed text) carries it into its node's label (contract 7.6).

A human merge clears the flags on typed values, never on free text, which `read` methods return as `ExternalText` handles. Free text becomes trusted only through `propose.endorse_text`, a signature record naming the span's bytes, which needs the `maintainer` or `approver` role and refuses the span's author and the authoring delegation chain.

Only the server that witnessed a write asserts its integrity. Spans arriving through Git import, archive import or federation are `data_untrusted`, their free text also `instruction_tainted`, unless a device key of this organization signed the Change. A bundle from another of its sites keeps integrity only when the receiving domain trusts the signing site.

### Proposals and merge

CI evaluates a Proposal's head and its would-be merge on untrusted-evaluation workers, and protected branches merge through a merge queue. A merge is clean only when every condition holds; each failure is a typed conflict.

1. **Source.** Files merge three ways over their block trees, matched by block id, or by GumTree for files edited outside Crucible. Child order merges by Parent-Child-Successor triples as in Mergiraf, sets merge as sets, and text merges on tokens; sketch seeds are ordinary literals (MEC), so concurrent seeds of one sketch conflict. `ingot.lock` merges per entry, and different pins of one package conflict.
2. **Compilation and resolution.** A compile or `Query` failure on neither parent is `Conflict::Semantic`.
3. **Verdicts.** No check's verdict on the merge, matched by `CheckId`, is worse than on each parent that defines it, in contract 7.1's order. Protected branches compare at the declared fidelity and others at `Interactive`; a worse verdict is `Conflict::Check`.
4. **Interference.** A `Hard` interference (positive volume, in MEC's classes) between Instances that neither parent has is `Conflict::Interference`.
5. **Geometric provenance.** A side's touched set is the base entities with a `Split`, `Merged`, `Deleted`, or `Boundary` or `Attributes` `Modified` record from an Op whose key differs from the base's; geometry-only parameter edits are excluded. Intersecting touched sets, or a created entity that meets an entity in the other side's touched set (certified distance zero, or below an optional merge clearance), give `Conflict::Geometric`.
6. **Connectivity.** A merged net that unions nets distinct in the base and in each side, for circuit nets, harness connections or `std::systems` interfaces, is `Conflict::NetMerge`; renamed nets match by provenance.

Contact that a mate, a `Weld` record, a fastened joint, `IntendedThread` or `IntendedFit` explains never conflicts under conditions 4 and 5. Symmetric-difference regions show in review but never block.

**Decision D-KLN-21:** A merge is clean only when the merged design compiles and resolves, keeps every check's verdict, adds no unexplained interference, and has no touched-set or connectivity conflict. *Why:* a compiling text merge can still break a part or short two nets (R3-15), and touched sets let a width change beside a new hole merge clean while two fillets on one edge conflict (R8-13). *Rejected:* line-based merge; overlap of changed regions; flagging designed contact. (revised in round 3)

Conflicts are first-class, as in Jujutsu: a conflicted block holds base and side alternatives, simplifies when rebased, and evaluates as a `Failure` with three fixes. Several merge bases merge into one virtual base, as Git's `ort` strategy merges common ancestors into a reference tree.

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
| Metric | Every check's value and margin before and after | `CheckId` |
| BOM and lifecycle | Items added, removed or re-revised; quantity, effectivity, state and compliance changes | Item number and record identity |

Diffs are Kiln nodes, so source and feature diffs appear in milliseconds and geometry refines afterwards.

Partial clones name a filter (`source-only`, `paths(<pattern>)`, `depth(<n>)`, `display(<lod>)`) and fetch missing objects in batches, as Git's promisor remotes do, and envelope Bodies check clearance without B-reps. They serve contract 13.3's phase 2 assembly rows; the phase 4 target is a cold partial clone of 100,000 Instances of 10,000 Parts to an interactive view in 15 s over 100 Mbit/s.

References to packages, catalog parts and other repositories are pinned in `ingot.lock` as `{ source, selector, resolved }`, where a selector is a release tag, a `ChangeId`, a followed branch or a derived view. An unreadable reference resolves to its derived view for holders of `read_derived`, else fails with `AccessDenied`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Changes and transaction log | `Repo::record`, `update_ref`, `edit.undo` | Conflicted refs | KLN-O-SIM-1 | 0 |
| Git export | Ingot text and `ingot.lock` | — | KLN-O-GIT-1 | 1 |
| Span integrity provenance | Per-span integrity into labels; endorsement; witnessed integrity | Untrusted text as `ExternalText` | KLN-O-SPAN-1 | 1 |
| Source, compilation and verdict conditions | `MergeDriver::merge` | `Text`, `Lockfile`, `Semantic`, `Check` conflicts | KLN-O-MERGE-1 | 1 |
| Geometric provenance conflicts | Touched sets; contact exemptions | `Conflict::Geometric` | KLN-O-MERGE-1 | 1 |
| Interference conflicts | MEC's interference classes | `Conflict::Interference` | KLN-O-MERGE-1 | 2 |
| Connectivity conflicts | Net partitions | `Conflict::NetMerge` | KLN-O-MERGE-1 | 3 |
| Semantic and geometric diff | `compare.diff` | Partial diff flagged | KLN-O-DIFF-1 | 1 |
| Partial clone | Clone filters; batched fetch | `RepoError::NotLocal` | KLN-O-LARGE-1 | 2 |
| Cross-repository references | Pinned in `ingot.lock` | `AccessDenied`, `RefMissing` | KLN-O-XREF-1 | 2 |

## Collaboration

### Live documents

Each participant (editor, language server, agent) edits a branch's live document locally and syncs through a relay. The document is a movable tree of blocks whose heads, children and tails own every byte; literals are last-writer-wins registers, so concurrent `65mm` and `70mm` never give `6570mm`. Other text is a sequence CRDT, and moves use Kleppmann and colleagues' move operation, proved convergent in Isabelle/HOL.

Block ids are Loro tree node ids, mapped onto text-derived identities and never part of a `CallSite`. Each block parses under its own production (ING), so a block that stops parsing keeps its kind and position, and Kiln serves its last good result as `Stale`.

**Decision D-KLN-22:** The live-document CRDT is Loro, a movable tree of blocks with Fugue text leaves, replicated per (package, module confidentiality label). A higher-labelled module is its own document for cleared participants, and the relay refuses moves into a lower-labelled one. *Why:* Loro has both structures with a stable format since 1.0 and fast import (1.15 ms for a 1,659,541-operation document), and one document cannot be filtered per recipient (R3-02). *Rejected:* a text-only CRDT with reparsing (moved features duplicate); Automerge 3, whose announcement adds no tree move; labels per block. (revised in round 3)

Every edit passes one reconcile step on the editing client. An edit inside one block applies to its text, and a structural edit reparses the range and matches blocks by GumTree. A delete concurrent with an edit inside the block wins, with a restore offered to both authors.

Concurrent sibling inserts may interleave, but order matters only for definition before use and for an unnamed statement's ordinal in its `CallSite`. After any CRDT merge the reconcile step checks both, a change to either is `Conflict::Text` on that block, and otherwise the merged order stands.

### Attribution, presence and locks

The relay checks every update against the sender's permissions and enforced locks and records Changes on the triggers of D-KLN-19. Device keys sign update batches, a Change lists its contributors, undo is per principal, and agents join only branches their scope allows. Presence (cursor, selection, camera, drag ghost, an agent's step) lives 30 s and is never stored.

| Lock | Scope | Enforcement | Typical use |
| --- | --- | --- | --- |
| Advisory | Block, file or Item | Presence shows the holder; agents' edits fail with `LockHeld` | Busy documents |
| Enforced | Path, block or Item | Relay and merge reject others' changes; expiry default 8 h; administrators break it with an audited record | Unmergeable Blobs; regulated Items |

**Decision D-KLN-23:** Locks are optional and scoped; enforced locks exist for content that cannot merge and for regulated Items. *Why:* structural merge makes pessimistic locking unnecessary for Ingot, but imported binaries cannot merge and some quality systems require exclusive checkout. *Rejected:* mandatory check-out as PLM vaults use (serializes teams).

### Offline work and sync

**Decision D-KLN-24:** On reconnection the relay fast-forwards when no one else changed the package meanwhile. Otherwise offline work rejoins as a branch when the disconnection exceeded 60 s or concurrent edits touched the client's blocks, and other divergences merge as CRDT updates. *Why:* the hazard is unseen concurrent edits, not elapsed time (R3-46), and a CRDT guarantees convergence, not correctness. *Rejected:* a pure 60 s rule; CRDT merge of every divergence. (revised in round 2)

One TLS 1.3 connection (WebSocket, or WebTransport) carries live sync (signed update batches every 30 ms after version-vector catch-up), object sync (missing closures as packs, pushed before a compare-and-swap ref update) and events with resumable cursors.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Live co-editing | Loro document per (package, module label); signed updates | `AccessDenied` | KLN-O-COLLAB-2 | 2 |
| Reconcile step | Edits to tree operations; order checks after merge | Unparseable blocks keep kind and result | KLN-O-COLLAB-1 | 2 |
| Labelled replication | Higher-labelled modules in their own documents | Downward moves refused | KLN-O-LABEL-1 | 2 |
| Presence and locks | Ephemeral presence; advisory or enforced locks | `LockHeld` | KLN-O-COLLAB-2 | 2 |
| Offline rejoin | Fast-forward, CRDT merge or branch | Conflicts become a Proposal | KLN-O-COLLAB-3 | 1 (branches), 2 (live) |
## Items, revisions and BOMs

PLM is not a separate vault: lifecycle records are signed CAS records in the design repository, BOMs are Kiln nodes, and gates are checks.

### Items

Item kinds are `Part`, `Assembly`, `Document`, `Software` item, `Purchased` catalog part and `Program`, a manufacturing program (contract 2). An Item record holds number, kind, name, classification, home repository and path, make or buy, unit of measure and labels. Revisions, states, effectivity and signatures live in records, because releasing must not edit what it releases.

**Decision D-KLN-45:** Item numbers live in source through `part(…, item:)` and its equivalents, where BOM nodes read them; an `External` system of record assigns them through a Proposal, and renumbering a released Item creates a new Item through a change order. *Why:* a number is outside the `ItemDefinition`, so assigning one marks nothing modified, and records keyed by lineage need a second identity (R9-53). *Rejected:* numbers in records referenced by a local key (R10-44).

A numbering policy sets the format and whether gaps are allowed. The server leases clients blocks of 20 numbers for offline work, and unused numbers return as void records after 30 days. Where gaps are forbidden, the first push replaces provisional numbers in a Change by the server's service principal.

**Decision D-KLN-39:** Each record type (item number, revision label, state, change order, BOM, approvals) has a system of record, `Crucible` or `External(connector)`. Under `External` the release Act publishes a release package (STEP AP242 with PMI, drawings, BOM, NC programs, a source archive) into the external revision, and external approvals return as pinned evidence, never as Approvals. *Why:* adopters keep an enterprise PLM authoritative for years (R4-19), and whoever writes the connector's input could otherwise forge a release (R11-18). *Rejected:* Crucible as the only system of record; external approvals as Approvals. (revised in round 3)

A release in this mode still needs an Approval on Crucible's page by a principal Cedar assigns. Where the external system is the only approver, that Approval covers only the publication, and the release record states "approved externally", naming the system. A release plan carries its ERP, MES and enterprise PLM deliveries as effects under its one Approval (contract 7.6).

An organization parts-policy package lists approved `Purchased` Items with approved manufacturers and part numbers, lifecycle (`Preliminary`, `Approved`, `NotRecommended`, `Obsolete`) and preferred flags. ELX selections and MEC's `fasten` resolve over approved parts first and reach the open catalog only under a Waiver (contract 2) of the parts-policy check.

**Decision D-KLN-25:** Interchangeability decides between a new revision and a new item number; Crucible computes it by comparing two definitions at their interfaces (mates, envelope, mass properties, fit and function checks), and a person confirms the verdict. *Why:* form-fit-function judgment is the most error-prone step of change control, and Crucible holds the data. *Rejected:* human judgment alone; a fully automatic verdict (some functions are not modelled).

### Revisions and lifecycle states

A revision's `ItemDefinition` (contract 5) holds, per Item kind, what is made, loaded or read as the product.

| Item kind | `ItemDefinition` |
| --- | --- |
| Part, Assembly | `GeometryId`s with definitional attributes by canonical entity number (contract 5's definitional attributes), `Material` `ObjectId`s, properties, BOM by value |
| Document | Semantic content: views, annotations, notes |
| Software item | Binary hashes, software bill of materials digest, target bindings, toolchain digest |
| `Program` | Posted program, simulation evidence ids, machine class, nominal tool assemblies (MFG) |
| `Purchased` | Approved-manufacturer entries |

The revision record adds the label, source `ChangeId`, release tag, classes of cited results and signatures. The definition digest hashes an `ItemDefinition` with late-bound fields as placeholders: MEC's title-block fields, and ELX's silkscreen revision, date and serial text.

**Decision D-KLN-26:** An Item is modified since release exactly when its `ItemDefinition` differs from every definition its revision records. An upgrade that keeps topology and definitional attributes and moves geometry within the definition tolerance adds its definition through the upgrade Proposal, and lifecycle-bound text is filled at output. *Why:* refactors change no `GeometryId` (R3-01), bit-level upgrades must not mark Items modified (R4-17), and a changed cosmetic thread moves no geometry (R8-01). *Rejected:* revision on any source change; `ObjectId` identity (renames would void releases). (revised in round 3)

"Keeps topology" means equal topology in Anvil's normal form with entities matched by `EntityId`; `anvil::deviation` measures the move. The definition tolerance defaults to the larger of 10ρ (ten times the Body's resolution) and the smaller of 0.1 µm and 1% of the Item's tightest tolerance, the general tolerance counting when none is tighter. A `Warning` check flags Items whose 1% falls below 10ρ.

**Decision D-KLN-47:** Revision-label rules are overridable policy data in the numbering policy package, which names the practice it follows, such as ASME Y14.35-2025. The default uses numbers, or letters skipping I, O, Q, S, X and Z, which read as digits or axis names. *Why:* customers follow their own drawing practice, and no code depends on labels (R10-44). *Rejected:* label rules fixed in code.

| State | Meaning | Entered by |
| --- | --- | --- |
| `InWork` | Being designed | Creation; a Change altering a released definition |
| `InReview` | Frozen candidate in an open order | Submission |
| `Prototype` | Released for prototype builds | An order with prototype scope |
| `Released` | Approved for production at its effectivity | The release Act |
| `Superseded` | Replaced, valid within its effectivity | The next revision's release |
| `Obsolete` | Not for new builds | An order with obsolescence disposition |

Entering `Released` requires every check to meet the gate predicate (contract 5), every child Item released already or in the same order, the required Approvals and no open conflicts. A policy package may replace the state machine. Phase 1 ships GP1's minimal lifecycle: item numbers, revision labels on release tags, `InWork` and `Released`, and the EBOM.

### Effectivity and variants

Windchill supports Serial, MSN, Block, Lot and Date effectivity; Crucible has one record with four kinds (`Date`, `Serial`, `Lot`, `Block`; an MSN is a `Serial`) in an end-item context. A configuration point (an end item and a value) is an input cell: Kiln picks the effective release, resolves each usage to the child revision effective there and assembles released `ItemDefinition`s without re-evaluating source. Substitution needs interchangeable revisions and exactly one applicable revision per usage and point.

**Decision D-KLN-27:** Variants are `#[configuration]` parameters of assembly features, and Kiln computes the 150% BOM by abstract interpretation with them symbolic. A usage's existence depends only on them and constants, an Instance set is one line with a quantity per configuration point, and SAT checks report dead usages, collisions and unbuildable configurations. *Why:* variants stay in the one model, a solver proves rule consistency (R3-18), and a fastener per resolved hole stays one usage (R9-16). *Rejected:* variant BOM tables (drift); enumerating configurations (exponential). (revised in round 3)

A 100% BOM is the 150% BOM at one configuration point. CI builds the declared sellable configurations plus a pairwise covering set and evaluates the rest symbolically (R4-21). This tab owns variant semantics and their oracle; ELX cites them and keeps its covering-set policy for boards.

### BOM views and where-used

| View | Content | Source |
| --- | --- | --- |
| EBOM | Items, quantities with units, find numbers, reference designators, conditions, effectivity; lines from MEC's `bom_item` | Assembly graph at a Change or configuration point |
| MBOM | Phantoms, kits, raw stock, consumables, manufacturing-only Items | MFG packages referencing EBOM Items |
| Service BOM | Field-replaceable units, spare kits, service effectivity | EBOM plus service annotations |

Views are Kiln nodes, never edited directly, and a released BOM changes only through a change order. The MBOM reconciliation check verifies that every EBOM Item and quantity is consumed exactly once per configuration or marked as not manufactured. BOMs export as CSV, as STEP AP242 product structure and through ECO's ERP connector.

The where-used index gains usage edges (parent revision, child Item, quantity, effectivity, condition) at each release and protected Change, across repositories and through `Purchased` Items. Lookups return parents up to end items, unreadable usages appear only as a count, and the index drives change impact, end-of-life notices and vulnerability response.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Items, numbering and labels | Item records; numbers in source; leased blocks; label policy | Duplicate number rejected at push | KLN-O-PLM-2 | 1 |
| System of record | Per record type; external approvals as evidence | Release fails while the connector is down | KLN-O-PLM-10 | 2 |
| Parts policy | Approved `Purchased` Items; Waivers | Policy check fails without a Waiver | KLN-O-PLM-11 | 2 |
| Interchangeability | Interface comparison | Unmodelled interfaces need a person | KLN-O-PLM-3 | 3 |
| Revisions and states | Revision records; gate predicate; state machine | Every unmet guard named | KLN-O-PLM-1 | 1 (`InWork`, `Released`), 2 |
| Item definitions | Per-kind `ItemDefinition` and digests | — | KLN-O-CHG-2 | 1 |
| Definition equivalence | Definition tolerance; normal-form topology | Out-of-tolerance upgrades mark Items modified | KLN-O-PLM-9 | 2 |
| Effectivity | Records and configuration points | Gaps and overlaps fail | KLN-O-PLM-4 | 3 |
| Variants and 150% BOM | Abstract interpretation; SAT; computed set quantities | Dead usages, collisions, unbuildable configurations | KLN-O-PLM-5 | 3 |
| BOM views | EBOM, MBOM, service BOM nodes | Reconciliation fails a check | KLN-O-PLM-6 | 1 (EBOM), 2 |
| Where-used | Indexed and access-filtered | Restricted usages counted | KLN-O-PLM-7 | 2 |

## Change control, signatures and compliance

### Change orders

| Record | Purpose and mechanism |
| --- | --- |
| Change request (ECR) | A problem or improvement with evidence, from nonconformances, complaints, CAPAs, field failures or agent findings |
| Engineering change order | A Proposal with lifecycle scope: affected Items with from and to revisions, effectivity, stock disposition, plan |
| Manufacturing change order (MCO) | A Proposal under the MCO policy class (D-KLN-38) |
| Change notice (ECN) | A signed record created by the release, with acknowledgements |
| Deviation | A temporary departure for given serials or lots, with expiry, granted by the `grant_deviation` Act |

An order starts from requests on a branch from the named release, and agents prepare work as Proposals under it. Impact analysis covers where-used, open orders on the same Items, interchangeability, MBOM reconciliation, compliance and dispositions, and submission moves affected Items to `InReview` and freezes the branch.

`act.prepare` produces a release plan whose subject is the order's `ApprovalSubject`, so the order's approvals are the plan's Approvals (R3-22). `act.commit` recomputes the subject at its target and refuses a mismatch; the merge, tag, revision records, effectivity and notice then commit in one transaction.

[[DIAGRAM diagrams/05-kiln-change-order-lifecycle.jsx: change order lifecycle · 8 stages, one loop back on a changed subject]]

Read the upper row left to right and the lower row right to left; the dashed arrow is the one loop, taken when the subject changes after approval.

**Decision D-KLN-28:** An approval signs the `ObjectId` of the order's `ApprovalSubject` (contract 5), covering the `ItemDefinition` digests of every affected Item of every kind, while the head `ChangeId` and the CI report stay unsigned provenance. *Why:* a rebase or CI re-run of identical content keeps approvals (R3-16), and a geometry-only subject would let a rebase swap firmware or a Material under a valid approval (R9-01). *Rejected:* signing the head `ChangeId`; a subject of geometry and PMI only. (revised in round 3)

An order's author cannot be its only approver, and agents never sign; they attach analysis as evidence. Concurrent orders on one Item serialize at release.

A policy allowance (contract 5) is a policy-package record changed only through `propose.policy` with two signers; phase 1 ships it with COV's catalogue (D-COV-24), though GP1's and GP2's proof loads supply their checks' model form. Waivers are contract 2's signature records, and a `#[waive]` attribute in source is only a request that review shows.

**Decision D-KLN-38:** Manufacturing change orders are their own policy class, limited to MBOM, routings, programs, fixtures, work instructions and inspection plans, and rejected if they touch an EBOM definition. `Program` Items move `Prototype`, `Proven` (after a first-article record), `Released`, approved against a machine class and nominal tool assemblies (contract 7.6). *Why:* shops change feeds and tools daily without touching the part (R4-11), and a serial-bound subject needs an approval per sister machine (R10-08). *Rejected:* every shop edit as an engineering order. (revised in round 3)

A first-article record is a signed record joining program revision, machine serial, part serial and one passing Evidence record per characteristic (MFG); phase 3's AS9102 forms render it. An order that changes a part returns exactly its dependent programs to `Prototype`: generated ones by their targets, imported ones by the revisions they declare in `verified_against`.

### Electronic signatures

A signature record holds signer, printed name, server time (no offline signing), meaning (`Authored`, `Reviewed`, `Approved`, `Released`, `Verified` or a policy meaning), the signed `ObjectId`, an algorithm id and the signature. People sign through WebAuthn with a device-bound credential enrolled for approval (contract 7.6). The record keeps the authenticator data, the client data whose challenge is the signed `ObjectId`, and the attestation, so it verifies offline.

Every Approval of a release, a `release_data` Act or a physical-effect Act is a signature record. Phase 1 ships this record for the GP1 release; Part 11 mode, re-authentication policy and dual signing follow in phase 2.

**Decision D-KLN-42:** Every signature record carries an algorithm id, and tenant records never use LMS. From phase 2, release tags, checkpoints and provenance are dual-signed with a classical signature plus ML-DSA-87 (FIPS 204, final on 13 August 2024), and long-retention records are re-timestamped before an algorithm retires. *Why:* records must verify for decades, and one stateful LMS key cannot serve a tenant's many signers safely (R11-25). *Rejected:* classical signatures only; replacing algorithms in place. (revised in round 3)

| 21 CFR Part 11 | Crucible mechanism |
| --- | --- |
| 11.10(a), (b) | Validation package from this tab's oracles; PDF/A plus JSON exports with an offline verifier |
| 11.10(c), (e) | Retention locks (D-KLN-18); transaction and audit logs |
| 11.10(f) to (k) | Lifecycle guards; Cedar; device-signed records; training records; controlled documentation |
| 11.30 | Cloud treated as open: domain encryption, signed records, end-to-end mode |
| 11.50, 11.70 | Name, time and meaning on every rendering; one `ObjectId` per signature |
| 11.100 to 11.300 | One principal per person; re-authentication per signing; AAL3 credentials |

The 11.100 certification to FDA is the customer's act. FDA's QMSR, effective 2 February 2026, incorporates ISO 13485:2016, and 820.10(c) applies its design clause 7.3 to class II and III devices, software-automated class I devices and listed class I types. Orders, checks and reports supply the design history.

**Decision D-KLN-49:** The Part 11 and AS9100 assessment package is contract 7.7's Computer Software Assurance package plus, per release, a table from each 21 CFR 11.10 clause and selected AS9100 clause to KLN oracles and results. The customer chooses the assessor; phase 3's third-party assessment uses one the founder retains. *Why:* assessors read clause-to-evidence tables, which oracle results fill (R9-54). *Rejected:* a package format per assessor.

### Traceability and compliance

Requirements are `std::systems` records in source or imported through ReqIF, OMG's format for exchanging requirements between organizations; a `require` names those it verifies. The traceability matrix is a Kiln node from requirement to check to outcome to evidence. Coverage is a check: each requirement needs a verifying check of its method (`Analysis`, `Test`, `Inspection` or `Demonstration`), each `Test` requirement an Evidence record, and a changed requirement's links stay suspect until a person signs them.

Compliance is a check over data, with substance rules (RoHS, REACH and SCIP, conflict minerals) from MFG. This tab owns compositions rolled up from `Material` versions, signed supplier declarations, regulation packages pinned as External inputs, exemptions signed by `quality`, and verdicts per revision (`Compliant`, `NonCompliant`, `Unknown`). Missing data is `Unknown` and blocks releases that require compliance, and a new regulation version re-evaluates released revisions and opens change requests through where-used.

The EU Cyber Resilience Act's reporting duties for actively exploited vulnerabilities apply from 11 September 2026: an early warning within 24 hours and a notification within 72. `Software` Items carry a CycloneDX 1.7 or SPDX 3.0 software bill of materials per release (ELX), and where-used lists affected shipped serials within minutes (target).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Approval subjects | Subject `ObjectId` signed; recomputed at commit | Changed subject voids; mismatch refused | KLN-O-CHG-1 | 1 |
| Policy allowances and Waivers | Two-signer allowances; contract 2's Waivers | Uncovered conditional `Pass` is `Undecided` | KLN-O-PLM-1 | 1 |
| Change requests, orders, notices | Records plus Proposal; release Act | Unmet conditions named | KLN-O-CHG-1 | 2 |
| Manufacturing change orders | MCO class; `Program` Items by machine class | EBOM-touching MCO rejected | KLN-O-PLM-8 | 2 |
| First-article records | Program, serials, Evidence per characteristic | Program stays `Prototype` | KLN-O-PLM-8 | 2 |
| Signature records | Detached, with WebAuthn data | Unenrolled credentials cannot sign | KLN-O-SIG-1 | 1 |
| Part 11 mode and assessment | Re-authentication; Part 11 controls; clause tables | Failed re-authentication blocks and is audited | KLN-O-SIG-1 | 2, 3 |
| Signature agility | Algorithm ids; dual signatures; no tenant LMS | Unknown algorithm named | KLN-O-SIG-2 | 2 |
| Requirements traceability | Requirement records; `verifies` links | Uncovered or suspect requirements block | KLN-O-TRACE-1 | 2 |
| Compliance checks | Regulation packages, declarations | `Unknown` | KLN-O-COMPL-1 | 3 |
| Vulnerability where-used | Software bills of materials | Unknown contents flagged | KLN-O-VULN-1 | 3 |

## Supplier collaboration and data release

### Data leaving a tenant

**Decision D-KLN-40:** AGT owns the `release_data` Act family (D-AGT-30), and `repo` runs its stage at `act.commit` for every exit, shared-branch pushes and federation sync included. The stage reads labels, the `RecipientRecord`, a fresh screening and any `ControlAuthorization`, and writes the release-data record, watermark, expiry and audit entry in one transaction. *Why:* six exit paths had six sets of controls (R5-06), and checks committed with their records cannot drift from them. *Rejected:* per-path controls; a second definition of the family here. (revised in round 3)

A human's export of an uncontrolled `public` or `internal` payload to a local folder or application, addressed to no recipient record, is an audited local write, not an Act (contract 7.6).

A `RecipientRecord` holds the organization, endpoints, out-of-band verification with its date, screening list versions, expiry and a clearance bounding the confidentiality label (level, controls with their `ControlAuthorization`s, scopes, licences). `release_data` refuses a payload above the clearance, or one whose `DataLicence` forbids redistribution to that recipient. Screening runs at every commit against lists at most 24 h old: the US Consolidated Screening List, updated daily, and the EU and UK lists where the tenant's policy names them.

A recipient-record change needs two people (D-KLN-41), is refused from a context with either integrity flag, and takes effect after 24 h with notice to the previous contact. The approval page flags recipients changed in the last 7 days. Watermarking is a recorded deterministic transform: the release-data record stores the file's hash, recipient, parameters and the recipient file's hash, so any leaked file traces to its release.

### Supplier packages and derived views

Suppliers have their own principals and never browse a design repository. They receive signed supplier packages listing contents, source Changes, recipient, labels and expiry: STEP AP242 with PMI, 3MF or glTF, PDF drawings with QIF 3.0 inspection plans, requirements and derived models. They return quotes, feedback on a shared branch, QIF results, certificates and declarations, read by agents as `ExternalText`, and the audit log records what each received.

| Derived view | Recipient gets | Stays private |
| --- | --- | --- |
| Frozen geometry | Released Bodies at fixed parameters, with PMI | Source, history, parameters |
| Envelope and interfaces | An offset hull, interface faces, mates, mass properties | Internal geometry |
| Behavioral model | An FMI 3.0 FMU or reduced model with its `ValidityEnvelope` | Geometry and source |
| Remote parametric model | A feature callable with parameters, evaluated on the owner's workers | Source and intermediate values |

**Decision D-KLN-31:** Parametric sharing without source uses remote evaluation on the owner's workers, never shipped compiled code. *Why:* code on the recipient's machine, Wasm included, can be decompiled, while remote evaluation keeps source with its owner and still caches by `OpKey`. *Rejected:* obfuscated Wasm components (false security); encrypted packages (the key must reach the recipient).

Each remote parametric share declares per-recipient query budgets, parameter ranges and steps, and every query is audited; one over budget fails with `ShareQuotaExceeded`. Redaction replaces `confidential` features by defeatured geometry or envelopes within a declared deviation and strips names, comments, provenance ids and history, and a redaction check verifies before signing that nothing leaks.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Data-release stage | Checks at `act.commit`, shared branches and federation included; local writes audited | Commit refused, naming the check | KLN-O-RELEASE-1 | 1 |
| Recipient records and screening | Clearances; two-person changes; lists at most 24 h old | Over-clearance or listed party refused | KLN-O-RELEASE-1 | 1 (other organizations), 2 (internal) |
| Supplier packages and watermarks | Signed packages with expiry | Expired access denied | KLN-O-SHARE-2 | 3 |
| Derived views and redaction | Redaction check | A leak refuses signing | KLN-O-SHARE-1 | 3 |
| Remote parametric shares | Budgets, ranges, audit | `ShareQuotaExceeded` | KLN-O-SHARE-3 | 3 |
## Security

### Identity and authorization

| Principal | Authentication | Keys |
| --- | --- | --- |
| Person | SSO over OpenID Connect or SAML 2.0; local accounts only on desktop and air-gapped installs; WebAuthn | Hardware-backed device key per device |
| Agent | Registered by an owner; short-lived tokens by exchange (AGT) | Ephemeral key bound to the token |
| Service | Workers, builders, runners, integrations | Workload identity or mTLS certificates |
| External organization | Its identity provider, or invited accounts with WebAuthn | As for persons |

SCIM 2.0 provisions users, sessions last 12 h, signing always re-authenticates, and offline desktops hold a 7-day refresh grant before losing push and labelled reads.

**Decision D-KLN-43:** Logs and records hold pseudonymous principal ids, mapped to names under per-person keys that can be crypto-shredded unless a retention lock keeps them. Each lock carries a `retention_basis` the customer sets as controller: `UnionOrMemberStateLaw { citation }`, `LegalClaims`, `ThirdCountryLaw { citation }` or `Contract`. *Why:* GDPR Article 17(3)(b) excepts only obligations under "Union or Member State law", so a US retention duty needs a stated basis (R11-42). *Rejected:* names in records; pruning logs (breaks verification). (revised in round 3)

An erasure request against a `ThirdCountryLaw` lock goes to the customer's privacy officer rather than being refused, as the DPIA template states.

**Decision D-KLN-29:** Authorization uses Cedar policies, evaluated in process on every request, including live-document updates at the relay. *Why:* Cedar covers role- and attribute-based access in one language, is written in Rust with a Lean model, and proves that a policy change grants no unintended access. *Rejected:* Open Policy Agent with Rego; hand-written role checks.

Roles come from identity-provider groups (`viewer`, `commenter`, `editor`, `maintainer`, `approver`, `release_manager`, `export_officer`, `quality`, `admin`). Attributes describe principals (organization, location, training, licences, `ControlAuthorization`s) and resources (labels, Item state, repository, path). Actions are `read_source`, `read_derived`, `evaluate`, `edit`, `push`, `merge`, `approve`, `sign`, `release`, `purge` and `manage_policy`; deny overrides allow, the default is deny, and policy changes are `propose.policy` Proposals whose access changes Cedar lists before merge.

**Decision D-KLN-41:** Two distinct people, one an `export_officer` for label items, approve: clearances of endpoints, clients and recipients for `confidential` or controlled data; declassification; `ControlAuthorization`s; widening Cedar changes; auto-merge policy; recipient records; `standing_release` plans (D-AGT-33); AGT's `allow_raw_external` and training opt-in; oracle and protected-path changes; purges. *Why:* one phished administrator could otherwise export a whole ITAR program (R5-15), and one list serves every tab (R11-22). *Rejected:* single approvers with audit only. (revised in round 3)

Break-glass access is invoked by one administrator with an AAL3 credential, lasts at most 4 hours and grants only reads within that administrator's clearances, agent freeze, ref revert, lock release and session termination. It never declassifies, clears an endpoint, client or recipient, changes Cedar policy, purges, approves or signs. Every action under it is audited with its id, and its review is a Proposal a second administrator closes within 72 hours.

Protected refs take rules per pattern: no direct pushes, required checks and reviews without self-approval, signed Changes, forward-only refs and immovable tags, change orders for `Released` Items, and no agent ref updates, approvals or signatures. Agents write only `agents/*` refs, within their scope and their owner's permissions (AGT), and policy Proposals from contexts holding untrusted data are refused.

### Labels and export control

Labels are contract 5's two parts, attached to repositories, modules, Items, records, CAS objects and API responses. The confidentiality part is what clearances, write-down, encryption domains and live replication compare, and `Labels::is_controlled()` holds when its `controls` set is non-empty; lowering it needs a declassification record signed by two people, one an export officer.

The integrity part never blocks a read or a write, and merging the Change that introduced a pin, an Asset or a source span clears it on typed values. A merged import thus endorses an Asset's geometry, structure and numbers, while its text stays `ExternalText` and a new Asset revision starts untrusted.

The module is the unit of a source label (contract 7.1): an uncleared clone holds only a higher-labelled module's declassified signature, compiles against it and evaluates the module remotely on cleared workers.

A principal, endpoint, recipient or service satisfies a `controls` element only through a `ControlAuthorization` record: regime, classifications, basis (US person, licence, licence exception, no licence required), permitted countries and recipients, conditions and expiry. An export officer creates it with a second person, and an Act plan's `authorization` names one. A controlled node runs and is stored only in the regulated cloud, end-to-end mode or a customer deployment, unless a record covers the operator's staff.

**Decision D-KLN-32:** Export-controlled data is handled by labels that propagate through Kiln and model contexts, policies over principal attributes, residency-bound storage and compute, and an optional end-to-end mode. *Why:* 22 CFR 120.56(a)(1) counts "Visual or other inspection by foreign persons" of technical data as a release, so every path to the data needs a check. *Rejected:* air-gapped installations as the only option; repository flags without propagation (derived values leak). (revised in round 2)

Residency can bind storage and compute to named regions and staff attributes. Other egress channels follow PLT's label-aware rule (D-PLT-38).

End-to-end mode keeps plaintext off Crucible's cloud. 22 CFR 120.54(a)(5) treats as not exported unclassified technical data end-to-end encrypted with FIPS 140-2 or successor modules, neither stored in nor sent to or from a §126.1 country, and 15 CFR 734.18(a)(5) is similar. Keys stay in the customer's key service and go only to the originator, U.S. persons in the United States or others authorized (120.54(b)(2)); qualification is the customer's legal determination.

**Decision D-KLN-48:** In end-to-end mode a customer-hosted tier 2 store and trusted builders inside the boundary form their own trust domain under contract 7.8, keyed in the customer's key service and trusted only by that customer's builders. *Why:* otherwise end-to-end customers lose the shared cache (R9-54). *Rejected:* a cloud tier holding customer keys (defeats the mode).

### Audit and encryption

Every write, read of labelled data, policy decision, signature, login, Act and administrative action is an audit entry holding only identifiers, digests and the pseudonymous principal. A full Act plan, approval or policy text is a CAS record in its label's encryption domain that the entry commits to by `ObjectId`, so readers without the label verify inclusion without reading content. KLN owns the log, its envelope and this rule; AGT owns the `api`-call fields inside an entry.

**Decision D-KLN-30:** The audit log, repository transaction logs and release tags are entries in per-tenant transparency logs in the C2SP tlog-tiles format, with checkpoints signed by the deployment and optionally cosigned by customer witnesses. *Why:* an RFC 6962 Merkle log exposes any rewrite or fork to anyone holding an earlier checkpoint, and witnesses keep the operator honest. *Rejected:* an append-only database table (rewritable undetectably); a public blockchain.

Clients verify consistency against their last checkpoint on every sync. Checkpoints carry Ed25519, as tlog-tiles requires for public witnesses, ECDSA P-256 in FIPS mode and ML-DSA-87 from phase 2. Release records keep the longest retention configured, transcripts and API logs 12 months by default, and phase 1's signed audit log already uses the tlog-tiles layout, without witnesses.

Transport is TLS 1.3, mutual between servers, workers and runners, and release and checkpoint keys live in HSMs and are never exported. FIPS mode routes all cryptography through a FIPS 140-3 module from PLT's provider, such as AWS-LC through aws-lc-rs, whose AWS-LC 3 module holds certificate 5314. NIST placed all FIPS 140-2 certificates on its historical list on 22 September 2026.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Identity | OIDC or SAML, SCIM, WebAuthn, device keys | Failed authentication audited | KLN-O-POLICY-1 | 1 |
| Pseudonymous records | Per-person keys; retention bases | Erasure refused, or routed for `ThirdCountryLaw` | KLN-O-AUDIT-2 | 2 |
| Authorization and branch protection | Cedar on every request; rules per ref pattern | `AccessDenied` naming the permission | KLN-O-POLICY-1 | 1 |
| Two-person rule and break-glass | One list; bounded break-glass | Change pending; forbidden actions refused | KLN-O-POLICY-1 | 1 |
| Labels and declassification | Confidentiality lattice; integrity by provenance; module labels | `label/write_down` | KLN-O-LABEL-1 | 1 |
| Control authorizations | `ControlAuthorization` records; controlled placement | Uncovered access refused | KLN-O-LABEL-1 | 1 |
| Residency | Region and operator constraints | `ResidencyDenied` | KLN-O-LABEL-1 | 2 |
| End-to-end mode | Customer keys; customer-hosted cache domain | Key release to the ineligible refused | KLN-O-LABEL-2 | 3 |
| Tamper-evident audit | tlog-tiles; identifiers and digests only; witnesses | Forks detected at sync | KLN-O-AUDIT-1 | 1 (log), 2 (witnesses) |
| FIPS mode | PLT's FIPS 140-3 provider | Non-approved algorithms refused | KLN-O-SIG-2 | 2 |

## Deployment

### Modes

Modes differ in services and data location, never in features.

| Mode | Services | Metadata store | Phase |
| --- | --- | --- | --- |
| Desktop | Kiln, local CAS and repository, local relay | SQLite | 1 |
| Browser | The engine in a worker, one engine per origin | SQLite on OPFS (`opfs-sahpool`) | 1 |
| Team server | Host or VM install: repository server, CI coordinator, untrusted back end, trusted builder; `apps/relay` and `apps/rig-runner`'s gateway from phase 2 | SQLite, or PostgreSQL | 1 |
| Cloud | Regional cells: gateways, relays, repository servers, worker fleets, per-tenant logs | FoundationDB | 2 |
| Regulated cloud | Contract 7.7's regulated mode; classified information is out of scope in every mode | FoundationDB | 3 |
| On-premises and air-gapped | The cloud stack on Kubernetes, or a team server; air-gapped adds no external network and an offline licence | PostgreSQL or FoundationDB | 2, 3 |

A desktop is a full peer that works offline and connects to any number of remotes. Without a team server it designs, simulates, evaluates and exports locally; Proposals, releases and every Act need one (contract 13.2). Tenant onboarding applies ECO's sector controls (D-ECO-29).

The single-node team server runs Proposal CI in Firecracker where `/dev/kvm` exists and in gVisor otherwise, because Firecracker needs `/dev/kvm` and EC2 offers KVM only on `.metal` instances. The installer reports the active back end, the health check refuses Proposal CI when neither works, and the trusted builder runs as a separate OS user without access to the sandbox's sockets or images.

**Decision D-KLN-33:** The desktop is local-first: the local repository is authoritative for unpushed work, and everything except remote services works offline. *Why:* engineers work on aircraft, at plants and on secure networks, and local-first makes interactive latency independent of the network. *Rejected:* a thin client over a cloud model (fails offline and air-gapped).

**Decision D-KLN-44:** In a browser, Kiln and `repo` run only in the engine PLT's one-engine-per-origin rule designates (D-PLT-29), which holds the journal, the SQLite store and every CAS pack but a heavy worker's pack in transfer. It adopts that pack by index, and any new owner, a recycled engine worker included, replays the journal first. *Why:* `opfs-sahpool` fails in a second tab (R6-15), and access handles lock per file (R12-19). *Rejected:* one engine per tab; heavy workers writing the engine's packs. (revised in round 3)

### Sync, scale and recovery

Mirrors keep label-filtered replicas at sites, and federation joins two organizations' servers through shared branches. Air-gapped sites exchange signed bundles (`crucible bundle create --since <checkpoint>`), and `crucible bundle import` verifies signatures, closure, labels, span integrity and log consistency after the receiving domain's review.

| Scope | Target (phase 4 unless marked) |
| --- | --- |
| Desktop | Local CAS up to 2 TiB; 10 million Changes per repository; contract 13.3's open and rebuild rows |
| Team server, 16 cores, 64 GiB | 200 active users, 50 live documents, 1,000 Changes per minute, 20 TiB (phase 2) |
| Cloud cell | 50,000 active users; ref update p99 under 200 ms; 10 GB/s object fetch; 100 participants per document |
| Cloud workers | 10,000 cores per tenant within 5 minutes; first remote result for cached inputs under 1 s |
| Repository | 100 TiB of results; 10⁹ objects; where-used over 10⁶ Items under 1 s |

The restore verifier checks every ref's closure against its hashes and every log against checkpoints held by clients and witnesses. Team servers target 5 minutes of data loss and 4 hours to recover, through log shipping, object versioning and nightly test restores. The cloud targets no loss within a region, 15 minutes across regions, 1 hour to fail over and write-once backups kept 35 days.

### Privacy

Deployments ship records-of-processing entries, a DPIA template and the list of hosted model providers as sub-processors (AGT). Presence, follow mode and approval tab-view recording are organization settings, and works-council mode disables per-person activity analytics, since BetrVG §87(1) item 6 gives German works councils co-determination over monitoring devices.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Desktop offline | Local repository, Kiln and exports without a server | `Offline` with the queued step | KLN-O-DEPLOY-1 | 1 |
| Browser engine ownership | One engine per origin; journal replay; pack adoption | A second engine refuses to start | KLN-O-DEPLOY-1 | 1 |
| Team server and on-premises | Host install with Firecracker or gVisor; separate builder user; Kubernetes package | CI refused without a back end; schema mismatch refused | KLN-O-DEPLOY-2 | 1, 2 |
| Cloud and regulated cloud | Regional cells; regulated controls | Cell failover | KLN-O-DEPLOY-3 | 2 (cloud), 3 (regulated) |
| Air-gapped bundles | Signed bundles | Rejected with the reason | KLN-O-DEPLOY-4 | 3 |
| Restore verifier | Closure and log consistency | Missing objects listed | KLN-O-RESTORE-1 | 2 |
| Privacy controls | Pseudonymous ids; works-council mode | — | KLN-O-AUDIT-2 | 2 |

## External interfaces and physical tests

### `api` methods and events

AGT owns the method catalog; this tab supplies repository behavior within contract 7.6's eight groups, and every response carries its `ChangeId`, generation and labels.

| Methods | Group | Agents |
| --- | --- | --- |
| `read.tree`, `read.source`, `read.history`, `read.audit`, `read.where_used`, `read.bom` | Read | Access-filtered; untrusted text by handle |
| `edit.apply`, `edit.stream`, `edit.revert`, `edit.create_branch`, `edit.undo` | Edit | Own branches only |
| `evaluate.*`, `evaluate.subscribe`, `evaluate.cancel` | Evaluate | Within budget |
| `compare.diff`, `compare.merge_preview` | Compare | Allowed |
| `propose.*`, including `change_request`, `change_order`, `policy`, `declassify`, `purge`, `endorse_text` | Propose | Under AGT's rules (D-AGT-17); policy only from clean contexts; the last three human-only |
| Act classes `release`, `grant_deviation` and `run_rig_test`, and the `release_data` family | Act | May prepare; never approve |

**Decision D-KLN-34:** Events carry identifiers and states, never design content, and above `internal` per-subscription opaque ids (an HMAC of the `ObjectId` under the subscription's key). ECO owns the CloudEvents envelope and delivery (D-ECO-12); this tab defines repository, lifecycle and evaluation event types (AGT the `act.*` and `session.*` types) and a per-repository `sequence` attribute. *Why:* thin events keep policy and audit in one place (R3-23), and a small record's `ObjectId` lets a receiver confirm a guessed value (R11-39). *Rejected:* full payloads (bypass policy). (revised in round 3)

Event types: `change.created`, `ref.updated`, `ref.conflicted`, `tag.created`; `evaluation.completed`, `evaluation.aborted`; `proposal.opened`, `proposal.updated`, `proposal.merged`, `ci.completed`, `check.failed`, `evidence.recorded`; `change_request.created`, `change_order.submitted`, `change_order.approved`, `change_order.rejected`, `release.created`, `change_notice.issued`, `item.state_changed`, `deviation.granted`; `compliance.alert`, `vulnerability.affected`, `policy.changed`, `audit.anomaly`, `budget.threshold`.

### Physical tests and Evidence records

**Decision D-KLN-35:** Physical tests are Acts on hardware rigs whose only product is an Evidence record, signed by a TPM-held key and addressed by `CheckId` and tested input identities. An Evaluation reads the newest record valid at its measurement time, up to its evidence watermark, and releases pin it. *Why:* physical results are not pure functions (R3-17), and a recorded watermark makes one Change give one outcome on every builder (R9-03). *Rejected:* cached derived values; validity judged at evaluation time (reads the clock). (revised in round 3)

The record's id goes to the `CheckOutcome`'s `evidence_records`. The watermark is a transaction-log position, an input cell recorded in the Evaluation and CI reports, which protected branches advance by an audited ref transaction. A check declares whether evidence holds while its inputs are unchanged (a fit check) or repeats per lot or build (a fatigue test).

1. A runner enrols by proving its TPM endorsement-key chain, certifying an attestation key and quoting its boot measurements over a server nonce. The server compares the quote with reference measurements signed by the image's build, and every Evidence record cites it.
2. It pulls requests over an outbound connection, so factory networks need no inbound ports.
3. A request names its artifacts, its procedure (Ingot, or a tool-world Wasm component) and its budget in rig minutes.
4. Transfers, flashing and starts follow contract 7.6's physical-effect Acts, `flash_device` included, and emergency stops are hardware.
5. `run_rig_test` runs only on rigs under an `unattended_safe` site policy, which contract 7.1 limits to test rigs with a signed ISO 12100 risk assessment, interlocked guarding and a safety-rated stop. The runner enforces the policy's energy limits.
6. The record holds raw data in the CAS, instruments with calibration records, environment, operator and procedure version. A record whose calibration did not cover the measurement date is invalid, and checks over it fail with `CalibrationExpired`.

Checks use the measurement uncertainty MFG and FLX define, and Evidence records stay out of calibration (contract 13.1). In phase 1, external metrology for GP1 and GP2 enters as one lab-signed Evidence record per characteristic, addressed to MFG's conformance check for it.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `api` methods | Eight groups; labels; edit stream and subscriptions | Denials name the permission | KLN-O-API-1 | 1 |
| Events | Event types; opaque ids; ECO's envelope | Retries, then dead letter | KLN-O-EVENT-1 | 1 |
| Evidence records | Valid at measurement time, up to the watermark; pinned | `CalibrationExpired`; else `Undecided` | KLN-O-HW-1 | 1 (lab records), 2 |
| Runner enrolment | TPM quote against signed references | Unmatched images refused | KLN-O-HW-1 | 2 |
| Physical test Acts | Pull-based; contract 7.6 Acts; site policy and energy limits | Limit violations abort, recorded | KLN-O-HW-1 | 2 |
## State of the art

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Incremental evaluation | Suspending scheduler with constructive traces (Mokhov, Mitchell and Peyton Jones, JFP 2020); Adapton | Salsa; Buck2's DICE | Adopt, with multi-output memo entries (D-KLN-1, D-KLN-36) | Re-executed set on 500 edits; contract 13.3 rebuild rows |
| Early cutoff | Value equality with lazy content identity | Salsa; Nix content-addressed derivations | Equality interactively, `ObjectId` for sharing (D-KLN-5) | Dependents within the drag budget |
| Shared build cache | Bazel Remote Execution API v2; signed realisations (Nix RFC 62) | Bazel with Buildbarn or EngFlow | Adopt, with attestation, microVMs and two-builder agreement (D-KLN-9) | Hit rate for 20 people on GP3 and GP4; target 90% |
| Eviction | GreedyDual-Size (Cao and Irani, 1997) | LRU | Adopt (D-KLN-7) | Rebuild under 256 MiB; target within 2× |
| Deterministic testing | Whole-system deterministic simulation | FoundationDB | Adopt for Kiln, sync, collector, server | Simulated hours per night |
| Content hashing | SHA-256 against BLAKE3 | BLAKE3 | SHA-256 for every object (D-KLN-14, D-KLN-46), for FIPS approval and one identity space | KLN-O-CAS-4 |
| Chunking | FastCDC (USENIX ATC 2016); prolly trees | Rabin chunkers; Dolt | Name-free segments; FastCDC for Blobs (D-KLN-15) | Deduplication between Changes; target 95% |
| Numeric compression | pcodec; shuffling plus zstd; meshoptimizer | zstd on raw arrays | Per-chunk codecs (D-KLN-16) | Ratio and decode speed |
| Encrypted deduplication | Server-aided message-locked encryption (DupLESS) | Convergent encryption | Domain-keyed derivation (D-KLN-17) | Cross-domain confirmation test |
| Version control | Git's SHA-256 objects; Jujutsu's operation log and conflicts | Git, Jujutsu | Changes, transaction log, first-class conflicts (D-KLN-19, D-KLN-20) | No lost Change under simulation |
| CAD history and merge | Onshape microversions; GumTree; Mergiraf | Onshape; Mergiraf | Verdict, touched-set and connectivity conditions (D-KLN-21) | KLN-O-MERGE-1 |
| Live collaboration | Movable tree CRDT; Fugue; Eg-walker | Loro; Automerge 3 | Loro per (package, module label) (D-KLN-22) | KLN-O-COLLAB-2 |
| Set reconciliation | Range-based set reconciliation (Meyer 2022) | Full listings | Adopt for tier anti-entropy | Bytes against the difference size |
| Authorization | Cedar (OOPSLA 2024) | Open Policy Agent | Adopt (D-KLN-29) | p99 decision under 1 ms (target) |
| Tamper-evident logs | RFC 6962 logs as C2SP tlog-tiles with witnesses | Certificate Transparency; Sigstore Rekor | Adopt (D-KLN-30) | Fork detection under fault injection |
| Long-lived signatures | ML-DSA (FIPS 204) | Classical-only signing | Dual signatures from phase 2 (D-KLN-42) | Verification under each algorithm |
| PLM change control | Change request, order and notice workflows with effectivity | Windchill, Teamcenter, Arena, Fusion Manage | Orders as Proposals; approvals over subjects (D-KLN-28) | Scripted-order cycle time; phase 3 assessment |
| Variant management | 150% BOM with variant conditions | Teamcenter Product Configurator | Abstract interpretation and SAT (D-KLN-27) | KLN-O-PLM-5; solver time on 200 parameters |
| Browser persistence | OPFS sync access handles; `opfs-sahpool` | Per-tab engines | One engine per origin (D-KLN-44) | KLN-O-DEPLOY-1 |


## Platform notes

| Platform | Risk | Decision |
| --- | --- | --- |
| Windows | Open packs cannot be replaced; long paths; case-insensitive names | Replace by rename after close; long-path APIs; case- or normalization-only differences rejected |
| macOS | Case- and normalization-insensitive file system; App Sandbox | The same path rule; security-scoped bookmarks (PLT) |
| Linux | Weak `fsync` on some configurations | Write-then-rename with `fsync` on file and directory; simulated torn writes |
| Browsers | Storage eviction; exclusive OPFS handles; shared memory only under cross-origin isolation | Persistent storage and eager pushes; one engine per origin; `crypto.subtle` hashing; cancellation by worker termination |
| Browsers | Origin-bound WebCrypto keys | WebAuthn device keys, re-enrolled when storage is cleared |
| iPadOS and Android (Tier 2) | Memory-pressure kills | Heavy Evaluations run remotely |
| Servers | FoundationDB operations burden; uneven conditional writes on S3-compatible stores | SQLite or PostgreSQL on team servers; ref updates through the metadata store |
| Air-gapped | No federation, time source or updates | Local identity provider; signed bundles; clock audited against a site source |

## Interfaces with other subsystems

### What this tab provides

| To | Provides | Types |
| --- | --- | --- |
| ANV, FLX, Wasm components | Operation contract; two-stage keys; the limit catalog; name-free random streams; derivatives; two-builder agreement; `crucible:host` | `OpImpl`, `OpCx`, `OpKey`, `Differentiable` |
| Every tab | Memoized, progressive evaluation with cost estimates; the CAS | `Kiln::demand`, `ResultEvent`, `ResultStatus`, `CasStore` |
| ING | Keys with `CallSite`s, code hashes, overrides and limits; front-end stages; ceiling-free `Undecided`; span integrity in labels | `Abort`, `ResultStatus` |
| COV | Evidence records by watermark; label joins; policy allowances and `min_evidence_level`; Waivers | `CheckOutcome`, `Labels` |
| UIX, AGT, CI | Changes, merge, diffs, Proposals, `ReviewVerdict` and `Comment` records, live documents, locks, span provenance, where-used, the per-user view store | `ChangeId`, `MergeDriver`, `Conflict` |
| MEC, MFG, ELX | Items, per-kind definitions, effectivity, BOM views, variant semantics, orders, MCOs, the `Proven` gate on MFG's first-article records, parts policy; the approver directory MFG's gateway pins | Item and revision records |
| AGT | Write-down at `repo`; recipient records; `ControlAuthorization`s; the two-person list; signature records; the audit log; the `release_data` stage; Cedar | `Labels`, signature records |
| ECO | Leaf inputs; event types; release-data records; the system-of-record policy; `crucible:host` | Event types, Item records |
| PLT | Grades and class acceptance; key composition; uncached Aborts; cost hints; what attestation signs | `DeterminismGrade`, `OpKey` |

### What this tab requires

| From | Requirement |
| --- | --- |
| ING | Front-end stages; `CallSite`s, `CheckId`s and `LiteralSite`s; block-local parsing; free-text spans; `#[configuration]` and Instance sets; `part(…, item:)`; the Wasm guest context |
| ANV | Graded `OpImpl`s with fidelity maps, cost estimates and two-stage keys; `GeometryId`; definitional attributes; interference, deviation, normal form and history for merge; defeaturing |
| FLX | Cost models, safe points, step checkpoints; `Differentiable` operations; Fields by virtual partition |
| COV | Envelope and Material records; property reads as enclosures; External Op keys; `DataLicence` values |
| PLT | `PoolLane`s, `Interactive` included; combinators; `detmath`; memory tables; storage and heavy-worker packs; attestation; egress; the FIPS provider |
| AGT | The method catalog, `edit.stream` included; `Budget` and `PriorityClass`; context labels; risk classes; the approval page; audit `api` fields |
| MEC, MFG, ELX | Item numbers, `bom_item`, interference classes, seeds as literals; MBOM rules, machine classes, `verified_against`, characteristics, substance rules; net partitions, Software items, resolved selections |
| UIX | `CommentAnchor`s and the display of comments and verdicts |
| ECO | Event envelope and delivery from phase 1; the egress proxy; ERP and PLM connectors; the watermark transform; sector controls |

## Oracles

Oracles live in `oracles/kln/`, readable but not writable by agents. Each has a held-out split chosen by a fixed hash rule outside the agent-readable tree, or a property generator seeded at CI time (contract 3, principle 6); those marked held-out also keep a fixed held-out corpus.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| KLN-O-FPRINT-1 | Registration, closure hashes | Digests match; changed digests need a version bump; a seeded `linalg` change outside the corpus is refused |
| KLN-O-RETIRE-1 | Retired versions | A product pinned to a retired version rebuilds bit-identically; a retired GPU path causes no shared-cache cross-talk |
| KLN-O-WIT-1 | `crucible:host` | Published WIT and bindings match this tab; a hard-coded `ObjectId` of a confidential object cannot be read |
| KLN-O-MIN-1 | Minimal re-execution | On 500 scripted edits, comment-only and fuel-only included, the re-executed set equals the reference |
| KLN-O-EQUIV-1 | Incremental equals from-scratch | After every edit and upgrade, identities equal a cold build's |
| KLN-O-SITE-1 | Site keys, two stages | Equal calls at two sites get distinct `EntityId`s; designs sharing a failing geometric stage get fixes naming their own bindings |
| KLN-O-ROUNDTRIP-1 | Canonical values | Outputs from memory and from the CAS give identical dependents |
| KLN-O-ABORT-1 | Aborts | Faults at random Ops in 10,000 Evaluations; every memo entry and CAS object equals the fault-free value |
| KLN-O-LIMIT-1 | Limits | `f(n) = f(n + 1)` aborts with `DemandDepthExhausted` on every Tier 1 target, leaving no memo entry; low ceilings refuse at admission |
| KLN-O-SIM-1 | Kiln, sync, collector, server | Seeded fault simulation loses no Change and caches no wrong value; failing seeds replay |
| KLN-O-PROG-1 | Progressive results, drag lane, overrides | One generation per frame; overridden results never answer other requests; after an `Interactive`-ceiling Evaluation, a `SignOff`-ceiling one with warm caches shows `Pending`, then the decided value |
| KLN-O-CANCEL-1 | Cancellation | 10,000 randomly cancelled Evaluations equal clean ones, threaded and unisolated web builds included |
| KLN-O-EVICT-1 | Eviction | A 256 MiB budget never changes results; rebuild within 2× of unbounded (target) |
| KLN-O-BUDGET-1 | Budgets | Caps exceeded by at most one safe-point interval; `BudgetExhausted` never cached |
| KLN-O-DERIV-1 | Derivatives | Taylor test of a three-Op chain gives order 2 ± 0.1; adjoints resumed from evicted checkpoints are bit-identical |
| KLN-O-REMOTE-1 | Remote evaluation | Local and remote golden-product Evaluations give identical `ObjectId`s |
| KLN-O-TRUST-1 (held-out) | Shared-cache integrity | Forged, replayed, cross-tenant and single-builder attestations refused; planted mismatches caught; a package escaping identically on every builder reaches only its tenant; forged External Op outputs fail receipts |
| KLN-O-LABEL-1 | Labels | Labels reach every derived value; relabelling unchanged bytes re-executes nothing; write-down and out-of-region placement refused; a merged catalog pin yields trusted values, an unmerged one does not; an uncleared clone evaluates around an ITAR module it cannot read; a foreign national without a `ControlAuthorization` cannot read (EAR, 9E003) data |
| KLN-O-LABEL-2 | End-to-end mode | Servers hold no plaintext; keys reach only eligible recipients; a customer-hosted tier shares only among that customer's builders |
| KLN-O-DET-1 | Bit equality per class | Every operation's corpus on every Tier 1 target, under perturbations, gives one identity per class |
| KLN-O-CAS-1 | Integrity and codecs | Bit flips and truncation fail with `Corrupt` and heal from another tier; unknown codecs never decode |
| KLN-O-CAS-2 | Collection | Concurrent writers, leases and crashes lose no reachable object |
| KLN-O-CAS-3 | Encryption domains | No decryption or storage-name correlation across domains |
| KLN-O-CAS-4 | Hashing and deduplication | Throughput targets met; browser and native ids equal; 95% deduplication between Changes (target); renames re-chunk no geometry |
| KLN-O-PURGE-1 | Purge and retention locks | Purged bytes unrecoverable from every tier and backup; locked records refuse purge |
| KLN-O-REPL-1 | Replication | Fault-injected replication converges with no residency breach |
| KLN-O-GIT-1 | Git round trip | Export, re-import and rebuild keep every `EntityId` and `GeometryId` on every golden product |
| KLN-O-SPAN-1 | Span provenance | Instructions planted in merged comments, identifiers, part names, BOM text and embossed text return as `ExternalText`, also after Git, archive and federation round trips; endorsement refuses the span's author |
| KLN-O-MERGE-1 (held-out) | Merge | Seeded conflicts of every kind found; no silent wrong merge; 90% of reference-clean merges clean (target); a width change beside a new hole and GP4 edits to adjacent welded members merge clean; two fillets on one edge and order-breaking inserts conflict |
| KLN-O-DIFF-1 | Diffs | Identical Changes diff empty; deviation within its bound of a reference |
| KLN-O-LARGE-1 | Large assemblies | The 100,000-Instance repository benchmark meets its phase 4 target |
| KLN-O-XREF-1 | References | Rebuilding from `ingot.lock` reproduces every `ObjectId` |
| KLN-O-COLLAB-1 | Reconcile | Text to block tree to text is byte-identical under random edits; unparseable blocks keep kind and position |
| KLN-O-COLLAB-2 | Convergence, presence, locks | 50 partitioned peers converge; p95 keystroke-to-remote under 100 ms on one continent (target); locks never bypassed |
| KLN-O-COLLAB-3 | Offline rejoin | No Change lost; seeded conflicts found; fast-forward only without concurrent changes |
| KLN-O-PLM-1 | Guards, gate predicate | Unreleased children block release, naming every unmet guard; `Warning`-only failures do not block; uncovered conditional `Pass`es do |
| KLN-O-PLM-2 | Numbering, labels | Concurrent allocation yields no duplicates; labels follow the policy package |
| KLN-O-PLM-3 | Interchangeability | Seeded form-fit-function breaks all flagged |
| KLN-O-PLM-4 | Effectivity | Configured BOMs equal references at 1,000 random points; gaps and overlaps found |
| KLN-O-PLM-5 | Variants | Each valid configuration's 100% BOM equals brute force; a bolt circle's quantity follows its hole-count parameter |
| KLN-O-PLM-6 | BOM views | GP3's MBOM reconciles with matching quantities |
| KLN-O-PLM-7 | Where-used | The index equals full recomputation nightly |
| KLN-O-PLM-8 | Manufacturing changes | EBOM-touching MCOs rejected; a part change returns exactly its dependent programs, imported ones included, to `Prototype`; none leaves it without a first-article record |
| KLN-O-PLM-9 | Definition equivalence | A bit-level upgrade marks no Item modified, a 300 m hull included; a seeded out-of-tolerance change marks exactly its Item |
| KLN-O-PLM-10 | System of record | Releases round trip through a mock PLM without changing digests; an external approval alone never releases |
| KLN-O-PLM-11 | Parts policy | Unapproved parts fail unless a Waiver names them |
| KLN-O-CHG-1 | Approval subjects | Stale content cannot be approved; a rebase or CI re-run with an unchanged subject keeps approvals; `act.commit` refuses a recomputed mismatch |
| KLN-O-CHG-2 | Item definitions | Swapping a Software binary, Material version or document, or one attribute of each definitional class, voids an approval; a `#[was]` rename or non-definitional change does not |
| KLN-O-SIG-1 | Part 11 controls | Excised and transferred signatures fail; re-authentication required; exports verify offline; synced passkeys cannot sign |
| KLN-O-SIG-2 | Signature agility, FIPS mode | Dual-signed records verify under each algorithm and after re-timestamping; signing a year-old Change changes no `ChangeId` or tag; tenant LMS and non-approved FIPS algorithms refused |
| KLN-O-TRACE-1 | Traceability | The matrix equals the reference on GP1 to GP4 |
| KLN-O-COMPL-1 | Compliance | Seeded restricted substances all found; missing data never compliant |
| KLN-O-VULN-1 | Vulnerability where-used | A seeded vulnerable library traced to every affected serial |
| KLN-O-RELEASE-1 | Data release | Every exit path, shared branches and federation included, runs `release_data`; tainted or recent recipient changes never apply; scope or licence mismatches and a party listed the day before are refused |
| KLN-O-SHARE-1 (held-out) | Redaction | Planted strings, features and provenance ids never reach a package |
| KLN-O-SHARE-2 | Supplier packages, watermarks | Suppliers read nothing outside their packages; every recipient file traces to its release |
| KLN-O-SHARE-3 | Parametric quotas | Out-of-range or over-budget queries fail with `ShareQuotaExceeded` and are audited |
| KLN-O-POLICY-1 | Identity and authorization | Fuzzing against a reference model; Cedar analysis on every change; agents never sign, approve or release; listed changes need two people; forbidden break-glass actions refused |
| KLN-O-AUDIT-1 | Tamper evidence | Rewritten and forked logs detected by clients and witnesses; no tile holds labelled bytes |
| KLN-O-AUDIT-2 | Pseudonymity | After erasure names are unrecoverable while logs and signatures verify; held records keep names |
| KLN-O-DEPLOY-1 | Offline, browser ownership | Airplane-mode suite of every API method; two-tab edits with the owner closed lose no Change |
| KLN-O-DEPLOY-2 | Team server, on-premises | Install to first Proposal in 15 minutes on a KVM host and a VM without nested virtualization; a microVM-escape tabletop leaves signing keys unreachable |
| KLN-O-DEPLOY-3 | Cloud | Zone-loss chaos tests lose no acknowledged write |
| KLN-O-DEPLOY-4 | Air-gapped | Bundle round trip between two isolated sites |
| KLN-O-RESTORE-1 | Restore | The verifier finds every fault in seeded corrupt backups |
| KLN-O-API-1 | `api` behavior | Conformance suite shared with AGT |
| KLN-O-EVENT-1 | Events | Receiver outages cause no loss or reordering per repository |
| KLN-O-HW-1 | Evidence and safety | Spoofed, replayed and expired-calibration records rejected; Evaluations at one watermark agree while a record arrives; unmatched runner images cannot enrol; limit violations and missing risk assessments abort in simulation; no start reaches a device |

## Phasing

| Phase | KLN contribution to the gate |
| --- | --- |
| 0 | Kiln core with multi-output memo entries, cancellation, Aborts, the limit catalog, priority classes and closure hashes; local CAS; Kiln's corpus green in the determinism suite; deterministic simulation; Changes and transaction log on the desktop |
| 1 | GP1 and GP2 along contract 13.2's chain D (team server, microVM Proposal CI, approval page and release Acts, used in the dry run): progressive results, drag lane, overrides and budgets; `crucible:host`; merge and Proposals; two-person rules; labels, control authorizations and span provenance; Git export; minimal lifecycle, per-kind definitions and EBOM; policy allowances; signature records; `release_data` and audited local exports; events; lab Evidence records; browser engine ownership |
| 2 | GP3 and GP4: live documents; attested shared cache and External Op receipts; cloud workers; encryption domains; interference conflicts; change orders, MCOs, first-article records, Part 11 mode, dual signing; internal screening; traceability; MBOM and where-used; definition equivalence; connectors and parts policy; the hardware runner; partial clone; on-premises; restore and privacy |
| 3 | GP5: connectivity conflicts; effectivity; variants; computed interchangeability; compliance; vulnerability where-used; supplier packages, derived views and quotas; end-to-end mode with customer-hosted tiers; regulated cloud; air-gapped bundles; the assessment package |
| 4 | GP6: the 100,000-Instance repository and cloud-cell targets, beside contract 13.3's high-band row; evidence as Flux validation data; multi-region replication |
| 5 and later | Certification evidence packages for DO-178C and DO-254 programs from the traceability matrix; program-scale effectivity; federation at scale |

KLN phases none of contract 13.4's shared capabilities.

## Open questions

Round 3 closes every earlier question: hashing (D-KLN-46), sibling order and designed contact (D-KLN-21), revision rules (D-KLN-47), item numbers (D-KLN-45), assessment (D-KLN-49), end-to-end caching (D-KLN-48) and the definition tolerance (D-KLN-26). None stays open; these findings are declined or applied in part.

1. **R10-44, item numbers.** It conflicts with R9-53; numbers stay in source, because a local key adds a second identity and ING and MEC already type the number.
2. **R9-53 and R8-36, definition tolerance.** The floor is 10ρ (R10-39) with R8-36's topology test. R9-53's 2¹⁰ρ term is Anvil's growth cap (about 0.5 mm on a 300 m hull), which bounds enclosures, not upgrade noise; R8-36's 4ρ floor sits too close to that noise.
3. **R9-52, contact.** Condition 4 counts only positive-volume interference, as proposed; condition 5 keeps touching as a conflict unless designed contact explains it (R10-30), since an unexplained new contact with an edited face is a real interaction.
4. **R11-13, Asset endorsement.** As contract 17 revised it: merging the import Proposal endorses typed values, with no separate record.
5. **R11-18, external approvals.** Applied without a new Act name; the release record says "approved externally".
6. **R11-19 and R11-38, standing releases.** Shared-branch pushes and federation sync run the stage; D-KLN-41 lists AGT's `standing_release` (D-AGT-33).
7. **R9-47, error codes.** Events added; contract 7.6 now writes `label/write_down` (CCR-KLN-9).
8. **R2-06, round 2.** Calls do not become CRDT blocks; contract 5 names calls by name and occurrence, and ING's lint covers prepends (R9-36).
9. **R3-20, round 2.** Contract 7.8's attestation service replaces per-build signing keys.

## Contract change requests

- CCR-KLN-6 to CCR-KLN-8 (Evidence records without geometry, Item, merge verdict order): accepted in contract v5 (sections 2, 2 and 7.1 `repo`).
- CCR-KLN-9, error-code form: accepted with CCR-AGT-12 and CCR-ECO-11 in contract v6.1 (section 7.6).
- CCR-KLN-10, catalog parts in `ItemDefinition`: accepted in contract v6.1 (section 5, `ItemDefinition`).

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
- Git, merge strategies (`ort` and `recursive`): https://git-scm.com/docs/merge-strategies
- NIST, FIPS 140-3 transition effort: https://csrc.nist.gov/projects/fips-140-3-transition-effort
- NIST CMVP, certificate 5314 (AWS-LC 3 Cryptographic Module, static): https://csrc.nist.gov/projects/cryptographic-module-validation-program/certificate/5314
- NIST SP 800-38D, GCM and GMAC: https://csrc.nist.gov/pubs/sp/800/38/d/final
- NIST SP 800-56C Rev. 2, key-derivation methods: https://csrc.nist.gov/pubs/sp/800/56/c/r2/final
- RFC 5869, HKDF: https://www.rfc-editor.org/rfc/rfc5869.html
- Cao and Irani, "Cost-Aware WWW Proxy Caching Algorithms" (full paper, PDF): https://www.usenix.org/legacy/publications/library/proceedings/usits97/full_papers/cao/cao.pdf
- Bazel Remote Execution API v2, `remote_execution.proto`: https://github.com/bazelbuild/remote-apis/blob/main/build/bazel/remote/execution/v2/remote_execution.proto
- Firecracker, getting started: https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md
- International Trade Administration, Consolidated Screening List: https://www.trade.gov/consolidated-screening-list
- OMG, Requirements Interchange Format (ReqIF): https://www.omg.org/spec/ReqIF/
- ASME Y14.35, revision of engineering drawings and associated documents: https://www.asme.org/codes-standards/find-codes-standards/revision-of-engineering-drawings-and-associated-documents
- Siemens, "Introducing Teamcenter Product Configurator for variability management": https://blogs.sw.siemens.com/teamcenter/introducing-teamcenter-product-configurator-for-variability-management
- FDA, Quality Management System Regulation (QMSR): https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr
- Regulation (EU) 2024/2847, Cyber Resilience Act (EUR-Lex): https://eur-lex.europa.eu/eli/reg/2024/2847/oj/eng
