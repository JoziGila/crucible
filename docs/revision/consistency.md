# Round 3: consistency pass (brief for each tab's agent)

All twelve subsystem tabs are v3, and contract v6.1 rules on every change request filed so far (contract sections 16 and 17). A cross-tab audit found the mismatches below and decided each one; the owner of a fact wins. Your job: apply your tab's edits, without reopening the revision.

## Rules

- Edit only your own `docs/spec/<file>.md` (and its diagram files if an edit touches a diagram). Never edit another tab, the contract, a README or CLAUDE.md, and never commit.
- Apply every edit in your tab's section below. Each quotes the current text; if the text has moved, find it by its words. If an edit is wrong on the evidence, skip it and say why in your report.
- Keep every decision, oracle and source. A decision you change ends with "(revised in round 3)" unless it is new in round 3.
- Stay within the word limit (12,000 to 18,000 words excluding Sources; ING and ANV up to 20,000). Apply your change-request edit first; it frees room.
- Names only the owner may choose are yours if you own them: FLX names its circuit-analysis operations (operating point, AC, transient, harmonic balance) in its operations catalog, and ELX then cites them; AGT names `api` methods for ING's language service, agent questions to the delegating human, and COV's coverage map, and adds their rows. PLT reopens NIST's CMVP page for certificate 5314 before citing it.
- Run `python3 docs/tools/check.py docs/spec/<file>.md --base round-2`: zero errors, and nothing cut since round 2.
- Reply in at most 150 words: edits applied and skipped (with reasons), names you chose, the word count and the check result.

## The audit

This audit covers the twelve subsystem tabs at commit `60f0264` (contract v6.1; the working tree was clean). It checks each interface row against the other tab's row, phases against contract 13.4 and the owners' capability tables, names against the glossary and the owners, change-request citations against contract 16 and 17, staffing wording against contract 13.2, and the items the round 3 agents reported.

**How the owner was chosen.** The owner of a fact wins (`docs/revision/consistency.md`). The owner is the tab named by contract 5's `[TAB]` tags or 13.4's Owner column. Otherwise it is the tab whose design section specifies the fact, and any item decided another way says so.

**How the quotes were checked.** Every "Now" quote below occurs exactly once in the committed file, at the line given (`grep -F`). A row quoted without its first cells is still unique.

**Word budgets.** Several tabs sit at their ceiling. Each tab's change-request edit below shortens its section by 20 to 110 words, which pays for that tab's additions. Apply that edit first, then run `python3 docs/tools/check.py docs/spec/<file>.md --base round-1`.

| Tab | Words now | Room | Tab | Words now | Room |
| --- | --- | --- | --- | --- | --- |
| ING | 19,918 | 82 | MFG | 17,860 | 140 |
| ANV | 19,963 | 37 | ELX | 17,956 | 44 |
| FLX | 17,937 | 63 | AGT | 17,836 | 164 |
| COV | 17,690 | 310 | UIX | 17,981 | 19 |
| KLN | 17,996 | 4 | ECO | 17,752 | 248 |
| MEC | 17,949 | 51 | PLT | 17,776 | 224 |

## Summary

**The round 3 agents' items.**

| Reported item | State at `60f0264` | Edit |
| --- | --- | --- |
| ANV relabels copies "in `CallSite` order"; ING says program order | Mismatch; ING owns the program-order index | ANV 1, 3 |
| KLN ships minimal signature records in phase 1 | Already consistent: KLN-O-SIG-1 is phase 1 ("Phase 1 ships this record for the GP1 release"), and declassification, Waivers and `ControlAuthorization`s are phase 1 too | none |
| KLN's two-person list includes AGT's items | Mismatch: D-KLN-41 lacks `allow_raw_external` and training opt-in, and names standing releases only generically | KLN 1 |
| ANV's on-demand query stability analysis | Exists: `anvil::query_stability`, phase 1, ANV-O-NAME-6 (D-ANV-34); AGT's phase 1 matches, but AGT never names it | AGT 4 |
| ECO's "data-package record" | That wording is gone; ECO now says "`release_data` commit records", where KLN says release-data records | ECO 7 |
| PLT adds `PoolLane::Interactive` | The enum exists (`enum PoolLane { Interactive, Foreground, Background }`), but PLT's rows to ING, MEC, ELX and AGT omit the lane those tabs require | PLT 4 |
| AGT lists `evaluate.subscribe` and `edit.stream` | Both are in the catalog (phase 1); AGT's interface rows still say "drag streams" | AGT 4 |
| ANV's references to KLN's limit catalog | Exists (`base` catalog, KLN-O-LIMIT-1) | none |
| ANV's references to MEC's `pmi_target_resolved` | Exists (D-MEC-27, MEC-O-TL-6). MEC's interface rows omit it, and ING cites the wrong MEC oracle | MEC 7, ING 4 |
| ANV's reference to ING's error for a wrong-kind role filter | Exists as the compiler error `ING5002`; ANV calls it a language-service rejection | ANV 4 |
| ANV's reference to D-AGT-8 | Exists, but it decides `inspect.suggest_query` ranking, not the ranking of `ResolveError` fixes ANV cites it for | ANV 5 |

**Sweeps with nothing to change.**

- **Staffing.** No staffing, hires, engineer-years or calendar months remain in the twelve tabs. KLN's "Hit rate for 20 people" is a benchmark scenario, and ECO's stewardship trigger is a governance date, not a plan figure.
- **Ids and names.** Every decision id cited across tabs exists, though four are cited for something they do not decide (ANV 5, KLN 1, ECO 7, MEC 11). Every cross-tab oracle id exists except `COV-O-ENV-2` (FLX 8). Every `<group>.<name>` method cited exists in AGT's catalog. No banned Act name (`transfer_program`, `start_build`, `queue_program`) appears.

**Judgment calls for the orchestrator.** These are decided below, but the other direction is defensible:

1. **`store_machine_job`.** AGT moves the Act to phase 3 behind ECO's and MFG's phase 3 OPC UA path (AGT 1). The alternative moves the OPC UA job path to phase 2.
2. **`CatalogSelection`.** ELX moves its row to phase 2, because GP3's bearings need it (ELX 3). The alternative moves ING's and MEC's rows to phase 3.
3. **RoHS checks.** MFG moves its row to phase 3 behind KLN's compliance roll-up (MFG 4). The alternative moves KLN's roll-up to phase 2, which COV's phase 2 substance data would support.
4. **`measure` and `sample` WIT interfaces.** ANV and FLX drop them, because contract 4 and ECO's D-ECO-7 route every engine read through `crucible:ops`, and KLN agrees (ANV 2, FLX 2).
5. **3D mice on Linux.** Contract 12 makes PLT the owner. PLT's row is reworded to fit D-UIX-31 rather than reversing that decision (PLT 5).

Two items need a name only the owner can choose: FLX's circuit-analysis operations (FLX 4), and AGT's methods for the language service, agent questions and the coverage map (AGT 7).

**Outside the twelve tabs** (plan step 6):

- The Overview (`00-overview.md`) still has durations, headcounts and engineer-years (lines 267 to 370) and the old `side(outline.top)` example (line 106).
- The Decisions log has no lines for round 3's new decisions (D-ING-26, D-ANV-32 to D-ANV-36, D-ECO-33 to D-ECO-37, D-PLT-41 to D-PLT-47 and others).
- The Adversarial review (line 180) still states the E_A + E_B agreement rule that D-PLT-35 replaced.

## ING

1. **[high] Seed quantum.** `### Builder blocks and sketches` (line 625)
   - Now: "A released sketch drag rounds seeds to a quantum q, by default the larger of 1 µm and 2¹⁰ times the sketch's resolution ρ, in decimal millimetres."
   - Must say: "A released sketch drag rounds seeds to MEC's quantum q (D-MEC-33), in decimal millimetres."
   - Why: MEC owns the quantum. D-MEC-33 says "rounded to a quantum q: the larger of 2¹⁰ρ for the sketch and 10⁻⁶ of its diagonal", and MEC's open questions decline R8-24's 1 µm floor. For a 60 × 40 mm sketch, MEC's rule gives about 0.07 µm and ING's gives 1 µm. The edit saves 15 words.
2. **[medium] `Aspect<K>` is MEC's `ShapeAspect`.** `### GD&T controls as types` (lines 458, 466, 469)
   - Now: "`Query<Aspect<K>>` selects shape aspects whose kind is static when the producing feature declares it: `hole(…)` gives `Aspect<OfSize>`, extrude caps `Aspect<Planar>`, recognized imports `Aspect<Any>`." Also "// Query<Aspect<OfSize>>" and "start_cap is Aspect<Planar>".
   - Must say: the same text with `ShapeAspect<K>`, `ShapeAspect<OfSize>`, `ShapeAspect<Planar>` and `ShapeAspect<Any>`.
   - Why: contract 5 names the type `ShapeAspect` [MEC]. MEC's shared types define "`ShapeAspect` | … | A `Query` over faces, typed by kind (D-ING-6)", and its record field is `target: Query<ShapeAspect>`. Contract 10 allows one name per concept.
3. **[medium] `general_tolerance` signature.** `` ### `Tol<T>` `` (line 397)
   - Now: "MEC's Part-level `general_tolerance(standard, class)` record"
   - Must say: "MEC's Part-level `part.general_tolerance(spec)` record (D-MEC-35)"
   - Why: D-MEC-35: "A Part declares its general tolerance with `part.general_tolerance(spec)`".
4. **[medium] Wrong MEC oracle for `pmi_target_resolved`.** `### Approximate values as inputs` (line 515)
   - Now: "| `ING4001`, `ING4002`; `pmi_target_resolved` | ING-O-7, MEC-O-TL-1 | 1 |"
   - Must say: "| `ING4001`, `ING4002`; `pmi_target_resolved` | ING-O-7, MEC-O-TL-6 | 1 |"
   - Why: MEC's "PMI target check" row cites MEC-O-TL-6 at phase 1, whose pass criterion is the forwarded `4mm ± 0.1mm` split. MEC-O-TL-1 judges dialects and backs MEC's phase 2 conversion row.
5. **[medium] A phase 1 oracle tests KLN's phase 3 BOM.** `## Oracles` (line 1324, ING-O-30)
   - Now: "the 150% BOM equals enumeration on small fixtures; "
   - Must say: delete the clause, since KLN-O-PLM-5 checks the 150% BOM.
   - Why: KLN owns it. "This tab owns variant semantics and their oracle", and its row is "Variants and 150% BOM | … | KLN-O-PLM-5 | 3". ING-O-30 backs ING's phase 1 "Variant regions" row, and 13.4 forbids a row that precedes its prerequisite.
6. **[medium] Wrong ANV oracle for solved points.** `### Patterns, loops and keys` (line 706)
   - Now: "| ING-O-5, ING-O-10, ING-O-23, ANV-O-NAME-5 | 1 |"
   - Must say: "| ING-O-5, ING-O-10, ING-O-23, ANV-O-SOLVE-1 | 1 |"
   - Why: ANV-O-NAME-5 checks query fixes. ANV-O-SOLVE-1 checks constraint solving ("Krawczyk boxes contain reference solutions"), which is what "certified solved points" claims.
7. **[low] Requirements the owner does not specify.** `### Ingot requires` (lines 1280, 1281)
   - Now: "| ANV | Operations catalog with tangent rules;" → Must say: "| ANV | Operations catalog;"
   - Now: "tangent and adjoint rules; `away_from` over several sets; basis enclosures as input parts" → Must say: "tangent and adjoint rules; basis enclosures as input parts"
   - Why: ANV specifies no tangent rules. Its derivative service is `anvil::shape_velocity` (phase 2), which this row already lists. `away_from(sets, d)` is defined by ING itself (`### Checks`); FLX supplies only the default distances, which the row lists as "singular sets with default distances".
8. **[low] Sketch re-solve target.** `## Oracles` (line 1317, ING-O-23)
   - Now: "Every constraint type expressible; at least 99% re-solve within tolerance (target)"
   - Must say: "Every constraint type expressible; re-solves meet MEC-O-SK-1's target"
   - Why: MEC owns sketch solving, and its target is "SketchGraphs replay: 99.5% on the recorded branch" (MEC `## State of the art`).
9. **[low] `vary` has no capability row.** `### Approximate values as inputs` (line 517)
   - Now: "| Statistical combination | Explicit `rss(coverage:)` and `monte_carlo`; name-free symbol order |"
   - Must say: "| Statistical combination | Explicit `rss(coverage:)`, `monte_carlo` and `vary`; name-free symbol order |"
   - Why: MEC's phase 2 "3D rebuild path" reads "ING's `vary`", and MEC's ING row requires it. ING specifies it only in prose.

## ANV

1. **[high] Copy relabelling order.** `### Copies and placements` (line 350)
   - Now: "the operand from the later transform in `CallSite` order is relabeled."
   - Must say: "the operand from the later transform in ING's program order is relabeled."
   - Why: ING owns the order. ING `### The Ingot IR and Kiln` says "Each call records its program-order index … Anvil's copy relabelling reads the same index", and ING's copy rule says "in program order". A `CallSite` is an identity, with no order defined on it.
2. **[high] `measure` host interface.** `### Rust surface and WIT interfaces` (line 86)
   - Now: "| `crucible:geom/build`, `measure` | Builders validated by `anvil::build`; mass properties, distance, classification and deviation with bounds | `invalid(violations)`, `work-limit`, `not-separated` |"
   - Must say: "| `crucible:geom/build` | Builders validated by `anvil::build`; measures through `crucible:ops/anvil` (contract 4) | `invalid(violations)`, `work-limit` |"
   - Why: contract 4 lets Wasm components "reach engine data only through `crucible:ops` and handles derived from their inputs", with every read a recorded dependency. ECO keeps the WIT index, where `crucible:geom` is "`types`, `build`", and D-ECO-7 rejects "`measure` and `sample` host interfaces (round 2)". KLN: "Measuring and sampling go through `crucible:ops` (contract 4)."
3. **[medium] The Ingot requirement row.** `### Anvil requires` (line 994)
   - Now: "| Ingot | Text-derived `CallSite`s; `QueryPlan`s; wrong-kind role filters as compile errors;"
   - Must say: "| Ingot | Text-derived `CallSite`s; the program-order index; `QueryPlan`s; wrong-kind role filters as compile errors (`ING5002`);"
   - Why: ING provides ANV "program order for copy relabelling" and names the error.
4. **[medium] A wrong-kind role is a compiler error.** `### Role vocabulary` (line 335) and the capability table after `### Imported and non-B-rep entities` (line 447)
   - Now: "ING's language service rejects a role filter on the wrong entity kind." → Must say: "ING's compiler rejects a role filter on the wrong entity kind (`ING5002`)."
   - Now: "A wrong-kind role filter is a compile error (ING)" → Must say: "A wrong-kind role filter fails to compile with `ING5002` (ING)"
   - Why: ING says "a wrong-kind role fails with `ING5002`" (its Queries table and ING-O-11). `INGnnnn` codes are compiler errors; the language service raises `ING-L-*` lints.
5. **[medium] D-AGT-8 cited for something it does not decide.** `### Query resolution` (line 394)
   - Now: "`query_stability` ranks the fixes (D-AGT-8)."
   - Must say: "`query_stability` ranks the fixes, as it ranks `inspect.suggest_query` candidates (D-AGT-8)."
   - Why: D-AGT-8 says "`inspect.suggest_query` ranks candidates by ANV's sampled stability analysis". The `ResolveError` fixes are ANV's own (contract 5 `Query`).
6. **[medium] A closure-hash exception the contract does not allow.** `### Behavior versions` (line 54)
   - Now: "Kiln refuses a released version whose closure hash changed; a security exception needs the founder's approval and identical corpus outputs."
   - Must say: "Kiln refuses a released version whose closure hash changed; a security fix ships as a new operation version (contract 4)."
   - Why: contract 4 states the refusal with no exception, and KLN owns registration (D-KLN-2: "refuses a changed one").
7. **[low] Concave-edge singularity is Flux's exponent rule.** `## Measurement, analysis and simulation services` (line 833) and `### Anvil requires` (line 993)
   - Now: "Flux sets the angle above which a concave edge is singular." → Must say: "Flux decides which concave edges are singular (D-FLX-39)."
   - Now: "sizing and metric Fields; the singular concave angle" → Must say: "sizing and metric Fields; the concave-edge singularity rule (D-FLX-39)"
   - Why: D-FLX-39 flags a `Concave` edge "when its leading Williams exponent λ₁ is below 0.9" and rejects one fixed angle.
8. **[low] Provided rows omit what other tabs require.** `### Anvil provides`
   - Now (line 983): "`query_stability` reports; measures and geometry diffs |" → Must say: "`query_stability` reports; measures, sections and geometry diffs |". AGT requires "measures, sections and geometry diffs", and round 2's follow-up ruling (consistency.md section 5, ANV row) asked for it.
   - Now (line 975): "closure hashes and two-stage keys; `Failure`s, never Aborts |" → Must say: "closure hashes and two-stage keys; deterministic outcomes as `Failure`s |". ANV's own rows make device loss, cancellation and memory exhaustion Aborts, as KLN's D-KLN-6 does.
   - Now (line 978): "| COV | Implicit and lattice Bodies; mid-surfaces and member axes; per-entity tolerances | `Body` |" → Must say: the same row with "; curvature and thickness queries" before the Types cell. COV requires them.
   - Now (line 981): "`anvil::planar` with centre–radius arcs and conservative snapping; `fold`; `convex_decompose` | `Body` |" → Must say: "… `fold`; `convex_decompose`; `text_outline` | `Body` |". ELX requires `anvil::text_outline`.
   - Now (line 977): "meshing and adaptation by canonical number; `shape_velocity`; `implicit_from_field` |" → Must say: "…; `implicit_from_field`; `common_refinement` (phase 4) |". FLX requires it.
9. **[medium] Change requests still written as pending.** `## Contract change requests` (lines 1104, 1105)
   - Now: "- CCR-ANV-7 and CCR-ANV-8: accepted in contract v4.1." → Must say: "- CCR-ANV-7 and CCR-ANV-8: accepted in contract v4.1 (sections 13.3 and 5)."
   - Now: the bullet beginning "- **CCR-ANV-9, `DisplayPackage` identity.**" → Must say: "- CCR-ANV-9, `DisplayPackage` identity: accepted with CCR-UIX-7 in contract v6.1 (section 5, `DisplayPackage`)."
   - Why: contract 16 gives 13.3 and 5. Contract 17 rules "CCR-ANV-9, CCR-UIX-7 `DisplayPackage` identity | Accepted together (5)". The edit saves about 40 words.

## FLX

1. **[high] DFN lands in phase 4.** `` ### Compilation and `local_solve` `` (line 310)
   - Now: "| Parameter-domain spaces | `Interval`, `Sphere`, products, `dξ` | `FormError::Conformity` | FLX-O-FORM-5 | 4 |"
   - Must say: the same row ending "| FLX-O-FORM-5 | 4, 5 (DFN) |"
   - Why: 13.4 is binding: "Battery cells: Doyle–Fuller–Newman (P2D) | 5 | None | FLX". FLX-O-FORM-5 demands "SPMe and P2D DFN voltage within 1 mV of PyBaMM", so as written DFN ships in phase 4. FLX's own Phasing puts DFN cells in phase 5.
2. **[high] `sample` host interface.** `### WIT interfaces` (lines 75, 81)
   - Now: "Flux owns `crucible:field` (interfaces `types`, `build`, `sample`)" → Must say: "Flux owns `crucible:field` (interfaces `types` and `build`; sampling is `flux::field_sample` through `crucible:ops/flux`)"
   - Now: "| `crucible:field` WIT package | `types`, `build`, `sample`, generated from the Rust types |" → Must say: "| `crucible:field` WIT package | `types` and `build`, generated from the Rust types |"
   - Why: the same reasons as ANV 2. FLX's catalog already has `field_sample`, and ECO's index lists `crucible:field` as "`types`, `build`".
3. **[high] Bolted-joint forms are provided but never specified.** `### Calibrated estimates` (line 207), plus a new capability row under `### Contact, constraints and fracture`
   - Now: "Reduction patches and step halving add classes in phase 2"
   - Must say: "Reduction patches, step halving and bolted-joint forms add classes in phase 2". Also add a phase 2 capability row for bolted-joint forms (preloaded bolt elements and joint springs for COV's VDI 2230 model), with a FLX oracle.
   - Why: FLX's MEC row (line 917) provides "bolted-joint forms", but that row is FLX's only mention of bolts. MEC's D-MEC-30 table needs "Bolted joints | `Estimated` plus a policy allowance | Bolted-joint forms | 2", and COV's "Bolted and bonded joints" model is phase 2. FLX owns forms and calibration classes (contract 7.1).
4. **[medium] Circuit-analysis operations have no names.** `## Scope and architecture`, operations table (line 29)
   - Now: "| Lumped and multibody | `compile_network`, `solve_dae`, `solve_multibody`, `linearize_multibody`, `solve_rod` |"
   - Must say: the same row, also naming the operations behind ELX's operating point, DC sweep, AC and noise, and pole-zero analyses. FLX chooses whether these are new names or existing ones such as `solve_nonlinear` and `solve_harmonic`. ELX's rows under `## Analog and mixed-signal simulation` then cite them.
   - Why: contract 2 puts every operation in Anvil or Flux, and ELX's D-ELX-13 says "Crucible's circuit simulator is a set of Rust Flux operations". FLX's catalog names none of them. FLX owns operation names.
5. **[medium] PLT's agreement rule restated wrongly.** `### Verification, validity and agreement` (line 231)
   - Now: "with equal resolved plans and adaptive marks, only the algebraic, floating-point and temporal-control parts plus a floor count."
   - Must say: "with equal resolved plans, adaptive marks and steps, only the algebraic and floating-point parts plus a floor count."
   - Why: PLT owns the rule. D-PLT-35: "With the same resolved `SolvePlan`, adaptive marks and steps … The tolerance is then both classes' algebraic and floating-point parts plus a floor".
6. **[medium] An Anvil failure that does not exist.** `` ### Compilation and `local_solve` `` (line 309)
   - Now: "| Spline and manifold spaces | NURBS and THB spaces; sheet and wire spaces | `NotParameterizable` from Anvil |"
   - Must say: "| Spline and manifold spaces | NURBS and THB spaces; sheet and wire spaces | `UnpairedFaces` or `NotPrismatic` from Anvil |". If NURBS-space extraction needs its own failure, ANV adds it to its catalog first.
   - Why: ANV defines no `NotParameterizable`. Its sheet and wire sources fail with `UnpairedFaces { faces, reason }` (`anvil::mid_surface`) and `NotPrismatic { region }` (`anvil::member_axes`).
7. **[medium] `OutsideEnvelope` names two concepts.** `### Rust API` (line 69), `### Verification, validity and agreement` (line 229), and the reduced-model text (lines 799, 814)
   - Now: "OutsideEnvelope { parameter: ParamId, range: (f64, f64) }," → Must say: "OutsideParameterBox { parameter: ParamId, range: (f64, f64) },". Rename it the same way in "queries outside it fail with `OutsideEnvelope { parameter, range }` unless the caller requests a full solve." and in "| `OutsideEnvelope { parameter, range }`; `TopologyChange` | FLX-O-ROM-1 | 3 |".
   - Now: "`ValidityError::OutsideEnvelope { variable, bound, escalations }`" → Must say: "`ValidityError::OutsideEnvelope { variable, bound, escalate_to }`"
   - Why: COV owns `ValidityError` and calls `OutsideEnvelope` "the one failure COV and FLX both name", with the field `escalate_to: Vec<ModelRef>`. A reduced model's parameter box is a different concept (contract 10).
8. **[low] A stale COV oracle id.** `## Oracles` (line 963)
   - Now: "| FLX-O-ERR-9 | Validity zones (merged with COV-O-ENV-2) |"
   - Must say: "| FLX-O-ERR-9 | Validity zones (COV's zone-semantics row cites it) |"
   - Why: COV no longer defines COV-O-ENV-2; its "Zone semantics" row cites FLX-O-ERR-9.
9. **[low] Rows that cite later ANV operations.**
   - `### General operations for non-variational methods` (line 467). Now: "| Fitted continuous FEM | Curved Anvil meshes to p ≤ 8; hex-dominant | `InvalidElement { cell, jacobian_min }` with an `untangle` fix | FLX-O-DISC-1 | 2 |" → Must say: the same row ending "| FLX-O-DISC-1 | 2, 4 (hex-dominant) |". ANV phases `anvil::hex_dominant` "3 (sweep), 4 (hex-dominant)".
   - `### Storage` (line 143). Now: "| Conservative for fluxes, consistent for states | `NotSameInterface` from Anvil | FLX-O-FIELD-2 | 1 |" → Must say: "… | FLX-O-FIELD-2 | 1, 4 (interface overlays) |". `NotSameInterface` comes from `anvil::common_refinement`, which is phase 4.
   - `### Regularized goals and singular points` (line 186, D-FLX-39). Now: "`Ambiguous` edges are flagged, with `recognize_aspects` as fix." → Must say: "`Ambiguous` edges are flagged, with `recognize_aspects` as fix from phase 2." ANV's `anvil::recognize_aspects` is phase 2.
10. **[low] 13.4 rows FLX never phases.** `## Phasing` (lines 1037, 1038)
    - Now: "FMU export and SSP, SPMe forms," → Must say: "FMU export and SSP, SPMe forms, cell swelling and stack pressure,"
    - Now: "GP9 crash with erosion; DFN cells;" → Must say: "GP9 crash with erosion; DFN cells; battery abuse mechanics (6);"
    - Why: 13.4 lists FLX under "Also phased in" for both rows ("Battery cells: swelling and stack pressure | 4", "Battery abuse mechanics … | 6").
11. **[low] The ELX row omits a 13.4 capability FLX owns.** `### What Flux provides` (line 919)
    - Now: "layered sheets; electromagnetic solvers; conjugate heat transfer; parameter-domain forms;"
    - Must say: "layered sheets; electromagnetic solvers; conjugate heat transfer; electro-thermal coupling; parameter-domain forms;"
    - Why: 13.4 makes FLX the owner (phase 4), and ELX's row reads "Electro-thermal coupling | Monolithic Newton with continuation (FLX)".
12. **[medium] Change requests still written as pending.** `### Eigenvalue problems` (line 587), `## Open questions` (line 1047), `## Contract change requests` (lines 1058, 1059)
    - Now: "and wait for CCR-FLX-11." → Must say: "and contract section 5 now admits them as `Guaranteed` bounds (CCR-FLX-11)."
    - Now: "- R7-05: `Guaranteed` eigenvalue lower bounds wait for CCR-FLX-11." → Must say: "- R7-05: `Guaranteed` eigenvalue lower bounds are admitted by contract section 5 (CCR-FLX-11)."
    - Now: the bullet beginning "- CCR-FLX-10, boundary layers:" → Must say: "- CCR-FLX-10, boundary layers: accepted in contract v6.1 (section 7.1)."
    - Now: the bullet beginning "- CCR-FLX-11, eigenvalue bounds:" → Must say: "- CCR-FLX-11, eigenvalue bounds: accepted in contract v6.1 (section 5, `ErrorBound`)."
    - Why: contract 17: "CCR-FLX-10 boundary layers | Accepted (7.1)" and "CCR-FLX-11 eigenvalue bounds | Accepted (5 `ErrorBound`)". If FLX ships these bounds, it states the phase, no earlier than fitted tetrahedra (phase 2, 13.4).

## COV

1. **[high] Calibration classes differ from FLX's.** `### Error budgets and model form` (line 64), `### Package contents` (line 569), `## Phasing` (line 891), `## Open questions` (line 909)
   - Now: "Phase 1 needs three classes, each with 300 held-out samples from FLX's corpus (FLX "Calibrated estimates"). `elasticity/regularized_peak` covers immersed linear elasticity at p = 2 to 6 at both fidelities, for GP1 and GP2 stress. `lattice/strut_stress` and `lattice/buckling_factor` cover the beam lattice's strut stresses and its eigenvalue-DWR buckling factor."
   - Must say: "Phase 1 needs FLX's four classes (FLX "Calibrated estimates"), each with 300 held-out samples: `elasticity.peak` and `elasticity.eigen` for immersed linear elasticity at p = 2 to 6, and `lattice.strut_stress` and `lattice.buckling` for the beam lattice's strut stresses and buckling factors."
   - Now: "calibration: ["elasticity/regularized_peak"]," → Must say: "calibration: ["elasticity.peak"],"
   - Now: "three calibration classes; strut buckling envelopes" → Must say: "four calibration classes; strut buckling envelopes"
   - Now: "R7-16: three phase 1 classes, not five" → Must say: "R7-16: four phase 1 classes, not five"
   - Why: FLX lists the classes (contract 7.1: "FLX lists them"): `elasticity.peak`, `elasticity.eigen`, `lattice.strut_stress` and `lattice.buckling`. COV drops `elasticity.eigen`, which 13.4's phase 1 modal and buckling row needs. COV's slashed names also read as `<family>/<code>` error codes.
2. **[high] Boiling uses VOF before 13.4's phase 5.** `### Heat transfer` (line 309)
   - Now: "| Nusselt film analytic | 4 · Nat |"
   - Must say: "| Nusselt film analytic | 4, 5 (VOF, 13.4) · Nat |"
   - Why: COV owns the 13.4 row "Free-surface and multiphase flow beyond mould filling | 5". This row's L3 method is "VOF with phase change", and FLX's finite volume row says "5 (beyond filling)".
3. **[medium] Two producers for the input part.** `### Error budgets and model form` (line 44)
   - Now: "COV fills the input part from Material uncertainty and the model-form part from validation of the 3D physics and constitutive model."
   - Must say: "COV supplies the Material uncertainty that Flux propagates into the input part, and fills the model-form part from validation of the 3D physics and constitutive model."
   - Why: contract 5 gives each source one producer. FLX's `### Budgets and guarantees` says Flux produces every part except model form, from "`std::uq` bounds; property-basis enclosures". COV's own D-COV-13 says Flux carries the enclosure "into solves as an input part".
4. **[medium] `std::uq` behaviour differs from its owner's.** `### Uncertainty` (line 675)
   - Now: "`std::uq` propagates input error by first-order adjoint sensitivities, switching at `SignOff` to seeded quasi-Monte Carlo when second-order terms exceed 10% of first-order ones (target)."
   - Must say: "`std::uq` propagates input error by FLX's worst-case rule (D-FLX-35): adjoint-linearized bounds plus a Lanczos remainder, with `NonlinearResponse` above 20% asking for a statistical method."
   - Why: FLX owns `std::uq`, which COV requires from FLX. D-FLX-35: "`NonlinearResponse` fires when the remainder exceeds 20% of the linear term". The FLX row "asks for a statistical method" and never switches on its own.
5. **[medium] Cohesive zones phased before Flux's hooks.** `### Solid mechanics` (line 259)
   - Now: "| DCB and ENF | 2 · Nat |"
   - Must say: "| DCB and ENF | 2 (bolts), 3 (cohesive) · Nat |"
   - Why: FLX: "Fracture hooks carry COV's models: J-integrals (phase 2), cohesive zones (3)". 13.4 forbids a row earlier than a capability it names.
6. **[low] Coverage rows that name later FLX methods carry only their first phase.** 13.4's prerequisite rule applies to each method a row names.
   - `### Solid mechanics` (line 251). Now: "| NAFEMS LE1 92.7 MPa, LE10 −5.38 MPa, LE11 −105 MPa [S3][S4]; GP1, GP2 | 1 · Nat |" → Must say: "… | 1 (octree), 2 (IGA, finite cell, frame networks) · Nat |". FLX phases spline spaces, the finite cell method and `compile_network` at 2.
   - `### Dynamics and stability` (line 267). Now: "| NAFEMS free vibration [S2][S5] | 1 · Nat |" → Must say: "… | 1, 2 (Craig–Bampton) · Nat |". FLX: "Modal superposition; Craig–Bampton | … | 2".
   - `### Heat transfer` (line 305). Now: "| NAFEMS T2 to T4 [S2][S5] | 1 · Nat |" → Must say: "… | 1 (FEM), 2 (IGA, networks), 3 (moment matching) · Nat |". FLX: "Krylov moment matching | … | 3".
   - `### Fluids` (line 328). Now: "| Porous channel | 3 · Nat |" → Must say: "| Porous channel | 3, 4 (lattice Boltzmann) · Nat |". FLX: "Lattice Boltzmann | … | 4".
   - `### Error budgets and model form` (line 71). Now: "| `None` keeps discretization `Indicator` | COV-O-VER-4 | 1 |" → Must say: "… | COV-O-VER-4 | 1, 3 (`Gci`) |". FLX: "Solution verification | Calibrated three-level GCI … | FLX-O-ERR-8 | 3".
7. **[low] `Undecided` reason not in ING's rule.** `### Acceptance and review` (lines 603, 621)
   - Now: "checks on models below it are `Undecided { reason: EvidenceBelowPolicy }`." and "| `min_evidence_level` per repository | `Undecided { reason: EvidenceBelowPolicy }` |"
   - Must say: `Undecided { reason: Flagged(EvidenceBelowPolicy) }` in both places.
   - Why: ING owns `Truth` and the decision rule (contract 5). ING's outcome table has no `EvidenceBelowPolicy`; its blocking-flag outcome is "`Undecided { Flagged(flag) }`".
8. **[low] The MFG row omits ratings MFG consumes.** `### What COV provides` (line 815)
   - Now: "| MFG | Process models and envelopes; state Fields; strut-scale Materials from its calibration; environmental records |"
   - Must say: the same row with "; gear, bearing and shaft ratings" before the Types cell.
   - Why: MFG consumes "gear, bearing and shaft ratings" from COV, and COV owns them in 13.4.
9. **[low] Wrong MEC open question.** `## Open questions` (line 903)
   - Now: "which needs the licensed editions (MEC open question 2)."
   - Must say: "which needs the licensed editions (MEC open question 1)."
   - Why: MEC's open question 1 is "Standards data licences"; question 2 lists declined findings.
10. **[low] Change request without its section.** `## Contract change requests` (line 917)
    - Now: "None. CCR-COV-9 (model level and evidence level in the glossary) was accepted in contract v5."
    - Must say: "None. CCR-COV-9 (model level and evidence level in the glossary) was accepted in contract v5 (section 2)."

## KLN

1. **[high] The two-person list lacks AGT's items.** `### Identity and authorization` (D-KLN-41, line 716) and `## Open questions` (line 1020)
   - Now: "auto-merge policy; recipient records; Approvals covering several future transfers; oracle and protected-path changes; purges."
   - Must say: "auto-merge policy; recipient records; `standing_release` plans (D-AGT-33); AGT's `allow_raw_external` and training opt-in; oracle and protected-path changes; purges."
   - Now: "a standing-release class is AGT's to define (D-AGT-30), so this tab names only an Approval covering several future transfers."
   - Must say: "D-KLN-41 lists AGT's `standing_release` (D-AGT-33)."
   - Why: KLN owns the one list ("one list serves every tab"), and AGT owns the items. D-AGT-27: "`api` enforces KLN's one two-person list (D-KLN-41), which includes this tab's items: client and endpoint clearance, standing releases, `allow_raw_external` and training opt-in". Contract 7.6 now names `standing_release`. D-AGT-30 decides `release_data`, not standing releases.
2. **[high] Dotted error code.** The capability tables after `### Failures and Aborts` (line 133) and `### Audit and encryption` (line 756), plus `## Open questions` (line 1021)
   - Now: "| Label propagation | Join per node; hits return values only | `label.write_down` at `api` |" → Must say: "… | `label/write_down` at `api` |"
   - Now: "| Labels and declassification | Confidentiality lattice; integrity by provenance; module labels | `label.write_down` |" → Must say: "… | `label/write_down` |"
   - Now: "Events added; the code form is AGT's, and contract 7.6 still writes `label.write_down` (CCR-KLN-9)." → Must say: "Events added; contract 7.6 now writes `label/write_down` (CCR-KLN-9)."
   - Why: contract 7.6 (v6.1): "Error codes take the form `<family>/<code>`", with `label/write_down` as the example.
3. **[medium] The front-end key includes the compiler release.** `### Graph model` (line 69)
   - Now: "| Front-end stage | Source content hash, language behavior version, compiler release, imported interface hashes (ING) |"
   - Must say: "| Front-end stage | Source content hash, language behavior version, imported interface hashes; diagnostics add the compiler release (ING) |"
   - Why: ING owns the front end. ING `### The Ingot IR and Kiln` says the front end "is keyed by its source hash, the language behavior version and its imports' interface hashes", with diagnostics "also keyed by the compiler release", so IIR is shared across releases.
4. **[medium] Budget error name.** `### Cost and budgets` (lines 181, 192)
   - Now: "an estimate above what remains returns `BudgetExceeded` with cheaper options." → Must say: "an estimate above what remains returns `budget/exceeded` with cheaper options."
   - Now: "| `BudgetExceeded`; `BudgetExhausted` |" → Must say: "| `budget/exceeded`; `BudgetExhausted` |"
   - Why: AGT owns the error namespace. AGT: "A failed reservation returns `budget/exceeded` with cheaper options", in contract 7.6's `<family>/<code>` form.
5. **[medium] UIX's per-user view store is never specified.** `### Changes and refs` (line 386) and `### What this tab provides` (line 903)
   - Now: "and agent branches (`agents/<agent>/<branch>`)." → Must say: "and agent branches (`agents/<agent>/<branch>`). Personal views and layouts live in a per-user store outside Changes (UIX)."
   - Now: "live documents, locks, span provenance, where-used |" → Must say: "live documents, locks, span provenance, where-used, the per-user view store |"
   - Why: UIX (D-UIX-1 text): "Personal views and layouts live in a per-user store that `repo` keeps outside Changes (KLN)". UIX's phase 1 workspace layout needs it, UIX's KLN row requires it, and `repo` is KLN's. KLN never mentions the store.
6. **[medium] The definitional attribute list predates CCR-MEC-1.** `### Revisions and lifecycle states` (line 529)
   - Now: "(GD&T, datums, `HoleSpec`, `ThreadSpec`, `Weld`, finish, plies, region materials)"
   - Must say: "(contract 5's definitional attributes)"
   - Why: contract 5 (v6.1) lists "size tolerances and GD&T, general tolerances, ISO 13715 edge callouts, datums, `HoleSpec`, `ThreadSpec`, `Weld`, surface texture and finish, ply and laminate records, region materials". KLN's copy omits four of them.
7. **[medium] KLN claims every event type.** `` ### `api` methods and events `` (D-KLN-34, line 829)
   - Now: "this tab defines event types and a per-repository `sequence` attribute."
   - Must say: "this tab defines repository, lifecycle and evaluation event types (AGT the `act.*` types) and a per-repository `sequence` attribute."
   - Why: ECO owns the envelope (D-ECO-12) and says "KLN defines repository, lifecycle and evaluation types, AGT the Act types". AGT defines `act.prepared`, `act.approved`, `act.denied` and `act.committed`.
8. **[low] `release_data` is a family, not a class.** `` ### `api` methods and events `` (line 827)
   - Now: "| Act classes `release`, `grant_deviation`, `release_data` and `run_rig_test` |"
   - Must say: "| Act classes `release`, `grant_deviation` and `run_rig_test`, and the `release_data` family |"
   - Why: D-AGT-30 ("one Act family, `release_data { … }`") and KLN's own D-KLN-40. AGT's class table has no `release_data` class.
9. **[low] `crucible:host/parallel` has one function.** `### WIT interfaces` (line 49)
   - Now: "`parallel` offers deterministic map and reduce in input order (PLT)"
   - Must say: "`parallel` offers `map-chunks`, a deterministic map with outputs in input order (PLT)"
   - Why: PLT specifies the interface, whose only function is `map-chunks`.
10. **[low] The reason allowances ship in phase 1 contradicts COV and MEC.** `### Change orders` (line 612)
    - Now: "phase 1 needs it, because GP1's checks are conditional on model form."
    - Must say: "phase 1 ships it with COV's catalogue (D-COV-24), though GP1's and GP2's proof loads supply their checks' model form."
    - Why: COV owns model form. D-COV-3 says "gauged proof loads replace allowances with measured model form". MEC: "Phase 1 releases therefore need no allowance for those quantities."
11. **[low] `SignOff` physics row.** `### Progressive results` (line 169)
    - Now: "| Converged; `Guaranteed` where proven |"
    - Must say: "| `Guaranteed` where proven, else calibrated `Estimated` |"
    - Why: FLX owns physics fidelities. FLX's `SignOff` bounds are "`Guaranteed` where proven, else calibrated `Estimated`". KLN's wording reads as if `SignOff` needs proofs.
12. **[low] "ECO" also abbreviates engineering change order.** `### Change orders` (line 595) and `## State of the art` (line 875)
    - Now: "| Engineering change order (ECO) |" → Must say: "| Engineering change order |"
    - Now: "ECR, ECO and ECN workflows with effectivity" → Must say: "Change request, order and notice workflows with effectivity"
    - Why: every tab uses "ECO" for the interop tab, and contract 2 allows no other codenames.
13. **[low] First-article records claimed by two rows.** `### What this tab provides` (line 904)
    - Now: "orders, MCOs, first-article records, parts policy; the approver directory MFG's gateway pins"
    - Must say: "orders, MCOs, the `Proven` gate on MFG's first-article records, parts policy; the approver directory MFG's gateway pins"
    - Why: MFG's design section specifies the record (`## Quality records: SPC, MSA, FAI and PPAP`, MFG-O-QUAL-2) and provides it to KLN. KLN's own text credits the content "(MFG)" and owns only the state change (D-KLN-38).
14. **[low] Software bill of materials formats.** `### Traceability and compliance` (line 645)
    - Now: "`Software` Items carry a CycloneDX 1.7 software bill of materials per release"
    - Must say: "`Software` Items carry a CycloneDX 1.7 or SPDX 3.0 software bill of materials per release (ELX)"
    - Why: ELX specifies Software items: "SPDX 3.0 or CycloneDX 1.7".
15. **[low] Late-bound fields MEC does not define.** `### Revisions and lifecycle states` (line 535)
    - Now: "MEC's title blocks and markings"
    - Must say: "MEC's title-block fields"
    - Why: MEC: "Title-block fields, revision text, dates and approvers are late-bound release fields". MEC defines no markings.
16. **[low] The COV row omits `min_evidence_level`.** `### What this tab provides` (line 902)
    - Now: "| COV | Evidence records by watermark; label joins; policy allowances; Waivers |"
    - Must say: "| COV | Evidence records by watermark; label joins; policy allowances and `min_evidence_level`; Waivers |"
    - Why: COV requires it from `repo`, and policy records are KLN's (contract 5).
17. **[medium] Change requests still written as pending.** `## Contract change requests` (lines 1027 to 1029)
    - Now: "- CCR-KLN-6 to CCR-KLN-8 (Evidence records without geometry, Item, merge verdict order): accepted in contract v5." → Must say: the same line ending "accepted in contract v5 (sections 2, 2 and 7.1 `repo`)."
    - Now: the bullet beginning "- CCR-KLN-9, error-code form (7.6)." → Must say: "- CCR-KLN-9, error-code form: accepted with CCR-AGT-12 and CCR-ECO-11 in contract v6.1 (section 7.6)."
    - Now: the bullet beginning "- CCR-KLN-10, catalog parts in `ItemDefinition` (5)." → Must say: "- CCR-KLN-10, catalog parts in `ItemDefinition`: accepted in contract v6.1 (section 5, `ItemDefinition`)."
    - Why: contract 16 and 17. The edit saves about 55 words, which pays for items 1, 3, 5 and 7.

## MEC

1. **[high] GD&T is not an attribute carried through operations.** `### Specification model` (D-MEC-27, lines 742 and 744)
   - Now: "and GD&T and PMI attributes use Anvil's split policy `Fail`." → Must say: "and no GD&T or PMI item travels through operations as an attribute (D-ANV-32)."
   - Now: "ANV keeps `Note::AttributeSplit` on the operation, and MEC owns the failure." → Must say: "ANV writes the resolved targets into the definition part, and MEC owns the failure."
   - Why: contract 5 tags design attributes [ANV] and puts a forwarded tolerance on "an anchored aspect query, re-resolved on the final Part". ANV: "Size tolerances, GD&T and datums are not carried through operations." The decision keeps its round 3 marker.
2. **[medium] Instance sets phased before ING's.** `### Mate inference and assembly-level features` (line 508)
   - Now: "| `instance`, `assembly`, Instance sets, `#[configuration]` existence | `ResolveError` on a mate frame; `ING2601` | MEC-O-AS-1 | 1 |"
   - Must say: the same row ending "| MEC-O-AS-1 | 1, 2 (Instance sets) |"
   - Why: ING owns Instance sets: "| Instance sets | … | ING-O-30 | 2 |". 13.4: a row naming another tab's capability is no earlier than the owner's row. MEC's own Fasteners row is phase 2.
3. **[medium] Changing internal operations is not a major version.** `### Roles, queries and fixes` (line 59)
   - Now: "A std feature that changes its internal operations therefore takes a major version (ING)."
   - Must say: "A std feature that changes its internal operations therefore releases as a labelled output-changing minor version (ING, D-ECO-14)."
   - Why: ING owns what breaks. Its table says changing "the entity names a public feature produces on the package's test designs" is "Minor, labelled output-changing (D-ECO-14)".
4. **[medium] `Weld` carries the quality level; the Part carries the execution class.** `### Shared types` (line 45) and `## Interfaces with other subsystems` (line 973)
   - Now: "`Weld` with its execution class, surface texture" → Must say: "`Weld` with its quality level, weldment `execution_class`, surface texture"
   - Now: "`Weld` with execution class; edge callouts;" → Must say: "`Weld` with quality level; weldment `execution_class`; edge callouts;"
   - Why: round 2's ruling: MEC "records the weld quality level on `Weld`". MEC's own text: "A `Weld` records … the imperfection quality level … A weldment Part records `execution_class`". MFG requires "`Weld` with quality level and execution class".
5. **[medium] FLX's calibration class ids.** `## Design checks` (lines 895 to 897)
   - Now: "| Elasticity regularized peak, aggregated CutFEM, p = 2 to 6 |" → Must say: "| `elasticity.peak` |"
   - Now: "| Beam-lattice localized strut stress |" → Must say: "| `lattice.strut_stress` |"
   - Now: "| Linear buckling factor, eigenvalue DWR, beam lattice; an octree variant |" → Must say: "| `lattice.buckling`; `elasticity.eigen` |"
   - Why: FLX owns the classes and names them in its "Phase 1 class" table. COV 1 aligns COV to the same ids.
6. **[medium] A phase 1 oracle tests KLN's phase 3 BOM.** `## Oracles` (MEC-O-PF-12, line 1013)
   - Now: "`#[configuration]` gives the expected 150% BOM"
   - Must say: "each `#[configuration]` variant builds as declared; KLN-O-PLM-5 checks the 150% BOM"
   - Why: the same reason as ING 5. KLN's 150% BOM row is phase 3, and MEC-O-PF-12 backs a phase 1 row.
7. **[medium] Interface rows omit what ANV and ING require.** `## Interfaces with other subsystems` (lines 968, 969)
   - Now: "| Constraint semantics; definitional attribute classes |" → Must say: "| Constraint semantics; definitional attribute classes; `FeatureRole` aliases; PMI as anchored aspect queries with `pmi_target_resolved`; the Assembly identity encoding |"
   - Now: "`std::standards::iso286`; `default_distribution`; general tolerances |" → Must say: "`std::standards::iso286`; `default_distribution`; general tolerances; `pmi_target_resolved`; `std::mech::refgeom`; `fasten` returning an Instance set; name-free Part and Assembly encodings |"
   - Why: ANV's "Anvil requires" row and ING's "Ingot requires" row ask for exactly these. MEC specifies each in its design sections (D-MEC-27, `std::mech::refgeom`, contract 5's Assembly `GeometryId` [MEC]).
8. **[low] Wrong merge condition.** `### Interference and clearance` (line 452) and `## Interfaces with other subsystems` (line 970)
   - Now: "KLN's merge condition 5 reuses these classes." → Must say: "KLN's merge condition 4 reuses these classes."
   - Now: "approved parts; merge condition 5 |" → Must say: "approved parts; merge conditions 4 and 5 |"
   - Why: KLN's condition 4 is "**Interference.** A `Hard` interference (positive volume, in MEC's classes)". The designed-contact exemption covers "conditions 4 and 5".
9. **[low] Wrong ANV failure name.** `### Machine elements` (line 376)
   - Now: "| `TopologyChange { faces }`; `RuleConflict { set }` |"
   - Must say: "| `TopologyChangeRejected`; `RuleConflict { set }` |"
   - Why: ANV's `move_faces`, `replace_faces` and `delete_faces` fail with `TopologyChangeRejected`. `TopologyChange` is `anvil::shape_velocity`'s failure.
10. **[low] Attributes are keyed by canonical number.** `### Shared types` (line 39)
    - Now: "| Manufacturing intent | Definitional attributes keyed by `EntityId` |"
    - Must say: "| Manufacturing intent | Definitional attributes by canonical entity number |"
    - Why: contract 5: definitional attributes "are encoded name-free by canonical entity number". MEC's own line 45 says so.
11. **[low] D-ANV-30 does not decide cut modes.** `### Mate inference and assembly-level features` (line 504)
    - Now: "while `AfterAssembly` is a manufacturing operation in the MBOM (D-ANV-30)."
    - Must say: "while `AfterAssembly` is a manufacturing operation in the MBOM; created ids carry the Instance path (ANV)."
    - Why: D-ANV-30 decides copy relabelling. ANV's `### Copies and placements` says "assembly-level features prefix ids with the Instance path".
12. **[low] Edit plans are UIX's.** `### Drawings` (D-MEC-36, line 833)
    - Now: "writes model source through ING's edit plans."
    - Must say: "writes model source through UIX's edit plans (D-UIX-15)."
    - Why: D-UIX-15: "Gestures edit source through ranked edit plans". ING provides only the ranking ("Derivatives serve UIX's edit plans").
13. **[low] Biomechanics models are COV's.** `## Human factors` (line 911)
    - Now: "strength and musculoskeletal loading need Flux biomechanics models"
    - Must say: "strength and musculoskeletal loading need COV's biomechanics models"
    - Why: COV's `### Biomechanics and human factors` holds those models, and FLX says COV owns physics models.
14. **[medium] Change request still written as pending.** `## Contract change requests` (line 1107)
    - Now: "- **CCR-MEC-1.** Contract 5's list of definitional attributes adds general tolerances (D-MEC-35) and edge callouts to ISO 13715. Both change what is made, so changing either must mark the Item modified, and the contract's list is explicit."
    - Must say: "- CCR-MEC-1, general tolerances and ISO 13715 edge callouts as definitional attributes: accepted in contract v6.1 (section 5)."
    - Why: contract 17: "CCR-MEC-1 definitional attributes | Accepted (5)". The edit saves about 20 words.

## MFG

1. **[high] 3MF Toolpath writer phase.** `## Printers, 3MF and print transfer` (lines 461, 452)
   - Now: "| Further 3MF extensions | Toolpath (2); Boolean, Volumetric and Secure Content (3), through ECO's writer | Written only where the target declares support | MFG-O-AM-10 | 2, 3 |"
   - Must say: "| Further 3MF extensions | Boolean, Volumetric and Secure Content (3), and Toolpath once a machine partner accepts it (3), through ECO's writer | Written only where the target declares support | MFG-O-AM-10 | 3 |"
   - Now: "the Toolpath extension, updated on 17 September 2026, is still a draft" → Must say: "the Toolpath extension is at 1.0.0 in ECO's catalog". The editor re-opens the 3MF specification page before citing the date.
   - Why: ECO owns every writer, its version and its phase (round 2 ruling). ECO's 3MF row: "Toolpath 1.0.0 … 3 (others; Toolpath once MFG's partner accepts it)". MFG's own PBF scan-vector work is phase 4.
2. **[high] The OPC UA allowlist precedes its transport.** `## Approval, transfer and physical safety` (line 141)
   - Now: "| Wire-level transfer verification | Manifest allowlists enforced in the gateway core; the OPC UA method allowlist | Other requests dropped and reported | MFG-O-SAFE-3 | 2 |"
   - Must say: "| Wire-level transfer verification | Manifest allowlists enforced in the gateway core (2); the OPC UA method allowlist (3) | Other requests dropped and reported | MFG-O-SAFE-3 | 2, 3 |"
   - Why: MFG's own "MTConnect and OPC UA adapters" row is phase 3 (MFG-O-FAC-2), and ECO's OPC UA for Machine Tools row is phase 3. This pairs with AGT 1.
3. **[medium] D-MFG-30 contradicts D-COV-27.** `## Scope, layering and core types` (line 20)
   - Now: "A parameter that depends on machine, mould, tooling or process window, such as melt-to-mould heat transfer, is MFG process data citing COV's model id."
   - Must say: "A property of the material in a stated condition stays COV's even when the condition names a process or machine; a parameter of material and equipment together, such as melt-to-mould heat transfer, is MFG process data citing COV's model id." End the decision with "(revised in round 3)".
   - Why: `Material` is [COV] in contract 5. D-COV-27: "A property of the material in a stated condition is a COV `Material` property, even when the condition names a process and machine." MFG's "process window" clause would hand per-machine strut Materials to MFG, while MFG itself says COV builds them.
4. **[medium] RoHS phased before KLN's compliance roll-up.** `## Sustainability and compliance` (line 692)
   - Now: "from COV's declared substances (2);"
   - Must say: "from COV's declared substances (3);". The row's Phase cell becomes "3".
   - Why: KLN owns the check over rolled-up compositions ("This tab owns compositions rolled up from `Material` versions"), and its "Compliance checks" row is phase 3. MFG supplies the substance rules. No phase 2 gate needs RoHS. This is judgment call 3 in the summary.
5. **[medium] Hele-Shaw is MFG's, not Flux's.** `### What MFG consumes` (line 748) and `### What MFG provides` (line 763)
   - Now: "level-set flow and Hele-Shaw" → Must say: "level-set flow with wall resolution"
   - Now: "coupon data for inherent strain, weld joints and as-built struts; process data under D-MFG-30 |" → Must say: "coupon data for inherent strain, weld joints and as-built struts; process data under D-MFG-30; the Hele-Shaw solver (D-MFG-15) |"
   - Why: MFG owns injection moulding (13.4), decides Hele-Shaw (D-MFG-15) and verifies it (MFG-O-MOLD-3). COV requires "the Hele-Shaw solver" from MFG. FLX provides MFG only "filling flow with wall resolution".
6. **[low] Springback from Flux arrives in phase 5.** `## Sheet cutting, nesting and press brake` (D-MFG-8, line 291)
   - Now: "springback from Flux or measurement."
   - Must say: "springback from measurement, and from Flux once sheet forming lands (phase 5, contract 13.4)." End the decision with "(revised in round 3)".
   - Why: 13.4: "Sheet forming simulation and springback compensation | 5 | None | MFG", while press-brake allowances keep phase 2.
7. **[low] Quality level is recorded on `Weld`.** `## Welding, joining and composites` (line 521)
   - Now: "MFG derives the quality level, NDT extent and ISO 3834 part from it"
   - Must say: "MFG derives the NDT extent and ISO 3834 part from it and checks each `Weld`'s quality level (MEC) against it"
   - Why: round 2's ruling and MEC's text put the quality level on `Weld` (see MEC 4).
8. **[low] Ply nesting phase is ambiguous.** `## Welding, joining and composites` (line 535)
   - Now: "Plate machining (3); MEC plies nested with grain; ordered plies with projector data (4)"
   - Must say: "Plate machining (3); MEC plies nested with grain and ordered, with projector data (4)"
   - Why: MEC owns composite laminates at phase 4 (13.4), so no ply work can read as phase 3.
9. **[medium] Change requests without their ruling or section.** `## Contract change requests` (lines 927, 928) and `## Open questions` (line 919)
   - Now: "- CCR-MFG-7, controller capture: contract 13.2's reference-shop agreement adds time on each family's physical controls in program-test mode (R10-29). Without it no post family can qualify." → Must say: "- CCR-MFG-7, controller capture: accepted in contract v6.1 (section 13.2)."
   - Now: "- Earlier: CCR-MFG-5 and CCR-MFG-6 were accepted in contract v5, and the machine gateway request in v6 (contract 12)." → Must say: "- Earlier: CCR-MFG-5 and CCR-MFG-6 were accepted in contract v5 (sections 2 and 7.6; 7.1), and the machine gateway request in v6 (section 12)."
   - Now: "R10-29's capture time in the reference-shop agreement is CCR-MFG-7." → Must say: "R10-29's capture time is in contract 13.2's reference-shop agreement (CCR-MFG-7)."

## ELX

1. **[high] Piezo actuators precede Flux's and COV's piezo models.** `### Sensors and drives` (line 651) and `### Electric machines` (line 637)
   - Now: "| Actuators | Force maps and lumped equivalents | As machine maps | ELX-O-MCH-2 | 4 |" → Must say: "| Actuators | Force maps and lumped equivalents (4); piezo stacks (5) | As machine maps | ELX-O-MCH-2 | 4, 5 |"
   - Now: "piezo stacks use Flux's piezoelectric model with a Butterworth-Van Dyke lumped equivalent." → Must say: "piezo stacks use Flux's piezoelectric model with a Butterworth-Van Dyke lumped equivalent from phase 5."
   - Why: FLX: "Piezoelectric and electrostatic MEMS | … | 5". COV's piezoelectric devices row is "5 · Nat". 13.4 forbids a row earlier than a capability it names.
2. **[medium] A lumped DC motor before electrical DAEs.** `### Sensors and drives` (lines 654, 643)
   - Now: "| Drivetrain coupling | ELX's drivetrain elements with ideal sources or a lumped DC motor in one Network | Port domain mismatch is a compile error | ELX-O-NET-3 | 2 |" → Must say: "| Drivetrain coupling | ELX's drivetrain elements with ideal sources (2) or a lumped DC motor (3) in one Network | Port domain mismatch is a compile error | ELX-O-NET-3 | 2, 3 |"
   - Now: "ELX's drivetrain elements let GP3's gearbox and a lumped motor form one drivetrain from phase 2." → Must say: "ELX's drivetrain elements let GP3's gearbox and ideal sources form one drivetrain from phase 2, with a lumped motor from phase 3."
   - Why: FLX: "`flux::solve_dae` | … | 2 (mechanical, thermal), 3 (electrical)". ELX's own electrical element library is phase 3.
3. **[medium] `CatalogSelection` is needed at GP3.** `### Creating and migrating catalog parts` (line 284)
   - Now: "| `CatalogSelection` | Pure over pinned definitions and offers; re-resolves when arguments change; recorded as `resolved:` once the layout is released | `SelectionError::NoCatalogMatch` with nearest candidates; `SelectionChangesLandPattern` | ELX-O-CAT-3 | 3 |"
   - Must say: the same row ending "| ELX-O-CAT-3 | 2 (selection over pinned definitions), 3 (offers, land patterns, layout release) |"
   - Why: ELX owns the type (D-ELX-3). 13.4 lands a capability at the first gate that needs it. That gate is GP3 in phase 2: ING's "Catalog selections" row and `bearing_62xx` example, and MEC's "Approved-parts selection", are both phase 2. This is judgment call 2 in the summary.
4. **[medium] Datasheet extraction runs quarantined.** `### Creating and migrating catalog parts` (line 272)
   - Now: "The datasheet is untrusted text, so the context is `instruction_tainted` and the values `data_untrusted` (contract sections 5 and 7.6); a human approves."
   - Must say: "AGT's quarantined `std::agents::extract` reads the datasheet, so the values are `data_untrusted` and the agent's context stays clean (D-AGT-25); a human approves."
   - Why: AGT owns context labels and extraction: "`std::agents::extract` runs a model with no tools and no other context that fills a templated Ingot record, schema-validated, range-checked and `data_untrusted`". AGT's ELX row provides "datasheet extraction, labelled `data_untrusted`".
5. **[low] A dotted name for KLN's check.** `### Creating and migrating catalog parts` (line 286)
   - Now: "`policy.unapproved_part` fails unless a Waiver names the part"
   - Must say: "KLN's parts-policy check fails unless a Waiver names the part"
   - Why: KLN owns the check ("Parts policy | … | Policy check fails without a Waiver | KLN-O-PLM-11"). Waivers name `CheckId`s, and the dotted form reads as an `api` method (contract 7.6).
6. **[low] Benches are KLN's physical-test runners.** `### Hardware-in-the-loop and flashing` (line 696)
   - Now: "bench adapters are external programs talking to `api`."
   - Must say: "benches run as KLN's enrolled physical-test runners (D-KLN-35) talking to `api`."
   - Why: contract 7.1: "Physical tests are Acts that run on hardware rigs". KLN owns runner enrolment and the TPM-signed Evidence record (D-KLN-35, `apps/rig-runner` in contract 12).
7. **[medium] Change request without its section.** `## Contract change requests` (line 1058)
   - Now: "None. CCR-ELX-8, the battery swelling and abuse rows, was accepted in contract v5."
   - Must say: "None. CCR-ELX-8, the battery swelling and abuse rows, was accepted in contract v5 (section 13.4)."

## AGT

1. **[high] `store_machine_job` precedes its OPC UA path.** `## Acts and approvals` (lines 880, 940)
   - Now: "| `store_machine_job` | Physical effect | OPC UA job `Store` only | Revocable before start | 2 |" → Must say: the same row ending "| 3 |"
   - Now: "These classes ship with MFG's transfers in phase 2, and `flash_device` with ELX's Software items in phase 3." → Must say: "These classes ship with MFG's transfers in phase 2, `store_machine_job` with the OPC UA path in phase 3, and `flash_device` with ELX's Software items in phase 3."
   - Why: ECO owns the codec and its phase: "OPC UA for Machine Tools | … | R; jobs only by `store_machine_job` | Machine state | 3". MFG's OPC UA adapters are phase 3. Under 13.4 an Act cannot precede its transport. The CAM programmer role (line 482) can prepare it only from phase 3. This is judgment call 1 in the summary.
2. **[high] `Authenticator` serves every client.** `## Acts and approvals` (line 890)
   - Now: "so PLT's `Authenticator` serves only Crucible's own cloud."
   - Must say: "so every client, Crucible's cloud included, approves in this browser session, which PLT's `Authenticator` opens (D-PLT-41)."
   - Why: PLT owns `Authenticator`: it "opens the approval page of contract 7.6 for one request id … It never handles a credential". D-PLT-41: "Every client approves in a browser on the approval origin". The current wording implies in-app WebAuthn for the cloud.
3. **[medium] Preemption restated against KLN's table.** `### Scheduling on Kiln workers` (lines 601, 602)
   - Now: "| `Interactive` | Sessions where a human is waiting, drag streams included | Never preempted |" → Must say: "| `Interactive` | Sessions where a human is waiting, drag streams included | Only by drags, at node boundaries (KLN) |"
   - Now: "| `Agent` | Agent sessions | By `Interactive`, at Op boundaries |" → Must say: "| `Agent` | Agent sessions | By `Interactive`, at node boundaries (KLN) |"
   - Why: AGT owns `PriorityClass` values, and Kiln owns scheduling ("Kiln owns Op scheduling"). KLN's table preempts non-drag `Interactive` work by drags "at node boundaries", and `Agent` by "Both above, at node boundaries".
4. **[medium] Interface rows name the drag methods and the stability analysis.** `### What AGT provides` (lines 1088, 1090, 1092) and `### What AGT requires` (line 1103)
   - Now: "| ING | `SourcePatch` application; drag streams under `LiteralSite` overrides;" → Must say: "| ING | `SourcePatch` application; `evaluate.subscribe` and `edit.stream` under `LiteralSite` overrides;"
   - Now: "| UIX | `inspect.render`, `inspect.ask_render`; drag streams;" → Must say: "| UIX | `inspect.render`, `inspect.ask_render`; `evaluate.subscribe` and `edit.stream`;"
   - Now: "| ELX | `flash_device`; datasheet extraction, labelled `data_untrusted`; budget caps for long tool runs |" → Must say: "| ELX | `flash_device`; `edit.stream` and `edit.apply`; datasheet extraction, labelled `data_untrusted`; budget caps for long tool runs |"
   - Now: "the stability analysis reporting `RankSwap`;" → Must say: "`anvil::query_stability` reporting `RankSwap`;"
   - Why: ING, UIX and ELX require these methods by name, and AGT's catalog defines them (phase 1). ANV names the analysis `anvil::query_stability` (D-ANV-34, phase 1).
5. **[medium] KLN's review record and Asset identity.** `## Method catalog` (line 339) and `### The Proposal object` (lines 635, 638)
   - Now: "| `propose.review` † | Verdict, findings → `Review` |" → Must say: "| `propose.review` † | Verdict, findings → KLN's `ReviewVerdict` |"
   - Now: "pub reviews: Vec<Review>," → Must say: "pub reviews: Vec<ReviewVerdict>,"
   - Now: "pub snapshots: Vec<AssetId>," → Must say: "pub snapshots: Vec<ObjectId>,"
   - Why: KLN defines "`Comment`, `ReviewVerdict` | Review records on a Proposal", and UIX agrees. `AssetId` exists nowhere else; Assets are content-addressed (contract 2).
6. **[medium] The render request rebuilds `ViewState`.** `### Snapshots and Field overlays` (line 381)
   - Now: "pub style: Style,                    // Shaded | HiddenLine | Wire | XRay"
   - Must say: "pub style: DisplayStyle,             // UIX's: Shaded, HiddenLine, Wireframe, XRay …". Also add one sentence after the code block: "The server resolves each request to a UIX `ViewState`, so a Snapshot is a `ViewState` under a `RenderProfile` (contract 2)."
   - Why: contract 5 makes `ViewState` [UIX] the one camera, visibility, section and Field-display record "used by the UI, agents, snapshots". Contract 2 defines a Snapshot from it. UIX's style type is `DisplayStyle`, with `Wireframe`.
7. **[medium] Methods other tabs need that the catalog lacks.** `## Method catalog` (lines 286, 296, 301). The method names are AGT's choice.
   - After "| `read.symbols` | Query → path, kind, signature, doc URI | — | AGT-O-16 | 1 |", add a Read method that carries ING's LSP 3.17 requests (completion, hover, inlay hints, semantic tokens, code actions) at a Change, phase 1. ING says "The UI and agents reach it through `api`", UIX's phase 1 code panel needs it, and D-AGT-1 maps every UI command to one method.
   - After "| `read.catalog` | Filters → catalog part summaries |", add a Read method for COV's coverage map and limit records, phase 0. COV's "Coverage map" row (phase 0) promises "`api` Read methods", and AGT requires the map from COV.
   - After "| `session.status` | Handle → head, grant, context label, usage, open Evaluations | `session/expired` | AGT-O-1 | 0 |", add a Session method for a typed question to the delegating human, and name the events the agent panel reads. UIX requires "agent events" and "questions" from AGT ("Agents ask through typed question cards whose answers return as typed data"), and AGT defines neither.
8. **[medium] The canonical bracket description misreads ING's decision rule.** `### Sections and descriptions` (line 417)
   - Now: "Checks: 1 of 1 `Pass` at `Interactive`. Regularized peak von Mises stress away from the clamp: 112 MPa ± 9 MPa (`Estimated`) against 165.6 MPa, margin 27% at the bound."
   - Must say: "Checks: 1 of 1 provisional `Pass` at `Interactive`, conditional on model form. Regularized peak von Mises stress away from the clamp and loaded face: 112 MPa ± 20 MPa (`Estimated`) against 144 MPa, margin 8% at the bound."
   - Why: ING owns the rule and the worked example: "a limit of 144 MPa to 165.6 MPa", and "`Interactive`: 112 MPa ± 20 MPa … a provisional `Pass { conditional_on: [model form] }`". Contract 6's region excludes "the clamp and the loaded face".
9. **[low] Invalid query syntax.** `### Geometry queries` (line 365)
   - Now: "`part.faces(normal: +z, area > 100mm2)`"
   - Must say: "`part.faces(normal: +z, area: 100mm2..)`"
   - Why: ING owns the syntax ("`area: 100mm2..`"), and contract 6 requires examples to follow Ingot's grammar.
10. **[low] Lane, credential and CLI names.** `### Drag streams` (line 181), `## Method catalog` (line 326), `### What AGT requires` (line 1111)
    - Now: "runs them on PLT's interactive pool lane." → Must say: "runs them on PLT's `Interactive` pool lane."
    - Now: "a frame stream on the interactive lane" → Must say: "a frame stream on Kiln's drag lane"
    - Now: "| PLT | Transport, `cli` exit codes, `Usage` measurement; keychain; the stdio MCP sandbox; the interactive pool lane; browser sessions and `Authenticator` |" → Must say: "| PLT | Transport, `Usage` measurement; `CredentialStore`; the stdio MCP sandbox; the `Interactive` pool lane; browser sessions and `Authenticator` |". Add "CLI exit codes;" to the ECO row.
    - Why: PLT defines `enum PoolLane { Interactive, Foreground, Background }` and maps "AGT's interactive `PriorityClass` to `Foreground`", so a lowercase "interactive lane" is ambiguous. PLT's credentials type is `CredentialStore`. ECO specifies the exit codes ("Exit codes are 0 success, 1 Check failures, …"); PLT never does.
11. **[low] OPC UA method count.** `## Acts and approvals` (line 936)
    - Now: "The other eight job methods are uncallable [S69]."
    - Must say: "Every other job method is uncallable [S69]."
    - Why: MFG owns the allowlist: "ISA-95 Job Control defines eleven job-order methods". Eleven less the four named leaves seven.
12. **[low] The `panel` world is UIX's.** `### Native SDKs and WIT` (line 257)
    - Now: "`crucible:api` serves ECO's panel, tool and connector worlds"
    - Must say: "`crucible:api` serves UIX's `panel` world and ECO's tool and connector worlds"
    - Why: round 2's ruling: "UIX owns them: … worlds `panel`, `canvas2d`".
13. **[low] UIX calls it the Proposal view.** `### Human review and separation of duties` (line 674) and `### What AGT requires` (line 1106)
    - Now: "UIX's review view" → Must say: "UIX's Proposal view"
    - Now: "| UIX | The renderer `apps/headless-render` links, with `RenderProfile`; the review view;" → Must say: "… with `RenderProfile`; the Proposal view;"
    - Why: UIX's capability row and its AGT row name it "the Proposal view".
14. **[medium] Change requests still written as pending.** `## Acts and approvals` (line 912), `## Open questions` (lines 1162, 1163), `## Contract change requests` (lines 1171 to 1174)
    - Now: "since Acts have no risk class (CCR-AGT-11)." → Must say: "since Acts have no risk class (contract 7.6)."
    - Now: "so the bootstrap is CCR-AGT-13." → Must say: "so contract 13.2 runs the `WorkItem` record over Git until then (CCR-AGT-13)."
    - Now: "CCR-AGT-10 asks contract section 7.6 to say so." → Must say: "contract section 7.6 says so (CCR-AGT-10)."
    - Now: the four bullets beginning "- **CCR-AGT-10.** Standing releases.", "- **CCR-AGT-11.** AAL3 for Acts.", "- **CCR-AGT-12.** Error codes." and "- **CCR-AGT-13.** Build-program bootstrap." → Must say: "- **CCR-AGT-10.** Standing releases: accepted in contract v6.1, section 7.6." / "- **CCR-AGT-11.** AAL3 for Acts: accepted in contract v6.1, section 7.6." / "- **CCR-AGT-12.** Error codes: accepted with CCR-KLN-9 and CCR-ECO-11 in contract v6.1, section 7.6." / "- **CCR-AGT-13.** Build-program bootstrap: accepted in contract v6.1, section 13.2."
    - Why: contract 17 rules on all four. The edit saves about 110 words, which pays for items 6 and 7.

## UIX

1. **[medium] The join table is the face table.** `### Display data` (line 210), `### Large assemblies and picking` (line 243), the capability table after `### Snapshots` (line 313), `### What UIX requires` (line 916)
   - Now: "The renderer maps them to `EntityId`s through the Body's name table, keyed by the Body's `ObjectId`." / "maps to the design's `EntityId` through the name table." / "Name-free `DisplayPackage`s joined to the name table;" / "`anvil::cluster_dag` from phase 2; the Body's name table;"
   - Must say: "face table" in place of "name table" in each.
   - Why: contract 5 `DisplayPackage` [ANV, UIX] joins canonical numbers to `EntityId`s "through the Body's face table". ANV's `anvil::tessellate` row and ANV's UIX row say "face table". ANV's line 124 uses "name table" for derived artifacts in general.
2. **[medium] Forward-mode derivatives are phase 2.** `### From gesture to Ingot edit` (line 413)
   - Now: "ING's forward-mode derivatives solve for the free literal from phase 1."
   - Must say: "ING's forward-mode derivatives solve for the free literal from phase 2."
   - Why: ING owns derivatives: "| Derivatives | Dependence and provenance ranking (1); forward and reverse modes (2) |". If UIX needs this in phase 1, ING moves forward mode instead.
3. **[medium] `Authenticator` opens the approval session.** `## Open questions` (line 1008)
   - Now: "so no approval runs in the app's process or through PLT's `Authenticator`."
   - Must say: "so no approval runs in the app's process; PLT's `Authenticator` only opens that session (D-PLT-41)."
   - Why: PLT: "`Authenticator` opens the approval page … It never handles a credential", and "only UIX's approval flow may call `Authenticator`".
4. **[medium] 3D mice use PLT's `NavDeviceEvent`.** `### Devices` (D-UIX-31, line 677), `### Localization and units` (line 724), `### What UIX requires` (line 924)
   - Now: "through PLT's `DeviceIo` on every desktop OS" / "| 3D mice | HID through `DeviceIo`; WebHID in Chromium |" / "clipboard flags, `DeviceIo`, hardware profile"
   - Must say: `NavDeviceEvent` in place of `DeviceIo` in each.
   - Why: PLT owns `platform-api`. It reads "6-DoF devices | `NavDeviceEvent` from HID", and "`DeviceIo` opens serial and USB ports outside evaluation for MFG's machine gateway and ELX's bench adapters".
5. **[medium] A render is instruction-capable, not `instruction_tainted`.** The capability table after `### Snapshots` (line 308)
   - Now: "A render showing geometry or appearance from an untrusted Asset is `instruction_tainted`, and agents"
   - Must say: "A render is instruction-capable when imported appearance or any visible Body derives from an untrusted node (D-AGT-26), and agents"
   - Why: AGT owns the labels. D-AGT-26 and contract 7.6 make a Snapshot "instruction-capable". `instruction_tainted` is the context flag that reading one sets, and a merged Asset's geometry is trusted (contract 5 `Labels`).
6. **[low] Bode charts arrive after ELX's phase 3 AC analysis.** `## Field views` (lines 370, 380) and `### What UIX provides` (line 905)
   - Now: "| Bode, Smith and eye diagrams | Fields over frequency, and folded time | 4 |" → Must say: "… | 3 (Bode), 4 |"
   - Now: "| UIX-O-FIELD-1 | 2 (waveforms); 4 |" → Must say: "| UIX-O-FIELD-1 | 2 (waveforms); 3 (Bode); 4 |"
   - Now: "waveform, Smith and eye charts" → Must say: "waveform, Bode, Smith and eye charts"
   - Why: ELX's AC, noise and loop-stability rows are phase 3 (GP5), and ELX requires "waveform, Bode, Smith and eye charts" from UIX. 13.4 lands a capability at the first gate that needs it.
7. **[low] Credential enrolment comes from PLT.** `### What UIX requires` (lines 920, 924)
   - Now: "the approval page's content; credential enrolment; `session.control`" → Must say: "the approval page's content; `session.control`". Add "credential enrolment" to the PLT row after "the approval browser session and `crucible://` callback".
   - Why: PLT specifies "WebAuthn | Approval and enrollment in a browser session (D-PLT-41)". AGT specifies no enrolment.
8. **[low] No hosted agent before phase 2.** `### Agents` (line 542), `### Handles, push-pull and sketching` (line 453), `## Design system and onboarding` (line 777)
   - Now: "goes to the default agent, and the palette says so first." / ""Constrain fully" asks an agent for an `EditPlan` preview." / "Unknown term: the palette offers the agent"
   - Must say: "goes to the hosted crew (phase 2), and the palette says so first." / ""Constrain fully" asks the hosted crew (phase 2) for an `EditPlan` preview." / "Unknown term: the palette offers the crew (phase 2)"
   - Why: AGT's "Hosted crew | `apps/crew` … | AGT-O-15 | 2", and contract 13.2 defers it. Phase 1 agents run in external MCP hosts, which the server cannot prompt.
9. **[low] The results example disagrees with ING's numbers.** `### Studies and results` (line 593)
   - Now: "beyond 8 mm from the clamp: `Pass`, margin 18% (`Estimated`, ±4%)"
   - Must say: "beyond 8 mm from the clamp and loaded face: conditional `Pass` at `SignOff`, margin 17% at the bound (`Estimated`, ±1.5 MPa)"
   - Why: ING's `SignOff` row is "118 MPa ± 1.5 MPa" → "`Pass { conditional_on: [model form] }`" against 144 MPa, and contract 6's region excludes the loaded face.
10. **[medium] Change requests still written as pending.** `### GPU capability tiers` (line 187), `## Open questions` (line 1011), `## Contract change requests` (lines 1019, 1020)
    - Now: "a measured capacity in the graphics popover (CCR-UIX-8)." → Must say: "a measured capacity in the graphics popover (contract 13.3)."
    - Now: "- R8-18 and R12-28, applied in this tab. The contract's own wording is CCR-UIX-7 and CCR-UIX-8." → Must say: "- R8-18 and R12-28, applied in this tab and in contract 5 and 13.3 (CCR-UIX-7, CCR-UIX-8)."
    - Now: the bullet beginning "- **CCR-UIX-7, name-free `DisplayPackage` (contract 5).**" → Must say: "- CCR-UIX-7, name-free `DisplayPackage`: accepted with CCR-ANV-9 in contract v6.1 (section 5)."
    - Now: the bullet beginning "- **CCR-UIX-8, `compute_raster` capacity (contract 13.3).**" → Must say: "- CCR-UIX-8, `compute_raster` capacity: accepted in contract v6.1 (section 13.3)."
    - Why: contract 17 rules on both. The edit saves about 70 words, which UIX's 19 words of room need for items 5 and 6.

## ECO

1. **[high] An Act class that does not exist.** `### Enterprise connectors` (line 579)
   - Now: "where the external system is the only approver, the Act is `publish_to_system_of_record` (KLN)."
   - Must say: "where the external system is the only approver, the release Act's Approval covers only the publication, and the release record says "approved externally" (KLN)."
   - Why: AGT owns Act classes, and its table has no such class. KLN owns the policy (D-KLN-39): "that Approval covers only the publication", and its open question 5 says "Applied without a new Act name".
2. **[high] Release drawings are PDF/A-2u.** `### Mechanical CAD and product data` (line 171)
   - Now: "PDF 2.0; SVG 1.1 Second Edition [SVG 1.1]; PDF/A-4, ISO 19005-4:2020 [PDF/A wiki]"
   - Must say: "PDF 2.0; SVG 1.1 Second Edition [SVG 1.1]; PDF/A-2u (ISO 19005-2:2011) for release drawings and PDF/A-4 (ISO 19005-4:2020) as MEC's option [PDF/A wiki]"
   - Why: ECO owns writers, but MEC's design section fixes the release format: "Release drawings are PDF/A-2, conformance level u (ISO 19005-2:2011) … PDF/A-4 … is an option". ECO's row names MEC as the format's owner, and GP1's phase 1 drawings need it.
3. **[high] Operations that do not exist.** `## Interfaces with other subsystems` (lines 935, 937)
   - Now: "`crucible:geom` and `anvil::measure_*`" → Must say: "`crucible:geom`; `anvil::mass_properties`, `distance` and `deviation`"
   - Now: "`crucible:field` and `flux::sample`" → Must say: "`crucible:field` and `flux::field_sample`"
   - Why: ANV's measures are `anvil::mass_properties`, `anvil::distance` and `anvil::deviation`; FLX's catalog names `field_sample`. Both are reached through `crucible:ops`, as ECO's own D-ECO-7 requires (see ANV 2 and FLX 2).
4. **[medium] Netlist writers ELX needs.** `### Electronics` (lines 204, 208)
   - Now: "| KiCad files | S-expression formats [KiCad formats] | R; W of libraries |" → Must say: "| KiCad files | S-expression formats [KiCad formats] | R; W of libraries and netlists |"
   - Now: "| SPICE netlists and models; Verilog-A | The ngspice, PSpice and LTspice dialects ELX reads | R |" → Must say: "… | R; W of netlists |"
   - Why: ECO owns every writer. ELX specifies "Netlists export as SPICE, KiCad netlist and EDIF 2 0 0" with a phase 3 row (ELX-O-SCH-3), and ECO lists only EDIF as written.
5. **[medium] Memory is reserved as it grows.** `### Determinism and limits` (line 462)
   - Now: "and PLT reserves declared memory before instantiation."
   - Must say: "and PLT's limiter reserves budget as memory grows."
   - Why: PLT owns the runtime: "its limiter reserves budget as memory grows (R3-33)". Contract 7.4's growth guards assume failures below the maximum.
6. **[medium] Licence evidence is needed in phase 0.** `### Round trips, fuzzing and qualification` (line 312) and `## Interfaces with other subsystems` (line 935)
   - Now: "| Corpora by hash list | No vendored third-party data; per-item licence evidence | An item without evidence is not fetched | ECO-O-31 | 1 |" → Must say: the same row ending "| ECO-O-31 | 0 |"
   - Now: "| `crucible:ops` bindings from its catalog |" → Must say: "| `crucible:ops` bindings from its catalog; per-model licence evidence for the ABC subset (phase 0) |"
   - Why: ANV builds its phase 0 re-fillet corpus and SSI cost spike "from the licence-filtered ABC subset" and requires the evidence from ECO. Contract 13.3 says models without it are not copied.
7. **[medium] Release-data records and the standing-release decision.** `## Interfaces with other subsystems` (lines 941, 942) and `### Exit surfaces` (D-ECO-28, line 561)
   - Now: "`release_data` commit records" → Must say: "release-data records"
   - Now: "Act classes, `release_data` and `standing_release` (D-AGT-30)" → Must say: "Act classes, `release_data` and `standing_release` (D-AGT-30, D-AGT-33)"
   - Now: "run under AGT's `standing_release` class (D-AGT-30)." → Must say: "run under AGT's `standing_release` class (D-AGT-33)."
   - Why: KLN names the record: "writes the release-data record, watermark, expiry and audit entry". D-AGT-33 defines `standing_release`; D-AGT-30 defines the `release_data` family.
8. **[medium] The standards namespace.** `### Licence and contributions` (D-ECO-36, line 763) and `## Interfaces with other subsystems` (line 936)
   - Now: "ship in separate `standards::` Packages with a `DataLicence`" → Must say: "ship in separate `crucible::standards::` Packages with a `DataLicence` (D-MEC-31)"
   - Now: "drawing writers; `standards::` Packages and their licence rule |" → Must say: "drawing writers; `crucible::standards::` Packages and their licence rule |"
   - Why: contract 6: "First-party packages outside std use `crucible::`". MEC's package table uses `crucible::standards::*`.
9. **[medium] `crucible:mfg` world names.** `### First-party WIT packages` (line 376) and `## Interfaces with other subsystems` (line 939)
   - Now: "| `crucible:mfg` | `strategy`, `post`; strategy, post, nesting, packing, slicer and recognizer worlds | MFG |" → Must say: "| `crucible:mfg` | Worlds `toolpath-strategy`, `post-processor`, nesting, packing, slicer and recognizer | MFG |"
   - Now: "strategy, post, nesting, slicer and recognizer worlds" → Must say: "`toolpath-strategy`, `post-processor`, nesting, packing, slicer and recognizer worlds"
   - Why: MFG owns the package and names the worlds (`toolpath-strategy`, `post-processor`). Round 2's ruling: ECO lists "the `crucible:mfg` worlds MFG defines". ECO's own line 243 already says `post-processor`.
10. **[low] `crucible:connect` names no worlds.** `### First-party WIT packages` (line 380) and `### Manifest, lockfile and compatibility` (line 624)
    - Now: "| `crucible:connect` | `types`, `secrets`, `partner`, `erp`, `mes`, `plm`; one connector world each |" → Must say: "| `crucible:connect` | `types`, `secrets`, `partner`, `erp`, `mes`, `plm`; worlds `partner-connector`, `erp-connector`, `mes-connector`, `plm-connector` |"
    - Now: "world   = "crucible:connect/connector@0.1.0"" → Must say: "world   = "crucible:connect/partner-connector@0.1.0""
    - Why: ECO owns the package but names no worlds, while its manifest example uses a `connector` world the index does not define. MFG already writes `erp-connector` and `mes-connector`, so adopting those spellings changes no other tab.
11. **[low] STEP-NC parts phased later by MFG.** `### Mechanical CAD and product data` (line 164)
    - Now: "| STEP AP238 and ISO 14649 | ISO 10303-238:2022, as MFG states | R/W | Semantics: workingsteps | Build | 3 | MFG |"
    - Must say: the same row with the Phase cell "3; parts 13, 14 and 17 at 5"
    - Why: ECO owns the phase, and its row takes scope from MFG, whose STEP-NC row reads "parts 10, 11, 12, 111 and 121 and AP238 … (3); parts 13, 14 and 17 (5)".
12. **[low] API method phases and a stale request.** `### Enterprise connectors` (line 584) and `### SDKs, methods and the CLI` (line 523)
    - Now: "| ECO's API methods and CLI | Methods above; aliases, exit codes, offline mode | Typed errors; exit codes 1 to 5 | ECO-O-11 | 1 |" → Must say: the same row ending "| ECO-O-11 | 1, 2 (registry search and bundles) |"
    - Now: "ECO asks AGT to add:" → Must say: "AGT's catalog holds ECO's methods:"
    - Why: AGT's row is "`read.packages`, `read.package`, `read.registry_bundle` | … | 1 (`read.package`), 2". AGT already lists every method ECO asked for.
13. **[low] Interface rows omit what other tabs require.** `## Interfaces with other subsystems`
    - Now (line 936): "Board readers; AP242 and QIF translators; drawing writers;" → Must say: "Board readers; AP242 and QIF translators; drawing writers; GDSII and OASIS writers (phase 5);". MEC requires them.
    - Now (line 944): "package metadata, capability descriptions and badges; licensed translators as external tools |" → Must say: "package metadata, capability descriptions and badges; `TranslationReport`s; font packages; licensed translators as external tools |". UIX requires them.
    - Now (line 943): "`crucible:host/parallel`; LMS release signing" → Must say: "`crucible:host/parallel` and `crucible:tool/process`; LMS release signing". PLT specifies both interfaces, and ECO indexes them.
14. **[medium] Change requests still written as pending.** `## Open questions` (line 1021) and `## Contract change requests` (lines 1028 to 1030)
    - Now: "R11-45, R11-28, R9-47: applied here; the contract text they touch is CCR-ECO-12, CCR-ECO-10 and CCR-ECO-11." → Must say: "R11-45, R11-28, R9-47: applied here and in contract 13.1, 7.7 and 7.6 (CCR-ECO-12, CCR-ECO-10, CCR-ECO-11)."
    - Now: the bullets beginning "- **CCR-ECO-10 (R11-28).**", "- **CCR-ECO-11 (R9-47).**" and "- **CCR-ECO-12 (R11-45).**" → Must say: "- CCR-ECO-10, support period: accepted with CCR-PLT-10 in contract v6.1 (section 7.7)." / "- CCR-ECO-11, error-code form: accepted with CCR-KLN-9 and CCR-AGT-12 in contract v6.1 (section 7.6)." / "- CCR-ECO-12, SDK names: accepted in contract v6.1 (section 13.1)."

## PLT

1. **[high] The wrong Abort for the fuel governor.** `### Worlds, calls and failures` (line 554)
   - Now: "| Evaluation fuel or budget exhausted | Abort: `FuelCeilingExceeded` or `BudgetExhausted` | Never |"
   - Must say: "| Evaluation fuel governor or work budget exhausted | Abort: `BudgetExhausted` | Never |" and a new row "| An organization ceiling below a source limit, at admission | Abort: `FuelCeilingExceeded` | Never |"
   - Why: KLN owns the catalog, and PLT says outcomes "come from KLN's one catalog". KLN: `BudgetExhausted` is "A work budget or the Evaluation's fuel governor"; `FuelCeilingExceeded` is "An organization ceiling below a source limit, at admission".
2. **[medium] The FIPS module's status.** `### OS services` (line 53) and `## Open questions` (line 992)
   - Now: "whose FIPS 3.x build "has been submitted to NIST for certification" [certificate status unverified]." → Must say: "whose AWS-LC 3 module holds FIPS 140-3 certificate 5314 [NIST CMVP certificate 5314]."
   - Now: the item beginning "1. **FIPS module certificate.**" → Must say: "1. **FIPS module certificate.** Closed: the AWS-LC 3 module holds FIPS 140-3 certificate 5314."
   - Why: PLT owns the provider, but KLN states and cites the fact: "whose AWS-LC 3 module holds certificate 5314", with the NIST CMVP page in KLN's Sources. The auditing agent opened that page and found certificate 5314 active under FIPS 140-3. The PLT editor re-opens it before citing, as contract 11 requires.
3. **[medium] IME and AccessKit hosting are needed in phase 0.** `### Paths, text and accessibility` (lines 78, 80)
   - Now: "| No IME: plain input, with a notice | PLT-O-OS-2 | 1 |" → Must say: "| No IME: plain input, with a notice | PLT-O-OS-2 | 0 (Windows, Chrome), 1 |"
   - Now: "| PLT-O-OS-3 | 1 (desktop, web), 3 (tablets) |" → Must say: "| PLT-O-OS-3 | 0 (Windows), 1 (desktop, web), 3 (tablets) |"
   - Why: UIX's phase 0 "Toolkit risk spike" exercises "AccessKit on Windows; IME field on Windows and in Chrome", and PLT's own D-PLT-8 says the spike runs "with PLT's IME paths and Windows AccessKit hosting". Under 13.4 a capability is phased no later than what depends on it.
4. **[medium] Rows omit the `Interactive` lane other tabs require (round 3 item).** `### Provided by PLT` (lines 893, 895, 896, 897)
   - Now: "| ING | Executors, the determinizer, verification of generated modules, `detmath` and `det_sum` (Ingot's `sum`), text normalization, the browser memory table |" → Must say: "…, text normalization, the `Interactive` pool lane, the browser memory table |"
   - Now: "| MEC, COV | `linalg`; for COV also `f64` availability per class, with no emulated `f64` on WebGPU, and the browser memory table |" → Must say: "| MEC, COV | `linalg`; for MEC also `detmath`, the `Interactive` pool lane and Parley shaping; for COV also `f64` availability per class, with no emulated `f64` on WebGPU, and the browser memory table |"
   - Now: "| ELX | `detmath`; the browser memory table; serial and USB access (FLX owns circuit LU) |" → Must say: "| ELX | `detmath`; the `Interactive` pool lane; the browser memory table; serial and USB access; registry font packages (FLX owns circuit LU) |"
   - Now: "| AGT | `api` transport, `cli` exit codes, `CredentialStore`, the approval session, `Usage` measurement, the stdio sandbox for external MCP servers |" → Must say: "| AGT | `api` transport, `CredentialStore`, the approval session, `Usage` measurement, the stdio sandbox for external MCP servers, the `Interactive` pool lane |"
   - Why: ING, MEC, ELX and AGT each require "the `Interactive` pool lane" (and MEC `detmath` and Parley, ELX font packages) from PLT. PLT defines `PoolLane::Interactive`. ECO, not PLT, specifies CLI exit codes (AGT 10).
5. **[low] The Linux 3D-mouse path.** `### Paths, text and accessibility` (line 79)
   - Now: "| 6-DoF devices | `NavDeviceEvent` from HID; spacenavd on Linux |"
   - Must say: "| 6-DoF devices | `NavDeviceEvent` from HID on every desktop OS, WebHID in Chromium; spacenavd optional on Linux |"
   - Why: PLT owns the device path (contract 12, `platform-api`). D-UIX-31 reads HID "on every desktop OS", makes vendor drivers optional and rejects spacenavd "as the Linux path". The rewording satisfies both. This is judgment call 5 in the summary.
6. **[low] WebUSB and Web Serial have no owner.** `### Paths, text and accessibility` (line 89)
   - Now: "| Serial and USB | `DeviceIo` on native targets, outside evaluation |"
   - Must say: "| Serial and USB | `DeviceIo` on native targets, WebUSB and Web Serial in Chromium, outside evaluation |"
   - Why: contract 7.6: "Client flashing through `apps/platform` or WebUSB is the same Act". ELX: "Browsers use WebUSB and Web Serial". `apps/platform` is the only crate that binds web APIs.
7. **[low] ECO's sector rule for update servers.** `### Consumed by PLT` (line 908) and `### Signed updates`
   - Now: "| ECO | Worlds; browser Wasm component descriptions; declared memory limits; font packages; export classification and CRA reporting |"
   - Must say: "| ECO | Worlds; browser Wasm component descriptions; declared memory limits; font packages; export classification, the sector rule for update servers and CRA reporting |". Also add to `### Signed updates`: "Update servers refuse the countries of ECO's sector rule (D-ECO-29)."
   - Why: D-ECO-29: "update servers geo-restrict those countries". PLT runs the update servers and says nothing about it.
8. **[low] `apps/tool-runner` is missing from PLT's crates.** `### Crates` (line 21)
   - Now: "| `desktop`, `web`, `mobile`, `server`, `cli`, `ci-runner`, `attestation` |"
   - Must say: "| `desktop`, `web`, `mobile`, `server`, `cli`, `ci-runner`, `attestation`, `tool-runner` (with ECO) |"
   - Why: contract 12 lists "`tool-runner` (ECO, PLT)", and ECO runs its Tool context "In `apps/tool-runner`".
9. **[low] Block-triangular LU is FLX's phase 2.** `### Canonical linear algebra` (line 387)
   - Now: "| FLX's supernodal elimination and block-triangular LU, thread-count independent | As above | PLT-O-LA-1 | 1 (sequential), 2 (parallel) |"
   - Must say: the same row ending "| PLT-O-LA-1 | 1 (sequential supernodal), 2 (parallel; block-triangular LU) |"
   - Why: FLX owns sparse factorization (D-PLT-34), and its "Networks and circuits | Block-triangular LU …" row is phase 2.
10. **[medium] Change requests still written as pending.** `## Contract change requests` (lines 1007, 1008)
    - Now: the bullet beginning "- **CCR-PLT-9, tablet engine placement.**" → Must say: "- CCR-PLT-9, tablet engine placement: accepted in contract v6.1 (section 9)."
    - Now: the bullet beginning "- **CCR-PLT-10, CRA support period.**" → Must say: "- CCR-PLT-10, CRA support period: accepted with CCR-ECO-10 in contract v6.1 (section 7.7)."
    - Why: contract 17: "CCR-PLT-9 tablet engine | Accepted (9)" and "CCR-ECO-10, CCR-PLT-10 support period | Accepted together (7.7)".
