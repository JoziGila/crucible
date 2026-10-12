# Adversarial review

Three adversarial reviews have attacked the spec. The first two each set six reviewers on the same six angles: the first filed 295 findings (23 Critical) against contract v3 and the round 1 drafts, and the second filed 278 (16 Critical) against contract v5 and the round 2 tabs. The third set nine reviewers on contract v6.1 and the round 3 tabs, against a higher bar (better than every incumbent, elegant, and a pleasure to read), and filed 312 findings (18 Critical).

Each review changed the spec in its own way. The first moved shared rules into the contract, added the shared phase table and cut the tabs by a quarter. The second found fixes that did not hold, hardened approvals, machine safety and labels, and rebuilt the program around agents and one founder. The third deleted mechanisms that did one job twice, set a parity floor against the incumbents, made the interface a viewer first, and rewrote every tab to teach before it specifies; contract v7 and v7.1 rule on all of it.

## How the reviews worked

Each review attacked one tagged text and is itself tagged. The first attacked `round-1` and is tagged `review`, the second attacked `round-2` and is tagged `second-review`, and the third attacked `round-3` and is tagged `third-review`. `findings.json` parses all twenty-one reports into one record per finding, 885 in all.

### Three briefs

All three briefs gave every reviewer the same core rules:

- Find what is wrong, missing, inconsistent, infeasible, below the state of the art, unsafe, legally risky or tasteless, and propose a concrete fix for each. No praise and no restatement.
- Read the contract first and do not re-report its rulings; report a ruling that is itself wrong.
- Verify load-bearing claims with WebFetch on primary sources, and cite only pages opened.
- Write 25 to 60 findings, most severe first, each naming its targets by tab code (or CONTRACT) with section, problem, evidence and fix.

The second brief, at tag `second-review` (the first stays at tag `review`), added four duties:

- **Fixes that hold.** Read this tab's record of the first review first. Report a first-review fix that does not hold, a fix that created a new problem, and a declined finding whose reason is wrong.
- **Buildability.** Report a capability whose contract, types, failure or oracle is too vague to build against, and an oracle whose pass criterion is not machine-checkable.
- **Open questions.** Propose an answer to each open question in the reviewer's area, as a finding whose fix is the decision.
- **Claims.** Verify each `[unverified]` claim on a primary source. A refuted claim is a finding; a confirmed one goes under "Verified claims" in the report.

The third brief, at `docs/review/brief.md`, calls itself the last review before building starts. It keeps the duty to report earlier fixes that do not hold, adds the Overview as a target (OVERVIEW), and sets a bar in three parts:

- **Better than everything.** An engineer who uses NX, CATIA, Creo, SOLIDWORKS, Fusion, Onshape, Ansys, Abaqus, COMSOL, Altium, KiCad, Mastercam, hyperMILL, Teamcenter or Windchill finds nothing they rely on missing, and finds clear reasons to switch. AI-built clones already copy interfaces quickly, so Crucible must win on what they cannot copy.
- **Elegant.** One concept per name, one fact per place, and the fewest mechanisms that do the job. Reviewers may propose replacing, merging or cutting a mechanism, and say what to delete.
- **A pleasure to read.** A human engineer reads each tab from start to finish and understands it: a clear lead, sections that build on each other, and terms defined before use.

| Severity | Definition from the second brief | First review | Second review | Third review |
| --- | --- | --- | --- | --- |
| Critical | Breaks a founder requirement, a principle or the architecture; a false or dangerous claim; something that cannot work or cannot be built as specified | 23 | 16 | 18 |
| Major | A significant gap, an inconsistency between tabs, a method clearly below the state of the art, an infeasible target, a missing capability practitioners need, or an open question that blocks building | 193 | 157 | 163 |
| Minor | A local precision, wording or ordering problem | 79 | 105 | 131 |
| Total | | 295 | 278 | 312 |

The first brief lacked "or cannot be built" and "an open question that blocks building"; the rest of each definition is the same. The third brief widens all three levels to match its bar. A Critical finding may also be "a gap that would make a serious engineer choose an incumbent instead". A Major one may be a design with "a clearly simpler or stronger alternative" or a section "a careful reader cannot follow", and a Minor one may be a readability problem.

### The reviewers

R7 to R12 repeat R1 to R6 in order. Each reviewer read its primary tabs in full and the sections of other tabs its angle touched. Counts read Critical, Major, Minor (total).

| Angle | What it covers | First review | Second review |
| --- | --- | --- | --- |
| Physics (R1, R7) | Error bounds, discretization, solvers, validity envelopes, physics coverage | 4, 37, 16 (57) | 3, 26, 15 (44) |
| Geometry (R2, R8) | Kernel determinism, error propagation, entity naming, blends, GD&T | 5, 26, 17 (48) | 3, 21, 27 (51) |
| Architecture and taste (R3, R9) | Identity and caching, labels, Ingot–Kiln semantics, coherence and length | 4, 41, 10 (55) | 2, 32, 20 (54) |
| Engineering practice (R4, R10) | Shop-floor safety, CAM, drawings, PLM, board design, enterprise workflows | 4, 27, 11 (42) | 2, 28, 15 (45) |
| Security and legal (R5, R11) | Labels and prompt injection, supply chain, approvals, licences, export control, privacy | 4, 26, 16 (46) | 4, 30, 15 (49) |
| Feasibility (R6, R12) | Program, phase 1 scope, performance targets, platform runtimes | 2, 36, 9 (47) | 2, 20, 13 (35) |
| All | | 23, 193, 79 (295) | 16, 157, 105 (278) |

The second review's reports list 118 claims verified on primary sources (R7 27, R8 20, R9 15, R10 15, R11 18, R12 23), and 68 of its findings name an open question in their section line. Several report a first-review fix that does not hold: R7-03 (R1-02's slenderness rule), R8-03 (R2-03's propagation rules), R10-01 (R4-01's no-start rule), R11-02 (R5-02's free-text rule) and R11-03 (R5-03's cache trust).

The third review keeps the six angles as R13 to R18 and widens two of them. R15 judges elegance as well as architecture, and R18 asks whether the Rust types, crates and build actually compile together. Three new lenses follow: R19 and R20 compare Crucible feature by feature with the incumbents and the AI-built clones, and R21 reads the spec as a human engineer would.

| Reviewer | Lens | What it covers | Critical, Major, Minor (total) |
| --- | --- | --- | --- |
| R13 | Physics | Error bounds and calibration, the canonical check, validation before release, dynamics, phase prerequisites | 2, 20, 13 (35) |
| R14 | Geometry | Error propagation, rebuild robustness, intersection classes per phase, tolerance realization, drawings | 2, 17, 21 (40) |
| R15 | Architecture and elegance | Mechanisms that do one job twice, one name per concept, keys and reproducible verdicts, crate structure | 2, 18, 18 (38) |
| R16 | Engineering practice | Approval ceremony in daily loops, machine programs and prove-out, sketching, review routing, electronics review | 1, 18, 12 (31) |
| R17 | Security and legal | Local agents and credentials, approval-credential enrolment, the agent-built program's supply chain, export control, liability, product names | 3, 20, 15 (38) |
| R18 | Feasibility and the Rust implementation | Whether the operation contract, closure hashes, crate map, browser build and oracle-first program can be built in Rust | 3, 17, 15 (35) |
| R19 | Parity for design, manufacturing and PLM | NX, SOLIDWORKS, Onshape, Mastercam and Windchill workflows, and the clones SolidCraft and CADCraft | 2, 15, 11 (28) |
| R20 | Parity for simulation and electronics | Ansys, Abaqus, COMSOL, Nastran, SPICE tools and Modelica: idealizations, reduced models, dynamics, flow, RF | 2, 19, 12 (33) |
| R21 | Editorial | Human reading: the trust qualifiers, review history in prose, leads, the house style, the contract's form | 1, 19, 14 (34) |
| All | | | 18, 163, 131 (312) |

Like the second review, the third found earlier fixes that do not hold or that created a new problem:

- **R13-01.** R7-02's fix to the canonical check excludes 8 mm above the clamped face, which removes the fillet the check most needs to judge.
- **R14-03.** R8-15's fix still lets phase 1 operations (loft, general sweep, twisted extrusion) make surfaces that no phase 1 intersection class covers.
- **R18-02.** R9-06's frozen "source closure" of Rust modules has no mechanical definition, so it cannot be computed.
- **R18-05.** R12-13's held-out split uses a fixed hash over public corpora, which a builder can compute for itself.
- **R19-03.** R11-30's licensed standards tables leave a new user's first M5 tapped hole failing with `UnknownSize`.
- **R20-17.** R4-23's fix runs vendor SPICE models only as External Ops on remote Linux workers, out of reach on a laptop.
- **R21-03.** The first review's cut of the tabs by a quarter removed connective prose, because the rules forbade cutting capabilities.
- **R13-04.** The prerequisite check that contract 13.4 and this tab credited to the spec check did not exist. `check.py` now enforces it through `Requires:` entries.

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

The third review also targets the Overview. 73 of its findings name one target and 239 name two or more; R21-02 names all twelve tabs and the contract.

| Target | Critical | Major | Minor | Total (sole) |
| --- | --- | --- | --- | --- |
| ING | 5 | 21 | 16 | 42 (3) |
| ANV | 6 | 35 | 22 | 63 (10) |
| FLX | 7 | 52 | 23 | 82 (6) |
| COV | 5 | 39 | 9 | 53 (5) |
| KLN | 11 | 57 | 31 | 99 (5) |
| MEC | 5 | 42 | 33 | 80 (10) |
| MFG | 3 | 31 | 12 | 46 (6) |
| ELX | 0 | 20 | 15 | 35 (6) |
| AGT | 5 | 30 | 18 | 53 (4) |
| UIX | 6 | 29 | 19 | 54 (2) |
| ECO | 0 | 28 | 12 | 40 (4) |
| PLT | 6 | 27 | 18 | 51 (2) |
| OVERVIEW | 2 | 6 | 3 | 11 (4) |
| CONTRACT | 14 | 65 | 32 | 111 (6) |

KLN again draws the most findings of any tab. FLX and MEC come next, because the parity reviews found most of their gaps in analysis workflows and in mechanical design. The contract draws 14 of the 18 Critical findings; the other four are fixed in the tabs, three of them (R19-01, R19-02, R20-01) through contract 13.4's parity floor.

### From findings to revised tabs

All three rounds ran the same pipeline.

1. **The contract rules first.** Section 15 (v4) rules on 81 first-review findings (20 Critical, 54 Major, 7 Minor): 72 of the 73 that target CONTRACT, since R3-49's naming drift is fixed in the tabs, and nine more whose fixes needed contract text. Section 17 (v6) rules on all 112 second-review findings that target CONTRACT and on two requests pending in round 2's open questions: `apps/machine-gateway` and the `flash_device` Act. Section 18 (v7) rules on all 111 third-review findings that target CONTRACT and on four directions from the founder, FD-1 to FD-4.
2. **Each tab gets a packet** with its findings in full and the contract changes that affect it. Round 3 packets add the tab's open questions with the reviewers' proposed answers, its `[unverified]` lines with the claims reviewers verified, and known items such as a reading sentence under each diagram. Round 4 packets carry the tab's third-review findings, its open questions and known items; the round 4 brief adds the software digest of what to adopt, port or study.
3. **One revision agent per tab applies its packet.** It applies every finding unless it has a sound reason, never cuts a decision, oracle or source whose claim stays, and passes the spec check. Round 2 revised ANV and FLX against v4 and the rest against v4.2, and round 3 revised all twelve against v6. Until round 3, a tab recorded each declined or partly applied finding under Open questions. Round 4 revised all twelve against v7 under a new brief: restructure to the teach-first skeleton, cover the parity floor, merge or delete mechanisms, and keep review history out of the tab. Declined parts now go only into the commit.
4. **Each revision lands as one commit** listing declined findings with reasons, decisions added and revised, and the word count.
5. **The tabs' change requests are ruled:** v4.1, v4.2 and v5 in section 16, v6.1 in section 17, and v7.1 in section 18, which accepts all six requests the round 4 tabs filed.
6. **A consistency pass aligns every tab with the latest contract:** names, shared phases, interface rows and citations. Round 3's pass applies 135 audited edits, and where two tabs disagree the owner's text wins. Round 4 runs the same audited pass after its revisions, before the summary tabs.

A finding with several targets is shared: each tab changes only what it owns and points to the owner for the rest.

## Critical findings

Each resolution below was checked against the committed text: the first two reviews' at the head of round 3, and the third's against contract v7.1 and the round 4 tabs. All 57 Critical findings have a committed resolution, except the Overview's share of R19-01 and R21-01, which arrives with the round 4 summary tabs. Where round 3 changed a first-review fix, the Status column says so; every decision cited in the second table was added or revised in round 3.

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
| R6-01 | CONTRACT, PLT | No critical path, and phases 0 and 1 as written were far larger than the program could carry | Round 2's contract 13.2 set a plan sized for a human team and fixed to dates. Round 3 replaced it (R12-02 to R12-04): one founder, agent roles, gates instead of dates, a budget per phase | Resolved; superseded in round 3 |
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

### Third review: 18 Critical findings

The third review's Critical findings ask new kinds of question. Four ask whether agents can build the design in Rust (R17-03, R18-01 to R18-03). Four ask whether it competes with the incumbents at all (R19-01, R19-02, R20-01, R20-02), and one whether a reader can follow it (R21-01).

Fourteen target the contract, and section 18 rules on each: eleven accepted, and R13-01, R18-02 and R21-01 accepted with a revised fix. R14-01 is ANV's alone. R19-01, R19-02 and R20-01 reach the contract through the founder's direction FD-3, which turns the parity reviewers' findings into the parity floor of contract 13.4.

| Id | Targets | Problem | Resolution | Status |
| --- | --- | --- | --- | --- |
| R13-01 | CONTRACT, ING, FLX | The canonical check excluded everything within 8 mm of the clamped face, including the web-root fillet where bending stress peaks, so a bracket whose root fails returned `Pass` | Contract 6 and 7.1: the check reads `study.regular()`, the Part minus the default neighbourhood of each singular set Flux flags for that study; the load direction is stated; a maximum on an exclusion boundary is `Undecided { MaximumAtExclusion }` with the fix "model the support". The default thickness is 6 mm. D-FLX-39; ING's canonical oracle: the region contains the web-root fillet, `Pass` at 6 mm and `Fail` at 4 mm | Resolved with a revised fix: singular sets belong to the study, not the Part |
| R13-02 | CONTRACT, MEC, COV, KLN | Phase 1 releases leaned on proof loads of articles made after the release, and a strain gauge cannot measure the fillet peak the checks decide | Contract 13.1 and 13.2: a validation campaign on separate specimens, with gauges and stereo image correlation at the regularization radius, precedes the run build and governs the releases; proof loads become held-out confirmation through gauge functionals (FLX's `f.gauge`). COV raises a model's credibility level for the listed response quantities before any release relies on it | Resolved; V&V 20's k and α are fixed (R13-09) |
| R14-01 | ANV | The propagation row max(p_a, p_b) / sin θ understated how far an intersection edge moves below 120° (a box edge moves p√2) and ignored curvature near tangency | ANV's propagation table: √(p_a² + p_b² + 2·p_a·p_b·\|cos θ\|) / sin θ, valid only where a certified curvature bound gives max(p_a, p_b)·κ̂ ≤ sin²θ / 4, otherwise `NotQuantified`; ANV-O-CONV-2 perturbs supports and checks every reported bound | Resolved |
| R14-02 | ANV, MEC, CONTRACT | Blend robustness was measured per case against OCCT, on a corpus that Parasolid built and OCCT filtered; 95% per fillet means a part with 20 fillets rebuilds about one time in three | Contract 13.1: GP1-class parts in the part-level rebuild corpus meet ANV's phase 1 target. D-ANV-38, ANV-O-PARITY-1: whole in-scope parts rebuild against their Parasolid originals, 98% at phase 1 and 99.5% at phase 2 | Resolved |
| R15-01 | CONTRACT, ING, COV, KLN | `Pass { conditional_on }` meant three things in three places, and the policy allowance that changed a verdict entered no key, so one Change could give two gate results | Contract 5.6: `conditional_on` and the re-evaluation pass are deleted. Allowances are records in pinned policy packages that a check reads like any input, so they enter its key, and `CheckOutcome.allowances` lists them | Resolved; the merge order loses a special case and the gate predicate a clause |
| R15-02 | CONTRACT, KLN, AGT, ING | Free-text integrity joined into node labels, so one untrusted name on a merged supplier part tainted every downstream mass, stress and drawing | Contract 5.3: a string evaluated from a free-text span is an `ExternalText` value that carries the span's integrity; node labels carry the integrity of typed inputs, plus text turned into non-text values. D-ING-24 | Resolved |
| R16-01 | CONTRACT, AGT, UIX, MFG, KLN | Every denial blocked re-preparing a plan for 24 h, so an ordinary "fix op 3" rejection locked a programmer out of the machine until the next day | Contract 7.6: three outcomes. *Approve*; *return for changes*, which closes the request without penalty; *deny as suspicious*, which freezes the session and blocks re-preparing for 24 h. AGT's approval-outcomes row; UIX's approval page | Resolved; the pending limit is three per delegating human for agent-prepared plans (R17-25), not R16-01's per-recipient count |
| R17-01 | AGT, KLN, ING, PLT, CONTRACT | A local agent with a shell drove the CLI with the human's keychain credential, and its edits through an editor extension counted as typed by a person | Contract 7.6: a local credential without a fresh user-presence proof authenticates as the device agent `agent:<org>/local/<device>`; human-only methods need a WebAuthn assertion bound to the call's argument digest. ING: spans arriving through the language server are `data_untrusted` until the person confirms them; KLN trusts only spans typed in Crucible's own editor | Resolved |
| R17-02 | CONTRACT, UIX, AGT, KLN, PLT, MFG | Enrolling an approval credential needed only a signed-in session, so a phished single sign-on session or a stolen synced passkey could enrol an attacker's key | Contract 5.4: enrolment is a row of the signature table, approved by the person's existing credential (or, for a first credential, an `admin` plus a recorded identity check), announced out of band, and held 24 h before it approves a physical-effect Act or an Act with `controls`. UIX: a synced-passkey or single sign-on session can request enrolment but never complete it (UIX-O-APPR-1) | Resolved |
| R17-03 | CONTRACT, PLT, AGT | The agents that build Crucible read attacker-reachable crates, papers and pages, then wrote `safe-to-deploy` audits and engine code, with no taint model before phase 2 | Contract 13.2: from phase 0, a context that reads third-party content is `instruction_tainted`, writes only to its own branches, and needs the founder's Approval for changes to protected paths. An audit an agent writes counts only as `agent-reviewed`; `safe-to-deploy` comes from human audit sets or a quarantined, tool-less review the founder approves. PLT's dependency register | Resolved |
| R18-01 | KLN, PLT, FLX, ANV, CONTRACT | `OpImpl::eval` returned `Failure` while calls inside it returned `Abort`, so propagating with `?` forced a conversion that made Aborts cacheable | Contract 7.2 and KLN: operations return `OpResult<T>`, a `Result<T, Stop>` whose `Stop` is a `Failure` or an `Abort`, with no conversion between them; Kiln caches only failures. KLN-O-ABORT-2 is a compile-fail suite proving neither conversion exists | Resolved |
| R18-02 | CONTRACT, ANV, KLN, FLX, PLT | R9-06's frozen "source closure" of Rust modules had no mechanical definition and left third-party crates and most of Anvil outside it | Contract 4 and 12: one crate per operation family, each released version a frozen source directory; `cargo xtask closure-hash` computes the closure from frozen directories and lockfile checksums. D-ANV-18, D-KLN-2 | Resolved with a revised fix: the toolchain pin and `detmath` epoch sit beside the hash, so upgrades pass golden-hash checks instead of minting versions |
| R18-03 | CONTRACT, PLT, ANV, FLX, UIX | Locked oracles had to compile against crate APIs that did not exist yet, and a builder's API change broke them | Contract 13.2, "Interface first": the oracle role writes a contract crate of signatures with `unimplemented!()` bodies, which builders implement and may not change. Oracles bind to `api` methods, the CLI and file formats first, and `oracles/` is its own Cargo workspace. PLT refuses builder Changes to contract crates | Resolved |
| R19-01 | OVERVIEW, MEC, MFG, KLN, UIX, ANV | No page said why an engineer should leave an incumbent, or what an AI-built clone such as SolidCraft or CADCraft cannot copy, and phase 1 lacked formats the clones ship | Contract 1 (requirement 5) and 8: each tab's lead names its gain over the incumbents, and each tab carries a parity table that names clones where they ship first. Contract 13.4's parity floor puts DXF write and IGES read in phase 1, and sheet metal, kinematics and motion studies in phase 2 | Resolved in the contract and tabs; the Overview's comparison arrives with the summary tabs |
| R19-02 | MEC, KLN, UIX | D-MEC-13 forbade in-context design, which machine designers use every day | D-MEC-13: context pins evaluate the assembly at a pinned past Change, so a part designed in place creates no cycle; moving a pin is a Proposal that shows the geometry diff. Parity floor, phase 2 | Resolved; R16-10's gesture merges into context pins |
| R20-01 | FLX, COV, MEC, UIX | Flux had no remote points, point masses, springs, bushings or fastener connectors, the idealizations in nearly every incumbent model | FLX's Idealizations (D-FLX-47, FLX-O-IDEAL-1). Parity floor: remote points, point masses and springs in phase 1; bushings, fasteners and spot welds in phase 2 | Resolved |
| R20-02 | FLX, COV, CONTRACT | No tab offered planar, axisymmetric, symmetry or cyclic-sector models, which incumbents solve at a hundredth of the 3D cost | Contract 13.4: planar and axisymmetric elasticity and heat in phase 1; symmetry, antisymmetry and cyclic-sector reductions with cyclic modal analysis in phase 2. D-FLX-48: a broken symmetry returns `SymmetryBroken`, never a silent answer; FLX-O-SYM-1 | Resolved |
| R21-01 | OVERVIEW, CONTRACT, ING, FLX, COV, KLN | A reader met eleven qualifiers on one number, defined in seven places, and no page showed them working together | Contract 5.2: one binding table of ten qualifiers, each with the question it answers, its values and its owner; tabs cite it. Conditional verdicts and the separate solution-verification status are gone. ING and COV walk the bracket through it | Resolved with a revised fix: the table is binding in the contract rather than in the Overview, whose walkthrough arrives with the summary tabs |

## Major and Minor findings by theme

The first review's 272 Major and Minor findings and the second's 262 fall into eighteen themes, each finding under the theme of its main problem; the second review adds oracles and buildability, which its brief asked for. The third review's 294 are grouped by the part of its bar they test, in the last subsection. The fixes named are representative, each checked in the committed text at the head of round 3.

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

**First review.** Contract 13.4 sets one phase per shared capability (R1-35, R2-27), phase 1 has one forward renderer (D-UIX-24; R6-24) and one Ingot executor (D-ING-13; R6-25), GP1 uses the shop's own CAM (R6-05), and every core dependency has a risk register (D-PLT-40; R6-30). Round 2's sized and dated plan (R6-03, R6-04) is gone since round 3.

**Second review.** Round 2's plan absorbed scope without approval and left the interface and release chains off the critical path.

- Contract 13.2 has no human team and no dates: one budget per phase, approved by the founder, and four critical-path chains, with chains C (interface) and D (release) added (R12-03, R12-04, R12-09, R12-22).
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

### Third review: Major and Minor findings by bar

The third review's 294 Major and Minor findings are grouped here by the part of the bar they test, not by the eighteen themes, because its parity and editorial lenses cut across every theme. Each fix named was checked in contract v7.1's section 18 or in the tab's round 4 commit.

**Correct physics and geometry (R13, R14).** Bounds and calibration needed one set of rules.

- Every error part is stated in the bounded quantity's norm, every `Estimated` bound belongs to a calibration class or a named statistical method (otherwise it is an `Indicator`), and one rule sets α (contract 5.1; R13-03, R13-10, R13-23, R13-25). V&V 20's coverage factor and exceedance level are fixed (contract 13.1; R13-09).
- Calibration references come from an independent code on fitted high-order meshes, not from the code being calibrated (contract 13.2; R13-08). Drop and crash gates compare regularized functionals and ensemble statistics (contract 13.1, D-FLX-50; R13-17).
- Phase 1 closes over its own surfaces: lofts, non-circular sweeps and twisted or scaled extrusions move to phase 2 (contract 7.1, 13.2; R14-03). One `accept: [Merged, Partial, Fragile]` list replaces three Boolean flags on extent queries (contract 5.5; R14-33).
- COV decides stocky GP2 struts by a strut-strength check rather than buckling (R13-05), and FLX splits buckling from frequencies in its calibration classes (R13-11). ING adds a tolerance-zone section and `realize:`, which builds geometry at the mid-limit or a material-condition limit of every tolerance zone (R14-08).

**Elegance (R15).** Pairs of mechanisms did one job. Contract v7 merges each pair and deletes the loser (see "Simplifications in version 7" below), and its smaller rulings follow the same idea.

- One hash-consed expression type, `kernels::expr`, serves constraints, analytic Fields and weak forms (contract 7.5; R15-12). `NodeKey` keys every node kind (contract 7.2; R15-17).
- One signature table states who signs what, replacing scattered two-person, AAL3 and self-approval rules (contract 5.4; R15-15, R17-02, R17-04, R17-16). "Policy" names only Cedar policies and pinned policy packages (contract 2, 5.6; R15-20).
- `Interactive` names only a fidelity: lanes and priority classes use `Drag` and `Foreground` (contract 2; R15-16). Product services split into `repo`, `plm`, `trust` and `engine`, and domain crates never depend on `kiln` (contract 12; R15-18, R15-33).

**Engineering practice (R16).** Ceremony fit the aerospace path but not the daily loop.

- A program's machine class excludes controller and post versions, so a control update no longer voids every approved program, and one `ProgramSubject` defines what a program approval covers (contract 5.6, 7.6; R16-02, R16-03).
- A restricted `bench_session` Act covers repeated firmware flashes on a bench (contract 7.6; R16-04), and uncontrolled releases may be approved in a phone browser with a roaming security key (contract 7.6; R16-30). MFG adds a minimum-ceremony table for high-mix shops.
- A desktop may run an External Op locally as `Unverified`, at most `Interactive`, never cached and never gating (contract 7.8; R16-14).

**Security and legal (R17).** Besides the three Critical findings, R17 tightened exits and phase 0 counsel.

- Licences form a usage part of the label, compared only at exits; the exits are listed truthfully, and local writes need permitting licences (contract 5.3, 7.6; R15-06, R17-12). Uncleared people and suppliers share one derived-view mechanism with query budgets (contract 7.1; R15-07, R17-13).
- Attested clients, controlled devices, client flashing, the determinizer and the registry each gain a rule (contract 5.3, 7.4, 7.6, 7.7; R17-05, R17-11, R17-14, R17-15, R17-24).
- Counsel's phase 0 opinions cover authorship of agent-written code and the DCO, freedom to operate over all four phase 1 chains, every user-visible name, and the standards tables std may ship (contract 13.1; R17-17 to R17-19, R19-03). Product liability joins the phase 1 gate (CCR-ECO-13, after R17-23), and the hosted service refuses every comprehensively embargoed jurisdiction through a pinned dataset (D-ECO-29; R17-07).

**The Rust implementation (R18).** The tabs' Rust fragments did not compile together.

- The contract adds `api-schema`, erased canonical forms with generated typed views, portable core crates, a `material` crate, a native-code register for C and C++, and named lint mechanisms (contract 5, 7.3, 7.4, 7.5, 12; R18-04, R18-09, R18-10, R18-12, R18-14, R18-15).
- The browser engine splits into a primary module with a per-phase size budget, and the single-threaded web build moves to phase 2 (contract 9, 13.2, 13.3; R18-11, R18-20). Held-out splits are chosen by a keyed hash and reported as one aggregate verdict (contract 3, 13.2; R18-05).

**Parity (R19, R20).** Most parity findings became rows of contract 13.4's parity floor, described under "What the reviews changed".

- Design and manufacturing: sketch edits, threads computed from formulas, generative design, context pins, toolpath editing, DXF and DWG (R16-07, R16-09, R19-03, R19-05, R19-10, R19-11, R19-14).
- PLM: review routing and approval delegation, shape-similarity search, quality records and foreign native CAD files (R16-12, R19-07, R19-08, R19-16, R19-17).
- Simulation and electronics: linear dynamics, load combinations, stress linearization, submodeling, imported Nastran and Abaqus decks, rotating machinery, Floquet ports, RLCG extraction, Modelica source, fluid libraries and native vendor SPICE models (R13-16, R20-03, R20-06, R20-09 to R20-17, R20-21).

**Reading (R21).** The tabs read as the minutes of their own revision.

- R21-02 counted 482 finding ids and 235 "(revised in round N)" tags in running prose. Contract 11 now keeps review history out of every tab above Open questions, and `check.py` fails a tab that breaks the rule; this tab and the Decisions log hold the history instead.
- Leads say what the engineer gains (R21-07), each fact is decided once (R21-09), cross-references name the thing rather than a decision number (R21-10), Interfaces lists only what a tab provides (R21-11), citations follow one style (R21-12), and terms are defined at first use (R21-14).
- "Evidence" now means only Evidence records; a model's tested credibility is its credibility level, C0 to C4 (contract 2; R21-08). The contract itself gets a two-sentence lead and glossary rows that define and point (R21-02, R21-15).

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
| R7-08 | Contract, FLX | A "Needs" column in contract 13.4, declined | Contract 17 states the prerequisite rule instead; since round 4 the spec check enforces it through `Requires:` entries (R13-04) |
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
| R12-02 to R12-04, R12-12, R12-22, R7-27 | Contract, PLT, UIX, AGT, FLX, ANV | Contract 13.2's agent program instead of the proposed plan lines | The program has no human team; CI capacity enters each phase budget |
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

### Third review

Contract 18 rules on all 111 third-review findings that target the contract: it declines one and accepts eight with a revised fix. In round 4 the tabs keep review history out of their text, so a tab's declined and changed parts are stated only in its revision commit; ANV, COV, ELX, ECO and PLT record none.

| Finding | Tab | Declined or changed | Stated reason |
| --- | --- | --- | --- |
| R16-25 | Contract | Renaming the `SignOff` fidelity to `Final`, declined | Contract 18: "sign-off" analysis means final-accuracy verification in simulation and EDA practice; the glossary already forbids "sign-off" for Approvals, and a rename would touch every tab for no gain in precision |
| R13-01 | Contract, ING, FLX | `p.regular()` on the Part, changed to `study.regular()` | Singular sets belong to the study, not the Part; the default thickness becomes 6 mm, so the example passes and the oracle shows failure at 4 mm |
| R15-18 | Contract, KLN | The proposed split of KLN's product crate, changed | Contract 12 names `repo`, `plm`, `trust` and `engine`; KLN hands Deployment to PLT, while Privacy stays with `trust` |
| R15-19, R21-15 | Contract | Moving the ruling logs out of the contract, declined in part | The logs stay at the end of the contract as history, read only when a ruling is in question, because each version keeps its ruling log there; the lead, the glossary rows and the long bullets are rewritten as proposed |
| R18-02 | Contract, ANV, KLN | The toolchain pin and `detmath` epoch inside the closure hash, changed | They sit beside the hash, so toolchain and `detmath` upgrades pass golden-hash checks instead of minting new operation versions |
| R18-26 | Contract, PLT, AGT | Lane names `Pointer`, `Foreground`, `Background`, changed | R15-16's names win: `Drag`, `Foreground` and `Background` |
| R21-01 | Contract, Overview | The trust table in the Overview, changed | The table is binding, so it lives in contract 5.2; with conditional verdicts gone and solution verification folded into the budget, it has ten rows, and the Overview walks the bracket through it |
| R21-03 | Contract | 12,000 to 18,000 words of prose per tab, changed | Contract 11 caps prose at 9,000 to 15,000 words (ING and ANV 17,000), since tables, Reference and State of the art no longer count |
| R16-01, R17-25 | Contract, AGT | A pending limit per session, Act kind and recipient, changed | Contract 7.6 counts three pending requests per delegating human, across sessions, and only for agent-prepared plans |
| R20-06 | FLX | Running imported decks as `Unverified` until their oracle passes, changed | Each card family is enabled only once its oracle passes; until then its cards fail with `UnmappedCard` |
| R20-08 | FLX | Frictionless as the default for touching faces, changed | A no-separation tie is the default, which keeps phase 2 assemblies linear on the octree; frictionless octree contact follows in phase 3 |
| R20-10 | FLX | A `Guaranteed` bound on a stress-classification line, declined | A line average cannot carry a guaranteed bound in 3D, so linearization averages over a thin tube |
| R20-09 | FLX | A new `Combination` domain, changed | Load combinations reuse the `LoadCase` domain |
| R20-27 | FLX | Rendering reports through MEC's drawing pipeline in phase 2, changed | Reports render through UIX's phase 1 generated reports |
| R13-15 | FLX | 30 ms per further goal estimate, changed | 100 ms plus 20 ms per further goal, so five goals fit the 1 s budget |
| R13-17 | FLX | Verified SAE J211 filter classes | The standard is paywalled, so the classes stay `[unverified]` and each check declares its filter class |
| R16-20 | MEC | Face deletion and defeaturing in phase 1, declined | ANV keeps them in phase 2, and no phase 1 gate needs them |
| R16-11, item 3 | MEC | A Crucible-defined clearance-hole series, declined | It would read as a standard and drift from ISO 273; explicit diameters and fits cover the need |
| R16-10 | MEC, UIX | Live in-context references through `context_ref`, merged | Live references form cycles; context pins to a past Change (R19-02) serve the same gesture |
| R19-09 | UIX | Photoreal rendering in phase 3, changed | Contract 13.4 puts it earlier, in phase 2, under the founder's viewer-first direction |
| R16-07, R19-05, R16-12, R19-07 | UIX | UIX-owned names for toolpath edits and review routes | The modules and types belong to MFG and KLN; UIX presents them |
| R15-25 | KLN | Renaming the derivative retention tier in the tab | It would contradict contract 7.1, so KLN filed CCR-KLN-12, which v7.1 accepts (`StepState`); `OpCx::safe_point` is applied |
| R15-22 | KLN | Withdrawing D-KLN-11 to D-KLN-13, changed | The three numbers now hold KLN's own gate-acceptance rules instead of restating PLT's |
| R16-21, R17-07, R17-23, R17-36 | KLN | KLN's share | Left to their owners: declared mass in MEC (D-MEC-41), embargoes and translator-host signatures in ECO, and product liability through CCR-ECO-13 |
| R13-22 | MFG | Finite-cell solves on CT voxel bodies, changed | CT-scanned unit cells use FLX's phase 1 immersed solver |
| R16-19 | MFG | A shop-qualified signature kind for controller families, declined | Shop-qualified families merge under the ordinary branch rule |
| R15-11 | ING | Affine `Tol` arithmetic inside bodies, declined in part | Tolerances drop to nominal inside bodies, as the finding allowed, with a deny-by-default lint |
| R21-09 | ING | Removing ING's copies of D-ING-11 and D-ING-26 | Each keeps only ING's part, the language rule, and links to the owner |
| R21-19, R21-30 | ING | Linking the bracket walkthrough to the Overview | ING's walkthrough quotes and links the contract's canonical example |

Many shared findings split as before: each tab applied its part and named the owner of the rest. AGT, for example, adds the method, view and orchestration for review routes, item search and mass change, and leaves the records to KLN and MFG.

## What the reviews changed

Rules that several tabs stated differently moved into the contract once, and the tabs replaced their restatements with pointers. The contract grew from 7,491 words (v3) to 14,022 (v5), 20,109 (v6.1) and 30,445 (v7.1). The twelve tabs, Sources excluded, fell from 290,613 words at `round-1` to 217,650 at `round-2` and 218,789 at `round-3`; round 4 changed what the length rule counts, and "Length" below gives both measures.

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

The third review changed five more:

11. **One mechanism per job.** Version 7 deletes conditional verdicts, the evidence watermark, the live-editing CRDT, the separate deviation record and other mechanisms that duplicated one another. One signature table says who signs what. Item 2's conditional `Pass` is gone: an allowance is now a pinned input that a check reads.
12. **Nothing an incumbent's user relies on is missing.** The parity floor sets the latest phase for every capability the parity reviews found missing, and every tab compares itself with the incumbents and the AI-built clones in a parity table.
13. **Agents author; people view, review and present.** The interface is a fast viewer, a reviewer and a presentation studio first, held to a stated polish bar.
14. **Study the incumbents, never copy them.** The clean-room insight protocol separates the agents that observe licensed software from the agents that build.
15. **Teach first, then specify.** Every tab opens on a worked example, keeps reference material in its own section, and leaves review history to this tab and the Decisions log.

### Simplifications in version 7

R15 found pairs of mechanisms that did one job, and the founder's directions asked for the fewest mechanisms that serve. Version 7 deletes each loser in the same change, as contract 10 requires, and its ruling log lists the deletions.

| Deleted in version 7 | What does the job now | Ruling |
| --- | --- | --- |
| `Pass { conditional_on }` and the allowance re-evaluation | Policy allowances, read by checks as pinned inputs and listed in `CheckOutcome.allowances` | 5.6; R15-01 |
| The evidence watermark | Evidence records pinned under `[[evidence]]` in `ingot.lock`, like any External input | 5.6; R15-03, R17-20 |
| The Loro CRDT, block-id mapping and reconcile step | A server-sequenced edit log rebased with the branch `MergeDriver`, so live and branch merges share one semantics | 7.1; R15-04 |
| The separate deviation record, the `grant_deviation` Act and the compliance verdict enum | Waivers for every departure, and `CheckOutcome` for compliance checks | 5.4, 7.6; R15-05 |
| The module-signature path for uncleared readers | One derived-view mechanism for uncleared people and suppliers, with query budgets and `Withheld` outcomes | 7.1; R15-07, R17-13 |
| 100% spot re-execution of nodes that feed releases | Two-builder agreement for gates and `SignOff`, fan-out-weighted spot checks elsewhere, and full re-verification after toolchain or `detmath` upgrades | 7.8; R15-13 |
| A separate `SignOff` geometry computation | Geometry that certifies in place, so `Interactive` and `SignOff` geometry share one computation and identity | 7.1; R15-08 |
| `on_merge`, `on_partial` and `on_fragile` | One `accept:` list on extent queries | 5.5; R14-33 |
| `DiagnosticSeverity` | One `Severity`, with `Hint` | 5; R15-26 |
| The name `OpKey` | `NodeKey`, defined once for every node kind | 7.2; R15-17 |
| `unsafe` code in `kernels` | `kernels` emits code and `wasm-host` loads it; `unsafe` lives only in `simd`, `gpu`, `wasm-host`, `bridges/` and `apps/platform-*` | 7.5, 12 |
| Rules carried in glossary rows, and the version history in the lead | Glossary rows that define and point to a section, and a two-sentence lead | 2, lead; R15-19, R21-02, R21-15 |

The tabs delete in the same spirit. AGT folds `share_external` and `notify_external` into `export`, MEC makes in-context design one mechanism and generative design one feature, MFG has one toolpath-editing package, and UIX one presentation file kind. ING, COV, ELX and UIX drop their copies of the conditional verdict, and ECO deletes a copied licence table.

### Contract versions

| Version | Marked by | What it rules | Words |
| --- | --- | --- | --- |
| v3 | Tag `round-1` | Section 14, on the first drafts' change requests: three-valued checks, `Approx<T>` and `Tol<T>`, product-domain Fields, External Ops, `Network`, platform classes. The first review attacked this text | 7,491 |
| v4 | Tag `contract-v4` | Section 15, on 81 first-review findings: two identities, the label lattice, Aborts, error bounds and `CheckOutcome`, per-region discretization, Act approvals and physical safety, cache trust, the program plan, performance targets | 12,388 |
| v4.1 | Commit "Contract v4.1" | CCR-ANV-7, CCR-ANV-8 and CCR-FLX-8: fidelity per rebuild row, unpropagated bounds as `NotQuantified`, a `regularization` error source | 12,562 |
| v4.2 | Commit "Contract v4.2" | CCR-FLX-9 and R1-35: the shared phase table, section 13.4 | 13,183 |
| v5 | Commit "Contract v5"; tags `round-2` and `second-review` | 21 requests from the ten tabs revised against v4.2, such as the merge verdict order, one list of physical-effect Acts and out-of-process third-party Wasm components. The second review attacked this text | 14,022 |
| v6 | Commit "Contract v6" | Section 17, on all 112 second-review findings that target the contract (81 accepted, 18 revised, 5 in a different form, 8 left to the tabs) and two pending requests (`apps/machine-gateway`, `flash_device`): definitional attributes and per-kind `ItemDefinition`s, wire-level transfer checks, split labels, third-party code kept out of attestation, calibrated bounds, an agent-built program | 19,638 |
| v6.1 | Commit "Contract v6.1"; tags `round-3` and `third-review` | Section 17, on the round 3 tabs' 18 change requests: name-free `DisplayPackage` pages, eigenvalue bounds, `<family>/<code>` error codes, standing releases, AAL3 scope, a five-year support period per release line. The third review attacked this text | 20,109 |
| v7 | Commit "Contract v7" | Section 18, on all 111 third-review findings that target the contract (102 accepted, 8 with a revised fix, 1 declined) and the founder's four directions: the deletions above, the trust table (5.2), the signature table (5.4), the clean-room insight protocol (7.7), the parity floor (13.4), a hardened build program (13.2) and the teach-first writing rules (10, 11) | 30,144 |
| v7.1 | Commit "Contract v7.1" | Section 18, on the round 4 tabs' six change requests: blend stages (CCR-ANV-10), three shared phase rows (CCR-FLX-12), approval delegation (CCR-KLN-11), the `StepState` retention tier (CCR-KLN-12), single-person merges (CCR-AGT-14) and product liability at the phase 1 gate (CCR-ECO-13) | 30,445 |

Section 16 records 25 accepted requests in 23 rows, because two pairs of overlapping requests are ruled together. No change request filed in rounds 2 to 4 was declined.

Version 7 deletes more mechanisms than any earlier version, yet the contract grows by half. It gains the parity floor (13.4 is now 1,621 words), the clean-room protocol with its adopt-or-study list (7.7, 1,293 words), the trust and signature tables, and its own ruling log (section 18, 2,217 words). The four ruling logs hold 5,635 words; they stay at the end of the contract, read only when a ruling is in question.

### The shared phase table

Round 1 tabs phased shared physics differently (R1-35): modal analysis was phase 1 in COV and phase 2 in Flux, and fibre orientation phase 3 in COV and phase 4 in MFG. Contract 13.4 now sets one phase for each capability that several tabs phase.

- **Rule.** A capability lands in the phase of the first gate that needs it. Since v7, one that no gate needs takes the parity floor's phase if it has one, and otherwise the latest phase any tab proposed. Nothing is phased before its prerequisites (R7-08, R9-32). Since round 4, a row that needs another tab's capability names it in a `Requires:` entry, and `check.py` fails a row phased earlier than a row it requires (R13-04).
- **Ownership.** The owner's capability table specifies the capability; every other tab states the phase in one line and cites 13.4.
- **Size.** 21 rows in v4.2, 23 in v5 (CCR-ELX-8's two battery rows) and 25 in v6. As-built strut calibration (phase 1) and gear, bearing and shaft ratings (phase 2) join, and inherent strain moves from phase 1 to 2 with supports, baseplate cut, support removal and stress relief (R7-06, R7-07, R7-19). Three neighbouring capabilities keep their own tab's phase.
- **Round 4.** Version 7 adds eight rows: B-basis tolerance limits and planar and axisymmetric models in phase 1, linear dynamics and symmetry reductions in phase 2, Helmholtz solvers in phase 3, and RLCG extraction, full-wave extraction and phase-transformation kinetics in phase 4 (R13-04, R13-07, R20-02). Version 7.1 adds three from CCR-FLX-12: elastohydrodynamic lubrication in phase 3, and the plane-pair cavity model and rotor aerodynamics in phase 4.
- **R1-35.** Its proposed phases hold except two: DFN battery cells go to phase 5 because no gate names them, and inherent strain goes to phase 2.

| Phase | Rows in v5 | Rows in v6.1 | Rows in v7.1 | Owners in v7.1 |
| --- | --- | --- | --- | --- |
| 1 | 2 | 2 | 4 | FLX 2, MFG 1, COV 1 |
| 2 | 2 | 4 | 6 | FLX 4, MFG 1, COV 1 |
| 3 | 5 | 5 | 7 | FLX 4, MFG 3 |
| 4 | 7 | 7 | 12 | FLX 7, ELX 2, MEC 1, MFG 1, COV 1 |
| 5 | 5 | 5 | 5 | FLX 2, COV 2, MFG 1 |
| 6 | 2 | 2 | 2 | ELX 1, MFG 1 |
| Total | 23 | 25 | 36 | FLX 19, MFG 8, COV 5, ELX 3, MEC 1 |

### The parity floor

The third review's parity lenses asked a question the earlier reviews had not: would an engineer who uses an incumbent today find something missing? R19 and R20 answered with gaps from sketch trim to cyclic symmetry. The founder's direction FD-3 turns 45 of their findings into a second table in contract 13.4, the parity floor, which sets the latest phase for each capability. A tab may phase a floor capability earlier, never later.

| Phase | Rows | What lands by then |
| --- | --- | --- |
| 1 | 7 | Threads computed from the ISO and ASME formulas; DXF write and IGES read; sketch edits as source rewrites; Insert Instance and Add mate; generative design for additive; remote points, point masses and springs; technical illustrations, exploded views, Field animation, web views and reports |
| 2 | 8 | Photoreal path tracing, moving-part animation and decks; context pins, sheet metal and kinematics; DXF and DWG; toolpath editing and engagement-limited roughing; review routing and shape search; EBOM and MBOM editing; generative design for milling and casting; bushings, fasteners, tied interfaces, load combinations and submodeling |
| 3 | 6 | Quality records and foreign native CAD files; vendor controller kernels; belt and chain couplings; runnable Nastran and Abaqus decks; fan curves and laminar adjoints; native PSpice and LTspice |
| 4 | 3 | RANS rotating frames and adjoints; Modelica source import; hydraulic libraries, switched transients and interface compliance kits |
| 5 | 3 | Floquet ports and finite arrays; particle tracing and pressure-equipment design by analysis; two-phase and pneumatic libraries |
| 6 | 1 | Ply-shape, ply-drop and stacking optimization |

Contract 8 makes the comparison visible in every tab. A parity table under State of the art lists each capability, the incumbent's documented feature, Crucible's row and phase, and a verdict of Ahead, Equal, Later or Out of scope with one reason. AI-built clones appear where they ship a capability first. Each tab's lead says in one sentence what its users gain that a clone cannot copy quickly.

### A viewer first

The founder's direction FD-1 changes who the interface serves. Agents and code author the typed program, and nobody needs to model by hand. People steer by pointing, marking up and asking; they review every Proposal, approve every Act and present the result (contract 3, principle 2). Every capability stays reachable through `api` and Ingot.

- **The interface.** Contract 7.6 makes the UI a viewer, a reviewer and a presentation studio first. Its polish bar is the founder's reference: editorial serif typography on a calm canvas, fine-line isometric drawings with labelled callouts, real 3D motion and physically convincing effects, all from Crucible's own Rust renderer on real geometry and results. Presentation outputs are Snapshots under pinned `RenderProfile`s.
- **The plan.** Chain C, the interface chain of phase 1's critical path, now runs review and presentation before steering (contract 13.2). The GUI's own sketch tools move to phase 2, since agents and Ingot sketch in phase 1, and photoreal path tracing moves from phase 5 to phase 2.
- **The tab.** UIX is rebuilt around review and presentation: a Review default preset, a new Present preset, one presentation file kind for reports, decks and figures, readouts bound to the model, and a presentation audit that gates publishing.

Every rule that protects people stands. Approvals, signatures and machine safety are unchanged by the shift.

### The clean-room insight protocol

Until round 4, ECO ruled that Crucible never reverse-engineers a proprietary format. The founder's direction FD-2 replaces that rule with a protocol for studying incumbents to design something better, never to copy them (contract 7.7).

1. **Two roles.** An observer agent studies licensed copies in an isolated workspace with no network access. It writes only behavioural specifications, test vectors and method analyses, never code. Implementers never see its workspace or any decompiled output.
2. **A gate between them.** The verifier rejects released material that copies expression, and each release carries a signed provenance record.
3. **An order of methods.** Published specifications come first, then open readers, sample files and black-box observation. Decompilation serves only interoperability, and never touches an incumbent's kernel, solver, mesher or CAM strategy.
4. **A legal boundary.** Counsel decides the governing jurisdiction and clears each engagement. Clean rooms do not avoid patents, so every resulting reader or method passes a freedom-to-operate review.

Counsel's jurisdiction opinion joins the phase 0 gate (13.1), and the observer joins the agent roles (13.2). The same direction brings an adopt, port or study list from the round 4 software digest, with its licence corrections, such as deal.II's Apache-2.0 option and OpenSubdiv and OpenUSD under TOST-1.0. AI-built clones are studied as competitors and linked only after a provenance audit.

### Teach first

R21 traced most readability problems to the house style itself (R21-03): leads that listed mechanisms, specification before explanation, a length cap that counted reference tables, and decisions packed into one paragraph. The founder's direction FD-4 and section 18's writing rulings rewrite contract sections 10 and 11.

- **Skeleton.** A three-sentence lead says what the subsystem is, what the engineer gains over the incumbents, and the one mechanism that delivers it. The first design section opens with a worked example on the canonical bracket or a golden product, and reference material moves to an optional `## Reference`.
- **Decisions.** Each takes three lines: the decision, *Why:* and *Rejected:*.
- **History.** No finding ids, round numbers or revision markers appear above Open questions, which hold only questions waiting on an outside input.
- **Length.** A tab carries 9,000 to 15,000 words of prose (ING and ANV up to 17,000); tables and Reference do not count.
- **Smaller rules.** Interfaces list only what a tab provides, citations follow one style, every abbreviation is spelled out at first use, and the Overview carries a generated glossary.

`check.py` enforces the skeleton, the decision blocks, the history ban and the prose length. Every round 4 tab opens on a worked example: the bracket on four machines in PLT, GP5's 3.3 V rail in ELX, a supplier STEP file through to QIF in ECO, and an agent widening the bracket in AGT. The contract gets the same editorial pass without changing any rule beyond section 18's rulings.

### The program plan

Round 2 answered R6-01 with a plan sized for a human team and fixed to dates. The second review showed it could not carry agent work, because people had to write the oracles first (R12-02) and scope had grown without approval (R12-03). Contract v6 replaces it in section 13.2.

- **Roles.** The founder approves each phase's scope and budget, golden-product criteria, every Act and every waiver. Claude orchestrates; an oracle role, builders and an independent verifier are separate agent roles; outside firms make, measure and advise.
- **Gates, not dates.** Milestones are ordered, not dated, and plan figures measure work, never people. One budget per phase covers agent compute, CI, rented hardware, physical runs, metrology and counsel.
- **Build program.** Oracles come first, each with a runner class; corpora agree with an independent source; work items name oracle ids and held-out splits (D-PLT-45). Four chains form the critical path: geometry, physics and printing, interface, and release.
- **Round 4.** Version 7 hardens the build program against the agents that run it. The oracle role writes interface-first contract crates in a separate oracle workspace (R18-03). Contexts that read third-party content are tainted (R17-03), held-out splits use a keyed hash (R18-05), and calibration references come from an independent code (R13-08). The observer joins the agent roles, a validation campaign precedes the run build (R13-02), and Crucible's own repository runs in single-person mode (contract 5.4, CCR-AGT-14).

### Length

R3-38 to R3-45 and R3-52 to R3-55 measured eleven of twelve round 1 tabs over their caps. The first four columns count words before `## Sources` at each tag, as the spec check did until round 4. The last column counts prose as contract 11 now defines it, without tables, Reference, State of the art, Interfaces, Oracles or Sources.

| Tab | `round-1` | `round-2` | `round-3` | Now | Prose now |
| --- | --- | --- | --- | --- | --- |
| ING | 30,303 | 19,616 | 19,888 | 23,123 | 14,327 |
| ANV | 32,040 | 19,964 | 19,945 | 26,594 | 15,783 |
| FLX | 22,244 | 17,872 | 17,997 | 29,095 | 14,691 |
| COV | 17,450 | 17,817 | 17,720 | 25,925 | 11,877 |
| KLN | 25,499 | 17,944 | 17,989 | 23,926 | 14,353 |
| MEC | 19,646 | 17,861 | 17,968 | 25,965 | 13,925 |
| MFG | 23,874 | 17,799 | 17,900 | 25,981 | 12,350 |
| ELX | 23,155 | 17,415 | 17,993 | 23,918 | 13,041 |
| AGT | 22,335 | 17,786 | 17,908 | 22,239 | 12,799 |
| UIX | 25,670 | 17,876 | 17,945 | 25,412 | 14,632 |
| ECO | 24,336 | 17,867 | 17,738 | 22,461 | 13,234 |
| PLT | 24,061 | 17,833 | 17,798 | 23,653 | 13,713 |
| Total | 290,613 | 217,650 | 218,789 | 298,292 | 164,725 |

Round 2 cut the tabs by a quarter, and round 3 absorbed 278 findings in 1,139 more words. R21-03 then showed what the cap had cost: it counted reference tables, so explanation and examples were cut first. Round 4 caps prose instead, and every tab fits. The text before Sources grows by 36%, and prose measured by the same rule grows from 125,638 words at `round-3` to 164,725, as each tab gains a worked first section, a parity table and the capabilities of the parity floor.

Against `round-3`, the spec check finds no decision cut. ING and AGT renamed their oracle ids by area, and AGT merged capability rows (96 now, 157 at `round-3`) as its method catalog moved to Reference. ING, KLN and UIX dropped 16 source links whose claims were cut, most of them with the deleted live-editing CRDT.

### Open questions and unverified claims

The second review proposed an answer to each open question, and the round 3 brief asked every tab to decide it, turn it into a change request or keep it with a reason. Round 4's rule is stricter in form: Open questions hold only questions that wait on an outside input. Twelve were open at `round-3`; twenty are open now, half of them new, each waiting on counsel, a vendor, a measurement or the research literature.

| Tab | `round-2` | `round-3` | Now | What stays open now, and what it waits on |
| --- | --- | --- | --- | --- |
| ING | 9 | 0 | 0 | |
| ANV | 7 | 1 | 2 | GPU sampling for SSI, on counsel's opinion on US 12,229,885 B1; GP1's receiver profile, on the phase 0 shop agreement |
| FLX | 9 | 1 | 3 | Guaranteed bounds on cut cells, on the research literature; Flux's name, on trademark clearance; SAE J211 classes and critical-distance operators, on paywalled texts |
| COV | 10 | 3 | 3 | The strut waviness threshold, on the first calibration build; sheet lattices in GP2, on the phase 0 gate; gear and bearing envelope limits, on the licensed standards |
| KLN | 8 | 0 | 1 | Freedom to operate for history and merge, on counsel |
| MEC | 8 | 1 | 1 | Which standards tables std may ship, on counsel; no design waits on it |
| MFG | 9 | 2 | 3 | Freedom to operate for adaptive clearing, on counsel; GP2's build-preparation software, on the phase 0 gate; a vendor NC kernel licence, on the vendor |
| ELX | 11 | 2 | 1 | The Verilog-A front end's scope, on the research prototype |
| AGT | 11 | 1 | 1 | Auto-merge thresholds, on phase 2 review data |
| UIX | 9 | 0 | 1 | Preset names and 3D-mouse device terms, on counsel |
| ECO | 11 | 1 | 3 | The translator vendor, on negotiated terms; EU sector rules for open-source downloads, on counsel; ODB++ partnership terms, on counsel |
| PLT | 11 | 0 | 1 | The iPadOS shell, on App Review of the first phase 3 build |
| Total | 113 | 12 | 20 | |

The `round-2` and `round-3` counts leave out the findings records and the two round 3 contract requests that some tabs filed under Open questions. `[unverified]` marks fell from 424 at `round-1` and 334 at `round-2` to none at `round-3`, when every claim was verified on a primary source, corrected or cut. Round 4 adds six, each on a claim that waits on a paywalled text, a vendor page or a measurement: Fusion's Form workspace (ANV), the SAE J211 classes and the critical-distance operators (FLX), SOLIDWORKS's path mate (MEC), and WebRTC in browser workers and the threaded browser build's split (PLT). The tabs' Sources hold 733 links at `round-1`, 866 at `round-2`, 1,312 at `round-3` and 1,459 now.

### Decisions and oracles

Decision numbers are stable. Through round 3, a changed decision kept its number and ended with its latest marker, "(revised in round 3)" replacing "(revised in round 2)", and a new one took the next free number. Revision counts below are markers at each tag, so a decision revised in both rounds counts in each.

| Tab | Decisions at `round-1` | Added in round 2 | Revised in round 2 | Added in round 3 | Revised in round 3 | Decisions at `round-3` | Oracle ids, `round-2` → `round-3` |
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

Round 4 removed the revision markers, because contract 11 keeps review history out of the tabs. A revised decision now simply states its new content under its number; the revision commits name the revised decisions, and the Decisions log records them.

| Tab | Decisions at `round-3` | Added in round 4 | Decisions now | Oracle ids, `round-3` → now |
| --- | --- | --- | --- | --- |
| ING | 27 | 2 | 29 | 38 → 39 |
| ANV | 36 | 4 | 40 | 139 → 143 |
| FLX | 46 | 10 | 56 | 82 → 107 |
| COV | 30 | 4 | 34 | 42 → 48 |
| KLN | 49 | 9 | 58 | 68 → 75 |
| MEC | 37 | 4 | 41 | 84 → 94 |
| MFG | 34 | 7 | 41 | 121 → 126 |
| ELX | 31 | 6 | 37 | 62 → 68 |
| AGT | 34 | 2 | 36 | 24 → 25 |
| UIX | 33 | 7 | 40 | 53 → 76 |
| ECO | 37 | 5 | 42 | 34 → 38 |
| PLT | 47 | 4 | 51 | 57 → 64 |
| Total | 441 | 64 | 505 | 804 → 903 |

FLX adds the most decisions and oracle ids, for the idealizations, reduced models, dynamics and flow workflows the parity review asked for. UIX adds 23 oracle ids for review and presentation, and KLN nine decisions, most for the parity floor's PLM records (review routes, item search, quality records, mass change) and the Rust operation contract. KLN keeps D-KLN-11 to D-KLN-13 with its own gate-acceptance rules rather than withdrawing them (R15-22), so no number goes unused.

### Across three reviews

Three reviews, 885 findings and 57 Critical ones show a few patterns that hold across all of them.

- **Fixes fail where nothing computes the rule.** The second review found five first-review fixes that did not hold, and the third found seven more, plus a check this tab credited to `check.py` that did not exist. Several failed fixes stated a rule that no tool computed: the source closure, the prerequisite check, the held-out hash. Round 4 makes each one mechanical, with `cargo xtask closure-hash`, `Requires:` entries and keyed splits.
- **Critical fixes land in the contract.** The contract draws 16 of 23, 16 of 16 and 14 of 18 Critical findings, because a Critical problem is usually a rule several tabs share.
- **The bar rises, so the counts do not fall.** The first review asked whether the design works, and the second whether its fixes hold and it can be built. The third asked whether it beats every incumbent, reads well and is as simple as it can be. Its Critical findings moved accordingly, from what cannot work (unbounded peaks, remote machine starts) to what agents cannot build in Rust, what an engineer would miss, and what a reader cannot follow.
- **Each round reshapes the design differently.** Round 2 centralized: shared rules moved into the contract. Round 3 separated what had been merged wrongly, such as confidentiality and integrity. Round 4 merged what had been split needlessly, such as two merge algorithms, two departure records and two ways to bring outside data in.

What stays constant is the method: one contract that wins over the tabs, one fact in one place, an oracle for every claim, and a recorded reason for every finding declined.

## Sources

| Source | Link |
| --- | --- |
| First review brief | Git tag `review`, `docs/review/brief.md` |
| Second review brief | Git tag `second-review`, `docs/review/brief.md` |
| Third review brief | [../review/brief.md](../review/brief.md) |
| First review reports, R1 to R6 | [R1 physics](../review/R1-physics.md), [R2 geometry](../review/R2-geometry.md), [R3 architecture](../review/R3-architecture.md), [R4 practice](../review/R4-practice.md), [R5 security and legal](../review/R5-security-legal.md), [R6 feasibility](../review/R6-feasibility.md) |
| Second review reports, R7 to R12 | [R7 physics](../review/R7-physics.md), [R8 geometry](../review/R8-geometry.md), [R9 architecture](../review/R9-architecture.md), [R10 practice](../review/R10-practice.md), [R11 security and legal](../review/R11-security-legal.md), [R12 feasibility](../review/R12-feasibility.md) |
| Third review reports, R13 to R21 | [R13 physics](../review/R13-physics.md), [R14 geometry](../review/R14-geometry.md), [R15 architecture](../review/R15-architecture.md), [R16 practice](../review/R16-practice.md), [R17 security and legal](../review/R17-security-legal.md), [R18 Rust feasibility](../review/R18-rust-feasibility.md), [R19 design parity](../review/R19-design-parity.md), [R20 simulation parity](../review/R20-simulation-parity.md), [R21 editorial](../review/R21-editorial.md) |
| All 885 findings, parsed | [../review/findings.json](../review/findings.json) |
| Contract v7.1: mission (1), glossary (2), principles (3), core types and the trust and signature tables (5), decided architecture and the insight protocol (7), parity (8), platforms (9), taste (10), writing rules (11), crate map (12), roadmap, program plan, targets, shared phases and the parity floor (13) | [../contract.md](../contract.md) |
| Contract ruling logs: round 1 (14), first review (15), round 2 requests (16), second review and round 3 requests (17), third review, the founder's directions and round 4 requests (18) | [../contract.md](../contract.md) |
| Revision brief and software digest (round 4) | [../revision/brief.md](../revision/brief.md), [../revision/digest.md](../revision/digest.md) |
| Consistency pass brief (round 3) | [../revision/consistency.md](../revision/consistency.md) |
| Revision packets (round 4; round 3's are at tag `round-3`) | [ING](../revision/packets/ING.md), [ANV](../revision/packets/ANV.md), [FLX](../revision/packets/FLX.md), [COV](../revision/packets/COV.md), [KLN](../revision/packets/KLN.md), [MEC](../revision/packets/MEC.md), [MFG](../revision/packets/MFG.md), [ELX](../revision/packets/ELX.md), [AGT](../revision/packets/AGT.md), [UIX](../revision/packets/UIX.md), [ECO](../revision/packets/ECO.md), [PLT](../revision/packets/PLT.md) |
| Revised tabs | [ING](01-ingot.md), [ANV](02-anvil.md), [FLX](03-flux.md), [COV](04-coverage.md), [KLN](05-kiln-repo-plm.md), [MEC](06-mechanical.md), [MFG](07-manufacturing.md), [ELX](08-electronics-systems.md), [AGT](09-agents.md), [UIX](10-ui.md), [ECO](11-interop-ecosystem.md), [PLT](12-platform-performance.md) |
| Round 1 drafts and contract v3; contract v4 and the round 2 packets; the v2 tabs and contract v5; the v3 tabs and contract v6.1 | Git tags `round-1`, `contract-v4`, `round-2`, `round-3` |
| Declined findings, decisions added and revised, word counts | Revision commit messages: `git log round-1..round-2 -- docs/spec docs/contract.md`, `git log second-review..round-3 -- docs/spec docs/contract.md` and `git log round-3..HEAD -- docs/spec docs/contract.md` |
