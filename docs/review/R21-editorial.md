# R21 editorial review

Summary: The spec's central promise, that every number states how far to trust it, is spread over eleven qualifiers in six places, and no page explains them together on one example. The tabs read as review logs: 482 finding ids in body prose, 235 "(revised in round N)" tags, about 940 decision-number cross-references and "Open questions" sections that list declined findings. The house style forces this: every tab sits within 300 words of its cap, leads list mechanisms rather than purpose, and reference material (crates, WIT, grammars, protocol mappings) comes before the ideas a reader needs. Contract sections 10 and 11 should change so that tabs teach first and specify second.

### R21-01 · Critical · Targets: OVERVIEW, CONTRACT, ING, FLX, COV, KLN
**Section:** Overview "Guarantees across every tab"; contract sections 2, 5 and 7.1; ING "Tolerances, approximations and truth"; FLX "Error budgets, goals and checks"; COV "Coverage model"
**Problem:** Crucible's headline claim is that every result states its error and evidence, yet a reader meets eleven separate qualifiers on one number: fidelity, `ResultStatus`, bound kind, `ErrorBudget` parts, validity zone, model level, evidence level, solution-verification status, platform class with determinism grade, verdict with `conditional_on`, and the gate predicate with policy allowances and Waivers. They are defined in four tabs and three contract sections, each in terms of the others, and no page shows them working together. A careful engineer cannot answer the first question they will ask: "does the bracket pass, and how sure are we?"
**Evidence:** The Overview's "Fidelity, errors and checks" compresses six of the axes into five paragraphs with no example ("calibrated parts combine by a union bound, so a total carries confidence 1 − Σαᵢ"). Solution-verification status (`Estimator`, `Gci`, `None`) appears only in COV D-COV-21; η99 appears in COV and MEC without definition and is defined only in FLX D-FLX-24. The best partial treatment, ING's `static_margin` outcome table, sits at line 900 of a language tab and omits zone, evidence level and platform class.
**Fix:** Add one Overview section, "How far to trust a number", right after the canonical example, and make every tab cite it instead of re-explaining. Its core is this table:

| Qualifier | Question it answers | Values | Owner |
| --- | --- | --- | --- |
| Fidelity | How hard did we try? | `Preview`, `Interactive`, `SignOff` | KLN |
| Result status | Is the value here and current? | `Pending`, `Proxy`, `Ready(Fidelity)`, `Stale`, `Failed`, `Aborted` | `base` |
| Error budget | Which errors were counted, and which were not? | One part per error source, each quantified or `NotQuantified` | `base`, FLX |
| Bound kind | How sure is each error bar? | `Guaranteed`, `Estimated { calibration }`, `Indicator` | `base`, FLX |
| Validity zone | Is the model inside the range where it was checked? | `Calibrated`, `Extrapolated`, `Invalid`, `Unassessed` | COV |
| Model level | What form of physics produced it? | L0 analytic to L3 full 3D | COV |
| Credibility level (today "evidence level") | How well has this model been tested against reality? | E0 declared to E4 context-qualified | COV |
| Solution verification | Was this particular solve checked for convergence? | `Estimator`, `Gci`, `None` | COV, FLX |
| Platform class | Where would the same bits come out again? | Canonical class, `CpuIsa`, `Gpu`, `Unverified` | PLT |
| Verdict | What does the check conclude? | `Pass { conditional_on }`, `Fail`, `Undecided { reason }`, `Error`, `Skipped` | ING |
| Gate | May it merge or release? | Severity below `Error`, a covered non-provisional `Pass`, or a Waiver | ING, KLN |

Follow it with the bracket traced through every row in about 250 words, reusing ING's numbers: at `Interactive` the regularized peak is 112 MPa ± 20 MPa `Estimated` against a limit of 144 MPa to 165.6 MPa (0.6 × the 240 MPa to 276 MPa yield enclosure), status `Ready(Interactive)`, model form `NotQuantified`, so the verdict is a provisional `Pass { conditional_on: [model form] }`; at `SignOff` the value is 118 MPa ± 1.5 MPa, confirmed by one refinement, in the canonical class, zone `Calibrated`, confidence 0.99; after GP1's strain-gauged proof loads lift immersed elasticity to E3 for this response-quantity class, the model-form part becomes `Estimated` and the `Pass` meets the gate with no allowance. Then trim the Overview's "Fidelity, errors and checks" to a pointer, and give contract section 2 one row, "Trust qualifiers: see Overview".

### R21-02 · Major · Targets: ING, FLX, COV, KLN, MFG, ELX, AGT, UIX, PLT, MEC, ANV, ECO, CONTRACT
**Section:** Every design section's decisions; "Open questions"; "Contract change requests"; contract lead
**Problem:** The tabs read as the minutes of their own revision. Review finding ids appear as evidence inside running prose, decisions end in "(revised in round N)", "Rejected" clauses name "the round 2 rule", and "Open questions" sections list declined findings rather than open questions. A reader who was not in the review cannot use any of it, and the Adversarial review tab already owns this history.
**Evidence:** Counted before each tab's "Open questions": finding ids such as "(R3-37, R9-40)" appear 112 times in PLT, 62 in FLX, 56 in MFG and AGT, 48 in ELX, 45 in UIX, 43 in KLN, 34 in COV and 26 in ING (482 in all), while ANV, MEC and ECO show that a tab reads well without any. "(revised in round N)" appears 235 times across twelve tabs. Examples: D-ING-7 "*Rejected:* … `Pending` and `ING6401` as node values, the round 2 rule. (revised in round 3)"; D-MEC-26 "*Why:* … the round 1 drafts claimed the formboard twice"; D-FLX-1 "*Rejected:* the round 1 seven-crate split"; MEC "It replaces `crucible:model`"; KLN "`crucible:product`, formerly `crucible:model`". ING's "Open questions" opens "This revision decides all nine round 2 questions" and then lists ten bullets of declined findings; MEC's question 2 and AGT's question 2 are titled "Findings declined…". The contract's lead is a version history.
**Fix:** One mechanical pass, then a rule. (1) Delete every finding id from text above "Open questions"; where the id stood in for a reason, write the reason ("a policy-clamped limit made two organizations cache different results for one key" stays, "(R3-12)" goes). (2) Delete every "(revised in round N)"; the Decisions log and `git log` keep revision history. (3) Delete "the round N rule", "formerly", "replaces" and similar history from decisions and names; a rejected alternative is described by what it is. (4) "Open questions" holds only unresolved questions; move every "Findings declined or applied in part" list to the Adversarial review tab under that tab's code. (5) "Contract change requests" holds only open requests or "None"; accepted ones are recorded in the contract's ruling log. (6) The contract's lead is one sentence: "Binding for every design agent and reviewer; where a tab disagrees with it, the contract wins." Add to `check.py` a rule that fails on `\bR\d{1,2}-\d{2}\b`, "revised in round" and "round \d" outside the Adversarial review and Decisions log tabs.

### R21-03 · Major · Targets: CONTRACT
**Section:** Contract section 11, "Style" and the skeleton; section 10, "One voice"
**Problem:** The house style is the root cause of most findings in this report. The lead rule ("stating the design in one breath") yields mechanism lists; the skeleton puts no explanation before specification; the length cap counts reference tables, so the cap squeezes out explanation and examples first; the inline decision format packs decision, reason and alternatives into one paragraph; and "paragraphs of at most three sentences" breaks explanations into disconnected fragments. The first review's fix ("cut the tabs by a quarter") created this problem: what was cut was connective prose, not capabilities, because the rule forbids cutting those.
**Evidence:** Words excluding Sources: COV 17,720, ECO 17,738, AGT 17,908, MFG 17,900, MEC 17,968, FLX 17,997, KLN 17,989, ELX 17,993, PLT 17,798, UIX 17,945; ING 19,888 and ANV 19,945 against their 20,000 cap. Every tab sits within 300 words of its limit, so the cap binds everywhere. The contract violates its own paragraph rule: the 7.1 Flux bullet is one 694-word paragraph. The Rust RFC template, the format a strong Rust team already knows, separates a "Guide-level explanation", written "as if … you were teaching it to another Rust programmer", from a "Reference-level explanation", "the technical portion" (https://raw.githubusercontent.com/rust-lang/rfcs/master/0000-template.md). Diátaxis likewise treats explanation and reference as distinct forms with distinct needs (https://diataxis.fr/).
**Fix:** Replace the style bullets of contract section 11 with:
1. "A lead of three sentences: what the subsystem is, in words an engineer outside it understands; what that engineer gains over the incumbents; and the one mechanism that delivers it. The lead uses no term it does not define."
2. "The first design section is guide-level: it opens with a worked example on the canonical bracket or a golden product and explains the model a user meets. Later sections build on it. Reference material (crates, WIT packages, operation and method catalogs, grammars, error-code catalogs, protocol mappings) goes in a final `## Reference` design section before State of the art."
3. "Length: 12,000 to 18,000 words of prose (ING and ANV up to 20,000). Capability tables, the Reference section, Interfaces, Oracles and Sources do not count."
4. "Paragraphs: at most five sentences where the paragraph explains a mechanism, at most three elsewhere. Each design section opens with one sentence saying why it exists."
5. "Decisions are a block of three lines: `**Decision D-<TAB>-<n>:** …`, then `*Why:* …`, then `*Rejected:* …`. Decision numbers are stable; a revision is recorded in the Decisions log, never in the tab."
6. "Running prose never contains review finding ids, round numbers or decision ids. Refer to another tab's fact by name with a link to its section."
Section 10's "One voice" gains: "Teach, then specify. Every new concept gets one sentence of why before its rules."

### R21-04 · Major · Targets: ANV, FLX, KLN, PLT
**Section:** ANV "Kernel structure and operation contract"; FLX "Scope and architecture"; KLN "Scope and the operation contract"; PLT "Scope, crates and the platform layer"
**Problem:** Four core tabs open with build infrastructure: crate tables with dependency lists, crate-layout decisions, operation registries, behavior-version freezing, `OpImpl` signatures and WIT package names. The reader learns which crate depends on `simd` before learning what a Body is, what a Field is or what Kiln does for an edit. The ideas these tabs are proud of (certified decisions, stable names, error-bounded Fields, minimal rebuilds) start in section two or three.
**Evidence:** ANV's first decision, D-ANV-1, is about six crates and `forbid(unsafe_code)`; its first section continues with closure hashes and `Current`, `Deprecated`, `Retired` statuses. FLX's first section is a crate table, D-FLX-1 on crate splits, and an 11-row table naming about 80 operations, before "Fields". KLN's first code block is the `OpImpl` trait, followed by D-KLN-2 and D-KLN-4 on closure hashes and retired versions. PLT's first sentence cites two finding ids and its first table lists crates and `unsafe` permissions.
**Fix:** In each tab, move crates, crate decisions, WIT packages, operation registries and version freezing into the closing `## Reference` section (R21-03), and open with the domain:
- ANV: open with "Bodies, identities and encoding" retitled "One Body, four representations", starting from the bracket's `fillet(body.edges(new), 2mm)`: what the Body is, why the edge keeps its name when `width` changes, and what happens at a near-tangency. "Kernel rules" follows as a summary list.
- FLX: open with "Fields" and a short tour: `static_stress` on the bracket returns a `Field<Part, Stress>`; `.max(over:)` returns an `Approx<Stress>`; here is its budget. The operation catalog moves to Reference.
- KLN: open with "Kiln: graph, keys and memoization", leading with the story of one edit: changing `width` re-runs the bracket feature, reuses the cached clamp face resolution, and backdates the unchanged IIR.
- PLT: open with "Numerical determinism" ("the same bracket gives the same bits on a laptop, in Safari and on the build farm; here is what that takes"), then the platform layer.

### R21-05 · Major · Targets: OVERVIEW
**Section:** "The canonical example"; "Architecture"
**Problem:** The Overview shows the bracket's source and then stops. Nowhere does the spec follow one change through the system: an edit, Kiln's recomputation, Anvil's names, Flux's bound, the check, the Proposal, review, the release Act and the shop's measurement. Every tab assumes this story, and a reader has to assemble it from twelve tabs. The diagram "How a design flows" shows boxes, not a sequence of events.
**Evidence:** Overview "How a design flows" is two paragraphs of component relations ("Kiln runs features, Wasm components and operations as memoized nodes and stores every derived artifact in the CAS"). The pieces exist but are scattered: drag streams in ING "The Ingot IR and Kiln" and AGT "Drag streams"; two-stage naming in ANV "Two identities and two stages"; risk classes in AGT; the approval page in contract 7.6.
**Fix:** Add "The life of one change" after the canonical example, about 600 words in numbered steps with links:
1. **Edit.** The designer drags the bracket's width from 60 mm to 80 mm. The UI streams literal overrides (`edit.stream`) and shows `Interactive` previews; releasing the drag writes one Change replacing the literal `60mm` (ING, UIX).
2. **Recompute.** Kiln re-runs only the nodes downstream of that literal. The extrude, rib and fillet run again; the edge `end(outline.top)` keeps its `EntityId` because names never depend on argument values (KLN, ANV).
3. **Simulate.** `static_stress` re-solves warm-started; the peak is shown as `Pending`, then 112 MPa ± 20 MPa at `Interactive` (FLX).
4. **Check.** The check shows a provisional `Pass`, conditional on model form (ING; see "How far to trust a number").
5. **Propose.** The designer, or a detail-designer agent, opens a Proposal. CI recomputes at `SignOff` on untrusted-evaluation workers, an independent verifier attacks it, and the server computes risk class R1 because the parameter stayed in range on an unreleased design (AGT).
6. **Review and merge.** A reviewer sees evidence before diffs: verdicts, margins and a geometry overlay, then source (UIX).
7. **Release.** `act.prepare` builds a release plan; the assigned approver signs its digest on the approval page with a device-bound credential; `act.commit` writes the signed release tag, and a `send_to_supplier` Act ships STEP AP242 with semantic PMI (KLN, AGT, ECO).
8. **Measure.** The shop's CMM report and the proof-load test return as Evidence records that later Evaluations cite (KLN, MFG).
Replace the "How a design flows" prose with this sequence and keep the diagram.

### R21-06 · Major · Targets: OVERVIEW
**Section:** Overview lead; "What Crucible is"
**Problem:** The Overview's lead describes the document ("This tab summarizes the binding architecture contract … and points to the tab that owns each fact"), and "What Crucible is" lists the founder's four requirements, which say what Crucible must achieve, not what it is or how using it feels. "Where the field stands" lists five competitor facts without drawing the conclusion. A reader finishes the first screen knowing the spec's governance but not the product.
**Evidence:** The first section's opening sentence is "Four hard requirements from the founder shape every tab (contract section 1)"; its last paragraph describes the contract's binding status and the two review tabs. "Where the field stands" ends with one sentence, "Crucible's answer is the principles below".
**Fix:** Replace the lead with: "Crucible is one Rust platform where people and agents design, simulate, manufacture and release physical products from a single typed program. A part is a short Ingot program; editing a dimension in the viewport edits that program, and every result it produces (geometry, stress, a toolpath, a cost) says how accurate it is and on what evidence. This page explains the idea, follows one change from edit to release, and points to the tab that owns each fact." Retitle "What Crucible is" to "What it must achieve" and open it with three sentences of what a session looks like, in the voice of the life-of-a-change section (R21-05). End "Where the field stands" with the synthesis the bullets support: "Each incumbent owns one piece: typed code, a kernel, a solver, an agent interface. None makes the program itself the model, with units and errors checked by the compiler and every edit reviewable as text. That is the gap Crucible fills."

### R21-07 · Major · Targets: ANV, FLX, COV, KLN, MEC, AGT, MFG
**Section:** The lead of each tab (and the Overview's "Subsystems" paragraphs, which restate them)
**Problem:** Leads follow the "design in one breath" rule literally: they list mechanisms in terms the lead does not define, and none says what the engineer gains. ANV's lead uses "decisions", "rounds", "frozen tolerances", "fidelity" and "label-invariant" without definition; FLX's names "aggregated CutFEM on an immersed octree" before saying what Flux gives a user; COV's uses "model level" and "evidence level" undefined. Because the Overview copies the leads, the weakest prose in the spec appears twice.
**Evidence:** ANV: "Decisions use exact predicates on linear geometry and certified enclosures on curved geometry, in rounds against frozen tolerances, identically at every fidelity." FLX: "Solids use aggregated CutFEM on an immersed octree, slender walls and members use shells and beams, and contact uses fitted meshes." COV: "…whose models declare a model level, an evidence level and a `ValidityEnvelope` as data."
**Fix:** Adopt the three-sentence lead of R21-03 and replace these leads:
- ANV: "Anvil is Crucible's geometry kernel: one `Body` type holds exact B-rep, implicit, mesh and subdivision geometry, and mixing them never silently approximates. Where other kernels settle near-coincidences with a global tolerance and a best guess, Anvil proves each topological decision or reports that it cannot, so a model builds the same way on every machine. Every operation is versioned and returns the history that keeps face and edge names stable when dimensions change."
- FLX: "Flux is Crucible's simulation engine: physics is written as weak forms in Ingot, or called as std studies such as `static_stress`, and every result is a Field with a stated bound on its error. Where incumbents report a number and leave convergence to the analyst, Flux names each error source, its norm and how sure the bound is, so a check decides only when the bound supports it. It chooses the discretization per region (shells for thin walls, beams for struts, an immersed grid for solids), so nobody meshes by hand."
- COV: "COV decides which physics Crucible can honestly claim. Every physics model is a package that states where it is valid and how well it has been tested, every material is a versioned record with its statistical basis and licence, and every gap is a named record that points to a tool that covers it. A result outside its model's validated range is flagged or refused, never quietly trusted."
- KLN: "Kiln, `repo` and PLM keep a design's history and compute its results. Kiln re-runs only what an edit affects and shares results across designs by content; `repo` records every edit as an immutable Change on cheap branches and merges only when geometry, checks and connectivity still agree; PLM turns merged Changes into Items, revisions, BOMs and signed releases. The same signed store runs on a laptop, a team server, the cloud or an air-gapped site."
- MEC: "`std::mech` is everything a mechanical designer does in Crucible, from sketch to drawing, written as ordinary Ingot features anyone can read, fork or replace. Where incumbents add sheet metal, weldments and composites as separate workbenches, every domain here shares one constraint solver, one way of naming faces and one semantic tolerancing model, so the drawing, the stack-up and the inspection plan read the same tolerances. Every feature fails with a typed reason and a fix that compiles."
- AGT: "Agents in Crucible are colleagues on branches: they call the same `api` a person's clicks call, and hand their work over as Proposals that a human reviews like a pull request. An independent verifier attacks every Proposal before review. Safety lives in the server, not in the model: untrusted text never carries authority, and nothing leaves Crucible, from a release to a program sent to a machine, until a named human approves its exact plan."
- MFG: keep its third sentence, and replace "through one typed plan: Ingot intent, Wasm planning, Anvil geometry and Flux physics" with "as one typed plan that regenerates when the design changes".

### R21-08 · Major · Targets: CONTRACT, COV, KLN, MFG, AGT, ECO, OVERVIEW
**Section:** Contract section 2 ("Evidence record", "Evidence level"); COV "Evidence levels"
**Problem:** "Evidence" names at least six things: an Evidence record (a signed physical measurement), an evidence level (a model's credibility, E0 to E4), the evidence watermark (a log position), the `evidence_records` field of `CheckOutcome`, "simulation evidence" for manufacturing programs, and "sampled evidence" for query stability, plus "licence evidence" and "oracle evidence". The contract notices the clash ("Distinct from an Evidence record"; "'evidence' never names a bound kind") but keeps it. A reader of "E3 evidence" next to "Evidence records from the proof load" cannot tell a model property from a measurement.
**Evidence:** Phrase counts across the contract and tabs: "simulation evidence" 6, "evidence levels" 5, "licence evidence" 4, "oracle evidence" 3, "sampled evidence" 2, besides 15 uses of "Evidence record(s)". Contract 5: "`ApprovalSubject` … `evidence record ids`"; contract 7.6: "the posted program and its simulation evidence"; contract 5 (`Query`): "Stability … is sampled evidence".
**Fix:** Rename the evidence level to the **credibility level**, C0 to C4 (Declared, Verified, Benchmarked, Validated, Context-qualified), the term ASME V&V 40, which COV already cites for E4, uses for this idea. Reserve "evidence" for Evidence records and the watermark over them. Replace the other uses: "simulation results" for manufacturing programs, "sampled stability" for queries, "licence proof" for ABC per-model records, "oracle results" for CSA packages. Contract section 2 rows: "**Credibility level** · How well a physics model has been tested against reality, C0 to C4 (COV) · 'evidence level'"; add "credibility level" to the Evidence record row's "Never call it" column. This is a contract change; COV files it.

### R21-09 · Major · Targets: ING, MEC, KLN, ANV, AGT
**Section:** D-ING-26 and D-MEC-33; D-ING-11 and D-KLN-6; D-ING-22 and D-MEC-10; D-ANV-18, D-KLN-2 and D-KLN-4; D-AGT-31
**Problem:** Several facts are decided twice, in two tabs, with two rationales, against "Say it once". A reader meets the same rule again and has to check whether the two copies differ, and the copies already drift in detail.
**Evidence:** Sketch seeds: D-ING-26 ("Sketch seeds are inline literals rounded to a quantum") and D-MEC-33 ("Seeds stay inline, rounded to a quantum q"), each with its own rejected list. Failures and Aborts: D-ING-11 and D-KLN-6 both justify themselves with the out-of-memory fallback example. Instance existence: D-ING-22 and D-MEC-10 both decide that existence depends only on `#[configuration]` parameters. Version freezing: contract 4, D-ANV-18, D-KLN-2 and D-KLN-4, with near-identical paragraphs in ANV ("Per-merge CI reproduces golden hashes of `Current` and `Deprecated` versions pinned by a golden product or registry package … weekly in shards") and KLN ("Per-merge CI reproduces golden hashes only for `Current` and `Deprecated` versions that a golden product or registry package pins … weekly in shards"). D-AGT-31 opens "Physical-effect Acts follow contract section 7.6", restating a contract rule as a decision.
**Fix:** Keep one decision per fact, in the owner's tab: seeds in MEC (D-MEC-33); Failure and Abort semantics in KLN (D-KLN-6), with ING keeping only the language rule that `try` cannot observe an Abort; existence in ING (D-ING-22); version freezing in ANV for operations, KLN for registration. In the other tab, replace the decision with one sentence and a link ("Sketch seeds are inline literals rounded to MEC's quantum; see MEC 'Determinism and seeds'"). Decision numbers stay reserved, so mark the removed ones in the Decisions log as "merged into D-MEC-33". D-AGT-31 keeps only what AGT adds (plan schemas and AGT-O-21).

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

### R21-13 · Major · Targets: PLT, FLX, MFG, AGT
**Section:** PLT "Targets" and "The browser target"; body prose of the tabs with finding ids
**Problem:** Some quotations from primary sources are attributed to review finding ids instead of the page that was opened, so the reader cannot follow the citation and the research rule ("cite only pages you opened") is met only in the Sources list. The finding id is not a source; it is the reason the sentence was added.
**Evidence:** PLT: "Wasmtime rates Windows ARM64 Tier 3, lacking 'CI testing, full-time maintainer', and aarch64 macOS and Linux Tier 2, lacking 'Continuous fuzzing' (R6-12)." PLT D-PLT-33: "Pulley carries 'a ~10x order-of-magnitude slowdown' (R6-13)". PLT's Sources do list the pages ("67. Wasmtime stability tiers. https://docs.wasmtime.dev/stability-tiers.html"; "68. Pulley, Wasmtime documentation"), but the prose never points to them.
**Fix:** Replace each finding id that follows a quotation or a sourced fact with the source key (R21-12): "(R6-12)" becomes "[Wasmtime stability tiers]", "(R6-13)" becomes "[Wasmtime Pulley]". Do this as part of R21-02's pass: where an id follows a quote, swap it for the source; elsewhere, delete it.

### R21-14 · Major · Targets: OVERVIEW, ING, ANV, FLX, COV, MEC, AGT, CONTRACT
**Section:** Overview "Program plan", "Phase 1 scope", "Roadmap"; tab-local terms throughout
**Problem:** Terms and abbreviations appear before any definition, and some are never defined in the tab that uses them. The Overview, the page meant for every reader, uses DWR, SSI, CutFEM, PMI, WIT, MCP and DAE without expanding them, and refers to "chains A and B" and "GP2's alloy, machine, bureau and build-preparation software" in the Roadmap table, sixty lines before "Critical path" defines the chains. The contract glossary covers platform concepts but not the technical vocabulary the tabs share.
**Evidence:** First Overview uses: "WIT package" (line 51), "compiled into a DAE" (77), "aggregated CutFEM" (145), "chains A and B searched" (282), "semantic PMI" (283), "Aggregated CutFEM with calibrated DWR" (333), "Certified SSI without sampling for GP1 and the prismatic ABC subset" (334); none is expanded. η99 is used in COV and MEC and defined only in FLX D-FLX-24; ρ appears in MEC's D-MEC-33 ("2¹⁰ρ") with no definition in MEC; "torsor", "Krawczyk test", "pass^4", "MRTR" and "Rule of Two" appear without a gloss at first use.
**Fix:** Add a generated "Glossary" at the end of the Overview, listing each term once with a one-line meaning and its owner, and require first-use expansion in every tab (contract 11). Entries to add:

| Term | Meaning | Owner |
| --- | --- | --- |
| SSI | Surface–surface intersection: computing the curves where two surfaces meet, the core of every Boolean | ANV |
| CutFEM (aggregated) | Finite elements on a background grid that the geometry cuts through, so no fitted mesh is needed; "aggregated" merges tiny cut cells with neighbours for stability | FLX |
| DWR | Dual-weighted residual: an error estimate for one goal quantity, such as a regional stress average, computed with an adjoint solve | FLX |
| η99 | A calibration class's 99th-percentile underestimate factor; every `Estimated` bound is reported already multiplied by it | FLX |
| ρ | A Body's resolution: the scale-relative length below which Anvil treats geometry as coincident | ANV |
| PMI | Product and manufacturing information: dimensions, tolerances and notes attached to the 3D model; "semantic" PMI is machine-readable | MEC |
| Torsor | The small rigid displacement (three rotations, three translations) by which a toleranced feature may deviate from nominal | MEC |
| Krawczyk test | An interval-arithmetic test that proves a system of equations has exactly one solution in a box | ANV, MEC |
| DAE | Differential-algebraic equations, the form a Network compiles to | FLX |
| WIT | WebAssembly Interface Types, the interface language of the Wasm Component Model | ECO |
| MCP | Model Context Protocol, the standard through which AI hosts call tools | AGT |
| IIR; kernel IR | The Ingot IR, Ingot's dataflow form after lowering; FLX's intermediate form for every result-affecting numeric kernel | ING; FLX |
| Golden product (GP1 to GP16) | A reference product whose checks, and whose made and measured articles, close a phase | Contract 13.1 |
| Chains A to D | The four sequences of work on phase 1's critical path: geometry, physics, interface, release | Contract 13.2 |
| ABC subset | The licence-filtered part of the ABC dataset of public Onshape models used for benchmarks | Contract 13.3, ECO |
| R0 to R4 | Risk classes of a Proposal, from no semantic change to changes that feed an Act | AGT |
| pass^k | The share of tasks an agent completes in every one of k independent trials | AGT |
| UFL | Unified Form Language, FEniCS's notation for weak forms, whose semantics Flux's forms follow | FLX |

In the Overview, move the Roadmap's phase 0 gate details on chains and GP2 behind a link to "Critical path", or define the chains before the table.

### R21-15 · Major · Targets: CONTRACT
**Section:** Sections 2, 7.1, 7.6 and 14 to 17; the lead
**Problem:** The contract is the second document in the reading order and the binding text every tab cites, but it reads worst of all. Single bullets run to hundreds of words, glossary rows carry rules and procedures, and a quarter of a binding document is ruling history. A reader looking up "what is Flux's discretization rule" must parse one 694-word bullet.
**Evidence:** The 7.1 "Flux" bullet is 694 words (discretization, singular sets, calibration, refinement confirmation, surrogates, bifurcations, method list and licensing in one paragraph); the 7.6 "Act approvals" bullet is 237 words. Glossary rows: "Evidence record" is 116 words and includes the watermark mechanism; "Act" lists every physical-effect Act, which 7.6 "Physical safety" lists again verbatim ("Physical-effect Acts are the transfer Acts `send_to_machine`…" at lines 60 and 251). Sections 14 to 17 hold about 3,400 of the contract's 20,100 words.
**Fix:** (1) Split 7.1's Flux bullet into a subsection "7.1.1 Flux" with five short paragraphs or a list: discretization per region (as the Overview's table), singular sets, error reporting and calibration, surrogates, and solver scope. Split "Anvil" the same way. (2) Cap glossary rows at about 25 words: a definition plus the "Never call it" entry; move the Evidence record's watermark rule to section 5 and the Act's list of physical-effect Acts to 7.6 only. (3) Move sections 14 to 17 to `docs/contract-rulings.md`, linked from section 1, so the contract states only the current design; the Adversarial review tab already narrates the rulings. (4) Replace the lead's version history as R21-02 says.

### R21-16 · Major · Targets: FLX
**Section:** "The weak-form language"
**Problem:** Flux's input language is weak forms in Ingot, yet the tab never shows a complete one. The section lists spaces, measures and operators in tables, and the only full form in the spec is the contract's three-line elasticity fragment. A simulation engineer cannot see how a problem is posed, solved, given a goal and checked end to end, which is the first thing they would try.
**Evidence:** FLX has three plain code blocks in about 18,000 words (ING has nineteen, MEC sixteen). "The weak-form language" consists of a spaces table, a measures paragraph, a problem-kinds table, a checks table and two decisions; the problem-kinds table gives forms only as fragments (`a == L`; `dt(u)`; `continue_in(load, to: 2kN)`).
**Fix:** Open the section with a complete, short example, with the syntax for prescribed values fixed by FLX:

```
use std::sim::{trial, test, dx, ds, solve}

/// Steady conduction: 5 W into the web's end cap, the clamp held at 40 degC.
pub feature bracket_thermal(p: Part, clamp: Query<Face>, pad: Query<Face>) -> Part {
    let t = trial(Temperature, p)
    let v = test(t)
    let k = p.material.conductivity(at: 20degC)
    let q = 5W / pad.area()
    let heat = inner(k * grad(t), grad(v)) * dx(p) == q * v * ds(pad)
    let result = solve(heat, fixed: [(clamp, 40degC)], goals: [t.mean(over: pad)])
    p.require(result.t.mean(over: pad) < 85degC, name: "pad_temperature")
}
```

Follow it with four sentences: the compiler checks that every term of `heat` has one dimension; `solve` picks a plan per region; the goal makes the adaptive loop refine for the pad's mean temperature; and because a regional mean is a bounded linear functional, its bound may be `Guaranteed` (contract 5), unlike the bracket's stress peak. Then add a five-line time-dependent variant using `dt(t)`.

### R21-17 · Major · Targets: AGT
**Section:** "The `api` surface", "MCP profile"
**Problem:** The tab's first design section after scope is protocol detail: MCP revision deprecations, Multi Round-Trip Requests, HTTP header mirroring, HMAC-truncated shard keys, AEAD-sealed request state and a tool-name character rule. A reader has not yet seen an agent do anything, so none of it has a reason. The tab's strongest material (an agent editing, checking, describing and proposing work on the bracket) is spread over four later sections.
**Evidence:** The first subsection under "The `api` surface" is "MCP profile", whose second paragraph reads: "Mirrored headers are visible to intermediaries [S3], so `shard_key` is an HMAC-SHA-256 of the repository id under the tenant's routing key, truncated to 16 bytes." The bracket's `inspect.describe` output, the best example in the tab, sits in "Observation interfaces", about 350 lines later.
**Fix:** Open AGT's first design section with "An agent's task, step by step", a numbered trace on the bracket: `session.open` as a detail designer on branch `widen-bracket`; `read.outline` of `bracket`; `edit.apply` with `SetParameter { width: 80mm }` returning the source patch; `evaluate.ci` streaming frames; `inspect.describe` returning the brief description already in the tab; `propose.create` with its five preconditions; the verifier's attack; risk class R1; a human approves the merge. Each step links to the subsection that specifies it. Move "MCP profile", HTTP headers and `shard_key` into a "Transports" subsection near the end of "The `api` surface", or into the Reference section (R21-03).

### R21-18 · Major · Targets: MEC
**Section:** "Library structure and shared conventions"
**Problem:** MEC opens with a legal decision on standards tables (D-MEC-31), the hash encoding of Part and Assembly identity down to quaternion sign conventions (D-MEC-32), the definition-tolerance default, a WIT package, and a dataset-licensing decision (D-MEC-37), before the reader sees one feature. The tab's best teaching example, `housing`, which shows sketch, extrude, pocket, tapped holes and fillets in ten lines, waits in the third section.
**Evidence:** The first decision a reader meets is D-MEC-31 ("std computes standard values from the formulas the standards define … Counsel reviews this split before phase 1"); the next section is "Identity of Parts and Assemblies" ("A placement is a unit quaternion with non-negative scalar part plus a translation, in canonical f64 bits"); "Third-party data and benchmarks" closes the section.
**Fix:** Reorder to: (1) a short opening with the `housing` example and the `lid` roles example, explaining roles, queries and typed failures (today's "Roles, queries and fixes" and D-MEC-1, D-MEC-2); (2) Sketching; (3) Part features; and onward. Move "Packages" and D-MEC-31 into a "Standards content" subsection beside "Holes and threads", where the thread and clearance tables first matter; move "Identity of Parts and Assemblies" and "WIT interface" to the Reference section; move D-MEC-37 to the preamble of "Oracles", where datasets are used.

### R21-19 · Major · Targets: ING
**Section:** "Lexical syntax and grammar"; "The language at a glance"
**Problem:** ING's second section is the full lexical specification and a 70-line EBNF grammar, so a reader meets NFC normalization, UAX #31 identifiers and statement-termination rules before tolerances, approximate values, queries or checks, the ideas that make Ingot worth learning. "The language at a glance" reprints the canonical example verbatim (its third copy in the spec) with a three-sentence gloss, instead of walking through it.
**Evidence:** Section order: "Scope and principles", "Lexical syntax and grammar" (encoding, keywords, literals, EBNF), "Types and dimensions", then "Tolerances, approximations and truth" at line 381. The tab's most readable passages (the `pin_joint` stack with worked numbers, the `drive_unit` catalog example, the `static_margin` outcome table) all sit after line 440.
**Fix:** Expand "The language at a glance" into an annotated walkthrough of the bracket: a table of eight rows, "Line · What Ingot does · Where specified" (units on parameters and `ING3001`; `Tol<Length>` forwarded as PMI; `end(outline.top)` as a role query; `body.edges(new)`; `part(…).material(…)`; `static_stress` returning Fields; `away_from` and the regularized peak; `require` as a three-valued check). Then order the sections as Types, Tolerances, Geometry, Evaluation, Diagnostics and checks, Execution, Rust features, Packages, Feature metadata, Tooling, and finally "Lexical syntax and grammar" as the Reference section. Keep the literal and unit tables near the start of Types, because units are the first thing a user types.

### R21-20 · Major · Targets: COV
**Section:** "Coverage model" ("Evidence levels", "Error budgets and model form")
**Problem:** The section is a wall of decisions. Eight decisions appear in it, three of them back to back, numbered out of order (D-COV-1, 2, 3, 21, 20, 4, 24, 17), and they use u_val, k, g(d), η99 and "response-quantity class" without defining them in this tab. A reader learns many rules about model-form error and never sees one number go through them, although this is where Crucible's honesty claim is decided.
**Evidence:** Under "Error budgets and model form": a two-sentence paragraph, a table, then D-COV-20, D-COV-4 and D-COV-24 consecutively, one paragraph, then D-COV-17. D-COV-20 reads: "Flux's bound B enters u_val as B/√3 when `Guaranteed` and B/z₁₋α/₂ when `Estimated` at level α".
**Fix:** Rewrite "Error budgets and model form" as a numbered procedure, "How the model-form part is filled", with each decision attached to its step: (1) find the response-quantity class (define it: quantity, location type, regime); (2) if the model is E2 or the class is not validated, the part is `NotQuantified` and a `Pass` is conditional (D-COV-4); (3) at a validation point, compute E = S − D and u_val, and the bound |E| + k·u_val (D-COV-20, defining k as the coverage factor); (4) away from validation points, inflate by g(d) (D-COV-25); (5) an allowance may cover an unquantified part only from a confirmed catalogue entry (D-COV-24). Close with one worked example: GP1's proof-load gauge strains, a simulated value, an illustrative E and u_val, and the resulting `Estimated` model-form part on the bracket's peak-stress class. Define η99 in one clause where D-COV-17 first uses it.

### R21-21 · Minor · Targets: CONTRACT, AGT, COV, KLN, MEC, MFG
**Section:** Contract section 2; uses of "class"
**Problem:** "Class" carries eleven meanings: platform, calibration, risk, Act, machine, execution (EN 1090), device, response-quantity, precision, retention and priority class. Several meet in one sentence ("a non-provisional `Pass` in a platform class the gate accepts … calibration class … risk class"), and "the canonical class" appears bare.
**Evidence:** Occurrences: risk class 15, calibration class 14, platform class 13, Act class 12, machine class 10, execution class 8, device class 8, response-quantity class 7, precision class 6, retention class 3, priority class 3.
**Fix:** Keep platform, calibration, risk, machine and execution class (core terms or industry usage). Rename Act class to **Act kind**, precision class to **precision tier**, retention class to **retention tier**, and say "response quantity" (the V&V term) instead of "response-quantity class" where the set is meant. In each tab, write "the canonical platform class" at first use.

### R21-22 · Minor · Targets: CONTRACT, ING, MEC, AGT
**Section:** Contract sections 9 and 11, "Platform notes"
**Problem:** Every tab must have a "Platform notes" section, so tabs with no platform-specific behaviour fill it with restatements, which a reader skims and learns to ignore.
**Evidence:** ING: "Accessibility | Diagnostics are plain text with spans"; "Air-gapped installs | Compiler and interpreter ship in every build; no network is needed"; "Every target | One canonical-class interpreter, so a divergence is a platform defect".
**Fix:** In contract 9 and 11, allow "Platform notes: none beyond PLT's rules" as a complete section, and require a row only for behaviour that differs by target (capacity, a missing capability in a tier, a browser limit).

### R21-23 · Minor · Targets: KLN, AGT
**Section:** AGT before "Method catalog", "Roles", "Proposals and review", "Clearance, egress and data protection", "Benchmarking and training data"; five places in KLN
**Problem:** A `##` heading follows a table row with no blank line. GitHub renders it, but a stricter Markdown renderer or the publishing step can fold the heading into the table, and the source reads as one block.
**Evidence:** AGT lines 275, 454, 623, 827 and 998 are `## …` headings directly after a capability-table row; KLN has five such headings.
**Fix:** Insert the blank lines, and make `check.py` fail on a heading directly after a table row.

### R21-24 · Minor · Targets: ING, AGT, FLX, MEC, ANV, KLN
**Section:** "Oracles"
**Problem:** Oracle ids follow different schemes: flat numbers (ING-O-1 to ING-O-38, AGT-O-1 to AGT-O-24) and area-prefixed ids (MEC-O-PF-1, ANV-O-VER-1, KLN-O-FPRINT-1, FLX-O-OPT-1). A flat id says nothing about what it verifies, so a capability row citing "ING-O-8" or "AGT-O-17" sends the reader to the Oracles table every time.
**Evidence:** ING capability rows cite "ING-O-1, ING-O-13, ING-O-27"; MEC rows cite "MEC-O-TL-6", whose area (tolerancing) is readable in place.
**Fix:** Adopt `<TAB>-O-<AREA>-<n>` in ING and AGT now, while `oracles/` holds no executable oracles and renaming costs one search-and-replace across tabs.

### R21-25 · Minor · Targets: MEC, KLN, ELX
**Section:** MEC "Interference and clearance" and Interfaces; KLN "Scope and the operation contract"
**Problem:** Some references point at an item number in another place's list, so the reader must open that list to learn what is meant, and the reference breaks if the list is reordered.
**Evidence:** MEC: "KLN's merge condition 4 reuses these classes"; MEC Interfaces: "merge conditions 4 and 5"; KLN's `OpCx` comment: "keyed by rule 2 under Keys"; KLN: "`OpKey(ObjectId)` // contract 7.2, items 1 to 6".
**Fix:** Name the rule: "KLN's no-new-interference merge condition"; "the interference and connectivity merge conditions"; "keyed as Kiln's random-stream rule says"; "the six `OpKey` inputs of contract 7.2".

### R21-26 · Minor · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, CONTRACT
**Section:** Capability tables at the end of each design section
**Problem:** Capability tables are the build contract, but in reading order they arrive as a dense block after every section, and many cells add nothing: "Failure: —" and "Not expressible" stand where the reader expects a typed failure. The published doc gives them the same weight as explanation.
**Evidence:** ING "Purity | … | Not expressible"; MEC "Typed failures and fixes | `FeatureError { kind, why, fix, at }` | —"; AGT "Priority classes | … | — ".
**Fix:** Replace "—" with "None: cannot fail" or the actual failure, and "Not expressible" with "None: the language cannot express a violation". In the published doc, render capability tables as a visually distinct, collapsible "Build contract" block under each section, so a reader can follow the prose without the tables breaking it.

### R21-27 · Minor · Targets: OVERVIEW
**Section:** `docs/README.md` "Reading order"; Overview
**Problem:** The spec runs to about 230,000 words, and the reading order is "Overview, contract, every tab". No reader reads that; each needs a path. A mechanical engineer, a simulation analyst, a security reviewer and a builder agent need different subsets.
**Evidence:** README "Reading order" has three items, the third being "one file per subsystem".
**Fix:** Add "Reading paths" to the Overview and README: **Mechanical engineer:** Overview, ING's walkthrough, MEC through Tolerancing, "How far to trust a number", MFG's milling and inspection sections. **Simulation analyst:** Overview, FLX's tour and weak-form language, COV "Coverage model", FLX "Error budgets". **Security and compliance reviewer:** contract 7.6 and 7.8, AGT "Labels and injection defence" and "Acts and approvals", KLN "Security". **Builder agent:** the contract, then the owning tab's capability tables and Oracles.

### R21-28 · Minor · Targets: UIX, MFG
**Section:** UIX "Workspace and information architecture"; MFG "Scope, layering and core types"
**Problem:** Sections open with decisions before any description, so the reader is asked to accept a rule about something not yet shown. UIX's first sentence is D-UIX-1; MFG's ownership table is followed by three consecutive decisions (D-MFG-1, D-MFG-2, D-MFG-30) before the first explanatory sentence.
**Evidence:** UIX line 7: "**Decision D-UIX-1:** The UI holds no product state…", before the "Places" and workspace tables. MFG: D-MFG-1, D-MFG-2 and D-MFG-30 appear back to back, then "Machines, fixtures, molds, nests and panels are Assemblies…".
**Fix:** UIX: open with two sentences describing what a user sees (places, then one workspace with presets), put the "Places" and "The workspace" tables first, and move D-UIX-1 after them. MFG: open with the paragraph that says what manufacturing objects are in Crucible ("Machines, fixtures, molds, nests and panels are Assemblies…"), then the `Toolpath` record, then the three decisions as the rules that follow.

### R21-29 · Minor · Targets: ANV
**Section:** Lead; "Kernel rules"
**Problem:** ANV uses its central terms before defining them. The lead's "in rounds against frozen tolerances" and kernel rule 8, "Each question is asked once per tolerance epoch", depend on "rounds" and "epochs", defined 185 lines later in "Numbers, tolerances and decisions".
**Evidence:** Rule 8 at line 33: "predicates are memoized by (pair, epoch)"; the definition at line 218: "Decisions run in rounds by dimension… Within a round, pairs are decided in parallel against tolerances frozen…"; epochs at line 220.
**Fix:** Take "rounds" out of the lead (R21-07). Rewrite rule 8 as "**Each geometric question is decided once**, and its answer is reused until a tolerance grows ('Numbers, tolerances and decisions')."

### R21-30 · Minor · Targets: OVERVIEW, ING, CONTRACT
**Section:** Overview "Principles", "The canonical example", "Platforms", "Roadmap"; ING "The language at a glance"
**Problem:** The Overview copies large parts of the contract nearly word for word instead of summarizing and linking: the seven principles, the canonical example with its explanatory paragraph, the platform tiers and the roadmap table. ING reprints the example a third time. Three copies must be kept identical, and a reader who has read the contract meets the same text again.
**Evidence:** The paragraph beginning "The edge is selected by its role, `end(e)`" is identical in contract section 6 and the Overview, apart from "section 7.1" becoming "contract 7.1"; the principles differ only by trimmed clauses; the Overview's roadmap table repeats contract 13.1's gate texts.
**Fix:** In the Overview, give the principles as seven one-line statements linking to contract 3; show the bracket once, annotated (the walkthrough of R21-19 can live here, with ING linking to it); keep the roadmap as phase, theme and golden products only, linking to contract 13.1 for the gate texts. ING links to the Overview's annotated example instead of reprinting the source.

### R21-31 · Minor · Targets: AGT
**Section:** "Budgets, limits and admission"; "Scheduling on Kiln workers"
**Problem:** Some sourced figures lack the referent that makes them meaningful.
**Evidence:** "Concise detail, the default, uses about a third of the tokens [S31]" (a third of what?); "Anthropic's Opus 4 lead with Sonnet 4 subagents beat one Opus 4 agent by 90.2% [S33], which golden tasks test" (on what measure, and what do golden tasks test?).
**Fix:** "Responses default to concise detail; a concise response uses about a third of the tokens of a detailed one [S31]." "On Anthropic's internal research evaluation, an Opus 4 lead with Sonnet 4 subagents outperformed a single Opus 4 agent by 90.2% [S33]; golden tasks measure whether the same split helps design work."

### R21-32 · Minor · Targets: MEC
**Section:** "Identity of Parts and Assemblies"; D-MEC-33; "Open questions"
**Problem:** One passage reads as correspondence ("MEC confirms the default"), and two different thresholds in units of ρ, never defined in MEC, are discussed by finding id, so a reader cannot tell which number governs what.
**Evidence:** "For KLN's definition tolerance, MEC confirms the default: the smaller of 0.1 µm and 1% of the Item's tightest tolerance, … never below 10ρ." D-MEC-33: the seed quantum is "the larger of 2¹⁰ρ for the sketch and 10⁻⁶ of its diagonal". Open questions: "R9-53: its 2¹⁰ρ floor is declined for R10-39's 10ρ".
**Fix:** "KLN's definition tolerance, the geometry change below which an Item keeps its revision, is the smaller of 0.1 µm and 1% of the Item's tightest tolerance (or general tolerance), and never below 10ρ, where ρ is the Body's resolution (ANV)." In D-MEC-33 add "(ρ as above)". Delete the Open questions bullet (R21-02).

### R21-33 · Minor · Targets: ING
**Section:** "Fidelity, drags, holes and derivatives"
**Problem:** One subsection joins four unrelated topics in four short paragraphs: fidelity being invisible to code, drag specialization, typed holes and derivatives for edit plans. The title is a list, which signals that the section has no single idea.
**Evidence:** The subsection's paragraphs open "Ingot code cannot observe fidelity", "When a drag starts on a literal", "Derivatives serve UIX's edit plans" and "In phase 1, edit plans rank by provenance first".
**Fix:** Move the fidelity paragraph into "`Approx<T>` and the decision rule", where fidelity already matters; move drag specialization into "The Ingot IR and Kiln" beside overrides; move typed holes into "Language service and tools"; keep "Derivatives and edit plans" as its own subsection.

### R21-34 · Minor · Targets: OVERVIEW
**Section:** "Where the field stands"; "Risks"
**Problem:** Two Overview sections state facts about competitors and risks with no line saying what the reader should conclude, and the Risks table's "How the plan contains it" column uses unexplained terms (re-fillet targets, calibration classes with envelopes, held-out splits), which keeps a non-specialist from judging the plan.
**Evidence:** Risks row "Error bounds": "Calibration classes with envelopes and held-out samples, refinement confirmation at `SignOff`, cut-cell totals kept `Estimated`"; row "Blends": "re-fillet targets of 95% of stage-1 cases".
**Fix:** End "Where the field stands" with the synthesis sentence in R21-06. In Risks, give each "How the plan contains it" cell a plain lead clause first: "Error bounds: we measure how often our estimates undershoot on held-out cases and inflate them to cover 99%; every sign-off result is re-checked with one finer solve." Link the technical terms to the Glossary (R21-14).
