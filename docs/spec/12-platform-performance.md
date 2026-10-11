# Platform and performance (PLT)

Crucible runs one Rust core on every Tier 1 target behind a single platform layer, so operating-system code lives in one crate and core crates never see an OS. The compute runtime makes CPU results bit-identical across Windows, macOS, Linux and the browser, on x86-64, ARM64 and wasm32, through a correctly rounded math library, a ban on implicit fused multiply-add, data-defined reduction orders and one canonical SIMD lane layout. GPU paths accelerate but never define canonical results, and every GPU path has an explicit CPU fallback.

## Scope and crate boundary

PLT owns the mechanisms below the product: OS services, app shells, the compute runtime, numerical determinism mechanisms and `PlatformClass`, the Wasm component runtime, packaging and updates, reliability, build and release, and performance engineering. The UI tab (UIX) owns the renderer and interaction design. Kiln (KLN) owns evaluation semantics, scheduling decisions and the determinism policy per operation; PLT provides the mechanisms that policy relies on.

### Crates

| Crate | Location | Contents | OS APIs | `unsafe` |
| --- | --- | --- | --- | --- |
| `platform-api` | `core/` | Traits and portable types for OS services and storage; `PlatformClass`, `ExecMode`, `HardwareProfile`, `RepoPath` | No | Forbidden |
| `runtime` | `core/` | Compute pool, IO bridge, deterministic parallel combinators, memory budgets, arenas, out-of-core residency | No | Forbidden |
| `simd` | `core/` | ISA detection, dispatch, canonical-lane kernels | No (`target_arch` only) | Allowed (SIMD crate) |
| `detmath` | `core/` | Correctly rounded elementary functions, scalar and batched | No | Allowed (SIMD paths) |
| `gpu` | `core/` | GPU compute abstraction over wgpu and CubeCL, deterministic reductions, device-loss recovery | No (wgpu is portable) | Allowed (GPU crate) |
| `wasm-host` | `core/` | Wasm component instrumentation, Wasmtime embedding, the `WasmComponentEngine` trait | No | Allowed (loads precompiled machine code) |
| `platform` | `apps/` | The only crate that binds OS APIs: winit, AccessKit adapters, clipboard, dialogs, file watching, memory mapping, web-sys, Android and iOS glue | Yes | Allowed (FFI) |
| `shell-desktop`, `shell-web`, `shell-ios`, `shell-android`, `server`, `cli` | `apps/` | Entry points, packaging metadata, wiring of `platform` into `api` | Through `platform` | Minimal |

**Decision D-PLT-1:** OS services sit behind traits in `core/platform-api`, implemented by exactly one crate, `apps/platform`, and injected at startup by the app shell. *Why:* core crates stay OS-agnostic as the contract requires, the browser and native builds share every core crate, and tests inject in-memory implementations so storage and clocks never leak into evaluation. *Rejected:* `cfg(target_os)` scattered through core crates (untestable, breaks the browser build); one crate per OS service (many boundaries instead of one).

`api` re-exports the `platform-api` and `wasm-host` traits, so `apps/` crates depend only on `api`, as the contract requires. A workspace check (`cargo xtask check-layers`, run in CI) fails when a crate outside `apps/` depends on an OS-binding crate (`windows`, `windows-sys`, `objc2*`, `core-foundation`, `ashpd`, `zbus`, `web-sys`, `js-sys`, `ndk`, `jni`, `winit`, `accesskit_*`, `arboard`, `rfd`, `notify`, `memmap2`) or uses `cfg(target_os)`. `target_arch` and `target_feature` remain allowed in `simd`, `detmath` and `gpu`, because ISA dispatch is not an OS service.

[[DIAGRAM: crate layering. Boxes top to bottom: apps/shell-desktop, shell-web, shell-ios, shell-android, server, cli; then api; then core crates kiln, cas, repo, anvil-*, flux-*, ingot-*; then runtime, simd, detmath, gpu, wasm-host; then platform-api. A separate box apps/platform beside the stack. Solid arrows "depends on" point downward; a dashed arrow "implements and is injected at startup" runs from apps/platform to platform-api; the shells have a solid arrow to apps/platform.]]

## Platform matrix

The contract fixes the tiers (section 9). This section fixes versions, architectures, GPU backends, known risks and CI for each target. "Per commit" means every commit that lands on `main` through the merge queue; pull-request commits run a fast subset.

### Tier 1

| Target | OS versions | CPU | GPU backends | Known risks | CI |
| --- | --- | --- | --- | --- | --- |
| Windows 11 x86-64 | Every Windows 11 release in Microsoft servicing: as of October 2026, 25H2 and 26H2 (shipped 29 September 2026 as an enablement package on the servicing branch shared with 24H2 and 25H2), plus 24H2 while serviced [servicing end dates unverified]. Windows 10 is outside the matrix | x86-64-v2 baseline; dispatch to x86-64-v3 (AVX2, FMA) and x86-64-v4 (AVX-512) | DX12 primary, Vulkan secondary | Driver variance across Intel, AMD and NVIDIA; timeout detection and recovery resets on long dispatches | Per commit: build, unit tests, determinism suite, golden-product checks on the CPU path. Nightly: GPU lab (NVIDIA, AMD, Intel) |
| Windows 11 ARM64 | 24H2, 25H2 and 26H2, plus 26H1 (build 28000, shipped on new devices [device scope unverified] and not offered the 26H2 upgrade) | ARMv8 NEON (Snapdragon X class) | DX12 | Young GPU drivers; Chrome ships WebGPU on Windows ARM64 only behind a flag; the `crash-handler` crate lists Windows support for x86-64 only | Per commit on native ARM64 runners; GPU lab with Snapdragon X devices |
| macOS | Current release and two prior, Apple silicon only: as of October 2026, macOS 27 [September 2026 release unverified], 26 Tahoe and 15 Sequoia | ARM64 NEON (M1 and later) | Metal | Wasmtime needs the hardened-runtime JIT entitlement; macOS 27 drops Intel and macOS 26 is the last Intel release | Per commit on Apple silicon runners; nightly once per supported OS version |
| Linux x86-64 and ARM64 | glibc 2.34 or later. Tested: Ubuntu 22.04, 24.04 and 26.04 LTS; Debian 12 and 13; RHEL 9 and 10 and rebuilds; current two Fedora releases [distribution glibc versions unverified]. Wayland (GNOME, KDE Plasma, wlroots compositors) and X11 | x86-64-v2 baseline with dispatch; ARM64 NEON | Vulkan primary (Mesa RADV, ANV and NVK; NVIDIA proprietary); OpenGL ES 3 through the wgpu GL backend as fallback | Wayland protocol gaps (clipboard data-control, drag sources, fractional scaling, text input); Flatpak portal behavior; Chrome ships WebGPU on Linux only for Intel Gen12+ and NVIDIA on Wayland | Per commit on both architectures in containers with software Vulkan; GPU lab nightly (AMD, NVIDIA, Intel) |
| Desktop browsers | Chrome and Edge (current and previous stable) and Firefox (current release and ESR) on Windows, macOS and Linux; Safari 26 and later on macOS | wasm32 with threads, SIMD128 and bulk memory | WebGPU where shipped, WebGL2 elsewhere | Cross-origin isolation needed for threads; 4 GiB wasm32 memory ceiling; storage eviction; Firefox ships WebGPU on Windows and macOS but not yet Linux | Per commit: Chrome and Firefox headless on Linux, Safari on a macOS runner. Nightly: the same on GPU-lab machines |

WebGPU availability decides the browser GPU path at run time. Status as of October 2026, from the gpuweb implementation status page:

1. Chrome: Windows x86/x64, macOS and ChromeOS since 113; Android 12+ on ARM, Qualcomm and Intel GPUs since 121; Linux only for Intel Gen12+ (144) and NVIDIA on Wayland (147); Windows ARM64 behind a flag.
2. Firefox: Windows since 141; Apple silicon Macs since 145 (macOS 26+) and 147 (all macOS versions); Linux in Nightly only.
3. Safari: version 26 on macOS, iOS, iPadOS and visionOS.

### Tier 2

| Target | OS versions | CPU | GPU backends | Known risks | CI |
| --- | --- | --- | --- | --- | --- |
| iPadOS | iPadOS 26 and later | ARM64; M-series for editing, A-series for viewing | Metal | No JIT for App Store apps, so Wasm components run on the Pulley interpreter; App Review guideline 2.5.2 on downloaded code; memory pressure kills | Every release: device-farm smoke tests and the determinism suite subset |
| Android tablets | Android 13 (API 33) and later; target API per Google Play policy (API 35+) | ARM64 | Vulkan 1.1, OpenGL ES 3.1 fallback | Driver quality on Mali, Adreno and Xclipse; 16 KB memory pages required for app updates from 1 February 2027 | Every release: device farm (Adreno, Mali, Xclipse) |
| ChromeOS | Current stable, through the browser target | x86-64, ARM64 | WebGPU (Chrome 113+), WebGL2 | Low-memory Chromebooks | Every release: browser suite on one Chromebook |
| Phones | iOS 26+, Android 13+ | ARM64 | Metal, Vulkan | Small memory and screens | Every release: viewer smoke tests |

### Tier 3

| Target | Status | GPU | CI |
| --- | --- | --- | --- |
| FreeBSD 14 and 15 [15.x release status unverified], x86-64 (Rust Tier 2 with host tools) | Community-supported desktop and server | Vulkan through Mesa where it works, otherwise CPU | Weekly community build and CPU determinism suite |
| OpenBSD, NetBSD, illumos; Linux on riscv64 | Best effort, server and CLI first | CPU | Community |
| Intel Macs on macOS 15 and 26 | Best effort until macOS 26 leaves Apple security support | Metal | Weekly build only |

A Tier 3 target joins the shared CPU platform class only after it passes the determinism suite (see "Numerical determinism"). Until then its results carry `PlatformClass::Unverified` and never enter the shared cache.

### Servers and cloud workers

| Target | Base | Acceleration | CI |
| --- | --- | --- | --- |
| Linux containers, x86-64 and ARM64 | OCI images on a glibc 2.34+ base; a static `cli` build on the musl targets (musl 1.2.5, Rust Tier 2 with host tools) | CPU by default, in the same CPU class as desktops; optional CUDA (NVIDIA) and ROCm (AMD) through CubeCL runtimes; headless Vulkan | Per commit: image build and determinism suite. Nightly: one CUDA and one ROCm runner |

ARM64 cloud CPUs with SVE run the NEON paths until Rust supports SVE (see "SIMD").

**Decision D-PLT-2:** Native x86-64 builds target x86-64-v2 and dispatch hot kernels at runtime to x86-64-v3 and x86-64-v4; ARM64 builds target ARMv8 with NEON. *Why:* every dispatched path produces identical bits (see "SIMD"), so a low baseline costs speed only in cold code and keeps older and low-end CPUs supported. *Rejected:* an x86-64-v3 baseline (drops CPUs without AVX2 for a gain that dispatch already captures); per-CPU builds (multiplies release artifacts).

**Decision D-PLT-3:** Linux binaries link against a glibc 2.34 sysroot and use no newer symbols, and Linux on Wayland is a first-class target equal to X11. *Why:* enterprise engineering desktops run long-lived distributions, and the oldest one in scope sets the floor. *Rejected:* fully static musl desktop builds (GPU drivers load through the system's dynamic loader); per-distribution builds.

## The platform layer

`apps/platform` implements every `platform-api` trait once per OS family and is the only crate that touches OS APIs. Core crates receive services as trait objects, so tests substitute in-memory fakes and evaluation never reaches a real file system, clock or environment variable.

### Library choices

| Service | Library | Backends | Status checked October 2026 | Rationale |
| --- | --- | --- | --- | --- |
| Windows, event loop, input | winit | Win32, AppKit, Wayland, X11, UIKit, Android, web canvas | 0.30.13 is the newest stable release; the 0.31 beta series reworks file drag and drop (`DragEntered`, `DragMoved`, `DragDropped`, `DragLeft` with pointer position), adds pen input on Wayland, Windows and web, Apple Pencil on iOS, IME hints and surrounding-text deletion, and Wayland gestures and native popups; MSRV 1.85 | Only Rust windowing library that covers every Tier 1 and Tier 2 target, including the browser |
| Accessibility | AccessKit | UI Automation (Windows), NSAccessibility (macOS), AT-SPI over D-Bus (Unix), Android, UIAccessibility (iOS) | Released adapters are "at rough feature parity" and do not yet support rich text or hypertext; the web adapter is planned, not released; Apache-2.0 or MIT | One accessibility tree drives every native API |
| Text layout and shaping | Parley with HarfRust, Fontique, Skrifa and ICU4X | All targets, pure Rust | HarfRust matches HarfBuzz v14.3.1, passes most of the HarfBuzz test and fuzzing suites, is "less than 25% slower than HarfBuzz on most common fonts", and rejects malformed fonts with an error | Pure Rust, so identical shaping on every OS and in the browser |
| Clipboard | arboard plus native code for custom formats | Windows, macOS, X11; Wayland through the `wayland-data-control` Cargo feature, which needs compositor support for data-control protocols | Text and images; Apache-2.0 or MIT | Mature text and image support; custom formats need native code anyway |
| File dialogs | rfd | Windows, macOS, Linux through GTK3 or the XDG Desktop Portal, web (async only) | MIT | Native dialogs, and the portal backend works inside Flatpak |
| File watching | notify | inotify (Linux, Android), FSEvents or kqueue (macOS), ReadDirectoryChangesW (Windows), kqueue (BSD, iOS), polling everywhere | MSRV 1.88; the `notify` crate is CC0 | Covers every native target with a polling fallback |
| File locking | `std::fs::File::lock`, `lock_shared`, `try_lock` | `flock` on Unix, `LockFileEx` on Windows | Stable since Rust 1.89; locks "may be advisory or mandatory" | No dependency; one documented behavior |
| Notifications | Native code per OS | Windows app notifications using the package identity that MSIX provides, macOS UserNotifications, freedesktop notifications over D-Bus or the portal, web Notifications API, iOS and Android local notifications | Built in `platform` | Small surface; avoids a dependency per OS |
| Credentials | Native code per OS | Windows Credential Manager, macOS and iOS Keychain, Secret Service portal, Android Keystore, WebAuthn and non-extractable WebCrypto keys in the browser | Built in `platform` | Holds `api` tokens; never stored in plain files |

**Decision D-PLT-4:** winit provides windows, the event loop and raw input on every target; Crucible tracks the 0.31 series, pinned to a beta in phase 0 and to the stable release once published. *Why:* it is the only Rust windowing library covering desktop, web, iOS and Android, and 0.31 adds the pen, Apple Pencil, drag-and-drop and IME work that CAD input needs. *Rejected:* SDL3 (a C dependency behind FFI that duplicates winit's coverage); GPUI's platform layer (bound to Zed's UI framework, and Zed lists the web as "not yet available"); a custom windowing layer (years of per-OS work with no benefit).

### Capability catalog

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Windows and surfaces | `WindowHost::create_window(WindowSpec) -> Result<WindowId, PlatformError>`; provides raw window and display handles to the UI renderer | `PlatformError::Window { backend, reason, fix }`, for example "no Wayland or X11 display found; set WAYLAND_DISPLAY or DISPLAY" | Shell smoke test per OS: create, resize, scale change, close | 0 |
| Pointer, pen and touch | One `PointerEvent` stream with device kind, position in physical pixels, pressure, tilt, azimuth and twist where reported; touch maps to pointers | Missing pen axes are `None`, never invented | Recorded input traces replayed per OS; pen axes verified on Wacom (Windows, Linux), Apple Pencil (iPadOS) and Surface Pen | 1 (desktop), 3 (iPadOS) |
| Keyboard and IME | Physical key, logical key and committed text are separate; IME preedit and commit events; keyboard layout never changes shortcuts bound to physical keys | IME unavailable: plain text input continues and the UI states that composition is unavailable | IME tests for Japanese, Chinese and Korean input on each desktop OS | 1 |
| 6-DoF navigation devices | `NavDeviceEvent { translation: [f32; 3], rotation: [f32; 3], buttons }` from HID devices; spacenavd on Linux when present | Device absent: no events and no error | Recorded HID report fixtures | 2 [device protocol coverage unverified] |
| Accessibility | `AccessibilityHost::update(TreeUpdate)` forwards the UI's AccessKit tree to the OS adapter; actions from assistive technology come back as events | Adapter inactive, for example when no AT-SPI bus is running: the UI keeps working and logs `AccessibilityUnavailable` once | Per-OS automation reads the tree through UI Automation, the macOS AX API and AT-SPI and compares it with a snapshot; axe-core audits the web mirror | 1 (desktop, web), 3 (mobile) |
| Clipboard | Copy writes plain-text Ingot plus `application/x-crucible+cbor` (an Ingot fragment with provenance ids); paste prefers the rich format | `ClipboardError::Unavailable { reason }`; on X11 and Wayland, exiting while owning the clipboard hands data to a clipboard manager or warns that the copy will be lost | Round-trip tests per OS and between two running Crucible apps | 1 |
| Drag and drop | Incoming files and text through winit drag events; outgoing drags (for example a Part dragged to the desktop as a STEP file) through OLE `IDropSource` on Windows, `NSDraggingSource` on macOS, `wl_data_source` and XDND on Linux, HTML drag and drop on the web | Unsupported outgoing drag: the UI offers "Export…" instead and says why | Automated drag tests on each desktop OS | 1 (incoming), 2 (outgoing) |
| File dialogs | `Dialogs::open`, `save`, `pick_folder` are async and return `Option<HostFile>` | Portal missing on Linux: an in-app file browser opens with a notice, never a silent GTK fallback | Dialog tests through OS automation | 1 |
| Notifications | `Notifications::post(Notice) -> Result<NoticeId, _>`, used for long evaluations, finished CI runs and proposal reviews | Permission denied: a notice appears in the app's activity panel instead, and the setting shows the denial | Mocked OS notification centers | 1 |
| File watching | `FileWatcher::watch(root) -> WatchStream` emitting `Changed(paths)`, `Rescan(reason)` and `Health(WatchHealth)` | Event overflow, network file system or watcher failure: emits `Rescan`, and `repo` re-hashes the tree; the status bar shows "watching by polling" | Fuzz test mutating files under load; the repository must converge to the on-disk state | 1 |
| File locking | Working-copy lock: an exclusive `File::lock` on `.crucible/lock` held by the owning process; CAS writes use write-to-temporary, flush, then atomic rename, so they need no lock | Second process: `LockError::Held { holder_pid, since }` with the fix "close the other Crucible window or open read-only" | Two-process contention test per OS; crash-while-holding test | 0 |
| Paths | `RepoPath` canonical form (below); conversion to OS paths only in `platform` | `PathError` variants with a suggested portable name | Property tests over generated names; the cross-OS checkout test | 0 |
| Line endings and encoding | Text in a design repository is UTF-8 without BOM and LF-terminated; input with CRLF, CR or a BOM is normalized on read | Invalid UTF-8: `TextError::InvalidUtf8 { offset }` | Byte-identical CAS hashes for the same source checked out on Windows and Linux | 0 |
| Fonts and shaping | UI text uses system fonts through Fontique; any text that enters a design (drawings, engraved or embossed text on Parts) uses fonts distributed as registry packages and pinned by hash in the lockfile | Missing glyph in a design font: `FontError::MissingGlyph { char, font }`, never a silent substitution | Shaping golden tests through HarfRust on every class; drawing text rendered identically on all OSes | 1 |
| System signals | `SystemSignals` stream: memory pressure, power source, thermal state, display scale, light or dark appearance, network reachability | Signal unavailable on a target: reported as `Unknown` | Simulated signals in shell tests | 1 |
| Credentials | `CredentialStore::get`, `put`, `delete` by account key | Store locked or absent: `CredentialError::Unavailable`, and the `api` login flow asks again | Per-OS tests with test keychains | 1 |

### Paths and Unicode

Repository paths have one canonical form, `RepoPath`, so a design repository checks out identically on every OS and in the browser.

1. UTF-8, normalized to NFC, `/` as the only separator, relative to the repository root, with no `.` or `..` segments.
2. Each segment has at most 255 bytes, contains no control characters and none of `< > : " | ? * \`, does not end in a dot or space, and is not a Windows reserved device name (`CON`, `PRN`, `AUX`, `NUL`, `COM1` to `COM9`, `LPT1` to `LPT9`, with or without an extension).
3. Two paths that are equal after Unicode default case folding are a collision. `repo` rejects the second at add time with `PathError::CaseCollision { existing }`.
4. Paths outside repositories (export targets, imported files) use `HostPath`, an opaque OS path that may be non-UTF-8 on Linux. It never enters the CAS or the repository.
5. On Windows, `platform` uses the `\\?\` prefix internally so paths longer than `MAX_PATH` (260 characters) work without registry changes.

**Decision D-PLT-5:** Repository paths are portable by construction: NFC, `/`-separated, case-fold unique and free of names that any Tier 1 OS rejects. *Why:* a name valid on Linux but not on Windows, or two names differing only in case, splits a team across operating systems, which the cross-platform requirement forbids. *Rejected:* storing OS-native paths (breaks checkouts across OSes); normalizing silently at checkout (two different source names map to one file, so content is lost).

**Decision D-PLT-6:** Text in a design repository is stored as UTF-8 with LF line endings and no byte-order mark, and readers normalize CRLF, CR and BOM on input. *Why:* content hashes must not depend on the OS that wrote the file. *Rejected:* per-OS line endings with conversion at checkout (Git's approach, which makes hashes depend on settings).

**Decision D-PLT-7:** Text that becomes part of a design uses fonts from registry packages pinned in the lockfile and shaped by the pure-Rust Parley stack; system fonts serve only the UI. *Why:* system font sets differ by OS and version, so engraved text or drawing annotations would change geometry between machines, an environment leak that principle 4 forbids. *Rejected:* platform text engines such as DirectWrite and Core Text (different shaping and metrics per OS); system fonts in designs (non-reproducible).

### Accessibility on the web

AccessKit has no released web adapter. Crucible's UI draws into a canvas, so assistive technology sees nothing unless a DOM mirror exists.

**Decision D-PLT-8:** Crucible builds a web adapter that mirrors the AccessKit tree into a hidden DOM of elements with ARIA roles and states, routes focus and actions back as AccessKit action requests, and offers the adapter upstream to AccessKit. *Why:* the browser is a Tier 1 target, and identical features include accessibility. *Rejected:* a separate accessible HTML UI (a second UI that drifts); waiting for upstream (no schedule exists).

The same tree feeds every OS, so accessible names and roles are identical everywhere. The oracle is a snapshot test of the tree for every golden-product screen, plus axe-core audits in the browser.

### Native shells

Each shell is a thin `apps/` crate that wires `platform` into `api` and owns packaging metadata.

| Shell | Main thread | Engine placement | OS integration |
| --- | --- | --- | --- |
| `shell-desktop` (Windows, macOS, Linux) | winit event loop and UI input; macOS requires UI on the main thread | Separate engine process started by the shell, holding the compute pools and IO runtime (D-PLT-12) | File associations for `.ingot` and design repository folders, URL scheme `crucible://` for `api` links, jump lists and dock menus, macOS menu bar |
| `shell-web` | Browser main thread: UI input and, where supported, rendering | Dedicated engine worker plus compute workers | Service worker for offline use, OPFS, `crucible://`-style links as URL fragments |
| `shell-ios` (iPadOS, iOS) | UIKit main thread | In process; heavy evaluation optionally remote | Files app document provider, Apple Pencil, share sheet |
| `shell-android` | Activity main thread | In process; heavy evaluation optionally remote | Storage Access Framework, share intents |
| `server` | None | Headless compute pool, IO runtime, optional GPU devices | Container entry point, health and readiness endpoints |
| `cli` | None | In process | Same commands as CI; exit codes per error type |

## The browser target

The browser runs the same core crates compiled to `wasm32-unknown-unknown`. Results fall in the same CPU platform class as native, so a browser session, a desktop and a server share cached results bit for bit.

### Process and thread layout

| Context | Runs | May block |
| --- | --- | --- |
| Main thread | Input, accessibility DOM mirror, presentation of frames (UIX decides whether rendering runs here or in a worker through OffscreenCanvas) | Never |
| Engine worker | `api` server side, Kiln, CAS front end, journal | Yes, with `Atomics.wait`, but only while no IO is pending |
| Compute workers, N = max(1, min(`navigator.hardwareConcurrency` − 1, 16)) | The compute pool (rayon threads started by wasm-bindgen-rayon) | Yes |
| Service worker | Offline cache and update checks | Never |

The engine worker stands in for the native engine process (see "Process model"). In the threaded build, the UI and the engine exchange `api` messages and triangle buffers through `SharedArrayBuffer` ring buffers. Without cross-origin isolation `SharedArrayBuffer` is unavailable, so the same transport falls back to `postMessage` with transferred `ArrayBuffer`s; the UI code is identical either way.

### Cross-origin isolation

WebAssembly threads need `SharedArrayBuffer`, which needs cross-origin isolation: `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp`, verified at runtime through `self.crossOriginIsolated` (web.dev). Every subresource must opt in through CORS or a `Cross-Origin-Resource-Policy` header. COEP `credentialless` relaxes this; web.dev lists it for Chrome (96+) and Edge only [current support in other browsers unverified].

1. Crucible serves every asset from its own origin with CORP headers. Third-party content, such as supplier images in the parts catalog, passes through the Crucible server.
2. Self-hosted team servers ship the same headers in their default configuration, and the server's health check reports a missing header.
3. Embedding a viewer in a third-party page uses `Document-Isolation-Policy`, which isolates a single document and imposes nothing on subframes; it shipped in Chrome 137 on desktop, with Android announced for later (Chrome developer blog, May 2025). Elsewhere the embed uses the single-threaded build.

**Decision D-PLT-9:** The web build ships two engine binaries from one source: a threaded build (atomics, bulk memory, SIMD128) and a single-threaded build (SIMD128 only). The page loads the threaded build when `crossOriginIsolated` is true and otherwise loads the single-threaded build and says why in the status bar. *Why:* features stay identical when isolation is unavailable, only speed differs, and both builds produce bit-identical results. *Rejected:* refusing to run without isolation (breaks embeds and misconfigured servers); a single-threaded web product (wastes cores on every Tier 1 browser).

The threaded build requires nightly Rust: wasm-bindgen-rayon documents that thread support "is still only available in nightly" and rebuilds `std` with `build-std` and the `+atomics,+bulk-memory` target features.

**Decision D-PLT-10:** The threaded web engine builds with a nightly toolchain pinned per release and `-Zbuild-std`; every other artifact builds with pinned stable Rust. *Why:* no stable route to Wasm threads with `std` exists as of October 2026, and Rust's specified float semantics make results independent of the compiler version, which the determinism suite verifies on every commit. *Rejected:* a hand-written worker runtime without `std` threads (large, duplicative); dropping browser threads (a 4 to 16 times loss on multi-core machines).

### WebAssembly proposals in use

Support versions come from the WebAssembly support table (`features.json` on webassembly.org).

| Proposal | Chrome | Firefox | Safari | Crucible use |
| --- | --- | --- | --- | --- |
| Fixed-width SIMD128 | 91 | 89 | 16.4 | Required |
| Threads and atomics | 74 | 79 | 14.1 | Threaded build |
| Bulk memory | 75 | 79 | 15 | Required |
| Exception handling (final) | 137 | 131 | 18.4 | Not used yet: the web build aborts on panic and restarts the engine worker; unwinding is evaluated in phase 2 [Rust toolchain support unverified] |
| Relaxed SIMD | 114 | 145 | Behind a flag | Never used: results are nondeterministic by design |
| memory64 | 133 | 134 | Technology Preview 251 only | Not used (below) |
| JS Promise Integration | 137 | 153 | 27 | Not required; may simplify async host calls later |
| Multiple memories | 120 | 125 | Not listed | Not used |

A module cannot detect instruction support at run time, so the web build requires SIMD128 statically. All Tier 1 browsers support it.

### Memory

A wasm32 engine addresses at most 4 GiB. memory64 lifts this limit, but the WebAssembly JS API caps a 64-bit memory at 16 GiB, and Safari ships memory64 only in Technology Preview (Wasm 3.0 announcement; WebAssembly support table). SpiderMonkey's engineers report a 10% to over 100% slowdown, because 64-bit memories cannot elide bounds checks with guard regions (SpiderMonkey blog).

**Decision D-PLT-11:** The browser engine stays wasm32 and handles large models through out-of-core chunks in OPFS and through remote evaluation on a team server or cloud worker. *Why:* memory64 is unavailable in Safari, costs speed everywhere, and still caps at 16 GiB, while out-of-core storage and remote evaluation scale further. *Rejected:* a memory64 build for Chrome and Firefox only (two browser behaviors for one Tier 1 target).

The decision is revisited when Safari ships memory64 and the measured penalty on the PLT benchmark suite falls below 10%.

The engine worker starts with 256 MiB of linear memory and grows on demand. Allocation failure becomes `ResourceExhausted`; Kiln evicts cold buffers and retries once, then suggests remote evaluation. The residency manager's budget is 3 GiB on desktop browsers, below the 4 GiB wasm32 ceiling [per-browser maximum memory unverified], and drops when growth fails or the device reports less memory.

### GPU

WebGPU is used where `navigator.gpu` returns an adapter; otherwise rendering uses WebGL2 (UIX) and all compute runs on the CPU. WGSL has no `f64`, and `shader-f16` is the only extra float type on the web (wgpu `Features`), so browser GPU compute serves interactive fidelity and the "GPU filters, CPU decides" pattern (see "GPU compute"). WebGL2 has no compute shaders, so WebGL2 sessions run every GPU path on its CPU fallback.

### Storage

The browser CAS, the edit journal and the package cache live in the Origin Private File System. Synchronous access handles, which are fast and in place, work only in workers, which matches the engine-worker design (MDN, OPFS).

| Browser | Quota per origin (MDN) | Eviction risk |
| --- | --- | --- |
| Chrome and Edge | Up to 60% of total disk | LRU eviction of non-persistent origins under storage pressure |
| Firefox | Best effort: the smaller of 10% of disk or 10 GiB per site; persistent: 50% of disk, capped at 8 TiB | Same, unless persistence is granted |
| Safari | About 60% of disk for browser apps, about 15% for embedded web views | With tracking prevention on, script-written data is deleted after seven days of browser use without user interaction |

1. The engine calls `navigator.storage.persist()` at first use and records the answer.
2. The browser CAS is a cache. The source of truth is the team server or, where the File System Access API exists, a folder the user picks [browser coverage of that API unverified].
3. Edits not yet pushed show a persistent "not yet synced" indicator. In Safari without granted persistence, the indicator also warns that the browser may delete local-only edits after seven days without interaction.

### Offline use and updates

A service worker caches the app shell, both engine binaries, fonts and the std packages under content-hashed, immutable URLs. Opened design repositories keep working offline from OPFS and synchronize through `repo` when the connection returns. A new app version activates on the next load or when the user accepts a prompt, never in the middle of a session, so an engine never changes under an open evaluation.

### Performance relative to native

Jangda and colleagues measured SPEC CPU compiled to WebAssembly in 2019 browsers running 45% (Firefox) to 55% (Chrome) slower than native on average, with peaks of 2.08 and 2.5 times (USENIX ATC 2019). Crucible's web build also loses AVX2, AVX-512 and hardware FMA, and gains only 128-bit SIMD. Figma's switch from asm.js to WebAssembly cut its load time by more than three times; it is the best-known case of a professional design tool running a native engine in the browser.

Targets for the browser on the mid reference machine, measured by the PLT benchmark suite on the same hardware as native: geometric-mean time at most 1.6 times native single-threaded and at most 2.0 times native multi-threaded; engine start with a warm HTTP cache under 2.5 s. These are targets.

## Tablets and phones

Tier 2 covers viewing, review and light editing. Both tablet shells reuse the same core crates, the same `api` and the same UI code as the desktop; only `platform` and the shell differ.

| Capability | iPadOS, M-series | iPadOS, A-series | Android tablet | Phone (viewer) |
| --- | --- | --- | --- | --- |
| View, measure, section and explode cached results | Local | Local | Local | Local |
| Review proposals: feature diff, geometry overlay, metric deltas | Local | Local | Local | Local |
| Light editing: parameters, Ingot source, simple features | Local evaluation | Local below the memory budget, otherwise remote | Local | Not offered |
| Heavy evaluation: sign-off simulation, 1,000-part assemblies | Remote by default; local on request | Remote | Remote by default | Remote |
| Wasm components | Pulley interpreter, pending App Review, otherwise remote | Remote | Wasmtime with Cranelift, pending Play policy review [unverified], otherwise remote | Remote |
| GPU | Metal through wgpu | Metal | Vulkan 1.1, GLES 3.1 fallback | Metal or Vulkan for rendering only |

Remote evaluation runs on a team server or cloud worker in the same CPU platform class, so a result computed remotely is bit-identical to one computed locally and lands in the same cache.

Platform constraints that shape the shells:

1. **iPadOS code execution.** App Review guideline 2.5.2 forbids downloading or executing code "which introduces or changes features or functionality of the app", while guideline 4.7 lets apps offer software "not embedded in the binary", including plug-ins, subject to rules 4.7.1 to 4.7.5. App Store apps on iOS cannot generate machine code at run time [JIT restriction not verified from an Apple source], so Wasm components run on Wasmtime's Pulley interpreter, which Wasmtime uses wherever Cranelift cannot run (Wasmtime platform support). Whether App Review accepts Wasm components as plug-ins is an open question; the fallback is remote execution.
2. **Memory.** iPadOS terminates apps that exceed their memory limit, so the residency manager budget is 50% of physical memory on iPadOS [the system limit per device is unverified] and the shell flushes caches on memory warnings.
3. **Android pages.** From 1 February 2027, Google Play rejects updates to apps targeting Android 15 or later that do not support 16 KB memory pages. NDK r28 aligns ELF segments to 16 KB by default (Android developer documentation). Crucible builds with NDK r28 or later, and `platform` queries the page size at runtime instead of assuming 4,096 bytes.
4. **Phones** run the viewer: the same renderer streaming tessellations from cache or a server, with evaluation disabled to keep memory low.

## The compute runtime

The `runtime`, `simd` and `gpu` crates execute what Kiln schedules. Kiln decides which operations run, in what priority and with which determinism mode; the runtime decides how they use cores, memory, vector units and GPUs, and guarantees that none of those choices changes a canonical result.

### Process model

**Decision D-PLT-12:** The UI always talks to the engine through the `api` transport, and the engine's placement varies by target: a separate OS process on desktop, a dedicated worker in the browser, a remote `server` for remote evaluation, and an in-process thread on iPadOS and Android. *Why:* one boundary on every target keeps the UI code identical, and on desktop an engine crash, out-of-memory kill or driver fault leaves the window and the user's view intact while the engine restarts and replays its journal. *Rejected:* a single desktop process (an engine crash closes the window, and the browser already needs a worker boundary); one process per operation (process start and copying costs exceed the 100 ms preview budget).

Desktop UI and engine processes share memory-mapped ring buffers for tessellations and Field samples. They exchange `api` messages over a local socket or named pipe. On Linux, the engine sets a higher `oom_score_adj` than the UI, so under memory pressure the kernel stops the engine, which recovers, rather than the window.

iPadOS does not let App Store apps start helper processes [unverified], so the engine runs on threads there and relies on the journal for crash recovery.

Native code from third parties, such as licensed translator plugins for proprietary formats, never loads into the engine. It runs in a separate plugin-host process, sandboxed with AppContainer on Windows, the App Sandbox on macOS, and seccomp with Landlock on Linux. A plugin crash returns a typed error to the operation that called it.

[[DIAGRAM: process and thread model per target. Four columns: Desktop, Browser, iPadOS and Android, Server. Desktop: "UI process" (event loop, renderer) and "Engine process" (IO runtime, interactive pool, background pool, GPU queue thread, Wasmtime), joined by "shared-memory rings + api socket", plus a "Plugin host" process with an arrow "typed calls". Browser: "Main thread" and "Engine worker" joined by "SharedArrayBuffer rings", the engine worker linked to "Compute workers 1..N". iPadOS and Android: one process holding UI thread, engine thread and pool. Server: engine process only, with "api over network" to remote UIs.]]

### Threading

| Thread or pool | Size | OS priority | Work |
| --- | --- | --- | --- |
| IO runtime: tokio on native targets, the engine worker's event loop in the browser | 2 workers plus a blocking pool (native) | Normal | IPC, network, file IO outside the CAS fast path, update checks |
| Interactive compute pool (rayon) | One thread per logical core | User-interactive: macOS QoS user-interactive, Windows normal priority, Linux nice 0 | Operations Kiln marks interactive: drag previews, selection queries, coarse results |
| Background compute pool (rayon) | One thread per logical core; halved on battery | Utility: macOS QoS utility, Windows below-normal with EcoQoS, Linux nice 10 | Exact rebuilds, sign-off simulation, prefetch, cache warming |
| GPU queue thread | One per device | User-interactive | Command encoding, submission, readback, device-loss handling |
| Browser compute workers | max(1, min(`hardwareConcurrency` − 1, 16)) | No OS priority | One pool; background chunks park while interactive work is queued |

Both pools have one thread per logical core, so OS priorities, not thread counts, divide the cores: when both pools are busy, the OS runs interactive threads first. On Apple silicon, utility QoS threads tend to run on efficiency cores [scheduler behavior unverified]. Where an OS misses the start-latency target below, background combinator chunks also park at chunk boundaries while interactive work is queued.

Rules that keep IO and compute from blocking each other:

1. Operations are pure and never call IO APIs. Their only data access is CAS chunk reads through the residency manager, which are synchronous over memory maps and OPFS synchronous handles.
2. Async code hands compute to a pool through `ComputePool::spawn`, which returns a future, and never runs compute on an IO worker.
3. Compute threads never call `block_on`. A lint forbids `tokio` as a dependency of `anvil-*`, `flux-*` and `ingot-*`.
4. In the browser, the engine worker never blocks while it holds pending IO futures. It awaits pool completion through `Atomics.waitAsync` where available and otherwise through a message from the finishing worker [per-browser `waitAsync` support unverified].
5. Cancellation is cooperative. A `CancelToken` is checked at every chunk boundary of the deterministic combinators and at every Wasm fuel checkpoint. A cancelled operation returns `Cancelled`, which is never cached.

Kiln's scheduler sits above the pools. Kiln submits each Op evaluation to a pool as one run; the runtime has no unit of work besides runs and the scheduling chunks inside them.

Kiln keeps priority queues, submits each ready Op to the pool matching its priority, and promotes a background operation to the interactive pool when an interactive operation waits on it and it has not started. If it has started, `ComputePool::boost` raises the background pool's thread priority until the waiting operation is satisfied.

Inside an operation, data parallelism uses the deterministic combinators below on the same pool, nested through rayon's work stealing. The scheduling target is that an interactive operation starts within 2 ms of submission at the 99th percentile while both pools are busy (target). To make this possible, the combinators split work into scheduling chunks sized from static cost hints to run for 0.1 to 1 ms; scheduling chunks never change a reduction tree, so they never affect results.

**Decision D-PLT-13:** CPU parallelism uses rayon work-stealing pools, split by priority into an interactive and a background pool, with all result-affecting parallelism expressed through Crucible's deterministic combinators. *Why:* rayon is the standard Rust work-stealing runtime and supports the browser through wasm-bindgen-rayon; the combinators remove any dependence of results on thread count or stealing order. *Rejected:* tokio for compute (cooperative async tasks starve under long kernels); a custom scheduler (no benefit over rayon at operation granularity).

Lower-overhead fork-join is evaluated in phase 1 for fine-grained recursion such as BVH builds: the chili crate, a Rust port of Spice, reports 3.4 µs against rayon's 51.1 µs on a 1,023-node tree on an AMD Ryzen 7 4800HS. Crucible adopts it for those kernels if the PLT suite shows a gain above 20% (target).

### Deterministic parallel combinators

Every combinator partitions work by data, never by thread count, and combines partial results in a fixed order.

| Combinator | Contract | Order guarantee |
| --- | --- | --- |
| `det_for_each_chunk(len, chunk, f)` | Applies `f` to disjoint index ranges with no result-affecting shared state | Results do not depend on execution order |
| `det_map_collect(slice, f) -> Vec<U>` | Parallel map | Output in input index order |
| `det_sum(&[f64]) -> f64`, `det_sum_f32` | Pairwise sum | Blocks of 2,048 elements; one canonical lane per element of a 512-bit virtual vector (8 lanes for f64, 16 for f32), lane i accumulating elements i, i + L, i + 2L, …; lanes reduced by a balanced binary tree over lane indices, for f64 ((l0+l1)+(l2+l3))+((l4+l5)+(l6+l7)); blocks combined by a balanced binary tree over block indices, in which a range of n blocks splits at ⌈n/2⌉ |
| `det_reduce(slice, identity, op)` | General reduction | Same block and tree structure as `det_sum` |
| `det_scan(slice, op)` | Prefix scan | Fixed blocks, fixed block-offset tree |
| `det_sort_by_key(slice, key)` | Stable sort | Keys implement `Ord`; floats enter only through `NonNan<f64>`; `EntityId` is the final tie-breaker |
| `exact_sum(&[f64]) -> f64` | Reproducible sum, independent of partitioning | Binned accumulation in the ReproBLAS method; correct for any data split, used where partitions differ between runs, for example distributed solves on different node counts |

Pairwise reduction also improves accuracy over naive left-to-right summation: its error bound grows with the logarithm of the element count instead of linearly. ReproBLAS reports that reproducible summation costs about 4 times a plain dot product on one Sandy Bridge core. Summing a million doubles on more than 512 Ivy Bridge cores costs less than 1.2 times, so `exact_sum` is reserved for global reductions in distributed solvers.

Rules enforced by Clippy `disallowed_methods` and `disallowed_types` in every crate that implements operations:

1. Floating-point `sum`, `product`, `reduce` and `fold` on rayon parallel iterators are forbidden, because rayon splits work adaptively at run time, so the combination tree can change between runs [rayon's documentation of this behavior not verified].
2. `rayon::current_num_threads` and similar queries are forbidden.
3. `std::collections::HashMap` and `HashSet` are forbidden; `IndexMap` and `IndexSet` with a fixed hasher are allowed, and output-relevant iteration uses insertion order or a sort. Hash values of `usize` keys differ between wasm32 and 64-bit targets, so hash order must never reach a result.
4. `usize` never appears in persisted or hashed data; indices there are `u32` or `u64`.
5. Pointer addresses never influence results. Allocator choice, and allocator randomization in tests, therefore cannot change outputs.

### Memory management

| Mechanism | Choice | Contract | Failure behavior |
| --- | --- | --- | --- |
| Global allocator, native | mimalloc v3 (v3.5.1, September 2026) | Process-wide allocator for UI and engine | Large allocations use `try_reserve`; failure becomes `ResourceExhausted` |
| Global allocator, browser | Rust's default wasm32 allocator in phase 0; phase 1 benchmark against mimalloc built for wasm32 | Same | Linear-memory growth failure becomes `ResourceExhausted` |
| Scratch arenas | `bumpalo` arena per operation evaluation, reset when the operation returns | Temporary data never outlives the operation; outputs move into CAS buffers | Arena allocations count against the operation's memory reservation |
| Memory budgets | `MemoryBudget` tree: process budget, then sub-budgets for CAS residency, GPU staging and operation scratch | Operations reserve before allocating more than 64 MiB | Reservation waits up to 2 s for evictions, then fails with `ResourceExhausted { requested, available, fix }` |
| Memory-mapped CAS objects | CAS objects of 1 MiB or more are read through read-only memory maps on native targets, through `Storage::map`, which `platform` implements with memmap2 | Objects are immutable: written to a temporary file, flushed, renamed into place and marked read-only | CAS on a network file system: mapping is disabled and buffered reads are used, detected through `statfs` or `GetDriveTypeW` |
| Out-of-core buffers | `ChunkedBuffer<T>`: a typed array in chunks of 1 MiB, each a CAS object hashed on its own; the residency manager pins chunks on access and evicts with a CLOCK policy under the budget | Algorithms visit chunks in index order through the deterministic combinators, so results are identical in memory and out of core | A chunk that fails its hash check on reload: `CasError::Corrupt { hash }`; Kiln recomputes it |

`ResourceExhausted` is a host failure, not a result. Kiln never caches it, and the UI suggests a fix: close other designs, raise the budget, or evaluate remotely.

Anvil meshes (vertex, index and adjacency arrays) and Flux Fields (nodal and quadrature-point values) larger than 64 MiB live in `ChunkedBuffer<T>`. PLT recommends that producers order elements along a space-filling curve such as a Morton curve, so spatially close data shares chunks. Consumers declare an access pattern (sequential, spatial or random) that the residency manager uses for prefetching; element order is part of the operation's output, so it is deterministic.

**Decision D-PLT-14:** mimalloc v3 is the native global allocator. *Why:* it is permissively licensed (MIT), ported to every Tier 1 OS and WASM, and its project reports outperforming jemalloc and tcmalloc on multi-threaded allocation benchmarks while noting those numbers date from 2021. *Rejected:* system allocators (behavior differs per OS, which complicates the memory budgets); jemalloc (no Windows support in the common Rust bindings [unverified]).

Phase 0 re-measures mimalloc, jemalloc and snmalloc on the PLT suite, and the choice cannot affect results.

Two OS-specific details apply. Windows refuses to delete a file that is mapped, so CAS garbage collection marks such objects delete-pending and retries after unmapping.

A mapped file truncated by another program raises SIGBUS on Unix. The CAS directory is private to the user and its files are read-only, so this needs outside interference. If it happens, the engine process crashes, the crash monitor tags the report `cas-truncated`, and the restarted engine verifies and quarantines the object before replaying the journal.

### SIMD

Status as of October 2026:

1. `std::simd` remains nightly-only; the portable-simd project publishes no stabilization timeline.
2. Rust 1.89 stabilized many AVX-512 intrinsics and target features.
3. Arm SVE support is experimental: tracking issue rust-lang/rust#145052 follows an experimental implementation of the not-yet-accepted RFC 3838 behind a feature gate, blocked on the Sized Hierarchy work (#144404).
4. WebAssembly SIMD128 intrinsics are stable in `core::arch::wasm32` [unverified this round]; relaxed SIMD exists but is nondeterministic by design.

The `simd` crate detects the instruction set once at startup (`is_x86_feature_detected!` for `avx2`, `fma`, `avx512f`, `avx512bw`, `avx512dq` and `avx512vl`; NEON is baseline on ARM64; SIMD128 is static on wasm32) and dispatches each kernel through a function table. A test and benchmark setting, `CRUCIBLE_ISA=x86-64-v2|x86-64-v3|x86-64-v4|neon|scalar`, forces a lower level. It never changes canonical results; in Native mode it also sets the `CpuIsa` class, so cache keys stay correct, and `scalar` is accepted in canonical mode only.

**Decision D-PLT-15:** Canonical kernels compute on fixed virtual vectors of 512 bits (8 × f64 or 16 × f32) on every instruction set, mapped onto native registers: four 128-bit registers on NEON, SSE and SIMD128, two 256-bit registers on AVX2, one 512-bit register on AVX-512. Horizontal reductions use the fixed lane tree defined for `det_sum`. *Why:* the order of every floating-point operation is then the same on every instruction set, so dispatch changes speed and never bits. *Rejected:* native-width accumulation (results change with the instruction set); scalar-only canonical code (forgoes 2 to 8 times the throughput).

Canonical kernels never use approximate instructions such as `rcp14`, `rsqrt14`, `FRECPE` or `FRSQRTE`, whose results differ across instruction sets.

The `simd` crate keeps an allow-list of intrinsics, and CI fails on any other.

Kernels use pulp for dispatch plumbing, a safe Rust abstraction that "dispatch[es] to equivalent vectorized versions based on the features detected at runtime" (MIT licensed). The fixed-width types of `std::simd` (`Simd<f64, 8>`) match the canonical layout and replace hand-written wrappers once stabilized. SVE replaces NEON on ARM64 servers when Rust stabilizes scalable vectors, under the same 512-bit canonical layout.

### GPU compute

Flux owns the choice of GPU algorithms; the `gpu` crate owns devices, memory, queues, kernel compilation, deterministic primitives, fallbacks and recovery.

| Backend | Path | Targets | f64 | Notes |
| --- | --- | --- | --- | --- |
| wgpu (30.0.1) | WGSL compiled by naga to SPIR-V, MSL, HLSL or WGSL | Vulkan, Metal, DX12, WebGPU, GLES 3.1 compute | `SHADER_F64` on Vulkan only | Subgroups, 64-bit integers and float atomics are native-only capabilities; `PIPELINE_CACHE` is implemented for Vulkan only |
| CubeCL on wgpu | `#[cube]` Rust kernels compiled to WGSL, SPIR-V or MSL | Same as wgpu | Same as wgpu | One kernel source for every backend; alpha with breaking changes between minor versions, so pinned per release |
| CubeCL CUDA | `#[cube]` kernels compiled to CUDA C++ | NVIDIA, servers and workstations | Native | Optional; never required for any capability |
| CubeCL ROCm | `#[cube]` kernels compiled to HIP | AMD, servers and workstations | Native | Optional; never required for any capability |
| CPU fallback | Canonical Rust implementation using `runtime` and `simd` | Every target | Native | Always present |

**Decision D-PLT-16:** Crucible's GPU kernels are written once as CubeCL kernels behind the `gpu::GpuCompute` trait, which runs on wgpu everywhere and on CUDA or ROCm where present; every GPU path has a registered CPU path, and the choice between them is explicit and reported. *Why:* one kernel source covers every backend, and a GPU that is missing, blocklisted or lost never removes a capability. *Rejected:* hand-written WGSL plus CUDA (two sources that drift); CUDA-first (no Apple GPUs and no browser).

The contract's single GPU abstraction holds at the kernel level: wgpu is the portable backend on every target, and CUDA and ROCm are optional accelerators that run the same CubeCL kernels behind the same trait, so they add speed and never a capability.

GPU results are not canonical. WGSL permits implementations to reassociate and fuse floating-point operations [WGSL section 15.7.5 not opened; unverified], Metal and WebGPU lack f64 compute, and subgroup sizes vary by vendor. Every GPU path therefore takes one of three roles, declared in its operation contract:

1. **GPU filters, CPU decides.** The GPU narrows candidates and canonical CPU code makes every result-affecting decision, as in Anvil's GPU sampling with certified CPU refinement for surface-surface intersection. The filter must be conservative under a certified error bound, so every true candidate appears on every device, and the CPU sorts candidates canonically so extra candidates never change the result. Results then stay in the canonical CPU class.
2. **Interactive fidelity.** The GPU computes an approximate result with an error estimate. Results carry the device's `GpuClass` and are cached only under it.
3. **GPU-class sign-off.** The result is bit-identical within one `GpuClass` and agrees with the CPU path within the declared tolerance, which the agreement oracle verifies. Kiln's policy decides where such results are accepted.

Deterministic GPU primitives in the `gpu` crate:

1. Reductions use two passes with a fixed topology: each workgroup reduces a 256-element tile through a fixed binary tree in workgroup memory, independent of subgroup size, and a second pass combines tile results in index order.
2. Floating-point atomics are forbidden in deterministic kernels. Scatter-add, such as finite-element assembly, sorts contributions by destination and applies a segmented reduction in a fixed order, or uses graph coloring.
3. Stream compaction uses prefix sums, never atomic append, so output order is fixed.
4. CubeCL autotuning chooses among kernel variants with different summation orders, so it changes bits. Deterministic modes run with autotuning off and a shipped tuning table per `GpuClass`; autotuning runs only for interactive fidelity.
5. Kernels needing more than f32 precision on Metal or WebGPU use Flux's mixed-precision refinement with canonical f64 residuals on the CPU, or double-float arithmetic (pairs of f32 values) from the `gpu` crate. Double-float arithmetic needs unfused, unreassociated operations, which WGSL does not guarantee, so each double-float kernel runs a self-test per `GpuClass` at device creation and falls back to the CPU path when the test fails.

Each dispatch is sized to finish within 100 ms, measured with timestamp queries, so Windows timeout detection and recovery never resets the device. Long kernels split into more dispatches; a split changes how many fixed tiles a dispatch covers, never the reduction topology, so results do not depend on it. When no adapter exists, the adapter is blocklisted, or compute is disabled in safe mode, Kiln records `ran_on: Cpu` with the reason, and the UI shows it.

## Numerical determinism

Kiln decides which determinism mode each operation runs in. This section defines the mechanisms behind those modes, the `PlatformClass` values that key the cache, and how agreement between classes is measured.

### Sources of divergence and their controls

| Source | Evidence | Control |
| --- | --- | --- |
| Implicit fusion of `a * b + c` | Rust's float semantics (RFC 3514) match IEEE 754-2008 and exclude implicit FMA contraction; Box2D found that "FMA must be disabled for cross-platform determinism" in C and C++ compilers | Rust code needs nothing. Any C or C++ code linked into the engine builds with `-ffp-contract=off` and no fast-math flags, and a CI check rejects other flags |
| Explicit FMA | Rust guarantees `mul_add` is "the rounded infinite-precision result", but x86-64-v2 and wasm32 have no FMA instruction, so it runs in software there | Canonical kernels use `mul_add` only inside `detmath` and error-free transformations; general kernels use separate multiply and add (D-PLT-18) |
| Platform math libraries | Rust documents `exp`, `ln`, `sin`, `powi`, `powf` and 26 other methods as having precision that "varies by platform, Rust version, and can even differ within the same execution"; Box2D found `atan2f` differs across platforms | `detmath` replaces them; Clippy `disallowed_methods` forbids the std methods in operation crates |
| Reduction order | Floating-point addition is not associative (ReproBLAS) | Deterministic combinators with data-defined trees |
| SIMD width | Different lane counts change summation order | Canonical 512-bit virtual vectors (D-PLT-15) |
| Approximate instructions | Reciprocal estimates differ by instruction set | Allow-list of intrinsics in the `simd` crate |
| Denormals and rounding mode | Rust assumes no flush-to-zero; changing the floating-point environment from inline assembly is undefined behavior (RFC 3514) | The engine never changes the floating-point environment. The flush-to-zero exception for NEON applies only to 32-bit ARM, which is not a target |
| Floating-point environment changed by foreign code | A driver or library that sets flush-to-zero or rounding control on a thread changes later results; Rust treats such changes as undefined behavior (RFC 3514) | Compute threads never run driver or plugin code. Each operation start checks that MXCSR (x86-64) or FPCR (ARM64) holds its default value, restores it if not, and logs `FpEnvironmentRestored` with the culprit module when known |
| x87 precision | RFC 3514 documents 32-bit x86 as non-conforming | 32-bit x86 is not a Crucible target |
| NaN bit patterns | NaN sign and payload are nondeterministic in Rust and in WebAssembly | NaNs are canonicalized at every operation output and in Wasm components (below) |
| Relaxed SIMD | `relaxed_madd` may round once or twice, and two calls with the same inputs may differ (relaxed SIMD overview) | Never used in the engine; disabled for Wasm components |
| Hash iteration order and `usize` width | Hash values differ between 32-bit and 64-bit targets | Lints from "Deterministic parallel combinators" |
| Thread count and scheduling | Work stealing changes execution order | Combinators partition by data, never by thread |
| GPU arithmetic | WGSL may reassociate and fuse [WGSL section 15.7.5 not opened]; no f64 on Metal or WebGPU; subgroup sizes vary | GPU results have their own classes (`PlatformClass::Gpu`) |
| Compiler and dependency upgrades | Code-generation bugs can change results despite specified semantics | The determinism suite runs on every toolchain or dependency bump; a change in any canonical hash blocks the bump or bumps the class epoch |

### The deterministic math library

`detmath` provides the elementary functions every operation uses, scalar and batched: `exp`, `exp2`, `exp_m1`, `ln`, `log2`, `log10`, `ln_1p`, `pow`, `powi`, `cbrt`, `hypot`, `sin`, `cos`, `tan`, `sin_cos`, `asin`, `acos`, `atan`, `atan2`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh`, `erf`, `erfc`, `tgamma` and `lgamma`, for f64 and f32, plus `min_total` and `max_total`, which order −0 below +0 and treat NaN as an error. `sqrt`, division and the basic operations come from the hardware, which IEEE 754 already makes correctly rounded.

**Decision D-PLT-17:** `detmath` implements correctly rounded functions in round-to-nearest, porting CORE-MATH (MIT licensed) wherever CORE-MATH provides correctly rounded code, and otherwise using a fixed sequence of IEEE basic operations with a documented error bound in ulps. *Why:* a correctly rounded result is unique, so every implementation, including a vectorized one, an FMA-free one for wasm32 or a later faster one, returns the same bits, and the functions are more accurate than platform libraries. *Rejected:* platform libm (documented as nondeterministic); porting musl or FreeBSD libm (deterministic once ported, but not correctly rounded, so every later optimization risks changing bits); Box2D-style approximations (deterministic but less accurate than CAD and simulation need).

A function without a correctly rounded implementation runs the same operation sequence on every target, with no ISA-specific fast path.

Correct rounding gives implementation freedom. The x86-64-v3, x86-64-v4 and NEON builds use hardware FMA in their fast paths; x86-64-v2 and wasm32 use FMA-free double-double paths; all return the same bits.

Batched versions run the fast path in SIMD lanes and send the rare lanes that fail the rounding test to the accurate scalar path. CORE-MATH code is already in GNU libc (seven binary64 functions from glibc 2.43 and a list of binary32 functions from 2.42) and in AMD libm 4.2, a sign that its speed is acceptable in production libraries.

Targets: scalar f64 `exp` and `ln` at most 1.5 times the cycles of glibc 2.43 on x86-64-v3; batched f64 `exp`, `ln`, `sin` and `cos` at least 2 times faster than the scalar loop on AVX2. These are targets measured by the PLT suite.

**Decision D-PLT-18:** Implicit contraction is impossible in Crucible's Rust code, and explicit `mul_add` is allowed in canonical kernels only inside `detmath` and error-free transformations (two-product, compensated sums). *Why:* FMA is correctly rounded, so it never breaks determinism, but software FMA on x86-64-v2 and wasm32 would slow every general kernel there; isolating it keeps both identical bits and browser speed. *Rejected:* FMA in all canonical kernels (multiplies browser cost in compute-bound kernels); banning FMA entirely (loses the accuracy of error-free transformations).

### Execution modes and platform classes

An operation may implement up to three execution modes. The operation's contract (ANV, FLX) declares which modes exist; Kiln's policy chooses one per evaluation; PLT guarantees each mode's determinism scope.

| Mode | Implementation | Bit-identical across | Cached under |
| --- | --- | --- | --- |
| Canonical | Canonical lanes, `detmath`, deterministic combinators, no ISA-specific arithmetic | Every Tier 1 CPU target, wasm32 included, at any thread count and ISA level | `PlatformClass::CpuCanonical { epoch }` |
| Native | Free to use native vector widths, hardware FMA and ISA-specific kernels; parallel work still uses data-defined partitioning, so thread count never matters | Targets with the same ISA level | `PlatformClass::CpuIsa { isa, epoch }` |
| GPU | Kernels on a GPU device | Devices in the same verified GPU class | `PlatformClass::Gpu(GpuClass)` |

**Decision D-PLT-19:** There is one canonical CPU platform class, `CpuCanonical`, shared by Windows, macOS, Linux, servers and browsers on x86-64, ARM64 and wasm32; the operating system is never part of a CPU class. *Why:* with no platform math library and no OS-dependent arithmetic, the OS cannot influence results, and one class lets a browser session, a laptop, a cloud worker and CI share every cached result. *Rejected:* one class per OS and architecture (multiplies cache misses and hides determinism bugs behind class boundaries); GPU results in the canonical class (WGSL permits fusion and reassociation).

`CpuIsa` classes are `x86-64-v2`, `x86-64-v3`, `x86-64-v4`, `arm64-neon` and `wasm32-simd128`. A `GpuClass` is the tuple (backend, vendor id, device family, driver version range, shader compiler, epoch), and only tuples listed in the verified-class registry count.

The registry is a signed data file built from GPU-lab runs of the determinism suite and shipped like the workaround database. An unlisted device gets `PlatformClass::Unverified`, and its results stay in the local cache of that machine.

The epoch is a small integer bumped when an unavoidable change, such as a fix for a compiler bug, alters any canonical output in the determinism corpus. A bump needs human approval, happens only at an LTS boundary unless it fixes wrong results, and invalidates cache entries of that class only.

Each release records the epoch it was built under. Reproducing it bit for bit after a bump uses an archived engine build of that epoch, which `cli` fetches and runs in a container; otherwise the agreement harness compares results within tolerance.

**Decision D-PLT-20:** Results of `CpuIsa`, `Gpu` and `Unverified` classes never substitute for canonical results. A check, release or proposal that requires canonical results recomputes them in canonical mode. *Why:* substitution would make a released result depend on the machine that happened to compute it first. *Rejected:* accepting any class within tolerance (makes released artifacts irreproducible bit for bit).

### Third-party numerical libraries

Libraries such as faer choose kernels by instruction set and may partition work by thread count [faer's partitioning behavior unverified]. A library runs in Native mode only in a configuration whose partitioning does not depend on thread count. It runs in canonical mode only in a qualified configuration that passes the canonical identity oracle on every Tier 1 CPU target, for example sequential execution with fixed block sizes inside a deterministic combinator.

For the kernels Flux needs in canonical mode (dense LU and Cholesky, triangular solves, sparse matrix-vector products), PLT and FLX either qualify such a faer configuration in phase 0 or provide canonical implementations in `runtime` built on the deterministic combinators.

### NaN canonicalization

Operations should report invalid numerics as typed errors rather than NaN values (ANV and FLX contracts). Where NaN is a legitimate value in an output, such as an undefined Field sample, the CAS serializer writes the canonical quiet NaN `0x7FF8_0000_0000_0000` (f64) or `0x7FC0_0000` (f32). Canonical results are therefore hashed identically even when hardware produced different payloads.

Operation code never inspects the sign or payload of a value that may be NaN (`to_bits`, `is_sign_negative`, `copysign`); a lint enforces this outside the serializer. `det_sort_by_key` accepts only keys that implement `Ord`, which floats implement only through the `NonNan` wrapper, so a NaN key is a typed error at construction rather than an order that depends on NaN bits.

### Measuring cross-class agreement

Principle 4 requires results from different classes to agree within declared tolerance. The agreement harness in `oracles/plt/agreement` measures this for each operation and output type, with tolerances declared by the owning operation and loosened only with human approval.

| Output type | Metric | Pass condition |
| --- | --- | --- |
| Plain number | Absolute and relative difference, and ulp distance (reported) | Below the operation's absolute plus relative tolerance |
| Body as B-rep | Topological isomorphism that preserves `EntityId`s, then the maximum Hausdorff distance from Anvil's certified sampler | Identical topology and distance at most the operation's `ErrorBound` |
| Body as mesh or implicit | Two-sided Hausdorff distance and volume difference | Within the declared bound |
| Field | Relative L2 and L-infinity norms of the difference at a shared set of sample points, plus declared integral quantities such as reaction forces | Within the declared tolerance |
| Solver output | Relative residual of each result in the other class's discretization, plus error against a reference solution where one exists | Within the declared tolerance |

The harness runs every golden product and the operation corpus in every class: canonical against each `CpuIsa` class and each verified `GpuClass`. It records the worst case per operation and fails CI when any metric exceeds its tolerance.

### The determinism suite

The suite is the phase 0 gate and runs on every commit to `main`.

1. **Corpus.** Golden-product builds, the operation corpus from ANV and FLX, a Wasm component corpus, and 10,000 randomly generated operation graphs per night from a fixed seed list.
2. **Canonical identity.** The corpus runs in canonical mode on Windows x86-64 (a runner with AVX-512) with `CRUCIBLE_ISA` forced to each of x86-64-v2, x86-64-v3 and x86-64-v4; on Windows ARM64; on macOS ARM64; on Linux x86-64 and ARM64; and on wasm32 in Chrome, Firefox, Safari and Node, threaded and single-threaded. Every output hash must match the reference.
3. **Schedule independence.** Each target repeats the corpus with 1, 2, 3, 8 and 64 threads, with randomized work-stealing delays injected by a test hook, and with allocator randomization.
4. **Out-of-core equivalence.** The corpus repeats with a 64 MiB memory budget, forcing chunks to disk, and must produce the same hashes.
5. **Native and GPU classes.** Repeated runs within each `CpuIsa` and verified `GpuClass` must be bit-identical, and the agreement harness must pass.
6. **`detmath` correctness.** Every univariate f32 function is tested exhaustively over all 2^32 inputs against MPFR, which runs in the oracle tooling only and is never linked into shipped binaries. Bivariate f32 functions and every f64 function are tested on CORE-MATH's hard-to-round cases and 10^9 random inputs per function per night.

A failure names the first operation whose output diverged, the two targets, the input hashes and the first differing value, so the bug is located without bisecting.

## Wasm component runtime

Wasm components must give bit-identical results in Wasmtime on every native target, in Wasmtime's Pulley interpreter on iPadOS, and in each browser's own WebAssembly engine. Browsers expose none of Wasmtime's determinism settings, so Crucible enforces deterministic semantics in the Wasm component's bytecode, where every engine must honor it.

### Status as of October 2026

1. WASI 0.3.0 shipped on 11 June 2026 and 0.3.1 on 11 August 2026; Wasmtime 46 and later enable it by default (WASI roadmap). Wasmtime's own `Config` documentation still calls its support for the Component Model's async ABI "very incomplete".
2. Wasmtime releases a new major version on the 20th of each month. Releases whose number is a multiple of 12 are long-term support (LTS) releases, supported for 24 months; other releases get 2 months. Wasmtime 48.0.0, released on 20 August 2026, is therefore an LTS release.
3. jco transpiles Wasm components into ES modules for browsers and Node; its WASI 0.3 shim targets Node only (jco 1.25.2, July 2026).

**Decision D-PLT-21:** Crucible embeds Wasmtime pinned to LTS releases (48 from phase 0, then 60), takes security patches within 7 days, and moves between LTS releases only after the determinism suite passes. *Why:* a 24-month support window matches Crucible's own LTS channel, and engine upgrades then happen yearly. *Rejected:* tracking monthly releases (each forces recompilation of every cached Wasm component and re-verification); Wasmer (smaller ecosystem around the Component Model and WASI 0.3 [unverified]).

### The instrumentation pass

`wasm-host` rewrites every core module inside a Wasm component once, at install. It also sets each core module's memory maximum to the limit declared in the Wasm component's package metadata (default 256 MiB, at most 4 GiB), so the host can reserve memory before instantiation.

The pass is deterministic and versioned (`instrument@1`). Its output is stored in the CAS, and only instrumented bytes ever execute.

| Rewrite | Problem it removes | Evidence |
| --- | --- | --- |
| Fuel metering: each basic block subtracts its cost from a fuel global and calls the host's `checkpoint` when the global goes negative; the host checks cancellation, then refills the global with the next slice or traps with `FuelExhausted` once the call's total fuel is spent | Engines meter differently or not at all, and browsers cannot meter | Wasmtime recommends fuel over epochs for deterministic interruption; injected metering gives "a uniform gas metering implementation across different execution engines" (wasm-instrument) |
| Stack-height metering with a fixed logical limit, set below the smallest real stack of any supported engine so the logical limit always trips first | Stack limits differ between engines, so stack overflow is engine-dependent | wasm-instrument's stack-height limiter: "meter the stack height at runtime and abort the execution when it reaches a predefined limit" |
| NaN canonicalization at every point where NaN bits become observable: float stores, `reinterpret`, the sign operand of `copysign`, values passed to imports or returned from exports, and the outputs of every float SIMD operation | NaN sign and payload are nondeterministic in WebAssembly | WebAssembly nondeterminism list; the Wasm 3.0 deterministic profile fixes NaN results the same way |
| Guarded `memory.grow` and `table.grow`: growth below the declared maximum that fails for host reasons traps with a host-failure marker instead of returning −1 | `memory.grow` may "non-deterministically succeed or fail" | Wasmtime deterministic-execution guide |
| Rejection of relaxed SIMD, shared memories and atomics | Relaxed SIMD results may differ between calls; shared memory makes results nondeterministic | Relaxed SIMD overview; WebAssembly nondeterminism list |

The fuel cost table belongs to `instrument@1`: one unit per instruction, with fixed surcharges per byte for bulk-memory instructions. Arithmetic order never changes, so these rewrites cannot alter a numeric result.

**Decision D-PLT-22:** Fuel, stack limits, NaN canonicalization and growth guards are enforced by Crucible's own instrumentation of Wasm component bytecode, identical on every engine; Wasmtime's epoch interruption is never used, and Wasmtime's built-in fuel serves only as a cross-check in tests. *Why:* browsers cannot meter fuel or canonicalize NaNs, and Wasmtime's own fuel costs change between releases (release 48 added configurable costs for variable-length opcodes, and 49 changed costs in constant expressions), so engine-side mechanisms would make fuel exhaustion depend on the engine and its version. *Rejected:* Wasmtime's `consume_fuel` plus `cranelift_nan_canonicalization` (native only, so browser results would diverge); epochs (nondeterministic by Wasmtime's own documentation); running Wasm components in the browser on Pulley compiled to wasm32 (identical semantics but an interpreter inside an interpreter [slowdown not measured]).

The instrumentation version is part of the cache key of every Wasm component call. Phase 0 measures the pass's overhead on the Wasm component corpus; the target is at most 10% over uninstrumented code in Wasmtime (target).

### Wasmtime configuration

| Setting | Value | Reason |
| --- | --- | --- |
| Compiler | Cranelift, `OptLevel::Speed`; Pulley (`pulley64`) on iPadOS and on any target where Cranelift cannot generate code | Cranelift supports x86-64 and AArch64; Wasmtime uses Pulley "if it's not supported" |
| Compilation | Ahead of time at install: `Engine::precompile_component`, stored in the local CAS under hash(instrumented Wasm component, Wasmtime version, `Config` fingerprint, target, CPU features) | Moves compile latency out of evaluation; artifacts load only into the same Wasmtime version and configuration |
| Loading precompiled code | Only artifacts that this machine compiled, or that Crucible's build service compiled and signed, after a hash check | Deserializing precompiled code trusts it as machine code |
| Shipped std Wasm components | Precompiled per target and included in installers and offline bundles | No first-run compile delay |
| `wasm_relaxed_simd` | `false` | Relaxed SIMD may differ "across x86_64 and AArch64" |
| `wasm_threads` | `false` | Shared memory is nondeterministic |
| `wasm_memory64` | `false` | Browsers cap 64-bit memories at 16 GiB, Safari lacks them, and they cost speed |
| `epoch_interruption` | `false` | Fuel is the only interruption mechanism |
| `consume_fuel` | `false` in release; `true` in the test harness | Cross-checks the injected meter |
| `memory_reservation` | 4 GiB with guard regions | Lets Cranelift elide bounds checks for 32-bit memories |
| Wasm instance allocation | Pooling allocator sized from the memory budget | Fast instantiation for many short calls |
| Resource limiter | Grants growth up to the declared maximum; reserves that maximum in the `MemoryBudget` before instantiation | A Wasm component either never starts or never observes a host-caused growth failure |

### Worlds, calls and failures

ECO defines Wasm component worlds and capabilities; PLT enforces them. The evaluation world imports only Crucible interfaces, such as Body and Field access, chunked buffers, deterministic diagnostics and `checkpoint`, and never WASI clocks, random, filesystem or sockets. A Wasm component importing anything else fails at install with `WasmComponentError::ForbiddenImport { import, fix }`, whose fix names the world that grants it.

Functions in the evaluation world are synchronous. They need no IO, and synchronous calls transpile with jco for every browser without the WASI 0.3 async shims, which target Node only. Async functions stay available in tool worlds that run outside evaluation on native targets and the server.

| Failure | Deterministic | Cached by Kiln | Behavior |
| --- | --- | --- | --- |
| Trap in Wasm component code | Yes | As a failed result | `WasmComponentError::Trap { code, function, fix }` |
| Fuel exhausted | Yes, under one `instrument@N` | As a failed result | `FuelExhausted { used, limit }`; the fix suggests raising the fuel limit in the feature or reporting a hang |
| Logical stack exhausted | Yes | As a failed result | `StackExhausted { limit }` |
| Growth beyond the declared maximum | Yes (`memory.grow` returns −1) | Decided by the Wasm component | Visible to the Wasm component as standard Wasm behavior |
| Host could not provide memory below the declared maximum | No | Never | `ResourceExhausted`; Kiln retries once, then suggests remote evaluation |
| Cancelled at a checkpoint | No | Never | `Cancelled` |

A Wasm component that needs more than 4 GiB of data reads it through the chunked-buffer interface backed by `ChunkedBuffer<T>`. A Wasm component that wants data parallelism exports a chunk function in its world; the host runs chunks on separate Wasm instances through the deterministic combinators and merges results in index order. Each Wasm instance stays single-threaded.

### In the browser

The engine worker transpiles each instrumented Wasm component once with jco's transpiler, run inside the engine worker [in-browser use of jco's transpiler unverified], and caches the result in OPFS. Core modules are compiled by the browser's WebAssembly engine and run in the engine worker or compute workers.

Each Wasm component has its own linear memory, so arguments are copied by the canonical ABI, and bulk data moves through chunked buffers in calls of at least 1 MiB to amortize the crossing. The single-threaded web build runs Wasm components on the engine worker in fuel slices of about 10 ms, yielding to the event loop at each `checkpoint`.

## Packaging, distribution and updates

In this section, "app package" means an OS installation format such as MSIX, deb or an app bundle. It is unrelated to packages in the package registry.

### Formats per target

| Target | Format | Signing | Update mechanism | Enterprise deployment |
| --- | --- | --- | --- | --- |
| Windows x86-64 and ARM64 | MSIX, one app package per architecture | Authenticode with a certificate whose key lives in a hardware security module; MSIX app packages must be signed before installation | Crucible updater: verifies TUF metadata, downloads only changed 64 KB blocks using the app package's block map, installs through the Windows PackageManager API | Intune, Configuration Manager and the Enterprise Modern App Management CSP, which the MSIX documentation lists as fully supported |
| macOS | Signed app bundle in a DMG | Developer ID Application certificate, hardened runtime, secure timestamp, notarized with `notarytool`, ticket stapled | Crucible updater: delta of the bundle applied to a staged copy, signature verified, bundle swapped at restart | MDM-installable flat installer (`.pkg`) signed with a Developer ID Installer certificate; settings through configuration profiles |
| Linux x86-64 and ARM64 | `.deb` and `.rpm` in signed apt and dnf repositories; Flatpak; AppImage | Repository metadata signed with OpenPGP; Flatpak repository signed; AppImage covered by TUF metadata | apt and dnf for deb and rpm, Flatpak for Flatpak, the Crucible updater for AppImage | Internal repository mirrors; `/etc/crucible/policy.json` |
| Browser | Content-hashed static assets plus a service worker | HTTPS; Subresource Integrity on the entry script | New version activates at the next load or on user approval | Self-hosted team server serves the same assets |
| iPadOS and iOS | App Store; TestFlight for beta | Apple distribution signing | App Store | Managed distribution through Apple Business Manager and MDM [unverified for this app category] |
| Android | Google Play app bundle; signed APK for managed devices | Play app signing; APK signature scheme | Google Play or MDM | Managed Google Play [unverified] |
| Servers | OCI images for x86-64 and ARM64; Helm chart | Image signatures and SLSA provenance attestations | Image tags per channel; the operator upgrades | Air-gapped registry mirror |
| `cli` | Included in every desktop app package; standalone archives with a `.sha256` and signature | Same as the host app package | Same as the host app package | Same |

The macOS bundle declares `com.apple.security.cs.allow-jit`, because the hardened runtime that notarization requires blocks writable executable memory and Wasmtime's Cranelift compiles at run time. Apple's notarization guide names `allow-jit` as the entitlement for hosts that run a JavaScript engine, the same class of need. Because Wasm components normally run from code precompiled at install, the entitlement is exercised only when a Wasm component is installed or upgraded.

**Decision D-PLT-23:** Windows ships as MSIX. *Why:* MSIX gives clean install and uninstall, package identity (which Windows APIs such as push notifications and background tasks require), 64 KB block-level differential updates and full Intune and Configuration Manager support. *Rejected:* MSI (no package identity, no block-level updates, and uninstall quality depends on authoring); a custom installer executable (repeats what MSIX provides).

Organizations whose tools require MSI receive an MSI that installs the MSIX [MSIX-in-MSI wrapping mechanism unverified], decided in phase 1.

**Decision D-PLT-24:** Linux ships as deb and rpm repositories, Flatpak and AppImage, all built from one binary per architecture linked against the glibc 2.34 floor. *Why:* deb and rpm serve managed fleets, Flatpak serves sandboxed desktop installs across distributions, and AppImage serves users without administrator rights. *Rejected:* Snap only (Ubuntu-centric); distribution-specific builds (multiplies testing).

### Signed delta updates

**Decision D-PLT-25:** Every self-updating channel verifies updates with The Update Framework (TUF, specification 1.0.37), using offline threshold-signed root and targets keys and automated online snapshot and timestamp keys; OS-native mechanisms (MSIX, apt, dnf, Flatpak, app stores) carry the bytes where they exist. *Why:* TUF defends against arbitrary installation, endless data, fast-forward, indefinite freeze, mix-and-match and rollback attacks, malicious mirrors, wrong software installation and key compromise, which a single signing key does not. *Rejected:* a signature on a manifest alone (no defense against freeze or rollback); Velopack (MIT-licensed and written in Rust, with delta updates on Windows, macOS and Linux, but its README documents no defense against freeze or rollback); Sparkle (macOS only).

TUF roles and keys:

| Role | Signs | Keys | Threshold | Expiry |
| --- | --- | --- | --- | --- |
| Root | The keys of every other role | 5 offline keys held by separate people in hardware tokens | 3 of 5 | 1 year |
| Targets | Hashes and lengths of every artifact, per channel, delegated to one role per channel | 3 keys in hardware security modules | 2 of 3 | 3 months |
| Snapshot | The versions of all targets metadata | 1 online key in a cloud key service | 1 | 7 days |
| Timestamp | The hash of the snapshot | 1 online key | 1 | 1 day |

Update flow on desktop:

1. The updater checks the timestamp metadata every 4 hours and at startup. The check is a single small request; enterprise policy can disable it.
2. It verifies timestamp, snapshot and targets in order, rejecting expired metadata and any version lower than the one installed.
3. It downloads the delta for the installed version: changed 64 KB blocks on Windows; on macOS and for AppImage, per-file patches. Executables get Zucchini patches, the Chromium patcher that models references inside PE and ELF binaries; Mach-O binaries and other files get generic binary patches, because Zucchini lists no Mach-O support.
4. It reconstructs every changed file in a staging directory and verifies each against the TUF targets hashes. A failed hash discards the delta and downloads the full file.
5. It installs at the next start, or immediately if the user agrees, never during an evaluation. The previous version stays installed.
6. The new version runs a self-test within 60 s of its first start: engine start, GPU initialization, opening and rebuilding a bundled sample design and comparing its hash. A failed self-test or two crashes within the first 10 minutes roll back to the previous version and file a report.

Releases roll out in stages, as Chrome and Firefox do [their rollout mechanics not opened]: 1%, 10%, 50% and then 100% of stable installs over at least 4 days. Rollout halts automatically when the crash rate of the new version exceeds the previous version's by 20% (target threshold), measured only from users who opted in to crash reporting.

Targets: the median delta for a stable release at most 15% of the full app package size, and the update check at most 2 KB of transfer when nothing changed. These are targets.

### Air-gapped installs

1. An **offline bundle** is one signed archive per release containing installers for every desktop target, the std packages, precompiled std Wasm components for each target, the GPU workaround database, the verified `GpuClass` registry, TUF metadata, SBOMs and provenance. Debug symbols are available as a separate bundle.
2. `crucible mirror import <bundle>` verifies the vendor's TUF metadata at import time and publishes the content on an internal mirror that also serves as a package-registry mirror.
3. Air-gapped clients trust the organization's own TUF root, installed by policy. That root delegates targets to the vendor's targets keys, so artifacts keep end-to-end vendor signatures while the organization controls snapshot and timestamp freshness.
4. With no network at all, `crucible install --offline <bundle>` installs from removable media and verifies against the vendor root embedded in the installer.
5. Telemetry and crash uploads are disabled in air-gapped mode. Crash reports can be exported as files for manual submission.

### Enterprise policy

One policy schema applies on every OS, delivered through ADMX templates (Windows), configuration profiles (macOS), `/etc/crucible/policy.json` (Linux), the server's configuration (browser) and MDM app configuration (iPadOS, Android).

| Policy | Values | Default |
| --- | --- | --- |
| `update.channel` | `stable`, `lts`, `beta`, `nightly` | `stable` |
| `update.mode` | `automatic`, `notify`, `disabled`, `mirror:<url>` | `automatic` |
| `update.pin` | A release line, such as `2027.3` for an LTS line | None |
| `telemetry.performance` | `off`, `opt_in` | `opt_in` (asks the user) |
| `crash.upload` | `off`, `ask`, `stack_only` | `ask` |
| `registry.allowed` | List of package registry URLs | Public registry |
| `server.url` | Team server URL | None |
| `gpu.compute` | `auto`, `cpu_only` | `auto` |
| `network.proxy` | `system`, an explicit proxy URL, or a PAC URL | `system` |

Policies are visible to the user under Settings with the source of each value. A policy-locked setting says which policy locked it.

## Reliability

The goal is that no crash, driver fault or power loss costs the user more than one second of edits, and that every failure reaches engineers as a symbolicated, deduplicated report.

### Crash handling

| Mechanism | Choice | Contract | Failure behavior |
| --- | --- | --- | --- |
| Crash capture, native | A small crash-monitor process started first by the shell; the UI, engine and plugin-host processes connect to it at start. Built on Embark's `crash-handler` and `minidumper` crates, which use `minidump-writer` | On a fatal signal or exception, the crashing process sends its crash context over IPC, and the monitor writes a minidump from outside | If the monitor itself is gone, the process writes a minimal in-process report (signal, faulting module and offset) to the crash directory |
| Crash capture, mobile | Android: `crash-handler`, which lists Android support on arm and aarch64. iPadOS: the OS's own crash reports, collected through MetricKit [unverified] | Same signatures on the crash server | Missing reports reduce coverage only |
| Windows ARM64 capture | `crash-handler` lists Windows support for x86-64 only. Crucible adds ARM64 support upstream in phase 0; until it lands, ARM64 uses Windows Error Reporting local dumps configured by the installer [WER local-dump configuration unverified] | Same minidump format | Same |
| Panics, native | `panic = "unwind"` in the engine; a panic inside an operation is caught at the operation boundary | Returns `OperationError::InternalPanic { crash_id }`, never cached; Kiln poisons the operation for the session after 2 panics | A panic outside an operation aborts the engine process, which then restarts |
| Panics, browser | `panic = "abort"`; a panic hook records the message and the Wasm stack, then the engine worker restarts | Report symbolicated on the server from the build's DWARF and name section | The UI shows "engine restarted" and replays the journal |
| Minidump processing | rust-minidump (`minidump-processor`, `minidump-stackwalk`) on the crash server | Stack traces, module list, crash signature | Unsymbolicated frames are kept as module plus offset |
| Symbol server | CI uploads Breakpad symbol files plus native PDB, dSYM and DWARF for every build, retained 2 years for stable releases and the full support period for LTS | Serves Breakpad and Microsoft symbol-server path layouts | Missing symbols block a release promotion |
| Hang detection | UI watchdog: no event processed for 2 s records a main-thread stack sample; engine watchdog: a compute thread that passes no cancellation checkpoint for 10 s records its stack | Reported like crashes, with the signature `hang:` | The UI stays responsive because the engine is a separate process |

Privacy rules for crash reports:

1. Minidumps contain thread stacks, registers and the module list, never heap memory. Stack memory can hold fragments of design data, so the default upload policy is `ask`, showing what will be sent.
2. Paths are scrubbed: the user's home directory becomes `~`, and design repository paths become hashes.
3. Reports go only to the Crucible crash server or the organization's own server named by policy. Air-gapped installs keep reports locally for manual export.
4. Reports are deleted after 90 days.

Crash signatures (top frames of the crashing thread, normalized) group reports. Release promotion requires a crash-free session rate of at least 99.8% over the beta channel's last 7 days (target).

### Autosave and recovery

`repo` records every edit as a fine-grained immutable change. PLT supplies the durability mechanism beneath it: the edit journal and crash-consistent storage primitives.

1. **Journal format.** An append-only file per open design repository. Each record holds its length, a sequence number, the payload (a `repo` change) and a CRC-32C checksum.
2. **Write policy.** Records are appended immediately and flushed to stable storage in groups at most every 1 s, and at once on explicit save, window close and power-state changes. The engine uses `fdatasync` on Linux, `FlushFileBuffers` on Windows, `fcntl(F_FULLFSYNC)` on macOS [Apple's fsync semantics not opened; unverified], and `FileSystemSyncAccessHandle.flush()` in the browser.
3. **Bound on loss.** On native targets, a process crash loses nothing that was appended, because the operating system keeps written data, and a power failure loses at most the last second of edits. In the browser, a tab or worker crash may lose unflushed OPFS writes [unverified], so loss there is bounded by the same 1 s flush interval.
4. **Clean-shutdown marker.** The engine sets a marker on start and clears it on clean exit.
5. **Recovery.** After an unclean exit, the engine reads the journal, truncates at the first record with a bad checksum or sequence gap, replays the remaining records into `repo`, and shows "Recovered N edits from <time>". Replayed edits re-evaluate from cache, so recovery of a cached design takes under 2 s (target).
6. **Compaction.** When `repo` has durably stored the changes, the journal is truncated with a new file and an atomic rename.

CAS writes are crash-consistent without the journal: write to a temporary file in the same directory, flush, rename to the content hash, flush the directory on Unix. A torn or partial object fails its hash check on read and is recomputed or refetched.

### GPU device loss

wgpu reports device loss through its device-lost callback and failed submissions. Device loss follows a fixed recovery sequence:

1. In-flight GPU operations fail with `DeviceLost`, which is never cached.
2. The `gpu` crate recreates the adapter and device after 100 ms, then 1 s, then 5 s.
3. GPU buffers are recreated lazily from their CAS sources; no GPU buffer holds data that exists nowhere else.
4. Kiln reruns the failed operations on the recovered device, or on the CPU path if recovery fails.
5. After 3 losses within 10 minutes, GPU compute is disabled for the session, the UI shows "GPU compute disabled after repeated driver resets", and a report proposes a workaround entry.

The UI renderer uses the same recovery hooks for its own resources (UIX).

### Driver-bug workaround database

The `gpu` crate ships a signed data file, `gpu-workarounds.json`, matched against the adapter before the first device is created. Chromium handles GPU driver bugs with a similar data-driven list [Chromium's GPU blocklist documentation could not be opened].

| Field | Meaning |
| --- | --- |
| `id`, `description`, `bug` | Stable id, human description, link to the issue |
| `os`, `os_version` | OS and version range |
| `backend` | Vulkan, Metal, DX12, GL or WebGPU |
| `vendor_id`, `device_ids` | PCI vendor and device ids from wgpu's `AdapterInfo` |
| `driver_version` | Version range parsed per vendor format |
| `actions` | From a closed list: `disable_gpu_compute`, `prefer_backend:<b>`, `disable_feature:<f>` (subgroups, f16, 64-bit atomics, pipeline cache), `max_dispatch_ms:<n>`, `max_buffer_size:<n>`, `exclude_from_gpu_class` |
| `reproducer` | The GPU-lab test that fails without the workaround |

Rules:

1. Every entry has a reproducer and a bounded driver range. When a newer driver passes the reproducer in the GPU lab, the range closes.
2. The file updates through TUF independently of app releases, and offline bundles include the current version.
3. The active workarounds appear in the About dialog and in every crash and performance report.
4. A workaround never changes canonical results, because canonical results never depend on the GPU.

### Safe mode

Safe mode starts when the user passes `--safe-mode` or holds Shift during launch, and automatically after 2 consecutive crashes during startup. It:

1. disables GPU compute and asks UIX for its most conservative renderer configuration (on Windows, the WARP software adapter [wgpu support unverified]; on Linux, Mesa's lavapipe software Vulkan driver where installed; macOS always has Metal);
2. disables the plugin host and every Wasm component that the opened design's lockfile does not require;
3. resets window layout and UI caches, but never touches design repositories, the CAS or settings files;
4. shows a banner naming what was disabled and why, with a button that restarts normally.

Safe mode never changes a canonical result, because canonical results never depend on the GPU or on anything outside the design's lockfile.

### Graceful degradation

At startup `platform` builds a `HardwareProfile` (cores, memory, ISA level, GPU class and memory, battery, thermal state) and assigns a profile band: low, mid or high (defined in "Performance engineering"). Every degradation is explicit and listed in a Performance panel.

| Condition | Degradation | What the user sees |
| --- | --- | --- |
| No usable GPU, or GPU blocklisted | CPU fallback for all compute; UIX lowers render quality | "Running on CPU" in the status bar, with the reason |
| Memory below the low band, or memory pressure | Smaller CAS residency budget; out-of-core earlier; fewer background threads | "Low memory: large models will use disk" |
| On battery or thermally throttled | Background pool halved; prefetch paused | Battery icon in the Performance panel |
| Heavy operation estimated beyond the local budget | Offer remote evaluation when a team server or cloud worker is configured | "This simulation needs about 24 GiB; run it on the team server?" |
| Browser without cross-origin isolation | Single-threaded engine | "Threads unavailable: the site is not cross-origin isolated" |
| Browser without WebGPU | WebGL2 rendering and CPU compute | "WebGPU unavailable in this browser" |

## Build and release engineering

### Toolchain and dependencies

1. `rust-toolchain.toml` pins one stable Rust version for the workspace; the pin moves at most every 6 weeks, after the determinism suite passes on the new version. A separate pinned nightly builds only the threaded web engine (D-PLT-10).
2. `Cargo.lock` is committed, and `cargo vendor` snapshots every dependency for each release, so release builds and air-gapped builds need no network.
3. cargo-deny runs on every pull request: licenses (no GPL or AGPL linked into core crates, per the contract), RustSec advisories, banned crates and allowed registries [cargo-deny capabilities not verified].
4. A new dependency of any core crate needs review by a PLT owner, recorded in `deps/approved.toml` with its license, maintainer status and reason.

### Workspace build times

**Decision D-PLT-26:** Cargo stays the only build system, accelerated by sccache with a shared remote cache for CI and opt-in for developers, plus workspace structure rules that keep crates cacheable. *Why:* the contract fixes one Cargo workspace, and sccache supports Rust with S3, GCS, Azure, Redis, GitHub Actions and WebDAV backends and icecream-style distributed compilation. *Rejected:* Bazel or Buck2 (a second build description for every crate, against the single-workspace decision); no shared cache (every CI run recompiles the whole workspace).

sccache cannot cache crates that invoke the system linker (`bin`, `dylib`, `cdylib`, `proc-macro`) or incrementally compiled crates, and needs matching absolute paths unless `SCCACHE_BASEDIRS` strips them. The workspace therefore follows four rules:

1. Binaries are thin: each `apps/` binary is a `main.rs` calling into a library crate.
2. Proc-macro crates stay small and few.
3. CI builds with `CARGO_INCREMENTAL=0` and a fixed checkout path; developers keep incremental builds locally.
4. Large crates split along their dependency structure when a change to one module rebuilds more than 25% of the workspace (measured by `cargo xtask rebuild-impact`).

Targets on the mid reference machine: a no-op `cargo check` under 2 s; editing one function in `anvil-ops` and running its unit tests under 20 s; a clean CI build with a warm remote cache under 6 minutes per target. These are targets.

### Reproducible builds

1. Builds set `--remap-path-prefix` for the workspace, the Cargo home and the toolchain, and `SOURCE_DATE_EPOCH` to the commit time.
2. Archives (DMG contents, deb, rpm, AppImage, MSIX payload, the offline bundle) list files in sorted order with normalized timestamps and permissions.
3. Two independent builders, on different cloud accounts with different machine images, build every release. The unsigned artifacts must match byte for byte before signing; signatures, which include timestamps, are applied afterwards.
4. A mismatch blocks the release, and `cargo xtask repro-diff` reports the first differing file and section.

Bit-reproducible Windows PE and macOS Mach-O outputs may need linker flags beyond these steps [toolchain-specific behavior unverified]. Phase 0 establishes reproducibility for Linux and wasm32 first and extends it per target.

### Cross-compilation

| Artifact | Built on | Method |
| --- | --- | --- |
| Linux x86-64 and ARM64 | Native Linux runners for each architecture | Container with a glibc 2.34 sysroot |
| Windows x86-64 and ARM64 | Windows x86-64 runners; ARM64 cross-compiled with the MSVC ARM64 toolchain, tested on native ARM64 runners | Rust MSVC targets (both Tier 1 with host tools) |
| macOS ARM64 | macOS runners on Apple silicon | Xcode toolchain; signing and notarization in a separate CI step that holds the credentials |
| iPadOS and iOS | macOS runners | Xcode; `aarch64-apple-ios` (Rust Tier 2) |
| Android | Linux runners | NDK r28 or later for 16 KB page alignment; `aarch64-linux-android` (Rust Tier 2) |
| Browser | Linux runners | Stable `wasm32-unknown-unknown` for the single-threaded build; pinned nightly with `-Zbuild-std` for the threaded build; wasm-bindgen; wasm-opt |
| Server images | Linux runners for both architectures | Multi-architecture OCI build from the Linux binaries |

### CI matrix

| Stage | Trigger | Runs | Time budget |
| --- | --- | --- | --- |
| Pull request | Every push to a proposal branch | Format, Clippy with the determinism lints, layering check, unit tests on Linux x86-64, wasm32 build, determinism suite subset (canonical hashes on Linux x86-64 and wasm32 in Node) | 15 minutes (target) |
| Merge queue | Every commit to `main` | Every Tier 1 target: build and unit tests; full canonical determinism suite on every Tier 1 CPU target and in Chrome, Firefox and Safari; golden-product checks on the CPU path; instruction-count benchmarks; GPU paths against software Vulkan in containers | 45 minutes (target) |
| Nightly | Daily | GPU lab: GPU paths and verified-class checks on real hardware; wall-time benchmarks on the reference machines; 10,000 random operation graphs; fuzzing; Tier 3 builds weekly | 6 hours |
| Release | Each release candidate | Everything above, plus installers, install and uninstall tests per format, update tests from the last 3 releases, Tier 2 device farm, reproducibility check, SBOM and provenance generation | 12 hours |

The GPU lab is a pool of self-hosted machines. At minimum it covers NVIDIA (one consumer and one professional card), AMD (two generations), Intel (one integrated and one discrete), Apple silicon (base and Pro-tier chips), Qualcomm Snapdragon X under Windows ARM64, and Android tablets with Adreno, Mali and Xclipse GPUs. Each machine runs one CI task at a time with a fixed driver version, and driver upgrades go through a canary machine first.

Chromium's GPU testing runs on physical hardware in a Swarming pool with pixel tests, WebGL conformance and GPU integration suites; Crucible's lab follows the same model at a smaller scale.

### Release channels and versions

| Channel | Cadence | Contents | Support |
| --- | --- | --- | --- |
| Nightly | Daily from `main` | Everything merged | None; auto-updates daily |
| Beta | Branched from `main` every 6 weeks | Fixes only after branching | Until the next beta |
| Stable | Every 6 weeks, from the previous beta | Fixes only | Until the next stable, plus security fixes for 4 weeks |
| Long-term support (LTS) | One stable release per year becomes LTS | Security fixes, crash fixes and fixes for wrong results; no new capabilities | 24 months, so two LTS lines overlap for 12 months |

Version numbers are calendar-based: `2027.3.0` is the third stable release of 2027, and patch releases increment the last number. An LTS line keeps its `CpuCanonical` epoch, Wasmtime LTS line and instrumentation version for its whole life, so a design built on an LTS line produces identical results on every patch release of that line.

**Decision D-PLT-27:** Releases follow a 6-week train (nightly, beta, stable) with one LTS release per year supported for 24 months, aligned with Wasmtime's 24-month LTS window. *Why:* engineering organizations qualify tool versions and cannot requalify every 6 weeks, while the train keeps fixes flowing to everyone else. *Rejected:* monthly releases with no LTS (too fast for qualified environments); LTS lines longer than the underlying Wasmtime LTS (Crucible would have to maintain an unsupported engine).

Longer support for regulated industries is an open question.

Old designs keep their results across upgrades because they pin operation behavior versions in their lockfile (ANV, FLX). PLT's part is that no release changes a canonical result of a pinned behavior version except through a declared epoch bump, which the determinism suite would detect.

### Software bill of materials and provenance

1. Every release artifact ships a CycloneDX SBOM in JSON, generated from `Cargo.lock` plus the non-Rust inputs (NDK, Xcode SDK, Wasmtime, fonts, std packages) [CycloneDX version and generator unverified]. An SPDX document is produced on request.
2. Binaries embed their dependency list in a dedicated section, so an installed binary can be audited without the SBOM [cargo-auditable mechanism unverified].
3. The build platform produces SLSA provenance at Build L3: builds run on dedicated, isolated infrastructure, runs cannot influence one another, and the build steps cannot read the provenance signing keys.
4. Provenance, SBOMs and signatures are listed in the TUF targets metadata, so the updater can verify them.
5. Security advisories follow a published coordinated-disclosure process. The EU Cyber Resilience Act's reporting obligations apply from 11 September 2026 and its main obligations from 11 December 2027; whether its text mandates an SBOM was not verified, and Crucible ships one regardless.

Wasm components published by third parties carry their own SBOM and provenance in the package registry (ECO). Crucible verifies provenance signatures at install when the registry policy demands it.

## Performance engineering

### Reference hardware

Each Tier 1 OS has three reference machines, one per band. The bands are defined by measured properties, so `HardwareProfile` can place any user's machine in one. Phase 0 buys the machines and fixes exact models; the examples below are candidates.

| Band | Definition | Windows x86-64 and Linux x86-64 (same machines, dual-boot) | Windows ARM64 | macOS | Linux ARM64 and servers |
| --- | --- | --- | --- | --- | --- |
| Low | 4 cores, 8 GiB, integrated GPU with Vulkan 1.1, DX12 or Metal | 2019 laptop, 4-core x86-64-v3, 8 GB, Intel UHD-class graphics | The lowest-specified Snapdragon X laptop available, with the engine's memory budget capped to emulate 8 GiB | MacBook Air M1, 8 GB | Raspberry Pi 5, 8 GB (CLI and viewer) |
| Mid | 8 to 14 cores, 24 to 32 GiB, current integrated GPU | 2025 laptop with a Ryzen AI 300 or Core Ultra 200V processor, 32 GB | Snapdragon X Elite laptop, 32 GB | MacBook Pro with an M4 Pro or later chip, 24 GB or more | Cloud virtual machine with 8 Graviton4 vCPUs, 32 GB |
| High | 16 or more cores, 64 GiB or more, discrete GPU with 16 GiB or more | 16-core desktop, 64 GB, NVIDIA RTX-class GPU with 16 GB or more | Same as mid until a higher Windows ARM64 class ships | Mac Studio with an M4 Max or M3 Ultra chip, 64 GB or more | 32-vCPU virtual machines (x86-64 with AVX-512, and Graviton4); one NVIDIA and one AMD Instinct GPU virtual machine |

Browsers run on the mid machines. Tablets: iPad Pro (M4) and an iPad with an A-series chip; Samsung Galaxy Tab S10 (Adreno-class) and a Mali-based tablet.

**Decision D-PLT-28:** The contract's reference laptop is the mid-band Windows x86-64 laptop, and every Tier 1 OS's mid machine must meet the same targets. *Why:* Windows on x86-64 is the most common CAD desktop [unverified], and a target met only on the fastest platform would violate "identical features". *Rejected:* an Apple silicon reference (flatters results for most users); a desktop reference (users work on laptops).

### Budgets

Targets on the mid band of every Tier 1 OS, from the overview plus PLT's own. Low-band targets apply on low machines; browser targets apply on mid machines. All values are targets.

| Measure | Mid (native) | Low (native) | Browser (mid machine) | Owner of the work |
| --- | --- | --- | --- | --- |
| Orbit, 5M triangles | 60 fps | 30 fps on 1M triangles | 60 fps with WebGPU; 30 fps with WebGL2 | UIX |
| Selection | Under 16 ms | Under 33 ms | Under 16 ms | UIX, with PLT spatial kernels |
| Coarse drag preview | Under 100 ms | Under 250 ms | Under 150 ms | KLN, ANV |
| Exact rebuild, 200-feature part, early edit | Under 2 s | Under 6 s | Under 4 s | KLN, ANV |
| Interactive simulation update | Under 1 s | Under 3 s | Under 2 s | FLX |
| 1,000-part assembly, warm cache | Under 10 s | Under 30 s | Under 20 s | KLN, PLT residency |
| Cold start to interactive window | Under 1.5 s | Under 4 s | Under 2.5 s with warm HTTP cache; under 8 s on a first visit over 100 Mbit/s | PLT |
| Warm start | Under 0.6 s | Under 1.5 s | Under 1.5 s | PLT |
| Memory with golden product 1 open | Under 1 GiB in total | Under 1 GiB in total | Under 1.5 GiB of linear memory | PLT |
| Idle memory, UI plus engine | Under 300 MiB | Under 300 MiB | Under 300 MiB | PLT |
| Installed size, desktop | Under 400 MiB | Same | Engine download under 25 MiB compressed per build | PLT |
| UI input-to-photon at the 99th percentile while a rebuild runs | Under 33 ms | Under 50 ms | Under 50 ms | UIX, PLT scheduling |

Startup work runs in this order:

1. The window appears with the last layout while the engine process starts in parallel.
2. The engine maps the CAS index, loads precompiled std Wasm components and opens the last design from cache.
3. GPU device creation and shader pipeline compilation run in the background and never block the first frame.

wgpu's `PIPELINE_CACHE` flag is implemented only on Vulkan, so on DX12 and Metal Crucible keeps shader counts low and compiles pipelines asynchronously [driver-level shader caches on DX12 and Metal unverified].

### Profiling

All crates instrument with the `tracing` crate's spans, never with a specific profiler's API.

| Tool | Targets | Use |
| --- | --- | --- |
| Tracy | Windows, macOS, Linux, servers | Default profiler; `tracing` spans become Tracy zones; GPU timing for Vulkan, Direct3D 12, Metal and WebGPU; memory, lock and context-switch tracking; remote capture from a running app |
| Chrome DevTools and the Firefox Profiler | Browsers | Spans become `performance.measure` entries in the browser build |
| perf | Linux | Sampling and hardware counters; used by benchmark runs |
| Instruments and Xcode GPU capture | macOS, iPadOS | Time Profiler, Metal System Trace |
| Windows Performance Recorder and Analyzer, PIX | Windows | System-wide traces; DX12 GPU captures |
| RenderDoc, Nsight Systems, Radeon GPU Profiler | Vulkan and vendor GPUs | GPU captures in the lab |

Builds for every channel compile instrumentation in. It is disabled at run time until a profiler connects or the user starts a capture from the Performance panel; disabled spans cost under 5 ns each (target). A capture is a file the user can attach to an issue.

### Continuous benchmarking

1. **Suite.** `benches/` holds micro-benchmarks per crate and macro-benchmarks for every budget row above, driven by the golden products and the PLT benchmark corpus. Each benchmark declares the budget row it serves.
2. **Instruction counts on every merge.** The merge queue runs the CPU benchmarks under an instruction-counting harness on Linux x86-64, once per ISA level. Deterministic code executes the same instructions on the same inputs, so counts change only when code changes. Any benchmark whose count rises by more than 1% blocks the merge, unless a PLT owner approves it with a recorded reason.
3. **Wall time nightly.** Dedicated reference machines, idle and with fixed clocks where the OS allows, run the full suite 30 times each. A rise of more than 3% in the median, confirmed by a Mann-Whitney U test at p < 0.01, files an issue that names the first commit range.
4. **Budgets.** Any budget row exceeded on any reference machine blocks promotion of the build to beta.
5. **History.** Results are stored per commit, machine and benchmark, and the dashboard shows trends and changepoints.

CodSpeed documents both a simulation mode and a wall-time mode for CI benchmarks; Crucible runs the same two kinds of measurement on its own hardware, because the GPU paths and the reference machines need dedicated devices.

### Opt-in performance telemetry

Telemetry exists to find performance problems on real hardware that the lab lacks.

| Collected | Never collected |
| --- | --- |
| Histograms of operation duration by operation id and behavior version; frame-time histograms; startup times; peak memory; profile band, ISA level, `GpuClass`, OS version, active workarounds; app version and channel | Design content, parameter values, file or repository names, entity names, Ingot source, user or organization identifiers beyond a random install id that resets on request |

1. Collection is off until the user opts in, and organizations can forbid it by policy. Air-gapped installs never collect it.
2. Data aggregates locally into histograms and uploads at most once a day. The user can view the exact payload before it is sent.
3. The server drops any aggregate with fewer than 50 distinct installs before analysts see it, and retains data for 13 months.
4. Organizations can redirect telemetry to their own server and use the same dashboards.

## Rust API

The API follows one rule of taste: a trait exists only where implementations differ by target. The compute pool, combinators, budgets and math library have one implementation everywhere, so they are concrete types and functions. Every error type implements `Guidance`, which maps into the `api` error shape, so each failure says why and suggests a fix.

### OS services (`core/platform-api`)

```rust
use std::sync::Arc;
use futures_core::future::BoxFuture;

/// OS services for the engine side, injected once by an app shell.
/// Operations never receive these: Kiln's sandbox exposes none of them.
pub struct EngineServices {
    pub storage: Arc<dyn Storage>,
    pub watcher: Arc<dyn FileWatcher>,
    pub notifications: Arc<dyn Notifications>,
    pub credentials: Arc<dyn CredentialStore>,
    pub signals: Arc<dyn SystemSignals>,
    pub wall_clock: Arc<dyn WallClock>, // journal timestamps, telemetry; never evaluation
    pub hardware: HardwareProfile,
}

/// OS services for the UI side.
pub struct UiServices {
    pub clipboard: Arc<dyn Clipboard>,
    pub dialogs: Arc<dyn Dialogs>,
    pub signals: Arc<dyn SystemSignals>,
}

/// Every PLT error explains itself and proposes a fix.
pub trait Guidance: std::error::Error + Send + Sync + 'static {
    fn why(&self) -> String;
    fn fix(&self) -> Option<String>;
}

/// File and object storage: native file systems, or OPFS in the browser.
pub trait Storage: Send + Sync {
    fn capabilities(&self) -> StorageCaps; // memory maps, locks, durability, case sensitivity
    fn resolve(&self, root: &HostPath, path: &RepoPath) -> HostPath;
    fn read(&self, path: &HostPath) -> Result<Vec<u8>, StorageError>;
    /// Read-only memory map. Returns `StorageError::Unsupported` where
    /// `capabilities().memory_maps` is false; callers choose `read` explicitly.
    fn map(&self, path: &HostPath) -> Result<MappedBytes, StorageError>;
    /// Write to a temporary file, flush to `durability`, rename into place.
    fn write_atomic(&self, path: &HostPath, data: &[u8], durability: Durability)
        -> Result<(), StorageError>;
    fn open_journal(&self, path: &HostPath) -> Result<Box<dyn Journal>, StorageError>;
    fn lock(&self, path: &HostPath, mode: LockMode) -> Result<LockGuard, LockError>;
    fn list(&self, dir: &HostPath) -> Result<Vec<DirEntry>, StorageError>;
    fn rename(&self, from: &HostPath, to: &HostPath) -> Result<(), StorageError>;
    fn remove(&self, path: &HostPath) -> Result<(), StorageError>;
}

pub trait Journal: Send {
    fn append(&mut self, record: &[u8]) -> Result<u64, StorageError>; // returns sequence number
    fn flush(&mut self, durability: Durability) -> Result<(), StorageError>;
    fn replay(&mut self) -> Result<JournalReplay, StorageError>; // stops at the first bad record
    fn truncate_through(&mut self, seq: u64) -> Result<(), StorageError>;
}

pub enum Durability {
    Buffered, // handed to the OS; survives a process crash
    Data,     // fdatasync, FlushFileBuffers, F_FULLFSYNC, OPFS flush
}

pub enum LockMode { Shared, Exclusive, TryExclusive }

pub enum LockError {
    Held { holder_pid: Option<u32>, since: Option<u64> },
    Unsupported { reason: String },
    Io(std::io::Error),
}

pub trait FileWatcher: Send + Sync {
    fn watch(&self, root: &HostPath) -> Result<WatchStream, WatchError>;
}

pub enum WatchEvent {
    Changed(Vec<RepoPath>),
    /// Events were lost or cannot be trusted: the consumer re-hashes the tree.
    Rescan { reason: RescanReason },
    Health(WatchHealth), // Native, Polling { interval_ms }, Failed { reason }
}

pub trait Clipboard: Send + Sync {
    fn write(&self, items: Vec<ClipItem>) -> BoxFuture<'_, Result<(), ClipboardError>>;
    fn read(&self, accept: &[ClipFormat]) -> BoxFuture<'_, Result<Option<ClipItem>, ClipboardError>>;
}

pub enum ClipFormat { PlainText, IngotFragment /* application/x-crucible+cbor */, Image, Files }

pub trait Dialogs: Send + Sync {
    fn open(&self, spec: OpenSpec) -> BoxFuture<'_, Result<Vec<HostFile>, DialogError>>;
    fn save(&self, spec: SaveSpec) -> BoxFuture<'_, Result<Option<HostFile>, DialogError>>;
    fn pick_folder(&self, spec: FolderSpec) -> BoxFuture<'_, Result<Option<HostPath>, DialogError>>;
}

/// A file chosen by the user: a path on native targets, a file handle
/// or uploaded blob in the browser. Never enters the CAS by identity.
pub struct HostFile { /* opaque */ }

pub trait Notifications: Send + Sync {
    fn post(&self, notice: Notice) -> Result<NoticeId, NotifyError>;
    fn withdraw(&self, id: NoticeId);
}

pub trait CredentialStore: Send + Sync {
    fn get(&self, account: &str) -> Result<Option<Secret>, CredentialError>;
    fn put(&self, account: &str, secret: Secret) -> Result<(), CredentialError>;
    fn delete(&self, account: &str) -> Result<(), CredentialError>;
}

pub trait SystemSignals: Send + Sync {
    fn current(&self) -> SystemState; // memory pressure, power, thermal, network, appearance
    fn subscribe(&self) -> SignalStream;
}

/// Wall time for journals, logs and telemetry. Not reachable from evaluation.
pub trait WallClock: Send + Sync {
    fn now_unix_ms(&self) -> u64;
}
```

### Windows, input and accessibility (`core/platform-api`, implemented with winit)

```rust
/// Implemented by the UI; driven by the shell's event loop.
pub trait AppHandler {
    fn event(&mut self, host: &mut dyn WindowHost, event: PlatformEvent);
}

pub trait WindowHost {
    fn create_window(&mut self, spec: WindowSpec) -> Result<WindowId, PlatformError>;
    /// Raw window and display handles for the renderer's surface.
    fn surface_target(&self, id: WindowId) -> Result<SurfaceTarget<'_>, PlatformError>;
    fn scale_factor(&self, id: WindowId) -> f64;
    fn request_redraw(&self, id: WindowId);
    fn set_ime(&mut self, id: WindowId, request: ImeRequest);
    fn set_cursor(&mut self, id: WindowId, cursor: CursorIcon);
    fn start_drag(&mut self, id: WindowId, payload: DragPayload) -> Result<(), DragError>;
    fn accessibility(&mut self, id: WindowId) -> &mut dyn AccessibilityHost;
}

pub trait AccessibilityHost {
    /// Forwards the UI's tree to UI Automation, NSAccessibility, AT-SPI,
    /// Android, UIAccessibility or the web DOM mirror.
    fn update(&mut self, update: accesskit::TreeUpdate);
    fn is_active(&self) -> bool; // false when no assistive technology is listening
}

pub enum PlatformEvent {
    Pointer(PointerEvent),     // mouse, pen and touch; pressure, tilt, azimuth when reported
    Key(KeyEvent),             // physical key, logical key, committed text
    Ime(ImeEvent),             // preedit, commit, delete-surrounding
    Drag(DragEvent),           // entered, moved, dropped, left, with position
    NavDevice(NavDeviceEvent), // 6-DoF translation and rotation
    Accessibility(accesskit::ActionRequest),
    Resized { window: WindowId, physical: (u32, u32) },
    ScaleChanged { window: WindowId, scale: f64 },
    Redraw(WindowId),
    CloseRequested(WindowId),
    Signal(SystemSignal),
    Suspended,
    Resumed,
}
```

### Paths and platform classes

```rust
/// Canonical repository path: NFC, '/'-separated, portable to every Tier 1 OS.
pub struct RepoPath(String);

impl RepoPath {
    /// Rejects non-portable names with a suggested replacement.
    pub fn parse(s: &str) -> Result<RepoPath, PathError>;
    /// Unicode default case folding; equal keys are collisions.
    pub fn collision_key(&self) -> String;
}

pub enum PathError {
    NotNfc { normalized: String },
    ReservedName { segment: String, suggestion: String },
    ForbiddenChar { ch: char, segment: String, suggestion: String },
    TrailingDotOrSpace { segment: String },
    SegmentTooLong { segment: String, bytes: usize },
    DotSegment,
    CaseCollision { existing: RepoPath },
}

/// The environment whose results must be bit-identical.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub enum PlatformClass {
    /// Every Tier 1 CPU target, wasm32 included, any thread count or ISA level.
    CpuCanonical { epoch: u16 },
    /// CPUs at one ISA level.
    CpuIsa { isa: IsaLevel, epoch: u16 },
    /// Devices in one entry of the verified GPU class registry.
    Gpu(GpuClass),
    /// Not verified; results stay in this machine's local cache.
    Unverified { fingerprint: [u8; 16] },
}

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub enum IsaLevel { X86_64V2, X86_64V3, X86_64V4, Arm64Neon, Wasm32Simd128 }

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct GpuClass { pub registry_id: u32, pub epoch: u16 }

/// Chosen per evaluation by Kiln's policy from the modes an operation declares.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub enum ExecMode { Canonical, Native, Gpu }

pub struct HardwareProfile {
    pub logical_cores: u32,
    pub memory_bytes: u64,
    pub page_size: u32,
    pub isa: IsaLevel,
    pub gpus: Vec<GpuInfo>, // adapter info, verified class if any, active workarounds
    pub band: ProfileBand,  // Low, Mid, High
}
```

### Compute runtime (`core/runtime`)

```rust
pub enum Priority { Interactive, Background }

/// Two rayon pools with OS priorities; one implementation on every target.
/// Kiln submits one run per Op evaluation; there is no other unit of work.
pub struct ComputePool { /* interactive and background pools */ }

impl ComputePool {
    /// Starts `run` at `priority`; the handle is a future for async callers.
    pub fn spawn<R, F>(&self, priority: Priority, budget: MemoryBudget, cancel: CancelToken, run: F)
        -> RunHandle<R>
    where
        R: Send + 'static,
        F: FnOnce(&OpCtx<'_>) -> R + Send + 'static;

    /// Raises the OS priority of a started background run that an interactive run waits on.
    pub fn boost(&self, run: RunId);
}

/// What an operation sees of the runtime. No clock, no randomness, no IO.
pub struct OpCtx<'a> {
    pub mode: ExecMode,
    pub cancel: &'a CancelToken,
    pub budget: &'a MemoryBudget,
    /// None without a usable device or in safe mode. In Canonical mode,
    /// only `GpuRole::FilterCpuDecides` paths may use it.
    pub gpu: Option<&'a dyn GpuCompute>,
}

impl OpCtx<'_> {
    /// A per-thread scratch arena, reset when the operation returns.
    pub fn with_scratch<R>(&self, f: impl FnOnce(&bumpalo::Bump) -> R) -> R;
}

pub struct Cancelled;

// Deterministic combinators: partitioned by data, combined in fixed order.
pub fn det_for_each_chunk(ctx: &OpCtx<'_>, len: usize, chunk: usize,
    f: impl Fn(std::ops::Range<usize>) + Sync) -> Result<(), Cancelled>;
pub fn det_map_collect<T: Sync, U: Send>(ctx: &OpCtx<'_>, xs: &[T],
    f: impl Fn(&T) -> U + Sync) -> Result<Vec<U>, Cancelled>;
pub fn det_sum(ctx: &OpCtx<'_>, xs: &[f64]) -> Result<f64, Cancelled>;
pub fn det_sum_f32(ctx: &OpCtx<'_>, xs: &[f32]) -> Result<f32, Cancelled>;
pub fn det_scan<T: Send + Sync + Clone>(ctx: &OpCtx<'_>, xs: &[T],
    op: impl Fn(&T, &T) -> T + Sync) -> Result<Vec<T>, Cancelled>;
pub fn det_reduce<T: Send + Sync + Clone>(ctx: &OpCtx<'_>, xs: &[T], identity: T,
    op: impl Fn(T, T) -> T + Sync) -> Result<T, Cancelled>;
/// Floats enter keys only as `NonNan<f64>`, so a NaN can never decide an order.
pub fn det_sort_by_key<T: Send, K: Ord + Send>(ctx: &OpCtx<'_>, xs: &mut [T],
    key: impl Fn(&T) -> K + Sync) -> Result<(), Cancelled>;
/// Reproducible for any partitioning of `xs` (binned summation).
pub fn exact_sum(xs: &[f64]) -> f64;

pub struct MemoryBudget { /* node in the budget tree */ }

impl MemoryBudget {
    pub fn child(&self, name: &'static str, limit_bytes: u64) -> MemoryBudget;
    /// Waits for eviction up to `wait`, then fails. Never affects a result's value.
    pub fn reserve(&self, bytes: u64, wait: std::time::Duration)
        -> Result<Reservation, ResourceExhausted>;
}

pub struct ResourceExhausted { pub requested: u64, pub available: u64, pub fix: String }

/// A large typed array stored as 1 MiB CAS chunks, paged by the residency manager.
pub struct ChunkedBuffer<T: bytemuck::Pod> { /* chunk hashes, length */ }

impl<T: bytemuck::Pod> ChunkedBuffer<T> {
    pub fn len(&self) -> u64;
    pub fn chunk_count(&self) -> u32;
    pub fn chunk(&self, index: u32) -> Result<Pinned<'_, [T]>, CasError>;
}
```

### SIMD, math and GPU (`core/simd`, `core/detmath`, `core/gpu`)

```rust
// core/simd
/// A kernel written once against 512-bit virtual vectors.
pub trait Kernel {
    type Output;
    fn run<S: CanonicalSimd>(self, simd: S) -> Self::Output;
}

/// Dispatches to the detected ISA level; every level returns identical bits.
pub fn dispatch<K: Kernel>(kernel: K) -> K::Output;

/// Operations allowed in canonical kernels. Approximate instructions are absent.
pub trait CanonicalSimd: Copy {
    type F64x8: Copy;
    fn splat(self, x: f64) -> Self::F64x8;
    fn add(self, a: Self::F64x8, b: Self::F64x8) -> Self::F64x8;
    fn mul(self, a: Self::F64x8, b: Self::F64x8) -> Self::F64x8;
    fn div(self, a: Self::F64x8, b: Self::F64x8) -> Self::F64x8;
    fn sqrt(self, a: Self::F64x8) -> Self::F64x8;
    fn min_total(self, a: Self::F64x8, b: Self::F64x8) -> Self::F64x8;
    /// Fixed tree ((l0+l1)+(l2+l3))+((l4+l5)+(l6+l7)).
    fn reduce_sum(self, a: Self::F64x8) -> f64;
}

// core/detmath: correctly rounded in round-to-nearest on every target.
pub fn exp(x: f64) -> f64;
pub fn ln(x: f64) -> f64;
pub fn sin_cos(x: f64) -> (f64, f64);
pub fn atan2(y: f64, x: f64) -> f64;
pub fn pow(x: f64, y: f64) -> f64;
pub fn exp_batch(xs: &[f64], out: &mut [f64]);

// core/gpu
pub trait GpuCompute: Send + Sync {
    fn info(&self) -> &GpuInfo;
    fn class(&self) -> PlatformClass; // Gpu(..) or Unverified
    fn alloc(&self, bytes: u64, usage: BufferUsage) -> Result<GpuBuffer, GpuError>;
    fn upload(&self, data: &[u8], dst: &GpuBuffer) -> Result<(), GpuError>;
    fn dispatch(&self, kernel: &CompiledKernel, args: &KernelArgs, grid: Grid)
        -> Result<Submission, GpuError>;
    fn readback(&self, src: &GpuBuffer) -> BoxFuture<'_, Result<Vec<u8>, GpuError>>;
}

pub enum GpuRole { FilterCpuDecides, Interactive, GpuClassSignoff }

/// Every GPU path is registered with its CPU path; no GPU-only feature exists.
pub struct GpuPath<I, O> {
    pub id: &'static str,
    pub role: GpuRole,
    pub gpu: fn(&OpCtx<'_>, &dyn GpuCompute, &I) -> Result<O, GpuError>,
    pub cpu: fn(&OpCtx<'_>, &I) -> Result<O, Cancelled>,
}

pub enum RanOn { Gpu(GpuClass), Cpu { reason: CpuReason } }

pub enum GpuError {
    DeviceLost { reason: String },
    OutOfMemory { requested: u64 },
    Unsupported { capability: GpuCapability, fix: String },
    Blocklisted { workaround_id: String },
    Cancelled,
}
```

### Wasm components (`core/wasm-host`)

```rust
/// Two implementations: `Wasmtime` (native, Cranelift or Pulley) in this crate,
/// and `BrowserWasmEngine` (jco plus the browser's engine) in `apps/platform`.
pub trait WasmComponentEngine: Send + Sync {
    /// Validates, checks imports against the world, instruments, precompiles.
    fn install(&self, bytes: &[u8], world: &WorldSpec)
        -> Result<InstalledWasmComponent, WasmComponentError>;
    fn instantiate(&self, installed: &InstalledWasmComponent, limits: CallLimits)
        -> Result<Box<dyn WasmInstance>, WasmComponentError>;
}

/// One instantiation of a Wasm component (not an assembly Instance).
pub trait WasmInstance: Send {
    fn call(&mut self, export: &str, args: &[Val], cancel: &CancelToken)
        -> Result<Vec<Val>, WasmComponentError>;
    fn fuel_used(&self) -> u64;
}

pub struct CallLimits {
    pub fuel: u64,              // instrument@1 units
    pub stack_frames: u32,      // logical stack limit
    pub max_memory_bytes: u64,  // declared in package metadata; reserved before instantiation
}

pub enum WasmComponentError {
    InvalidComponent { reason: String },
    ForbiddenImport { import: String, fix: String },
    Trap { code: String, function: String, fix: String },
    FuelExhausted { used: u64, limit: u64 },
    StackExhausted { limit: u32 },
    ResourceExhausted(ResourceExhausted), // host failure: never cached
    Cancelled,                            // never cached
}
```

## State of the art

All performance and accuracy numbers in the last column are targets unless they cite a source.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Cross-platform numerical determinism | IEEE 754 arithmetic without contraction, own elementary functions, data-ordered parallel reductions (Box2D; Rapier's `enhanced-determinism`, whose parallel solver matches its sequential one) | Box2D, tested for cross-platform determinism on x64 and ARM with MSVC, GCC and Clang | One canonical class across OS, ISA and wasm32 (D-PLT-19), with correctly rounded math (D-PLT-17), canonical lanes (D-PLT-15) and combinators | Determinism suite: zero hash differences across every Tier 1 CPU target, thread count and ISA level |
| Elementary functions | Correct rounding (CORE-MATH) | glibc 2.43 (CORE-MATH-derived binary64 functions) and AMD libm 4.2 for speed; platform libm for coverage | Port CORE-MATH into `detmath`, scalar and batched | Exhaustive univariate f32 tests and hard-case f64 tests against MPFR; cycles per call against glibc 2.43 (scalar `exp` and `ln` within 1.5 times) |
| Reproducible reductions | Binned summation independent of partitioning (Demmel and Nguyen, IEEE Transactions on Computers 2015; ReproBLAS) | Intel oneMKL strict CNR (bitwise reproducible `?gemm`, `?symm`, `?hemm`, `?trsm` across thread counts on AVX2 and AVX-512) | Data-defined pairwise trees by default; binned `exact_sum` for partition-varying sums | Bit identity at 1 to 64 threads; `det_sum` at least 90% of a native-width unordered SIMD sum at memory bandwidth |
| CPU scheduling | Work-stealing fork-join; low-overhead fork-join for fine-grained tasks (Spice, ported to Rust as chili) | rayon; chili (3.4 µs against rayon's 51.1 µs on a 1,023-node tree) | rayon pools split by priority (D-PLT-13); chili evaluated for fine-grained recursion | Interactive start latency under 2 ms at p99 while both pools are loaded; fork overhead on the PLT suite |
| SIMD | Write once, dispatch at run time per ISA | pulp-style dispatch in Rust numerical crates such as faer [faer's use of pulp unverified]; `std::simd` when stabilized | pulp-style dispatch over canonical 512-bit virtual vectors | Throughput per ISA as a fraction of peak FLOP/s on PLT kernels; AVX2 path at least 3 times the scalar path on `det_sum` |
| Memory allocation | Sharded free lists with thread-local heaps (mimalloc) | mimalloc v3, jemalloc, snmalloc | mimalloc v3 (D-PLT-14) | PLT macro-benchmarks and peak memory, re-measured in phase 0 |
| Out-of-core large data | Content-addressed chunks with explicit residency and eviction | No single leading CAD implementation identified [unverified] | `ChunkedBuffer<T>` over 1 MiB CAS chunks with CLOCK eviction | Identical hashes in and out of core; 1,000-part assembly under 10 s with a 2 GiB budget |
| GPU compute abstraction | One kernel language compiled to every vendor and the web | CUDA libraries on NVIDIA; CubeCL with cubek kernels in Rust | CubeCL behind `GpuCompute`, with CPU fallbacks (D-PLT-16) | Matmul and reduction throughput at least 70% of the vendor library on NVIDIA and AMD lab GPUs |
| Deterministic GPU reductions | Fixed-topology tree reductions; sort plus segmented reduction instead of float atomics | Vendor primitive libraries with deterministic modes [unverified] | Two-pass fixed-tree reductions, atomic-free scatter | Bit identity per `GpuClass` over 1,000 runs; throughput at least 70% of an atomic-based reduction |
| Wasm runtime | Ahead-of-time Cranelift compilation, pooling allocation, guard-region bounds checks | Wasmtime; V8 for browsers | Wasmtime LTS (D-PLT-21) natively, the browser's engine on the web | Wasm component corpus time against the same code as native Rust: at most 1.3 times in Wasmtime, 2.0 times in browsers |
| Deterministic Wasm execution | Injected metering and stack limits (wasm-instrument); the Wasm 3.0 deterministic profile | wasm-instrument; Wasmtime fuel plus NaN canonicalization on native only | Engine-independent instrumentation (D-PLT-22) | Identical outputs and fuel counts in Cranelift, Pulley, Chrome, Firefox and Safari; overhead at most 10% |
| Browser engine | Wasm with threads and SIMD; workers; OPFS | Figma (load time more than 3 times faster after moving to Wasm) | Two web builds, out-of-core OPFS, remote evaluation (D-PLT-9, D-PLT-11) | PLT suite ratio to native at most 1.6 single-threaded and 2.0 multi-threaded |
| Native Rust GPU desktop app | Rust core with a GPU renderer and a thin platform layer | Zed, which ships on macOS, Linux and Windows | winit, AccessKit and wgpu under one platform layer | Input-to-photon p99 under 33 ms during rebuilds, measured with high-speed camera rigs on each OS |
| Text shaping | HarfBuzz shaping | HarfBuzz | HarfRust in Parley, pure Rust, identical on every target | HarfBuzz test suite pass rate; shaping throughput within 25% of HarfBuzz |
| Accessibility | One tree mapped to each OS API | Chromium's accessibility layer (AccessKit is partly derived from it) | AccessKit plus a Crucible web adapter (D-PLT-8) | Screen-reader automation per OS; tree snapshot tests; axe-core audits |
| Crash reporting | Out-of-process capture to minidumps, server-side symbolication | Crashpad (Chromium) and Firefox's crash reporting [pipeline details not opened] | `crash-handler`, `minidumper` and rust-minidump with a monitor process | Crash-injection tests over every crash type: at least 99% captured and symbolicated on every desktop target |
| Software updates | TUF metadata; executable-aware binary diffs | Chrome's updater; the Chromium code base contains the Zucchini patcher [Chrome's use of it not confirmed] | TUF plus MSIX block maps and Zucchini (D-PLT-25) | TUF attack simulations; median delta at most 15% of the full package; update success rate at least 99.9% |
| Build acceleration | Remote caching and remote execution | Bazel and Buck2 remote execution [unverified] | Cargo with sccache remote cache (D-PLT-26) | Clean CI build with a warm cache under 6 minutes; incremental edit-test loop under 20 s |
| Supply-chain security | Reproducible builds; SLSA Build L3 provenance | Reproducible Linux distributions [unverified] | Two independent builders, byte-identical outputs, SLSA L3 provenance | Byte comparison of every release; provenance verification in the updater |
| Continuous benchmarking | Instruction counting for low-noise gating plus wall time on dedicated hardware | CodSpeed's simulation and wall-time modes | Same two methods on Crucible hardware | Gate false-positive rate below one per week; detection of a 1% instruction regression |
| Profiling | Low-overhead always-compiled instrumentation with remote capture | Tracy | `tracing` spans exported to Tracy and browser profilers | Disabled-span cost under 5 ns; capture overhead under 5% of frame time |

## Platform notes

This tab is itself the platform specification, so these notes collect the risks that can still break the "identical features" promise, with their mitigations.

| Platform | Risk | Mitigation | Phase |
| --- | --- | --- | --- |
| Windows ARM64 | The `crash-handler` crate lists Windows x86-64 only; young GPU drivers; Chrome's WebGPU behind a flag | Upstream ARM64 support; Windows Error Reporting dumps meanwhile; GPU lab coverage of Snapdragon X; WebGL2 plus CPU compute in Chrome | 0 |
| Windows | GPU timeout detection and recovery on long dispatches; paths over 260 characters; files cannot be deleted while mapped; real-time antivirus scanning slows the creation of many small files [magnitude unverified] | Dispatches under 100 ms; `\\?\` paths; deferred CAS deletion; a request to KLN, which owns the CAS layout, to pack objects under 64 KiB into append-only pack files | 0 |
| macOS | Hardened runtime blocks JIT without an entitlement; macOS 27 drops Intel | `allow-jit` entitlement and precompiled Wasm components; Intel Macs in Tier 3 | 1 |
| Linux | Wayland protocol gaps in clipboard, drag sources and text input; portal availability; old distributions | Data-control and portal backends with explicit fallbacks; glibc 2.34 floor; X11 support kept | 0 to 1 |
| Browsers | Threads need cross-origin isolation; 4 GiB memory; storage eviction (seven days in Safari); WebGPU missing in Firefox on Linux and partial in Chrome on Linux | Single-threaded build; out-of-core and remote evaluation; server as source of truth; WebGL2 and CPU compute fallback | 0 to 1 |
| iPadOS | No JIT; App Review rules on downloaded code; memory limits | Pulley interpreter; remote execution fallback; strict memory budget | 3 |
| Android | 16 KB pages required for updates from 1 February 2027; driver quality | NDK r28 or later; runtime page-size queries; device farm across GPU vendors | 3 |
| Servers | GPU drivers in containers; heterogeneous cloud CPUs | Canonical CPU class independent of ISA; CUDA and ROCm optional and never required | 2 |
| FreeBSD and other Tier 3 | No vendor CI hardware | Community runners; `Unverified` class until the suite passes | 5 |

## Interfaces with other subsystems

### Provided by PLT

| To | What | Types |
| --- | --- | --- |
| Kiln (KLN) | Execution of scheduled Op evaluations at two priorities; cancellation; memory budgets; the platform class that keys the cache; storage for the CAS; deterministic combinators | `ComputePool`, `Priority`, `OpCtx`, `CancelToken`, `MemoryBudget`, `ResourceExhausted`, `PlatformClass`, `ExecMode`, `Storage`, `ChunkedBuffer<T>` |
| Anvil (ANV) | Canonical SIMD, correctly rounded math, combinators, GPU paths of role "GPU filters, CPU decides" for surface-surface intersection sampling, out-of-core meshes | `simd::Kernel`, `CanonicalSimd`, `detmath`, `det_*`, `GpuPath`, `ChunkedBuffer<T>` |
| Flux (FLX) | GPU compute on wgpu, CUDA and ROCm through CubeCL; deterministic GPU reductions; CPU fallbacks; reproducible global sums for distributed solves; double-float helpers | `GpuCompute`, `GpuPath`, `GpuRole`, `RanOn`, `exact_sum`, `det_sum` |
| UI (UIX) | Windows, input, IME, drag and drop, accessibility hosting, clipboard, dialogs, surfaces for the renderer, hardware profile, GPU workaround database, device-loss hooks, safe-mode flag, shared-memory transport for tessellations and Field samples | `WindowHost`, `AppHandler`, `PlatformEvent`, `AccessibilityHost`, `UiServices`, `HardwareProfile` |
| `repo` | Durable journal, atomic writes, file locks, file watching, portable paths, text normalization | `Journal`, `Durability`, `LockMode`, `FileWatcher`, `WatchEvent`, `RepoPath`, `PathError` |
| Ingot (ING) | The math functions behind std's numeric built-ins; a no-contraction rule for compiled Ingot; JIT constraints per target | `detmath`; if Ingot compiles to machine code at run time, it follows the same rules as Wasm components (precompiled artifacts, Pulley-class interpretation or remote evaluation on iPadOS) |
| Ecosystem (ECO) | Enforcement of Wasm component worlds, install-time instrumentation, precompilation, provenance verification at install | `WasmComponentEngine`, `WasmInstance`, `CallLimits`, `WasmComponentError` |
| `api` and agents (AGT) | Transport between UI and engine on every target; `cli` exit codes; resource-usage measurements for agent cost caps (CPU seconds, fuel, peak memory, GPU seconds per evaluation); remote evaluation on servers | `Guidance` errors mapped into `api` errors; `ResourceUsage` [field list to be agreed with AGT] |

### Consumed by PLT

| From | What PLT needs |
| --- | --- |
| Kiln (KLN) | The determinism policy: which `ExecMode` each evaluation uses and where `PlatformClass::Gpu` results are acceptable; the cache-key composition including `PlatformClass`; never caching `Cancelled`, `ResourceExhausted` or `DeviceLost`; a CAS layout that packs small objects; static cost hints per operation for scheduling chunks |
| Anvil and Flux (ANV, FLX) | For every operation: the execution modes it implements, the `GpuRole` of each GPU path, agreement tolerances per output, and corpus inputs for the determinism suite and benchmarks |
| UI (UIX) | The AccessKit tree; renderer behavior on device loss and in safe mode; render-quality levels for graceful degradation; the budget rows it owns |
| Ecosystem (ECO) | WIT worlds and capability definitions for evaluation and tool worlds; a declared memory limit in Wasm component package metadata; packages that carry font files for design text; the registry's signing and provenance format; the licensed-translator plugin interface run in the plugin host |
| `api` (AGT) | The message framing and error shape that `Guidance` maps into |
| Ingot (ING) | The compilation strategy for features, so its JIT and determinism constraints can be confirmed |

## Oracles

All PLT oracles live in `oracles/plt/`, which agents can read but not write. Loosening any threshold below needs human approval.

| Oracle | Verifies | Runs | Phase |
| --- | --- | --- | --- |
| Canonical identity | Identical output hashes for the corpus on every Tier 1 CPU target, every forced ISA level, and wasm32 in Chrome, Firefox, Safari and Node, threaded and single-threaded | Merge queue | 0 |
| Schedule independence | Identical hashes at 1, 2, 3, 8 and 64 threads with injected stealing delays and allocator randomization | Merge queue | 0 |
| Out-of-core equivalence | Identical hashes with a 64 MiB budget forcing chunks to disk | Nightly | 0 |
| `detmath` correct rounding | Univariate f32 functions exhaustively against MPFR; bivariate f32 and all f64 functions on known hard-to-round cases and 10^9 random inputs per night | Nightly | 0 |
| Determinism lints | Layering check, Clippy disallowed methods and types, SIMD intrinsic allow-list, no `-ffp-contract` other than `off` | Every pull request | 0 |
| Wasm determinism | Identical outputs, fuel counts and trap points for the Wasm component corpus in Cranelift, Pulley, Chrome, Firefox and Safari; instrumented code passes the WebAssembly specification test suite; injected fuel agrees with Wasmtime's built-in fuel on a reference cost table | Merge queue | 0 |
| Cross-class agreement | Every `CpuIsa` and verified `GpuClass` within declared tolerances of canonical results on golden products and the operation corpus | Nightly | 1 |
| Path portability | Property tests over generated names; a repository created on each OS checks out with identical hashes on the others | Merge queue | 0 |
| Journal durability | Process kills at random points lose no appended record; a fault-injecting storage layer that drops unflushed writes loses at most 1 s of edits; recovery restores the exact `repo` state | Nightly | 1 |
| Crash capture | Every crash type from the `sadness-generator` crate, in UI, engine and plugin host on every desktop target, yields a symbolicated report | Release | 0 |
| GPU recovery | Forced device loss during dispatch recovers within 5 s, reruns on the GPU or the CPU path, and leaves no corrupted cache entry | Nightly, GPU lab | 1 |
| Update security | TUF attack simulations (rollback, freeze, mix-and-match, fast-forward, endless data, wrong target) are rejected; power loss during apply leaves a runnable version; a failed self-test rolls back | Release | 1 |
| Install hygiene | Install, upgrade from each of the last 3 releases, and uninstall per format leave no files outside documented locations | Release | 1 |
| Reproducible build | Two independent builders produce byte-identical unsigned artifacts | Release | 0 (Linux, wasm32), 2 (all) |
| Budgets | Every budget row on every reference machine | Nightly, gating beta | 1 |
| Performance regression | Instruction counts within 1%; wall-time changes confirmed statistically | Merge queue, nightly | 0 |
| Accessibility | Tree snapshots for every golden-product screen; per-OS assistive-technology automation reads names and roles; axe-core audits on the web | Release | 1 |
| Platform services | Clipboard round trips, lock contention between processes, watcher convergence under mutation fuzzing, dialog automation | Merge queue (fakes), release (real OS) | 0 to 1 |
| Browser isolation | Threaded build loads only when cross-origin isolated; both web builds produce identical hashes | Merge queue | 0 |
| Memory | Golden products build within their budget rows; exhaustion yields typed `ResourceExhausted`, never an abort | Nightly | 1 |

## Phasing

| Phase | PLT deliverables | Gate contribution |
| --- | --- | --- |
| 0, foundations | `platform-api` and `platform` for Windows, macOS, Linux and the browser; `runtime` with both pools and the combinators; `simd` dispatch; `detmath` core functions (`exp`, `ln`, `sin`, `cos`, `tan`, `atan2`, `pow`, `hypot`, `cbrt`); `CpuCanonical` class; Wasmtime LTS embedding with instrumentation; CAS storage, journal, locks, `RepoPath`; crash capture on desktop; CI matrix with sccache; reproducible Linux and wasm32 builds; reference machines bought and the reference laptop fixed; benchmark harness; nightly channel | Determinism suite green on every Tier 1 CPU target and browser |
| 1, wedge | Installers and TUF-signed delta updates for every desktop format; beta and stable channels; browser offline use, OPFS and both web builds; accessibility on desktop and web; GPU compute through CubeCL with CPU fallbacks; GPU lab, verified-class registry and workaround database; safe mode; autosave and recovery; out-of-core `ChunkedBuffer` (lattices in golden product 2); design fonts; opt-in telemetry; budgets enforced; full `detmath` | Golden products 1 and 2 meet their budget rows on every Tier 1 target |
| 2, mechanical depth | First LTS release; server images with optional CUDA and ROCm; remote evaluation; offline bundles, mirrors and enterprise policy; outgoing drag and drop; 6-DoF devices; reproducible builds on all targets | Golden products 3 and 4 build identically on desktop, browser and server |
| 3, product breadth | iPadOS and Android tablet shells, phone viewers, Pulley on iPadOS, mobile accessibility, device farm | Golden product 5 reviewable and lightly editable on Tier 2 |
| 4, full multiphysics | GPU-class sign-off paths, multi-GPU servers, distributed solves with `exact_sum` | Golden product 6 simulations meet the interactive and sign-off budgets |
| 5 and later | Tier 3 targets in the canonical class; SVE dispatch once Rust stabilizes scalable vectors; memory64 re-evaluation; riscv64 servers | Tier 3 targets pass the determinism suite |

## Open questions

1. Will App Review accept installed Wasm components as plug-ins under guideline 4.7, given guideline 2.5.2? If not, iPadOS runs Wasm components remotely.
2. Does install-time instrumentation stay within 10% overhead on real Wasm components, and should PLT switch to the Wasm 3.0 deterministic profile once browsers expose it?
3. Can batched CORE-MATH ports meet the speed targets for `pow` and for trigonometric functions with large arguments?
4. Where does Kiln accept `PlatformClass::Gpu` results for sign-off, and for which operations does Flux need GPU-class determinism at all?
5. Regulated industries may need support far beyond 24 months, which outlives Wasmtime's LTS. Options: backporting security fixes to an old Wasmtime ourselves, or running old Wasm components on a pinned Pulley build inside a sandboxed process.
6. Should the engine process itself run inside an OS sandbox (seccomp and Landlock, AppContainer, App Sandbox) for defense in depth, given that GPU drivers need broad access?
7. Can Windows PE and macOS Mach-O builds become byte-reproducible with the current toolchains, or must signed-artifact verification rely on provenance alone there?
8. Does chili's low-overhead fork-join beat rayon enough on BVH builds and sparse assembly to justify a second scheduler?
9. Which fields does `ResourceUsage` need for agent cost caps, and should fuel be a billable unit?
10. How long must archived engine builds of retired `CpuCanonical` epochs stay runnable for bit-exact reproduction of old releases, and who signs and hosts them?

## Contract change requests

1. **`PlatformClass` definition (section 5).** Change "a set of targets (OS, CPU architecture, GPU backend) whose results must be bit-identical" to "a set of execution environments, either a CPU determinism level (canonical or one ISA level) or one verified GPU device class, with an epoch, whose results must be bit-identical; the operating system is never part of a class". *Reason:* the canonical CPU class spans every OS and architecture (D-PLT-19), and GPU determinism depends on vendor, device family and driver, not only on the backend.
2. **SVE (section 9).** Note that SVE dispatch is deferred until Rust stabilizes scalable vectors (tracking issue rust-lang/rust#145052), with NEON on ARM64 servers until then. *Reason:* SVE support in Rust is experimental and blocked on the Sized Hierarchy work.
3. **Crate list (section 7).** Add `platform-api`, `runtime`, `simd`, `detmath`, `gpu` and `wasm-host` under `core/`, and `platform` under `apps/`. Allow `unsafe` in `wasm-host`, because loading precompiled Wasm code is an unsafe operation. *Reason:* the contract's crate list has no home for the runtime and platform mechanisms.
4. **Cache key for Wasm component calls (section 5, `Op`).** Include the instrumentation version (`instrument@N`) in the cache key of every Wasm component call. *Reason:* fuel exhaustion points depend on the instrumentation version, so results computed under different versions must not share entries.

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
