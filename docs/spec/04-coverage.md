# Physics coverage and materials (COV)

COV decides which physics Crucible can honestly claim, as versioned physics packages, and keeps the versioned material records every simulation reads. Where Ansys, Abaqus or COMSOL leave credibility to the analyst, every Crucible result states whether its model was tested in this regime, how wrong those tests say it may be, and what to use where no model is valid. The mechanism is the validity envelope, each model's record of where physical tests checked it, stored as data that compiles into checks on every result, which a clone cannot copy without running the tests.

## Trusting a result: the bracket

An engineer who reads a stress needs to know three things that numerical accuracy alone does not answer: whether the physics model applies here, how well it has been tested against reality, and how wrong the model's assumptions may make the number. This section walks the canonical bracket of contract section 6 through those questions and introduces the vocabulary the rest of the tab builds on.

### The bracket's check

The bracket's check reads `study.von_mises.max(over: study.regular())` and requires it to stay below `0.6 * p.material.yield_strength(at: 20degC)`. Behind `static_stress` sits a physics model, `std::physics::solid::linear_elasticity`, and behind `alu_6061_t6` sits a Material record. Both are packages that COV defines, and both are pinned in the design's `ingot.lock`, so the answer never changes unless someone changes a pin.

At `SignOff` fidelity, Flux reports the regularized peak at the web-root fillet as 94 MPa with a discretization bound of 1.5 MPa (FLX). A regularized peak is a stress averaged over a stated small region rather than read at one point, because a raw maximum depends on the mesh. Flux's bound is `Estimated`: it was multiplied by a calibrated factor, so it covers the true discretization error in all but a stated fraction α = 0.01 of cases.

The limit reads the Material's yield strength. For 6061-T6 the record holds a basis interval from 240 MPa, the specification minimum, to 276 MPa, so the limit is the interval 144 MPa to 165.6 MPa. A check written against a design basis must hold at the interval's conservative end, here 144 MPa, and the interval adds nothing to the error budget, because the design value is the requirement itself ([Materials](#materials)).

Three more questions decide whether 94 MPa may be compared with 144 MPa at all. COV answers each with a record attached to the result:

1. **Is the model valid here?** The model's validity envelope evaluates to a zone Field over the Part. At the fillet the stress ratio σ_eq/σ_proportional is about 0.5 and the temperature is 20 °C, both inside the conditions the model was validated at, so the zone is `Calibrated`.
2. **How well has the model been tested?** Linear elasticity holds credibility level C3 (Validated) for the response quantity "regularized surface peak at a fillet, linear elastic", because the phase 1 validation campaign measured exactly that quantity on separate 6061-T6 plates (contract 13.1).
3. **How wrong may the model's form be?** The validation campaign gives a model-form bound of 8.6% at the nearest validation point, which at 94 MPa is 8.1 MPa ([Model form](#model-form-how-far-tests-say-a-model-can-be-wrong) derives this number).

The check's total is then 94 + 1.5 + 8.1 = 103.6 MPa against a limit of 144 MPa. The verdict is `Pass` at confidence at least 1 − (0.01 + 0.05) = 0.94, stated at 95% confidence, because the discretization part carries α = 0.01 and the model-form part α = 0.05. The modulus does not appear in the budget: the bracket is loaded by a force, so its stress is insensitive to stiffness, and Flux's adjoint sensitivity to Young's modulus is zero.

### When the answers change

The same bracket shows what happens outside the comfortable case. Each outcome is a typed value, never a silent fallback.

| Change to the bracket | What COV reports | Verdict |
| --- | --- | --- |
| Run at 120 °C, where no validation plate was tested | Zone `Extrapolated`; the model-form part grows by the package's inflation factor, here 1.6 times to 12.9 MPa | `Pass` if the inflated total stays below the limit, with the zone named in the report |
| Run at 250 °C, beyond the range the inflation was fitted on | Model-form part `NotQuantified { reason: BeyondInflationFit }` | `Undecided { reason: Unquantified([ModelForm]) }` until a test, an allowance or a Waiver covers it |
| Raise the load to 3 kN, so the fillet yields | The stress-ratio bound is `Refuse`; `ValidityError::OutsideEnvelope` suggests `solid::finite_strain_plasticity` | `Error(Failure)` on the check; no Waiver applies |
| Swap to a new alloy with no validation data | The model is C2 for that Material: benchmarked, not validated | `Undecided { reason: Unquantified([ModelForm]) }` unless a pinned policy allowance covers model form |

Crucible never switches the model by itself. It names the valid model and the fix, and a person or agent edits the design.

### The vocabulary

Contract section 5.2 lists every qualifier a Crucible number carries, from fidelity to the merge gate. COV owns three of them and fills one part of the error budget:

- **Validity zone** (`Calibrated`, `Extrapolated`, `Invalid`, `Unassessed`): whether the model is inside the conditions where it was checked. [Validity envelopes](#validity-envelopes) defines it.
- **Model level** (L0 to L3): the form of physics that produced the number, from a handbook formula to a full 3D solve.
- **Credibility level** (C0 to C4): how well the model has been tested against reality, named after the credibility that ASME V&V 40 assesses [ASME V&V 40].
- **Model-form part** of the `ErrorBudget`: how wrong the model's equations may be, from validation data or from a policy allowance.

Flux owns the numerical parts of the budget and the bound kinds (FLX). The model level chooses the physics, and the `Fidelity` chooses how accurately Flux solves it; the two are independent, and both enter result provenance.

### Model levels

| Level | Form and typical cost | Error statement | Examples |
| --- | --- | --- | --- |
| L0 Analytic | Closed form, handbook or standard method; microseconds | Method assumptions plus model form | Beam formulas, Nusselt correlations, ISO 6336 gear ratings, Paschen breakdown |
| L1 System | Lumped or 1D Networks solved as DAEs (systems of differential-algebraic equations), with FMI 3.0.2 (Functional Mock-up Interface) export; milliseconds to seconds | As L0, plus Network discretization | Thermal RC networks, battery equivalent circuits, blade-element rotors |
| L2 Reduced | Projection (modal, Craig–Bampton, Krylov, proper orthogonal decomposition) or surrogates; milliseconds online | Estimator, or the surrogate's marginal coverage | Modal superposition, inherent strain, SPMe battery models (single-particle model with electrolyte) |
| L3 Full 3D | FEM (finite elements), IGA (isogeometric analysis), DG (discontinuous Galerkin), finite volume, BEM (boundary elements) or particles through Flux, including planar and axisymmetric sections; seconds to hours | Flux estimators plus model form | Nonlinear contact, large-eddy simulation (LES), full-wave electromagnetics |

Each domain publishes a ladder of rungs from L0 to L3, so an engineer can start with a formula and climb only as far as the question needs. Planar and axisymmetric models are L3 forms on a reduced section. They sit one rung below the 3D solid in the solid, thermal and magnetostatic ladders, and Flux returns `SymmetryBroken` when loads or geometry break the symmetry (FLX).

**Decision D-COV-2:** Each domain publishes a model ladder from L0 to L3, and adjacent rungs carry a consistency oracle inside the narrower rung's envelope.
*Why:* two forms that must agree, such as Euler–Bernoulli and a 3D solid within 1% at L/h ≥ 20 (target), catch errors that single-model benchmarks miss.
*Rejected:* verifying each level only in isolation; naming the rungs after fidelities, which collides with the three `Fidelity` names.

### Credibility levels

| Level | Meaning | Required results | Allowed use |
| --- | --- | --- | --- |
| C0 Declared | Implemented, not verified | None | Experiments; never decides `SignOff` |
| C1 Verified | Code verification passed | Manufactured solutions, conservation, derivatives, determinism | `Preview` and `Interactive` |
| C2 Benchmarked | C1 plus community benchmarks | NAFEMS, NASA TMR or TEAM values within stated tolerance | `SignOff` in the literature-documented zone; model form `NotQuantified` unless a policy allowance covers it |
| C3 Validated | C2 plus physical validation on held-out tests | ASME V&V 10 for solids [ASME V&V 10], V&V 20 otherwise [ASME V&V 20]; contract 13.1 replicates | Release gates, for the response quantities the validation plan lists |
| C4 Context-qualified | C3 plus a credibility package for a named context of use | ASME V&V 40 [ASME V&V 40], NASA-STD-7009B [NASA-STD-7009B] or FDA guidance [FDA CM&S credibility] | Regulated submissions; the authority decides |

A response quantity is the triple (quantity, location type, regime) that a validation plan measures: "regularized surface peak stress, at fillets, linear elastic" is one. Credibility belongs to a model and a response quantity together, so linear elasticity can be C3 for fillet peaks and C2 for bolt-hole bearing stress in the same release.

**Decision D-COV-3:** `std` physics decides `SignOff` checks only at C2 or above, and only CI-signed oracle results raise a level. A validation campaign on separate specimens raises a model to C3 for the response quantities its plan lists before any release relies on it, and golden-product proof loads then confirm it on held-out articles.
*Why:* V&V 40 ties credibility to how much a decision relies on the model [ASME V&V 40], and data that judged a model must stay out of the release they approve (contract 13.1).
*Rejected:* a single "validated" flag; levels assigned by agents; C3 from the very articles a release approves; C3 from one unreplicated article.

A C2 model's calibrated zone is the validation domain its cited literature documents, confirmed by a named human reviewer; bounds without one start `Extrapolated`.

**Decision D-COV-21:** Credibility levels describe models, never single results. Whether one solve was checked for convergence is recorded on its discretization part, which names its source: an a posteriori estimator or a convergence study (FLX); a part with neither is an `Indicator`.
*Why:* code verification proves a method, not one result, and recording the source on the part keeps one place to look for it.
*Rejected:* folding solution verification into the credibility levels; a separate per-result verification status beside the budget.

### Packages and the coverage map

A physics package is a Package that exports `PhysicsModel` and `ConstitutiveModel` records; std ships them in `std::physics` and `std::materials`. A `PhysicsModel` names its implementation, required properties, outputs, model level, envelope, calibration classes and precision tier. [Adding new physics](#adding-new-physics) describes how one is built and accepted.

The coverage map is the list of what Crucible can simulate, by domain, scale, model level and credibility level. It is generated from package metadata and served through `api` Read methods, so an agent asking "can Crucible simulate squeeze-film damping?" gets the package, its level and its envelope, or the limit record that explains why not.

**Decision D-COV-1:** Physics coverage is delivered only as physics packages that use public mechanisms, and the coverage map is generated from package metadata. Each row shows `Planned (phase n)` until a package backs it, then its credibility level; planned rows never count as coverage.
*Why:* principle 1 forbids privileged physics, and agents read an unbacked row as an existing capability.
*Rejected:* an in-app solver catalogue, which is privileged and unverifiable; a hand-written list, which drifts from reality; planned domains without a status.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Coverage map | Generated from package metadata by domain, scale, model level and credibility level; `api` Read methods | Unbacked cells show `Planned (phase n)` and the nearest packages, outside counts | COV-O-MAP-1 | 0 |
| Model ladders | Adjacent rungs consistent inside the narrower envelope; planar and axisymmetric rungs in the solid, thermal and magnetostatic ladders | Disagreement blocks the higher rung's level | COV-O-VER-2 | 1 |
| Credibility levels | C0 to C4, raised only by CI-signed results; C3 per validated response quantity | Unsigned or agent-set levels rejected | COV-O-VER-3 | 0 |
| Discretization source | Every discretization part names an estimator or a convergence study; neither makes it `Indicator` | An `Indicator` part never decides a `SignOff` check | COV-O-VER-4 | 1 |

## Model form: how far tests say a model can be wrong

Numerical error shrinks as Flux refines, but model-form error does not: a linear elastic model of a part that yields stays wrong at any mesh. This section shows how COV fills the model-form part of a result's budget, step by step, and ends with the numbers behind the bracket's 8.1 MPa.

### Who fills which part

Each `ErrorBudget` source has one producer (contract 5.1). Flux fills the numerical parts and the reduction or surrogate part, which includes shell and beam reduction (FLX). COV supplies the Material uncertainty that Flux propagates into the input part, and fills the model-form part from validation of the physics and constitutive model, or leaves it to a policy allowance.

Flux reports each estimated bound already multiplied by its calibration class's η99: the 99th-percentile ratio of true to estimated error over a held-out corpus of solved cases. A result outside the class's envelope, the range of features the corpus covered, is only an `Indicator` (FLX). The estimator behind most of these bounds is DWR, the dual-weighted residual, which estimates the error in one goal quantity with an extra adjoint solve.

**Decision D-COV-17:** Every `PhysicsModel` names the calibration class of each `Estimated` estimator it uses, and the class's η99 entry and envelope are pinned in `ingot.lock`. Its bounds carry `Estimated { Class { id, α: 0.01 } }`; membership is computed from features FLX lists, such as degree, cut fraction and distance to singular sets, and a result outside the envelope, or without an entry, reports `Indicator`.
*Why:* only the model's author knows which estimator it needs, but a label alone cannot show that a result belongs to the sampled population.
*Rejected:* one class per numerical method; membership assigned by the author.

Phase 1 needs FLX's six classes, each with 300 held-out samples: `elasticity.peak`, `elasticity.peak.interactive`, `elasticity.frequency` and `elasticity.buckling` for immersed linear elasticity at p = 2 to 6, and `lattice.strut_stress` and `lattice.buckling` for the beam lattice's strut stresses and buckling factors. A `SignOff` `Pass` resting on such a bound also needs FLX's one-refinement confirmation, otherwise it is `Undecided { reason: CalibrationUnconfirmed }` (contract 7.1).

### How the model-form part is filled

Five steps fill the part for every checked quantity. Each step names the decision that governs it.

1. **Find the response quantity.** The check's quantity, the location type of its region (a fillet, a weld toe, a bolt hole) and the regime its zone Field reports form the response quantity. Contract 5.1 applies a validated bound only to a functional whose response quantity the validation plan lists.
2. **Without validation, leave it unquantified.** If the model is C2, or C3 for other response quantities only, the part is `NotQuantified { reason: NoValidationData }` or `NotQuantified { reason: UnvalidatedQuantity }`. The check is then `Undecided { reason: Unquantified([ModelForm]) }` unless a pinned policy allowance quantifies the part (D-COV-4).
3. **At a validation point, apply the V&V 20 metric.** The comparison error is E = S − D, simulated minus measured. The validation uncertainty is u_val = √(u_num² + u_input² + u_D²), and the bound is |E| + k·u_val, where k is the coverage factor that turns a standard uncertainty into an interval (D-COV-20).
4. **Away from validation points, inflate.** Inside the calibrated distance d_cal the bound applies as measured. Between d_cal and the package's d_max it grows by the inflation function g(d); beyond d_max it is `NotQuantified { reason: BeyondInflationFit }` (D-COV-25).
5. **Let an allowance cover what tests do not.** An organization's policy allowance may quantify the part only by citing a confirmed std catalogue entry whose scope covers the analysis (D-COV-24).

| Credibility level, zone and quantity | Model-form part |
| --- | --- |
| C3 or C4, `Calibrated`, validated quantity | `Estimated`: \|E\| + k·u_val at the nearest validation points |
| C3 or C4, `Extrapolated` within d_max, validated quantity | The calibrated bound times g(d) |
| C3 or C4, beyond d_max | `NotQuantified { reason: BeyondInflationFit }` |
| C3 or C4, quantity not validated | `NotQuantified { reason: UnvalidatedQuantity }` |
| C2, any zone | `NotQuantified { reason: NoValidationData }` |
| `Invalid` or `Unassessed` | Not reached: dependent checks return `Error(Failure)` |

**Decision D-COV-20:** Model-form error is the V&V 20 metric at validation points for the response quantities the plan lists, with α_mf = 0.05 and k = t₁₋α_mf/2 at ν_eff degrees of freedom from the Welch–Satterthwaite formula over u_num, u_input and u_D. The part carries `Estimated { Statistical { method: VvTwenty { k, ν_eff }, α: 0.05 } }`. Flux's bound B enters u_num as B/√3 when `Guaranteed` and as B/z₁₋α when `Estimated` at a one-sided level α. Each package declares whether its bound transfers to nearby conditions as an absolute or a relative error.
*Why:* V&V 20 quantifies accuracy only at validation points and for the quantities measured [ASME V&V 20], and with three replicates u_D has two degrees of freedom, so a normal k = 2 would cover far less than its stated level.
*Rejected:* transferring one validated bound to every check; a fixed k = 2; converting one-sided calibrated bounds with a two-sided factor.

**Decision D-COV-4:** An unquantified part is shown as "not quantified", never as zero. A check whose margin lies inside the quantified budget, or whose budget holds an unquantified part, is `Undecided`, unless a pinned policy allowance quantifies that part.
*Why:* a design-code factor that the code states covers model uncertainty is the honest route for C2 models, and as a pinned input it enters the check's key like any other dependency (contract 5.6).
*Rejected:* treating a missing term as zero; refusing every C2 result; a pass that carries its missing parts and is evaluated again at the gate.

**Decision D-COV-24:** A model-form allowance cites only a std catalogue entry that two non-author domain reviewers confirmed. Each entry records code, edition, clause, factor, scope and what it covers (uncertainty in the action effect or in the resistance), and only action-effect entries cover finite-element analysis.
*Why:* a resistance factor covers the capacity formula, not the analysis that computed the load effect.
*Rejected:* free-text citations; treating every partial factor as covering every model.

The allowance itself is a record in the organization's policy package, pinned in `ingot.lock` and read by the check like any input, so it appears in `CheckOutcome.allowances` and in the check's key (KLN). COV owns only the catalogue it cites.

### The bracket's model-form bound

The phase 1 validation campaign tests filleted 6061-T6 plates in three replicates, measuring surface strain at the fillet roots with gauges and stereo digital image correlation (DIC) sampled at the regularization radius (contract 13.1). The numbers below are illustrative; the campaign supplies the real ones.

At the validation point nearest the bracket, the simulated regularized peak is S = 100.0 MPa and the mean measured value is D = 96.0 MPa, so E = 4.0 MPa. The uncertainties are:

- u_num = 1.2 MPa / z₀.₉₉ = 0.52 MPa, from Flux's one-sided `Estimated` bound of 1.2 MPa;
- u_input = 1.0 MPa, from the measured load, plate thickness and modulus, propagated by `std::uq`;
- u_D = 1.4 MPa with two degrees of freedom, from DIC uncertainty and the scatter of three replicates.

Then u_val = √(0.52² + 1.0² + 1.4²) = 1.80 MPa. Welch–Satterthwaite gives ν_eff = 1.80⁴ / (1.4⁴/2) ≈ 5.5, rounded down to 5, so k = t₀.₉₇₅,₅ = 2.571. The bound is 4.0 + 2.571 × 1.80 = 8.6 MPa, or 8.6% of S.

Linear elasticity declares a relative transfer, since its error scales with the response. At the bracket's 94 MPa the part is therefore 8.1 MPa, `Estimated { Statistical { VvTwenty { k: 2.571, ν_eff: 5 }, α: 0.05 } }`. When GP1's proof-load articles are later gauged, each check also predicts its gauge functional (the average surface strain over the gauge grid), and agreement within the prediction's budget confirms the bound on held-out articles (COV-O-VAL-1).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Model-form part | V&V 20 metric per validated response quantity with k from ν_eff; u_num from Flux bounds; relative or absolute transfer; g(d) to d_max | `NotQuantified` with `NoValidationData`, `UnvalidatedQuantity` or `BeyondInflationFit` | COV-O-VAL-2 | 1 |
| Phase 1 validation campaign | Separate-specimen campaign lifting immersed elasticity and the beam lattice to C3 for fillet peaks and localized strut stress; golden-product gauge functionals as held-out confirmation | A gauge reading outside its prediction's budget blocks the gate | COV-O-VAL-1 | 1 |
| Calibration classes | Model-to-class map; pinned η99 entries and class envelopes. Requires: FLX Calibration | No entry, or outside the envelope: `Indicator` | COV-O-ERR-2 | 1 |
| Allowances | Policy-package allowances citing confirmed catalogue entries; action-effect scope for FE analysis | `Undecided { reason: Unquantified(sources) }` | COV-O-ERR-3 | 1 |

## Validity envelopes

A model is trustworthy only inside the conditions where someone checked it, and those conditions must be data a machine can evaluate, not a paragraph in a manual. This section defines the envelope record, how zones are computed, and what each zone allows.

### The record

A `ValidityEnvelope` is a content-addressed record versioned with its model. It holds regime bounds, scale limits, assumptions that cannot be computed, the validation points behind the calibrated zone, and the inflation function for extrapolation. COV owns the records and the zone semantics; Flux evaluates them with `flux::validity_zones` (FLX).

```rust
pub struct ValidityEnvelope {
    pub model: ModelRef,                 // PhysicsModel or ConstitutiveModel, id@version
    pub bounds: Vec<RegimeBound>,
    pub validation: Option<PointSet>,    // validation points; None at C2
    pub validated: Vec<ResponseQuantity>, // (quantity, location type, regime), contract 5.1
    pub length_scale: ScaleRange,        // continuum valid above 1 µm, for example
    pub assumptions: Vec<Assumption>,    // each becomes an acknowledgement check
    pub inflation: Inflation,            // g(d) fitted by leave-one-out, with d_max
    pub sources: Vec<ObjectId>,          // oracle results and Evidence records
}

pub struct RegimeBound {
    pub variable: RegimeVariableId,      // a typed Ingot function with its transform
    pub reduction: Reduction,            // Pointwise | Max | Min | Mean | Percentile(p)
    pub calibrated: QuantityInterval,    // backed by tests; its width normalizes the variable
    pub extrapolated: QuantityInterval,  // superset; plausibility limit
    pub outside: Disposition,            // Flag (a Waiver may cover it) | Refuse
    pub on_missing: OnMissing,           // Unassessed | ConservativeDefault { value, basis }
    pub escalate_to: Vec<ModelRef>,
    pub basis: Citation,
}

pub enum ValidityZone { Calibrated, Extrapolated, Invalid, Unassessed }
```

Material-specific bounds come from constitutive calibration, so a model has a calibrated zone per Material. The bracket's linear elasticity, for example, is calibrated for 6061-T6 at the temperatures and stress ratios its validation plates covered.

### Regime variables

A regime variable is a dimensionless or scaled quantity that says which physics dominates: a Reynolds number, a stress ratio, a Knudsen number. Each one states its length or time scale, so a Reynolds number without a declared length is not a regime variable. [Reference](#regime-variables-1) lists the std catalogue; a few examples show the idea.

- **Stress ratio** σ_eq/σ_proportional(T) of the assigned Material bounds every small-strain linear elastic model. It is calibrated to 0.9, extrapolated to 1.0 and refused beyond, escalating to plasticity.
- **Member inelasticity** σ_cr,Euler/σ_proportional says whether a strut buckles elastically or yields first.
- **Knudsen number**, mean free path over a declared gap, says whether a gas is a continuum.
- **Coupling diameter over wall thickness** says whether a rigid remote point stiffens a thin wall it is attached to.

**Decision D-COV-18:** Every `RegimeBound.variable` resolves to a typed Ingot function of inputs or solution Fields; an uncomputable condition is an `Assumption` a human acknowledges. A missing material input makes a bound `Unassessed`, or `Extrapolated` under a documented conservative default.
*Why:* prose bounds such as "mildly separated flow" cannot be evaluated, and one missing grain size would otherwise block every design.
*Rejected:* checking only that a bound cites a basis; silently skipping bounds with missing inputs.

Std ships detectors for common prose conditions, such as flow separation and imperfection-sensitive shells, and Flux computes the lattice regime variables (FLX).

### Zones and distance

Intervals alone describe a box, which overstates coverage when tests ran only at, say, high temperature and low strain rate. A point outside any extrapolated interval is `Invalid`. Inside them, zones also measure the distance to the validation points, so a corner of the box nobody tested is `Extrapolated` even when every variable lies in its calibrated interval.

**Decision D-COV-25:** Zones use the L∞ distance d to the nearest validation point, with each variable log- or affine-transformed and scaled by its calibrated width. `Calibrated` needs d ≤ d_cal inside every calibrated interval. Between d_cal and a per-package d_max the model-form part grows by g(d), non-decreasing from g(0) = 1 and fitted by leave-one-out, and the inflated part meets gates like any quantified part. Beyond d_max the part is `NotQuantified { reason: BeyondInflationFit }`.
*Why:* log coordinates fail for signed variables such as stress triaxiality, convex hulls go sparse above about six dimensions, one distance serves both zone and inflation, and a fitted inflation that is trusted for the budget must also be trusted for the gate.
*Rejected:* convex hulls; a Gaussian-process density, which measures sample density rather than validity; a Waiver for every extrapolated result; std default inflation before three C3 packages exist per domain.

### Evaluation

1. **A priori screen.** Bounds computable from inputs, such as an inlet Reynolds number, run first; a `Refuse` bound beyond its extrapolated range stops the solve.
2. **Solve.** Flux evaluates the Ops as usual.
3. **A posteriori assessment.** Every accepted step updates each regime variable's running extrema per region by a segmented reduction, and zone Fields are written at output steps from those extrema.
4. **Composition.** Envelopes of coupled models, and of the coupling itself, compose by intersection.
5. **Checks.** Each bound compiles to a check named `validity::<model>::<variable>`, with severity from the zone policy below.
6. **Display.** UIX hatches `Extrapolated`, `Invalid` and `Unassessed` zones on the Part; inspecting one shows value, bound, basis and escalations (UIX).

Zone Fields are identical across the canonical platform class, the set of CPU targets whose results are bit-identical (contract 7.3), and releases use canonical zones. Other platform classes may differ only within twice a bound's cross-class tolerance, where they report `NearBound`. Assessment costs under 2% of solve time (target).

[[DIAGRAM diagrams/04-coverage-validity-flow.jsx: validity flow · screen, solve, zones, checks and the ErrorBudget]]

Read the centre column from top to bottom. The left branches show where a `Refuse` bound stops the solve and where a Waiver may cover a `Flag` zone; the box on the right is the budget each result carries.

**Decision D-COV-5:** Validity bounds compile to ordinary checks, and validity zones are a Field built from running extrema that every accepted step updates.
*Why:* checks and Fields already carry severity, review and display, and sampling only at output steps misses transients such as an impact's peak strain rate.
*Rejected:* a separate warnings channel; clamping results to the envelope; assessment at output steps only.

### Policy by zone

| Zone | `Interactive` | `SignOff` | Release gate |
| --- | --- | --- | --- |
| `Calibrated` | Shown | Checks evaluate normally | Allowed |
| `Extrapolated`, d ≤ d_max | Hatched; model form inflated | Checks use the inflated part and name the zone | Allowed: the inflated budget decides |
| `Extrapolated`, d > d_max | Hatched | Model form `NotQuantified`; checks `Undecided` | A policy allowance or a Waiver |
| `Invalid`, `Flag` | Hatched; dependent checks error | Dependent checks return `Error(Failure)` | A Waiver |
| `Invalid`, `Refuse` | Shown for diagnosis only | Dependent checks return `Error(Failure)` | Blocked; no Waiver applies |
| `Unassessed` | Hatched with a missing-input notice | Dependent checks return `Error(Failure)` | Blocked until the input or a default exists |

**Decision D-COV-6:** Crucible suggests escalation to a valid model but never switches models automatically.
*Why:* a switch changes cost, provenance and sometimes the answer, so it must be an explicit edit.
*Rejected:* automatic escalation between model levels.

A `Refuse` bound surfaces as `Error(Failure)` carrying `ValidityError::OutsideEnvelope`, the one failure COV and FLX both name; [Reference](#failures) lists the full enum. The message reads like a reviewer's note:

```
error[validity]: std::physics::fluid::navier_stokes@3 is invalid in region `squeeze_gap`
  Knudsen number reaches 0.31; calibrated below 0.001, refused above 0.01
  basis: no-slip walls fail in slip and transitional flow (std::physics::regime::knudsen)
  try: std::physics::rarefied::dsmc (External Op; valid for Kn 0.1 to 10)
```

Widening any envelope needs a human Approval of the Proposal, as loosening a tolerance does; agents may propose widenings but never merge them.

### Surrogates and learned models

A learned surrogate predicts a Field from geometry and parameters in milliseconds, which makes it ideal for exploration and dangerous for decisions: an optimizer seeks out exactly the inputs where it is wrong. COV treats it as an L2 model with an envelope like any other.

**Decision D-COV-7:** A learned surrogate is an L2 model whose calibrated zone is its training distribution and whose predictions carry `Estimated { Statistical, scope: Marginal }` bounds that drive results up to `Interactive`. Out-of-distribution queries are `Extrapolated` or `Invalid`, and `SignOff` needs a confirming solve or a per-prediction bound in the check's norm, which for a peak is DWR with an adjoint solve.
*Why:* conformal coverage is marginal over the training distribution, optimizers seek a surrogate's errors, and energy-norm bounds never certify a peak.
*Rejected:* treating a surrogate as its source model; split-conformal intervals at `SignOff`; C3 without held-out physical validation.

From phase 2, Flux trains `Preview` geometry surrogates on a design repository's own cached results (FLX); their envelope is that repository's training set, and they never decide a check. Ansys SimAI "will always generate a result" with a confidence level [Ansys SimAI]; Crucible's surrogate also always answers, but a `SignOff` check never rests on it alone.

### Coupled physics

Flux owns the coupling algorithms; COV owns their envelopes, so a weak coupling outside its envelope is flagged like any model. One-way coupling (solve the first field, pass it to the second, never feed back) is cheap and usually right, and the envelope says when it is not.

| Pair | One-way coupling allowed when | Benchmark |
| --- | --- | --- |
| Thermal → structure | Deformation leaves thermal conditions and contact conductance unchanged | NAFEMS LE11 −105 MPa [ESRD NAFEMS LE] |
| Fluid ↔ structure | The mass-ratio and damping rule below holds | Turek–Hron [Turek and Hron 2006] |
| Electromagnetic → thermal | Conductivity and permeability insensitive to temperature | TEAM 36 [Compumag TEAM] |
| Electrochemical ↔ thermal | Below a declared C-rate and temperature rise | PyBaMM lumped and x-full thermal options [PyBaMM model options] |
| Structure ↔ acoustics | Fluid-loading parameter ρ_f·c/(ω·m_s) below 0.1 over the band; never for heavy fluids | Baffled piston, plate radiation |
| Electrostatic ↔ structure | Never near pull-in | Parallel-plate pull-in |
| Process → structure | Always one-way within Crucible; VMAP exchanges state with process tools [VMAP] | AM-Bench [NIST AM-Bench] |
| Aerodynamics ↔ structure | The mass-ratio and damping rule below holds, with p–k flutter as the stability check | AGARD wing 445.6 [Yates 1987] |

**Decision D-COV-19:** One-way fluid– or aerodynamic–structure coupling needs a mass ratio ρ_s·t/(ρ_f·L) above 10 or added mass below 5%, clear forcing frequencies and positive coupled damping. Damping comes from p–k flutter or a linearized coupled eigenanalysis over the operating envelope; otherwise the coupling is `Invalid` and escalates to two-way.
*Why:* flutter, galloping and lock-in grow from infinitesimal amplitudes, so a displacement test approves one-way analysis exactly where coupling destabilizes.
*Rejected:* displacement below 1% of the flow length; small static twist.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Envelope records | `ValidityEnvelope` per model version with validation points, validated response quantities and inflation to d_max | Registry rejects a missing envelope, basis, transform, escalation or inflation | COV-O-ENV-1 | 0 |
| Regime variables | Typed Ingot functions with declared scales and transforms | `RegimeUncomputable { variable }` at registration | COV-O-ENV-6 | 0 |
| Zone semantics | Intervals, running extrema and zone policy, evaluated by `flux::validity_zones`. Requires: FLX Validity zones | `Error(Failure)` carrying `ValidityError::OutsideEnvelope` | FLX-O-ERR-9 | 1 |
| Zone geometry | Normalized L∞ distance, d_cal, fitted g(d) and d_max | Beyond d_cal: `Extrapolated`, nearest validated condition reported; beyond d_max: `BeyondInflationFit` | COV-O-VAL-2 | 1 |
| Zones across classes | Canonical zones identical; `NearBound` elsewhere | A mismatch outside the band is a determinism incident | COV-O-ENV-3 | 1 |
| `Refuse` bounds | Stop the solve or block dependent checks | `Error(Failure)` with fixes | COV-O-ENV-4 | 1 |
| Waivers and widening | Waivers for `Flag` zones and for extrapolation beyond d_max; widening by human Approval | Agent attempts fail; `Refuse` accepts no Waiver | COV-O-ENV-5 | 1 |
| Missing inputs | Documented default, else `Unassessed` | `ValidityError::Unassessed { missing }` | COV-O-ENV-6 | 1 |
| Surrogate envelopes | Training distribution as calibrated zone; `Preview` geometry surrogates never decide; bounds in the check's norm at `SignOff` | Out-of-distribution queries `Extrapolated` or `Invalid` | COV-O-ENV-7 | 2 `Preview`, 4 |
| Coupling envelopes | Weak couplings inside their envelope | One-way analysis outside it `Invalid` | COV-O-ENV-8 | 1 thermal, 4 fluid |

## Coverage by domain

"Anything physical" is a promise only if each domain says which models exist, where they are valid, how they are benchmarked and when they arrive. This section explains how to read the coverage matrix, walks through the domains with the rules that matter most in each, and records the domain decisions; the full matrix, one table per domain, is in [Reference](#coverage-matrix).

### Reading the matrix

Each matrix row is one physics domain. Its columns give the scales it serves, the L0 to L2 rungs of its ladder, the L3 method, default envelope bounds, the benchmark its oracle runs, and its phase and delivery route. The matrix is generated from package metadata (D-COV-1), so this tab sets its initial content and every row reads `Planned` until a package backs it. A phase followed by "(13.4)" is fixed by contract section 13.4.

Scales use five bands: **N** below 100 nm, **µ** to 1 mm, **Me** to 100 mm, **P** to 10 m and **L** beyond. Delivery uses three routes: **Nat**, an Ingot weak form or Flux operation; **Wasm**, a std Wasm component; and **Ext**, an External Op that runs a large or copyleft solver in an isolated host ([Adding new physics](#adding-new-physics)). Envelope numbers in the matrix are design defaults, which each package confirms or changes before it reaches C2.

### Solid mechanics

Linear elasticity carries phase 1: high-order FEM on the immersed octree for solids, Timoshenko and Vlasov beams for struts, and planar and axisymmetric sections where the geometry and loads allow (13.4). Its envelope is the stress ratio of [Validity envelopes](#regime-variables) together with a rotation bound for small-strain kinematics and a feature-size bound of at least ten grains, or a strut-scale Material for printed lattices. Shells, IGA on trimmed B-rep and the finite cell method for voxel data follow in phase 2.

Nonlinear solid mechanics arrives in phase 2: total Lagrangian geometric nonlinearity with arc-length continuation, finite-strain plasticity (J2, Hill48, Yld2000-2d, Chaboche), hyperelasticity and mortar contact on fitted tetrahedra (13.4). Viscoelasticity and creep follow in phase 3. Every nonlinear envelope reports limit and bifurcation points instead of stepping over them, because a solver that silently picks a branch gives an answer that is not reproducible (contract principle 4).

Analyst idealizations reach every solid model: rigid and distributing remote points, point masses with rotary inertia and springs in phase 1, then bushings, fastener and spot-weld connectors in phase 2 (FLX). COV gives each one an envelope. A rigid coupling stiffens the wall it grips, so a rigid remote point whose coupling diameter exceeds five times the local wall thickness is `Flag`, with a distributing coupling as the escalation. Point-mass and spring idealizations carry their parameter sources, and joint stiffness and damping come only from tests of the joint class, because nothing predicts them from first principles (limit OOR-18).

Snap fits and soft parts use mortar contact until FLX's Incremental Potential Contact arrives in phase 5, which reports its barrier distance and friction smoothing under the regularization part of the budget [IPC Toolkit tutorial]. Bolted joints follow VDI 2230-1 for preload and joint stiffness [VDI 2230-1].

### Dynamics and stability

Modal analysis and linear buckling, with Lanczos and LOBPCG eigensolvers, land in phase 1 because GP2's struts need them (13.4). Flux bounds each eigenvalue on both sides, since an immersed discretization may err either way (FLX). Linear dynamics follows in phase 2 as one FLX capability (13.4): prestressed, damped and gyroscopic eigenproblems; mode-superposition harmonic, random and response-spectrum response; and damping models declared as data (modal, Rayleigh, structural hysteretic and frequency-dependent viscoelastic).

COV's vibration and shock row therefore covers sine sweeps, base-excitation power spectral density (PSD) response and shock response spectra together in phase 2. Its envelope requires the forcing band to lie inside the modal coverage, with a residual-flexibility term for the modes left out. Near a resonance, an error in a natural frequency is amplified by about 1/(2ζ) for damping ratio ζ, so the envelope `Flag`s a response whose half-power band contains an eigenvalue whose bound overlaps the forcing frequency. Launch environments reuse this row; they add only the launch provider's spectra.

Rotordynamics also lands in phase 2. Its rungs run from the Jeffcott rotor through rotor beam networks to Campbell diagrams from FLX's prestressed and gyroscopic eigenproblems, which include stress stiffening and spin softening. Fluid-film bearings come from the Reynolds equation and are linearized at the operating speed.

Buckling of members and struts is where printed lattices meet classical stability theory. An additively made strut of about 1 mm diameter and length-to-diameter ratio 4 has slenderness 4L/d ≈ 16, so its Euler stress π²E/λ² is about 2,700 MPa for AlSi10Mg, far above any proportional limit. Such a strut yields long before it buckles elastically, so the strut decides by strength, and eigen-buckling serves only the slender members where it governs global instability.

**Decision D-COV-30:** Strut compression is decided by a strut-strength check: the localized axial stress from `lattice.strut_stress` against the as-built compressive strength, reduced by a Johnson–Perry–Robertson factor computed from the measured waviness. Linear eigen-buckling (`lattice.buckling`) runs only on members whose inelasticity ratio σ_cr,Euler/σ_proportional stays below 1; it is `Calibrated` below 0.5 and `Extrapolated` to 1, and waviness beyond the declared value is `Flag`.
*Why:* stocky printed struts fail by compressive yield and plastic collapse, where Euler's load overstates capacity, and the strength check needs no calibration class beyond the strut-stress class phase 1 already has.
*Rejected:* refusing eigen-buckling on stocky struts with no strength rung, which left most of GP2 undecided; refusing only imperfection-sensitive shells, which let every strut pass.

MFG's as-built strut calibration includes compression tests of single struts at GP2's diameters, so the strength check reads a measured compressive strength (13.4). Shell buckling uses arc-length post-buckling with imperfections and Koiter coefficients from phase 2, and imperfection-sensitive shells are `Refuse` at `SignOff` for linear eigen-buckling.

### Impact, drop and crash

Explicit dynamics serves GP5's drop in phase 3 and GP9's crash box in phase 5 (13.4). Raw peak accelerations depend on sampling rate and mesh, and crush folding is a sequence of bifurcations, so neither is a well-posed quantity to check. COV defines what a check may read instead.

**Decision D-COV-33:** Explicit-dynamics checks read regularized functionals: acceleration through a declared channel filter, energy absorbed, mean crush force over a displacement window, and the maximum of a time-averaged strain. Buckling-sensitive cases run as an ensemble over seeded geometric imperfections, whose statistics form the statistical part, and the discretization part comes from FLX's grid-convergence study calibrated once per family (drop, crash).
*Why:* these functionals converge under refinement where peak histories do not, they are what the gates of contract 13.1 compare, and an ensemble declares branch selection as principle 4 requires.
*Rejected:* raw peak accelerations; a single imperfect geometry; leaving explicit results as indicators only.

Channel filters follow the SAE J211 channel frequency classes, CFC 60, 180, 600 and 1000, each a low-pass filter with a specified response [DADiSP CFC module]. The envelope bounds mass scaling at 2% calibrated and refuses it above 5%, and it bounds hourglass energy at 10% of internal energy. Material failure under impact is `Flag`, because ductile fracture has no validated predictive method (limit OOR-6).

### Durability

Fatigue starts in phase 1 with uniaxial stress-life: Basquin's law with Goodman, Gerber or Walker mean-stress corrections and rainflow counting. Phase 2 adds multiaxial critical-plane methods, strain-life, weld fatigue to IIW and Eurocode 3 [Hobbacher and Baumgartner 2024], and vibration fatigue from PSD response by the Dirlik and narrow-band methods. Crack growth arrives in phase 3. Fracture runs from linear elastic fracture mechanics in phase 2 to ductile damage in phase 5, and ductile damage is `Flag`: a blind round robin found "a striking lack of consistency" among predictions [Boyce et al. 2014].

Fatigue and fracture checks near notches use the theory of critical distances, which reads stress at a material length L from the hot spot [Taylor 2008]. L is fitted together with the operator that evaluates it (a point, a line, an area or a volume average), so reading a published L with a different operator gives a different, often unconservative stress.

**Decision D-COV-34:** Every critical distance in a Material records the method that calibrated it (point, line, area or volume), and Flux's critical-distance goal evaluates that method's own operator along the inward normal from the hot spot. A check that asks for another method fails with FLX's `CriticalDistanceMismatch { calibrated, requested }`.
*Why:* the length and its operator are one calibration, and pairing a point-method length with a volume average understates stress by an amount that depends on the gradient.
*Rejected:* one smoothing radius for every method; a Gaussian volume average with the published length.

Gears, bearings and shafts are rated by their standards, because that is how practitioners and certifying customers judge them.

**Decision D-COV-26:** Gear, bearing and shaft strength use L0 standard ratings and L2 loaded tooth contact analysis, with mortar contact on fitted tetrahedra as the validation rung. Ratings return margin Fields per failure mode from MEC's gear records (geometry, accuracy grade, load spectrum).
*Why:* practitioners rate gears and bearings to standards, and tooth contact analysis gives load sharing and transmission error far more cheaply than 3D contact.
*Rejected:* 3D mortar contact as the design rung; geometry without ratings.

Gears follow ISO 6336:2019 [ISO 6336-1] or ANSI/AGMA 2101-E25 [MPMA catalogue], bearings ISO 281:2007 with ISO 16281:2025 [ISO 16281], and shafts DIN 743:2012 [DIN 743-1] or the FKM guideline [FKM guideline], all in phase 2 (13.4). Lubrication enters at two rungs: Hamrock–Dowson film thickness in phase 2 [Hamrock and Dowson 1977], and a full elastohydrodynamic solve in phase 3, once FLX's FFT and hierarchical-matrix deflection operators exist and a semismooth Newton method handles cavitation.

### Composites and lattices

Laminates, progressive failure and constitutive draping are aerospace work and land in phases 4 and 5 (13.4); MEC owns plies and kinematic draping, and COV owns draping with shear locking and cure simulation. Progressive failure is `Flag`: in the second World-Wide Failure Exercise no theory matched all the test data [Christensen WWFE-II]. Short-fibre moulded composites use Mori–Tanaka averaging over the orientation Field that mould filling computes, in phase 3 with GP5.

Lattices are GP2's core and land in phase 1. Strut cells use beam-lattice models with node corrections, and a lattice part's critical region signs off on the beam lattice's localized strut stresses. Node corrections are fitted per cell topology over a relative-density range against full-resolution immersed solves on computed tomography (CT) scans of as-built unit cells from the bureau's coupons, because printed nodes gather material that nominal CAD cells lack (MFG, FLX). Strut-scale Materials from MFG's as-built calibration include strut diameter in their coverage, so printed struts escape the grain-size default. Sheet cells use mid-surface shells on the minimal surface's zero set in phase 2.

### Heat transfer

Conduction lands in phase 1 with high-order FEM, including planar and axisymmetric sections; its envelope refuses Fourier's law where phonon mean free paths exceed the feature size. Convection climbs from Nusselt correlations within their published ranges in phase 2 to laminar and natural conjugate heat transfer in phase 3 and turbulent conjugate heat transfer in phase 4 (13.4). Conjugate analysis inherits the flow model's envelope, and a laminar wall is `Extrapolated` with fewer than five cells across the thermal boundary layer.

Radiation, phase change, boiling and condensation, moisture and Joule heating follow in phases 3 to 5. Ablation, which is empirical at every rung, is always `Flag`. Fluid properties come from CoolProp [CoolProp] or a licensed REFPROP connector.

### Fluids

Incompressible laminar flow arrives in phase 3, Reynolds-averaged Navier–Stokes (RANS) models in phase 4 and scale-resolving methods in phase 5. RANS envelopes calibrate attached flow, `Flag` separation and declare a y⁺ range, because predictive RANS for smooth-body separation is out of reach anywhere (OOR-3). Direct numerical simulation (DNS) is refused above an a priori cost budget, since its cost grows as about Re^2.91 [Yang and Griffin 2020].

Rotating machinery needs three FLX capabilities that the parity floor phases (13.4): laminar rotating frames, fan curves and flow resistances in phase 3; RANS rotating frames and sliding interfaces in phase 4; and mixing-plane interfaces in phase 5. COV's turbomachinery and fans row gives them envelopes. A frozen-rotor or mixing-plane solve is a steady approximation of an unsteady flow, so strong blade-row interaction is `Flag`, and a fan modelled as a pressure jump is valid only inside its measured P–Q curve.

System-level fluids sit in ELX's element libraries: single-phase hydraulics and coolant loops in phase 4, two-phase and pneumatic elements in phase 5 (13.4). COV adds their envelopes, with cavitation and choking `Flag`, and a ladder link from 1D pipe elements to 3D flow, so a coolant loop can check one branch in 3D against its network element.

Free-surface and multiphase flow beyond mould filling is COV's own phase 5 capability (13.4). Interface-resolving methods converge only above a resolution of k_max·η_KH ≥ 60 with second-order schemes [Hatashita et al. 2025], and coarser solves are `Flag`. Particle tracing in flows, one-way Lagrangian transport on a computed flow Field, joins in phase 5 as the first rung of dispersed multiphase. Free-molecular flow also lands in phase 5, by the angular coefficient method, a deterministic radiosity-like method on Flux's view-factor operations that avoids the statistical noise of particle methods [COMSOL Molecular Flow].

### Acoustics and electromagnetics

Linear acoustics lands in phase 3 with FLX's indefinite Helmholtz solvers (13.4), with perfectly matched layers and fast boundary elements. Vibro-acoustics, porous absorbers and aeroacoustics follow, with broadband aeroacoustics `Flag` unless a scale-resolving flow supplies it.

Electromagnetics follows ELX's needs. Electrostatics and magnetostatics, including axisymmetric coils, arrive in phase 3; eddy currents, electric machines and the drone's antenna in phase 4; general RF in phase 5. Signal and power integrity use 2D cross-section RLGC extraction in phase 3 (ELX) and 3D quasi-static and full-wave extraction in phase 4 (13.4). Periodic structures (phased arrays, frequency-selective surfaces, radomes) use Bloch-periodic unit cells, Floquet ports and finite arrays assembled from a cached unit cell in phase 5 (13.4).

Charged-particle tracing joins in phase 5: Lorentz-force trajectories through electrostatic and magnetostatic Fields, with space-charge iteration, on Flux's BVH queries. It serves electron guns, ion optics and sputtering sources, and its benchmark is the Child–Langmuir space-charge-limited diode.

### Electrochemistry, particles, plasma and the rest

Battery cells, swelling, packs and abuse belong to ELX, and the Doyle–Fuller–Newman solver to FLX (13.4); COV owns their envelopes and the degradation, runaway and corrosion models. Lithium plating, degradation and abuse are always `Flag`, because their onset is empirical. Lithium iron phosphate (LFP) hysteresis uses PyBaMM's one-state model, which was developed on nickel–metal hydride cells, so it is refit on LFP data before ELX's oracle counts it [PyBaMM one-state hysteresis].

Granular media, particle methods for large deformation, molecular dynamics, multiscale coupling, plasma and radiation transport arrive in phases 5 to 7. The large or copyleft codes among them (LAMMPS, WarpX, OpenMC, Geant4) run as External Ops, and molecular results enter continuum models only as provenance. Biomechanics, MEMS, civil structures, marine and the remaining aerospace rows follow the golden products that need them, from GP7 in phase 5 to GP16 in phase 7.

Pressure equipment joins in phase 5 with GP8's structural checks: design by analysis to ASME VIII-2 Part 5 and EN 13445-3, read from licensed data packages, with plastic-collapse and ratcheting routes on FLX's plasticity. Its membrane and bending stresses come from FLX's stress linearization, which can bound them as linear functionals of the stress, where incumbents report the same quantities without a bound [Ansys linearized stress]. Civil rows read load combinations from a `std::systems` code-combination package per standard edition, on FLX's combination operations.

### Rotors and aircraft

GP6's gate validates rotor thrust and torque, so rotor aerodynamics has a full ladder by phase 4.

**Decision D-COV-31:** Rotor aerodynamics, FLX's capability in phase 4 (13.4), is a ladder of three rungs with COV envelopes. Blade-element momentum theory with tip losses is an Ingot package (L1); a vortex particle method with regularized particles and a stated core size is a std Wasm component on Flux's fast multipole operations; and RANS runs on FLX's rotating frames and sliding interfaces (L3). Each carries its envelope, and the ladder's consistency oracle compares the rungs on GP6's propellers.
*Why:* a drone engineer needs thrust and torque from the first sketch, and each rung serves a different question at a cost that differs by orders of magnitude.
*Rejected:* RANS as the only rotor model; leaving rotor aerodynamics to an outside tool.

Transonic flow, aeroelasticity, icing and spacecraft thermal follow in phase 6 with GP10 and GP11. Flight dynamics reads stability derivatives and 6-DoF models in phase 4. Flux owns multibody dynamics and rods (contract 7.1), and MEC owns the assemblies and joints they read.

### Manufacturing processes

MFG owns the process setups and the as-built calibrations, and the moulding, casting, welding, forming and chatter capabilities (13.4). COV owns every process row's physics models, envelopes and state Fields, and the constitutive draping and cure models. The rule for who owns a parameter is D-COV-27 in [Materials](#materials).

Powder bed fusion distortion by inherent strain lands in phase 2 and is valid only for the calibrated machine, material, parameters and stress relief. Injection moulding lands in phase 3 with GP5. The Hele-Shaw approximation of thin-cavity filling is valid only where cavity thickness over flow length and the thickness gradient are both below 0.1. The flow must also be at least two thicknesses from gates, rib roots, steps and the flow front; elsewhere `SignOff` needs a 3D solve. Phase 3 calibrates those thresholds against 3D solves on a step plate and a ribbed plaque, and until then the zone is `Extrapolated`.

Welding distortion starts in phase 2 with inherent strains from coupons per joint type, thickness, process and heat input, applied to beam frames as equivalent joint loads (MFG, FLX). The transient weld model, a Goldak heat source with solid-state phase transformation and thermo-elasto-plasticity, lands in phase 4. The phase-transformation kinetics it needs, JMAK for diffusional transformations and Koistinen–Marburger for martensite, are COV's phase 4 capability (13.4); full heat-treatment process simulation reuses them in phase 6.

### The parity map

A buyer comparing Crucible with Ansys or Abaqus asks a workflow question: "can I do my harmonic analysis there yet?", not "is the Lanczos solver phased?". The parity table in [State of the art](#state-of-the-art) answers it.

**Decision D-COV-32:** COV keeps the simulation parity map, one row per workflow an incumbent's analyst relies on. Each row names the capability rows it needs in FLX, COV and ELX, the incumbent's documented feature, the phase by which every listed row exists, and Crucible's difference. An oracle fails the map when a listed capability lacks a row or carries a later phase than the workflow.
*Why:* gaps hide between tabs until someone builds the workflow checklist, and a capability list never tells a buyer when the tool they use today is matched.
*Rejected:* per-tab capability lists only; a parity claim without the rows behind it.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Solid, dynamics and durability models | `std::physics` models with envelopes and ladders, including planar and axisymmetric rungs and idealization envelopes | `ValidityError` per bound | COV-O-BENCH-1, COV-O-BENCH-2 | 1 to 5 per row |
| Strut strength and buckling envelopes | Strut-strength check with a Johnson–Perry–Robertson factor; eigen-buckling below inelasticity ratio 1; waviness `Flag`. Requires: FLX Beam-lattice models | Struts above ratio 1 `Refuse` linear eigen-buckling and decide by strength | COV-O-BENCH-2 | 1 |
| Vibration, shock and rotordynamics envelopes | Harmonic, PSD, response-spectrum and Campbell rows; resonance and modal-coverage bounds; Dirlik and narrow-band PSD fatigue | Forcing outside modal coverage or an overlapping resonance: `Flag` | COV-O-BENCH-2 | 2 |
| Impact functionals | Channel-filtered acceleration, energy absorbed, mean crush force, time-averaged strain maxima; seeded imperfection ensembles. Requires: FLX Explicit dynamics | Mass scaling above 5%: `Refuse`; a raw peak as a goal: `NotRegularized` | COV-O-BENCH-14 | 3 drop, 5 crash |
| Critical distances | Method recorded per Material; the method's own operator (FLX) | `CriticalDistanceMismatch { calibrated, requested }` | COV-O-MAT-11 | 1 |
| Gear, bearing and shaft ratings (13.4) | L0 ratings and L2 tooth contact with margin Fields | Outside the rating's scope or lambda range: `Invalid` | COV-O-BENCH-10 | 2 |
| Composite and lattice models | Laminate, failure, short-fibre and lattice envelopes; CT-fitted node corrections | `Invalid` near boundaries; `Flag` above the Bloch-wave bound | COV-O-BENCH-2 | 1 to 4 per row |
| Thermal and fluid models | Conduction to two-phase rows; turbulence closures, wall treatments and wall resolution; turbomachinery, fan and fluid-system envelopes | Correlations outside range `Refuse`; separation, blade-row interaction, cavitation and choking `Flag`; under-resolved walls `Extrapolated` | COV-O-BENCH-3 | 1 to 6 per row |
| Free surface and multiphase beyond mould filling (13.4) | Resolved and dispersed models with resolution envelopes; particle tracing in flows | Under-resolved interfaces `Flag`; breakup per OOR-8 | COV-O-BENCH-8 | 5 |
| Charged-particle tracing and free-molecular flow | Lorentz-force trajectories with space charge; angular coefficient method on view factors | Fields outside their solve's zone: `Unassessed`; Knudsen below the free-molecular bound: `Invalid` | COV-O-BENCH-11 | 5 |
| Pressure-equipment design by analysis | ASME VIII-2 Part 5 and EN 13445-3 routes from licensed packages, on linearized stress and plasticity | Missing code package: `MissingStandard { code, edition }` | COV-O-BENCH-12 | 5 |
| Rotor aerodynamics | Blade-element momentum, vortex particle and rotating-frame RANS rungs | Advance ratio or tip Mach outside the rung's envelope: `Invalid` | COV-O-BENCH-13 | 4 |
| Electromagnetic and optical models | Static to full-wave rows; periodic unit cells and arrays | Non-causal fits rejected; EMC `Flag` | COV-O-BENCH-4 | 3 to 6 per row |
| Electrochemical models | Envelopes of ELX's and FLX's battery rows (13.4); degradation, runaway and corrosion models | Plating, degradation and abuse `Flag` | COV-O-BENCH-6 | 3 to 6 per row |
| Process models | State Fields and process envelopes | Uncalibrated machine or alloy: `Unassessed` | COV-O-BENCH-5 | 2 to 6 per row |
| Phase-transformation kinetics (13.4) | JMAK and Koistinen–Marburger with transformation plasticity, from TTT and CCT data | Missing transformation data: `Unassessed` | COV-O-BENCH-5 | 4 |
| Constitutive draping and cure (13.4) | Fibre-angle and cure-state Fields; spring-in stress | Shear above the locking angle: `Invalid` | COV-O-BENCH-9 | 5 |
| Particle, kinetics, molecular, plasma and transport domains | Flux operations, Wasm kinetics and External Ops | Host failure is a `Failure`; worker loss an Abort | COV-O-BENCH-7 | 5 to 7 |
| Later-phase domains | Biomechanics, MEMS, civil, marine and aerospace rows | `ValidityError` per bound | COV-O-VAL-1 | 3 to 7 per row |
| Parity map | Workflow rows naming capability rows, incumbent features and phases | A missing row or a later phase fails the map | COV-O-MAP-2 | 1 |

## Scope and limits

Honest coverage needs an equally precise statement of what Crucible does not simulate, so that a missing model is a named answer rather than a silent gap. Contract section 13.1 sets the product's scope; this section records COV's two scope decisions and the two limit lists that validity errors cite.

### Building products

Much of construction is manufactured products: facade units, modular pods, mass-timber connections and prefabricated steel. They have BOMs, tolerances and fabrication drawings like any machine, so Crucible designs them; whole buildings, with spaces, zones and building energy, are a different product.

**Decision D-COV-8:** Crucible designs and simulates building products and structures natively and exchanges with BIM tools through IFC 4.3 (ISO 16739-1:2024 [buildingSMART IFC]), never authoring whole buildings. Steel structures and the IFC round trip land in phase 5 for GP8; timber, structural fire and building physics in phase 7 for GP14.
*Why:* prefabricated building products have BOMs, while whole-building authoring is a different product that mature tools serve through an open standard.
*Rejected:* full building scope, which duplicates BIM tools; no building scope, which abandons prefabrication.

### Chip layout and MEMS

Integrated-circuit physical design rests on process design kits under non-disclosure agreements and on non-geometric abstractions, and OpenROAD already runs RTL to GDSII with open process kits [OpenROAD]. MEMS devices, by contrast, are mechanical structures defined by masks and process steps.

**Decision D-COV-9:** IC layout stays out of scope. Crucible exchanges GDSII and OASIS layers for MEMS, packaging and die-level analysis, and generates MEMS masks through a process-emulation package in phase 5 for GP7.
*Why:* MEMS and chip packaging are physical design problems; logic layout is not.
*Rejected:* an IC layout editor, which is the wrong abstraction on data under non-disclosure; no layout interchange, which blocks MEMS.

### Out of reach

These problems have no validated predictive method anywhere as of October 2026; best practice is testing or calibration. Each is a record in `std::physics::limits`, and a request that needs one returns `ValidityError::NoCoveringModel` citing it.

| Id | Problem | Why it is out of reach | Best available approach | Crucible behaviour | Categories affected |
| --- | --- | --- | --- | --- | --- |
| OOR-1 | DNS of turbulence at product scale | Cost scales as Re^2.91 [Yang and Griffin 2020], about 800 times per tenfold Reynolds number | Wall-modelled LES at Re^1.14; RANS in design loops | `Refuse` above the a priori budget | Vehicles, aircraft, ships |
| OOR-2 | Wall-resolved LES of high-Reynolds external flow | Cost scales as Re^2.72 | Wall-modelled LES with non-equilibrium wall models [Agrawal et al. 2024] | Cost reported first | Vehicles, aircraft, ships |
| OOR-3 | Predictive RANS for smooth-body separation and corner flows | Equilibrium closures miss separation onset even in wall-modelled LES; a NASA CFD Vision 2030 goal [Slotnick et al. 2014] | Scale-resolving simulation calibrated against tests | Separation `Flag`; model form inflated | Vehicles, aircraft, drones |
| OOR-4 | First-principles chemistry of whole products | A 1 kg aluminium part holds about 2×10^25 atoms | Continuum models with measured parameters; machine-learned potentials [MACE] | DFT and MD only as C1 provenance | All |
| OOR-5 | Long-horizon degradation without test data | Coupled mechanisms; uncontrolled time extrapolation | Accelerated tests with a declared acceleration model; Bayesian updates | `Extrapolated` to 3× the tested duration, `Invalid` beyond | Batteries, buildings, ships, medical |
| OOR-6 | Ductile fracture and composite failure | 13 teams disagreed in a blind round robin [Boyce et al. 2014]; composite theories miss tests | Building-block pyramids; conservative allowables | `Flag` | Vehicles, aircraft, fabrications |
| OOR-7 | Turbulent combustion, soot and emissions | Empirical turbulence–chemistry closures | Flamelet tables; rig calibration | `Flag` | Machines, vehicles, aircraft |
| OOR-8 | Atomization at engineering Weber numbers | Resolved cost grows as We^(12/5) [Hatashita et al. 2025] | Lagrangian sprays with calibrated breakup | Breakup `Flag`; die-casting filling `Extrapolated` above the gate threshold | Castings, machines, vehicles |
| OOR-9 | Cavitation erosion, fretting, tribochemistry | Mechanisms span atomic to part scales | Indicators and tests | Indicators only | Mechanisms, ships, machines |
| OOR-10 | Chaotic trajectories beyond the predictability horizon | Sensitivity below floating-point resolution | Statistics with convergence error | Statistics; trajectories labelled | Every category with turbulent flow |
| OOR-11 | Individual-specimen life | Stochastic defects govern life | Probabilistic life; CT defect populations | Lives are distributions | Printed parts, castings, aircraft |
| OOR-12 | Patient-specific biological response | Inter-subject variability and adaptation | Population models | `Flag`; C4 only through V&V 40 | Medical |
| OOR-13 | Human behaviour and misuse | Not physics | Standards, user studies | Anthropometry only | Wearables, machines, medical |
| OOR-14 | Fire spread, explosions, runaway venting | Combustion, turbulence and fracture at extreme rates | Specialist tools and tests | Prescribed fire curves and runaway onset only | Batteries, buildings |
| OOR-17 | Site-scale geology, weather and climate loads | Site data govern | Site investigation; code loads | Site data imported with provenance | Buildings, ships |
| OOR-18 | Damping of assembled structures | Joint micro-slip varies with preload, wear and assembly | Modal testing; damping per joint class | Damping is a calibrated input | Mechanisms, fabrications, aircraft, spacecraft |
| OOR-19 | Friction and contact conductance from first principles | Surface chemistry, roughness and contamination dominate | Tests per pair | Pair data only; a missing pair is `Unassessed` | Mechanisms, machines, electronics |

### Out of scope

Mature specialist tools simulate these problems well, and Crucible exchanges data with them instead of competing.

| Id | Problem | Specialist practice | Crucible behaviour |
| --- | --- | --- | --- |
| OOS-1 | Semiconductor device physics and quantum devices | TCAD and quantum transport with process-specific calibration | Compact models, package thermal and stress only |
| OOS-2 | Nuclear criticality safety | Licensed codes with benchmark-validated nuclear data | Monte Carlo transport never decides a criticality check |
| OOS-3 | Superconducting magnets: quench and critical-state AC loss | Quench codes such as CERN's STEAM tools [CERN STEAM LEDET] | Geometry, structure and cryogenic thermal native; superconducting behaviour exchanged as Fields |

**Decision D-COV-10:** Limits are two versioned `std` record lists that validity errors cite: `OutOfReach`, where no validated method exists, and `OutOfScope`, where mature external tools do. An entry moves or leaves only through a Proposal backed by test results and approved by humans.
*Why:* limits must be as machine-readable as coverage, and calling specialist simulation impossible misstates the state of the art.
*Rejected:* limits in documentation only; one mixed list.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Building products and IFC | Native design and analysis; IFC 4.3 through ECO | Content outside the product subset kept as Assets with a note | COV-O-VAL-1 | 5 steel, 7 timber |
| MEMS layout | GDSII and OASIS layers; process emulation | Unknown layer purposes reported per layer | COV-O-VAL-1 | 5 |
| Limit records | `OutOfReach` and `OutOfScope` entries cited by `NoCoveringModel` | Uncovered requests name an entry or the nearest package | COV-O-LIM-1 | 0 |

## Adding new physics

Coverage grows only through physics packages, std and third-party alike, so the path from a new method to a trusted result must be the same for Crucible's own builders as for anyone. ECO owns the registry and its publish pipeline; COV contributes the domain acceptance checks.

### What a package holds

1. `PhysicsModel` records with domain tag, model level, required properties, outputs, envelope, calibration classes and precision tier.
2. An implementation: an Ingot weak form (preferred), a Wasm component implementing `crucible:physics/solver`, or an External Op manifest.
3. Regime-variable functions, with their transforms, for any new bounds.
4. Oracles: manufactured solutions, benchmarks and validation Evidence records by `ObjectId`.
5. An SPDX licence for code and a data licence for every dataset.

The bracket's elasticity model looks like this; ING defines the record syntax, so the example is illustrative.

```
pub fn linear_elasticity() -> PhysicsModel {
    PhysicsModel {
        id: "std::physics::solid::linear_elasticity@4",
        level: ModelLevel::Full3d,
        precision: Precision::F32Safe,
        requires: [Material.elastic_stiffness, Material.proportional_limit],
        form: elasticity_form,
        calibration: ["elasticity.peak"],
        envelope: envelope {
            bound(stress_ratio, max) { calibrated: 0.0..=0.9, extrapolated: 0.0..=1.0,
                outside: refuse, escalate_to: [solid::finite_strain_plasticity] }
            bound(rotation, max) { calibrated: 0.0rad..=0.05rad, extrapolated: 0.0rad..=0.1rad,
                outside: refuse, escalate_to: [solid::geometric_nonlinear] }
            bound(homologous_temperature, max) { calibrated: 0.0..=0.4, extrapolated: 0.0..=0.5, outside: flag }
            assume("homogeneous at the smallest feature's scale")
            inflation: inflation::leave_one_out(transfer: relative)
        },
        sources: [oracle("COV-O-VER-1"), oracle("COV-O-BENCH-1")],
    }
}
```

The stress ratio is σ_eq/σ_proportional(T) of the assigned Material, so the bound follows the alloy and its temperature rather than a fixed strain. A homologous temperature of 0.4 keeps aluminium alloys at room temperature (about 0.34 for 6061) inside the calibrated zone, while creep-prone conditions fall outside it.

### Implementation routes

| Route | Use for | Limits |
| --- | --- | --- |
| Ingot weak form | Any variational PDE system, including parameter-domain forms; gets kernels, derivatives, estimators and caching | Methods without a weak form |
| Wasm component (`crucible:physics/solver`) | Monte Carlo, ray-tracing, boundary-element-kernel and Network methods | No clocks, files, network or raw GPU; randomness from KLN's streams |
| External Op | Large or copyleft codes: OpenFOAM (GPLv3 [OpenFOAM licence]), LAMMPS (GPLv2 [LAMMPS licence]), SPARTA (GPL [SPARTA]), OpenRadioss (AGPL-3.0 [OpenRadioss]) | Untrusted-evaluation workers only; `SignOff` needs two agreeing runs |

**Decision D-COV-11:** Non-variational methods run their hot loops on general Flux operations: BVH traversal, neighbour lists, segmented reductions, counter-based random streams, fast multipole and hierarchical matrices. Method logic (collision laws, scattering kernels, source terms) lives in Ingot or a Wasm component.
*Why:* these loops need GPUs, which Wasm components reach only through `crucible:ops/flux` (contract section 4).
*Rejected:* one privileged in-tree solver per method; CPU-only Wasm solvers.

**Decision D-COV-12:** Large and copyleft solvers run as External Ops in single-use, egress-denied microVMs on untrusted-evaluation workers, and their results carry the host's platform class or `Unverified`. Gates and `SignOff` checks need two hosts to agree on the output `ObjectId` under signed receipts, or a policy allowance for a nondeterministic solver (contract 7.8).
*Why:* GPL and AGPL code is never linked (contract 7.7), untrusted code never runs beside attestation keys, and a guest's own claim about its output proves nothing.
*Rejected:* linking copyleft solvers; dropping their domains; one untrusted run at `SignOff`.

**Decision D-COV-23:** `F32Safe` models may solve in `f32` on GPUs, with residuals and estimators evaluated in canonical CPU `f64` after readback; GPU-evaluated estimators are `Indicator` (FLX). `F64Required` models, including every circuit and device analysis, run only on CPU or on `f64` server GPU classes, never in emulated `f64` on WebGPU.
*Why:* SPICE tolerances lie below `f32` resolution, and WGSL lets devices flush subnormals, which breaks the error-free transformations double-float arithmetic needs [WebGPU CTS floating point].
*Rejected:* `f32` execution with an added budget term; double-float emulation on WebGPU.

### Acceptance and review

1. **Static checks.** The registry rejects models lacking envelope, inflation, classes or precision tier, bounds lacking basis, transform or computable variable, and `Refuse` bounds without escalation.
2. **Oracle pass.** Registry CI runs the oracles in the canonical platform class and each targeted GPU class and assigns C0 to C2. C3 needs protected validation records that the author's agents never see.
3. **Domain review.** A std package needs two human domain reviewers with no authorship stake, who confirm C2 literature zones and catalogue entries. Third-party packages publish at whatever level their results show.
4. **Minimum credibility.** An organization's policy package may set `min_credibility_level` per check kind; checks on models below it are `Undecided { reason: CredibilityBelowMinimum }`.
5. **Domain tags.** Tags are namespaced, and review merges duplicates.

Agents draft packages, oracles and envelope changes, but never assign levels, merge widenings or approve reviews.

[[DIAGRAM diagrams/04-coverage-package-acceptance.jsx: physics package acceptance · checks, credibility levels and human review]]

Follow the top row left to right: automated checks assign C0 to C2, and typed errors loop back to the author. The bottom row adds protected validation for C3 and human review before a package reaches the coverage map.

**Decision D-COV-29:** From phase 6, with GP10, Crucible supplies a tool qualification kit for linear elasticity, modal analysis and laminates, extending the Computer Software Assurance package of contract 7.7. It holds tool operational requirements, oracle results, known-problem lists and release impact notes, and applicants qualify it per use, as under RTCA DO-330 [FAA AC 20-115D].
*Why:* qualification belongs to the applicant and the use, so a vendor supplies the material an applicant needs.
*Rejected:* claiming qualified status; no kit.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Physics packages | Models with oracles and licences | Incomplete packages rejected with typed errors | COV-O-PKG-2 | 1 |
| Weak-form models | Compiled by Flux with derivatives and estimators | `FormError` at compile time (FLX) | COV-O-VER-1 | 1 |
| Solver Wasm components | `crucible:physics/solver` on `crucible:ops/flux` | Determinizer rejection | COV-O-BENCH-7 | 2 |
| External Op solvers | Two agreeing single-use runs under signed receipts | Host failure is a `Failure`; worker loss an Abort; disagreeing runs `Unverified` | COV-O-PKG-1 | 3 |
| Precision tiers | `F32Safe` or `F64Required` per model | The plan places `F64Required` kernels on a CPU or `f64` class and says so | COV-O-PKG-3 | 1 |
| Minimum credibility | `min_credibility_level` per check kind in a policy package | `Undecided { reason: CredibilityBelowMinimum }` | COV-O-VER-3 | 1 |
| Domain tags | Namespaced; duplicates merged | Duplicates rejected with the existing name | COV-O-PKG-2 | 1 |
| Tool qualification kit | Requirements, oracle results, known problems and impact notes | A requirement without a passing oracle result blocks the kit | COV-O-VAL-3 | 6 |

## Materials

Every simulation reads material properties, and a property change that silently alters a design is as dangerous as a silent geometry change. A Material is therefore a versioned, content-addressed record pinned in `ingot.lock`; `std::materials` ships the open library, and licensed data arrive as External inputs that stay in the customer's private registry.

### The record

```rust
pub struct Material {
    pub id: MaterialId,                      // "std::materials::alu_6061_t6"
    pub version: SemVer,
    pub class: MaterialClass,                // Metal | Polymer | Ceramic | Glass | Composite | Fluid
                                             // | Biological | Granular | Electrochemical | Other(DomainTag)
    pub designations: Vec<Designation>,      // UNS, ASTM, EN, JIS, ISO, SAE AMS, GB
    pub condition: Condition,                // temper, product form, build orientation, process
    pub properties: BTreeMap<PropertyId, Property>,
    pub models: Vec<ConstitutiveBinding>,    // ConstitutiveModel id@version, parameters, envelope
    pub provenance: Provenance,              // sources, test records, calibration Ops, approvals
    pub licence: DataLicence,                // joins the usage part of Labels
    pub certifications: Vec<Certification>,
    pub environment: Vec<EnvironmentalRecord>,
    pub microstructure: Option<MicrostructureDescriptor>,
}

pub struct Property {
    pub value: PropertyField,  // Field<(Temperature, StrainRate), Stress>, for example
    pub basis: BasisSet,       // Typical; SpecLimit; A- and B-basis, lower and upper; Design { code, clause }
    pub uncertainty: Uncertainty,
    pub coverage: PointSet,    // test conditions; zones as for envelopes
    pub sources: Vec<SourceRef>,
}
```

The types live in the `material` crate (contract 12), which Flux, `mech-model` and std read.

**Decision D-COV-14:** Material properties are Fields over quantity-typed domains such as temperature and strain rate, and spatial variation enters only through state Fields on the Part.
*Why:* one Field type covers temperature dependence, anisotropy and process-induced variation, composing as property(state Fields) → `Field<Body, V>`.
*Rejected:* a separate "material curve" type; per-element material copies.

A read outside a property's `coverage` is zoned like a model, `Extrapolated` or `Invalid`, and never clamped to the nearest tabulated value.

### Two uses of a property

The bracket used its yield strength as a limit; its stiffness, had the load been a displacement, would have entered the solve. These are different statistical statements, and COV keeps them apart.

A basis value is a statistical tolerance limit. A B-basis value is a lower bound on the 10th percentile at 95% confidence, so about a tenth of the population lies below it; an A-basis value bounds the 1st percentile. 14 CFR 25.613 requires design values covering 99% of the population with 95% confidence for single-load-path structure, and 90% for redundant structure [eCFR 14 CFR 25.613]. CMH17 STATS computes these values [CMH17 STATS], and a designation's "nearest" equivalent never satisfies a specification check.

**Decision D-COV-13:** A property used as a check limit (`0.6 * yield_strength`) reads its design basis as an exact interval from the lower to the upper basis value. The check must hold at both ends, and the interval adds no part to the error budget; the basis defaults to the specification limit, else B-basis, else `MissingBasis`. A property that enters a solve carries its scatter into the input part: its distribution when it has one, otherwise its basis interval as `Estimated { Statistical { method: ToleranceLimit, α } }`. Here α is the basis's non-content on the side the sensitivity selects (0.10 for B-basis, 0.01 for A-basis), and a specification limit with no stated population gives `NotQuantified { reason: NoStatisticalBasis }`.
*Why:* a limit defined by a design value is the requirement itself, while a modulus inside a solve is a random input, and calling a B-basis value guaranteed would overstate every check's confidence by the tenth of the population below it.
*Rejected:* one guaranteed enclosure for both uses; resolving each read by its consuming check; always reading the lower value; typical values by default.

ING represents the limit interval and its decision rule; Flux propagates the solve input by the adjoint sensitivity's sign, testing monotonicity across the interval and splitting it where the response turns (FLX).

### Statistical basis

Phase 1 needs basis values for GP2's strut-scale Materials, which come from coupons rather than a handbook, so COV computes them natively (13.4). Normal and Weibull one-sided tolerance limits follow CMH-17 [CMH-17] and MMPDS [MMPDS]: a closed-form tolerance factor applied to the coupon set's fitted distribution, with a goodness-of-fit test choosing between them. MFG's as-built strut calibration states replicate counts per strut diameter and build angle large enough for a B-basis value (13.4).

Phase 3 adds the non-parametric method and pooling across batches by analysis of variance, which larger qualification programs need. A coupon set too small for the requested basis fails with `InsufficientSamples { needed }`, never with a typical value in its place. Aircraft programs read the same population and confidence requirements from 14 CFR 25.613 [LII 14 CFR 25.613].

### Assignment and state

A Part's material assignment is a Material reference, an orientation `Field<Body, Rotation>` and state Fields: residual stress, plastic strain, porosity, fibre orientation, phase fractions, cure and damage. Process models write state Fields; without one, the as-specified condition applies and the report records the assumption.

**Decision D-COV-27:** A property of the material in a stated condition is a COV `Material` property, even when the condition names a process and machine. A parameter of material and equipment together is an MFG process profile: melt-to-mould heat transfer, interfacial resistance, machine response, injection profiles and inherent-strain coefficients per machine.
*Why:* one parameter needs one owner, and its test record shows whether it depends on equipment, as mould heat transfer does and rheology does not.
*Rejected:* ownership by domain, which duplicates melt rheology across processes.

Rheology, pvT data, solidus and liquidus, fraction-solid curves, and cure and crystallization kinetics are therefore Material properties.

### Uncertainty

**Decision D-COV-22:** Material uncertainty is typed as `Aleatory { distribution, group }`, `Epistemic { interval }` or both, and correlation is declared only through named correlation groups across properties and Materials. Flux propagates intervals by nested sampling and reports probability boxes, never summed with distributions.
*Why:* correlated inputs need groups for grouped Sobol indices and Shapley effects, and summing intervals with distributions overstates confidence.
*Rejected:* a free correlation matrix; one type for both kinds.

`std::uq` propagates input error by FLX's worst-case rule, which confirms the linearized worst case with one solve at the vertex the sensitivities select and reports `NonlinearResponse` when the confirmation disagrees (FLX). A basis interval already covers its own property's aleatory scatter, so propagation covers the other properties and the epistemic parts.

### Constitutive models

A `ConstitutiveModel` maps state, internal variables and time step to stresses, fluxes and updated internal variables, and declares its thermodynamic structure, parameters, admissibility constraints and envelope. It is an Ingot function or a Wasm component implementing `crucible:material/constitutive` (contract 7.4). Models in the kernel IR get tangents by algorithmic differentiation, with `local_solve` for local Newton iterations; opaque Wasm models supply tangents that FLX's Taylor-test oracle verifies.

`std::materials::models` ships these families, by phase:

- **Phase 1.** Elastic: isotropic and anisotropic, temperature-dependent, small-strain thermoelastic. Thermal: Fourier conduction with mean-free-path curves, enthalpy phase change, emissivity spectra. Durability: S–N with mean stress; critical distances with their calibration method.
- **Phase 2.** Hyperelastic: Neo-Hookean, Mooney–Rivlin, Yeoh, Ogden, Arruda–Boyce, Gent, hyperfoam, Holzapfel–Gasser–Ogden. Plasticity: J2 with isotropic, Chaboche and Yoshida–Uemori hardening; Hill48; Yld2000-2d; Johnson–Cook; Zerilli–Armstrong; crushable foam; Drucker–Prager. Contact pairs: Coulomb and rate-and-state friction, contact conductance. Durability: ε–N.
- **Phase 3.** Viscoelastic: Prony series with WLF and Arrhenius shifts, Bergström–Boyce. Creep and viscoplasticity: Norton–Bailey, Garofalo, theta projection, Perzyna, Chaboche. Damage and fracture: Lemaitre, Gurson–Tvergaard–Needleman, Johnson–Cook and Hosford–Coulomb loci, cohesive laws, phase-field energy. Magnetic: B–H splines, Jiles–Atherton, Preisach, Bertotti. Melts and fluids: ideal gas, Peng–Robinson, CoolProp [CoolProp], Cross–WLF, Carreau–Yasuda, Herschel–Bulkley, Oldroyd-B, Giesekus, Tait pvT, ARD-RSC closures, crystallization. Also moisture, NASGRO-form crack growth and Archard coefficients.
- **Phase 4.** Composites: ply elasticity and strength; Tsai–Wu, Hashin, Puck, LaRC05; continuum damage. Dielectric and optical: Debye, Cole–Cole, Lorentz–Drude, Sellmeier, Cauchy, measured BSDFs. Electrochemical: Butler–Volmer, hysteresis and multi-species multi-reaction potentials, concentration-dependent transport. Solid-state phase transformation: JMAK, Koistinen–Marburger and transformation plasticity (13.4).
- **Phase 5.** Smart materials: linear piezoelectricity, superelastic shape-memory alloys.
- **Phase 7.** Concrete and geomaterials: concrete damage plasticity, Mohr–Coulomb, modified Cam-clay, hardening soil.

Admissibility oracles run before release: objectivity, non-negative dissipation, strong ellipticity or a positive-definite tangent over the envelope, convexity where required, causality and passivity. MFront behaviours are the largest open catalogue, under the GPL with a linking exception or CeCILL-A [MFront]; their generated C++ becomes Wasm components once ECO's licence RFC accepts the exception [TFEL GPL licence].

**Decision D-COV-28:** Industrial UMATs are ported, not wrapped: an agent-drafted Proposal translates each into an Ingot constitutive function with `local_solve`. The original runs in an External Op harness as the port's test oracle.
*Why:* an External Op per quadrature point costs a round trip per point per Newton iteration, while a port gets algorithmic tangents everywhere.
*Rejected:* wrapping UMATs as External Ops; Fortran compiled to Wasm until a toolchain passes the same oracle.

### Calibration from test data

Calibration turns test records into a Material version through cached Ops, so every fitted parameter traces to the tests behind it.

1. **Ingest.** Records follow ISO 10303-235:2019, which covers measured values and who measured them [ISO 10303-235]. Signed rig measurements arrive as Evidence records citing method (such as ASTM E8/E8M [ASTM E8/E8M-25]), specimen, conditions and raw curves.
2. **Reduce.** True stress and strain, toe compensation and filtering, each a declared Op.
3. **Identify.** Least squares with gradients; finite-element model updating for non-uniform specimens; the virtual fields method for DIC data.
4. **Quantify.** Laplace approximation or seeded Markov chain Monte Carlo; correlations become correlation groups.
5. **Bound.** The test conditions form the property's `coverage`, with d_cal from their spacing; the calibrator declares the extrapolated region.
6. **Admit.** Admissibility oracles run over the whole envelope.
7. **Basis.** With enough replicates, basis values come from the tolerance limits of [Statistical basis](#statistical-basis).
8. **Publish.** The version enters a Proposal with fit residuals, held-out error, parameter uncertainty, envelope and inputs; overlap with validation data is rejected (contract 13.1).

### Material databases and licensing

**Decision D-COV-15:** Every Material carries a typed `DataLicence` in the usage part of its labels, which joins through every derivation and is compared at exits: `release_data` Acts, exports, registry publishing and responses to model contexts (contract 5.3). A connector publishes only after counsel's written review of its terms is recorded in its `DataLicence`.
*Why:* licences differ sharply, shared designs must not leak licensed tables, a licence restricts redistribution rather than reading inside the tenant, and only counsel can read terms for derived results.
*Rejected:* tracking licences by hand; refusing licensed data; licences in the confidentiality part, which would split encryption domains and workers per combination of databases.

| Source | Content | Licence (as verified) | Integration | Phase |
| --- | --- | --- | --- | --- |
| `std::materials` | Curated open library | Each value cites an open source | Built in | 1 |
| NIST Standard Reference Data | 49 free and 41 fee-based databases, including REFPROP and ICSD [NIST SRD] | Copyrighted under the Standard Reference Data Act; reproduction needs NIST's permission [NIST SRD law] | Connector per database; fee-based ones need a customer licence | 3 |
| Materials Project | DFT properties of inorganic compounds | CC BY 4.0 downloads; no scraping; data "computed, and may not be accurate enough" [Materials Project terms] | ICME connector; C1 at most | 5 |
| MMPDS | Allowables for aerospace metals and fasteners; MMPDS-2026 current [MMPDS] | Purchased; a download licenses one simultaneous user [MMPDS order form] | Customer-licensed connector | 6 |
| CMH-17 | Composite data, test and statistics guidance [CMH-17] | Licensed; CMH17 STATS has a single-user licence [CMH-17 software] | Customer-licensed connector | 6 |
| Ansys Granta MI | 250,000+ reference materials; MaterialUniverse environmental data [Ansys Granta MI] | Commercial | Through the customer's Granta MI Scripting Toolkit [Granta MI Scripting Toolkit] | 5 |
| MatWeb | Datasheets | Terms forbid redistribution, mass export and collecting over 500 materials [MatWeb terms] | None | Not planned |
| Plastics databases (CAMPUS, UL Prospector) | Grades with rheology and pvT | CAMPUS: personal consultation, no machine interface [CAMPUS]; Prospector: internal use, no automated retrieval [UL Prospector terms] | None; users enter grades with their datasheets | 3 |
| CoolProp | Fluid properties | MIT [CoolProp] | Built in | 3 |
| ICE embodied carbon | 200+ construction materials; V5.0 Educational, June 2026 | Educational use only; software needs the licensed IC+ dataset [Circular Ecology ICE] | IC+ connector | 5 |
| ecoinvent | Life-cycle inventory | A developer licence grants integration; users receive LCIA data only [ecoinvent licences] | Connector under a developer licence | 5 |

### Microstructure and ICME

A `MicrostructureDescriptor` records grain size distribution, texture, phase fractions, porosity and defects, fibre architecture and lattice cells, with measurement provenance. Integrated computational materials engineering (ICME) chains process, microstructure and property models; each link carries its own envelope, so a chain is as valid as its weakest link, and chains are validated against AM-Bench data [NIST AM-Bench].

| Link | Method | Delivery | Phase |
| --- | --- | --- | --- |
| Process to microstructure | Thermal histories into JMAK, Koistinen–Marburger and solidification maps | Nat | 6 |
| Microstructure to properties | Hall–Petch, rules of mixtures, Mori–Tanaka; FFT RVE solvers with crystal plasticity | Nat, Wasm | 5 |
| Thermodynamics | CALPHAD through customer-licensed tools or pycalphad (MIT) [pycalphad] | Ext | 6 |
| Atomistic to continuum | DFT and machine-learned-potential results as provenance (MACE, Materials Project) | Ext | 6 |
| Exchange with process tools | VMAP data-interface standard | Interop | 5 |

### Environmental data

An `EnvironmentalRecord` gives global warming potential per unit mass by life-cycle stage, embodied energy, water use, recycled content, recyclability and restricted substances. Each value carries geography, reference year, system boundary, method standard, source, licence and uncertainty. MFG owns product life-cycle assessment and passports.

Phase 2 ships what MFG's carbon and RoHS checks need: entered or supplier-declared factors and declared substances. Database connectors arrive in phase 5.

**Decision D-COV-16:** Environmental values follow the provenance, uncertainty and licence rules of mechanical properties, and an embodied-carbon check reports its boundary and year.
*Why:* carbon numbers vary by source and boundary more than most mechanical properties do.
*Rejected:* a single "CO2 per kg" number per Material.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Property Fields | Fields over state domains, declared interpolation | Reads outside `coverage` zoned, never clamped | COV-O-MAT-8 | 1 |
| Directional properties | Tensors in a material frame with a symmetry class | Ill-formed tensors rejected with the failing eigenvalue | COV-O-MAT-1 | 1 |
| Units | Every property a `Quantity<D>` | Compile error | COV-O-MAT-2 | 0 |
| Property reads | Limits read the basis interval exactly; solve inputs carry a statistical part at the basis's α. Requires: FLX Property-basis propagation | `MissingBasis { available }`; `NotQuantified { NoStatisticalBasis }` | COV-O-MAT-6 | 1 |
| Statistical basis (13.4) | Normal and Weibull one-sided tolerance limits per CMH-17 and MMPDS, with goodness of fit | `InsufficientSamples { needed }` | COV-O-MAT-4 | 1 |
| Allowables | Non-parametric and pooled-batch basis values | `InsufficientSamples { needed }`; `BatchesNotPoolable` | COV-O-MAT-4 | 3 |
| Uncertainty | Aleatory with groups; epistemic intervals | Input part `NotQuantified { MissingUncertainty }` | COV-O-ERR-1 | 2, 3 epistemic |
| Designations and certification | Equivalence basis; specification and lot-certificate links | "Nearest" fails specification checks; missing certificates fail release | COV-O-MAT-7 | 1, 3 certification |
| Constitutive library | `crucible:material/constitutive`; `local_solve` tangents | Inadmissible models rejected; `TangentInconsistent` | COV-O-MAT-1 | 1 to 7 per family |
| UMAT ports | Ingot port checked against the original | Rejected beyond 10⁻¹⁰ relative or on a failed Taylor test | COV-O-MAT-10 | 3 |
| Calibration | `calibrate(model, tests) -> (ConstitutiveBinding, CalibrationReport)`; inverse, full-field, model selection | Non-identifiable parameters reported with their null space | COV-O-MAT-3 | 2, 3 inverse, 5 DIC |
| Data licences | `DataLicence` in the usage part, with counsel's review per connector | Forbidden export or release refused, naming the licence | COV-O-MAT-5 | 3 |
| Connectors | External inputs pinned in `ingot.lock` | Fetch failure keeps the pinned version | COV-O-MAT-7 | 3 |
| Microstructure and ICME | Descriptors, state Fields, linked envelopes | Zoned by the weakest link | COV-O-BENCH-5 | 5, 6 |
| Environmental records | Boundary, year, source and licence per value | `BoundaryMismatch` when a check mixes boundaries | COV-O-MAT-9 | 2, 5 connectors |

## Reference

### Crates, packages and interfaces

| Item | Kind | Contents |
| --- | --- | --- |
| `material` | Rust crate, Engine core row (contract 12) | `Material`, `Property`, `PropertyField`, `BasisSet`, `Uncertainty`, `ConstitutiveBinding`, `ValidityEnvelope`, `RegimeBound`, `ValidityZone`, `ValidityError`, `DataLicence` data |
| `flux-op-material` | Operation family owned with FLX | Property interpolation over state domains, tolerance limits, calibration reduction and identification Ops |
| `std::physics` | Ingot packages | Physics models by domain; `std::physics::regime` (regime variables and detectors); `std::physics::limits` (`OutOfReach`, `OutOfScope`) |
| `std::materials` | Ingot packages | The open Material library; `std::materials::models` (constitutive families); the model-form allowance catalogue |
| `crucible:physics/solver` | WIT world | Solver Wasm components on `crucible:ops/flux` |
| `crucible:material/constitutive` | WIT world (contract 7.4) | Constitutive models with consistent tangents |

### Regime variables

| Variable | Definition | Typical users |
| --- | --- | --- |
| Stress ratio, rotation | σ_eq/σ_proportional(T) of the assigned Material; rotation from the displacement Field | Small-strain linear elasticity |
| Homologous temperature | T / T_melt, absolute temperatures | Creep onset, rate-independent plasticity |
| Strain rate, triaxiality, Lode parameter | From strain-rate and stress Fields | Johnson–Cook range, ductile fracture |
| Coupling diameter over wall thickness | Diameter of a rigid remote point's coupled region over the local wall thickness | Rigid couplings on thin walls |
| Reynolds, Mach, y⁺ | u·L/ν with L declared per bound | Laminar models, wall treatment |
| Separation | Wall-shear sign change; Clauser parameter β = (δ*/τ_w)·dp/dx | RANS envelopes |
| Knudsen | Mean free path over a declared gap or feature length | Continuum, slip, DSMC and free-molecular models |
| Biot, Rayleigh, Prandtl | From geometry and properties | Lumped capacitance, correlations |
| Wall resolution | Cells at p = 2 across δ_T = H·Ra_H^(−1/4); cells across the cavity half-thickness | Laminar heat transfer; 3D fill and pack |
| Weber, capillary, Weissenberg | From interface and rheology Fields | Breakup, viscoelastic flow, die-casting filling |
| Lubrication geometry | h/L_flow; \|∇h\|; distance in units of h from gates, rib roots, steps and the flow front | Hele-Shaw filling |
| Local slenderness | t / L_local for walls, d / L_local for members (contract 7.1) | Shell and beam models |
| Member inelasticity | σ_cr,Euler / σ_proportional per member | Eigen-buckling of members and struts |
| Strut imperfection | Waviness amplitude over radius of gyration, from MFG's calibration | Strut strength and buckling |
| Lattice regimes | Cell size over gradient length; cells to the boundary; relative density; slenderness times macro strain against a Bloch-wave bound | Lattice models |
| Imperfection sensitivity | Koiter coefficient from FLX (phase 2), or a classifier of known sensitive shells | Eigen-buckling of shells |
| Mass ratio, frequency separation | ρ_s·t/(ρ_f·L) or added-mass fraction; frequencies against forcing bands | Weak fluid–structure coupling |
| Resonance overlap | Eigenvalue bounds against the forcing band, with half-power width 2ζω | Harmonic and random response |
| Electrical size kL, skin depth δ/L, optical size L/λ | From frequency or wavelength, geometry and properties | Quasi-static electromagnetics, geometric optics |
| Mean-free-path share | Conductivity share from phonon mean free paths above the feature size | Fourier conduction |
| Lambda ratio | Elastohydrodynamic film thickness over composite roughness | Gear and bearing ratings |
| Advance ratio, tip Mach number | V/(nD); blade-tip speed over sound speed | Rotor aerodynamics |
| C-rate, state of charge, cell temperature | From cell states | Battery model selection |
| Acoustic amplitude p′/ρc² | From the pressure Field | Linear acoustics |
| Cycles N, stress ratio R, ΔK | From load histories | Fatigue regimes |
| Scale ratio ℓ/L | Microstructure length over feature size | Homogenized properties |

### Failures

```rust
pub enum ValidityError {
    OutsideEnvelope {
        model: ModelRef, variable: RegimeVariableId, value: QuantityValue,
        bound: QuantityInterval, zone: ValidityZone, region: Query,
        escalate_to: Vec<ModelRef>,
    },
    Unassessed { model: ModelRef, variable: RegimeVariableId, missing: MissingInput },
    NoCoveringModel { domain: DomainTag, regime: Vec<RegimeSample>, see: LimitId },
}
```

Other typed failures COV raises: `MissingBasis { available }`, `InsufficientSamples { needed }`, `BatchesNotPoolable`, `MissingStandard { code, edition }`, `NotRegularized`, `RegimeUncomputable { variable }`, `BoundaryMismatch` and `TangentInconsistent`. Their error codes take the form `cov/<snake_case>` (contract 7.6).

### Coverage matrix

Columns: domain and scales; the L0 · L1 · L2 rungs; the L3 method; envelope defaults; the benchmark; phase and delivery. A dash in a rung column means the ladder has no rung at that level.

#### Solid mechanics

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Linear elasticity (µ Me P L) | Beam, plate and shell formulas · frame networks · static condensation | High-order FEM on the immersed octree; planar and axisymmetric sections (13.4); IGA on trimmed B-rep; finite cell for voxels; symmetry and cyclic sectors (13.4) | σ_eq/σ_proportional(T) ≤ 0.9 calibrated, ≤ 1.0 extrapolated, `Refuse` above; rotation ≤ 0.05 rad; feature ≥ 10 grains or a strut-scale Material | NAFEMS LE1 92.7 MPa, LE10 −5.38 MPa, LE11 −105 MPa [FeenoX examples]; Lamé thick cylinder; GP1, GP2 | 1 (octree, planar, axisymmetric), 2 (IGA, finite cell, frame networks, symmetry and cyclic sectors) · Nat |
| Shells, beams and frames (Me P L) | Beam and plate formulas · frame networks · — | Reissner–Mindlin and IGA Kirchhoff–Love shells; Timoshenko and Vlasov beams; Nitsche couplings (FLX) | t/L_local ≤ 0.2, or ≤ 0.05 for Kirchhoff–Love; d/L_local ≤ 0.2; reduction error from FLX's patch re-solves and global modelling-error term | NAFEMS shell and beam cases | 1 lattices, 2 · Nat |
| Idealized connections (Me P L) | Rigid-body and spring formulas · — · — | Remote points, point masses and springs (phase 1); bushings, fastener and spot-weld connectors (phase 2) (FLX) | Rigid coupling diameter ≤ 5 local wall thicknesses, else `Flag`; joint stiffness and damping from tests of the joint class (OOR-18) | RBE2 and RBE3 references; bolted lap joint | 1, 2 connectors · Nat |
| Geometric nonlinearity (µ Me P L) | — | Total Lagrangian FEM with arc-length continuation | Limit and bifurcation points reported, never stepped over | NAFEMS R0024 group [NAFEMS Nastran verification] | 2 · Nat |
| Plasticity (µ Me P L) | Neuber and Glinka notch rules · — · — | Finite-strain J2, Hill48, Yld2000-2d, Chaboche; tangents through `local_solve` | Rate-independent below homologous temperature 0.4; past uniform elongation only with damage | NAFEMS R0024 panel; thick cylinder | 2 · Nat |
| Hyperelasticity (µ Me P) | — | Mixed u–p and F-bar; Neo-Hookean to Gent; axisymmetric seals with contact | Stretch within the calibrated range per mode; strong ellipticity | Cook's membrane; patch tests | 2 · Nat |
| Viscoelasticity (µ Me P) | — · Prony networks · complex-modulus modal | Generalized Maxwell with WLF or Arrhenius shift; Bergström–Boyce | Temperature and frequency within the master curve | Analytic creep and relaxation | 3 · Nat |
| Creep (Me P L) | Larson–Miller · — · — | Norton–Bailey, Garofalo, theta projection; Kachanov–Rabotnov damage | Time ≤ longest test calibrated, ≤ 3× extrapolated (OOR-5) | NAFEMS R0027 | 3 · Nat |
| Contact and friction (µ Me P L) | Hertz, Boussinesq · — · — | Mortar contact on fitted tetrahedra (13.4); Incremental Potential Contact from phase 5 (FLX) [IPC Toolkit] | Penetration below tolerance; friction only from a tested pair (OOR-19) | NAFEMS R0094; Hertz | 2 · Nat |
| Bolted and bonded joints (Me P L) | VDI 2230-1:2015 · joint springs · — | Preloaded bolts; cohesive zones with Benzeggagh–Kenane mixing | Joint parameters and damping from tests of the joint class (OOR-18) | DCB and ENF | 2 (bolts), 3 (cohesive) · Nat |
| Pressure equipment (Me P L) | Design-by-rule formulas · — · — | Design by analysis to ASME VIII-2 Part 5 and EN 13445-3: stress linearization and classification, elastic-plastic collapse, ratcheting | Code edition recorded; licensed code package required | The cited edition's worked examples | 5 · Nat |

#### Dynamics and stability

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Modal analysis (µ Me P L) | Rayleigh, Dunkerley · lumped MDOF · Craig–Bampton | Lanczos and LOBPCG (13.4); two-sided eigenvalue bounds; prestressed modes with stress stiffening and spin softening; cyclic-sector modes by harmonic index (13.4) | Linear; damping from test (OOR-18) | NAFEMS free vibration [NAFEMS P18] | 1, 2 (prestressed, cyclic, Craig–Bampton) · Nat |
| Vibration and shock (Me P L) | SDOF, Miles, shock spectra · — · modal superposition with residual vectors | Direct and modal frequency response; base excitation; PSD response; response spectrum with SRSS and CQC; damping models (13.4); implicit generalized-α | Forcing band within modal coverage; damping from test; an eigenvalue bound overlapping the forcing band `Flag` | NAFEMS R0016; SDOF and two-DOF closed forms | 2 · Nat |
| Rotordynamics (Me P) | Jeffcott rotor · rotor beams · Campbell modal | Prestressed gyroscopic eigenproblems with spin softening (FLX); fluid-film bearings from the Reynolds equation | Bearings linearized at operating speed | Jeffcott critical speed | 2 · Nat |
| Buckling (µ Me P L) | Euler, Johnson, Perry–Robertson; strut-strength check · — · linear eigen-buckling (13.4) | Arc-length post-buckling with imperfections and plasticity; Koiter asymptotics (FLX) | Struts decide by strength above inelasticity ratio 1; eigen-buckling `Calibrated` below 0.5; `Refuse` at `SignOff` on imperfection-sensitive shells | NAFEMS R0024; Euler and Johnson columns; single-strut compression coupons | 1 linear and strut strength, 2 nonlinear and Koiter · Nat |
| Explicit dynamics, impact, crash (Me P L) | Energy methods · lumped crash networks · — | Explicit dynamics with diagonal mass and penalty contact (FLX); erosion from COV damage; checks on channel-filtered acceleration, energy absorbed, mean crush force and time-averaged strain | Mass scaling ≤ 2% calibrated, `Refuse` above 5%; hourglass energy ≤ 10% of internal; failure `Flag` (OOR-6); seeded imperfection ensembles where buckling-sensitive | Taylor bar; GP5 drop; GP9 crash box | 3 drop, 5 crash (13.4) · Nat; OpenRadioss (AGPL) as Ext reference [OpenRadioss] |

#### Durability: fatigue, fracture, wear

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Stress-life (Me P L) | Basquin with Goodman, Gerber or Walker · rainflow · — | Critical plane (Findley, Dang Van) with surface, size and notch factors; probabilistic S–N; Dirlik and narrow-band PSD fatigue; critical distances by their calibrated method | N ≥ 10⁴; R and temperature within tests; defects below Kitagawa–Takahashi | Held-out coupons; narrow-band closed form | 1 uniaxial, 2 multiaxial and PSD · Nat |
| Strain-life (Me P L) | Coffin–Manson, Morrow, SWT · — · — | Fatemi–Socie, Brown–Miller on elastic-plastic FE | Cyclic curve from the same condition | Notched specimens | 2 · Nat |
| Weld fatigue (Me P L) | Nominal, hot-spot and effective notch stress (IIW, EN 1993-1-9 [JRC Eurocode 3]) · — · — | Structural-stress methods on shells and solids | Weld class and quality declared | Hand calculations to the cited code | 2 · Nat |
| Gears, bearings and shafts (Me P) | Gears to ISO 6336:2019 or ANSI/AGMA 2101-E25; bearings to ISO 281:2007 [ISO 281] with ISO 16281:2025; shafts to DIN 743:2012 or the FKM guideline · — · loaded tooth contact analysis with FE influence coefficients | Mortar contact on fitted tetrahedra as the validation rung (13.4) | Lambda ratio and temperature within the rating's scope; load spectrum declared | ISO/TR 6336-30 examples [ISO/TR 6336-30]; GP3 | 2 (13.4) · Nat |
| Lubrication and rolling-contact fatigue (µ Me P) | Hamrock–Dowson film thickness · — · — | Elastohydrodynamic Reynolds equation with pressure–viscosity, elastic deflection by FFT or hierarchical matrices and a semismooth Newton for cavitation; subsurface critical-plane fatigue | Isothermal Newtonian film unless declared; life `Flag` without bearing-steel data | Hertz pressure; Hamrock–Dowson film thickness | 2 Hamrock–Dowson, 3 EHL · Nat |
| Crack growth (Me P L) | Paris, NASGRO with handbook K · — · — | Interaction-integral K and J; spectrum retardation | Small-scale yielding; ΔK above threshold | NAFEMS R0020 | 3 · Nat |
| Fracture (µ Me P L) | K_Ic, failure assessment diagrams · — · — | Cohesive zones; phase field (AT1, AT2); Gurson–Tvergaard–Needleman, Hosford–Coulomb | Ductile `Flag` (OOR-6) | Sandia Fracture Challenge [Boyce et al. 2014] | 2 LEFM, 3 cohesive, 4 phase field, 5 ductile · Nat |
| Wear and erosion (µ Me P) | Archard; Finnie erosion [Finnie 1960] · — · — | Archard on local pressure and slip with geometry update; particle impact erosion | Coefficients from the tested pair and medium; erosion `Flag` | Pin-on-disc | 3 wear, 5 erosion · Nat |

#### Composites and architected materials

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Laminates (Me P L) | Classical laminate theory · — · — | Layered and IGA shells on draped fibre-angle Fields (plies and draping: MEC) | Through-thickness stress needs layerwise or solid models | NAFEMS R0031 | 4 (13.4) · Nat |
| Progressive failure (Me P L) | Tsai–Wu, Hashin, Puck, LaRC05 · — · — | Continuum damage with cohesive interlaminar zones, calibrated in a building-block pyramid | `Flag`: in WWFE-II no theory matched all test data | WWFE-II [Christensen WWFE-II] | 4 · Nat |
| Short-fibre moulded composites (Me P) | Rule of mixtures · — · — | Mori–Tanaka averaging over the orientation tensor Field from filling | Aspect ratio and fraction within calibration | Unidirectional limit | 3 (13.4) · Nat |
| Lattices (µ Me P) | Gibson–Ashby · — · homogenization with localization | Beam lattices with node corrections fitted on CT scans of as-built cells (strut cells); Reissner–Mindlin mid-surface shells (sheet cells); full-resolution immersed FEM as reference | Cell over gradient length ≤ 0.1; `Invalid` within 2 cells of an uncorrected boundary; relative density within the node-correction calibration; `Flag` above the Bloch-wave bound | Full-resolution unit cells (FLX-O-COUP-2) | 1 strut cells, 2 sheet cells · Nat |

#### Heat transfer

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Conduction (N µ Me P L) | Slab, fin and shape factors · RC networks · moment matching | High-order FEM, planar and axisymmetric sections, IGA, immersed methods | Fourier law `Refuse` above the declared mean-free-path share | NAFEMS T2 to T4 | 1 (FEM, planar, axisymmetric), 2 (IGA, networks), 3 (moment matching) · Nat |
| Convection (Me P L) | Nusselt correlations within published ranges · flow networks · — | Conjugate heat transfer on laminar, RANS or LES flow | Correlation ranges `Refuse`; conjugate analysis inherits the flow envelope; laminar walls `Extrapolated` below five cells across δ_T | NAFEMS T4; Graetz | 2 correlations, 3 laminar and natural, 4 turbulent (13.4) · Nat |
| Radiation (Me P L) | Two-surface enclosures · radiosity networks · — | Ray-traced view factors; Monte Carlo for specular and spectral surfaces; discrete ordinates | Gray-diffuse declared; spectral bands where emissivity varies | Analytic view factors; closure ΣF = 1 within 10⁻⁶ | 3, 4 discrete ordinates · Nat |
| Solid–liquid phase change (µ Me P) | Stefan, Neumann · — · — | Enthalpy method with mushy zone | Freezing range declared; no undercooling | Stefan analytic | 3 · Nat |
| Boiling, condensation, heat pipes (Me P) | Rohsenow, Nusselt film · heat-pipe and vapour-compression networks with CoolProp · — | VOF with phase change | Correlations `Refuse` outside range; heat-pipe limits reported; resolved boiling `Flag` | Nusselt film analytic | 4, 5 (VOF, 13.4) · Nat |
| Moisture and hygro-mechanics (µ Me P L) | Equilibrium moisture tables · — · — | Fickian diffusion with sorption isotherms, hygro-expansion, mechano-sorptive creep | Humidity and temperature within sorption data; mechano-sorptive creep `Flag` | Fickian slab | 3 packages, 7 timber · Nat |
| Ablation and pyrolysis (Me P) | Heat of ablation · 1D charring ablator · — | Surface energy balance with B′ tables and recession | `Flag` always | Ablation Workshop test cases [Risch and Kostyk 2012] | 6 · Wasm |
| Joule heating and thermoelectrics (µ Me P) | Resistive and Peltier module formulas · — · — | Electro-thermal coupling with temperature-dependent resistivity; Seebeck–Peltier–Thomson FEM | Resistivity within data; linear thermoelectric coefficients | Wire heating; analytic module | 4 Joule (13.4), 5 thermoelectric · Nat |

#### Fluids

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Incompressible laminar (µ Me P) | Hagen–Poiseuille, Moody · duct networks · POD-Galerkin | Stabilized high-order FEM or DG | Re below transition (pipe: 2,000 calibrated, 2,300 extrapolated) | Lid-driven cavity [Ghia et al. 1982] | 3 · Nat |
| RANS (Me P L) | Loss data · networks with loss coefficients · — | Spalart–Allmaras, SST, GEKO; γ–Reθ transition; quadratic constitutive relation; wall models (FLX) | Attached flow calibrated; separation `Flag`; y⁺ range declared | NASA TMR 2DZP, 2DB, 2DMEA, 2DWMH, ATB [NASA TMR] | 4 · Nat |
| Turbomachinery and fans (Me P L) | Fan laws, P–Q curves · fan and flow-resistance Network elements · — | Rotating reference frames (laminar phase 3, RANS phase 4), sliding interfaces (phase 4), mixing planes (phase 5) (FLX) | Frozen-rotor and mixing-plane solves: strong blade-row interaction `Flag`; a fan pressure jump only inside its measured curve | Measured fan P–Q curve | 3, 4, 5 (13.4) · Nat |
| Hydraulic, pneumatic and thermofluid systems (Me P L) | Orifice and pipe-loss formulas · ELX element libraries with CoolProp media · — | One branch in 3D flow through the ladder link | Cavitation and choking `Flag`; media within their property range | Analytic water-hammer wave speed | 4 single-phase, 5 two-phase and pneumatic (13.4) · Nat |
| Scale-resolving: DDES, WMLES, LES (Me P L) | — | Entropy-stable DG [Trixi.jl] and flux reconstruction [PyFR]; non-equilibrium wall models | Cost from Yang–Griffin scalings; equilibrium wall models `Flag` in adverse pressure gradients [Agrawal et al. 2024] | 2DWMH hump | 5 · Nat |
| DNS (µ Me) | — | Spectral and high-order DG | `Refuse` above the a priori budget (OOR-1) | Taylor–Green vortex [Brachet et al. 1983] | 5 · Nat |
| Lattice Boltzmann (Me P L) | — | Cumulant collision with wall models (FLX); XLB (Apache-2.0) as reference [XLB] | Ma ≤ 0.1 calibrated, ≤ 0.3 extrapolated | As LES | 4 · Nat |
| Compressible flow (Me P L) | Isentropic and shock relations · quasi-1D nozzle · — | Entropy-stable DG and flux reconstruction; SU2 (LGPL-2.1) as reference [SU2] | Perfect gas below a declared temperature; nonequilibrium Ext | ATB, ONERA M6 | 5 · Nat |
| Free surface and resolved multiphase (µ Me P L) | Linear wave theory · — · — | Geometric VOF, conservative level set, Cahn–Hilliard; weakly compressible SPH | Converged at k_max·η_KH ≥ 60 with second-order schemes; coarser `Flag` | Dam break [Martin and Moyce 1952]; rising bubble | 5 (13.4) · Nat |
| Dispersed multiphase and particle tracing (Me P L) | Settling and drag correlations · — · — | One-way particle tracing on a flow Field; Euler–Lagrange with two-way coupling; Euler–Euler | Volume-fraction limit per model; one-way only below a declared mass loading; breakup `Flag` (OOR-8) | Stokes settling [Hysing et al. 2009] | 5 (13.4) · Nat |
| Cavitation (Me P) | Cavitation number; Rayleigh bubble collapse [Brennen cavitation] · — · — | Mixture models with Schnerr–Sauer or Zwart transfer | `Flag` always; erosion out of reach (OOR-9) | Rayleigh collapse time [Rayleigh 1917] | 6 · Nat |
| Non-Newtonian (µ Me P) | Power-law pipe flow · — · — | Carreau–Yasuda, Cross–WLF, Herschel–Bulkley; Oldroyd-B, Giesekus, PTT with log-conformation | Shear rate within rheometry; Weissenberg within the verified range | Poiseuille; 4:1 planar contraction [Alves et al. 2003] | 3, 5 viscoelastic · Nat |
| Porous media (µ Me P L) | Darcy, Ergun · — · — | Darcy–Brinkman–Forchheimer; permeability from pore-scale lattice Boltzmann | Pore Reynolds number within the law | Porous channel | 3, 4 (lattice Boltzmann) · Nat |
| Rarefied gas (µ Me P) | Free-molecular formulas · — · — | Slip and temperature jump; DSMC with SPARTA (GPL) [SPARTA] | Continuum below Kn 0.001, slip to 0.1, transitional to 10 | Microchannel slip | 5 · Nat slip, Ext DSMC |
| Free-molecular flow (µ Me P) | Clausing factors · — · — | Angular coefficient method on Flux view factors | Kn above 10 | Clausing factor of a tube | 5 · Nat |
| Microfluidics (µ Me) | Stokes resistances · hydraulic networks · — | Stokes FEM with electro-osmotic slip and Nernst–Planck transport | Debye length much smaller than the channel | Electro-osmotic plug flow | 5 · Nat |
| Combustion (Me P L) | Adiabatic flame temperature · reactor networks with Cantera (BSD-3) [Cantera] · flamelet tables | Flamelet-progress-variable, FGM; finite-rate chemistry in LES | `Flag` always (OOR-7) | Flame speeds; Sandia piloted flames of the TNF Workshop [TNF piloted flames] | 6 · Wasm kinetics, Nat transport |

#### Acoustics and ultrasonics

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Linear acoustics (Me P L) | Sabine, Eyring · duct transfer matrices · modal | High-order FEM with PML on indefinite Helmholtz solvers (13.4); fast BEM; geometrical room acoustics | p′/ρc² ≤ 10⁻²; points per wavelength above the order's minimum | Pulsating sphere, baffled piston | 3 · Nat |
| Vibro-acoustics (Me P L) | — · statistical energy analysis · modal | Structural–acoustic FEM and FEM–BEM | SEA needs 3 modes per band; heavy fluids and light panels two-way | Plate radiation | 3 FEM, 5 SEA · Nat |
| Porous absorbers (Me P) | Delany–Bazley · transfer matrix · — | Johnson–Champoux–Allard; Biot | Flow resistivity within measured range | Impedance tube | 5 · Nat |
| Aeroacoustics (Me P L) | Gutin tonal noise · — · — | Ffowcs Williams–Hawkings from blade loading or scale-resolving surfaces | Broadband `Flag` without scale-resolving input | GP6 rotor acoustics | 4 tonal, 5 broadband · Nat |
| Ultrasonic testing (µ Me P) | Ray and beam-spread formulas · — · — | Spectral-element or DG elastodynamics with transducers | Linear; grain scattering `Flag` without microstructure | Lamb-wave dispersion | 6 · Nat |

#### Electromagnetics

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Electrostatics (N µ Me P L) | Plate, sphere, coaxial formulas · capacitance networks · — | High-order FEM; fast BEM; capacitance extraction as in Palace (Apache-2.0) [Palace] | kL ≤ 0.1 calibrated, ≤ 0.3 extrapolated | Sphere, coaxial; Palace | 3 · Nat |
| Magnetostatics (µ Me P L) | Magnetic circuits · reluctance networks · — | Nédélec FEM with tree–cotree gauging and Newton on B–H curves; axisymmetric coils | B within measured B–H range | TEAM 13 [Compumag TEAM] | 3 · Nat |
| Eddy currents and induction (µ Me P L) | Skin-depth formulas · — · — | A–φ and T–Ω; surface impedance | Surface impedance only where δ/L ≤ 0.1 | TEAM 7 and 36 | 4 · Nat |
| Electric machines (Me P) | dq circuits · loss and thermal networks · flux-linkage maps | Sliding-interface motion; Bertotti iron loss; magnet eddy loss; demagnetization | Loss coefficients per lamination grade and band | GP6 motor tests | 4 · Nat |
| RF and antennas (Me P L) | Line formulas · S-parameter networks · Krylov sweeps | Nédélec FEM with wave ports and fast sweep; FDTD for broadband; MoM with fast multipole; Bloch-periodic unit cells, Floquet ports and finite arrays (13.4) | Dispersion fit inside the measured band; Floquet modes attenuated before the port | Dipole with a Hallén reference; Mie sphere; infinite dipole array | 4 drone antenna, 5 general and periodic · Nat |
| Signal and power integrity (µ Me) | RLGC lines · — · vector fitting | 2D cross-section RLGC (ELX); 3D quasi-static RLCG and full-wave extraction (13.4) | Causality and passivity enforced | Microstrip | 3 cross-sections, 4 3D extraction · Nat; ELX owns use |
| EMC (Me P) | Shielding formulas · cable models · — | FDTD and DG time domain with field-to-cable coupling | `Flag` always for compliance prediction | Enclosures with apertures [Robinson et al. 1998] | 4 emissions, 5 immunity · Nat |
| Charged-particle tracing (µ Me P) | Child–Langmuir law · — · — | Lorentz-force trajectories with space-charge iteration on electrostatic and magnetostatic Fields; secondary emission declared | Fields inside their solve's zone; relativistic speeds declared | Child–Langmuir diode | 5 · Nat |

#### Optics and photonics

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Imaging optics (µ Me P) | Paraxial ABCD · sequential ray tracing · — | Differentiable ray tracing with polarization; Fourier-optics PSF and MTF | Geometric optics where L/λ ≥ 100 | Singlet and doublet | 5 · Nat |
| Illumination and stray light (Me P L) | Photometric formulas · — · — | Spectral Monte Carlo path tracing with measured BSDFs [Mitsuba 3] | BSDF within measured angles and wavelengths | Light-guide measurements | 3 light pipes, 5 · Nat |
| Wave optics and photonics (N µ) | Thin-film matrices · — · eigenmode expansion | FDTD, DG, RCWA, FEM mode solvers; Meep (GPL) as Ext reference | Linear unless declared | Mie; slab modes | 6 · Nat |

#### Electrochemistry and chemical kinetics

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Battery cells, reduced (µ Me P) | Capacity formulas · equivalent circuits with OCV, entropic heat and LFP hysteresis [PyBaMM OCP submodels] · SPM, SPMe | — | C-rate, temperature and SOC bounds per rung; lithium plating `Flag` | Ladder at low C-rate; drive cycles | 4 (13.4) · Nat |
| Battery cells, DFN (µ Me P) | — | Doyle–Fuller–Newman as parameter-domain forms (FLX); MSMR OCV [PyBaMM lithium-ion models]; PyBaMM reference [Sulzer et al. 2021] | As above, plus particle-radius range | PyBaMM DFN [PyBaMM] | 5 (13.4) · Nat |
| Swelling and stack pressure (Me P) | Thickness change with SOC · pad and stack springs · — | Particle expansion homogenized to the cell against pad stiffness; Ai et al.'s model in PyBaMM [PyBaMM swelling] | Expansion curve from measured cell thickness; pad stiffness from test | Thickness and force against SOC [PyBaMM particle mechanics] | 4 (13.4) · Nat |
| Battery packs (Me P) | Series-parallel scaling · cell, busbar and thermal networks · — | Cells in 3D pack thermal and coolant flow; pseudo-4D packs | Cell spread from measurement | GP6 pack test | 4, 6 pseudo-4D · Nat |
| Battery degradation (µ Me P) | Calendar and cycle fade · — · — | SEI growth, plating, particle cracking, active-material loss | `Flag` always; beyond tested duration `Invalid` (OOR-5) | Held-out ageing data | 5 · Nat |
| Abuse mechanics (Me P) | — | Homogenized jelly-roll crush with failure strain, coupled to runaway screening | `Flag` always: short onset is empirical | GP12 crush tests | 6 (13.4) · Nat |
| Thermal runaway (Me P) | ARC onset · multi-step Arrhenius · — | 3D abuse with decomposition kinetics and propagation | `Flag` always; venting and fire out of reach (OOR-14) | ARC data | 5 · Nat |
| Fuel cells and electrolysers (µ Me P) | Polarization curves · 1D membrane models · — | 3D two-phase PEM with Butler–Volmer kinetics | `Flag`: water closures are empirical | Measured polarization curves | 6 · Nat |
| Corrosion and electroplating (µ Me P L) | Galvanic series, Faraday's law · — · — | Secondary and tertiary current distribution; Nernst–Planck in crevices | Polarization data in the same electrolyte; long horizons `Flag` (OOR-5) | Cathodic-protection cases; parallel-plate primary distribution | 5 · Nat |
| Gas-phase kinetics | Equilibrium · reactors and flames with Cantera [Cantera licence] · mechanism reduction | Finite-rate chemistry in CFD | Mechanism ranges enforced | Ignition delay | 6 · Wasm |
| Cure and crystallization kinetics (Me P) | — · Kamal–Sourour cure, crystallization kinetics · — | Cure–thermal–residual-stress coupling | DSC calibration range | DSC data | 3 · Nat |

#### Particles, molecules and multiscale

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Granular media (µ Me P) | Angle of repose, Janssen · — · — | GPU DEM with Hertz–Mindlin and rolling resistance; Project Chrono (BSD-3) reference [Project Chrono] | Parameters from repose and shear-cell tests | Beverloo hopper | 5 · Nat |
| Particle methods for large deformation (Me P L) | — | MLS-MPM, SPH, peridynamics | `Flag`: tensile instability, numerical fracture | Column collapse; Taylor bar | 5 · Nat |
| Molecular dynamics (N) | — · — · coarse-grained MD | Machine-learned potentials (MACE, MIT code); LAMMPS (GPL-2.0) as External Op | Potential valid only in its training chemistry; model licences checked [MACE] | Elastic constants | 6 · Ext |
| Multiscale coupling (N µ Me) | Rules of mixtures · — · surrogate laws | FE² (FLX); FFT RVE solvers; concurrent atomistic coupling | ℓ/L ≤ 0.1; RVE convergence checked | Hashin–Shtrikman bounds | 5 · Nat; Ext concurrent |

#### Plasma and radiation transport

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Gas discharge (µ Me) | Paschen law · global models · — | Drift-diffusion with local-field approximation | Paschen pd range; arcs `Flag` | Paschen curves | 6 · Nat |
| Kinetic plasma (µ Me P) | — | Particle-in-cell; WarpX (BSD-3-Clause-LBNL) as External Op [WarpX] | Debye length resolved | Two-stream growth rate | 7 · Ext |
| Magnetohydrodynamics (Me P L) | Hartmann flow · — · — | Entropy-stable DG as in Trixi.jl | Ideal or resistive declared | Orszag–Tang | 7 · Nat |
| Neutron and photon transport (µ Me P L) | Attenuation laws · — · — | Continuous-energy Monte Carlo; OpenMC (MIT) [OpenMC]; CAD geometry through DAGMC [DAGMC] | Data library recorded; criticality safety out of scope (OOS-2) | ICSBEP benchmarks [Briggs et al. 2003] | 7 · Ext |
| Shielding and dose (Me P L) | Point kernel with buildup · — · — | Monte Carlo transport; Geant4 [Geant4 licence] | Physics list and energy range declared | Slab attenuation | 6 · Ext |

#### Biomechanics and human factors

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Soft tissue (µ Me P) | — | Holzapfel–Gasser–Ogden; biphasic poroelasticity; FEBio (MIT) reference [FEBio] | `Flag` always; C4 only with V&V 40 | Confined compression | 7 · Nat |
| Implants (Me P) | Beam and plate formulas · — · — | Nonlinear FEM with bone–implant contact; plate bending fatigue to ASTM F382 [FDA ASTM F382] | Declared density–modulus relation | GP15 bone plate tests | 7 · Nat |
| Cardiovascular flow (Me P) | Poiseuille, Womersley · Windkessel · — | ALE fluid–structure interaction | `Flag`: patient boundary conditions dominate | FDA benchmark nozzle [Hariharan et al. 2011] | 7 · Nat |
| Musculoskeletal posture (P) | Anthropometric tables · — · — | Multibody with optimal control; OpenSim (Apache-2.0) reference [OpenSim] | Population and task within data | Motion-capture gait trials | 5 · Wasm |
| Human factors (P) | Reach envelopes, revised NIOSH lifting equation [Waters et al. 1994] · — · — | Digital humans from ANSUR II (6,068 subjects, 93 measures [ANSUR II]) | Multivariate percentiles, not single-measure | Fit and reach | 5 · Nat |
| Cloth and soft goods (Me P) | — | Shell or discrete elastic models with IPC contact (FLX, phase 5) | Fabric data from Kawabata-type tests [Kato Tech KES] | ISO 9073-9 drape coefficient [ISO 9073-9]; GP16 | 5 · Nat |

#### Manufacturing process physics

| Process (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Powder bed fusion (µ Me P) | Rosenthal source · — · inherent strain through supports, baseplate cut and stress relief (FLX) | Layer-agglomerated thermo-mechanics; melt-pool thermal-fluid with Marangoni and keyhole physics | Inherent strain and relaxation only for the calibrated machine, material, parameters and stress relief; melt pool `Flag` outside AM-Bench conditions | AM-Bench 2018, 2022, 2025 [NIST AM-Bench] | 2 inherent strain (13.4), 4 thermo-mechanical, 6 melt pool · Nat |
| Extrusion and resin printing (Me P) | Bead formulas · — · — | Thermal history with bond strength; vat cure depth | Interlayer strength from tests | AM-Bench | 2 · Nat |
| Injection moulding (Me P) | Flow-length ratios · Hele-Shaw filling (MFG) · — | Level-set fill; Cross–WLF, Tait pvT; ARD-RSC orientation [Phelps and Tucker 2009]; pvT-path stress with frozen layers and mould constraint; crystallization; post-ejection relaxation | Hele-Shaw only at h/L_flow ≤ 0.1, \|∇h\| ≤ 0.1 and 2h from gates, rib roots, steps and the flow front, else 3D at `SignOff`; 3D `Extrapolated` below eight cells across the half-thickness | GP5 short shots and warpage | 3 (13.4) · Nat |
| Casting (Me P L) | Chvorinov rule · — · — | VOF filling; Niyama porosity; hot-tearing indicators | Gate Weber number above breakup makes filling `Extrapolated` and indicators qualitative (OOR-8) | Chvorinov and Stefan solidification times | 6 (13.4) · Nat |
| Welding distortion (Me P L) | Shrinkage forces · — · inherent strain; joint loads on beam frames | Goldak source with solid-state phase transformation and thermo-elasto-plasticity | Inherent strains from coupons per joint type, thickness, process and heat input; transient source from macrographs | GP4 measured distortion | 2, 4 transient (13.4) · Nat |
| Machining and chatter (Me P) | Mechanistic cutting coefficients · — · — | Stability lobes from tool-tip FRFs; semi-discretization | Coefficients per tool, material and speed | Analytic lobes | 3 (13.4) · Nat |
| Stamping and springback (Me P L) | Bend allowance · — · one-step inverse | Incremental shell forming with Yld2000-2d and Yoshida–Uemori | Springback `Flag` without tension–compression data | NUMISHEET benchmarks [Green 2005] | 2 bend, 5 forming (13.4) · Nat |
| Heat treatment (Me P) | Jominy · — · — | JMAK and Koistinen–Marburger kinetics (13.4) with transformation plasticity; quench distortion and carburizing | TTT and CCT data required | Jominy data | 4 kinetics, 6 process · Nat |
| Composite draping and cure (Me P L) | Kinematic draping (MEC, phase 4) · — · — | Constitutive draping with shear locking; cure kinetics with process stress and spring-in | Shear below the measured locking angle; cure within DSC range | Picture-frame and bias-extension tests; spring-in coupons | 5 (13.4) · Nat |

#### MEMS and piezoelectrics

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Electrostatic actuation (µ Me) | Parallel-plate pull-in · spring–capacitor · macromodels | Monolithic electromechanical FEM; pull-in as a bifurcation | Bulk properties need features ≥ 1 µm | Pull-in analytic | 5 · Nat |
| Squeeze-film damping (µ) | Reynolds coefficients · — · — | Rarefaction-corrected Reynolds equation; DSMC in transitional gaps | Knudsen bounds as for rarefied gas | Analytic squeeze film | 5 · Nat |
| Piezoelectric devices (µ Me P) | Mason and BVD circuits · — · modal | Piezoelectric FEM with losses; axisymmetric transducers | Below the coercive field | Thickness-mode resonator | 5 · Nat |
| Thermal MEMS and anchor loss (µ) | Zener damping · — · — | Thermoelastic eigenanalysis; PML anchor loss | Q `Flag` without fabrication data | Zener analytic | 6 · Nat |

#### Civil structures and geomechanics

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Steel structures (P L) | Member checks (Eurocode 3, AISC 360-22 [AISC 360-22]) · frame analysis · — | Beams and shells with geometric nonlinearity; bolted connections; load combinations from a code package per edition | Code edition recorded | GP8 structural check | 5 · Nat |
| Timber structures (P L) | Member checks (Eurocode 5) [JRC Eurocode 5] · frame analysis · — | Beams, shells and orthotropic solids with moisture | Service class declared | GP14 | 7 · Nat |
| Structural fire resistance (P L) | Standard fire curve (ISO 834-1:2025 [ISO 834-1]) and parametric curves · — · — | Thermal analysis with charring (EN 1995-1-2) and temperature-dependent degradation | Prescribed exposure only; fire growth is OOR-14 | Charring depth | 7 · Nat |
| Reinforced concrete (Me P L) | Section design (Eurocode 2 [JRC Eurocode 2], ACI CODE-318-25 [ACI 318-25]) · frames · — | Concrete damage plasticity; smeared cracking | Nonlinear concrete `Flag` without calibration | Hand calculations to the cited code | 7 · Nat |
| Soil, foundations and soil–structure interaction (P L) | Bearing capacity, impedance functions · Winkler springs · — | Mohr–Coulomb, hardening soil, Cam-clay; Biot consolidation; absorbing boundaries | `Flag` always: site data govern | Terzaghi; footing impedance | 7 · Nat |
| Seismic analysis (P L) | Equivalent lateral force · response spectrum · — | Nonlinear time history with fibre beam-columns; OpenSees as reference only (commercial use needs permission [OpenSees copyright]) | Collapse `Flag` | PEER NGA-West2 records [PEER NGA-West2] | 7 · Nat |

#### Marine and offshore

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Hydrostatics and stability (P L) | Metacentric height · righting-lever curves · — | Exact hydrostatics over B-rep or Implicit hulls | Quasi-static; tank free surfaces declared | Box barge | 7 · Nat |
| Resistance and propulsion (P L) | Holtrop–Mennen [Holtrop and Mennen 1982] · open-water curves · — | RANS with VOF; body-force propellers | Froude and Reynolds range of the calibration | KCS [Tokyo 2015 workshop]; KVLCC2 [Larsson et al. 2014] | 7 · Nat |
| Seakeeping (P L) | Strip theory · — · response amplitude operators | Potential-flow BEM with Capytaine (Apache-2.0) reference [Capytaine]; Cummins equations | Linear waves; slamming `Flag` | Floating sphere | 7 · Nat |
| Mooring and risers (L) | Catenary · lumped-mass lines · — | Nonlinear rods with Morison loads | Morison coefficients from data | Catenary | 7 · Nat |
| Marine fatigue and slamming (P L) | Spectral fatigue · — · — | Wave-scatter hot-spot fatigue; VOF slamming | Slamming `Flag` always | Hot-spot examples of DNV-RP-C203 [DNV-RP-C203] | 7 · Nat |

#### Aerospace

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Low-speed aerodynamics and rotors (Me P L) | Thin airfoil · blade-element momentum with tip losses, vortex lattice, panels · — | Vortex particle method on fast multipole operations; rotating-frame RANS and DDES (FLX) | Panels attached flow only; each rotor rung within its advance-ratio and tip-Mach calibration | GP6 rotor thrust and torque | 4 · Nat, Wasm vortex particles |
| Transonic and supersonic (P L) | Shock-expansion · — · — | RANS and DG with shock capturing | Shock-induced separation `Flag` | ONERA M6, ATB | 6 · Nat |
| Hypersonics (P L) | Modified Newtonian · — · — | Nonequilibrium Navier–Stokes; DSMC where rarefied | `Flag` outside verified chemistry | Double cone [Harvey et al. 2001] | 7 · Ext |
| Aeroelasticity (P L) | Divergence formulas · — · doublet lattice with modal structure | p–k flutter; CFD aeroelasticity | Transonic dip needs CFD | AGARD wing 445.6 | 6 · Nat |
| Ice accretion (P L) | — · Messinger energy balance [Messinger 1953] · — | Droplet impingement, surface energy balance, geometry update | `Flag` always: roughness and shedding are empirical | Icing Research Tunnel shapes used to validate LEWICE [Wright 2005] | 6 · Nat |
| Spacecraft thermal (P L) | Equilibrium temperature · radiative node networks · — | Ray-traced solar, albedo and planetary infrared | Optical properties at a declared mission life | Flat plate | 6 · Nat |
| Launch environments (P L) | Miles' equation · — · — | The vibration and shock row with the launch provider's spectra; diffuse-field acoustic loading | Spectra from the launch provider | SDOF | 6 · Nat |
| Flight dynamics (P) | Stability derivatives · 6-DoF models · — | — | Table ranges `Refuse` | GP6 flight logs | 4 · Nat |

## State of the art

Targets run on contract 13.3's reference laptop or a named GPU, and copyleft leaders run only as External Ops. FLX's table covers the numerical methods; this one covers models, materials and credibility.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Validity and credibility | V&V 40 [ASME V&V 40], NASA-STD-7009B [NASA-STD-7009B], FDA guidance (2023) [FDA CM&S credibility]; V&V 10 [ASME V&V 10] and V&V 20 metrics | Hand-written credibility assessments; no incumbent evaluates envelopes on every result | Envelopes as checks; zone Fields; V&V 20 per response quantity with k from ν_eff | Target: a cited envelope on every std model before C2; three-replicate synthetic cases cover at their stated level |
| Static stress workflow | Immersed high-order FEM with goal-oriented error estimates | Ansys Mechanical with automated meshing and its Mesh Quality Worksheet [Ansys Mechanical] | No meshing or defeaturing step; bounded, zoned results | Target: time from STEP import to a decided stress check on the same 20 parts, against Ansys Mechanical including meshing |
| Code verification | Manufactured solutions; NAFEMS P18 [NAFEMS P18] | MSC Nastran's verification manual [NAFEMS Nastran verification] | Manufactured solutions for every std form; all of P18 | P18 within 1% [ESRD NAFEMS LE] |
| Planar and axisymmetric models | Axisymmetric elements with and without twist | Abaqus CAX and CGAX element families [Abaqus axisymmetric elements] | FLX's sections as ladder rungs below the 3D solid | Lamé cylinder exact; NAFEMS axisymmetric cases within 1% |
| Linear dynamics | Mode superposition with residual vectors; prestressed and gyroscopic eigenproblems | Ansys Mechanical's modal, harmonic, spectrum and random vibration analyses [Ansys Mechanical] | FLX's linear dynamics with COV's resonance and modal-coverage envelopes | NAFEMS R0016 within 1%; SDOF and two-DOF closed forms exact to 10⁻⁸ |
| Contact | Mortar contact; Incremental Potential Contact [IPC Toolkit] | IPC Toolkit (MIT) | Mortar; IPC from phase 5 (FLX) | NAFEMS R0094; Hertz peak within 1% |
| Fatigue | Multiaxial critical plane with probabilistic S–N; spectral methods for PSD loading | Ansys nCode DesignLife [Ansys nCode DesignLife] | Critical plane with basis-aware life distributions (OOR-11); Dirlik and narrow band | Target: 90% of held-out lives within a factor of 3 |
| Gear and bearing ratings | ISO 6336 and ISO 281 ratings with loaded tooth contact analysis | KISSsoft, rating to ISO, DIN, AGMA and VDI standards [KISSsoft gears] | Standard ratings plus tooth contact, mortar contact as validation | Worked examples to 3 significant figures |
| Fracture | Phase field, cohesive zones, calibrated ductile damage | Sandia Fracture Challenge entrants [Boyce et al. 2014] | Cohesive and phase-field defaults; ductile `Flag` | Sandia data; target: enter the next blind round |
| Composite failure | Building-block calibration of LaRC05 and Puck | Theories assessed in WWFE-II [Christensen WWFE-II] | Calibrated criteria library; progressive failure `Flag` | WWFE-II; GP10 pyramid |
| Turbulence models | SA, SST, GEKO and transition per NASA TMR [NASA TMR] | SU2 (LGPL-2.1) [SU2]; OpenFOAM (GPLv3) [OpenFOAM licence] | Native, on TMR definitions | Reference codes' finest-grid spread |
| Rotating machinery | Moving reference frames, mixing planes and sliding meshes | Ansys Fluent's MRF, mixing-plane and sliding-mesh models [Ansys Fluent moving zones] | FLX's rotating frames and interfaces with COV's turbomachinery envelopes | Target: fan P–Q curve within measurement uncertainty |
| Scale-resolving CFD | GPU high-order DG and flux reconstruction; non-equilibrium wall models [Agrawal et al. 2024] | PyFR (BSD) [PyFR]; Trixi.jl (MIT) [Trixi.jl] | Entropy-stable DG on Flux GPUs | 2DWMH; target: cost per DOF per stage within 1.5× of PyFR |
| Multiphase | VOF, level set, phase field; k_max·η_KH ≥ 60 [Hatashita et al. 2025] | Basilisk's geometric VOF (GPL-3.0) [Basilisk VOF] | Native, with a priori resolution | Interfacial statistics converge |
| Rarefied and free-molecular gas | DSMC; the angular coefficient method | SPARTA (GPL) [SPARTA]; COMSOL Molecular Flow Module [COMSOL Molecular Flow] | DSMC as External Op; native slip and angular coefficient | Microchannel analytic; Clausing factor |
| Particle tracing | Lorentz-force and drag-driven trajectories with space charge | COMSOL Particle Tracing Module [COMSOL Particle Tracing] | Native on Flux BVH queries | Child–Langmuir diode within 1% |
| Electromagnetics | Nédélec FEM with Newton on B–H; high-order FEM with model reduction | Palace (Apache-2.0) [Palace] | Native | TEAM 7 and 13 probes within 5% [Compumag TEAM]; eigenfrequencies within 0.1% of Palace |
| Optics | Differentiable spectral, polarized Monte Carlo transport | Mitsuba 3 [Mitsuba 3] | Native on Flux BVH operations | Target: equal-noise time within 2× of Mitsuba 3 |
| Batteries | DFN with thermal coupling; MSMR OCV [PyBaMM lithium-ion models] | PyBaMM (BSD-3) [PyBaMM] | Native ladder to DFN | Within 1 mV RMS of PyBaMM; target: 10× faster sweeps |
| Fibre orientation | Anisotropic rotary diffusion with reduced strain closure [Wang et al. 2008] | Autodesk Moldflow, on Folgar–Tucker [Moldflow fibre orientation] | ARD-RSC; Folgar–Tucker as L0 | GP5 short shots and warpage |
| Chemical kinetics | Detailed mechanisms in reactor networks and 1D flames | Cantera (BSD-3) [Cantera] | Wasm component reading Cantera's YAML mechanisms [Cantera input tutorial] | Target: equilibrium and ignition delay within 0.1% |
| Atomistic | Equivariant machine-learned potentials | MACE (MIT code; model licences vary) [MACE]; LAMMPS (GPLv2) [LAMMPS licence] | External Ops; results as provenance | Elastic constants within the model's published error |
| Plasma and radiation | Particle-in-cell (WarpX, 2022 Gordon Bell Prize [WarpX]); Monte Carlo transport | OpenMC [OpenMC]; Geant4 [Geant4 licence] | External Ops | Analytic cases; code-to-code |
| Biomechanics | Fibre-reinforced hyperelastic FE; musculoskeletal optimal control | FEBio (MIT) [FEBio]; OpenSim (Apache-2.0) [OpenSim] | Native FE; Wasm musculoskeletal models | Code-to-code with FEBio |
| Seakeeping | Potential-flow BEM with Cummins time domain | Capytaine (Apache-2.0) [Capytaine] | Native BEM on Flux fast multipole | Target: added mass and damping within 1% |
| Additive process | Inherent strain, part-scale thermo-mechanics, melt-pool CFD | AM-Bench blind-challenge entrants [NIST AM-Bench] | Native | AM-Bench quantities inside measurement uncertainty |
| Learned surrogates | Geometry-agnostic neural field predictors with conformal or ensemble uncertainty | Ansys SimAI, which always returns a result with a confidence level [Ansys SimAI]; Luminary, claiming under 2% error [Luminary] | `Preview` and `Interactive` only; `SignOff` needs a bound in the check's norm or a confirming solve | No false `SignOff` `Pass` in 10⁴ adversarial evaluations; their confidence indicators measured on the same held-out set |
| Constitutive authoring | Domain-specific languages generating integration code | MFront 5.2 (GPL with a linking exception, or CeCILL-A) [MFront] | Ingot behaviours with `local_solve`; MFront import as Wasm | Stress updates within 10⁻¹⁰ relative of MFront tests |
| Materials data | Data management with traceable tests | Ansys Granta MI [Ansys Granta MI] | Versioned records; licences in labels | ISO 10303-235 round trip [ISO 10303-235] |
| Allowables | One-sided tolerance limits per CMH-17 and MMPDS [MMPDS] | CMH17 STATS, which incorporates STAT17 [CMH17 STATS] | Native, normal and Weibull in phase 1 | Worked examples to 3 significant figures |

The parity table maps each workflow an incumbent's analyst relies on to the Crucible rows that close it (D-COV-32). Comparing documented features is not a benchmark of a commercial product.

| Capability | Incumbent and its documented feature | Crucible's capability row and phase | Ahead, Equal, Later or Out of scope |
| --- | --- | --- | --- |
| Linear static with idealizations | Ansys Mechanical exports rigid and deformable remote points as RBE2 and RBE3, bushings as CBUSH and point masses as CONM2 [Ansys Nastran export] | FLX analyst idealizations (1); COV idealization envelopes (1) | Ahead: the same idealizations, with a `Flag` where a rigid coupling stiffens a thin wall |
| Planar and axisymmetric models | Abaqus axisymmetric elements with and without twist, thermal, acoustic and piezoelectric variants [Abaqus axisymmetric elements] | FLX planar and axisymmetric models (1); COV ladder rungs (1) | Equal, with `SymmetryBroken` instead of a silent wrong answer |
| Symmetry and cyclic sectors | Ansys Mechanical symmetry, periodic and cyclic regions [Ansys Mechanical] | FLX symmetry and cyclic reductions (2) | Later: phase 2, by the parity floor |
| Prestressed modal | Ansys Mechanical "Modal (Pre-Stressed)" exported as SOL103 with STATSUB [Ansys Nastran export] | FLX linear dynamics (2); COV rotordynamics (2) | Later: phase 2; modal analysis itself is phase 1 |
| Harmonic, random and spectrum response | Ansys Mechanical modal, harmonic, spectrum response and random vibration [Ansys Mechanical] | FLX linear dynamics (2); COV vibration and shock (2) | Later: phase 2, then ahead through resonance envelopes |
| Stress linearization and pressure equipment | Ansys Mechanical linearized membrane, bending, peak and total stress along a path [Ansys linearized stress] | FLX stress linearization (2); COV pressure-equipment design by analysis (5) | Ahead from phase 5: membrane and bending stresses carry bounds |
| Rotating machinery CFD | Fluent MRF and mixing-plane models as steady approximations, and the sliding mesh model [Ansys Fluent moving zones] | FLX rotating frames (3 laminar, 4 RANS), sliding interfaces (4), mixing planes (5); COV turbomachinery envelopes | Later: phases 3 to 5 |
| Charged-particle and flow particle tracing | COMSOL Particle Tracing Module for ions, electrons and particles in fluid flow [COMSOL Particle Tracing] | COV charged-particle tracing and particle tracing in flows (5) | Later: phase 5, by the parity floor |
| Free-molecular flow | COMSOL Molecular Flow Module, the deterministic angular coefficient method [COMSOL Molecular Flow] | COV free-molecular flow (5) | Later: phase 5, by the parity floor |
| Phased arrays and periodic structures | HFSS unit cells with paired boundaries, Floquet ports and finite-array domain decomposition, as an Ansys channel partner describes [PADT HFSS arrays] | FLX Floquet ports, Bloch-periodic cells and finite arrays (5); COV RF row | Later: phase 5 |
| System fluid libraries | Simcenter Amesim hydraulic, pneumatic and thermal domains, with valves, pumps, heat exchangers and refrigerant loops [Simcenter Amesim domains] | ELX hydraulic and coolant libraries (4), two-phase and pneumatic (5); COV fluid-system envelopes | Later: phases 4 and 5 |
| Learned field surrogates | Ansys SimAI predicts 3D fields with a confidence level [Ansys SimAI]; Luminary physics models [Luminary] | FLX `Preview` geometry surrogates (2), surrogate prediction (4); COV surrogate envelopes | Ahead: a surrogate never decides `SignOff` alone, so it cannot pass a design on its own error |
| Fatigue post-processing | Ansys nCode DesignLife analysis settings [Ansys nCode DesignLife] | COV stress-life (1), multiaxial and PSD fatigue (2) | Equal in methods; ahead in basis-aware life distributions |
| Gear and bearing ratings | KISSsoft rating to ISO, DIN, AGMA and VDI [KISSsoft gears] | COV gear, bearing and shaft ratings (2) | Equal in standards; ahead through tooth contact validated against 3D contact |
| Fibre orientation | Moldflow's Folgar–Tucker-based orientation models [Moldflow fibre orientation] | MFG fibre orientation (3); COV short-fibre models (3) | Ahead: ARD-RSC with warpage measured on GP5 |
| Materials data management | Ansys Granta MI with 250,000+ reference materials [Ansys Granta MI] | COV Material records, data licences and connectors (1 to 6) | Ahead: licences travel with every derived result to every exit |

## Platform notes

- **Double precision on GPUs.** WGSL has no `f64`, makes `f16` an extension and lets implementations flush subnormals [W3C WGSL]. An Apple WebGPU engineer said Metal-based implementations would not offer `f64` [Maxfield 2022], so `F64Required` models stay off WebGPU.
- **Browser memory.** Wasm memory64 is not on every engine [WebAssembly features]. Browser sessions follow PLT's browser memory table (contract 9), and remote results are canonical.
- **Relaxed SIMD.** It ships in Chrome and Firefox and behind a flag in Safari. Its results vary by hardware, so `Portable` physics never uses it.
- **External Ops.** They run on Linux untrusted-evaluation workers, reached remotely from every client; air-gapped installs need a local Linux worker (contract 9).
- **Monte Carlo determinism.** Particle and transport methods draw from KLN's `OpCx::rng` streams, keyed without platform class, fidelity or names, and reduce in fixed order.
- **Zones and data.** Canonical zones are identical everywhere, and other platform classes report `NearBound` regions. Connectors fetch only at import time, so builds run air-gapped.

## Interfaces with other subsystems

| To | What | Types | Phase |
| --- | --- | --- | --- |
| FLX | Physics and constitutive models; envelopes and regime functions for `flux::validity_zones`; the model-to-class map; critical distances with their method; property scatter for solve inputs; the method logic non-variational methods run on Flux's general operations; the `flux-op-material` operation family, owned with FLX | `PhysicsModel`, `Material`, `ValidityEnvelope` | 1 |
| ING | `std::physics` and `std::materials`; record syntax needs; property reads as exact basis intervals for limits | Ingot packages, `Range<Q>` | 1 |
| KLN | Envelope and Material records as CAS inputs; calibration Ops; External Op keys; `DataLicence` values in the usage part; the model-form allowance catalogue that policy-package allowances cite; Material composition for compliance | `Op`, `Labels`, `Material` | 1 |
| AGT | Coverage map; limit records; envelopes; `ValidityError`s with escalations; the parity map | `api` Read and Inspect methods | 1 |
| UIX | Zone Fields with assumptions; model-form parts; basis citations; escalations | `Field<Body, ValidityZone>` | 1 |
| MEC | Materials; solid, contact, joint, fatigue, buckling and dynamics models; strut-strength and idealization envelopes; gear, bearing and shaft ratings; constitutive draping (13.4) | `Material`, `PhysicsModel` | 1; 2 (contact, joint and dynamics models; ratings); 5 (constitutive draping) |
| MFG | Process models and envelopes; state Fields; strut-scale Materials and tolerance limits from its calibration; phase-transformation kinetics; environmental records; gear, bearing and shaft ratings | `Field`, `ValidityEnvelope`, `EnvironmentalRecord` | 1; 2 (environmental records, ratings); 4 (phase-transformation kinetics) |
| ELX | Dielectric, copper, magnetic and cell Materials; electromagnetic, thermal, electrochemical and fluid-system envelopes, including refit LFP hysteresis; precision tiers | `PhysicsModel`, `Material` | 3 |
| ECO | Domain acceptance checks; semantics of `crucible:physics`, `crucible:material`, MatML and OpenFOAM cases | Package | 1 |
| PLT | Precision tiers per model; External Op worker needs | Model metadata | 1 |

## Oracles

Oracles live in the protected `oracles/cov/`; held-out validation Evidence records live in a store agents never see.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| COV-O-MAP-1 | Coverage map | Rows match package metadata; `Planned` rows never counted |
| COV-O-MAP-2 | Parity map | Every capability a workflow row lists exists as a capability row with a phase no later than the workflow's |
| COV-O-VER-1 | Manufactured solutions for every std weak form | Observed order within 0.1 of the declared order over three refinements, until the error falls below 10³ times round-off |
| COV-O-VER-2 | Model ladders | Adjacent rungs agree within the narrower rung's declared tolerance at every test point, planar and axisymmetric rungs included |
| COV-O-VER-3 | Credibility levels and minimum credibility | Only CI-signed results change levels; agent credentials cannot; models below the minimum give `Undecided` |
| COV-O-VER-4 | Discretization source | On the labelled corpus, no discretization part without an estimator or a convergence study decides a `SignOff` check |
| COV-O-ERR-1 | Input propagation | Mean and variance within 2% of a high-sample reference; epistemic inputs as probability boxes, never summed |
| COV-O-ERR-2 | Calibration classes | Every `Estimated` estimator of a std model names a class with entry and envelope; a removed entry or a result outside the envelope gives `Indicator` |
| COV-O-ERR-3 | Allowances | Labelled C2 cases give `Undecided { Unquantified([ModelForm]) }` without an allowance and a decided verdict with a pinned one, whose `ObjectId` appears in `CheckOutcome.allowances` and the check's key; unconfirmed or resistance-only entries never cover |
| COV-O-VAL-1 | Golden-product confirmation | Every gauge functional of every article lies within its prediction ± the total budget, in `Calibrated` zones; no article's data entered calibration or validation |
| COV-O-VAL-2 | Model form, zone geometry and inflation | On synthetic known-error cases, including three-replicate cases, bounds with k from ν_eff and g(d) cover at their stated level; zones exact; unvalidated quantities `NotQuantified`; beyond d_max `BeyondInflationFit`; calibration and validation data disjoint |
| COV-O-VAL-3 | Tool qualification kit | Every requirement traces to a passing oracle result of the release; known problems and impact notes per release |
| COV-O-ENV-1 | Envelope completeness | Every model has envelope, transforms, inflation with d_max, classes and precision tier; every bound a basis; every `Refuse` bound an escalation (exact) |
| COV-O-ENV-3 | Zones across platform classes | Canonical zones identical on golden models; others differ only inside `NearBound` bands |
| COV-O-ENV-4 | `Refuse` behaviour | Dependent checks blocked; `OutsideEnvelope` with fixes (exact) |
| COV-O-ENV-5 | Waivers and widening | Agents cannot create Waiver records or merge widenings; `Refuse` zones take no Waiver (exact) |
| COV-O-ENV-6 | Regime computability and missing inputs | Every variable resolves to a typed function; a missing input gives `Extrapolated` with a default, else `Unassessed` |
| COV-O-ENV-7 | Surrogate envelopes | Out-of-distribution queries `Extrapolated` or `Invalid`; CMA-ES with 10⁴ seeded evaluations per surrogate finds no surrogate `SignOff` `Pass` the full solve fails; no `Preview` surrogate decides a check |
| COV-O-ENV-8 | Coupling envelopes | One-way coupling `Invalid` on labelled flutter-prone, light-panel and heavy-fluid cases; valid on controls |
| COV-O-BENCH-1 | NAFEMS P18 LE, FV and T benchmarks | Within 1% of reference values |
| COV-O-BENCH-2 | NAFEMS R0024, R0027, R0094, R0020, R0031 and R0016; lattices; struts; idealizations | Published values within 2%, limit loads and lives within 5%; Hertz peak pressure within 1%; lattice tensors within 1% of full-resolution cells; labelled stocky struts decide by strength against single-strut compression coupons; a rigid coupling on a thin wall `Flag` |
| COV-O-BENCH-3 | NASA TMR and thermal-fluid references | Within the reference codes' finest-grid spread; analytic cases within 1%; fan and fluid-system cases inside measurement uncertainty |
| COV-O-BENCH-4 | TEAM 7, 13 and 36; optical and periodic references | Within published measurement uncertainty; infinite-array active reflection within 0.1 dB of the reference |
| COV-O-BENCH-5 | AM-Bench blind predictions and process references | Inside measurement uncertainty for at least 80% of entered quantities; analytic process cases and Jominy curves within 2% |
| COV-O-BENCH-6 | Battery ladder | SPM, SPMe and DFN within 5 mV at C/20; DFN within 1 mV RMS of PyBaMM; refit LFP hysteresis within 10 mV RMS of measured cycles |
| COV-O-BENCH-7 | Particle, kinetics, molecular, plasma and transport domains | Each row's State of the art target, else within 2% or three standard errors of the reference |
| COV-O-BENCH-8 | Free surface and multiphase | Dam-break front and bubble rise velocity within 2%; interfacial statistics converge; volume conserved to solver tolerance; particle tracing matches Stokes settling within 1% |
| COV-O-BENCH-9 | Constitutive draping and cure | Shear angles within 2° of frame and bias tests; degree of cure within 0.02 of DSC; spring-in within 0.2° |
| COV-O-BENCH-10 | Gear, bearing and shaft ratings | Standards' worked examples to 3 significant figures; tooth contact within 5% of mortar contact on GP3's root stress and transmission error |
| COV-O-BENCH-11 | Charged-particle tracing and free-molecular flow | Child–Langmuir diode current within 1%; Clausing factors of tubes within 1% of tabulated values |
| COV-O-BENCH-12 | Pressure-equipment design by analysis | The licensed code edition's worked examples reproduced to 3 significant figures |
| COV-O-BENCH-13 | Rotor aerodynamics | Blade-element momentum, vortex particle and RANS rungs agree within each rung's tolerance on GP6's propellers; GP6 dynamometer thrust and torque inside the budget |
| COV-O-BENCH-14 | Impact functionals | Channel filters match the SAE J211 response corridors; functionals converge under refinement on the Taylor bar; ensemble statistics stable to 5% between seed sets |
| COV-O-LIM-1 | Limit records | Every `NoCoveringModel` error cites a limit record; records change only through approved Proposals |
| COV-O-PKG-1 | External Op agreement and placement | Two hosts agree on output `ObjectId`s under signed receipts, else `Unverified`; never on trusted builders |
| COV-O-PKG-2 | Package acceptance | Seeded incomplete packages get the right typed error; std packages need two non-author reviewers |
| COV-O-PKG-3 | Precision tiers | No `F64Required` kernel in an `f32` or emulated-`f64` class; `F32Safe` residuals and estimators in CPU `f64` |
| COV-O-MAT-1 | Admissibility and tangents | Admissibility over each envelope (exact or 10⁻¹² relative); Taylor tests per FLX's tangent oracle |
| COV-O-MAT-2 | Units | Every property dimension-checks; affine temperatures handled (compile time) |
| COV-O-MAT-3 | Calibration recovery | Known parameters recovered from noisy synthetic data; 95% intervals cover within 2 points of nominal |
| COV-O-MAT-4 | Statistical basis and allowables | CMH-17 and MMPDS worked examples for normal and Weibull limits reproduced to 3 significant figures in phase 1; non-parametric and pooled examples in phase 3 |
| COV-O-MAT-5 | Licence propagation | Exporting embedded licensed values fails; derived results export where the terms allow (exact) |
| COV-O-MAT-6 | Property reads | A limit read decides at both ends of the basis interval and adds no budget part; a B-basis solve input carries α = 0.10 into the union bound; a specification limit in a solve is `NotQuantified` |
| COV-O-MAT-7 | Records, designations, certification, connectors | Lossless ISO 10303-235 round trip; "nearest" fails specification checks; no fetch in evaluation |
| COV-O-MAT-8 | Property Fields | Exact at tabulated nodes; monotone where declared; out-of-coverage reads zoned, never clamped |
| COV-O-MAT-9 | Environmental records | Every value carries source, boundary and year; carbon checks report them; mixed boundaries fail |
| COV-O-MAT-10 | UMAT ports | Stress updates within 10⁻¹⁰ relative of the original over the calibrated envelope; Taylor tests pass |
| COV-O-MAT-11 | Critical distances | Point, line, area and volume operators reproduce their analytic values on a notch field; a mismatched method fails with `CriticalDistanceMismatch` |

## Phasing

Shared phases follow contract 13.4, and each matrix row lists its own phase. Golden products 7 to 16 start only with a test partner and an approved plan (contract 13.1).

| Phase | COV's contribution to the gate |
| --- | --- |
| 0 | Envelope schema; regime variables with transforms; credibility levels; Material records and units; the coverage map; limit records |
| 1 | GP1 and GP2: immersed linear elasticity and the beam-lattice model at C3 from the separate-specimen validation campaign, confirmed by gauge functionals on the proof loads; FLX's six phase 1 calibration classes; the strut-strength check and buckling envelopes; strut-scale Materials with normal and Weibull basis values; planar and axisymmetric rungs; idealization envelopes; the allowance catalogue; the parity map |
| 2 | GP3 and GP4: gear, bearing and shaft ratings; vibration, shock and rotordynamics envelopes on FLX's linear dynamics; weld distortion from coupons at C3. Also inherent strain for metal powder bed fusion and environmental records with generic factors |
| 3 | GP5: moulding with the Hele-Shaw envelope, laminar conjugate heat transfer and drop functionals; warpage and drop models at C3. Also linear acoustics |
| 4 | GP6: rotor aerodynamics, motor and thermal models validated by flight, dynamometer and thermal tests. Also phase-transformation kinetics |
| 5 | GP7 MEMS, GP8 steel platform with the IFC structural check and pressure-equipment routes, GP9 crash box; particle tracing and free-molecular flow |
| 6 | GP10 wing box with the tool qualification kit, GP11 CubeSat, GP12 battery sub-pack |
| 7 | GP13 hull, GP14 timber pavilion, GP15 bone plate with its V&V 40 package, GP16 sewn pack |

## Open questions

1. **Strut waviness threshold.** The `Flag` value for strut waviness over radius of gyration comes from the first as-built calibration build (contract 13.4) and cannot be set before that build is measured.
2. **Sheet lattices in GP2.** If the phase 0 gate fixes GP2 with sheet cells, mid-surface shells for sheet lattices move to phase 1. The GP2 record in contract 13.1 decides it.
3. **Gear and bearing envelope limits.** The lambda-ratio and temperature limits come from each standard's scope, which needs the licensed editions (MEC's open question on standards content).

## Contract change requests

None.

## Sources

Licence statements reflect the pages as read and are not legal advice.

| Key | Title | URL | Date opened |
| --- | --- | --- | --- |
| [Abaqus axisymmetric elements] | Abaqus 2016 analysis user's guide, axisymmetric solid element library (University of Colorado mirror) | https://ceae-server.colorado.edu/v2016/books/usb/pt06ch28s01ael05.html | 2026-10-12 |
| [ACI 318-25] | ACI CODE-318-25, Building Code for Structural Concrete | https://www.concrete.org/store/productdetail.aspx?ItemID=318U25 | 2026-10 |
| [Agrawal et al. 2024] | Agrawal, Bose and Moin, non-equilibrium wall model for smooth-body separation (2024) | https://arxiv.org/abs/2407.11390 | 2026-10 |
| [AISC 360-22] | AISC, ANSI/AISC 360-22, Specification for Structural Steel Buildings | https://www.aisc.org/aisc/publications/current-standards/aisc-360/ | 2026-10 |
| [Alves et al. 2003] | Alves, Oliveira and Pinho, "Benchmark solutions for the flow of Oldroyd-B and PTT fluids in planar contractions", *J. Non-Newtonian Fluid Mech.* 110 (2003), Crossref record | https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Alves+Oliveira+Pinho+Benchmark+solutions+for+the+flow+of+Oldroyd-B+and+PTT+fluids+in+planar+contractions | 2026-10 |
| [ANSUR II] | ANSUR II | https://www.openlab.psu.edu/ansur2/ | 2026-10 |
| [Ansys Fluent moving zones] | Ansys Fluent 2024 R2 theory guide, flows with moving reference frames, mixing planes and sliding meshes | https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/flu_th/flu_th_sec_mzrrf.html | 2026-10-12 |
| [Ansys Granta MI] | Ansys Granta MI | https://ansys.synopsys.com/products/materials/granta-mi | 2026-10 |
| [Ansys linearized stress] | Ansys Mechanical 2024 R2 help, linearized stresses | https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_linearized_stresses.html | 2026-10-12 |
| [Ansys Mechanical] | Ansys Mechanical, product page | https://ansys.synopsys.com/products/structures/ansys-mechanical | 2026-10-12 |
| [Ansys Nastran export] | Ansys Mechanical 2024 R2 help, Nastran export supported features | https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_NASTRAN_export_supported_features.html | 2026-10-12 |
| [Ansys nCode DesignLife] | Ansys Help 2025 R1, nCode DesignLife analysis settings | https://ansyshelp.ansys.com/public/Views/Secured/corp/v251/en/mech_addon/ds_fatigue_designlife_settings.html | 2026-10 |
| [Ansys SimAI] | Ansys SimAI, product page | https://ansys.synopsys.com/products/simai | 2026-10-12 |
| [ASME V&V 10] | ASME V&V 10-2019 (R2025), *Standard for Verification and Validation in Computational Solid Mechanics* | https://www.asme.org/codes-standards/find-codes-standards/standard-for-verification-and-validation-in-computational-solid-mechanics | 2026-10 |
| [ASME V&V 20] | ASME V&V 20-2009 (R2021) | https://www.asme.org/codes-standards/find-codes-standards/standard-for-verification-and-validation-in-computational-fluid-dynamics-and-heat-transfer | 2026-10 |
| [ASME V&V 40] | ASME V&V 40-2018 | https://www.asme.org/codes-standards/find-codes-standards/assessing-credibility-of-computational-modeling-through-verification-and-validation-application-to-medical-devices | 2026-10 |
| [ASTM E8/E8M-25] | ASTM E8/E8M-25, tension testing of metallic materials, Crossref record | https://api.crossref.org/works/10.1520/E0008_E0008M-25 | 2026-10 |
| [Basilisk VOF] | Basilisk, geometric VOF (src/vof.h; GPL-3.0 in src/COPYING) | http://basilisk.fr/src/vof.h | 2026-10 |
| [Boyce et al. 2014] | Boyce et al., "The Sandia Fracture Challenge: blind round robin predictions of ductile tearing", *Int. J. Fracture* 186 (2014) | https://link.springer.com/article/10.1007/s10704-013-9904-6 | 2026-10 |
| [Brachet et al. 1983] | Brachet et al., "Small-scale structure of the Taylor–Green vortex", *J. Fluid Mech.* 130 (1983), Crossref record | https://api.crossref.org/works?query.bibliographic=Brachet+Small-scale+structure+of+the+Taylor-Green+vortex&rows=2&select=DOI,title,author,container-title,volume,page,issued | 2026-10 |
| [Brennen cavitation] | Brennen, *Cavitation and Bubble Dynamics*, chapter 2 (Rayleigh collapse time) | http://brennen.caltech.edu/HTMBUB/chap2.htm | 2026-10 |
| [Briggs et al. 2003] | Briggs, Scott and Nouri, "The International Criticality Safety Benchmark Evaluation Project", *Nucl. Sci. Eng.* 145 (2003), Crossref record | https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Briggs+Scott+Nouri+The+International+Criticality+Safety+Benchmark+Evaluation+Project+Nuclear+Science+and+Engineering | 2026-10 |
| [buildingSMART IFC] | buildingSMART, IFC schema specifications | https://technical.buildingsmart.org/standards/ifc/ifc-schema-specifications/ | 2026-10 |
| [CAMPUS] | CAMPUS, about | https://www.campusplastics.com/campus/about | 2026-10 |
| [Cantera] | Cantera | https://github.com/Cantera/cantera | 2026-10 |
| [Cantera input tutorial] | Cantera user guide, input file tutorial (YAML and ck2yaml) | https://cantera.org/stable/userguide/input-tutorial.html | 2026-10 |
| [Cantera licence] | Cantera licence | https://raw.githubusercontent.com/Cantera/cantera/main/License.txt | 2026-10 |
| [Capytaine] | Capytaine | https://github.com/capytaine/capytaine | 2026-10 |
| [CERN STEAM LEDET] | CERN STEAM framework, LEDET | https://steam.docs.cern.ch/tools/ledet/ | 2026-10 |
| [Christensen WWFE-II] | R. M. Christensen, critique of the World-Wide Failure Exercise II | https://failurecriteria.com/theworldwidefail.html | 2026-10 |
| [Circular Ecology ICE] | Circular Ecology, ICE database | https://circularecology.com/embodied-carbon-footprint-database.html | 2026-10 |
| [CMH-17] | CMH-17 | https://www.cmh17.org/ | 2026-10 |
| [CMH-17 software] | CMH-17, software | https://www.cmh17.org/RESOURCES/Software | 2026-10 |
| [CMH17 STATS] | CMH-17, CMH17 STATS statistics software | https://www.cmh17.org/RESOURCES/Statistics-Software | 2026-10 |
| [Compumag TEAM] | Compumag TEAM problems | https://www.compumag.org/wp/team/ | 2026-10 |
| [COMSOL Molecular Flow] | COMSOL, Molecular Flow Module | https://www.comsol.com/molecular-flow-module | 2026-10-12 |
| [COMSOL Particle Tracing] | COMSOL, Particle Tracing Module | https://www.comsol.com/particle-tracing-module | 2026-10-12 |
| [CoolProp] | CoolProp | https://github.com/CoolProp/CoolProp | 2026-10 |
| [DADiSP CFC module] | DADiSP, CFC filter module for SAE J211 channel frequency classes | https://www.dadisp.com/cfc1.htm | 2026-10-12 |
| [DAGMC] | DAGMC, direct accelerated geometry Monte Carlo | https://github.com/svalinn/DAGMC | 2026-10 |
| [DIN 743-1] | DIN Media, DIN 743-1:2012-12, calculation of load capacity of shafts and axles | https://www.dinmedia.de/en/standard/din-743-1/145165373 | 2026-10 |
| [DNV-RP-C203] | DNV-RP-C203, fatigue design of offshore steel structures | https://www.dnv.com/energy/standards-guidelines/dnv-rp-c203-fatigue-design-of-offshore-steel-structures/ | 2026-10 |
| [eCFR 14 CFR 25.613] | 14 CFR 25.613 | https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-25/subpart-D/subject-group-ECFR6bf0df4e8d5f12e/section-25.613 | 2026-10 |
| [ecoinvent licences] | ecoinvent licences | https://ecoinvent.org/offerings/licences/ | 2026-10 |
| [ESRD NAFEMS LE] | ESRD, benchmarks guide to the standard NAFEMS linear elastic tests | https://www.esrd.com/download/benchmarks-guide-standard-nafems-benchmarks-linear-elastic-tests-pdf/ | 2026-10 |
| [FAA AC 20-115D] | FAA, AC 20-115D, citing RTCA DO-330, Software Tool Qualification Considerations | https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/1032046 | 2026-10 |
| [FDA ASTM F382] | FDA recognized consensus standards, ASTM F382-24, metallic bone plates | https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards/detail.cfm?standard__identification_no=45857 | 2026-10 |
| [FDA CM&S credibility] | FDA, *Assessing the Credibility of Computational Modeling and Simulation in Medical Device Submissions* (November 2023) | https://www.fda.gov/regulatory-information/search-fda-guidance-documents/assessing-credibility-computational-modeling-and-simulation-medical-device-submissions | 2026-10 |
| [FEBio] | FEBio | https://github.com/febiosoftware/FEBio | 2026-10 |
| [FeenoX examples] | FeenoX mechanical examples (NAFEMS LE1, LE10, LE11) | https://www.seamplex.com/feenox/examples/mechanical.pdf | 2026-10 |
| [Finnie 1960] | Finnie, "Erosion of surfaces by solid particles", *Wear* 3 (1960), Crossref record | https://api.crossref.org/works?query.bibliographic=Finnie+Erosion+of+surfaces+by+solid+particles+Wear+1960&rows=3 | 2026-10 |
| [FKM guideline] | VDMA Verlag, FKM guideline, *Analytical Strength Assessment of Components*, 7th edition (2020) | https://www.vdmashop.de/en/fkm-guidelines/6/analytical-strength-assessment-for-engineering-components-7th-edition-2020?c=9 | 2026-10 |
| [Geant4 licence] | Geant4 software licence | https://geant4.web.cern.ch/download/license | 2026-10 |
| [Ghia et al. 1982] | Ghia, Ghia and Shin, "High-Re solutions for incompressible flow using the Navier-Stokes equations and a multigrid method", *J. Comput. Phys.* 48 (1982), Crossref record | https://api.crossref.org/works?query.bibliographic=Ghia+Shin+High-Re+solutions+incompressible+flow+Navier-Stokes+multigrid+1982&rows=3 | 2026-10 |
| [Granta MI Scripting Toolkit] | Ansys, Granta MI Scripting Toolkit for Python | https://developer.synopsys.com/docs/granta-mi-scripting-toolkit-40/welcome.md | 2026-10 |
| [Green 2005] | Green, "Description of Numisheet 2005 Benchmark #3", *AIP Conf. Proc.* 778 (2005), Crossref record | https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=NUMISHEET+2016+benchmark | 2026-10 |
| [Hamrock and Dowson 1977] | Hamrock and Dowson, "Isothermal elastohydrodynamic lubrication of point contacts, Part III: fully flooded results", *J. Lubrication Technology* 99 (1977), Crossref record | https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Hamrock+Dowson+Isothermal+elastohydrodynamic+lubrication+of+point+contacts+film+thickness | 2026-10 |
| [Hariharan et al. 2011] | Hariharan et al., "Multilaboratory particle image velocimetry analysis of the FDA benchmark nozzle model", *J. Biomech. Eng.* 133 (2011), Crossref record | https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Hariharan+Multilaboratory+particle+image+velocimetry+analysis+of+the+FDA+benchmark+nozzle+model | 2026-10 |
| [Harvey et al. 2001] | Harvey, Holden and Wadhams, "Code validation study of laminar shock/boundary layer and shock/shock interactions in hypersonic flow, Part B" (double cone), AIAA 2001-1031, Crossref record | https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Holden+Wadhams+Code+validation+study+of+laminar+shock%2Fboundary+layer+and+shock%2Fshock+interactions+in+hypersonic+flow+double+cone | 2026-10 |
| [Hatashita et al. 2025] | Hatashita, Nathan and Jain, "Scalings and simulation requirements in two-phase flows" (2025) | https://arxiv.org/abs/2510.07727 | 2026-10 |
| [Hobbacher and Baumgartner 2024] | Hobbacher and Baumgartner, *Recommendations for Fatigue Design of Welded Joints and Components*, 3rd edition, IIW Collection (Springer, 2024) | https://link.springer.com/content/pdf/bfm:978-3-031-57667-6/1 | 2026-10 |
| [Holtrop and Mennen 1982] | Holtrop and Mennen, "An approximate power prediction method", *International Shipbuilding Progress* 29 (1982), Crossref record | https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Holtrop+Mennen+An+approximate+power+prediction+method | 2026-10 |
| [Hysing et al. 2009] | Hysing et al., "Quantitative benchmark computations of two-dimensional bubble dynamics", *Int. J. Numer. Meth. Fluids* 60 (2009), Crossref record | https://api.crossref.org/works?query.bibliographic=Hysing+Quantitative+benchmark+computations+of+two-dimensional+bubble+dynamics&rows=3 | 2026-10 |
| [IPC Toolkit] | IPC Toolkit | https://github.com/ipc-sim/ipc-toolkit | 2026-10 |
| [IPC Toolkit tutorial] | IPC Toolkit, getting started (barrier distance and friction smoothing) | https://ipctk.xyz/tutorials/getting_started.html | 2026-10 |
| [ISO 10303-235] | ISO 10303-235:2019 | https://www.iso.org/standard/74409.html | 2026-10 |
| [ISO 16281] | ISO 16281:2025, rolling bearings: modified reference rating life for universally loaded bearings | https://www.iso.org/standard/80221.html | 2026-10 |
| [ISO 281] | ISO 281:2007, rolling bearings: dynamic load ratings and rating life | https://www.iso.org/standard/38102.html | 2026-10 |
| [ISO 6336-1] | ISO 6336-1:2019, calculation of load capacity of spur and helical gears (parts 2, 3 and 6 are also 2019 editions) | https://www.iso.org/standard/63819.html | 2026-10 |
| [ISO 834-1] | ISO 834-1:2025, fire-resistance tests: general requirements | https://www.iso.org/standard/83943.html | 2026-10 |
| [ISO 9073-9] | ISO 9073-9:2008, nonwovens: drapability including drape coefficient | https://www.iso.org/standard/41375.html | 2026-10 |
| [ISO/TR 6336-30] | ISO/TR 6336-30:2022, calculation examples for ISO 6336 parts 1, 2, 3 and 5 | https://www.iso.org/standard/84147.html | 2026-10 |
| [JRC Eurocode 2] | European Commission JRC, Eurocode 2 parts | https://eurocodes.jrc.ec.europa.eu/EN-Eurocodes/eurocode-2-design-concrete-structures | 2026-10 |
| [JRC Eurocode 3] | European Commission JRC, Eurocode 3 parts, including EN 1993-1-9 fatigue | https://eurocodes.jrc.ec.europa.eu/EN-Eurocodes/eurocode-3-design-steel-structures | 2026-10 |
| [JRC Eurocode 5] | European Commission JRC, Eurocode 5 parts, including EN 1995-1-2:2004 structural fire design | https://eurocodes.jrc.ec.europa.eu/EN-Eurocodes/eurocode-5-design-timber-structures | 2026-10 |
| [Kato Tech KES] | Kato Tech, Kawabata Evaluation System (KES) texture measurement | https://english.keskato.co.jp/texture-measurement | 2026-10 |
| [KISSsoft gears] | KISSsoft, gears module | https://www.kisssoft.com/en/products/products/modules/gears | 2026-10 |
| [LAMMPS licence] | LAMMPS open-source licence | https://docs.lammps.org/Intro_opensource.html | 2026-10 |
| [Larsson et al. 2014] | Larsson, Stern and Visonneau (eds.), *Numerical Ship Hydrodynamics: an assessment of the Gothenburg 2010 Workshop* (Springer, 2014), including KVLCC2, Crossref record | https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Numerical+Ship+Hydrodynamics+An+assessment+of+the+Gothenburg+2010+Workshop+Larsson+Stern+Visonneau | 2026-10 |
| [LII 14 CFR 25.613] | 14 CFR 25.613, material strength properties and design values (Cornell LII) | https://www.law.cornell.edu/cfr/text/14/25.613 | 2026-10 |
| [Luminary] | Luminary Cloud, home page | https://luminary.ai/ | 2026-10-12 |
| [MACE] | MACE | https://github.com/ACEsuit/mace | 2026-10 |
| [Martin and Moyce 1952] | Martin and Moyce, "An experimental study of the collapse of liquid columns on a rigid horizontal plane", *Phil. Trans. R. Soc. A* 244 (1952), Crossref record | https://api.crossref.org/works?query.bibliographic=Martin+Moyce+collapse+of+liquid+columns+on+a+rigid+horizontal+plane&rows=3 | 2026-10 |
| [Materials Project terms] | Materials Project terms of use (legacy site) | https://legacy.materialsproject.org/terms | 2026-10 |
| [MatWeb terms] | MatWeb terms of use | https://www.matweb.com/reference/terms.aspx | 2026-10 |
| [Maxfield 2022] | M. Maxfield, public-gpu mailing list on f64 in WebGPU (April 2022) | https://lists.w3.org/Archives/Public/public-gpu/2022Apr/0006.html | 2026-10 |
| [Messinger 1953] | Messinger, "Equilibrium temperature of an unheated icing surface as a function of air speed", *J. Aeronautical Sciences* 20 (1953), Crossref record | https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Messinger+Equilibrium+temperature+of+an+unheated+icing+surface+as+a+function+of+air+speed | 2026-10 |
| [MFront] | MFront and TFEL | https://thelfer.github.io/tfel/web/index.html | 2026-10 |
| [Mitsuba 3] | Mitsuba 3 | https://github.com/mitsuba-renderer/mitsuba3 | 2026-10 |
| [MMPDS] | MMPDS | https://www.mmpds.org/ | 2026-10 |
| [MMPDS order form] | Battelle, MMPDS order form (2023) | https://www.mmpds.org/wp-content/uploads/2023/07/Order-Form_2023_FINAL.pdf | 2026-10 |
| [Moldflow fibre orientation] | Autodesk Moldflow Insight 2025 help, fiber orientation models | https://help.autodesk.com/cloudhelp/2025/ENU/MoldflowInsight-CLC-Analyses/files/analysis-sequences/Fiber-orientation-analysis/MoldflowInsight_CLC_Analyses_analysis_sequences_Fiber_orientation_analysis_Moldflow_s_fiber_orientation_html.html | 2026-10 |
| [MPMA catalogue] | Motion + Power Manufacturers Alliance, publications catalogue (ANSI/AGMA 2101-E25) | https://motionpower.org/wp-content/uploads/2026/06/MPMA_Publications_Catalog.pdf | 2026-10 |
| [NAFEMS Nastran verification] | NAFEMS code verification, MSC Nastran benchmark sets | https://nafems.org/publications/code-verification/nastran-code-verification | 2026-10 |
| [NAFEMS P18] | NAFEMS, *The Standard NAFEMS Benchmarks* (P18) | https://www.nafems.org/publications/resource_center/p18/ | 2026-10 |
| [NASA TMR] | NASA Turbulence Modeling Resource, verification and validation cases and model list | https://tmbwg.github.io/turbmodels/ | 2026-10 |
| [NASA-STD-7009B] | NASA-STD-7009B | https://standards.nasa.gov/standard/NASA/NASA-STD-7009 | 2026-10 |
| [NIST AM-Bench] | NIST AM-Bench | https://www.nist.gov/ambench | 2026-10 |
| [NIST SRD] | NIST Standard Reference Data | https://www.nist.gov/srd | 2026-10 |
| [NIST SRD law] | NIST, Standard Reference Data: public law | https://www.nist.gov/srd/public-law | 2026-10 |
| [OpenFOAM licence] | OpenFOAM licence | https://openfoam.org/licence/ | 2026-10 |
| [OpenMC] | OpenMC | https://github.com/openmc-dev/openmc | 2026-10 |
| [OpenRadioss] | OpenRadioss | https://github.com/OpenRadioss/OpenRadioss | 2026-10 |
| [OpenROAD] | OpenROAD | https://github.com/The-OpenROAD-Project/OpenROAD | 2026-10 |
| [OpenSees copyright] | OpenSees copyright | https://opensees.berkeley.edu/OpenSees/copyright.php | 2026-10 |
| [OpenSim] | OpenSim | https://github.com/opensim-org/opensim-core | 2026-10 |
| [PADT HFSS arrays] | PADT, efficient and accurate simulation of antenna arrays in HFSS | https://www.padtinc.com/blog/efficient-and-accurate-simulation-of-antenna-arrays-in-hfss/ | 2026-10-12 |
| [Palace] | Palace | https://github.com/awslabs/palace | 2026-10 |
| [PEER NGA-West2] | PEER Ground Motion Database, NGA-West2 | https://ngawest2.berkeley.edu/ | 2026-10 |
| [Phelps and Tucker 2009] | Phelps and Tucker, "An anisotropic rotary diffusion model for fiber orientation in short- and long-fiber thermoplastics", *J. Non-Newtonian Fluid Mech.* 156 (2009), Crossref record | https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Phelps+Tucker+An+anisotropic+rotary+diffusion+model+for+fiber+orientation+in+short-+and+long-fiber+thermoplastics | 2026-10 |
| [Project Chrono] | Project Chrono | https://github.com/projectchrono/chrono | 2026-10 |
| [PyBaMM] | PyBaMM | https://github.com/pybamm-team/PyBaMM | 2026-10 |
| [PyBaMM lithium-ion models] | PyBaMM documentation, lithium-ion models (SPM, SPMe, DFN, MSMR) | https://docs.pybamm.org/en/latest/source/api/models/lithium_ion/index.html | 2026-10 |
| [PyBaMM model options] | PyBaMM documentation, battery model options (lumped, x-lumped and x-full thermal) | https://docs.pybamm.org/en/latest/source/api/models/base_models/base_battery_model.html | 2026-10 |
| [PyBaMM OCP submodels] | PyBaMM documentation, open-circuit potential submodels (including one-state hysteresis) | https://docs.pybamm.org/en/latest/source/api/models/submodels/interface/open_circuit_potential/index.html | 2026-10 |
| [PyBaMM one-state hysteresis] | PyBaMM documentation, one-state hysteresis open-circuit potential | https://docs.pybamm.org/en/latest/source/api/models/submodels/interface/open_circuit_potential/one_state_hysteresis_ocp.html | 2026-10 |
| [PyBaMM particle mechanics] | PyBaMM documentation, particle mechanics submodels (swelling, crack propagation) | https://docs.pybamm.org/en/latest/source/api/models/submodels/particle_mechanics/index.html | 2026-10 |
| [PyBaMM swelling] | PyBaMM documentation, swelling-only particle mechanics (Ai et al., J. Electrochem. Soc. 167, 013512) | https://docs.pybamm.org/en/latest/source/api/models/submodels/particle_mechanics/swelling_only.html | 2026-10 |
| [pycalphad] | pycalphad | https://github.com/pycalphad/pycalphad | 2026-10 |
| [PyFR] | PyFR | https://github.com/PyFR/PyFR | 2026-10 |
| [Rayleigh 1917] | Rayleigh, "On the pressure developed in a liquid during the collapse of a spherical cavity", *Phil. Mag.* 34 (1917), Crossref record | https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Rayleigh+On+the+pressure+developed+in+a+liquid+during+the+collapse+of+a+spherical+cavity | 2026-10 |
| [Risch and Kostyk 2012] | Risch and Kostyk, "Test case baseline results", 5th Ablation Workshop (2012), NTRS record | https://ntrs.nasa.gov/api/citations/20120011414 | 2026-10 |
| [Robinson et al. 1998] | Robinson et al., "Analytical formulation for the shielding effectiveness of enclosures with apertures", *IEEE Trans. EMC* 40 (1998), Crossref record | https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Robinson+Analytical+formulation+for+the+shielding+effectiveness+of+enclosures+with+apertures | 2026-10 |
| [Simcenter Amesim domains] | Siemens Simcenter blog, many physical domains in one system simulation tool (Amesim) | https://blogs.sw.siemens.com/simcenter/many-physical-domains-and-applications-in-one-system-simulation-tool/ | 2026-10-12 |
| [Slotnick et al. 2014] | Slotnick et al., *CFD Vision 2030 Study*, NASA/CR-2014-218178 | https://ntrs.nasa.gov/citations/20140003093 | 2026-10 |
| [SPARTA] | SPARTA | https://sparta.github.io/ | 2026-10 |
| [SU2] | SU2 | https://github.com/su2code/SU2 | 2026-10 |
| [Sulzer et al. 2021] | Sulzer et al., "Python Battery Mathematical Modelling (PyBaMM)", *J. Open Research Software* 9 (2021) | https://openresearchsoftware.metajnl.com/articles/10.5334/jors.309 | 2026-10 |
| [Taylor 2008] | Taylor, "The theory of critical distances", *Engineering Fracture Mechanics* 75 (2008), Crossref record | https://api.crossref.org/works/10.1016/j.engfracmech.2007.04.007 | 2026-10-12 |
| [TFEL GPL licence] | TFEL/MFront, GNU GPL licence text with the linking exception | https://raw.githubusercontent.com/thelfer/tfel/master/LICENCE-GNU-GPL | 2026-10 |
| [TNF piloted flames] | TNF Workshop, Sandia/TUD piloted CH4/air jet flames data archive | https://tnfworkshop.org/data-archives/pilotedjet/ch4-air/ | 2026-10 |
| [Tokyo 2015 workshop] | Tokyo 2015 Workshop on CFD in Ship Hydrodynamics (KCS, JBC, ONRT) | https://t2015.nmri.go.jp/ | 2026-10 |
| [Trixi.jl] | Trixi.jl | https://github.com/trixi-framework/Trixi.jl | 2026-10 |
| [Turek and Hron 2006] | Turek and Hron, "Proposal for numerical benchmarking of fluid-structure interaction between an elastic object and laminar incompressible flow", in *Fluid-Structure Interaction*, LNCSE (Springer, 2006), Crossref record | https://api.crossref.org/works/10.1007/3-540-34596-5_15 | 2026-10 |
| [UL Prospector terms] | UL Solutions, Prospector and Product iQ service terms | https://ul.com/resources/prospectorproduct-iq-service-terms | 2026-10 |
| [VDI 2230-1] | DIN Media, VDI 2230 Blatt 1:2015-11, systematic calculation of highly stressed bolted joints | https://www.dinmedia.de/en/technical-rule/vdi-2230-blatt-1/242566299 | 2026-10 |
| [VMAP] | VMAP Standards Community | https://www.vmap-standard.org/ | 2026-10 |
| [W3C WGSL] | W3C, WebGPU Shading Language | https://www.w3.org/TR/WGSL/ | 2026-10 |
| [Wang et al. 2008] | Wang, O'Gara and Tucker, "An objective model for slow orientation kinetics in concentrated fiber suspensions", *J. Rheol.* 52 (2008), Crossref record | https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Wang+O%27Gara+Tucker+An+objective+model+for+slow+orientation+kinetics+in+concentrated+fiber+suspensions | 2026-10 |
| [WarpX] | WarpX | https://github.com/BLAST-WarpX/warpx | 2026-10 |
| [Waters et al. 1994] | Waters et al., *Applications Manual for the Revised NIOSH Lifting Equation*, DHHS (NIOSH) 94-110 (CDC Stacks) | https://stacks.cdc.gov/view/cdc/5434 | 2026-10 |
| [WebAssembly features] | WebAssembly feature status data | https://raw.githubusercontent.com/WebAssembly/website/main/features.json | 2026-10 |
| [WebGPU CTS floating point] | WebGPU conformance test suite, floating-point primer | https://kdab.searchfox.org/firefox-main/source/dom/webgpu/tests/cts/checkout/docs/fp_primer.md | 2026-10 |
| [Wright 2005] | Wright, *Validation Results for LEWICE 3.0*, NASA/CR-2005-213561, NTRS record | https://ntrs.nasa.gov/api/citations/20050160961 | 2026-10 |
| [XLB] | XLB | https://github.com/Autodesk/XLB | 2026-10 |
| [Yang and Griffin 2020] | Yang and Griffin, "Grid-point and time-step requirements for direct numerical simulation and large-eddy simulation" | https://arxiv.org/abs/2010.15307 | 2026-10 |
| [Yates 1987] | Yates, *AGARD Standard Aeroelastic Configurations for Dynamic Response I: Wing 445.6*, NASA-TM-100492 (1987), NTRS record | https://ntrs.nasa.gov/api/citations/search?q=AGARD+standard+aeroelastic+configurations+dynamic+response+445.6+wing | 2026-10 |
