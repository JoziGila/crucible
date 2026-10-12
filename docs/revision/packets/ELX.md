# ELX round 4 packet

Your tab is `docs/spec/08-electronics-systems.md` at v3 (tag `round-3`). Round 4 fixes, in one pass: the 35 third-review findings that target it (0 Critical, 20 Major, 15 Minor), its 0 `[unverified]` claims, its open questions and the known items below. Contract v7 is binding; its section 18 lists the rulings on this review, and many findings below are already settled there.

## Third-review findings

### R13-04 · Major · Targets: CONTRACT, COV, FLX, MFG, ELX
**Section:** Contract 13.4 (prerequisite rule, "the spec check enforces this across tabs"); COV coverage matrix rows; FLX "Eigenvalue problems", "Krylov methods and preconditioners"
**Problem:** Contract 13.4 says nothing is phased before its prerequisites and that the spec check enforces this. The checker has no such rule, and rows outside 13.4 break it: (a) COV rotordynamics is phase 2 (Campbell diagrams, rotating-frame FEM), but the gyroscopic and damped eigenproblems arrive in FLX phase 3 ("Damping and flutter linearizations follow in phase 3"). (b) COV linear acoustics FEM with PML is phase 3, but FLX's indefinite Helmholtz solvers (complex LDLᵀ, shifted-Laplacian multigrid) are phase 4. (c) COV's signal and power integrity row is phase 3 with full-wave extraction, but FLX full-wave FEM is phase 4 and ELX's own post-layout extraction is phase 4. (d) COV's welding row puts the phase 4 transient model "with phase transformation", while JMAK and Koistinen–Marburger arrive in phase 6 (heat treatment, ICME). (e) R13-07: allowables in phase 3 against phase 1 strut basis values.
**Evidence:** `docs/tools/check.py` only checks that each capability row has a phase (line 298, "has no phase"); it never compares phases across tabs or against 13.4. FLX's linear-algebra table lists "Indefinite Maxwell and Helmholtz | Complex LDLᵀ; optimized Schwarz; shifted-Laplacian multigrid | 4".
**Fix:** Add a "Requires" field to every capability row that names another tab's capability, and have `check.py` compare phases. Contract 13.4 can stay a table without a Needs column, because the field lives in the tabs. Add 13.4 rows: structural frequency response and damped or gyroscopic eigenproblems at phase 2 (owner FLX; also COV and MEC), and Helmholtz FEM solvers at phase 3 (owner FLX; also COV and ELX). Drop "with phase transformation" from COV's phase 4 weld row, or move JMAK and Koistinen–Marburger to phase 4. Make COV's signal and power integrity row "3 quasi-static, 4 full-wave".

### R13-10 · Major · Targets: CONTRACT, FLX, COV, ELX
**Section:** Contract 5 `ErrorBound` kinds; contract 7.1 ("Every `Estimated` bound is reported already multiplied by its calibrated factor … outside it reports `Indicator`"); FLX budget table; D-FLX-35; ELX "Analyses and results"; D-COV-17
**Problem:** Contract 7.1 and D-COV-17 make every `Estimated` bound a calibrated class member, and anything outside a class is `Indicator`. Yet several `Estimated` bounds have no class. These are FLX's cut-cell energy bounds ("`Estimated` (open question 1)"), D-FLX-35's worst-case remainder, ELX's "Algebraic error is `Estimated` from residuals", COV's V&V 20 model-form part, and confidence intervals from sampling. Read literally, all of them are `Indicator` and can never decide. Read loosely, some uncalibrated estimates decide `SignOff`. The mechanism mixes two different guarantees: empirical calibration against a corpus, and a statistical interval with a stated α.
**Evidence:** The quoted contract sentence, against "Algebraic error is `Estimated` from residuals" (ELX) and "The result is `Estimated`" (D-FLX-35), neither naming a class.
**Fix:** Make the calibration field one enum in contract 5: `Class { id, α }` (η99 tables) or `Statistical { method, α }` (confidence intervals, V&V 20, conformal, probabilistic Lanczos bounds). Then state: an `Estimated` bound without either is `Indicator`. List every current `Estimated` source in FLX's table with its variant, and have ELX name the class or method for circuit algebraic parts.

### R13-18 · Major · Targets: FLX, COV, ELX
**Section:** COV "Aerospace" (low-speed aerodynamics and rotors, phase 4, benchmark "GP6 rotor thrust and torque"); FLX (no rotor or rotating-domain capability)
**Problem:** GP6's gate validates rotor thrust and torque, but no tab owns a rotor-aerodynamics method. COV names vortex particle methods and RANS or DDES. FLX lists no vortex-particle method, no rotating reference frame, and no sliding or overset mesh for flow; its sliding interface serves magnetics only. Blade-element momentum theory (the L1 rung) has no package owner either. A drone engineer would reach for a separate tool on day one.
**Evidence:** In FLX and ELX a search finds no "rotor", "vortex", "blade-element" or "rotating frame". The only sliding interface is FLX's: "Motion uses a sliding interface on a cylindrical air gap or mortar coupling, for ELX's loss maps".
**Fix:** Add three phase 4 rows to 13.4, all owned by FLX with COV and ELX also phasing them:
- blade-element momentum with tip losses as an Ingot package (L1);
- a vortex particle method on `fmm_apply` as a std Wasm component (D-COV-11's route), with regularized particles and a stated core size;
- rotating-domain flow by a moving reference frame and a sliding interface reusing the magnetics machinery, with an oracle against published propeller data.

### R13-30 · Minor · Targets: ELX, FLX
**Section:** ELX "Power integrity"; FLX "Electromagnetics" (layered sheets)
**Problem:** ELX solves the PDN by "Flux's layered sheets solving the Helmholtz equation per plane pair", but FLX defines layered sheets as "thin-sheet conduction coupled through-plane by `dI` conductances", which is a diffusion form. A plane-pair cavity Helmholtz model with complex wave numbers and ports is a different form and needs the indefinite solvers of R13-04.
**Evidence:** ELX: "PDN impedance comes from Flux's layered sheets solving the Helmholtz equation per plane pair". FLX capability row: "Layered sheets | Thin-sheet conduction with through-plane `dI` | … | 3".
**Fix:** Add a "plane-pair cavity model" row to FLX in phase 4 (2D Helmholtz on sheet Bodies with port and via elements, complex LDLᵀ) and point ELX at it.

### R16-04 · Major · Targets: CONTRACT, ELX, MFG, AGT
**Section:** Contract 7.6 "Firmware" and "Approval credentials"; ELX D-ELX-29; MFG "Printers, 3MF and print transfer" and "Approval, transfer and physical safety"
**Problem:** Each `flash_device` needs an Approval of one image digest and target, each `send_print_job` its own, and each `Prototype` program push its own, every one with AAL3 WebAuthn on the approval page. Embedded developers flash dozens of times an hour, makers iterate prints, and machinists re-send a program several times during prove-out. They will flash with their own probe tools and print from the slicer instead. The record that D-ELX-29 exists to keep is then never written. `standing_release` already solves the same problem for data transfers, but nothing covers physical effects.
**Evidence:** D-ELX-29: "Every client flashes a board only through the transfer Act `flash_device`". Contract 7.6: "Its Approval covers the image digest and the target". `standing_release` covers only "recipients, channel, schema, label ceiling and expiry".
**Fix:** Add one restricted Act, `bench_session`. It takes one AAL3 Approval over {the named person at the device, device serial (board, printer or machine), probe or gateway, payload kind, Software item or program Item lineage (one branch), maximum count, expiry of at most 8 h, hazard acknowledgements from the Network or machine package}. Transfers inside the session need no further Approval, but each keeps every check: read-back, hold in reset, no start, the gateway's offset check and the canonical hash. The session ends early on expiry, on a hazard change in the Network, or on a payload outside the lineage. Agents cannot open or extend one. The approval page lists every transfer in the session afterwards. Phase it with each underlying Act, with oracles AGT-O-new and ELX-O-FW-3 for count, lineage and expiry bounds.

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

### R16-21 · Minor · Targets: MEC, KLN, ELX
**Section:** MEC "Design checks" (`decides_on` table: mass); MEC "Standard parts and fasteners"; ELX "Electrical facets"
**Problem:** Mass checks need `Guaranteed` bounds, and mass properties come from geometry and `Material` density. Purchased parts arrive as simplified or hollow STEP bodies: a motor, a battery, a populated board. Their computed mass and centre of gravity are therefore wrong by large factors, yet they carry certified-looking bounds. No record lets a datasheet mass override the computed one.
**Evidence:** MEC: "Fits, clearance, interference, thickness, mass | `Guaranteed`". ELX's catalog facets list a "3D body" and "Specifications" but no mass. MEC hands Flux "mass properties with their bounds" (D-MEC-12).
**Fix:** Add `part.mass_properties(declared: { mass: Tol<Mass>, cg: Tol<Point>, inertia: Option<…> }, source: Datasheet | Measured(Evidence))`. It replaces computed values in roll-ups, and reports label it "declared". Catalog parts carry a mass facet. A `Warning` check flags purchased Instances whose computed mass is used without a declaration.

### R16-24 · Minor · Targets: ELX
**Section:** ELX "The drawn schematic" (editor behaviour 2 and 3)
**Problem:** A connection made only in code renders dashed until a human draws it, and `schematic_matches_network` blocks release. Every connectivity edit by an agent or the code editor therefore leaves manual drawing work before release. Agents cannot fix this, because the fix is a drawing gesture.
**Evidence:** "A connection made only in code renders dashed until one gesture draws it or places a label." "`schematic_matches_network` blocks release."
**Fix:** Add `schematic.autodraw(nets)`, a deterministic Wasm component. It proposes segment or label rows for code-only connections, using net labels when a wire would cross more than a stated number of symbols, and ordering work by canonical numbers. It opens a Proposal that a person reviews. Phase 3, with ELX-O-SCH-1.

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

### R17-15 · Major · Targets: CONTRACT, AGT, ELX, UIX
**Section:** Contract 7.6 "Firmware"; AGT D-AGT-31 (Firmware)
**Problem:** "Client flashing through `apps/platform` or WebUSB is the same Act", but a server Approval cannot bind what a client writes to a USB probe. WebUSB permission belongs to the web app's main origin, which R11-05 already treats as script-injectable, so injected script with a remembered device grant can flash any image with no Act at all. In the browser, the read-back check is performed by the same compromised code. The machine gateway verifies Approvals in its own core (D-MFG-24); client flashing has no equivalent.
**Evidence:** Contract 7.6: "Client flashing through `apps/platform` or WebUSB is the same Act." No tab says which component checks the Approval signature and image digest before bytes reach the probe.
**Fix:** Contract 7.6: "Client flashing runs only in code that verifies the Approval: in browsers, on the approval origin page after the ceremony, which holds the WebUSB grant and checks the image's SHA-256 against the approved plan; on desktops, in `apps/platform`'s flashing service, which verifies the Approval signature against the pinned approver directory as the machine gateway does. The main web origin never holds a WebUSB grant." AGT-O-21 adds a main-origin flashing attempt.

### R18-12 · Major · Targets: CONTRACT, COV, MFG, ELX, PLT
**Section:** Contract 12 crate map; COV "Materials system"; PLT D-PLT-36
**Problem:** Several Rust types and components have no buildable home in contract 12. COV's `Material` holds `PropertyField`s (`Field`s), so it cannot live in `base`, which sits below `field`, yet no COV crate exists and `mech-model` and Flux both need it. MFG, ELX and COV name no crates at all, so their Rust code (cost models, DfAM check operations, the MNA engine, envelope evaluation) has no layer. The browser's first-party Wasm component runtime (D-PLT-36) calls `WebAssembly.instantiate` through `web-sys`, which `check-layers` bans outside `apps/`, yet `kernels` must run user-form modules through it.
**Evidence:** COV: `pub struct Material { … pub properties: BTreeMap<PropertyId, Property>, … }` with `value: PropertyField, // e.g. Field<(Temperature, StrainRate), Stress>`. Contract 12 lists crates for PLT, KLN, FLX, ANV, MEC, ING and AGT only. PLT bans `web-sys` outside `apps/`.
**Fix:** Contract 12 adds `material` (COV) to the Engine core row after `field`, holding `Material`, `ConstitutiveBinding` and envelope data types. It adds one sentence: "COV, MFG and ELX ship Rust only as operations inside `flux-*` crates (owned with FLX), as std Wasm components under `std/`, or as `apps/` services; they own no core crate." The browser Wasm runtime is `apps/platform`'s implementation of `wasm-host`'s `WasmComponentEngine` trait, injected at startup like `Storage`; `wasm-host` keeps the determinizer and the Wasmtime implementation behind `cfg(not(target_arch = "wasm32"))`, and `check-layers` allows `target_arch` there.

### R20-04 · Major · Targets: COV, ELX, OVERVIEW
**Section:** COV "Coverage matrix"; ELX "Phasing"; Overview roadmap
**Problem:** No tab tells an engineer when Crucible matches the tool they use today. The coverage matrix lists methods by domain and phase, but nothing maps an incumbent workflow tier (linear static and modal of an assembly; nonlinear contact; harmonic and random; laminar CFD; turbulent CFD; schematic plus two-layer board; high-speed board) to the phase where every capability it needs exists. Reviewers and buyers cannot judge the bar "nothing they rely on missing", and gaps such as R20-01 and R20-02 stay invisible because no row lists the workflow.
**Evidence:** COV's matrix and FLX's phasing list capabilities, not workflows; ELX phase 1 and 2 give no board capability (ELX "Phasing"). The present review found its first two Critical gaps only by building such a checklist from Ansys, Abaqus and Nastran documents.
**Fix:** Add to COV a "Parity map" table, one row per workflow tier: workflow · capabilities it needs (by FLX, COV, ELX row) · incumbent reference (Ansys Mechanical, Abaqus/Standard, Fluent, HFSS, Altium Designer, Dymola) · phase at which all rows exist · Crucible's difference. The spec check fails if any listed capability lacks a row or carries a later phase than the tier. ELX adds the board tiers; the Overview cites the table in one line.

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

### R21-02 · Major · Targets: ING, FLX, COV, KLN, MFG, ELX, AGT, UIX, PLT, MEC, ANV, ECO, CONTRACT
**Section:** Every design section's decisions; "Open questions"; "Contract change requests"; contract lead
**Problem:** The tabs read as the minutes of their own revision. Review finding ids appear as evidence inside running prose, decisions end in "(revised in round N)", "Rejected" clauses name "the round 2 rule", and "Open questions" sections list declined findings rather than open questions. A reader who was not in the review cannot use any of it, and the Adversarial review tab already owns this history.
**Evidence:** Counted before each tab's "Open questions": finding ids such as "(R3-37, R9-40)" appear 112 times in PLT, 62 in FLX, 56 in MFG and AGT, 48 in ELX, 45 in UIX, 43 in KLN, 34 in COV and 26 in ING (482 in all), while ANV, MEC and ECO show that a tab reads well without any. "(revised in round N)" appears 235 times across twelve tabs. Examples: D-ING-7 "*Rejected:* … `Pending` and `ING6401` as node values, the round 2 rule. (revised in round 3)"; D-MEC-26 "*Why:* … the round 1 drafts claimed the formboard twice"; D-FLX-1 "*Rejected:* the round 1 seven-crate split"; MEC "It replaces `crucible:model`"; KLN "`crucible:product`, formerly `crucible:model`". ING's "Open questions" opens "This revision decides all nine round 2 questions" and then lists ten bullets of declined findings; MEC's question 2 and AGT's question 2 are titled "Findings declined…". The contract's lead is a version history.
**Fix:** One mechanical pass, then a rule. (1) Delete every finding id from text above "Open questions"; where the id stood in for a reason, write the reason ("a policy-clamped limit made two organizations cache different results for one key" stays, "(R3-12)" goes). (2) Delete every "(revised in round N)"; the Decisions log and `git log` keep revision history. (3) Delete "the round N rule", "formerly", "replaces" and similar history from decisions and names; a rejected alternative is described by what it is. (4) "Open questions" holds only unresolved questions; move every "Findings declined or applied in part" list to the Adversarial review tab under that tab's code. (5) "Contract change requests" holds only open requests or "None"; accepted ones are recorded in the contract's ruling log. (6) The contract's lead is one sentence: "Binding for every design agent and reviewer; where a tab disagrees with it, the contract wins." Add to `check.py` a rule that fails on `\bR\d{1,2}-\d{2}\b`, "revised in round" and "round \d" outside the Adversarial review and Decisions log tabs.

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

### R21-25 · Minor · Targets: MEC, KLN, ELX
**Section:** MEC "Interference and clearance" and Interfaces; KLN "Scope and the operation contract"
**Problem:** Some references point at an item number in another place's list, so the reader must open that list to learn what is meant, and the reference breaks if the list is reordered.
**Evidence:** MEC: "KLN's merge condition 4 reuses these classes"; MEC Interfaces: "merge conditions 4 and 5"; KLN's `OpCx` comment: "keyed by rule 2 under Keys"; KLN: "`OpKey(ObjectId)` // contract 7.2, items 1 to 6".
**Fix:** Name the rule: "KLN's no-new-interference merge condition"; "the interference and connectivity merge conditions"; "keyed as Kiln's random-stream rule says"; "the six `OpKey` inputs of contract 7.2".

### R21-26 · Minor · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, CONTRACT
**Section:** Capability tables at the end of each design section
**Problem:** Capability tables are the build contract, but in reading order they arrive as a dense block after every section, and many cells add nothing: "Failure: —" and "Not expressible" stand where the reader expects a typed failure. The published doc gives them the same weight as explanation.
**Evidence:** ING "Purity | … | Not expressible"; MEC "Typed failures and fixes | `FeatureError { kind, why, fix, at }` | —"; AGT "Priority classes | … | — ".
**Fix:** Replace "—" with "None: cannot fail" or the actual failure, and "Not expressible" with "None: the language cannot express a violation". In the published doc, render capability tables as a visually distinct, collapsible "Build contract" block under each section, so a reader can follow the prose without the tables breaking it.

## Claims the reviewers verified

Drop the `[unverified]` marker on these and cite the URL in Sources.

None in this review.

## Unverified claims in your tab

Verify each with WebFetch on a primary source and drop the marker, correct it, or cut the claim if nothing supports it. Line numbers are at tag `round-3`.

None.

## Your open questions

Close each: decide it (the reviewers propose answers above), move it to a contract change request, or keep it with the reason it cannot be decided yet.

1. **Verilog-A front end.** The phase 1 research track decides whether a clean-room front end fits phase 3; the fallback is ported SPICE3 models with ngspice vendor models. Only the track's prototype can measure that scope.
2. **GPU back ends (R1-39, declined in part).** CUDA and ROCm wait for the phase 4 gate decision in contract section 7.5. Vulkan `SHADER_F64` server classes serve until then.
3. **R10-45, applied in part.** Layouts stay text as it asks, but a region split replaces its binary-sidecar fallback, following R9-34 (D-ELX-27).

## Known items

- Read `docs/revision/digest.md`: adopt the permissive libraries that serve your tab, name copyleft tools only as oracles, and use the clean-room insight protocol of contract 7.7 for incumbent behaviour.
- Add one sentence under each drawn diagram that tells the reader how to read it (`diagrams/08-electronics-source-model.jsx`, `diagrams/08-electronics-analysis-dataflow.jsx`).
