# Adversarial review

Six adversarial reviewers attacked contract v3 and the twelve round 1 subsystem tabs, each from one angle, and filed 295 findings with concrete fixes. Each finding reached its target tabs through a revision packet, and contract-level findings were ruled in contract section 15. The review produced contract v4 to v5, a shared phase table and a program plan, resolved all 23 Critical findings and cut the tabs 25%.

## How the review worked

The review attacked the drafts tagged `round-1`, written against contract v3, and its six reports are tagged `review`. Every reviewer worked from one shared brief and wrote one report; `findings.json` holds all six reports parsed into one record per finding.

### The brief

The brief gave every reviewer the same rules:

- Find what is wrong, missing, inconsistent, infeasible, below the state of the art, unsafe, legally risky or tasteless. Propose a concrete fix for each, with no praise and no restatement of the drafts.
- Read contract v3 first and do not re-report its section 14 rulings. Report a ruling that is itself wrong.
- Verify load-bearing factual claims, especially those marked [unverified], with WebFetch on primary sources, and cite only pages opened. A refuted or outdated claim is a finding.
- Write 25 to 60 findings, most severe first. Each names its targets by tab code (or CONTRACT) and gives the section, the problem, the evidence and the fix.

| Severity | Definition from the brief | Findings |
| --- | --- | --- |
| Critical | Breaks a founder requirement, a principle or the architecture; a false or dangerous claim; something that cannot work as specified | 23 |
| Major | A significant gap, an inconsistency between tabs, a method clearly below the state of the art, an infeasible target, or a missing capability practitioners need | 193 |
| Minor | A local precision, wording or ordering problem | 79 |
| Total | | 295 |

### The six reviewers

Each reviewer read its primary tabs in full and the sections of other tabs its angle touched.

| Reviewer | Angle | Critical | Major | Minor | Total | Most targeted |
| --- | --- | --- | --- | --- | --- | --- |
| R1 physics | Error bounds, discretization, solvers, validity envelopes, physics coverage | 4 | 37 | 16 | 57 | FLX 42, COV 30, CONTRACT 13 |
| R2 geometry | Kernel determinism, error propagation, entity naming, blends, GD&T | 5 | 26 | 17 | 48 | ANV 40, MEC 21, ING 12 |
| R3 architecture and taste | Identity and caching, labels, Ingot–Kiln semantics, coherence and length | 4 | 41 | 10 | 55 | KLN 31, ING 27, CONTRACT 24 |
| R4 engineering practice | Shop-floor safety, CAM, drawings, PLM, board design and enterprise workflows | 4 | 27 | 11 | 42 | MFG 23, ELX 15, KLN 12 |
| R5 security and legal | Labels and prompt injection, supply chain, approvals, licences, export control, privacy | 4 | 26 | 16 | 46 | AGT 25, ECO 20, KLN 19 |
| R6 feasibility | Staffing, schedule, phase 1 scope, performance targets, platform runtimes | 2 | 36 | 9 | 47 | PLT 35, CONTRACT 17, UIX 17 |
| All | | 23 | 193 | 79 | 295 | |

### Findings by target tab

A finding may name several targets: 86 name one, 209 name two or more, and R6-02 names eleven. The columns therefore sum to more than 295. "Sole target" counts the findings that name only that tab.

| Target | Critical | Major | Minor | Total | Sole target |
| --- | --- | --- | --- | --- | --- |
| ING | 6 | 33 | 8 | 47 | 3 |
| ANV | 8 | 36 | 17 | 61 | 13 |
| FLX | 7 | 48 | 11 | 66 | 7 |
| COV | 5 | 22 | 6 | 33 | 9 |
| KLN | 12 | 59 | 8 | 79 | 3 |
| MEC | 2 | 32 | 11 | 45 | 4 |
| MFG | 3 | 28 | 10 | 41 | 11 |
| ELX | 4 | 27 | 5 | 36 | 4 |
| AGT | 7 | 24 | 11 | 42 | 9 |
| UIX | 3 | 29 | 10 | 42 | 7 |
| ECO | 1 | 37 | 10 | 48 | 8 |
| PLT | 2 | 46 | 13 | 61 | 7 |
| CONTRACT | 16 | 49 | 8 | 73 | 1 |

KLN draws the most findings: identity, caching, labels, merges and approvals all pass through Kiln and `repo`. The contract draws 16 of the 23 Critical findings, since most Critical fixes needed a new or corrected contract rule.

### From findings to revised tabs

1. **Contract v4 rules on the contract-level findings.** Section 15 names 81 findings: 20 Critical, 54 Major and 7 Minor. It covers 72 of the 73 findings that target CONTRACT; the 73rd, R3-49 (naming drift), is fixed in the tabs. Nine findings without a CONTRACT target are ruled there too (R3-03, R3-04, R4-03, R4-04, R6-08 to R6-11, R6-14), because their fixes needed contract text.
2. **Each tab gets a packet:** its round 1 edits, the v4 contract changes that affect it, and every finding that targets it, in full.
3. **One revision agent per tab applies its packet** under the revision brief. It applies every finding unless it has a sound reason and records each declined finding, with its reason, under Open questions. It never cuts a decision, oracle or source, and it passes the spec check. ANV and FLX were revised first, against v4; the other ten tabs followed against v4.2.
4. **Each revision lands as one commit.** Its message lists declined findings with reasons, decisions added and revised, and the word count.
5. **Change requests from the revised tabs are ruled** in contract v4.1, v4.2 and v5 (section 16).
6. **A consistency pass aligns every tab with contract v5:** names, shared phases, interface rows and citations of other tabs' oracles, one commit per tab.

A finding with several targets is shared. Each tab changes only what it owns and points to the owner for the rest. The contract and two or three tabs therefore often resolve one finding together.

## Critical findings

Each resolution below was checked against the committed contract and tabs, not against working copies. All 23 have a committed resolution. Four carry a stated limit in the Status column: a pending legal opinion, a declined phase move, a kept exception and a modified item.

| Id | Targets | Problem | Resolution | Status |
| --- | --- | --- | --- | --- |
| R1-01 | FLX, COV, CONTRACT | Energy-norm bounds were used to certify peak and pointwise stresses, budget totals mixed norms, and no total could ever be `Guaranteed` | Contract 5: a `Guaranteed` bound needs a proof in the quantity's norm, and bounds in different norms never combine. D-FLX-4 (revised) and D-FLX-23: peaks are regularized goals with `Estimated` bounds; rounding gets a `Guaranteed` bound γₖ | Resolved |
| R1-02 | FLX, COV, ANV, MEC, CONTRACT | The default immersed octree failed on thin walls, lattices and frames, and Flux had no beams | Contract 7.1: discretization per region, with beams, shells where t/L_local ≤ 0.2, at least four cells across any section, and beam lattices. D-FLX-12 and D-FLX-13 (revised), D-FLX-26; `anvil::mid_surface`; MEC members modelled as beams | Resolved |
| R1-03 | CONTRACT, COV, FLX, ING | Contract and COV disagreed on unquantified model-form error, so either no check could pass or the missing term counted as zero | Contract 5 `CheckOutcome`: `Pass { conditional_on }`, which meets a release gate only under a cited policy allowance, else `Undecided { reason: Unquantified }`. D-COV-4 (revised), COV-O-ERR-3; ING's decision rule lists the unquantified sources | Resolved |
| R1-04 | CONTRACT, FLX, COV | Surrogate guarantees rested on marginal conformal coverage, which optimizers break | Contract 7.1: surrogate Fields are `Estimated { confidence, scope: Marginal }`; a `SignOff` check needs a per-prediction bound or a confirming solve; weighted conformal prediction inside optimization loops. D-FLX-14 and D-COV-7 (revised); FLX-O-ROM-2 runs an adversarial optimizer | Resolved |
| R2-01 | ANV | Tolerance growth during parallel pair decisions made outcomes depend on pair order | Contract 7.1: decisions in rounds by dimension against tolerances frozen at each round's start. D-ANV-4 (revised), `ToleranceCascade` failure, ANV-O-DET-2 with shuffled orders and 1 to 64 threads | Resolved |
| R2-02 | ANV, ING, KLN, MEC, CONTRACT | Entity names hashed hidden CRDT block ids, and those names steered meshes, seeds and orders | Contract 7.1 label invariance and contract 5 text-derived `OpSite`; D-ANV-25, D-ING-21; ANV-O-LABEL-1 rebuilds every golden product with re-randomized names | Resolved |
| R2-03 | ANV, CONTRACT | Derived faces "inherited" error bounds that do not hold through offsets, intersections and blends | Contract 5 `Body`: per-face `{ position, normal }` bounds that compose by stated propagation rules or become `NotQuantified`. ANV's propagation table; ANV-O-CONV-2 | Resolved |
| R2-04 | ANV, CONTRACT | The freedom-to-operate argument ignored claim 16 of US 12,229,885 B1, which reads on the CPU path | Contract 7.1: counsel reviews claims 1, 6, 11 and 16, both paths and continuations, and SSI itself is a phase 1 release risk. D-ANV-17 (revised): every intersection point is a certified root, never a point selected from samples by a threshold | Resolved in the spec; counsel's opinion is pending (ANV open question 2) |
| R2-05 | ANV | Validity was checked only near changed entities, so far-field self-intersections passed | Contract 7.1: created and modified entities are checked for separation against the whole Body through the broad phase. ANV-O-VALID-2 | Resolved |
| R3-01 | CONTRACT, ANV, KLN, FLX | Every identity hashed names, so cross-design sharing failed and a geometry-neutral refactor voided releases | Contract 5 `GeometryId` beside `ObjectId`; contract 7.2 two-stage keys. D-ANV-24, D-KLN-26 (revised), D-FLX-6; ANV-O-CACHE-1 | Resolved |
| R3-02 | CONTRACT, KLN, AGT | Labels leaked through backdating, a one-string data class and per-package live replicas | Contract 5 label lattice; contract 7.1 label as a separate memo output and live replication per (package, label set). D-KLN-36, D-KLN-22; D-AGT-24 | Resolved |
| R3-03 | ING, KLN | `try` caught environmental failures, whose fallbacks Kiln then cached | Contract 2 Abort and 7.2: Aborts are uncatchable, propagate and are never cached. D-ING-11 and D-KLN-6 (revised); KLN-O-ABORT | Resolved; `OpVersionRetired` stays a `Failure`, as contract 7.2 rules |
| R3-04 | ING, KLN | Recursion through feature calls was unbounded, so evaluations need not terminate | Contract 7.1: a demand-depth limit (default 10,000) and a fuel governor per Evaluation, both Aborts; contract 7.2: every Evaluation terminates or aborts. D-ING-23; ING-O-24, KLN-O-LIMIT-1 | Resolved |
| R4-01 | CONTRACT, MFG, AGT, KLN | No rule stopped Crucible from starting machines remotely, and tabs disagreed on Act names and who may transfer | Contract 2 Act and 7.6 Physical safety: one named list of physical-effect Acts, and Crucible never issues cycle start, `Start` or `StoreAndStart`. Contract 7.1: `unattended_safe` is a signed site policy. D-AGT-31, MFG-O-SAFE-3, D-KLN-35 | Resolved; the Acts stay in phase 2 with CAM and slicing, not phase 1 |
| R4-02 | MFG | Collision checks simulated the toolpath, not how the control moves between programmed points | D-MFG-23: simulation and the independent re-interpreter execute the posted NC text under the controller's declared `MotionSemantics`; undeclared semantics sweep a conservative envelope or report `Unsupported`. MFG-O-SIM-2; phase 2, with CAM | Resolved |
| R4-03 | ELX, KLN | Set-union `connect` let two clean branches merge into a silent short | Contract 7.1 `repo`: connectivity merge condition. KLN's `Conflict::NetMerge`; D-ELX-21: named nets join only through an explicit `tie`; ELX-O-NET-2 | Resolved |
| R4-04 | UIX, ELX | Schematic and layout editors had no workable home in the UI | Contract 7.6: Electronics preset and the public `crucible:ui/canvas2d` world, with per-pointer tools on an interactive edit lane. D-UIX-27, UIX-O-CANVAS-1; Altium-like and KiCad-like presets (D-UIX-20) | Resolved |
| R5-01 | AGT, KLN, CONTRACT | Agent model contexts carried no label, so content read under one label could be written down into another repository | Contract 7.6 context labels and write-down. D-AGT-24: `label.write_down` unless a declassification record names the write; untrusted typed values travel by `ValueRef`. D-KLN-32 | Resolved |
| R5-02 | AGT, KLN, ING, CONTRACT | Human merges endorsed agent-written free text, which then instructed later sessions and the verifier | Contract 7.6: free text is never endorsed by merging; contract 7.1: span-level integrity provenance. D-ING-24, KLN-O-SPAN-1; D-AGT-12: the verifier reads a typed view with the author's free text elided | Resolved |
| R5-03 | KLN, CONTRACT, AGT, FLX, ELX, COV | Machines that ran untrusted Proposals and native External Ops also signed shared-cache attestations | Contract 7.8: two worker pools, a separate attestation service, two-builder agreement for release gates and `SignOff` checks, operator-only writes to the public domain. D-KLN-9 (revised); D-FLX-30 and D-ELX-12 keep native code on untrusted-evaluation workers | Resolved |
| R5-04 | AGT, UIX, KLN, CONTRACT | Approval URLs passed through the agent's channel, any approver could approve, and three approval surfaces existed | Contract 7.6 Act approvals: assigned approvers, no URL ever returned to a model, one server-generated page, WebAuthn, no approval on phones. D-AGT-20 (revised), D-UIX-29 | Resolved |
| R6-01 | CONTRACT, PLT | No duration, headcount or critical path; phases 0 and 1 as written needed about 465 engineer-years | Contract 13.2 program plan: phase 0 in 12 months (20 → 59 people, about 40 engineer-years), phase 1 in 24 months (59 → 100, about 160), gate at month 36, agent swarms at most 1.5×. PLT points to it for staffing | Resolved |
| R6-02 | CONTRACT, ANV, FLX, ING, KLN, UIX, MFG, ECO, AGT, PLT, ELX | Phase 1 carried work that neither GP1 nor GP2 needs | Contract 13.2 phase 1 scope with named deferrals. In the tabs: D-ING-13 (the interpreter is the only executor), D-UIX-24 (one forward renderer), KLN's single-node team server, MFG's CAM in phase 2, ECO's signed first-party index | Resolved; phase 1 keeps three agent roles, not two |

## Major and Minor findings by theme

The 193 Major and 79 Minor findings fall into seventeen themes. Each finding counts once, under the theme of its main problem. The fixes named in each theme are representative, and each was checked in the committed text.

| Theme | Major | Minor | Total |
| --- | --- | --- | --- |
| Identity, names and cache keys | 12 | 3 | 15 |
| Error bounds and check semantics | 12 | 3 | 15 |
| Validity envelopes, evidence and physics coverage | 10 | 4 | 14 |
| Physics methods | 13 | 4 | 17 |
| Geometry, modelling, drawings and tolerancing | 12 | 14 | 26 |
| Determinism and numerics | 16 | 6 | 22 |
| Language, Kiln and `repo` semantics | 16 | 2 | 18 |
| Manufacturing practice and machine safety | 11 | 6 | 17 |
| Electronics practice | 4 | 1 | 5 |
| PLM and enterprise integration | 8 | 1 | 9 |
| Security | 16 | 10 | 26 |
| Legal, licensing, privacy and compliance | 10 | 6 | 16 |
| Feasibility, staffing and phasing | 14 | 1 | 15 |
| Performance targets and platform support | 19 | 6 | 25 |
| Spec form, length and names | 10 | 7 | 17 |
| Interop and formats | 9 | 1 | 10 |
| UI and rendering practice | 1 | 4 | 5 |
| Total | 193 | 79 | 272 |

### Identity, names and cache keys (15)

The reviewers found names that moved under ordinary edits. Slot paths renamed every stage when one was appended, iteration was positional, rank selectors switched entities silently, and imports were named by ordinals. Keys also still carried names where the contract promised sharing.

- **Call sites from text.** `OpSite` frames name calls by name and occurrence and iterations by key (contract 5; D-ING-21; R2-06, R2-12, R3-06).
- **Fragile selectors.** Rank selectors need a provenance anchor or role filter first, else `ING-L-FragileSelector` (contract 5 `Query`; R2-22). Extent references fail on a merge unless `on_merge: Accept` is written (R2-32).
- **Complete keys.** Every node whose value carries `EntityId`s keys on its `OpSite`, and geometric stages key on `GeometryId`s (contract 7.2; R3-05, R2-10). The key also holds the effective fidelity (R3-11).
- **Copies and imports.** Placement keeps names and copies derive names with role `copy` or `mirror` (D-ANV-30; R2-11). Imports are named from source persistent ids or exact signatures, never ordinals (D-ANV-31; R2-21).

### Error bounds and check semantics (15)

Four tabs gave four rules for deciding a check, and `ErrorBudget` had three incompatible shapes. The canonical example checked a peak stress next to a clamped face, where linear elasticity makes stress singular.

- **One rule, one shape.** ING owns the single decision rule behind `Truth` (D-FLX-15; R3-07). `ErrorBudget` has one shape, with `NotQuantified` parts (contract 5; R3-08, R1-08).
- **Singular points.** Point quantities at re-entrant edges, clamped patches and material changes are `Undecided { SingularPoint }`, unless the check excludes a stated distance (contract 7.1; R1-05, R3-09).
- **Consumers never change producers.** Adaptivity goals are explicit study inputs, so adding a check does not change a solve's key (D-FLX-5, revised; R3-10).
- **Fixed calibration.** Every `Estimated` bound carries the calibration factor η99 of its estimator class, pinned in `ingot.lock` (D-FLX-24, D-COV-17; R1-14, R1-07).

### Validity envelopes, evidence and physics coverage (14)

The validation framework lacked a solid-mechanics standard and a metric. Envelope bounds were prose, E2 models had no calibrated zone, and the coverage matrix claimed methods no package backs.

- **Validation metric.** ASME V&V 10, the V&V 20 metric, extrapolation inflation and replicate counts govern every physical gate (contract 13.1; D-COV-20; R1-29).
- **Solution verification.** Each result carries its solution-verification status, and methods without an estimator report `Indicator` unless solution verification runs (D-COV-21, D-FLX-34; R1-28).
- **Computable envelopes.** Every regime variable is a typed Ingot function; a condition that cannot be computed is an `Assumption` (D-COV-18; R1-31).
- **Coupling limits.** One-way fluid–structure coupling requires stated mass-ratio and frequency conditions (D-COV-19; R1-27).

### Physics methods (17)

Several methods were below the state of the art for the golden products. Smoothers failed on cut cells, Navier–Stokes preconditioners suited only Stokes flow, and antennas went to FDTD.

- **Electromagnetics.** Resonant problems use frequency-domain Nédélec FEM with port eigenmodes and PML (D-FLX-32; R1-22).
- **Flow.** PCD and augmented Lagrangian preconditioners (D-FLX-33; R1-23); patch smoothers and aggregation around cut cells (D-FLX-16, revised; R1-17).
- **Nested models.** Battery particles, FE² and radiation are forms over product spaces with a parameter measure (D-FLX-38; R1-24).
- **Tangents.** Kernel-IR models get tangents by algorithmic differentiation with `local_solve`; opaque models pass a Taylor-test oracle (contract 7.4; R1-25).

### Geometry, modelling, drawings and tolerancing (26)

Phase 1 blends were too narrow for real corners, and tangential contact after blends had no treatment. Lattice joins lost B-rep faces, and the GD&T record could not express daily constructs. This theme holds the most Minor findings, mostly local precision in Anvil and MEC.

- **Blends.** A staged program whose stage 1 covers sequential fillets, `RollOver` and valence-3 corners with setbacks (contract 7.1). One re-fillet benchmark measures every stage (D-ANV-29; R2-07).
- **Tangency.** `Continuity` certificates on constructed edges and a certified contact-curve algorithm (D-ANV-26; R2-08).
- **Mixed Bodies.** Leaf-preserving conversion keeps exact faces and their `EntityId`s (contract 5 `Body`; R2-14).
- **Tolerancing.** MEC owns one default distribution (D-MEC-28; R1-37), and toleranced faces that a later operation splits fail with `ToleranceTargetSplit` (D-MEC-27; R2-18).

### Determinism and numerics (22)

WGSL lets compilers reassociate and flush, and faer picks block sizes at run time. Banning FMA halves throughput, and the merge queue promised more than 45 minutes allow.

- **GPU semantics.** WGSL kernels never claim bit-identity with CPU kernels (contract 7.5; R1-09).
- **Canonical linear algebra.** One `linalg` crate with fixed blocking, canonical lane order and no FMA (contract 7.1; D-FLX-36, D-PLT-34). faer runs only in `CpuIsa` (R1-10, R6-21).
- **FMA and vector width.** `CpuIsa` variants with FMA serve `Preview` and `Interactive`; the canonical lane order binds horizontal operations only (contract 7.3; R6-17, R6-18).
- **Cheaper determinizing.** NaN canonicalization only where bits become observable, and cancellation only at fuel checks (contract 7.4; R6-20, R3-21, R6-36).
- **Agreement.** Two classes agree when their difference lies within the sum of their error budgets (D-PLT-35; R1-12, R1-13).

### Language, Kiln and `repo` semantics (18)

Merges could pass while breaking a check, rebases voided approvals, measurements had no identity, variants and derivatives had no owner, and rotation was ill-typed.

- **Merges.** Six merge conditions, among them a verdict order over parents and a connectivity condition (contract 7.1 `repo`; D-KLN-21, revised; R3-15).
- **Approvals.** Approvals sign an `ApprovalSubject` built on `GeometryId`s, so rebases and CI re-runs leave them valid (contract 5; D-KLN-28, revised; R3-16). Measurements are Evidence records (contract 2; R3-17).
- **Variants and derivatives.** `#[configuration]` parameters (D-ING-22, D-KLN-27; R3-18); a Kiln derivative traversal (D-KLN-37; R3-19).
- **Types.** A strong angular system (contract 5; R3-29) and one `Scalar<D>` trait over four flavors (D-ING-20; R3-31).

### Manufacturing practice and machine safety (17)

Approval binding ended at the handover to the control, and there was no setup sheet. Shops could not verify legacy NC programs, and the wedge assumed Crucible's own slicer.

- **Handover checks.** Posts write a content hash into the program header, and the gateway checks it on transfer and read-back (D-MFG-24; R4-05).
- **Verify any program.** A product NC interpreter verifies programs from any CAM or hand programming (D-MFG-28; R4-09).
- **Wedge printing.** Phase 1 hands builds to the user's slicer as a 3MF build (D-MFG-25; R4-13).
- **Shop data.** Feeds and speeds default to vendor or shop values (D-MFG-27; R4-36); balloon labels are allocated once per characteristic (D-MFG-26; R4-14).

### Electronics practice (5)

Board designers' vocabulary and workflows were missing: stored schematic topology, encrypted vendor models, fabrication classes and end-product safety standards.

- **Schematics.** A schematic is a stored drawing that the blocking check `schematic_matches_network` proves equal to the code (D-ELX-1, revised; R4-22).
- **Vendor models.** Imported models run in ngspice by default until they match on their own bench (D-ELX-25; R4-23).
- **Classes and safety.** Boards declare fabrication and assembly classes (D-ELX-23; R4-25); creepage comes from a declared isolation barrier under its end-product standard (D-ELX-24; R4-26).

### PLM and enterprise integration (9)

Crucible assumed it was every customer's system of record, shops had no fast path for program changes, and engine upgrades could mark released Items modified.

- **Records.** Each record type has a system of record, `Crucible` or an external connector (D-KLN-39; R4-19).
- **Change orders.** Manufacturing change orders are their own policy class (D-KLN-38; R4-11).
- **Revisions.** Revision identity compares Item definitions within a definition tolerance (D-KLN-26, revised; R4-17); revision markers come from the release diff (D-MEC-29; R4-16).
- **Enterprise.** ERP, MES and PLM connector worlds (D-ECO-30; R4-18); an organization parts policy (D-ELX-22; R4-20).

### Security (26)

Third-party code ran inside the engine process, and data left a tenant through at least six paths with different controls. Single people held the most consequential settings, and signatures had no post-quantum path.

- **Isolation.** Every third-party Wasm component runs out of process on every target (contract 7.4; D-ECO-26, D-PLT-31; R5-09). Browsers use one first-party runtime with no JavaScript per Wasm component (D-PLT-36; R5-12).
- **One exit.** Every byte that leaves a tenant goes through the `release_data` Act family (D-AGT-30, D-KLN-40, D-ECO-28; R5-05, R5-06).
- **Two people.** Clearances, declassification and access-widening policy changes need two distinct approvers (D-KLN-41, D-AGT-27; R5-15).
- **Untrusted text and images.** Package text is always `ExternalText` (D-ECO-32; R5-13). External hosts get typed extracts, not raw text (D-AGT-25; R5-07). Snapshots of untrusted Assets are untrusted (D-AGT-26; R5-17).
- **Egress and signatures.** Content labelled above `internal` leaves the organization in notifications and emails only as ids and generic text (D-UIX-28, D-PLT-38; R5-16). Post-quantum dual signing starts in phase 2 (contract 7.8; D-KLN-42, D-PLT-37; R5-23).

### Legal, licensing, privacy and compliance (16)

The name Flux collides with an existing electromagnetic simulator, and the patent owner was misnamed. Support terms were too short for regulated programmes, and several privacy rules were missing.

- **Names and patents.** Flux is renamed in phase 0, before any operation name or WIT package freezes (contract 2, 13.1; R5-19). The patent is attributed to its inventor (contract 7.1; R5-31).
- **Regulated customers.** A 10-year LTS line every two years and a regulated cloud mode (contract 7.7; R5-20). The MPL obligation is stated exactly (contract 7.7; R5-32).
- **Export and contributions.** Export classification of every distributable (D-ECO-29; R5-22). Agents never sign off under the DCO, agent-assisted commits carry an `Assisted-by` trailer, and a similarity scan runs (D-ECO-21, revised; ECO-O-30; R5-26).
- **Privacy.** Pseudonymous principal ids with crypto-shredding (D-KLN-43, D-AGT-32; R5-27). One opt-in telemetry pipeline (D-PLT-39, D-UIX-22; R5-29). Shipped models train only on procedural data, std, golden products, commercially licensed data and opted-in customer data (D-AGT-22; R5-28, R5-33).

### Feasibility, staffing and phasing (15)

No tab stated teams or hiring order, and phases contradicted each other across tabs. Phase 1 built two renderers, a code generator and an own toolkit for a single-Part wedge.

- **Plan.** Contract 13.2 sets staffing, first hires and two critical-path chains (R6-03, R6-04). GP1 is made with the shop's own CAM (R6-05), and later phases are sized (R6-34).
- **Narrower phase 1.** Kernel IR v0 freezes at month 6 with only phase 0 and 1 constructs (contract 7.5; R6-22). Phase 1 has one forward renderer (D-UIX-24; R6-24), and the interpreter is the only Ingot executor (D-ING-13; R6-25).
- **Shared phases.** One phase per shared capability in contract 13.4 (R1-35, R2-27); the harness split between MEC, ELX and MFG (D-MEC-26; R4-30).
- **Dependencies.** A risk register for every core dependency (D-PLT-40; R6-30).

### Performance targets and platform support (25)

Contract v3 had no performance targets and no reference machine, and several rows could not hold as worded. R6-12 found Wasmtime rating two of Crucible's Tier 1 targets below its own Tier 1.

- **Targets.** Contract 13.3 fixes the reference laptop, the drag preview rule, scene capacity per tier and fidelity per rebuild row (R6-07 to R6-11, R2-09). Motion renders at most 2.1 MP (D-UIX-25; R6-10).
- **Runtimes.** Tier 1 preview for one phase (contract 9; R6-06, R6-31); Wasm inside WebKit on iPadOS (D-PLT-33; R6-13).
- **Browsers.** One engine per origin (D-PLT-29, D-KLN-44; R6-15) and a disposable heavy worker for large evaluations (D-PLT-30; R6-14).
- **Scheduling.** One GPU dispatch rule (D-PLT-32; R6-16), and admission at the priced upper bound (D-AGT-29; R6-29). Physics shows as `Proxy` during geometric drags until phase 3 (D-FLX-37; R1-16).

### Spec form, length and names (17)

Eleven of the twelve round 1 tabs exceeded their word cap, two by more than half. The tabs used four layouts for capabilities, and six tabs each listed the sources of nondeterminism.

- **One skeleton.** One capability table at the end of every design section (contract 11; R3-36).
- **Say it once.** Contract 7.3 states the determinism mechanisms once and names PLT their owner (R3-37).
- **Length.** Every tab is now within its cap; the length table below gives the numbers (R3-38 to R3-45, R3-52 to R3-55).
- **Names.** Repository states are Changes (`ChangeRef` in AGT), and CAM steps are workingsteps in UIX. The software bill of materials is spelled out (R3-49, R4-37).

### Interop and formats (10)

Two or three tabs specified the same formats with different versions and phases: FMU and SSP, board outputs, ODB++ and the event envelope.

- **One owner each.** Flux owns the FMI and SSP runtime (D-FLX-30; R3-24). IPC-2581C with Gerber X2 is the default fabrication package, and ODB++ comes from ECO's own writer in phase 3. MFG chooses the package per fabricator; ECO owns every writer (D-MFG-16, revised; R3-25, R4-24, R4-27).
- **One event envelope.** Events carry identifiers and states, never design content, in ECO's CloudEvents envelope (D-KLN-34, revised; R3-23).
- **ECAD migration.** KiCad's importers run as an external tool, then Crucible's KiCad reader (D-ECO-31; R4-28).

### UI and rendering practice (5)

The reviewers found flicker in X-ray views, soft small text on 1080p displays and missing navigation presets.

- **Transparency.** Phase 1 uses weighted blended transparency. From phase 2 a k-buffer keys layers by depth plus an Instance and face hash and breaks ties by `EntityId` (D-UIX-11; R6-27).
- **Text.** Bundled fonts with grayscale antialiasing, hinted below UI scale 1.5 (D-UIX-4; R6-43).
- **Presets.** Navigation presets add NX, Creo, Inventor, Altium and KiCad (D-UIX-20, revised; R4-39).

## Declined and partly applied findings

Every tab applied its packet. The tables list each finding a tab moved to a later phase, declined in part, applied in part or left to its owner. Each row gives the reason stated under Open questions or in the commit message.

### Moved to a later phase

Contract 13.2 defers CAM, posts, stock simulation and slicing to phase 2, and GP1 uses the shop's own CAM. Findings that asked for these in phase 1 land in phase 2.

| Finding | Tab | What moves | Stated reason |
| --- | --- | --- | --- |
| R4-01 | AGT, MFG | `send_to_machine`, `send_print_job` and `start_print` stay in phase 2 rather than phase 1 | The Acts ship with the effects they govern, which contract 13.2 defers |
| R4-05 | MFG | DNC | Contract 13.2; AGT adds that program headers, offset checks and DNC belong to MFG |
| R4-06 | MFG, UIX | Setup sheet and its preview | Arrives with CAM |
| R4-07, R4-08 | MFG | 3+1 indexing, vises, probing; Ingot hooks for posts | Arrives with CAM and posts |
| R4-09, R4-10 | MFG, ECO | `verify_nc`, migrated NC programs, tool importers and tool-data readers | Arrives with CAM |
| R4-12 | MFG, UIX | Edge-break toolpaths, toolpath playback and the NC code panel; agent-proposed programs | Arrives with CAM; UIX moves the cost panel to phase 1 instead |
| R4-35 | MFG | Each added controller family | One phase later than proposed, for the same reason |
| R4-14 | MEC | Characteristic balloons | Follow MFG's characteristic extraction into phase 2; phase 1 drawings carry item balloons |
| R4-29 | ECO, ELX, MEC | IDF read and STEP board import | An early 1.x train in phase 2, since phase 1 holds only what GP1 and GP2 need; ELX and MEC follow ECO's phase after the consistency pass |
| R2-19 | MEC | Form sampling per GD&T dialect | Needs skin model shapes, which arrive in phase 4 |
| R1-16 | FLX | Morphing reduced models during geometric drags | Phase 3; `Proxy` results before then |
| R1-40 | COV | Pseudo-4D battery packs | Phase 6 with ELX's pack-scale DFN; DFN cells are phase 5 (contract 13.4) |
| R1-39 | ELX | Monte Carlo batches on CUDA or ROCm | Wait for the phase 4 back-end decision (contract 7.5); Vulkan `SHADER_F64` server classes serve until then |

### Declined in part

| Finding | Tab | What is declined | Stated reason |
| --- | --- | --- | --- |
| R1-43 | FLX, PLT | Routine `SignOff` in `CpuIsa` with FMA | Contract 7.3 requires canonical recomputation for `SignOff` |
| R1-21 | FLX | GPU element-cycle targets at `SignOff` | Explicit trajectories have no cheap canonical certificate, so the targets apply at `Interactive` only |
| R2-06 | ING, KLN | CRDT identities for calls inside `OpSite` | Contract 5 derives call identity from name and occurrence, stable when stages are appended or wrapped |
| R3-03 | KLN | Making an unavailable retired version an Abort | Contract 7.2 keeps `OpVersionRetired` a `Failure`; archived Wasm builds make retired versions available everywhere |
| R3-20 | KLN | Per-build signing keys | Replaced by contract 7.8's attestation service bound to workload identity |
| R3-33 | ING | One instance per worker with state machines | Applies to the deferred code generator; the interpreter isolates through heap frames |
| R3-47 | ING | A Pulley fallback for Ingot | Ingot runs on the interpreter on iPadOS, so the fallback concerns Wasm components only |
| R6-33 | ING | Speed ratios for Wasm components and user forms | ING sets only its own ratios; PLT, ECO and FLX own the others |
| R5-18 | MFG, AGT | Renaming `send_to_machine` to `queue_program` | R4-01's shared list names `send_to_machine`; R5-18's meaning (delivery only, start at the machine) is adopted |
| R3-25 | MFG | ODB++ through a licensed external tool | R4-27's own writer, which ECO builds, replaces it |
| R4-24 | MFG | Output writers in MFG | Writers stay ECO's under R3-25 and contract 7.7; MFG chooses the package |
| R6-02 item 6 | AGT, contract | Two agent roles in phase 1 | Contract 13.2 names three: detail designer, simulation engineer and verifier |
| R3-53 | AGT | Retitling the tab | The brief fixes the title line and the README keys on it; the rest is applied |
| R3-41 | UIX | Eight design sections | Ten sections, so each capability table covers one coherent area |
| R5-25 | ECO | A foundation at phase 0 | Contract 7.7 sets company stewardship until a trigger; a 36-month backstop, trademark escrow and a key ceremony make the trigger binding |
| R1-33 | COV | Superconductors as a coverage row | Listed out of scope (OOS-3) instead |
| R1-35 | Contract | DFN batteries in phase 4 | Phase 5, because no gate names DFN; GP6 uses equivalent-circuit and SPMe cells (contract section 16) |

### Applied in part, or left to the owning tab

| Finding | Tab | What the tab applied | Owner of the rest, or reason |
| --- | --- | --- | --- |
| R2-36 | ANV | The implicit fallback states its deviation per instance by certified measurement | Not as a closed form in the radius, since the departure from a circular section depends on the dihedral angle |
| R1-16 | ANV | Anvil's two stage budgets | Flux owns the other stages and the morphing-versus-`Proxy` choice |
| R6-32 | ANV | The section-stack target | Direct slicing is MFG's, in phase 2 |
| R2-09, R2-26 | ANV | Anvil's part | Item 5 of R2-09 and R2-26's text layout belong to MEC |
| R1-02, R1-18, R1-19, R1-35, R1-38, R1-57, R2-15, R2-44, R6-42 | ANV | Anvil's part of each shared finding | The owning tabs |
| R2-18 | ING | ISO 5458 and 2692 dialect modules and the `Fail` split policy | The extended GD&T record is MEC's |
| R1-01, R1-02, R1-04, R1-07, R1-08, R1-21 to R1-25, R3-08, R5-03 | COV | COV's rows, envelopes and records | The machinery is FLX's or the contract's |
| R1-32 | COV | The tab's matrix shows planned phases | Status lives in the generated map |
| R1-36, R1-39 | COV | The uncertainty representation and precision classes | FLX owns the methods; ELX restates its Monte Carlo target |
| R1-41, R1-54 | COV | The models and envelopes | MFG owns the capabilities (contract 13.4) |
| R3-55 | COV | "Coverage by category" became a column of the out-of-reach list | Scope lives in contract 13.1 |
| R1-10, R1-36, R2-09, R2-36, R6-11 | MEC | Canonical solver algebra, grouped contributors, the drawing target, fallback notes, capacity rows | ANV, PLT, FLX and UIX own the rest |
| R3-30, R3-31 | MEC | Consequences in Tolerancing and Sketching | ING owns `Tol<T>` keying and the `Scalar` flavors (D-ING-20) |
| R4-25, R4-14, R1-37, R4-18, R5-05, R5-06 | MFG | MFG's side of each | ELX, MEC, ECO, KLN and AGT own the rest |
| R2-24 | PLT | No PLT change | MFG owns gouge detection, and PLT's 1 GiB memory row stands (commit message) |

The consistency pass settled the two points the revisions left open. ELX and MEC now phase board import in phase 2 with ECO's readers, and FLX moved its shared physics to the phases of contract 13.4. MEC still marks two facts [unverified]: the ISO 19005 part for PDF/A (R4-16) and the source of the Bender inflation factor (R1-37).

## What the review changed

Rules that several tabs had stated differently moved into the contract once, and the tabs replaced their restatements with pointers. The contract nearly doubled, from 7,491 to 14,022 words, while the twelve tabs lost about 71,700 words.

### In kind

1. **Names never steer geometry.** Every Body has a `GeometryId` beside its `ObjectId`, `OpSite`s come from source text, and operations are invariant under renaming.
2. **Bounds claim only what a proof gives.** A `Guaranteed` bound needs a proof in its own norm, and peaks are regularized goals. An unquantified part makes a `Pass` conditional.
3. **Trust follows data.** Labels form a lattice and travel with model contexts, merges never endorse free text, and only trusted builders feed attestations.
4. **Crucible never starts motion.** Physical-effect Acts transfer data or start a print or rig test under stated conditions; a person starts machines at the device.
5. **Phase 1 is a wedge.** It holds only what GP1 and GP2 need, under a program plan with headcount, engineer-years and a critical path.

### Contract versions

| Version | Marked by | What it rules | Words |
| --- | --- | --- | --- |
| v3 | Tag `round-1` | The first drafts' change requests and cross-tab conflicts (section 14): three-valued checks, `Approx<T>` and `Tol<T>`, product-domain Fields, External Op and External input, `Network`, `crucible:ops`, platform classes. This is the text the review attacked | 7,491 |
| v4 | Tag `contract-v4` | Section 15, on 81 review findings: two identities and label invariance; the label lattice and context labels; Aborts and evaluation limits; error bounds and `CheckOutcome`; surrogates and per-region discretization; Act approvals and physical safety; cache trust; numerics rules; the Ingot executor and iPadOS; the program plan, performance targets and Tier 1 preview | 12,388 |
| v4.1 | Commit "Contract v4.1" | CCR-ANV-7 (fidelity per rebuild row and a `SignOff` recertification row), CCR-ANV-8 (unpropagated bounds become `NotQuantified`), CCR-FLX-8 (a `regularization` error source) | 12,562 |
| v4.2 | Commit "Contract v4.2" | CCR-FLX-9 and R1-35: the shared phase table, section 13.4 | 13,183 |
| v5 | Commit "Contract v5" | All 21 requests from the ten tabs revised against v4.2: `Pending` branches, phase and angular frequency, `OpSite` frames, `RenderProfile`; Model level, Evidence level and Item; the merge verdict order; one list of physical-effect Acts and `unattended_safe` as a site policy; no Act approvable on a phone; third-party Wasm components out of process; signature agility; two battery rows in 13.4 | 14,022 |

Section 16 records 25 accepted requests in 23 rows, because two pairs of overlapping requests are ruled together. No request filed in round 2 was declined.

### The shared phase table

Round 1 tabs phased shared physics differently (R1-35). Modal analysis was phase 1 in COV and phase 2 in Flux; fibre orientation was phase 3 in COV and phase 4 in MFG. Contract 13.4 now sets one phase for each capability that several tabs phase.

- **Rule.** A capability lands in the phase of the first gate that needs it. One that no gate needs takes the latest phase any tab proposed. A tab that needs a different phase files a change request.
- **Ownership.** The owner's capability table specifies the capability; every other tab states the phase in one line and cites 13.4.
- **Size.** 21 rows in v4.2 and 23 in v5. CCR-ELX-8 added battery swelling and stack pressure (phase 4) and battery abuse mechanics (phase 6). Three neighbouring capabilities keep their own tab's phase.
- **R1-35.** Its proposed phases hold except DFN battery cells, which go to phase 5 rather than 4 because no gate names them. GP6 uses equivalent-circuit and SPMe cells.

| Phase | Rows | Owners |
| --- | --- | --- |
| 1 | 2 | FLX 2 |
| 2 | 2 | FLX 1, MFG 1 |
| 3 | 5 | FLX 2, MFG 3 |
| 4 | 7 | FLX 3, ELX 2, MEC 1, MFG 1 |
| 5 | 5 | FLX 2, COV 2, MFG 1 |
| 6 | 2 | ELX 1, MFG 1 |
| Total | 23 | FLX 10, MFG 7, ELX 3, COV 2, MEC 1 |

FLX v2 predated the table. Its consistency pass moved electro-thermal coupling and FMU export with SSP to phase 4, and DFN cells to phase 5.

### Length

R3-38 to R3-45 and R3-52 to R3-55 measured eleven of twelve round 1 tabs over their caps. The table gives each tab's whole-file count (`wc -w`) and its count excluding Sources, which is what the check measures and the cap limits.

| Tab | Round 1, whole file | v2, whole file | Round 1, excluding Sources | v2, excluding Sources | Change |
| --- | --- | --- | --- | --- | --- |
| ING | 30,733 | 20,151 | 30,303 | 19,721 | −35% |
| ANV | 32,974 | 20,956 | 32,040 | 19,964 | −38% |
| FLX | 22,646 | 18,523 | 22,244 | 17,998 | −19% |
| COV | 17,905 | 18,451 | 17,450 | 17,932 | +3% |
| KLN | 25,971 | 18,556 | 25,499 | 17,985 | −29% |
| MEC | 19,936 | 18,438 | 19,646 | 17,997 | −8% |
| MFG | 24,216 | 18,403 | 23,874 | 17,955 | −25% |
| ELX | 23,744 | 18,169 | 23,155 | 17,520 | −24% |
| AGT | 22,830 | 18,543 | 22,335 | 17,919 | −20% |
| UIX | 26,057 | 18,399 | 25,670 | 17,980 | −30% |
| ECO | 24,879 | 18,817 | 24,336 | 17,992 | −26% |
| PLT | 24,434 | 18,509 | 24,061 | 17,958 | −25% |
| Total | 296,325 | 225,915 | 290,613 | 218,921 | −25% |

ING and ANV fit their 20,000-word cap and the other ten fit 18,000. COV is the only tab that grew: it started within range, and its fixes added seven decisions and twenty oracles. The cuts removed restatement, not substance: compared with `round-1`, no decision, oracle id or source link is missing.

### Oracle ids

Only ING, ANV and MEC used `<TAB>-O-` ids in round 1. The other nine tabs used other ids, paths, plain names or no ids, and several oracle tables carried a phase column. Every v2 tab defines each oracle once, as a `<TAB>-O-<name>` id with what it verifies and its pass criterion (contract 11).

| Tab | Round 1 form | v2 ids |
| --- | --- | --- |
| ING | `ING-O-n` | 36 |
| ANV | `ANV-O-…` | 129 |
| FLX | Named rows without ids | 77 |
| COV | `cov/…` paths | 40 |
| KLN | `kiln/…` paths | 66 |
| MEC | `MEC-O-…` | 82 |
| MFG | Named rows without ids | 117 |
| ELX | Suite names such as `connectivity` and `erc` | 60 |
| AGT | `O-AGT-n` | 24 |
| UIX | `uix_…` names | 51 |
| ECO | `O-ECO-n` | 33 |
| PLT | Named rows without ids | 53 |
| Total | | 768 |

The commit messages record how the old names map:

- AGT and ECO renamed `O-AGT-n` and `O-ECO-n` to `AGT-O-n` and `ECO-O-n`.
- UIX maps its `uix_` oracles one to one onto `UIX-O-` ids.
- COV's 20 `cov/` oracles and KLN's path-named oracles became `COV-O-` and `KLN-O-` ids.
- PLT's 20 unnamed oracles gained ids, and MFG's 117 ids are all new.

The consistency pass updated every citation of another tab's oracle; the old names survive only in the notes that map them.

### Decisions

Decision numbers are stable. A changed decision keeps its number and ends with "(revised in round 2)"; a new one takes the next free number. The table counts decisions in each tab's committed text.

| Tab | Round 1 | v2 | Added | Revised | URLs under Sources |
| --- | --- | --- | --- | --- | --- |
| ING | 19 | 25 | 6 | 10 | 68 → 68 |
| ANV | 23 | 31 | 8 | 12 | 68 → 74 |
| FLX | 22 | 38 | 16 | 18 | 43 → 56 |
| COV | 16 | 23 | 7 | 10 | 60 → 65 |
| KLN | 35 | 44 | 9 | 19 | 66 → 80 |
| MEC | 25 | 30 | 5 | 13 | 46 → 59 |
| MFG | 21 | 29 | 8 | 8 | 65 → 78 |
| ELX | 20 | 26 | 6 | 14 | 59 → 64 |
| AGT | 23 | 32 | 9 | 11 | 54 → 65 |
| UIX | 23 | 30 | 7 | 13 | 69 → 72 |
| ECO | 25 | 32 | 7 | 10 | 69 → 96 |
| PLT | 28 | 40 | 12 | 14 | 66 → 89 |
| Total | 280 | 380 | 100 | 152 | 733 → 866 |

FLX added the most decisions: the fixes for R1-01 and R1-02 and most physics-method findings land there, for example D-FLX-23, D-FLX-26, D-FLX-32 and D-FLX-33. KLN revised the most, since identity, labels, merges, approvals and cache trust each changed an existing KLN decision.

## Sources

| Source | Link |
| --- | --- |
| Review brief | [../review/brief.md](../review/brief.md) |
| R1 physics review | [../review/R1-physics.md](../review/R1-physics.md) |
| R2 geometry review | [../review/R2-geometry.md](../review/R2-geometry.md) |
| R3 architecture review | [../review/R3-architecture.md](../review/R3-architecture.md) |
| R4 practice review | [../review/R4-practice.md](../review/R4-practice.md) |
| R5 security and legal review | [../review/R5-security-legal.md](../review/R5-security-legal.md) |
| R6 feasibility review | [../review/R6-feasibility.md](../review/R6-feasibility.md) |
| All 295 findings, parsed | [../review/findings.json](../review/findings.json) |
| Contract v5: glossary (2), core types (5), decided architecture (7), platforms (9), taste (10), writing rules (11), roadmap, plan, targets and shared phases (13) | [../contract.md](../contract.md) |
| Contract ruling logs: round 1 (14), adversarial review (15), revised tabs (16) | [../contract.md](../contract.md) |
| Revision brief | [../revision/brief.md](../revision/brief.md) |
| Consistency pass brief | [../revision/consistency.md](../revision/consistency.md) |
| Revision packets | [ING](../revision/packets/ING.md), [ANV](../revision/packets/ANV.md), [FLX](../revision/packets/FLX.md), [COV](../revision/packets/COV.md), [KLN](../revision/packets/KLN.md), [MEC](../revision/packets/MEC.md), [MFG](../revision/packets/MFG.md), [ELX](../revision/packets/ELX.md), [AGT](../revision/packets/AGT.md), [UIX](../revision/packets/UIX.md), [ECO](../revision/packets/ECO.md), [PLT](../revision/packets/PLT.md) |
| Revised tabs | [ING](01-ingot.md), [ANV](02-anvil.md), [FLX](03-flux.md), [COV](04-coverage.md), [KLN](05-kiln-repo-plm.md), [MEC](06-mechanical.md), [MFG](07-manufacturing.md), [ELX](08-electronics-systems.md), [AGT](09-agents.md), [UIX](10-ui.md), [ECO](11-interop-ecosystem.md), [PLT](12-platform-performance.md) |
| Round 1 drafts and contract v3 | Git tag `round-1` |
| Contract v4 and the packets | Git tag `contract-v4` |
| Declined findings, decisions added and revised, word counts | Round 2 commit messages: `git log round-1..HEAD -- docs/spec docs/contract.md` |
