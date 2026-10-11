# Physics coverage and materials (COV)

Crucible covers physics through versioned physics packages whose models declare a model level, an evidence level and a `ValidityEnvelope` as data. Every result therefore carries a validity-zone Field and an `ErrorBudget` with a model-form part, and every gap is a named record. Materials are versioned records of property Fields over state domains, with statistical basis, typed uncertainty, provenance and a `DataLicence` that travels in the label lattice.

## Coverage model

Three rules make "anything physical" as true as it can honestly be:

1. Every model says where it is valid.
2. Every result says how wrong it may be, and why.
3. Every gap has a name, a reason and a recommended alternative.

A physics package is a Package that exports `PhysicsModel` and `ConstitutiveModel` records; std ships them in `std::physics` and `std::materials`. A `PhysicsModel` names its implementation (a weak form, a Wasm component or an External Op), required properties, outputs, levels, envelope, calibration classes and precision class. Regime variables are Ingot functions returning Fields, zones form a `Field<Body, ValidityZone>`, and budgets are contract section 5's `ErrorBudget`.

**Decision D-COV-1:** Physics coverage is delivered only as physics packages that use public mechanisms. The coverage map is generated from package metadata, and each row has a status: `Planned (phase n)` until a package backs it, then the package's evidence level. Planned rows never count as coverage in `api`. *Why:* principle 1 forbids privileged physics, and readers and agents read an unbacked row as an existing capability (R1-32). *Rejected:* an in-app solver catalogue (privileged and unverifiable); a hand-written list (drifts from reality); planned domains without a status. (revised in round 2)

### Model levels

| Level | Form | Typical cost | Error statement | Examples |
| --- | --- | --- | --- | --- |
| L0 Analytic | Closed form, handbook or standard method | Microseconds | Method assumptions plus model-form error | Beam formulas, Nusselt correlations, gear rating, Paschen breakdown |
| L1 System | Lumped or 1D Networks solved as DAEs; exportable as FMI 3.0.2 | Milliseconds to seconds | As L0, plus Network discretization | Thermal RC networks, battery equivalent circuits, blade-element rotor theory |
| L2 Reduced | Projection (modal, Craig–Bampton, Krylov, POD with hyper-reduction) or surrogates | Milliseconds online | A posteriori estimator, or marginal surrogate coverage (D-COV-7) | Modal superposition, inherent-strain distortion, SPMe |
| L3 Full 3D | FEM, IGA, DG, finite volume, BEM or particle methods through Flux | Seconds to hours | Flux estimators plus model-form error | Nonlinear contact, LES, full-wave electromagnetics |

The model level chooses the model form; the `Fidelity` (`Preview`, `Interactive`, `SignOff`) chooses discretization accuracy. The two are independent, and both enter result provenance.

**Decision D-COV-2:** Each domain publishes a model ladder (L0 to L3), and adjacent rungs carry a consistency oracle inside the narrower envelope. *Why:* agreement between independent model forms is cheap verification that catches errors single-model benchmarks miss. Example target: Euler–Bernoulli tip deflection within 1% of a 3D solid at L/h ≥ 20. *Rejected:* verifying each level only in isolation; calling the rungs "fidelity levels", which collides with the three `Fidelity` names. (revised in round 2)

### Evidence levels

| Level | Meaning | Required results | Allowed use |
| --- | --- | --- | --- |
| E0 Declared | Implemented, not verified | None | Experimental packages; never decides a `SignOff` check |
| E1 Verified | Code verification passed | Manufactured-solution convergence at the declared order, conservation, derivatives against finite differences, determinism | `Preview` and `Interactive` |
| E2 Benchmarked | E1 plus community benchmarks | Published reference values within stated tolerance (NAFEMS, NASA TMR, TEAM) | `SignOff` inside the literature-documented zone, with `conditional_on: [ModelForm]` (D-COV-4) |
| E3 Validated | E2 plus held-out physical validation | ASME V&V 10 for solid mechanics [S65], V&V 20 otherwise [S7]; Evidence records under contract section 13.1's replicate rule | Golden-product release gates; the validation domain defines the calibrated zone |
| E4 Context-qualified | E3 plus a credibility package for a named context of use | ASME V&V 40 [S8], NASA-STD-7009 [S9] or the FDA credibility guidance [S10] | Regulated submissions; the authority decides |

**Decision D-COV-3:** `std` physics decides `SignOff` checks only at E2 or above. A model that a golden-product gate compares with physical tests reaches E3 by that gate. Validation follows ASME V&V 10-2019 for solid mechanics and V&V 20 otherwise, with contract section 13.1's replicates. Evidence levels rise only through CI-signed oracle results. *Why:* V&V 40 ties required credibility to how heavily a decision relies on the model [S8]; V&V 10 frames solid mechanics, where most golden products sit [S65] (R1-29). *Rejected:* a single "validated" flag; agent-assigned levels (principle 6); E3 resting on one unreplicated article. (revised in round 2)

An E2 model has no validation data of its own. Its calibrated zone is the validation domain that each bound's cited literature documents, confirmed by a named human reviewer (R1-30). Bounds without such a domain start in the Extrapolated zone.

**Decision D-COV-21:** Each result carries a solution-verification status beside its model's evidence level: `Estimator` (a guaranteed or calibrated bound), `Gci` (FLX's `std::sim::solution_verification`) or `None`. A result with `None` has an `Indicator` discretization part and never supports `SignOff`. *Why:* code verification proves a method, not one application result, and several methods have no reliable estimator (R1-28, D-FLX-34). *Rejected:* folding solution verification into the E levels, which describe models rather than results.

### Error budgets and model form

Every result Field carries contract section 5's `ErrorBudget<Q>`, one bound per `ErrorSource` in its own norm. Flux fills the numerical parts (FLX "Error budgets, goals and checks"). COV fills the input part from Material uncertainty and the model-form part from validation.

| Evidence level and zone | Model-form part |
| --- | --- |
| E3 or E4, Calibrated | `Estimated`: \|E\| + k·u_val at the nearest validation points, with E = S − D and u_val = √(u_num² + u_input² + u_D²) |
| E3 or E4, Extrapolated | The Calibrated bound times the envelope's inflation g(d) |
| E2, any zone | `NotQuantified { reason: NoValidationData }` |
| Invalid or Unassessed | Not reached: dependent checks return `Error(Failure)` |

**Decision D-COV-20:** Model-form error is the V&V 20 validation metric at validation points, `Estimated` with a coverage factor k declared per package. Across the Extrapolated band it grows by a declared inflation function g(d) of the normalized distance d to the nearest validation point, in log-normalized regime coordinates; g is non-decreasing with g(0) = 1. *Why:* V&V 20 quantifies accuracy only at validation points [S7], and round 1's `inflation` field had no definition (R1-29). *Rejected:* one constant inflation factor per domain; carrying the validation error unchanged into extrapolation.

**Decision D-COV-4:** An unquantified part is shown as "not quantified", never as zero, and a check whose margin lies inside the quantified budget is `Undecided`. A check that depends on an unquantified part is `Pass { conditional_on }` (contract section 5). It meets a release gate only when repository policy names a cited covering allowance for each listed part, and is then re-evaluated with that allowance as an `Estimated` part. *Why:* a design-code partial factor that the code states covers model uncertainty is the honest route for E2 models (R1-03). *Rejected:* round 1's `unquantified` tag on a verdict from the quantified part, which treats the missing term as zero; refusing every E2 result. (revised in round 2)

`Estimated` discretization bounds arrive multiplied by a factor η99 from `std::sim::calibration` (D-FLX-24); FLX keeps the corpus, and COV maps models to classes.

**Decision D-COV-17:** Every `PhysicsModel` names the calibration class of each `Estimated` estimator it relies on, and that class's η99 entry is pinned in `ingot.lock`. A model–estimator pair with no entry reports `Indicator`. *Why:* only the model author knows which problem class a model's results fall in (R1-07). *Rejected:* one class per numerical method regardless of physics; classes inferred at run time from heuristics outside the pinned inputs.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Coverage map | Generated from package metadata by domain, scale, model level and status; `api` Read methods | Unbacked cells show `Planned (phase n)`, the nearest packages and limit records, outside counts | COV-O-MAP-1 | 0 |
| Model ladders | Consistency of adjacent rungs inside the narrower envelope | Disagreement blocks the higher rung's evidence level | COV-O-VER-2 | 1 |
| Evidence levels | E0 to E4, raised only by CI-signed results and protected validation | Unsigned or agent-set levels rejected | COV-O-VER-3 | 0 |
| Solution-verification status | `Estimator`, `Gci` or `None` on every result | `None` keeps the discretization part `Indicator` | COV-O-VER-4 | 1 |
| Model-form part | V&V 20 metric; inflation g(d) over the Extrapolated band | `NotQuantified { NoValidationData }` at E2 | COV-O-VAL-2 | 1 |
| Input part | Material uncertainty through `std::uq` | `NotQuantified { MissingUncertainty }` | COV-O-ERR-1 | 2, 3 epistemic |
| Calibration classes | Model-to-class map with pinned η99 entries | No entry: `Indicator` | COV-O-ERR-2 | 1 |
| Conditional passes | `Pass { conditional_on }`; policy allowances with citations | `Undecided { reason: Unquantified(components) }` | COV-O-ERR-3 | 1 |

## Validity envelopes as data

### Data model

A `ValidityEnvelope` is a content-addressed record versioned with its model. It bounds regime variables, states scale limits, lists assumptions that cannot be computed, and cites the evidence behind each zone.

```rust
pub struct ValidityEnvelope {
    pub model: ModelRef,                 // PhysicsModel or ConstitutiveModel, id@version
    pub bounds: Vec<RegimeBound>,
    pub calibrated_region: CalibratedRegion, // per-variable box or joint hull (below)
    pub length_scale: ScaleRange,        // e.g. continuum valid above 1 µm for this class
    pub assumptions: Vec<Assumption>,    // "perfect bond"; each becomes an acknowledgement check
    pub inflation: Inflation,            // g(d) over the Extrapolated band (D-COV-20)
    pub evidence: Vec<ObjectId>,         // oracle results and Evidence records
}

pub struct RegimeBound {
    pub variable: RegimeVariableId,      // resolves to a typed Ingot function (D-COV-18)
    pub reduction: Reduction,            // Pointwise | Max | Min | Mean | Percentile(p)
    pub calibrated: QuantityInterval,    // backed by evidence
    pub extrapolated: QuantityInterval,  // superset; plausibility limit
    pub outside: Disposition,            // Flag (a human may waive) | Refuse
    pub on_missing: OnMissing,           // Unassessed | ConservativeDefault { value, basis }
    pub escalate_to: Vec<ModelRef>,      // models valid beyond this bound
    pub basis: Citation,                 // why the bound sits where it does
}

pub enum ValidityZone { Calibrated, Extrapolated, Invalid, Unassessed }
```

An assumption becomes an acknowledgement check: a design using the model carries a human-signed statement that it holds. Material-specific bounds come from the constitutive model's calibration, so one physics model has a different calibrated zone for each Material.

### Joint bounds

Per-variable intervals describe a box, which overstates coverage when validation data are correlated, for example tests run only at high temperature and low rate. A bound set may instead declare the convex hull of validation points in log-normalized regime coordinates, inflated by a declared margin. A point inside the box but outside the hull is Extrapolated, and inspection reports the nearest validated condition.

```rust
pub enum CalibratedRegion {
    Box,                                            // per-variable intervals only
    Hull { variables: Vec<RegimeVariableId>, points: ObjectId, margin: f64 },
}
```

### Regime variables

Each variable states its length or time scale; a Reynolds number without one is not a regime variable.

| Variable | Definition | Typical users |
| --- | --- | --- |
| Equivalent strain, rotation | From the displacement Field | Small-strain kinematics |
| Homologous temperature | T / T_melt, absolute temperatures | Creep onset, rate-independent plasticity |
| Strain rate, triaxiality, Lode parameter | From strain-rate and stress Fields | Johnson–Cook range, ductile fracture |
| Reynolds, Mach, y⁺ | u·L/ν with L declared per bound (hydraulic diameter, chord, wall distance) | Laminar models, wall treatment |
| Separation | Wall-shear sign change; Clauser parameter β = (δ*/τ_w)·dp/dx | RANS envelopes |
| Knudsen | Mean free path over a declared gap or feature length | Continuum, slip and DSMC models |
| Biot, Rayleigh, Prandtl | From geometry and properties | Lumped capacitance, correlations |
| Weber, capillary, Weissenberg | From interface and rheology Fields; gate Weber number for die casting | Breakup, viscoelastic flow, HPDC filling |
| Local slenderness | t / L_local for walls, d / L_local for members, as FLX defines L_local | Shell and beam models |
| Lattice regimes | Cell size over gradient length; distance to the boundary in cells; strut slenderness times compressive macro strain against a Bloch-wave bound | Homogenized lattices |
| Imperfection sensitivity | Koiter post-buckling coefficient, or a classifier for shells known to be sensitive | Linear eigen-buckling |
| Mass ratio, frequency separation | ρ_s·t/(ρ_f·L) or added-mass fraction; structural frequencies against Strouhal and blade-passing bands | Weak fluid–structure coupling |
| Electrical size kL, skin depth δ/L, optical size L/λ | From frequency or wavelength, geometry and properties | Quasi-static electromagnetics, geometric optics |
| Mean-free-path share | Share of conductivity carried by phonon mean free paths above the feature size | Fourier conduction |
| C-rate, state of charge, cell temperature | From cell states | Battery model selection |
| Acoustic amplitude p′/ρc² | From the pressure Field | Linear acoustics |
| Cycles N, stress ratio R, ΔK | From load histories | Fatigue regimes |
| Scale ratio ℓ/L | Microstructure length over feature size | Homogenized properties |

**Decision D-COV-18:** Every `RegimeBound.variable` resolves to a typed Ingot function of inputs or solution Fields, and the registry rejects a bound whose variable does not. A condition that cannot be computed is an `Assumption`, which becomes an acknowledgement check. A missing material input makes a bound `Unassessed` unless the bound declares a documented conservative default, which makes it `Extrapolated`. *Why:* prose bounds such as "mildly separated flow" cannot be evaluated, and one missing grain size would otherwise block every design using the model (R1-31). *Rejected:* checking only that a bound cites a basis; silently skipping bounds with missing inputs.

Std ships detectors for common prose conditions: separation, by wall-shear sign change or the Clauser parameter, and imperfection-sensitive shells, by Koiter's coefficient or a classifier. Flux computes the lattice regime variables (FLX "Homogenization and lattices").

### Evaluation

1. **A priori screen.** Bounds computable from inputs, such as inlet Reynolds number, run before solving. A `Refuse` bound beyond its extrapolated range stops the solve with a typed error.
2. **Solve.** Flux evaluates the Ops as usual.
3. **A posteriori assessment.** Regime Fields from the solution are reduced per bound and mapped to zones; the worst zone per point forms the zone Field.
4. **Composition.** Envelopes of coupled models and of the coupling itself compose by intersection.
5. **Checks.** Each bound compiles to a check named `validity::<model>::<variable>`, with severity from the zone policy.
6. **Display.** COV states each point's zone in the zone Field; UIX hatches the Extrapolated, Invalid and Unassessed zones and owns their display (UIX "Field views"). Inspection shows value, bound, basis and escalation options.

Zone Fields are identical within the canonical class. Another class may differ only within twice the declared cross-class tolerance of a bound, reported as `NearBound`. Release decisions use canonical zones (R1-45). Assessment cost targets under 2% of solve time.

[[DIAGRAM: Validity flow: "Inputs and Material" → "A priori screen" → "Flux solve" → "Regime variable Fields" → "Zone Field" → "Checks" → "UIX hatching" and "Release gate". Side arrows: screen –Refuse→ "Typed error with escalation list"; checks –Extrapolated or Flag→ "Human waiver in the change order". An "ErrorBudget" box fed by "Flux estimators (η99)", "Material uncertainty" and "Validation metric and inflation" attaches to the result Fields and tags checks with conditional_on.]]

### Policy by zone

| Zone | `Interactive` | `SignOff` | Release gate |
| --- | --- | --- | --- |
| Calibrated | Shown | Checks evaluate normally | Allowed |
| Extrapolated | Hatched by UIX; model-form part inflated | Checks evaluate with the inflated part; the outcome names the zone | Human waiver in the change order |
| Invalid, `Flag` | Hatched by UIX; dependent checks error | Dependent checks return `Error(Failure)` | Human waiver with rationale; agents cannot waive |
| Invalid, `Refuse` | Shown for diagnosis only | Dependent checks return `Error(Failure)` | Blocked; no waiver |
| Unassessed | Hatched by UIX with a missing-input notice | Dependent checks return `Error(Failure)` | Blocked until the input or a documented default exists |

**Decision D-COV-5:** Validity bounds compile to ordinary checks, and validity zones are a Field. *Why:* checks already carry severity, CI, reports and review, and Fields already paint on geometry (composition over special cases). *Rejected:* a separate warnings channel (a parallel abstraction); clamping results to the envelope (silent).

**Decision D-COV-6:** Crucible suggests escalation to a valid model but never switches models automatically. *Why:* a switch changes cost, provenance and sometimes the answer, so it must be explicit. *Rejected:* automatic escalation between model levels.

### Failure behaviour

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
  Knudsen number reaches 0.31; calibrated below 0.001, extrapolated to 0.01, refused above 0.01
  basis: the no-slip wall closure fails in slip and transitional flow, see std::physics::regime::knudsen
  try: std::physics::rarefied::dsmc (External Op; valid for Kn 0.1 to 10)
```

Widening any envelope, in any package, needs a human Approval of the Proposal, as loosening a tolerance does. Agents may propose envelope changes with evidence; they cannot merge them.

### Surrogates and learned models

**Decision D-COV-7:** A learned surrogate is an L2 model whose calibrated zone is its training distribution and whose predictions are Fields of kind `Estimated { confidence, scope: Marginal }`. It drives `Preview`, `Interactive` and exploration; a `SignOff` check uses it only with a per-prediction a posteriori bound or a confirming solve (D-FLX-14). Out-of-distribution queries are Extrapolated or Invalid, and no surrogate reaches E3 without held-out physical validation. *Why:* conformal coverage is marginal, and optimizers steer queries toward a surrogate's errors (R1-04). *Rejected:* treating a surrogate as interchangeable with its source model; split-conformal intervals as `SignOff` evidence. (revised in round 2)

### Coupled physics

Flux owns coupling algorithms. A coupling is itself a model with an envelope, so a weak coupling outside its envelope is flagged like any other model.

| Pair | Default coupling | Weaker coupling allowed when | Benchmark |
| --- | --- | --- | --- |
| Thermal → structure | One-way, sequential | Deformation leaves thermal boundary conditions and contact conductance unchanged | NAFEMS P18 thermal stress; LE11 −105 MPa [S2][S3] |
| Fluid ↔ structure | Partitioned with interface quasi-Newton; monolithic for strong added mass | One-way only under D-COV-19 | Turek–Hron FSI [unverified] |
| Electromagnetic → thermal | Period-averaged losses, one-way | Conductivity and permeability insensitive to temperature over the range | TEAM 36 [S6] |
| Electrochemical ↔ thermal | Two-way, monolithic | One-way below a declared C-rate and temperature rise | PyBaMM thermal comparison [unverified] |
| Structure ↔ acoustics | Two-way for heavy fluids and light panels in air | One-way when the fluid-loading parameter ρ_f·c/(ω·m_s) stays below 0.1 over the band [unverified threshold] | Baffled piston, plate radiation |
| Electrostatic ↔ structure | Monolithic, for pull-in | Never one-way near pull-in | Parallel-plate pull-in |
| Process → structure | One-way through state Fields | Always one-way within Crucible; VMAP [S58] is the candidate exchange format [unverified fit] | AM-Bench [S11] |
| Aerodynamics ↔ structure | Partitioned, modal structure | One-way only under D-COV-19, with p–k flutter as the stability check | AGARD 445.6 [unverified] |

**Decision D-COV-19:** One-way fluid–structure or aerodynamic–structural coupling is valid only when three conditions hold. The mass ratio ρ_s·t/(ρ_f·L) exceeds 10, or added mass is below 5% of structural mass. Structural natural frequencies clear the fluid forcing band (Strouhal and blade-passing frequencies) by a stated margin. A coupled stability check (p–k flutter or a linearized coupled eigenanalysis) shows positive damping across the operating envelope. Otherwise the coupling is Invalid, with escalation to two-way coupling. *Why:* flutter, galloping and lock-in grow from infinitesimal amplitudes, so a small-displacement test approves one-way analysis exactly where coupling destabilizes the structure (R1-27). *Rejected:* round 1's displacement below 1% of the flow length scale; small static twist as the aeroelastic test.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Envelope records | `ValidityEnvelope` per model version | Registry rejects a missing envelope, basis, escalation or inflation | COV-O-ENV-1 | 0 |
| Regime variables | Typed Ingot functions with declared scales | `RegimeUncomputable { variable }` at registration | COV-O-ENV-6 | 0 |
| Zone evaluation | A priori screen, a posteriori zones, intersection | `ValidityError::OutsideEnvelope` with escalations | COV-O-ENV-2 | 1 |
| Joint calibrated regions | Box or hull in log-normalized coordinates | Outside the hull: Extrapolated, nearest validated condition reported | COV-O-ENV-2 | 2 |
| Zones across classes | Canonical zones identical; `NearBound` elsewhere | A mismatch outside the band opens a determinism incident | COV-O-ENV-3 | 1 |
| `Refuse` bounds | Stop the solve or block dependent checks | `Error(Failure)` with fixes | COV-O-ENV-4 | 1 |
| Waivers and widening | Human only, in the change order | Agent attempts fail with a permission error | COV-O-ENV-5 | 1 |
| Missing inputs | Documented conservative default, else `Unassessed` | `ValidityError::Unassessed { missing }` | COV-O-ENV-6 | 1 |
| Surrogate envelopes | Training distribution as the calibrated zone | Out-of-distribution queries Extrapolated or Invalid | COV-O-ENV-7 | 4 |
| Coupling envelopes | Weak couplings only inside their envelope (D-COV-19) | One-way analysis outside it is Invalid | COV-O-ENV-8 | 1 thermal, 4 fluid |

## Coverage matrix

The matrix is generated from package metadata (D-COV-1). This tab sets its initial content, so every row is `Planned` in its listed phase; "(13.4)" marks a phase set by contract section 13.4.

Scales: **N** below 100 nm, **µ** to 1 mm, **Me** to 100 mm, **P** to 10 m, **L** beyond. Delivery: **Nat** an Ingot weak form compiled by Flux; **Wasm** a `std` Wasm component on Flux operations (D-COV-11); **Ext** an External Op (D-COV-12). Attributions tagged [Sn] were verified; envelope numbers are design defaults, [unverified] until the owning package reaches E2.

### Solid mechanics

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Linear elasticity | µ Me P L | Beam, plate and shell formulas · frame networks · static condensation | High-order FEM on the immersed octree; IGA on trimmed B-rep; finite cell for voxels | Strain ≤ 0.5% calibrated, ≤ 2% extrapolated; below the proportional limit; rotation ≤ 0.05 rad; feature ≥ 10 grains (default if missing) | NAFEMS LE1 92.7 MPa, LE10 −5.38 MPa, LE11 −105 MPa [S3][S4] | Nat | 1 |
| Shells, beams and frames | Me P L | Beam and plate formulas · frame networks · — | Reissner–Mindlin and IGA Kirchhoff–Love shells; Timoshenko and Vlasov beams; Nitsche couplings (D-FLX-12) | t/L_local ≤ 0.2, or ≤ 0.05 for Kirchhoff–Love; d/L_local ≤ 0.2; reduction error by 3D patch re-solves (D-FLX-26) | NAFEMS shell and beam cases | Nat | 1 lattices, 2 |
| Geometric nonlinearity | µ Me P L | — | Total Lagrangian FEM with arc-length continuation | Limit and bifurcation points reported, never stepped over | NAFEMS R0024 group [S5] | Nat | 2 |
| Plasticity | µ Me P L | Neuber and Glinka notch rules · — · — | Finite-strain J2, Hill48, Yld2000-2d, Chaboche; tangents through `local_solve` | Rate-independent below homologous T 0.3; beyond uniform elongation only with damage | NAFEMS R0024 panel [S5]; thick cylinder | Nat | 2 |
| Hyperelasticity | µ Me P | — | Mixed u–p and F-bar; Neo-Hookean to Gent | Stretch within the calibrated range per mode; strong ellipticity over the envelope | Cook's membrane; patch tests | Nat | 2 |
| Viscoelasticity | µ Me P | — · Prony networks · complex-modulus modal | Generalized Maxwell with WLF or Arrhenius shift; Bergström–Boyce | Temperature and frequency within the master curve | Analytic creep and relaxation | Nat | 3 |
| Creep | Me P L | Larson–Miller · — · — | Norton–Bailey, Garofalo, theta projection; Kachanov–Rabotnov damage | Time ≤ longest test calibrated, ≤ 3× extrapolated (OOR-5) | NAFEMS R0027 [S5] | Nat | 3 |
| Contact and friction | µ Me P L | Hertz, Boussinesq · — · — | Mortar contact on fitted tetrahedra (13.4); Incremental Potential Contact [S26] | Penetration below tolerance; friction only from a tested pair (OOR-19) | NAFEMS R0094 [S5]; Hertz | Nat | 2 |
| Bolted and bonded joints | Me P L | VDI 2230 [unverified] · joint springs · — | Preloaded bolts; cohesive zones with Benzeggagh–Kenane mixing | Joint parameters and damping from tests of the joint class (OOR-18) | DCB and ENF | Nat | 2 |

### Dynamics and stability

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Modal analysis | µ Me P L | Rayleigh, Dunkerley · lumped MDOF · Craig–Bampton | Lanczos and LOBPCG (13.4) | Linear; damping from test (OOR-18) | NAFEMS free vibration [S2][S5] | Nat | 1 |
| Vibration and shock | Me P L | SDOF, Miles, shock spectra · — · modal with residual vectors | Direct frequency response; PSD response; implicit generalized-α | Damping declared; PSD band and pulse within modal coverage | NAFEMS R0016 [S5]; half-sine SDOF | Nat | 2 |
| Rotordynamics | Me P | Jeffcott rotor · rotor beams · Campbell modal | Rotating-frame FEM; fluid-film bearings from the Reynolds equation | Bearings linearized at operating speed | Jeffcott critical speed | Nat | 2 |
| Buckling | µ Me P L | Euler, Johnson · — · linear eigen-buckling (13.4) | Arc-length post-buckling with seeded imperfections; Koiter asymptotics | Eigen-buckling `Refuse` at `SignOff` on shells flagged imperfection-sensitive | NAFEMS R0024 [S5]; Euler column | Nat | 1 linear, 2 nonlinear |
| Explicit dynamics, impact, crash | Me P L | Energy methods · lumped crash networks · — | Explicit dynamics with diagonal mass and penalty contact (FLX); erosion from COV damage models | Mass scaling ≤ 2% calibrated, `Refuse` above 5%; hourglass energy ≤ 10% of internal; failure `Flag` (OOR-6) | Taylor bar; GP5 drop; GP9 crash box | Nat; OpenRadioss (AGPL) as External Op reference [S25] | 3 drop, 5 crash (13.4) |

Production-scale crash models are practical; predicting where they fail is not (OOR-6).

### Durability: fatigue, fracture, wear

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Stress-life | Me P L | Basquin with Goodman, Gerber or Walker · rainflow · — | Critical-plane criteria (Findley, Dang Van) with surface, size and notch factors; probabilistic S–N | N ≥ 10⁴; R and temperature within tests; defects below Kitagawa–Takahashi | Held-out coupons | Nat | 1 uniaxial, 2 multiaxial |
| Strain-life | Me P L | Coffin–Manson, Morrow, SWT · — · — | Fatemi–Socie, Brown–Miller on elastic-plastic FE | Cyclic curve from the same condition | Notched specimens | Nat | 2 |
| Weld fatigue | Me P L | Nominal, hot-spot, effective notch (IIW, EN 1993-1-9) [unverified] · — · — | Structural-stress methods on shells and solids | Weld class and quality declared | Code examples [unverified] | Nat | 2 |
| Lubrication and rolling-contact fatigue | µ Me P | Hamrock–Dowson film thickness [unverified] · — · — | Elastohydrodynamic Reynolds equation with pressure–viscosity and elastic deflection; subsurface critical-plane fatigue | Isothermal Newtonian film unless declared; life `Flag` without bearing-steel data | Hertz pressure; film-thickness data [unverified] | Nat | 2 |
| Crack growth | Me P L | Paris, NASGRO with handbook K · — · — | Interaction-integral K and J; spectrum retardation | Small-scale yielding; ΔK above threshold | NAFEMS R0020 [S5] | Nat | 3 |
| Fracture | µ Me P L | K_Ic, failure assessment diagrams · — · — | Cohesive zones; phase field (AT1, AT2); Gurson–Tvergaard–Needleman, Hosford–Coulomb | Ductile `Flag`: a blind round robin found "a striking lack of consistency across research groups" [S12] | Sandia Fracture Challenge [S12] | Nat | 2 LEFM, 3 cohesive, 4 phase field, 5 ductile |
| Wear and erosion | µ Me P | Archard; Finnie-type erosion [unverified] · — · — | Archard on local pressure and slip with geometry update; impact erosion from tracked particles | Coefficients from the tested pair and medium; erosion `Flag` always | Pin-on-disc | Nat | 3 wear, 5 erosion |

### Composites and architected materials

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Laminates | Me P L | Classical laminate theory · — · — | Layered and IGA shells on draped fibre-angle Fields; MEC owns plies and kinematic draping | Through-thickness stress needs layerwise or solid models | NAFEMS R0031 [S5] | Nat | 4 (13.4) |
| Progressive failure | Me P L | Tsai–Wu, Hashin, Puck, LaRC05 · — · — | Continuum damage with cohesive interlaminar zones, calibrated in a building-block pyramid | `Flag`: a review of WWFE-II found none of 12 theories matched all test data [S13] | WWFE-II [S13] | Nat | 4 |
| Short-fibre moulded composites | Me P | Rule of mixtures · — · — | Mori–Tanaka averaging over the orientation tensor Field from filling | Aspect ratio and fraction within calibration | Unidirectional limit | Nat | 3 (13.4) |
| Lattices | µ Me P | Gibson–Ashby · — · homogenization with localization | Beam-lattice models; full-resolution immersed FEM | Cell over gradient length ≤ 0.1; `Invalid` within 2 cells of a boundary without correction; `Flag` above the Bloch-wave buckling bound | Homogenized against beam lattice and full resolution | Nat | 1 |

Lattice strength checks read localized strut stresses, and a lattice part's critical region signs off on the beam-lattice model (R1-26).

### Heat transfer

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Conduction | N µ Me P L | Slab, fin and shape factors · RC networks · moment matching | High-order FEM, IGA, immersed methods | Fourier law `Refuse` where a declared share of conductivity comes from mean free paths above the feature size | NAFEMS T2 to T4 [S2][S5] | Nat | 1 |
| Convection | Me P L | Nusselt correlations within published ranges · flow networks · — | Conjugate heat transfer on laminar, RANS or LES flow | Correlation ranges `Refuse`; conjugate analysis inherits the flow envelope | NAFEMS T4 [S5]; Graetz | Nat | 2 correlations, 3 laminar and natural, 4 turbulent (13.4) |
| Radiation | Me P L | Two-surface enclosures · radiosity networks · — | Ray-traced view factors; Monte Carlo for specular and spectral surfaces; discrete ordinates (D-FLX-38) | Gray-diffuse declared; spectral bands where emissivity varies | Analytic view factors; closure ΣF = 1 within 10⁻⁶ (target) | Nat | 3, 4 discrete ordinates |
| Solid–liquid phase change | µ Me P | Stefan, Neumann · — · — | Enthalpy method with mushy zone | Freezing range declared; no undercooling | Stefan analytic | Nat | 3 |
| Boiling, condensation, heat pipes | Me P | Rohsenow, Nusselt film · heat-pipe and vapour-compression networks with CoolProp [S43] · — | VOF with phase change | Correlations `Refuse` outside range; heat-pipe capillary, sonic, entrainment and boiling limits reported; resolved boiling `Flag` | Nusselt film analytic | Nat | 4 |
| Moisture and hygro-mechanics | µ Me P L | Equilibrium moisture tables · — · — | Fickian diffusion with sorption isotherms, hygro-expansion, mechano-sorptive creep | Humidity and temperature within sorption data; mechano-sorptive creep `Flag` | Fickian slab | Nat | 3 packages, 7 timber |
| Ablation and pyrolysis | Me P | Heat of ablation · 1D charring ablator · — | Surface energy balance with B′ tables and recession | `Flag` always | Ablation workshop [unverified] | Wasm | 6 |
| Joule heating and thermoelectrics | µ Me P | Resistive and Peltier module formulas · — · — | Electro-thermal coupling with temperature-dependent resistivity; Seebeck–Peltier–Thomson FEM | Resistivity within data; linear thermoelectric coefficients | Wire heating; analytic module | Nat | 4 Joule (13.4), 5 thermoelectric |

### Fluids

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Incompressible laminar | µ Me P | Hagen–Poiseuille, Moody · duct networks · POD-Galerkin | Stabilized high-order FEM or DG | Re below transition (pipe: 2,000 calibrated, 2,300 extrapolated) | Lid-driven cavity [unverified] | Nat | 3 |
| RANS | Me P L | Loss data · networks with loss coefficients · — | Spalart–Allmaras, SST, GEKO; γ–Reθ transition; quadratic constitutive relation; wall functions and immersed wall models (FLX) | Attached flow calibrated; separation `Flag`; wall-function y⁺ range declared | NASA TMR 2DZP, 2DB, 2DMEA, 2DWMH, ATB [S1] | Nat | 4 |
| Scale-resolving: DDES, WMLES, LES | Me P L | — | Entropy-stable DG [S28] and flux reconstruction [S27]; non-equilibrium wall models [S15] | Cost from Yang–Griffin scalings [S14]; equilibrium wall models `Flag` under adverse pressure gradient [S15] | 2DWMH hump [S1] | Nat | 5 |
| DNS | µ Me | — | Spectral and high-order DG | `Refuse` above the a priori budget (OOR-1) | Taylor–Green [unverified] | Nat | 5 |
| Lattice Boltzmann | Me P L | — | Cumulant collision with wall models; XLB (Apache-2.0) as reference [S38] | Ma ≤ 0.1 calibrated, ≤ 0.3 extrapolated, as compressibility error scales with Ma² | As LES | Wasm | 5 |
| Compressible flow | Me P L | Isentropic and shock relations · quasi-1D nozzle · — | Entropy-stable DG and flux reconstruction; SU2 (LGPL-2.1) as reference [S37] | Perfect gas below a declared temperature; nonequilibrium Ext | ATB, ONERA M6 [S1] | Nat | 5 |
| Free surface and resolved multiphase | µ Me P L | Linear wave theory · — · — | Geometric VOF, conservative level set, Cahn–Hilliard; weakly compressible SPH | Converged at k_max·η_KH ≥ 60 with second-order schemes [S16]; coarser `Flag` | Dam break, rising bubble [unverified] | Nat | 5 (13.4) |
| Dispersed multiphase | Me P L | Settling and drag correlations · — · — | Euler–Lagrange with two-way coupling; Euler–Euler | Volume-fraction limit per model; breakup `Flag` (OOR-8) | Particle-laden pipe [unverified] | Nat | 5 (13.4) |
| Cavitation | Me P | Cavitation number · — · — | Mixture models with Schnerr–Sauer or Zwart transfer | `Flag` always; erosion out of reach (OOR-9) | Cavitating hydrofoil [unverified] | Nat | 6 |
| Non-Newtonian | µ Me P | Power-law pipe flow · — · — | Carreau–Yasuda, Cross–WLF, Herschel–Bulkley; Oldroyd-B, Giesekus, PTT with log-conformation | Shear rate within rheometry; Weissenberg within the verified range | Poiseuille; 4:1 contraction [unverified] | Nat | 3, 5 viscoelastic |
| Porous media | µ Me P L | Darcy, Ergun · — · — | Darcy–Brinkman–Forchheimer; permeability from pore-scale lattice Boltzmann | Pore Reynolds number within the law | Porous channel | Nat | 3 |
| Rarefied gas | µ Me P | Free-molecular formulas · — · — | Slip and temperature jump; DSMC with SPARTA (GPL) [S34] | Kn < 0.001 continuum, to 0.1 slip, to 10 transitional [unverified] | Microchannel slip | Nat slip, Ext DSMC | 5 |
| Microfluidics | µ Me | Stokes resistances · hydraulic networks · — | Stokes FEM with electro-osmotic slip and Nernst–Planck transport | Debye length much smaller than the channel | Electro-osmotic plug flow | Nat | 5 |
| Combustion | Me P L | Adiabatic flame temperature · reactor networks with Cantera (BSD-3) [S21][S22] · flamelet tables | Flamelet-progress-variable, FGM; finite-rate chemistry in LES | `Flag` always (OOR-7) | Flame speeds; TNF flames [unverified] | Wasm kinetics, Nat transport | 6 |

COV owns free-surface and multiphase flow beyond mould filling (13.4). Real-fluid properties come from CoolProp (MIT) [S43] or a licensed REFPROP connector.

### Acoustics and ultrasonics

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Linear acoustics | Me P L | Sabine, Eyring · duct transfer matrices · modal | High-order FEM with PML; fast BEM; geometrical room acoustics | p′/ρc² ≤ 10⁻²; points per wavelength above the order's minimum | Pulsating sphere, baffled piston | Nat | 3 |
| Vibro-acoustics | Me P L | — · statistical energy analysis · modal | Structural–acoustic FEM and FEM–BEM | SEA needs 3 modes per band; heavy fluids and light panels two-way | Plate radiation | Nat | 3 FEM, 5 SEA |
| Porous absorbers | Me P | Delany–Bazley · transfer matrix · — | Johnson–Champoux–Allard; Biot | Flow resistivity within measured range | Impedance tube | Nat | 5 |
| Aeroacoustics | Me P L | Gutin tonal noise · — · — | Ffowcs Williams–Hawkings from blade loading or scale-resolving surfaces | Broadband `Flag` without scale-resolving input | GP6 rotor acoustics | Nat | 4 tonal, 5 broadband |
| Ultrasonic testing | µ Me P | Ray and beam-spread formulas · — · — | Spectral-element or DG elastodynamics with PML and transducers | Linear; grain scattering `Flag` without microstructure | Lamb-wave dispersion | Nat | 6 |

### Electromagnetics

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Electrostatics | N µ Me P L | Plate, sphere, coaxial formulas · capacitance networks · — | High-order FEM; fast BEM; capacitance extraction as in Palace (Apache-2.0) [S18] | kL ≤ 0.1 calibrated, ≤ 0.3 extrapolated | Sphere, coaxial; Palace [S18] | Nat | 3 |
| Magnetostatics | µ Me P L | Magnetic circuits · reluctance networks · — | Nédélec FEM with tree–cotree gauging and Newton on B–H curves | B within measured B–H range | TEAM 13 [S6] | Nat | 3 |
| Eddy currents and induction | µ Me P L | Skin-depth formulas · — · — | A–φ and T–Ω; surface impedance | Surface impedance only where δ/L ≤ 0.1 | TEAM 7 and 36 [S6] | Nat | 4 |
| Electric machines | Me P | dq circuits · loss and thermal networks · flux-linkage maps | Motion with sliding interfaces; Bertotti iron loss; magnet eddy loss; demagnetization | Loss coefficients per lamination grade and band | GP6 motor tests | Nat | 4 |
| RF and antennas | Me P L | Line formulas · S-parameter networks · Krylov sweeps | Frequency-domain Nédélec FEM with wave ports and fast sweep for narrowband; FDTD for broadband (D-FLX-32); MoM with multilevel fast multipole | Dispersion fit inside the measured band | Dipole with a Hallén reference; Mie sphere | Nat | 4 drone antenna, 5 general |
| Signal and power integrity | µ Me | RLGC lines · — · vector fitting | Quasi-static and full-wave extraction | Causality and passivity enforced | Microstrip | Nat; ELX owns use | 3 |
| EMC | Me P | Shielding formulas · cable models · — | FDTD and DG time domain with field-to-cable coupling | `Flag` always for compliance prediction | Aperture cases [unverified] | Nat | 4 emissions, 5 immunity |

### Optics and photonics

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Imaging optics | µ Me P | Paraxial ABCD · sequential ray tracing · — | Differentiable ray tracing with polarization; Fourier-optics PSF and MTF | Geometric optics where L/λ ≥ 100 | Singlet and doublet | Nat | 5 |
| Illumination and stray light | Me P L | Photometric formulas · — · — | Spectral Monte Carlo path tracing with measured BSDFs, as in Mitsuba 3 [S39] | BSDF within measured angles and wavelengths | Light-guide measurements | Nat | 3 light pipes, 5 |
| Wave optics and photonics | N µ | Thin-film matrices · — · eigenmode expansion | FDTD, DG, RCWA, FEM mode solvers; Meep (GPL) only as External Op reference | Linear unless declared | Mie; slab modes | Nat | 6 |

### Electrochemistry and chemical kinetics

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Battery cells, reduced | µ Me P | Capacity formulas · equivalent circuits with OCV, entropic heat and LFP hysteresis [S62] · SPM, SPMe | — | C-rate, temperature and SOC bounds per rung; lithium plating `Flag` | Ladder at low C-rate; drive cycles | Nat | 4 (13.4) |
| Battery cells, DFN | µ Me P | — | Doyle–Fuller–Newman as parameter-domain forms (D-FLX-38); multi-species multi-reaction OCV, as PyBaMM's MSMR [S61]; PyBaMM reference [S19][S20] | As above, plus particle-radius range | PyBaMM DFN | Nat | 5 (13.4) |
| Swelling and stack pressure | Me P | Thickness change with SOC · pad and stack springs · — | Particle expansion homogenized to cell expansion against pad stiffness; PyBaMM swelling submodels at particle scale [S63] | Expansion curve from measured cell thickness; pad stiffness from test | Thickness and force against SOC | Nat | 4 (13.4) |
| Battery packs | Me P | Series-parallel scaling · cell, busbar and thermal networks · — | Cells in 3D pack thermal and coolant flow; pseudo-4D packs | Cell spread from measurement | GP6 pack test | Nat | 4, 6 pseudo-4D |
| Battery degradation | µ Me P | Calendar and cycle fade · — · — | SEI growth, plating, particle cracking, active-material loss | `Flag` always; beyond tested duration `Invalid` (OOR-5) | Held-out ageing data | Nat | 5 |
| Abuse mechanics | Me P | — | Homogenized jelly-roll crush with failure strain, coupled to runaway screening | `Flag` always: short onset is empirical | Crush tests [unverified] | Nat | 6 (13.4) |
| Thermal runaway | Me P | ARC onset · multi-step Arrhenius · — | 3D abuse with decomposition kinetics and propagation | `Flag` always; venting and fire out of reach (OOR-14) | ARC data | Nat | 5 |
| Fuel cells and electrolysers | µ Me P | Polarization curves · 1D membrane models · — | 3D two-phase PEM with Butler–Volmer kinetics | `Flag`: water closures are empirical | Polarization curves [unverified] | Nat | 6 |
| Corrosion and electroplating | µ Me P L | Galvanic series, Faraday's law · — · — | Secondary and tertiary current distribution; cathodic protection; Nernst–Planck in crevices | Polarization data in the same electrolyte; long horizons `Flag` (OOR-5); additive chemistry empirical | Cathodic-protection cases; Hull cell [unverified] | Nat | 5 |
| Gas-phase kinetics | — | Equilibrium · reactors and flames with Cantera [S21][S22] · mechanism reduction | Finite-rate chemistry in CFD | Mechanism ranges enforced | Ignition delay | Wasm | 6 |
| Cure and crystallization kinetics | Me P | — · Kamal–Sourour cure, crystallization kinetics · — | Cure–thermal–residual-stress coupling | DSC calibration range | DSC data | Nat | 3 |

ELX owns equivalent-circuit and SPMe cells, swelling and stack pressure, and abuse mechanics; FLX owns the DFN solver (13.4). ELX also owns packs, and COV owns every row's envelope and the degradation and runaway models.

### Particles, molecules and multiscale

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Granular media | µ Me P | Angle of repose, Janssen · — · — | GPU DEM with Hertz–Mindlin and rolling resistance; Project Chrono (BSD-3) reference [S32] | Parameters from repose and shear-cell tests | Beverloo hopper | Wasm | 5 |
| Particle methods for large deformation | Me P L | — | MLS-MPM, SPH, peridynamics | `Flag`: tensile instability, numerical fracture | Column collapse; Taylor bar | Wasm | 6 |
| Molecular dynamics | N | — · — · coarse-grained MD | Machine-learned potentials (MACE, MIT code [S31]); LAMMPS (GPL-2.0) as External Op [S35] | Potential valid only in its training chemistry; model licences checked [S31] | Elastic constants | Ext | 6 |
| Multiscale coupling | N µ Me | Rules of mixtures · — · surrogate laws | FE² (D-FLX-38); FFT RVE solvers; concurrent atomistic coupling | ℓ/L ≤ 0.1; RVE convergence checked | Hashin–Shtrikman bounds | Nat; Ext concurrent | 5 |

### Plasma and radiation transport

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Gas discharge | µ Me | Paschen law · global models · — | Drift-diffusion with local-field approximation | Paschen pd range; arcs `Flag` | Paschen curves | Nat | 6 |
| Kinetic plasma | µ Me P | — | Particle-in-cell; WarpX (BSD-3-Clause-LBNL) as External Op [S33] | Debye length resolved | Two-stream growth rate | Ext | 7 |
| Magnetohydrodynamics | Me P L | Hartmann flow · — · — | Entropy-stable DG as in Trixi.jl [S28] | Ideal or resistive declared | Orszag–Tang | Nat | 7 |
| Neutron and photon transport | µ Me P L | Attenuation laws · — · — | Continuous-energy Monte Carlo; OpenMC (MIT) [S23]; CAD through DAGMC [unverified] | Data library recorded; criticality safety out of scope (OOS-2) | ICSBEP [unverified] | Ext | 7 |
| Shielding and dose | Me P L | Point kernel with buildup · — · — | Monte Carlo transport; Geant4 [S24] | Physics list and energy range declared | Slab attenuation | Ext | 6 |

### Biomechanics and human factors

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Soft tissue | µ Me P | — | Holzapfel–Gasser–Ogden; biphasic poroelasticity; FEBio (MIT) reference [S40] | `Flag` always; E4 only with V&V 40 [S8] | Confined compression | Nat | 7 |
| Implants | Me P | Beam and plate formulas · — · — | Nonlinear FEM with bone–implant contact; fatigue per ASTM F2996 [unverified] | Declared density–modulus relation | GP15 bone plate tests | Nat | 7 |
| Cardiovascular flow | Me P | Poiseuille, Womersley · Windkessel · — | ALE fluid–structure interaction | `Flag`: patient boundary conditions dominate | FDA nozzle [unverified] | Nat | 7 |
| Musculoskeletal posture | P | Anthropometric tables · — · — | Multibody with optimal control; OpenSim (Apache-2.0) reference [S41] | Population and task within data | Gait data [unverified] | Wasm | 5 |
| Human factors | P | Reach envelopes, NIOSH lifting [unverified] · — · — | Digital humans from ANSUR II (6,068 subjects, 93 measures [S47]) | Multivariate percentiles, not single-measure | Fit and reach | Nat | 5 |
| Cloth and soft goods | Me P | — | Shell or discrete elastic models with IPC contact [S26] | Fabric data from Kawabata-type tests [unverified] | Cusick drape [unverified]; GP16 | Nat | 5 |

### Manufacturing process physics

MFG owns process setups and the moulding, casting, welding, forming and chatter capabilities (13.4). COV owns constitutive draping and cure (13.4), and the models, envelopes and state Fields of every row.

| Process | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Powder bed fusion | µ Me P | Rosenthal source · — · inherent strain (13.4) | Layer-agglomerated thermo-mechanics; melt-pool thermal-fluid with Marangoni and keyhole physics | Inherent strain only for the calibrated machine, material and parameters; melt pool `Flag` outside AM-Bench conditions | AM-Bench 2018, 2022, 2025 [S11] | Nat | 1, 4 thermo-mechanical, 6 melt pool |
| Extrusion and resin printing | Me P | Bead formulas · — · — | Thermal history with bond strength; vat cure depth | Interlayer strength from tests | AM-Bench [S11] | Nat | 2 |
| Injection moulding | Me P | Flow-length ratios · Hele-Shaw filling (MFG) · — | Level-set fill; Cross–WLF, Tait pvT; ARD-RSC orientation, Folgar–Tucker as L0 [unverified: Phelps and Tucker]; pvT-path stress with frozen-layer pressure and mould constraint; crystallization; post-ejection relaxation | Rheology and pvT required | GP5 short shots and warpage; a plaque benchmark [unverified] | Nat | 3 (13.4) |
| Casting | Me P L | Chvorinov rule · — · — | VOF filling; Niyama porosity; hot-tearing indicators | Gate Weber number above breakup makes filling `Extrapolated` and indicators qualitative (OOR-8) | Casting benchmarks [unverified] | Nat | 6 (13.4) |
| Welding distortion | Me P L | Shrinkage forces · — · inherent strain (13.4) | Goldak source with phase transformation and thermo-elasto-plasticity | Source calibrated by macrograph | GP4 measured distortion | Nat | 2, 4 transient (13.4) |
| Machining and chatter | Me P | Mechanistic cutting coefficients · — · — | Stability lobes from tool-tip FRFs; semi-discretization | Coefficients per tool, material and speed | Analytic lobes | Nat | 3 (13.4) |
| Stamping and springback | Me P L | Bend allowance · — · one-step inverse | Incremental shell forming with Yld2000-2d and Yoshida–Uemori | Springback `Flag` without tension–compression data | NUMISHEET [unverified] | Nat | 2 bend, 5 forming (13.4) |
| Heat treatment | Me P | Jominy · — · — | JMAK, Koistinen–Marburger, transformation plasticity | TTT and CCT data required | Jominy data | Nat | 6 |
| Composite draping and cure | Me P L | Kinematic draping (MEC, phase 4) · — · — | Constitutive draping with shear locking; cure kinetics with process stress and spring-in | Shear below the measured locking angle; cure within DSC range | Picture-frame and bias-extension tests; spring-in coupons | Nat | 5 (13.4) |

### MEMS and piezoelectrics

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Electrostatic actuation | µ Me | Parallel-plate pull-in · spring–capacitor · macromodels | Monolithic electromechanical FEM; pull-in as a bifurcation | Bulk properties need features ≥ 1 µm | Pull-in analytic | Nat | 5 |
| Squeeze-film damping | µ | Reynolds coefficients · — · — | Rarefaction-corrected Reynolds equation; DSMC in transitional gaps | Knudsen bounds as for rarefied gas | Analytic squeeze film | Nat | 5 |
| Piezoelectric devices | µ Me P | Mason and BVD circuits · — · modal | Piezoelectric FEM with losses | Below the coercive field | Thickness-mode resonator | Nat | 5 |
| Thermal MEMS and anchor loss | µ | Zener damping · — · — | Thermoelastic eigenanalysis; PML anchor loss | Q `Flag` without fabrication data | Zener analytic | Nat | 6 |

### Civil structures and geomechanics

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Steel structures | P L | Member checks (Eurocode 3, AISC 360) [unverified] · frame analysis · — | Beams and shells with geometric nonlinearity; bolted connections | Code edition recorded | GP8 structural check | Nat | 5 |
| Timber structures | P L | Member checks (Eurocode 5) [S64] · frame analysis · — | Beams, shells and orthotropic solids with moisture | Service class declared | GP14 | Nat | 7 |
| Structural fire resistance | P L | Standard and parametric fire curves (ISO 834) [unverified] · — · — | Thermal analysis with charring (EN 1995-1-2 [S64]) and temperature-dependent degradation | Prescribed exposure only; fire growth is OOR-14 | Charring depth | Nat | 7 |
| Reinforced concrete | Me P L | Section design (Eurocode 2, ACI 318) [unverified] · frames · — | Concrete damage plasticity; smeared cracking | Nonlinear concrete `Flag` without calibration | Code examples [unverified] | Nat | 7 |
| Soil, foundations and soil–structure interaction | P L | Bearing capacity, impedance functions · Winkler springs · — | Mohr–Coulomb, hardening soil, Cam-clay; Biot consolidation; absorbing boundaries and domain reduction | `Flag` always: site data govern | Terzaghi; footing impedance | Nat | 7 |
| Seismic analysis | P L | Equivalent lateral force · response spectrum · — | Nonlinear time history with fibre beam-columns; OpenSees as reference only (commercial use needs University of California permission [S44]) | Collapse `Flag` | PEER data [unverified] | Nat | 7 |

### Marine and offshore

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Hydrostatics and stability | P L | Metacentric height · righting-lever curves · — | Exact hydrostatics over B-rep or Implicit hulls | Quasi-static; tank free surfaces declared | Box barge | Nat | 7 |
| Resistance and propulsion | P L | Holtrop–Mennen [unverified] · open-water curves · — | RANS with VOF; body-force propellers | Froude and Reynolds range of the calibration | KCS, KVLCC2 [unverified] | Nat | 7 |
| Seakeeping | P L | Strip theory · — · response amplitude operators | Potential-flow BEM with Capytaine (Apache-2.0) reference [S42]; Cummins equations | Linear waves; slamming `Flag` | Floating sphere | Nat | 7 |
| Mooring and risers | L | Catenary · lumped-mass lines · — | Nonlinear rods with Morison loads | Morison coefficients from data | Catenary | Nat | 7 |
| Marine fatigue and slamming | P L | Spectral fatigue · — · — | Wave-scatter fatigue at hot spots; VOF slamming | Slamming `Flag` always | Class-rule examples [unverified] | Nat | 7 |

### Aerospace

| Domain | Scales | L0 · L1 · L2 | L3 method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Low-speed aerodynamics and rotors | Me P L | Thin airfoil · blade-element momentum, vortex lattice, panels · — | Vortex particle methods for rotors; RANS and DDES | Panels attached flow only | GP6 rotor thrust and torque | Nat | 4 |
| Transonic and supersonic | P L | Shock-expansion · — · — | RANS and DG with shock capturing | Shock-induced separation `Flag` | ONERA M6, ATB [S1] | Nat | 6 |
| Hypersonics | P L | Modified Newtonian · — · — | Nonequilibrium Navier–Stokes; DSMC in rarefied regions | `Flag` outside verified chemistry | Double cone [unverified] | Ext | 7 |
| Aeroelasticity | P L | Divergence formulas · — · doublet lattice with modal structure | p–k flutter; CFD aeroelasticity | Transonic dip needs CFD | AGARD 445.6 [unverified] | Nat | 6 |
| Ice accretion | P L | — · Messinger energy balance [unverified] · — | Droplet impingement with surface energy balance and geometry update | `Flag` always: roughness and shedding are empirical | Icing-tunnel shapes [unverified] | Nat | 6 |
| Spacecraft thermal | P L | Equilibrium temperature · radiative node networks · — | Ray-traced exchange with solar, albedo and planetary infrared | Optical properties at a declared mission life | Flat plate | Nat | 6 |
| Launch environments | P L | Miles' equation · — · — | Random vibration and diffuse-field acoustics | Spectra from the launch provider | SDOF | Nat | 6 |
| Flight dynamics | P | Stability derivatives · 6-DoF models · — | — | Table ranges `Refuse` | GP6 flight logs | Nat | 4 |

Flux owns rigid and flexible multibody dynamics and rods (contract section 14); MEC owns the assemblies and joints they read.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Solid, dynamics and durability models | `std::physics` models with envelopes and ladders | `ValidityError` per bound; `Refuse` stops the solve | COV-O-BENCH-1, COV-O-BENCH-2 | 1 to 5 per row |
| Composite and lattice models | Laminate, failure, short-fibre and lattice envelopes | `Invalid` near boundaries; `Flag` above the buckling bound | COV-O-BENCH-2 | 1 to 4 per row |
| Thermal and fluid models | Conduction to two-phase rows; turbulence closures and wall treatments | Correlations outside range `Refuse`; separation `Flag` | COV-O-BENCH-3 | 1 to 6 per row |
| Free surface and multiphase beyond mould filling (13.4) | VOF, level set, phase field, SPH and dispersed models with resolution envelopes | Under-resolved interfaces `Flag`; breakup per OOR-8 | COV-O-BENCH-8 | 5 |
| Electromagnetic and optical models | Static to full-wave rows | Non-causal fits rejected; EMC prediction `Flag` | COV-O-BENCH-4 | 3 to 6 per row |
| Electrochemical models | Envelopes of the battery ladder, swelling and abuse rows, whose capabilities ELX and FLX own (13.4); degradation, runaway and corrosion models | Plating, degradation and abuse `Flag` | COV-O-BENCH-6 | 3 to 6 per row |
| Process models | State Fields per process | Uncalibrated machine or alloy: `Unassessed` | COV-O-BENCH-5 | 1 to 6 per row |
| Constitutive draping and cure (13.4) | Draped fibre-angle and cure-state Fields; spring-in stress | Shear above the locking angle: `Invalid` | COV-O-BENCH-9 | 5 |
| Wasm and External Op domains | Granular, particles, kinetics, MD, plasma, transport | Host failure is a `Failure`; worker loss an Abort | COV-O-BENCH-7 | 5 to 7 |
| Later-phase domains | Biomechanics, MEMS, civil, marine, aerospace | As above, per row | COV-O-VAL-1 | 3 to 7 per row |

## Scope and limits

Contract section 13.1 sets the scope. This section records COV's two scope decisions and the two lists of limits that validity errors cite.

### Building products

Whole-building authoring needs spatial and zone semantics and jurisdictional codes that BIM tools already serve, through IFC. Much of construction, though, is manufactured products with parts, BOMs and fabrication: facade units, modular pods, mass-timber connections, prefabricated steel.

**Decision D-COV-8:** Crucible designs and simulates building products and structures natively and exchanges with BIM through IFC 4.3 (ISO 16739-1:2024 [S45]). It does not author whole buildings (spaces, zones, whole-building energy). Steel structures and the IFC round trip land in phase 5 for GP8; timber, structural fire and building physics in phase 7 for GP14. *Why:* prefabricated building products are physical products with BOMs, while whole-building authoring is a different product served by mature tools through an open standard. *Rejected:* full scope (dilutes the product, duplicates BIM); none at all (abandons prefabrication). (revised in round 2)

### Chip layout and MEMS

IC physical design depends on NDA-bound process design kits and on abstractions, such as standard cells and static timing, that are not geometric physics. OpenROAD (BSD-3) already runs RTL to GDSII with open PDKs such as SKY130 and ASAP7 [S46]. MEMS, by contrast, are mechanical devices defined by mask layouts and process steps.

**Decision D-COV-9:** IC layout stays out of scope. Crucible exchanges GDSII and OASIS layer geometry for MEMS, package design and die-level thermal and stress analysis. It generates MEMS masks from Ingot through a process-emulation package (layer stack, deposition, etch). Phase 5, for GP7. *Why:* MEMS and chip packaging are physical design problems Crucible should own; logic layout is not. *Rejected:* an IC layout editor (wrong abstraction, NDA-bound data); no layout interop (blocks MEMS, a founder-named scale).

### Out of reach

These problems have no validated predictive method anywhere in October 2026; best practice is testing or calibration. Each is a record in `std::physics::limits` that validity errors cite and agents read.

| Id | Problem | Why it is out of reach | Best available approach | Crucible behaviour | Categories affected |
| --- | --- | --- | --- | --- | --- |
| OOR-1 | DNS of turbulence at product scale | Cost scales as Re^2.91 [S14], about 800 times per tenfold Reynolds number | WMLES, cost Re^1.14 [S14]; RANS in design loops | `Refuse` above the a priori budget | Vehicles, aircraft, ships, drones |
| OOR-2 | Wall-resolved LES of high-Reynolds external flow | Cost scales as Re^2.72 [S14] | WMLES with non-equilibrium wall models [S15] | Cost reported before solving | Vehicles, aircraft, ships |
| OOR-3 | Predictive RANS for smooth-body separation and corner flows | Model form dominates; equilibrium closures miss separation onset even in WMLES [S15]; a NASA CFD Vision 2030 goal [S17] | Scale-resolving simulation calibrated against tests | Separation `Flag`; model-form part inflated | Vehicles, aircraft, drones |
| OOR-4 | First-principles chemistry of whole products | A 1 kg aluminium part holds about 2×10^25 atoms | Continuum models with measured parameters; ML potentials (MACE [S31]) | DFT and MD data only as Material provenance at E1 | All |
| OOR-5 | Long-horizon degradation without test data | Coupled mechanisms; time extrapolation is uncontrolled | Accelerated tests with a declared acceleration model; Bayesian field updates | `Extrapolated` to 3× the tested duration, `Invalid` beyond | Batteries, buildings, ships, medical |
| OOR-6 | Ductile fracture and composite failure | A blind round robin of 13 teams disagreed [S12]; composite theories disagree with tests [S13] | Building-block pyramids; conservative allowables | `Flag` | Vehicles, aircraft, fabrications |
| OOR-7 | Turbulent combustion, soot and emissions | Stiff chemistry; empirical turbulence–chemistry closures | Flamelet tables; rig calibration | Always `Flag` | Machines, vehicles, aircraft |
| OOR-8 | Atomization at engineering Weber numbers | Resolved cost grows as We^(12/5) [S16] | Lagrangian sprays with calibrated breakup | Breakup `Flag`; HPDC filling `Extrapolated` above the gate threshold | Castings, machines, vehicles |
| OOR-9 | Cavitation erosion, fretting, tribochemistry | Mechanisms span atomic to part scales | Indicators plus tests | Indicators only | Mechanisms, ships, machines |
| OOR-10 | Chaotic trajectories beyond the predictability horizon | Sensitivity below floating-point resolution | Statistics with convergence error | Statistics reported; trajectories labelled | Every category with turbulent flow |
| OOR-11 | Individual-specimen life | Life depends on stochastic defects | Probabilistic life with basis values; CT defect populations | Life outputs are distributions | Printed parts, castings, aircraft |
| OOR-12 | Patient-specific biological response | Inter-subject variability and adaptation | Population models with E4 credibility | `Flag`; E4 only through V&V 40 [S8] | Medical |
| OOR-13 | Human behaviour and misuse | Not physics | Standards-based checks, user studies | Nothing beyond anthropometry | Wearables, machines, medical |
| OOR-14 | Fire spread, explosions, runaway venting | Combustion, turbulence and fracture at extreme rates | Specialist tools and physical tests | Prescribed fire curves and runaway onset only | Batteries, buildings |
| OOR-17 | Site-scale geology, weather and climate loads | Site data govern, not models | Site investigation; code loads | Site data imported with provenance | Buildings, ships |
| OOR-18 | Damping of assembled structures | Joint friction and micro-slip vary with preload, wear and assembly | Modal testing; damping per joint class | Damping is a calibrated input, never predicted | Mechanisms, fabrications, aircraft, spacecraft |
| OOR-19 | Friction and contact conductance from first principles | Surface chemistry, roughness and contamination dominate | Tribometer and conductance tests per pair | Pair data only; a missing pair is `Unassessed` | Mechanisms, machines, electronics |

### Out of scope

Mature specialist tools simulate these well; Crucible exchanges data with them.

| Id | Problem | Specialist practice | Crucible behaviour |
| --- | --- | --- | --- |
| OOS-1 (was OOR-15) | Semiconductor device physics and quantum devices | TCAD and quantum transport with process-specific calibration | Compact models, package thermal and stress only |
| OOS-2 (was OOR-16) | Nuclear criticality safety | Licensed codes with benchmark-validated nuclear data | Monte Carlo transport is an External Op and never decides a criticality check |
| OOS-3 | Superconducting magnets: quench, critical-state AC loss | Specialist electromagnetic and quench codes [unverified] | Geometry, structure and cryogenic thermal native; superconducting behaviour exchanged as Fields |

**Decision D-COV-10:** Limits are two versioned `std` record lists that validity errors cite. `OutOfReach` means no validated method exists anywhere; `OutOfScope` means mature external tools exist and Crucible exchanges data with them. An entry moves or leaves only through an evidence-backed Proposal approved by humans. *Why:* honesty about limits must be as machine-readable as coverage, and calling routine specialist simulation impossible misstates the state of the art (R1-34). *Rejected:* documentation-only limits; one list mixing impossibility with scope. (revised in round 2)

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Building products and IFC | Native design and analysis; IFC 4.3 through ECO's packages | IFC content outside the product subset kept as Assets with a note | COV-O-VAL-1 | 5 steel, 7 timber |
| MEMS layout | GDSII and OASIS layers; process emulation | Unknown layer purposes reported per layer | COV-O-VAL-1 | 5 |
| Limit records | `OutOfReach` and `OutOfScope` entries, cited by `NoCoveringModel` | Every uncovered request names an entry or the nearest package | COV-O-LIM-1 | 0 |

## Adding new physics

Coverage grows only through physics packages (D-COV-1), and std physics takes the same path as third-party physics. ECO owns the registry and its publish pipeline; COV contributes domain acceptance checks as data.

### Package contents

1. `PhysicsModel` records, each with a domain tag, model level, required Material properties, outputs, envelope, calibration classes and precision class.
2. An implementation: an Ingot weak form (preferred), a Wasm component implementing `crucible:physics/solver`, or an External Op manifest (D-COV-12).
3. Regime-variable functions for any new bounds.
4. Oracles: manufactured solutions, benchmarks and validation Evidence records by `ObjectId`.
5. An SPDX licence for code and a data licence for every dataset.

```
use std::physics::{PhysicsModel, ModelLevel, Precision, domain, envelope, bound, refuse, flag, inflation}
use std::physics::regime::{equivalent_strain, homologous_temperature}

pub fn linear_elasticity() -> PhysicsModel {
    PhysicsModel {
        id: "std::physics::solid::linear_elasticity@4",
        domain: domain::solid::linear_elastic,
        level: ModelLevel::Full3d,
        precision: Precision::F32Safe,
        requires: [Material.elastic_stiffness],
        form: elasticity_form,
        calibration: ["elasticity/regularized_peak"],
        envelope: envelope {
            bound(equivalent_strain, max) { calibrated: 0.0..=0.005, extrapolated: 0.0..=0.02,
                outside: refuse, escalate_to: [solid::finite_strain_plasticity] }
            bound(homologous_temperature, max) { calibrated: 0.0..=0.3, extrapolated: 0.0..=0.4, outside: flag }
            assume("material is homogeneous at the scale of the smallest feature")
            inflation: inflation::linear(slope: 2.0)
        },
        evidence: [oracle("COV-O-VER-1"), oracle("COV-O-BENCH-1")],
    }
}
```

The record syntax is illustrative; ING defines record and range syntax.

### Implementation routes

| Route | Use for | What the author gets | Limits |
| --- | --- | --- | --- |
| Ingot weak form | Any variational PDE system, including parameter-domain forms (D-FLX-38) | CPU and GPU kernels, form-level derivatives, estimators, Kiln caching | Methods without a weak form |
| Wasm component (`crucible:physics/solver`) | Particle, Monte Carlo, ray-tracing, BEM-kernel and Network methods | Sandboxed native speed on every Tier 1 platform and the browser | No clocks, files, network or raw GPU; randomness from counter-based streams |
| External Op | Large or copyleft codes: OpenFOAM (GPLv3 [S36]), LAMMPS (GPLv2 [S35]), SPARTA (GPL [S34]), OpenRadioss (AGPL-3.0 [S25]) | Mature solvers without linking them | Untrusted-evaluation workers only; results carry the host's class or `Unverified` |

**Decision D-COV-11:** Non-variational methods (particles, Monte Carlo transport, ray tracing, boundary elements) run their hot loops on general Flux operations: BVH build and traversal, neighbour lists, segmented reductions, counter-based random streams, and fast-multipole and hierarchical-matrix kernels. Method logic (collision laws, scattering kernels, source terms) lives in Ingot or a Wasm component. *Why:* these loops need GPUs, and Wasm components get no raw GPU access but may call GPU-backed operations through `crucible:ops/flux` (contract section 4). *Rejected:* one privileged in-tree solver per method; CPU-only Wasm solvers.

**Decision D-COV-12:** Large and copyleft external solvers run as External Ops: pinned images on untrusted-evaluation workers in single-use microVMs, without network, cached by input hashes plus the image digest. Results carry the host's class or `Unverified`, import as Fields with an `ErrorBudget`, and are pinned by `ObjectId` in releases that use them. *Why:* GPL and AGPL code is never linked (contract section 7.7), and untrusted native code never runs where attestation keys live (section 7.8, R5-03). *Rejected:* linking copyleft solvers; dropping their domains; round 1's execution on servers that also sign cache entries. (revised in round 2)

**Decision D-COV-23:** Every `PhysicsModel` declares a precision class: `F32Safe` (mixed precision with `f64` residuals evaluated canonically on the CPU) or `F64Required`. `F64Required` kernels run only on CPU classes or `f64` server GPU classes, at every fidelity. Analyses of circuits and device models are `F64Required`. *Why:* junction currents span 10⁻¹² A to 1 A, SPICE tolerances lie below `f32` resolution, and WGSL has no `f64` (R1-39). *Rejected:* round 1's `f32` execution with an added budget term, which cannot reach those tolerances.

### Acceptance and review

1. **Static checks.** The registry rejects models without envelopes, inflation, calibration classes or a precision class; bounds without a basis or a computable variable (D-COV-18); and `Refuse` bounds without an escalation or limit record.
2. **Evidence pass.** Registry CI runs the oracles in the canonical class and on each GPU class the package targets, and assigns E0 to E2. E3 needs validation Evidence records in the protected store, unseen by the author's agents.
3. **Domain review.** A std package needs two human domain reviewers with no authorship stake, one of whom confirms each E2 literature zone. Third-party packages publish at any level, which the registry shows.
4. **Use policy.** A design repository declares `min_evidence_level`; checks on models below it are `Undecided { reason: EvidenceBelowPolicy }`.
5. **Domain tags.** Namespaced; review merges duplicates.

Agents can draft packages, oracles and envelope changes; they cannot assign evidence levels, merge envelope widenings or approve reviews.

[[DIAGRAM: Physics package acceptance, left to right: "Author (person or agent)" → "Package: models, envelopes, oracles, licences" → "Static checks (ECO pipeline, COV checks)" → "Evidence pass, canonical and target GPU classes" → "E0 to E2" → "Protected validation Evidence records" → "E3" → "Two human domain reviewers" → "Coverage map in api". Typed-error arrows return from the static checks and the evidence pass to the author.]]

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Physics packages | Model exports with oracles and licences | Registry rejects incomplete packages with typed errors | COV-O-PKG-2 | 1 |
| Weak-form models | Compiled by Flux with derivatives and estimators | `FormError` at compile time (FLX) | COV-O-VER-1 | 1 |
| Solver Wasm components | `crucible:physics/solver` on `crucible:ops/flux` | Determinizer rejection | COV-O-BENCH-7 | 2 |
| External Op solvers | D-COV-12 | Host failure is a `Failure`; worker loss an Abort | COV-O-PKG-1 | 3 |
| Precision classes | `F32Safe` or `F64Required` per model | The plan places `F64Required` kernels on a CPU or `f64` class and says so | COV-O-PKG-3 | 1 |
| Use policy | `min_evidence_level` per repository | `Undecided { reason: EvidenceBelowPolicy }` | COV-O-VER-3 | 1 |
| Domain tags | Namespaced; duplicates merged | A duplicate tag is rejected with the existing name | COV-O-PKG-2 | 1 |

## Materials system

A Material is a versioned, content-addressed record, pinned in `ingot.lock`, so a property change never alters an existing design silently. `std::materials` ships the open library; licensed data arrive as External inputs through connector packages and stay in the customer's private registry.

### Data model

```rust
pub struct Material {
    pub id: MaterialId,                      // "std::materials::alu_6061_t6"
    pub version: SemVer,
    pub class: MaterialClass,                // Metal | Polymer | Ceramic | Glass | Composite | Fluid
                                             // | Biological | Granular | Electrochemical | Other(DomainTag)
    pub designations: Vec<Designation>,      // UNS, ASTM, EN, JIS, ISO, SAE AMS, GB
    pub condition: Condition,                // temper, heat treatment, product form, thickness, build orientation
    pub properties: BTreeMap<PropertyId, Property>,
    pub models: Vec<ConstitutiveBinding>,    // ConstitutiveModel id@version, parameters, envelope
    pub provenance: Provenance,              // sources, test records, calibration Ops, approvals
    pub licence: DataLicence,                // joins Labels.licences (D-COV-15)
    pub certifications: Vec<Certification>,
    pub environment: Vec<EnvironmentalRecord>,
    pub microstructure: Option<MicrostructureDescriptor>,
}

pub struct Property {
    pub value: PropertyField,  // a Field over state domains, e.g. Field<(Temperature, StrainRate), Stress>
    pub basis: BasisSet,       // Typical; SpecLimit; A- and B-basis, lower and upper; Design { code, clause }
    pub uncertainty: Uncertainty, // aleatory, epistemic or both (D-COV-22)
    pub coverage: CalibratedRegion, // where data exist; feeds validity
    pub sources: Vec<SourceRef>,
}
```

**Decision D-COV-14:** Material properties are Fields over product domains of quantity types, such as temperature and strain rate. Spatial variation enters through state Fields on the Part, never through a second property type. *Why:* one Field type then covers temperature dependence, anisotropy and process-induced variation, and evaluation composes as property(state Fields) → `Field<Body, V>`. *Rejected:* a separate "material curve" type; per-element material copies.

**Decision D-COV-13:** Property reads resolve to a statistical basis on the side the check needs. Form-level derivatives give the sign of the check's sensitivity: the lower value applies when the margin grows with the property, the upper otherwise. Where the sign varies over the check's inputs, both sides are evaluated and the worse kept. Repository policy names the basis (default: specification limit, else B-basis, else error), and every check report names basis and side. *Why:* low stiffness, conductivity or expansion is unconservative in thermal-stress, heating and frequency checks (R1-51), and `0.6 * yield` must mean one auditable number. *Rejected:* always the lower value (round 1); typical values by default; an explicit basis at every read. (revised in round 2)

A-basis and B-basis values cover 99% and 90% of the population with 95% confidence [handbook definitions unverified]. 14 CFR 25.613 requires them for single-load-path and redundant structure [S51]. A designation's "nearest" equivalent never satisfies a specification check.

### Assignment and state

A Part's material assignment is a versioned Material reference, an orientation `Field<Body, Rotation>` and named state Fields: residual stress, plastic strain, porosity, fibre orientation, phase fractions, cure and damage. Process models write state Fields and downstream models read them; without one, the as-specified condition applies and the assumption is recorded.

### Uncertainty

**Decision D-COV-22:** Material uncertainty is typed as `Aleatory { distribution, group }`, `Epistemic { interval }` or both, and correlation is declared only through named correlation groups across properties and Materials. Flux propagates intervals by nested sampling and reports probability boxes, never summed with distributions. *Why:* Sobol indices are ill-defined for correlated inputs, so Flux needs the groups for grouped indices and Shapley effects, and summing intervals with distributions overstates confidence (R1-36). *Rejected:* round 1's free correlation matrix; one distribution type for both kinds.

Input error propagates through `std::uq` by first-order adjoint sensitivities by default. At `SignOff`, randomized quasi-Monte Carlo with an explicit seed takes over when a second-derivative estimate exceeds 10% of the first-order term (target). A property read at a basis value already covers its aleatory scatter, so propagation covers the other properties and the epistemic parts.

### Constitutive-model library

A `ConstitutiveModel` is an Ingot function or a Wasm component implementing `crucible:material/constitutive` (contract section 7.4). It maps state, internal variables and time step to flux-like quantities and updated internal variables, and declares its thermodynamic structure, parameters, admissibility constraints and envelope. Kernel-IR models get tangents by algorithmic differentiation, with local Newton updates in `local_solve` rather than differentiated loops (R1-25). Opaque Wasm models supply tangents verified by FLX-O-FORM-3.

| Family | Models in `std::materials::models` | Phase |
| --- | --- | --- |
| Elastic | Isotropic and anisotropic, temperature-dependent; small-strain thermoelasticity | 1 |
| Hyperelastic | Neo-Hookean, Mooney–Rivlin, Yeoh, Ogden, Arruda–Boyce, Gent; hyperfoam; Holzapfel–Gasser–Ogden | 2 |
| Viscoelastic | Generalized Maxwell (Prony) with WLF and Arrhenius shifts; Bergström–Boyce | 3 |
| Plasticity | J2 with isotropic, Chaboche and Yoshida–Uemori hardening; Hill48; Yld2000-2d; Johnson–Cook; Zerilli–Armstrong; crushable foam; Drucker–Prager | 2 |
| Creep and viscoplasticity | Norton–Bailey, Garofalo, theta projection; Perzyna and Chaboche | 3 |
| Damage and fracture | Lemaitre; Gurson–Tvergaard–Needleman; Johnson–Cook and Hosford–Coulomb loci; cohesive laws; phase-field energy | 3 |
| Composites | Ply elasticity and strength; Tsai–Wu, Hashin, Puck, LaRC05; continuum damage | 4 |
| Concrete and geomaterials | Concrete damage plasticity; Mohr–Coulomb; modified Cam-clay; hardening soil | 7 |
| Smart materials | Linear piezoelectricity; superelastic shape-memory alloys | 5 |
| Magnetic | B–H splines; Jiles–Atherton and Preisach hysteresis; Bertotti loss separation | 3 |
| Dielectric and optical | Debye, Cole–Cole, Lorentz–Drude; Sellmeier and Cauchy; measured BSDFs | 4 |
| Thermal | Fourier conduction with cumulative mean-free-path curves; enthalpy phase change; emissivity spectra | 1 |
| Polymer melts and fluids | Ideal gas; Peng–Robinson; CoolProp equations of state [S43]; Cross–WLF, Carreau–Yasuda, Herschel–Bulkley; Oldroyd-B, Giesekus; Tait pvT; ARD-RSC closures; crystallization kinetics | 3 |
| Electrochemical | Butler–Volmer; open-circuit potentials with hysteresis and multi-species multi-reaction forms; concentration-dependent transport | 4 |
| Moisture | Sorption isotherms; diffusivity; hygro-expansion and mechano-sorptive coefficients | 3 |
| Durability | S–N with mean-stress models; ε–N; NASGRO-form da/dN; Archard coefficients per pair | 1 to 3 |
| Contact pairs | Coulomb and rate-and-state friction; thermal contact conductance per pair | 2 |

Admissibility oracles run before release: objectivity under superposed rotation, non-negative dissipation, strong ellipticity (Legendre–Hadamard) over the envelope for finite-strain models and a positive-definite tangent for small-strain ones, convexity where theory requires, and causality and passivity for dispersive models. MFront behaviours (GPL with linking exception or CeCILL-A [S30]) are the largest open catalogue. Crucible compiles their generic-interface C++ to Wasm components, subject to legal review.

### Calibration from test data

Calibration turns test records into a Material version through Ops that Kiln caches and `repo` versions.

1. **Ingest.** Records follow ISO 10303-235:2019, which covers measured values and the qualifications of those responsible [S53]. Signed rig measurements arrive as Evidence records citing method (for example ASTM E8/E8M [unverified]), specimen, conditions and raw curves.
2. **Reduce.** True stress and strain, toe compensation and filtering, each a declared Op.
3. **Identify.** Least squares with derivative-based gradients; finite-element model updating for non-uniform specimens; the virtual fields method for DIC data.
4. **Quantify.** Laplace approximation, or Markov chain Monte Carlo with an explicit seed; correlations become correlation groups.
5. **Bound.** The calibrated region is the hull of test conditions; the calibrator declares the extrapolated region with a rationale.
6. **Admit.** Admissibility oracles run over the whole envelope, not only at test points.
7. **Allowables.** With enough replicates, basis values come from one-sided tolerance limits per CMH-17 [S57] or MMPDS [S50] [procedure details unverified].
8. **Publish.** The new version enters a Proposal with fit residuals, held-out error, parameter uncertainty, envelope and the `ObjectId`s used. The evidence pass rejects overlap with validation data (contract section 13.1).

### Material databases and licensing

**Decision D-COV-15:** Every Material carries a typed `DataLicence` in the `licences` element of its labels. Kiln joins it through every derivation, and `api` enforces it at every boundary (contract section 5). Each licence states terms for embedded values and for derived results, and export and release checks refuse what the terms forbid. *Why:* licences differ sharply, and a design shared with a supplier must not leak licensed tables. *Rejected:* tracking licences by hand; refusing licensed data, which loses MMPDS and Granta users; round 1's separate propagation mechanism beside the label lattice. (revised in round 2)

| Source | Content | Licence (as verified) | Integration | Phase |
| --- | --- | --- | --- | --- |
| `std::materials` | Curated open library with sources per value | Each value cites a public or openly licensed source | Built in | 1 |
| NIST Standard Reference Data | 49 free and 41 fee-based databases, including REFPROP and ICSD [S52] | Terms vary by database [unverified] | Connector per database; fee-based ones need a customer licence | 3 |
| Materials Project | Computed (DFT) properties of inorganic compounds | CC BY 4.0 for downloads; no scraping; data "computed, and may not be accurate enough" [S54] | ICME connector; E1 at most | 5 |
| MMPDS | Allowables for aerospace metals and fasteners; MMPDS-2026 current [S50] | Purchased handbook [terms unverified] | Customer-licensed connector | 6 |
| CMH-17 | Composite data, test and statistics guidance [S57] | Licensed [terms unverified] | Customer-licensed connector | 6 |
| Ansys Granta MI | Materials data management; 250,000+ reference materials; MaterialUniverse environmental data [S49] | Commercial | Connector through the customer's Granta API [API unverified] | 5 |
| MatWeb | Datasheet aggregation | Terms forbid redistribution, mass export and collecting more than 500 materials [S48] | None | — |
| Plastics databases (CAMPUS, UL Prospector) | Grades with rheology and pvT | [unverified] | Connector if licensing allows | 3 |
| CoolProp | Fluid thermophysical properties | MIT [S43] | Built in | 3 |
| ICE embodied carbon | 200+ construction materials; V5.0 Educational, June 2026 | Educational use only; software needs the licensed IC+ dataset [S55] | IC+ connector under customer licence | 5 |
| ecoinvent | Life-cycle inventory | A developer licence grants integration rights; tool users receive LCIA data only [S56] | Connector under a developer licence | 5 |

### Microstructure and ICME

A `MicrostructureDescriptor` records grain size distribution, texture, phase fractions, porosity and defects, fibre architecture and lattice cells, with measurement provenance; spatial variation is a state Field. Each ICME link carries its own envelope, so a chain is only as valid as its weakest link; chains are validated against AM-Bench data [S11].

| Link | Method | Delivery | Phase |
| --- | --- | --- | --- |
| Process to microstructure | Thermal histories into JMAK, Koistinen–Marburger and solidification maps | Nat | 6 |
| Microstructure to properties | Hall–Petch, rules of mixtures, Mori–Tanaka; FFT RVE solvers with crystal plasticity | Nat, Wasm | 5 |
| Thermodynamics | CALPHAD through customer-licensed tools or open implementations [unverified] | Ext | 6 |
| Atomistic to continuum | DFT and ML-potential results as provenance (MACE [S31]; Materials Project [S54]) | Ext | 6 |
| Exchange with process tools | VMAP data-interface standard [S58] | Interop | 5 |

### Environmental data

An `EnvironmentalRecord` gives global warming potential per unit mass by life-cycle stage, embodied energy, water use, recycled content, recyclability and restricted substances. Each value carries geography, reference year, system boundary (cradle-to-gate, cradle-to-site, cradle-to-grave), method standard, source, licence and uncertainty. MFG owns product life-cycle assessment and passports (contract section 14); COV owns the per-material records.

**Decision D-COV-16:** Environmental values follow the same provenance, uncertainty and licence rules as mechanical properties, and an embodied-carbon check reports the boundary and year it used. *Why:* carbon numbers vary by source and boundary more than most mechanical properties do. *Rejected:* a single "CO2 per kg" number per Material.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Property Fields | Fields over state domains with declared interpolation | Reads outside `coverage` are `Extrapolated` or `Invalid`, never clamped | COV-O-MAT-8 | 1 |
| Directional properties | Tensors in a material frame with a symmetry class | Ill-formed tensor rejected with the failing eigenvalue | COV-O-MAT-1 | 1 |
| Units | Every property a `Quantity<D>` | Compile error | COV-O-MAT-2 | 0 |
| Statistical basis | Lower and upper bases; side by sensitivity sign | `MissingBasis { available }` | COV-O-MAT-6 | 1 |
| Uncertainty | Aleatory with groups; epistemic intervals | Input part `NotQuantified` | COV-O-ERR-1 | 2, 3 epistemic |
| Designations and certification | Equivalence basis; specification and lot-certificate links | "Nearest" fails specification checks; a missing certificate fails release | COV-O-MAT-7 | 1, 3 certification |
| Constitutive library | `crucible:material/constitutive`; `local_solve` tangents | Inadmissible models do not register; `TangentInconsistent` | COV-O-MAT-1 | 1 to 7 per family |
| Calibration | `calibrate(model, tests) -> (ConstitutiveBinding, CalibrationReport)`; inverse, full-field and model selection | Non-identifiable parameters reported with their null space; ties never broken silently | COV-O-MAT-3 | 2, 3 inverse, 5 DIC |
| Allowables | Replicates to A- and B-basis values | `InsufficientSamples { needed }` | COV-O-MAT-4 | 3 |
| Data licences | `DataLicence` in the label lattice | Forbidden export or release refused, naming the licence | COV-O-MAT-5 | 3 |
| Connectors | External inputs pinned in `ingot.lock` | Fetch failure keeps the pinned version | COV-O-MAT-7 | 3 |
| Microstructure and ICME | Descriptors, state Fields, linked envelopes | A chain is zoned by its weakest link | COV-O-BENCH-5 | 5, 6 |
| Environmental records | Boundary, year, source, licence per value | `BoundaryMismatch` when a check mixes boundaries | COV-O-MAT-9 | 5 |

## State of the art

Targets are measured on contract section 13.3's reference laptop or a named GPU. Copyleft leaders are measured against as External Ops, never linked; FLX's table covers numerical methods, lattice Boltzmann and particles.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Validity and credibility | Risk-informed credibility: ASME V&V 40-2018 [S8], NASA-STD-7009B [S9], FDA guidance of November 2023 [S10]; validation per V&V 10-2019 [S65] and V&V 20 [S7] | Commercial CAE states validity in documentation, not data [unverified] | Envelopes compiled to checks; zone Fields; V&V 20 model-form metric | Target: every std model has a cited envelope before E2 |
| Code verification | Manufactured solutions; NAFEMS P18 [S2] | Verification manuals such as MSC Nastran 2021.01, as NAFEMS lists them [S5] | Manufactured solutions for every std form; full P18 coverage | Target: P18 values within 1% [S3][S4] |
| Contact | Mortar contact; Incremental Potential Contact [S26] | IPC Toolkit (MIT) [S26] | Mortar by default; IPC for cloth, snap fits and soft parts | NAFEMS R0094 [S5]; target: Hertz peak pressure within 1% |
| Fatigue | Multiaxial critical plane with probabilistic S–N | Commercial durability tools [unverified] | Critical plane with basis-aware life distributions (OOR-11) | Target: 90% of held-out lives within a factor of 3 |
| Fracture | Phase field, cohesive zones, calibrated ductile damage | Entrants of the Sandia Fracture Challenge [S12] | Cohesive and phase-field defaults; ductile `Flag` | Sandia data [S12]; target: enter the next blind round |
| Composite failure | Building-block calibration of LaRC05 and Puck | Theories assessed in WWFE-II [S13] | Criteria library with calibration; progressive failure `Flag` | WWFE-II [S13]; GP10 coupon-to-component pyramid |
| Turbulence models | SA, SST, GEKO and transition as the NASA TMR documents them [S1] | SU2 (LGPL-2.1) [S37]; OpenFOAM (GPLv3, External Op only) [S36] | Native models on TMR definitions | Target: within the reference codes' spread on the finest grid [S1] |
| Scale-resolving CFD | High-order DG and flux reconstruction on GPUs; non-equilibrium wall models [S15]; Yang–Griffin cost [S14] | PyFR (BSD) [S27]; Trixi.jl (MIT) [S28] | Entropy-stable DG on Flux GPU back ends | 2DWMH [S1]; target: cost per DOF per stage within 1.5× of PyFR |
| Multiphase | VOF, level set, phase field; resolution k_max·η_KH ≥ 60 [S16] | [unverified] | Native, with a priori resolution | Interfacial statistics converge per [S16] |
| Rarefied gas | DSMC | SPARTA (GPL) [S34] | External Op; native slip models | Microchannel analytic; code-to-code |
| Electromagnetics | Nédélec FEM with Newton on B–H; high-order FEM with model reduction | Palace (Apache-2.0) [S18]; commercial low-frequency tools [unverified] | Native | Targets: TEAM 7 and 13 probe errors under 5% [S6]; eigenfrequencies within 0.1% of Palace |
| Optics | Differentiable spectral and polarized Monte Carlo transport | Mitsuba 3 [S39] | Native on Flux BVH operations | Target: equal-noise time within 2× of Mitsuba 3 |
| Batteries | DFN with thermal coupling; multi-species multi-reaction OCV [S61] | PyBaMM (BSD-3) [S19][S20] | Native ladder from equivalent circuits to DFN | Targets: terminal voltage within 1 mV RMS of PyBaMM; 10× faster sweeps |
| Fibre orientation | Anisotropic rotary diffusion with reduced strain closure [unverified: Phelps and Tucker] | Commercial moulding simulation [unverified] | ARD-RSC with a fitted closure; Folgar–Tucker as L0 | GP5 short shots and warpage |
| Chemical kinetics | Detailed mechanisms in reactor networks and 1D flames | Cantera (BSD-3) [S21][S22] | Wasm component; Cantera mechanisms imported [format unverified] | Target: equilibrium and ignition delay within 0.1% |
| Atomistic | Equivariant machine-learned potentials | MACE (MIT code, model licences vary) [S31]; LAMMPS (GPLv2) [S35] | External Ops; results as Material provenance | Elastic constants within the model's published error |
| Plasma and radiation | Particle-in-cell (WarpX, 2022 Gordon Bell Prize [S33]); Monte Carlo (OpenMC [S23], Geant4 [S24]) | The same codes | External Ops | Analytic cases; code-to-code |
| Biomechanics | Fibre-reinforced hyperelastic FE; musculoskeletal optimal control | FEBio (MIT) [S40]; OpenSim (Apache-2.0) [S41] | Native FE; Wasm musculoskeletal models | Code-to-code against FEBio |
| Seakeeping | Potential-flow BEM with Cummins time domain | Capytaine (Apache-2.0) [S42] | Native BEM on Flux fast-multipole operations | Target: added mass and damping within 1% |
| Additive process | Inherent strain, part-scale thermo-mechanics, melt-pool CFD | Entrants of the AM-Bench blind challenges [S11] | Native | Target: blind predictions inside measurement uncertainty for most quantities |
| Constitutive authoring | Domain-specific languages generating integration code | MFront 5.2 (GPL with linking exception or CeCILL-A) [S30] | Ingot behaviours with derivatives and `local_solve`; MFront import as Wasm | Target: stress updates within 10⁻¹⁰ relative of MFront tests |
| Materials data | Data management with traceable tests | Ansys Granta MI [S49]; ISO 10303-235:2019 [S53] | Versioned records; licences in the label lattice | ISO 10303-235 round trip |
| Allowables | One-sided tolerance limits per CMH-17 and MMPDS [S57][S50] | Handbook procedures and their software [unverified] | Native, with `InsufficientSamples` | Target: worked examples to 3 significant figures |

## Platform notes

- **Double precision on GPUs.** WGSL defines `f32` and an optional `f16` extension [S29] and no `f64` [unverified against the latest draft]. An Apple WebGPU engineer said Metal-based implementations would not offer an `f64` extension [S59]. Precision classes (D-COV-23) keep `F64Required` models on CPU classes and `f64` server GPUs.
- **Browser memory.** Wasm memory64 is not on every engine [S60]. Browser sessions follow PLT's browser memory table: a 1.5 GiB engine worker, a heavy worker above 512 MiB, remote beyond. Remote results are the same canonical results.
- **Relaxed SIMD.** It ships in Chrome 114 and Firefox 145 and is behind a flag in Safari [S60]. Its results vary by hardware, so `Portable` physics code never uses it.
- **External Ops.** They run on Linux untrusted-evaluation workers, reached remotely from every client; air-gapped installs need a local Linux worker (contract section 9).
- **Monte Carlo determinism.** Particle and transport methods use counter-based streams keyed by the class-independent part of the Op key. Reductions run in fixed order, so results are bit-identical within a class at any thread count.
- **Zones.** Canonical zones are identical everywhere; other classes report `NearBound` regions (R1-45).
- **Material data offline.** Connectors fetch only at import time, outside evaluation; the records are External inputs pinned in `ingot.lock`, so builds run air-gapped.

## Interfaces with other subsystems

### What COV provides

| To | What COV provides | Types |
| --- | --- | --- |
| FLX | Physics models and constitutive models with tangents; regime functions and envelopes; the calibration-class map; turbulence, fatigue, fracture and damage models; D-COV-11's operation needs | `Field`, `Material`, `ValidityEnvelope` |
| ING | `std::physics` and `std::materials`; envelope record syntax needs | Ingot packages |
| KLN | Envelope and Material records as CAS inputs; calibration chains as Ops; External Op keys (D-COV-12); `DataLicence` values for the label lattice; `Material` composition (each `EnvironmentalRecord`'s restricted substances) for compliance roll-ups | `Op`, `Labels`, `Material` |
| `repo` | Material versions; waivers; validity, certification and licence release checks | `Material`, `CheckOutcome` |
| AGT and `api` | Coverage map; limit records; validity envelopes; typed `ValidityError`s with escalation; calibration Ops | Read and Inspect methods |
| UIX | Zone Fields with their assumptions; budget displays with the model-form part; basis citations; escalation options | `Field<Body, ValidityZone>` |
| MEC | Materials with yield, locking angle and process windows; solid, contact, joint, fatigue and dynamics models with envelopes; the basis side per check; constitutive draping in phase 5 (13.4) | `Material`, `PhysicsModel` |
| MFG | Process models and `ValidityEnvelope`s for cutting, melts, cast alloys, forming, transformation and cure; state Fields; OOR-8; per-material environmental records for product LCA | `Field`, `ValidityEnvelope`, `EnvironmentalRecord` |
| ELX | Dielectric, copper, magnetic and cell Materials with envelopes; electromagnetic (EMC included), thermal and electrochemical models with envelopes; precision classes | `PhysicsModel`, `Material` |
| ECO | Domain acceptance checks for the registry; semantics of the `crucible:physics` and `crucible:material` worlds; material semantics for MatML; OpenFOAM case semantics with FLX | Package |
| PLT | Precision classes per model; External Op worker needs | Model metadata |

### What COV requires

| From | Requirement |
| --- | --- |
| FLX | Forms and solvers; estimators, the calibration corpus and η99 tables; solution verification; parameter-domain forms; per-region reduction and localization; regime-variable Fields and zone evaluation; coupling algorithms; `std::uq`; the D-COV-11 operations |
| ING | Records, enums, `Range` as interval and kinds for parameter domains; typed regime functions; `require`; `CheckOutcome` with `conditional_on`; the `Truth` decision rule |
| KLN | Deterministic calibration and External Op evaluation; label joins; Evidence record lookup; two-builder agreement at `SignOff` |
| `repo` | Human-only waivers and envelope approvals; policy allowances with citations; `min_evidence_level` |
| ECO | The registry, its publish pipeline with domain acceptance checks, and package metadata for the coverage map; hosting for solver and constitutive Wasm components; IFC 4.3, GDSII, OASIS, MatML and ISO 10303-235 codecs |
| ANV | Implicit and lattice Bodies; mid-surfaces and member axes; per-entity tolerances |
| MEC | Laminate data (plies and kinematic draping) and part data for envelopes; which mechanical checks need calibrated classes |
| MFG | Process setups and data for the process capabilities it owns |
| ELX | Equivalent-circuit and SPMe cells, swelling and stack pressure, and abuse mechanics (13.4); packs; the electrical use of physics models |
| PLT | `linalg` for calibration fits; `f64` availability per class; the browser memory table |

## Oracles

Oracles live in the protected directory `oracles/cov/`; agents can read them but not write them. Held-out validation Evidence records live in a store agents never see.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| COV-O-MAP-1 | Coverage map | Rows match package metadata; `Planned` rows excluded from counts |
| COV-O-VER-1 | Manufactured solutions for every std weak form | Observed order within 0.1 of the declared order over three refinements, stopping once the error is below 10³ times the round-off floor |
| COV-O-VER-2 | Model-ladder consistency (D-COV-2) | Per ladder inside the narrower envelope; for example tip deflection within 1% of 3D at L/h ≥ 20 |
| COV-O-VER-3 | Evidence levels and use policy | Levels change only through CI-signed results; agent credentials cannot set them; below-policy models give `Undecided` |
| COV-O-VER-4 | Solution-verification status | No result with status `None` decides a `SignOff` check on the labelled corpus |
| COV-O-ERR-1 | Input propagation from Material uncertainty | Mean and variance within 2% of a high-sample reference; epistemic inputs reported as probability boxes, never summed |
| COV-O-ERR-2 | Calibration-class map | Every std model with an `Estimated` estimator names a class with an η99 entry; removing the entry yields `Indicator` |
| COV-O-ERR-3 | Conditional passes | Labelled E2 cases give `Pass { conditional_on: [ModelForm] }`; `Undecided` at a gate without an allowance; a re-evaluated verdict with one |
| COV-O-VAL-1 | Golden-product validation | Checks hold against physical tests where the gate includes them, with contract section 13.1 replicates and Calibrated zones on critical regions |
| COV-O-VAL-2 | Model-form metric and inflation | On synthetic cases with known model error, the bound covers the truth at the declared confidence; calibration and validation `ObjectId`s disjoint |
| COV-O-ENV-1 | Envelope completeness | Every model has an envelope, inflation, calibration classes and a precision class; every bound a basis; every `Refuse` bound an escalation or limit record (exact) |
| COV-O-ENV-2 | Zone assignment, including joint hulls | Synthetic regime Fields give the expected zone Field (exact) |
| COV-O-ENV-3 | Zones across classes | Canonical zones identical on golden models; other classes differ only inside `NearBound` bands |
| COV-O-ENV-4 | `Refuse` behaviour | Dependent checks blocked; `OutsideEnvelope` emitted with fixes (exact) |
| COV-O-ENV-5 | Human-only waivers and widening | Agent credentials cannot create waivers or merge widenings (exact) |
| COV-O-ENV-6 | Regime computability and missing inputs | Every bound variable resolves to a typed function; a missing input gives `Extrapolated` with a documented default, `Unassessed` without |
| COV-O-ENV-7 | Surrogate envelopes | Out-of-distribution queries land in Extrapolated or Invalid; with FLX-O-ROM-2, no surrogate-backed `SignOff` `Pass` that the full solve fails |
| COV-O-ENV-8 | Coupling envelopes | One-way coupling `Invalid` on labelled flutter-prone, light-panel and heavy-fluid cases; valid on separated controls |
| COV-O-BENCH-1 | NAFEMS P18 LE, FV and T benchmarks | Within 1% of reference values |
| COV-O-BENCH-2 | NAFEMS groups R0024, R0027, R0094, R0020 and R0031; lattice references | Per benchmark |
| COV-O-BENCH-3 | NASA TMR cases and thermal-fluid references | Within the reference codes' spread on the finest grid |
| COV-O-BENCH-4 | TEAM 7, 13 and 36; electromagnetic and optical references | Within published measurement uncertainty |
| COV-O-BENCH-5 | AM-Bench blind predictions and process references | Inside measurement uncertainty for most quantities |
| COV-O-BENCH-6 | Battery ladder | SPM, SPMe and DFN consistent at low C-rate; DFN within 1 mV RMS of PyBaMM on shared parameters (target); hysteresis model against measured LFP cycles |
| COV-O-BENCH-7 | Wasm and External Op domains | Code-to-code within the State of the art targets |
| COV-O-BENCH-8 | Free surface and multiphase | Dam break and rising bubble references; interfacial statistics converge per [S16]; filled volume conserved to solver tolerance |
| COV-O-BENCH-9 | Constitutive draping and cure | Shear angles against picture-frame and bias-extension data; cure against DSC; spring-in against measured coupons |
| COV-O-LIM-1 | Limit records | Every `NoCoveringModel` error cites an `OutOfReach` or `OutOfScope` record; records change only through approved Proposals |
| COV-O-PKG-1 | External Op determinism and placement | Reruns from one image digest identical or within declared tolerance; never on trusted builders; results carry the host class or `Unverified` |
| COV-O-PKG-2 | Package acceptance | Seeded incomplete packages rejected with the right typed error; std packages need two non-author reviewers |
| COV-O-PKG-3 | Precision classes | No `F64Required` kernel runs in an `f32` class; `F32Safe` residuals checked canonically |
| COV-O-MAT-1 | Admissibility and tangents | Every admissibility condition holds over each envelope (exact or 10⁻¹² relative); Taylor tests per FLX-O-FORM-3 |
| COV-O-MAT-2 | Units | Every property dimension-checks; affine temperatures handled (compile time) |
| COV-O-MAT-3 | Calibration recovery | Known parameters recovered from noisy synthetic data; 95% intervals cover the truth within 2 points of nominal |
| COV-O-MAT-4 | Allowables | Published worked examples reproduced to 3 significant figures |
| COV-O-MAT-5 | Licence propagation | Exporting a design that embeds licensed values fails; exporting derived results succeeds where the terms allow (exact) |
| COV-O-MAT-6 | Basis side | Synthetic checks with rising and falling margins pick the lower and upper basis; mixed signs evaluate both |
| COV-O-MAT-7 | Records, designations, certification, connectors | ISO 10303-235 round trip lossless; "nearest" equivalents fail specification checks; no fetch during evaluation |
| COV-O-MAT-8 | Property Fields | Interpolation exact at tabulated nodes; monotone where declared; out-of-coverage reads zoned, never clamped |
| COV-O-MAT-9 | Environmental records | Every carbon check reports boundary and year; mixed boundaries fail |

## Phasing

Phases of shared capabilities follow contract section 13.4; golden products 7 to 16 are proposals (contract section 13.1).

| Phase | COV's contribution to the gate |
| --- | --- |
| 0 | Envelope schema and completeness; regime-variable mechanism; evidence levels; Material records and units; the coverage map with `Planned` status; limit records |
| 1 | GP1 and GP2: linear elasticity, modal analysis and linear buckling, conduction, stress-life fatigue, lattice envelopes with localized strut stresses, inherent-strain distortion; metals and print polymers with specification-limit bases; E2 checks passing on cited allowances |
| 2 | GP3 and GP4: plasticity, mortar contact, shells, beams and frames, joints, lubrication, vibration, rotordynamics, strain-life and weld fatigue, weld distortion by inherent strain, bend allowances, calibration Ops; the weld-distortion model at E3 |
| 3 | GP5: viscoelasticity, creep, crack growth, moisture, laminar and natural conjugate heat transfer, radiation, moulding models with ARD-RSC orientation, drop, electrostatics, magnetostatics, acoustics, chatter, allowables, connectors; warpage and drop models at E3 |
| 4 | GP6: RANS and turbulent conjugate heat transfer, rotor aerodynamics and acoustics, motors, Joule heating, antennas, EMC emissions, equivalent-circuit and SPMe cells, swelling, laminates, two-phase heat transfer, flight dynamics; models validated against flight, dynamometer and thermal tests |
| 5 | GP7 MEMS, GP8 steel platform with the IFC structural check, GP9 crash box; DFN cells, free surface and multiphase, draping and cure, sheet forming, scale-resolving CFD |
| 6 | GP10 wing box, GP11 CubeSat, GP12 battery sub-pack: aeroelasticity, transonic flow, ice accretion, spacecraft thermal, launch environments, dose, abuse mechanics, pseudo-4D packs, casting |
| 7 | GP13 hull, GP14 timber pavilion (timber, structural fire, IFC export), GP15 bone plate (V&V 40 package), GP16 sewn pack; marine, geomechanics, seismic, plasma and radiation transport |

## Open questions

1. **Envelope cost on large transients.** Regime Fields at every saved step may exceed 2% of the solve. Should assessment run at output steps only, with a declared sampling risk?
2. **Joint-hull dimensionality.** Hulls of validation points in more than about six regime dimensions are sparse. Is a Gaussian-process density over regime space a better calibrated-region model?
3. **Citable model-form allowances.** Which design-code clauses state that their factors cover model uncertainty, per model class? COV proposes a std catalogue with ING and MEC.
4. **Default inflation functions.** Should std publish a default g(d) per domain once enough E3 models exist?
5. **Fortran UMAT import.** Is a Fortran-to-Wasm toolchain mature enough on every Tier 1 platform for industrial UMATs?
6. **Legal review of data licences.** NIST SRD, MMPDS, CMH-17, CAMPUS and Granta API terms, including their terms for derived results, need counsel before connectors ship.
7. **Test partners.** GP7 to GP16 need physical test partners and data rights.
8. **Tool qualification.** Regulated industries need qualified tools, for example under DO-330 [unverified]. Should a subset of std physics pursue qualification in phase 6 or later?
9. **Emulated `f64`.** Is double-float emulation on WebGPU accurate and fast enough for `SignOff` solves of `F64Required` models?
10. **Calibration classes for phase 1.** FLX proposes classes and COV confirms them (FLX open question 1).
11. **Findings applied in part.**
    - R1-32: the status lives in the generated map; this tab's matrix shows planned phases.
    - R1-01, R1-02, R1-04, R1-07, R1-08, R1-21 to R1-25, R3-08 and R5-03: applied to COV's rows, envelopes and records; the machinery is FLX's or the contract's.
    - R1-36 and R1-39: COV owns the uncertainty representation and precision classes; FLX owns the methods, and ELX restates its Monte Carlo target.
    - R1-41 and R1-54: COV owns the models and envelopes; MFG owns the capabilities (contract section 13.4).
    - R1-40: DFN cells are phase 5 (contract section 13.4), and pseudo-4D packs land in phase 6 with ELX's pack-scale DFN.
    - R1-33: superconductors are out of scope (OOS-3) rather than a matrix row.
    - R3-55: "Coverage by category" became the out-of-reach list's Categories column; scope lives in contract section 13.1.

## Contract change requests

- CCR-COV-9, model level and evidence level in the glossary: accepted in contract v5 (section 2).

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
