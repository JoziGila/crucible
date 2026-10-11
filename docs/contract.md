# Crucible architecture contract (v6.1)

Binding for every design agent and reviewer. Version 4 integrates the rulings on the first round's contract change requests (section 14) and on the adversarial review (section 15); versions 4.1 and 4.2 rule on the change requests of the first revised tabs and add the shared phase table (13.4); version 5 rules on the change requests of the other ten revised tabs (section 16); version 6 rules on the second adversarial review's findings against the contract and on two pending requests, and 6.1 on the round 3 tabs' change requests (section 17). Where a draft disagrees with this contract, the contract wins. If you believe a ruling is wrong, do not work around it: say so under "Contract change requests" with your reason.

## 1. Mission

Crucible is one Rust platform where people and agents design, simulate, manufacture and release physical products from a single typed model. Every subsystem must be specified completely enough that agent swarms working against oracles, directed by one founder, can build it without further design work. "Fully specified" means every capability has a purpose, a contract (inputs, outputs, types), failure behavior, an oracle that verifies it, and a phase.

Four hard requirements from the founder:

1. **Anything physical.** Every major physics domain and every scale from MEMS to ships and building products. Honesty rule: no software validly simulates literally everything, so every model states its validity envelope, the spec says plainly what is out of reach, and it defines how new physics and domains are added.
2. **State-of-the-art, optimized methods** for every component and every simulation (section 8).
3. **Every major operating system, identical features** (section 9).
4. **Supreme coherence and taste** across the whole design (section 10).

## 2. Canonical names and glossary

| Name | What it is |
| --- | --- |
| Crucible | The platform (working name; full trademark clearance in classes 9 and 42 is a phase 0 gate, assuming Atlassian's mark persists) |
| Ingot | The design language; source files end in `.ingot`; package manifest `ingot.toml`, lockfile `ingot.lock` |
| Anvil | The geometry kernel |
| Flux | The physics and simulation engine (working name; collides with Siemens Simcenter Flux and flux.ai, so it is renamed in phase 0 before any operation name or WIT package freezes) |
| Kiln | The incremental evaluation engine |
| CAS | The content-addressed store for all derived artifacts |
| `repo` | The repository crate: Changes, branches, merges, releases, change orders, BOM |
| `api` | The single API used by the UI, agents, CLI and CI, exposed over MCP and native SDKs |
| std | The standard library of Ingot packages |
| Golden products | Reference products whose passing checks close each phase |

No other codenames. One name per concept, one concept per name:

| Term | Definition | Never call it |
| --- | --- | --- |
| **Operation** | A versioned primitive implemented in native Rust inside Anvil or Flux (`anvil::blend@2`, `flux::solve_linear@1`). Pure; deterministic per its determinism grade. | "op" in prose, "kernel", "function" |
| **Feature** | An Ingot function that captures design intent by orchestrating operations; the unit people see in a design's history. | "macro", "script" |
| **Wasm component** | A sandboxed, native-speed extension with a WIT interface, determinized before it runs (section 7.4). | bare "component", "plugin" |
| **Node** | One memoized computation in Kiln's graph: a front-end stage, a feature call, an Op, a check, a query resolution or a derived view such as a BOM. | "job", "task" |
| **Op** | A node that calls one operation or one Wasm component; its cache key is an `OpKey`. Rust types with the `Op` prefix name operations (`OpImpl`, `OpCx`), except `OpKey`, which keys an Op node. | |
| **External Op** | An Op whose implementation runs outside the sandbox in an isolated host (a pinned container image for a copyleft solver, an FMU or IBIS-AMI host, a firmware emulator). Runs only on untrusted-evaluation workers (section 7.8). Cached by input hashes plus the host image digest; its results carry the host's platform class or `Unverified`. | "external tool run", "out-of-process result" |
| **External input** | Signed, content-addressed data produced outside evaluation (a licensed translation, a supplier offer, a catalog or regulation dataset, a machine reading). Pinned in `ingot.lock` and read by Kiln as a leaf input; changes only through an explicit update. | "snapshot", "data package" for this meaning |
| **Evidence record** | A signed measurement from a physical test (a hardware rig, a CMM, a test lab), addressed by the check it serves and the identities of the inputs it tested (`GeometryId`s for geometric inputs, `ObjectId`s otherwise). An Evaluation reads the newest record valid at its measurement time (the instrument's calibration covered the measurement date), up to the Evaluation's evidence watermark, and stores its `ObjectId` in the `CheckOutcome`. The watermark is a transaction-log position recorded in the Evaluation and CI reports; protected branches advance it by an audited ref transaction, so one Change at one watermark fixes every outcome. Releases and approvals pin the evidence ids they cite. | "measurement cell", "hardware result" |
| **Asset** | A non-source file stored in a design repository (a STEP file, a scan, a PDF datasheet), content-addressed and referenced from Ingot. | |
| **Evaluation** | One request to Kiln to compute a set of nodes for a Change, with a lifecycle (queued, running, done, aborted), streamed results and a report. | "job", "run", "build request" |
| **Check** | A predicate declared with `require`, evaluated as its own node and identified by its `CheckId`; its result is a `CheckOutcome` (section 5). | "assertion", "rule result" |
| **Waiver** | A signature record by an authorized human naming a `CheckId`, the Items and effectivity it covers, a reason and an expiry (a revision, a serial range or a date checked when the gate applies), attached to a Proposal or change order. `#[waive]` in source only requests one, and counts nowhere until a matching record exists. Agents never sign one; protected checks and `Refuse` envelopes accept none. | |
| **Package** | A versioned unit in the package registry holding Ingot source, Wasm components, data (standards tables, catalog-part definitions, templates, tutorials, themes) or any combination. | |
| **Catalog part** | A purchasable item (bearing, motor, chip, fastener). Its definition is a Package under `parts::<manufacturer>::…`; its offers (price, stock, lead time) are External inputs. | "component" |
| **Body** | Geometry in any representation. | "Shape", "Solid" as a type |
| **Part** | A Body with identity (item number, name, material, properties) that appears in a BOM. | |
| **Assembly** | A tree of Instances with placements and mates. | |
| **Instance** | One occurrence of a Part or Assembly inside an Assembly. An Instance set is one BOM line whose members are keyed by anchors (such as hole `EntityId`s) and counted by evaluation (section 6). | "occurrence", "component" |
| **Software item** | A versioned binary with identity (firmware, bitstream, application) that appears in a BOM and is bound to a programmable Instance. | |
| **Item** | The lifecycle identity of a releasable thing (Part, Assembly, document, Software item, catalog part, manufacturing program) with an item number. Its revisions are the only meaning of "revision". | |
| **Field** | A physical quantity distributed over a domain (section 5). | "result", "map", "curve", "waveform" as types |
| **Network** | A lumped model: elements connected through domain-typed ports (electrical, magnetic, thermal, rotational, translational, fluid, signal), compiled by Flux into a DAE. Results are Fields over time or frequency on its ports. | "Circuit" as the type name |
| **Material** | A versioned record of properties and constitutive models. | |
| **Proposal** | A branch plus rationale plus CI report; the unit of agent work and of human review. | "PR", "merge request" |
| **Approval** | A human principal's signature over the `ObjectId` of an approval subject (section 5). Any change to the subject voids it; changes outside the subject (a rebase, a CI re-run, a refactor) do not. | "sign-off" as a noun for this |
| **Act** | An API method with an effect outside Crucible: release, yank, export, order, request a quote, send to a supplier, transfer a program or job to a device, flash a board, start a print, run a rig test, publish a package or passport. Always two-phase: `act.prepare` produces a plan with a digest; `act.commit` runs only after an assigned human Approval of that digest (section 7.6). Physical-effect Acts are the transfer Acts `send_to_machine`, `send_robot_program`, `store_machine_job` (OPC UA `Store` only), `send_print_job` and `flash_device`, and the restricted `start_print` and `run_rig_test`; Crucible never starts a device it transfers to, except through the restricted `start_print` (section 7.6). One plan may carry several effects under one Approval. A human's export of an uncontrolled `public` or `internal` payload to a local folder or application is an audited local write, not an Act (section 7.6). | "action" for this meaning |
| **API method** | An entry in the `api` catalog, named `<group>.<name>`. | "operation" |
| **Change** | One immutable fine-grained edit, like an Onshape microversion. "Revision" is reserved for PLM item revisions. | "commit" (except when comparing with Git) |
| **Design repository** | The repository holding one product's Ingot source, Assets, `ingot.lock` and history. | |
| **Snapshot** | A rendered image of a `ViewState` under a `RenderProfile`, with structured marks and the renderer identity, attached to Proposals and reviews. Its pixels belong to the `Unverified` platform class: never canonical and never used for data. | |
| **Fidelity** | The accuracy a result is demanded at: `Preview` (fastest, approximate, never written to the shared cache), `Interactive` (approximate with an error estimate), `SignOff` (converged or exact). | "coarse", "exact" as fidelity names; "sign-off mode" |
| **Model level** | The form of a physics model, from L0 (analytic) to L3 (full 3D), declared per model (COV). | "fidelity", "fidelity level" |
| **Evidence level** | The credibility of a physics model, from E0 to E4 (COV). Distinct from an Evidence record. | |
| **Platform class** | The set of execution environments whose results are bit-identical (section 7.3). | |
| **Determinism grade** | What an operation version guarantees: `Portable`, `ClassExact` or `Certified` (section 7.3). | "execution mode" |
| **Labels** | The label lattice attached to every artifact, API response and model context (section 5). | "taint flags", "classification tags" as separate concepts |
| **Abort** | An environmental end to a computation (cancellation, resource exhaustion, device loss, budget exhaustion, worker loss, demand-depth or Evaluation fuel limit). Not a `Failure`: never catchable, never cached (section 7.2). | "error" for this meaning |
| **Service BOM** | The BOM view for service and spare parts. The abbreviation SBOM is never used; "software bill of materials" is always spelled out. | "SBOM" |

## 3. Principles (non-negotiable)

1. **No privileged code.** Built-in features use only the public mechanisms anyone can use: Ingot for features, Wasm components for heavy algorithms, and versioned Anvil and Flux operations underneath. If a user or agent cannot build a feature, neither can the core team. The one permitted difference is process isolation of third-party Wasm components, bounded by PLT's call-overhead targets (section 7.4).
2. **One model, three editors.** The visual editor, the code editor and agents edit the same typed program. Nothing exists only in the GUI.
3. **Two universal types.** `Body` carries geometry and `Field` carries physics data. Models (weak forms, Networks) describe how Fields are computed; libraries consume and produce Bodies, Fields and plain values.
4. **Determinism is a feature.** Same inputs and versions give identical outputs per platform class; cross-class results agree within declared tolerance, or, for chaotic problems, in declared statistics. Problems with bifurcations or multiple solutions declare branch selection explicitly (an imperfection or symmetry-breaking input) or declare agreement on branch-invariant quantities. Evaluation never depends on clocks, randomness, thread order or names (section 7.3).
5. **The compiler checks physics.** Units, dimensions and tolerances are types, checked before anything runs. Every approximation carries its error, in a stated norm.
6. **Every claim has an oracle.** No capability ships without a machine-checkable test that the agents building it cannot edit. Every oracle that judges agent-built code also has a held-out split outside the agent-readable tree, chosen by a fixed hash rule, or a property generator seeded at CI time; a pass on visible inputs with a failure on held-out inputs fails the oracle.
7. **Open core, interop first.** Kernel, language and standard library are open source. Open standards are first-class; no design is ever trapped.

## 4. Layering: operations, Wasm components, features (D-ARCH-1)

- **Operations, in native Rust.** Geometry and physics algorithms live in Anvil and Flux crates behind stable, versioned contracts; a few hundred primitives. A released operation version freezes its source closure: its own modules plus the versioned modules of every result-affecting first-party crate it calls (`linalg`, the `kernels` back ends, the horizontal operations of `simd`), recorded as a closure hash in the operation registry. A change to a frozen module creates a new module version that only new operation versions use, and Kiln's registration refuses a released version whose closure hash changed; toolchain and `detmath` upgrades pass golden-hash checks instead (ANV, PLT). A design pins the versions it was built with. Retired versions stay executable from archived Wasm builds of their frozen source; only versions that cannot compile to Wasm (GPU `ClassExact` paths) fall back to an `OpVersionRetired` failure whose fix is an upgrade Proposal.
- **Wasm components, for heavy custom algorithms.** Nesting, CAM strategies, slicers, placers and routers, importers, specialist solvers. Sandboxed, determinized, portable to every OS and the browser, published in the registry. Evaluation-world Wasm components may import the WIT package `crucible:ops`, whose generated interfaces `crucible:ops/anvil` and `crucible:ops/flux` expose versioned operations, including GPU-backed ones; each call is a recorded Op dependency. They never get raw GPU, clock, file or network access, and they reach engine data only through `crucible:ops` and handles derived from their inputs, never through a raw `ObjectId`; every read is a recorded dependency whose label joins the node's.
- **Features, in Ingot.** Design intent, orchestration, entity selection and naming, checks and UI metadata.
- **Tier rule (D-ECO-6).** Use Ingot unless code needs more than about 10⁶ primitive steps per call, an existing codebase in another language, or a data structure Ingot cannot express efficiently; then a Wasm component. Promote to an operation when at least three independent packages need it, it needs GPU or SIMD kernels, or it must be differentiable through Flux's form-level derivatives. Promotion happens in public, with oracles.
- **Fallback.** Features may be authored in Rust as Wasm components through `#[ingot::feature]`, which generates the WIT world and a typed Ingot wrapper (D-ING-15).

## 5. Core cross-subsystem types

Rust names are canonical; shared types live in `base` unless another crate is named. Owners in brackets.

**Values**

- `Quantity<D>` [ING]: a number with dimension `D`. SI base dimensions plus plane angle as a base dimension (radian coherent, never cancelled implicitly). Rotational kinds use the strong angular system: `Torque` = J/rad, `MomentOfInertia` = kg·m²/rad², `RotationalStiffness` = J/rad²; std defines named units so datasheet literals stay short (`Nm` is newton metre per radian; energy is written `J` or `[N*m]`). Oscillation angular frequency (ω = √(k/m), the ω in ωL) is a kind of T⁻¹, distinct from angular velocity (plane angle per time), and phase is dimensionless; a rotation becomes a phase only through an explicit `radian` conversion. Affine quantities: °C and °F are points, kelvin values are differences, `.absolute()` converts. Complex quantities. Every dimensional literal carries its unit; there are no default units; conversion is exact rational with one rounding. Checked at compile time, erased at runtime. ING publishes the consistent system and an oracle of at least 50 textbook rotational, electrical and thermal formulas that type-check without casts.
- `Tol<T>` [ING]: a toleranced value. Arithmetic is worst case by default, using affine forms over per-site noise symbols so repeated uses stay correlated; statistics (RSS, Monte Carlo, distributions, correlation groups) are explicit calls. A `Tol<T>` may be passed wherever `T` is declared: the body computes with the nominal and the tolerance's site is forwarded to the feature that realizes it, which records it as PMI on an anchored aspect query, re-resolved on the final Part like an explicit control. A PMI target that no longer resolves (split, merged or deleted) fails an `Error`-severity check and never degrades to a Note.
- `ErrorBound<Q>` [`base`]: `{ value: Q, norm, kind }`; norm `LInf`, `L2`, `Energy`, `Pointwise` or `Goal(functional)`; kind `Guaranteed`, `Estimated { calibration }` or `Indicator`, where the calibration names its class and its exceedance level α (0.01 for a 99th-percentile factor). A `Guaranteed` bound on a quantity requires a proof in that quantity's norm. A check declares `decides_on`, the weakest kind that may decide it; "evidence" never names a bound kind. Energy-norm bounds never certify pointwise or extremal quantities; `Guaranteed` goal bounds exist only for bounded linear functionals (regional averages over a stated volume, reaction resultants, compliance, mean temperature) and for eigenvalues where the method proves the bound (a guaranteed lower bound for scalar diffusion on fitted simplices, for example).
- `ErrorBudget<Q>` [`base`]: `{ parts: map ErrorSource → Component<Q>, total: Component<Q> }`, where `Component<Q>` is `Quantified(ErrorBound<Q>)` or `NotQuantified { reason }`. `ErrorSource` is one of: discretization, algebraic, temporal, quadrature, geometry, floating point, input and tolerance, statistical, model form, reduction or surrogate, interpolation, regularization. Composition: bounds in the same norm add; bounds in different norms never combine (the total is `NotQuantified`); components carrying a confidence (statistical, conformal, input distributions, and calibrated `Estimated` bounds at their α) become bounds at a stated per-component level and combine by a union bound, so the total, and every `CheckOutcome` that rests on it, carries confidence 1 − Σαᵢ; distributions are reported alongside and never summed with intervals. The total is `NotQuantified` if any part is, and its kind is the weakest part's. Each source has one producer: model form comes only from validation of the physics and constitutive model (COV), and dimensional reduction (shells, beams), reduced-order models and surrogates file under reduction or surrogate (FLX). A model-form bound from validation applies to a check functional only when the validation plan lists that functional's response-quantity class (quantity, location type, regime) among its validated classes; otherwise the model-form part is `NotQuantified { reason: UnvalidatedQuantity }`.
- `Approx<T>` [ING]: a value with an `ErrorBudget<T::Delta>` restricted to `Pointwise` and `Goal` norms. Comparisons return `Truth`. A reduction of a Field (a maximum, an average) is `Quantified` only when Flux estimated that functional; otherwise it is `NotQuantified` and comparisons on it are `Undecided`.
- `Truth` [ING]: `True`, `False`, `Undecided`. One decision rule, owned by ING and used by `if`, `match`, `require` and query `where:`: disjoint enclosures decide, subject to the check's `decides_on`. Control flow on `Undecided` yields the value `Undecided { needed, fidelity }` at the node's effective fidelity; it is cached like any value, `try` cannot catch it, and dependents receive `DependencyUndecided`. The Evaluation's fidelity ceiling changes only reporting, never a value. While a higher-fidelity node of the same target is demanded, the consumer's `ResultStatus` is `Pending`; at the ceiling the Evaluation report raises the failure with the margin and the accuracy needed (`ING6401` for control flow, `ResolveError::Ambiguous` for a `where:` filter).
- `Money<C>` [std, with Rust `Money { amount: Decimal, currency }` in `base`]: a decimal amount with an ISO 4217 currency type parameter; not a `Quantity`; no implicit conversion.
- `ExternalText` [ING, AGT]: untrusted text with origin, written `external("...")`; never interpreted as instructions.
- `Labels` [`base`, KLN, AGT]: two parts, both joined through every derivation by Kiln and carried by every model context (section 7.6).
  - The confidentiality part `{ level, controls, scopes, licences }` is a lattice. `level` is public < internal < confidential; `controls` is a set of (regime, classification) pairs such as (ITAR, category) or (EAR, ECCN); `scopes` is a set of organization-defined scopes such as `customer:<name>` or `program:<name>`; `licences` is a set of `DataLicence`. The join takes the maximum level and the union of each set. A principal may read a value only if it satisfies every element, and `api` enforces this at every boundary. Clearances, write-down, encryption domains and live replication use this part only.
  - A principal, endpoint, recipient or service satisfies a `controls` element only through a `ControlAuthorization` [KLN]: regime, classifications, basis (US person, licence, licence exception, no licence required), permitted countries and recipients, conditions and expiry, created by an export officer with a second person. A node whose label has `controls` runs and is stored only in the regulated cloud, in end-to-end mode or in a customer deployment, unless such a record covers the operator's staff.
  - The integrity part `{ instruction_tainted, data_untrusted }` never blocks a read or a write; it sets risk classes and auto-merge eligibility (AGT). It attaches to input cells by provenance. A human merge of the Change that introduced an input (a lockfile pin, an Asset, a source span) clears both flags on that input's structure and typed values; free text keeps its integrity until a per-span endorsement (section 7.6). Kiln joins integrity from the inputs' current endorsement state. Declassification never changes integrity, and endorsement never changes confidentiality.
- `PrincipalId`, `Budget` [AGT], `PriorityClass` [AGT], `ResultStatus`, `CheckOutcome` and the `PlacementPolicy` trait (which `repo::policy` implements and Kiln calls) live in `base` so that `kiln` never depends on layers above it.

**Geometry and product structure**

- `Body` [ANV]: geometry in one of four representations: `BRep` (exact NURBS, analytic and procedural surfaces, cellular topology with regions), `Implicit`, `Mesh`, `SubD`. Representation lattice: Mesh ⊂ BRep, SubD ⊂ BRep, BRep ⊂ Implicit; SubD ⊂ BRep is exact except near extraordinary vertices and semi-sharp creases, where the conversion records a bound. Mixed operations return the least representation that holds both operands without approximating geometry or dropping B-rep faces that remain on the boundary (leaf-preserving conversion keeps exact faces, their `EntityId`s and attributes). Approximating conversions record per-face bounds `{ position: ErrorBound, normal: angle bound }` and per-edge bounds `{ position, tangent: angle bound }`, which compose through stated propagation rules with certified conditioning (offsets, intersections, blend spines, Natural-offset corners) or become `NotQuantified`. The rules carry tangent and normal bounds, never position alone, and an offset of an approximated face propagates only where a certified curvature bound shows the offset is regular. `Body` lives in Anvil's crates; `field` and `kiln` reach Bodies only through handles in `base`.
- Two identities: `GeometryId` hashes the canonical encoding with names, lineage and name-keyed attributes removed, and `ObjectId` hashes the full encoding with names. A Body's `GeometryId` numbers its entities in a canonical geometric order. An Assembly's hashes the canonically ordered multiset of (child `GeometryId`, placement, mates by canonical entity number), without Instance names or paths; MEC owns that encoding. Caching, revision identity and approvals use them as sections 7.2 and 5 (`ItemDefinition`) say.
- Design attributes [ANV]: every attribute class declares whether it is definitional. Definitional attributes (size tolerances and GD&T, general tolerances, ISO 13715 edge callouts, datums, `HoleSpec`, `ThreadSpec`, `Weld`, surface texture and finish, ply and laminate records, region material assignments) are encoded name-free by canonical entity number and enter the `ItemDefinition`. Role aliases and display styles are not definitional.
- `Part`, `Assembly`, `Instance` [MEC]; `Transform` (rigid placement); `CoordSys` (a `Transform` anchored by a `Query`, re-resolved on every rebuild) [MEC]; `ShapeAspect` (an identified portion of a Body's boundary for GD&T, kinds such as `OfSize`, `Hole`, `Pattern`; named after AP242's `shape_aspect`) [MEC].
- `CallSite` [ING]: the identity of a call site, derived from source text only. A `let` statement's identity is (item path, arm path, binding name). An unnamed statement's identity is (item path, arm path, nearest preceding binding name, ordinal after it). A call's identity inside a statement is its operation or feature name with its occurrence index among calls of that name. A `CallSite` is the path of these frames (statement, call, iteration keys) from the Evaluation's root, `fn` calls included, so two calls of one helper name their entities apart. Iteration contributes keys, never positions: iteration over entity lists or resolved queries keys by `EntityId`; pattern generators return keyed lists (`linear` keys `(i, j)`, `circular` the angular index, `at_points` the anchor's `EntityId`, `fill` lattice coordinates from a declared origin, `by_density` each seed's initial key); only plain integer ranges keep integer keys. Renaming a binding is a refactor that writes `#[was(old_name)]` and preserves identity. CRDT block ids are never part of a `CallSite`; they map onto these identities for live collaboration only. Exporting to Git, re-importing and rebuilding leaves every `EntityId` unchanged.
- `EntityId` [ANV]: hash of (kind, `CallSite`, role, generating entity ids, discriminator). Argument values are excluded, so dimension edits that keep topology never rename entities; topology changes surface as `HistoryRecord`s and typed `ResolveError`s. Features may attach role aliases (`FeatureRole`) to entities they return.
- `HistoryRecord` [ANV]: created, modified, split from, merged from, deleted.
- `Query` [ING, ANV]: criteria over provenance and roles plus certified geometric filters, resolved by `anvil::resolve` as its own Op on every rebuild. No positional indexing. Rank selectors (`longest`, `largest`, `first(along:)`) are allowed only after a provenance anchor or role filter; elsewhere the language service raises `ING-L-FragileSelector`. Failure is a typed `ResolveError` with ranked fixes; success may carry Notes (`Merged`, `Partial`, `FragileAnchor`, `NearTie`) that checks may forbid. Each operation declares per `Query` parameter whether it uses a surface (accepts these with a note) or an extent (edges of a face, areas, GD&T and PMI targets, drawing items). For an extent, a merge, a partial deletion, an `Ordinal` discriminator or a rank selection with a `NearTie` note fails with a typed `ResolveError` unless the call writes `on_merge: Accept`, `on_partial: Accept` or `on_fragile: Accept`. Resolution never silently picks another entity at the evaluated configuration. Stability across declared parameter ranges is sampled evidence from a separate on-demand analysis (ANV) that reports `RankSwap`; protected-branch CI runs it on every query that ends in a rank selector or reaches an `Ordinal` id.
- `DisplayPackage` [ANV, UIX]: a per-Body clustered tessellation keyed by `GeometryId`, with stated chordal error and canonical-entity-number back-references that consumers join to `EntityId`s through the Body's face table, cached in CAS and consumed by every renderer. Its pages carry no names, so equal geometry in two designs shares pages; a cluster DAG arrives in phase 2 (13.2).
- `ViewState` [UIX]: camera, visibility, sections and Field displays; stored as repository files; used by the UI, agents, snapshots and comments.
- `RenderProfile` [UIX]: locale, theme, display units, font package pins and renderer behavior version; a `ViewState` under a `RenderProfile` determines a Snapshot.

**Physics**

- `Field<D, V>` [`field`, FLX]: a quantity over a domain `D`. Domains are spatial or entity sets (`Body`, `Regions`, `Faces`, `Edges`, `Vertices`, `Points`, `Instances`, `Ports`), parameter domains named by a quantity type (`Time`, `Frequency`, `Temperature`, `AngularVelocity`, `StrainRate`, …), index sets (`Mode`, `LoadCase`, `Sample`, `Variant`), and products written as tuples. Examples: `Field<Body, Stress>`, `Field<(Body, Time), Temperature>`, `Field<Temperature, YoungsModulus>`, `Field<(Instances, Time), Transform>`, `Field<(Ports, Frequency), Complex<Impedance>>`, `Field<AngularVelocity, Length>` (a stability lobe), `Field<Body, ValidityZone>`. Values may be scalars, vectors, tensors, complex values or enums. Representations: `Analytic`, `Discrete`, `QuadraturePoint`, `SparseGrid`, `PerEntity`, `PointCloud`, `Reduced`, `Surrogate`. A `Part` is accepted wherever a `Body` domain is expected. Every result Field carries an `ErrorBudget`. Waveforms, spectra, sweeps, mode sets, load cases, ensembles, tables and material curves are all Fields, never separate types.
- `Network` [ELX, FLX]: see glossary. Each port type declares its power expression, and the compiler checks that it is a power.
- `Material` [COV]: properties as Fields over state domains (temperature, strain rate, direction), statistical basis per property, constitutive model ids, provenance, certification, uncertainty, `DataLicence`, environmental records and microstructure descriptors.
- `ValidityEnvelope` [COV]: declared conditions where a model is trusted. Evaluates to a zone Field (`Calibrated`, `Extrapolated`, `Invalid`, `Unassessed`) and to checks with disposition `Flag` or `Refuse`. Only humans waive. Crucible suggests escalation to a valid model but never switches models automatically.

**Evaluation and collaboration**

- `Feature` [ING]: an Ingot function from typed parameters to Parts, Bodies or plain values, with metadata that generates its dialog, docs and agent tool schema.
- `Op`, `OpKey`, `OpCx` [KLN, in `base`]; `ObjectId`: SHA-256 identity of a canonical CAS object, with a one-byte algorithm code reserved.
- `CheckId` [ING, in `base`]: (the attachment's `CallSite` or Instance path, the `require` statement's identity under the `CallSite` statement rule, the `name` if written). It never derives from predicate text, so editing a limit keeps the check's identity, verdict history and Evidence records. Approvals, merges, diffs, evidence addressing and Waivers name checks by it.
- `CheckOutcome` [ING, in `base`]: `{ verdict, fidelity, decides_on, evidence_records, value, limit, margin, severity, source }`. `verdict` is `Pass { conditional_on }`, `Fail`, `Undecided { reason, needed }`, `Error(Failure)` or `Skipped { reason }`. A `Pass` whose `conditional_on` lists unquantified components (typically model form) is conditional. It counts only when a policy allowance covers each listed component; the check is then re-evaluated with that allowance as a declared `Estimated` component, and without one the verdict is `Undecided { reason: Unquantified(components) }`. A policy allowance [KLN] is a signed policy record naming an error source, its scope (check kinds, Items, model families), the allowance as an `Estimated` component and its citation (code and clause, such as a design-code partial factor that the code states covers model uncertainty); it changes only through a Proposal with two signers. "Provisional" is the derived predicate "fidelity below the declared one", never a verdict. `Severity` is `Error`, `Warning` or `Info`.
- The gate predicate [ING, used by KLN and AGT]: a check meets a gate (a protected merge, a Proposal, a release) when its severity is below `Error`, or its verdict is a non-provisional `Pass` in a platform class the gate accepts (section 7.3) with every `conditional_on` component covered by a policy allowance, or a Waiver covers it. Every rule that says "passes every check" means this predicate.
- `Fidelity` [KLN]: `Preview`, `Interactive`, `SignOff`.
- `ResultStatus` [`base`]: what a consumer holds for a demanded result: `Pending`, `Proxy`, `Ready(Fidelity)`, `Stale`, `Failed`, `Aborted`.
- `PlatformClass`, `DeterminismGrade` [PLT, KLN] (section 7.3).
- `Proposal` [AGT, `repo`]: branch, rationale, CI report, author, delegation chain, parent and plan, risk class, labels, snapshots, provenance.
- `ItemDefinition` [KLN]: the name-free definition of one Item revision, per Item kind: for a Part or Assembly, its `GeometryId`s with definitional attributes, `Material` `ObjectId`s, properties and the BOM by value; for a Software item, its binary hashes, software bill of materials digest, target bindings and toolchain digest; for a catalog part, its approved-manufacturer entries; for a document, its semantic content; for a manufacturing program, its posted text and simulation evidence ids. Late-bound fields stay placeholders.
- `ApprovalSubject` [KLN]: `{ base revisions, ItemDefinition digests of every affected Item, check-verdict digest (CheckId, verdict, fidelity, platform class, value, limit), effectivity, evidence record ids }` for releases and change orders. Approvals sign its `ObjectId`; the `ChangeId` and the full CI report are unsigned provenance, and `act.commit` recomputes the subject at its target and refuses a mismatch. Act plans and manufacturing programs have their own subjects (the plan digest; the posted program and its simulation evidence).

## 6. Ingot syntax reference

The canonical example. Every tab's examples follow Ingot's grammar; ING owns refinements and must keep this example valid.

```
use std::mech::{sketch, rect, extrude, rib, fillet, part}
use std::materials::alu_6061_t6
use std::sim::quick::static_stress

/// L-bracket with a stiffening web.
#[feature(category: "Structure", icon: "bracket")]
pub feature bracket(
    #[ui(step: 5mm)]
    width: Length in 20mm..=400mm = 60mm,
    thickness: Length = 4mm ± 0.1mm,
    load: Force = 1.2kN,
) -> Part {
    let outline = rect(width, 40mm)
    let base = sketch(plane.xy) { outline } |> extrude(thickness)
    let web = base.edge(role: end(outline.top)) |> rib(height: 20mm, t: thickness)
    let body = base + web
    let solid = body |> fillet(body.edges(new), 2mm)
    let p = part(solid, name: "Bracket").material(alu_6061_t6)
    let clamp = base.face(role: start_cap)
    let study = static_stress(p, fixed: clamp, force: load, on: web.face(role: end_cap))
    let stress = study.von_mises.max(over: p.away_from([clamp, web.face(role: end_cap)], 2 * thickness))
    p.require(stress < 0.6 * p.material.yield_strength(at: 20degC))
}
// width + load  →  error ING3001: cannot add Length and Force
```

The edge is selected by its role, `end(e)`: the edge the end cap gets from profile edge `outline.top`, never a rank. Every sweeping feature gives its faces, edges and vertices roles (ANV owns the vocabulary). The stress check reads a regularized maximum over a region that excludes the clamp and the loaded face by twice the wall thickness, because stress is singular where a clamped face meets a free face and may be singular at a loaded patch's edges (section 7.1). The result is an `Approx<Stress>` with an `Estimated` bound, the check is three-valued, and an ING oracle shows that it decides at `SignOff`.

Weak forms:

```
let u = trial(Displacement, p)
let v = test(u)
let elasticity = inner(sigma(u, p.material), eps(v)) * dx(p)
              == dot(traction, v) * ds(web.face(role: end_cap))
let result = solve(elasticity, fixed: clamp)
result.von_mises  // Field<Part, Stress>
```

Language rules every tab follows: no new keywords for domain concepts. Constraints are ordinary functions over `Expr<T>`; interfaces are records marked `#[interface]`; variants are enum or record parameters marked `#[configuration]` on assembly features and selected with `if` and `match`; an Instance's or Instance set's existence may depend only on configuration parameters and constants (a compile error otherwise), so Kiln can compute the 150% BOM by abstract interpretation with SAT checks instead of enumeration, while an Instance set's member count and placements may depend on any value, keyed by its anchors (a fastener per resolved hole is one BOM line whose quantity is evaluated); variant rules and requirements are `require` checks and `std::systems` records; builder blocks (`sketch { … }`, `network { … }`) are the only block sugar. Constitutive code never differentiates through loops: local Newton solves use the kernel IR's `local_solve(residual, x0)`, whose derivative comes from the implicit function theorem at the converged point.

**std package names.** `std::mech`, `std::mfg`, `std::electronics`, `std::systems`, `std::sim` (Flux building blocks: spaces, forms, `solve`, plans, quick studies), `std::physics` (physics models built on `std::sim`), `std::materials`, `std::opt`, `std::uq`, `std::agents`, `std::explore`. Sub-packages nest under these (`std::physics::regime`, `std::agents::proposal`). First-party packages outside std use `crucible::`; catalog parts use `parts::<manufacturer>::`; WIT packages use the `crucible:` namespace, one package per domain.

## 7. Decided architecture (do not contradict without a change request)

### 7.1 Engines

- **Anvil.** One Body type over four representations with the lattice above. Cellular B-rep with regions for multi-material parts and conformal meshing. Per-Body scale-relative resolution plus per-entity tolerances; no global tolerance. Exact adaptive predicates for linear decisions; certified enclosures with recorded, capped tolerance growth for decisions on curved geometry, made in rounds by dimension against tolerances frozen at each round's start, so outcomes never depend on pair order. Decisions are the same at every fidelity: at `Interactive` a floating-point filter with a forward error bound decides when the bound separates the alternatives, and the certified rule runs otherwise; only seeding and tracing may be uncertified at `Interactive`. Every operation checks separation of created and modified entities against the whole Body through the broad phase, not only against neighbours. Surface-surface intersection: every intersection point is a certified root of the exact equations, never a point selected from a sample set by a distance threshold. Freedom-to-operate review of US 12,229,885 B1 (inventor Alyn Rockwood, assignee an individual; Zoo's engine overview describes a related method) covers claims 1, 6, 11 and 16, the CPU and GPU paths and pending continuations; counsel's written opinion is a phase 0 gate item (13.1). Phase 1 SSI has no sampling stage: closed-form intersections among planes, quadrics and tori, and certified subdivision for the other phase 1 pairs; counsel confirms that this path avoids the claimed comparison. GPU sampling that orders CPU work and runs an exact integer broad phase joins in phase 2, only after a favourable opinion. History records in every operation. Blends are a staged research program: stage 1 supports procedural blend, offset and swept supports (sequential fillets), `RollOver` overflow, valence-3 corners with unequal radii and mixed convexity by setbacks, chamfer–fillet corners, termination at smooth edges and linearly varying radius; later stages add valence four and above, Field-driven radii and G2 and G3 sections; an implicit fallback only when requested, with stated deviation. G2 and G3 analysis built in. Anvil owns all mesh generation, including volume meshing, adaptation and node optimization; Flux passes sizing and metric Fields. Anvil owns the geometric constraint solver (`anvil::solve_constraints`, `anvil::analyze_constraints`). Anvil owns `anvil-planar`: exact predicates on stored integer-coordinate 2D geometry with lines and arcs; constructions (offsets, Minkowski sums with a disc, arc intersections) snap to the grid in a declared conservative direction, so derived geometry passes the exact rule checks by construction (`anvil::planar::boolean`, `offset`, `distance`, `medial_axis`). Flex circuits bend with the sheet-metal `anvil::fold`. Anvil's operations catalog is the canonical list of operation names.
- **Label invariance.** An operation's geometry, connectivity, Field values and statistics are invariant under any injective renaming of input `EntityId`s and `CallSite`s; only name sections may change. Canonical orders, symbolic-perturbation indices, independent-set priorities, random seeds and the order of statistical inputs (tolerance noise symbols, Sobol dimensions) come from geometry, topology and argument values, never from names. Oracle: rebuild every golden product with every name re-randomized; geometry hashes and check values, statistical checks included, are identical.
- **Flux.** Physics stated as weak forms in Ingot, compiled through the shared kernel IR (7.5). Discretization is chosen per region: dimensionally reduced models where a local slenderness criterion holds (Timoshenko and Vlasov beams for members and struts; Reissner–Mindlin shells on Anvil mid-surfaces for thin walls, by a local criterion t/L_local ≤ 0.2, where L_local is the smallest of the span between supports, the radius of curvature, the distance to the nearest concentrated condition (a point or line load, the edge of a load or support patch inside the wall, an opening or a feature) and, for a distributed load q, the length |q|/|∇q| over which it varies; distributed loads, body forces and inertia that cover the wall do not shorten L_local), coupled to solids through rigid and Nitsche-based mixed-dimensional interfaces; an immersed adaptive octree for solids (aggregated CutFEM at `Interactive` and `SignOff` with at least four cells across any section, finite cell for voxel data; the shifted boundary method serves at most `Preview`); fitted meshes for contact and turbulent boundary layers, with octree wall refinement for laminar thermal and frozen boundary layers; beam-lattice models with node corrections and homogenization for lattices; isogeometric shells. Matrix-free high-order FEM with sum factorization; own p- and h-multigrid and deterministic AMG; a canonical linear-algebra crate (fixed machine-independent blocking, canonical lane order, no FMA) for `Portable` results, with unmodified faer only in `CpuIsa`; optional PETSc and hypre bridges. Discrete-consistent adjoints from forms, chained through Kiln. The resolved `SolvePlan` (from a versioned `flux::plan` operation) is pinned and enters the cache key. Every result Field carries an `ErrorBudget`. Peak and pointwise quantities are regularized goals (a p-norm or a local average over a stated region, with the regularization error in the budget) and carry `Estimated` bounds; a raw maximum is never a goal. Flux flags singular sets: re-entrant edges and corners, material interfaces meeting the boundary, and conditions that are incompatible where they meet. Those are edges where a clamped or fixed face meets a free face, edges of a load or support patch that lie inside a face, edges where a loaded face meets a free face and the traction has a component along the free face's normal, and contact zones that contain an edge or corner of either surface. A uniform normal traction over a whole face meeting free faces at convex edges is compatible and is not flagged; smooth non-conforming contact is a low-regularity set that guides refinement but is not singular. A flagged set makes point quantities `Undecided { SingularPoint }` unless the check's region excludes it by a stated distance; each flagged set carries a default distance (FLX) that a check may override. Every `Estimated` bound is reported already multiplied by its calibrated factor and labelled `Estimated { calibration }`. A calibration class declares an applicability envelope over computable features of the result (FLX lists them), and a result outside it reports `Indicator`. A `SignOff` `Pass` that rests on an `Estimated` discretization part is confirmed by one further refinement (h/2 or p + 1, the plan's choice): the refined value lies inside the first bound and its own bound is smaller, or the verdict is `Undecided { reason: CalibrationUnconfirmed }`; Kiln's cost model counts the extra solve. Surrogate predictions are Fields with kind `Estimated { confidence, scope: Marginal }`; they may drive `Preview` and `Interactive` results and design exploration; a `SignOff` check may use one only with a per-prediction a posteriori bound in the check's norm or a confirming solve; inside optimization loops calibration uses weighted conformal prediction. From phase 2, Newton and arc-length solvers detect bifurcation points and return `Bifurcation { load, modes }` instead of silently choosing a branch; in phase 1 Newton accepts only forms declared convex and returns `Unsupported { reason: NoBifurcationMonitor }` otherwise. Flux also provides rigid and flexible multibody dynamics, Cosserat rods for cables and hoses, the Network compiler and DAE solver, block-triangular sparse LU, full-wave electromagnetics, magnetodynamics with motion, and the general operations non-variational methods need (BVH build and traversal, neighbour lists, segmented reductions, counter-based random streams, fast multipole and hierarchical matrices, FFT solves). GPL tools (Meep, Elmer, OpenFOAM, LAMMPS and others) run only as External Ops or oracles.
- **Kiln.** Suspending scheduler with dynamic dependencies, Salsa-style durability and backdating, verifying traces in memory and constructive traces in the shared cache. A node's label is a separate memo output with its own change marker: verification re-joins labels from current inputs even when the value backdates, and a shared-cache hit returns only the value, with the label recomputed locally. Interactive early cutoff compares values directly; hashing happens off the interactive path. Progressive refinement is a set of independent nodes keyed by fidelity. GreedyDual-Size eviction. A Derivatives section specifies `trait Differentiable: OpImpl { tangent, adjoint }` in `base`, reverse traversal from a scalar goal, and checkpoints keyed by (`OpKey`, step) in a `Checkpoint` retention class that eviction drops first. Kiln is generic: Anvil, Flux and Ingot register node kinds through the operation contract in `base`. Two evaluation-wide limits are enforced as Aborts: a demand-depth limit on nested node demands (default 10,000) and an aggregate fuel governor per Evaluation taken from its budget.
- **`repo`.** Every edit becomes an immutable Change; ref updates go through a Jujutsu-style transaction log; branches are cheap. A merge is clean only when the result compiles and resolves; no check's verdict on the merge is worse than its verdict on each parent that defines it (`Pass` > `Undecided` > `Fail` > `Error`; `Skipped` counts as undefined, and a `Pass` whose `conditional_on` gains components ranks below the `Pass` without them); no interference appears that neither parent has; there is no provenance-level geometric conflict (both sides modify, split or delete the same base entity, or one side's new entity intersects the other side's modified region); and no connectivity conflict (a merged net, harness connection or interface connection that unions nets distinct in the base and in each side). Symmetric-difference regions appear in review but do not block. Live collaboration uses a Loro block tree with Fugue text leaves. The unit of a source label is a module (one file): a feature labelled above its package lives in its own module, whose public signature may carry a lower label through a declassification record, so uncleared principals compile against the signature and evaluate the module remotely on cleared workers. The unit of live replication is (package, module confidentiality label). On reconnection the relay fast-forwards when no other participant changed the package meanwhile, whatever the duration; otherwise, when the disconnection exceeded 60 s or concurrent edits touched blocks the client also edited, offline work rejoins as a branch. `repo` keeps span-level integrity provenance: each source span records the integrity of the context that wrote it, and merges preserve it. Releases are signed tags; change orders are Proposals whose approvals are the Approvals of the release Act's plan; revision identity uses the `ItemDefinition` (section 5). The BOM is a derived view over the assembly graph with EBOM, MBOM and service BOM views. Authorization uses Cedar policies; audit, transaction logs and release tags live in per-tenant transparency logs (C2SP tlog-tiles).
- **Hardware CI.** Every Change on a protected branch rebuilds the design and evaluates its checks; regression and golden-product sign-off simulations run at least nightly. Physical tests are Acts that run on hardware rigs when their inputs change. `unattended_safe` is a signed site policy issued by a named safety officer; a runner never declares it for itself. Production equipment (machine tools, robots, lasers, production presses and furnaces, and every device class `send_to_machine` reaches) never receives it. A test rig receives it only with a risk assessment to ISO 12100 that the safety officer signs for the rig and its test article, interlocked guarding and its own safety-rated stop. The runner enforces the policy's energy limits locally (force, displacement, temperature, voltage, current, stored charge), and battery tests above the policy's cell energy run only in a rated containment chamber with gas detection. Rigs under that policy run through the `run_rig_test` Act after an Approval, without on-site confirmation. Their results are Evidence records signed with TPM-held device keys under measured boot.

### 7.2 Cache keys and failures

An `OpKey` is the SHA-256 of:

1. the operation name and behavior version, or for a Wasm component the SHA-256 of its determinized binary, or for Ingot code the code hashes of the modules actually used plus the language behavior version;
2. the canonical encoding of the arguments, including any resolved plan;
3. the identities of the inputs: `GeometryId`s for the geometric stage of an entity-naming Op and for Flux solves (plus the canonical numbers of the entities their conditions reference); `ObjectId`s otherwise;
4. the platform class of the result, which is `CpuCanonical` for `Portable` and `Certified` results;
5. the effective fidelity, which each operation version maps from the requested fidelity (an operation that ignores fidelity maps all three to one value);
6. for External Ops, the host image digest.

The lockfile as a whole never enters a key. Entity-naming Ops cache in two stages: the geometric stage, keyed by input `GeometryId`s, numbers new entities canonically and refers to input entities by canonical number, so std features called from different designs share every geometric result; the relabeling stage, keyed by the geometric output's id, the `CallSite` and the inputs' name maps, assigns `EntityId`s. Both stages apply to failures and notes: the geometric stage reports them over canonical numbers with fix templates, and the relabeling stage maps them to `EntityId`s and source fixes that name the design's own bindings. Every node whose value carries `EntityId`s (feature calls, entity-naming Ops, query resolutions) includes its `CallSite` in its key. Random streams are keyed by the operation identity, argument values and input `GeometryId`s or name-free content hashes, never by class, fidelity, `ObjectId`s of named values or `CallSite`s; KLN owns the mechanism.

**Failures and Aborts.** A deterministic `Failure` (a fillet radius too large, a query split) is a value: catchable with `try`, cached, and wrapped as `DependencyFailed` for dependents. `OpVersionRetired` is a catchable `Failure` that is never memoized or written to the shared cache, because it depends on the engine release rather than on the inputs. An Abort is environmental: `try` cannot observe it, it propagates to every transitive dependent, and no node that observed one writes a memo entry, a CAS object or an attestation. Oracle: inject environmental faults at random Ops in 10,000 runs; every value that reaches the memo or the shared cache equals the fault-free run's value. Every node terminates with a value or a typed `Failure`; every Evaluation terminates or aborts.

### 7.3 Determinism

- `PlatformClass` [PLT]: `CpuCanonical { epoch }` (every Tier 1 CPU target, browsers included, at any thread count and ISA level), `CpuIsa { isa, epoch }` (a native fast path for one ISA level, which may use FMA and native widths), `Gpu(GpuClass)` (one compiled pipeline on one verified device class: driver and shader-compiler build plus pipeline hash, where on Apple platforms the shader compiler is the OS build), `Unverified` (unlisted devices and external hosts). The operating system is never part of a CPU class. In prose: "the canonical class".
- `DeterminismGrade` [KLN], declared per operation version: `Portable` (bit-identical across the canonical class; the only grade for geometry and oracle reference results), `ClassExact` (bit-identical within one class), `Certified` (output independent of the class that computed intermediates, for example GPU filtering with CPU decisions). Kiln selects the class an Op runs in; there is no separate execution-mode concept.
- Results from `CpuIsa`, `Gpu` and `Unverified` classes never substitute for canonical results. A check, release or Proposal that requires canonical results recomputes them in the canonical class, with one exception: a check may rest on a pinned non-canonical Field (GPU solves, CPU certifies) when its residual and error bound are computed canonically from that Field. A release pins the `ObjectId`s of every External Op result and Evidence record it relies on. `CpuIsa` variants with FMA may serve `Preview` and `Interactive` fidelity when a kernel family loses more than 1.3× without FMA; sign-off recomputes canonically, and Kiln's cost model counts the recompute.
- Mechanisms [PLT]: `detmath`, the only elementary-function library in `Portable` code (correctly rounded, ported from CORE-MATH); a canonical lane order for horizontal operations (every reduction, scan or cross-lane operation in `Portable` code follows the 8-lane f64 or 16-lane f32 tree of `det_sum`; element-wise code may use any native width); binned reproducible summation (`exact_sum`) where partitioning varies; on CPU classes no implicit FMA contraction anywhere and explicit `mul_add` only inside `detmath` and error-free transformations; on GPUs, integer arithmetic for everything that must be exact (integer-limb reductions), non-finite detection on the CPU after readback by integer inspection, and a known-answer test for each compiled pipeline at creation and after any driver or OS update, with CPU fallback on failure; the canonical linear-algebra crate.
- The determinism suite runs on every merge on a representative set (Linux x86-64 with forced v2, v3 and v4; Linux ARM64; macOS ARM64; wasm32 in Node and in headless Chrome, threaded and single-threaded) and on every other Tier 1 target and browser engine at least nightly. A nightly divergence bisects automatically, opens a severity-1 determinism incident and blocks promotion to beta.

### 7.4 Wasm execution

- One determinizer, versioned, in `wasm-host` [PLT]. The registry runs it at publish time; the local toolchain runs it at build time for unpublished Wasm components; hosts execute only determinized binaries. It validates the binary, rejects nondeterministic features, and injects fuel metering (with a check that also reads a host cancellation word), stack-depth limits, growth guards that turn a host-caused `memory.grow` or `table.grow` failure below the declared maximum into an Abort, and NaN canonicalization only where NaN bits become observable (float stores, `reinterpret`, the sign operand of `copysign`, host-call arguments and results, and v128 values from float operations that reach bitwise, integer-lane, shuffle, store or extract-to-integer instructions). Cancellation lands only at fuel-check points; epoch interruption is never used. Where shared memory is absent, cancellation lands at Op boundaries, and Kiln runs every Op estimated above 100 ms in a disposable worker that it cancels by terminating. When verifying modules emitted by the Ingot code generator, it checks for forbidden instructions or imports, a fuel decrement dominating every loop back-edge and function entry, a non-finite check before every observable float use, and a depth counter in every prologue.
- Executors. Native: Wasmtime pinned to its LTS releases, with Cranelift. Browsers: one first-party Wasm component runtime instantiates determinized core modules in the browser's engine, with no per-component generated JavaScript. iPadOS: the web build runs in a thin WKWebView shell, where JavaScriptCore compiles Wasm, so it shares the browser runtime and its asynchronous `crucible:ops` bridge. The app runs only the first-party Wasm components shipped inside its binary and evaluates registry Wasm components remotely, so no downloaded code runs in it (App Review guideline 2.5.2); registry packages appear only as dependencies of an opened design, never as a browsable catalog (guideline 3.2.2(i)). Only first-party Wasm components (std and Crucible's own packages, built by the operator's registry builders) run in the engine process. Every third-party Wasm component runs out of process on every target: in an OS-sandboxed worker on native targets, one per tenant and confidentiality label on servers, and in an opaque-origin sandboxed worker in browsers. Browsers evaluate third-party evaluation-world components remotely until the asynchronous bridge passes PLT's executor oracle in browsers.
- Ingot executors. Until the Ingot code generator ships, the Ingot reference interpreter (written in Rust, in the canonical class) is the only Ingot executor on every target. The code generator to Wasm enters when `ingot-bench` shows Ingot above 2% of a golden-product rebuild; from then on, generated modules pass the determinizer's verification and run on the executors above, and the interpreter remains for cold start, debugging, replay and differential testing.
- Evaluation worlds import no WASI and are deterministic. Their `crucible:ops` imports are Component Model async functions in the callback ABI (no stack switching), so a host may answer them across a process or agent-cluster boundary, and native hosts may still answer at once. Results never depend on completion order or timing, and fuel never counts host time. Tool and connector worlds use WASI 0.3. A determinized Wasm component whose host calls are all `Portable` is itself `Portable`.
- Constitutive models use the `crucible:material/constitutive` world. Models expressed in the kernel IR get tangents by algorithmic differentiation (with `local_solve` for local Newton solves); opaque Wasm models must supply consistent tangents, verified by a Taylor-test oracle, and a plasticity benchmark must show quadratic global Newton convergence.
- PLT publishes one overhead table that ECO cites. Determinizer targets: scalar-float components ≤ 10%, SIMD-float components ≤ 25%, fuel and stack metering ≤ 10%, per component class. Isolation targets: one `crucible:ops` round trip from a sandboxed worker costs at most 20 µs between native processes and 250 µs across browser agent clusters, plus argument transfer per MiB; `crucible:ops` offers a batched call form; and std's Wasm components, run in the third-party configuration on every release, stay within 15% of their in-process time.

### 7.5 Shared kernel IR

One kernel IR, in the crate `kernels`, is the source of every compute kernel that affects results: weak forms, constitutive functions, analytic Fields, implicit tapes, constraint residuals, Network residuals and device models from Verilog-A. Hand-written kernels use the IR's Rust embedding. The IR fixes the order of every floating-point operation and reduction on CPU back ends. IR v0 holds only the constructs phases 0 and 1 need (element kernels with sum factorization, pointwise constitutive functions with forward-mode derivatives, implicit tapes). It is additive-only once its first consumer compiles against it, except for defects its first consumers find, and freezes at the phase 0 gate once one H¹ elasticity kernel with sum factorization, one constitutive function with forward-mode derivatives and one implicit tape have compiled through both CPU back ends and passed their oracles. Network, constraint and Verilog-A constructs join in the phases that need them. Back ends: ahead-of-time Rust with canonical SIMD and Wasm SIMD128 in phase 0; WGSL through wgpu in phase 1 for implicit preview, and for interactive elasticity only if the phase 0 gate measures `CpuIsa` kernels missing the interactive simulation row of 13.3 on the reference laptop (otherwise WGSL elasticity joins in phase 2); server f64 GPU paths use wgpu on Vulkan with `SHADER_F64` first; a CUDA or HIP back end (CubeCL or another) is reconsidered at the phase 4 gate. WGSL kernels never claim bit-identity with CPU kernels. Every GPU path has a registered CPU path. Render shaders are WGSL and never affect results. FLX owns the kernel IR and its back ends.

### 7.6 `api`, agents and UI

- One API over MCP and native SDKs (Rust, Python, TypeScript, plus a C ABI). Every method is `<group>.<name>` in eight groups: Session, Read, Edit, Evaluate, Inspect, Compare, Propose, Act. Registry, event and archive methods belong to these groups (search, fetch and subscribe are Read; publish, yank, export, release and deviation grants are Act classes). There is no other group.
- Agents work only on branches, with scoped permissions, cost budgets and clearances. They must build, pass every check and attach snapshots before proposing; passing every check means every check meets the gate predicate (section 5). Every agent Proposal is attacked by an independent verifier that reasons over a typed view (IR, semantic diff, check results) with the author's free text elided. Risk class is computed by the server from the semantic diff; auto-merge only for the two lowest classes.
- **Context labels and write-down.** Every model context carries a label: the join of the labels of every value returned to it, typed or textual. For the hosted crew the context is the conversation. For an external MCP host it is the pair (user, client identity), where the client identity is the registered key of an attested client and otherwise one shared unattested identity per user. Every token family, refresh, concurrent grant and stdio launch of that pair joins one monotone label stored on the server. A context label resets only through `session.reset_context`, which a human confirms with WebAuthn after clearing the host's conversation; the reset is audited and shown in provenance. Reading untrusted free text (the content of an `ExternalText` handle) or an instruction-capable image marks the context `instruction_tainted`; reading any untrusted value marks it `data_untrusted`. Every write (edit, Proposal, comment, review, exploration record, Act payload) carries at least the context's label. Write-down compares the confidentiality part only: a write to a destination with a lower confidentiality label fails with `label/write_down` unless a declassification record signed by two people, one of them an export officer, names it. Integrity flags never block a write. Untrusted typed values are returned by handle, and edits cite the handle.
- **Free text is never endorsed by merging.** Free-text spans (comments, doc comments, string literals, description templates, and identifiers neither produced by the compiler nor typed by a human) are returned as `ExternalText` handles when their author is outside the reader's delegation chain or their integrity is untrusted. A human merge endorses structure and typed values, never free text; free text becomes trusted only through an explicit per-span endorsement that shows it verbatim with invisible and bidirectional characters highlighted. Every value evaluated from a free-text span (a part name, a BOM description, a drawing note, embossed text) carries the span's integrity into its node's label. `api` returns every string that a response takes from a node of untrusted integrity as an `ExternalText` handle, and a Snapshot is instruction-capable when any visible Body, text or overlay derives from such a node.
- **Act approvals.** An approval request is a server record assigned to named approvers by Cedar policy and delivered only to their Crucible inbox; push notifications carry no content; anyone else who opens it sees "not assigned to you". The approval URL is never returned to a model; `act/approval_pending` carries only a request id. Error codes take the form `<family>/<code>`, so errors and API methods never share a name. The server generates the one approval page (desktop, web and tablet use the same page): file names from item number, revision, format and release tag; a server-rendered thumbnail; a content summary (Items, labels, bytes); the recipient's verification and screening dates; a diff against the last approved plan of the same class to the same recipient; and the session's purpose, marked as agent text. For a physical-effect plan the page adds the device serial, location and controller version; what the transfer replaces; the simulation verdicts with the minimum clearance and the count of unsupported semantics; the gateway's offset results with their time; the setup-sheet revision; and the steps the person at the device must take (reduced-speed prove-out, tool-length check, reduced override, propellers off). At most three pending requests per session; a denial blocks re-preparing a plan to the same recipients for 24 h and offers "report as suspicious", which freezes the session. Plans containing invisible characters, Unicode tag characters (U+E0000 to U+E007F), bidirectional controls or zero-width characters are rejected.
- **Plans and local exports.** An Act plan may carry several effects, and one Approval covers them. A release, change-notice or deviation plan lists its deliveries to the organization's own systems (ERP, MES, enterprise PLM), whose recipient records are marked internal and verified under the two-person rule; failed deliveries retry under that Approval until the plan expires. Messages outside a release, such as a new-part request into an ERP, stay separate Acts. A human's export of a payload whose confidentiality label is `public` or `internal`, with no `controls` and no recipient record, to a local folder or a local application is an audited local write, not an Act. Agent-prepared exports, labelled or controlled payloads and transfers to another organization are export Acts.
- **Approval credentials.** Approvals and signatures need phishing-resistant WebAuthn user verification with a device-bound credential. The credential is enrolled for approval from a Crucible desktop or tablet app, which records the device class, or is a roaming security key whose attested AAGUID is on an allowlist. Synced passkeys sign in but never approve or sign, and Crucible's phone clients offer no approval. Export-officer actions, physical-effect Acts, Acts whose payload label carries `controls`, and 21 CFR Part 11 signatures need AAL3 (NIST SP 800-63B-4). Signature records keep the authenticator data, client data and attestation, so they verify offline. A `standing_release` is approved by two humans over a plan that fixes recipients, channel, schema, label ceiling and expiry; later transfers are its effects and need no further Approval.
- **Physical safety.** Physical-effect Acts are the transfer Acts `send_to_machine`, `send_robot_program`, `store_machine_job` (OPC UA `Store` only), `send_print_job` and `flash_device`, and the restricted `start_print` and `run_rig_test`. Reading machine data is a Read. Crucible never issues cycle start, resume, jog, `Start` or `StoreAndStart` to any device it transfers to (machine tools, CMMs, robots, lasers, presses and press brakes, furnaces and ovens, placement and harness machines, printers); a person starts them at the device, and `start_print` is the one restricted exception. Agents may prepare transfer Acts; only assigned humans approve them.
- **Transfers.** `send_to_machine` carries a program or recipe, typed by kind (NC, DMIS, bend, placement and cut-list programs, process recipes; MFG owns the kinds), to any device reached through the machine gateway. A transfer never completes a start the device was already waiting for: drip feed is pull-only, streaming only on a request made at the control after the commit, and the gateway refuses with `DncSessionPreArmed` when a data request or DNC session is open at commit. Robot programs transfer only as files into the controller's program store, never through script, dashboard or real-time interfaces. Transfer Acts are verified at the protocol level: the machine gateway (`apps/machine-gateway`) enforces each connector's allowlist of endpoints and fixed parameter values in its own core, outside the connector, and a behavioural oracle under wire capture against real servers or vendor simulators shows that no request carries a start semantic. An interface that cannot express a start is necessary, not sufficient. The gateway connects outbound only, and its safety functions live in its core, never in connectors.
- **Firmware.** `flash_device` writes a Software item image to a named board serial through a named probe or bootloader, verifies it by read-back, and leaves the target halted or held in reset; a person at the bench releases it. Its Approval covers the image digest and the target, Cedar policy may assign the person at the bench to give it, and the approval page shows the board's hazards from its Network (rotating ports, heaters, high voltage) with a step to remove propellers and loads. Client flashing through `apps/platform` or WebUSB is the same Act. On a rig under an `unattended_safe` policy, flashing is part of `run_rig_test`.
- **Restricted Acts.** `start_print` exists only for material-extrusion printers whose serial is covered by a site policy signed by the named safety officer, declaring firmware thermal-runaway protection and smoke or heat detection that cuts printer power. It needs an Approval of the job digest plus a confirmation that the build plate is clear, given at the printer within 10 minutes before the start by a printer-side button or a one-time code shown on the printer's display. `run_rig_test` exists only for rigs under an `unattended_safe` site policy (7.1) and needs an Approval of the test plan's digest.
- **Manufacturing programs.** A program is approved over the posted program and its simulation evidence, bound to a machine class (machine package, controller family and software version, post version) and to nominal tool assemblies by T number, never to a serial or a pocket. The gateway verifies instance data (pockets, measured tools, offsets) at transfer against the setup sheet. A released program may go to any qualified serial of its class through the pull path, on an operator's request at that machine, under its release Approval; a remote push needs its own Approval.
- The UI holds no product state; every product change is an `api` Edit or Propose call. One Rust UI toolkit and wgpu renderer, native and Wasm; GPU tiers G1 (native), G2 (WebGPU), G3 (WebGL2), with identical features and declared capacity per tier. Display data are `DisplayPackage`s; camera, culling and selection run locally. Direct manipulation writes Ingot through ranked edit plans. Fields paint on the true geometry with stated error. Proposal review shows feature, geometry, metric and source diffs. Design, Simulate, Manufacture, Electronics (schematic and layout) and Review are presets over one workspace. A public `crucible:ui/canvas2d` world lets any package submit retained 2D primitive buffers (lines, arcs, polygons, text, with layer and net ids) that the renderer draws and hit-tests; tools that compute per pointer move (the router, placement drag with live rule checks) run in the engine process on an interactive edit lane and stream geometry each frame through `api`.

### 7.7 Interop, ecosystem and support

- Open formats are built in Rust as Wasm components generated from their schemas (one EXPRESS code generator for every STEP application protocol and IFC). Licensed translators for proprietary formats run as external tools outside evaluation, and their output enters builds only as External inputs, so anyone can rebuild without the licence.
- Imports are Ingot expressions over Assets; there is no imported state outside the program. Crucible never replays proprietary feature history; it imports geometry, structure, semantic PMI and metadata, and offers design-intent reconstruction as a reviewed Proposal.
- Registry: namespaces owned by verified publishers; trusted publishing only; Sigstore signatures and SLSA provenance; std and translators reproducibly built; yank but never delete; output-changing releases flagged; a legal-removal path for patent and copyright notices with counter-notice and transparency-log entries.
- Licensing: code under Apache-2.0 WITH LLVM-exception; documentation CC-BY-4.0; examples and templates MIT-0; contributions under the DCO; company stewardship until a fixed trigger, then a foundation. Linked dependencies may use MIT, MIT-0, Apache-2.0, BSD, 0BSD, ISC, Zlib, BSL-1.0, CC0-1.0, Unicode-3.0 or the OpenSSL licence (the pre-3.0 dual licence). Bundled data and fonts may use OFL-1.1, CDLA-Permissive-2.0, CC-BY-4.0 and Unicode-3.0, each shipped with its notices. Operating-system libraries (glibc, the C++ runtime under the GCC Runtime Library Exception, platform frameworks) are linked dynamically and never shipped. Any other licence needs an RFC (ECO). MPL-2.0 files may be linked; every distribution (native, Wasm, browser bundle, container) ships MPL notices and a source offer for each MPL file, and modifications are published under MPL-2.0. Apart from those operating-system libraries, LGPL, GPL and AGPL code is never linked; it runs only as an external tool, an External Op or a test oracle, and distributed GPL or AGPL container images ship with their corresponding-source offer.
- Releases ride a 6-week train (nightly, beta, stable) with one LTS release per year supported for 24 months, aligned with Wasmtime's LTS window. Every stable release line has a support period of at least five years: security fixes reach it as separate patch releases, by backport or by a free upgrade that raises no OS or hardware minimum. Regulated extended support: one LTS line every two years is supported for 10 years, with security backports by the steward or retired engines run in sandboxed processes. A regulated cloud deployment mode serves defence and ITAR customers (US-only regions, US-person operations staff for ITAR tenants, controls mapped to NIST SP 800-171 with evidence of FedRAMP Moderate equivalence, support for DFARS 252.204-7012 incident reporting, image retention and forensic access). Medical customers receive a Computer Software Assurance package (intended use and risk tier per capability, vendor oracle evidence, release impact notes, a supplier quality agreement template and audit rights).

### 7.8 Trust and the shared cache

- Two worker pools. Untrusted-evaluation workers run Proposal CI from agent and external branches and every External Op, in single-use microVMs (Firecracker- or gVisor-class); they hold no attestation key and write only to a per-Proposal namespace. Trusted builders evaluate only merged Changes of protected branches.
- A separate attestation service holds the signing keys and signs (`OpKey`, `ObjectId`) only for jobs dispatched to trusted builders, bound to workload identity; the host, not the guest, computes output `ObjectId`s.
- Release gates and every `SignOff` check accept a cached result only when two independent trusted builders produced the same `ObjectId` (different hosts; for `Portable` operations, different ISAs); otherwise they recompute. Two-builder agreement protects against faults, not against a deterministic exploit.
- Trusted builders run every Wasm component and package from outside std, `crucible::` and the first-party translators only in single-use microVMs, with the host computing output `ObjectId`s; an OS-process sandbox is never a trust boundary for attestation. A node whose dependency closure contains third-party code is attested only into its tenant's domain, by builders whose hosts serve that tenant alone.
- A release gate or `SignOff` check accepts an External Op result when two single-use runs on different untrusted-evaluation hosts produce the same output `ObjectId`. Each host computes it outside the microVM and records it in an execution receipt signed by a receipt key that never signs shared-cache attestations. A nondeterministic External Op yields `Unverified` results, which meet a gate only under a policy allowance.
- Every External Op host, translator host, spawned tool process and stdio MCP server runs with network egress denied. A manifest may declare named egress endpoints (a licence server, an MCP server's API host), which an administrator grants per organization and the sandbox enforces by address. A host with any egress grant receives only inputs whose confidentiality label is at most `internal` with no `controls`, unless a two-person grant names that host and label.
- Where one host serves both pools (the phase 1 single-node team server), the signing keys live in a TPM, HSM or OS keystore whose signing service accepts requests only from the trusted-builder process, External Ops are not offered, and every release records "single host" in its provenance.
- Only the operator's registry builders write the global public cache domain, with 2-of-n agreement, and it holds only results whose dependency closure is first-party; those builders never run third-party code, so publish-time test vectors and acceptance checks of third-party packages run on untrusted-evaluation workers. The hermetic builder for first-party packages never builds third-party ones. The default client trust policy is "own organization plus operator public signers".
- Spot re-execution of shared-cache hits is weighted by downstream fan-out and is 100% for nodes that feed released checks.
- Encryption domains are keyed by tenant and canonical confidentiality label; deduplication never crosses them.
- Signatures are detached records about content: the identity of a Change, tag, release record or Evidence record hashes its unsigned content, so adding a signature or a timestamp never changes an identity. Every signature record carries an algorithm id. From phase 2, release tags, TUF root and targets metadata, transparency-log checkpoints and provenance are dual-signed with a classical signature plus ML-DSA-87. LMS (as HSS) serves only the steward's software-release signing, with each tree generated in its own HSM at a key ceremony, key replication disabled and the remaining signature count monitored.

## 8. State-of-the-art mandate

- For every major component, identify the best published method as of October 2026 (a paper, a standard or a leading implementation), cite it, and state Crucible's choice. The default is to adopt or beat the state of the art. Any deviation needs a stated reason: license, robustness, determinism, portability or maturity.
- Name the leading implementation to beat, the benchmark or dataset to measure on, and a performance or accuracy target, labelled as a target.
- Prefer methods that are robust, deterministic, parallel and SIMD- or GPU-friendly, and methods with provable guarantees where they exist.
- Every tab includes a `## State of the art` section with a table: Component · Best published method · Leading implementation to beat · Crucible's choice · How we measure.

## 9. Platforms

- **Tier 1** (full product, identical features, every golden product passes): Windows 11 on x86-64 and ARM64; macOS on Apple silicon (current release and two prior); Linux on x86-64 and ARM64 (glibc 2.34 or newer, Wayland and X11); desktop browsers (Chrome and Edge, Safari, Firefox) through Wasm with WebGPU and a WebGL2 fallback.
- **Tier 1 preview.** A Tier 1 target may be a preview target for at most one phase: it runs the same build with identical features, passes the determinism suite and the golden-product checks in automation (real Safari through safaridriver, not a WebKit build), and ships through the beta channel. By the next gate it completes installers, the updater, a published Accessibility Conformance Report with an external audit, and GPU-driver qualification (PLT's GPU oracles pass on every lab device listed for the target). Phase 1 general availability: Windows 11 x86-64, macOS, Linux x86-64, Chrome and Edge. Tier 1 preview in phase 1, general availability at the phase 2 gate: Windows 11 ARM64, Linux ARM64 desktop (a Snapdragon X or ARM64 workstation joins the mid band and GPU lab), Safari, Firefox.
- **Tier 2** (viewing, review and light editing; CI on every release): iPadOS and Android tablets, ChromeOS through the browser; phones as viewers; Crucible's phone clients offer no approval (7.6).
- **Tier 3** (community-supported): FreeBSD and other Unix systems. A Tier 3 target joins the canonical class only after it passes the determinism suite.
- **Servers**: Linux containers on x86-64 and ARM64 for team servers and cloud workers; optional GPU acceleration.
- **Parity** means identical features and identical canonical results on every Tier 1 platform, whether computed locally or through remote evaluation on a team server or cloud worker. Capacity and speed may differ and are declared per platform and GPU tier. External Ops run on hosts that support them and are reached remotely from every client; air-gapped installs need a local Linux worker.
- Core crates are OS-agnostic; OS services sit behind `platform-api` traits implemented once in `apps/platform`. The engine runs as a separate process on desktop, a worker in the browser, threads on Android tablets, a worker on iPadOS, or a remote server, and the UI always talks to it through `api`. Native x86-64 builds target x86-64-v2 with runtime dispatch to v3 and v4; ARM64 targets ARMv8 with NEON; SVE dispatch waits until Rust stabilizes scalable vectors. Accessibility goes through each OS's native accessibility API (AccessKit), plus a DOM mirror on the web.
- **Browser memory.** WebAssembly memory never shrinks, so the engine worker keeps a fixed linear-memory cap, set per browser engine from the phase 0 kill-threshold measurements on the low-band machine (8 GiB). Evaluations whose estimated peak exceeds 512 MiB run in a disposable heavy worker that writes results to the OPFS CAS and terminates; above the measured kill thresholds, heavy evaluations go remote. The engine worker recycles too: above a memory threshold, once the session is idle, it hands over to a fresh engine worker that replays the journal. PLT owns one browser memory table with these figures.
- Every tab includes a `## Platform notes` section.

## 10. Coherence and taste

- **Fewest concepts.** Use the core types. Never invent a parallel abstraction.
- **One name per concept.** Follow section 2 exactly, including the "never call it" column.
- **Common things simple, advanced things possible.** Sensible defaults for the usual case; power revealed progressively.
- **Explicit over magic.** No silent fallbacks. Every approximation states its error.
- **Composition over special cases.** One general mechanism (Fields driving geometry, queries over provenance, checks everywhere, Approvals over digests, labels through every derivation) beats many one-off features.
- **Errors are guidance.** Every failure is typed, explains why, and suggests a fix.
- **One voice.** Present tense, precise, calm. No hype words ("revolutionary", "seamless", "cutting-edge", "world-class", "powerful", "robust" as praise), no exclamation marks.
- **Say it once.** Each fact lives in the tab that owns it; other tabs state the consequence in one line and point to the owner.
- **One skeleton.** Every tab follows section 11.
- **Code style.** Ingot: `snake_case` for functions and features, `PascalCase` for types, units on every dimensional literal. Rust: the Rust API Guidelines.

## 11. Research and writing rules

Research:

- Cite only pages you actually opened with WebFetch; search snippets are not sources. Prefer primary sources. Mark anything unverified with [unverified]. Never invent version numbers, dates, statistics or customer names. Web search quota may be exhausted; use WebFetch on known primary URLs.

Every tab follows this skeleton, in this order:

1. A lead of one to three sentences under the tab title, stating the design in one breath (no heading).
2. Design sections (`##`, with `###` subsections). Each design section ends with one capability table: Capability · Contract · Failure · Oracle id · Phase. There are no separate catalog sections.
3. `## State of the art`
4. `## Platform notes`
5. `## Interfaces with other subsystems`
6. `## Oracles` (each oracle once: id · verifies · pass criterion; no phase column)
7. `## Phasing` (gate contributions only, consistent with section 13)
8. `## Open questions`
9. `## Contract change requests` ("None" if none)
10. `## Sources`

Style:

- Tables for items compared on several attributes; numbered lists for sequences; code blocks for Ingot and Rust. Sentences under 25 words where possible; paragraphs of at most three sentences; specifics over adjectives; no emoji.
- Decisions inline: `**Decision D-<TAB>-<n>:** <decision>. *Why:* <rationale>. *Rejected:* <alternatives and why>.` Tab codes: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT. Decision numbers are stable: never renumber; a reversed decision keeps its number, states the new decision and ends with "(revised in round 2)"; new decisions take the next free number.
- At most two diagrams per tab, marked `[[DIAGRAM: …]]` in drafts.
- Length after revision: 12,000 to 18,000 words per tab excluding Sources (Ingot and Anvil up to 20,000). Cut repetition, restated rationale, content another tab owns and prose that a table already says. Never cut a capability, decision, oracle or source. Targets are labelled as targets.

## 12. Crate map

Each crate depends only on crates in its own or earlier rows, and apps talk to the engine only through `api`; PLT's CI fails any other dependency.

| Layer | Crates (all under `core/` unless noted) | Owner |
| --- | --- | --- |
| Platform | `platform-api`, `detmath`, `simd`, `runtime`, `gpu`, `wasm-host`, `linalg` (canonical linear algebra) | PLT (`linalg` with FLX) |
| Contracts | `base` (shared value types from section 5; identity and handle types such as `GeometryId`, `EntityId`, `BodyHandle`, `InstancePath` and `PortId`; the `Classify` trait that Anvil implements for `field`'s `Sampler`; and the operation contract `OpImpl`, `OpCx`, `Differentiable`, `DeterminismGrade`); `cas` | KLN, with every owner of a type |
| Engine core | `kernels` (shared kernel IR and back ends); `field` (`Field`, domains, representations, `Sampler`); `kiln` | FLX, KLN |
| Geometry | `anvil-geom`, `anvil-topo`, `anvil-planar`, `anvil-mesh`, `anvil-implicit`, `anvil-ops`; `mech-model` (`Part`, `Assembly`, `Instance`, `Transform`, `CoordSys`) | ANV; MEC for `mech-model` |
| Physics | `flux-forms`, `flux-solve`, `flux-couple`, `flux-opt` | FLX |
| Language | `ingot-syntax`, `ingot-types`, `ingot-ir`, `ingot-codegen`, `ingot-bindgen` with `ingot-macros`, `ingot-service` | ING |
| Product services | `repo` | KLN |
| Surface | `api` | AGT |
| Outside `core/` | `bridges/` (optional FFI: PETSc, hypre, GPU vendor specifics); `io/` (translators as Wasm components); `std/` (Ingot packages and first-party Wasm components); `wit/` (`crucible:` packages); `apps/` (`platform`, `ui-toolkit`, `renderer`, `desktop`, `web`, `mobile`, `server`, `cli`, `ci-runner`, `registry`, `attestation`, `headless-render`, `mcp`, `crew` and `model-gateway` (AGT), `machine-gateway` (MFG, packaged by PLT for Linux x86-64 and ARM64 and Windows 11 x86-64), `relay` and `rig-runner` (KLN), `tool-runner` (ECO, PLT)); `sdk/` (`rust`, published as `crucible-sdk`, `python`, `typescript`, `c`; ECO); `oracles/` (protected) | per tab |

`inspect.render` dispatches to `apps/headless-render`, a service that links `apps/renderer`; `api` depends on neither. `unsafe` is allowed only in `simd`, `gpu`, `wasm-host`, the code-loading parts of `kernels`, `bridges/` and `apps/platform`. Everything else is `forbid(unsafe_code)`. Until every `detmath` function's Rust port passes the CORE-MATH oracle, `detmath` may depend on `bridges/core-math`, which wraps CORE-MATH's C build in safe functions. PLT renames its pool priority to `PoolLane` and its file durability to `WriteDurability`, so `PriorityClass` and Kiln's durability keep their meanings.

## 13. Roadmap, program plan, performance targets and shared phases

### 13.1 Phases and golden products

| Phase | Theme | Gate |
| --- | --- | --- |
| 0 | Foundations | Determinism suite green on the representative set and nightly on every Tier 1 target; unit errors fail to compile; names cleared (Crucible) or replaced (Flux) before any operation version or WIT package freezes, and the SDK names reserved on crates.io, PyPI, npm, Maven Central and NuGet; counsel's written opinion on claims 1, 6, 11 and 16 of US 12,229,885 B1 and its continuations delivered, and a freedom-to-operate search of the phase 1 code paths of chains A and B (SSI, Booleans, blends, tessellation, implicit lattice meshing) completed; GP2's alloy, machine, print bureau, build-preparation software and accepted 3MF extensions fixed and recorded in this section; kernel IR v0 frozen (7.5) |
| 1 | Wedge: code-CAD and 3D printing | GP1 machined bracket: designed, toleranced, simulated and released in Crucible; made by a reference shop from Crucible's STEP AP242 with semantic PMI and drawing, using the shop's own CAM; measured by external metrology against Crucible's tolerances; proof-loaded. GP2 topology-optimized lattice bracket in metal laser powder bed fusion: optimized and verified in Crucible; built from Crucible's 3MF with the bureau's build-preparation software; measured externally; proof-loaded |
| 2 | Mechanical depth | GP3 gearbox, including machined parts cut from Crucible-generated programs; GP4 welded frame with sheet-metal guards, including measured weld distortion; one material-extrusion part sliced by Crucible and sent through `send_print_job` to an open-firmware printer (Klipper or RepRapFirmware) |
| 3 | Product breadth | GP5 molded enclosure with its PCB, including measured warpage and drop response; the board fabricated and assembled from Crucible outputs alone |
| 4 | Full multiphysics | GP6 drone, validated against flight, dynamometer and thermal test data |
| 5 | Scale | GP7 MEMS accelerometer; GP8 bolted steel platform round-tripped through IFC 4.3 with a structural check; GP9 crash box |
| 6 | Aerospace and electrification | GP10 composite wing box; GP11 CubeSat; GP12 EV battery sub-pack with BMS, harness and charger |
| 7 | Marine, buildings, medical and soft goods | GP13 workboat hull; GP14 timber pavilion (building product, IFC export); GP15 bone plate (ASME V&V 40 credibility); GP16 sewn pack (soft goods) |

Every physical gate states its replicate count (at least three articles, or a GUM uncertainty budget for a single article), measures as-built geometry and material coupons from the same lot, and keeps validation data out of calibration. Solid-mechanics validation follows ASME V&V 10; the validation metric follows V&V 20 (comparison error E = S − D, validation uncertainty u_val = √(u_num² + u_input² + u_D²), model-form bound |E| + k·u_val at validation points), and extrapolation inflation is a declared function of normalized distance to the nearest validation point. Each validation plan places sensors on the quantities the gate's checks decide, so its validated response-quantity classes (section 5) cover them. GP1 and GP2 each add a proof-load test on every article, with strain gauges in each checked region and a load–displacement record. The phase 1 gate release reproduces the exported STEP AP242 and 3MF files of the tagged run build, bit for bit (equal `ObjectId`s), or shows equal `GeometryId`s and definitional attributes with a reviewed diff of the rest; otherwise the physical run repeats. "Released in Crucible" is satisfied through `api` and the CLI, so a UI slip moves UIX's own target and not the gate. Golden products 7 to 16 are proposals, each a separately funded program started only with a physical test partner and an approved plan.

**Scope.** In: products made of parts, assemblies, boards, cables and software items, from MEMS to ships; building products and structures (prefabricated, steel, timber), exchanged with BIM tools through IFC 4.3; MEMS layout and chip-package design through GDSII and OASIS. Out: whole-building authoring (spaces, zones, whole-building energy); integrated-circuit logic layout; film and animation; classified information under any national security classification system, for which no deployment mode is accredited.

### 13.2 Program plan

Crucible is built by agents. One human, the founder, directs the program; Claude orchestrates agent work against the oracles; outside firms make, measure and advise where the physical or legal world requires a person. Phases end at their gates, never on a date, and no plan figure counts people or engineer-years.

**Roles.**

- **Founder.** Approves each phase's scope and budget at the previous gate, signs each golden product's pass/fail criteria before builders start on it, approves every Act (7.6) and every waiver, and decides anything that changes money or scope.
- **Orchestrator.** Claude plans the work, opens work items, runs reviews and rulings, and keeps this contract and the tabs current.
- **Agent roles.** An oracle role writes and locks a phase's oracles before any builder works on the capabilities they verify; builders never write or edit `oracles/`. A verifier role, independent of both, checks every oracle against its capability row and an independent source, and attacks every builder Proposal (7.6). An adversarial review of the spec runs before each gate.
- **Outside firms.** Retained counsel for freedom-to-operate and trademark work. Signed phase 0 agreements with a reference machine shop (including time on each controller family's physical controls in program-test mode), a metrology lab, a metal powder bed fusion bureau and a proof-load test lab. The bureau agreement includes a file-acceptance test of its build-preparation software on three files: a 3MF with the Beam Lattice extension, a 3MF of triangles at a stated chordal error, and a sliced build where the software takes one.

**Budget.** Each phase carries one budget, approved by the founder at the previous gate: agent compute, cloud CI, rented GPU and device-farm time, physical golden-product runs with replicates and one re-run, metrology, proof loads and counsel. A scope addition to an open phase needs the same approval as a gate change.

**Phase 1 scope.** Deferred to phase 2 or 1.x release trains, with contracts and oracles unchanged: the Ingot code generator, Perceus and the state-machine transform (the interpreter executes Ingot); cluster-DAG streaming, the visibility buffer, compute rasterization, k-buffer transparency, the variant grid, presence and follow mode (one forward renderer on every tier); cloud SaaS, live CRDT documents, encryption domains, transparency logs and the hardware runner (a single-node team server with branches, merge, Proposals, Cedar policies and a signed append-only audit log); CAM, posts, stock simulation, slicing and nesting (phase 1 keeps DfAM checks, 3MF production output and cost); the public registry and trusted publishing (a signed first-party package index); Bayesian exploration, the hosted crew, quarantined extraction and the TypeScript SDK (phase 1 ships `api` over MCP, Rust and Python SDKs, Propose with CI report, risk classes and three roles: detail designer, simulation engineer and verifier); guaranteed estimators on cut cells, GPU sign-off paths and CUDA back ends; SubD, certified SSI for general NURBS–NURBS pairs beyond what GP1 and the licence-filtered prismatic ABC subset need, GPU sampling for SSI (7.1) and free-form offsets; the browser sandbox for third-party Wasm components (browsers evaluate them remotely, 7.4); inherent-strain distortion prediction (13.4); the shifted boundary method and, unless the phase 0 measurement needs it, WGSL elasticity (7.1, 7.5); restricted-party screening of recipients inside the organization; TUF delta updates (full signed packages suffice), Flatpak, AppImage, reproducible builds beyond Linux and wasm32, and telemetry (phase 1 ships MSIX, a notarized DMG, deb and rpm). Electronics before the phase 1 gate is limited to a circuit-simulation research track. Phase 1 supports a desktop install without a team server: it designs, simulates, evaluates and exports locally (audited local writes, 7.6), while Proposals, releases and every Act need a team server.

**Build program.** PLT owns how Crucible itself is built against its oracles.

1. **Oracle first.** A work item opens only when its oracle ids exist in `oracles/` as executable checks written by the oracle role and passed by the verifier. Chain A and B oracles exist before Chain A and B work starts, and every phase 1 oracle exists before the physical dry run; each gate reports oracle coverage per crate.
2. **Runner classes.** Every oracle declares one runner class: `cpu-ci`, `browser-ci`, `gpu-lab`, `device-farm`, `physical` or `founder`. Agents run every class except `physical` (outside firms) and `founder` (sign-offs); `gpu-lab` and `device-farm` run on rented hardware.
3. **Corpora.** Agent-built corpora and reference data enter `oracles/` only through a Proposal the verifier passes, and must agree with an independent source (MPFR, Open CASCADE, lib3mf, MFEM or libCEED, CAx-IF data).
4. **Work items.** A work item is `{ crate, capability row, oracle ids, held-out split, budget }`, run through AGT's Plan and Proposal machinery against Crucible's own repository, with the verifier role. Until that machinery ships in phase 2, phases 0 and 1 run the same `WorkItem` record over Git, with the same oracle and verifier rules.

**Critical path for phase 1.** Each chain runs in the order shown. Chain A: exact predicates → certified SSI on GP1's surface set → Booleans → fillets and shells → GP1 features and drawing → STEP AP242 → shop machining → metrology and proof load. Chain B: kernel IR → CPU back ends → immersed elasticity with DWR → topology optimization and homogenization → implicit lattice → strut calibration coupons printed and measured → 3MF → build → measurement and proof load. Chain C (interface): toolkit decision → toolkit core, forward renderer and picking → feature dialogs, sketching, drag preview, sections and Field colour → drawing editor and review diffs → keyboard-complete workflows with accessibility oracles green. Chain D (release): single-node team server with Cedar and the audit log → microVM Proposal CI → the approval page with WebAuthn and the release and export Acts → used end to end in the physical dry run.

**Milestones through phase 1, in order.**

1. `detmath` core functions; combinators; CAS and Kiln core; Ingot parser, types and interpreter; kernel IR v0, additive-only; predicates, analytic geometry, topology and `EntityId`; CI on every Tier 1 CPU target.
2. Analytic SSI and Booleans; tessellation and `DisplayPackage`; CPU kernel back ends; H¹ elements, CG and manufactured-solution tests; toolkit core and forward renderer; counsel's freedom-to-operate opinion received; kernel IR v0 frozen once three consumers compile against it; the phase 0 gate, judged per crate on the corpus that exists.
3. Fillets, chamfers, shells, holes, patterns, sketches; drawings and GD&T; immersed elasticity, DWR, p-multigrid; topology optimization, homogenization, implicit lattices; strut calibration coupons; STEP AP242 and 3MF writers; team server; Propose and review; the approval page and release Acts.
4. Physical dry run of both gates with interim outputs.
5. Hardening, keyboard-complete workflows, accessibility, Tier 1 preview targets.
6. Run build tagged; the GP1 and GP2 articles are made from its exports.
7. GP1 and GP2 physical runs with proof loads, with one re-run budgeted.
8. The phase 1 gate.

### 13.3 Performance targets

Owned by PLT. The reference laptop is fixed: Intel Core Ultra 7 258V (8 cores, 8 threads, AVX2, Arc 140V GPU), 32 GB, Windows 11 and Ubuntu LTS, measured at 1920×1080 render resolution. Because the processor's sustained throughput depends on chassis and power, PLT names the exact laptop model (chassis, panel and its refresh rate, firmware version) at the phase 0 gate and fixes the measurement conditions: AC power, one named OS power mode, logged package power, thermal soak, ambient temperature, pinned OS builds, kernel and GPU drivers, and a calibration workload that discards a session when it drifts. Each row names its benchmark file in `oracles/plt/`, cache state, render resolution and percentile, and has held-out variants (principle 6). Other operating systems' mid machines land within 1.5× of each row. A row blocks beta promotion on the reference laptop from the phase in its last column; before that phase it is a measured target. All figures are targets.

| Row | Native | Browser | Phase |
| --- | --- | --- | --- |
| Cold start / warm start | 1.5 s / 0.6 s | first visit 8 s at 50 Mbit/s, with at most 25 MiB of brotli-compressed initial Wasm; warm 2.5 s | 1 |
| Selection highlight | 16 ms | 33 ms with WebGPU (asynchronous readback), or a CPU ray cast | 1 |
| Orbit | 60 fps at 5M visible triangles at up to 2.1 MP render resolution (upsampled during motion; edges, overlays and text at native resolution; still frames accumulate at native resolution) | WebGPU 30 fps at 5M or 60 fps at 2M visible triangles; WebGL2 30 fps at 2M visible triangles and at most 1,000 distinct Parts | 1 |
| Orbit of implicit Bodies | 30 fps at up to 2.1 MP render resolution | 30 fps with WebGPU | 1 |
| X-ray views | 30 fps | | 2 |
| Scene capacity at 60 fps | G1 100,000 Instances; 1,000,000 on the high band from phase 4 (adapters reporting `compute_raster`; others declare a measured capacity) | G2 20,000 Instances; G3 10,000 Instances of at most 1,000 distinct Parts | 2 |
| Drag preview | The dragged feature plus as many dependents as Kiln's cost estimate fits in 80 ms (at least the next 10 when cheap) within 100 ms; later dependents show as `Proxy` where the change is affine on them, otherwise `Stale` | same rule, 200 ms, measured on the threaded build | 1 |
| Rebuild after an early edit | `SignOff`: 2 s on a named GP1-class benchmark of prismatic features. `Interactive`: p90 ≤ 10 s on a 200-feature corpus from the licence-filtered ABC subset and Crucible's procedural generator | 3× native | 1 |
| `SignOff` recertification after an early edit | p90 ≤ 30 s on the same 200-feature corpus | 3× native | 1 |
| Interactive simulation update | 1 s for linear static elasticity up to 100,000 DOFs at p = 2, warm-started, on G1 | 2 s with WebGPU; 6 s CPU-only; remote above that | 1 |
| Open a 1,000-part assembly from warm cache | 10 s, with a coarse view in 2 s | 20 s | 2 |
| Input to photon, p99 | 50 ms at 60 Hz; 33 ms at 120 Hz, measured on the macOS mid machine if the reference laptop's panel is 60 Hz | same | 1 |
| Memory | under 1 GiB with GP1 open; idle 300 MiB with the GPU device created lazily | per PLT's browser memory table | 1 |
| Installed size | 400 MiB | | 1 |
| Flux CPU throughput (CEED bake-off), `CpuIsa { X86_64V3 }` with FMA, against MFEM and libCEED built for the same ISA | BP3 and BP5 at p ≥ 3: at least 50% of MFEM or libCEED; memory-bound cases (BP1, BP2, p ≤ 2): at least 80% | | 1 |
| Flux CPU throughput (CEED bake-off), canonical class | BP3 and BP5 at p ≥ 3: at least 25% of MFEM or libCEED in `CpuIsa`; memory-bound cases: at least 70% | | 1 |

The ABC subset holds only documents for which the Onshape API shows a Free Plan owner, a creation date on or after 7 August 2018 and no LICENSE tab; ECO keeps that evidence per model, and models without it are not copied.

### 13.4 Shared phases

A capability that several tabs phase has one phase, set here. The owner's capability table specifies it: contract, failure and oracle. Every other tab states the phase in one line and cites this table. A capability lands in the phase of the first gate that needs it; one that no gate needs takes the latest phase any tab proposed. A capability is phased no later than anything that depends on it, so a row or a gate never precedes its prerequisites, and a capability row that names another tab's capability carries a phase no earlier than the owner's row; the spec check enforces this across tabs. A tab that needs a different phase files a change request.

| Capability | Phase | First gate that needs it | Owner | Also phased in |
| --- | --- | --- | --- | --- |
| Modal analysis and linear buckling: Lanczos and LOBPCG eigen-solvers | 1 | GP2 strut buckling | FLX | COV |
| As-built lattice strut calibration for metal powder bed fusion: strut diameter, waviness and strut-scale Materials | 1 | GP2 strut checks | MFG | COV |
| Additive distortion by inherent strain: layer activation of part and supports, baseplate cut, support removal and stress relief | 2 | None; MFG's metal powder bed fusion compensation | FLX | COV, MFG |
| Weld distortion at structure scale, by inherent strain | 2 | GP4 measured weld distortion | MFG | COV, FLX |
| Gear, bearing and shaft ratings (ISO 6336, ISO 281, DIN 743 or the FKM guideline) and loaded tooth contact analysis | 2 | GP3 | COV | MEC |
| Fitted FEM on conforming curved tetrahedra, with mortar contact | 2 | GP3 validation of loaded tooth contact | FLX | ANV |
| Conjugate heat transfer, laminar and natural convection | 3 | GP5 | FLX | COV, ELX |
| Injection moulding: level-set fill front, pack, cool and warpage | 3 | GP5 measured warpage | MFG | COV, FLX |
| Short-fibre orientation transport and its effect on warpage | 3 | GP5 measured warpage | MFG | COV, FLX |
| Explicit dynamics for drop | 3 | GP5 drop response | FLX | COV |
| Stability lobes and chatter prediction | 3 | None; GP3's programs use tool-library cutting data | MFG | COV |
| Conjugate heat transfer, turbulent (RANS) | 4 | GP6 thermal test data | FLX | COV, ELX |
| Electro-thermal coupling: Joule heating with temperature-dependent resistivity | 4 | GP6 thermal test data | FLX | ELX |
| FMU export and SSP | 4 | GP6 | FLX | ELX |
| Battery cells: equivalent-circuit and SPMe models | 4 | GP6 pack voltage | ELX | COV, FLX |
| Composite laminates: zone-based plies, kinematic draping and laminate analysis | 4 | GP6 | MEC | ANV, COV |
| Weld simulation at joint scale, transient | 4 | None | MFG | COV |
| Battery cells: swelling and stack pressure | 4 | None | ELX | COV, FLX |
| Battery cells: Doyle–Fuller–Newman (P2D) | 5 | None | FLX | COV, ELX |
| Free-surface and multiphase flow beyond mould filling | 5 | None | COV | FLX |
| Explicit dynamics with erosion for crash | 5 | GP9 | FLX | COV |
| Sheet forming simulation and springback compensation | 5 | None | MFG | COV |
| Constitutive draping and composite cure simulation | 5 | None | COV | MFG |
| Battery abuse mechanics: crush, penetration and crash screening | 6 | GP12 | ELX | COV, FLX |
| Casting simulation: mould filling, solidification and porosity for sand, high-pressure die and investment casting | 6 | None | MFG | COV |

Three neighbours keep their own tab's phase: board thermal from part power Fields (ELX, 3), press-brake bend allowances (MFG and COV, 2) and distortion compensation for metal powder bed fusion (MFG, 2).

## 14. Ruling log, round 1 (contract change requests from the first drafts)

| CCR | Ruling |
| --- | --- |
| ING-1 three-valued checks; FLX-3 | Accepted; `Undecided`. COV's `Indeterminate` becomes `Undecided`. Extended in round 2 (section 5 `CheckOutcome`). |
| ING-2 `Approx<T>` | Accepted; carries an `ErrorBudget` (section 5). |
| ING-3 `Tol<T>` semantics; MEC-3 | Accepted (section 5). |
| ING-4 syntax reference | Accepted and revised in round 2 (section 6). |
| ING-5 crate list | Accepted (section 12). |
| ING-6 language behavior version | Accepted (section 7.2). |
| ING-7 angle base dimension, torque | Modified in round 2: strong angular system (section 5). |
| ING-8 one `Severity` | Accepted. |
| ING-9 MEC `constraint` and `interface` keywords | Accepted: `Expr<T>` functions and `#[interface]` records. |
| ING-10 `OpSite` in keys; ANV-5 | Modified: two-stage caching with `GeometryId` (section 7.2). |
| ANV-1 `ErrorBound` location | Modified: in `base`. |
| ANV-2 `EntityId` formula | Accepted (section 5), with text-derived `OpSite`. |
| ANV-3 canonical operation names | Accepted: Anvil's catalog is canonical. |
| ANV-4 `Query` notes | Accepted and extended (section 5). |
| ANV-6 predicates for curved geometry | Accepted (section 7.1). |
| FLX-1 `ErrorBound` | Accepted and revised (section 5). |
| FLX-2 Field axes; COV-8; MEC-4; MFG-1; ELX-1 | Modified: product domains, `Field<(Body, Time), V>`. `Field<D, V, A>` becomes `Field<(D, A…), V>`; `TimeSpan`, `FreqSpan`, `Sweep`, `Interval<Q>` and `StateDomain` become quantity-type domains. |
| FLX-4 platform classes; PLT-1 | Modified: PLT's enum (section 7.3). |
| FLX-5 Kiln derivative support | Accepted; KLN adds a Derivatives section. |
| FLX-6 crate list | Modified: `field` and `kernels` below Anvil; `bridges/` outside core. |
| FLX-7 statistical agreement for chaotic problems | Accepted (principle 4), extended to bifurcations. |
| COV-1 `ErrorBudget` | Accepted (section 5). |
| COV-2 external tools; ELX-2; MFG-2; ECO-1 | Modified: External Op, External input and Evidence record (section 2). |
| COV-3 Flux operations for non-variational methods | Accepted (section 7.1). |
| COV-4 `Material` extension | Accepted. |
| COV-5 envelope zones and dispositions | Accepted. |
| COV-6 scope | Accepted (section 13.1). |
| COV-7 physical tests in GP4 and GP5 gates | Accepted (section 13.1). |
| KLN-1 cache key by package closure | Accepted (section 7.2). |
| KLN-2 hardware CI | Accepted (section 7.1). |
| KLN-3 "node" | Accepted (section 2). |
| KLN-4 `DeterminismGrade` | Accepted. |
| KLN-5 service BOM | Accepted. |
| MEC-1 `CoordSys`; MEC-2 `ShapeAspect`; MEC-5 role aliases | Accepted. |
| MFG-3 approval bound to content | Accepted as `Approval` over an approval subject. |
| MFG-4 `Money<C>` | Accepted. |
| ELX-3 remote parity; ELX-4 Software item; ELX-6 interop list | Accepted. |
| ELX-5 `Circuit` as a core type | Modified: `Network`, builder `network { … }`. |
| ELX-7 Wasm components may call operations | Accepted: WIT package `crucible:ops`. |
| AGT-1 to AGT-6 | Accepted (sections 2, 5, 7.6). |
| UIX-1 to UIX-4 | Accepted (sections 5, 9). |
| ECO-2, ECO-3, ECO-4, ECO-6, ECO-7 | Accepted. |
| ECO-5 name clearance | Accepted and strengthened in round 2: Flux is renamed in phase 0. |
| PLT-2 SVE; PLT-3 crates | Accepted. |
| PLT-4 instrumentation version in key | Subsumed by the determinized binary's hash. |

Round 1 conflicts resolved without a CCR: GPU code generation (one kernel IR; section 7.5); `detmath` is PLT's and the only math library; retired versions run from archived Wasm builds; one determinizer at publish and local build; `Preview`, `Interactive`, `SignOff` everywhere; no keywords for variants or requirements; `anvil::fold` for flex circuits; `anvil-planar` owned by Anvil; lockfile `ingot.lock`; std names (section 6); golden products 7 to 16 (section 13.1); no `ExecMode`; Flux owns multibody and rod models; MFG owns cost models, product LCA and passports; COV owns material environmental records; ECO owns the package registry.

## 15. Ruling log, round 2 (adversarial review)

All review findings go to the owning tabs as revision packets. The rulings below change the contract itself; every tab conforms.

| Finding | Ruling |
| --- | --- |
| R2-02, R3-01, R2-10, R3-05, R3-06 identity and names | Accepted: label invariance (7.1), `GeometryId` beside `ObjectId` (5), text-derived `OpSite` (5), two-stage keys and `OpSite` in keys of every node carrying `EntityId`s (7.2). |
| R2-12 positional iteration; R2-22 rank selectors; R2-32 merged anchors | Accepted (section 5 `OpSite` and `Query`). |
| R3-02, R5-01 labels | Accepted: label lattice (5), label as separate memo output (7.1), replication by (package, label set) (7.1), context labels and write-down (7.6). |
| R5-02 free-text endorsement | Accepted (7.6, 7.1 `repo` span provenance). |
| R5-03, R3-20 cache poisoning | Accepted (7.8). |
| R5-04 Act approvals | Accepted (7.6). |
| R4-01 remote machine starts | Accepted (2 Act, 7.6 Physical safety, 7.1 Hardware CI). |
| R4-03 net merges | Accepted: connectivity merge condition (7.1). |
| R4-04 electronics editors | Accepted: Electronics preset and `crucible:ui/canvas2d` (7.6). |
| R3-03, R3-04 failures and termination | Accepted (2 Abort, 7.1 Kiln, 7.2). |
| R1-01, R1-03, R1-08, R3-07, R3-08 error bounds and outcomes | Accepted (5 `ErrorBound`, `ErrorBudget`, `Approx`, `Truth`, `CheckOutcome`). |
| R1-04 surrogates | Accepted (7.1 Flux). |
| R1-02 thin walls and frames | Accepted (7.1 Flux). |
| R1-05, R3-09 canonical check | Accepted (section 6 example; 7.1 singular points). |
| R1-09, R1-44 WGSL semantics; R1-10 faer blocking; R1-11 defect correction; R6-17 FMA; R6-18 vector width | Accepted (7.3, 7.1, 12 `linalg`). |
| R1-13 bifurcations | Accepted (principle 4, 7.1). |
| R1-25 consistent tangents | Accepted (section 6 `local_solve`, 7.4). |
| R1-29 validation and replicates | Accepted (13.1). |
| R2-03 error propagation; R2-14 lattice faces; R2-23 planar snapping; R2-04 patent claims; R2-07 blend stages | Accepted (5 `Body`, 7.1 Anvil). |
| R3-11 key completeness | Accepted (7.2). |
| R3-15 merge rule | Accepted (7.1 `repo`). |
| R3-16 approval subjects; R3-17 evidence | Accepted (5 `ApprovalSubject`, 2 Evidence record). |
| R3-18 variants | Accepted: `#[configuration]` (section 6). |
| R3-19 derivatives in Kiln | Accepted (7.1 Kiln). |
| R3-21 cancellation | Accepted (7.4). |
| R3-22 method naming | Accepted (7.6). |
| R3-26 `crucible:ops` | Accepted (4). |
| R3-27 base types; R3-29 rotational units | Accepted (5, 12). |
| R3-36 capability tables | Accepted (11). |
| R3-46 offline rejoin | Accepted (7.1 `repo`). |
| R3-47, R6-25 Ingot executor; R6-13 iPadOS; R6-12 Wasmtime tiers | Accepted (7.4). |
| R3-51 determinizer verification; R6-20 NaN canonicalization cost | Accepted (7.4). |
| R5-19 trademarks; R5-31 patent ownership | Accepted (2, 7.1). |
| R5-20 regulated support; R5-32 licence wording | Accepted (7.7). |
| R6-01 to R6-05, R6-34 program plan | Accepted (13.2), with three phase 1 agent roles instead of two. |
| R6-06, R6-31 Tier 1 preview | Accepted (9). |
| R6-07 to R6-11 performance targets | Accepted (13.3). |
| R6-14 browser memory | Accepted (9). |
| R6-22 kernel IR scope | Accepted (7.5). |
| R6-28 determinism suite cadence | Accepted (7.3). |

## 16. Ruling log, round 2 revisions (change requests from revised tabs)

Each revised tab files its change requests under "Contract change requests". The rulings below change the contract; tabs that cite an accepted request update the citation in the consistency pass.

| Request | Ruling |
| --- | --- |
| CCR-ANV-7 fidelity of the rebuild rows | Accepted (13.3): the rebuild row states its fidelity per benchmark, and a `SignOff` recertification row is added. |
| CCR-ANV-8 `Unknown` bounds | Accepted (5 `Body`): unpropagated bounds become `NotQuantified`. |
| CCR-FLX-8 `regularization` error source | Accepted (5 `ErrorBudget`), as 7.1 already requires the regularization error of peak and pointwise goals in the budget. |
| CCR-FLX-9 one physics phase table; R1-35 | Accepted (13.4): one row per shared capability, phased by the first gate that needs it or else by the latest phase a tab proposed. R1-35's fixes hold except DFN, which goes to phase 5 rather than 4 because no gate names it; GP6 uses equivalent-circuit and SPMe cells. Five shared capabilities beyond R1-35 get rows: free-surface flow beyond moulding, electro-thermal coupling, FMU export and SSP, sheet forming and springback, and composite laminates. FLX v2 moves electro-thermal coupling and FMU export and SSP to phase 4 and DFN to phase 5 in the consistency pass. |
| CCR-ING-11 pending branches | Accepted (5 `Truth`): below the fidelity ceiling an `if` on `Undecided` is `Pending`, so branches on Flux results wait for a higher fidelity instead of failing at `Interactive`. |
| CCR-ING-12 rotation and phase | Accepted (5 `Quantity`): oscillation angular frequency is a kind of T⁻¹ and phase is dimensionless, so ω = √(k/m) and ωL type-check. |
| CCR-ING-13 `OpSite` as a frame path | Accepted (5 `OpSite`). |
| CCR-COV-9 model and evidence levels | Accepted (2): both terms enter the glossary, and "fidelity level" is never used. |
| CCR-KLN-6 evidence for inputs without geometry | Accepted (2 Evidence record). |
| CCR-KLN-7 Item | Accepted (2). |
| CCR-KLN-8 merge verdict order | Accepted (7.1 `repo`). |
| CCR-MFG-5 physical-effect Acts; CCR-AGT-8 rig tests | Accepted together (2 Act, 7.6 Physical safety): one named list of transfer Acts, plus the restricted `start_print` and `run_rig_test`. |
| CCR-MFG-6 `unattended_safe` | Accepted (7.1 Hardware CI): a signed site policy, never self-declared and never granted to machines that cut or move. |
| CCR-ELX-8 battery rows | Accepted (13.4): swelling and stack pressure in phase 4, abuse mechanics in phase 6 for GP12. |
| CCR-AGT-7 passing every check | Accepted (7.6). |
| CCR-AGT-9 owners of `Budget` and `PriorityClass` | Accepted (5): both are AGT's, in `base`. |
| CCR-UIX-5 one device rule | Accepted (7.6): no Act is approvable on a phone. |
| CCR-UIX-6 `RenderProfile` | Accepted (5, 2 Snapshot). |
| CCR-ECO-8 and CCR-PLT-5 third-party Wasm components | Accepted together (7.4): every third-party Wasm component runs out of process on every target, because the engine process holds repositories, tokens and keys. |
| CCR-ECO-9 browser runtime | Accepted (7.4): one first-party runtime, no per-component JavaScript. |
| CCR-PLT-6 browser first visit | Accepted (13.3). |
| CCR-PLT-7 signature agility | Accepted in 7.8 rather than 7.7, since it concerns trust records rather than interop. |
| CCR-PLT-8 `detmath` C build | Accepted (12), until every function's Rust port passes the CORE-MATH oracle. |

## 17. Ruling log, round 3 (second review)

The second review's findings that target the contract go to the owning tabs as round 3 packets; the rulings below change the contract itself, and every tab conforms. Two pending requests from the tabs' open questions are ruled here too. Revised means accepted with a different or smaller fix; "tab only" means the contract already states the rule and the fix is the tab's.

| Finding | Ruling |
| --- | --- |
| R7-01 calibrated bounds | Accepted (5 `ErrorBound`, `ErrorBudget`; 7.1 Flux): α joins the union bound, calibration classes declare applicability envelopes, a `SignOff` `Pass` on an `Estimated` discretization part is confirmed by one refinement, and every `Estimated` bound is reported calibrated. |
| R7-02, R8-05, R7-18 singular sets and the canonical check | R8-05 and R7-18 accepted, R7-02 revised (6, 7.1 Flux): Flux flags only incompatible conditions, contact zones only with an edge or corner, each flagged set has a default distance, and the canonical check excludes the clamp and the loaded face. The near-maximal-set rule is declined, because estimates are least reliable next to a singular set. |
| R7-03 local slenderness | Accepted (7.1 Flux): distributed loads, body forces and inertia do not shorten L_local. |
| R7-17 immersed treatment | Accepted (7.1 Flux): aggregated CutFEM at `Interactive` and `SignOff`; the shifted boundary method serves at most `Preview`. |
| R7-24 surrogate bounds | Revised (7.1 Flux): a per-prediction bound counts only in the check's norm. |
| R7-31 bifurcations | Accepted (7.1 Flux): detection from phase 2; phase 1 Newton accepts only convex forms. |
| R7-10, R7-11 model form | Accepted (5 `ErrorBudget`, 13.1): one producer per error source, validated bounds transfer only to validated response-quantity classes, and gates place sensors on checked quantities. |
| R7-04, R7-06, R7-07, R12-11, R10-23 GP2 and phase 1 validation | Accepted, R7-06 revised (13.1, 13.2, 13.4): GP2 is metal laser powder bed fusion with its details fixed at the phase 0 gate; GP1 and GP2 add strain-gauged proof loads; as-built strut calibration is phase 1; inherent strain moves to phase 2; the bureau agreement adds a file-acceptance test. |
| R7-08, R9-32 phase prerequisites | Accepted, R7-08 revised (13.4): nothing is phased before its prerequisites or before the owner's row it names; no "Needs" column; SPMe adds FLX. |
| R7-19 gear ratings | Accepted (13.4): ratings and loaded tooth contact in phase 2, with mortar contact as their validation rung. |
| R7-27 phase 1 physics | Accepted (7.1, 7.5, 13.2): one immersed treatment, inherent strain to phase 2, WGSL elasticity only if the phase 0 measurement needs it. |
| R7-39, R12-23 CEED rows | R7-39 accepted, R12-23 revised (13.3): one `CpuIsa` row and one canonical row at 25% and 70%. |
| R8-01, R9-01, R11-17, R9-12 definitions and approval subjects | Accepted, R9-12 revised (5): definitional attributes, `ItemDefinition` per Item kind, an Assembly `GeometryId`, and `act.commit` recomputes the subject. |
| R8-02, R8-11 queries | R8-11 accepted, R8-02 revised (5 `Query`): `NearTie` from resolve, sampled stability analysis for `RankSwap`, and extent use fails on merges, partial deletions, `Ordinal` ids and near ties unless accepted. |
| R8-03, R8-41, R8-40 bodies and names | Accepted (5 `Body`, `EntityId`): tangent and normal propagation, the SubD exception, and the topology-preserving wording. |
| R8-04 `Interactive` decisions | Accepted (7.1 Anvil): filtered decisions at every fidelity. |
| R8-06 edge roles | Accepted (6): the canonical example selects `end(outline.top)`. |
| R8-08, R9-17 statistics and names | Revised (7.1 label invariance): the order of statistical inputs is name-free; ING owns the rule. |
| R8-12 forwarded tolerances | Accepted (5 `Tol<T>`). |
| R8-19 two-stage failures | Accepted (7.2). |
| R8-20 Instance sets | Accepted (2 Instance, 6). |
| R8-49, R12-10 freedom to operate | Accepted (7.1 Anvil, 13.1, 13.2): the opinion is a phase 0 gate item and phase 1 SSI has no sampling stage. |
| R9-02, R9-20 undecided branches | R9-02 accepted, R9-20 revised (5 `Truth`): control flow on `Undecided` yields a ceiling-independent value; the ceiling changes only reporting. |
| R9-03 evidence selection | Accepted (2 Evidence record): the evidence watermark. |
| R9-04, R11-01, R11-13, R11-21 labels | Accepted, R11-13 revised (5 `Labels`, 7.1 `repo`, 7.6, 7.8): confidentiality and integrity are separate parts, a merge clears integrity on typed inputs including imported Assets, and `ControlAuthorization` defines what satisfies a control. |
| R11-02, R11-35 free text | Accepted (7.6): evaluated strings carry span integrity; only untrusted text taints a context. |
| R11-04 external host contexts | Accepted (7.6): one context per (user, client identity), reset only by a human. |
| R9-05, R9-14, R9-15, R9-23 checks | Accepted (2 Check, Waiver; 5 `CheckId`, `CheckOutcome`, gate predicate; 7.6). |
| R9-06 source closure | Accepted (4). |
| R9-08 component data access | Accepted (4). |
| R9-09 random streams | Accepted (7.2). |
| R9-10 source labels | Accepted (7.1 `repo`): the module is the unit of a source label. |
| R9-11, R11-25 signatures | Accepted (7.8): detached signatures; ML-DSA-87 everywhere and LMS only for the steward's releases. |
| R9-21, R12-01 isolated Wasm components | Accepted (3, 7.4): asynchronous `crucible:ops` imports, remote evaluation in browsers until the bridge passes, and call-overhead targets. |
| R9-24, R9-25, R9-38, R10-28 crate map; the machine gateway request | Accepted, R9-24 revised (5, 12, 7.6): handles and `Classify` in `base`, `mech-model`, the missing apps and SDKs, `apps/machine-gateway`, and a layer check. |
| R9-33, R12-05 target phases | R12-05 accepted, R9-33 revised (13.3): a Phase column; orbit at 5M triangles stays phase 1. |
| R9-35 retired versions | Accepted (7.2): never cached. |
| R9-41 call sites | Accepted (2, 5, 7.1, 7.2): `OpSite` becomes `CallSite`; earlier logs keep the old name. |
| R9-42 growth guards | Accepted (7.4). |
| R9-46 names | Accepted (2, 7.8). |
| R10-01, R10-02, R10-04, R10-07, R10-08, R10-17 physical safety | Accepted (2 Act, 7.1 Hardware CI, 7.6): wire-level verification, pull-only drip feed, every device program through the gateway, one `unattended_safe` rule, class-bound programs, and a physical-effect section on the approval page. |
| R10-05 `start_print` | Revised (7.6): material extrusion only, a safety officer's policy per serial and confirmation at the printer. |
| R10-06; the firmware-flashing request | Accepted (2 Act, 7.6): `flash_device`. |
| R10-22 phase 2 additive part | Accepted (13.1): material extrusion through `send_print_job`. |
| R10-26, R12-16 plans and local exports | Accepted (2 Act, 7.6, 13.2): one Approval covers a plan's effects; a human's uncontrolled local export is an audited write; phase 1 supports a desktop install without a team server. |
| R11-03, R11-08, R11-09, R11-10 trust | Accepted, R11-10 revised (7.8): third-party code only in microVMs and per-tenant attestation, External Op receipts, default-deny egress, and the single-host rule. |
| R11-06 approval credentials | Accepted (7.6, 9). |
| R11-33 benchmark corpus | Accepted (13.2, 13.3): the licence-filtered ABC subset. |
| R11-34 licences | Accepted (7.7). |
| R11-43 classified information | Accepted (13.1 Scope). |
| R12-02, R12-03, R12-04, R12-12, R12-22 program plan | Accepted in a different form (13.2): the program has no human team. The founder directs, Claude orchestrates, separate agent roles write oracles, build and verify, and outside firms make, measure and advise. Phases end at gates, not dates; budgets count agent compute and outside services; the build program puts oracles first. |
| R12-06 reference laptop | Revised (13.3): a named model and fixed conditions, chosen by PLT. |
| R12-07, R12-09, R12-25 phase 1 schedule | Accepted, R12-07 revised (7.5, 13.1, 13.2): the kernel IR freezes once three consumers compile against it, chains C and D join the critical path, and the run build is tagged before the physical runs. Milestones are ordered, not dated. |
| R12-13 held-out splits | Accepted (3 principle 6, 13.3). |
| R12-14 iPadOS | Accepted (7.4). |
| R12-17 cancellation | Accepted (7.4). |
| R12-18 browser memory | Revised (9): the engine worker recycles; PLT sets the figures. |
| R12-24 preview criteria | Accepted (9). |
| R7-14, R8-15, R8-27, R9-22, R9-39, R9-53, R9-54, R12-21 | Revised, tab only: the contract already states the rule, or the fix is the tab's own. |
| CCR-ANV-9, CCR-UIX-7 `DisplayPackage` identity | Accepted together (5): name-free pages keyed by `GeometryId` with canonical-number back-references and a face table; the cluster DAG from phase 2. |
| CCR-FLX-10 boundary layers | Accepted (7.1): fitted meshes for turbulent layers, octree wall refinement for laminar ones, so 13.4's phase 3 rows do not wait for phase 4. |
| CCR-FLX-11 eigenvalue bounds | Accepted (5 `ErrorBound`): `Guaranteed` eigenvalue bounds where the method proves them. |
| CCR-KLN-9, CCR-AGT-12, CCR-ECO-11 error codes | Accepted together (7.6): `<family>/<code>` codes such as `label/write_down` and `act/approval_pending`. |
| CCR-KLN-10 catalog parts | Accepted (5 `ItemDefinition`): approved-manufacturer entries, so a changed source voids an approval. |
| CCR-MEC-1 definitional attributes | Accepted (5): general tolerances and ISO 13715 edge callouts are definitional. |
| CCR-MFG-7 controller capture | Accepted (13.2): the shop agreement includes time on each controller family's physical controls. |
| CCR-AGT-10 standing releases | Accepted (7.6). |
| CCR-AGT-11 AAL3 scope | Accepted (7.6): physical-effect Acts and Acts with `controls` labels, since risk classes belong to Proposals. |
| CCR-AGT-13 build-program bootstrap | Accepted (13.2): `WorkItem` over Git until AGT's Plan machinery ships. |
| CCR-UIX-8 scene capacity | Accepted (13.3). |
| CCR-ECO-10, CCR-PLT-10 support period | Accepted together (7.7): five years per stable release line, as the EU Cyber Resilience Act requires. |
| CCR-ECO-12 SDK names | Accepted (13.1). |
| CCR-PLT-9 tablet engine | Accepted (9). |
