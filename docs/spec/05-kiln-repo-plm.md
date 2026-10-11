# Kiln, repository and PLM (KLN)

Kiln evaluates Ingot as a memoized graph keyed by content and pinned operation versions, so an edit recomputes only what it affects, with identical bits on every Tier 1 machine. The CAS stores everything under SHA-256 identities, and `repo` records each edit as an immutable Change that merges by syntax tree, feature, check and geometry. Lifecycle, identity, policy and audit records share that signed store and behave the same on a laptop, a team server, the cloud and an air-gapped site.

## Scope and terms

This tab owns evaluation semantics, the determinism policy at the level of operations, storage, versioning, collaboration, product lifecycle management (PLM), security, compliance and deployment. The Platform and performance tab (PLT) owns threads, executors, SIMD dispatch, the math library implementation and packaging; this tab states what it requires from them. The Ingot tab (ING) owns compilation; Anvil (ANV) and Flux (FLX) own operations and their behavior-versioning policies.

The tab introduces the terms below. Each is either a field of a contract type or a record that the contract implies; none replaces a contract type.

| Term | Meaning | Relation to contract types |
| --- | --- | --- |
| `ObjectId` | SHA-256 identity of a canonical object in the CAS | The "input hashes" in the `Op` cache key |
| `OpKey` | The cache key of one Op evaluation | Exactly the contract's `Op` cache key, refined in D-KLN-3 |
| Node | One memoized pure computation in Kiln's graph | An `Op` evaluation is one node kind; there is no separate "job" or "task" concept |
| Generation | Kiln's counter of input changes | Internal to Kiln; "revision" is reserved for PLM item revisions |
| Memo entry | A stored node result with its dependencies | A persistent memo entry maps an `OpKey` to an `ObjectId` |
| `Fidelity` | `Preview`, `Interactive` or `SignOff` | Kiln's demand levels. Anvil's `Preview` and `Exact` and Flux's interactive and sign-off modes map onto them (Progressive results) |
| `DeterminismGrade` | `Portable`, `ClassExact` or `Certified` | Declared per operation version; selects the `PlatformClass` in the key |
| Change | One immutable fine-grained edit with its resulting snapshot | Onshape's microversion; a described Change is what Git calls a commit |
| Item | The lifecycle identity of a Part, Assembly, document or catalog part | Carries the item number of a `Part` |
| Live document | The replicated CRDT state of one branch's packages during live editing (Collaboration section) | Checkpointed into Changes; distinct from an `api` session, which binds a principal, grant and budget (AGT tab) |
| Label | An integrity label and a data class, as the agents tab (AGT) defines them; data classes include `export_controlled` subclasses such as `itar` or `ear:9E610` | Attached to repositories, records, API responses and CAS objects |

## Kiln: incremental evaluation

### Graph model

Kiln evaluates a graph of input cells and derived nodes. Input cells hold values that the outside world sets: source files, the lockfile, package contents, `Material` records, catalog records, measured data from hardware checks and configuration points (variant selection, effectivity). Derived nodes are pure functions of the cells and nodes they read, and Kiln records those reads as they happen. Evaluation is demand-driven, as in Adapton: an input change only advances the generation, and nothing recomputes until a subscription demands a result.

| Node kind | Key | Value | Example |
| --- | --- | --- | --- |
| Front-end | module identity, Ingot compiler behavior version | IR and diagnostics | parse, resolve, type-check, lower (stages defined by ING) |
| Feature | feature identity, package closure hash, argument `ObjectId`s | `Part`, `Body`, `Field` or plain values, plus `HistoryRecord`s | one call of `bracket(width: 60mm)` |
| Op | `OpKey` | operation outputs with `ErrorBound` where applicable | one call of `anvil::blend@2` |
| Check | check node, subject `ObjectId`s, `Fidelity` | `CheckOutcome` | one `require` predicate |

Dependencies are dynamic: a feature may branch on a computed value, so Kiln cannot know every edge before running it. Within one feature body most Op calls are static, and the IR exposes them, so Kiln prefetches static dependencies in parallel and suspends only on data-dependent ones.

**Decision D-KLN-1:** Kiln uses a suspending scheduler with dynamic dependency recording, verifying traces in memory and constructive traces in the shared cache. *Why:* the build-systems taxonomy of Mokhov, Mitchell and Peyton Jones shows that dynamic (monadic) dependencies require a restarting or suspending scheduler, and that suspending scheduling with constructive traces (their proposed "Cloud Shake" cell) gives minimal rebuilds plus shareable results. *Rejected:* a topological scheduler (needs static dependencies, which Ingot control flow does not have); restarting scheduling as in Bazel (wastes work on restarts during interactive edits); deep constructive traces as in Nix and Buck (lose early cutoff on intermediate values).

### Keys and behavior versions

An `OpKey` is a SHA-256 digest over a deterministic CBOR record with the domain tag `crucible/opkey/1`:

| Field | Content |
| --- | --- |
| `op`, `v` | Operation id and the behavior version pinned in the design's lockfile, for example `anvil::blend` and `2` |
| `inputs` | Ordered `ObjectId`s of every input value |
| `params` | Canonical encoding of plain parameters, with units in SI base form |
| `impl` | For a Wasm component: the component's `ObjectId` and the runtime configuration version |
| `class` | `cpu-f64` for `Portable` operations and for `Certified` operations that run on the CPU; the class of the device for `ClassExact` operations, such as `wgpu-f32:<vendor>:<driver>` |
| `fidelity` | `Preview`, `Interactive` or `SignOff` |

Feature and check keys follow the same scheme. The lockfile has two parts: package pins and operation version pins. A feature key carries the package closure hash (the package defining the feature plus its resolved dependency closure) and the hash of the operation version pins, so a design that pins different versions never reuses another design's feature results.

The design's lockfile records which behavior version of each operation the design uses. Kiln dispatches every call to that version's implementation in the operation registry, and a new design pins the newest versions. Upgrading versions is an explicit Proposal that shows the geometric and metric diff, never a side effect of installing a new engine.

**Decision D-KLN-2:** The engine build identity is not part of any key; a behavior fingerprint makes that safe. Each operation version has a registered digest of its outputs over a conformance corpus, and CI fails when code changes the digest without a version bump. *Why:* keying on the build would invalidate every cache on every release; keying on behavior versions alone is unsafe unless version bumps are enforced. *Rejected:* build id in the key (no reuse across releases); trusting developers to bump versions (silent cache poisoning).

**Decision D-KLN-3:** Keys include the package closure of the code actually used, not the whole lockfile. *Why:* a whole-lockfile key means adding any package to a design invalidates every cached result and blocks sharing between designs that use the same std features. *Rejected:* the contract's literal "library lockfile" term; this tab raises it as a change request.

**Decision D-KLN-4:** A pinned operation version that the engine has retired is never substituted. Kiln returns `OpVersionRetired` with two fixes: evaluate on a compatibility worker that runs the archived, signed engine build that still implements it, or open an upgrade Proposal. *Why:* old designs must rebuild identically (contract section 4). *Rejected:* silent fallback to the newest version, which violates "explicit over magic".

### Memoization, verification and backdating

Each memo entry stores the value handle, the value's `ObjectId` once computed, `changed_at` and `verified_at` generations, the ordered list of dependencies read, the minimum durability of its inputs and a cost record. Kiln increments the generation once per batch of input changes: one CRDT transaction, one checkout or one configuration change.

Inputs carry a durability, as in Salsa: `High` for std, packages, Materials and catalog records; `Medium` for repository files not open in an editor; `Low` for open documents. Kiln tracks the last generation in which any input of each durability changed, so a node that reads only `High` inputs is revalidated in constant time after a keystroke.

Verification of node `q` at generation `G` follows Salsa's algorithm:

1. If `verified_at == G`, return the memo.
2. If no input with durability at or above the memo's minimum changed after `verified_at`, set `verified_at = G` and return.
3. Otherwise verify the recorded dependencies in recorded order. If none changed after `verified_at`, set `verified_at = G` and return.
4. Otherwise re-execute `q`, recording fresh dependencies.
5. If the new value equals the old one, keep `changed_at` (backdating) and set `verified_at = G`; otherwise set `changed_at = G`.

Backdating is what makes code-CAD edits cheap. Editing a comment re-parses the file, but the lowered IR is equal, so no feature re-executes. Changing a fillet whose edge a later cut removes re-executes the fillet, but the cut's output is equal, so everything downstream is reused.

**Decision D-KLN-5:** Early cutoff on the interactive path compares values directly; content hashing happens off that path. Values in memory carry a lazily computed `ObjectId`. Equality first compares `ObjectId`s when both exist, then buffer contents bitwise (so `-0.0` and `+0.0` differ and NaN equals itself), which is far cheaper than hashing a 100 MB mesh during a drag. Kiln consults the shared cache only when the operation's estimated cost exceeds the cost of computing input identities plus one lookup (default 200 ms, measured per operation). *Why:* the drag preview target is 100 ms, and hashing large Bodies inside it would consume the budget. *Rejected:* hashing every value eagerly (latency); never sharing cheap results (no loss, since recomputing them is cheaper than fetching).

[[DIAGRAM: Kiln evaluation path. Boxes: "Input cells (repo workspace, lockfile, Materials, catalog, measured data)" → "Generation bump" → "Red-green verification (memo entries)" → decision "valid?" → yes: "return value"; no: "estimated cost > threshold?" → yes: "compute OpKey" → "shared cache lookup (team or cloud CAS)" → hit: "fetch ObjectId" / miss: "schedule (local or cloud worker)"; no: "execute locally" → "compare with old value" → "backdate or mark changed" → "progressive result stream to UI and agents".]]

### Errors as values

Kiln separates two kinds of failure. A deterministic failure is a property of the inputs: a Boolean of coplanar faces that Anvil rejects, a `ResolveError`, a unit error, a solver that reports divergence. Kiln memoizes it like any other value, so a broken feature does not re-execute on every keystroke, and it flows downstream as a typed error with its fixes.

An environmental failure is a property of the run: out of memory, a crashed worker, a lost connection, an exhausted budget or a cancellation. Kiln never caches it. It retries environmental failures up to the policy limit (default two retries on a different worker), then reports `EvalError::Environment` with the cause.

**Decision D-KLN-6:** Deterministic errors are cached values; environmental errors are never cached. *Why:* caching deterministic errors keeps interactive editing fast while a feature is broken, and never caching environmental errors keeps a transient fault from poisoning the shared cache. *Rejected:* caching nothing that fails (slow when a design is mid-edit); caching every failure (one out-of-memory event would persist for every user).

### Scheduling and parallelism

Kiln runs nodes on the Platform tab's compute pools: an interactive pool and a background pool with operating-system priorities, and deterministic parallel combinators inside operations. Concurrent demands for one node share one execution. Every evaluation request carries one of the four priority classes that the agents tab defines, and Kiln maps each to a pool:

| Class | Demand source | Pool | Preemption |
| --- | --- | --- | --- |
| `interactive` | A person waiting: viewport, selection, drag preview, their own rebuild | Interactive | Never preempted |
| `agent` | Agent sessions | Background | Preempted by `interactive` at node boundaries |
| `ci` | Proposal CI, merge queue, release builds | Background | Preempted by `interactive` |
| `batch` | Explorations, benchmarks, prefetch, background sign-off audits | Background | Preemptible by all; resumes from cached nodes |

Inside a class, Kiln shares capacity among principals by dominant resource (CPU, GPU, memory), as the agents tab requires. A background node that an interactive node is waiting on is promoted to the interactive pool, or boosted if it has started.

A drag runs on a drag lane, as the UI tab requires: at most one coarse request in flight and one pending, with the latest value replacing the pending one. A newer value cancels an in-flight request only when that request has not yet produced its first `Preview` result, so a fast drag still shows motion.

Parallel execution never changes results. Nodes share no mutable state, each result depends only on its key, and Kiln merges collections such as diagnostics and check outcomes in a canonical order (source position, then error code), never in completion order.

Implicit cycles are errors. When a node demands a node already on its own active stack, Kiln returns `EvalError::Cycle` with the path of features and source spans. Iteration that needs a fixpoint (a mate solve, a coupled simulation) is expressed inside one operation or as an explicit bounded loop in Ingot, where the convergence criterion is visible.

### Cancellation

A node runs only while something demands it. Demand comes from subscriptions: a viewport, an agent's evaluation request, a CI run. When a new generation arrives, Kiln re-verifies the dependencies an in-flight node has already read; if they are still valid and the node is still demanded, it continues, otherwise Kiln cancels it.

Cancellation is cooperative. Kiln checks a cancellation token at every node boundary, native operations must poll it at least every 10 ms of CPU time, and GPU work is split into dispatches of at most 50 ms (target). Wasm components are interrupted by Wasmtime epoch interruption, which is not deterministic, but a cancelled node yields no result, so determinism is unaffected. Deterministic compute limits use Wasmtime fuel instead, since Wasmtime documents fuel with a fixed bound as the deterministic way to halt execution.

A cancelled node leaves no memo entry and no CAS write. Completed lower-fidelity results remain valid, because each fidelity is its own node.

### Memory management and eviction

Values in memory are immutable, reference-counted buffers. Large buffers (meshes, Field arrays, sparse matrices) are memory-mapped from the local CAS whenever they already exist there, so a warm start reads geometry without copying it.

Kiln keeps memo metadata after evicting a value. The dependency list, generations and `ObjectId` remain, so verification still works; if the value is demanded again, Kiln reloads it from the local CAS by `ObjectId`, or recomputes it if the CAS has also dropped it.

**Decision D-KLN-7:** Kiln evicts values by GreedyDual-Size, with cost equal to the cheaper of recomputing and reloading. Each value gets priority `H = L + cost / size`; Kiln evicts the lowest `H` and raises the floor `L` to it [formula from the paper's standard statement; the abstract page opened does not show it]. *Why:* Cao and Irani's GreedyDual-Size combines recency, cost and size with no tuning parameters, and CAD values vary in both size (bytes to gigabytes) and cost (microseconds to hours) by nine orders of magnitude. *Rejected:* plain LRU (evicts an hour-long solve to keep a thousand cheap sketches); manual pinning only (fragile).

Values on screen, values held by an open Proposal review and inputs of running nodes are pinned. The default memory budget is 50% of physical memory on desktops, 2 GiB in browsers and a configured quota on workers. Kiln writes a memo snapshot (dependency edges plus `ObjectId`s, not values) to the local CAS every 60 s and on exit, so a restart revalidates instead of recomputing.

### Progressive results

Every demanded output is computed at up to three fidelities, each a separate node with `fidelity` in its key:

| Fidelity | What it computes | Error statement |
| --- | --- | --- |
| `Preview` | Anvil `Preview` geometry (coarser tolerances, surrogates, GPU); no Flux solve unless the study declares a preview model | `ErrorBound` per Body |
| `Interactive` | Anvil `Exact` geometry; Flux interactive mode | Flux estimate with its calibrated safety factor |
| `SignOff` | Anvil `Exact` geometry; Flux sign-off mode | Flux sign-off estimators, guaranteed where proven |

Anvil's `Exact` fidelity serves both `Interactive` and `SignOff`, so exact geometry is one shared node; only Flux results and checks differ between those two levels. Kiln's `Fidelity` is distinct from the coverage tab's fidelity levels L0 to L3, which choose a model form and are ordinary inputs. Flux's interactive mode keeps its own outcome rule (a pass needs a margin of at least three times the error estimate, otherwise `Undecided`).

A subscription names a target, a fidelity ceiling and a priority. Kiln schedules `Preview` first for every demanded target, then `Interactive`, then `SignOff` when the ceiling allows. It streams `ResultEvent`s carrying the generation, the fidelity, the value handle, the error statement and a stream status (`Partial`, `Final` or `Superseded`). The UI derives its display status (`Coarse`, `Exact`, `Stale`, `Failed`) from these fields.

The UI never shows a torn frame. A published frame contains results from exactly one generation, each labelled with its fidelity; results from an older generation are shown only when explicitly marked stale.

Checks evaluated on `Preview` or `Interactive` results are reported as `Provisional`. Only results at the fidelity a check declares (default `SignOff`) count toward CI, Proposals and release gates.

**Decision D-KLN-8:** Progressive refinement is a set of independent nodes keyed by fidelity, not a stateful refinement process. *Why:* each tier is then cacheable, cancellable and shareable on its own, and a coarse result can never be mistaken for a sign-off result. *Rejected:* in-place refinement of one value (not cacheable, and invisible to the key).

### Distributed and remote evaluation

Kiln runs the same engine on the desktop, in the browser, on a team server and on cloud workers. A worker advertises its `PlatformClass`, engine build, available operation versions, GPU backends and price. Workers run as Linux containers on x86-64 or ARM64, with optional CUDA or ROCm (contract section 9).

For each costly node, Kiln compares the estimated local time with the remote estimate: upload of missing inputs, queue wait, remote execution and download of the outputs actually needed. Inputs usually already live in the shared CAS, so offloading a solve uploads only small changed objects. Remote outputs stay remote until something local needs their bytes; the viewport fetches tessellations, not B-rep or solver state.

Placement respects labels. A node whose inputs carry a residency or export-control label runs only on workers whose region and operator attributes satisfy it, and Kiln reports `ResidencyDenied` rather than running it elsewhere.

Shared memo entries are signed result attestations: (`OpKey`, output `ObjectId`, worker identity, engine build digest, cost, time). Nix's content-addressed derivation RFC makes the same observation: a content-addressed path verifies itself, but the mapping from a build recipe to its output does not, so that mapping must be signed. The trust policy names which signers a client accepts. Attestations live in the encryption domain of their inputs (CAS section), so a lookup never crosses tenants or label scopes; values whose inputs are all public (std, public packages, public catalog parts) live in one global public domain that every tenant shares.

**Decision D-KLN-9:** Only trusted builders write the shared result cache: CI runners and the organization's workers. Developer machines and agents read it and write to their own namespace. *Why:* a forged attestation would silently corrupt every downstream design; restricting writers bounds that risk to infrastructure the organization controls. *Rejected:* any authenticated user writes (one compromised laptop poisons the team); no sharing of attestations (loses most of the benefit of a team cache).

Kiln continuously re-executes 1% of shared cache hits (default, configurable) on an independent worker of the same `PlatformClass`. A mismatch quarantines the attestation, opens a determinism incident and notifies the operation's owner.

The remote protocol is Kiln's own: an action here is an in-process call that takes microseconds to seconds, and the Bazel Remote Execution API's model of command lines over materialized input trees adds overhead that such calls cannot absorb. Kiln borrows that API's split between content-addressed storage and a shared cache of action results, and provides an adapter so an existing Remote Execution API v2 server can serve as a storage tier [unverified: adapter fit per server].

### Cost accounting

Every node records CPU time, GPU time, peak memory, CAS bytes read and written, network bytes and, for remote work, the deployment's price. A cache hit records the fetch cost and the cost avoided.

Every evaluation request carries a `Budget`, the type the agents tab defines (money, core seconds, GPU seconds, wall clock, evaluation count), carved from the requester's budget hierarchy. Before scheduling remote or costly work, Kiln estimates its cost from a per-operation cost model and reserves budget; when the estimate exceeds what remains, it returns `EvalError::BudgetExceeded` with the estimate and cheaper options (a lower fidelity, a coarser discretization, or local execution). Exhausting a budget mid-run is an environmental failure and is never cached.

Per-operation cost models are linear regressions on input sizes, fitted from measurements and stored as versioned CAS objects. Admission control belongs to `api`: Kiln returns the estimate, `api` reserves it, and metering charges actual usage as nodes finish (agents tab). Agents therefore see estimates before anything runs (the contract's cost caps). Costs are attributed to the principal, repository, branch and Proposal that demanded the work.

### Kiln capability catalog

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Memoized evaluation with backdating | `Kiln::demand(EvalRequest) -> ResultStream` | Typed `EvalError`; deterministic errors memoized | `oracles/kiln/minimality`: re-executed set equals the reference set on 500 scripted edits | 0 |
| Durability levels | inputs tagged `High`, `Medium`, `Low` | none | keystroke on an open file triggers zero re-verification of std nodes | 0 |
| Cooperative cancellation | `CancelToken` polled every 10 ms | cancelled nodes leave no trace | `oracles/kiln/cancel`: random cancellation of 10,000 runs; final state equals a clean run | 0 |
| GreedyDual-Size eviction | memory budget per process | reload or recompute on demand | eviction under a 256 MiB budget never changes results; rebuild time within 2x of unbounded | 1 |
| Progressive results | `ResultEvent` stream, no torn frames | stale frames marked | UI harness asserts generation consistency per frame | 1 |
| Shared result cache | signed attestations, trust policy | unsigned or untrusted entries ignored | forged-attestation test rejected; 1% spot re-execution | 1 |
| Remote evaluation | worker advertisement, cost-based placement | retry on a second worker, then local | identical `ObjectId`s from local and remote runs on the golden products | 2 |
| Budgets | `Budget` per request | `BudgetExceeded` with options | budget never exceeded by more than one node's estimate error | 1 |

## Determinism policy

Principle 4 promises identical outputs per `PlatformClass` and agreement within declared tolerance across classes. This section names every source of nondeterminism, its control, and how the control is verified. It binds every operation, Wasm component and Kiln itself.

### Grades and platform classes

Each operation version declares a `DeterminismGrade`, which selects the `PlatformClass` that enters its `OpKey`. The Platform tab owns the `PlatformClass` type and its mechanisms; this tab owns the policy, meaning which grade each kind of result needs and where each class is accepted. The class names below are the ones Flux proposes, and the Platform tab fixes the final list.

| Grade | Meaning | Key class | Shareable across |
| --- | --- | --- | --- |
| `Portable` | Bit-identical on every Tier 1 CPU target | `cpu-f64` | every Tier 1 CPU target, browsers and cloud workers included |
| `ClassExact` | Bit-identical within one device class, and within declared tolerance of the `Portable` CPU path | The device's class, such as `wgpu-f32:<vendor>:<driver>`, `cuda-f64` or `rocm-f64` | that class only |
| `Certified` | Output independent of every nondeterministic intermediate: the GPU only filters candidates and canonical CPU code makes every result-affecting decision, or the answer is exact | `cpu-f64` | as `Portable`, even when a GPU assisted |

`Portable` is the default and the requirement for std features and for the reference results of oracles. `ClassExact` serves GPU sign-off solves and interactive GPU results, at the cost of cache sharing. `Certified` needs an oracle showing that the output is identical with and without the assisting device. A target outside Tier 1 joins `cpu-f64` only after it passes the determinism suite; until then its results carry `PlatformClass::Unverified` and never enter the shared cache, as the Platform tab specifies.

| Result kind | Grade required | Accepted for release gates |
| --- | --- | --- |
| Geometry (Anvil `Exact`) | `Portable` or `Certified` | Yes |
| Flux sign-off results | `Portable`, or `ClassExact` when the repository's release policy names that class | Yes, on the recorded class |
| Flux interactive results | Any grade | No (never usable for release) |
| Checks | The grade of their inputs | Only at the check's declared fidelity |
| Display tessellations and renders | Any grade | Not applicable |

| `PlatformClass` (proposed with Flux) | Members | Status |
| --- | --- | --- |
| `cpu-f64` | Every Tier 1 CPU target: Windows 11 x86-64 and ARM64, macOS on Apple silicon, Linux x86-64 and ARM64, browsers on wasm32, Linux server containers | Shared by every cache tier |
| `wgpu-f32:<vendor>:<driver line>` | One GPU vendor and driver major version through wgpu; widened when the determinism suite proves more members identical | Shared within the class |
| `cuda-f64`, `rocm-f64` | One vendor's accelerators through CubeCL | Shared within the class |
| `PlatformClass::Unverified` | Any target that has not passed the determinism suite, including Tier 3 | Never enters a shared cache |

**Decision D-KLN-10:** `Portable` means bit-identical across every Tier 1 CPU target, browsers included, and is the only grade for geometry and for oracle reference results. *Why:* a cache shared by Windows, macOS, Linux, browsers and cloud workers works only if their results are the same bits, and the founder requires identical features everywhere; Flux reaches the same conclusion for its `cpu-f64` class. *Rejected:* one class per operating system and architecture (fragments the cache about eightfold and turns every cross-platform review into a tolerance argument).

### Sources of nondeterminism and their controls

| Source | Effect | Control | Verified by |
| --- | --- | --- | --- |
| Basic floating-point operations | None on Tier 1: Rust's `+ - * / sqrt` and `mul_add` follow IEEE 754-2008 with round-to-nearest-even (RFC 3514) | No 32-bit x86 target (x87 excess precision); no alternative rounding modes | Determinism suite |
| Fused multiply-add | Implicit contraction would change results by target | No implicit contraction (Rust does not contract `a*b + c`). Explicit `mul_add` is correctly rounded on every target, but costly where hardware lacks FMA (x86-64-v2 and Wasm), so its use in `Portable` code is per operation, following the Platform tab's rule; Flux kernels use no FMA on CPU and WGSL targets | Lint plus suite on targets with and without hardware FMA |
| Elementary functions | Rust documents the precision of `sin`, `exp`, `powf` and others as "non-deterministic" across platform and Rust version | All `Portable` operations call Crucible's correctly rounded math library (D-KLN-11) | Differential test against an arbitrary-precision reference on hard cases |
| NaN payloads and signs | Rust and Wasm leave NaN bit patterns nondeterministic | `Portable` operations never hash, bit-cast or `total_cmp`-order a value that may be NaN; operation boundaries canonicalize NaN or return a typed `NumericError`; the CAS encodes one canonical NaN; Wasmtime runs with Cranelift NaN canonicalization, and on browser engines, which have no such switch, Crucible's Wasm component loader inserts the same canonicalization | Fuzzing with injected NaNs |
| SIMD width | Wider vectors change reduction order | Element-wise kernels are width-independent by construction; reductions use a canonical order defined by data indices, not lanes (D-KLN-13) | Suite run with forced dispatch levels: scalar, SSE4.2, AVX2, AVX-512, NEON, SVE, Wasm SIMD128 |
| Hardware-specific SIMD semantics | `min`/`max` with NaN or signed zeros, approximate reciprocals and Wasm relaxed SIMD differ by host | Platform SIMD layer exposes only operations with one defined semantics; approximate-reciprocal instructions are banned in `Portable` code; the registry rejects `Portable` Wasm components that contain relaxed SIMD instructions, since browsers choose their behavior per host; Wasmtime also runs with `relaxed_simd_deterministic` | Lint on intrinsics; suite |
| Subnormals | Flush-to-zero modes change results | Floating-point control state stays at the IEEE default; the platform layer asserts it at thread start and at operation boundaries in verification builds; native libraries that alter it are not admitted | Control-register assertion in CI |
| Threading | Completion order changes reductions and greedy decisions | Partition work by data size into a fixed number of blocks, independent of thread count; merge in index order; decisions such as mesh refinement order follow data priorities, never completion order | Suite run with 1, 2, 7 and all threads |
| GPU arithmetic | WGSL lets an implementation reassociate, fuse when "at least as accurate", flush subnormals and ignore the sign of zero; float atomics add run-to-run variation | GPU floating-point results are `ClassExact` or feed a `Certified` decision (D-KLN-12); no float atomics in deterministic kernels; integer-limb exact reductions (Flux) | GPU suite per device class |
| Hash-map ordering | Randomly seeded maps iterate in a different order per process | Evaluation crates use insertion-ordered or sorted maps, with one fixed-key, target-independent hasher from the platform layer; `RandomState` is banned there by lint | Suite run with randomized seeds for any remaining std maps |
| Allocators and addresses | Pointer order differs per run | No ordering or hashing by address in evaluation crates; arena ids are assigned in deterministic order | Suite with an address-randomizing allocator |
| Library and compiler versions | A dependency upgrade can change results | Behavior fingerprints per operation version (D-KLN-2); `Cargo.lock` pinned; the math library is versioned with the engine and, being correctly rounded, cannot change results | Fingerprint check on every commit |
| Clocks, randomness and environment | Time, entropy, locale and environment variables leak into results | The evaluation sandbox exposes none of them; randomness comes from a counter-based generator (Philox, Random123) keyed by the `OpKey` and a stream number; deterministic limits use iteration counts or Wasmtime fuel, never wall time | Sandbox test that probes every ambient source |
| Integer overflow | Debug builds panic and release builds wrap | Evaluation crates enable overflow checks in every profile or use explicit checked and wrapping arithmetic | Build-profile matrix in CI |
| Stack depth and memory size | Recursion limits and memory-adaptive strategies vary by host | Operations use explicit stacks with one fixed depth limit returning a typed error; a strategy chosen by available memory must not change results | Suite under 256 MiB and 64 GiB budgets |
| Text and paths | Unicode normalization, line endings and directory order differ by OS | Canonical objects store NFC text with LF line endings; directory listings are sorted by normalized bytes in the platform layer | Cross-OS checkout test |

**Decision D-KLN-11:** Every `Portable` operation computes elementary functions with a correctly rounded math library, ported from or equivalent to CORE-MATH, owned by the Platform tab. *Why:* a correctly rounded function has exactly one right answer, so results cannot differ between targets, compilers or library versions; Rust's own functions are documented as non-deterministic, and CORE-MATH is MIT-licensed with per-function correctness proofs. *Rejected:* one pinned non-correctly-rounded libm compiled for every target (deterministic, but each bug fix changes results and forces behavior version bumps); the host libm (differs by OS).

**Decision D-KLN-12:** GPU floating-point results are `ClassExact` on their device class, or they feed a `Certified` computation whose output is independent of them. *Why:* WGSL states "An implementation may reassociate operations" and may fuse or flush subnormals, so no shader author can force identical bits across drivers. *Rejected:* claiming cross-vendor GPU determinism (false); banning GPUs from sign-off work (wastes the hardware that makes large solves practical).

A `ClassExact` result is reproducible bit for bit on its recorded class and agrees with the `Portable` CPU path within the tolerance Flux declares per operation, which Flux's cross-platform oracle enforces. When a request does not pin a class, Kiln prefers the class of an existing cached result, then the local class; CI pins one class per repository, so its reports are stable. A release records the class of every result it cites. Anvil's GPU sampling with certified CPU refinement for surface-surface intersection qualifies as `Certified` only when its oracle shows that the refined output does not depend on which GPU produced the samples.

**Decision D-KLN-13:** Reductions in `Portable` code use a canonical order: fixed blocks by element index, combined by a fixed pairwise tree (the Platform tab's `det_sum` and `det_reduce`). Where partitioning varies between runs (distributed solves on different node counts) or scatter patterns make a fixed order costly, operations use binned reproducible summation in the style of ReproBLAS (`exact_sum`). *Why:* a fixed tree costs nothing in arithmetic and only constrains partitioning. Binned summation is order-independent, which permits dynamic load balancing; ReproBLAS reports about 9n floating-point operations per sum of n values and a dot product about 4x slower than an optimized non-reproducible one on one core. *Rejected:* atomics or completion-order reduction (nondeterministic); always using binned summation (pays its cost where a fixed tree is free).

### Requirements on the Platform tab

The Platform tab's draft already provides most of these mechanisms: priority pools, deterministic combinators (`det_sum`, `det_reduce`, `exact_sum`), the `detmath` correctly rounded library, ISA dispatch with a forcing switch, and the `PlatformClass` type. This tab relies on them as follows.

1. Compute pools whose scheduling never affects results, plus a deterministic simulation mode that permutes task order from a seed.
2. Deterministic combinators for every result-affecting parallel loop and reduction; `exact_sum` for reductions whose partitioning varies between runs.
3. `detmath` for binary32 and binary64 on every Tier 1 target, Wasm included.
4. Floating-point control-state assertions, a fixed-key target-independent hasher, and Philox counter-based random numbers.
5. A crypto provider abstraction with a FIPS 140-3 mode on servers and desktops.
6. Wasmtime configured with NaN canonicalization, deterministic relaxed SIMD, fuel for limits and epochs for cancellation; for browser engines, a Wasm component loader that inserts NaN canonicalization and fuel counting, so limits and results match native runs.
7. A stated rule for `mul_add` in `Portable` code on targets without hardware FMA (x86-64-v2 and Wasm, whose core instruction set has no scalar FMA [unverified]), with its cost.

### Continuous verification

Determinism is tested at four levels. Every commit runs the determinism suite: each operation version evaluates its corpus on every Tier 1 target, browsers included through headless runners, and all output `ObjectId`s must match within each class. Each commit also runs the perturbation matrix: thread counts, forced SIMD levels, an address-randomizing allocator, randomized hash seeds, eviction under tight budgets, and random cancellation with restart.

Kiln, the sync protocol, CAS garbage collection and the repository server run under deterministic simulation testing in the style of FoundationDB, which reports running "tens of thousands of simulations every night". One seed fixes the task order, simulated time, network delivery, disk faults and crashes, so any failure replays exactly. Phase 0 runs 1,000 simulated hours per night, rising to 10,000 by phase 2 (targets).

In production, spot re-execution of shared cache hits (section on distributed evaluation) and nightly rebuilds of every golden product's release on every Tier 1 target catch what the suites miss. A mismatch is a severity-1 determinism incident: the attestation is quarantined, the operation version is flagged, and the golden-product gate fails until the owner resolves it.

## The CAS

### Object model

Every object is an immutable value with a type tag, a canonical encoding and an `ObjectId`. There are four object kinds.

| Kind | Content | Typical size |
| --- | --- | --- |
| `Blob` | Opaque bytes: an imported STEP file, an image, a Wasm component | bytes to gigabytes |
| `Record` | A typed deterministic-CBOR value: a `Change`, a source tree, a `Material`, a signature, a result attestation | under 64 KiB |
| `Segmented` | A large typed array (mesh, `Field` values, sparse matrix) stored as keyed segments | megabytes to terabytes |
| `Index` | An interior node listing child `ObjectId`s with lengths and keys, for large Blobs and Segmented values | about 16 KiB |

Records use the core deterministic encoding of RFC 8949 section 4.2.1: preferred (shortest) serialization of integers and floats, definite lengths, and map keys sorted bytewise by their encodings. Crucible adds two rules: every NaN encodes as one canonical quiet NaN, and text is NFC. Large numeric arrays are never CBOR floats; they live in Segmented values as little-endian typed arrays.

An `ObjectId` is `SHA-256(domain tag ‖ type tag ‖ canonical bytes)`, prefixed with a one-byte algorithm code. Identity is computed on the uncompressed, unencrypted canonical form, so tiers may recompress or re-encrypt freely without changing it. The identity of a large value is the identity of its root `Index` node; chunking parameters are part of the type tag, so a chunking change is a versioned format migration, never a silent identity change.

Identity is sound but not complete. Equal `ObjectId`s imply equal values; two meshes that differ only in vertex order have different `ObjectId`s. Anvil and Flux therefore emit canonical forms (Interfaces section) so that early cutoff fires for equal geometry.

### Hashing

**Decision D-KLN-14:** The CAS identity hash is SHA-256, with a one-byte algorithm code reserved for migration. *Why:* SHA-256 is approved under FIPS 180-4, which matters to defense and medical customers. It is the digest of RFC 6962 transparency logs, C2SP tiles and Git's SHA-256 object format, so Crucible interoperates without translation tables. Most Tier 1 CPUs also have SHA-256 instructions [unverified for every Tier 1 CPU]. Git's transition document shows the cost of a hash without an agility field. *Rejected:* BLAKE3 (faster, tree-parallel and verifiable while streaming, but not NIST-approved, and Crucible gets the parallelism anyway by hashing chunks independently); SHA-3 (slower in software, no Tier 1 hardware support [unverified]).

BLAKE3's speed advantage is real: its authors describe `b3sum` as "an order of magnitude faster" than `sha256sum`. Crucible recovers most of it by design: chunks hash in parallel, identities of large values are computed lazily off the interactive path (D-KLN-5), and an `Index` node makes a large value verifiable chunk by chunk, as Bao does for BLAKE3. Throughput target: hashing a 1 GiB mesh in under 150 ms on the reference laptop (contract section 7).

### Chunking

Large values are split so that a local edit changes few chunks, and so that the same content splits the same way regardless of edit history.

**Decision D-KLN-15:** Chunking is structure-aware first and byte-level second. Segmented values split into typed segments keyed by provenance or space, and segments group into chunks by a content-defined rule over their keys, as in a prolly tree; opaque Blobs use FastCDC with normalized chunking. *Why:* byte-level chunking of a mesh shifts every boundary when an operation renumbers vertices, while provenance keys stay stable across edits; Dolt's prolly trees show that key-defined boundaries make the tree independent of insertion order, so diffs cost time proportional to the change. FastCDC is about 10x faster than the best open-source Rabin-based chunker with a nearly equal deduplication ratio. *Rejected:* fixed-size chunks (one insertion shifts every chunk); Rabin fingerprints (slower for the same ratio). Gregoriadis and colleagues found no impartial comparison of chunking algorithms before their 2024 study, so phase 1 benchmarks FastCDC against the alternatives they evaluate on Crucible's own data before the format freezes.

| Value | Segment key | Segment content |
| --- | --- | --- |
| Tessellated B-rep | Face `EntityId` | Vertices, normals and triangles of that face |
| Mesh (Manifold-style) | Morton code of a spatial cell | A cluster of up to 4,096 triangles with their vertices |
| `Field` nodal or quadrature values | Flux virtual partition | Canonical little-endian values of that partition, in 1 MiB chunks as the Flux tab specifies |
| Sparse matrix | Row block | Compressed rows |
| Opaque Blob | none | FastCDC: minimum 16 KiB, average 64 KiB, maximum 256 KiB |

For key-chunked values, a chunk boundary falls after a segment whose key hash is below a threshold, giving chunks of about 64 KiB; Field arrays keep Flux's partition-aligned chunks, which are already stable under local edits because partitions are a function of problem size. `Index` nodes group up to 512 children and are themselves grouped by the same rule.

Anvil and Flux own canonical forms. Kiln requires that a canonical Body or Field order its data deterministically by `EntityId` or by spatial key, never by allocation or completion order (Interfaces section).

### Compression

**Decision D-KLN-16:** Each stored chunk names its codec, and tiers may recompress without changing identity. Field arrays use Flux's byte shuffling plus zstd, with pcodec as a measured alternative for numeric columns; other chunks use zstd at level 3 in hot tiers and level 19 in the archive tier; display meshes on the wire use meshoptimizer's vertex codec. *Why:* per-chunk codec names let Crucible adopt a better codec later without a format break. pcodec is a lossless codec for numeric sequences whose authors chart better compression than zstd, so phase 1 benchmarks decide whether it replaces shuffling plus zstd for Fields. meshoptimizer's vertex codec is lossless and decodes at 3 to 6 GB/s. Its index codec may rotate triangles, so the CAS does not use it for canonical data. *Rejected:* one codec for everything (gives up the numeric gains); lossy quantization in storage (changes identity).

A reader that does not know a chunk's codec fails with `CasError::UnknownCodec`, never by guessing. Every codec in use has a decoder in every Tier 1 build, the browser included.

### Encryption at rest

| Deployment | Mechanism | Key holder |
| --- | --- | --- |
| Desktop | Operating-system disk encryption, plus CAS encryption for labelled repositories | OS keystore (TPM, Secure Enclave, Secret Service); a non-extractable WebCrypto key in browsers |
| Team server, cloud, on-premises | Envelope encryption per encryption domain | Data keys wrapped by a key in a KMS or HSM; customer-managed keys optional |
| End-to-end mode | Client-side encryption; servers store ciphertext only | The customer's key service inside its own security boundary |

An encryption domain is one tenant and one label scope. Within a domain, the key for an object is `HKDF-SHA-256(domain key, ObjectId)`, and each stored chunk is sealed with AES-256-GCM under that key with a random 96-bit nonce kept beside the ciphertext. Deduplication uses the storage name, not the ciphertext, so randomized encryption costs nothing, and recompressing an object never reuses a nonce. The storage name is `HMAC-SHA-256(domain key, ObjectId)`, so a storage operator cannot correlate objects across domains. In encrypted domains the sync protocol addresses objects by storage name, so plaintext `ObjectId`s never leave the domain's principals.

**Decision D-KLN-17:** Deduplication happens only within an encryption domain, using keys derived from a domain secret. *Why:* plain convergent encryption lets anyone confirm a guessed file; DupLESS shows the remedy is deriving keys through a secret held by the authorized side. Here only principals already authorized in the domain hold the secret. AES-GCM and HKDF are FIPS-approved [unverified: NIST SP 800-38D and SP 800-56C not opened], and a per-object key bounds the data under any one key to copies of one object. *Rejected:* global deduplication across tenants (confirmation attacks leak which designs exist); random per-write keys (no deduplication at all).

Deleting a domain key destroys every object of that domain at once (crypto-shredding), which is how a contaminated label scope is purged.

### Garbage collection

Source history is never collected; derived values are cache. The roots are refs, the transaction log, pinned releases (whose cited derived values a release keeps for inspection without recomputation), open Proposals, legal holds and in-flight uploads.

1. Writers upload objects before they update a ref, and a ref update succeeds only when the object closure is present (server-side check).
2. A writer that deduplicates against an existing object takes a 24-hour reference lease on it in the metadata store, closing the race where collection deletes an object that a new Change is about to reference.
3. The collector marks from the roots in a consistent snapshot, then sweeps unmarked, unleased objects older than the grace period (default 48 h, longer than any lease).
4. Derived values outside the roots are evicted by GreedyDual-Size (D-KLN-7) against a storage budget.

**Decision D-KLN-18:** Removing source history requires a purge: a signed, audited record listing the removed `ObjectId`s and the authority. History verification treats purged objects as known-missing, so the hash chain stays intact. *Why:* export-control spills and court orders require real deletion, and Part 11 requires that changes never obscure previously recorded information; a purge record satisfies both. *Rejected:* history rewriting (breaks every signature downstream); no deletion at all (cannot remediate a spill).

### Tiers and replication

| Tier | Store | Contents | Eviction |
| --- | --- | --- | --- |
| 0 | Process memory | Kiln values | GreedyDual-Size |
| 1 | Local disk: 64 MiB append-only pack files with an index, memory-mapped; browsers use the Origin Private File System | Working set, unpushed Changes | Budget (default 20% of free disk); unpushed Changes never evicted |
| 2 | Team server or regional cloud: object storage (S3-compatible, Azure Blob, GCS or a file system) plus a transactional metadata store | All source, shared derived values, attestations | Collector plus budget |
| 3 | Archive object storage | Release snapshots and their cited results | Retention policy only |

Refs and the transaction log live in the metadata store: SQLite on desktops and single-node team servers, PostgreSQL on larger team servers, and FoundationDB in the cloud. Ref updates are compare-and-swap transactions; on bare object storage they use conditional writes (`If-Match` on the ETag), which S3 documents as failing with 412 when a concurrent writer wins.

Cloud regions keep three synchronous copies of metadata across zones and replicate objects asynchronously to a second region of the same residency zone. Label-scoped repositories replicate only within the regions their residency policy allows. Anti-entropy between tiers uses range-based set reconciliation over sorted `ObjectId`s, which skips every range whose fingerprints match, so work tracks the difference rather than the store [unverified: the abstract opened states no complexity bound].

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Put and get by `ObjectId` | `CasStore::put`, `get`, `has_many` | Hash mismatch on read is `CasError::Corrupt`; fetch from another tier and quarantine the bad copy | Bit-flip injection on every tier | 0 |
| Structure-aware chunking | Segment keys from Anvil and Flux | Unkeyed values fall back to FastCDC, with a warning | Deduplication of 95% or more between successive golden-product Changes (target) | 1 |
| Encryption domains | Domain keys in KMS | Missing key is `CasError::KeyUnavailable`, never plaintext | Ciphertext of one domain never decrypts in another | 1 |
| Collection | Mark, lease, sweep | Collector stops on any inconsistency; never deletes on doubt | Deterministic simulation with concurrent writers and crashes: zero reachable objects lost | 1 |
| Purge | Signed purge record | Requires two administrators | Purged bytes unrecoverable from every tier and backup after the retention window | 2 |
| Tier replication | Asynchronous, residency-aware | Lag alarms; residency violations blocked at write | Fault-injected replication: no residency breach, convergence after partition | 2 |

## `repo`

### Data model

A design repository is a set of CAS objects plus a ref store. Every object below is a `Record` in the CAS.

| Object | Content | Identity |
| --- | --- | --- |
| `Change` | Parents, tree, author, `on_behalf_of` (for agents), live document, hybrid logical clock time, optional description, conflict records, signature. Time and authorship are history metadata that evaluation never reads | `ChangeId` = its `ObjectId` |
| `Tree` | Prolly-tree map from normalized path to file object, plus the lockfile `crucible.lock` | `ObjectId` |
| `SourceFile` | Canonical Ingot text plus a block map: `BlockId` to byte span; above 64 KiB a Segmented value keyed by top-level block, so a Change stores only the blocks it altered | `ObjectId` |
| `Tag` | Name, target `ChangeId`, tagger, message; release tags add a release record and signatures | `ObjectId` |
| `RefTransaction` | Previous transaction ids, the resulting view of all refs, the principal, the API call | `ObjectId` |
| Lifecycle records | Items, revisions, change orders, signatures, compliance evidence (PLM section) | `ObjectId` |

**Decision D-KLN-19:** Every committed edit becomes an immutable `Change`, as Onshape does with microversions. A Change is created per completed GUI action, per agent `edit.apply` call, after 2 s without typing, at least every 60 s during continuous editing, and whenever something references the current state (a comment, a Proposal update, a CI run, a share link). A description turns a Change into a reviewable step; tags name Changes. *Why:* fine-grained history lets anyone inspect, diff or branch from any state without a manual commit step, and Onshape shows the model works for CAD. *Rejected:* explicit commits only (history loses intermediate states that reviewers and agents need); one Change per keystroke (millions of objects with no meaning; the live document keeps keystroke-level edits for undo).

Refs are branch heads (`branches/<name>`), tags (`tags/<name>`, immutable once created), Proposal heads (`proposals/<id>`) and agent branches (`agents/<agent>/<task>`). A branch's head is its latest Change; the branch's live document (Collaboration section) produces new Changes on it.

**Decision D-KLN-20:** Ref updates are recorded in a transaction log, as Jujutsu records its operation log. Each `RefTransaction` names its predecessors and the full resulting view of refs. Concurrent transactions, such as two offline devices moving one branch, merge by a three-way merge of views, and a ref moved two ways becomes a conflicted ref that the user resolves. *Why:* Jujutsu shows that an operation log gives lock-free concurrency and safe sync of clones; because every transaction records a full view of refs, undoing any repository action is a new transaction that restores an earlier view, and the log doubles as the repository's audit trail. *Rejected:* Git-style reflogs (per-clone, not merged, not auditable); server locks (break offline work).

On a server, ref updates are compare-and-swap transactions in the metadata store, so the server's log is linear; offline clients keep their own log and merge on sync.

### Storage format

Locally, objects live in append-only pack files of up to 64 MiB with a sorted `ObjectId` index, plus a write-ahead pack for recent objects. A repository is self-describing: a header records the format version, the hash algorithm code and the canonical-encoding version. Git compatibility is an export, not the storage format: `crucible export git` writes Ingot text and lockfiles to a Git repository, so no design is trapped. Derived values live in the CAS, never in source history.

### Branches and Proposals

A branch costs one ref. A Proposal is a branch plus a rationale record plus a CI report (contract section 2). Opening a Proposal fixes its base; CI evaluates its head and the would-be merge result, and the review shows the diffs below. Merging creates a merge Change with two parents. Protected branches merge through a merge queue: CI evaluates each queued Proposal on top of the queue head, so a protected branch never holds an untested combination. Agents push only to `agents/*` refs and open Proposals; the server rejects any agent update to another ref (Security section).

### Merge

A merge is clean only when five conditions hold. The merge driver checks them in order and records every failure as a typed conflict.

1. **Structural source merge.** The driver merges each Ingot file three ways over its block tree (Collaboration section). Blocks are matched by `BlockId`; blocks without ids, from files edited outside Crucible, are matched by the GumTree algorithm as in Mergiraf. Child order is merged by Parent-Child-Successor triples, as in Spork and Mergiraf, and lists the Ingot grammar declares order-insensitive (imports, named arguments, struct fields) merge as sets. Text inside a block merges three ways on tokens, not lines. The lockfile merges per entry, and different pins of one package or operation are a conflict.
2. **Compilation.** The merged program parses and type-checks. A failure, such as one side renaming a parameter that the other side's new call still uses, is a semantic conflict (`Conflict::Semantic`) that names both contributing Changes.
3. **Query resolution.** Every `Query` resolves. A `ResolveError` that occurs on neither parent is a semantic conflict; Anvil's suggested fixes travel with it.
4. **Checks.** Every check that passes on both parents passes on the merge, at the fidelity the merge policy names: the check's declared fidelity for protected branches, `Interactive` elsewhere. A newly failing check is a check conflict (`Conflict::Check`), which catches combinations that are individually valid and jointly invalid (two sides each thin a wall within the limit; together they break it).
5. **Geometric conflicts.** For each Part, the driver computes the regions each side changed relative to the base. Overlapping regions are a geometric conflict (`Conflict::Geometric`), even when the merged program builds. For each Assembly, interference between Instances that exists in neither parent is an interference conflict (`Conflict::Interference`).

Changed regions come from provenance first: faces whose `EntityId`s differ from the base identify changed features. The driver then computes the region as the symmetric difference of base and side Bodies, using Anvil's regional difference operation with its `ErrorBound`; two regions conflict when their distance is below the merge clearance (default 0 mm, configurable per repository).

**Decision D-KLN-21:** Merge succeeds only when the merged design compiles, resolves, passes every check that both parents passed, and shows no new geometric overlap or interference. *Why:* a text merge that compiles can still produce a broken part, and the contract decides that merges are semantic plus geometric; checks make the definition general instead of a list of special cases. *Rejected:* line-based merge (conflicts on formatting, misses semantic breaks); feature-level merge alone (misses physical interactions between separate features); last-writer-wins on features (silent loss of work).

Conflicts are first-class, as in Jujutsu. A conflicted block is stored in the merge Change as an ordered set of alternatives, base and sides, and conflicts simplify algebraically when a conflicted Change is rebased, so rebasing never nests conflicts. Kiln evaluates a conflicted block as a typed error with three fixes: take one side, take both, or edit. Kiln can evaluate any side's alternative on demand, so the review shows each candidate geometry.

Merge bases come from the Change graph. With several merge bases, the driver merges them recursively into a virtual base, the approach of Git's recursive merge strategy [unverified: Git documentation not opened].

### Diff

| Diff | Content | Matching |
| --- | --- | --- |
| Source | Block insertions, deletions, moves and token edits | `BlockId`, else GumTree |
| Feature | Features added, removed and moved; parameter deltas with units | Feature block identity |
| Geometry | Per Part: changed regions as Bodies for the overlay; volume, mass and bounding-box deltas; Hausdorff distance with its `ErrorBound` | `EntityId` provenance, then geometry |
| Metric | Every check's value and margin before and after | Check identity |
| BOM | Items added, removed, re-revised; quantity and effectivity changes | Item number |
| Lifecycle | Revision, state, effectivity, compliance changes | Item and record identity |

All diffs are Kiln nodes over two `ChangeId`s, so they are cached and stream coarse results first: the source and feature diffs appear in milliseconds, the geometric diff refines afterwards.

### Very large assemblies

A product may hold 100,000 Instances of 10,000 unique Parts across many repositories (target for phase 4). Four mechanisms keep it usable.

1. **Partial clone.** A clone names a filter: `source-only` (no derived values), `paths(<pattern>)`, `depth(<n>)` or `display(<lod>)`. The origin is a promisor, as in Git's partial clone: missing objects are fetched on demand. Unlike Git, which fetches missing objects one at a time, Kiln batches demands per scheduling step into one request.
2. **Lazy loading.** Assembly evaluation needs only placements, mates and envelopes until something inspects a Part. Each Part's evaluated result carries derived envelope Bodies (convex hull and oriented bounding box) and mass properties, cached in the CAS and archived with every release, so a 100,000-Instance assembly lays out and checks clearance coarsely without loading B-reps.
3. **Display streaming.** Tessellations are stored as clustered segments with levels of detail. The viewport requests clusters by screen-space error, so orbiting a large assembly fetches what is visible.
4. **Split repositories.** Sub-assemblies owned by different teams live in their own repositories and are referenced across repositories, so each team clones only what it changes.

Target: open a 100,000-Instance assembly from a cold partial clone to an interactive coarse view in under 15 s on the reference laptop with a 100 Mbit/s link.

### Cross-repository references

A design repository references packages from the registry, catalog parts from the parts catalog and other design repositories. Each reference is pinned in the lockfile by content: `{ source, selector, resolved: ChangeId or ObjectId }`.

| Selector | Meaning | Update rule |
| --- | --- | --- |
| Release tag | A released revision, for example `motor-mount@C` | Explicit Proposal showing the diff |
| `ChangeId` | One exact state | Explicit |
| Branch, followed | Tracks a branch during co-development | Each Change records the resolved `ChangeId`; resolution moves only on an explicit refresh |
| Derived view | A derived package without source (IP protection) | Explicit |

A reference never moves silently, so rebuilds stay reproducible. When the referenced repository is not readable to a user, Kiln evaluates against the derived view if the user holds `read_derived`, and otherwise reports `AccessDenied` naming the reference.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Changes and transaction log | `Repo::commit`, `transactions`, `undo` | Concurrent ref moves become conflicted refs | Deterministic simulation of offline devices: no Change lost | 0 |
| Structural merge | `MergeDriver::merge(base, left, right)` | Typed conflicts, first-class in the merge Change | Merge corpus, including held-out merges: zero silent wrong merges; 90% or more of reference-clean merges clean (target) | 1 |
| Semantic and check conflicts | merged program evaluated | `Conflict::Semantic`, `Conflict::Check` | Seeded joint-invalid pairs all detected | 1 |
| Geometric conflict detection | regional difference with `ErrorBound` | `Conflict::Geometric`, `Conflict::Interference` | Seeded overlapping edits on golden products all detected; false positives under 5% (target) | 2 |
| Semantic and geometric diff | `compare.diff` | Partial diff flagged when a side fails to build | Diff of identical Changes is empty; geometry diff Hausdorff within `ErrorBound` of a reference | 1 |
| Partial clone and lazy loading | clone filters, promisor fetch | Offline access to a missing object is `RepoError::NotLocal` with a fetch suggestion | Large-assembly benchmark | 2 |
| Cross-repository references | pinned in lockfile | `AccessDenied`, `RefMissing` | Rebuild from lockfile reproduces `ObjectId`s | 2 |

## Collaboration

### CRDT over the syntax tree

Live editing on a branch happens in a live document: a replicated document that every participant (visual editor, code editor, language server, agent) edits locally and syncs through a relay. Its state maps deterministically to Ingot text, and the relay checkpoints it into Changes.

The document is a movable tree of blocks. A block is a grammar node that the Ingot tab declares mergeable; Kiln requires at least items (`use`, `feature`, `fn`, types and constants), statements inside bodies and parameters. Each block holds a kind, a `head` text, an ordered list of child blocks and a `tail` text. A file's text is the depth-first concatenation of heads, children and tails, so `pub feature bracket(...) -> Part {` is a head, each statement is a child and `}` is a tail. Comments and whitespace belong to the head of the block that follows them, so every byte of the file has exactly one owner.

Text inside blocks is a sequence CRDT, except literals. Each numeric, unit or string literal in a head is an atomic last-writer-wins register, so concurrent edits of `60mm` to `65mm` and to `70mm` yield one value, never `6570mm`. The overwritten author sees the competing value with a one-click restore, as the UI tab specifies. The tree uses the highly available move operation of Kleppmann, Mulligan, Gomes and Beresford. That algorithm applies moves in timestamp order, ignores a move that would create a cycle, and is proved convergent in Isabelle/HOL. Moving a feature is a real move, so a concurrent edit inside it follows the feature instead of being duplicated.

**Decision D-KLN-22:** The live document CRDT is Loro: a movable tree of blocks with Fugue-based text leaves, one document per package. *Why:* Loro provides both structures with a stable data format since 1.0; its text CRDT builds on Fugue, which minimizes interleaving of concurrent insertions; its import is fast (1.15 ms for a 1,659,541-operation document); and shallow snapshots drop history that already lives in Changes. *Rejected:* a text-only CRDT with reparsing, as in Zed's editor (a feature move becomes delete plus insert, and a concurrent edit to the moved feature duplicates it); Automerge 3 (cut memory over 10x, but Crucible would build the tree move layer itself [unverified that Automerge lacks native move]); operational transformation (needs a central ordering server, and Eg-walker's authors report that OT merges long-diverged branches slowly).

Every edit goes through one reconcile step, which keeps text editing and structural editing consistent:

1. An edit that stays inside one block and keeps its block structure applies directly to that block's text. This covers nearly all typing and every parameter change from the visual editor.
2. An edit that changes block structure (a newline that ends one statement and begins another, a paste of several features, a deletion across blocks) triggers a local reparse of the affected range. The client matches new blocks to old ones by span and content with GumTree, then emits tree operations (create, move, delete) and text operations on matched blocks.
3. Visual editor actions such as reordering features or inserting a feature from a dialog emit tree operations directly.

The reconcile step runs on one client against its own state, so it is deterministic and needs no coordination. Splitting or joining blocks moves text as a delete plus an insert, so a concurrent edit inside the moved span lands in the old block. The next reconcile detects text that no longer parses in place and flags it to both authors with the edit preserved, rather than dropping it. Block identities are Loro tree node ids; Changes store them in each `SourceFile`'s block map, which is what the merge driver matches by `BlockId`. A file edited outside Crucible goes through the same reconcile on import.

Concurrent edits can leave a block that does not parse. The parser is error-tolerant (a requirement on ING); Kiln reports the diagnostic and the UI shows the last good result for that block, marked stale. A delete concurrent with an edit inside the deleted block keeps the delete; the edit is preserved in history, and both authors see a notification with a one-click restore.

### Live documents, Changes and attribution

A live document belongs to a branch. The relay (team server or cloud) stores the document, checks every update against the sender's permissions and applies enforced locks. The relay snapshots the document into a Change on the triggers of D-KLN-19.

Every update batch is signed by the sender's device key. A Change created from a live document lists every contributing principal, and the relay keeps the signed update log segment that produced it; per-operation attribution comes from that log. Part 11 asks that records be attributable and that changes not obscure earlier information; signed updates plus immutable Changes give both.

Undo is per principal and reverts only that principal's operations, as in Zed's collaborative editor. A drag in the visual editor sends transient values through presence, so collaborators see a ghost of the motion; releasing the drag commits one text edit.

The language server joins the live document as its user, so text editors outside Crucible participate live. Agents join live documents only on branches their scope allows (Security section); people can join the live document of an agent's branch to watch or co-edit.

### Presence

Presence is ephemeral state per participant: cursor (`BlockId` plus offset), selection (`EntityId`s or a `Query`), camera, open dialog, a drag ghost, and for agents the current task and operation group. Each key is last-writer-wins per participant with a 30 s time-to-live. Presence is never stored in the CAS or the audit log; agent actions are audited by the API, not by presence.

### Optional locking

Locking is off by default because merges are structural. Two kinds are available:

| Lock | Scope | Enforcement | Typical use |
| --- | --- | --- | --- |
| Advisory | Block, file or Item | Presence shows "Ana is editing `rib`"; people are not blocked; agents respect advisory locks by policy, so their edits to a locked block fail with `LockHeld` | Default courtesy in busy live documents |
| Enforced | Path, block or Item | The relay rejects updates from others; merge rejects Proposals touching it; expiry default 8 h; administrators may break it with an audited record | Unmergeable Blobs (an imported native CAD file), regulated items under change control |

**Decision D-KLN-23:** Locks are optional and scoped; enforced locks exist for content that cannot merge and for regulated items. *Why:* structural merge makes pessimistic locking unnecessary for Ingot, but an imported binary cannot merge and some quality systems require exclusive checkout. *Rejected:* mandatory check-out and check-in, as classic PLM vaults use (serializes teams); no locks at all (unmergeable files lose work).

### Offline work and sync

A client keeps working offline: it edits its local document and creates local Changes. Reconnection takes one of two paths.

**Decision D-KLN-24:** CRDT auto-merge applies only to live documents and to reconnections within 60 s (default). Longer offline work becomes a private branch from the last synced Change and rejoins through the merge driver. *Why:* a CRDT guarantees convergence, not correctness, and offline authors never saw each other's edits, so their work needs the semantic, check and geometric conflict detection of D-KLN-21. *Rejected:* CRDT merge of every offline divergence (can silently combine individually valid edits into a broken design); forbidding offline editing (fails the local-first requirement).

Three protocols carry sync, all over TLS 1.3 on one connection (WebSocket, or WebTransport where available):

| Protocol | Content | Mechanism |
| --- | --- | --- |
| Live document sync | Signed CRDT update batches | Version-vector catch-up, then streamed updates batched every 30 ms |
| Object sync | Changes, trees, files, lifecycle records, derived values | Fetch: the client sends ref heads, the server streams the missing closure as a pack. Push: the client uploads objects missing on the server (`has_many`), then requests a compare-and-swap ref update |
| Events | Ref moves, CI results, review activity | Subscription stream with resumable cursors |

Tiers reconcile large sets of derived values with range-based set reconciliation, as Meyer describes: recursive partitioning by `ObjectId` range with fingerprints, descending only into ranges that differ.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Live co-editing | Loro document per package; signed updates | Unauthorized updates rejected by the relay with `AccessDenied` | Simulation: 50 peers, random partitions, all converge to identical text; 95th-percentile keystroke-to-remote latency under 100 ms on one continent (target) | 1 |
| Reconcile step | Text and structural edits to tree operations | Unparseable blocks keep the last good result, marked stale | Round-trip corpus: text to tree to text is byte-identical | 1 |
| Presence | Ephemeral keys with TTL | Expired presence disappears | Presence never appears in storage dumps | 1 |
| Locks | Advisory or enforced | `LockHeld` with holder and expiry | Enforced lock cannot be bypassed by live editing, push or merge | 2 |
| Offline rejoin | Private branch and merge driver after 60 s | Conflicts become a Proposal to resolve | Simulation of offline edits: no lost Change; every seeded semantic conflict detected | 1 |

## Product lifecycle management

PLM in Crucible is not a separate vault. Lifecycle records are signed CAS records in the design repository, BOMs are Kiln nodes over the assembly graph, and lifecycle gates are checks. The configuration management functions of SAE EIA-649 (identification, change management, status accounting, verification and audit) [unverified] map onto Items, change orders, Kiln nodes over lifecycle records, and checks plus the audit log respectively.

### Items and item numbers

An Item is the lifecycle identity of something that can be released: a Part, an Assembly, a document, a software item (firmware or a configuration file) or a purchased item that adopts a catalog part under an internal number. A Part carries its item number in Ingot, through the mechanical tab's `part(body, name, item: Option<ItemNumber>)` constructor, so the number belongs to the model and every editor sees it. Lifecycle data (revisions, states, effectivity, signatures) lives in records, because releasing must not edit the source it releases.

| Field | Content |
| --- | --- |
| `number` | Unique within the organization; allocated by the numbering policy |
| `kind` | `Part`, `Assembly`, `Document`, `Software`, `Purchased` |
| `name`, `description`, `classification` | Classification follows the organization's taxonomy |
| `home` | The design repository and path that define it |
| `make_buy`, `unit_of_measure` | `make` or `buy`; `each`, length, mass or volume |
| `approved_sources` | For `Purchased`: catalog part references with manufacturer part numbers, ranked |
| `labels` | Labels: integrity and data class (Security section) |

A numbering policy defines the format (sequential, prefixed by class, or a template) and whether gaps are allowed. The server leases blocks of 20 numbers to each client, so offline creation works; numbers left unused when a lease expires (default 30 days) return as void records. When a policy forbids gaps, the client writes a provisional number, and the server substitutes the permanent one in an automatic Change at first push, attributed to the server identity.

**Decision D-KLN-25:** Interchangeability decides between a new revision and a new item number, and Crucible computes it. The interchangeability check compares two definitions at their interfaces: mating faces and mates, envelope, mass properties within declared tolerance, and the Item's declared interface checks (fit, function). If all are equal within tolerance, the change is a revision; otherwise policy requires a new number, and a person confirms either verdict. *Why:* form-fit-function judgment is the most error-prone step in classical change control, and Crucible holds the data to compute it. *Rejected:* human judgment alone (inconsistent); a fully automatic verdict (some functions are not modeled, so a person confirms).

### Revisions and lifecycle states

A revision binds an Item to a released definition. The `ItemDefinition` record holds the canonical evaluated Part or Assembly `ObjectId`, the `Material` id and version, the product manufacturing information (PMI), properties and controlled documents. The revision record holds the label, the `ItemDefinition` `ObjectId`, the source `ChangeId`, the release tag, the `PlatformClass` of its results, the CI report and the signatures.

**Decision D-KLN-26:** Revision identity is content-based. An Item is "modified since release" exactly when its evaluated `ItemDefinition` differs from the released one, so an edit that leaves the definition unchanged (a refactor, a comment, a change elsewhere in the repository) never invalidates a release. *Why:* this is backdating applied to lifecycle state, and it removes the false "needs revision" noise that file-based vaults generate on every save. *Rejected:* revision on any source change (noise); manual tracking of what changed (error-prone).

Revision labels follow the policy: letters by default, skipping I, O, Q, S, X and Z as ASME Y14.35 practice recommends [unverified], or numbers. In-work iterations need no labels: they are Changes.

| State | Meaning | Entered by |
| --- | --- | --- |
| `InWork` | Being designed; any Change may alter it | Creation; a Change that alters a released definition |
| `InReview` | Frozen candidate in an open change order | Change order submission |
| `Prototype` | Released for prototype builds only | Change order with prototype scope |
| `Released` | Approved for production at its effectivity | Change order approval and release |
| `Superseded` | Replaced by a later revision; still valid within its effectivity | Release of the next revision |
| `Obsolete` | Not to be used in any new build | Change order with obsolescence disposition |

Transitions are guarded by checks: entering `Released` requires every check to pass at `SignOff` fidelity on a release-accepted class (Determinism policy) or hold a signed waiver, every child Item in the BOM to be released or released in the same change order, the required signatures, and no open conflicts. The default state machine is replaceable per organization by a policy package, and policy changes are themselves versioned and signed.

A release is a signed tag (contract section 7) on a Change. It creates the revision records of every Item it releases, archives their cited derived values in tier 3, and appends to the transparency log.

### Effectivity

Effectivity states when a revision applies. Windchill supports Serial, MSN, Block, Lot and Date effectivity; Crucible defines one record with four kinds, where an aircraft manufacturer serial number (MSN) is a `Serial` in the context of its end item:

```rust
pub struct Effectivity { pub context: ItemNumber /* end item */, pub kind: EffectivityKind, pub ranges: Vec<EffectivityRange> }
pub enum EffectivityKind { Date, Serial, Lot, Block }
```

Effectivity attaches to a revision within an end-item context: `BRK-10042 rev D` is effective for end item `D-200` from serial 500. A change order sets the new revision's effectivity and closes the previous revision's range in the same transaction.

A configuration point names an end item and a serial, date, lot or block value. Kiln treats it as an input cell, so configured views are cached nodes:

1. Select the end item's release whose effectivity contains the point.
2. For each usage in that release's BOM, resolve the child Item to the revision whose effectivity in this context contains the point; default to the revision recorded in the release.
3. Evaluate the configured assembly by substituting each resolved revision's released `ItemDefinition` from the CAS. This requires that an Instance of an Item resolves by item number and revision (Interfaces section).

Substitution is valid only between interchangeable revisions (D-KLN-25), which the release gate verifies. A configured view therefore never re-evaluates source: it assembles released definitions, so it is fast and cannot drift from what was signed. The effectivity consistency check rejects gaps and overlaps: for every usage and every point in the end item's effective range, exactly one revision applies.

The as-built record of a serial (installed revisions, lots and serials of each usage, deviations) is captured by manufacturing (MFG tab) and stored as a lifecycle record linked to the configuration point it was built from. Medical device customers record the UDI there, as 21 CFR 820.35 requires for each device or batch.

### Variants and the 150% BOM

A product declares options in Ingot, with constraints between them:

The syntax is illustrative; the Ingot tab owns it.

```
pub options drone_options {
    battery: Battery = standard,        // enum Battery { standard, extended }
    camera: bool = true,
    frame: Frame = short,
    rule battery == extended => frame == long
}
```

Instances and features may depend on options through `when` blocks. The Ingot compiler enforces that whether an Instance exists depends only on options and constants, never on computed geometry. Kiln can then evaluate assembly structure with options as symbolic values, producing the 150% BOM: every usage that exists in any valid configuration, each with its variant condition, a Boolean formula over options.

A satisfiability check over the option rules and conditions runs as a check on every build. It reports dead usages (no valid configuration includes them), slot collisions (two usages occupy one position in some valid configuration) and unbuildable configurations. A 100% BOM is the 150% BOM filtered by one option assignment, which is also a configuration point. A sellable configuration may map to its own item number through the policy.

**Decision D-KLN-27:** Variants are typed Ingot options with rules, and the 150% BOM comes from symbolic evaluation of assembly structure. *Why:* variants then live in the one model, every configuration is a cacheable node, and a solver proves rule consistency instead of relying on review. *Rejected:* separately maintained variant BOM tables, as PLM systems keep alongside CAD (drift from the model); enumerating configurations (exponential in the number of options).

### BOM views

All BOM views are Kiln nodes; none is edited directly.

| View | Content | Source |
| --- | --- | --- |
| EBOM | Items, quantities with units, instance names, find numbers, variant conditions, effectivity | Assembly graph at a Change or configuration point |
| MBOM | Process structure: phantoms, kits, raw stock, consumables, manufacturing-only Items | Manufacturing packages (MFG tab) that reference EBOM Items |
| SBOM | Service view: field-replaceable units, spare kits, service effectivity by serial | EBOM plus service annotations (`serviceable`, kits) |

In this spec, SBOM always means the service BOM, as in the contract. The software bill of materials is written out in full and never abbreviated.

The MBOM reconciliation check verifies that every EBOM Item and quantity is consumed exactly once by the MBOM for each configuration, or is marked as not manufactured (for example, a purchased sub-assembly installed in the field). An EBOM change that breaks reconciliation fails the check on the change order, which routes the change to manufacturing engineering.

Exports: BOMs export as CSV, as STEP AP242 product structure, and through the ERP connector events (Interfaces section).

### Where-used

The repository server maintains a where-used index: every release and every Change on a protected branch adds usage edges (parent Item revision, child Item, quantity, effectivity, variant condition) from the EBOM node. The index spans repositories within an organization through cross-repository references, and covers catalog parts through `Purchased` Items.

A where-used lookup returns parent revisions up to end items, with effectivity and condition. Results are filtered by the caller's access: a usage in a repository the caller cannot read appears as a count of restricted usages, never with names.

Where-used drives impact analysis on change orders, supplier end-of-life notices (every end item and serial range containing an obsolete catalog part) and vulnerability response (every shipped serial range containing an affected software item).

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Items and numbering | `part.item(...)`, numbering policy | Duplicate number rejected at push with the existing owner named | Concurrent allocation simulation: no duplicates | 2 |
| Interchangeability | `compare.diff` with the interchangeability check | Undecidable cases (unmodeled interfaces) require human verdict | Seeded FFF-breaking edits all flagged | 3 |
| Revisions and states | Revision records, policy state machine | Guard failures name every unmet condition | Release of a Part with an unreleased child is impossible | 2 |
| Effectivity | `Effectivity` records, configuration points | Gaps and overlaps are check failures | Configured BOM equals reference for 1,000 random points | 3 |
| Variants and 150% BOM | Ingot options and rules; symbolic structure evaluation | Dead usages, collisions and unbuildable configurations reported | Every valid configuration's 100% BOM equals a brute-force evaluation on small products | 3 |
| BOM views | EBOM, MBOM, SBOM nodes | Reconciliation failure is a check failure | Golden product 3 MBOM reconciles; quantities match | 2 |
| Where-used | Indexed lookup, access-filtered | Restricted usages counted, not named | Index equals full recomputation nightly | 2 |

### Change management

The contract decides that change orders are pull requests; the agents tab adds that a change order is a Proposal against a released configuration. Crucible keeps the three classical records and maps each to one mechanism.

| Record | Purpose | Mechanism |
| --- | --- | --- |
| Change request (ECR) | States a problem or an improvement, its evidence and the affected Items | `ChangeRequest` record, linked from nonconformances, complaints, CAPAs, field failures, compliance alerts or agent findings |
| Change order (ECO) | Implements one or more requests | A Proposal with lifecycle scope: affected Items with from and to revisions, effectivity, disposition of existing stock, implementation plan, approvals |
| Change notice (ECN) | Tells downstream parties what was released and from when | Signed `ChangeNotice` record created by the release, delivered as an event, with acknowledgement tracking |
| Deviation | Permits a temporary departure for given serials or lots | `Deviation` record with effectivity and expiry; appears in the as-built record |

A change order runs this sequence:

1. Create the order from one or more requests; the order's branch starts from the release or protected branch named in the request.
2. Edit on the branch. Agents may prepare the change on their own branches and open it as a Proposal under the order.
3. Run impact analysis: where-used up to end items, open orders touching the same Items, interchangeability per Item (D-KLN-25), MBOM reconciliation, compliance deltas and stock dispositions.
4. Submit. Affected Items enter `InReview`, and the branch freezes; further edits create a new iteration that resets approvals.
5. Approve. The policy routes approval steps by role and attribute, serial or parallel; each approval is an electronic signature on the order's evaluated state.
6. Release. The merge, the release tag, the revision records, effectivity updates and the change notice are written in one metadata-store transaction; the objects they reference are uploaded first, so a failure leaves no partial release.
7. Implement. Downstream acknowledgements (manufacturing, suppliers, ERP) are tracked until the order closes.

[[DIAGRAM: Change order lifecycle. Boxes: "Change request" → "Change order (branch + Proposal)" → "Impact analysis (where-used, interchangeability, MBOM reconciliation, compliance)" → "Submitted: Items InReview, branch frozen" → "Approval steps (signatures)" → "Release transaction (merge, signed tag, revision records, effectivity, change notice)" → "Implementation (acknowledgements from manufacturing, suppliers, ERP)" → "Closed". Back-arrow from "Approval steps" to "Change order" labelled "rejected or new iteration (approvals reset)".]]

Approvals bind to content. A signature signs the order record, which names the head `ChangeId`, the evaluated `ItemDefinition`s and the CI report `ObjectId`. If anything changes, the signed hashes no longer match, and every approval is void without anyone having to notice.

**Decision D-KLN-28:** An approval is a signature over the exact evaluated content, so any later edit voids it automatically. *Why:* classical PLM tracks approvals by object and revision, so an edit after approval needs a process rule to catch it; a hash makes it impossible to miss. *Rejected:* approvals by reference to a branch (an edit after approval would ride on the old approval).

Separation of duties is policy: an order's author cannot be its only approver, and an agent can never sign. Agents may attach analysis and recommendations, which appear in the review as evidence. Concurrent orders that touch the same Item serialize at release: the second must rebase onto the first, which resets its approvals only if its evaluated content changes.

### Electronic signatures

A signature record holds the signer's identity, printed name, the time from the server clock (offline signing is not allowed), the meaning (`Authored`, `Reviewed`, `Approved`, `Released`, `Verified`, or a policy-defined meaning), the signed record's `ObjectId`, the authentication event and an ECDSA P-256 signature from the signer's hardware-backed key. Crucible uses ECDSA P-256 for signatures by people and devices because it is FIPS-approved and supported by the platform keystores and WebAuthn authenticators of every Tier 1 platform [unverified: FIPS 186-5 and each keystore's documentation not opened].

| 21 CFR Part 11 requirement | Crucible mechanism |
| --- | --- |
| 11.10: validation, including the ability to discern invalid or altered records | Validation package with the oracle results of this tab; every record is hash-verified, so alteration is detectable |
| 11.10: secure, computer-generated, time-stamped audit trails that do not obscure earlier information, kept as long as the records | Transaction log and audit log in the transparency log (Security section); records are immutable; audit retention is at least the retention of the records it covers |
| 11.10: operational checks enforcing permitted sequencing | Lifecycle state machine guards |
| 11.10: authority checks | Cedar policies evaluated on every request and every signature |
| 11.10: device checks of the source of input | Device keys sign live document updates and Changes; hardware runners sign measurements |
| 11.50: printed name, date and time, meaning, shown in human-readable form | Signature records carry all three; every rendered or exported record shows them |
| 11.70: signatures cannot be excised, copied or transferred | A signature covers the record's `ObjectId`; moved to another record, it does not verify |
| 11.100: unique to one individual, identity verified before issuance | One principal per person; administrators record identity verification; principals are never reassigned |
| 11.200: two distinct identification components; in a continuous session the first signing uses all, later signings at least one | In Part 11 mode, every signing asks for re-authentication: the user identity plus a password or a user-verifying authenticator; the policy chooses, and the customer's validation documents the choice |
| 11.300: uniqueness, periodic revision, loss management, transaction safeguards | Delegated to the identity provider and Crucible's lockout and anomaly alerts |

The 11.100 certification to FDA is the customer's act. Crucible provides the template and records the certification as a document Item.

Medical device makers now work under the QMSR: FDA's amended 21 CFR Part 820, effective 2 February 2026, which incorporates ISO 13485:2016 by reference and requires the design and development controls of its clause 7.3 for class II and III devices. The design history and design changes those controls ask for are change orders, checks and their reports; Crucible does not claim certification on a customer's behalf.

Aerospace makers following AS9100 practice need configuration management, control of design changes and first article inspection [unverified: the AS9100D text was not opened]. Crucible covers the first two with Items, change orders and effectivity. First article inspection results arrive as QIF 3.0 results from manufacturing (MFG tab) and become lifecycle records linked to the revision and serial. Customer approval of changes, where a contract requires it, is an approval step assigned to an external principal.

### Requirements traceability

Requirements are typed records in the design repository, declared in Ingot or imported (ReqIF import is planned [unverified that ReqIF suits every source tool]). The syntax below is illustrative; the Ingot tab owns it.

```
requirement load_capacity "Carries 1.2 kN at the mounting hole below 60% of yield" {
    parent: sys::payload_mount
    verify: analysis
}

part.require(peak_stress(part, load) < 0.6 * yield)
    .verifies(load_capacity)
```

A requirement holds an identifier, text, rationale, parent requirements, a verification method (`analysis`, `test`, `inspection` or `demonstration`) and an owner. A check declares the requirements it verifies; a hardware check in CI may verify `test` requirements.

The traceability matrix is a Kiln node from requirement to design to check to result to evidence. For each requirement it lists the checks, the Items and features they cover, each outcome at a Change with its fidelity and margin, and the evidence objects: CI reports, hardware test data and signed reviews.

Coverage is itself a check. Every requirement needs at least one verifying check of its method, every check at release fidelity must pass or hold a waiver, and every `test` requirement needs a hardware result on the released revision.

When a requirement's text or parameters change, its links become suspect: the verifying checks keep running, but release gates treat the requirement as unverified until a person reviews the links and signs. Requirements are versioned with the design, so a release records exactly which requirement text it verified.

### Compliance records

Compliance is a check over data, not a questionnaire. The Manufacturing tab (MFG) specifies the substance rules: RoHS per homogeneous material against Annex II as amended by Delegated Directive 2015/863 (ten restricted substances), REACH candidate-list and SCIP data, and conflict minerals. This tab owns the records those checks consume and produce, and their lifecycle.

| Record | Content | Source |
| --- | --- | --- |
| Composition | Substances per homogeneous material, with CAS registry numbers and mass fractions | `Material` versions; derived for assemblies by roll-up |
| Supplier declaration | Signed document, date, scope (catalog part or Item and revision), declared substances | Supplier returns (supplier collaboration below) or catalog data packages |
| Regulation package | Versioned list of restricted substances, thresholds and exemptions | Pinned, dated data packages from the registry, as MFG requires for regulatory lists |
| Exemption | The exemption used, its scope and its expiry | Signed by the `quality` role |
| Compliance verdict | Per Item revision: `Compliant`, `NonCompliant` or `Unknown`, with evidence `ObjectId`s | Output of the MFG compliance checks, stored with the revision |

Missing data is never treated as compliant; it yields `Unknown`, which blocks any release whose policy requires compliance.

Regulation packages and declarations are `High`-durability inputs. When a new regulation version arrives, Kiln re-evaluates compliance checks for every released revision; where-used then names affected end items and serial ranges, and the policy opens change requests automatically. An expired exemption fails the check on the next evaluation.

Products with firmware fall under the EU Cyber Resilience Act, whose reporting obligations for actively exploited vulnerabilities and severe incidents apply from 11 September 2026: an early warning within 24 hours and a notification within 72 hours. `Software` Items carry a CycloneDX 1.7 software bill of materials (ECMA-424) per release. When a vulnerability is published, where-used lists the affected shipped serials within minutes (target), so the 24-hour deadline is spent on assessment, not search. The reports themselves go through the manufacturer's process; Crucible supplies the evidence.

### Secure supplier collaboration

Suppliers are external organizations with their own principals, federated through their identity provider or invited directly with mandatory second factors. A supplier never browses the design repository. It receives data packages:

| Package content | Form |
| --- | --- |
| Geometry | STEP AP242 with PMI, 3MF or glTF, generated from released revisions |
| Drawings and inspection plans | PDF plus QIF 3.0 plans |
| Requirements | The requirements the supplier must meet, with verification methods |
| Derived models | Envelopes, interface geometry or behavioral models without source (Security section) |

A data package is a signed record listing its contents, their source revisions, the recipient organization, its labels and an expiry. Each file is watermarked per recipient: visibly where the format allows, and by a recipient fingerprint in metadata.

Suppliers return quotes, design-for-manufacture feedback (comments anchored to entities, or a Proposal on a branch shared with them), QIF inspection results, certificates of conformance and material declarations. Returned records are signed by the supplier's principals and enter the lifecycle as evidence.

Access is policy-checked on every request, and export-controlled data reaches a supplier only when its attributes satisfy the labels (Security section). Expiry revokes access. Revocation cannot recall copies already downloaded; the audit log records exactly what each supplier received.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Change requests, orders, notices | Records plus Proposal | Guard failures name unmet conditions; edits after submission reset approvals | Approval on stale content impossible (signature verification test) | 2 |
| Electronic signatures | Signature records, re-authentication | Failed re-authentication blocks signing and is audited | Part 11 mapping test suite; excised signature fails to verify | 2 |
| Requirements traceability | Requirement records, `verifies` links | Uncovered or suspect requirements block release | Matrix equals reference on golden products 1 to 4 | 2 |
| Compliance checks | Regulation packages, declarations | Missing data yields `Unknown`, never compliant | Seeded restricted substances all detected | 3 |
| Supplier packages | Signed package records, watermarks | Expired access denied; label mismatch denied | Supplier principal cannot read outside its packages (policy fuzzing) | 3 |
| Vulnerability where-used | Software Items with software bills of materials | Unknown software contents flagged | Seeded vulnerable library traced to every affected serial | 3 |

## Security

### Identity

Every actor is a principal with a stable id that is never reused or reassigned.

| Principal | Authentication | Keys |
| --- | --- | --- |
| Person | Single sign-on through the organization's identity provider over OpenID Connect or SAML 2.0; local accounts only on desktop and air-gapped installs; WebAuthn passkeys as the second factor | A device key per device, hardware-backed where available (TPM, Secure Enclave, Android keystore, WebAuthn), for signing Changes and live document updates |
| Agent | Registered by an owner; short-lived, audience-bound tokens obtained by token exchange from the owner's credential, as the agents tab specifies | Ephemeral signing key bound to the token |
| Service | Workers, CI runners, the hardware runner, integrations | Workload identity (cloud workload identity or mTLS certificates from the deployment's CA) |
| External organization | Federated identity provider of a supplier or customer, or invited accounts with mandatory WebAuthn | As for persons |

User provisioning and deprovisioning follow the identity provider through SCIM 2.0. Sign-in sessions last 12 h by default; signing always re-authenticates (Electronic signatures section). Offline desktops hold a refresh grant valid for 7 days by default, after which they can still edit local branches but cannot push or read newly fetched labelled data.

### Authorization

**Decision D-KLN-29:** Authorization uses Cedar policies, evaluated in-process on every request, including live document updates at the relay. *Why:* Cedar supports role- and attribute-based access in one language, is implemented in Rust and has a formal model in Lean. Its authors describe a sound and complete logical encoding for policy analysis, which lets Crucible prove that a policy change grants no unintended access before it takes effect. *Rejected:* Open Policy Agent with Rego (Cedar's authors report Cedar performs far better and reads as well or better); hand-written role checks (no analysis, scattered logic).

The policy model has three parts. Roles come from groups in the identity provider: `viewer`, `commenter`, `editor`, `maintainer`, `approver`, `release_manager`, `export_officer`, `quality`, `admin`. Attributes describe principals (organization, citizenship and US-person status, location, training, license authorizations, clearances per data class) and resources (labels, Item state, repository, path). Agents hold the agents tab's scopes; this tab maps each scope to the actions below. Actions are fine-grained: `read_source`, `read_derived`, `evaluate`, `edit`, `push`, `merge`, `approve`, `sign`, `release`, `purge`, `manage_policy`.

Policies attach to the organization, repository, path and Item. A deny overrides any allow, and the default is deny. Every decision is logged with the policy ids that decided it.

Policy changes are Proposals to a policy repository. Before such a Proposal merges, Cedar's analysis compares the old and new policy sets and lists every principal and action whose access changes; a person approves that list.

### Branch protection

Protection rules attach to ref patterns, such as `main`, `release/*` and `tags/*`.

| Rule | Effect |
| --- | --- |
| No direct pushes | Changes arrive only through merged Proposals |
| Required checks | Named checks at named fidelity pass on the merge result |
| Required reviews | Number of approvals, owner approvals for paths or Items, no self-approval |
| Signed Changes | Every Change carries a valid device signature |
| No history rewrite | Refs move forward only; tags never move |
| Change control | Changes to Items in `Released` state require a change order |
| Agent exclusion | Agent principals cannot update the ref, approve or sign |

### Agent identities and scopes

An agent principal has an owner (a person accountable for it) and a scope:

| Scope element | Example |
| --- | --- |
| Repositories and paths (write set) | `drone/*`, read; `drone/frame`, edit |
| Refs | Writes only to `agents/<agent>/*` (fixed by the contract) |
| Scopes | The agents tab's scopes, which cover the operation groups `Read`, `Edit`, `Evaluate`, `Inspect`, `Compare` and `Propose` |
| Clearance | The data classes the agent may read: the minimum of its owner's clearance, its model endpoint's clearance and the repository policy (agents tab); default excludes `export_controlled` |
| Model endpoint | The language-model endpoint the agent sends content to, with the clearance per data class the organization grants it |
| Budget | The agents tab's `Budget`, carved from the owner's hierarchy |
| Expiry | Default 30 days; tokens default to 15 minutes |

The API evaluates every agent request against both the agent's scope and the owner's own permissions; the agent gets the intersection. An agent can never sign, approve, release, change policy, edit the oracles directory or read held-out models (contract section 7); loosening a tolerance or check is possible only in a Proposal that a person approves, as the agents tab's risk class R3 requires. Content goes to an agent only when its model endpoint is cleared for the content's data class: ITAR content goes only to endpoints the organization has cleared as operated inside the permitted boundary, such as an on-premises model.

### Tamper-evident audit

Every write, every read of labelled data, every policy decision, signature, login, export and administrative action becomes an audit entry: principal, action, resource `ObjectId`s, decision with policy ids, client device, server time and request id. Entries record identifiers, never labelled content.

**Decision D-KLN-30:** The audit log, the repository transaction logs and release tags are entries in per-tenant transparency logs served in the C2SP tlog-tiles format. Checkpoints are signed by the deployment; customers may run witnesses that cosign checkpoints. *Why:* a Merkle-tree log, whose operations follow RFC 6962 with SHA-256, makes any rewrite or fork detectable by anyone holding an earlier checkpoint, and static tiles make verification cheap and cacheable; witnesses keep even the cloud operator honest. *Rejected:* an append-only database table (the operator can rewrite it undetectably); a public blockchain (cost, latency, and leakage of metadata).

Clients store the last checkpoint they saw and verify consistency on every sync, so a forked log is detected at the next connection. Checkpoints carry an Ed25519 signature, which tlog-tiles requires for logs that interact with the public witness network, and an ECDSA P-256 signature in FIPS mode. Logs are never pruned without a retention policy, as tlog-tiles requires, and retention defaults to the longest record retention the organization configures.

### Encryption

Transport uses TLS 1.3 everywhere, with mutual TLS between servers, workers and runners. Storage encryption is described in the CAS section. In FIPS mode, every cryptographic operation goes through a FIPS 140-3 validated module; the Platform tab owns the provider abstraction, with AWS-LC through aws-lc-rs as the leading candidate [unverified: current certificate status]. NIST's validation program moves FIPS 140-2 modules to the historical list after 21 September 2026, so new deployments require FIPS 140-3.

Keys live in the platform keystore on desktops, in a KMS or HSM on servers, and in a customer-controlled key service for end-to-end mode. Signing keys for releases and checkpoints live in HSMs on servers and are never exported.

### IP protection

People often need to share a design's behavior without its source. Crucible offers four derived views, each a Kiln node whose output is a signed package:

| Derived view | What the recipient gets | What stays private |
| --- | --- | --- |
| Frozen geometry | Released Bodies at fixed parameters, with PMI | Source, history, parameters, `HistoryRecord`s |
| Envelope and interfaces | A simplified envelope Body (offset hull at a declared clearance), interface faces, mates, mass properties | Internal geometry |
| Behavioral model | An FMI 3.0 FMU or reduced-order model for system simulation, with its `ValidityEnvelope` | Geometry and source |
| Remote parametric model | A feature callable with parameters; evaluation runs on the owner's workers, and results return as Bodies | Source and intermediate values never leave the owner's infrastructure |

**Decision D-KLN-31:** Parametric sharing without source uses remote evaluation on the owner's workers, never shipped compiled code. *Why:* any code that runs on the recipient's machine, Wasm included, can be decompiled, so obfuscation is not protection; remote evaluation keeps the source with its owner while results still cache by `OpKey`. *Rejected:* obfuscated Wasm components (false security); encrypted packages (the key must reach the recipient's machine).

Redaction removes geometry and metadata from a derived view: features marked `confidential` are replaced by Anvil's defeaturing or envelope operations within a declared deviation; names, comments, provenance ids and history are stripped or remapped. A redaction check runs before signing. It verifies that the package's CAS closure contains no object from the source closure except those explicitly allowed, that no string from the source appears in the package, and that the geometric deviation stays within the declared bound.

### Export control

Labels classify data, following the agents tab's model: every value carries an integrity label (`trusted` or `untrusted`) and a data class. Policy defines the data classes; the defaults are `public`, `internal`, `confidential` and `export_controlled`, with subclasses per regime such as `export_controlled:itar:<USML category>` and `export_controlled:ear:<ECCN>`. Organizations add classes such as `cui` or `customer:<name>`. Labels attach to repositories, paths, Items, records, API responses and CAS objects.

Labels propagate as information flow, as in the FIDES model the agents tab adopts. Kiln assigns each derived value the most restrictive combination of its inputs' labels, so a simulation result over an ITAR part is ITAR and a render of a model holding an untrusted STEP name is untrusted. Lowering a label requires a declassification record: a signed determination by a principal with the `export_officer` role naming the derived view and the reason. Redaction checks support that determination, but never replace it.

**Decision D-KLN-32:** Export-controlled data is handled by labels that propagate through Kiln, policies over principal attributes, residency-bound storage, and an optional end-to-end mode. *Why:* ITAR treats even visual inspection by a foreign person as a release (22 CFR 120.56), so every path to the data, including viewing and agents, must be checked, and only propagation through derived values closes the gap where an analysis result leaks a controlled design. *Rejected:* separate air-gapped installations as the only option (they remain available but isolate teams); repository-level flags without propagation (derived values leak).

Policy controls who sees labelled data, including through presence and live documents: a participant who does not satisfy a label sees neither the labelled content nor its geometry.

Residency controls where labelled data is stored and evaluated. A label can require storage and compute in named regions, operated only by staff with named attributes. Cloud workers for such data run in matching regions, and the scheduler refuses placement elsewhere with `ResidencyDenied`.

End-to-end mode lets a customer store labelled data on Crucible's cloud without giving the cloud the plaintext. ITAR 22 CFR 120.54(a)(5) and EAR 15 CFR 734.18(a)(5) treat end-to-end encrypted technical data meeting their conditions as not exported. The conditions include FIPS 140-2 or successor modules and no intentional storage in proscribed countries (ITAR section 126.1, EAR Country Group D:5). In this mode, keys stay in the customer's key service; storage and relay see ciphertext only; evaluation runs on customer-controlled workers inside the customer's boundary. Whether a deployment qualifies is the customer's legal determination; Crucible documents the controls.

Classification fields on Items and repositories record jurisdiction, classification, the classifier and the date. New repositories inherit the organization's default label. Data shared with external organizations passes a restricted-party screening connector, and the policy denies sharing with unscreened organizations.

### Software supply chain

| Asset | Control |
| --- | --- |
| Crucible releases | Reproducible builds; SLSA Build L3 provenance (levels read in SLSA 1.1; 1.2 is current [unverified against 1.2]); Sigstore signatures; a CycloneDX software bill of materials; updates delivered under The Update Framework, which resists rollback, freeze and key-compromise attacks |
| Rust dependencies | Pinned `Cargo.lock`; audits of each third-party crate recorded in-tree; license and advisory checks on every commit; no GPL or AGPL in the core (contract) |
| Registry packages | Publishers authenticated through Sigstore keyless signing (short-lived certificates bound to an OIDC identity, logged in Rekor); registry metadata under The Update Framework; lockfiles pin content hashes |
| Wasm components | Built from source by the registry's build service at SLSA Build L3; the registry rebuilds independently and publishes only when the bytes match |
| Air-gapped installs | Signed offline bundles that carry their Update Framework metadata, provenance and transparency proofs |

Package policy per organization lists allowed publishers, requires a minimum age for new versions (default 72 h), blocks names within an edit distance of 1 from popular packages unless the publisher is verified, and resolves private package names only from the private registry, which prevents dependency confusion.

### Threat model

| Threat | Vector | Controls | Residual risk |
| --- | --- | --- | --- |
| Malicious package | Wasm component or Ingot code that sabotages geometry, leaks data or exhausts resources | No clocks, randomness, files or network during evaluation; fuel and memory limits; publisher signing, minimum age, allowed publishers; behavior visible in diffs and checks | A package can encode the data it receives into its outputs; outputs reach outsiders only through exports, which are policy-checked and audited |
| Compromised publisher or registry | Malicious version published or served | Sigstore identities and transparency; Update Framework metadata; content-pinned lockfiles; independent rebuilds | A compromise before the first pin of a new dependency |
| Prompt injection through model content | Instructions hidden in comments, part names, catalog datasheets, imported STEP metadata, supplier returns or package documentation | Labels mark untrusted content in every API response and in every derived value; untrusted strings reach agents only as `ExternalText` handles, and reading one taints the session (AGT tab), following CaMeL's separation of control flow from data; tainted sessions cannot trigger externally visible actions without a person's approval; agents cannot sign, approve, release or change policy, and tainted Proposals never auto-merge | An injected agent can still produce a bad Proposal, which review and checks must catch |
| Data exfiltration by agents | Agent sends design data to its model endpoint, a webhook, a package or an external tool | Agents reach the outside only through the API; labels gate which model endpoints receive content; only people configure webhooks and integrations; agents hold no general network egress in Crucible-hosted runtimes; every read of labelled data is audited | An external agent that misdeclares its endpoint; mitigated by administrator registration and audit |
| Lethal trifecta | One agent session holding private data, untrusted content and an external channel | No agent session holds all three, following Willison's analysis: agents have no external channel except `api` acts, which need a person's approval, and a tainted session cannot request them | Approvers who approve without reading; mitigated by acts showing a deterministic summary of effects and recipients |
| Cache poisoning | Forged result attestation | Only trusted builders write the shared cache (D-KLN-9); 1% spot re-execution | A compromised CI worker, caught statistically by spot re-execution |
| Malicious insider | Leaks or alters designs | Least privilege, labels, audit with witnesses, separation of duties on approvals, signed Changes | Authorized reads by a cleared insider |
| Cloud operator | Reads or alters tenant data | Envelope encryption with customer keys; end-to-end mode; witnessed logs; residency | Metadata such as object sizes and timing |
| Network attacker | Interception or replay | TLS 1.3, mTLS, signed updates with sequence numbers | none known |
| Compromised device | Stolen laptop or session | Disk encryption, hardware-backed keys, short tokens, remote revocation, device posture attributes in policy | Data already cached on the device |

## Deployment

### Modes

One codebase serves every mode; modes differ in which services run and where data lives, never in features.

| Mode | Services | Metadata store | Object store | Identity |
| --- | --- | --- | --- | --- |
| Local-first desktop | One application with Kiln, a local CAS and repository, and a local relay for live documents on the same machine | SQLite | Local packs | OS account, or SSO when connected |
| Browser | The same engine compiled to Wasm, in a worker | SQLite compiled to Wasm over the Origin Private File System | Origin Private File System | SSO |
| Team server | One container or binary: repository server, relay, CI coordinator, optional workers and hardware runner gateway | SQLite on one node, PostgreSQL for larger teams | File system or S3-compatible storage | OIDC or SAML through the organization's identity provider |
| Cloud SaaS | Regional cells: API gateways, relays, repository servers, worker fleets, per-tenant transparency logs | FoundationDB | Cloud object storage | Federated SSO, SCIM |
| On-premises | The cloud stack on the customer's Kubernetes, or a team server | PostgreSQL or FoundationDB | Customer object storage | Customer identity provider; customer-managed keys |
| Air-gapped | On-premises with no external network | As on-premises | As on-premises | Local identity provider; offline license |

A desktop is a full peer. It edits, evaluates, branches, merges and keeps history offline; it connects to any number of remotes (a team server, the cloud, a supplier's server), as a Git clone does.

**Decision D-KLN-33:** The desktop is local-first: the local repository is authoritative for unpushed work, and every feature except remote-only services (shared cache, cloud workers, relays for other machines) works offline. *Why:* engineers work on aircraft, at plants and on secure networks; local-first also makes interactive latency independent of the network. *Rejected:* a thin client over a cloud model, as browser-only CAD systems use (fails offline and in air-gapped sites).

### Sync between deployments

Deployments sync with the same three protocols as clients (Collaboration section): object sync, live document sync and events. Two server patterns build on them.

| Pattern | Use | Mechanism |
| --- | --- | --- |
| Mirror | A team server or factory site keeps a read replica of cloud repositories for local speed or continuity | Object sync on ref events; label and residency policy filters what is mirrored |
| Federation | Two organizations collaborate, each on its own server | Supplier data packages and shared branches cross the boundary as signed records; each side enforces its own policy and keeps its own audit log |

Air-gapped sites exchange data by signed bundles. `crucible bundle create --since <checkpoint>` writes a file holding the missing objects, ref updates and transparency-log proofs; `crucible bundle import` verifies signatures, closure, labels and log consistency before applying anything. Bundles for transfer between security domains go through the receiving domain's review step, so a person or an approved guard inspects the contents first.

Software updates, registry packages, catalog data and regulation packages reach air-gapped sites the same way, as offline bundles carrying their Update Framework metadata.

### Scaling targets

All numbers are targets for phase 4 unless marked otherwise.

| Scope | Target |
| --- | --- |
| Desktop | Local CAS up to 2 TiB; 10 million Changes per repository; open a warm 200-feature part to an exact view in under 1 s; 1,000-part assembly from warm cache in under 10 s (contract target) |
| Browser | Every feature of the desktop; evaluations that exceed the browser's memory limit run on cloud workers when the user or policy allows, and return identical bits (D-KLN-10) |
| Team server, one node with 16 cores and 64 GiB | 200 active users, 50 concurrent live documents, 1,000 Changes per minute, 20 TiB objects (phase 2) |
| Cloud cell | 50,000 active users; ref update 99th percentile under 200 ms; object fetch 10 GB/s per cell; 100 participants per live document |
| Cloud workers | 10,000 cores per tenant on demand within 5 minutes; first remote result for a cached input in under 1 s |
| Repository | 100 TiB derived values; 10^9 objects; where-used over 10^6 Items in under 1 s |

### Backup and disaster recovery

Content addressing makes backups verifiable. A restore is correct when every ref's object closure is present with matching hashes and every transparency log is consistent with checkpoints held by clients and witnesses; the restore tool checks both.

| Mode | Backup | Recovery point (target) | Recovery time (target) |
| --- | --- | --- | --- |
| Desktop | Unpushed Changes push as soon as a remote is reachable; optional copy of append-only packs to any folder | Last push | Minutes, by re-cloning |
| Team server | Continuous metadata log shipping (PostgreSQL point-in-time recovery, or SQLite write-ahead-log replication); object storage versioning; nightly test restore | 5 minutes | 4 hours |
| Cloud | Metadata replicated synchronously across three zones; objects replicated to a second region in the same residency zone; immutable (write-once) backups kept 35 days | 0 within a region; 15 minutes across regions | 1 hour for regional failover |
| On-premises and air-gapped | As team server, with the customer's backup system; Crucible ships the restore verifier | Customer policy | Customer policy |

Restore drills run quarterly in the cloud and are part of the on-premises acceptance procedure. Deterministic simulation (Determinism policy section) covers crash and partial-replication scenarios of the metadata store and the collector.

### Identical behavior on every Tier 1 platform

Every Tier 1 build runs the same engine, the same policy evaluator and the same storage formats. Behavior that could differ by platform lives in the platform layer: paths, Unicode normalization, file locking, keystores, file watching and threading. Results are bit-identical across Tier 1 CPU targets by D-KLN-10, so a design opened on Windows, macOS, Linux or a browser shows the same geometry, checks and diffs.

Capacity differs by platform; features do not. When a browser or a small laptop lacks the memory for an evaluation, Kiln offers remote evaluation, subject to labels, residency and budget, and the result is the same bits it would compute locally. Offline, the same evaluation runs locally under a tighter memory budget or reports `EvalError::Environment` with the memory it needs.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Desktop offline | Full local repository and Kiln | Remote-only services report `Offline` with the queued action | Airplane-mode suite of every API operation | 1 |
| Team server | One container | Health checks; refuses to start on schema mismatch with a migration hint | Install-to-first-Proposal test under 15 minutes | 1 |
| Cloud | Regional cells | Cell failover | Chaos tests: zone loss with no acknowledged write lost | 1 |
| On-premises | Kubernetes package | Preflight report names missing prerequisites | Install on reference clusters | 2 |
| Air-gapped | Signed bundles | Bundle rejected on any verification failure, with the reason | Bundle round-trip between two isolated sites | 3 |
| Restore verifier | Closure and log consistency | Lists missing or inconsistent objects | Restore of seeded corrupt backups detects every fault | 2 |

## External interfaces

### Repository API

The agents tab (AGT) defines the `api` method catalog and its transports over MCP and the native SDKs. This tab supplies the behavior behind the repository methods in that catalog and adds the lifecycle and governance methods that the catalog lacks.

| `api` methods (AGT) | Behavior supplied here |
| --- | --- |
| `read.tree`, `read.source`, `read.history`, `read.branches` | Trees, files and Changes at a `ChangeId`; history from the Change graph; refs |
| `edit.apply`, `edit.revert`, `edit.create_branch`, `edit.reset_branch` | One Change per call (D-KLN-19); ref compare-and-swap; transaction-log entries |
| `evaluate.*`, `evaluate.cancel` | Kiln demand with a priority class, fidelity ceiling and budget |
| `compare.diff` | The six diffs of the `repo` section |
| `propose.*` | Proposals, the merge driver, branch protection |
| `read.audit` | Audit entries from the transparency log |

| Added method | Group | Purpose | Agents |
| --- | --- | --- | --- |
| `repo.merge_preview(base, left, right)` | Compare | Conflicts and merged result without writing | Allowed |
| `repo.undo(transaction)` | Edit | Undo one repository transaction from the transaction log | Own branches only |
| `lifecycle.where_used(item)`, `lifecycle.bom(view, point)` | Read | Where-used and configured BOM views | Allowed, access-filtered |
| `change_request.create`, `change_order.create`, `change_order.submit` | Propose | Lifecycle requests and orders | Draft only; a person submits |
| `change_order.approve(id, meaning, reauth)`, `release.create(order)`, `deviation.grant` | Govern | Signatures and releases | Never |
| `policy.propose`, `label.declassify`, `purge.request` | Govern | Administration | Never (`policy:admin` is human-only in AGT) |

Every response carries the `ChangeId` and generation it reflects and the labels of its content. Strings from outside the organization (supplier returns, catalog datasheets, imported files, external packages) arrive as the agents tab's `ExternalText` handles, so reading them taints the session. Errors are typed and carry fixes, as everywhere in `api`.

### Events and webhooks

| Event family | Events |
| --- | --- |
| Repository | `change.created`, `ref.updated`, `ref.conflicted`, `tag.created` |
| Proposals and CI | `proposal.opened`, `proposal.updated`, `proposal.merged`, `ci.completed`, `check.failed`, `hardware.completed` |
| Lifecycle | `change_request.created`, `change_order.submitted`, `change_order.approved`, `change_order.rejected`, `release.created`, `change_notice.issued`, `item.state_changed`, `deviation.granted` |
| Compliance and security | `compliance.alert`, `vulnerability.affected`, `policy.changed`, `audit.anomaly`, `budget.threshold` |

An event envelope holds an id, type, organization, repository, subject id, server time, a per-repository sequence number and a small data record of identifiers and states.

**Decision D-KLN-34:** Events and webhook payloads carry identifiers, never design content; receivers fetch content through the API with their own credentials. *Why:* webhook receivers are often third-party systems, and thin payloads keep policy enforcement, label checks and audit in one place. *Rejected:* full payloads (bypass policy, leak labelled data into logs of other systems).

Delivery is at least once and ordered per repository by sequence number; receivers deduplicate by event id. Each webhook request carries an HMAC-SHA-256 signature over the timestamp and body, and receivers reject timestamps older than 5 minutes. Failed deliveries retry with exponential backoff for 72 hours, then move to a dead-letter queue visible to administrators. Only people with the `maintainer` or `admin` role create webhooks; agents cannot.

The ERP connector is a standard webhook consumer: it reads change notices and BOM views and posts acknowledgements back as lifecycle records.

### Hardware CI runner

The hardware runner executes checks that need physical equipment. Each execution is a hardware run: it is not a Kiln node, and its only product is a measurement record that enters Kiln as an input cell. Examples: print a part and measure it, flash firmware and run a test, load a specimen on a rig, inspect on a coordinate measuring machine.

**Decision D-KLN-35:** Hardware results enter Kiln as measured input cells, never as cached derived values. A measurement record is keyed by the check, the `ObjectId`s of the design inputs it tested, the rig and the run. A hardware check declares whether a result stays valid while those inputs are unchanged (a fit check) or must be repeated per lot or per build (a fatigue test). *Why:* physical results are not pure functions, so caching them as derived values would claim a determinism they do not have; as inputs, they flow into checks and traceability like any other data, with their uncertainty. *Rejected:* hardware runs on literally every commit (rig time and consumables make that impossible for long tests).

Hardware checks therefore run on every commit that changes their inputs, and reuse valid results otherwise; this tab raises a change request to state the contract's "hardware CI on every commit" that way.

The runner protocol works as follows:

1. A runner registers as a service principal with a hardware-backed key and advertises its rigs, instruments, consumables and safety envelope.
2. The runner pulls run requests over an outbound connection, so factory networks need no inbound ports.
3. A run request names its artifacts (G-code and other manufacturing output from the MFG tab, firmware images), its procedure (an Ingot test procedure or a Wasm component that drives instruments through a capability-scoped interface), its required instruments and its budget in rig minutes. Instrument access is a capability granted to the procedure by the runner, never available during evaluation, so evaluation stays free of I/O.
4. The runner enforces its safety envelope locally (force, temperature, speed, voltage limits) regardless of the request. Emergency stops are hardware. Runs requested from agent branches use only rigs marked `unattended_safe`; other rigs require an operator to start them. Programs that reach a machine follow the manufacturing tab's approval rule: a person approves every program before it runs.
5. The runner returns a signed measurement record: raw data in the CAS, instrument ids with calibration records, environment readings, operator identity and the procedure version.
6. A measurement from an instrument past its calibration date is recorded but invalid; checks over it fail with `CalibrationExpired`.

Measurement uncertainty is part of the record. Checks compare measured values with requirements using the uncertainty that the manufacturing and physics tabs define. Measurement records feed the traceability matrix as `test` evidence and, for the drone in phase 4, as validation data for Flux models.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Repository API | Operations above, typed errors | Policy denials name the missing permission | API conformance suite shared with `api` | 1 |
| Events and webhooks | Thin, signed, ordered per repository | Retries, then dead-letter | Delivery simulation with receiver outages: no loss, no reordering per repository | 1 |
| Hardware runner | Pull-based run requests, signed measurements | Safety envelope violations abort the run and are recorded | Rig simulator suite; spoofed measurement rejected | 1 (printers), 2 (rigs and instruments) |
| Calibration control | Calibration records with expiry | `CalibrationExpired` | Expired instrument cannot produce valid evidence | 2 |

## Rust API

The signatures are illustrative but plausible; they follow the Rust API Guidelines. Crates: `core/kiln`, `core/cas` and `core/repo` (lifecycle and security records live in `repo`, with policy evaluation in a `repo::policy` module). Async trait methods use native `async fn` in traits; implementations that cross threads return `Send` futures.

### CAS

```rust
/// SHA-256 identity of a canonical object, with an algorithm code for migration.
#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
pub struct ObjectId { alg: HashAlg, digest: [u8; 32] }

#[non_exhaustive]
#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
pub enum HashAlg { Sha256 = 1 }

#[derive(Copy, Clone, PartialEq, Eq, Debug)]
pub enum ObjectKind { Blob, Record, Segmented, Index }

pub trait CasStore: Send + Sync {
    /// Returns verified bytes; a hash mismatch is `CasError::Corrupt`, never data.
    async fn get(&self, id: ObjectId) -> Result<Bytes, CasError>;
    async fn get_range(&self, id: ObjectId, range: Range<u64>) -> Result<Bytes, CasError>;
    async fn has_many(&self, ids: &[ObjectId]) -> Result<BitVec, CasError>;
    /// Computes the identity from canonical bytes; encryption and compression are tier details.
    async fn put(&self, kind: ObjectKind, canonical: Bytes, domain: &EncryptionDomain)
        -> Result<ObjectId, CasError>;
    /// Protects objects that a pending Change will reference from collection.
    async fn lease(&self, ids: &[ObjectId], ttl: Duration) -> Result<LeaseId, CasError>;
}

#[non_exhaustive]
pub enum CasError {
    NotFound(ObjectId),
    Corrupt { id: ObjectId, tier: TierId },
    UnknownCodec { id: ObjectId, codec: u16 },
    KeyUnavailable { domain: DomainId },
    ResidencyDenied { label: Label, region: Region },
    /// The lease expired or the object was purged before the ref update.
    LeaseLost { id: ObjectId },
    Io(std::io::Error),
}
```

### Kiln

```rust
pub struct Kiln { /* memo tables, scheduler handle, CAS tiers, trust policy */ }

impl Kiln {
    pub fn new(config: KilnConfig, cas: Arc<dyn CasStore>, platform: PlatformHandle) -> Self;
    /// Applies a batch of input changes atomically and returns the new generation.
    pub fn apply(&self, batch: InputBatch) -> Generation;
    /// Streams results coarse first; dropping the stream withdraws the demand.
    pub fn demand(&self, request: EvalRequest) -> ResultStream;
    pub fn estimate(&self, request: &EvalRequest) -> Result<CostEstimate, EvalError>;
    /// Writes the memo snapshot (edges and ObjectIds, not values) to the local CAS.
    pub fn snapshot_memo(&self) -> Result<ObjectId, CasError>;
}

/// A stream of `ResultEvent`s; dropping it cancels nodes no one else demands.
pub struct ResultStream { /* receiver, demand handle */ }
impl futures::Stream for ResultStream { type Item = ResultEvent; /* ... */ }

pub struct EvalRequest {
    pub snapshot: Snapshot,          // a ChangeId, or a live document state at a generation
    pub targets: Vec<Target>,        // Parts, Fields, checks, BOM views, diffs
    pub fidelity: Fidelity,          // ceiling
    pub priority: Priority,
    pub budget: Budget,
    pub principal: PrincipalId,
}

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
pub enum Fidelity { Preview, Interactive, SignOff }

/// The agents tab's priority classes.
#[derive(Copy, Clone, PartialEq, Eq, Debug)]
pub enum Priority { Interactive, Agent, Ci, Batch }

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, Debug)]
pub enum Durability { Low, Medium, High }

pub struct ResultEvent {
    pub generation: Generation,
    pub target: Target,
    pub fidelity: Fidelity,
    pub status: StreamStatus,              // Partial, Final, Superseded; the UI derives its ResultStatus
    pub value: Result<ValueHandle, EvalError>,
    pub error: Option<ErrorStatement>,     // ErrorBound or Flux error estimate
    pub check: Option<CheckStatus>,        // Provisional below the check's declared fidelity
    pub labels: LabelSet,
    pub cost: CostRecord,
}

#[non_exhaustive]
pub enum EvalError {
    /// Deterministic: memoized like a value. Carries Anvil, Flux or Ingot errors with fixes.
    Domain(DomainError),
    Cycle { path: Vec<SourceSpan> },
    OpVersionRetired { op: OpId, version: u32, fixes: Vec<Fix> },
    BudgetExceeded { estimate: CostEstimate, remaining: Budget, options: Vec<Fix> },
    AccessDenied { action: Action, resource: ResourceRef, hints: Vec<PolicyHint> },
    ResidencyDenied { label: Label, region: Region },
    /// Environmental: never cached; retried by policy.
    Environment(EnvironmentError),
    Cancelled,
}
```

### Operations as Kiln sees them

Anvil and Flux implement this trait for every operation version; Kiln never calls an operation any other way.

```rust
pub trait OpImpl: Send + Sync + 'static {
    const ID: OpId;                    // OpId::new("anvil", "blend")
    const VERSION: u32;                // behavior version, pinned by the lockfile
    const GRADE: DeterminismGrade;
    type Inputs: OpInputs;             // Bodies, Fields, plain values; each has an ObjectId
    type Outputs: OpOutputs;           // canonical forms, with HistoryRecords and ErrorBounds

    fn eval(&self, cx: &mut OpCx<'_>, inputs: Self::Inputs) -> Result<Self::Outputs, OpError>;
    fn cost(&self, sizes: &InputSizes) -> CostEstimate;
}

#[derive(Copy, Clone, PartialEq, Eq, Hash, Debug)]
pub enum DeterminismGrade { Portable, ClassExact, Certified }

// `PlatformClass` is defined by the Platform tab in `platform-api`; Kiln only reads it.
use platform_api::PlatformClass;

/// Everything an operation may use: no clocks, no ambient randomness, no I/O.
impl OpCx<'_> {
    pub fn checkpoint(&mut self) -> Result<(), Cancelled>;            // poll at least every 10 ms of CPU
    pub fn rng(&self, stream: u64) -> Philox4x32;                     // keyed by the OpKey
    pub fn det(&self) -> &runtime::Det;                               // the Platform tab's det_* combinators and exact_sum
    pub fn fidelity(&self) -> Fidelity;
    pub fn progress(&mut self, fraction: f32);
}

#[derive(Copy, Clone, PartialEq, Eq, Hash, Debug)]
pub struct OpKey(ObjectId);

pub enum StreamStatus { Partial, Final, Superseded }

pub struct ResultAttestation {
    pub key: OpKey,
    pub output: ObjectId,
    pub worker: PrincipalId,
    pub engine_build: ObjectId,
    pub cost: CostRecord,
    pub signature: Signature,
}
```

### Repository

```rust
#[derive(Copy, Clone, PartialEq, Eq, Hash, Debug)]
pub struct ChangeId(ObjectId);

pub struct Change {
    pub parents: Vec<ChangeId>,
    pub tree: ObjectId,
    pub author: PrincipalId,
    pub on_behalf_of: Option<PrincipalId>,     // the owner, when an agent authors
    pub contributors: Vec<PrincipalId>,
    pub live_document: Option<DocumentId>,
    pub time: HybridTime,
    pub description: Option<String>,
    pub conflicts: Vec<ConflictRecord>,
    pub signature: Signature,
}

pub trait Repo: Send + Sync {
    async fn change(&self, id: ChangeId) -> Result<Change, RepoError>;
    async fn commit(&self, branch: &RefName, edits: EditBatch, by: &Principal)
        -> Result<ChangeId, RepoError>;
    /// Compare-and-swap; `expected: None` creates the ref.
    async fn update_ref(&self, name: &RefName, expected: Option<ChangeId>, new: ChangeId, by: &Principal)
        -> Result<RefTransactionId, RepoError>;
    async fn transactions(&self, limit: usize) -> Result<Vec<RefTransaction>, RepoError>;
    async fn undo(&self, tx: RefTransactionId, by: &Principal) -> Result<RefTransactionId, RepoError>;
}

pub trait MergeDriver: Send + Sync {
    /// Runs the five merge conditions; never writes refs.
    async fn merge(&self, kiln: &Kiln, base: ChangeId, left: ChangeId, right: ChangeId)
        -> Result<MergeOutcome, RepoError>;
}

pub struct MergeOutcome { pub tree: ObjectId, pub conflicts: Vec<Conflict> }

#[non_exhaustive]
pub enum Conflict {
    Text { path: RepoPath, block: BlockId, alternatives: Alternatives },
    Lockfile { entry: LockEntryId, left: Pin, right: Pin },
    Semantic { diagnostics: Vec<Diagnostic>, from: [ChangeId; 2] },
    Check { check: CheckId, outcome: CheckOutcome },
    Geometric { part: EntityRef, left: ObjectId, right: ObjectId, bound: ErrorBound },
    Interference { assembly: EntityRef, a: InstancePath, b: InstancePath, volume: Quantity<Volume> },
}
```

### Lifecycle and security records

```rust
pub struct Item {
    pub number: ItemNumber,
    pub kind: ItemKind,                         // Part, Assembly, Document, Software, Purchased
    pub name: String,
    pub home: SourceRef,
    pub make_buy: MakeBuy,
    pub unit: UnitOfMeasure,
    pub approved_sources: Vec<CatalogRef>,
    pub labels: LabelSet,
}

pub struct Revision {
    pub item: ItemNumber,
    pub label: RevisionLabel,
    pub definition: ObjectId,                   // evaluated ItemDefinition
    pub source: ChangeId,
    pub release: TagName,
    pub class: PlatformClass,
    pub ci_report: ObjectId,
    pub state: LifecycleState,
}

pub enum LifecycleState { InWork, InReview, Prototype, Released, Superseded, Obsolete }

// `Effectivity` and `EffectivityKind` as defined in the Effectivity section.

pub struct ChangeOrder {
    pub id: ChangeOrderId,
    pub requests: Vec<ChangeRequestId>,
    pub proposal: ProposalId,
    pub affected: Vec<AffectedItem>,            // item, from and to revision, disposition
    pub effectivity: Vec<(ItemNumber, Effectivity)>,
    pub head: ChangeId,                         // the exact content approvals sign
    pub definitions: Vec<ObjectId>,             // evaluated ItemDefinitions
    pub ci_report: ObjectId,
    pub state: ChangeOrderState,                // Draft, Submitted, Approved, Released, Closed, Rejected
}

pub struct SignatureRecord {
    pub signer: PrincipalId,
    pub printed_name: String,
    pub meaning: SignatureMeaning,
    pub signed: ObjectId,                       // the exact record signed
    pub time: ServerTime,
    pub authentication: ObjectId,               // the re-authentication event
    pub signature: Signature,                   // ECDSA P-256
}

pub enum SignatureMeaning { Authored, Reviewed, Approved, Released, Verified, Custom(SmolStr) }

pub struct Principal { pub id: PrincipalId, pub kind: PrincipalKind, pub attributes: Attributes }

pub enum PrincipalKind {
    Person,
    Agent { owner: PrincipalId, scope: AgentScope },
    Service,
    External { organization: OrgId },
}

pub struct Label { pub integrity: Integrity, pub class: DataClass }  // as defined by the agents tab
pub enum Integrity { Trusted, Untrusted }
pub struct DataClass(SmolStr);   // public, internal, confidential, export_controlled:ear:9E610

pub trait Authorizer: Send + Sync {
    fn decide(&self, who: &Principal, action: Action, resource: &ResourceRef, context: &RequestContext)
        -> Decision;
}

pub struct Decision { pub allowed: bool, pub policies: Vec<PolicyId>, pub hints: Vec<PolicyHint> }
```

## State of the art

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Incremental evaluation | Suspending scheduler with constructive traces and early cutoff (Mokhov, Mitchell and Peyton Jones, JFP 2020); demand-driven incremental computation (Adapton, PLDI 2014) | Salsa; Buck2's DICE | Adopt: Salsa-style verification with durability and backdating, suspending scheduling, signed constructive traces for sharing (D-KLN-1) | Re-executed nodes per edit against the minimal set on 500 scripted edits; target: 200-feature rebuild after an early edit under 2 s (contract target) |
| Early cutoff without hashing on the hot path | Value equality with lazily computed content identity | Salsa (equality); Nix content-addressed derivations (hash) | Adopt both: equality interactively, `ObjectId` for sharing (D-KLN-5) | Drag-preview latency on golden product 2; target: under 100 ms (contract target) |
| Shared build cache | Content-addressed CAS plus action cache (Bazel Remote Execution API v2); signed realisations (Nix RFC 62) | Bazel with Buildbarn or EngFlow | Adopt the structure, with signed attestations and a trusted-writer policy (D-KLN-9); REAPI adapter for storage | Hit rate across a 20-person team on golden products 3 and 4; target: 90% or more of nodes served from cache after the first CI run |
| Eviction | GreedyDual-Size (Cao and Irani, USITS 1997) | LRU in build caches | Adopt (D-KLN-7) | Rebuild time under a 256 MiB budget; target: within 2x of unbounded memory |
| Reproducible reductions | Binned summation (Demmel, Nguyen, Ahrens; ReproBLAS) | ReproBLAS | Adopt for varying partitions; fixed trees elsewhere (D-KLN-13) | Bit equality across 1 to 64 threads and 1 to 16 nodes; cost per reduction against plain summation |
| Elementary functions | Correctly rounded functions with proofs (CORE-MATH) | glibc libm, LLVM libc | Adopt through the Platform tab's `detmath` (D-KLN-11) | Bit equality on all Tier 1 targets; worst-case hard-case corpus |
| Deterministic testing | Deterministic simulation of whole clusters (FoundationDB) | FoundationDB | Adopt for Kiln, sync, collector and server | Simulated hours per night; target: 1,000 in phase 0 and 10,000 by phase 2 |
| Content hashing | SHA-256 (FIPS 180-4) versus BLAKE3 (tree-parallel, verified streaming) | BLAKE3 for raw speed | SHA-256 with an algorithm code, parallel by chunk (D-KLN-14); deviation for FIPS approval and ecosystem interoperability | Hash throughput; target: 1 GiB in under 150 ms on the reference laptop |
| Chunking | FastCDC with normalized chunking (USENIX ATC 2016); prolly trees (Noms, Dolt) | Open-source Rabin-based chunkers (the FastCDC baseline); Dolt for structured data | Structure-aware segments with key-defined boundaries; FastCDC for opaque Blobs (D-KLN-15) | Bytes stored per Change on golden-product histories; target: deduplication of 95% or more between successive Changes |
| Numeric compression | pcodec for numeric columns; byte shuffling plus zstd; meshoptimizer codecs for display meshes | zstd on raw arrays | Per-chunk codecs: shuffling plus zstd for Fields now, pcodec if phase 1 benchmarks show a gain (D-KLN-16) | Compression ratio and decode speed on golden-product Fields and meshes against zstd level 3 |
| Encrypted deduplication | Server-aided message-locked encryption (DupLESS, USENIX Security 2013) | Convergent encryption in backup tools | Domain-keyed derivation, deduplication only within a domain (D-KLN-17) | Cross-domain confirmation test; storage overhead versus no encryption |
| Version control storage | Git object model with SHA-256 format; Jujutsu's operation log and first-class conflicts | Git, Jujutsu | Changes as microversions; transaction log; first-class conflicts (D-KLN-19, D-KLN-20) | No lost Change under deterministic simulation; time to log 10 million Changes |
| Fine-grained CAD history | Onshape microversions and branches | Onshape | Adopt microversions; beat with feature-level, check-level and geometric merge (D-KLN-21) | Merge corpus of reference designs; target: 90% of reference-clean merges clean, zero silent wrong merges |
| Structured merge | GumTree matching; Spork and Mergiraf PCS-triple merge | Mergiraf | Adopt for unidentified blocks; `BlockId` matching for Crucible-edited files | Conflict counts versus Git and Mergiraf on a corpus of Ingot merges |
| Live collaboration | Movable tree CRDT (Kleppmann et al.); Fugue for text; Eg-walker architecture | Loro; Automerge 3 | Loro over a block tree (D-KLN-22) | Convergence under simulation; target: 95th-percentile keystroke-to-remote under 100 ms on one continent |
| Set reconciliation | Range-based set reconciliation (Meyer 2022) | rsync-style full listing | Adopt for tier anti-entropy | Bytes exchanged against the size of the difference |
| Authorization | Cedar (OOPSLA 2024): analyzable, Lean-modelled policy language | Open Policy Agent (Rego) | Adopt (D-KLN-29) | Policy decision latency; target: 99th percentile under 1 ms per request; analysis of every policy change |
| Tamper-evident logs | RFC 6962 Merkle logs served as C2SP tlog-tiles with witnesses | Certificate Transparency; Sigstore Rekor | Adopt (D-KLN-30) | Fork detection in fault-injected tests; verification cost per client sync |
| Software supply chain | SLSA Build L3 provenance; Sigstore keyless signing; The Update Framework | Registries without build provenance or update metadata | Adopt all three | SLSA L3 assessment; Update Framework attack test suite |
| Prompt-injection defense | Control and data flow separation with capabilities (CaMeL; 77% of AgentDojo tasks solved with provable security against 84% undefended) | Guardrail classifiers | Taint labels and capability gating in `api` and the agent runtime (AGT tab) | AgentDojo-style suite on Crucible tools; target: zero successful exfiltrations |
| PLM change control | ECR, ECO and ECN workflows with effectivity (Teamcenter, Windchill, Arena, Fusion Manage) | Windchill, Teamcenter, Arena, Fusion Manage | Change orders as Proposals with content-bound signatures (D-KLN-28); effectivity as configuration inputs to Kiln | Change-order cycle time on a scripted ECO scenario; Part 11 mapping audited by a third party in phase 3 |
| Variant management | 150% BOM with variant conditions and configurators | Teamcenter product configurator [unverified: product pages opened gave no detail] | Typed options with symbolic structure evaluation and SAT checks (D-KLN-27) | Configured BOM equals brute force on small products; solver time on 200 options |

The PLM rows cite vendor practice that this draft could not confirm in primary documentation, except Windchill's effectivity types: the Teamcenter and Arena pages opened gave only general claims, and the Fusion Manage help page returned not found. The targets in those rows therefore come from Crucible's own oracles, not from vendor comparison.

## Platform notes

| Platform | Risk | Decision |
| --- | --- | --- |
| All Tier 1 | Bit-identical `Portable` results across x86-64, ARM64 and wasm32 | Determinism policy and Platform tab mechanisms; nightly cross-target rebuild of every golden release |
| Windows | File locking prevents replacing open pack files; paths over 260 characters; case-insensitive names | Packs are append-only and replaced by rename after close; the platform layer uses long-path APIs; the repository rejects paths that differ only by case or Unicode normalization |
| macOS | Case-insensitive, normalization-insensitive default file system; App Sandbox limits on folder access | Same path rule as Windows; repositories live in user-chosen folders with security-scoped bookmarks (Platform tab) |
| Linux | Many file systems with weak `fsync` semantics on some configurations | Pack writes use write-then-rename with `fsync` on file and directory; the deterministic simulation suite injects torn writes |
| Browsers | Storage eviction; quota limits; no SHA-256 instructions guaranteed in Wasm; threads only under cross-origin isolation | Request persistent storage; unpushed Changes push eagerly and the UI warns when storage is not persistent; hashing uses Wasm SIMD; Crucible's hosting always sends the cross-origin isolation headers, and a self-hosted page without them runs the engine on one worker and says so |
| Browsers | WebCrypto keys are non-extractable but bound to the origin | Device keys for signing are WebAuthn credentials where possible; origin-bound keys are re-enrolled when storage is cleared |
| iPadOS and Android (Tier 2) | No JIT for App Store apps; memory pressure kills | Wasm components run interpreted; Kiln uses a 1 GiB budget and offloads heavy evaluation to workers |
| Servers | FoundationDB operations burden; S3-compatible stores differ in conditional-write support | Team servers default to PostgreSQL; the object store adapter probes conditional-write support at startup and otherwise routes ref updates through the metadata store |
| Air-gapped | No identity provider federation, no time source of record, no package updates | Local identity provider; signed bundles for software, packages and regulations; the server clock is the time of record and is audited against a site time source |
| FIPS mode | Validated modules differ by platform | The Platform tab's crypto provider selects a FIPS 140-3 module on servers and desktops; browsers use WebCrypto, so FIPS-required deployments must use desktop or server clients for signing |

## Interfaces with other subsystems

### Consumed

| From | What | Canonical types | Requirement |
| --- | --- | --- | --- |
| Ingot (ING) | Compiler stages as Kiln nodes; dependency recording on every read; error-tolerant parsing; the block grammar (which nodes are mergeable, which lists are order-insensitive); syntax for options, `when`, `requirement` and `verifies` | `Feature`, `Check`, IR | The compiler emits static Op calls per feature body so Kiln can prefetch them; whether an Instance exists depends only on options and constants |
| Anvil (ANV) | Every operation through `OpImpl`; `Exact` and `Preview` fidelities; canonical forms; regional difference and interference for merge; defeaturing and envelopes for derived views | `Body`, `EntityId`, `HistoryRecord`, `ErrorBound`, `Query`, `ResolveError` | Canonical Bodies order data by `EntityId` or spatial key; segment keys exposed for chunking; behavior fingerprints per operation version |
| Flux (FLX) | Solver operations through `OpImpl`; fidelity modes; error estimates; checkpoints keyed by Op key and step; per-operation cross-class tolerances; Field storage in partition-aligned chunks | `Field`, `ValidityEnvelope`, `PlatformClass` | Field values in canonical order; cost models per operation; no consumer-triggered re-solves (D-FLX-5 agrees with Kiln's dataflow model) |
| Platform (PLT) | Compute pools, deterministic combinators, `detmath`, SIMD dispatch, GPU primitives, Wasm runtime configuration, file and keystore services, crypto provider | `PlatformClass`, `HardwareProfile`, `RepoPath` | Section "Requirements on the Platform tab" |
| Agents and `api` (AGT) | Method catalog and transports; sessions, grants, clearances and taint; budgets and admission control; priority classes; Proposal record fields | `Proposal`, `Principal`, `Budget`, labels | Agents never hold `sign`, `approve`, `release` or `policy:admin`; tainted sessions never satisfy auto-merge |
| Mechanical (MEC) | `part(body, name, item: Option<ItemNumber>)`; family rows as Items; after-assembly operations for the MBOM; title blocks and revision tables reading release data | `Part`, `Assembly`, `Instance` | Every BOM line traces to a `Part` with an item number or to a family row |
| Manufacturing (MFG) | MBOM restructuring rules, routings, as-built records, QIF results, compliance rule packages, serial numbers | `Part`, `Assembly`, `Instance` | As-built records reference configuration points; compliance checks return per-Item verdicts with evidence |
| Electronics (ELX) | Board assemblies and firmware images; BOM lines for catalog parts | `Part`, Catalog part | Firmware builds become `Software` Items with a CycloneDX software bill of materials |
| Coverage and materials (COV) | `Material` versions with composition; regulation-relevant properties | `Material` | Composition per homogeneous material for compliance roll-up |
| UI (UIX) | Display of progressive results, conflicts, presence, locks and review | `ResultStatus`, `ChangeId` | The UI derives `ResultStatus` from `ResultEvent` |
| Ecosystem (ECO) | Package registry, catalog parts and regulation data packages | Package, Catalog part | Registry follows the supply-chain controls of the Security section |

### Provided

| To | What | Types and methods |
| --- | --- | --- |
| Every tab | Memoized, cancellable, coarse-first evaluation with cost estimates | `Kiln::demand`, `ResultEvent`, `EvalError`, `Fidelity`, `CostEstimate` |
| Anvil, Flux, Wasm components | The operation contract and its sandbox | `OpImpl`, `OpCx`, `DeterminismGrade`, `OpKey` |
| Every tab | Content-addressed storage | `CasStore`, `ObjectId` |
| UI, agents, CI | Changes, refs, merge, diffs, Proposals, live documents, presence, locks | `ChangeId`, `Change`, `MergeDriver`, `Conflict` |
| Mechanical, Manufacturing, Electronics | Items, revisions, effectivity, BOM views, where-used, change orders, release records for title blocks and revision tables | `Item`, `Revision`, `Effectivity`, `SignatureRecord` |
| Every tab | Identity, policy decisions, labels, audit | `Principal`, `Authorizer`, `Label` |
| Manufacturing and hardware CI | Hardware runner protocol and measurement records | Measurement records as Kiln input cells |

## Oracles

All oracles live under `oracles/kiln/`, `oracles/cas/` and `oracles/repo/`, which agents can read but not write. Held-out sets are marked.

| Oracle | Verifies | Method | Gate |
| --- | --- | --- | --- |
| `kiln/minimality` | Only affected nodes re-execute | 500 scripted edits on golden products; compare the re-executed set with a reference computed by full dependency analysis | Phase 0 |
| `kiln/equivalence` | Incremental equals from-scratch | After every scripted edit, compare every output `ObjectId` with a cold build | Phase 0 |
| `kiln/cancel` | Cancellation leaves no trace | 10,000 runs with random cancellation and restart; final state equals a clean run | Phase 0 |
| `kiln/determinism` | Bit equality within each class | Every operation version's corpus on every Tier 1 target, with perturbations of threads, SIMD level, allocator, hash seeds and memory budget | Phase 0 (contract gate) |
| `kiln/fingerprint` | Behavior versions bumped when outputs change | Conformance corpus digest per operation version | Every commit |
| `kiln/attestation` | Shared cache integrity | Forged, replayed and cross-tenant attestations rejected; 1% spot re-execution reports mismatches | Phase 1 |
| `kiln/sim` | Kiln, sync, collector and server under faults | Deterministic simulation; seeds replay | Phase 0, nightly |
| `cas/integrity` | Corruption detected on every tier | Bit flips and truncation injected; reads fail with `Corrupt` and heal from another tier | Phase 0 |
| `cas/gc` | No reachable object collected | Simulation with concurrent writers, leases and crashes | Phase 1 |
| `cas/domains` | No cross-domain decryption or correlation | Ciphertext and storage names compared across domains | Phase 1 |
| `repo/merge` (held-out) | Merge correctness | Corpus of three-way merges with known results, including seeded semantic, check, geometric and interference conflicts; zero silent wrong merges | Phase 1 |
| `repo/roundtrip` | Text, block tree and text are byte-identical | Corpus of Ingot files and random edits | Phase 1 |
| `repo/converge` | CRDT convergence | 50 simulated peers with partitions and offline periods | Phase 1 |
| `repo/plm` | Lifecycle rules | Release with unreleased child rejected; effectivity gaps and overlaps detected; configured BOMs equal brute force on 1,000 random points | Phase 2 |
| `repo/part11` | Part 11 controls | Excised and transferred signatures fail; approval after edit void; re-authentication required; audit retained | Phase 2 |
| `repo/policy` | Authorization | Policy fuzzing against a reference model; Cedar analysis on each policy change; agent principals never sign, approve or release | Phase 1 |
| `repo/redaction` (held-out) | Derived views leak nothing beyond what is declared | Planted strings, features and provenance ids in source; package scanned | Phase 3 |
| `repo/labels` | Label propagation and residency | Seeded ITAR inputs; every derived value labelled; no placement outside allowed regions | Phase 2 |
| `repo/audit` | Tamper evidence | Rewritten and forked logs detected by clients and witnesses | Phase 1 |
| `repo/restore` | Backup correctness | Seeded corrupt backups; the verifier finds every fault | Phase 2 |
| `repo/hardware` | Measurement integrity | Spoofed, replayed and expired-calibration measurements rejected; safety envelope violations abort in the rig simulator | Phase 1 |

## Phasing

| Phase | Gate (contract) | This tab delivers |
| --- | --- | --- |
| 0 Foundations | Determinism suite green; unit errors fail to compile | Kiln core (memoization, backdating, durability, cancellation, priority classes); local CAS with SHA-256 and canonical CBOR; determinism policy and suite; deterministic simulation harness; Changes and transaction log on the desktop |
| 1 Wedge | Golden products 1 and 2 | Progressive results; GreedyDual-Size eviction; team server; shared cache with attestations; structural and semantic merge; source, feature and metric diffs; Loro live documents, presence and offline rejoin; Cedar authorization, SSO, branch protection, agent scopes; audit transparency log; budgets; events and webhooks; hardware runner for printers; cloud SaaS single region |
| 2 Mechanical depth | Golden products 3 and 4 | Remote evaluation on cloud workers; geometric conflict detection and geometry diff; partial clone and lazy loading; cross-repository references; Items, revisions, change orders, electronic signatures (Part 11 mode); EBOM, MBOM and SBOM views; where-used; traceability; labels with propagation and residency; encryption domains; purge; on-premises; backup and restore verifier; hardware runner for rigs and instruments |
| 3 Product breadth | Golden product 5 | Effectivity and configured views; variants and 150% BOM; compliance records; supplier collaboration; derived views and redaction; end-to-end mode; air-gapped bundles; interchangeability check; vulnerability where-used; third-party Part 11 assessment |
| 4 Full multiphysics | Golden product 6 | Scale targets (100,000-Instance assemblies, cloud cells); measured hardware data as Flux validation evidence; multi-region replication |
| 5 and later (proposed) | Large structures, aerospace certification | Certification evidence packages (for example DO-178C and DO-254 style traceability for software and hardware items [unverified scope]); program-scale effectivity across many end items; federation between primes and suppliers at scale |

## Open questions

1. **Shared result cache trust.** Is a 1% spot re-execution rate enough to bound the damage of a compromised CI worker, or should high-value results (release citations) always be re-executed on a second, independent worker?
2. **Hashing large values.** Is SHA-256 throughput adequate for 10 GB Fields on browsers without SHA instructions, or should Crucible add a BLAKE3 tree mode for derived values only, which never need FIPS approval?
3. **CRDT choice.** Loro's movable tree uses fractional indices with a known interleaving issue for siblings; does concurrent insertion of features between the same two siblings produce orders that people find wrong often enough to need a different sibling-order algorithm?
4. **Offline window.** Is 60 s the right boundary between CRDT auto-merge and merge-driver rejoin, or should it depend on whether a check changed outcome during the divergence?
5. **Geometric conflict false positives.** Do symmetric-difference regions flag too many conflicts on golden product 4, where welded members touch by design? The merge clearance may need per-mate exemptions.
6. **Revision letters and standards.** The skipped letters and revision rules need confirmation against ASME Y14.35 and customer-specific rules before phase 2.
7. **Item numbers in source.** Should the item number stay in Ingot source (the `item` argument of `part`), which makes a renumbering a Change, or live only in lifecycle records keyed by `EntityId` lineage?
8. **AS9100 and Part 11 validation.** Which third-party assessor and which validation package format customers expect; this affects phase 2 and 3 deliverables.
9. **End-to-end mode and Kiln sharing.** End-to-end mode prevents shared cloud caching of labelled results; is a customer-hosted cache tier inside the boundary the right answer?

## Contract change requests

1. **Cache key: package closure instead of the whole lockfile.** Contract section 5 says the `Op` cache key includes the "library lockfile". This tab keys features by the closure of packages they use plus the operation version pins (D-KLN-3), and operations by their own version. Keying on the whole lockfile invalidates every cached result whenever any package is added and prevents sharing std results between designs. Proposed wording: "Cache key = hash(operation and behavior version, input hashes, closure of pinned packages and operation versions the node uses, platform class)."
2. **Hardware CI on every commit.** Contract section 7 says "hardware CI on every commit". Physical tests take hours and consume material, so this tab runs hardware checks on every commit that changes their inputs and reuses valid results otherwise (D-KLN-35). Proposed wording: "hardware checks run on every commit that changes their inputs."
3. **Name for the memoized evaluation unit.** The glossary has no term for a memoized computation that is not an operation (a feature call, a check, a BOM view). This tab uses "node" and states its relation to `Op`; the contract could adopt "node" in section 5 so that other tabs stop using "query", which section 5 already assigns to provenance criteria.
4. **Determinism grades.** Contract section 5 defines `PlatformClass` only. This tab adds `DeterminismGrade` (`Portable`, `ClassExact`, `Certified`) per operation version to select the class; Flux proposes the class names `cpu-f64`, `wgpu-f32`, `cuda-f64` and `rocm-f64`. Proposed: add `DeterminismGrade` to section 5 and fix the class names in the Platform tab.
5. **Rename SBOM to "service BOM".** The contract uses SBOM for the service bill of materials, while CycloneDX (ECMA-424) and common security practice use SBOM for the software bill of materials, which Crucible also produces. Proposed: write "service BOM" in the contract and UI, and reserve no abbreviation for either; this tab follows the contract until the change is decided.

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

