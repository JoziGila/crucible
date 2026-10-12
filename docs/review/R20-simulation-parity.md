# R20 competitive parity (simulation and electronics) review

Summary: The spec never gives analysts the idealization primitives every incumbent model uses: remote points (rigid and distributing couplings), point masses, springs, bushings, fastener connectors, 2D plane and axisymmetric models, and symmetry or cyclic-symmetry reduction. Without them a Crucible model of an ordinary bracket-with-motor or O-ring seal costs 10 to 100 times an Ansys or Abaqus model.
Linear dynamics practice (prestressed modal, mode-superposition harmonic, PSD random response, response spectrum, damping models) has no owner, no oracle and, for response spectrum, phase 7. Load-case combination, stress linearization and assembly contact detection are missing as well.
Migration and coexistence fail at the seams: imported Nastran and Abaqus decks have no execution contract, Modelica source cannot be imported, and vendor SPICE models run only on remote Linux workers.
CFD and RF lack whole workflow families that GP5, GP6 and GP11 need: rotating frames, fan models, adjoints on the production flow path, Floquet ports, and 3D partial-inductance extraction.
Crucible's real advantages (no meshing or defeaturing, associative results with bounds, determinism, typed weak forms) are not stated against the incumbents; FLX compares itself only with open-source codes, and ELX ignores JITX, tscircuit and flux.ai.

### R20-01 · Critical · Targets: FLX, COV, MEC, UIX
**Section:** FLX "Contact, constraints and fracture"; FLX "Operators, problem kinds and checks"; COV "Solid mechanics"; UIX "Studies and results"
**Problem:** Flux has no remote point (a rigid or a distributing coupling from a face to a reference point), no point mass with rotary inertia, no grounded or two-point spring and damper, no six-DOF bushing and no fastener or spot-weld connector. FLX's constraint row lists "multi-point, periodic, cyclic and integral constraints" generically, and UIX's study setup offers only "fixed, force, pressure, preload, temperature, convection". An analyst who models a motor on a bracket, a load through an unmodelled clevis, or a PCB on standoffs uses these primitives in nearly every Ansys or Nastran model; in Crucible they must model the motor and clevis as solids, which is slower, changes the answer at the attachment and breaks modal mass.
**Evidence:** Ansys Mechanical's remote point behaviors: Deformable is "similar to the Mechanical APDL constraint defined by the RBE3 command", Rigid "similar to ... the CERIG command" (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_Geometry_Behavior.html). Ansys's Nastran export maps rigid and deformable remote points to RBE2 and RBE3, bushings to CBUSH and point masses to CONM2 (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_NASTRAN_export_supported_features.html). FLX line 593 and UIX line 591 name none of them.
**Fix:** Add an FLX subsection "Idealizations" under "Contact, constraints and fracture" with one capability row each, phase 1 for the first three and phase 2 for the rest:
- `remote_point(faces, at: CoordSys, behavior: Rigid | Distributing { weight: Uniform | Area | Distance })`, enforced by multipliers on fitted meshes and Nitsche on the octree, returning a point whose six DOFs take forces, moments, displacements, masses and springs. Oracle FLX-O-IDEAL-1: reactions and displacements equal a fitted RBE2/RBE3 reference on 20 cases; a distributing coupling adds no stiffness (eigenvalues of a free plate unchanged within 10⁻⁸).
- `point_mass(at: remote_point or vertex, m, J: Tensor)`; checks of mass properties include it (MEC).
- `spring(a, b, k: Tensor6, c: Tensor6)` and `bushing(...)` with grounded variants.
- Phase 2: `fastener(holes, spec)` from MEC's `fasten` Instance sets, as a beam-plus-distributing-coupling connector with VDI 2230 preload, and `spot_weld(points, d)`.
Each primitive is an Ingot function over `Query` targets, so it stays associative; UIX's study template adds them to the condition list. COV adds a regime variable "coupling region diameter over local wall thickness" so a rigid coupling on a thin wall is `Flag`, since rigid couplings stiffen thin walls.

### R20-02 · Critical · Targets: FLX, COV, CONTRACT
**Section:** Contract 7.1 Flux (per-region discretization); FLX "Per-region models", "Spaces, elements and measures"; COV "Solid mechanics", "Electromagnetics"
**Problem:** No tab offers plane stress, plane strain, generalized plane strain, axisymmetric (with or without torsion) models, mirror-symmetry or antisymmetry reduction, or cyclic symmetry with harmonic indices (nodal diameters) for modal and static solves. Contract 7.1's per-region list reduces only to shells and beams. O-ring and lip seals, pressure vessels, flanges, rotating discs, bolts, solenoids and coils are routinely solved as axisymmetric models in Abaqus, Ansys and COMSOL at one hundredth of the 3D cost; bladed discs and fans use cyclic sectors. A hyperelastic seal with contact in 3D on an octree is impractical where the incumbent solves it in seconds.
**Evidence:** Abaqus's axisymmetric library has CAX, CGAX "Generalized axisymmetric elements with twist", thermally coupled, pore-pressure, acoustic and piezoelectric variants (https://ceae-server.colorado.edu/v2016/books/usb/pt06ch28s01ael05.html). Ansys Mechanical lists "symmetry region" and "cyclic region" objects (https://ansys.synopsys.com/products/structures/ansys-mechanical). COMSOL documents symmetry, antisymmetry and periodic conditions to reduce a coil "to a one-eighth model" (https://www.comsol.com/blogs/exploiting-symmetry-simplify-magnetic-field-modeling). `grep -i "axisymm\|plane strain\|harmonic index\|nodal diameter"` over `docs/spec` returns nothing; FLX line 593 names "cyclic constraints" only as a constraint type.
**Fix:** Contract change request (FLX files it): extend 7.1's per-region rule with "dimensional reduction by symmetry: plane stress, plane strain, generalized plane strain and axisymmetric models, detected or declared, and symmetry, antisymmetry and cyclic-sector reductions, each with a check that loads and geometry satisfy the symmetry". In FLX:
- `flux::mark_reduction` gains `ReductionKind::Axisymmetric { axis }` and `Planar { kind }`, detected when Anvil's certified analysis shows a revolved or prismatic Body and the study's conditions share the symmetry; `std::sim::symmetry(planes:, kind: Symmetric | Antisymmetric)` and `cyclic(sector:, count:, harmonics: 0..=N/2)` are explicit.
- Spaces: `H1(domain: section, kind: axisymmetric(twist: bool))` with the r-weighted measure, Fourier-mode extension for non-axisymmetric loads in phase 3.
- Cyclic modal analysis solves complex Bloch-periodic sector problems per harmonic index and returns a `Field<(Body, Mode, HarmonicIndex), Displacement>`; the full-model expansion is a display operation.
- A violated symmetry (a non-symmetric load, a feature off the plane) returns `SymmetryBroken { entity }`, never a silent wrong answer.
Phase 1 for planar and axisymmetric elasticity and thermal (they reuse H¹ kernels in 2D), phase 2 for symmetry with contact and hyperelasticity, phase 2 for cyclic modal (fans and gear blanks in GP3). Oracle FLX-O-SYM-1: axisymmetric thick cylinder (Lamé), NAFEMS axisymmetric cases and a cyclic bladed-disc modal benchmark agree with the full 3D model within the 3D model's budget. COV adds the axisymmetric and planar rungs to the solid, thermal and magnetostatic ladders (D-COV-2).

### R20-03 · Major · Targets: FLX, COV
**Section:** COV "Dynamics and stability"; FLX "Eigenvalue problems", "Reduced models and surrogates"
**Problem:** The linear dynamics workflow analysts rely on is incomplete and has no owner. Prestressed modal and buckling (stress stiffening from preload, pressure or spin, and spin softening) appear nowhere. Mode-superposition harmonic response, PSD random response and response spectrum are listed only in COV's "Vibration and shock" row with no FLX operation, capability row or oracle; response-spectrum analysis appears only as a civil L1 rung in phase 7. Damping models (Rayleigh, modal, structural hysteretic, frequency-dependent viscoelastic) are "declared" without a type. Vibration fatigue from PSD (Dirlik, narrow band) is missing from the durability rows.
**Evidence:** Ansys Mechanical names "modal, harmonic, spectrum response and random vibration" (https://ansys.synopsys.com/products/structures/ansys-mechanical); its Nastran export lists "Modal (Pre-Stressed): SOL103, STATSUB" (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_NASTRAN_export_supported_features.html). COV line 268 ("Direct frequency response; PSD response") cites no FLX oracle; COV line 449 phases response spectrum at 7.
**Fix:** FLX adds a "Linear dynamics" subsection with these rows:

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Linear perturbation | Modal and buckling about a converged nonlinear state, with stress stiffening, spin softening and pressure load stiffness | `BaseStateNotConverged` | FLX-O-DYN-1 | 2 |
| Mode-superposition harmonic | Modes plus residual vectors; `Field<(Body, Frequency), Complex<V>>`; truncation part in the budget | `ModalTruncation { missing_mass }` above 10% | FLX-O-DYN-2 | 2 |
| Random vibration | PSD inputs, one- and multi-point, 1σ and 3σ Fields, correlation | As above | FLX-O-DYN-2 | 2 |
| Response spectrum | Single- and multi-point; SRSS, CQC, NRL and DDAM combination; missing-mass correction | As above | FLX-O-DYN-3 | 2 |
| Damping | `Damping::Rayleigh`, `Modal`, `Structural`, `Viscoelastic(Field<Frequency, ...>)` on Materials and joints | Undamped resonance in a harmonic band fails | FLX-O-DYN-2 | 2 |

COV moves response spectrum to phase 2 in its "Vibration and shock" row, adds Dirlik and narrow-band PSD fatigue to "Stress-life" (phase 2), and points rotordynamics' rotating-frame rung at FLX-O-DYN-1. Oracles: NAFEMS forced-vibration benchmarks and an analytic SDOF and two-DOF spectrum case.

### R20-04 · Major · Targets: COV, ELX, OVERVIEW
**Section:** COV "Coverage matrix"; ELX "Phasing"; Overview roadmap
**Problem:** No tab tells an engineer when Crucible matches the tool they use today. The coverage matrix lists methods by domain and phase, but nothing maps an incumbent workflow tier (linear static and modal of an assembly; nonlinear contact; harmonic and random; laminar CFD; turbulent CFD; schematic plus two-layer board; high-speed board) to the phase where every capability it needs exists. Reviewers and buyers cannot judge the bar "nothing they rely on missing", and gaps such as R20-01 and R20-02 stay invisible because no row lists the workflow.
**Evidence:** COV's matrix and FLX's phasing list capabilities, not workflows; ELX phase 1 and 2 give no board capability (ELX "Phasing"). The present review found its first two Critical gaps only by building such a checklist from Ansys, Abaqus and Nastran documents.
**Fix:** Add to COV a "Parity map" table, one row per workflow tier: workflow · capabilities it needs (by FLX, COV, ELX row) · incumbent reference (Ansys Mechanical, Abaqus/Standard, Fluent, HFSS, Altium Designer, Dymola) · phase at which all rows exist · Crucible's difference. The spec check fails if any listed capability lacks a row or carries a later phase than the tier. ELX adds the board tiers; the Overview cites the table in one line.

### R20-05 · Major · Targets: FLX, COV
**Section:** FLX lead, "Scope and architecture", "State of the art"; COV "State of the art"
**Problem:** FLX never says why an Ansys, Abaqus or COMSOL user is better off. Its lead names methods; its State of the art table names only open-source leaders (DOLFINx, MFEM, deal.II, SLEPc, Palace) and LS-DYNA once. The advantages that incumbents cannot copy quickly are scattered and unstated as advantages: solves on the exact B-rep with no meshing or defeaturing step; results that stay associative with the design and recompute incrementally; every result with a bound in a stated norm, a validity zone and a confidence; bit-identical results across platforms for audit; weak forms with compile-time dimensions and form-level derivatives (COMSOL offers a Weak Form PDE interface, so "weak forms" alone is not a difference); and agents that run studies under the same checks.
**Evidence:** COMSOL documents "Weak Form PDE (w)", with boundary, edge and point variants (https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_ref_equationbased.32.023.html), and its Application Builder (https://www.comsol.com/comsol-multiphysics). FLX lines 860 to 889 name no commercial code except LS-DYNA. Ansys Mechanical advertises "Mesh Quality Worksheet" and automated meshing (https://ansys.synopsys.com/products/structures/ansys-mechanical), which Crucible makes unnecessary but never says so.
**Fix:** Rewrite FLX's lead's last sentence as: "Unlike Ansys, Abaqus and COMSOL, Flux solves on the exact design geometry without a meshing or defeaturing step, recomputes only what an edit touches, and reports every result with a bound, a validity zone and a confidence, identically on every platform." Add a column "Incumbent reference" to FLX's and COV's State of the art tables (Ansys Mechanical, Abaqus, Simcenter Nastran, COMSOL, Fluent, STAR-CCM+, HFSS per row) and state the measured difference in "How we measure" (for example, "time from STEP import to a decided stress check, against Ansys Mechanical on the same 20 parts, including meshing and defeaturing").

### R20-06 · Major · Targets: ECO, FLX, COV
**Section:** ECO format catalog ("Nastran BDF; Abaqus input"); FLX "Interfaces with other subsystems"
**Problem:** ECO reads and writes Nastran BDF and Abaqus input at phase 3 as "FE models; OP2 results as Fields", but no tab says what Crucible does with an imported deck: Flux has no element semantics for CQUAD4, CBUSH, RBE3, CONM2, PCOMP, MPCs or SPCs on grid ids, so a company's validated legacy models can be viewed but not run or compared. The export direction matters as much: aerospace and defence customers deliver Craig–Bampton models as Nastran DMIG or OP4 for coupled loads analysis, and some regulators expect the qualified incumbent's run. LS-DYNA keyword decks, the crash and drop lingua franca, are absent.
**Evidence:** ECO line 224; Ansys documents a mapping of its own model to SOL101, SOL103, SOL109, RBE2, RBE3, CBUSH and CONM2 (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_NASTRAN_export_supported_features.html), showing that deck export with idealizations is what users expect.
**Fix:** FLX adds "Imported FE models" with a contract: an imported deck becomes a `Mesh` Body plus a study whose cards map to Flux forms and R20-01's idealizations; unmapped cards fail with `UnmappedCard { card, line }`, never dropped. Oracle FLX-O-DECK-1: the NAFEMS decks distributed for Nastran verification run in Crucible within 1% of their reference values. Add export of a study to BDF (SOL 101, 103, 111, 112) and of Craig–Bampton reductions as DMIG and OP4, phase 3, so an incumbent can re-run a Crucible model. ECO adds LS-DYNA keyword read for meshes, parts, materials and contacts at phase 3 with GP5's drop model. The deck route is labelled `Unverified` until its oracle passes per card family.

### R20-07 · Major · Targets: CONTRACT, FLX, PLT
**Section:** Contract 13.3; FLX "Interactive latency", "Linear algebra", "State of the art"
**Problem:** The only solve-size target is `Interactive` elasticity up to 100,000 DOFs; there is no target for a `SignOff` solve of the size analysts run daily (5 to 50 million DOFs on a workstation), and none for CFD throughput. Phase 1's canonical direct solver reaches "about 2M DOFs" and distributed solves wait for phase 4. Meanwhile Fluent's native GPU solver reports single-GPU speed-ups of 8 to 15 times over 8 to 32 CPU cores, and Crucible's canonical class runs CPU-only with no flow target at all.
**Evidence:** Contract 13.3 row "Interactive simulation update"; FLX lines 528 and 549. Ansys reports "8.32X for an air intake system" and "8.6X for a traction inverter" on one A100 (https://ansys.synopsys.com/blog/unleashing-the-full-power-of-gpus-for-ansys-fluent-part-2), vendor-stated.
**Fix:** File a change request adding two 13.3 rows, both targets: "`SignOff` linear static, 10M DOFs at p = 2 on an immersed GP1-class part, recertified, under 10 minutes on the reference workstation (phase 2) and 50M DOFs on a 64-core server (phase 3)"; "incompressible flow, 10M cells laminar steady to residual 10⁻⁶, time per iteration within 2× of OpenFOAM on the same CPU (phase 3) and, on a `Gpu` class with CPU certification, within 2× of Fluent's published GPU speed-up shape on the same case family (phase 4)". FLX states the per-phase DOF ceiling in "Linear algebra" and adds FLX-O-KER-7 for both rows.

### R20-08 · Major · Targets: FLX, MEC
**Section:** FLX "Contact, constraints and fracture"; MEC "Interference and clearance"
**Problem:** The commonest analyst task, a static or modal solve of a multi-part assembly with bonded and frictionless interfaces, has no defined path before phase 3 on the immersed octree: bonded interfaces use mortar on fitted tetrahedra in phase 2, and immersed Nitsche contact waits for phase 3. Phase 2 users therefore mesh, losing Crucible's no-meshing advantage exactly where assemblies begin. Automatic interface detection, which Abaqus offers as general contact over an "all-inclusive" surface, is only implied by MEC's "contact candidates" and UIX's "unconfirmed contacts".
**Evidence:** FLX lines 594 and 595; Abaqus's general contact "allows for a highly automated contact definition" (https://abaqus-docs.mit.edu/2017/English/SIMACAEGSARefMap/simagsa-c-cntgeneral.htm).
**Fix:** Add to FLX a phase 2 row "Immersed tied interfaces": Nitsche tie across `dI` between Instances on the octree, with interfaces found by MEC's interference classes (touching faces within the definition tolerance), default `Bonded` for welded or glued contact and `Frictionless` otherwise, each listed for confirmation in UIX's pre-flight. Oracle: a two-block tied patch test and a bolted lap joint against fitted mortar, inside the fitted model's budget. Keep mortar on fitted meshes for frictional contact as now.

### R20-09 · Major · Targets: FLX, COV, MEC
**Section:** FLX "Domains and values" (`LoadCase` index set), "Post-processing and display"
**Problem:** `LoadCase` is an index domain, but nothing defines load-case combination: factored linear superposition, envelopes (max and min over cases with the governing case recorded), and code combinations (Eurocode ULS and SLS, AISC LRFD). Nastran subcases and Ansys solution combinations do this routinely, GP8's structural check needs it, and the error budget of a combined result (bounds add only in one norm; superposition is valid only for linear solves) is unspecified.
**Evidence:** Contract section 5 lists `LoadCase` among `Field` index sets; `grep -i "load combination"` over `docs/spec` returns nothing.
**Fix:** FLX adds `std::sim::combine(cases, factors)` and `envelope(cases, by: Max | Min | AbsMax)` returning Fields over `(Body, Combination)` plus a `PerEntity` governing-case Field. Superposition requires every case from one linear solve and fails with `NonlinearSuperposition` otherwise; budgets combine by the factors' absolute values per norm. COV's civil rows cite a `std::systems` code-combination package per standard edition (licensed data, D-ELX-30's rule). Phase 2; oracle: hand-combined frame cases.

### R20-10 · Major · Targets: FLX, COV
**Section:** FLX "Post-processing and display"; COV "Civil structures and geomechanics"
**Problem:** Pressure-vessel and piping engineers classify stress by linearizing it through the wall into membrane, bending and peak parts (ASME Section VIII Division 2 Part 5, EN 13445). No tab offers stress linearization. This is also a missed advantage: membrane and bending stresses are bounded linear functionals of the stress over a stress classification line, so Flux could report them with `Guaranteed` goal bounds where the incumbent reports unbounded numbers.
**Evidence:** Ansys's Linearized Stress results "calculate membrane, bending, peak, and total stress along a straight line path" (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_linearized_stresses.html). Contract 5 admits `Guaranteed` goal bounds for "bounded linear functionals".
**Fix:** Add `f.linearize(along: Query or segment, curvature: Auto)` returning membrane, bending and peak tensors with goal-oriented bounds (`Guaranteed` on fitted simplices with polynomial data, calibrated `Estimated` elsewhere), phase 2. COV adds a pressure-equipment row (ASME VIII-2 Part 5 and EN 13445-3 design-by-analysis, licensed data packages) in phase 5 with GP8's structural checks, with ratcheting and plastic-collapse routes on FLX's plasticity rows.

### R20-11 · Major · Targets: FLX, COV
**Section:** FLX "Fluids and free surfaces"; COV "Fluids", "Aerospace", "Heat transfer"
**Problem:** No tab offers rotating-machinery CFD: a moving reference frame, a mixing plane or a sliding mesh. Nor does it offer the macro models electronics cooling relies on: a fan as a pressure jump with a P–Q curve, perforated plates, heat-exchanger and porous-resistance blocks. GP6's propellers and motor cooling, GP5's enclosure if it gets a fan, and every pump, blower and compressor need them. COV routes rotors to blade-element and vortex methods only.
**Evidence:** Fluent offers the Multiple Reference Frame model, the Mixing Plane Model and the Sliding Mesh Model; the first two are "steady-state approximations" (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/flu_th/flu_th_sec_mzrrf.html). `grep -i "overset\|MRF\|turbomach\|fan curve"` over `docs/spec` returns nothing.
**Fix:** FLX adds a "Rotating and moving zones" row: rotating-frame source terms in the flow forms (phase 3, laminar; phase 4, RANS), mixing-plane interfaces (phase 5), and sliding interfaces on the octree reusing the electromagnetic sliding interface (phase 4, for GP6). Add `fan(face, curve: Field<VolumeFlow, Pressure>, swirl:)` and `resistance(region, K: Tensor)` as Network-coupled boundary and volume models in phase 3 with GP5. COV adds a "Turbomachinery and fans" row with envelopes (frozen-rotor validity: blade-row interaction `Flag`) and the NASA Rotor 37 or a fan-curve benchmark.

### R20-12 · Major · Targets: FLX, COV
**Section:** FLX "Gradients and optimization", "Fluids and free surfaces"
**Problem:** Flux's adjoints come "from forms", but its production flow path for RANS and conjugate heat transfer is cell-centred finite volume, which is not a weak form. So it is unspecified whether the flow solver GP6 uses has an adjoint at all. STAR-CCM+ and Fluent sell adjoint shape optimization of ducts, manifolds, heat sinks and aerodynamic surfaces. Without a flow adjoint, Crucible's associative optimization (its strongest argument) stops at structures.
**Evidence:** FLX line 457 ("Cell-centred finite volume runs on cut cells and polyhedra") against FLX line 706 ("Flux differentiates the discretized problem from its forms"). Siemens shows STAR-CCM+'s adjoint-derived "surface sensitivity of drag" driving shape changes (https://blogs.sw.siemens.com/simcenter/adjoint-shape-optimization-for-improved-car-aerodynamics/).
**Fix:** Decide in FLX: either express finite volume as a DG(0) weak form in the form language, so the compiler derives its discrete adjoint like any form, or state that RANS ships as stabilized FEM or DG forms with FV only for `Preview`. Add capability rows "Steady flow adjoint (laminar, phase 3; frozen-turbulence and full RANS adjoint, phase 4)" with oracle FLX-O-OPT-4: Taylor order 2 on a duct pressure-drop goal and agreement with a finite-difference sensitivity on a backward-facing step.

### R20-13 · Major · Targets: FLX, ELX, COV
**Section:** FLX "Electromagnetics"; ELX "RF: antennas and matching networks"; COV "Electromagnetics"
**Problem:** Phased arrays, frequency-selective surfaces, metasurfaces and radomes are designed as unit cells with Bloch-periodic (phase-shifted) boundaries and Floquet ports, then as finite arrays by domain decomposition. FLX's ports come only from 2D eigenmode solves, its periodic constraints are structural, and no tab mentions arrays beyond ELX's antenna feature list. GP11's CubeSat antennas, and any 5G or radar customer, would stay in HFSS.
**Evidence:** PADT, an Ansys channel partner, describes HFSS unit cells in which "Master/Slave boundaries are always paired" and a Floquet port that is "always linked to P/S boundaries", plus finite array domain decomposition (third-party, https://www.padtinc.com/blog/efficient-and-accurate-simulation-of-antenna-arrays-in-hfss/). FLX D-FLX-32 lists wave and lumped ports only.
**Fix:** FLX adds to frequency-domain Nédélec FEM: Bloch-periodic boundary pairs with scan-angle phase, Floquet ports with a computed mode set and evanescent-mode attenuation check, and finite-array assembly from a cached unit-cell discretization by domain decomposition (phase 5). Oracles: an infinite dipole array's active reflection against an analytic or published reference, and an FSS transmission curve. ELX adds `array(element, lattice, taper)` returning embedded patterns as `Field<(Ports, Direction, Frequency), Complex<...>>`; COV moves "RF and antennas" general rows to state the periodic rung.

### R20-14 · Major · Targets: ELX, FLX
**Section:** ELX "Power converters and magnetics", "Signal integrity"; FLX "Electromagnetics"
**Problem:** Power-electronics design depends on 3D quasi-static RLC extraction: partial self and mutual inductances, resistance and capacitance of busbars, power modules, connectors, packages and hot loops, frequency-dependent and exported as SPICE subcircuits. ELX says hot-loop inductance comes "from Flux extraction" and lists "quasi-static and full-wave extraction" without a method, port definition, frequency treatment or output type. GP6's ESC and GP12's charger need it.
**Evidence:** Ansys Q3D "extracts resistance, partial inductance and capacitance parasitics from high-power" bus bars, cables and inverter modules and generates "an equivalent SPICE model" (https://ansys.synopsys.com/products/electronics/ansys-q3d-extractor). ELX line 756; COV line 354.
**Fix:** FLX adds `flux::extract_rlcg(bodies, terminals, band)`: magnetoquasistatic A–φ with terminal currents for partial inductance and AC resistance, electrostatic BEM or FEM for capacitance (bempp-rs path), returning `Field<(Ports, Ports, Frequency), Complex<Impedance>>` with error budgets, plus a passive SPICE subcircuit by ELX's vector fitting. Phase 4 with GP6. Oracle: analytic partial inductance of parallel bars and a coaxial line, and a busbar against a published Q3D-class or measured case. ELX's "Losses and parasitics" row cites it.

### R20-15 · Major · Targets: ELX, FLX, ECO
**Section:** ELX "Co-simulation"; FLX "Networks"
**Problem:** Modelica users bring their models as source: the Modelica Standard Library and commercial libraries. ELX accepts Modelica only as compiled FMUs and leaves Rumoca as a phase 5 option. So a Dymola user cannot edit, version, diff or optimize their models in Crucible, cannot use Crucible's adjoints through them, and needs a second tool to build each FMU. Since Crucible's Network compiler already does Pantelides with dummy derivatives, BLT and tearing, the missing piece is a front end, not a solver.
**Evidence:** ELX line 681 ("Modelica arrives through FMUs"). Dymola is built on "an object-oriented language for physical modeling" with multi-domain libraries (https://www.3ds.com/products/catia/dymola). The Modelica Standard Library is v4.1.0 and spans mechanical, electrical, magnetic, thermal, fluid and control components plus state machines (https://github.com/modelica/ModelicaStandardLibrary).
**Fix:** ECO adds a Modelica reader as an `io/` Wasm component (Rumoca or a clean-room parser) that translates a declared subset (equation sections, connectors with flow and stream variables, `inner` and `outer`, records, replaceable classes) into `network { … }` Ingot, phase 4 for GP6. Unsupported constructs stay as an FMU fallback with `Untranslated { construct }`. Oracle: the MSL's `Modelica.Electrical`, `Mechanics.Rotational`, `Mechanics.Translational` and `Thermal.HeatTransfer` examples translate and match MSL reference results within their tolerances. ELX states the translation coverage as a percentage of MSL example models (target: 80% by phase 5).

### R20-16 · Major · Targets: ELX, COV, FLX
**Section:** ELX "Networks in every domain"; COV "Fluids", "Heat transfer"
**Problem:** `Network` declares fluid ports, but no tab ships the element libraries that system engineers use: hydraulic pumps, valves (spool, poppet, check, relief), accumulators, cylinders, pipes with compressibility and cavitation; pneumatics; thermofluid components with real-fluid media (refrigerant loops, coolant circuits, heat exchangers with effectiveness-NTU). GP12's pack coolant loop and every actuation system need them, and Amesim or Modelica.Fluid users would stay put.
**Evidence:** Amesim's libraries address "hydraulic, pneumatic, thermal, electrical, mechanical" domains, with thermal-hydraulic libraries for "heat exchangers, and refrigerant loops" (https://blogs.sw.siemens.com/simcenter/many-physical-domains-and-applications-in-one-system-simulation-tool/). `grep -i "valve\|accumulator\|pneumatic"` over FLX, COV and ELX returns nothing.
**Fix:** ELX adds `std::systems::fluid` element libraries: incompressible and compressible hydraulic elements, pneumatic elements and two-phase thermofluid elements with stream connectors (balanced across and through variables per D-ELX-15, plus enthalpy transport), media from CoolProp. Phase 4 for single-phase coolant and hydraulics (GP6 and GP12 cooling), phase 5 for two-phase and pneumatics. COV adds envelopes (cavitation and choking `Flag`) and a ladder link from 1D pipes to FLX's 3D flow. Oracle: Modelica.Fluid example agreement and analytic water-hammer wave speed.

### R20-17 · Major · Targets: ELX, PLT
**Section:** ELX "Engine choice", D-ELX-25
**Problem:** The round 2 fix for R4-23 (vendor models in ngspice by default) runs ngspice only as an External Op on Linux untrusted-evaluation workers. So an engineer on a laptop simulating a buck converter with the manufacturer's PSpice or LTspice model needs a team server or cloud worker, and an air-gapped user needs a local Linux worker. LTspice and KiCad run the same model locally in seconds, and vendor models dominate real converter and analog work. The native engine accepts a vendor model "only after matching ngspice on its own test bench", with no target for how many will pass when.
**Evidence:** ELX D-ELX-25 and line 927 ("Clients reach them remotely; air-gapped installs need a local Linux worker"). ngspice's home page says "You may apply PSPICE or LTSPICE device model parameters and netlists for simulating discrete circuits" (https://ngspice.sourceforge.io/). Contract 7.8 runs every External Op on untrusted-evaluation workers.
**Fix:** Make dialect compatibility a native-engine capability with a coverage target: ELX's native simulator parses the PSpice and LTspice dialects and behavioural sources and runs every unencrypted vendor model that passes an automatic differential check against the ngspice External Op on first use. The check runs once in CI or on the team server, and the model is then cached as native-qualified. Target: 90% of the vendor corpus (TI, ADI, Infineon, onsemi, ST power and analog models) native-qualified at the phase 3 gate. Laptops then simulate locally; ngspice stays the oracle and the fallback.

### R20-18 · Major · Targets: ELX
**Section:** ELX "The electrical model", "State of the art"
**Problem:** ELX positions code-first capture against atopile, KiCad and Altium only. The products closest to it, and the ones that already add AI agents, are absent: JITX (Python code, AI-written design code, generated pin assignment and routing, HFSS in the loop), tscircuit (MIT-licensed "React for Electronics" with a registry, autorouting and AI footprints) and flux.ai (browser-based, AI copilot, live parts data, built-in collaboration). ELX never states what Crucible offers that they cannot copy quickly: one repository with enclosure, harness and firmware; checks with error budgets and envelopes; deterministic exact DRC; semantic merges with connectivity conflict detection; Approvals over digests; verified agent Proposals.
**Evidence:** JITX: "AI writes the code" and generated "pin assignments" and routing (https://www.jitx.com/). tscircuit: "completely free and MIT-licensed open-source" (https://github.com/tscircuit/tscircuit). flux.ai: "your AI hardware engineer", "connected to live parts data", collaboration "built in" (https://www.flux.ai/).
**Fix:** Add these three to ELX's State of the art rows "Connectivity capture" and "Automatic placement" as implementations to beat, and add one paragraph under D-ELX-1 naming the five differences above with the oracle that proves each (ELX-O-NET-2, ELX-O-LAY-1, ELX-O-BRD-2, ELX-O-SYS-3). Add a measured target: "an agent completes GP5's board from requirements to DRC-clean Proposal with fewer human corrections than a recorded JITX or flux.ai session on the same brief" (phase 3).

### R20-19 · Major · Targets: FLX, COV
**Section:** FLX "Surrogates"; COV "Surrogates and learned models"
**Problem:** Geometry-agnostic AI surrogates are the fastest-moving competitor in simulation, and FLX ships surrogates only in phase 4 without naming them or stating the difference. Ansys SimAI predicts 3D fields from unparametrized geometry and returns a "confidence level"; Luminary sells "Large Physics Models" with "<2% prediction error". Crucible's real difference is that a surrogate prediction can never decide a `SignOff` check without a bound in the check's norm or a confirming solve, and that weights are pinned and labelled. Neither tab says so against these products, and phase 4 leaves three phases with no learned acceleration.
**Evidence:** SimAI "always returns a result", and each prediction carries "a confidence level indicating whether it can be trusted" (https://ansys.synopsys.com/products/simai). Luminary claims ">1K faster than simulation" (https://luminary.ai/). FLX D-FLX-14, phase 4 rows FLX-O-ROM-2.
**Fix:** Add SimAI, Luminary and PhysicsNeMo-based tools to FLX's surrogate State of the art row, with the measurement "no false `SignOff` `Pass` in 10⁴ adversarial evaluations, where their confidence indicators are measured on the same held-out set". Move `Preview`-only geometry surrogates (trained on Crucible's own cached `Interactive` results per design repository) to phase 2, since they never decide checks and Kiln's cache already holds the training data; keep `Interactive` and per-prediction bounds in phase 4.

### R20-20 · Major · Targets: COV
**Section:** COV "Coverage matrix", "Out of reach", "Out of scope"
**Problem:** Several physics families that COMSOL sells as standard modules have neither a matrix row nor a limit record, which breaks D-COV-1's promise that "every gap has a name": charged-particle tracing in electric and magnetic fields (electron guns, ion optics, mass spectrometers, sputtering), particle tracing in flows (aerosols, sedimentation), deterministic free-molecular flow by the angular coefficient method (vacuum chambers, semiconductor tools), and rotating-mixer flow (R20-11).
**Evidence:** COMSOL's Particle Tracing Module covers ions and electrons "essential to the design of spectrometers, electron guns, and particle accelerators" (https://www.comsol.com/particle-tracing-module). Its Molecular Flow Module uses the angular coefficient method with "a deterministic approach that is completely free of this statistical noise" (https://www.comsol.com/molecular-flow-module). COV's rarefied-gas row offers only free-molecular formulas and DSMC.
**Fix:** Add rows: "Charged-particle tracing (µ Me P)", with Lorentz-force trajectories on FLX's `bvh_query` and fields from electrostatic and magnetostatic solves and space-charge iteration, phase 5; "Particle tracing in flows", Lagrangian one-way on the flow Field, phase 5 (merge with the dispersed-multiphase row's one-way rung); "Free-molecular flow, angular coefficient", radiosity-like on FLX's view-factor machinery, phase 5. Each row gets an envelope and a benchmark (Child–Langmuir diode; Clausing factor of a tube).

### R20-21 · Major · Targets: FLX, UIX
**Section:** FLX "Per-region models" (D-FLX-26), "Meshing and adaptivity"
**Problem:** Incumbent users run submodeling: a coarse global model (often shells and beams) drives cut-boundary conditions on a refined local solid. Crucible makes routine submodeling unnecessary through goal-oriented hp-adaptivity, and D-FLX-26 already re-solves a 3D patch from a reduced model. But the tabs neither state the replacement nor expose the patch to users for the cases where it is still the workflow: a shell-modelled frame with a solid weld detail, or a supplier's global loads applied to a local part.
**Evidence:** Ansys Mechanical's submodeling "takes the results of a broader upstream analysis and applies them as boundary conditions to a smaller downstream model" (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_submodeling.html). FLX D-FLX-26 builds that patch internally for error estimation only.
**Fix:** Add one sentence to FLX "Meshing and adaptivity": "Goal-oriented adaptivity refines where a check needs accuracy, so routine submodeling is unnecessary." Add `std::sim::submodel(global: Field, region:, model:)` reusing D-FLX-26's patch with the transfer error in the budget, phase 2, and a UIX study template for it.

### R20-22 · Minor · Targets: ELX
**Section:** ELX "Firmware-in-the-loop" (D-ELX-18), "Platform notes"
**Problem:** ELX says Renode "publishes Linux, Apple-silicon macOS and Windows packages but no ARM64 Linux package", so ARM64 server classes send firmware runs to x86-64 workers. This is out of date: Renode 1.17.0 ships a Linux ARM64 portable package.
**Evidence:** Renode's releases page lists `renode-1.17.0.linux-arm64-portable.tar.gz` (https://github.com/renode/renode/releases).
**Fix:** Replace the sentence with "Renode publishes Linux x86-64 and ARM64, Apple-silicon macOS and Windows packages (1.17.0), so firmware runs on both server architectures; ELX-O-FW-1 runs on each." Delete the x86-64 routing rule from "Platform notes".

### R20-23 · Minor · Targets: ELX, ECO
**Section:** ELX "Creating and migrating catalog parts"; ECO D-ECO-31, "Migration from incumbent tools"
**Problem:** Both tabs route proprietary ECAD through "KiCad 9's importers" (Altium, CADSTAR, EasyEDA, P-CAD, Fabmaster). KiCad 10 adds direct importers for Allegro and PADS, the two Cadence and Siemens formats whose users most need a migration path, plus gEDA and Lepton.
**Evidence:** "KiCad 10 can now import designs from Allegro, PADS, and gEDA / Lepton PCB" (https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/).
**Fix:** Pin KiCad 10 in the migration container. Name Allegro and PADS in ELX's step 2 and in D-ECO-31, and add an Allegro and a PADS design to ECO-O-25's corpus (netlist equality, empty Gerber XOR).

### R20-24 · Minor · Targets: ELX, MEC
**Section:** ELX "Hierarchy, buses and ports", "Wire harnesses"
**Problem:** Altium sells multi-board design: a system schematic of board modules, board-to-board connectivity checks and a multi-board assembly in an enclosure with collision checks. Crucible does more by construction, with one Network across boards, harnesses and enclosure. But ELX never says so, and it has no check for directly mated board-to-board connectors (pin 1 to pin 1 mirrored across a mezzanine), the commonest multi-board error.
**Evidence:** Altium's multi-board ERC "will detect net-to-pin assignment errors and pin-to-pin interconnection wiring errors", and its assembly checks collisions (https://altium.com/documentation/altium-designer/multi-board-design).
**Fix:** Add `mate(connector_a, connector_b)` to ELX, deriving pin correspondence from the catalog parts' mating facet and the Assembly placement. Rule `mated_pinout` fails on mirrored or role-incompatible pairs (phase 3, ELX-O-NET-2). Add one sentence under D-ELX-7 stating that multi-board systems are one Network and one Assembly with no system-level sync step.

### R20-25 · Minor · Targets: ELX
**Section:** ELX "Power converters and magnetics", "Analyses and results"
**Problem:** Converter and drive designers simulate control loops over thousands of switching periods with ideal-switch, piecewise-linear simulators (PLECS, SIMPLIS), whose events cost two linear solves each. ELX offers averaged models and full device-level BDF transients, so a closed-loop inverter run is either too coarse or orders of magnitude slower.
**Evidence:** PLECS reduces "power semiconductors to ideal switches being either fully on or off", so a switching event "requires just two steps" (https://www.plexim.com/products/plecs).
**Fix:** Add a phase 4 analysis `switched_transient(network)`: ideal-switch elements with loss lookup tables, per-topology state matrices cached by Flux's per-mode compilation (D-FLX-27), and exact event location. Its temporal error follows FLX's rule. Oracle: buck and three-phase inverter waveforms against device-level transients within the loss tables' tolerance, at 50 times the speed (target).

### R20-26 · Minor · Targets: UIX, FLX
**Section:** UIX "Studies and results"; FLX "Scope and architecture"
**Problem:** COMSOL's Application Builder turns an expert's model into "a simulation application with a dedicated user interface" for non-experts, and companies buy it for that. In Crucible, any study wrapped as a `#[feature]` already generates its dialog, docs and agent tool schema and stays checked and versioned, which is a stronger form of the same thing. No tab says so.
**Evidence:** https://www.comsol.com/comsol-multiphysics; contract section 5 `Feature` ("metadata that generates its dialog, docs and agent tool schema").
**Fix:** Add one paragraph to UIX "Studies and results" stating that a study published as a feature is a simulation app, with locked inputs, typed ranges and checks. Add an example in which a sizing feature wraps `static_stress` for a sales engineer.

### R20-27 · Minor · Targets: FLX, UIX
**Section:** FLX "Post-processing and display" (`std::sim::report`)
**Problem:** `std::sim::report` builds report data, but no tab renders it as a document an analyst can send or archive (PDF/A, HTML, DOCX). Ansys Mechanical and COMSOL generate reports, and certification and customer reviews consume documents.
**Evidence:** FLX line 840; no report-document writer in ECO's catalog for simulation reports.
**Fix:** Name the output: report data renders through MEC's drawing and document pipeline to PDF/A-2u and HTML, with figures from Snapshots under a pinned `RenderProfile`, phase 2. Oracle: re-rendering a stored report is byte-identical.

### R20-28 · Minor · Targets: FLX
**Section:** FLX "Electromagnetics", Oracles FLX-O-DISC-8
**Problem:** HFSS users judge an EM solver by its adaptive convergence on S-parameters (a maximum ΔS between passes). FLX's electromagnetic oracle checks accuracy at fixed cases but states no adaptive stopping rule or goal, so an S-parameter's error budget is undefined at `SignOff`.
**Evidence:** FLX D-FLX-32 and FLX-O-DISC-8 ("S-parameters within 0.01 of Palace").
**Fix:** State that each port's S-parameters at declared frequencies are DWR goals of `solve_harmonic`, with a calibrated class `em.sparam` (phase 4), and that adaptivity stops when every goal's bound is below the requested |ΔS|. Extend FLX-O-DISC-8 with coverage of held-out cases at 99%.

### R20-29 · Minor · Targets: ELX
**Section:** ELX "Signal integrity", "State of the art"
**Problem:** High-speed designers run standard compliance kits: JEDEC DDR4 and DDR5 eye masks and timing budgets, PCIe and USB channel compliance. ELX names only IEEE 802.3ck's COM tool.
**Evidence:** ELX line 907.
**Fix:** Add `std::electronics::compliance` packages per standard edition (licensed data under D-ELX-30), each a set of checks over ELX's channel results, phase 4. Oracle: published compliance examples reproduced.

### R20-30 · Minor · Targets: FLX, ELX
**Section:** FLX "Networks"; ELX "Co-simulation"
**Problem:** Modelica users wait on model translation for large systems, and Crucible's per-mode compilation cached by Kiln could recompile only the changed part. FLX gives only a run-time target ("2× of IDA") and no compile-time target, so the advantage over Dymola is neither stated nor measured.
**Evidence:** FLX line 876.
**Fix:** Add a target row: "re-translation after a one-parameter or one-element edit of a 50,000-equation Network under 1 s (incremental), full translation within 2× of OpenModelica", with FLX-O-NET-1 measuring it. State the incremental compile in one sentence under D-FLX-27.

### R20-31 · Minor · Targets: ELX
**Section:** ELX "The drawn schematic" (D-ELX-27)
**Problem:** Several engineers editing one board at once is a premium incumbent feature (Altium's shared workspaces, Allegro's concurrent team design). Crucible gives row-level merges, live documents and connectivity-conflict detection to every user, but ELX states this only as a storage decision.
**Evidence:** ELX D-ELX-27 and the contract's connectivity merge condition (7.1 `repo`).
**Fix:** Add one sentence after D-ELX-27: "Two designers routing different regions of one board work on branches or live in one document, merge row by row, and see a `Conflict::NetMerge` instead of a silent short."

### R20-32 · Minor · Targets: FLX, MEC
**Section:** FLX "Shape, parameter and experimental design"
**Problem:** Structural optimizers in OptiStruct and Nastran SOL 200 size shell thicknesses (free-size) and optimize composite ply shapes, counts and stacking under manufacturing rules. Flux offers density topology optimization and shape optimization, but no shell-thickness or ply optimization, which GP10's wing box will need.
**Evidence:** FLX "Topology optimization" table, with density, graded lattice, level set and multiphysics rows only.
**Fix:** Add "Shell sizing and laminate optimization" rows: thickness Fields on mid-surface shells with adjoints (phase 2), and ply-shape, ply-drop and stacking optimization with MEC's ply rules (phase 6, GP10).

### R20-33 · Minor · Targets: UIX, FLX
**Section:** UIX "Field views"
**Problem:** Analysts trust a solve partly by inspecting its discretization. Without a mesh, they will ask where the octree refined, which cells are cut and aggregated, and where shells and beams replaced solids. UIX shows an error overlay but no discretization view.
**Evidence:** UIX "Field views" capability table has no row for the discretization; FLX's `mark_reduction` produces a `Field<Body, ReductionKind>` that is never displayed.
**Fix:** Add a "Discretization" `VisualizationSpec` showing octree cells, cut and aggregated cells, polynomial degree and `ReductionKind` regions, phase 1. A one-line legend states that the model was not meshed by the user.

## Appendix: parity checklist

The checklist below drove the findings. "Covered" means a capability row with a phase exists; the phase is the earliest at which the incumbent workflow works.

| Incumbent capability (source) | Crucible | Phase | Finding |
| --- | --- | --- | --- |
| Linear static, modal, linear buckling of a part (Ansys, Abaqus, Nastran) | Covered (FLX, contract 13.4) | 1 | — |
| Remote points, point masses, springs, bushings, fastener connectors (Ansys, Nastran) | Missing | — | R20-01 |
| 2D, axisymmetric, symmetry, cyclic symmetry (Abaqus, Ansys, COMSOL) | Missing | — | R20-02 |
| Prestressed modal, harmonic, PSD, response spectrum, damping (Ansys, Nastran) | Partial, no owner | 2 to 7 | R20-03 |
| Assembly with bonded and frictionless contact, automatic detection (Abaqus, Ansys) | Fitted only | 2 (fitted), 3 (immersed) | R20-08 |
| Nonlinear materials, large deformation, frictional contact (Abaqus) | Covered | 2 | — |
| Load-case combination and envelopes (Nastran, Ansys) | Missing | — | R20-09 |
| Stress linearization (Ansys) | Missing | — | R20-10 |
| Submodeling (Ansys) | Internal only | — | R20-21 |
| Solver-deck exchange that runs (Nastran, Abaqus, LS-DYNA) | Read and write without execution | 3 | R20-06 |
| Topology and lattice optimization (Ansys, nTop) | Covered; stronger | 1 | — |
| Fatigue, gear and bearing ratings (nCode, KISSsoft) | Covered | 1 to 2 | — |
| Explicit drop and crash (LS-DYNA) | Covered | 3, 5 | — |
| Laminar and natural-convection CFD, conjugate heat transfer (Fluent) | Covered | 3 | — |
| RANS, LES, multiphase (Fluent, STAR-CCM+) | Covered | 4, 5 | — |
| Rotating frames, mixing plane, sliding mesh, fan models (Fluent) | Missing | — | R20-11 |
| Flow adjoint (STAR-CCM+, Fluent) | Unspecified | — | R20-12 |
| GPU CFD throughput (Fluent) | No target | — | R20-07 |
| Full-wave FEM with wave ports and fast sweep (HFSS) | Covered | 4 | — |
| Floquet ports and array domain decomposition (HFSS) | Missing | — | R20-13 |
| 3D partial-inductance RLC extraction (Q3D) | Unspecified | — | R20-14 |
| Weak-form equation modelling (COMSOL) | Covered; typed and differentiable | 0 to 1 | R20-05 |
| Simulation apps (COMSOL Application Builder) | Covered by features; unstated | 1 | R20-26 |
| Charged-particle tracing, molecular flow (COMSOL) | Missing, no limit record | — | R20-20 |
| AI field surrogates (SimAI, Luminary) | Bounded; late | 4 | R20-19 |
| Acausal multi-domain system models (Dymola) | Covered as `Network` | 2 | — |
| Modelica source and MSL (Dymola) | FMU only | 3 (FMU) | R20-15 |
| Hydraulic, pneumatic, thermofluid libraries (Amesim) | Missing | — | R20-16 |
| Schematic, ERC, layout, DRC, routing (Altium, KiCad) | Covered | 3 | — |
| Multi-board systems (Altium) | Covered by construction; unstated | 3 | R20-24 |
| Vendor SPICE models locally (LTspice, PSpice) | Remote External Op only | 3 | R20-17 |
| Ideal-switch converter simulation (PLECS) | Missing | — | R20-25 |
| Allegro and PADS migration (KiCad 10) | Not named | 3 | R20-23 |
| Code-first and AI PCB design (JITX, tscircuit, flux.ai) | Covered; differences unstated | 3 | R20-18 |
