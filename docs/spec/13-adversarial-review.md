# Adversarial review

Two adversarial reviews attacked the spec, each with six reviewers on the same six angles: the first filed 295 findings (23 Critical) against contract v3 and the round 1 drafts, and the second filed 278 (16 Critical) against contract v5 and the round 2 tabs. The first review moved shared rules into the contract, added the shared phase table and a program plan, and cut the tabs by a quarter. The second found fixes that did not hold and answered open questions; round 3 resolved all 16 Critical findings in contract v6 and v6.1, rebuilt the program around agents and one founder, and settled every `[unverified]` claim.

## How the reviews worked

Each review attacked one tagged text and is itself tagged. The first attacked `round-1` and is tagged `review`; the second attacked `round-2` and is tagged `second-review`. `findings.json` parses all twelve reports into one record per finding.

### Two briefs

Both briefs gave every reviewer the same core rules:

- Find what is wrong, missing, inconsistent, infeasible, below the state of the art, unsafe, legally risky or tasteless, and propose a concrete fix for each. No praise and no restatement.
- Read the contract first and do not re-report its rulings; report a ruling that is itself wrong.
- Verify load-bearing claims with WebFetch on primary sources, and cite only pages opened.
- Write 25 to 60 findings, most severe first, each naming its targets by tab code (or CONTRACT) with section, problem, evidence and fix.

The second brief, at `docs/review/brief.md` (the first stays at tag `review`), added four duties:

- **Fixes that hold.** Read this tab's record of the first review first. Report a first-review fix that does not hold, a fix that created a new problem, and a declined finding whose reason is wrong.
- **Buildability.** Report a capability whose contract, types, failure or oracle is too vague to build against, and an oracle whose pass criterion is not machine-checkable.
- **Open questions.** Propose an answer to each open question in the reviewer's area, as a finding whose fix is the decision.
- **Claims.** Verify each `[unverified]` claim on a primary source. A refuted claim is a finding; a confirmed one goes under "Verified claims" in the report.

| Severity | Definition from the second brief | First review | Second review |
| --- | --- | --- | --- |
| Critical | Breaks a founder requirement, a principle or the architecture; a false or dangerous claim; something that cannot work or cannot be built as specified | 23 | 16 |
| Major | A significant gap, an inconsistency between tabs, a method clearly below the state of the art, an infeasible target, a missing capability practitioners need, or an open question that blocks building | 193 | 157 |
| Minor | A local precision, wording or ordering problem | 79 | 105 |
| Total | | 295 | 278 |

The first brief lacked "or cannot be built" and "an open question that blocks building"; the rest of each definition is the same.

### The six angles

R7 to R12 repeat R1 to R6 in order. Each reviewer read its primary tabs in full and the sections of other tabs its angle touched. Counts read Critical, Major, Minor (total).

| Angle | What it covers | First review | Second review |
| --- | --- | --- | --- |
| Physics (R1, R7) | Error bounds, discretization, solvers, validity envelopes, physics coverage | 4, 37, 16 (57) | 3, 26, 15 (44) |
| Geometry (R2, R8) | Kernel determinism, error propagation, entity naming, blends, GD&T | 5, 26, 17 (48) | 3, 21, 27 (51) |
| Architecture and taste (R3, R9) | Identity and caching, labels, Ingot–Kiln semantics, coherence and length | 4, 41, 10 (55) | 2, 32, 20 (54) |
| Engineering practice (R4, R10) | Shop-floor safety, CAM, drawings, PLM, board design, enterprise workflows | 4, 27, 11 (42) | 2, 28, 15 (45) |
| Security and legal (R5, R11) | Labels and prompt injection, supply chain, approvals, licences, export control, privacy | 4, 26, 16 (46) | 4, 30, 15 (49) |
| Feasibility (R6, R12) | Staffing or program, phase 1 scope, performance targets, platform runtimes | 2, 36, 9 (47) | 2, 20, 13 (35) |
| All | | 23, 193, 79 (295) | 16, 157, 105 (278) |

The second review's reports list 118 claims verified on primary sources (R7 27, R8 20, R9 15, R10 15, R11 18, R12 23), and 68 of its findings name an open question in their section line. Several report a first-review fix that does not hold: R7-03 (R1-02's slenderness rule), R8-03 (R2-03's propagation rules), R10-01 (R4-01's no-start rule), R11-02 (R5-02's free-text rule) and R11-03 (R5-03's cache trust).

### Findings by target

A finding may name several targets, so the columns sum to more than each review's total. In the first review 86 findings name one target and 209 name two or more (R6-02 names eleven); in the second 55 name one and 223 name two or more (R9-44 names all twelve tabs). "Sole" counts findings that name only that target.

| Target | First: Critical | First: Major | First: Minor | First: total (sole) | Second: Critical | Second: Major | Second: Minor | Second: total (sole) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ING | 6 | 33 | 8 | 47 (3) | 5 | 29 | 13 | 47 (2) |
| ANV | 8 | 36 | 17 | 61 (13) | 4 | 30 | 21 | 55 (5) |
| FLX | 7 | 48 | 11 | 66 (7) | 4 | 37 | 17 | 58 (5) |
| COV | 5 | 22 | 6 | 33 (9) | 1 | 28 | 8 | 37 (2) |
| KLN | 12 | 59 | 8 | 79 (3) | 6 | 62 | 28 | 96 (3) |
| MEC | 2 | 32 | 11 | 45 (4) | 2 | 38 | 24 | 64 (8) |
| MFG | 3 | 28 | 10 | 41 (11) | 3 | 38 | 15 | 56 (8) |
| ELX | 4 | 27 | 5 | 36 (4) | 1 | 17 | 5 | 23 (1) |
| AGT | 7 | 24 | 11 | 42 (9) | 7 | 36 | 13 | 56 (5) |
| UIX | 3 | 29 | 10 | 42 (7) | 1 | 21 | 10 | 32 (3) |
| ECO | 1 | 37 | 10 | 48 (8) | 2 | 36 | 13 | 51 (7) |
| PLT | 2 | 46 | 13 | 61 (7) | 3 | 35 | 20 | 58 (4) |
| CONTRACT | 16 | 49 | 8 | 73 (1) | 16 | 77 | 19 | 112 (2) |

KLN draws the most findings of any tab in both reviews, because identity, caching, labels, merges, approvals and cache trust all pass through Kiln and `repo`. The contract draws 16 of the first review's 23 Critical findings and all 16 of the second's, since most Critical fixes need a new or corrected contract rule.

### From findings to revised tabs

Both rounds ran the same pipeline.

1. **The contract rules first.** Section 15 (v4) rules on 81 first-review findings (20 Critical, 54 Major, 7 Minor): 72 of the 73 that target CONTRACT, since R3-49's naming drift is fixed in the tabs, and nine more whose fixes needed contract text. Section 17 (v6) rules on all 112 second-review findings that target CONTRACT and on two requests pending in round 2's open questions: `apps/machine-gateway` and the `flash_device` Act.
2. **Each tab gets a packet** with its findings in full and the contract changes that affect it. Round 3 packets add the tab's open questions with the reviewers' proposed answers, its `[unverified]` lines with the claims reviewers verified, and known items such as a reading sentence under each diagram.
3. **One revision agent per tab applies its packet.** It applies every finding unless it has a sound reason, records each declined or partly applied finding under Open questions, never cuts a decision, oracle or source, and passes the spec check. Round 2 revised ANV and FLX against v4 and the rest against v4.2; round 3 revised all twelve against v6, and its brief also removed every staffing figure and calendar month.
4. **Each revision lands as one commit** listing declined findings with reasons, decisions added and revised, and the word count.
5. **The tabs' change requests are ruled:** v4.1, v4.2 and v5 in section 16, and v6.1 in section 17.
6. **A consistency pass aligns every tab with the latest contract:** names, shared phases, interface rows and citations. Round 3's pass applies 135 audited edits, and where two tabs disagree the owner's text wins.

A finding with several targets is shared: each tab changes only what it owns and points to the owner for the rest.

## Critical findings

Each resolution below was checked against the committed contract and tabs at the head of round 3, not against working copies or packets. All 39 Critical findings have a committed resolution. Where round 3 changed a first-review fix, the Status column says so; every decision cited in the second table was added or revised in round 3.

### First review: 23 Critical findings

| Id | Targets | Problem | Resolution | Status |
| --- | --- | --- | --- | --- |
| R1-01 | FLX, COV, CONTRACT | Energy-norm bounds certified peak stresses, totals mixed norms, and no total could be `Guaranteed` | Contract 5: a `Guaranteed` bound needs a proof in the quantity's norm, and bounds in different norms never combine. D-FLX-4, D-FLX-23: peaks are regularized goals with `Estimated` bounds | Resolved; R7-01 and R7-14 extend it |
| R1-02 | FLX, COV, ANV, MEC, CONTRACT | The immersed octree failed on thin walls, lattices and frames, and Flux had no beams | Contract 7.1: discretization per region, with beams, shells where t/L_local ≤ 0.2, four cells across any section, and beam lattices. D-FLX-12, D-FLX-13, D-FLX-26; `anvil::mid_surface` | Resolved; R7-03 corrected L_local |
| R1-03 | CONTRACT, COV, FLX, ING | Contract and COV disagreed on unquantified model-form error, so no check could pass or the term counted as zero | Contract 5 `CheckOutcome`: `Pass { conditional_on }` meets a gate only under a cited policy allowance, else `Undecided { reason: Unquantified }`. D-COV-4, COV-O-ERR-3 | Resolved |
| R1-04 | CONTRACT, FLX, COV | Surrogate guarantees rested on marginal conformal coverage, which optimizers break | Contract 7.1: surrogates are `Estimated { confidence, scope: Marginal }`; a `SignOff` check needs a per-prediction bound or a confirming solve; weighted conformal prediction in optimization loops. D-FLX-14, D-COV-7; FLX-O-ROM-2 | Resolved; R7-24 puts the bound in the check's norm |
| R2-01 | ANV | Tolerance growth during parallel pair decisions made outcomes depend on pair order | Contract 7.1: decisions in rounds by dimension against tolerances frozen at each round's start. D-ANV-4; ANV-O-DET-2 shuffles orders on 1 to 64 threads | Resolved |
| R2-02 | ANV, ING, KLN, MEC, CONTRACT | Entity names hashed hidden CRDT block ids and steered meshes, seeds and orders | Contract 7.1 label invariance; contract 5 text-derived call sites (`OpSite`, renamed `CallSite` by R9-41). D-ANV-25, D-ING-21; ANV-O-LABEL-1 re-randomizes every name | Resolved |
| R2-03 | ANV, CONTRACT | Derived faces "inherited" bounds that fail through offsets, intersections and blends | Contract 5 `Body`: per-face `{ position, normal }` bounds that compose by stated rules or become `NotQuantified`. ANV-O-CONV-2 | Resolved; R8-03 added edge tangent bounds for blends |
| R2-04 | ANV, CONTRACT | The freedom-to-operate argument ignored claim 16 of US 12,229,885 B1, which reads on the CPU path | Contract 7.1: counsel reviews claims 1, 6, 11 and 16, both paths and continuations. D-ANV-17: every intersection point is a certified root, never a thresholded sample | Resolved in the spec; counsel's written opinion is a phase 0 gate item (contract 13.1, R8-49) |
| R2-05 | ANV | Validity was checked only near changed entities, so far-field self-intersections passed | Contract 7.1: created and modified entities are checked against the whole Body. ANV-O-VALID-2 | Resolved |
| R3-01 | CONTRACT, ANV, KLN, FLX | Every identity hashed names, so sharing failed and a geometry-neutral refactor voided releases | Contract 5 `GeometryId` beside `ObjectId`; contract 7.2 two-stage keys. D-ANV-24, D-KLN-26, D-FLX-6; ANV-O-CACHE-1 | Resolved |
| R3-02 | CONTRACT, KLN, AGT | Labels leaked through backdating, a one-string data class and per-package live replicas | Contract 5 label lattice; contract 7.1: the label is a separate memo output, and live replication is per (package, module confidentiality label). D-KLN-36, D-KLN-22, D-AGT-24 | Resolved; R11-01 split integrity from confidentiality |
| R3-03 | ING, KLN | `try` caught environmental failures, whose fallbacks Kiln then cached | Contract 2 Abort and 7.2: Aborts are uncatchable, propagate and are never cached. D-ING-11, D-KLN-6; KLN-O-ABORT-1 | Resolved; `OpVersionRetired` stays a `Failure` and, since R9-35, is never cached |
| R3-04 | ING, KLN | Recursion through feature calls was unbounded | Contract 7.1: a demand-depth limit (default 10,000) and a fuel governor per Evaluation, both Aborts. D-ING-23; ING-O-24, KLN-O-LIMIT-1 | Resolved |
| R4-01 | CONTRACT, MFG, AGT, KLN | No rule stopped Crucible from starting machines remotely, and tabs disagreed on Act names | Contract 2 and 7.6: one named list of physical-effect Acts, and Crucible never issues cycle start, `Start` or `StoreAndStart`; contract 7.1: `unattended_safe` is a signed site policy. D-AGT-31, D-KLN-35 | Resolved; Acts in phase 2 with CAM; R10-01 and R10-02 carried the rule onto the wire |
| R4-02 | MFG | Collision checks simulated the toolpath, not the control's motion between points | D-MFG-23: simulation and an independent re-interpreter execute posted NC text under the controller's declared `MotionSemantics`, else sweep a conservative envelope or report `Unsupported`. MFG-O-SIM-2; phase 2 | Resolved |
| R4-03 | ELX, KLN | Set-union `connect` let two clean branches merge into a silent short | Contract 7.1 connectivity merge condition; KLN's `Conflict::NetMerge`; D-ELX-21: nets join only through `tie`; ELX-O-NET-2 | Resolved |
| R4-04 | UIX, ELX | Schematic and layout editors had no workable home in the UI | Contract 7.6: Electronics preset and the public `crucible:ui/canvas2d` world, with per-pointer tools on an interactive edit lane. D-UIX-27, D-UIX-20; UIX-O-CANVAS-1 | Resolved |
| R5-01 | AGT, KLN, CONTRACT | Model contexts carried no label, so content could be written down into another repository | Contract 7.6: a write to a lower destination fails with `label/write_down` unless two people, one an export officer, sign a declassification record. D-AGT-24, D-KLN-32 | Resolved; write-down compares confidentiality only since R11-01 |
| R5-02 | AGT, KLN, ING, CONTRACT | Human merges endorsed agent-written free text, which then instructed later sessions | Contract 7.6: merging never endorses free text; contract 7.1: span-level integrity provenance. D-ING-24, KLN-O-SPAN-1; D-AGT-12: the verifier sees no author free text | Resolved; R11-02 extended it to evaluated strings |
| R5-03 | KLN, CONTRACT, AGT, FLX, ELX, COV | Machines running untrusted Proposals and native External Ops also signed cache attestations | Contract 7.8: two worker pools, a separate attestation service, two-builder agreement for gates and `SignOff`, operator-only public writes. D-KLN-9; D-FLX-30, D-ELX-12 | Resolved; R11-03 closed the third-party gap |
| R5-04 | AGT, UIX, KLN, CONTRACT | Approval URLs passed through the agent, any approver could approve, and three approval surfaces existed | Contract 7.6: assigned approvers, no URL returned to a model, one server-generated page, WebAuthn, no approval on phones. D-AGT-20, D-UIX-29 | Resolved; the page has its own origin since R11-05 |
| R6-01 | CONTRACT, PLT | No duration, headcount or critical path; phases 0 and 1 as written needed about 465 engineer-years | Round 2's contract 13.2 set durations, headcount, engineer-years and a month-36 gate. Round 3 replaced it (R12-02 to R12-04): one founder, agent roles, gates instead of dates, a budget per phase | Resolved; superseded in round 3 |
| R6-02 | CONTRACT, ANV, FLX, ING, KLN, UIX, MFG, ECO, AGT, PLT, ELX | Phase 1 carried work that neither GP1 nor GP2 needs | Contract 13.2 phase 1 scope with named deferrals: one Ingot executor (D-ING-13), one forward renderer (D-UIX-24), a single-node team server, CAM in phase 2, a signed first-party package index | Resolved; phase 1 keeps three agent roles, not two |

### Second review: 16 Critical findings

Every second-review Critical finding targets the contract. Section 17 accepts each one, R7-02 and R8-02 with a revised fix and R12-02 in a different form, and each also changed at least one tab.

| Id | Targets | Problem | Resolution | Status |
| --- | --- | --- | --- | --- |
| R7-01 | CONTRACT, FLX, COV, MEC, ING | Phase 1 `SignOff` checks passed on η99-calibrated bounds whose coverage held only over the corpus, so optimizers would select undershoots; the miss rate never entered the confidence | Contract 5: a calibrated bound carries its α into the union bound. Contract 7.1: classes declare applicability envelopes, and one further refinement confirms a `SignOff` `Pass` or returns `Undecided { reason: CalibrationUnconfirmed }`. D-FLX-24, D-FLX-40 (adversarial samples), D-COV-17, D-MEC-30; FLX-O-ERR-3 | Resolved |
| R7-02 | CONTRACT, FLX, ING | Contract, FLX and ING gave three singular-point rules, and the loaded end cap left the canonical check always `Undecided` | Contract 7.1: one rule that flags only incompatible conditions, each flagged set with a default distance. Contract 6: the canonical check excludes the clamp and the loaded face. D-FLX-39; ING-O-31: the canonical check decides at `SignOff` | Resolved; the near-maximal-set rule is declined (contract 17) |
| R7-03 | CONTRACT, FLX | "Distance to the nearest load" in L_local disabled shells and beams under any distributed load, gravity or inertia | Contract 7.1: distributed loads, body forces and inertia that cover a wall do not shorten L_local; a varying load counts by \|q\|/\|∇q\|. FLX-O-PLAN-2 adds plates under pressure, pressurized cylinders and a free plate in modal analysis | Resolved |
| R8-01 | CONTRACT, KLN, ANV, MEC | Threads, hole specifications, welds, finish and plies lay outside the approval subject, so changing them left a release unmodified and its Approval valid | Contract 5: every attribute class declares whether it is definitional, and definitional attributes enter the `ItemDefinition` name-free (general tolerances and edge callouts joined by CCR-MEC-1). D-ANV-32, D-KLN-26; KLN-O-CHG-2 | Resolved |
| R8-02 | CONTRACT, ANV, ING, AGT | `RankSwap` could not come from a pure `anvil::resolve`, and `Ordinal` ids could swap silently after a dimension edit | Contract 5 `Query`: `resolve` reports `NearTie`; range stability is sampled evidence from `anvil::query_stability`, run in protected-branch CI; extent use of merges, partial deletions, `Ordinal` ids and near ties fails unless accepted. D-ANV-15, D-ANV-34; ANV-O-NAME-2, ANV-O-NAME-6 | Resolved, with contract 17's revised fix |
| R8-03 | ANV, CONTRACT | Blend normal bounds used only the spine's position bound, so a later offset could pass a `Guaranteed` check on a false bound | Contract 5 `Body`: per-edge tangent bounds, rules that carry tangent and normal bounds, and offsets of approximated faces only under a certified curvature bound, else `OffsetNotRegular`. D-ANV-21; ANV-O-CONV-2 perturbs supports in position and direction | Resolved |
| R9-01 | CONTRACT, KLN, AGT, ELX, MFG | The approval subject covered geometry and PMI only, so firmware, a Material or a document could change after approval | Contract 5: `ItemDefinition` per Item kind, and the subject holds every affected Item's digest; `act.commit` recomputes the subject and refuses a mismatch. D-KLN-28; AGT's `act/subject_mismatch`; KLN-O-CHG-2 | Resolved |
| R9-02 | CONTRACT, ING, KLN | A branch on `Undecided` cached `Pending` or a failure depending on the fidelity ceiling, which no key holds | Contract 5 `Truth`: control flow on `Undecided` yields a cached `Undecided` value, and the ceiling changes only reporting. D-ING-7; ING-O-35 | Resolved |
| R10-01 | CONTRACT, MFG, AGT | OctoPrint, Moonraker and PrusaLink start a print from an upload flag, and robot script interfaces run code, so static oracles passed unsafe connectors | Contract 7.6: the machine gateway enforces each connector's endpoint allowlist in its own core, robot programs go only into the program store, and oracles capture the wire against real servers or simulators. D-AGT-31; MFG-O-SAFE-3, AGT-O-21 | Resolved |
| R10-02 | CONTRACT, MFG | Drip feed into a control already waiting for data would start motion at commit | Contract 7.6: a transfer never completes a start the device was waiting for; drip feed is pull-only, and an open session fails with `DncSessionPreArmed`. MFG's pull-only DNC row; MFG-O-SAFE-5: zero bytes to waiting controls | Resolved |
| R11-01 | CONTRACT, AGT, KLN | Integrity flags sat in the confidentiality lattice, so every tainted edit counted as a write-down while one person's endorsement lowered a label | Contract 5 `Labels`: separate confidentiality and integrity parts; write-down, clearances, encryption domains and live replication use confidentiality only. D-AGT-24, D-KLN-22; AGT-O-17 | Resolved |
| R11-02 | ING, KLN, AGT, CONTRACT | Agent-written literals became plain strings once evaluated (part names, BOM text, notes, embossed text), reopening R5-02's channel | Contract 7.6: values evaluated from free text carry the span's integrity, `api` returns strings from untrusted nodes as `ExternalText` handles, and such Snapshots are instruction-capable. D-ING-24, D-AGT-18, D-AGT-26; AGT-O-8, ECO-O-18 | Resolved |
| R11-03 | CONTRACT, KLN, ECO, PLT | Trusted and registry builders ran third-party code with attestation authority, and two-builder agreement cannot stop a deterministic exploit | Contract 7.8: third-party code runs only in single-use microVMs, its closures are attested only into their tenant's domain, and the global domain holds first-party closures only. D-KLN-9; KLN-O-TRUST-1 | Resolved |
| R11-04 | CONTRACT, AGT | A second OAuth grant or a stdio relaunch gave an external host a fresh, clean context label | Contract 7.6: an external host's context is (user, client identity) with one monotone label stored on the server; only a human resets it, through `session.reset_context` with WebAuthn. D-AGT-24; AGT-O-17 | Resolved |
| R12-01 | CONTRACT, PLT, ECO | Synchronous `crucible:ops` imports could not be answered across the browser sandbox, so third-party components that call operations could not run in browsers | Contract 7.4: `crucible:ops` imports are Component Model async functions in the callback ABI; browsers evaluate third-party components remotely until the bridge passes; isolation round-trip targets. D-PLT-36, D-PLT-42; PLT-O-WASM-7 | Resolved; the local browser sandbox follows in phase 2 |
| R12-02 | CONTRACT, PLT, AGT, ANV, FLX, UIX | About 430 phase 0 and 1 oracles had to be written by people before swarm work, with no build program or review path | Contract 13.2: an oracle role writes and locks oracles, a verifier passes them, work items open only on verified oracle ids, every oracle declares a runner class, and corpora agree with an independent source. D-PLT-45; PLT-O-BLD-4; `WorkItem` over Git until AGT's plans ship (CCR-AGT-13) | Resolved in a different form: the program has no human team |

## Major and Minor findings by theme

The first review's 272 Major and Minor findings and the second's 262 fall into eighteen themes, each finding under the theme of its main problem; the second review adds oracles and buildability, which its brief asked for. The fixes named are representative, each checked in the committed text at the head of round 3.

| Theme | First: Major | First: Minor | Second: Major | Second: Minor | Total |
| --- | --- | --- | --- | --- | --- |
| Identity, names and cache keys | 12 | 3 | 10 | 5 | 30 |
| Error bounds and check semantics | 12 | 3 | 10 | 0 | 25 |
| Validity envelopes, evidence and physics coverage | 10 | 4 | 9 | 4 | 27 |
| Physics methods | 13 | 4 | 5 | 6 | 28 |
| Geometry, modelling, drawings and tolerancing | 12 | 14 | 7 | 18 | 51 |
| Determinism and numerics | 16 | 6 | 4 | 5 | 31 |
| Language, Kiln and `repo` semantics | 16 | 2 | 15 | 6 | 39 |
| Manufacturing practice and machine safety | 11 | 6 | 20 | 5 | 42 |
| Electronics practice | 4 | 1 | 3 | 2 | 10 |
| PLM and enterprise integration | 8 | 1 | 4 | 7 | 20 |
| Security | 16 | 10 | 21 | 8 | 55 |
| Legal, licensing, privacy and compliance | 10 | 6 | 13 | 13 | 42 |
| Feasibility, program and phasing | 14 | 1 | 13 | 4 | 32 |
| Performance targets and platform support | 19 | 6 | 11 | 10 | 46 |
| Spec form, names and ownership | 10 | 7 | 6 | 8 | 31 |
| Interop and formats | 9 | 1 | 1 | 0 | 11 |
| UI and rendering practice | 1 | 4 | 1 | 3 | 9 |
| Oracles and buildability | 0 | 0 | 4 | 1 | 5 |
| Total | 193 | 79 | 157 | 105 | 534 |

Compared with the first, the second review found more in manufacturing, security and law, and less in physics methods and numerics.

### Identity, names and cache keys

**First review.** Names moved under ordinary edits. Call sites now come from source text (contract 5; D-ING-21; R2-06, R2-12, R3-06), rank selectors need an anchor (R2-22), keys carry the call site, `GeometryId`s and the effective fidelity (contract 7.2; R3-05, R2-10, R3-11), and imports are named from source ids (D-ANV-31; R2-21).

**Second review.** Names still leaked through edge roles, copies, statistics and shared artifacts.

- Edges and vertices take roles from the operation that creates them (D-ANV-33; R8-06), and copying is decided only where names would collide (D-ANV-30; R8-07).
- Statistical inputs are ordered, and random streams keyed, by geometry and argument values, never by names (contract 7.1, 7.2; R8-08, R9-17, R9-09). Assemblies get a name-free `GeometryId` (contract 5; R9-12), and `DisplayPackage` pages carry canonical numbers (contract 5; R8-18).

### Error bounds and check semantics

**First review.** Four tabs gave four rules for deciding a check. ING owns the one decision rule (D-FLX-15; R3-07), `ErrorBudget` has one shape with `NotQuantified` parts (contract 5; R3-08, R1-08), flagged singular sets make point quantities `Undecided` unless excluded (contract 7.1; R1-05, R3-09), adaptivity goals are study inputs (D-FLX-5; R3-10), and every `Estimated` bound carries its class's η99 (D-FLX-24, D-COV-17; R1-14, R1-07).

**Second review.**

- Eigenvalue checks rest on a calibrated DWR estimate with Kato–Temple or Lehmann algebraic bounds (D-FLX-41; R7-05). Each error source has one producer (contract 5; R7-11).
- Smooth non-conforming contact guides refinement but is not singular (contract 7.1; R7-18). The default smoothing radius follows fillet radius and wall thickness, not part size (D-FLX-23; R7-15).

### Validity envelopes, evidence and physics coverage

**First review.** The validation framework lacked a standard and a metric. ASME V&V 10 and the V&V 20 metric govern physical gates (contract 13.1; D-COV-20; R1-29), results carry their solution-verification status (D-COV-21, D-FLX-34; R1-28), regime variables are typed functions (D-COV-18; R1-31), and one-way coupling states its conditions (D-COV-19; R1-27).

**Second review.** Phase 1 validated no physics model, and validation transferred to any quantity.

- Model-form bounds apply only to validated response-quantity classes, gates place sensors on checked quantities, and GP1 and GP2 add strain-gauged proof loads (contract 5, 13.1; R7-04, R7-10).
- As-built strut calibration enters phase 1 and gear, bearing and shaft ratings phase 2 (contract 13.4; R7-06, R7-19, R10-18). COV owns material parameters and MFG owns process data (D-MFG-30; R7-42).

### Physics methods

**First review.** Resonant electromagnetics uses frequency-domain Nédélec FEM (D-FLX-32; R1-22), flow uses PCD and augmented Lagrangian preconditioners (D-FLX-33; R1-23) and Schwarz smoothers around cut cells (D-FLX-16; R1-17), nested models are forms over product spaces (D-FLX-38; R1-24), and kernel-IR models get tangents by algorithmic differentiation (contract 7.4; R1-25).

**Second review.**

- Aggregated CutFEM serves `Interactive` and `SignOff`, and the shifted boundary method at most `Preview` (contract 7.1; R7-17). Laminar layers get octree wall refinement (D-FLX-45; R7-09, CCR-FLX-10).
- Weld shrinkage on beam frames enters as joint loads from local joint models (D-FLX-43, D-MFG-32; R7-20), and sheet lattices sign off on mid-surface shells from phase 2 (D-FLX-44; R7-25).

### Geometry, modelling, drawings and tolerancing

**First review.** A staged blend program is measured by one re-fillet benchmark (contract 7.1; D-ANV-29; R2-07), constructions record `Continuity` certificates (D-ANV-26; R2-08), conversion preserves exact faces (contract 5; R2-14), MEC owns one default distribution (D-MEC-28; R1-37), and split toleranced faces fail (D-MEC-27; R2-18).

**Second review.** This theme holds the most Minor findings in both reviews.

- Modular rank certifies only exact rational witness configurations; elsewhere a nonzero interval minor at a Krawczyk-certified witness serves, and deficiencies are `Estimated` (MEC; R8-09). Release drawings use certified hidden lines within a stated bound (D-MEC-24; R8-34).
- General tolerances and edge callouts are definitional (contract 5; R10-21), datum targets join the GD&T record (MEC-O-TL-6; R8-38), and dialect conversion is exact translation with typed holes (R10-36).

### Determinism and numerics

**First review.** WGSL kernels never claim bit-identity with CPU kernels (contract 7.5; R1-09), one canonical `linalg` crate serves `Portable` code with faer only in `CpuIsa` (contract 7.1; D-FLX-36, D-PLT-34; R1-10, R6-21), FMA variants serve `Preview` and `Interactive` (contract 7.3; R6-17, R6-18), and NaN canonicalization runs only where bits become observable (contract 7.4; R6-20).

**Second review.**

- D-PLT-35 replaces the round 2 rule |q_A − q_B| ≤ E_A + E_B. Classes that share a plan, marks and steps agree within their algebraic and floating-point parts plus a floor; otherwise full budgets apply and the divergence is reported (R7-12).
- Decisions are the same at every fidelity (contract 7.1; R8-04), GPU results only order work and propose candidates (D-ANV-35; R8-10), and a released operation version freezes its source closure (contract 4; R9-06).

### Language, Kiln and `repo` semantics

**First review.** Merges follow six conditions with a verdict order (contract 7.1; D-KLN-21; R3-15), approvals sign an `ApprovalSubject` (contract 5; D-KLN-28; R3-16), measurements are Evidence records (R3-17), variants are `#[configuration]` parameters and derivatives a Kiln traversal (D-ING-22, D-KLN-27, D-KLN-37; R3-18, R3-19), and one `Scalar<D>` trait spans four flavors (D-ING-20; R3-31).

**Second review.** Core concepts had several owners or none.

- One `CheckId` never derives from predicate text, and one gate predicate and one Waiver record serve every tab (contract 2, 5; R9-05, R9-14, R9-15). An evidence watermark fixes which Evidence records an Evaluation reads (contract 2; R9-03).
- Instance sets count members by evaluation while existence stays static (contract 2, 6; R8-20, R9-16). Literal overrides enter the keys of nodes holding the site and never reach the shared cache (KLN; R9-07).

### Manufacturing practice and machine safety

**First review.** A product NC interpreter verifies any program (D-MFG-28; R4-09), builds go out as 3MF (D-MFG-25; R4-13), feeds and speeds default to vendor or shop values (D-MFG-27; R4-36), and balloon labels are allocated once (D-MFG-26; R4-14). R4-05's header hash gave way in round 3 to the pinned-approver check below.

**Second review.**

- Programs are approved per machine class and nominal tools (contract 7.6; R10-08), and the gateway checks offsets at transfer and watches them until the program ends (MFG; R10-09). It sends only payloads named in an approved plan, checks a canonical hash on read-back and overwrites only its own programs (D-MFG-24; R10-10, R10-11, R11-07).
- Posts emit restart points (D-MFG-31; R10-12), conformance decisions count the lab's uncertainty (D-MFG-33; R10-03), the approval page adds a physical-effect section (contract 7.6; R10-17), and `flash_device` joins the transfer Acts (R10-06).

### Electronics practice

**First review.** A schematic is a stored drawing proven equal to the code (D-ELX-1; R4-22), vendor models run in ngspice by default (D-ELX-25; R4-23), boards declare fabrication and assembly classes (D-ELX-23; R4-25), and creepage comes from a declared isolation barrier (D-ELX-24; R4-26).

**Second review.**

- Nets that cross no barrier take voltage-dependent IPC-2221 spacing (D-ELX-28; R10-25), and a `CatalogSelection` re-resolves only until the layout's first release (D-ELX-3; R10-24).
- Arcs store an integer centre, radius and rays, so clearance offsets stay concentric (D-ANV-27; R8-22). Schematics and layouts stay Ingot text (D-ELX-27; R10-45).

### PLM and enterprise integration

**First review.** Crucible assumed it was every customer's system of record; each record type now has one (D-KLN-39; R4-19), manufacturing change orders are their own class (D-KLN-38; R4-11), revision identity tolerates bit-level upgrades (D-KLN-26; R4-17), and ERP, MES and PLM connect through connector worlds (D-ECO-30; R4-18).

**Second review.**

- The definition tolerance has a floor of 10ρ with a topology test (D-KLN-26; R10-39, R8-36), and revision-label rules are policy data (D-KLN-47).
- A release plan lists its deliveries to the organization's ERP, MES and PLM under one Approval (contract 7.6; R10-26). External approvals are recorded as such (R11-18), and release drawings are PDF/A-2u (MEC; R10-38).

### Security

**First review.** Third-party Wasm components run out of process (contract 7.4; D-ECO-26, D-PLT-31; R5-09), one `release_data` stage guards exits, except a human's audited local export of uncontrolled data (D-AGT-30, D-KLN-40; R5-05, R5-06, R12-16), two people change clearances and widening policies (D-KLN-41, D-AGT-27; R5-15), package text is `ExternalText` (D-ECO-32; R5-13), and post-quantum dual signing starts in phase 2 (contract 7.8; R5-23).

**Second review.** Approval pages, native hosts and the single-node server each left a path around round 2's controls.

- Every client approves in a browser on the approval origin, with its own relying-party id (D-PLT-41, D-UIX-29; R11-05, R12-15). Device-bound credentials approve, and synced passkeys never do (contract 7.6; R11-06).
- Every process that runs untrusted code starts with no network (D-PLT-43; R11-09), External Op results meet gates through receipts from two hosts (contract 7.8; R11-08), and a single-host server keeps its keys in a TPM, HSM or OS keystore and offers no External Ops (contract 7.8; R11-10).

### Legal, licensing, privacy and compliance

**First review.** Flux is renamed in phase 0 (contract 2, 13.1; R5-19), the patent is attributed to its inventor (contract 7.1; R5-31), regulated customers get 10-year lines and a regulated cloud (contract 7.7; R5-20), agents never sign off under the DCO (D-ECO-21; R5-26), and principal ids are pseudonymous (D-KLN-43, D-AGT-32; R5-27).

**Second review.**

- Crucible refuses tenants, buyers and update clients established in Russia or Belarus (D-ECO-29; R11-27), and std computes standard values from formulas instead of shipping transcribed tables (D-MEC-31, D-ECO-36; R11-30).
- The company is the Cyber Resilience Act manufacturer, with five years of support per stable line (D-ECO-34, contract 7.7; R11-28), and the registry runs notice and moderation under the Digital Services Act (D-ECO-35; R11-29). Benchmarks use only the licence-filtered ABC subset (contract 13.3, D-ECO-37; R11-33, R8-23).

### Feasibility, program and phasing

**First review.** Contract 13.4 sets one phase per shared capability (R1-35, R2-27), phase 1 has one forward renderer (D-UIX-24; R6-24) and one Ingot executor (D-ING-13; R6-25), GP1 uses the shop's own CAM (R6-05), and every core dependency has a risk register (D-PLT-40; R6-30). Round 2's staffing and hiring plan (R6-03, R6-04) is gone since round 3.

**Second review.** Round 2's plan absorbed scope without approval and left the interface and release chains off the critical path.

- Contract 13.2 has no human team, no dates and no engineer-years: one budget per phase, approved by the founder, and four critical-path chains, with chains C (interface) and D (release) added (R12-03, R12-04, R12-09, R12-22).
- Nothing is phased before its prerequisites, which moves inherent strain to phase 2 (contract 13.4; R7-07, R7-08, R9-32). The kernel IR freezes at the phase 0 gate once its first consumers compile (contract 7.5; R12-07), and the run build is tagged before the physical runs (R12-25).

### Performance targets and platform support

**First review.** Contract 13.3 sets targets with the drag preview rule, scene capacity and fidelity per rebuild row (R6-07 to R6-11, R2-09), a Tier 1 target may be a preview for one phase (contract 9; R6-06, R6-31), browsers run one engine per origin and a disposable heavy worker (D-PLT-29, D-PLT-30; R6-15, R6-14), and physics shows as `Proxy` during geometric drags until phase 3 (D-FLX-37; R1-16).

**Second review.**

- Each 13.3 row has a phase and blocks beta promotion only from it, and PLT names the reference laptop model and its measurement conditions at the phase 0 gate (R12-05, R9-33, R12-06). The CEED row splits into a `CpuIsa` row and a canonical row (R7-39, R12-23).
- Without shared memory, cancellation lands at Op boundaries and long Ops run in disposable workers (contract 7.4; R12-17). The browser engine worker recycles (contract 9; R12-18), and isolated `crucible:ops` calls have round-trip targets (contract 7.4; R9-21).

### Spec form, names and ownership

**First review.** Every design section ends in one capability table (contract 11; R3-36), the determinism mechanisms are stated once (contract 7.3; R3-37), every tab fits its cap (R3-38 to R3-45, R3-52 to R3-55), and "software bill of materials" is spelled out (R4-37).

**Second review.**

- `OpSite` became `CallSite` (contract 2, 5; R9-41), `decides_on` names the bound kind a check accepts so that "evidence" never does (contract 5; R9-23), and error codes take the form `<family>/<code>` (contract 7.6; R9-47).
- The crate map adds the missing apps and SDKs, and CI fails any other dependency (contract 12; R9-24, R9-25, R9-38). PLT applies R9-44 in part: decision paragraphs keep their Decision, Why and Rejected sentences.

### Interop and formats

**First review.** Flux owns the FMI and SSP runtime (D-FLX-30; R3-24), ECO owns every output writer while MFG chooses the package per fabricator (D-MFG-16; R3-25, R4-24, R4-27), events carry ids, never design content (D-KLN-34; R3-23), and KiCad's importers run as an external tool (D-ECO-31; R4-28).

**Second review.** R9-26 found first-party WIT packages assigned to owners whose tabs never specified them. ECO now tables its own four packages, `units`, `io`, `tool` and `connect` (ECO-O-34), and KLN specifies `crucible:host` (KLN-O-WIT-1).

### UI and rendering practice

**First review.** Phase 1 uses weighted blended transparency and phase 2 a k-buffer that breaks ties by Instance index and canonical face number (D-UIX-11; R6-27), fonts are bundled with grayscale antialiasing (D-UIX-4; R6-43), and presets add NX, Creo, Inventor, Altium and KiCad (D-UIX-20; R4-39).

**Second review.** The toolkit bake-off could not discriminate its options, and UI questions stayed open. Crucible builds its own retained-mode toolkit, decided now (D-UIX-3; R12-08); scene capacity depends on whether an adapter reports `compute_raster` (contract 13.3; R12-28); and D-UIX-31 to D-UIX-33 settle 3D mice, a usability target and XR through WebXR (R12-33).

### Oracles and buildability

**Second review only.** Agents could pass oracles by special-casing visible inputs, and some pass criteria were not machine-checkable (R7-26, R10-27). Principle 6 now requires a held-out split, or a property generator seeded at CI time, for every oracle that judges agent-built code (R12-13). The blend benchmark states 95% and 97% pass rates (D-ANV-29; R8-16), and UIX-O-SNAP-2 compares renders with a reference rasterizer rather than the renderer's own outputs (R12-34).

## Declined and partly applied findings

Every tab applied its packet. The tables list each finding a tab moved to a later phase, declined in part or applied in part, with the reason stated under its Open questions or in its revision commit; ANV's round 2 records now live only in its commit message.

### First review

Contract 13.2 defers CAM, posts, stock simulation and slicing to phase 2, and GP1 uses the shop's own CAM, so findings that asked for these in phase 1 land in phase 2.

| Finding | Tab | Moved to a later phase | Stated reason |
| --- | --- | --- | --- |
| R4-01 | AGT, MFG | The physical-effect Acts in phase 2 | They ship with the effects they govern |
| R4-05 | MFG | DNC | Contract 13.2; MFG owns program headers, offsets and drip feed |
| R4-06, R4-07, R4-08 | MFG, UIX | Setup sheet and its preview; 3+1 indexing, vises and probing; Ingot hooks for posts | Arrive with CAM and posts |
| R4-09, R4-10 | MFG, ECO | `verify_nc`, migrated NC programs, tool importers and tool-data readers | Arrive with CAM |
| R4-12 | MFG, UIX | Toolpath playback, the NC code panel and agent-proposed programs | Arrive with CAM; UIX moves the cost panel to phase 1 |
| R4-35 | MFG | Each added controller family | One phase later than proposed, for the same reason |
| R4-29 | ECO, ELX, MEC | IDF read and STEP board import | An early 1.x train in phase 2; phase 1 holds only what GP1 and GP2 need |
| R2-19 | MEC | Form sampling per GD&T dialect | Needs skin model shapes, which arrive in phase 4 |
| R1-16 | FLX | Morphing reduced models during geometric drags | Phase 3; `Proxy` results before then |
| R1-40 | COV | Pseudo-4D battery packs | Phase 6 with ELX's pack-scale DFN; DFN cells are phase 5 (contract 13.4) |
| R1-39 | ELX | Monte Carlo on CUDA or ROCm | Waits for the phase 4 back-end decision (contract 7.5) |

| Finding | Tab | Declined in part | Stated reason |
| --- | --- | --- | --- |
| R1-43 | FLX, PLT | Routine `SignOff` in `CpuIsa` with FMA | Contract 7.3 requires canonical recomputation for `SignOff` |
| R1-21 | FLX | GPU element-cycle targets at `SignOff` | Explicit trajectories have no cheap canonical certificate, so the targets apply at `Interactive` |
| R2-06 | ING, KLN | CRDT identities for calls | Contract 5 derives call identity from name and occurrence; since R9-36 an ING lint covers inserted same-name calls |
| R3-03 | KLN | Making an unavailable retired version an Abort | Contract 7.2 keeps `OpVersionRetired` a `Failure`, never cached since R9-35 |
| R3-20 | KLN | Per-build signing keys | Contract 7.8's attestation service replaces them |
| R3-33 | ING | One instance per worker with state machines | Applies to the deferred code generator; the interpreter isolates calls with heap frames |
| R3-47 | ING | A Pulley fallback for Ingot | Ingot runs on the interpreter on iPadOS, so the fallback concerns Wasm components only |
| R6-33 | ING | Speed ratios for Wasm components and user forms | ING sets only its own ratios; PLT, ECO and FLX own the others |
| R5-18 | MFG, AGT | Renaming `send_to_machine` to `queue_program` | R4-01's shared list names `send_to_machine`; R5-18's meaning, delivery only, is adopted |
| R3-25, R4-24 | MFG | ODB++ through a licensed external tool; output writers in MFG | ECO builds every writer, ODB++ included (R4-27); MFG chooses the package |
| R6-02 item 6 | AGT, contract | Two agent roles in phase 1 | Contract 13.2 names three: detail designer, simulation engineer and verifier |
| R3-53 | AGT | Retitling the tab | The brief fixes the title line; the rest is applied |
| R3-41 | UIX | Eight design sections | Ten, so each capability table covers one coherent area |
| R5-25 | ECO | A foundation at phase 0 | Company stewardship until a trigger (contract 7.7), bound by a three-year backstop, a recorded trademark option and a key ceremony (D-ECO-22) |
| R1-33 | COV | Superconductors as a coverage row | Listed out of scope (OOS-3) instead |
| R1-35 | Contract | DFN batteries in phase 4 | Phase 5, because no gate names DFN; GP6 uses equivalent-circuit and SPMe cells. Round 3 also moves R1-35's phase 1 inherent strain to phase 2 (R7-07) |

| Finding | Tab | Applied in part | Owner of the rest, or reason |
| --- | --- | --- | --- |
| R2-36 | ANV | The implicit fallback states its deviation per instance by certified measurement | Not as a closed form in the radius, since the departure depends on the dihedral angle |
| R1-16, R6-32, R2-09, R2-26 and nine shared findings | ANV | Anvil's part of each | FLX, MFG and MEC own the rest |
| R2-18 | ING | ISO 5458 and 2692 dialect modules | The extended GD&T record is MEC's |
| R1-01, R1-02, R1-04, R1-07, R1-08, R1-21 to R1-25, R3-08, R5-03 | COV | COV's rows, envelopes and records | The machinery is FLX's or the contract's |
| R1-32, R1-36, R1-39, R1-41, R1-54, R3-55 | COV | Planned phases, uncertainty representation, models and envelopes | FLX, ELX and MFG own the methods; status and scope live in the generated map and contract 13.1 |
| R1-10, R1-36, R2-09, R2-36, R6-11, R3-30, R3-31 | MEC | MEC's consequences of each | ANV, PLT, FLX, UIX and ING own the rest |
| R4-25, R4-14, R1-37, R4-18, R5-05, R5-06 | MFG | MFG's side of each | ELX, MEC, ECO, KLN and AGT own the rest |
| R2-24 | PLT | No PLT change | MFG owns gouge detection, and PLT's 1 GiB memory row stands |

Round 3 closed the points round 2 left open. MEC now applies R2-19, R4-14, R4-16 and R1-37 fully: phase 1 drawings carry characteristic balloons, release drawings are PDF/A-2u (ISO 19005-2), and Bender's inflation factor cites its source. ELX and MEC phase board import in phase 2 with ECO's readers, and FLX follows contract 13.4's phases.

### Second review

Contract 17 accepts every second-review finding that targets the contract in some form, but declines two parts of revised findings. The tabs decline a few more parts and apply others in a different form.

| Finding | Tab | Declined or changed | Stated reason |
| --- | --- | --- | --- |
| R7-02, part 3 | FLX, ING | The near-maximal-set rule, declined | Contract 17: estimates are least reliable next to a singular set |
| R7-08 | Contract, FLX | A "Needs" column in contract 13.4, declined | Contract 17 states the prerequisite rule instead, and the spec check enforces it across tabs |
| R10-44 | KLN | Item numbers outside source, declined | A separate record would add a second identity, and ING and MEC already type the number (D-KLN-45) |
| R9-53, R8-36 | KLN, MEC | Floors of 2¹⁰ρ and 4ρ for the definition tolerance, declined | 2¹⁰ρ is Anvil's growth cap and would hide 0.49 mm changes on a 300 m hull; 4ρ sits too close to upgrade noise; the floor is 10ρ (R10-39) |
| R8-44 | MEC, MFG | Machining implicit regions through mesh-capable CAM, declined | STEP hand-offs need B-rep, which shops' CAM and CMM read (R10-37) |
| R8-24 | MEC | A 1 µm floor on the seed quantum, declined | The quantum scales with the sketch, so MEMS sketches keep sub-micrometre seeds |
| R10-41 | MEC | The DIN 6935 correction factor, declined | It could not be verified; the R/t-dependent default K comes from MFG's press-brake data |
| R10-45 | ELX | A binary sidecar for large data modules, declined | A region split keeps layouts as text (D-ELX-27, following R9-34) |
| R11-12 | AGT | A verifier review that counts only when its delegating human differs from the author's, declined | An unattested review shows as `Declared` and needs a human approval beside it, so a solo phase 1 user can still merge |
| R9-44 | PLT | Paragraphs of at most three sentences inside decisions, declined | Decision paragraphs keep their Decision, Why and Rejected sentences |
| R8-08 with R9-17; R8-20 with R9-16; R8-51 with R9-49 | ING | Each pair merged into one rule | One name-free key in sensitivity order; `instances(of:, at:, min:)`; R8-51's condensation with R9-49's 4,096-symbol threshold |
| R9-18 | ING | No second front-end key | Releases emit bit-identical IIR, so code hashes never depend on which release ran first |
| R7-16 | FLX, COV | Four phase 1 calibration classes, not five | One immersed treatment serves both fidelities, and inherent strain left phase 1 |
| R7-25 | FLX | Sheet lattices in phase 2 | GP2 uses strut lattices |
| R12-02 to R12-04, R12-12, R12-22, R7-27 | Contract, PLT, UIX, AGT, FLX, ANV | Contract 13.2's form instead of staffing lines | The program has no human team; CI capacity enters each phase budget |
| R12-15, R11-05 | PLT, UIX | One approval path | No native WebAuthn and no in-app webview: every client approves in a browser on the approval origin |
| R12-06, R12-18 | PLT | The laptop model and browser memory figures | Fixed at the phase 0 gate by stated rules, since the measurements do not exist yet |
| R12-33, item 7 | UIX | 90% task success | UIX's target at each gate (D-UIX-32), not a contract gate |
| R11-13 | KLN | Asset endorsement | As contract 17 revised it: merging the import Proposal endorses typed values, with no separate record |
| R11-18 | KLN | External approvals | Recorded as "approved externally", with no new Act name |
| R9-52 | KLN | Contact in merges | Only positive-volume interference counts; touching stays a conflict unless designed contact explains it |
| R11-19 | AGT, KLN | Recurring transfers | Effects of one approved standing release (D-AGT-33, contract 7.6) |
| R11-29, R11-32, R11-49 | ECO | Digital Services Act articles, ISO permission, numbering-authority scope | Articles 20 and 30 adopted by choice; the permission and the numbering-authority scope follow milestones, not dates or a team |
| R12-11 | MFG | The polymer branch for GP2 | Lapses: contract 13.1 fixes GP2 as metal laser powder bed fusion |
| R7-09 | MFG | GP5's cell count | An estimate over an assumed cavity area until GP5's design exists |
| R10-36 | MEC | Dialect conversion | Exact translation plus typed holes; nothing is translated approximately |
| R9-26 | ECO | The WIT package index | ECO keeps a short table of its own four packages beside the index |

Many partial applications split a shared finding: each tab applied its part and named the owner of the rest. ANV leaves the rest of R7-08, R7-09, R7-25 and R8-17 to FLX and of R8-09, R8-23, R8-34 and R9-22 to MEC; COV states one-line consequences of six FLX-owned fixes (R7-05, R7-11, R7-13, R7-15, R7-21, R7-24); MFG leaves ratings, gear data and board spacing (R10-18, R10-25) to COV, MEC and ELX.

## What the reviews changed

Rules that several tabs stated differently moved into the contract once, and the tabs replaced their restatements with pointers. The contract grew from 7,491 words (v3) to 14,022 (v5) and 20,109 (v6.1). The twelve tabs, Sources excluded, fell from 290,613 words at `round-1` to 217,650 at `round-2` and stand at 218,789 now.

### In kind

The first review changed five things:

1. **Names never steer geometry.** Every Body has a `GeometryId` beside its `ObjectId`, call sites come from source text, and operations are invariant under renaming.
2. **Bounds claim only what a proof gives.** A `Guaranteed` bound needs a proof in its own norm, peaks are regularized goals, and an unquantified part makes a `Pass` conditional.
3. **Trust follows data.** Labels travel with model contexts, merges never endorse free text, and only trusted builders feed attestations.
4. **Crucible never starts motion.** Physical-effect Acts transfer data or start a print or rig test under stated conditions; a person starts machines at the device.
5. **Phase 1 is a wedge.** It holds only what GP1 and GP2 need.

The second review changed five more:

6. **Approvals bind what ships.** Every affected Item's definition, of every kind and with its definitional attributes, enters the approval subject, and `act.commit` recomputes it.
7. **Safety holds on the wire.** Transfers are verified at the protocol level, drip feed is pull-only, and robot programs go only into the program store.
8. **Confidentiality and integrity are separate.** Write-down compares confidentiality only, evaluated free text keeps its integrity, and a host cannot reset its own context label.
9. **Calibration is earned per result.** A calibrated bound counts its miss rate, holds only inside its class envelope, and a `SignOff` `Pass` resting on it is confirmed by one refinement.
10. **Agents build Crucible.** One founder directs, Claude orchestrates, separate agent roles write oracles, build and verify, and phases end at gates.

### Contract versions

| Version | Marked by | What it rules | Words |
| --- | --- | --- | --- |
| v3 | Tag `round-1` | Section 14, on the first drafts' change requests: three-valued checks, `Approx<T>` and `Tol<T>`, product-domain Fields, External Ops, `Network`, platform classes. The first review attacked this text | 7,491 |
| v4 | Tag `contract-v4` | Section 15, on 81 first-review findings: two identities, the label lattice, Aborts, error bounds and `CheckOutcome`, per-region discretization, Act approvals and physical safety, cache trust, the program plan, performance targets | 12,388 |
| v4.1 | Commit "Contract v4.1" | CCR-ANV-7, CCR-ANV-8 and CCR-FLX-8: fidelity per rebuild row, unpropagated bounds as `NotQuantified`, a `regularization` error source | 12,562 |
| v4.2 | Commit "Contract v4.2" | CCR-FLX-9 and R1-35: the shared phase table, section 13.4 | 13,183 |
| v5 | Commit "Contract v5"; tags `round-2` and `second-review` | 21 requests from the ten tabs revised against v4.2, such as the merge verdict order, one list of physical-effect Acts and out-of-process third-party Wasm components. The second review attacked this text | 14,022 |
| v6 | Commit "Contract v6" | Section 17, on all 112 second-review findings that target the contract (81 accepted, 18 revised, 5 in a different form, 8 left to the tabs) and two pending requests (`apps/machine-gateway`, `flash_device`): definitional attributes and per-kind `ItemDefinition`s, wire-level transfer checks, split labels, third-party code kept out of attestation, calibrated bounds, an agent-built program | 19,638 |
| v6.1 | Commit "Contract v6.1" | Section 17, on the round 3 tabs' 18 change requests: name-free `DisplayPackage` pages, eigenvalue bounds, `<family>/<code>` error codes, standing releases, AAL3 scope, a five-year support period per release line | 20,109 |

Section 16 records 25 accepted requests in 23 rows, because two pairs of overlapping requests are ruled together. No change request filed in round 2 or round 3 was declined.

### The shared phase table

Round 1 tabs phased shared physics differently (R1-35): modal analysis was phase 1 in COV and phase 2 in Flux, and fibre orientation phase 3 in COV and phase 4 in MFG. Contract 13.4 now sets one phase for each capability that several tabs phase.

- **Rule.** A capability lands in the phase of the first gate that needs it; one that no gate needs takes the latest phase any tab proposed. Since round 3, nothing is phased before its prerequisites or before the owner's row it names, and the spec check enforces this across tabs (R7-08, R9-32).
- **Ownership.** The owner's capability table specifies the capability; every other tab states the phase in one line and cites 13.4.
- **Size.** 21 rows in v4.2, 23 in v5 (CCR-ELX-8's two battery rows) and 25 in v6. As-built strut calibration (phase 1) and gear, bearing and shaft ratings (phase 2) join, and inherent strain moves from phase 1 to 2 with supports, baseplate cut, support removal and stress relief (R7-06, R7-07, R7-19). Three neighbouring capabilities keep their own tab's phase.
- **R1-35.** Its proposed phases hold except two: DFN battery cells go to phase 5 because no gate names them, and inherent strain goes to phase 2.

| Phase | Rows in v5 | Rows now | Owners now |
| --- | --- | --- | --- |
| 1 | 2 | 2 | FLX 1, MFG 1 |
| 2 | 2 | 4 | FLX 2, MFG 1, COV 1 |
| 3 | 5 | 5 | FLX 2, MFG 3 |
| 4 | 7 | 7 | FLX 3, ELX 2, MEC 1, MFG 1 |
| 5 | 5 | 5 | FLX 2, COV 2, MFG 1 |
| 6 | 2 | 2 | ELX 1, MFG 1 |
| Total | 23 | 25 | FLX 10, MFG 8, COV 3, ELX 3, MEC 1 |

### The program plan

Round 2 answered R6-01 with a staffed plan: headcount, engineer-years and a gate at month 36. The second review showed it could not carry agent work, because people had to write the oracles first (R12-02) and scope had grown without approval (R12-03). Contract v6 replaces it in section 13.2.

- **Roles.** The founder approves each phase's scope and budget, golden-product criteria, every Act and every waiver. Claude orchestrates; an oracle role, builders and an independent verifier are separate agent roles; outside firms make, measure and advise.
- **Gates, not dates.** Milestones are ordered, not dated, and no plan figure counts people or engineer-years. One budget per phase covers agent compute, CI, rented hardware, physical runs, metrology and counsel.
- **Build program.** Oracles come first, each with a runner class; corpora agree with an independent source; work items name oracle ids and held-out splits (D-PLT-45). Four chains form the critical path: geometry, physics and printing, interface, and release.

### Length

R3-38 to R3-45 and R3-52 to R3-55 measured eleven of twelve round 1 tabs over their caps. The table counts words before `## Sources` at each tag, as the spec check does; that is what the cap limits.

| Tab | `round-1` | `round-2` | Now | Change since round 1 |
| --- | --- | --- | --- | --- |
| ING | 30,303 | 19,616 | 19,888 | −34% |
| ANV | 32,040 | 19,964 | 19,945 | −38% |
| FLX | 22,244 | 17,872 | 17,997 | −19% |
| COV | 17,450 | 17,817 | 17,720 | +2% |
| KLN | 25,499 | 17,944 | 17,989 | −29% |
| MEC | 19,646 | 17,861 | 17,968 | −9% |
| MFG | 23,874 | 17,799 | 17,900 | −25% |
| ELX | 23,155 | 17,415 | 17,993 | −22% |
| AGT | 22,335 | 17,786 | 17,908 | −20% |
| UIX | 25,670 | 17,876 | 17,945 | −30% |
| ECO | 24,336 | 17,867 | 17,738 | −27% |
| PLT | 24,061 | 17,833 | 17,798 | −26% |
| Total | 290,613 | 217,650 | 218,789 | −25% |

ING and ANV fit their 20,000-word cap and the other ten fit 18,000. Round 3 absorbed 278 findings in 1,139 more words; its brief asked each tab to make room by cutting restatement. Whole files grew from 224,644 to 230,227 words as Sources gained links, and against `round-2` the spec check finds no decision or source cut and one oracle merged (COV-O-ENV-2 into FLX-O-ERR-9).

### Open questions and unverified claims

The second review proposed an answer to each open question, and the round 3 brief asked every tab to decide it, turn it into a change request or keep it with a reason. Twelve stay open, four of them new.

| Tab | Questions at `round-2` | Open now | What stays open, and why | `[unverified]` marks: `round-1`, `round-2`, now |
| --- | --- | --- | --- | --- |
| ING | 9 | 0 | | 20, 14, 0 |
| ANV | 7 | 1 | The mesh Boolean method waits for the phase 0 bake-off | 4, 3, 0 |
| FLX | 9 | 1 | Guaranteed bounds on cut cells are research deferred past phase 1 | 76, 44, 0 |
| COV | 10 | 3 | New: the strut waviness threshold needs the first calibration build; sheet lattices in GP2 wait for the phase 0 gate; gear and bearing envelope limits need the licensed standards | 58, 63, 0 |
| KLN | 8 | 0 | | 17, 15, 0 |
| MEC | 8 | 1 | Distributor terms for tabulated standards values wait for counsel | 39, 32, 0 |
| MFG | 9 | 2 | Freedom to operate for adaptive clearing waits for counsel; GP2's build-preparation software is fixed at the phase 0 gate (new) | 46, 46, 0 |
| ELX | 11 | 2 | The Verilog-A front end waits for the research track; CUDA and ROCm wait for the phase 4 gate (R1-39's record, now a question) | 55, 37, 0 |
| AGT | 11 | 1 | Auto-merge thresholds wait for phase 2 review data | 8, 6, 0 |
| UIX | 9 | 0 | | 19, 16, 0 |
| ECO | 11 | 1 | The translator vendor depends on terms only negotiation reveals | 68, 53, 0 |
| PLT | 11 | 0 | | 14, 5, 0 |
| Total | 113 | 12 | | 424, 334, 0 |

The question counts leave out the findings records and the two round 3 contract requests that some tabs filed under Open questions. No tab now marks a claim `[unverified]`: round 3 verified each on a primary source, corrected it or cut it. The tabs' Sources hold 733 links at `round-1`, 866 at `round-2` and 1,312 now.

### Decisions and oracles

Decision numbers are stable. A changed decision keeps its number and ends with its latest marker, "(revised in round 3)" replacing "(revised in round 2)"; a new one takes the next free number. Revision counts are markers at each tag, so a decision revised in both rounds counts in each.

| Tab | Decisions at `round-1` | Added in round 2 | Revised in round 2 | Added in round 3 | Revised in round 3 | Decisions now | Oracle ids, `round-2` → now |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ING | 19 | 6 | 10 | 2 | 7 | 27 | 36 → 38 |
| ANV | 23 | 8 | 12 | 5 | 13 | 36 | 129 → 139 |
| FLX | 22 | 16 | 18 | 8 | 15 | 46 | 77 → 82 |
| COV | 16 | 7 | 10 | 7 | 10 | 30 | 40 → 42 |
| KLN | 35 | 9 | 17 | 5 | 20 | 49 | 66 → 68 |
| MEC | 25 | 5 | 13 | 7 | 11 | 37 | 82 → 84 |
| MFG | 21 | 8 | 8 | 5 | 13 | 34 | 117 → 121 |
| ELX | 20 | 6 | 14 | 5 | 7 | 31 | 60 → 62 |
| AGT | 23 | 9 | 11 | 2 | 21 | 34 | 24 → 24 |
| UIX | 23 | 7 | 13 | 3 | 8 | 33 | 51 → 53 |
| ECO | 25 | 7 | 10 | 5 | 15 | 37 | 33 → 34 |
| PLT | 28 | 12 | 14 | 7 | 23 | 47 | 53 → 57 |
| Total | 280 | 100 | 150 | 61 | 163 | 441 | 768 → 804 |

Round 2 added the most decisions to FLX, where most physics fixes land; round 3 revised the most in PLT, AGT and KLN, where the security, approval and platform fixes land. Round 2 also gave every tab `<TAB>-O-<name>` oracle ids defined once under Oracles: AGT and ECO renamed `O-AGT-n` and `O-ECO-n`, UIX mapped its `uix_` names one to one, COV and KLN replaced path names, and FLX, MFG and PLT gave ids to unnamed rows.

## Sources

| Source | Link |
| --- | --- |
| First review brief | Git tag `review`, `docs/review/brief.md` |
| Second review brief | [../review/brief.md](../review/brief.md) |
| First review reports, R1 to R6 | [R1 physics](../review/R1-physics.md), [R2 geometry](../review/R2-geometry.md), [R3 architecture](../review/R3-architecture.md), [R4 practice](../review/R4-practice.md), [R5 security and legal](../review/R5-security-legal.md), [R6 feasibility](../review/R6-feasibility.md) |
| Second review reports, R7 to R12 | [R7 physics](../review/R7-physics.md), [R8 geometry](../review/R8-geometry.md), [R9 architecture](../review/R9-architecture.md), [R10 practice](../review/R10-practice.md), [R11 security and legal](../review/R11-security-legal.md), [R12 feasibility](../review/R12-feasibility.md) |
| All 573 findings, parsed | [../review/findings.json](../review/findings.json) |
| Contract v6.1: glossary (2), core types (5), decided architecture (7), platforms (9), taste (10), writing rules (11), crate map (12), roadmap, program plan, targets and shared phases (13) | [../contract.md](../contract.md) |
| Contract ruling logs: round 1 (14), first review (15), round 2 requests (16), second review and round 3 requests (17) | [../contract.md](../contract.md) |
| Revision brief and consistency pass brief (round 3) | [../revision/brief.md](../revision/brief.md), [../revision/consistency.md](../revision/consistency.md) |
| Revision packets (round 3) | [ING](../revision/packets/ING.md), [ANV](../revision/packets/ANV.md), [FLX](../revision/packets/FLX.md), [COV](../revision/packets/COV.md), [KLN](../revision/packets/KLN.md), [MEC](../revision/packets/MEC.md), [MFG](../revision/packets/MFG.md), [ELX](../revision/packets/ELX.md), [AGT](../revision/packets/AGT.md), [UIX](../revision/packets/UIX.md), [ECO](../revision/packets/ECO.md), [PLT](../revision/packets/PLT.md) |
| Revised tabs | [ING](01-ingot.md), [ANV](02-anvil.md), [FLX](03-flux.md), [COV](04-coverage.md), [KLN](05-kiln-repo-plm.md), [MEC](06-mechanical.md), [MFG](07-manufacturing.md), [ELX](08-electronics-systems.md), [AGT](09-agents.md), [UIX](10-ui.md), [ECO](11-interop-ecosystem.md), [PLT](12-platform-performance.md) |
| Round 1 drafts and contract v3; contract v4 and the round 2 packets; the v2 tabs and contract v5 | Git tags `round-1`, `contract-v4`, `round-2` |
| Declined findings, decisions added and revised, word counts | Revision commit messages: `git log round-1..round-2 -- docs/spec docs/contract.md` and `git log second-review..HEAD -- docs/spec docs/contract.md` |
