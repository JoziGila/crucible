# Kiln, repository and PLM (KLN)

Kiln is Crucible's evaluation engine, and `repo`, `plm` and `trust` are the services that keep a design's history, its product records (Items, revisions, BOMs and change orders) and its signatures: Kiln re-runs only what an edit affects, every edit becomes an immutable Change on a cheap branch, and merged Changes become signed releases in the design's own repository. Where Onshape merges a branch tab by tab and cannot merge drawings, and enterprise PLM keeps lifecycle records in a system apart from the model, Crucible merges block by block, drawings included, refuses any merge that worsens a check, adds interference or edits one entity from both sides, and releases exactly the content its checks evaluated. One mechanism delivers both: source, results and signed records are objects in one content-addressed store (the CAS, where each object is named by the SHA-256 hash of its bytes), so a cached result, a merge verdict and an Approval (a person's signature) all name the same immutable content, on a laptop, a team server, the cloud or an air-gapped site.

## A bracket's life: edit, merge and release

This section follows the canonical bracket (contract 6) from one edit to a measured release, so that every later section has a place in one story.

### One edit

A designer drags the bracket's `width` handle from 60 mm to 80 mm. While the drag lasts, the new value is a literal override: an input to Kiln keyed by its `LiteralSite` (the call site plus the argument slot), not yet a change to the source text. Kiln holds the design as a graph of memoized nodes:

1. the front-end stage, which parses and type-checks `bracket.ingot` into the IIR, Ingot's intermediate representation;
2. the feature call `bracket(width, thickness, load)`;
3. the Ops inside it, each one call of a versioned operation: `extrude`, `rib`, the Boolean `+` and `fillet`;
4. the query resolutions `base.edge(role: end(outline.top))`, `base.face(role: start_cap)` and `web.face(role: end_cap)`;
5. the `static_stress` solve and the reduction `von_mises.max(over: study.regular())`;
6. the check named `static_margin`.

The source text did not change, so the front-end stage is not even consulted. Kiln re-runs the feature call and every Op downstream of `width`. The clamp face and the loaded face resolve to the same `EntityId`s as before, because entity names never depend on argument values (ANV), so the study's boundary conditions and the check keep their identities, their history and any Evidence records attached to them.

Had the designer instead edited the doc comment `/// L-bracket with a stiffening web.`, the front-end stage would re-run, produce an IIR equal to the old one, and stop there. Kiln calls this backdating: a recomputed node whose value is unchanged keeps its old change marker, so nothing downstream runs.

### Results by fidelity

Results stream back tagged with their fidelity (`Preview`, `Interactive` or `SignOff`, contract 2) and the other trust qualifiers of contract 5.2. Within 100 ms the drag shows the feature and the dependents that fit; within about a second an `Interactive` stress value arrives with an `Estimated` bound; `SignOff` follows in the background. Each fidelity is its own set of nodes, so a quick result never stands in for a final one.

When the drag ends, UIX writes the new default into the source through `edit.apply`, and `repo` records an immutable Change naming its parent, tree and author. Undo is one more Change; nothing is overwritten.

### A branch, a Proposal and a merge

Meanwhile an agent on its own branch adds a lightening hole to the web and opens a Proposal: a branch plus rationale and a CI report. The merge with `main` is clean only when the result compiles, no check gets worse, no new interference appears and neither side touched an entity the other modified. The width change and the hole touch different entities, so they merge clean; two fillets on one edge would be a geometric conflict naming that edge.

### A release

The bracket's Item number lives in source, as in `part(solid, name: "Bracket", item: "BRK-0101")`. To release revision A, an engineer opens a change order, a Proposal with lifecycle scope. `act.prepare` builds a release plan whose subject digests the Item's name-free definition, the verdicts and the cited records; the approver signs that digest, and `act.commit` writes the merge, signed tag and revision record in one transaction. A rebase that leaves the definition unchanged keeps the Approval; any change to what is made voids it.

Everything the release depended on is pinned in `ingot.lock`: every operation version, every package, the organization's policy packages and every Evidence record a check reads. One Change therefore fixes every outcome, on every machine, for as long as the records are kept.

### Measurement

The shop machines the bracket from the released STEP file, and an external lab's signed measurements arrive as Evidence records, which a bot Proposal pins against the checks they serve.

### How this tab is organized

The tab follows the three crate groups of contract 12.

- **Kiln and the CAS:** the graph, keys and memoization; scheduling, fidelity and budgets; derivatives; the shared cache and determinism; the store itself.
- **Repository and collaboration:** Changes and history; Proposals and merge; live sessions and offline work.
- **PLM and trust:** Items and revisions; BOMs, effectivity and where-used; change control; quality records and compliance; physical tests and Evidence records; signatures and approvals; identity, authorization and audit; labels and export control; data release to other organizations.

ING owns compilation and `CallSite`s, ANV and FLX own operations, PLT owns the determinism mechanisms of contract 7.3 and deployment, AGT owns the `api` catalog and agent safety, and ECO owns the registry, events delivery and connectors.

`ingot.lock` pins every version a design uses. Upgrading is an explicit Proposal that shows the geometric and metric diff, never a side effect of installing a new engine.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Pinned inputs and upgrade Proposals | `ingot.lock` pins operation versions, packages, policy packages, External inputs and Evidence records; upgrades are Proposals with diffs | An unknown or unreadable pin fails resolution with `repo/pin_unresolved` | KLN-O-EQUIV-1, KLN-O-XREF-1 | 0 |
| Incremental equals from-scratch | Any sequence of edits and upgrades gives the identities a cold build gives | None: a divergence is a defect the oracle reports | KLN-O-EQUIV-1 | 0 |

## Kiln: graph, keys and memoization

Kiln exists so that an edit costs only what it changes: it records what each computation read, keys it by content, and reuses it everywhere the same content appears.

### Graph model

Kiln evaluates a demand-driven graph of input cells and derived nodes, as Adapton does [Adapton]. Input cells hold what the outside world sets: source files, `ingot.lock` with its pins, packages, External inputs (supplier offers, regulation datasets, policy packages, Evidence records), configuration points and a request's literal overrides. Nodes are pure functions of what they read, recorded as they read it.

| Node kind | Key | Value |
| --- | --- | --- |
| Front-end stage | Source content hash, language behavior version, imported interface hashes; diagnostics add the compiler release (ING) | The IIR, named by its module code hash, with diagnostics as a separate output |
| Feature call | Code hashes of the modules used, argument identities, `CallSite`, overrides in its code, requested fidelity | Parts, Bodies, Fields or plain values, with `HistoryRecord`s |
| Op | `NodeKey` (contract 7.2); entity-naming Ops in two stages | Canonical outputs with `ErrorBudget`s, or a `Failure` |
| Query resolution | Query, input identities, `CallSite`, requested fidelity | Entities with Notes, or a `ResolveError` |
| Check | `CheckId`, predicate code, subject identities, pinned allowances and Evidence records, requested fidelity | `CheckOutcome` |
| Derived view | View kind, inputs, requested fidelity | A BOM, diff, traceability matrix or where-used result |

Ingot nodes carry the requested fidelity unchanged, and each operation version maps it to its own effective fidelity. An operation that ignores fidelity maps all three to one value, so its results are shared across fidelities; geometry operations map `Interactive` and `SignOff` to one effective fidelity, because Anvil certifies `Interactive` geometry in place (ANV).

Every node whose value carries `EntityId`s includes its `CallSite` in its key, so equal calls at different sites share only the geometric stage of their Ops. Checks read results and never feed them, so adding a `require` changes no other key. Kiln stores the erased forms of contract 5, `Value` and `DynField`.

**Decision D-KLN-1:** Kiln uses a suspending scheduler with dynamic dependency recording, verifying traces in memory and constructive traces in the shared cache.
*Why:* dynamic dependencies need a restarting or suspending scheduler, and suspending with constructive traces gives minimal, shareable rebuilds [Mokhov 2020].
*Rejected:* topological scheduling, which needs static dependencies; restarting, as Bazel does; deep constructive traces, as Nix uses, which lose early cutoff.

### Keys

A `NodeKey` is the SHA-256 of the items of contract 7.2 that apply to the node's kind, encoded as deterministic CBOR under the domain tag `crucible/nodekey/1`. Five rules govern what enters it.

1. **Two stages.** Entity-naming Ops key in contract 7.2's geometric and relabeling stages, Failures and Notes included. Designs that share a failing geometric stage each get fixes that name their own bindings.
2. **Class and random streams.** The class item is `CpuCanonical` for `Portable` and `Certified` results, even when a GPU assisted. `OpCx::rng` keys each stream by operation identity, argument values and input `GeometryId`s or name-free hashes, never by class, fidelity, `ObjectId`s of named values or `CallSite`s.
3. **Pinned data by identity.** Data a node reads (calibration tables, regulation datasets, supplier offers, policy allowances, Evidence records) enters its key by identity. The lockfile as a whole never does.
4. **Limits that change values.** A limit that can change a value, such as a `#[fuel]` set in source, enters the key. Organization ceilings never do; they act at admission.
5. **Overrides stay local.** A node's key includes the literal overrides whose `LiteralSite` lies in its own code, and results under overrides never enter the shared cache.

**Decision D-KLN-3:** Keys include the code hashes of the Ingot modules a node actually used plus the language behavior version, never the whole lockfile.
*Why:* a lockfile key invalidates every result when a package is added and prevents sharing std results across designs.
*Rejected:* the whole lockfile; the closure of every package the design depends on, which misses nothing but re-runs nodes when an unused module changes.

### Memo entries and backdating

A memo entry stores, per output, a value handle, a lazy identity and a `changed_at` generation, plus `verified_at`, the ordered dependencies read, the minimum input durability and a cost record. Durabilities follow Salsa [Salsa durability]: `High` for std, packages, Materials and catalog data, `Medium` for closed files and `Low` for open documents.

**Decision D-KLN-36:** A node has four kinds of output, each with its own `changed_at`: value, per-kind accumulators, metadata and label; metadata never backdates, and labels re-join from current inputs even when the value backdates.
*Why:* with one combined output, an edit that changes only a fuel figure would re-execute every dependent, and an input relabelled with unchanged bytes would never relabel what was derived from it.
*Rejected:* one combined value; labels stored inside the value.

Kiln verifies as Salsa does [Salsa algorithm]: a memo whose durability class saw no change revalidates in constant time, and an output equal to its old value keeps its `changed_at`, which is why a comment edit re-executes no feature.

**Decision D-KLN-5:** Early cutoff on the interactive path compares canonical values directly (−0.0 becomes +0.0; non-finite values are not canonical), and Kiln consults the shared cache only when an Op's estimated cost exceeds a key computation plus one lookup (default 200 ms).
*Why:* hashing a 100 MB mesh inside a 100 ms drag spends the whole budget, and non-canonical values would make results depend on what was evicted.
*Rejected:* hashing every value eagerly; an equality that distinguishes signed zeros.

A node's label is the join of its inputs' labels under contract 5.3, kept as its own memo output and recomputed locally on every shared-cache hit.

### Failures and Aborts

Kiln separates two ways a node can end without a value. A `Failure` is a property of the inputs: coplanar Boolean faces, a `ResolveError`, a diverged solve. Kiln memoizes it, Ingot's `try` catches it, and dependents see `DependencyFailed`. An Abort is a property of the Evaluation: cancellation, resource exhaustion, device or worker loss, an exhausted budget, or a depth or fuel limit (contract 2).

In Rust an operation returns `OpResult<T>`, a `Result<T, Stop>` whose `Stop` is either a `Failure` or an `Abort` (Reference). Calls inside an operation, such as `OpCx::safe_point` or PLT's `det_sum`, return `Result<_, Abort>`, and `?` lifts them into `Stop::Abort`. No conversion exists between `Failure` and `Abort`, so no code path can turn an environmental end into a cached fact, and Kiln memoizes only `Stop::Failure`.

**Decision D-KLN-6:** Failures are cached values; Aborts are invisible to Ingot, propagate to every transitive dependent and leave no memo entry, CAS object or attestation, and worker or device loss retries once elsewhere.
*Why:* cached Failures keep editing fast while a feature is broken, and a computation that ran out of memory on one machine must never become a cached fact on every machine.
*Rejected:* caching nothing that fails; one failure type with an environmental flag.

`OpVersionRetired` is the one `Failure` never memoized or shared, because it depends on the engine release, not the inputs. Failures render as `<family>/<snake_case>` (contract 7.6); this tab's families are `kiln`, `cas`, `repo`, `plm`, `trust`, `auth`, `label`, `evidence` and `share`, registered with AGT.

One catalog of limit outcomes in `base-op` serves every tab (Reference). Declared limits, such as a source's fuel, are Failures because they are part of the key; environmental limits, such as a budget or the demand depth (10,000 nested demands by default), are Aborts. A node that demands a node on its own active stack fails with `kiln/cycle` and the path of spans.

### The operation contract

Kiln knows no domain. Anvil, Flux and Ingot register node kinds through the operation contract in `base-op`, and the `engine` crate wires every registry into one `Kiln`; domain crates never depend on `kiln` (contract 12). An operation implements `OpImpl`: identity, behavior version, determinism grade, typed inputs, canonical outputs, a fidelity map, a cost model and `eval`. Kiln calls operations by name, so it holds them type-erased as `DynOp`, which a blanket implementation derives from every `OpImpl`.

**Decision D-KLN-56:** Kiln holds operations in an `OpRegistry` of `Arc<dyn DynOp>` keyed by (operation id, version), filled by explicit registration functions that each operation-family crate exports and that `engine` calls in a fixed order.
*Why:* `OpImpl` has associated types and constants, so it cannot be a trait object, and explicit lists make registration order, and therefore every registry listing, deterministic.
*Rejected:* link-time collection through the `inventory` crate (order depends on the linker); a type-erasure layer per consumer.

`OpCx` is what an operation may use: a safe point, a keyed random stream, a work budget, its effective fidelity and progress reporting, but no clock, ambient randomness or I/O.

**Decision D-KLN-57:** `OpCx` is an owned, cheaply cloned handle (`Arc` inside), `Send + Sync`, whose methods all take `&self`; cancellation is an atomic flag read by `safe_point`, due every 10 ms of monotonic time on the operation's thread, with the clock taken from `platform-api`'s `Monotonic`.
*Why:* PLT's pools move an `OpCx` into `'static` tasks and call it from parallel chunks that hold only shared references, and browsers cannot measure CPU time.
*Rejected:* a borrowed `&mut OpCx<'_>`, which no pool task can hold; a CPU-time cadence.

**Decision D-KLN-2:** The engine build never enters a key; registration records each released version's closure hash (contract 4) and refuses a version whose hash changed, and a toolchain or `detmath` upgrade passes golden-hash checks instead of minting versions.
*Why:* a build key would empty every cache at each release, and a Cargo-level hash over frozen directories and locked third-party versions catches changes to the code a version runs, while golden hashes cover the toolchain.
*Rejected:* the build id in every key; a corpus fingerprint as the only guard, which misses changes the corpus does not exercise.

ANV owns operation version freezing and its CI cadence; Kiln owns registration.

**Decision D-KLN-4:** A pinned operation version is never substituted: retired versions run in archived engine builds compiled to Wasm through the frozen world `crucible:archive/op@1`, and a version without a Wasm build (a GPU `ClassExact` path) fails with `OpVersionRetired`.
*Why:* old designs must rebuild identically without old engines, and a substitute version would change released geometry silently.
*Rejected:* falling back to the newest version; caching `OpVersionRetired`.

The archive world exports one `eval` over CAS object ids and imports only CAS reads, a safe point, a random block and progress (Reference). Every engine release keeps decoders for each encoding version an archived engine can emit.

Wasm components receive ING's guest context instead of `OpCx`. KLN owns the `crucible:host` package they import beside `crucible:ops`: write-only `diagnostics` and `progress`; `cas`, which reads only objects reachable from the call's input handles and records each read as a dependency; and `parallel`, a deterministic map that PLT implements. MEC owns `crucible:product`, which returns this tab's Item and BOM records.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Memoized evaluation with backdating | `Kiln::demand(EvalRequest) -> ResultStream`; equal outputs keep `changed_at` | None: typed `Failure`s are memoized values | KLN-O-MIN-1 | 0 |
| Durabilities | `High`, `Medium`, `Low` inputs; constant-time revalidation | None: an unchanged durability class revalidates, others verify dependencies | KLN-O-MIN-1 | 0 |
| Site-keyed and two-stage nodes | `CallSite` in keys; geometric stage for values, Failures and Notes | `kiln/entity_id_collision`, unreachable by construction and reported as a defect | KLN-O-SITE-1 | 0 |
| Requested fidelity in Ingot node keys | Feature calls, query resolutions, checks and derived views key by requested fidelity; operations map to effective fidelity | None: every request carries a fidelity | KLN-O-PROG-1 | 0 |
| Literal overrides | In keys of nodes holding the `LiteralSite`; never shared | None: an override that names no site is rejected by `api` as `edit/unknown_site` | KLN-O-PROG-1 | 1 |
| Multi-output memo entries | Value, accumulator, metadata and label outputs | None: each output verifies independently | KLN-O-MIN-1 | 0 |
| Canonical round trip | decode(encode(v)) = v for every output; erased `Value` and `DynField` | Non-canonical outputs fail registration | KLN-O-ROUNDTRIP-1 | 0 |
| Label propagation | Join per node under contract 5.3; shared-cache hits return values only | `label/write_down` at `api` | KLN-O-LABEL-1 | 1 |
| Failures and Aborts | `OpResult`, `Stop`; `Failure` cached; Abort uncached; no conversion between them | Abort reported with its cause | KLN-O-ABORT-1, KLN-O-ABORT-2 | 0 |
| Limit outcomes | One catalog; demand depth; fuel governor; ceilings at admission | The catalog's outcomes | KLN-O-LIMIT-1 | 0 |
| Operation contract and registry | `OpImpl`, `DynOp`, `OpRegistry`, `OpCx` in `base-op`; explicit registration lists | Missing grade, cost model or fidelity map fails registration | KLN-O-FPRINT-1 | 0 |
| Closure hashes at registration | Recorded per released version; golden hashes gate toolchain and `detmath` upgrades | A changed closure hash is refused with `kiln/closure_changed` | KLN-O-FPRINT-1 | 0 |
| Retired versions | `crucible:archive/op@1`; decoders for every archived encoding | `OpVersionRetired`, never cached | KLN-O-RETIRE-1 | 1 |
| `crucible:host` | Write-only diagnostics and progress; handle-scoped CAS reads; `parallel` with `chunk-worker` | `kiln/unreachable_handle` | KLN-O-WIT-1 | 1 |

## Kiln: scheduling, fidelity and budgets

A person dragging a handle, an agent running a study and a nightly regression all share one engine, so Kiln decides who runs first, how results arrive, and what each request may spend.

### Scheduling and cancellation

Scheduling never changes a result: nodes share no mutable state, concurrent demands of one node share one execution, and collections such as diagnostics merge in canonical order. Kiln picks PLT's `PoolLane` from the request's `PriorityClass` (AGT).

| Priority class | Demand source | Pool lane | Preempted by |
| --- | --- | --- | --- |
| `Drag` | A drag, edit stream or per-pointer tool | `Drag` | Nothing |
| `Foreground` | A person waiting: viewport, selection, own rebuild | `Foreground` | Drags, at node boundaries |
| `Agent` | Agent sessions | `Background` | Both above, at node boundaries |
| `Ci` | Proposal CI, merge queue, releases | `Background` | Both above |
| `Batch` | Explorations, benchmarks, prefetch, background `SignOff` | `Background` | All; resumes from cached nodes |

An awaited background node is promoted to its waiter's class. The drag lane serves AGT's `evaluate.subscribe` and `edit.stream` with one request in flight and one pending. Within 100 ms it recomputes the dragged feature plus the dependents that fit an 80 ms estimate; later dependents show as `Proxy` where the change is affine on them, otherwise `Stale` (contract 13.3).

A node runs only while demanded, and a new generation cancels in-flight nodes whose reads changed. Native operations call `OpCx::safe_point`, Wasm stops at fuel checks, and GPU dispatches follow PLT's rule. Without shared memory, Kiln runs every Op estimated above 100 ms in a disposable worker and cancels it by terminating the worker (contract 7.4).

### Memory and eviction

Values are immutable, reference-counted buffers, large ones memory-mapped from the local CAS. An evicted value keeps its memo metadata, and values on screen or feeding running nodes are pinned.

**Decision D-KLN-7:** Kiln evicts by GreedyDual-Size: each access sets `H = L + cost / size`, cost being the cheaper of recomputing and reloading, and eviction takes the lowest `H` and raises the inflation value `L` to it.
*Why:* it weighs recency, cost and size without tuning, and CAD values span nine orders of magnitude in both [Cao 1997].
*Rejected:* plain LRU, which evicts an hour-long solve to keep cheap sketches.

Kiln writes its memo table (edges and identities, not values) to the local CAS every 60 s and on exit, so a restart revalidates instead of recomputing.

### Progressive results

| Fidelity | Geometry (ANV) | Physics (FLX) | Shared cache |
| --- | --- | --- | --- |
| `Preview` | Surrogates and looser tolerances | Reduced or surrogate solves, `Indicator` bounds | Never written |
| `Interactive` | Filtered decisions equal to `SignOff`'s; traced from canonical start points | Calibrated `Estimated` bounds | Written; never used by `SignOff` checks or releases |
| `SignOff` | The `Interactive` result, confirmed bit for bit by certification nodes; recomputed only if certification fails | `Guaranteed` where proven, else calibrated `Estimated`, confirmed by one refinement | Used after two-builder agreement |

A subscription names targets, a fidelity ceiling, overrides and a priority. Kiln streams `ResultEvent`s carrying generation, fidelity, `ResultStatus`, value or `Failure`, budget and label. A published frame holds one generation, and older results appear only as `Stale`.

An outcome below a check's declared fidelity (default `SignOff`) is provisional and never counts for CI, Proposals or releases. Control flow on `Undecided` follows ING's decision rule (contract 5.1): the value `Undecided { needed, fidelity }` is cached whatever the ceiling, and the ceiling changes only reporting, raising `ing/6401` at the ceiling.

**Decision D-KLN-8:** Progressive refinement is a set of independent nodes keyed by requested fidelity, never a stateful process; geometry certified in place shares one node for `Interactive` and `SignOff`.
*Why:* each tier is then cacheable, cancellable and shareable, a lower-fidelity result can never answer a `SignOff` demand, and certified geometry lets meshes and solves downstream be reused across fidelities.
*Rejected:* in-place refinement of one value, which the key cannot see; separate `SignOff` geometry, which doubles every downstream node.

A release demands every node at `SignOff`.

### Cost and budgets

Every node records CPU and GPU time, memory, bytes moved and remote price, attributed to principal, branch and Proposal. Before running, Kiln returns a priced upper bound from per-operation cost models, which `api` reserves against AGT's `Budget`; an estimate above what remains fails with `budget/exceeded` and cheaper options.

An Op estimated above 10 core-seconds gets a work budget from the reservation and reaches a safe point at least every 10 core-seconds of work. Exhausting it is the Abort `BudgetExhausted`, reported with the last safe point reached; the budget never enters a key.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Priority classes | `PriorityClass` `Drag`, `Foreground`, `Agent`, `Ci`, `Batch`; promotion of awaited nodes | None: every request has a class, `Foreground` by default | KLN-O-SIM-1 | 0 |
| Drag lane | PLT's `Drag` lane; dependents fitted to 80 ms | Later dependents shown as `Proxy` or `Stale` | KLN-O-PROG-1 | 1 |
| Cancellation | `OpCx::safe_point` on monotonic time; fuel checks; disposable workers without shared memory | The Abort `Cancelled`, with no memo entry or CAS write | KLN-O-CANCEL-1 | 0 |
| Eviction | GreedyDual-Size; persisted memo table | None: an evicted value is reloaded or recomputed | KLN-O-EVICT-1 | 1 |
| Progressive results | `ResultEvent`; one generation per frame; ceiling-free `Undecided`; one geometry node for `Interactive` and `SignOff` | `Stale`; `Pending` while a higher fidelity runs | KLN-O-PROG-1 | 1 |
| Budgets | Priced bound reserved; safe points every 10 core-seconds | `budget/exceeded`; the Abort `BudgetExhausted` | KLN-O-BUDGET-1 | 1 |

## Derivatives

ING's `grad`, FLX's adjoints and topology optimization chain derivatives across features, so Kiln keeps the one recorded graph they need (contract 7.1).

An operation that can be differentiated implements `Differentiable` beside `OpImpl`, with `tangent` and `adjoint` methods that return `OpResult` like `eval`. Forward mode composes tangents along the recorded graph. Reverse mode walks a scalar goal's dependencies in reverse topological order, calls each `adjoint` once and sums cotangents in canonical order. An Op without `Differentiable` fails with `kiln/not_differentiable` naming the operation. Derivative nodes are keyed by the primal key plus the goal's, so a change to the objective alone reuses every primal result.

Transient solves save their step checkpoints as CAS objects keyed by (`NodeKey`, step) in the `Checkpoint` retention tier, which eviction drops first. A resumed solve or adjoint is bit-identical whether its checkpoints were kept, reloaded or recomputed.

**Decision D-KLN-37:** Derivatives are a Kiln traversal over `Differentiable` operations, with step checkpoints in their own retention tier.
*Why:* adjoints that cross features need one recorded graph, and checkpoints that are cheap to recompute must yield memory to ordinary values.
*Rejected:* a tape per engine, which cannot chain through features; checkpoints stored as ordinary values.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `Differentiable` operations | `tangent`, `adjoint` in `base-op`, returning `OpResult` | `kiln/not_differentiable` | KLN-O-DERIV-1 | 0 |
| Reverse traversal | From a scalar goal; canonical sums | Aborts propagate; no partial gradient is cached | KLN-O-DERIV-1 | 1 |
| Step checkpoints | `Checkpoint` retention tier keyed by (`NodeKey`, step) | None: an evicted checkpoint is recomputed | KLN-O-DERIV-1 | 1 |

## Shared cache, remote evaluation and determinism

A result computed once should serve every engineer, agent and CI run that asks for the same content, so Kiln shares results across machines, and this section says when a shared result can be trusted.

### One engine everywhere

Kiln runs the same engine on desktops, in browsers, on team servers and on cloud workers. Workers advertise their classes, operation versions, region and price, and Kiln offloads a node when transfer plus remote time beats local time. Its remote protocol is its own, because Bazel's Remote Execution API models command lines over file trees [Bazel REAPI].

### Who may write the shared cache

Contract 7.8 fixes four roles (Reference): untrusted-evaluation workers in single-use microVMs, trusted builders for merged protected Changes, the attestation service that alone holds signing keys (KLN's, packaged by PLT), and the operator's registry builders.

Each use has one rule. Release gates and every `SignOff` check accept a cached result only when two independent trusted builders produced the same `ObjectId`; otherwise they recompute. Every other shared-cache hit is spot re-executed at a rate weighted by its downstream fan-out, and every released revision is re-verified in full after a toolchain or `detmath` upgrade. A mismatch quarantines the attestation and opens a determinism incident.

Agreement guards against faults, not a deterministic exploit, so a node whose closure holds third-party code is attested only into its own tenant's domain. An External Op result meets a gate when two single-use runs agree in signed execution receipts; otherwise it stays `Unverified` and counts only under a pinned policy allowance.

**Decision D-KLN-9:** Only trusted builders evaluating merged protected Changes produce attestations, signed by a separate service; untrusted and third-party code runs in single-use microVMs; third-party closures are attested per tenant; gates and `SignOff` checks require two-builder agreement, and other hits are spot-checked by fan-out.
*Why:* runners that execute agent Proposals must never hold a signing key, one deterministic escape would otherwise compromise every builder that runs the package, and one rule per use avoids running every released node three times.
*Rejected:* trusting machines instead of their inputs; OS-process sandboxes as an attestation boundary; full re-execution of every hit that feeds a release.

### Placement and the single host

On servers each worker process serves one (tenant, confidentiality label) pair, and labels with `controls` get dedicated VMs. Placement calls `base`'s `PlacementPolicy`, which `trust` implements, and refuses a region or operator outside the label's terms with `label/residency_denied`.

In phase 1 the single-node team server is the only trusted builder, so gates recompute, and each release records "single host" (contract 7.8). It runs Proposal CI in Firecracker where KVM exists [Firecracker start] and in gVisor otherwise, refuses Proposal CI when neither works, and runs the trusted builder as a separate OS user.

### Determinism: which results a gate accepts

Contract 7.3 defines grades and classes, and PLT owns the mechanisms, such as `detmath` [CORE-MATH] and binned summation [ReproBLAS]. This section owns which results a gate accepts.

| Result | Grade or form required | Accepted by release gates |
| --- | --- | --- |
| Geometry and oracle reference results | `Portable` or `Certified`, keyed `CpuCanonical` | Yes |
| Flux `SignOff` results | `Portable`, `Certified`, or a witness: a pinned non-canonical Field whose residual and bound are computed canonically | Yes, pinned by `ObjectId` |
| `Interactive` results and `CpuIsa` variants with FMA | Any grade, keyed by class | No; `SignOff` recomputes canonically |
| External Op results | The host's class, or `Unverified` | When two runs agree, pinned by `ObjectId`; `Unverified` only under an allowance |

**Decision D-KLN-10:** `Portable` means bit-identical across `CpuCanonical { epoch }` (every Tier 1 CPU target and browser at any thread count and ISA level) and is the only grade for geometry and oracle reference results.
*Why:* a cache shared by every operating system, browser and cloud worker needs the same bits from each.
*Rejected:* one class per operating system and architecture, which would split the cache about eightfold.

**Decision D-KLN-11:** Kiln accepts at a release gate only the forms in the table above, and records in the release the platform class or witness of every result it cites.
*Why:* one Change must give one gate outcome on every builder, and an auditor must be able to re-derive each cited result.
*Rejected:* accepting `CpuIsa` or `Gpu` results that agree with canonical ones within a tolerance, which makes the gate depend on which machine ran first.

**Decision D-KLN-12:** A check may rest on a GPU-computed Field only as a witness: Kiln keys the Field by its `Gpu` class, pins its `ObjectId`, and evaluates the residual, the error bound and the check canonically from it.
*Why:* re-solving every GPU result on the CPU would erase the GPU's benefit, while a canonical residual makes the check reproducible though the Field is not.
*Rejected:* re-running every GPU solve canonically before a check; trusting GPU results by tolerance.

**Decision D-KLN-13:** A request that pins no class gets the class of an existing cached result, else the local one, and CI pins one class per repository.
*Why:* interactive work should reuse whatever is already computed, while CI must not flap between classes from run to run.
*Rejected:* always computing in the canonical class, which slows interactive work; a free choice per CI request.

The determinism suite also perturbs threads, allocator, hash seeds and cancellation. Kiln, sync, the collector and the server run under seeded deterministic simulation, as FoundationDB does [FoundationDB testing]: 1,000 simulated hours per night in phase 0 and 10,000 by phase 2 (targets).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Remote evaluation | Worker advertisement; cost-based placement | Worker loss is the Abort `WorkerLost`, retried once | KLN-O-REMOTE-1 | 1 (team server), 2 (cloud) |
| Worker pools and attestation | Contract 7.8 roles; microVMs; per-tenant attestation of third-party closures | Untrusted entries ignored; `trust/attestation_invalid` | KLN-O-TRUST-1 | 2 |
| Two-builder agreement | Same `ObjectId` from two trusted hosts for gates and `SignOff` checks | None: without agreement the gate recomputes | KLN-O-TRUST-1 | 2 |
| External Op receipts | Two agreeing single-use runs | Results stay `Unverified` | KLN-O-TRUST-1 | 2 |
| Fan-out-weighted spot checks | Weighted by fan-out; full re-verification of released revisions after toolchain or `detmath` upgrades | Quarantine and a determinism incident | KLN-O-TRUST-1 | 2 |
| Label-aware placement | `PlacementPolicy`; one process per (tenant, label) | `label/residency_denied` | KLN-O-LABEL-1 | 2 |
| Single-host team server | Signing service bound to the trusted-builder process; Firecracker or gVisor; separate builder user | Proposal CI refused with `kiln/no_sandbox` when no back end works | KLN-O-DEPLOY-2 | 1 |
| Determinism grades | Grade per operation version | An undeclared grade fails registration | KLN-O-DET-1 | 0 |
| Release acceptance | The acceptance table; witnesses pinned; classes recorded | Non-canonical inputs recomputed before the gate | KLN-O-DET-1 | 1 |
| Determinism suite | Every merge on the representative set; nightly elsewhere | A severity-1 incident; beta promotion blocked | KLN-O-DET-1 | 0 |
| Deterministic simulation | Seeded order, time, network and faults | Failing seeds replay | KLN-O-SIM-1 | 0 |

## The CAS

Every source file, result, record and signature is stored once, named by its content, so identity, deduplication, caching and verification all rest on one rule.

### Object model

The CAS holds four kinds of object (Reference): opaque `Blob`s, deterministic CBOR `Record`s, `Segmented` large typed arrays and `Index` nodes that list children.

Records use RFC 8949's core deterministic encoding [RFC 8949], one canonical quiet NaN and NFC text; large numeric arrays are little-endian typed arrays. An `ObjectId` is `SHA-256(domain tag ‖ type tag ‖ canonical bytes)` behind a one-byte algorithm code, computed before compression and encryption, so storage tiers may recompress or re-encrypt freely. A large value's identity is its root `Index` node's.

Producers emit canonical forms, because equal values need not have equal encodings. Bodies also carry the name-free `GeometryId` (contract 5.5).

### Hashing, chunking and compression

**Decision D-KLN-14:** The CAS identity hash is SHA-256, with a one-byte algorithm code reserved for migration.
*Why:* SHA-256 is approved under FIPS 180-4 [NIST hash functions] and is the digest of RFC 6962 logs, C2SP tiles and Git's SHA-256 object format, and Git's transition shows the cost of a hash without an agility field [Git hash transition].
*Rejected:* BLAKE3, which is not NIST-approved and whose speed chunk-parallel SHA-256 mostly recovers; SHA-3, which is slower in software.

**Decision D-KLN-46:** Derived values use the same hash as every other object, and a browser that misses the hashing target gets a relaxed target, never a second algorithm.
*Why:* a second hash would give one value two `ObjectId`s across deduplication and two-builder agreement.
*Rejected:* BLAKE3's tree mode for derived values.

BLAKE3's authors call `b3sum` "an order of magnitude faster" than `sha256sum` [BLAKE3], so Crucible hashes chunks in parallel and off the interactive path. Browsers hash chunks of at most 1 MiB with `crypto.subtle.digest`, which takes no streaming input [MDN digest]. Targets: 1 GiB in under 150 ms natively on the reference laptop and under 1 s in a browser with 8 workers.

**Decision D-KLN-15:** Chunking is structure-aware: segmented values split into typed segments keyed by geometric content or space, never by names, grouped by a content-defined rule over their keys as in a prolly tree, and opaque Blobs use FastCDC; each type tag's chunking rule freezes at the phase 1 gate, and a later rule is a new type tag that only new operation versions emit.
*Why:* byte-level chunking shifts every boundary when vertices renumber, FastCDC is about 10× faster than the best open-source Rabin chunker at nearly equal deduplication [Xia 2016], and a large value's identity depends on its chunking, so changing a rule after releases exist would change every stored identity.
*Rejected:* fixed-size chunks; `EntityId` segment keys, which re-chunk geometry on a rename; chunking rules that may change in place.

A chunk ends after a segment whose key hash falls below a threshold (about 64 KiB chunks), and `Index` nodes hold up to 512 children [Dolt prolly trees]; the Reference section lists the segment key of each value kind. Gregoriadis and colleagues found no impartial comparison of chunking algorithms before their 2024 study [Gregoriadis 2024], so phase 1 benchmarks the alternatives on Crucible data before the rules freeze.

**Decision D-KLN-16:** Each stored chunk names its codec: Fields use byte shuffling plus zstd, with pcodec measured as an alternative, other chunks use zstd (level 3 hot, 19 archived), and display meshes travel with meshoptimizer's lossless vertex codec.
*Why:* named codecs admit better ones without a format break, and pcodec's authors chart better ratios than zstd on numeric data [pcodec].
*Rejected:* one codec for everything; lossy quantization in storage, which would change identities.

A reader that does not know a chunk's codec fails with `cas/unknown_codec`; every codec in use decodes in every Tier 1 build.

### Encryption at rest

Desktops encrypt labelled repositories under OS-keystore or non-extractable WebCrypto keys; servers use envelope encryption under KMS or HSM keys. An encryption domain is one tenant and one canonical confidentiality label; usage and integrity never split domains. An object's key is `HKDF-SHA-256(domain key, ObjectId)` [RFC 5869], chunks are sealed with AES-256-GCM under random 96-bit nonces [NIST SP 800-38D], and the storage name is `HMAC-SHA-256(domain key, ObjectId)`, so plaintext `ObjectId`s never leave the domain's principals.

**Decision D-KLN-17:** Deduplication happens only within an encryption domain, with keys derived from a domain secret.
*Why:* convergent encryption lets anyone confirm a guessed file, DupLESS shows that the remedy is a secret held by the authorized side [Bellare 2013], and GCM and extract-then-expand key derivation are NIST-specified [NIST SP 800-56C].
*Rejected:* deduplication across tenants, which reveals which designs exist.

Deleting a domain key purges a contaminated label, subject to retention locks.

### Collection, tiers and replication

Source history is never collected; derived values are cache. Roots are refs, the transaction log, releases with their cited results, open Proposals, legal holds and in-flight uploads. Writers upload objects before updating a ref and take 24-hour leases, and the collector sweeps unmarked, unleased objects older than 48 h.

**Decision D-KLN-18:** Removing source history requires a purge: a record signed by two people, listing the removed `ObjectId`s and the authority, which verification treats as known-missing; a record under a retention lock is purged before its retention ends only when the same two signers also release the lock with its legal basis.
*Why:* spills and court orders require deletion, while 21 CFR Part 11 requires records to stay retrievable throughout retention [21 CFR 11.10].
*Rejected:* history rewriting, which breaks signatures; purges by one administrator.

Four tiers hold objects (Reference): process memory, local disk or OPFS, the team server or cloud region, and archive storage for releases. Refs and the transaction log live in SQLite on desktops and single-node team servers, PostgreSQL on larger team servers and FoundationDB in the cloud. Ref updates are compare-and-swap transactions, or conditional writes on object storage [S3 conditional writes]. Cloud regions keep three synchronous metadata copies and reconcile tiers by range-based set reconciliation [Meyer 2022].

In a browser, Kiln and `repo` run only in the engine that PLT's one-engine-per-origin rule designates, because OPFS sync access handles lock per file [MDN sync access handle] and SQLite's `opfs-sahpool` fails in a second tab [SQLite Wasm persistence].

**Decision D-KLN-44:** In a browser, the designated engine holds the journal, the SQLite store and every CAS pack except a heavy worker's pack in transfer, which it adopts by index; any new owner, a recycled engine worker included, replays the journal first.
*Why:* two engines writing one origin's store would corrupt it, and a heavy worker must hand its results over without a second writer.
*Rejected:* one engine per tab; heavy workers writing the engine's packs.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Put and get by `ObjectId` | `CasStore` (Reference) | `cas/corrupt`, healed from another tier and quarantined | KLN-O-CAS-1 | 0 |
| Hashing | SHA-256 per chunk; `crypto.subtle` in browsers | None: a hash always computes; slow targets are reported, not failed | KLN-O-CAS-4 | 0 |
| Structure-aware chunking | Name-free segment keys; FastCDC for Blobs; rules frozen per type tag at the phase 1 gate | None: an unkeyed value falls back to FastCDC | KLN-O-CAS-4 | 1 |
| Per-chunk codecs | Codec named per chunk | `cas/unknown_codec` | KLN-O-CAS-1 | 1 |
| Encryption domains | Tenant and confidentiality label; KMS or HSM keys | `cas/key_unavailable` | KLN-O-CAS-3 | 2 |
| Collection | Mark, lease, sweep | `cas/inconsistent`; the collector stops | KLN-O-CAS-2 | 1 |
| Purge and retention locks | Two-person purge; locks with a basis | `trust/retention_locked` | KLN-O-PURGE-1 | 2 |
| Tier replication | Residency-aware range reconciliation; three synchronous metadata copies | Residency violations blocked with `label/residency_denied` | KLN-O-REPL-1, KLN-O-DEPLOY-3 | 2 |
| Browser engine ownership | One engine per origin; journal replay; pack adoption | A second engine refuses to start with `kiln/engine_owned` | KLN-O-DEPLOY-1 | 1 |

## Changes and history

`repo` keeps every state of a design that anyone saw, so a reviewer, an auditor or an agent can inspect, diff or branch from any of them without a manual commit step.

### Changes and refs

A `Change` names its parents, its source tree, its author and the principal it acted for; trees, source files, tags, ref transactions, review records and lifecycle records are its companions (Reference).

Evaluation never reads time or authorship, and adding a signature or a timestamp never changes an identity (contract 7.8).

**Decision D-KLN-19:** Edits become immutable Changes, as Onshape's microversions do [Onshape API intro]: one per completed GUI action, per `edit.apply`, after 2 s without typing, at least every 60 s of editing, and whenever something references the current state.
*Why:* anyone can then inspect, diff or branch from any state without a manual step.
*Rejected:* explicit commits only, which lose states reviewers need; one Change per keystroke.

Refs are branch heads (`branches/<name>`), immutable tags (`tags/<name>`), Proposal heads (`proposals/<id>`) and agent branches (`agents/<agent>/<branch>`). Personal views and layouts live in a per-user store outside Changes (UIX).

**Decision D-KLN-20:** Ref updates are recorded in a transaction log, as in Jujutsu [Jujutsu concurrency]: each `RefTransaction` names its predecessors and the full resulting view of refs, concurrent transactions merge three ways, and a ref moved two ways becomes a conflicted ref.
*Why:* full views give lock-free sync, make undoing any repository action one transaction, and double as the audit trail.
*Rejected:* Git-style reflogs, which live in each clone; server locks, which break offline work.

### Git export

Git is an export, not the storage format. `crucible export git` writes Ingot text and `ingot.lock`, and because `CallSite`s derive from text alone, re-importing leaves every `EntityId` unchanged.

### Span provenance

Each source span records the integrity of the context that wrote it, and merges, rebases and moves preserve it. A span is trusted only when a person typed it in Crucible's own editor or the compiler produced it. Spans that arrive through a language-server connection, a file or Git import, or any other channel are `data_untrusted` until the user confirms the batch on the approval origin (contract 7.1), because a language-server edit cannot tell a keystroke from an editor extension's write.

How integrity flows from spans into values is contract 5.3's rule, stated once there: merging clears integrity on typed values, never on free text, and text evaluated from an untrusted span is an `ExternalText` value carrying that span's integrity. `read` methods return such values as handles. Free text becomes trusted only through `propose.endorse_text`, a signature record naming the span's bytes, which contract 5.4 governs; injected instructions in comments and names are the attack this defends against [Debenedetti 2025].

Only the server that witnessed a write asserts its integrity. Spans arriving through archive import or federation keep their integrity only when the witnessing server signed their span-integrity record and the receiving domain trusts that server; otherwise they are `data_untrusted`, and their free text also `instruction_tainted`.

### References across repositories

References to packages, catalog parts and other repositories are pinned in `ingot.lock` as `{ source, selector, resolved }`, where a selector is a release tag, a `ChangeId`, a followed branch or a derived view. MEC's context pins, which let a part be designed against a past state of its assembly, are entries of this kind whose selector is a `ChangeId` in the same repository. A reference whose source the reader cannot read resolves to its derived view for holders of `read_derived`, and otherwise fails with `repo/access_denied`.

Partial clones name a filter (`source-only`, `paths(<pattern>)`, `depth(<n>)`, `display(<lod>)`) and fetch missing objects in batches, as Git's promisor remotes do [Git partial clone]. The phase 4 target is a cold partial clone of 100,000 Instances of 10,000 Parts to an interactive view in 15 s over 100 Mbit/s.

### The `api` surface and events

AGT owns the method catalog; this tab supplies the repository behavior behind contract 7.6's eight groups, and every response carries its `ChangeId`, generation and labels. The Reference section lists the methods and event types.

**Decision D-KLN-34:** Events carry identifiers and states, never design content, and for any label above `public` they carry per-subscription opaque ids (an HMAC of the `ObjectId` under the subscription's key); ECO owns the CloudEvents envelope and delivery, this tab defines repository, lifecycle and evaluation event types and a per-repository `sequence` attribute [CloudEvents sequence], and AGT defines the `act.*` and `session.*` types.
*Why:* thin events keep policy and audit in one place, and webhook receivers are often third parties, for whom even a small `internal` record's `ObjectId` would confirm a guessed value.
*Rejected:* full payloads, which bypass policy; raw `ObjectId`s for `internal` content.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Changes and transaction log | `Repo::record`, `update_ref`, `edit.undo` | Conflicted refs, resolved by a later transaction | KLN-O-SIM-1 | 0 |
| Git export | Ingot text and `ingot.lock`; identities unchanged on re-import | `repo/export_unrepresentable` for content Git cannot hold, such as an unresolved conflict | KLN-O-GIT-1 | 1 |
| Span integrity provenance | Per-span integrity; trusted only from Crucible's editor or the compiler; confirmed batches; witnessed integrity records; endorsement | Untrusted text returned as `ExternalText` handles | KLN-O-SPAN-1 | 1 |
| Cross-repository references | Pinned `{ source, selector, resolved }`; context pins; derived views for unreadable sources | `repo/access_denied`, `repo/ref_missing` | KLN-O-XREF-1 | 2 |
| Partial clone | Clone filters; batched fetch | `repo/not_local` | KLN-O-LARGE-1 | 2 |
| `api` methods | Eight groups; labels on every response; edit stream and subscriptions | Denials name the permission | KLN-O-API-1 | 1 |
| Events | Event types; opaque ids above `public`; ECO's envelope | Retries, then a dead letter | KLN-O-EVENT-1 | 1 |

## Proposals and merge

Branches are only useful if merging them is safe, so `repo` merges by the meaning of a design, not its bytes, and refuses a merge that would quietly break the product.

### What a clean merge means

CI evaluates a Proposal's head and its would-be merge on untrusted-evaluation workers, and protected branches merge through a merge queue. Contract 7.1 states the conditions; `repo` checks them in this order, and each failure is a typed conflict.

1. **Source.** Files merge three ways over their block trees, matched by block id, or by GumTree for files edited outside Crucible. Child order merges by parent–child–successor triples, as Mergiraf does [Mergiraf], sets merge as sets, and other text merges on tokens. Sketch seeds are ordinary literals (MEC), so concurrent seeds of one sketch conflict. `ingot.lock` merges per entry, and two different pins of one package conflict.
2. **Compilation and resolution.** A compile or `Query` failure that neither parent has is `Conflict::Semantic`.
3. **Verdicts.** No check's verdict on the merge, matched by `CheckId`, is worse than on each parent that defines it (`Pass` > `Undecided` > `Fail` > `Error`). Protected branches compare at each check's declared fidelity and other branches at `Interactive`; a worse verdict is `Conflict::Check`.
4. **No new interference.** A `Hard` interference (positive volume, in MEC's classes) between Instances that neither parent has is `Conflict::Interference`.
5. **No touched-entity conflict.** A side's touched set is the base entities that an Op whose key differs from the base's split, merged, deleted, or modified in boundary or attributes; geometry-only parameter edits are excluded. Intersecting touched sets, or a created entity that meets the other side's touched set (certified distance zero, or below an optional merge clearance), give `Conflict::Geometric`.
6. **Connectivity.** A merged net that unions nets distinct in the base and on each side, whether circuit nets, harness connections or `std::systems` interfaces, is `Conflict::NetMerge`; renamed nets match by provenance.

Contact that a mate, a `Weld` record, a fastened joint, `IntendedThread` or `IntendedFit` explains never conflicts under the interference and touched-entity conditions. Symmetric-difference regions appear in review but never block.

**Decision D-KLN-21:** A merge is clean only when the merged design compiles and resolves, keeps every check's verdict, adds no unexplained interference, and has no touched-entity or connectivity conflict.
*Why:* a text merge that compiles can still break a part or short two nets, and touched sets let a width change beside a new hole merge clean while two fillets on one edge conflict.
*Rejected:* line-based merge; any overlap of changed regions as a conflict; flagging designed contact.

This is where Crucible is furthest ahead of incumbent CAD. Onshape merges per tab by Keep, Merge or Replace, cannot select individual changes within a tab, cannot merge a drawing, and warns only that changes from different branches can be incompatible [Onshape merging]. Crucible merges per block, drawings included, and reports exactly which check, Instance pair, entity or net blocks a merge.

Conflicts are first-class, as in Jujutsu [Jujutsu conflicts]. A conflicted block holds the base and side alternatives, simplifies when rebased, and evaluates as a `Failure` with three fixes: take one side, take the other, or edit. Several merge bases merge into one virtual base, as Git's `ort` strategy merges common ancestors into a reference tree [Git merge strategies]. The `MergeDriver` trait and the `Conflict` enum are in the Reference section; live sessions use the same driver.

### Diffs

Review needs to show what changed in terms a reviewer of each discipline reads.

| Diff | Content | Matching |
| --- | --- | --- |
| Source | Block insertions, deletions, moves, token edits | Block id, else GumTree |
| Feature | Features added, removed, moved; parameter deltas with units | Feature block |
| Geometry | Changed regions per Part; volume, mass and bounding-box deltas; Hausdorff distance with its bound | `EntityId` provenance, then geometry |
| Metric | Every check's value and margin before and after | `CheckId` |
| Schematic and layout (ELX) | Symbols moved, wires whose net membership changed, per-layer copper differences | ELX's net partitions and layout data |
| BOM and lifecycle | Items added, removed or re-revised; quantity, effectivity, state and compliance changes | Item number and record identity |

Diffs are Kiln nodes, so source and feature diffs appear in milliseconds and geometry refines afterwards. ELX owns the schematic and layout diff nodes; `repo` places them in review beside the others.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Source, compilation and verdict conditions | `MergeDriver::merge` | `Conflict::Text`, `Lockfile`, `Semantic`, `Check` | KLN-O-MERGE-1 | 1 |
| Touched-entity conflicts | Touched sets; designed-contact exemptions | `Conflict::Geometric` | KLN-O-MERGE-1 | 1 |
| Interference conflicts | MEC's interference classes | `Conflict::Interference` | KLN-O-MERGE-1 | 2 |
| Connectivity conflicts | Net partitions | `Conflict::NetMerge` | KLN-O-MERGE-1 | 3 |
| First-class conflicts | Conflicted blocks with alternatives; virtual merge base | A conflicted block evaluates as `repo/conflicted_block` with three fixes | KLN-O-MERGE-1 | 1 |
| Semantic and geometric diff | `compare.diff`; Kiln nodes refining by fidelity | A partial diff is flagged `repo/diff_partial` | KLN-O-DIFF-1 | 1 |

## Live sessions and offline work

People and agents often edit one branch at the same moment, and engineers work on aircraft and plant floors, so `repo` must merge concurrent and disconnected edits the same way it merges branches.

### Live sessions

A live session is a server-sequenced edit log per branch. Each participant (an editor, the language server, an agent) applies its own `SourcePatch`es optimistically. The relay orders every patch, checks it against the sender's permissions and enforced locks, and appends it. Each client then rewinds to the server's order, applies the patches it missed, and rebases its pending patches with the same `MergeDriver` that branch merges use, as Replicache rebases pending mutations on the server's state [Replicache]. Literal edits are last-writer-wins in sequence order, so concurrent `65mm` and `70mm` never give `6570mm`.

Each block parses under its own production (ING), so a block that stops parsing mid-edit keeps its kind and position and serves its last good result as `Stale`. Block ids never enter a `CallSite`.

**Decision D-KLN-22:** Live co-editing uses a server-sequenced edit log per branch, with clients rebasing pending patches through the branch `MergeDriver`, sequenced and replicated per (package, module confidentiality label); a higher-labelled module is its own log for cleared participants, and the relay refuses moves into a lower-labelled one.
*Why:* Crucible already has a central relay that checks every update, so the server can define the order of events, as Figma's multiplayer design does instead of a true CRDT [Figma multiplayer], and one merge algorithm means a pair of edits merges the same way live or on branches.
*Rejected:* a replicated tree CRDT with a separate reconcile step, which merges the same edits differently depending on timing; one log filtered per recipient, which cannot hide a labelled module's structure.

Device keys sign patch batches, a Change lists its contributors, undo is per principal, and agents join only branches their scope allows. Presence (cursor, selection, camera, an agent's current step) lives 30 s and is never stored.

| Lock | Scope | Enforcement | Typical use |
| --- | --- | --- | --- |
| Advisory | Block, file or Item | Presence shows the holder; agents' edits fail with `repo/lock_held` | Busy documents |
| Enforced | Path, block or Item | The relay and merge reject others' changes; expiry 8 h by default; administrators break it with an audited record | Binary Assets that cannot merge; regulated Items |

**Decision D-KLN-23:** Locks are optional and scoped; enforced locks exist for content that cannot merge and for regulated Items.
*Why:* structural merge makes pessimistic locking unnecessary for Ingot, but imported binaries cannot merge and some quality systems require exclusive checkout.
*Rejected:* mandatory checkout as PLM vaults use, which serializes teams.

### Offline work

**Decision D-KLN-33:** The desktop is local-first: its repository is authoritative for unpushed work, and everything except services that need a second party works offline.
*Why:* engineers work on aircraft, at plants and on secure networks, and local-first makes interactive latency independent of the network.
*Rejected:* a thin client over a cloud model, which fails offline and air-gapped.

A desktop without a team server designs, simulates, evaluates, presents and exports locally. It lacks only what needs a second party: Proposals, releases and Acts (contract 13.2).

**Decision D-KLN-24:** On reconnection the relay fast-forwards when nobody else changed the package meanwhile; after a disconnection of up to 60 s, pending patches rebase like any live edit when they do not conflict; otherwise offline work rejoins as a branch.
*Why:* short gaps are ordinary network jitter and should feel live, while longer ones hide concurrent work a person should review as a Proposal.
*Rejected:* rebasing every divergence automatically; turning every reconnection into a branch.

One TLS 1.3 connection (WebSocket, or WebTransport) carries live patches, object sync (missing closures as packs, pushed before a compare-and-swap ref update) and events with resumable cursors.

### Mirrors, federation and air-gapped sites

Mirrors keep label-filtered replicas at sites, and federation joins two organizations' servers through shared branches, both running the data-release stage at every exit. Air-gapped sites exchange signed bundles (`crucible bundle create --since <log checkpoint>`), and `crucible bundle import` verifies signatures, closure, labels, span integrity and log consistency after the receiving domain's review. Scale targets for desktops, team servers, cloud cells and repositories are in the Reference section.

The restore verifier checks every ref's closure and every log against checkpoints held by clients and witnesses. Team servers target 5 minutes of data loss and 4 hours to recover; the cloud targets no loss within a region and 15 minutes across regions. PLT owns the deployment modes these figures apply to.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Live sessions | Server-sequenced log per (package, module label); optimistic patches rebased by `MergeDriver`; signed batches | `repo/access_denied`; a rebase conflict becomes `Conflict::Text` on that block | KLN-O-COLLAB-1, KLN-O-COLLAB-2 | 2 |
| Labelled replication | Higher-labelled modules in their own logs | Downward moves refused with `label/write_down` | KLN-O-LABEL-1 | 2 |
| Presence and locks | Ephemeral presence; advisory or enforced locks | `repo/lock_held` | KLN-O-COLLAB-2 | 2 |
| Desktop offline | Local repository, Kiln and exports without a server | `repo/offline`, naming the queued step that needs a server | KLN-O-DEPLOY-1 | 1 |
| Offline rejoin | Fast-forward, rebase within 60 s, or a branch | Conflicts become a Proposal | KLN-O-COLLAB-3 | 1 (branches), 2 (live) |
| Air-gapped bundles | Signed bundles verified on import | `repo/bundle_rejected`, with the failed verification | KLN-O-DEPLOY-4 | 3 |
| Restore verifier | Closure and log consistency | Missing objects listed | KLN-O-RESTORE-1 | 2 |

## Items and revisions

Product lifecycle management (PLM) answers which thing was released, at which revision, made from which definition; Crucible keeps those answers as signed records in the design repository itself, so they can never drift from the model.

### Items

An Item is the lifecycle identity of a releasable thing (contract 2). `ItemKind` is `Part`, `Assembly`, `Document`, `SoftwareItem`, `CatalogPart` or `ManufacturingProgram`.

What an Item *is* comes from source; what has *happened* to it lives in records. Identity attributes (number, name, kind, classification, make or buy, unit of measure) are evaluated from `part(…, item:, name:)`, MEC's `bom_item` and their equivalents. The Item record, keyed by the item number, holds only lifecycle facts: revisions, states, effectivity, signatures and the system of record.

**Decision D-KLN-45:** Item numbers and every other identity attribute live in source, where BOM nodes read them; the Item record holds only lifecycle facts; an external system of record assigns numbers through a Proposal, and renumbering a released Item creates a new Item through a change order.
*Why:* a number or name kept in two places can disagree, and a number is outside the `ItemDefinition`, so assigning one marks nothing modified.
*Rejected:* numbers and names in records referenced by a local key, which adds a second identity; make-or-buy and unit of measure with no stated source.

A numbering policy in the policy package sets the format and whether gaps are allowed. The server leases clients blocks of 20 numbers for offline work, and where gaps are forbidden the first push rewrites provisional numbers in a server-made Change.

**Decision D-KLN-39:** Each record type (item number, revision label, state, change order, BOM, approvals) has a system of record, `Crucible` or `External(connector)`; under `External`, the release Act publishes a release package (STEP AP242 with PMI, drawings, BOM, NC programs, a source archive) into the external revision, and external approvals return as pinned external approval records, never as Approvals.
*Why:* adopters keep an enterprise PLM authoritative for years, and whoever can write the connector's input could otherwise forge a release.
*Rejected:* Crucible as the only system of record; external approvals counted as Approvals.

A release in this mode still needs a Crucible Approval; where the external system is the only approver, it covers only the publication, and the release record states "approved externally".

The parts policy, also in the policy package, lists approved catalog parts with manufacturers, lifecycle (`Preliminary`, `Approved`, `NotRecommended`, `Obsolete`) and preferred flags. ELX selections and MEC's `fasten` reach unapproved parts only under a Waiver of the parts-policy check. The package is pinned (contract 5.6), so a policy update never changes the verdict of an unchanged Change.

### Finding an existing part

Engineers create a new part when finding an existing one is harder [Siemens Geolus]. Crucible can do better than a name search: every Body has a `GeometryId` that hashes its geometry without names (contract 5.5), so identical parts under different names share it. Classification is typed: the policy package names a classification dictionary (ECLASS or the organization's own) whose classes carry attributes with units, computed from the model where possible.

**Decision D-KLN-51:** `read.search_items(class, where:, shape_like:, k)` searches readable released Items by class, typed attributes and shape: exact matches by `GeometryId` rank first, then by name-free shape descriptors computed once per `GeometryId` by a deterministic Wasm component with pinned weights; a new-part Proposal shows the five most similar Items, and an `Info` check, `duplicate_candidate`, flags a new Item above a similarity threshold.
*Why:* a shape search finds a part whatever anyone called it, and exact identity makes duplicate detection certain rather than probable.
*Rejected:* attribute search alone; a shape index outside access control, which would reveal what an uncleared principal cannot read.

### Foreign native CAD files

Adopting teams keep SOLIDWORKS, Creo or NX files for years, and Teamcenter manages such files in multi-CAD assemblies [Teamcenter MCAD].

**Decision D-KLN-53:** A native file from another CAD system is a `Document` Item whose reference graph (the files it references and their configurations) ECO's licensed readers extract at import; where-used, change impact and release completeness follow that graph, and Crucible never edits the file.
*Why:* teams can then release and trace mixed products during migration, without Crucible taking on another kernel's editing semantics.
*Rejected:* opaque Assets, which hide references; editing foreign files through their vendors' APIs.

### Interchangeability

**Decision D-KLN-25:** Interchangeability decides between a new revision and a new item number; Crucible computes it by comparing two definitions at their interfaces (mates, envelope, mass properties, fit and function checks), and a person confirms the verdict.
*Why:* form-fit-function judgment is the most error-prone step of change control, and Crucible holds the data to compute it.
*Rejected:* human judgment alone; a fully automatic verdict, since some functions are not modelled.

### Revisions and lifecycle states

A revision is identified by its `ItemDefinition` (contract 5.6): per Item kind, the name-free content that is made, loaded or read as the product, such as a Part's `GeometryId`s with definitional attributes, Materials and BOM, or a program's `ProgramSubject`. The revision record adds the label, source `ChangeId`, release tag, result classes and signatures. Late-bound fields (title-block fields, silkscreen revision and serial text) enter the digest as placeholders.

**Decision D-KLN-26:** An Item is modified since release exactly when its `ItemDefinition` differs from every definition its revision records; an upgrade that keeps topology and definitional attributes and moves geometry within the definition tolerance adds its definition through the upgrade Proposal, and lifecycle-bound text is filled at output.
*Why:* a refactor changes no `GeometryId`, bit-level noise from an operation upgrade must not mark Items modified, and a changed cosmetic thread moves no geometry.
*Rejected:* a new revision on any source change; `ObjectId` identity, under which a rename would void releases.

"Keeps topology" means equal topology in Anvil's normal form with entities matched by `EntityId`, and `anvil::deviation` measures the move. The definition tolerance is the larger of 10ρ (ten times the Body's resolution) and the smaller of 0.1 µm and 1% of the Item's tightest tolerance, counting the general tolerance when none is tighter. A `Warning` check flags Items whose 1% falls below 10ρ.

**Decision D-KLN-47:** Revision-label rules are data in the numbering policy, which names the drawing practice it follows, such as ASME Y14.35 [ASME Y14.35]; the default uses numbers, or letters skipping I, O, Q, S, X and Z, which read as digits or axis names.
*Why:* customers follow their own drawing practice, and no code depends on labels.
*Rejected:* label rules fixed in code.

| State | Meaning | Entered by |
| --- | --- | --- |
| `InWork` | Being designed | Creation; a Change that alters a released definition |
| `InReview` | A frozen candidate in an open order | Submission |
| `Prototype` | Released for prototype builds | An order with prototype scope; for a manufacturing program, its first transfer plan |
| `Proven` | A manufacturing program that ran and passed first article | A first-article record (Change control) |
| `Released` | Approved for production at its effectivity | The release Act |
| `Superseded` | Replaced, valid within its effectivity | The next revision's release |
| `Obsolete` | Not for new builds | An order with obsolescence disposition |

Entering `Released` requires every check to meet the gate predicate (contract 5.6), every child released already or in the same order, the route's Approvals and no open conflicts. Organizations add states and guards through the policy package. Phase 1 ships GP1's minimal lifecycle: item numbers, revision labels on release tags, `InWork` and `Released`, and the EBOM.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Items, numbering and labels | Lifecycle-only Item records keyed by number; identity attributes from source; leased number blocks; label policy | A duplicate number is rejected at push with `plm/duplicate_number` | KLN-O-PLM-2 | 1 |
| System of record | Per record type; external approval records | The release fails with `plm/connector_unavailable` while the connector is down | KLN-O-PLM-10 | 2 |
| Parts policy | Approved catalog parts in the pinned policy package; Waivers | The parts-policy check fails without a Waiver | KLN-O-PLM-11 | 2 |
| Classification and shape-similarity search | Typed classes; `read.search_items`; exact duplicates by `GeometryId`; `duplicate_candidate` | None: a search returns ranked matches or none | KLN-O-PLM-13 | 2 |
| Foreign native CAD files | `Document` Items with extracted reference graphs | `plm/reference_unresolved` for a referenced file missing at import | KLN-O-PLM-16 | 3 |
| Interchangeability | Interface comparison, confirmed by a person | Unmodelled interfaces are flagged for a person | KLN-O-PLM-3 | 3 |
| Revisions and states | Revision records; the gate predicate; the state machine | Every unmet guard named in `plm/guard_unmet` | KLN-O-PLM-1 | 1 (`InWork`, `Released`), 2 |
| Item definitions | Per-kind `ItemDefinition` and digests | None: every kind has a definition, with late-bound fields as placeholders | KLN-O-CHG-2 | 1 |
| Definition equivalence | Definition tolerance; normal-form topology | An out-of-tolerance upgrade marks its Items modified | KLN-O-PLM-9 | 2 |

## BOMs, effectivity and where-used

A bill of materials (BOM) is what purchasing, manufacturing and service act on, so Crucible derives every BOM from the one model, never edits one by hand, and traces every usage across repositories.

### Effectivity and variants

Windchill supports Serial, MSN, Block, Lot and Date effectivity [Windchill effectivity]; Crucible has one effectivity record with four kinds (`Date`, `Serial`, `Lot`, `Block`; an MSN is a `Serial`) in an end-item context. A configuration point (an end item and a value) is an input cell: Kiln resolves each usage to the child revision effective there and assembles released definitions without re-evaluating source.

**Decision D-KLN-27:** Variants are `#[configuration]` parameters of assembly features, and Kiln computes the 150% BOM (every usage of every variant, with its conditions) by abstract interpretation with those parameters symbolic; SAT checks report dead usages, collisions and unbuildable configurations.
*Why:* variants stay in the one model, a solver proves the rules consistent, and a fastener per resolved hole stays one usage with a computed quantity.
*Rejected:* variant BOM tables, which drift from the model; enumerating configurations, which is exponential.

A 100% BOM is the 150% BOM at one configuration point. CI builds the sellable configurations plus a pairwise covering set and evaluates the rest symbolically.

### BOM views

| View | Content | Source |
| --- | --- | --- |
| EBOM | Items, quantities with units, find numbers, reference designators, conditions, effectivity; lines from MEC's `bom_item` | The assembly graph at a Change or configuration point |
| MBOM | Phantoms, kits, raw stock, consumables, manufacturing-only Items, per `Site` | MFG packages referencing EBOM Items |
| Service BOM | Field-replaceable units, spare kits, service effectivity | The EBOM plus service annotations |

Views are Kiln nodes, never edited directly. A product is often made in two plants, so MBOM views, routings and work centres are keyed by (configuration point, `Site`), a policy-package record naming the plant and its ERP mapping. Per site, the reconciliation check consumes every EBOM Item and quantity exactly once or marks it not manufactured there. BOMs export as CSV, STEP AP242 product structure and through ECO's ERP connector.

### Where-used

The where-used index gains usage edges at each release and protected Change, across repositories. Lookups return parents up to end items, unreadable usages appear only as a count, and the index drives change impact, obsolescence, vulnerability response and mass change.

**Decision D-KLN-55:** ECO's catalog connector applies part lifecycle and change-notice events as dated External input updates on a monitoring branch, never on released source, and a nightly `obsolescence` check over the where-used of released revisions reports, per end item, the affected Items and effectivity, alternates found by re-running each catalog selection with the part excluded, and a last-time-buy quantity when ERP supplies demand as an External input; each finding opens a change request.
*Why:* obsolescence is the main reason released BOMs change, and engineers should learn of it from the product's own usage graph, not a spreadsheet.
*Rejected:* refreshing offers on released branches, which would change released verdicts; manual lifecycle tracking.

**Decision D-KLN-54:** `propose.mass_change(from, to, scope)` swaps one Item for another in all its usages across many parents: where-used selects the parents, an agent role prepares one Proposal per repository under one change order, interchangeability decides a new revision or a new number per parent, and the order releases only when every Proposal passes.
*Why:* Windchill swaps a part number in every using assembly in one operation [Windchill mass change], and Crucible can match it while running each parent's checks and keeping each repository's review.
*Rejected:* one cross-repository Change, which no repository's review could cover; editing parents without CI.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Effectivity | Records and configuration points | Gaps and overlaps fail with `plm/effectivity_gap` and `plm/effectivity_overlap` | KLN-O-PLM-4 | 3 |
| Variants and 150% BOM | Abstract interpretation; SAT; computed set quantities | Dead usages, collisions and unbuildable configurations reported | KLN-O-PLM-5 | 3 |
| BOM views | EBOM, MBOM per `Site`, service BOM as nodes | Reconciliation fails its check per site | KLN-O-PLM-6 | 1 (EBOM), 2 |
| Where-used | Indexed and access-filtered | None: restricted usages are counted, not shown | KLN-O-PLM-7 | 2 |
| Obsolescence monitoring | Monitoring branch; nightly `obsolescence` check; change requests | None: a missing lifecycle feed is reported as `plm/feed_stale`, not as a pass | KLN-O-PLM-12 | 3 |
| Mass change | `propose.mass_change`; one Proposal per repository under one order | The order cannot release while any Proposal fails | KLN-O-PLM-15 | 3 |

## Change control

A released product changes only through a reviewed, signed change, and Crucible makes that change a Proposal whose approvals sign exactly what will be made.

### Requests, orders and notices

| Record | Purpose and mechanism |
| --- | --- |
| Change request | A problem or improvement with its supporting records, from nonconformances, complaints, corrective actions, field failures, obsolescence findings or agent findings |
| Engineering change order | A Proposal with lifecycle scope: affected Items with from and to revisions, effectivity, stock disposition and plan |
| Manufacturing change order | A Proposal limited to manufacturing content (below) |
| Change notice | A signed record created by the release, with acknowledgements |

An order branches from the named release, agents prepare work as Proposals under it, and impact analysis covers where-used, open orders, interchangeability, reconciliation and compliance. Submission moves the affected Items to `InReview` and freezes the branch.

`act.prepare` produces a release plan whose subject is the order's `ApprovalSubject` (contract 5.6), so the order's approvals are the plan's Approvals. `act.commit` recomputes the subject at its target and refuses a mismatch; the merge, tag, revision records, effectivity and notice then commit in one transaction. On the approval page an approver may approve, return the plan for changes without penalty, or deny it as suspicious (contract 7.6).

[[DIAGRAM diagrams/05-kiln-change-order-lifecycle.jsx: change order lifecycle · 8 stages, one loop back on a changed subject]]

Read the upper row left to right and the lower row right to left; the dashed arrow is the one loop, taken when the subject changes after approval.

**Decision D-KLN-28:** An Approval signs the `ObjectId` of the order's `ApprovalSubject`, covering the `ItemDefinition` digests of every affected Item of every kind, while the head `ChangeId` and the CI report stay unsigned provenance.
*Why:* a rebase or CI re-run of identical content keeps approvals, and a subject of geometry alone would let a rebase swap firmware or a Material under a valid approval.
*Rejected:* signing the head `ChangeId`; a subject of geometry and PMI only.

Agents never sign; they attach analysis to the order as attachments. Concurrent orders on one Item serialize at release.

### Review routes and delegation

A change board needs to say who must approve, in what order, and who stands in for someone away, as Windchill's workflow templates [Windchill workflow] and delegation [Windchill delegate] do.

**Decision D-KLN-50:** Review routing is a `ReviewRoute` record in the policy package: ordered stages, each a reviewer set selected by Cedar (roles and attributes) with a quorum of `All`, `Any` or `AtLeast(n)`, and conditions over the subject's typed facts (Item class, labels, risk class, changed special characteristics, cost delta) that add stages; an `ApprovalDelegation` signature record names delegator, delegate, scope, Item classes and expiry, never an agent, and is refused when the delegate lacks the clearance.
*Why:* routes written as typed records over the evaluated subject cannot drift from what the order changes, and delegation keeps one absent approver from blocking a release.
*Rejected:* free-form workflow scripts; Cedar alone, which says who may approve but not who must or in what order.

Due dates remind and escalate to a named role, never approve. Delegation covering physical-effect Acts or `controls` needs two people, delegated signatures name both people, and protected-branch merges use the same routes.

### Waivers and policy allowances

A Waiver lets one named check count at a gate for named Items and effectivity (contract 5.6). A deviation is a Waiver whose effectivity is a serial or lot range, and a compliance exemption is a Waiver of a compliance check; contract 5.4 says who signs each. A `#[waive]` attribute in source only requests one.

A policy allowance is a policy-package record that quantifies one error source, such as a design code's model-form factor (contract 5.6). Checks read allowances like any pinned input, listed in `CheckOutcome.allowances`, and an uncovered check is simply `Undecided`. Phase 1 ships policy packages with the allowances COV catalogues; GP1's and GP2's stress checks take their model-form bounds from the phase 1 validation campaign instead (contract 13.1).

### Manufacturing change orders

Shops change feeds, tools and fixtures daily without touching the part, so manufacturing content changes on its own path.

**Decision D-KLN-38:** A manufacturing change order is limited to MBOM, routings, programs, fixtures, work instructions and inspection plans, and is rejected if it touches an EBOM definition; a manufacturing program Item enters `Prototype` with its first transfer plan, without an order, moves to `Proven` when a first-article record names a run revision merged into the program source, and needs a manufacturing change order only to enter `Released`.
*Why:* prove-out happens at the machine and must not need paperwork per edit, the released program must be the one that actually ran, and a one-off job can close in `Prototype` with a run record.
*Rejected:* every shop edit as an engineering change order; an order to create every program.

A first-article record joins program revision, machine serial, part serial and one passing Evidence record per characteristic (MFG). Edits captured at the control in `Prototype` open a Proposal with no nonconformance (MFG). An order that changes a part returns exactly its dependent programs to `Prototype`, imported ones by their `verified_against` revisions.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Approval subjects | Subject `ObjectId` signed; recomputed at commit | A changed subject voids Approvals; a mismatch is refused with `act/subject_mismatch` | KLN-O-CHG-1 | 1 |
| Waivers and policy allowances | Contract 5.6 records, pinned policy packages, contract 5.4 signers | An uncovered check stays `Undecided` | KLN-O-PLM-1 | 1 |
| Change requests, orders and notices | Records plus Proposal; release Act; three approval outcomes | Unmet conditions named in `plm/guard_unmet` | KLN-O-CHG-1 | 2 |
| Review routes and delegation | `ReviewRoute` stages, quorum and conditions; `ApprovalDelegation` records | A route stays open until every stage's quorum holds; an ineligible delegate is refused with `trust/delegate_ineligible` | KLN-O-CHG-3 | 2 |
| Manufacturing change orders | Manufacturing scope; program states by first transfer and first article | An EBOM-touching order is rejected with `plm/scope_violation` | KLN-O-PLM-8 | 2 |
| First-article records | Program, serials, Evidence per characteristic; run revision merged | The program stays `Prototype` | KLN-O-PLM-8 | 2 |

## Quality records and compliance

Regulated customers must show that every requirement was verified, every substance declared and every problem corrected, so these records are checks and signed records in the same repository as the design.

### Requirements traceability

Requirements are `std::systems` records in source, or imported through ReqIF, OMG's format for exchanging requirements between organizations [OMG ReqIF]; a `require` names the requirements it verifies. The traceability matrix is a Kiln node from requirement to check to outcome to Evidence record. Coverage is itself a check: each requirement needs a verifying check of its method (`Analysis`, `Test`, `Inspection` or `Demonstration`), each `Test` requirement an Evidence record, and a changed requirement's links stay suspect until a person signs them.

### Compliance

Compliance is a check over data. MFG supplies the substance rules (RoHS [EC RoHS], REACH and SCIP, conflict minerals); this tab owns the compositions rolled up from `Material` versions, signed supplier declarations, and regulation datasets pinned as External inputs. Compliance checks return `CheckOutcome`s like any check: missing data is `Undecided { MissingData }`, which blocks releases that require compliance, and a compliance exemption is a Waiver. A new regulation version arrives by bot Proposal, re-evaluates released revisions on the monitoring branch, and opens change requests through where-used.

The EU Cyber Resilience Act's reporting duties for actively exploited vulnerabilities apply from 11 September 2026, with an early warning within 24 hours and a notification within 72 [EC CRA reporting]. Software items carry a CycloneDX or SPDX software bill of materials per release (ELX) [CycloneDX], and where-used lists the affected shipped serials within minutes (target).

### Corrective action, complaints and audits

Windchill ships corrective and preventive action (CAPA), nonconformance, customer-experience and audit modules beside its change control [Windchill quality], and medical and aerospace customers must close that loop.

**Decision D-KLN-52:** Crucible keeps three signed quality records in the design repository: `Complaint` (source, product, serials, reportability decision), `Capa` (problem, linked nonconformances and complaints, affected serials through where-used, containment, root cause with its method, actions as links to change requests, manufacturing change orders or training records, an effectiveness check, and a closure signature by `quality`) and `AuditFinding`; the effectiveness check is an ordinary `require` over Evidence records gathered after a stated period, and a `Capa` cannot close until it passes; an organization that keeps an external quality system connects it through ECO's quality connector world instead.
*Why:* the design history then has no hole where auditors look first, and an effectiveness check written as a check is verified like every other claim.
*Rejected:* free-text CAPA forms; requiring every customer to move its quality system into Crucible.

MFG's nonconformance records link to these records.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Requirements traceability | Requirement records; `verifies` links; coverage check | Uncovered or suspect requirements block release | KLN-O-TRACE-1 | 2 |
| Compliance checks | Regulation datasets, declarations, rolled-up compositions; `CheckOutcome` | `Undecided { MissingData }` | KLN-O-COMPL-1 | 3 |
| Vulnerability where-used | Software bills of materials per release | Unknown contents flagged `plm/sbom_incomplete` | KLN-O-VULN-1 | 3 |
| Quality records | `Complaint`, `Capa`, `AuditFinding`; effectiveness as a check; or ECO's quality connector | A `Capa` closure before its effectiveness check passes is refused with `plm/capa_unverified` | KLN-O-PLM-14 | 3 |

## Physical tests and Evidence records

Measurements from rigs, CMMs and test labs decide checks and close golden products, so they enter designs the way every outside input does: signed, content-addressed and pinned.

An Evidence record is an External input (contract 5.6). A bot Proposal, or on protected branches an audited ref transaction, pins its id in `ingot.lock` under `[[evidence]]` keyed by the `CheckId` it serves; the update tool picks the newest record valid at its measurement time, and the check reads only the pinned one. A check declares whether a record holds while its inputs are unchanged or must repeat per lot.

**Decision D-KLN-35:** Physical tests are Acts on hardware rigs whose only product is an Evidence record, signed by an enrolled runner or a registered evidence signer, addressed by `CheckId` and the identities of the tested inputs, and read by checks only through its pin in `ingot.lock`.
*Why:* physical results are not pure functions, and pinning makes one Change give one outcome on every builder without a second selection mechanism.
*Rejected:* cached derived values; selecting the newest record at evaluation time, which reads a clock; a separate cursor over the evidence log.

### Rigs and labs

1. **Enrolment.** A runner proves its TPM endorsement-key chain, certifies an attestation key and quotes its boot measurements over a server nonce. The server compares the quote with reference measurements signed by the image's build, and every Evidence record cites it.
2. **Pull.** The runner pulls requests over an outbound connection, so factory networks need no inbound ports.
3. **Requests.** A request names its artifacts, its procedure (Ingot, or a tool-world Wasm component) and its budget in rig minutes.
4. **Physical effects.** Transfers, flashing and starts follow contract 7.6's physical-effect Acts, and emergency stops are hardware.
5. **Unattended tests.** `run_rig_test` runs only on rigs under an `unattended_safe` site safety record, which contract 7.1 limits to test rigs with a signed ISO 12100 risk assessment, interlocked guarding and a safety-rated stop. The runner enforces the record's energy limits.
6. **Contents.** The record holds raw data in the CAS, instruments with calibration records, environment, operator and procedure version. A record whose calibration did not cover the measurement date is invalid, and checks over it fail with `evidence/calibration_expired`.

An external lab signs as a registered evidence signer: a record of the organization, its ISO/IEC 17025 accreditation scope and certificate, a signing key verified out of band, the characteristic kinds it may measure and an expiry, created under contract 5.4's two-person row. A lab's Evidence record verifies only against a live signer record whose scope covers its characteristic.

Evidence records stay out of calibration (contract 13.1). In phase 1, external metrology for GP1 and GP2 enters as one lab-signed record per characteristic. The phase 1 validation campaign on separate specimens enters the same way and feeds COV's model-form validation, and the proof loads then serve as held-out confirmation against each check's predicted gauge functional.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Evidence records | External inputs pinned under `[[evidence]]` by `CheckId`; valid at measurement time | `evidence/calibration_expired`; an unpinned check stays `Undecided` | KLN-O-HW-1 | 1 (lab records), 2 |
| Evidence signers | Registered lab records with accreditation scope and expiry | `evidence/signer_unregistered` or `evidence/out_of_scope` | KLN-O-HW-1 | 1 |
| Runner enrolment | TPM quote against signed reference measurements | Unmatched images refused with `evidence/enrolment_refused` | KLN-O-HW-1 | 2 |
| Physical test Acts | Pull-based; contract 7.6 Acts; site safety records and energy limits | Limit violations abort the test and are recorded | KLN-O-HW-1 | 2 |

## Signatures and approvals

Every human decision that Crucible relies on is a signature over exact content, so a later reader can verify who decided what, and nobody can move a signature to different content.

### Signature records

A signature record holds signer, printed name, server time (there is no offline signing), meaning, the signed `ObjectId`, an algorithm id and the signature. Contract 5.4 lists the meanings and, in one table, who may sign each: how many people, which roles, which credential, and whether the author or delegating human may sign. `trust` evaluates that table; no tab restates it.

**Decision D-KLN-41:** `trust` compiles contract 5.4's signature table into Cedar policies generated from the table, never hand-written, and one oracle fuzzes every row, single-person mode included.
*Why:* rules about who may sign were scattered across tabs in prose, where two copies could disagree, and a generated policy cannot drift from its table.
*Rejected:* a hand-maintained list of two-person items in this tab; per-tab signing rules.

People sign through WebAuthn with a device-bound approval credential (contract 7.6). The record keeps the authenticator data, the client data and the attestation, so it verifies offline.

**Decision D-KLN-58:** A signature's WebAuthn challenge is SHA-256(domain tag ‖ a 16-byte server nonce ‖ the signed `ObjectId` ‖ meaning ‖ signer principal ‖ request id), and the record stores the nonce and every other field, so an offline verifier recomputes the challenge.
*Why:* with the meaning and the signer inside the signed bytes, nobody can relabel a review signature as a release approval, which 21 CFR 11.50 and 11.70 require [21 CFR Part 11], and a fresh nonce stops replay.
*Rejected:* the signed `ObjectId` alone as the challenge, which is predictable and leaves the meaning outside the signature.

Enrolling an approval credential is itself a row of contract 5.4, with notice through an independent channel as NIST requires when binding an authenticator [NIST SP 800-63B-4 binding]. Synced passkeys never sign, because syncable authenticators cannot meet AAL3 [NIST SP 800-63B-4]. Phone approvals and single-person mode for organizations with fewer than two eligible people follow contracts 7.6 and 5.4.

**Decision D-KLN-42:** Every signature record carries an algorithm id, and tenant records never use LMS; from phase 2, release tags, log checkpoints and provenance are dual-signed with a classical signature plus ML-DSA-87 [NIST FIPS 204], and long-retention records are re-timestamped before an algorithm retires.
*Why:* records must verify for decades, and one stateful LMS key cannot safely serve a tenant's many signers.
*Rejected:* classical signatures only; replacing algorithms in place.

### Part 11 and assessment

Crucible maps each control of 21 CFR Part 11 to a mechanism (Reference). Phase 1 ships signature records for the GP1 release, and Part 11 mode follows in phase 2. The 11.100 certification to FDA is the customer's act. FDA's QMSR, effective 2 February 2026, incorporates ISO 13485:2016 [FDA QMSR], and 21 CFR 820.10(c) applies its design clause 7.3 to class II and III devices, software-automated class I devices and listed class I types [21 CFR 820.10]. Orders, checks, quality records and reports supply the design history.

**Decision D-KLN-49:** The Part 11 and AS9100 assessment package is contract 7.7's Computer Software Assurance package plus, per release, a table from each 21 CFR 11.10 clause and selected AS9100 clause to KLN oracles and their results; the customer chooses the assessor, and phase 3's third-party assessment uses one the founder retains.
*Why:* assessors read clause-to-evidence tables, and oracle results fill them.
*Rejected:* a package format per assessor.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Signature records | Detached records with WebAuthn data; the challenge binds nonce, `ObjectId`, meaning, signer and request | Unenrolled credentials cannot sign; a relabelled meaning fails verification with `trust/signature_invalid` | KLN-O-SIG-1 | 1 |
| The signature table | Contract 5.4 compiled to generated Cedar policies; credential enrolment; single-person mode | `trust/signers_insufficient`, naming the missing signer or role | KLN-O-POLICY-1 | 1 |
| Part 11 mode and assessment | Re-authentication; Part 11 controls; clause tables | Failed re-authentication blocks and is audited | KLN-O-SIG-1 | 2, 3 |
| Signature agility | Algorithm ids; dual signatures; no tenant LMS | `trust/unknown_algorithm` | KLN-O-SIG-2 | 2 |

## Identity, authorization and audit

Every call names a principal and every decision leaves a verifiable trace, so access can be reasoned about before it happens and checked after.

### Principals

| Principal | Authentication | Keys |
| --- | --- | --- |
| Person | SSO over OpenID Connect or SAML 2.0; local accounts only on desktop and air-gapped installs; WebAuthn | A hardware-backed device key per device |
| Agent | Registered by an owner; short-lived tokens by exchange (AGT) | An ephemeral key bound to the token |
| Local device agent | A credential held on a device without a fresh user-presence proof | Authenticates as `agent:<org>/local/<device>` with `Declared` assurance |
| Service | Workers, builders, runners, integrations | Workload identity or mTLS certificates |
| External organization | Its identity provider, or invited accounts with WebAuthn | As for persons |

Any process a user runs can reach the desktop keychain, so a process acting for the person, such as an agent running the CLI, authenticates only as a device agent. Human-only methods (merging, endorsing, changing policy, declassifying, waiving, changing recipients, and writing anything above `public` locally) need a fresh WebAuthn assertion bound to the call (contract 7.6).

SCIM 2.0 provisions users, sessions last 12 h, and offline desktops hold a 7-day refresh grant; controlled data follows a shorter lease (Labels and export control).

### Authorization

**Decision D-KLN-29:** Authorization uses Cedar policies, evaluated in process on every request, including live-session patches at the relay; Cedar's analysis lists every request a policy change newly permits or denies, and reviewers approve that list.
*Why:* Cedar covers role- and attribute-based access in one language, is written in Rust with a formal model, and is analyzable [Cutler 2024].
*Rejected:* Open Policy Agent with Rego; hand-written role checks.

Roles come from identity-provider groups: `viewer`, `commenter`, `editor`, `maintainer`, `approver`, `release_manager`, `export_officer`, `quality`, `admin`. Attributes describe principals (organization, location, training, licences, `ControlAuthorization`s) and resources (labels, Item state, repository, path). Actions are `read_source`, `read_derived`, `evaluate`, `edit`, `push`, `merge`, `approve`, `sign`, `release`, `purge` and `manage_policy`. Deny overrides allow, the default is deny, and policy changes are `propose.policy` Proposals, refused from contexts holding untrusted data.

Cedar policies authorize `api` calls and never feed evaluation; policy packages feed evaluation and are pinned like any input (contract 5.6). Only these two things are called policy.

Protected refs take rules per pattern: no direct pushes, required checks, review routes without self-approval, signed Changes, forward-only refs and immovable tags, change orders for `Released` Items, and no agent ref updates, approvals or signatures. Agents write only `agents/*` refs, within their scope and their owner's permissions (AGT).

Break-glass access, invoked by one administrator with AAL3 for at most 4 hours, grants only reads within that administrator's clearances, agent freeze, ref revert, lock release and session termination; it never declassifies, clears, changes policy, purges, approves or signs. A second administrator reviews it within 72 hours.

### Audit

Every write, labelled read, policy decision, signature, login, Act and administrative action is an audit entry holding only identifiers, digests and the pseudonymous principal; full content is a CAS record in its label's domain, committed by `ObjectId`. AGT owns the `api`-call fields inside an entry.

**Decision D-KLN-30:** The audit log, repository transaction logs and release tags are entries in per-tenant transparency logs in the C2SP tlog-tiles format [C2SP tlog-tiles], with checkpoints signed by the deployment and optionally cosigned by customer witnesses.
*Why:* a Merkle log exposes any rewrite or fork to anyone holding an earlier checkpoint, and witnesses keep the operator honest.
*Rejected:* an append-only database table, which can be rewritten undetectably; a public blockchain.

Clients verify consistency on every sync. Checkpoints carry Ed25519, ECDSA P-256 in FIPS mode and ML-DSA-87 from phase 2. Phase 1's signed append-only audit log already uses the tlog-tiles layout, without witnesses.

Transport is TLS 1.3, mutual between services, and release keys live in HSMs. FIPS mode routes all cryptography through a FIPS 140-3 module from PLT's provider, such as AWS-LC through aws-lc-rs [aws-lc-rs], whose AWS-LC 3 module holds certificate 5314 [NIST CMVP 5314]. NIST placed all FIPS 140-2 certificates on its historical list on 22 September 2026 [NIST FIPS 140-3 transition].

### Privacy

**Decision D-KLN-43:** Logs and records hold pseudonymous principal ids, mapped to names under per-person keys that can be crypto-shredded unless a retention lock keeps them; each lock carries a `retention_basis` the customer sets as controller: `UnionOrMemberStateLaw { citation }`, `LegalClaims`, `ThirdCountryLaw { citation }` or `Contract`.
*Why:* GDPR Article 17(3)(b) excepts only obligations under "Union or Member State law" [GDPR Art 17], so a US retention duty needs a stated basis.
*Rejected:* names in records; pruning logs, which breaks verification.

An erasure request against a `ThirdCountryLaw` lock goes to the customer's privacy officer. Deployments ship records-of-processing entries and a DPIA template. Presence, follow mode and approval tab-view recording are organization settings, and works-council mode disables per-person activity analytics, since BetrVG §87(1) item 6 gives German works councils co-determination over monitoring devices [BetrVG].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Identity | OIDC or SAML, SCIM, WebAuthn, device keys; local device agents | Failed authentication audited as `auth/failed` | KLN-O-POLICY-1 | 1 |
| Local credentials | Device agents with `Declared` assurance; per-call assertions for human-only methods | `auth/user_presence_required` | KLN-O-POLICY-1 | 1 |
| Authorization and branch protection | Cedar on every request; rules per ref pattern; analysis on every policy change | `auth/access_denied`, naming the permission | KLN-O-POLICY-1 | 1 |
| Break-glass | Bounded actions; second-administrator review | Forbidden actions refused with `auth/break_glass_forbidden` | KLN-O-POLICY-1 | 1 |
| Tamper-evident audit | tlog-tiles; identifiers and digests only; witnesses | Forks detected at sync and reported as `trust/log_fork` | KLN-O-AUDIT-1 | 1 (log), 2 (witnesses) |
| FIPS mode | PLT's FIPS 140-3 provider | Non-approved algorithms refused | KLN-O-SIG-2 | 2 |
| Pseudonymous records and privacy | Per-person keys; retention bases; works-council mode | Erasure refused under a lock, or routed for `ThirdCountryLaw` | KLN-O-AUDIT-2 | 2 |

## Labels and export control

Export-controlled, customer-confidential and licensed data must stay with the people allowed to see it even after it has been combined, meshed and simulated, so every value carries labels that Kiln joins through every derivation.

### Three parts of a label

Contract 5.3 defines labels and is their only statement; this section says how `trust` applies them.

- **Confidentiality** (`level`, `controls`, `scopes`) decides who may read. Clearances, write-down, encryption domains, worker partitions and live replication compare this part only. `Labels::is_controlled()` holds when `controls` is non-empty. Lowering it needs a declassification record signed under contract 5.4.
- **Usage** (`licences`) is compared only where data leaves: `release_data` Acts, exports, audited local writes, registry publishing and responses to model contexts. A design that uses Materials from several licensed databases therefore stays one encryption domain and one worker partition.
- **Integrity** never blocks a read or a write. Merging the Change that introduced a pin, an Asset or a source span clears it on typed values: a merged supplier STEP import yields trusted geometry and numbers, while its part names stay `ExternalText`, and a new Asset revision starts untrusted.

A principal sees the name of a scope or control it satisfies; others see an opaque per-tenant id and the text `restricted`, so program code names and customer names do not leak through errors, where-used counts or partly visible results.

### Readers who are not cleared

The unit of a source label is a module (contract 7.1). A supplier or uncleared colleague works with a labelled module only through derived views (signature, envelope, interfaces, mass properties), each with its own declassification record and evaluated on cleared workers. Any node joining an undeclassified output is unreadable to them.

Outcomes leak too, so such Evaluations run under a per-principal query budget and parameter grid named in the declassification record. Every outcome that depends on the module beyond its views (verdict, failure kind, cost, duration) reaches that principal only as `Withheld`, and CI reports "blocked by a check you cannot read". 22 CFR 120.56(a)(1) counts inspection by foreign persons as a release [22 CFR 120.56], and budgets keep probing from becoming inspection.

### Control authorizations, devices and residency

A `controls` element is satisfied only through a `ControlAuthorization` record (contract 5.3). A controlled node runs and is stored only in the regulated cloud, in end-to-end mode, in a customer deployment, or on a desktop registered as a `controlled_device`, which leases the domain key for at most 24 h and loses it remotely or before travel outside the permitted countries; an expired lease leaves only ciphertext.

**Decision D-KLN-32:** Export-controlled data is handled by labels that propagate through Kiln and model contexts, policies over principal attributes, residency-bound storage and compute, leased keys on registered devices, and an optional end-to-end mode.
*Why:* every path to controlled data, including inspection of a derived value, is a potential release, so every path needs a check.
*Rejected:* air-gapped installations as the only option; repository flags without propagation, through which derived values leak.

Residency binds storage and compute to named regions and staff attributes. Other egress channels follow PLT's label-aware egress rule.

End-to-end mode keeps plaintext off Crucible's cloud: 22 CFR 120.54(a)(5) treats end-to-end encrypted unclassified technical data as not exported under stated conditions [22 CFR 120.54], as does 15 CFR 734.18(a)(5) [15 CFR 734.18]. Keys stay in the customer's key service, and qualification is the customer's legal determination.

**Decision D-KLN-48:** In end-to-end mode, a customer-hosted tier 2 store and trusted builders inside the customer's boundary form their own trust domain under contract 7.8, keyed in the customer's key service and trusted only by that customer's builders.
*Why:* otherwise end-to-end customers lose the shared cache.
*Rejected:* a cloud tier holding customer keys, which defeats the mode.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Labels and declassification | Contract 5.3's three parts; usage compared only at exits; opaque scope names | `label/write_down` | KLN-O-LABEL-1 | 1 |
| Derived views for uncleared principals | Declassified views; per-principal budgets and parameter grids; `Withheld` outcomes | `label/budget_exhausted`; undeclared outputs unreadable | KLN-O-LABEL-1 | 1 |
| Control authorizations | `ControlAuthorization` records; controlled placement | Uncovered access refused with `label/control_unauthorized` | KLN-O-LABEL-1 | 1 |
| Controlled devices | Registered `controlled_device`; 24 h key leases; travel revocation | An expired lease leaves ciphertext; reads fail with `label/lease_expired` | KLN-O-LABEL-1 | 2 |
| Residency | Region and operator constraints | `label/residency_denied` | KLN-O-LABEL-1 | 2 |
| End-to-end mode | Customer keys; customer-hosted cache domain | Key release to an ineligible principal refused | KLN-O-LABEL-2 | 3 |

## Data release to other organizations

Suppliers, customers and partner organizations need exactly the data a job requires, so every byte that leaves a tenant passes one checked stage, and suppliers work from packages and derived views rather than repositories.

### Exits

Tenant bytes leave through three exits (contract 7.6): `release_data` Acts, `api` responses to model contexts cleared for them, and audited local writes. Each exit compares both the confidentiality and the usage parts of the label.

**Decision D-KLN-40:** AGT owns the `release_data` Act family, and `repo` runs its stage at `act.commit` for every transfer to another party, shared-branch pushes and federation sync included; the stage reads labels, the `RecipientRecord`, a fresh screening and any `ControlAuthorization`, and writes the release-data record, watermark, expiry and audit entry in one transaction.
*Why:* separate exit paths with separate controls drift apart, and checks committed with their records cannot.
*Rejected:* controls per path; a second definition of the Act family here.

A person's export to a local folder or application is an audited local write, not an Act, when the payload is `public` or `internal`, carries no `controls` and no `scopes`, carries only `DataLicence`s that permit the disclosure, and names no recipient record; above `public` it needs the per-call assertion of Identity, authorization and audit.

A `RecipientRecord` holds the organization, endpoints, out-of-band verification, screening versions, expiry and a clearance over both label parts; `release_data` refuses a payload above it. Screening runs at every commit against lists at most 24 h old, such as the US Consolidated Screening List [ITA CSL]. A recipient change needs two people (contract 5.4), is refused from a flagged context, and takes effect after 24 h.

Watermarks deter casual redistribution and identify unmodified copies only. Each is an HMAC under the tenant's watermark key, so recipients cannot forge each other's marks, and it never alters definitional geometry or attributes. A recipient who re-saves a STEP file or re-slices a 3MF removes it. Traceability therefore rests on the release-data record of who received which file hash, not on the mark.

### Supplier packages and derived views

Suppliers never browse a design repository. They receive signed, expiring supplier packages (STEP AP242 with PMI, 3MF, drawings with QIF 3.0 inspection plans, requirements, derived views) and return quotes, QIF results, certificates and declarations, which agents read as `ExternalText`.

| Derived view | Recipient gets | Stays private |
| --- | --- | --- |
| Frozen geometry | Released Bodies at fixed parameters, with PMI | Source, history, parameters |
| Envelope and interfaces | An offset hull, interface faces, mates, mass properties | Internal geometry |
| Behavioral model | An FMI 3.0 FMU or reduced model with its `ValidityEnvelope` | Geometry and source |
| Remote parametric model | A feature callable with parameters, evaluated on the owner's workers | Source and intermediate values |

**Decision D-KLN-31:** One derived-view mechanism serves suppliers and uncleared staff alike: each view has its own declassification record, parametric views are evaluated remotely on the owner's cleared workers under per-recipient budgets, parameter ranges and steps, and no compiled code is ever shipped.
*Why:* code on the recipient's machine, Wasm included, can be decompiled, while remote evaluation keeps source with its owner and still caches by `NodeKey`; one mechanism means one set of budgets and audits to verify.
*Rejected:* obfuscated Wasm components; encrypted packages, whose key must reach the recipient; a separate path for internal readers.

Every remote query is audited, and one over budget fails with `share/quota_exceeded`. Redaction swaps `confidential` features for defeatured geometry or envelopes within a declared deviation and strips names, comments, provenance ids and history, and a redaction check verifies before signing that nothing leaks.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Data-release stage | Checks at `act.commit`, shared branches and federation included; both label parts compared | The commit is refused, naming the failed check | KLN-O-RELEASE-1 | 1 |
| Audited local writes | Uncontrolled, unscoped, licence-permitted payloads; assertion above `public` | `act/export_required` for any other payload | KLN-O-RELEASE-1 | 1 |
| Recipient records and screening | Clearances; two-person changes; lists at most 24 h old | Over-clearance or a listed party refused with `share/recipient_refused` | KLN-O-RELEASE-1 | 1 (other organizations), 2 (internal) |
| Supplier packages and watermarks | Signed packages with expiry; keyed watermarks; release-data records | Expired access denied with `share/expired` | KLN-O-SHARE-2 | 3 |
| Derived views and redaction | Declassified views; redaction check | A detected leak refuses signing with `share/redaction_leak` | KLN-O-SHARE-1 | 3 |
| Remote parametric shares | Budgets, ranges, audit | `share/quota_exceeded` | KLN-O-SHARE-3 | 3 |

## Reference

### Crates

| Crate | Holds |
| --- | --- |
| `kiln` | The scheduler, memo table, eviction, progressive results, cost models, derivative traversal and remote placement |
| `cas` | Object kinds, hashing, chunking, codecs, encryption domains, tiers, collection |
| `repo` | Changes, refs, the transaction log, merge, diff, live sessions, sync and bundles |
| `plm` | Items, revisions, effectivity, BOM views, change orders, Waivers, policy packages, Evidence records, quality records |
| `trust` | Cedar, labels, signature records and the signature table, recipient records, control authorizations, the audit log, the `PlacementPolicy` implementation |
| `engine` | Builds one `Kiln` with every operation registry; used by `api` and the apps |
| `base-op` (KLN's part) | `OpImpl`, `DynOp`, `OpRegistry`, `OpCx`, `OpResult`, `Stop`, `Failure`, `Abort`, `NodeKey`, `Differentiable`, `DeterminismGrade`, `Fidelity` |
| `apps/attestation`, `apps/relay`, `apps/rig-runner` | The attestation service, the live-session relay and the hardware runner (KLN, packaged by PLT) |

### Shared-cache roles

| Role | Runs | Holds | Writes |
| --- | --- | --- | --- |
| Untrusted-evaluation worker | Proposal CI, External Ops, tests of third-party packages, each in a single-use microVM | A receipt key only | A per-Proposal namespace; execution receipts |
| Trusted builder | Merged Changes of protected branches; third-party code only in microVMs | Workload identity | Results for attestation |
| Attestation service (`apps/attestation`, KLN's, packaged by PLT) | Signing only | Signing keys | Attestations over (`NodeKey`, `ObjectId`), with ids the host computed |
| Operator registry builders | First-party packages only | Operator keys | The global public domain, under 2-of-n agreement |

### CAS object kinds

| Kind | Content | Typical size |
| --- | --- | --- |
| `Blob` | Opaque bytes: an imported STEP file, an image, a Wasm component | Bytes to gigabytes |
| `Record` | Deterministic CBOR: a Change, a tree, a `Material`, a signature, an attestation | Under 64 KiB |
| `Segmented` | A large typed array (mesh, Field values, sparse matrix) in keyed segments | Megabytes to terabytes |
| `Index` | Child `ObjectId`s with lengths and keys | About 16 KiB |

### Segment keys

| Value | Segment key and content |
| --- | --- |
| Body | Anvil's content-defined encoding leaves of at most 1,024 rows (ANV) |
| Mesh and `DisplayPackage` clusters | Morton code of a spatial cell; up to 4,096 triangles |
| Field values | Flux virtual partition, in 1 MiB chunks |
| Sparse matrix | Row block |
| Opaque Blob | FastCDC: minimum 16 KiB, average 64 KiB, maximum 256 KiB |

### CAS tiers

| Tier | Store | Contents | Eviction |
| --- | --- | --- | --- |
| 0 | Process memory | Kiln values | GreedyDual-Size |
| 1 | Local disk in 64 MiB append-only packs; OPFS in browsers | Working set, unpushed Changes | Budget (default 20% of free disk); unpushed Changes never |
| 2 | Team server or cloud region: object storage plus a metadata store | All source, shared results, attestations | Collector plus budget |
| 3 | Archive object storage | Releases and their cited results | Retention policy only |

### Repository objects

| Object | Content |
| --- | --- |
| `Change` | Parents, tree, author, `on_behalf_of`, contributors, hybrid logical clock time, description, conflicts; its `ChangeId` hashes the unsigned Change |
| `Tree` | A prolly-tree map from normalized path to file, `ingot.lock` included |
| `SourceFile` | Canonical Ingot text, a block map (block id to span) and span integrity; segmented by top-level block above 64 KiB |
| `Tag` | A name and a target Change; a release tag adds the release record |
| `RefTransaction` | Predecessors, the resulting view of all refs, principal, `api` call |
| Signature records | Detached records naming the `ObjectId` they sign |
| `Comment`, `ReviewVerdict` | Review records on a Proposal or order: author, target Change and UIX's `CommentAnchor`; the text is an integrity-tracked span; a verdict adds `Accept` or `RequestChanges` |
| Lifecycle records | Items, revisions, change orders, Waivers, quality records |

### Scale targets

| Scope | Target (phase 4 unless marked) |
| --- | --- |
| Desktop | Local CAS up to 2 TiB; 10 million Changes per repository; contract 13.3's open and rebuild rows |
| Team server, 16 cores, 64 GiB | 200 active users, 50 live sessions, 1,000 Changes per minute, 20 TiB (phase 2) |
| Cloud cell | 50,000 active users; ref update p99 under 200 ms; 10 GB/s object fetch; 100 participants per session |
| Cloud workers | 10,000 cores per tenant within 5 minutes; first remote result for cached inputs under 1 s |
| Repository | 100 TiB of results; 10⁹ objects; where-used over 10⁶ Items under 1 s |

### Rust surface

```rust
// base-op: the operation contract
pub trait OpImpl: Send + Sync + 'static {
    const ID: OpId;                    // OpId::new("anvil", "blend")
    const VERSION: u32;                // behavior version, pinned in ingot.lock
    const GRADE: DeterminismGrade;
    const CLOSURE: ClosureHash;        // generated by `cargo xtask closure-hash`
    type Inputs: OpInputs;             // each input exposes its GeometryId or ObjectId
    type Outputs: OpOutputs;           // canonical: decode(encode(v)) == v
    fn effective_fidelity(&self, requested: Fidelity) -> Fidelity;
    fn cost(&self, sizes: &InputSizes) -> CostEstimate;   // priced upper bound
    fn eval(&self, cx: &OpCx, inputs: Self::Inputs) -> OpResult<Self::Outputs>;
}

/// What an operation returns when it produces no value.
pub enum Stop { Failure(Failure), Abort(Abort) }
impl From<Failure> for Stop { /* … */ }
impl From<Abort> for Stop { /* … */ }
pub type OpResult<T> = Result<T, Stop>;
// There is no From<Abort> for Failure and no From<Failure> for Abort (KLN-O-ABORT-2).

/// Deterministic and typed: memoized, catchable with `try`, rendered `<family>/<snake_case>`.
#[non_exhaustive]
pub struct Failure { pub code: FailureCode, pub detail: Value, pub why: String, pub fixes: Vec<Fix> }

/// Environmental: never memoized, never observed by `try`. Closed.
pub enum Abort {
    Cancelled, ResourceExhausted, DeviceLost, WorkerLost,
    BudgetExhausted, DemandDepthExhausted, FuelCeilingExceeded,
}

/// Type-erased operations, held by Kiln and called by name.
pub trait DynOp: Send + Sync {
    fn id(&self) -> OpId;
    fn version(&self) -> u32;
    fn grade(&self) -> DeterminismGrade;
    fn closure_hash(&self) -> ClosureHash;
    fn effective_fidelity(&self, requested: Fidelity) -> Fidelity;
    fn cost(&self, sizes: &InputSizes) -> CostEstimate;
    fn eval_dyn(&self, cx: &OpCx, inputs: &[Value]) -> OpResult<Vec<Value>>;
}
impl<T: OpImpl> DynOp for T { /* decode Inputs from Values, encode Outputs */ }

pub struct OpRegistry { ops: BTreeMap<(OpId, u32), Arc<dyn DynOp>> }
impl OpRegistry {
    pub fn register(&mut self, op: Arc<dyn DynOp>) -> Result<(), RegistrationError>;
}
// Each operation-family crate exports `pub fn register(r: &mut OpRegistry) -> Result<(), RegistrationError>`;
// `engine` calls them in a fixed order.

/// What a native operation may use: no clocks, ambient randomness or I/O.
#[derive(Clone)]
pub struct OpCx(Arc<OpCxInner>);           // Send + Sync; moved into pool tasks by value
impl OpCx {
    pub fn safe_point(&self) -> Result<(), Abort>;  // due every 10 ms of monotonic time per thread
    pub fn rng(&self, stream: u64) -> Philox4x32;   // keyed as Kiln's random-stream rule says
    pub fn work_budget(&self) -> Option<WorkBudget>;
    pub fn fidelity(&self) -> Fidelity;             // the effective fidelity
    pub fn progress(&self, done: u64, total: u64);  // never keyed
}

pub trait Differentiable: OpImpl {
    fn tangent(&self, cx: &OpCx, inputs: &Self::Inputs, dx: &Tangents) -> OpResult<Tangents>;
    fn adjoint(&self, cx: &OpCx, inputs: &Self::Inputs, y_bar: &Cotangents) -> OpResult<Cotangents>;
}

pub struct NodeKey(ObjectId);              // the items of contract 7.2 for the node's kind
pub enum Fidelity { Preview, Interactive, SignOff }
pub enum DeterminismGrade { Portable, ClassExact, Certified }

// cas
pub struct ObjectId { alg: HashAlg, digest: [u8; 32] }   // in base-id
#[non_exhaustive] pub enum HashAlg { Sha256 = 1 }
pub trait CasStore: Send + Sync {
    async fn get(&self, id: ObjectId) -> Result<Bytes, CasError>;   // verified; mismatch is Corrupt
    async fn has_many(&self, ids: &[ObjectId]) -> Result<BitVec, CasError>;
    async fn put(&self, kind: ObjectKind, canonical: Bytes, domain: &EncryptionDomain)
        -> Result<ObjectId, CasError>;
    async fn lease(&self, ids: &[ObjectId], ttl: Duration) -> Result<LeaseId, CasError>;
}

// repo
pub trait MergeDriver: Send + Sync {
    /// Checks the merge conditions in order; never writes refs. Live sessions call it too.
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

### WIT packages

```wit
package crucible:host@0.1.0;          // KLN; frozen with the other WIT packages (contract 13.1)

interface diagnostics { emit: func(d: diagnostic); }                 // write-only, never keyed
interface progress    { report: func(done: u64, total: u64); }       // write-only, never keyed
interface cas {                                                      // reads reachable objects only
    read: func(h: handle, range: option<byte-range>) -> result<list<u8>, cas-error>;
}
interface parallel {                                                 // implemented by PLT
    map-chunks: async func(count: u32, input: list<u8>) -> result<list<list<u8>>, chunk-error>;
}
interface chunk-worker {                                             // exported by every world importing `parallel`
    chunk: func(index: u32, input: list<u8>) -> result<list<u8>, u32>;
}
```

```wit
package crucible:archive@1;            // frozen at phase 1, never changed

world op {
    import crucible:host/cas;
    import safe-point: func() -> result<_, abort>;
    import rng-block: func(stream: u64, counter: u64) -> list<u32>;
    import progress: func(done: u64, total: u64);
    export eval: func(op: string, version: u32, inputs: list<object-id>, fidelity: fidelity)
        -> result<list<object-id>, stop>;   // outputs are CAS objects tagged with their encoding version
}
```

### Limit outcomes

| Outcome | Kind | Meaning |
| --- | --- | --- |
| `kiln/work_limit { kind, limit }` | `Failure` | An operation's declared search or work limit |
| `kiln/fuel_exhausted { used, limit }` | `Failure` | The fuel a key declares |
| `kiln/stack_exhausted { limit }` | `Failure` | The declared stack depth |
| `kiln/memory_limit { limit }` | `Failure` | The declared memory maximum; host failure below it is `ResourceExhausted` |
| `BudgetExhausted` | Abort | A work budget or the Evaluation's fuel governor |
| `DemandDepthExhausted` | Abort | Nested demands past 10,000 (default) |
| `FuelCeilingExceeded` | Abort | An organization ceiling below a source limit, at admission |
| `ResourceExhausted` | Abort | Host memory, disk or device capacity |

### `api` methods

| Methods | Group | Agents |
| --- | --- | --- |
| `read.tree`, `read.source`, `read.history`, `read.audit`, `read.where_used`, `read.bom`, `read.search_items` | Read | Access-filtered; untrusted text by handle |
| `edit.apply`, `edit.stream`, `edit.revert`, `edit.create_branch`, `edit.undo` | Edit | Own branches only |
| `evaluate.*`, `evaluate.subscribe`, `evaluate.cancel` | Evaluate | Within budget |
| `compare.diff`, `compare.merge_preview` | Compare | Allowed |
| `propose.*`, including `change_request`, `change_order`, `mass_change`, `merge`, `policy`, `waive`, `declassify`, `purge`, `endorse_text` | Propose | Under AGT's rules; `policy` only from clean contexts; `merge`, `waive`, `declassify`, `purge` and `endorse_text` human-only |
| The `release` and `run_rig_test` Act kinds, and the `release_data` family | Act | May prepare; never approve |

### Event types

`change.created`, `ref.updated`, `ref.conflicted`, `tag.created`; `evaluation.completed`, `evaluation.aborted`; `proposal.opened`, `proposal.updated`, `proposal.merged`, `ci.completed`, `check.failed`, `evidence.received`, `evidence.pinned`; `change_request.created`, `change_order.submitted`, `change_order.stage_completed`, `change_order.approved`, `change_order.returned`, `release.created`, `change_notice.issued`, `item.state_changed`, `waiver.signed`; `capa.opened`, `capa.closed`, `obsolescence.found`, `compliance.alert`, `vulnerability.affected`, `policy.changed`, `audit.anomaly`, `budget.threshold`.

### 21 CFR Part 11 mapping

| 21 CFR Part 11 | Crucible mechanism |
| --- | --- |
| 11.10(a), (b) | Validation package from this tab's oracles; PDF/A plus JSON exports with an offline verifier |
| 11.10(c), (e) | Retention locks and purges; transaction and audit logs |
| 11.10(f) to (k) | Lifecycle guards; Cedar; device-signed records; training records; controlled documentation |
| 11.30 | The cloud treated as an open system: domain encryption, signed records, end-to-end mode [21 CFR 11.30] |
| 11.50, 11.70 | Name, time and meaning on every rendering; meaning and signer inside the signed challenge; one `ObjectId` per signature |
| 11.100 to 11.300 | One principal per person; re-authentication per signing; AAL3 credentials |

## State of the art

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Incremental evaluation | Suspending scheduler with constructive traces [Mokhov 2020]; Adapton [Adapton] | Salsa [Salsa algorithm]; Buck2's DICE [Buck2 DICE] | Adopt, with multi-output memo entries and requested-fidelity keys | Re-executed set on 500 edits; contract 13.3 rebuild rows |
| Early cutoff | Value equality with lazy content identity | Salsa; Nix content-addressed derivations [Nix RFC 62] | Equality interactively, `ObjectId` for sharing | Dependents within the drag budget |
| Shared build cache | Bazel Remote Execution API v2 [Bazel REAPI proto]; signed realisations | Bazel with Buildbarn or EngFlow | Adopt the idea, with attestation, microVMs and two-builder agreement | Hit rate for 20 people on GP3 and GP4; target 90% |
| Eviction | GreedyDual-Size [Cao 1997] | LRU | Adopt | Rebuild under 256 MiB; target within 2× of unbounded |
| Deterministic testing | Whole-system deterministic simulation [FoundationDB testing] | FoundationDB | Adopt for Kiln, sync, collector and server | Simulated hours per night |
| Content hashing | SHA-256 against BLAKE3 | BLAKE3 [BLAKE3] | SHA-256 for every object, for FIPS approval and one identity space | KLN-O-CAS-4 |
| Chunking | FastCDC [Xia 2016]; prolly trees [Dolt prolly trees] | Rabin chunkers; Dolt | Name-free segments; FastCDC for Blobs; rules frozen per type tag | Deduplication between Changes; target 95% |
| Numeric compression | pcodec [pcodec]; shuffling plus zstd; meshoptimizer [meshoptimizer] | zstd on raw arrays | Per-chunk codecs | Ratio and decode speed |
| Encrypted deduplication | Server-aided message-locked encryption [Bellare 2013] | Convergent encryption | Domain-keyed derivation | Cross-domain confirmation test |
| Version control | Git's SHA-256 objects; Jujutsu's operation log and conflicts [Jujutsu conflicts] | Git, Jujutsu | Changes, transaction log, first-class conflicts | No lost Change under simulation |
| CAD history and merge | Onshape microversions; GumTree; Mergiraf [Mergiraf] | Onshape, which merges whole tabs, cannot select changes within a tab and cannot merge drawings [Onshape merging] | Block-level merge, drawings included, refusing worse verdicts, new interference, touched-entity and connectivity conflicts | KLN-O-MERGE-1, with the share of seeded two-branch edits that merge clean beside the share a per-tab merge keeps |
| Live collaboration | A server-ordered log with client rebase [Replicache]; server-defined order [Figma multiplayer] | Figma; Replicache | One `MergeDriver` for live and branch merges | KLN-O-COLLAB-1, KLN-O-COLLAB-2 |
| Set reconciliation | Range-based set reconciliation [Meyer 2022] | Full listings | Adopt for tier anti-entropy | Bytes against the difference size |
| Authorization | Cedar [Cutler 2024] | Open Policy Agent | Adopt, with the signature table compiled to policies | p99 decision under 1 ms (target) |
| Tamper-evident logs | Merkle logs as C2SP tlog-tiles with witnesses [C2SP tlog-tiles] | Certificate Transparency; Sigstore Rekor [Sigstore] | Adopt | Fork detection under fault injection |
| Long-lived signatures | ML-DSA [NIST FIPS 204] | Classical-only signing | Dual signatures from phase 2 | Verification under each algorithm |
| PLM change control | Change request, order and notice workflows with effectivity | Windchill, Teamcenter, Arena [Arena change], Fusion Manage | Orders as Proposals; Approvals over subject digests; typed review routes | Scripted-order cycle time; the phase 3 assessment |
| Variant management | 150% BOM with variant conditions | Teamcenter Product Configurator [Teamcenter configurator] | Abstract interpretation and SAT | KLN-O-PLM-5; solver time on 200 parameters |
| Browser persistence | OPFS sync access handles; `opfs-sahpool` [SQLite Wasm persistence] | One engine per tab | One engine per origin | KLN-O-DEPLOY-1 |

| Capability | Incumbent and its documented feature | Crucible's capability row and phase | Standing |
| --- | --- | --- | --- |
| Branch merge | Onshape merges each tab by Keep, Merge or Replace, cannot select individual changes within a tab, and offers no Merge for drawings [Onshape merging] | Proposals and merge: source, verdict, touched-entity, interference and connectivity conditions; 1 to 3 | Ahead: block-level merge, drawings included, that refuses a merge breaking a check |
| Version history | Onshape records every change as a microversion [Onshape API intro] | Changes and transaction log; 0 | Equal, and any repository action undoes as one transaction |
| Change workflows | Windchill workflow templates assign activities to roles, define the flow of control and route by evaluating expressions [Windchill workflow] | Review routes and delegation; 2 | Equal: routes are typed records whose conditions read the evaluated subject |
| Approval delegation | Windchill users delegate work to another user on days they are unavailable [Windchill delegate] | Review routes and delegation; 2 | Equal: never to an agent, and two people for physical-effect or controlled approvals |
| Change approvals | Arena routes approvals electronically from change request to change order [Arena change] | Change requests, orders and notices; 2 | Ahead: an Approval signs the subject digest, so a rebase keeps it and any content change voids it |
| Effectivity | Windchill supports Serial, MSN, Block, Lot and Date effectivity [Windchill effectivity] | Effectivity; 3 | Equal |
| Variant configuration | Teamcenter Product Configurator [Teamcenter configurator] | Variants and 150% BOM; 3 | Ahead: a SAT solver proves the rules consistent |
| Shape search | Geolus finds similar parts whatever they are named [Siemens Geolus] | Classification and shape-similarity search; 2 | Ahead: exact duplicates by `GeometryId` across every readable repository |
| Mass change | Windchill swaps a part number in every assembly that uses it [Windchill mass change] | Mass change; 3 | Ahead: one Proposal per repository, each with its own CI |
| Quality management | Windchill ships CAPA, Nonconformance Management, Customer Experience Management and Audit Management [Windchill quality] | Quality records; 3 | Equal: effectiveness is an ordinary check |
| Multi-CAD file management | Teamcenter manages AutoCAD, Inventor, CATIA, Creo, NX, Solid Edge and SOLIDWORKS files in multi-CAD assemblies [Teamcenter MCAD] | Foreign native CAD files; 3 | Later: references are traced, files are never edited, and before phase 3 they are opaque Assets |
| Program and schedule management | Teamcenter Program Planning and Schedule Manager [Teamcenter program planning] | None | Out of scope: external project systems read Items, BOMs and release events through ECO's connectors |

## Platform notes

| Platform | Risk | Decision |
| --- | --- | --- |
| Windows | Open packs cannot be replaced; long paths; case-insensitive names | Replace by rename after close; long-path APIs; paths differing only in case or normalization rejected |
| macOS | Case- and normalization-insensitive file system; App Sandbox | The same path rule; security-scoped bookmarks (PLT) |
| Linux | Weak `fsync` on some configurations | Write-then-rename with `fsync` on file and directory; simulated torn writes |
| Browsers | Storage eviction; exclusive OPFS handles; shared memory only under cross-origin isolation [MDN SharedArrayBuffer] | Persistent storage and eager pushes; one engine per origin, coordinated by Web Locks [MDN Web Locks]; `crypto.subtle` hashing; cancellation by worker termination |
| Browsers | Origin-bound WebCrypto keys | WebAuthn device keys, re-enrolled when storage is cleared |
| iPadOS and Android (Tier 2) | Memory-pressure kills | Heavy Evaluations run remotely |
| Servers | FoundationDB operations burden; uneven conditional writes on S3-compatible stores | SQLite or PostgreSQL on team servers; ref updates through the metadata store |
| Air-gapped | No federation, time source or updates | Local identity provider; signed bundles; the clock audited against a site source |

## Interfaces with other subsystems

| To | What | Types | Phase |
| --- | --- | --- | --- |
| ANV, FLX, COV, MFG, ELX | The operation contract and registry; `NodeKey` composition and two-stage keys; the limit catalog; name-free random streams; derivatives; retired versions through the archive world | `OpImpl`, `DynOp`, `OpRegistry`, `OpCx`, `OpResult`, `Stop`, `Failure`, `Abort`, `Differentiable`, `NodeKey` | 0 |
| ING | Keys with `CallSite`s, code hashes, requested fidelity, overrides and limits; front-end stage memoization; ceiling-free `Undecided`; span integrity | `NodeKey`, `ResultStatus`, `Abort` | 0 |
| Every tab | Memoized, progressive evaluation with cost estimates; the CAS | `Kiln::demand`, `ResultEvent`, `ResultStatus`, `CasStore`, `ObjectId` | 0 |
| ANV, FLX, PLT | Grades and class acceptance; witnesses; what attestation signs; the attestation service, packaged by PLT; the `crucible:host` package, whose `parallel` PLT implements | `DeterminismGrade`, `PlatformClass`, `crucible:host` | 0 to 2 |
| COV, FLX, MFG | Evidence records pinned by `CheckId`; evidence signers; policy packages and allowances read as pinned inputs; Waivers | `CheckOutcome`, Evidence and allowance records | 1 |
| UIX, AGT | Changes, merge, diffs, Proposals, `ReviewVerdict` and `Comment` records, live sessions, locks, span provenance, where-used, review-route progress, the per-user view store | `ChangeId`, `MergeDriver`, `Conflict` | 1 (live sessions 2) |
| MEC, MFG, ELX | Items, per-kind definitions, effectivity, BOM views per `Site`, variant semantics, change orders and manufacturing change orders, program states and the `Proven` gate, parts policy, context-pin entries in `ingot.lock` | Item and revision records, `ItemDefinition` | 1 to 3 |
| MFG | The approver directory the machine gateway pins; first-article records | Signature records | 2 |
| AGT | Write-down enforcement at `repo`; recipient records; `ControlAuthorization`s; the signature table compiled to Cedar; signature records; the audit log; the `release_data` stage; local-device principals | `Labels`, signature records, `PrincipalId` | 1 |
| ECO | Leaf inputs; event types; release-data records; the system-of-record policy; the obsolescence check over catalog lifecycle events; the quality connector world's records | Event types, Item and quality records | 1 to 3 |
| UIX | Item search results and duplicate candidates; quality-record and route views | `read.search_items` results | 2 |

## Oracles

Oracles live in `oracles/kln/`, a protected workspace that builders cannot write. Each has a held-out split chosen by a keyed hash or generated from a seed drawn at CI time (contract 3, principle 6); those marked held-out also keep a fixed held-out corpus.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| KLN-O-FPRINT-1 | Registration and closure hashes | Recorded hashes match; a changed closure hash is refused; planted cases, a bumped third-party patch version and an edit in `anvil-topo`, are each refused; registration order is identical across runs |
| KLN-O-RETIRE-1 | Retired versions | A golden product whose pins are all retired rebuilds through `crucible:archive/op@1` with identical hashes; a retired GPU path causes no shared-cache cross-talk |
| KLN-O-WIT-1 | `crucible:host` | Published WIT and bindings match this tab; a hard-coded `ObjectId` of a confidential object cannot be read; a world importing `parallel` without exporting `chunk-worker` fails to link |
| KLN-O-MIN-1 | Minimal re-execution | On 500 scripted edits, comment-only and fuel-only included, the re-executed set equals the reference |
| KLN-O-EQUIV-1 | Incremental equals from-scratch | After every edit and upgrade, identities equal a cold build's |
| KLN-O-SITE-1 | Site keys and two stages | Equal calls at two sites get distinct `EntityId`s; designs sharing a failing geometric stage get fixes naming their own bindings |
| KLN-O-ROUNDTRIP-1 | Canonical values | Outputs from memory and from the CAS give identical dependents |
| KLN-O-ABORT-1 | Aborts | Faults at random Ops in 10,000 Evaluations; every memo entry and CAS object equals the fault-free value |
| KLN-O-ABORT-2 | No conversion between `Failure` and `Abort` | A `trybuild` compile-fail suite proves neither conversion exists and that `?` on a `Result<_, Abort>` yields only `Stop::Abort` |
| KLN-O-LIMIT-1 | Limits | `f(n) = f(n + 1)` aborts with `DemandDepthExhausted` on every Tier 1 target, leaving no memo entry; low ceilings refuse at admission |
| KLN-O-SIM-1 | Kiln, sync, collector, server | Seeded fault simulation loses no Change and caches no wrong value; failing seeds replay |
| KLN-O-PROG-1 | Progressive results, drag lane, overrides, fidelity keys | One generation per frame; overridden results never answer other requests; an `Interactive` feature result never answers a `SignOff` demand; after an `Interactive`-ceiling Evaluation, a `SignOff`-ceiling one with warm caches shows `Pending`, then the decided value |
| KLN-O-CANCEL-1 | Cancellation | 10,000 randomly cancelled Evaluations equal clean ones, threaded and unisolated web builds included |
| KLN-O-EVICT-1 | Eviction | A 256 MiB budget never changes results; rebuild within 2× of unbounded (target) |
| KLN-O-BUDGET-1 | Budgets | Caps exceeded by at most one safe-point interval; `BudgetExhausted` never cached |
| KLN-O-DERIV-1 | Derivatives | A Taylor test of a three-Op chain gives order 2 ± 0.1; adjoints resumed from evicted checkpoints are bit-identical |
| KLN-O-REMOTE-1 | Remote evaluation | Local and remote golden-product Evaluations give identical `ObjectId`s |
| KLN-O-TRUST-1 (held-out) | Shared-cache integrity | Forged, replayed, cross-tenant and single-builder attestations refused for gates; planted mismatches caught by fan-out spot checks; a package escaping identically on every builder reaches only its tenant; forged External Op outputs fail receipts |
| KLN-O-LABEL-1 | Labels | Labels reach every derived value; relabelling unchanged bytes re-executes nothing; write-down and out-of-region placement refused; a merged supplier STEP import gives trusted geometry and untrusted names; an uncleared clone sees only the declared derived views; a probing agent exhausts its budget before recovering a seeded dimension; an expired device lease leaves only ciphertext; unsatisfied scope names show as `restricted`; a foreign national without a `ControlAuthorization` cannot read EAR 9E003 data |
| KLN-O-LABEL-2 | End-to-end mode | Servers hold no plaintext; keys reach only eligible recipients; a customer-hosted tier shares only among that customer's builders |
| KLN-O-DET-1 | Bit equality per class | Every operation's corpus on every Tier 1 target, under perturbations, gives one identity per class; a witness check reproduces on every builder |
| KLN-O-CAS-1 | Integrity and codecs | Bit flips and truncation fail with `cas/corrupt` and heal from another tier; unknown codecs never decode |
| KLN-O-CAS-2 | Collection | Concurrent writers, leases and crashes lose no reachable object |
| KLN-O-CAS-3 | Encryption domains | No decryption or storage-name correlation across domains |
| KLN-O-CAS-4 | Hashing and deduplication | Throughput targets met; browser and native ids equal; 95% deduplication between Changes (target); renames re-chunk no geometry |
| KLN-O-PURGE-1 | Purge and retention locks | Purged bytes unrecoverable from every tier and backup; locked records refuse purge |
| KLN-O-REPL-1 | Replication | Fault-injected replication converges with no residency breach |
| KLN-O-DEPLOY-1 | Offline and browser ownership | An airplane-mode suite of every `api` method; two-tab edits with the owner closed lose no Change |
| KLN-O-DEPLOY-2 | Single-host team server | Install to first Proposal in 15 minutes on a KVM host and on a VM without nested virtualization; a microVM-escape tabletop leaves signing keys unreachable |
| KLN-O-DEPLOY-3 | Metadata replication | Zone-loss chaos tests lose no acknowledged write |
| KLN-O-DEPLOY-4 | Air-gapped bundles | A bundle round trip between two isolated sites verifies and imports |
| KLN-O-RESTORE-1 | Restore | The verifier finds every fault in seeded corrupt backups |
| KLN-O-GIT-1 | Git round trip | Export, re-import and rebuild keep every `EntityId` and `GeometryId` on every golden product |
| KLN-O-SPAN-1 | Span provenance | Instructions planted in merged comments, identifiers, part names, BOM text and embossed text return as `ExternalText`, also after Git, archive and federation round trips; spans written through a language-server connection or the CLI by a process are untrusted until confirmed; endorsement refuses the span's author |
| KLN-O-MERGE-1 (held-out) | Merge | Seeded conflicts of every kind found; no silent wrong merge; 90% of reference-clean merges clean (target); a width change beside a new hole and GP4 edits to adjacent welded members merge clean; two fillets on one edge and order-breaking inserts conflict; the report gives the share of seeded edits merging clean beside the share a per-tab merge keeps |
| KLN-O-DIFF-1 | Diffs | Identical Changes diff empty; deviation within its bound of a reference |
| KLN-O-LARGE-1 | Large assemblies | The 100,000-Instance repository benchmark meets its phase 4 target |
| KLN-O-XREF-1 | References | Rebuilding from `ingot.lock` reproduces every `ObjectId`; two branches moving one context pin differently give `Conflict::Lockfile` |
| KLN-O-COLLAB-1 | Live and branch merge agree | Any pair of concurrent edits merges to the same result live, after a short disconnection, and as two branches; unparseable blocks keep kind and position |
| KLN-O-COLLAB-2 | Sequencing, presence, locks | 50 participants with partitions converge; p95 keystroke-to-remote under 100 ms on one continent (target); locks never bypassed |
| KLN-O-COLLAB-3 | Offline rejoin | No Change lost; seeded conflicts found; fast-forward only without concurrent changes; disconnections over 60 s become branches |
| KLN-O-PLM-1 | Guards and the gate predicate | Unreleased children block release, naming every unmet guard; `Warning`-only failures do not block; an uncovered model-form part stays `Undecided`; a policy-package update changes no verdict until its Proposal merges |
| KLN-O-PLM-2 | Numbering and labels | Concurrent allocation yields no duplicates; labels follow the numbering policy |
| KLN-O-PLM-3 | Interchangeability | Seeded form-fit-function breaks all flagged |
| KLN-O-PLM-4 | Effectivity | Configured BOMs equal references at 1,000 random points; gaps and overlaps found |
| KLN-O-PLM-5 | Variants | Each valid configuration's 100% BOM equals brute force; a bolt circle's quantity follows its hole-count parameter |
| KLN-O-PLM-6 | BOM views | GP3's MBOM reconciles with matching quantities; two sites with different routings both reconcile against one EBOM |
| KLN-O-PLM-7 | Where-used | The index equals full recomputation nightly |
| KLN-O-PLM-8 | Manufacturing changes | EBOM-touching orders rejected; a part change returns exactly its dependent programs, imported ones included, to `Prototype`; no program reaches `Proven` without a first-article record whose run revision is merged |
| KLN-O-PLM-9 | Definition equivalence | A bit-level upgrade marks no Item modified, a 300 m hull included; a seeded out-of-tolerance change marks exactly its Item |
| KLN-O-PLM-10 | System of record | Releases round trip through a mock PLM without changing digests; an external approval record alone never releases |
| KLN-O-PLM-11 | Parts policy | Unapproved parts fail unless a Waiver names them |
| KLN-O-PLM-12 | Obsolescence | A seeded end-of-life event finds every affected released end item, with alternates and effectivity, and opens one change request each; released branches are unchanged |
| KLN-O-PLM-13 | Similarity search | In a 10,000-Item corpus, seeded exact duplicates rank first and seeded near-duplicates rank in the top five; unreadable Items never appear |
| KLN-O-PLM-14 | Quality records | A `Capa` cannot close before its effectiveness check passes; affected serials match where-used |
| KLN-O-PLM-15 | Mass change | A replacement across three repositories opens one Proposal each under one order, picks revision or new number per interchangeability, and releases only when all pass |
| KLN-O-PLM-16 | Foreign native CAD files | Reference graphs extracted at import match a reference for a seeded multi-file assembly; where-used and release completeness follow them |
| KLN-O-CHG-1 | Approval subjects | Stale content cannot be approved; a rebase or CI re-run with an unchanged subject keeps approvals; `act.commit` refuses a recomputed mismatch; a returned plan can be re-prepared at once |
| KLN-O-CHG-2 | Item definitions | Swapping a Software binary, Material version or document, or one attribute of each definitional class, voids an approval; a `#[was]` rename or non-definitional change does not |
| KLN-O-CHG-3 | Review routes and delegation | A seeded order set completes only when every stage's quorum holds; conditions add their stages; a delegated signature names both people; delegation to an agent or an uncleared delegate is refused |
| KLN-O-SIG-1 | Part 11 controls | Excised and transferred signatures fail; a record whose meaning was changed after signing fails; re-authentication required; exports verify offline; synced passkeys cannot sign |
| KLN-O-SIG-2 | Signature agility and FIPS mode | Dual-signed records verify under each algorithm and after re-timestamping; signing a year-old Change changes no `ChangeId` or tag; tenant LMS and non-approved FIPS algorithms refused |
| KLN-O-TRACE-1 | Traceability | The matrix equals the reference on GP1 to GP4 |
| KLN-O-COMPL-1 | Compliance | Seeded restricted substances all found; missing data is never compliant |
| KLN-O-VULN-1 | Vulnerability where-used | A seeded vulnerable library is traced to every affected serial |
| KLN-O-RELEASE-1 | Data release | Every exit runs its checks, shared branches and federation included; tainted or recent recipient changes never apply; scope or licence mismatches and a party listed the day before are refused; a scoped or licensed `internal` payload cannot leave as a local write |
| KLN-O-SHARE-1 (held-out) | Redaction | Planted strings, features and provenance ids never reach a package |
| KLN-O-SHARE-2 | Supplier packages and watermarks | Suppliers read nothing outside their packages; an unmodified file's keyed watermark identifies its release; a re-exported file is reported untraceable by mark and traced by the release-data record |
| KLN-O-SHARE-3 | Parametric quotas | Out-of-range or over-budget queries fail with `share/quota_exceeded` and are audited |
| KLN-O-POLICY-1 | Identity, authorization and the signature table | Fuzzing every row of contract 5.4's table, single-person mode included, against a reference model; Cedar analysis on every change; agents never sign, approve or release; a process using the desktop credential neither merges, endorses, waives nor exports as the person; forbidden break-glass actions refused |
| KLN-O-AUDIT-1 | Tamper evidence | Rewritten and forked logs detected by clients and witnesses; no tile holds labelled bytes |
| KLN-O-AUDIT-2 | Pseudonymity | After erasure, names are unrecoverable while logs and signatures verify; held records keep names |
| KLN-O-API-1 | `api` behavior | The conformance suite shared with AGT |
| KLN-O-EVENT-1 | Events | Receiver outages cause no loss or reordering per repository; no event above `public` carries a raw `ObjectId` |
| KLN-O-HW-1 | Evidence and safety | Spoofed, replayed and expired-calibration records rejected; a record from an unregistered or out-of-scope lab key rejected; Evaluations at one Change agree while a new record arrives unpinned; unmatched runner images cannot enrol; limit violations and missing risk assessments abort in simulation; no start reaches a device |

## Phasing

| Phase | KLN contribution to the gate |
| --- | --- |
| 0 | Kiln core with multi-output memo entries, requested-fidelity keys, cancellation, `Stop` and the limit catalog, priority classes, the operation registry and closure hashes; the local CAS; Kiln's corpus green in the determinism suite; deterministic simulation; Changes and the transaction log on the desktop |
| 1 | GP1 and GP2 along chain D (single-host team server, microVM Proposal CI, the approval page and release Acts, used in the dry run): progressive results, drag lane, overrides and budgets; `crucible:host` and the archive world; merge and Proposals; the signature table; labels, control authorizations, derived views for uncleared staff and span provenance; Git export; minimal lifecycle, per-kind definitions and the EBOM; policy packages and allowances; signature records; `release_data` and audited local writes; events; lab Evidence records with registered evidence signers; browser engine ownership |
| 2 | GP3 and GP4: live sessions; attested shared cache and External Op receipts; cloud workers; encryption domains and controlled devices; interference conflicts; change orders, review routes and delegation, manufacturing change orders, first-article records, Part 11 mode, dual signing; internal screening; traceability; MBOM per site and where-used; definition equivalence; connectors and parts policy; classification and shape-similarity search; the hardware runner; partial clone; restore and privacy |
| 3 | GP5: connectivity conflicts; effectivity; variants; computed interchangeability; compliance; vulnerability where-used; quality records; mass change; obsolescence monitoring; foreign native CAD files; supplier packages, derived views and quotas; end-to-end mode with customer-hosted tiers; air-gapped bundles; the assessment package |
| 4 | GP6: the 100,000-Instance repository and cloud-cell targets, beside contract 13.3's high-band row; Evidence records as Flux validation data; multi-region replication |
| 5 and later | Certification packages for DO-178C and DO-254 programs from the traceability matrix; program-scale effectivity; federation at scale |

KLN phases none of contract 13.4's shared capabilities. It owns two rows of the parity floor in phase 2 (review routing and delegation; shape-similarity search with exact duplicates by `GeometryId`) and three in phase 3 (quality records; mass change across repositories; foreign native CAD files as Document Items with reference graphs), each at the phase the floor names.

## Open questions

1. **Freedom to operate for history and merge.** Counsel's search at the phase 0 gate covers Changes, branches, merge and live sessions (contract 13.1). If it finds a claim that reads on per-Change history or on merge by provenance, the design changes before the phase 1 freeze; this waits on counsel's opinion.

## Contract change requests

- **CCR-KLN-11, approval delegation.** Contract 5.4's signature table has no row for an `ApprovalDelegation`. Proposed row: subject the delegation record; signer the delegator with an approval credential; two people, one an export officer, when the scope covers physical-effect Acts or `controls` payloads; never an agent as delegate; the delegator may sign.
- **CCR-KLN-12, the derivative retention tier.** Contract 7.1 names the retention tier for saved transient-solve state `Checkpoint`, while "checkpoint" also names signed transparency-log heads (C2SP's term). Proposed: name the tier `StepState` and the objects "step state".

## Sources

| Key | Title | URL | Date opened |
| --- | --- | --- | --- |
| [Salsa algorithm] | Salsa, "The red-green algorithm" | https://salsa-rs.github.io/salsa/reference/algorithm.html | 2026-10-11 |
| [Salsa durability] | Salsa, "Durability" | https://salsa-rs.github.io/salsa/reference/durability.html | 2026-10-11 |
| [Buck2 DICE] | Buck2, "Modern DICE" | https://buck2.build/docs/insights_and_knowledge/modern_dice/ | 2026-10-11 |
| [Mokhov 2020] | Mokhov, Mitchell and Peyton Jones, "Build systems à la carte: theory and practice" (JFP 2020) | https://www.microsoft.com/en-us/research/publication/build-systems-a-la-carte/ | 2026-10-11 |
| [Mokhov 2018] | Mokhov, Mitchell and Peyton Jones, "Build systems à la carte" (PDF, 2018) | https://www.microsoft.com/en-us/research/wp-content/uploads/2018/03/build-systems.pdf | 2026-10-11 |
| [Adapton] | Adapton project page (PLDI 2014) | https://www.cs.umd.edu/~hammer/adapton/ | 2026-10-11 |
| [Bazel REAPI] | Bazel Remote APIs | https://github.com/bazelbuild/remote-apis | 2026-10-11 |
| [Bazel REAPI proto] | Bazel Remote Execution API v2, `remote_execution.proto` | https://github.com/bazelbuild/remote-apis/blob/main/build/bazel/remote/execution/v2/remote_execution.proto | 2026-10-11 |
| [Nix RFC 62] | Nix RFC 62, content-addressed paths | https://github.com/NixOS/rfcs/blob/master/rfcs/0062-content-addressed-paths.md | 2026-10-11 |
| [Cao 1997] | Cao and Irani, "Cost-Aware WWW Proxy Caching Algorithms" (USITS 1997) | https://www.usenix.org/conference/usits-97/cost-aware-www-proxy-caching-algorithms | 2026-10-11 |
| [Cao 1997 paper] | Cao and Irani, full paper (PDF) | https://www.usenix.org/legacy/publications/library/proceedings/usits97/full_papers/cao/cao.pdf | 2026-10-11 |
| [Rust RFC 3514] | Rust RFC 3514, float semantics | https://rust-lang.github.io/rfcs/3514-float-semantics.html | 2026-10-11 |
| [Rust f64] | Rust standard library, `f64` | https://doc.rust-lang.org/std/primitive.f64.html | 2026-10-11 |
| [W3C WGSL] | WGSL specification (W3C); sections on IEEE-754 differences and reassociation read in the specification source | https://www.w3.org/TR/WGSL/ | 2026-10-11 |
| [gpuweb] | gpuweb repository (WGSL specification source) | https://github.com/gpuweb/gpuweb | 2026-10-11 |
| [Wasm relaxed SIMD] | WebAssembly relaxed SIMD proposal | https://github.com/WebAssembly/relaxed-simd/blob/main/proposals/relaxed-simd/Overview.md | 2026-10-11 |
| [Wasmtime Config] | Wasmtime `Config` documentation | https://docs.rs/wasmtime/latest/wasmtime/struct.Config.html | 2026-10-11 |
| [CORE-MATH] | CORE-MATH project | https://core-math.gitlabpages.inria.fr/ | 2026-10-11 |
| [ReproBLAS] | ReproBLAS | https://bebop.cs.berkeley.edu/reproblas/ | 2026-10-11 |
| [Random123] | Random123 | https://www.thesalmons.org/john/random123/ | 2026-10-11 |
| [FoundationDB testing] | FoundationDB, "Simulation and testing" | https://apple.github.io/foundationdb/testing.html | 2026-10-11 |
| [Xia 2016] | Xia et al., "FastCDC" (USENIX ATC 2016) | https://www.usenix.org/conference/atc16/technical-sessions/presentation/xia | 2026-10-11 |
| [Gregoriadis 2024] | Gregoriadis et al., "A Thorough Investigation of Content-Defined Chunking Algorithms for Data Deduplication" (arXiv 2409.06066) | https://arxiv.org/abs/2409.06066 | 2026-10-11 |
| [Dolt prolly trees] | Dolt, "Prolly trees" | https://www.dolthub.com/docs/architecture/storage-engine/prolly-tree/ | 2026-10-11 |
| [BLAKE3] | BLAKE3 repository | https://github.com/BLAKE3-team/BLAKE3 | 2026-10-11 |
| [NIST hash functions] | NIST, hash functions | https://csrc.nist.gov/projects/hash-functions | 2026-10-11 |
| [Git hash transition] | Git, hash function transition | https://git-scm.com/docs/hash-function-transition | 2026-10-11 |
| [Git partial clone] | Git, partial clone | https://git-scm.com/docs/partial-clone | 2026-10-11 |
| [Git merge strategies] | Git, merge strategies (`ort` and `recursive`) | https://git-scm.com/docs/merge-strategies | 2026-10-11 |
| [RFC 8949] | RFC 8949 (CBOR), section 4.2 | https://www.rfc-editor.org/rfc/rfc8949.html#section-4.2 | 2026-10-11 |
| [pcodec] | pcodec | https://github.com/pcodec/pcodec | 2026-10-11 |
| [meshoptimizer] | meshoptimizer | https://github.com/zeux/meshoptimizer | 2026-10-11 |
| [Bellare 2013] | Bellare, Keelveedhi and Ristenpart, "DupLESS" (USENIX Security 2013) | https://www.usenix.org/conference/usenixsecurity13/technical-sessions/presentation/bellare | 2026-10-11 |
| [S3 conditional writes] | Amazon S3, conditional writes | https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html | 2026-10-11 |
| [Meyer 2022] | Meyer, "Range-Based Set Reconciliation" (arXiv 2212.13567) | https://arxiv.org/abs/2212.13567 | 2026-10-11 |
| [Jujutsu concurrency] | Jujutsu, concurrency | https://docs.jj-vcs.dev/latest/technical/concurrency/ | 2026-10-11 |
| [Jujutsu conflicts] | Jujutsu, first-class conflicts | https://docs.jj-vcs.dev/latest/technical/conflicts/ | 2026-10-11 |
| [Onshape API intro] | Onshape API introduction (documents, workspaces, versions, microversions) | https://onshape-public.github.io/docs/api-intro/ | 2026-10-11 |
| [Onshape merging] | Onshape Help, "Merging" | https://cad.onshape.com/help/Content/merge.htm | 2026-10-12 |
| [Mergiraf] | Mergiraf architecture | https://mergiraf.org/architecture.html | 2026-10-11 |
| [Figma multiplayer] | Figma, "How Figma's multiplayer technology works" | https://www.figma.com/blog/how-figmas-multiplayer-technology-works/ | 2026-10-12 |
| [Replicache] | Replicache, "How Replicache works" | https://doc.replicache.dev/concepts/how-it-works | 2026-10-12 |
| [Cedar docs] | Cedar documentation | https://docs.cedarpolicy.com/ | 2026-10-11 |
| [Cutler 2024] | Cutler et al., "Cedar: A New Language for Expressive, Fast, Safe, and Analyzable Authorization" (OOPSLA 2024) | https://www.amazon.science/publications/cedar-a-new-language-for-expressive-fast-safe-and-analyzable-authorization | 2026-10-11 |
| [C2SP tlog-tiles] | C2SP tlog-tiles | https://github.com/C2SP/C2SP/blob/main/tlog-tiles.md | 2026-10-11 |
| [SLSA levels] | SLSA v1.1 build levels | https://slsa.dev/spec/v1.1/levels | 2026-10-11 |
| [Sigstore] | Sigstore overview | https://docs.sigstore.dev/about/overview/ | 2026-10-11 |
| [TUF] | The Update Framework overview | https://theupdateframework.io/docs/overview/ | 2026-10-11 |
| [Debenedetti 2025] | Debenedetti et al., "Defeating Prompt Injections by Design" (CaMeL, arXiv 2503.18813) | https://arxiv.org/abs/2503.18813 | 2026-10-11 |
| [Willison 2025] | Willison, "The lethal trifecta for AI agents" | https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/ | 2026-10-11 |
| [NIST CMVP] | NIST Cryptographic Module Validation Program | https://csrc.nist.gov/projects/cryptographic-module-validation-program | 2026-10-11 |
| [NIST CMVP 5314] | NIST CMVP, certificate 5314 (AWS-LC 3 Cryptographic Module, static) | https://csrc.nist.gov/projects/cryptographic-module-validation-program/certificate/5314 | 2026-10-11 |
| [NIST FIPS 140-3 transition] | NIST, FIPS 140-3 transition effort | https://csrc.nist.gov/projects/fips-140-3-transition-effort | 2026-10-11 |
| [aws-lc-rs] | aws-lc-rs | https://github.com/aws/aws-lc-rs | 2026-10-11 |
| [NIST FIPS 204] | NIST, FIPS 204, "Module-Lattice-Based Digital Signature Standard" | https://csrc.nist.gov/pubs/fips/204/final | 2026-10-11 |
| [NIST SP 800-38D] | NIST SP 800-38D, GCM and GMAC | https://csrc.nist.gov/pubs/sp/800/38/d/final | 2026-10-11 |
| [NIST SP 800-56C] | NIST SP 800-56C Rev. 2, key-derivation methods | https://csrc.nist.gov/pubs/sp/800/56/c/r2/final | 2026-10-11 |
| [RFC 5869] | RFC 5869, HKDF | https://www.rfc-editor.org/rfc/rfc5869.html | 2026-10-11 |
| [NIST SP 800-63B-4] | NIST SP 800-63B-4, Authentication and Authenticator Management | https://pages.nist.gov/800-63-4/sp800-63b.html | 2026-10-12 |
| [NIST SP 800-63B-4 binding] | NIST SP 800-63B-4, authenticator event management (binding) | https://pages.nist.gov/800-63-4/sp800-63b/events/ | 2026-10-12 |
| [21 CFR Part 11] | 21 CFR Part 11 (eCFR) | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11 | 2026-10-11 |
| [21 CFR 11.10] | 21 CFR 11.10 (Cornell LII) | https://www.law.cornell.edu/cfr/text/21/11.10 | 2026-10-11 |
| [21 CFR 11.30] | 21 CFR 11.30 (Cornell LII) | https://www.law.cornell.edu/cfr/text/21/11.30 | 2026-10-11 |
| [21 CFR Part 820] | 21 CFR Part 820 (eCFR) | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-820 | 2026-10-11 |
| [21 CFR 820.10] | 21 CFR 820.10 (Cornell LII) | https://www.law.cornell.edu/cfr/text/21/820.10 | 2026-10-11 |
| [FDA QS] | FDA, Quality System Regulation and medical device good manufacturing practices | https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-system-qs-regulationmedical-device-good-manufacturing-practices | 2026-10-11 |
| [FDA QMSR] | FDA, Quality Management System Regulation (QMSR) | https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr | 2026-10-11 |
| [22 CFR 120.54 eCFR] | 22 CFR 120.54 (eCFR) | https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120/subpart-C/section-120.54 | 2026-10-11 |
| [22 CFR 120.54] | 22 CFR 120.54 (Cornell LII) | https://www.law.cornell.edu/cfr/text/22/120.54 | 2026-10-11 |
| [22 CFR 120.56 eCFR] | 22 CFR 120.56 (eCFR) | https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120/subpart-C/section-120.56 | 2026-10-11 |
| [22 CFR 120.56] | 22 CFR 120.56 (Cornell LII, opened because eCFR refused the fetcher) | https://www.law.cornell.edu/cfr/text/22/120.56 | 2026-10-11 |
| [15 CFR 734.18] | 15 CFR 734.18 (eCFR) | https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-734/section-734.18 | 2026-10-11 |
| [DFARS 252.204-7012] | DFARS 252.204-7012 | https://www.acquisition.gov/dfars/252.204-7012-safeguarding-covered-defense-information-and-cyber-incident-reporting | 2026-10-11 |
| [ITA CSL] | International Trade Administration, Consolidated Screening List | https://www.trade.gov/consolidated-screening-list | 2026-10-11 |
| [EC RoHS] | European Commission, RoHS Directive | https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en | 2026-10-11 |
| [EC CRA reporting] | European Commission, Cyber Resilience Act reporting | https://digital-strategy.ec.europa.eu/en/policies/cra-reporting | 2026-10-11 |
| [EU CRA] | Regulation (EU) 2024/2847, Cyber Resilience Act (EUR-Lex) | https://eur-lex.europa.eu/eli/reg/2024/2847/oj/eng | 2026-10-11 |
| [CycloneDX] | CycloneDX specification overview | https://cyclonedx.org/specification/overview/ | 2026-10-11 |
| [GDPR Art 17] | GDPR Article 17 | https://gdpr-info.eu/art-17-gdpr/ | 2026-10-11 |
| [BetrVG] | Works Constitution Act (BetrVG), English translation | https://www.gesetze-im-internet.de/englisch_betrvg/englisch_betrvg.html | 2026-10-11 |
| [MDN SharedArrayBuffer] | MDN, `SharedArrayBuffer` | https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer | 2026-10-11 |
| [MDN sync access handle] | MDN, `FileSystemFileHandle.createSyncAccessHandle()` | https://developer.mozilla.org/en-US/docs/Web/API/FileSystemFileHandle/createSyncAccessHandle | 2026-10-11 |
| [MDN Web Locks] | MDN, Web Locks API | https://developer.mozilla.org/en-US/docs/Web/API/Web_Locks_API | 2026-10-11 |
| [MDN digest] | MDN, `SubtleCrypto.digest()` | https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest | 2026-10-11 |
| [SQLite Wasm persistence] | SQLite, "Persistent storage options" for Wasm | https://sqlite.org/wasm/doc/trunk/persistence.md | 2026-10-11 |
| [CloudEvents sequence] | CloudEvents, sequence extension | https://github.com/cloudevents/spec/blob/main/cloudevents/extensions/sequence.md | 2026-10-11 |
| [Firecracker start] | Firecracker, getting started | https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md | 2026-10-11 |
| [OMG ReqIF] | OMG, Requirements Interchange Format (ReqIF) | https://www.omg.org/spec/ReqIF/ | 2026-10-11 |
| [ASME Y14.35] | ASME Y14.35, revision of engineering drawings and associated documents | https://www.asme.org/codes-standards/find-codes-standards/revision-of-engineering-drawings-and-associated-documents | 2026-10-11 |
| [Windchill effectivity] | PTC Windchill Help Center, "Adding Effectivity" | https://support.ptc.com/help/wnc/r11.2.1.0/en/Windchill_Help_Center/ChgMgmtEffectivityAdd.html | 2026-10-11 |
| [Windchill workflow] | PTC Windchill Help Center, workflow template administration | https://support.ptc.com/help/windchill/r13.0.2.0/en/Windchill_Help_Center/workflow/WFAdminAbout.html | 2026-10-12 |
| [Windchill delegate] | PTC Windchill Help Center, "Delegate Work" | https://support.ptc.com/help/wnc/r12.0.1.0/en/Windchill_Help_Center/CalDelegWork.html | 2026-10-12 |
| [Windchill mass change] | PTC Windchill Help Center, "Mass Change Operation: Replacing an Existing Part" | https://support.ptc.com/help/windchill/r13.1.2.0/en/Windchill_Help_Center/changemanagement/ChgMgmtMassChangeReplace.html | 2026-10-12 |
| [Windchill quality] | PTC Windchill Help Center, Windchill Quality Management Solutions | https://support.ptc.com/help/windchill/plus/r13.0.2.0/pt_BR/Windchill_Help_Center/sublandingpages/wqOvw.html | 2026-10-12 |
| [Arena change] | Arena, change management overview | https://www.arenasolutions.com/products/plm/change-management/ | 2026-10-11 |
| [Teamcenter] | Siemens Teamcenter product page | https://www.siemens.com/en-us/products/teamcenter/ | 2026-10-11 |
| [Teamcenter configurator] | Siemens, "Introducing Teamcenter Product Configurator for variability management" | https://blogs.sw.siemens.com/teamcenter/introducing-teamcenter-product-configurator-for-variability-management | 2026-10-11 |
| [Teamcenter MCAD] | Siemens, Teamcenter MCAD design management | https://www.siemens.com/en-us/products/teamcenter/solutions/mcad-mechanical-design-management/ | 2026-10-12 |
| [Teamcenter program planning] | Siemens, "Program management in PLM has arrived" | https://blogs.sw.siemens.com/teamcenter/program-management-in-plm-has-arrived/ | 2026-10-12 |
| [Siemens Geolus] | Siemens, "How Geolus 3D shape search drives part re-use" | https://blogs.sw.siemens.com/teamcenter/how-geolus-3d-shape-search-drives-part-re-use/ | 2026-10-12 |
