# R15 architecture and elegance review

Summary:
1. Check verdicts are not reproducible: the conditional `Pass` means three different things in the contract, COV and ING, and the policy allowance that changes a verdict sits in no key and no pinned input (R15-01).
2. Integrity is joined per node, so one untrusted part name taints every downstream value of the assembly; AGT's own oracle (a merged supplier part leaves R1 changes at R1) cannot pass under KLN's join rule (R15-02).
3. Several pairs of mechanisms do one job: Evidence records and External inputs, Waivers and deviations, a CRDT and a block merge, declassified modules and derived views, two-builder agreement and 100% spot re-execution. Merging each pair removes a concept, an oracle and a failure mode (R15-03 to R15-07, R15-13).

### R15-01 · Critical · Targets: CONTRACT, ING, COV, KLN
**Section:** Contract 5 `CheckOutcome` and gate predicate; ING "Checks"; COV D-COV-4 and COV-O-ERR-3; KLN "Kiln: graph, keys and memoization" (node table) and "Change orders"
**Problem:** The conditional `Pass` has three meanings. Contract 5 says that without an allowance "the verdict is `Undecided { reason: Unquantified(components) }`"; COV makes `Pass { conditional_on }` the verdict and turns it into `Undecided` only "at a gate"; ING's worked table shows `Pass { conditional_on: [model form] }` as the outcome with no allowance, while ING's prose follows the contract. The allowance then "re-evaluates" the check, but KLN's Check key is "`CheckId`, predicate code, subject identities, fidelity": no allowance enters it, and no tab says where a "policy-package record" lives or how evaluation pins it. A cached verdict therefore depends on organization state outside its key, and one Change can give two gate results (principle 4).
**Evidence:** Contract 5: "It counts only when a policy allowance covers each listed component; the check is then re-evaluated with that allowance … and without one the verdict is `Undecided`". COV D-COV-4: "A check resting on one is `Pass { conditional_on }`, meeting a gate only when a cited policy allowance covers each listed part". COV-O-ERR-3: "give `Pass { conditional_on: [ModelForm] }`, `Undecided` at a gate without an allowance". ING Checks table: "`SignOff` … | `Pass { conditional_on: [model form] }` at confidence 0.99". KLN node table row "Check".
**Fix:** Delete `conditional_on` and the re-evaluation step. Allowances are ordinary inputs: a policy Package pinned in `ingot.lock` (see R15-20) whose allowance records the check reads like any other dependency, so they enter its trace and key. The model-form part of the budget is then `Quantified` by the allowance (as an `Estimated` component citing the record) or `NotQuantified`, and the one decision rule gives `Pass`, `Fail` or `Undecided { Unquantified }`. `CheckOutcome` gains `allowances: [ObjectId]` for reports and the `ApprovalSubject`. This removes a verdict variant, the merge-order special case ("a `Pass` whose `conditional_on` gains components ranks below…"), a clause of the gate predicate and a second evaluation pass. The same pinned record covers `Unverified` External Op results.

### R15-02 · Critical · Targets: CONTRACT, KLN, AGT, ING
**Section:** Contract 5 `Labels` (integrity part), 7.6 "Free text is never endorsed by merging"; KLN "Memo entries and backdating", "Labels and export control"; AGT D-AGT-16 and AGT-O-14; ING "Free text"
**Problem:** Integrity is part of the node label and joins through every derivation, while free-text integrity enters at the node that evaluates the string. A Body or Part node holds geometry and names in one value, so a merged supplier STEP file whose names stay untrusted gives its Body node an untrusted label, and every mass, stress, BOM and drawing node downstream inherits it. Any agent that reads those results becomes `data_untrusted`, so every change is at least R2 and never auto-merges. AGT promises the opposite, so its oracle cannot pass against KLN's mechanism.
**Evidence:** Contract 7.6: "Every value evaluated from a free-text span … carries the span's integrity into its node's label." KLN: "A node's label is the join of its inputs' labels." AGT line 772: "A merged supplier STEP file thus yields trusted geometry and untrusted names". AGT-O-14: "a clean R1-shaped change on an assembly with a merged supplier part is R1". A node has one label, so it cannot be trusted for geometry and untrusted for names.
**Fix:** Track free-text integrity on values, not nodes. Ingot already has the type: a string evaluated from an untrusted span is an `ExternalText` value carrying its span's integrity, and `String` values are trusted by construction. `api` returns `ExternalText` values as handles wherever they appear, and node labels keep only confidentiality plus the integrity of typed inputs from unmerged pins. Delete the clause "carries the span's integrity into its node's label" from contract 7.6, KLN and ING, and change D-ING-24 to "values evaluated from free text are `ExternalText`". AGT-O-14 then holds by construction, and the instruction-capable Snapshot rule reads "any visible text derived from an `ExternalText` value".

### R15-03 · Major · Targets: CONTRACT, KLN, COV, MFG
**Section:** Contract 2 (External input, Evidence record); KLN D-KLN-35 and "Physical tests and Evidence records"
**Problem:** Two mechanisms bring signed outside data into a deterministic Evaluation. External inputs are pinned in `ingot.lock` and change "only through an explicit update"; Evidence records are selected by a separate cursor, the evidence watermark, advanced by an audited ref transaction. The glossary even lists "a machine reading" as an External input, which is what an Evidence record is. The watermark adds an input cell, a reporting field, a ref-transaction kind, a "newest record valid at measurement time" lookup and an oracle, and each duplicates what pinning already gives.
**Evidence:** Contract 2, External input: "Signed, content-addressed data produced outside evaluation (… a catalog or regulation dataset, a machine reading). Pinned in `ingot.lock`". Evidence record: "An Evaluation reads the newest record valid at its measurement time … up to the Evaluation's evidence watermark". Releases already "pin the evidence ids they cite".
**Fix:** Make an Evidence record a kind of External input. A rig, lab or gateway result lands in the store; a bot Proposal (or, on protected branches, the same audited transaction that now moves the watermark) pins its id in `ingot.lock` under `[[evidence]]` keyed by `CheckId`, and the check reads the pinned record. Selection ("newest valid at measurement time") moves into the update tool, where it belongs. Delete the watermark from contract 2, KLN's input cells, CI reports and KLN-O-HW-1's watermark clause. One Change then fixes every outcome because its tree pins everything it reads.

### R15-04 · Major · Targets: KLN, CONTRACT, UIX, ING
**Section:** Contract 7.1 `repo` (Loro, reconnection); KLN "Live documents", "Offline work and sync", D-KLN-22, D-KLN-24
**Problem:** Concurrent edits to one Ingot text merge by two different algorithms: Loro's CRDT (Fugue leaves, Kleppmann's tree move) for live sessions, and the three-way block merge with GumTree and Mergiraf-style triples for branches. A reconcile step patches the gap, and the 60 s rule routes a divergence to one or the other, so the same pair of edits merges differently depending on timing. Crucible already has a central relay that checks every update, and offline work beyond 60 s already becomes a branch, so the CRDT handles only short divergences that a sequencer handles more simply. Loro adds a document per (package, module label), block-id mapping and its own oracles.
**Evidence:** KLN: "The relay checks every update against the sender's permissions and enforced locks"; D-KLN-24: offline work "rejoins as a branch when the disconnection exceeded 60 s". Figma's multiplayer post: "Figma isn't using true CRDTs though", because "the server is the ultimate authority" and "can define the order of events" (https://www.figma.com/blog/how-figmas-multiplayer-technology-works/). Replicache: "In Replicache, the server is authoritative", and the client "rewinds … applies the server's patch, and then replays pending mutations" (https://doc.replicache.dev/concepts/how-it-works).
**Fix:** Replace Loro with a server-sequenced edit log per branch: clients apply `SourcePatch`es optimistically, the relay orders them, and clients rebase pending patches with the same `MergeDriver` block merge that branches use, so live and branch merges share one semantics and one oracle. Literal edits stay last-writer-wins by sequence order. Delete D-KLN-22's CRDT, the block-id mapping and the reconcile step; keep per-module replication for labels as per-module sequencing. If the founder keeps Loro, state why a central relay is not enough, and make the reconcile step call the same `MergeDriver` so outcomes cannot depend on timing.

### R15-05 · Major · Targets: CONTRACT, KLN, AGT, MFG
**Section:** Contract 2 (Waiver, Act), 7.6; KLN "Change orders" (Deviation), "Traceability and compliance" (exemptions); AGT "Acts and approvals"
**Problem:** Four records accept a departure under signature: a Waiver (a `CheckId`, Items, effectivity, reason, expiry), a Deviation ("a temporary departure for given serials or lots, with expiry"), a compliance exemption "signed by `quality`", and a policy allowance. The first three have the same shape. Deviations are granted by `grant_deviation`, an Act, although an Act is defined as "an effect outside Crucible" and AGT files it under the `Record` family with `release` and `yank_package`. Compliance also keeps its own verdict enum (`Compliant`, `NonCompliant`, `Unknown`) beside `CheckOutcome`.
**Evidence:** Contract 2 Waiver: "naming a `CheckId`, the Items and effectivity it covers, a reason and an expiry (a revision, a serial range or a date…)". KLN: "Deviation | A temporary departure for given serials or lots, with expiry, granted by the `grant_deviation` Act"; "exemptions signed by `quality`, and verdicts per revision (`Compliant`, `NonCompliant`, `Unknown`)". AGT: "`grant_deviation` | Record | A deviation against a release".
**Fix:** One Waiver record. A deviation is a Waiver whose effectivity is a serial or lot range against a released revision (MFG's conformance checks are what it waives); a compliance exemption is a Waiver of a compliance check by a principal with the `quality` role. Compliance checks return `CheckOutcome` (`Undecided { MissingData }` for "Unknown"). Redefine Act as "an API method whose effect needs a human Approval of an exact plan", which matches the `Record` family, and drop `grant_deviation` as an Act class.

### R15-06 · Major · Targets: CONTRACT, KLN, COV, AGT
**Section:** Contract 5 `Labels` (confidentiality part), 7.8 (encryption domains); KLN "Encryption at rest", "Shared cache and remote evaluation"
**Problem:** `licences` sits in the confidentiality lattice, and that lattice keys encryption domains, worker processes and live replication. Every `Material` carries a `DataLicence` that joins into every Field derived from it, so a design using materials from several licensed databases splits into one encryption domain, one worker process and no deduplication per combination of licences. A licence mostly restricts redistribution, which `release_data` already checks at exits; it rarely restricts who may read inside the tenant.
**Evidence:** Contract 5: confidentiality is "`{ level, controls, scopes, licences }`"; 7.8: "Encryption domains are keyed by tenant and canonical confidentiality label; deduplication never crosses them". KLN: "each worker process serves one (tenant, confidentiality label)". KLN `release_data` "refuses … one whose `DataLicence` forbids redistribution to that recipient".
**Fix:** Move `licences` out of the confidentiality part into a third label part, usage, joined through Kiln like the others but compared only at exits (`release_data`, exports, registry publish) and never used for encryption domains, worker partitioning or replication. A licence that does restrict reading maps to an organization `scope`, which stays in confidentiality.

### R15-07 · Major · Targets: CONTRACT, KLN, ING
**Section:** Contract 7.1 `repo` (module as the unit of a source label); KLN "Labels and export control", "Supplier packages and derived views", D-KLN-31; ING "Packages and versions"
**Problem:** An uncleared principal "compiles against the signature and evaluates the module remotely on cleared workers", but every value derived from that module carries the module's label, so the principal can read none of the results unless something declassifies them. The mechanism that does that, a declassified derived view evaluated on the owner's workers, already exists for suppliers (envelope, frozen geometry, remote parametric model). Two mechanisms do one job, and the module path leaves the reader guessing what the uncleared engineer actually sees.
**Evidence:** Contract 7.1: "whose public signature may carry a lower label through a declassification record, so uncleared principals compile against the signature and evaluate the module remotely". KLN-O-LABEL-1: "an uncleared clone evaluates around an ITAR module it cannot read". KLN D-KLN-31: "Parametric sharing without source uses remote evaluation on the owner's workers".
**Fix:** One mechanism: a labelled module exposes declassified derived views (signature, envelope, interfaces, mass properties), each with its own declassification record, evaluated remotely on cleared workers. Internal uncleared staff and suppliers use the same derived-view records; only the recipient type differs. State in contract 7.1 that any node that joins an undeclassified output is unreadable to the uncleared principal, and rewrite KLN-O-LABEL-1 to check that the uncleared clone sees the declared views and nothing else.

### R15-08 · Major · Targets: ANV, KLN, CONTRACT, PLT
**Section:** Contract 7.1 Anvil (decisions at every fidelity), 13.3 rebuild and recertification rows; ANV D-ANV-28 and its fidelity table; KLN "Progressive results"
**Problem:** Topology, `EntityId`s and every decision already agree across `Interactive` and `SignOff`; only seeding and tracing differ. Yet `SignOff` geometry is a separate computation with different bits, so every downstream node (meshes, solves, drawings, checks) exists twice and is recomputed at `SignOff`. That doubles the graph and is why 13.3 needs a separate recertification row at three times the rebuild target.
**Evidence:** ANV fidelity table: "`Interactive` | `SignOff`'s decisions; sampled seeding and uncertified tracing, validated by `check_body` and Krawczyk checks"; "`SignOff` | … recomputed in the background after `Interactive` results". Contract 13.3: rebuild `Interactive` p90 ≤ 10 s; "`SignOff` recertification after an early edit | p90 ≤ 30 s".
**Fix:** Certify in place. Trace every intersection component from a canonical start point, so a trace is a function of the component, not of the seed that found it. At `SignOff` a certification node runs certified seeding and confirms that it finds exactly the components already traced, and Krawczyk confirms each traced point. On success the `Interactive` result is the `SignOff` result with identical bits; only a failed certification recomputes. Geometry then has one identity across `Interactive` and `SignOff`, Flux reuses meshes across fidelities, and the 13.3 recertification row becomes the cost of the certification nodes.

### R15-09 · Major · Targets: CONTRACT, KLN, ING
**Section:** Contract 7.2 item 5; KLN node table ("Feature call", "Query resolution", "Derived view"); ING "Fidelity, drags, holes and derivatives"
**Problem:** A feature's value depends on fidelity: it branches on `Approx` values, and its geometry differs between `Interactive` and `SignOff` (R15-08). KLN's key for feature calls, query resolutions and derived views lists no fidelity, and contract 7.2 defines the effective fidelity only as "each operation version maps from the requested fidelity", with no rule for Ingot code. As written, an `Interactive` feature result can answer a `SignOff` demand.
**Evidence:** KLN: "Feature call | Code hashes of modules used, argument identities, `CallSite`, overrides in its code". D-KLN-8: "Progressive refinement is a set of independent nodes keyed by fidelity". ING: "Ingot code cannot observe fidelity, so every fidelity runs the same program."
**Fix:** Contract 7.2 item 5 adds: "Ingot nodes (feature calls, query resolutions, checks, derived views) carry the requested fidelity unchanged; operations map it to their effective fidelity." KLN's node table adds "requested fidelity" to those rows. Equal values then deduplicate in the CAS, and Ops that ignore fidelity still share one node.

### R15-10 · Major · Targets: ING, CONTRACT, KLN
**Section:** Contract 5 `CallSite` and `CheckId`; ING "Call sites and names", "Checks"; ING-O-27
**Problem:** A `require` is usually an unnamed statement, so its `CheckId` takes the statement rule "(item path, arm path, nearest preceding binding name, ordinal after it)". Inserting one unnamed `require` before another shifts the ordinal and gives the second check a new `CheckId`, which silently orphans its Waivers, Evidence records, verdict history and approval-subject entries. Only exact duplicates are diagnosed (`ING1103`), and ING-O-27 tests the edited check, not its neighbours. The canonical example's check is exactly this case.
**Evidence:** Contract 5 `CheckId`: "the `require` statement's identity under the `CallSite` statement rule, the `name` if written". Contract 6: `p.require(stress < …)` is unnamed. ING-O-27: "Adding or removing any `require` | Every non-check node key unchanged; the edited check keeps its `CheckId`".
**Fix:** Every `Error`-severity check needs a `name:` (deny-by-default lint `ING-L-UnnamedCheck` with a machine-applicable fix that derives a name from the predicate's left operand, such as `von_mises_max`). The GUI's "Add a check" writes the name, and contract 6 adds `name: "static_margin"`. Extend ING-O-27: inserting a check before a named check keeps that check's `CheckId`.

### R15-11 · Major · Targets: ING, MEC
**Section:** ING "Inference and scalar flavors" (flavor table), D-ING-4, D-ING-20
**Problem:** Inside a body, a `Tol` argument is its nominal and the result is "Exact, unless returned itself". So `rib(t: 2 * thickness)` silently forwards no tolerance, while the same arithmetic on a `Tol` binding outside a parameter slot is affine and keeps it. One expression has two meanings depending on where the value came from, and the tolerance vanishes without a diagnostic, against contract 10's "Explicit over magic. No silent fallbacks."
**Evidence:** ING flavor table: "`Tol<Quantity<D>>` | The nominal; passing it on forwards the tolerance (D-ING-4) | Exact, unless returned itself"; Arithmetic on tolerances: "`a ± b`, `k * a` … | Exact affine combination".
**Fix:** Pick one meaning: arithmetic on a forwarded `Tol` stays an affine `Tol` (the monomorphized flavor carries through), and a slot declared `T` takes the nominal and forwards the whole form. If the founder keeps the nominal rule for cost, add the deny-by-default lint `ING-L-ToleranceDropped` when a `Tol`-flavoured value enters arithmetic whose result is neither forwarded nor returned, with fixes `.nominal` (explicit drop) or a `Tol` binding.

### R15-12 · Major · Targets: CONTRACT, ING, FLX, ANV
**Section:** Contract 7.5, 12 (crate map); ING D-ING-9; FLX "Forms" (`flux-forms`); ANV `anvil-implicit`
**Problem:** D-ING-9 promises "one mechanism" (a hash-consed expression DAG) for constraints, analytic Fields and weak forms, but the spec has three symbolic layers above the kernel IR: Ingot's `Expr` DAG, `flux-forms`' "Form IR", and `anvil-implicit`'s "Expression DAG, tapes". The crate map also forbids the handover: `flux-forms` (Physics row) and `anvil-*` (Geometry row) sit above `ingot-*` (Language row), so they cannot depend on the type Ingot hands them.
**Evidence:** ING D-ING-9: "handed over as a hash-consed expression DAG". FLX crate table: "`flux-forms` | Physics | Form IR, typing, symbolic differentiation". ANV: "`anvil-implicit` | Expression DAG, tapes, evaluators". Contract 12: "Each crate depends only on crates in its own or earlier rows".
**Fix:** Put one hash-consed symbolic expression type in `kernels` (module `kernels::expr`), with typed node sets for forms, implicit functions and residuals, and symbolic differentiation once. Ingot's `Expr<T>` lowers to it, `flux-forms` and `anvil-implicit` extend it, and the kernel IR compiles from it. Name it in contract 7.5 and FLX owns it. This removes two DAG implementations and makes D-ING-9 true.

### R15-13 · Major · Targets: CONTRACT, KLN
**Section:** Contract 7.8 (two-builder agreement; spot re-execution); KLN "Shared cache and remote evaluation"
**Problem:** Release gates and `SignOff` checks accept a cached result only under two-builder agreement, and spot re-execution of shared-cache hits is "100% for nodes that feed released checks". Read together, every released result runs three times (two builders and the re-execution), and the cache saves nothing at release. Either the two mechanisms are redundant, or "released checks" means something the text does not say, such as checks of already released revisions.
**Evidence:** Contract 7.8: "Release gates and every `SignOff` check accept a cached result only when two independent trusted builders produced the same `ObjectId`"; "Spot re-execution of shared-cache hits is weighted by downstream fan-out and is 100% for nodes that feed released checks."
**Fix:** One rule per use. Release gates and `SignOff` checks: two-builder agreement only. Everything else: fan-out-weighted spot re-execution, with 100% reserved for re-verifying already released revisions after a toolchain or `detmath` upgrade. State it in 7.8 and update KLN's capability rows.

### R15-14 · Major · Targets: KLN, MEC
**Section:** KLN "Items" (Item record, D-KLN-45)
**Problem:** The Item record holds "number, kind, name, classification, home repository and path, make or buy, unit of measure and labels", while D-KLN-45 puts the number in source through `part(…, item:)` and the name is `part(…, name:)`. Number and name now live in two places that can disagree, and make-or-buy and unit of measure have no stated source.
**Evidence:** KLN: "An Item record holds number, kind, name, classification…"; D-KLN-45: "Item numbers live in source through `part(…, item:)` … where BOM nodes read them".
**Fix:** The Item record holds only lifecycle facts (revisions, states, effectivity, signatures, system of record) and is keyed by the item number. Identity attributes (number, name, kind, classification, make or buy, unit of measure) are evaluated from source (`part`, `bom_item`, MEC's equivalents) and read by BOM nodes. A changed name is then a source change reviewed like any other.

### R15-15 · Major · Targets: CONTRACT, KLN, AGT
**Section:** Contract 5 (`ControlAuthorization`, policy allowance), 7.6 (write-down, approval credentials, standing releases), 7.8 (egress grants); KLN D-KLN-18, D-KLN-41, "Electronic signatures"; AGT "Acts and approvals"
**Problem:** Crucible has about a dozen kinds of human-signed record (Approval, Waiver, endorsement, declassification, `ControlAuthorization`, policy allowance, purge, recipient-record change, standing release, egress grant, envelope approval, review verdict), and the rules for who may sign each (how many people, which role, which credential level, whether the author or an agent may sign) are prose in contract 5, 7.6 and 7.8, KLN D-KLN-41, D-KLN-18 and AGT. KLN already has one signature record with a `meaning`, so the variety is in the rules, not the data.
**Evidence:** Contract 7.6: "a declassification record signed by two people, one of them an export officer"; "A `standing_release` is approved by two humans"; "Export-officer actions, physical-effect Acts … need AAL3". Contract 5: `ControlAuthorization` "created by an export officer with a second person"; allowance "with two signers". 7.8: "a two-person grant". KLN D-KLN-41 lists eleven items.
**Fix:** One table in contract 5, "Signature meanings": meaning · subject type · signers required · roles · credential level · author may sign · agent may sign. Every two-person, AAL3 and no-self-approval rule becomes a row, Cedar evaluates it, and KLN-O-POLICY-1 fuzzes the table. Delete the scattered prose and D-KLN-41's list in favour of the table.

### R15-16 · Major · Targets: CONTRACT, KLN, AGT, PLT, UIX
**Section:** Contract 2 (Fidelity), 5 (`PriorityClass`), 12 (the `PoolLane` rename); KLN "Scheduling and cancellation"; AGT "Scheduling on Kiln workers"; PLT D-PLT-13; UIX "Interactive edit lane"
**Problem:** "Interactive" names a fidelity, a `PriorityClass`, a `PoolLane` and UIX's edit lane, and they do not line up: the `Interactive` priority class runs on the `Foreground` lane, while the `Interactive` lane serves drags. KLN's table also adds a fifth class, "`Interactive`, drag", which AGT's four-row class table lacks. Contract 12 renamed PLT's pool priority to avoid exactly this kind of clash and left the worst one in place.
**Evidence:** PLT: "`pub enum PoolLane { Interactive, Foreground, Background }`"; "AGT's interactive `PriorityClass` to `Foreground`". KLN: "`Interactive`, drag | … | `Interactive`"; "`Interactive` | A person waiting … | `Foreground`". AGT's class table has `Interactive`, `Agent`, `Ci`, `Batch`.
**Fix:** Keep `Interactive` only as a fidelity. `PoolLane` becomes `Drag`, `Foreground`, `Background`; `PriorityClass` becomes `Drag`, `Foreground`, `Agent`, `Ci`, `Batch` in AGT, KLN and `base`; UIX's "interactive edit lane" becomes "the drag lane". Add "interactive" (for lanes or classes) to the glossary's "Never call it" column.

### R15-17 · Major · Targets: CONTRACT, KLN, ING, ANV, FLX
**Section:** Contract 2 (Op, Node), 7.2; KLN "Keys"
**Problem:** `OpKey` keys more than Op nodes. Contract 7.2 item 1 covers "for Ingot code the code hashes of the modules actually used", so feature nodes key by the `OpKey` formula, and every node with `EntityId`s adds its `CallSite`. Meanwhile the glossary needs an exception to explain the name ("Rust types with the `Op` prefix name operations … except `OpKey`, which keys an Op node"). The name tells a reader the wrong scope, and the exception exists only to excuse it.
**Evidence:** Contract 2, Op: "Rust types with the `Op` prefix name operations (`OpImpl`, `OpCx`), except `OpKey`, which keys an Op node." Contract 7.2 item 1 as quoted; KLN node table.
**Fix:** Rename `OpKey` to `NodeKey` and define it once in 7.2 for every node kind, with per-kind items (operation identity and version, code hashes, `CallSite`, fidelity, host digest). The `Op` prefix then means "operation" without exception, and the glossary entry for Op shrinks to "a node that calls one operation, Wasm component or External Op". Do it before `base` freezes.

### R15-18 · Major · Targets: KLN, CONTRACT
**Section:** KLN (whole tab), contract 12 (`repo` row)
**Problem:** KLN owns an incremental evaluation engine, a content-addressed store, version control, live collaboration, PLM, change control, electronic signatures, Part 11, compliance, supplier data release, identity and authorization, export control, audit, deployment and privacy, in 18,700 words. Its one product crate, `repo`, holds Changes, merge, Items, BOMs, orders, Cedar, labels, signatures, audit and compliance. A reader cannot hold the tab, and one crate with that many reasons to change will be a merge bottleneck for agent swarms.
**Evidence:** KLN "Scope": "This tab owns evaluation, caching, the determinism policy, the CAS, `repo`, collaboration, product lifecycle management (PLM), security, compliance records and deployment." Contract 12: "Product services | `repo` | KLN".
**Fix:** Split the crate now: `repo` (Changes, refs, merge, diff, sync), `plm` (Items, revisions, effectivity, BOM views, orders, compliance) and `trust` (Cedar, labels, signature records, the two-person table of R15-15, audit log, recipient records), all in the Product services row. Reorder KLN to match, with three parts: Kiln and the CAS, repository and collaboration, PLM and trust. If the tab limit allows, move "Deployment" and "Privacy" to PLT, which already owns packaging and the team server install.

### R15-19 · Major · Targets: CONTRACT
**Section:** Contract lead, 2 (glossary), 14 to 17 (ruling logs)
**Problem:** The binding contract is 20,100 words, longer than any tab, and a reader has to dig its current rules out of history. Sections 14 to 17 (about 3,400 words) record how past requests were ruled, the lead is a version history, and glossary rows carry whole mechanisms: Act runs to about 190 words, and Evidence record, Waiver and External Op each state rules that section 7 states again. A builder agent reading "the contract in full" spends a sixth of it on rulings it must not re-apply.
**Evidence:** `sed -n 469,677p docs/contract.md | wc -w` gives 3,388; the glossary (lines 16 to 73) gives 1,547. Contract 2, Act: "Always two-phase … Physical-effect Acts are the transfer Acts … One plan may carry several effects … A human's export … is an audited local write".
**Fix:** Move sections 14 to 17 to `docs/review/rulings.md`, which tab 13 already summarizes, and leave one line in the contract pointing to it. Replace the lead with one sentence ("Binding. Where a tab disagrees, the contract wins; disagreements go to Contract change requests"). Cut each glossary row to a definition of at most 25 words with a pointer to its section, so every rule lives in section 5 or 7 only.

### R15-20 · Major · Targets: KLN, CONTRACT, COV, AGT
**Section:** KLN "Items" (parts-policy package, D-KLN-47), "Revisions and lifecycle states" ("A policy package may replace the state machine"), "Change orders" (allowances); contract 7.1 Hardware CI and 7.6 (site policies)
**Problem:** "Policy" means five unrelated containers: Cedar policies, "policy packages" (parts, numbering, lifecycle, allowances), signed site policies (`unattended_safe`, `start_print`), the `PlacementPolicy` trait and "policy classes" of change orders. Policy packages change check verdicts (the parts-policy check, allowances), yet no tab says which repository holds them, how a design pins them or how they enter a key. A parts-policy update would change verdicts of unchanged Changes.
**Evidence:** KLN: "An organization parts-policy package lists approved `Purchased` Items"; "A policy allowance (contract 5) is a policy-package record changed only through `propose.policy` with two signers". No pinning rule appears in KLN, ECO or the contract.
**Fix:** A policy package is an ordinary Package in the organization's policy repository, versioned and signed like any other, pinned in each design's `ingot.lock` and updated by a bot Proposal like any dependency. Evaluation reads it only through that pin, so its records enter traces and keys. Changing the policy repository itself needs the signers of R15-15's table. Cedar policies stay separate, because they authorize `api` calls and never feed evaluation. Rename "site policy" to "site safety record" and "MCO policy class" to "MCO scope", so "policy" names only Cedar and policy packages.

### R15-21 · Minor · Targets: CONTRACT, KLN, PLT
**Section:** Contract 7.3 (`Certified` grade; the pinned non-canonical Field exception); KLN "Determinism policy"
**Problem:** "GPU computes, CPU verifies" appears twice under different rules. The `Certified` grade (bits independent of the class that computed intermediates, keyed `CpuCanonical`) and the exception "a check may rest on a pinned non-canonical Field … when its residual and error bound are computed canonically" (keyed by the GPU class, pinned by `ObjectId`) are different guarantees with no name for the second.
**Evidence:** Contract 7.3: "`Certified` (output independent of the class that computed intermediates…)"; "with one exception: a check may rest on a pinned non-canonical Field (GPU solves, CPU certifies)". KLN table row "Flux `SignOff` results | `Portable`, or a pinned non-canonical Field…".
**Fix:** Name the second mechanism "witness": a pinned non-canonical Field whose canonical residual and bound make a check reproducible though the Field is not. Define it once in 7.3 beside the grades, and have KLN's table cite "`Portable`, `Certified`, or a witness".

### R15-22 · Minor · Targets: KLN
**Section:** KLN "Determinism policy" (D-KLN-11, D-KLN-12, D-KLN-13)
**Problem:** Three decisions decide nothing. Each restates a PLT decision, and each "Rejected" alternative is "a second rationale here".
**Evidence:** D-KLN-11: "*Why:* one owner per mechanism (R9-40). *Rejected:* a second rationale here." D-KLN-12 and D-KLN-13 repeat the pattern.
**Fix:** Replace the three with one sentence: "`detmath`, GPU grading and reduction order follow contract 7.3 and D-PLT-15 to D-PLT-17." Mark D-KLN-11 to D-KLN-13 as "withdrawn in round 4, see D-PLT-15 to 17" in the decisions log, so the numbers stay stable.

### R15-23 · Minor · Targets: CONTRACT, KLN, AGT
**Section:** Contract 2 (Change); KLN "Change orders"
**Problem:** "Change" is a microversion, while "change request", "change order", "change notice" and "manufacturing change order" are PLM records over many Changes. A PLM reader reads "change order" as an order of Changes. KLN also writes "MCO" but avoids "ECO", because ECO is a tab code.
**Evidence:** Contract 2: "**Change** | One immutable fine-grained edit, like an Onshape microversion." KLN: "Engineering change order | A Proposal with lifecycle scope"; "Manufacturing change order (MCO)".
**Fix:** Keep the industry PLM terms, and add to contract 2's "Never call it" column for Change: "a change order, request or notice". Spell out "engineering change order" and "manufacturing change order" everywhere, with no abbreviations, so MCO goes and ECO never appears.

### R15-24 · Minor · Targets: CONTRACT, COV, MFG, KLN
**Section:** Contract 2 (Evidence record, Evidence level); KLN D-KLN-39; MFG program subjects
**Problem:** "Evidence" names the E0 to E4 credibility scale, signed measurements, the watermark, "simulation evidence" in a program's approval subject, "pinned evidence" for external approvals, and agent "analysis as evidence". The glossary separates only the first two.
**Evidence:** Contract 2: "**Evidence level** | The credibility of a physics model, from E0 to E4 (COV). Distinct from an Evidence record." Contract 7.6: "approved over the posted program and its simulation evidence". KLN D-KLN-39: "external approvals return as pinned evidence".
**Fix:** Rename Evidence level to "credibility level" (C0 to C4), the term ASME V&V 40 uses, and reserve "evidence" for Evidence records. Say "simulation report" for programs, "external approval record" in D-KLN-39, and "analysis attachments" for agents.

### R15-25 · Minor · Targets: KLN, PLT, FLX
**Section:** KLN operation contract (`OpCx::checkpoint`), "Derivatives" (step checkpoints), "Audit and encryption" (log checkpoints), "Sync, scale and recovery" (`--since <checkpoint>`)
**Problem:** "Checkpoint" names a cancellation poll, saved solver state and a signed log head.
**Evidence:** KLN: "`pub fn checkpoint(&mut self) -> Result<(), Abort>; // safe point, every 10 ms of CPU`"; "Step checkpoints of transient solves are CAS objects"; "Checkpoints carry Ed25519".
**Fix:** Rename `OpCx::checkpoint` to `OpCx::safe_point`, which matches KLN's own prose ("reaches a safe point"). Keep "checkpoint" for transparency-log checkpoints (C2SP's term), and call saved transient-solve state "step state", in a `StepState` retention class.

### R15-26 · Minor · Targets: ING, CONTRACT
**Section:** ING "Diagnostics" (`DiagnosticSeverity`); contract 5 (`Severity`); contract 14 ruling ING-8
**Problem:** Contract 14 accepted "ING-8 one `Severity`", but ING defines a second enum, `DiagnosticSeverity` (`Error | Warning | Info | Hint`), beside the check `Severity` (`Error`, `Warning`, `Info`).
**Evidence:** ING: "`pub severity: DiagnosticSeverity, // Error | Warning | Info | Hint`". Contract 14: "ING-8 one `Severity` | Accepted."
**Fix:** One `Severity { Error, Warning, Info, Hint }` in `base`; checks may not declare `Hint` (`ING2001` otherwise).

### R15-27 · Minor · Targets: CONTRACT, ING, KLN, AGT
**Section:** Contract 7.6 (error codes); ING "Diagnostics"; KLN failures
**Problem:** An agent meets three error-naming schemes: `<family>/<code>` from `api` (`label/write_down`), numeric codes from Ingot (`ING6401`), and bare Rust variants in failures (`CalibrationExpired`, `ShareQuotaExceeded`, `ResidencyDenied`, `LockHeld`). The contract says errors take the first form.
**Evidence:** Contract 7.6: "Error codes take the form `<family>/<code>`". ING: "`ING3001`"; KLN: "fail with `CalibrationExpired`".
**Fix:** One rendering everywhere: `<family>/<code>`, with ING's numbers in family `ing` (`ing/3001`, lints as `ing/l-fragile-selector`) and every typed `Failure` variant mapped to `<owner family>/<snake_case>`. AGT keeps the family registry; ING's catalog pages index by both.

### R15-28 · Minor · Targets: KLN
**Section:** KLN "WIT interfaces"
**Problem:** A migration leftover remains in the spec of a system that has not been built.
**Evidence:** KLN: "MEC owns `crucible:product`, formerly `crucible:model`".
**Fix:** Delete "formerly `crucible:model`".

### R15-29 · Minor · Targets: KLN, CONTRACT
**Section:** KLN "Items" (Item kinds); contract 2 (Item, Catalog part, Software item)
**Problem:** The Item kind enum uses names the glossary does not: `Purchased` for a catalog part, `Program` for a manufacturing program, and `Software` for a Software item.
**Evidence:** KLN: "Item kinds are `Part`, `Assembly`, `Document`, `Software` item, `Purchased` catalog part and `Program`, a manufacturing program (contract 2)."
**Fix:** `ItemKind { Part, Assembly, Document, SoftwareItem, CatalogPart, ManufacturingProgram }`, matching contract 2.

### R15-30 · Minor · Targets: CONTRACT, ING, KLN, AGT, UIX
**Section:** Contract 5 (`CallSite`, `ResultStatus`)
**Problem:** `LiteralSite` crosses five tabs and enters node keys, but the contract never defines it. `ResultStatus::Proxy` appears in contract 5 and the 13.3 drag row with no definition.
**Evidence:** ING: "literal overrides keyed by `LiteralSite` (statement identity, call identity, argument slot)"; KLN rule 5 under Keys; AGT and UIX interface rows. Contract 5: "`Pending`, `Proxy`, `Ready(Fidelity)`, …".
**Fix:** Contract 5 adds "`LiteralSite` [ING]: a `CallSite` plus an argument slot; overrides key by it and follow `#[was]`" and "`Proxy`: a dependent shown by affine extrapolation from its last value while it recomputes, never cached".

### R15-31 · Minor · Targets: CONTRACT
**Section:** Contract 2 (Act), 7.6 (Physical safety, Plans and local exports)
**Problem:** The contract breaks its own "say it once" rule. The list of physical-effect Acts appears word for word in 2 and 7.6, and the local-export exemption three times (2, 7.6 Plans, and KLN, which is fine as a consequence).
**Evidence:** Contract 2: "Physical-effect Acts are the transfer Acts `send_to_machine`, `send_robot_program`, `store_machine_job` (OPC UA `Store` only), `send_print_job` and `flash_device`, and the restricted `start_print` and `run_rig_test`"; 7.6 Physical safety repeats the sentence.
**Fix:** Keep both lists in 7.6 only, and let R15-19's one-line glossary entry point there.

### R15-32 · Minor · Targets: KLN, PLT, ECO, CONTRACT
**Section:** Interfaces with other subsystems (KLN, PLT, ECO); contract 12 (`apps/attestation`)
**Problem:** Three facts have two owners. KLN requires "the egress proxy" from ECO, while contract 7.8 and KLN say PLT enforces egress and PLT provides it. KLN requires "attestation" from PLT, while contract 7.8 and KLN's role table make the attestation service KLN's, and contract 12 lists `apps/attestation` without an owner. KLN owns `crucible:host`, while PLT provides `crucible:host/parallel`.
**Evidence:** KLN requires: "ECO | … the egress proxy"; "PLT | … attestation; egress". PLT provides KLN "attestation … label-aware egress". ECO requires from PLT "`crucible:host/parallel`".
**Fix:** Egress: PLT. Attestation service and `apps/attestation`: KLN, packaged by PLT. `crucible:host`: KLN owns the WIT package, and PLT implements `parallel` behind it. Fix the three interface rows and name the owner in contract 12.

### R15-33 · Minor · Targets: CONTRACT, KLN, PLT
**Section:** Contract 12 (crate map rule); contract 7.1 Kiln ("Anvil, Flux and Ingot register node kinds")
**Problem:** The layer rule lets `anvil-*`, `flux-*` and `ingot-*` depend on `kiln`, since `kiln` sits in an earlier row, though they need only `base`'s operation contract. No crate is named as the place where Kiln is wired to the Anvil, Flux and Ingot registries, so every app may do it differently.
**Evidence:** Contract 12: "Each crate depends only on crates in its own or earlier rows"; Engine core holds `kiln`. Contract 7.1: "Kiln is generic: Anvil, Flux and Ingot register node kinds through the operation contract in `base`."
**Fix:** Add one rule: domain crates may depend on `base`, `cas`, `field` and `kernels` but never on `kiln`. Add an `engine` crate in the Product services row that builds a `Kiln` with every registry, which `api` and the apps use.

### R15-34 · Minor · Targets: ING, CONTRACT
**Section:** ING "Call sites and names" (`#[was]`); contract 5 `CallSite`
**Problem:** Each rename leaves `#[was(old)]` in source "until a person removes the attribute", and removing it renames every entity downstream. Over years, source keeps a growing trail of identity scaffolding, and the spec gives no rule for chains (a renamed to b, then to c) or a safe way to retire the attribute.
**Evidence:** ING: "Renaming a binding is a refactor that writes `#[was(old_name)]`, keeping the identity until a person removes the attribute."
**Fix:** `#[was]` holds the original name only, so a second rename rewrites the attribute rather than stacking it. `crucible fmt --retire-was` removes all of them in one Proposal whose review shows the entity renames and the checks, Waivers and Evidence records they touch, typically run at a major revision.

### R15-35 · Minor · Targets: ING, CONTRACT
**Section:** ING "Feature metadata and dialogs"; contract 6
**Problem:** `feature` is both the declaration keyword and the toolbox attribute, so the canonical example writes it twice with different meanings (`#[feature(category:, icon:)]` above `pub feature bracket`).
**Evidence:** Contract 6: "`#[feature(category: "Structure", icon: "bracket")]` / `pub feature bracket(`".
**Fix:** Rename the attribute to `#[toolbox(category:, icon:, handles:)]`, which says what it controls, in ING, the contract example and ING-O-20.

### R15-36 · Minor · Targets: KLN, ANV
**Section:** KLN "Object model", "Hashing, chunking and compression"; ANV D-ANV-9
**Problem:** A large value's `ObjectId` is its root `Index` node's hash, and "chunking parameters belong to the type tag", so identity depends on storage layout. KLN plans to benchmark alternative chunkers in phase 1. Adopting one after releases exist would change the identities of every stored value and, through keys, every cached result. Body encodings are frozen by D-ANV-9; Fields, meshes and Blobs are not.
**Evidence:** KLN: "A large value's identity is its root `Index` node's, and chunking parameters belong to the type tag"; "phase 1 benchmarks their alternatives on Crucible data".
**Fix:** Freeze the chunking rule of every type tag at the phase 1 gate, before the first release is signed, and state that a later change is a new type tag used only by new operation versions, like a frozen operation closure (contract 4).

### R15-37 · Minor · Targets: KLN
**Section:** KLN "Modes"
**Problem:** The section says modes "never" differ in features, and the next paragraph lists features a desktop lacks.
**Evidence:** KLN: "Modes differ in services and data location, never in features." Then: "Without a team server it designs, simulates, evaluates and exports locally; Proposals, releases and every Act need one".
**Fix:** "Modes differ in services and data location. A desktop without a team server lacks only what needs a second party: Proposals, releases and Acts."

### R15-38 · Minor · Targets: CONTRACT
**Section:** Contract 7.1 (Anvil, Flux, Kiln, `repo` bullets)
**Problem:** The decided architecture is written as single bullets of several hundred words. The Flux bullet alone is 694 words with no break, mixing discretization, singular-set rules, calibration, surrogates, bifurcation and a list of other solvers, against contract 11's "paragraphs of at most three sentences".
**Evidence:** `sed -n 201p docs/contract.md | wc -w` gives 694.
**Fix:** Turn each engine bullet into a `####` subsection with short paragraphs or a rule table: Flux as discretization, singular sets, bounds and calibration, surrogates, nonlinear solvers and other solvers. Move the patent facts out of the Anvil bullet to 13.1, which already states the gate.
