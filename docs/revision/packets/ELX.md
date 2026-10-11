# ELX round 3 packet

Your tab is `docs/spec/08-electronics-systems.md` at v2 (tag `round-2`). Round 3 fixes, in one pass: the 23 second-review findings that target it (1 Critical, 17 Major, 5 Minor), its 36 `[unverified]` claims, its open questions and the known items below. Contract v6 is binding; its section 17 lists the rulings on this review, and many findings below are already settled there.

## Second-review findings

### R7-08 · Major · Targets: CONTRACT, FLX, MFG, ANV, ELX, COV
**Section:** Contract 13.4 rule and rows
**Problem:** The shared phase table phases each capability by the gate that names it, but not by what it depends on. Several prerequisites therefore land after the capabilities that need them: metal PBF supports (MFG 2) after inherent strain (1); as-built strut calibration (MFG 2) after GP2's strut checks (1); `anvil::boundary_layer` (ANV 4) after the phase 3 laminar conjugate heat transfer and 3D mould fill that FLX's own plan sends to fitted boundary layers; an eigenvalue estimator (none) under row 1; and a Koiter-coefficient computation (none) under COV's buckling envelope. The SPMe row omits FLX, although SPMe needs FLX's phase 4 parameter-domain spaces.
**Evidence:** ANV: "`anvil::boundary_layer` | … | ANV-O-BL-1 | 4". FLX plan defaults: "Contact, sliding interfaces, boundary layers; voxel data | Fitted meshes; finite cell". FLX: "Parameter-domain spaces | … | FLX-O-FORM-5 | 4" and "parameter-domain forms for SPMe cells" (phase 4), while 13.4's SPMe row lists "Also phased in: COV".
**Fix:** Add to the 13.4 rule: "A capability that a row or a gate depends on takes a phase no later than its dependent; each row names its prerequisites in a column 'Needs'." Then apply it: supports and inherent strain both in phase 2 (R7-07); as-built strut calibration in phase 1 (R7-06); laminar conjugate heat transfer and mould fill state an octree wall-resolution rule instead of fitted layers (R7-09); eigenvalue DWR in phase 1 under row 1 (R7-05); a Koiter computation in phase 2 under COV's nonlinear buckling; FLX added to the SPMe row's "Also phased in".

### R7-22 · Major · Targets: ELX, FLX
**Section:** ELX "Analyses and results"; FLX "Time integration", budget table (temporal row)
**Problem:** ELX contradicts FLX on the temporal error of circuit transients. ELX labels temporal error `Estimated` from truncation-error control, but FLX rules that summed local truncation errors are `Indicator` because phase error accumulates in oscillatory problems (R1-20). Oscillators, LC tanks, PLLs and switching converters are exactly such problems. Under ELX's wording a circuit check could pass `SignOff` on an indicator.
**Evidence:** ELX: "temporal and algebraic errors `Estimated` from truncation control and residuals". FLX: "Temporal goal error is the adjoint-weighted residual in time; summed local estimates are `Indicator`, because phase error accumulates in oscillatory problems (R1-20)."
**Fix:** ELX adopts FLX's rule: the temporal part is `Indicator` unless `solve_dae` runs the adjoint-weighted temporal estimate for the checked goal (FLX-O-ERR-6), or a step-halving solution verification with frozen breakpoints computes it as a calibrated class. ELX's transient check examples and ELX-O-SIM-1 state which applies.

### R7-41 · Minor · Targets: ELX, COV
**Section:** ELX Open questions 7 and "Cell models"
**Problem:** ELX has opened no reference models for LFP hysteresis, swelling or abuse, though PyBaMM, its stated reference, documents two of them.
**Evidence:** PyBaMM's one-state hysteresis OCP submodel cites Börjesson Axén et al., Journal of Energy Storage 48 (2022), an evaluation of hysteresis expressions developed on a NiMH system (https://docs.pybamm.org/en/latest/source/api/models/submodels/interface/open_circuit_potential/one_state_hysteresis_ocp.html). Its swelling-only submodel cites Ai, Kraft, Sturm, Jossen and Wu, J. Electrochem. Soc. 167(1):013512 (https://docs.pybamm.org/en/latest/source/api/models/submodels/particle_mechanics/swelling_only.html).
**Fix (answers ELX open question 7):** Hysteresis uses PyBaMM's one-state model, with its parameters fitted to LFP charge and discharge data before ELX-O-BAT-1 counts it, since its source system is NiMH. Swelling uses the Ai et al. model, with cell thickness against state of charge and pad stiffness as ELX-O-BAT-2's data. Abuse mechanics stays [unverified] and blocked until phase 6 names a published homogenized jelly-roll model with test data.

### R8-22 · Major · Targets: ANV, ELX
**Section:** ANV Planar integer geometry (D-ANV-27); ELX Layout (D-ELX-6)
**Problem:** Storing "an arc as three integer points" makes the commonest board construction leave the representation: offsetting an arc or round pad by a clearance keeps its centre and changes its radius, but the three offset points are irrational, so every clearance offset snaps and either loses concentricity or falls back to a polygon. A three-point arc's centre is also ill-conditioned for short arcs, so a sub-grid snap moves it far. Gerber, IPC-2581 and ODB++ describe arcs by centre and end points, so every import converts.
**Evidence:** ANV: "polygons with line and arc edges, an arc stored as three integer points"; "A reconstructed arc is kept only when the snapped arc passes the exact check; otherwise its polygonal approximation ... replaces it". D-ANV-27 rejects approximating arcs because it "loses exact arcs that boards and masks use".
**Fix:** Store arcs as an integer centre, an integer radius and two integer direction vectors for the start and end rays. Offsets by integer distances are then exact (same centre, r ± d, same rays), circles and round pads are exact, and only arc–arc and arc–line intersections snap conservatively. Predicates stay exact with square roots eliminated by repeated squaring; ANV states the integer widths this needs for ELX's ±2⁴⁰ nm range. Three-point arcs from KiCad import convert with the declared conservative snap. Add ANV-O-PLANAR cases on concentric clearances.

### R9-01 · Critical · Targets: CONTRACT, KLN, AGT, ELX, MFG
**Section:** CONTRACT 5 (`ApprovalSubject`); KLN "Revisions and lifecycle states" (D-KLN-26), "Change orders" (D-KLN-28); AGT "Acts and approvals" (D-AGT-20); ELX "Software and firmware as BOM items"
**Problem:** The binding `ApprovalSubject` covers only geometry and PMI, so an approved release does not bind the firmware, material, properties, documents or programs it ships. The release plan's digest deliberately excludes the `ChangeId`, so after approval anyone who can push may rebase onto a Change with the same subject but a different Software item binary or Material, and the approval stays valid. KLN's `ItemDefinition` is richer than the contract's subject but is defined only for Parts and Assemblies, and the contract wins where they differ.
**Evidence:** Contract 5: "`ApprovalSubject` [KLN]: `{ base revisions, ItemDefinition GeometryIds with PMI attached by canonical entity number, check-verdict digest …, effectivity, evidence record ids }`". KLN l.490: "A revision's `ItemDefinition` holds the `GeometryId`s of the Part or Assembly with PMI …, the `Material` version, properties, the BOM by value and documents by semantic content" (no rule for Software, Document, `Program` or `Purchased` Items). AGT l.889: "A release plan's digest covers the `ApprovalSubject`'s `ObjectId`, the tag and the effectivity, never the `ChangeId`". ELX l.798: a Software item "records its item number, version, binary hashes, source repository and Change, toolchain". A firmware or material swap changes no `GeometryId` and no PMI, and changes a check-verdict entry only if some check happens to read it.
**Fix:** Contract 5 replaces the second element: "`ItemDefinition` digests of every affected Item (KLN), for every Item kind". KLN defines `ItemDefinition` per kind in one table: Part and Assembly (name-free identity per R9-12, PMI by canonical entity number, `Material` `ObjectId`, properties, BOM by value); Document (semantic content); Software item (binary hashes, software bill of materials digest, `load` bindings, toolchain digest); `Program` (posted text digest and its simulation evidence ids); `Purchased` (approved-manufacturer list entries). Late-bound fields stay placeholders. AGT's release plan digest keeps excluding the `ChangeId`, and `act.commit` refuses a tag target whose recomputed subject differs from the approved one. New oracle KLN-O-CHG-2: swapping a Software item binary, a Material version or a document after approval voids the approval, while a rename with `#[was]` does not.

### R9-03 · Major · Targets: CONTRACT, KLN, MFG, ELX
**Section:** CONTRACT 2 (Evidence record); KLN "Physical tests and Evidence records" (D-KLN-35); MFG "Inspection and measurement"
**Problem:** Round 1's R3-17 found that a check's outcome for a fixed Change depended on when it was evaluated. The fix, "an evaluation reads the newest valid evidence record", keeps that dependence: two Evaluations of one Change and lockfile differ when a record arrives between them, two trusted builders can disagree, and incremental and cold builds can differ. "Valid" also reads the clock, since a record from an instrument "past calibration is invalid".
**Evidence:** Contract 2: "An evaluation reads the newest valid evidence record and stores its `ObjectId` in the `CheckOutcome`". KLN l.792: "A record from an instrument past calibration is invalid, and checks over it fail with `CalibrationExpired`". MFG l.563 repeats "Evaluation reads the newest valid record". KLN-O-EQUIV-1 requires incremental to equal from-scratch; contract 7.8 requires two builders to produce the same `ObjectId`.
**Fix:** Evidence selection becomes a function of a recorded input. Each Evaluation reads an evidence index at a transaction-log position, the evidence watermark, which is an input cell recorded in the Evaluation report and CI report. Protected branches advance the watermark by an audited ref transaction when records arrive, so a (Change, watermark) pair fixes every outcome, and two builders evaluate at the same watermark. Validity is judged at the measurement time (the instrument's calibration covered the measurement date), never at evaluation time. Contract 2 rewrites the sentence to "reads the newest record valid at its measurement time, up to the Evaluation's evidence watermark". KLN-O-HW-1 adds: two Evaluations at one watermark agree while a record arrives in between.

### R9-07 · Major · Targets: ING, KLN, AGT, PLT, UIX, MEC, ELX
**Section:** ING "The Ingot IR and Kiln" item 5 (overrides); KLN "Graph model", "Keys"; AGT `evaluate.*` methods; PLT `PoolLane`; UIX D-UIX-15, D-UIX-27; MEC sketch drag; ELX router
**Problem:** The drag path, the most latency-critical path in the product, has no owner in Kiln or `api`. Literal overrides are input cells per ING, but KLN never mentions them, and a feature node's key (module code hashes, argument identities, `OpSite`, limits) does not include an override of a literal inside the feature's own body, so an overridden result can be stored and served under the un-overridden key. UIX, MEC and ELX route per-pointer tools through an "interactive edit lane" and an `api` edit stream that neither PLT's lanes nor AGT's catalog define.
**Evidence:** ING l.753: "A request may carry literal overrides keyed by `LiteralSite` … Kiln treats them as input cells". KLN l.54 lists input cells without overrides, and the word appears nowhere else in KLN. AGT l.312: `evaluate.build` takes "Targets, `Fidelity`, `estimate_only`". UIX l.593: tools "run in the engine process on an interactive edit lane and stream geometry each frame through `api`"; MEC l.180: "`api` Edit stream at 60 Hz"; PLT l.293: `pub enum PoolLane { Foreground, Background }`.
**Fix:** KLN adds overrides to its input cells and to rule 4 of "Keys": a node's key includes the canonical encoding of the overrides whose `LiteralSite` lies in its own code, and results computed under overrides are never written to the shared cache. AGT adds `evaluate.subscribe { targets, overrides, ceiling }` and an `edit.stream` method (a session-scoped stream of override updates ending in one `edit.apply`). PLT adds a third `PoolLane`, `Interactive`, preempting `Foreground` work at node boundaries, which KLN's priority table maps from the drag lane. ING-O-12 and KLN-O-PROG-1 add: a drag's overridden result never answers a request without the override.

### R9-09 · Major · Targets: CONTRACT, KLN, FLX, COV, ELX
**Section:** CONTRACT 7.1 (label invariance), 7.2 (last paragraph); KLN "Keys" rule 2 and `OpCx::rng`; FLX "General operations for non-variational methods"; COV "Platform notes" (Monte Carlo determinism); ELX "Analyses and results"
**Problem:** The keying of random streams is stated four ways, and two of them break other rules. Contract 7.2's "class-independent part of the key" still contains `ObjectId`s, which hash names, so it contradicts 7.1's label invariance; FLX keys streams "by the Op key", which includes the class, so CPU and GPU runs draw different samples (round 1's R3-11). Only KLN's form is consistent.
**Evidence:** Contract 7.2: "Random streams are keyed by the class-independent part of the key." Contract 7.1: "random seeds come from geometry, topology and argument values, never from names." FLX l.450: "counter-based random streams (Philox, keyed by the Op key)". COV l.782 and ELX l.523: "keyed by the class-independent part of the Op key". KLN l.74: "keyed without class, fidelity or names (by `GeometryId`s and argument values)".
**Fix:** Contract 7.2's sentence becomes KLN's: "Random streams are keyed by the operation identity, argument values and input `GeometryId`s or name-free content hashes, never by class, fidelity, `ObjectId`s of named values or `OpSite`s." KLN owns the mechanism (`OpCx::rng`); FLX, COV and ELX replace their sentences with one line pointing to KLN. ANV-O-LABEL-1 adds a Monte Carlo golden check under re-randomized names.

### R9-15 · Major · Targets: CONTRACT, ING, KLN, COV, MFG, ELX, AGT
**Section:** ING "Checks" (`#[waive]`); KLN release guard ("signed waiver"); COV "Policy by zone" (human waiver in the change order); MFG "Sustainability and compliance" ("a person records a time-bounded waiver"); ELX "Electrical rule checks"; KLN, MEC and ELX parts-policy waivers
**Problem:** "Waiver" is one concept with four mechanisms and no glossary entry: a source attribute any editor can write, a signed waiver at release, a human-only waiver in the change order for envelopes, and recorded waivers for parts policy. Which one a release accepts, who may author it, how it expires and what it names differ by tab, and agents can write the source form, which then shows as a waived status in ELX's requirement view.
**Evidence:** ING l.853: "A waiver is an attribute, `#[waive(check: "static_margin", reason: "…", until: "C")]`". KLN l.507: "or a signed waiver". COV l.168: "Human waiver with rationale; agents cannot waive". MFG l.651: "unless a person records a time-bounded waiver in the change order". ELX l.792: status "waived with a reason".
**Fix:** Contract 2 adds **Waiver**: a signature record by an authorized human naming a `CheckId` (R9-05), the Items and effectivity it covers, a reason and an expiry (revision, date or serial range), attached to a Proposal or change order. `#[waive]` in source is only a request that review shows; it counts nowhere until a matching Waiver record exists. Agents may write the attribute, never the record; `Protected` checks and `Refuse` envelopes accept none. ING, KLN, COV, MFG, ELX and MEC cite the entry instead of defining their own.

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

### R9-34 · Major · Targets: ING, ELX
**Section:** ING Open questions 5 ("ELX data modules"); ELX Open questions 10 ("Data-module size")
**Problem:** Both tabs leave open a binary sidecar for large `Schematic` and `Layout` data modules. A second storage format would bypass every mechanism built on Ingot text: block-level merge, the live document, span provenance, text-derived `OpSite`s and Git export, so each would need a binary path.
**Evidence:** ING l.1282: "Layouts of 10⁶ items may parse too slowly as Ingot; the fallback is a binary sidecar keyed by statement identity." ELX l.982: "if very large layouts parse too slowly, ING's binary sidecar keeps their semantics and changes only the file format".
**Fix:** Decide: no sidecar. Data modules use `table { … }` literals whose rows are atomic blocks (ING already makes table rows blocks), parsed by a row-specialized lexer that skips the general tree for rows and builds lossless nodes lazily on edit. Target: 10⁶ rows parsed and hashed in under 1 s natively (ING-O-n, measured on an ELX layout fixture in phase 2, before ELX's phase 3 need). If the target fails, split the module by board region, which merge and live documents already handle.

### R9-44 · Minor · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT
**Section:** Every tab (contract 11 style rules)
**Problem:** The tabs carry about 1,080 sentences over 25 words and about 340 paragraphs over three sentences, by the spec check's own count, mostly inside decisions; KLN's lead sentence alone runs 33 words. Contract 11 asks for sentences under 25 words and paragraphs of at most three sentences, and the founder's taste requirement makes this more than polish for a spec read by agents.
**Evidence:** `python3 docs/tools/check.py` per tab: ANV 167, KLN 128, PLT 122, AGT 99, UIX 96, ELX 94, ECO 85, MEC 83, FLX 79, ING 72, MFG 41, COV 12 long sentences; FLX 41 and KLN 34 long paragraphs.
**Fix:** Round 3's revision brief sets a hard budget the check enforces as an error: no sentence over 40 words, at most 5% of sentences over 25, no paragraph over four sentences; decisions split *Why* and *Rejected* into short sentences. Leads are rewritten first.

### R9-50 · Minor · Targets: ING, MEC, FLX, ELX, UIX
**Section:** ING Open questions 7 ("Feature granularity"), 8 ("Jacobian types") and 9 ("Literal sites under live edits")
**Problem:** Three design questions remain open before std freezes in phase 1.
**Evidence:** ING l.1284 to 1286.
**Fix:** Question 7: one rule, checked by a std lint: a std helper is a `feature` if it calls an entity-naming operation or returns a value carrying `EntityId`s, a `#[memo] fn` if it is pure and estimated above 10⁶ steps, and a `fn` otherwise. Question 8: `Mat<R, C>` diagnostics name the offending entry `(i, j)` with its expected and actual dimensions and print the row and column dimension vectors once, as an `ING3001` note. Question 9: overrides key by `LiteralSite`, which follows `#[was]`; a concurrent rename writes `#[was(old)]`, so the override maps to the new site and the drag continues. Only a deleted literal ends the drag, with the notice ING describes.

### R10-06 · Major · Targets: CONTRACT, ELX, AGT, KLN
**Section:** ELX Open questions 13; ELX "Hardware-in-the-loop"; ELX Platform notes ("Hardware access")
**Problem:** ELX leaves open whether flashing a board outside an `unattended_safe` rig is an Act. Its Platform notes already let clients flash through `apps/platform`, and browsers through WebUSB. Flashing is a physical effect: firmware runs when the core leaves reset. Flashing a motor controller, ESC, heater driver or charger therefore starts motion or energy at that moment, which is what contract 7.6 reserves to a person at the device. GP6 (ESCs and flight controller) and GP12 (BMS and charger) depend on flashing.
**Evidence:** ELX: "on any other bench a person flashes the board and enables outputs". ELX Platform notes: "Bench adapters and flashing use USB and serial through `apps/platform`; browsers use WebUSB and WebSerial where available".
**Fix:** Answer to ELX OQ13. Flashing becomes a transfer Act, `flash_device`, in contract 2's list.
1. Its plan names the Software item version, image digest, target board serial and the probe or bootloader.
2. The bench adapter or gateway writes the image, verifies it by reading back its digest, and leaves the target halted or held in reset. A person at the bench releases reset or applies power.
3. The Approval covers the image digest and target. The approval page shows the board's hazards from its Network (rotational ports, heaters, high voltage) and a "remove propellers and loads" step where they exist.
4. Client-side flashing through `apps/platform` and WebUSB is the same Act, never a side path. `run_rig_test` keeps covering flashing on `unattended_safe` rigs.

### R10-24 · Major · Targets: ELX, KLN
**Section:** ELX D-ELX-3 and D-ELX-5 (catalog selections and offers)
**Problem:** A `CatalogSelection` re-resolves whenever its arguments change. It may rank by price or stock from pinned offers, and `crucible update parts` refreshes those offers. After layout and release, a part choice is a qualified decision. A price refresh or an upstream edit can still swap the manufacturer part number, or the land pattern, of a placed part, and the next build's assembly BOM changes without a change order. A diff that lists substitutions is not the control component engineering expects.
**Evidence:** D-ELX-3: "A selection re-resolves whenever its arguments change; `crucible update parts` refreshes only the data pins, and its diff lists every substitution."
**Fix:**
1. When a board's layout is first released or locked, each selection records its resolved part in the BOM data module (`resolved: parts::…`).
2. After that, re-resolution never changes the part. It opens a Proposal ("selection now prefers X", with the reason), and a re-pick that changes the land pattern fails with `SelectionChangesLandPattern`.
3. Price- and stock-ranked picks never change a released board's assembly BOM outside a change order.

ELX-O-CAT-3 adds a post-release offer refresh that must leave the BOM unchanged.

### R10-25 · Major · Targets: ELX, MFG
**Section:** ELX "Design rules and the constraint manager" (D-ELX-24)
**Problem:** Spacing comes either from fabricator minimums or from an isolation barrier declared under a safety standard. Most boards also carry functional voltages (24 V, 48 V and 100 V buses) that cross no safety barrier but still need voltage-dependent spacing. Board designers take it from IPC-2221's conductor-spacing table, which separates internal layers, uncoated and coated external layers, and altitude. Without it they hand-write rules. Conformal coating changes those values and needs keep-outs over connectors and test points, yet has no record either.
**Evidence:** ELX's rule example uses only `fab.min_space` and `iso.creepage()`. Neither ELX nor MFG refers to IPC-2221 or coating.
**Fix:** Both arrive in phase 3 with DRC.
1. Add `functional_spacing(nets, voltage)` to `std::electronics::rules`. It reads a licensed IPC-2221 data package [unverified edition] with columns for internal, external uncoated by altitude, external coated, and assembly. Voltages come from `Power` ranges and net classes.
2. Add a `conformal_coating` board record (material, thickness, keep-out regions). It selects the coated column, feeds MFG's assembly package, and fails test-point access checks under coating.

### R10-34 · Minor · Targets: MFG, ELX
**Section:** MFG "Electronics and harness manufacturing handoff"; ELX D-ELX-23; ELX "Pours, planes and vias"
**Problem:** Three gaps remain in the board-house vocabulary:
- MFG's fabrication package omits the IPC-D-356 netlist, which ECO writes and many fabricators use for bare-board test of Gerber packages.
- Vias have no IPC-4761 protection type (tented, plugged, filled, capped), which via-in-pad needs on the fabrication drawing.
- Classes start at 2, though Class 1 governs much consumer work.
**Evidence:** MFG's package list: "IPC-2581C, Gerber X2, XNC drill and route, Gerber job file, impedance and stackup tables, or ODB++". ECO: "Gerber, XNC, IPC-2581C, ODB++, IPC-D-356, placements". ELX: "Class 2, 3 or 3/A".
**Fix:**
1. Add IPC-D-356 to the Gerber package list.
2. Add `protection: Ipc4761Type` per via class, with a fabrication-drawing note and a DFM rule for via-in-pad [unverified edition].
3. Accept Class 1 in `fab_class` and `assembly_class`.

### R10-45 · Minor · Targets: ELX
**Section:** ELX Open questions 10
**Problem:** ELX defers the format question for large `Schematic` and `Layout` modules without a criterion for when to act.
**Evidence:** ELX OQ10: "if very large layouts parse too slowly, ING's binary sidecar keeps their semantics and changes only the file format".
**Fix:**
1. Keep both modules as text.
2. A 20-layer, 10,000-net board holds of the order of 10⁵ to 10⁶ one-line items, tens of megabytes (estimate). At 50 MB/s it parses in under 1 s (target), which ING's benchmark measures on the golden large board.
3. Add the binary sidecar only if that measurement exceeds 1 s, and keep text as the canonical form for merges.

## Verified claims

- MFG: ISA-95 Job Control defines eleven job-order methods, among them `StoreAndStart`, `Start`, `RevokeStart` and `Resume` | https://reference.opcfoundation.org/ISA95JOBCONTROL/v200/docs/6.3
- MFG: OPC 40001-3 (Machinery Job Management) is at 1.0.1 of 1 May 2024 | https://reference.opcfoundation.org/Machinery/Jobs/v100/docs/
- MFG: the EU Machinery Regulation applies from 20 January 2027 with cyber-safety provisions | https://single-market-economy.ec.europa.eu/sectors/mechanical-engineering/machinery_en
- MFG: Bambu Connect "removes slicing functions while enabling remote control and print initiation" | https://blog.bambulab.com/firmware-update-introducing-new-authorization-control-system-2/
- MFG: sparrow is MIT-licensed | https://github.com/JeroenGar/sparrow
- MFG, ELX: jagua-rs is MPL-2.0 | https://github.com/JeroenGar/jagua-rs
- MFG, ELX, ECO: Gerber Layer Format revision 2026.05 (19 May 2026), job format 2020.08, XNC 2021.11 | https://www.ucamco.com/en/gerber/downloads
- MFG: robot safety documentation cites ISO 10218-1:2025 and ISO 10218-2:2025 (marked [unverified] in the tab; both valid from 5 February 2025) | https://www.evs.ee/en/iso-10218-1-2025 and https://www.evs.ee/en/iso-10218-2-2025
- MFG: weld procedure records follow ISO 15614-1 and ISO 15609-1 ([unverified editions] in the tab; current editions are ISO 15614-1:2017 with Amd 1:2019 and ISO 15609-1:2019) | https://www.evs.ee/en/iso-15614-1-2017 and https://www.evs.ee/en/iso-15609-1-2019
- MFG, ECO: QIF 3.0 is ISO 23952:2020, and DMSC Model-Based Characteristics 1.0 was approved by ANSI on 24 June 2026 | https://qifstandards.org
- MFG: AIAG lists the PPAP manual under the identifier PPAP-4 | https://www.aiag.org/training-and-resources/manuals/details/PPAP-4
- MEC: ASME Y14.5-2018 is reaffirmed (R2024) and on stabilized maintenance | https://www.asme.org/codes-standards/find-codes-standards/y14-5-dimensioning-tolerancing
- MEC, KLN: ASME Y14.35-2025 is the current edition of the revision standard | https://www.asme.org/codes-standards/find-codes-standards/y14-35-revision-engineering-drawings-associated-documents
- ELX: the current KBL version (marked [unverified] in the tab) is KBL 2.5 SR-1 | https://ecad-wiki.prostep.org/specifications/kbl/
- ELX: derating follows ECSS-Q-ST-30-11C ([unverified: edition] in the tab; Rev.2 of 23 June 2021, superseding Rev.1) | https://ecss.nl/standard/ecss-q-st-30-11c-rev-2-derating-eee-components-23-june-2021/

### R11-08 · Major · Targets: CONTRACT, KLN, ELX, COV
**Section:** Contract 2 External Op, 7.3, 7.8; KLN "Determinism policy"; ELX D-ELX-12, D-ELX-25
**Problem:** External Ops run only on untrusted-evaluation workers, but 7.8 lets release gates and `SignOff` checks accept a result only from two trusted builders, otherwise "they recompute", which for an External Op means another untrusted run. A `SignOff` check over an IBIS-AMI eye, an ngspice vendor-model run (ELX's default) or a GPL solver is therefore either never acceptable or silently exempt, and nothing binds the pinned result to the run that produced it: the guest computes its own outputs and no receipt is signed.
**Evidence:** Contract 7.8: "Release gates and every `SignOff` check accept a cached result only when two independent trusted builders produced the same `ObjectId` … otherwise they recompute." Contract 2: External Ops run "only on untrusted-evaluation workers". D-ELX-25: "Imported vendor models run by default in ngspice as an External Op". KLN: "External Op results | The host's class or `Unverified` | Only as `ObjectId`s the release pins".
**Fix:** Add an External Op rule to contract 7.8: a release gate or `SignOff` check accepts an External Op result when two single-use runs on different untrusted hosts produce the same output `ObjectId`, computed by each host outside the microVM and recorded in an execution receipt signed by a receipt key that never signs shared-cache attestations. Nondeterministic External Ops yield `Unverified` evidence that meets a gate only under a policy allowance, like a conditional `Pass`. KLN-O-TRUST-1 adds a forged guest output.

### R11-09 · Major · Targets: CONTRACT, PLT, KLN, ECO, ELX
**Section:** Contract 7.8; PLT "Tier 3 and servers", "The compute runtime" (stdio MCP sandbox); ECO "Where translators run", "Tiers and contexts"; ELX "Engine choice"
**Problem:** Every native-code path receives labelled design data, and none states a network policy: External Op microVMs (vendor AMI libraries, emulators, vendor SPICE engines), the licensed-translator host, processes spawned through `crucible:tool/process`, and stdio MCP servers. Vendor engines also need licence servers, so egress cannot simply be absent. Untrusted native code with labelled inputs and an open socket is a direct exfiltration path that bypasses `release_data`.
**Evidence:** Contract 7.8 says untrusted workers "hold no attestation key and write only to a per-Proposal namespace", with no network rule. PLT: stdio MCP servers run "with only their pipes and user-granted folders". ECO's tool context imports `crucible:tool/process`. D-ELX-25 runs encrypted models "in their vendor's engine … where the user holds a licence".
**Fix:** Add to contract 7.8: every External Op host, translator host, spawned tool process and stdio MCP server runs with network egress denied by default; a manifest may declare named egress endpoints (a licence server, an MCP server's API host), which an administrator grants per organization and which the sandbox enforces by address, never by DNS name alone. A host with any egress grant may receive only inputs whose confidentiality label is at most `internal` and carries no `controls`, unless a two-person grant (D-AGT-27) names that host and label. PLT-O-WASM-6 and ECO-O-8 add a native guest that tries DNS, TCP, UDP and HTTP egress.

### R11-17 · Major · Targets: CONTRACT, KLN, ELX
**Section:** Contract 5 `ApprovalSubject`; KLN "Revisions and lifecycle states" (D-KLN-26), "Change orders" (D-KLN-28)
**Problem:** The approval subject is built from `ItemDefinition` `GeometryId`s with PMI, the check-verdict digest, effectivity and evidence ids. A `Software` item (firmware, bitstream) has no geometry, and neither the contract nor KLN says its binary digest is part of its definition. Because approvals deliberately ignore the `ChangeId`, a rebase that swaps a firmware binary while keeping geometry and check verdicts keeps every approval.
**Evidence:** Contract 5: `ApprovalSubject` is "{ base revisions, ItemDefinition GeometryIds with PMI attached by canonical entity number, check-verdict digest …, effectivity, evidence record ids }". KLN: an `ItemDefinition` "holds the `GeometryId`s of the Part or Assembly with PMI …, the `Material` version, properties, the BOM by value and documents by semantic content". Contract 2 defines Software items as BOM entries "bound to a programmable Instance".
**Fix:** Amend contract 5 and D-KLN-26: an `ItemDefinition` holds, per Item kind, everything that is manufactured or loaded: geometry and PMI for Parts and Assemblies; the binary `ObjectId`, its build provenance digest and the target binding for Software items; the posted program for `Program` items; the semantic content for documents. The approval subject covers the full released BOM by value with each line's definition digest. KLN-O-CHG-1 adds a firmware swap under an unchanged geometry that must void the approval.

### R11-31 · Major · Targets: ECO, ELX
**Section:** ECO "Mirrors, licences and the parts catalog" (D-ECO-18); ELX "Creating and migrating catalog parts"
**Problem:** Until a manufacturer verifies, "the operator curates" its `parts::` namespace, and ELX imports KiCad libraries "directly". Manufacturers' CAD models and datasheet compilations come under their own terms, often for design use without redistribution, and KiCad's libraries are CC-BY-SA 4.0, whose design exception does not cover redistributing library items as a collection. Republishing either in the public registry under Crucible's licence would infringe, and the registry's SPDX checks do not say which licences `parts::` data may carry.
**Evidence:** ECO: "A `parts::<manufacturer>` namespace belongs to the manufacturer once it verifies. Until then the operator curates it". ELX: "KiCad libraries import directly." KiCad's library licence: "Redistributed library collections must be shared under the same license agreement" (https://www.kicad.org/libraries/license/).
**Fix:** Add to D-ECO-18: operator-curated `parts::` packages contain only facts (dimensions, pin tables, ratings, each with its datasheet citation) and geometry that Crucible's own generators produce from those facts (ELX's footprint generators, MEC's parametric bodies); manufacturer CAD files enter only when the manufacturer's terms allow redistribution, recorded in `geometry_licence`. Migrated KiCad library items stay in organization-private packages, or in public packages licensed CC-BY-SA-4.0 with attribution kept. The registry refuses `parts::` packages whose data licence is missing or non-redistributable.

## Claims the reviewers verified

Drop the `[unverified]` marker on these and cite the URL in Sources.

- the current KBL version (marked [unverified] in the tab) is KBL 2.5 SR-1 | https://ecad-wiki.prostep.org/specifications/kbl/ (R10)
- derating follows ECSS-Q-ST-30-11C ([unverified: edition] in the tab; Rev.2 of 23 June 2021, superseding Rev.1) | https://ecss.nl/standard/ecss-q-st-30-11c-rev-2-derating-eee-components-23-june-2021/ (R10)

## Unverified claims in your tab

Verify each with WebFetch on a primary source and drop the marker, correct it, or cut the claim if nothing supports it. Line numbers are at tag `round-2`.

- l.190: Netlists export as SPICE, KiCad netlist and EDIF 2 0 0 [unverified]. KiCad schematics import through an `io/` Wasm component: wires become `connect` statements, the drawing becomes the `Schematic` module, and near-miss w
- l.234: Land patterns follow IPC-7351B, whose 2010 edition defines three density levels per package [55][56]; IPC also publishes IPC-7352 [unverified: which document now applies]. The generators read their standard from a pinned
- l.247: Symbols are generated from the pin table, which is the source, as KiCad 10's CSV pin tables suggest [1]; a librarian may refine the drawn view. Alternate body styles follow IEC 60617 or IEEE 315 [unverified: current edit
- l.274: A `Stackup` is an ordered list of layers plus the via spans a fabricator can build. Dielectric permittivity and loss are Fields over frequency fitted with a causal multi-pole Debye model, and laminate records carry IPC-4
- l.290: **Decision D-ELX-23:** A board declares `fab_class` and `assembly_class` (Class 2, 3 or 3/A under IPC-6012 and IPC-A-610, with J-STD-001 soldering [unverified: current editions]). They select MFG rule packs for annular r
- l.332: A flex region carries bend lines with radius, angle and order. `anvil::fold` maps it onto cylinders with the neutral-layer offset from the flex stackup, and folded copper follows the same map. Checks follow IPC-2223 guid
- l.384: **Decision D-ELX-24:** Creepage and clearance come from a declared isolation barrier: its end-product standard (such as IEC 62368-1, IEC 61010-1 or IEC 60601-1), insulation grade, peak and RMS working voltage, overvoltag
- l.412: Global routing follows PathFinder (McMurchie and Ebeling, 1995 [unverified]). Allegro X AI claims a 10× or greater turnaround reduction [40], and Quilter generates candidate boards by reinforcement learning under physics
- l.454: Macromodels use vector fitting (Gustavsen and Semlyen, 1999 [52]) with residue perturbation for passivity, as the SINTEF toolbox does [52], and a Hamiltonian test [unverified: citation]; fit error enters the `ErrorBudget
- l.464: IR drop solves DC conduction on per-layer copper sheets joined by via and plating resistances, beside an IPC-2152-based current-capacity screen [unverified: edition]. Electro-thermal coupling is phase 4 (contract section
- l.477: Part power comes from simulation averaged over a stated window, a declared operating mode or datasheet values, labelled by source. Packages use two-resistor or DELPHI compact models per JEDEC JESD15 [unverified: part num
- l.515: **Decision D-ELX-25:** Imported vendor models run by default in ngspice as an External Op labelled with its host, and move to the native engine only after matching ngspice on their own test bench. Encrypted models never 
- l.548: Crucible ships the engines; handbook tables are licensed data packages outside the public registry. Mission profiles are Ingot values, so part stresses per phase come from simulation and thermal results. Derating follows
- l.556: | Pole-zero and loop stability | Generalized eigenvalues; Middlebrook or Tian loop gain [unverified: citations]; margins | As AC | ELX-O-SIM-1 | 3 |
- l.585: A sensor has three layers: optional Flux transduction physics, such as a Hall element in a magnet's field; a behavioral element with transfer, noise, drift and quantization; and a register interface from CMSIS-SVD or Sys
- l.661: | Equivalent circuit | OCV(SOC, T), R0 and RC pairs; a hysteresis state for LFP [unverified: reference model] | Pack and BMS design in the fitted range | 4 (contract section 13.4) |
- l.664: | Swelling and stack pressure | Expansion against state of charge with pad stiffness [unverified: reference model] | Within the tested pressure range | 4 (contract section 13.4) |
- l.666: | Abuse mechanics | Homogenized jelly roll with failure strain, coupled to runaway screening [unverified: reference model] | Crush, penetration and crash screening | 6 (contract section 13.4) |
- l.687: | Winding loss | Dowell (1966) [unverified: citation]; Albach and Lammeraner for round wire, Albach and Ferreira for Litz [53] | 2D or 3D Flux eddy-current solve of the window |
- l.714: - **Package data.** Connector face views from the mating side, splice and marker lists, a continuity and insulation test netlist, and the IPC/WHMA-A-620 class [unverified: current edition]. MFG combines them with MEC's 1
- l.715: - **Exchange.** VEC 2.2.0 is VDA 4968 and prostep ivip PSI21, and VEC 1.1.2 absorbed KBL 2.4 features [22]. ECO's codec reads and writes VEC in phase 4, and KBL reading follows in phase 5 [unverified: current KBL version
- l.732: | SDFormat | Worlds, models, sensors, closed loops | 1.12 [unverified: latest version] |
- l.736: Collision geometry comes from `anvil::convex_decompose` with a stated Hausdorff bound, and exports carry their Change id. Kilted Kaiju is supported until November 2026, and the May 2026 ROS 2 release is Lyrical Luth [23]
- l.798: A Software item (contract section 2) records its item number, version, binary hashes, source repository and Change, toolchain, and a software bill of materials in SPDX or CycloneDX [unverified: versions].
- l.816: Commercial tools below (Allegro, Sigrity, Xpedition, HyperLynx, E3.series, Ansys, JMAG, MATLAB) are named from general knowledge; their documentation was not opened, so no claim about their internals is made [unverified]
- l.829: | Channel simulation | Statistical eye and bit-by-bit with IBIS-AMI [20][21] | Sigrity, HyperLynx | Both modes; AMI as External Ops | IEEE 802.3 reference channels [unverified]; eye height within 5% of a commercial tool 
- l.836: | Electric machines | Transient FEM with motion and loss models | Ansys, JMAG; Pyleecan with FEMM [44] | Flux maps plus transient `SignOff` (D-ELX-16) | TEAM problems [unverified]; GP6 dynamometer, ±5 points efficiency |
- l.839: | Control design | Riccati, structured H∞, conic MPC | MATLAB Control System Toolbox | Rust on `linalg`; MPC through Clarabel [49] | Closed-form cases, relative 10⁻⁹; Maros-Meszaros set [unverified] |
- l.844: | Matching networks | Real-frequency matching; Bode-Fano bound | RF circuit tools [unverified] | Synthesis with real parts and yield | Analytic L-networks to 10⁻⁶; bound never exceeded |
- l.849: - **External Ops.** IBIS-AMI models, native FMUs, emulators, Verilator, ngspice, vendor engines, robot simulators and firmware toolchains run only on Linux untrusted-evaluation workers. Every client reaches them remotely
- l.850: - **Emulator and simulator packages.** Renode publishes packages for Linux, macOS on Apple silicon and Windows [28], with ARM64 status [unverified]; MuJoCo's prebuilt binaries cover Linux on x86-64 and AArch64, Windows o
- l.855: - **Hardware access.** Bench adapters and flashing use USB and serial through `apps/platform`; browsers use WebUSB and WebSerial where available [unverified: Safari and Firefox], and a local adapter program connects to `
- l.937: | ELX-O-CTL-2 | FMU elements and bus simulation | Reference FMUs map ports and units correctly; FMI-LS-BUS reference examples [unverified: availability] |
- l.974: 2. **IPC-2581 revision.** Revision C dates from December 2020 [19], and the consortium's site names no revision [69]; a later revision is [unverified].
- l.975: 3. **Land-pattern document.** IPC's catalog pages for IPC-7351 and IPC-7352 could not be opened, so which document now applies is [unverified] (R4-42). The pinned standard package keeps either answer an explicit update.
- l.978: 6. **Vendor engines.** LTspice and PSpice terms for batch use in containers are [unverified]; D-ELX-25 offers them only where those terms allow.

## Your open questions

Close each: decide it (the reviewers propose answers above), move it to a contract change request, or keep it with the reason it cannot be decided yet.

1. **ODB++ terms.** R4-27 settles the plan: ECO builds an ODB++ writer in phase 3, and MFG offers it as a package. Siemens' page says ODB++ interfaces cost nothing and lists a partner program, but states no licence for third-party writers [18]; ECO confirms the terms before the writer ships.
2. **IPC-2581 revision.** Revision C dates from December 2020 [19], and the consortium's site names no revision [69]; a later revision is [unverified].
3. **Land-pattern document.** IPC's catalog pages for IPC-7351 and IPC-7352 could not be opened, so which document now applies is [unverified] (R4-42). The pinned standard package keeps either answer an explicit update.
4. **Licensed tables.** FIDES guides need registration [59]; SR-332, MIL-HDBK-217, the safety standards behind D-ELX-24 and the IPC class rule packs carry their own terms. Which tables may ship in std, and which stay user-licensed packages?
5. **Verilog-A front end.** The phase 1 research track decides whether a clean-room front end fits phase 3; the fallback is ported SPICE3 models plus vendor models in ngspice.
6. **Vendor engines.** LTspice and PSpice terms for batch use in containers are [unverified]; D-ELX-25 offers them only where those terms allow.
7. **Battery reference models.** The hysteresis, swelling and abuse rows need published models with test data before their phases; none was opened this round.
8. **Renode.** Determinism under multi-core and network models, and ARM64 hosts, need verification [28][62].
9. **Learned cost hints and patents.** PCBWorld does not state its corpus licence [30], and placement and routing are an active patent area; a freedom-to-operate review precedes the placer and autorouter.
10. **Data-module size.** `Schematic` and `Layout` are Ingot data modules; if very large layouts parse too slowly, ING's binary sidecar keeps their semantics and changes only the file format.
11. **ROS 2 target.** The LTS distribution to target needs confirmation from the release schedule [23].
12. **Findings declined in part.** R1-39's CUDA and ROCm route waits for the phase 4 gate decision in contract section 7.5; Vulkan `SHADER_F64` server classes serve until then.
13. **Firmware flashing outside `unattended_safe` rigs (round 3 contract request).** Contract section 7.6 names no Act for flashing a board on a bench without that policy, so a person flashes it there. Round 3 decides whether flashing becomes a physical-effect Act with an Approval over the image digest or stays manual.

## Known items

- Contract 17 rules on an Act for firmware flashing outside `unattended_safe` rigs; apply the ruling and close open question 13.
- Add one sentence under each drawn diagram that tells the reader how to read it (`diagrams/08-electronics-source-model.jsx`, `diagrams/08-electronics-analysis-dataflow.jsx`).
