# Physics coverage and materials (COV)

Crucible covers physics through versioned physics packages whose models declare a model level, an evidence level and a `ValidityEnvelope` as data. Every result carries a validity-zone Field and an `ErrorBudget` whose model-form part comes from validation, and every gap is a named record. Materials are versioned records of property Fields over state domains, with statistical basis, typed uncertainty, provenance and a `DataLicence` that travels in the label lattice.

## Coverage model

Three rules make "anything physical" as true as it can honestly be. Every model says where it is valid, and every result says how wrong it may be and why. Every gap has a name, a reason and a recommended alternative.

A physics package is a Package that exports `PhysicsModel` and `ConstitutiveModel` records; std ships them in `std::physics` and `std::materials`. A `PhysicsModel` names its implementation, required properties, outputs, levels, envelope, calibration classes and precision class.

**Decision D-COV-1:** Physics coverage is delivered only as physics packages that use public mechanisms, and the coverage map is generated from package metadata. Each row shows `Planned (phase n)` until a package backs it, then its evidence level; planned rows never count as coverage. *Why:* principle 1 forbids privileged physics, and agents read an unbacked row as an existing capability (R1-32). *Rejected:* an in-app solver catalogue (privileged and unverifiable); a hand-written list (drifts from reality); planned domains without a status. (revised in round 2)

### Model levels

| Level | Form and typical cost | Error statement | Examples |
| --- | --- | --- | --- |
| L0 Analytic | Closed form, handbook or standard method; microseconds | Method assumptions plus model form | Beam formulas, Nusselt correlations, ISO 6336 gear ratings, Paschen breakdown |
| L1 System | Lumped or 1D Networks solved as DAEs, with FMI 3.0.2 export; milliseconds to seconds | As L0, plus Network discretization | Thermal RC networks, battery equivalent circuits, blade-element rotors |
| L2 Reduced | Projection (modal, Craig–Bampton, Krylov, POD) or surrogates; milliseconds online | Estimator, or marginal surrogate coverage (D-COV-7) | Modal superposition, inherent strain, SPMe |
| L3 Full 3D | FEM, IGA, DG, finite volume, BEM or particles through Flux; seconds to hours | Flux estimators plus model form | Nonlinear contact, LES, full-wave electromagnetics |

The model level chooses the model form and the `Fidelity` chooses discretization accuracy; both enter result provenance.

**Decision D-COV-2:** Each domain publishes a model ladder (L0 to L3), and adjacent rungs carry a consistency oracle inside the narrower envelope. *Why:* agreeing forms, such as Euler–Bernoulli and a 3D solid within 1% at L/h ≥ 20 (target), catch errors single-model benchmarks miss. *Rejected:* verifying each level only in isolation; calling the rungs "fidelity levels", which collides with the three `Fidelity` names. (revised in round 2)

### Evidence levels

| Level | Meaning | Required results | Allowed use |
| --- | --- | --- | --- |
| E0 Declared | Implemented, not verified | None | Experiments; never decides `SignOff` |
| E1 Verified | Code verification passed | Manufactured solutions, conservation, derivatives, determinism | `Preview` and `Interactive` |
| E2 Benchmarked | E1 plus community benchmarks | NAFEMS, NASA TMR or TEAM values within stated tolerance | `SignOff` in the literature-documented zone, `conditional_on: [ModelForm]` (D-COV-4) |
| E3 Validated | E2 plus held-out physical validation | ASME V&V 10 for solids [S65], V&V 20 otherwise [S7]; contract 13.1 replicates | Release gates, for validated response-quantity classes |
| E4 Context-qualified | E3 plus a credibility package for a named context of use | ASME V&V 40 [S8], NASA-STD-7009 [S9] or FDA guidance [S10] | Regulated submissions; the authority decides |

**Decision D-COV-3:** `std` physics decides `SignOff` checks only at E2 or above, and only CI-signed oracle results raise a level. Physical tests at a golden-product gate raise a model to E3 for the response-quantity classes their plan lists. *Why:* V&V 40 ties credibility to a decision's reliance on the model [S8], and gauged proof loads replace allowances with measured model form (R7-04). *Rejected:* a single "validated" flag; agent-assigned levels (principle 6); E3 resting on one unreplicated article. (revised in round 3)

An E2 model's calibrated zone is the validation domain its cited literature documents, confirmed by a named human reviewer (R1-30); bounds without one start Extrapolated.

**Decision D-COV-21:** Each result carries a solution-verification status beside its model's evidence level: `Estimator`, `Gci` or `None`. `Gci` is a grid-convergence band from FLX's `std::sim::solution_verification`, calibrated as its own class, and `None` makes the discretization part `Indicator`. *Why:* code verification proves a method, not one result (R1-28), and an uncalibrated band means something different from an η99 bound (R7-21). *Rejected:* folding solution verification into the E levels, which describe models rather than results. (revised in round 3)

### Error budgets and model form

Each `ErrorBudget` source has one producer (contract 5): Flux fills the numerical parts and `reduction or surrogate`, shell and beam reduction included (D-FLX-26). COV supplies the Material uncertainty that Flux propagates into the input part, and fills the model-form part from validation of the 3D physics and constitutive model.

| Evidence level, zone and quantity | Model-form part |
| --- | --- |
| E3 or E4, Calibrated, validated class | `Estimated`: \|E\| + k·u_val at the nearest validation points (contract 13.1) |
| E3 or E4, Extrapolated, validated class | The Calibrated bound times g(d) (D-COV-25) |
| E3 or E4, class not validated | `NotQuantified { reason: UnvalidatedQuantity }` |
| E2, any zone | `NotQuantified { reason: NoValidationData }` |
| Invalid or Unassessed | Not reached: dependent checks return `Error(Failure)` |

**Decision D-COV-20:** Model-form error is the V&V 20 metric at validation points, `Estimated` with coverage factor k, for the response-quantity classes the plan lists. Flux's bound B enters u_val as B/√3 when `Guaranteed` and B/z₁₋α/₂ when `Estimated` at level α. *Why:* V&V 20 quantifies accuracy only at validation points and for the quantities measured [S7], so gauge strains bound nothing about a peak elsewhere (R7-10). *Rejected:* transferring one validated bound to every check; carrying it unchanged into extrapolation. (revised in round 3)

**Decision D-COV-4:** An unquantified part is shown as "not quantified", never as zero, and a check whose margin lies inside the quantified budget is `Undecided`. A check resting on one is `Pass { conditional_on }`, meeting a gate only when a cited policy allowance covers each listed part (contract 5). *Why:* a design-code factor that the code states covers model uncertainty is the honest route for E2 models (R1-03). *Rejected:* round 1's `unquantified` tag, which treats the missing term as zero; refusing every E2 result. (revised in round 2)

**Decision D-COV-24:** Model-form allowances cite only std catalogue entries that two non-author domain reviewers confirmed. Each entry records code, edition, clause, factor, scope and covered uncertainty, action effect or resistance; only action-effect entries cover finite-element analysis. *Why:* a resistance factor covers the capacity formula, not the analysis that computed the load effect (R7-04). *Rejected:* free-text citations; treating every partial factor as covering every model.

`Estimated` discretization bounds arrive multiplied by their class's η99 at exceedance level α = 0.01 (D-FLX-24), and α joins the budget's union bound (contract 5). A `SignOff` `Pass` on such a bound also needs FLX's one-refinement confirmation, else `Undecided { reason: CalibrationUnconfirmed }` (contract 7.1).

**Decision D-COV-17:** Every `PhysicsModel` names the calibration class of each `Estimated` estimator it uses, with the class's η99 entry and envelope pinned in `ingot.lock`. Membership is computed from features FLX lists (degree, cut fraction, distance to singular sets); a result outside the envelope, or without an entry, reports `Indicator`. *Why:* only the author knows which estimator a model needs (R1-07), but a label cannot show that a result belongs to the sampled population (R7-01). *Rejected:* one class per numerical method; author-assigned membership. (revised in round 3)

Phase 1 needs FLX's four classes (FLX "Calibrated estimates"), each with 300 held-out samples: `elasticity.peak` and `elasticity.eigen` for immersed linear elasticity at p = 2 to 6, and `lattice.strut_stress` and `lattice.buckling` for the beam lattice's strut stresses and buckling factors.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Coverage map | Generated from package metadata by domain, scale, level and status; `api` Read methods | Unbacked cells show `Planned (phase n)` and the nearest packages, outside counts | COV-O-MAP-1 | 0 |
| Model ladders | Adjacent rungs consistent inside the narrower envelope | Disagreement blocks the higher rung's level | COV-O-VER-2 | 1 |
| Evidence levels | E0 to E4, raised only by CI-signed results; E3 per validated class | Unsigned or agent-set levels rejected | COV-O-VER-3 | 0 |
| Solution-verification status | `Estimator`, calibrated `Gci` or `None` | `None` keeps discretization `Indicator` | COV-O-VER-4 | 1, 3 (`Gci`) |
| Model-form part | V&V 20 metric per validated class; u_num from Flux bounds; g(d) | `NotQuantified` with `NoValidationData` or `UnvalidatedQuantity` | COV-O-VAL-2 | 1 |
| Input part | Material uncertainty through `std::uq` | `NotQuantified { MissingUncertainty }` | COV-O-ERR-1 | 2, 3 epistemic |
| Calibration classes | Model-to-class map; pinned η99 entries and class envelopes | No entry, or outside the envelope: `Indicator` | COV-O-ERR-2 | 1 |
| Conditional passes and allowances | `Pass { conditional_on }`; allowances from catalogue entries (D-COV-24) | `Undecided { reason: Unquantified(components) }` | COV-O-ERR-3 | 1 |

## Validity envelopes as data

### Data model

A `ValidityEnvelope` is a content-addressed record versioned with its model: regime bounds, scale limits, assumptions that cannot be computed, and the evidence behind each zone. COV owns the records and zone semantics; Flux evaluates them with `flux::validity_zones` (FLX "Verification, validity and agreement").

```rust
pub struct ValidityEnvelope {
    pub model: ModelRef,                 // PhysicsModel or ConstitutiveModel, id@version
    pub bounds: Vec<RegimeBound>,
    pub validation: Option<PointSet>,    // validation points; None at E2 (D-COV-25)
    pub validated: Vec<ResponseClass>,   // (quantity, location type, regime), contract 5
    pub length_scale: ScaleRange,        // e.g. continuum valid above 1 µm
    pub assumptions: Vec<Assumption>,    // each becomes an acknowledgement check
    pub inflation: Inflation,            // g(d), fitted by leave-one-out (D-COV-25)
    pub evidence: Vec<ObjectId>,         // oracle results and Evidence records
}

pub struct RegimeBound {
    pub variable: RegimeVariableId,      // a typed Ingot function with its transform (D-COV-18)
    pub reduction: Reduction,            // Pointwise | Max | Min | Mean | Percentile(p)
    pub calibrated: QuantityInterval,    // backed by evidence; its width normalizes the variable
    pub extrapolated: QuantityInterval,  // superset; plausibility limit
    pub outside: Disposition,            // Flag (a Waiver may cover it) | Refuse
    pub on_missing: OnMissing,           // Unassessed | ConservativeDefault { value, basis }
    pub escalate_to: Vec<ModelRef>,
    pub basis: Citation,
}

pub struct PointSet { pub points: ObjectId, pub d_cal: f64 } // normalized coordinates, L∞ distance

pub enum ValidityZone { Calibrated, Extrapolated, Invalid, Unassessed }
```

Material-specific bounds come from constitutive calibration, so a model has a calibrated zone per Material.

### Zone geometry

Intervals alone describe a box, which overstates coverage when tests ran only at, say, high temperature and low rate. A point outside any extrapolated interval is Invalid. Inside them, zones also measure distance to the validation points, which an E2 envelope lacks.

**Decision D-COV-25:** Zones use L∞ distance d to the nearest validation point, each variable log- or affine-transformed and scaled by its calibrated width. Calibrated needs d ≤ d_cal inside every calibrated interval, and Extrapolated model form grows by g(d), non-decreasing from g(0) = 1 and fitted per package by leave-one-out. *Why:* log coordinates fail for signed variables such as triaxiality, hulls go sparse above about six dimensions, and one distance serves zone and inflation (R7-28). *Rejected:* convex hulls (round 2); a Gaussian-process density, which measures sample density, not validity; std g(d) defaults before three E3 packages per domain.

### Regime variables

Each variable states its length or time scale; a Reynolds number without one is not a regime variable.

| Variable | Definition | Typical users |
| --- | --- | --- |
| Equivalent strain, rotation | From the displacement Field | Small-strain kinematics |
| Homologous temperature | T / T_melt, absolute temperatures | Creep onset, rate-independent plasticity |
| Strain rate, triaxiality, Lode parameter | From strain-rate and stress Fields | Johnson–Cook range, ductile fracture |
| Reynolds, Mach, y⁺ | u·L/ν with L declared per bound | Laminar models, wall treatment |
| Separation | Wall-shear sign change; Clauser parameter β = (δ*/τ_w)·dp/dx | RANS envelopes |
| Knudsen | Mean free path over a declared gap or feature length | Continuum, slip and DSMC models |
| Biot, Rayleigh, Prandtl | From geometry and properties | Lumped capacitance, correlations |
| Wall resolution | Cells at p = 2 across δ_T = H·Ra_H^(−1/4); cells across the cavity half-thickness | Laminar heat transfer; 3D fill and pack |
| Weber, capillary, Weissenberg | From interface and rheology Fields | Breakup, viscoelastic flow, HPDC filling |
| Lubrication geometry | h/L_flow; \|∇h\|; distance in units of h from gates, rib roots, steps and the flow front | Hele-Shaw filling |
| Local slenderness | t / L_local for walls, d / L_local for members (contract 7.1) | Shell and beam models |
| Member inelasticity | σ_cr,Euler / σ_proportional per member | Eigen-buckling of members and struts |
| Strut imperfection | Waviness amplitude over radius of gyration (MFG's calibration) | Strut buckling |
| Lattice regimes | Cell size over gradient length; cells to the boundary; relative density; slenderness times macro strain against a Bloch-wave bound | Lattice models |
| Imperfection sensitivity | Koiter coefficient from FLX (phase 2), or a classifier of known sensitive shells | Eigen-buckling of shells |
| Mass ratio, frequency separation | ρ_s·t/(ρ_f·L) or added-mass fraction; frequencies against forcing bands | Weak fluid–structure coupling |
| Electrical size kL, skin depth δ/L, optical size L/λ | From frequency or wavelength, geometry and properties | Quasi-static electromagnetics, geometric optics |
| Mean-free-path share | Conductivity share from phonon mean free paths above the feature size | Fourier conduction |
| Lambda ratio | EHL film thickness over composite roughness | Gear and bearing ratings |
| C-rate, state of charge, cell temperature | From cell states | Battery model selection |
| Acoustic amplitude p′/ρc² | From the pressure Field | Linear acoustics |
| Cycles N, stress ratio R, ΔK | From load histories | Fatigue regimes |
| Scale ratio ℓ/L | Microstructure length over feature size | Homogenized properties |

**Decision D-COV-18:** Every `RegimeBound.variable` resolves to a typed Ingot function of inputs or solution Fields; an uncomputable condition is an `Assumption` a human acknowledges. A missing material input makes a bound `Unassessed`, or `Extrapolated` under a documented conservative default. *Why:* prose bounds such as "mildly separated flow" cannot be evaluated, and one missing grain size would otherwise block every design (R1-31). *Rejected:* checking only that a bound cites a basis; silently skipping bounds with missing inputs.

Std ships detectors for common prose conditions, such as separation and imperfection-sensitive shells; Flux computes the lattice regime variables (FLX "Homogenization and lattices").

### Evaluation

1. **A priori screen.** Bounds computable from inputs, such as inlet Reynolds number, run first; a `Refuse` bound beyond its extrapolated range stops the solve.
2. **Solve.** Flux evaluates the Ops as usual.
3. **A posteriori assessment.** Every accepted step updates each regime variable's running extrema per region by a segmented reduction. Zones use them; zone Fields are written at output steps.
4. **Composition.** Envelopes of coupled models and of the coupling itself compose by intersection.
5. **Checks.** Each bound compiles to a check named `validity::<model>::<variable>`, with severity from the zone policy.
6. **Display.** UIX hatches Extrapolated, Invalid and Unassessed zones (UIX "Field views"); inspection shows value, bound, basis and escalations.

Zone Fields are identical within the canonical class, and releases use canonical zones (R1-45). Other classes may differ only within twice a bound's cross-class tolerance (`NearBound`). Assessment costs under 2% of solve time (target, FLX-O-DISC-7).

[[DIAGRAM diagrams/04-coverage-validity-flow.jsx: validity flow · screen, solve, zones, checks and the ErrorBudget]]

Read the centre column downward; side branches mark `Refuse` stops and Waivers, and the right box is each result's budget.

### Policy by zone

| Zone | `Interactive` | `SignOff` | Release gate |
| --- | --- | --- | --- |
| Calibrated | Shown | Checks evaluate normally | Allowed |
| Extrapolated | Hatched; model form inflated | Checks use the inflated part and name the zone | A Waiver (contract 2) |
| Invalid, `Flag` | Hatched; dependent checks error | Dependent checks return `Error(Failure)` | A Waiver |
| Invalid, `Refuse` | Shown for diagnosis only | Dependent checks return `Error(Failure)` | Blocked; no Waiver applies |
| Unassessed | Hatched with a missing-input notice | Dependent checks return `Error(Failure)` | Blocked until the input or a default exists |

**Decision D-COV-5:** Validity bounds compile to ordinary checks, and validity zones are a Field built from running extrema that every accepted step updates. *Why:* checks and Fields already carry severity, review and display, and output-step sampling misses transients such as an impact's peak strain rate (R7-33). *Rejected:* a separate warnings channel; clamping results to the envelope; assessment at output steps only. (revised in round 3)

**Decision D-COV-6:** Crucible suggests escalation to a valid model but never switches models automatically. *Why:* a switch changes cost, provenance and sometimes the answer, so it must be explicit. *Rejected:* automatic escalation between model levels.

### Failure behaviour

A `Refuse` bound surfaces as `Error(Failure)` carrying `ValidityError::OutsideEnvelope`, the one failure COV and FLX both name.

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

```
error[validity]: std::physics::fluid::navier_stokes@3 is invalid in region `squeeze_gap`
  Knudsen number reaches 0.31; calibrated below 0.001, refused above 0.01
  basis: no-slip walls fail in slip and transitional flow (std::physics::regime::knudsen)
  try: std::physics::rarefied::dsmc (External Op; valid for Kn 0.1 to 10)
```

Widening any envelope needs a human Approval of the Proposal, as loosening a tolerance does; agents may propose but never merge widenings.

### Surrogates and learned models

**Decision D-COV-7:** A learned surrogate is an L2 model whose calibrated zone is its training distribution and whose `Estimated { confidence, scope: Marginal }` predictions drive exploration up to `Interactive`. Out-of-distribution queries are Extrapolated or Invalid; `SignOff` needs a confirming solve or a bound in the check's norm, DWR with an adjoint solve for peaks. *Why:* conformal coverage is marginal, optimizers seek a surrogate's errors (R1-04), and energy bounds never certify a peak (R7-24). *Rejected:* treating a surrogate as its source model; split-conformal intervals at `SignOff`; E3 without held-out physical validation. (revised in round 3)

### Coupled physics

Flux owns coupling algorithms; COV owns their envelopes, so a weak coupling outside its envelope is flagged like any model.

| Pair | One-way coupling allowed when | Benchmark |
| --- | --- | --- |
| Thermal → structure | Deformation leaves thermal conditions and contact conductance unchanged | NAFEMS LE11 −105 MPa [S2][S3] |
| Fluid ↔ structure | D-COV-19 holds | Turek–Hron [S69] |
| Electromagnetic → thermal | Conductivity and permeability insensitive to temperature | TEAM 36 [S6] |
| Electrochemical ↔ thermal | Below a declared C-rate and temperature rise | PyBaMM lumped and x-full thermal options [S70] |
| Structure ↔ acoustics | Fluid-loading parameter ρ_f·c/(ω·m_s) below 0.1 over the band; never for heavy fluids | Baffled piston, plate radiation |
| Electrostatic ↔ structure | Never near pull-in | Parallel-plate pull-in |
| Process → structure | Always one-way within Crucible; VMAP exchanges state with process tools [S58] | AM-Bench [S11] |
| Aerodynamics ↔ structure | D-COV-19 holds, with p–k flutter as the stability check | AGARD wing 445.6 [S71] |

**Decision D-COV-19:** One-way fluid– or aerodynamic–structure coupling needs mass ratio ρ_s·t/(ρ_f·L) above 10 or added mass below 5%, clear forcing frequencies and positive coupled damping. Damping comes from p–k flutter or a linearized coupled eigenanalysis over the operating envelope; otherwise the coupling is Invalid and escalates to two-way. *Why:* flutter, galloping and lock-in grow from infinitesimal amplitudes, so a displacement test approves one-way analysis where coupling destabilizes (R1-27). *Rejected:* displacement below 1% of the flow length; small static twist.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Envelope records | `ValidityEnvelope` per model version with validation points and validated classes | Registry rejects a missing envelope, basis, transform, escalation or inflation | COV-O-ENV-1 | 0 |
| Regime variables | Typed Ingot functions with declared scales and transforms | `RegimeUncomputable { variable }` at registration | COV-O-ENV-6 | 0 |
| Zone semantics | Intervals, running extrema and zone policy, evaluated by `flux::validity_zones` | `Error(Failure)` carrying `ValidityError::OutsideEnvelope` | FLX-O-ERR-9 | 1 |
| Zone geometry | Normalized L∞ distance, d_cal and fitted g(d) (D-COV-25) | Beyond d_cal: Extrapolated, nearest validated condition reported | COV-O-VAL-2 | 1 |
| Zones across classes | Canonical zones identical; `NearBound` elsewhere | A mismatch outside the band is a determinism incident | COV-O-ENV-3 | 1 |
| `Refuse` bounds | Stop the solve or block dependent checks | `Error(Failure)` with fixes | COV-O-ENV-4 | 1 |
| Waivers and widening | Waivers (contract 2) for Extrapolated and `Flag` zones; widening by human Approval | Agent attempts fail; `Refuse` accepts no Waiver | COV-O-ENV-5 | 1 |
| Missing inputs | Documented default, else `Unassessed` | `ValidityError::Unassessed { missing }` | COV-O-ENV-6 | 1 |
| Surrogate envelopes | Training distribution as calibrated zone; bounds in the check's norm | Out-of-distribution queries Extrapolated or Invalid | COV-O-ENV-7 | 4 |
| Coupling envelopes | Weak couplings inside their envelope (D-COV-19) | One-way analysis outside it Invalid | COV-O-ENV-8 | 1 thermal, 4 fluid |

## Coverage matrix

The matrix is generated from package metadata (D-COV-1). This tab sets its initial content, so every row is `Planned`, and "(13.4)" marks a contract-set phase.

Scales: **N** below 100 nm, **µ** to 1 mm, **Me** to 100 mm, **P** to 10 m, **L** beyond. Delivery: **Nat** an Ingot weak form or Flux operation; **Wasm** a `std` Wasm component (D-COV-11); **Ext** an External Op (D-COV-12). Envelope numbers are design defaults that each package confirms or replaces before E2.

### Solid mechanics

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Linear elasticity (µ Me P L) | Beam, plate and shell formulas · frame networks · static condensation | High-order FEM on the immersed octree; IGA on trimmed B-rep; finite cell for voxels | Strain ≤ 0.5% calibrated, ≤ 2% extrapolated; below the proportional limit; rotation ≤ 0.05 rad; feature ≥ 10 grains or a strut-scale Material | NAFEMS LE1 92.7 MPa, LE10 −5.38 MPa, LE11 −105 MPa [S3][S4]; GP1, GP2 | 1 (octree), 2 (IGA, finite cell, frame networks) · Nat |
| Shells, beams and frames (Me P L) | Beam and plate formulas · frame networks · — | Reissner–Mindlin and IGA Kirchhoff–Love shells; Timoshenko and Vlasov beams; Nitsche couplings (D-FLX-12) | t/L_local ≤ 0.2, or ≤ 0.05 for Kirchhoff–Love; d/L_local ≤ 0.2; reduction error from 3D patches (D-FLX-26) | NAFEMS shell and beam cases | 1 lattices, 2 · Nat |
| Geometric nonlinearity (µ Me P L) | — | Total Lagrangian FEM with arc-length continuation | Limit and bifurcation points reported, never stepped over | NAFEMS R0024 group [S5] | 2 · Nat |
| Plasticity (µ Me P L) | Neuber and Glinka notch rules · — · — | Finite-strain J2, Hill48, Yld2000-2d, Chaboche; tangents through `local_solve` | Rate-independent below homologous T 0.3; past uniform elongation only with damage | NAFEMS R0024 panel [S5]; thick cylinder | 2 · Nat |
| Hyperelasticity (µ Me P) | — | Mixed u–p and F-bar; Neo-Hookean to Gent | Stretch within the calibrated range per mode; strong ellipticity | Cook's membrane; patch tests | 2 · Nat |
| Viscoelasticity (µ Me P) | — · Prony networks · complex-modulus modal | Generalized Maxwell with WLF or Arrhenius shift; Bergström–Boyce | Temperature and frequency within the master curve | Analytic creep and relaxation | 3 · Nat |
| Creep (Me P L) | Larson–Miller · — · — | Norton–Bailey, Garofalo, theta projection; Kachanov–Rabotnov damage | Time ≤ longest test calibrated, ≤ 3× extrapolated (OOR-5) | NAFEMS R0027 [S5] | 3 · Nat |
| Contact and friction (µ Me P L) | Hertz, Boussinesq · — · — | Mortar contact on fitted tetrahedra (13.4); IPC from phase 5 (FLX) [S26] | Penetration below tolerance; friction only from a tested pair (OOR-19) | NAFEMS R0094 [S5]; Hertz | 2 · Nat |
| Bolted and bonded joints (Me P L) | VDI 2230-1:2015 [S115] · joint springs · — | Preloaded bolts; cohesive zones with Benzeggagh–Kenane mixing | Joint parameters and damping from tests of the joint class (OOR-18) | DCB and ENF | 2 (bolts), 3 (cohesive) · Nat |

Snap fits and soft parts use mortar contact until FLX's IPC arrives in phase 5, reporting d̂ and ε_v under `regularization` [S111].

### Dynamics and stability

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Modal analysis (µ Me P L) | Rayleigh, Dunkerley · lumped MDOF · Craig–Bampton | Lanczos and LOBPCG (13.4); eigenvalue DWR bound on the unsafe side (FLX) | Linear; damping from test (OOR-18) | NAFEMS free vibration [S2][S5] | 1, 2 (Craig–Bampton) · Nat |
| Vibration and shock (Me P L) | SDOF, Miles, shock spectra · — · modal with residual vectors | Direct frequency response; PSD response; implicit generalized-α | Damping declared; PSD band and pulse within modal coverage | NAFEMS R0016 [S5]; half-sine SDOF | 2 · Nat |
| Rotordynamics (Me P) | Jeffcott rotor · rotor beams · Campbell modal | Rotating-frame FEM; fluid-film bearings from the Reynolds equation | Bearings linearized at operating speed | Jeffcott critical speed | 2 · Nat |
| Buckling (µ Me P L) | Euler, Johnson, Perry–Robertson · — · linear eigen-buckling (13.4) | Arc-length post-buckling with imperfections and plasticity; Koiter asymptotics (FLX) | Members and struts per D-COV-30; `Refuse` at `SignOff` on imperfection-sensitive shells | NAFEMS R0024 [S5]; Euler and Johnson columns | 1 linear, 2 nonlinear and Koiter · Nat |
| Explicit dynamics, impact, crash (Me P L) | Energy methods · lumped crash networks · — | Explicit dynamics with diagonal mass and penalty contact (FLX); erosion from COV damage | Mass scaling ≤ 2% calibrated, `Refuse` above 5%; hourglass energy ≤ 10% of internal; failure `Flag` (OOR-6) | Taylor bar; GP5 drop; GP9 crash box | 3 drop, 5 crash (13.4) · Nat; OpenRadioss (AGPL) as Ext reference [S25] |

**Decision D-COV-30:** Linear eigen-buckling of a member or strut is Calibrated while the inelasticity ratio σ_cr,Euler/σ_proportional stays below 0.5, Extrapolated to 1 and `Refuse` beyond. Escalation goes to Johnson or tangent-modulus rungs; strut waviness over radius of gyration beyond the declared value is `Flag`, with a Perry–Robertson rung. *Why:* printed struts are stocky enough to buckle inelastically, where Euler's load overstates capacity, and waviness lowers it further (R7-06). *Rejected:* refusing only imperfection-sensitive shells (round 2), which let every strut pass.

### Durability: fatigue, fracture, wear

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Stress-life (Me P L) | Basquin with Goodman, Gerber or Walker · rainflow · — | Critical plane (Findley, Dang Van) with surface, size and notch factors; probabilistic S–N | N ≥ 10⁴; R and temperature within tests; defects below Kitagawa–Takahashi | Held-out coupons | 1 uniaxial, 2 multiaxial · Nat |
| Strain-life (Me P L) | Coffin–Manson, Morrow, SWT · — · — | Fatemi–Socie, Brown–Miller on elastic-plastic FE | Cyclic curve from the same condition | Notched specimens | 2 · Nat |
| Weld fatigue (Me P L) | Nominal, hot-spot and effective notch stress (IIW [S116], EN 1993-1-9 [S117]) · — · — | Structural-stress methods on shells and solids | Weld class and quality declared | Hand calculations to the cited code | 2 · Nat |
| Gears, bearings and shafts (Me P) | Gears to ISO 6336:2019 [S118] or ANSI/AGMA 2101-E25 [S120]; bearings to ISO 281:2007 with ISO 16281:2025 [S121][S122]; shafts to DIN 743:2012 [S123] or the FKM guideline [S112] · — · loaded tooth contact analysis with FE influence coefficients | Mortar contact on fitted tetrahedra as the validation rung (13.4) | Lambda ratio and temperature within the rating's scope; load spectrum declared | ISO/TR 6336-30 examples [S119]; GP3 | 2 (13.4) · Nat |
| Lubrication and rolling-contact fatigue (µ Me P) | Hamrock–Dowson film thickness [S72] · — · — | Elastohydrodynamic Reynolds equation with pressure–viscosity and elastic deflection; subsurface critical-plane fatigue | Isothermal Newtonian film unless declared; life `Flag` without bearing-steel data | Hertz pressure; Hamrock–Dowson film thickness | 2 · Nat |
| Crack growth (Me P L) | Paris, NASGRO with handbook K · — · — | Interaction-integral K and J; spectrum retardation | Small-scale yielding; ΔK above threshold | NAFEMS R0020 [S5] | 3 · Nat |
| Fracture (µ Me P L) | K_Ic, failure assessment diagrams · — · — | Cohesive zones; phase field (AT1, AT2); Gurson–Tvergaard–Needleman, Hosford–Coulomb | Ductile `Flag`: a blind round robin found "a striking lack of consistency" [S12] | Sandia Fracture Challenge [S12] | 2 LEFM, 3 cohesive, 4 phase field, 5 ductile · Nat |
| Wear and erosion (µ Me P) | Archard; Finnie erosion [S73] · — · — | Archard on local pressure and slip with geometry update; particle impact erosion | Coefficients from the tested pair and medium; erosion `Flag` | Pin-on-disc | 3 wear, 5 erosion · Nat |

**Decision D-COV-26:** Gear, bearing and shaft strength use L0 standard ratings and L2 loaded tooth contact analysis, with mortar contact on fitted tetrahedra as the validation rung. Ratings return margin Fields per failure mode from MEC's gear records (geometry, accuracy grade, load spectrum). *Why:* practitioners rate gears and bearings by standard, and tooth contact gives load sharing and transmission error far more cheaply than 3D contact (R7-19, R10-18). *Rejected:* 3D mortar contact as the design rung; geometry without ratings.

### Composites and architected materials

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Laminates (Me P L) | Classical laminate theory · — · — | Layered and IGA shells on draped fibre-angle Fields (plies and draping: MEC) | Through-thickness stress needs layerwise or solid models | NAFEMS R0031 [S5] | 4 (13.4) · Nat |
| Progressive failure (Me P L) | Tsai–Wu, Hashin, Puck, LaRC05 · — · — | Continuum damage with cohesive interlaminar zones, calibrated in a building-block pyramid | `Flag`: in WWFE-II none of 12 theories matched all test data [S13] | WWFE-II [S13] | 4 · Nat |
| Short-fibre moulded composites (Me P) | Rule of mixtures · — · — | Mori–Tanaka averaging over the orientation tensor Field from filling | Aspect ratio and fraction within calibration | Unidirectional limit | 3 (13.4) · Nat |
| Lattices (µ Me P) | Gibson–Ashby · — · homogenization with localization | Beam lattices with calibrated node corrections (strut cells); Reissner–Mindlin mid-surface shells (sheet cells); full-resolution immersed FEM as reference | Cell over gradient length ≤ 0.1; `Invalid` within 2 cells of an uncorrected boundary; relative density within the node-correction calibration; `Flag` above the Bloch-wave bound | Full-resolution unit cells (FLX-O-COUP-2) | 1 strut cells, 2 sheet cells · Nat |

A lattice part's critical region signs off on the beam-lattice model's localized strut stresses (R1-26). Strut-scale Materials from MFG's as-built calibration (13.4) include strut diameter in their coverage, so printed struts escape the grain default. Node corrections are calibration data per cell topology over a relative-density range; sheet cells use shells on the minimal surface's zero set (FLX, ANV).

### Heat transfer

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Conduction (N µ Me P L) | Slab, fin and shape factors · RC networks · moment matching | High-order FEM, IGA, immersed methods | Fourier law `Refuse` above the declared mean-free-path share | NAFEMS T2 to T4 [S2][S5] | 1 (FEM), 2 (IGA, networks), 3 (moment matching) · Nat |
| Convection (Me P L) | Nusselt correlations within published ranges · flow networks · — | Conjugate heat transfer on laminar, RANS or LES flow | Correlation ranges `Refuse`; conjugate analysis inherits the flow envelope; laminar walls Extrapolated below five cells across δ_T | NAFEMS T4 [S5]; Graetz | 2 correlations, 3 laminar and natural, 4 turbulent (13.4) · Nat |
| Radiation (Me P L) | Two-surface enclosures · radiosity networks · — | Ray-traced view factors; Monte Carlo for specular and spectral surfaces; discrete ordinates | Gray-diffuse declared; spectral bands where emissivity varies | Analytic view factors; closure ΣF = 1 within 10⁻⁶ | 3, 4 discrete ordinates · Nat |
| Solid–liquid phase change (µ Me P) | Stefan, Neumann · — · — | Enthalpy method with mushy zone | Freezing range declared; no undercooling | Stefan analytic | 3 · Nat |
| Boiling, condensation, heat pipes (Me P) | Rohsenow, Nusselt film · heat-pipe and vapour-compression networks with CoolProp [S43] · — | VOF with phase change | Correlations `Refuse` outside range; heat-pipe limits reported; resolved boiling `Flag` | Nusselt film analytic | 4, 5 (VOF, 13.4) · Nat |
| Moisture and hygro-mechanics (µ Me P L) | Equilibrium moisture tables · — · — | Fickian diffusion with sorption isotherms, hygro-expansion, mechano-sorptive creep | Humidity and temperature within sorption data; mechano-sorptive creep `Flag` | Fickian slab | 3 packages, 7 timber · Nat |
| Ablation and pyrolysis (Me P) | Heat of ablation · 1D charring ablator · — | Surface energy balance with B′ tables and recession | `Flag` always | Ablation Workshop test cases [S74] | 6 · Wasm |
| Joule heating and thermoelectrics (µ Me P) | Resistive and Peltier module formulas · — · — | Electro-thermal coupling with temperature-dependent resistivity; Seebeck–Peltier–Thomson FEM | Resistivity within data; linear thermoelectric coefficients | Wire heating; analytic module | 4 Joule (13.4), 5 thermoelectric · Nat |

### Fluids

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Incompressible laminar (µ Me P) | Hagen–Poiseuille, Moody · duct networks · POD-Galerkin | Stabilized high-order FEM or DG | Re below transition (pipe: 2,000 calibrated, 2,300 extrapolated) | Lid-driven cavity [S75] | 3 · Nat |
| RANS (Me P L) | Loss data · networks with loss coefficients · — | Spalart–Allmaras, SST, GEKO; γ–Reθ transition; quadratic constitutive relation; wall models (FLX) | Attached flow calibrated; separation `Flag`; y⁺ range declared | NASA TMR 2DZP, 2DB, 2DMEA, 2DWMH, ATB [S1] | 4 · Nat |
| Scale-resolving: DDES, WMLES, LES (Me P L) | — | Entropy-stable DG [S28] and flux reconstruction [S27]; non-equilibrium wall models [S15] | Cost from Yang–Griffin scalings [S14]; equilibrium wall models `Flag` in adverse pressure gradients [S15] | 2DWMH hump [S1] | 5 · Nat |
| DNS (µ Me) | — | Spectral and high-order DG | `Refuse` above the a priori budget (OOR-1) | Taylor–Green vortex [S76] | 5 · Nat |
| Lattice Boltzmann (Me P L) | — | Cumulant collision with wall models (FLX); XLB (Apache-2.0) as reference [S38] | Ma ≤ 0.1 calibrated, ≤ 0.3 extrapolated | As LES | 4 · Nat |
| Compressible flow (Me P L) | Isentropic and shock relations · quasi-1D nozzle · — | Entropy-stable DG and flux reconstruction; SU2 (LGPL-2.1) as reference [S37] | Perfect gas below a declared temperature; nonequilibrium Ext | ATB, ONERA M6 [S1] | 5 · Nat |
| Free surface and resolved multiphase (µ Me P L) | Linear wave theory · — · — | Geometric VOF, conservative level set, Cahn–Hilliard; weakly compressible SPH | Converged at k_max·η_KH ≥ 60 with second-order schemes [S16]; coarser `Flag` | Dam break [S78]; rising bubble [S77] | 5 (13.4) · Nat |
| Dispersed multiphase (Me P L) | Settling and drag correlations · — · — | Euler–Lagrange with two-way coupling; Euler–Euler | Volume-fraction limit per model; breakup `Flag` (OOR-8) | Stokes settling | 5 (13.4) · Nat |
| Cavitation (Me P) | Cavitation number · — · — | Mixture models with Schnerr–Sauer or Zwart transfer | `Flag` always; erosion out of reach (OOR-9) | Rayleigh collapse time [S95][S96] | 6 · Nat |
| Non-Newtonian (µ Me P) | Power-law pipe flow · — · — | Carreau–Yasuda, Cross–WLF, Herschel–Bulkley; Oldroyd-B, Giesekus, PTT with log-conformation | Shear rate within rheometry; Weissenberg within the verified range | Poiseuille; 4:1 planar contraction [S79] | 3, 5 viscoelastic · Nat |
| Porous media (µ Me P L) | Darcy, Ergun · — · — | Darcy–Brinkman–Forchheimer; permeability from pore-scale lattice Boltzmann | Pore Reynolds number within the law | Porous channel | 3, 4 (lattice Boltzmann) · Nat |
| Rarefied gas (µ Me P) | Free-molecular formulas · — · — | Slip and temperature jump; DSMC with SPARTA (GPL) [S34] | Continuum below Kn 0.001, slip to 0.1, transitional to 10 | Microchannel slip | 5 · Nat slip, Ext DSMC |
| Microfluidics (µ Me) | Stokes resistances · hydraulic networks · — | Stokes FEM with electro-osmotic slip and Nernst–Planck transport | Debye length much smaller than the channel | Electro-osmotic plug flow | 5 · Nat |
| Combustion (Me P L) | Adiabatic flame temperature · reactor networks with Cantera (BSD-3) [S21][S22] · flamelet tables | Flamelet-progress-variable, FGM; finite-rate chemistry in LES | `Flag` always (OOR-7) | Flame speeds; Sandia piloted flames of the TNF Workshop [S80] | 6 · Wasm kinetics, Nat transport |

COV owns free-surface and multiphase flow beyond mould filling (13.4); real-fluid properties come from CoolProp [S43] or a licensed REFPROP connector.

### Acoustics and ultrasonics

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Linear acoustics (Me P L) | Sabine, Eyring · duct transfer matrices · modal | High-order FEM with PML; fast BEM; geometrical room acoustics | p′/ρc² ≤ 10⁻²; points per wavelength above the order's minimum | Pulsating sphere, baffled piston | 3 · Nat |
| Vibro-acoustics (Me P L) | — · statistical energy analysis · modal | Structural–acoustic FEM and FEM–BEM | SEA needs 3 modes per band; heavy fluids and light panels two-way | Plate radiation | 3 FEM, 5 SEA · Nat |
| Porous absorbers (Me P) | Delany–Bazley · transfer matrix · — | Johnson–Champoux–Allard; Biot | Flow resistivity within measured range | Impedance tube | 5 · Nat |
| Aeroacoustics (Me P L) | Gutin tonal noise · — · — | Ffowcs Williams–Hawkings from blade loading or scale-resolving surfaces | Broadband `Flag` without scale-resolving input | GP6 rotor acoustics | 4 tonal, 5 broadband · Nat |
| Ultrasonic testing (µ Me P) | Ray and beam-spread formulas · — · — | Spectral-element or DG elastodynamics with transducers | Linear; grain scattering `Flag` without microstructure | Lamb-wave dispersion | 6 · Nat |

### Electromagnetics

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Electrostatics (N µ Me P L) | Plate, sphere, coaxial formulas · capacitance networks · — | High-order FEM; fast BEM; capacitance extraction as in Palace (Apache-2.0) [S18] | kL ≤ 0.1 calibrated, ≤ 0.3 extrapolated | Sphere, coaxial; Palace [S18] | 3 · Nat |
| Magnetostatics (µ Me P L) | Magnetic circuits · reluctance networks · — | Nédélec FEM with tree–cotree gauging and Newton on B–H curves | B within measured B–H range | TEAM 13 [S6] | 3 · Nat |
| Eddy currents and induction (µ Me P L) | Skin-depth formulas · — · — | A–φ and T–Ω; surface impedance | Surface impedance only where δ/L ≤ 0.1 | TEAM 7 and 36 [S6] | 4 · Nat |
| Electric machines (Me P) | dq circuits · loss and thermal networks · flux-linkage maps | Sliding-interface motion; Bertotti iron loss; magnet eddy loss; demagnetization | Loss coefficients per lamination grade and band | GP6 motor tests | 4 · Nat |
| RF and antennas (Me P L) | Line formulas · S-parameter networks · Krylov sweeps | Nédélec FEM with wave ports and fast sweep; FDTD for broadband (D-FLX-32); MoM with fast multipole | Dispersion fit inside the measured band | Dipole with a Hallén reference; Mie sphere | 4 drone antenna, 5 general · Nat |
| Signal and power integrity (µ Me) | RLGC lines · — · vector fitting | Quasi-static and full-wave extraction | Causality and passivity enforced | Microstrip | 3 · Nat; ELX owns use |
| EMC (Me P) | Shielding formulas · cable models · — | FDTD and DG time domain with field-to-cable coupling | `Flag` always for compliance prediction | Enclosures with apertures [S81] | 4 emissions, 5 immunity · Nat |

### Optics and photonics

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Imaging optics (µ Me P) | Paraxial ABCD · sequential ray tracing · — | Differentiable ray tracing with polarization; Fourier-optics PSF and MTF | Geometric optics where L/λ ≥ 100 | Singlet and doublet | 5 · Nat |
| Illumination and stray light (Me P L) | Photometric formulas · — · — | Spectral Monte Carlo path tracing with measured BSDFs [S39] | BSDF within measured angles and wavelengths | Light-guide measurements | 3 light pipes, 5 · Nat |
| Wave optics and photonics (N µ) | Thin-film matrices · — · eigenmode expansion | FDTD, DG, RCWA, FEM mode solvers; Meep (GPL) as Ext reference | Linear unless declared | Mie; slab modes | 6 · Nat |

### Electrochemistry and chemical kinetics

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Battery cells, reduced (µ Me P) | Capacity formulas · equivalent circuits with OCV, entropic heat and LFP hysteresis [S62] · SPM, SPMe | — | C-rate, temperature and SOC bounds per rung; lithium plating `Flag` | Ladder at low C-rate; drive cycles | 4 (13.4) · Nat |
| Battery cells, DFN (µ Me P) | — | Doyle–Fuller–Newman as parameter-domain forms (D-FLX-38); MSMR OCV [S61]; PyBaMM reference [S19][S20] | As above, plus particle-radius range | PyBaMM DFN | 5 (13.4) · Nat |
| Swelling and stack pressure (Me P) | Thickness change with SOC · pad and stack springs · — | Particle expansion homogenized to the cell against pad stiffness; Ai et al.'s model in PyBaMM [S63][S98] | Expansion curve from measured cell thickness; pad stiffness from test | Thickness and force against SOC | 4 (13.4) · Nat |
| Battery packs (Me P) | Series-parallel scaling · cell, busbar and thermal networks · — | Cells in 3D pack thermal and coolant flow; pseudo-4D packs | Cell spread from measurement | GP6 pack test | 4, 6 pseudo-4D · Nat |
| Battery degradation (µ Me P) | Calendar and cycle fade · — · — | SEI growth, plating, particle cracking, active-material loss | `Flag` always; beyond tested duration `Invalid` (OOR-5) | Held-out ageing data | 5 · Nat |
| Abuse mechanics (Me P) | — | Homogenized jelly-roll crush with failure strain, coupled to runaway screening | `Flag` always: short onset is empirical | GP12 crush tests | 6 (13.4) · Nat |
| Thermal runaway (Me P) | ARC onset · multi-step Arrhenius · — | 3D abuse with decomposition kinetics and propagation | `Flag` always; venting and fire out of reach (OOR-14) | ARC data | 5 · Nat |
| Fuel cells and electrolysers (µ Me P) | Polarization curves · 1D membrane models · — | 3D two-phase PEM with Butler–Volmer kinetics | `Flag`: water closures are empirical | Measured polarization curves | 6 · Nat |
| Corrosion and electroplating (µ Me P L) | Galvanic series, Faraday's law · — · — | Secondary and tertiary current distribution; Nernst–Planck in crevices | Polarization data in the same electrolyte; long horizons `Flag` (OOR-5) | Cathodic-protection cases; parallel-plate primary distribution | 5 · Nat |
| Gas-phase kinetics | Equilibrium · reactors and flames with Cantera [S21][S22] · mechanism reduction | Finite-rate chemistry in CFD | Mechanism ranges enforced | Ignition delay | 6 · Wasm |
| Cure and crystallization kinetics (Me P) | — · Kamal–Sourour cure, crystallization kinetics · — | Cure–thermal–residual-stress coupling | DSC calibration range | DSC data | 3 · Nat |

ELX owns the cell, swelling, abuse and pack capabilities and FLX the DFN solver (13.4); COV owns the envelopes and the degradation and runaway models. LFP hysteresis uses PyBaMM's one-state model, developed on NiMH, refit on LFP data before ELX-O-BAT-1 counts it [S97]. Abuse mechanics names a published jelly-roll model with test data before phase 6 work starts.

### Particles, molecules and multiscale

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Granular media (µ Me P) | Angle of repose, Janssen · — · — | GPU DEM with Hertz–Mindlin and rolling resistance; Project Chrono (BSD-3) reference [S32] | Parameters from repose and shear-cell tests | Beverloo hopper | 5 · Nat |
| Particle methods for large deformation (Me P L) | — | MLS-MPM, SPH, peridynamics | `Flag`: tensile instability, numerical fracture | Column collapse; Taylor bar | 5 · Nat |
| Molecular dynamics (N) | — · — · coarse-grained MD | Machine-learned potentials (MACE, MIT code [S31]); LAMMPS (GPL-2.0) as External Op [S35] | Potential valid only in its training chemistry; model licences checked [S31] | Elastic constants | 6 · Ext |
| Multiscale coupling (N µ Me) | Rules of mixtures · — · surrogate laws | FE² (D-FLX-38); FFT RVE solvers; concurrent atomistic coupling | ℓ/L ≤ 0.1; RVE convergence checked | Hashin–Shtrikman bounds | 5 · Nat; Ext concurrent |

### Plasma and radiation transport

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Gas discharge (µ Me) | Paschen law · global models · — | Drift-diffusion with local-field approximation | Paschen pd range; arcs `Flag` | Paschen curves | 6 · Nat |
| Kinetic plasma (µ Me P) | — | Particle-in-cell; WarpX (BSD-3-Clause-LBNL) as External Op [S33] | Debye length resolved | Two-stream growth rate | 7 · Ext |
| Magnetohydrodynamics (Me P L) | Hartmann flow · — · — | Entropy-stable DG as in Trixi.jl [S28] | Ideal or resistive declared | Orszag–Tang | 7 · Nat |
| Neutron and photon transport (µ Me P L) | Attenuation laws · — · — | Continuous-energy Monte Carlo; OpenMC (MIT) [S23]; CAD geometry through DAGMC [S93] | Data library recorded; criticality safety out of scope (OOS-2) | ICSBEP benchmarks [S94] | 7 · Ext |
| Shielding and dose (Me P L) | Point kernel with buildup · — · — | Monte Carlo transport; Geant4 [S24] | Physics list and energy range declared | Slab attenuation | 6 · Ext |

### Biomechanics and human factors

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Soft tissue (µ Me P) | — | Holzapfel–Gasser–Ogden; biphasic poroelasticity; FEBio (MIT) reference [S40] | `Flag` always; E4 only with V&V 40 [S8] | Confined compression | 7 · Nat |
| Implants (Me P) | Beam and plate formulas · — · — | Nonlinear FEM with bone–implant contact; plate bending fatigue to ASTM F382 [S124] | Declared density–modulus relation | GP15 bone plate tests | 7 · Nat |
| Cardiovascular flow (Me P) | Poiseuille, Womersley · Windkessel · — | ALE fluid–structure interaction | `Flag`: patient boundary conditions dominate | FDA benchmark nozzle [S82] | 7 · Nat |
| Musculoskeletal posture (P) | Anthropometric tables · — · — | Multibody with optimal control; OpenSim (Apache-2.0) reference [S41] | Population and task within data | Motion-capture gait trials | 5 · Wasm |
| Human factors (P) | Reach envelopes, revised NIOSH lifting equation [S125] · — · — | Digital humans from ANSUR II (6,068 subjects, 93 measures [S47]) | Multivariate percentiles, not single-measure | Fit and reach | 5 · Nat |
| Cloth and soft goods (Me P) | — | Shell or discrete elastic models with IPC contact (FLX, phase 5) [S26] | Fabric data from Kawabata-type tests [S126] | ISO 9073-9 drape coefficient [S127]; GP16 | 5 · Nat |

### Manufacturing process physics

MFG owns process setups, the as-built strut calibration and the moulding, casting, welding, forming and chatter capabilities (13.4). COV owns constitutive draping and cure (13.4) and every row's models, envelopes and state Fields; D-COV-27 separates Material properties from process profiles.

| Process (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Powder bed fusion (µ Me P) | Rosenthal source · — · inherent strain through supports, baseplate cut and stress relief (FLX) | Layer-agglomerated thermo-mechanics; melt-pool thermal-fluid with Marangoni and keyhole physics | Inherent strain and relaxation only for the calibrated machine, material, parameters and stress relief; melt pool `Flag` outside AM-Bench conditions | AM-Bench 2018, 2022, 2025 [S11] | 2 inherent strain (13.4), 4 thermo-mechanical, 6 melt pool · Nat |
| Extrusion and resin printing (Me P) | Bead formulas · — · — | Thermal history with bond strength; vat cure depth | Interlayer strength from tests | AM-Bench [S11] | 2 · Nat |
| Injection moulding (Me P) | Flow-length ratios · Hele-Shaw filling (MFG) · — | Level-set fill; Cross–WLF, Tait pvT; ARD-RSC orientation [S83][S84]; pvT-path stress with frozen layers and mould constraint; crystallization; post-ejection relaxation | Hele-Shaw only at h/L_flow ≤ 0.1, \|∇h\| ≤ 0.1 and 2h from gates, rib roots, steps and the flow front, else 3D at `SignOff`; 3D Extrapolated below eight cells across the half-thickness | GP5 short shots and warpage | 3 (13.4) · Nat |
| Casting (Me P L) | Chvorinov rule · — · — | VOF filling; Niyama porosity; hot-tearing indicators | Gate Weber number above breakup makes filling `Extrapolated` and indicators qualitative (OOR-8) | Chvorinov and Stefan solidification times | 6 (13.4) · Nat |
| Welding distortion (Me P L) | Shrinkage forces · — · inherent strain; joint loads on beam frames | Goldak source with phase transformation and thermo-elasto-plasticity | Inherent strains from coupons per joint type, thickness, process and heat input; transient source from macrographs | GP4 measured distortion | 2, 4 transient (13.4) · Nat |
| Machining and chatter (Me P) | Mechanistic cutting coefficients · — · — | Stability lobes from tool-tip FRFs; semi-discretization | Coefficients per tool, material and speed | Analytic lobes | 3 (13.4) · Nat |
| Stamping and springback (Me P L) | Bend allowance · — · one-step inverse | Incremental shell forming with Yld2000-2d and Yoshida–Uemori | Springback `Flag` without tension–compression data | NUMISHEET benchmarks [S85] | 2 bend, 5 forming (13.4) · Nat |
| Heat treatment (Me P) | Jominy · — · — | JMAK, Koistinen–Marburger, transformation plasticity | TTT and CCT data required | Jominy data | 6 · Nat |
| Composite draping and cure (Me P L) | Kinematic draping (MEC, phase 4) · — · — | Constitutive draping with shear locking; cure kinetics with process stress and spring-in | Shear below the measured locking angle; cure within DSC range | Picture-frame and bias-extension tests; spring-in coupons | 5 (13.4) · Nat |

Beam-modelled frames take weld shrinkage as equivalent joint loads from inherent strains on a local shell or solid model of each joint (MFG, FLX). Phase 3 calibrates the Hele-Shaw thresholds against 3D solves on a step plate and a ribbed plaque; until then the zone is Extrapolated.

### MEMS and piezoelectrics

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Electrostatic actuation (µ Me) | Parallel-plate pull-in · spring–capacitor · macromodels | Monolithic electromechanical FEM; pull-in as a bifurcation | Bulk properties need features ≥ 1 µm | Pull-in analytic | 5 · Nat |
| Squeeze-film damping (µ) | Reynolds coefficients · — · — | Rarefaction-corrected Reynolds equation; DSMC in transitional gaps | Knudsen bounds as for rarefied gas | Analytic squeeze film | 5 · Nat |
| Piezoelectric devices (µ Me P) | Mason and BVD circuits · — · modal | Piezoelectric FEM with losses | Below the coercive field | Thickness-mode resonator | 5 · Nat |
| Thermal MEMS and anchor loss (µ) | Zener damping · — · — | Thermoelastic eigenanalysis; PML anchor loss | Q `Flag` without fabrication data | Zener analytic | 6 · Nat |

### Civil structures and geomechanics

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Steel structures (P L) | Member checks (Eurocode 3 [S117], AISC 360-22 [S128]) · frame analysis · — | Beams and shells with geometric nonlinearity; bolted connections | Code edition recorded | GP8 structural check | 5 · Nat |
| Timber structures (P L) | Member checks (Eurocode 5) [S64] · frame analysis · — | Beams, shells and orthotropic solids with moisture | Service class declared | GP14 | 7 · Nat |
| Structural fire resistance (P L) | Standard fire curve (ISO 834-1:2025 [S129]) and parametric curves · — · — | Thermal analysis with charring (EN 1995-1-2 [S64]) and temperature-dependent degradation | Prescribed exposure only; fire growth is OOR-14 | Charring depth | 7 · Nat |
| Reinforced concrete (Me P L) | Section design (Eurocode 2 [S130], ACI CODE-318-25 [S131]) · frames · — | Concrete damage plasticity; smeared cracking | Nonlinear concrete `Flag` without calibration | Hand calculations to the cited code | 7 · Nat |
| Soil, foundations and soil–structure interaction (P L) | Bearing capacity, impedance functions · Winkler springs · — | Mohr–Coulomb, hardening soil, Cam-clay; Biot consolidation; absorbing boundaries | `Flag` always: site data govern | Terzaghi; footing impedance | 7 · Nat |
| Seismic analysis (P L) | Equivalent lateral force · response spectrum · — | Nonlinear time history with fibre beam-columns; OpenSees as reference only (commercial use needs permission [S44]) | Collapse `Flag` | PEER NGA-West2 records [S86] | 7 · Nat |

### Marine and offshore

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Hydrostatics and stability (P L) | Metacentric height · righting-lever curves · — | Exact hydrostatics over B-rep or Implicit hulls | Quasi-static; tank free surfaces declared | Box barge | 7 · Nat |
| Resistance and propulsion (P L) | Holtrop–Mennen [S87] · open-water curves · — | RANS with VOF; body-force propellers | Froude and Reynolds range of the calibration | KCS [S88]; KVLCC2 [S89] | 7 · Nat |
| Seakeeping (P L) | Strip theory · — · response amplitude operators | Potential-flow BEM with Capytaine (Apache-2.0) reference [S42]; Cummins equations | Linear waves; slamming `Flag` | Floating sphere | 7 · Nat |
| Mooring and risers (L) | Catenary · lumped-mass lines · — | Nonlinear rods with Morison loads | Morison coefficients from data | Catenary | 7 · Nat |
| Marine fatigue and slamming (P L) | Spectral fatigue · — · — | Wave-scatter hot-spot fatigue; VOF slamming | Slamming `Flag` always | Hot-spot examples of DNV-RP-C203 [S132] | 7 · Nat |

### Aerospace

| Domain (scales) | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Phase · delivery |
| --- | --- | --- | --- | --- | --- |
| Low-speed aerodynamics and rotors (Me P L) | Thin airfoil · blade-element momentum, vortex lattice, panels · — | Vortex particle methods for rotors; RANS and DDES | Panels attached flow only | GP6 rotor thrust and torque | 4 · Nat |
| Transonic and supersonic (P L) | Shock-expansion · — · — | RANS and DG with shock capturing | Shock-induced separation `Flag` | ONERA M6, ATB [S1] | 6 · Nat |
| Hypersonics (P L) | Modified Newtonian · — · — | Nonequilibrium Navier–Stokes; DSMC where rarefied | `Flag` outside verified chemistry | Double cone [S90] | 7 · Ext |
| Aeroelasticity (P L) | Divergence formulas · — · doublet lattice with modal structure | p–k flutter; CFD aeroelasticity | Transonic dip needs CFD | AGARD wing 445.6 [S71] | 6 · Nat |
| Ice accretion (P L) | — · Messinger energy balance [S91] · — | Droplet impingement, surface energy balance, geometry update | `Flag` always: roughness and shedding are empirical | Icing Research Tunnel shapes used to validate LEWICE [S92] | 6 · Nat |
| Spacecraft thermal (P L) | Equilibrium temperature · radiative node networks · — | Ray-traced solar, albedo and planetary infrared | Optical properties at a declared mission life | Flat plate | 6 · Nat |
| Launch environments (P L) | Miles' equation · — · — | Random vibration and diffuse-field acoustics | Spectra from the launch provider | SDOF | 6 · Nat |
| Flight dynamics (P) | Stability derivatives · 6-DoF models · — | — | Table ranges `Refuse` | GP6 flight logs | 4 · Nat |

Flux owns multibody dynamics and rods (contract 7.1); MEC owns the assemblies and joints they read.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Solid, dynamics and durability models | `std::physics` models with envelopes and ladders | `ValidityError` per bound | COV-O-BENCH-1, COV-O-BENCH-2 | 1 to 5 per row |
| Member and strut buckling envelopes | Inelasticity and waviness regime variables with L0 rungs (D-COV-30) | Inelastic struts `Refuse` linear eigen-buckling | COV-O-BENCH-2 | 1 |
| Gear, bearing and shaft ratings (13.4) | L0 ratings and L2 tooth contact with margin Fields (D-COV-26) | Outside the rating's scope or lambda range: `Invalid` | COV-O-BENCH-10 | 2 |
| Composite and lattice models | Laminate, failure, short-fibre and lattice envelopes | `Invalid` near boundaries; `Flag` above the buckling bound | COV-O-BENCH-2 | 1 to 4 per row |
| Thermal and fluid models | Conduction to two-phase rows; turbulence closures, wall treatments and wall resolution | Correlations outside range `Refuse`; separation `Flag`; under-resolved walls Extrapolated | COV-O-BENCH-3 | 1 to 6 per row |
| Free surface and multiphase beyond mould filling (13.4) | Resolved and dispersed models with resolution envelopes | Under-resolved interfaces `Flag`; breakup per OOR-8 | COV-O-BENCH-8 | 5 |
| Electromagnetic and optical models | Static to full-wave rows | Non-causal fits rejected; EMC `Flag` | COV-O-BENCH-4 | 3 to 6 per row |
| Electrochemical models | Envelopes of ELX's and FLX's battery rows (13.4); degradation, runaway and corrosion models | Plating, degradation and abuse `Flag` | COV-O-BENCH-6 | 3 to 6 per row |
| Process models | State Fields and process envelopes | Uncalibrated machine or alloy: `Unassessed` | COV-O-BENCH-5 | 2 to 6 per row |
| Constitutive draping and cure (13.4) | Fibre-angle and cure-state Fields; spring-in stress | Shear above the locking angle: `Invalid` | COV-O-BENCH-9 | 5 |
| Particle, kinetics, molecular, plasma and transport domains | Flux operations, Wasm kinetics and External Ops | Host failure is a `Failure`; worker loss an Abort | COV-O-BENCH-7 | 5 to 7 |
| Later-phase domains | Biomechanics, MEMS, civil, marine, aerospace | Per row | COV-O-VAL-1 | 3 to 7 per row |

## Scope and limits

Contract section 13.1 sets the scope; COV records two scope decisions and the limit lists.

### Building products

Much of construction is manufactured products: facade units, modular pods, mass-timber connections, prefabricated steel.

**Decision D-COV-8:** Crucible designs and simulates building products and structures natively and exchanges with BIM through IFC 4.3 (ISO 16739-1:2024 [S45]), never authoring whole buildings. Steel structures and the IFC round trip land in phase 5 for GP8; timber, structural fire and building physics in phase 7 for GP14. *Why:* prefabricated building products have BOMs, while whole-building authoring is a different product that mature tools serve through an open standard. *Rejected:* full scope (duplicates BIM); none (abandons prefabrication). (revised in round 2)

### Chip layout and MEMS

IC physical design rests on NDA-bound process design kits and non-geometric abstractions, and OpenROAD (BSD-3) already runs RTL to GDSII with open PDKs [S46]. MEMS are mechanical devices defined by masks and process steps.

**Decision D-COV-9:** IC layout stays out of scope. Crucible exchanges GDSII and OASIS layers for MEMS, packaging and die-level analysis, and generates MEMS masks through a process-emulation package in phase 5 for GP7. *Why:* MEMS and chip packaging are physical design problems; logic layout is not. *Rejected:* an IC layout editor (wrong abstraction, NDA-bound data); no layout interop (blocks MEMS).

### Out of reach

These problems have no validated predictive method anywhere in October 2026; best practice is testing or calibration. Each is a record in `std::physics::limits`.

| Id | Problem | Why it is out of reach | Best available approach | Crucible behaviour | Categories affected |
| --- | --- | --- | --- | --- | --- |
| OOR-1 | DNS of turbulence at product scale | Cost scales as Re^2.91 [S14], about 800 times per tenfold Reynolds number | WMLES at Re^1.14 [S14]; RANS in design loops | `Refuse` above the a priori budget | Vehicles, aircraft, ships |
| OOR-2 | Wall-resolved LES of high-Reynolds external flow | Cost scales as Re^2.72 [S14] | WMLES with non-equilibrium wall models [S15] | Cost reported first | Vehicles, aircraft, ships |
| OOR-3 | Predictive RANS for smooth-body separation and corner flows | Equilibrium closures miss separation onset even in WMLES [S15]; a NASA CFD Vision 2030 goal [S17] | Scale-resolving simulation calibrated against tests | Separation `Flag`; model form inflated | Vehicles, aircraft, drones |
| OOR-4 | First-principles chemistry of whole products | A 1 kg aluminium part holds about 2×10^25 atoms | Continuum models with measured parameters; ML potentials [S31] | DFT and MD only as E1 provenance | All |
| OOR-5 | Long-horizon degradation without test data | Coupled mechanisms; uncontrolled time extrapolation | Accelerated tests with a declared acceleration model; Bayesian updates | `Extrapolated` to 3× the tested duration, `Invalid` beyond | Batteries, buildings, ships, medical |
| OOR-6 | Ductile fracture and composite failure | 13 teams disagreed in a blind round robin [S12]; composite theories miss tests [S13] | Building-block pyramids; conservative allowables | `Flag` | Vehicles, aircraft, fabrications |
| OOR-7 | Turbulent combustion, soot and emissions | Empirical turbulence–chemistry closures | Flamelet tables; rig calibration | `Flag` | Machines, vehicles, aircraft |
| OOR-8 | Atomization at engineering Weber numbers | Resolved cost grows as We^(12/5) [S16] | Lagrangian sprays with calibrated breakup | Breakup `Flag`; HPDC filling `Extrapolated` above the gate threshold | Castings, machines, vehicles |
| OOR-9 | Cavitation erosion, fretting, tribochemistry | Mechanisms span atomic to part scales | Indicators and tests | Indicators only | Mechanisms, ships, machines |
| OOR-10 | Chaotic trajectories beyond the predictability horizon | Sensitivity below floating-point resolution | Statistics with convergence error | Statistics; trajectories labelled | Every category with turbulent flow |
| OOR-11 | Individual-specimen life | Stochastic defects govern life | Probabilistic life; CT defect populations | Lives are distributions | Printed parts, castings, aircraft |
| OOR-12 | Patient-specific biological response | Inter-subject variability and adaptation | Population models | `Flag`; E4 only through V&V 40 [S8] | Medical |
| OOR-13 | Human behaviour and misuse | Not physics | Standards, user studies | Anthropometry only | Wearables, machines, medical |
| OOR-14 | Fire spread, explosions, runaway venting | Combustion, turbulence and fracture at extreme rates | Specialist tools and tests | Prescribed fire curves and runaway onset only | Batteries, buildings |
| OOR-17 | Site-scale geology, weather and climate loads | Site data govern | Site investigation; code loads | Site data imported with provenance | Buildings, ships |
| OOR-18 | Damping of assembled structures | Joint micro-slip varies with preload, wear and assembly | Modal testing; damping per joint class | Damping is a calibrated input | Mechanisms, fabrications, aircraft, spacecraft |
| OOR-19 | Friction and contact conductance from first principles | Surface chemistry, roughness and contamination dominate | Tests per pair | Pair data only; a missing pair is `Unassessed` | Mechanisms, machines, electronics |

### Out of scope

Mature specialist tools simulate these well; Crucible exchanges data with them.

| Id | Problem | Specialist practice | Crucible behaviour |
| --- | --- | --- | --- |
| OOS-1 (was OOR-15) | Semiconductor device physics and quantum devices | TCAD and quantum transport with process-specific calibration | Compact models, package thermal and stress only |
| OOS-2 (was OOR-16) | Nuclear criticality safety | Licensed codes with benchmark-validated nuclear data | Monte Carlo transport never decides a criticality check |
| OOS-3 | Superconducting magnets: quench, critical-state AC loss | Quench codes such as CERN's STEAM tools [S110] | Geometry, structure and cryogenic thermal native; superconducting behaviour exchanged as Fields |

**Decision D-COV-10:** Limits are two versioned `std` record lists that validity errors cite: `OutOfReach`, where no validated method exists, and `OutOfScope`, where mature external tools do. An entry moves or leaves only through an evidence-backed Proposal approved by humans. *Why:* limits must be as machine-readable as coverage, and calling specialist simulation impossible misstates the state of the art (R1-34). *Rejected:* documentation-only limits; one mixed list. (revised in round 2)

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Building products and IFC | Native design and analysis; IFC 4.3 through ECO | Content outside the product subset kept as Assets with a note | COV-O-VAL-1 | 5 steel, 7 timber |
| MEMS layout | GDSII and OASIS layers; process emulation | Unknown layer purposes reported per layer | COV-O-VAL-1 | 5 |
| Limit records | `OutOfReach` and `OutOfScope` entries cited by `NoCoveringModel` | Uncovered requests name an entry or the nearest package | COV-O-LIM-1 | 0 |

## Adding new physics

Coverage grows only through physics packages, std and third-party alike; ECO owns the registry, and COV contributes domain acceptance checks.

### Package contents

1. `PhysicsModel` records with domain tag, model level, required properties, outputs, envelope, calibration classes and precision class.
2. An implementation: an Ingot weak form (preferred), a Wasm component implementing `crucible:physics/solver`, or an External Op manifest (D-COV-12).
3. Regime-variable functions, with their transforms, for any new bounds.
4. Oracles: manufactured solutions, benchmarks and validation Evidence records by `ObjectId`.
5. An SPDX licence for code and a data licence for every dataset.

```
pub fn linear_elasticity() -> PhysicsModel {
    PhysicsModel {
        id: "std::physics::solid::linear_elasticity@4",
        level: ModelLevel::Full3d,
        precision: Precision::F32Safe,
        requires: [Material.elastic_stiffness],
        form: elasticity_form,
        calibration: ["elasticity.peak"],
        envelope: envelope {
            bound(equivalent_strain, max) { calibrated: 0.0..=0.005, extrapolated: 0.0..=0.02,
                outside: refuse, escalate_to: [solid::finite_strain_plasticity] }
            bound(homologous_temperature, max) { calibrated: 0.0..=0.3, extrapolated: 0.0..=0.4, outside: flag }
            assume("homogeneous at the smallest feature's scale")
            inflation: inflation::leave_one_out()
        },
        evidence: [oracle("COV-O-VER-1"), oracle("COV-O-BENCH-1")],
    }
}
```

The syntax is illustrative; ING defines it.

### Implementation routes

| Route | Use for | Limits |
| --- | --- | --- |
| Ingot weak form | Any variational PDE system, including parameter-domain forms (D-FLX-38); gets kernels, derivatives, estimators and caching | Methods without a weak form |
| Wasm component (`crucible:physics/solver`) | Monte Carlo, ray-tracing, BEM-kernel and Network methods | No clocks, files, network or raw GPU; randomness from KLN's streams |
| External Op | Large or copyleft codes: OpenFOAM (GPLv3 [S36]), LAMMPS (GPLv2 [S35]), SPARTA (GPL [S34]), OpenRadioss (AGPL-3.0 [S25]) | Untrusted-evaluation workers only; `SignOff` needs two agreeing runs (D-COV-12) |

**Decision D-COV-11:** Non-variational methods run their hot loops on general Flux operations: BVH traversal, neighbour lists, segmented reductions, counter-based random streams, fast multipole and hierarchical matrices. Method logic (collision laws, scattering kernels, source terms) lives in Ingot or a Wasm component. *Why:* these loops need GPUs, which Wasm components reach only through `crucible:ops/flux` (contract section 4). *Rejected:* one privileged in-tree solver per method; CPU-only Wasm solvers.

**Decision D-COV-12:** Large and copyleft solvers run as External Ops in single-use, egress-denied microVMs on untrusted-evaluation workers; results carry the host's class or `Unverified`. Gates and `SignOff` checks need two hosts to agree on the output `ObjectId` under signed receipts, or a policy allowance for a nondeterministic one (7.8). *Why:* GPL and AGPL code is never linked (7.7), untrusted code never runs beside attestation keys (R5-03), and a guest's own output claim proves nothing (R11-08). *Rejected:* linking copyleft solvers; dropping their domains; one untrusted run at `SignOff`. (revised in round 3)

**Decision D-COV-23:** `F32Safe` models may solve in `f32` on GPUs, with residuals and estimators evaluated in canonical CPU `f64` after readback; GPU-evaluated estimators are `Indicator` (FLX). `F64Required` models, including every circuit and device analysis, run only on CPU or `f64` server GPU classes, never in emulated `f64` on WebGPU. *Why:* SPICE tolerances lie below `f32` resolution (R1-39), and WGSL lets devices flush subnormals, breaking the error-free transformations double-float arithmetic needs [S68] (R7-13, R7-32). *Rejected:* `f32` execution with an added budget term; double-float emulation on WebGPU. (revised in round 3)

### Acceptance and review

1. **Static checks.** The registry rejects models lacking envelope, inflation, classes or precision class, bounds lacking basis, transform or computable variable (D-COV-18), and `Refuse` bounds without escalation.
2. **Oracle pass.** Registry CI runs the oracles in the canonical class and each targeted GPU class and assigns E0 to E2. E3 needs protected validation records the author's agents never see.
3. **Domain review.** A std package needs two human domain reviewers with no authorship stake, who confirm E2 literature zones and catalogue entries (D-COV-24). Third-party packages publish at any shown level.
4. **Use policy.** A design repository declares `min_evidence_level`; checks on models below it are `Undecided { reason: Flagged(EvidenceBelowPolicy) }`.
5. **Domain tags.** Namespaced; review merges duplicates.

Agents draft packages, oracles and envelope changes but never assign levels, merge widenings or approve reviews.

[[DIAGRAM diagrams/04-coverage-package-acceptance.jsx: physics package acceptance · checks, evidence levels and human review]]

The top row assigns E0 to E2 by automated checks; the bottom row adds protected validation for E3 and human review before publication.

**Decision D-COV-29:** From phase 6, with GP10, Crucible supplies a tool qualification kit for linear elasticity, modal analysis and laminates, extending contract 7.7's Computer Software Assurance package. It holds tool operational requirements, oracle evidence, known-problem lists and release impact notes; applicants qualify it per use, as under RTCA DO-330 [S133]. *Why:* qualification belongs to the applicant and the use, so a vendor supplies evidence (R7-43). *Rejected:* claiming qualified status; no kit.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Physics packages | Models with oracles and licences | Incomplete packages rejected with typed errors | COV-O-PKG-2 | 1 |
| Weak-form models | Compiled by Flux with derivatives and estimators | `FormError` at compile time (FLX) | COV-O-VER-1 | 1 |
| Solver Wasm components | `crucible:physics/solver` on `crucible:ops/flux` | Determinizer rejection | COV-O-BENCH-7 | 2 |
| External Op solvers | D-COV-12 | Host failure is a `Failure`; worker loss an Abort; disagreeing runs `Unverified` | COV-O-PKG-1 | 3 |
| Precision classes | `F32Safe` or `F64Required` (D-COV-23) | The plan places `F64Required` kernels on a CPU or `f64` class and says so | COV-O-PKG-3 | 1 |
| Use policy | `min_evidence_level` per repository | `Undecided { reason: Flagged(EvidenceBelowPolicy) }` | COV-O-VER-3 | 1 |
| Domain tags | Namespaced; duplicates merged | Duplicates rejected with the existing name | COV-O-PKG-2 | 1 |
| Tool qualification kit | Requirements, evidence, known problems and impact notes (D-COV-29) | A requirement without passing evidence blocks the kit | COV-O-VAL-3 | 6 |

## Materials system

A Material is a versioned, content-addressed record pinned in `ingot.lock`, so a property change never alters a design silently. `std::materials` ships the open library; licensed data arrive as External inputs and stay in the customer's private registry.

### Data model

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
    pub licence: DataLicence,                // joins Labels.licences (D-COV-15)
    pub certifications: Vec<Certification>,
    pub environment: Vec<EnvironmentalRecord>,
    pub microstructure: Option<MicrostructureDescriptor>,
}

pub struct Property {
    pub value: PropertyField,  // e.g. Field<(Temperature, StrainRate), Stress>
    pub basis: BasisSet,       // Typical; SpecLimit; A- and B-basis, lower and upper; Design { code, clause }
    pub uncertainty: Uncertainty, // D-COV-22
    pub coverage: PointSet,    // test conditions; zones as D-COV-25
    pub sources: Vec<SourceRef>,
}
```

**Decision D-COV-14:** Material properties are Fields over quantity-typed domains such as temperature and strain rate, and spatial variation enters only through state Fields on the Part. *Why:* one Field type covers temperature dependence, anisotropy and process-induced variation, composing as property(state Fields) → `Field<Body, V>`. *Rejected:* a separate "material curve" type; per-element material copies.

**Decision D-COV-13:** A property read returns `Approx<Q>` whose `input and tolerance` part is a `Guaranteed` basis enclosure, which Flux carries into solves as an input part. The basis defaults to specification limit, else B-basis, else an error, and ING's rule decides conservatively: `stress < 0.6 * sy` must hold at the lower basis. *Why:* a pure binding has one value, so round 2's read resolved by its consumer broke strict evaluation and checks of opposite sign (R9-13). *Rejected:* resolving reads by the consuming check (round 2); always the lower value (round 1); typical values by default. (revised in round 3)

14 CFR 25.613 requires design values covering 99% of the population with 95% confidence for single-load-path structure, and 90% for redundant structure [S51][S66]. CMH17 STATS computes these as A- and B-basis values [S114], and a designation's "nearest" equivalent never satisfies a specification check. Durability Materials carry a critical distance, Flux's smoothing radius for fatigue and fracture checks.

### Assignment and state

A Part's material assignment is a Material reference, an orientation `Field<Body, Rotation>` and state Fields: residual stress, plastic strain, porosity, fibre orientation, phase fractions, cure, damage. Process models write state Fields; without one, the as-specified condition applies and the assumption is recorded.

**Decision D-COV-27:** A property of the material in a stated condition is a COV `Material` property, even when the condition names a process and machine. A parameter of material and equipment together is an MFG process profile: melt-to-mould heat transfer, interfacial resistance, machine response, injection profiles, inherent-strain coefficients per machine. *Why:* one parameter needs one owner, and its test record shows whether it depends on equipment, as mould heat transfer does and rheology does not (R7-42). *Rejected:* ownership by domain, which duplicates melt rheology across processes.

Rheology, pvT, solidus and liquidus, fraction-solid curves, and cure and crystallization kinetics are therefore Material properties.

### Uncertainty

**Decision D-COV-22:** Material uncertainty is typed as `Aleatory { distribution, group }`, `Epistemic { interval }` or both, and correlation is declared only through named correlation groups across properties and Materials. Flux propagates intervals by nested sampling and reports probability boxes, never summed with distributions. *Why:* correlated inputs need groups for grouped Sobol indices and Shapley effects, and summing intervals with distributions overstates confidence (R1-36). *Rejected:* a free correlation matrix; one type for both kinds.

`std::uq` propagates input error by FLX's worst-case rule (D-FLX-35): adjoint-linearized bounds plus a Lanczos remainder, with `NonlinearResponse` above 20% asking for a statistical method. A basis enclosure already covers its property's aleatory scatter, so propagation covers the other properties and epistemic parts.

### Constitutive-model library

A `ConstitutiveModel` is an Ingot function or a Wasm component implementing `crucible:material/constitutive` (contract 7.4). It maps state, internal variables and time step to flux-like quantities and updated internal variables, and declares its thermodynamic structure, parameters, admissibility constraints and envelope. Kernel-IR models get tangents by algorithmic differentiation with `local_solve` (R1-25); opaque Wasm models supply tangents that FLX-O-FORM-3 verifies.

`std::materials::models` ships these families, by phase:

- **Phase 1.** Elastic: isotropic and anisotropic, temperature-dependent, small-strain thermoelastic. Thermal: Fourier conduction with mean-free-path curves, enthalpy phase change, emissivity spectra. Durability: S–N with mean stress, critical distances.
- **Phase 2.** Hyperelastic: Neo-Hookean, Mooney–Rivlin, Yeoh, Ogden, Arruda–Boyce, Gent, hyperfoam, Holzapfel–Gasser–Ogden. Plasticity: J2 with isotropic, Chaboche and Yoshida–Uemori hardening; Hill48; Yld2000-2d; Johnson–Cook; Zerilli–Armstrong; crushable foam; Drucker–Prager. Contact pairs: Coulomb and rate-and-state friction, contact conductance. Durability: ε–N.
- **Phase 3.** Viscoelastic: Prony with WLF and Arrhenius shifts, Bergström–Boyce. Creep and viscoplasticity: Norton–Bailey, Garofalo, theta projection, Perzyna, Chaboche. Damage and fracture: Lemaitre, Gurson–Tvergaard–Needleman, Johnson–Cook and Hosford–Coulomb loci, cohesive laws, phase-field energy. Magnetic: B–H splines, Jiles–Atherton, Preisach, Bertotti. Polymer melts and fluids: ideal gas, Peng–Robinson, CoolProp [S43], Cross–WLF, Carreau–Yasuda, Herschel–Bulkley, Oldroyd-B, Giesekus, Tait pvT, ARD-RSC closures, crystallization. Also moisture, NASGRO-form da/dN and Archard coefficients.
- **Phase 4.** Composites: ply elasticity and strength; Tsai–Wu, Hashin, Puck, LaRC05; continuum damage. Dielectric and optical: Debye, Cole–Cole, Lorentz–Drude, Sellmeier, Cauchy, measured BSDFs. Electrochemical: Butler–Volmer, hysteresis and multi-species multi-reaction potentials, concentration-dependent transport.
- **Phase 5.** Smart materials: linear piezoelectricity, superelastic shape-memory alloys.
- **Phase 7.** Concrete and geomaterials: concrete damage plasticity, Mohr–Coulomb, modified Cam-clay, hardening soil.

Admissibility oracles run before release: objectivity, non-negative dissipation, strong ellipticity or a positive-definite tangent over the envelope, convexity where required, causality and passivity. MFront behaviours are the largest open catalogue, under the GPL with a linking exception or CeCILL-A [S30][S67]. Their generated C++ becomes Wasm components once ECO's licence RFC accepts the exception (contract 7.7).

**Decision D-COV-28:** Industrial UMATs are ported, not wrapped: an agent-drafted Proposal translates each into an Ingot constitutive function with `local_solve`. The original runs in an External Op harness as the port's test oracle (COV-O-MAT-10). *Why:* an External Op per quadrature point costs a round trip per point per Newton iteration, while a port gets algorithmic tangents everywhere (R7-43). *Rejected:* wrapping UMATs as External Ops; Fortran-to-Wasm until a toolchain passes the same oracle.

### Calibration from test data

Calibration turns test records into a Material version through cached Ops.

1. **Ingest.** Records follow ISO 10303-235:2019, which covers measured values and who measured them [S53]. Signed rig measurements arrive as Evidence records citing method (such as ASTM E8/E8M [S134]), specimen, conditions and raw curves.
2. **Reduce.** True stress and strain, toe compensation and filtering, each a declared Op.
3. **Identify.** Least squares with gradients; finite-element model updating for non-uniform specimens; the virtual fields method for DIC data.
4. **Quantify.** Laplace approximation or seeded Markov chain Monte Carlo; correlations become correlation groups.
5. **Bound.** The test conditions form the property's `coverage`, with d_cal from their spacing; the calibrator declares the extrapolated region.
6. **Admit.** Admissibility oracles run over the whole envelope.
7. **Allowables.** With enough replicates, basis values come from one-sided tolerance limits per CMH-17 [S57] or MMPDS [S50].
8. **Publish.** The version enters a Proposal with fit residuals, held-out error, parameter uncertainty, envelope and inputs; overlap with validation data is rejected (13.1).

### Material databases and licensing

**Decision D-COV-15:** Every Material carries a typed `DataLicence` in its labels, whose terms for embedded values and derived results `api`, export and release checks enforce (contract 5). A connector publishes only after counsel's written review of its terms is recorded in its `DataLicence`. *Why:* licences differ sharply, shared designs must not leak licensed tables, and only counsel can read terms for derived results (contract 13.2). *Rejected:* tracking licences by hand; refusing licensed data; a propagation mechanism beside the label lattice. (revised in round 3)

| Source | Content | Licence (as verified) | Integration | Phase |
| --- | --- | --- | --- | --- |
| `std::materials` | Curated open library | Each value cites an open source | Built in | 1 |
| NIST Standard Reference Data | 49 free and 41 fee-based databases, including REFPROP and ICSD [S52] | Copyrighted under the Standard Reference Data Act; reproduction needs NIST's permission [S99] | Connector per database; fee-based ones need a customer licence | 3 |
| Materials Project | DFT properties of inorganic compounds | CC BY 4.0 downloads; no scraping; data "computed, and may not be accurate enough" [S54] | ICME connector; E1 at most | 5 |
| MMPDS | Allowables for aerospace metals and fasteners; MMPDS-2026 current [S50] | Purchased; a download licenses one simultaneous user [S100] | Customer-licensed connector | 6 |
| CMH-17 | Composite data, test and statistics guidance [S57] | Licensed; CMH17 STATS has a single-user licence [S114] | Customer-licensed connector | 6 |
| Ansys Granta MI | 250,000+ reference materials; MaterialUniverse environmental data [S49] | Commercial | Through the customer's Granta MI Scripting Toolkit [S102] | 5 |
| MatWeb | Datasheets | Terms forbid redistribution, mass export and collecting over 500 materials [S48] | None | — |
| Plastics databases (CAMPUS, UL Prospector) | Grades with rheology and pvT | CAMPUS: personal consultation, no machine interface [S103]; Prospector: internal use, no automated retrieval [S104] | None; users enter grades with their datasheets | 3 |
| CoolProp | Fluid properties | MIT [S43] | Built in | 3 |
| ICE embodied carbon | 200+ construction materials; V5.0 Educational, June 2026 | Educational use only; software needs the licensed IC+ dataset [S55] | IC+ connector | 5 |
| ecoinvent | Life-cycle inventory | A developer licence grants integration; users receive LCIA data only [S56] | Connector under a developer licence | 5 |

### Microstructure and ICME

A `MicrostructureDescriptor` records grain size distribution, texture, phase fractions, porosity and defects, fibre architecture and lattice cells, with measurement provenance. Each ICME link carries its own envelope, so a chain is as valid as its weakest link; chains are validated against AM-Bench data [S11].

| Link | Method | Delivery | Phase |
| --- | --- | --- | --- |
| Process to microstructure | Thermal histories into JMAK, Koistinen–Marburger, solidification maps | Nat | 6 |
| Microstructure to properties | Hall–Petch, rules of mixtures, Mori–Tanaka; FFT RVE solvers with crystal plasticity | Nat, Wasm | 5 |
| Thermodynamics | CALPHAD through customer-licensed tools or pycalphad (MIT) [S105] | Ext | 6 |
| Atomistic to continuum | DFT and ML-potential results as provenance (MACE [S31]; Materials Project [S54]) | Ext | 6 |
| Exchange with process tools | VMAP data-interface standard [S58] | Interop | 5 |

### Environmental data

An `EnvironmentalRecord` gives global warming potential per unit mass by life-cycle stage, embodied energy, water use, recycled content, recyclability and restricted substances. Each value carries geography, reference year, system boundary, method standard, source, licence and uncertainty. MFG owns product life-cycle assessment and passports.

Phase 2 ships what MFG's carbon and RoHS checks need: entered or supplier-declared factors and declared substances. Database connectors arrive in phase 5.

**Decision D-COV-16:** Environmental values follow the provenance, uncertainty and licence rules of mechanical properties, and an embodied-carbon check reports its boundary and year. *Why:* carbon numbers vary by source and boundary more than most mechanical properties do. *Rejected:* a single "CO2 per kg" number per Material.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Property Fields | Fields over state domains, declared interpolation | Reads outside `coverage` zoned, never clamped | COV-O-MAT-8 | 1 |
| Directional properties | Tensors in a material frame with a symmetry class | Ill-formed tensors rejected with the failing eigenvalue | COV-O-MAT-1 | 1 |
| Units | Every property a `Quantity<D>` | Compile error | COV-O-MAT-2 | 0 |
| Statistical basis | `Guaranteed` basis enclosures; reports name basis and deciding side (D-COV-13) | `MissingBasis { available }` | COV-O-MAT-6 | 1 |
| Uncertainty | Aleatory with groups; epistemic intervals | Input part `NotQuantified` | COV-O-ERR-1 | 2, 3 epistemic |
| Designations and certification | Equivalence basis; specification and lot-certificate links | "Nearest" fails specification checks; missing certificates fail release | COV-O-MAT-7 | 1, 3 certification |
| Constitutive library | `crucible:material/constitutive`; `local_solve` tangents | Inadmissible models rejected; `TangentInconsistent` | COV-O-MAT-1 | 1 to 7 per family |
| UMAT ports | Ingot port checked against the original (D-COV-28) | Rejected beyond 10⁻¹⁰ relative or on a failed Taylor test | COV-O-MAT-10 | 3 |
| Calibration | `calibrate(model, tests) -> (ConstitutiveBinding, CalibrationReport)`; inverse, full-field, model selection | Non-identifiable parameters reported with their null space | COV-O-MAT-3 | 2, 3 inverse, 5 DIC |
| Allowables | Replicates to A- and B-basis values | `InsufficientSamples { needed }` | COV-O-MAT-4 | 3 |
| Data licences | `DataLicence` in labels, with counsel's review per connector | Forbidden export or release refused, naming the licence | COV-O-MAT-5 | 3 |
| Connectors | External inputs pinned in `ingot.lock` | Fetch failure keeps the pinned version | COV-O-MAT-7 | 3 |
| Microstructure and ICME | Descriptors, state Fields, linked envelopes | Zoned by the weakest link | COV-O-BENCH-5 | 5, 6 |
| Environmental records | Boundary, year, source and licence per value | `BoundaryMismatch` when a check mixes boundaries | COV-O-MAT-9 | 2, 5 connectors |

## State of the art

Targets run on contract 13.3's reference laptop or a named GPU; copyleft leaders run only as External Ops. FLX's table covers numerical methods.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Validity and credibility | V&V 40-2018 [S8], NASA-STD-7009B [S9], FDA guidance (2023) [S10]; V&V 10 [S65], V&V 20 [S7] | Hand-written credibility assessments | Envelopes as checks; zone Fields; V&V 20 per response class | Target: a cited envelope on every std model before E2 |
| Code verification | Manufactured solutions; NAFEMS P18 [S2] | MSC Nastran 2021.01's verification manual [S5] | Manufactured solutions for every std form; all of P18 | P18 within 1% [S3][S4] |
| Contact | Mortar contact; Incremental Potential Contact [S26] | IPC Toolkit (MIT) [S26] | Mortar; IPC from phase 5 (FLX) | NAFEMS R0094 [S5]; Hertz peak within 1% |
| Fatigue | Multiaxial critical plane with probabilistic S–N | Ansys nCode DesignLife [S106] | Critical plane with basis-aware life distributions (OOR-11) | Target: 90% of held-out lives within a factor of 3 |
| Gear and bearing ratings | ISO 6336 and ISO 281 ratings with loaded tooth contact analysis | KISSsoft, rating to ISO, DIN, AGMA and VDI standards [S113] | D-COV-26 | Worked examples to 3 significant figures |
| Fracture | Phase field, cohesive zones, calibrated ductile damage | Sandia Fracture Challenge entrants [S12] | Cohesive and phase-field defaults; ductile `Flag` | Sandia data [S12]; target: enter the next blind round |
| Composite failure | Building-block calibration of LaRC05 and Puck | Theories assessed in WWFE-II [S13] | Calibrated criteria library; progressive failure `Flag` | WWFE-II [S13]; GP10 pyramid |
| Turbulence models | SA, SST, GEKO and transition per NASA TMR [S1] | SU2 (LGPL-2.1) [S37]; OpenFOAM (GPLv3) [S36] | Native, on TMR definitions | Reference codes' finest-grid spread [S1] |
| Scale-resolving CFD | GPU high-order DG and flux reconstruction; non-equilibrium wall models [S15] | PyFR (BSD) [S27]; Trixi.jl (MIT) [S28] | Entropy-stable DG on Flux GPUs | 2DWMH [S1]; target: cost per DOF per stage within 1.5× of PyFR |
| Multiphase | VOF, level set, phase field; k_max·η_KH ≥ 60 [S16] | Basilisk's geometric VOF (GPL-3.0) [S107] | Native, with a priori resolution | Interfacial statistics converge [S16] |
| Rarefied gas | DSMC | SPARTA (GPL) [S34] | External Op; native slip | Microchannel analytic; code-to-code |
| Electromagnetics | Nédélec FEM with Newton on B–H; high-order FEM with model reduction | Palace (Apache-2.0) [S18] | Native | TEAM 7 and 13 probes within 5% [S6]; eigenfrequencies within 0.1% of Palace |
| Optics | Differentiable spectral, polarized Monte Carlo transport | Mitsuba 3 [S39] | Native on Flux BVH operations | Target: equal-noise time within 2× of Mitsuba 3 |
| Batteries | DFN with thermal coupling; MSMR OCV [S61] | PyBaMM (BSD-3) [S19][S20] | Native ladder to DFN | Within 1 mV RMS of PyBaMM; target: 10× faster sweeps |
| Fibre orientation | Anisotropic rotary diffusion with reduced strain closure [S83][S84] | Autodesk Moldflow, on Folgar–Tucker [S109] | ARD-RSC; Folgar–Tucker as L0 | GP5 short shots and warpage |
| Chemical kinetics | Detailed mechanisms in reactor networks and 1D flames | Cantera (BSD-3) [S21][S22] | Wasm component reading Cantera's YAML mechanisms [S108] | Target: equilibrium and ignition delay within 0.1% |
| Atomistic | Equivariant machine-learned potentials | MACE (MIT code; model licences vary) [S31]; LAMMPS (GPLv2) [S35] | External Ops; results as provenance | Elastic constants within the model's published error |
| Plasma and radiation | Particle-in-cell (WarpX, 2022 Gordon Bell Prize [S33]); Monte Carlo [S23][S24] | The same codes | External Ops | Analytic cases; code-to-code |
| Biomechanics | Fibre-reinforced hyperelastic FE; musculoskeletal optimal control | FEBio (MIT) [S40]; OpenSim (Apache-2.0) [S41] | Native FE; Wasm musculoskeletal models | Code-to-code with FEBio |
| Seakeeping | Potential-flow BEM with Cummins time domain | Capytaine (Apache-2.0) [S42] | Native BEM on Flux fast multipole | Target: added mass and damping within 1% |
| Additive process | Inherent strain, part-scale thermo-mechanics, melt-pool CFD | AM-Bench blind-challenge entrants [S11] | Native | COV-O-BENCH-5 |
| Constitutive authoring | Domain-specific languages generating integration code | MFront 5.2 (GPL with a linking exception, or CeCILL-A) [S30][S67] | Ingot behaviours with `local_solve`; MFront import as Wasm | Stress updates within 10⁻¹⁰ relative of MFront tests |
| Materials data | Data management with traceable tests | Ansys Granta MI [S49] | Versioned records; licences in labels | ISO 10303-235 round trip [S53] |
| Allowables | One-sided tolerance limits per CMH-17 and MMPDS [S57][S50] | CMH17 STATS, which incorporates STAT17 [S101][S114] | Native, with `InsufficientSamples` | Worked examples to 3 significant figures |

## Platform notes

- **Double precision on GPUs.** WGSL has no `f64`, makes `f16` an extension and lets implementations flush subnormals [S29][S68]. An Apple WebGPU engineer said Metal-based implementations would not offer `f64` [S59], so D-COV-23 keeps `F64Required` models off WebGPU.
- **Browser memory.** Wasm memory64 is not on every engine [S60]. Browser sessions follow PLT's browser memory table (contract 9), and remote results are canonical.
- **Relaxed SIMD.** It ships in Chrome 114 and Firefox 145 and behind a flag in Safari [S60]. Its results vary by hardware, so `Portable` physics never uses it.
- **External Ops.** They run on Linux untrusted-evaluation workers, reached remotely from every client; air-gapped installs need a local Linux worker (contract 9).
- **Monte Carlo determinism.** Particle and transport methods draw from KLN's `OpCx::rng` streams, keyed without class, fidelity or names, and reduce in fixed order.
- **Zones and data.** Canonical zones are identical everywhere, and other classes report `NearBound` regions (R1-45). Connectors fetch only at import time, so builds run air-gapped.

## Interfaces with other subsystems

### What COV provides

| To | What COV provides | Types |
| --- | --- | --- |
| FLX | Physics and constitutive models; envelopes and regime functions for `flux::validity_zones`; the model-to-class map; critical distances; D-COV-11's operation needs | `Field`, `Material`, `ValidityEnvelope` |
| ING | `std::physics` and `std::materials`; record syntax needs; basis enclosures (D-COV-13) | Ingot packages |
| KLN | Envelope and Material records as CAS inputs; calibration Ops; External Op keys; `DataLicence` values; Material composition for compliance | `Op`, `Labels`, `Material` |
| `repo` | Material versions; validity, certification and licence release checks; the allowance catalogue | `Material`, `CheckOutcome` |
| AGT and `api` | Coverage map; limit records; envelopes; `ValidityError`s with escalation | Read and Inspect methods |
| UIX | Zone Fields with assumptions; model-form parts; basis citations; escalations | `Field<Body, ValidityZone>` |
| MEC | Materials; solid, contact, joint, fatigue, buckling and dynamics models; gear, bearing and shaft ratings; constitutive draping (13.4) | `Material`, `PhysicsModel` |
| MFG | Process models and envelopes; state Fields; strut-scale Materials from its calibration; environmental records; gear, bearing and shaft ratings | `Field`, `ValidityEnvelope`, `EnvironmentalRecord` |
| ELX | Dielectric, copper, magnetic and cell Materials; electromagnetic, thermal and electrochemical models, including refit LFP hysteresis; precision classes | `PhysicsModel`, `Material` |
| ECO | Domain acceptance checks; semantics of `crucible:physics`, `crucible:material`, MatML and OpenFOAM cases | Package |
| PLT | Precision classes per model; External Op worker needs | Model metadata |

### What COV requires

| From | Requirement |
| --- | --- |
| FLX | Forms and solvers; estimators, η99 tables and class envelopes; refinement confirmation; eigenvalue DWR; Koiter coefficients (phase 2); solution verification; `flux::validity_zones`; coupling; IPC (phase 5); `std::uq`; D-COV-11's operations |
| ING | Records, enums and `Range`; typed regime functions; `require`; `CheckOutcome` with `conditional_on`; the `Truth` decision rule over basis enclosures |
| KLN | Deterministic calibration; External Op receipts; label joins; Evidence record lookup; `OpCx::rng` |
| `repo` | Waiver records (contract 2); envelope approvals; policy allowances; `min_evidence_level` |
| ECO | The registry and publish pipeline; package metadata; IFC 4.3, GDSII, OASIS, MatML and ISO 10303-235 codecs; the MFront licence RFC |
| ANV | Implicit and lattice Bodies; mid-surfaces, including minimal-surface zero sets; member axes; curvature and thickness queries |
| MEC | Plies and kinematic draping; gear records with accuracy grade and load spectrum; which mechanical checks need calibrated classes |
| MFG | Process setups and profiles (D-COV-27); as-built strut calibration (13.4); weld coupons per joint type; the Hele-Shaw solver |
| ELX | Cells, swelling, abuse mechanics and packs (13.4); the electrical use of physics models |
| PLT | `linalg`; `f64` availability per class; the browser memory table |

## Oracles

Oracles live in the protected `oracles/cov/`; held-out validation Evidence records live in a store agents never see.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| COV-O-MAP-1 | Coverage map | Rows match package metadata; `Planned` rows never counted |
| COV-O-VER-1 | Manufactured solutions for every std weak form | Observed order within 0.1 of the declared order over three refinements, until the error falls below 10³ times round-off |
| COV-O-VER-2 | Model ladders (D-COV-2) | Adjacent rungs agree within the narrower rung's declared tolerance at every test point |
| COV-O-VER-3 | Evidence levels and use policy | Only CI-signed results change levels; agent credentials cannot; below-policy models give `Undecided` |
| COV-O-VER-4 | Solution-verification status | On the labelled corpus, no `None` status or uncalibrated band decides a `SignOff` check |
| COV-O-ERR-1 | Input propagation | Mean and variance within 2% of a high-sample reference; epistemic inputs as probability boxes, never summed |
| COV-O-ERR-2 | Calibration classes | Every `Estimated` estimator of a std model names a class with entry and envelope; a removed entry or a result outside the envelope gives `Indicator` |
| COV-O-ERR-3 | Conditional passes and allowances | Labelled E2 cases give `Pass { conditional_on: [ModelForm] }`, `Undecided` at a gate without an allowance, a re-evaluated verdict with one; unconfirmed or resistance-only entries never cover |
| COV-O-VAL-1 | Golden-product validation | Every gauged measurement of every article lies within the prediction ± its total budget, in Calibrated zones |
| COV-O-VAL-2 | Model form, zone geometry and inflation | On synthetic known-error cases, bounds and g(d) cover at the declared confidence; zones exact; unvalidated classes `NotQuantified`; calibration and validation data disjoint |
| COV-O-VAL-3 | Tool qualification kit | Every requirement traces to a passing oracle result of the release; known problems and impact notes per release |
| COV-O-ENV-1 | Envelope completeness | Every model has envelope, transforms, inflation, classes and precision class; every bound a basis; every `Refuse` bound an escalation (exact) |
| COV-O-ENV-3 | Zones across classes | Canonical zones identical on golden models; others differ only inside `NearBound` bands |
| COV-O-ENV-4 | `Refuse` behaviour | Dependent checks blocked; `OutsideEnvelope` with fixes (exact) |
| COV-O-ENV-5 | Waivers and widening | Agents cannot create Waiver records or merge widenings; `Refuse` zones take no Waiver (exact) |
| COV-O-ENV-6 | Regime computability and missing inputs | Every variable resolves to a typed function; a missing input gives `Extrapolated` with a default, else `Unassessed` |
| COV-O-ENV-7 | Surrogate envelopes | Out-of-distribution queries Extrapolated or Invalid; CMA-ES with 10⁴ seeded evaluations per surrogate (FLX-O-ROM-2) finds no surrogate `SignOff` `Pass` the full solve fails |
| COV-O-ENV-8 | Coupling envelopes | One-way coupling `Invalid` on labelled flutter-prone, light-panel and heavy-fluid cases; valid on controls |
| COV-O-BENCH-1 | NAFEMS P18 LE, FV and T benchmarks | Within 1% of reference values |
| COV-O-BENCH-2 | NAFEMS R0024, R0027, R0094, R0020 and R0031; lattices; struts | Published values within 2%, limit loads and lives within 5%; Hertz peak pressure within 1%; lattice tensors within 1% of full-resolution cells; labelled inelastic struts `Refuse` |
| COV-O-BENCH-3 | NASA TMR and thermal-fluid references | Within the reference codes' finest-grid spread; analytic cases within 1% |
| COV-O-BENCH-4 | TEAM 7, 13 and 36; optical references | Within published measurement uncertainty |
| COV-O-BENCH-5 | AM-Bench blind predictions and process references | Inside measurement uncertainty for at least 80% of entered quantities; analytic process cases within 2% |
| COV-O-BENCH-6 | Battery ladder | SPM, SPMe and DFN within 5 mV at C/20; DFN within 1 mV RMS of PyBaMM; refit LFP hysteresis within 10 mV RMS of measured cycles |
| COV-O-BENCH-7 | Particle, kinetics, molecular, plasma and transport domains | Each row's State of the art target, else within 2% or three standard errors of the reference |
| COV-O-BENCH-8 | Free surface and multiphase | Dam-break front and bubble rise velocity within 2% [S78][S77]; interfacial statistics converge [S16]; volume conserved to solver tolerance |
| COV-O-BENCH-9 | Constitutive draping and cure | Shear angles within 2° of frame and bias tests; degree of cure within 0.02 of DSC; spring-in within 0.2° |
| COV-O-BENCH-10 | Gear, bearing and shaft ratings | Standards' worked examples to 3 significant figures; tooth contact within 5% of mortar contact on GP3's root stress and transmission error |
| COV-O-LIM-1 | Limit records | Every `NoCoveringModel` error cites a limit record; records change only through approved Proposals |
| COV-O-PKG-1 | External Op agreement and placement | Two hosts agree on output `ObjectId`s under signed receipts, else `Unverified`; never on trusted builders |
| COV-O-PKG-2 | Package acceptance | Seeded incomplete packages get the right typed error; std packages need two non-author reviewers |
| COV-O-PKG-3 | Precision classes | No `F64Required` kernel in an `f32` or emulated-`f64` class; `F32Safe` residuals and estimators in CPU `f64` |
| COV-O-MAT-1 | Admissibility and tangents | Admissibility over each envelope (exact or 10⁻¹² relative); Taylor tests per FLX-O-FORM-3 |
| COV-O-MAT-2 | Units | Every property dimension-checks; affine temperatures handled (compile time) |
| COV-O-MAT-3 | Calibration recovery | Known parameters recovered from noisy synthetic data; 95% intervals cover within 2 points of nominal |
| COV-O-MAT-4 | Allowables | Published worked examples reproduced to 3 significant figures |
| COV-O-MAT-5 | Licence propagation | Exporting embedded licensed values fails; derived results export where the terms allow (exact) |
| COV-O-MAT-6 | Basis enclosures | One binding feeding checks of opposite sign decides each at its conservative end; sign-varying solves evaluate both ends |
| COV-O-MAT-7 | Records, designations, certification, connectors | Lossless ISO 10303-235 round trip; "nearest" fails specification checks; no fetch in evaluation |
| COV-O-MAT-8 | Property Fields | Exact at tabulated nodes; monotone where declared; out-of-coverage reads zoned, never clamped |
| COV-O-MAT-9 | Environmental records | Every value carries source, boundary and year; carbon checks report them; mixed boundaries fail |
| COV-O-MAT-10 | UMAT ports | Stress updates within 10⁻¹⁰ relative of the original over the calibrated envelope; Taylor tests pass |

## Phasing

Shared phases follow contract 13.4, and each matrix row lists its phase. Golden products 7 to 16 start only with a test partner and an approved plan (13.1).

| Phase | COV's contribution to the gate |
| --- | --- |
| 0 | Envelope schema; regime variables with transforms; evidence levels; Material records and units; the coverage map; limit records |
| 1 | GP1 and GP2: immersed linear elasticity and the beam-lattice model at E3 from the proof loads; four calibration classes; strut buckling envelopes and strut-scale Materials; basis enclosures; the allowance catalogue |
| 2 | GP3 and GP4: gear, bearing and shaft ratings; weld distortion from coupons at E3; inherent strain for metal powder bed fusion; environmental records with generic factors |
| 3 | GP5: moulding with the Hele-Shaw envelope, laminar conjugate heat transfer and drop; warpage and drop models at E3 |
| 4 | GP6: models validated by flight, dynamometer and thermal tests |
| 5 | GP7 MEMS, GP8 steel platform with the IFC structural check, GP9 crash box |
| 6 | GP10 wing box with the tool qualification kit, GP11 CubeSat, GP12 battery sub-pack |
| 7 | GP13 hull, GP14 timber pavilion, GP15 bone plate with its V&V 40 package, GP16 sewn pack |

## Open questions

1. **Strut waviness threshold.** D-COV-30's `Flag` value comes from the first as-built calibration build (13.4) and cannot be set before that build is measured.
2. **Sheet lattices in GP2.** If the phase 0 gate fixes GP2 with sheet cells, mid-surface shells for sheet lattices move to phase 1. The GP2 record in contract 13.1 decides it.
3. **Gear and bearing envelope limits.** The lambda-ratio and temperature limits come from each standard's scope, which needs the licensed editions (MEC open question 1).
4. **Findings applied in part.**
    - R7-01: class envelopes and α here; the adversarial corpus and refinement confirmation are FLX's and contract 7.1's.
    - R7-05, R7-11, R7-13, R7-15, R7-21, R7-24: one-line consequences; FLX owns the eigenvalue estimator, patch rule, GPU readback, smoothing radius, GCI calibration and surrogate bound.
    - R7-06, R7-20, R7-25: envelopes, Materials and phases here; FLX owns Koiter coefficients and joint loads, MFG the calibrations, ANV the implicit mid-surface.
    - R7-09, R7-29: regime variables here; FLX owns the plan rules, MFG GP5's cell count and the Hele-Shaw solver.
    - R7-16: four phase 1 classes, not five, since one immersed treatment serves both fidelities (R7-17) and inherent strain left phase 1.
    - R7-19, R10-18: rating rows here; the accuracy grade and drawing data table are MEC's.
    - R7-26: COV's oracles; FLX's are FLX's.
    - R9-09, R9-15, R9-23, R9-28, R11-08: pointers to KLN, contract 2, contract 5, FLX's operation and contract 7.8.
    - Round 2's partial applications stand (R1-32, R1-33, R1-36, R1-39, R1-40, R1-41, R1-54, R3-55).

## Contract change requests

None. CCR-COV-9 (model level and evidence level in the glossary) was accepted in contract v5 (section 2).

## Sources

All pages were opened in October 2026. Licence statements reflect the pages as read and are not legal advice.

- [S1] NASA Turbulence Modeling Resource, verification and validation cases and model list: https://tmbwg.github.io/turbmodels/
- [S2] NAFEMS, *The Standard NAFEMS Benchmarks* (P18): https://www.nafems.org/publications/resource_center/p18/
- [S3] ESRD, benchmarks guide to the standard NAFEMS linear elastic tests: https://www.esrd.com/download/benchmarks-guide-standard-nafems-benchmarks-linear-elastic-tests-pdf/
- [S4] FeenoX mechanical examples (NAFEMS LE1, LE10, LE11): https://www.seamplex.com/feenox/examples/mechanical.pdf
- [S5] NAFEMS code verification, MSC Nastran benchmark sets: https://nafems.org/publications/code-verification/nastran-code-verification
- [S6] Compumag TEAM problems: https://www.compumag.org/wp/team/
- [S7] ASME V&V 20-2009 (R2021): https://www.asme.org/codes-standards/find-codes-standards/standard-for-verification-and-validation-in-computational-fluid-dynamics-and-heat-transfer
- [S8] ASME V&V 40-2018: https://www.asme.org/codes-standards/find-codes-standards/assessing-credibility-of-computational-modeling-through-verification-and-validation-application-to-medical-devices
- [S9] NASA-STD-7009B: https://standards.nasa.gov/standard/NASA/NASA-STD-7009
- [S10] FDA, *Assessing the Credibility of Computational Modeling and Simulation in Medical Device Submissions* (November 2023): https://www.fda.gov/regulatory-information/search-fda-guidance-documents/assessing-credibility-computational-modeling-and-simulation-medical-device-submissions
- [S11] NIST AM-Bench: https://www.nist.gov/ambench
- [S12] Boyce et al., "The Sandia Fracture Challenge: blind round robin predictions of ductile tearing", *Int. J. Fracture* 186 (2014): https://link.springer.com/article/10.1007/s10704-013-9904-6
- [S13] R. M. Christensen, critique of the World-Wide Failure Exercise II: https://failurecriteria.com/theworldwidefail.html
- [S14] Yang and Griffin, "Grid-point and time-step requirements for direct numerical simulation and large-eddy simulation": https://arxiv.org/abs/2010.15307
- [S15] Agrawal, Bose and Moin, non-equilibrium wall model for smooth-body separation (2024): https://arxiv.org/abs/2407.11390
- [S16] Hatashita, Nathan and Jain, "Scalings and simulation requirements in two-phase flows" (2025): https://arxiv.org/abs/2510.07727
- [S17] Slotnick et al., *CFD Vision 2030 Study*, NASA/CR-2014-218178: https://ntrs.nasa.gov/citations/20140003093
- [S18] Palace: https://github.com/awslabs/palace
- [S19] PyBaMM: https://github.com/pybamm-team/PyBaMM
- [S20] Sulzer et al., "Python Battery Mathematical Modelling (PyBaMM)", *J. Open Research Software* 9 (2021): https://openresearchsoftware.metajnl.com/articles/10.5334/jors.309
- [S21] Cantera: https://github.com/Cantera/cantera
- [S22] Cantera licence: https://raw.githubusercontent.com/Cantera/cantera/main/License.txt
- [S23] OpenMC: https://github.com/openmc-dev/openmc
- [S24] Geant4 software licence: https://geant4.web.cern.ch/download/license
- [S25] OpenRadioss: https://github.com/OpenRadioss/OpenRadioss
- [S26] IPC Toolkit: https://github.com/ipc-sim/ipc-toolkit
- [S27] PyFR: https://github.com/PyFR/PyFR
- [S28] Trixi.jl: https://github.com/trixi-framework/Trixi.jl
- [S29] W3C, WebGPU Shading Language: https://www.w3.org/TR/WGSL/
- [S30] MFront and TFEL: https://thelfer.github.io/tfel/web/index.html
- [S31] MACE: https://github.com/ACEsuit/mace
- [S32] Project Chrono: https://github.com/projectchrono/chrono
- [S33] WarpX: https://github.com/BLAST-WarpX/warpx
- [S34] SPARTA: https://sparta.github.io/
- [S35] LAMMPS open-source licence: https://docs.lammps.org/Intro_opensource.html
- [S36] OpenFOAM licence: https://openfoam.org/licence/
- [S37] SU2: https://github.com/su2code/SU2
- [S38] XLB: https://github.com/Autodesk/XLB
- [S39] Mitsuba 3: https://github.com/mitsuba-renderer/mitsuba3
- [S40] FEBio: https://github.com/febiosoftware/FEBio
- [S41] OpenSim: https://github.com/opensim-org/opensim-core
- [S42] Capytaine: https://github.com/capytaine/capytaine
- [S43] CoolProp: https://github.com/CoolProp/CoolProp
- [S44] OpenSees copyright: https://opensees.berkeley.edu/OpenSees/copyright.php
- [S45] buildingSMART, IFC schema specifications: https://technical.buildingsmart.org/standards/ifc/ifc-schema-specifications/
- [S46] OpenROAD: https://github.com/The-OpenROAD-Project/OpenROAD
- [S47] ANSUR II: https://www.openlab.psu.edu/ansur2/
- [S48] MatWeb terms of use: https://www.matweb.com/reference/terms.aspx
- [S49] Ansys Granta MI: https://ansys.synopsys.com/products/materials/granta-mi
- [S50] MMPDS: https://www.mmpds.org/
- [S51] 14 CFR 25.613: https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-25/subpart-D/subject-group-ECFR6bf0df4e8d5f12e/section-25.613
- [S52] NIST Standard Reference Data: https://www.nist.gov/srd
- [S53] ISO 10303-235:2019: https://www.iso.org/standard/74409.html
- [S54] Materials Project terms of use (legacy site): https://legacy.materialsproject.org/terms
- [S55] Circular Ecology, ICE database: https://circularecology.com/embodied-carbon-footprint-database.html
- [S56] ecoinvent licences: https://ecoinvent.org/offerings/licences/
- [S57] CMH-17: https://www.cmh17.org/
- [S58] VMAP Standards Community: https://www.vmap-standard.org/
- [S59] M. Maxfield, public-gpu mailing list on f64 in WebGPU (April 2022): https://lists.w3.org/Archives/Public/public-gpu/2022Apr/0006.html
- [S60] WebAssembly feature status data: https://raw.githubusercontent.com/WebAssembly/website/main/features.json
- [S61] PyBaMM documentation, lithium-ion models (SPM, SPMe, DFN, MSMR): https://docs.pybamm.org/en/latest/source/api/models/lithium_ion/index.html
- [S62] PyBaMM documentation, open-circuit potential submodels (including one-state hysteresis): https://docs.pybamm.org/en/latest/source/api/models/submodels/interface/open_circuit_potential/index.html
- [S63] PyBaMM documentation, particle mechanics submodels (swelling, crack propagation): https://docs.pybamm.org/en/latest/source/api/models/submodels/particle_mechanics/index.html
- [S64] European Commission JRC, Eurocode 5 parts, including EN 1995-1-2:2004 structural fire design: https://eurocodes.jrc.ec.europa.eu/EN-Eurocodes/eurocode-5-design-timber-structures
- [S65] ASME V&V 10-2019 (R2025), *Standard for Verification and Validation in Computational Solid Mechanics*: https://www.asme.org/codes-standards/find-codes-standards/standard-for-verification-and-validation-in-computational-solid-mechanics
- [S66] 14 CFR 25.613, material strength properties and design values (Cornell LII): https://www.law.cornell.edu/cfr/text/14/25.613
- [S67] TFEL/MFront, GNU GPL licence text with the linking exception: https://raw.githubusercontent.com/thelfer/tfel/master/LICENCE-GNU-GPL
- [S68] WebGPU conformance test suite, floating-point primer: https://kdab.searchfox.org/firefox-main/source/dom/webgpu/tests/cts/checkout/docs/fp_primer.md
- [S69] Turek and Hron, "Proposal for numerical benchmarking of fluid-structure interaction between an elastic object and laminar incompressible flow", in *Fluid-Structure Interaction*, LNCSE (Springer, 2006), Crossref record: https://api.crossref.org/works/10.1007/3-540-34596-5_15
- [S70] PyBaMM documentation, battery model options (lumped, x-lumped and x-full thermal): https://docs.pybamm.org/en/latest/source/api/models/base_models/base_battery_model.html
- [S71] Yates, *AGARD Standard Aeroelastic Configurations for Dynamic Response I: Wing 445.6*, NASA-TM-100492 (1987), NTRS record: https://ntrs.nasa.gov/api/citations/search?q=AGARD+standard+aeroelastic+configurations+dynamic+response+445.6+wing
- [S72] Hamrock and Dowson, "Isothermal elastohydrodynamic lubrication of point contacts, Part III: fully flooded results", *J. Lubrication Technology* 99 (1977), Crossref record: https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Hamrock+Dowson+Isothermal+elastohydrodynamic+lubrication+of+point+contacts+film+thickness
- [S73] Finnie, "Erosion of surfaces by solid particles", *Wear* 3 (1960), Crossref record: https://api.crossref.org/works?query.bibliographic=Finnie+Erosion+of+surfaces+by+solid+particles+Wear+1960&rows=3
- [S74] Risch and Kostyk, "Test case baseline results", 5th Ablation Workshop (2012), NTRS record: https://ntrs.nasa.gov/api/citations/20120011414
- [S75] Ghia, Ghia and Shin, "High-Re solutions for incompressible flow using the Navier-Stokes equations and a multigrid method", *J. Comput. Phys.* 48 (1982), Crossref record: https://api.crossref.org/works?query.bibliographic=Ghia+Shin+High-Re+solutions+incompressible+flow+Navier-Stokes+multigrid+1982&rows=3
- [S76] Brachet et al., "Small-scale structure of the Taylor–Green vortex", *J. Fluid Mech.* 130 (1983), Crossref record: https://api.crossref.org/works?query.bibliographic=Brachet+Small-scale+structure+of+the+Taylor-Green+vortex&rows=2&select=DOI,title,author,container-title,volume,page,issued
- [S77] Hysing et al., "Quantitative benchmark computations of two-dimensional bubble dynamics", *Int. J. Numer. Meth. Fluids* 60 (2009), Crossref record: https://api.crossref.org/works?query.bibliographic=Hysing+Quantitative+benchmark+computations+of+two-dimensional+bubble+dynamics&rows=3
- [S78] Martin and Moyce, "An experimental study of the collapse of liquid columns on a rigid horizontal plane", *Phil. Trans. R. Soc. A* 244 (1952), Crossref record: https://api.crossref.org/works?query.bibliographic=Martin+Moyce+collapse+of+liquid+columns+on+a+rigid+horizontal+plane&rows=3
- [S79] Alves, Oliveira and Pinho, "Benchmark solutions for the flow of Oldroyd-B and PTT fluids in planar contractions", *J. Non-Newtonian Fluid Mech.* 110 (2003), Crossref record: https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Alves+Oliveira+Pinho+Benchmark+solutions+for+the+flow+of+Oldroyd-B+and+PTT+fluids+in+planar+contractions
- [S80] TNF Workshop, Sandia/TUD piloted CH4/air jet flames data archive: https://tnfworkshop.org/data-archives/pilotedjet/ch4-air/
- [S81] Robinson et al., "Analytical formulation for the shielding effectiveness of enclosures with apertures", *IEEE Trans. EMC* 40 (1998), Crossref record: https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Robinson+Analytical+formulation+for+the+shielding+effectiveness+of+enclosures+with+apertures
- [S82] Hariharan et al., "Multilaboratory particle image velocimetry analysis of the FDA benchmark nozzle model", *J. Biomech. Eng.* 133 (2011), Crossref record: https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Hariharan+Multilaboratory+particle+image+velocimetry+analysis+of+the+FDA+benchmark+nozzle+model
- [S83] Phelps and Tucker, "An anisotropic rotary diffusion model for fiber orientation in short- and long-fiber thermoplastics", *J. Non-Newtonian Fluid Mech.* 156 (2009), Crossref record: https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Phelps+Tucker+An+anisotropic+rotary+diffusion+model+for+fiber+orientation+in+short-+and+long-fiber+thermoplastics
- [S84] Wang, O'Gara and Tucker, "An objective model for slow orientation kinetics in concentrated fiber suspensions", *J. Rheol.* 52 (2008), Crossref record: https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Wang+O%27Gara+Tucker+An+objective+model+for+slow+orientation+kinetics+in+concentrated+fiber+suspensions
- [S85] Green, "Description of Numisheet 2005 Benchmark #3", *AIP Conf. Proc.* 778 (2005), Crossref record: https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=NUMISHEET+2016+benchmark
- [S86] PEER Ground Motion Database, NGA-West2: https://ngawest2.berkeley.edu/
- [S87] Holtrop and Mennen, "An approximate power prediction method", *International Shipbuilding Progress* 29 (1982), Crossref record: https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Holtrop+Mennen+An+approximate+power+prediction+method
- [S88] Tokyo 2015 Workshop on CFD in Ship Hydrodynamics (KCS, JBC, ONRT): https://t2015.nmri.go.jp/
- [S89] Larsson, Stern and Visonneau (eds.), *Numerical Ship Hydrodynamics: an assessment of the Gothenburg 2010 Workshop* (Springer, 2014), including KVLCC2, Crossref record: https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Numerical+Ship+Hydrodynamics+An+assessment+of+the+Gothenburg+2010+Workshop+Larsson+Stern+Visonneau
- [S90] Harvey, Holden and Wadhams, "Code validation study of laminar shock/boundary layer and shock/shock interactions in hypersonic flow, Part B" (double cone), AIAA 2001-1031, Crossref record: https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Holden+Wadhams+Code+validation+study+of+laminar+shock%2Fboundary+layer+and+shock%2Fshock+interactions+in+hypersonic+flow+double+cone
- [S91] Messinger, "Equilibrium temperature of an unheated icing surface as a function of air speed", *J. Aeronautical Sciences* 20 (1953), Crossref record: https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Messinger+Equilibrium+temperature+of+an+unheated+icing+surface+as+a+function+of+air+speed
- [S92] Wright, *Validation Results for LEWICE 3.0*, NASA/CR-2005-213561, NTRS record: https://ntrs.nasa.gov/api/citations/20050160961
- [S93] DAGMC, direct accelerated geometry Monte Carlo: https://github.com/svalinn/DAGMC
- [S94] Briggs, Scott and Nouri, "The International Criticality Safety Benchmark Evaluation Project", *Nucl. Sci. Eng.* 145 (2003), Crossref record: https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Briggs+Scott+Nouri+The+International+Criticality+Safety+Benchmark+Evaluation+Project+Nuclear+Science+and+Engineering
- [S95] Rayleigh, "On the pressure developed in a liquid during the collapse of a spherical cavity", *Phil. Mag.* 34 (1917), Crossref record: https://api.crossref.org/works?rows=3&select=DOI,title,author,container-title,volume,page,issued&query.bibliographic=Rayleigh+On+the+pressure+developed+in+a+liquid+during+the+collapse+of+a+spherical+cavity
- [S96] Brennen, *Cavitation and Bubble Dynamics*, chapter 2 (Rayleigh collapse time): http://brennen.caltech.edu/HTMBUB/chap2.htm
- [S97] PyBaMM documentation, one-state hysteresis open-circuit potential: https://docs.pybamm.org/en/latest/source/api/models/submodels/interface/open_circuit_potential/one_state_hysteresis_ocp.html
- [S98] PyBaMM documentation, swelling-only particle mechanics (Ai et al., J. Electrochem. Soc. 167, 013512): https://docs.pybamm.org/en/latest/source/api/models/submodels/particle_mechanics/swelling_only.html
- [S99] NIST, Standard Reference Data: public law: https://www.nist.gov/srd/public-law
- [S100] Battelle, MMPDS order form (2023): https://www.mmpds.org/wp-content/uploads/2023/07/Order-Form_2023_FINAL.pdf
- [S101] CMH-17, software: https://www.cmh17.org/RESOURCES/Software
- [S102] Ansys, Granta MI Scripting Toolkit for Python: https://developer.synopsys.com/docs/granta-mi-scripting-toolkit-40/welcome.md
- [S103] CAMPUS, about: https://www.campusplastics.com/campus/about
- [S104] UL Solutions, Prospector and Product iQ service terms: https://ul.com/resources/prospectorproduct-iq-service-terms
- [S105] pycalphad: https://github.com/pycalphad/pycalphad
- [S106] Ansys Help 2025 R1, nCode DesignLife analysis settings: https://ansyshelp.ansys.com/public/Views/Secured/corp/v251/en/mech_addon/ds_fatigue_designlife_settings.html
- [S107] Basilisk, geometric VOF (src/vof.h; GPL-3.0 in src/COPYING): http://basilisk.fr/src/vof.h
- [S108] Cantera user guide, input file tutorial (YAML and ck2yaml): https://cantera.org/stable/userguide/input-tutorial.html
- [S109] Autodesk Moldflow Insight 2025 help, fiber orientation models: https://help.autodesk.com/cloudhelp/2025/ENU/MoldflowInsight-CLC-Analyses/files/analysis-sequences/Fiber-orientation-analysis/MoldflowInsight_CLC_Analyses_analysis_sequences_Fiber_orientation_analysis_Moldflow_s_fiber_orientation_html.html
- [S110] CERN STEAM framework, LEDET: https://steam.docs.cern.ch/tools/ledet/
- [S111] IPC Toolkit, getting started (barrier distance and friction smoothing): https://ipctk.xyz/tutorials/getting_started.html
- [S112] VDMA Verlag, FKM guideline, *Analytical Strength Assessment of Components*, 7th edition (2020): https://www.vdmashop.de/en/fkm-guidelines/6/analytical-strength-assessment-for-engineering-components-7th-edition-2020?c=9
- [S113] KISSsoft, gears module: https://www.kisssoft.com/en/products/products/modules/gears
- [S114] CMH-17, CMH17 STATS statistics software: https://www.cmh17.org/RESOURCES/Statistics-Software
- [S115] DIN Media, VDI 2230 Blatt 1:2015-11, systematic calculation of highly stressed bolted joints: https://www.dinmedia.de/en/technical-rule/vdi-2230-blatt-1/242566299
- [S116] Hobbacher and Baumgartner, *Recommendations for Fatigue Design of Welded Joints and Components*, 3rd edition, IIW Collection (Springer, 2024): https://link.springer.com/content/pdf/bfm:978-3-031-57667-6/1
- [S117] European Commission JRC, Eurocode 3 parts, including EN 1993-1-9 fatigue: https://eurocodes.jrc.ec.europa.eu/EN-Eurocodes/eurocode-3-design-steel-structures
- [S118] ISO 6336-1:2019, calculation of load capacity of spur and helical gears (parts 2, 3 and 6 are also 2019 editions): https://www.iso.org/standard/63819.html
- [S119] ISO/TR 6336-30:2022, calculation examples for ISO 6336 parts 1, 2, 3 and 5: https://www.iso.org/standard/84147.html
- [S120] Motion + Power Manufacturers Alliance, publications catalogue (ANSI/AGMA 2101-E25): https://motionpower.org/wp-content/uploads/2026/06/MPMA_Publications_Catalog.pdf
- [S121] ISO 281:2007, rolling bearings: dynamic load ratings and rating life: https://www.iso.org/standard/38102.html
- [S122] ISO 16281:2025, rolling bearings: modified reference rating life for universally loaded bearings: https://www.iso.org/standard/80221.html
- [S123] DIN Media, DIN 743-1:2012-12, calculation of load capacity of shafts and axles: https://www.dinmedia.de/en/standard/din-743-1/145165373
- [S124] FDA recognized consensus standards, ASTM F382-24, metallic bone plates: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards/detail.cfm?standard__identification_no=45857
- [S125] Waters et al., *Applications Manual for the Revised NIOSH Lifting Equation*, DHHS (NIOSH) 94-110 (CDC Stacks): https://stacks.cdc.gov/view/cdc/5434
- [S126] Kato Tech, Kawabata Evaluation System (KES) texture measurement: https://english.keskato.co.jp/texture-measurement
- [S127] ISO 9073-9:2008, nonwovens: drapability including drape coefficient: https://www.iso.org/standard/41375.html
- [S128] AISC, ANSI/AISC 360-22, Specification for Structural Steel Buildings: https://www.aisc.org/aisc/publications/current-standards/aisc-360/
- [S129] ISO 834-1:2025, fire-resistance tests: general requirements: https://www.iso.org/standard/83943.html
- [S130] European Commission JRC, Eurocode 2 parts: https://eurocodes.jrc.ec.europa.eu/EN-Eurocodes/eurocode-2-design-concrete-structures
- [S131] ACI CODE-318-25, Building Code for Structural Concrete: https://www.concrete.org/store/productdetail.aspx?ItemID=318U25
- [S132] DNV-RP-C203, fatigue design of offshore steel structures: https://www.dnv.com/energy/standards-guidelines/dnv-rp-c203-fatigue-design-of-offshore-steel-structures/
- [S133] FAA, AC 20-115D, citing RTCA DO-330, Software Tool Qualification Considerations: https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/1032046
- [S134] ASTM E8/E8M-25, tension testing of metallic materials, Crossref record: https://api.crossref.org/works/10.1520/E0008_E0008M-25
