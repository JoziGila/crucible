# Crucible architecture contract (v7.4)

Binding for every design agent and reviewer: where a tab disagrees with this contract, the contract wins, and a tab that believes a rule is wrong files a contract change request instead of working around it. Sections 1 to 13 state the design; sections 14 to 18 record how each version was ruled (versions 7 to 7.4 are section 18) and are read only when a ruling is in question.

## 1. Mission

Crucible is one Rust platform in which agents author physical products as typed programs and people steer, review, approve and present them: design, simulation, manufacture and release from a single model. Every subsystem is specified completely enough that agents working against oracles, directed by one founder, can build it without further design work. "Fully specified" means every capability has a purpose, a contract (inputs, outputs, types), failure behavior, an oracle that verifies it, and a phase.

The founder sets five hard requirements:

1. **Anything physical.** Every major physics domain and every scale, from MEMS to ships and building products. No software validly simulates literally everything, so every model states its validity envelope, the spec says plainly what is out of reach, and it defines how new physics and domains are added.
2. **State-of-the-art methods** for every component and every simulation (section 8).
3. **Every major operating system, identical features** (section 9).
4. **Coherence and taste** across the whole design (section 10), and text a human engineer reads with pleasure (section 11).
5. **Better than the incumbents and their clones.** An engineer who uses NX, CATIA, Creo, SOLIDWORKS, Fusion, Onshape, Ansys, Abaqus, COMSOL, Altium, KiCad, Mastercam, hyperMILL, Teamcenter or Windchill finds nothing they rely on missing by the phase the parity floor names (13.4), and finds reasons to switch that an AI-built clone cannot copy in weeks (section 8).

How this contract is organized: sections 2 to 6 define the vocabulary, the principles, the layering, the shared types and the language; section 7 fixes the architecture; sections 8 to 11 set the rules every tab follows; sections 12 and 13 fix the crates, the plan and the phases.

## 2. Names and glossary

Crucible's parts have one name each. The first table names the components; the second defines every shared concept in a sentence or two and points to the section that holds its rules. A term in the "Never call it" column is never used for that meaning.

| Name | What it is |
| --- | --- |
| Crucible | The platform (working name; clearance is a phase 0 gate item, 13.1) |
| Ingot | The design language; source files end in `.ingot`; package manifest `ingot.toml`, lockfile `ingot.lock` |
| Anvil | The geometry kernel |
| Flux | The physics and simulation engine (working name; it collides with Siemens Simcenter Flux and flux.ai and is renamed in phase 0, before any operation name or WIT package freezes) |
| Kiln | The incremental evaluation engine (name at risk; cleared or replaced in phase 0, 13.1) |
| CAS | The content-addressed store for all derived artifacts |
| `repo`, `plm`, `trust` | The product-service crates: history and merge; Items, revisions, BOMs and change orders; labels, signatures, authorization and audit (12) |
| `api` | The single API used by the UI, agents, CLI and CI, exposed over MCP (the Model Context Protocol) and native SDKs |
| std | The standard library of Ingot packages |
| Golden products | Reference products (GP1 to GP16) whose made and measured articles close each phase (13.1) |

No other codenames.

| Term | Definition | Never call it |
| --- | --- | --- |
| **Operation** | A versioned primitive in native Rust inside Anvil or Flux (`anvil::blend@2`, `flux::solve_linear@1`), pure and deterministic per its determinism grade (4, 7.3). | "op" in prose, "kernel", "function" |
| **Feature** | An Ingot function that captures design intent by orchestrating operations; the unit people see in a design's history. | "macro", "script" |
| **Wasm component** | A sandboxed extension compiled to WebAssembly with a WIT (WebAssembly Interface Types) interface, determinized before it runs (7.4). | bare "component", "plugin" |
| **Node** | One memoized computation in Kiln's graph: a front-end stage, feature call, Op, check, query resolution or computed view such as a BOM; keyed by its `NodeKey` (7.2). | "job", "task" |
| **Op** | A node that calls one operation, Wasm component or External Op. Rust types with the `Op` prefix name operations (`OpImpl`, `OpCx`, `OpResult`). | |
| **External Op** | An Op whose implementation runs outside the Wasm sandbox in an isolated host: a pinned container image for a copyleft solver, an FMU host, a firmware emulator (7.8). | "external tool run", "out-of-process result" |
| **External input** | Signed, content-addressed data produced outside evaluation (a licensed translation, a supplier offer, a catalog or regulation dataset, a policy package, an Evidence record), pinned in `ingot.lock`, read as a leaf input and changed only through an explicit update (7.2). | "snapshot", "data package" for this meaning |
| **Evidence record** | A signed measurement from a physical test (a rig, a CMM, a test lab): an External input addressed by the check it serves (5). | "measurement cell", "hardware result", "credibility level" |
| **Policy package** | A Package of organization records that evaluation reads (policy allowances, the parts policy, numbering, review routing), pinned in `ingot.lock` like any dependency (5). | "policy" alone |
| **Asset** | A non-source file in a design repository (a STEP file, a scan, a PDF datasheet), content-addressed and referenced from Ingot. | |
| **Evaluation** | One request to Kiln to compute a set of nodes for a Change, with a lifecycle (queued, running, done, aborted), streamed results and a report. | "job", "run", "build request" |
| **Check** | A predicate declared with `require`, evaluated as its own node, identified by its `CheckId` and concluded by a `CheckOutcome` (5). | "assertion", "rule result" |
| **Waiver** | A signature record that lets one named check count at a gate for named Items and effectivity, with a reason and an expiry; deviations and compliance exemptions are Waivers (5). | "deviation" as a separate record |
| **Signature record** | A detached, signed statement by a principal whose meaning comes from the signature table (5): Approvals, Waivers, endorsements, declassifications and grants. | |
| **Package** | A versioned unit in the package registry holding Ingot source, Wasm components, data (standards tables, catalog-part definitions, templates, tutorials, themes) or any combination. | |
| **Catalog part** | A purchasable item (bearing, motor, chip, fastener). Its definition is a Package under `parts::<manufacturer>::…`; its offers (price, stock, lead time) are External inputs. | "component" |
| **Body** | Geometry in any representation (5). | "Shape", "Solid" as a type |
| **Part** | A Body with identity (item number, name, material, properties) that appears in a BOM. | |
| **Assembly** | A tree of Instances with placements and mates. | |
| **Instance** | One occurrence of a Part or Assembly inside an Assembly. An Instance set is one BOM line whose members are keyed by anchors (6). | "occurrence", "component" |
| **Software item** | A versioned binary with identity (firmware, bitstream, application) that appears in a BOM and is bound to a programmable Instance. | |
| **Item** | The lifecycle identity of a releasable thing (Part, Assembly, document, Software item, catalog part, manufacturing program) with an item number. Its revisions are the only meaning of "revision". | |
| **Field** | A physical quantity distributed over a domain (5). | "result", "map", "curve", "waveform" as types |
| **Network** | A lumped model: elements connected through domain-typed ports, compiled by Flux into a DAE (a system of differential-algebraic equations) (5). | "Circuit" as the type name |
| **Material** | A versioned record of properties and constitutive models (5). | |
| **Proposal** | A branch plus rationale plus CI report; the unit of agent work and of human review. | "PR", "merge request" |
| **Approval** | A human principal's signature over the `ObjectId` of an approval subject (5). Any change to the subject voids it; changes outside it (a rebase, a CI re-run) do not. | "sign-off" as a noun for this |
| **Act** | An API method whose effect needs a human Approval of an exact plan, because it reaches outside Crucible or publishes a record others rely on (7.6). | "action" for this meaning |
| **API method** | An entry in the `api` catalog, named `<group>.<name>` (7.6). | "operation" |
| **Change** | One immutable fine-grained edit, like an Onshape microversion, stored as one Git commit (7.1). | "commit", except for its Git storage; a change order, request or notice |
| **Design repository** | The repository holding one product's Ingot source, Assets, `ingot.lock` and history. | |
| **Derived view** | A declassified, evaluated view of a labelled module or supplier package (signature, envelope, interfaces, mass properties) served to principals who cannot read its source (7.1). | |
| **Snapshot** | A rendered image of a `ViewState` under a `RenderProfile`, with structured marks and the renderer identity. Its pixels are `Unverified`: never canonical, never used for data. | |
| **Fidelity** | The accuracy a result is demanded at: `Preview` (fastest, approximate, never written to the shared cache), `Interactive` (approximate with an error estimate), `SignOff` (converged or exact). | "coarse", "exact", "sign-off mode"; "interactive" for a lane or priority class |
| **Model level** | The form of a physics model, from L0 (analytic) to L3 (full 3D) (COV). | "fidelity", "fidelity level" |
| **Credibility level** | How well a physics model has been tested against reality, from C0 (declared) to C4 (context-qualified) (COV). | "evidence level" |
| **Platform class** | The set of execution environments whose results are bit-identical (7.3). | |
| **Determinism grade** | What an operation version guarantees: `Portable`, `ClassExact` or `Certified` (7.3). | "execution mode" |
| **Witness** | A pinned non-canonical Field whose residual and error bound are computed canonically, so a check on it reproduces though the Field does not (7.3). | |
| **Labels** | The labels attached to every artifact, API response and model context: confidentiality, usage and integrity (5). | "taint flags", "classification tags" as separate concepts |
| **Failure** | A deterministic, typed reason a node produced no value (a fillet radius too large); a cached value that `try` can catch (7.2). | |
| **Abort** | An environmental end to a computation (cancellation, resource exhaustion, device or worker loss, budget, depth or fuel limit); never catchable, never cached (7.2). | "error" for this meaning |
| **Site safety record** | A record signed by a named safety officer that admits one device or rig to a restricted mode (`unattended_safe`, `start_print`) (7.1, 7.6). | "site policy" |
| **Service BOM** | The BOM view for service and spare parts. "Software bill of materials" is always spelled out. | "SBOM" |

The qualifiers that say how far to trust a number (fidelity, status, budget, bound kind, zone, levels, platform class, verdict and gate) are tabulated together in section 5.

## 3. Principles (non-negotiable)

1. **No privileged code.** Built-in features use only the public mechanisms anyone can use: Ingot for features, Wasm components for heavy algorithms, and versioned Anvil and Flux operations underneath. If a user or agent cannot build a feature, neither can Crucible's own builders. The one permitted difference is process isolation of third-party Wasm components, bounded by PLT's call-overhead targets (7.4).
2. **Agents author; people steer, review and present.** Agents and code write the typed program, and nobody needs to model by hand. People steer by pointing, marking up and asking; they review every Proposal, approve every Act, sign every Waiver and present the result. The UI is first a fast viewer, a reviewer and a presentation studio (7.6), and its direct edits write the same program an agent would. Every capability is reachable through `api` and Ingot; nothing exists only in the GUI.
3. **Two universal types.** `Body` carries geometry and `Field` carries physics data. Models (weak forms, Networks) describe how Fields are computed; libraries consume and produce Bodies, Fields and plain values.
4. **Determinism is a feature.** Same inputs and versions give identical outputs per platform class; results from different classes agree within declared tolerance or, for chaotic problems, in declared statistics. Problems with bifurcations or multiple solutions declare branch selection (an imperfection or symmetry-breaking input) or agreement on branch-invariant quantities. Evaluation never depends on clocks, randomness, thread order or names (7.3).
5. **The compiler checks physics.** Units, dimensions and tolerances are types, checked before anything runs. Every approximation carries its error in a stated norm.
6. **Every claim has an oracle.** No capability ships without a machine-checkable test that the agents building it cannot edit. Every oracle that judges agent-built code also has a held-out split outside the agent-readable tree, chosen by a keyed hash (HMAC-SHA-256 under a key only the oracle role holds, rotated at each gate) or generated from a seed drawn at CI time. A pass on visible inputs with a failure on held-out inputs fails the oracle, and builders see held-out results only as one aggregate verdict per work item per day (13.2).
7. **Open core, interop first.** Kernel, language and standard library are open source. Open standards are first-class; no design is ever trapped.

## 4. Layering: operations, Wasm components, features

Crucible's code sits in three tiers, and a capability lives in the lowest tier that serves it well. This keeps the core small and lets anyone extend Crucible the way its own builders do (principle 1).

- **Operations, in native Rust.** Geometry and physics algorithms, a few hundred primitives behind stable, versioned contracts in Anvil and Flux. Each operation family is its own crate (`anvil-op-blend`, `flux-op-solve-linear`), and each released version is a frozen source directory in it (`src/v2/`) that depends only on versioned first-party path dependencies (`linalg-v3`, `anvil-geom-v5`) and exact third-party versions.
- **Frozen closures.** A released version's closure hash is SHA-256 over its frozen directory, the frozen version directories of its first-party dependencies and the `Cargo.lock` checksums of its third-party dependencies, computed from `cargo metadata` by `cargo xtask closure-hash`. Kiln's registration refuses a released version whose closure hash changed, so a change to frozen code creates a new version that only new designs pin. The toolchain pin and the `detmath` epoch are recorded beside the hash; upgrading either passes golden-hash checks instead (ANV, PLT). A design pins the versions it was built with.
- **Retired versions.** Retired versions stay executable in archived engine builds compiled to Wasm, called through the frozen WIT world `crucible:archive/op@1` (KLN). It reads inputs and writes outputs as CAS objects tagged with their encoding version, and every release keeps decoders for each encoding an archived engine can emit. Only versions that cannot compile to Wasm (GPU `ClassExact` paths) fail with `OpVersionRetired`, whose fix is an upgrade Proposal.
- **Wasm components, for heavy custom algorithms.** Nesting, CAM strategies, slicers, placers and routers, importers, specialist solvers: sandboxed, determinized, portable to every OS and the browser, and published in the registry. Evaluation-world components may import the WIT package `crucible:ops`, whose interfaces `crucible:ops/anvil` and `crucible:ops/flux` expose versioned operations, GPU-backed ones included; each call is a recorded Op dependency. Components never get raw GPU, clock, file or network access. They reach engine data only through `crucible:ops` and handles derived from their inputs, never through a raw `ObjectId`, and every read is a recorded dependency whose label joins the node's.
- **Features, in Ingot.** Design intent, orchestration, entity selection and naming, checks and UI metadata.
- **Tier rule.** Use Ingot unless code needs more than about 10⁶ primitive steps per call, an existing codebase in another language, or a data structure Ingot cannot express efficiently; then write a Wasm component. Promote to an operation when at least three independent packages need it, it needs GPU or SIMD kernels, or it must be differentiable through Flux's form-level derivatives. Promotion happens in public, with oracles.
- **Rust features.** A feature may be authored in Rust as a Wasm component through `#[ingot::feature]`, which generates the WIT world and a typed Ingot wrapper (ING).

## 5. Core cross-subsystem types

These are the types every tab shares. Rust names are canonical, and shared types live in `base` (the three crates `base-id`, `base-value` and `base-op`, section 12) unless another crate is named; owners are in brackets. What Kiln memoizes, the CAS encodes and `crucible:ops` carries are erased forms: `Value` (scalars, `DynQuantity { si: f64, dim: Dim }` with `Dim` a vector of rational exponents over the base dimensions plus a kind id, records, lists, handles) and `DynField { domain, value, header, repr }`. Typed Rust views (`Length`, `Stress`, `Torque`, `Field<D, V>`) are generated from ING's kind table and check on conversion; Rust code never uses `uom` or `typenum`.

### 5.1 Values

- `Quantity<D>` [ING]: a number with dimension `D`. The base dimensions are SI's plus plane angle, which is radian-coherent and never cancelled implicitly. Rotational kinds use the strong angular system: `Torque` = J/rad, `MomentOfInertia` = kg·m²/rad², `RotationalStiffness` = J/rad². std defines named units so datasheet literals stay short (`Nm` is newton metre per radian; energy is written `J` or `[N*m]`). Oscillation angular frequency (ω = √(k/m), the ω in ωL) is a kind of T⁻¹, distinct from angular velocity (plane angle per time), and phase is dimensionless; a rotation becomes a phase only through an explicit `radian` conversion. °C and °F are affine points, kelvin values are differences, and `.absolute()` converts. Complex quantities exist. Every dimensional literal carries its unit, there are no default units, and conversion is exact rational with one rounding. Dimensions are checked at compile time and erased at run time. ING publishes the consistent system and an oracle of at least 50 textbook rotational, electrical and thermal formulas that type-check without casts.
- `Tol<T>` [ING]: a toleranced value. Arithmetic is worst case by default, using affine forms over noise symbols so repeated uses stay correlated; statistics (RSS, Monte Carlo, distributions, correlation groups) are explicit calls. A `Tol<T>` may be passed wherever `T` is declared: the body computes with the nominal, and the tolerance travels to the feature that realizes it, which records it as PMI (product and manufacturing information) on an anchored aspect query, re-resolved on the final Part. Std features mark the parameters whose value they realize (`#[realizes(OfSize)]` on `extrude`'s distance and `rib`'s `t`); a `Tol` passed to any other parameter fails with `ing/4104 ToleranceNotRealized`, whose fixes are `.nominal` or an explicit `part.tolerance(…)`. A forwarded noise symbol is keyed by (site, realizing feature `CallSite`, Part or Instance path), so two features of one Part, and two Parts made from one specification, vary independently. A PMI target that no longer resolves (split, merged or deleted) fails an `Error`-severity check and never degrades to a Note.
- `ErrorBound<Q>` [`base`]: `{ value: Q, norm, kind }`.
  - `norm` is `LInf`, `L2`, `Energy`, `Pointwise` or `Goal(functional)`. A `Guaranteed` bound on a quantity requires a proof in that quantity's norm. Energy-norm bounds never certify pointwise or extremal quantities. `Guaranteed` goal bounds exist only for bounded linear functionals (regional averages over a stated volume, reaction resultants, compliance, mean temperature) and for eigenvalues where the method proves the bound.
  - `kind` is `Guaranteed`, `Estimated { calibration }` or `Indicator`. The calibration is `Class { id, α }`, an empirical class with its measured factor (FLX), or `Statistical { method, α }`, an interval with a stated exceedance level (confidence intervals, the V&V 20 model-form part, conformal prediction, probabilistic eigenvalue bounds). An `Estimated` bound without either is an `Indicator`. α is recorded as verified: zero undershoots in at least 300 held-out cases is recorded as "α = 0.01 at 95% confidence", and reports print the total as "confidence ≥ 1 − Σα at 95%".
  - A check declares `decides_on`, the weakest kind that may decide it. "Evidence" never names a bound kind.
- `ErrorBudget<Q>` [`base`]: `{ parts: map ErrorSource → Component<Q>, total: Component<Q> }`, where `Component<Q>` is `Quantified(ErrorBound<Q>)` or `NotQuantified { reason }`.
  - `ErrorSource` is one of discretization, algebraic, temporal, quadrature, geometry, floating point, input and tolerance, statistical, model form, reduction or surrogate, interpolation, regularization. Each source has one producer: model form comes only from validation of the physics and constitutive model (COV) or from a policy allowance; dimensional reduction (shells, beams), reduced-order models and surrogates file under reduction or surrogate (FLX). The discretization part names how it was obtained: an a posteriori estimator or a convergence study.
  - Every part is stated in the norm of the quantity it bounds. An estimator computed in another norm enters only through a stated inequality (for a goal, the algebraic part includes the residual term the adjoint exposes, FLX), or the part is `NotQuantified`.
  - Composition: bounds in the same norm add; bounds in different norms never combine (the total is `NotQuantified`). Components that carry a confidence (`Estimated` bounds at their α, statistical parts, input distributions) become bounds at a stated per-component level and combine by a union bound, so the total, and every `CheckOutcome` resting on it, carries confidence 1 − Σαᵢ. Distributions are reported alongside and never summed with intervals. The total is `NotQuantified` if any part is, and its kind is the weakest part's.
  - A model-form bound from validation applies to a check functional only when the validation plan lists that functional's response quantity (quantity, location type, regime) among the quantities it validated; otherwise the part is `NotQuantified { reason: UnvalidatedQuantity }`.
- `Approx<T>` [ING]: a value with an `ErrorBudget<T::Delta>` restricted to `Pointwise` and `Goal` norms. Comparisons return `Truth`. A reduction of a Field (a maximum, an average) is `Quantified` only when Flux estimated that functional; otherwise comparisons on it are `Undecided`.
- `Truth` [ING]: `True`, `False`, `Undecided`. One decision rule, owned by ING and used by `if`, `match`, `require` and query `where:`: disjoint enclosures decide, subject to the check's `decides_on`. Control flow on `Undecided` yields the value `Undecided { needed, fidelity }` at the node's effective fidelity; it is cached like any value, `try` cannot catch it, and dependents receive `DependencyUndecided`. The Evaluation's fidelity ceiling changes only reporting, never a value: while a higher-fidelity node of the same target is demanded, the consumer's `ResultStatus` is `Pending`, and at the ceiling the Evaluation report raises the failure with the margin and the accuracy needed (`ing/6401` for control flow, `ResolveError::Ambiguous` for a `where:` filter).
- `Money<C>` [std, with Rust `Money { amount: Decimal, currency }` in `base`]: a decimal amount with an ISO 4217 currency type parameter; not a `Quantity`; no implicit conversion.
- `ExternalText` [ING, AGT]: untrusted text with its origin and integrity, written `external("...")`, never interpreted as instructions. Every string evaluated from a free-text span of untrusted integrity is an `ExternalText` value (5.3).
- `Severity` [`base`]: `Error`, `Warning`, `Info`, `Hint`, one enum for checks and diagnostics; a check may not declare `Hint`.

### 5.2 How far to trust a number

Every result Crucible shows answers the questions below, and each answer has one type and one owner. Tabs cite this table instead of re-explaining it; the Overview walks the canonical bracket through every row.

| Qualifier | Question it answers | Values | Owner |
| --- | --- | --- | --- |
| Fidelity | How hard did we try? | `Preview`, `Interactive`, `SignOff` | KLN |
| Result status | Is the value here and current? | `Pending`, `Proxy`, `Ready(Fidelity)`, `Stale`, `Failed`, `Aborted` | `base` |
| Error budget | Which errors were counted, and which were not? | One part per error source, `Quantified` or `NotQuantified` | `base`, FLX |
| Bound kind | How sure is each error bar? | `Guaranteed`, `Estimated { Class or Statistical }`, `Indicator` | `base`, FLX |
| Validity zone | Is the model inside the range where it was checked? | `Calibrated`, `Extrapolated`, `Invalid`, `Unassessed` | COV |
| Model level | What form of physics produced it? | L0 analytic to L3 full 3D | COV |
| Credibility level | How well has this model been tested against reality? | C0 declared to C4 context-qualified | COV |
| Platform class | Where would the same bits come out again? | The canonical class, `CpuIsa`, `Gpu`, `Unverified`; or a witness | PLT |
| Verdict | What does the check conclude? | `Pass`, `Fail`, `Undecided { reason }`, `Error`, `Skipped` | ING |
| Gate | May it merge or release? | The gate predicate (5.6) | ING, KLN |

### 5.3 Labels

- `Labels` [`base`, `trust`, AGT]: three parts, each joined through every derivation by Kiln and carried by every model context (7.6).
  - **Confidentiality** `{ level, controls, scopes }` is a lattice. `level` is public < internal < confidential; `controls` is a set of (regime, classification) pairs such as (ITAR, category) or (EAR, ECCN); `scopes` is a set of organization-defined scopes such as `customer:<name>` or `program:<name>`. The join takes the maximum level and the union of each set. A principal may read a value only if it satisfies every element, and `api` enforces this at every boundary. Clearances, write-down, encryption domains, worker partitions and live replication use this part only.
  - **Usage** `{ licences }` is a set of `DataLicence`s. It joins like confidentiality but is compared only at exits (7.6: `release_data` Acts, the one Act family that sends tenant data to another party; exports; audited local writes, registry publishing, responses to model contexts), never for encryption domains, worker partitions or replication. A licence that restricts who may read inside the tenant maps to a confidentiality scope instead.
  - **Integrity** `{ instruction_tainted, data_untrusted }` never blocks a read or a write; it sets risk classes and auto-merge eligibility (AGT). It attaches to typed inputs by provenance. A human merge of the Change that introduced an input (a lockfile pin, an Asset, a source span) clears both flags on that input's typed values: its structure, geometry and numbers. Merging never endorses free text. A string evaluated from a free-text span is an `ExternalText` value carrying the span's integrity, so text integrity travels with the value and not with the node. A node's label holds confidentiality, usage and the integrity of its typed inputs, plus the integrity of any `ExternalText` it turns into a non-text value (embossed geometry, a parsed number). Free text becomes trusted only through a per-span endorsement (7.6). Declassification never changes integrity, and endorsement never changes confidentiality. This paragraph is the only statement of the rule; tabs cite it.
- `ControlAuthorization` [`trust`]: what lets a principal, endpoint, recipient or service satisfy a `controls` element: regime, classifications, basis (US person, licence, licence exception, no licence required), permitted countries and recipients, conditions and expiry. A node whose label has `controls` runs and is stored only in the regulated cloud, in end-to-end mode, in a customer deployment, or on a desktop registered by an export officer as `controlled_device` (managed and full-disk encrypted), unless a `ControlAuthorization` covers the operator's staff. Such a desktop holds the controlled encryption domain's key on a lease of at most 24 h, without the offline grant, revoked remotely and before travel to a country outside the authorization's permitted countries. Location compliance remains the organization's determination.

### 5.4 Signature records and the signature table

Every human-signed record is one detached signature record `{ meaning, subject ObjectId, signer, credential assertion, time }` (7.8). The rules for who may sign each meaning live in one table, which the `trust` crate evaluates through Cedar and KLN fuzzes with one oracle. "Approval credential" means phishing-resistant WebAuthn user verification with a device-bound credential (7.6); AAL3 is the NIST SP 800-63B-4 level. No agent signs any record in this table.

| Meaning | Subject | Signers and roles | Credential | May the author or delegating human sign? |
| --- | --- | --- | --- | --- |
| Approval | An Act plan or `ApprovalSubject` | One assigned approver per Cedar | Approval credential; AAL3 for physical-effect Acts, `controls` payloads and 21 CFR Part 11 signatures | Yes, unless the plan relies on a Waiver they signed |
| Approval delegation | An `ApprovalDelegation` record | The delegator; never an agent as delegate; two people, one an export officer, when the scope covers physical-effect Acts or `controls` payloads | Approval credential; AAL3 with `controls` | Yes |
| Merge approval | A Proposal into a protected branch | Reviewers the branch rule requires | Approval credential, fresh, bound to the call | No: protected refs forbid self-approval |
| Waiver of a `Warning` check | Check, Items, effectivity | One authorized human | Approval credential | Yes |
| Waiver of an `Error` check | Check, Items, effectivity (serials or lots for a deviation) | One `quality` principal outside the Proposal's authoring and delegation chain; a release relying on it needs a different approver | Approval credential | No |
| Free-text endorsement | Source spans, shown verbatim | One human reader | Approval credential | Yes |
| Policy package change | Policy repository Change | Two people; `quality` for allowances | Approval credential | As one of the two |
| Declassification; `ControlAuthorization`; clearance of an endpoint, client or recipient for `confidential` or controlled data | Record | Two people, one an export officer | AAL3 | No |
| Recipient record; egress grant above `internal`; standing release; purge; widening Cedar change; auto-merge policy; `allow_raw_external` and training opt-in (AGT); evidence signer | Record | Two people with the `admin` or `quality` role the record names | Approval credential; AAL3 with `controls` | As one of the two |
| Approval-credential enrolment | The new credential's public key | The person's existing approval credential; a first credential needs an `admin`'s approval credential plus a recorded identity check and takes effect after 24 h | Approval credential | Yes, as stated |
| Site safety record | Device or rig serial | The named safety officer | AAL3 | Yes |
| Protected oracle and path changes in Crucible's own repository | Change | The founder, after the verifier role's attested review (recorded as the second check, `single_person`) | AAL3 | Yes |

Every enrolment notifies the person through their identity provider's out-of-band channel and the security contact. A credential enrolled within the last 24 h never approves a physical-effect Act or an Act with `controls`. **Single-person mode:** an organization with fewer than two eligible people signs each two-person row with its one person's AAL3 signature, and approves merges into a protected branch with a fresh approval credential after an `Attested` verifier review (before phase 2, a review the verifier role runs in Crucible's own CI under the work-item record of 13.2, signed by the CI runner's key, counts as `Attested`); two-person records and R3 and R4 merges take effect after 72 h, R1 and R2 merges at once, each with notice to the organization's recorded out-of-band contact and is marked `single_person`. Rows that touch `controls` are refused in this mode.

### 5.5 Geometry and product structure

- `Body` [ANV]: geometry in one of four representations: `BRep` (exact NURBS, analytic and procedural surfaces, cellular topology with regions), `Implicit`, `Mesh`, `SubD`.
  - The representation lattice is Mesh ⊂ BRep, SubD ⊂ BRep, BRep ⊂ Implicit. SubD ⊂ BRep is exact except near extraordinary vertices that carry semi-sharp creases, where the conversion records a bound.
  - Mixed operations return the least representation that holds both operands without approximating geometry or dropping B-rep faces that remain on the boundary; leaf-preserving conversion keeps exact faces, their `EntityId`s and attributes.
  - Approximating conversions record per-face bounds `{ position: ErrorBound, normal: angle bound }` and per-edge bounds `{ position, tangent: angle bound }`. These compose through stated propagation rules with certified conditioning (offsets, intersections, blend spines, Natural-offset corners) or become `NotQuantified`. The rules carry tangent and normal bounds, never position alone, and an offset of an approximated face propagates only where a certified curvature bound shows the offset is regular.
  - `Body` lives in Anvil's crates; `field` and `kiln` reach Bodies only through handles in `base`.
- **Two identities.** `GeometryId` hashes the canonical encoding with names, lineage and name-keyed attributes removed; `ObjectId` hashes the full encoding with names. A Body's `GeometryId` numbers its entities in a canonical geometric order. An Assembly's hashes the canonically ordered multiset of (child `GeometryId`, placement, mates by canonical entity number), without Instance names or paths; MEC owns that encoding. Caching, revision identity and approvals use them as 7.2 and `ItemDefinition` say.
- **Design attributes** [ANV]: every attribute class declares whether it is definitional. Definitional attributes (size tolerances and GD&T, general tolerances, ISO 13715 edge callouts, datums, `HoleSpec`, `ThreadSpec`, `Weld`, surface texture and finish, ply and laminate records, region material assignments) are encoded name-free by canonical entity number and enter the `ItemDefinition`. Role aliases and display styles are not definitional.
- `Part`, `Assembly`, `Instance`, `Transform` (rigid placement), `CoordSys` (a `Transform` anchored by a `Query`, re-resolved on every rebuild) [MEC, in `mech-model`]. `ShapeAspect<K>` [MEC]: an identified portion of a Body's boundary for GD&T, named after AP242's `shape_aspect`; MEC owns the one closed list of kinds.
- `CallSite` [ING]: the identity of a call site, derived from source text only.
  - A `let` statement's identity is (item path, arm path, binding name). An unnamed statement's identity is (item path, arm path, nearest preceding binding name, ordinal after it). A call's identity inside a statement is its operation or feature name with its occurrence index among calls of that name.
  - A `CallSite` is the path of these frames (statement, call, iteration keys) from the Evaluation's root, `fn` calls included, so two calls of one helper name their entities apart.
  - Iteration contributes keys, never positions: iteration over entity lists or resolved queries keys by `EntityId`; pattern generators return keyed lists (`linear` keys `(i, j)`, `circular` the angular index, `at_points` the anchor's `EntityId`, `fill` lattice coordinates from a declared origin, `by_density` each seed's initial key); only plain integer ranges keep integer keys.
  - Renaming a binding writes `#[was(original_name)]`, which preserves identity. The attribute always holds the original name, so a second rename rewrites it rather than stacking another; `crucible fmt --retire-was` removes them all in one Proposal whose review lists the entity renames and the checks, Waivers and Evidence records they touch.
  - Live-session block ids are never part of a `CallSite`. Cloning, pushing or mirroring through any Git host and rebuilding leaves every `EntityId` unchanged.
- `LiteralSite` [ING]: a `CallSite` plus an argument slot. Literal overrides key by it and follow `#[was]`.
- `EntityId` [ANV]: hash of (kind, `CallSite`, role, generating entity ids, discriminator). Argument values are excluded, so dimension edits that keep topology never rename entities; topology changes surface as `HistoryRecord`s and typed `ResolveError`s. Features may attach role aliases (`FeatureRole`) to entities they return.
- `HistoryRecord` [ANV]: created, modified, split from, merged from, deleted.
- `Query` [ING, ANV]: criteria over provenance and roles plus certified geometric filters, resolved by `anvil::resolve` as its own Op on every rebuild. There is no positional indexing.
  - Rank selectors (`longest`, `largest`, `first(along:)`) are allowed only after a provenance anchor or role filter; elsewhere the language service raises `ing/l-fragile-selector`.
  - Failure is a typed `ResolveError` with ranked fixes; success may carry Notes (`Merged`, `Partial`, `FragileAnchor`, `NearTie`) that checks may forbid.
  - Each operation declares per `Query` parameter whether it uses a surface (accepting these with a note) or an extent (edges of a face, areas, GD&T and PMI targets, drawing items). For an extent, a merge, a partial deletion, an `Ordinal` discriminator or a rank selection with a `NearTie` note fails with a typed `ResolveError` unless the call accepts it with `accept: [Merged, Partial, Fragile]` (default `[]`).
  - Resolution never silently picks another entity at the evaluated configuration. Stability across declared parameter ranges is sampled stability from a separate on-demand analysis (ANV) that reports `RankSwap`; protected-branch CI runs it on every query that ends in a rank selector or reaches an `Ordinal` id.
- `DisplayPackage` [ANV, UIX]: a per-Body clustered tessellation keyed by `GeometryId`, with stated chordal error and canonical-entity-number back-references that consumers join to `EntityId`s through the Body's face table. It is cached in CAS and consumed by every renderer. Its pages carry no names, so equal geometry in two designs shares pages; a cluster DAG arrives in phase 2 (13.2).
- `ViewState` [UIX]: camera, visibility, sections, explode offsets, animation and Field displays; stored as repository files and used by the UI, agents, Snapshots, presentations and comments.
- `RenderProfile` [UIX]: locale, theme, display units, font package pins and renderer behavior version; a `ViewState` under a `RenderProfile` determines a Snapshot.

### 5.6 Physics, evaluation and checks

- `Field<D, V>` [`field`, FLX]: a quantity over a domain `D`. Domains are spatial or entity sets (`Body`, `Regions`, `Faces`, `Edges`, `Vertices`, `Points`, `Instances`, `Ports`), parameter domains named by a quantity type (`Time`, `Frequency`, `Temperature`, `AngularVelocity`, `StrainRate`, …), index sets (`Mode`, `LoadCase`, `HarmonicIndex`, `Sample`, `Variant`) and products written as tuples. Examples: `Field<Body, Stress>`, `Field<(Body, Time), Temperature>`, `Field<Temperature, YoungsModulus>`, `Field<(Instances, Time), Transform>`, `Field<(Ports, Frequency), Complex<Impedance>>`, `Field<AngularVelocity, Length>` (a stability lobe), `Field<Body, ValidityZone>`. Values may be scalars, vectors, tensors, complex values or enums. Representations are `Analytic`, `Discrete`, `QuadraturePoint`, `SparseGrid`, `PerEntity`, `PointCloud`, `Reduced`, `Surrogate`. A `Part` is accepted wherever a `Body` domain is expected. Every result Field carries an `ErrorBudget`. Waveforms, spectra, sweeps, mode sets, load cases, ensembles, tables and material curves are all Fields, never separate types.
- `Network` [ELX, FLX]: elements connected through ports typed by domain (electrical, magnetic, thermal, rotational, translational, fluid, signal). Each port type declares its power expression, and the compiler checks that it is a power. Results are Fields over time or frequency on its ports.
- `Material` [COV, in `material`]: properties as Fields over state domains (temperature, strain rate, direction), statistical basis per property, constitutive model ids, provenance, certification, uncertainty, `DataLicence`, environmental records and microstructure descriptors.
- `ValidityEnvelope` [COV]: declared conditions where a model is trusted. It evaluates to a zone Field (`Calibrated`, `Extrapolated`, `Invalid`, `Unassessed`) and to checks with disposition `Flag` or `Refuse`. Only humans waive. Crucible suggests escalation to a valid model but never switches models automatically.
- `Feature` [ING]: an Ingot function from typed parameters to Parts, Bodies or plain values, with metadata that generates its dialog, docs and agent tool schema.
- `NodeKey`, `OpImpl`, `OpCx`, `OpResult`, `Stop`, `Failure`, `Abort` [KLN, in `base-op`] (7.2); `ObjectId`: the SHA-256 identity of a canonical CAS object, with a one-byte algorithm code reserved.
- `CheckId` [ING, in `base`]: (the attachment's `CallSite` or Instance path, the check's `name`). Every `Error`-severity check carries a `name:` (the deny-by-default lint `ing/l-unnamed-check` offers a name derived from the predicate), so inserting or removing another check never changes its identity; lower severities without a name fall back to the `require` statement's identity. A `CheckId` never derives from predicate text, so editing a limit keeps the check's identity, verdict history, Evidence records and Waivers.
- `CheckOutcome` [ING, in `base`]: `{ verdict, fidelity, decides_on, evidence_records, allowances, value, limit, margin, severity, source }`. `verdict` is `Pass`, `Fail`, `Undecided { reason, needed }`, `Error(Failure)` or `Skipped { reason }`. `allowances` lists the `ObjectId`s of the policy allowances the check read. "Provisional" is the derived predicate "fidelity below the declared one", never a verdict.
- **Policy allowance** [KLN]: a policy-package record naming an error source, its scope (check kinds, Items, model families), the allowance as an `Estimated` component and its citation (code and clause, such as a design-code partial factor that the code states covers model uncertainty). A check reads allowances like any pinned input, so they enter its trace and key. The model-form part is then `Quantified` by the allowance or `NotQuantified`, and the one decision rule gives `Pass`, `Fail` or `Undecided { reason: Unquantified(sources) }`. The same mechanism admits `Unverified` External Op results (7.8).
- **Policy packages** [KLN]: an organization's policy packages live in its policy repository, are versioned and signed like any Package, are pinned in each design's `ingot.lock` and are updated by a bot Proposal like any dependency, so a policy change never alters the verdict of an unchanged Change. Changing the policy repository needs the signers in 5.4. Cedar policies are separate: they authorize `api` calls and never feed evaluation.
- **Evidence records** [KLN]: an Evidence record is addressed by the `CheckId` it serves and the identities of the inputs it tested (`GeometryId`s for geometric inputs, `ObjectId`s otherwise). It is signed by an enrolled rig runner (TPM-held key under measured boot) or by a registered evidence signer: an external lab's record of organization, ISO/IEC 17025 accreditation scope, a signing key verified out of band, permitted characteristic kinds and expiry. It is valid only if the instrument's calibration covered the measurement date. A bot Proposal, or on protected branches an audited ref transaction, pins each record's id in `ingot.lock` under `[[evidence]]` keyed by `CheckId`; the update tool picks the newest valid record, and the check reads only the pinned one. One Change therefore fixes every outcome. Releases and Approvals cite the pinned ids.
- **Waivers** [KLN]: a Waiver names a `CheckId`, the Items and effectivity it covers (a revision range, or serials or lots for a deviation), a reason and an expiry (a revision, a serial range or a date checked when the gate applies), and attaches to a Proposal or change order. `#[waive]` in source only requests one and counts nowhere until a matching record exists. Protected checks and `Refuse` envelopes accept none; 5.4 says who signs.
- **Gate predicate** [ING, used by KLN and AGT]: a check meets a gate (a protected merge, a Proposal, a release) when its severity is below `Error`, or its verdict is a non-provisional `Pass` in a platform class the gate accepts (7.3), or a Waiver covers it. Every rule that says "passes every check" means this predicate.
- `Fidelity` [KLN]: `Preview`, `Interactive`, `SignOff`.
- `ResultStatus` [`base`]: what a consumer holds for a demanded result: `Pending`, `Proxy` (a dependent shown by affine extrapolation from its last value while it recomputes, never cached), `Ready(Fidelity)`, `Stale`, `Failed`, `Aborted`.
- `PlatformClass`, `DeterminismGrade` [PLT, KLN] (7.3). `PrincipalId`, `Budget` and `PriorityClass` [AGT], `ResultStatus`, `CheckOutcome` and the `PlacementPolicy` trait (which `trust` implements and Kiln calls) live in `base` so that `kiln` never depends on layers above it. `PriorityClass` is `Drag`, `Foreground`, `Agent`, `Ci`, `Batch`.
- `Proposal` [AGT, `repo`]: branch, rationale, CI report, author, delegation chain, parent and plan, risk class, labels, Snapshots, provenance.
- `ItemDefinition` [KLN, in `plm`]: the name-free definition of one Item revision, per `ItemKind { Part, Assembly, Document, SoftwareItem, CatalogPart, ManufacturingProgram }`. For a Part or Assembly: its `GeometryId`s with definitional attributes, `Material` `ObjectId`s, properties and the BOM by value. For a Software item: its binary hashes, software bill of materials digest, target bindings and toolchain digest. For a catalog part: its approved-manufacturer entries. For a document: its semantic content. For a manufacturing program: MFG's `ProgramSubject` (canonical program digests, machine class, nominal tool assemblies by T number, setup sheet, simulation verdicts and block map). Late-bound fields stay placeholders.
- `ApprovalSubject` [KLN, in `plm`]: `{ base revisions, ItemDefinition digests of every affected Item, check-verdict digest (CheckId, verdict, fidelity, platform class, value, limit, allowances), effectivity, Evidence record ids }` for releases and change orders. Approvals sign its `ObjectId`; the `ChangeId` and the full CI report are unsigned provenance, and `act.commit` recomputes the subject at its target and refuses a mismatch. Act plans have the plan digest as their subject, and manufacturing programs have MFG's `ProgramSubject`.

## 6. Ingot syntax reference

This is the canonical example. Every tab's examples follow Ingot's grammar; ING owns refinements and keeps this example valid.

```
use std::mech::{sketch, rect, extrude, rib, fillet, part}
use std::materials::alu_6061_t6
use std::sim::quick::static_stress

/// L-bracket with a stiffening web.
#[toolbox(category: "Structure", icon: "bracket")]
pub feature bracket(
    #[ui(step: 5mm)]
    width: Length in 20mm..=400mm = 60mm,
    thickness: Length = 6mm ± 0.1mm,
    load: Force = 1.2kN,
) -> Part {
    let outline = rect(width, 40mm)
    let base = sketch(plane.xy) { outline } |> extrude(thickness)
    let web = base.edge(role: end(outline.top)) |> rib(height: 20mm, t: thickness)
    let body = base + web
    let solid = body |> fillet(body.edges(new), 2mm)
    let p = part(solid, name: "Bracket").material(alu_6061_t6)
    let clamp = base.face(role: start_cap)
    let tip = web.face(role: end_cap)
    let study = static_stress(p, fixed: clamp, force: load * dir(-y), on: tip)
    let stress = study.von_mises.max(over: study.regular())
    p.require(stress < 0.6 * p.material.yield_strength(at: 20degC), name: "static_margin")
}
// width + load  →  error ing/3001: cannot add Length and Force
```

Read it top to bottom. The feature takes three typed parameters; `thickness` carries a tolerance, and `width + load` would not compile. The base plate is a sketched rectangle extruded by `thickness`. The web stands on the plate's top edge, selected by its role `end(outline.top)` (the edge the end cap gets from profile edge `outline.top`), never by a rank; every sweeping feature gives its faces, edges and vertices roles, and ANV owns the vocabulary. The tolerance on `thickness` becomes two independent PMI sites, one on the plate and one on the web, because each feature that realizes a tolerance owns its own noise symbol (5.1).

The study clamps the plate's bottom face and pushes the web's top face sideways, along −y. The check reads the maximum over `study.regular()`: the Part minus the default neighbourhood of each singular set Flux flags for this study (the edges of the clamped face and of the loaded face), never a whole face. Stress at those sets is singular in the model but not in the part, so a raw maximum there means nothing (7.1). The excluded neighbourhoods keep the web root and its fillet, where the bending stress peaks. If the maximum sits on the boundary of an excluded neighbourhood, the result is `Undecided { reason: MaximumAtExclusion }` with the fix "model the support".

The result is an `Approx<Stress>` with an `Estimated` bound, and the check is three-valued and named, so inserting another check never changes its identity. An ING oracle shows that the check decides at `SignOff`: the bracket passes at 6 mm and fails at 4 mm, where the web root's bending stress exceeds the limit.

Weak forms are written the same way:

```
let u = trial(Displacement, p)
let v = test(u)
let elasticity = inner(sigma(u, p.material), eps(v)) * dx(p)
              == dot(traction, v) * ds(tip)
let result = solve(elasticity, fixed: clamp)
result.von_mises  // Field<Part, Stress>
```

Language rules every tab follows:

- No new keywords for domain concepts. Constraints are ordinary functions over `Expr<T>`; interfaces are records marked `#[interface]`; variants are enum or record parameters marked `#[configuration]` on assembly features, selected with `if` and `match`.
- An Instance's or Instance set's existence may depend only on configuration parameters and constants (a compile error otherwise), so Kiln computes the 150% BOM by abstract interpretation with SAT checks instead of enumeration. An Instance set's member count and placements may depend on any value and are keyed by its anchors: a fastener per resolved hole is one BOM line whose quantity is evaluated.
- Variant rules and requirements are `require` checks and `std::systems` records. Builder blocks (`sketch { … }`, `network { … }`) are the only block sugar.
- Constitutive code never differentiates through loops: local Newton solves use the kernel IR's `local_solve(residual, x0)`, whose derivative comes from the implicit function theorem at the converged point.
- Every diagnostic and failure renders as `<family>/<code>` (7.6): Ingot's numbered errors are `ing/<number>` and its lints `ing/l-<name>`.

**std package names.** `std::mech`, `std::mfg`, `std::electronics`, `std::systems`, `std::sim` (Flux building blocks: spaces, forms, `solve`, plans, quick studies), `std::physics` (physics models built on `std::sim`), `std::materials`, `std::opt`, `std::uq`, `std::agents`, `std::explore`. Sub-packages nest under these (`std::physics::regime`, `std::agents::proposal`). First-party packages outside std use `crucible::`; catalog parts use `parts::<manufacturer>::`; WIT packages use the `crucible:` namespace, one package per domain.

## 7. Decided architecture

These decisions hold across every tab; contradicting one needs a change request.

### 7.1 Engines

#### Anvil

- **One Body, four representations,** with the lattice of 5.5. Cellular B-rep with regions serves multi-material parts and conformal meshing. Each Body has a scale-relative resolution ρ (the length below which Anvil treats geometry as coincident) plus per-entity tolerances; there is no global tolerance.
- **Decisions.** Linear decisions use exact adaptive predicates. Decisions on curved geometry use certified enclosures with recorded, capped tolerance growth, made in rounds by dimension against tolerances frozen at each round's start, so outcomes never depend on pair order. Every operation checks separation of created and modified entities against the whole Body through the broad phase, not only against neighbours.
- **One computation for `Interactive` and `SignOff`.** Decisions are the same at every fidelity: at `Interactive` a floating-point filter with a forward error bound decides when the bound separates the alternatives, and the certified rule runs otherwise. Every intersection component is traced from a canonical start point, so a trace depends on the component and not on the seed that found it. `Interactive` may seed by sampling where the freedom-to-operate opinion of 13.1 allows it (never in phase 1); `SignOff` adds a certification node that runs certified seeding, confirms it finds exactly the components already traced, and confirms each traced point by a Krawczyk test (an interval test that proves one root in a box). When certification succeeds, the `Interactive` geometry is the `SignOff` geometry bit for bit; only a failed certification recomputes. Geometry operations therefore map `Interactive` and `SignOff` to one effective fidelity (7.2).
- **Surface–surface intersection (SSI),** the computation of the curves where two surfaces meet. Every transversal intersection point is a certified root of the exact equations; tangential contact curves and coincidence regions are certified enclosures within their recorded tolerance; no point is ever selected from a sample set by a distance threshold. Phase 1 SSI has no sampling stage: closed forms among planes, quadrics and tori, and certified subdivision for the other phase 1 pairs. GPU sampling that orders CPU work, with an exact integer broad phase, joins in phase 2 only after a favourable freedom-to-operate opinion (13.1).
- **Phase closure.** An operation is phased no earlier than the SSI and offset classes its output surfaces need. ANV lists every pair of surface types that a phase's operations create as a class with a phase, so lofts, non-circular sweeps and twisted or scaled extrusions join in phase 2 with general NURBS intersection and offsets.
- **Blends** are a staged research program. Stage 1 supports procedural blend, offset and swept supports (sequential fillets), `RollOver` overflow, valence-3 corners with unequal radii and mixed convexity by setbacks, chamfer–fillet corners, termination at smooth edges, convexity change along an edge and linearly varying radius. Later stages add valence four and above, partial-length blends with setback ends, capped and cliff ends, Field-driven radii and G2 and G3 sections. An implicit fallback runs only when requested, with stated deviation. G2 and G3 analysis is built in.
- **Ownership.** History records in every operation. Anvil owns all mesh generation, including volume meshing, adaptation and node optimization; Flux passes sizing and metric Fields. Anvil owns the geometric constraint solver (`anvil::solve_constraints`, `anvil::analyze_constraints`) and `anvil-planar`: exact predicates on stored integer-coordinate 2D geometry with lines and arcs, whose constructions (offsets, Minkowski sums with a disc, arc intersections) snap to the grid in a declared conservative direction, so derived geometry passes exact rule checks by construction (`anvil::planar::boolean`, `offset`, `distance`, `medial_axis`). Flex circuits bend with the sheet-metal `anvil::fold`. Anvil's operations catalog is the canonical list of operation names.
- **Label invariance.** An operation's geometry, connectivity, Field values and statistics are invariant under any injective renaming of input `EntityId`s and `CallSite`s; only name sections may change. Canonical orders, symbolic-perturbation indices, independent-set priorities, random seeds and the order of statistical inputs (tolerance noise symbols, Sobol dimensions) come from geometry, topology and argument values, never from names. Oracle: rebuild every golden product with every name re-randomized; geometry hashes and check values, statistical checks included, are identical.

#### Flux

Physics is stated as weak forms in Ingot and compiled through the shared kernel IR (7.5). Every result Field carries an `ErrorBudget`, and the resolved `SolvePlan` (from a versioned `flux::plan` operation) is pinned and enters the cache key.

- **Discretization per region.** Dimensionally reduced models serve where a local slenderness criterion holds: Timoshenko and Vlasov beams for members and struts, and Reissner–Mindlin shells on Anvil mid-surfaces for thin walls where t/L_local ≤ 0.2. L_local is the smallest of the span between supports, the radius of curvature, the distance to the nearest concentrated condition (a point or line load, the edge of a load or support patch inside the wall, an opening or a feature) and, for a distributed load q, the length |q|/|∇q| over which it varies; distributed loads, body forces and inertia that cover the wall do not shorten it. Reduced regions couple to solids through rigid and Nitsche-based mixed-dimensional interfaces.
- **Reduction by symmetry.** Plane stress, plane strain, generalized plane strain and axisymmetric models (with or without twist), and symmetry, antisymmetry and cyclic-sector reductions with harmonic indices, are detected from Anvil's certified analysis or declared. Each checks that loads and geometry satisfy the symmetry and fails with `SymmetryBroken { entity }` otherwise, never giving a silent wrong answer.
- **Solids and flow.** Solids use an immersed adaptive octree: aggregated CutFEM (finite elements on a background grid that the geometry cuts, with tiny cut cells merged into neighbours) at `Interactive` and `SignOff`, with at least four cells across any section; the finite cell method for voxel data; and the shifted boundary method for at most `Preview`. Fitted meshes serve contact and turbulent boundary layers, with octree wall refinement for laminar thermal and frozen boundary layers. Lattices use beam-lattice models with node corrections and homogenization; isogeometric shells are available.
- **Solvers.** Matrix-free high-order FEM with sum factorization; Flux's own p- and h-multigrid and deterministic algebraic multigrid; the canonical linear-algebra crate `linalg` (fixed machine-independent blocking, canonical lane order, no FMA) for `Portable` results, with unmodified faer only in `CpuIsa`; optional PETSc and hypre bridges. Adjoints are discrete-consistent, derived from forms and chained through Kiln.
- **Singular sets and regularized goals.** Peak and pointwise quantities are regularized goals (a p-norm or a local average over a stated region, with the regularization error in the budget) and carry `Estimated` bounds; a raw maximum is never a goal. Flux flags singular sets: re-entrant edges and corners, material interfaces meeting the boundary, and conditions that are incompatible where they meet. Those are edges where a clamped or fixed face meets a free face, edges of a load or support patch inside a face, edges where a loaded face meets a free face and the traction has a component along the free face's normal, and contact zones that contain an edge or corner of either surface. A uniform normal traction over a whole face meeting free faces at convex edges is compatible and is not flagged; smooth non-conforming contact is a low-regularity set that guides refinement but is not singular. Each flagged set carries a default neighbourhood (FLX); `study.regular()` is the domain minus those neighbourhoods. A point quantity whose region meets a flagged set is `Undecided { SingularPoint }`, and a maximum attained on the boundary of an excluded neighbourhood is `Undecided { MaximumAtExclusion }` with the fix "model the support".
- **Calibration.** Every `Estimated` bound is reported already multiplied by its calibrated factor and labelled with its calibration (5.1). A calibration class declares an applicability envelope over computable features of the result (FLX lists them), and a result outside it reports `Indicator`. A `SignOff` `Pass` that rests on an `Estimated` discretization part is confirmed by one further refinement (h/2 or p + 1, the plan's choice): the refined value lies inside the first bound and its own bound is smaller, or the verdict is `Undecided { reason: CalibrationUnconfirmed }`; Kiln's cost model counts the extra solve.
- **Surrogates.** Surrogate predictions are Fields with kind `Estimated { Statistical, scope: Marginal }`. They may drive `Preview` and `Interactive` results and design exploration; a `SignOff` check may use one only with a per-prediction a posteriori bound in the check's norm or a confirming solve. Inside optimization loops, calibration uses weighted conformal prediction.
- **Nonlinear solves.** From phase 2, Newton and arc-length solvers detect bifurcation points and return `Bifurcation { load, modes }` instead of silently choosing a branch; in phase 1, Newton accepts only forms declared convex and returns `Unsupported { reason: NoBifurcationMonitor }` otherwise.
- **Scope.** Flux also provides rigid and flexible multibody dynamics, Cosserat rods for cables and hoses, the Network compiler and DAE solver, block-triangular sparse LU, full-wave electromagnetics, magnetodynamics with motion, analyst idealizations (remote points, point masses, springs, bushings, connectors) and the general operations that non-variational methods need (BVH build and traversal, neighbour lists, segmented reductions, counter-based random streams, fast multipole and hierarchical matrices, FFT solves). GPL tools (Meep, Elmer, OpenFOAM, LAMMPS and others) run only as External Ops or oracles (7.7).

#### Kiln

- **Scheduler.** A suspending scheduler with dynamic dependencies, Salsa-style durability and backdating, verifying traces in memory and constructive traces in the shared cache. Interactive early cutoff compares values directly; hashing happens off the interactive path. Progressive refinement is a set of independent nodes keyed by fidelity. Eviction is GreedyDual-Size.
- **Labels in the memo.** A node's label is a separate memo output with its own change marker: verification re-joins labels from current inputs even when the value backdates, and a shared-cache hit returns only the value, with the label recomputed locally.
- **Derivatives.** `trait Differentiable: OpImpl { tangent, adjoint }` lives in `base-op`, with reverse traversal from a scalar goal and step state keyed by (`NodeKey`, step) in a `StepState` retention tier that eviction drops first.
- **Generic engine.** Kiln knows no domain: Anvil, Flux and Ingot register node kinds through the operation contract in `base-op`, and the `engine` crate wires them together (12). Two Evaluation-wide limits are enforced as Aborts: a demand-depth limit on nested node demands (default 10,000) and an aggregate fuel governor per Evaluation taken from its budget.

#### `repo`, `plm` and `trust`

- **Git storage.** A Crucible repository is an ordinary Git repository, so people clone, branch, pull and push it with the tools they already use. Each Change is a commit; branches and release tags are refs; Ingot source, `ingot.lock`, policy packages and the text records of `plm` and `trust` are files and refs (signature records under `refs/crucible/`). Computed results (Bodies, Fields, Snapshots) stay out of Git, in Kiln's content-addressed cache keyed by `NodeKey`, and large imported Assets are Git LFS pointers that Kiln's store serves. Each commit carries a `Crucible-Object` trailer holding its SHA-256 `ObjectId`, so signatures, Evidence records and approvals bind to Crucible's identity while the Git object format follows the host (SHA-1 where a host lacks SHA-256). `repo` reads and writes Git through gitoxide, a pure-Rust implementation.
- **Hosts and protected branches.** Any Git host can be a repository's home: Kiln's own Git server, GitHub, GitLab or another. A pull request is a Proposal: Kiln's CI runs it and its review links both ways. On protected branches Kiln is a required status check that passes only when the merge rule below holds and the merge's signature records (5.4) exist, and Kiln signs a release only when every merge in the released history carries them, so a merge that bypasses the host's protection can never be released. A conflicted Change records its sides as Jujutsu does, as extra trees named in a commit header, and never reaches a protected branch.
- **History.** Every edit becomes an immutable Change; ref updates go through a Jujutsu-style transaction log; branches are cheap. A merge is clean only when the result compiles and resolves and all of these hold: no check's verdict on the merge is worse than on each parent that defines it (`Pass` > `Undecided` > `Fail` > `Error`; `Skipped` counts as undefined); no interference appears that neither parent has; there is no provenance-level geometric conflict (both sides modify, split or delete the same base entity, or one side's new entity intersects the other side's modified region); and no connectivity conflict (a merged net, harness connection or interface connection that unions nets distinct in the base and in each side). Symmetric-difference regions appear in review but do not block.
- **Live sessions.** People and agents editing one branch at once share a server-sequenced edit log. Clients apply `SourcePatch`es optimistically, the relay orders and checks them against permissions and locks, and each client rebases its pending patches with the same `MergeDriver` that branch merges use, so a pair of edits merges the same way live or on branches. Literal edits are last-writer-wins in sequence order. Offline work rejoins by fast-forward when nobody else changed the package meanwhile; after a disconnection of up to 60 s its pending patches rebase like any live edit when they do not conflict; otherwise it rejoins as a branch. Replication and sequencing are per (package, module confidentiality label).
- **Labelled modules and derived views.** The unit of a source label is a module (one file). Git has no per-path read control, so a module goes in a separate repository only when someone who reads the product repository may not read it (a `controls` or `scopes` entry they lack); the product repository references it by commit. An organization whose readers are all cleared keeps one repository. Suppliers and customers receive exports and derived views, never clones. A principal who cannot read a labelled module, or a supplier, sees it only through derived views: its signature, envelope, interfaces and mass properties, each with its own declassification record, evaluated remotely on cleared workers. Any node that joins an output not covered by a declassification record is unreadable to that principal. Evaluations by such a principal run under a per-principal query budget and parameter grid named in the declassification record, and every outcome that depends on the module beyond its declared views (verdict, failure kind, cost, duration) reaches that principal only as `Withheld`; Proposal CI reports "blocked by a check you cannot read" without naming it.
- **Span provenance.** `repo` keeps span-level integrity: each source span records the integrity of the context that wrote it, and merges preserve it. A span is trusted only when a person typed it in Crucible's own editor or the compiler produced it. Spans arriving through a language-server connection, a file import, a push from a Git client or any other channel are `data_untrusted` until the user confirms the batch on the approval origin (the separate web origin that serves only approval pages and ceremonies, 7.6), and imported spans keep their integrity only when the server that witnessed the write signed their span-integrity record.
- **PLM.** Releases are signed tags. Change orders are Proposals whose approvals are the Approvals of the release Act's plan, and revision identity uses the `ItemDefinition` (5.6). The BOM is a computed view over the assembly graph with EBOM, MBOM and service BOM views. Deviations and compliance exemptions are Waivers (5.4), and compliance checks return `CheckOutcome`s like any check.
- **Trust.** Cedar policies authorize `api` calls; the signature table (5.4) governs every signature record; audit, transaction logs and release tags live in per-tenant transparency logs (C2SP tlog-tiles).

#### Hardware CI

Every Change on a protected branch rebuilds the design and evaluates its checks; regression and golden-product `SignOff` simulations run at least nightly. Physical tests are Acts that run on hardware rigs when their inputs change, and their Evidence records enter designs by pinning (5.6).

`unattended_safe` is a site safety record issued by the named safety officer; a runner never declares it for itself. Production equipment (machine tools, robots, lasers, production presses and furnaces, and every device class `send_to_machine` reaches) never receives it. A test rig receives it only with a risk assessment to ISO 12100 that the safety officer signs for the rig and its test article, interlocked guarding and its own safety-rated stop. The runner enforces the record's energy limits locally (force, displacement, temperature, voltage, current, stored charge), and battery tests above the record's cell energy run only in a rated containment chamber with gas detection. Rigs under that record run through the `run_rig_test` Act after an Approval, without on-site confirmation, and sign their Evidence records with TPM-held device keys under measured boot.

### 7.2 Keys, failures and aborts

A `NodeKey` is the SHA-256 of the items that apply to the node's kind:

1. its code: the operation name and behavior version; for a Wasm component, the SHA-256 of its determinized binary; for Ingot code, the code hashes of the modules actually used plus the language behavior version;
2. the canonical encoding of the arguments, including any resolved plan;
3. the identities of the inputs, pinned External inputs (policy packages and Evidence records among them) included: `GeometryId`s for the geometric stage of an entity-naming Op and for Flux solves (plus the canonical numbers of the entities their conditions reference); `ObjectId`s otherwise;
4. the platform class of the result, which is `CpuCanonical` for `Portable` and `Certified` results;
5. the fidelity: Ingot nodes (feature calls, query resolutions, checks, computed views) carry the requested fidelity unchanged, and each operation version maps the requested fidelity to its effective fidelity (an operation that ignores fidelity maps all three to one value, so equal results share one node);
6. the `CallSite`, for every node whose value carries `EntityId`s (feature calls, entity-naming Ops, query resolutions);
7. for External Ops, the host image digest.

The lockfile as a whole never enters a key. Entity-naming Ops cache in two stages. The geometric stage, keyed by input `GeometryId`s, numbers new entities canonically and refers to input entities by canonical number, so std features called from different designs share every geometric result. The relabeling stage, keyed by the geometric output's id, the `CallSite` and the inputs' name maps, assigns `EntityId`s. Both stages apply to failures and notes: the geometric stage reports them over canonical numbers with fix templates, and the relabeling stage maps them to `EntityId`s and source fixes that name the design's own bindings. Random streams are keyed by the operation identity, argument values and input `GeometryId`s or name-free content hashes, never by class, fidelity, `ObjectId`s of named values or `CallSite`s; KLN owns the mechanism.

**Failures and Aborts.** A deterministic `Failure` (a fillet radius too large, a query split) is a value: catchable with `try`, cached, and wrapped as `DependencyFailed` for dependents. `OpVersionRetired` is a catchable `Failure` that is never memoized or written to the shared cache, because it depends on the engine release rather than on the inputs. An Abort is environmental: `try` cannot observe it, it propagates to every transitive dependent, and no node that observed one writes a memo entry, a CAS object or an attestation. In Rust, an operation returns `OpResult<T> = Result<T, Stop>`, where `Stop` is `Failure(Failure)` or `Abort(Abort)`; `base-op` defines all three, `Failure` as an extensible typed union with a code, a reason and fixes, and `Abort` as a closed enum of the kinds in section 2. There is no conversion between `Failure` and `Abort` (a compile-fail oracle proves it), and Kiln memoizes only `Stop::Failure`. Oracle: inject environmental faults at random Ops in 10,000 runs; every value that reaches the memo or the shared cache equals the fault-free run's value. Every node terminates with a value or a typed `Failure`; every Evaluation terminates or aborts. A reached work or memory limit is a `Failure` in the `kiln/` family (`kiln/work_limit`, `kiln/memory_limit`) whichever layer reaches it, and a search that stops at a limit returns its best result so far beside that Failure.

### 7.3 Determinism

- `PlatformClass` [PLT]: `CpuCanonical { epoch }` (every Tier 1 CPU target, browsers included, at any thread count and ISA level; in prose "the canonical platform class", or "the canonical class" after first use), `CpuIsa { isa, epoch }` (a native fast path for one ISA level, which may use FMA and native widths), `Gpu(GpuClass)` (one compiled pipeline on one verified device class: driver and shader-compiler build plus pipeline hash, where on Apple platforms the shader compiler is the OS build), and `Unverified` (unlisted devices and external hosts). The operating system is never part of a CPU class.
- `DeterminismGrade` [KLN], declared per operation version: `Portable` (bit-identical across the canonical class; the only grade for geometry and oracle reference results), `ClassExact` (bit-identical within one class), `Certified` (output independent of the class that computed intermediates, for example GPU filtering with CPU decisions). Kiln selects the class an Op runs in; there is no separate execution-mode concept.
- Results from `CpuIsa`, `Gpu` and `Unverified` classes never substitute for canonical results. A check, release or Proposal that requires canonical results recomputes them in the canonical class, with one exception: a check may rest on a witness, a pinned non-canonical Field (GPU solves, CPU certifies) whose residual and error bound are computed canonically from it. A release pins the `ObjectId`s of every witness, External Op result and Evidence record it relies on. `CpuIsa` variants with FMA may serve `Preview` and `Interactive` fidelity when a kernel family loses more than 1.3× without FMA; `SignOff` recomputes canonically, and Kiln's cost model counts the recompute.
- Mechanisms [PLT]: `detmath`, the only elementary-function library in `Portable` code (correctly rounded, ported from CORE-MATH); a canonical lane order for horizontal operations (every reduction, scan or cross-lane operation in `Portable` code follows the 8-lane f64 or 16-lane f32 tree of `det_sum`; element-wise code may use any native width); binned reproducible summation (`exact_sum`) where partitioning varies; on CPU classes no implicit FMA contraction anywhere and explicit `mul_add` only inside `detmath` and error-free transformations; on GPUs, integer arithmetic for everything that must be exact (integer-limb reductions), non-finite detection on the CPU after readback by integer inspection, and a known-answer test for each compiled pipeline at creation and after any driver or OS update, with CPU fallback on failure; and the canonical linear-algebra crate. Each source-level rule names its enforcement: Clippy's `disallowed-methods` and `disallowed-types`, cargo-deny bans, or Crucible's own dylint library (PLT).
- The determinism suite runs on every merge on a representative set (Linux x86-64 with forced v2, v3 and v4; Linux ARM64; macOS ARM64; wasm32 in Node and in headless Chrome, threaded and single-threaded) and on every other Tier 1 target and browser engine at least nightly. A nightly divergence bisects automatically, opens a severity-1 determinism incident and blocks promotion to beta.

### 7.4 Wasm execution

- **One determinizer,** versioned, in `wasm-host` [PLT]. The registry runs it at publish time, in a single-use microVM that runs no package code, twice on different hosts, with the host computing the output hash; the local toolchain runs it at build time for unpublished components. Hosts execute only determinized binaries, and every host re-runs the pinned determinizer on the published input binary at install and refuses a component whose output hash differs from the index entry.
- **What it injects.** It validates the binary, rejects nondeterministic features, and injects fuel metering (whose check also reads a host cancellation word), stack-depth limits, growth guards that turn a host-caused `memory.grow` or `table.grow` failure below the declared maximum into an Abort, and NaN canonicalization only where NaN bits become observable: float stores, `reinterpret`, the sign operand of `copysign`, host-call arguments and results, and v128 values from float operations that reach bitwise, integer-lane, shuffle, store or extract-to-integer instructions. For modules emitted by the Ingot code generator it verifies instead of rewriting: no forbidden instructions or imports, a fuel decrement dominating every loop back-edge and function entry, a non-finite check before every observable float use, and a depth counter in every prologue.
- **Cancellation** lands only at fuel-check points; epoch interruption is never used. Where shared memory is absent, cancellation lands at Op boundaries, and Kiln runs every Op estimated above 100 ms in a disposable worker that it cancels by terminating.
- **Executors.** Native: Wasmtime pinned to its LTS releases, with Cranelift. Browsers: one first-party component runtime, `apps/platform-web`'s implementation of `wasm-host`'s engine trait, instantiates determinized core modules in the browser's engine, with no per-component generated JavaScript. iPadOS: the web build runs in a thin WKWebView shell, where JavaScriptCore compiles Wasm, so it shares the browser runtime and its asynchronous `crucible:ops` bridge. The iPadOS app runs only first-party components shipped inside its binary and evaluates registry components remotely, so no downloaded code runs in it (App Review guideline 2.5.2); registry packages appear only as dependencies of an opened design, never as a browsable catalog (guideline 3.2.2(i)).
- **Isolation.** Only first-party Wasm components (std and Crucible's own packages, built by the operator's registry builders) run in the engine process. Every third-party component runs out of process on every target: in an OS-sandboxed worker on native targets, one per tenant and confidentiality label on servers, and in an opaque-origin sandboxed worker in browsers. Browsers evaluate third-party evaluation-world components remotely until the asynchronous bridge passes PLT's executor oracle in browsers.
- **Ingot executors.** Until the Ingot code generator ships, the Ingot reference interpreter (in Rust, in the canonical class) is the only Ingot executor on every target. The code generator to Wasm enters when `ingot-bench` shows Ingot above 2% of a golden-product rebuild; from then on, generated modules pass the determinizer's verification and run on the executors above, and the interpreter remains for cold start, debugging, replay and differential testing.
- **Worlds.** Evaluation worlds import no WASI and are deterministic. Their `crucible:ops` imports are Component Model async functions in the callback ABI (no stack switching), so a host may answer them across a process or agent-cluster boundary, and native hosts may still answer at once. Results never depend on completion order or timing, and fuel never counts host time. Tool and connector worlds use WASI 0.3. A determinized component whose host calls are all `Portable` is itself `Portable`. Constitutive models use the `crucible:material/constitutive` world: models expressed in the kernel IR get tangents by algorithmic differentiation (with `local_solve` for local Newton solves); opaque Wasm models supply consistent tangents, verified by a Taylor-test oracle, and a plasticity benchmark shows quadratic global Newton convergence.
- **Overheads.** PLT publishes one overhead table that ECO cites. Determinizer targets: scalar-float components ≤ 10%, SIMD-float components ≤ 25%, fuel and stack metering ≤ 10%, per component class. Isolation targets: one `crucible:ops` round trip from a sandboxed worker costs at most 20 µs between native processes and 250 µs across browser agent clusters, plus argument transfer per MiB; `crucible:ops` offers a batched call form; and std's components, run in the third-party configuration on every release, stay within 15% of their in-process time.

### 7.5 Shared kernel IR and symbolic expressions

- **One symbolic layer.** One hash-consed symbolic expression type, `kernels::expr`, carries constraints, analytic Fields, implicit functions, weak forms and residuals, with typed node sets per use and symbolic differentiation implemented once. Ingot's `Expr<T>` lowers to it, `flux-forms` and `anvil-implicit` extend it, and the kernel IR compiles from it. FLX owns it.
- **One kernel IR,** in `kernels`, is the source of every compute kernel that affects results: weak forms, constitutive functions, analytic Fields, implicit tapes, constraint residuals, Network residuals and device models from Verilog-A. Hand-written kernels use the IR's Rust embedding. The IR fixes the order of every floating-point operation and reduction on CPU back ends. `kernels` emits code and asks `wasm-host` to load generated modules; it holds no `unsafe` code.
- **Freeze.** IR v0 holds only the constructs phases 0 and 1 need (element kernels with sum factorization, pointwise constitutive functions with forward-mode derivatives, implicit tapes). It is additive-only once its first consumer compiles against it, except for defects its first consumers find, and freezes at the phase 0 gate once one H¹ elasticity kernel with sum factorization, one constitutive function with forward-mode derivatives and one implicit tape have compiled through both CPU back ends and passed their oracles. Network, constraint and Verilog-A constructs join in the phases that need them.
- **Back ends.** Ahead-of-time Rust with canonical SIMD and Wasm SIMD128 in phase 0. WGSL through wgpu in phase 1 for implicit preview, and for interactive elasticity only if the phase 0 gate measures `CpuIsa` kernels missing the interactive simulation row of 13.3 on the reference laptop (otherwise WGSL elasticity joins in phase 2). Server f64 GPU paths use wgpu on Vulkan with `SHADER_F64` first; a CUDA or HIP back end (CubeCL or another) is reconsidered at the phase 4 gate. WGSL kernels never claim bit-identity with CPU kernels, and every GPU path has a registered CPU path. Render shaders are WGSL and never affect results. FLX owns the kernel IR and its back ends.

### 7.6 `api`, agents, Acts and the human interface

Everything a person or an agent does goes through one API. This section fixes who may call what, how agent contexts are labelled, how effects outside Crucible are approved, how physical devices stay safe, and what the human interface is for.

#### The API and its principals

- **One API** over MCP and native SDKs (Rust, Python, TypeScript, plus a C ABI). Every method is `<group>.<name>` in eight groups: Session, Read, Edit, Evaluate, Inspect, Compare, Propose, Act. Registry, event and archive methods belong to these groups (search, fetch and subscribe are Read; publish, yank, export and release are Act kinds); there is no other group. `api-schema` holds the method catalog, error namespace, codec and client stubs; `api` holds the implementations (12).
- **Error codes** take the form `<family>/<code>` everywhere, so errors and API methods never share a name: `api` errors (`label/write_down`, `act/approval_pending`), Ingot diagnostics (`ing/3001`) and every typed `Failure` variant (`<owner family>/<snake_case>`). AGT keeps the family registry.
- **Local credentials.** A credential held on a device (the desktop keychain, the CLI's session) authenticates without a fresh user-presence proof as the principal `agent:<org>/local/<device>` with `Declared` assurance, never as the human. Human-only methods (`propose.merge`, `propose.endorse_text`, `propose.policy`, `propose.declassify`, `propose.waive`, recipient and clearance changes, and every local write of a payload above `public`) need a WebAuthn user-verification assertion on the approval origin, bound to the call's argument digest and valid for one call. A process acting for the person, such as an agent with a shell tool running the CLI, therefore never merges, endorses, waives or exports as the person.

#### Agents and model contexts

- **Agents work only on branches,** with scoped permissions, cost budgets and clearances. They build, pass every check (the gate predicate, 5.6) and attach Snapshots before proposing. Every agent Proposal is attacked by an independent verifier that reasons over a typed view (IR, semantic diff, check results) with the author's free text elided. The server computes the risk class from the semantic diff; auto-merge applies only to the two lowest classes and only from clean contexts.
- **Context labels.** Every model context carries a label: the join of the labels of every value returned to it, typed or textual. For the hosted crew the context is the conversation. For an external MCP host it is the pair (user, client identity), where the client identity is the registered key of an attested client and otherwise one shared unattested identity per user. Every token family, refresh, concurrent grant and stdio launch of that pair joins one monotone label stored on the server. A context label resets only through `session.reset_context`, which a human confirms with WebAuthn after clearing the host's conversation; the reset is audited and shown in provenance.
- **Taint.** Reading an `ExternalText` value or an instruction-capable image marks the context `instruction_tainted`; reading any untrusted value marks it `data_untrusted`. An attested client counts as clean only while its model requests carry no tool result or user turn other than server-signed Crucible responses and the delegating human's goal, and only when its declared tool list holds no non-Crucible tools; the gateway marks any other context `instruction_tainted`.
- **Write-down.** Every write (edit, Proposal, comment, review, exploration record, Act payload) carries at least the context's label. A write to a destination with a lower confidentiality label fails with `label/write_down` unless a declassification record (5.4) names it. Integrity flags never block a write. Untrusted typed values are returned by handle, and edits cite the handle. A newly registered `Declared` client is cleared for `public` until an administrator raises it to `internal`, and a `Declared` client never clears above `internal`, any `controls`, any `scopes`, or a `DataLicence` that forbids disclosure to processors.
- **Free text.** Free-text spans (comments, doc comments, string literals, description templates, and identifiers neither produced by the compiler nor typed by a person in Crucible's editor) are `ExternalText` when their author is outside the reader's delegation chain or their integrity is untrusted, and values evaluated from them are `ExternalText` too (5.3). `api` returns every `ExternalText` as a handle. An endorsement shows the text verbatim with invisible and bidirectional characters highlighted. A Snapshot is instruction-capable when any visible text, or any geometry made from text, derives from an untrusted `ExternalText` value.
- **Exits.** Tenant bytes leave through `release_data` Acts, through `api` responses to model contexts cleared for them, and through audited local writes. Each exit compares both the confidentiality and the usage parts of the label.

#### Acts and approvals

- **Two phases.** `act.prepare` produces a plan with a digest; `act.commit` runs only after an assigned human Approval of that digest. One plan may carry several effects under one Approval. Act kinds are release, yank, export, order, request a quote, send to a supplier, transfer a program or job to a device, flash a board, start a print, run a rig test, open a bench session, publish a package or passport, and set up a standing release (`standing_release`), whose later transfers are its effects. Waivers, endorsements and declassifications are signature records, not Acts.
- **Requests.** An approval request is a server record assigned to named approvers by Cedar and delivered only to their Crucible inbox; push notifications carry no content, and anyone else who opens it sees "not assigned to you". The approval URL is never returned to a model; `act/approval_pending` carries only a request id. Plans containing invisible characters, Unicode tag characters (U+E0000 to U+E007F), bidirectional controls or zero-width characters are rejected.
- **The approval page.** The server generates one approval page for every device and serves it from the approval origin, which has its own strict content policy and issues WebAuthn challenges bound to the plan digest, request id and approver (AGT). It shows file names derived from item number, revision, format and release tag; a server-rendered thumbnail; a content summary (Items, labels, bytes); the recipient's verification and screening dates; and a diff against the last approved plan of the same kind to the same recipient. The session's purpose appears collapsed below the typed content, as a handle with its integrity flags, and expands only on request; text from an `instruction_tainted` context carries a banner naming the taint sources. A physical-effect plan adds the device serial, location and controller version; what the transfer replaces; the simulation verdicts with the minimum clearance and the count of unsupported semantics; the gateway's offset results with their time; the setup-sheet revision; and the steps the person at the device must take (reduced-speed prove-out, tool-length check, reduced override, propellers off).
- **Three outcomes.** *Approve.* *Return for changes* closes the request with a reason and no penalty: a new plan with a different digest may be prepared at once, and resubmitting the same digest fails with `act/returned_unchanged`. *Deny as suspicious* freezes the session and blocks re-preparing a plan to the same recipients for 24 h.
- **Limits.** Plans prepared in a context with an agent in its delegation chain hold at most three pending requests per delegating human, across all sessions.
- **Plans and local exports.** A release or change-notice plan lists its deliveries to the organization's own systems (ERP, MES, enterprise PLM), whose recipient records are marked internal and verified by two people (5.4); failed deliveries retry under that Approval until the plan expires. Messages outside a release, such as a new-part request into an ERP, stay separate Acts. A person's export to a local folder or local application is an audited local write, not an Act, when the payload is `public` or `internal`, carries no `controls` and no `scopes`, carries only `DataLicence`s that permit the disclosure, and names no recipient record; above `public` it needs the per-call assertion above. Agent-prepared exports, other labelled or controlled payloads and transfers to another organization are export Acts.
- **Approval credentials.** Approvals and signatures need an approval credential: phishing-resistant WebAuthn user verification with a device-bound credential, enrolled under 5.4. Synced (backup-eligible) passkeys sign in but never approve or sign; platform passkeys on macOS, iPadOS and Android are backup-eligible, so those devices approve with a roaming security key whose attested AAGUID is on an allowlist. The machine gateway pins an approver directory of credential public keys. Signature records keep the authenticator data, client data and attestation, so they verify offline.
- **Phones.** Crucible's phone apps offer no approval. In a phone browser on the approval origin, a person may approve release and change-notice Acts that carry no `controls` and no physical effect, using an allowlisted roaming security key over NFC or USB. Physical-effect Acts, `controls` payloads and Part 11 signatures are never approved on a phone.
- **Standing releases.** A `standing_release` is approved by two people over a plan that fixes recipients, channel, schema, label ceiling and expiry; later transfers are its effects and need no further Approval.

#### Physical safety

- **Physical-effect Acts** are the transfer Acts `send_to_machine`, `send_robot_program`, `store_machine_job` (OPC UA `Store` only), `send_print_job` and `flash_device`, and the restricted `start_print`, `run_rig_test` and `bench_session`. This is the only list. Reading machine data is a Read.
- **No remote starts.** Crucible never issues cycle start, resume, jog, `Start` or `StoreAndStart` to any device it transfers to (machine tools, CMMs, robots, lasers, presses and press brakes, furnaces and ovens, placement and harness machines, printers); a person starts them at the device, and `start_print` is the one restricted exception. Agents may prepare transfer Acts; only assigned humans approve them.
- **Transfers.** `send_to_machine` carries a program or recipe, typed by kind (NC, DMIS, bend, placement and cut-list programs, process recipes; MFG owns the kinds), to any device reached through the machine gateway (`apps/machine-gateway`). A transfer never completes a start the device was already waiting for: drip feed is pull-only, streaming only on a request made at the control after the commit, and the gateway refuses with `DncSessionPreArmed` when a data request or DNC session is open at commit. Robot programs transfer only as files into the controller's program store, never through script, dashboard or real-time interfaces. The gateway enforces each connector's allowlist of endpoints and fixed parameter values in its own core, outside the connector, connects outbound only, and keeps its safety functions in its core. A behavioural oracle under wire capture against real servers or vendor simulators shows that no request carries a start semantic; an interface that cannot express a start is necessary, not sufficient.
- **Bench sessions.** `bench_session` is one Approval, with AAL3, over the named person at the device, the device serial (board, printer or machine), the probe or gateway, the payload kind, one Software item or program Item lineage on one branch, a maximum count, an expiry of at most 8 h, and hazard acknowledgements from the Network or machine package. Transfers inside the session need no further Approval but keep every check: read-back, hold in reset, no start, the gateway's offset check and the canonical program hash. The session ends early on expiry, on a hazard change in the Network, or on a payload outside the lineage. Agents never open or extend one, and the approval page lists every transfer in the session afterwards.
- **Firmware.** `flash_device` writes a Software item image to a named board serial through a named probe or bootloader, verifies it by read-back, and leaves the target halted or held in reset; a person at the bench releases it. Its Approval covers the image digest and the target; Cedar may assign the person at the bench to give it; and the approval page shows the board's hazards from its Network (rotating ports, heaters, high voltage) with a step to remove propellers and loads. Client flashing runs only in code that verifies the Approval: in browsers, on the approval origin page after the ceremony, which holds the WebUSB grant and checks the image's SHA-256 against the approved plan; on desktops, in `apps/platform-*`'s flashing service, which verifies the Approval signature against the pinned approver directory as the machine gateway does. The main web origin never holds a WebUSB grant. On a rig under `unattended_safe`, flashing is part of `run_rig_test`.
- **Restricted Acts.** `start_print` exists only for material-extrusion printers whose serial is covered by a site safety record declaring firmware thermal-runaway protection and smoke or heat detection that cuts printer power. It needs an Approval of the job digest plus a confirmation that the build plate is clear, given at the printer within 10 minutes before the start by a printer-side button or a one-time code shown on the printer's display. `run_rig_test` exists only for rigs under `unattended_safe` (7.1) and needs an Approval of the test plan's digest.
- **Manufacturing programs.** A program is approved over MFG's `ProgramSubject` (5.6), bound to a machine class and to nominal tool assemblies by T number, never to a serial or a pocket. The machine class is {machine package digest, controller family, `MotionSemantics` digest, `FileRules` digest}. The controller's software version is instance data, checked at transfer against the package's qualified version range; a version outside it blocks transfer with `ControllerVersionUnqualified` until MFG's controller capture runs for it, and if the recaptured `MotionSemantics` digest is unchanged, the class and every approval persist. A post-processor release that reproduces a program's canonical hash keeps its approval; one that changes it needs a new approval, with the semantic NC diff on the page. The gateway verifies instance data (pockets, measured tools, offsets) at transfer against the setup sheet. A released program may go to any qualified serial of its class through the pull path, on an operator's request at that machine, under its release Approval; a remote push needs its own Approval.

#### The human interface

- **Purpose.** The UI is a viewer, a reviewer and a presentation studio first. People inspect geometry and results, review agent Proposals, steer by pointing, marking up and asking, and present the product; agents do the authoring. A markup or a question becomes a Proposal comment or an agent request anchored to `EntityId`s and a `ViewState`. The UI holds no product state: every product change is an `api` Edit or Propose call.
- **Viewer.** One Rust UI toolkit and one wgpu renderer, native and Wasm, with GPU tiers G1 (native), G2 (WebGPU) and G3 (WebGL2), identical features and declared capacity per tier. Display data are `DisplayPackage`s; camera, culling and selection run locally. Fields paint on the true geometry with stated error.
- **Reviewer.** Proposal review shows feature, geometry, metric, check and source diffs beside renders of both sides, and every review comment anchors to entities and a `ViewState`.
- **Presentation studio.** Crucible produces, from the live model: photoreal renders by progressive path tracing; animation of moving parts from mates and motion studies; exploded views; technical illustrations (fine-line isometric drawings with labelled callouts, hidden-line and section views); simulation visuals (Field colour, deformed shapes, mode shapes, streamlines, and volumetric flow and thermal rendering); shareable web views (read-only, label-checked links that open in any Tier 1 or Tier 2 browser); and generated decks and reports (PDF/A and HTML). Every output is a Snapshot or an ordered set of Snapshots under a pinned `RenderProfile`, so it re-renders identically and updates with the model.
- **Polish bar.** The founder's reference (recorded 12 October 2026) sets the bar: editorial serif typography on a calm canvas, fine-line isometric technical drawings with labelled callouts, real 3D motion with moving parts a viewer can rotate and inspect, and physically convincing effects (fluid, fire, plasma) from shaders. Crucible meets it with its own Rust renderer, on real engineering geometry and simulation Fields; UIX's oracles measure it against path-traced references and frame-time targets (13.3).
- **Steering.** Direct manipulation writes Ingot through ranked edit plans; generated feature dialogs edit parameters; drag preview shows dependents as they update. Review, Present, Design, Simulate, Manufacture and Electronics (schematic and layout) are presets over one workspace, with Review the default. A public `crucible:ui/canvas2d` world lets any package submit retained 2D primitive buffers (lines, arcs, polygons, text, with layer and net ids) that the renderer draws and hit-tests. Tools that compute per pointer move (the router, placement drag with live rule checks) run in the engine process on the drag lane and stream geometry each frame through `api`.

### 7.7 Interop, ecosystem and support

- **Formats.** Open formats are built in Rust as Wasm components generated from their schemas (one EXPRESS code generator for every STEP application protocol and IFC). Licensed translators for proprietary formats run as external tools outside evaluation, and their output enters builds only as External inputs, so anyone can rebuild without the licence. Clean-room readers built under the insight protocol below may replace a licensed translator.
- **Imports** are Ingot expressions over Assets; there is no imported state outside the program. Crucible never replays proprietary feature history; it imports geometry, structure, semantic PMI and metadata, and offers design-intent reconstruction as a reviewed Proposal.
- **Registry.** Namespaces are owned by verified publishers. Packages publish through trusted publishing, or through a person's publish Act approved with an approval credential. Sigstore signatures and SLSA provenance; std and translators reproducibly built; yank but never delete; output-changing releases flagged; a legal-removal path for patent and copyright notices with counter-notice and transparency-log entries.
- **Licensing.** Code is under Apache-2.0 WITH LLVM-exception, documentation CC-BY-4.0, examples and templates MIT-0. External contributions come under the DCO; agent-written commits carry `Assisted-by` and a founder `Reviewed-by`, never `Signed-off-by`, and the licence notice states that portions may not be protected by copyright (counsel's opinion is a phase 0 gate item, 13.1). Company stewardship lasts until a fixed trigger, then a foundation. Linked dependencies may use MIT, MIT-0, Apache-2.0, BSD, 0BSD, ISC, Zlib, BSL-1.0, CC0-1.0, Unicode-3.0 or the OpenSSL licence (the pre-3.0 dual licence). Bundled data and fonts may use OFL-1.1, CDLA-Permissive-2.0, CC-BY-4.0 and Unicode-3.0, each shipped with its notices. MPL-2.0 files may be linked; every distribution (native, Wasm, browser bundle, container) ships MPL notices and a source offer for each MPL file, and modifications are published under MPL-2.0. Operating-system libraries (glibc, the C++ runtime under the GCC Runtime Library Exception, platform frameworks) are linked dynamically and never shipped. Apart from those, LGPL, GPL and AGPL code is never linked; it runs only as an external tool, an External Op or a test oracle, and distributed GPL or AGPL container images ship with their corresponding-source offer. Any other licence needs an RFC (ECO). C and C++ code builds only through the native-code register (12).
- **Releases and support.** Releases ride a 6-week train (nightly, beta, stable) with one LTS release per year supported for 24 months, aligned with Wasmtime's LTS window. Every stable release line has a support period of at least five years: security fixes reach it as separate patch releases, by backport or by a free upgrade that raises no OS or hardware minimum. Regulated extended support: one LTS line every two years is supported for 10 years, with security backports by the steward or retired engines run in sandboxed processes. A regulated cloud deployment mode serves defence and ITAR customers (US-only regions, US-person operations staff for ITAR tenants, controls mapped to NIST SP 800-171 with documentation of FedRAMP Moderate equivalence, support for DFARS 252.204-7012 incident reporting, image retention and forensic access). Medical customers receive a Computer Software Assurance package (intended use and risk tier per capability, vendor oracle results, release impact notes, a supplier quality agreement template and audit rights).

#### Clean-room insight protocol

Crucible studies incumbents to design something far better, never to copy them. Its methods come from the published literature and first principles, and its code never reproduces an incumbent's code.

1. **Two roles.** An *observer* agent may study licensed software, including with REA (github.com/morluto/rea) and decompilers, only on copies the founder holds a licence to examine, in an isolated, egress-denied workspace outside the repository. It writes three things only: behavioural specifications of formats and protocols (record layouts, field meanings, invariants, version differences); test vectors (files the licensed copy produced from Crucible-authored inputs, with expected values); and method analyses describing what an incumbent does, measured from outside, and where it falls short. It never writes code, pseudocode, decompiled identifiers or control flow. *Implementers* are builders that never have REA, the observer's workspace or any decompiled output, and work only from released specifications, vectors, analyses and public documents.
2. **The gate between them.** The verifier role reads each specification and analysis before release and rejects anything that copies expression: decompiled names, code structure, comments, or algorithm descriptions beyond what black-box behaviour shows. Released material enters `oracles/` or the spec through a Proposal, with a signed provenance record (observer run id; method: published document, file analysis, black-box run or decompilation, with the parts touched; tool and target versions; licence reference; counsel's clearance id). Builders' Proposals cite the specification ids they used.
3. **Order of methods.** Published specifications first, then open readers, then analysis of sample files, then black-box observation of the running program. Method insight comes from observing, studying and testing the program while running it normally. Decompilation is used only for interoperability (a file format or protocol), only when the information is not readily available otherwise, and only on the parts needed for it; never on an incumbent's geometry kernel, solver, mesher or CAM strategy, and never to make a substantially similar program. Licence checks and activation are never circumvented, and vendor binaries, vendor sample outputs, artwork and text are never committed.
4. **Legal boundary.** In the EU, Directive 2009/24/EC article 5(3) permits observing, studying and testing a program's functioning to determine its ideas and principles, article 6 permits decompilation only for interoperability under its conditions, and article 8 voids contract terms contrary to those rights. Elsewhere, licence terms that forbid reverse engineering are respected where enforceable, which in the US limits such copies to black-box study. Counsel decides the governing jurisdiction and clears each engagement before any decompilation. Clean rooms do not avoid patents: every resulting reader or method passes counsel's freedom-to-operate review before release, and names formats only by what they are ("reads DWG"), with a non-affiliation line.

#### Adopt, port or study

The licences below were read on each project's own page on 12 October 2026, as the software digest of that date records. Every linked crate still needs a cargo-vet audit and a `deps/approved.toml` entry.

| Use | Software, owner |
| --- | --- |
| Link (permissive) | faer (FLX, PLT); wgpu, winit, AccessKit, Parley, HarfRust, fontations, Taffy (UIX, PLT); Wasmtime (PLT); Salsa, rowan, Cedar (KLN, ING); robust, spade (ANV, MEC); iOverlay, cavalier_contours (ELX, MFG); meshoptimizer (UIX, through the native-code register); Clarabel.rs (ELX, MFG); bempp-rs (FLX); CORE-MATH through `bridges/core-math` (PLT); hypre and PETSc in `bridges/` only, refusing GPL downloads (FLX); egui for internal tools only (PLT) |
| Port, keeping notices | deal.II under its Apache-2.0 WITH LLVM-exception option, libCEED, MFEM, SUNDIALS, SLEPc (FLX); Axom, Geogram (ANV); Algoim, recording its LBNL enhancements grant-back (ANV, FLX); IPC Toolkit (FLX); ngspice's BSD core files only (ELX) |
| Link under MPL-2.0 duties | jagua-rs, the collision engine under MIT-licensed sparrow (MFG); pubgrub, or reimplement it (ECO, ING); acadrust for DWG and DXF, after a provenance audit (ECO) |
| Oracle or benchmark (permissive) | MFEM, deal.II, libCEED (FLX references); Manifold, truck (ANV); Foxtrot, lib3mf, pyNastran, meshio (ECO); PyBaMM, Cantera, Project Chrono, Palace, PyFR, FEBio, Capytaine (FLX, COV, ELX) |
| Oracle or External Op only (copyleft or not allowlisted) | Open CASCADE, Gmsh, fTetWild, Fidget, libfive (ANV); FreeCAD, for behaviour only and never read for code (ANV, MEC); CalculiX, Elmer, OpenFOAM (FLX, COV); KiCad, Freerouting, OpenVAF, VACASK, the ngspice engine (ELX, ECO); PrusaSlicer, OrcaSlicer, OpenCAMLib (MFG); LibreDWG (ECO); OpenSubdiv and OpenUSD under TOST-1.0, which needs an RFC to link (ANV, UIX) |
| Study, through the protocol | Proprietary incumbents and their documented behaviour (blends, constraint solving, PMI on NIST test cases, adaptive roughing, NC verification, analysis benchmarks, PLM workflows, agents in CAD); AI-built clones such as SolidCraft and CADCraft, measured as competitors and linked only after a provenance audit |

### 7.8 Trust and the shared cache

- **Two worker pools.** Untrusted-evaluation workers run Proposal CI from agent and external branches and every External Op, in single-use microVMs (Firecracker- or gVisor-class); they hold no attestation key and write only to a per-Proposal namespace. Trusted builders evaluate only merged Changes of protected branches.
- **Attestation.** A separate attestation service (KLN, packaged by PLT as `apps/attestation`) holds the signing keys and signs (`NodeKey`, `ObjectId`) only for jobs dispatched to trusted builders, bound to workload identity; the host, not the guest, computes output `ObjectId`s.
- **One rule per use.** Release gates and every `SignOff` check accept a cached result only when two independent trusted builders produced the same `ObjectId` (different hosts; for `Portable` operations, different ISAs); otherwise they recompute. Every other shared-cache hit is spot re-executed at a rate weighted by downstream fan-out, and every released revision is re-verified in full after a toolchain or `detmath` upgrade. Two-builder agreement protects against faults, not against a deterministic exploit.
- **Third-party code.** Trusted builders run every Wasm component and package from outside std, `crucible::` and the first-party translators only in single-use microVMs, with the host computing output `ObjectId`s; an OS-process sandbox is never a trust boundary for attestation. A node whose dependency closure contains third-party code is attested only into its tenant's domain, by builders whose hosts serve that tenant alone.
- **External Ops.** An External Op runs on untrusted-evaluation workers, cached by its input hashes plus the host image digest, and its results carry the host's platform class or `Unverified`. A release gate or `SignOff` check accepts an External Op result when two single-use runs on different untrusted-evaluation hosts produce the same output `ObjectId`; each host computes it outside the microVM and records it in an execution receipt signed by a receipt key that never signs shared-cache attestations. A nondeterministic External Op yields `Unverified` results, which meet a gate only when a pinned policy allowance quantifies them (5.6). A desktop may also run an External Op locally in an OS-sandboxed process with egress denied; its results are `Unverified`, at most `Interactive`, never written to the shared cache and never decide a gate.
- **Egress.** Every External Op host, translator host, spawned tool process and stdio MCP server runs with network egress denied, enforced by PLT. A manifest may declare named egress endpoints (a licence server, an MCP server's API host), which an administrator grants per organization and the sandbox enforces by address. A host with any egress grant receives only inputs whose confidentiality label is at most `internal` with no `controls`, unless a two-person grant (5.4) names that host and label.
- **Single host.** Where one host serves both pools (the phase 1 single-node team server), the signing keys live in a TPM, HSM or OS keystore whose signing service accepts requests only from the trusted-builder process, External Ops are not offered, and every release records "single host" in its provenance.
- **Public cache.** Only the operator's registry builders write the global public cache domain, with 2-of-n agreement, and it holds only results whose dependency closure is first-party. Those builders never run third-party code, so publish-time test vectors and acceptance checks of third-party packages run on untrusted-evaluation workers. The hermetic builder for first-party packages never builds third-party ones. The default client trust policy is "own organization plus operator public signers".
- **Encryption domains** are keyed by tenant and canonical confidentiality label; deduplication never crosses them.
- **Signatures** are detached records about content: the identity of a Change, tag, release record or Evidence record hashes its unsigned content, so adding a signature or a timestamp never changes an identity. Every signature record carries an algorithm id. From phase 2, release tags, TUF root and targets metadata, transparency-log checkpoints and provenance are dual-signed with a classical signature plus ML-DSA-87. LMS (as HSS) serves only the steward's software-release signing, with each tree generated in its own HSM at a key ceremony, key replication disabled and the remaining signature count monitored.

## 8. State of the art and parity

Crucible aims to beat the best published method in every component and to leave an incumbent's user nothing to miss. Each tab shows both, in two tables under `## State of the art`.

- For every major component, identify the best published method as of October 2026 (a paper, a standard or a leading implementation), cite it, and state Crucible's choice. The default is to adopt or beat the state of the art. Any deviation needs a stated reason: licence, robustness, determinism, portability or maturity.
- Name the leading implementation to beat (the commercial incumbent where it leads), the benchmark or dataset to measure on, and a performance or accuracy target, labelled as a target.
- Prefer methods that are robust, deterministic, parallel and SIMD- or GPU-friendly, and methods with provable guarantees where they exist.
- **State-of-the-art table:** Component · Best published method · Leading implementation to beat · Crucible's choice · How we measure.
- **Parity table:** Capability · Incumbent and its documented feature (cited from vendor documentation) · Crucible's capability row and phase · Ahead, Equal, Later or Out of scope, with one reason. Comparing documented features is not a benchmark of a commercial product, so a tab that keeps kernel benchmarks internal still complies. Every capability of 13.4's parity floor in the tab's domain has a row, and AI-built clones appear where they ship the capability first.
- Each tab's lead says in one sentence what its users gain over the incumbents, in terms a clone cannot copy quickly.

## 9. Platforms

- **Tier 1** (full product, identical features, every golden product passes): Windows 11 on x86-64 and ARM64; macOS on Apple silicon (current release and two prior); Linux on x86-64 and ARM64 (glibc 2.34 or newer, Wayland and X11); desktop browsers (Chrome and Edge, Safari, Firefox) through Wasm with WebGPU and a WebGL2 fallback.
- **Tier 1 preview.** A Tier 1 target may be a preview target for at most one phase: it runs the same build with identical features, passes the determinism suite and the golden-product checks in automation (real Safari through safaridriver, not a WebKit build), and ships through the beta channel. By the next gate it completes installers, the updater, a published Accessibility Conformance Report with an external audit, and GPU-driver qualification (PLT's GPU oracles pass on every lab device listed for the target). Phase 1 general availability: Windows 11 x86-64, macOS, Linux x86-64, Chrome and Edge. Tier 1 preview in phase 1, general availability at the phase 2 gate: Windows 11 ARM64, Linux ARM64 desktop (a Snapdragon X or ARM64 workstation joins the mid band and GPU lab), Safari, Firefox.
- **Tier 2** (viewing, review, presentation and light editing; CI on every release): iPadOS and Android tablets, ChromeOS through the browser, and phones as viewers. Phone approvals follow 7.6.
- **Tier 3** (community-supported): FreeBSD and other Unix systems. A Tier 3 target joins the canonical class only after it passes the determinism suite.
- **Servers:** Linux containers on x86-64 and ARM64 for team servers and cloud workers; optional GPU acceleration.
- **Parity** means identical features and identical canonical results on every Tier 1 platform, whether computed locally or through remote evaluation on a team server or cloud worker. Capacity and speed may differ and are declared per platform and GPU tier. External Ops run on hosts that support them and are reached remotely from every client (desktops may run them locally as `Unverified`, 7.8); air-gapped installs need a local Linux worker for gate-quality External Op results.
- **Engine placement.** Core crates are OS-agnostic; OS services sit behind `platform-api` traits implemented once per OS family in `apps/platform-*`. The engine runs as a separate process on desktop, a worker in the browser, threads on Android tablets, a worker on iPadOS, or a remote server, and the UI always talks to it through `api`. Native x86-64 builds target x86-64-v2 with runtime dispatch to v3 and v4; ARM64 targets ARMv8 with NEON; SVE dispatch waits until Rust stabilizes scalable vectors. Accessibility goes through each OS's native accessibility API (AccessKit), plus a DOM mirror on the web.
- **Browser memory.** WebAssembly memory never shrinks, so the engine worker keeps a fixed linear-memory cap, set per browser engine from the phase 0 kill-threshold measurements on the low-band machine (8 GiB). Evaluations whose estimated peak exceeds 512 MiB run in a disposable heavy worker that writes results to the OPFS CAS and terminates; above the measured kill thresholds, heavy evaluations go remote. The engine worker recycles too: above a memory threshold, once the session is idle, it hands over to a fresh engine worker that replays the journal. PLT owns one browser memory table with these figures.
- **Browser engine module.** The engine's Wasm is split by profile-guided `wasm-split` into a primary module and lazily fetched secondary modules sharing its memory, and PLT's table holds a per-phase budget for the primary module's compressed size (13.3).
- Every tab includes a `## Platform notes` section, which may read "None beyond PLT's rules" when nothing in the tab differs by target (capacity, a capability missing in a tier, a browser limit).

## 10. Coherence and taste

- **Fewest concepts.** Use the core types. Never invent a parallel abstraction; when two mechanisms do one job, merge them.
- **One name per concept.** Follow section 2 exactly, including the "Never call it" column.
- **Name things by what they are.** No version suffixes, legacy aliases, compatibility shims or "old" and "new" names in code, docs or the spec. A replaced thing is deleted in the same change.
- **Common things simple, advanced things possible.** Sensible defaults for the usual case; power revealed progressively.
- **Explicit over magic.** No silent fallbacks. Every approximation states its error.
- **Composition over special cases.** One general mechanism (Fields driving geometry, queries over provenance, checks everywhere, Approvals over digests, labels through every derivation, pinning for every outside input) beats many one-off features.
- **Errors are guidance.** Every failure is typed, explains why, and suggests a fix.
- **Teach, then specify.** Every new concept gets one sentence of why before its rules, and an example where one helps.
- **One voice.** Present tense, precise, calm. No hype words ("revolutionary", "seamless", "cutting-edge", "world-class", "powerful", "robust" as praise), no exclamation marks.
- **Say it once.** Each fact lives in the tab that owns it; other tabs state the consequence in one line and link to the owner. Summary tabs (the Overview) summarize and link; they never copy contract or tab text.
- **One skeleton.** Every tab follows section 11.
- **Code style.** Ingot: `snake_case` for functions and features, `PascalCase` for types, units on every dimensional literal. Rust: the Rust API Guidelines.

## 11. Research and writing rules

A tab is read start to finish by an engineer who was not in the room. It teaches first and specifies second, and it never reads as the minutes of its own revision.

**Research.** Cite only pages you actually opened; search snippets are not sources. Prefer primary sources. Mark anything unverified with [unverified]. Never invent version numbers, dates, statistics or customer names. Web search quota may run out; fetch known primary URLs instead.

**Skeleton.** Every tab follows this order:

1. **Lead** (no heading), three sentences: what the subsystem is, in words an engineer outside it understands; what that engineer gains over the incumbents; and the one mechanism that delivers it. The lead uses no term it does not define.
2. **Design sections** (`##`, with `###` subsections). The first is guide-level: it opens with a worked example on the canonical bracket or a golden product and explains the model a user meets. Later sections build on it. Each design section opens with one sentence saying why it exists and ends with one capability table: Capability · Contract · Failure · Oracle id · Phase. A Failure cell names the typed failure or reads "None: cannot fail" (or "None: the language cannot express a violation"); it is never a dash.
3. **`## Reference`** (optional): crates, WIT packages, operation and method catalogs, grammars, error-code catalogs and protocol mappings.
4. **`## State of the art`**, with the state-of-the-art and parity tables of section 8.
5. **`## Platform notes`** (section 9).
6. **`## Interfaces with other subsystems`**: one table of what this tab provides: To · What · Types · Phase. What it requires is generated from the other tabs by `extract.py`.
7. **`## Oracles`**: each oracle once: id · verifies · pass criterion (no phase column).
8. **`## Phasing`**: gate contributions only, consistent with section 13.
9. **`## Open questions`**: only questions still open, each with the outside input it waits on.
10. **`## Contract change requests`**: only open requests, or "None".
11. **`## Sources`**: key · title · URL · date opened.

**Style.**

- Tables for items compared on several attributes; numbered lists for sequences; code blocks for Ingot and Rust. Sentences under 25 words where possible. Paragraphs of at most five sentences when explaining a mechanism and at most three elsewhere. Specifics over adjectives; no emoji.
- Spell out every abbreviation at first use in each tab (SSI, DWR, PMI, WIT, MCP, DAE). The Overview carries a glossary generated by `extract.py` from the tabs, one line per term with its owner.
- Citations use readable keys, `[Author Year]` or `[Organization short title]`, at most one per sentence, defined in Sources.
- Decisions are a block of three lines: `**Decision D-<TAB>-<n>:** <decision>.`, then `*Why:* <rationale>.`, then `*Rejected:* <alternatives, each described by what it is>.` Tab codes: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT. Decision numbers are stable and never renumbered; a revised decision states the new decision under its number, and the Decisions log records the revision.
- Review history stays out of running prose: no review finding ids, round numbers, "(revised in round N)", "formerly" or "replaces" anywhere above "Open questions". The Adversarial review and Decisions log tabs hold that history, and `check.py` fails on it elsewhere. Refer to another tab's fact by name, with a link to its section.
- At most two diagrams per tab, marked `[[DIAGRAM: …]]` in drafts.
- **Length:** 9,000 to 15,000 words of prose per tab (ING and ANV up to 17,000). Capability tables, the Reference section, State of the art, Interfaces, Oracles and Sources do not count. Cut repetition, restated rationale, content another tab owns and prose that a table already says; never cut a capability, decision, oracle or source. Targets are labelled as targets.

## 12. Crate map

Crates are small enough that agents working in parallel rarely edit the same one, and layered so that each depends only on crates in its own or earlier rows; apps talk to the engine only through `api`, and PLT's `cargo xtask check-layers` fails any other dependency.

| Layer | Crates (all under `core/` unless noted) | Owner |
| --- | --- | --- |
| Platform | `platform-api` (including the `Monotonic` clock and `Spawner` traits), `detmath`, `simd`, `runtime`, `gpu`, `wasm-host`, `linalg` (canonical linear algebra) | PLT (`linalg` with FLX) |
| Contracts | `base-id` (identities and handles: `GeometryId`, `EntityId`, `BodyHandle`, `InstancePath`, `PortId`), `base-value` (section 5 values and the `Classify` trait Anvil implements for `field`'s `Sampler`), `base-op` (the operation contract: `OpImpl`, `OpCx`, `OpResult`, `Stop`, `Differentiable`, `DeterminismGrade`, `NodeKey`); `cas` | KLN, with every owner of a type |
| Engine core | `kernels` (symbolic expressions, kernel IR and back ends); `field` (`Field`, domains, representations, `Sampler`); `material` (`Material`, constitutive bindings, envelope data); `kiln` | FLX; COV for `material`; KLN for `kiln` |
| Geometry | `anvil-geom`, `anvil-topo`, `anvil-planar`, `anvil-mesh`, `anvil-implicit`, `anvil-ops` (the `Body` enum and dispatch only), one `anvil-op-<family>` crate per operation family; `mech-model` (`Part`, `Assembly`, `Instance`, `Transform`, `CoordSys`) | ANV; MEC for `mech-model` |
| Physics | `flux-forms`, `flux-solve`, `flux-couple`, `flux-opt`, one `flux-op-<family>` crate per operation family | FLX, with COV, MFG and ELX for the operation families they own |
| Language | `ingot-syntax`, `ingot-types`, `ingot-ir`, `ingot-codegen`, `ingot-bindgen` with `ingot-macros`, `ingot-service` | ING |
| Product services | `repo` (Changes as Git commits through gitoxide, refs, merge, diff, live sessions, the status check on any Git host); `plm` (Items, revisions, effectivity, BOM views, change orders, Waivers, policy packages, Evidence records); `trust` (Cedar, labels, signature records and table, recipient records, audit); `engine` (builds a Kiln with every registry, used by `api` and apps) | KLN |
| Surface | `api-schema` (method catalog, error namespace, codec, client stubs and transport traits; depends only on Contracts); `api` (method implementations) | AGT |
| Outside `core/` | `bridges/` (optional FFI: PETSc, hypre, CORE-MATH, GPU vendor specifics); `io/` (translators as Wasm components); `std/` (Ingot packages and first-party Wasm components); `wit/` (`crucible:` packages); `apps/` (`platform-windows`, `platform-apple`, `platform-linux`, `platform-web`, `platform-android`, `ui-toolkit`, `renderer`, `desktop`, `web`, `mobile`, `server`, `cli`, `ci-runner`, `registry`, `attestation` (KLN, packaged by PLT), `headless-render`, `mcp`, `crew` and `model-gateway` (AGT), `machine-gateway` (MFG, packaged by PLT for Linux x86-64 and ARM64 and Windows 11 x86-64), `relay` and `rig-runner` (KLN), `tool-runner` (ECO, PLT)); `sdk/` (`rust`, published as `crucible-sdk`, `python`, `typescript`, `c`; ECO); `oracles/` (a separate, protected Cargo workspace) | per tab |

Rules that go with the map:

- **Domain crates never depend on `kiln`.** Geometry, Physics and Language crates depend on the Platform and Contracts rows and on `kernels`, `field`, `material` and `cas`; only `engine`, `api` and apps see `kiln`. COV, MFG and ELX ship Rust only as operation families in `flux-op-*` crates, as std Wasm components under `std/`, or as `apps/` services; they own no other core crate.
- **UIs link `api-schema`.** The engine process, the browser engine worker and the CLI's local mode link `api`; UI processes, the browser UI module, `sdk/rust` and `apps/mcp`'s client side link only `api-schema`. `inspect.render` dispatches to `apps/headless-render`, a service that links `apps/renderer`; `api` depends on neither.
- **`base` stays still.** After the phase 0 gate, `base-id`, `base-value` and `base-op` change only by a contract ruling.
- **Unsafe code** is allowed only in `simd`, `gpu`, `wasm-host`, `bridges/` and `apps/platform-*`; everything else is `forbid(unsafe_code)`.
- **Native code.** C and C++ build only through the native-code register in `deps/approved.toml`. Each entry records why no Rust crate serves, its targets including wasm32 (built with clang and a pinned wasi-libc sysroot, or excluded with the Rust fallback named), its compile flags (`-ffp-contract=off` where results could change), whether it affects results (only CORE-MATH may), and its fuzzing. Until every `detmath` function's Rust port passes the CORE-MATH oracle, `detmath` may depend on `bridges/core-math`, which wraps CORE-MATH's C build in safe functions.
- **Portable core.** Crates under `core/` never use `std::time::{Instant, SystemTime}`, `std::thread`, `std::fs`, `std::net`, `std::process`, `std::env`, or `tokio` beyond `tokio/sync`; they take clocks, tasks and storage from `platform-api`. Their unit tests run on wasm32 in headless Chrome on every merge.
- **Names that must not collide.** PLT's pool priority is `PoolLane { Drag, Foreground, Background }` and its file durability `WriteDurability`, so `PriorityClass`, Kiln's durability and the fidelity `Interactive` keep their meanings.

## 13. Roadmap, program plan, performance targets and phases

Crucible ships in phases, and each phase ends at a gate that real, made and measured products must pass. This section fixes the gates (13.1), how agents build toward them (13.2), the performance targets (13.3), and the phase of every capability that several tabs share or that an incumbent's user relies on (13.4).

### 13.1 Phases and golden products

| Phase | Theme | Gate |
| --- | --- | --- |
| 0 | Foundations | The phase 0 gate list below |
| 1 | Wedge: code-CAD and 3D printing | GP1 machined bracket: designed, toleranced, simulated and released in Crucible; made by a reference shop from Crucible's STEP AP242 with semantic PMI and drawing, using the shop's own CAM; measured by external metrology against Crucible's tolerances; proof-loaded. GP1-class parts in the part-level rebuild corpus meet ANV's phase 1 target. GP2 topology-optimized lattice bracket in metal laser powder bed fusion: optimized and verified in Crucible; built from Crucible's 3MF with the bureau's build-preparation software; measured externally; proof-loaded |
| 2 | Mechanical depth | GP3 gearbox, including machined parts cut from Crucible-generated programs; GP4 welded frame with sheet-metal guards, including measured weld distortion; one material-extrusion part sliced by Crucible and sent through `send_print_job` to an open-firmware printer (Klipper or RepRapFirmware) |
| 3 | Product breadth | GP5 molded enclosure with its PCB, including measured warpage and drop response; the board fabricated and assembled from Crucible outputs alone |
| 4 | Full multiphysics | GP6 drone, validated against flight, dynamometer and thermal test data |
| 5 | Scale | GP7 MEMS accelerometer; GP8 bolted steel platform round-tripped through IFC 4.3 with a structural check; GP9 crash box |
| 6 | Aerospace and electrification | GP10 composite wing box; GP11 CubeSat; GP12 EV battery sub-pack with BMS, harness and charger |
| 7 | Marine, buildings, medical and soft goods | GP13 workboat hull; GP14 timber pavilion (building product, IFC export); GP15 bone plate (ASME V&V 40 credibility); GP16 sewn pack (soft goods) |

**The phase 0 gate.**

- The determinism suite is green on the representative set and nightly on every Tier 1 target; unit errors fail to compile; kernel IR v0 is frozen (7.5).
- Every user-visible name (Crucible, against Atlassian's mark; Ingot and `.ingot`; Anvil; Kiln; Flux's replacement; every crate, package and CLI name) is cleared in classes 9 and 42 or replaced before any operation version or WIT package freezes. Internal crates carry the `crucible-` prefix on crates.io, and the SDK names are reserved on crates.io, PyPI, npm, Maven Central and NuGet.
- Counsel's written opinions are delivered on: claims 1, 6, 11 and 16 of US 12,229,885 B1 (inventor Alyn Rockwood, assignee an individual; Zoo's engine overview describes a related method), covering the CPU and GPU paths and pending continuations, with confirmation that phase 1 SSI avoids the claimed comparison; authorship of agent-written code and the DCO (7.7); the standard thread, clearance-hole and fastener series tables std may ship; and the governing jurisdiction and a template engagement clearance for the insight protocol (7.7).
- A freedom-to-operate search covers every phase 1 code path in chains A to D (13.2): SSI, Booleans, blends, tessellation and implicit lattice meshing; Changes, branches, merge and live sessions; the Proposal and review flow; and the STEP AP242 and 3MF writers. Each later gate adds the same search for its phase's new capabilities, and the phase 1 gate adds counsel's opinion on the adaptive-clearing and trochoidal-slotting claims MFG names.
- ISO has answered the request to distribute the STEP layer-1 build generated from its schemas; if it refuses, the steward publishes the generator and the expected binary hash for each pinned schema hash, so any holder of the schema generates bit-identical layer 1 locally and every `NodeKey` matches.
- GP2's alloy, machine, print bureau, build-preparation software and accepted 3MF extensions are fixed and recorded in this section.

**The phase 1 gate** adds counsel's product-liability assessment for hosted and commercial distributions (Directive (EU) 2024/2853 and US law), with the release information and terms it requires, before general availability.

**Validation.** Every physical gate states its replicate count (at least three articles, or a GUM uncertainty budget for a single article), measures as-built geometry and material coupons from the same lot, and keeps validation data out of calibration. Solid-mechanics validation follows ASME V&V 10, and the validation metric follows V&V 20: comparison error E = S − D, validation uncertainty u_val = √(u_num² + u_input² + u_D²), and model-form bound |E| + k·u_val at validation points, with α_mf = 0.05 and k = t₁₋α_mf/2 at ν_eff degrees of freedom from Welch–Satterthwaite over the three uncertainties; one-sided calibrated bounds convert with z₁₋α. Extrapolation inflation is a declared function of normalized distance to the nearest validation point. Each validation plan places sensors on the quantities the gate's checks decide, so its validated response quantities (5.1) cover them.

**Phase 1 validation.** Before the run build is tagged, a validation campaign on separate specimens of GP1's alloy and GP2's process (notched and filleted plates; printed strut and lattice coupons) measures surface strain with gauges and stereo digital image correlation sampled at the regularization radius, with at least three replicates. Its response quantities are regularized surface peaks at fillets (linear elastic) and localized strut stress, and its bounds govern the GP1 and GP2 releases. GP1 and GP2 then add a proof-load test on every article, with strain gauges in each checked region and a load–displacement record, as held-out confirmation: each check also predicts its gauge functional, so agreement is judged like for like.

**Dynamic gates.** GP5's drop response and GP9's crash box compare regularized functionals: acceleration through a declared channel filter, energy absorbed, mean crush force over a displacement window, and the maximum of a time-averaged strain. Buckling-sensitive cases compare ensemble statistics over seeded geometric imperfections (principle 4).

**Reproducing the release.** The phase 1 gate release reproduces the exported STEP AP242 and 3MF files of the tagged run build bit for bit (equal `ObjectId`s), or shows equal `GeometryId`s and definitional attributes with a reviewed diff of the rest; otherwise the physical run repeats. "Released in Crucible" is satisfied through `api` and the CLI, so a UI slip moves UIX's own target and not the gate. Golden products 7 to 16 are proposals, each a separately funded program started only with a physical test partner and an approved plan.

**Scope.** In: products made of parts, assemblies, boards, cables and software items, from MEMS to ships; building products and structures (prefabricated, steel, timber), exchanged with BIM tools through IFC 4.3; MEMS layout and chip-package design through GDSII and OASIS. Out: whole-building authoring (spaces, zones, whole-building energy); integrated-circuit logic layout; film and animation production; classified information under any national security classification system, for which no deployment mode is accredited.

### 13.2 Program plan

Crucible is built by agents. One human, the founder, directs the program; Claude orchestrates agent work against the oracles; outside firms make, measure and advise where the physical or legal world requires a person. Phases end at their gates, never on a date, and no plan figure counts people or engineer-years.

**Roles.**

- **Founder.** Approves each phase's scope and budget at the previous gate, signs each golden product's pass/fail criteria before builders start on it, approves every Act (7.6) and every Waiver, and decides anything that changes money or scope.
- **Orchestrator.** Claude plans the work, opens work items, runs reviews and rulings, and keeps this contract and the tabs current.
- **Agent roles.** The *oracle* role writes a phase's contract crates and oracles and locks them before any builder works on the capabilities they verify; builders never write or edit `oracles/` or contract crates. *Builders* implement against them. The *verifier*, independent of both, checks every oracle against its capability row and an independent source, and attacks every builder Proposal (7.6). The *observer* studies incumbents under the insight protocol (7.7), and builders never see its workspace. An adversarial review of the spec runs before each gate.
- **Outside firms.** Retained counsel for freedom-to-operate, trademark, authorship and reverse-engineering clearance. Signed phase 0 agreements with a reference machine shop (including time on each controller family's physical controls in program-test mode), a metrology lab, a metal powder bed fusion bureau and a proof-load test lab. The bureau agreement includes a file-acceptance test of its build-preparation software on three files: a 3MF with the Beam Lattice extension, a 3MF of triangles at a stated chordal error, and a sliced build where the software takes one.

**Budget.** Each phase carries one budget, approved by the founder at the previous gate: agent compute, cloud CI, rented GPU and device-farm time, physical golden-product runs with replicates and one re-run, validation specimens, metrology, proof loads and counsel. A scope addition to an open phase needs the same approval as a gate change.

**Build program.** PLT owns how Crucible itself is built against its oracles.

1. **Interface first.** For each work item, the oracle role writes a contract crate, `<crate>-contract`, with the public types and signatures the oracles call and `unimplemented!()` bodies, and the verifier checks it against the tab's Rust surface. Builders implement it and may not change it; a signature change is a Proposal by the oracle role. Oracles bind, in order of preference, to `api` methods, the CLI and file formats; then WIT worlds; then contract crates. `oracles/` is a separate Cargo workspace that depends on contract crates by path, so builder code never breaks its build.
2. **Oracle first.** A work item opens only when its oracle ids exist in `oracles/` as executable checks written by the oracle role and passed by the verifier. Chain A and B oracles exist before chain A and B work starts, and every phase 1 oracle exists before the physical dry run; each gate reports oracle coverage per crate.
3. **Runner classes.** Every oracle declares one runner class: `cpu-ci`, `browser-ci`, `gpu-lab`, `device-farm`, `physical` or `founder`. Agents run every class except `physical` (outside firms) and `founder` (sign-offs); `gpu-lab` and `device-farm` run on rented hardware.
4. **Held-out splits.** Builders' sandboxes have no network route to public corpora; held-out results reach a builder only as one aggregate verdict per work item per day; and visible and held-out runs execute in byte-identical harnesses with case order and count padded to a fixed size (principle 6).
5. **Corpora.** Agent-built corpora and reference data enter `oracles/` only through a Proposal the verifier passes, and agree with an independent source (MPFR, Open CASCADE, lib3mf, MFEM, deal.II or libCEED, CAx-IF data). References for error-estimator calibration come from an independent code on fitted, curved high-order meshes, accepted only when a p-sequence shows exponential convergence and its Richardson spread is below 10% of the bound; each records its code and mesh hash.
6. **Taint.** From phase 0, every agent context that reads third-party source, a web page or a paper is `instruction_tainted`. Tainted contexts write only to their own branches, and their Changes to `core/`, `apps/`, `oracles/`, `deps/` or CI configuration need the founder's Approval with the taint sources listed. A cargo-vet audit written by an agent counts only as `agent-reviewed`, which implies `safe-to-run` in sandboxed CI and never `safe-to-deploy`; `safe-to-deploy` comes only from imported human audit sets or a quarantined review whose model sees the crate source alone, has no tools and returns a typed verdict the founder approves per crate version. Adding a dependency to the engine closure needs the founder's Approval.
7. **Work items.** A work item is `{ crate, capability row, oracle ids, held-out split, budget }`, run through AGT's Plan and Proposal machinery against Crucible's own repository, with the verifier role. Until that machinery ships in phase 2, phases 0 and 1 run the same `WorkItem` record over Git, with the same oracle, verifier and taint rules. Crucible's own repository runs in single-person mode (5.4).

**Phase 1 scope.** Phase 1 builds only what GP1 and GP2 need, plus the presentation floor of 13.4. Deferred to phase 2 or 1.x release trains, with contracts and oracles unchanged:

- the Ingot code generator, Perceus and the state-machine transform (the interpreter executes Ingot);
- cluster-DAG streaming, the visibility buffer, compute rasterization, k-buffer transparency, the variant grid, presence and follow mode (one forward renderer on every tier), and the GUI's own sketch tools (agents and Ingot sketch in phase 1);
- the single-threaded web product build, its Op worker and embedded viewers (phase 1 refuses to start without cross-origin isolation and says why; the single-threaded wasm32 build stays in the determinism suite);
- cloud SaaS, live sessions, encryption domains, transparency logs and the hardware runner (phase 1 runs a single-node team server with branches, merge, Proposals, Cedar policies and a signed append-only audit log);
- CAM, posts, stock simulation, slicing and nesting (phase 1 keeps DfAM checks, 3MF production output and cost);
- the public registry and trusted publishing (phase 1 uses a signed first-party package index);
- Bayesian exploration, the hosted crew, quarantined extraction and the TypeScript SDK (phase 1 ships `api` over MCP, Rust and Python SDKs, Propose with CI report, risk classes and three roles: detail designer, simulation engineer and verifier);
- guaranteed estimators on cut cells, GPU `SignOff` paths and CUDA back ends;
- SubD, lofts, non-circular sweeps, twisted or scaled extrusions with general NURBS intersections and offsets, and GPU sampling for SSI (7.1);
- the browser sandbox for third-party Wasm components (browsers evaluate them remotely, 7.4);
- inherent-strain distortion prediction (13.4), the shifted boundary method and, unless the phase 0 measurement needs it, WGSL elasticity (7.1, 7.5);
- restricted-party screening of recipients inside the organization;
- TUF delta updates (full signed packages suffice), Flatpak, AppImage, reproducible builds beyond Linux and wasm32, and telemetry (phase 1 ships MSIX, a notarized DMG, deb and rpm).

Electronics before the phase 1 gate is limited to a circuit-simulation research track. Phase 1 supports a desktop install without a team server: it designs, simulates, evaluates, presents and exports locally (audited local writes, 7.6), while Proposals, releases and every Act need a team server.

**Critical path for phase 1.** Each chain runs in the order shown.

- **Chain A (geometry):** exact predicates → certified SSI on GP1's surface set → Booleans → fillets and shells → GP1 features and drawing → STEP AP242 → shop machining → metrology and proof load.
- **Chain B (physics):** kernel IR → CPU back ends → immersed elasticity with DWR (dual-weighted residual) error estimation → topology optimization and homogenization → implicit lattice → strut calibration coupons printed and measured → 3MF → build → measurement and proof load.
- **Chain C (interface):** toolkit risk spike (including the DOM mirror for a 1,000,000-row tree in Chrome, read by NVDA within 1 ms per frame) → toolkit core, forward renderer and picking → review: semantic diffs, markup anchored to entities, sections and Field colour → presentation: technical illustrations, exploded views, shareable web views and generated reports → steering: generated feature dialogs, drag preview, Insert Instance and Add mate → drawing editor → keyboard-complete workflows with accessibility oracles green.
- **Chain D (release):** single-node team server with Cedar and the audit log → microVM Proposal CI → the approval page with WebAuthn and the release and export Acts → used end to end in the physical dry run.

**Milestones through phase 1, in order.**

1. `detmath` core functions; combinators; CAS and Kiln core; Ingot parser, types and interpreter; kernel IR v0, additive-only; predicates, analytic geometry, topology and `EntityId`; CI on every Tier 1 CPU target.
2. Analytic SSI and Booleans; tessellation and `DisplayPackage`; CPU kernel back ends; H¹ elements, CG and manufactured-solution tests; toolkit core and forward renderer; counsel's opinions received; kernel IR v0 frozen once three consumers compile against it; the phase 0 gate, judged per crate on the corpus that exists.
3. Fillets, chamfers, shells, holes, patterns, sketches; drawings and GD&T; immersed elasticity, DWR, p-multigrid; topology optimization, homogenization, implicit lattices; strut calibration coupons; STEP AP242 and 3MF writers; team server; Propose and review; presentation outputs; the approval page and release Acts.
4. Physical dry run of both gates with interim outputs, and the phase 1 validation campaign on separate specimens (13.1).
5. Hardening, keyboard-complete workflows, accessibility, Tier 1 preview targets.
6. Run build tagged; the GP1 and GP2 articles are made from its exports.
7. GP1 and GP2 physical runs with proof loads, with one re-run budgeted.
8. The phase 1 gate.

### 13.3 Performance targets

PLT owns these targets. The reference laptop is fixed: Intel Core Ultra 7 258V (8 cores, 8 threads, AVX2, Arc 140V GPU), 32 GB, Windows 11 and Ubuntu LTS, measured at 1920×1080 render resolution. Because the processor's sustained throughput depends on chassis and power, PLT names the exact laptop model (chassis, panel and its refresh rate, firmware version) at the phase 0 gate and fixes the measurement conditions: AC power, one named OS power mode, logged package power, thermal soak, ambient temperature, pinned OS builds, kernel and GPU drivers, and a calibration workload that discards a session when it drifts. PLT also names a reference workstation (a 16-core desktop with a discrete GPU) at the phase 1 gate and a rented 64-core server class for the server rows. Each row names its benchmark file in `oracles/plt/`, cache state, render resolution and percentile, and has held-out variants (principle 6). Other operating systems' mid machines land within 1.5× of each row. A row blocks beta promotion on its reference machine from the phase in its last column; before that phase it is a measured target. All figures are targets.

| Row | Native | Browser | Phase |
| --- | --- | --- | --- |
| Cold start / warm start | 1.5 s / 0.6 s | first visit 8 s at 50 Mbit/s, with at most 25 MiB of brotli-compressed primary engine module; warm 2.5 s | 1 |
| Shareable web view | | a read-only GP1 view opens to its first shaded frame in 3 s at 50 Mbit/s on the browser mid machine | 1 |
| Selection highlight | 16 ms | 33 ms with WebGPU (asynchronous readback), or a CPU ray cast | 1 |
| Orbit | 60 fps at 5M visible triangles at up to 2.1 MP render resolution (upsampled during motion; edges, overlays and text at native resolution; still frames accumulate at native resolution) | WebGPU 30 fps at 5M or 60 fps at 2M visible triangles; WebGL2 30 fps at 2M visible triangles and at most 1,000 distinct Parts | 1 |
| Orbit of implicit Bodies | 30 fps at up to 2.1 MP render resolution | 30 fps with WebGPU | 1 |
| X-ray views | 30 fps | | 2 |
| Animation of moving parts | 60 fps playback of a mate-driven motion study at 5M visible triangles on G1 | 30 fps with WebGPU | 2 |
| Photoreal still | A 1920×1080 path-traced image of a GP-class assembly reaches mean ꟻLIP ≤ 0.05 against a converged reference within 30 s on G1 | within 90 s with WebGPU | 2 |
| Scene capacity at 60 fps | G1 100,000 Instances; 1,000,000 on the high band from phase 4 (adapters reporting `compute_raster`; others declare a measured capacity) | G2 20,000 Instances; G3 10,000 Instances of at most 1,000 distinct Parts | 2 |
| Drag preview | The dragged feature plus as many dependents as Kiln's cost estimate fits in 80 ms (at least the next 10 when cheap) within 100 ms; later dependents show as `Proxy` where the change is affine on them, otherwise `Stale` | same rule, 200 ms, measured on the threaded build | 1 |
| Rebuild after an early edit | `SignOff`: 2 s on a named GP1-class benchmark of prismatic features. `Interactive`: p90 ≤ 10 s on a 200-feature corpus from the licence-filtered ABC subset and Crucible's procedural generator | 3× native | 1 |
| Certification after an early edit | The certification nodes of 7.1 finish at p90 ≤ 30 s on the same 200-feature corpus | 3× native | 1 |
| Interactive simulation update | 1 s for linear static elasticity up to 100,000 DOFs at p = 2, warm-started, on G1, including the error estimates of up to five checked goals | 2 s with WebGPU; 6 s CPU-only; remote above that | 1 |
| `SignOff` linear static at scale | 10M DOFs at p = 2 on an immersed GP1-class part, recertified, under 10 minutes on the reference workstation; 50M DOFs on the 64-core server from phase 3 | remote | 2 |
| Incompressible flow throughput | 10M cells, laminar steady to residual 10⁻⁶: time per iteration within 2× of OpenFOAM on the same CPU; from phase 4, on a `Gpu` class with CPU certification, a speed-up over the canonical CPU run at least half the one Ansys publishes for Fluent's native GPU solver on the same case family | remote | 3 |
| Open a 1,000-part assembly from warm cache | 10 s, with a coarse view in 2 s | 20 s | 2 |
| Input to photon, p99 | 50 ms at 60 Hz; 33 ms at 120 Hz, measured on the macOS mid machine if the reference laptop's panel is 60 Hz | same | 1 |
| Memory | Under 1 GiB with GP1 open; idle 300 MiB with the GPU device created lazily. Memory is the sum of the peak resident sets of the UI process, the engine process and any sandbox workers, plus GPU allocations the adapter reports, sampled every 100 ms | per PLT's browser memory table | 1 |
| Installed size | 400 MiB | | 1 |
| Flux CPU throughput (CEED bake-off), `CpuIsa { X86_64V3 }` with FMA, against MFEM and libCEED built for the same ISA | BP3 and BP5 at p ≥ 3: at least 50% of MFEM or libCEED; memory-bound cases (BP1, BP2, p ≤ 2): at least 80% | | 1 |
| Flux CPU throughput (CEED bake-off), canonical class | BP3 and BP5 at p ≥ 3: at least 25% of MFEM or libCEED in `CpuIsa`; memory-bound cases: at least 70% | | 1 |

The ABC subset holds only documents for which the Onshape API shows a Free Plan owner, a creation date on or after 7 August 2018 and no LICENSE tab; ECO keeps that licence proof per model, and models without it are not copied. Its prismatic subset holds the models all of whose faces are planes, quadrics, tori, or extrusion or revolution surfaces of lines, arcs and conics.

### 13.4 Shared phases and the parity floor

A capability that several tabs phase has one phase, set in the first table below; a capability that an incumbent's user relies on has a latest phase, set in the second. The owner's capability table specifies each row (contract, failure, oracle); every other tab states the phase in one line and cites this section.

Phasing rules:

- A shared capability lands in the phase of the first gate that needs it. One that no gate needs takes the parity floor's phase if it has one, and otherwise the latest phase any tab proposed. A tab may phase a parity-floor capability earlier, never later.
- Nothing is phased before its prerequisites. A capability row that names another tab's capability carries a `Requires:` entry naming that row, and `check.py` fails a row whose phase is earlier than a row it requires.
- A tab that needs a different phase files a change request.

| Capability | Phase | First gate that needs it | Owner | Also phased in |
| --- | --- | --- | --- | --- |
| Modal analysis and linear buckling: Lanczos and LOBPCG eigen-solvers | 1 | GP2 strut buckling | FLX | COV |
| As-built lattice strut calibration for metal powder bed fusion: strut diameter, waviness and strut-scale Materials | 1 | GP2 strut checks | MFG | COV |
| Statistical basis: normal and Weibull one-sided tolerance limits (CMH-17, MMPDS), with replicate counts per strut diameter and angle large enough for a B-basis value | 1 | GP2 strut checks | COV | MFG |
| Planar (plane stress, plane strain, generalized plane strain) and axisymmetric elasticity and thermal models | 1 | None; parity floor | FLX | COV |
| Additive distortion by inherent strain: layer activation of part and supports, baseplate cut, support removal and stress relief | 2 | None; MFG's metal powder bed fusion compensation | FLX | COV, MFG |
| Weld distortion at structure scale, by inherent strain | 2 | GP4 measured weld distortion | MFG | COV, FLX |
| Gear, bearing and shaft ratings (ISO 6336, ISO 281, DIN 743 or the FKM guideline) and loaded tooth contact analysis | 2 | GP3 | COV | MEC |
| Fitted FEM on conforming curved tetrahedra, with mortar contact | 2 | GP3 validation of loaded tooth contact | FLX | ANV |
| Linear dynamics: prestressed, damped and gyroscopic eigenproblems; mode-superposition harmonic, random and response-spectrum response; damping models | 2 | None; COV rotordynamics and vibration | FLX | COV |
| Symmetry, antisymmetry and cyclic-sector reductions, with cyclic modal analysis by harmonic index | 2 | None; parity floor | FLX | COV |
| Conjugate heat transfer, laminar and natural convection | 3 | GP5 | FLX | COV, ELX |
| Injection moulding: level-set fill front, pack, cool and warpage | 3 | GP5 measured warpage | MFG | COV, FLX |
| Short-fibre orientation transport and its effect on warpage | 3 | GP5 measured warpage | MFG | COV |
| Explicit dynamics for drop | 3 | GP5 drop response | FLX | COV |
| Indefinite Helmholtz solvers (complex LDLᵀ, shifted-Laplacian multigrid) for acoustics | 3 | None; COV linear acoustics | FLX | COV, ELX |
| Elastohydrodynamic lubrication | 3 | None | FLX | COV |
| Stability lobes and chatter prediction | 3 | None; GP3's programs use tool-library cutting data | MFG | COV |
| Conjugate heat transfer, turbulent (RANS) | 4 | GP6 thermal test data | FLX | COV, ELX |
| Electro-thermal coupling: Joule heating with temperature-dependent resistivity | 4 | GP6 thermal test data | FLX | ELX |
| 3D quasi-static RLCG extraction: partial inductance, AC resistance and capacitance, exported as passive SPICE subcircuits | 4 | GP6 controller hot loop | FLX | ELX |
| Full-wave extraction for signal and power integrity | 4 | None | FLX | ELX, COV |
| Plane-pair cavity model for power-distribution impedance | 4 | None | FLX | ELX |
| Rotor aerodynamics: blade-element momentum, vortex particle method and rotating-domain flow | 4 | GP6 rotor thrust and torque | FLX | COV, ELX |
| FMU import (model exchange, co-simulation and scheduled execution) | 3 | None | FLX | ELX, ECO |
| FMU export and SSP | 4 | GP6 | FLX | ELX, ECO |
| Battery cells: equivalent-circuit and SPMe models | 4 | GP6 pack voltage | ELX | COV, FLX |
| Composite laminates: zone-based plies, kinematic draping and laminate analysis | 4 | GP6 | MEC | ANV, COV |
| Weld simulation at joint scale, transient | 4 | None | MFG | COV |
| Solid-state phase-transformation kinetics (JMAK, Koistinen–Marburger) | 4 | None; transient weld simulation | COV | MFG |
| Battery cells: swelling and stack pressure | 4 | None | ELX | COV |
| Battery cells: Doyle–Fuller–Newman (P2D) | 5 | None | FLX | COV, ELX |
| Free-surface and multiphase flow beyond mould filling | 5 | None | COV | FLX |
| Explicit dynamics with erosion for crash | 5 | GP9 | FLX | COV |
| Sheet forming simulation and springback compensation | 5 | None | MFG | COV |
| Constitutive draping and composite cure simulation | 5 | None | COV | MFG |
| Battery abuse mechanics: crush, penetration and crash screening | 6 | GP12 | ELX | COV |
| Casting simulation: mould filling, solidification and porosity for sand, high-pressure die and investment casting | 6 | None | MFG | COV |

Three neighbours keep their own tab's phase: board thermal from part power Fields (ELX, 3), press-brake bend allowances (MFG and COV, 2) and distortion compensation for metal powder bed fusion (MFG, 2).

**The parity floor.** These capabilities close workflows that users of the incumbents and of AI-built clones rely on. Each lands no later than the phase shown.

| Phase | Capability | Owner |
| --- | --- | --- |
| 1 | Standard thread and clearance-hole designations computed from the ISO 68-1, ISO 965-1 and ASME B1.1 formulas, explicit diameters and fits, needing no licensed table | MEC |
| 1 | DXF write of drawing sheets and planar sections; IGES read | ECO |
| 1 | Sketch edits as source rewrites: trim, extend, split, sketch fillet and chamfer, offset, use edges | MEC |
| 1 | Insert Instance and Add mate as generated dialogs with selection-driven frames | UIX |
| 1 | Generative design for additive and unrestricted methods (`std::mech::generate`), kept interfaces exact and toleranced | MEC |
| 1 | Analyst idealizations: rigid and distributing remote points, point masses with rotary inertia, grounded and two-point springs | FLX |
| 1 | Presentation: technical illustrations, exploded views, Field and deformed-shape animation, shareable web views, generated reports (PDF/A and HTML), and a discretization view (octree and cut cells, degree, reduced regions) | UIX |
| 2 | Presentation: photoreal progressive path tracing on G1 and G2 with a CPU path in `apps/headless-render`; animation of moving parts; generated decks; glTF export | UIX |
| 2 | In-context design through context pins to a past Change of the assembly; path mates; reference images in sketches; sheet metal, kinematics and motion studies | MEC |
| 2 | DXF and DWG read and write | ECO |
| 2 | Toolpath editing (trim, delete passes, reverse, reorder, relink, change tool) on stable pass keys; an engagement-limited roughing strategy that ships whatever the patent opinion; parameterized machine templates | MFG |
| 2 | Review routing (stages, quorum, conditions) and approval delegation; shape-similarity search with exact duplicates by `GeometryId` | KLN |
| 2 | Side-by-side EBOM and MBOM editor; family table editor | UIX |
| 2 | Generative design for milling, two-axis cutting and casting, with fitted implicit-to-B-rep conversion | MEC, ANV |
| 2 | Bushings, fastener and spot-weld connectors; immersed tied interfaces with automatic interface detection; load-case combination and envelopes; stress linearization; submodeling; `Preview` geometry surrogates trained on a repository's own results; shell-thickness sizing | FLX |
| 3 | Quality records (complaints, corrective and preventive actions, audit findings) or a named connector to an external quality system; mass change across repositories; foreign native CAD files as Document Items with reference graphs | KLN |
| 3 | Vendor controller kernels as `MotionSemantics` sources | MFG |
| 3 | Belt and chain couplings | MEC |
| 3 | Imported Nastran and Abaqus decks that run, with BDF, DMIG and OP4 export and LS-DYNA keyword read | FLX, ECO |
| 3 | Fan curves, flow resistances and laminar rotating frames; laminar steady flow adjoint | FLX |
| 3 | Native PSpice and LTspice dialects, with 90% of the vendor model corpus native-qualified; mated board-to-board connector checks | ELX |
| 4 | RANS rotating frames, sliding interfaces and RANS adjoint; S-parameter goals with adaptive stopping | FLX |
| 4 | Modelica source import of a declared subset into Networks | ECO |
| 4 | Single-phase hydraulic and coolant element libraries; ideal-switch transient analysis; interface compliance kits (DDR, PCIe, USB) | ELX |
| 5 | Floquet ports, Bloch-periodic unit cells and finite arrays; mixing-plane interfaces | FLX |
| 5 | Charged-particle tracing, particle tracing in flows and free-molecular flow; pressure-equipment design by analysis (ASME VIII-2 Part 5, EN 13445-3) | COV |
| 5 | Two-phase and pneumatic fluid element libraries | ELX |
| 6 | Ply-shape, ply-drop and stacking optimization | FLX, MEC |

## 14. Ruling log, round 1 (contract change requests from the first drafts)

Sections 14 to 18 are history: they record how each version was ruled, in the names of their time, and bind nothing that sections 1 to 13 do not state.

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

## 18. Ruling log, round 4 (third review)

Version 7 rules on the 111 third-review findings that target the contract and on the founder's four directions of 12 October 2026. Findings that target only tabs go to the round 4 packets, as do the tab halves of the findings below. "Revised" means accepted with a different fix; "tab only" means the contract already states the rule and the fix is the tab's.

| Finding | Ruling |
| --- | --- |
| FD-1 agents author, people steer, view and present | Accepted (1, 3 principle 2, 7.6, 13.2, 13.3, 13.4): agents and code author the program; people steer by pointing, marking up and asking, review, approve and present. The UI is a viewer, reviewer and presentation studio first, held to the founder's polish reference; presentation outputs are Snapshots under pinned `RenderProfile`s. Every rule that protects people stands. Chain C leads with review and presentation, the GUI's own sketch tools move to phase 2, and photoreal path tracing moves from phase 5 to phase 2. |
| FD-2 reverse engineering for insight | Accepted (7.7, 13.1, 13.2): the clean-room insight protocol with observer and implementer roles, provenance records, the order of methods and the legal boundary; decompilation only for interoperability; clean rooms do not avoid patents. Counsel's jurisdiction opinion joins the phase 0 gate. ECO's rule that Crucible never reverse-engineers a proprietary format is replaced by the protocol. The adopt, port or study list comes from the round 4 software digest, with its licence corrections (deal.II's Apache option, jagua-rs and acadrust under MPL-2.0, Algoim's grant-back, OpenSubdiv and OpenUSD under TOST-1.0). |
| FD-3 better than everything | Accepted (1 requirement 5, 8, 13.4): the parity floor states the latest phase of each capability the R19 and R20 parity findings name (R19-01 to R19-03, R19-05 to R19-11, R19-14 to R19-17, R19-19 to R19-21, R19-24 to R19-27; R20-01 to R20-03, R20-06, R20-08 to R20-21, R20-24, R20-25, R20-27, R20-29, R20-32, R20-33), and every tab adds a parity table. |
| FD-4 readable | Accepted (10, 11, and the whole contract): teach first, then specify; review history leaves running prose; reference tables do not count toward length; the contract is edited for a human reader (section leads, terms defined before use, long bullets split, glossary rows cut to definitions) without changing any rule except by the rulings in this table. |
| R15-01 conditional verdicts | Accepted (5.6, 7.1): `conditional_on` and the re-evaluation pass are deleted. Policy allowances are records in pinned policy packages that checks read like any input, listed in `CheckOutcome.allowances`; the merge order loses its special case and the gate predicate a clause. |
| R15-20 policy packages | Accepted (2, 5.6): policy packages are pinned in `ingot.lock` and updated by Proposal; "policy" names only Cedar policies and policy packages; signed device records become site safety records. |
| R15-02, R17-38 text integrity | Accepted (5.3, 7.6): free-text integrity travels on `ExternalText` values; node labels carry typed-input integrity plus text turned into non-text values; 5.3 is the only statement of the merge rule. |
| R15-03, R17-20 evidence | Accepted (2, 5.6, 7.1): an Evidence record is an External input pinned under `[[evidence]]` by `CheckId`; the evidence watermark is deleted; external labs sign as registered evidence signers. |
| R15-04 live collaboration | Accepted (7.1, 13.2): the Loro CRDT, block-id mapping and reconcile step are deleted; live sessions use a server-sequenced edit log rebased with the branch `MergeDriver`, so live and branch merges share one semantics. |
| R15-05 departures | Accepted (2, 5.4, 7.1, 7.6): deviations and compliance exemptions are Waivers; compliance checks return `CheckOutcome`; an Act is defined by its Approval of an exact plan; `grant_deviation` is no longer an Act. |
| R15-06, R17-12 labels and exits | Accepted (5.3, 7.6): licences form a usage part compared only at exits; the exits are listed truthfully; local writes and `Declared` clients require empty scopes and permitting licences; new `Declared` clients start at `public`. |
| R15-07, R17-13 uncleared readers | Accepted (2, 7.1): one derived-view mechanism serves uncleared staff and suppliers, with per-principal query budgets and `Withheld` outcomes. |
| R15-08, R15-09 fidelity | Accepted (7.1, 7.2, 13.3): geometry certifies in place, so `Interactive` and `SignOff` geometry share one computation and identity; Ingot nodes key by requested fidelity; the recertification row measures certification nodes. |
| R15-10, R15-35, R14-07, R13-01 canonical example | R13-01 revised, the others accepted (5.1, 5.6, 6): the check reads `study.regular()`, because singular sets belong to the study rather than the Part; the load direction is stated; a maximum on an excluded neighbourhood's boundary is `Undecided { MaximumAtExclusion }`; the check is named; the attribute is `#[toolbox]`; forwarded tolerance symbols are keyed by the realizing feature; the default thickness becomes 6 mm, so the example passes and the oracle shows failure at 4 mm. |
| R15-12 symbolic layer | Accepted (7.5, 12): one hash-consed expression type, `kernels::expr`. |
| R15-13 cache verification | Accepted (7.8): two-builder agreement for gates and `SignOff`; fan-out-weighted spot checks elsewhere; full re-verification of released revisions after toolchain or `detmath` upgrades. |
| R15-15, R17-02, R17-04, R17-16 signatures | Accepted (5.4, 7.6, 13.2): one signature table replaces the scattered two-person, AAL3 and self-approval rules; credential enrolment is itself approved; single-person mode; `Error`-check Waivers need a `quality` signer outside the chain. |
| R15-16, R18-26 lane names | R15-16 accepted, R18-26 revised to R15-16's names (2, 5.6, 12): `Interactive` is only a fidelity; `PriorityClass` and `PoolLane` use `Drag` and `Foreground`. |
| R15-17 node keys | Accepted (2, 7.2): `OpKey` becomes `NodeKey`, defined once for every node kind. |
| R15-18, R15-33 product crates | R15-33 accepted, R15-18 revised (12): `repo`, `plm`, `trust` and `engine`; domain crates never depend on `kiln`; KLN reorders its tab to match and hands Deployment to PLT, while Privacy stays with `trust`. |
| R15-19, R21-02, R21-15 contract form | R21-02 accepted, R15-19 and R21-15 revised (lead, 2, 7, 14 to 18): the lead is two sentences; glossary rows define and point; long bullets are split; the ruling logs stay at the end as history read only when a ruling is in question, because the plan keeps each version's ruling log in the contract. |
| R15-21, R15-23, R15-24, R21-08, R21-21 names | Accepted (2, 5, 7.6): witness; Change is never a change order; credibility level C0 to C4 replaces evidence level, and "evidence" means Evidence records; Act kind, retention tier and response quantity. |
| R15-26, R15-27, R15-29, R15-30, R15-34 small types | Accepted (5, 6, 7.6): one `Severity` with `Hint`; `<family>/<code>` everywhere; `ItemKind` names match the glossary; `LiteralSite` and `Proxy` defined; `#[was]` holds the original name and can be retired. |
| R15-31, R15-38 say it once | Accepted (2, 7.1, 7.6): the physical-effect list appears once; engine bullets become subsections; patent facts move to 13.1. |
| R15-32 owners | Accepted (7.8, 12): egress is PLT's; the attestation service is KLN's, packaged by PLT. |
| R13-02, R13-09 phase 1 validation | Accepted (13.1, 13.2): a validation campaign on separate specimens precedes the run build; proof loads become held-out confirmation through gauge functionals; V&V 20's k and α are fixed. |
| R13-03, R13-10, R13-23, R13-25 bounds | Accepted (5.1): parts are stated in the bounded quantity's norm; calibration is a class or a statistical method, otherwise `Indicator`; one α rule; the Crouzeix–Raviart example is cut. |
| R13-04, R13-07, R20-02 phases | Accepted (7.1, 13.4): `Requires:` entries checked by `check.py`; rows for linear dynamics, symmetry reductions, planar and axisymmetric models, Helmholtz solvers, RLCG and full-wave extraction, phase-transformation kinetics and phase 1 tolerance limits. |
| R13-08 references | Accepted (13.2): calibration references come from an independent fitted high-order code. |
| R13-15, R20-07, R18-35 targets | Accepted (13.3): the interactive row counts five goal estimates; `SignOff` and flow throughput rows on a reference workstation and a server class; memory is defined. |
| R13-17 dynamic gates | Accepted (13.1): GP5 and GP9 compare regularized functionals and ensemble statistics. |
| R13-19 | Accepted, tab only (FLX). |
| R14-02 rebuild parity | Accepted (13.1): a part-level rebuild corpus with GP1's gate line; ANV owns the targets. |
| R14-03 SSI closure | Accepted (7.1, 13.2, 13.3): the phase closure rule; lofts, non-circular sweeps and twisted or scaled extrusions move to phase 2; the prismatic subset is defined by rule. |
| R14-24, R14-28, R14-33, R14-36 geometry wording | Accepted (5.5, 7.1). |
| R16-01, R17-25, R17-30 approvals | Accepted (7.6): approve, return for changes, or deny as suspicious; the pending limit is per delegating human for agent-prepared plans; the purpose is collapsed with a taint banner. |
| R16-02, R16-03 programs | Accepted (5.6, 7.6): the machine class excludes controller and post versions; one program subject, MFG's `ProgramSubject`. |
| R16-04 bench sessions | Accepted (7.6): the restricted `bench_session` Act. |
| R16-14 local External Ops | Accepted (7.8, 9): `Unverified`, at most `Interactive`, never cached or gating. |
| R16-25 `SignOff` rename | Declined: "sign-off" analysis means final-accuracy verification in simulation and EDA practice, so `SignOff` reads correctly as a fidelity; the glossary already forbids "sign-off" for Approvals, and a rename would touch every tab for no gain in precision. |
| R16-30 phone approvals | Accepted (7.6): uncontrolled release and change-notice Acts may be approved in a phone browser with a roaming security key. |
| R17-01 local credentials | Accepted (7.1, 7.6): local credentials authenticate as a device agent; human-only methods need a per-call WebAuthn assertion; spans from other channels are untrusted until confirmed. |
| R17-03, R18-03, R18-05 build program | Accepted (3 principle 6, 13.2): taint rule and agent audits; interface-first contract crates and a separate oracle workspace; keyed held-out splits with aggregate verdicts. |
| R17-05 determinizer | Accepted (7.4). |
| R17-11 attested clients | Accepted (7.6). |
| R17-14 controlled devices | Accepted (5.3). |
| R17-15 client flashing | Accepted (7.6). |
| R17-17, R17-18, R17-19, R17-21, R19-03 phase 0 counsel and names | Accepted (2, 7.7, 13.1, 13.4): authorship and DCO opinion; freedom-to-operate search over chains A to D and at each later gate; every user-visible name cleared; ISO's answer with a deterministic fallback; a thread and fastener table opinion, with formula-based designations needing no table. |
| R17-24 registry | Accepted (7.7). |
| R18-01 Failure and Abort | Accepted (7.2, 12): `Stop` and `OpResult`, with no conversion between `Failure` and `Abort`. |
| R18-02, R18-08, R18-13 operation crates | R18-08 and R18-13 accepted, R18-02 revised (4, 12): one crate per operation family with frozen version directories and a Cargo-level closure hash; the toolchain pin and `detmath` epoch sit beside the hash, not in it, so upgrades pass golden-hash checks instead of minting versions; archived engines run through `crucible:archive/op@1`; `base` and `apps/platform` split. |
| R18-04, R18-09, R18-10, R18-12, R18-14, R18-15 Rust structure | Accepted (5, 7.3, 7.4, 7.5, 12): `api-schema`; erased canonical forms with generated typed views; portable core crates; the `material` crate; the native-code register; named lint mechanisms. |
| R18-11, R18-20 browser | Accepted (9, 13.2, 13.3): a split engine module with a per-phase budget; the single-threaded web product build moves to phase 2. |
| R18-34 chain C | Accepted (13.2). |
| R19-04 parity tables | Accepted, extended to every tab (8). |
| R21-01 trust qualifiers | Revised (5.2): the table lives in the contract as binding definitions and the Overview walks the bracket through it; with conditional verdicts gone and solution verification folded into the budget, it has ten rows. |
| R21-03, R21-11, R21-12, R21-14, R21-22, R21-26, R21-30 writing rules | R21-03 revised, the others accepted (9, 10, 11): teach first; a three-sentence lead; a guide-level first section and an optional Reference section; 9,000 to 15,000 words of prose (ING and ANV up to 17,000) with tables excluded; three-line decisions; provides-only interfaces; one citation style; first-use expansion with a generated glossary; optional platform notes; no dashes in Failure cells; summary tabs link and never copy. |
| CCR-ANV-10 blend stages | Accepted (7.1): convexity change along an edge joins stage 1; partial-length blends with setback ends and capped and cliff ends join the later stages. Version 7.1. |
| CCR-FLX-12 shared rows | Accepted (13.4): elastohydrodynamic lubrication (3), the plane-pair cavity model (4) and rotor aerodynamics (4, GP6). Version 7.1. |
| CCR-KLN-11 approval delegation | Accepted (5.4): one signature-table row for `ApprovalDelegation`. Version 7.1. |
| CCR-KLN-12 step state | Accepted (7.1): the derivative retention tier is `StepState`, so "checkpoint" names only transparency-log heads. Version 7.1. |
| CCR-AGT-14 single-person merges | Accepted (5.4): single-person mode covers merge approval after an `Attested` verifier review, with the 72-hour delay. Crucible's own repository relies on it. Version 7.1. |
| CCR-ECO-13 product liability | Accepted (13.1): counsel's product-liability assessment joins the phase 1 gate. Version 7.1. |
| FD-5 Git-native history (founder, 12 October 2026) | Accepted (2, 7.1, 12): a Crucible repository is an ordinary Git repository; Changes are commits, protected refs are written only by Kiln's Git server under the signature table, other hosts are mirrors whose pull requests become Proposals; results stay in Kiln's cache, large Assets are LFS pointers, `ObjectId` rides in a commit trailer, and labels above `internal` get their own repositories. Version 7.2. |
| FD-5 amended (founder, 12 October 2026) | Accepted (7.1): any Git host can be a repository's home; Kiln enforces protected branches as a required status check and refuses to release a history with an unsigned merge, instead of being the only writer; a module gets its own repository only when some reader of the product repository may not read it. Version 7.3. |
| Round 4 audit (contract items) | Accepted (5, 5.4, 7.1, 7.2, 7.6, 13.4): `standing_release` joins 7.6's Act kinds; a reached work or memory limit is a `kiln/` Failure with any best-so-far result beside it; in single-person mode only two-person records and R3 and R4 merges wait 72 h, and before phase 2 the verifier role's CI-signed review counts as `Attested`; `trust` implements `PlacementPolicy`; a BOM is a computed view, and "derived view" means only the declassified view; 13.4's "Also phased in" column corrected and FMU import given a shared row (phase 3). The bracket's figures are ING's (contract 6 makes ING the example's owner). Version 7.4. |
| Deleted in version 7 | `conditional_on` and the allowance re-evaluation; the evidence watermark; the Loro CRDT, block-id mapping and reconcile step; the separate deviation record, the `grant_deviation` Act and the compliance verdict enum; the module-signature path for uncleared readers; 100% spot re-execution of released nodes; the separate `SignOff` geometry recomputation; `on_merge`, `on_partial` and `on_fragile`; `DiagnosticSeverity`; the name `OpKey`; `unsafe` in `kernels`; rules carried in glossary rows; the version history in the lead. |
