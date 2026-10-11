# Platform and performance (PLT)

Crucible runs one Rust core on every Tier 1 target behind one platform layer, so OS code lives in one crate. CPU results are bit-identical on every OS and browser through correctly rounded math, no implicit fused multiply-add and fixed reduction orders, while GPU paths are verified per compiled pipeline and keep a CPU path. PLT also owns the Wasm determinizer, packaging, reliability, CI and the performance targets of contract section 13.3, measured on one fixed reference laptop.

## Scope, crates and the platform layer

PLT owns the mechanisms below the product: OS services and shells, the compute runtime, determinism mechanisms and `PlatformClass`, `linalg` with FLX, the Wasm determinizer and executors, packaging, reliability, egress, CI and the performance targets. Contract sections 7.3 and 7.4 own the rules, KLN the determinism policy and UIX the renderer. This tab holds the one table of nondeterminism sources and controls (R3-37).

### Crates

| Crate | Location | Contents | `unsafe` |
| --- | --- | --- | --- |
| `platform-api` | `core/` | OS-service traits, `RepoPath`, `HardwareProfile`, `IsaLevel`, `GpuClass` | Forbidden |
| `runtime` | `core/` | Pools, IO bridge, combinators, memory budgets, `ChunkedBuffer<T>` | Forbidden |
| `simd` | `core/` | ISA detection, dispatch, canonical horizontal operations | Allowed |
| `detmath` | `core/` | Correctly rounded elementary functions | Forbidden |
| `gpu` | `core/` | Devices, pipelines, known-answer tests, integer reductions, recovery, workarounds | Allowed |
| `wasm-host` | `core/` | Determinizer, Wasmtime embedding, sandbox workers | Allowed |
| `linalg` | `core/` | Canonical dense and sparse linear algebra, with FLX | Forbidden |
| `platform` | `apps/` | The only crate that binds OS APIs | Allowed |
| `desktop`, `web`, `mobile`, `server`, `cli`, `ci-runner`, `attestation` | `apps/` | Entry points and packaging metadata | Forbidden |

`PlatformClass` lives in `base`, built from `IsaLevel` and `GpuClass`. `OpCx` in `base` wraps PLT's runtime handles (cancellation, budget, pool lane, GPU device), so operations see one context type (R3-27).

**Decision D-PLT-1:** OS services sit behind traits in `core/platform-api`, implemented by exactly one crate, `apps/platform`, and injected at startup by the app shell. *Why:* core crates stay OS-agnostic as contract section 9 requires, browser and native builds share every core crate, and tests inject in-memory implementations so storage and clocks never leak into evaluation. *Rejected:* `cfg(target_os)` scattered through core crates (untestable, breaks the browser build); one crate per OS service (many boundaries instead of one).

`cargo xtask check-layers` fails CI when a crate outside `apps/` depends on an OS-binding crate (`windows`, `objc2*`, `web-sys`, `winit`, `accesskit_*` and the like) or uses `cfg(target_os)`; ISA dispatch through `target_arch` stays allowed in `simd`, `detmath` and `gpu`.

[[DIAGRAM diagrams/12-platform-crate-layering.jsx: crate layering · dependencies point down, one crate binds the OS]]

### Library choices

| Service | Library | Status checked October 2026 |
| --- | --- | --- |
| Windows, event loop, input | winit | 0.30.13 stable; 0.31.0-beta.3 (4 September) adds pen, IME and positional drag events |
| Accessibility | AccessKit | Adapters for UI Automation, NSAccessibility, AT-SPI, Android, UIAccessibility; no web adapter, no rich text |
| Text | Parley with HarfRust, Fontique, Skrifa, ICU4X | Pure Rust; HarfRust reports under 25% slower than HarfBuzz on common fonts |
| Clipboard, dialogs, watching | arboard, rfd, notify | Wayland data-control and the XDG portal where available; polling fallback for watching |
| File locking | `std::fs::File::lock` | Stable since Rust 1.89; locks "may be advisory or mandatory" |
| Notifications, credentials | Native code in `platform` | MSIX identity on Windows; Keychain, Credential Manager, Secret Service, Android Keystore, non-extractable WebCrypto keys |

**Decision D-PLT-4:** winit provides windows, the event loop and raw input on every target. Crucible pins one 0.31 beta commit on a Crucible-maintained patch branch with a named owner, re-pins at each beta, moves to stable once published, and budgets half an engineer for upstream pen, IME and drag-out work. *Why:* only winit covers desktop, web, iOS and Android, and 0.31 adds the input events CAD needs, but its betas break APIs (R6-39). *Rejected:* SDL3 (a C dependency duplicating winit); GPUI's platform layer (bound to Zed, no web target); a custom layer; staying on 0.30 (no pen or positional drag events). (revised in round 2)

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

`Journal` (append, flush, replay to the first bad record), `WindowHost` (windows, surfaces, IME, drags, accessibility hosts), `FileWatcher`, `Clipboard`, `Dialogs`, `Notifications`, `CredentialStore`, `SystemSignals` and `WallClock` follow the same pattern; `WallClock` never reaches evaluation. `Authenticator` returns WebAuthn assertions with user verification for the approval page (contract section 7.6), and `DeviceIo` opens serial and USB ports on native targets for MFG's machine gateway, whose device key stays non-exportable in the OS keystore, and for ELX's bench adapters, never inside evaluation. `CryptoProvider` supplies TLS, hashes and signatures; KLN's FIPS mode routes it through a FIPS 140-3 module, with AWS-LC through aws-lc-rs the leading candidate [certificate status unverified], and refuses non-approved algorithms.

### Paths, text and accessibility

`RepoPath` is UTF-8 in NFC, `/`-separated and relative, without `.` or `..`. Segments hold at most 255 bytes and no control characters, `< > : " | ? * \`, trailing dot or space, or Windows device name (`CON`, `NUL`, `COM1` and the like). Paths equal after Unicode case folding collide (`PathError::CaseCollision`), and paths outside repositories are opaque `HostPath`s that never enter the CAS.

**Decision D-PLT-5:** Repository paths are portable by construction: NFC, `/`-separated, case-fold unique and free of names that any Tier 1 OS rejects. *Why:* a name valid on Linux but not on Windows, or two names differing only in case, splits a team across operating systems. *Rejected:* storing OS-native paths (breaks checkouts across OSes); normalizing silently at checkout (two source names map to one file, so content is lost).

**Decision D-PLT-6:** Text in a design repository is stored as UTF-8 with LF line endings and no byte-order mark, and readers normalize CRLF, CR and BOM on input. *Why:* content hashes must not depend on the OS that wrote the file. *Rejected:* per-OS line endings with conversion at checkout (Git's approach, which makes hashes depend on settings).

**Decision D-PLT-7:** Text that becomes part of a design uses fonts from registry packages pinned in `ingot.lock` and shaped by the pure-Rust Parley stack; system fonts serve only the UI. *Why:* system font sets differ by OS and version, so engraved text or drawing annotations would change geometry between machines, which principle 4 forbids. *Rejected:* DirectWrite and Core Text (different shaping per OS); system fonts in designs (not reproducible).

**Decision D-PLT-8:** Crucible's canvas UI gets a web accessibility adapter that mirrors the AccessKit tree into a hidden ARIA DOM, routes focus and actions back as AccessKit requests, and is offered upstream with two engineers shared with UIX. *Why:* AccessKit has no released web adapter, browsers are Tier 1, and identical features include accessibility. *Rejected:* a separate accessible HTML UI (a second UI that drifts); waiting for upstream (no schedule exists).

Shells are thin `apps/` crates that wire `platform` into `api` and own OS integration. `desktop` handles file associations and `crucible://` links, `web` the service worker and OPFS, `mobile` document providers and Apple Pencil, `server` and `ci-runner` health endpoints, and `cli` per-error exit codes.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Layered crates | Only `apps/platform` binds OS APIs; `unsafe` as contract section 12 allows | Layering check fails the build | PLT-O-DET-5 | 0 |
| Windows and surfaces | `WindowHost` gives raw handles to the renderer | `PlatformError::Window { backend, reason, fix }` | PLT-O-OS-1 | 0 |
| Pointer, pen and touch | One `PointerEvent` stream with pressure and tilt where reported | Missing axes are `None`, never invented | PLT-O-OS-1 | 1 (desktop), 3 (tablets) |
| Keyboard and IME | Physical key, logical key and committed text kept apart; preedit and commit | No IME: plain input, and the UI says so | PLT-O-OS-2 | 1 |
| 6-DoF devices | `NavDeviceEvent` from HID; spacenavd on Linux | Device absent: no events, no error | PLT-O-OS-1 | 2 |
| Accessibility | AccessKit tree per window; actions return as events; web DOM mirror | Inactive adapter: UI works, `AccessibilityUnavailable` logged once | PLT-O-OS-3 | 1 (desktop, web), 3 (tablets) |
| Clipboard | Plain-text Ingot plus `application/x-crucible+cbor`; labelled content per D-PLT-38 | `ClipboardError::Unavailable { reason }` | PLT-O-OS-4 | 1 |
| Drag and drop | Incoming through winit; outgoing through each OS's drag source | Unsupported outgoing drag: "Export…" offered with the reason | PLT-O-OS-4 | 1 (incoming), 2 (outgoing) |
| File dialogs | Async `open`, `save`, `pick_folder` | No portal on Linux: in-app browser with a notice | PLT-O-OS-4 | 1 |
| Notifications | `Notifications::post`; content per D-PLT-38 | Denied: notice in the activity panel | PLT-O-OS-4 | 1 |
| File watching | `Changed`, `Rescan`, `Health` events | Overflow or network file system: `Rescan`, and the status bar says "watching by polling" | PLT-O-OS-4 | 1 |
| File locking | Exclusive lock on `.crucible/lock`; CAS writes by temporary file and rename | `LockError::Held { holder_pid, since }` with "close the other window or open read-only" | PLT-O-OS-4 | 0 |
| Credentials | `CredentialStore` per account | `CredentialError::Unavailable`; sign-in asks again | PLT-O-OS-4 | 1 |
| WebAuthn | `Authenticator` assertions with user verification | No verifying authenticator: approval refused with the reason | PLT-O-OS-4 | 1 |
| Serial and USB | `DeviceIo` ports on native targets, outside evaluation; the gateway's device key in the OS keystore | `DeviceError::Unavailable { port, reason }` | PLT-O-OS-4 | 2 |
| FIPS-mode cryptography | `CryptoProvider` through a FIPS 140-3 module on servers and desktops | Non-approved algorithm refused with the reason | KLN-O-SIG-2 | 2 |
| System signals | Memory pressure, power, thermal state, scale, reachability | Unavailable signal: `Unknown` | PLT-O-OS-1 | 1 |
| Portable paths | `RepoPath::parse`; OS paths only in `platform` | `PathError` with a suggested portable name | PLT-O-OS-5 | 0 |
| Text normalization | UTF-8, LF, no BOM | `TextError::InvalidUtf8 { offset }` | PLT-O-OS-6 | 0 |
| Design fonts | Registry fonts pinned by hash, shaped by HarfRust | `FontError::MissingGlyph { char, font }`, never a substitution | PLT-O-OS-6 | 1 |

## Targets

Contract section 9 fixes the tiers, the Tier 1 preview rule (R6-06) and parity. This section fixes versions, CPUs, GPU back ends, Wasm executors and risks per target.

| Target | Phase 1 | OS and CPU | GPU back ends | Wasmtime tier | Main risks |
| --- | --- | --- | --- | --- | --- |
| Windows 11 x86-64 | General availability | Releases in Microsoft servicing [end dates unverified]; x86-64-v2 with dispatch to v3 and v4 | DX12, Vulkan | 1 | Driver variance; timeout resets |
| Windows 11 ARM64 | Preview | 24H2 and later; ARMv8 NEON | DX12 | 3 | No `crash-handler` support; Chrome's WebGPU behind a flag |
| macOS | General availability | Current and two prior on Apple silicon [macOS 27 release unverified] | Metal | 2 | JIT entitlement; shader compiler ships with the OS |
| Linux x86-64 | General availability | glibc 2.34 or later [distribution versions unverified]; Wayland and X11 | Vulkan; OpenGL ES 3 | 1 | Wayland protocol gaps |
| Linux ARM64 desktop | Preview | As above, ARMv8 NEON | Vulkan | 2 | Desktop GPU coverage (R6-31) |
| Chrome and Edge | General availability | Current and previous stable; wasm32 with SIMD128 and threads | WebGPU, WebGL2 | Browser engine | Isolation; memory that never shrinks |
| Safari | Preview | 26 and later | WebGPU, WebGL2 | Browser engine | Seven-day deletion of script-written data |
| Firefox | Preview | Current and ESR | WebGPU on Windows and macOS; WebGL2 on Linux | Browser engine | WebGPU on Linux in Nightly only |

Per the gpuweb status page, Chrome ships WebGPU on Windows x86-64, macOS and ChromeOS since 113, and on Linux only for Intel Gen12+ and NVIDIA on Wayland. Firefox ships it on Windows since 141 and macOS from 145, and Safari from 26.

Wasmtime's Tier 3 (Windows ARM64) lacks "CI testing, full-time maintainer" and Tier 2 (aarch64 macOS and Linux) "Continuous fuzzing" (R6-12). The Wasm runtime engineer of contract section 13.2 funds upstream fuzzing on aarch64 and CI for Windows ARM64, iOS and Android, aiming for Tier 2 on Windows ARM64 by the phase 1 gate.

**Decision D-PLT-2:** Native x86-64 builds target x86-64-v2 and dispatch hot kernels at run time to x86-64-v3 and x86-64-v4; ARM64 builds target ARMv8 with NEON. *Why:* every dispatched path produces identical canonical bits, so a low baseline costs speed only in cold code and keeps older CPUs supported. *Rejected:* an x86-64-v3 baseline (drops CPUs without AVX2 for a gain dispatch already captures); per-CPU builds (multiplies release artifacts).

**Decision D-PLT-3:** Linux binaries link against a glibc 2.34 sysroot and use no newer symbols, and Wayland is a first-class target equal to X11. *Why:* engineering desktops run long-lived distributions, and the oldest in scope sets the floor. *Rejected:* static musl desktop builds (GPU drivers load through the system loader); per-distribution builds.

### Tablets and phones

Tier 2 covers viewing, review and light editing with the same core crates and UI. M-series iPads and Android tablets edit locally, A-series iPads below the memory budget, and heavy evaluation is remote by default; phones are viewers that never approve Acts (contract section 7.6).

**Decision D-PLT-33:** On iPadOS, Wasm runs inside WebKit, in a WKWebView worker beside the native engine threads or as the web build in a thin WKWebView shell, where JavaScriptCore compiles it as in Safari; Pulley is the fallback. std and first-party Wasm components ship in the binary, and registry packages appear only as dependencies of an opened design. *Why:* `allow-jit` exists only on macOS, and Pulley carries "a ~10x order-of-magnitude slowdown" (R6-13). *Rejected:* Pulley for all Wasm (too slow); remote-only evaluation (no offline editing); a browsable package catalog (App Review guideline 3.2.2(i)).

The app meets App Review guidelines 2.5.2, 3.1, 3.2.2(i), 4.2.3(ii) and 4.7; the native Ingot interpreter runs on the engine threads.

Google Play's ban on downloaded executable code "does not apply to code that runs in a virtual machine or an interpreter" with indirect API access. Android therefore runs Wasmtime with Cranelift, and no world imports Android APIs (R6-41). Builds use NDK r28 or later for the 16 KB pages Google Play requires from 1 February 2027.

### Tier 3 and servers

FreeBSD, OpenBSD, NetBSD, illumos and riscv64 Linux are community-supported, CLI and server first, and join the canonical class only after passing the determinism suite; until then their results are `Unverified` and stay local.

Servers are OCI images for x86-64 and ARM64 that compute in the canonical class. Optional GPUs serve `f64` Vulkan solves from phase 3, and CUDA or HIP is reconsidered at the phase 4 gate (contract section 7.5).

PLT builds the images of contract section 7.8's two worker pools. Untrusted-evaluation workers run Proposal CI and External Ops in single-use Firecracker- or gVisor-class microVMs with no attestation key and a per-Proposal namespace. Trusted builders evaluate merged revisions of protected branches in one process per (tenant, label set), with dedicated VMs for export-controlled label sets and no pooling slot shared across them (R5-09).

`apps/attestation` keeps its keys in an HSM and signs (`OpKey`, `ObjectId`) only for trusted-builder work, bound to workload identity; KLN owns what is signed and accepted. The phase 1 single-node team server has no second builder, so `SignOff` checks recompute there (contract section 7.8), and attestation arrives with cloud workers in phase 2.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Tier 1 general availability | Windows 11 x86-64, macOS, Linux x86-64, Chrome and Edge pass every golden product | A divergence blocks beta promotion | PLT-O-DET-1 | 1 |
| Tier 1 preview | Windows 11 ARM64, Linux ARM64 desktop, Safari, Firefox: same build, suite and golden checks headless, beta channel | Missing installer, updater or driver qualification blocks general availability | PLT-O-DET-1 | 1 (preview), 2 (general) |
| Upstream Wasmtime coverage | Fuzzing and CI funded for ARM64 and mobile targets | Below Tier 2: the target stays in preview | PLT-O-WASM-1 | 0 |
| Tier 2 tablets and phones | Same `api` and UI; local light editing, remote heavy evaluation | Over budget: remote evaluation offered | PLT-O-TGT-1 | 3 |
| iPadOS Wasm executor | JavaScriptCore in WebKit, Pulley fallback, std in the binary | Review rejection: remote evaluation | PLT-O-TGT-1 | 3 |
| Android Wasm executor | Wasmtime with Cranelift; no Android API imports | A world with a direct Android import fails to load | PLT-O-TGT-1 | 3 |
| Tier 3 targets | Community builds, `Unverified` until the suite passes | Results stay local | PLT-O-DET-1 | 5 |
| Server images | OCI images on x86-64 and ARM64 in the canonical class | Missing GPU: CPU path, reported | PLT-O-DET-1 | 1 |
| Untrusted-evaluation workers | Single-use microVMs, no key, per-Proposal namespace | Write outside the namespace destroys the VM | PLT-O-TGT-2 | 1 |
| Trusted builders | One process per (tenant, label set); dedicated VMs for export controls | Scope mismatch: dispatch refused | PLT-O-TGT-2 | 1 |
| Attestation service | HSM keys; signs only trusted-builder results bound to workload identity | Unbound request refused and logged | PLT-O-TGT-2 | 2 |

## The browser target

The browser runs the same core crates compiled to `wasm32-unknown-unknown`, in the canonical class, so a browser session, a desktop and a server share cached results bit for bit.

| Context | Runs | May block |
| --- | --- | --- |
| Main thread | Input, accessibility DOM mirror, frame presentation | Never |
| Engine worker | `api` server side, Kiln, CAS, journal, every OPFS write handle | With `Atomics.wait`, only while no IO is pending |
| Compute workers, max(1, min(`hardwareConcurrency` − 1, 16)) | The compute pool through wasm-bindgen-rayon | Yes |
| Heavy worker | One disposable evaluation with its own memory (D-PLT-30) | Yes |
| Wasm component sandbox | Third-party Wasm components in an opaque-origin iframe's worker (D-PLT-31) | Yes |
| Service worker | Offline cache, verified updates, port brokering | Never |

The threaded build passes `api` messages and triangle buffers through `SharedArrayBuffer` rings, and the unisolated build through transferred buffers.

**Decision D-PLT-29:** One engine runs per browser origin. The first tab's engine worker takes a Web Lock and owns every OPFS write handle (CAS packs, journal, and KLN's SQLite store on `opfs-sahpool`); other tabs run only the UI and reach it through a `MessagePort` brokered once by the service worker, and the next tab takes over and replays the journal when the owner closes. *Why:* a synchronous access handle "takes an exclusive lock on the file", and `opfs-sahpool` fails when initialized twice in one origin (R6-15). *Rejected:* one engine per tab on `readwrite-unsafe` handles (no journal consistency); the `opfs` VFS (needs cross-origin isolation).

### Isolation and sign-in

WebAssembly threads need `SharedArrayBuffer`, which needs `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp`. Crucible serves every asset from its own origin with CORP headers, relays third-party content, and ships the headers in team servers, whose health check reports a missing one. Embedded viewers use `Document-Isolation-Policy`, "shipping in Chrome 137 for desktop only", and the single-threaded build elsewhere.

**Decision D-PLT-9:** The web build ships two engine binaries from one source: a threaded build (atomics, bulk memory, SIMD128) and a single-threaded build (SIMD128). The page loads the threaded build when `crossOriginIsolated` is true and otherwise loads the single-threaded build and says why in the status bar. *Why:* features stay identical without isolation, only speed differs, and both builds produce bit-identical results. *Rejected:* refusing to run without isolation (breaks embeds and misconfigured servers); a single-threaded web product (wastes cores on every Tier 1 browser).

**Decision D-PLT-10:** The threaded web engine builds with a nightly toolchain pinned per release and `-Zbuild-std`; every other artifact builds with pinned stable Rust. *Why:* wasm-bindgen-rayon documents that thread support "is still only available in nightly", and Rust's specified float semantics make results independent of the compiler version, which the determinism suite verifies. *Rejected:* a hand-written worker runtime without `std` threads (large, duplicative); dropping browser threads (a 4 to 16 times loss on multi-core machines).

`same-origin` severs references to cross-origin popups, which breaks popup sign-in (R6-45). Sign-in therefore redirects to a non-isolated page on Crucible's origin that completes the authorization-code exchange with PKCE, keeps the token as a non-extractable WebCrypto key and redirects back.

The web build requires SIMD128 (Chrome 91, Firefox 89, Safari 16.4), threads (74, 79, 14.1) and bulk memory (75, 79, 15) statically, per the WebAssembly feature table. Relaxed SIMD, memory64, exception handling and JS Promise Integration are not used.

### Memory

A wasm32 engine addresses at most 4 GiB. memory64 caps at 16 GiB in the JS API, ships in Safari only in Technology Preview, and costs 10% to over 100% in SpiderMonkey's measurements.

**Decision D-PLT-11:** The browser engine stays wasm32 and handles large models through out-of-core chunks in OPFS, a disposable heavy worker and remote evaluation. *Why:* memory64 is missing in Safari, costs speed everywhere and still caps at 16 GiB, while out-of-core storage and remote evaluation scale further. *Rejected:* a memory64 build for Chrome and Firefox only (two behaviors for one Tier 1 target). It is revisited when Safari ships memory64 and the penalty on the PLT suite falls below 10%.

WebAssembly memory "can only grow and never shrink", and the memory-control proposal "is in its early stages", so one large evaluation would pin the engine worker at its peak (R6-14).

**Decision D-PLT-30:** The engine worker keeps a fixed linear-memory cap, and every evaluation estimated above 512 MiB runs in a disposable heavy worker that writes results to the OPFS CAS and terminates, returning its memory; larger evaluations are offered to a team server or cloud worker. *Why:* termination is the only way a browser releases Wasm memory, and one table replaces the conflicting KLN, UIX and round 1 numbers. *Rejected:* one growing engine worker (idle memory never recovers); memory64 (D-PLT-11).

The browser memory table of contract section 9, proposed until phase 0 measures kill thresholds (open question 3):

| Context | Cap or target | Rule |
| --- | --- | --- |
| UI module | 512 MiB linear memory | UIX owns the contents |
| Engine worker | 1.5 GiB linear memory | Kiln evicts to OPFS; a larger reservation routes the evaluation to the heavy worker |
| Heavy worker | min(4 GiB, kill threshold − UI cap − engine cap − 512 MiB) | One at a time, terminated after each evaluation |
| Idle, UI plus engine | 300 MiB after a heavy-worker recycle | Contract section 13.3 memory row |
| GP1 open | 1.5 GiB of linear memory in total | Same row |
| Suspended feature calls | 500 at once in 256 MiB of the engine cap (ING) | Memory reserved as used, never the declared maximum (R3-33) |

### Storage, hashing and updates

The CAS, journal and package cache live in OPFS, whose synchronous handles work only in dedicated workers. Quotas range from about 60% of disk in Chrome, Edge and Safari to the smaller of 10% or 10 GiB in Firefox, and Safari deletes script-written data after seven days without interaction.

The engine requests persistence at first use and treats the browser CAS as a cache, with the team server or a user-chosen folder as source of truth [File System Access API coverage unverified]. Unsynced edits show a "not yet synced" indicator, with Safari's seven-day warning where persistence is denied.

The browser CAS hashes chunks of at most 1 MiB with `crypto.subtle.digest`, which "does not support streaming input", and KLN's index nodes combine the digests; a Wasm SHA-256 serves small synchronous objects (R6-44). The target is 1 GiB in 1 s across 8 workers.

A service worker caches the shell, both engine builds, fonts and std packages under content-hashed URLs and activates a new version only on the next load or with consent. Each release's asset manifest is listed in TUF targets and a transparency log and verified before activation (R5-12); the first visit still trusts HTTPS and Subresource Integrity.

Jangda and colleagues measured browsers 45% to 55% slower than native on SPEC CPU (USENIX ATC 2019), and WebAssembly cut Figma's load time more than three times. Targets (R6-33, R6-38): the suite within 2.0 times native single-threaded and 2.5 times multi-threaded, and SIMD-heavy kernels within 3 times.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Two web builds | Threaded when `crossOriginIsolated`, single-threaded otherwise; identical hashes | Status bar: "Threads unavailable: the site is not cross-origin isolated" | PLT-O-WEB-1 | 0 |
| Sign-in under isolation | Redirect-based authorization code with PKCE | Popup flows never offered on isolated pages | PLT-O-WEB-1 | 1 |
| One engine per origin | Web Lock owner holds every OPFS write handle | Owner closes: next tab takes the lock and replays | PLT-O-WEB-2 | 1 |
| Browser memory table | Engine cap; heavy worker above 512 MiB; remote beyond | Over the cap: heavy worker, or a `ResourceExhausted` Abort with a remote offer | PLT-O-WEB-3 | 1 |
| OPFS storage | Persistence requested; CAS as cache; sync indicator | Eviction: refetch; local-only edits warned | PLT-O-WEB-3 | 1 |
| Chunk hashing | `crypto.subtle.digest` per chunk, native-identical `ObjectId`s | Digest failure: Wasm SHA-256 | PLT-O-WEB-5 | 1 |
| Verified updates | TUF-verified manifest before activation | Failure keeps the running version and reports | PLT-O-WEB-4 | 1 |
| GPU path selection | WebGPU where available, WebGL2 and CPU compute otherwise | "WebGPU unavailable in this browser", same features | PLT-O-DET-1 | 1 |
| Startup and payload | Warm 2.5 s; first visit 8 s; 25 MiB initial Wasm (contract section 13.3) | A missed row blocks beta promotion | PLT-O-PERF-1 | 1 |
| Browser speed | Suite ratios 2.0 and 2.5; SIMD-heavy 3 | Regression filed nightly | PLT-O-PERF-3 | 1 |

## The compute runtime

The `runtime`, `simd`, `gpu` and `linalg` crates execute what Kiln schedules, and no choice of cores, vector units or GPUs changes a canonical result.

**Decision D-PLT-12:** The UI always talks to the engine through the `api` transport, and the engine runs as a separate OS process on desktop, a dedicated worker in browsers, threads on tablets (with Wasm in WebKit on iPadOS, D-PLT-33) or a remote `server`. Third-party native code and third-party Wasm components run in sandboxed processes outside the engine (D-PLT-31). *Why:* one boundary keeps the UI code identical, and an engine crash, out-of-memory kill or driver fault leaves the window intact while the engine restarts and replays its journal. *Rejected:* a single desktop process (an engine crash closes the window); one process per Op (start and copy costs exceed the drag-preview row). (revised in round 2)

Desktop UI and engine processes share memory-mapped rings for tessellations and Field samples and exchange `api` messages over a local socket. On Linux a higher `oom_score_adj` makes the kernel stop the engine rather than the window. Licensed translators run outside evaluation in a sandboxed translator host (contract section 7.7), and external MCP servers that agent sessions start over stdio run in the same OS sandbox (D-PLT-31) with only their pipes and user-granted folders.

[[DIAGRAM diagrams/12-platform-process-model.jsx: process and thread model · four targets]]

### Threads and pools

| Thread or pool | Size | OS priority | Work |
| --- | --- | --- | --- |
| IO runtime (tokio natively, the event loop in browsers) | 2 workers plus a blocking pool | Normal | IPC, network, file IO outside the CAS fast path |
| Foreground pool (rayon) | One per logical core | QoS user-interactive, Windows normal, nice 0 | Drag previews, selection queries, `Preview` results |
| Background pool (rayon) | One per logical core, halved on battery | QoS utility, below-normal with EcoQoS, nice 10 | Rebuilds, `SignOff` work, prefetch |
| GPU queue thread | One per device | User-interactive | Encoding, submission, readback, device loss |

Kiln maps AGT's interactive `PriorityClass` to the foreground `PoolLane`, promotes a waiting background Op that has not started, and calls `ComputePool::boost` for one that has.

Operations are pure and read data only through the residency manager. Compute never runs on IO workers or calls `block_on`, and the browser engine worker awaits pools through `Atomics.waitAsync` where available [per-browser `waitAsync` support unverified]. `OpCx` checks cancellation at every chunk boundary and fuel check, and a cancelled Op ends in an Abort, never cached.

A foreground Op starts within 2 ms at p99 while both pools are busy (target); scheduling chunks of 0.1 to 1 ms never change a reduction tree. Ops estimated above 10 core-seconds take a deterministic work budget derived from AGT's `Budget` (D-AGT-29) and reach a safe point at least every 10 core-seconds; reaching the budget is an Abort (R6-29).

**Decision D-PLT-13:** CPU parallelism uses rayon work-stealing pools, one per `PoolLane`, with all result-affecting parallelism expressed through Crucible's deterministic combinators. *Why:* rayon is the standard Rust work-stealing runtime and supports browsers through wasm-bindgen-rayon; the combinators remove any dependence of results on thread count or stealing order. *Rejected:* tokio for compute (cooperative futures starve under long kernels); a custom scheduler (no gain at Op granularity).

### Deterministic parallel combinators

| Combinator | Contract | Order guarantee |
| --- | --- | --- |
| `det_for_each_chunk`, `det_map_collect` | Disjoint ranges; parallel map | No result-affecting shared state; output in input order |
| `det_sum`, `det_reduce` | Pairwise reduction | Blocks of 2,048 elements; canonical lane i of 8 (f64) or 16 (f32) accumulates elements i, i + L, …, lanes reduce by a balanced tree over lane indices, and blocks by a balanced tree splitting n blocks at ⌈n/2⌉ |
| `det_scan` | Prefix scan | Fixed blocks and block-offset tree |
| `det_sort_by_key` | Stable sort | Keys implement `Ord`; floats only as `NonNan<f64>`; ties keep input order, never a name-derived id (contract section 7.1) |
| `exact_sum` | Partition-independent sum | Binned accumulation (ReproBLAS), only where partitions vary, such as across ranks |

Binned summation costs about 4 times a plain dot product (ReproBLAS), so node-local reductions use `det_sum` (R6-35). Clippy forbids float reductions on rayon iterators, thread-count queries, `std` hash maps, `usize` in hashed data and address-dependent results.

### Memory

| Mechanism | Choice | Failure behavior |
| --- | --- | --- |
| Allocator | mimalloc v3 natively; Rust's wasm32 allocator in browsers, compared with mimalloc in phase 1 | `try_reserve` failure: `ResourceExhausted` Abort |
| Budgets | `MemoryBudget` tree for CAS residency, GPU staging and Op scratch; reserve above 64 MiB | Waits 2 s for eviction, then `ResourceExhausted { requested, available, fix }` |
| Scratch | A `bumpalo` arena per Op execution | Counts against the reservation |
| Mapped CAS objects | Read-only maps for objects of 1 MiB or more | Network file system: buffered reads |
| Out-of-core buffers | `ChunkedBuffer<T>`: 1 MiB CAS chunks, CLOCK eviction, index-order visits | Hash mismatch: `CasError::Corrupt`, recomputed |

**Decision D-PLT-14:** mimalloc v3 is the native global allocator. *Why:* it is MIT-licensed, ported to every Tier 1 OS and Wasm, and its project reports outperforming jemalloc and tcmalloc on multi-threaded benchmarks, while noting those numbers date from 2021. *Rejected:* system allocators (behavior differs per OS); jemalloc (no Windows support in the common Rust bindings [unverified]). Phase 0 re-measures mimalloc, jemalloc and snmalloc; the choice cannot affect results.

Windows refuses to delete mapped files, so CAS garbage collection defers them; a mapped file truncated by another program raises SIGBUS on Unix, and the restarted engine quarantines it.

### GPU dispatch and resource usage

**Decision D-PLT-32:** One dispatch rule holds for every engine GPU path: at most 4 ms per dispatch while any window renders interactively, 16 ms while views are idle and 100 ms only in headless processes, measured with timestamp queries. Display-only GPU work (per-pixel Field evaluation, implicit preview, display isosurfaces) runs on the UI process's device from coefficient buffers passed through the mapped rings, and the engine creates its device lazily. *Why:* the engine and renderer share one GPU that the OS arbitrates, and wgpu offers external memory only on Vulkan, so on DX12 and Metal shared buffers would cross host memory twice (R6-16). *Rejected:* separate KLN, FLX and PLT limits (50, 4 and 100 ms); engine-side display evaluation.

A split dispatch covers more fixed tiles, never a different reduction topology, and UIX states a copy budget for buffers that cross processes.

The runtime measures AGT's `Usage` fields per Evaluation (core seconds, GPU seconds, memory GiB-seconds, CAS bytes) plus fuel; GPU seconds come from timestamp queries and are unattributed when the renderer shares the device (R6-29).

```rust
pub enum PoolLane { Foreground, Background }
impl ComputePool {
    pub fn spawn<R: Send + 'static>(&self, lane: PoolLane, cx: OpCx, f: impl FnOnce(&OpCx) -> R + Send + 'static) -> ExecHandle<R>;
    pub fn boost(&self, exec: ExecId);
}
pub fn det_sum(cx: &OpCx, xs: &[f64]) -> Result<f64, Aborted>;
pub fn det_sort_by_key<T: Send, K: Ord + Send>(cx: &OpCx, xs: &mut [T], key: impl Fn(&T) -> K + Sync) -> Result<(), Aborted>;
pub fn exact_sum(xs: &[f64]) -> f64;
impl MemoryBudget { pub fn reserve(&self, bytes: u64, wait: Duration) -> Result<Reservation, ResourceExhausted>; }
```

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Engine placement | Process, worker, tablet threads or remote server | Engine crash: restart and journal replay, window intact | PLT-O-REL-2 | 0 |
| stdio MCP server sandbox | External MCP servers in the D-PLT-31 sandbox, pipes and granted folders only | Access outside the grant denied and logged | PLT-O-WASM-6 | 1 |
| Pools and lanes | Two rayon pools by `PoolLane`; promotion and boost | Start beyond 2 ms at p99 fails the oracle | PLT-O-RT-1 | 0 |
| Deterministic combinators | Data partitions, fixed trees, canonical lane order | Divergence fails the suite | PLT-O-DET-2 | 0 |
| Combinator lints | Five Clippy rules in operation crates | Lint failure blocks the merge | PLT-O-DET-5 | 0 |
| Cancellation and safe points | Chunk boundaries and fuel checks; safe points every 10 core-seconds | Abort, never cached | PLT-O-WASM-3 | 0 |
| Memory budgets and allocator | Reservation tree; mimalloc v3 | `ResourceExhausted` Abort with a fix | PLT-O-RT-2 | 0 |
| Out-of-core buffers | Identical results in and out of core | `CasError::Corrupt`, recomputed | PLT-O-DET-3 | 1 |
| GPU dispatch rule | 4, 16 and 100 ms; display work on the UI device; lazy engine device | Overlong dispatch split; repeated resets disable GPU compute | PLT-O-GPU-4 | 1 |
| Resource usage | AGT's `Usage` fields plus fuel | Shared GPU: GPU seconds unattributed | PLT-O-RT-3 | 1 |

## SIMD, GPU and linear algebra

### SIMD

`std::simd` remains nightly-only and Arm SVE experimental (rust-lang/rust#145052). `simd` detects the instruction set once at startup and dispatches through a function table; `CRUCIBLE_ISA` forces a lower level for tests and never changes canonical bits.

**Decision D-PLT-15:** Canonical kernels fix the order of every horizontal operation: each reduction, scan or cross-lane operation in `Portable` code follows the 8-lane f64 or 16-lane f32 tree of `det_sum` on every instruction set, while element-wise code uses any native vector width. *Why:* only horizontal operations depend on lane count, and fixed 512-bit virtual vectors occupy four of the 16 vector registers on x86-64-v2 and SIMD128, which forces spills (R6-18). *Rejected:* fixed 512-bit virtual vectors for all code (round 1); native-width reductions (bits change with the ISA); scalar canonical code (forgoes 2 to 8 times the throughput). (revised in round 2)

An intrinsic allow-list keeps approximate instructions such as `rcp14` and `FRECPE` out of canonical kernels. Dispatch uses pulp, and phase 0 evaluates fearless_simd 1.0, which promises "3 years of security updates", as its replacement (R6-30); SVE waits for stable scalable vectors in Rust.

### GPU compute

WGSL lets compilers reassociate and "fuse operations if the transformed expression is at least as accurate", and gives `fma` an accuracy "Inherited from `x * y + z`". Implementations may also "assume that overflow, infinities, and NaNs are not present" and flush subnormals (WGSL Candidate Recommendation Draft, 21 September 2026). GPU bits therefore belong to one compiled pipeline, never the canonical class (R1-09).

**Decision D-PLT-16:** GPU kernels come from the shared kernel IR (FLX) through WGSL on wgpu. The `gpu` crate owns devices, buffers, pipeline creation, integer exact reductions, known-answer tests, workarounds and device-loss recovery, and every GPU path is registered with its CPU path. *Why:* contract section 7.5 makes the kernel IR the single kernel source, CubeCL is alpha with breaking changes between minor versions, and WGSL allows verification only per pipeline (R6-22). *Rejected:* CubeCL as the kernel language (reconsidered with CUDA or HIP at the phase 4 gate); hand-written WGSL plus CUDA (two sources that drift); CUDA first (no Apple GPUs or browsers). (revised in round 2)

Each GPU path declares one role:

- **GPU filters, CPU decides** (`Certified`): the GPU narrows candidates under a certified bound and canonical CPU code decides, as in Anvil's SSI sampling.
- **`Interactive`** (`ClassExact`): results are cached only under their `Gpu` class.
- **GPU solves, CPU certifies:** a check rests on the pinned Field only with a canonically computed residual and bound (contract section 7.3; D-FLX-17).

Every role relies on four `gpu` mechanisms:

1. **Known-answer tests.** Each compiled pipeline reproduces its class's recorded outputs at creation and after driver or OS updates; failure falls back to the CPU and proposes a workaround entry.
2. **Integer exactness.** Exact results use integers, such as D-FLX-18's 32-bit-limb reductions; no float atomics, and compaction by prefix sums.
3. **Non-finite detection on the CPU.** Read-back exponent bits are inspected as integers, because in-shader NaN checks may be compiled away.
4. **Math functions.** Fixed-sequence approximations with documented ulp bounds, never vendor built-ins (D-FLX-11).

wgpu exposes `SHADER_F64` only on Vulkan, so `f64` GPU paths are Vulkan server paths from phase 3 (FLX). Without a usable adapter or in safe mode, Kiln records `ran_on: Cpu` with the reason.

```rust
pub enum GpuRole { FilterCpuDecides, Interactive, CpuCertified }
pub struct GpuPath<I, O> {                     // no GPU-only capability exists
    pub id: &'static str, pub role: GpuRole,
    pub gpu: fn(&OpCx, &dyn GpuCompute, &I) -> Result<O, GpuError>,
    pub cpu: fn(&OpCx, &I) -> Result<O, Aborted>,
}
pub enum RanOn { Gpu(GpuClass), Cpu { reason: CpuReason } }
```

### Canonical linear algebra

faer's dense kernels come from `gemm`, whose `kernel_params` derives the reduction block from L1 geometry read at run time, and which has FMA microkernels. faer 0.24.4 documents "cpu feature detection at runtime" and nothing on reproducibility (R1-10, R6-21).

**Decision D-PLT-34:** `linalg`, owned by PLT with FLX, is the only linear algebra in `Portable` code: dense kernels (GEMM, LU, Cholesky, QR, SVD, triangular solves) with fixed machine-independent blocks, the canonical horizontal order, no FMA and index-ordered pivot ties, and FLX's canonical supernodal factorization (D-FLX-36). Unmodified faer runs only in `CpuIsa` classes with cache detection pinned. *Why:* cache-derived blocks make sums machine-dependent even within one ISA, and MEC's constraint solver, ELX's circuit LU and COV's calibration fits need `Portable` results (R2-15). *Rejected:* unmodified faer in the canonical class; a permanent faer and `gemm` fork (a single-maintainer code base built around FMA; a deterministic mode is offered upstream instead).

The dense target is within 2.5 times faer's `CpuIsa` time for n ≥ 1,000; sparse targets are FLX's.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| ISA dispatch | Detection once; forced levels for tests | Unsupported forced level: startup error naming the detected level | PLT-O-DET-1 | 0 |
| Canonical horizontal order | `det_sum` lane tree for every horizontal operation | Divergence fails the suite | PLT-O-DET-1 | 0 |
| Intrinsic allow-list | No approximate instructions in canonical kernels | CI rejects the intrinsic | PLT-O-DET-5 | 0 |
| GPU paths with CPU paths | Three roles; `RanOn` reported | No adapter, blocklist or safe mode: CPU path with the reason shown | PLT-O-GPU-3 | 1 |
| Known-answer tests | Per pipeline at creation and after driver or OS updates | CPU fallback and a proposed workaround | PLT-O-GPU-1 | 1 |
| Exact GPU primitives | Integer-limb reductions, prefix-sum compaction, no float atomics | Non-identity fails the oracle | PLT-O-GPU-3 | 1 |
| Non-finite detection | Integer inspection after readback | Typed numerical `Failure` naming the kernel | PLT-O-GPU-3 | 1 |
| `f64` GPU server paths | Vulkan `SHADER_F64`, certified on the CPU | Missing feature: CPU path, reported | PLT-O-GPU-1 | 3 |
| Canonical dense linear algebra | Fixed blocking, no FMA, index-ordered pivot ties | Divergence fails the suite | PLT-O-LA-1 | 0 |
| Canonical sparse factorization | FLX's supernodal elimination, thread-count independent | As above | PLT-O-LA-1 | 1 (sequential), 2 (parallel) |
| faer in `CpuIsa` | Pinned cache detection; never in `Portable` code | Lint rejects faer in `Portable` operations | PLT-O-DET-5 | 1 |
| Linear algebra speed | Dense within 2.5 times faer `CpuIsa` | Regression filed nightly | PLT-O-LA-2 | 1 |

## Numerical determinism

This section owns the mechanisms, classes, agreement and the suite, and engine tabs keep at most 150 words of their own rules (R3-37).

### Sources of divergence and their controls

| Source | Evidence | Control |
| --- | --- | --- |
| Implicit contraction | RFC 3514 excludes implicit FMA in Rust; Box2D found FMA "must be disabled for cross-platform determinism" in C and C++ | Linked C and C++ build with `-ffp-contract=off` and no fast-math, checked in CI |
| Explicit FMA | `mul_add` runs in software on x86-64-v2 and wasm32 | Only inside `detmath` and error-free transformations in canonical code (D-PLT-18) |
| Platform math | Rust documents `exp`, `sin`, `powf` and others as varying "by platform, Rust version" | `detmath` only; Clippy forbids the std methods |
| Reduction order and width | Addition is not associative; lane counts differ | Combinators; canonical horizontal order (D-PLT-15) |
| Approximate instructions | Reciprocal estimates differ by ISA | Intrinsic allow-list |
| Cache-dependent blocking | `gemm` sizes blocks from detected caches | `linalg` (D-PLT-34) |
| Floating-point environment | Foreign code may set flush-to-zero or rounding, undefined behavior per RFC 3514 | No driver or foreign native code on compute threads; MXCSR or FPCR checked at Op start and end; a change at the end is an Abort, and the Op reruns (R1-55) |
| NaN bit patterns | Sign and payload are nondeterministic in Rust and WebAssembly | Canonical NaN in the CAS; the determinizer for Wasm |
| Relaxed SIMD | `relaxed_madd` may round once or twice | Never used; rejected in Wasm |
| Hashes, `usize`, addresses, threads | Hash values differ by pointer width; stealing reorders work | Combinator lints |
| Names in orderings | Label invariance (contract section 7.1) | Sort ties keep input order; canonical numbers come from geometry |
| GPU arithmetic | WGSL may reassociate, fuse, flush and assume finite values | Per-pipeline classes; known-answer tests; integer exactness; CPU non-finite detection |
| Toolchain upgrades | Code-generation bugs | The suite runs on every bump; a changed hash blocks it or bumps the epoch |

### The deterministic math library

`detmath` provides f64 and f32 elementary functions, scalar and batched: exponentials, logarithms, powers, roots, `hypot`, circular and hyperbolic functions and inverses, `erf`, `erfc`, `tgamma` and `lgamma`. `sqrt`, division and basic operations come from IEEE 754 hardware.

**Decision D-PLT-17:** `detmath` returns correctly rounded results in round-to-nearest wherever CORE-MATH provides correctly rounded code, and otherwise a fixed sequence of IEEE basic operations with a documented ulp bound. By month 3 of phase 0, CORE-MATH's C sources (MIT) build behind the `detmath` API with clang and `-ffp-contract=off` on every target, wasm32 included; functions then move to Rust one at a time, hot ones first (`exp`, `ln`, `pow`, `sin`, `cos`, `atan2`), and batched paths are compared with crmvec. *Why:* a correctly rounded result is unique, so scalar, batched, FMA and FMA-free paths return the same bits, and the C build unblocks the suite while the port proceeds (R6-19). *Rejected:* platform libm (nondeterministic); porting musl or FreeBSD libm (not correctly rounded, so optimizations risk changing bits); Box2D-style approximations (too inaccurate for CAD); waiting for a complete Rust port. (revised in round 2)

Without hardware FMA, the C build's correctly rounded `fma` keeps the bits at lower speed. The C build sits in `bridges/core-math` behind safe functions, so `detmath` stays free of `unsafe` (contract section 12).

glibc 2.43 integrates seven CORE-MATH binary64 functions and AMD libm 4.2 its `tanhf`, so speed targets are Crucible's own. On x86-64-v3, `exp` and `ln` stay within 1.5 times and `pow`, `sin` and `cos` within 2 times glibc 2.43; wasm32 stays within 3 times native, and batched paths reach at least 2 times scalar on AVX2.

**Decision D-PLT-18:** No implicit contraction exists anywhere, and explicit `mul_add` appears in canonical code only inside `detmath` and error-free transformations. A kernel family that loses more than 1.3 times without FMA may ship a `CpuIsa` variant with FMA for `Preview` and `Interactive` results; `SignOff` recomputes canonically, and Kiln's cost model counts the recompute. *Why:* x86-64-v2 and wasm32 lack FMA, while compute-bound kernels elsewhere halve their peak without it (R6-17). *Rejected:* FMA in canonical kernels (software FMA in browsers); no FMA anywhere (loses error-free transformations and fast previews); FMA variants at `SignOff` (contract section 7.3). (revised in round 2)

### Platform classes

**Decision D-PLT-19:** One canonical CPU class, `CpuCanonical { epoch }`, spans every Tier 1 CPU target, browsers included, at any thread count and ISA level, and the operating system is never part of a CPU class. A GPU class is one compiled pipeline on one verified device class: back end, device family, driver build, shader-compiler build (the OS build on Apple platforms) and pipeline hash. *Why:* with no OS-dependent arithmetic left, one CPU class lets browsers, laptops, cloud workers and CI share every cached result, while WGSL lets each compiler reassociate and fuse differently (R1-09, R1-44). *Rejected:* one class per OS and architecture (multiplies misses, hides bugs behind class boundaries); GPU classes keyed by back end or vendor alone. (revised in round 2)

```rust
pub enum PlatformClass {                          // in base; owned by PLT
    CpuCanonical { epoch: u16 },
    CpuIsa { isa: IsaLevel, epoch: u16 },          // X86_64V2..V4, Arm64Neon, Wasm32Simd128
    Gpu(GpuClass),                                 // a registry entry: device class plus pipeline
    Unverified { fingerprint: [u8; 16] },          // unlisted devices and external hosts
}
```

The verified-class registry is a signed data file built from GPU-lab runs; unlisted devices are `Unverified`. An epoch bump needs human approval and an LTS boundary unless it fixes wrong results, and `cli` reproduces an old release by running the archived engine of its epoch.

**Decision D-PLT-20:** Results of `CpuIsa`, `Gpu` and `Unverified` classes never substitute for canonical results; a check, release or Proposal that requires canonical results recomputes them in the canonical class. The one exception is contract section 7.3's: a check may rest on a pinned non-canonical Field when its residual and error bound are computed canonically from that Field. *Why:* substitution would make a release depend on the machine that computed it first, while canonical certification keeps the verdict canonical. *Rejected:* any class within tolerance (irreproducible releases); no exception (forfeits GPU solves the CPU certifies cheaply). (revised in round 2)

Invalid numerics are typed `Failure`s; where NaN is a legitimate value, the CAS serializer writes the canonical quiet NaN, and a lint forbids inspecting NaN bits elsewhere.

### Cross-class agreement

**Decision D-PLT-35:** Two classes A and B agree on a checked quantity q when |q_A − q_B| ≤ E_A + E_B, where E is q's `ErrorBudget` total in q's norm plus an absolute floor scaled by the Field norm. The harness reports the ratio |q_A − q_B| / (E_A + E_B), a ratio above 1 also fails the owning tab's effectivity oracle, and bifurcating problems compare branch-invariant quantities and chaotic ones declared statistics (principle 4). *Why:* a residual bounds forward error only through the condition number, adaptive runs refine differently per class, and ulp tolerances mean nothing near zero (R1-12, R1-13). *Rejected:* round 1's per-class residual rule and FLX's larger of residual and 100 ulp; hand-set tolerances per operation.

FLX applies the same rule (FLX-O-ERR-10); B-rep Bodies must first match in topology and canonical entity numbers. The harness runs nightly, comparing every `CpuIsa` and verified `GpuClass` with canonical results.

### The determinism suite

The suite runs on every merge on the representative set and nightly on every other Tier 1 target and browser (contract section 7.3). The representative set is Linux x86-64 at v2, v3 and v4, Linux ARM64, macOS ARM64, and wasm32 in Node and headless Chrome, threaded and not.

1. **Corpus.** Golden products, ANV and FLX corpora, Wasm components and 10,000 random operation graphs a night.
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
| Mechanism table | One control per divergence source, cited by every engine tab | A source found by the suite adds a row | PLT-O-DET-1 | 0 |
| `detmath` C build | CORE-MATH C on every target by month 3 | Missing function fails the build, never a platform fallback | PLT-O-DET-4 | 0 |
| `detmath` Rust ports | Hot functions first; batched paths | A port differing from the C build in any bit is rejected | PLT-O-DET-4 | 0 to 1 |
| `detmath` speed | Per-function targets | Regression filed nightly | PLT-O-DET-8 | 1 |
| FMA variants | `CpuIsa` kernels above a 1.3 times penalty; never at `SignOff` | Divergence beyond the agreement rule disables the variant | PLT-O-DET-6 | 1 |
| Floating-point environment guard | Checked at Op start and end | Abort and rerun, culprit logged | PLT-O-DET-7 | 0 |
| Platform classes | Four variants in `base`; signed GPU registry | Unlisted device: `Unverified`, local cache only | PLT-O-DET-1 | 0 |
| Epochs and archived engines | Approved bumps; archived builds reproduce old releases | Missing archive: agreement-rule comparison, reported | PLT-O-BLD-3 | 2 |
| No substitution | Canonical recomputation with contract section 7.3's exception | Uncertified non-canonical input: check is `Undecided` | PLT-O-DET-6 | 1 |
| NaN canonicalization | Canonical quiet NaN in the CAS | Lint failure blocks the merge | PLT-O-DET-5 | 0 |
| Cross-class agreement | \|q_A − q_B\| ≤ E_A + E_B, ratio reported | Ratio above 1 fails nightly | PLT-O-DET-6 | 1 |
| Determinism suite | Representative set per merge, the rest nightly, automatic bisection | Nightly divergence: severity-1 incident, beta blocked | PLT-O-DET-9 | 0 |

## Wasm component runtime

Wasm components give bit-identical results in Wasmtime, browser engines and JavaScriptCore, because the one determinizer of contract section 7.4 fixes their semantics in the bytecode.

WASI 0.3.0 shipped on 11 June 2026. Wasmtime releases monthly, "Each release that is a multiple of 12 is considered an LTS release and is supported for 24 months", and only security fixes are guaranteed on every supported release. Its 2026 advisories include an out-of-bounds write in Component Model string transcoding (GHSA-394w-hwhg-8vgm) and leakage between pooling-allocator instances (GHSA-6wgr-89rj-399p).

**Decision D-PLT-21:** Crucible embeds Wasmtime pinned to LTS releases (48 from phase 0, then 60), applies Wasmtime security releases within 7 days on every supported Crucible line, and moves between LTS releases only after the determinism suite passes. *Why:* the 24-month window matches Crucible's LTS channel, and only security fixes are guaranteed upstream (R5-09). *Rejected:* tracking monthly releases (each recompiles every cached Wasm component); Wasmer (smaller ecosystem around the Component Model and WASI 0.3 [unverified]). (revised in round 2)

### The determinizer

`wasm-host` holds the determinizer, `determinize@N`, which the registry runs at publish and the local toolchain at build. Hosts execute only determinized binaries, whose hash enters the `OpKey` (contract section 7.2).

| Step | Problem it removes |
| --- | --- |
| Validation; rejection of relaxed SIMD, shared memories, atomics and forbidden imports | Results that differ between calls or threads |
| Fuel metering per basic block; the check also reads a host cancellation word or, without shared memory (the single-threaded web build), yields to the host every fixed number of fuel units | Engines meter differently; cancellation must land at the same points everywhere (R3-21) |
| A logical stack-depth limit below the smallest real stack of any engine | Engine-dependent stack overflow |
| NaN canonicalization only where bits become observable: float stores, `reinterpret`, the sign operand of `copysign`, host-call arguments and results, and v128 values from float operations reaching bitwise, integer-lane, shuffle, store or extract-to-integer instructions, found by forward type tracking | Nondeterministic NaN payloads, which arithmetic, comparisons, `min`, `max` and conversions never expose (R6-20) |
| Guarded `memory.grow` and `table.grow`: host-caused failure below the declared maximum traps with a host-failure marker | `memory.grow` may "non-deterministically succeed or fail" |

Ingot code generator output is verified, not rewritten (R3-51). Verification requires no forbidden instructions or imports, a fuel decrement dominating every loop back-edge and entry, a non-finite check before every observable float use, and a depth counter in every prologue.

**Decision D-PLT-22:** Fuel, cancellation, stack limits, NaN canonicalization and growth guards are enforced by the determinizer in bytecode, identically on every engine. Wasmtime's epoch mechanism is never used, and its built-in fuel only cross-checks tests. *Why:* browsers can neither meter fuel nor canonicalize NaNs, Wasmtime's fuel costs change between releases, and canonicalizing every float result adds two or three instructions per float SIMD operation. *Rejected:* engine-side fuel and NaN switches (native only); epochs (nondeterministic by Wasmtime's own documentation); canonicalizing every NaN-producing instruction (round 1's cost). (revised in round 2)

PLT publishes the overhead table ECO cites (contract section 7.4), measured per Wasm component class against undeterminized binaries in Wasmtime: scalar-float at most 10%, SIMD-float at most 25%, fuel and stack metering at most 10%. Determinized Wasm components target 1.6 times native Rust in Wasmtime and 2.5 times in browsers (R6-33).

### Executors

| Target | Executor | Notes |
| --- | --- | --- |
| Native Tier 1 | Wasmtime LTS, Cranelift at `OptLevel::Speed` | Compiled at install with `Engine::precompile_component` into the local CAS, keyed by binary, Wasmtime version, `Config`, target and CPU features; only locally compiled or Crucible-signed artifacts load |
| Browsers | One first-party runtime in the browser's engine | D-PLT-36 |
| iPadOS | JavaScriptCore in WebKit; Pulley fallback | D-PLT-33 |
| Android | Wasmtime with Cranelift | No Android API imports |
| Where Cranelift cannot generate code | Pulley | About ten times slower |

Until the Ingot code generator ships, the reference interpreter is the only Ingot executor (contract section 7.4). Wasmtime runs with relaxed SIMD, threads and memory64 off and a 4 GiB guarded `memory_reservation`. Its resource limiter reserves budget as memory grows, never the declared maximum (R3-33), and pooling slots never cross tenants or label sets.

**Decision D-PLT-36:** Browsers run every Wasm component through one fixed, first-party Wasm component runtime that instantiates determinized core modules from ECO's browser Wasm component description, so no JavaScript ships per Wasm component; unpublished local Wasm components get descriptions from the desktop toolchain or team server, and jco never runs in the browser. *Why:* glue per Wasm component would run in the engine worker's origin with access to OPFS and credentials, and in-browser transpiling adds a toolchain and a second bundle source (R5-12, R6-37). *Rejected:* jco glue per Wasm component; transpiling in the engine worker (round 1).

### Isolation of third-party Wasm components

**Decision D-PLT-31:** Only first-party, hermetically built Wasm components (std and `crucible::`) run in the engine process. Every third-party Wasm component runs in an OS-sandboxed worker process (AppContainer, App Sandbox, or seccomp with Landlock), like the translator host, with no repository handles, tokens or keys, one per (tenant, label set) on servers; in browsers it runs in a worker inside an opaque-origin sandboxed iframe without OPFS, cookies or keys, exchanging data by `postMessage`. *Why:* the engine process holds every open repository and token, and Wasmtime's 2026 advisories include memory-safety and isolation bugs (R5-09, R5-12). *Rejected:* in-process execution for verified publishers (one engine bug exposes everything); isolation only below Wasmtime Tier 2 (round 1's contract section 7.4).

Sandbox workers read bulk data through read-only CAS maps, so a call costs one message plus the canonical-ABI copy of its arguments.

### Worlds, calls and failures

ECO defines the worlds and PLT enforces them: evaluation worlds are synchronous, import no WASI and may import `crucible:ops`, while tool worlds use WASI 0.3 outside evaluation. Any other import fails at install with `ForbiddenImport { import, fix }` naming the world that grants it.

| Event | Kind | Cached |
| --- | --- | --- |
| Trap in Wasm component code | `Failure`: `Trap { code, function, fix }` | Yes |
| The call's own fuel limit | `Failure`: `FuelExhausted { used, limit }`, deterministic under one determinizer version | Yes |
| Logical stack limit | `Failure`: `StackExhausted { limit }` | Yes |
| Growth beyond the declared maximum | Standard Wasm: `memory.grow` returns −1 | Decided by the Wasm component |
| Host memory unavailable below the maximum; Evaluation fuel or budget exhausted; cancellation; sandbox worker lost | Abort | Never |

Data beyond 4 GiB moves through chunked buffers, and data parallelism through exported chunk functions run on separate instances and merged in index order.

```rust
pub trait WasmComponentEngine: Send + Sync {   // Wasmtime, sandbox worker, browser runtime, WebKit
    fn install(&self, determinized: &[u8], world: &WorldSpec) -> Result<InstalledWasmComponent, WasmComponentError>;
    fn instantiate(&self, c: &InstalledWasmComponent, limits: CallLimits) -> Result<Box<dyn WasmInstance>, WasmComponentError>;
}
pub struct CallLimits { pub fuel: u64, pub stack_frames: u32, pub max_memory_bytes: u64 }
```

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Determinizer | Validation, fuel with cancellation, stack limit, observable-NaN canonicalization, growth guards | `InvalidComponent { reason }` | PLT-O-WASM-1 | 0 |
| Observable-NaN canonicalization | Only at the listed observation points | Divergence fails the oracle | PLT-O-WASM-4 | 0 |
| Verification of Ingot modules | Four structural checks | Verification error naming the function | PLT-O-WASM-5 | 2 |
| Overhead table | Scalar-float 10%, SIMD-float 25%, metering 10% | Regression filed nightly | PLT-O-WASM-2 | 0 |
| Wasmtime LTS embedding | Pinned LTS; security releases within 7 days | An unpatched advisory blocks the release | PLT-O-WASM-1 | 0 |
| Ahead-of-time compilation | At install; trusted artifacts only | Unknown artifact: recompiled locally | PLT-O-WASM-1 | 0 |
| Browser Wasm component runtime | One first-party runtime; registry-built descriptions, no JavaScript per Wasm component | Missing description: fetched from the toolchain or team server | PLT-O-WASM-1 | 1 |
| Third-party isolation | Sandbox processes natively, opaque-origin workers in browsers | Lost worker: Abort for its calls | PLT-O-WASM-6 | 1 |
| Cancellation | Only at fuel checks, in every executor | Abort, never cached | PLT-O-WASM-3 | 0 |
| Failure taxonomy | Deterministic `Failure`s cached, Aborts never | A cached Abort fails the oracle | PLT-O-WASM-3 | 0 |
| Worlds | Imports checked at install | `ForbiddenImport { import, fix }` | PLT-O-WASM-6 | 0 |

## Packaging, distribution and updates

Here "app package" means an OS installation format such as MSIX or deb, unrelated to registry packages.

| Target | Format | Signing | Phase |
| --- | --- | --- | --- |
| Windows | MSIX per architecture through the PackageManager API; Intune, Configuration Manager and the Enterprise Modern App Management CSP | Authenticode, HSM-held key | 1; MSI wrapper 2 [MSIX-in-MSI mechanism unverified] |
| macOS | Notarized DMG; `.pkg` for MDM | Developer ID, hardened runtime, stapled ticket | 1; `.pkg` 2 |
| Linux | deb and rpm in apt and dnf repositories; Flatpak and AppImage | Signed metadata expiring within 7 days, enforced by the updater (R5-12) | 1; Flatpak and AppImage 2 |
| Browser | Content-hashed assets and a service worker | Manifest in TUF and a transparency log | 1 |
| iPadOS, Android | App Store, Google Play, managed APKs | Platform signing | 3 |
| Servers and `cli` | OCI images and a Helm chart; `cli` in every desktop package and as signed archives | Image signatures and SLSA provenance | 1 |

The macOS bundle declares `com.apple.security.cs.allow-jit`, which allows memory created "using the `MAP_JIT` flag" that "The Hardened Runtime disallows" by default. Wasmtime uses it whenever it loads or compiles code, so the macOS security review assumes dynamic code in every session (R6-40).

**Decision D-PLT-23:** Windows ships as MSIX. *Why:* MSIX gives clean install and uninstall, package identity (which push notifications and background tasks require), 64 KB block-level differential updates and full Intune and Configuration Manager support. *Rejected:* MSI (no package identity or block updates); a custom installer executable (repeats MSIX).

**Decision D-PLT-24:** Linux ships deb and rpm repositories in phase 1 and adds Flatpak and AppImage in phase 2, all from one binary per architecture linked against the glibc 2.34 floor. *Why:* deb and rpm serve managed fleets and suffice for the wedge (contract section 13.2), Flatpak serves sandboxed installs, and AppImage serves users without administrator rights. *Rejected:* Snap only (Ubuntu-centric); distribution-specific builds; all four formats in phase 1 (R6-02). (revised in round 2)

### Signed updates

**Decision D-PLT-25:** Every self-updating channel verifies updates with The Update Framework (specification 1.0.37), with offline threshold-signed root and targets keys and online snapshot and timestamp keys; OS mechanisms carry the bytes where they exist. Phase 1 installs full signed packages; deltas (MSIX block maps, Zucchini patches for PE and ELF, generic patches for Mach-O) arrive in phase 2. *Why:* TUF defeats indefinite-freeze, rollback, mix-and-match, fast-forward and endless-data attacks and key compromise, and full packages suffice for the wedge (R6-02). *Rejected:* a signed manifest alone; Velopack (no documented freeze or rollback defense); Sparkle (macOS only); deltas in phase 1. (revised in round 2)

| TUF role | Signs | Keys and threshold | Expiry |
| --- | --- | --- | --- |
| Root | Every other role's keys | 3 of 5 offline hardware tokens held by separate people | 1 year |
| Targets | Hashes and lengths per artifact, delegated per channel | 2 of 3 HSM keys | 3 months |
| Snapshot | Versions of all targets metadata | 1 online key | 7 days |
| Timestamp | The snapshot's hash | 1 online key | 1 day |

The updater checks timestamp metadata at startup and every 4 hours, verifies the chain, rejects expired metadata and lower versions, and installs at the next start, never mid-evaluation. A new version self-tests within 60 s and rolls back on failure or two crashes in 10 minutes. Stable releases roll out to 1%, 10%, 50% and 100% over at least 4 days and halt when opted-in crash rates rise 20% (target).

**Decision D-PLT-37:** Every signature PLT produces or verifies (artifacts, TUF metadata, web manifests, provenance) carries an algorithm id. From phase 2, TUF root and targets, release signing and provenance are dual-signed with the current algorithm plus ML-DSA-87 (FIPS 204), or LMS for release signing, and long-retention records are re-timestamped before an algorithm retires. *Why:* releases must verify for decades, and national-security customers will require post-quantum signatures [CNSA 2.0 timeline unverified] (R5-23). *Rejected:* classical signatures alone; switching algorithms at once (old verifiers break). KLN's and ECO's records follow contract section 7.8.

### Air-gapped installs and enterprise policy

An offline bundle is one signed archive per release with installers, std packages, precompiled std Wasm components, the workaround database, the GPU class registry, TUF metadata, software bills of materials and provenance. `crucible mirror import` publishes it on an internal mirror whose TUF root delegates to the vendor's keys, and `crucible install --offline` verifies against the root embedded in the installer.

From phase 2 one policy schema applies on every OS through ADMX, configuration profiles, `/etc/crucible/policy.json`, server configuration and MDM: `update.channel`, `update.mode`, `update.pin`, `telemetry.performance`, `crash.upload` (`off`, `ask`, `signature_only`), `egress.allowlist`, `clipboard.labelled`, `registry.allowed`, `server.url`, `gpu.compute` and `network.proxy`. Settings name the policy that locks a value.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Phase 1 app packages | MSIX, notarized DMG, deb and rpm, OCI images, web assets | Unsigned or unnotarized artifact blocks the release | PLT-O-PKG-2 | 1 |
| Further formats | MSI wrapper, `.pkg`, Flatpak, AppImage | As above | PLT-O-PKG-2 | 2 |
| TUF-verified updates | Full signed packages; expiry, rollback and freeze checks | Failure keeps the installed version and reports | PLT-O-PKG-1 | 1 |
| Delta updates | Block maps, Zucchini and generic patches | Failed patch hash: full file | PLT-O-PKG-1 | 2 |
| Self-test and rollback | 60 s self-test; rollback on failure or two early crashes | Rollback and a filed report | PLT-O-PKG-1 | 1 |
| Repository freshness | apt and dnf metadata expiring within 7 days | Expired metadata refused | PLT-O-PKG-1 | 1 |
| Signature agility | Algorithm ids; dual signatures from phase 2 | Unknown algorithm id fails closed | PLT-O-PKG-3 | 2 |
| Air-gapped installs | Offline bundle, mirror import, offline install | Bad bundle signature: import refused | PLT-O-PKG-4 | 2 |
| Enterprise policy | One schema on every OS | Invalid value: default kept, error shown | PLT-O-PKG-4 | 2 |
| macOS JIT entitlement | `allow-jit` for Wasmtime | Missing entitlement: Wasm components refused with the reason | PLT-O-PKG-2 | 1 |

## Reliability

No crash, driver fault or power loss costs a user more than one second of edits, and every failure reaches engineers as a symbolicated, deduplicated report.

### Crash handling

| Mechanism | Choice | Failure behavior |
| --- | --- | --- |
| Native capture | A crash-monitor process started first; UI, engine, sandbox workers and translator host connect at start; Embark's `crash-handler` and `minidumper` write minidumps from outside | Monitor gone: minimal in-process report |
| Windows ARM64 | `crash-handler` has no Windows aarch64 support; Crucible adds it upstream in phase 0 and uses Windows Error Reporting local dumps meanwhile [WER local-dump configuration unverified] | Same minidump format |
| Mobile | `crash-handler` on Android arm and aarch64; OS reports on iPadOS [MetricKit collection unverified] | Lower coverage only |
| Panics | Natively `panic = "unwind"`, caught at the Op boundary and treated as worker loss: an Abort with a crash id, never cached, the operation poisoned after 2 panics; browsers abort and restart the engine worker | "Engine restarted" and journal replay |
| Processing | rust-minidump; Breakpad, PDB, dSYM and DWARF symbols per build, kept 2 years for stable and the support period for LTS | Missing symbols block promotion |
| Hang detection | 2 s without a UI event; 10 s without an engine cancellation check | Reported with a `hang:` signature |

Minidumps hold stacks, registers and modules, never heap memory, but stacks can hold design fragments. Uploads default to `ask`, show their contents, scrub paths, go only to Crucible's or the organization's server and are deleted after 90 days; labelled content follows D-PLT-38. Promotion requires a crash-free session rate of 99.8% over the beta's last 7 days (target).

### Autosave and recovery

PLT supplies the journal beneath `repo`'s Changes: records with length, sequence number, payload and CRC-32C, appended at once and flushed with `WriteDurability::Data` at most every 1 s and on save, close and power changes.

A native process crash loses nothing appended, and a power failure or browser tab crash at most 1 s. After an unclean exit the engine truncates at the first bad record, replays the rest and shows "Recovered N edits from <time>", within 2 s for a cached design (target); compaction restarts the journal by atomic rename.

CAS writes are crash-consistent on their own (temporary file, flush, rename, directory flush), and a torn object fails its hash check and is recomputed.

### Device loss, workarounds and safe mode

Device loss aborts in-flight GPU work and recreates the device after 100 ms, 1 s and 5 s; buffers are rebuilt from the CAS, and the work reruns on the device or the CPU. After 3 losses in 10 minutes, GPU compute is off for the session.

`gpu-workarounds.json` is a signed, TUF-updated data file matched before the first device is created. Entries name OS, back end, PCI ids and driver ranges, actions from a closed list (`disable_gpu_compute`, `prefer_backend`, `disable_feature`, `max_dispatch_ms`, `max_buffer_size`, `exclude_from_gpu_class`) and the reproducer that fails without them. A range closes when a newer driver passes, and no workaround changes a canonical result.

Safe mode starts with `--safe-mode`, Shift at launch or after 2 startup crashes. It disables GPU compute and requests UIX's most conservative renderer (WARP [wgpu support unverified], lavapipe or Metal). It also disables the translator host and Wasm components the lockfile does not require, and resets layout without touching repositories, the CAS or settings.

`platform` builds a `HardwareProfile` at startup and assigns a band. The Performance panel lists every degradation with its cause: CPU fallback, earlier out-of-core work under memory pressure, a halved background pool on battery, and remote evaluation offers.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Crash capture, desktop | Out-of-process minidumps, server symbolication | Monitor gone: minimal report | PLT-O-REL-1 | 0 |
| Crash capture, Windows ARM64 and mobile | Upstream ARM64 support; WER dumps meanwhile; OS reports on iPadOS | Reduced coverage, reported | PLT-O-REL-1 | 1 (Windows ARM64), 3 (mobile) |
| Panics | Abort at the Op boundary with a crash id | Panic outside an Op restarts the engine | PLT-O-REL-1 | 0 |
| Hang detection | 2 s UI and 10 s engine watchdogs | Reported as `hang:` | PLT-O-REL-1 | 1 |
| Journal and recovery | 1 s flush bound; truncate, replay, report | Bad record: truncated there | PLT-O-REL-2 | 1 |
| Crash-consistent CAS writes | Temporary file, flush, rename | Torn object recomputed | PLT-O-REL-2 | 0 |
| GPU device loss | Backoff recreation, rerun, disable after 3 losses | Abort for in-flight work; CPU path | PLT-O-GPU-2 | 1 |
| Workaround database | Signed, TUF-updated, one reproducer per entry | Unknown driver: known-answer tests still apply | PLT-O-GPU-1 | 1 |
| Safe mode | GPU, translator host and optional Wasm components off; caches reset | Never changes a canonical result | PLT-O-REL-3 | 1 |
| Graceful degradation | Explicit degradations in the Performance panel | Each names its cause | PLT-O-REL-3 | 1 |

## Telemetry and label-aware egress

Label enforcement in `api` stops at the API boundary, yet labelled content can leave through notifications, crash dumps, backups, synced folders and clipboard history (R5-16).

**Decision D-PLT-38:** For content labelled above `internal` or under any export control, channels outside `api` follow one egress rule: notifications and emails carry ids and generic text only, push payloads nothing; crash reports carry the signature and module list; reproduction bundles go only to the organization's server; the CAS, journal and caches refuse cloud-synced folders and are excluded from OS backup; and copies are excluded from clipboard history and cloud clipboard where the OS allows, or forbidden by `clipboard.labelled = deny`. *Why:* each channel hands plaintext to a third party, and ITAR's end-to-end encryption requires that "The means of decryption are not provided to any third party" (22 CFR 120.54(b)(1)(ii)). *Rejected:* label checks at `api` only; disabling notifications and crash reports for everyone.

**Decision D-PLT-39:** One telemetry pipeline, owned by PLT, serves UIX and PLT with one public schema, the union of both tabs' fields minus raw command streams. It is opt-in per install, rotates the install id every 90 days without joining it to accounts, drops aggregates under 50 installs, keeps raw data 90 days and aggregates 13 months, collects EU organizations' data in the EU, and ships a privacy notice naming the steward as controller with a DPIA template. *Why:* people "may be associated with online identifiers provided by their devices" (GDPR recital 30), and two pipelines differed in payload and retention (R5-29). *Rejected:* separate pipelines; compile-time exclusion for air-gapped builds (breaks the single binary; `telemetry.performance = off` and `egress.allowlist` replace it).

Telemetry collects operation duration histograms, frame and startup times, peak memory, band, ISA, `GpuClass`, OS, workarounds, version, command ids and error codes, and never design content, parameter values, names, Ingot source or account ids. Users can inspect each daily upload, and organizations can redirect it.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Notification and email content | Ids and generic text for labelled content | Labelled payload detected: send refused and logged | PLT-O-PRIV-1 | 1 |
| Crash and reproduction egress | Signature and module list; bundles to the organization's server | No organization server: bundle kept local | PLT-O-PRIV-1 | 1 |
| Storage placement | CAS, journal and caches outside synced folders and backups | `StorageError::CloudSynced { path, fix }` names a local folder | PLT-O-PRIV-1 | 1 |
| Clipboard exclusion | History and cloud exclusion; policy can deny | Denied copy explains the policy | PLT-O-PRIV-1 | 1 |
| Telemetry pipeline | One schema; opt-in; rotating id; thresholds; retention; EU region | Schema violation: upload rejected | PLT-O-PRIV-2 | 2 |
| Egress allowlist | Policy-listed hosts only | Blocked host logged locally | PLT-O-PRIV-2 | 2 |

## Build, release and CI

`rust-toolchain.toml` pins one stable Rust version, moved at most every 6 weeks after the suite passes; the nightly pin serves only D-PLT-10. Dependencies are locked and vendored per release, and cargo-deny checks licences (no LGPL, GPL or AGPL linked), advisories and banned crates [cargo-deny capabilities unverified].

**Decision D-PLT-40:** `deps/approved.toml` records each core dependency's licence, risk class, owning engineer, upgrade cadence and fork-or-replace plan, reviewed at each gate; first actions fund or vendor faer and pulp, evaluate fearless_simd, budget one wgpu upgrade a quarter (about three engineer-weeks, an estimate) and defer CubeCL. *Why:* core paths rest on young or single-maintainer crates (R6-30). *Rejected:* licence-only review; avoiding young crates (several have no alternative).

**Decision D-PLT-26:** Cargo stays the only build system, accelerated by sccache with a shared remote cache for CI and opt-in for developers, plus workspace rules that keep crates cacheable. *Why:* the workspace is one Cargo workspace, and sccache supports Rust with S3, GCS, Azure, Redis, GitHub Actions and WebDAV back ends. *Rejected:* Bazel or Buck2 (a second build description for every crate); no shared cache (every CI run recompiles everything).

sccache cannot cache linker-invoking or incremental crates, so binaries stay thin, proc-macro crates few and CI non-incremental from a fixed path. Targets: a no-op `cargo check` under 2 s, an `anvil-ops` edit-and-test loop under 20 s, and a warm-cache CI build under 6 minutes per target.

Two independent builders with remapped paths, `SOURCE_DATE_EPOCH` and normalized archives must produce byte-identical unsigned artifacts: Linux and wasm32 in phase 1, other targets in phase 2 [PE and Mach-O linker behavior unverified]. Apple signing runs in a separate credential-holding step.

### CI stages and capacity

| Stage | Runs | Time budget |
| --- | --- | --- |
| Pull request | Format, Clippy with determinism lints, layering, unit tests on Linux x86-64, wasm32 build, determinism subset on Linux x86-64 and wasm32 in Node | 15 minutes (target) |
| Merge queue | Build and unit tests on every Tier 1 target; the suite on the representative set; golden-product checks at `Interactive`; instruction counts; GPU paths in the pinned renderer container | 45 minutes (target) |
| Nightly | The suite on every other target and browser engine; golden-product `SignOff` simulations; GPU lab; wall-time benchmarks; random graphs; fuzzing; Tier 3 weekly; automatic bisection | 6 hours |
| Release | Installers; install, upgrade and uninstall per format; updates from the last 3 releases; Tier 2 device farm; reproducibility; software bill of materials and provenance | 12 hours |

The pinned renderer image fixes the lavapipe build, `LP_NATIVE_VECTOR_WIDTH` and `GALLIUM_OVERRIDE_CPU_CAPS`, because llvmpipe "uses LLVM to do runtime code generation" for the host CPU; snapshot byte identity holds only there (R6-26).

The GPU lab covers NVIDIA, AMD and Intel GPUs (including the reference laptop's Arc 140V), Apple silicon, Snapdragon X under Windows ARM64, a Linux ARM64 desktop (R6-31) and Adreno, Mali and Xclipse tablets. Each machine keeps a fixed driver, and upgrades pass a canary first.

CI capacity is planned per phase, with estimates of ±50% (R6-28). Phase 0 needs about 1,000 cloud vCPUs, 8 macOS and 8 ARM64 runners and 12 lab machines; phase 1 about 3,000, 24, 24 and 24; phase 2 about 5,000, 40, 40 and 36.

### Release channels and versions

| Channel | Cadence | Contents | Support |
| --- | --- | --- | --- |
| Nightly, beta | Daily; branched every 6 weeks | Everything merged; fixes only | None; until the next beta |
| Stable | Every 6 weeks from the previous beta | Fixes only | Until the next stable plus 4 weeks of security fixes |
| LTS | One stable release per year | Security, crash and wrong-result fixes | 24 months |
| Regulated extended support | One LTS line every two years | Security fixes | 10 years |

Versions are calendar-based (`2027.3.0`), and an LTS line keeps its epoch, Wasmtime line and determinizer version for life, so its patches never change results.

**Decision D-PLT-27:** Releases follow a 6-week train (nightly, beta, stable) with one LTS release per year supported for 24 months, aligned with Wasmtime's LTS window, and one LTS line every two years receives regulated extended support for 10 years. After Wasmtime's window closes, the steward backports security fixes to that line's Wasmtime or runs its retired engine in sandboxed processes. *Why:* engineering organizations cannot requalify every 6 weeks, and aerospace, defence and medical programs qualify one version for a decade (R5-20). *Rejected:* monthly releases with no LTS; standard LTS lines longer than Wasmtime's. (revised in round 2)

Releases ship a CycloneDX software bill of materials [generator unverified], an embedded dependency list [cargo-auditable mechanism unverified] and SLSA Build L3 provenance, listed in TUF targets. The Cyber Resilience Act expects manufacturers to document the third-party software in their products, including by a software bill of materials (recital 77); ECO owns export classification and CRA reporting (R5-22).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Pinned toolchains and vendored dependencies | Stable pin per 6 weeks; nightly only for the threaded web build | Suite failure blocks the bump | PLT-O-DET-1 | 0 |
| Dependency register | Risk class, owner, cadence and fork plan per core dependency | Missing entry fails CI | PLT-O-BLD-2 | 0 |
| Build acceleration | sccache and workspace rules | Cache outage: slower builds only | PLT-O-PERF-2 | 0 |
| Reproducible builds | Two builders, byte-identical unsigned artifacts | Mismatch blocks the release | PLT-O-BLD-1 | 1 (Linux, wasm32), 2 (all) |
| CI stages and capacity | As tabulated, with capacity per phase | Stage over budget: capacity review | PLT-O-DET-9 | 0 |
| Pinned renderer image | Fixed lavapipe build and CPU settings; byte-identical Snapshots for CI | Bytes may differ elsewhere; every Snapshot stays `Unverified` (contract section 2) | PLT-O-BLD-1 | 1 |
| GPU lab | Listed devices, fixed drivers, canary upgrades | Lab outage blocks beta promotion of GPU paths | PLT-O-GPU-1 | 1 |
| Release channels | Train, LTS, regulated extended support | A canonical change inside a line blocks the patch | PLT-O-BLD-3 | 1 (train), 2 (LTS) |
| Software bill of materials and provenance | CycloneDX, embedded list, SLSA Build L3 | Missing artifact blocks the release | PLT-O-PKG-2 | 1 |

## Performance engineering

PLT owns contract section 13.3's rows, their measurement and low-band targets. Staffing and the critical path are in contract section 13.2 (R6-01, R6-03, R6-04).

**Decision D-PLT-28:** The reference laptop is fixed: Intel Core Ultra 7 258V (8 cores, 8 threads, AVX2, Arc 140V GPU), 32 GB, dual-booting Windows 11 and Ubuntu LTS, measured at 1920×1080. Only it blocks beta promotion, and every other Tier 1 OS's mid machine must land within 1.5 times of each row. *Why:* as the weaker candidate (no AVX-512, 8 threads) it makes wider dispatch elsewhere margin, and Chrome enables WebGPU for its GPU on Linux (R6-07). *Rejected:* an unnamed mid laptop; a Ryzen AI 300 reference (AVX-512 and 24 threads hide costs, and its GPU runs browsers on WebGL2 under Linux); Apple silicon; a desktop. (revised in round 2)

| Band | Definition | x86-64 | Windows ARM64 | macOS | Linux ARM64 |
| --- | --- | --- | --- | --- | --- |
| Low | 4 cores, 8 GiB, integrated GPU | 2019 4-core x86-64-v3 laptop | Lowest Snapdragon X laptop, engine capped at 8 GiB | MacBook Air M1, 8 GB | Raspberry Pi 5 (CLI and viewer) |
| Mid | 8 to 14 cores, 24 to 32 GiB | The reference laptop | Snapdragon X Elite, 32 GB | MacBook Pro, M4 Pro or later | Snapdragon X laptop or ARM64 workstation with an AMD GPU |
| High | 16 or more cores, 64 GiB, discrete GPU | 16-core desktop, RTX-class GPU | As mid | Mac Studio, 64 GB or more | 32-vCPU servers with NVIDIA and AMD GPU VMs |

### Measurement protocol

Benchmark files live in `oracles/plt/bench/`; "warm" means the CAS holds every derived artifact and the process has started once. Rows run 30 times unless stated, browsers on the mid machines (R2-09, R6-08 to R6-10).

| Contract section 13.3 row | Benchmark file | Cache and statistic | Low band (target) | Work owner |
| --- | --- | --- | --- | --- |
| Cold and warm start | `start.toml` | Median | 4 s and 1.5 s | PLT |
| Selection highlight | `select.toml` | Warm; p99 over 1,000 picks | 33 ms | UIX |
| Orbit and X-ray | `orbit.toml` | Warm; p95 frame time at 2.1 MP | 30 fps at 1M triangles | UIX |
| Scene capacity | `scene.toml` | Warm; p95 frame time | Half the mid count | UIX |
| Drag preview | `drag-early.toml` and `drag-late.toml`, run separately | Warm; p90, dependents covered reported | 250 ms | KLN, ANV |
| Rebuild after an early edit | `rebuild-gp1.toml` (`SignOff`, median of 10), `rebuild-abc200.toml` (`Interactive`, p90) | Warm except the edited chain | 3 times mid | KLN, ANV |
| `SignOff` recertification | `recert-abc200.toml` | As above; p90 | 3 times mid | KLN, ANV |
| Interactive simulation update | `sim-elastic-100k.toml` | Warm-started; median | 3 s | FLX |
| Open a 1,000-part assembly | `assembly-1000.toml` | Warm CAS, cold process; median | 30 s | KLN, UIX |
| Input to photon | `latency.toml` | p99 by camera rig during a rebuild | 50 ms | UIX, PLT |
| Memory | `memory-gp1.toml`, `memory-idle.toml` | Peak resident set; browser linear memory after a heavy-worker recycle | As mid | PLT |
| Installed size | Per app package | Release builds | As mid | PLT |
| Flux CPU throughput | `ceed.toml` | Median | Not set | FLX |

Startup shows the last layout while the engine maps the CAS index, loads precompiled std Wasm components and opens the last design. GPU pipelines compile in the background, asynchronously on DX12 and Metal, where wgpu's `PIPELINE_CACHE` is unavailable.

### Profiling and continuous benchmarking

All crates emit `tracing` spans, exported to Tracy or `performance.measure` and enabled on demand. Each merge runs CPU benchmarks under an instruction counter at each ISA level, and a rise above 1% blocks it unless a PLT owner records a reason.

Nightly, reference machines run the suite 30 times, and a median rise above 3% confirmed by a Mann-Whitney U test at p < 0.01 files an issue. A row missed on the reference laptop blocks beta promotion; misses beyond 1.5 times elsewhere file issues.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Reference laptop | Fixed model and resolution; sole beta blocker | A missed row blocks beta promotion | PLT-O-PERF-1 | 0 |
| Bands and `HardwareProfile` | Measured properties place every machine | Unknown hardware: low band | PLT-O-PERF-1 | 1 |
| Contract section 13.3 rows | Benchmark file, cache state and statistic per row | A missed row blocks beta promotion | PLT-O-PERF-1 | 1 |
| PLT's own rows | Update check under 2 KB; library, hashing and ratio targets | A missed row files an issue | PLT-O-PERF-3 | 1 |
| Instruction-count gate | 1% per merge | Merge blocked without an approved reason | PLT-O-PERF-2 | 0 |
| Wall-time tracking | Nightly, statistically confirmed | Issue with the commit range | PLT-O-PERF-2 | 0 |
| Profiling | `tracing` spans to Tracy and browser profilers | Disabled span over 5 ns fails the oracle | PLT-O-PERF-4 | 0 |

## State of the art

Figures in the last column are targets on the reference laptop unless they cite a source.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Cross-platform determinism | No contraction, own elementary functions, data-ordered reductions | Box2D across x64 and ARM compilers; Rapier's `enhanced-determinism` | One canonical class (D-PLT-19) | Zero hash differences across targets, threads and ISA levels |
| Elementary functions | Correct rounding (CORE-MATH) | glibc 2.43 | CORE-MATH C build, then Rust ports (D-PLT-17) | MPFR tests; `exp` and `ln` within 1.5 times glibc |
| FMA-free canonical kernels | Error-free transformations; FMA only where correctly rounded | libCEED and vendor BLAS with FMA | `CpuIsa` FMA variants above a 1.3 times penalty (D-PLT-18) | Penalty per family and degree [to be measured in phase 0] |
| Reproducible reductions | Binned summation (Demmel and Nguyen; ReproBLAS) | oneMKL strict CNR | Data-defined trees; `exact_sum` across ranks | Identity at 1 to 64 threads; `det_sum` at 90% of an unordered sum |
| Canonical linear algebra | Fixed blocking, deterministic pivoting | oneMKL CNR; faer | `linalg` (D-PLT-34) | Identity under two cache settings; 2.5 times faer `CpuIsa` |
| CPU scheduling | Work stealing; low-overhead fork-join (Spice) | rayon; chili | rayon pools by lane | Foreground start under 2 ms at p99 |
| SIMD | Write once, dispatch per ISA | pulp; fearless_simd 1.0 | Canonical horizontal order (D-PLT-15) | Fraction of peak per ISA; AVX2 `det_sum` 3 times scalar |
| Allocation | Thread-local heaps | mimalloc v3, jemalloc, snmalloc | mimalloc v3 (D-PLT-14) | Macro-benchmarks, re-measured in phase 0 |
| Out-of-core data | Content-addressed chunks with explicit residency | None identified for CAD [unverified] | `ChunkedBuffer<T>` | Identical hashes; assembly row on a 2 GiB budget |
| GPU compute | One kernel source for every vendor and the web | CUDA libraries; CubeCL | Kernel IR through WGSL (D-PLT-16) | Known-answer pass rate; reductions at 50% of float-atomic throughput |
| GPU determinism | Integer or fixed-topology reductions | Vendor primitives [deterministic modes unverified] | Per-pipeline classes, integer limbs | Identity per `GpuClass` over 1,000 runs |
| Wasm runtime | Ahead-of-time Cranelift, pooling, guard regions | Wasmtime; V8 | Wasmtime LTS; browser engines; JavaScriptCore | 1.6 times native in Wasmtime, 2.5 times in browsers |
| Deterministic Wasm | Injected metering (wasm-instrument); Wasm 3.0 deterministic profile | Wasmtime fuel and NaN switches | One determinizer (D-PLT-22) | Identical outputs and fuel counts; the overhead table |
| Browser engine | Threads, SIMD, workers, OPFS | Figma (load time over 3 times faster after Wasm) | Two builds, one engine per origin, heavy worker | Suite 2.0 and 2.5 times native |
| Rust GPU desktop app | Rust core, GPU renderer, thin platform layer | Zed | winit, AccessKit, wgpu | Input-to-photon p99 by camera rig |
| Text shaping | HarfBuzz | HarfBuzz | HarfRust in Parley | Test pass rate; within 25% of HarfBuzz |
| Accessibility | One tree mapped per OS | Chromium's layer | AccessKit plus a web adapter (D-PLT-8) | Screen-reader automation; axe-core |
| Crash reporting | Out-of-process minidumps | Crashpad [pipeline not opened] | `crash-handler`, rust-minidump | 99% of injected crashes symbolicated |
| Updates | TUF; executable-aware diffs | Chrome's updater [Zucchini use not confirmed] | TUF, deltas from phase 2 (D-PLT-25) | Attack simulations; median delta 15% of the package |
| Build acceleration | Remote caching and execution | Bazel, Buck2 [unverified] | Cargo with sccache (D-PLT-26) | Clean CI build under 6 minutes |
| Supply chain | Reproducible builds; SLSA L3; FIPS 204 signatures | Reproducible Linux distributions [unverified] | Two builders; dual signatures (D-PLT-37) | Byte comparison; dual verification |
| Benchmarking and profiling | Instruction counting plus wall time; always-compiled spans | CodSpeed; Tracy | The same methods on Crucible hardware | Under one false gate a week; disabled span under 5 ns |

## Platform notes

These are the risks that can still break parity on each platform.

| Platform | Risk | Mitigation | Phase |
| --- | --- | --- | --- |
| Windows | Timeout resets; paths beyond 260 characters; undeletable mapped files; antivirus on small files [magnitude unverified] | Dispatch rule; `\\?\` paths; deferred deletion; KLN packs small objects | 0 |
| Windows ARM64 | Wasmtime Tier 3; no `crash-handler`; WebGPU behind a flag | Preview; upstream work; WER dumps; WebGL2 | 1 to 2 |
| macOS | `allow-jit`; OS-shipped shader compiler | Entitlement; OS build in `GpuClass`; known-answer tests after updates | 1 |
| Linux | Wayland gaps; portals; old distributions | Data-control and portal back ends; glibc 2.34 floor | 0 to 1 |
| Linux ARM64 desktop | No lab GPU in round 1; Wasmtime Tier 2 | Mid-band and lab machine; preview | 1 to 2 |
| Browsers | Isolation; non-shrinking memory; Safari's seven-day deletion; partial WebGPU | Two builds; heavy worker; sync indicator; WebGL2 | 1 to 2 |
| iPadOS | No native JIT; App Review; memory pressure | WebKit executor; std in the binary; remote fallback | 3 |
| Android | 16 KB pages; Wasmtime Tier 3; drivers | NDK r28; upstream CI; device farm | 3 |
| Servers | Shared tenants; GPU drivers in containers | Workers per (tenant, label set); canonical CPU class | 1 to 4 |
| Tier 3 | No vendor CI | `Unverified` until the suite passes | 5 |

## Interfaces with other subsystems

### Provided by PLT

| To | What | Types |
| --- | --- | --- |
| KLN | Lanes, cancellation, safe points, memory budgets, the class for keys, CAS storage, combinators, `detmath`, the mechanism table, the dispatch rule, worker images, attestation, memory tables, label-aware egress, the FIPS-mode crypto provider | `ComputePool`, `PoolLane`, `MemoryBudget`, `PlatformClass`, `Storage`, `WriteDurability`, `ChunkedBuffer<T>`, `CryptoProvider` |
| ANV | Canonical SIMD lanes, `detmath`, `det_sum` and `exact_sum`, `linalg`, GPU paths with known-answer tests, archived toolchains for frozen versions | `simd`, `detmath`, `det_*`, `GpuPath` |
| FLX | `detmath`; `det_sum`, `det_reduce`, `exact_sum`; `linalg` jointly; `gpu` with known-answer tests and CPU fallbacks; the dispatch and agreement rules; the class enum; the browser memory table | `GpuCompute`, `GpuPath`, `RanOn`, `PlatformClass` |
| UIX | Windows, input and IME, accessibility hosting, clipboard with exclusion flags, dialogs, surfaces, WebAuthn, hardware profile, workarounds, device-loss hooks, safe mode, crash monitor, rings, dispatch rule, memory caps, browser and startup rows, telemetry pipeline, renderer image, dependency register | `WindowHost`, `PlatformEvent`, `AccessibilityHost`, `Authenticator` |
| `repo` | Journal, atomic writes, locks, watching, portable paths, text normalization | `Journal`, `WatchEvent`, `RepoPath` |
| ING | Executors, the determinizer, verification of generated modules, `detmath` for native and wasm32, text normalization, the browser memory table | `WasmComponentEngine`, `CallLimits` |
| ECO | The determinizer and its overhead table, Wasmtime LTS with 7-day security releases, world enforcement, the OS sandbox for workers, the browser Wasm component runtime, offline bundles, NFC normalization, TUF and signature formats | `WasmComponentEngine`, `CallLimits` |
| AGT | `api` transport, `cli` exit codes, the keychain through `CredentialStore`, WebAuthn, `Usage` measurement with GPU timestamps, the stdio sandbox for external MCP servers | `Guidance` errors, `Authenticator` |
| MEC | `linalg` for constraint solving | `linalg` |
| COV | `linalg` for calibration fits; `f64` availability per class; the browser memory table | `linalg`, `PlatformClass` |
| ELX | `linalg` for circuit LU; `detmath`; the browser memory table; serial and USB access | `linalg`, `DeviceIo` |
| MFG | Serial and USB access and a device key for the machine gateway; its packaging once an app exists (open question 13); the browser memory table | `DeviceIo` |

### Consumed by PLT

| From | What PLT needs |
| --- | --- |
| KLN | Grades and class acceptance; key composition; uncached Aborts; small-object packing; cost hints; lane mapping by `PriorityClass`; what attestation signs |
| ANV, FLX | Grades, GPU roles, budgets for agreement and corpora per operation; the kernel IR, sparse factorization and no-FMA penalties |
| COV | Precision classes per model; External Op worker needs |
| UIX | The AccessKit tree; render-quality levels; device-loss and safe-mode behavior; its rows; telemetry fields; a copy budget |
| ECO | Worlds; browser Wasm component descriptions; declared memory limits; font packages; export classification and CRA reporting |
| AGT | Message framing, error shape, `Usage`, and the `Budget` behind work budgets |
| ING | The interpreter on every target; generated modules; the feature-call memory model |

## Oracles

All PLT oracles live in `oracles/plt/`, readable but not writable by agents; loosening a threshold needs human approval.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| PLT-O-DET-1 | Canonical identity | Every hash equals the reference on every Tier 1 target, forced ISA level, browser and Wasm executor |
| PLT-O-DET-2 | Schedule independence | Identical at 1, 2, 3, 8 and 64 threads with stealing delays and allocator randomization |
| PLT-O-DET-3 | Out-of-core equivalence | Identical with a 64 MiB budget |
| PLT-O-DET-4 | `detmath` correct rounding | Exhaustive f32 and hard-case plus 10⁹ random f64 inputs match MPFR; ports match the C build |
| PLT-O-DET-5 | Lints | Layering, disallowed methods and types, intrinsics, `-ffp-contract=off`, no faer in `Portable` code, no NaN inspection |
| PLT-O-DET-6 | Cross-class agreement | Every `CpuIsa` and `GpuClass` meets \|q_A − q_B\| ≤ E_A + E_B on golden products and corpus |
| PLT-O-DET-7 | Floating-point environment | A planted flush-to-zero library causes an Abort and a correct rerun |
| PLT-O-DET-8 | `detmath` speed | Per-function targets on x86-64-v3 and wasm32 |
| PLT-O-DET-9 | Suite cadence | Representative set per merge, the rest nightly; a planted divergence bisects to its commit and blocks beta |
| PLT-O-LA-1 | `linalg` identity | Identical under two cache settings and any thread count; index-ordered pivot ties |
| PLT-O-LA-2 | `linalg` speed | Dense n ≥ 1,000 within 2.5 times faer `CpuIsa` |
| PLT-O-GPU-1 | Known-answer tests | A planted fused or reassociated pipeline fails and falls back to the CPU |
| PLT-O-GPU-2 | GPU recovery | Forced loss recovers within 5 s and leaves no cache entry from lost work |
| PLT-O-GPU-3 | GPU primitives and roles | Identity per `GpuClass` over 1,000 runs; injected NaN detected; filters drop no true candidate |
| PLT-O-GPU-4 | Dispatch rule | No dispatch over 4 ms while orbiting; orbit holds its row during a solve; no reset in 1,000 long solves |
| PLT-O-RT-1 | Start latency | Foreground start under 2 ms at p99 with both pools loaded |
| PLT-O-RT-2 | Memory exhaustion | Golden products within their rows; exhaustion is a typed Abort, never cached |
| PLT-O-RT-3 | Usage accounting | Within 5% of an independent measurement; shared-GPU seconds unattributed |
| PLT-O-OS-1 | Shells and input | Window lifecycle per OS; recorded pointer, pen and HID traces replay identically |
| PLT-O-OS-2 | IME | Japanese, Chinese and Korean composition on each desktop OS |
| PLT-O-OS-3 | Accessibility | Tree snapshots per golden-product screen; OS automation reads names and roles; axe-core passes |
| PLT-O-OS-4 | Platform services | Clipboard round trips, lock contention, watcher convergence under fuzzing, dialog and notification automation, virtual-authenticator assertions, serial and USB loopback |
| PLT-O-OS-5 | Path portability | A repository created on each OS checks out with identical hashes on the others |
| PLT-O-OS-6 | Text and fonts | Identical text hashes from every OS; identical shaping on every class |
| PLT-O-TGT-1 | Tier 2 targets | Device-farm smoke tests and the determinism subset; WebKit and Android executors match canonical hashes |
| PLT-O-TGT-2 | Worker isolation | Untrusted workers reach no key and write only their namespace; no pooling slot crosses tenants or label sets |
| PLT-O-WEB-1 | Isolation and sign-in | Threaded build only when isolated; both builds identical; redirect sign-in works with reference identity providers |
| PLT-O-WEB-2 | One engine per origin | Two tabs editing, owner closed: no Change lost |
| PLT-O-WEB-3 | Browser memory | Caps hold on 8 GB and 32 GB machines; recycle restores idle memory; 500 suspended calls fit |
| PLT-O-WEB-4 | Verified web updates | Tampered, rolled-back or frozen manifests refused |
| PLT-O-WEB-5 | Browser hashing | Native-identical `ObjectId`s; 1 GiB in 1 s with 8 workers |
| PLT-O-WASM-1 | Wasm determinism | Identical outputs, fuel counts and traps in every executor; spec tests pass; injected fuel matches Wasmtime's on a reference table |
| PLT-O-WASM-2 | Determinizer overhead | Each class within its row of the overhead table |
| PLT-O-WASM-3 | Cancellation and failure kinds | Cancellation lands at fuel checks everywhere; `Failure`s cache identically; no Abort reaches a memo or the CAS |
| PLT-O-WASM-4 | Observable NaN | NaN-observing modules agree across engines; others are unchanged |
| PLT-O-WASM-5 | Ingot module verification | Each planted violation is rejected |
| PLT-O-WASM-6 | Isolation and worlds | A hostile Wasm component or stdio MCP server reads no repository, OPFS, token or key; forbidden imports fail at install |
| PLT-O-PKG-1 | Update security | TUF attacks rejected; power loss during apply leaves a runnable version; failed self-tests roll back |
| PLT-O-PKG-2 | Install hygiene | Install, upgrade from the last 3 releases and uninstall leave no stray files; signatures and notarization verify |
| PLT-O-PKG-3 | Dual signatures | Classical verifiers accept; post-quantum verifiers require both; unknown ids fail closed |
| PLT-O-PKG-4 | Air-gapped installs and policy | Mirror import and offline install verify; every policy applies on every OS |
| PLT-O-REL-1 | Crash capture | Every `sadness-generator` crash type in every process yields a symbolicated report |
| PLT-O-REL-2 | Journal durability | Random kills lose no appended record; dropped writes lose at most 1 s; recovery is exact |
| PLT-O-REL-3 | Safe mode and degradation | Safe mode after 2 startup crashes changes no canonical hash; degradations name their cause |
| PLT-O-PRIV-1 | Label-aware egress | With a confidential design open, no notification, email, crash upload or bundle carries content; synced folders refused |
| PLT-O-PRIV-2 | Telemetry | Payloads match the schema; only the rotating id; small aggregates dropped; allowlist enforced |
| PLT-O-BLD-1 | Reproducible build | Byte-identical unsigned artifacts; the renderer image reproduces snapshot bytes |
| PLT-O-BLD-2 | Dependency register | Every core dependency has a complete entry |
| PLT-O-BLD-3 | Old releases | Archived engines rebuild old golden products bit for bit; patches never change a canonical hash |
| PLT-O-PERF-1 | Budgets | Every contract section 13.3 row on the reference laptop; other mid machines within 1.5 times |
| PLT-O-PERF-2 | Regression gates | Instruction counts within 1%; wall-time changes confirmed statistically |
| PLT-O-PERF-3 | PLT's own rows | Browser and Wasm ratios, update check |
| PLT-O-PERF-4 | Profiling overhead | Disabled span under 5 ns; capture under 5% of frame time |

## Phasing

Gate contributions only, consistent with contract sections 13.1 and 13.2; no capability of section 13.4 belongs to PLT.

| Phase | PLT contribution to the gate |
| --- | --- |
| 0 | Determinism suite green on the representative set and nightly on every Tier 1 target; `detmath` C build by month 3 and hot functions ported; `linalg` dense kernels; Wasmtime LTS with the determinizer and its overhead table; pools and combinators; platform layers for Windows, macOS, Linux and browsers; desktop crash capture; reference laptop bought; kill thresholds and no-FMA penalties measured; dependency register |
| 1 | GP1 and GP2 meet every contract section 13.3 row on the reference laptop; general availability on Windows 11 x86-64, macOS, Linux x86-64, Chrome and Edge, with preview targets passing headless; MSIX, notarized DMG, deb and rpm with TUF-verified full packages; one engine per origin and the heavy worker; third-party Wasm isolation; WebAuthn for approvals; known-answer tests; journal, safe mode and egress rules; reproducible Linux and wasm32 builds |
| 2 | Preview targets reach general availability; first LTS line; deltas, Flatpak, AppImage, MSI wrapper and `.pkg`; enterprise policy, offline bundles and telemetry; dual signatures; reproducible builds everywhere; parallel canonical sparse factorization; serial and USB access for the machine gateway; cloud workers with attestation; GP3 and GP4 identical on desktop, browser and server |
| 3 | iPadOS after the WebKit spike, Android tablets and phone viewers; mobile accessibility and crash capture; Vulkan `f64` paths with FLX; GP5 reviewable and lightly editable on Tier 2 |
| 4 | Multi-GPU servers and distributed `exact_sum`; CUDA or HIP reconsidered with FLX; GP6 simulations within their rows |
| 5 and later | Tier 3 in the canonical class; SVE dispatch; memory64 re-evaluated; riscv64 servers |

## Open questions

1. **App Review.** If review rejects registry Wasm components as dependencies of an opened design, iPadOS evaluates them remotely.
2. **WebKit executor shape.** A phase 3 spike measures WKWebView memory, WebAssembly speed and WebGPU and picks one of D-PLT-33's two forms.
3. **Browser caps.** Phase 0 kill thresholds may lower the proposed 1.5 GiB engine and 512 MiB UI caps.
4. **No-FMA penalties.** Which kernel families ship `CpuIsa` variants, measured with FLX in phase 0.
5. **`detmath` speed.** Whether batched ports meet the `pow` and large-argument trigonometric targets.
6. **WGSL accuracy for intervals.** Reassociation and fusion void per-operation bounds, so ANV's GPU intervals stay `Preview`-only unless a per-pipeline audit shows neither occurred (ANV open question 5).
7. **PE and Mach-O reproducibility.** If unreachable, verification there rests on provenance alone.
8. **chili.** Whether it beats rayon enough on BVH builds and sparse assembly to justify a second scheduler.
9. **Archive retention.** How long archived engines and toolchains stay runnable, who signs and hosts them, and what ANV's five-year native retention costs in CI (ANV open question 1).
10. **Extended support funding.** Backporting Wasmtime security fixes beyond its 24-month window needs a funded owner; otherwise retired engines run in sandboxed processes.
11. **Fuel pricing.** AGT decides whether `Usage` prices fuel.
12. **Declined in part.** R1-43's routine `SignOff` in `CpuIsa` with FMA is declined, because contract section 7.3 requires canonical recomputation for `SignOff`.
13. **Machine gateway app.** MFG's gateway (D-MFG-20) needs an app package with `DeviceIo` and a device key, but contract section 12's crate map has no gateway app; round 3 files a contract request to add one.

## Contract change requests

- CCR-PLT-5, third-party Wasm components out of process everywhere: accepted in contract v5; section 7.4 holds the rule.
- CCR-PLT-6, browser first visit and payload: accepted in contract v5; section 13.3 holds the rule.
- CCR-PLT-7, signature agility: accepted in contract v5; section 7.8 holds the rule.
- CCR-PLT-8, the `detmath` C build: accepted in contract v5; section 12 holds the rule.

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
