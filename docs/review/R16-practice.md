# R16 practice review

Summary: (1) Contract 7.6 treats every Act denial as an attack, so a routine "fix op 3" rejection locks a CAM programmer, a firmware developer or a change board out of that machine or recipient for 24 hours. (2) Program approvals bind to the controller's software version and the post version, so a control update or a post release voids every approved program. The contract's own program subject also omits the setup sheet, tools and machine class that MFG binds. (3) The everyday iteration loops have no workable ceremony. Each firmware flash, each print and each prove-out push needs its own AAL3 Approval, edits made during prove-out become nonconformances, and a one-off job-shop program has no defined minimal path. Practitioners will do this work outside Crucible. Beyond these three, the tabs lack tools that incumbents' users touch every day: sketch trim and extend, toolpath editing, machine-model authoring, approval routes, obsolescence monitoring, schematic and layout review diffs, and part-reuse search.

### R16-01 · Critical · Targets: CONTRACT, AGT, UIX, MFG, KLN
**Section:** Contract 7.6 "Act approvals"; AGT "Approval limits" row; UIX approval page; MFG "Approval, transfer and physical safety"
**Problem:** Every denial blocks re-preparing a plan to the same recipients for 24 hours, and a session may hold at most three pending requests. The rule applies to human-prepared plans as well as agent ones. Approvers use rejection as their normal way to say "fix this": a shop lead rejects a program because of a feed in op 3, and a change board rejects a release because a drawing note is wrong. Under this rule the corrected program cannot go to that machine until tomorrow. A rejected release also blocks every release delivery to the organization's own ERP recipient for a day.
**Evidence:** Contract 7.6: "At most three pending requests per session; a denial blocks re-preparing a plan to the same recipients for 24 h and offers 'report as suspicious', which freezes the session." AGT's capability table: "Three pending; 24 h block after denial … `act/denied_cooldown`". UIX's Proposal review offers "Request changes" (10-ui line 498), but the approval page has only approve and deny. MFG step 4 sends every `Prototype` program through an approved `send_to_machine` plan, so prove-out rejections are routine.
**Fix:** Give the approval page three outcomes. **Approve.** **Return for changes:** closes the request with a reason and no cooldown. A new plan with a different digest may be prepared at once, and resubmitting the same digest is refused with `act/returned_unchanged`. **Deny as suspicious:** today's behaviour, which freezes the session and applies the 24 h block. Count the pending limit per (session, Act class, recipient) and apply it only to contexts with an agent in the delegation chain. Human sessions batch effects into one plan instead. Contract wording: "A return for changes closes the request without penalty; only a denial marked suspicious blocks re-preparing a plan to the same recipients for 24 h and freezes the session." Add AGT-O-9 cases for both outcomes.

### R16-02 · Major · Targets: CONTRACT, MFG, KLN
**Section:** Contract 7.6 "Manufacturing programs"; MFG D-MFG-4; KLN D-KLN-38
**Problem:** A program's machine class includes the controller's software version and the post version. Updating the control's software, which shops do for bug fixes and options, therefore moves every approved program out of its class. Released programs then stop flowing through the pull path until each is approved again. A Crucible post-engine release has the same effect: it changes every subject even when re-posting produces identical canonical NC text.
**Evidence:** Contract 7.6: "bound to a machine class (machine package, controller family and software version, post version)". D-MFG-4 repeats it. MFG's canonical hash already covers the posted token stream (D-MFG-24), so the post version adds nothing to what the approver reviewed.
**Fix:** Define the machine class as {machine package digest, controller family, `MotionSemantics` digest, `FileRules` digest}. The controller software version becomes instance data checked at transfer against the package's qualified version range. A version outside the range blocks transfer with `ControllerVersionUnqualified` until MFG-O-POST-3's capture runs once for the new version. If the recaptured `MotionSemantics` digest is unchanged, the class and every approval persist. Remove the post version from the subject. A post bump that reproduces the canonical hash keeps the approval. One that changes it needs a new approval, and the page shows the semantic NC diff.

### R16-03 · Major · Targets: CONTRACT, MFG, KLN
**Section:** Contract 5 `ItemDefinition` and `ApprovalSubject`; MFG "Approval, transfer and physical safety" (`ProgramSubject`); KLN "Revisions and lifecycle states"
**Problem:** The binding contract defines a manufacturing program's subject as "the posted program and its simulation evidence". Its `ItemDefinition` holds only "posted text and simulation evidence ids". MFG's `ProgramSubject` also binds the machine class, nominal tools, setup sheet, verdicts and block map, and KLN's table adds the machine class and tools to the definition. Because the contract wins, a changed setup sheet would not void an approval, even though the setup sheet carries work offsets dimensioned to datums, fixtures and the on-device steps. Three documents now define one safety subject.
**Evidence:** Contract 5: "Act plans and manufacturing programs have their own subjects (the posted program and its simulation evidence)". Contract 5 `ItemDefinition`: "for a manufacturing program, its posted text and simulation evidence ids". MFG: "`ProgramSubject { programs, machine_class, tools, setup_sheet, verdicts, block_map }`". KLN table: "`Program` | Posted program, simulation evidence ids, machine class, nominal tool assemblies (MFG)".
**Fix:** In contract 5, replace both phrases with one reference: "for a manufacturing program, MFG's `ProgramSubject`: canonical program digests, machine class, nominal tool assemblies by T number, setup sheet, simulation verdicts and block map". KLN's table then cites that list instead of restating it. MFG-O-SAFE-1 adds a case where a changed setup sheet voids the Approval.

### R16-04 · Major · Targets: CONTRACT, ELX, MFG, AGT
**Section:** Contract 7.6 "Firmware" and "Approval credentials"; ELX D-ELX-29; MFG "Printers, 3MF and print transfer" and "Approval, transfer and physical safety"
**Problem:** Each `flash_device` needs an Approval of one image digest and target, each `send_print_job` its own, and each `Prototype` program push its own, every one with AAL3 WebAuthn on the approval page. Embedded developers flash dozens of times an hour, makers iterate prints, and machinists re-send a program several times during prove-out. They will flash with their own probe tools and print from the slicer instead. The record that D-ELX-29 exists to keep is then never written. `standing_release` already solves the same problem for data transfers, but nothing covers physical effects.
**Evidence:** D-ELX-29: "Every client flashes a board only through the transfer Act `flash_device`". Contract 7.6: "Its Approval covers the image digest and the target". `standing_release` covers only "recipients, channel, schema, label ceiling and expiry".
**Fix:** Add one restricted Act, `bench_session`. It takes one AAL3 Approval over {the named person at the device, device serial (board, printer or machine), probe or gateway, payload kind, Software item or program Item lineage (one branch), maximum count, expiry of at most 8 h, hazard acknowledgements from the Network or machine package}. Transfers inside the session need no further Approval, but each keeps every check: read-back, hold in reset, no start, the gateway's offset check and the canonical hash. The session ends early on expiry, on a hazard change in the Network, or on a payload outside the lineage. Agents cannot open or extend one. The approval page lists every transfer in the session afterwards. Phase it with each underlying Act, with oracles AGT-O-new and ELX-O-FW-3 for count, lineage and expiry bounds.

### R16-05 · Major · Targets: MFG, KLN
**Section:** MFG "Approval, transfer and physical safety" (edit capture); MFG "Quality records"; KLN D-KLN-38
**Problem:** Every edit captured at the control opens a Proposal, and parts made from the edited program get a nonconformance record, whatever the program's state. In `Prototype`, editing at the control is the prove-out itself: machinists adjust feeds, depths and clearances on the first parts. The rule therefore turns ordinary prove-out into a stream of nonconformances that a quality system must disposition. It also leaves the first-article record pointing at a program revision that never ran unedited.
**Evidence:** MFG: "An edited program opens a Proposal with its semantic NC diff. Parts made from it get a nonconformance record for disposition (R10-32)." The Nonconformance row covers "parts from programs edited at the control". D-KLN-38 moves a program to `Proven` "after a first-article record".
**Fix:** Split the rule by state. In `Prototype`, a captured edit opens a Proposal on the program Item's branch and enters a prove-out log, and the parts get no nonconformance. The first-article record names the captured revision that actually ran, and `Proven` requires that revision merged into the program source, so the released program is the one that ran. A nonconformance applies only when a `Proven` or `Released` program is edited at the control. Add both cases to MFG-O-SAFE-4.

### R16-06 · Major · Targets: MFG, KLN, AGT
**Section:** MFG "Approval, transfer and physical safety"; KLN "Change orders"; AGT D-AGT-20
**Problem:** The spec describes the full aerospace path (MCO, `Prototype`, first article, `Proven`, `Released`) and never states the minimum path for the commonest shop: high-mix, low-volume, where a program runs once. It is silent on three questions. Can the human who prepared a transfer plan approve it? Does a `Prototype` program need a manufacturing change order? How does a one-off job close without ever reaching `Released`? A one-person shop cannot tell from the tabs whether it can send its own program at all. KLN's rule that "an order's author cannot be its only approver" covers orders only.
**Evidence:** MFG step 3: "The program releases as an Item through KLN's manufacturing change order: `Prototype`, `Proven` … `Released`". KLN: "An order's author cannot be its only approver". D-AGT-20 rejects "approval by any authority holder" but does not address the preparer.
**Fix:** Add a "Minimum ceremony" table to MFG, with one row each for a one-person shop, a job shop and a regulated production shop. It states the following:
- A program Item is created in `Prototype` by its first transfer plan, without an order.
- A human who prepared a transfer plan may approve it under the Cedar policy `self_approve_transfer`, off by default, which the site's safety officer enables. AAL3 still applies.
- A one-off job closes in `Prototype` with a run record linking program, serials and results.
- An MCO is needed only to enter `Released`.

Add MFG-O-SAFE-7 for the self-approval policy and its audit.

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

### R16-08 · Major · Targets: MFG, ECO
**Section:** MFG "Machines, controllers and posts"
**Problem:** Simulation, posts, the gateway and program classes all depend on a machine package: kinematic chain, envelope, limits, spindle curves, tool changer and `MotionSemantics`. The tab says only "Builders publish machine packages, shops extend them". It has no capability row, contract, failure or oracle for building one. Machine builders rarely publish open kinematic models; shops get them from their CAM or verification vendor. GP3 in phase 2 needs the reference shop's machines modelled before any program can pass simulation.
**Evidence:** No capability table in MFG names machine-package creation. "Forward and inverse kinematics" assumes a `Machine` exists. MFG-O-POST-3 qualifies a post, not the kinematic model behind it.
**Fix:** Add the row "Machine package builder", phase 2. Its contract: `machine(structure: Asset, axes: [Axis { joint: Query, travel, rapid, accel, jerk }], spindles, tool_changer, controller) -> Machine`, built from the builder's STEP and spec sheet. Its failures are typed checks: the chain closes, travels match the spec, the home pose is collision-free, and pivot and offset lengths agree with the control's kinematic parameters read through a connector. Add oracle MFG-O-KIN-3: the reference shop's machines, built from STEP and spec sheets, reproduce the controls' stored kinematic parameters within 0.01 mm and the captured crash corpus. ECO lists any machine-definition formats Crucible reads, each with its licence check.

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

### R16-11 · Major · Targets: MEC, ECO
**Section:** MEC D-MEC-31; "Holes and threads"; "Standard parts and fasteners"; Open question 1
**Problem:** Thread diameter–pitch series, clearance holes and fastener dimensions are licensed data packages awaiting counsel, and "until then an organization supplies its own table packages". `ThreadSpec::iso_metric("M5")`, the tab's own example, needs ISO 261's coarse pitch, so a new user's first tapped hole can fail `UnknownSize`. Standard fasteners arrive only in phase 2, and only as licensed packages. Engineers used to free toolbox libraries and supplier catalogues would meet a paywall or an error on their first day.
**Evidence:** D-MEC-31; MEC's "Holes and threads" table marks `crucible::standards::thread_plans` and `clearance_holes` as "Licensed data"; Open question 1. The formula packages (`iso_metric_thread`, `unified_thread`) already compute profile and tolerance once diameter and pitch are given.
**Fix:**
1. Designations that carry their pitch (`M5x0.8`, `1/4-20 UNC`) resolve from the formula packages with no table. The UI always writes the explicit form, so source never depends on a series table.
2. The coarse-pitch lookup stays a data package, decided with counsel.
3. Clearance holes default to a Crucible-defined rule (nominal plus a class allowance), labelled `CrucibleDefined` and checked, until ISO 273 data can ship.
4. Fastener geometry defaults to manufacturers' `parts::` packages published under their own terms (D-ECO-18), the model supplier catalogues use. Standard-dimension packages stay optional.

State in the phase 1 row that a design compiles with no licensed package installed.

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

### R16-13 · Major · Targets: ELX, KLN, ECO
**Section:** ELX D-ELX-5, "Catalog parts"; KLN "BOM views and where-used"; ECO D-ECO-18
**Problem:** Offers and catalog definitions change only through an explicit update, and part lifecycle sits in a pinned facet. Nothing tells a released product that one of its parts has gone end-of-life or received a product change notice. Electronics and parts engineers track obsolescence weekly; it is the main reason released BOMs change. KLN's where-used index "drives … end-of-life notices", but no tab produces the event, owns the check or defines the report.
**Evidence:** D-ELX-5: "changed by an explicit update". KLN line 572 names end-of-life notices as a use of where-used. No capability row anywhere covers lifecycle monitoring. A search of the spec for "obsolescence" and "PCN" finds only the `Obsolete` state.
**Fix:** ECO's catalog connector emits `part.lifecycle_changed` and `part.change_notice` events, applied as dated External input updates on a monitoring branch, never on released source. KLN adds a nightly check, `obsolescence`, over the where-used of released revisions. For each end item it reports the affected Items, effectivity, alternates found by re-running each `CatalogSelection` with the part excluded, and a last-time-buy quantity from MBOM demand when ERP supplies it as an External input. Each finding opens a change request. Phase 3, with oracle KLN-O-PLM-12.

### R16-14 · Major · Targets: ELX, CONTRACT, PLT
**Section:** ELX D-ELX-25, "Engine choice"; contract 2 "External Op", 7.8, 9 "Parity", 13.2 phase 1 desktop install
**Problem:** Vendor SPICE models run only in ngspice as an External Op. External Ops run only on Linux untrusted-evaluation workers, and "air-gapped installs need a local Linux worker". An engineer on a Windows or macOS laptop, the daily LTspice loop of a buck converter with the vendor's model, must reach a server for every run. Offline it cannot run at all. A circuit simulator with no local vendor models loses to free incumbents on the first afternoon.
**Evidence:** Contract 2: an External Op "Runs only on untrusted-evaluation workers (section 7.8)". Contract 9: "air-gapped installs need a local Linux worker". D-ELX-25: "Vendor models run in ngspice as an External Op by default". A model moves to the native engine "only after matching ngspice on its own test bench".
**Fix:** File a contract change. A desktop may run an External Op locally in an OS-sandboxed process with egress denied. Its results take platform class `Unverified` and fidelity at most `Interactive`; they are never written to the shared cache and never decide a gate, which still needs two microVM receipts (7.8). In ELX, run unencrypted vendor subcircuits natively wherever they use only supported SPICE3 primitives and behavioural sources. Add phase 3 B-sources and the PSpice and LTspice behavioural dialect to ELX-O-SIM-2's corpus, so most vendor models need no External Op at all.

### R16-15 · Major · Targets: ELX, UIX, KLN
**Section:** ELX "The drawn schematic", D-ELX-27; KLN "Diff, large assemblies and references"; contract 7.6 Proposal review
**Problem:** Schematics and layouts are `table { … }` rows, and review shows "feature, geometry, metric and source diffs". No tab defines what an electrical reviewer sees. A row diff of segment coordinates is unreadable. KLN's geometry diff (changed regions, Hausdorff distance) does not show what changed electrically: a moved symbol, a pin moved to another net, a changed value, copper added on L3. Electronics review in incumbents is visual and net-aware.
**Evidence:** KLN's diff table lists Source, Feature, Geometry, Metric and BOM diffs only. ELX never mentions a diff. Contract 7.6: "Proposal review shows feature, geometry, metric and source diffs."
**Fix:** ELX defines two diff views as Kiln nodes. The **schematic diff** shows symbols added, removed or moved, wires whose net membership changed highlighted in both versions, and value and part changes. The **layout diff** shows a per-layer copper XOR computed exactly from the integer data, moved parts with displacement arrows, and changed rules with the objects they now affect. A net-partition diff lists merged, split and renamed nets. UIX shows these views in Proposal review for the Electronics preset. Phase 3, with oracle ELX-O-SCH-6: every seeded change appears once, and unchanged items never appear.

### R16-16 · Major · Targets: KLN, MEC, AGT
**Section:** KLN "Items"; MEC "Standard parts and fasteners"
**Problem:** The Item record has a "classification" field but no classification scheme, attribute search or shape search. Part proliferation is one of the costs enterprise PLM is bought to cut. Engineers search by class and attributes ("M6 standoff, 20 mm, aluminium") or by shape before creating a new item number. Crucible already computes name-free `GeometryId`s and certified mass properties, so it could do this better than incumbents, but the spec never asks it to.
**Evidence:** KLN line 509 lists "classification" among Item record fields; nothing defines it. No `api` Read method searches Items by attributes or shape.
**Fix:**
- A classification schema in the policy package: classes with typed attributes, so units check.
- A Read method `read.search_items(class, where:, shape_like: Body, tol)`, ranked by name-free shape descriptors cached per `GeometryId`.
- A new-part Proposal that shows the five most similar released Items.
- An `Info` check, `duplicate_candidate`, above a similarity threshold.

Phase 3, with oracle KLN-O-PLM-13: seeded duplicates in a 10,000-Item corpus rank first.

### R16-17 · Major · Targets: KLN, MFG
**Section:** KLN "Change orders", "Electronic signatures" (QMSR, AS9100); MFG "Quality records"
**Problem:** KLN cites ISO 13485 through FDA's QMSR and AS9100 assessment packages, and lists CAPAs as a source of change requests. Yet no tab defines a corrective and preventive action record. That record links a nonconformance or complaint to root cause, containment, actions and a verified effectiveness check. Medical and aerospace quality engineers cannot close the loop inside Crucible, and the design history the tab promises has a hole where auditors look first.
**Evidence:** KLN's change-request row: "from nonconformances, complaints, CAPAs, field failures or agent findings". MFG has a Nonconformance row but no CAPA row. KLN D-KLN-49 builds an assessment package for Part 11 and AS9100.
**Fix:** KLN adds a signed `Capa` record holding:
- trigger: nonconformance, complaint, audit finding or field failure;
- affected serials through where-used;
- containment and root cause, with a method field;
- actions as links to change requests, MCOs or training records;
- an effectiveness check (a `CheckId` with an Evidence record after a stated period);
- a closure signature by `quality`.

MFG's nonconformance row links to it. Phase 3, with oracle KLN-O-PLM-14: a CAPA cannot close before its effectiveness check passes.

### R16-18 · Major · Targets: MFG, KLN, ECO
**Section:** MFG "Factory connection and digital twin" (MBOM and routings); KLN "BOM views and where-used"
**Problem:** The MBOM is one view derived from EBOM rules, with routings and work centres. Real products are often made in two plants, or by a contract manufacturer and an in-house line, each with its own MBOM, routings, programs and suppliers for the same EBOM revision. Nothing keys an MBOM or routing by site, so MBOM reconciliation, cost and ERP mapping assume a single factory.
**Evidence:** MFG's MBOM row: "EBOM-to-MBOM rules as Ingot (phantoms, kits, stations, consumables); routing steps with times and work centers". KLN: "MBOM | Phantoms, kits, raw stock, consumables, manufacturing-only Items". No "plant" or "site" appears in either tab.
**Fix:** Key MBOM, routings and work centres by (EBOM configuration point, `Site`). `Site` is a policy record naming the plant or supplier and its ERP mapping. Run MBOM reconciliation per site, compute cost per site, and let the ERP connector map per plant. Program Items already bind machine classes, so they need no change. Phase 3, with oracle MFG-O-FAC-8: two sites with different routings both reconcile against one EBOM.

### R16-19 · Major · Targets: MFG
**Section:** MFG "Machines, controllers and posts" (post qualification, D-MFG-23); Phasing
**Problem:** A control family's post ships only after its crash corpus is captured on the reference shop's controls. Okuma and Mazak arrive in phase 3 and Mitsubishi, Brother and Hurco in phase 4. The generic ISO 6983 post exists from phase 2, but an undeclared `MotionSemantics` returns `Unsupported` instead of passing. A shop whose machines are not among the four phase 2 families therefore cannot get any program through simulation and approval, for one or two phases. No path lets a shop qualify its own control.
**Evidence:** MFG: "A family's post ships only when its crash corpus, captured on the reference shop's controls, matches `MotionSemantics`". D-MFG-23: "An undeclared semantic sweeps a conservative envelope and returns `Unsupported` instead of passing."
**Fix:** Add a "shop-qualified family" path in phase 2. The shop runs MFG's published capture procedure in program-test mode on its own control and produces a `MotionSemantics` record and corpus. That record is signed by the shop's named qualifier and scoped to the shop's tenant and serials. MFG-O-POST-3's comparison runs on it unchanged. Programs posted for that class carry the label "shop-qualified" on the approval page. A family becomes generally supported when the reference shop's capture confirms it.

### R16-20 · Minor · Targets: MEC
**Section:** MEC "Direct edits and wraps"; Phasing
**Problem:** Phase 1 offers only push-pull on imported B-reps, while delete, move and replace of faces wait for phase 2. Removing fillets, logos and holes from a supplier's STEP file is the most frequent direct edit. Phase 1 needs it, because its enclosure checks run against imported boards and its assemblies use supplier models.
**Evidence:** MEC: "Phase 1 offers push-pull; moves, replacements and rule detection follow in phase 2." `anvil::defeature` already exists for `InstanceRepr::Defeatured`.
**Fix:** Move `delete_faces` with neighbour healing, and `defeature(body, rules)` as a feature, to phase 1, both using MEC-O-PF-9. Keep moves, replacements and rule detection in phase 2.

### R16-21 · Minor · Targets: MEC, KLN, ELX
**Section:** MEC "Design checks" (`decides_on` table: mass); MEC "Standard parts and fasteners"; ELX "Electrical facets"
**Problem:** Mass checks need `Guaranteed` bounds, and mass properties come from geometry and `Material` density. Purchased parts arrive as simplified or hollow STEP bodies: a motor, a battery, a populated board. Their computed mass and centre of gravity are therefore wrong by large factors, yet they carry certified-looking bounds. No record lets a datasheet mass override the computed one.
**Evidence:** MEC: "Fits, clearance, interference, thickness, mass | `Guaranteed`". ELX's catalog facets list a "3D body" and "Specifications" but no mass. MEC hands Flux "mass properties with their bounds" (D-MEC-12).
**Fix:** Add `part.mass_properties(declared: { mass: Tol<Mass>, cg: Tol<Point>, inertia: Option<…> }, source: Datasheet | Measured(Evidence))`. It replaces computed values in roll-ups, and reports label it "declared". Catalog parts carry a mass facet. A `Warning` check flags purchased Instances whose computed mass is used without a declaration.

### R16-22 · Minor · Targets: MFG
**Section:** MFG "Turning, EDM, gears and grinding" (gear data and inspection); "Inspection and measurement"
**Problem:** GP3 in phase 2 needs gear inspection plans "for gear machines or CMMs". DMIS output and QIF Plans arrive only with CMM programs in phase 3, so phase 2's plan has no machine-readable format.
**Evidence:** "Gear data and inspection | Profile, helix and pitch plans … for gear machines or CMMs | … | 2"; "CMM paths and programs | … DMIS and QIF Plans … | 3".
**Fix:** Phase 2 writes gear inspection plans as QIF 3.0 Plans plus the PDF gear data table, through ECO's QIF writer, and moves "QIF Plans write" to phase 2. DMIS and path generation stay in phase 3.

### R16-23 · Minor · Targets: MFG, MEC
**Section:** MFG "Tools, stock, setups and workholding" (setup sheet, blank and hand-off)
**Problem:** Multi-operation parts need in-process drawings: the shape and dimensions after setup N, with grinding or heat-treat allowances. Machinists and inspectors work to them between operations. MFG already computes setup N's output stock as setup N+1's blank, but only the setup sheet is a drawing, and it shows offsets and tools rather than in-process dimensions.
**Evidence:** "Blank and hand-off | … setup N's stock is setup N+1's blank". `setup_sheet` lists offsets, fixtures, tools and workingsteps.
**Fix:** Add `in_process_drawing(program, after: SetupRef, template)`, built from the hand-off Body. It is dimensioned from the setup's datums, lists allowances per face, and carries characteristics that MFG's allocator labels as in-process. Phase 2, with MFG-O-SETUP-1.

### R16-24 · Minor · Targets: ELX
**Section:** ELX "The drawn schematic" (editor behaviour 2 and 3)
**Problem:** A connection made only in code renders dashed until a human draws it, and `schematic_matches_network` blocks release. Every connectivity edit by an agent or the code editor therefore leaves manual drawing work before release. Agents cannot fix this, because the fix is a drawing gesture.
**Evidence:** "A connection made only in code renders dashed until one gesture draws it or places a label." "`schematic_matches_network` blocks release."
**Fix:** Add `schematic.autodraw(nets)`, a deterministic Wasm component. It proposes segment or label rows for code-only connections, using net labels when a wire would cross more than a stated number of symbols, and ordering work by canonical numbers. It opens a Proposal that a person reviews. Phase 3, with ELX-O-SCH-1.

### R16-25 · Minor · Targets: CONTRACT
**Section:** Contract 2 "Fidelity" and "Approval"
**Problem:** Engineers say "sign-off" for a person's approval. The contract forbids "sign-off" as a noun for Approval, then names the top fidelity `SignOff`. Phrases such as "the `SignOff` check passed" or "sign-off stress" read to a practitioner as a person signing, the confusion the "Never call it" column exists to prevent.
**Evidence:** Contract 2: Approval, "Never call it: 'sign-off' as a noun for this"; Fidelity: "`SignOff` (converged or exact)".
**Fix:** Rename the fidelity to `Final` (`Preview`, `Interactive`, `Final`) before any operation version or WIT package freezes, at the same phase 0 point as the Flux rename. Keep "sign-off" banned for Approvals. This is a contract change request.

### R16-26 · Minor · Targets: MFG
**Section:** MFG section order
**Problem:** "Approval, transfer and physical safety" is the second section. It uses program subjects, setup sheets, `wear_range`, D registers, `BlockMap`, restart points, the program registry and drip feed before the tab defines machines, tools, setups, posts or simulation. A machinist reading from the top meets the safety path before the things it protects.
**Evidence:** Section order at lines 5, 84, 149, 216 and 323. `BlockMap` is first defined at line 214, and the setup sheet at line 222.
**Fix:** Move "Approval, transfer and physical safety" after "Programs, regeneration and agents". Leave a two-sentence pointer in "Scope, layering and core types" saying that every program reaches a device only through that path.

### R16-27 · Minor · Targets: MFG, ELX
**Section:** Body text throughout
**Problem:** Review-finding ids sit in design prose: 42 lines of MFG and 36 of ELX cite `(R10-13)`, `(R4-24, R4-27)` and similar. To an engineer reading the spec they are noise. They record how the text came about, which the Adversarial review tab already maps.
**Evidence:** For example MFG: "Gouge and collision checks then run at both ends of `wear_range`, so wear adjustments at the control stay verified (R10-13)." ELX: "MFG owns the factory handoff (R3-25, R4-24, R4-27)". MEC keeps them almost entirely to Open questions.
**Fix:** Remove R-ids from body prose and capability tables in MFG and ELX. Keep them only in decisions' *Why* clauses, where they justify a choice, and in Open questions, as MEC does.

### R16-28 · Minor · Targets: MEC, MFG, ELX
**Section:** Sources and in-text citations
**Problem:** The three primary tabs use three citation styles: MEC quotes inline and lists URLs, MFG uses bracketed labels (`[Haas G-codes]`), and ELX uses numbers (`[85]`). A reader moving between tabs cannot tell at a glance what `[85]` is, while `[IPC store]` is self-describing.
**Evidence:** ELX: "IPC-6012F, IPC-A-610J and IPC J-STD-001J … [85][86]". MFG: "[IPC store]". MEC: "[ISO 10303 notice]", plus unlabelled lists.
**Fix:** Adopt MFG's bracketed short labels in every tab, and add the rule to contract 11's style list.

### R16-29 · Minor · Targets: ELX, MEC, MFG
**Section:** ELX "Wire harnesses"; MEC "Routing"; MFG "Electronics and harness manufacturing handoff"
**Problem:** A harness engineer's work is split three ways by D-MEC-26: connectivity and wire tables in ELX, 3D routes and formboard geometry in MEC, and the manufacturing package in MFG. No tab walks through one harness from connector selection to formboard. The phases also differ (MEC 3, ELX 4, MFG 4), and the reader has to assemble that order alone.
**Evidence:** D-MEC-26; ELX: "ELX's part lands in phase 4 … MEC's phase 3 routing uses declared bundle diameters until then"; MFG's harness row in phase 4.
**Fix:** Open ELX's "Wire harnesses" with a five-step numbered walkthrough: connectivity, route, lengths, checks, package. Each step names its owner and phase in one line, which "say it once" permits because the step only points to the owner.

### R16-30 · Minor · Targets: CONTRACT, UIX, KLN
**Section:** Contract 7.6 "Approval credentials"; contract 9 Tier 2; CCR-UIX-5 ruling
**Problem:** No Act is approvable on a phone, including release and change-notice Acts with no physical effect and no `controls` label. Change board members approve engineering changes from phones in incumbent PLM, and an approval waiting for someone to reach a desk delays every release. The ruling's reasons, physical effects and AAL3, do not apply to an uncontrolled release.
**Evidence:** Contract 7.6: "Synced passkeys sign in but never approve or sign, and Crucible's phone clients offer no approval." Contract 16, CCR-UIX-5: "no Act is approvable on a phone".
**Fix:** Allow the release, change-notice and deviation Act classes, with no `controls` label and no physical effect, to be approved in a phone browser on the approval origin. The approver must use a roaming security key from the AAGUID allowlist (NFC or USB), which meets the device-bound requirement. Physical-effect Acts, `controls` payloads and Part 11 signatures stay off phones.

### R16-31 · Minor · Targets: MEC
**Section:** MEC "Sheet metal"
**Problem:** `SheetParams` is named but never defined. Sheet-metal designers work from gauge or style tables, per material and thickness, that set the default inside radius, relief type and size, and K factor or bend table. Without such a record, every part restates them, and `check::sheet` cannot say which shop standard a part follows.
**Evidence:** "A sheet-metal part is a `SheetBody`: the folded `Body`, the flat `Body`, a bend table and `SheetParams`." No other mention appears.
**Fix:** Define `SheetParams { material, thickness: Tol<Length>, inside_radius, relief: ReliefRule, bend_rule: BendRule, min_flange }` and `SheetStyle`, a shop data package of `SheetParams` rows keyed by (material, gauge). `sheet_from(…, style: shop::al5052_2mm)` reads it, and `check::sheet` reports the style it applied. Phase 2, with MEC-O-SM-1.
