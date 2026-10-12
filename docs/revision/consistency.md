# Round 4: consistency pass (brief for each tab's agent)

All twelve subsystem tabs are v4 and pass `check.py`, and contract v7.3 is binding: version 7.1 rules on every change request the v4 tabs filed, and versions 7.2 and 7.3 make Crucible's history Git-native (contract section 18). A cross-tab audit found the mismatches below and decided each one; the owner of a fact wins. Your job: apply your tab's edits, without reopening the revision.

## Rules

- Edit only your own `docs/spec/<file>.md` (and its diagram files if an edit touches a diagram). Never edit another tab, the contract, a README or CLAUDE.md, and never commit.
- Apply every edit in your tab's section below. Each quotes the current text and gives its line in the committed tab; if the text has moved, find it by its words. If an edit is wrong on the evidence, skip it and say why in your report.
- Keep every decision, oracle and source that the edits do not name. A decision you change states the new decision under its number, and the Decisions log records the change. Write no "(revised in round N)" markers, finding ids, "formerly" or "replaces" anywhere above `## Open questions` (contract 10 and 11); `check.py` fails on them. When an edit removes the last citation of a source key, drop that Sources row.
- Delete each change request contract 18 accepted from your `## Contract change requests` section; a section left empty reads "None." Wherever your text relies on a ruling, cite the contract section, never the request.
- A `Requires:` entry names the other tab's Capability cell word for word, and several entries are separated by ";" (contract 13.4). Two entries added here point at rows that another tab's edit creates or re-phases: ELX's "FLX Electro-thermal coupling" (added by FLX) and UIX's "MEC Exploded views" (moved to phase 1 by MEC). If `check.py` reports only those, apply everything else and say so; the orchestrator re-runs the check once every tab has landed.
- Stay within the length rule: 9,000 to 15,000 words of prose (ING and ANV up to 17,000). Capability tables, the Reference section, State of the art, Interfaces, Oracles and Sources do not count (contract 11). The budget table below gives your room.
- Run `python3 docs/tools/check.py docs/spec/<file>.md --base round-3`: zero errors, and nothing reported cut since round 3 except what an edit below removes.
- Reply in at most 150 words: edits applied and skipped (with reasons), names you chose, the word count and the check result.

## The audit

This audit covers the twelve subsystem tabs as committed at `312d1b3` (unchanged since `be97e4f`), against contract v7.3. It checks every `Requires:` entry; each tab's Interfaces rows against what the receiving tab's design assumes; phases against contract 13.1, 13.2 and both tables of 13.4; names against contract 2 and the owners; the renames and deletions of v7 and the v4 revisions; change-request citations against contract 18; cross-tab decision and oracle ids; shared facts (the canonical bracket's figures, lanes, fidelities, the signature table, failure families); the orchestrator's follow-up notes; every intra-spec link; and editorial coherence across tabs.

**How the owner was chosen.** The owner of a fact wins. The owner is the tab named by contract 5's `[TAB]` tags or 13.4's Owner column; otherwise it is the tab whose design section specifies the fact. Items where the other direction is defensible are listed under "Judgment calls".

**How the edits were checked.** Every "Now" quote below occurs exactly once in the committed file, at the line given (`grep -F`). A row quoted without its first cells is still unique. Applying every quoted replacement to a scratch copy of the tabs, with FLX's two new rows, gives zero `check.py` errors and leaves every tab inside its length range before any of the deletions, which only free room.

**Where the working is.** The audit's scripts and helper findings are in `docs/build/audit/` (ignored by git): `caps.tsv` (every capability row), `requires.tsv` (every `Requires:` entry), `xids.tsv` (every cross-tab oracle and decision citation), `links.py` (the intra-spec link checker) and `verify.py`, `verify2.py` and `apply.py` (the quote, line and scratch-copy checks).

**Word budgets.** Prose words from `check.py` at `312d1b3`, and room to the ceiling. FLX, UIX and KLN are tightest; UIX 18 and KLN 9, 10 and 12 free about 330 and 120 words.

| Tab | Words now | Room | Tab | Words now | Room |
| --- | --- | --- | --- | --- | --- |
| ING | 14,327 | 2,673 | MFG | 12,350 | 2,650 |
| ANV | 15,783 | 1,217 | ELX | 13,041 | 1,959 |
| FLX | 14,691 | 309 | AGT | 12,799 | 2,201 |
| COV | 11,877 | 3,123 | UIX | 14,632 | 368 |
| KLN | 14,353 | 647 | ECO | 13,234 | 1,766 |
| MEC | 13,925 | 1,075 | PLT | 13,713 | 1,287 |

## Summary

**Edits per tab.** ING 14, ANV 9, FLX 18, COV 11, KLN 15, MEC 14, MFG 10, ELX 13, AGT 11, UIX 18, ECO 17, PLT 15: 165 numbered edits, several with sub-edits.

**The orchestrator's follow-up notes** (`docs/build/r4-followups.md`).

| Note | State at `312d1b3` | Edit |
| --- | --- | --- |
| AGT and ELX cite renamed ING oracles | AGT and ELX cite no ING oracle; all 27 cross-tab oracle citations exist | none |
| COV drops the yield-strength enclosure from D-COV-13 | Done in COV (an exact basis interval, held at both ends); ING still reads one number and FLX an enclosure | ING 1, FLX 2, FLX 17 |
| The Overview uses ING's bracket figures | The rewritten Overview now uses COV's 118 MPa; ING (94 MPa) and COV disagree, and AGT reads a 166 MPa limit | ING 2, FLX 5, COV 3, AGT 2, UIX 7; judgment call 1 |
| ECO's "Imported identity and matching" needs a `Requires:` | ANV's rows exist at phase 1 | ECO 1 |
| MFG's nine `Requires:` may need re-matching | All resolve; one names a weaker row than the 13.4 owner row | MFG 9 |
| ELX `Requires:` for the plane-pair model, `flux::extract_rlcg` and Floquet arrays | FLX names them "Plane-pair cavity model", "RLCG extraction" and "Periodic structures and arrays" | ELX 10 |
| COV's five FLX `Requires:`; `flux-op-material` | All five resolve; FLX never hears of `flux-op-material` | COV 7 |
| AGT oracle ids and row names renamed | No other tab cites an old AGT oracle id or the old row names | none |
| AGT walkthrough 74 MPa ± 7 against 166 MPa | 166 MPa is the non-conservative end of COV's basis interval | AGT 2 |
| CCR-AGT-14 | Accepted in 5.4; AGT's merge and `Attested` rules still exclude it | AGT 3, AGT 4 |
| KLN deleted the CRDT, watermark, `grant_deviation`, module-signature path and Deployment | No tab cites them; KLN's CRDT mention is a rejected alternative, and recipient watermarks are a separate, live mechanism | none |
| CCR-KLN-11 and CCR-KLN-12 | Accepted; `Checkpoint` survives in KLN, FLX and AGT | KLN 1 to 3, FLX 4, AGT 1 |
| MEC's `Repr` → `Detail`; generative design is MEC's `generate` | No tab or contract text uses `Repr`; FLX and ANV cite `std::mech::generate` | FLX 14 (MEC row) |
| FLX's calibration classes | COV and MEC still use `elasticity.eigen` and "four classes" | COV 1, COV 2, MEC 3 |
| FLX's `Repr` → `FieldRepr`, `OpCx::safe_point`, `flux/<code>` failures | No other tab uses the old names; contract 5's `DynField { …, repr }` field holds a `FieldRepr` | none |
| CCR-FLX-12 | Accepted in 13.4; COV and ELX still credit COV with rotor aerodynamics | FLX 18, COV 10, ELX 5, ELX 6 |

**Git-native history (contract v7.2 and v7.3).** Changes are Git commits, any Git host can be home with Kiln as a required status check, and a module gets its own repository only when some reader may not read it. KLN's `### Git export` section contradicts this outright (KLN 15), and ING, ANV, MEC, ELX and ECO still describe Git as an export (ING 14, ANV 9, MEC 14, ELX 13, ECO 17).

**Intra-spec links.** Thirteen cross-tab anchors resolve to no heading, most into KLN's and MEC's reorganized sections (ING 1, 5; MFG 4; ELX 1; UIX 12, 18; ECO 8).

**Sweeps with nothing to change.**

- **`Requires:` entries.** All 60 resolve and none is earlier than its target (`check.py`, `requires.tsv`); no entry cites a row v4 renamed.
- **Cross-tab ids.** No tab cites another tab's decision id; tabs link by section. The 27 cross-tab oracle citations all exist and test what they are cited for.
- **Retired and deleted names.** `check.py` finds none in the twelve tabs, and neither do greps for `Repr`, `InstanceRepr`, `OpCx::checkpoint`, `SolveFailure`, old `AGT-O-<n>` ids, Loro, the evidence watermark, `grant_deviation`, `conditional_on`, the module-signature path, `share_external`, `notify_external` and `deprecate_package` (ECO's deprecation row is ECO 2).
- **Lanes, fidelities and qualifiers.** `PoolLane` and `PriorityClass` agree in PLT, AGT, KLN, ING, ELX and UIX; only `Preview`, `Interactive` and `SignOff` name fidelities; result statuses, verdicts, `Severity`, grades, platform classes, zones, model and credibility levels and bound kinds match contract 5.
- **Phases.** Every 13.4 first-table row has an owner capability row at its phase except FLX's conjugate heat transfer and electro-thermal coupling (FLX 13); every parity-floor row lands no later than its phase except exploded views (MEC 1); no tab puts a 13.2 deferral at phase 1; gate contributions name the right golden products.
- **Signatures and Acts.** No tab copies the signature table; restated two-person rules match 5.4; only 7.6's physical-effect kinds appear; every `<group>.<name>` method cited exists in AGT's catalog.
- **Shared numbers.** 13.3 targets, the 60 s rejoin, 8 h bench sessions, demand depth 10,000, α = 0.01 with 300 held-out cases, and the 1.3× FMA rule agree; the 10 ms safe point differs only in FLX (FLX 8).
- **Forbidden phrasings.** "op", "kernel", "job", "macro", "plugin", "occurrence", "PR", "action" and "commit" appear only in their allowed senses (Git, `act.commit`, other products).

**Judgment calls.** Each is decided below, but the other direction is defensible:

1. **The bracket's figures.** This brief takes ING's stresses (contract 6 makes ING the example's owner; its 94 MPa at 6 mm and about 210 MPa at 4 mm scale as bending should, and a hand estimate of 67 MPa nominal times a fillet factor near 1.4 agrees) and COV's 240 MPa basis, so the limit is 144 MPa. The alternative keeps COV's 118 MPa, which the Overview committed at `582cf4f` uses: then ING (three figures), AGT and UIX change instead of COV, and the Overview stays.
2. **Ingot's limit codes** render in KLN's `kiln` family (ING 4). The alternative keeps `ing/63xx` as the diagnostic that reports KLN's Failure.
3. **Critical distances** keep FLX's failure name, and FLX's row moves to phase 1 (FLX 3, COV 5). The alternative renames FLX's failure to COV's.
4. **Exploded views.** MEC moves ordered explode steps to phase 1 for the parity floor (MEC 1). The alternative is a contract ruling that moves exploded views to the phase 2 floor, since both phase 1 golden products are single Parts.
5. **`Site`** (KLN, ECO) wins over MFG's `ProductionSite` (MFG 1), though the latter avoids a near-collision with "site safety record".
6. **Priority classes.** KLN's copy of AGT's table goes (KLN 9). The alternative keeps the table in KLN, which schedules, and has AGT point to it.
7. **The `ui` failure family.** UIX follows AGT's registry (UIX 6). The alternative registers `uix` in AGT.
8. **The quality connector.** ECO adds a `quality` world (ECO 7). The alternative drops KLN's reliance on it, since KLN's own quality records already meet the parity floor.
9. **Duplicates kept.** D-ECO-26 restates D-PLT-31, and KLN's "Determinism suite" row restates PLT's; a consistency pass never cuts a decision or a capability, so both wait for the next capability audit.

**For the contract to rule on.**

1. **`standing_release` and the Act-kind list.** Contract 7.6 lists Act kinds without it, yet 7.6 and 5.4 treat it as an approved plan and AGT tables it as an Act kind while D-AGT-36 says the kinds are "contract 7.6's list and no more". Add it to the list, or call it a mode of `release_data`.
2. **Reached limits.** After ING 4, KLN's `kiln/work_limit` and `kiln/memory_limit` serve operations and Ingot, but MFG defines `MfgError::WorkLimit { limit: base::WorkLimit, best_so_far }` with an undefined `base::WorkLimit`, and PLT and ECO say a Wasm `memory.grow` past the maximum returns −1 while KLN caches `kiln/memory_limit`. Contract 7.2 should say that a reached limit renders under `kiln/` and how a search returns its best result beside it.
3. **Single-person mode.** Contract 5.4 can read as every single-person merge waiting 72 h, where CCR-AGT-14 proposed the delay for R3 and R4 merges; and an `Attested` verifier review exists only in the hosted crew or behind the model gateway, which arrive in phase 2, while 13.2 runs Crucible's own repository in single-person mode from phase 0. Say which merges wait, and what attests the verifier before phase 2.
4. **`PlacementPolicy`.** Contract 5.6 says `repo` implements it; KLN puts it in `trust` (KLN lines 278, 1011), which owns labels, residency and control authorizations. Recommended: "which `trust` implements".
5. **"Derived view" has two meanings.** Contract 2 defines a declassified view, while its Node row and 7.2 item 5 call a BOM a derived view; KLN and ELX use both senses. Name the computed node kind differently (for example "computed view").
6. **13.4's "Also phased in" column** names tabs that do not phase the row (MEC for planar models, linear dynamics and symmetry reductions; FLX for fibre orientation, phase-transformation kinetics, battery swelling and abuse), omits ECO from "FMU export and SSP", and FMU import (phase 3 in FLX, ELX and ECO) has no shared row.
7. **Exploded views at phase 1.** If MEC cannot ship ordered explode steps in phase 1, the phase 1 presentation row of 13.4's parity floor must drop exploded views to phase 2.

**Outside the twelve tabs** (plan step 4):

- The Overview's trust walk-through (`00-overview.md` lines 137, 143 and 149) uses COV's 118 MPa, 10.2 MPa and 129.7 MPa; it follows whichever bracket figures the orchestrator settles (this brief: 94 MPa, 8.1 MPa model form, 103.6 MPa total against 144 MPa).
- The Decisions log needs lines for the decisions this brief changes: D-KLN-37, D-FLX-37, D-COV-31, D-MFG-40, D-UIX-28, D-ECO-10 and D-ECO-42, and the *Why* lines of D-MEC-33 and D-ELX-27.
- After the tabs land, re-run `python3 docs/tools/extract.py`, `python3 docs/tools/check.py --all -q` and `python3 docs/build/audit/links.py`.

## ING

1. **[high] A property read in a limit is an interval.** `` ### `Approx<T>` and the decision rule `` (line 383)
   - Now: "returns the design value at a statistical basis as an exact number. The read may name the basis (`basis:`); otherwise COV's default applies, the specification minimum and else the B-basis value ([COV, Coverage model](04-coverage.md#coverage-model))."
   - Must say: "returns the property's basis interval, from its lower to its upper basis value, as an exact `Range`, and the check must hold at both ends. The read may name the basis (`basis:`); otherwise COV's default applies, the specification limit and else B-basis ([COV, Two uses of a property](04-coverage.md#two-uses-of-a-property))."
   - Why: COV owns `Material` (contract 5.6). D-COV-13 (COV line 668): a limit property "reads its design basis as an exact interval from the lower to the upper basis value. The check must hold at both ends"; COV's row to ING provides "property reads as exact basis intervals for limits". The old anchor resolves to no COV heading.
2. **[high] The bracket's limit is 144 MPa.** `### Checks` (line 832)
   - Now: "The limit is 0.6 × 241 MPa = 144.6 MPa, from the 6061-T6 specification minimum yield that COV's default basis selects"
   - Must say: "The check holds at 0.6 × 240 MPa = 144 MPa, the conservative end of the basis interval in COV's 6061-T6 record ([COV, The bracket's check](04-coverage.md#the-brackets-check))"
   - Why: COV owns the Material record. COV line 15: "a basis interval from 240 MPa, the specification minimum, to 276 MPa, so the limit is the interval 144 MPa to 165.6 MPa … here 144 MPa". This tab's stresses (94 MPa ± 1.5 MPa at 6 mm, about 210 MPa at 4 mm) stay; FLX, COV, AGT and UIX follow them in their edits below.
3. **[medium] Two verdict reasons other tabs return are missing.** `` ### `Approx<T>` and the decision rule `` (line 394)
   - Now: "| `Undecided { SingularPoint }`, `Undecided { MaximumAtExclusion }`, `Undecided { Flagged(flag) }` | A blocking flag from the producer, such as a peak on the boundary of an excluded neighbourhood |"
   - Must say: the same row, followed by a new row: "| `Undecided { MissingData }`, `Undecided { CredibilityBelowMinimum }` | A compliance input is unknown (KLN, MFG), or the model's credibility level is below the policy package's minimum (COV) |"
   - Why: contract 5.2 makes ING the verdict's owner. KLN line 760 and MFG lines 1002 and 1013 return `Undecided { MissingData }`; COV line 598 returns `Undecided { reason: CredibilityBelowMinimum }`. Neither reason is in this table.
4. **[medium] Limit failures render in KLN's family.** `### Limits` (lines 695 to 703), the capability row at line 752, `### Diagnostic codes` (line 1291) and ING-O-EXEC-2 (line 1376)
   - Now: "Outcome names follow KLN's catalog of limit outcomes." → Must say: "Each limit ends in a `Failure` from KLN's catalog of limit outcomes."
   - Now, in the Failure column (lines 699 to 703): "`ing/6301 FuelExhausted`", "`ing/6302 StackExhausted`", "`ing/6303 MemoryLimit`", "`ing/6304 WorkLimit { kind: OperationCalls }`", "`ing/6305 WorkLimit { kind: ExpressionSize }`" → Must say: "`kiln/fuel_exhausted`", "`kiln/stack_exhausted`", "`kiln/memory_limit`", "`kiln/work_limit { kind: OperationCalls }`", "`kiln/work_limit { kind: ExpressionSize }`".
   - Now (line 752): "`ing/63xx`; Abort `FuelCeilingExceeded`" → Must say: "KLN's limit `Failure`s; Abort `FuelCeilingExceeded`".
   - Now (line 1291): "`ing/6203` empty Instance set; `ing/63xx` limits; `ing/6401` undecided branch" → Must say: "`ing/6203` empty Instance set; `ing/6401` undecided branch".
   - Now (line 1376): "fails with `ing/6302` everywhere" → Must say: "fails with `kiln/stack_exhausted` everywhere".
   - Why: KLN line 128: "One catalog of limit outcomes in `base-op` serves every tab", rendered `kiln/fuel_exhausted { used, limit }`, `kiln/stack_exhausted`, `kiln/memory_limit`, `kiln/work_limit { kind, limit }` (KLN lines 1212 to 1215). Contract 7.6 renders each typed `Failure` once, as `<owner family>/<snake_case>`; two codes for one Failure break that.
5. **[medium] Aspect kinds link to a heading MEC does not have.** `### GD&T controls as types` (line 357)
   - Now: "([MEC, Shared types](06-mechanical.md#shared-types))"
   - Must say: "([MEC, Specification model](06-mechanical.md#specification-model))"
   - Why: MEC's closed `ShapeAspect` kind table sits under `### Specification model` (MEC lines 889, 912 to 926); no "Shared types" heading exists.
6. **[medium] The general tolerance links to the wrong MEC section.** `` ### `Tol<T>` `` (line 270)
   - Now: "([MEC, Part features](06-mechanical.md#part-features))"
   - Must say: "([MEC, Specification model](06-mechanical.md#specification-model))"
   - Why: `part.general_tolerance(spec)` is D-MEC-35 (MEC line 949) under `### Specification model`.
7. **[medium] Variation analysis links to the wrong MEC section.** `### Arithmetic on tolerances` (line 315)
   - Now: "the sites behind `x` ([MEC, Interference and clearance](06-mechanical.md#interference-and-clearance))"
   - Must say: "the sites behind `x` ([MEC, Stack-up and variation analysis](06-mechanical.md#stack-up-and-variation-analysis))"
   - Why: zone and rebuild paths are D-MEC-22 (MEC line 1019) under `### Stack-up and variation analysis` (line 990).
8. **[medium] Fastener stack contributions link to the wrong MEC section.** `### Geometric zones in a stack` (line 339)
   - Now: "read these contributions in phase 1 ([MEC, Interference and clearance](06-mechanical.md#interference-and-clearance))"
   - Must say: "read these contributions in phase 1 ([MEC, Stack-up and variation analysis](06-mechanical.md#stack-up-and-variation-analysis))"
   - Why: one-dimensional chains and fixed and floating fastener conditions are rows of MEC's stack-up table (MEC lines 996 to 1011).
9. **[medium] `mirrored: true` is a filter Anvil never provides.** `### Call sites and names` (line 467)
   - Now: "and role queries on reflections accept `mirrored: true`"
   - Must say: "and a reflection marks its entities with the aspect `Mirrored`"
   - Why: ANV owns `anvil::resolve`, whose filters are "normal, type, area, adjacency, `bounded_by`" (ANV line 331); ANV line 303: "Reflections add the aspect `Mirrored` in place". No tab defines a `mirrored:` filter.
10. **[medium] The guest SDK reaches `crucible:ops/flux` before Flux publishes it.** `## Rust features and Wasm components` (line 933)
    - Now: "| `crucible:ops/anvil`, `crucible:ops/flux`, asynchronous |"
    - Must say: "| `crucible:ops/anvil`; `crucible:ops/flux` from phase 2; asynchronous |"
    - Why: FLX's "Flux operations from Wasm" row is phase 2 (FLX line 995); this tab's "Guest SDK" row is phase 1 (line 975).
11. **[low] The conversion argument is `accuracy`.** `### Approximate values as inputs` (line 414)
    - Now: "`body.convert(into: Mesh, tolerance: 0.01mm)`"
    - Must say: "`body.convert(into: Mesh, accuracy: 0.01mm)`"
    - Why: ANV line 925: "`anvil::convert(body, into, accuracy)` is the only conversion operation."
12. **[low] The 150% BOM is KLN's, in phase 3.** `## State of the art` (line 1334)
    - Now: "ahead in that variant existence is static, so the 150% BOM needs no enumeration"
    - Must say: "ahead in that variant existence is static, so KLN's 150% BOM (phase 3) needs no enumeration"
    - Why: KLN's "Variants and 150% BOM" row is phase 3 (KLN line 682); this row cites phase 1.
13. **[low] Contract 5.3's integrity rule restated.** `### Free text` (line 853)
    - Now: "Integrity therefore travels with the value, not with the node that holds it, so a merged supplier file gives trusted geometry and untrusted names. A node's label takes a text's integrity only when the node turns that text into a non-text value, such as embossed geometry or a parsed number ([contract section 5.3](../contract.md#53-labels))."
    - Must say: "How that integrity reaches node labels is [contract section 5.3](../contract.md#53-labels)'s rule."
    - Why: contract 5.3: "This paragraph is the only statement of the rule; tabs cite it." Saves about 45 words.
14. **[high] Git is the storage, not an export.** `### Call sites and names` (line 459), `### Lossless tree and blocks` (line 1092) and ING-O-NAME-1 (line 1404)
    - Now: "Live-session edits and Git export never enter a `CallSite`: exporting to Git, re-importing and rebuilding leaves every `EntityId` unchanged." → Must say: "Live-session block ids never enter a `CallSite`: cloning, pushing or mirroring through any Git host and rebuilding leaves every `EntityId` unchanged."
    - Now: "and Git export all work on text" → Must say: "and Git storage all work on text"
    - Now: "Golden products through Git export and re-import" → Must say: "Golden products cloned, pushed and mirrored through a second Git host"
    - Why: contract 7.1 and 5.5 (v7.2 and v7.3, ruling FD-5): "A Crucible repository is an ordinary Git repository" and "Cloning, pushing or mirroring through any Git host and rebuilding leaves every `EntityId` unchanged."

## ANV

1. **[medium] A `Preview` result is not a `Proxy`.** `### Fidelity` (line 1066)
   - Now: "GPU `f32` evaluation; results may show as `Proxy`"
   - Must say: "GPU `f32` evaluation; results are `Ready(Preview)`"
   - Why: contract 5.6 defines `Proxy` as "a dependent shown by affine extrapolation from its last value while it recomputes"; a computed `Preview` value is `Ready(Fidelity)` (UIX line 85 renders it so).
2. **[medium] The Interfaces row to FLX gives mid-surfaces and adaptation the wrong phase.** `## Interfaces with other subsystems` (line 1274)
   - Now: "| `Body`, `Field`, `FaceBound`, `EdgeBound` | 1; 2 (meshing, `shape_velocity`); 4 (`common_refinement`) |"
   - Must say: "| `Body`, `Field`, `FaceBound`, `EdgeBound` | 1; 2 (mid-surfaces, swept-member axes, meshing, `shape_velocity`); 3 (metric adaptation); 4 (`common_refinement`) |"
   - Why: this tab's rows: `anvil::mid_surface` 2 (line 762), `member_axes` "1 (lattices), 2 (swept members)" (line 763), `adapt_mesh` 3 (line 872). FLX reads them at those phases (FLX lines 1231, 1233).
3. **[low] The Interfaces row to ING claims phase 0 for phase 1 items.** `## Interfaces with other subsystems` (line 1271)
   - Now: "| `Body`, `EntityId`, `HistoryRecord`, `ResolveError`, `OpError` | 0 |"
   - Must say: "| `Body`, `EntityId`, `HistoryRecord`, `ResolveError`, `OpError` | 0; 1 (`query_stability`, constraint solves, `text_outline`) |"
   - Why: `anvil::query_stability` (line 414), `solve_constraints` (line 1056) and `text_outline` (line 750) are phase 1.
4. **[low] The Interfaces row to UIX phases `offset_faces` at 2.** `## Interfaces with other subsystems` (line 1279)
   - Now: "| `DisplayPackage`, `Body` | 1; 2 (`cluster_dag`, face edits) |"
   - Must say: "| `DisplayPackage`, `Body` | 1; 2 (`cluster_dag`, face edits other than `offset_faces`) |"
   - Why: `anvil::offset_faces` is phase 1 (line 720), and UIX's push-pull uses it in phase 1 (UIX line 520).
5. **[low] The receiver profile is ECO's `parasolid`.** `### Exchange form and receiver profiles` (line 966), ANV-O-NF-2 (line 1314), `## Open questions` (line 1389)
   - Now: "Named profiles ship with Crucible (`Parasolid`, at a tolerance of 5 × 10⁻⁹ m)" → Must say: "Named profiles ship with Crucible (ECO's `parasolid`, at a tolerance of 5 × 10⁻⁹ m)"
   - Now: "exported under the `Parasolid` profile" → Must say: "exported under the `parasolid` profile"
   - Now: "until then GP1 exports under the `Parasolid` profile" → Must say: "until then GP1 exports under the `parasolid` profile"
   - Why: ECO owns the named profiles (D-ECO-38, ECO line 113: "starting with `parasolid` at 5 × 10⁻⁹ m"; ECO line 40: `receivers::parasolid`).
6. **[low] Duplicate search is KLN's, phase 2.** `## State of the art` (line 1250)
   - Now: "`GeometryId` for exact duplicates, phase 0; similarity search is KLN's, phase 2"
   - Must say: "`GeometryId`, phase 0; KLN's duplicate and similarity search, phase 2"
   - Why: KLN's "Classification and shape-similarity search" row finds exact duplicates by `GeometryId` in phase 2 (KLN line 636).
7. **[low] Three abbreviations used before they are spelled out.** `### The Body value` (line 51), `### Query resolution` (line 356), `### WIT packages and contract crates` (line 1198)
   - Now: "CAx-IF practice allows those only on exact geometry" → Must say: "CAx Implementor Forum (CAx-IF) practice allows those only on exact geometry"
   - Now: "changes the extent a fillet or GD&T target means" → Must say: "changes the extent a fillet or GD&T (geometric dimensioning and tolerancing) target means"
   - Now: "Anvil owns the WIT package `crucible:geom`" → Must say: "Anvil owns the WIT (WebAssembly Interface Types) package `crucible:geom`"
   - Why: contract 11 spells out every abbreviation at first use in each tab.
8. **[medium] CCR-ANV-10 is accepted.** `## Contract change requests` (line 1393)
   - Now: the bullet beginning "- **CCR-ANV-10, blend stages in contract 7.1.**"
   - Must say: "None."
   - Why: contract 18 accepts it (7.1 now lists convexity change along an edge in stage 1, and partial-length, capped and cliff ends in later stages); the stage table in `### Blends` already matches.
9. **[medium] Git is the storage, not an export.** ANV-O-SITE-1 (line 1297)
   - Now: "Golden products exported to Git, re-imported and rebuilt keep every `EntityId`"
   - Must say: "Golden products cloned, pushed and mirrored through a second Git host and rebuilt keep every `EntityId`"
   - Why: contract 5.5 and 7.1 (v7.3, ruling FD-5). Lines 238 and 279 ("Git round trips") already read correctly.

## FLX

1. **[high] A `Preview` check is `Undecided { Indicator }`.** `### Validity zones and cross-class agreement` capability table (line 213) and `### Explicit dynamics` capability table (line 487)
   - Now: "`Undecided { reason: PreviewOnly }` for every check" → Must say: "`Undecided { Indicator }` for every check"
   - Now: "`Undecided { reason: PreviewOnly }` for any check" → Must say: "`Undecided { Indicator }` for any check"
   - Why: ING owns verdicts and their reasons (contract 5.2). ING line 391: "`Undecided { Indicator }` | A part is only an `Indicator`: every `Preview` result". No tab defines `PreviewOnly`.
2. **[high] A limit property reads as an interval; a solve input carries `ToleranceLimit`.** `### Budgets and guarantees` (line 117)
   - Now: "reads that value as an exact definitional number with no budget part (COV owns this rule). A property that drives the solve, such as Young's modulus or conductivity, arrives as an enclosure from its statistical basis. Its input part is `Estimated { Statistical { method: basis, α } }`"
   - Must say: "reads its basis as an exact interval, holds at both ends and adds no budget part (COV owns this rule). A property that drives the solve, such as Young's modulus or conductivity, arrives as its basis interval. Its input part is `Estimated { Statistical { method: ToleranceLimit, α } }`"
   - Why: D-COV-13 (COV line 668): a limit reads "an exact interval from the lower to the upper basis value. The check must hold at both ends"; a solve input carries "its basis interval as `Estimated { Statistical { method: ToleranceLimit, α } }`".
3. **[high] Critical-distance goals are phase 1.** `### Validity zones and cross-class agreement` capability table (line 205)
   - Now: "`CriticalDistanceMismatch { calibrated, requested }` | FLX-O-ERR-12 | 2 |"
   - Must say: "`CriticalDistanceMismatch { calibrated, requested }` | FLX-O-ERR-12 | 1 |"
   - Why: this tab's phase 1 class `elasticity.peak` covers "critical-distance goals" (line 157), its Interfaces row to ING offers them in phase 1 (line 1420), and COV's "Critical distances" row (COV line 453) and phase 1 durability use them. The failure name stays this tab's, since `tcd` raises it; COV follows (COV 5).
4. **[high] The derivative retention tier is `StepState`.** `## Gradients and optimization` (line 870), `## Execution and extension` (line 981) and the "Adjoints" capability row (line 901)
   - Now: "stored in Kiln's `Checkpoint` retention tier by (`NodeKey`, step), so an objective-only change reuses them" → Must say: "stored in Kiln's `StepState` retention tier by (`NodeKey`, step), so an objective-only change reuses them"
   - Now: "is stored in Kiln's `Checkpoint` retention tier by (`NodeKey`, step), so a resumed solve continues bit-identically" → Must say: "is stored in Kiln's `StepState` retention tier by (`NodeKey`, step), so a resumed solve continues bit-identically"
   - Now: "| `CheckpointMissing` triggers recomputation |" → Must say: "| None: missing step state is recomputed (KLN) |"
   - Why: contract 7.1 (ruling CCR-KLN-12) names the tier `StepState`; "checkpoint" now names only transparency-log heads. KLN's row reads "None: an evicted checkpoint is recomputed", so no failure exists to name. "CAMS checkpointing" (line 870) is the algorithm's published name and stays.
5. **[medium] The bracket's discretization part is ± 1.5 MPa.** `### The answer and its budget` (line 37)
   - Now: "| Discretization | ± 1.1 MPa |"
   - Must say: "| Discretization | ± 1.5 MPa |"
   - Why: ING owns the canonical walk-through (contract 6): ING line 838 "`SignOff`, 6 mm: 94 MPa ± 1.5 MPa, confirmed by one refinement"; COV line 13 cites "a discretization bound of 1.5 MPa (FLX)"; UIX line 812 shows ± 1.5 MPa.
6. **[low] The reason lists `ModelForm`.** `### The answer and its budget` (line 46)
   - Now: "`Undecided { reason: Unquantified([model form]) }`"
   - Must say: "`Undecided { reason: Unquantified([ModelForm]) }`"
   - Why: ING line 837 and COV lines 32 and 124 write `Unquantified([ModelForm])`.
7. **[medium] `Proxy` only where the change is affine.** `### What happens while the engineer works` (line 52), D-FLX-37 (line 591) and the "Interactive stage budgets" row (line 600)
   - Now: "Results show as `Proxy` during the drag." → Must say: "During the drag, results show as `Proxy` where the change is affine on them, otherwise `Stale`."
   - Now: "physics results show as `Proxy` until the full update arrives in phases 1 and 2" → Must say: "physics results show as `Proxy` where the change is affine on them, otherwise `Stale`, until the full update arrives in phases 1 and 2"
   - Now: "A budget miss streams the coarse result as `Proxy`" → Must say: "A budget miss shows dependents as `Proxy` or `Stale` until the update arrives (KLN)"
   - Why: contract 5.6 defines `Proxy` as affine extrapolation from the last value, and contract 13.3's drag row says "later dependents show as `Proxy` where the change is affine on them, otherwise `Stale`" (KLN line 191 agrees). A computed coarse result is a value, not a `Proxy`.
8. **[medium] Safe points run on monotonic time.** `## Execution and extension` (line 982)
   - Now: "`OpCx::safe_point` is polled at least every 10 ms of CPU time"
   - Must say: "`OpCx::safe_point` is polled at least every 10 ms of monotonic time"
   - Why: KLN owns `OpCx` (contract 5.6). D-KLN-57 (KLN line 140): "due every 10 ms of monotonic time on the operation's thread"; PLT lines 182 and 248 agree.
9. **[medium] The general operations are Flux's.** `### General operations for non-variational methods` (line 538)
   - Now: "COV's general operations serve particles, ray tracing, boundary elements and ELX's placer"
   - Must say: "Flux's general operations serve COV's particle methods, ray tracing, boundary elements and ELX's placer"
   - Why: contract 7.1 ("Flux also provides … the general operations that non-variational methods need"); D-COV-11 (COV line 581): hot loops run "on general Flux operations".
10. **[medium] Symmetry comes from MEC's declarations.** `### Per-region models` (line 385) and `### Reduction by symmetry` (line 398)
    - Now: "| Certified symmetry analysis and section |" → Must say: "| MEC's declared symmetry; `anvil::section` |"
    - Now: "are detected by `mark_reduction` from Anvil's certified analysis or declared with" → Must say: "are detected by `mark_reduction` from MEC's declared symmetries or declared with"
    - Why: ANV specifies no symmetry analysis. MEC line 346: "A `mirror` and a complete `circular` pattern record their plane or axis as a declared symmetry. Flux may use it"; MEC's Interfaces row to FLX lists "declared symmetries". `anvil::section` is ANV's phase 1 operation (ANV line 764).
11. **[medium] Manufacturing constraints read MFG's process profiles from phase 2.** `### Topology optimization` (line 876)
    - Now: "and MFG's process profiles parameterize manufacturing constraints."
    - Must say: "and manufacturing constraints take their limits as arguments, read from MFG's process profiles from phase 2."
    - Why: MFG's row to FLX offers process profiles for manufacturing-constraint forms in phase 2 (MFG line 1142); this tab's "Manufacturing constraints" row ships additive and unrestricted constraints in phase 1 (line 905).
12. **[medium] Name the circuit Newton class ELX relies on.** `### Calibrated estimates` (line 164)
    - Now: "Later phases add classes for reduction, step halving, modal truncation, bolted joints and solution verification."
    - Must say: "Later phases add classes for reduction, step halving, modal truncation, bolted joints, solution verification and circuit Newton residuals (`mna_newton`, on ELX's corpus)."
    - Why: FLX owns calibration classes (contract 7.1). ELX lines 702, 738 and 1279 rely on `mna_newton`, "measured on ELX's simulation corpus by FLX's calibration machinery", which this tab never names.
13. **[medium] Owner rows for three 13.4 capabilities.** `## Coupling, homogenization and co-simulation` capability table, after the "Monolithic and partitioned coupling" row (line 847)
    - Now: "| Monolithic and partitioned coupling | Product-space forms; Aitken and interface quasi-Newton; conservative transfer | `CouplingDiverged { residual_history }` | FLX-O-COUP-1 | 1 (one way), 2, 3, 4, 5 per coupling |"
    - Must say: the same row, followed by two new rows: "| Conjugate heat transfer | Robin partitioned, or monolithic on a shared octree with wall refinement | `CouplingDiverged { residual_history }` | FLX-O-COUP-1 | 3 (laminar, natural convection), 4 (turbulent) |" and "| Electro-thermal coupling | Joule heating with temperature-dependent resistivity; monolithic Newton with continuation | `Runaway { power }` at the turning point | FLX-O-COUP-1 | 4 |". Add to FLX-O-COUP-1's pass criterion a conjugate-heat case and a self-heating strip case.
    - Why: contract 13.4 makes FLX the owner of laminar conjugate heat transfer (3), turbulent conjugate heat transfer (4) and electro-thermal coupling (4), and "the owner's capability table specifies each row". This tab phases them only in the method catalog (lines 1291 and 1292) and prose (line 821). ELX 10 adds a `Requires:` entry on the new electro-thermal row.
14. **[medium] Interfaces rows give wrong phases or omit what others use.** `## Interfaces with other subsystems` (lines 1419 to 1427)
    - Now (ING): "plans and form checks; the `kernels::expr` symbolic layer | `Expr<T>`, `SolvePlan` | 0 |" → Must say: "plans and form checks; the `kernels::expr` symbolic layer | `Expr<T>`, `SolvePlan` | 0; 1 (plans, `modes`); 2 (`continue_in`) |". `flux::plan` and eigen-solvers are phase 1 (lines 428, 677), arc length phase 2 (line 1266).
    - Now (ANV): "| ANV | `field` and `kernels`; `Sampler`s with error and gradient bounds; `geometry_density`; reduction marking; sizing and metric Fields | `Field` | 1 |" → Must say: "| ANV | `field` and `kernels`; `Sampler`s with error and gradient bounds; `geometry_density`; reduction marking; sizing and metric Fields | `Field` | 0 (`field`, `kernels`); 1; 2 (sizing and metric Fields) |". ANV uses the kernel IR in phase 0 (ANV line 825); sizing and metric Fields are phase 2 (line 597).
    - Now (COV): "EHL film Fields; rotor ladder; explicit-dynamics functionals and ensembles | `Field` | 2 |" → Must say: "EHL film Fields; rotor ladder; explicit-dynamics functionals and ensembles | `Field` | 2; 3 (EHL, drop functionals); 4 (rotor ladder); 5 (crash ensembles) |". Contract 13.4 and this tab's rows (lines 494, 556, 557).
    - Now (MEC, phase 1): "strut stress for strut-strength checks; idealizations; influence coefficients | `Field` | 1 |" → Must say: "strut stress for strut-strength checks; idealizations; density topology optimization with additive and unrestricted constraints for `std::mech::generate` | `Field` | 1 |". Influence coefficients are phase 2 (line 937); MEC's generative design requires "FLX Density topology optimization" at phase 1 (MEC line 462).
    - Now (MEC, phase 2): "tied interfaces; manufacturing constraints for `std::mech::generate`; shell and ply optimization | `Field`, `Assembly` | 2 |" → Must say: "tied interfaces; influence coefficients; milling, two-axis cutting and casting constraints for `std::mech::generate`; shell and ply optimization | `Field`, `Assembly` | 2; 4 (rods); 6 (ply optimization) |". `flux::solve_rod` is phase 4 (line 815), plies phase 6 (line 906).
    - Now (MFG): "| MFG | Modal analysis; additive distortion and weld joint loads; thermo-elasto-plasticity; filling flow with wall resolution; topology optimization with manufacturing constraints; GCI on warpage | `Field`, `Body` | 1 |" → Must say: "| MFG | Modal analysis; topology optimization with manufacturing constraints; additive distortion and weld joint loads; thermo-elasto-plasticity; rigid multibody contact for assembly stability; filling flow with wall resolution; GCI on warpage | `Field`, `Body` | 1 (modal, topology optimization); 2; 3 (filling, GCI) |". This tab's rows (lines 214, 813, 848, 850); MFG D-MFG-17 relies on "Flux rigid-body contact" (MFG line 865).
15. **[low] Phasing puts no-gate rows under golden products.** `## Phasing` (lines 1558 to 1560)
    - Now: "GP3: fitted tetrahedra with mortar contact, cyclic modal analysis, linear dynamics, rigid multibody" → Must say: "GP3: fitted tetrahedra with mortar contact, rigid multibody"
    - Now: "additive distortion; 10M-DOF `SignOff` solves" → Must say: "linear dynamics and cyclic modal analysis; additive distortion; 10M-DOF `SignOff` solves"
    - Now: "layered sheets, Helmholtz solvers, circuit DAEs, FDTD, FMU import, solver decks, EHL, 50M-DOF and flow throughput rows" → Must say: "layered sheets, circuit DAEs, FDTD, FMU import, 50M-DOF and flow throughput rows. Also Helmholtz solvers, solver decks and EHL"
    - Now: "S-parameter goals, the plane-pair cavity model, FMU export and SSP," → Must say: "S-parameter goals, FMU export and SSP,"; and end the phase 4 cell with ". Also the plane-pair cavity model"
    - Why: contract 13.4's first gates: linear dynamics "None; COV rotordynamics and vibration", symmetry reductions "None; parity floor", Helmholtz solvers "None; COV linear acoustics", EHL and the plane-pair cavity model "None"; imported decks are a parity-floor row with no gate.
16. **[low] "Snapshot" names a rendered image only.** `### Method catalogs` (line 1327) and `## Reduced models and surrogates` capability table (line 966)
    - Now: "| Snapshots (proper orthogonal decomposition); DEIM" → Must say: "| Solution samples (proper orthogonal decomposition); DEIM"
    - Now: "| Snapshot bases; certified or residual bounds |" → Must say: "| Bases from solution samples; certified or residual bounds |"
    - Why: contract 2 defines Snapshot as "a rendered image of a `ViewState` under a `RenderProfile`".
17. **[low] Basis intervals, not enclosures.** "Property-basis propagation" capability row (line 210)
    - Now: "| Property-basis propagation | Basis enclosures into the input part"
    - Must say: "| Property-basis propagation | Basis intervals into the input part"
    - Why: D-COV-13 names the basis an interval and rejects "one guaranteed enclosure for both uses".
18. **[medium] CCR-FLX-12 is accepted.** `## Contract change requests` (line 1571)
    - Now: the bullet beginning "- **CCR-FLX-12, shared rows for rotors, lubrication and board cavities.**"
    - Must say: "None."
    - Why: contract 18 adds the three rows to 13.4 (elastohydrodynamic lubrication 3, plane-pair cavity model 4, rotor aerodynamics 4, owner FLX); this tab's rows (lines 549, 556, 557) already carry those phases.

## COV

1. **[high] FLX has six phase 1 classes.** `### Who fills which part` (line 117)
   - Now: "Phase 1 needs FLX's four classes, each with 300 held-out samples: `elasticity.peak` and `elasticity.eigen` for immersed linear elasticity at p = 2 to 6, and `lattice.strut_stress` and `lattice.buckling` for the beam lattice's strut stresses and buckling factors."
   - Must say: "Phase 1 needs FLX's six classes, each with 300 held-out samples: `elasticity.peak`, `elasticity.peak.interactive`, `elasticity.frequency` and `elasticity.buckling` for immersed linear elasticity at p = 2 to 6, and `lattice.strut_stress` and `lattice.buckling` for the beam lattice's strut stresses and buckling factors."
   - Why: FLX lines 157 to 162 list six classes; FLX's phase 1 gate says "The six calibration classes" (line 1557). `elasticity.eigen` no longer exists.
2. **[medium] The phase 1 gate repeats the old count.** `## Phasing` (line 1215)
   - Now: "four calibration classes;"
   - Must say: "FLX's six phase 1 calibration classes;"
   - Why: as above.
3. **[high] The bracket's stress is ING's 94 MPa.** `### The bracket's check` (lines 13, 17, 21, 23), `### When the answers change` (line 31), `## Model form: how far tests say a model can be wrong` (line 105) and `### The bracket's model-form bound` (line 164)
   - Now: "Flux reports the regularized peak at the web-root fillet as 118 MPa" → Must say: "Flux reports the regularized peak at the web-root fillet as 94 MPa"
   - Now: "Three more questions decide whether 118 MPa may be compared with 144 MPa at all." → Must say: "Three more questions decide whether 94 MPa may be compared with 144 MPa at all."
   - Now: "which at 118 MPa is 10.2 MPa" → Must say: "which at 94 MPa is 8.1 MPa"
   - Now: "The check's total is then 118 + 1.5 + 10.2 = 129.7 MPa against a limit of 144 MPa." → Must say: "The check's total is then 94 + 1.5 + 8.1 = 103.6 MPa against a limit of 144 MPa."
   - Now: "here 1.6 times to 16.3 MPa" → Must say: "here 1.6 times to 12.9 MPa"
   - Now: "the bracket's 10.2 MPa" (line 105) → Must say: "the bracket's 8.1 MPa"
   - Now: "At the bracket's 118 MPa the part is therefore 10.2 MPa" → Must say: "At the bracket's 94 MPa the part is therefore 8.1 MPa"
   - Why: ING owns the canonical walk-through (contract 6) and its figures are self-consistent: 94 MPa ± 1.5 MPa at 6 mm (ING line 838) and about 210 MPa at 4 mm, the (6/4)² bending scaling. This tab's 8.6% relative transfer gives 0.086 × 94 = 8.1 MPa, inflated 1.6 times to 12.9 MPa. This tab's 240 MPa basis and 144 MPa limit stand, and ING follows them (ING 2).
4. **[high] Eigenvalue bounds are two-sided.** `### Dynamics and stability` (line 341) and the modal analysis row of `#### Dynamics and stability` (line 874)
   - Now: "Flux bounds each eigenvalue on the unsafe side (FLX)." → Must say: "Flux bounds each eigenvalue on both sides, since an immersed discretization may err either way (FLX)."
   - Now: "eigenvalue bounds on the unsafe side" → Must say: "two-sided eigenvalue bounds"
   - Why: D-FLX-41 (FLX line 656) applies the bound "two-sided", with the one-sided reading only on fitted conforming discretizations; MEC's D-MEC-30 rejects one-sided bounds on immersed models.
5. **[high] The critical-distance failure is FLX's.** D-COV-34 (line 371), `### The parity map` capability table (line 453), Reference `### Failures` (line 848), COV-O-MAT-11 (line 1206)
   - Now: "A check that asks for another method fails with `CriticalDistanceMethodMismatch { calibrated, requested }`." → Must say: "A check that asks for another method fails with FLX's `CriticalDistanceMismatch { calibrated, requested }`."
   - Now: "| Method recorded per Material; the method's own operator | `CriticalDistanceMethodMismatch { calibrated, requested }` |" → Must say: "| Method recorded per Material; the method's own operator (FLX) | `CriticalDistanceMismatch { calibrated, requested }` |"
   - Now: "`BatchesNotPoolable`, `CriticalDistanceMethodMismatch { calibrated, requested }`, `MissingStandard { code, edition }`" → Must say: "`BatchesNotPoolable`, `MissingStandard { code, edition }`"
   - Now: "a mismatched method fails with `CriticalDistanceMethodMismatch`" → Must say: "a mismatched method fails with `CriticalDistanceMismatch`"
   - Why: FLX's `tcd` goal raises the failure (FLX lines 131 and 205, FLX-O-ERR-12), so it renders `flux/critical_distance_mismatch`; one failure keeps one name. FLX moves its row to phase 1 (FLX 3), so this row's phase 1 holds.
6. **[medium] The Interfaces row to ING names the wrong type.** `## Interfaces with other subsystems` (line 1143)
   - Now: "property reads as exact basis intervals for limits | Ingot packages, `Approx<Q>` |"
   - Must say: "property reads as exact basis intervals for limits | Ingot packages, `Range<Q>` |"
   - Why: D-COV-13 makes the read an exact interval with no budget part; `Approx<T>` carries an `ErrorBudget` (contract 5.1), while ING provides "`Range` as interval" (ING lines 234, 1361).
7. **[medium] The Interfaces row to FLX reverses the general operations and omits `flux-op-material`.** `## Interfaces with other subsystems` (line 1142)
   - Now: "property scatter for solve inputs; the operations non-variational methods need"
   - Must say: "property scatter for solve inputs; the method logic non-variational methods run on Flux's general operations; the `flux-op-material` operation family, owned with FLX"
   - Why: contract 7.1 gives the general operations to Flux, and D-COV-11 (line 581) keeps only method logic here. This tab's Reference lists `flux-op-material` (line 797), which contract 12 allows, but no Interfaces row tells FLX.
8. **[medium] The Interfaces row to MEC puts phase 2 and 5 content at 1.** `## Interfaces with other subsystems` (line 1147)
   - Now: "constitutive draping (13.4) | `Material`, `PhysicsModel` | 1 |"
   - Must say: "constitutive draping (13.4) | `Material`, `PhysicsModel` | 1; 2 (contact, joint and dynamics models; ratings); 5 (constitutive draping) |"
   - Why: this tab's rows: ratings 2 (line 454), contact 2 (line 866), linear dynamics 2 (line 341), constitutive draping 5 (line 465).
9. **[low] The Interfaces row to MFG puts later content at 1.** `## Interfaces with other subsystems` (line 1148)
   - Now: "phase-transformation kinetics; environmental records; gear, bearing and shaft ratings | `Field`, `ValidityEnvelope`, `EnvironmentalRecord` | 1 |"
   - Must say: "phase-transformation kinetics; environmental records; gear, bearing and shaft ratings | `Field`, `ValidityEnvelope`, `EnvironmentalRecord` | 1; 2 (environmental records, ratings); 4 (phase-transformation kinetics) |"
   - Why: contract 13.4 phases ratings at 2 and kinetics at 4; environmental records are phase 2 (line 788).
10. **[medium] Rotor aerodynamics is FLX's capability.** `### Rotors and aircraft` (line 425)
    - Now: "**Decision D-COV-31:** Rotor aerodynamics is a ladder of three COV packages."
    - Must say: "**Decision D-COV-31:** Rotor aerodynamics, FLX's capability in phase 4 (13.4), is a ladder of three rungs with COV envelopes."
    - Why: contract 13.4 (ruling CCR-FLX-12) makes FLX the owner, also COV and ELX; FLX line 526: "All three arrive in phase 4, and COV records their envelopes"; FLX line 556 is the owner row. This tab's row (line 460) already covers only envelopes.
11. **[low] Phasing puts no-gate rows under golden products.** `## Phasing` (lines 1216 to 1218)
    - Now: "weld distortion from coupons at C3; inherent strain for metal powder bed fusion; environmental records with generic factors" → Must say: "weld distortion from coupons at C3. Also inherent strain for metal powder bed fusion and environmental records with generic factors"
    - Now: "laminar conjugate heat transfer, linear acoustics and drop functionals; warpage and drop models at C3" → Must say: "laminar conjugate heat transfer and drop functionals; warpage and drop models at C3. Also linear acoustics"
    - Now: "dynamometer and thermal tests; phase-transformation kinetics" → Must say: "dynamometer and thermal tests. Also phase-transformation kinetics"
    - Why: contract 13.4's first gates: additive inherent strain "None; MFG's metal powder bed fusion compensation", Helmholtz solvers "None; COV linear acoustics", phase-transformation kinetics "None; transient weld simulation".

## KLN

1. **[high] The derivative retention tier is `StepState`.** `## Derivatives` (lines 244 to 254) and KLN-O-DERIV-1 (line 1336)
   - Now: "Transient solves save their step checkpoints as CAS objects keyed by (`NodeKey`, step) in the `Checkpoint` retention tier, which eviction drops first. A resumed solve or adjoint is bit-identical whether its checkpoints were kept, reloaded or recomputed." → Must say: "Transient solves save their step state as CAS objects keyed by (`NodeKey`, step) in the `StepState` retention tier, which eviction drops first (contract 7.1). A resumed solve or adjoint is bit-identical whether its step state was kept, reloaded or recomputed."
   - Now: "with step checkpoints in their own retention tier." → Must say: "with step state in its own retention tier."
   - Now: "and checkpoints that are cheap to recompute must yield memory to ordinary values" → Must say: "and step state that is cheap to recompute must yield memory to ordinary values"
   - Now: "checkpoints stored as ordinary values" → Must say: "step state stored as ordinary values"
   - Now: "| Step checkpoints | `Checkpoint` retention tier keyed by (`NodeKey`, step) | None: an evicted checkpoint is recomputed |" → Must say: "| Step state | `StepState` retention tier keyed by (`NodeKey`, step) | None: evicted step state is recomputed |"
   - Now: "adjoints resumed from evicted checkpoints are bit-identical" → Must say: "adjoints resumed from evicted step state are bit-identical"
   - Why: contract 7.1 now names the tier `StepState` (ruling CCR-KLN-12), so "checkpoint" names only transparency-log heads (lines 547, 831, 886 stay).
2. **[medium] CCR-KLN-11 and CCR-KLN-12 are accepted.** `## Contract change requests` (lines 1416, 1417)
   - Now: the two bullets beginning "- **CCR-KLN-11, approval delegation.**" and "- **CCR-KLN-12, the derivative retention tier.**"
   - Must say: "None."
   - Why: contract 18 adds the approval-delegation row to 5.4 and renames the tier in 7.1.
3. **[medium] Delegation signers follow contract 5.4's row.** `### Review routes and delegation` (line 723)
   - Now: "Delegation covering physical-effect Acts or `controls` needs two people"
   - Must say: "Delegation covering physical-effect Acts or `controls` needs two people, one an export officer (contract 5.4)"
   - Why: contract 5.4's approval-delegation row: "two people, one an export officer, when the scope covers physical-effect Acts or `controls` payloads".
4. **[medium] `auth` and `label` are AGT's families.** `### Failures and Aborts` (line 126)
   - Now: "this tab's families are `kiln`, `cas`, `repo`, `plm`, `trust`, `auth`, `label`, `evidence` and `share`, registered with AGT"
   - Must say: "this tab's families are `kiln`, `cas`, `repo`, `plm`, `trust`, `evidence` and `share`, registered with AGT; it also raises codes in AGT's `auth` and `label` families"
   - Why: contract 7.6: "AGT keeps the family registry"; AGT lists `auth` (line 1254) and `label` (line 1263) as its own.
5. **[medium] The override error is AGT's `edit/override_site_unknown`.** `### The operation contract` capability table, "Literal overrides" (line 164)
   - Now: "an override that names no site is rejected by `api` as `edit/unknown_site`"
   - Must say: "an override that names no site is rejected by `api` as `edit/override_site_unknown`"
   - Why: AGT owns the `edit` family; AGT lines 234 and 1194 name `edit/override_site_unknown`.
6. **[medium] The per-call assertion failure is `auth/assertion_required`.** `### Privacy` capability table, "Local credentials" (line 905)
   - Now: "`auth/user_presence_required`"
   - Must say: "`auth/assertion_required`"
   - Why: AGT owns the `auth` family (line 1254), and its "Local credentials" row fails with `auth/assertion_required` (AGT lines 138, 229).
7. **[medium] Three Interfaces rows omit ING.** `## Interfaces with other subsystems` (lines 1303, 1306, 1307)
   - Now: "| ANV, FLX, COV, MFG, ELX | The operation contract and registry;" → Must say: "| ING, ANV, FLX, COV, MFG, ELX | The operation contract and registry;"
   - Now: "| ANV, FLX, PLT | Grades and class acceptance;" → Must say: "| ING, ANV, FLX, PLT | Grades and class acceptance;"
   - Now: "| COV, FLX, MFG | Evidence records pinned by `CheckId`;" → Must say: "| ING, COV, FLX, MFG | Evidence records pinned by `CheckId`;"
   - Why: ING's limits follow this tab's limit catalog (ING line 695) and its reverse mode uses `Differentiable` (line 743); ING's guest SDK is generated from `crucible:host` (ING lines 928, 935); ING's checks read policy allowances and its gate counts Waivers (ING lines 824 to 828).
8. **[medium] The operation registry states the version statuses ANV and PLT use.** `### The operation contract` capability table (line 170)
   - Now: "| `OpImpl`, `DynOp`, `OpRegistry`, `OpCx` in `base-op`; explicit registration lists |"
   - Must say: "| `OpImpl`, `DynOp`, `OpRegistry`, `OpCx` in `base-op`; explicit registration lists; per-version status `Current`, `Deprecated`, `Retired` or `Yanked` |"
   - Why: ANV's registry row relies on "KLN's registry; status `Current`, `Deprecated`, `Retired` or `Yanked`" (ANV line 1140), and PLT's merge queue on "`Current` and `Deprecated` operation versions" (PLT line 902).
9. **[low] The priority-class table copies AGT's.** `### Scheduling and cancellation` (line 181 and the table at lines 183 to 189)
   - Now: "Kiln picks PLT's `PoolLane` from the request's `PriorityClass` (AGT)."
   - Must say: "Kiln runs each request on the pool lane its `PriorityClass` maps to and preempts at node boundaries as [AGT, Priority classes](09-agents.md#priority-classes) states." Delete the five-row table that follows.
   - Why: contract 5.6 makes `PriorityClass` AGT's, and AGT's table (lines 285 to 291) holds the classes, lanes and preemption; PLT restates the mapping in one line (PLT line 170). This copy already drifts: its `Ci` row says "Both above" where AGT says "The classes above". Saves about 60 words.
10. **[low] The single-host sandbox sentence restates PLT's install.** `### Placement and the single host` (line 280)
    - Now: "It runs Proposal CI in Firecracker where KVM exists [Firecracker start] and in gVisor otherwise, refuses Proposal CI when neither works, and runs the trusted builder as a separate OS user."
    - Must say: "PLT's install runs Proposal CI in a microVM sandbox and the trusted builder as its own OS user."
    - Why: PLT owns deployment (D-PLT-51); D-PLT-44 (PLT line 702) states exactly this. Drop the `[Firecracker start]` Sources row if nothing else cites it.
11. **[low] Only the attestation service is packaged by PLT.** `### Crates` (line 1014)
    - Now: "The attestation service, the live-session relay and the hardware runner (KLN, packaged by PLT)"
    - Must say: "The attestation service, the live-session relay and the hardware runner (KLN; PLT packages the attestation service)"
    - Why: contract 12: "`attestation` (KLN, packaged by PLT)" but "`relay` and `rig-runner` (KLN)".
12. **[low] Contract 5.3's integrity rule restated.** `### Three parts of a label` (line 922)
    - Now: "- **Integrity** never blocks a read or a write. Merging the Change that introduced a pin, an Asset or a source span clears it on typed values: a merged supplier STEP import yields trusted geometry and numbers, while its part names stay `ExternalText`, and a new Asset revision starts untrusted."
    - Must say: "- **Integrity** follows contract 5.3's rule; a new Asset revision starts untrusted."
    - Why: contract 5.3: "This paragraph is the only statement of the rule; tabs cite it." This section's own lead (line 918) says so.
13. **[low] "Policy" alone.** `### Authorization` (line 876) and `### Items` (line 581)
    - Now: "Only these two things are called policy." → Must say: delete the sentence.
    - Now: "so a policy update never changes the verdict of an unchanged Change" → Must say: "so a policy package update never changes the verdict of an unchanged Change"
    - Why: contract 2, Policy package: never call it "policy" alone.
14. **[low] Five abbreviations used before they are spelled out.** `### Collection, tiers and replication` (line 379), `### Items` (line 575), `### Revisions and lifecycle states` (line 629), `### Signature records` (line 823), `### Supplier packages and derived views` (line 977)
    - Now: "local disk or OPFS, the team server" → Must say: "local disk or the browser's origin private file system (OPFS), the team server"
    - Now: "release package (STEP AP242 with PMI, drawings" → Must say: "release package (STEP AP242 with product and manufacturing information (PMI), drawings"
    - Now: "revision labels on release tags, `InWork` and `Released`, and the EBOM." → Must say: "revision labels on release tags, `InWork` and `Released`, and the engineering BOM (EBOM)."
    - Now: "People sign through WebAuthn with a device-bound approval credential" → Must say: "People sign through WebAuthn (Web Authentication) with a device-bound approval credential"
    - Now: "drawings with QIF 3.0 inspection plans" → Must say: "drawings with Quality Information Framework (QIF) 3.0 inspection plans"
    - Why: contract 11 spells out every abbreviation at first use in each tab.
15. **[high] Git is the storage format, and any host can be home.** `### Git export` (lines 419 to 421), its capability row (line 448), KLN-O-GIT-1 (line 1353), `### Span provenance` (line 425) and `### Readers who are not cleared` (line 928)
    - Now: "### Git export" → Must say: "### Git storage and hosts"
    - Now: "Git is an export, not the storage format. `crucible export git` writes Ingot text and `ingot.lock`, and because `CallSite`s derive from text alone, re-importing leaves every `EntityId` unchanged." → Must say: "A Crucible repository is an ordinary Git repository ([contract 7.1](../contract.md#repo-plm-and-trust)), so people clone, branch and push it with their own tools. `repo` writes each Change as one commit through gitoxide, with a `Crucible-Object` trailer holding its `ObjectId`; signature records live under `refs/crucible/`, large Assets are Git LFS pointers the CAS serves, and computed results stay in the CAS. Any Git host can be home: on protected branches Kiln is a required status check, and it signs a release only when every merge in the released history carries its signature records. Because `CallSite`s derive from text alone, cloning, pushing or mirroring through any host and rebuilding leaves every `EntityId` unchanged."
    - Now: "| Git export | Ingot text and `ingot.lock`; identities unchanged on re-import | `repo/export_unrepresentable` for content Git cannot hold, such as an unresolved conflict | KLN-O-GIT-1 | 1 |" → Must say: "| Git storage and hosts | Changes as commits with `Crucible-Object` trailers; signature records under `refs/crucible/`; LFS Assets; Kiln as a required status check on any host; conflicted Changes as extra trees, never on a protected branch | A release whose history holds a merge without its signature records is refused, naming the merge | KLN-O-GIT-1 | 1 |" (this tab names the `repo/` failure code)
    - Now: "| KLN-O-GIT-1 | Git round trip | Export, re-import and rebuild keep every `EntityId` and `GeometryId` on every golden product |" → Must say: "| KLN-O-GIT-1 | Git storage and hosts | Cloning, pushing and mirroring through a second Git host and rebuilding keep every `EntityId` and `GeometryId` on every golden product; a merge pushed past a host's branch protection blocks the release |"
    - Now: "through a language-server connection, a file or Git import, or any other channel" → Must say: "through a language-server connection, a file import, a push from a Git client or any other channel"
    - Now: "Any node joining an undeclassified output is unreadable to them." → Must say: "Any node joining an undeclassified output is unreadable to them. Git has no per-path read control, so such a module lives in its own repository, which the product repository references by commit; an organization whose readers are all cleared keeps one repository (contract 7.1)."
    - Why: contract 7.1, 2 and 12 (versions 7.2 and 7.3, ruling FD-5 of 12 October 2026) make Changes Git commits stored through gitoxide, let any Git host be home with Kiln as a required status check, record conflicts as extra trees, and split repositories only per reader. KLN owns `repo`, so it also checks that `### Changes and refs` (ref names map to Git refs), `### What a clean merge means` (conflicts) and the Reference `### Repository objects` agree with Git storage, and states any further consequence in its own words. Contract 7.1's anchor is `#repo-plm-and-trust`.

## MEC

1. **[high] Ordered explode steps land in phase 1.** `## Assemblies` capability table, "Exploded views" (line 646); `## Phasing` (line 1506); `## Interfaces with other subsystems` (line 1391)
   - Now: "| `CollidesDuringStep { step, pair }` (warning) | MEC-O-AS-5 | 2, 3 (automatic) |" → Must say: "| `CollidesDuringStep { step, pair }` (warning) | MEC-O-AS-5 | 1, 3 (automatic) |"
   - Now: "push-pull, basic mates, GD&T" → Must say: "push-pull, basic mates, explode steps, GD&T"
   - Now: "context queries for Edit in context; `auto_drawing`; revision markers | `Field`, `Sketch`, `Context` | 1, 2 |" → Must say: "context queries for Edit in context; exploded-view steps; `auto_drawing`; revision markers | `Field`, `Sketch`, `Context` | 1, 2 |"
   - Why: contract 13.4's phase 1 parity floor (owner UIX) includes exploded views, and UIX's phase 1 rows build them from `explode(asm, steps)` (UIX lines 282, 324, 382). Instances and mates are already phase 1 here (lines 635, 637); `explode_auto` stays phase 3. UIX 8 adds the matching `Requires:` entry.
2. **[high] Non-size sites keep their nominal under `Mmc` and `Lmc`.** `### Stack-up and variation analysis` capability table, "Geometry at a tolerance point" (line 1033)
   - Now: "`NotOfSize { site }` for `Mmc` or `Lmc` on a site without a size"
   - Must say: "Non-size sites keep their nominal under `Mmc` and `Lmc` and are listed in the report (ING)"
   - Why: ING owns `realize:` and decides (ING line 345): "A site that is not a feature of size keeps its nominal under `Mmc` and `Lmc`, and the Evaluation report lists it."
3. **[medium] Calibration classes follow FLX's names.** `### What may decide a check` (lines 1176 to 1179, 1184)
   - Now: "| Static stress on regularized peaks in solids (GP1) | `Estimated` | `elasticity.peak` |" → Must say: "| Static stress on regularized peaks in solids (GP1) | `Estimated` | `elasticity.peak`; `elasticity.peak.interactive` at `Interactive` |"
   - Now: "`lattice.buckling`; `elasticity.eigen` for buckling factors" → Must say: "`lattice.buckling`; `elasticity.buckling`"
   - Now: "`elasticity.eigen` for frequencies" → Must say: "`elasticity.frequency`"
   - Now: "Frequencies, whose operator is fixed, are a separate entry of the eigen class." → Must say: "Frequencies, whose operator is fixed, use their own class, `elasticity.frequency`."
   - Why: FLX owns calibration classes; its phase 1 table (FLX lines 157 to 162) has `elasticity.peak.interactive`, `elasticity.frequency` and `elasticity.buckling`, and no `elasticity.eigen`.
4. **[medium] The drape failure is ANV's kind.** `## Composites design` capability table, "Kinematic drape" (line 806)
   - Now: "`ShearLimitExceeded { ply, region, max }`"
   - Must say: "`ExcessiveShear { region, angle }`"
   - Why: the row requires `anvil::drape_kinematic`, whose failure is `ExcessiveShear { region, angle }` (ANV line 761); ANV-O-NAME-7 requires feature failure kinds to equal ANV's plus MEC's marked feature-level kinds.
5. **[medium] Late-bound fields enter the definition as placeholders.** `### Drawings` (line 1072)
   - Now: "Title-block fields, revision text, dates and approvers are late-bound release fields, excluded from the Item's definition digest"
   - Must say: "Title-block fields, revision text, dates and approvers are late-bound release fields, which enter the Item's definition digest only as placeholders"
   - Why: KLN owns `ItemDefinition` (contract 5.6: "Late-bound fields stay placeholders"); KLN line 607 says the same.
6. **[medium] Interfaces rows omit what ANV, ELX and MFG read.** `## Interfaces with other subsystems` (lines 1381, 1388, 1389)
   - Now: "feature-level failure kinds; the Assembly `GeometryId` encoding | `FeatureError`, `HoleSpec`, `ThreadSpec`, `CoordSys` |" → Must say: "feature-level failure kinds; the Assembly `GeometryId` encoding; the `Continuity` enum | `FeatureError`, `HoleSpec`, `ThreadSpec`, `CoordSys`, `Continuity` |". ANV line 477: "`Continuity` is MEC's order enum".
   - Now: "plies, harness geometry, balloons; the drawing library for in-process drawings; the `realize` point of each export |" → Must say: "plies, harness geometry, balloons, `BendRule` and `BendTable`, preload ranges, mates for machine, robot and fixture Assemblies; the drawing library for in-process drawings; the `realize` point of each export |". MFG reads them (MFG lines 131, 397, 403, 804, 812, 869).
   - Now: "| ELX | Enclosure geometry and checks; mates; interface records for board outlines and keep-outs; routes, bundle and formboard geometry; fastener selection | `Assembly`, `Route`, `CoordSys` | 1, 3 |" → Must say: "| ELX | Enclosure geometry and checks; mates; gear records for drivetrain elements; interface records for board outlines and keep-outs; routes, bundle and formboard geometry; fastener selection | `Assembly`, `Route`, `CoordSys` | 1, 2 (gear records), 3, 4 (formboard) |". ELX's "Drivetrain elements" row (ELX line 191, phase 2) reads MEC's gear records; MEC's formboard row is phase 4 (line 852).
7. **[low] Tie kinds are FLX's `Bonded` and `NoSeparation`.** `### Interference and clearance` (line 543)
   - Now: "each listed for confirmation as bonded or frictionless"
   - Must say: "each listed for confirmation as `Bonded` or `NoSeparation`"
   - Why: D-FLX-52 (FLX line 714): ties are "`Bonded` by default … and `NoSeparation`"; frictionless contact with separation is a separate nonlinear path.
8. **[low] An instruction-capable canvas taints the context.** `### Reference images` (line 171)
   - Now: "which marks its context as untrusted ([AGT](09-agents.md))"
   - Must say: "which sets its context `instruction_tainted` ([AGT](09-agents.md))"
   - Why: contract 7.6 and AGT line 440: reading an instruction-capable image sets `instruction_tainted`.
9. **[low] The drag priority class is AGT's.** `### Solver` (line 196)
   - Now: "at PLT's `Drag` priority"
   - Must say: "at the `Drag` priority class, on PLT's `Drag` lane"
   - Why: contract 5.6: `PriorityClass` [AGT]; PLT owns only `PoolLane` (contract 12).
10. **[low] The scan-to-CAD failures are ANV's.** `### SubD and scans` capability table, "Scan to CAD" (line 705)
    - Now: "`FitRejected { region, rms }`"
    - Must say: "`FitFailed { residual }`; `NotConverged { rms }`"
    - Why: the row rests on `anvil::fit` and `anvil::align`, whose failures are `FitFailed { residual }` and `NotConverged { rms }` (ANV lines 895, 1055).
11. **[low] Continuity thresholds copied from ANV.** `### Continuity and surfaces` (line 665)
    - Now: "Default thresholds: G0 within the edge's own tolerance, G1 within 10⁻⁶ rad, G2 within 10⁻⁴ relative curvature difference and G3 within 10⁻³ relative difference."
    - Must say: "The default threshold per order is ANV's, and each check may override it." Cut the next sentence of the paragraph too, which restates the length threshold and the override.
    - Why: ANV states the defaults for `analyze_continuity` (ANV line 744, row line 1045).
12. **[low] The definition tolerance is KLN's formula.** `### Identity of Parts and Assemblies` (line 1257)
    - Now: "KLN's definition tolerance is the geometry change below which an Item keeps its revision."
    - Must say: "KLN's definition tolerance, the geometry change below which an Item keeps its revision, reads the Part's tightest or general tolerance and its resolution ρ ([KLN](05-kiln-repo-plm.md))." Delete the rest of the paragraph.
    - Why: KLN owns the formula (KLN line 613: "the larger of 10ρ … and the smaller of 0.1 µm and 1% of the Item's tightest tolerance").
13. **[low] Flux's symmetric reductions are phase 2.** `### Patterns, mirror and hulls` (line 346)
    - Now: "Flux may use it for symmetric, antisymmetric and cyclic-sector reductions, after checking that the loads respect it"
    - Must say: "Flux may use it for symmetric, antisymmetric and cyclic-sector reductions from phase 2 (contract 13.4), after checking that the loads respect it"
    - Why: contract 13.4: symmetry, antisymmetry and cyclic-sector reductions, phase 2, owner FLX, also MEC.
14. **[low] Git stores the text.** D-MEC-33's *Why:* (line 209)
    - Now: "belong in the text that `crucible export git` carries"
    - Must say: "belong in the text Git stores"
    - Why: contract 7.1 (v7.3, ruling FD-5): a Crucible repository is an ordinary Git repository; `crucible export git` no longer exists.

## MFG

1. **[high] The production-site record is KLN's `Site`.** `## Factory connection and digital twin`, D-MFG-40 (line 966) and the "Production sites" row (line 984); `## Interfaces with other subsystems` (line 1146)
   - Now: "keyed by (EBOM configuration point, `ProductionSite`), where a `ProductionSite` is a policy-package record" → Must say: "keyed by (EBOM configuration point, `Site`), where a `Site` is KLN's policy-package record"
   - Now: "| Production sites | MBOM, routings and work centres keyed by (EBOM configuration point, `ProductionSite`);" → Must say: "| Production sites | MBOM, routings and work centres keyed by (EBOM configuration point, `Site`);"
   - Now: "| KLN | MBOM rules and routings per production site; nonconformance records linked to corrective actions; as-built records | Records | 2 |" → Must say: "| KLN | MBOM rules and routings per `Site`; nonconformance records linked to corrective actions; as-built records | Records | 2; 3 (sites, corrective-action links, as-built records) |"
   - Why: KLN owns BOM views and policy packages: KLN line 665 keys MBOM views by "(configuration point, `Site`), a policy-package record naming the plant and its ERP mapping", and ECO uses `Site` (ECO lines 494, 513, 1128). This tab's own rows put production sites, corrective-action links and as-built records in phase 3 (lines 924, 984, 986).
2. **[high] The gateway failure AGT returns has no `MfgError` variant.** `### Failures` (line 1040)
   - Now: "    DncSessionPreArmed  { machine: MachineSerial },"
   - Must say: the same line, followed by "    GatewayUnreachable  { machine: MachineSerial },"
   - Why: AGT's `read.machine_data` fails with `mfg/gateway_unreachable` (AGT lines 1181, 1269), and this tab owns the `mfg` family (line 1021: "Every `MfgError` variant renders as `mfg/<snake_case>`"). The gateway's other failures are already `MfgError` variants.
3. **[medium] State the `realize:` point the process hand-off chooses.** `### The model a user meets` (line 102)
   - Now: "Process profiles declare the representations their hand-off accepts."
   - Must say: "Process profiles declare the representations their hand-off accepts and the `realize:` point their exports use, `Mid` for machining by default, recorded in the export record."
   - Why: ING line 347 and MEC line 962 both say "MFG's process hand-off chooses the point, `Mid` for machining by default"; this tab never states it.
4. **[medium] Two links name headings that do not exist.** `### As-built struts for GP2` (line 677) and `## Quality records: SPC, MSA, FAI and PPAP` (line 916)
   - Now: "([COV, Validity envelopes as data](04-coverage.md#validity-envelopes-as-data))" → Must say: "([COV, Dynamics and stability](04-coverage.md#dynamics-and-stability))"
   - Now: "[KLN, Change control, signatures and compliance](05-kiln-repo-plm.md#change-control-signatures-and-compliance)" → Must say: "[KLN, Revisions and lifecycle states](05-kiln-repo-plm.md#revisions-and-lifecycle-states)"
   - Why: the strut-strength rule is D-COV-30 under COV `### Dynamics and stability` (COV line 339); `Proven` is a lifecycle state in KLN's `### Revisions and lifecycle states` table (KLN line 624).
5. **[medium] Interfaces rows give wrong phases or omit what others read.** `## Interfaces with other subsystems` (lines 1138, 1140, 1144, 1147, 1149)
   - Now: "| MEC | Process profiles (Cp, Cpk, accepted representations); DfAM, manufacturability and assembly checks; cost models | `Check`, `Field`, packages | 1 |" → Must say: "| MEC | Process profiles (Cp, Cpk, accepted representations); DfAM, manufacturability and assembly checks; cost models | `Check`, `Field`, packages | 1; 2 (Cp and Cpk, assembly checks) |". Line 922 declares Cp and Cpk in phase 2; design for assembly is phase 2 (line 875).
   - Now: "| MEC | Press-brake allowance data; the harness manufacturing package; in-process drawings | Packages, drawings | 2 |" → Must say: "| MEC | Press-brake allowance data; in-process drawings; the harness manufacturing package | Packages, drawings | 2; 4 (harness package) |". The "Harness manufacturing package" row is phase 4 (line 859).
   - Now: "| ELX | Rule packs by class; package choice; panels, stencils, test programs; fabrication feedback | `Check`, packages | 3 |" → Must say: "| ELX | Fabricator capability records (`fab::…`: laminates, via spans, spacing and HDI limits); rule packs by class; package choice; panels, stencils, test programs; fabrication feedback | `Check`, packages | 3 |". ELX reads them (ELX lines 399, 486, 562); line 842 makes them this tab's.
   - Now: "`request_quote` and `publish_passport` payloads; `MfgError` fixes | Act plans | 2 |" → Must say: "`request_quote` and `publish_passport` payloads; `MfgError` fixes | Act plans | 2; 3 (`publish_passport`) |". Passports are phase 3 (line 1011; AGT line 928).
   - Now: "| UIX | DfAM and carbon Fields, cost lines | `Field`, records | 1 |" → Must say: "| UIX | DfAM and carbon Fields, cost lines | `Field`, records | 1; 2 (carbon) |". Embodied carbon is phase 2 (line 1006).
6. **[low] The approval page and its outcomes are copied from contract 7.6.** `### What the person approving sees and can do` (lines 522 to 532)
   - Now: "MFG fills each physical-effect plan with the fields contract 7.6 requires of the approval page:" and the five bullets after it → Must say: "MFG fills each physical-effect plan with the fields contract 7.6 requires of the approval page, from the device serial to the steps the person at the device must take."
   - Now: the paragraph beginning "The approver has three outcomes (contract 7.6)." → Must say: "The approver has the three outcomes of [AGT, Three outcomes](09-agents.md#three-outcomes). A shop lead who returns a program because of a feed in workingstep 3 gets a corrected plan back the same hour; only resubmitting the identical digest is refused."
   - Why: contract 7.6 lists the page contents and the outcomes, and AGT owns the page (AGT line 969) and the outcome table (line 971). The copy also misstates "deny as suspicious": it blocks re-preparing a plan to the same recipients, not the recipients. Saves about 90 words.
7. **[low] The bench session is copied from contract 7.6.** `### Prove-out and the minimum ceremony` (line 544)
   - Now: the paragraph beginning "Repeated sends during prove-out use `bench_session` (contract 7.6), one AAL3 Approval for a run of transfers."
   - Must say: "Repeated sends during prove-out use `bench_session`, one AAL3 Approval over the machine, the gateway and one program Item lineage ([AGT, Physical effects](09-agents.md#physical-effects))."
   - Why: contract 7.6 ("Bench sessions") and AGT line 1024 state every clause.
8. **[low] Forming simulation is this tab's.** `## Sheet cutting, nesting and press brake` (line 403)
   - Now: "springback from measurement, and from Flux once sheet forming lands in phase 5 (contract 13.4)"
   - Must say: "springback from measurement, and from this tab's forming simulation once it lands in phase 5 (contract 13.4)"
   - Why: contract 13.4: "Sheet forming simulation and springback compensation | 5 | None | MFG"; this tab's rows 785 to 787 carry it.
9. **[low] Inherent strain requires FLX's sequence row.** `### Distortion and compensation` capability table (line 704)
   - Now: "Requires: FLX Element activation"
   - Must say: "Requires: FLX Additive distortion sequence"
   - Why: line 687 says "FLX owns inherent-strain prediction, phase 2 in contract 13.4, as a declared sequence"; the owner row is FLX's "Additive distortion sequence" (FLX line 849, phase 2). Element activation is one step of it.
10. **[low] Abbreviations used before they are spelled out.** `### The model a user meets` (line 102), `## Programs, regeneration and agents` (line 492), `## Factory connection and digital twin` (line 954)
    - Now: "which shops' CAM and CMM software read" → Must say: "which shops' CAM and coordinate measuring machine (CMM) software read"
    - Now: "adds geometry, GD&T and kinematics to the program" → Must say: "adds geometry, GD&T (geometric dimensioning and tolerancing) and kinematics to the program"
    - Now: "so this section connects machines, ERP and MES, and keeps per-serial records" → Must say: "so this section connects machines, enterprise resource planning (ERP) and manufacturing execution systems (MES), and keeps per-serial records"
    - Why: contract 11 spells out every abbreviation at first use in each tab.

## ELX

1. **[medium] Two links name headings that do not exist, and one copies KLN's report.** `### Choosing parts` (line 337) and `### Creating and migrating catalog parts` (line 358)
   - Now: "([KLN, BOM views and where-used](05-kiln-repo-plm.md#bom-views-and-where-used)). The report lists the Items and effectivity, alternates found by re-running each `CatalogSelection` without the part, and a last-time-buy quantity when ERP demand is available." → Must say: "([KLN, Where-used](05-kiln-repo-plm.md#where-used))."
   - Now: "([AGT, Quarantined extraction](09-agents.md#quarantined-extraction-and-external-hosts))" → Must say: "([AGT, Quarantined extraction](09-agents.md#quarantined-extraction))"
   - Why: the nightly obsolescence check and its report are D-KLN-55 under KLN `### Where-used` (KLN lines 667, 671); AGT's heading is `### Quarantined extraction` (AGT line 822).
2. **[medium] Three failure codes belong to other families.** `### Typed failures` (lines 1142, 1148, 1149) and the "Transient" row of `### Reliability prediction and derating` (line 737)
   - Now: "| `elx/net_merge` (`Conflict::NetMerge`) | A merge that unions nets distinct on both sides | Resolve the conflicting `connect`s on one branch |" → Must say: delete the row.
   - Now: "| `elx/step_too_small` | A transient that cannot advance | Check the device and nodes named |" → Must say: delete the row.
   - Now: "`StepTooSmall` with time, device and nodes" → Must say: "FLX's `StepTooSmall { t }`, with the device and nodes named"
   - Now: "| `elx/untranslated` | A Modelica construct outside the subset | Keep the FMU, or rewrite the construct |" → Must say: delete the row.
   - Why: `Conflict::NetMerge` is KLN's merge-driver enum (KLN lines 1166 to 1173, row line 500); `StepTooSmall { t }` is `flux::solve_dae`'s failure (FLX line 811), rendered `flux/step_too_small`; `Untranslated { construct }` is ECO's Modelica reader failure (ECO line 232). Contract 7.6 renders each typed Failure once, in its owner's family. Lines 156 and 195 already name `Conflict::NetMerge` correctly.
3. **[medium] The SysML v2 and ReqIF codecs are ECO's.** `### Crates, packages and WIT` (line 1087)
   - Now: "the Verilog-A front end, the SysML v2 and ReqIF codecs |"
   - Must say: "the Verilog-A front end |"
   - Why: ECO owns the translators (ECO lines 870, 954), and contract 12 puts translators in `io/`; this tab's ownership table gives "every `io/` reader and writer" to ECO (line 104).
4. **[low] Automatic test-point Proposals are MFG's test strategy.** `### Test points and the manufacturing handoff` (line 567)
   - Now: "adds probe access, and an automatic Proposal adds test points to nets without access."
   - Must say: "adds probe access, and MFG's test-access analysis proposes test points for nets without access."
   - Why: MFG owns test strategy (MFG line 842) and specifies the Proposal ("Test access and programs", MFG line 857, MFG-O-PCB-6).
5. **[medium] Rotor aerodynamics is FLX's, phase 4.** `### Sensors, drives and loads` (line 777)
   - Now: "The map comes from FLX and COV's rotor aerodynamics: blade-element momentum theory at L1, and rotating-domain flow at L3 in phase 4 ([COV, Aerospace](04-coverage.md#aerospace))."
   - Must say: "The map comes from FLX's rotor aerodynamics, phase 4 in contract 13.4: blade-element momentum theory at L1 up to rotating-domain flow at L3 ([FLX, Fluids and free surfaces](03-flux.md#fluids-and-free-surfaces))."
   - Why: contract 13.4 (ruling CCR-FLX-12): rotor aerodynamics, phase 4, owner FLX, also COV and ELX; FLX line 526 holds the ladder; the link pointed at COV's coverage matrix rather than the owner.
6. **[medium] The plane-pair cavity model is phase 4.** `### Power integrity` (line 615) and `## Phasing` (line 1314)
   - Now: "comes from Flux's plane-pair cavity model ([FLX, Electromagnetics](03-flux.md#electromagnetics))." → Must say: "comes from Flux's plane-pair cavity model, phase 4 in contract 13.4 ([FLX, Electromagnetics](03-flux.md#electromagnetics))."
   - Now: "conjugate heat transfer, Helmholtz solvers, electro-thermal coupling, RLCG and full-wave extraction, FMU export and SSP, and every battery cell row" → Must say: "conjugate heat transfer, Helmholtz solvers, electro-thermal coupling, RLCG and full-wave extraction, the plane-pair cavity model, rotor aerodynamics, FMU export and SSP, and every battery cell row"
   - Why: contract 13.4 lists ELX under "Also phased in" for both v7.1 rows; "every other tab states the phase in one line and cites this section".
7. **[low] The DFN pointer cites the wrong FLX section.** `### Cell models` (line 940)
   - Now: "DFN cells use Flux's parameter-domain forms ([FLX, Fields](03-flux.md#fields)), and pack-scale models"
   - Must say: "DFN cells use Flux's parameter-domain forms in phase 5 (contract 13.4; [FLX, One symbolic layer and compilation](03-flux.md#one-symbolic-layer-and-compilation)), and pack-scale models"
   - Why: parameter-domain forms are D-FLX-38 (FLX line 282) under `### One symbolic layer and compilation`; contract 13.4 puts DFN at phase 5.
8. **[low] The reason carries a list.** `### Analyses and their error budgets` (line 708)
   - Now: "`Undecided { reason: Unquantified(ModelForm) }`"
   - Must say: "`Undecided { reason: Unquantified([ModelForm]) }`"
   - Why: contract 5.6: "`Undecided { reason: Unquantified(sources) }`"; ING line 837 writes `Unquantified([ModelForm])`.
9. **[low] Flashing and bench sessions restate contract 7.6.** `### Flashing` (lines 901 and 905)
   - Now: the step beginning "4. **Clients.** Client flashing runs only in code that verifies the Approval." → Must say: "4. **Clients.** Client flashing runs only in code that verifies the Approval ([AGT, Physical effects](09-agents.md#physical-effects)); on a rig under `unattended_safe`, `run_rig_test` covers it."
   - Now: the paragraph beginning "A `bench_session` is one AAL3 Approval that covers a bench for at most 8 h (contract section 7.6)." → Must say: "A `bench_session` covers a bench under one AAL3 Approval ([AGT, Physical effects](09-agents.md#physical-effects)); for boards it names the probe, one Software item lineage and the board's hazard acknowledgements."
   - Why: contract 7.6 ("Firmware", "Bench sessions") and AGT lines 1024 and 1025 state every clause. Saves about 110 words.
10. **[medium] Rows that use FLX capabilities carry `Requires:` entries.** Capability tables (lines 649, 653, 656, 657, 968, 973, 1031). Append to the cell named:
    - Line 649, Contract cell ending "full-wave for unmodelled discontinuities": ". Requires: FLX Frequency-domain electromagnetics"
    - Line 653, Contract cell ending "plane-pair cavity model with capacitor, via and regulator elements": ". Requires: FLX Plane-pair cavity model"
    - Line 657, Contract cell ending "fitted to passive SPICE subcircuits used as Network elements": ". Requires: FLX RLCG extraction"
    - Line 968, Contract cell ending "to voltage, temperature and concentration Fields": ". Requires: FLX Parameter-domain spaces"
    - Line 973, Contract cell ending "DFN cells in pack thermal": ". Requires: FLX Parameter-domain spaces"
    - Line 1031, Contract cell ending "array factors over scan angle": ". Requires: FLX Periodic structures and arrays"
    - Line 656, Now: "| Monolithic Newton with continuation (FLX) |" → Must say: "| Copper self-heating on FLX's monolithic coupling. Requires: FLX Electro-thermal coupling |"
    - Why: contract 13.4: "A capability row that names another tab's capability carries a `Requires:` entry naming that row." Every target exists at the same or an earlier phase except "Electro-thermal coupling", which FLX's edit adds (see the rules on cross-tab `Requires:` entries).
11. **[low] Bare "component".** `### Drawing what the code connected` (line 254)
    - Now: "The component routes short connections as wires"
    - Must say: "`autodraw` routes short connections as wires"
    - Why: contract 2: a Wasm component is never a bare "component"; D-ELX-37 names it `schematic.autodraw`.
12. **[low] Abbreviations used before they are spelled out.** `### Choosing parts` (line 332) and `### Crates, packages and WIT` (line 1090)
    - Now: "the design, the ERP system and the assembly BOM disagree" → Must say: "the design, the enterprise resource planning (ERP) system and the assembly BOM disagree"
    - Now: "The WIT package `crucible:electronics` holds the worlds" → Must say: "The WIT (WebAssembly Interface Types) package `crucible:electronics` holds the worlds"
    - Why: contract 11.
13. **[low] Git stores the text.** D-ELX-27's *Why:* (line 229)
    - Now: "text-derived `CallSite`s and Git export"
    - Must say: "text-derived `CallSite`s and Git storage"
    - Why: contract 7.1 (v7.3, ruling FD-5).

## AGT

1. **[high] Budget exhaustion is KLN's `BudgetExhausted` Abort.** `### Budgets and admission` (line 268) and the "Admission and metering" row (line 335)
   - Now: "exhaustion aborts it at its last checkpoint." → Must say: "exhaustion is KLN's Abort `BudgetExhausted`, reported with the last safe point reached."
   - Now: "`budget/exceeded`; a budget Abort keeps the checkpoint" → Must say: "`budget/exceeded`; KLN's Abort `BudgetExhausted`"
   - Why: KLN owns work budgets (KLN line 227: "Exhausting it is the Abort `BudgetExhausted`, reported with the last safe point reached"), and contract 7.2 says no node that observed an Abort writes anything. "Checkpoint" now names only transparency-log heads (contract 7.1).
2. **[high] The widened bracket's figures.** `### Widening the bracket` (line 25)
   - Now: "74 MPa ± 7 MPa (`Estimated`) against a limit of 166 MPa"
   - Must say: "72 MPa ± 9 MPa (`Estimated`) against a limit of 144 MPa"
   - Why: 166 MPa is 0.6 × 276 MPa, the non-conservative end of COV's basis interval; COV line 15: the check "must hold at the interval's conservative end, here 144 MPa". The web-root bending stress scales with 1/width, so ING's `Interactive` 96 MPa ± 12 MPa at 60 mm (ING line 837) becomes 72 MPa ± 9 MPa at 80 mm.
3. **[high] Single-person mode covers merge approvals.** `### Human review and separation of duties` (line 584) and `### Independent verifier` (line 509)
   - Now: "each with a fresh approval credential bound to the call (contract 5.4)." → Must say: "each with a fresh approval credential bound to the call; in single-person mode the one person approves after an `Attested` verifier review, and the merge takes effect after contract 5.4's delay."
   - Now: "The review is `Attested` only under a different delegating human, in the hosted crew or behind the model gateway" → Must say: "The review is `Attested` only in the hosted crew or behind the model gateway, under a different delegating human except in single-person mode (contract 5.4)"
   - Why: contract 5.4 (ruling CCR-AGT-14): single-person mode "approves merges into a protected branch with a fresh approval credential after an `Attested` verifier review; the record takes effect after 72 h". As written, a one-person organization could never get an `Attested` review. See the contract items on the delay's scope and on attestation before phase 2.
4. **[medium] CCR-AGT-14 is accepted.** `## Contract change requests` (line 1385)
   - Now: the bullet beginning "- **CCR-AGT-14. Single-person merge approvals.**"
   - Must say: "None."
   - Why: contract 18 accepts it into 5.4.
5. **[high] Failure codes no owner defines.** `### Method catalog` (lines 1203, 1204) and `### Error families` (lines 1267, 1269)
   - Now: "`flux/study_invalid`; zones flag, never hide" → Must say: "`flux/study_error`; zones flag, never hide"
   - Now: "| `flux`, `cov` | FLX, COV | `study_invalid`, `symmetry_broken`; validity failures |" → Must say: "| `flux`, `cov` | FLX, COV | `study_error`, `symmetry_broken`; validity failures |"
   - Now: "| Setup → toolpaths, collisions, removal, cycle time | `mfg/setup_invalid` |" → Must say: "| Setup → toolpaths, collisions, removal, cycle time | `mfg/unreachable`, `mfg/infeasible`, `mfg/missing_data` |"
   - Now: "`mfg/gateway_unreachable`, `mfg/setup_invalid`, `mfg/dnc_session_pre_armed`" → Must say: "`mfg/gateway_unreachable`, `mfg/plan_unapproved`, `mfg/dnc_session_pre_armed`"
   - Why: FLX's study failure is `StudyError { missing, fix }` (FLX line 90), rendered `flux/<snake_case>` (line 1125). `MfgError` (MFG lines 1024 to 1041) has `Unreachable`, `Infeasible`, `MissingData` and `PlanUnapproved` but no `SetupInvalid`; MFG adds `GatewayUnreachable` (MFG 2). The `ui` family for UIX stays as registered; UIX follows it.
6. **[medium] Register KLN's other families.** `### Error families` (line 1268)
   - Now: "| `kiln`, `repo`, `plm`, `trust` | KLN |"
   - Must say: "| `kiln`, `cas`, `repo`, `plm`, `trust`, `evidence`, `share` | KLN |"
   - Why: contract 7.6: AGT keeps the registry. KLN declares `cas`, `evidence` and `share` "registered with AGT" (KLN line 126) and raises `cas/corrupt`, `evidence/calibration_expired` and `share/quota_exceeded` (KLN lines 389, 806, 990).
7. **[medium] `self_approve_transfer` is enabled by a widening Cedar change.** `### Physical effects` (line 1026)
   - Now: "off by default and enabled by the site's safety officer, lets the person who prepared a transfer approve it with AAL3"
   - Must say: "off by default and enabled by a widening Cedar change that names the site's safety officer, lets the person who prepared a transfer approve it with AAL3"
   - Why: MFG owns the policy: MFG line 546, "enabling it is a widening Cedar change signed under contract 5.4, and the record names the site's safety officer"; contract 5.4 gives a widening Cedar change to two people.
8. **[medium] The export Act carries outside web-view links.** `### Act kinds` (line 924)
   - Now: "| `export` | Data release | A repository archive or release bundle; a Git mirror, a branch shared with another organization or a message to a connector | Irreversible; sharing revocable going forward | 1 (archive, bundle), 2 (others) |"
   - Must say: "| `export` | Data release | A repository archive, release bundle or web-view link; a Git mirror, a branch shared with another organization or a message to a connector | Irreversible; sharing revocable going forward | 1 (archive, bundle, web-view link), 2 (others) |"
   - Why: UIX's phase 1 shareable web views (parity floor, contract 13.4) create outside links "by a `release_data` Act naming the recipients" (D-UIX-38, UIX lines 354, 387); D-AGT-36 makes sharing with another organization an `export` Act, but its effects and phase omit web views.
9. **[medium] Interfaces rows give wrong phases.** `## Interfaces with other subsystems` (lines 1323, 1327, 1328)
   - Now: "| `Budget`, `PriorityClass`, `Proposal` | 1 |" → Must say: "| `Budget`, `PriorityClass`, `Proposal` | 0 (`PriorityClass`); 1 |". KLN uses `PriorityClass` in phase 0 (KLN lines 231, 1401).
   - Now: "`bench_session`; `read.machine_data`; the CAM programmer | `ActPlan` | 2 |" → Must say: "`bench_session`; `read.machine_data`; the CAM programmer | `ActPlan` | 2; 3 (`publish_passport`, `store_machine_job`) |". This tab's Act table (lines 928, 934).
   - Now: "datasheet extraction, labelled `data_untrusted`; budget caps for long tool runs | API method, `Proposal` | 1 |" → Must say: "datasheet extraction, labelled `data_untrusted`; budget caps for long tool runs | API method, `Proposal` | 1; 2 (extraction) |". Quarantined extraction is phase 2 (lines 824, 852).
10. **[low] The OPC UA allowlist is MFG's.** `### Physical effects` (line 1023)
    - Now: "- **OPC UA.** Crucible calls `Store` only in `store_machine_job`, and `Cancel`, `Clear` and `RevokeStart` only on its own unstarted jobs; every other job-control method is uncallable [OPC 10031-4]."
    - Must say: "- **OPC UA.** `store_machine_job` calls only the job methods MFG allows ([MFG, Acts, payloads and wire-level rules](07-manufacturing.md#acts-payloads-and-wire-level-rules))."
    - Why: MFG owns the gateway's wire rules (MFG line 584, MFG-O-SAFE-3). Drop the `[OPC 10031-4]` Sources row if nothing else cites it.
11. **[low] Abbreviations used before they are spelled out.** `### One catalog` (line 80) and `### Role catalog` (line 486)
    - Now: "MCP tools, SDK methods, WIT functions, UI commands" → Must say: "MCP tools, SDK methods, WIT (WebAssembly Interface Types) functions, UI commands"
    - Now: "| Drawing and MBD author |" → Must say: "| Drawing and model-based definition author |"
    - Why: contract 11.

## UIX

1. **[high] Transients animate from phase 2.** `### What the studio makes` (line 283) and the capability row (line 383)
   - Now: "| Field and deformed-shape animation | Deformation under load, mode shapes and transients, scaled and labelled | 1 |" → Must say: "| Field and deformed-shape animation | Deformation under load and mode shapes, scaled and labelled; transients from phase 2 | 1 |"
   - Now: "| Deformation, mode shapes and transients with stated scale | Frame cache evicted: recomputed with progress | UIX-O-ANIM-1 | 1 |" → Must say: "| Deformation, mode shapes and transients with stated scale | Frame cache evicted: recomputed with progress. Requires: FLX Mode shapes | UIX-O-ANIM-1 | 1; 2 (transients) |"
   - Why: FLX's time integrators are phase 2 (FLX line 676); this tab's Field views phase transients at 2 (line 786). FLX's "Mode shapes" row is phase 1.
2. **[high] `store_machine_job` is phase 3.** `### Phones, devices and exports` capability table (line 271)
   - Now: "Printer code missing, wrong or stale: no start; main-origin flash attempt: refused | UIX-O-APPR-1 | 2; 3 (`flash_device`) |"
   - Must say: "Printer code missing, wrong or stale: no start; main-origin flash attempt: refused. Requires: AGT Physical-effect Acts | UIX-O-APPR-1 | 2; 3 (`store_machine_job`, `flash_device`) |"
   - Why: AGT's Act table: `store_machine_job` phase 3 (AGT line 934).
3. **[high] The drag oracle uses PLT's statistic.** `## Oracles`, UIX-O-DRAG-1 (line 1270) and UIX-O-PERF-1 (line 1264)
   - Now: "Late- and early-edit scripts meet contract 13.3's drag row at p95" → Must say: "Late- and early-edit scripts meet contract 13.3's drag row at p90"
   - Now: "Benchmark and held-out scenes meet contract 13.3's rows and this tab's budgets at p95" → Must say: "Benchmark and held-out scenes meet contract 13.3's rows at PLT's statistic per row and this tab's budgets at p95"
   - Why: PLT owns 13.3's benchmark files and percentiles (contract 13.3): "Drag preview | … | Warm; p90" (PLT line 1146), selection and input to photon at p99 (PLT lines 1139, 1153).
4. **[high] Label-aware egress includes `controls`.** D-UIX-28 (line 992), the "Label-aware egress" row (line 1028) and UIX-O-PRIV-2 (line 1294)
   - Now: "**Decision D-UIX-28:** Above `internal`, nothing the UI sends outside the organization carries content" → Must say: "**Decision D-UIX-28:** Above `internal` or with any `controls`, nothing the UI sends outside the organization carries content"
   - Now: "| Nothing with content leaves above `internal` |" → Must say: "| Nothing with content leaves above `internal` or with `controls` |"
   - Now: "Above `internal`, notifications, push, crash uploads and bundles hold no content" → Must say: "Above `internal` or with `controls`, notifications, push, crash uploads and bundles hold no content"
   - Why: PLT owns egress (contract 7.8); D-PLT-38 (PLT line 830): "Content labelled above `internal` or with non-empty `controls` follows one egress rule".
5. **[medium] Locks fail with KLN's `repo/lock_held`.** `## Collaboration` capability table (line 892) and UIX-O-OFFLINE-1 (line 1297)
   - Now: "Agent edit to a locked block: `LockHeld` on the timeline" → Must say: "Agent edit to a locked block: `repo/lock_held` on the timeline. Requires: KLN Live sessions"
   - Now: "an agent edit to a locked block shows `LockHeld`" → Must say: "an agent edit to a locked block shows `repo/lock_held`"
   - Why: KLN line 553: "Presence and locks | … | `repo/lock_held`".
6. **[medium] The lint family is AGT's registered `ui`.** `### Presentation files` (line 302) and the "Readouts" row (line 379)
   - Now: "raises the lint `uix/literal_number_in_caption`" → Must say: "raises the lint `ui/literal_number_in_caption`"
   - Now: "Typed number in a caption: `uix/literal_number_in_caption`" → Must say: "Typed number in a caption: `ui/literal_number_in_caption`"
   - Why: contract 7.6: AGT keeps the family registry, and AGT registers `ui` for UIX (AGT line 1269).
7. **[medium] The bracket's readout uses ING's figures.** `### Studies and results` (line 812)
   - Now: "margin 17% at the bound (`Estimated`, ±1.5 MPa)"
   - Must say: "94 MPa ± 1.5 MPa (`Estimated`) against 144 MPa"
   - Why: ING owns the walk-through: "`SignOff`, 6 mm: 94 MPa ± 1.5 MPa" (ING line 838) against the 144 MPa limit (COV line 15). 17% matches neither.
8. **[medium] Exploded views require MEC's steps, and `explode_auto` is phase 3.** `### Rendered images and the audit` capability table (line 382)
   - Now: "| MEC's explode steps with trail lines and eased motion | Step unresolved after a rebuild: `explode_auto` steps offered |"
   - Must say: "| MEC's explode steps with trail lines and eased motion | Step unresolved after a rebuild: the step is named with its `ResolveError`; `explode_auto` proposals from phase 3. Requires: MEC Exploded views |"
   - Why: MEC's "Exploded views" row phases automatic proposals at 3 (MEC line 646). MEC moves ordered steps to phase 1 in its edit, which this entry then guards (see the rules on cross-tab `Requires:` entries).
9. **[medium] Native accessibility adapters are phase 0 on Windows only.** `### Text and accessibility` capability table (line 579)
   - Now: "A widget without name or role fails the build | UIX-O-A11Y-1 | 0; 1 (web) |"
   - Must say: "A widget without name or role fails the build. Requires: PLT Accessibility | UIX-O-A11Y-1 | 0 (Windows); 1 (other desktops, web) |"
   - Why: PLT's "Accessibility" row: "0 (Windows), 1 (desktop, web), 3 (tablets)" (PLT line 501).
10. **[medium] Reports render HTML through the headless renderer.** `### Presentation files` (line 304)
    - Now: "Reports render through MEC's drawing and document pipeline to PDF/A-2u, the archival profile MEC uses for release drawings, and to HTML ([MEC, Drawings](06-mechanical.md#drawings))."
    - Must say: "Reports render to PDF/A-2u through MEC's drawing pipeline, the archival profile MEC uses for release drawings ([MEC, Drawings](06-mechanical.md#drawings)), and to HTML through `apps/headless-render`."
    - Why: MEC's sheets output "PDF, SVG and PDF/A-2u" (MEC line 1126) and offers no HTML document pipeline; reports are this tab's parity-floor row (contract 13.4).
11. **[medium] Interfaces rows to ECO and PLT.** `## Interfaces with other subsystems` (lines 1235, 1236)
    - Now: "scene cameras for glTF and OpenUSD export | WIT `crucible:ui`, `ViewState` | 1; 2 (glTF); 3 (OpenUSD) |" → Must say: "scene cameras for glTF and OpenUSD export | WIT `crucible:ui`, `ViewState` | 1 (schemas, package pages, grants); 2 (marketplace, glTF); 3 (`crucible:ui` worlds, panel chrome, OpenUSD) |". This tab's rows 1034 and 1035 are phase 3; marketplace listings open in phase 2 (line 32; ECO line 655).
    - Now: "| PLT | The AccessKit tree; device-loss and safe-mode behaviour; benchmark rows; telemetry fields; the copy budget; render-quality levels; the web-view viewer build | `ViewState` | 0 |" → Must say: "| PLT | The AccessKit tree; device-loss recovery and the G3 path for safe mode; frame budgets and capacity per tier; telemetry fields; the display-data copy budget; the web-view viewer build | `ViewState` | 0; 1 (web-view viewer); 2 (telemetry) |". "Copy budget" and "render-quality levels" are defined nowhere; this tab's terms are at lines 603 and 717 and D-UIX-22.
12. **[medium] Five links name headings that do not exist.** `### The approval page` (line 242), `### Exploded views and motion` (line 324), `### Assemblies` (line 480), `## Field views` (line 768), `## Collaboration` (line 883)
    - Now: "([KLN, Change orders](05-kiln-repo-plm.md#change-orders))" → Must say: "([KLN, Review routes and delegation](05-kiln-repo-plm.md#review-routes-and-delegation))"
    - Now: "([MEC, Exploded views](06-mechanical.md#exploded-views-subassemblies-and-interfaces))" → Must say: "([MEC, Designing across parts](06-mechanical.md#designing-across-parts))"
    - Now: "([MEC, Exploded views, subassemblies and interfaces](06-mechanical.md#exploded-views-subassemblies-and-interfaces))" → Must say: "([MEC, Designing across parts](06-mechanical.md#designing-across-parts))"
    - Now: "([FLX, Post-processing and display](03-flux.md#post-processing-and-display))" → Must say: "([FLX, Display](03-flux.md#display))"
    - Now: "([KLN, Live documents](05-kiln-repo-plm.md#live-documents))" → Must say: "([KLN, Live sessions](05-kiln-repo-plm.md#live-sessions))"
    - Why: KLN's headings are `### Review routes and delegation` (line 715) and `### Live sessions` (line 508); `explode` and context pins are under MEC `### Designing across parts` (MEC lines 549 to 573); FLX's evaluators are under `### Display` (FLX line 1026). The broken link at line 239 goes with UIX 18.
13. **[medium] Rows that use other tabs' capabilities carry `Requires:` entries.** Append ". Requires: <entry>" to the Failure cell of each row (every target exists at the same or an earlier phase):

    | Line | Row | Entry |
    | --- | --- | --- |
    | 143 | Item place | KLN Items, numbering and labels |
    | 218 | Electronics review diffs | ELX Electronics review diffs |
    | 223 | Find similar | KLN Classification and shape-similarity search |
    | 269 | Review-route progress | KLN Review routes and delegation |
    | 384 | Animation of moving parts | MEC Kinematics and motion studies |
    | 388 | Reports | FLX Reports; MEC Sheets, title blocks and standards |
    | 515 | Feature dialogs | ING Dialogs from signatures |
    | 517 | Drag preview | AGT Drag streams |
    | 520 | Push-pull | ANV `anvil::offset_faces` |
    | 521 | Insert Instance and Add mate | MEC Mate solve and diagnosis |
    | 523 | Edit in context | MEC In-context design |
    | 524 | Sketching and inference | MEC Sketch edits |
    | 525 | Reference images | MEC Reference images |
    | 527 | Family table editor | MEC Configurations and families |
    | 529 | Code panel | ING Language service |
    | 726 | Virtualized geometry | ANV `anvil::cluster_dag` |
    | 727 | GPU device loss | PLT GPU device loss |
    | 736 | Implicit display | ANV WGSL tape interpreter |
    | 795 | Field colour, isolines and probes | FLX Display evaluators |
    | 797 | Discretization view | FLX Discretization Fields |
    | 852 | Study setup | FLX Remote points |
    | 854 | Submodel template | FLX Submodeling |
    | 856 | DfAM and build preview | MFG DfAM checks |
    | 857 | Cost panel | MFG Parametric cost |
    | 859 | Toolpath edit selection | MFG Toolpath editing |
    | 860 | NC code panel | MFG Semantic NC diff and block map |
    | 861 | Setup-sheet preview | MFG Setup sheet |
    | 862 | EBOM and MBOM editor | MFG MBOM and routings |
    | 864 | Automatic drawings and revision markers | MEC Revision markers |
    | 866 | Schematic, layout and constraint-manager canvases | ELX Interactive routing |
    | 889 | Presence and follow mode | KLN Presence and locks |
    | 893 | Offline and rejoin | KLN Offline rejoin |
    | 949 | 3D mice | PLT 6-DoF devices |
    | 1029 | Telemetry | PLT Telemetry pipeline |

    - Why: contract 13.4: "A capability row that names another tab's capability carries a `Requires:` entry naming that row." This tab has none. Rows 271, 382, 383, 579 and 892 get theirs in the edits above.
14. **[low] The Item place shows quality records from phase 3.** `### Places and the workspace` (line 31)
    - Now: "change orders and their review routes, compliance, cost, similar Items |"
    - Must say: "change orders and their review routes, compliance, cost, similar Items; quality records from phase 3 |"
    - Why: KLN provides "quality-record and route views" to this tab (KLN line 1313); its "Quality records" row is phase 3 (KLN line 779).
15. **[low] The drag lane is PLT's.** `### Drag preview` (line 455)
    - Now: "| Preview | While dragging, on Kiln's drag lane |"
    - Must say: "| Preview | While dragging, on PLT's `Drag` lane |"
    - Why: contract 12: `PoolLane { Drag, Foreground, Background }` is PLT's; line 460 of this tab already says so.
16. **[low] A conventions table that does not exist.** `## Platform notes` (line 1219)
    - Now: "native dialogs differ by OS, listed in one conventions table owned with PLT"
    - Must say: "native dialogs differ by OS"
    - Why: neither PLT nor this tab has such a table, and PLT's Interfaces row to UIX offers none.
17. **[low] Abbreviations used before they are spelled out.** `### Approvals` (line 234) and `### Extending the interface` (line 1014)
    - Now: "an in-app webview or an MCP host's viewer" → Must say: "an in-app webview or the viewer of an MCP (Model Context Protocol) host"
    - Now: "Code-driven views are Wasm components in the `crucible:ui` WIT package" → Must say: "Code-driven views are Wasm components in the `crucible:ui` WIT (WebAssembly Interface Types) package"
    - Why: contract 11.
18. **[low] The approval sections copy AGT, KLN, PLT and contract 7.6.** `### The approval page` (lines 238 to 246), `### Credentials` (lines 250, 252), `### Phones, devices and exports` (lines 256, 258, 260)
    - Now: the bullet beginning "- **Isolation.** The page renders only server-generated text under a strict content security policy" → Must say: "- **Origin.** The page lives on AGT's approval origin ([AGT, Plans and the approval page](09-agents.md#plans-and-the-approval-page)), opened through PLT's browser session."
    - Now: the bullet beginning "- **Challenges.** Each WebAuthn challenge follows KLN's one definition" → Must say: delete the bullet.
    - Now: the bullet beginning "- **Clients.** The web client opens the page as a top-level page." → Must say: delete the bullet.
    - Now: the paragraph beginning "The page offers three outcomes. **Approve** signs." → Must say: "The page offers contract 7.6's three outcomes ([AGT, Three outcomes](09-agents.md#three-outcomes))."
    - Now: the paragraph beginning "Delivery follows contract 7.6: only Cedar-assigned approvers' inboxes" → Must say: delete the paragraph.
    - Now: the paragraph beginning "Only a device-bound credential enrolled for approval approves." → Must say: "Approval credentials are device-bound and never synced (contract 7.6)."
    - Now: "The person's existing approval credential approves it; a first credential needs an `admin` plus a recorded identity check and takes effect after 24 h." → Must say: delete the sentence.
    - Now: "In a phone browser on the approval origin, a person may approve release and change-notice Acts that carry no `controls` and no physical effect, with an allowlisted security key over NFC or USB. Physical-effect Acts, `controls` payloads and Part 11 signatures never appear as approvable on a phone." → Must say: "Which Acts a phone browser may approve is contract 7.6's rule; the others show read-only with the reason."
    - Now: "The Manufacture preset offers the transfer Acts (`send_to_machine`, `send_robot_program`, `store_machine_job`, `send_print_job`) and," → Must say: "The Manufacture preset offers contract 7.6's transfer Acts and,"
    - Now: the three sentences from "In a browser, the flash runs on the approval page after the ceremony." to "before any byte reaches the probe." → Must say: "It flashes only from code that verifies the Approval ([AGT, Physical effects](09-agents.md#physical-effects))."
    - Why: AGT owns the approval origin and page (contract 7.6; AGT lines 963 to 987), KLN the challenge (D-KLN-58), PLT the client session (D-PLT-41), and contract 7.6 the outcomes, delivery, credentials, phones, the physical-effect list ("This is the only list") and client flashing. The cut also removes the broken `#electronic-signatures` link and "PLT's flashing service", which contract 7.6 places in `apps/platform-*` as ELX's service. Saves about 330 words in the tab closest to its ceiling.

## ECO

1. **[high] Import matching and the exchange form use ANV's names and rows.** `### Untrusted content in imported files` capability table (lines 147, 149)
   - Now: "| Persistent ids or exact signatures; re-imports matched into a reviewed `import_map` (ANV) |" → Must say: "| Persistent ids or exact signatures; re-imports matched into a reviewed `import_map`. Requires: ANV Imported entity ids; ANV `anvil::match_bodies` |"
   - Now: "`NotRepresentable { faces }` (ANV). Requires: ANV `anvil::exchange_form`" → Must say: "`NotRepresentable { entities, reason }` (ANV). Requires: ANV `anvil::exchange_form`"
   - Why: ANV's rows "Imported entity ids" (ANV line 415, phase 1) and "`anvil::match_bodies`" (line 416, phase 1 for the same site) own matching; `anvil::exchange_form` fails with `NotRepresentable { entities, reason }` (ANV line 989), as this tab's own line 148 already writes.
2. **[high] Deprecation is a mode of `yank_package`.** `### Scanning, advisories and removal` (line 616)
   - Now: "| Deprecate | A notice and an optional successor | Publisher, as a publish Act |"
   - Must say: "| Deprecate | A notice and an optional successor | Publisher, as a `yank_package` Act in its deprecation mode |"
   - Why: D-AGT-36 (AGT line 937): "deprecation is a mode of `yank_package`"; AGT line 922: `yank_package` marks a version "yanked or deprecated".
3. **[high] Archive import keeps span integrity only through a witnessing server.** `### Where tenant bytes leave` (line 480)
   - Now: "On import, spans keep their integrity only if a device key of a principal in this organization signed the Change (KLN)."
   - Must say: "On import, spans keep their integrity only when the server that witnessed each write signed its span-integrity record and this organization trusts that server (KLN)."
   - Why: KLN owns span provenance (contract 7.1); KLN line 429: spans from archive import "keep their integrity only when the witnessing server signed their span-integrity record and the receiving domain trusts that server". AGT's `edit.import_archive` (AGT line 1198) agrees.
4. **[high] The install-time determinizer re-run is phase 1.** `### Versioning` capability table (line 420) and `## Phasing` (line 1187)
   - Now: "| Limit `Failure`s cached; a hash mismatch refuses the component | ECO-O-6, ECO-O-7 | 0 |" → Must say: "| Limit `Failure`s cached; a hash mismatch refuses the component | ECO-O-6, ECO-O-7 | 0; 1 (install-time re-run) |"
   - Now: "ECO-O-6 and ECO-O-7 green in the determinism suite" → Must say: "ECO-O-6 and ECO-O-7's publish-time and build-time cases green in the determinism suite"
   - Why: PLT's "Install-time determinizer check" row is phase 1 (PLT line 414).
5. **[medium] The browser sandbox is PLT's.** D-ECO-10 (lines 344 to 346)
   - Now: "until the asynchronous bridge passes PLT-O-WASM-1 there (contract section 7.4)." → Must say: "until the asynchronous bridge passes PLT-O-WASM-1, PLT-O-WASM-6 and PLT-O-WASM-7 there ([PLT, Isolation of third-party Wasm components](12-platform-performance.md#isolation-of-third-party-wasm-components))."
   - Now: the sentences from "Then each runs in a dedicated worker started by an" to "An engine evaluates third-party components locally only after ECO-O-8's exfiltration cases pass in it." → Must say: "Then each runs in PLT's browser sandbox, and only after ECO-O-8's exfiltration cases pass in that engine."
   - Now (*Why:*): "The sandbox drops storage and credentials, and `default-src 'none'` blocks `fetch` and WebSocket [MDN default-src]. The content security policy's fetch directives do not govern WebRTC, which has its own directive with the values `'allow'` and `'block'` [CSP3], and a worker exposes no `RTCPeerConnection` [unverified per engine]." → Must say: delete these sentences, keeping "generated glue would run beside every local repository and key."
   - Now (*Rejected:*): "; an opaque-origin worker without a network policy; trusting `default-src` alone, which leaves a WebRTC channel to an attacker's STUN or TURN server" → Must say: delete it, so the line ends at "Pulley compiled to Wasm."
   - Why: PLT owns the browser runtime and sandbox (contract 7.4); D-PLT-42 (PLT line 378) specifies the same iframe, sandbox site, policy string, COEP and CORP, names the three oracles, and argues the WebRTC point (PLT line 379). This decision keeps its own part: descriptions, never per-component JavaScript. Drop `[MDN default-src]` and `[CSP3]` from Sources if nothing else cites them.
6. **[medium] `ProgramUnverified` exists nowhere.** `### Reconstruction and tooling` capability table (line 861)
   - Now: "`ProgramUnverified` blocks any transfer Act (MFG)"
   - Must say: "No transfer until the program Item's subject is approved, else MFG's `PlanUnapproved`. Requires: MFG External NC verification"
   - Why: MFG line 451: legacy programs "release as program Items on the same approval path"; the transfer refusal is `PlanUnapproved` (MFG line 1037). MFG's "External NC verification" row is phase 2 (MFG line 459).
7. **[medium] Add the quality connector KLN relies on.** `### WIT package index` (line 989) and `### ECO's WIT packages` (line 998)
   - Now: "`partner`, `erp`, `mes`, `plm`; worlds `partner-connector`, `erp-connector`, `mes-connector`, `plm-connector`" → Must say: "`partner`, `erp`, `mes`, `plm`, `quality`; worlds `partner-connector`, `erp-connector`, `mes-connector`, `plm-connector`, `quality-connector`"
   - Now: "`erp`, `mes`, `plm` (mapped records) | `partner-error`, `mapping-conflict` | 2 |" → Must say: "`erp`, `mes`, `plm` (mapped records); `quality` (KLN's quality records) | `partner-error`, `mapping-conflict` | 2; 3 (`quality`) |"
   - Why: D-KLN-52 (KLN line 768): an organization with an external quality system "connects it through ECO's quality connector world instead"; KLN's row to ECO lists "the quality connector world's records" (KLN line 1312); contract 13.4's phase 3 parity row offers "a named connector to an external quality system".
8. **[medium] A link names a heading that does not exist.** `### Exports the receiver can use` (line 127)
   - Now: "([KLN, Data leaving a tenant](05-kiln-repo-plm.md#data-leaving-a-tenant))"
   - Must say: "([KLN, Exits](05-kiln-repo-plm.md#exits))"
   - Why: the watermark and release-data record paragraph is KLN line 973, under `### Exits` (line 961).
9. **[medium] Rows that use other tabs' capabilities carry `Requires:` entries.** Capability tables (lines 225, 231, 860). Append to the Failure cell:
   - Line 225, "Unmatched labels reported": ". Requires: MFG Results as Evidence records"
   - Line 231, "`UnmappedCard { card, line }` | ECO-O-37": insert ". Requires: FLX Imported solver decks; FLX Solver deck export" after `UnmappedCard { card, line }`
   - Line 860, "`UnresolvedReference { file }`": ". Requires: KLN Foreign native CAD files"
   - Why: contract 13.4's `Requires:` rule; the targets are MFG phase 1, FLX phase 3 and KLN phase 3, none later than these rows.
10. **[medium] Interfaces rows omit what ING and MEC use.** `## Interfaces with other subsystems` (lines 1127, 1131)
    - Now: "receiver profiles for `export_resolution` | `Imported`; `File`; Package | 1, 2 (DWG), 5 (GDSII) |" → Must say: "receiver profiles for `export_resolution`; IDF and STEP board readers; IFC 4.3 | `Imported`; `File`; Package | 1, 2 (DWG, boards), 5 (GDSII, IFC) |". MEC reads boards in phase 2 (MEC line 547; this tab's row 229) and round-trips IFC 4.3 in phase 5 (MEC line 880).
    - Now: "| ING | Registry and signing; interface diffs; determinized components; the RFC process |" → Must say: "| ING | Registry and signing; interface diffs; determinized components; the RFC process; PubGrub resolution with typed explanations |". ING line 1019: "Resolution uses PubGrub … through ECO's resolver"; this tab's "Resolution and lockfile" row is phase 0 (line 643).
11. **[low] `crucible:host` includes `chunk-worker`, which PLT specifies.** `### WIT package index` (line 982)
    - Now: "| `crucible:host` | `diagnostics`, `progress` (write-only), `cas` (handle reads), `parallel` | KLN; PLT implements `parallel` |"
    - Must say: "| `crucible:host` | `diagnostics`, `progress` (write-only), `cas` (handle reads), `parallel`, `chunk-worker` | KLN; PLT specifies and implements `parallel` and `chunk-worker` |"
    - Why: KLN line 173 ("`parallel` with `chunk-worker`"); PLT line 1105 ("PLT specifies and implements its `parallel` and `chunk-worker` interfaces").
12. **[low] Agents read events through AGT's methods.** `### Events and webhooks` (line 468)
    - Now: "Agents receive the same events as MCP (Model Context Protocol) resource subscriptions (AGT)."
    - Must say: "Agents read events through `read.events` and MCP (Model Context Protocol) resource subscriptions to branch heads, Proposals and Evaluations (AGT)."
    - Why: AGT's subscriptions cover "Branch-head, Proposal and Evaluation resources" (AGT line 1238), and `read.events` reads the feed (line 1179).
13. **[low] PLT has no "translator host" component.** `### Where translators run` (line 67)
    - Now: "An external tool on the vendor SDK, in PLT's translator host"
    - Must say: "An external tool on the vendor SDK, in a translator host under PLT's sandbox"
    - Why: PLT sandboxes translator hosts (D-PLT-43, PLT line 384) but designs no host; this tab specifies its signing (line 74).
14. **[low] The product-liability assessment is a phase 1 gate item.** D-ECO-42 (line 739)
    - Now: "**Decision D-ECO-42:** Before phase 1 general availability, counsel assesses"
    - Must say: "**Decision D-ECO-42:** Before phase 1 general availability, as the phase 1 gate requires (contract 13.1), counsel assesses"
    - Why: contract 13.1 now carries the assessment (ruling CCR-ECO-13); cite the section, not the request.
15. **[medium] CCR-ECO-13 is accepted.** `## Contract change requests` (line 1202)
    - Now: the bullet beginning "- **CCR-ECO-13, product-liability assessment at the phase 1 gate.**"
    - Must say: "None."
    - Why: contract 18 adds the item to 13.1's phase 1 gate.
16. **[low] FMU spelled out.** `### Untrusted content in imported files` (line 137)
    - Now: "Archives (3MF, USDZ, FMU packaged simulation models"
    - Must say: "Archives (3MF, USDZ, Functional Mock-up Unit (FMU) packaged simulation models"
    - Why: contract 11.
17. **[medium] Every Change is already a commit.** `### Where tenant bytes leave` (line 478)
    - Now: "- **Git mirror** (phase 2): Ingot sources, manifests and lockfiles, one Git commit per selected Change."
    - Must say: "- **Git mirror** (phase 2): a push of selected branches, with their commits, to another party's Git host."
    - Why: contract 7.1 (v7.2 and v7.3, ruling FD-5): each Change is a commit and any Git host can be home, so a mirror to another party is a push, still a `release_data` exit.

## PLT

1. **[medium] `AccessibilityHost` is named but never defined.** `### OS services` (line 452)
   - Now: "`SystemSignals`, `WallClock`, `Monotonic`, `Spawner`, `SharedRing`, `DeviceIo`, `CryptoProvider` and `Authenticator` (signatures in Reference)"
   - Must say: "`SystemSignals`, `WallClock`, `Monotonic`, `Spawner`, `SharedRing`, `DeviceIo`, `CryptoProvider`, `AccessibilityHost` and `Authenticator` (signatures in Reference)"
   - Why: this tab's Interfaces row gives UIX `AccessibilityHost` (line 1214); nothing else defines it. Add its signature to the Reference with the others.
2. **[medium] Specify the webhook egress proxy ECO relies on.** `## Telemetry and label-aware egress` capability table (line 847) and `## Interfaces with other subsystems` (line 1216)
   - Now: "| Egress allowlist | Policy-listed hosts only | Blocked host logged locally | PLT-O-PRIV-2 | 2 |" → Must say: "| Egress allowlist and webhook proxy | Policy-listed hosts only; webhook deliveries through a proxy that checks each resolved address against ECO's address rules at connect time | Blocked host or refused address logged | PLT-O-PRIV-2, ECO-O-14 | 1 (webhook proxy), 2 |"
   - Now: "TUF and signature formats, release lines and support periods | `WasmComponentEngine`, `CallLimits` | 0 |" → Must say: "TUF and signature formats, release lines and support periods, the webhook egress proxy | `WasmComponentEngine`, `CallLimits` | 0; 1 (install-time re-runs, browser runtime, webhook proxy); 2 (sandbox site, `crucible:tool/process`, LTS lines); 3 (offline bundles, local External Op sandboxes) |"
   - Why: ECO line 466: "Deliveries leave through PLT's egress proxy, which checks each resolved address at connect time against ECO's webhook rules", in phase 1 (ECO line 510); contract 7.8 makes PLT the egress enforcer. This tab's own rows give the phases (lines 414, 421, 423, 425, 430, 776, 931).
3. **[low] The Interfaces row to UIX puts every item at phase 0.** `## Interfaces with other subsystems` (line 1214)
   - Now: "renderer image, native-code register | `WindowHost`, `AccessibilityHost`, `SharedRing`, `Authenticator` | 0 |"
   - Must say: "renderer image, native-code register | `WindowHost`, `AccessibilityHost`, `SharedRing`, `Authenticator` | 0; 1 (shared rings, approval session, device loss, safe mode); 2 (telemetry) |"
   - Why: this tab's rows: shared display rings 1 (line 243), WebAuthn 1 (line 510), device loss 1 (line 821), safe mode 1 (line 823), telemetry pipeline 2 (line 846).
4. **[medium] ELX's flashing service lives in `apps/platform-*`.** `### Crates` (line 987) and `## Interfaces with other subsystems` (line 1219)
   - Now: "| The only crates that bind OS APIs; `platform-web` holds the browser `WasmComponentEngine` and WebCrypto | Allowed |" → Must say: "| The only crates that bind OS APIs; `platform-web` holds the browser `WasmComponentEngine` and WebCrypto; ELX's flashing service and bench adapters live here | Allowed |"
   - Now: "| ELX | `detmath`, the `Drag` lane, the browser memory table, serial and USB access, local External Op sandboxes for vendor models, registry font packages (FLX owns circuit LU) | `DeviceIo` | 1 |" → Must say: "| ELX | `detmath`, the `Drag` lane, the browser memory table, serial and USB access, hosting of ELX's flashing service and bench adapters in `apps/platform-*`, local External Op sandboxes for vendor models, registry font packages (FLX owns circuit LU) | `DeviceIo` | 1; 2 (serial and USB); 3 (flashing service) |"
   - Why: contract 7.6 puts desktop client flashing "in `apps/platform-*`'s flashing service"; ELX hands PLT "the flashing service and bench adapters in `apps/platform-*`" (ELX line 1235). This tab's "Serial and USB" row is phase 2 (line 511) and never mentions flashing.
5. **[medium] The restricted-jurisdiction rule is ECO's dataset.** `### Signed updates` (line 754) and tenant onboarding (line 698)
   - Now: "Update servers refuse the countries of ECO's sector rule." → Must say: "Update servers refuse the jurisdictions of ECO's restricted-jurisdiction dataset."
   - Now: "Tenant onboarding applies ECO's sector rule." → Must say: "Tenant onboarding applies ECO's restricted-jurisdiction rule."
   - Why: D-ECO-29 (ECO line 763) covers comprehensive embargoes and regions, not only sector rules; ECO provides "the restricted-jurisdiction dataset for update servers" (ECO line 1134).
6. **[medium] The stack limit is set in bytes.** `### Rust surface` (line 1100)
   - Now: "pub struct CallLimits { pub fuel: u64, pub stack_frames: u32, pub max_memory_bytes: u64 }"
   - Must say: "pub struct CallLimits { pub fuel: u64, pub logical_stack_bytes: u32, pub max_memory_bytes: u64 }"
   - Why: ECO's limits table is the only place that sets the figure, "Logical stack | 256 KiB" (ECO line 392); this tab's determinizer text says only "a logical stack-depth limit" (line 330).
7. **[medium] `ResourceExhausted` is a unit Abort.** `### Memory` (line 213)
   - Now: "Waits 2 s for eviction, then `ResourceExhausted { requested, available, fix }`"
   - Must say: "Waits 2 s for eviction, then the `ResourceExhausted` Abort"
   - Why: KLN owns `Abort` in `base-op` (contract 7.2: "a closed enum"); KLN line 1105 gives `ResourceExhausted` no fields, and this tab's line 404 writes "Abort: `ResourceExhausted`".
8. **[low] The human-only method list is contract 7.6's.** `### Approvals and local credentials` (line 470)
   - Now: "A human-only method (merge, text endorsement, waiver, declassification, a local write above `public`)"
   - Must say: "A human-only method (contract 7.6's list, a local write above `public` included)"
   - Why: contract 7.6 also lists `propose.policy` and recipient and clearance changes, which this copy drops.
9. **[low] The approval-origin cookie rule is AGT's.** `### Approvals and local credentials` (lines 468, 472)
   - Now: the bullet beginning "- **Cookies.** The approval origin sets only `__Host-` cookies" → Must say: delete the bullet.
   - Now: "Three rules from contract 7.6 land here:" → Must say: "Two rules from contract 7.6 land here:"
   - Why: AGT owns the approval origin (contract 7.6; AGT line 963 states the cookie rule); this tab's lead (line 460) says "AGT and UIX own the ceremony and the page". Drop `[MDN Set-Cookie]` from Sources if nothing else cites it.
10. **[low] ECO's world rules restated.** `### Worlds, calls and failures` (line 394)
    - Now: "ECO defines the worlds and PLT enforces them. Tool and connector worlds use WASI 0.3, and an import a world does not grant fails at install with `ForbiddenImport { import, fix }`. Evaluation worlds import no WASI, their `crucible:ops` imports are callback-ABI async functions, results never depend on completion order, and host time never counts as fuel."
    - Must say: "ECO defines the worlds ([ECO, Determinism and limits](11-interop-ecosystem.md#determinism-and-limits)) and PLT enforces them: an import a world does not grant fails at install with `ForbiddenImport { import, fix }`."
    - Why: contract 7.4 ("Worlds") and D-ECO-9 (ECO line 382) state the WASI, callback-ABI, ordering and fuel rules.
11. **[low] Rows that use other tabs' capabilities carry `Requires:` entries.** Capability tables (lines 308, 770)
    - Now: "| Canonical sparse factorization | FLX's supernodal elimination and block-triangular LU, thread-count independent | Divergence fails the suite |" → Must say: "| Canonical sparse factorization | FLX's supernodal elimination and block-triangular LU, thread-count independent | Divergence fails the suite. Requires: FLX Canonical direct solvers |"
    - Now: "| No TPM: readings `data_untrusted` |" → Must say: "| No TPM: readings `data_untrusted`. Requires: MFG Gateway |"
    - Why: contract 13.4's `Requires:` rule; FLX's row is phase 1 (FLX line 670) and MFG's phase 2 (MFG line 980).
12. **[low] The `base-op` comment names the wrong crate owner.** `### Rust surface` (line 1085)
    - Now: "// base-op, owned by PLT"
    - Must say: "// base-op (KLN's crate); this type is PLT's"
    - Why: contract 12: `base-op` is KLN's, "with every owner of a type".
13. **[low] Fidelity and risk-class names.** `## State of the art` (line 1191) and `### Toolchain and dependencies` (line 861)
    - Now: "Later on `f64` GPU sign-off solves" → Must say: "Later on `f64` GPU `SignOff` solves"
    - Now: "records each core dependency's risk class, cadence and fork plan" → Must say: "records each core dependency's risk tier, cadence and fork plan"
    - Why: contract 2 forbids "sign-off" for the fidelity; "risk class" names AGT's Proposal classes R0 to R4 (contract 7.6).
14. **[low] "BOM" means bill of materials.** `### Paths, text, fonts and accessibility` (line 482)
    - Now: "readers normalize CRLF, CR and a BOM on input"
    - Must say: "readers normalize CRLF, CR and a byte-order mark on input"
    - Why: BOM is KLN's bill of materials (contract 2, Service BOM).
15. **[low] MCP spelled out.** `### Isolation of third-party Wasm components` (line 384)
    - Now: "tool processes and stdio MCP servers; Windows"
    - Must say: "tool processes and stdio MCP (Model Context Protocol) servers; Windows"
    - Why: contract 11.


## Contract v7.4 (applies to every tab)

Contract v7.4 ruled on the audit's contract items after this brief was written. Apply these on top of your section:

- **Computed view.** "Derived view" now means only the declassified view of a labelled module or supplier package (contract 2). Where your tab calls a BOM or another computed node a derived view, write "computed view" (KLN and ELX use this sense; grep your tab).
- **Reached limits** are `kiln/work_limit` and `kiln/memory_limit` Failures whichever layer reaches them, with any best-so-far result beside the Failure (contract 7.2). MFG: replace `MfgError::WorkLimit { limit: base::WorkLimit, best_so_far }` accordingly. PLT and ECO: a Wasm `memory.grow` past the maximum surfaces as `kiln/memory_limit`.
- **`standing_release`** is in contract 7.6's Act kinds; AGT's table and D-AGT-36 stay as they are.
- **Single-person mode** (5.4): only two-person records and R3 and R4 merges wait 72 h; before phase 2 the verifier role's CI-signed review counts as `Attested`. AGT and KLN state this in one line with a pointer.
- **`PlacementPolicy`** is implemented by `trust`.
- **13.4:** MEC no longer appears as "Also phased in" for planar models, linear dynamics and symmetry reductions, nor FLX for fibre orientation, phase-transformation kinetics, battery swelling and abuse; a tab that still phases these itself states the owner's phase in one line instead. FMU import has a shared row at phase 3 (owner FLX, also ELX and ECO): ELX's "FMU elements" row and ECO's FMU catalog row cite it.
- **Bracket figures** are ING's, as judgment call 1 says.
