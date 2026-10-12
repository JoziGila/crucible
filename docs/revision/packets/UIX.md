# UIX round 4 packet

Your tab is `docs/spec/10-ui.md` at v3 (tag `round-3`). Round 4 fixes, in one pass: the 54 third-review findings that target it (6 Critical, 29 Major, 19 Minor), its 0 `[unverified]` claims, its open questions and the known items below. Contract v7 is binding; its section 18 lists the rulings on this review, and many findings below are already settled there.

## Third-review findings

### R15-04 · Major · Targets: KLN, CONTRACT, UIX, ING
**Section:** Contract 7.1 `repo` (Loro, reconnection); KLN "Live documents", "Offline work and sync", D-KLN-22, D-KLN-24
**Problem:** Concurrent edits to one Ingot text merge by two different algorithms: Loro's CRDT (Fugue leaves, Kleppmann's tree move) for live sessions, and the three-way block merge with GumTree and Mergiraf-style triples for branches. A reconcile step patches the gap, and the 60 s rule routes a divergence to one or the other, so the same pair of edits merges differently depending on timing. Crucible already has a central relay that checks every update, and offline work beyond 60 s already becomes a branch, so the CRDT handles only short divergences that a sequencer handles more simply. Loro adds a document per (package, module label), block-id mapping and its own oracles.
**Evidence:** KLN: "The relay checks every update against the sender's permissions and enforced locks"; D-KLN-24: offline work "rejoins as a branch when the disconnection exceeded 60 s". Figma's multiplayer post: "Figma isn't using true CRDTs though", because "the server is the ultimate authority" and "can define the order of events" (https://www.figma.com/blog/how-figmas-multiplayer-technology-works/). Replicache: "In Replicache, the server is authoritative", and the client "rewinds … applies the server's patch, and then replays pending mutations" (https://doc.replicache.dev/concepts/how-it-works).
**Fix:** Replace Loro with a server-sequenced edit log per branch: clients apply `SourcePatch`es optimistically, the relay orders them, and clients rebase pending patches with the same `MergeDriver` block merge that branches use, so live and branch merges share one semantics and one oracle. Literal edits stay last-writer-wins by sequence order. Delete D-KLN-22's CRDT, the block-id mapping and the reconcile step; keep per-module replication for labels as per-module sequencing. If the founder keeps Loro, state why a central relay is not enough, and make the reconcile step call the same `MergeDriver` so outcomes cannot depend on timing.

### R15-16 · Major · Targets: CONTRACT, KLN, AGT, PLT, UIX
**Section:** Contract 2 (Fidelity), 5 (`PriorityClass`), 12 (the `PoolLane` rename); KLN "Scheduling and cancellation"; AGT "Scheduling on Kiln workers"; PLT D-PLT-13; UIX "Interactive edit lane"
**Problem:** "Interactive" names a fidelity, a `PriorityClass`, a `PoolLane` and UIX's edit lane, and they do not line up: the `Interactive` priority class runs on the `Foreground` lane, while the `Interactive` lane serves drags. KLN's table also adds a fifth class, "`Interactive`, drag", which AGT's four-row class table lacks. Contract 12 renamed PLT's pool priority to avoid exactly this kind of clash and left the worst one in place.
**Evidence:** PLT: "`pub enum PoolLane { Interactive, Foreground, Background }`"; "AGT's interactive `PriorityClass` to `Foreground`". KLN: "`Interactive`, drag | … | `Interactive`"; "`Interactive` | A person waiting … | `Foreground`". AGT's class table has `Interactive`, `Agent`, `Ci`, `Batch`.
**Fix:** Keep `Interactive` only as a fidelity. `PoolLane` becomes `Drag`, `Foreground`, `Background`; `PriorityClass` becomes `Drag`, `Foreground`, `Agent`, `Ci`, `Batch` in AGT, KLN and `base`; UIX's "interactive edit lane" becomes "the drag lane". Add "interactive" (for lanes or classes) to the glossary's "Never call it" column.

### R15-30 · Minor · Targets: CONTRACT, ING, KLN, AGT, UIX
**Section:** Contract 5 (`CallSite`, `ResultStatus`)
**Problem:** `LiteralSite` crosses five tabs and enters node keys, but the contract never defines it. `ResultStatus::Proxy` appears in contract 5 and the 13.3 drag row with no definition.
**Evidence:** ING: "literal overrides keyed by `LiteralSite` (statement identity, call identity, argument slot)"; KLN rule 5 under Keys; AGT and UIX interface rows. Contract 5: "`Pending`, `Proxy`, `Ready(Fidelity)`, …".
**Fix:** Contract 5 adds "`LiteralSite` [ING]: a `CallSite` plus an argument slot; overrides key by it and follow `#[was]`" and "`Proxy`: a dependent shown by affine extrapolation from its last value while it recomputes, never cached".

### R16-01 · Critical · Targets: CONTRACT, AGT, UIX, MFG, KLN
**Section:** Contract 7.6 "Act approvals"; AGT "Approval limits" row; UIX approval page; MFG "Approval, transfer and physical safety"
**Problem:** Every denial blocks re-preparing a plan to the same recipients for 24 hours, and a session may hold at most three pending requests. The rule applies to human-prepared plans as well as agent ones. Approvers use rejection as their normal way to say "fix this": a shop lead rejects a program because of a feed in op 3, and a change board rejects a release because a drawing note is wrong. Under this rule the corrected program cannot go to that machine until tomorrow. A rejected release also blocks every release delivery to the organization's own ERP recipient for a day.
**Evidence:** Contract 7.6: "At most three pending requests per session; a denial blocks re-preparing a plan to the same recipients for 24 h and offers 'report as suspicious', which freezes the session." AGT's capability table: "Three pending; 24 h block after denial … `act/denied_cooldown`". UIX's Proposal review offers "Request changes" (10-ui line 498), but the approval page has only approve and deny. MFG step 4 sends every `Prototype` program through an approved `send_to_machine` plan, so prove-out rejections are routine.
**Fix:** Give the approval page three outcomes. **Approve.** **Return for changes:** closes the request with a reason and no cooldown. A new plan with a different digest may be prepared at once, and resubmitting the same digest is refused with `act/returned_unchanged`. **Deny as suspicious:** today's behaviour, which freezes the session and applies the 24 h block. Count the pending limit per (session, Act class, recipient) and apply it only to contexts with an agent in the delegation chain. Human sessions batch effects into one plan instead. Contract wording: "A return for changes closes the request without penalty; only a denial marked suspicious blocks re-preparing a plan to the same recipients for 24 h and freezes the session." Add AGT-O-9 cases for both outcomes.

### R16-07 · Major · Targets: MFG, UIX
**Section:** MFG "Milling, drilling and probing strategies"; "Programs, regeneration and agents"; D-MFG-22; UIX toolpath playback
**Problem:** CAM programmers in Mastercam, hyperMILL and NX edit toolpaths every day. They trim passes to a boundary, delete or reorder passes, move an entry point, relink, and slow the feed in one region. MFG and UIX offer strategies, regeneration, playback and an NC panel, but no toolpath edit. Users would have to tune strategy parameters until the path looks right, or hand-edit the NC. A hand-edited program becomes a legacy program that loses associativity. D-MFG-22 also addresses moves by (edge `EntityId`, vertex index), a positional key that regeneration renumbers, so an edit could not survive a design change.
**Evidence:** MFG's capability tables and UIX lines 602 to 634 contain no edit operation on a `Toolpath`. D-MFG-22: "A move is addressed by (edge `EntityId`, vertex index), not by a persistent name."
**Fix:** Strategies emit keyed passes, as pattern generators do: a key of (depth level, region key, pass index along the region's medial order). Add `std::mfg::edit` features written after the strategy call:
- `trim(tp, by: Region | Plane | Boundary, keep:)`
- `remove_passes(tp, keys)`
- `reorder(tp, keys)`
- `relink(tp, policy)`
- `entry(tp, at: Query)`
- `feed_scale(tp, region, factor)`

Each edit resolves by pass key. A key lost after regeneration is a `ResolveError` with fixes, never a silent re-target. Gouge, collision and engagement checks re-run on the edited path. Phase 2, with oracle MFG-O-PROG-6: edits survive a dimension change that keeps the passes, and fail typed when a pass disappears.

### R16-09 · Major · Targets: MEC, UIX
**Section:** MEC "Sketching: Entities and constraints"; UIX "Handles, push-pull and sketching"
**Problem:** The sketch entity and constraint tables have no trim, extend, split, sketch fillet, sketch chamfer, silhouette projection or DXF import. UIX says only "the usual drawing and editing tools". In a constraint-first source model, trim is a design question, not a UI detail. It turns a circle into an arc, splits a line into two entities with new helper names, and must decide what happens to constraints and dimensions on the removed span. Those choices change `EntityId` roles downstream.
**Evidence:** MEC's entity table (lines 106 to 116) and constraint table (lines 120 to 133); `rect` names its sub-entities, but nothing names the pieces of a split line. UIX line 449: "with the usual drawing and editing tools".
**Fix:** MEC specifies sketch edits that rewrite source. `trim(entity, at: point)`, `extend(entity, to: entity)` and `split_at(entity, point)` name their pieces `.a` and `.b` in curve direction. `corner_fillet(v, r)` and `corner_chamfer(v, d)` create a named entity `fillet(v)`. The constraint-transfer rule:
- Coincidence and tangency move to the surviving endpoint.
- Dimensions on a removed span are deleted, and the source diff lists them.
- Seeds of new points come from the solved geometry.

`import_dxf(asset, layers:)` writes entities with inferred coincidences within a stated tolerance and `fix` constraints, in phase 2 with ECO's DXF reader. Add oracle MEC-O-SK-10: trims on held-out sketches keep the solve report's freedom count and every surviving role.

### R16-10 · Major · Targets: MEC, UIX
**Section:** MEC D-MEC-13; "Derived parts and families"
**Problem:** D-MEC-13 rejects captured in-context references and requires skeletons and interface records. That is defensible, but no gesture or feature turns the commonest machinery-design act into an explicit reference: designing a bracket in the assembly by picking edges of the frame it bolts to. Without one, designers must stop, refactor the frame into a skeleton and come back. Many will instead copy dimensions by hand, which loses the very associativity the rule protects.
**Evidence:** D-MEC-13: "Implicit in-context references that capture another part's geometry are not supported." `derive(source, take, …)` takes outputs from "a feature here or in a pinned dependency", with no placement from an assembly path. Neither MEC nor UIX defines an in-assembly pick.
**Fix:** Add the gesture "Reference from assembly". It writes two explicit, reviewable edits:
1. If the provider's source is writable, a named output added to the provider feature's returned record (`mount_face`), with no new keyword. Otherwise a `derive(take:)` of the picked entity.
2. In the consumer, `context_ref(asm.path("frame/rail_2"), provider.mount_face)`, which carries the placement from that Instance path.

Cycles fail at compile time with the loop listed. The Proposal review shows the new cross-part edge in the dependency view, and moving the provider updates the consumer on rebuild. Phase 2, with oracle MEC-O-AS-14.

### R16-12 · Major · Targets: KLN, AGT, UIX
**Section:** KLN "Revisions and lifecycle states", "Change orders"; AGT D-AGT-20; contract 7.6 "Act approvals"
**Problem:** Releases need "the required Approvals" from approvers "assigned … by Cedar policy". Nothing models how a change board works:
- which roles must sign (design, manufacturing, quality, customer);
- in what order, serial or parallel, and with what quorum;
- added roles triggered by content, such as quality when a special characteristic changes;
- delegation during absence;
- due dates and reminders.

Teamcenter and Windchill users rely on workflow templates of exactly this kind. Cedar can say who may approve; it cannot say who must, in which order.
**Evidence:** KLN line 552: "the required Approvals". Contract 7.6: approval requests are "assigned to named approvers by Cedar policy". No tab defines a route, quorum or delegation record.
**Fix:** Add an `ApprovalRoute` policy record to KLN's policy package. It holds ordered stages, each a set of roles with a quorum (`All`, `Any`, `AtLeast(n)`). It holds conditions over the `ApprovalSubject`, such as Item classes, safety characteristics or label `controls`, that add stages. Due dates send reminders and escalate to a named role, and never approve automatically. Delegation records name principal, delegate, scope and expiry. Delegation of a physical-effect or `controls` class needs D-KLN-41's two people, and nothing ever delegates to an agent. The approval page shows the route's progress. Phase 2, with change orders, and oracle KLN-O-CHG-3: routes complete only when every stage's quorum holds, and a delegated signature names both people.

### R16-15 · Major · Targets: ELX, UIX, KLN
**Section:** ELX "The drawn schematic", D-ELX-27; KLN "Diff, large assemblies and references"; contract 7.6 Proposal review
**Problem:** Schematics and layouts are `table { … }` rows, and review shows "feature, geometry, metric and source diffs". No tab defines what an electrical reviewer sees. A row diff of segment coordinates is unreadable. KLN's geometry diff (changed regions, Hausdorff distance) does not show what changed electrically: a moved symbol, a pin moved to another net, a changed value, copper added on L3. Electronics review in incumbents is visual and net-aware.
**Evidence:** KLN's diff table lists Source, Feature, Geometry, Metric and BOM diffs only. ELX never mentions a diff. Contract 7.6: "Proposal review shows feature, geometry, metric and source diffs."
**Fix:** ELX defines two diff views as Kiln nodes. The **schematic diff** shows symbols added, removed or moved, wires whose net membership changed highlighted in both versions, and value and part changes. The **layout diff** shows a per-layer copper XOR computed exactly from the integer data, moved parts with displacement arrows, and changed rules with the objects they now affect. A net-partition diff lists merged, split and renamed nets. UIX shows these views in Proposal review for the Electronics preset. Phase 3, with oracle ELX-O-SCH-6: every seeded change appears once, and unchanged items never appear.

### R16-30 · Minor · Targets: CONTRACT, UIX, KLN
**Section:** Contract 7.6 "Approval credentials"; contract 9 Tier 2; CCR-UIX-5 ruling
**Problem:** No Act is approvable on a phone, including release and change-notice Acts with no physical effect and no `controls` label. Change board members approve engineering changes from phones in incumbent PLM, and an approval waiting for someone to reach a desk delays every release. The ruling's reasons, physical effects and AAL3, do not apply to an uncontrolled release.
**Evidence:** Contract 7.6: "Synced passkeys sign in but never approve or sign, and Crucible's phone clients offer no approval." Contract 16, CCR-UIX-5: "no Act is approvable on a phone".
**Fix:** Allow the release, change-notice and deviation Act classes, with no `controls` label and no physical effect, to be approved in a phone browser on the approval origin. The approver must use a roaming security key from the AAGUID allowlist (NFC or USB), which meets the device-bound requirement. Physical-effect Acts, `controls` payloads and Part 11 signatures stay off phones.

### R17-02 · Critical · Targets: CONTRACT, UIX, AGT, KLN, PLT, MFG
**Section:** Contract 7.6 "Approval credentials"; UIX "Approvals" (Credentials); PLT D-PLT-41; KLN "Electronic signatures"; MFG D-MFG-24
**Problem:** The whole Act model rests on which credentials may approve, yet enrolling a new approval credential needs only a signed-in app session. Sign-in accepts synced passkeys and SSO, so anyone who phishes an SSO session or steals a synced passkey enrols a security key they hold and approves exports, releases and machine transfers. The machine gateway trusts a server-signed approver directory, so the enrolled key reaches the shop floor too. "Synced passkeys never approve" is therefore one step from void.
**Evidence:** UIX: "Enrolment starts from a signed-in Crucible desktop or tablet app, which reports its form factor, or uses an allowlisted security key." The form factor is a client claim. NIST SP 800-63B-4 4.1.2.1 requires binding a new authenticator to need "authentication at either the maximum AAL currently available" or the new authenticator's AAL, whichever is lower, and that "the CSP SHALL notify the subscriber via a mechanism independent of the transaction binding the new authenticator" (https://pages.nist.gov/800-63-4/sp800-63b.html). D-KLN-41's two-person list does not include credential enrolment.
**Fix:** Contract 7.6 adds: "Enrolling an approval credential is itself approved on the approval origin: by an existing approval credential of the same person, or, for a person's first credential, by an `admin` with their own approval credential plus an identity check recorded in the record, effective after 24 h. Every enrolment notifies the person through their identity provider's out-of-band channel and the security contact. The approver directory the gateway pins lists credential public keys, and a key enrolled within 24 h never approves a physical-effect Act or an Act with `controls`." Add credential enrolment and revocation to D-KLN-41, drop "reports its form factor" from UIX (the BE flag already decides), and state that on macOS, iPadOS and Android platform passkeys are backup eligible, so those devices approve only with a roaming security key. UIX-O-APPR-1 gains: a synced-passkey session cannot enrol a credential.

### R17-09 · Major · Targets: KLN, UIX, AGT
**Section:** KLN "Electronic signatures"; UIX "Approvals" (Isolation); AGT D-AGT-20
**Problem:** The tabs give two incompatible definitions of what an approver's authenticator signs. KLN's offline verifier expects the WebAuthn challenge to equal the signed `ObjectId`; UIX and AGT make it a hash of plan digest, request id and approver id. In KLN's form the meaning (`Reviewed`, `Approved`, `Released`) and the signer are outside the signed bytes, so a server could relabel a review signature as a release approval and it would still verify, which Part 11's 11.50 and 11.70 linkage requirements exist to prevent. A challenge equal to a content hash is also predictable rather than fresh.
**Evidence:** KLN: "the client data whose challenge is the signed `ObjectId`". UIX: "Each challenge is the hash of plan digest, request id and approver id." AGT: "Its challenge hashes plan digest, request id and approver id."
**Fix:** One definition, owned by KLN and cited by UIX and AGT: "challenge = SHA-256(domain tag ‖ server nonce of 16 random bytes ‖ signed `ObjectId` ‖ meaning ‖ signer principal ‖ request id). The signature record stores the nonce and the other fields, so an offline verifier recomputes the challenge." KLN-O-SIG-1 adds: a record whose meaning is changed after signing fails verification.

### R17-15 · Major · Targets: CONTRACT, AGT, ELX, UIX
**Section:** Contract 7.6 "Firmware"; AGT D-AGT-31 (Firmware)
**Problem:** "Client flashing through `apps/platform` or WebUSB is the same Act", but a server Approval cannot bind what a client writes to a USB probe. WebUSB permission belongs to the web app's main origin, which R11-05 already treats as script-injectable, so injected script with a remembered device grant can flash any image with no Act at all. In the browser, the read-back check is performed by the same compromised code. The machine gateway verifies Approvals in its own core (D-MFG-24); client flashing has no equivalent.
**Evidence:** Contract 7.6: "Client flashing through `apps/platform` or WebUSB is the same Act." No tab says which component checks the Approval signature and image digest before bytes reach the probe.
**Fix:** Contract 7.6: "Client flashing runs only in code that verifies the Approval: in browsers, on the approval origin page after the ceremony, which holds the WebUSB grant and checks the image's SHA-256 against the approved plan; on desktops, in `apps/platform`'s flashing service, which verifies the Approval signature against the pinned approver directory as the machine gateway does. The main web origin never holds a WebUSB grant." AGT-O-21 adds a main-origin flashing attempt.

### R17-26 · Minor · Targets: UIX, AGT, PLT
**Section:** UIX "Approvals" (Isolation); D-PLT-41
**Problem:** The approval origin is `approve.<deployment>`, a subdomain of the main app's site, and relies on `SameSite=Strict` cookies. SameSite compares sites, not origins, so the main origin's script is same-site with the approval origin and can toss cookies onto it with a `Domain=` attribute. That allows session fixation on the very page R11-05 separated.
**Evidence:** UIX: "The page lives at `approve.<deployment>`" with "`SameSite=Strict` cookies and no CORS".
**Fix:** Require `__Host-`-prefixed, host-only cookies on the approval origin, reject requests that carry any non-`__Host-` cookie, and recommend a separate registrable domain for hosted deployments. The approval origin publishes no WebAuthn related-origins file. UIX-O-APPR-1 adds a tossed cookie.

### R17-30 · Minor · Targets: CONTRACT, UIX, AGT
**Section:** Contract 7.6 "Act approvals" (page contents)
**Problem:** The approval page shows "the session's purpose, marked as agent text". An injected agent's purpose ("routine; already cleared by the export officer") is a direct social-engineering line to the approver, the last control, and a label does not neutralize persuasive text.
**Evidence:** Contract 7.6: "the session's purpose, marked as agent text".
**Fix:** "The purpose appears collapsed below the typed content, as a handle with its integrity flags, and expands only on request; text from an `instruction_tainted` context carries a banner naming the taint sources."

### R18-03 · Critical · Targets: CONTRACT, PLT, ANV, FLX, UIX
**Section:** Contract 13.2 "Build program" items 1 and 4; PLT "The build program" (D-PLT-45)
**Problem:** A work item opens only when its oracles exist "as executable checks", and builders never edit `oracles/`. An executable Rust oracle must compile against the crate's API, which does not exist before the builder writes it. So either the oracle role invents signatures the builder must match exactly (nowhere specified), or the builder changes a signature and breaks a locked oracle it cannot fix. In one Cargo workspace, a builder's API change also breaks the workspace build through `oracles/`, which CI then blames on the builder. No tab says whether oracles bind to crate APIs, to `api` methods, to the CLI or to files.
**Evidence:** Contract 13.2: "A work item opens only when its oracle ids exist in `oracles/` as executable checks written by the oracle role and passed by the verifier." D-PLT-45: "Policy refuses builder Changes under `oracles/`." The Rust signatures in the tabs are fragments (R18-01, R18-06, R18-07 show they do not compile together).
**Fix:** Contract 13.2 adds a step before item 1: "**Interface first.** For each work item the oracle role writes a contract crate, `<crate>-contract`, with the public types and signatures the oracles call and bodies of `unimplemented!()`. The verifier checks it against the tab's Rust surface. Builders implement it and may not change it; a signature change is a Proposal by the oracle role." Oracles bind in this order of preference: `api` methods, CLI and file formats (black box); WIT worlds; contract crates. `oracles/` is a separate Cargo workspace that depends on contract crates by path, so builder code never breaks its build. PLT-O-BLD-4 adds: a builder Change that alters a contract crate is refused.

### R18-04 · Major · Targets: AGT, PLT, UIX, CONTRACT
**Section:** AGT "One catalog, several transports", Platform notes; PLT D-PLT-12, "The browser target"; contract 12
**Problem:** AGT says the desktop app, web app and CLI "link `core/api` in process", while PLT runs the engine as a separate process or worker that the UI reaches only through `api` messages. `core/api` holds the method implementations, so it depends on `repo`, `kiln`, Anvil and Flux. The desktop UI process and the browser's UI module would then link the whole engine, doubling the browser download against contract 13.3's 25 MiB first-visit cap, and the UI could call the engine in process, which D-PLT-12 forbids.
**Evidence:** AGT: "`core/api` has no transport code; the desktop app, web app and CLI link it in process." and "the page links `core/api` as Wasm and runs no models." D-PLT-12: "The UI talks to the engine only through `api`. The engine runs as an OS process on desktop, a worker in browsers". PLT's memory table gives the "UI module" its own 512 MiB.
**Fix:** Split the Surface row of contract 12 into `api-schema` (method catalog types, error namespace, canonical codec, client stub and transport traits; depends only on `base`) and `api` (the server: method implementations over `repo` and `kiln`). `apps/desktop`'s UI process, the browser UI module, `sdk/rust` and `apps/mcp`'s client side depend on `api-schema` only. `cargo xtask check-layers` fails any `apps/ui-toolkit`, `apps/renderer` or UI entry point that depends on `api`. AGT's sentence becomes: "the engine process, the browser engine worker and the CLI's local mode link `core/api`; UIs link `api-schema`."

### R18-05 · Major · Targets: CONTRACT, PLT, ANV, UIX, FLX, KLN
**Section:** Contract 3 principle 6; PLT D-PLT-45, PLT-O-BLD-5; ANV and UIX Oracles
**Problem:** R12-13's held-out fix does not hold against agent builders, for three reasons. A "fixed hash rule" over a public corpus (the ABC subset, Thingi10K) lets a builder compute which case ids are held out and fetch those models from the public dataset. Unlimited CI runs return a pass or fail on held-out cases, which leaks them by adaptive querying, the known failure of reused holdouts. And nothing stops builder code from detecting the held-out harness (paths, environment, case counts) and behaving differently there.
**Evidence:** ANV: "ABC cases come only from the licence-filtered subset … Held-out splits follow a fixed hash rule outside the agent-readable tree." UIX: held-out scenes are "picked by a fixed hash rule from perturbed golden-product parameters and the licence-filtered ABC subset." D-PLT-45 limits only reading: "Held-out splits … are unreadable to builders." No tab limits held-out queries.
**Fix:** Principle 6 replaces "chosen by a fixed hash rule" with "chosen by a keyed hash (HMAC-SHA-256 under a key held only by the oracle role, rotated at each gate) or generated from a seed drawn at CI time". D-PLT-45 adds three rules. Builders' sandboxes have no network route to public corpora. Held-out results reach a builder only as one aggregate pass or fail per work item per day, with no per-case detail. Visible and held-out runs execute in byte-identical harnesses, with case order and count padded to a fixed size. PLT-O-BLD-5 adds a planted builder that probes held-out results case by case and must fail to identify more than chance.

### R18-09 · Major · Targets: ING, FLX, KLN, ANV, UIX, CONTRACT
**Section:** Contract 5 `Quantity<D>`, `Field<D, V>`; ING "Types and dimensions"; FLX "Rust API"; UIX "From gesture to Ingot edit"
**Problem:** The contract names Rust types canonical, but no tab says how Ingot's types exist in Rust. Stable Rust cannot compute `Quantity<D1·D2>` from const generics (`generic_const_exprs` is unstable), and the strong angular system with rational powers rules out simple marker types. Ingot also creates domains and value types at run time (user enums, tuple domains), so `Field<D: Domain, V: Value>` with `PhantomData` cannot be the representation Kiln stores or `crucible:ops` passes. Tabs already improvise: ANV uses `Length` and `Angle`, UIX `Quantity<Dyn>`, and FLX a generic `Field<D, V>`.
**Evidence:** ING: "`Quantity<D>` | A `Real` in coherent SI units with dimension `D`; checked at compile time, erased at run time" (true of Ingot, silent on Rust). UIX: `SetMeasure { target: Query, measure: Measure, to: Quantity<Dyn> }`. FLX: `pub struct Field<D: Domain, V: Value> { header, repr, _kind: PhantomData<(D, V)> }`.
**Fix:** ING and FLX state one rule in their Rust surfaces. The erased forms are canonical: `Value` (an enum over scalars, `DynQuantity { si: f64, dim: Dim }` with `Dim` a vector of rational exponents over the eight base dimensions plus a kind id, records, lists, handles) and `DynField { domain: DomainDesc, value: ValueDesc, header, repr }`. These are what Kiln memoizes, the CAS encodes and `crucible:ops` carries. Typed views are generated, not hand-written: `base` generates newtypes (`Length`, `Stress`, `Torque`) and the `Mul`/`Div` impls the prelude kind table lists, from that table, plus `Field<D, V>` as a checked view over `DynField` (`TryFrom<DynField>`). Rust code never uses `uom` or `typenum`.

### R18-14 · Major · Targets: CONTRACT, PLT, UIX, FLX
**Section:** Contract 12 (`unsafe` and `bridges/`); PLT "Crates", D-PLT-14, D-PLT-17, `CryptoProvider`; UIX "Display data"
**Problem:** The `unsafe` rule names crates, but the build links C and C++ through ordinary crates.io dependencies that the rule never mentions. mimalloc and CORE-MATH are C, and aws-lc-rs is C and assembly that needs CMake. meshoptimizer, whose codecs UIX adopts for every page, is C++. Each needs a C toolchain in the hermetic, reproducible builders and `-ffp-contract=off` where it affects results. Each needs a stated `wasm32-unknown-unknown` story, since `detmath` must be canonical in browsers and meshoptimizer decoding runs in the browser renderer. Meanwhile `kernels` is granted `unsafe` for "code-loading", though runtime-generated modules load through Wasmtime, whose unsafe deserialization belongs in `wasm-host`.
**Evidence:** Contract 12: "`unsafe` is allowed only in `simd`, `gpu`, `wasm-host`, the code-loading parts of `kernels`, `bridges/` and `apps/platform`." `bridges/` holds "optional FFI: PETSc, hypre, GPU vendor specifics". PLT: "linked C and C++ use `-ffp-contract=off`, checked in CI". UIX: "Pages use meshoptimizer's codecs".
**Fix:** PLT adds a native-code register to `deps/approved.toml`. Each C or C++ dependency records why no Rust crate serves, its targets including wasm32 (built with clang and a pinned wasi-libc sysroot, or excluded with the Rust fallback named), its compile flags, whether it affects results (only CORE-MATH may), and its fuzzing. Only register entries may build C. Contract 12 drops "the code-loading parts of `kernels`": `kernels` emits Wasm bytes and asks `wasm-host` to load them. The browser `CryptoProvider` is WebCrypto in `apps/platform-web`, stated in PLT.

### R18-16 · Major · Targets: UIX
**Section:** UIX Oracles (UIX-O-INT-1) and the 17 capability rows that cite it
**Problem:** UIX-O-INT-1 is the oracle for 17 capability rows, from presets and gizmos to sketch inference, assembly drag, presence, offline rejoin, study setup, the cost panel, 3D mice, pen input and first run. Its pass criterion is "the specified state", which no tab specifies for these rows. An oracle role cannot write it, a verifier cannot check it against the row, and per-crate oracle coverage counts all 17 rows as covered by one placeholder.
**Evidence:** UIX-O-INT-1: "Injected input scripts reach the specified state, accessibility tree and `api` calls, including failure rows". Rows citing it include "Sketching and inference", "Assembly drag and motion", "Offline and rejoin", "Cost panel" and "3D mice".
**Fix:** Split UIX-O-INT-1 into one oracle per row group, each naming its script and its machine-checkable end state as `api` calls or source. UIX-O-SKETCH-1: every inference type, given scripted pointer paths, emits the listed constraint call within 8 px and 3 px hysteresis. UIX-O-ASM-1: scripted drags never violate a mate and stop at remaining degrees of freedom. UIX-O-OFFLINE-1: disconnects of 30 s and 90 s rejoin by fast-forward or as a branch per contract 7.1. UIX-O-NAV-1: each preset's binding table replays to the recorded camera deltas. UIX-O-COST-1: displayed lines equal MFG's cost records. Keep UIX-O-INT-1 only for "registry commands emit exactly their recorded `api` calls".

### R18-18 · Major · Targets: UIX, ANV
**Section:** UIX "Display data" (`DisplayPackage`); contract 5 `DisplayPackage`
**Problem:** `DisplayPackage` is a content-addressed CAS object keyed by `GeometryId` and tolerance, yet it carries `status: ResultStatus`, which is "Ready(Preview) while streaming, then the requested fidelity". Two packages with one key then differ in content, and a streamed `Preview` package written to the CAS has a different `ObjectId` from its finished twin. That breaks the cross-design sharing the type exists for, and `Preview` results must never reach the shared cache.
**Evidence:** UIX: `/// Produced by Anvil, cached in CAS, keyed by GeometryId and tolerance` and `pub status: ResultStatus, // Ready(Preview) while streaming, then the requested fidelity`. Contract 2: `Preview` is "never written to the shared cache".
**Fix:** Remove `status` from `DisplayPackage`. A package's identity is (`GeometryId`, `chordal_error`, encoding version), and its content is fixed. Streaming status travels in KLN's `ResultEvent` for the node that demanded the package, which already carries `ResultStatus`. A coarser package is a different object with its own `chordal_error`.

### R18-19 · Major · Targets: UIX, ECO, AGT
**Section:** UIX "Extending the interface" (`crucible:ui@0.1.0`)
**Problem:** The panel world returns a UI tree as `element`, a type that must contain child elements, but WIT forbids recursive types, so the package cannot be written as specified. The `use types.{…}` clauses also name an interface `types` that the package never declares.
**Evidence:** UIX: `render: func() -> element;   // element tree from data read through api`. The WIT specification: "Types, however, cannot be recursive" (https://github.com/WebAssembly/component-model/blob/main/design/mvp/WIT.md).
**Fix:** Declare `interface types` in `crucible:ui` with a flat tree: `record node { kind: node-kind, key: u64, parent: option<u32>, props: list<prop> }` and `render: func() -> list<node>`, nodes in pre-order with parents by index. Use the same arena form for `primitive-batch` if it nests. UIX-O-EXT-1 adds a published-WIT check that `wasm-tools component wit` parses the package.

### R18-21 · Minor · Targets: PLT, UIX
**Section:** PLT "Tablets and phones" (D-PLT-33); UIX Platform notes (tablets)
**Problem:** The iPadOS plan depends on capabilities of WKWebView that no source in the tab confirms: `crossOriginIsolated` for content served through the app's own URL scheme (needed for threads), OPFS synchronous access handles, and WebGPU inside WKWebView rather than Safari. The phase 3 spike "measures only WKWebView memory limits and WebGPU", too late and too narrow for a target whose whole architecture rests on these.
**Evidence:** PLT: "A phase 3 spike measures only WKWebView memory limits and WebGPU." The gpuweb status page states Safari 26 support on iPadOS but says nothing about WKWebView (https://github.com/gpuweb/gpuweb/wiki/Implementation-Status).
**Fix:** Move the spike to phase 1 as a `device-farm` check (PLT-O-TGT-1 case) covering `crossOriginIsolated` under a `WKURLSchemeHandler` that sets COOP and COEP, `createSyncAccessHandle`, WebGPU adapter availability, the WebContent memory ceiling and Wasm compile time for the engine module. Name the fallbacks now: the single-threaded build without isolation (R18-20), WebGL2 without WebGPU, and remote evaluation above the measured ceiling.

### R18-23 · Minor · Targets: PLT, UIX
**Section:** PLT "The compute runtime" (memory-mapped rings); contract 12 `unsafe` list
**Problem:** Desktop UI and engine processes "share memory-mapped rings for tessellations and Field samples", but no crate owns them. Cross-process shared memory needs `unsafe`, and reading a buffer another process may still write is a data race, which Rust treats as undefined behaviour even if the bytes look valid.
**Evidence:** PLT: "Desktop UI and engine processes share memory-mapped rings for tessellations and Field samples and exchange `api` messages over a local socket." Only `apps/platform` among the crates involved may use `unsafe` (contract 12).
**Fix:** `platform-api` gains `SharedRing`, implemented in `apps/platform`, with a safe API: the writer publishes a slot by an atomic sequence number, and the reader copies the slot into its own memory with volatile reads before validating the sequence (a seqlock), then hands out owned bytes. The renderer uploads from the copy. PLT-O-DET-5's layering check confirms no other crate maps shared memory.

### R18-25 · Minor · Targets: PLT, UIX
**Section:** PLT D-PLT-4; PLT "Pointer, pen and touch" row; UIX "Devices"
**Problem:** winit 0.31's pen events cover Wayland, Windows and the web, plus Apple Pencil on iOS from beta 3. macOS tablets and X11 pens have no pen events, and beta 3 reclassifies X11 absolute pointers away from pens. Desktop pen parity in phase 2 therefore depends on Crucible's own patches, which the fork plan does not list.
**Evidence:** winit v0.31.0-beta.1 adds "Pen input support on Wayland, Windows, and Web via new Pointer event"; v0.31.0-beta.3 adds Apple Pencil on iOS and fixes "X11 absolute pointing devices that were misclassified as pens" (https://github.com/rust-windowing/winit/releases).
**Fix:** D-PLT-4's patch list names macOS `NSEvent` tablet events and X11 XInput2 pen axes, each with its upstream pull request as the exit. PLT-O-OS-1's recorded pen traces include a macOS tablet and an X11 tablet.

### R18-33 · Minor · Targets: PLT, FLX, UIX
**Section:** PLT "GPU compute" (known-answer tests); contract 13.3 cold start
**Problem:** Every compute pipeline runs a known-answer test "at creation and after driver or OS updates", and wgpu's `PIPELINE_CACHE` exists only on Vulkan. Run eagerly at start-up on DX12 and Metal, pipeline creation plus tests compete with the 1.5 s cold-start row, which the tab does not budget.
**Evidence:** PLT: "Each pipeline reproduces its class's recorded outputs at creation and after driver or OS updates." wgpu 30.0.1 `PIPELINE_CACHE`: "Supported platforms: Vulkan"; "Unimplemented Platforms: DX12, Metal" (https://docs.rs/wgpu/latest/wgpu/struct.Features.html).
**Fix:** Run known-answer tests lazily, before a pipeline's first result-affecting dispatch, and persist each pass keyed by (`GpuClass`, pipeline hash) in the local CAS until the driver or OS build changes. Until a pipeline passes, its Ops run on the CPU path. The cold-start row excludes compute pipelines, which PLT-O-PERF-1 states.

### R18-34 · Minor · Targets: CONTRACT, UIX
**Section:** Contract 13.2 "Critical path for phase 1" (chain C); UIX "UI toolkit" risk spike
**Problem:** Chain C still begins with "toolkit decision", which D-UIX-3 already made. The phase 0 risk spike tests AccessKit only on Windows and IME only on Windows and in Chrome. It leaves out the riskiest new piece, the AccessKit web adapter that Crucible must build, so the phase 1 web accessibility row has no early evidence.
**Evidence:** Contract 13.2: "Chain C (interface): toolkit decision → toolkit core, forward renderer and picking → …". UIX risk spike: "1,000,000-row tree with AccessKit on Windows; IME field on Windows and in Chrome; 50,000-line code panel". AccessKit lists the web adapter as planned, not released (https://github.com/AccessKit/accesskit).
**Fix:** Chain C begins "toolkit risk spike → toolkit core …". The spike adds a fourth part: the DOM mirror for the 1,000,000-row tree in Chrome, read by NVDA, within 1 ms per frame.

### R19-01 · Critical · Targets: OVERVIEW, MEC, MFG, KLN, UIX, ANV
**Section:** OVERVIEW "Where the field stands"; the lead of each primary tab
**Problem:** The bar is that Crucible wins on what AI-built clones cannot copy quickly, yet no tab names a clone except Zoo, and no page states the advantages in a user's terms. SolidCraft already ships, under MIT or Apache-2.0, much of MEC's phase 1 and 2 surface: sketches with a solver, a timeline of features, sheet metal, assemblies with joints and motion studies, STEP, IGES, 3MF, STL and OBJ, and MCP control. CADCraft is a clean-room AutoCAD with DWG read and write, and it plans its own gaps in agent-hours. Against this, Crucible's phase 1 has no sheet metal, kinematics, IGES or DXF (MEC Phasing; ECO formats), and the Overview's comparison bullets cover languages, kernels and agents only.
**Evidence:** SolidCraft README (https://github.com/bherbruck/solvecraft): "An open-source parametric 3D CAD application built in pure Rust", with "Assemblies with nested components and occurrences, joints, motion studies, contact sets, interference and material-aware mass properties". CADCraft README (https://github.com/storytold/cadcraft): "a clean-room reimplementation of Autodesk AutoCAD"; its docs/gaps.md (https://github.com/storytold/cadcraft/blob/main/docs/gaps.md) costs work in agent-hours. Zoo Design Studio (https://zoo.dev/design-studio): Zookeeper is "built into Zoo Design Studio". Grep of `docs/spec/` finds no mention of SolidCraft or CADCraft.
**Fix:** Add an Overview section "Why Crucible, and why not a clone" with one table: capability · what incumbents give · what the clones give · Crucible's mechanism · why it cannot be copied in weeks. Its rows: certified geometry with stated error and oracles (ANV); `GeometryId` identity that makes approvals, the shared cache and duplicate detection exact (KLN, ANV); merges that refuse broken checks, new interference and touched-entity conflicts (KLN, see R19-12); units and tolerances as types (ING); every check gating every merge with verdict history (MEC, KLN); validated physics with evidence levels (COV); approvals over content digests and the machine gateway (MFG, AGT); PLM records in the design repository (KLN). Each primary tab's lead gains one sentence naming its advantage over incumbents. State a phase 1 parity floor: DXF write and IGES read join phase 1 (both are formats an AI clone already ships), and say plainly that sheet metal and kinematics arrive in phase 2.

### R19-02 · Critical · Targets: MEC, KLN, UIX
**Section:** MEC Exploded views, subassemblies and interfaces (D-MEC-13); MEC Derived parts and families
**Problem:** D-MEC-13 forbids every reference to another part's geometry except through skeletons and interface records planned in advance. Designing a cover to fit a housing, a bracket to clear a cable run or a guard around a mechanism in its assembly position is the daily work of machine designers, and every incumbent supports it. Onshape does it without hidden coupling: an in-context reference is a snapshot of the assembly, never updated automatically, so the graph stays acyclic. Crucible already has every piece needed (pinned references in `ingot.lock`, `derive`, Proposals). The tab also never says that one feature may return several Parts designed together, Onshape's Part Studio pattern, or how their identities work.
**Evidence:** MEC D-MEC-13: "Implicit in-context references that capture another part's geometry are not supported"; *Rejected:* "edit-in-context with captured references, as in SOLIDWORKS". Onshape, Modeling in context (https://cad.onshape.com/help/Content/Assembly/modeling_in_context.htm): "An Assembly context (snapshot) is created", "Updates are never applied automatically", "These references are never lost or broken". Creo (https://support.ptc.com/help/creo/creo_plus/usascii/assembly/asm/About_Copy_and_Publish_Geom_Feat.html): Copy and Publish Geometry "are top-down design tools to associatively communicate design criteria".
**Fix:** Revise D-MEC-13: cross-part references go through skeletons, interface records or context pins. Add `context(of: assembly_feature, at: Pin, take: [Query]) -> Context` to `std::mech::asm` (phase 2, for GP3's covers and GP4's guards). A context is a past evaluation of the assembly at a pinned `ChangeId`, recorded in `ingot.lock` as `{ source, selector: Change, resolved }`, and returns the taken Bodies, frames and sketches transformed into the consuming Part's frame by its Instance placement at that Change. Because the pin names a past Change, the consuming Part may sit inside that assembly without a cycle. "Update context" is a Proposal that moves the pin and shows the geometry diff; a lost reference is a typed `ResolveError`; two branches that move one pin differently give `Conflict::Lockfile`. UIX adds "Edit in context": the assembly drawn transparent, selections becoming context `Query`s. State that a feature may return a record of Parts (`-> (Housing: Part, Cover: Part)`), each with its own item number and `GeometryId`, as the multi-part design pattern.

### R19-04 · Major · Targets: CONTRACT, MEC, MFG, KLN, UIX, ANV
**Section:** Contract 8 (the State of the art table); State of the art in MEC, KLN and UIX
**Problem:** Contract 8's table compares methods with "the leading implementation to beat", so whole areas of incumbent capability never appear. MEC's table has no row for weldments, mould tooling, routing, configurations, top-down design or rendering, names Onshape alone for sheet metal and OCCT for drawings, and D-MEC-37 limits published comparisons to open implementations. KLN has two PLM rows, and UIX compares its renderer with Nanite and Bevy, not with CAD products. Gaps such as R19-02, R19-05, R19-09 and R19-10 therefore pass every tab's own check.
**Evidence:** MEC State of the art rows "Sheet metal … Onshape sheet metal" and "Hidden-line removal … Open CASCADE `HLRBRep_Algo`"; MEC D-MEC-37: "published comparisons use only open implementations such as OCCT"; KLN State of the art: only "PLM change control" and "Variant management" concern PLM.
**Fix:** Add to contract 8 a second required table in the primary tabs (MEC, MFG, KLN, UIX, ANV), "Parity with incumbents": capability · incumbent and its documented feature (cited from vendor documentation) · Crucible's capability row and phase · Ahead, Equal, Later or Out of scope, with one reason. Comparing documented features is not a benchmark of a commercial kernel, so D-MEC-37 still holds. The spec check counts one row per incumbent feature listed in this review and fails a tab that omits one without an Out-of-scope reason.

### R19-05 · Major · Targets: MFG, UIX
**Section:** MFG Programs, regeneration and agents; Milling, drilling and probing strategies; UIX Manufacturing
**Problem:** A toolpath is a derived value, and MFG offers no way to edit one: no trim by boundary, deletion of passes, reordering, relinking or tool change without recalculation. Machinists use these daily to remove an air cut, avoid a clamp found at the machine, or split a path between tools. Without them, every small fix means changing strategy parameters and recomputing, which Fusion's own help calls slower.
**Evidence:** Fusion, Toolpath trimming (https://help.autodesk.com/cloudhelp/ENU/Fusion-CAM/files/MFG-TRIM-OVERVIEW.htm): "Trim parts of a milling toolpath that are contained by a polygon, plane, or boundary", and a trim "gouge-checks any leads or links that are added". Fusion, Deleting passes or segments (https://help.autodesk.com/cloudhelp/ENU/Fusion-CAM/files/MFG-TOOLPATH-DELETE-OVERVIEW.htm): "Modify a toolpath by deleting a selection of passes or segments." No MFG capability row edits a `Toolpath`.
**Fix:** Add `std::mfg::modify` (phase 2): `trim(tp, by: Polygon | Plane | Boundary(Query), keep: Inside | Outside | Both)`, `delete_passes(tp, passes: [PassKey])`, `reverse`, `reorder(tp, by:)`, `relink(tp, rules)` and `change_tool(tp, tool)` where the cutter geometry allows. Strategies key passes by depth level and offset index (`PassKey`), never by move index, so an edit survives regeneration (D-MFG-22's move addresses are not stable). Every modification re-runs the gouge and collision checks on new links and is an ordinary step in the workingstep's history. UIX's toolpath playback selects passes and boundaries for these calls.

### R19-07 · Major · Targets: KLN, UIX
**Section:** KLN Revisions and lifecycle states; Change orders; Identity and authorization
**Problem:** Review routing is unspecified. Cedar assigns approvers and protected refs require reviews, but there is no model of stages, sequential or parallel reviewers, quorum (all, any, two of three), conditions (route to quality when a special characteristic changes), or delegation when an assigned approver is away. "A policy package may replace the state machine" names an escape hatch without a contract, so an enterprise customer cannot express its change board, and one absent approver blocks a release.
**Evidence:** KLN: "A policy package may replace the state machine"; "An order's author cannot be its only approver". Windchill Workflow Template Administration (https://support.ptc.com/help/windchill/r13.0.2.0/en/Windchill_Help_Center/workflow/WFAdminAbout.html): templates "Create activities and assign them to certain roles", "Define the flow of control for the activities", with routing by "evaluating expressions". Grep of KLN finds no approver delegation.
**Fix:** Add a `ReviewPolicy` record to the policy package (phase 2): ordered stages, each a reviewer set selected by Cedar (roles and attributes), a quorum (`All`, `Any`, `AtLeast(n)`), and a condition over the order's typed facts (Item class, label, risk class, changed characteristics, cost delta). Add `ApprovalDelegation`: a signature record by the delegator naming delegate, scope, Item classes and expiry, never to an agent, refused when the delegate lacks the clearance, shown on the approval page and audited. Reminders and escalation are server notifications and never touch evaluation. One oracle routes a seeded order set through stages, quorum and delegation. UIX's Item place shows the order's stage and who is pending.

### R19-08 · Major · Targets: KLN, UIX, ANV
**Section:** KLN Items; UIX Places
**Problem:** Part reuse is one of PLM's main returns, and the spec gives no way to find an existing part by shape or by class. The Item record has a `classification` field with no schema, and there is no similarity search, so engineers recreate parts under new names. Crucible holds an advantage it never states: a name-free `GeometryId` finds exact duplicates instantly across every repository, which a filename or attribute search cannot.
**Evidence:** KLN Items: "An Item record holds number, kind, name, classification, …"; no capability row searches by shape. Siemens on Geolus in Teamcenter (https://blogs.sw.siemens.com/teamcenter/how-geolus-3d-shape-search-drives-part-re-use/): "3D shape search will find similar parts even if one person calls it a fastener while another person calls it a clip", and reuse "has enormous value in the effort to limit part proliferation". Contract 5: `GeometryId` "hashes the canonical encoding with names, lineage and name-keyed attributes removed".
**Fix:** Add to KLN (phase 2): `read.similar(subject: Body | Item, k, filters) -> [ItemMatch]`, over an access-filtered index of name-free shape descriptors computed once per `GeometryId` by a deterministic Wasm component with pinned weights; exact matches by `GeometryId` rank first. Add a `Warning` check `possible_duplicate` on Item creation. Make `classification` a typed record whose classes and properties come from a classification dictionary package (ECLASS or the organization's own, under a `DataLicence`), with properties computed from the model where possible. UIX's palette and Item place expose "Find similar".

### R19-09 · Major · Targets: UIX, MEC
**Section:** UIX Styles, appearance and color; Phasing
**Problem:** Photorealistic rendering arrives in phase 5, though industrial designers, marketing and design reviews use it from the first concept, and Onshape builds it into its browser product linked to the live model. The stated reason, experimental ray queries in wgpu, does not require the delay: a path tracer can traverse a BVH in compute shaders on G1 and G2, or on the CPU in `apps/headless-render`, and its images are non-canonical Snapshots anyway (D-UIX-26).
**Evidence:** UIX: "A path-traced Realistic preview arrives in phase 5, since wgpu's ray queries are experimental." Onshape Render Studio (https://cad.onshape.com/help/Content/render-studio.htm): it "allows the creation of photorealistic scenes from imported Part Studios or Assemblies", scenes are "linked to their part, Part Studio, or Assembly", and output is JPG or PNG.
**Fix:** Move a progressive path tracer to phase 3 (GP5's moulded enclosure is the first consumer product): compute-shader BVH traversal over `DisplayPackage` clusters on G1 and G2, a CPU path in `apps/headless-render` for G3 and servers, the OpenPBR appearances already specified, HDR environments as packages, and render scenes as shared `ViewState` files so they update with the model. Output is a Snapshot with `PlatformClass::Unverified`. Until then, state glTF (phase 2) and OpenUSD (phase 3) export to external renderers as the supported path.

### R19-10 · Major · Targets: ECO, MEC, UIX
**Section:** ECO Mechanical CAD and product data (DXF; DWG); MEC Drawings capability table
**Problem:** DXF waits for phase 2 and DWG for a licensed translator in phase 3, though shops quote, cut and archive from DXF and DWG every day. An open path exists: the acadrust crate reads and writes DXF R12 to 2018 and DWG R13 to 2018 under MPL-2.0, which contract 7.7 allows to link, and CADCraft already ships DWG through it. Crucible also has no stated way to make a 2D-only document (a layout, a plate drawn flat, an edited supplier DWG), which AutoCAD users and the CADCraft clone treat as basic.
**Evidence:** ECO: "DXF; DWG | DXF at phase 2 | R/W | … | Build; License | 2; 3"; MEC drawings row: "then DXF (2) and DWG through a licensed translator (3)". acadrust 0.4.1 (https://docs.rs/crate/acadrust/0.4.1): "MPL-2.0", "DWG Read/Write — Native binary, R13–R2018". Contract 7.7: "MPL-2.0 files may be linked" with notices and a source offer.
**Fix:** Move DXF write of drawing sheets and planar sections to phase 1, and DXF and DWG read and write to phase 2 through acadrust (linked under 7.7) or an own codec with acadrust as the oracle; the licensed translator becomes the fallback for versions acadrust lacks. In MEC, state that a drawing may hold 2D-only sheets: sketch geometry, layers as attributes, blocks as Ingot functions, hatches and dimensions, with an imported DWG becoming an editable drawing program through an import expression, as for 3D Assets.

### R19-12 · Major · Targets: KLN, OVERVIEW, UIX
**Section:** KLN Proposals and merge (D-KLN-21); KLN State of the art; OVERVIEW Where the field stands
**Problem:** Crucible's merge is far ahead of the one incumbent with CAD branching, and the spec never says so. Onshape merges per tab by Replace, Merge or Keep, cannot select changes within a tab, cannot merge drawings and reports no conflicts. Crucible merges per block, drawings included, and refuses a merge that worsens a check, adds interference or touches one entity from both sides. KLN's table names Onshape as the implementation to beat and measures only its own oracle, and the Overview omits merging.
**Evidence:** Onshape, Merging (https://cad.onshape.com/help/Content/merge.htm): "You cannot select individual changes within a tab. All changes from each tab must be either kept, merged, or replaced"; for a drawing, "changes from separate branches cannot be merged"; and "changes from different branches can be incompatible, causing errors". KLN State of the art: "CAD history and merge | … | Onshape; Mergiraf | Verdict, touched-set and connectivity conditions (D-KLN-21) | KLN-O-MERGE-1".
**Fix:** In KLN's State of the art row, write the comparison above as the reason. Add an Overview bullet: "Branches and merges. Onshape merges whole tabs and cannot merge drawings; Crucible merges blocks, drawings included, and refuses a merge that breaks a check, adds interference or edits one entity on both sides ([KLN](05-kiln-repo-plm.md))." Add a measured target to KLN-O-MERGE-1's report: the share of seeded two-branch edits that merge clean in Crucible, beside the share that a per-tab merge would keep.

### R19-14 · Major · Targets: MEC, UIX
**Section:** MEC Entities and constraints; UIX Handles, push-pull and sketching
**Problem:** Sketching is the most-used tool in every CAD system, and its editing operations are unspecified: trim, extend, split, sketch fillet and chamfer at a corner, offset of a chain in the GUI, and convert entities. UIX promises "the usual drawing and editing tools", but principle 2 requires each gesture to become a defined source edit, and MEC defines none. CADCraft lists trim, offset, fillet and arrays, and SolidCraft lists its sketch tools.
**Evidence:** UIX: "Sketches start on a plane … with the usual drawing and editing tools and construction geometry." MEC's entity and constraint tables list no trim, extend, split or corner operation. CADCraft README (https://github.com/storytold/cadcraft): "modify tools such as trim, offset, fillet, and arrays".
**Fix:** Add a "Sketch edits" table to MEC (phase 1) mapping each tool to its source rewrite: `trim` deletes the selected segment and writes `split_at` points with `point_on` constraints on the kept pieces (or, for profiles, selects regions of `make_regions` so no geometry is deleted); `extend` adds `point_on` to the target; `sketch_fillet(corner, r)` inserts an `arc` with two `tangent` constraints and moves the endpoints; `sketch_chamfer` likewise with a line; `offset` and `use_edges` as today. Each edit is one Change, keeps the `CallSite`s of untouched entities, and has an oracle on the SketchGraphs replay corpus.

### R19-19 · Minor · Targets: UIX, MEC
**Section:** UIX Handles, push-pull and sketching; MEC Assemblies capability table
**Problem:** MEC ships mates in phase 1, but UIX puts mate glyphs and Instance dragging in phase 2 and never says how a phase 1 user places an Instance or adds a mate without typing Ingot. The SolidCraft clone offers joints in its GUI today.
**Evidence:** MEC: "Mate solve and diagnosis | … | 1, 2, 3 (cam)". UIX: "In assemblies (phase 2), mates draw as glyphs and Instances drag within their degrees of freedom"; "Assembly drag and motion | … | 2".
**Fix:** State the phase 1 path in UIX: Insert Instance and Add mate are generated feature dialogs (from `instance` and the mate functions' metadata) whose two frame fields take selections as `CoordSys` queries, with the solved placement previewed; glyphs and dragging stay phase 2.

### R19-20 · Minor · Targets: MEC, UIX
**Section:** MEC Reference geometry (`std::mech::refgeom`); UIX Handles, push-pull and sketching
**Problem:** There is no reference image: designers trace concept sketches, photos and scanned legacy drawings on a scaled image in a sketch plane.
**Evidence:** Fusion, Insert canvas (https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-INSERT-CANVAS.htm): "insert an image onto a planar face, plane, or sketch plane to use as a reference". No MEC or UIX row places an image.
**Fix:** Add `canvas(image: Asset, on: CoordSys, calibrate: (Point, Point, Length), opacity)` to `refgeom` (phase 2): display-only, non-definitional, outside the `ItemDefinition`, and an instruction-capable image for agents (AGT's rule). UIX traces sketch entities over it with the usual inference.

### R19-26 · Minor · Targets: UIX, MFG
**Section:** UIX Places and workspace presets; MFG Factory connection (MBOM and routings)
**Problem:** The MBOM is written as Ingot rules, and UIX offers no editor for it. Manufacturing engineers who restructure an EBOM into stations, kits and phantoms work side by side in incumbent PLM tools, and principle 2 promises them a visual editor of the same program.
**Evidence:** MFG: "EBOM-to-MBOM rules as Ingot (phantoms, kits, stations, consumables)"; KLN: views "are Kiln nodes, never edited directly". UIX lists no MBOM view.
**Fix:** Add to UIX's Manufacture preset (phase 2) a side-by-side EBOM and MBOM tree whose drags write MBOM rule source through `EditPlan`s, with KLN's reconciliation check shown live per line.

### R19-27 · Minor · Targets: UIX, MEC
**Section:** MEC Derived parts and families; UIX Model tree, dialogs and version history
**Problem:** Part families are `family(f, key:, rows: table { … })`, and UIX gives no table editor, so a designer who maintains a 200-row family, as incumbents' design tables allow, edits text.
**Evidence:** MEC: "`family(f, key:, rows: table { … })` checks every row's types and units at compile time". UIX's variant grid shows variants but edits no rows.
**Fix:** Add a family table editor to UIX (phase 2): a grid over the `table { … }` literal with typed, unit-aware cells, paste from spreadsheets, per-row build status from `RowFailed`, and each edit one Change.

### R19-28 · Minor · Targets: UIX
**Section:** UIX View state, saved views and dashboards; Styles, appearance and color
**Problem:** `DisplayStyle` lists `Realistic` in the phase 1 `ViewState`, while realistic appearance is a phase 2 capability, so a phase 1 view file can name a style the renderer lacks.
**Evidence:** UIX `ViewState`: "ShadedEdges, Shaded, Wireframe, HiddenLine, Realistic, XRay"; "Realistic appearance | … | 2"; X-ray views are phase 2 in contract 13.3.
**Fix:** State the phase of each `DisplayStyle` variant in the struct comment, and have the renderer show an unavailable style as `Shaded` with a notice.

### R20-01 · Critical · Targets: FLX, COV, MEC, UIX
**Section:** FLX "Contact, constraints and fracture"; FLX "Operators, problem kinds and checks"; COV "Solid mechanics"; UIX "Studies and results"
**Problem:** Flux has no remote point (a rigid or a distributing coupling from a face to a reference point), no point mass with rotary inertia, no grounded or two-point spring and damper, no six-DOF bushing and no fastener or spot-weld connector. FLX's constraint row lists "multi-point, periodic, cyclic and integral constraints" generically, and UIX's study setup offers only "fixed, force, pressure, preload, temperature, convection". An analyst who models a motor on a bracket, a load through an unmodelled clevis, or a PCB on standoffs uses these primitives in nearly every Ansys or Nastran model; in Crucible they must model the motor and clevis as solids, which is slower, changes the answer at the attachment and breaks modal mass.
**Evidence:** Ansys Mechanical's remote point behaviors: Deformable is "similar to the Mechanical APDL constraint defined by the RBE3 command", Rigid "similar to ... the CERIG command" (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_Geometry_Behavior.html). Ansys's Nastran export maps rigid and deformable remote points to RBE2 and RBE3, bushings to CBUSH and point masses to CONM2 (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_NASTRAN_export_supported_features.html). FLX line 593 and UIX line 591 name none of them.
**Fix:** Add an FLX subsection "Idealizations" under "Contact, constraints and fracture" with one capability row each, phase 1 for the first three and phase 2 for the rest:
- `remote_point(faces, at: CoordSys, behavior: Rigid | Distributing { weight: Uniform | Area | Distance })`, enforced by multipliers on fitted meshes and Nitsche on the octree, returning a point whose six DOFs take forces, moments, displacements, masses and springs. Oracle FLX-O-IDEAL-1: reactions and displacements equal a fitted RBE2/RBE3 reference on 20 cases; a distributing coupling adds no stiffness (eigenvalues of a free plate unchanged within 10⁻⁸).
- `point_mass(at: remote_point or vertex, m, J: Tensor)`; checks of mass properties include it (MEC).
- `spring(a, b, k: Tensor6, c: Tensor6)` and `bushing(...)` with grounded variants.
- Phase 2: `fastener(holes, spec)` from MEC's `fasten` Instance sets, as a beam-plus-distributing-coupling connector with VDI 2230 preload, and `spot_weld(points, d)`.
Each primitive is an Ingot function over `Query` targets, so it stays associative; UIX's study template adds them to the condition list. COV adds a regime variable "coupling region diameter over local wall thickness" so a rigid coupling on a thin wall is `Flag`, since rigid couplings stiffen thin walls.

### R20-21 · Major · Targets: FLX, UIX
**Section:** FLX "Per-region models" (D-FLX-26), "Meshing and adaptivity"
**Problem:** Incumbent users run submodeling: a coarse global model (often shells and beams) drives cut-boundary conditions on a refined local solid. Crucible makes routine submodeling unnecessary through goal-oriented hp-adaptivity, and D-FLX-26 already re-solves a 3D patch from a reduced model. But the tabs neither state the replacement nor expose the patch to users for the cases where it is still the workflow: a shell-modelled frame with a solid weld detail, or a supplier's global loads applied to a local part.
**Evidence:** Ansys Mechanical's submodeling "takes the results of a broader upstream analysis and applies them as boundary conditions to a smaller downstream model" (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_submodeling.html). FLX D-FLX-26 builds that patch internally for error estimation only.
**Fix:** Add one sentence to FLX "Meshing and adaptivity": "Goal-oriented adaptivity refines where a check needs accuracy, so routine submodeling is unnecessary." Add `std::sim::submodel(global: Field, region:, model:)` reusing D-FLX-26's patch with the transfer error in the budget, phase 2, and a UIX study template for it.

### R20-26 · Minor · Targets: UIX, FLX
**Section:** UIX "Studies and results"; FLX "Scope and architecture"
**Problem:** COMSOL's Application Builder turns an expert's model into "a simulation application with a dedicated user interface" for non-experts, and companies buy it for that. In Crucible, any study wrapped as a `#[feature]` already generates its dialog, docs and agent tool schema and stays checked and versioned, which is a stronger form of the same thing. No tab says so.
**Evidence:** https://www.comsol.com/comsol-multiphysics; contract section 5 `Feature` ("metadata that generates its dialog, docs and agent tool schema").
**Fix:** Add one paragraph to UIX "Studies and results" stating that a study published as a feature is a simulation app, with locked inputs, typed ranges and checks. Add an example in which a sizing feature wraps `static_stress` for a sales engineer.

### R20-27 · Minor · Targets: FLX, UIX
**Section:** FLX "Post-processing and display" (`std::sim::report`)
**Problem:** `std::sim::report` builds report data, but no tab renders it as a document an analyst can send or archive (PDF/A, HTML, DOCX). Ansys Mechanical and COMSOL generate reports, and certification and customer reviews consume documents.
**Evidence:** FLX line 840; no report-document writer in ECO's catalog for simulation reports.
**Fix:** Name the output: report data renders through MEC's drawing and document pipeline to PDF/A-2u and HTML, with figures from Snapshots under a pinned `RenderProfile`, phase 2. Oracle: re-rendering a stored report is byte-identical.

### R20-33 · Minor · Targets: UIX, FLX
**Section:** UIX "Field views"
**Problem:** Analysts trust a solve partly by inspecting its discretization. Without a mesh, they will ask where the octree refined, which cells are cut and aggregated, and where shells and beams replaced solids. UIX shows an error overlay but no discretization view.
**Evidence:** UIX "Field views" capability table has no row for the discretization; FLX's `mark_reduction` produces a `Field<Body, ReductionKind>` that is never displayed.
**Fix:** Add a "Discretization" `VisualizationSpec` showing octree cells, cut and aggregated cells, polynomial degree and `ReductionKind` regions, phase 1. A one-line legend states that the model was not meshed by the user.

## Appendix: parity checklist

The checklist below drove the findings. "Covered" means a capability row with a phase exists; the phase is the earliest at which the incumbent workflow works.

| Incumbent capability (source) | Crucible | Phase | Finding |
| --- | --- | --- | --- |
| Linear static, modal, linear buckling of a part (Ansys, Abaqus, Nastran) | Covered (FLX, contract 13.4) | 1 | — |
| Remote points, point masses, springs, bushings, fastener connectors (Ansys, Nastran) | Missing | — | R20-01 |
| 2D, axisymmetric, symmetry, cyclic symmetry (Abaqus, Ansys, COMSOL) | Missing | — | R20-02 |
| Prestressed modal, harmonic, PSD, response spectrum, damping (Ansys, Nastran) | Partial, no owner | 2 to 7 | R20-03 |
| Assembly with bonded and frictionless contact, automatic detection (Abaqus, Ansys) | Fitted only | 2 (fitted), 3 (immersed) | R20-08 |
| Nonlinear materials, large deformation, frictional contact (Abaqus) | Covered | 2 | — |
| Load-case combination and envelopes (Nastran, Ansys) | Missing | — | R20-09 |
| Stress linearization (Ansys) | Missing | — | R20-10 |
| Submodeling (Ansys) | Internal only | — | R20-21 |
| Solver-deck exchange that runs (Nastran, Abaqus, LS-DYNA) | Read and write without execution | 3 | R20-06 |
| Topology and lattice optimization (Ansys, nTop) | Covered; stronger | 1 | — |
| Fatigue, gear and bearing ratings (nCode, KISSsoft) | Covered | 1 to 2 | — |
| Explicit drop and crash (LS-DYNA) | Covered | 3, 5 | — |
| Laminar and natural-convection CFD, conjugate heat transfer (Fluent) | Covered | 3 | — |
| RANS, LES, multiphase (Fluent, STAR-CCM+) | Covered | 4, 5 | — |
| Rotating frames, mixing plane, sliding mesh, fan models (Fluent) | Missing | — | R20-11 |
| Flow adjoint (STAR-CCM+, Fluent) | Unspecified | — | R20-12 |
| GPU CFD throughput (Fluent) | No target | — | R20-07 |
| Full-wave FEM with wave ports and fast sweep (HFSS) | Covered | 4 | — |
| Floquet ports and array domain decomposition (HFSS) | Missing | — | R20-13 |
| 3D partial-inductance RLC extraction (Q3D) | Unspecified | — | R20-14 |
| Weak-form equation modelling (COMSOL) | Covered; typed and differentiable | 0 to 1 | R20-05 |
| Simulation apps (COMSOL Application Builder) | Covered by features; unstated | 1 | R20-26 |
| Charged-particle tracing, molecular flow (COMSOL) | Missing, no limit record | — | R20-20 |
| AI field surrogates (SimAI, Luminary) | Bounded; late | 4 | R20-19 |
| Acausal multi-domain system models (Dymola) | Covered as `Network` | 2 | — |
| Modelica source and MSL (Dymola) | FMU only | 3 (FMU) | R20-15 |
| Hydraulic, pneumatic, thermofluid libraries (Amesim) | Missing | — | R20-16 |
| Schematic, ERC, layout, DRC, routing (Altium, KiCad) | Covered | 3 | — |
| Multi-board systems (Altium) | Covered by construction; unstated | 3 | R20-24 |
| Vendor SPICE models locally (LTspice, PSpice) | Remote External Op only | 3 | R20-17 |
| Ideal-switch converter simulation (PLECS) | Missing | — | R20-25 |
| Allegro and PADS migration (KiCad 10) | Not named | 3 | R20-23 |
| Code-first and AI PCB design (JITX, tscircuit, flux.ai) | Covered; differences unstated | 3 | R20-18 |

### R21-02 · Major · Targets: ING, FLX, COV, KLN, MFG, ELX, AGT, UIX, PLT, MEC, ANV, ECO, CONTRACT
**Section:** Every design section's decisions; "Open questions"; "Contract change requests"; contract lead
**Problem:** The tabs read as the minutes of their own revision. Review finding ids appear as evidence inside running prose, decisions end in "(revised in round N)", "Rejected" clauses name "the round 2 rule", and "Open questions" sections list declined findings rather than open questions. A reader who was not in the review cannot use any of it, and the Adversarial review tab already owns this history.
**Evidence:** Counted before each tab's "Open questions": finding ids such as "(R3-37, R9-40)" appear 112 times in PLT, 62 in FLX, 56 in MFG and AGT, 48 in ELX, 45 in UIX, 43 in KLN, 34 in COV and 26 in ING (482 in all), while ANV, MEC and ECO show that a tab reads well without any. "(revised in round N)" appears 235 times across twelve tabs. Examples: D-ING-7 "*Rejected:* … `Pending` and `ING6401` as node values, the round 2 rule. (revised in round 3)"; D-MEC-26 "*Why:* … the round 1 drafts claimed the formboard twice"; D-FLX-1 "*Rejected:* the round 1 seven-crate split"; MEC "It replaces `crucible:model`"; KLN "`crucible:product`, formerly `crucible:model`". ING's "Open questions" opens "This revision decides all nine round 2 questions" and then lists ten bullets of declined findings; MEC's question 2 and AGT's question 2 are titled "Findings declined…". The contract's lead is a version history.
**Fix:** One mechanical pass, then a rule. (1) Delete every finding id from text above "Open questions"; where the id stood in for a reason, write the reason ("a policy-clamped limit made two organizations cache different results for one key" stays, "(R3-12)" goes). (2) Delete every "(revised in round N)"; the Decisions log and `git log` keep revision history. (3) Delete "the round N rule", "formerly", "replaces" and similar history from decisions and names; a rejected alternative is described by what it is. (4) "Open questions" holds only unresolved questions; move every "Findings declined or applied in part" list to the Adversarial review tab under that tab's code. (5) "Contract change requests" holds only open requests or "None"; accepted ones are recorded in the contract's ruling log. (6) The contract's lead is one sentence: "Binding for every design agent and reviewer; where a tab disagrees with it, the contract wins." Add to `check.py` a rule that fails on `\bR\d{1,2}-\d{2}\b`, "revised in round" and "round \d" outside the Adversarial review and Decisions log tabs.

### R21-10 · Major · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT
**Section:** Running prose and table cells in every tab
**Problem:** Cross-references use decision numbers as nouns: "MEC's Part-level `part.general_tolerance(spec)` record (D-MEC-35)", "the default distribution (D-MEC-28)", "standing releases (D-AGT-33)". A reader cannot tell what D-KLN-41 is without leaving the page, and a sentence carrying three such ids reads as a lookup table. Decision numbers are stable ids for logs and reviews, not prose.
**Evidence:** Decision ids before "Open questions", per tab: AGT 101, MFG 95, ECO 90, FLX 87, KLN 86, PLT 83, ELX 77, COV 76, MEC 75, ANV 58, UIX 58, ING 51, about 940 in all. Example from AGT: "`api` enforces KLN's one two-person list (D-KLN-41), which includes this tab's items"; from KLN's interface row: "`release_data` and standing releases (D-AGT-30, D-AGT-33)".
**Fix:** Refer to facts by name and link the owning section: "KLN's two-person list ([KLN, Change control](05-kiln-repo-plm.md#change-control-signatures-and-compliance))". Keep a decision id only where the decision itself is the subject ("D-MEC-33 is merged into …") and in the Decisions log. Add a `check.py` warning for more than one decision id in a sentence outside decision blocks.

### R21-11 · Major · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, CONTRACT
**Section:** "Interfaces with other subsystems" in every tab; contract section 11, item 5
**Problem:** The Interfaces sections use at least six formats, and every interface is written four times (A provides it to B, A requires it from B, and both again from B's side), which is why the plan needs `extract.py` to reconcile rows. A reader comparing two tabs finds the same edge described in different words and cannot tell which wording is binding.
**Evidence:** Formats: ING, FLX, COV, AGT and UIX use "provides" (To · Provides · Types) plus "requires" (From · Requirement); ANV uses "Anvil provides" with columns To · What · Types; MEC one table Subsystem · MEC consumes · MEC provides; ECO Tab · ECO requires · ECO provides; MFG "What MFG consumes" with From · Canonical name or type · Used for; PLT "Provided by PLT" and "Consumed by PLT". The repository's working notes list "make each row of 'Interfaces with other subsystems' match the other tab's row" as a standing consistency task.
**Fix:** Each tab writes only what it provides, in one format: `| To | What | Types | Phase |`. `extract.py` generates the "requires" view per tab and one interface matrix (twelve by twelve, linking cells to rows) for the Overview. Change contract 11 item 5 to: "`## Interfaces with other subsystems`: one table of what this tab provides (To · What · Types · Phase); what it requires is generated from the other tabs." A requirement nobody provides then shows up as an empty cell instead of a mismatch hunt.

### R21-12 · Major · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, CONTRACT
**Section:** Inline citations and "Sources" in every tab
**Problem:** The tabs use four inline citation systems, so a reader re-learns how to follow a reference in each tab, and in two of them the markers crowd the prose. COV and AGT tag almost every sentence with `[Sn]`, ELX with `[n]`, ANV and MFG use readable keys, and ING, KLN, UIX and PLT name sources in prose with no marker at all.
**Evidence:** `[Sn]` markers: COV 384, AGT 239; bare numeric `[n]`: ELX 177; bracketed keys such as `[Parasolid convergent modeling]` and `[Gardeyn et al. 2025]` in ANV, MEC and MFG; none in ING, KLN, UIX and PLT. One AGT table row carries `[S2][S4][S8]`. ELX's Sources opens "[65] to [69] were opened in round 2".
**Fix:** One style in contract section 11: readable keys `[Author Year]` or `[Organization short title]`, defined in Sources as "key · title · URL · date opened", and at most one marker per sentence. Convert COV, AGT and ELX mechanically from their source lists; add markers in ING, KLN, UIX and PLT where a sentence states a sourced fact. Remove round history from Sources headers.

### R21-26 · Minor · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, CONTRACT
**Section:** Capability tables at the end of each design section
**Problem:** Capability tables are the build contract, but in reading order they arrive as a dense block after every section, and many cells add nothing: "Failure: —" and "Not expressible" stand where the reader expects a typed failure. The published doc gives them the same weight as explanation.
**Evidence:** ING "Purity | … | Not expressible"; MEC "Typed failures and fixes | `FeatureError { kind, why, fix, at }` | —"; AGT "Priority classes | … | — ".
**Fix:** Replace "—" with "None: cannot fail" or the actual failure, and "Not expressible" with "None: the language cannot express a violation". In the published doc, render capability tables as a visually distinct, collapsible "Build contract" block under each section, so a reader can follow the prose without the tables breaking it.

### R21-28 · Minor · Targets: UIX, MFG
**Section:** UIX "Workspace and information architecture"; MFG "Scope, layering and core types"
**Problem:** Sections open with decisions before any description, so the reader is asked to accept a rule about something not yet shown. UIX's first sentence is D-UIX-1; MFG's ownership table is followed by three consecutive decisions (D-MFG-1, D-MFG-2, D-MFG-30) before the first explanatory sentence.
**Evidence:** UIX line 7: "**Decision D-UIX-1:** The UI holds no product state…", before the "Places" and workspace tables. MFG: D-MFG-1, D-MFG-2 and D-MFG-30 appear back to back, then "Machines, fixtures, molds, nests and panels are Assemblies…".
**Fix:** UIX: open with two sentences describing what a user sees (places, then one workspace with presets), put the "Places" and "The workspace" tables first, and move D-UIX-1 after them. MFG: open with the paragraph that says what manufacturing objects are in Crucible ("Machines, fixtures, molds, nests and panels are Assemblies…"), then the `Toolpath` record, then the three decisions as the rules that follow.

## Claims the reviewers verified

Drop the `[unverified]` marker on these and cite the URL in Sources.

None in this review.

## Unverified claims in your tab

Verify each with WebFetch on a primary source and drop the marker, correct it, or cut the claim if nothing supports it. Line numbers are at tag `round-3`.

None.

## Your open questions

Close each: decide it (the reviewers propose answers above), move it to a contract change request, or keep it with the reason it cannot be decided yet.

Round 2's nine open questions are closed by D-UIX-1, D-UIX-3, D-UIX-9 (two questions), D-UIX-13, D-UIX-20, D-UIX-31, D-UIX-32 and D-UIX-33. None remains open.

**Findings applied in part or declined.**

- R12-15 and R11-05, applied with one path. Native clients use the system browser session for every relying party, Crucible's cloud included, so no approval runs in the app's process; PLT's `Authenticator` only opens that session (D-PLT-41). One path is simpler, and an in-app webview would share the app's process.
- R12-02 and R12-03, applied in contract 13.2's form. No staffing figures remain, every oracle names a runner class and a held-out split, and Phasing lists UIX's phase 1 work.
- R12-33, item 7, applied as UIX's target at each gate (D-UIX-32), not a contract gate. Contract 13.1 lets a UI slip move only UIX's target (R12-09).
- R8-18 and R12-28, applied in this tab and in contract 5 and 13.3 (CCR-UIX-7, CCR-UIX-8).
- R4-12 and R4-06 (round 2): toolpath playback, the NC panel and the setup-sheet preview stay in phase 2 with MFG's CAM. The cost panel moved to phase 1.
- R3-41 (round 2): the tab keeps ten design sections, so each capability table covers one coherent area.

## Known items

- Founder direction (CLAUDE.md): agents author and people steer, review and present. Rebuild the tab around viewing, review and presentation output at the polish level CLAUDE.md names; hand-modelling ergonomics shrink to steering (point, mark up, ask).
- Study Anatomy (github.com/wheresryan22/anatomy, MIT: `SKILL.md`, `references/craft.md`) and carry its craft rules into the renderer and presentation specs: every shown number comes from the model that drives the motion; a geometry audit (no interpenetration, every part mounted, depth-ordered); shaded technical-illustration styles; effects layered in the same camera; calm motion that stops under reduced motion; self-checking renders.
- Read `docs/revision/digest.md`: adopt the permissive libraries that serve your tab, name copyleft tools only as oracles, and use the clean-room insight protocol of contract 7.7 for incumbent behaviour.
- Add one sentence under each drawn diagram that tells the reader how to read it (`diagrams/10-ui-frame-graph.jsx`, `diagrams/10-ui-drag-preview.jsx`).
