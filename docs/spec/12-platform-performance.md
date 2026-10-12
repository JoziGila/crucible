# Platform and performance (PLT)

PLT runs Crucible on every machine: deterministic numerics, the compute and WebAssembly (Wasm) runtimes, the OS and browser layer, deployment, packaging, the build program and the performance targets. An engineer gets identical results on a Windows laptop, a Mac, a Linux server and a browser tab, so one computation serves the whole team and every later audit, which incumbents and clones do not promise. The mechanism is one canonical platform class, whose arithmetic (correctly rounded math, no implicit fused multiply-add, fixed reduction trees) leaves nothing to the processor, OS or thread count.

## Numerical determinism

Determinism lets a cached result stand in for a computation, so this section comes first. It shows what "the same bits everywhere" means for one design, and what it takes.

### The bracket on four machines

Take the canonical L-bracket of contract 6 and its check `static_margin`, which bounds the von Mises stress over the regular part of the study. A designer changes `width` from 60 mm to 80 mm on a Windows laptop. Kiln, the incremental evaluation engine, rebuilds the plate, the web and the fillet, solves the elasticity problem at `SignOff` fidelity and evaluates the check. Each result is stored in the content-addressed store (CAS) under its `ObjectId`, the hash of its bytes. It is found through its `NodeKey`, the hash of what produced it (contract 7.2).

Four machines then meet the same nodes.

| Machine | What happens | Why it matches |
| --- | --- | --- |
| The designer's laptop, x86-64 with AVX2, 8 threads | Computes every node | Reference run |
| A reviewer's MacBook in Safari, wasm32 with 128-bit SIMD, 10 workers | Opens the Proposal; every `NodeKey` hits the team cache, and a re-run of any node gives the same `ObjectId` | Same canonical class, so the same key and the same bytes |
| Two trusted builders, Linux x86-64 and Linux ARM64 | Recompute the gate's `SignOff` nodes and compare `ObjectId`s before the release (contract 7.8) | Bit identity across instruction sets is the release check |
| A regulator's audit machine in ten years | Re-runs the archived engine of that release | The archive pins the arithmetic, not the hardware |

Nothing in that table is free, because four ordinary things would break it:

- The fillet evaluates NURBS surfaces, where a native fast path uses fused multiply-add (FMA) instructions that round once instead of twice; wasm32 has no such instruction.
- The material model calls `exp` and `powf`, whose results Rust's standard library lets vary "by platform, Rust version" [Rust f64].
- The conjugate-gradient solver sums dot products across threads, and the laptop has 8 threads where the browser has 10.
- A GPU kernel may reassociate a sum.

Each would change the last bits, the `ObjectId` and so every key downstream.

PLT removes each source, and the rest of this section explains how. The payoff is concrete. The reviewer's browser shows the designer's numbers without recomputing them. The release gate's two builders agree, or the release stops. A decade-old release reproduces its STEP file and its check values bit for bit.

Incumbent numerics libraries do not offer this. Intel's oneMKL reproduces bits only at a fixed thread count, except for a few BLAS routines in its strict mode [Intel oneMKL reproducibility]. A clone that calls platform `libm` and parallel iterators gets different bits per machine and cannot share a cache across them.

Fast paths still exist. While the designer drags the `width` slider, the interactive stress preview comes from a native kernel that uses FMA, cached only under that machine's class. The `SignOff` check that gates the release always comes from the canonical class, so speed never leaks into a released number.

### Sources of divergence and their controls

Every way two machines can disagree has one control, and this table is the one list that the engine tabs cite. A source found later adds a row.

| Source | Evidence | Control |
| --- | --- | --- |
| Implicit contraction | Box2D found FMA "must be disabled for cross-platform determinism" [Box2D determinism] | Rust never contracts [Rust RFC 3514]; C and C++ build with `-ffp-contract=off` through the native-code register |
| Explicit FMA | `mul_add` runs in software on x86-64-v2 and wasm32 | Only in `detmath` and error-free transformations (D-PLT-18) |
| Platform math | Rust's `exp`, `sin` and `powf` vary by platform and version | `detmath` only; the std methods are disallowed by lint |
| Reduction order and width | Lane counts and thread counts differ | Deterministic combinators; the canonical horizontal order (D-PLT-15) |
| Approximate instructions | Reciprocal estimates differ by instruction set | Intrinsic allow-list |
| Cache-dependent blocking | faer's `gemm` sizes blocks from detected caches [gemm cache.rs] | `linalg` (D-PLT-34) |
| Floating-point environment | Foreign code may set flush-to-zero or a rounding mode | MXCSR or FPCR checked at Op start and end; a change aborts and reruns the Op |
| NaN bit patterns | Payloads are nondeterministic in Rust and Wasm [Wasm nondeterminism] | Canonical NaN in the CAS; the determinizer for Wasm |
| Relaxed SIMD | `relaxed_madd` may round once or twice [Relaxed SIMD] | Never used; rejected in Wasm |
| Hashes, addresses, threads | Hashes differ by pointer width; work stealing reorders work | The lints of D-PLT-49 |
| Names in orderings | Label invariance (contract 7.1) | Ties keep input order; canonical numbers come from geometry |
| GPU arithmetic | WGSL may reassociate, fuse and flush (GPU compute) | Per-pipeline classes; known-answer tests; integer exactness |
| Changed shared code | A fix in `linalg` or `simd` would alter released bits | Frozen versions in closure hashes (contract 4) |
| Toolchain and `detmath` upgrades | Code-generation bugs | Golden-hash checks on every bump; a changed hash blocks the bump or raises the epoch |

Engine tabs keep at most 150 words of their own determinism rules and cite this table for the rest. KLN owns determinism grades and the acceptance policy, contract 7.3 owns the rules, and PLT owns the mechanisms.

### The deterministic math library

A correctly rounded function returns the floating-point number nearest the exact result, and that number is unique. Every implementation that is correctly rounded therefore returns the same bits, whatever its algorithm or instruction set, which is why `detmath` exists.

`detmath` provides f64 and f32 elementary functions, scalar and batched, from exponentials to `lgamma`. Square root, division and the basic operations come from IEEE 754 hardware, which already rounds them correctly.

**Decision D-PLT-17:** `detmath` is correctly rounded wherever CORE-MATH is, and otherwise a fixed sequence of IEEE operations with a documented ulp bound; CORE-MATH's C sources (MIT) build behind its API on every target at milestone 1 of contract 13.2, functions then move to Rust, hot ones first, batched paths are compared against crmvec, and a function that misses its speed target gets a target of 3 times glibc instead, filed without blocking.
*Why:* a correctly rounded result is unique, so every path returns the same bits, and correct rounding is never traded for speed.
*Rejected:* platform libm; porting musl or FreeBSD libm (not correctly rounded); Box2D-style approximations (too inaccurate for CAD); faster functions with weaker rounding.

The C build sits in `bridges/core-math` behind safe functions, and it is the only native-code register entry allowed to affect results (Reference). Since glibc 2.43 integrates seven CORE-MATH functions, Crucible sets its own speed targets. On x86-64-v3, `exp` and `ln` stay within 1.5 times glibc and `pow`, `sin` and `cos` within 2 times. Under wasm32 they stay within 3 times native, and batched paths reach 2 times scalar.

FMA halves the cost of compute-bound kernels, yet x86-64-v2 and wasm32 lack it in hardware. The rule below keeps it out of canonical results and lets fast native variants serve the fidelities that are never released.

**Decision D-PLT-18:** No implicit contraction exists anywhere, and explicit `mul_add` appears in canonical code only inside `detmath` and error-free transformations; `CpuIsa` variants with FMA serve `Preview` and `Interactive` from phase 0 for sum-factorized kernels at p ≥ 3, dense GEMM and LU, and NURBS evaluation, other families need a measured penalty above 1.3 times, memory-bound operators at p ≤ 2 never get one, and `SignOff` recomputes canonically with the cost counted by Kiln.
*Why:* x86-64-v2 and wasm32 lack FMA, while compute-bound kernels halve their peak without it, and contract 7.3 forbids non-canonical results at `SignOff`.
*Rejected:* FMA in canonical kernels (software FMA in browsers); no FMA anywhere; FMA variants at `SignOff`.

### Platform classes

A platform class names where the same bits would come out again (contract 5.2). It enters every `NodeKey`, so results from different classes never share a cache entry by accident.

**Decision D-PLT-19:** One canonical class, `CpuCanonical { epoch }`, spans every Tier 1 CPU target at any thread count and instruction-set level, no CPU class names an operating system, and a GPU class is one pipeline on one verified device class: back end, device family, driver build, shader-compiler build and pipeline hash.
*Why:* with no OS-dependent arithmetic left, every target can share cached results, while each WGSL compiler fuses differently.
*Rejected:* one class per operating system and architecture; GPU classes keyed by vendor alone.

The four variants are `CpuCanonical`, `CpuIsa` (a native fast path for one instruction-set level, which may use FMA), `Gpu` (one verified pipeline) and `Unverified` (unlisted devices and external hosts). The verified-class registry is a signed data file built from GPU-lab runs. An epoch bump needs the founder's approval and an LTS boundary unless it fixes wrong results, and `cli` reproduces an old release with its epoch's archived engine.

**Decision D-PLT-20:** `CpuIsa`, `Gpu` and `Unverified` results never substitute for canonical ones, which a check, release or Proposal recomputes when it needs them; the one exception is a witness, a pinned non-canonical Field whose residual and error bound are computed canonically (contract 7.3).
*Why:* substitution would make a release depend on the machine that computed it first, while a witness keeps the check reproducible at the cost of one canonical residual.
*Rejected:* accepting any class within tolerance; no exception (forfeits cheap CPU certification of GPU solves).

Invalid numerics are typed `Failure`s. Where NaN is a legitimate value, the CAS writes the canonical quiet NaN.

### Cross-class agreement

Fast classes must stay honest even though their bits differ. The agreement harness compares every `CpuIsa` and verified `GpuClass` with the canonical class nightly, on golden products and the engine corpora.

**Decision D-PLT-35:** Classes A and B agree on a checked quantity q within a tolerance set by what they shared: with the same resolved `SolvePlan`, adaptive marks and steps, the tolerance is both classes' algebraic and floating-point parts plus a floor scaled by the Field norm; when marks or steps differ, the full `ErrorBudget` totals apply and the diverging marks are reported as a finding of their own; a failed `Guaranteed` or algebraic comparison opens an incident at once, an `Estimated` one after two consecutive nightly failures, and bifurcating or chaotic problems compare branch-invariant quantities or statistics.
*Why:* full budgets would let a class drift by the whole discretization error unseen, and a bound calibrated at α = 0.01 is exceeded by design, so single misses would open incidents every night.
*Rejected:* |q_A − q_B| ≤ E_A + E_B everywhere; residual rules and ulp tolerances (meaningless near zero).

FLX applies the same rule to its own corpora. B-rep Bodies must first match in topology before any quantity is compared.

### The determinism suite

The suite is the oracle behind every claim in this section. It runs on every merge on contract 7.3's representative set, and nightly on every other Tier 1 target and browser engine.

1. **Corpus.** Golden products, the ANV and FLX corpora, Wasm components, and 10,000 random operation graphs a night.
2. **Canonical identity.** Every hash matches on every target and executor.
3. **Schedule independence.** 1 to 64 threads, with injected stealing delays and allocator randomization.
4. **Out-of-core equivalence.** A 64 MiB budget forces chunks to disk.
5. **Linear algebra.** Factorizations under two cache-size settings.
6. **Floating-point environment.** A planted flush-to-zero library forces an Abort and a rerun.
7. **Native and GPU classes.** Repeated runs within a class are identical, and the agreement harness passes.
8. **`detmath`.** Univariate f32 functions exhaustively against MPFR, others on hard cases and 10⁹ random inputs a night.

A failure names the first diverging Op, both targets, the inputs and the first differing value. A nightly divergence bisects automatically, opens a severity-1 incident and blocks promotion to beta, not the merge queue, so one flaky target never stalls every builder.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Mechanism table | One control per divergence source, cited by every engine tab | A newly found source adds a row and a suite case | PLT-O-DET-1 | 0 |
| `detmath` C build | CORE-MATH C on every target at milestone 1 | A missing function fails the build | PLT-O-DET-4 | 0 |
| `detmath` Rust ports | Hot functions first; batched paths | A port differing from the C build is rejected | PLT-O-DET-4 | 0 to 1 |
| `detmath` speed | Per-function targets; a miss relaxes to 3 times glibc | Regression filed, never blocking | PLT-O-DET-8 | 1 |
| FMA variants | Named families first; others above a 1.3 times penalty; never at `SignOff` | Divergence beyond D-PLT-35 disables the variant | PLT-O-DET-6 | 0 (named families), 1 (others) |
| Floating-point environment guard | Checked at Op start and end | Abort and rerun, culprit logged | PLT-O-DET-7 | 0 |
| Platform classes | Four variants in `base-op`; signed GPU registry | Unlisted device: `Unverified`, local cache only | PLT-O-DET-1 | 0 |
| Epochs and archived engines | Approved bumps; archived builds reproduce old releases | Missing archive: agreement-rule comparison, reported | PLT-O-BLD-3 | 2 |
| No substitution | Canonical recomputation, or a witness | Uncertified non-canonical input: the check is `Undecided` | PLT-O-DET-6 | 1 |
| NaN canonicalization | Canonical quiet NaN in the CAS | Lint failure blocks the merge | PLT-O-DET-5 | 0 |
| Cross-class agreement | Shared-plan tolerance from algebraic and floating-point parts; full budgets when marks differ | Incident at once, or after two nightly `Estimated` misses | PLT-O-DET-6 | 1 |
| Determinism suite | Representative set per merge, the rest nightly, automatic bisection | Nightly divergence: severity-1 incident, beta blocked | PLT-O-DET-9 | 0 |

## The compute runtime

The compute runtime keeps a drag responsive on any number of cores without letting that number change a canonical result.

### Where the engine runs

**Decision D-PLT-12:** The UI talks to the engine only through `api`; the engine runs as an OS process on desktops, a worker in browsers and on iPadOS, threads on Android, or a remote `server`, and third-party code runs in sandboxes (D-PLT-31).
*Why:* one boundary keeps the UI identical on every target, and an engine crash leaves the window open while the engine replays its journal.
*Rejected:* one desktop process (a crash closes the window); one process per Op (too slow for a drag).

UI processes link only `api-schema`, the method catalog and codec, while the engine process links `api` and everything below it (contract 12). The layering check fails any UI crate that depends on `api`.

On desktops the UI and engine processes exchange `api` messages over a local socket and bulk display data (tessellations, Field samples) through shared rings. A ring is unsafe territory. The writer may still be writing while the reader looks, which Rust treats as a data race even when the bytes look valid.

**Decision D-PLT-50:** `platform-api` defines `SharedRing`, implemented only in `apps/platform-*`; the writer publishes a slot under an atomic sequence number, the reader copies the slot into its own memory with volatile reads and then re-checks the sequence (a seqlock), and only owned, validated bytes leave the ring.
*Why:* the copy turns cross-process memory into ordinary owned data for the renderer, so no `unsafe` code exists outside the crates contract 12 allows, and a torn read is retried rather than rendered.
*Rejected:* handing the renderer a borrowed view of mapped memory (a data race in Rust's model); sending display data through the socket (two extra copies of every tessellation).

On Linux a higher `oom_score_adj` makes the kernel stop the engine before the UI.

[[DIAGRAM diagrams/12-platform-process-model.jsx: process and thread model · four targets]]

Read each column as one target: tinted boxes run engine code, dashed boxes are sandboxed, and arrows are the only channels between the UI and the engine.

### Threads and pools

The engine separates work by how long a person will wait for it. A pool lane (`PoolLane`) is that separation: drag work must never queue behind an agent's rebuild.

| Thread or pool | Size | OS priority | Work |
| --- | --- | --- | --- |
| IO runtime (tokio natively, the event loop in browsers) | 2 workers plus a blocking pool | Normal | IPC, network, file IO |
| Drag pool (rayon) | One per logical core | QoS user-interactive; Windows above normal | Drag previews and per-pointer tools |
| Foreground pool (rayon) | One per logical core | QoS user-initiated; Windows normal | Selection, `Preview` results, awaited requests |
| Background pool (rayon) | One per core, halved on battery | QoS utility; EcoQoS; nice 10 | Rebuilds, `SignOff` work, prefetch |
| GPU queue thread | One per device | User-interactive | Encoding, submission, readback, device loss |

`PoolLane` has three values, `Drag`, `Foreground` and `Background`. AGT's `PriorityClass` maps onto them: `Drag` to `Drag`, `Foreground` to `Foreground`, and `Agent`, `Ci` and `Batch` to `Background`. "Interactive" names only a fidelity.

`Drag` work pauses `Foreground` work at its next chunk boundary until the lane idles, which never changes a reduction tree. Kiln also promotes a waiting background Op and calls `ComputePool::boost` for a running one. A `Drag` Op starts within 1 ms and a `Foreground` Op within 2 ms at p99 while the other pools are busy (targets).

**Decision D-PLT-13:** CPU parallelism uses rayon work-stealing pools, one per `PoolLane` natively and one pool with three lane queues in browsers, and all result-affecting parallelism goes through Crucible's deterministic combinators; no second scheduler enters before phase 4, and chili returns only if it beats rayon by 1.3 times on BVH builds and sparse assembly.
*Why:* rayon is the standard Rust work-stealing runtime and runs in browsers, and the combinators make results independent of thread count; a browser has one shared Wasm memory per engine, so its lanes are queues in one pool that apply the native pause rule at chunk boundaries.
*Rejected:* tokio for compute (futures starve under long kernels); a custom scheduler; two lanes (a drag waits behind agent work).

### The operation context

Every operation receives an `OpCx`, KLN's operation context in `base-op`. It is an owned, cheaply cloneable handle that is `Send + Sync`, and every method takes `&self`, so rayon chunks can share it.

PLT supplies what the context wraps: the pool handles, the memory budget, the `Monotonic` clock and the cancellation flag. `cx.safe_point()` reads an atomic flag and returns an Abort when the evaluation is cancelled. Operations call it at least every 10 ms of monotonic time on their thread, and every combinator calls it at each chunk boundary.

Operations return `OpResult<T>`, which is `Result<T, Stop>`, where `Stop` is a `Failure` or an `Abort` (contract 7.2). PLT's functions that can only be interrupted return `Result<_, Abort>`, which `?` converts into a `Stop`; nothing ever converts an Abort into a Failure.

Ops estimated above 10 core-seconds take a deterministic work budget from AGT's `Budget` and check it at safe points. Exhausting it is KLN's `BudgetExhausted` Abort.

### Deterministic parallel combinators

A parallel sum depends on how the work was split unless the split is fixed. The combinators fix it: data partitions and reduction trees depend on the input length only, never on threads or timing.

| Combinator | Contract | Order guarantee |
| --- | --- | --- |
| `det_for_each_chunk`, `det_map_collect` | Disjoint ranges; parallel map | Output in input order |
| `det_sum`, `det_reduce` | Pairwise reduction | Blocks of 2,048 elements; canonical lane i of 8 (f64) or 16 (f32) accumulates elements i, i + L, …; lanes reduce by a balanced tree over lane indices, and blocks by a balanced tree splitting n blocks at ⌈n/2⌉ |
| `det_scan` | Prefix scan | Fixed blocks and a block-offset tree |
| `det_sort_by_key` | Stable sort | Floats only as `NonNan<f64>`; ties keep input order, never a name-derived id |
| `exact_sum` | Partition-independent sum | Binned accumulation, only where partitions vary |

Binned summation costs about 4 times a plain dot product [ReproBLAS], so node-local reductions use `det_sum`, and Ingot's `sum` is `det_sum`. `exact_sum` serves sums whose partition varies, such as a distributed reduction across ranks. The combinators are free functions over `&OpCx`, and `OpCx` offers no second reduction API.

Rules that keep code on the combinators are lints, and each lint names the tool that enforces it.

**Decision D-PLT-49:** Every source-level determinism rule is enforced by a named mechanism: Clippy's `disallowed-methods` and `disallowed-types` for std math, `HashMap` and `HashSet`, rayon float reductions, thread-count queries and approximate intrinsics; cargo-deny `bans` with `wrappers` to keep faer out of every crate a `Portable` operation version depends on; and Crucible's own dylint library in `lints/` for values that no path can name (pointer or `usize` values reaching a `Hash` or an encoder, `as usize` casts of addresses, `f64::to_bits` and `is_nan` outside `detmath`, NaN payload inspection).
*Why:* Clippy's configuration bans items by fully qualified path but cannot follow a value into a hash [Clippy configuration]. cargo-deny's `wrappers` allow a direct dependency from listed crates and deny it everywhere else [cargo-deny bans]. Dylint runs custom `LateLintPass` lints from dynamic libraries [Dylint], and one operation family per crate lets each rule scope to `Portable` versions.
*Rejected:* promising lints without a mechanism; a fork of Clippy; review by eye.

### Memory

| Mechanism | Choice | Failure behavior |
| --- | --- | --- |
| Allocator | mimalloc v3 natively; Rust's wasm32 allocator in browsers | `try_reserve` failure: `ResourceExhausted` Abort |
| Budgets | A `MemoryBudget` tree for CAS residency, GPU staging and Op scratch | Waits 2 s for eviction, then the `ResourceExhausted` Abort |
| Scratch | A `bumpalo` arena per Op execution | Counts against the reservation |
| Mapped CAS objects | Read-only maps for objects of 1 MiB or more, local file systems only | Network or cloud-synced file system: buffered reads |
| Out-of-core buffers | `ChunkedBuffer<T>`: 1 MiB CAS chunks, CLOCK eviction | Hash mismatch: `CasError::Corrupt`, recomputed |

**Decision D-PLT-14:** mimalloc v3 is the native global allocator.
*Why:* it is MIT-licensed and runs on every Tier 1 OS and Wasm, and its project reports beating jemalloc and tcmalloc, in numbers from 2021 [mimalloc]; phase 0 re-measures mimalloc, jemalloc and snmalloc, and the choice cannot affect results.
*Rejected:* system allocators (behavior differs per OS); jemalloc (the common Rust bindings exclude Windows).

mimalloc is C, so it builds through the native-code register; wasm32 builds exclude it and use Rust's own allocator.

Maps serve only CAS objects, which Crucible writes once and never truncates. Another process can still truncate a mapped file, and an access past its end raises SIGBUS [Linux mmap]. Safe Rust cannot recover from that at an arbitrary load, so the engine process ends. The crash monitor records the faulting address's file; on restart the engine quarantines that object and replays its journal. Windows refuses to delete mapped files, so CAS collection defers them.

### SIMD dispatch

`std::simd` remains nightly-only and Arm's scalable vectors experimental [Rust scalable vectors]. `simd` detects the instruction set once and dispatches through a function table, and `CRUCIBLE_ISA` forces a lower level for tests.

**Decision D-PLT-15:** Every reduction, scan or cross-lane operation in `Portable` code follows the 8-lane f64 or 16-lane f32 tree of `det_sum` on every instruction set, and element-wise code uses any native vector width.
*Why:* only horizontal operations depend on lane count, and 512-bit virtual vectors force register spills on x86-64-v2 and 128-bit Wasm SIMD.
*Rejected:* 512-bit virtual vectors for all code; native-width reductions; scalar canonical code.

An intrinsic allow-list keeps approximate instructions such as `rcp14` and `FRECPE` out of canonical kernels. Dispatch uses pulp, and phase 0 evaluates fearless_simd 1.0, which promises "3 years of security updates", as its successor [Fearless SIMD 1.0].

**Decision D-PLT-2:** Native x86-64 builds target x86-64-v2 and dispatch hot kernels at run time to x86-64-v3 and x86-64-v4, and ARM64 builds target ARMv8 with NEON.
*Why:* every dispatched path gives identical canonical bits, so a low baseline costs speed only in cold code.
*Rejected:* an x86-64-v3 baseline (drops CPUs without AVX2); per-CPU builds.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Engine placement | Process, worker, Android threads or remote server; UIs link `api-schema` only | Engine crash: restart and replay | PLT-O-REL-2 | 0 |
| Shared display rings | `SharedRing` with a seqlock copy-out, only in `apps/platform-*` | Torn slot: re-read; no other crate maps shared memory | PLT-O-DET-5 | 1 |
| Pools and lanes | `Drag`, `Foreground`, `Background`; pausing at chunk boundaries; one pool with three queues in browsers | Start beyond 1 ms or 2 ms at p99 fails | PLT-O-RT-1 | 0 |
| Operation context | `OpCx` owned and `Send + Sync`; `&OpCx` everywhere; `OpResult` with `Stop` | `Failure: From<Abort>` does not compile | PLT-O-RT-1 | 0 |
| Deterministic combinators | Data partitions, fixed trees, canonical lane order | Divergence fails the suite | PLT-O-DET-2 | 0 |
| Determinism lints | Clippy, cargo-deny and dylint rules per D-PLT-49 | A lint failure blocks the merge | PLT-O-DET-5 | 0 |
| Cancellation and safe points | `safe_point` every 10 ms of monotonic time and at chunk boundaries; work budgets | Abort, never cached | PLT-O-WASM-3 | 0 |
| Memory budgets and allocator | Reservation tree; mimalloc v3 natively | `ResourceExhausted` Abort with a fix | PLT-O-RT-2 | 0 |
| Out-of-core buffers | Identical results in and out of core | `CasError::Corrupt`, recomputed | PLT-O-DET-3 | 1 |
| Mapped-object loss | SIGBUS ends the engine; the object is quarantined on restart | Journal replay after restart | PLT-O-REL-2 | 1 |
| ISA dispatch | Detection once; forced levels for tests | Unsupported forced level: startup error | PLT-O-DET-1 | 0 |
| Canonical horizontal order | `det_sum` lane tree for every horizontal operation | Divergence fails the suite | PLT-O-DET-1 | 0 |
| Intrinsic allow-list | No approximate instructions in canonical kernels | CI rejects the intrinsic | PLT-O-DET-5 | 0 |
| Resource usage | AGT's `Usage` fields per Evaluation; fuel never priced | Shared GPU: GPU seconds unattributed | PLT-O-RT-3 | 1 |

## GPU compute and linear algebra

GPUs and dense linear algebra give the most speed and hide the most machine dependence, so Crucible takes the speed and keeps the machine out of released results.

### GPU compute

WGSL, the WebGPU shading language, lets compilers "fuse operations if the transformed expression is at least as accurate" [W3C WGSL]. Implementations may also assume that overflow, infinities and NaNs are absent and flush subnormals. GPU bits therefore belong to one compiled pipeline, never to the canonical class.

**Decision D-PLT-16:** GPU kernels come from FLX's kernel IR through WGSL on wgpu, each registered in `gpu` beside its CPU path; GPU intervals serve only `Preview`, so `Interactive` uses take the filter role, and models that need `f64` never run on emulated `f64`.
*Why:* contract 7.5 makes the kernel IR the one source, CubeCL breaks between minor versions, and fusion and flushing void interval bounds and double-float arithmetic.
*Rejected:* CubeCL (reconsidered at the phase 4 gate); WGSL plus CUDA (two sources); CUDA first (no Apple GPUs or browsers); per-pipeline interval audits (unprovable).

Each GPU path declares one role. In *filter, CPU decides* (`Certified`), the GPU narrows candidates under a certified bound and the CPU makes every decision. In *class-exact* paths (`ClassExact`), which serve `Preview` and `Interactive` results, the bits are cached only under their `Gpu` class. In *witness* paths, the GPU solves and a check rests on the pinned Field, with its residual and bound computed canonically.

Every role relies on four `gpu` mechanisms:

1. **Known-answer tests.** A pipeline reproduces its class's recorded outputs before its first result-affecting dispatch, and again after a driver or OS update. A pass is persisted in the local CAS under (`GpuClass`, pipeline hash) until the driver or OS build changes. Until a pipeline passes, its Ops run on the CPU path.
2. **Integer exactness.** Exact results use integers, such as FLX's 32-bit-limb reductions, with no float atomics and compaction by prefix sums.
3. **Non-finite detection on the CPU.** Read-back exponent bits are inspected as integers, because in-shader NaN checks may be compiled away.
4. **Math functions.** Fixed-sequence approximations with documented ulp bounds, never vendor built-ins.

Known-answer tests run lazily because wgpu's pipeline cache works only on Vulkan [wgpu Features]. On DX12 and Metal, eager tests at start-up would compete with the cold-start row, which excludes compute pipelines.

WGSL serves implicit preview from phase 1. Interactive elasticity joins in phase 1 only if the phase 0 measurement of `CpuIsa` kernels misses contract 13.3's simulation row (contract 7.5). Because wgpu exposes `SHADER_F64` only on Vulkan, `f64` GPU paths are Vulkan server paths from phase 3. Without a usable adapter, or in safe mode, Kiln records `ran_on: Cpu` with the reason.

**Decision D-PLT-32:** An engine GPU dispatch lasts at most 4 ms while a window renders interactively, 16 ms while views idle and 100 ms headless; display-only GPU work runs on the UI process's device from coefficient buffers in the shared rings, and the engine creates its device lazily.
*Why:* engine and renderer share one GPU, and wgpu offers external memory only on Vulkan, so shared GPU buffers would cross host memory twice elsewhere.
*Rejected:* separate KLN, FLX and PLT limits; engine-side display evaluation.

A split dispatch covers more fixed tiles, never a different reduction topology. GPU seconds stay unattributed when the renderer shares the device.

### Canonical linear algebra

faer's dense kernels come from `gemm`, which sizes reduction blocks from L1 cache geometry read at run time and uses FMA; version 0.24.4 documents "cpu feature detection at runtime" [faer 0.24.4]. Two machines with different caches would therefore sum in different orders.

**Decision D-PLT-34:** `linalg`, owned by PLT with FLX, is the only linear algebra in `Portable` code; its dense kernels (GEMM, LU, Cholesky, QR, SVD) use fixed blocks, the canonical order, no FMA and index-ordered pivot ties, FLX owns its sparse factorizations, a bit-changing fix ships as a new frozen version (`linalg-v4`) that only new operation versions depend on (contract 4), and unmodified faer runs only in `CpuIsa` classes with cache detection pinned.
*Why:* cache-derived blocks make sums machine-dependent even within one instruction set, and MEC's constraint solver and COV's calibration fits need `Portable` results.
*Rejected:* unmodified faer in the canonical class; a permanent fork of faer and `gemm` (built around FMA); depending on upstream acceptance of a deterministic mode.

The dense target is within 2.5 times faer's `CpuIsa` time for n ≥ 1,000; sparse targets are FLX's.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| GPU paths with CPU paths | Three roles; `RanOn` reported; intervals `Preview`-only; no emulated `f64` | No adapter or safe mode: CPU path, reason shown | PLT-O-GPU-3 | 1 |
| GPU path selection | WebGPU, else WebGL2 and CPU compute; Vulkan, DX12 or Metal natively | "WebGPU unavailable", same features and canonical hash | PLT-O-WEB-6 | 1 |
| Known-answer tests | Lazy, before the first result-affecting dispatch; passes persisted per (`GpuClass`, pipeline hash) | CPU path until pass; failure proposes a workaround | PLT-O-GPU-1 | 1 |
| Exact GPU primitives | Integer-limb reductions, prefix-sum compaction, no float atomics | Non-identity fails the oracle | PLT-O-GPU-3 | 1 |
| Non-finite detection | Integer inspection after readback | Typed numerical `Failure` naming the kernel | PLT-O-GPU-3 | 1 |
| GPU dispatch rule | 4, 16 and 100 ms; display work on the UI device | Overlong dispatch split; repeated resets disable GPU compute | PLT-O-GPU-4 | 1 |
| `f64` GPU server paths | Vulkan `SHADER_F64`, certified on the CPU | Missing feature: CPU path | PLT-O-GPU-1 | 3 |
| Canonical dense linear algebra | Fixed blocking, no FMA, index-ordered pivot ties; frozen versions | Divergence fails the suite | PLT-O-LA-1 | 0 |
| Canonical sparse factorization | FLX's supernodal elimination and block-triangular LU, thread-count independent | Divergence fails the suite. Requires: FLX Canonical direct solvers | PLT-O-LA-1 | 1 (sequential supernodal), 2 (parallel; block-triangular LU) |
| faer in `CpuIsa` | Pinned cache detection; never in a `Portable` dependency closure | cargo-deny rejects the dependency | PLT-O-DET-5 | 1 |
| Linear algebra speed | Dense within 2.5 times faer `CpuIsa` | Regression filed nightly | PLT-O-LA-2 | 1 |

## Wasm component runtime

Wasm components let anyone extend Crucible with heavy algorithms, so each must give the same bits on every engine and reach nothing it was not given.

WASI 0.3.0 shipped on 11 June 2026 [WASI releases]. Wasmtime, the native runtime, treats "each release that is a multiple of 12" as an LTS release "supported for 24 months" [Wasmtime release process].

**Decision D-PLT-21:** Crucible embeds Wasmtime pinned to LTS releases (48, then 60), applies its security releases within 7 days on every supported line, moves between LTS releases only after the suite passes, and qualifies each target by its own criteria rather than upstream tier labels.
*Why:* the 24-month window matches Crucible's LTS channel, and upstream labels are outside Crucible's control.
*Rejected:* monthly releases (each recompiles every cached Wasm component); Wasmer (its runtime documentation names WASIX, not the Component Model).

### The determinizer

Wasm engines differ in exactly the places a bit-exact platform cares about: NaN payloads, fuel accounting, stack depth and whether memory growth succeeds. The determinizer, `determinize@N` in `wasm-host`, rewrites a component's bytecode so those places behave the same on every engine.

| Step | Problem it removes |
| --- | --- |
| Validation; rejection of relaxed SIMD, shared memories, atomics and forbidden imports | Results that differ between calls or threads |
| Fuel metering per basic block; with shared memory the check also reads a cancellation word | Engines meter differently; cancellation must land at the same points everywhere |
| A logical stack-depth limit below the smallest real stack of any engine | Engine-dependent stack overflow |
| NaN canonicalization only where bits become observable: float stores, `reinterpret`, the sign operand of `copysign`, host-call values, and v128 float results reaching bitwise, integer-lane, shuffle, store or extract-to-integer instructions | Nondeterministic NaN payloads, which arithmetic, comparisons and conversions never expose |
| Growth guards: a host-caused `memory.grow` or `table.grow` failure below the declared maximum becomes a `ResourceExhausted` Abort | `memory.grow` may non-deterministically succeed or fail [Wasm nondeterminism] |

Ingot code-generator output is verified, not rewritten. It must show no forbidden imports, a fuel decrement dominating every back-edge and function entry, a non-finite check before every observable float use, and a depth counter in every prologue.

Hosts execute only determinized binaries, and the binary's hash enters the `NodeKey`. A determinized binary that lost its instrumentation would silently drop fuel and cancellation everywhere. Every host therefore re-runs the pinned determinizer on the published input binary at install, and refuses a component whose output hash differs from the registry's index entry. The determinizer is deterministic, so the check costs one pass.

**Decision D-PLT-22:** The determinizer enforces fuel, cancellation, stack limits, NaN canonicalization and growth guards in bytecode, identically on every engine; Wasmtime's epochs are never used, fuel is a determinism and termination limit only, and AGT's `Usage` prices core-seconds, GPU-seconds and memory, never fuel.
*Why:* browsers can neither meter fuel nor canonicalize NaNs, Wasmtime's fuel costs change between releases, and fuel counts instructions, not cost.
*Rejected:* engine-side switches (native only); epochs (nondeterministic); canonicalizing every NaN-producing instruction; fuel-priced usage.

PLT publishes the one overhead table ECO cites (contract 7.4); all figures are targets. Determinizer rows compare with undeterminized binaries in Wasmtime, and isolation rows run on the reference laptop.

| Row | Target | Oracle |
| --- | --- | --- |
| Scalar-float Wasm components | At most 10% | PLT-O-WASM-2 |
| SIMD-float Wasm components | At most 25% | PLT-O-WASM-2 |
| Fuel and stack metering | At most 10% | PLT-O-WASM-2 |
| `crucible:ops` round trip from a native sandbox worker | At most 20 µs, plus 0.2 ms per MiB of arguments | PLT-O-WASM-7 |
| `crucible:ops` round trip across browser agent clusters | At most 250 µs, plus 1 ms per MiB | PLT-O-WASM-7 |
| std's Wasm components in the third-party configuration | Within 15% of in-process time, every release | PLT-O-WASM-7 |

Determinized components target 1.6 times native Rust in Wasmtime and 2.5 times in browsers for scalar and memory-bound code. Compute-bound SIMD kernels target 2.5 times AVX2 code, since Wasm's 128-bit SIMD is half as wide; FLX sets the ratios for user forms.

### Executors

| Target | Executor | Notes |
| --- | --- | --- |
| Native Tier 1 | Wasmtime LTS, Cranelift at `OptLevel::Speed` | Precompiled at install, keyed by binary, Wasmtime version, `Config`, target and CPU features; only local or Crucible-signed artifacts load |
| Browsers and iPadOS | One first-party runtime in the browser's own Wasm engine | `apps/platform-web`'s implementation of `WasmComponentEngine`; iPadOS through the web build |
| Android | Wasmtime with Cranelift | No Android API imports |
| No Cranelift code generation, or unqualified Windows ARM64 | Pulley, Wasmtime's portable interpreter | About ten times slower [Wasmtime Pulley] |

Until the Ingot code generator ships, the reference interpreter is the only Ingot executor. Wasmtime runs with relaxed SIMD, threads and memory64 off, and its limiter reserves budget as memory grows. `wasm-host` keeps the determinizer and the Wasmtime implementation behind `cfg(not(target_arch = "wasm32"))`; the browser implementation is injected at start-up like `Storage`.

**Decision D-PLT-36:** Browsers run every Wasm component through one first-party runtime, which instantiates determinized core modules from ECO's description with no JavaScript per component and implements the Component Model's stackless async ABI, "selected by providing a `callback` function", so a `crucible:ops` call returns to the event loop and resumes when the answer arrives.
*Why:* per-component glue code would run beside the engine worker's storage and credentials, and a synchronous import cannot wait on its own blocked event loop [Component Model concurrency].
*Rejected:* jco glue; transpiling in the engine worker; JS Promise Integration (needless stack switching).

### Isolation of third-party Wasm components

The engine process holds every open repository, token and device key. Wasmtime's 2026 advisories include isolation bugs, such as data leakage between pooling-allocator instances [Wasmtime GHSA-6wgr]. So only first-party code shares the engine's address space.

**Decision D-PLT-31:** Only first-party Wasm components (std, `crucible::` packages and the first-party translators, hermetically built) run in the engine process; on desktops each third-party component runs in an OS-sandboxed worker (AppContainer, App Sandbox, or seccomp with Landlock) with no repository, token, key or network, servers run such workers per tenant and label, trusted builders use microVMs (contract 7.8), and workers read bulk data through read-only CAS maps, so a call costs one round trip plus the copy of its arguments.
*Why:* an escape from an in-process component would reach everything the engine holds, and an OS-process sandbox is no trust boundary for attestation.
*Rejected:* in-process execution for verified publishers; process sandboxes on trusted builders.

**Decision D-PLT-42:** Browsers evaluate third-party evaluation-world components remotely until the asynchronous bridge passes PLT-O-WASM-1, PLT-O-WASM-6 and PLT-O-WASM-7 in that browser engine; the local sandbox, from phase 2, is an `<iframe sandbox="allow-scripts">` from a sandbox site on another registrable domain, whose fixed, content-hashed document starts a dedicated worker that runs the component, with `Content-Security-Policy: default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; webrtc 'block'` plus the COEP and CORP headers, and a `MessagePort` pair that carries transferred `ArrayBuffer`s to the engine worker.
*Why:* an opaque origin holds no OPFS, cookies or keys but can still send data, since CORS limits only reading responses; fetch directives do not govern WebRTC, so `webrtc 'block'` stops ICE candidates [W3C CSP3], and workers expose no `RTCPeerConnection` in current engines [unverified], which the oracle checks per engine.
*Rejected:* a worker without an iframe (workers have no `sandbox` attribute); memory shared with the engine (another agent cluster); a phase 1 sandbox.

Until PLT-O-WASM-6 passes in a browser engine, including its WebRTC, DNS-prefetch and preconnect cases, that engine evaluates third-party components remotely.

**Decision D-PLT-43:** Every process running untrusted code starts with no network: Wasm workers, translator hosts, External Op hosts, tool processes and stdio MCP (Model Context Protocol) servers; Windows uses AppContainers without network capabilities, macOS the App Sandbox without network entitlements, Linux empty network namespaces and servers microVMs without a network device, and endpoints that a manifest names and an administrator grants (contract 7.8) go through a host relay that connects only to the addresses the grant pins.
*Why:* untrusted native code with labelled inputs and a socket would bypass every audited exit, and Landlock filters by port, not by address [Landlock].
*Rejected:* egress rules by DNS name; per-OS firewall rules; no egress at all (licence servers need it).

A host with any grant receives only inputs labelled at most `internal` with empty `controls`, unless a two-person grant names it (contract 5.4).

A desktop may also run an External Op locally, such as ngspice with a vendor's SPICE model, so a laptop simulates offline. It runs the tool's native build for that OS, pinned by digest in its manifest, in the same sandbox as any tool process, with egress denied. Its results take the platform class `Unverified` and at most `Interactive` fidelity; they are never written to the shared cache and never decide a gate (contract 7.8).

### Worlds, calls and failures

ECO defines the worlds ([ECO, Determinism and limits](11-interop-ecosystem.md#determinism-and-limits)) and PLT enforces them: an import a world does not grant fails at install with `ForbiddenImport { import, fix }`. A batched call carries many operation calls in one round trip and returns results in call order.

Limits end a call in one of two ways, from KLN's one catalog in `base-op`. A limit the call itself declared is part of its inputs, so hitting it is a deterministic `Failure`; a limit the environment imposed is an Abort.

| Event | Outcome | Cached |
| --- | --- | --- |
| Trap in Wasm component code | `Failure`: `Trap { code, function, fix }` | Yes |
| The call's own fuel limit | `Failure`: `kiln/fuel_exhausted { used, limit }` | Yes |
| Logical stack limit | `Failure`: `kiln/stack_exhausted { limit }` | Yes |
| `memory.grow` beyond the declared maximum | `Failure`: `kiln/memory_limit { limit }` (contract 7.2) | Yes |
| Host memory unavailable below the maximum | Abort: `ResourceExhausted` | Never |
| Evaluation fuel governor or work budget exhausted | Abort: `BudgetExhausted` | Never |
| An organization ceiling below a source limit, at admission | Abort: `FuelCeilingExceeded` | Never |
| Cancellation; sandbox worker lost | Abort | Never |

Data beyond 4 GiB moves through chunked buffers, and data parallelism through `crucible:host/parallel` (Reference).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Determinizer | Validation, fuel, stack limit, observable-NaN canonicalization, growth guards | `InvalidComponent { reason }` | PLT-O-WASM-1 | 0 |
| Install-time determinizer check | Every host re-runs the pinned determinizer on the published input binary | Output hash differs from the index: component refused | PLT-O-WASM-1 | 1 |
| Observable-NaN canonicalization | Only at the listed observation points | Divergence fails the oracle | PLT-O-WASM-4 | 0 |
| Verification of Ingot modules | Four structural checks | Error naming the function | PLT-O-WASM-5 | 2 |
| Overhead table | Determinizer and isolation rows | Regression filed nightly | PLT-O-WASM-2 | 0 |
| Isolation overhead | 20 µs and 250 µs round trips; batched calls; std within 15% | std over 15% blocks the release | PLT-O-WASM-7 | 1 (native), 2 (browsers) |
| Wasmtime LTS embedding | Pinned LTS; security releases within 7 days | An unpatched advisory blocks the release | PLT-O-WASM-1 | 0 |
| Ahead-of-time compilation | At install; trusted artifacts only | Unknown artifact: recompiled locally | PLT-O-WASM-1 | 0 |
| Browser Wasm component runtime | One first-party runtime; callback async ABI | Missing description: fetched from the toolchain or team server | PLT-O-WASM-1 | 1 |
| Third-party isolation | OS sandboxes natively; microVMs on trusted builders; remote evaluation in browsers | Lost worker: Abort for its calls | PLT-O-WASM-6 | 1 |
| Browser sandbox | Sandbox site, dedicated worker, CSP with `webrtc 'block'`, `MessagePort` bridge | Engine failing the oracle: remote evaluation | PLT-O-WASM-6 | 2 |
| Default-deny egress | No network; granted endpoints at pinned addresses | Unlisted connection refused and logged | PLT-O-WASM-6 | 1 |
| Local External Ops on desktops | Native tool build in the tool sandbox; `Unverified`, at most `Interactive`, never cached | A gate reading it: `Undecided` with the reason | PLT-O-WASM-6 | 3 |
| stdio MCP server sandbox | Pipes, granted folders, no network unless granted | Access outside the grant denied and logged | PLT-O-WASM-6 | 1 |
| Cancellation | Fuel checks with shared memory, Op boundaries without | Abort, never cached | PLT-O-WASM-3 | 0 |
| Failure taxonomy | KLN's catalog; `Failure`s cached, Aborts never | A cached Abort fails the oracle | PLT-O-WASM-3 | 0 |
| Worlds | Imports checked at install; async `crucible:ops` with a batched form | `ForbiddenImport { import, fix }` | PLT-O-WASM-6 | 0 |
| WIT interfaces | `parallel` and `chunk-worker` in `crucible:host`; `process` in `crucible:tool` | Published WIT differs: release blocked | PLT-O-WASM-8 | 1 (`parallel`), 2 (`process`) |

## The platform layer

Every OS service sits behind one trait in `platform-api`, so core crates never learn which OS they run on.

**Decision D-PLT-1:** OS services sit behind traits in `core/platform-api`, implemented only by the `apps/platform-*` crates (`platform-windows`, `platform-apple`, `platform-linux`, `platform-web`, `platform-android`) and injected at start-up by the app shell.
*Why:* core crates stay OS-agnostic, tests inject in-memory implementations so storage and clocks never leak into evaluation, and one crate per OS family lets agents work on two operating systems without editing one crate.
*Rejected:* `cfg(target_os)` in core crates (untestable); one crate binding every OS; one crate per OS service.

The crate table and the layering rules are in Reference. Read the diagram below top down.

[[DIAGRAM diagrams/12-platform-crate-layering.jsx: crate layering · dependencies point down, only apps/platform-* bind the OS]]

Each row depends only on rows below it; the `apps/platform-*` crates at the side implement the bottom row's traits, and `cargo xtask check-layers` fails CI on any other edge.

**Decision D-PLT-4:** winit provides windows, the event loop and raw input on every target; Crucible pins one 0.31 beta commit on its own patch branch, re-pins at each beta, and carries patches for macOS `NSEvent` tablet events and X11 XInput2 pen axes, each with its upstream pull request as the exit.
*Why:* only winit covers desktop, web, iOS and Android, and its 0.31 betas add pen input on Wayland, Windows and the web and Apple Pencil on iOS but no macOS tablet events [winit releases].
*Rejected:* SDL3 (a C dependency); GPUI's platform layer (no web target); staying on 0.30.

### OS services

Every PLT error implements `Guidance` (`why`, `fix`), which maps into the `api` error shape. The services are `Storage`, `Journal`, `WindowHost`, `FileWatcher`, `Clipboard`, `Dialogs`, `Notifications`, `CredentialStore`, `SystemSignals`, `WallClock`, `Monotonic`, `Spawner`, `SharedRing`, `DeviceIo`, `CryptoProvider`, `AccessibilityHost` and `Authenticator` (signatures in Reference).

- `Monotonic` is a monotonic clock for watchdogs and safe-point cadences, never visible to evaluation; `WallClock` never reaches evaluation either. `Spawner` runs async tasks on the IO runtime. Both exist because `std::time::Instant::now()` "will simply panic" on `wasm32-unknown-unknown` [web-time].
- `DeviceIo` opens serial and USB ports outside evaluation for MFG's machine gateway and ELX's bench adapters.
- `CryptoProvider` supplies TLS, hashes and signatures. Natively it is aws-lc-rs, whose AWS-LC 3 module holds FIPS 140-3 certificate 5314 [NIST CMVP 5314]. KLN's FIPS mode routes through that module, and browsers use WebCrypto in `apps/platform-web`.

### Approvals and local credentials

Approvals are the one place a person's intent must not be forged by a process acting for them. PLT supplies the session that carries the ceremony; AGT and UIX own the ceremony and the page.

**Decision D-PLT-41:** Every client approves in a browser on the approval origin, which has its own WebAuthn relying-party id; the web app opens it as a top-level window, macOS and iPadOS through `ASWebAuthenticationSession`, and Windows and Linux in the default browser, and the session is bound to the request id, returns by a `crucible://` callback, and the app reads the outcome from `api`.
*Why:* an app "can't use passkeys to authenticate for services that you haven't configured as the app's associated domains" [Apple supporting passkeys], and a separate origin keeps script injected into the main app away from the ceremony.
*Rejected:* native WebAuthn per OS; an embedded webview the app can script; the main origin.

`Authenticator` opens that page for one request id and reports when the ceremony ends. It never handles a credential.

Two rules from contract 7.6 land here:

- **Local credentials.** `CredentialStore` holds the device credential, which authenticates as `agent:<org>/local/<device>` with `Declared` assurance, never as the person. A human-only method (contract 7.6's list, a local write above `public` included) first calls `Authenticator` for a WebAuthn assertion bound to the call's argument digest and valid for one call. An agent with a shell tool running the CLI therefore never merges or exports as the person.
- **Enrolment.** Enrolling an approval credential uses the same session and is itself approved on the approval origin under the signature table (contract 5.4). Platform passkeys on macOS, iPadOS and Android are backup-eligible, so those devices approve with a roaming security key.

### Paths, text, fonts and accessibility

`RepoPath` is UTF-8 in NFC, `/`-separated and relative, without `.` or `..`. Segments hold at most 255 bytes and no control characters, `< > : " | ? * \`, trailing dot or space, or Windows device name. Paths equal after case folding collide (`PathError::CaseCollision`). Other paths are opaque `HostPath`s that never enter the CAS.

**Decision D-PLT-5:** Repository paths are portable by construction: NFC, `/`-separated, case-fold unique and free of names any Tier 1 OS rejects.
*Why:* a name valid only on Linux, or two names differing only in case, splits a team across operating systems.
*Rejected:* OS-native paths; silent normalization at checkout (two names map to one file).

**Decision D-PLT-6:** Repository text is UTF-8 with LF line endings and no byte-order mark, and readers normalize CRLF, CR and a byte-order mark on input.
*Why:* content hashes must not depend on the OS that wrote the file.
*Rejected:* per-OS line endings converted at checkout (hashes depend on settings).

**Decision D-PLT-7:** Design text uses fonts from registry packages pinned in `ingot.lock`, shaped by the pure-Rust Parley stack; system fonts serve only the UI, and Ingot reaches shaping only through ANV's `anvil::text_outline`, whose missing font is ANV's `FontMissing`.
*Why:* system fonts differ by OS and version, so engraved text would change geometry between machines.
*Rejected:* DirectWrite and Core Text; system fonts in designs.

**Decision D-PLT-8:** A web accessibility adapter mirrors the AccessKit tree into a hidden ARIA DOM and routes focus and actions back; it is offered upstream, and UIX's toolkit risk spike exercises it first, with PLT's IME paths and Windows AccessKit hosting.
*Why:* AccessKit has no released web adapter [AccessKit], and identical features include accessibility.
*Rejected:* a separate HTML UI (drifts); waiting for upstream.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Layered crates | Only `apps/platform-*` bind OS APIs; contract 12's rows; portable core | The layering check fails the build | PLT-O-DET-5 | 0 |
| Windows and surfaces | `WindowHost` gives raw handles to the renderer | `PlatformError::Window { backend, reason, fix }` | PLT-O-OS-1 | 0 |
| Pointer, pen and touch | One `PointerEvent` stream with pressure and tilt; macOS and X11 pen patches | Missing axes are `None` | PLT-O-OS-1 | 1 (desktop), 3 (tablets) |
| Keyboard and IME | Physical key, logical key and text apart; preedit and commit | No IME: plain input, with a notice | PLT-O-OS-2 | 0 (Windows, Chrome), 1 |
| 6-DoF devices | `NavDeviceEvent` from HID on every desktop OS, WebHID in Chromium; spacenavd optional on Linux | Device absent: no events | PLT-O-OS-1 | 2 |
| Accessibility | AccessKit tree per window; web DOM mirror | `AccessibilityUnavailable` logged once | PLT-O-OS-3 | 0 (Windows), 1 (desktop, web), 3 (tablets) |
| Clipboard | Plain-text Ingot plus `application/x-crucible+cbor` | `ClipboardError::Unavailable { reason }` | PLT-O-OS-4 | 1 |
| Drag and drop | Incoming through winit; outgoing per OS | "Export…" offered with the reason | PLT-O-OS-4 | 1 (incoming), 2 (outgoing) |
| File dialogs | Async `open`, `save`, `pick_folder` | No portal on Linux: in-app browser | PLT-O-OS-4 | 1 |
| Notifications | `Notifications::post` under D-PLT-38 | Denied: notice in the activity panel | PLT-O-OS-4 | 1 |
| File watching | `Changed`, `Rescan`, `Health` events | Overflow: `Rescan`, "watching by polling" | PLT-O-OS-4 | 1 |
| File locking | Exclusive lock on `.crucible/lock` | `LockError::Held { holder_pid, since }` | PLT-O-OS-4 | 0 |
| Clocks and tasks | `Monotonic` and `Spawner` injected; no std clocks or threads in `core/` | Disallowed use fails the layering check | PLT-O-DET-5 | 0 |
| Credentials | `CredentialStore` per account; device credential as a local agent | `CredentialError::Unavailable` | PLT-O-OS-4 | 1 |
| WebAuthn | Approval, per-call assertion and enrolment in a browser session (D-PLT-41) | No session: the call is refused with the reason | PLT-O-OS-4 | 1 |
| Serial and USB | `DeviceIo` on native targets, WebUSB and Web Serial in Chromium, outside evaluation | `DeviceError::Unavailable { port, reason }` | PLT-O-OS-4 | 2 |
| FIPS-mode cryptography | `CryptoProvider` through a FIPS 140-3 module natively; WebCrypto in browsers | Non-approved algorithm refused | KLN-O-SIG-2 | 2 |
| System signals | Memory pressure, power, thermal state, scale, reachability | Unavailable signal: `Unknown` | PLT-O-OS-1 | 1 |
| Portable paths | `RepoPath::parse`; OS paths only in `apps/platform-*` | `PathError` with a portable name | PLT-O-OS-5 | 0 |
| Text normalization | UTF-8, LF, no byte-order mark | `TextError::InvalidUtf8 { offset }` | PLT-O-OS-6 | 0 |
| Design fonts | Registry fonts pinned by hash | `FontError::MissingGlyph { char, font }`, never a substitution | PLT-O-OS-6 | 1 |

## Targets

An engineer moves between Windows, macOS, Linux and a browser without losing a feature, because each target's versions, processors and back ends are fixed here under contract 9's tiers.

| Target | Phase 1 | OS and CPU | GPU back ends | Wasmtime tier |
| --- | --- | --- | --- | --- |
| Windows 11 x86-64 | General availability | Releases in Microsoft servicing; x86-64-v2 with dispatch to v3 and v4 | DX12, Vulkan | 1 |
| Windows 11 ARM64 | Preview | 24H2 and later; ARMv8 NEON | DX12 | 3; Crucible-qualified |
| macOS | General availability | Current and two prior on Apple silicon | Metal | 2 |
| Linux x86-64 | General availability | glibc 2.34 or later; Wayland and X11 | Vulkan; OpenGL ES 3 | 1 |
| Linux ARM64 desktop | Preview | As above, ARMv8 NEON | Vulkan | 2 |
| Chrome and Edge | General availability | Current and previous stable; wasm32 with SIMD128 and threads | WebGPU, WebGL2 | Browser engine |
| Safari | Preview | 26 and later | WebGPU, WebGL2 | Browser engine |
| Firefox | Preview | Current and ESR | WebGPU on Windows and macOS; WebGL2 on Linux | Browser engine |

Chrome ships WebGPU on Linux only for Intel Gen12+ and NVIDIA on Wayland, and behind a flag on Windows ARM64; Firefox ships it on Windows since 141 and on macOS from 145 [WebGPU implementation status]. Every row still has every feature, because WebGL2 and the CPU paths carry the same canonical results.

Wasmtime rates Windows ARM64 Tier 3, lacking "CI testing, full-time maintainer", and aarch64 macOS and Linux Tier 2, lacking "Continuous fuzzing" [Wasmtime stability tiers]. Crucible qualifies these targets itself. Every merge runs Wasmtime's test suite and PLT-O-WASM-1 to PLT-O-WASM-8 on them, with 24 hours of fuzzing a week. A target still unqualified at the phase 2 gate runs Wasm components through Pulley and declares the speed as capacity.

Preview targets meet contract 9 in three ways. Golden checks run in automation, Safari through safaridriver on a macOS host. Each target publishes an Accessibility Conformance Report with an external audit. Driver qualification means PLT-O-GPU-1 to PLT-O-GPU-5 and UIX's Snapshot oracle pass on every listed lab device.

**Decision D-PLT-3:** Linux binaries link against a glibc 2.34 sysroot with no newer symbols, and Wayland is a first-class target equal to X11.
*Why:* engineering desktops run long-lived distributions.
*Rejected:* static musl desktop builds (GPU drivers load through the system loader); per-distribution builds.

### Tablets and phones

Tier 2 covers viewing, review, presentation and light editing with the same core crates and UI. Heavy evaluation is remote by default, and phones approve only what contract 7.6 allows in a phone browser.

**Decision D-PLT-33:** iPadOS runs the web build in a thin WKWebView shell, where JavaScriptCore compiles Wasm (contract 7.4); the app runs only first-party Wasm components shipped in its binary and evaluates registry components remotely.
*Why:* the JIT entitlement exists only on macOS [Apple allow-jit], Pulley carries "a ~10x order-of-magnitude slowdown" [Wasmtime Pulley], and downloaded code would bring App Review guidelines 2.5.2 and 4.7 into play [Apple App Review].
*Rejected:* native engine threads beside a WKWebView worker (they cannot answer its imports); Pulley; local registry components.

The whole iPadOS plan rests on three WKWebView capabilities that no source confirms: `crossOriginIsolated` for pages served through the app's own URL scheme, OPFS synchronous access handles, and WebGPU inside WKWebView rather than Safari. A phase 1 `device-farm` case of PLT-O-TGT-1 measures them, plus the WebContent memory ceiling and the compile time of the engine module. The fallbacks are named now: the single-threaded build without isolation, WebGL2 without WebGPU, and remote evaluation above the measured ceiling.

Embedded WebKit apps get about 15% of disk, the figure the Tier 2 storage plan uses [MDN storage quotas].

Google Play's ban on downloaded code "does not apply to code that runs in a virtual machine or an interpreter" [Google Play device abuse]. Android runs Wasmtime with Cranelift, and no world imports Android APIs. Builds use NDK r28 for the 16 KB pages Google Play requires from 1 February 2027 [Android 16 KB pages].

### Tier 3 and servers

FreeBSD, OpenBSD, NetBSD, illumos and riscv64 Linux are community-supported, CLI and server first. Their results stay `Unverified` and local until they pass the determinism suite.

Servers are OCI images for x86-64 and ARM64 that compute in the canonical class. Optional GPUs serve `f64` Vulkan solves from phase 3, and CUDA or HIP is reconsidered at the phase 4 gate. Without a GPU, a server runs every golden product on the CPU path with `ran_on: Cpu` and the reason recorded.

PLT builds the images for contract 7.8's two pools. Untrusted-evaluation workers are single-use microVMs with no key and no network unless granted. Trusted builders evaluate merged Changes; they run first-party code per (tenant, confidentiality label) and anything else in single-use microVMs on single-tenant hosts. Labels with non-empty `controls` get dedicated VMs. PLT packages KLN's attestation service as `apps/attestation`, which signs only trusted-builder work from phase 2.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Tier 1 general availability | Windows 11 x86-64, macOS, Linux x86-64, Chrome and Edge pass every golden product | A divergence blocks beta promotion | PLT-O-DET-1 | 1 |
| Tier 1 preview | Windows 11 ARM64, Linux ARM64 desktop, Safari, Firefox: same build, suite and golden checks in automation | A missing installer, updater, report or driver qualification blocks general availability | PLT-O-DET-1 | 1 (preview), 2 (general) |
| Upstream Wasmtime coverage | Crucible's own qualification per merge, with weekly fuzzing | Unqualified at the phase 2 gate: Pulley | PLT-O-WASM-1 | 0 |
| iPadOS capability spike | Isolation under the app's URL scheme, sync access handles, WebGPU, memory ceiling, compile time | A missing capability selects its named fallback | PLT-O-TGT-1 | 1 |
| Tier 2 tablets and phones | Same `api` and UI; light local editing | Over budget: remote evaluation offered | PLT-O-TGT-1 | 3 |
| iPadOS Wasm executor | The web build in WKWebView; registry components remote | Memory limit: evaluation goes remote | PLT-O-TGT-1 | 3 |
| Android Wasm executor | Wasmtime with Cranelift; no Android API imports | A direct Android import fails to load | PLT-O-TGT-1 | 3 |
| Tier 3 targets | Community builds, `Unverified` until the suite passes | Results stay local | PLT-O-DET-1 | 5 |
| Server images | OCI images on x86-64 and ARM64 in the canonical class | Missing GPU: CPU path, `ran_on: Cpu` with the reason | PLT-O-TGT-3 | 1 |
| Untrusted-evaluation workers | Single-use microVMs, no key, no network unless granted | A write outside the namespace destroys the VM | PLT-O-TGT-2 | 1 |
| Trusted builders | Third-party code only in microVMs on single-tenant hosts | Shared host for a third-party closure: refused | PLT-O-TGT-2 | 1 |
| Attestation packaging | KLN's service as `apps/attestation`, with HSM-held keys | Unbound request refused and logged | PLT-O-TGT-2 | 2 |

## The browser target

A reviewer who opens a link runs the same core crates, compiled to `wasm32-unknown-unknown` in the canonical class, so a browser shares cached results with desktops bit for bit.

| Context | Runs | May block |
| --- | --- | --- |
| Main thread | Input, accessibility DOM mirror, frame presentation | Never |
| Engine worker | `api` server side, Kiln, CAS, journal, OPFS write handles | With `Atomics.wait`, only while no IO is pending |
| Compute workers, max(1, min(`hardwareConcurrency` − 1, 16)) | The engine's pool through wasm-bindgen-rayon | Yes |
| Heavy worker | One disposable evaluation with its own memory and pool | Yes |
| Op worker, single-threaded build only, from phase 2 | One disposable Op estimated above 100 ms | Yes |
| Wasm component sandbox, from phase 2 | Third-party components on a separate site (D-PLT-42) | Yes |
| Service worker | Offline cache, verified updates, port brokering | Never |

The threaded build passes `api` messages and triangle buffers through `SharedArrayBuffer` rings, and the single-threaded build through transferred buffers.

wasm-bindgen-rayon asks callers to initialize its pool "right after instantiating your module on the main thread" [wasm-bindgen-rayon]. Crucible starts the pool from the engine worker instead, and a nested pool from the heavy worker. A phase 0 `browser-ci` case of PLT-O-RT-1 proves both start-ups and measures the 1 ms and 2 ms start targets there; if worker-side start-up fails, PLT carries a patch in the crate's fork plan.

**Decision D-PLT-29:** One engine runs per browser origin: the first tab's engine worker takes a Web Lock and owns every OPFS write handle except packs a heavy worker is still writing, a heavy worker writes each pack under a name only it holds and sends the index for adoption, other tabs reach the engine through a `MessagePort`, and the next tab takes over and replays the journal when the owner closes.
*Why:* a synchronous access handle "takes an exclusive lock on the file" [MDN createSyncAccessHandle], and SQLite's `opfs-sahpool` fails when initialized twice in one origin [SQLite Wasm persistence].
*Rejected:* one engine per tab; the `opfs` VFS (needs isolation); heavy-worker writes through the engine (double copies).

### Isolation and sign-in

WebAssembly threads need `SharedArrayBuffer`, which needs `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` [web.dev COOP and COEP]. Crucible serves every asset from its own origin with CORP headers, and team servers report a missing header.

**Decision D-PLT-9:** In phase 1 the web product runs only the threaded engine (atomics, bulk memory, SIMD128) and refuses to start without cross-origin isolation, saying why; from phase 2 a single-threaded build from the same source serves embedded viewers, and the iPadOS shell if it lacks isolation, with cancellation at Op boundaries through a disposable Op worker per Op estimated above 100 ms (contract 7.4).
*Why:* Crucible serves its own app isolated and every Tier 1 browser supports isolation, so no phase 1 gate needs a second product build, while the determinism suite keeps the single-threaded wasm32 build tested from phase 0.
*Rejected:* shipping both builds in phase 1 (a second cancellation path no gate needs); refusing to run without isolation forever (breaks embeds); host yields at fuel checks (they run on the blocked thread).

From phase 2, embedded viewers use `Document-Isolation-Policy`, "shipping in Chrome 137 for desktop only" [Chrome Document-Isolation-Policy], and the single-threaded build elsewhere. That build reaches idle within 150 ms of a cancel at p99 (target), and contract 13.3's drag row is measured on the threaded build.

**Decision D-PLT-10:** The threaded web engine builds with a nightly toolchain pinned per release and `-Zbuild-std`, and every other artifact uses pinned stable Rust.
*Why:* wasm-bindgen-rayon's thread support "is still only available in nightly" [wasm-bindgen-rayon], and Rust's float semantics keep results independent of the compiler, which the suite verifies.
*Rejected:* a hand-written worker runtime; dropping browser threads (a 4 to 16 times loss).

`same-origin` severs references to cross-origin popups [MDN COOP]. Sign-in therefore redirects to a non-isolated page that completes the authorization-code exchange with PKCE, and keeps the token as a non-extractable WebCrypto key.

The app origin's content policy is `default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self' <team server>; frame-src <sandbox site>; object-src 'none'`. Without `'wasm-unsafe-eval'` under a policy, "WebAssembly is blocked from loading and executing" [MDN script-src], and the engine worker compiles user forms and translator modules at run time from phase 1.

The web build requires SIMD128, threads and bulk memory, which every Tier 1 browser ships, Safari since 16.4 [Wasm feature support]. Relaxed SIMD, memory64, exception handling and JS Promise Integration are not used.

### Memory

**Decision D-PLT-11:** The browser engine stays wasm32 with 4 GiB of address space, and large models use out-of-core chunks in OPFS, a heavy worker and remote evaluation.
*Why:* memory64 caps at 16 GiB, is in Safari only in Technology Preview, and costs 10% to over 100% in SpiderMonkey's measurements [SpiderMonkey memory64].
*Rejected:* a memory64 build for Chrome and Firefox only (two behaviors for one Tier 1 target), revisited when Safari ships memory64 and the penalty on the PLT suite falls below 10%.

**Decision D-PLT-30:** The engine worker keeps a fixed linear-memory cap; evaluations estimated above 512 MiB run in a disposable heavy worker and larger ones go remote; the heavy worker starts its own pool of min(`hardwareConcurrency` − 2, 8) nested workers while the engine pauses its pool, with the start-up counted by Kiln's cost model; and above 768 MiB, after 30 s idle, the engine worker hands the Web Lock to a fresh one, which replays the journal.
*Why:* Wasm memory can only grow, never shrink [Wasm memory control], and compute workers share the engine module's memory, not the heavy worker's.
*Rejected:* one growing engine worker; single-threaded heavy evaluations; memory64.

Workers "may spawn more workers" from the same origin [MDN Web Workers], which the nested pool relies on. This is contract 9's browser memory table. Each starting value holds until the phase 0 gate sets it per browser engine, as the largest value 25% below the kill threshold measured on the 8 GiB low-band machine.

| Context | Cap or target | Rule |
| --- | --- | --- |
| UI module | 512 MiB linear memory (starting value) | UIX owns the contents |
| Engine worker | 1.5 GiB (starting value); recycles above 768 MiB after 30 s idle | Kiln evicts to OPFS; larger reservations go to the heavy worker |
| Heavy worker | min(4 GiB, kill threshold − UI cap − engine cap − 512 MiB) | One at a time, terminated after each evaluation |
| Idle, UI plus engine | 300 MiB after an engine recycle | Contract 13.3 memory row |
| GP1 open | 1.5 GiB of linear memory in total | Same row |
| Suspended feature calls | 500 at once in 256 MiB of the engine cap (ING) | Reserved as used |

### The engine module

Rust links no Rust code dynamically on `wasm32-unknown-unknown`, so every operation, solver and translator host lands in one engine module. Each phase adds physics to it, while contract 13.3 caps the first visit at 25 MiB of brotli-compressed primary module.

**Decision D-PLT-48:** The engine module is split by profile-guided `wasm-split` into a primary module (Kiln, CAS, `repo`, the Ingot interpreter and the operations that golden-product sessions touch at start) and lazily fetched secondary modules that share its memory; the profile comes from instrumented golden-product sessions, and `cargo xtask wasm-size` reports each crate's compressed contribution on every merge.
*Why:* Binaryen's `wasm-split` can "split a module in two or instrument a module to inform future splitting" [Binaryen wasm-split], which keeps the first visit within its budget as phases add operations.
*Rejected:* one ever-growing module (the first-visit row fails late); per-family Wasm components from the start (an asynchronous call boundary inside the engine).

Whether the threaded build splits with shared memory is a phase 0 spike [unverified]. If it cannot, operation families above a size threshold become first-party Wasm components loaded on first use. The primary module's budget is a target per phase: 16 MiB brotli in phase 1, 20 MiB in phase 2, and 25 MiB from phase 3, gated by PLT-O-PERF-1.

### Storage, hashing and updates

The CAS, journal and package cache live in the origin private file system (OPFS), whose synchronous handles work only in dedicated workers [MDN OPFS]. Quotas are about 60% of disk in Chrome, Edge and Safari. Firefox allows the smaller of 10% or 10 GiB, or up to 50% with persistence [MDN storage quotas]. Safari deletes script-written data after seven days without interaction.

The engine requests persistence at first use. The browser CAS is a cache of the team server, or of a folder picked through `showDirectoryPicker`, which is not Baseline [MDN showDirectoryPicker]. Unsynced edits show "not yet synced".

The browser CAS hashes chunks of at most 1 MiB in parallel with `crypto.subtle.digest`, which "does not support streaming input" [MDN SubtleCrypto digest]. A Wasm SHA-256 serves small objects. The target is 1 GiB in 1 s across 8 workers, and a miss relaxes the browser row to the measured value rather than adding a second hash.

A service worker caches the shell, engines, fonts and std packages under content-hashed URLs and activates a new version on the next load. Each release's manifest is verified against TUF targets, and from phase 2 logged in a transparency log.

Browsers ran 45% to 55% slower than native on SPEC CPU [Jangda 2019]. The targets are the suite within 2.0 times native single-threaded, 2.5 times multi-threaded and 3 times for SIMD-heavy kernels.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Threaded web build | Starts only when `crossOriginIsolated`; identical hashes | "Threads unavailable: the site is not cross-origin isolated" | PLT-O-WEB-1 | 0 |
| Single-threaded web product build | Embedded viewers and the iPadOS fallback; Op workers | Over 150 ms to idle at p99 fails | PLT-O-WASM-3 | 2 |
| App origin policy | Served CSP with `'wasm-unsafe-eval'`; user-form modules compile under it | Missing header: the team server health check fails | PLT-O-WEB-1 | 1 |
| Sign-in under isolation | Redirect-based authorization code with PKCE | Popups never offered | PLT-O-WEB-1 | 1 |
| One engine per origin | Web Lock owner holds the write handles; packs adopted | Owner closes: next tab replays | PLT-O-WEB-2 | 1 |
| Browser pools | One pool with three lane queues, started from the engine worker; nested pool in the heavy worker | Start-up failure: fork-plan patch, or single-threaded heavy work | PLT-O-RT-1 | 0 |
| Browser memory table | Cap and recycle; heavy worker with its own pool | `ResourceExhausted` Abort with a remote offer | PLT-O-WEB-3 | 1 |
| Split engine module | Profile-guided primary module; secondary modules on demand; per-crate size report | Primary module over its phase budget blocks beta | PLT-O-PERF-1 | 1 |
| OPFS storage | Persistence requested; CAS as cache; sync indicator | Eviction: refetch; local-only edits warned | PLT-O-WEB-3 | 1 |
| Chunk hashing | Parallel `crypto.subtle.digest`; native-identical `ObjectId`s | Digest failure: Wasm SHA-256 | PLT-O-WEB-5 | 1 |
| Verified updates | TUF-verified manifest; transparency log from phase 2 | The running version stays | PLT-O-WEB-4 | 1 |
| Startup and payload | Contract 13.3's browser rows | A missed row blocks beta promotion | PLT-O-PERF-1 | 1 |
| Browser speed | Suite ratios 2.0 and 2.5; SIMD-heavy 3 | Regression filed nightly | PLT-O-PERF-3 | 1 |

## Deployment

Each deployment mode, from one laptop to an air-gapped site, runs the same features, so moving between modes changes capacity and location, never behavior.

**Decision D-PLT-51:** Deployment modes differ only in the services they run and where data lives, never in features or canonical results, and every mode installs from the same signed artifacts.
*Why:* an engineer who moves from a desktop to a team server or a regulated cloud must find the same product and the same bits, and one artifact set is one thing to sign, test and audit.
*Rejected:* a lighter desktop edition; mode-specific builds.

| Mode | Services | Metadata store | Phase |
| --- | --- | --- | --- |
| Desktop | Kiln, local CAS and repository, local relay | SQLite | 1 |
| Browser | The engine in a worker, one engine per origin | SQLite on OPFS (`opfs-sahpool`) | 1 |
| Team server | Host or VM install: repository server, CI coordinator, untrusted back end, trusted builder; `apps/relay` and `apps/rig-runner`'s gateway from phase 2 | SQLite, or PostgreSQL | 1 |
| Cloud | Regional cells: gateways, relays, repository servers, worker fleets, per-tenant logs | FoundationDB | 2 |
| Regulated cloud | Contract 7.7's regulated mode; classified information is out of scope in every mode | FoundationDB | 3 |
| On-premises and air-gapped | The cloud stack on Kubernetes, or a team server; air-gapped adds no external network and an offline licence | PostgreSQL or FoundationDB | 2, 3 |

A desktop is a full peer under KLN's local-first rule: without a team server it designs, simulates, evaluates, presents and exports locally, while Proposals, releases and every Act need one (contract 13.2). Tenant onboarding applies ECO's restricted-jurisdiction rule. KLN owns what runs inside these modes: offline work, mirrors, federation, air-gapped bundles, the restore verifier and the scale targets ([KLN, Live sessions and offline work](05-kiln-repo-plm.md#live-sessions-and-offline-work)).

### The team server

**Decision D-PLT-44:** The single-node team server installs on a Linux host or VM, not in one container, and runs its services as OCI containers; Proposal CI uses Firecracker where `/dev/kvm` exists and gVisor otherwise, the health check refuses Proposal CI when neither works, and the trusted builder runs as its own OS user, outside the sandbox service, as the only caller the signing service accepts (contract 7.8).
*Why:* "Firecracker requires read/write access to `/dev/kvm`" [Firecracker getting started], while gVisor's systrap platform suits "running inside a VM" [gVisor platforms].
*Rejected:* one container (no KVM, and one boundary for both pools); requiring bare metal.

The installer reports the active sandbox back end. The trusted builder has no access to the sandbox's sockets or images. In single-host mode External Ops are not offered, and every release records "single host" (contract 7.8).

A team server either hosts a repository's Git home itself, over smart HTTP and SSH with an LFS endpoint for large Assets, or works beside an existing Git host as a required status check on protected branches (contract 7.1).

On-premises sites run the cloud stack from one Helm chart on Kubernetes, or a team server. Air-gapped sites add no external network, an offline licence and the offline bundles of the next section.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Deployment modes | Desktop, browser, team server, cloud, regulated cloud, on-premises and air-gapped from one signed artifact set, with identical features | A mode that loses a feature or a canonical hash blocks the release | PLT-O-DEPLOY-1 | 1 (desktop, browser, team server), 2 (cloud, on-premises), 3 (regulated, air-gapped) |
| Team server install | Host or VM; Firecracker or gVisor; separate builder user | No back end: Proposal CI refused | PLT-O-TGT-2 | 1 |
| On-premises package | The cloud stack on Kubernetes | Schema mismatch: upgrade refused with the reason | PLT-O-DEPLOY-2 | 2 |
| Cloud and regulated cloud cells | Regional cells; regulated controls | A failed cell fails over with the reason logged | PLT-O-DEPLOY-3 | 2 (cloud), 3 (regulated) |

## Packaging, distribution and updates

Crucible installs the way each platform's administrators expect and updates without trusting any single server or key. Here "app package" means an OS installation format such as MSIX or deb, unrelated to registry packages.

| Target | Format | Signing | Phase |
| --- | --- | --- | --- |
| Windows | MSIX per architecture through the PackageManager API; Intune, Configuration Manager and the Enterprise Modern App Management CSP | Authenticode, HSM-held key | 1; an MSI wrapper for MSI-only tools 2 |
| macOS | Notarized DMG; `.pkg` for MDM | Developer ID, hardened runtime, stapled ticket | 1; `.pkg` 2 |
| Linux | deb and rpm in apt and dnf repositories; Flatpak and AppImage | Signed metadata expiring within 7 days | 1; Flatpak and AppImage 2 |
| Browser | Content-hashed assets and a service worker | Manifest in TUF; transparency log from phase 2 | 1 |
| Machine gateway (`apps/machine-gateway`, MFG) | MSIX on Windows 11 x86-64; deb and rpm on Linux x86-64 and ARM64 | As its OS; device key in a TPM 2.0 | 2 |
| iPadOS, Android | App Store, Google Play, managed APKs | Platform signing | 3 |
| Servers and `cli` | OCI images and a Helm chart; `cli` in every desktop package and as signed archives | Image signatures and SLSA provenance | 1 |

The gateway connects outbound only, and readings from one without a TPM carry `data_untrusted`. The macOS bundle declares `com.apple.security.cs.allow-jit` for memory created "using the `MAP_JIT` flag", which Wasmtime needs [Apple allow-jit].

**Decision D-PLT-23:** Windows ships as MSIX.
*Why:* MSIX gives clean uninstall, package identity for notifications and background tasks, 64 KB block-level differential updates and Intune support [Microsoft MSIX].
*Rejected:* MSI (no package identity or block updates); a custom installer.

**Decision D-PLT-24:** Linux ships deb and rpm repositories in phase 1 and Flatpak and AppImage in phase 2, from one binary per architecture.
*Why:* deb and rpm serve managed fleets and suffice for the first gate, while Flatpak and AppImage serve sandboxed and unprivileged installs.
*Rejected:* Snap only; per-distribution builds; all four in phase 1.

### Signed updates

**Decision D-PLT-25:** Every self-updating channel verifies updates with The Update Framework (TUF, specification 1.0.37) with offline root and targets keys, OS mechanisms carry the bytes where they exist, phase 1 installs full signed packages, and deltas (MSIX block maps, Zucchini patches for PE and ELF, generic patches for Mach-O) arrive in phase 2.
*Why:* TUF defeats freeze, rollback, mix-and-match, fast-forward and endless-data attacks and survives key compromise [TUF overview].
*Rejected:* a signed manifest alone; Velopack (no documented rollback defense); Sparkle (macOS only).

| TUF role | Signs | Keys and threshold | Expiry |
| --- | --- | --- | --- |
| Root | Every other role's keys | 3 of 5 offline hardware tokens in separate locations, held by the founder and outside custodians | 1 year |
| Targets | Hashes and lengths per artifact, delegated per channel | 2 of 3 HSM keys | 3 months |
| Snapshot | Versions of all targets metadata | 1 online key | 7 days |
| Timestamp | The snapshot's hash | 1 online key | 1 day |

The updater checks timestamp metadata at start-up and every 4 hours, rejects expired metadata and lower versions, and installs at the next start. A new version self-tests within 60 s and rolls back on failure or after two crashes in 10 minutes. Stable releases roll out to 1%, 10%, 50% and 100% over at least 4 days and halt if crash rates rise 20% (target). Update servers refuse the jurisdictions of ECO's restricted-jurisdiction dataset.

**Decision D-PLT-37:** Every signature PLT produces or verifies (artifacts, TUF metadata, web manifests, provenance) is a detached record carrying an algorithm id; from phase 2, TUF root and targets metadata and provenance are dual-signed with a classical signature plus ML-DSA-87 (FIPS 204), LMS signs only the steward's software releases under contract 7.8's rules, and long-retention records are re-timestamped before an algorithm retires.
*Why:* releases must verify for decades [FIPS 204], and a stateful scheme breaks if an HSM cluster replicates its one-time keys.
*Rejected:* classical signatures alone; switching algorithms at once (old verifiers break); LMS for metadata or provenance (high-volume signing from a finite tree).

### Air-gapped installs and enterprise policy

From phase 3, an offline bundle is one signed archive per release. It holds installers, std packages, the GPU registry, TUF metadata, provenance and archived engines. `crucible mirror import` publishes it on a mirror whose TUF root delegates to the vendor's keys, and `crucible install --offline` verifies it against the embedded root.

From phase 2 one policy schema applies on every OS through ADMX, configuration profiles, `/etc/crucible/policy.json` and MDM. It covers updates, telemetry, crash uploads, egress, clipboard, registries and proxies.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Phase 1 app packages | MSIX, notarized DMG, deb and rpm, OCI images, web assets | An unsigned artifact blocks the release | PLT-O-PKG-2 | 1 |
| Further formats | MSI wrapper, `.pkg`, Flatpak, AppImage | An unsigned artifact blocks the release | PLT-O-PKG-2 | 2 |
| Machine gateway packages | `apps/machine-gateway` for Windows 11 x86-64 and Linux; TPM-held key | No TPM: readings `data_untrusted`. Requires: MFG Gateway | PLT-O-PKG-2 | 2 |
| TUF-verified updates | Full signed packages; expiry, rollback and freeze checks | The installed version stays, with a report | PLT-O-PKG-1 | 1 |
| Delta updates | Block maps, Zucchini and generic patches | Failed patch hash: full file | PLT-O-PKG-1 | 2 |
| Self-test and rollback | 60 s self-test; rollback on failure or two early crashes | Rollback and a filed report | PLT-O-PKG-1 | 1 |
| Repository freshness | apt and dnf metadata expiring within 7 days | Expired metadata refused | PLT-O-PKG-1 | 1 |
| Signature agility | Detached records with algorithm ids; dual signatures; LMS only for software releases | An unknown algorithm id fails closed | PLT-O-PKG-3 | 2 |
| Air-gapped installs | Offline bundle, mirror import, offline install | Bad bundle signature: import refused | PLT-O-PKG-4 | 3 |
| Enterprise policy | One schema on every OS | Invalid value: default kept, error shown | PLT-O-PKG-4 | 2 |
| macOS JIT entitlement | `allow-jit` for Wasmtime | Wasm components refused with the reason | PLT-O-PKG-2 | 1 |

## Reliability

No crash, driver fault or power loss costs a user more than one second of edits, and every failure arrives as a symbolicated report.

### Crash handling

| Mechanism | Choice | Failure behavior |
| --- | --- | --- |
| Native capture | A crash monitor started first; `crash-handler` and `minidumper` write every process's dumps from outside | Monitor gone: minimal in-process report |
| Windows ARM64 | `crash-handler` lacks aarch64 Windows, so an unhandled-exception filter signals the monitor, which calls `MiniDumpWriteDump`; offered upstream in phase 0 | Same minidump format |
| Mobile | `crash-handler` on Android; on iPadOS the shell reports WebKit content-process terminations and restarts the engine | Lower coverage only |
| Panics | Caught at the Op boundary as worker loss: an uncached Abort; the operation is poisoned after 2 panics | "Engine restarted" and replay |
| Processing | rust-minidump with PDB, dSYM and DWARF symbols, kept 2 years, or the support period for LTS lines | Missing symbols block promotion |
| Hang detection | 2 s without a UI event; 10 s without an engine safe point, both measured on `Monotonic` | Reported with a `hang:` signature |

Microsoft advises calling `MiniDumpWriteDump` "from a separate process if at all possible" [Microsoft MiniDumpWriteDump]. Windows Error Reporting's local dumps stay an opt-in, since enabling them "requires administrator privileges" [Microsoft user-mode dumps].

Minidumps hold stacks but never heap memory, so uploads default to `ask`, show their contents, scrub paths and are deleted after 90 days. Promotion needs 99.8% crash-free sessions over the beta's last 7 days (target).

### Autosave and recovery

PLT supplies the journal beneath `repo`'s Changes. Its CRC-checked records are flushed with `WriteDurability::Data` at most every 1 s and on save, close and power changes. A process crash loses nothing appended, and a power failure at most 1 s.

After an unclean exit the engine truncates at the first bad record and replays the rest within 2 s (target). CAS writes go through a temporary file, flush, rename and directory flush, and a torn object fails its hash check.

### Device loss, workarounds and safe mode

Device loss aborts in-flight GPU work and recreates the device after 100 ms, 1 s and 5 s. After 3 losses in 10 minutes, GPU compute turns off.

`gpu-workarounds.json` is a signed, TUF-updated file matched before the first device is created. Its entries name OS, back end, PCI ids, driver ranges, actions from a closed list and a reproducer, and none changes a canonical result. An unsigned or expired file is refused, and every entry's reproducer runs in the GPU lab.

Safe mode starts with `--safe-mode`, Shift at launch or after 2 start-up crashes. It turns off GPU compute, the translator host and Wasm components the lockfile does not require, and requests UIX's most conservative renderer. `apps/platform-*` places each machine in a band from its `HardwareProfile`, and the Performance panel lists every degradation with its cause.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Crash capture, desktop | Out-of-process minidumps, server symbolication | Monitor gone: minimal report | PLT-O-REL-1 | 0 |
| Crash capture, Windows ARM64 and mobile | Exception filter and monitor; WebKit terminations on iPadOS | Reduced coverage, reported | PLT-O-REL-1 | 0 (Windows ARM64), 3 (mobile) |
| Panics | Abort at the Op boundary with a crash id | A panic outside an Op restarts the engine | PLT-O-REL-1 | 0 |
| Hang detection | 2 s UI and 10 s engine watchdogs on `Monotonic` | Reported as `hang:` | PLT-O-REL-1 | 1 |
| Journal and recovery | 1 s flush bound; truncate, replay, report | Bad record: truncated there | PLT-O-REL-2 | 1 |
| Crash-consistent CAS writes | Temporary file, flush, rename | Torn object recomputed | PLT-O-REL-2 | 0 |
| GPU device loss | Backoff recreation, rerun, disable after 3 losses | Abort for in-flight work; CPU path | PLT-O-GPU-2 | 1 |
| Workaround database | Signed, TUF-updated, one reproducer per entry | Unsigned or expired file refused; unknown driver still runs known-answer tests | PLT-O-GPU-5 | 1 |
| Safe mode | GPU, translator host and optional Wasm components off | Never changes a canonical result | PLT-O-REL-3 | 1 |
| Graceful degradation | Degradations listed in the Performance panel | Each names its cause | PLT-O-REL-3 | 1 |

## Telemetry and label-aware egress

Labelled content can leave outside `api`, through notifications, crash dumps, backups, synced folders and clipboard history, so PLT guards those exits. Contract 7.8 also makes PLT the enforcer of network egress.

**Decision D-PLT-38:** Content labelled above `internal` or with non-empty `controls` follows one egress rule outside `api`: notifications and emails carry ids and generic text, crash reports only the signature and modules, reproduction bundles go only to the organization's server, the CAS, journal and caches refuse cloud-synced folders and OS backup, and copies skip clipboard history and cloud clipboards, or `clipboard.labelled = deny` forbids them.
*Why:* ITAR's end-to-end rule requires that "The means of decryption are not provided to any third party" [22 CFR 120.54].
*Rejected:* label checks at `api` only; no notifications or crash reports for anyone.

**Decision D-PLT-39:** One telemetry pipeline, owned by PLT, serves UIX and PLT with one public schema; it is opt-in, rotates an install id never joined to accounts every 90 days, drops aggregates under 50 installs, keeps raw data 90 days and aggregates 13 months, keeps EU data in the EU, and its privacy notice names the steward as controller.
*Why:* people "may be associated with online identifiers provided by their devices" [GDPR recital 30], and two pipelines would differ in payload and retention.
*Rejected:* separate pipelines; compile-time exclusion (breaks the single binary, and policy covers it).

Telemetry collects timings, memory, band, ISA, `GpuClass`, OS, version, command ids and error codes, never design content, values, names, source or account ids.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Notification and email content | Ids and generic text for labelled content | Labelled payload: send refused and logged | PLT-O-PRIV-1 | 1 |
| Crash and reproduction egress | Signature and module list; bundles to the organization | No organization server: bundle kept local | PLT-O-PRIV-1 | 1 |
| Storage placement | CAS, journal and caches outside synced folders and backups | `StorageError::CloudSynced { path, fix }` | PLT-O-PRIV-1 | 1 |
| Clipboard exclusion | History and cloud exclusion; policy can deny | A denied copy explains the policy | PLT-O-PRIV-1 | 1 |
| Telemetry pipeline | One schema; opt-in; rotating id; thresholds; retention; EU region | Schema violation: upload rejected | PLT-O-PRIV-2 | 2 |
| Egress allowlist and webhook proxy | Policy-listed hosts only; webhook deliveries through a proxy that checks each resolved address against ECO's address rules at connect time | Blocked host or refused address logged | PLT-O-PRIV-2, ECO-O-14 | 1 (webhook proxy), 2 |

## Build, release and CI

Agents build Crucible against oracles, so the toolchain, the supply chain and the build rules must keep a poisoned crate or a self-graded builder out of the product.

### Toolchain and dependencies

`rust-toolchain.toml` pins one stable Rust version, moved at most every 6 weeks after the suite passes; the nightly pin serves only D-PLT-10. Dependencies are locked and vendored per release, and cargo-deny checks licences against contract 7.7's list, advisories, bans and sources [cargo-deny]. C and C++ build only through the native-code register in `deps/approved.toml` (Reference).

**Decision D-PLT-40:** Every crate in the engine, UI, server and `wasm-host` closures carries a cargo-vet `safe-to-deploy` audit, which comes only from imported human audit sets the founder approves or from a quarantined review whose model sees the crate source alone, has no tools and returns a typed verdict the founder approves per crate version; an audit an agent writes counts only as the custom criterion `agent-reviewed`, which implies `safe-to-run` in sandboxed CI; adding a crate to the engine closure needs the founder's Approval; CI fails on an unaudited crate or version delta; and build scripts and procedural macros always run in the hermetic builder's sandbox with no network and a read-only source tree.
*Why:* the engine links hundreds of crates while holding every key, `safe-to-deploy` means a crate "will not introduce a serious security vulnerability to production software exposed to untrusted input" [cargo-vet criteria], and a crate's own comments and docs can instruct an agent that audits it.
*Rejected:* licence and advisory checks alone; agent-written `safe-to-deploy` audits; avoiding young crates.

cargo-vet supports custom criteria and implication chains between them [cargo-vet audit criteria]. `deps/approved.toml` records each core dependency's risk tier, cadence and fork plan.

A new version of a dependency waits 14 days. A hijacked maintainer account can publish an advisory and a "fix" together, so a version skips the wait only when all three of these hold:

- the advisory it fixes was published by a party other than the crate's publishers (RustSec, OSV's upstream source or a CVE numbering authority);
- the fixing version comes from an unchanged set of owners;
- its diff from the previous version touches only the advisory's affected files, or passes a quarantined review the founder approves.

**Decision D-PLT-26:** Cargo stays the only build system, accelerated by sccache with a shared remote cache.
*Why:* the workspace is one Cargo workspace, and sccache supports Rust with S3, GCS, Azure, Redis, GitHub Actions and WebDAV back ends [sccache].
*Rejected:* Bazel or Buck2 remote execution (a second build description for every crate); no shared cache.

The targets are a no-op `cargo check` under 2 s, an edit-and-test loop in one operation-family crate under 20 s and a warm-cache CI build under 6 minutes, measured weekly.

**Decision D-PLT-46:** Two independent builders produce byte-identical unsigned artifacts, for Linux and wasm32 from phase 1 and other targets from phase 2, and where PE or Mach-O identity stays out of reach after normalization, SLSA provenance from both builders verifies the release.
*Why:* reproducible builds give "an independently-verifiable path from source to binary code" [Reproducible Builds], as Debian, Arch Linux and NixOS show.
*Rejected:* provenance alone everywhere; blocking releases on PE and Mach-O identity.

### CI stages and capacity

| Stage | Runs | Time budget |
| --- | --- | --- |
| Pull request | Format, determinism lints, layering, cargo-vet, Linux unit tests, wasm32 build, determinism subset | 15 minutes (target) |
| Merge queue | Every Tier 1 target; core crates' unit tests on wasm32 in headless Chrome; the suite on the representative set; golden hashes of pinned `Current` and `Deprecated` versions; golden checks at `Interactive`; instruction counts; engine module size; GPU paths in the renderer image | 45 minutes (target) |
| Nightly | The suite elsewhere; `SignOff` simulations; GPU lab; wall-time benchmarks; random graphs; fuzzing; weekly Tier 3, retired versions in shards and build-speed targets | 6 hours |
| Release | Installers; install, upgrade and uninstall; updates from the last 3 releases; Tier 2 device farm; reproducibility; bills of materials and provenance | 12 hours |

Core crates' unit tests run under wasm-bindgen-test, which runs tests in a browser with `run_in_browser` and headless Chrome [wasm-bindgen-test browsers]. The pinned renderer image fixes the lavapipe build and CPU settings, because llvmpipe "uses LLVM to do runtime code generation" for the host CPU [Mesa llvmpipe].

The GPU lab is rented hardware that agents drive remotely, with fixed drivers and canary upgrades. It holds NVIDIA, AMD and Intel GPUs, Apple silicon, Snapdragon X, a Linux ARM64 desktop and Adreno, Mali and Xclipse tablets.

CI capacity enters each phase budget the founder approves (contract 13.2), estimated ±50%. Phase 0 needs about 1,000 cloud vCPUs, 8 macOS and 8 ARM64 runners and 12 lab machines. Phase 1 needs about 3,000, 24, 24 and 24, and phase 2 about 5,000, 40, 40 and 36.

### Release channels and versions

Versions are calendar-based (`2027.3.0`). Nightly builds run daily and beta branches every 6 weeks, and an LTS line keeps its epoch, Wasmtime line and determinizer version for life.

**Decision D-PLT-27:** Releases follow a 6-week train with security fixes also shipped as patch releases (`x.y.z`); each LTS is cut within 12 weeks of a Wasmtime LTS and supported for 24 months, with Wasmtime fixes backported for the remaining gap of at most 3 months; every release states a five-year Cyber Resilience Act support period, met by free upgrades while the minimum OS and hardware stay fixed, a floor that rises only at an LTS cut, where the last release under the old floor becomes a five-year security-only line; and one LTS line every two years gets 10 years of regulated support, on its retired Wasmtime in a sandbox unless a customer funds backports.
*Why:* regulated programs qualify one version for a decade, the Cyber Resilience Act requires "at least five years" [EU 2024/2847], and Wasmtime supports each LTS for 24 months.
*Rejected:* no LTS; LTS lines longer than Wasmtime's; floor rises on any train.

**Decision D-PLT-47:** Archived engine builds compiled to Wasm stay runnable for the longest supported line plus 2 years, or 12 for regulated lines, signed by the TUF targets role; native builds are kept 5 years, for LTS lines only; the merge queue checks golden hashes only for `Current` and `Deprecated` operation versions that a golden product or registry package pins; and `Retired` versions run from archived engines through KLN's frozen world `crucible:archive/op@1`, re-verified on every toolchain, `detmath` or Wasmtime upgrade and weekly in shards.
*Why:* a retired version's bits depend only on its archive and the Wasm runtime, which their own suites cover, and the frozen world lets today's Kiln call a decade-old engine without a native ABI.
*Rejected:* every version on every merge (CI grows with history); native archives for every release.

Each release compiles `OpCx` against `crucible:archive/op@1` for its archive build, so a retired version runs unchanged in the archived engine. Releases ship a CycloneDX software bill of materials from cargo-cyclonedx and SLSA Build L3 provenance [SLSA levels]. The dependency list is embedded by cargo-auditable as compressed JSON in a linker section. ECO owns export classification and Cyber Resilience Act reporting.

### The build program

Contract 13.2 gives PLT the build program: how the oracle, builder, verifier and observer roles build Crucible against its oracles. Builders read every visible input and could special-case it, and they read untrusted text all day, so the rules below keep their work honest and their contexts contained.

**Decision D-PLT-45:** `oracles/` is a separate, protected Cargo workspace whose `index.toml` lists every oracle id with its crate, capability row, runner class, held-out split and verifier record; for each work item the oracle role first writes a contract crate, `<crate>-contract`, with the public types and signatures the oracles call and `unimplemented!()` bodies, which builders implement and may not change; a work item opens only when each oracle id has a verifier pass; policy refuses builder Changes under `oracles/` or to a contract crate, and loosening a threshold needs the founder's Approval; held-out splits are chosen by HMAC-SHA-256 under a key only the oracle role holds, rotated at each gate, or generated from a seed drawn at CI time; builders' sandboxes have no network route to public corpora; held-out results reach a builder only as one aggregate verdict per work item per day; and visible and held-out runs execute in byte-identical harnesses with case order and count padded to a fixed size.
*Why:* an executable oracle needs signatures to compile against before the builder writes code, a separate workspace keeps builder edits from breaking it, and a public hash rule, per-case results or a detectable harness would each let a builder find or probe the held-out cases.
*Rejected:* oracles written alongside code; oracles in the builders' workspace; a fixed public hash rule; per-case held-out results.

Oracles bind, in order of preference, to `api` methods, the CLI and file formats; then to WIT worlds; then to contract crates (contract 13.2). A held-out failure fails the oracle (principle 6). `gpu-lab` and `device-farm` oracles run on rented hardware, the reference laptops included, and each gate reports oracle coverage per crate. Agent-built corpora enter `oracles/` through a verified Proposal, after agreeing with an independent source such as MPFR, Open CASCADE or libCEED.

Every agent context that reads third-party source, a web page or a paper is `instruction_tainted` from phase 0 (contract 13.2). Tainted contexts write only to their own branches. Their Changes to `core/`, `apps/`, `oracles/`, `deps/` or CI configuration need the founder's Approval, with the taint sources listed. The observer role of the clean-room insight protocol (contract 7.7) works in a workspace outside the repository with egress denied, which PLT provisions; builders never reach it.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Pinned toolchains and vendored dependencies | Stable pin per 6 weeks; nightly only for the threaded web build | A changed golden hash blocks the bump | PLT-O-BLD-6 | 0 |
| Dependency register and audits | Register entries; human or quarantined `safe-to-deploy` audits; `agent-reviewed` only for sandboxed CI; founder Approval for engine-closure additions; sandboxed build scripts | Unaudited crate or delta fails CI | PLT-O-BLD-2 | 0 |
| Dependency hold | 14-day wait; skipped only for third-party advisories with an unchanged owner set and a limited or reviewed diff | A self-filed advisory never skips the wait | PLT-O-BLD-2 | 0 |
| Native-code register | Every C or C++ dependency recorded with targets, flags and result impact | An unregistered C build fails CI | PLT-O-BLD-2 | 0 |
| Build acceleration | sccache and one Cargo workspace; no-op check, edit-and-test loop and warm CI targets | A missed build target files an issue | PLT-O-BLD-6 | 0 |
| Reproducible builds | Byte-identical unsigned artifacts, or provenance for PE and Mach-O | A mismatch blocks the release | PLT-O-BLD-1 | 1 (Linux, wasm32), 2 (all) |
| CI stages and capacity | As tabulated, inside each phase budget | Stage over budget: capacity review | PLT-O-BLD-6 | 0 |
| Pinned renderer image | Fixed lavapipe build; byte-identical Snapshots in CI | Snapshots stay `Unverified` (contract 2) | PLT-O-BLD-1 | 1 |
| GPU lab | Listed devices, fixed drivers, canary upgrades | Outage blocks beta promotion of GPU paths | PLT-O-GPU-1 | 1 |
| Release channels | Train with separate security patches; LTS; five-year lines; regulated support | A canonical change in a line, or no support end date, blocks the release | PLT-O-BLD-3 | 1 (train), 2 (LTS) |
| Archives and retired versions | Retention per D-PLT-47; retired versions through `crucible:archive/op@1` weekly | A missing archive blocks the release | PLT-O-BLD-3 | 2 |
| Software bill of materials and provenance | CycloneDX, embedded list, SLSA Build L3 | A missing artifact blocks the release | PLT-O-PKG-2 | 1 |
| Interface-first work items | Contract crates and verified oracle ids first; separate oracle workspace; coverage per crate | `WorkItemError::OracleMissing { id }`; a builder Change to a contract crate is refused | PLT-O-BLD-4 | 0 |
| Held-out splits | Keyed or seeded splits; no corpus network route; daily aggregate verdicts; padded identical harnesses | A held-out failure fails the oracle | PLT-O-BLD-5 | 0 |
| Tainted builder contexts | Own branches only; founder Approval for protected paths with taint sources listed | Unapproved protected-path Change refused | PLT-O-BLD-4 | 0 |

## Performance engineering

A performance target means only as much as the machine and protocol behind it, so PLT owns the measurement and the gates against slow drift.

**Decision D-PLT-28:** The reference processor is the Intel Core Ultra 7 258V (8 cores, AVX2, Arc 140V GPU) with 32 GB, measured at 1920×1080; at the phase 0 gate PLT names the laptop model, panel and firmware and keeps three units (Windows 11, Ubuntu LTS and a spare), which alone block beta promotion, while other Tier 1 OSes' mid machines land within 1.5 times of each row; PLT names the reference workstation (a 16-core desktop with a discrete GPU) at the phase 1 gate and rents a 64-core server class for the server rows.
*Why:* the 258V runs between "Minimum assured power 8 W" and "Peak turbo power 37 W" [Intel Core Ultra 7 258V], so the chassis sets sustained speed, and as the weaker candidate it turns wider dispatch elsewhere into margin.
*Rejected:* an unnamed chassis; one dual-booted unit; a Ryzen AI 300 (AVX-512 and 24 threads hide costs); Apple silicon.

Bands place every other machine. Low is 4 cores, 8 GiB and an integrated GPU (a 2019 x86-64-v3 laptop, the lowest Snapdragon X laptop, a MacBook Air M1). Mid is 8 to 14 cores and 24 to 32 GiB: the reference laptop, a Snapdragon X Elite, an M4 Pro MacBook Pro and an ARM64 workstation. High is 16 or more cores, 64 GiB and a discrete GPU.

### Measurement protocol

Benchmark files live in `oracles/plt/bench/`, one or more per contract 13.3 row (Reference), each with a held-out variant such as perturbed GP1 parameters or a second sample from the ABC subset. "Warm" means the CAS holds every derived artifact. Rows run 30 times, and browser rows run on mid machines.

Sessions run on AC power in one named power mode after 10 minutes of thermal soak at 20 to 25 °C. OS builds and drivers are pinned, and package power is logged. A calibration workload opens each session, and a result more than 3% off discards it. On a 60 Hz panel, the 120 Hz row moves to the macOS mid machine and does not block beta.

Memory is the sum of the peak resident sets of the UI process, the engine process and any sandbox workers, plus GPU allocations the adapter reports, sampled every 100 ms. Cold start excludes compute pipelines, which compile lazily. The interactive simulation row includes the error estimates of five checked goals, so a part with several regularized-peak checks meets it.

Before phase 2 the forward renderer's capacity per GPU tier is published as a measured target that does not block beta. GPU render pipelines compile in the background, asynchronously on DX12 and Metal.

### Profiling and continuous benchmarking

All crates emit `tracing` spans, exported to Tracy or `performance.measure` on demand [Tracy]. Each merge runs CPU benchmarks under an instruction counter.

Many agents merging in parallel would each pass a per-merge gate while the total drifts by tens of percent, so the gates work at two scales. A rise above 1% in one merge blocks it unless the verifier accepts a recorded reason. Instruction counts per benchmark also stay within 3% of the last beta's baseline. A breach blocks merges touching that crate until a Proposal restores the budget or the founder approves a new baseline. Nightly, a median wall-time rise above 3% confirmed by a Mann-Whitney U test at p < 0.01 files an issue.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Reference machines | Named laptop with three units and fixed conditions; workstation and server class named at the phase 1 gate | A session off its calibration is discarded | PLT-O-PERF-1 | 0 |
| Bands and `HardwareProfile` | Measured properties place every machine | Unknown hardware: low band | PLT-O-PERF-1 | 1 |
| Contract 13.3 rows | File, statistic and held-out variant per row; each blocks from its phase; memory and cold start as defined | A missed row blocks beta; a held-out gap above 10% fails | PLT-O-PERF-1 | 1 |
| PLT's own rows | Update check under 2 KB; library, hashing, module-size and ratio targets | A missed row files an issue | PLT-O-PERF-3 | 1 |
| Instruction-count gates | 1% per merge; 3% cumulative against the last beta | Merge blocked without an accepted reason; crate blocked on a cumulative breach | PLT-O-PERF-2 | 0 |
| Wall-time tracking | Nightly, statistically confirmed | Issue with the commit range | PLT-O-PERF-2 | 0 |
| Profiling | `tracing` spans to Tracy and browser profilers | A disabled span over 5 ns fails | PLT-O-PERF-4 | 0 |

## Reference

### Crates

| Crate | Location | Contents | `unsafe` |
| --- | --- | --- | --- |
| `platform-api` | `core/` | OS-service traits (with `Monotonic`, `Spawner`, `SharedRing`), `RepoPath`, `HardwareProfile`, `IsaLevel`, `GpuClass` | Forbidden |
| `runtime` | `core/` | Pools, IO bridge, combinators, memory budgets, `ChunkedBuffer<T>` | Forbidden |
| `simd` | `core/` | ISA detection, dispatch, canonical horizontal operations | Allowed |
| `detmath` | `core/` | Correctly rounded elementary functions | Forbidden |
| `gpu` | `core/` | Devices, pipelines, known-answer tests, integer reductions, recovery | Allowed |
| `wasm-host` | `core/` | Determinizer, `WasmComponentEngine` trait, Wasmtime implementation and sandbox workers (not on wasm32) | Allowed |
| `linalg`, with frozen versions `linalg-v<n>` | `core/` | Canonical dense and sparse linear algebra, with FLX | Forbidden |
| `platform-windows`, `platform-apple`, `platform-linux`, `platform-web`, `platform-android` | `apps/` | The only crates that bind OS APIs; `platform-web` holds the browser `WasmComponentEngine` and WebCrypto; ELX's flashing service and bench adapters live here | Allowed |
| `desktop`, `web`, `mobile`, `server`, `cli`, `ci-runner`, `tool-runner` (with ECO) | `apps/` | Entry points and packaging metadata | Forbidden |
| `attestation` | `apps/` | KLN's attestation service, packaged by PLT | Forbidden |
| `core-math` | `bridges/` | CORE-MATH's C build behind safe functions | Allowed |
| `lints` | `lints/` | Crucible's dylint library | Forbidden |

`PlatformClass` lives in `base-op`, built from `IsaLevel` and `GpuClass`. `OpCx`, `OpResult` and `Stop` are KLN's, in `base-op`.

### Layering rules

`cargo xtask check-layers` fails CI on any of these:

1. A dependency that breaks contract 12's row order, or a domain crate (`anvil-*`, `flux-*`, `ingot-*`) that depends on `kiln`; only `engine`, `api` and apps see `kiln`.
2. A UI crate (`apps/ui-toolkit`, `apps/renderer`, a UI entry point, `sdk/rust`, `apps/mcp`'s client side) that depends on `api` instead of `api-schema`.
3. A crate outside `apps/platform-*` that binds the OS (`windows`, `objc2*`, `web-sys`, `winit`, `accesskit_*`) or uses `cfg(target_os)`.
4. A crate under `core/` that uses `std::time::{Instant, SystemTime}`, `std::thread`, `std::fs`, `std::net`, `std::process`, `std::env`, or depends on `tokio` beyond `tokio/sync`. tokio's Wasm support covers only `sync`, `macros`, `io-util`, `rt` and `time`, and "enabling any other feature (including `full`) will cause a compilation failure" [tokio].
5. `unsafe` outside `simd`, `gpu`, `wasm-host`, `bridges/` and `apps/platform-*`, or shared memory mapped outside `apps/platform-*`.
6. A C or C++ build outside the native-code register.

`target_arch` dispatch stays allowed in `simd`, `detmath`, `gpu` and `wasm-host`.

### Determinism lints

| Rule | Mechanism | Scope |
| --- | --- | --- |
| No std elementary functions (`f64::exp`, `sin`, `powf` and the rest) | Clippy `disallowed-methods` | Operation crates |
| No `HashMap` or `HashSet` with default hashers | Clippy `disallowed-types` | Operation crates |
| No float reductions on rayon iterators (`sum`, `product`, `reduce` over floats) | Clippy `disallowed-methods` | Operation crates |
| No thread-count queries (`rayon::current_num_threads`, `available_parallelism`) | Clippy `disallowed-methods` | Operation crates |
| No approximate intrinsics outside the allow-list | Clippy `disallowed-methods` | `simd` and operation crates |
| No faer in a `Portable` dependency closure | cargo-deny `bans` with `wrappers` | Every crate a `Portable` operation version depends on |
| No pointer or `usize` value reaching a `Hash` implementation or an encoder | dylint, `lints/` | Operation crates |
| No `as usize` casts of addresses | dylint, `lints/` | Operation crates |
| No `f64::to_bits`, `is_nan` or NaN payload inspection outside `detmath` | dylint, `lints/` | Operation crates |
| `-ffp-contract=off` for every result-affecting C build | Native-code register check | `bridges/` |

### Native-code register

Each entry in `deps/approved.toml` records why no Rust crate serves, its targets including wasm32 (built with clang and a pinned wasi-libc sysroot, or excluded with the Rust fallback named), its compile flags, whether it affects results, and its fuzzing.

| Entry | Why native | wasm32 | Affects results |
| --- | --- | --- | --- |
| CORE-MATH (`bridges/core-math`) | Correctly rounded reference until each Rust port passes | Built with clang and wasi-libc | Yes, the only one |
| mimalloc | The native allocator (D-PLT-14) | Excluded; Rust's allocator | No |
| aws-lc-rs (C and assembly, CMake) | FIPS 140-3 module | Excluded; WebCrypto in `platform-web` | No |
| meshoptimizer (UIX) | Display codecs | Built with clang and wasi-libc | No |
| PETSc, hypre (FLX, optional) | Optional solver bridges | Excluded; Flux's own solvers | Only in non-canonical classes |

### Rust surface

```rust
// platform-api
pub trait Storage: Send + Sync {          // native file systems, or OPFS in browsers
    fn capabilities(&self) -> StorageCaps; // maps, locks, durability, case sensitivity, cloud-synced
    fn map(&self, path: &HostPath) -> Result<MappedBytes, StorageError>;
    fn write_atomic(&self, path: &HostPath, data: &[u8], d: WriteDurability) -> Result<(), StorageError>;
    fn open_journal(&self, path: &HostPath) -> Result<Box<dyn Journal>, StorageError>;
    fn lock(&self, path: &HostPath, mode: LockMode) -> Result<LockGuard, LockError>;
    fn exclude_from_backup(&self, path: &HostPath) -> Result<(), StorageError>;
}
pub enum WriteDurability { Buffered, Data }   // Data: fdatasync, FlushFileBuffers, F_FULLFSYNC, OPFS flush
pub trait Monotonic: Send + Sync { fn now(&self) -> MonoInstant; }   // never visible to evaluation
pub trait Spawner: Send + Sync { fn spawn(&self, task: BoxFuture<'static, ()>); }
pub trait SharedRing: Send + Sync {
    fn publish(&self, slot: u32, bytes: &[u8]) -> Result<(), RingError>;   // writer side
    fn read(&self, slot: u32) -> Result<Vec<u8>, RingError>;               // seqlock copy-out, owned bytes
}
pub trait AccessibilityHost: Send + Sync {   // AccessKit adapter per window; DOM mirror on the web
    fn push(&self, window: WindowKey, update: accesskit::TreeUpdate) -> Result<(), AccessibilityUnavailable>;
    fn take_actions(&self, window: WindowKey) -> Vec<accesskit::ActionRequest>;   // focus and actions routed back
}
pub trait Authenticator: Send + Sync {
    async fn approve(&self, request: ApprovalRequestId) -> Result<CeremonyOutcome, AuthError>;
    async fn assert_call(&self, method: &str, args_digest: [u8; 32]) -> Result<CallAssertion, AuthError>;
}
```

```rust
// runtime
pub enum PoolLane { Drag, Foreground, Background }
impl ComputePool {
    pub fn spawn<R: Send + 'static>(&self, lane: PoolLane, cx: OpCx, f: impl FnOnce(&OpCx) -> R + Send + 'static) -> ExecHandle<R>;
    pub fn boost(&self, exec: ExecId);
}
pub fn det_sum(cx: &OpCx, xs: &[f64]) -> Result<f64, Abort>;   // `?` lifts the Abort into Stop
pub fn exact_sum(xs: &[f64]) -> f64;
impl MemoryBudget { pub fn reserve(&self, bytes: u64, wait: Duration) -> Result<Reservation, Abort>; }
```

```rust
// gpu
pub enum GpuRole { FilterCpuDecides, ClassExact, Witness }
pub enum GpuStop { Fallback(GpuError), Stop(Stop) }   // Fallback: run the CPU path; Stop: as the CPU path would
pub struct GpuPath<I, O> {                            // no GPU-only capability exists
    pub id: &'static str, pub role: GpuRole,
    pub gpu: fn(&OpCx, &dyn GpuCompute, &I) -> Result<O, GpuStop>,
    pub cpu: fn(&OpCx, &I) -> OpResult<O>,
}
pub enum RanOn { Gpu(GpuClass), Cpu { reason: CpuReason } }
```

```rust
// base-op (KLN's crate); this type is PLT's
pub enum PlatformClass {
    CpuCanonical { epoch: u16 },
    CpuIsa { isa: IsaLevel, epoch: u16 },          // X86_64V2..V4, Arm64Neon, Wasm32Simd128
    Gpu(GpuClass),                                 // a registry entry: device class plus pipeline
    Unverified { fingerprint: [u8; 16] },          // unlisted devices and external hosts
}
```

```rust
// wasm-host
pub trait WasmComponentEngine: Send + Sync {   // Wasmtime, sandbox worker, browser runtime
    fn install(&self, determinized: &[u8], world: &WorldSpec) -> Result<InstalledWasmComponent, WasmComponentError>;
    fn instantiate(&self, c: &InstalledWasmComponent, limits: CallLimits) -> Result<Box<dyn WasmInstance>, WasmComponentError>;
}
pub struct CallLimits { pub fuel: u64, pub logical_stack_bytes: u32, pub max_memory_bytes: u64 }
```

### WIT interfaces

`crucible:host` is KLN's package; PLT specifies and implements its `parallel` and `chunk-worker` interfaces. `crucible:tool` is ECO's package; PLT specifies and implements its `process` interface. All stay at `@0.1.0` until contract 13.1's freeze.

```wit
package crucible:host@0.1.0;
interface parallel {
  variant chunk-error { failed(u32), fuel-exhausted }
  map-chunks: async func(count: u32, input: list<u8>) -> result<list<list<u8>>, chunk-error>;
}
interface chunk-worker {
  chunk: func(index: u32, input: list<u8>) -> result<list<u8>, u32>;
}
```

A world that imports `parallel` must export `chunk-worker`. `map-chunks` calls the exported `chunk` once per index on fresh instances, on any thread count, and returns outputs in index order or the lowest failing index. Each chunk runs with the caller's remaining fuel as its limit and the sum is charged afterwards, so `kiln/fuel_exhausted` never depends on thread count.

```wit
package crucible:tool@0.1.0;
interface process {
  record command { program: string, args: list<string>, dirs: list<string> }
  record exit-status { code: s32, stdout: list<u8>, stderr: list<u8> }
  enum process-error { not-declared, sandbox-unavailable, budget-exceeded }
  run: async func(cmd: command, stdin: list<u8>) -> result<exit-status, process-error>;
}
```

`run` exists only in tool worlds and runs programs the manifest declares by digest, with granted directories only.

### Benchmark files per contract 13.3 row

| Contract 13.3 row | Benchmark file | Cache and statistic | Low band (target) | Blocks from phase |
| --- | --- | --- | --- | --- |
| Cold and warm start | `start.toml` | Median; compute pipelines excluded | 4 s and 1.5 s | 1 |
| Primary engine module size | `wasm-size.toml` | Brotli size per release build | Same as mid | 1 |
| Shareable web view | `webview-gp1.toml` | Cold browser cache; median at 50 Mbit/s | 6 s | 1 |
| Selection highlight | `select.toml` | Warm; p99 over 1,000 picks | 33 ms | 1 |
| Orbit | `orbit.toml` | Warm; p95 frame time at 2.1 MP | 30 fps at 1M triangles | 1 |
| Orbit of implicit Bodies | `orbit-implicit.toml` | Warm; p95 frame time | 20 fps | 1 |
| X-ray views | `xray.toml` | Warm; p95 frame time | 15 fps | 2 |
| Animation of moving parts | `animate.toml` | Warm; p95 frame time | 30 fps at 1M triangles | 2 |
| Photoreal still | `photoreal.toml` | Warm; time to mean ꟻLIP ≤ 0.05 | Not set (G1 and G2 only) | 2 |
| Scene capacity | `scene.toml` | Warm; p95 frame time | Half the mid count | 2; high band 4 |
| Drag preview | `drag-early.toml`, `drag-late.toml` | Warm; p90, dependents covered | 250 ms | 1 |
| Rebuild after an early edit | `rebuild-gp1.toml`, `rebuild-abc200.toml` | Warm except the edited chain; p90 | 3 times mid | 1 |
| Certification after an early edit | `certify-abc200.toml` | Certification nodes only; p90 | 3 times mid | 1 |
| Interactive simulation update | `sim-elastic-100k.toml` | Warm-started; median; five checked goals | 3 s | 1 |
| `SignOff` linear static at scale | `signoff-10m.toml`, `signoff-50m.toml` | Cold solve; median of 3 | Not set (workstation and server rows) | 2 (workstation), 3 (server) |
| Incompressible flow throughput | `flow-10m.toml` | Time per iteration; median | Not set (server row) | 3 |
| Open a 1,000-part assembly | `assembly-1000.toml` | Warm CAS, cold process; median | 30 s | 2 |
| Input to photon | `latency.toml` | p99 by camera rig during a rebuild | 50 ms | 1 |
| Memory | `memory-gp1.toml`, `memory-idle.toml` | Peak summed resident sets plus adapter-reported GPU memory, sampled every 100 ms; browser memory after a recycle | As mid | 1 |
| Installed size | Per app package | Release builds | As mid | 1 |
| Flux CPU throughput, both rows | `ceed.toml` | Median | Not set | 1 |

## State of the art

Figures in the last column are targets on the reference laptop unless they cite a source.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Cross-platform determinism | No contraction, own elementary functions, ordered reductions | Box2D; Rapier | One canonical class (D-PLT-19) | Zero hash differences across targets |
| Elementary functions | Correct rounding (CORE-MATH) | glibc 2.43 | CORE-MATH, then Rust ports (D-PLT-17) | MPFR tests; `exp` within 1.5 times glibc |
| FMA-free kernels | Error-free transformations | libCEED and vendor BLAS | Named `CpuIsa` FMA families (D-PLT-18) | Penalty per family |
| Reproducible reductions | Binned summation (ReproBLAS) | oneMKL strict CNR | Fixed trees; `exact_sum` across ranks | `det_sum` at 90% of an unordered sum |
| Canonical linear algebra | Fixed blocking, deterministic pivoting | oneMKL CNR; faer | `linalg` (D-PLT-34) | 2.5 times faer |
| CPU scheduling | Work stealing | rayon; chili | Three pools by lane (D-PLT-13) | Start under 1 ms and 2 ms |
| SIMD | Dispatch per ISA | pulp; fearless_simd | Canonical horizontal order (D-PLT-15) | AVX2 `det_sum` 3 times scalar |
| Determinism lints | Path bans plus custom lint passes | Clippy; dylint | Named mechanism per rule (D-PLT-49) | One planted violation per rule caught |
| Allocation | Thread-local heaps | mimalloc, jemalloc, snmalloc | mimalloc v3 (D-PLT-14) | Macro-benchmarks |
| Out-of-core data | Chunked storage with explicit residency | Zarr v3 chunk stores | `ChunkedBuffer<T>` over the CAS | Assembly row on 2 GiB |
| GPU compute | One kernel source; integer reductions | CUDA libraries; CubeCL | Kernel IR through WGSL (D-PLT-16) | Identity per `GpuClass` |
| Wasm runtime | Ahead-of-time Cranelift, pooling | Wasmtime; V8 | Wasmtime LTS; one browser runtime | 1.6 times native |
| Deterministic Wasm | Injected metering; Wasm 3.0 deterministic profile | Wasmtime fuel | One determinizer, re-run at install (D-PLT-22) | The overhead table |
| Isolated Wasm calls | Component Model async with a `callback` export | Wasmtime with WASI 0.3 | Callback ABI everywhere (D-PLT-36) | 20 µs and 250 µs |
| Browser engine | Threads, SIMD, workers, OPFS, module splitting | Figma (load time over 3 times faster after Wasm) | Threaded build, heavy worker, split module (D-PLT-48) | Suite 2.0 and 2.5 times native; module budget |
| Rust GPU desktop app | Thin platform layer, GPU renderer | Zed | winit, AccessKit, wgpu, Parley | Input-to-photon p99 |
| Crash reporting | Out-of-process minidumps | Crashpad | `crash-handler`, rust-minidump | 99% symbolicated |
| Updates | TUF; executable-aware diffs | Zucchini (Chromium) | TUF, deltas (D-PLT-25) | Attack simulations |
| Build acceleration | Remote caching and execution | Bazel and Buck2 | sccache (D-PLT-26) | Warm CI under 6 minutes |
| Supply chain | Reproducible builds; audits; FIPS 204 | Debian, Arch Linux, NixOS; cargo-vet | Two builders; human or quarantined audits (D-PLT-40, D-PLT-46) | Byte comparison; audit coverage |
| Benchmarking | Instruction counts plus wall time | CodSpeed; Tracy | The same methods, with a cumulative gate | One false gate a week at most |

Contract 13.4's parity floor assigns PLT no capability. The rows below compare what an engineer relies on in an incumbent's platform with what Crucible offers.

| Capability | Incumbent and its documented feature | Crucible's capability row and phase | Standing |
| --- | --- | --- | --- |
| Operating systems | Ansys 2026 R1 focuses on Windows and Linux on Intel and AMD x86, with a few products on ARM64 [Ansys platform strategy 2026] | Tier 1 general availability and Tier 1 preview: Windows, macOS, Linux on x86-64 and ARM64, and four browser engines; phases 1 and 2 | Ahead: macOS, ARM64 and browsers with identical features |
| GPU acceleration | Ansys 2026 R1's fully resident GPU solvers are tested on NVIDIA and, for Fluent, AMD Instinct and Intel GPUs, on Windows and Linux [Ansys GPU compute 2026 R1] | GPU paths with CPU paths, on every Tier 1 GPU including Apple silicon and WebGPU, phase 1; `f64` GPU server paths, phase 3 | Ahead on reach; Later on `f64` GPU `SignOff` solves, which wait for phase 3 Vulkan servers |
| Reproducible numerics | Intel oneMKL reproduces bits only at a fixed thread count, except a few BLAS routines in strict mode on AVX2 or AVX-512 [Intel oneMKL reproducibility] | Platform classes and the determinism suite, phase 0 | Ahead: identical bits at any thread count, instruction set, OS and browser |

## Platform notes

| Platform | Risk to parity | Mitigation | Phase |
| --- | --- | --- | --- |
| Windows | Timeout resets; long paths; undeletable mapped files; antivirus; on ARM64, Wasmtime Tier 3 and no `crash-handler` | Dispatch rule; `\\?\` paths; deferred deletion; packed small objects; own qualification or Pulley; exception filter | 0 to 2 |
| macOS | `allow-jit`; OS-shipped shader compiler; no pen events in winit | Entitlement; OS build in `GpuClass`; carried winit patch | 1 |
| Linux | Wayland gaps; old distributions; ARM64 GPU coverage; X11 pen axes | Portal back ends; glibc 2.34 floor; lab machine; carried winit patch | 0 to 2 |
| Browsers | Isolation; memory that never shrinks; Safari's deletion; partial WebGPU; one module | Isolated threaded build; recycling; sync indicator; WebGL2; split module | 1 to 2 |
| Tablets | No native JIT and App Review on iPadOS; unconfirmed WKWebView capabilities; 16 KB pages on Android | Web build in WKWebView with registry components remote; phase 1 spike with named fallbacks; NDK r28 | 1 to 3 |
| Servers | Shared tenants; no KVM in some VMs | Single-tenant hosts; Firecracker or gVisor | 1 to 4 |
| Tier 3 | No vendor CI | `Unverified` until the suite passes | 5 |

## Interfaces with other subsystems

| To | What | Types | Phase |
| --- | --- | --- | --- |
| KLN | Pool lanes, safe-point flag and `Monotonic` cadence, memory budgets and tables, the platform class for keys, CAS storage, combinators, `detmath`, the mechanism table, the dispatch rule, worker images, the team server install and deployment modes, packaging of the attestation service, heavy and Op workers, label-aware and network egress, the FIPS-mode crypto provider, the `parallel` and `chunk-worker` interfaces of `crucible:host` | `ComputePool`, `PoolLane`, `MemoryBudget`, `PlatformClass`, `Storage`, `ChunkedBuffer<T>`, `CryptoProvider`, `Monotonic` | 0 |
| `repo` | Journal, atomic writes, locks, watching, portable paths, text normalization | `Journal`, `WatchEvent`, `RepoPath` | 0 |
| ANV | Canonical SIMD lanes, `detmath`, `det_sum`, `exact_sum`, `linalg` and its frozen versions, GPU paths, archived engines for retired versions, the Parley stack under `anvil::text_outline` | `simd`, `detmath`, `GpuPath`, `GpuStop` | 0 |
| FLX | `detmath`, combinators, `linalg` jointly, `gpu` with known-answer tests, the dispatch and agreement rules, FMA families, the class enum, the browser memory table, witness-role GPU paths | `GpuCompute`, `GpuPath`, `GpuStop`, `RanOn`, `PlatformClass` | 0 |
| UIX | Windows, input and IME, accessibility hosting, clipboard, dialogs, surfaces, shared display rings, the approval session, hardware profile, workarounds, device loss, safe mode, crash monitor, the `Drag` lane, dispatch rule, memory caps, browser rows, telemetry pipeline, renderer image, native-code register | `WindowHost`, `AccessibilityHost`, `SharedRing`, `Authenticator` | 0; 1 (shared rings, approval session, device loss, safe mode); 2 (telemetry) |
| ING | Executors, the determinizer, verification of generated modules, `detmath` and `det_sum` (Ingot's `sum`), text normalization, the `Drag` lane, the browser memory table | `WasmComponentEngine`, `CallLimits` | 0 |
| ECO | The determinizer with install-time re-runs, the overhead table, Wasmtime LTS, world enforcement, sandboxes with default-deny egress, local External Op sandboxes, the browser runtime and sandbox site, `crucible:tool/process`, offline bundles, TUF and signature formats, release lines and support periods, the webhook egress proxy | `WasmComponentEngine`, `CallLimits` | 0; 1 (install-time re-runs, browser runtime, webhook proxy); 2 (sandbox site, `crucible:tool/process`, LTS lines); 3 (offline bundles, local External Op sandboxes) |
| AGT | `api` transport, `CredentialStore` with the device credential, the approval session and per-call assertions, `Usage` measurement, the stdio sandbox for external MCP servers, the pool lanes behind `PriorityClass`, the build program's taint and audit rules | `Guidance` errors, `Authenticator` | 0 |
| MEC, COV | `linalg`; for MEC also `detmath`, the `Drag` lane and Parley shaping; for COV also `f64` availability per class, with no emulated `f64` on WebGPU, and the browser memory table | `linalg`, `PlatformClass` | 0 |
| ELX | `detmath`, the `Drag` lane, the browser memory table, serial and USB access, hosting of ELX's flashing service and bench adapters in `apps/platform-*`, local External Op sandboxes for vendor models, registry font packages (FLX owns circuit LU) | `DeviceIo` | 1; 2 (serial and USB); 3 (flashing service) |
| MFG | Packages for `apps/machine-gateway`, serial and USB access, the TPM-held gateway key, the browser memory table | `DeviceIo` | 2 |

## Oracles

PLT oracles live in `oracles/plt/`, with held-out splits as D-PLT-45 sets them. Runner classes: `browser-ci` for PLT-O-WEB-1 to PLT-O-WEB-6; `gpu-lab` for PLT-O-GPU-1 to PLT-O-GPU-5, PLT-O-PERF-1, PLT-O-PERF-3 and PLT-O-OS-1 to PLT-O-OS-3; `device-farm` for PLT-O-TGT-1; `cpu-ci` otherwise, with PLT-O-RT-1's browser case on `browser-ci`.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| PLT-O-DET-1 | Canonical identity | Every hash equals the reference on every Tier 1 target, forced ISA level, browser and executor |
| PLT-O-DET-2 | Schedule independence | Identical at 1, 2, 3, 8 and 64 threads with stealing delays and allocator randomization |
| PLT-O-DET-3 | Out-of-core equivalence | Identical with a 64 MiB budget |
| PLT-O-DET-4 | `detmath` correct rounding | Exhaustive f32, hard-case and 10⁹ random f64 inputs match MPFR; ports match the C build |
| PLT-O-DET-5 | Layering and lints | One planted violation per layering rule and per D-PLT-49 rule is caught, `kiln` and `api` edges and std clocks in `core/` included; `-ffp-contract=off` is set for result-affecting C; no crate outside `apps/platform-*` maps shared memory |
| PLT-O-DET-6 | Cross-class agreement | Every `CpuIsa` and `GpuClass` meets D-PLT-35 on golden products and corpora; a planted 3% drift under a shared plan fails |
| PLT-O-DET-7 | Floating-point environment | A planted flush-to-zero library causes an Abort and a correct rerun |
| PLT-O-DET-8 | `detmath` speed | Per-function targets on x86-64-v3 and wasm32 |
| PLT-O-DET-9 | Suite cadence | A planted divergence bisects to its commit, opens an incident and blocks beta |
| PLT-O-LA-1 | `linalg` identity | Identical under two cache settings and any thread count |
| PLT-O-LA-2 | `linalg` speed | Dense n ≥ 1,000 within 2.5 times faer `CpuIsa` |
| PLT-O-GPU-1 | Known-answer tests | A planted fused or reassociated pipeline fails and its Ops run on the CPU; a pass persists until the driver build changes |
| PLT-O-GPU-2 | GPU recovery | Forced loss recovers within 5 s and caches nothing from lost work |
| PLT-O-GPU-3 | GPU primitives and roles | Identity per `GpuClass` over 1,000 runs; injected NaN detected; filters drop no true candidate |
| PLT-O-GPU-4 | Dispatch rule | No dispatch over 4 ms while orbiting; no reset in 1,000 long solves |
| PLT-O-GPU-5 | Workaround database | An unsigned or expired file is refused, and every entry's reproducer runs and shows its fault |
| PLT-O-RT-1 | Runtime contract | `Drag` under 1 ms and `Foreground` under 2 ms at p99 with the other pools loaded, natively and in Chrome with the pool started from the engine worker and a nested pool from the heavy worker; KLN's, FLX's, ANV's and PLT's signatures compile together, and `Failure: From<Abort>` fails to compile |
| PLT-O-RT-2 | Memory exhaustion | Golden products within their rows; exhaustion is an uncached Abort |
| PLT-O-RT-3 | Usage accounting | CPU time within 5% of OS accounting (`getrusage`, `GetProcessTimes`, `task_info`); GPU time within 5% of GPU timestamp queries |
| PLT-O-OS-1 | Shells and input | Create, resize, scale change, minimize, restore, occlusion, close and surface loss give the listed `WindowHost` events on each OS; recorded pointer, pen and HID traces, a macOS tablet and an X11 tablet included, replay identically |
| PLT-O-OS-2 | IME | Japanese, Chinese and Korean composition on each desktop OS |
| PLT-O-OS-3 | Accessibility | Tree snapshots per golden-product screen; OS automation reads names and roles; axe-core passes |
| PLT-O-OS-4 | Platform services | Clipboard, locks, watcher fuzzing, dialogs, notifications, USB loopback; an approval and a per-call assertion against a self-hosted domain on every desktop OS |
| PLT-O-OS-5 | Path portability | A repository created on each OS checks out with identical hashes on the others |
| PLT-O-OS-6 | Text and fonts | Identical text hashes from every OS; identical shaping on every class |
| PLT-O-TGT-1 | Tier 2 targets | The phase 1 iPadOS case reports isolation under the app's URL scheme, sync access handles, WebGPU, memory ceiling and compile time; device-farm smoke tests pass; WebKit and Android executors match canonical hashes |
| PLT-O-TGT-2 | Worker isolation and team servers | Untrusted workers reach no key; no slot crosses tenants; a third-party closure on a shared host is refused; the team server installs with and without KVM |
| PLT-O-TGT-3 | Servers without a GPU | A server image without a GPU runs the golden products with `ran_on: Cpu` and the reason recorded, and canonical hashes unchanged |
| PLT-O-WEB-1 | Isolation, policy and sign-in | The threaded build starts only when isolated and says why otherwise; the served headers match the app origin's policy and a user-form module compiles under them; redirect sign-in works |
| PLT-O-WEB-2 | One engine per origin | Owner closed mid-edit: no Change lost; heavy-worker packs adopted intact |
| PLT-O-WEB-3 | Browser memory | Caps hold on 8 GB and 32 GB machines; a recycle restores idle memory; heavy evaluations at 1 and 8 threads match |
| PLT-O-WEB-4 | Verified web updates | Tampered, rolled-back or frozen manifests refused |
| PLT-O-WEB-5 | Browser hashing | Native-identical `ObjectId`s; 1 GiB in 1 s with 8 workers |
| PLT-O-WEB-6 | GPU path selection | With WebGPU forced absent, the app selects WebGL2 and CPU compute, offers every feature and gives unchanged canonical hashes |
| PLT-O-WASM-1 | Wasm determinism and install checks | Identical outputs, fuel and traps in every executor; spec tests pass; a substituted uninstrumented binary is refused at install |
| PLT-O-WASM-2 | Determinizer overhead | Each class within its row |
| PLT-O-WASM-3 | Cancellation and failure kinds | Cancellation lands at fuel checks, or at Op boundaries within 150 ms at p99 without shared memory; no Abort reaches a memo or the CAS |
| PLT-O-WASM-4 | Observable NaN | NaN-observing modules agree across engines; others are unchanged |
| PLT-O-WASM-5 | Ingot module verification | Each planted violation is rejected |
| PLT-O-WASM-6 | Isolation, egress and worlds | A hostile guest reads no repository, OPFS, token or key; its DNS, TCP, UDP and HTTP attempts fail outside its grant; in every Tier 1 browser engine a sandbox worker cannot `fetch`, open a WebSocket, import scripts, navigate, open an `RTCPeerConnection`, or leak through DNS prefetch or `<link rel=preconnect>`; a local External Op reaches no network and its results stay `Unverified` and uncached |
| PLT-O-WASM-7 | Isolated calls | 10,000 `anvil::offset` calls give identical results through every executor within the isolation rows; std within 15% |
| PLT-O-WASM-8 | WIT interfaces | Published WIT matches this tab; `map-chunks` gives identical outputs and fuel at 1 and 64 threads; an undeclared program is refused |
| PLT-O-PKG-1 | Update security | TUF attacks rejected; power loss during apply leaves a runnable version |
| PLT-O-PKG-2 | Install hygiene | Install, upgrade and uninstall leave no stray files; signatures and notarization verify |
| PLT-O-PKG-3 | Dual signatures | Post-quantum verifiers require both signatures; unknown ids fail closed |
| PLT-O-PKG-4 | Air-gapped installs and policy | Mirror import and offline install verify; every policy applies on every OS |
| PLT-O-REL-1 | Crash capture | Every `sadness-generator` crash type in every process, Windows ARM64 included, is symbolicated |
| PLT-O-REL-2 | Journal durability and engine restart | Random kills lose no appended record; dropped writes lose at most 1 s; a planted truncation of a mapped CAS object ends the engine, which quarantines the object and replays its journal on restart |
| PLT-O-REL-3 | Safe mode and degradation | Safe mode changes no canonical hash; degradations name their cause |
| PLT-O-PRIV-1 | Label-aware egress | With a confidential design open, no notification, email, crash upload or bundle carries content |
| PLT-O-PRIV-2 | Telemetry | Payloads match the schema; small aggregates dropped; allowlist enforced |
| PLT-O-DEPLOY-1 | Deployment modes | Every mode installs from the same signed artifacts and runs the golden products with identical features and canonical hashes; a desktop with no network designs, evaluates, presents and exports one |
| PLT-O-DEPLOY-2 | On-premises package | The Kubernetes package installs, upgrades and refuses a schema mismatch with the reason |
| PLT-O-DEPLOY-3 | Cloud cells | A forced cell failure fails over, and a regulated cell refuses an unauthorized region |
| PLT-O-BLD-1 | Reproducible build | Byte-identical unsigned artifacts; the renderer image reproduces Snapshot bytes |
| PLT-O-BLD-2 | Dependency register and audits | Complete entries; every crate audited; a build script reaching the network fails; a planted crate whose docs instruct its auditor never receives `safe-to-deploy`; a self-filed advisory does not skip the 14-day wait; an unregistered C build fails |
| PLT-O-BLD-3 | Old releases and lines | Archived engines and retired versions reproduce their golden hashes through `crucible:archive/op@1`; patches change no canonical hash; every release states its support end |
| PLT-O-BLD-4 | Interface-first work | Work items naming unverified oracles, builder Changes under `oracles/` or to a contract crate, and unapproved protected-path Changes from tainted contexts are refused; coverage matches a recount |
| PLT-O-BLD-5 | Held-out splits | A planted special-casing implementation fails held-out; builder credentials cannot read the held-out store; builders have no route to public corpora; a planted builder probing held-out results case by case identifies no more cases than chance |
| PLT-O-BLD-6 | Build speed and toolchain | Weekly: a no-op `cargo check` under 2 s, an operation-family edit-and-test loop under 20 s, a warm CI build under 6 minutes and each CI stage within its budget; a toolchain bump that changes a golden hash is blocked |
| PLT-O-PERF-1 | Budgets | Every contract 13.3 row from its phase, memory and cold start as defined, and the primary engine module within its phase budget; other mid machines within 1.5 times; held-out within 10% of visible |
| PLT-O-PERF-2 | Regression gates | Instruction counts within 1% per merge; ten planted 0.9% regressions trip the 3% cumulative gate; wall-time changes confirmed statistically |
| PLT-O-PERF-3 | PLT's own rows | Browser and Wasm ratios, hashing, update check |
| PLT-O-PERF-4 | Profiling overhead | Disabled span under 5 ns; capture under 5% of frame time |

## Phasing

Gate contributions only, consistent with contract 13.1 and 13.2; no capability in contract 13.4's tables belongs to PLT.

| Phase | PLT contribution to the gate |
| --- | --- |
| 0 | Determinism suite green; `detmath` C build and hot ports; `linalg` dense kernels; Wasmtime LTS, determinizer and overhead table; lanes, `OpCx` contract and combinators; layering and determinism lints; platform layers with `Monotonic` and `Spawner`; browser pool start-up; crash capture; the reference laptop named; kill thresholds, memory figures and no-FMA penalties measured; the `CpuIsa` elasticity measurement for WGSL (contract 7.5); the `wasm-split` shared-memory spike; cargo-vet with human and quarantined audits; the oracle workspace, contract crates, held-out store and work-item gate |
| 1 | Contract 13.3's phase 1 rows with the primary module budget; general availability on contract 9's phase 1 targets, with preview targets in automation; the iPadOS capability spike; MSIX, DMG, deb and rpm with TUF; the isolated threaded web build, one engine per origin, heavy worker and recycling; remote third-party evaluation in browsers; native isolation with default-deny egress; install-time determinizer checks; the approval session and per-call assertions; lazy known-answer tests; journal, safe mode and egress rules; reproducible Linux and wasm32 builds; desktop, browser and team server modes; the reference workstation named |
| 2 | Phase 2 rows on GP3 and GP4, the workstation `SignOff` row included; preview targets at general availability; the single-threaded web build for embedded viewers; first LTS line; deltas and further formats; gateway packages; policy and telemetry; the manifest transparency log; dual signatures; reproducible builds or provenance everywhere; the browser sandbox; attestation packaging; cloud and on-premises modes; GP3 and GP4 identical on desktop, browser and server |
| 3 | iPadOS through WKWebView, Android tablets and phone viewers; air-gapped installs and the regulated cloud; local External Ops on desktops; mobile accessibility and crash capture; Vulkan `f64` paths; the server `SignOff` and flow throughput rows; GP5 on Tier 2 |
| 4 | The 1,000,000-Instance high-band row; multi-GPU servers and distributed `exact_sum`; CUDA or HIP reconsidered; GP6 simulations within their rows |
| 5 and later | Tier 3 in the canonical class; SVE dispatch; memory64 re-evaluated; riscv64 servers |

## Open questions

1. **App Review of the iPadOS shell.** Whether Apple accepts a WKWebView shell that runs first-party Wasm components and evaluates registry components remotely waits on App Review of the first phase 3 build; the fallback is a viewer-only iPadOS app with all evaluation remote.

## Contract change requests

None.

## Sources

| Key | Title | URL | Date opened |
| --- | --- | --- | --- |
| 22 CFR 120.54 | 22 CFR 120.54, Activities that are not exports, reexports, retransfers, or temporary imports (Cornell LII) | https://www.law.cornell.edu/cfr/text/22/120.54 | 2026-10-11 |
| AccessKit | AccessKit repository | https://github.com/AccessKit/accesskit | 2026-10-11 |
| Android 16 KB pages | Support 16 KB page sizes, Android Developers | https://developer.android.com/guide/practices/page-sizes | 2026-10-11 |
| Ansys GPU compute 2026 R1 | Ansys 2026 R1 GPU compute capabilities (PDF) | https://ansys.synopsys.com/content/dam/it-solutions/platform-support/2026-r1/ansys-2026-r1-gpu-compute-capabilities.pdf | 2026-10-12 |
| Ansys platform strategy 2026 | Ansys 2026 R1 platform support strategy and plans (PDF, April 2026) | https://ansys.synopsys.com/content/dam/it-solutions/platform-support/2026-r1/ansys-platform-support-strategy-plans-april-2026.pdf | 2026-10-12 |
| Apple allow-jit | Allow execution of JIT-compiled code entitlement, Apple | https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.cs.allow-jit | 2026-10-11 |
| Apple App Review | App Review Guidelines, Apple | https://developer.apple.com/app-store/review/guidelines/ | 2026-10-11 |
| Apple ASWebAuthenticationSession | ASWebAuthenticationSession, Apple | https://developer.apple.com/tutorials/data/documentation/authenticationservices/aswebauthenticationsession.json | 2026-10-11 |
| Apple notarization | Notarizing macOS software before distribution, Apple | https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution.md | 2026-10-11 |
| Apple supporting passkeys | Supporting passkeys, Apple | https://developer.apple.com/tutorials/data/documentation/authenticationservices/supporting-passkeys.json | 2026-10-11 |
| Apple WebContent termination | `webViewWebContentProcessDidTerminate(_:)`, Apple | https://developer.apple.com/tutorials/data/documentation/webkit/wknavigationdelegate/webviewwebcontentprocessdidterminate(_:).json | 2026-10-11 |
| arboard | arboard repository | https://github.com/1Password/arboard | 2026-10-11 |
| aws-lc-rs | aws-lc-rs repository | https://github.com/aws/aws-lc-rs | 2026-10-11 |
| Bazel remote execution | Remote execution overview, Bazel documentation | https://bazel.build/remote/rbe | 2026-10-11 |
| Binaryen wasm-split | Binaryen wasm-split source | https://raw.githubusercontent.com/WebAssembly/binaryen/main/src/tools/wasm-split/wasm-split.cpp | 2026-10-12 |
| Box2D determinism | Determinism, Box2D blog | https://box2d.org/posts/2024/08/determinism/ | 2026-10-11 |
| Buck2 remote execution | Remote execution, Buck2 documentation | https://buck2.build/docs/users/remote_execution/ | 2026-10-11 |
| cargo-auditable | cargo-auditable repository | https://github.com/rust-secure-code/cargo-auditable | 2026-10-11 |
| cargo-cyclonedx | cargo-cyclonedx repository | https://github.com/CycloneDX/cyclonedx-rust-cargo | 2026-10-11 |
| cargo-deny | cargo-deny repository | https://github.com/EmbarkStudios/cargo-deny | 2026-10-11 |
| cargo-deny bans | cargo-deny bans configuration (wrappers) | https://embarkstudios.github.io/cargo-deny/checks/bans/cfg.html | 2026-10-12 |
| cargo-vet audit criteria | cargo-vet audit criteria (custom criteria) | https://mozilla.github.io/cargo-vet/audit-criteria.html | 2026-10-12 |
| cargo-vet criteria | cargo-vet built-in criteria | https://mozilla.github.io/cargo-vet/built-in-criteria.html | 2026-10-11 |
| cargo-vet importing audits | cargo-vet, importing audits | https://mozilla.github.io/cargo-vet/importing-audits.html | 2026-10-11 |
| chili | chili repository | https://github.com/dragostis/chili | 2026-10-11 |
| Chrome Document-Isolation-Policy | Document-Isolation-Policy, Chrome for Developers | https://developer.chrome.com/blog/document-isolation-policy | 2026-10-11 |
| Chromium GPU testing | Chromium GPU testing | https://chromium.googlesource.com/chromium/src/+/HEAD/docs/gpu/gpu_testing.md | 2026-10-11 |
| Clippy configuration | Clippy lint configuration (disallowed-methods, disallowed-types) | https://doc.rust-lang.org/clippy/lint_configuration.html | 2026-10-12 |
| CodSpeed | CodSpeed documentation | https://codspeed.io/docs | 2026-10-11 |
| Component Model concurrency | Component Model concurrency explainer (stackless and stackful async) | https://github.com/WebAssembly/component-model/blob/main/design/mvp/Concurrency.md | 2026-10-11 |
| CORE-MATH | CORE-MATH project | https://core-math.gitlabpages.inria.fr/ | 2026-10-11 |
| Crashpad | Crashpad README | https://chromium.googlesource.com/crashpad/crashpad/+/HEAD/README.md | 2026-10-11 |
| CubeCL | CubeCL repository | https://github.com/tracel-ai/cubecl | 2026-10-11 |
| Dylint | Dylint repository | https://github.com/trailofbits/dylint | 2026-10-12 |
| Embark crash-handling | Embark crash-handling repository | https://github.com/EmbarkStudios/crash-handling | 2026-10-11 |
| EU 2024/2847 | Regulation (EU) 2024/2847 (Cyber Resilience Act), Official Journal | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202402847 | 2026-10-11 |
| EU Cyber Resilience Act | Cyber Resilience Act, European Commission | https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act | 2026-10-11 |
| faer 0.24.4 | faer 0.24.4 documentation | https://docs.rs/faer/latest/faer/ | 2026-10-11 |
| Fearless SIMD 1.0 | Fearless SIMD 1.0, Linebender | https://linebender.org/blog/fearless-simd-1-0/ | 2026-10-11 |
| Figma WebAssembly | WebAssembly cut Figma's load time by 3x | https://www.figma.com/blog/webassembly-cut-figmas-load-time-by-3x/ | 2026-10-11 |
| FIPS 204 | FIPS 204, Module-Lattice-Based Digital Signature Standard | https://csrc.nist.gov/pubs/fips/204/final | 2026-10-11 |
| Firecracker getting started | Firecracker getting started | https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md | 2026-10-11 |
| GDPR recital 30 | GDPR recital 30, Online identifiers for profiling and identification | https://gdpr-info.eu/recitals/no-30/ | 2026-10-11 |
| gemm cache.rs | gemm-common `cache.rs` | https://github.com/sarah-quinones/gemm/blob/main/gemm-common/src/cache.rs | 2026-10-11 |
| Google Play device abuse | Device and Network Abuse policy, Google Play Console Help | https://support.google.com/googleplay/android-developer/answer/9888379 | 2026-10-11 |
| gVisor platforms | gVisor platforms | https://gvisor.dev/docs/architecture_guide/platforms/ | 2026-10-11 |
| HarfRust | HarfRust repository | https://github.com/harfbuzz/harfrust | 2026-10-11 |
| Intel Core Ultra 7 258V | Intel Core Ultra 7 Processor 258V specifications, Intel | https://www.intel.com/content/www/us/en/products/sku/240957/intel-core-ultra-7-processor-258v-12m-cache-up-to-4-80-ghz/specifications.html | 2026-10-11 |
| Intel oneMKL reproducibility | Intel oneMKL reproducibility conditions | https://www.intel.com/content/www/us/en/docs/onemkl/developer-guide-linux/2025-2/reproducibility-conditions.html | 2026-10-11 |
| Jangda 2019 | Jangda, Powers, Berger, Guha. Not So Fast: Analyzing the Performance of WebAssembly vs. Native Code. USENIX ATC 2019 | https://www.usenix.org/conference/atc19/presentation/jangda | 2026-10-11 |
| jco | jco repository | https://github.com/bytecodealliance/jco | 2026-10-11 |
| Landlock | Landlock, Linux kernel documentation | https://docs.kernel.org/userspace-api/landlock.html | 2026-10-11 |
| Linux mmap | mmap(2), Linux manual page | https://man7.org/linux/man-pages/man2/mmap.2.html | 2026-10-12 |
| MacRumors macOS 27 | macOS 27 will mark the end of an era, MacRumors | https://www.macrumors.com/2026/05/26/macos-27-will-mark-the-end-of-an-era/ | 2026-10-11 |
| MDN Atomics.waitAsync | `Atomics.waitAsync()`, MDN | https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Atomics/waitAsync | 2026-10-11 |
| MDN COOP | Cross-Origin-Opener-Policy, MDN | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cross-Origin-Opener-Policy | 2026-10-11 |
| MDN createSyncAccessHandle | `FileSystemFileHandle.createSyncAccessHandle()`, MDN | https://developer.mozilla.org/en-US/docs/Web/API/FileSystemFileHandle/createSyncAccessHandle | 2026-10-11 |
| MDN iframe | `<iframe>` element, MDN | https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe | 2026-10-11 |
| MDN OPFS | Origin private file system, MDN | https://developer.mozilla.org/en-US/docs/Web/API/File_System_API/Origin_private_file_system | 2026-10-11 |
| MDN script-src | CSP script-src, 'wasm-unsafe-eval', MDN | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/script-src | 2026-10-12 |
| MDN showDirectoryPicker | `Window.showDirectoryPicker()`, MDN | https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker | 2026-10-11 |
| MDN storage quotas | Storage quotas and eviction criteria, MDN | https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria | 2026-10-11 |
| MDN SubtleCrypto digest | `SubtleCrypto.digest()`, MDN | https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest | 2026-10-11 |
| MDN Web Workers | Using Web Workers, MDN | https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Using_web_workers | 2026-10-11 |
| Mesa llvmpipe | llvmpipe, Mesa documentation | https://docs.mesa3d.org/drivers/llvmpipe.html | 2026-10-11 |
| Microsoft MiniDumpWriteDump | `MiniDumpWriteDump`, Microsoft Learn | https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/nf-minidumpapiset-minidumpwritedump | 2026-10-11 |
| Microsoft MSIX | What is MSIX? Microsoft Learn | https://learn.microsoft.com/en-us/windows/msix/overview | 2026-10-11 |
| Microsoft user-mode dumps | Collecting user-mode dumps, Microsoft Learn | https://learn.microsoft.com/en-us/windows/win32/wer/collecting-user-mode-dumps | 2026-10-11 |
| mimalloc | mimalloc repository | https://github.com/microsoft/mimalloc | 2026-10-11 |
| NIST CMVP 5314 | NIST CMVP certificate 5314, AWS-LC 3 Cryptographic Module (static), FIPS 140-3 | https://csrc.nist.gov/projects/cryptographic-module-validation-program/certificate/5314 | 2026-10-11 |
| notify | notify repository | https://github.com/notify-rs/notify | 2026-10-11 |
| Parley | Parley repository | https://github.com/linebender/parley | 2026-10-11 |
| pulp | pulp repository | https://github.com/sarah-quinones/pulp | 2026-10-11 |
| Pureinfotech Windows 11 26H2 | Windows 11 26H2 officially released, Pureinfotech | https://pureinfotech.com/?p=192070 | 2026-10-11 |
| Rapier determinism | Rapier determinism guide | https://rapier.rs/docs/user_guides/rust/determinism/ | 2026-10-11 |
| Relaxed SIMD | Relaxed SIMD overview | https://github.com/WebAssembly/relaxed-simd/blob/main/proposals/relaxed-simd/Overview.md | 2026-10-11 |
| ReproBLAS | ReproBLAS | https://bebop.cs.berkeley.edu/reproblas/ | 2026-10-11 |
| Reproducible Builds | Reproducible Builds | https://reproducible-builds.org/ | 2026-10-11 |
| Reproducible Builds success stories | Reproducible Builds success stories | https://reproducible-builds.org/success-stories/ | 2026-10-11 |
| rfd | rfd repository | https://github.com/PolyMeilex/rfd | 2026-10-11 |
| Rust 1.89.0 | Announcing Rust 1.89.0 | https://blog.rust-lang.org/2025/08/07/Rust-1.89.0/ | 2026-10-11 |
| Rust f64 | Rust `f64` documentation | https://doc.rust-lang.org/std/primitive.f64.html | 2026-10-11 |
| Rust File | Rust `File` documentation | https://doc.rust-lang.org/std/fs/struct.File.html | 2026-10-11 |
| Rust portable SIMD | Portable SIMD repository | https://github.com/rust-lang/portable-simd | 2026-10-11 |
| Rust RFC 3514 | RFC 3514, float semantics | https://rust-lang.github.io/rfcs/3514-float-semantics.html | 2026-10-11 |
| Rust scalable vectors | Tracking issue for scalable vectors, rust-lang/rust#145052 | https://github.com/rust-lang/rust/issues/145052 | 2026-10-11 |
| rust-minidump | rust-minidump repository | https://github.com/rust-minidump/rust-minidump | 2026-10-11 |
| rustc platform support | rustc platform support | https://doc.rust-lang.org/rustc/platform-support.html | 2026-10-11 |
| sccache | sccache repository | https://github.com/mozilla/sccache | 2026-10-11 |
| SLSA levels | SLSA 1.0 security levels | https://slsa.dev/spec/v1.0/levels | 2026-10-11 |
| SpiderMonkey memory64 | Is Memory64 actually worth using? SpiderMonkey blog | https://spidermonkey.dev/blog/2025/01/15/is-memory64-actually-worth-using.html | 2026-10-11 |
| SQLite Wasm persistence | Persistent storage options, SQLite Wasm documentation | https://sqlite.org/wasm/doc/trunk/persistence.md | 2026-10-11 |
| tikv-jemallocator | tikv-jemallocator repository | https://github.com/tikv/jemallocator | 2026-10-11 |
| tokio | tokio crate documentation, WASM support | https://docs.rs/tokio/latest/tokio/ | 2026-10-12 |
| Tracy | Tracy repository | https://github.com/wolfpld/tracy | 2026-10-11 |
| TUF overview | The Update Framework overview | https://theupdateframework.io/docs/overview/ | 2026-10-11 |
| TUF specification | The Update Framework specification 1.0.37 | https://theupdateframework.github.io/specification/latest/ | 2026-10-11 |
| Velopack | Velopack repository | https://github.com/velopack/velopack | 2026-10-11 |
| W3C CSP3 | Content Security Policy Level 3, section 6.2.1 webrtc | https://www.w3.org/TR/CSP3/ | 2026-10-12 |
| W3C WGSL | WebGPU Shading Language, W3C Candidate Recommendation Draft, 21 September 2026 (section text read in the specification source, https://raw.githubusercontent.com/gpuweb/gpuweb/main/wgsl/index.bs) | https://www.w3.org/TR/WGSL/ | 2026-10-11 |
| WASI releases | WASI releases | https://github.com/WebAssembly/WASI/releases | 2026-10-11 |
| WASI roadmap | WASI roadmap | https://wasi.dev/roadmap | 2026-10-11 |
| Wasm 3.0 | Wasm 3.0 announcement | https://webassembly.org/news/2025-09-17-wasm-3.0/ | 2026-10-11 |
| Wasm feature support | WebAssembly feature support data | https://raw.githubusercontent.com/WebAssembly/website/main/features.json | 2026-10-11 |
| Wasm memory control | WebAssembly memory-control proposal overview | https://github.com/WebAssembly/memory-control/blob/main/proposals/memory-control/Overview.md | 2026-10-11 |
| Wasm nondeterminism | WebAssembly nondeterminism | https://github.com/WebAssembly/design/blob/main/Nondeterminism.md | 2026-10-11 |
| wasm-bindgen-rayon | wasm-bindgen-rayon repository | https://github.com/RReverser/wasm-bindgen-rayon | 2026-10-11 |
| wasm-bindgen-test browsers | wasm-bindgen-test, testing in headless browsers | https://wasm-bindgen.github.io/wasm-bindgen/wasm-bindgen-test/browsers.html | 2026-10-12 |
| wasm-instrument | wasm-instrument repository | https://github.com/paritytech/wasm-instrument | 2026-10-11 |
| Wasmer runtime | Wasmer runtime documentation | https://docs.wasmer.io/runtime | 2026-10-11 |
| Wasmtime advisories | Wasmtime security advisories | https://github.com/bytecodealliance/wasmtime/security/advisories | 2026-10-11 |
| Wasmtime Config | Wasmtime `Config` documentation (49.0.2) | https://docs.rs/wasmtime/latest/wasmtime/struct.Config.html | 2026-10-11 |
| Wasmtime deterministic execution | Wasmtime deterministic execution | https://docs.wasmtime.dev/examples-deterministic-wasm-execution.html | 2026-10-11 |
| Wasmtime GHSA-394w | GHSA-394w-hwhg-8vgm, Out-of-bounds write or crash when transcoding component model strings | https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-394w-hwhg-8vgm | 2026-10-11 |
| Wasmtime GHSA-6wgr | GHSA-6wgr-89rj-399p, Data leakage between pooling allocator instances | https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-6wgr-89rj-399p | 2026-10-11 |
| Wasmtime platform support | Wasmtime platform support | https://docs.wasmtime.dev/stability-platform-support.html | 2026-10-11 |
| Wasmtime Pulley | Pulley, Wasmtime documentation | https://docs.wasmtime.dev/examples-pulley.html | 2026-10-11 |
| Wasmtime release process | Wasmtime release process | https://docs.wasmtime.dev/stability-release.html | 2026-10-11 |
| Wasmtime releases | Wasmtime releases | https://github.com/bytecodealliance/wasmtime/releases | 2026-10-11 |
| Wasmtime stability tiers | Wasmtime stability tiers | https://docs.wasmtime.dev/stability-tiers.html | 2026-10-11 |
| web-time | web-time README | https://github.com/daxpedda/web-time | 2026-10-12 |
| web.dev COOP and COEP | Making your website cross-origin isolated using COOP and COEP, web.dev | https://web.dev/articles/coop-coep | 2026-10-11 |
| WebGPU implementation status | WebGPU implementation status | https://github.com/gpuweb/gpuweb/wiki/Implementation-Status | 2026-10-11 |
| wgpu Features | wgpu `Features` documentation (30.0.1) | https://docs.rs/wgpu/latest/wgpu/struct.Features.html | 2026-10-11 |
| wgpu releases | wgpu releases | https://github.com/gfx-rs/wgpu/releases | 2026-10-11 |
| winit releases | winit releases | https://github.com/rust-windowing/winit/releases | 2026-10-11 |
| Zarr v3 | Zarr core specification, version 3 | https://zarr-specs.readthedocs.io/en/latest/v3/core/index.html | 2026-10-11 |
| Zed | Zed repository | https://github.com/zed-industries/zed | 2026-10-11 |
| Zucchini | Zucchini README | https://chromium.googlesource.com/chromium/src/+/HEAD/components/zucchini/README.md | 2026-10-11 |
