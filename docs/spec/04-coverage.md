# Physics coverage and materials (COV)

Crucible covers physics through versioned physics packages whose models declare fidelity, evidence and a `ValidityEnvelope` as data. Every result carries a validity-zone Field and an error budget instead of an implied guarantee. Materials are versioned records of property Fields over temperature, rate and direction, with typed provenance, statistical basis, uncertainty and data licence.

## Coverage model

"Anything physical" is made as true as it honestly can be by three rules. Every model says where it is valid. Every result says how wrong it may be and why. Every gap has a name, a reason and a recommended alternative.

### Concepts this tab uses

Six concepts appear in this tab. Each is a plain record or a use of a core type; none is a parallel abstraction.

| Concept | What it is | Relation to core types |
| --- | --- | --- |
| Physics package | A Package whose exports include `PhysicsModel`s and `ConstitutiveModel`s. Built-in physics ships as `std::phys::*`, `std::regime` and `std::mat::*` | A Package; no new mechanism |
| `PhysicsModel` | A record naming governing equations (an Ingot weak form or a Wasm component solver), required constitutive behaviour, outputs, fidelity level, evidence level, `ValidityEnvelope` and model-form error | Solving it emits `Op`s; its outputs are `Field`s |
| `ConstitutiveModel` | A material behaviour law: stress update, heat-flux law, B–H curve, dispersion model, Butler–Volmer kinetics | Referenced by id from `Material`; carries its own `ValidityEnvelope` |
| Regime variable | A named, dimension-typed quantity computed from inputs or solution: Reynolds number, Knudsen number, plastic strain, electrical size | A `Field<Body, Quantity<D>>` returned by an Ingot function |
| Validity zone | Calibrated, Extrapolated, Invalid or Unassessed, per point | A `Field<Body, ValidityZone>`; envelope bounds compile to `Check`s |
| `ErrorBudget` | Discretization, solver, input and model-form error of a result | A record attached to each result `Field` |

**Decision D-COV-1:** Physics coverage is delivered only as physics packages that use public mechanisms, and the coverage map is generated from package metadata rather than maintained by hand. *Why:* principle 1 forbids privileged physics, and a generated map cannot claim coverage that no package backs. *Rejected:* an in-app solver catalogue (privileged and unverifiable); a hand-written coverage list (drifts from reality).

### Fidelity levels

| Level | Form | Typical cost | Error statement | Examples |
| --- | --- | --- | --- | --- |
| L0 Analytic | Closed form, handbook or standard method | Microseconds | Method assumptions plus model-form error from evidence | Beam formulas, Nusselt correlations, gear rating methods, Paschen breakdown |
| L1 System | Lumped or 1D networks solved as DAEs; exportable as FMI 3.0.2 | Milliseconds to seconds | As L0, plus network discretization | Thermal RC networks, battery equivalent circuits, blade-element rotor theory, transmission lines |
| L2 Reduced order | Projection (modal, Craig–Bampton, Krylov, POD with hyper-reduction) or certified surrogates | Milliseconds online | A posteriori estimator or held-out residual statistics | Modal superposition, inherent-strain distortion, battery SPMe |
| L3 Full 3D | FEM, IGA, DG, FV, BEM or particle methods through Flux | Seconds to hours | Flux discretization estimator plus model-form error | Nonlinear contact, LES, full-wave EM |

Fidelity level chooses the model form. The Flux mode (interactive or sign-off) chooses discretization accuracy. The two are independent axes, and both are recorded in result provenance.

**Decision D-COV-2:** Each domain publishes a fidelity ladder, and adjacent rungs carry a consistency oracle inside the narrower envelope. *Why:* agreement between independent model forms is cheap, strong verification and catches errors that single-model benchmarks miss; example target: Euler–Bernoulli tip deflection within 1% of a 3D solid for slenderness L/h ≥ 20. *Rejected:* verifying each level only in isolation.

### Evidence levels

| Level | Meaning | Required oracle results | Allowed use |
| --- | --- | --- | --- |
| E0 Declared | Implemented, not yet verified | None | Experimental packages only; results labelled; never sign-off |
| E1 Verified | Code verification passed | Manufactured-solution convergence at declared order, conservation, AD against finite differences, determinism | Interactive mode |
| E2 Benchmarked | E1 plus community benchmarks | Published reference values within stated tolerance (NAFEMS, NASA TMR, TEAM) | Sign-off inside the calibrated zone |
| E3 Validated | E2 plus held-out physical experiments | Comparison with quantified experimental uncertainty; the validated region defines the calibrated zone | Release gates of golden products |
| E4 Context-qualified | E3 plus a credibility package for a named context of use | Evidence organised per ASME V&V 40 [S8], NASA-STD-7009 [S9] or the FDA credibility guidance [S10] | Regulated submissions; the authority decides |

**Decision D-COV-3:** `std` physics enters sign-off only at E2 or above; a model whose results a golden-product gate compares with physical tests must reach E3 by that gate; evidence levels rise only through CI-signed oracle results. *Why:* ASME V&V 40 ties required credibility to how heavily a decision relies on the model and to the consequence of a wrong decision [S8]. *Rejected:* a single "validated" flag (hides what was checked); agent-assigned levels (violates principle 6).

### Error budget

Every result Field carries an `ErrorBudget` with four components. Discretization and solver error come from Flux. Input error comes from propagating Material and load uncertainty, and model-form error comes from the `PhysicsModel`'s evidence for the zone each point lies in.

```rust
pub struct ErrorBudget<D> {
    pub discretization: Estimate<D>, // Flux a posteriori estimator
    pub solver: Estimate<D>,         // algebraic and nonlinear residual contribution
    pub input: Estimate<D>,          // propagated Material and load uncertainty
    pub model_form: Estimate<D>,     // validation evidence for this point's zone
}

pub enum Estimate<D> {
    Bound(Quantity<D>),
    Distribution(Dist<D>),
    NotQuantified { reason: String },
}
```

Input error propagates by first-order sensitivities from form-level AD by default. Sign-off mode switches to quasi-Monte Carlo when a directional second-derivative estimate exceeds 10% of the first-order term (target threshold). The scrambled Sobol' sequence takes its seed as an explicit input, so propagation stays deterministic.

**Decision D-COV-4:** An unquantified component is shown as "not quantified", never as zero, and a check whose margin lies inside the quantified budget reports `Indeterminate` instead of pass or fail. *Why:* ASME V&V 20 quantifies accuracy only at validation points and leaves interpolation and extrapolation to engineering judgement [S7], so that judgement must be visible. *Rejected:* reporting discretization error alone, which implies the model form is exact.

A check evaluates on the quantified part of its budget and carries an `unquantified` tag naming the missing components. Release policy in `repo` decides whether a tag is acceptable, for example when the design declares a code safety factor that covers model-form error and cites the code clause.

## Validity envelopes as data

### Data model

A `ValidityEnvelope` is a content-addressed record versioned with its model. It bounds regime variables, states the scale limits of the continuum and of the model's closures, lists assumptions that cannot be computed, and cites the evidence behind each zone.

```rust
pub struct ValidityEnvelope {
    pub model: ModelRef,                 // PhysicsModel or ConstitutiveModel, id@version
    pub bounds: Vec<RegimeBound>,
    pub length_scale: ScaleRange,        // e.g. continuum valid above 1 µm for this class
    pub assumptions: Vec<Assumption>,    // "perfect bond", "no lithium plating"
    pub evidence: Vec<EvidenceRef>,      // oracle results and datasets, by CAS hash
}

pub struct RegimeBound {
    pub variable: RegimeVariableId,      // e.g. std::regime::knudsen
    pub reduction: Reduction,            // Pointwise | Max | Min | Mean | Percentile(p)
    pub calibrated: QuantityInterval,    // backed by evidence
    pub extrapolated: QuantityInterval,  // superset; plausibility limit
    pub outside: Disposition,            // Flag (a human may waive) | Refuse
    pub inflation: Inflation,            // model-form error growth across the extrapolated band
    pub escalate_to: Vec<ModelRef>,      // models valid beyond this bound
    pub basis: Citation,                 // why the bound sits where it does
}

pub enum ValidityZone { Calibrated, Extrapolated, Invalid, Unassessed }
```

Assumptions that cannot be computed become acknowledgement checks: a design using the model carries a human-signed statement that the assumption holds. Material-specific bounds come from the `ConstitutiveModel` calibration (see "Calibration from test data"), so one physics model has a different calibrated zone for each Material.

### Joint bounds

Per-variable intervals describe a box, which overstates coverage when validation data are correlated, for example tests run only at high temperature and low rate. A bound set may therefore declare a joint region: the convex hull of validation points in log-normalized regime coordinates, inflated by a declared margin. A point inside the box but outside the hull lies in the Extrapolated zone, and the inspector reports the nearest validated condition.

```rust
pub enum CalibratedRegion {
    Box,                                            // per-variable intervals only
    Hull { variables: Vec<RegimeVariableId>, points: CasHash, margin: f64 },
}
```

### Standard regime variables

| Variable | Definition | Typical users |
| --- | --- | --- |
| Equivalent strain, rotation | From the displacement Field | Small-strain kinematics |
| Homologous temperature | T / T_melt, absolute temperatures | Creep onset, rate-independent plasticity |
| Strain rate, triaxiality, Lode parameter | From strain-rate and stress Fields | Johnson–Cook range, ductile fracture |
| Reynolds, Mach, y+ | Local or global, from flow Fields | Laminar models, incompressibility, wall treatment |
| Knudsen | Molecular mean free path over local length | Continuum, slip and DSMC models |
| Biot, Rayleigh, Prandtl | From geometry and properties | Lumped capacitance, convection correlations |
| Weber, capillary, Weissenberg | From interface and rheology Fields | Breakup resolution, viscoelastic flow |
| Electrical size kL, skin-depth ratio δ/L | From frequency, geometry and properties | Quasi-static EM, surface-impedance models |
| Optical size L/λ | From geometry and wavelength | Geometric versus wave optics |
| C-rate, state of charge, cell temperature | From cell states | Battery model selection |
| Acoustic amplitude p′/ρc² | From the pressure Field | Linear acoustics |
| Cycles N, stress ratio R, ΔK | From load histories | Fatigue regime selection |
| Scale ratio ℓ/L | Microstructure or cell length over feature size | Homogenized properties, lattices |

Each regime variable is an Ingot function returning a Field. New packages add variables the same way they add physics.

### Evaluation

1. **A priori screen.** Bounds computable from inputs (inlet Reynolds number, frequency against part size, service temperature against Material data coverage) are evaluated before solving. A Refuse bound outside its extrapolated range stops the solve with a typed error.
2. **Solve.** Flux evaluates the Ops as usual.
3. **A posteriori assessment.** Regime Fields are computed from the solution, reduced per bound and mapped to zones. The worst zone per point forms `Field<Body, ValidityZone>`.
4. **Composition.** A coupled analysis is valid where every constituent envelope and the coupling's own envelope hold. Envelopes compose by intersection.
5. **Checks.** Each bound compiles to a Check named `validity::<model>::<variable>`. Severity comes from the zone policy below; the oracle source is the envelope's evidence.
6. **Display.** The UI paints the zone Field on geometry. Inspection shows the value, the bound, the basis citation and the escalation options.

Values within the declared cross-platform tolerance of a bound resolve to the worse zone. Zone results are therefore identical across platform classes. Regime Fields are pointwise functions of solution Fields; the target cost of a posteriori assessment is under 2% of solve time.

[[DIAGRAM: Validity flow. Boxes: "Inputs and Material" → "A priori screen" → "Flux solve (Ops)" → "Regime variable Fields" → "Zone Field" → "Checks" → "UI paint" and "Release gate". Side arrows: "A priori screen" –Refuse→ "Typed error with escalation list"; "Checks" –Extrapolated or Flag→ "Waiver record in repo (human only)". An "ErrorBudget" box receives arrows from "Flux estimator", "Material uncertainty" and "Model-form evidence" and attaches to the result Fields.]]

### Policy by zone

| Zone | Interactive mode | Sign-off mode | Release gate |
| --- | --- | --- | --- |
| Calibrated | Shown | Checks evaluate normally | Allowed |
| Extrapolated | Shown with an amber overlay; model-form error inflated | Checks evaluate; outcome tagged "extrapolated" | Needs a human waiver recorded in the change order |
| Invalid, Flag | Shown hatched for diagnosis; dependent checks error | Dependent checks fail | Needs a human waiver with rationale; agents cannot waive |
| Invalid, Refuse | Shown for diagnosis only | Dependent checks fail | Blocked; no waiver |
| Unassessed | Shown with a missing-input notice | Dependent checks fail | Blocked until the input exists |

**Decision D-COV-5:** Validity bounds compile to ordinary Checks, and validity zones are a Field. *Why:* Checks already carry severity, CI, reports and review, and Fields already paint on geometry (composition over special cases). *Rejected:* a separate warnings channel (a parallel abstraction); clamping results to the envelope (silent).

**Decision D-COV-6:** Crucible suggests escalation to a valid model but never switches models automatically. *Why:* a switch changes cost, provenance and sometimes the answer, so it must be explicit. *Rejected:* automatic fidelity escalation.

### Failure behaviour

Validity failures are typed and carry fixes.

```rust
pub enum ValidityError {
    OutsideEnvelope {
        model: ModelRef, variable: RegimeVariableId, value: QuantityValue,
        bound: QuantityInterval, zone: ValidityZone, region: Query,
        escalate_to: Vec<ModelRef>,
    },
    Unassessed { model: ModelRef, variable: RegimeVariableId, missing: MissingInput },
    NoCoveringModel { domain: DomainTag, regime: Vec<RegimeSample>, see: OutOfReachId },
}
```

```
error[validity]: std::phys::fluid::navier_stokes@3 is invalid in region `squeeze_gap`
  Knudsen number reaches 0.31; calibrated below 0.001, extrapolated to 0.01, refused above 0.01
  basis: no-slip wall closure fails in the slip and transitional regimes, see std::regime::knudsen
  try: std::phys::rarefied::dsmc (external tool; valid for Kn 0.1 to 10)
```

Widening any envelope, in any package, needs human approval, as loosening a tolerance does (contract section 7). Agents may propose envelope changes with evidence; they cannot merge them.

### Surrogates and learned models

**Decision D-COV-7:** A learned surrogate is an L2 model whose calibrated zone is its training distribution, whose model-form error comes from held-out data, and whose out-of-distribution queries fall in the Extrapolated or Invalid zone. No surrogate reaches E3 without held-out physical validation. *Why:* learned models fail silently outside their data, so their envelope must be explicit. *Rejected:* treating a surrogate as interchangeable with the model it approximates.

### Coupled physics

Flux owns coupling algorithms. This tab declares, for each common pair, the default coupling and the envelope under which a weaker coupling is valid. A coupling is itself a model with an envelope, so a one-way analysis outside its envelope is flagged like any other model.

| Pair | Default coupling | Weaker coupling allowed when | Benchmark |
| --- | --- | --- | --- |
| Thermal → structure | One-way, sequential | Deformation does not change thermal boundary conditions or contact conductance | NAFEMS P18 thermal stress and LE11 (−105 MPa at A) [S2][S3] |
| Fluid ↔ structure | Partitioned with quasi-Newton (IQN-ILS) acceleration; monolithic when added-mass effects are strong | One-way if wall displacement stays below 1% of the local flow length scale | Turek–Hron FSI benchmark [unverified] |
| Electromagnetic → thermal | Period-averaged losses, one-way | Conductivity and permeability insensitive to temperature over the solved range | TEAM 36, induction heating [S6] |
| Electrochemical ↔ thermal | Two-way, monolithic | One-way only below a declared C-rate where self-heating stays under a declared temperature rise | PyBaMM thermal model comparison [unverified] |
| Structure ↔ acoustics | One-way for light fluids | Fluid loading negligible (air); two-way for water | Baffled-piston and pulsating-sphere analytic solutions |
| Electrostatic ↔ structure | Monolithic (needed for pull-in) | Never one-way near pull-in | Parallel-plate pull-in analytic voltage |
| Process → structure | One-way via state Fields (residual stress, porosity, fibre orientation) | Always one-way within Crucible; VMAP, an open CAE data-interface standard [S58], is the candidate exchange format with external process tools [unverified fit] | AM-Bench residual strain and part deflection [S11] |
| Aerodynamics ↔ structure | Partitioned, modal structure | Static aeroelastic effects small (twist below a declared bound) | AGARD 445.6 wing [unverified] |

## Coverage matrix

The matrix is generated from package metadata (D-COV-1); this tab specifies its initial content. Scale tiers: **N** nano (below 100 nm), **µ** micro (100 nm to 1 mm), **Me** meso (1 mm to 100 mm), **P** product (100 mm to 10 m), **L** large structure (above 10 m). Delivery: **Nat** native (Ingot weak form compiled by Flux); **Wasm** specialist `std` Wasm component whose hot loops call general Flux operations (D-COV-11); **Ext** external tool through a recorded external Op (D-COV-12); **Interop** exchange only. Phase numbers refer to section 7 of the contract and to the phases proposed under "Phasing".

Method attributions tagged [Sn] were verified in this round. Untagged method names are standard literature methods, and envelope numbers are design defaults; both are [unverified] until the owning package reaches E2 with cited evidence.

### Solid mechanics

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Linear elasticity | µ Me P L | Beam, plate and shell formulas · frame networks · static condensation | Matrix-free high-order FEM with p-multigrid; IGA on trimmed B-rep; immersed finite-cell for Implicit and lattice Bodies | Strain ≤ 0.5% calibrated, ≤ 2% extrapolated; stress below the Material's proportional limit; rotation ≤ 0.05 rad; feature size ≥ 10 grains or 5 lattice cells | NAFEMS LE1 92.7 MPa, LE10 −5.38 MPa, LE11 −105 MPa [S3][S4]; MMS | Nat | 1 |
| Geometric nonlinearity | µ Me P L | — · — · — | Total Lagrangian FEM with arc-length continuation; solid-shell and IGA Kirchhoff–Love shells | Strain within the constitutive envelope; limit points reported, never stepped over silently | NAFEMS large deflection and snap-through (R0024 group) [S5] | Nat | 2 |
| Plasticity | µ Me P L | Neuber and Glinka notch rules · — · — | Finite-strain multiplicative plasticity: J2, Hill48, Barlat Yld2000-2d; Chaboche kinematic hardening; AD consistent tangents | Rate-independent below homologous T 0.3; strain ≤ calibrated range, beyond uniform elongation only with a damage model | NAFEMS elasto-plastic stiffened panel (R0024 group) [S5]; thick-cylinder analytic | Nat | 2 |
| Hyperelasticity | µ Me P | — · — · — | Mixed u–p and F-bar formulations; Neo-Hookean, Mooney–Rivlin, Yeoh, Ogden, Arruda–Boyce, Gent | Stretch within calibrated range for each deformation mode tested; Drucker stability checked over the envelope | Cook's membrane; patch tests; uniaxial and biaxial analytic | Nat | 2 |
| Viscoelasticity | µ Me P | — · Prony networks · complex-modulus modal | Generalized Maxwell with WLF or Arrhenius shift; finite-strain parallel networks (Bergström–Boyce) | Temperature and frequency within the master-curve span | Analytic creep and relaxation; master-curve reconstruction | Nat | 3 |
| Creep | Me P L | Larson–Miller rupture · — · — | Norton–Bailey, Garofalo, theta projection; Kachanov–Rabotnov damage for tertiary creep | Stress and temperature within test matrix; time ≤ longest test calibrated, ≤ 3× extrapolated | NAFEMS primary and secondary creep (R0027) [S5] | Nat | 3 |
| Contact and friction | µ Me P L | Hertz, Boussinesq · — · — | Mortar contact with semismooth Newton and Coulomb stick-slip; Incremental Potential Contact with smooth friction and continuous collision detection for large deformation [S26] | Penetration below declared tolerance; friction coefficient only from a tested pair | NAFEMS contact punch and pin (R0094) [S5]; Hertz analytic | Nat | 2 |
| Bolted and bonded joints | Me P L | VDI 2230 [unverified] · joint springs · — | Preloaded bolt elements; cohesive zones (bilinear, Benzeggagh–Kenane mixed mode) | Joint parameters from tests of the same joint class | DCB and ENF analytic energy release rates | Nat | 2 |

### Dynamics and stability

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Modal analysis | µ Me P L | Rayleigh, Dunkerley · lumped MDOF · Craig–Bampton | Shift-invert Krylov–Schur and LOBPCG on high-order FEM | Linear, small amplitude; damping from test or declared | NAFEMS free-vibration (FV) series [S2][S5] | Nat | 1 |
| Harmonic and random vibration | Me P L | SDOF and Miles · — · modal superposition with residual vectors | Direct frequency response with structural damping; PSD response | Linear; damping model declared; PSD band within modal coverage | NAFEMS forced vibration harmonic and random (R0016) [S5] | Nat | 2 |
| Shock | Me P L | Shock response spectrum · — · modal transient | Implicit generalized-α transient | Linear unless nonlinear material declared; pulse within modal band | Half-sine SDOF analytic | Nat | 2 |
| Rotordynamics | Me P | Jeffcott rotor · rotor beam models · Campbell modal | Rotating-frame FEM with gyroscopic terms; fluid-film bearing coefficients from the Reynolds equation | Bearing coefficients linearised at operating speed; speed within map | Jeffcott analytic critical speed | Nat | 2 |
| Buckling | µ Me P L | Euler, Johnson · — · linear eigen-buckling | Arc-length post-buckling with imperfection seeding (eigen-affine or measured); Koiter asymptotics for shells | Linear eigen-buckling on imperfection-sensitive shells: Refuse for sign-off | NAFEMS buckling (R0024 group) [S5]; Euler column | Nat | 1 linear, 2 nonlinear |
| Explicit dynamics, impact, crash | Me P L | Energy methods · lumped crash networks · — | Explicit central difference with selective mass scaling; penalty or IPC contact; damage-driven erosion | Added mass ≤ 2% calibrated, Refuse above 5%; hourglass energy ≤ 10% of internal; rate within material calibration | Taylor bar impact; drop-test correlation on golden product 5 | Nat (OpenRadioss, AGPL, as Ext reference only [S25]) | 3 drop, 5 crash |

### Durability: fatigue, fracture, wear

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Stress-life | Me P L | Basquin with Goodman, Gerber or Walker · rainflow on histories · — | Critical-plane stress criteria (Findley, Dang Van) with surface, size and notch factors; probabilistic S–N | N ≥ 10⁴ cycles; R ratio and temperature within tests; defects below Kitagawa–Takahashi threshold | Constant-amplitude analytic; held-out coupon data | Nat | 1 uniaxial, 2 multiaxial |
| Strain-life | Me P L | Coffin–Manson, Morrow, SWT with Neuber · — · — | Strain-based critical plane (Fatemi–Socie, Brown–Miller) on elastic-plastic FE | Cyclic curve from the same material condition | Notched-specimen analytic | Nat | 2 |
| Weld fatigue | Me P L | Nominal, hot-spot and effective-notch methods (IIW, EN 1993-1-9) [unverified] · — · — | Structural-stress methods on shell and solid models | Weld class and quality level declared | Code worked examples [unverified] | Nat | 2 |
| Crack growth | Me P L | Paris and NASGRO equations with handbook K solutions · — · — | Interaction-integral K and J on remeshed or XFEM cracks; spectrum retardation models | Small-scale yielding (plastic zone ≪ crack length); ΔK above threshold | NAFEMS linear elastic fracture (R0020) [S5] | Nat | 3 |
| Fracture | µ Me P L | LEFM K_Ic and failure assessment diagrams · — · — | Phase-field fracture (AT1, AT2); cohesive zones; ductile damage (Gurson–Tvergaard–Needleman, Hosford–Coulomb) | Ductile fracture defaults to Flag: a blind round robin found "a striking lack of consistency across research groups" [S12] | Sandia Fracture Challenge data [S12] | Nat | 3 LEFM, 5 ductile |
| Wear | µ Me P | Archard · — · — | Archard on local contact pressure and slip with geometry update | Wear coefficient only from the tested tribo-pair, load, speed and lubricant | Pin-on-disc analytic | Nat | 3 |

### Composites and architected materials

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Laminates | Me P L | Classical laminate theory, first-order shear · — · — | Layered solid-shell and IGA shells with draped fibre-angle Fields | Ply count and thickness within shell assumptions; through-thickness stresses need solid or layerwise models | NAFEMS composites: laminated strip, thick cylinder, sandwich shell (R0031) [S5] | Nat | 3 |
| Progressive failure | Me P L | First-ply failure: Tsai–Wu, Hashin, Puck, LaRC05 · — · — | Continuum damage with cohesive interlaminar zones, calibrated in a building-block test pyramid | Default Flag: a review of the second World-Wide Failure Exercise found that none of 12 theories matched all test data [S13] | WWFE-II data sets [S13] | Nat | 4 |
| Short-fibre moulded composites | Me P | Rule of mixtures · — · — | Mori–Tanaka with orientation averaging over the fibre-orientation tensor Field from fill simulation | Aspect ratio and volume fraction within calibration | Unidirectional limit against laminate theory | Nat | 3 |
| Lattices and architected materials | µ Me P | Gibson–Ashby scaling · — · asymptotic homogenization | Full-resolution immersed FEM; de-homogenization | Scale ratio cell/feature ≤ 0.1 calibrated, else full resolution | Homogenized versus full-resolution consistency (D-COV-2) | Nat | 1 |

### Heat transfer

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Conduction | N µ Me P L | Slab, fin and shape-factor solutions · thermal RC networks · Krylov moment matching | High-order FEM and IGA; immersed methods for Implicit Bodies | Fourier law Refuse where feature length is below 10 phonon mean free paths (a Material property); properties within data range | NAFEMS T2 to T4 [S2][S5]; MMS | Nat | 1 |
| Convection | Me P L | Nusselt correlations within their published Re and Pr ranges · flow networks · — | Conjugate heat transfer on RANS or LES flow (see Fluids) | Correlation ranges are Refuse bounds; conjugate analysis inherits the flow envelope | NAFEMS T4 convection [S5]; Graetz analytic | Nat | 2 correlations, 3 conjugate laminar, 4 turbulent |
| Radiation | Me P L | Two-surface enclosures · radiosity networks with view factors · — | GPU ray-traced view factors with reciprocity and closure enforced; Monte Carlo ray tracing for specular and spectral surfaces; discrete ordinates for participating media | Gray-diffuse assumption declared; spectral bands required where emissivity varies beyond a declared limit | NAFEMS T2 1D radiation [S5]; analytic view factors; closure ΣF = 1 within 10⁻⁶ (target) | Nat | 3 |
| Phase change | µ Me P | Stefan and Neumann solutions · — · — | Enthalpy method with mushy zone; latent heat from the Material record | Declared freezing range; undercooling not modelled | Stefan analytic | Nat | 3 |
| Ablation and pyrolysis | Me P | Heat of ablation · 1D charring ablator · — | Surface energy balance with B′ tables, pyrolysis and recession with geometry update | Flag always: high-enthalpy surface chemistry needs test data | Ablation workshop cases [unverified] | Wasm | 6 |
| Thermoelectric and Joule heating | µ Me P | Peltier module equations · — · — | Coupled Seebeck–Peltier–Thomson FEM | Linear thermoelectric coefficients | Analytic module | Nat | 5 |

### Fluids

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Incompressible laminar | µ Me P | Hagen–Poiseuille, Moody · pipe and duct networks · POD-Galerkin | Stabilized high-order FEM or DG; immersed boundaries for Implicit Bodies | Re below transition for the geometry class (pipe: 2,000 calibrated, 2,300 extrapolated) | Lid-driven cavity, Schäfer–Turek cylinder [unverified] | Nat | 3 |
| RANS | Me P L | Loss and drag data · 1D networks with loss coefficients · — | Spalart–Allmaras, SST k–ω, GEKO; γ–Reθ transition; quadratic constitutive relation for corner flows | Attached and mildly separated flow calibrated; massive and smooth-body separation Flag | NASA TMR verification cases 2DZP, 2DB and 2DMEA (up to 8 codes) and validation cases 2DWMH and ATB [S1] | Nat | 4 |
| Scale-resolving: DDES, WMLES, LES | Me P L | — | Entropy-stable DG with flux differencing [S28] and flux reconstruction [S27] on GPU; equilibrium and non-equilibrium wall models [S15] | Grid and cost estimated a priori from Yang–Griffin scalings [S14]; equilibrium wall models Flag under adverse pressure gradient [S15] | 2DWMH hump [S1]; channel DNS statistics | Nat | 5 |
| DNS | µ Me | — | Spectral and high-order DG | Refuse when the a priori cost exceeds the declared budget (see "Out of reach") | Taylor–Green vortex [unverified] | Nat | 5 |
| Lattice Boltzmann | Me P L | — | Cumulant or regularized collision with wall models, multi-GPU; XLB (Apache-2.0) as reference [S38] | Ma ≤ 0.3 on standard lattices; wall-model envelope as WMLES | As LES | Wasm | 5 |
| Compressible flow | Me P L | Isentropic and normal-shock relations · quasi-1D nozzle · — | DG and flux reconstruction with entropy-stable shock capturing; SU2 (LGPL-2.1) as reference [S37] | Calorically perfect gas below a declared temperature; real-gas and nonequilibrium flow Ext | ATB transonic bump, ONERA M6 wing [S1] | Nat | 5 |
| Multiphase, interface-resolved | µ Me P | — | Geometric VOF, conservative level set, Cahn–Hilliard phase field | Interfacial statistics converged at k_max·η_KH ≥ 60 with second-order schemes [S16]; coarser grids Flag | Rising-bubble benchmark [unverified] | Nat | 5 |
| Multiphase, dispersed | Me P L | Settling and drag correlations · — · — | Euler–Lagrange tracking with two-way coupling; Euler–Euler for dense flow | Volume-fraction limit per model; breakup models Flag | Particle-laden pipe data [unverified] | Nat | 5 |
| Free surface | Me P L | Linear wave theory · — · — | VOF; weakly compressible SPH for violent flow | Breaking waves need VOF or SPH | Dam break [unverified] | Nat | 5 |
| Cavitation | Me P | Cavitation number · — · — | Homogeneous mixture with Schnerr–Sauer or Zwart mass transfer | Flag always: empirical rate constants; erosion out of reach | Cavitating hydrofoil data [unverified] | Nat | 6 |
| Non-Newtonian | µ Me P | Power-law pipe flow · — · — | Generalized Newtonian (Carreau–Yasuda, Cross–WLF, Herschel–Bulkley); Oldroyd-B, Giesekus and PTT with log-conformation | Shear rate within rheometry range; Weissenberg number within verified range | Poiseuille analytic; 4:1 contraction [unverified] | Nat | 3 generalized Newtonian, 5 viscoelastic |
| Porous media | µ Me P L | Darcy, Ergun · — · — | Darcy–Brinkman–Forchheimer; permeability tensors homogenized from pore-scale LBM | Pore Reynolds number within the law's range | Porous-layer channel analytic | Nat | 3 |
| Rarefied gas | µ Me P | Free-molecular formulas · — · — | Velocity-slip and temperature-jump conditions on Navier–Stokes; DSMC with SPARTA (GPL, LGPL on request) [S34] | Kn < 0.001 continuum, 0.001 to 0.1 slip, 0.1 to 10 transitional, above 10 free molecular [unverified] | Microchannel slip analytic | Nat slip, Ext DSMC | 5 |
| Microfluidics | µ Me | Stokes resistances · hydraulic circuit networks · — | Stokes FEM with electro-osmotic slip and Nernst–Planck transport | Debye length much smaller than channel size for the slip model | Electro-osmotic plug flow analytic | Nat | 5 |
| Combustion and reacting flow | Me P L | Adiabatic flame temperature, equilibrium · 0D and 1D flames and reactor networks with Cantera (BSD-3) [S21][S22] · flamelet tables | Flamelet-progress-variable and FGM; finite-rate chemistry with dynamic reduction in LES | Flag always: mechanism ranges of pressure, temperature and equivalence ratio; soot and pollutants need data | Laminar flame speeds; TNF flames [unverified] | Wasm kinetics, Nat transport | 6 |

Real-fluid properties come from CoolProp (MIT) [S43]. REFPROP, a NIST Standard Reference Database [S52], is reached through a customer-licence connector [licence terms unverified].

### Acoustics and aeroacoustics

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Linear acoustics | Me P L | Sabine and Eyring room acoustics · transfer matrices for ducts and mufflers · modal | High-order FEM with PML; fast BEM (FMM or H-matrices) for exterior radiation; geometrical acoustics for rooms | Linear amplitude p′/ρc² ≤ 10⁻²; points per wavelength above the order-dependent minimum | Pulsating sphere, baffled piston analytic | Nat | 3 |
| Vibro-acoustics | Me P L | — · statistical energy analysis above the modal-overlap threshold · modal | Coupled structural–acoustic FEM and FEM–BEM | SEA needs at least 3 modes per band; heavy fluids need two-way coupling | Plate radiation analytic | Nat | 3 FEM, 5 SEA |
| Porous absorbers | Me P | Delany–Bazley · transfer matrix · — | Johnson–Champoux–Allard equivalent fluid; Biot poroelastic | Flow resistivity within measured range | Impedance-tube data | Nat | 5 |
| Aeroacoustics | Me P L | Gutin tonal propeller noise · — · — | Ffowcs Williams–Hawkings integration from blade loading (tonal) or DDES and LES surfaces (broadband) | Compact-source and permeable-surface conditions; broadband Flag without scale-resolving input | Drone rotor acoustic measurements (golden product 6); BANC cases [unverified] | Nat | 4 tonal, 5 broadband |

### Electromagnetics

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Electrostatics | N µ Me P L | Plate, sphere and coaxial formulas · capacitance networks · — | High-order H1 FEM; fast BEM for open domains; capacitance-matrix extraction as in Palace (Apache-2.0) [S18] | Quasi-static: electrical size kL ≤ 0.1 calibrated, ≤ 0.3 extrapolated | Analytic sphere and coaxial line; code-to-code capacitance matrices against Palace [S18] | Nat | 3 |
| Magnetostatics | µ Me P L | Magnetic circuits · reluctance networks · — | Nédélec H(curl) FEM on the vector potential with Newton on measured B–H curves; reduced scalar potential with cuts | B within the measured B–H range; hysteresis needs a hysteresis Material model | TEAM 13, 3D nonlinear magnetostatics [S6] | Nat | 3 |
| Eddy currents and induction | µ Me P L | Skin-depth formulas · — · — | A–φ and T–Ω formulations in frequency and time domain; surface-impedance boundaries | Surface impedance only where δ/L ≤ 0.1; nonlinear materials need time domain or harmonic balance | TEAM 7, asymmetrical conductor with a hole [S6]; TEAM 36, induction heating [S6] | Nat | 4 |
| Electric machines | Me P | dq equivalent circuits · lumped loss and thermal networks · flux-linkage maps | 2D and 3D motion with moving band or mortar sliding interface; Bertotti iron loss; magnet eddy loss; demagnetization check | Loss coefficients per lamination grade and frequency band; demagnetization knee from the Material | Golden product 6 motor test data | Nat | 4 |
| RF and antennas | Me P L | Antenna and line formulas · S-parameter networks · Krylov model-order reduction for sweeps | High-order Nédélec FEM with PML; lumped and numeric wave ports as in Palace [S18]; MoM with multilevel fast multipole for radiation and RCS; DG time domain for broadband | Dispersion fit inside the measured band; resolution per order and wavelength from the Flux estimator | Dipole and waveguide cut-off analytic; Mie sphere scattering | Nat | 4 drone antenna, 5 general |
| Signal and power integrity | µ Me | RLGC lines · — · rational (vector) fitting | Quasi-static and full-wave interconnect extraction | Causality and passivity enforced on fitted models | Analytic microstrip | Nat; ELX owns use | 3 |
| EMC | Me P | Shielding-effectiveness formulas · multiconductor cable models · — | Full-wave FEM or DG time domain with field-to-cable coupling | Flag always for compliance prediction: source spectra and parasitics are rarely known | Shielded enclosure aperture cases [unverified] | Nat | 5 |

### Optics and photonics

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Imaging optics | µ Me P | Paraxial ABCD matrices · sequential ray tracing with Seidel and Zernike analysis · — | Differentiable sequential and non-sequential ray tracing with polarization; diffraction PSF and MTF by Fourier optics | Geometric optics where L/λ ≥ 100; diffraction-limited checks need the wave model | Analytic singlet and doublet designs | Nat | 5 |
| Illumination and stray light | Me P L | Photometric formulas · — · — | Spectral Monte Carlo path tracing with measured BSDFs; differentiable spectral and polarized rendering as in Mitsuba 3 [S39] | BSDF within measured angles and wavelengths | Integrating-sphere and light-guide measurements | Nat | 3 light pipes, 5 general |
| Wave optics and photonics | N µ | Thin-film transfer matrix · — · eigenmode expansion | FDTD and DG time domain; RCWA for periodic structures; FEM mode solvers; Meep (GPL) only as an external reference | Linear optics unless a nonlinear Material model is declared; dispersion fit within band | Mie scattering; slab waveguide modes analytic | Nat | 6 |

### Electrochemistry and chemical kinetics

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Battery cells | µ Me P | Capacity and energy formulas · equivalent-circuit models with OCV and entropic heat · SPM and SPMe | Doyle–Fuller–Newman (P2D) with thermal coupling and multi-scale pouch or cylinder models; PyBaMM (BSD-3) as reference [S19][S20] | Each rung declares C-rate, temperature and SOC bounds; lithium plating Flag | Ladder consistency SPM, SPMe and DFN at low C-rate (D-COV-2); held-out drive-cycle data | Nat | 4 |
| Battery packs | Me P | Series-parallel scaling · cell network with busbar resistance and thermal network · — | Cell models embedded in 3D pack thermal and coolant flow | Cell-to-cell variation needs measured spread | Golden product 6 pack test | Nat | 4 |
| Battery degradation | µ Me P | Empirical calendar and cycle fade · — · — | SEI growth, lithium plating, particle cracking and loss of active material | Flag always; time beyond tested duration is Invalid for sign-off | Held-out ageing data | Nat | 5 |
| Thermal runaway | Me P | ARC onset temperature · lumped multi-step Arrhenius decomposition · — | 3D thermal abuse with decomposition kinetics and cell-to-cell propagation | Flag always: kinetics are cell-specific; venting, jetting and fire are out of reach natively | ARC data for the cell; propagation test | Nat | 5 |
| Fuel cells and electrolysers | µ Me P | Polarization curves · 1D membrane-electrode models · — | 3D two-phase PEM models with Butler–Volmer kinetics and membrane water transport | Flag: water management closures are empirical | Published polarization curves [unverified] | Nat | 6 |
| Corrosion | µ Me P L | Galvanic series, area-ratio rules · — · — | Secondary current distribution with measured polarization curves; cathodic protection; Nernst–Planck for crevices | Rates only with polarization data in the same electrolyte and temperature; long horizons Flag | Cathodic-protection analytic cases | Nat | 5 |
| Electroplating | µ Me P | Faraday's law · — · — | Tertiary current distribution with thickness growth | Additive chemistry is empirical | Hull-cell data [unverified] | Nat | 5 |
| Gas-phase kinetics | — | Equilibrium · 0D and 1D reactors, flames and reactor networks with Cantera (BSD-3) [S21][S22] · mechanism reduction | Finite-rate chemistry inside CFD (see Fluids) | Mechanism validity ranges in pressure, temperature and composition | Ignition-delay and flame-speed data | Wasm | 6 |
| Cure and polymer reaction kinetics | Me P | — · Kamal–Sourour cure kinetics · — | Cure–thermal–residual-stress coupling | DSC calibration range | DSC data | Nat | 3 |

### Particles, molecules and multiscale

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Granular media | µ Me P | Angle of repose, Janssen silo stress · — · — | DEM with Hertz–Mindlin contact and rolling resistance on GPU; non-smooth DEM for dense packing; Project Chrono (BSD-3) as reference [S32] | Particle shape and count limits; parameters calibrated by angle-of-repose and shear-cell tests | Hopper discharge (Beverloo law) | Wasm | 5 |
| Large-deformation particle methods | Me P L | — | Material point method (MLS-MPM) for flow-like solids and soils; SPH for violent fluid and hypervelocity impact; peridynamics for fragmentation | Flag: numerical fracture and tensile instability; mesh-based models preferred where valid | Column collapse; Taylor bar | Wasm | 6 |
| Molecular dynamics | N | — · — · coarse-grained MD | Classical MD with machine-learned interatomic potentials (MACE, MIT code [S31]); LAMMPS (GPL-2.0) as external engine [S35] | Time scale ns to µs; potential valid only within its training chemistry; the foundation-model licence is checked per model [S31] | Lattice constants, elastic constants against reference data | Ext | 6 |
| Multiscale coupling | N µ Me | Rules of mixtures · — · surrogate-homogenized laws | FE² computational homogenization; FFT-based RVE solvers; concurrent atomistic-to-continuum handshaking | Scale separation ℓ/L ≤ 0.1; RVE convergence checked | Hashin–Shtrikman bounds; periodic laminate analytic | Nat FE² and FFT, Ext concurrent | 5 |

### Plasma and radiation transport

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Gas discharge and breakdown | µ Me | Paschen law · global plasma models · — | Fluid drift-diffusion with local-field approximation | Paschen law within its pd range; arcs Flag | Paschen curves | Nat | 6 |
| Kinetic plasma | µ Me P | — | Electromagnetic and electrostatic particle-in-cell; WarpX (BSD-3-Clause-LBNL) as external engine [S33] | Debye length and plasma frequency resolved; collisions declared | Two-stream instability analytic growth rate | Ext | 7 |
| Magnetohydrodynamics | Me P L | Hartmann flow · — · — | Entropy-stable DG MHD as in Trixi.jl [S28] | Ideal or resistive declared; low magnetic Reynolds number approximations stated | Hartmann analytic; Orszag–Tang vortex | Nat | 7 |
| Neutron and photon transport | µ Me P L | Attenuation laws · — · — | Continuous-energy Monte Carlo on constructive solid geometry, CAD through DAGMC [unverified]; OpenMC (MIT) as reference and engine [S23] | Nuclear data library and version recorded; criticality safety Refuse without benchmark validation | Criticality benchmarks (ICSBEP) [unverified] | Ext | 7 |
| Radiation shielding and dose | Me P L | Point-kernel with buildup factors · — · — | Monte Carlo transport; Geant4 (permissive licence [S24]) for charged particles and space radiation | Physics list and energy range declared | Analytic slab attenuation | Ext | 7 |

### Biomechanics and human factors

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Soft tissue | µ Me P | — · — · — | Anisotropic fibre-reinforced hyperelasticity (Holzapfel–Gasser–Ogden), biphasic poroelasticity; FEBio (MIT) as reference [S40] | Flag always: inter-subject variability dominates; no E4 without a V&V 40 package [S8] | Biphasic confined-compression analytic solution | Nat | 7 |
| Implants and orthopaedic devices | Me P | Beam and plate formulas · — · — | Nonlinear FEM with bone–implant contact, fatigue per ASTM F2996 [unverified] | Bone properties from imaging with declared density–modulus relation | Device fatigue test data | Nat | 7 |
| Cardiovascular flow | Me P | Poiseuille and Womersley · 0D Windkessel networks · — | Arbitrary Lagrangian–Eulerian FSI with non-Newtonian blood | Flag: patient-specific boundary conditions drive results | FDA nozzle benchmark [unverified] | Nat | 7 |
| Musculoskeletal and posture | P | Anthropometric tables · — · — | Musculoskeletal multibody with optimal control; OpenSim (Apache-2.0) as reference [S41] | Population and task within data | Gait data [unverified] | Wasm | 5 |
| Human factors and ergonomics | P | Reach envelopes, NIOSH lifting equation [unverified] · — · — | Digital human models posed from population percentiles (ANSUR II, 6,068 subjects, 93 measures [S47]) | Population declared; percentile mixing across measures uses multivariate methods, not single-measure percentiles | Fit and reach checks against ANSUR II data | Nat | 3 reach and fit, 5 posture |
| Cloth and soft goods | Me P | — · — · — | Shell FEM or discrete elastic models with IPC contact and friction [S26]; measured fabric bending and shear | Fabric properties from Kawabata or equivalent tests [unverified] | Cusick drape and fabric bending tests [unverified] | Nat | 5 |

### Manufacturing process physics

Process models feed state Fields (residual stress, porosity, fibre orientation, microstructure) into downstream structural models. The Manufacturing tab (MFG) owns process planning; this tab owns the physics and its validity.

| Process | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Additive: powder bed fusion | µ Me P | Rosenthal moving heat source · — · inherent strain from calibrated coupons | Part scale: layer-agglomerated thermo-mechanical FEM; melt pool: high-fidelity thermal-fluid with Marangoni flow and keyhole physics | Inherent strain valid only for the calibrated machine, material and parameter set; melt pool Flag outside AM-Bench conditions | AM-Bench 2018, 2022 and 2025 residual strain, deflection and melt-pool data [S11] | Nat | 1 inherent strain, 4 thermo-mechanical, 6 melt pool |
| Additive: extrusion and resin | Me P | Bead-geometry formulas · — · — | Thermal history with bond-strength models; vat cure-depth models | Interlayer strength from tests | AM-Bench extrusion and vat cure-depth sets [S11] | Nat | 2 |
| Casting solidification | Me P L | Chvorinov rule · — · — | Mould filling with VOF; solidification with Niyama porosity criterion; hot tearing indicators | Porosity and microstructure Flag outside calibration | Modeling of Casting, Welding and Solidification benchmarks [unverified] | Nat | 6 |
| Injection moulding | Me P | Flow-length ratios · — · — | 3D fill, pack and cool with Cross–WLF viscosity and Tait PVT; Folgar–Tucker fibre orientation with IBOF closure; warpage | Material record must contain rheology and PVT; shear-rate range from rheometry | Golden product 5 measured warpage | Nat | 3 |
| Welding distortion | Me P L | Shrinkage-force rules · — · inherent strain | Goldak double-ellipsoid heat source with metallurgical phase transformation and thermo-elasto-plasticity | Heat source calibrated by macrograph; phase models per alloy | Golden product 4 measured distortion | Nat | 2 inherent strain, 4 transient |
| Machining forces and chatter | Me P | Mechanistic cutting-force coefficients · — · — | Stability lobes in frequency domain from measured or simulated tool-tip FRFs; semi-discretization for milling | Cutting coefficients per tool, material and speed | Analytic stability lobes | Nat | 2 |
| Stamping and springback | Me P L | Bend allowance · — · one-step inverse forming | Incremental shell forming with Yld2000-2d and Yoshida–Uemori kinematic hardening; forming-limit diagrams | Springback Flag without cyclic (tension–compression) calibration | NUMISHEET benchmarks [unverified] | Nat | 2 bend, 5 forming |
| Heat treatment | Me P | Jominy hardenability · — · — | Johnson–Mehl–Avrami–Kolmogorov and Koistinen–Marburger phase kinetics with transformation plasticity | TTT and CCT data for the alloy required | Jominy data | Nat | 6 |
| Composites cure and draping | Me P L | Kinematic draping · — · — | Cure kinetics with process-induced residual stress; constitutive draping with shear locking | Cure-kinetics DSC range | Fibre-angle measurement | Nat | 5 |

### MEMS and piezoelectrics

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Electrostatic actuation | µ Me | Parallel-plate pull-in · lumped spring–capacitor · reduced-order macromodels | Monolithic electromechanical FEM with fringing fields | Continuum and bulk properties need features ≥ 1 µm for metals and polysilicon (size effects declared per Material) | Parallel-plate pull-in analytic | Nat | 5 |
| Squeeze-film and gas damping | µ | Reynolds-equation damping coefficients · — · — | Reynolds equation with rarefaction-corrected effective viscosity; DSMC for transitional gaps | Knudsen bounds as for rarefied gas | Analytic squeeze-film coefficients | Nat | 5 |
| Piezoelectric devices | µ Me P | Mason and BVD equivalent circuits · — · modal | Coupled piezoelectric FEM with dielectric and mechanical losses | Linear constitutive model below the coercive field; depolarization temperature declared | Analytic thickness-mode resonator | Nat | 5 |
| Thermal MEMS and anchor losses | µ | Zener thermoelastic damping · — · — | Coupled thermoelastic eigenanalysis; PML anchor loss | Q prediction Flag without fabrication data | Zener analytic | Nat | 6 |

### Geomechanics and civil structures

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Reinforced concrete | Me P L | Code section design (Eurocode 2, ACI 318) [unverified] · frame analysis · — | Concrete damage plasticity with embedded reinforcement; smeared crack models | Code-method use requires the code edition recorded; nonlinear concrete Flag without calibration | Code worked examples [unverified] | Nat | 7 |
| Steel and timber structures | P L | Code member checks (Eurocode 3 and 5, AISC 360) [unverified] · frame analysis · — | Shell and beam FEM with geometric nonlinearity | As linear and nonlinear solids | Code worked examples [unverified] | Nat | 7 |
| Soil and foundations | P L | Bearing capacity, settlement formulas · Winkler springs · — | Mohr–Coulomb, hardening soil and Cam-clay critical-state models; consolidation by Biot poroelasticity | Flag always: site investigation data govern; parameters per soil layer | Terzaghi consolidation analytic | Nat | 7 |
| Soil–structure interaction | P L | Impedance functions · — · — | Coupled FEM with absorbing boundaries; domain reduction method for seismic input | Linear soil unless nonlinear declared | Rigid footing impedance analytic | Nat | 7 |
| Seismic analysis | P L | Equivalent lateral force · response-spectrum with modal combination (SRSS, CQC) · — | Nonlinear time history with fibre beam-columns; OpenSees as reference only (commercial products need University of California permission [S44]) | Ground motion selection declared; collapse Flag | PEER and NHERI benchmark data [unverified] | Nat | 7 |

### Marine and offshore

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Hydrostatics and stability | P L | Displacement and metacentric height · righting-lever curves · — | Exact hydrostatics by integration over B-rep or Implicit hulls | Quasi-static; free-surface effects of tanks declared | Box-barge analytic | Nat | 7 |
| Resistance and propulsion | P L | Holtrop–Mennen [unverified] · propeller open-water curves · — | RANS with VOF free surface; sliding mesh or body force propellers | Froude and Reynolds number range of the correlation or calibration | KCS and KVLCC2 cases [unverified] | Nat | 7 |
| Seakeeping | P L | Strip theory · — · response amplitude operators | Linear potential-flow BEM: Capytaine (Apache-2.0) as reference [S42]; Cummins time-domain equations; CFD for extreme seas | Linear wave amplitude relative to body size; slamming and green water Flag | Floating sphere and box analytic coefficients | Nat | 7 |
| Mooring and risers | L | Catenary · lumped-mass lines · — | Nonlinear rod FEM with hydrodynamic loads (Morison) | Morison coefficients from data | Catenary analytic | Nat | 7 |
| Marine fatigue and slamming | P L | Spectral fatigue · — · — | Wave-scatter spectral fatigue on hot spots; slamming pressures from VOF | Slamming Flag always | Classification rule examples [unverified] | Nat | 7 |

### Aerospace

| Domain | Scales | L0 · L1 · L2 | L3 state-of-the-art method | Envelope defaults | Benchmark | Delivery | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Aerodynamics, low speed and rotors | Me P L | Thin-airfoil theory · blade-element momentum, vortex-lattice and panel methods · — | Unsteady vortex particle methods for rotors; RANS and DDES (see Fluids) | BEMT and panel methods attached flow only; rotor–rotor and rotor–body interaction need wake models | Golden product 6 rotor thrust and torque tests | Nat | 4 |
| Aerodynamics, transonic and supersonic | P L | Shock-expansion · — · — | RANS and DG with shock capturing | Shock-induced separation Flag | ONERA M6 wing, ATB [S1] | Nat | 6 |
| Hypersonics and aerothermodynamics | P L | Modified Newtonian · — · — | Thermochemical nonequilibrium Navier–Stokes; DSMC in rarefied regions | Flag always outside verified chemistry models; Ext for nonequilibrium | Double-cone cases [unverified] | Ext | 7 |
| Aeroelasticity | P L | Divergence and reversal formulas · — · doublet-lattice with modal structure | Flutter by p-k method; CFD-based aeroelasticity with modal structure | Linear unsteady aerodynamics for DLM; transonic dip needs CFD | AGARD 445.6 wing [unverified] | Nat | 6 |
| Orbital and spacecraft thermal | P L | Equilibrium temperature · thermal node networks with radiative couplings · — | Monte Carlo ray-traced radiative exchange with orbital environment (solar, albedo, planetary infrared) | Optical properties at beginning or end of life declared | Analytic flat-plate equilibrium | Nat | 6 |
| Launch and space environments | P L | Miles' equation · — · — | Random vibration and acoustic loading (diffuse field) with vibro-acoustics | Load spectra from the launch provider | Analytic SDOF | Nat | 6 |
| Flight dynamics | P | Stability derivatives · 6-DoF rigid-body models with aerodynamic tables, FMI export | — | Table ranges are Refuse bounds | Golden product 6 flight logs | Nat | 4 |

### Multibody and system dynamics

Multibody dynamics of mechanisms is owned by the Mechanical tab (MEC) and is listed here only for coverage completeness: rigid and flexible multibody (floating frame with Craig–Bampton bodies), joints with friction and clearance, contact. System-level models of mixed domains (Modelica-style networks and FMI 3.0.2 exchange) appear as L1 rungs throughout the matrix; Flux owns the DAE solver.

## Product categories and scale tiers

### Coverage by category

| Category | Typical scale | Native coverage | Interop coverage | Golden or proposed product | Phase |
| --- | --- | --- | --- | --- | --- |
| Machined and printed parts | Me P | Linear and nonlinear structure, fatigue, thermal, additive process | STEP AP242, 3MF | GP1 bracket, GP2 lattice bracket | 1 |
| Mechanisms and powertrains | Me P | Contact, gear rating, rotordynamics, lubrication, modal | STEP | GP3 gearbox | 2 |
| Fabrications and sheet metal | P | Shells, welds, weld fatigue, bend and springback | STEP | GP4 welded frame | 2 |
| Moulded electromechanical products | Me P | Moulding, drop test, thermal, EM for PCB thermal and SI | IDX V6 with the ELX tab | GP5 enclosure with PCB | 3 |
| Drones and small vehicles | P | Rotor aerodynamics, aeroacoustics, motors, batteries, structure | FMI, SSP | GP6 drone | 4 |
| MEMS and microsystems | µ Me | Electrostatic, piezo, squeeze-film, thermal | GDSII and OASIS import for layer geometry (proposed) | GP7 MEMS accelerometer (proposed) | 5 |
| Wearables and soft goods | Me P | Hyperelastic, cloth, human factors | — | None; oracle suites only | 5 |
| Industrial machines and robots | P | Multibody, explicit, controls through FMI, machining dynamics | FMI | None; GP3 and GP6 cover the physics | 5 |
| Cars and crash structures | P L | Explicit crash, NVH, CFD aerodynamics, thermal | Solver input-deck export through licensed translator packages | GP8 crash box (proposed) | 5 |
| Aircraft structures and systems | P L | Composites, aeroelasticity, fatigue and damage tolerance | Certification evidence packages | GP9 composite wing box (proposed) | 6 |
| Spacecraft | P L | Orbital thermal, launch vibration, radiation dose (Ext) | — | GP10 CubeSat structure and thermal (proposed) | 6 |
| Ships and offshore | L | Hydrostatics, seakeeping, structure | STEP AP242 hull geometry; class-rule checks as packages | GP11 workboat hull (proposed) | 7 |
| Buildings and civil works | L | Structural analysis and checks, building physics (thermal) | IFC 4.3 (ISO 16739-1:2024) [S45] | GP12 timber pavilion via IFC (proposed) | 7 |
| Implants and medical devices | Me P | Biomechanics, fatigue, credibility packages | — | GP13 bone plate (proposed) | 7 |
| Integrated circuits | N µ | Device physics out of reach; package thermal and stress native | GDSII and OASIS import for packaging and MEMS; OpenROAD (BSD-3) [S46] as the external layout tool | No golden product | Interop 5 |

### Position on buildings

The overview placed buildings out of scope. That is half right. Building authoring needs spatial and zone semantics, jurisdictional codes and a user base that BIM tools already serve, and IFC already carries the exchange. But much of construction is manufactured products: facade units, modular pods, mass-timber connections, prefabricated steel and MEP equipment. These have parts, BOMs and fabrication, which is Crucible's model exactly.

**Decision D-COV-8:** Crucible designs and simulates building products and structures natively, exchanges with BIM through IFC 4.3 (ISO 16739-1:2024 [S45]) import and export packages, and does not author whole buildings (spaces, zones, whole-building energy). Phase 7, with IFC import of context geometry in phase 5. *Why:* prefabricated building products are physical products with BOMs; whole-building authoring is a different product served by mature tools with an open standard between them. *Rejected:* full scope (dilutes the product and duplicates BIM); out of scope entirely (abandons prefabrication, a natural market).

### Position on chip layout

Integrated-circuit physical design (placement, routing, timing closure, DRC and LVS) depends on process design kits under NDA and on abstractions such as standard cells and static timing that are not geometric physics. An open flow already exists: OpenROAD (BSD-3) runs RTL to GDSII and is tested with open PDKs such as SKY130 and ASAP7, while proprietary PDKs cannot be distributed [S46]. MEMS, by contrast, are mechanical devices whose geometry is defined by mask layouts and process steps.

**Decision D-COV-9:** IC layout stays out of scope. Crucible imports and exports GDSII and OASIS layer geometry for MEMS, package design and die-level thermal and stress analysis. It generates MEMS mask layouts from Ingot through a process-emulation package (layer stack, deposition, etch). Phase 5. *Why:* MEMS design and chip packaging are physical design problems Crucible should own; logic layout is not. *Rejected:* an IC layout editor (wrong abstraction, NDA-bound data); no layout interop (blocks MEMS, a founder-named scale).

## Out of reach

These problems cannot be simulated well by Crucible or by anyone in October 2026. Each entry is a record `OutOfReachId` in `std::regime::out_of_reach`, so validity errors can point to it and agents can read it.

| Id | Problem | Why it is out of reach | Best available approach | Crucible behaviour |
| --- | --- | --- | --- | --- |
| OOR-1 | DNS of turbulence at product scale | Cost scales as Re^2.91 [S14]; each tenfold rise in Reynolds number multiplies cost by about 800 | WMLES, whose cost scales as Re^1.14 [S14]; RANS for design loops | DNS Refuses when the a priori estimate exceeds the budget |
| OOR-2 | Wall-resolved LES of high-Reynolds-number external flow | Cost scales as Re^2.72 [S14] | WMLES with non-equilibrium wall models [S15] | Grid estimator reports cost before the run |
| OOR-3 | Predictive RANS for smooth-body separation and corner flows | Model-form error dominates; equilibrium closures also fail to predict separation onset in WMLES [S15]; NASA's CFD Vision 2030 study set routine, physics-based prediction of complex turbulent flows, including separation, as a goal [S17] | Scale-resolving simulation with calibration against tests | Separation regions get Flag zones; RANS result inflated by model-form error |
| OOR-4 | First-principles chemistry of whole products | Electronic-structure cost grows steeply with atom count; a 1 kg aluminium part contains about 2×10^25 atoms | Continuum models with measured parameters; ML potentials (MACE [S31]) for nanoscale properties; ICME chains | MD and DFT data enter only as Material provenance with evidence E1 |
| OOR-5 | Long-horizon degradation without test data (corrosion, polymer ageing, battery calendar life, creep beyond test durations) | Many coupled mechanisms, each sensitive to environment and microstructure; extrapolation in time is uncontrolled | Accelerated tests with a declared acceleration model, Bayesian updating from field data, inspection intervals | Time beyond tested duration is Extrapolated up to 3× and Invalid beyond; never sign-off without data |
| OOR-6 | Ductile fracture and composite failure prediction | A blind round robin of 13 teams found inconsistent predictions [S12]; composite failure theories disagree with each other and with tests [S13] | Building-block test pyramids; calibrated damage models; conservative allowables | Fracture and progressive failure default to Flag |
| OOR-7 | Turbulent combustion, soot and pollutant emissions | Stiff chemistry with hundreds of species; turbulence–chemistry closures are empirical | Flamelet and FGM tables, reactor networks, calibration to rigs | Always Flag; mechanism ranges enforced |
| OOR-8 | Atomization and spray breakup at engineering Weber numbers | Interface-resolved cost grows as We^(12/5) [S16] | Lagrangian sprays with calibrated breakup models | Breakup models Flag |
| OOR-9 | Cavitation erosion, fretting and tribochemistry | Mechanisms span atomic to component scales; coefficients are empirical | Indicators (collapse energy, slip amplitude) plus tests | Indicators only; no life prediction |
| OOR-10 | Exact trajectories of chaotic systems beyond their predictability horizon | Sensitivity to perturbations below floating-point resolution | Statistics with convergence error | Results report statistics; trajectories beyond the horizon labelled |
| OOR-11 | Individual-specimen life and defect-driven scatter | Fatigue and fracture depend on stochastic defects | Probabilistic life with basis values; defect populations from CT | Life outputs are distributions, never single numbers |
| OOR-12 | Patient-specific biological response | Inter-subject variability and adaptation | Population models with credibility packages (E4) | Flag; E4 only through V&V 40 evidence [S8] |
| OOR-13 | Human behaviour and misuse | Not physics | Standards-based checks, user studies | Out of scope beyond anthropometry and biomechanics |
| OOR-14 | Fire spread, explosions, detonations and thermal-runaway venting | Coupled combustion, turbulence and fracture at extreme rates | Specialist external tools and physical tests | Not native; runaway onset only (see Electrochemistry) |
| OOR-15 | Semiconductor device physics and quantum devices | TCAD and quantum transport are separate disciplines with process-specific calibration | External TCAD and compact models | Out of scope |
| OOR-16 | Nuclear criticality safety sign-off | Regulatory quality assurance and benchmark-validated nuclear data required | Licensed codes with benchmark validation | Monte Carlo transport is Ext and never sign-off for criticality |
| OOR-17 | Site-scale geology, weather and climate loads | Governed by site data, not by models | Site investigation and code-specified loads | Site data imported as inputs with provenance |

**Decision D-COV-10:** The out-of-reach list is a versioned `std` record that validity errors reference, and an entry leaves the list only through an evidence-backed proposal approved by humans. *Why:* honesty about limits must be as machine-readable as coverage. *Rejected:* documentation-only limits, which agents and users never see at the moment of decision.

## Adding new physics

Coverage grows only through physics packages (D-COV-1). Built-in physics follows the same path as third-party physics.

### Package contents

A physics package contains:

1. One or more `PhysicsModel` records, each with a domain tag, fidelity level, required Material properties, outputs and envelope.
2. An implementation: an Ingot weak form (preferred), or a Wasm component that implements the WIT world `crucible:physics/solver`, or an external-tool manifest (D-COV-12).
3. Regime-variable functions for any new bounds.
4. Oracles: method-of-manufactured-solutions cases, benchmarks, and validation datasets by CAS hash.
5. An SPDX licence for code and a data licence for every dataset.

```
use std::phys::{PhysicsModel, Fidelity, domain, envelope, bound, refuse, flag}
use std::regime::{equivalent_strain, homologous_temperature}

pub fn linear_elasticity() -> PhysicsModel {
    PhysicsModel {
        id: "std::phys::solid::linear_elasticity@4",
        domain: domain::solid::linear_elastic,
        fidelity: Fidelity::Full3d,
        requires: [Material.elastic_stiffness],
        form: elasticity_form,
        envelope: envelope {
            bound(equivalent_strain, max) { calibrated: 0 .. 0.005, extrapolated: 0 .. 0.02, outside: refuse,
                escalate_to: [solid::finite_strain_plasticity] }
            bound(homologous_temperature, max) { calibrated: 0 .. 0.3, extrapolated: 0 .. 0.4, outside: flag }
            assume("material is homogeneous at the scale of the smallest feature")
        },
        evidence: [oracle("cov/solid/mms_p1_p4"), oracle("cov/solid/nafems_le1_le11")],
    }
}
```

The record syntax is illustrative; the Ingot tab defines record and range syntax.

### Implementation routes

| Route | Use for | What the author gets | Limits |
| --- | --- | --- | --- |
| Ingot weak form | Any PDE system expressible in a variational form | Flux compilation to CPU and GPU, form-level AD, error estimators, Kiln caching | Methods without a weak form |
| Wasm component (`crucible:physics/solver`) | Particle, Monte Carlo, ray-tracing, BEM-kernel and network methods | Sandboxed native speed on every Tier 1 platform and the browser | No clocks, randomness, files or network; randomness comes from a counter-based generator seeded by an explicit input |
| External tool | Large or copyleft codes (OpenFOAM is GPLv3 [S36]; LAMMPS is GPLv2 [S35]; SPARTA is GPL [S34]; OpenRadioss is AGPL-3.0 [S25]) | Reuse of mature solvers without linking them into the core | Runs only on Linux workers; see D-COV-12 |

**Decision D-COV-11:** Non-variational methods (particles, Monte Carlo transport, ray tracing, boundary elements) run their hot loops on general Flux operations: BVH build and traversal, spatial hashing and neighbour lists, segmented reductions, counter-based random streams, and fast-multipole and hierarchical-matrix kernels. Method logic (collision laws, scattering kernels, source terms) lives in Ingot or a Wasm component. *Why:* these loops need GPUs, and this tab assumes Wasm components get no GPU access during evaluation [unverified for WASI 0.3]; general operations serve every method and keep principle 1. *Rejected:* one privileged in-tree solver per method; CPU-only Wasm solvers.

**Decision D-COV-12:** An external tool runs as an Op whose cache key includes the container image digest, the input-deck hash and the platform class. It has no network, a declared determinism class (bitwise or tolerance), and its outputs are imported as Fields with an `ErrorBudget`. It executes only on Linux team servers or cloud workers, so every client OS reaches it identically. *Why:* the contract keeps GPL and AGPL out of the core and calls GPL tools "external tools" without saying how they enter evaluation. *Rejected:* linking copyleft solvers (forbidden); dropping their domains (abandons coverage); unrecorded side runs (break determinism and provenance). See the contract change requests.

### Acceptance and review

1. **Static checks.** The registry rejects a package whose models lack envelopes, whose bounds lack a basis citation, or whose Refuse bounds lack an escalation or out-of-reach reference.
2. **Evidence run.** Registry CI runs the package oracles on every Tier 1 platform class and assigns the evidence level they support (E0 to E2). E3 needs validation datasets held in the protected oracle store, unseen by the author's agents.
3. **Domain review.** A `std` physics package needs two human domain reviewers with no authorship stake. Third-party packages publish at any evidence level, and the registry displays it.
4. **Use policy.** A design repository declares its policy, for example `min_evidence = E2` for sign-off checks. Evaluation enforces it.
5. **Coverage map.** The registry indexes accepted packages by domain tag, scale and fidelity, and `api` exposes the map. Uncovered cells list the nearest packages and the out-of-reach entries.
6. **Domain tags.** New tags are namespaced. Registry review merges duplicates, keeping one name per concept.

Agents can draft packages, oracles and envelope changes. They cannot assign evidence levels, merge envelope widenings or approve reviews.

[[DIAGRAM: Physics package acceptance. Boxes left to right: "Author (person or agent)" → "Package with PhysicsModels, envelopes, oracles, licences" → "Registry static checks" → "Evidence run on every Tier 1 platform class" → "Evidence level E0 to E2" → "Held-out validation (protected store)" → "E3" → "Two human domain reviewers" → "Registry index" → "Coverage map in api". Rejection arrows from "Registry static checks" and "Evidence run" back to the author, each labelled with a typed error.]]

## Materials system

A Material is a versioned, content-addressed record. Designs pin Material versions in the lockfile, so a property change never alters an existing design silently. `std::mat` ships the open library; licensed data arrives through connector packages and stays in the customer's private registry.

### Data model

```rust
pub struct Material {
    pub id: MaterialId,                      // "std::mat::alu_6061_t6"
    pub version: SemVer,
    pub class: MaterialClass,                // Metal | Polymer | Ceramic | Glass | Composite | Fluid
                                             // | Biological | Granular | Electrochemical | Other(DomainTag)
    pub designations: Vec<Designation>,      // UNS, ASTM, EN, JIS, ISO, SAE AMS, GB
    pub condition: Condition,                // temper, heat treatment, product form, thickness range, build orientation
    pub properties: BTreeMap<PropertyId, Property>,
    pub models: Vec<ConstitutiveBinding>,    // ConstitutiveModel id@version, parameters, envelope
    pub provenance: Provenance,              // sources, test records, calibration Ops, approvals
    pub licence: DataLicence,
    pub certifications: Vec<Certification>,
    pub environment: Vec<EnvironmentalRecord>,
    pub microstructure: Option<MicrostructureDescriptor>,
}

pub struct Property {
    pub value: Field<StateDomain, PropertyValue>, // over temperature, strain rate, frequency, ...
    pub basis: StatisticalBasis,                  // Typical | SpecMinimum | ABasis | BBasis | SBasis | Design { code, clause }
    pub uncertainty: Uncertainty,                 // distribution or interval, with correlations
    pub coverage: CalibratedRegion,               // where data exist (feeds validity)
    pub sources: Vec<SourceRef>,
}
```

| Element | Contract | Failure behaviour | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Property over state | `Field<StateDomain, V>` over named state variables (temperature, strain rate, frequency, magnetic flux density, state of charge). Tabulated, piecewise, spline or analytic, with declared interpolation | Reads outside `coverage` follow the property's envelope bound: Extrapolated or Invalid, never clamped | Interpolation exactness on tabulated nodes; monotonicity where declared | 1 |
| Direction | Tensor-valued properties in a material frame. Symmetry class declared: isotropic, cubic, transversely isotropic, orthotropic, monoclinic, triclinic | An ill-formed tensor is rejected at registration with the failing eigenvalue | Positive-definite elasticity; symmetry-group invariance | 1 |
| Units | Every property is a `Quantity<D>`, affine temperature handled correctly | Unit mismatch is a compile error | Ingot type tests | 0 |
| Statistical basis | Each value states its basis. A-basis and B-basis values cover 99% and 90% of the population with 95% confidence [handbook definitions unverified]; 14 CFR 25.613 requires these levels for single-load-path and redundant structure [S51] | Reading a basis the record lacks returns `MissingBasis` with available bases | Tolerance-limit computations against published tables [unverified] | 2 |
| Uncertainty | Distribution (normal, lognormal, Weibull, empirical) or interval, with a correlation matrix across properties | Missing uncertainty makes input error "not quantified" (D-COV-4) | Propagation against Monte Carlo reference | 2 |
| Designations | Typed systems and codes; one Material may carry several equivalents with an equivalence basis (identical specification, or nearest) | "Nearest" equivalents never satisfy a specification check | Registry consistency checks | 1 |
| Certification | Links to specifications (for example ASTM B209 for aluminium sheet [unverified]) and to lot certificates at MBOM level | A release whose Material lacks the required certification fails its check | `repo` release-gate tests | 3 |

**Decision D-COV-13:** Property reads resolve to a statistical basis. The design repository declares a policy (default: specification minimum, else B-basis, else error); every check report names the basis used, and a typical value satisfies a sign-off check only when the policy says so. *Why:* the contract's `0.6 * yield` example must mean one auditable number. *Rejected:* typical values by default (unconservative); requiring an explicit basis at every read (noisy for the common case).

**Decision D-COV-14:** Material properties are Fields over a state domain, and spatial variation enters through state Fields on the Part, never through a second property type. *Why:* one Field type then covers temperature dependence, anisotropy and process-induced variation, and property evaluation composes as `property(state Fields) → Field<Body, V>`. *Rejected:* a separate "material curve" type; per-element material copies.

### Material assignment and state

A Body's material assignment (contract section 5) has three parts: a Material reference with version, an orientation `Field<Body, Rotation>` (rolling direction, fibre angle from draping, build direction), and named state Fields. Standard state Fields are residual stress, equivalent plastic strain, porosity, fibre-orientation tensor, phase fractions, degree of cure and damage. Process simulations write state Fields; downstream models read them. When no state Field exists, the Material's as-specified condition applies and the assumption is recorded.

### Constitutive-model library

A `ConstitutiveModel` is an Ingot function or a Wasm component implementing the WIT world `crucible:material/behaviour`. Its inputs are the kinematic or field state, internal variables and time step; its outputs are flux-like quantities and updated internal variables. Tangents come from form-level AD, so authors write only the update. Each model declares thermodynamic structure (free energy and dissipation potential where one exists), parameters with units, admissibility constraints and an envelope.

| Family | Models in `std::mat::models` | Phase |
| --- | --- | --- |
| Elastic | Isotropic and anisotropic linear elasticity, temperature-dependent; small-strain thermoelasticity | 1 |
| Hyperelastic | Neo-Hookean, Mooney–Rivlin, Yeoh, Ogden, Arruda–Boyce, Gent; hyperfoam; Holzapfel–Gasser–Ogden | 2 |
| Viscoelastic | Generalized Maxwell (Prony) with WLF and Arrhenius shifts; Bergström–Boyce | 3 |
| Plasticity | J2 with isotropic, Chaboche and Yoshida–Uemori hardening; Hill48; Barlat Yld2000-2d; Johnson–Cook; Zerilli–Armstrong; crushable foam; Drucker–Prager | 2 |
| Creep and viscoplasticity | Norton–Bailey, Garofalo, theta projection; Perzyna and Chaboche viscoplasticity | 3 |
| Damage and fracture | Lemaitre; Gurson–Tvergaard–Needleman; Johnson–Cook and Hosford–Coulomb failure loci; cohesive laws; phase-field fracture energy | 3 |
| Composites | Ply elasticity and strength; Tsai–Wu, Hashin, Puck, LaRC05; continuum damage mechanics | 3 |
| Concrete and geomaterials | Concrete damage plasticity; Mohr–Coulomb; modified Cam-clay; hardening soil | 7 |
| Smart materials | Linear piezoelectricity; superelastic shape-memory alloys (Auricchio) | 5 |
| Magnetic | Single-valued B–H with Newton-ready splines; Jiles–Atherton and Preisach hysteresis; Bertotti loss separation | 3 |
| Dielectric and optical | Debye, Cole–Cole, Lorentz–Drude dispersion; Sellmeier and Cauchy indices; measured BSDF tables | 4 |
| Thermal | Isotropic and anisotropic Fourier conduction; enthalpy phase change; emissivity spectra | 1 |
| Fluids | Ideal gas; cubic equations of state (Peng–Robinson); Helmholtz-energy equations through CoolProp [S43]; Cross–WLF, Carreau–Yasuda, Herschel–Bulkley; Oldroyd-B, Giesekus; Tait PVT | 3 |
| Electrochemical | Butler–Volmer kinetics; open-circuit potential curves; concentration-dependent diffusivity and conductivity | 4 |
| Durability | S–N curves with mean-stress models; ε–N parameters; NASGRO-form da/dN; Archard coefficients per tribo-pair | 1 to 3 |
| Contact pairs | Friction laws (Coulomb, rate-and-state) and thermal contact conductance per pair of Materials | 2 |

Every model passes admissibility oracles before release: objectivity under superposed rigid rotation, non-negative dissipation, positive-definite elastic tangent in its envelope, convex yield surfaces where the theory requires convexity, and causality and passivity for dispersive models.

MFront behaviours (GPL with linking exception or CeCILL-A; interfaces to Abaqus, Ansys, Code_Aster, CalculiX and a generic interface [S30]) are the largest open catalogue to interoperate with. Crucible imports MFront behaviours by compiling their generic-interface C++ to Wasm components, subject to legal review of generated-code licensing. Fortran UMAT import is an open question.

### Calibration from test data

Calibration turns test records into a Material version, as a chain of Ops that Kiln caches and `repo` versions.

1. **Ingest.** Test records follow the ISO 10303-235:2019 information model, which covers measured values and the qualifications of the personnel and organizations responsible for measurement [S53]. Records cite the test method (for example ASTM E8/E8M tension [unverified]), specimen geometry, conditions and raw curves.
2. **Reduce.** Engineering to true stress and strain, toe compensation and filtering, each as a declared Op with its parameters.
3. **Identify.** Least squares over the model parameters with AD gradients. For specimens with non-uniform fields, finite-element model updating runs the specimen through Flux; for full-field strain data (DIC), the virtual fields method.
4. **Quantify.** Posterior uncertainty by Laplace approximation, or by Markov chain Monte Carlo with a seed that is an explicit input. Parameter correlations are kept.
5. **Bound.** The calibrated region is the hull of test conditions (joint bounds); the extrapolated region is declared by the calibrator with a rationale.
6. **Admit.** Admissibility oracles run over the whole envelope, not only at test points; hyperelastic fits check Drucker stability.
7. **Allowables.** With enough replicates, basis values come from one-sided tolerance limits on the fitted distribution, following CMH-17 [S57] or MMPDS [S50] procedures [procedure details unverified].
8. **Publish.** A new Material version enters a Proposal with a calibration report: fit residuals, held-out error, parameter uncertainty and envelope.

| Capability | Contract | Failure behaviour | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Curve fitting | `calibrate(model, tests) -> (ConstitutiveBinding, CalibrationReport)` | Non-identifiable parameters reported with the Fisher-information null space; no silent regularization | Recover known parameters from synthetic data with noise | 2 |
| Inverse FE calibration | Specimen model plus measured response | Non-convergence returns the best iterate with the residual history | Synthetic notched-specimen recovery | 3 |
| Full-field calibration | DIC Fields plus geometry | Missing or noisy regions masked explicitly | Synthetic DIC recovery | 5 |
| Allowables | Replicates to A-basis and B-basis values | Too few replicates returns `InsufficientSamples` with the count needed | Published worked examples [unverified] | 3 |
| Model selection | Candidate models ranked by held-out error and parameter count | Ties reported, never broken silently | Synthetic data from a known model | 5 |

### Material databases and licensing

**Decision D-COV-15:** Every Material carries a typed `DataLicence`. Kiln propagates licence obligations to artifacts that embed licensed values, and `repo` export and release checks refuse to redistribute data the licence does not allow. *Why:* material licences differ sharply, and a design shared with a supplier must not leak licensed tables. *Rejected:* trusting users to track licences by hand; refusing all licensed data (loses MMPDS and Granta users).

Results derived from licensed data, such as a stress Field, carry provenance but not redistribution limits, unless the licence states otherwise.

| Source | Content | Licence (as verified) | Integration | Phase |
| --- | --- | --- | --- | --- |
| `std::mat` | Curated open library of common engineering materials with sources per value | Open; each value cites a public or openly licensed source | Built in | 1 |
| NIST Standard Reference Data | 49 free and 41 fee-based databases, including REFPROP and ICSD [S52] | Terms vary by database [unverified] | Connector packages per database; fee-based ones need a customer licence | 3 |
| Materials Project | Computed (DFT) properties of inorganic compounds | CC BY 4.0 for downloaded content; no scraping; data "computed, and may not be accurate enough" [S54] | ICME connector; evidence E1 at most | 5 |
| MMPDS | Statistically based design allowables for aerospace metals and fasteners; MMPDS-2026 is current [S50] | Purchased handbook [licence terms unverified] | Customer-licensed connector; data stays private | 6 |
| CMH-17 | Composite data, test and statistics guidance [S57] | Licensed [terms unverified] | Customer-licensed connector | 6 |
| Ansys Granta MI | Enterprise materials data management; 250,000+ reference materials; MaterialUniverse environmental data [S49] | Commercial | Connector through the customer's Granta API [API specifics unverified] | 5 |
| MatWeb | Datasheet aggregation | Terms forbid redistribution, mass export, and collecting or downloading more than 500 materials [S48] | None; Crucible ships no MatWeb importer | — |
| Plastics databases (CAMPUS, UL Prospector) | Grade data with moulding rheology and PVT | [unverified] | Connector if licensing allows | 3 |
| CoolProp | Fluid thermophysical properties | MIT [S43] | Built in | 3 |
| ICE embodied carbon | 200+ construction materials; V5.0 Educational, June 2026 | Educational use only; software and tools need the licensed IC+ dataset [S55] | IC+ connector under customer licence | 5 |
| ecoinvent | Life-cycle inventory database | Developer licence grants software integration rights; tool users receive LCIA data only [S56] | Connector under a developer licence | 5 |

### Microstructure and ICME

A `MicrostructureDescriptor` records grain size distribution, crystallographic texture, phase fractions, porosity and defect populations, fibre architecture and lattice unit cells, each with measurement provenance. Where these vary in space, they are state Fields on the Part.

| Link | Method | Delivery | Phase |
| --- | --- | --- | --- |
| Process to microstructure | Thermal histories from process models into phase kinetics (JMAK, Koistinen–Marburger) and solidification maps | Nat | 6 |
| Microstructure to properties | Analytic laws (Hall–Petch, rule of mixtures); mean-field homogenization (Mori–Tanaka); FFT RVE solvers with crystal plasticity | Nat, Wasm | 5 |
| Thermodynamics | CALPHAD phase equilibria through customer-licensed tools or open implementations [unverified] | Ext | 6 |
| Atomistic to continuum | DFT and ML-potential results as provenance for elastic constants and surface energies (MACE [S31]; Materials Project [S54]) | Ext | 6 |
| Exchange with external process tools | VMAP data-interface standard [S58] | Interop | 5 |

ICME chains are validated against AM-Bench microstructure, residual-strain and deflection data [S11]. Each link carries its own envelope, so a chain is only as valid as its weakest link.

### Environmental data

An `EnvironmentalRecord` gives a material's global warming potential per unit mass by life-cycle stage, embodied energy, water use, recycled content, recyclability, and restricted-substance declarations. Each value carries geography, reference year, system boundary (cradle-to-gate, cradle-to-site, cradle-to-grave), method standard, source, licence and uncertainty. Product-level life-cycle assessment belongs to another tab (see Open questions); this tab owns the per-material data and its provenance.

**Decision D-COV-16:** Environmental values follow the same provenance, uncertainty and licence rules as mechanical properties, and an embodied-carbon check reports the boundary and year it used. *Why:* carbon numbers vary by source and boundary more than most mechanical properties do. *Rejected:* a single "CO2 per kg" number per Material.

## State of the art

Targets in the last column are targets, measured on the phase 0 reference laptop or a named GPU. Where the leading implementation is copyleft, Crucible measures against it as an external tool and never links it.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Validity and credibility | Risk-informed credibility: ASME V&V 40-2018 [S8], NASA-STD-7009B [S9], FDA guidance of November 2023 [S10]; validation comparison per ASME V&V 20 [S7] | Commercial CAE states validity in documentation, not as data [unverified] | Envelopes as data compiled to Checks; zone Fields; evidence levels (D-COV-3, D-COV-5) | Envelope-completeness and zone-assignment oracles; target: every `std` model has a cited envelope before E2 |
| Code verification | Manufactured solutions with observed order; NAFEMS P18 benchmarks [S2] | Verification manuals of commercial codes, such as MSC Nastran 2021.01 as listed by NAFEMS [S5] | MMS for every `std` weak form; full P18 LE, FV and T coverage | Target: observed order within 0.1 of design order; P18 reference values within 1% [S3][S4] |
| Linear and nonlinear solids | Matrix-free high-order FEM and IGA with AD tangents (FLX specifies the method) | Leading commercial implicit FEA on the reference laptop [baseline unverified] | Flux high-order FEM, IGA and immersed methods | Time to 1% stress error on NAFEMS and GP1 to GP4 models; target: within 2× of the best commercial solver at sign-off |
| Contact | Mortar contact; Incremental Potential Contact for intersection-free large deformation [S26] | IPC Toolkit (MIT) [S26] | Mortar by default; IPC where intersection-free guarantees matter (cloth, snap fits, soft parts) | NAFEMS contact set R0094 [S5]; target: Hertz peak pressure within 1%; zero intersections on the IPC stress suite |
| Fatigue | Multiaxial critical-plane methods with probabilistic S–N | Commercial durability tools [unverified] | Critical plane with basis-aware life distributions (OOR-11) | Held-out coupon and component data; target: 90% of predicted lives within a factor of 3 |
| Fracture | Phase-field fracture, cohesive zones, calibrated ductile damage | Entrants of the Sandia Fracture Challenge [S12] | Phase-field and cohesive defaults; ductile fracture Flag | Sandia challenge data [S12]; target: enter the next blind round |
| Composite failure | Building-block calibration of physically based criteria (LaRC05, Puck) | Theories assessed in WWFE-II [S13] | Criteria library plus calibration; progressive failure Flag | WWFE-II data sets [S13]; GP9 coupon-to-component pyramid |
| RANS CFD | SA, SST, GEKO and transition models as documented by the NASA TMR [S1] | SU2 (LGPL-2.1) [S37]; OpenFOAM (GPLv3, external only) [S36] | Native DG and finite-volume RANS using TMR model definitions | Target: TMR verification results within the spread of the reference codes on the finest grid [S1] |
| Scale-resolving CFD | High-order DG and flux reconstruction on GPUs; non-equilibrium wall models [S15]; a priori cost from Yang–Griffin scalings [S14] | PyFR (BSD) [S27]; Trixi.jl (MIT) [S28] | Entropy-stable DG on Flux GPU backends | 2DWMH hump separation and reattachment [S1]; target: cost per degree of freedom per stage within 1.5× of PyFR on the same GPU |
| Lattice Boltzmann | Multi-GPU LBM with wall models | XLB (Apache-2.0) [S38] | Wasm component on Flux grid and neighbour operations | Cell updates per second on the same GPU; target: parity with XLB's Warp backend |
| Multiphase | Geometric VOF, conservative level set, phase field; resolution criterion k_max·η_KH ≥ 60 [S16] | [unverified] | Native, with a priori resolution estimation | Rising-bubble benchmark; interfacial statistics converge per [S16] |
| Rarefied gas | Direct simulation Monte Carlo | SPARTA (GPL) [S34] | External tool; native slip models | Couette and microchannel analytic cases; code-to-code against SPARTA |
| Low-frequency EM | Nédélec FEM with Newton on B–H curves; A–φ eddy-current formulations | Commercial low-frequency EM tools [unverified] | Native | TEAM 7 and 13 [S6]; target: probe-point field errors under 5% |
| High-frequency EM | High-order Nédélec FEM on GPUs with model-order reduction | Palace (Apache-2.0) [S18] | Native, Palace as code-to-code reference | Target: eigenfrequencies within 0.1% of Palace and time to solution within 1.5× on the same GPU |
| Optics and illumination | Differentiable spectral and polarized Monte Carlo light transport | Mitsuba 3 [S39] | Native ray tracing on Flux BVH operations | Light-guide and integrating-sphere measurements; target: equal-noise time within 2× of Mitsuba 3 |
| Batteries | DFN (P2D) with thermal coupling and reduced models | PyBaMM (BSD-3) [S19][S20] | Native ladder: equivalent circuit, SPM, SPMe, DFN | Target: terminal voltage within 1 mV RMS of PyBaMM DFN on shared parameter sets; 10× faster parameter sweeps |
| Chemical kinetics | Detailed mechanisms in reactor networks and 1D flames | Cantera (BSD-3) [S21][S22] | Wasm component; Cantera mechanism files imported [format details unverified] | Target: equilibrium and ignition delay within 0.1% of Cantera on the same mechanism |
| Granular media | GPU DEM; non-smooth contact dynamics | Project Chrono (BSD-3) [S32] | Wasm component on Flux neighbour operations | Beverloo hopper discharge; particle-steps per second against Chrono |
| Atomistic | Equivariant machine-learned interatomic potentials | MACE (MIT code, model licences vary) [S31]; LAMMPS (GPLv2) [S35] | External tools; results enter as Material provenance | Elastic constants against reference data within the model's published error |
| Plasma and radiation | Particle-in-cell with mesh refinement (WarpX, 2022 Gordon Bell Prize [S33]); continuous-energy Monte Carlo (OpenMC [S23], Geant4 [S24]) | The same codes | External tools | Analytic growth rates and attenuation; code-to-code |
| Biomechanics | Fibre-reinforced hyperelastic FE; musculoskeletal optimal control | FEBio (MIT) [S40]; OpenSim (Apache-2.0) [S41] | Native FE; Wasm musculoskeletal models | Analytic cases; code-to-code against FEBio |
| Seakeeping | Linear potential-flow BEM with Cummins time domain | Capytaine (Apache-2.0) [S42] | Native BEM on Flux fast-multipole operations | Target: added mass and damping within 1% of Capytaine |
| Additive process | Inherent strain, part-scale thermo-mechanics, melt-pool CFD | Entrants of the AM-Bench blind challenges [S11] | Native | Target: blind AM-Bench deflection and residual strain inside the measurement uncertainty for most quantities |
| Constitutive authoring | Domain-specific languages generating integration code | MFront 5.2 (GPL with linking exception or CeCILL-A) [S30] | Ingot behaviours with AD tangents; MFront import as Wasm | Target: stress updates match MFront test cases within 10⁻¹⁰ relative |
| Materials data | Enterprise materials data management with traceable test data | Ansys Granta MI [S49]; ISO 10303-235:2019 information model [S53] | Versioned Material records with typed licences (D-COV-15) | ISO 10303-235 round trip; licence-propagation oracle |
| Allowables | One-sided tolerance limits per CMH-17 and MMPDS procedures [S57][S50] | Handbook procedures and their statistics software [unverified] | Native, with `InsufficientSamples` errors | Target: reproduce published worked examples to 3 significant figures |
| Surrogates | Held-out error with out-of-distribution detection | [unverified] | Training-hull envelopes (D-COV-7) | Interval coverage on held-out data |

## Platform notes

- **Double precision on GPUs.** WGSL defines f32 and an optional f16 extension [S29]; it has no f64 type [unverified against the latest draft], and an Apple WebGPU engineer has said Metal-based implementations would not offer an f64 extension [S59]. Every `PhysicsModel` therefore declares a precision class: `F32Safe` (mixed precision with f64 residuals on CPU) or `F64Required`. `F64Required` models run on CPU or on CUDA and ROCm servers, or on GPU double-float emulation once Flux verifies it, at a declared cost. Interactive mode may use f32 for an `F64Required` model only with an added error-budget term.
- **Browser memory.** Wasm memory64 ships in Chrome 133 and Firefox 134 but sits behind a flag in Safari [S60]. Browser sessions keep L3 solves under 4 GB of address space and send larger solves to team workers. Workers run the same Ops, so results agree within the declared cross-platform tolerance, and each result records the platform class that produced it.
- **Relaxed SIMD.** Relaxed SIMD ships in Chrome 114 and Firefox 145 and is behind a flag in Safari [S60]. Its results can differ by hardware, so physics operations do not use it inside a platform class that requires bitwise identity.
- **External tools.** External tools run only in Linux containers on team servers or cloud workers (D-COV-12). Any desktop may host a local worker in a Linux virtual machine. Browser sessions always use remote workers. Air-gapped installs mirror container images by digest.
- **Monte Carlo determinism.** Particle and transport methods use counter-based random streams keyed by (seed, particle id, event index). Reductions run in a fixed order, so results are bitwise identical within a platform class at any thread count.
- **Validity zones across platforms.** The worse-zone rule near bounds makes zone Fields identical across platform classes even when solution values differ within tolerance.
- **Material data offline.** Connector packages fetch data only at import time, outside evaluation. Imported records are pinned in CAS, so builds run air-gapped. Licensed data live in the customer's private registry mirror.

## Interfaces with other subsystems

### Provided

| To | What COV provides | Canonical types |
| --- | --- | --- |
| Flux (FLX) | `PhysicsModel` and `ConstitutiveModel` definitions as Ingot weak forms or Wasm components; regime-variable functions; envelope records; required operation list (D-COV-11) | `Field`, `Material`, `ValidityEnvelope`, `Op` |
| Ingot (ING) | `std::phys::*`, `std::mat::*` and `std::regime` packages; envelope and record syntax requirements | Ingot packages |
| Kiln (KLN) | Envelope and Material records as CAS inputs; calibration chains as Ops; external-tool Op cache keys (D-COV-12) | `Op`, CAS hashes |
| `repo` | Material versions, waiver records, release-gate checks for validity, certification and data licences | `Material`, `Check` |
| `api` and agents (AGT) | The coverage map; out-of-reach records; typed `ValidityError`s with escalation lists; calibration Ops | `api` Read and Inspect groups |
| UI (UIX) | Validity zone Fields, `ErrorBudget` displays, basis citations and escalation options | `Field<Body, ValidityZone>` |
| Mechanical (MEC) | Solid, contact, fatigue and dynamics models with envelopes | `PhysicsModel` |
| Manufacturing (MFG) | Process physics models; state Fields for downstream analysis | `Field` |
| Electronics (ELX) | EM, thermal and signal-integrity physics with envelopes; electronic material records | `PhysicsModel`, `Material` |
| Platform (PLT) | Precision classes per model; external-tool worker requirements | Model metadata |
| Owner of product life-cycle assessment (tab to be confirmed; see Open questions) | Per-material environmental records with boundary, year, source and licence | `EnvironmentalRecord` inside `Material` |

### Consumed

| From | What COV needs | Canonical types |
| --- | --- | --- |
| Flux | A posteriori discretization and solver error estimates as Fields; form-level AD for tangents, calibration and sensitivities; the operations named in D-COV-11; coupling algorithms; double-precision policy per backend | `Field`, `ErrorBudget` |
| Ingot | Record types, quantity intervals and dimension-checked regime functions; `require` with severity; a way to attach envelopes to models | `Quantity<D>`, `Check` |
| Kiln | Deterministic evaluation of calibration and external-tool Ops; licence propagation along derived artifacts | `Op` |
| `repo` | Human-only waivers and envelope approvals; release checks for data licences | `Proposal` |
| Package registry (owning tab to be confirmed) | Physics package acceptance pipeline and the coverage index | Package |
| Interop | IFC 4.3, GDSII and OASIS readers and writers; ISO 10303-235 for test data | `Body`, `Material` |
| Anvil | Implicit and lattice Bodies for immersed analysis; per-entity tolerances for scale checks | `Body`, `ErrorBound` |

## Oracles

Oracles live in the protected directory `oracles/cov/`. Agents can read them but not write them. Held-out validation datasets live in a store agents never see.

| Oracle | What it checks | Tolerance (target) | Phase |
| --- | --- | --- | --- |
| `cov/envelope_completeness` | Every exported model declares an envelope, every bound cites a basis, every Refuse bound names an escalation or an out-of-reach entry | Exact | 0 |
| `cov/zone_assignment` | Synthetic regime Fields produce the expected zone Field, including the worse-zone rule at boundaries | Exact | 1 |
| `cov/zone_cross_platform` | Zone Fields are identical across all Tier 1 platform classes on the golden models | Exact | 1 |
| `cov/refuse_behaviour` | A Refuse bound blocks dependent checks and emits `ValidityError::OutsideEnvelope` with fixes | Exact | 1 |
| `cov/waiver_human_only` | Agent credentials cannot create waivers or widen envelopes | Exact | 1 |
| `cov/mms/<model>` | Manufactured-solution convergence at the declared order | Observed order within 0.1 | 1 onward |
| `cov/nafems_p18` | LE, FV and T benchmarks of NAFEMS P18 | 1% of reference values | 1 to 3 |
| `cov/nafems_nonlinear` | Groups R0024, R0027, R0094, R0020 and R0031 | Per benchmark | 2 to 4 |
| `cov/tmr` | NASA TMR verification cases | Within the spread of reference codes | 4 |
| `cov/team` | TEAM 7, 13 and 36 | Measured data within published uncertainty | 3 to 4 |
| `cov/ladder/<domain>` | Fidelity-ladder consistency inside the narrower envelope (D-COV-2) | Per ladder, for example 1% for beams | 1 onward |
| `cov/ambench` | Blind predictions of AM-Bench residual strain and deflection | Inside measurement uncertainty | 4 |
| `cov/material_admissibility` | Objectivity, dissipation sign, positive-definite tangents, Drucker stability, causality and passivity over each envelope | Exact or 10⁻¹² relative | 1 onward |
| `cov/material_units` | Every property dimension-checks; affine temperature handled correctly | Compile-time | 0 |
| `cov/calibration_recovery` | Calibration recovers known parameters from noisy synthetic data, with credible intervals that cover the truth | 95% interval coverage within 2 points of nominal | 2 |
| `cov/allowables` | Basis values reproduce published worked examples | 3 significant figures | 3 |
| `cov/licence_propagation` | Export of a design embedding licensed data fails; export of derived results succeeds | Exact | 3 |
| `cov/external_op_determinism` | External tools rerun from the same image digest give identical or within-tolerance outputs per their declared class | Per class | 4 |
| `cov/uq_propagation` | First-order and quasi-Monte Carlo propagation against a high-sample reference | Mean and variance within 2% | 2 |
| `cov/golden_validation` | Golden-product checks hold against physical test data where the gate includes tests (GP6 by contract; GP4 distortion and GP5 warpage and drop as requested below), with zone Fields Calibrated on critical regions | Per golden product | 2 to 4 |

## Phasing

| Phase | Coverage delivered | Gate contribution |
| --- | --- | --- |
| 0 | Envelope schema and `cov/envelope_completeness`; regime-variable mechanism; Material record and units; evidence levels; `ErrorBudget` | Determinism suite includes zone Fields |
| 1 | Linear elasticity, modal, linear buckling, conduction, stress-life fatigue, lattice homogenization, inherent-strain additive; `std::mat` metals and print polymers | GP1 and GP2 sign-off checks at E2 or above |
| 2 | Plasticity, hyperelasticity, contact, joints, harmonic, random and shock, rotordynamics, strain-life and weld fatigue, welding inherent strain, sheet-metal bend, machining stability, calibration Ops, allowables | GP3 and GP4 |
| 3 | Viscoelasticity, creep, crack growth, LEFM, wear, laminates, radiation, phase change, laminar CFD, porous media, generalized Newtonian flow, acoustics, electrostatics, magnetostatics, injection moulding, drop test, reach and fit, data connectors | GP5 |
| 4 | RANS and conjugate heat transfer, rotor aerodynamics, tonal aeroacoustics, eddy currents, motors, antennas, batteries, progressive failure, flight dynamics, AM thermo-mechanics, welding transient | GP6, validated against physical tests |
| 5 (proposed) | Scale-resolving CFD, compressible flow, multiphase, rarefied flow, microfluidics, MEMS, piezoelectrics, EMC, illumination, optics, granular, FE², posture, cloth, stamping, crash, battery degradation, corrosion, ICME links, GDSII interop, IFC import | GP7 MEMS accelerometer; GP8 crash box |
| 6 (proposed) | Combustion, cavitation, wave optics and photonics, MPM, SPH and peridynamics, MD (external), casting, heat treatment, melt pool, transonic and supersonic aerodynamics, aeroelasticity, orbital thermal, launch environments, ablation, fuel cells | GP9 composite wing box; GP10 CubeSat |
| 7 (proposed) | Civil structures and geomechanics, seismic, marine, hypersonics (external), plasma, radiation transport (external), biomechanics with V&V 40 packages, IFC export | GP11 workboat hull; GP12 timber pavilion; GP13 bone plate |

Phase 5 to 7 golden products are proposals. Each needs a physical test partner before its gate is fixed.

## Open questions

1. **Envelope evaluation cost on large transients.** Pointwise regime Fields at every saved step may cost more than 2% of the solve. Should transient assessment run at output steps only, with a declared sampling risk?
2. **Joint-hull dimensionality.** Hulls of validation points in more than about six regime dimensions are sparse. Is a Gaussian-process density over regime space a better calibrated-region model?
3. **Model-form error without validation data.** E2 models have no measured model-form error. Should Crucible publish default inflation factors per domain, or keep "not quantified"?
4. **Fortran UMAT import.** Many industrial constitutive models exist only as Fortran UMATs. Is a Fortran-to-Wasm toolchain mature enough on every Tier 1 platform?
5. **Legal review of data licences.** NIST SRD terms, MMPDS, CMH-17, CAMPUS and Granta API terms need counsel before connectors ship.
6. **Owners of the registry and of life-cycle assessment.** The contract lists tab code ECO without a scope. If ECO is the package ecosystem tab, it owns the acceptance pipeline this tab relies on, and product-level life-cycle assessment still needs an owner.
7. **Test partners.** Phase 5 to 7 golden products need physical test data. Which partners, and under what data rights?
8. **Certification claims.** Regulated industries need qualified tools, for example under DO-330 [unverified]. Should Crucible pursue tool qualification for a subset of `std` physics in phase 6 or later?
9. **Double-float emulation.** Is emulated f64 on WebGPU accurate and fast enough for sign-off solves, or do `F64Required` models stay on CPU and server GPUs?

## Contract change requests

1. **Add `ErrorBudget` to the core types (section 5).** Every result Field needs discretization, solver, input and model-form components. Without a shared type, each tab reports error differently, contradicting "every approximation states its error".
2. **Define "external tool" (sections 4, 7 and 9).** The contract mentions GPL tools as external tools but not how they enter evaluation. Proposed: D-COV-12, an external Op with an image digest in the cache key, no network, a declared determinism class, Linux workers only, and identical access from every OS.
3. **Flux operations for non-variational methods (section 4).** D-COV-11 needs BVH, neighbour-list, segmented-reduction, counter-based random and fast-multipole operations in Flux. Without them, particle, ray-tracing and BEM physics cannot use GPUs without privileged code.
4. **Extend `Material` (section 5).** Add statistical basis per property, `DataLicence`, environmental records and microstructure descriptors, as specified in the materials data model.
5. **Make `ValidityEnvelope` policy explicit (section 5).** Replace "results outside it are flagged" with zones (Calibrated, Extrapolated, Invalid, Unassessed) and dispositions (Flag, Refuse), so refusal is part of the contract.
6. **Scope statement (section 1 and overview).** Replace "buildings out of scope" with D-COV-8 and "chip layout out of scope" with D-COV-9.
7. **Physical tests in earlier gates (section 7).** Add measured weld distortion to the GP4 gate and measured warpage and drop response to the GP5 gate. Otherwise manufacturing-process physics cannot reach E3 before phase 4.
8. **Field domains and values (section 5).** Section 5 already calls Material properties "property Fields", but defines Field over a Body or region. Allow parameter-space domains (temperature, strain rate, frequency) and categorical values (validity zones), so D-COV-5 and D-COV-14 use Field without a parallel type.

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
