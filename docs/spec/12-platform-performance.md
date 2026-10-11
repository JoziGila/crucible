# Platform and performance (PLT)

Crucible runs one Rust core on every Tier 1 target behind one platform layer, so OS code lives in one crate. Correctly rounded math, no implicit fused multiply-add and fixed reduction orders make CPU results bit-identical everywhere; each GPU pipeline is verified alone. PLT also owns the Wasm runtime, packaging, reliability, CI, the build program and the performance targets of contract 13.3.

## Scope, crates and the platform layer

PLT owns the mechanisms below the product. Contract 7.3 and 7.4 own the rules, KLN the grade and acceptance policy, and UIX the renderer. This tab holds the one table of nondeterminism sources and every mechanism decision behind it (R3-37, R9-40).

### Crates

| Crate | Location | Contents | `unsafe` |
| --- | --- | --- | --- |
| `platform-api` | `core/` | OS-service traits, `RepoPath`, `HardwareProfile`, `IsaLevel`, `GpuClass` | Forbidden |
| `runtime` | `core/` | Pools, IO bridge, combinators, memory budgets, `ChunkedBuffer<T>` | Forbidden |
| `simd` | `core/` | ISA detection, dispatch, canonical horizontal operations | Allowed |
| `detmath` | `core/` | Correctly rounded elementary functions | Forbidden |
| `gpu` | `core/` | Devices, pipelines, known-answer tests, integer reductions, recovery | Allowed |
| `wasm-host` | `core/` | Determinizer, Wasmtime embedding, sandbox workers | Allowed |
| `linalg` | `core/` | Canonical dense and sparse linear algebra, with FLX | Forbidden |
| `platform` | `apps/` | The only crate that binds OS APIs | Allowed |
| `desktop`, `web`, `mobile`, `server`, `cli`, `ci-runner`, `attestation` | `apps/` | Entry points and packaging metadata | Forbidden |

`PlatformClass` lives in `base`, built from `IsaLevel` and `GpuClass`. `OpCx` in `base` wraps PLT's runtime handles, so operations see one context type (R3-27). PLT's combinators are free functions over it, and `OpCx` offers no second reduction API (R9-39).

**Decision D-PLT-1:** OS services sit behind traits in `core/platform-api`, implemented by exactly one crate, `apps/platform`, and injected at startup by the app shell. *Why:* core crates stay OS-agnostic, and tests inject in-memory implementations, so storage and clocks never leak into evaluation. *Rejected:* `cfg(target_os)` in core crates (untestable); one crate per OS service.

`cargo xtask check-layers` fails CI when a crate outside `apps/` binds the OS (`windows`, `objc2*`, `web-sys`, `winit`, `accesskit_*`) or uses `cfg(target_os)`. It also enforces contract 12's row order; `target_arch` dispatch stays allowed in `simd`, `detmath` and `gpu`.

[[DIAGRAM diagrams/12-platform-crate-layering.jsx: crate layering · dependencies point down, one crate binds the OS]]

Read the diagram top down: each layer depends only on layers below it, and `apps/platform`, at the side, implements the bottom layer's traits.

**Decision D-PLT-4:** winit provides windows, the event loop and raw input on every target. Crucible pins one 0.31 beta commit on its own patch branch, re-pins at each beta and sends its pen, IME and drag-out fixes upstream. *Why:* only winit covers desktop, web, iOS and Android, and 0.31.0-beta.3 adds pen, IME and positional drag events, but betas break APIs (R6-39). *Rejected:* SDL3 (a C dependency); GPUI's platform layer (no web target); staying on 0.30. (revised in round 3)

### OS services

Every PLT error implements `Guidance` (`why`, `fix`), which maps into the `api` error shape.

```rust
pub trait Storage: Send + Sync {          // native file systems, or OPFS in browsers
    fn capabilities(&self) -> StorageCaps; // maps, locks, durability, case sensitivity, cloud-synced
    fn map(&self, path: &HostPath) -> Result<MappedBytes, StorageError>;
    fn write_atomic(&self, path: &HostPath, data: &[u8], d: WriteDurability) -> Result<(), StorageError>;
    fn open_journal(&self, path: &HostPath) -> Result<Box<dyn Journal>, StorageError>;
    fn lock(&self, path: &HostPath, mode: LockMode) -> Result<LockGuard, LockError>;
    fn exclude_from_backup(&self, path: &HostPath) -> Result<(), StorageError>;
}
pub enum WriteDurability { Buffered, Data }   // Data: fdatasync, FlushFileBuffers, F_FULLFSYNC, OPFS flush
```

`Journal`, `WindowHost`, `FileWatcher`, `Clipboard`, `Dialogs`, `Notifications`, `CredentialStore`, `SystemSignals` and `WallClock`, which never reaches evaluation, follow the same pattern. `DeviceIo` opens serial and USB ports outside evaluation for MFG's machine gateway and ELX's bench adapters.

`CryptoProvider` supplies TLS, hashes and signatures, and KLN's FIPS mode routes it through a FIPS 140-3 module. The candidate is AWS-LC through aws-lc-rs, whose FIPS 3.x build "has been submitted to NIST for certification" [certificate status unverified].

`Authenticator` opens the approval page of contract 7.6 for one request id and reports when the ceremony ends. It never handles a credential.

**Decision D-PLT-41:** Every client approves in a browser on the approval origin, which has its own WebAuthn relying-party id (AGT, UIX). The web app opens it as a top-level window, macOS and iPadOS through `ASWebAuthenticationSession`, and Windows and Linux in the default browser. The session is bound to the request id, returns by a `crucible://` callback, and the app reads the outcome from `api`. *Why:* an app "can't use passkeys to authenticate for services that you haven't configured as the app's associated domains" (R12-15). A separate origin keeps script injected into the main app away from the ceremony (R11-05). *Rejected:* native WebAuthn per OS; an embedded webview the app can script; the main origin.

Enrollment uses the same session, and only UIX's approval flow may call `Authenticator`.

### Paths, text and accessibility

`RepoPath` is UTF-8 in NFC, `/`-separated and relative, without `.` or `..`. Segments hold at most 255 bytes and no control characters, `< > : " | ? * \`, trailing dot or space, or Windows device name. Paths equal after case folding collide (`PathError::CaseCollision`), and other paths are opaque `HostPath`s that never enter the CAS.

**Decision D-PLT-5:** Repository paths are portable by construction: NFC, `/`-separated, case-fold unique and free of names any Tier 1 OS rejects. *Why:* a name valid only on Linux, or two names differing only in case, splits a team across operating systems. *Rejected:* OS-native paths; silent normalization at checkout (two names map to one file).

**Decision D-PLT-6:** Repository text is UTF-8 with LF line endings and no byte-order mark. Readers normalize CRLF, CR and BOM on input. *Why:* content hashes must not depend on the OS that wrote the file. *Rejected:* per-OS line endings converted at checkout (hashes depend on settings).

**Decision D-PLT-7:** Design text uses fonts from registry packages pinned in `ingot.lock`, shaped by the pure-Rust Parley stack. System fonts serve only the UI. Ingot reaches shaping only through ANV's `anvil::text_outline`, whose missing font is ANV's `FontMissing` (R9-30). *Why:* system fonts differ by OS and version, so engraved text would change geometry between machines. *Rejected:* DirectWrite and Core Text; system fonts in designs. (revised in round 3)

**Decision D-PLT-8:** A web accessibility adapter mirrors the AccessKit tree into a hidden ARIA DOM and routes focus and actions back. It is offered upstream. UIX's toolkit risk spike exercises it first, with PLT's IME paths and Windows AccessKit hosting (R12-08). *Why:* AccessKit has no released web adapter, and identical features include accessibility. *Rejected:* a separate HTML UI (drifts); waiting for upstream. (revised in round 3)

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Layered crates | Only `apps/platform` binds OS APIs; contract 12's order | Layering check fails the build | PLT-O-DET-5 | 0 |
| Windows and surfaces | `WindowHost` gives raw handles to the renderer | `PlatformError::Window { backend, reason, fix }` | PLT-O-OS-1 | 0 |
| Pointer, pen and touch | One `PointerEvent` stream with pressure and tilt | Missing axes are `None` | PLT-O-OS-1 | 1 (desktop), 3 (tablets) |
| Keyboard and IME | Physical key, logical key and text apart; preedit and commit | No IME: plain input, with a notice | PLT-O-OS-2 | 1 |
| 6-DoF devices | `NavDeviceEvent` from HID; spacenavd on Linux | Device absent: no events | PLT-O-OS-1 | 2 |
| Accessibility | AccessKit tree per window; web DOM mirror | `AccessibilityUnavailable` logged once | PLT-O-OS-3 | 1 (desktop, web), 3 (tablets) |
| Clipboard | Plain-text Ingot plus `application/x-crucible+cbor` | `ClipboardError::Unavailable { reason }` | PLT-O-OS-4 | 1 |
| Drag and drop | Incoming through winit; outgoing per OS | "Export…" offered with the reason | PLT-O-OS-4 | 1 (incoming), 2 (outgoing) |
| File dialogs | Async `open`, `save`, `pick_folder` | No portal on Linux: in-app browser | PLT-O-OS-4 | 1 |
| Notifications | `Notifications::post` under D-PLT-38 | Denied: notice in the activity panel | PLT-O-OS-4 | 1 |
| File watching | `Changed`, `Rescan`, `Health` events | Overflow: `Rescan`, "watching by polling" | PLT-O-OS-4 | 1 |
| File locking | Exclusive lock on `.crucible/lock` | `LockError::Held { holder_pid, since }` | PLT-O-OS-4 | 0 |
| Credentials | `CredentialStore` per account | `CredentialError::Unavailable` | PLT-O-OS-4 | 1 |
| WebAuthn | Approval and enrollment in a browser session (D-PLT-41) | No session: approval refused with the reason | PLT-O-OS-4 | 1 |
| Serial and USB | `DeviceIo` on native targets, outside evaluation | `DeviceError::Unavailable { port, reason }` | PLT-O-OS-4 | 2 |
| FIPS-mode cryptography | `CryptoProvider` through a FIPS 140-3 module | Non-approved algorithm refused | KLN-O-SIG-2 | 2 |
| System signals | Memory pressure, power, thermal state, scale, reachability | Unavailable signal: `Unknown` | PLT-O-OS-1 | 1 |
| Portable paths | `RepoPath::parse`; OS paths only in `platform` | `PathError` with a portable name | PLT-O-OS-5 | 0 |
| Text normalization | UTF-8, LF, no BOM | `TextError::InvalidUtf8 { offset }` | PLT-O-OS-6 | 0 |
| Design fonts | Registry fonts pinned by hash | `FontError::MissingGlyph { char, font }`, never a substitution | PLT-O-OS-6 | 1 |

## Targets

Contract 9 fixes the tiers, the preview rule and parity. This section fixes versions, CPUs, back ends and executors.

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

Per the gpuweb status page, Chrome ships WebGPU on Linux only for Intel Gen12+ and NVIDIA on Wayland, and behind a flag on Windows ARM64. Firefox ships it on Windows since 141 and macOS from 145.

Wasmtime rates Windows ARM64 Tier 3, lacking "CI testing, full-time maintainer", and aarch64 macOS and Linux Tier 2, lacking "Continuous fuzzing" (R6-12). Crucible qualifies these targets itself (R12-21).

Every merge runs Wasmtime's test suite and PLT-O-WASM-1 to PLT-O-WASM-7 on these targets, with 24 hours of fuzzing a week. A target unqualified at the phase 2 gate runs Wasm components through Pulley and declares the speed as capacity.

Preview targets meet contract 9 thus (R12-24): golden checks run in automation, Safari through safaridriver on a macOS host. Each target publishes an Accessibility Conformance Report with an external audit. Driver qualification means PLT-O-GPU-1 to PLT-O-GPU-4 and UIX-O-SNAP-2 pass on every listed lab device.

**Decision D-PLT-2:** Native x86-64 builds target x86-64-v2 and dispatch hot kernels at run time to x86-64-v3 and x86-64-v4; ARM64 builds target ARMv8 with NEON. *Why:* every dispatched path gives identical canonical bits, so a low baseline costs speed only in cold code. *Rejected:* an x86-64-v3 baseline (drops CPUs without AVX2); per-CPU builds.

**Decision D-PLT-3:** Linux binaries link against a glibc 2.34 sysroot with no newer symbols, and Wayland is a first-class target equal to X11. *Why:* engineering desktops run long-lived distributions. *Rejected:* static musl desktop builds (GPU drivers load through the system loader); per-distribution builds.

### Tablets and phones

Tier 2 covers viewing, review and light editing with the same core crates and UI. Heavy evaluation is remote by default, and phones never approve Acts.

**Decision D-PLT-33:** iPadOS runs the web build in a thin WKWebView shell, where JavaScriptCore compiles Wasm (contract 7.4). The app runs only first-party Wasm components shipped in its binary and evaluates registry Wasm components remotely. *Why:* `allow-jit` exists only on macOS, Pulley carries "a ~10x order-of-magnitude slowdown" (R6-13), and downloaded code would bring guidelines 2.5.2 and 4.7 into play (R12-14). *Rejected:* native engine threads beside a WKWebView worker (they cannot answer its imports); Pulley; local registry Wasm components. (revised in round 3)

The app thus meets App Review guidelines 2.5.2 and 3.2.2(i) and stays outside 4.7. Embedded WebKit apps get about 15% of disk, the figure the Tier 2 storage plan uses (R12-31). A phase 3 spike measures only WKWebView memory limits and WebGPU.

Google Play's ban on downloaded code "does not apply to code that runs in a virtual machine or an interpreter". Android runs Wasmtime with Cranelift, and no world imports Android APIs (R6-41). Builds use NDK r28 for the 16 KB pages Google Play requires from 1 February 2027.

### Tier 3 and servers

FreeBSD, OpenBSD, NetBSD, illumos and riscv64 Linux are community-supported, CLI and server first. Their results stay `Unverified` and local until they pass the determinism suite.

Servers are OCI images for x86-64 and ARM64 that compute in the canonical class. Optional GPUs serve `f64` Vulkan solves from phase 3, and CUDA or HIP is reconsidered at the phase 4 gate.

PLT builds the images for contract 7.8's pools. Untrusted-evaluation workers are single-use microVMs with no key and no network unless granted (D-PLT-43). Trusted builders evaluate merged Changes (R9-46).

They run first-party code per (tenant, confidentiality label), and anything else in single-use microVMs on single-tenant hosts (R11-03, R11-22). Labels with non-empty `controls` get dedicated VMs, and `apps/attestation` signs only trusted-builder work from phase 2.

**Decision D-PLT-44:** The single-node team server installs on a Linux host or VM, not in one container, and runs its services as OCI containers. Proposal CI uses Firecracker where `/dev/kvm` exists and gVisor otherwise, and the health check refuses Proposal CI when neither works. The trusted builder runs as its own OS user, outside the sandbox service, and is the only caller the signing service accepts (contract 7.8, R11-10). *Why:* "Firecracker requires read/write access to `/dev/kvm`", which cloud VMs rarely expose, while gVisor's systrap platform suits "running inside a VM" (R12-20). *Rejected:* one container (no KVM, one boundary for both pools); requiring bare metal.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Tier 1 general availability | Windows 11 x86-64, macOS, Linux x86-64, Chrome and Edge pass every golden product | A divergence blocks beta promotion | PLT-O-DET-1 | 1 |
| Tier 1 preview | Windows 11 ARM64, Linux ARM64 desktop, Safari, Firefox: same build, suite and golden checks in automation | A missing installer, updater, report or driver qualification blocks general availability | PLT-O-DET-1 | 1 (preview), 2 (general) |
| Upstream Wasmtime coverage | Crucible's own qualification per merge, with weekly fuzzing | Unqualified at the phase 2 gate: Pulley | PLT-O-WASM-1 | 0 |
| Tier 2 tablets and phones | Same `api` and UI; light local editing | Over budget: remote evaluation offered | PLT-O-TGT-1 | 3 |
| iPadOS Wasm executor | The web build in WKWebView; registry Wasm components remote | Memory limit: evaluation goes remote | PLT-O-TGT-1 | 3 |
| Android Wasm executor | Wasmtime with Cranelift; no Android API imports | A direct Android import fails to load | PLT-O-TGT-1 | 3 |
| Tier 3 targets | Community builds, `Unverified` until the suite passes | Results stay local | PLT-O-DET-1 | 5 |
| Server images | OCI images on x86-64 and ARM64 in the canonical class | Missing GPU: CPU path, reported | PLT-O-DET-1 | 1 |
| Untrusted-evaluation workers | Single-use microVMs, no key, no network unless granted | Write outside the namespace destroys the VM | PLT-O-TGT-2 | 1 |
| Trusted builders | Third-party code only in microVMs on single-tenant hosts | Shared host for a third-party closure: refused | PLT-O-TGT-2 | 1 |
| Team server install | Host or VM; Firecracker or gVisor; separate builder user | No back end: Proposal CI refused | PLT-O-TGT-2 | 1 |
| Attestation service | HSM keys; signs only trusted-builder results | Unbound request refused and logged | PLT-O-TGT-2 | 2 |

## The browser target

The browser runs the same core crates compiled to `wasm32-unknown-unknown` in the canonical class, so browsers, desktops and servers share cached results bit for bit.

| Context | Runs | May block |
| --- | --- | --- |
| Main thread | Input, accessibility DOM mirror, frame presentation | Never |
| Engine worker | `api` server side, Kiln, CAS, journal, OPFS write handles | With `Atomics.wait`, only while no IO is pending |
| Compute workers, max(1, min(`hardwareConcurrency` − 1, 16)) | The engine's pool through wasm-bindgen-rayon | Yes |
| Heavy worker | One disposable evaluation with its own memory and pool | Yes |
| Op worker, single-threaded build only | One disposable Op estimated above 100 ms | Yes |
| Wasm component sandbox, from phase 2 | Third-party Wasm components on a separate site (D-PLT-42) | Yes |
| Service worker | Offline cache, verified updates, port brokering | Never |

The threaded build passes `api` messages and triangle buffers through `SharedArrayBuffer` rings, and the single-threaded build through transferred buffers.

**Decision D-PLT-29:** One engine runs per browser origin. The first tab's engine worker takes a Web Lock and owns every OPFS write handle, except packs a heavy worker is still writing. A heavy worker writes each pack under a name only it holds and then sends the index for adoption. Other tabs reach it through a `MessagePort`, and the next tab takes over and replays the journal when the owner closes. *Why:* a synchronous access handle "takes an exclusive lock on the file", and `opfs-sahpool` fails when initialized twice in one origin (R6-15, R12-19). *Rejected:* one engine per tab; the `opfs` VFS (needs isolation); heavy-worker writes through the engine (double copies). (revised in round 3)

### Isolation and sign-in

WebAssembly threads need `SharedArrayBuffer`, which needs `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp`. Crucible serves every asset from its own origin with CORP headers, and team servers report a missing header. Embedded viewers use `Document-Isolation-Policy`, "shipping in Chrome 137 for desktop only", and the single-threaded build elsewhere.

**Decision D-PLT-9:** The web build ships a threaded engine (atomics, bulk memory, SIMD128) and a single-threaded one (SIMD128) from one source. The page loads the threaded build only when `crossOriginIsolated` is true and says why otherwise. Without shared memory, cancellation lands at Op boundaries. Kiln therefore runs each Op estimated above 100 ms in a disposable Op worker and terminates it to cancel (contract 7.4). *Why:* features and bits stay identical, and a cancel message cannot reach a worker blocked in an Op (R12-17). *Rejected:* refusing to run without isolation (breaks embeds); a single-threaded product; host yields at fuel checks (they run on the blocked thread). (revised in round 3)

The single-threaded build reaches idle within 150 ms of a cancel at p99 (target), and contract 13.3's drag row is measured on the threaded build.

**Decision D-PLT-10:** The threaded web engine builds with a nightly toolchain pinned per release and `-Zbuild-std`; every other artifact uses pinned stable Rust. *Why:* wasm-bindgen-rayon's thread support "is still only available in nightly", and Rust's float semantics keep results independent of the compiler, which the suite verifies. *Rejected:* a hand-written worker runtime; dropping browser threads (a 4 to 16 times loss).

`same-origin` severs references to cross-origin popups (R6-45). Sign-in therefore redirects to a non-isolated page that completes the authorization-code exchange with PKCE. It keeps the token as a non-extractable WebCrypto key.

The web build requires SIMD128, threads and bulk memory, which every Tier 1 browser ships (Safari since 16.4). Relaxed SIMD, memory64, exception handling and JS Promise Integration are not used.

### Memory

**Decision D-PLT-11:** The browser engine stays wasm32 with 4 GiB of address space. Large models use out-of-core chunks in OPFS, a heavy worker and remote evaluation. *Why:* memory64 caps at 16 GiB, is in Safari only in Technology Preview, and costs 10% to over 100% in SpiderMonkey's measurements. *Rejected:* a memory64 build for Chrome and Firefox only (two behaviors for one Tier 1 target). It is revisited when Safari ships memory64 and the penalty on the PLT suite falls below 10%.

**Decision D-PLT-30:** The engine worker keeps a fixed linear-memory cap. Evaluations estimated above 512 MiB run in a disposable heavy worker, and larger ones go remote. The heavy worker starts its own pool of min(`hardwareConcurrency` − 2, 8) nested workers while the engine pauses its pool. Kiln's cost model counts the start-up. Above 768 MiB and after 30 s idle, the engine worker hands the Web Lock to a fresh one, which replays the journal. *Why:* Wasm memory "can only grow and never shrink" (R6-14, R12-18). Compute workers share the engine module's memory, not the heavy worker's (R12-19). *Rejected:* one growing engine worker; single-threaded heavy evaluations; memory64. (revised in round 3)

Workers "may spawn more workers" from the same origin, which the nested pool relies on. In contract 9's browser memory table below, the phase 0 gate replaces each starting value per browser engine. The rule is the largest value 25% below the kill threshold measured on the 8 GiB low-band machine.

| Context | Cap or target | Rule |
| --- | --- | --- |
| UI module | 512 MiB linear memory (starting value) | UIX owns the contents |
| Engine worker | 1.5 GiB (starting value); recycles above 768 MiB after 30 s idle | Kiln evicts to OPFS; larger reservations go to the heavy worker |
| Heavy worker | min(4 GiB, kill threshold − UI cap − engine cap − 512 MiB) | One at a time, terminated after each evaluation |
| Idle, UI plus engine | 300 MiB after an engine recycle | Contract 13.3 memory row |
| GP1 open | 1.5 GiB of linear memory in total | Same row |
| Suspended feature calls | 500 at once in 256 MiB of the engine cap (ING) | Reserved as used (R3-33) |

### Storage, hashing and updates

The CAS, journal and package cache live in OPFS, whose synchronous handles work only in dedicated workers. Quotas are about 60% of disk in Chrome, Edge and Safari.

Firefox allows the smaller of 10% or 10 GiB, or up to 50% with persistence (R12-31). Safari deletes script-written data after seven days without interaction.

The engine requests persistence at first use. The browser CAS is a cache of the team server, or of a folder picked through `showDirectoryPicker`, which is not Baseline. Unsynced edits show "not yet synced".

The browser CAS hashes chunks of at most 1 MiB in parallel with `crypto.subtle.digest`, which "does not support streaming input". A Wasm SHA-256 serves small objects (R6-44).

The target is 1 GiB in 1 s across 8 workers. A miss relaxes the browser row to the measured value rather than adding a second hash (R9-51).

A service worker caches the shell, engines, fonts and std packages under content-hashed URLs and activates a new version on the next load. Each release's manifest is verified against TUF targets, and from phase 2 logged in a transparency log (R5-12, R9-45).

Browsers ran 45% to 55% slower than native on SPEC CPU (Jangda and colleagues). Targets (R6-33): the suite within 2.0 times native single-threaded, 2.5 times multi-threaded and 3 times for SIMD-heavy kernels.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Two web builds | Threaded when `crossOriginIsolated`; identical hashes | "Threads unavailable: the site is not cross-origin isolated" | PLT-O-WEB-1 | 0 |
| Cancellation without shared memory | Op boundaries; disposable Op workers | Over 150 ms to idle at p99 fails | PLT-O-WASM-3 | 1 |
| Sign-in under isolation | Redirect-based authorization code with PKCE | Popups never offered | PLT-O-WEB-1 | 1 |
| One engine per origin | Web Lock owner holds the write handles; packs adopted | Owner closes: next tab replays | PLT-O-WEB-2 | 1 |
| Browser memory table | Cap and recycle; heavy worker with its own pool | `ResourceExhausted` Abort with a remote offer | PLT-O-WEB-3 | 1 |
| OPFS storage | Persistence requested; CAS as cache; sync indicator | Eviction: refetch; local-only edits warned | PLT-O-WEB-3 | 1 |
| Chunk hashing | Parallel `crypto.subtle.digest`; native-identical `ObjectId`s | Digest failure: Wasm SHA-256 | PLT-O-WEB-5 | 1 |
| Verified updates | TUF-verified manifest; transparency log from phase 2 | The running version stays | PLT-O-WEB-4 | 1 |
| GPU path selection | WebGPU, else WebGL2 and CPU compute | "WebGPU unavailable", same features | PLT-O-DET-1 | 1 |
| Startup and payload | Contract 13.3's browser rows | A missed row blocks beta promotion | PLT-O-PERF-1 | 1 |
| Browser speed | Suite ratios 2.0 and 2.5; SIMD-heavy 3 | Regression filed nightly | PLT-O-PERF-3 | 1 |

## The compute runtime

The `runtime`, `simd`, `gpu` and `linalg` crates execute what Kiln schedules, and no choice of cores, vector units or GPUs changes a canonical result.

**Decision D-PLT-12:** The UI talks to the engine only through `api`. The engine runs as an OS process on desktop, a worker in browsers and on iPadOS, threads on Android or a remote `server`. Third-party code runs in sandboxes (D-PLT-31). *Why:* one boundary keeps the UI identical, and an engine crash leaves the window intact while the engine replays its journal. *Rejected:* one desktop process (a crash closes the window); one process per Op (too slow for drag). (revised in round 3)

Desktop UI and engine processes share memory-mapped rings for tessellations and Field samples and exchange `api` messages over a local socket. On Linux a higher `oom_score_adj` makes the kernel stop the engine first.

[[DIAGRAM diagrams/12-platform-process-model.jsx: process and thread model · four targets]]

Read each column as one target: tinted boxes run engine code, dashed boxes are sandboxed, and arrows are the only channels between UI and engine.

### Threads and pools

| Thread or pool | Size | OS priority | Work |
| --- | --- | --- | --- |
| IO runtime (tokio natively, the event loop in browsers) | 2 workers plus a blocking pool | Normal | IPC, network, file IO |
| Interactive pool (rayon) | One per logical core | QoS user-interactive; Windows above normal | Drag previews and per-pointer edit tools |
| Foreground pool (rayon) | One per logical core | QoS user-initiated; Windows normal | Selection, `Preview` results, awaited requests |
| Background pool (rayon) | One per core, halved on battery | QoS utility; EcoQoS; nice 10 | Rebuilds, `SignOff` work, prefetch |
| GPU queue thread | One per device | User-interactive | Encoding, submission, readback, device loss |

`PoolLane` has three values (R9-07). KLN's priority table maps the drag lane and UIX's interactive edit lane to `Interactive`, AGT's interactive `PriorityClass` to `Foreground` and the rest to `Background`.

`Interactive` work pauses `Foreground` work at its next chunk boundary until the lane idles, which never changes a reduction tree. Kiln also promotes a waiting background Op and calls `ComputePool::boost` for a running one.

Operations are pure and read data through the residency manager. The browser engine worker awaits pools through `Atomics.waitAsync` (Baseline 2025), and `OpCx` checks cancellation at every chunk boundary and fuel check.

An `Interactive` Op starts within 1 ms and a `Foreground` Op within 2 ms at p99 while other pools are busy (targets). Ops estimated above 10 core-seconds take a deterministic work budget from AGT's `Budget` and reach a safe point every 10 core-seconds. Exhausting it is KLN's `BudgetExhausted` Abort (R6-29, R9-27).

**Decision D-PLT-13:** CPU parallelism uses rayon work-stealing pools, one per `PoolLane`, and all result-affecting parallelism goes through Crucible's deterministic combinators. No second scheduler enters before phase 4, and chili returns only if it beats rayon by 1.3 times on BVH builds and sparse assembly. *Why:* rayon is the standard Rust work-stealing runtime and runs in browsers, and the combinators make results independent of thread count. *Rejected:* tokio for compute (futures starve under long kernels); a custom scheduler; two lanes (a drag waits behind agent work, R9-07). (revised in round 3)

### Deterministic parallel combinators

| Combinator | Contract | Order guarantee |
| --- | --- | --- |
| `det_for_each_chunk`, `det_map_collect` | Disjoint ranges; parallel map | Output in input order |
| `det_sum`, `det_reduce` | Pairwise reduction | Blocks of 2,048 elements; canonical lane i of 8 (f64) or 16 (f32) accumulates elements i, i + L, …; lanes reduce by a balanced tree over lane indices, and blocks by a balanced tree splitting n blocks at ⌈n/2⌉ |
| `det_scan` | Prefix scan | Fixed blocks and block-offset tree |
| `det_sort_by_key` | Stable sort | Floats only as `NonNan<f64>`; ties keep input order, never a name-derived id |
| `exact_sum` | Partition-independent sum | Binned accumulation (ReproBLAS), only where partitions vary |

Binned summation costs about 4 times a plain dot product (ReproBLAS), so node-local reductions use `det_sum` (R6-35), and Ingot's `sum` is `det_sum` (R9-37). Clippy forbids float reductions on rayon iterators, thread-count queries, `std` hash maps, `usize` in hashed data and address-dependent results.

### Memory

| Mechanism | Choice | Failure behavior |
| --- | --- | --- |
| Allocator | mimalloc v3 natively; Rust's wasm32 allocator in browsers | `try_reserve` failure: `ResourceExhausted` Abort |
| Budgets | `MemoryBudget` tree for CAS residency, GPU staging and Op scratch | Waits 2 s for eviction, then `ResourceExhausted { requested, available, fix }` |
| Scratch | A `bumpalo` arena per Op execution | Counts against the reservation |
| Mapped CAS objects | Read-only maps for objects of 1 MiB or more | Network file system: buffered reads |
| Out-of-core buffers | `ChunkedBuffer<T>`: 1 MiB CAS chunks, CLOCK eviction | Hash mismatch: `CasError::Corrupt`, recomputed |

**Decision D-PLT-14:** mimalloc v3 is the native global allocator. *Why:* it is MIT-licensed and runs on every Tier 1 OS and Wasm. Its project reports beating jemalloc and tcmalloc, in numbers from 2021. *Rejected:* system allocators (behavior differs per OS); jemalloc (the common Rust bindings exclude Windows). Phase 0 re-measures mimalloc, jemalloc and snmalloc, and the choice cannot affect results.

Windows refuses to delete mapped files, so CAS garbage collection defers them; a mapped file truncated elsewhere raises SIGBUS on Unix and is quarantined.

### GPU dispatch and resource usage

**Decision D-PLT-32:** An engine GPU dispatch lasts at most 4 ms while a window renders interactively, 16 ms while views idle and 100 ms headless. Display-only GPU work runs on the UI process's device from coefficient buffers in the mapped rings, and the engine creates its device lazily. *Why:* engine and renderer share one GPU, and wgpu offers external memory only on Vulkan, so shared buffers would cross host memory twice elsewhere (R6-16). *Rejected:* separate KLN, FLX and PLT limits; engine-side display evaluation.

A split dispatch covers more fixed tiles, never a different reduction topology. The runtime measures AGT's `Usage` fields per Evaluation, and reports fuel without pricing it (D-PLT-22). GPU seconds stay unattributed when the renderer shares the device (R6-29).

```rust
pub enum PoolLane { Interactive, Foreground, Background }
impl ComputePool {
    pub fn spawn<R: Send + 'static>(&self, lane: PoolLane, cx: OpCx, f: impl FnOnce(&OpCx) -> R + Send + 'static) -> ExecHandle<R>;
    pub fn boost(&self, exec: ExecId);
}
pub fn det_sum(cx: &OpCx, xs: &[f64]) -> Result<f64, Abort>;
pub fn exact_sum(xs: &[f64]) -> f64;
impl MemoryBudget { pub fn reserve(&self, bytes: u64, wait: Duration) -> Result<Reservation, Abort>; }
```

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Engine placement | Process, worker, Android threads or remote server | Engine crash: restart and replay | PLT-O-REL-2 | 0 |
| stdio MCP server sandbox | D-PLT-31 sandbox: pipes, granted folders, no network unless granted | Access outside the grant denied and logged | PLT-O-WASM-6 | 1 |
| Pools and lanes | Three pools by `PoolLane`; pausing at chunk boundaries | Start beyond 1 ms or 2 ms at p99 | PLT-O-RT-1 | 0 |
| Deterministic combinators | Data partitions, fixed trees, canonical lane order | Divergence fails the suite | PLT-O-DET-2 | 0 |
| Combinator lints | Five Clippy rules in operation crates | Lint failure blocks the merge | PLT-O-DET-5 | 0 |
| Cancellation and safe points | Chunk boundaries and fuel checks; safe points every 10 core-seconds | Abort, never cached | PLT-O-WASM-3 | 0 |
| Memory budgets and allocator | Reservation tree; mimalloc v3 | `ResourceExhausted` Abort with a fix | PLT-O-RT-2 | 0 |
| Out-of-core buffers | Identical results in and out of core | `CasError::Corrupt`, recomputed | PLT-O-DET-3 | 1 |
| GPU dispatch rule | 4, 16 and 100 ms; display work on the UI device | Overlong dispatch split; repeated resets disable GPU compute | PLT-O-GPU-4 | 1 |
| Resource usage | AGT's `Usage` fields; fuel never priced | Shared GPU: seconds unattributed | PLT-O-RT-3 | 1 |

## SIMD, GPU and linear algebra

### SIMD

`std::simd` remains nightly-only and Arm SVE experimental (rust-lang/rust#145052). `simd` detects the instruction set once and dispatches through a function table; `CRUCIBLE_ISA` forces a lower level for tests.

**Decision D-PLT-15:** Every reduction, scan or cross-lane operation in `Portable` code follows the 8-lane f64 or 16-lane f32 tree of `det_sum` on every instruction set. Element-wise code uses any native vector width. *Why:* only horizontal operations depend on lane count, and 512-bit virtual vectors force spills on x86-64-v2 and SIMD128 (R6-18). *Rejected:* 512-bit virtual vectors for all code (round 1); native-width reductions; scalar canonical code. (revised in round 2)

An intrinsic allow-list keeps approximate instructions such as `rcp14` and `FRECPE` out of canonical kernels. Dispatch uses pulp, and phase 0 evaluates fearless_simd 1.0, which promises "3 years of security updates", as its replacement (R6-30).

### GPU compute

WGSL lets compilers "fuse operations if the transformed expression is at least as accurate" (Candidate Recommendation Draft, 21 September 2026). Implementations may also "assume that overflow, infinities, and NaNs are not present" and flush subnormals. GPU bits therefore belong to one compiled pipeline, never the canonical class (R1-09).

**Decision D-PLT-16:** GPU kernels come from the kernel IR (FLX) through WGSL on wgpu, each registered in `gpu` beside its CPU path. GPU intervals serve only `Preview`, so `Interactive` uses take the filter role, and `F64Required` models never run on emulated `f64`. *Why:* contract 7.5 makes the kernel IR the one source, and CubeCL breaks between minor versions (R6-22). Fusion and flushing void interval bounds and double-float arithmetic (R7-32). *Rejected:* CubeCL (reconsidered at the phase 4 gate); WGSL plus CUDA (two sources); CUDA first (no Apple GPUs or browsers); per-pipeline interval audits (unprovable). (revised in round 3)

Each GPU path declares one role.

In **GPU filters, CPU decides** (`Certified`), the GPU narrows candidates under a certified bound. **`Interactive`** (`ClassExact`) results are cached only under their `Gpu` class.

In **GPU solves, CPU certifies**, a check rests on the pinned Field with a canonical residual and bound (D-FLX-17). Every role relies on four `gpu` mechanisms:

1. **Known-answer tests.** Each pipeline reproduces its class's recorded outputs at creation and after driver or OS updates. Failure falls back to the CPU.
2. **Integer exactness.** Exact results use integers, such as D-FLX-18's 32-bit-limb reductions, with no float atomics and compaction by prefix sums.
3. **Non-finite detection on the CPU.** Read-back exponent bits are inspected as integers, because in-shader NaN checks may be compiled away.
4. **Math functions.** Fixed-sequence approximations with documented ulp bounds, never vendor built-ins (D-FLX-11).

WGSL serves implicit preview from phase 1. Interactive elasticity joins in phase 1 only if the phase 0 measurement of `CpuIsa` kernels misses contract 13.3's simulation row (contract 7.5, R7-27).

Because wgpu exposes `SHADER_F64` only on Vulkan, `f64` GPU paths are Vulkan server paths from phase 3. Without a usable adapter or in safe mode, Kiln records `ran_on: Cpu` with the reason.

```rust
pub enum GpuRole { FilterCpuDecides, Interactive, CpuCertified }
pub struct GpuPath<I, O> {                     // no GPU-only capability exists
    pub id: &'static str, pub role: GpuRole,
    pub gpu: fn(&OpCx, &dyn GpuCompute, &I) -> Result<O, GpuError>,
    pub cpu: fn(&OpCx, &I) -> Result<O, Abort>,
}
pub enum RanOn { Gpu(GpuClass), Cpu { reason: CpuReason } }
```

### Canonical linear algebra

faer's dense kernels come from `gemm`, which sizes reduction blocks from L1 geometry read at run time and uses FMA. Version 0.24.4 documents "cpu feature detection at runtime" (R1-10, R6-21).

**Decision D-PLT-34:** `linalg`, owned by PLT with FLX, is the only linear algebra in `Portable` code. Its dense kernels (GEMM, LU, Cholesky, QR, SVD) use fixed blocks, the canonical order, no FMA and index-ordered pivot ties. FLX owns its sparse factorizations (D-FLX-36, R9-29). `linalg` and `simd`'s horizontal operations are versioned modules in source closures, so a bit-changing fix serves only new operation versions (contract 4, R9-06). Unmodified faer runs only in `CpuIsa` classes with cache detection pinned, and a deterministic mode offered to faer is optional. *Why:* cache-derived blocks make sums machine-dependent even within one ISA, and MEC's constraint solver and COV's calibration fits need `Portable` results (R2-15). *Rejected:* unmodified faer in the canonical class; a permanent fork of faer and `gemm` (built around FMA); depending on upstream acceptance (R7-35). (revised in round 3)

The dense target is within 2.5 times faer's `CpuIsa` time for n ≥ 1,000; sparse targets are FLX's.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| ISA dispatch | Detection once; forced levels for tests | Unsupported forced level: startup error | PLT-O-DET-1 | 0 |
| Canonical horizontal order | `det_sum` lane tree for every horizontal operation | Divergence fails the suite | PLT-O-DET-1 | 0 |
| Intrinsic allow-list | No approximate instructions in canonical kernels | CI rejects the intrinsic | PLT-O-DET-5 | 0 |
| GPU paths with CPU paths | Three roles; `RanOn` reported; intervals `Preview`-only; no emulated `f64` | No adapter or safe mode: CPU path, reason shown | PLT-O-GPU-3 | 1 |
| Known-answer tests | Per pipeline at creation and after driver or OS updates | CPU fallback and a proposed workaround | PLT-O-GPU-1 | 1 |
| Exact GPU primitives | Integer-limb reductions, prefix-sum compaction, no float atomics | Non-identity fails the oracle | PLT-O-GPU-3 | 1 |
| Non-finite detection | Integer inspection after readback | Typed numerical `Failure` naming the kernel | PLT-O-GPU-3 | 1 |
| `f64` GPU server paths | Vulkan `SHADER_F64`, certified on the CPU | Missing feature: CPU path | PLT-O-GPU-1 | 3 |
| Canonical dense linear algebra | Fixed blocking, no FMA, index-ordered pivot ties; versioned modules | Divergence fails the suite | PLT-O-LA-1 | 0 |
| Canonical sparse factorization | FLX's supernodal elimination and block-triangular LU, thread-count independent | As above | PLT-O-LA-1 | 1 (sequential), 2 (parallel) |
| faer in `CpuIsa` | Pinned cache detection; never in `Portable` code | Lint rejects it | PLT-O-DET-5 | 1 |
| Linear algebra speed | Dense within 2.5 times faer `CpuIsa` | Regression filed nightly | PLT-O-LA-2 | 1 |

## Numerical determinism

This section owns the mechanisms, classes, agreement and the suite; engine tabs keep at most 150 words of their own rules (R3-37).

### Sources of divergence and their controls

| Source | Evidence | Control |
| --- | --- | --- |
| Implicit contraction | Box2D found FMA "must be disabled for cross-platform determinism" | Rust never contracts (RFC 3514); linked C and C++ use `-ffp-contract=off`, checked in CI |
| Explicit FMA | `mul_add` runs in software on x86-64-v2 and wasm32 | Only in `detmath` and error-free transformations (D-PLT-18) |
| Platform math | Rust's `exp`, `sin` and `powf` vary "by platform, Rust version" | `detmath` only; Clippy forbids the std methods |
| Reduction order and width | Lane counts differ | Combinators; canonical horizontal order (D-PLT-15) |
| Approximate instructions | Reciprocal estimates differ by ISA | Intrinsic allow-list |
| Cache-dependent blocking | `gemm` sizes blocks from detected caches | `linalg` (D-PLT-34) |
| Floating-point environment | Foreign code may set flush-to-zero or rounding | MXCSR or FPCR checked at Op start and end; a change aborts and reruns the Op (R1-55) |
| NaN bit patterns | Payloads are nondeterministic in Rust and WebAssembly | Canonical NaN in the CAS; the determinizer for Wasm |
| Relaxed SIMD | `relaxed_madd` may round once or twice | Never used; rejected in Wasm |
| Hashes, addresses, threads | Hashes differ by pointer width; stealing reorders work | Combinator lints |
| Names in orderings | Label invariance (contract 7.1) | Ties keep input order; numbers come from geometry |
| GPU arithmetic | WGSL may reassociate, fuse and flush | Per-pipeline classes; known-answer tests; integer exactness |
| Changed shared code | A fix in `linalg` or `simd` alters released bits | Versioned modules in source closures (contract 4) |
| Toolchain upgrades | Code-generation bugs | The suite runs on every bump; a changed golden hash blocks it or bumps the epoch |

### The deterministic math library

`detmath` provides f64 and f32 elementary functions, scalar and batched, from exponentials to `lgamma`; `sqrt`, division and basic operations come from IEEE 754 hardware.

**Decision D-PLT-17:** `detmath` is correctly rounded wherever CORE-MATH is, and otherwise a fixed sequence of IEEE operations with a documented ulp bound. CORE-MATH's C sources (MIT) build behind its API on every target at milestone 1 of contract 13.2. Functions then move to Rust, hot ones first, and batched paths are compared against crmvec. Correct rounding is never traded for speed: a function that misses its speed target gets a target of 3 times glibc instead, filed without blocking. *Why:* a correctly rounded result is unique, so every path returns the same bits (R6-19). *Rejected:* platform libm; porting musl or FreeBSD libm (not correctly rounded); Box2D-style approximations (too inaccurate for CAD); faster functions with weaker rounding. (revised in round 3)

The C build sits in `bridges/core-math` behind safe functions (contract 12). Since glibc 2.43 integrates seven CORE-MATH functions, speed targets are Crucible's own.

On x86-64-v3, `exp` and `ln` stay within 1.5 times glibc and `pow`, `sin` and `cos` within 2 times. Under wasm32 they stay within 3 times native, and batched paths reach 2 times scalar.

**Decision D-PLT-18:** No implicit contraction exists anywhere, and explicit `mul_add` appears in canonical code only inside `detmath` and error-free transformations. `CpuIsa` variants with FMA serve `Preview` and `Interactive` from phase 0 for sum-factorized kernels at p ≥ 3, dense GEMM and LU, and NURBS evaluation. Other families need a measured penalty above 1.3 times, and memory-bound operators at p ≤ 2 never get one. `SignOff` recomputes canonically, and Kiln's cost model counts it. *Why:* x86-64-v2 and wasm32 lack FMA, while compute-bound kernels halve their peak without it (R6-17, R7-35, R12-23). *Rejected:* FMA in canonical kernels (software FMA in browsers); no FMA anywhere; FMA variants at `SignOff` (contract 7.3). (revised in round 3)

### Platform classes

**Decision D-PLT-19:** One canonical class, `CpuCanonical { epoch }`, spans every Tier 1 CPU target at any thread count and ISA level. No CPU class names an OS. A GPU class is one pipeline on one verified device class: back end, device family, driver build, shader-compiler build and pipeline hash. *Why:* with no OS-dependent arithmetic left, every target can share cached results, while each WGSL compiler fuses differently (R1-09, R1-44). *Rejected:* one class per OS and architecture; GPU classes keyed by vendor alone. (revised in round 2)

```rust
pub enum PlatformClass {                          // in base; owned by PLT
    CpuCanonical { epoch: u16 },
    CpuIsa { isa: IsaLevel, epoch: u16 },          // X86_64V2..V4, Arm64Neon, Wasm32Simd128
    Gpu(GpuClass),                                 // a registry entry: device class plus pipeline
    Unverified { fingerprint: [u8; 16] },          // unlisted devices and external hosts
}
```

The verified-class registry is a signed data file built from GPU-lab runs. An epoch bump needs the founder's approval and an LTS boundary unless it fixes wrong results. `cli` reproduces an old release with its epoch's archived engine.

**Decision D-PLT-20:** `CpuIsa`, `Gpu` and `Unverified` results never substitute for canonical ones, which a check, release or Proposal recomputes when it needs them. The one exception is contract 7.3's: a check may rest on a pinned non-canonical Field when its residual and error bound are computed canonically. *Why:* substitution would make a release depend on the machine that computed it first. *Rejected:* any class within tolerance; no exception (forfeits cheap CPU certification). (revised in round 2)

Invalid numerics are typed `Failure`s. Where NaN is legitimate, the CAS writes the canonical quiet NaN.

### Cross-class agreement

**Decision D-PLT-35:** Classes A and B agree on a checked quantity q within a tolerance set by what they shared. With the same resolved `SolvePlan`, adaptive marks and steps, shared discretization error cancels. The tolerance is then both classes' algebraic and floating-point parts plus a floor scaled by the Field norm. When marks or steps differ, the full `ErrorBudget` totals apply and the diverging marks are reported as a finding of their own. A failed `Guaranteed` or algebraic comparison opens an incident at once, and an `Estimated` one after two consecutive nightly failures. Bifurcating and chaotic problems compare branch-invariant quantities or statistics. *Why:* full budgets let a class drift by the whole discretization error unseen (R7-12). A bound calibrated at α = 0.01 is exceeded by design, so single misses would open incidents nightly. *Rejected:* |q_A − q_B| ≤ E_A + E_B everywhere (round 2); residual rules and ulp tolerances (meaningless near zero, R1-12, R1-13). (revised in round 3)

FLX applies the same rule (FLX-O-ERR-10); B-rep Bodies must first match in topology. The harness runs nightly over every `CpuIsa` and verified `GpuClass`.

### The determinism suite

The suite runs on every merge on contract 7.3's representative set, and nightly on every other Tier 1 target and browser engine.

1. **Corpus.** Golden products, ANV and FLX corpora, Wasm components, and 10,000 random operation graphs a night.
2. **Canonical identity.** Every hash matches on every target and executor.
3. **Schedule independence.** 1 to 64 threads with injected stealing delays and allocator randomization.
4. **Out-of-core equivalence.** A 64 MiB budget forces chunks to disk.
5. **Linear algebra.** Factorizations under two cache-size settings.
6. **Floating-point environment.** A planted flush-to-zero library forces an Abort and rerun.
7. **Native and GPU classes.** Repeated runs within a class are identical, and the agreement harness passes.
8. **`detmath`.** Univariate f32 functions exhaustively against MPFR, others on hard cases and 10⁹ random inputs a night.

A failure names the first diverging Op, both targets, the inputs and the first differing value. A nightly divergence bisects automatically, opens a severity-1 incident and blocks beta promotion, not the merge queue (R6-28).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Mechanism table | One control per divergence source, cited by every engine tab | A newly found source adds a row | PLT-O-DET-1 | 0 |
| `detmath` C build | CORE-MATH C on every target at milestone 1 | Missing function fails the build | PLT-O-DET-4 | 0 |
| `detmath` Rust ports | Hot functions first; batched paths | A port differing from the C build is rejected | PLT-O-DET-4 | 0 to 1 |
| `detmath` speed | Per-function targets; a miss relaxes to 3 times glibc | Regression filed, never blocking | PLT-O-DET-8 | 1 |
| FMA variants | Named families first; others above a 1.3 times penalty; never at `SignOff` | Divergence beyond D-PLT-35 disables the variant | PLT-O-DET-6 | 0 (named families), 1 (others) |
| Floating-point environment guard | Checked at Op start and end | Abort and rerun, culprit logged | PLT-O-DET-7 | 0 |
| Platform classes | Four variants in `base`; signed GPU registry | Unlisted device: `Unverified`, local cache only | PLT-O-DET-1 | 0 |
| Epochs and archived engines | Approved bumps; archived builds reproduce old releases | Missing archive: agreement-rule comparison, reported | PLT-O-BLD-3 | 2 |
| No substitution | Canonical recomputation with contract 7.3's exception | Uncertified non-canonical input: check is `Undecided` | PLT-O-DET-6 | 1 |
| NaN canonicalization | Canonical quiet NaN in the CAS | Lint failure blocks the merge | PLT-O-DET-5 | 0 |
| Cross-class agreement | Shared-plan tolerance from algebraic and floating-point parts; full budgets when marks differ | Incident at once, or after two nightly `Estimated` misses | PLT-O-DET-6 | 1 |
| Determinism suite | Representative set per merge, the rest nightly, automatic bisection | Nightly divergence: severity-1 incident, beta blocked | PLT-O-DET-9 | 0 |

## Wasm component runtime

Wasm components give bit-identical results in Wasmtime, browser engines and JavaScriptCore, because the one determinizer of contract 7.4 fixes their semantics in the bytecode.

WASI 0.3.0 shipped on 11 June 2026. In Wasmtime, "Each release that is a multiple of 12 is considered an LTS release and is supported for 24 months". Its 2026 advisories include GHSA-394w-hwhg-8vgm and GHSA-6wgr-89rj-399p.

**Decision D-PLT-21:** Crucible embeds Wasmtime pinned to LTS releases (48, then 60) and applies its security releases within 7 days on every supported line. It moves between LTS releases only after the suite passes. Crucible's own criteria, not upstream tier labels, qualify each target (Targets). *Why:* the 24-month window matches Crucible's LTS channel (R5-09), and upstream labels are outside Crucible's control (R12-21). *Rejected:* monthly releases (each recompiles every cached Wasm component); Wasmer (its runtime documentation names WASIX, not the Component Model). (revised in round 3)

### The determinizer

`wasm-host` holds the determinizer, `determinize@N`, which runs at publish and at local builds. Hosts execute only determinized binaries, whose hash enters the `OpKey`.

| Step | Problem it removes |
| --- | --- |
| Validation; rejection of relaxed SIMD, shared memories, atomics and forbidden imports | Results that differ between calls or threads |
| Fuel metering per basic block; with shared memory the check also reads a cancellation word | Engines meter differently; cancellation must land at the same points everywhere (R3-21) |
| A logical stack-depth limit below the smallest real stack of any engine | Engine-dependent stack overflow |
| NaN canonicalization only where bits become observable: float stores, `reinterpret`, the sign operand of `copysign`, host-call values, and v128 float results reaching bitwise, integer-lane, shuffle, store or extract-to-integer instructions | Nondeterministic NaN payloads, which arithmetic, comparisons and conversions never expose (R6-20) |
| Growth guards: a host-caused `memory.grow` or `table.grow` failure below the declared maximum becomes a `ResourceExhausted` Abort | `memory.grow` may "non-deterministically succeed or fail" (R9-42) |

Ingot code generator output is verified, not rewritten (R3-51). It needs no forbidden imports, fuel decrements dominating every back-edge, non-finite checks before observable float uses and depth counters.

**Decision D-PLT-22:** The determinizer enforces fuel, cancellation, stack limits, NaN canonicalization and growth guards in bytecode, identically on every engine. Wasmtime's epochs are never used. Fuel is a determinism and termination limit only, and AGT's `Usage` prices core-seconds, GPU-seconds and memory, never fuel. *Why:* browsers can neither meter fuel nor canonicalize NaNs, Wasmtime's fuel costs change between releases, and fuel counts instructions, not cost. *Rejected:* engine-side switches (native only); epochs (nondeterministic); canonicalizing every NaN-producing instruction; fuel-priced usage. (revised in round 3)

PLT publishes the one overhead table ECO cites (contract 7.4); all figures are targets. Determinizer rows compare with undeterminized binaries in Wasmtime, and isolation rows run on the reference laptop.

| Row | Target | Oracle |
| --- | --- | --- |
| Scalar-float Wasm components | At most 10% | PLT-O-WASM-2 |
| SIMD-float Wasm components | At most 25% | PLT-O-WASM-2 |
| Fuel and stack metering | At most 10% | PLT-O-WASM-2 |
| `crucible:ops` round trip from a native sandbox worker | At most 20 µs, plus 0.2 ms per MiB of arguments | PLT-O-WASM-7 |
| `crucible:ops` round trip across browser agent clusters | At most 250 µs, plus 1 ms per MiB | PLT-O-WASM-7 |
| std's Wasm components in the third-party configuration | Within 15% of in-process time, every release | PLT-O-WASM-7 |

Determinized Wasm components target 1.6 times native Rust in Wasmtime and 2.5 times in browsers for scalar and memory-bound code. Compute-bound SIMD kernels target 2.5 times AVX2 code, since SIMD128 is half as wide (R6-33, R7-38); FLX sets user-form ratios.

### Executors

| Target | Executor | Notes |
| --- | --- | --- |
| Native Tier 1 | Wasmtime LTS, Cranelift at `OptLevel::Speed` | Precompiled at install, keyed by binary, Wasmtime version, `Config`, target and CPU features; only local or Crucible-signed artifacts load |
| Browsers and iPadOS | One first-party runtime in the browser's engine | D-PLT-36; iPadOS through the web build |
| Android | Wasmtime with Cranelift | No Android API imports |
| No Cranelift code generation, or unqualified Windows ARM64 | Pulley | About ten times slower |

Until the Ingot code generator ships, the reference interpreter is the only Ingot executor. Wasmtime runs with relaxed SIMD, threads and memory64 off, and its limiter reserves budget as memory grows (R3-33).

**Decision D-PLT-36:** Browsers run every Wasm component through one first-party runtime, which instantiates determinized core modules from ECO's description. No JavaScript ships per Wasm component. It implements the Component Model's stackless async ABI, "selected by providing a `callback` function". A `crucible:ops` call returns to the event loop and resumes when the answer arrives. *Why:* per-component glue would hold the engine worker's OPFS and credentials (R5-12, R6-37). A synchronous import cannot wait on its own blocked event loop (R12-01). *Rejected:* jco glue; transpiling in the engine worker; JS Promise Integration (needless stack switching). (revised in round 3)

### Isolation of third-party Wasm components

**Decision D-PLT-31:** Only first-party Wasm components (std, `crucible::` and the first-party translators, hermetically built) run in the engine process. On desktops each third-party Wasm component runs in an OS-sandboxed worker (AppContainer, App Sandbox, or seccomp with Landlock) with no repository, token, key or network. Servers run such workers per tenant and label, and trusted builders use microVMs (contract 7.8). Workers read bulk data through read-only CAS maps, so a call costs one round trip plus the copy of its arguments. *Why:* the engine holds every open repository and token, and Wasmtime's 2026 advisories include isolation bugs (R5-12). An OS-process sandbox is no trust boundary for attestation (R11-03). *Rejected:* in-process execution for verified publishers; process sandboxes on trusted builders. (revised in round 3)

**Decision D-PLT-42:** Browsers evaluate third-party evaluation-world Wasm components remotely until the asynchronous bridge passes PLT-O-WASM-1 and PLT-O-WASM-7 there; a local sandbox joins in phase 2. It is an `<iframe sandbox="allow-scripts">` from a sandbox site on another registrable domain, so its opaque origin holds no OPFS, cookies or keys. Its fixed, content-hashed document and worker scripts carry `Content-Security-Policy: default-src 'none'; script-src 'self' 'wasm-unsafe-eval'`, which blocks every connection, plus the COEP and CORP headers the isolated page needs. A `MessagePort` pair links the sandbox worker to the engine worker, and data cross as transferred `ArrayBuffer`s. *Why:* an opaque origin can still send data, since CORS limits only reading responses (R11-11). Parity allows remote evaluation, and phase 1's third-party components are a user's own (R12-01). *Rejected:* a worker without an iframe (workers have no `sandbox` attribute); memory shared with the engine (another agent cluster); a phase 1 sandbox.

**Decision D-PLT-43:** Every process running untrusted code starts with no network: Wasm workers, translator hosts, External Op hosts, tool processes and stdio MCP servers. Windows uses AppContainers without network capabilities, macOS the App Sandbox without network entitlements, Linux empty network namespaces, and servers microVMs without a network device. Endpoints that a manifest names and an administrator grants (contract 7.8) go through a host relay that connects only to the addresses the grant pins. A host with any grant receives only inputs labelled at most `internal` with empty `controls`, unless a two-person grant names it (KLN). *Why:* untrusted native code with labelled inputs and a socket bypasses `release_data` (R11-09), and Landlock filters by port, not address. *Rejected:* egress rules by DNS name; per-OS firewall rules; no egress at all (licence servers).

### Worlds, calls and failures

ECO defines the worlds and PLT enforces them. Tool and connector worlds use WASI 0.3, and any import a world does not grant fails at install with `ForbiddenImport { import, fix }`.

Evaluation worlds import no WASI, and their `crucible:ops` imports are callback-ABI async functions. Results never depend on completion order, and host time never counts as fuel. A batched call carries many operation calls in one round trip and returns results in call order.

Limit outcomes come from KLN's one catalog in `base` (R9-27):

| Event | Outcome | Cached |
| --- | --- | --- |
| Trap in Wasm component code | `Failure`: `Trap { code, function, fix }` | Yes |
| The call's own fuel limit | `Failure`: `FuelExhausted { used, limit }` | Yes |
| Logical stack limit | `Failure`: `StackExhausted { limit }` | Yes |
| `memory.grow` beyond the declared maximum | Returns −1; the Wasm component decides | As its outcome |
| Host memory unavailable below the maximum | Abort: `ResourceExhausted` | Never |
| Evaluation fuel or budget exhausted | Abort: `FuelCeilingExceeded` or `BudgetExhausted` | Never |
| Cancellation; sandbox worker lost | Abort | Never |

Data beyond 4 GiB moves through chunked buffers, and data parallelism through `crucible:host/parallel`.

### WIT interfaces

PLT specifies two interfaces that ECO's package table indexes (R9-08, R9-26). Both stay at `@0.1.0` until contract 13.1's freeze; the rest of `crucible:tool` is ECO's.

```wit
package crucible:host@0.1.0;
interface parallel {
  variant chunk-error { failed(u32), fuel-exhausted }
  map-chunks: async func(count: u32, input: list<u8>) -> result<list<list<u8>>, chunk-error>;
}
```

```wit
package crucible:tool@0.1.0;
interface process {
  record command { program: string, args: list<string>, dirs: list<string> }
  record exit-status { code: s32, stdout: list<u8>, stderr: list<u8> }
  enum process-error { not-declared, sandbox-unavailable, budget-exceeded }
  run: async func(cmd: command, stdin: list<u8>) -> result<exit-status, process-error>;
}
```

`map-chunks` calls the exported `chunk` once per index on fresh instances, on any thread count. It returns outputs in index order, or the lowest failing index.

Each chunk runs with the caller's remaining fuel as its limit and the sum is charged afterwards, so `FuelExhausted` never depends on thread count. `run` exists only in tool worlds and runs programs the manifest declares by digest, with granted directories only.

```rust
pub trait WasmComponentEngine: Send + Sync {   // Wasmtime, sandbox worker, browser runtime
    fn install(&self, determinized: &[u8], world: &WorldSpec) -> Result<InstalledWasmComponent, WasmComponentError>;
    fn instantiate(&self, c: &InstalledWasmComponent, limits: CallLimits) -> Result<Box<dyn WasmInstance>, WasmComponentError>;
}
pub struct CallLimits { pub fuel: u64, pub stack_frames: u32, pub max_memory_bytes: u64 }
```

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Determinizer | Validation, fuel, stack limit, observable-NaN canonicalization, growth guards | `InvalidComponent { reason }` | PLT-O-WASM-1 | 0 |
| Observable-NaN canonicalization | Only at the listed observation points | Divergence fails the oracle | PLT-O-WASM-4 | 0 |
| Verification of Ingot modules | Four structural checks | Error naming the function | PLT-O-WASM-5 | 2 |
| Overhead table | Determinizer and isolation rows | Regression filed nightly | PLT-O-WASM-2 | 0 |
| Isolation overhead | 20 µs and 250 µs round trips; batched calls; std within 15% | std over 15% blocks the release | PLT-O-WASM-7 | 1 (native), 2 (browsers) |
| Wasmtime LTS embedding | Pinned LTS; security releases within 7 days | An unpatched advisory blocks the release | PLT-O-WASM-1 | 0 |
| Ahead-of-time compilation | At install; trusted artifacts only | Unknown artifact: recompiled locally | PLT-O-WASM-1 | 0 |
| Browser Wasm component runtime | One first-party runtime; callback async ABI | Missing description: fetched from the toolchain or team server | PLT-O-WASM-1 | 1 |
| Third-party isolation | OS sandboxes natively; microVMs on trusted builders; remote evaluation in browsers | Lost worker: Abort for its calls | PLT-O-WASM-6 | 1 |
| Browser sandbox | Sandbox site, CSP, `MessagePort` bridge | Bridge unavailable: remote evaluation | PLT-O-WASM-6 | 2 |
| Default-deny egress | No network; granted endpoints at pinned addresses | Unlisted connection refused and logged | PLT-O-WASM-6 | 1 |
| Cancellation | Fuel checks with shared memory, Op boundaries without | Abort, never cached | PLT-O-WASM-3 | 0 |
| Failure taxonomy | KLN's catalog; `Failure`s cached, Aborts never | A cached Abort fails the oracle | PLT-O-WASM-3 | 0 |
| Worlds | Imports checked at install; async `crucible:ops` with a batched form | `ForbiddenImport { import, fix }` | PLT-O-WASM-6 | 0 |
| WIT interfaces | `crucible:host/parallel`; `crucible:tool/process` | Published WIT differs: release blocked | PLT-O-WASM-8 | 1 (`parallel`), 2 (`process`) |

## Packaging, distribution and updates

Here "app package" means an OS installation format such as MSIX or deb, unrelated to registry packages.

| Target | Format | Signing | Phase |
| --- | --- | --- | --- |
| Windows | MSIX per architecture through the PackageManager API; Intune, Configuration Manager and the Enterprise Modern App Management CSP | Authenticode, HSM-held key | 1; an MSI wrapper for MSI-only tools 2 |
| macOS | Notarized DMG; `.pkg` for MDM | Developer ID, hardened runtime, stapled ticket | 1; `.pkg` 2 |
| Linux | deb and rpm in apt and dnf repositories; Flatpak and AppImage | Signed metadata expiring within 7 days (R5-12) | 1; Flatpak and AppImage 2 |
| Browser | Content-hashed assets and a service worker | Manifest in TUF; transparency log from phase 2 | 1 |
| Machine gateway (`apps/machine-gateway`, MFG) | MSIX on Windows 11 x86-64; deb and rpm on Linux x86-64 and ARM64 | As its OS; device key in a TPM 2.0 | 2 |
| iPadOS, Android | App Store, Google Play, managed APKs | Platform signing | 3 |
| Servers and `cli` | OCI images and a Helm chart; `cli` in every desktop package and as signed archives | Image signatures and SLSA provenance | 1 |

The gateway connects outbound only, and readings from one without a TPM carry `data_untrusted` (MFG, R10-28). The macOS bundle declares `com.apple.security.cs.allow-jit` for memory created "using the `MAP_JIT` flag", which Wasmtime needs (R6-40).

**Decision D-PLT-23:** Windows ships as MSIX. *Why:* MSIX gives clean uninstall, package identity for notifications and background tasks, 64 KB block-level differential updates and Intune support. *Rejected:* MSI (no package identity or block updates); a custom installer.

**Decision D-PLT-24:** Linux ships deb and rpm repositories in phase 1 and Flatpak and AppImage in phase 2, from one binary per architecture. *Why:* deb and rpm serve managed fleets and suffice for the wedge; Flatpak and AppImage serve sandboxed and unprivileged installs. *Rejected:* Snap only; per-distribution builds; all four in phase 1 (R6-02). (revised in round 2)

### Signed updates

**Decision D-PLT-25:** Every self-updating channel verifies updates with The Update Framework (specification 1.0.37), with offline root and targets keys. OS mechanisms carry the bytes where they exist. Phase 1 installs full signed packages, and deltas (MSIX block maps, Zucchini patches for PE and ELF, generic patches for Mach-O) arrive in phase 2. *Why:* TUF defeats freeze, rollback, mix-and-match, fast-forward and endless-data attacks and key compromise (R6-02). *Rejected:* a signed manifest alone; Velopack (no documented rollback defense); Sparkle (macOS only). (revised in round 2)

| TUF role | Signs | Keys and threshold | Expiry |
| --- | --- | --- | --- |
| Root | Every other role's keys | 3 of 5 offline hardware tokens in separate locations, held by the founder and outside custodians | 1 year |
| Targets | Hashes and lengths per artifact, delegated per channel | 2 of 3 HSM keys | 3 months |
| Snapshot | Versions of all targets metadata | 1 online key | 7 days |
| Timestamp | The snapshot's hash | 1 online key | 1 day |

The updater checks timestamp metadata at startup and every 4 hours, rejects expired metadata and lower versions, and installs at the next start. A new version self-tests within 60 s and rolls back on failure or two crashes in 10 minutes. Stable releases roll out to 1%, 10%, 50% and 100% over at least 4 days and halt if crash rates rise 20% (target).

**Decision D-PLT-37:** Every signature PLT produces or verifies (artifacts, TUF metadata, web manifests, provenance) is a detached record carrying an algorithm id. From phase 2, TUF root and targets metadata and provenance are dual-signed with a classical signature plus ML-DSA-87 (FIPS 204). LMS signs only the steward's software releases, under contract 7.8's rules. Long-retention records are re-timestamped before an algorithm retires. *Why:* releases must verify for decades, and a stateful scheme breaks if an HSM cluster replicates its one-time keys (R11-25). *Rejected:* classical signatures alone; switching algorithms at once (old verifiers break); LMS for metadata or provenance (high-volume signing from a finite tree). (revised in round 3)

### Air-gapped installs and enterprise policy

From phase 3, with KLN's bundles (R9-45), an offline bundle is one signed archive per release. It holds installers, std packages, the GPU registry, TUF metadata, provenance and archived engines (D-PLT-47). `crucible mirror import` publishes it on a mirror whose TUF root delegates to the vendor's keys, and `crucible install --offline` verifies against the embedded root.

From phase 2 one policy schema applies on every OS through ADMX, profiles, `/etc/crucible/policy.json` and MDM. It covers updates, telemetry, crash uploads, egress, clipboard, registries and proxies.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Phase 1 app packages | MSIX, notarized DMG, deb and rpm, OCI images, web assets | An unsigned artifact blocks the release | PLT-O-PKG-2 | 1 |
| Further formats | MSI wrapper, `.pkg`, Flatpak, AppImage | As above | PLT-O-PKG-2 | 2 |
| Machine gateway packages | `apps/machine-gateway` for Windows 11 x86-64 and Linux; TPM-held key | No TPM: readings `data_untrusted` | PLT-O-PKG-2 | 2 |
| TUF-verified updates | Full signed packages; expiry, rollback and freeze checks | The installed version stays, with a report | PLT-O-PKG-1 | 1 |
| Delta updates | Block maps, Zucchini and generic patches | Failed patch hash: full file | PLT-O-PKG-1 | 2 |
| Self-test and rollback | 60 s self-test; rollback on failure or two early crashes | Rollback and a filed report | PLT-O-PKG-1 | 1 |
| Repository freshness | apt and dnf metadata expiring within 7 days | Expired metadata refused | PLT-O-PKG-1 | 1 |
| Signature agility | Detached records with algorithm ids; dual signatures; LMS only for software releases | Unknown algorithm id fails closed | PLT-O-PKG-3 | 2 |
| Air-gapped installs | Offline bundle, mirror import, offline install | Bad bundle signature: import refused | PLT-O-PKG-4 | 3 |
| Enterprise policy | One schema on every OS | Invalid value: default kept, error shown | PLT-O-PKG-4 | 2 |
| macOS JIT entitlement | `allow-jit` for Wasmtime | Wasm components refused with the reason | PLT-O-PKG-2 | 1 |

## Reliability

No crash, driver fault or power loss costs a user more than one second of edits, and every failure arrives as a symbolicated, deduplicated report.

### Crash handling

| Mechanism | Choice | Failure behavior |
| --- | --- | --- |
| Native capture | A crash monitor started first; `crash-handler` and `minidumper` write every process's dumps from outside | Monitor gone: minimal in-process report |
| Windows ARM64 | `crash-handler` lacks aarch64 Windows, so an unhandled-exception filter signals the monitor, which calls `MiniDumpWriteDump`; offered upstream in phase 0 | Same minidump format |
| Mobile | `crash-handler` on Android; on iPadOS the shell reports WebKit content-process terminations and restarts the engine | Lower coverage only |
| Panics | Caught at the Op boundary as worker loss: an uncached Abort; the operation is poisoned after 2 panics | "Engine restarted" and replay |
| Processing | rust-minidump with PDB, dSYM and DWARF symbols, kept 2 years, or the support period for LTS | Missing symbols block promotion |
| Hang detection | 2 s without a UI event; 10 s without an engine cancellation check | Reported with a `hang:` signature |

Microsoft advises calling `MiniDumpWriteDump` "from a separate process if at all possible". Windows Error Reporting's local dumps stay an opt-in, since enabling them "requires administrator privileges" (R12-29).

Minidumps hold stacks but never heap memory, so uploads default to `ask`, show their contents, scrub paths and are deleted after 90 days. Promotion needs 99.8% crash-free sessions over the beta's last 7 days (target).

### Autosave and recovery

PLT supplies the journal beneath `repo`'s Changes. Its CRC-checked records are flushed with `WriteDurability::Data` at most every 1 s and on save, close and power changes. A process crash loses nothing appended, and a power failure at most 1 s.

After an unclean exit the engine truncates at the first bad record and replays the rest within 2 s (target). CAS writes go through a temporary file, flush, rename and directory flush, and a torn object fails its hash check.

### Device loss, workarounds and safe mode

Device loss aborts in-flight GPU work and recreates the device after 100 ms, 1 s and 5 s. After 3 losses in 10 minutes, GPU compute is off.

`gpu-workarounds.json` is a signed, TUF-updated file matched before the first device is created. Its entries name OS, back end, PCI ids, driver ranges, actions from a closed list and a reproducer, and none changes a canonical result.

Safe mode starts with `--safe-mode`, Shift at launch or after 2 startup crashes. It turns off GPU compute, the translator host and Wasm components the lockfile does not require, and requests UIX's most conservative renderer. `platform` places each machine in a band from its `HardwareProfile`, and the Performance panel lists every degradation with its cause.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Crash capture, desktop | Out-of-process minidumps, server symbolication | Monitor gone: minimal report | PLT-O-REL-1 | 0 |
| Crash capture, Windows ARM64 and mobile | Exception filter and monitor; WebKit terminations on iPadOS | Reduced coverage, reported | PLT-O-REL-1 | 0 (Windows ARM64), 3 (mobile) |
| Panics | Abort at the Op boundary with a crash id | Panic outside an Op restarts the engine | PLT-O-REL-1 | 0 |
| Hang detection | 2 s UI and 10 s engine watchdogs | Reported as `hang:` | PLT-O-REL-1 | 1 |
| Journal and recovery | 1 s flush bound; truncate, replay, report | Bad record: truncated there | PLT-O-REL-2 | 1 |
| Crash-consistent CAS writes | Temporary file, flush, rename | Torn object recomputed | PLT-O-REL-2 | 0 |
| GPU device loss | Backoff recreation, rerun, disable after 3 losses | Abort for in-flight work; CPU path | PLT-O-GPU-2 | 1 |
| Workaround database | Signed, TUF-updated, one reproducer per entry | Unknown driver: known-answer tests still apply | PLT-O-GPU-1 | 1 |
| Safe mode | GPU, translator host and optional Wasm components off | Never changes a canonical result | PLT-O-REL-3 | 1 |
| Graceful degradation | Degradations listed in the Performance panel | Each names its cause | PLT-O-REL-3 | 1 |

## Telemetry and label-aware egress

Label enforcement in `api` stops at the API boundary, yet labelled content can leave through notifications, crash dumps, backups, synced folders and clipboard history (R5-16).

**Decision D-PLT-38:** Content labelled above `internal` or with non-empty `controls` follows one egress rule outside `api`. Notifications and emails carry ids and generic text, and crash reports only the signature and modules. Reproduction bundles go only to the organization's server. The CAS, journal and caches refuse cloud-synced folders and OS backup, and copies skip clipboard history and cloud clipboards, or `clipboard.labelled = deny` forbids them. *Why:* ITAR's end-to-end rule requires that "The means of decryption are not provided to any third party" (22 CFR 120.54). *Rejected:* label checks at `api` only; no notifications or crash reports for anyone. (revised in round 3)

**Decision D-PLT-39:** One telemetry pipeline, owned by PLT, serves UIX and PLT with one public schema. It is opt-in, rotates an install id never joined to accounts every 90 days, and drops aggregates under 50 installs. Raw data lasts 90 days and aggregates 13 months, EU data stays in the EU, and the privacy notice names the steward as controller. *Why:* people "may be associated with online identifiers provided by their devices" (GDPR recital 30), and two pipelines differed in payload and retention (R5-29). *Rejected:* separate pipelines; compile-time exclusion (breaks the single binary; policy replaces it).

Telemetry collects timings, memory, band, ISA, `GpuClass`, OS, version, command ids and error codes, never design content, values, names, source or account ids.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Notification and email content | Ids and generic text for labelled content | Labelled payload: send refused and logged | PLT-O-PRIV-1 | 1 |
| Crash and reproduction egress | Signature and module list; bundles to the organization | No organization server: bundle kept local | PLT-O-PRIV-1 | 1 |
| Storage placement | CAS, journal and caches outside synced folders and backups | `StorageError::CloudSynced { path, fix }` | PLT-O-PRIV-1 | 1 |
| Clipboard exclusion | History and cloud exclusion; policy can deny | Denied copy explains the policy | PLT-O-PRIV-1 | 1 |
| Telemetry pipeline | One schema; opt-in; rotating id; thresholds; retention; EU region | Schema violation: upload rejected | PLT-O-PRIV-2 | 2 |
| Egress allowlist | Policy-listed hosts only | Blocked host logged locally | PLT-O-PRIV-2 | 2 |

## Build, release and CI

`rust-toolchain.toml` pins one stable Rust version, moved at most every 6 weeks after the suite passes, and the nightly pin serves only D-PLT-10. Dependencies are locked and vendored per release. cargo-deny checks licences against contract 7.7's list, advisories, bans and sources (R11-34).

**Decision D-PLT-40:** Every crate in the engine, UI, server and `wasm-host` closures carries a cargo-vet `safe-to-deploy` audit. The verifier role writes it, or it is imported from audit sets the founder approves. CI fails on an unaudited crate or version delta, and a new version waits 14 days unless it fixes an advisory. Build scripts and procedural macros always run in the hermetic builder's sandbox, with no network and a read-only source tree. `deps/approved.toml` records each core dependency's risk class, cadence and fork plan. *Why:* the engine links hundreds of crates while holding every key (R11-24). `safe-to-deploy` means a crate "will not introduce a serious security vulnerability to production software exposed to untrusted input". *Rejected:* licence and advisory checks alone; avoiding young crates. (revised in round 3)

**Decision D-PLT-26:** Cargo stays the only build system, accelerated by sccache with a shared remote cache. *Why:* the workspace is one Cargo workspace, and sccache supports Rust with S3, GCS, Azure, Redis, GitHub Actions and WebDAV back ends. *Rejected:* Bazel or Buck2 remote execution (a second build description for every crate); no shared cache.

Targets: a no-op `cargo check` under 2 s, an `anvil-ops` edit-and-test loop under 20 s and a warm-cache CI build under 6 minutes.

**Decision D-PLT-46:** Two independent builders produce byte-identical unsigned artifacts, for Linux and wasm32 from phase 1 and other targets from phase 2. Where PE or Mach-O identity stays out of reach after normalization, SLSA provenance from both builders verifies the release. *Why:* reproducible builds give "an independently-verifiable path from source to binary code", as Debian, Arch Linux and NixOS show. *Rejected:* provenance alone everywhere; blocking releases on PE and Mach-O identity.

### CI stages and capacity

| Stage | Runs | Time budget |
| --- | --- | --- |
| Pull request | Format, Clippy with determinism lints, layering, cargo-vet, Linux unit tests, wasm32 build, determinism subset | 15 minutes (target) |
| Merge queue | Every Tier 1 target; the suite on the representative set; golden hashes of pinned `Current` and `Deprecated` versions; golden checks at `Interactive`; instruction counts; GPU paths in the renderer image | 45 minutes (target) |
| Nightly | The suite elsewhere; `SignOff` simulations; GPU lab; wall-time benchmarks; random graphs; fuzzing; weekly Tier 3 and retired versions in shards | 6 hours |
| Release | Installers; install, upgrade and uninstall; updates from the last 3 releases; Tier 2 device farm; reproducibility; bills of materials and provenance | 12 hours |

The pinned renderer image fixes the lavapipe build and CPU settings, because llvmpipe "uses LLVM to do runtime code generation" for the host CPU (R6-26). The GPU lab is rented hardware that agents drive remotely, with fixed drivers and canary upgrades. It holds NVIDIA, AMD and Intel GPUs, Apple silicon, Snapdragon X, a Linux ARM64 desktop (R6-31) and Adreno, Mali and Xclipse tablets.

CI capacity enters each phase budget the founder approves (contract 13.2), estimated ±50% (R6-28). Phase 0 needs about 1,000 cloud vCPUs, 8 macOS and 8 ARM64 runners and 12 lab machines. Phase 1 needs about 3,000, 24, 24 and 24, and phase 2 about 5,000, 40, 40 and 36.

### Release channels and versions

Versions are calendar-based (`2027.3.0`). Nightly builds run daily and beta branches every 6 weeks, and an LTS line keeps its epoch, Wasmtime line and determinizer version for life.

**Decision D-PLT-27:** Releases follow a 6-week train, and security fixes also ship as patch releases (`x.y.z`). Each LTS is cut within 12 weeks of a Wasmtime LTS and supported for 24 months. Wasmtime fixes are backported for the remaining gap of at most 3 months. Every release states a five-year CRA support period, met by free upgrades while the minimum OS and hardware stay fixed. That floor rises only at an LTS cut, and the last release under the old floor becomes a five-year security-only line. One LTS line every two years gets 10 years of regulated support, on its retired Wasmtime in a sandbox unless a customer funds backports. *Why:* regulated programs qualify one version for a decade (R5-20). The CRA requires "at least five years" (R11-28), and Wasmtime supports each LTS "for 24 months" (R12-30). *Rejected:* no LTS; LTS lines longer than Wasmtime's; floor rises on any train. (revised in round 3)

**Decision D-PLT-47:** Archived Wasm engine builds stay runnable for the longest supported line plus 2 years, or 12 for regulated lines. The TUF targets role signs them. Native builds are kept 5 years, for LTS lines only. The merge queue checks golden hashes only for `Current` and `Deprecated` operation versions that a golden product or registry package pins. `Retired` versions run from archived Wasm builds, re-verified on every toolchain, `detmath` or Wasmtime upgrade and weekly in shards. *Why:* a retired version's bits depend only on its archive and the Wasm runtime, which their own suites cover (R8-48). *Rejected:* every version on every merge (CI grows with history); native archives for every release.

Releases ship a CycloneDX software bill of materials from cargo-cyclonedx and SLSA Build L3 provenance. The dependency list is embedded by cargo-auditable as compressed JSON in a linker section. ECO owns export classification and CRA reporting.

### The build program

Contract 13.2 gives PLT the build program: how the oracle, builder and verifier roles build Crucible against its oracles.

**Decision D-PLT-45:** `oracles/index.toml` lists every oracle id with its crate, capability row, runner class, held-out split and verifier record. A work item `{ crate, capability row, oracle ids, held-out split, budget }` opens only when each id has a verifier pass, else `WorkItemError::OracleMissing { id }`. Policy refuses builder Changes under `oracles/`, and loosening a threshold needs the founder's Approval. Held-out splits, chosen by a fixed hash of case ids or by generators seeded in CI, are unreadable to builders. *Why:* builders read every visible input and can special-case it (R12-13), and verified oracles give "oracle-covered" a meaning before code exists (R12-02). *Rejected:* oracles written alongside code; held-out data in the readable tree.

A held-out failure fails the oracle (principle 6). `gpu-lab` and `device-farm` oracles run on rented hardware, the reference laptops included, and each gate reports oracle coverage per crate. Agent-built corpora enter `oracles/` through a verified Proposal, after agreeing with an independent source such as MPFR, Open CASCADE or libCEED.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Pinned toolchains and vendored dependencies | Stable pin per 6 weeks; nightly only for the threaded web build | Suite failure blocks the bump | PLT-O-DET-1 | 0 |
| Dependency register and audits | Register entries; `safe-to-deploy` audits; 14-day wait; sandboxed build scripts | Unaudited crate or delta fails CI | PLT-O-BLD-2 | 0 |
| Build acceleration | sccache and workspace rules | Cache outage: slower builds only | PLT-O-PERF-2 | 0 |
| Reproducible builds | Byte-identical unsigned artifacts, or provenance for PE and Mach-O | Mismatch blocks the release | PLT-O-BLD-1 | 1 (Linux, wasm32), 2 (all) |
| CI stages and capacity | As tabulated, inside each phase budget | Stage over budget: capacity review | PLT-O-DET-9 | 0 |
| Pinned renderer image | Fixed lavapipe build; byte-identical Snapshots in CI | Snapshots stay `Unverified` (contract 2) | PLT-O-BLD-1 | 1 |
| GPU lab | Listed devices, fixed drivers, canary upgrades | Outage blocks beta promotion of GPU paths | PLT-O-GPU-1 | 1 |
| Release channels | Train with separate security patches; LTS; five-year lines; regulated support | A canonical change in a line, or no support end date, blocks the release | PLT-O-BLD-3 | 1 (train), 2 (LTS) |
| Archives and retired versions | Retention per D-PLT-47; retired versions weekly | Missing archive blocks the release | PLT-O-BLD-3 | 2 |
| Software bill of materials and provenance | CycloneDX, embedded list, SLSA Build L3 | Missing artifact blocks the release | PLT-O-PKG-2 | 1 |
| Oracle-first work items | Verified oracle ids first; no builder writes to `oracles/`; coverage per crate | `WorkItemError::OracleMissing { id }` | PLT-O-BLD-4 | 0 |
| Held-out splits | Outside the builder-readable tree; reported apart | A held-out failure fails the oracle | PLT-O-BLD-5 | 0 |

## Performance engineering

PLT owns contract 13.3's rows, their measurement and low-band targets.

**Decision D-PLT-28:** The reference processor is the Intel Core Ultra 7 258V (8 cores, AVX2, Arc 140V GPU) with 32 GB, measured at 1920×1080. At the phase 0 gate PLT names the laptop model, panel and firmware. It keeps three units: Windows 11, Ubuntu LTS and a spare. Only they block beta promotion, and other Tier 1 OSes' mid machines land within 1.5 times of each row. *Why:* the 258V runs between "Minimum assured power 8 W" and "Peak turbo power 37 W", so the chassis sets sustained speed (R12-06). As the weaker candidate, it turns wider dispatch elsewhere into margin (R6-07). *Rejected:* an unnamed chassis; one dual-booted unit; a Ryzen AI 300 (AVX-512 and 24 threads hide costs); Apple silicon. (revised in round 3)

Bands: low is 4 cores, 8 GiB and an integrated GPU (a 2019 x86-64-v3 laptop, the lowest Snapdragon X laptop, a MacBook Air M1). Mid is 8 to 14 cores and 24 to 32 GiB.

Mid machines are the reference laptop, a Snapdragon X Elite, an M4 Pro MacBook Pro and an ARM64 workstation. High is 16 or more cores, 64 GiB and a discrete GPU.

### Measurement protocol

Benchmark files live in `oracles/plt/bench/`, each with a held-out variant such as perturbed GP1 parameters or a second ABC sample (R12-13). "Warm" means the CAS holds every derived artifact; rows run 30 times, browsers on mid machines.

Sessions run on AC power in one named power mode after 10 minutes of thermal soak at 20 to 25 °C. OS builds and drivers are pinned, and package power is logged.

A calibration workload opens each session, and a result more than 3% off discards it. On a 60 Hz panel, the 120 Hz row moves to the macOS mid machine and does not block beta.

| Contract 13.3 row | Benchmark file | Cache and statistic | Low band (target) | Blocks from phase |
| --- | --- | --- | --- | --- |
| Cold and warm start | `start.toml` | Median | 4 s and 1.5 s | 1 |
| Selection highlight | `select.toml` | Warm; p99 over 1,000 picks | 33 ms | 1 |
| Orbit | `orbit.toml` | Warm; p95 frame time at 2.1 MP | 30 fps at 1M triangles | 1 |
| Orbit of implicit Bodies | `orbit-implicit.toml` | Warm; p95 frame time | 20 fps | 1 |
| X-ray views | `xray.toml` | Warm; p95 frame time | 15 fps | 2 |
| Scene capacity | `scene.toml` | Warm; p95 frame time | Half the mid count | 2; high band 4 |
| Drag preview | `drag-early.toml`, `drag-late.toml` | Warm; p90, dependents covered | 250 ms | 1 |
| Rebuild after an early edit | `rebuild-gp1.toml`, `rebuild-abc200.toml` | Warm except the edited chain; p90 | 3 times mid | 1 |
| `SignOff` recertification | `recert-abc200.toml` | As above | 3 times mid | 1 |
| Interactive simulation update | `sim-elastic-100k.toml` | Warm-started; median | 3 s | 1 |
| Open a 1,000-part assembly | `assembly-1000.toml` | Warm CAS, cold process; median | 30 s | 2 |
| Input to photon | `latency.toml` | p99 by camera rig during a rebuild | 50 ms | 1 |
| Memory | `memory-gp1.toml`, `memory-idle.toml` | Peak resident set; browser memory after a recycle | As mid | 1 |
| Installed size | Per app package | Release builds | As mid | 1 |
| Flux CPU throughput, both rows | `ceed.toml` | Median | Not set | 1 |

Before phase 2 the forward renderer's capacity per GPU tier is published as a measured target that does not block beta (R12-05). GPU pipelines compile in the background, asynchronously on DX12 and Metal, where wgpu's `PIPELINE_CACHE` is unavailable.

### Profiling and continuous benchmarking

All crates emit `tracing` spans, exported to Tracy or `performance.measure` on demand. Each merge runs CPU benchmarks under an instruction counter.

A rise above 1% blocks the merge unless the verifier accepts a recorded reason. Nightly, a median rise above 3% confirmed by a Mann-Whitney U test at p < 0.01 files an issue.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Reference laptop | Named model, three units, fixed conditions; sole beta blocker | Session off its calibration: discarded | PLT-O-PERF-1 | 0 |
| Bands and `HardwareProfile` | Measured properties place every machine | Unknown hardware: low band | PLT-O-PERF-1 | 1 |
| Contract 13.3 rows | File, statistic and held-out variant per row; each blocks from its phase | Missed row blocks beta; held-out gap above 10% fails | PLT-O-PERF-1 | 1 |
| PLT's own rows | Update check under 2 KB; library, hashing and ratio targets | A missed row files an issue | PLT-O-PERF-3 | 1 |
| Instruction-count gate | 1% per merge | Merge blocked without an accepted reason | PLT-O-PERF-2 | 0 |
| Wall-time tracking | Nightly, statistically confirmed | Issue with the commit range | PLT-O-PERF-2 | 0 |
| Profiling | `tracing` spans to Tracy and browser profilers | Disabled span over 5 ns fails | PLT-O-PERF-4 | 0 |

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
| Allocation | Thread-local heaps | mimalloc, jemalloc, snmalloc | mimalloc v3 (D-PLT-14) | Macro-benchmarks |
| Out-of-core data | Chunked storage with explicit residency | Zarr v3 chunk stores | `ChunkedBuffer<T>` over the CAS | Assembly row on 2 GiB |
| GPU compute | One kernel source; integer reductions | CUDA libraries; CubeCL | Kernel IR through WGSL (D-PLT-16) | Identity per `GpuClass` |
| Wasm runtime | Ahead-of-time Cranelift, pooling | Wasmtime; V8 | Wasmtime LTS; one browser runtime | 1.6 times native |
| Deterministic Wasm | Injected metering; Wasm 3.0 deterministic profile | Wasmtime fuel | One determinizer (D-PLT-22) | The overhead table |
| Isolated Wasm calls | Component Model async with a `callback` export | Wasmtime with WASI 0.3 | Callback ABI everywhere (D-PLT-36) | 20 µs and 250 µs |
| Browser engine | Threads, SIMD, workers, OPFS | Figma (load time over 3 times faster after Wasm) | Two builds, heavy worker | Suite 2.0 and 2.5 times native |
| Rust GPU desktop app | Thin platform layer, GPU renderer | Zed | winit, AccessKit, wgpu, Parley | Input-to-photon p99 |
| Crash reporting | Out-of-process minidumps | Crashpad | `crash-handler`, rust-minidump | 99% symbolicated |
| Updates | TUF; executable-aware diffs | Zucchini (Chromium) | TUF, deltas (D-PLT-25) | Attack simulations |
| Build acceleration | Remote caching and execution | Bazel and Buck2 | sccache (D-PLT-26) | Warm CI under 6 minutes |
| Supply chain | Reproducible builds; audits; FIPS 204 | Debian, Arch Linux, NixOS; cargo-vet | Two builders; cargo-vet (D-PLT-40, D-PLT-46) | Byte comparison; audit coverage |
| Benchmarking | Instruction counts plus wall time | CodSpeed; Tracy | The same methods | One false gate a week at most |

## Platform notes

| Platform | Risk to parity | Mitigation | Phase |
| --- | --- | --- | --- |
| Windows | Timeout resets; long paths; undeletable mapped files; antivirus; on ARM64, Wasmtime Tier 3 and no `crash-handler` | Dispatch rule; `\\?\` paths; deferred deletion; packed small objects; own qualification or Pulley; exception filter | 0 to 2 |
| macOS | `allow-jit`; OS-shipped shader compiler | Entitlement; OS build in `GpuClass` | 1 |
| Linux | Wayland gaps; old distributions; ARM64 GPU coverage | Portal back ends; glibc 2.34 floor; lab machine | 0 to 2 |
| Browsers | Isolation; memory that never shrinks; Safari's deletion; partial WebGPU | Two builds; recycling; sync indicator; WebGL2 | 1 to 2 |
| Tablets | No native JIT and App Review on iPadOS; 16 KB pages on Android | Web build in WKWebView with registry Wasm components remote; NDK r28 | 3 |
| Servers | Shared tenants; no KVM in cloud VMs | Single-tenant hosts; Firecracker or gVisor | 1 to 4 |
| Tier 3 | No vendor CI | `Unverified` until the suite passes | 5 |

## Interfaces with other subsystems

### Provided by PLT

| To | What | Types |
| --- | --- | --- |
| KLN | Three lanes, cancellation, safe points, memory budgets and tables, the class for keys, CAS storage, combinators, `detmath`, the mechanism table, the dispatch rule, worker images and the team server install, attestation, disposable Op workers, label-aware egress, the FIPS-mode crypto provider | `ComputePool`, `PoolLane`, `MemoryBudget`, `PlatformClass`, `Storage`, `ChunkedBuffer<T>`, `CryptoProvider` |
| ANV | Canonical SIMD lanes, `detmath`, `det_sum`, `exact_sum`, `linalg`, GPU paths, archived Wasm builds of frozen versions, the Parley stack under `anvil::text_outline` | `simd`, `detmath`, `GpuPath` |
| FLX | `detmath`; combinators; `linalg` jointly; `gpu` with known-answer tests; the dispatch and agreement rules; FMA families; the class enum; the browser memory table | `GpuCompute`, `GpuPath`, `RanOn`, `PlatformClass` |
| UIX | Windows, input and IME, accessibility hosting, clipboard, dialogs, surfaces, the approval session, hardware profile, workarounds, device loss, safe mode, crash monitor, rings, the `Interactive` lane, dispatch rule, memory caps, browser rows, telemetry pipeline, renderer image, dependency register | `WindowHost`, `AccessibilityHost`, `Authenticator` |
| `repo` | Journal, atomic writes, locks, watching, portable paths, text normalization | `Journal`, `WatchEvent`, `RepoPath` |
| ING | Executors, the determinizer, verification of generated modules, `detmath` and `det_sum` (Ingot's `sum`), text normalization, the browser memory table | `WasmComponentEngine`, `CallLimits` |
| ECO | The determinizer and overhead table, Wasmtime LTS, world enforcement, sandboxes with default-deny egress, the browser runtime and sandbox site, `crucible:host/parallel` and `crucible:tool/process`, offline bundles, TUF and signature formats, release lines and support periods | `WasmComponentEngine`, `CallLimits` |
| AGT | `api` transport, `cli` exit codes, `CredentialStore`, the approval session, `Usage` measurement, the stdio sandbox for external MCP servers | `Guidance` errors, `Authenticator` |
| MEC, COV | `linalg`; for COV also `f64` availability per class, with no emulated `f64` on WebGPU, and the browser memory table | `linalg`, `PlatformClass` |
| ELX | `detmath`; the browser memory table; serial and USB access (FLX owns circuit LU) | `DeviceIo` |
| MFG | Packages for `apps/machine-gateway`; serial and USB access; the TPM-held gateway key; the browser memory table | `DeviceIo` |

### Consumed by PLT

| From | What PLT needs |
| --- | --- |
| KLN | Grades and class acceptance; key composition and closure hashes; the catalog of limit outcomes; small-object packing; cost hints; the priority table that maps lanes; what attestation signs; two-person egress grants |
| ANV, FLX | Grades, GPU roles, agreement budgets and corpora per operation; the kernel IR, sparse factorization and no-FMA penalties; `anvil::text_outline` |
| COV | Precision classes per model; External Op worker needs |
| UIX | The AccessKit tree; render-quality levels; device-loss and safe-mode behavior; its rows; telemetry fields; a copy budget; the approval flow |
| ECO | Worlds; browser Wasm component descriptions; declared memory limits; font packages; export classification and CRA reporting |
| AGT | Message framing, error shape, `Usage`, `Budget` and the approval origin |
| ING | The interpreter on every target; generated modules; the feature-call memory model |
| MFG | The gateway's core and connectors to package |

## Oracles

PLT oracles live in `oracles/plt/`, with held-out splits outside the builder-readable tree (D-PLT-45). Runner classes: `browser-ci` for PLT-O-WEB-1 to PLT-O-WEB-5; `gpu-lab` for PLT-O-GPU-1 to PLT-O-GPU-4, PLT-O-PERF-1, PLT-O-PERF-3 and PLT-O-OS-1 to PLT-O-OS-3; `device-farm` for PLT-O-TGT-1; `cpu-ci` otherwise.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| PLT-O-DET-1 | Canonical identity | Every hash equals the reference on every Tier 1 target, forced ISA level, browser and executor |
| PLT-O-DET-2 | Schedule independence | Identical at 1, 2, 3, 8 and 64 threads with stealing delays and allocator randomization |
| PLT-O-DET-3 | Out-of-core equivalence | Identical with a 64 MiB budget |
| PLT-O-DET-4 | `detmath` correct rounding | Exhaustive f32, hard-case and 10⁹ random f64 inputs match MPFR; ports match the C build |
| PLT-O-DET-5 | Lints | Layering and crate order, disallowed methods and types, intrinsics, `-ffp-contract=off`, no faer in `Portable` code, no NaN inspection |
| PLT-O-DET-6 | Cross-class agreement | Every `CpuIsa` and `GpuClass` meets D-PLT-35 on golden products and corpus; a planted 3% drift under a shared plan fails |
| PLT-O-DET-7 | Floating-point environment | A planted flush-to-zero library causes an Abort and a correct rerun |
| PLT-O-DET-8 | `detmath` speed | Per-function targets on x86-64-v3 and wasm32 |
| PLT-O-DET-9 | Suite cadence | A planted divergence bisects to its commit and blocks beta |
| PLT-O-LA-1 | `linalg` identity | Identical under two cache settings and any thread count |
| PLT-O-LA-2 | `linalg` speed | Dense n ≥ 1,000 within 2.5 times faer `CpuIsa` |
| PLT-O-GPU-1 | Known-answer tests | A planted fused or reassociated pipeline fails and falls back to the CPU |
| PLT-O-GPU-2 | GPU recovery | Forced loss recovers within 5 s and caches nothing from lost work |
| PLT-O-GPU-3 | GPU primitives and roles | Identity per `GpuClass` over 1,000 runs; injected NaN detected; filters drop no true candidate |
| PLT-O-GPU-4 | Dispatch rule | No dispatch over 4 ms while orbiting; no reset in 1,000 long solves |
| PLT-O-RT-1 | Start latency | `Interactive` under 1 ms and `Foreground` under 2 ms at p99 with the other pools loaded |
| PLT-O-RT-2 | Memory exhaustion | Golden products within their rows; exhaustion is an uncached Abort |
| PLT-O-RT-3 | Usage accounting | Within 5% of an independent measurement |
| PLT-O-OS-1 | Shells and input | Window lifecycle per OS; recorded pointer, pen and HID traces replay identically |
| PLT-O-OS-2 | IME | Japanese, Chinese and Korean composition on each desktop OS |
| PLT-O-OS-3 | Accessibility | Tree snapshots per golden-product screen; OS automation reads names and roles; axe-core passes |
| PLT-O-OS-4 | Platform services | Clipboard, locks, watcher fuzzing, dialogs, notifications, USB loopback; an approval against a self-hosted domain on every desktop OS |
| PLT-O-OS-5 | Path portability | A repository created on each OS checks out with identical hashes on the others |
| PLT-O-OS-6 | Text and fonts | Identical text hashes from every OS; identical shaping on every class |
| PLT-O-TGT-1 | Tier 2 targets | Device-farm smoke tests; WebKit and Android executors match canonical hashes |
| PLT-O-TGT-2 | Worker isolation and team servers | Untrusted workers reach no key; no slot crosses tenants; a third-party closure on a shared host is refused; the team server installs with and without KVM |
| PLT-O-WEB-1 | Isolation and sign-in | Threaded build only when isolated; both builds identical; redirect sign-in works |
| PLT-O-WEB-2 | One engine per origin | Owner closed mid-edit: no Change lost; heavy-worker packs adopted intact |
| PLT-O-WEB-3 | Browser memory | Caps hold on 8 GB and 32 GB machines; a recycle restores idle memory; heavy evaluations at 1 and 8 threads match |
| PLT-O-WEB-4 | Verified web updates | Tampered, rolled-back or frozen manifests refused |
| PLT-O-WEB-5 | Browser hashing | Native-identical `ObjectId`s; 1 GiB in 1 s with 8 workers |
| PLT-O-WASM-1 | Wasm determinism | Identical outputs, fuel and traps in every executor; spec tests pass |
| PLT-O-WASM-2 | Determinizer overhead | Each class within its row |
| PLT-O-WASM-3 | Cancellation and failure kinds | Cancellation lands at fuel checks, or at Op boundaries within 150 ms at p99 without shared memory; no Abort reaches a memo or the CAS |
| PLT-O-WASM-4 | Observable NaN | NaN-observing modules agree across engines; others are unchanged |
| PLT-O-WASM-5 | Ingot module verification | Each planted violation is rejected |
| PLT-O-WASM-6 | Isolation, egress and worlds | A hostile guest reads no repository, OPFS, token or key; its DNS, TCP, UDP and HTTP attempts fail outside its grant; a browser sandbox worker cannot `fetch`, open a WebSocket, import scripts or navigate |
| PLT-O-WASM-7 | Isolated calls | 10,000 `anvil::offset` calls give identical results through every executor within the isolation rows; std within 15% |
| PLT-O-WASM-8 | WIT interfaces | Published WIT matches this tab; `map-chunks` gives identical outputs and fuel at 1 and 64 threads; an undeclared program is refused |
| PLT-O-PKG-1 | Update security | TUF attacks rejected; power loss during apply leaves a runnable version |
| PLT-O-PKG-2 | Install hygiene | Install, upgrade and uninstall leave no stray files; signatures and notarization verify |
| PLT-O-PKG-3 | Dual signatures | Post-quantum verifiers require both signatures; unknown ids fail closed |
| PLT-O-PKG-4 | Air-gapped installs and policy | Mirror import and offline install verify; every policy applies on every OS |
| PLT-O-REL-1 | Crash capture | Every `sadness-generator` crash type in every process, Windows ARM64 included, is symbolicated |
| PLT-O-REL-2 | Journal durability | Random kills lose no appended record; dropped writes lose at most 1 s |
| PLT-O-REL-3 | Safe mode and degradation | Safe mode changes no canonical hash; degradations name their cause |
| PLT-O-PRIV-1 | Label-aware egress | With a confidential design open, no notification, email, crash upload or bundle carries content |
| PLT-O-PRIV-2 | Telemetry | Payloads match the schema; small aggregates dropped; allowlist enforced |
| PLT-O-BLD-1 | Reproducible build | Byte-identical unsigned artifacts; the renderer image reproduces snapshot bytes |
| PLT-O-BLD-2 | Dependency register and audits | Complete entries; every crate audited; a build script reaching the network fails |
| PLT-O-BLD-3 | Old releases and lines | Archived engines and retired versions reproduce their golden hashes; patches change no canonical hash; every release states its support end |
| PLT-O-BLD-4 | Oracle-first work | Work items naming unverified oracles and builder Changes under `oracles/` are refused; coverage matches a recount |
| PLT-O-BLD-5 | Held-out splits | A planted special-casing implementation fails held-out; builder credentials cannot read the held-out repository |
| PLT-O-PERF-1 | Budgets | Every contract 13.3 row from its phase; other mid machines within 1.5 times; held-out within 10% of visible |
| PLT-O-PERF-2 | Regression gates | Instruction counts within 1%; wall-time changes confirmed statistically |
| PLT-O-PERF-3 | PLT's own rows | Browser and Wasm ratios, update check |
| PLT-O-PERF-4 | Profiling overhead | Disabled span under 5 ns; capture under 5% of frame time |

## Phasing

Gate contributions only, consistent with contract 13.1 and 13.2; no capability in contract 13.4's shared phase table belongs to PLT.

| Phase | PLT contribution to the gate |
| --- | --- |
| 0 | Determinism suite green; `detmath` C build and hot ports; `linalg` dense kernels; Wasmtime LTS, determinizer and overhead table; lanes and combinators; platform layers; crash capture; the reference laptop named; kill thresholds, memory figures and no-FMA penalties measured; the `CpuIsa` elasticity measurement for WGSL (contract 7.5); cargo-vet; the oracle index, held-out store and work-item gate |
| 1 | Contract 13.3's phase 1 rows; general availability on contract 9's phase 1 targets, with preview targets in automation; MSIX, DMG, deb and rpm with TUF; one engine per origin, heavy worker and recycling; remote third-party evaluation in browsers; native isolation with default-deny egress; the approval session; known-answer tests; journal, safe mode and egress rules; reproducible Linux and wasm32 builds; the team server install |
| 2 | Phase 2 rows on GP3 and GP4; preview targets at general availability; first LTS line; deltas and further formats; gateway packages; policy and telemetry; the manifest transparency log; dual signatures; reproducible builds or provenance everywhere; the browser sandbox; attestation; GP3 and GP4 identical on desktop, browser and server |
| 3 | iPadOS through WKWebView, Android tablets and phone viewers; air-gapped installs; mobile accessibility and crash capture; Vulkan `f64` paths; GP5 on Tier 2 |
| 4 | The 1,000,000-Instance high-band row; multi-GPU servers and distributed `exact_sum`; CUDA or HIP reconsidered; GP6 simulations within their rows |
| 5 and later | Tier 3 in the canonical class; SVE dispatch; memory64 re-evaluated; riscv64 servers |

## Open questions

1. **FIPS module certificate.** AWS-LC-FIPS 3.x awaits NIST certification. A phase 2 check confirms a certificate before FIPS mode ships, or KLN names another validated module; NIST decides the date.

Round 2's questions are closed. Decisions D-PLT-33 (1, 2), D-PLT-30 (3), D-PLT-18 (4), D-PLT-17 (5) and D-PLT-16 (6) settle the first six. D-PLT-46 (7), D-PLT-13 (8), D-PLT-47 (9), D-PLT-27 (10) and D-PLT-22 (11) settle the rest, and contract 12 settles 13.

Declined or partly applied findings:

- **R1-43**, declined in round 2: routine `SignOff` in `CpuIsa` with FMA, because contract 7.3 requires canonical recomputation.
- **R12-15** and **R11-05**, partly: no native WebAuthn and no isolated webview. One ceremony runs on one origin in a browser session.
- **R12-18** and **R12-06**, partly: browser figures and the laptop model are fixed at the phase 0 gate by stated rules. The measurements do not exist yet.
- **R12-02, R12-03 and R12-22**, in contract 13.2's form: no staffing or dated milestones; CI capacity enters each phase budget.
- **R9-44**, partly: sentences stay under 25 words, but decision paragraphs keep their Decision, Why and Rejected sentences and so run past three.

## Contract change requests

- CCR-PLT-5 to CCR-PLT-8: accepted in contract v5 (sections 7.4, 13.3, 7.8 and 12).
- **CCR-PLT-9, tablet engine placement.** Contract 9 runs the engine as "threads on tablets", but 7.4 makes iPadOS's engine the web build's worker. Proposed: "threads on Android tablets, a worker on iPadOS".
- **CCR-PLT-10, CRA support period.** Contract 7.7 sets LTS support but no five-year support period per release line, which the CRA requires (R11-28). Proposed: "Every release line has a five-year support period (D-PLT-27)."

## Sources

1. winit releases. https://github.com/rust-windowing/winit/releases
2. AccessKit repository. https://github.com/AccessKit/accesskit
3. WebAssembly feature support data. https://raw.githubusercontent.com/WebAssembly/website/main/features.json
4. WebGPU implementation status. https://github.com/gpuweb/gpuweb/wiki/Implementation-Status
5. wgpu releases. https://github.com/gfx-rs/wgpu/releases
6. wgpu `Features` documentation (30.0.1). https://docs.rs/wgpu/latest/wgpu/struct.Features.html
7. CubeCL repository. https://github.com/tracel-ai/cubecl
8. Wasmtime release process. https://docs.wasmtime.dev/stability-release.html
9. Wasmtime releases. https://github.com/bytecodealliance/wasmtime/releases
10. Wasmtime `Config` documentation (49.0.2). https://docs.rs/wasmtime/latest/wasmtime/struct.Config.html
11. Wasmtime platform support. https://docs.wasmtime.dev/stability-platform-support.html
12. Wasmtime deterministic execution. https://docs.wasmtime.dev/examples-deterministic-wasm-execution.html
13. jco repository. https://github.com/bytecodealliance/jco
14. WASI roadmap. https://wasi.dev/roadmap
15. Wasm 3.0 announcement. https://webassembly.org/news/2025-09-17-wasm-3.0/
16. WebAssembly nondeterminism. https://github.com/WebAssembly/design/blob/main/Nondeterminism.md
17. Relaxed SIMD overview. https://github.com/WebAssembly/relaxed-simd/blob/main/proposals/relaxed-simd/Overview.md
18. wasm-instrument repository. https://github.com/paritytech/wasm-instrument
19. Is Memory64 actually worth using? SpiderMonkey blog. https://spidermonkey.dev/blog/2025/01/15/is-memory64-actually-worth-using.html
20. Document-Isolation-Policy, Chrome for Developers. https://developer.chrome.com/blog/document-isolation-policy
21. Making your website cross-origin isolated using COOP and COEP, web.dev. https://web.dev/articles/coop-coep
22. Origin private file system, MDN. https://developer.mozilla.org/en-US/docs/Web/API/File_System_API/Origin_private_file_system
23. Storage quotas and eviction criteria, MDN. https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria
24. wasm-bindgen-rayon repository. https://github.com/RReverser/wasm-bindgen-rayon
25. Jangda, Powers, Berger, Guha. Not So Fast: Analyzing the Performance of WebAssembly vs. Native Code. USENIX ATC 2019. https://www.usenix.org/conference/atc19/presentation/jangda
26. WebAssembly cut Figma's load time by 3x. https://www.figma.com/blog/webassembly-cut-figmas-load-time-by-3x/
27. Portable SIMD repository. https://github.com/rust-lang/portable-simd
28. Announcing Rust 1.89.0. https://blog.rust-lang.org/2025/08/07/Rust-1.89.0/
29. Tracking issue for scalable vectors, rust-lang/rust#145052. https://github.com/rust-lang/rust/issues/145052
30. pulp repository. https://github.com/sarah-quinones/pulp
31. RFC 3514, float semantics. https://rust-lang.github.io/rfcs/3514-float-semantics.html
32. Rust `f64` documentation. https://doc.rust-lang.org/std/primitive.f64.html
33. Rust `File` documentation. https://doc.rust-lang.org/std/fs/struct.File.html
34. rustc platform support. https://doc.rust-lang.org/rustc/platform-support.html
35. CORE-MATH project. https://core-math.gitlabpages.inria.fr/
36. ReproBLAS. https://bebop.cs.berkeley.edu/reproblas/
37. Intel oneMKL reproducibility conditions. https://www.intel.com/content/www/us/en/docs/onemkl/developer-guide-linux/2025-2/reproducibility-conditions.html
38. Determinism, Box2D blog. https://box2d.org/posts/2024/08/determinism/
39. Rapier determinism guide. https://rapier.rs/docs/user_guides/rust/determinism/
40. chili repository. https://github.com/dragostis/chili
41. mimalloc repository. https://github.com/microsoft/mimalloc
42. Parley repository. https://github.com/linebender/parley
43. HarfRust repository. https://github.com/harfbuzz/harfrust
44. notify repository. https://github.com/notify-rs/notify
45. arboard repository. https://github.com/1Password/arboard
46. rfd repository. https://github.com/PolyMeilex/rfd
47. Zed repository. https://github.com/zed-industries/zed
48. Crashpad README. https://chromium.googlesource.com/crashpad/crashpad/+/HEAD/README.md
49. Embark crash-handling repository. https://github.com/EmbarkStudios/crash-handling
50. rust-minidump repository. https://github.com/rust-minidump/rust-minidump
51. Chromium GPU testing. https://chromium.googlesource.com/chromium/src/+/HEAD/docs/gpu/gpu_testing.md
52. Zucchini README. https://chromium.googlesource.com/chromium/src/+/HEAD/components/zucchini/README.md
53. What is MSIX? Microsoft Learn. https://learn.microsoft.com/en-us/windows/msix/overview
54. Notarizing macOS software before distribution, Apple. https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution.md
55. App Review Guidelines, Apple. https://developer.apple.com/app-store/review/guidelines/
56. Support 16 KB page sizes, Android Developers. https://developer.android.com/guide/practices/page-sizes
57. The Update Framework overview. https://theupdateframework.io/docs/overview/
58. The Update Framework specification 1.0.37. https://theupdateframework.github.io/specification/latest/
59. Velopack repository. https://github.com/velopack/velopack
60. SLSA 1.0 security levels. https://slsa.dev/spec/v1.0/levels
61. Cyber Resilience Act, European Commission. https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act
62. sccache repository. https://github.com/mozilla/sccache
63. Tracy repository. https://github.com/wolfpld/tracy
64. CodSpeed documentation. https://codspeed.io/docs
65. macOS 27 will mark the end of an era, MacRumors. https://www.macrumors.com/2026/05/26/macos-27-will-mark-the-end-of-an-era/
66. Windows 11 26H2 officially released, Pureinfotech. https://pureinfotech.com/?p=192070
67. Wasmtime stability tiers. https://docs.wasmtime.dev/stability-tiers.html
68. Pulley, Wasmtime documentation. https://docs.wasmtime.dev/examples-pulley.html
69. Device and Network Abuse policy, Google Play Console Help. https://support.google.com/googleplay/android-developer/answer/9888379
70. Allow execution of JIT-compiled code entitlement, Apple. https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.cs.allow-jit
71. WebAssembly memory-control proposal overview. https://github.com/WebAssembly/memory-control/blob/main/proposals/memory-control/Overview.md
72. `FileSystemFileHandle.createSyncAccessHandle()`, MDN. https://developer.mozilla.org/en-US/docs/Web/API/FileSystemFileHandle/createSyncAccessHandle
73. Persistent storage options, SQLite Wasm documentation. https://sqlite.org/wasm/doc/trunk/persistence.md
74. `SubtleCrypto.digest()`, MDN. https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest
75. Cross-Origin-Opener-Policy, MDN. https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cross-Origin-Opener-Policy
76. WebGPU Shading Language, W3C Candidate Recommendation Draft, 21 September 2026. https://www.w3.org/TR/WGSL/ (section text read in the specification source, https://raw.githubusercontent.com/gpuweb/gpuweb/main/wgsl/index.bs)
77. GHSA-394w-hwhg-8vgm, Out-of-bounds write or crash when transcoding component model strings. https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-394w-hwhg-8vgm
78. GHSA-6wgr-89rj-399p, Data leakage between pooling allocator instances. https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-6wgr-89rj-399p
79. Wasmtime security advisories. https://github.com/bytecodealliance/wasmtime/security/advisories
80. FIPS 204, Module-Lattice-Based Digital Signature Standard. https://csrc.nist.gov/pubs/fips/204/final
81. 22 CFR 120.54, Activities that are not exports, reexports, retransfers, or temporary imports (Cornell LII). https://www.law.cornell.edu/cfr/text/22/120.54
82. GDPR recital 30, Online identifiers for profiling and identification. https://gdpr-info.eu/recitals/no-30/
83. Fearless SIMD 1.0, Linebender. https://linebender.org/blog/fearless-simd-1-0/
84. llvmpipe, Mesa documentation. https://docs.mesa3d.org/drivers/llvmpipe.html
85. faer 0.24.4 documentation. https://docs.rs/faer/latest/faer/
86. gemm-common `cache.rs`. https://github.com/sarah-quinones/gemm/blob/main/gemm-common/src/cache.rs
87. Intel Core Ultra 7 Processor 258V specifications, Intel. https://www.intel.com/content/www/us/en/products/sku/240957/intel-core-ultra-7-processor-258v-12m-cache-up-to-4-80-ghz/specifications.html
88. Regulation (EU) 2024/2847 (Cyber Resilience Act), Official Journal. https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202402847
89. Component Model concurrency explainer (stackless and stackful async). https://github.com/WebAssembly/component-model/blob/main/design/mvp/Concurrency.md
90. WASI releases. https://github.com/WebAssembly/WASI/releases
91. cargo-vet built-in criteria. https://mozilla.github.io/cargo-vet/built-in-criteria.html
92. cargo-vet, importing audits. https://mozilla.github.io/cargo-vet/importing-audits.html
93. cargo-deny repository. https://github.com/EmbarkStudios/cargo-deny
94. cargo-auditable repository. https://github.com/rust-secure-code/cargo-auditable
95. cargo-cyclonedx repository. https://github.com/CycloneDX/cyclonedx-rust-cargo
96. tikv-jemallocator repository. https://github.com/tikv/jemallocator
97. aws-lc-rs repository. https://github.com/aws/aws-lc-rs
98. Firecracker getting started. https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md
99. gVisor platforms. https://gvisor.dev/docs/architecture_guide/platforms/
100. Landlock, Linux kernel documentation. https://docs.kernel.org/userspace-api/landlock.html
101. `<iframe>` element, MDN. https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe
102. Using Web Workers, MDN. https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Using_web_workers
103. `Atomics.waitAsync()`, MDN. https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Atomics/waitAsync
104. `Window.showDirectoryPicker()`, MDN. https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker
105. ASWebAuthenticationSession, Apple. https://developer.apple.com/tutorials/data/documentation/authenticationservices/aswebauthenticationsession.json
106. Supporting passkeys, Apple. https://developer.apple.com/tutorials/data/documentation/authenticationservices/supporting-passkeys.json
107. `webViewWebContentProcessDidTerminate(_:)`, Apple. https://developer.apple.com/tutorials/data/documentation/webkit/wknavigationdelegate/webviewwebcontentprocessdidterminate(_:).json
108. `MiniDumpWriteDump`, Microsoft Learn. https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/nf-minidumpapiset-minidumpwritedump
109. Collecting user-mode dumps, Microsoft Learn. https://learn.microsoft.com/en-us/windows/win32/wer/collecting-user-mode-dumps
110. Reproducible Builds. https://reproducible-builds.org/
111. Reproducible Builds success stories. https://reproducible-builds.org/success-stories/
112. Remote execution, Buck2 documentation. https://buck2.build/docs/users/remote_execution/
113. Remote execution overview, Bazel documentation. https://bazel.build/remote/rbe
114. Wasmer runtime documentation. https://docs.wasmer.io/runtime
115. Zarr core specification, version 3. https://zarr-specs.readthedocs.io/en/latest/v3/core/index.html
