# ING round 4 packet

Your tab is `docs/spec/01-ingot.md` at v3 (tag `round-3`). Round 4 fixes, in one pass: the 42 third-review findings that target it (5 Critical, 21 Major, 16 Minor), its 0 `[unverified]` claims, its open questions and the known items below. Contract v7 is binding; its section 18 lists the rulings on this review, and many findings below are already settled there.

## Third-review findings

### R13-01 · Critical · Targets: CONTRACT, ING, FLX
**Section:** Contract 6 (canonical example and its paragraph); ING "Canonical example" (ING-O-31); FLX "Regularized goals and singular points" (D-FLX-39)
**Problem:** The round 3 fix for R7-02 opened a new hole: the canonical check leaves out the region it most needs to judge. `clamp` is the base's `start_cap`, the whole bottom face at z = 0 (ANV's worked example puts the end cap at z = 4 mm). `away_from([clamp, …], 2 * thickness)` therefore removes everything below z = 8 mm, which takes in the rib root and its 2 mm fillet (z = 4 to 6 mm), where the rib's bending stress and the fillet concentration peak. FLX's own rule would exclude only the flagged *edges* (the clamp perimeter) by max(2ρ, t) = 4 mm, and that keeps the fillet, which lies about 5.7 mm from the perimeter edge. The load's direction is also never stated, so it is unclear what is being checked.
**Evidence:** Take a lateral 1.2 kN on the 20 mm rib (60 mm wide, 4 mm thick). The section modulus is 60·4²/6 = 160 mm³. The root moment of 1.2 kN × 20 mm gives 150 MPa nominal, about 210 MPa with a fillet Kt of about 1.4. In the band that remains (z = 8 to 16 mm) the stress is at most 1.2 kN × 16 mm / 160 mm³ = 120 MPa. The limit is 0.6 × 241 MPa = 145 MPa at the 6061-T6 specification yield that D-COV-13's default basis selects. So the check returns `Pass` on a bracket whose root fails, and ING-O-31 requires exactly this outcome ("its check decides at `SignOff`").
**Fix:** Write the check as `study.von_mises.max(over: p.regular())`. `regular()` is the Body minus each flagged set's default neighbourhood, taken from `flux::singular_sets` for this study, and never a whole face. State the load as a vector, for example `force: 1.2kN * dir(-x)`. Add a rule to D-FLX-39 and contract 7.1: when the maximizer of a regularized maximum lies on the boundary of an excluded neighbourhood, the result is `Undecided { reason: MaximumAtExclusion }` with the fix "model the support". Extend ING-O-31: the check region contains the rib-root fillet, and with a lateral load the canonical bracket `Fail`s at 4 mm and passes at 6 mm.

### R13-03 · Major · Targets: FLX, CONTRACT, ING
**Section:** FLX "Budgets and guarantees" (the algebraic and bounded-linear-goal rows; the paragraph that says guaranteed goal bounds rest on |J(u) − J(u_h)| ≤ ‖e‖·‖z − z_h‖); contract 5 `ErrorBudget`
**Problem:** For a goal check, the algebraic row's norm is "As discretization", which means the goal norm. But both listed estimators (Papež's multilevel bound and ‖r‖_{M⁻¹}/√σ) give energy-norm values, and contract 5 forbids combining norms. As written, every regularized-peak and eigenvalue budget is therefore `NotQuantified`, and ING turns that into a conditional `Pass` that no allowance will cover. Second, the product bound holds only under Galerkin orthogonality. With an iterative solve, J(u) − J(u_h) = a(u − u_h, z − z_h) + r(z_h), and r(z_h) ≠ 0, so the "Guaranteed" linear-goal bound is false without that term.
**Evidence:** The FLX table row reads "Algebraic | Multilevel bound … or a certified spectral bound after factorization; else equilibrated residual | As discretization | `Guaranteed`; else `Estimated`". The guarantee is stated as resting on "|J(u) − J(u_h)| ≤ ‖u − u_h‖_E · ‖z − z_h‖_E".
**Fix:** Define the goal-norm algebraic part as |r(z_h)| ≤ η_alg,E · ‖z_h‖_A (Cauchy–Schwarz on the discrete residual). It is `Guaranteed` when η_alg,E is, and the adjoint solve already gives ‖z_h‖_A. Restate the linear-goal bound as |J(u) − J(u_h) − r(z_h)| ≤ η_E(u_h)·η_E(z_h), and add r(z_h) to the algebraic part. Give the floating-point row the same goal-norm rule. Extend FLX-O-ERR-2 with deliberately loose solver tolerances.

### R13-06 · Major · Targets: COV, ING, FLX
**Section:** COV "Materials system", "Data model" (D-COV-13); FLX "Budgets and guarantees" (property reads)
**Problem:** D-COV-13 calls the basis enclosure a `Guaranteed` input part. A B-basis value is a statistical tolerance bound: 90% content at 95% confidence, so by construction about 10% of the population lies below it. Contract 5 reserves `Guaranteed` for proofs, and the union bound then misstates every check's confidence. The label is right only when the check's limit is defined by the basis value (a design value), not when the property drives the solve (modulus, conductivity, CTE).
**Evidence:** D-COV-13: "A property read returns `Approx<Q>` whose `input and tolerance` part is a `Guaranteed` basis enclosure". COV quotes 14 CFR 25.613: design values cover "99% of the population with 95% confidence … and 90% for redundant structure".
**Fix:** Split the two uses. (a) A limit written against a basis (`0.6 * yield_strength`) reads the basis value as an exact definitional number, with no budget part. (b) A property that enters a solve carries an input part of kind `Estimated` with α equal to the basis's non-content (0.10 for B, 0.01 for A), and the union bound includes it. Update FLX-O-ERR-11 and COV-O-MAT-6.

### R14-07 · Major · Targets: CONTRACT, ING, MEC
**Section:** Contract 5 `Tol<T>`, 6 (canonical example); ING Arithmetic on tolerances (symbol rule 2), D-ING-4
**Problem:** In the canonical example `thickness = 4mm ± 0.1mm` is forwarded into `extrude(thickness)` and into `rib(t: thickness)`. ING keys a forwarded symbol by (site, realizing Part), so the plate thickness and the web thickness, made by separate machining operations, share one noise symbol and are perfectly correlated: a stack containing their difference gets zero width. The same rule that makes "two parts made from one specification vary independently" is missing for two features of one Part. The example also passes `2 * thickness`, a `Tol`, to `away_from`, which realizes no geometry, and no tab says whether that site becomes PMI, is dropped, or fails (query filters reject a `Tol` with `ING4103`, but `away_from` is not a filter).
**Evidence:** Contract 6: `extrude(thickness)`, `rib(height: 20mm, t: thickness)`, `p.away_from([...], 2 * thickness)`. ING: "A tolerance forwarded into a Part is keyed by (site, realizing Part or Instance path), so two parts made from one specification vary independently."
**Fix:** Key a forwarded symbol by (site, realizing feature `CallSite`, Part or Instance path), in contract 5 and ING rule 2. Std features mark the parameters whose value they realize as an aspect (`#[realizes(OfSize)]` on `extrude`'s distance and `rib`'s `t`); a `Tol` passed to any other parameter fails with a new `ING4104 ToleranceNotRealized` whose fixes are `.nominal` or an explicit `part.tolerance(…)`. Change the canonical example to `2 * thickness.nominal`, and add to ING-O-7 that the canonical bracket has two independent thickness symbols.

### R14-08 · Major · Targets: ING, MEC, ANV
**Section:** ING `Tol<T>`, D-ING-4; MEC Interference and clearance, Model-based definition
**Problem:** Geometry is always built at nominal, and nothing builds it at another point of the tolerance zones. An H7 bore is modelled at its lower limit and a g6 pin above its upper limit, so the STEP file the GP1 shop programs from puts every fitted hole at the edge of its zone, and interference reports a press fit as touching. Creo, which engineers moving to Crucible know, regenerates a model at the upper, middle or lower bound of every dimension for exactly this purpose; Crucible has the information (every site's limits) but no way to use it for geometry.
**Evidence:** MEC: "Geometry is built at nominal, so a 10 H7/p6 press fit touches". ING: "`fit(10mm, H7)` ... the slot holds the nominal". Creo's Dimension Boundaries: "Middle: Sets the dimension value to the nominal value plus the mean of the upper and lower tolerance values" and "the system generates geometry based on new dimensions" (https://support.ptc.com/help/creo/creo_plus/usascii/model-based_definition/to_set_the_dimension_bounds_1.html).
**Fix:** Add an Evaluation parameter `realize: Nominal | Mid | Upper | Lower | Mmc | Lmc` (default `Nominal`), applied to every `Tol` site through ING's literal overrides, the mechanism `vary` already uses; `Mmc` and `Lmc` take the feature-of-size side from the site's `ShapeAspect` kind. PMI and `ItemDefinition`s always come from the nominal Evaluation. Exports take `realize:` (MFG's process hand-off chooses `Mid` for machining by default and states it in the export record), and `interference` and `min_clearance` accept it, so a press fit at `Mmc` reports its true overlap. Oracle ING-O-36: the bracket exported at `Mid` has every fitted diameter at its mid-limit and the same `EntityId`s as at `Nominal`.

### R14-09 · Major · Targets: MEC, ING
**Section:** MEC Stack-up and variation analysis (1D methods), Design checks (`check::fastening`); ING Arithmetic on tolerances
**Problem:** Phase 1 has GD&T on GP1 but no analysis that reads it: the 1D stack sums size `Tol`s and general tolerances only, and geometric zones, bonus tolerance from MMC and virtual conditions first enter in phase 2's 3D zone path. The everyday check on a bolted bracket, whether positional tolerances of clearance and tapped holes let the fasteners assemble (the fixed and floating fastener formulas, with a projected zone for tapped holes), sits in `check::fastening`, phase 2. A GP1 engineer therefore cannot verify in Crucible the assemblability that the GD&T on GP1's drawing exists to guarantee.
**Evidence:** MEC 1D table: "Worst case: Affine `Tol` sum over a closed, signed chain, general tolerances included", phase 1; "3D zone path" phase 2; `check::fastening` phase 2. The fixed fastener formula is T₁ + T₂ = H − F with H "MMC size of the through hole" and F "MMC size of the fastener thread" (https://www.gdandtbasics.com/?p=9816).
**Fix:** In phase 1, let a 1D chain take a `GeometricTolerance` contributor: a position or profile zone of width t contributes ±t/2 along the chain direction, and an MMC or LMC modifier adds the bonus as an affine term in the feature's own size symbol (bonus = |size − MMC size|, linear in that symbol, so ING's affine forms keep its correlation with the size contributor exactly). Move `check::fastening`'s fixed and floating fastener checks, with projected zones, to phase 1, and add MEC-O-TL-9: GP1's bolt pattern gives the hand-computed T₁ + T₂ = H − F margin.

### R14-18 · Major · Targets: MEC, ING
**Section:** MEC Specification model (`GeometricTolerance`), Two dialects, one model
**Problem:** The record's `modifiers` field ends in "…", so agents cannot build validators, renderers, the AP242 mapping or QIF output against it. ISO GPS form, orientation and location specifications also carry elements the record has no field for: the association criterion for the toleranced feature, filter specifications, and the parameter evaluated (peak to valley and others) [unverified: the exact ISO 1101:2017 symbols]. These matter at the CMM, where ISO 8015's independency makes the specification operator decide the measured value.
**Evidence:** MEC: `modifiers: [Modifier], // material condition, projected, free state, dynamic profile, statistical, …`; `Zone // width, shape, disposition`; QIF 3.0 output through MFG (capability row "PMI import, QIF and data-set completeness").
**Fix:** Replace "…" with a closed `Modifier` enum per dialect, listed in a table with the clause that defines each and its AP242 and QIF mapping. Add `association: Option<Association>`, `filter: Option<FilterSpec>` and `parameter: Option<Parameter>` to the ISO dialect's form, orientation, location and profile records, defaulting to the dialect's default specification operator, and make MEC-O-TL-1 check that every enum value round-trips through AP242 and QIF.

### R14-22 · Minor · Targets: ANV, ING
**Section:** ANV Query resolution (stage 3, `Note::NearTie`)
**Problem:** "A winner whose certified margin is under 5% of the ranked measure" is not translation-invariant for position ranks: for `first(along: +x)` the measure is a coordinate, so a part 1 m from the origin gets a 50 mm near-tie band and the same part at the origin almost none.
**Evidence:** ANV: "A winner whose certified margin is under 5% of the ranked measure carries `Note::NearTie`"; ING lists `first(along: d)` and `nearest: p` as rank selectors.
**Fix:** Define the margin relative to the spread of the candidates: "under 5% of (largest − smallest measure among the candidates), or under 2¹⁰ρ for position measures with two candidates". Add a translated copy to ANV-O-NAME-2.

### R14-25 · Minor · Targets: ANV, ING
**Section:** ANV Booleans, splits and patterns; ING Kiln-held values
**Problem:** ANV says "Kiln lowers a whole CSG tree to one arrangement", but Kiln never rewrites Op graphs, and ING lowers only "a chain such as `a + b + c`" by a syntactic rule. A tree whose intermediate results are bound (`let ab = a + b`) and reused cannot fuse without changing `CallSite`s, keys and `EntityId`s.
**Evidence:** ANV: "Kiln lowers a whole CSG tree to one arrangement, so rounding happens once per tree". ING: "A chain such as `a + b + c` lowers to one n-ary `anvil::boolean` by a fixed rule".
**Fix:** ANV: "Ingot lowers each Boolean expression without intermediate bindings to one n-ary operation (ING), so rounding happens once per expression."

### R14-28 · Minor · Targets: CONTRACT, ING, MEC
**Section:** Contract 5 `ShapeAspect`; ING GD&T controls as types; MEC Shared types
**Problem:** The aspect kinds differ in every place they are listed: the contract names `OfSize`, `Hole`, `Pattern`; ING uses `OfSize`, `Planar`, `Any`; MEC says "a feature of size, face set, pattern or recognized aspect". The type parameter of `Query<ShapeAspect<K>>` drives ING's compile errors, so one closed list is needed.
**Evidence:** Contract 5: "kinds such as `OfSize`, `Hole`, `Pattern`"; ING: "`hole(…)` gives `ShapeAspect<OfSize>`, extrude caps `ShapeAspect<Planar>`, recognized imports `ShapeAspect<Any>`".
**Fix:** MEC owns one enum, by Clément's invariance classes plus size: `Planar`, `Cylindrical`, `Spherical`, `Helical`, `Prismatic`, `Revolute`, `Complex`, each with an `OfSize` marker trait where a size applies, plus `Pattern<K>` and `Any`. The contract cites MEC instead of listing kinds.

### R14-32 · Minor · Targets: MEC, ING
**Section:** MEC Determinism and seeds (D-MEC-33)
**Problem:** The seed quantum "the larger of 2¹⁰ρ for the sketch and 10⁻⁶ of its diagonal" has a redundant term: 2¹⁰ρ lies between 0.95 × 10⁻⁶ D and 1.9 × 10⁻⁶ D, so the second term binds only when D is within 5% below a power of two.
**Evidence:** ANV: ρ(D) = 2^(⌈log₂ D⌉ − 30), so 2¹⁰ρ = 2^(⌈log₂ D⌉ − 20).
**Fix:** q = 2¹⁰ρ of the sketch, in ING and MEC.

### R14-33 · Minor · Targets: CONTRACT, ANV, ING, MEC
**Section:** Contract 5 `Query`; ANV Query resolution; ING The query language
**Problem:** Three Boolean parameters, `on_merge: Accept`, `on_partial: Accept` and `on_fragile: Accept`, express one idea: which degradations an extent use accepts. Three names, three dialog fields and three agent tool parameters for one set.
**Evidence:** Contract 5: "unless the call writes `on_merge: Accept`, `on_partial: Accept` or `on_fragile: Accept`".
**Fix:** One parameter `accept: [Merged, Partial, Fragile]`, default `[]`, in the contract, ANV, ING and MEC.

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

### R15-04 · Major · Targets: KLN, CONTRACT, UIX, ING
**Section:** Contract 7.1 `repo` (Loro, reconnection); KLN "Live documents", "Offline work and sync", D-KLN-22, D-KLN-24
**Problem:** Concurrent edits to one Ingot text merge by two different algorithms: Loro's CRDT (Fugue leaves, Kleppmann's tree move) for live sessions, and the three-way block merge with GumTree and Mergiraf-style triples for branches. A reconcile step patches the gap, and the 60 s rule routes a divergence to one or the other, so the same pair of edits merges differently depending on timing. Crucible already has a central relay that checks every update, and offline work beyond 60 s already becomes a branch, so the CRDT handles only short divergences that a sequencer handles more simply. Loro adds a document per (package, module label), block-id mapping and its own oracles.
**Evidence:** KLN: "The relay checks every update against the sender's permissions and enforced locks"; D-KLN-24: offline work "rejoins as a branch when the disconnection exceeded 60 s". Figma's multiplayer post: "Figma isn't using true CRDTs though", because "the server is the ultimate authority" and "can define the order of events" (https://www.figma.com/blog/how-figmas-multiplayer-technology-works/). Replicache: "In Replicache, the server is authoritative", and the client "rewinds … applies the server's patch, and then replays pending mutations" (https://doc.replicache.dev/concepts/how-it-works).
**Fix:** Replace Loro with a server-sequenced edit log per branch: clients apply `SourcePatch`es optimistically, the relay orders them, and clients rebase pending patches with the same `MergeDriver` block merge that branches use, so live and branch merges share one semantics and one oracle. Literal edits stay last-writer-wins by sequence order. Delete D-KLN-22's CRDT, the block-id mapping and the reconcile step; keep per-module replication for labels as per-module sequencing. If the founder keeps Loro, state why a central relay is not enough, and make the reconcile step call the same `MergeDriver` so outcomes cannot depend on timing.

### R15-07 · Major · Targets: CONTRACT, KLN, ING
**Section:** Contract 7.1 `repo` (module as the unit of a source label); KLN "Labels and export control", "Supplier packages and derived views", D-KLN-31; ING "Packages and versions"
**Problem:** An uncleared principal "compiles against the signature and evaluates the module remotely on cleared workers", but every value derived from that module carries the module's label, so the principal can read none of the results unless something declassifies them. The mechanism that does that, a declassified derived view evaluated on the owner's workers, already exists for suppliers (envelope, frozen geometry, remote parametric model). Two mechanisms do one job, and the module path leaves the reader guessing what the uncleared engineer actually sees.
**Evidence:** Contract 7.1: "whose public signature may carry a lower label through a declassification record, so uncleared principals compile against the signature and evaluate the module remotely". KLN-O-LABEL-1: "an uncleared clone evaluates around an ITAR module it cannot read". KLN D-KLN-31: "Parametric sharing without source uses remote evaluation on the owner's workers".
**Fix:** One mechanism: a labelled module exposes declassified derived views (signature, envelope, interfaces, mass properties), each with its own declassification record, evaluated remotely on cleared workers. Internal uncleared staff and suppliers use the same derived-view records; only the recipient type differs. State in contract 7.1 that any node that joins an undeclassified output is unreadable to the uncleared principal, and rewrite KLN-O-LABEL-1 to check that the uncleared clone sees the declared views and nothing else.

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

### R15-17 · Major · Targets: CONTRACT, KLN, ING, ANV, FLX
**Section:** Contract 2 (Op, Node), 7.2; KLN "Keys"
**Problem:** `OpKey` keys more than Op nodes. Contract 7.2 item 1 covers "for Ingot code the code hashes of the modules actually used", so feature nodes key by the `OpKey` formula, and every node with `EntityId`s adds its `CallSite`. Meanwhile the glossary needs an exception to explain the name ("Rust types with the `Op` prefix name operations … except `OpKey`, which keys an Op node"). The name tells a reader the wrong scope, and the exception exists only to excuse it.
**Evidence:** Contract 2, Op: "Rust types with the `Op` prefix name operations (`OpImpl`, `OpCx`), except `OpKey`, which keys an Op node." Contract 7.2 item 1 as quoted; KLN node table.
**Fix:** Rename `OpKey` to `NodeKey` and define it once in 7.2 for every node kind, with per-kind items (operation identity and version, code hashes, `CallSite`, fidelity, host digest). The `Op` prefix then means "operation" without exception, and the glossary entry for Op shrinks to "a node that calls one operation, Wasm component or External Op". Do it before `base` freezes.

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

### R15-30 · Minor · Targets: CONTRACT, ING, KLN, AGT, UIX
**Section:** Contract 5 (`CallSite`, `ResultStatus`)
**Problem:** `LiteralSite` crosses five tabs and enters node keys, but the contract never defines it. `ResultStatus::Proxy` appears in contract 5 and the 13.3 drag row with no definition.
**Evidence:** ING: "literal overrides keyed by `LiteralSite` (statement identity, call identity, argument slot)"; KLN rule 5 under Keys; AGT and UIX interface rows. Contract 5: "`Pending`, `Proxy`, `Ready(Fidelity)`, …".
**Fix:** Contract 5 adds "`LiteralSite` [ING]: a `CallSite` plus an argument slot; overrides key by it and follow `#[was]`" and "`Proxy`: a dependent shown by affine extrapolation from its last value while it recomputes, never cached".

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

### R17-01 · Critical · Targets: AGT, KLN, ING, PLT, CONTRACT
**Section:** AGT "Platform notes" and "Sessions, identity and delegation"; KLN "Storage, Git export and span provenance"; ING "Language service and tools"; contract 7.6 "Plans and local exports"
**Problem:** Every agent control keys on the principal, but on a desktop the human principal's credential sits in the OS keychain where any process the user runs can use it. An external host with a shell tool (the normal coding-agent setup) can run `crucible` subcommands, which map one-to-one onto API methods, as the human: merge R0 to R2 Proposals, endorse free text, export `internal` payloads as "audited local writes" and then send them out with its own network tool, and edit protected branches, all with no context label, no risk class and no delegation chain. The same agent editing `.ingot` buffers through the first-party VS Code or Zed extension produces spans recorded as "trusted when a person typed it", since LSP `didChange` cannot tell keystrokes from an AI extension's writes; a device key then vouches for those spans across archive import.
**Evidence:** AGT: "`crucible mcp` runs on stdio with the keychain credential [S6]". AGT D-AGT-1: "UI commands and CLI subcommands map one-to-one onto API methods." KLN: span integrity is "trusted when a person typed it or the compiler produced it", and imported spans keep integrity when "a device key of this organization signed the Change". ING D-ING-25 ships the language service "over stdio with first-party VS Code and Zed extensions". Nothing in AGT, KLN or PLT separates a human at the CLI from a process acting for one.
**Fix:** Add to contract 7.6: "A local credential without a fresh user-presence proof authenticates as the principal `agent:<org>/local/<device>` with `Declared` assurance, never as the human. Human-only methods (`propose.merge`, `propose.endorse_text`, `propose.policy`, `propose.declassify`, `propose.waive`, recipient and clearance changes, and every local write of a payload above `public`) need a WebAuthn user-verification assertion on the approval origin bound to the call's argument digest, valid for one call." In KLN, record spans arriving through LSP, file import or any channel other than the in-app editor's keystroke path as `data_untrusted` unless the user confirms the batch on the approval origin, and replace "a device key of this organization signed the Change" with "the server that witnessed the write signed its span-integrity record". AGT-O-8 gains a case: a host with a shell tool runs the CLI and an editor extension, and neither merge, endorsement, local export nor trusted spans result.

### R18-09 · Major · Targets: ING, FLX, KLN, ANV, UIX, CONTRACT
**Section:** Contract 5 `Quantity<D>`, `Field<D, V>`; ING "Types and dimensions"; FLX "Rust API"; UIX "From gesture to Ingot edit"
**Problem:** The contract names Rust types canonical, but no tab says how Ingot's types exist in Rust. Stable Rust cannot compute `Quantity<D1·D2>` from const generics (`generic_const_exprs` is unstable), and the strong angular system with rational powers rules out simple marker types. Ingot also creates domains and value types at run time (user enums, tuple domains), so `Field<D: Domain, V: Value>` with `PhantomData` cannot be the representation Kiln stores or `crucible:ops` passes. Tabs already improvise: ANV uses `Length` and `Angle`, UIX `Quantity<Dyn>`, and FLX a generic `Field<D, V>`.
**Evidence:** ING: "`Quantity<D>` | A `Real` in coherent SI units with dimension `D`; checked at compile time, erased at run time" (true of Ingot, silent on Rust). UIX: `SetMeasure { target: Query, measure: Measure, to: Quantity<Dyn> }`. FLX: `pub struct Field<D: Domain, V: Value> { header, repr, _kind: PhantomData<(D, V)> }`.
**Fix:** ING and FLX state one rule in their Rust surfaces. The erased forms are canonical: `Value` (an enum over scalars, `DynQuantity { si: f64, dim: Dim }` with `Dim` a vector of rational exponents over the eight base dimensions plus a kind id, records, lists, handles) and `DynField { domain: DomainDesc, value: ValueDesc, header, repr }`. These are what Kiln memoizes, the CAS encodes and `crucible:ops` carries. Typed views are generated, not hand-written: `base` generates newtypes (`Length`, `Stress`, `Torque`) and the `Mul`/`Div` impls the prelude kind table lists, from that table, plus `Field<D, V>` as a checked view over `DynField` (`TryFrom<DynField>`). Rust code never uses `uom` or `typenum`.

### R18-28 · Minor · Targets: ING
**Section:** ING "Rust features and Wasm components" (the `involute_profile` example)
**Problem:** The example likely fails the borrow checker. If `planar_builder` borrows `cx` mutably, as builders of an `&mut Cx` usually do, `cx.site_keyed(…)` inside the loop conflicts with the live builder `s`. Agents copy canonical examples, so an example that does not compile spreads.
**Evidence:** `let mut s = cx.planar_builder(Plane::XY, cx.site("profile"));` followed by `s.add_spline(cx.site_keyed("flank", i), …)?` while `s` is alive.
**Fix:** Make site keys methods of the builder (`s.site_keyed("flank", i)`) or have `planar_builder` return an owned builder holding a cloned handle. ING-O-17 compiles every Rust block in ING with `rustc` against the generated `ingot_sdk`.

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

### R21-19 · Major · Targets: ING
**Section:** "Lexical syntax and grammar"; "The language at a glance"
**Problem:** ING's second section is the full lexical specification and a 70-line EBNF grammar, so a reader meets NFC normalization, UAX #31 identifiers and statement-termination rules before tolerances, approximate values, queries or checks, the ideas that make Ingot worth learning. "The language at a glance" reprints the canonical example verbatim (its third copy in the spec) with a three-sentence gloss, instead of walking through it.
**Evidence:** Section order: "Scope and principles", "Lexical syntax and grammar" (encoding, keywords, literals, EBNF), "Types and dimensions", then "Tolerances, approximations and truth" at line 381. The tab's most readable passages (the `pin_joint` stack with worked numbers, the `drive_unit` catalog example, the `static_margin` outcome table) all sit after line 440.
**Fix:** Expand "The language at a glance" into an annotated walkthrough of the bracket: a table of eight rows, "Line · What Ingot does · Where specified" (units on parameters and `ING3001`; `Tol<Length>` forwarded as PMI; `end(outline.top)` as a role query; `body.edges(new)`; `part(…).material(…)`; `static_stress` returning Fields; `away_from` and the regularized peak; `require` as a three-valued check). Then order the sections as Types, Tolerances, Geometry, Evaluation, Diagnostics and checks, Execution, Rust features, Packages, Feature metadata, Tooling, and finally "Lexical syntax and grammar" as the Reference section. Keep the literal and unit tables near the start of Types, because units are the first thing a user types.

### R21-22 · Minor · Targets: CONTRACT, ING, MEC, AGT
**Section:** Contract sections 9 and 11, "Platform notes"
**Problem:** Every tab must have a "Platform notes" section, so tabs with no platform-specific behaviour fill it with restatements, which a reader skims and learns to ignore.
**Evidence:** ING: "Accessibility | Diagnostics are plain text with spans"; "Air-gapped installs | Compiler and interpreter ship in every build; no network is needed"; "Every target | One canonical-class interpreter, so a divergence is a platform defect".
**Fix:** In contract 9 and 11, allow "Platform notes: none beyond PLT's rules" as a complete section, and require a row only for behaviour that differs by target (capacity, a missing capability in a tier, a browser limit).

### R21-24 · Minor · Targets: ING, AGT, FLX, MEC, ANV, KLN
**Section:** "Oracles"
**Problem:** Oracle ids follow different schemes: flat numbers (ING-O-1 to ING-O-38, AGT-O-1 to AGT-O-24) and area-prefixed ids (MEC-O-PF-1, ANV-O-VER-1, KLN-O-FPRINT-1, FLX-O-OPT-1). A flat id says nothing about what it verifies, so a capability row citing "ING-O-8" or "AGT-O-17" sends the reader to the Oracles table every time.
**Evidence:** ING capability rows cite "ING-O-1, ING-O-13, ING-O-27"; MEC rows cite "MEC-O-TL-6", whose area (tolerancing) is readable in place.
**Fix:** Adopt `<TAB>-O-<AREA>-<n>` in ING and AGT now, while `oracles/` holds no executable oracles and renaming costs one search-and-replace across tabs.

### R21-26 · Minor · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, CONTRACT
**Section:** Capability tables at the end of each design section
**Problem:** Capability tables are the build contract, but in reading order they arrive as a dense block after every section, and many cells add nothing: "Failure: —" and "Not expressible" stand where the reader expects a typed failure. The published doc gives them the same weight as explanation.
**Evidence:** ING "Purity | … | Not expressible"; MEC "Typed failures and fixes | `FeatureError { kind, why, fix, at }` | —"; AGT "Priority classes | … | — ".
**Fix:** Replace "—" with "None: cannot fail" or the actual failure, and "Not expressible" with "None: the language cannot express a violation". In the published doc, render capability tables as a visually distinct, collapsible "Build contract" block under each section, so a reader can follow the prose without the tables breaking it.

### R21-30 · Minor · Targets: OVERVIEW, ING, CONTRACT
**Section:** Overview "Principles", "The canonical example", "Platforms", "Roadmap"; ING "The language at a glance"
**Problem:** The Overview copies large parts of the contract nearly word for word instead of summarizing and linking: the seven principles, the canonical example with its explanatory paragraph, the platform tiers and the roadmap table. ING reprints the example a third time. Three copies must be kept identical, and a reader who has read the contract meets the same text again.
**Evidence:** The paragraph beginning "The edge is selected by its role, `end(e)`" is identical in contract section 6 and the Overview, apart from "section 7.1" becoming "contract 7.1"; the principles differ only by trimmed clauses; the Overview's roadmap table repeats contract 13.1's gate texts.
**Fix:** In the Overview, give the principles as seven one-line statements linking to contract 3; show the bracket once, annotated (the walkthrough of R21-19 can live here, with ING linking to it); keep the roadmap as phase, theme and golden products only, linking to contract 13.1 for the gate texts. ING links to the Overview's annotated example instead of reprinting the source.

### R21-33 · Minor · Targets: ING
**Section:** "Fidelity, drags, holes and derivatives"
**Problem:** One subsection joins four unrelated topics in four short paragraphs: fidelity being invisible to code, drag specialization, typed holes and derivatives for edit plans. The title is a list, which signals that the section has no single idea.
**Evidence:** The subsection's paragraphs open "Ingot code cannot observe fidelity", "When a drag starts on a literal", "Derivatives serve UIX's edit plans" and "In phase 1, edit plans rank by provenance first".
**Fix:** Move the fidelity paragraph into "`Approx<T>` and the decision rule", where fidelity already matters; move drag specialization into "The Ingot IR and Kiln" beside overrides; move typed holes into "Language service and tools"; keep "Derivatives and edit plans" as its own subsection.

## Claims the reviewers verified

Drop the `[unverified]` marker on these and cite the URL in Sources.

None in this review.

## Unverified claims in your tab

Verify each with WebFetch on a primary source and drop the marker, correct it, or cut the claim if nothing supports it. Line numbers are at tag `round-3`.

None.

## Your open questions

Close each: decide it (the reviewers propose answers above), move it to a contract change request, or keep it with the reason it cannot be decided yet.

This revision decides all nine round 2 questions:

| Question | Decided by |
| --- | --- |
| Kind granularity; frequency into phase | The RFC rule; `ING-L-HertzPhase` |
| Geometry-driven Instances | Instance sets (D-ING-22) |
| Affine arithmetic at scale | Condensation above 4,096 symbols |
| ELX data modules | No sidecar (D-ING-27) |
| `Decimal` resolution | 10⁻⁹, round half to even, `round_minor` |
| Feature granularity | `ING-L-FeatureKind` |
| Jacobian types | Entry-level `Mat` diagnostics |
| Literal sites under live edits | Overrides follow `#[was]` |

Findings declined or applied in part:

- R2-06: calls get no CRDT identity, because contract section 5 derives call identity from name and occurrence; R9-36's lint closes the gap.
- R3-33: one instance per worker with state machines applies to the code generator; the interpreter isolates calls with heap frames.
- R6-33: ING sets only its own ratios; Wasm component and user-form ratios belong to PLT, ECO and FLX.
- R3-47: Ingot runs on the interpreter on iPadOS, so the Pulley fallback concerns Wasm components only.
- R2-18: ING adds the dialect modules; the extended GD&T record is MEC's.
- R7-02: contract section 17 declines the near-maximal-set rule, because estimates are least reliable next to a singular set.
- R8-08 and R9-17: merged into one name-free key, led by R8-08's sensitivity order so Sobol's first dimensions go to the largest contributors.
- R8-20 and R9-16: merged into `instances(of:, at:, min:)`.
- R8-51 and R9-49: their condensation rules conflict; ING keeps R8-51's mechanism with R9-49's 4,096-symbol threshold, bounding memory.
- R9-18: applied in another form. Releases emit bit-identical IIR, so no second key is needed and code hashes never depend on which release ran first.

## Known items

- Read `docs/revision/digest.md`: adopt the permissive libraries that serve your tab, name copyleft tools only as oracles, and use the clean-room insight protocol of contract 7.7 for incumbent behaviour.
- Add one sentence under each drawn diagram that tells the reader how to read it (`diagrams/01-ingot-pipeline.jsx`).
