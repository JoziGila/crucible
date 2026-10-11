# MFG round 3 packet

Your tab is `docs/spec/07-manufacturing.md` at v2 (tag `round-2`). Round 3 fixes, in one pass: the 56 second-review findings that target it (3 Critical, 38 Major, 15 Minor), its 44 `[unverified]` claims, its open questions and the known items below. Contract v6 is binding; its section 17 lists the rulings on this review, and many findings below are already settled there.

## Second-review findings

### R7-06 · Major · Targets: COV, FLX, MFG, CONTRACT
**Section:** COV "Dynamics and stability" (Buckling) and "Regime variables" (Imperfection sensitivity); COV "Solid mechanics" (feature ≥ 10 grains); MFG "Slicing, lattices, process simulation and DfAM" (as-built struts)
**Problem:** GP2's strut-buckling check uses linear elastic eigen-buckling, which overestimates the capacity of typical printed lattice struts. They are stocky enough to buckle inelastically, and their as-built waviness and diameter scatter reduce capacity further. COV's envelope refuses eigen-buckling only for shells flagged imperfection-sensitive, so struts pass unchecked. Flux has no operation that computes the Koiter coefficient the regime variable needs. The as-built strut diameters MFG calibrates arrive in phase 2, after GP2. COV's default "feature ≥ 10 grains" also puts many printed struts in the Extrapolated zone, and no strut-scale Material exists to fix that.
**Evidence:** The Johnson transition slenderness is π√(2E/σ_y). With typical Ti-6Al-4V values (E ≈ 110 GPa, σ_y ≈ 900 MPa, unverified handbook figures) it is about 49. A 0.6 mm strut 3 mm long has L/r = 3/0.15 = 20, well inside the inelastic range, where Euler's load exceeds the Johnson load. COV buckling envelope: "Eigen-buckling `Refuse` at `SignOff` on shells flagged imperfection-sensitive". MFG: "as-printed strut diameters calibrated per process", phase 2. FLX defines no Koiter computation.
**Fix:** (1) COV's linear eigen-buckling envelope adds the regime variable σ_cr,Euler / σ_proportional per member: Calibrated below 0.5, `Refuse` above 1. Escalation goes to the Johnson or tangent-modulus L0 rung for struts, or to nonlinear analysis with plasticity in phase 2. (2) It adds an imperfection regime variable for struts, the waviness amplitude over the radius of gyration from MFG's as-built calibration, `Flag` above a declared value with a Perry–Robertson-type reduction as the L0 alternative. (3) MFG's as-built strut calibration for metal PBF moves to phase 1 and enters 13.4, since GP2 needs it. (4) COV ships strut-scale Materials calibrated on as-built strut specimens, whose coverage includes strut diameter, so printed lattices are not Extrapolated by the grain default. (5) FLX adds `flux::koiter_coefficient` in phase 2 with nonlinear shells. In phase 1 the shell classifier is moot because shells start in phase 2.

### R7-07 · Major · Targets: CONTRACT, FLX, MFG, COV
**Section:** Contract 13.4 row "Additive distortion by inherent strain"; FLX "Coupling" (element activation); MFG "Additive processes and build preparation", "Slicing, lattices, process simulation and DfAM"
**Problem:** Phase 1 predicts GP2's distortion with no supports, no baseplate removal and no stress relief, so the prediction cannot match what is printed and measured. Metal PBF supports are an MFG phase 2 capability. In phase 1 the vendor's slicer generates supports Crucible never sees, and the as-built shape the gate measures follows baseplate cutting, support removal and usually stress-relief heat treatment, none of which Flux models. GP2's gate compares no distortion prediction anyway (R7-04), so the 13.4 rule ("the first gate that needs it") does not put inherent strain in phase 1.
**Evidence:** MFG: "Supports | … block, line, cone and lattice supports (metal PBF) | … | MFG-O-AM-4 | 2". D-MFG-25: "In phase 1 … Crucible hands builds to the user's slicer". FLX: "Element activation switches cells on by a layer or time Field: per layer group for additive inherent strain (phase 1)". MFG-O-AM-8: "metal PBF build of GP2 within 0.1 mm in phase 2".
**Fix:** Move "Additive distortion by inherent strain" in 13.4 to phase 2, beside metal PBF supports and compensation, and update FLX, COV and MFG phasing. Specify the analysis as a declared sequence: layer-group activation of part plus supports (supports as a homogenized lattice material with calibrated stiffness), baseplate cut, support removal and optional stress relief (inherent strain scaled by a calibrated relaxation factor). Each step's data comes from MFG's coupons, for example cantilever coupons cut from the plate. If phase 1 keeps the row, the bureau's support geometry must be imported as an Asset into the build model; otherwise phase 1 states that distortion is not predicted.

### R7-08 · Major · Targets: CONTRACT, FLX, MFG, ANV, ELX, COV
**Section:** Contract 13.4 rule and rows
**Problem:** The shared phase table phases each capability by the gate that names it, but not by what it depends on. Several prerequisites therefore land after the capabilities that need them: metal PBF supports (MFG 2) after inherent strain (1); as-built strut calibration (MFG 2) after GP2's strut checks (1); `anvil::boundary_layer` (ANV 4) after the phase 3 laminar conjugate heat transfer and 3D mould fill that FLX's own plan sends to fitted boundary layers; an eigenvalue estimator (none) under row 1; and a Koiter-coefficient computation (none) under COV's buckling envelope. The SPMe row omits FLX, although SPMe needs FLX's phase 4 parameter-domain spaces.
**Evidence:** ANV: "`anvil::boundary_layer` | … | ANV-O-BL-1 | 4". FLX plan defaults: "Contact, sliding interfaces, boundary layers; voxel data | Fitted meshes; finite cell". FLX: "Parameter-domain spaces | … | FLX-O-FORM-5 | 4" and "parameter-domain forms for SPMe cells" (phase 4), while 13.4's SPMe row lists "Also phased in: COV".
**Fix:** Add to the 13.4 rule: "A capability that a row or a gate depends on takes a phase no later than its dependent; each row names its prerequisites in a column 'Needs'." Then apply it: supports and inherent strain both in phase 2 (R7-07); as-built strut calibration in phase 1 (R7-06); laminar conjugate heat transfer and mould fill state an octree wall-resolution rule instead of fitted layers (R7-09); eigenvalue DWR in phase 1 under row 1 (R7-05); a Koiter computation in phase 2 under COV's nonlinear buckling; FLX added to the SPMe row's "Also phased in".

### R7-09 · Major · Targets: FLX, MFG, ANV, COV
**Section:** FLX "Solve plans and per-region discretization" (plan defaults), "Coupling" (conjugate heat transfer); MFG "Molds and injection molding" (D-MFG-15)
**Problem:** Phase 3 runs laminar conjugate heat transfer and 3D fill, pack and cool on the immersed octree, yet neither states how finely the wall-normal layers must be resolved, and FLX's plan default sends boundary layers to fitted meshes that Anvil delivers only in phase 4. The octree's only resolution rule, four cells across a section, comes from elasticity. It does not resolve a natural-convection thermal boundary layer or the frozen skin and gapwise shear profile that govern fill pressure, pack and warpage. GP5's measured warpage and hottest-part targets therefore have no defined resolution, and no estimator or GCI requirement says when the octree solution is converged.
**Evidence:** FLX: "Conjugate heat transfer | Partitioned with Robin conditions, or monolithic on a shared octree | 3 (laminar, natural convection), 4 (turbulent)". D-MFG-15: "a level-set fill front on the immersed octree for the Stokes-regime melt". ELX phase 3 evidence: "hottest part within ±5 K of measurement (targets)".
**Fix:** Amend FLX's plan default to "turbulent boundary layers needing y⁺ resolution: fitted layers from phase 4; laminar thermal layers and frozen layers: octree wall refinement". Add plan rules: at least five cells at p = 2 across δ_T = H·Ra_H^(−1/4) on heated walls, and at least eight cells across the cavity half-thickness for 3D fill and pack. Name both as regime variables in COV's convection and moulding envelopes, with under-resolution making the zone Extrapolated. Require solution verification (D-FLX-34) or an estimator for the fill-pressure and warpage goals at `SignOff`. MFG states GP5's expected 3D cell count as a target.

### R7-20 · Major · Targets: MFG, FLX, COV
**Section:** MFG "Welding, joining and composites" (structure-scale distortion); FLX "Coupling" (weld-group activation); COV "Manufacturing process physics" (welding distortion)
**Problem:** GP4's frame members are Timoshenko or Vlasov beams, and inherent strain is not defined on a beam, so phase 2 cannot predict the weld distortion the gate measures. The welds sit at member joints, which a beam model reduces to nodes. MFG says "inherent strain on shells or solids", and FLX keeps junction zones solid for two thicknesses, but neither says how weld shrinkage enters a beam frame. The phase 2 inherent strains also have no stated source: COV's envelope "Source calibrated by macrograph" belongs to the Goldak transient model, which arrives in phase 4.
**Evidence:** MEC: "Flux therefore models them as Timoshenko or Vlasov beams on `anvil::member_axes`". MFG: "inherent strain on shells or solids in Flux". COV: "Welding distortion | … | Source calibrated by macrograph | GP4 measured distortion | … | 2, 4 transient".
**Fix:** For beam-modelled frames, weld shrinkage enters as equivalent joint loads: longitudinal shrinkage force, transverse shrinkage and angular distortion per weld. These are computed from inherent-strain values on a local shell or solid joint model, which `mark_reduction` keeps around each welded joint (welded joints count as features for L_local). Phase 2 inherent strains come from measured coupons per joint type, thickness, process and heat input (MFG-O-JOIN-2), recorded as calibration data with an envelope over heat input per length and plate thickness. COV's phase 2 envelope cites the coupons, and the macrograph calibration moves to the phase 4 transient row.

### R7-29 · Major · Targets: MFG, COV
**Section:** MFG D-MFG-15 and Open questions 4
**Problem:** The Hele-Shaw envelope tests only one of the conditions the lubrication approximation needs. Gap-averaged flow also needs the gap to vary slowly, and it fails within about one thickness of the flow front (fountain flow), at gates, at rib and boss roots and at thickness steps, where flow is fully 3D. These are exactly where warpage-driving orientation and frozen layers form, so a check inside the envelope can still rest on an invalid model.
**Evidence:** MFG: "The Hele-Shaw envelope defaults to local thickness under one tenth of local flow length, calibrated in phase 3 [unverified]". D-MFG-15: "Hele-Shaw … valid only inside a declared thickness-ratio envelope".
**Fix (answers MFG open question 4):** The Hele-Shaw envelope has three regime variables: h/L_flow ≤ 0.1 (kept); thickness gradient |∇h| ≤ 0.1; and distance from gates, rib and boss roots, thickness steps and the flow front of at least 2h. Regions failing the third are `Flag` at `Interactive` and require the 3D model at `SignOff`. Phase 3 calibrates all three thresholds against 3D solves on a step plate and a ribbed plaque, and until then the zone is Extrapolated.

### R7-42 · Minor · Targets: MFG, COV
**Section:** MFG Open questions 7
**Problem:** The boundary between COV's material models and MFG's process data is undecided, so two tabs can own one parameter: a melt's heat-transfer coefficient to the mould, or a cast alloy's interfacial resistance.
**Evidence:** MFG open question 7: "Where does COV's material model ownership end and MFG's process data begin for melts and cast alloys?"
**Fix (answers MFG open question 7):** A parameter that belongs to the material alone, whatever machine or mould is used, is a COV `Material` property: Cross–WLF rheology, Tait pvT, solidus and liquidus, fraction-solid curves, cure and crystallization kinetics. A parameter that depends on the machine, mould, tooling or process window is an MFG process profile: melt-to-mould heat-transfer coefficients, interfacial resistance, machine response, injection profiles, and inherent-strain coefficients per machine. Each record cites the tests that produced it.

### R8-44 · Minor · Targets: MEC, MFG
**Section:** MEC Open questions 3
**Problem:** Release behaviour for implicit blend fallbacks is open.
**Evidence:** MEC open question 3: "Which processes accept a released part with an implicit region?"
**Fix:** Decide: a release check `fallback_regions` passes only if each fallback region's certified deviation is within the governing profile or general tolerance of its faces, the target MFG process profile accepts non-NURBS regions (additive yes; machining only with mesh-capable CAM), and no semantic PMI targets the region (presentation only, as the CAx-IF practice requires for non-exact geometry). Reason: the deviation is already certified, so the remaining question is whether the process and the PMI can use it.

### R9-01 · Critical · Targets: CONTRACT, KLN, AGT, ELX, MFG
**Section:** CONTRACT 5 (`ApprovalSubject`); KLN "Revisions and lifecycle states" (D-KLN-26), "Change orders" (D-KLN-28); AGT "Acts and approvals" (D-AGT-20); ELX "Software and firmware as BOM items"
**Problem:** The binding `ApprovalSubject` covers only geometry and PMI, so an approved release does not bind the firmware, material, properties, documents or programs it ships. The release plan's digest deliberately excludes the `ChangeId`, so after approval anyone who can push may rebase onto a Change with the same subject but a different Software item binary or Material, and the approval stays valid. KLN's `ItemDefinition` is richer than the contract's subject but is defined only for Parts and Assemblies, and the contract wins where they differ.
**Evidence:** Contract 5: "`ApprovalSubject` [KLN]: `{ base revisions, ItemDefinition GeometryIds with PMI attached by canonical entity number, check-verdict digest …, effectivity, evidence record ids }`". KLN l.490: "A revision's `ItemDefinition` holds the `GeometryId`s of the Part or Assembly with PMI …, the `Material` version, properties, the BOM by value and documents by semantic content" (no rule for Software, Document, `Program` or `Purchased` Items). AGT l.889: "A release plan's digest covers the `ApprovalSubject`'s `ObjectId`, the tag and the effectivity, never the `ChangeId`". ELX l.798: a Software item "records its item number, version, binary hashes, source repository and Change, toolchain". A firmware or material swap changes no `GeometryId` and no PMI, and changes a check-verdict entry only if some check happens to read it.
**Fix:** Contract 5 replaces the second element: "`ItemDefinition` digests of every affected Item (KLN), for every Item kind". KLN defines `ItemDefinition` per kind in one table: Part and Assembly (name-free identity per R9-12, PMI by canonical entity number, `Material` `ObjectId`, properties, BOM by value); Document (semantic content); Software item (binary hashes, software bill of materials digest, `load` bindings, toolchain digest); `Program` (posted text digest and its simulation evidence ids); `Purchased` (approved-manufacturer list entries). Late-bound fields stay placeholders. AGT's release plan digest keeps excluding the `ChangeId`, and `act.commit` refuses a tag target whose recomputed subject differs from the approved one. New oracle KLN-O-CHG-2: swapping a Software item binary, a Material version or a document after approval voids the approval, while a rename with `#[was]` does not.

### R9-03 · Major · Targets: CONTRACT, KLN, MFG, ELX
**Section:** CONTRACT 2 (Evidence record); KLN "Physical tests and Evidence records" (D-KLN-35); MFG "Inspection and measurement"
**Problem:** Round 1's R3-17 found that a check's outcome for a fixed Change depended on when it was evaluated. The fix, "an evaluation reads the newest valid evidence record", keeps that dependence: two Evaluations of one Change and lockfile differ when a record arrives between them, two trusted builders can disagree, and incremental and cold builds can differ. "Valid" also reads the clock, since a record from an instrument "past calibration is invalid".
**Evidence:** Contract 2: "An evaluation reads the newest valid evidence record and stores its `ObjectId` in the `CheckOutcome`". KLN l.792: "A record from an instrument past calibration is invalid, and checks over it fail with `CalibrationExpired`". MFG l.563 repeats "Evaluation reads the newest valid record". KLN-O-EQUIV-1 requires incremental to equal from-scratch; contract 7.8 requires two builders to produce the same `ObjectId`.
**Fix:** Evidence selection becomes a function of a recorded input. Each Evaluation reads an evidence index at a transaction-log position, the evidence watermark, which is an input cell recorded in the Evaluation report and CI report. Protected branches advance the watermark by an audited ref transaction when records arrive, so a (Change, watermark) pair fixes every outcome, and two builders evaluate at the same watermark. Validity is judged at the measurement time (the instrument's calibration covered the measurement date), never at evaluation time. Contract 2 rewrites the sentence to "reads the newest record valid at its measurement time, up to the Evaluation's evidence watermark". KLN-O-HW-1 adds: two Evaluations at one watermark agree while a record arrives in between.

### R9-15 · Major · Targets: CONTRACT, ING, KLN, COV, MFG, ELX, AGT
**Section:** ING "Checks" (`#[waive]`); KLN release guard ("signed waiver"); COV "Policy by zone" (human waiver in the change order); MFG "Sustainability and compliance" ("a person records a time-bounded waiver"); ELX "Electrical rule checks"; KLN, MEC and ELX parts-policy waivers
**Problem:** "Waiver" is one concept with four mechanisms and no glossary entry: a source attribute any editor can write, a signed waiver at release, a human-only waiver in the change order for envelopes, and recorded waivers for parts policy. Which one a release accepts, who may author it, how it expires and what it names differ by tab, and agents can write the source form, which then shows as a waived status in ELX's requirement view.
**Evidence:** ING l.853: "A waiver is an attribute, `#[waive(check: "static_margin", reason: "…", until: "C")]`". KLN l.507: "or a signed waiver". COV l.168: "Human waiver with rationale; agents cannot waive". MFG l.651: "unless a person records a time-bounded waiver in the change order". ELX l.792: status "waived with a reason".
**Fix:** Contract 2 adds **Waiver**: a signature record by an authorized human naming a `CheckId` (R9-05), the Items and effectivity it covers, a reason and an expiry (revision, date or serial range), attached to a Proposal or change order. `#[waive]` in source is only a request that review shows; it counts nowhere until a matching Waiver record exists. Agents may write the attribute, never the record; `Protected` checks and `Refuse` envelopes accept none. ING, KLN, COV, MFG, ELX and MEC cite the entry instead of defining their own.

### R9-25 · Major · Targets: CONTRACT, AGT, MFG, KLN, ECO, UIX
**Section:** CONTRACT 12 (`apps/`); AGT "Scope and invariants", "One catalog, several transports"; MFG Open questions 12; KLN "Deployment"; ECO "SDKs, methods and the CLI"; UIX "Snapshots"
**Problem:** Contract 12 is the build plan, and it omits about ten deliverables that tabs depend on: `apps/mcp` and `apps/crew` (AGT), the machine gateway (MFG), the relay and runner gateway (KLN), the hardware runner (KLN, ELX, AGT), the tool runner (ECO), the model gateway (AGT), and the Python, TypeScript and C-ABI SDKs. Two placements are wrong: AGT says `api` owns transports and also that it has "no transport code", and `inspect.render`, an `api` method, runs `apps/renderer`, making a core crate depend on an app, while the contract's `apps/headless-render` appears in no tab.
**Evidence:** AGT l.1036: "`apps/mcp` and `apps/crew` ship as Linux containers". MFG l.914: "Contract 12's crate map lists no gateway app". KLN l.723: "relay and runner gateway from phase 2". ECO l.322: "In a tool runner". AGT l.7: the `api` crate covers "catalog, transports"; AGT l.39: "`core/api` … no transport code. `apps/mcp` serves it". UIX l.289: "`inspect.render` (AGT's method) runs this renderer headless".
**Fix:** Contract 12 lists `apps/mcp`, `apps/crew`, `apps/machine-gateway` (MFG, packaged by PLT), `apps/relay` and `apps/rig-runner` (KLN), `apps/tool-runner` (ECO, PLT) and `apps/model-gateway` (AGT), and `sdk/python`, `sdk/typescript` and `sdk/c` beside the Rust `crucible-sdk` (ECO). `inspect.render` dispatches to `apps/headless-render`, a service that links `apps/renderer`; `api` depends on neither. AGT's l.7 drops "transports".

### R9-27 · Major · Targets: KLN, MFG, ECO, PLT, ING, ANV
**Section:** KLN "Cost and budgets"; MFG "Scope, layering and core types"; ECO "Determinism and limits"; PLT "Worlds, calls and failures"; ING "Limits"; ANV work limits
**Problem:** One failure name means two kinds, and one kind has three names. `BudgetExhausted` is an uncached Abort in KLN and a cached `Failure` in MFG; ANV calls MFG's meaning `WorkLimit`. Wasm limit failures are `OutOfFuel`, `StackLimit` and `MemoryLimit` in ECO, `FuelExhausted` and `StackExhausted` in PLT, and `FuelExhausted`, `DepthExhausted` and `MemoryLimit` in ING; ECO also calls memory growth past the maximum a cached `Failure`, while PLT says `memory.grow` returns −1 and the component decides.
**Evidence:** KLN l.156: "Exhausting it is the Abort `BudgetExhausted`". MFG l.63: "`BudgetExhausted` is a cacheable `Failure`". ANV l.28: "reaching one is the deterministic `Failure` `WorkLimit`". ECO l.433: "`OutOfFuel`, `StackLimit` and `MemoryLimit` are cached `Failure`s". PLT l.523 to 525: `FuelExhausted { used, limit }`, `StackExhausted { limit }`, and growth "Decided by the Wasm component". ING l.723 to 725.
**Fix:** `base` holds one catalog of limit outcomes, owned by KLN, which every tab cites: Failures `WorkLimit { kind, limit }` (argument-set search or work limits), `FuelExhausted`, `StackExhausted`, `MemoryLimit` (semantic limits); Aborts `BudgetExhausted`, `DemandDepthExhausted`, `FuelCeilingExceeded`, `ResourceExhausted`. MFG renames its failure `WorkLimit`; ECO adopts PLT's names and PLT's growth rule.

### R9-31 · Major · Targets: AGT, KLN, ECO, MFG
**Section:** AGT capability tables ("Branch confinement", "Server-side enforcement", "Release Acts", "Data-release family") and Phasing; KLN "Security", "Electronic signatures", "Supplier packages and derived views"; ECO "Recipient watermarking"
**Problem:** AGT phases its safety mechanisms earlier than the KLN and ECO capabilities they run on, so AGT's gate oracles cannot pass when AGT says. Server-side scope, label and approval enforcement is phase 0 in AGT but identity, authorization and labels are phase 1 in KLN; release Acts rest on "KLN signature records" in phase 1 while signature records are phase 2; the data-release family promises watermark and expiry in phase 1 while KLN and ECO deliver them in phase 3.
**Evidence:** AGT l.30: "Server-side enforcement | Scopes, labels, budgets and approvals checked on every call | … | AGT-O-7 | 0"; AGT l.1111 (phase 0): "AGT-O-1, 4, 5, 6, 7, 16 and 20 green". KLN l.703, l.705, l.707: identity, authorization and labels at phase 1. AGT l.913: "Release Acts | Digest over the approval subject; KLN signature records | … | 1"; KLN l.607: "Electronic signatures | Signature records … | 2" while KLN l.576 says "Every Approval of a release … is a signature record". AGT l.914: "Data-release family | … watermark, expiry … | 1"; KLN l.644 and ECO l.123: watermarks at phase 3.
**Fix:** Phase by the owner. AGT moves policy enforcement to phase 1 (phase 0 keeps the `api` types and a single-principal mode) and splits the data-release row: labels, screening, authorization and audit at 1; watermark and expiry at 3 with KLN and ECO. KLN moves a minimal signature record (signer, meaning, signed `ObjectId`, WebAuthn event, algorithm id) to phase 1, since the GP1 release needs it, and keeps Part 11 mode, re-authentication policy and dual signing at 2.

### R9-32 · Major · Targets: MFG, COV, ING, ECO, UIX, PLT, CONTRACT
**Section:** MFG "Sustainability and compliance"; COV "Environmental data"; ING "Assemblies, variants and families" (catalog selections); ECO "Mirrors, licences and the parts catalog"; UIX "Performance, privacy and extension" (telemetry row); CONTRACT 13.2 (phase 1 scope)
**Problem:** Several consumers phase a capability before its producer exists, and two tabs ship in phase 1 what contract 13.2 defers. MFG's embodied carbon and RoHS checks (phase 2) read COV's environmental records (phase 5); ING's catalog selections (phase 1) run over `parts::` packages that ECO delivers in phase 2; UIX ships telemetry in phase 1 on a pipeline PLT builds in phase 2, which the contract defers out of phase 1.
**Evidence:** MFG l.655: "Global warming potential per BOM line from COV's per-material `EnvironmentalRecord`s … | 2"; COV l.744: "Environmental records | … | 5". ING l.654: "Catalog selections | Pure over pinned data … | 1"; ECO l.690: "Catalog-part definitions | `parts::` packages … | 2". UIX l.796: "Telemetry | PLT's opt-in pipeline … | 1"; PLT l.669: "Telemetry pipeline | … | 2"; contract 13.2 defers "telemetry" from phase 1.
**Fix:** Apply contract 13.4's rule (first gate that needs it) to these pairs too, and make the spec check enforce it: every capability row that names another tab's capability carries a phase no earlier than that owner's row. Concretely: COV's environmental records move to phase 2 with MFG (generic factors and declared substances only; database connectors stay at 5); ING's catalog selections take phase 2; UIX's telemetry row takes phase 2.

### R9-44 · Minor · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT
**Section:** Every tab (contract 11 style rules)
**Problem:** The tabs carry about 1,080 sentences over 25 words and about 340 paragraphs over three sentences, by the spec check's own count, mostly inside decisions; KLN's lead sentence alone runs 33 words. Contract 11 asks for sentences under 25 words and paragraphs of at most three sentences, and the founder's taste requirement makes this more than polish for a spec read by agents.
**Evidence:** `python3 docs/tools/check.py` per tab: ANV 167, KLN 128, PLT 122, AGT 99, UIX 96, ELX 94, ECO 85, MEC 83, FLX 79, ING 72, MFG 41, COV 12 long sentences; FLX 41 and KLN 34 long paragraphs.
**Fix:** Round 3's revision brief sets a hard budget the check enforces as an error: no sentence over 40 words, at most 5% of sentences over 25, no paragraph over four sentences; decisions split *Why* and *Rejected* into short sentences. Leads are rewritten first.

### R9-45 · Minor · Targets: UIX, PLT, ECO, COV, FLX, KLN, AGT, MFG
**Section:** Capability tables and Phasing sections named below
**Problem:** Owners and consumers state different phases for the same capability, and two tabs contradict their own Phasing sections.
**Evidence:** Tablets: UIX l.691 and Phasing phase 2, PLT l.147 and ECO l.473 phase 3. Lattice Boltzmann and particles: COV l.309 phase 5 (Wasm) and l.375 phase 6, FLX l.470 phase 4 and l.471 phase 5 (native). ERP and MES connectors: ECO l.563 phase 2, MFG l.632 phase 4. Air-gapped installs: PLT l.601 phase 2, KLN l.758 phase 3. Rust SDK: AGT l.265 phase 1, AGT Phasing l.1111 and ECO l.558 phase 0. FLX flexible multibody: l.646 phase 3, FLX Phasing l.1017 phase 4. FLX sizing Fields: l.139 phase 1, l.503 phase 2. Browser updates: PLT l.561 puts "a transparency log" in phase 1, which contract 13.2 defers.
**Fix:** The owner's row wins and consumers cite it: tablets 3 (PLT owns the targets); lattice Boltzmann 4 and particles 5, native (FLX); ERP and MES connector worlds 2 (ECO), with MFG's mapping at 4 stating it builds on them; air-gapped 3 (KLN's bundles); Rust SDK 0 (AGT corrects its row); flexible multibody 3 and sizing Fields 2 in FLX's own tables; PLT's update manifest uses TUF alone in phase 1 and adds the transparency log in phase 2. The spec check gains a cross-tab phase comparison for capability names shared between tabs.

### R9-49 · Minor · Targets: ING, MEC, MFG
**Section:** ING Open questions 4 ("Affine arithmetic at scale") and 6 ("`Decimal` resolution")
**Problem:** Both questions block std numerics that phase 2 freezes.
**Evidence:** ING l.1281: "Stacks over 10⁵ sites may need symbol condensation". ING l.1283: "Is 10⁻⁹ enough for every currency and pricing rule MFG needs?"
**Fix:** Question 4: when an affine form exceeds 4,096 symbols, symbols whose coefficient is below 10⁻⁶ of the form's radius fold into the remainder, which keeps `.limits()` a guaranteed enclosure and loses only their correlation; `tolerances(x)` reports how many folded, and ING-O-7 adds a 10⁵-site stack measured against the exact result. Question 6: keep 10⁻⁹, since currency minor units and per-unit prices of small parts need far fewer decimals [unverified: ISO 4217 table not opened]; specify round-half-even for every `Decimal` product and quotient, and require an explicit `round_minor(currency)` where a value becomes an amount payable, with a lint on unrounded payable amounts.

### R10-01 · Critical · Targets: CONTRACT, MFG, AGT
**Section:** MFG "Approval, transfer and physical safety" (Act table, MFG-O-SAFE-3); AGT D-AGT-31 and AGT-O-21; contract 7.6 Physical safety
**Problem:** The guarantee that a transfer never starts a device rests on static oracles. MFG-O-SAFE-3 passes when connector WIT worlds "expose no motion or start method (the static interface is the product boundary)", and AGT-O-21 passes when "no Act plan schema can express a machine start". In the protocols MFG targets, though, the start sits inside the upload call itself: a flag, a header or a choice of port. A connector whose interface is pure "upload" can therefore start a print or move a robot, and both oracles pass. R4-01's fix holds at the interface but not on the wire.
**Evidence:** OctoPrint's upload endpoint takes `print`, "Whether to start printing the file directly after upload" (https://docs.octoprint.org/en/master/api/files.html). With Moonraker's `print` set, "Moonraker will command Klippy to start the print after the upload has successfully completed" (https://moonraker.readthedocs.io/en/latest/external_api/file_manager/). PrusaLink's PUT upload takes a `Print-After-Upload` header, "Whether to start printing the file after upload" (https://raw.githubusercontent.com/prusa3d/Prusa-Link-Web/master/spec/openapi.yaml). Universal Robots' client interfaces "receive URScript commands" and make it "possible to control robot remotely without robot program" (https://www.universal-robots.com/articles/ur/interface-communication/overview-of-client-interfaces/). MFG names OctoPrint, Moonraker and PrusaLink for `send_print_job` and URScript among its robot posts.
**Fix:**
1. Replace MFG-O-SAFE-3's pass criterion with a behavioural one. Each connector runs against the real server or the vendor simulator (OctoPrint; Moonraker with a Klipper simulator; PrusaLink; URSim; each controller simulator) under wire capture. It passes when no request carries a start semantic and the device stays idle after every transfer. Start semantics include OctoPrint `print` or `select` set true, Moonraker `print` true, PrusaLink `Print-After-Upload`, Bambu MQTT print commands, any URScript to the primary, secondary or real-time interfaces, and Dashboard Server commands.
2. Each connector manifest declares an allowlist of endpoints with fixed parameter values. The gateway enforces it in its own egress filter, outside the Wasm connector, so a defective or malicious connector cannot add a flag.
3. Robot programs transfer only as program files into the controller's program store, never through script or dashboard interfaces (transport per vendor [unverified]).
4. AGT-O-21 adds the same wire-level criterion. Contract 7.6 adds one sentence: "Transfer Acts are verified at the protocol level; an interface that cannot express a start is necessary, not sufficient."

### R10-02 · Critical · Targets: CONTRACT, MFG
**Section:** MFG "Approval, transfer and physical safety" (DNC and drip feed row; `send_to_machine` rule); contract 7.6 Physical safety
**Problem:** `send_to_machine` "Delivers a program to a control's memory or DNC queue" and "Never selects, loads or starts it", and MFG ships serial and Ethernet drip feed in phase 2. In drip feed the control executes blocks as they arrive. A control left in tape or remote mode with cycle start pressed waits for data. When the approved Act commits and the gateway starts streaming, axes and spindle move at commit time, perhaps hours after the button press and with nobody at the machine; the approver may be remote. Contract 7.6's "a person starts them at the device" does not hold on this path.
**Evidence:** The stated mechanism ("Serial DNC with XON/XOFF or RTS/CTS flow control, and Ethernet DNC") lets the control pace execution by requesting data, so the commit is the first event that supplies it. MFG-O-SAFE-5 ("Drip feed against controller simulators stops and reports every injected fault") tests faults during a feed, never a control that was waiting before the commit.
**Fix:**
1. Drip feed is pull-only. `send_to_machine` stages the approved program in the gateway's per-machine DNC library and sends nothing.
2. The gateway streams only in response to a request made at the control: a DNC remote request naming the staged program, or the control's data request. The request must begin after the commit and after an on-site confirmation entered on the gateway's machine-side terminal.
3. If the control already has a data request or DNC session open when the Act commits, the gateway refuses with `DncSessionPreArmed` and asks the operator to reset and request again. It never sends unsolicited data to a control in tape, remote or DNC mode.
4. MFG-O-SAFE-5 adds simulator cases waiting for data at commit, with a pass criterion of zero bytes sent in 100% of them.
5. Contract 7.6 adds: "A transfer never completes a start the device was already waiting for."

### R10-03 · Major · Targets: MFG, MEC, KLN, ECO
**Section:** MFG "Inspection and measurement" and "Quality records" (phases); MEC "Revisions, balloons and generated drawings"; KLN "Physical tests and Evidence records"; ECO QIF row; MEC Open questions 9 (R4-14)
**Problem:** The phase 1 gate measures GP1 "by external metrology against Crucible's tolerances", but every piece that turns lab readings into a verdict on a tolerance lands later:
- characteristic identities and balloon labels (MFG and MEC, phase 2);
- QIF characteristics (ECO, phase 2);
- results as Evidence records (MFG, phase 3);
- uncertainty-based conformance decisions (MFG, phases 2 and 3).

KLN admits lab Evidence records in phase 1 "addressed by the check it serves", but a GD&T control has no check until MFG creates its characteristic. MEC's partial decline of R4-14 ("phase 1 drawings carry item balloons only") rests on a wrong premise, because the phase 1 gate itself needs characteristic balloons.
**Evidence:** Contract 13.1 phase 1 gate. MFG rows "Characteristics and balloons ... 2", "Results as Evidence records ... 3" and "Uncertainty budgets and decisions ... 2, 3, 4". KLN: "In phase 1, external metrology for GP1 and GP2 enters as Evidence records signed by the lab's principal."
**Fix:** Move a minimal inspection loop to phase 1, scoped to GP1 and GP2:
1. D-MFG-18 characteristic extraction and D-MFG-26 labels for size, location, orientation, form and profile controls.
2. MEC's characteristic balloons and the ballooned PDF.
3. A results import from QIF 3.0 Results, plus a CSV template keyed by balloon label for labs without QIF output, creating one Evidence record per characteristic.
4. One conformance check per characteristic using the ISO 14253-1 default decision rule [unverified edition] with the lab's stated expanded uncertainty: `Pass`, `Fail`, or `Undecided` inside the guard band.

CMM programming, SPC and AS9102 stay in phases 2 and 3. Contract 13.2's "DfAM and cost 0 → 2" or "features, sketches, drawings and GD&T 2 → 6" line absorbs the work.

### R10-04 · Major · Targets: CONTRACT, MFG, AGT
**Section:** Contract 2 (Act) and 7.6 Physical safety; MFG Act table; MFG rows for CMM programs, press brakes, heat treatment, reflow and harness packages
**Problem:** The physical-effect Acts are a closed list, and the machine transfer is "`send_to_machine` (an NC program)". MFG also generates programs for devices that are not NC machine tools in that sense:
- CMM part programs;
- press-brake bend programs;
- heat-treatment and reflow recipes;
- SMT placement programs;
- harness cut-and-crimp job lists;
- molding-machine setups.

None has a transfer Act. They leave through data-release Acts or on a USB stick, which bypasses the gateway's hash, read-back, offset and numbering checks, and the never-start rule does not name CMMs, press brakes, ovens or placement machines.
**Evidence:** Contract 2: "Physical-effect Acts are the transfer Acts `send_to_machine`, `send_robot_program`, `store_machine_job` (OPC UA `Store` only) and `send_print_job`". Contract 7.6: "`send_to_machine` (an NC program)". MFG: "CMM paths and programs | Collision-free paths with articulating heads; DMIS and QIF Plans"; "Press-brake planning"; "Heat treatment and HIP | Recipes"; "Panels, stencils and reflow".
**Fix:**
1. Contracts 2 and 7.6 redefine `send_to_machine` as "a program or recipe for any device reached through the machine gateway". Its payload is typed as `NcProgram | DmisProgram | BendProgram | Recipe | PlacementProgram | CutList`, each with a device class.
2. The never-start list becomes: machine tools, CMMs, robots, lasers, presses and press brakes, furnaces and ovens, placement and harness machines.
3. Every payload kind gets D-MFG-24's digest, read-back where the device supports it, and R10-11's number registry.
4. AGT's Act table and AGT-O-21 follow.

### R10-05 · Major · Targets: CONTRACT, MFG, AGT, UIX
**Section:** Contract 7.6 Physical safety (`start_print`); MFG "Printers, 3MF and print transfer"; AGT D-AGT-31
**Problem:** `start_print` rests on four weak conditions.
1. The safety declaration lives in a printer profile, which is a registry package from a third party, so it is self-declared. `unattended_safe`, by contrast, needs a safety officer's signed site policy.
2. "Enclosure or smoke detection" accepts an enclosure without detection, which contains nothing when the enclosure is plastic.
3. Nothing restricts the process, so a laser powder-bed machine with such a profile qualifies, although contract 7.6 says Crucible never starts lasers or furnaces.
4. "A site-bound key" lets someone confirm a clear build plate from anywhere on site without seeing it.
**Evidence:** Contract 7.6: "`start_print` exists only for printers whose profile declares thermal-runaway protection and enclosure or smoke detection, and needs an Approval of the job digest plus an on-site confirmation that the build plate is clear, given at the printer or with a site-bound key." MFG: "Printer profiles are packages".
**Fix:** Contract 7.6 replaces the rule:
1. `start_print` exists only for material-extrusion printers and for vat-photopolymerization printers whose light source is not a laser above Class 1 [unverified classification per model]. It never applies to powder bed fusion, directed energy deposition, binder jetting or any printer that needs inert gas.
2. Each printer serial needs a signed site policy from the named safety officer. The policy declares firmware thermal-runaway protection and smoke or heat detection that cuts printer power.
3. The on-site confirmation is given at the printer, within 10 minutes before the start. It uses a printer-side button where the firmware offers one, or a one-time code shown on the printer's display and typed into the confirmation.

MFG-O-SAFE-2 seeds profile-only declarations, laser-process printers and confirmations from elsewhere on site, and all must be refused.

### R10-08 · Major · Targets: MFG, KLN, AGT, CONTRACT
**Section:** MFG "Approval, transfer and physical safety" (`ProgramSubject`); KLN D-KLN-38; AGT D-AGT-20
**Problem:** The program subject signs data that shops change every shift.
- `machine` names one machine, so moving a job to an identical sister machine needs a new program approval.
- `tool_table` maps tools to pockets, which random-access tool changers reassign while running.

On top of that, every transfer needs its own WebAuthn Approval by an assigned approver. Approvals are single-use, standing pre-approvals are rejected, and a session may hold three pending requests, so a cell programmer feeding six machines is throttled. Shops will route around this.
**Evidence:** MFG: "`ProgramSubject { programs, machine, controller, tool_table, setup_sheet, verdicts, block_map }`"; "Per-machine tool tables | Tool Assemblies → T number, pocket, H and D registers". AGT D-AGT-20: "Rejected: ... standing pre-approvals". Contract 7.6: "At most three pending requests per session".
**Fix:**
1. The subject binds the machine class and nominal tool assemblies by T number, never a serial or a pocket. The class is the machine package version, controller family and software version, and post version. MFG-O-POST-3's qualification record lists the serials qualified for the class.
2. Instance data (pockets, measured lengths and radii, work offsets, calibration) stay outside the subject. The gateway verifies them at transfer against the setup sheet's tolerances.
3. A `Released` program may go to any qualified serial of its class through R10-02's pull path, on an operator's request at that machine. The program's release Approval serves as the plan's approval. Remote pushes keep the assigned Approval.
4. Contract 7.6 states this one exception to D-AGT-20 explicitly.

### R10-09 · Major · Targets: MFG
**Section:** MFG D-MFG-24; capability row "Pre-run offset verification"
**Problem:** The check is named pre-run but runs before transfer. Operators routinely touch off tools and set work offsets after loading a program and before cycle start. The offsets that decide a crash are therefore set after the gateway's check, so a pass at transfer says little about the run. R4-05's fix does not hold here.
**Evidence:** D-MFG-24: "It reads tool and work offsets and re-simulates with them before transfer". Row: "Pre-run offset verification | Offsets read; collision re-simulated with actual gauge lengths".
**Fix:**
1. Rename the row "Transfer-time offset verification".
2. Add an "Offset watch" row. From transfer until the program ends, the gateway re-runs the gouge and collision checks on every change to a referenced H, D or work-offset register. This works wherever the connector reads offsets: vendor connectors in phase 2, MTConnect `ToolOffsets` and `WorkOffsets` in phase 3.
3. On a change that fails, the gateway raises a machine-side alarm and an andon event within 5 s (target), naming the register and the predicted collision. It cannot block the cycle, and the setup sheet says so.
4. The setup sheet prints the verified values with their tolerances for the operator's check before cycle start.

MFG-O-SAFE-4 adds offset edits made after transfer.

### R10-10 · Major · Targets: MFG
**Section:** MFG D-MFG-24 (header hash); `Controller.files`
**Problem:** Controls rewrite programs they store. They change line endings and case, strip or reformat comments, add or drop block numbers and leading zeros, and normalize the program-number line. A hash over posted bytes then fails on read-back of correct programs, and users learn to ignore `HashMismatch`. The header line also cannot include its own hash, and long header comments exceed some controls' comment limits.
**Evidence:** D-MFG-24: "Posts write item, revision, release id and a short content hash into the program header, and the gateway recomputes the hash on transfer and on read-back." `FileRules` describes only writing ("line endings, character set, length, size, names").
**Fix:**
1. Define the hash over the canonical token stream of the semantic NC parser that already powers the semantic NC diff (MFG-O-POST-4). It is computed per dialect and excludes the header line.
2. `FileRules` declares each control's storage normalizations.
3. The header comment carries item, revision and 12 hexadecimal digits of the hash, within the control's comment limit.
4. A mismatch reports the semantic NC diff, not two hashes.

MFG-O-SAFE-2 adds round trips through each family's simulator and the reference shop's controls: correct programs never mismatch, and seeded single-token edits always do.

### R10-11 · Major · Targets: MFG, AGT
**Section:** MFG "Approval, transfer and physical safety"; `Controller.files`
**Problem:** Controls address programs by number or short name. Storing a program under a number already in memory overwrites the old one or is rejected, depending on the control. MFG says nothing about:
- how a program Item maps to a number or name per machine;
- how subprograms called by the main program travel with it;
- what happens when the number is taken.

Overwriting another job's program is a classic way to run the wrong program.
**Evidence:** MFG's Act table and D-MFG-24 cover header and hash only. No capability row allocates program numbers, and `FileRules` mentions only "names".
**Fix:**
1. Add a per-machine program registry to the gateway. Each program Item gets a stable number or name per machine class, kept across revisions. Subprograms belong to the transfer set.
2. Before transfer the gateway reads the control's directory. It refuses to overwrite a program Crucible did not store, with `ProgramSlotOccupied { number, foreign: true }`, and overwrites a Crucible program only with a later revision of the same Item.
3. The setup sheet prints the number, and the approval page states what is replaced, for example "replaces O1234, bracket rev B".

New oracle MFG-O-SAFE-6: seeded collisions are refused in 100% of cases.

### R10-12 · Major · Targets: MFG
**Section:** MFG "Machines, controllers and posts"; "Machining simulation and NC verification"; DNC row
**Problem:** After a broken tool, a power loss or a drip-feed fault, operators restart mid-program by block search. A restart that skips the tool call, length offset, work offset or spindle start is one of the commonest crash causes. Crucible simulates only full runs from the first block, and the DNC row says a fault is "never resumed automatically" without giving a safe way to resume.
**Evidence:** MFG has no restart, block-search or sequence-number capability. DNC row: "A fault stops the feed; never resumed automatically".
**Fix:**
1. Posts emit a restart point at every workingstep and tool change: a sequence number followed by a full modal restatement. The restatement covers the tool call, length offset, work offset, plane, units, absolute mode, spindle, coolant and an approach from the clearance plane.
2. Simulation verifies each restart entry from the tool-change position.
3. The setup sheet lists the restart points. A restart inside a workingstep is `Unsupported`.
4. Drip feed resumes only from a restart point, on a request made at the control (R10-02).

New oracle row: every restart entry simulates collision-free, and seeded restarts that skip the restatement are caught.

### R10-13 · Major · Targets: MFG, UIX
**Section:** MFG "Scope, layering and core types" (`Toolpath`, `Workingstep`); `MotionSemantics.cutter_comp`; posts
**Problem:** Shops hold tight wall and bore sizes by letting the operator adjust a wear offset at the control. That needs posts to output control-side or wear-mode cutter compensation (G41 and G42 with a D register). MFG's types have no compensation mode, so the gouge check cannot know that a finishing pass moves with a value set later at the control.
**Evidence:** The `Toolpath` and `Workingstep` records have no compensation field. `MotionSemantics` declares only "cutter_comp: look-ahead blocks, entry rule".
**Fix:**
1. Add `comp: CompMode { Computer, Control, Wear, ReverseWear }` and `wear_range: Range<Length>` to finishing workingsteps, defaulting to `Computer`.
2. Posts emit G41 or G42 with the D register for the other modes.
3. Gouge and collision checks run at both ends of the declared range.
4. The gateway's offset check verifies that the D register lies inside the range, and the setup sheet prints it.

MFG-O-SIM-1 seeds wear values outside the range. UIX's NC panel shows the mode per workingstep.

### R10-14 · Major · Targets: MFG, ECO
**Section:** MFG D-MFG-28 (`verify_nc`); "Milling, drilling and probing strategies" (probing paths)
**Problem:** D-MFG-28 promises to verify "any NC text", but `verify_nc` cannot simulate two common patterns. Programs from other CAM systems and from hand programming:
- call macros stored in the control (builder tool-change macros, probe makers' cycles, custom G- and M-code macros), whose source `verify_nc` lacks;
- branch on system variables that read live state (current position, probe results, tool-life counters), whose outcome is a measurement.

Many also write offsets from inside the program. MFG's own on-machine probing emits the same kind of calls.
**Evidence:** D-MFG-28: "A product NC interpreter ... verifies any NC text, including programs from other CAM systems and hand programming". The capability table lists "Macro B variables", "R parameters, GUD variables" and "Q parameters".
**Fix:**
1. The machine package carries a macro library captured from the control or the macro's maker, under its licence. A call to a macro not in the library is `Unsupported { macro }`; its motion is bounded by a declared envelope, or verification fails.
2. System variables that read live state are typed inputs with declared ranges. `verify_nc` explores both outcomes of each branch they control, up to a declared branch budget, then returns `Undecided`.
3. Programs that write offsets are flagged, since they change values the gateway checked.

MFG-O-SIM-3 adds macro-calling and probe-branching programs with planted crashes.

### R10-15 · Major · Targets: MFG, KLN
**Section:** MFG D-MFG-28; "Change impact" row; KLN D-KLN-38
**Problem:** Imported legacy NC programs are program Items "never converted to workingsteps", so they have no targets. The change-impact rule selects "exactly the programs whose targets or setups changed", so it never selects them. When the part changes, a legacy program stays `Released` and transfers without re-verification.
**Evidence:** D-MFG-28; change-impact row ("A design change invalidates exactly the programs whose targets or setups changed"). KLN: "An engineering order that changes a part returns exactly its dependent programs to `Prototype`."
**Fix:** A legacy program Item declares `verified_against: [ItemRevision]` for the parts and fixtures it was verified with.
1. A change order revising any of them returns the program to `Prototype`, as for generated programs.
2. `verify_nc` re-runs against the new revision and reports the regions where simulated stock and the new design differ.

MFG-O-SAFE-1 adds a legacy program on a revised part.

### R10-16 · Major · Targets: KLN, MFG
**Section:** KLN D-KLN-38; MFG "Quality records: SPC, MSA, FAI and PPAP"
**Problem:** Program Items ship with CAM in phase 2. They become `Proven` "after a passing first-article record", then `Released`. AS9102 first-article reports and QIF results as Evidence records arrive only in phase 3, and nothing in phase 2 defines a first-article record. GP3 and GP4 programs therefore cannot leave `Prototype`.
**Evidence:** KLN D-KLN-38: "`Proven` (after a passing first-article record)". MFG: "AS9102 and partial FAI ... 3"; "Results as Evidence records ... 3".
**Fix:**
1. KLN and MFG define a first-article record as a signed record joining the program revision, machine serial, part serial and one passing Evidence record per characteristic. It is built on R10-03's phase 1 loop.
2. AS9102 forms in phase 3 render the same record.
3. MFG adds a phase 2 row "First-article record", checked by MFG-O-QUAL-2's partial-scope cases.

### R10-17 · Major · Targets: CONTRACT, AGT, UIX, MFG
**Section:** Contract 7.6 Act approvals; AGT "Acts and approvals" (approval page); UIX D-UIX-29
**Problem:** The one approval page shows file names, a thumbnail, a content summary (Items, labels, bytes), recipient verification and screening dates, and a diff. Those fit data release. For a physical-effect plan the approver sees nothing that bears on safety:
- which device it is, and where;
- what the transfer overwrites;
- the simulation verdicts and minimum clearance;
- the gateway's offset result;
- what the person at the device must do.

MFG's rule that robot programs are "Proved in manual reduced-speed mode" appears nowhere a person reads it.
**Evidence:** Contract 7.6 lists the page contents. MFG: "`send_robot_program` | Delivers a robot program | Proved in manual reduced-speed mode; never writes safety configuration".
**Fix:** Contract 7.6 adds a physical-effect section to the page:
- device serial, location and controller version;
- program number and what it replaces (R10-11);
- simulation verdicts, with the minimum clearance and the count of `Unsupported` semantics;
- gateway offset results with their timestamp;
- the setup-sheet revision;
- the required on-device steps, each shown as an instruction to the person at the device: reduced-speed prove-out, tool-length check, reduced override, propellers off.

AGT-O-9 adds rendering cases for each physical-effect class.

### R10-18 · Major · Targets: MEC, MFG, COV
**Section:** MEC "Lattices and machine elements"; MFG "Turning, EDM, gears and grinding"; COV model levels
**Problem:** GP3 is a gearbox in phase 2, but no tab specifies gear load capacity or accuracy. MEC covers geometry to ISO 21771-1 only. MFG says "MEC owns gear geometry and rating", and its oracle reads "the design's quality grade", which no MEC record holds. COV mentions "gear rating" only as an example of an L0 model. A practitioner rates every gear for pitting, bending and scuffing, puts the accuracy grade and inspection data in a gear data table on the drawing, and checks bearing life.
**Evidence:** MEC machine-element table: "Involute spur and helical gears | ... | ISO 21771-1:2024". MFG: "MEC owns gear geometry and rating". MFG-O-GEAR-1: "Simulated flanks within the design's quality grade". COV L0 row: "gear rating".
**Fix:** Add the following in phase 2, with oracles from the standards' worked examples:
1. MEC's gear record gains an accuracy grade to ISO 1328-1 [unverified edition].
2. A rating check library implements ISO 6336 parts 1, 2, 3 and 6, or ANSI/AGMA 2101 [unverified editions], as L0 models with COV envelopes and margin Fields.
3. Catalog bearings get ISO 281 rating life [unverified edition] from the gear record's load spectrum.
4. Drawings gain a gear data table: module, teeth, pressure and helix angles, profile shift, modifications, grade, and span or over-pins measurement.

### R10-19 · Major · Targets: MFG, MEC
**Section:** MFG "Turning, EDM, gears and grinding" (gear generating); MFG Phasing, phase 2
**Problem:** Phase 2 promises hobbing, shaping and power skiving "through machine cycles", but gear machines are programmed through the builders' gear software, as parameter sets rather than ISO 6983 programs. Power skiving also needs synchronized multi-axis motion that phase 2's 3+2 collision check does not cover. The stated fix for an unsupported machine, 5-axis gear milling, is phase 3. GP3 needs neither capability if the shop cuts its gears.
**Evidence:** MFG: "Gear generating | Hobbing, shaping and power skiving from MEC's gear record through machine cycles | `Unsupported`; fix: 5-axis gear milling | MFG-O-GEAR-1 | 2"; "5-axis gear milling ... 3"; "Machine collision ... 2 (to 3+2), 3 (5-axis)".
**Fix:**
1. Phase 2 gear output is the gear data table and inspection plan (R10-18) for the shop's own gear process. Crucible programs cut GP3's housings, shafts and blanks.
2. Gear generating moves to phase 4. Before it ships, MFG names for each machine family whether output is ISO cycle calls or a parameter set for the builder's software.
3. Power skiving waits for simultaneous 5-axis collision checking.

### R10-20 · Major · Targets: MFG, MEC, ECO
**Section:** MFG "Sheet cutting, nesting and press brake"
**Problem:** GP4 needs press-brake planning and profile cutting in phase 2, but neither has an output a machine reads. Posts cover four milling and turning families. No press-brake control, laser, plasma or waterjet controller is named, and press brakes are usually programmed in the builder's offline software or at the control. A bend plan without an output becomes a paper note.
**Evidence:** MFG rows "Press-brake planning | Bend sequence, tool stations and backgauge" and "Profile cutting and ordering", both phase 2. Posts: "Fanuc, Haas, Siemens and Heidenhain".
**Fix:**
1. Press brakes, phase 2: a bend sheet generated as an Ingot drawing (sequence, punch and die ids and stations, backgauge positions, target angles, flange lengths, the flat pattern with bend lines), plus a STEP of the bent part and the flat DXF, which brake offline software imports.
2. Profile cutting, phase 2: a generic ISO 6983 cutting post whose pierce, lead-in and process codes are `Controller` data, plus the DXF hand-off for the cutter's own CAM.
3. Native press-brake programs arrive in phase 3 through `send_to_machine` (R10-04), for families named after a survey of the reference shop.

### R10-21 · Major · Targets: MEC, MFG, ING
**Section:** MEC "Tolerancing" (stack-up, completeness); MEC "Drawings" (general-tolerance tables)
**Problem:** Most dimensions on a real part carry no explicit tolerance. A general tolerance governs them: ISO 2768-1 classes, an ISO 22081 general specification, or an ASME title-block rule. In Crucible an untoleranced length is exact. A worst-case stack counts it as zero, MFG extracts no characteristic for it, cost ignores it, and inspection has no limit for it. The general tolerance exists only as a drawing table.
**Evidence:** MEC: "Size tolerances are `Tol<T>` values"; "Worst case | Affine `Tol` sum over a closed, signed contributor chain"; drawing row "hole and general-tolerance tables".
**Fix:**
1. Add `general_tolerance(standard, class)` to `std::mech::tol` as a Part-level record (ISO 2768-1 class, ISO 22081 general specification, or ASME decimal-place rules) that the drawing renders.
2. Stacks, characteristic extraction, inspection plans, tolerance-driven cost and KLN's definition tolerance read it for every untoleranced size, location and angle. Reports label those contributors "general".
3. Ingot arithmetic is unchanged: the record applies at the tolerancing layer.
4. A Part without a general tolerance fails `check::standards` before release.

### R10-22 · Major · Targets: MFG, ECO, CONTRACT
**Section:** MFG "Additive processes and build preparation" (category table); MFG Phasing, phase 2; contract 13.1, phase 2
**Problem:** The phase 2 gate needs "one additive part printed through Crucible's slicer" without naming a process. MFG's phase 2 powder-bed output is "own scan vectors in 3MF Toolpath", an extension MFG itself calls "still a draft", and no tab names a machine or build processor that reads it. If the gate part is metal PBF, the gate depends on a format nobody consumes.
**Evidence:** MFG: "Powder bed fusion ... own scan vectors in 3MF Toolpath (2)"; "the Toolpath extension was updated on 17 September 2026 and is still a draft".
**Fix:**
1. Contract 13.1 names the phase 2 slicer part as material extrusion on an open-firmware printer (Klipper or RepRapFirmware), sent through `send_print_job`.
2. PBF scan vectors move to the phase in which a named machine partner accepts 3MF Toolpath or another open vector format, recorded with contract 13.2's partner agreements.
3. Metal PBF compensation (MFG-O-AM-8) stays a geometry change sent through the vendor's build processor.

### R10-23 · Major · Targets: MFG, ECO, CONTRACT
**Section:** MFG D-MFG-11, D-MFG-25 and "Slicer hand-off"; contract 13.1 (GP2) and 13.2 (phase 0 agreements)
**Problem:** GP2 is a lattice part printed in phase 1 "with the printer vendor's slicer" from Crucible's 3MF. Nothing states whether that build processor reads the 3MF Beam Lattice extension, and MFG-O-AM-2 names only three FFF slicers. A dense lattice triangulated for a processor that does not read it is the bottleneck D-MFG-11 cites. For example, a 100 mm part with 2 mm cells has about 1.25 × 10⁵ cells. At about 10³ triangles per cell for a 10 µm chordal error, that is of the order of 10⁸ triangles (estimate).
**Evidence:** D-MFG-11: "triangulating a dense lattice is the bottleneck of conventional build preparation". MFG-O-AM-2: "Each named slicer opens the 3MF with plates, orientation and settings intact". ECO's phase 1 3MF scope is Core, Production, Materials and Beam Lattice.
**Fix:**
1. The phase 0 print-bureau agreement includes a file-acceptance test of the bureau's build processor on three files: a 3MF with Beam Lattice, a 3MF of Core triangles at a stated chordal error, and a sliced build where the processor takes one.
2. MFG-O-AM-2 extends to that build processor.
3. MFG states a mesh-export target for GP2 (triangle count, chordal error and file size, labelled as targets), and the GP2 lattice density is chosen within it.

### R10-25 · Major · Targets: ELX, MFG
**Section:** ELX "Design rules and the constraint manager" (D-ELX-24)
**Problem:** Spacing comes either from fabricator minimums or from an isolation barrier declared under a safety standard. Most boards also carry functional voltages (24 V, 48 V and 100 V buses) that cross no safety barrier but still need voltage-dependent spacing. Board designers take it from IPC-2221's conductor-spacing table, which separates internal layers, uncoated and coated external layers, and altitude. Without it they hand-write rules. Conformal coating changes those values and needs keep-outs over connectors and test points, yet has no record either.
**Evidence:** ELX's rule example uses only `fab.min_space` and `iso.creepage()`. Neither ELX nor MFG refers to IPC-2221 or coating.
**Fix:** Both arrive in phase 3 with DRC.
1. Add `functional_spacing(nets, voltage)` to `std::electronics::rules`. It reads a licensed IPC-2221 data package [unverified edition] with columns for internal, external uncoated by altitude, external coated, and assembly. Voltages come from `Power` ranges and net classes.
2. Add a `conformal_coating` board record (material, thickness, keep-out regions). It selects the coated column, feeds MFG's assembly package, and fails test-point access checks under coating.

### R10-27 · Major · Targets: MFG
**Section:** MFG Oracles
**Problem:** Several MFG oracles have no machine-checkable pass criterion:
- MFG-O-MOLD-4 names "a published plaque benchmark [unverified which]".
- MFG-O-FORM-2 and MFG-O-JOIN-2 cite published benchmarks marked [unverified], and MFG-O-BULK-1 cites "published die-fill and load benchmarks".
- MFG-O-TOOL-2 ("Predicted changes against as-run records") and MFG-O-FEED-2 ("Predicted power matches measured") state no tolerance.
- MFG-O-AM-7 and MFG-O-TREAT-2 measure "where data exist" or "on golden parts" without a bound.
- MFG-O-NEST-1 targets sparrow's density "at equal work", but sparrow's published runs are wall-clock limited, so "equal work" is undefined.
**Evidence:** The oracle rows quoted above. Sparrow's README sets a global time limit, 600 s by default (https://github.com/JeroenGar/sparrow).
**Fix:** Give each oracle a dataset and a number:
- springback on named NUMISHEET benchmark cases [unverified edition], within a stated angle;
- weld residual stress on the NeT TG1 single-bead plate [unverified], within a stated MPa band;
- fibre orientation on Bay and Tucker's centre-gated disk data [unverified], within a stated error in the orientation tensor component a₁₁;
- AM-Bench bridge-structure deflection within 10% (target);
- tool-life prediction within ±25% of as-run counts (target);
- spindle power within 10% of spindle-load data (target);
- nesting density within one point of sparrow at equal wall-clock time on the reference laptop, with the work-unit budget calibrated to that time.

Loosening any tolerance needs human approval, as ELX's oracles already state.

### R10-28 · Major · Targets: MFG, PLT, CONTRACT
**Section:** MFG Open questions 12; D-MFG-20 and D-MFG-24; contract 12
**Problem:** The gateway carries most of the shop-floor safety logic: hash and read-back, offset checks, edit capture and DNC, plus R10-01's egress filter, R10-02's pull path and R10-11's registry. Yet no crate, platform, packaging or network posture is specified. Shop DNC computers often run Windows, many lack a TPM, and an OT network must not accept inbound connections from the office network.
**Evidence:** MFG OQ12: "Contract 12's crate map lists no gateway app under `apps/`". MFG: "Gateway | Shop-network gateway for machines, printers and CMMs; device key under measured boot; offline buffering".
**Fix:** Answer to MFG OQ12.
1. Contract 12 adds `apps/gateway`, owned by MFG and packaged by PLT for Linux x86-64 and ARM64 and Windows 11 x86-64.
2. The gateway connects outbound only, as KLN's runners do, so the factory network needs no inbound ports. It runs connectors out of process (contract 7.4) behind its own wire-level egress filter.
3. Signing External inputs requires TPM 2.0. A gateway without one may transfer programs, but its readings carry `data_untrusted` and cannot serve `SignOff` checks.
4. The safety functions (no start, pull-only DNC, the registry) live in the gateway's core, never in connectors, so a connector update cannot change them.
5. Network guidance cites IEC 62443-3-3 zones and conduits [unverified edition].

### R10-29 · Major · Targets: MFG
**Section:** MFG Open questions 2; MFG-O-POST-1; MFG-O-SIM-2
**Problem:** Post qualification and the crash corpus need each control family's real interpolation of rapids, rotary unwinding and reference returns. MFG asks whether physical controls or licensed virtual controllers should provide it. A crash corpus cannot run on a machine with axes enabled, and virtual controllers do not exist for every family.
**Evidence:** MFG OQ2. MFG: "A family's post ships only after zero false negatives on the controller-semantics crash corpus."
**Fix:** Answer to MFG OQ2.
1. Capture on the reference shop's physical controls, in each family's program-test mode (machine lock or dry-run graphics), in which the control interpolates and reports positions while axes stay still [unverified mode names per family].
2. Sample commanded positions through the vendor connector or MTConnect. Licensed vendor programming stations serve only as a second source.
3. A family's post ships when the captured traces of the whole crash corpus match the simulator's `MotionSemantics` within the declared tolerance.
4. The reference-shop agreement in contract 13.2 adds controller-capture time.

### R10-31 · Minor · Targets: MFG, AGT
**Section:** MFG D-MFG-20; "No motion commands" row; MFG-O-SAFE-3
**Problem:** The OPC UA rule is a denylist. ISA-95 Job Control defines eleven methods. MFG forbids `Start`, `StoreAndStart`, `Resume` and `RevokeStart` but says nothing of `Update`, `Pause`, `Stop` or `Abort`, while `RevokeStart` only withdraws permission and is harmless. A connector author can read the gap as permission to call `Update` on a running job.
**Evidence:** OPC 10031-4 section 6.3 lists Store, StoreAndStart, Start, RevokeStart, Pause, Resume, Update, Abort, Stop, Cancel and Clear (https://reference.opcfoundation.org/ISA95JOBCONTROL/v200/docs/6.3).
**Fix:** State an allowlist everywhere. Crucible calls `Store` only inside `store_machine_job`, and `Cancel`, `Clear` and `RevokeStart` only on jobs it stored that have not started. Every other method is uncallable. MFG-O-SAFE-3 checks the allowlist, together with R10-01's wire criterion.

### R10-32 · Minor · Targets: MFG, KLN
**Section:** MFG D-MFG-24 (edit capture); KLN "Change orders" (Deviation)
**Problem:** MFG says parts made from a program edited at the control "get an as-built deviation". In KLN, though, a deviation is a pre-approved, time-limited departure granted by the `grant_deviation` Act. A part made from an unapproved program is a nonconformance awaiting disposition, so one word names two concepts.
**Evidence:** MFG: "parts made from it get an as-built deviation". KLN: "Deviation | A temporary departure for given serials or lots, with expiry; granted by the `grant_deviation` Act".
**Fix:** MFG writes "a nonconformance record, linked to the serials, for disposition" (its "Nonconformance" capability), and "deviation" keeps KLN's meaning.

### R10-33 · Minor · Targets: MFG, ECO
**Section:** MFG "Factory connection and digital twin" (MES and ERP mapping); ECO "Enterprise connectors"
**Problem:** ECO ships ERP and MES connectors in phase 2 and says Crucible owns MBOM and routings where it plans manufacturing. MFG ships MBOM and routings in phase 2 but maps routings and work orders through the connectors only in phase 4. Phase 2 MES connectors therefore carry no routing data.
**Evidence:** ECO: "ERP and MES connectors | Mapped records out; External inputs in; field ownership | ... | 2". MFG: "MES and ERP mapping | Work orders, routing status, scrap and labor ... | 4"; "MBOM and routings ... | 2, 3".
**Fix:** MFG moves the outbound routing and work-order mapping to phase 2, with its MBOM and routings. Scrap, labor and status feedback may stay in phase 4.

### R10-34 · Minor · Targets: MFG, ELX
**Section:** MFG "Electronics and harness manufacturing handoff"; ELX D-ELX-23; ELX "Pours, planes and vias"
**Problem:** Three gaps remain in the board-house vocabulary:
- MFG's fabrication package omits the IPC-D-356 netlist, which ECO writes and many fabricators use for bare-board test of Gerber packages.
- Vias have no IPC-4761 protection type (tented, plugged, filled, capped), which via-in-pad needs on the fabrication drawing.
- Classes start at 2, though Class 1 governs much consumer work.
**Evidence:** MFG's package list: "IPC-2581C, Gerber X2, XNC drill and route, Gerber job file, impedance and stackup tables, or ODB++". ECO: "Gerber, XNC, IPC-2581C, ODB++, IPC-D-356, placements". ELX: "Class 2, 3 or 3/A".
**Fix:**
1. Add IPC-D-356 to the Gerber package list.
2. Add `protection: Ipc4761Type` per via class, with a fabrication-drawing note and a DFM rule for via-in-pad [unverified edition].
3. Accept Class 1 in `fab_class` and `assembly_class`.

### R10-35 · Minor · Targets: MFG
**Section:** MFG "Additive processes and build preparation" (Bambu); Open questions 9
**Problem:** MFG says "Crucible reaches Bambu printers only through that path" (Bambu Connect). Bambu later added an optional LAN Developer Mode that leaves MQTT, the live stream and FTP open, without vendor support, so the claim is out of date.
**Evidence:** Developer Mode lets users "leave the MQTT channel, live stream, and FTP open", and Bambu "will not be able to provide customer support for this mode" (https://blog.bambulab.com/updates-and-third-party-integration-with-bambu-connect/).
**Fix:** Answer to MFG OQ9. Support two paths and replace "only through that path":
1. On printers the owner sets to Developer Mode, `send_print_job` uploads over FTP only and never sends an MQTT print command. The site policy records that the owner accepted an unsupported mode.
2. Otherwise the desktop client hands the job to Bambu Connect, where a person starts it.

### R10-37 · Minor · Targets: MEC, MFG
**Section:** MEC Open questions 3
**Problem:** MEC asks which processes accept a released part with an implicit blend region. The answer decides a release check.
**Evidence:** MEC OQ3: "Which processes accept a released part with an implicit region? Proposal: MFG process rules decide".
**Fix:**
1. Only processes that consume implicit or mesh geometry accept implicit regions: additive through 3MF.
2. Any process whose hand-off is STEP (machining, molding, sheet) requires conversion to B-rep before release, with the deviation inside the face's tolerance or general tolerance (R10-21).
3. MFG's process rule checks this, and `check::standards` enforces it.

Shops' CAM and CMM software read B-rep, not implicit fields.

### R10-40 · Minor · Targets: MFG
**Section:** MFG Open questions 3, 7 and 8
**Problem:** Three open questions on anytime budgets, the COV–MFG data boundary and stock representation have no proposed answers.
**Evidence:** MFG OQ3 ("run for 10 minutes"), OQ7 ("Where does COV's material model ownership end"), OQ8 ("A benchmark run before phase 2 decides").
**Fix:**
- OQ3: Keep fixed work budgets per evaluation class, shown as an estimated time on the reference laptop. Offer "continue", which warm-starts from the best result with a larger budget; warm starts never worsen a result (MFG-O-NEST-1).
- OQ7: COV owns material state models and their envelopes: Cross-WLF, Tait pVT, solidification paths and fraction-solid curves. MFG owns process parameters, machine and mould data, coupon programs and calibration records. A coefficient fitted from a process coupon lives in MFG's process profile and cites COV's model id.
- OQ8: Benchmark GP3's programs at each setup's stated stock tolerance. Choose tri-dexel only if it meets the tolerance with no more memory than the grid and within PLT's heavy-worker cap.

### R10-42 · Minor · Targets: MEC, MFG
**Section:** MEC "Weldments and structural frames"; MFG "Welding, joining and composites"
**Problem:** In Europe, welded structural steel is made to EN 1090-2 execution classes. The class sets the ISO 5817 level, the NDT extent and the ISO 3834 quality requirements. GP8's platform needs one, as do many frames like GP4's, but neither tab records it.
**Evidence:** MEC's `Weld` record carries "the imperfection quality level: ISO 5817 level B, C or D, or AWS D1.1 acceptance criteria", with no execution class. MFG lists procedure standards only.
**Fix:**
1. Add `execution_class: Exc1..Exc4` (EN 1090-2 [unverified edition]) to weldment Parts.
2. MFG derives default quality levels, NDT extent and the required ISO 3834 part from it.
3. Phase 2 records the class, and phase 5 enforces it for GP8.

### R10-43 · Minor · Targets: MFG
**Section:** MFG "Assembly and work instructions" (robot programming)
**Problem:** The robot post list hides how each program reaches its controller. FANUC TP programs are binary on the controller; a post can produce only the text form, which needs a paid ASCII-upload option or the vendor's offline converter [unverified]. Other families have their own loading conventions.
**Evidence:** MFG: "posts to RAPID, KRL, FANUC TP, INFORM and URScript [unverified] without safety configuration".
**Fix:**
1. For each robot family, the machine package states the output file type and its loading path.
2. A post fails with `Unsupported { capability: AsciiUpload }` when the controller lacks the option it needs.
3. R10-01 applies to every family's loading path.

### R11-07 · Major · Targets: MFG, AGT, KLN
**Section:** MFG "Approval, transfer and physical safety" (D-MFG-24), "Factory connection and digital twin" (D-MFG-20); AGT D-AGT-31
**Problem:** The gateway checks a short content hash that the post writes into the program header, which detects corruption but not substitution: a compromised server, relay or account can send any program with a self-consistent header, and the gateway never verifies that an assigned human approved that program. The approval therefore ends at the server, not at the machine. No tab states OPC UA security mode or certificate trust for the gateway's sessions.
**Evidence:** D-MFG-24: "Posts write item, revision, release id and a short content hash into the program header, and the gateway recomputes the hash on transfer and on read-back." D-AGT-31 makes approval "of the exact plan" the safety control. MFG has no occurrence of an OPC UA security policy or IEC 62443.
**Fix:** Add to D-MFG-24: the gateway transfers only a program whose full SHA-256 appears in an `ActionPlan` carrying a valid Approval assertion from a principal in the gateway's locally pinned approver set (a signed directory plus a transparency-log checkpoint), verified on the gateway itself; the short header hash stays only for operator display. OPC UA sessions use `SignAndEncrypt` with application certificates in a trust list managed by the site, and the gateway sits in an OT zone with one outbound conduit. Extend MFG-O-SAFE tests with a forged plan from a compromised server.

### R12-11 · Major · Targets: CONTRACT, MFG, ECO, FLX, COV
**Section:** CONTRACT 13.1 (GP2), 13.2 Chain B, 13.4 (inherent strain, phase 1); MFG Additive (D-MFG-25); ECO 3MF row
**Problem:** GP2's process is not defined, and the tabs assume incompatible ones. Inherent-strain prediction (phase 1 via contract 13.4) is a metal powder-bed method that "needs per-machine calibration" from MFG's coupons, yet D-MFG-25's hand-off names three FFF slicers. Crucible must mark 3MF's Beam Lattice extension as required, and a consumer that does not support it must refuse the file, so GP2 prints only if the vendor's build software reads beam lattices. Chain B also omits the calibration build that inherent strain needs before GP2 can be predicted.
**Evidence:** Contract 13.1: GP2 is "printed from Crucible's 3MF with the printer vendor's slicer". MFG: "FLX owns inherent-strain layer activation and prediction, from MFG's calibration coupons. The method is layer-lumped, so it needs per-machine calibration"; MFG-O-AM-8: "metal PBF build of GP2 within 0.1 mm in phase 2". D-MFG-25: a 3MF build "that OrcaSlicer, Bambu Studio and PrusaSlicer read". ECO phase 1: "GP2: 3MF with beam lattice". 3MF Beam Lattice 1.2.0: producers "MUST mark the "b" extension as required" (https://github.com/3MFConsortium/spec_beamlattice/blob/master/3MF%20Beam%20Lattice%20Extension.md). 3MF Core: "Editors and manufacturing devices MUST NOT process this model-file if they do not support the required extensions" (https://github.com/3MFConsortium/spec_core/blob/master/3MF%20Core%20Specification.md).
**Fix:** In phase 0, fix GP2's process, alloy or polymer, machine, print bureau, the vendor's build-preparation software and the 3MF extensions that software accepts, and record them in contract 13.1.
- **Metal powder-bed fusion:** Chain B gains "calibration coupons printed and measured (month 16) → inherent-strain calibration (month 18)" before the month-20 dry run. If the vendor software lacks Beam Lattice, Crucible writes a mesh 3MF with a declared triangle budget beside the beam-lattice file. D-MFG-25 adds the metal build-preparation software.
- **Polymer FFF:** inherent strain leaves phase 1 through a contract 13.4 change, and GP2 uses a strut lattice exported as a mesh, since the named FFF slicers are not shown to read beam lattices.

### R12-16 · Major · Targets: AGT, KLN, MFG, UIX, CONTRACT
**Section:** AGT Acts and approvals (D-AGT-20, D-AGT-30); KLN Phasing (`release_data` for STEP and 3MF exports); MFG D-MFG-25
**Problem:** Every byte that leaves a tenant goes through the `release_data` Act family, and every Act needs an assigned Approval on the server's page with WebAuthn. KLN applies this to STEP and 3MF exports in phase 1, and no tab says where the tenant boundary lies for a local file. So the phase 1 wedge user, who hands a 3MF to their own slicer (D-MFG-25) or saves a STEP file for a shop, needs a team server, an inbox, a passkey and a recipient record for each export. The spec does not define whether a desktop install without a server can export at all.
**Evidence:** D-AGT-30: "Every byte that leaves a tenant goes through one Act family, `release_data` ... restricted-party screening ... audit". D-AGT-20: "`act.commit` creates an approval request that Cedar policy assigns to named approvers ... after phishing-resistant WebAuthn user verification". KLN phase 1: "`release_data` for STEP and 3MF exports". D-MFG-25: Crucible "writes a 3MF build ... and opens it there". Contract 13.1 names phase 1 the "Wedge: code-CAD and 3D printing".
**Fix:** In D-AGT-30 and KLN, define the tenant boundary for local files. A human principal writing an export to a local folder or a local application is an audited local write, not an Act, when the payload's label is `public` or `internal`, carries no export control, and is not addressed to a recipient record. Agent-prepared exports, labelled or controlled payloads, and every transfer to another organization stay `release_data` Acts. State in contract 13.2 whether phase 1 supports a desktop install without a team server, and what it can do.

### R12-25 · Minor · Targets: CONTRACT, MFG, ECO
**Section:** CONTRACT 13.2 milestones (hardening months 24–32, physical runs 30–34, gate 36)
**Problem:** GP1 and GP2 are made in months 30 to 34 from outputs of a build that hardening keeps changing until month 32, so the release judged at month 36 is not the one whose STEP and 3MF files produced the measured articles. The gate does not say how the two are tied.
**Evidence:** Contract 13.2 milestones: "24–32 | Hardening ..."; "30–34 | GP1 and GP2 physical runs, with one re-run budgeted"; "36 | Phase 1 gate".
**Fix:** Contract 13.1 adds that the gate release must reproduce the run build's exported STEP AP242 and 3MF bit for bit (equal `ObjectId`s), or else show equal `GeometryId`s and PMI with a reviewed diff of non-geometric content. Otherwise the run repeats. The run build is tagged at month 29.

## Claims the reviewers verified

Drop the `[unverified]` marker on these and cite the URL in Sources.

- ISA-95 Job Control defines eleven job-order methods, among them `StoreAndStart`, `Start`, `RevokeStart` and `Resume` | https://reference.opcfoundation.org/ISA95JOBCONTROL/v200/docs/6.3 (R10)
- OPC 40001-3 (Machinery Job Management) is at 1.0.1 of 1 May 2024 | https://reference.opcfoundation.org/Machinery/Jobs/v100/docs/ (R10)
- the EU Machinery Regulation applies from 20 January 2027 with cyber-safety provisions | https://single-market-economy.ec.europa.eu/sectors/mechanical-engineering/machinery_en (R10)
- Bambu Connect "removes slicing functions while enabling remote control and print initiation" | https://blog.bambulab.com/firmware-update-introducing-new-authorization-control-system-2/ (R10)
- sparrow is MIT-licensed | https://github.com/JeroenGar/sparrow (R10)
- robot safety documentation cites ISO 10218-1:2025 and ISO 10218-2:2025 (marked [unverified] in the tab; both valid from 5 February 2025) | https://www.evs.ee/en/iso-10218-1-2025 and https://www.evs.ee/en/iso-10218-2-2025 (R10)
- weld procedure records follow ISO 15614-1 and ISO 15609-1 ([unverified editions] in the tab; current editions are ISO 15614-1:2017 with Amd 1:2019 and ISO 15609-1:2019) | https://www.evs.ee/en/iso-15614-1-2017 and https://www.evs.ee/en/iso-15609-1-2019 (R10)
- AIAG lists the PPAP manual under the identifier PPAP-4 | https://www.aiag.org/training-and-resources/manuals/details/PPAP-4 (R10)

## Unverified claims in your tab

Verify each with WebFetch on a primary source and drop the marker, correct it, or cut the claim if nothing supports it. Line numbers are at tag `round-2`.

- l.144: **Decision D-MFG-23:** Collision simulation and the independent re-interpreter both execute the posted NC text under the controller's declared `MotionSemantics`, never the pre-post toolpath. Where a semantic is undeclare
- l.152: ISO 6983-1:2009 defines the format and address words, confirmed in 2025 [ISO 6983-1]. Posts read capability flags, not vendor names; the codes below come from manuals not opened [unverified], and each family's conformanc
- l.180: A tool is an Assembly of catalog parts whose ISO 13399 properties are typed Quantities; ISO confirmed part 1 in 2021 [ISO 13399-1]. Vendors publish catalogs as packages built on ISO 13399 and DIN 4000 [unverified], shops
- l.258: | Grinding, broaching, honing and lapping | Gear and profile grinding with distortion allowance; surface and cylindrical grinding with a burn-risk Field [unverified]; process records | `MissingData`; `OutsideEnvelope` fo
- l.341: STEP-NC is ISO 14649, in parts for process data, milling, turning, tools, EDM and additive [ISO 14649 catalog]. AP238 edition 3 (ISO 10303-238:2022) adds geometry, GD&T and kinematics [ISO 10303-238; STEP Tools AP238e3].
- l.366: **Decision D-MFG-25:** In phase 1, and for FFF until Crucible's slicer passes its comparison, Crucible hands builds to the user's slicer. It writes a 3MF build with plates, per-object orientation, modifiers and settings 
- l.406: FLX owns inherent-strain layer activation and prediction, from MFG's calibration coupons. The method is layer-lumped, so it needs per-machine calibration and cannot see melt-pool effects [unverified], which COV owns. DfA
- l.444: **Decision D-MFG-29:** Short-fibre orientation uses an anisotropic rotary diffusion model with reduced strain closure (ARD-RSC) and a fitted closure, keeping Folgar–Tucker as the L0 model level (COV). Warpage comes from 
- l.446: The Hele-Shaw envelope defaults to local thickness under one tenth of local flow length, calibrated in phase 3 [unverified].
- l.491: MEC owns weld joints, symbols and laminate design; MFG owns procedures, sequences, paths, distortion and laminate manufacture. Procedure, procedure-qualification and welder records follow ISO 15609-1, ISO 15614-1 and ISO
- l.527: **Decision D-MFG-16:** The default fabrication package is IPC-2581 revision C together with Gerber X2 layers (Layer Format revision 2026.05), an XNC drill file and the Gerber job file, generated from one board model. ODB
- l.529: Boards carry `fab_class` and `assembly_class` (Class 2, 3 or 3/A) that select rule packs citing IPC-6012, IPC-A-600, IPC-A-610 and J-STD-001, pinned in licensed packages [unverified revisions].
- l.540: | Harness manufacturing package | 1:1 formboard from MEC geometry with branch lengths and tolerances; connector face views from the mating side with cavity numbers; cut list with gauge, colour, cut and strip lengths; ter
- l.548: Robots are Machines sharing kinematics, collision and posts with machine tools. Robot programs are proved first in manual reduced-speed mode and never change safety-rated zones or speed limits. The safety documentation c
- l.554: | Design-for-assembly | `dfa(assembly) -> DfaReport`: separate-part test, handling and insertion times from tables after Boothroyd and Dewhurst [unverified], efficiency index | Instances without data listed as undetermin
- l.556: | Robot programming | Targets, external axes and positioners, collision-free planning on a counter-based seed; posts to RAPID, KRL, FANUC TP, INFORM and URScript [unverified] without safety configuration; cycle time | `U
- l.561: MEC owns GD&T semantics; MFG owns how characteristics are measured, evaluated and reported. QIF is ISO 23952:2020, confirmed in 2026 [ISO 23952]; DMIS remains common for CMMs [unverified].
- l.585: Per the IAQG summary of 9102 revision C, FAI is not product acceptance, each item needs its own FAI, and Form 1 gains "FAIR Verified By" [IAQG 9102C]. AIAG lists PPAP-4 [AIAG PPAP] and the AIAG & VDA FMEA Handbook [AIAG-
- l.620: ECO specifies the `erp-connector` and `mes-connector` worlds in `crucible:connect` with OAGIS and B2MML messages (D-ECO-30) [unverified versions]. MFG supplies routings and reads costs, lead times and inventory back as E
- l.641: ISO 14044:2006, amended in 2017 and 2020 and confirmed in 2022, sets LCA requirements [ISO 14044]; ISO 14040's current edition is [unverified]. MFG computes the cradle-to-gate inventory from the process plan and end of l
- l.645: Implementing Decision (EU) 2026/1736 references EN 18216, 18219, 18220, 18221, 18222 and 18223 [EUR-Lex 2026/1736]. EN 18239, EN 18246 and the delegated-act timetable come from vendor summaries [unverified] [Renoon DPP u
- l.657: | Impact, hotspots and uncertainty | Versioned factor packages (EF or ecoinvent under licence [unverified versions]); contributions; Monte Carlo (4) | Unlicensed datasets unavailable, never substituted | MFG-O-SUST-2 | 3
- l.661: | Battery passport | Battery Regulation elements for GP6's pack where in scope [unverified dates] | As mapping | MFG-O-DPP-1 | 4 |
- l.662: | RoHS, REACH and SCIP | Ten RoHS substances per homogeneous material against Annex II [EU RoHS] [unverified values]; Candidate List above 0.1% w/w, Annex XVII, SCIP data (3); IPC-1752B declarations read in A and B forms
- l.664: | Other regimes | Packaging, batteries, WEEE marking, TSCA, Proposition 65 [unverified] | As RoHS | MFG-O-REG-1 | 4 |
- l.672: | Adaptive clearing | Constant engagement; parameter-varied trochoids [Li et al. 2025] | Mastercam Dynamic, Fusion adaptive, hyperMILL, NX [unverified] | Medial-axis spiral measured on stock (D-MFG-7), after freedom-to-o
- l.674: | Collision and NC verification | Continuous collision detection on the posted code | ModuleWorks 5-axis [ModuleWorks]; VERICUT [unverified] | Posted text under declared motion semantics (D-MFG-23); certified per-move go
- l.675: | Material removal | Adaptive tri-dexel on GPU [Ozcan et al. 2024] | ModuleWorks GPU simulation, VERICUT [unverified] | Adaptive narrow-band stock (D-MFG-6); tri-dexel as render cache and benchmark candidate | Volume err
- l.676: | Feeds and speeds | Mechanistic force models with constrained optimization | CloudNC [CloudNC CAM Assist]; VERICUT Force [unverified] | Source-labelled defaults, advisory model, calibrated optimization (D-MFG-27) | Cycl
- l.684: | Multi-axis slicing | Quaternion-field curved layers [Zhang et al. 2022] | Research code [unverified] | Adopt in phase 4 | Support-free coverage and collision-free order on the paper's models |
- l.685: | Lattices | Implicit, Field-driven lattices | nTop [unverified] | MEC lattices checked and written without meshing | Relative density error under 1% |
- l.686: | PBF distortion | Inherent strain; layer thermo-mechanics [unverified] | Magics with Ansys [Materialise Magics]; Fusion [Fusion Manufacturing Extension] | Both in Flux with Field-driven compensation (D-MFG-13) | AM-Benc
- l.687: | Injection molding | 3D non-isothermal flow, pvT; ARD-RSC orientation [unverified] | Moldflow [Moldflow] | Level-set 3D at `SignOff`, Hele-Shaw at `Interactive` (D-MFG-15, D-MFG-29) | Analytic cases; GP5 short shots and
- l.689: | Sheet forming | Incremental shell FEM with compensation | AutoForm [AutoForm] | Flux shells, Field-driven compensation | Published springback benchmarks [unverified] |
- l.690: | Weld distortion | Inherent strain (structure); transient thermo-mechanics (joint) [unverified] | Simufact Welding, SYSWELD [unverified] | Both in Flux by envelope | GP4 distortion inside the prediction band |
- l.693: | Robot offline programming | Redundancy-resolved collision-free planning | RoboDK, Process Simulate [unverified] | Robots as Machines sharing CAM kinematics and posts | Re-interpreted programs reproduce motion; cycle ti
- l.694: | Inspection | Model-based QIF plans [ISO 23952]; GUM and JCGM 101 [BIPM JCGM] | PC-DMIS, CALYPSO, PolyWorks [unverified] | Provenance identities (D-MFG-18), stable balloons (D-MFG-26), typed budgets | QIF round trip; JC
- l.696: | Machine connectivity | MTConnect 2.5 [MTConnect 2.5]; OPC 40501-1 [OPC 40501-1] | Vendor MES connectors [unverified] | Read adapters, non-motion job management, signed inputs (D-MFG-20) | Conformance against reference 
- l.697: | PCB handoff | IPC-2581C with DFX [IPC-2581C]; Gerber 2026.05 [Ucamco Gerber downloads] | Siemens Valor NPI [unverified] | IPC-2581C with Gerber X2 by default, ODB++ through ECO's writer (D-MFG-16) | 1 µm XOR against in
- l.698: | Life-cycle assessment | ISO 14040 and 14044 process LCA [ISO 14044] | openLCA, SimaPro [unverified] | Inventory from actual process plans | Mass balance; reference product systems |
- l.826: | MFG-O-MOLD-4 | Orientation and warpage | A published plaque benchmark [unverified which]; GP5 short shots and warpage |
- l.831: | MFG-O-FORM-2 | Forming | Published formability and springback benchmarks [unverified]; continuity and tonnage recomputed |
- l.833: | MFG-O-JOIN-2 | Weld distortion | GP4 measured distortion inside the prediction band; published joint-scale benchmarks [unverified] |
- l.853: | MFG-O-INSP-4 | Evaluation and scans | Reference fitting sets in the style of ISO 10360-6 [unverified]; known transforms recovered |

## Your open questions

Close each: decide it (the reviewers propose answers above), move it to a contract change request, or keep it with the reason it cannot be decided yet.

1. **Freedom to operate.** Does an engagement-controlled spiral without a pre-roughing slot avoid US 9,164,503 and the other engagement-control families? Counsel's opinion gates adaptive clearing.
2. **Controller conformance.** Can the reference shop provide physical controls of each family for corpus capture, or must we license virtual controllers?
3. **Anytime quality.** Is a fixed default work budget per evaluation class acceptable to users who expect "run for 10 minutes"?
4. **Hele-Shaw envelope.** The thickness-to-flow-length default needs phase 3 calibration.
5. **Training data.** MFInstSeg and similar licences must permit commercial use of trained weights.
6. **Passport hosting.** Should Crucible operate a passport service, or only publish to third parties?
7. **Process-physics boundary.** Where does COV's material model ownership end and MFG's process data begin for melts and cast alloys?
8. **Stock representation.** A benchmark run before phase 2 decides between the adaptive narrow-band grid and tri-dexel stock (R2-24).
9. **Bambu access.** Whether Bambu's partner documentation permits job upload from the gateway is unknown [Bambu Lab 2025].
10. **Findings applied with a later phase.** Contract 13.2 defers CAM, posts and stock simulation, and GP1 uses the shop's CAM, so these land in phase 2 instead of 1:
    - R4-05 (DNC), R4-06 (setup sheet), R4-07 (3+1 indexing, vises, probing) and R4-08 (Ingot hooks);
    - R4-09 (`verify_nc`), R4-10 (tool importers, count-based life) and R4-12 (edge-break toolpaths);
    - R4-35's controller families, each one phase later than proposed;
    - R4-01's transfer Acts, so its reason for moving AGT's Acts to phase 1 lapses, and agent-proposed programs, which move to phase 2 with AGT's CAM programmer role (R4-12).
11. **Findings declined in part.**
    - R5-18's rename of `send_to_machine`: R4-01, accepted in contract section 15, names `send_to_machine`, and contract 7.6 now fixes the list of physical-effect Acts. R5-18's semantics (delivery to the queue, start at the machine) are adopted.
    - R3-25's "licensed external tool" for ODB++ gives way to R4-27's own writer, which ECO builds.
    - R4-24's output writers stay ECO's under R3-25 and contract 7.7; MFG chooses the package.
    - Owned elsewhere, with MFG stating its side: R4-25's IPC-2152 screen and `test_point` features (ELX), R4-14's balloon annotation and R1-37's default distribution (MEC), R4-18's connector world (ECO), R5-05's recipient records (KLN) and R5-06's Act family (AGT).
12. **Machine gateway crate (round 3 contract request).** Contract 12's crate map lists no gateway app under `apps/` for the gateway (D-MFG-20, D-MFG-24). Round 3 should add one, owned by MFG and packaged by PLT.

## Known items

- Contract 17 rules on the machine gateway app; apply the ruling and close the open question.
- Add one sentence under each drawn diagram that tells the reader how to read it (`diagrams/07-manufacturing-program-release.jsx`, `diagrams/07-manufacturing-factory-feedback.jsx`).
