# Revision packet: UI and interaction (UIX)

42 review findings target this tab: Critical 3, Major 29, Minor 10.

## 1. Round 1 edits (from contract v3 section 14)

`Fidelity` and `ResultStatus` names; `DisplayPackage` and `ViewState` as core types; GP numbering.

## 2. Round 2 contract changes that affect this tab (contract v4)

Electronics preset (schematic and layout) and the public `crucible:ui/canvas2d` world with an engine-side interactive edit lane; the single server-generated approval page with WebAuthn and no phone approvals; the performance rows and render-scale policy of section 13.3 (G1 100,000 Instances, G2 20,000, G3 1,000 distinct Parts); the drag-preview rule with `Proxy` and `Stale`; phase 1 forward renderer on every tier; PLT owns the browser memory table; Altium-like and KiCad-like presets; capability tables per section.

## 3. Review findings targeting this tab

Apply each finding unless you have a sound reason not to; record any finding you decline, with the reason, in Open questions or Contract change requests. Findings with several targets are shared: change only what this tab owns and state the consequence in one line where another tab owns the rest.

### R4-04 · Critical · Targets: UIX, ELX
**Section:** UIX Modes; Extending the interface; Capability catalog; Migration from other CAD tools; ELX Interactive routing; What this tab requires (UIX row).
**Problem:** UIX hosts electronics only as Wasm panels that return element trees, may not draw pixels and get 2 ms of CPU per frame, yet ELX requires schematic and layout editors with push-and-shove routing at 16 ms per mouse move. A layered board canvas with net highlighting, ratsnest, DRC markers and a live router head cannot be built from stacks, grids and overlay glyphs inside 2 ms, and UIX has no Electronics mode, no electronics role and no Altium or KiCad key presets. As written, the board designer's daily tools have no owner.
**Evidence:** UIX: "Domain views from other tabs, such as the electronics board view …, use the same extension points as any third-party package."; panels "never draw pixels or ship shaders"; "Each panel gets 2 ms of CPU per frame."; modes are Design, Simulate, Manufacture and Review; presets "for SOLIDWORKS, Fusion, Onshape and Blender users". ELX: "Targets: under 16 ms per mouse-move update with up to 50 shoved items"; ELX requires "Schematic and layout editors writing `Schematic`, `Layout` and source edits; constraint manager view; waveform, Smith chart, eye diagram and timeline viewers".
**Fix:** UIX adds an Electronics mode (Schematic, Layout) and a public `crucible:ui/canvas2d` world any package may use, so principle 1 holds: a component submits retained 2D primitive buffers (lines, arcs, polygons, text, with layer ids and net ids) that the wgpu renderer draws with layer visibility, opacity, high-contrast and net-highlight modes, and hit-testing uses the same buffers. Tools that compute per pointer move (the router, placement drag with live DRC) run in the engine process on an interactive edit lane like Kiln's drag lane and stream head geometry each frame through `api`; the 2 ms budget applies to panel UI logic only. Specify the schematic canvas (symbols, wires, junctions, labels, sheet frames, cross-references), the layout canvas (layer stack, ratsnest, DRC markers, length-tuning meters) and the constraint-manager grid, with budgets equal to ELX's targets. Add Altium-like and KiCad-like presets and an electronics first-run role. Phase 3, with a UIX oracle that replays ELX's recorded routing sessions at 16 ms or less per update.

### R5-04 · Critical · Targets: AGT, UIX, KLN, CONTRACT
**Section:** AGT Irreversible real-world actions (D-AGT-20), MCP profile; UIX Approving and rejecting, Approvals, Platforms and devices
**Problem:** D-AGT-20 claims "the approval never passes through the agent's channel", but the approval URL does: the client presents it, and without elicitation support it returns to the model in `context`. Because any "approver with the required authority" may approve, a hijacked agent, compromised host or insider can prepare a plan and forward its genuine Crucible URL to a busy approver. File names in `Effect::SendFiles` come from the plan's author, so the human approves a name while the digest names other content. There are three approval surfaces (UIX's "secure dialog", AGT's approval page, the planned MCP Apps viewer inside the host), and phones may approve although the contract makes them viewers.
**Evidence:** MCP: "URL mode elicitation returns a URL that an attacker can use to send to a victim. The MCP Server **MUST** verify the identity of the user who opens the URL before accepting information." (https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation). AGT: "A client that does not support elicitation receives `act.approval_pending` with the approval URL in `context`"; "Approval requests reach the delegating human, or an approver with the required authority". UIX: "explicit human confirmation through the platform's secure dialog"; "The phone app shows saved views, comments, approvals". Contract §9: "phones as viewers".
**Fix:**
1. Make an approval request a server record assigned to named approvers by Cedar policy, delivered only to their Crucible inbox. Push notifications carry no content. Anyone else who opens the URL sees "not assigned to you".
2. Never return the approval URL to the model; `act.approval_pending` carries only a request id.
3. The server generates the approval page: file names from item number, revision, format and release tag; a server-rendered thumbnail; a content summary (Items, labels, bytes); the recipient's verification and screening dates; a diff against the last approved plan of the same class to the same recipient; and the session `purpose`, marked as agent text.
4. Require phishing-resistant WebAuthn user verification. R4 classes can be approved on desktops and tablets only.
5. Allow at most 3 pending requests per session. A denial blocks re-preparing a plan to the same recipients for 24 h and offers "report as suspicious", which freezes the session.
6. Reject invisible characters, Unicode tag characters (U+E0000 to U+E007F), bidirectional controls and zero-width characters in free-text payloads (`notify_external`, RFQ notes).
7. Make the MCP Apps viewer read-only, and make UIX's secure dialog this same page.
8. Extend O-AGT-9: approvals from a forwarded URL by a non-assignee, plan substitution, hidden characters and approval spam are all refused.

### R6-02 · Critical · Targets: CONTRACT, ANV, FLX, ING, KLN, UIX, MFG, ECO, AGT, PLT, ELX
**Section:** Phasing (all tabs); CONTRACT §13 Roadmap and golden products
**Problem:** Phase 1 carries work that neither GP1 (one machined bracket) nor GP2 (one printed lattice bracket) needs, and much of it sits on long chains: cloud services, live collaboration, CAM, a public registry, a second Ingot executor and a second renderer path. Without named deferrals each team builds its full phase 1 list and the gate waits for the slowest team.
**Evidence:** GP1 and GP2 are single Parts with no assembly, no multi-user editing and no third-party package (CONTRACT §13). Phase 1 lists still include "cloud SaaS single region" and "Loro live documents, presence and offline rejoin" (KLN Phasing), "2.5D and 3-axis milling, adaptive clearing … posts … slicing" (MFG Phasing), "public registry with trusted publishing, provenance, TUF and transparency log" (ECO Phasing), "Wasm code generator with Perceus" (ING Phasing), "browser on G2 and G3" (UIX Phasing), seven agent roles and Bayesian exploration (AGT Phasing), and "TUF-signed delta updates for every desktop format" (PLT Phasing).
**Fix:** Move the following to phase 2 or to 1.x release trains after the gate; contracts and oracles stay as written.
1. ING: Wasm code generator, Perceus and the state-machine transform; the reference interpreter is the only executor in phase 1 (R6-25).
2. UIX: cluster-DAG streaming, visibility buffer, compute rasterization, k-buffer, variant grid, presence and follow mode; phase 1 uses one forward renderer on every tier (R6-24) and the code-panel scope of R6-23.
3. KLN: cloud SaaS and FoundationDB, live CRDT documents, encryption domains, transparency logs, hardware runner; phase 1 ships a single-node team server (SQLite or PostgreSQL) with branches, merge, Proposals, Cedar policies and a signed append-only audit log.
4. MFG: CAM, posts, stock simulation, slicing and nesting; phase 1 keeps DfAM checks, 3MF production output and cost (R6-05).
5. ECO: public registry and trusted publishing; phase 1 ships a signed first-party package index, STEP AP242 (geometry, structure, semantic PMI write), AP203 and AP214 read, and 3MF with beam lattice.
6. AGT: Bayesian exploration, hosted crew, quarantined extraction, TypeScript SDK; phase 1 ships `api` over MCP, Rust and Python SDKs, Propose with CI report, risk classes and two roles (detail designer, verifier).
7. FLX: guaranteed equilibrated estimators on cut cells (FLX open question 11), GPU sign-off paths, CubeCL; phase 1 ships one immersed discretization (shifted boundary interactive, CutFEM sign-off), DWR, p-multigrid with an AMG coarse level, steady adjoints and density topology optimization.
8. ANV: SubD, certified SSI for general NURBS–NURBS pairs, free-form offsets, healing beyond the CAx-IF corpus; phase 1 certifies SSI among planes, quadrics, tori, extrusion and revolution surfaces, and NURBS–analytic pairs.
9. PLT: TUF delta updates (full signed packages suffice), the MSI wrapper, Flatpak, AppImage, reproducible builds beyond Linux and wasm32, telemetry, enterprise policy; phase 1 ships MSIX, a notarized DMG, deb and rpm.
10. ELX: no team before the phase 1 gate beyond a two-person circuit-simulation research track.

### R1-16 · Major · Targets: FLX, ANV, UIX
**Section:** FLX OQ4; "Fidelity modes" (latency row and "Interactive updates within 1 s come from ...").
**Problem:** The 1 s target lists only solver-side savings, but a dimension drag changes the Body, so Anvil rebuild, certified cell classification, closest-point queries for every shifted-boundary quadrature point, geometry-factor setup, the solve, the estimate and display sampling all rerun, and none has a budget. The reduced-model shortcut for drags does not apply to geometric parameters on an immersed discretization, because cell classification changes with the geometry.
**Evidence:** FLX: "Interactive updates within 1 s come from cached assembly structure, a reused multigrid hierarchy, `f32` GPU kernels, and coarse-first streaming"; "When a drag moves only parameters inside a valid reduced-model box, the reduced model answers instead."
**Fix:** Publish per-stage budgets (targets: Anvil rebuild 150 ms, classification and distance queries 200 ms, setup 100 ms, solve 350 ms, estimate 100 ms, display 100 ms), measured on GP1, GP2 and GP5 in phase 0, with incremental classification for local edits. For geometric drags, either build reduced models on a fixed background discretization with geometry entering through a morphing map from `anvil::shape_velocity`, or state that geometric drags return `Proxy` until the full update arrives.

### R2-09 · Major · Targets: ANV, KLN, PLT, UIX, MEC
**Section:** ANV Performance targets, Fidelity levels; MEC Performance budget; UIX Coarse-first preview pipeline; ING Previews, drags and incomplete code; PLT Budgets
**Problem:** The 2 s exact rebuild of a 200-feature part after an early edit and the 100 ms coarse preview "with dependent features updated" are not supported by any mechanism in the drafts. After an early edit every downstream input changes, so MEC's read sets and tool-body caching save nothing and drag specialization's forward slice is the whole chain; 1.2 s for about 200 certified operations leaves about 6 ms each for certified SSI and marching, `check_body`, relabeling and Merkle hashing, while Anvil expects certified SSI at up to twice OCCT's time. Coarser preview tolerances do not reduce the number of B-rep operations, and Anvil defines no geometry fidelity between `Preview` and certified results.
**Evidence:** ANV "Anvil share ≤ 1.2 s of the 2 s budget, with Kiln backdating unchanged features"; MEC "Kiln re-runs only features whose inputs changed"; UIX coarse stage "dependent features updated | ≤ 100 ms (contract)"; ING drag specialization "computes the forward slice of that literal"; ANV SSI target "at most 2× OCCT time on transversal cases"; MEC "drawing update after an edit to a 200-feature part in under 1 s", shorter than the rebuild it depends on.
**Fix:** (1) Define Anvil `Interactive` fidelity: the same Portable code with floating-point topology decisions validated after the fact (`check_body` plus Krawczyk verification of traced points), cacheable, never consumed by SignOff checks or releases; SignOff recertifies in the background. (2) State the 2 s target for `Interactive` and add a SignOff target (for example 10 s). (3) Define preview scope: within 100 ms, the dragged feature and as many downstream features as fit, in program order; the rest show stale geometry with a visible boundary. (4) Publish the 200-feature benchmark's operation mix and per-operation budgets, and run a phase 0 spike measuring certified SSI and Boolean cost on ABC face pairs before freezing the targets. (5) Restate the drawing target as "under 1 s after the rebuild completes".

### R2-20 · Major · Targets: ANV, MEC, UIX
**Section:** ANV Direct edits and defeaturing (`move_faces`); MEC Direct edits (D-MEC-9); UIX Push-pull
**Problem:** MEC promises that `anvil::move_faces` "regrows or removes blends", but Anvil's contract only re-intersects neighbors. Moving a face next to fillets, which is nearly every face of a real part, then fails or leaves blends with the wrong radius and broken tangency. Imported blends must first be recognized, which is phase 2, while UIX push-pull plans `move_faces` in phase 1.
**Evidence:** MEC D-MEC-9 "`anvil::move_faces` then re-intersects neighbors and regrows or removes blends"; ANV `move_faces` "Faces and a motion ...; neighbors re-intersected", phase 2; UIX phase 1 includes push-pull, which on non-cap faces "plans `offset_faces` or `move_faces`".
**Fix:** Specify blend handling in ANV's `move_faces`, `offset_faces`, `replace_faces` and `draft`: blends adjacent to moved faces (Anvil-made blends carry supports, radius and section; imported ones come from `recognize_aspects`) are removed, the edit is applied, and the blends are rebuilt with the same parameters and EntityIds (`Modified`), or the operation fails with `BlendRegrowFailed { blend, reason }` and the fixes "remove blend" and "reduce radius". Align phases: phase 1 push-pull on non-cap faces offers only `offset_faces` with this handling; `move_faces` arrives with ANV phase 2.

### R3-09 · Major · Targets: CONTRACT, FLX, ING, AGT, UIX
**Section:** CONTRACT 6 (canonical example); FLX "Honest reporting of singular quantities", "Solve plans"; ING worked example 3; AGT "Text descriptions"; UIX "Running and exploring results"
**Problem:** The canonical check takes a peak stress next to a clamped face, and linear elasticity makes stress singular where a clamped face meets a free face. By Flux's own rule such a check can only report `Undecided`, yet AGT and UIX show it passing with margins. ING example 3 claims a `Guaranteed` ± 1.5 MPa bound on a peak stress, which no FLX estimator provides. The first example every author copies teaches a check that cannot pass.
**Evidence:** Contract 6: `peak_stress(p, load, fixed: base.face(role: start_cap))`. FLX: "Point loads, point supports, re-entrant edges and corners ... make exact stresses infinite ... A check on a flagged peak returns `Undecided`"; guaranteed bounds hold "For energy norms" on fitted simplicial meshes, and immersed results are `Estimated`. AGT: "worst margin `peak_stress` 31%"; UIX: "peak_stress < 0.6 × yield: margin 18% ± 4%". Reasoning: where a clamped face meets a free face at a right angle, the linear-elastic stress field is singular, so the peak grows under refinement and FLX's own detector ("a local estimate that fails to decrease under refinement") flags it. Dual-weighted residual estimation needs a differentiable goal, and a maximum is not differentiable.
**Fix:** Rewrite the canonical check over a region that excludes the clamp: `let stress = study.von_mises.max(over: p.body.away_from(base.face(role: start_cap), 2 * thickness))`, then `p.require(stress < 0.6 * p.material.yield_strength(at: 20degC))` with default evidence. FLX defines `peak_stress` as a regularized goal (a p-norm or local average over a stated region, with the regularization error in the budget) and states that a raw maximum is never a goal. ING example 3's sign-off row becomes `Estimated`. AGT and UIX reuse the new check.

### R3-35 · Major · Targets: UIX, AGT, KLN
**Section:** UIX "Localization and units", Interfaces (`render_snapshot`); AGT "Rendered views and Field overlays" (D-AGT-9)
**Problem:** Snapshots are content-addressed results of `render_snapshot(ViewState, size)` and serve as Proposal evidence and benchmark grading. Their legends and labels depend on locale ("4,5 mm in German"), theme, display units, bundled fonts and the renderer version, and none of these is in `ViewState` or the call. Two agents' snapshots of one state can differ, and a cached snapshot can show another user's locale or an older renderer.
**Evidence:** UIX: `render_snapshot(ViewState, size) -> CasRef<Image>`, "deterministic per platform class on the CPU path"; "Display follows the locale (4,5 mm in German)". Contract 5: `ViewState` holds "camera, visibility, sections and Field displays". D-AGT-9: snapshots "must be reproducible".
**Fix:** Add a `RenderProfile` (locale, theme, display units, font package pins, renderer behavior version) to the snapshot key. Proposals and benchmarks use one fixed review profile (`en`, SI with millimetres, light theme), so evidence is reproducible.

### R3-36 · Major · Targets: CONTRACT, ING, UIX, KLN, MEC, ELX
**Section:** CONTRACT 11 (skeleton); ING "Capability catalog"; UIX "Capability catalog"; KLN capability tables; MEC "Sketching contract", "Assembly oracles and phases", "Tolerancing contract", "Drawing and MBD oracles"; ELX "Layout capability catalog"
**Problem:** Section 11 demands "for every capability: what it does, its contract, failure behavior, oracle and phase" but gives that information no place. The tabs invented four layouts: one catalog section (ING, UIX), a table per section (KLN), contract and oracle subsections scattered through the design (MEC, ELX), or none. Phases and oracles are then stated two or three times.
**Evidence:** UIX "Capability catalog" (1,326 words) beside "Oracles" (1,027); KLN has eight capability tables plus "Oracles"; MEC has four contract or oracle subsections inside design sections.
**Fix:** Amend section 11: each design section ends with one table (Capability · Contract · Failure · Oracle id · Phase); `## Oracles` lists each oracle once (id · verifies · pass criterion) with no phase column; `## Phasing` lists gate contributions only. Separate catalog sections go.

### R3-41 · Major · Targets: UIX
**Section:** UIX "Capability catalog", "Oracles", "Renderer", "State of the art", "Design system and visual language", "Interface principles", "Platforms and devices", "Platform notes"
**Problem:** At 25,578 words, UIX is 7,600 over the cap. It has 19 design sections, a capability catalog that duplicates Oracles and Phasing, and two platform sections.
**Evidence:** "Capability catalog" (1,326 words) plus "Oracles" (1,027); "Renderer" 3,820; "Color tokens" 526; "Interface principles" (306) restates contract 3 and 10; "Platforms and devices" (550) beside "Platform notes" (496).
**Fix:** Merge catalog, Oracles and Phasing per R3-36, which saves about 1,500 words. Cut Renderer to 2,400 and move token values to a token file referenced by name. Delete "Interface principles" and merge the two platform sections. Regroup the 19 sections into eight: workspace; toolkit; renderer and Field views; manipulation and code; review, agents and collaboration; domain panels; input, accessibility and localization; design system, performance and extension. Result: about 17,900 words.

### R4-06 · Major · Targets: MFG, UIX
**Section:** MFG Tool libraries, Controllers and post-processors, What MFG provides; UIX Toolpath preview and playback, Modes.
**Problem:** Neither tab produces a setup sheet, the document every machinist runs from: tools with holder, stick-out, gauge length, T, H and D numbers and pocket; stock size and material; work offset location and probing instructions; clamping views; program names and cycle times. UIX shows toolpaths but no NC text, although MFG already keeps a `BlockMap` from blocks to toolpath points. A reference shop cannot run GP1 without these.
**Evidence:** 07-manufacturing.md contains no "setup sheet", "tool table" or "G54". UIX toolpath table covers toolpaths, tool and holder, stock, collisions and additive only. MFG: "Each `BlockMap` entry links a posted block to its workingstep, path parameter and content hash."
**Fix:** MFG adds `setup_sheet(program, template) -> Drawing` in phase 1, an Ingot drawing built from the `Program`, tool Assemblies and setup, so it diffs and releases with the program; templates are packages. Content: setup views with the WCS triad and dimensions from the work offset to datum features, fixture and clamp positions, stock definition, tool table (T, pocket, H, D, holder, stick-out, gauge length, flute length, expected life), workingstep list with tool, cycle time and Z extremes, and first-run notes (tool-length verification, reduced override) from MFG's safety text. UIX Manufacture mode adds an NC code panel with two-way highlighting through `BlockMap` (block, toolpath point, workingstep, design feature) and a setup-sheet preview. Oracle: every tool in the program appears once in the table, with gauge length equal to the tool Assembly's analytic stack-up.

### R4-12 · Major · Targets: KLN, MEC, MFG, UIX, AGT
**Section:** Phasing in each tab.
**Problem:** The GP1 chain is phased inconsistently. MEC title blocks read item and revision from `repo` and drawings carry BOM tables in phase 1, MFG rolls up BOM cost and releases programs in phase 1, and UIX's phase-1 gate approves GP1 through the UI; but KLN delivers Items, revisions and BOM views in phase 2, UIX delivers toolpath playback and the cost panel in phase 2, chamfer and deburr toolpaths (needed for edge breaks on any machined part) are phase 2, and AGT's CAM programmer role is phase 2 while MFG ships agent-proposed toolpaths in phase 1.
**Evidence:** KLN phasing: "2 Mechanical depth | … | … Items, revisions, change orders …; EBOM, MBOM and SBOM views". MEC: "Sheets and title blocks | … read item, revision and approvals from `repo` | 1"; "Tables | BOM … | 1 (BOM, holes), 2". MFG: "BOM roll-up | `repo` BOM query … | 1"; "Deburr and chamfer | … | 2"; agent-proposed toolpaths "Phase 1". UIX: "Toolpath playback | … | 2"; "Cost panel | … | 2". AGT role catalog: CAM programmer, phase 2.
**Fix:** KLN phase 1 adds a minimal lifecycle: item numbers, revision labels on release tags, `InWork` and `Released` states and the EBOM view; full change orders, effectivity and MBOM stay in phase 2. UIX moves toolpath playback, the NC view (R4-06) and the cost panel to phase 1. MFG moves 2D chamfer and edge-break toolpaths to phase 1. AGT moves the CAM programmer role to phase 1, or MFG moves agent proposals to phase 2; state the same choice in both tabs. KLN either delivers the interchangeability check with change orders in phase 2 or states that phase-2 change orders take a human verdict.

### R4-16 · Major · Targets: MEC, KLN, UIX
**Section:** MEC Drawings; KLN Revisions and lifecycle states; UIX Drawings and model-based definition.
**Problem:** Drawings get a revision table but no revision markers. Practitioners flag each changed item with a revision symbol or cloud and list the change by zone; Crucible has the semantic diff to generate them, but no tab specifies it. Tabulated drawings, the usual way to document dash-number families, are also missing.
**Evidence:** MEC: "Tables | … revisions (from `repo` releases and change orders) …"; no tab specifies revision clouds, revision symbols or tabulated drawings. ASME lists Y14.35-2025 as the current edition of the revision standard (https://www.asme.org/codes-standards/find-codes-standards/y14-35-revision-engineering-drawings-associated-documents).
**Fix:** MEC adds `revision_markers(drawing, from: Release, to: Release, style: Delta | Cloud)`: the annotation and view diff between two releases places a symbol beside each changed item, fills the revision block with change-order number, description and zone, and regenerates at release. Markers and revision text are late-bound release fields excluded from the definition digest (R4-17). Drafting packages carry Y14.35-2025 rules and the ISO practice. Add tabulated drawings driven by `family` rows. Released drawings are also written as PDF/A [unverified part] for archive. Oracle: a release changing two dimensions yields exactly two markers and one revision row.

### R4-22 · Major · Targets: ELX, UIX
**Section:** ELX Writing a circuit (schematic module and editor behavior); Electrical rule checks.
**Problem:** The stored drawing models pin-to-pin wires only, so real schematics cannot be stored: wires meeting wires at junctions, power symbols, no-connect flags, bus entries, sheet symbols. Nothing stops the drawing from lying: a code edit can leave a drawn wire between pins that are no longer connected, and only removed pins are caught. Labels are drawing items, although in every schematic tool a label is connectivity, and net ties (an intended short at one point) have no representation although IPC-2581C carries intended net shorts.
**Evidence:** ELX: `wire w_3c1 [u1.pin("SW"), l1.a] path [(78mm, 40mm)]`; "A wire end that touches no pin is impossible: the editor snaps or refuses."; "Annotations that point at removed pins fail with `SchematicError::StaleAnnotation`"; ELX contains no schematic junction or "net tie". MFG cites IPC-2581C support for "intended net shorts".
**Fix:** The `Schematic` module stores drawn topology: segments whose ends lie on pins, labels, power symbols, sheet pins or other segments (explicit junctions), plus no-connect flags and bus entries. A blocking check `schematic_matches_circuit` maps each drawn connected group to exactly one net; a group spanning two nets is `SchematicError::DrawnShort`, drawn in the danger style and failing release. Label text equals the net name: editing it renames the net in source, and placing a label with an existing net's name writes a `connect`. Net ties are explicit `tie(net_a, net_b, at: footprint)` elements that ERC, DRC, netlists and IPC-2581 export treat as intended shorts; no-connect flags write `no_connect(pin)`. Oracle: the 10⁵-edit property test also asserts that no drawn group spans two nets after any code edit.

### R4-31 · Major · Targets: UIX, KLN
**Section:** UIX Information architecture (Places).
**Problem:** Every place is a design workspace or a project view. Purchasing, quality, manufacturing engineering, suppliers and the shop floor work from items, not branches: an item's released revisions, documents, where-used, BOM, change orders, effectivity, compliance and approved sources. Without an item page, PLM users keep their old system.
**Evidence:** UIX Places: Home, Project dashboard, Design repository overview, Workspace; UIX contains no "where-used", "item page" or "purchasing". KLN specifies where-used, effectivity and compliance records that no UIX surface displays.
**Fix:** Add an Item place in phase 2, with KLN Items: header (number, name, kind, state, make or buy), revisions with states and effectivity, released documents for download (PDF drawing, STEP, NC programs) with digests, multi-level BOM and where-used filtered by access as KLN specifies, change requests and orders, compliance verdicts, approved manufacturers with supplier snapshots, and cost. It works on Tier 2 devices and for supplier principals within their package scope, and links into the workspace at the release Change.

### R5-16 · Major · Targets: UIX, PLT, KLN
**Section:** UIX Comments anchored to geometry, Notifications, Crash and error reporting; PLT Crash handling; KLN Export control
**Problem:** Label enforcement stops at the API, but labelled content leaves through channels that never consult labels: comment snapshots "for email and mobile", email digests, push notifications relayed by OS vendors, OS cloud backup or sync of the local CAS and journal, clipboard-history sync, crash minidumps whose stack memory may hold design data, and reproduction bundles containing the whole branch. Each sends content to a third party that holds the plaintext, which defeats ITAR's end-to-end condition. UIX's "Values and content are never recorded" also contradicts PLT's own statement about stack memory.
**Evidence:** UIX: `snapshot` is a "rendered still frame, for email and mobile"; "email digests are optional"; a reproduction bundle holds "branch, `api` call log and `ViewState`". PLT: "Stack memory can hold fragments of design data". 22 CFR 120.54(b)(1) requires that "the means of decryption are not provided to any third party" (https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120/subpart-C/section-120.54).
**Fix:** Add one label-aware egress rule to PLT and UIX. For labels above `internal`:
- Notifications and emails carry only ids and generic text, never snapshots or names; push payloads carry no content.
- Crash reports upload only the signature and module list.
- Reproduction bundles go only to the organization's own server.
- The CAS, journal and caches refuse to live in a cloud-synced folder and are marked excluded from OS backup.
- Copies of labelled content are excluded from clipboard history and cloud clipboard where the OS allows, and a policy can forbid copying.

Correct UIX's crash-reporting text to match PLT.

### R5-17 · Major · Targets: AGT, ECO, UIX
**Section:** AGT Rendered views and Field overlays; Untrusted content is data (instruction-capable content)
**Problem:** Images can carry instructions, and imported geometry or textures can depict text: embossed letters, or texture maps in glTF, 3MF or USD files. If label propagation applies, every render of an assembly with any supplier part is untrusted and taints every session that uses vision, which destroys utility and invites approval fatigue. If it does not apply, text-shaped geometry is an unmonitored injection channel. The draft does not say which.
**Evidence:** AGT: "Only free text and images can carry instructions"; "a render of a model containing an untrusted STEP name stays untrusted"; "The renderer never draws external strings: marks are numbers, and labels come from typed data", which covers labels but not geometry or textures.
**Fix:** A render is untrusted and instruction-capable when the geometry or appearance of any visible Body derives from an untrusted Asset. Agent renders default to `appearance: neutral`, which drops imported textures. Privileged contexts query untrusted renders only through a quarantined vision call with templated questions and typed answers: `inspect.ask_render { template, marks }` returns mark ids, booleans or counts. The scene graph, measurements and `inspect.describe` stay non-tainting. The injection suite adds embossed-text geometry and textured imports.

### R5-27 · Major · Targets: KLN, AGT, UIX
**Section:** KLN Tamper-evident audit (D-KLN-30), Electronic signatures; AGT Audit, Provenance of agent changes; UIX Approvals, Presence
**Problem:** Transparency logs are append-only and never pruned without a retention policy; signature records carry printed names; audit records, transcripts and API logs carry principal identities for seven years by default; and the UI records which tabs each approver viewed. None of this personal data has an erasure or minimization design. Per-person activity records (presence, follow mode, viewed tabs) are monitoring that needs works-council agreement in Germany, which blocks deployment for EU customers until it is configurable.
**Evidence:** KLN: "Logs are never pruned without a retention policy". AGT: "a default of seven years for repositories that contain releases [unverified ...]". UIX: "The UI records which tabs were viewed as part of the approval". GDPR Art. 17(3)(b) and (e) permit retention for legal obligations and legal claims (https://gdpr-info.eu/art-17-gdpr/). German Works Constitution Act §87(1) item 6 gives co-determination over "the introduction and use of technical devices designed to monitor the behaviour or performance of the employees" (https://www.gesetze-im-internet.de/englisch_betrvg/englisch_betrvg.html).
**Fix:**
- Logs and records hold pseudonymous principal ids. A separate identity directory maps ids to names under a per-person key that can be crypto-shredded, except under documented legal holds (Part 11 retention, litigation).
- Transcripts and API logs get their own retention, 12 months by default, separate from release records.
- Presence, follow mode and tab-view recording are organization settings, with a works-council mode that disables per-person activity analytics.
- Ship records-of-processing entries and a DPIA template.
- List hosted model providers as sub-processors, with their regions and retention terms.

### R5-29 · Major · Targets: UIX, PLT
**Section:** UIX Telemetry (D-UIX-22), Crash and error reporting; PLT Opt-in performance telemetry, Enterprise policy
**Problem:** There are two telemetry pipelines with different payloads, identifiers and retention: UIX keeps raw events for 90 days and sends command ids, error codes and settings, while PLT uses a random install id, drops aggregates covering fewer than 50 installs, and keeps data for 13 months. Neither names a controller, legal basis, processors, storage region or transfer mechanism, although install ids and IP addresses are personal data. UIX's "air-gapped builds exclude the sender at compile time" contradicts PLT's single reproducible binary per architecture.
**Evidence:** UIX: "Raw events are kept 90 days; aggregates are kept longer". PLT: "a random install id that resets on request"; the server "retains data for 13 months". GDPR Recital 30: persons "may be associated with online identifiers provided by their devices, applications, tools and protocols", such as IP addresses (https://gdpr-info.eu/recitals/no-30/).
**Fix:** One pipeline, owned by PLT, with one public schema: the union of the UIX and PLT fields, minus raw command streams.
- Telemetry is opt-in per install.
- The install id rotates every 90 days and is never joined to account ids.
- The server drops aggregates covering fewer than 50 installs.
- Raw data is kept for 90 days and aggregates for 13 months.
- EU organizations' data is collected in an EU region.
- A privacy notice names the steward as controller, plus the processors and the transfer basis, and a DPIA template ships with it.

Replace compile-time exclusion with the signed enterprise policy `telemetry.performance = off` plus an egress allowlist.

### R6-04 · Major · Targets: CONTRACT, PLT, ANV, FLX, UIX
**Section:** CONTRACT §13 (no sequencing); PLT Phasing; ANV, FLX and UIX Phasing
**Problem:** No tab sequences work across tabs, yet phase 1 has two long chains and one coupling point. Chain A: exact predicates → certified SSI on GP1's surface set → Booleans → constant fillets and shells → GP1 features and drawing → STEP AP242 → machining → metrology. Chain B: kernel IR → CPU back ends → immersed elasticity with DWR → topology optimization and homogenization → implicit lattice → 3MF → print → measurement. The phase 0 gate couples every tab, because the determinism suite runs every tab's corpus on every target.
**Evidence:** ANV, FLX, MFG and ECO phase 1 lists; CONTRACT §7.5 makes the kernel IR the source of Flux kernels and of Anvil's implicit tapes; the GP1 gate needs a reference shop and external metrology, which are bound by calendar time, not engineering effort.
**Fix:** Add a sequencing table to §13.1 and track both chains weekly as the program's critical path:

| Months | Milestones |
| --- | --- |
| 0–6 | `detmath` core functions through the C build (R6-19); combinators; CAS and Kiln core; Ingot parser, types and interpreter; kernel IR v0 frozen at month 6; predicates, analytic geometry, topology and `EntityId`; CI on every Tier 1 CPU target |
| 6–12 | Analytic SSI and Booleans; tessellation and `DisplayPackage`; CPU kernel back ends; H¹ elements, CG, MMS; toolkit core and forward renderer; phase 0 gate at month 12, judged per crate on the corpus that exists |
| 12–24 | Fillets, chamfers, shells, holes, patterns, sketches; drawings and GD&T; immersed elasticity, DWR, p-multigrid; topology optimization, homogenization, implicit lattices; STEP AP242 and 3MF writers; team server; Propose and review |
| 20 | Physical dry run of both gates with interim outputs, to exercise the shop, CMM, printer and measurement oracles |
| 24–32 | Hardening, keyboard-complete workflows, accessibility, Tier 1 preview targets |
| 30–34 | GP1 and GP2 physical runs, with one re-run budgeted |
| 36 | Phase 1 gate |

### R6-08 · Major · Targets: PLT, UIX, KLN, FLX
**Section:** PLT Performance engineering, Budgets; UIX Performance, telemetry and quality, Interaction budgets
**Problem:** The budget table mixes rows that hold, rows that hold only once their workload is defined, and rows that cannot hold on the reference laptop. All of them block beta promotion, so infeasible rows will either block every release or be waived case by case.
**Evidence:** PLT Continuous benchmarking item 4: "Any budget row exceeded on any reference machine blocks promotion of the build to beta". The titles of Chrome's "What's New in WebGPU" entries from Chrome 135 to 156 include no 64-bit atomics feature (developer.chrome.com/docs/web-platform/webgpu/news). UIX's own latency target is "≤ 2 frames plus display scan-out", which exceeds 33 ms at 60 Hz.
**Fix:** Rewrite the rows (mid band, reference laptop of R6-07):
1. Keep: cold start 1.5 s and warm start 0.6 s (native); 1,000-part assembly from warm cache 10 s native and 20 s browser, with a coarse view in 2 s; memory with GP1 open under 1 GiB (native); installed size 400 MiB; selection 16 ms (native); browser warm start 2.5 s.
2. Define, then keep: exact rebuild 2 s on a named GP1-class benchmark of prismatic features, plus p90 ≤ 10 s on an ABC-derived 200-feature corpus; interactive simulation update 1 s for linear static elasticity up to 100,000 DOFs at p = 2, warm-started, on G1; orbit 60 fps at 5M visible triangles at 2.1 MP render resolution (R6-10).
3. Replace: coarse drag preview per R6-09; browser orbit with WebGPU 30 fps at 5M or 60 fps at 2M visible triangles; WebGL2 30 fps at 2M visible triangles and at most 1,000 distinct Parts; browser selection ≤ 33 ms (WebGPU readback resolves asynchronously) or a CPU ray cast as on G3; browser interactive simulation 2 s with WebGPU, 6 s on CPU-only sessions, remote above that; input-to-photon p99 ≤ 50 ms at 60 Hz and ≤ 33 ms at 120 Hz; native idle memory 300 MiB with the engine's GPU device created lazily (R6-16); browser idle memory measured after a heavy-worker recycle (R6-14).
4. Low-band rows stay, except the drag preview, which follows R6-09.

### R6-09 · Major · Targets: UIX, KLN, ANV, PLT
**Section:** UIX Direct manipulation, Coarse-first preview pipeline; KLN Scheduling and parallelism (drag lane); ANV Performance targets; PLT Budgets
**Problem:** "Coarse drag preview under 100 ms" with "dependent features updated" cannot hold for an early edit in a 200-feature part, because every downstream feature re-evaluates. Anvil's own exact targets give 50 ms to one 500-face Boolean and 100 ms to one 50-edge fillet chain; even at Preview tolerance, 150 dependents fit in 100 ms only at under 0.7 ms each.
**Evidence:** UIX: "only the edited Part's downstream features are re-evaluated", which for an early edit is nearly all of them. ANV Performance targets: "≤ 50 ms exact" and "≤ 100 ms exact" for single operations. PLT Budgets holds both "Coarse drag preview under 100 ms" and "Exact rebuild, 200-feature part, early edit under 2 s".
**Fix:** State the preview scope in UIX, KLN and ANV: within 100 ms the drag lane recomputes the dragged feature and as many dependents as Kiln's cost estimate fits in 80 ms (at least the next 10 when they are cheap). Later dependents show their previous geometry as Proxy where the change is affine on them, otherwise as Stale. After release, the 2 s exact-rebuild row applies. `uix_drag_preview_budget` runs a late-edit script and an early-edit script separately and reports how many dependents each preview covered.

### R6-10 · Major · Targets: UIX, PLT
**Section:** UIX Renderer, Frame budgets; UIX Transparency; PLT Budgets (orbit row)
**Problem:** The frame budget is set at 1920×1080, but the macOS mid machine (a MacBook Pro) and many Windows laptops drive panels of about 4 to 8 MP at their default scale. Resolve, edges, ambient occlusion, transparency and anti-aliasing scale with pixel count, so the 6.0 ms of pixel-proportional GPU work grows to about 17 ms on a 5.9 MP panel (2.8× the pixels), and 60 fps fails before geometry cost is counted.
**Evidence:** UIX Frame budgets at 1920×1080: resolve and edges 2.5 ms; ambient occlusion, transparency and overlays 2.5 ms; tone map, filter and composite 1.0 ms. UIX cites XeGTAO at "about 2.39 ms on an Intel i7-1195G7 integrated GPU" at 1080p. UIX switches the k-buffer to k = 2 only "above 8 megapixels".
**Fix:** Add a render-scale policy to UIX: during camera motion the 3D view renders at most 2.1 MP and upsamples, while edges, overlays and text draw at native resolution; still frames accumulate at native resolution, which D-UIX-12 already does. State every frame-budget row per render megapixel, add "60 fps at native resolution" as a high-band row, and give X-ray views their own 30 fps row (R6-27).

### R6-11 · Major · Targets: UIX, MEC
**Section:** UIX Renderer, GPU capability tiers; UIX Frame budgets; UIX Very large assemblies
**Problem:** G1 promises 1,000,000 Instances at 60 fps on the reference laptop with 1.0 ms for instance culling, cluster culling and the LOD cut together. Reading 1M transforms of 64 bytes moves 64 MB per frame, about half a millisecond of an integrated GPU's shared memory bandwidth before any cluster work. G2 promises 100,000 Instances in browsers that expose no 64-bit atomics, and G3 promises 10,000 Instances on WebGL2, where each distinct Part costs draw calls.
**Evidence:** UIX: "40,000 transforms of 64 bytes each"; Core Ultra 7 258V uses LPDDR5X-8533 on 2 channels (Intel ARK); the bandwidth figure is my arithmetic for a 128-bit bus. MEC sets the reference-laptop target at a "100,000-instance assembly … orbit it at 60 fps". Chrome's WebGPU entries through Chrome 156 list no 64-bit atomics.
**Fix:** Change UIX's tier table (60 fps, reference laptop, 1920×1080): G1 100,000 Instances and 5M visible triangles; G1 on the high band 1,000,000 Instances; G2 20,000 Instances and 2M visible triangles; G3 1,000 distinct Parts, or 10,000 Instances of at most 1,000 distinct Parts, and 2M visible triangles. Keep 10 million Instances as a phase 5 high-band target only. Split the 1.0 ms culling row into instance culling and cluster culling, with per-tier figures measured in phase 2.

### R6-14 · Major · Targets: PLT, KLN, UIX
**Section:** PLT The browser target, Memory; KLN Memory management and eviction; UIX Very large assemblies (budgets) and Interaction budgets; PLT Budgets
**Problem:** WebAssembly linear memory never shrinks, so one large evaluation leaves the engine worker at its peak for the rest of the session, and the browser idle-memory row cannot hold. The tabs also disagree on the budget: PLT sets a 3 GiB residency budget, KLN a 2 GiB browser budget, and UIX adds up to 1.5 GiB of UI memory plus a 512 MiB GPU page pool, more than many tabs survive.
**Evidence:** WebAssembly memory-control overview: "WebAssembly memory can only grow and never shrink, and there are no APIs for releasing memory to the host"; the proposal "is in its early stages". PLT: "The residency manager's budget is 3 GiB on desktop browsers"; KLN: "2 GiB in browsers"; UIX: "UI memory, 1,000-part assembly ≤ 1.5 GiB host memory"; PLT Budgets browser column: "Idle memory … Under 300 MiB".
**Fix:** PLT owns one browser memory table, replacing KLN's and UIX's numbers. The engine worker keeps a fixed linear-memory cap (proposed 1.5 GiB). Evaluations whose estimated peak exceeds 512 MiB run in a disposable heavy worker with its own memory and compute workers, write results to the OPFS CAS, and terminate afterwards. Phase 0 measures the out-of-memory kill threshold of Chrome, Edge, Firefox and Safari on 8 GB and 32 GB machines, and sets UI, engine and heavy-worker caps below it; where the sum would exceed it, heavy evaluations go remote. The browser idle-memory row is measured after a heavy-worker recycle.

### R6-16 · Major · Targets: PLT, KLN, FLX, UIX
**Section:** PLT The compute runtime, GPU compute and Process model (D-PLT-12); KLN Cancellation; FLX Execution, Placement and scheduling; UIX Field visualization (per-pixel evaluation)
**Problem:** Dispatch limits disagree (PLT 100 ms, KLN 50 ms, FLX 4 ms while the camera moves), and the two larger values stall the renderer, because the engine's compute device and the UI's render device share one GPU and the OS arbitrates between the two processes. wgpu's feature list offers external memory only for Vulkan, so on DX12 and Metal, the Windows and macOS defaults, every GPU-computed Field or preview that the UI paints round-trips through host memory and is uploaded twice.
**Evidence:** PLT: "Each dispatch is sized to finish within 100 ms"; KLN: "GPU work is split into dispatches of at most 50 ms"; FLX: "solver dispatches stay under 4 ms while the camera moves, so orbit holds 60 fps". wgpu 30.0.1 lists only `VULKAN_EXTERNAL_MEMORY_WIN32`, `VULKAN_EXTERNAL_MEMORY_FD` and `VULKAN_EXTERNAL_MEMORY_DMA_BUF` for external memory (docs.rs/wgpu, Features).
**Fix:** PLT owns one rule, cited by KLN and FLX: dispatches ≤ 4 ms while any window renders interactively, ≤ 16 ms while views are idle, ≤ 100 ms only in headless processes. Display-only GPU work (per-pixel Field evaluation, implicit preview, display isosurfaces) runs on the UI process's device from coefficient buffers passed through the existing memory-mapped rings. The engine creates its GPU device lazily, so the idle-memory row excludes it, and UIX's frame budget states a copy budget (for example ≤ 5 ms per 100 MB on unified-memory laptops).

### R6-23 · Major · Targets: UIX, ING
**Section:** UIX UI toolkit, Choice (D-UIX-3); UIX Open questions 1; UIX Code and visual together, The code panel; ING Tooling, Language service
**Problem:** UIX decides between its own toolkit and Masonry "at the phase 1 gate after a two-week spike", by which time the own toolkit, code editor, IME and accessibility layers will have absorbed about 20 EY. The code panel must also compete with the editors code-CAD users already work in, which is a product of its own.
**Evidence:** UIX open question 1 and D-UIX-3. Zed's editor, built on its own toolkit, reached Windows on 15 October 2025 with a dedicated Windows team (zed.dev). AccessKit's web adapter is "planned", and its adapters "don't yet support rich text or hypertext" (github.com/AccessKit/accesskit).
**Fix:** (1) Move the decision to month 3 of phase 0: a six-week bake-off builds three screens with both options (a virtualized 1,000,000-row tree, a properties panel with an IME text field, a code panel on a 50,000-line file) on Windows, macOS, Linux and Chrome, judged by `uix_a11y_tree`, `uix_ime` and the frame budgets. (2) Phase 1 toolkit scope: docked layout with collapsible panels, no detached windows, bidirectional text but no layout mirroring until phase 2, no Vim mode. (3) ING ships the language service as an LSP server over stdio in phase 1, with first-party VS Code and Zed extensions and a custom request that drives Crucible's viewport for cross-probing. The in-app code panel then covers editing, diagnostics, hover, completion and scrubbing in phase 1.

### R6-24 · Major · Targets: UIX
**Section:** UIX Renderer, Frame pipeline (G1 and G2), Transparency; UIX Phasing (phases 0 and 1)
**Problem:** Phases 0 and 1 build a visibility-buffer pipeline for G1 and G2, a forward pipeline for G3 and hybrid transparency, although both phase 1 golden products are single Parts. The cluster-DAG pipeline is still unfinished in its open reference implementation and belongs with the first assembly golden products.
**Evidence:** UIX Phasing: phase 0 "wgpu renderer on G1 and G3", phase 1 "browser on G2 and G3", phase 2 "Cluster DAG streaming and two-pass occlusion culling at assembly scale". Bevy's virtual geometry on wgpu: "I'm still not done working on DAG quality" and "culling is the biggest bottleneck at the moment" (jms55.github.io, 27 March 2025).
**Fix:** Phase 1 ships one forward renderer on G1, G2 and G3: per-face and per-Instance id targets for picking, model edges from `DisplayPackage`, level-0 clusters with per-Part discrete LOD, weighted blended transparency, section caps, half-resolution ambient occlusion, and Keeter-style direct implicit rendering on G1 and G2 for the GP2 lattice. The visibility buffer, DAG LOD cut, two-pass occlusion, compute rasterization and k-buffer arrive in phase 2, gated by `uix_frame_budget` on GP3 and GP4. `DisplayPackage` carries DAG pages from phase 0, so no format changes.

### R6-26 · Major · Targets: UIX, AGT, PLT
**Section:** UIX Interfaces with other subsystems (headless snapshots); UIX Renderer, GPU capability tiers; AGT Platform notes (Determinism); AGT Oracles (O-AGT-3)
**Problem:** UIX promises `render_snapshot` "deterministic per platform class on the CPU path", and AGT requires CPU renders "byte-identical within a platform class". The CPU path is Mesa lavapipe or WARP, whose shader code is generated at run time for the host CPU, and `CpuCanonical` spans every CPU, so the promise cannot hold; macOS has no software renderer at all.
**Evidence:** Mesa llvmpipe documentation: "a software rasterizer that uses LLVM to do runtime code generation", with `LP_NATIVE_VECTOR_WIDTH` and `GALLIUM_OVERRIDE_CPU_CAPS` changing the code it emits (docs.mesa3d.org/drivers/llvmpipe.html). UIX: "Headless servers and broken drivers render through wgpu on software Vulkan (Mesa lavapipe on Linux) or WARP".
**Fix:** Declare snapshots non-canonical: they carry `PlatformClass::Unverified` plus the renderer identity, never enter cache keys or Approval digests, and are compared by ꟻLIP thresholds. Byte identity applies only on one pinned CI renderer image (a container with a pinned lavapipe build and fixed `LP_NATIVE_VECTOR_WIDTH` and `GALLIUM_OVERRIDE_CPU_CAPS`); reword O-AGT-3 accordingly. Snapshots attached to Proposals are stored once as Assets, so reviewers and approvals see the same bytes.

### R6-27 · Major · Targets: UIX
**Section:** UIX Renderer, Transparency (D-UIX-11)
**Problem:** The k-buffer orders layers with 32-bit atomics on depth alone, so coincident faces, common in X-ray views of assemblies where mating faces touch, tie and resolve in varying order, which shows as flicker between frames. Its memory, 41 bytes per pixel at k = 4, exceeds WebGPU's default 128 MiB storage binding on any panel above about 3.3 MP, well below the 8 MP switch to k = 2.
**Evidence:** D-UIX-11: "a two-pass k-buffer built from 32-bit atomics", "41 bytes per pixel for k = 4 (85 MB at 1920×1080)", "k = 2 above 8 megapixels on G2"; UIX Browser specifics: default `maxStorageBufferBindingSize` of 128 MiB. A 5.9 MP panel needs about 243 MB at k = 4 (my arithmetic).
**Fix:** Pack each 32-bit key as 24 bits of quantized reversed-Z depth plus an 8-bit hash of (Instance, face), and break remaining ties by `EntityId` order in the resolve pass; opaque depth stays f32. Choose k per frame from the adapter's `maxStorageBufferBindingSize` and the render resolution (R6-10), splitting bindings where the adapter allows. X-ray views get their own 30 fps row that includes the second geometry pass.

### R6-30 · Major · Targets: PLT, FLX, UIX
**Section:** PLT Build and release engineering, Toolchain and dependencies (item 4); PLT The platform layer, Library choices; PLT The compute runtime, SIMD; FLX Build, wrap or avoid
**Problem:** Core paths depend on young or thinly maintained crates, with no risk register: CubeCL is alpha, winit 0.31 is in beta, faer and pulp come from one maintainer whose repository moved to Codeberg, AccessKit has no web adapter and no rich text, Parley, HarfRust and Taffy are pre-1.0, and wgpu changes its API every major release. `deps/approved.toml` records licence and maintainer status but no fallback.
**Evidence:** CubeCL README ("alpha"; breaking changes "between minor versions"); winit releases (0.31.0-beta.3 on 4 September, latest stable 0.30.13); faer README: "the project has migrated to codeberg" and the GitHub repository "is currently left as a mirror"; AccessKit README; Linebender: "Fearless SIMD v1.0 is here", with "3 years of security updates for v1.0" (linebender.org/blog/fearless-simd-1-0).
**Fix:** Extend `deps/approved.toml` with a risk class, an owning engineer, an upgrade cadence and a fork-or-replace plan for every core dependency, reviewed at each gate. Specific actions: fund faer's maintainer or vendor faer and pulp under a named Crucible owner; evaluate fearless_simd 1.0 against pulp for `simd` dispatch in phase 0; budget one wgpu upgrade per quarter (about three engineer-weeks, estimate); defer CubeCL (R6-22); keep AccessKit web-adapter work upstream with two engineers (R6-03).

### R6-38 · Major · Targets: PLT, UIX
**Section:** PLT Performance engineering, Budgets (cold start and installed size rows); UIX Platforms and devices, Browser specifics
**Problem:** The two tabs set different browser startup and payload targets for the same measurement.
**Evidence:** PLT: "under 2.5 s with warm HTTP cache; under 8 s on a first visit over 100 Mbit/s" and "Engine download under 25 MiB compressed per build"; UIX: "interactive in 3 s on a warm HTTP cache and 6 s cold on a 50 Mbit/s link, with a Wasm payload under 20 MB compressed".
**Fix:** PLT owns one row: warm start ≤ 2.5 s; first visit ≤ 8 s at 50 Mbit/s; initial Wasm (UI module plus engine) ≤ 25 MiB brotli-compressed, with translators, CAM, electronics and physics packages loaded on demand. UIX points to it.

### R2-44 · Minor · Targets: UIX, ING, ANV
**Section:** UIX From gesture to Ingot edit (ranking rule 1); ING Derivatives
**Problem:** Edit-plan ranking uses derivatives of the dragged quantity with respect to literals, but derivatives through Anvil operations need `anvil::shape_velocity`, which is phase 2, while direct manipulation is phase 1, and ING then falls back to dependence only. UIX does not say what the phase 1 ranking is.
**Evidence:** UIX "The nearest single literal with a non-zero derivative ranks first"; ANV `shape_velocity` "Phase 2"; ING "An Op without a tangent rule makes the derivative fail ... and the UIX ranking falls back to dependence only".
**Fix:** State the phase 1 ranking: provenance first (the literal of the call whose OpSite and role created the dragged entity, for example the extrude distance for an end cap), then IIR dependence distance; derivatives refine the ranking from phase 2.

### R3-49 · Minor · Targets: CONTRACT, AGT, KLN, PLT, ELX, UIX, ECO
**Section:** CONTRACT 7.1; AGT "Method catalog"; KLN "Progressive results"; PLT "Software bill of materials and provenance"; ELX "Software and firmware as BOM items"; UIX Interfaces; ECO "Contexts"
**Problem:** Several naming drifts are not covered by section 14.
**Evidence:** AGT uses "revision" for repository states (`RevisionRef`, `{rev, ...}`, `CheckReport { revision: RevisionId }`) and writes `fidelity: Coarse or Exact`. KLN adds a `Provisional` status. PLT and ELX write "SBOM" for the software bill of materials. The contract itself writes "Every commit rebuilds the design" (7.1) and "The BOM is a query". UIX uses the placeholders `FeatureId`, `ExprId`, `CasRef` and `FieldRef`, and ECO names the UI world `crucible:ui/ui-panel` where UIX writes `crucible:ui/panel`.
**Fix:** AGT: `ChangeRef`, `change` and `Fidelity`. KLN: the derived "provisional" predicate of R3-07. PLT and ELX: "software bill of materials". Contract: "Every Change on a protected branch rebuilds the design"; "The BOM is a derived view over the assembly graph". UIX: `OpSite`, `LiteralSite`, `ObjectId` and a Field handle. One world name: `crucible:ui/panel`.

### R4-37 · Minor · Targets: UIX
**Section:** Modes; Toolpath preview and playback.
**Problem:** UIX uses "operation" for CAM steps, which the contract reserves for Anvil and Flux primitives; MFG maps the industry term to "workingstep".
**Evidence:** UIX: Manufacture panels "Setups, operations, playback, cost"; collisions "each linking to the operation"; "scrub by time or by operation"; "The timeline shows operations and tool changes".
**Fix:** Use "workingstep" throughout UIX and register "operation" as a CAM synonym in the command registry so palette searches still find it.

### R4-38 · Minor · Targets: UIX, MEC
**Section:** UIX Drawings and model-based definition; MEC Automated drawing generation.
**Problem:** UIX runs automatic dimensioning as an agent request, while MEC specifies `auto_drawing` as a deterministic function with a layout optimizer and an oracle, so users cannot tell whether the result is reproducible.
**Evidence:** UIX: "Automatic dimensioning runs as an agent request and arrives as an `EditPlan` preview."; MEC: "`auto_drawing(part, template, rules)` writes an editable drawing program".
**Fix:** UIX calls MEC's `auto_drawing` and shows its output as an `EditPlan` preview; agents may refine the result afterwards in a separate Proposal.

### R4-39 · Minor · Targets: UIX
**Section:** Keymaps; Migration from other CAD tools; First run.
**Problem:** Presets cover SOLIDWORKS, Fusion, Onshape and Blender. NX, Creo, Inventor and CATIA users and CAM programmers have no presets or synonym sets, and first-run roles omit electronics.
**Evidence:** UIX preset table; "Presets for SOLIDWORKS, Fusion, Onshape and Blender users"; first run asks "role (design, simulation, manufacturing, review)".
**Fix:** Add NX-like, Creo-like and Inventor-like navigation presets and palette synonym sets, verified by daily users as UIX already requires, CAM synonym sets, the Altium-like and KiCad-like presets of R4-04, and an electronics role.

### R5-42 · Minor · Targets: UIX, ECO
**Section:** UIX Extending the interface (D-UIX-23); What the toolkit requires from the platform layer (deep links)
**Problem:** Panel components can render element trees that imitate Crucible's own dialogs, such as a fake "session expired" prompt. Their `api/edit` calls appear in history as the user's own edits. URL-scheme deep links let any web page or agent message open in-app views, including approval pages.
**Evidence:** UIX: panels return "stacks, grids, text, fields, tables, charts, trees and viewport overlays"; `crucible:api/edit` is granted "only when the user grants it to this package". UIX's platform requirements list "URL-scheme deep links".
**Fix:** Panels render inside chrome that shows the package identity and may not use modal or system-styled elements. Panel edits record the package in `ChangeProvenance`, as agent edits do. Deep links navigate and never act; approval pages are reachable only from the inbox (R5-04).

### R5-43 · Minor · Targets: UIX, AGT
**Section:** UIX Steering mid-task, Comments anchored to geometry (@mentions), Agent panel (attachments)
**Problem:** UIX does not say who may steer a running agent or @mention it into action. Request attachments (comments, files) enter as part of the goal, which AGT treats as trusted. A collaborator, or a supplier's principal on a shared branch, could therefore instruct an agent with the delegating human's authority.
**Evidence:** UIX: "A message sent while an agent runs is delivered at its next step boundary as a priority instruction"; threads support "@mentions of people and agents"; the request input takes attachments including "comments, files". AGT trusts "The goal text from the delegating human."
**Fix:** Only the delegating human can steer. An @mention by anyone else creates a request in the delegating human's inbox. Attachments enter the agent's context as `ExternalText` with their origin, never as goal text.

### R6-42 · Minor · Targets: UIX, ANV
**Section:** UIX Renderer, Display of Implicit, SubD and Mesh Bodies; ANV Performance, parallelism and determinism, GPU use
**Problem:** UIX compiles each Anvil implicit expression to WGSL for direct rendering, so every edit of a lattice parameter creates a new pipeline whose shader compile lands inside the drag. Anvil already specifies a GPU tape interpreter with interval pruning that takes new tapes as data.
**Evidence:** UIX: "Direct implicit rendering compiles the Anvil expression to WGSL"; ANV GPU use table: "Implicit tape interpreter with interval pruning".
**Fix:** UIX renders implicits with Anvil's WGSL tape interpreter during edits, and compiles a specialized shader only for still views of an unchanged expression.

### R6-43 · Minor · Targets: UIX
**Section:** UIX UI toolkit, Text (D-UIX-4)
**Problem:** Grayscale antialiasing of unhinted 11 and 12 px text on 100%-scaled 1080p Windows and Linux displays looks soft beside native applications, and D-UIX-4 says nothing about hinting.
**Evidence:** UIX Typography sets tree rows and controls at 12 px and captions at 11 px; Skrifa's `outline` module covers "Loading, scaling and hinting of glyph outlines" (docs.rs skrifa 0.48.0).
**Fix:** Add to D-UIX-4: glyphs are hinted with Skrifa's hinter at UI scale below 1.5 on every platform, using the same code so layout and bitmaps stay identical across OSes, and unhinted above; the snapshot oracles run at both scales.

### R6-46 · Minor · Targets: UIX
**Section:** UIX Renderer, Frame pipeline (G1 and G2), G2 paragraph
**Problem:** G2 draws visible clusters with one non-indexed `drawIndirect` that runs 384 vertex invocations per 128-triangle cluster and pads with degenerate triangles. Vertex work is therefore three invocations per triangle with no post-transform reuse, on the tier that has no compute rasterization to fall back on.
**Evidence:** UIX: "A vertex shader pulls cluster vertices from storage buffers and emits degenerate triangles past a cluster's triangle count."
**Fix:** The cluster-culling pass writes the surviving clusters' triangle indices into one compacted index buffer, drawn with a single `drawIndexedIndirect`, so shared vertices are reused and no degenerate triangles are issued; keep the per-cluster method as the fallback when the compacted buffer would exceed the binding limit.
