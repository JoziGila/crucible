# UIX round 3 packet

Your tab is `docs/spec/10-ui.md` at v2 (tag `round-2`). Round 3 fixes, in one pass: the 32 second-review findings that target it (1 Critical, 21 Major, 10 Minor), its 12 `[unverified]` claims, its open questions and the known items below. Contract v6 is binding; its section 17 lists the rulings on this review, and many findings below are already settled there.

## Second-review findings

### R8-18 · Major · Targets: ANV, UIX, FLX
**Section:** ANV Measurement services (`anvil::tessellate`), Volume meshes, Interfaces (UIX row); UIX Display data and precision; FLX D-FLX-6
**Problem:** Several Anvil artifacts carry names but are keyed or shared by name-free identity. ANV's interface promises "`DisplayPackage` keyed by `GeometryId`" while `tessellate` emits "`(EntityId, u, v)` back-references", so a second design (or a renamed binding) with the same geometry receives the first design's `EntityId`s; picks then map to entities that do not exist in the reader's Body and suggested queries resolve wrongly. UIX already keys pages by `GeometryId` with a separate face table, which contradicts ANV's back-references. Volume meshes classify boundary facets "so Flux resolves `ds(part.face(q))` through `EntityId`s", while D-FLX-6 keys solves on `GeometryId`s and canonical entity numbers.
**Evidence:** ANV: "`anvil::tessellate` | ... `(EntityId, u, v)` back-references"; UIX row "`DisplayPackage` keyed by `GeometryId`". UIX: "Pages are keyed by `GeometryId` and tolerance, so renamed or reused geometry shares them; only the face table carries names." D-FLX-6: "solves receive them as canonical entity numbers of the Body's `GeometryId`, never as mesh entities or names".
**Fix:** Every derived geometric artifact (tessellation pages, cluster DAGs, volume meshes, adaptation maps, sample sets) references canonical entity numbers only and is keyed by `GeometryId`. The canonical-number-to-`EntityId` table comes from the Body's name part, keyed by the Body's `ObjectId`, and is joined at the consumer. Change contract 5 `DisplayPackage` to "with canonical-entity-number back-references; names come from the Body's face table". Add to ANV-O-LABEL-1: two designs with equal geometry and different names share pages, and picks return each design's own `EntityId`s.

### R8-29 · Minor · Targets: ANV, UIX
**Section:** ANV Geometry types (watertight tessellation)
**Problem:** Watertightness does not follow from equal parameters. Two faces evaluated at "the same parameter" of their parameter curves give points up to τ_edge apart, so display meshes gain cracks of up to τ_edge, which for healed imports is micrometres to τ_heal.
**Evidence:** ANV: "Parameter curves share their edge curve's parameter within τ_edge, so tessellation places shared edge vertices at the same parameter from both sides and display meshes are watertight by construction."
**Fix:** Tessellate each edge once from its 3D edge curve and share those vertex positions with both faces; include τ_edge in each face's chordal bound. ANV-O-TESS-1 runs on healed imports with large edge tolerances.

### R8-45 · Minor · Targets: MEC, UIX, ING
**Section:** MEC Open questions 6
**Problem:** Whether drawing edits write model source is open.
**Evidence:** MEC open question 6: "Should editing a driving dimension on a drawing write model source through its `Query`?"
**Fix:** Decide yes, through ING's edit plans: a drawing dimension that traces by provenance to exactly one literal writes it directly; otherwise the UI offers ranked edit plans; driven and reference dimensions stay read-only. Reason: principle 2 makes every surface an editor of one program, and drawings already reference model entities by `Query`, so this adds no new mechanism.

### R9-07 · Major · Targets: ING, KLN, AGT, PLT, UIX, MEC, ELX
**Section:** ING "The Ingot IR and Kiln" item 5 (overrides); KLN "Graph model", "Keys"; AGT `evaluate.*` methods; PLT `PoolLane`; UIX D-UIX-15, D-UIX-27; MEC sketch drag; ELX router
**Problem:** The drag path, the most latency-critical path in the product, has no owner in Kiln or `api`. Literal overrides are input cells per ING, but KLN never mentions them, and a feature node's key (module code hashes, argument identities, `OpSite`, limits) does not include an override of a literal inside the feature's own body, so an overridden result can be stored and served under the un-overridden key. UIX, MEC and ELX route per-pointer tools through an "interactive edit lane" and an `api` edit stream that neither PLT's lanes nor AGT's catalog define.
**Evidence:** ING l.753: "A request may carry literal overrides keyed by `LiteralSite` … Kiln treats them as input cells". KLN l.54 lists input cells without overrides, and the word appears nowhere else in KLN. AGT l.312: `evaluate.build` takes "Targets, `Fidelity`, `estimate_only`". UIX l.593: tools "run in the engine process on an interactive edit lane and stream geometry each frame through `api`"; MEC l.180: "`api` Edit stream at 60 Hz"; PLT l.293: `pub enum PoolLane { Foreground, Background }`.
**Fix:** KLN adds overrides to its input cells and to rule 4 of "Keys": a node's key includes the canonical encoding of the overrides whose `LiteralSite` lies in its own code, and results computed under overrides are never written to the shared cache. AGT adds `evaluate.subscribe { targets, overrides, ceiling }` and an `edit.stream` method (a session-scoped stream of override updates ending in one `edit.apply`). PLT adds a third `PoolLane`, `Interactive`, preempting `Foreground` work at node boundaries, which KLN's priority table maps from the drag lane. ING-O-12 and KLN-O-PROG-1 add: a drag's overridden result never answers a request without the override.

### R9-25 · Major · Targets: CONTRACT, AGT, MFG, KLN, ECO, UIX
**Section:** CONTRACT 12 (`apps/`); AGT "Scope and invariants", "One catalog, several transports"; MFG Open questions 12; KLN "Deployment"; ECO "SDKs, methods and the CLI"; UIX "Snapshots"
**Problem:** Contract 12 is the build plan, and it omits about ten deliverables that tabs depend on: `apps/mcp` and `apps/crew` (AGT), the machine gateway (MFG), the relay and runner gateway (KLN), the hardware runner (KLN, ELX, AGT), the tool runner (ECO), the model gateway (AGT), and the Python, TypeScript and C-ABI SDKs. Two placements are wrong: AGT says `api` owns transports and also that it has "no transport code", and `inspect.render`, an `api` method, runs `apps/renderer`, making a core crate depend on an app, while the contract's `apps/headless-render` appears in no tab.
**Evidence:** AGT l.1036: "`apps/mcp` and `apps/crew` ship as Linux containers". MFG l.914: "Contract 12's crate map lists no gateway app". KLN l.723: "relay and runner gateway from phase 2". ECO l.322: "In a tool runner". AGT l.7: the `api` crate covers "catalog, transports"; AGT l.39: "`core/api` … no transport code. `apps/mcp` serves it". UIX l.289: "`inspect.render` (AGT's method) runs this renderer headless".
**Fix:** Contract 12 lists `apps/mcp`, `apps/crew`, `apps/machine-gateway` (MFG, packaged by PLT), `apps/relay` and `apps/rig-runner` (KLN), `apps/tool-runner` (ECO, PLT) and `apps/model-gateway` (AGT), and `sdk/python`, `sdk/typescript` and `sdk/c` beside the Rust `crucible-sdk` (ECO). `inspect.render` dispatches to `apps/headless-render`, a service that links `apps/renderer`; `api` depends on neither. AGT's l.7 drops "transports".

### R9-29 · Major · Targets: KLN, AGT, UIX, ELX, PLT, FLX
**Section:** KLN "Audit and encryption", "Effectivity and variants", Interfaces; AGT "Audit and personal data"; UIX "Review, agents and collaboration"; ELX "Variants"; PLT and FLX sparse factorization
**Problem:** Four facts have two owners or none. KLN and AGT both define the audit-entry schema, with opposite content rules. KLN and UIX each say the other defines review verdicts and comments. KLN and ELX each specify variant analysis with their own oracle. PLT says it provides `linalg` circuit LU while its own D-PLT-34 gives sparse factorization to FLX.
**Evidence:** KLN l.683: audit entries "never labelled content"; AGT l.825: "This tab owns the schema … with full content only for Act plans, approvals and policy changes". KLN l.853 provides UIX "comments, review verdicts" and l.870 requires "Comment anchors and review verdicts" from UIX; UIX l.483: "Review verdicts are `repo` records". KLN l.546 (KLN-O-PLM-5) and ELX l.140 (ELX-O-VAR-1) both check the 150% BOM against brute force. PLT l.838: "`linalg` for circuit LU"; FLX l.854 lists block-triangular LU.
**Fix:** One owner each. KLN owns the audit log and its envelope; AGT owns the `api`-call payload fields inside it; the content rule is KLN's ("ids and digests, never labelled content"), with Act plans, approvals and policy changes stored as separate labelled records the entry references. KLN defines `ReviewVerdict` and `Comment` records; UIX owns `CommentAnchor` and display. KLN owns variant semantics and KLN-O-PLM-5; ELX's row cites it and keeps only its covering-set policy. FLX owns sparse factorization in `linalg` (D-PLT-34), and PLT's row drops it.

### R9-30 · Major · Targets: ANV, UIX, FLX, ELX, MEC, PLT
**Section:** UIX "Display data" (cluster DAG); ANV "Measurement, analysis and simulation services" (`anvil::tessellate`); ELX "Hardware-in-the-loop" (linearization); FLX "Multibody dynamics"; MEC "Entities and helpers" (`text`); PLT "Paths, text and accessibility" (D-PLT-7)
**Problem:** Three consumers rely on capabilities their producers never specify. UIX's phase 2 renderer needs a cluster-DAG `DisplayPackage` built "as a deterministic Anvil operation", which ANV does not have. ELX's phase 4 control design needs exact linearization of Flux multibody plants, which FLX's multibody and adjoint tables omit. MEC engraves text from "bundled fonts" while PLT says design text uses registry font packages shaped by Parley, and no operation exposes shaping to Ingot.
**Evidence:** UIX l.211: "Its `clusterlod` method builds the DAG as a deterministic Anvil operation with monotone error bounds"; ANV l.794 has only `anvil::tessellate` → "cluster pages" (phase 1). ELX l.639: "Exact Jacobians of the plant DAE through Flux derivatives" (phase 4); FLX's ELX row (l.903) and adjoint table omit multibody. MEC l.85: "Driven glyph outlines from bundled fonts"; PLT l.70 (D-PLT-7): "fonts from registry packages pinned in `ingot.lock` and shaped by the pure-Rust Parley stack".
**Fix:** ANV adds `anvil::cluster_dag` (phase 2) with monotone error bounds and its oracle. FLX adds `flux::linearize_multibody` (phase 4), `Differentiable`, with a Taylor-test oracle. PLT's D-PLT-7 is the rule; ANV adds `anvil::text_outline(font package, string, layout)` over Parley's shaping, and MEC's `text` calls it with `FontMissing` as its failure.

### R9-32 · Major · Targets: MFG, COV, ING, ECO, UIX, PLT, CONTRACT
**Section:** MFG "Sustainability and compliance"; COV "Environmental data"; ING "Assemblies, variants and families" (catalog selections); ECO "Mirrors, licences and the parts catalog"; UIX "Performance, privacy and extension" (telemetry row); CONTRACT 13.2 (phase 1 scope)
**Problem:** Several consumers phase a capability before its producer exists, and two tabs ship in phase 1 what contract 13.2 defers. MFG's embodied carbon and RoHS checks (phase 2) read COV's environmental records (phase 5); ING's catalog selections (phase 1) run over `parts::` packages that ECO delivers in phase 2; UIX ships telemetry in phase 1 on a pipeline PLT builds in phase 2, which the contract defers out of phase 1.
**Evidence:** MFG l.655: "Global warming potential per BOM line from COV's per-material `EnvironmentalRecord`s … | 2"; COV l.744: "Environmental records | … | 5". ING l.654: "Catalog selections | Pure over pinned data … | 1"; ECO l.690: "Catalog-part definitions | `parts::` packages … | 2". UIX l.796: "Telemetry | PLT's opt-in pipeline … | 1"; PLT l.669: "Telemetry pipeline | … | 2"; contract 13.2 defers "telemetry" from phase 1.
**Fix:** Apply contract 13.4's rule (first gate that needs it) to these pairs too, and make the spec check enforce it: every capability row that names another tab's capability carries a phase no earlier than that owner's row. Concretely: COV's environmental records move to phase 2 with MFG (generic factors and declared substances only; database connectors stay at 5); ING's catalog selections take phase 2; UIX's telemetry row takes phase 2.

### R9-33 · Major · Targets: CONTRACT, PLT, UIX, KLN, MEC
**Section:** CONTRACT 13.3 (scene capacity, orbit and X-ray rows); PLT "Performance engineering" and Phasing; UIX "Two pipelines", "Frame budgets" (D-UIX-24, k-buffer); KLN "Diff, large assemblies and references"; MEC large-assembly representations
**Problem:** PLT says GP1 and GP2 meet every contract 13.3 row at the phase 1 gate, and a missed row blocks beta promotion, but three tabs deliver the capacity those rows need only in phases 2 to 4. Phase 1 has only a forward renderer, which UIX itself rejects as CPU-bound beyond about 10,000 Instances, while the G1 row asks 100,000; the X-ray row assumes a k-buffer that is phase 2.
**Evidence:** Contract 13.3: "G1 100,000 Instances (1,000,000 on the high band)". PLT l.920: "GP1 and GP2 meet every contract section 13.3 row"; PLT l.770: "A missed row blocks beta promotion | … | 1". UIX l.230 rejects per-object draws as "CPU-bound beyond about 10,000 Instances"; UIX l.285: the X-ray row "includes the k-buffer's second pass", k-buffer phase 2. KLN l.414: "100,000 Instances of 10,000 unique Parts (phase 4 target)"; MEC l.539: large-assembly capacity at 2.
**Fix:** Contract 13.3 gives each row the phase from which it blocks promotion: cold and warm start, selection, drag, rebuild, interactive simulation, input latency, memory and installed size from phase 1; orbit at 5M triangles, X-ray and scene capacity from phase 2 for G1 and G2; the 100,000-Instance assembly open from phase 4. PLT's Phasing and PLT-O-PERF-1 cite the column.

### R9-44 · Minor · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT
**Section:** Every tab (contract 11 style rules)
**Problem:** The tabs carry about 1,080 sentences over 25 words and about 340 paragraphs over three sentences, by the spec check's own count, mostly inside decisions; KLN's lead sentence alone runs 33 words. Contract 11 asks for sentences under 25 words and paragraphs of at most three sentences, and the founder's taste requirement makes this more than polish for a spec read by agents.
**Evidence:** `python3 docs/tools/check.py` per tab: ANV 167, KLN 128, PLT 122, AGT 99, UIX 96, ELX 94, ECO 85, MEC 83, FLX 79, ING 72, MFG 41, COV 12 long sentences; FLX 41 and KLN 34 long paragraphs.
**Fix:** Round 3's revision brief sets a hard budget the check enforces as an error: no sentence over 40 words, at most 5% of sentences over 25, no paragraph over four sentences; decisions split *Why* and *Rejected* into short sentences. Leads are rewritten first.

### R9-45 · Minor · Targets: UIX, PLT, ECO, COV, FLX, KLN, AGT, MFG
**Section:** Capability tables and Phasing sections named below
**Problem:** Owners and consumers state different phases for the same capability, and two tabs contradict their own Phasing sections.
**Evidence:** Tablets: UIX l.691 and Phasing phase 2, PLT l.147 and ECO l.473 phase 3. Lattice Boltzmann and particles: COV l.309 phase 5 (Wasm) and l.375 phase 6, FLX l.470 phase 4 and l.471 phase 5 (native). ERP and MES connectors: ECO l.563 phase 2, MFG l.632 phase 4. Air-gapped installs: PLT l.601 phase 2, KLN l.758 phase 3. Rust SDK: AGT l.265 phase 1, AGT Phasing l.1111 and ECO l.558 phase 0. FLX flexible multibody: l.646 phase 3, FLX Phasing l.1017 phase 4. FLX sizing Fields: l.139 phase 1, l.503 phase 2. Browser updates: PLT l.561 puts "a transparency log" in phase 1, which contract 13.2 defers.
**Fix:** The owner's row wins and consumers cite it: tablets 3 (PLT owns the targets); lattice Boltzmann 4 and particles 5, native (FLX); ERP and MES connector worlds 2 (ECO), with MFG's mapping at 4 stating it builds on them; air-gapped 3 (KLN's bundles); Rust SDK 0 (AGT corrects its row); flexible multibody 3 and sizing Fields 2 in FLX's own tables; PLT's update manifest uses TUF alone in phase 1 and adds the transparency log in phase 2. The spec check gains a cross-tab phase comparison for capability names shared between tabs.

### R9-50 · Minor · Targets: ING, MEC, FLX, ELX, UIX
**Section:** ING Open questions 7 ("Feature granularity"), 8 ("Jacobian types") and 9 ("Literal sites under live edits")
**Problem:** Three design questions remain open before std freezes in phase 1.
**Evidence:** ING l.1284 to 1286.
**Fix:** Question 7: one rule, checked by a std lint: a std helper is a `feature` if it calls an entity-naming operation or returns a value carrying `EntityId`s, a `#[memo] fn` if it is pure and estimated above 10⁶ steps, and a `fn` otherwise. Question 8: `Mat<R, C>` diagnostics name the offending entry `(i, j)` with its expected and actual dimensions and print the row and column dimension vectors once, as an `ING3001` note. Question 9: overrides key by `LiteralSite`, which follows `#[was]`; a concurrent rename writes `#[was(old)]`, so the override maps to the new site and the drag continues. Only a deleted literal ends the drag, with the notice ING describes.

### R10-05 · Major · Targets: CONTRACT, MFG, AGT, UIX
**Section:** Contract 7.6 Physical safety (`start_print`); MFG "Printers, 3MF and print transfer"; AGT D-AGT-31
**Problem:** `start_print` rests on four weak conditions.
1. The safety declaration lives in a printer profile, which is a registry package from a third party, so it is self-declared. `unattended_safe`, by contrast, needs a safety officer's signed site policy.
2. "Enclosure or smoke detection" accepts an enclosure without detection, which contains nothing when the enclosure is plastic.
3. Nothing restricts the process, so a laser powder-bed machine with such a profile qualifies, although contract 7.6 says Crucible never starts lasers or furnaces.
4. "A site-bound key" lets someone confirm a clear build plate from anywhere on site without seeing it.
**Evidence:** Contract 7.6: "`start_print` exists only for printers whose profile declares thermal-runaway protection and enclosure or smoke detection, and needs an Approval of the job digest plus an on-site confirmation that the build plate is clear, given at the printer or with a site-bound key." MFG: "Printer profiles are packages".
**Fix:** Contract 7.6 replaces the rule:
1. `start_print` exists only for material-extrusion printers and for vat-photopolymerization printers whose light source is not a laser above Class 1 [unverified classification per model]. It never applies to powder bed fusion, directed energy deposition, binder jetting or any printer that needs inert gas.
2. Each printer serial needs a signed site policy from the named safety officer. The policy declares firmware thermal-runaway protection and smoke or heat detection that cuts printer power.
3. The on-site confirmation is given at the printer, within 10 minutes before the start. It uses a printer-side button where the firmware offers one, or a one-time code shown on the printer's display and typed into the confirmation.

MFG-O-SAFE-2 seeds profile-only declarations, laser-process printers and confirmations from elsewhere on site, and all must be refused.

### R10-13 · Major · Targets: MFG, UIX
**Section:** MFG "Scope, layering and core types" (`Toolpath`, `Workingstep`); `MotionSemantics.cutter_comp`; posts
**Problem:** Shops hold tight wall and bore sizes by letting the operator adjust a wear offset at the control. That needs posts to output control-side or wear-mode cutter compensation (G41 and G42 with a D register). MFG's types have no compensation mode, so the gouge check cannot know that a finishing pass moves with a value set later at the control.
**Evidence:** The `Toolpath` and `Workingstep` records have no compensation field. `MotionSemantics` declares only "cutter_comp: look-ahead blocks, entry rule".
**Fix:**
1. Add `comp: CompMode { Computer, Control, Wear, ReverseWear }` and `wear_range: Range<Length>` to finishing workingsteps, defaulting to `Computer`.
2. Posts emit G41 or G42 with the D register for the other modes.
3. Gouge and collision checks run at both ends of the declared range.
4. The gateway's offset check verifies that the D register lies inside the range, and the setup sheet prints it.

MFG-O-SIM-1 seeds wear values outside the range. UIX's NC panel shows the mode per workingstep.

### R10-17 · Major · Targets: CONTRACT, AGT, UIX, MFG
**Section:** Contract 7.6 Act approvals; AGT "Acts and approvals" (approval page); UIX D-UIX-29
**Problem:** The one approval page shows file names, a thumbnail, a content summary (Items, labels, bytes), recipient verification and screening dates, and a diff. Those fit data release. For a physical-effect plan the approver sees nothing that bears on safety:
- which device it is, and where;
- what the transfer overwrites;
- the simulation verdicts and minimum clearance;
- the gateway's offset result;
- what the person at the device must do.

MFG's rule that robot programs are "Proved in manual reduced-speed mode" appears nowhere a person reads it.
**Evidence:** Contract 7.6 lists the page contents. MFG: "`send_robot_program` | Delivers a robot program | Proved in manual reduced-speed mode; never writes safety configuration".
**Fix:** Contract 7.6 adds a physical-effect section to the page:
- device serial, location and controller version;
- program number and what it replaces (R10-11);
- simulation verdicts, with the minimum clearance and the count of `Unsupported` semantics;
- gateway offset results with their timestamp;
- the setup-sheet revision;
- the required on-device steps, each shown as an instruction to the person at the device: reduced-speed prove-out, tool-length check, reduced override, propellers off.

AGT-O-9 adds rendering cases for each physical-effect class.

### R11-05 · Major · Targets: UIX, AGT, PLT
**Section:** UIX "Approvals" (D-UIX-29); AGT "Acts and approvals" (D-AGT-20); PLT "OS services" (`Authenticator`)
**Problem:** The approval page is "rendered verbatim" by the desktop, web and tablet clients, but no tab isolates it from the rest of the client. In the web app it shares an origin with views that render untrusted content (imported names, SVG sections, Markdown descriptions, panel element trees), so a script injection there can fetch a pending approval challenge and start a WebAuthn ceremony under a pretext such as "confirm it's you"; the passkey prompt shows only the relying-party name, never the plan. On desktop, any UI code can call PLT's `Authenticator`.
**Evidence:** UIX D-UIX-29: "desktop, web and tablet clients render verbatim from the server's record". PLT: "`Authenticator` returns WebAuthn assertions with user verification for the approval page". No tab names an origin, relying-party id, content security policy or caller restriction for the approval ceremony.
**Fix:** Add to D-AGT-20 and D-UIX-29: the approval page is served from a dedicated origin (for example `approve.<deployment>`) with its own WebAuthn relying-party id, so credentials registered for the main app cannot approve; it renders only server-generated text under a strict CSP (`default-src 'none'`, scripts by hash); approval challenges are issued only to that origin (`SameSite=Strict` cookies, no CORS). The challenge is the hash of (plan digest, request id, approver id). Desktop and tablet clients open this origin in an isolated webview or the system browser; PLT's `Authenticator` is callable only from that view. Extend UIX-O-APPR-1 with a scripted main-origin page that tries to complete an approval.

### R11-06 · Major · Targets: CONTRACT, AGT, UIX, KLN
**Section:** Contract 7.6 "Act approvals", 9 Tier 2; AGT D-AGT-20; UIX "Approvals"; KLN "Electronic signatures"
**Problem:** "No Act of any risk class is approvable on a phone" has no enforcement mechanism: WebAuthn does not reveal the device class, user-agent strings are client-controlled, and synced passkeys created on a phone are usable on any device. Synced passkeys are also exportable keys, which NIST SP 800-63B-4 bars from AAL3, yet they would sign export-officer declassifications, R4 Act approvals and Part 11 signatures. UIX-O-APPR-1's "phones … are refused" is therefore not machine-checkable as specified.
**Evidence:** NIST SP 800-63B-4: "syncable authenticators SHALL NOT be used at AAL3" and AAL3 requires "a cryptographic authenticator with a non-exportable private key" (https://pages.nist.gov/800-63-4/sp800-63b.html). UIX: "phone: 'approve on a desktop or tablet'". KLN signs with "ECDSA P-256 keys in platform keystores or WebAuthn authenticators".
**Fix:** Replace the phone rule with an enrolment rule in contract 7.6: approvals and signatures need a device-bound (non-exportable) credential registered through an enrolment that records device class, from a Crucible desktop or tablet app (which reports its form factor through the platform API) or a roaming security key whose attested AAGUID is on an allowlist. Synced passkeys may sign in but never approve or sign. Export-officer actions, R4-class Acts and Part 11 signatures require AAL3. KLN's signature record stores `authenticatorData`, `clientDataJSON` (challenge = the signed `ObjectId`) and the credential's attestation, so the record verifies offline. UIX-O-APPR-1 then tests "credential not enrolled for approval" instead of "phone".

### R11-34 · Major · Targets: CONTRACT, PLT, ECO, UIX
**Section:** Contract 7.7 (Licensing); PLT "OS services" (`CryptoProvider`), "Build, release and CI"; KLN "Audit and encryption" (FIPS mode); UIX "Design system and onboarding"
**Problem:** The contract's linked-licence list (MIT, Apache-2.0, BSD, ISC, Zlib, Unicode-3.0) excludes licences the spec already depends on. The FIPS build of AWS-LC, PLT's and KLN's leading candidate for FIPS mode, carries the OpenSSL licence; `webpki-roots` (common with rustls) is CDLA-Permissive-2.0; UIX bundles Inter, JetBrains Mono and Noto under the SIL Open Font License; and Tier 1 Linux links glibc, which is LGPL, while 7.7 says LGPL code "is never linked".
**Evidence:** crates.io: `aws-lc-fips-sys` 0.14.2 is "ISC AND (Apache-2.0 OR ISC) AND OpenSSL"; `webpki-roots` 1.0.9 is "CDLA-Permissive-2.0". UIX: "Inter (SIL Open Font License 1.1) … JetBrains Mono (OFL 1.1)". Contract 9: "glibc 2.34 or newer". Contract 7.7: "LGPL, GPL and AGPL code is never linked".
**Fix:** Amend contract 7.7: linked code may also use OpenSSL (the pre-3.0 dual licence), BSL-1.0, CC0-1.0, 0BSD and MIT-0; bundled data and fonts may use OFL-1.1, CDLA-Permissive-2.0, CC-BY-4.0 and Unicode-3.0, each with its notices; operating-system libraries (glibc, the C++ runtime under the GCC Runtime Library Exception, platform frameworks) are dynamically linked and never shipped, which LGPL permits. Every other licence needs an RFC. cargo-deny's allowlist (PLT) and ECO-O-31 follow this list.

### R12-02 · Critical · Targets: CONTRACT, PLT, AGT, ANV, FLX, UIX
**Section:** CONTRACT 1 Mission, 3 principle 6, 13.2 Program plan; Oracles in every tab
**Problem:** The mission and the 1.5× factor rest on swarms "working against oracles", yet every oracle sits in a directory agents cannot write, so each one, with its corpus and executable pass criterion, must be written and reviewed by people before any swarm work on its capability can start. Phase 0 and 1 capability rows cite about 427 distinct oracle ids, many on corpora that do not exist yet, while "oracles, corpora and QA" grows from 2 to 5 people and no milestone says when any oracle must exist. The spec has no build-program section at all: no work-item format, eligibility rule, runner class or review path for swarm output, and contract 13.2 lists "test corpora" as swarm work although agents cannot write `oracles/`.
**Evidence:** Parsing every capability table (Capability · Contract · Failure · Oracle id · Phase) gives 760 distinct cited oracle ids, 427 of them on rows phased 0 or 1. PLT: "All PLT oracles live in `oracles/plt/`, readable but not writable by agents"; UIX: "Oracles live in `oracles/uix/`, protected from agent edits." Corpora still to build include the "ABC-derived 200-feature corpus" and "a named GP1-class benchmark" (contract 13.3), "the prismatic ABC corpus" (13.2) and FLX's calibration entries with "at least 300 held-out samples and zero undershoots" per estimator class. Several oracles have runners agents cannot drive: PLT-O-PERF-1 on the physical reference laptop, UIX's "photodiode latency each phase", PLT-O-TGT-1's device farm, UIX-O-A11Y-3's screen readers and UIX-O-KEY-1's "reference tables kept by daily users". The only "swarm" text in the spec (AGT's Orchestration of swarms) describes agents using Crucible, not agents building it.
**Fix:** Add a "Build program" paragraph to contract 13.2, owned by PLT, which already owns engineering capacity:
1. **Oracle first.** An implementation work item opens only when its oracle ids exist in `oracles/` as executable checks reviewed by a second engineer. Chain A and B oracles exist by month 9 and every phase 1 oracle by month 15; each gate reports oracle coverage per crate.
2. **Runner classes.** Every oracle declares one runner class: `cpu-ci`, `browser-ci`, `gpu-lab`, `device-farm`, `physical` or `human`. Only `cpu-ci` and `browser-ci` work is swarm-eligible.
3. **Corpora.** Swarm-built corpora and reference data enter `oracles/` only through a human-reviewed Proposal and must agree with an independent source (MPFR, Open CASCADE, lib3mf, MFEM or libCEED, CAx-IF data).
4. **Staff.** Oracles, corpora and QA grow 4 → 10 instead of 2 → 5, or each domain team's line in the staffing table carries 15% of its engineer-years for oracle authorship, stated explicitly.
5. **Work items.** A work item is `{ crate, capability row, oracle ids, held-out split, budget }`, run through AGT's Plan and Proposal machinery against Crucible's own repository, with the verifier role of D-AGT-12.

### R12-03 · Major · Targets: CONTRACT, PLT, KLN, AGT, UIX, FLX
**Section:** CONTRACT 13.2 Program plan ("A scope addition above 5 engineer-years to an open phase needs the same approval as a gate change"); Phasing in PLT, KLN, AGT, UIX, FLX
**Problem:** The round 2 fixes added or moved into phases 0 and 1 a set of capabilities that the round 1 drafts and R6-01's 200 engineer-year baseline did not contain, totalling an estimated 20 to 30 engineer-years. Neither the staffing table nor the 160 engineer-years changed, and no approval is recorded, so the gate date silently absorbs the additions.
**Evidence:** Absent from the `round-1` text of KLN, AGT, UIX and PLT and present now with phase 0 or 1 (git comparison): the opaque-origin browser sandbox and OS sandboxes for third-party Wasm components on every target (PLT "Third-party isolation", phase 1); one first-party browser Wasm component runtime (D-PLT-36, phase 1); microVM Proposal CI on the team server (KLN phase 1); context labels and write-down (KLN and AGT phase 1); two-person rules (KLN phase 1); `release_data` with restricted-party screening (KLN phase 1); label-aware egress (PLT and UIX phase 1); the stdio MCP server sandbox (PLT phase 1); GPU known-answer tests and per-pipeline classes (PLT phase 1); the heavy worker and one engine per origin (PLT phase 1). Contract 13.4 also put Lanczos and LOBPCG and inherent strain in phase 1, and FLX phase 1 adds beam-lattice strut buckling. Estimate (±50%): sandboxes and browser runtime 5, microVM CI 2, labels and write-down 4, span provenance and endorsement 2, approval page, `release_data` and two-person rules 3, egress and stdio sandbox 1.5, GPU known-answer machinery 1.5, browser engine ownership and heavy worker 2, FLX additions 3 to 4.
**Fix:** Record a phase 1 re-baseline in contract 13.2: re-estimate each tab against v5 bottom-up, list every addition with its engineer-years, and either approve the increase (phase 1 at about 185 engineer-years, ending at 110 people) or defer to phase 2 the items no GP1 or GP2 step needs. Candidates: the browser third-party sandbox (replaced by remote evaluation, R12-01), two-person rules beyond releases, and `release_data` screening for recipients inside the organization.

### R12-05 · Major · Targets: CONTRACT, PLT, UIX, KLN
**Section:** CONTRACT 13.3 Performance targets; PLT Phasing; PLT Performance engineering; UIX Two pipelines, State of the art
**Problem:** The rows of contract 13.3 have no phase, yet PLT makes GP1 and GP2 meet "every contract section 13.3 row" in phase 1, and every missed row blocks beta promotion. Phase 1 ships one forward renderer that UIX itself calls CPU-bound beyond about 10,000 Instances, has no single-Part golden product that exercises the 100,000-Instance or 1,000-part assembly rows, and gets KLN's scale targets only in phase 4. UIX also sets GP2's implicit lattice display at 30 fps, under a 60 fps orbit row.
**Evidence:** PLT Phasing, phase 1: "GP1 and GP2 meet every contract section 13.3 row on the reference laptop"; PLT: "A row missed on the reference laptop blocks beta promotion"; benchmark files `scene.toml` and `assembly-1000.toml`. D-UIX-9 rejects "per-object draws everywhere (CPU-bound beyond about 10,000 Instances)", and D-UIX-24 makes phase 1 a forward renderer with per-Part discrete LOD. 13.3: G1 100,000 Instances at 60 fps, G3 10,000 Instances, and "Open a 1,000-part assembly from warm cache: 10 s, with a coarse view in 2 s", whose coarse-first path in UIX uses "Root pages", which arrive with cluster-DAG pages in phase 2. UIX State of the art: "30 fps at 1080p on G1 for GP2". KLN Phasing: "scale targets (100,000-Instance assemblies, cloud cells)" in phase 4.
**Fix:** Add a Phase column to contract 13.3. Cold and warm start, selection, orbit at 5M triangles, drag, rebuild, recertification, simulation update, input to photon, memory, installed size and CEED rows are phase 1. Scene capacity and the 1,000-part assembly row are phase 2, gated on GP3 and GP4 with the cluster-DAG renderer. The 1,000,000-Instance high-band figure is phase 4, with KLN's scale targets. Add a phase 1 row "orbit of implicit Bodies: 30 fps at 2.1 MP on G1 and G2", and declare phase 1 forward-renderer capacity per tier as measured targets that do not block beta.

### R12-08 · Major · Targets: UIX, PLT
**Section:** UIX UI toolkit (D-UIX-3); UIX Open questions 1
**Problem:** The month-3 bake-off cannot discriminate between its options. It asks about two engineers, hired in months 0 to 4, to build three screens twice on four platforms in six weeks, judged partly by UIX-O-A11Y-1 on Chrome, which neither option can pass while AccessKit has no web adapter. Masonry paints through Vello, whose original renderer needs compute (UIX's own words), so it has no G3 path, and it names no web backend. The capability row then defaults a failed bake-off to the own toolkit, so the outcome is fixed in advance and the six weeks buy no information.
**Evidence:** D-UIX-3: "chooses between its own retained-mode GPU toolkit ... and Masonry at month 3 of phase 0, after a six-week bake-off; the own toolkit is the working choice"; "The bake-off builds three screens with both options on Windows, macOS, Linux and Chrome". Capability row: "Neither option passes: own toolkit with gaps named". UIX: "Vello's original renderer needs GPU compute". Masonry's README: "Imaging (by default Vello and wgpu for 2D graphics)", with backends listed only for winit and Android (https://github.com/linebender/xilem/tree/main/masonry). AccessKit lists a web adapter only as planned (https://github.com/AccessKit/accesskit).
**Fix:** Answers UIX open question 1. Decide the own toolkit now. Masonry fails two hard requirements, a non-compute paint path for G3 and a browser target, and closing both is the same work as the own toolkit's renderer. Spend the six weeks on a risk spike of the own toolkit's three hardest parts instead: a 1,000,000-row virtualized tree with an AccessKit tree on Windows, an IME field on Windows and in Chrome through EditContext, and a 50,000-line code panel at 8 ms keystroke-to-paint. If any part misses its oracle at month 3, re-plan the UIX staffing line, not the toolkit choice.

### R12-09 · Major · Targets: CONTRACT, UIX, KLN, AGT
**Section:** CONTRACT 13.2 Critical path for phase 1; UIX Phasing; KLN Phasing
**Problem:** Contract 13.2 names only two chains, geometry (A) and physics and printing (B), yet UIX turns the phase 1 gate into "designed, toleranced, simulated, reviewed and released through the UI, entirely by keyboard", and a release needs the team server, the approval page with WebAuthn and the release Act. The UI chain runs from the month-3 toolkit decision through toolkit core, renderer, sketching, dialogs, drag preview, the drawing editor and keyboard completeness. The release chain needs a single-node server with Cedar, a signed audit log, microVM CI, `release_data` and the approval page. Neither chain has milestones, and the month-20 dry run cannot exercise "released in Crucible" if the release chain is not ready.
**Evidence:** Contract 13.2 lists Chain A and Chain B only; milestones put "team server; Propose and review" somewhere in months 12 to 24 and "keyboard-complete workflows, accessibility" in months 24 to 32. UIX Phasing, phase 1: "GP1 and GP2 designed, toleranced, simulated, reviewed and released through the UI, entirely by keyboard". KLN phase 1: "the release Act over approval subjects; `release_data` for STEP and 3MF exports". Contract 13.1 gate: GP1 "designed, toleranced, simulated and released in Crucible".
**Fix:** Add to contract 13.2:
1. **Chain C (interface):** toolkit decision (month 3) → toolkit core, forward renderer, picking (month 12) → feature dialogs, sketching, drag preview, sections, Field color (month 18) → drawing editor and review diffs (month 22) → keyboard-complete and accessibility oracles green (month 32).
2. **Chain D (release):** single-node team server with Cedar and the audit log (month 15) → microVM Proposal CI (month 17) → approval page with WebAuthn and the release and `release_data` Acts (month 19) → used end to end in the month-20 dry run.

Also state that the gate reads "released in Crucible" as satisfied through `api` and the CLI, so that a UI slip moves UIX's own target and not the gate.

### R12-13 · Major · Targets: CONTRACT, PLT, UIX, FLX, KLN, ECO
**Section:** CONTRACT 3 principle 6; Oracles in every tab
**Problem:** Agents read every oracle's inputs and pass criteria, and only Anvil keeps held-out data outside the agent-readable tree. Code written against fixed visible inputs can pass by special-casing them, which is the standard failure of optimizing against a fixed test set. PLT's benchmark files, UIX's recorded scripts and reference images, and most corpora in other tabs are fixed and readable, so "oracle-covered" work is not yet evidence of correct behaviour.
**Evidence:** ANV: "Held-out ABC and Thingi10K subsets, chosen by a fixed hash rule, stay outside the agent-readable tree." PLT: oracles "readable but not writable by agents"; benchmark files "live in `oracles/plt/bench/`". UIX-O-SNAP-2: "Mean ꟻLIP at most 0.01 against references per backend"; UIX-O-ELX-1 replays "ELX's recorded routing and placement sessions". No other tab's Oracles section names a held-out split.
**Fix:** Contract principle 6 adds: "Every oracle that agent-built code is judged against has a held-out split outside the agent-readable tree, chosen by a fixed hash rule, or a property generator seeded at CI time and never shown to agents. A pass on visible inputs with a failure on held-out inputs fails the oracle." PLT adds held-out variants of each 13.3 benchmark (perturbed GP1 parameters, a second ABC sample); a visible-to-held-out performance gap above 10% fails PLT-O-PERF-1.

### R12-14 · Major · Targets: CONTRACT, PLT, UIX, ECO
**Section:** CONTRACT 7.4 Executors (iPadOS); PLT Tablets and phones (D-PLT-33); PLT Open questions 1 and 2; UIX Platform notes
**Problem:** The contract claims the iPadOS app "meets App Review guidelines ... 3.2.2(i) ... and 4.7" while registry packages are "never ... a browsable catalog". But guideline 4.7.4 requires "an index of software and metadata available in your app" with universal links, and 4.7.1 and 4.7.5 add reporting, blocking and age restriction, which no tab plans for. D-PLT-33's first form, a WKWebView worker beside native engine threads, also cannot answer the synchronous `crucible:ops` imports of Wasm running in WebKit (R12-01): it would need a relay from a separate WebKit process through a callback-based reply handler. UIX has already picked the second form, while PLT defers the choice to a phase 3 spike, so the tabs disagree.
**Evidence:** App Review Guidelines: 2.5.2 forbids apps to "download, install, or execute code which introduces or changes features or functionality of the app"; 4.7.4: "You must provide an index of software and metadata available in your app. It must include universal links that lead to all of the software offered in your app"; 3.2.2(i) bans an interface "similar to the App Store or as a general-interest collection" (https://developer.apple.com/app-store/review/guidelines/). Apple's `WKScriptMessageHandlerWithReply` answers JavaScript through a `replyHandler: (Any?, String?) -> Void` callback (https://developer.apple.com/tutorials/data/documentation/webkit/wkscriptmessagehandlerwithreply.json). UIX: "On iPadOS the web build runs in a thin WKWebView shell"; PLT open question 2: "A phase 3 spike ... picks one of D-PLT-33's two forms".
**Fix:** Answers PLT open questions 1 and 2.
1. iPadOS uses only the second form, the web build in a WKWebView shell, so it shares the browser runtime and the async `crucible:ops` bridge of R12-01.
2. Only first-party Wasm components shipped in the binary run locally. Registry Wasm components evaluate remotely by default, which keeps the app inside 2.5.2 and outside 4.7.
3. Replace the contract sentence with "the app runs only first-party Wasm components locally and evaluates registry Wasm components remotely". If local registry components are ever wanted, ECO first ships a 4.7.4 index on the web with universal links, 4.7.1 reporting and blocking through its legal-removal path, and a 4.7.5 age mechanism.
4. The phase 3 spike measures WKWebView memory limits and WebGPU only.

### R12-15 · Major · Targets: PLT, UIX, AGT
**Section:** PLT OS services (`Authenticator`), capability "WebAuthn"; UIX Approvals (D-UIX-29); AGT D-AGT-20
**Problem:** Every Act approval needs WebAuthn user verification, which PLT's `Authenticator` provides natively on each desktop. On Apple platforms an app can use passkeys only for relying parties listed as its associated domains, so the native macOS app cannot approve against a customer's self-hosted team server, the only server in phase 1. PLT names no Linux mechanism. Approvals on a general-availability Tier 1 target therefore fail for the phase 1 deployment model.
**Evidence:** Apple, Supporting passkeys: "You need to have an associated domain with the `webcredentials` service type when making a registration or assertion request; otherwise, the request returns an error"; "Your app can't use passkeys to authenticate for services that you haven't configured as the app's associated domains" (https://developer.apple.com/tutorials/data/documentation/authenticationservices/supporting-passkeys.json). PLT: "`Authenticator` returns WebAuthn assertions with user verification for the approval page"; capability "WebAuthn | `Authenticator` assertions with user verification | ... | 1". KLN phase 1: "a single-node team server".
**Fix:** Native desktop and tablet clients open the approval page in a browser session: `ASWebAuthenticationSession` on macOS and iPadOS, and the default browser on Windows and Linux, bound to the request id and returned to the app by a `crucible://` callback. The browser, not the app, performs WebAuthn, for any relying-party domain. `Authenticator` is used natively only where the relying party is an associated domain of the shipped app (Crucible's own cloud). PLT-O-OS-4 adds an approval against a self-hosted domain on every desktop OS.

### R12-16 · Major · Targets: AGT, KLN, MFG, UIX, CONTRACT
**Section:** AGT Acts and approvals (D-AGT-20, D-AGT-30); KLN Phasing (`release_data` for STEP and 3MF exports); MFG D-MFG-25
**Problem:** Every byte that leaves a tenant goes through the `release_data` Act family, and every Act needs an assigned Approval on the server's page with WebAuthn. KLN applies this to STEP and 3MF exports in phase 1, and no tab says where the tenant boundary lies for a local file. So the phase 1 wedge user, who hands a 3MF to their own slicer (D-MFG-25) or saves a STEP file for a shop, needs a team server, an inbox, a passkey and a recipient record for each export. The spec does not define whether a desktop install without a server can export at all.
**Evidence:** D-AGT-30: "Every byte that leaves a tenant goes through one Act family, `release_data` ... restricted-party screening ... audit". D-AGT-20: "`act.commit` creates an approval request that Cedar policy assigns to named approvers ... after phishing-resistant WebAuthn user verification". KLN phase 1: "`release_data` for STEP and 3MF exports". D-MFG-25: Crucible "writes a 3MF build ... and opens it there". Contract 13.1 names phase 1 the "Wedge: code-CAD and 3D printing".
**Fix:** In D-AGT-30 and KLN, define the tenant boundary for local files. A human principal writing an export to a local folder or a local application is an audited local write, not an Act, when the payload's label is `public` or `internal`, carries no export control, and is not addressed to a recipient record. Agent-prepared exports, labelled or controlled payloads, and every transfer to another organization stay `release_data` Acts. State in contract 13.2 whether phase 1 supports a desktop install without a team server, and what it can do.

### R12-24 · Minor · Targets: CONTRACT, PLT, UIX
**Section:** CONTRACT 9 Tier 1 preview; PLT Targets; PLT The determinism suite
**Problem:** Three criteria of the preview rule cannot be executed as worded. Preview targets must pass "the golden-product checks headless", but Safari is a preview target and PLT names no runner that drives real Safari, and a WebKit build is not Safari. "Accessibility certification" is not a defined artefact for WCAG, which has conformance claims rather than certificates. "GPU-driver qualification" has no pass criterion.
**Evidence:** Contract 9: "runs the same build with identical features, passes the determinism suite and the golden-product checks headless ... installers, updater, accessibility certification and GPU-driver qualification complete by the next gate". The PLT suite names "wasm32 in Node and headless Chrome" for the per-merge set, and only "every other Tier 1 target and browser engine" nightly.
**Fix:**
- **Safari:** contract 9 reads "golden-product checks in automation", and PLT names a Safari runner (safaridriver on a logged-in macOS CI host).
- **Accessibility:** "accessibility certification" means a published Accessibility Conformance Report per target, built on UIX-O-A11Y-1 to UIX-O-A11Y-3 plus an external audit.
- **GPU drivers:** "GPU-driver qualification" means PLT-O-GPU-1 and UIX-O-SNAP-2 pass on every lab device listed for the target.

### R12-28 · Minor · Targets: UIX
**Section:** UIX GPU capability tiers; UIX Platform notes (macOS)
**Problem:** The tier table makes 64-bit atomic min and max a G1 requirement, but compute rasterization, the only user, arrives in phase 2. The platform notes then let Apple GPUs without these atomics "run G1 without compute rasterization", which contradicts the table and leaves capacity undeclared for that case.
**Evidence:** UIX tier table, G1: "Compute, storage buffers, indirect draws; 64-bit atomic min and max for compute rasterization". UIX Platform notes: "some older Apple GPUs may lack 64-bit atomic min and max [unverified], so they run G1 without compute rasterization".
**Fix:** G1 requires native compute, storage buffers and indirect draws. Compute rasterization is a reported G1 capability, `compute_raster`, with its own capacity row in contract 13.3 from phase 2. The graphics popover names it.

### R12-33 · Minor · Targets: UIX
**Section:** UIX Open questions 2, 3, 4, 5, 7, 8 and 9
**Problem:** Seven UIX open questions can be decided now, which removes undecided items from phase 1 and phase 2 planning.
**Evidence:** UIX Open questions 2 to 5 and 7 to 9.
**Fix:** Decisions:
- **2, mesh shaders:** no mesh shaders before phase 4, since WebGPU has none and they would add a G1-only path for a capacity gain alone.
- **3, Field evaluators:** FLX emits WGSL evaluators for H¹ Lagrange elements up to p = 4 on the immersed octree in phase 1; other discretizations use vertex samples with stated error until their evaluators exist.
- **4, web 64-bit atomics:** G2 compute rasterization waits until the feature ships in stable Chrome, Firefox and Safari; until then G2 uses the compacted index buffer.
- **5, 3D mouse SDK:** devices are read as HID on every desktop OS and through WebHID in Chromium, with the vendor driver as an optional path, so no SDK licence sits on a critical path; counsel still checks device terms.
- **7, usability thresholds:** 90% task success on core tasks gates each phase, and System Usability Scale scores are reported as a tracked metric, not a gate.
- **8, visionOS:** WebXR in Safari, since Safari 18.0 for visionOS 2 "adds support for immersive-vr sessions with WebXR" (https://webkit.org/blog/15865/webkit-features-in-safari-18-0/); a native shell only with a funded Tier 2 commitment.
- **9, saved views:** shared views live in the repository, and per-user views in a per-user store that creates no Changes.

### R12-34 · Minor · Targets: UIX
**Section:** UIX Oracles (UIX-O-SNAP-2)
**Problem:** UIX-O-SNAP-2 judges 3D rendering against "references per backend" without saying where the references come from. If they are the renderer's own approved outputs, the oracle detects regressions, not errors, and an agent-built renderer can pass while wrong from the first reference.
**Evidence:** UIX-O-SNAP-2: "Mean ꟻLIP at most 0.01 against references per backend". UIX-O-OIT-1 and UIX-O-MAT-1, by contrast, name independent references (depth peeling, path tracing).
**Fix:** UIX-O-SNAP-2's references come from an independent CPU reference rasterizer kept in `oracles/uix/` and written separately from `apps/renderer`, for shading, edges and sections on the golden products. Regression images become a separate oracle.

### R12-35 · Minor · Targets: PLT, UIX
**Section:** PLT and UIX [unverified] marks
**Problem:** Several [unverified] marks in PLT and UIX can be closed with primary sources. Leaving them open hides settled facts from implementers, as R6-47 found in round 1.
**Evidence:** See the Verified claims section: `Atomics.waitAsync` is Baseline 2025; tikv-jemallocator lists only Linux and macOS targets and gates its use on `not(target_env = "msvc")`; cargo-deny's four checks; cargo-auditable's embedded JSON; WER's local-dump configuration; Burns and Hunt 2013; WebXR on visionOS; the cross-origin isolation requirement for shared memory. The AWS-LC FIPS mark stays open: the aws-lc-rs README says AWS-LC-FIPS 3.x "has been submitted to NIST for certification" (https://github.com/aws/aws-lc-rs).
**Fix:** Remove these marks and cite the pages in the Verified claims section. Keep the AWS-LC mark and record the README's status, with a phase 2 check before FIPS mode ships.

## Verified claims

- PLT: Chrome ships WebGPU on Linux by default only for Intel Gen12+ (from 144) and NVIDIA on Wayland (from 147) | https://github.com/gpuweb/gpuweb/wiki/Implementation-Status
- PLT, UIX: Chrome keeps WebGPU behind a flag on Windows ARM64 | https://github.com/gpuweb/gpuweb/wiki/Implementation-Status
- PLT, UIX: Firefox ships WebGPU on Windows from 141 and on macOS from 145 (macOS 26) and 147 (all versions), and on Linux only in Nightly | https://github.com/gpuweb/gpuweb/wiki/Implementation-Status
- UIX: WebGPU is on by default in Safari 26 (macOS, iPadOS and visionOS 26) | https://github.com/gpuweb/gpuweb/wiki/Implementation-Status
- PLT: Wasmtime rates Windows ARM64 Tier 3 (lacking CI testing and a full-time maintainer) and aarch64 macOS and Linux Tier 2 (lacking continuous fuzzing) | https://docs.wasmtime.dev/stability-tiers.html
- PLT: every Wasmtime release that is a multiple of 12 is an LTS supported for 24 months, with security fixes on every supported release | https://docs.wasmtime.dev/stability-release.html
- PLT: WASI 0.3.0 shipped on 11 June 2026 | https://github.com/WebAssembly/WASI/releases
- PLT: `crash-handler` has no Windows aarch64 support | https://github.com/EmbarkStudios/crash-handling
- PLT: jemalloc has no Windows support in the common Rust bindings | https://github.com/tikv/jemallocator
- PLT: cargo-deny checks licences, bans, advisories and sources | https://github.com/EmbarkStudios/cargo-deny
- PLT: cargo-auditable embeds the dependency list as compressed JSON in a linker section | https://github.com/rust-secure-code/cargo-auditable
- PLT: Windows Error Reporting can store local user-mode dumps (LocalDumps key) | https://learn.microsoft.com/en-us/windows/win32/wer/collecting-user-mode-dumps
- PLT: `Atomics.waitAsync` is available across current browsers (Baseline 2025) | https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Atomics/waitAsync
- PLT: about 60% of disk in Chrome and Safari, the smaller of 10% or 10 GiB in Firefox best-effort mode, and Safari's seven-day deletion of script-written data | https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria
- PLT, UIX: AccessKit has no released web adapter (planned) and no rich-text support | https://github.com/AccessKit/accesskit
- PLT: the Core Ultra 7 258V has 8 cores, 8 threads, AVX2 and an Arc 140V GPU | https://www.intel.com/content/www/us/en/products/sku/240957/intel-core-ultra-7-processor-258v-12m-cache-up-to-4-80-ghz/specifications.html
- PLT, CONTRACT: App Review guidelines 2.5.2 (no downloaded code that changes functionality) and 3.2.2(i) (no store-like interface for plug-ins) say what the spec cites them for | https://developer.apple.com/app-store/review/guidelines/
- UIX: the WebGPU Candidate Recommendation Draft of 15 September 2026 has no multi-draw indirect | https://www.w3.org/TR/webgpu/
- UIX: EditContext is not Baseline | https://developer.mozilla.org/en-US/docs/Web/API/EditContext_API
- UIX: Burns and Hunt, "The Visibility Buffer: A Cache-Friendly Approach to Deferred Shading", JCGT 2(2), 2013 | https://jcgt.org/published/0002/02/04/paper.pdf
- UIX: visionOS is reachable through WebXR in Safari (Safari 18.0 for visionOS 2 adds immersive-vr sessions) | https://webkit.org/blog/15865/webkit-features-in-safari-18-0/
- UIX: shared-memory threads need a secure context and cross-origin isolation | https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer
- ECO: 3MF Beam Lattice extension 1.2.0 is published | https://github.com/3MFConsortium/spec_beamlattice/blob/master/3MF%20Beam%20Lattice%20Extension.md

## Claims the reviewers verified

Drop the `[unverified]` marker on these and cite the URL in Sources.

- WebGPU is on by default in Safari 26 (macOS, iPadOS and visionOS 26) | https://github.com/gpuweb/gpuweb/wiki/Implementation-Status (R12)
- the WebGPU Candidate Recommendation Draft of 15 September 2026 has no multi-draw indirect | https://www.w3.org/TR/webgpu/ (R12)
- EditContext is not Baseline | https://developer.mozilla.org/en-US/docs/Web/API/EditContext_API (R12)
- Burns and Hunt, "The Visibility Buffer: A Cache-Friendly Approach to Deferred Shading", JCGT 2(2), 2013 | https://jcgt.org/published/0002/02/04/paper.pdf (R12)
- visionOS is reachable through WebXR in Safari (Safari 18.0 for visionOS 2 adds immersive-vr sessions) | https://webkit.org/blog/15865/webkit-features-in-safari-18-0/ (R12)
- shared-memory threads need a secure context and cross-origin isolation | https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer (R12)

## Unverified claims in your tab

Verify each with WebFetch on a primary source and drop the marker, correct it, or cut the claim if nothing supports it. Line numbers are at tag `round-2`.

- l.535: **Decision D-UIX-19:** Presence colors come from a six-color categorical set per theme, chosen to stay distinct under protan, deutan and tritan simulation (Machado, Oliveira and Fernandes 2009), and every color pairs wit
- l.640: | SOLIDWORKS-like, Blender-like | Middle drag [unverified] | Ctrl + middle drag, Shift + middle drag [unverified] |
- l.641: | Onshape-like | Right drag [unverified] | Ctrl + right drag [unverified] |
- l.650: - **3D mice.** The 3Dconnexion driver on Windows and macOS [unverified: SDK name and licensing], `spacenavd` on Linux [unverified], and WebHID in Chromium browsers; other browsers offer the desktop app.
- l.652: - **OpenXR review (phase 3).** Multiview stereo at 90 Hz per eye on G1, true and tabletop scale, ray selection, hand-placed sections, comments and verdicts. Shared sessions follow in phase 4 and passthrough overlay in ph
- l.812: | Shading pipeline | Visibility buffer with deferred attribute fetch (Burns and Hunt 2013 [unverified]) | Nanite; Bevy | 32-bit packed buffer on G2 | Resolve at most 1.2 ms per render MP |
- l.813: | Transparency | Weighted blended OIT (McGuire and Bavoil); moment-based OIT (Münstermann et al. 2018); hybrid k-buffer (Maule et al. 2013 [unverified]) | CAD X-ray modes [no public numbers] | Weighted blending, then a p
- l.818: | Field accuracy on screen | Per-pixel evaluation of high-order solutions (ElVis [unverified]) | Commercial post-processors [unverified] | Flux evaluators on the UI device (D-UIX-13) | Color error at most 1% of range; pe
- l.823: | Retained 2D editing canvas | Layered GPU canvas with live push-and-shove [unverified: no published method] | KiCad; Altium Designer | `crucible:ui/canvas2d` and an edit lane (D-UIX-27) | ELX's recorded sessions under 1
- l.847: - **macOS.** Metal has 64-bit texture atomics only from MSL 3.1, and some older Apple GPUs may lack 64-bit atomic min and max [unverified], so they run G1 without compute rasterization. Indirect-count draws exist only on
- l.848: - **Linux.** Vulkan; Wayland and X11 with fractional scaling; AT-SPI; IME through IBus and Fcitx [unverified].
- l.850: - **Browser services.** The CAS and replica live in OPFS, a service worker caches the shell, and threads need cross-origin isolation [unverified: current requirements]. EditContext and WebHID are not Baseline and have fa

## Your open questions

Close each: decide it (the reviewers propose answers above), move it to a contract change request, or keep it with the reason it cannot be decided yet.

1. **Toolkit.** The month-3 bake-off decides between the own toolkit and Masonry (D-UIX-3).
2. **Mesh shaders.** Do they beat compute culling by 15% on CAD scenes? A phase 2 benchmark decides.
3. **Field evaluators.** Can Flux emit WGSL evaluators for every discretization? The answer sets how often vertex samples apply.
4. **Web 64-bit atomics.** When `atomic-vec2u-min-max` reaches stable browsers, G2 may rasterize in compute.
5. **3D mouse SDK.** Licensing of the vendor SDK and the Linux and browser paths need legal review.
6. **Presets.** Default bindings of every imitated product need confirmation by daily users, and preset names need trade-dress review.
7. **Usability thresholds.** Are 90% task success and a System Usability Scale of 75 the right gates for professionals with strong habits?
8. **visionOS.** A native shell, or WebXR in Safari?
9. **Saved view location.** In the design repository, or in a store that creates no Changes? `repo` decides.
10. **Findings declined in part.**
    - R4-12: toolpath playback and the NC code panel stay in phase 2, because contract 13.2 defers CAM and posts and GP1 uses the shop's own CAM; the cost panel moves to phase 1.
    - R4-06: the setup-sheet preview arrives with MFG's CAM in phase 2, for the same reason.
    - R3-41: ten design sections rather than eight, so each capability table covers one coherent area.

## Known items

- Add one sentence under each drawn diagram that tells the reader how to read it (`diagrams/10-ui-frame-graph.jsx`, `diagrams/10-ui-drag-preview.jsx`).
