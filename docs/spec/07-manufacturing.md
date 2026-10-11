# Manufacturing (MFG)

The manufacturing libraries turn a released design into parts and products through one typed, deterministic plan. Intent is Ingot (`std::mfg`), heavy planning runs in Wasm components, geometry in Anvil operations and process physics in Flux forms. Every toolpath, nest, mold, routing, cost and passport is an oracle-verified function of the design, and people approve every program before it reaches a machine.

## Scope and ownership

| Area | MFG owns | Others own |
| --- | --- | --- |
| Process planning | Setups, workingsteps, toolpaths, nests, builds, routings, post-processors | None |
| Geometry kernels | Requirements and oracles for the operations listed below | Anvil implements them |
| Process physics | Process setups, boundary conditions, process data, interpretation, Checks | Flux (forms, solvers); COV (models, validity envelopes) |
| Design intent | DFM, DFA and DfAM Checks that read design Queries | MEC (sheet metal, weld joints, GD&T, bolted joints); ELX (board design) |
| Product structure | Manufacturing views, routings, as-built records | `repo` (EBOM, MBOM, SBOM views, releases, change orders) |
| Connectivity | Machine, printer, CMM and factory protocol mappings | PLT (serial, sockets, certificates); `api` (actions, permissions) |

## Architecture of the manufacturing libraries

### Layering

**Decision D-MFG-1:** Every manufacturing capability is split along the contract's layers. Intent is Ingot, heavy search is a Wasm component, shared geometry is an Anvil operation and physics is a Flux form. *Why:* shops edit intent, while algorithms need sandboxed native speed, and the same kernels serve CAM, slicing, molding and inspection. *Rejected:* a monolithic CAM engine (privileged code, which breaks principle 1); all-Ingot strategies (inner loops too hot).

| Capability | Ingot (intent) | Wasm components (heavy algorithms) | Anvil operations | Flux forms |
| --- | --- | --- | --- | --- |
| Machining programs | `setup`, `adaptive`, `contour`, `finish`, `drill`, `turn`, `wire_cut` | Strategy Wasm components (adaptive clearing, flowline, swarf, turning rough) | `slice`, `offset_curves_2d`, `medial_axis_2d`, `tool_drop`, `tool_push`, `swept_volume`, `distance` | Cutting force, stability, tool deflection |
| Post-processing | `post(program, machine)` | Post Wasm components (generic ISO 6983, vendor posts) | None | None |
| Machining simulation | `simulate(program)` | None | `swept_volume`, `boolean`, `collide`, `distance` | None |
| Nesting and packing | `nest`, `pack` | `nest-2d` (search and polygon collision), `pack-3d` (search) | `voxelize`, `correlate_grids`, `offset_curves_2d` | None |
| AM build and slicing | `build`, `orient`, `supports`, `slice_build` | Slicers, hatchers, support generators, orientation search, lattice generators | `slice`, `offset_curves_2d`, `deform` | Inherent strain, thermo-mechanical |
| Molding and casting | `mold`, `parting`, `gate`, `cooling`, `gating`, `riser` | Gate optimizer, runner balancer | `visibility`, `draft_map`, `split`, `extend_surface` | Fill, pack, cool, warp, solidification |
| Forming and joining | `die_face`, `bend_sequence`, `weld`, `tightening` | Bend-sequence search, strip layout, weld sequencing | `collide`, `swept_volume` | Sheet forming, springback, weld distortion |
| Assembly | `sequence`, `work_instructions`, `line`, `robot_program` | Sequence planner, line balancer, motion planner | `collide`, `distance`, `swept_volume` | Rigid-body stability |
| Inspection | `inspection_plan`, `cmm_program`, `deviation` | Registration, CMM path planner | `distance`, `fit` | Uncertainty propagation |
| Cost, sourcing, sustainability | `should_cost`, `make_or_buy`, `lca`, `passport` | Quoting components | None | None |

### One model, no parallel geometry

**Decision D-MFG-2:** Manufacturing adds no geometry or result types. Physical things are Bodies, Parts and Assemblies; paths are wire Bodies carrying Fields; results are Fields. *Why:* the UI paints, diffs, caches and queries these types already, so every manufacturing artifact inherits those abilities. *Rejected:* a separate stock type, toolpath geometry type or simulation-result type (parallel abstractions that section 10 forbids).

- Stock, in-process stock, remnants, EDM electrodes and soft jaws are Bodies or Parts.
- Machine tools, robots, printers, fixtures, molds, dies, nests, build plates, PCB panels and cells are Assemblies.
- Cutting tools, holders, inserts, mold-base standard parts, rivets and probes are Catalog parts; a tool assembly is an Assembly.
- Toolpaths, extrusion paths, scan vectors, weld seams, robot paths and probe paths are wire Bodies (lines, arcs, NURBS edges) with Fields over them.
- Engagement, fill time, residual stress, distortion, deviation, cost density and carbon density are Fields painted on geometry.
- Every process step is an `Op` that Kiln caches. There is no separate job concept.
- CAM vocabulary maps onto the glossary. An industry "operation" is a workingstep, after ISO 14649. A "manufacturing feature" such as a hole or pocket is a machining target, found by a `Query`. In this tab, "operation" and "feature" keep their contract meanings.

### Core manufacturing types

The listing is illustrative. The Ingot tab fixes record syntax.

```
// std::mfg::core
pub record Toolpath {
    path:    Body,                         // wire Body: the tool-tip trajectory
    tool:    Instance,                     // tool Assembly placed in its holder
    axis:    Field<Body, Direction>,       // tool orientation; constant for 3-axis
    feed:    Field<Body, Velocity>,
    spindle: Field<Body, AngularVelocity>,
    kinds:   Map<EntityId, MotionKind>,    // cut, plunge, link, rapid; per path edge (a plain value, not a Field)
    error:   ErrorBound,                   // deviation from the ideal path
}

pub record Setup {
    machine: Machine,                      // an Assembly plus controller record
    fixture: Assembly,
    stock:   Body,                         // blank, or the previous setup's in-process stock
    part:    Instance,                     // the design Part, placed
    datum:   Transform,                    // work offset
}

pub record Workingstep {                   // ISO 14649 workingstep
    target:    Query,                      // machining target (hole, pocket, face); re-resolved on every rebuild
    strategy:  StrategyCall,               // strategy Wasm component, parameters, tool, technology
    toolpath:  Toolpath,
}

pub record Program { setup: Setup, steps: [Workingstep] }
pub record Routing { steps: [RoutingStep] }   // ordered steps over work centers
```

### Determinism

**Decision D-MFG-3:** Searches that use randomness take an explicit `seed` input and a counter-based generator. Budgets count work units, never seconds, and parallelism runs as a seeded portfolio. *Why:* the contract forbids clocks and thread-order dependence, and anytime optimizers (nesting, orientation, sequencing) are where these dependences usually creep in. *Rejected:* wall-clock time limits (non-reproducible); shared-state parallel search (thread-order dependent).

1. Anytime results are keyed by budget. The 10,000-iteration nest is the same nest on every platform, so coarse-first streaming stays deterministic.
2. Kiln runs N independent seeded instances and keeps the best by the order (objective, seed). This replaces shared-memory worker threads.
3. Transcendental functions come from one portable math library. Fused multiply-add is used only where written explicitly.
4. Outputs quantize to their declared resolution before formatting, and formatting never depends on locale. NC coordinates quantize to the controller increment; slice contours quantize to the declared slice resolution.
5. External data enters only as pinned, dated data packages: prices, exchange rates, supplier capabilities and regulatory lists. Network calls run as `api` actions outside evaluation and write signed snapshots that become inputs.

### Errors are guidance

Every failure is a typed value that states the reason and where it occurred. Each also carries ranked fixes that an agent or a person can apply as an edit.

```rust
pub enum MfgError {
    Unreachable   { region: Query, reason: ReachReason, fixes: Vec<Fix> },   // tool too short, no access direction
    Collision     { a: InstanceRef, b: InstanceRef, at: PathParam, block: Option<u32>, fixes: Vec<Fix> },
    Gouge         { depth: Length, at: PathParam, fixes: Vec<Fix> },
    AxisLimit     { axis: AxisId, required: f64, limit: f64, fixes: Vec<Fix> },
    Unsupported   { capability: Capability, controller: ControllerId, fixes: Vec<Fix> },
    Infeasible    { constraint: ConstraintRef, witness: Option<CasHash>, fixes: Vec<Fix> },
    OutsideEnvelope { model: ModelId, quantity: QuantityRef, value: f64, fixes: Vec<Fix> },
    MissingData   { what: DataRef, fixes: Vec<Fix> },
    BudgetExhausted { best_so_far: Option<CasHash>, work_done: u64 },
}
```

Every `Fix` is a typed edit, such as a longer tool, an added setup, a tilt angle, a part split, a relaxed constraint or missing data. A strategy never substitutes a different tool, direction or material without saying so. When an explicit policy applies a fix automatically, the CI report shows the policy and the substitution.

### Approval and machine safety

Machines injure people and destroy equipment, so release follows one fixed path.

1. Evaluation generates the program on a branch.
2. Oracles pass: no collisions, no gouges, axis limits respected, and the posted code re-interprets to the toolpath within tolerance.
3. A person approves the program. The approval binds to the content hash of the program, the machine model version and the tool list.
4. The release is a signed tag in `repo`. Released programs are immutable artifacts in CAS.
5. A person triggers transfer to the controller through an `api` action. The action is logged against the release.
6. As-run data is compared with expectations (see Factory connection and digital twin).

**Decision D-MFG-4:** Approval binds to content hashes. A regenerated toolpath never inherits approval, and agents can neither approve nor transfer programs. *Why:* regeneration is automatic, so trust must attach to exactly what was reviewed. *Rejected:* approval per workingstep name (silently survives geometry edits); agent self-approval (no accountability for physical risk).

Simulation proves that a program is consistent with the model; it does not prove that the model matches the shop floor. A wrong tool length in the machine or a mis-clamped part is outside what any software can see. Work instructions therefore require tool-length verification and a reduced-override first run for every newly released program.

[[DIAGRAM: Program release flow. Boxes: Design Part (Ingot) -> Setup (machine, fixture, stock) -> Workingsteps (target Query, strategy, tool) -> Toolpath Wasm components -> Feeds and speeds plus stability (Flux) -> Material removal and collision simulation -> Post-processor Wasm component -> Independent G-code re-interpretation oracle -> Human approval bound to content hash -> Signed release in repo -> Transfer action via api -> Machine (MTConnect/OPC UA) -> As-run data back to the cost and twin models. Red return arrows from each oracle to the Workingsteps box labelled "typed MfgError with fixes".]]

## Machining

### Machine models

A machine is an Assembly of links joined by kinematic mates, plus a controller record. The kinematic mates come from MEC, which owns mates and joints. MFG adds axis limits, dynamics, spindles, tool changers and the controller dialect.

```
pub record Machine {
    structure:    Assembly,              // links are Instances; joints are kinematic mates
    chain:        KinematicChain,        // workpiece side -> tool side, ordered joints
    axes:         [Axis],                // kind, travel limits, velocity, acceleration, jerk
    spindles:     [Spindle],             // power and torque: Field<Interval<AngularVelocity>, _> (CCR-MFG-1)
    tool_changer: Option<ToolChanger>,   // pockets, change position, change time
    channels:     [Channel],             // one per independent controller channel
    controller:   Controller,            // dialect, options, capability flags
    envelope:     Body,                  // working volume for reach checks
}
```

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Forward kinematics | `fk(machine, joints) -> Transform` per channel | `AxisLimit` when a joint value is outside travel | Compare with an independent screw-theory implementation on 10,000 random poses, error under 1e-12 m | 1 |
| Inverse kinematics | `ik(machine, tool_pose) -> [JointSolution]`, closed form for table-table, head-head and head-table 5-axis; damped least squares otherwise | Returns every branch; `Unreachable` with the nearest reachable pose when none exists | `fk(ik(p)) == p` within 1e-9 m and 1e-9 rad | 2 |
| Singularity handling | Branch choice minimizes rotary travel and keeps continuity along the path | `Infeasible` with the singular segment when a flip is unavoidable; fix: re-orient the setup or add a lead angle | No branch flip inside a segment unless reported | 2 |
| Rotary linearization | Inserts points so the tool tip deviates from the programmed path by at most the declared tolerance during rotary interpolation | None; densifies until the bound holds | Re-simulated tip deviation stays under the bound | 2 |
| Kinematic feed limits | Feed Field limited by per-axis velocity, acceleration and jerk | None; reports the binding axis per segment | Axis-wise derivatives of the simulated motion stay under the limits | 1 |
| Spindle limits | Requested power and torque checked against the spindle curve | `Infeasible` naming the segment and the margin | Computed power at sampled points stays under the curve | 1 |

Machine models are packages: a machine builder publishes geometry, kinematics and limits, and a shop adds its own options and fixtures. The model describes nominal kinematics only. Volumetric error compensation lives on the controller and stays out of scope.

### Controllers and post-processors

**Decision D-MFG-5:** Programs are stored in one canonical intermediate form that mirrors ISO 14649. Each workingstep binds a machining target, a strategy with its tool and technology, and a toolpath. Post-processors are Wasm components that map this form to one controller dialect. *Why:* STEP-NC export becomes a mapping rather than a translation, every posted block traces back to its workingstep and path parameter, and one post serves every strategy. *Rejected:* posting from raw cutter-location files (loses target and technology intent); one post per strategy and machine pair (combinatorial and unmaintainable).

ISO 6983-1:2009 defines the G-code program format and address words; ISO reviewed and confirmed it in 2025 [ISO 6983-1]. Each vendor extends it differently. A `Controller` record therefore declares capabilities, and posts read those flags instead of hard-coding vendor names.

| Capability flag | Fanuc | Siemens Sinumerik | Heidenhain TNC | Haas |
| --- | --- | --- | --- | --- |
| Tool center point control | G43.4 / G43.5 | TRAORI | M128 or FUNCTION TCPM | G234 |
| Tilted work plane | G68.2 | CYCLE800 | PLANE functions | G68.2 |
| High-speed contour mode | G05.1 | CYCLE832 | CYCL DEF 32 | G187 |
| Drilling cycles | G81 to G89 | CYCLE81 to CYCLE89 | CYCL DEF 200 series | G81 to G89 |
| Parametric programs | Macro B variables | R parameters and GUD variables | Q parameters | Macro variables |
| Native dialect | ISO | ISO plus Siemens language | Klartext and ISO | ISO |

The codes in this table come from vendor manuals that were not opened in this round [unverified]. Each row is fixed by that controller's conformance corpus (see Oracles) before a post ships.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Generic ISO 6983 post | `post(program, machine) -> NcText + BlockMap`; arcs, helices, cutter compensation, canned cycles when supported, expanded motion otherwise | `Unsupported { capability, controller }` with fixes: expand the cycle, linearize the arc, or choose another controller option | Independent re-interpreter reproduces the toolpath within the declared tolerance | 1 |
| Fanuc and Haas posts, 3-axis | As above, plus tool changes, work offsets, coolant and program structure | As above | Re-interpreter plus the controller conformance corpus | 1 |
| Siemens and Heidenhain posts, 3-axis | Siemens ISO and native; Heidenhain Klartext and ISO | As above | As above | 2 |
| 5-axis posts, all four families | TCP output when available; joint-space output with inverse-time feed otherwise | `AxisLimit` or `Unsupported` with the failing block | Re-interpreter with the full kinematic chain; tip deviation within tolerance | 2 |
| Post configuration in Ingot | Headers, tool-change sequence, coolant codes, block numbering, safe moves and comments are Ingot data | Typed configuration errors at compile time | Golden posted files for each configuration in the corpus | 1 |
| Post extension hooks | Rust Wasm component hooks for logic that data cannot express | Hook errors become `MfgError` with the hook name | Same as the base post | 2 |
| Semantic NC diff | Compares two posted programs by motion and technology, ignoring numbering and formatting | None | Diff of a program with itself is empty; diff of known edits matches | 1 |

Each `BlockMap` entry links a posted block to its workingstep, path parameter and content hash. A machine alarm at block N therefore resolves to a highlighted point on the toolpath and the design feature that produced its target.

### STEP-NC

ISO 14649 defines the STEP-NC data model in parts. Part 10 covers general process data, part 11 milling, part 12 turning, part 111 milling tools and part 121 turning tools. Part 13 covers wire EDM, part 14 sink EDM and part 17 additive manufacturing [ISO 14649 catalog].

ISO 10303-238:2022 (AP238 edition 3) replaced the 2020 edition; AP238 builds on the ISO 14649 machining model and adds product geometry, GD&T and product data management [ISO 10303-238]. Edition 2 added semantic tolerances, machine tool kinematics, additive manufacturing support and machining digital twins [STEP Tools AP238e3].

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| ISO 14649 export | `to_iso14649(program) -> Part21` for parts 10, 11, 12, 111 and 121 | `Unsupported` for constructs without an ISO 14649 entity, listed per workingstep | Schema validation; round trip to the canonical form is identity | 2 |
| AP238 export | `to_ap238(program, design) -> Part21` with geometry, GD&T, workingsteps and toolpaths, using the EXPRESS-generated writer shared with AP242 | As above | Schema validation; geometry round trip within the AP242 tolerances | 3 |
| AP238 and ISO 14649 import | Reads workingsteps, machining targets and toolpaths into the canonical form | `MissingData` for absent technology; never invents feeds | Round trip of a public corpus | 3 |
| EDM and additive parts | ISO 14649-13, -14 and -17 mappings | As above | As above | 4 |

G-code stays the primary shop-floor output because few controllers execute STEP-NC directly [unverified]. STEP-NC is the archival and interchange format. It keeps machining targets, tolerances and technology that G-code discards.

### Tool libraries

ISO 13399 defines how cutting-tool data is represented and exchanged; ISO reviewed and confirmed part 1 in 2021 [ISO 13399-1]. A tool in Crucible is an Assembly of Catalog parts: cutting item, adaptive items (holders, extensions, collets) and machine-side interface. Its ISO 13399 properties are typed Quantities on the Catalog part.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| ISO 13399 import | Vendor packages to Catalog parts with 2D profile, 3D geometry and properties | `MissingData` per absent property; never guesses a dimension | Imported geometry matches the vendor 3D model within 1 µm on a public corpus | 1 |
| Tool assembly | `assemble_tool(cutter, holder, stickout) -> Instance` with gauge length and collision envelope | `Infeasible` when interfaces mismatch | Gauge length equals the analytic stack-up | 1 |
| Cutting data | Per tool and material group: speed, feed per tooth, engagement limits, mechanistic force coefficients, tool-life parameters, each with source and uncertainty | `MissingData` with fixes: run the calibration routine or accept vendor nominal values with their stated uncertainty | Coefficients reproduce the calibration cuts within their stated uncertainty | 1 |
| Shop library | A package of tool Assemblies with pocket numbers and measured lengths | Conflicting pocket numbers fail the build | Unique pockets per machine | 1 |
| Tool wear and life | Expected life per tool from cutting data and engagement history | Flags tools past expected life before the program ends | Life prediction checked against as-run tool changes (factory feedback) | 4 |

### Stock models

Stock is a Body. The blank can be bar, plate or extrusion, a near-net casting or forging Body produced by an upstream process plan, or the in-process stock of the previous setup.

**Decision D-MFG-6:** In-process stock is an `Implicit` Body backed by a sparse narrow-band distance grid at a declared resolution, with an `ErrorBound`. The interactive viewer derives a GPU tri-dexel cache from it, and that cache is a render cache, not a model type. Gouge and leftover checks use `anvil::distance` against the exact design B-rep. *Why:* repeated swept-volume subtraction is fast and robust on narrow-band grids, error is explicit, and the design side stays exact. *Rejected:* exact B-rep stock (Boolean cost grows with every move, and robustness suffers); meshes only (repeated mesh Booleans accumulate slivers).

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Blank definition | `stock(kind, material, size or Body, cert)` | Typed error when the part is not inside the stock | Containment check | 1 |
| In-process stock | `simulate(program) -> (Body, Field<Body, u32>)`: stock plus the index in `Program.steps` of the step that last cut each region | `OutsideEnvelope` when the resolution is too coarse for the requested tolerance | Volume removed equals the integrated swept volume within the error bound | 1 |
| Stock hand-off | Stock of setup N becomes the blank of setup N+1 under the new datum | `Infeasible` when the new fixture collides with the stock | Transform round trip | 1 |
| Remaining material | `rest(stock, part, tolerance) -> Body` | None | Rest Body plus part covers the stock within the bound | 1 |

### Toolpath algorithms

Each strategy is a Wasm component with one WIT interface. It receives a resolved `Setup`, a target region (`Query` results), a tool Instance and parameters, and it returns a `Toolpath`. Strategies call Anvil operations for geometry and never re-implement offsetting, slicing or distance.

```
// WIT, abridged
interface strategy {
  record request { setup: setup-ref, region: list<entity-ref>, tool: instance-ref,
                   params: list<param>, tolerance: f64, seed: u64, budget: u64 }
  generate: func(r: request) -> result<toolpath, mfg-error>;
}
```

The shared geometric operations are specified by MFG and implemented in Anvil:

| Anvil operation | Purpose | Method | Phase |
| --- | --- | --- | --- |
| `anvil::offset_curves_2d` | Pocket offsets, contours, AM perimeters | Exact predicates on line and arc segments; arcs stay arcs, as in cavalier_contours (MIT or Apache-2.0) [cavalier_contours] | 1 |
| `anvil::medial_axis_2d` | Adaptive clearing skeletons, trochoidal slotting, variable-width AM perimeters | Segment Voronoi diagram with exact predicates; arcs supported | 1 |
| `anvil::slice` | Waterlines, AM layers, cutting profiles | Plane-Body section on every representation, returns curves with an `ErrorBound` | 1 |
| `anvil::tool_drop` | Raster and projection finishing | Drop-cutter for flat, ball, bull, taper and generic revolved profiles against B-rep and mesh, with exact contact classification | 1 |
| `anvil::tool_push` | Waterline finishing | Push-cutter against triangles and faces | 1 |
| `anvil::swept_volume` | Stock update, collision, reachability | Envelope of a revolved tool profile along a 5-axis motion; narrow-band implicit output with error bound | 1 (3-axis), 2 (5-axis) |
| `anvil::distance` | Gouge and leftover checks | Exact closest-point queries with bounding-volume hierarchies | 1 |
| `anvil::correlate_grids` | 3D packing collision and proximity | GPU FFT correlation of occupancy grids with a proven rounding bound, exact integer output, CPU fallback (D-MFG-12) | 2 |

OpenCAMLib implements drop-cutter and push-cutter for flat, ball, bull, cone and composite cutters [OpenCAMLib]. It is LGPL-2.1, and Open Hub reports very low recent activity [Open Hub OpenCAMLib]. Crucible re-implements the published algorithms natively and uses OpenCAMLib only as an external reference oracle in CI, never linked.

| Strategy | Contract summary | Method | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- | --- |
| Face, pocket, contour (2.5D) | Region + depth steps -> offset or zigzag passes with lead-in, lead-out and links | Offsets of the region, island-aware ordering, ramp or helix entry | `Unreachable` for regions narrower than the tool; fix: smaller tool or rest pass | Stock simulation leaves no material above the floor plus allowance; no gouge | 1 |
| Adaptive clearing | Region + max radial engagement angle + axial depth -> trochoidal-blended path whose engagement Field stays within the bound | Medial-axis-seeded spiral with engagement measured on the in-process stock and corrected per step (see below) | `Infeasible` when the bound cannot be held, with the offending region; reports achieved maximum | Engagement Field recomputed by the independent stock simulator stays under the bound plus tolerance | 1 |
| Trochoidal slotting | Slot centerline + width + engagement -> trochoid with variable radius and step | Constant-engagement trochoid with parameters varied per period (PVTR) [Li et al. 2025] | As above | As above | 2 |
| Rest machining | Previous stock + smaller tool -> passes only where material remains | Uses the `rest` Body as the region | None; empty program when nothing remains | Rest Body after the pass is empty within tolerance | 1 |
| Parallel and scallop finishing | Surfaces + scallop height -> raster or constant-scallop passes | `tool_drop` sampling, refined until the chord between samples deviates by less than the tolerance; scallop offsets on the surface | Gouge depth is bounded by the tolerance; reports unreachable areas | Scallop height Field under the target; independent gouge check against exact B-rep | 1 |
| Waterline and steep-and-shallow | Surfaces + slope threshold -> Z-level passes on steep areas, scallop passes on shallow areas | `tool_push` waterlines, slope-split regions, overlap blending | As above | As above | 1 |
| Pencil and corner cleanup | Concave edges + reference tool -> bi-tangent passes | Double-contact curves from `tool_drop` | As above | Rest material along corners under target | 2 |
| Flowline and isoparametric | Surface set -> passes along surface parameters | Iso-curves, re-spaced to a scallop bound | Typed error on degenerate parameterization | Scallop bound | 2 |
| 5-axis swarf | Ruled walls + tool -> flank passes | Ruling line plus deviation-minimizing tool axis | `Infeasible` when the wall is not developable within tolerance; reports deviation | Wall deviation Field within tolerance | 2 |
| 5-axis multi-axis finishing | Surfaces + tilt strategy (lead, lean, tilt to point or curve, automatic) -> 5-axis path | Drive from any 3-axis pattern, then axis assignment with collision-aware tilting and smoothing | `Collision` or `AxisLimit` with fixes (more lead, shorter holder, other setup) | Full machine collision simulation; axis smoothness bounds | 2 |
| 5-axis roughing | Region + tool -> tilted 3+2 or simultaneous adaptive passes | Adaptive clearing in tilted frames, chosen by access analysis | As adaptive | As adaptive plus collision | 3 |
| Barrel and circle-segment finishing | Large-radius tools tangent to the surface -> wide stepovers | Tangent-plane fitting of the barrel profile | As multi-axis | Scallop and gouge | 3 |
| Deburr and chamfer | Edges + chamfer tool -> edge-following passes at the target size | Edge chains, tool axis normal to the bisector | Unreachable edges reported | Chamfer size measured on the simulated stock | 2 |
| Engraving and text | Text or curves -> V-carve or line passes | Medial axis for V-carve depth | None | Simulated groove width | 2 |
| Thread milling | Hole + thread spec -> helical passes | Analytic helix | `Infeasible` when the tool does not fit | Thread profile on simulated stock | 2 |
| Drilling cycles | Holes -> spot, drill, peck, chip-break, ream, bore, tap, back-bore cycles | Hole recognition from design semantics, ordering by shortest tour with tool changes | `Unsupported` cycle -> expanded moves | Hole depth and position on simulated stock | 1 |
| Probing | Targets -> probe paths for setup and in-process measurement | Touch points from the inspection plan | Unreachable points reported | Probe path collision-free | 2 |

**Decision D-MFG-7:** Adaptive clearing is an engagement-controlled spiral seeded by the medial axis, measured against the true in-process stock rather than geometric offsets. Its quality bound is stated as maximum engagement angle and maximum chip thickness, and the oracle measures that bound independently. Crucible's implementation is clean-room and uses no vendor code. *Why:* vendors document the behavior (constant engagement, smooth motion) but not their algorithms, so the measurable bound is the contract. *Rejected:* offset-based "high-speed" pockets (engagement spikes at corners); adopting a single vendor's patented method.

Boeing holds US patent 9,164,503 on medial-axis toolpaths with a pre-roughing slot and a constant-radial-depth spiral; Google Patents lists it as active until an estimated February 2034 [US 9,164,503]. The adaptive clearing Wasm component therefore needs a freedom-to-operate review before phase 1 ships, as the contract requires for Anvil's intersection patent. Engagement-controlled methods without the claimed pre-roughing slot sequence are the default design.

Adaptive clearing method, in order:

1. Compute the medial axis of the region minus the tool radius, with exact predicates.
2. Seed an entry: helix or ramp at the medial axis vertex of maximal clearance, or a pre-drilled hole.
3. Grow the cleared region in spiral steps. Each step solves for the next curve so the engagement angle against the current stock equals the requested angle within tolerance.
4. Where the engagement bound cannot be held (narrow necks, corners), switch locally to trochoidal arcs with variable radius.
5. Link passes with smooth, collision-checked, tangent-continuous moves that stay inside cleared material.
6. Assign the feed Field from chip thinning so that maximum chip thickness stays at the requested value.

### Turning, mill-turn and Swiss

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Turning profile extraction | Revolved Body -> 2D profile in the XZ half-plane | `Infeasible` when the part is not turnable; reports non-revolved faces | Profile revolved equals the part within tolerance | 2 |
| Rough and finish turning | Profile + insert -> longitudinal, facing or profile passes with insert-angle clearance checks | `Unreachable` for undercuts the insert cannot reach | Simulated 2D stock matches the profile plus allowance | 2 |
| Adaptive turning | Constant chip-thickness roughing for heat-resistant alloys, as in NX 2606 Rough Turn Adaptive [Janus NX 2606] | As above | Chip thickness Field under target | 3 |
| Grooving, parting, threading | Groove, cutoff and thread cycles (single point, multi-start) | `Unsupported` cycle -> expanded moves | Simulated profile | 2 |
| Mill-turn | Multi-channel programs: C and Y axis milling, B-axis tilting, sub-spindle transfer | Channel conflicts reported as `Infeasible` with the time window | Multi-channel simulation without collision; synchronization points honored | 3 |
| Swiss-type | Sliding headstock, guide bushing, gang tools, parallel channels | As mill-turn | As mill-turn plus bar-feed model | 4 |
| Channel synchronization and balancing | Assigns workingsteps to channels to minimize cycle time subject to precedence and collision | `Infeasible` with the conflicting workingstep pair | Optimal on small benchmark instances; simulation of the schedule | 4 |

### EDM

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Wire EDM, 2-axis | Profile + wire + technology table -> rough and skim passes with offsets, tabs and corner strategies | `Infeasible` for internal radii under wire radius plus overburn | Simulated kerf profile within tolerance | 3 |
| Wire EDM, 4-axis taper | Ruled upper and lower profiles -> synchronized UV paths | `Infeasible` when taper exceeds the machine angle | Ruled-surface deviation | 3 |
| Sinker EDM electrodes | Design region -> electrode Body with undersize (spark gap and orbit) and burn sequence | Typed error when the electrode cannot be machined | Electrode plus gap reproduces the cavity | 4 |
| ISO 14649-13 and -14 | Wire and sink EDM process data | As STEP-NC | As STEP-NC | 4 |

Technology tables (speeds, offsets, passes per material and thickness) come from machine packages. MFG does not model the spark physics.

### Gears, grinding and other machining processes

Golden product 3 (gearbox) needs gear manufacturing in phase 2. MEC owns gear geometry and rating; MFG owns how gears are cut, finished and inspected.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Gear generating | Hobbing, shaping and power skiving: tool selection, machine settings and cycle data from the gear record, posted through the machine's gear cycles | `Unsupported` when the machine lacks the generating cycle; fix: 5-axis gear milling | Simulated tooth flank from the generating kinematics matches the design flank within the gear quality grade | 2 |
| 5-axis gear milling | Flank and root passes from the multi-axis strategies for low-volume and large gears | As 5-axis finishing | Flank deviation Field within tolerance | 2 |
| Gear grinding | Generating and profile grinding settings, dressing, stock allowance from heat-treatment distortion | `MissingData` without distortion allowance | Simulated ground flank | 4 |
| Surface and cylindrical grinding | Wheel selection, infeed, spark-out, dressing intervals | `OutsideEnvelope` for unmodeled wheel and material pairs | Simulated profile; burn-risk Field from specific energy [unverified] | 4 |
| Broaching, honing, lapping | Routing steps with process records; no toolpath synthesis | `MissingData` | Records complete | 4 |
| Gear inspection | Profile, helix and pitch measurement plans for gear inspection machines or CMMs | As inspection | Evaluation against the design flank | 3 |

### Laser, plasma, waterjet, punching and press brake

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Profile cutting | Flat parts or nests -> cut paths with kerf compensation, lead-ins, micro-joints, pierce strategy, common-line cutting | `Infeasible` for details smaller than kerf plus minimum web | Simulated kerf boundary matches the part within tolerance | 2 |
| Cut ordering and heat control | Order inner before outer, spread heat, avoid crossing cut parts, minimize rapid travel | None; reports rapid distance | Constraint satisfaction checker; tour length against a computed lower bound | 2 |
| Waterjet taper and lag compensation | Speed-dependent taper and corner slowdown from technology tables | `MissingData` without tables | Simulated edge taper | 3 |
| Bevel cutting | 5-axis plasma or waterjet bevels for weld preparation | `AxisLimit` with fixes | Bevel angle on the simulated edge | 4 |
| Turret punching | Tool assignment, nibbling, forming tools, sheet repositioning | `Infeasible` with the contour and missing tool | Simulated punched sheet matches the flat pattern | 3 |
| Press-brake planning | Flat pattern + tooling -> bend sequence, tool stations, backgauge positions | `Infeasible` with the colliding bend and fixes (split, re-sequence, other tooling) | Bend simulation collision-free; sequence optimal on small instances | 2 |

**Decision D-MFG-8:** Press-brake sequencing is a search over bend orders with collision checks between the partially bent part, punch, die and machine. The bend allowance comes from MEC's sheet-metal model, and springback from Flux or measured data. *Why:* one search handles every part, and the physics stays in its owning tabs. *Rejected:* rule tables per part family (brittle, not general).

### 2D nesting

Sparrow (MIT) is the strongest published heuristic for 2D irregular strip packing [sparrow]. It decomposes the problem into a sequence of feasibility problems and resolves overlap with guided local search [Gardeyn et al. 2025]. It builds on jagua-rs (MPL-2.0), a collision engine with continuous rotation, container holes and quality zones, and minimum separation [jagua-rs].

With 20-minute runs on the ESICUP benchmarks, sparrow matches or improves every prior best-known density [Gardeyn et al. 2025]. The largest gains are on SWIM (79.83% versus 75.94%) and SHIRTS (90.92% versus 88.96%) [Gardeyn et al. 2025]. Its authors note a weakness on homogeneous instances, where it does not exploit repeated compact patterns [Gardeyn et al. 2025].

**Decision D-MFG-9:** The 2D nesting Wasm component adopts the sparrow approach on a jagua-rs-style collision engine. Wall-clock limits are replaced by work-unit budgets and seeded portfolios (D-MFG-3). *Why:* these are the leading open methods, both are Rust and both permit Wasm builds. *Rejected:* no-fit-polygon placement heuristics (lower density in published comparisons); closed vendor libraries (unauditable, license-bound).

MPL-2.0 is file-level copyleft: Crucible may link jagua-rs unmodified, and modifications to its files must be published. This is compatible with the open-core policy, but `PLT` must confirm it in the license policy (see Open questions).

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Strip and sheet nesting | `nest(items, sheets, rules, seed, budget) -> Nest` (an Assembly of placed flat Parts) | `Infeasible` when an item exceeds every sheet; `BudgetExhausted` returns the best feasible nest | Independent exact overlap checker; utilization recomputed | 1 |
| Rules | Rotation sets (free, 90 degrees, grain), mirroring, part spacing, sheet margins, quality zones, common-line eligibility | Typed rule conflicts | Each rule checked on the result | 1 |
| Remnants | Remaining sheet becomes a remnant Part with geometry and identity | None | Remnant plus parts plus kerf equals the sheet | 2 |
| Associativity | Nests regenerate when part geometry or quantities change, keeping prior placements as warm starts | None | Warm start never worsens the incumbent | 2 |
| Multi-sheet and inventory | Assigns items to a mix of sheet sizes and remnants to minimize cost | As above | Cost recomputed independently | 3 |

Nesting quality target: within 1 percentage point of sparrow's published expected density on the ESICUP set at an equal work budget (target). The benchmark uses the ESICUP instances plus the ten GARDEYN real-world instances [Gardeyn et al. 2025].

### Physics-based feeds and speeds

Feeds and speeds are computed, not looked up. The `cutting_conditions` function combines the engagement Field from stock simulation with the tool's cutting data, the machine's spindle curve and the stability lobes. It outputs feed and spindle-speed Fields that maximize material removal rate subject to explicit constraints.

| Constraint | Model | Validity envelope | Phase |
| --- | --- | --- | --- |
| Maximum chip thickness | Chip thinning from radial engagement and tool geometry | Rigid tool; calibrated chip-thickness range | 1 |
| Cutting force and power | Mechanistic model: cutting and edge coefficients per tool-material pair, integrated over engaged flute segments | Calibrated speed and chip-thickness ranges; stable cutting | 1 |
| Spindle torque and power | Machine spindle curve | Machine record | 1 |
| Tool deflection | Cantilever of the tool assembly; Flux beam or solid model for complex holders | Linear elastic | 2 |
| Stability | Stability lobes (next subsection) with a declared margin | FRF validity | 3 |
| Surface finish | Feed marks and scallop height from the tool profile | Kinematic roughness only | 1 |
| Tool life | Extended Taylor equation per tool-material pair | Calibrated speed range | 3 |

Contract: `cutting_conditions(toolpath, material, machine, objective) -> (Field<Body, Velocity>, Field<Body, AngularVelocity>, ConstraintReport)`. The feed Field is piecewise constant, quantized to the controller increment, and limited to a declared number of changes per meter. The `ConstraintReport` names the binding constraint for each segment.

Failure behavior: inputs outside a model's envelope return `OutsideEnvelope`, never an extrapolated feed. Missing coefficients return `MissingData` with a calibration-cut program as the fix. Vendor nominal values remain available as an explicit, flagged choice.

Oracle: spindle power predicted by the model matches measured power on the calibration corpus within the coefficient uncertainty. A held-out set of shop programs checks that no segment exceeds any constraint when recomputed independently. Phase 1 (chip thickness, power, finish); phase 2 (deflection); phase 3 (stability, tool life).

Calibration is a built-in program. A short sequence of cuts at varied feed and engagement, with spindle power or a dynamometer, fits the coefficients by least squares and records their uncertainty in the cutting-data record.

CloudNC describes its cutting-parameters engine as physics-based AI and states that strategies still need human review [CloudNC CAM Assist]. Physics-based feed optimization along the path is offered by VERICUT Force [unverified: its product page did not load]. Crucible's target: cycle time within 5% of the leading feed optimizer on a shared benchmark set, with zero constraint violations (target).

### Material removal and machine collision simulation

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Material removal | `simulate(program) -> in-process stock` per D-MFG-6, streamed coarse to fine | `OutsideEnvelope` when the grid cannot meet the requested tolerance | Independent simulator using exact mesh Booleans on reduced cases; removed volume agrees within the error bound | 1 |
| Gouge and leftover | Signed distance from simulated stock to the exact design B-rep, as a Field | None; reports locations and depths | Seeded gouge corpus: every planted gouge detected | 1 |
| Machine collision | Continuous collision detection between every pair of machine links, tool, holder, fixture and stock along every motion | `Collision` with block, path parameter, pair and fixes | Seeded crash corpus with 100% detection; zero false negatives is a hard gate | 1 (3-axis), 2 (5-axis) |
| Near-miss clearance | Minimum distance per pair as a Field along the path, against a declared clearance | Warning below clearance | Analytic cases | 2 |
| Rapid-move safety | Rapids checked against stock and fixture with the same rigor as cuts | `Collision` | As above | 1 |
| Cycle time | Jerk-limited kinematic simulation with a controller look-ahead model, tool changes and dwell | None; reports time per workingstep | Within 5% of measured time after calibration (target) | 1 |
| Viewer | GPU tri-dexel render cache of the stock for scrubbing and playback | Falls back to CPU rendering | Visual regression snapshots | 1 |

Continuous collision detection uses conservative advancement on bounding-volume hierarchies. Each motion segment is subdivided until the swept bound is separated or contact is proven. The method never samples at fixed intervals, so thin parts cannot slip between samples.

An adaptive tri-dexel method on GPU refines dexels only near the surface and reports about a fivefold speedup at the highest resolution [Ozcan et al. 2024]. Crucible's viewer cache uses the same adaptive idea. ModuleWorks states that its 5-axis library is used by more than 60% of leading CAM vendors, which makes it the main implementation to beat [ModuleWorks].

### Chatter and stability lobes

Flux supplies the frequency response function (FRF) at the tool tip. It comes from modal analysis of the spindle, holder and tool, coupled by receptance coupling, or from a measured tap test stored as a Field. MFG computes stability lobes from the FRF and the cutting coefficients.

Altintas, Stepan, Merdol and Dombovari compare the zero-order frequency-domain solution, the multi-frequency solution and semi-discretization [Altintas et al. 2008]. The zero-order solution is analytic and fast, and it is accurate when radial immersion exceeds about a quarter of the cutter diameter. At low radial immersion it misses added lobes that the other two capture, and semi-discretization also handles variable pitch and spindle-speed variation [Altintas et al. 2008].

**Decision D-MFG-10:** Interactive mode uses the zero-order solution; sign-off mode uses semi-discretization. Low radial immersion, variable-pitch tools and spindle-speed variation always use semi-discretization. *Why:* this matches each method's published validity and keeps interactive updates under one second. *Rejected:* zero-order everywhere (misses lobes at low immersion, which adaptive clearing uses constantly); time-domain simulation as the default (too slow for interactive use, kept as a reference oracle).

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Tool-tip FRF | `frf(tool_assembly, machine) -> Field<Interval<Frequency>, Complex<Compliance>>` (CCR-MFG-1) from Flux modal analysis plus receptance coupling, or from tap-test data | `MissingData` without spindle-side receptance; fix: tap-test routine | Published benchmark FRFs | 3 |
| Stability lobes | `lobes(frf, coefficients, engagement) -> Field<Interval<AngularVelocity>, Length>` with uncertainty bands | `OutsideEnvelope` at low surface speed, because process damping is not modeled [Altintas et al. 2008] | Agreement with published lobes and with time-domain simulation | 3 |
| Stability-aware planning | Spindle speed and axial depth chosen inside the stable region with margin | Reports when no stable speed exists for the requested depth | Every segment below the lobe minus margin | 3 |
| Chatter detection feedback | Spindle-load or vibration data from the machine flags chatter and updates the FRF estimate | None | Replay of recorded chatter events | 4 |

### Regeneration, templates and target recognition

**Toolpaths are functions of geometry.** A workingstep refers to its target through a `Query`, never through stored face indices, and Kiln recomputes only the workingsteps whose resolved inputs changed. A lost target produces a `ResolveError` with suggested fixes and is never silently re-targeted.

Regeneration invalidates approval (D-MFG-4), and proposal review shows the toolpath diff.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Incremental regeneration | Edit -> only affected workingsteps recompute; unchanged steps keep their content hash | `ResolveError` per lost target | Rebuilding an unchanged design reproduces identical hashes | 1 |
| Toolpath diff | Geometric and technology diff between two program versions, painted on geometry | None | Diff of identical programs is empty | 1 |
| Workingstep templates | Ingot functions from (target class, material, machine class) to lists of strategy calls; published as packages | Typed error when no template matches; never a silent default | Golden programs for template test parts | 1 |
| Template matching | Ranks templates by declared applicability predicates | Ties reported; the person or agent chooses | Deterministic ranking | 2 |
| Setup planning | Groups targets by access direction into setups and proposes fixtures | `Unreachable` for targets with no access direction | Every target machined in exactly one setup | 2 |

Templates are ordinary Ingot. A shop's knowledge (preferred tools, step-downs, finishing allowances) lives in its own package, versioned like any other.

```
use std::mfg::{adaptive, finish_walls, StrategyCall, Pocket, Machine}

// A shop template: an ordinary Ingot function, published in the shop's package
pub fn pocket_alu(p: Pocket, m: Machine) -> [StrategyCall] {
    let rougher  = shop::em_10mm_3fl
    let finisher = shop::em_6mm_4fl
    let rough = adaptive(p, tool: rougher, engagement: 12deg, stepdown: 1.5 * rougher.diameter)
    let walls = finish_walls(p, tool: finisher, allowance: 0mm, scallop: 2um)
    [rough, walls]
        .require(m.spindle.max_speed >= 12000rpm)
}
```

The `require` makes the template's applicability explicit, so template matching can rank templates by their declared predicates instead of by hidden rules.

**Machining-target recognition** (feature recognition in the CAM literature) has two sources.

1. Design semantics come first. Ingot features already know they are holes, pockets or threads, with their tolerances, so no guessing is needed for native designs.
2. Imported B-reps without history go through a recognition Wasm component. It runs rule-based graph matching on the face adjacency graph, followed by a learned panoptic segmenter. Its output is a set of proposed targets (holes, pockets, slots) with confidences, which a person or agent confirms. Unconfirmed targets never drive toolpaths. Rule-based recognition ships in phase 2 and the learned segmenter in phase 3.

The leading learned recognizers are graph networks over B-rep adjacency graphs. On the MFInstSeg dataset, AAGNet reaches 97.44% panoptic quality (PQ) with the full training set [FeatureFox]. FeatureFox reaches PQ above 0.9 with about 250 training parts, where AAGNet needs about 5,000 [FeatureFox].

Crucible's target is PQ of at least 97% on MFInstSeg, and above 0.9 with 250 training parts (target). Inference runs on CPU in fixed-order arithmetic with pinned weights, so results are deterministic.

### Agent-proposed toolpaths

Agents program machines the same way people do: through Ingot on a branch. CloudNC presents CAM Assist output as a draft that users review, simulate and edit before running [CloudNC CAM Assist]. NX 2606 offers generative machining suggestions, and a Lambda Function add-on for NX CAM recommends tools, parameters and toolpaths [Janus NX 2606; Siemens Lambda Function].

1. The agent reads the design and a machinability report through `api` Inspect.
2. It writes setups, templates and workingsteps as Ingot on a branch.
3. CI evaluates every oracle: collision, gouge, axis limits, re-interpretation, constraint report and cycle time.
4. The agent opens a Proposal with rationale, cycle-time and tool-count deltas, and snapshots.
5. A person reviews the overlay, engagement Fields and diff, then approves under D-MFG-4.

Agents cannot approve programs, transfer them to machines, or edit oracles. Cost caps apply to simulation compute as to any evaluation. Phase 1.

## Additive manufacturing

### Process categories

ISO/ASTM 52900:2021 is the current vocabulary standard, reviewed and confirmed by ISO in 2025 [ISO/ASTM 52900]. The seven process categories, first formulated by ASTM F42 [Loughborough AMRG] and carried into ISO/ASTM 52900 [unverified], organize `std::mfg::am`. One pipeline (build, orient, pack, support, simulate, compensate, slice, emit) serves all seven, and each category supplies Wasm components for the steps that differ.

| Category | Typical processes | Build preparation | Layer output | Process simulation | Phase |
| --- | --- | --- | --- | --- | --- |
| Material extrusion | FFF, pellet, continuous fiber, concrete | Plate nesting, tree supports | G-code (Marlin, Klipper, RepRapFirmware flavors) | Warp (phase 4) | 1 |
| Powder bed fusion | Laser and electron beam, metal and polymer | Plate placement (phase 1), 3D packing for polymer (phase 2), supports for metal (phase 2) | 3MF production files for the vendor build processor (phase 1); own scan vectors in 3MF Toolpath (phase 2) | Inherent strain (interactive), thermo-mechanical (sign-off) | 1 (polymer), 2 (metal) |
| Vat photopolymerization | SLA, DLP, mSLA | Orientation for peel force, point supports, island detection | Layer images with exposure | Cure depth, peel force | 2 |
| Material jetting | Photopolymer and wax jetting | Voxel material assignment | Voxel or image stacks per material | None beyond geometry | 3 |
| Binder jetting | Metal and sand | 3D packing, sintering setters | Layer bitmaps | Sintering shrinkage and distortion (phase 4) | 3 |
| Directed energy deposition | Laser or arc wire and powder, hybrid with machining | Substrate, bead model, multi-axis paths | NC programs on the machining stack | Thermo-mechanical, bead geometry | 3 |
| Sheet lamination | Ultrasonic AM, laminated object manufacturing | Layer outlines and bonding | Cut paths plus machining programs | Out of scope (stated) | 5 |

**Decision D-MFG-11:** The AM pipeline slices the design Body directly in any representation. It never converts to an STL as an intermediate step. Implicit lattices are sliced from their fields, and B-reps are sliced exactly, each with an `ErrorBound`. *Why:* triangulating a dense lattice is the bottleneck of conventional build preparation, and direct slicing removes both that cost and the facet error. *Rejected:* mesh-only pipelines (memory blow-up on lattices, faceting on curved faces).

```
use std::mfg::am::{build, orient, pack, supports, compensate, slice_build}

let plate = build(printer: shop::pbf_ti64_400, parts: [bracket.qty(12)])
    |> orient(objectives: [support_volume, distortion, face_quality(bracket.face(mount))])
    |> pack(spacing: 3mm, seed: 7)
    |> supports(style: block_lattice, critical_angle: 45deg)
    |> compensate(model: inherent_strain, max_iterations: 4, tolerance: 0.1mm)
    |> slice_build(layer: 30um)
plate.require(predicted_deviation(plate) < 0.1mm)
```

### Build preparation

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Orientation | `orient(part, printer, objectives, seed) -> [Pareto orientation]` over support volume and area, build height, critical-face quality, distortion risk, projected peel area and anisotropy relative to load paths from MEC | Reports dominated objectives; never picks silently when the Pareto front has more than one point and no weights are given | Objective values recomputed independently; brute-force optimum on small grids | 1 |
| Plate nesting | 2D nesting (D-MFG-9) of part footprints with spacing and thermal rules | As nesting | As nesting | 1 |
| 3D packing | `pack(parts, volume, rules, seed, budget) -> Assembly` for powder beds, with interlock-free option | `Infeasible` when a part exceeds the volume | Exact pairwise clearance and translational removability checks | 2 |
| Supports, extrusion | Tree supports with collision-free branches and controlled contact area | Reports unsupported overhangs with fixes (reorient, raise angle, add chamfer) | Every overhang beyond the critical angle supported; support removability by access check | 1 |
| Supports, vat | Point supports with peel-force and island checks per layer | Reports islands and peel-force violations | Every layer island supported; peel force under printer limit | 2 |
| Supports, metal PBF | Block, line, cone and lattice supports chosen for heat conduction, distortion restraint and removal access | Reports regions with predicted distortion above tolerance | Support adequacy from process simulation; removal access check | 2 |
| Labels and serials | Engraved or embossed identifiers per instance, linked to `repo` serial numbers | Typed error when the label face is too small | Label present and legible on the sliced layers | 2 |

Spectral packing computes all collision tests for one placement as an FFT correlation of voxel grids. It also checks that each object can still be removed by translation [Cui et al. 2023]. On the "pieces" benchmark it reaches 50.45% density in 103 s on GPU. PolyDevs reaches 40.87% in 3,598 s, and Netfabb 28.23% in 1,810 s [Cui et al. 2023].

**Decision D-MFG-12:** 3D packing adopts spectral packing. The correlation is the Anvil operation `anvil::correlate_grids`, collision counts use exact integer arithmetic, and proximity scores quantize to fixed point, with ties broken by grid index. *Why:* this is the best published density-speed trade-off, and integer collision counts make placements bit-identical across platforms, which floating-point FFT alone cannot guarantee. *Rejected:* heuristic bounding-box packers (low density); the floating-point method unchanged (platform-dependent argmin flips).

FFT correlation of 0/1 grids yields integers plus rounding error. The `anvil::correlate_grids` operation proves that this error stays below 0.5 for the grid size used, and otherwise falls back to direct integer correlation. The density target is within 2 percentage points of the published Thingi10K result, at equal or lower GPU time (target).

### Slicing and toolpath strategies

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Planar slicing | `anvil::slice` per layer on any Body representation -> region contours with `ErrorBound` | Non-closed contours become typed errors naming the defective faces | Area per layer equals the integrated cross-section within the bound | 1 |
| Adaptive layer height | Layer heights chosen so cusp height stays under a bound, limited by the printer's allowed set | None | Cusp height Field under the bound | 1 |
| Variable-width perimeters | Contour-parallel beads whose count and widths fill thin regions without gaps or overlaps | Regions thinner than the minimum bead are reported, never dropped silently | Fill ratio per region; no over- or under-fill beyond tolerance | 1 |
| Infill | Rectilinear, grid, triangular, gyroid and other TPMS, adaptive density driven by a Field | None | Density Field matches the target within tolerance | 1 |
| Seams, ordering, travel | Seam placement by visibility and curvature, travel minimization, retraction and wipe | None | Tour length against a computed lower bound | 1 |
| Multi-material and color | Per-region material assignment from Fields, purge and prime planning | `MissingData` for undefined materials | Each region assigned exactly one material | 2 |
| PBF scan strategies | Contour, hatch with stripes or islands, rotation per layer, upskin and downskin parameter sets | `OutsideEnvelope` for parameters outside the printer profile | Scan coverage of every region; energy density Field within profile bounds | 2 |
| Vat layer images | Anti-aliased masks with per-layer exposure | None | Image area equals contour area within one pixel per edge | 2 |
| DED paths | Bead-model paths, planar or multi-axis, on the machining stack | `Collision` and `AxisLimit` as in machining | Bead deposition simulated against the target Body | 3 |
| Curved-layer and multi-axis slicing | Layers as isosurfaces of an optimized scalar field | `Infeasible` with fixes when no collision-free sequence exists | Collision-free printing order; support-free coverage | 4 |

Variable-width perimeters follow Kuipers, Doubrovski, Wu and Wang, whose framework sets bead count and widths with pluggable schemes and limits extreme widths [Kuipers et al. 2020]. PrusaSlicer, OrcaSlicer and CuraEngine are AGPL-3.0 [PrusaSlicer; OrcaSlicer; CuraEngine], so Crucible implements the method from the paper and links none of them. The slicers remain external reference oracles for output comparison.

Curved-layer slicing follows the general framework of Zhang, Fang, Huang, Dutta, Lefebvre, Kilic and Wang, which won Best in Show at SIGGRAPH Asia 2022 [Zhang et al. 2022]. It optimizes quaternion fields for support-free printing, strength and surface quality, then takes isosurfaces of a deformation-mapped scalar field as curved layers [Zhang et al. 2022]. This is a phase 4 Wasm component on the multi-axis machine models of the machining stack.

### Lattices and infill structures

Lattices are `Implicit` Bodies whose parameters are Fields. A graded lattice comes from a density Field produced by Flux topology optimization (golden product 2). The lattice is sliced and simulated without meshing.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| TPMS lattices | Gyroid, Schwarz, diamond and others with thickness and cell-size Fields | `Infeasible` where wall thickness falls below the printer minimum | Relative density matches the analytic value within tolerance | 1 |
| Beam lattices | Graph lattices (cubic, octet, Voronoi, conformal) as beams with radius Fields; exported as 3MF Beam Lattice | As above | Beam-node consistency; 3MF schema validation | 1 |
| Conformal lattices | Lattice cells mapped into a volume by a parameterization | Reports cells with distortion above a bound | Cell distortion Field | 2 |
| Homogenized properties | Effective stiffness per cell type and density from Flux homogenization, stored on the Material | `OutsideEnvelope` for densities outside the calibrated range | Homogenized stiffness against full-resolution simulation | 2 |
| Lattice DfAM | Minimum strut, trapped powder, drainage and inspection access | Typed Check failures with fixes | Seeded defect corpus | 1 |

### Process simulation and compensation

**Decision D-MFG-13:** Distortion compensation is a geometry operation driven by a Field. MFG simulates the build, inverts the displacement Field, and applies it to the Body with `anvil::deform`. It iterates until the predicted as-built shape is within tolerance. *Why:* this uses the contract's "Fields driving geometry" mechanism, works on all four representations, and keeps the design Body untouched. *Rejected:* mesh-only morphing in an export step (breaks associativity and loses the B-rep).

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Inherent strain distortion (PBF) | Layer-lumped strain from calibration coupons, solved elastically in Flux -> displacement and stress Fields | `OutsideEnvelope` outside calibrated machine, material and parameter set | Coupon deflection reproduced; AM-Bench comparison where data exist | 2 |
| Thermo-mechanical simulation (PBF, DED) | Layer or bead activation with temperature-dependent elasto-plasticity in Flux | `OutsideEnvelope` at melt-pool scale, which is out of scope | AM-Bench measured temperature, residual stress and deflection for DED (AMB2025-04) [NIST AM-Bench 2025] | 3 |
| Support and recoater risk | Flags regions where predicted vertical displacement exceeds the recoater clearance | Typed Check failure with fixes | Seeded failure corpus | 2 |
| Compensation | Iterative pre-deformation per D-MFG-13 | `Infeasible` when iterations do not converge; reports the residual | Re-simulated compensated build within tolerance; physical check on a metal PBF build of golden product 2 in phase 2 | 2 |
| Vat cure depth | Working-curve model of cure depth against exposure | `MissingData` without resin constants | AM-Bench cure depth against radiant exposure (AMB2022-09) [NIST AM-Bench 2025] | 2 |
| Binder-jet sintering | Viscous sintering shrinkage and slumping in Flux, with compensation | `OutsideEnvelope` outside calibrated alloys | Measured coupon shrinkage | 4 |
| Extrusion warp | Thermal contraction and layer-adhesion anisotropy | `OutsideEnvelope` for unmodeled materials | Measured warp on calibration parts | 4 |

The inherent strain method is fast but layer-lumped, so it needs per-machine calibration and cannot predict local melt-pool effects [unverified: the primary inherent-strain papers could not be opened]. Melt-pool and microstructure prediction remain outside MFG; the coverage tab owns those models and their envelopes.

### Printer profiles, 3MF and machine connectivity

Printer profiles are packages containing the printer Assembly (build volume, kinematics, heads), process parameter sets with validity envelopes, and material profiles. Calibration programs ship with them: temperature, flow and retraction prints for extrusion, as OrcaSlicer provides [OrcaSlicer], and coupon builds for PBF and vat. Calibrated values record their date, machine serial and uncertainty.

The 3MF specification suite is ISO/IEC 25422:2025 [3MF specifications]. The Toolpath extension was last updated on 17 September 2026, and its repository still describes it as a draft [3MF specifications; 3MF Toolpath].

| Specification | Version in ISO/IEC 25422:2025 | Latest revision | Crucible support | Phase |
| --- | --- | --- | --- | --- |
| Core | 1.3.0 | 1.4.0 | Read and write | 1 |
| Production | 1.1.2 | 1.1.2 | Read and write | 1 |
| Materials and Properties | 1.2.1 | 1.2.1 | Read and write | 1 |
| Beam Lattice | 1.2.0 | 1.2.0 | Read and write | 1 |
| Boolean Operations | 1.1.0 | 1.1.1 | Read and write | 2 |
| Secure Content | 1.0.2 | 1.0.2 | Read and write | 3 |
| Toolpath | Not included | 1.0.0 | Version-gated write | 2 |
| Volumetric | Not included | 0.8.0 | Version-gated write | 3 |

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| 3MF production write | Build items, components, UUIDs, materials, beam lattices, Boolean shapes, thumbnails | Unsupported constructs listed; never dropped silently | Consortium validation tooling; round trip | 1 |
| 3MF Volumetric | Field-defined materials and properties for material jetting and graded parts | Version-gated: written only when the target declares support | Schema validation | 3 |
| 3MF Toolpath | Layered scan or extrusion paths with process profiles | Version-gated as above | Schema validation; re-read equals the internal path | 2 |
| 3MF Secure Content | Encrypted production files for contract manufacturers | Key errors typed | Round trip with test keys | 3 |
| Printer connectivity | Send, start, pause, cancel, monitor through plugins (OctoPrint, Moonraker, PrusaLink, vendor APIs, MTConnect, OPC UA) as `api` actions | Disconnects and rejections reported; never retried without the person's action | Simulated printer endpoints in CI | 1 |

Connectivity runs outside evaluation as `api` actions with network capability, through the same approval path as machining (D-MFG-4). Web Serial is not Baseline and works only in some browsers [MDN Web Serial]. Every platform therefore reaches USB-attached printers through a machine gateway (the desktop app or a headless gateway on the shop network), which keeps features identical.

### Design-for-additive checks

DfAM checks are `require` predicates parameterized by the printer profile, so the same design reports differently for different printers.

| Check | Measures | Default source | Phase |
| --- | --- | --- | --- |
| Minimum wall and detail size | Local thickness Field from `anvil::distance` | Printer profile | 1 |
| Overhang and downskin | Facet angle to build direction, by region | Printer profile critical angle | 1 |
| Trapped powder or resin | Enclosed voids with no drain path | Process category | 1 |
| Drain and escape holes | Hole diameter and count per enclosed volume | Profile minimums | 1 |
| Bridging length | Unsupported spans in extrusion | Printer profile | 1 |
| Thermal mass change | Abrupt cross-section changes along the build direction | Process simulation thresholds | 2 |
| Aspect ratio and slenderness | Thin tall features at risk of recoater collision or vibration | Profile | 2 |
| Support removal access | Line-of-sight and tool access to support contacts | Profile and post-processing tools | 2 |
| Machining allowance | Stock on faces that the downstream process plan finishes | Routing | 2 |

Each failing DfAM check reports the located region, the measured value, the printer limit and ranked fixes. The oracle is a seeded-defect corpus per check, in which every planted defect must be found and no clean region flagged.

## Molding and casting

### Shared approach

Every molding and casting process follows one pattern. Tooling is designed in Ingot as ordinary Parts and Assemblies; the process is simulated as Flux forms; and the results are Fields that drive Checks, compensation and inspection.

**Decision D-MFG-14:** Tooling geometry (cavities, cores, dies, patterns) is derived from the part by Anvil operations and remains associative. A part edit regenerates the tool, and tool-only edits (shutoffs, vents, cooling) are features applied to the derived Body. *Why:* associativity is the main lever against late tooling changes, and it reuses the `Query` regeneration machinery. *Rejected:* exported tool geometry edited separately (breaks the single model).

**Decision D-MFG-15:** Flow and solidification sign-off runs 3D non-isothermal solvers in Flux with immersed free-surface tracking. A thin-wall Hele-Shaw model on a mid-surface serves interactive mode and is valid only inside a declared thickness-ratio envelope. *Why:* 3D handles thick sections, ribs and inertia that Hele-Shaw ignores, while Hele-Shaw answers in seconds for thin-walled parts. *Rejected:* Hele-Shaw only (invalid for thick parts and HPDC inertia); 3D only (too slow for interactive design).

The default envelope for the thin-wall model is local thickness under one tenth of the local flow length. This value is a starting point and is calibrated in phase 3 against the 3D solver [unverified].

### Injection molding: mold design

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Moldability analysis | Part + pull direction -> draft Field, undercut regions, thickness Field, sink-risk Field | Typed Check failures with fixes (add draft, core out, change direction) | Analytic draft on test geometry; seeded undercut corpus | 2 |
| Pull direction | Ranks directions by undercut area and side-action count from visibility analysis | Reports ties | Brute-force visibility on small cases | 2 |
| Parting line and surface | Silhouette edges -> parting line; ruled or extended parting surfaces; shutoff surfaces | `Infeasible` with the open loop and suggested shutoffs | Watertight split of the mold block | 3 |
| Core and cavity split | `split(mold_block, part.scale(shrink), parting) -> (core, cavity)` with anisotropic shrink Field | `ResolveError` when parting surfaces fail to close | Core plus cavity plus part equals the block | 3 |
| Side actions | Slides and lifters per undercut with motion vectors, travel and collision check | `Collision` during opening, with the colliding pair | Opening simulation without collision | 3 |
| Mold base | Standard plates, guides and ejector sets as Catalog parts | `MissingData` for unknown standards | BOM and geometric fit | 3 |
| Gates and runners | Gate type and location, cold-runner layout, hot-runner Catalog parts, runner balancing | `Infeasible` when no gate meets the constraints; reports which ones | Fill imbalance under bound; pressure drop recomputed | 3 |
| Gate location optimization | Wasm component: search over admissible gate regions minimizing fill pressure, weld lines on critical faces and air traps | Returns the Pareto front | Objective values recomputed by Flux | 3 |
| Cooling design | Drilled channels, baffles, bubblers, conformal channels for AM inserts | `Collision` with ejectors or cavity; minimum steel distance violations reported | Steel-distance Field; coolant Reynolds number above the turbulent threshold | 3 |
| Ejection | Ejector pin layout on permitted faces, ejection force from shrinkage on core | `Infeasible` when the force exceeds the pin capacity | Pin stress under the limit | 3 |
| Venting | Vent placement at air-trap locations from fill simulation | None | Every air trap vented or reported | 3 |

### Injection molding: process simulation

Moldflow simulates fill, pack, cool and warp, and lists gas-assisted, injection-compression, co-injection and microcellular molding in Moldflow Insight [Moldflow]. Crucible matches that scope in phases 3 and 4.

| Stage | Physics (Flux forms) | Material model fields | Validity envelope and limits | Phase |
| --- | --- | --- | --- | --- |
| Fill | Generalized Newtonian, non-isothermal flow with free surface | Cross-WLF viscosity, Tait pVT, temperature-dependent conductivity and specific heat, no-flow temperature | Viscoelastic effects (jetting, die swell) out of scope | 3 |
| Pack | Compressible flow with pVT, gate freeze | As above | As above | 3 |
| Cool | Transient conduction in part and mold, coolant convection, cycle-averaged mold temperature | Mold steel and coolant properties | Cycle steady state assumed after a declared number of cycles | 3 |
| Fiber orientation | Folgar-Tucker family with a closure approximation [unverified] | Fiber length, volume fraction, interaction coefficients | Short-fiber only; long-fiber attrition out of scope | 4 |
| Warp | Residual stress from in-cavity cooling and orientation-dependent shrinkage; linear and buckling analysis | Anisotropic thermo-elastic properties | Small-strain linear elastic after ejection | 3 |
| Variants | Gas-assist, co-injection, overmolding, injection-compression, foaming | Additional phases and blowing agents | Each declared separately | 4+ |

Outputs are Fields: fill time, pressure, temperature, frozen layer, weld-line locations, air traps, volumetric shrinkage, sink depth and warp displacement. Warp compensation reuses D-MFG-13: the inverted displacement Field pre-deforms the cavity.

A short shot is a result, reported as an unfilled-region Field with the frozen flow front, not an error. Solver non-convergence returns `Infeasible` with the last converged time. Melt temperatures, shear rates or thicknesses outside a material's calibrated range return `OutsideEnvelope`.

Oracles are analytic Hele-Shaw solutions (center-gated disk, isothermal power-law) and mass conservation within 0.1%. Golden product 5 (molded enclosure) adds physical evidence: its short-shot sequence and measured warp are compared with predictions.

### Die casting

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| HPDC die design | Derived die halves, slides, overflows, vacuum vents, trim die | As injection molding | As injection molding | 4 |
| Shot profile | Slow and fast phase velocities, switch-over, intensification pressure | `OutsideEnvelope` beyond machine capability | Machine record checks | 4 |
| Filling and solidification | 3D turbulent free-surface filling (inertia-dominated), solidification with latent heat | `OutsideEnvelope` for unmodeled alloys | Published HPDC benchmark data [unverified] | 4 |
| Die thermal cycling | Cyclic steady state with spray cooling | Non-convergence reported | Energy balance per cycle | 4 |
| Defect indicators | Air entrapment, cold-shut risk, porosity Fields | None | Comparison with X-ray of golden castings | 4 |

MAGMASOFT covers HPDC, LPDC, permanent mold and investment casting. It also offers autonomous optimization through a virtual design of experiments [MAGMASOFT]. Crucible's design exploration uses the generic optimization and design-of-experiments capabilities of the coverage tab, not a casting-specific optimizer.

### Sand and investment casting

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Pattern and allowances | Part -> pattern with shrinkage, draft and machining-allowance Fields; cores and core prints | Typed Check failures for missing draft or unsupported cores | Pattern minus allowances equals the part | 4 |
| Gating design | Sprue, well, runners and ingates sized from fill time and a pressurization ratio | Reports velocities above the ingate limit | Fill simulation velocities under the limit | 4 |
| Riser design | Modulus method for size, feeding-distance rules for placement, chills | `Infeasible` with the isolated hot spot when no feeding path exists | Solidification simulation shows directional solidification toward risers | 4 |
| Solidification | Enthalpy formulation with fraction-solid curves | `OutsideEnvelope` outside calibrated alloys | Analytic Stefan problem; published plate castings | 4 |
| Porosity prediction | Dimensionless Niyama criterion mapped to shrinkage pore volume fraction [Carlson and Beckermann 2009] | Restricted to the alloys and conditions of the calibrated curves | Published WCB steel plate results [Carlson and Beckermann 2009] | 4 |
| Investment casting | Wax pattern trees, shell model, radiation-dominated cooling in vacuum | `OutsideEnvelope` for directional and single-crystal solidification | Radiation view-factor reciprocity; published cases | 5 |
| Hot tears, residual stress | Thermo-mechanical solidification stress | `OutsideEnvelope` for hot-tear criteria outside calibration | Comparison with measured distortion | 5 |

Carlson and Beckermann validated their dimensionless Niyama method on WCB steel, A356 and AZ91D [Carlson and Beckermann 2009]. Crucible restricts its porosity predictions to calibrated alloys and flags the rest.

### Forging, extrusion and other forming of bulk material

| Process | Capabilities | Physics | Failure behavior and envelope | Oracle | Phase |
| --- | --- | --- | --- | --- | --- |
| Closed-die forging | Preform and die design with flash land, draft and parting; load and die stress | Rigid-viscoplastic FEM with remeshing in Flux; temperature-dependent flow stress | Laps and folds flagged; envelope from flow-stress calibration range | Die fill and load against published forging benchmarks | 5 |
| Aluminum extrusion | Profile DFM (wall ratios, tongue ratios, circumscribing circle), die design with bearings, pockets, portholes and bridges | Arbitrary Lagrangian-Eulerian thermo-mechanical flow | Seam-weld quality out of scope (stated) | Exit velocity uniformity; press-load limit | 5 |
| Thermoforming | Mold design with draft and vents; thickness prediction; trim programs from the machining stack | Membrane hyperelastic or viscoelastic sheet with contact | Envelope from material test range | Thickness against measured parts | 4 |
| Blow molding | Parison programming (extrusion blow); preform design (stretch blow) | Membrane inflation with contact and cooling | As thermoforming | As thermoforming | 5 |
| Rotational molding | Wall-thickness DFM, cycle estimate | Powder deposition by mold-wall temperature history | Simplified deposition model; flagged as indicative | Measured wall thickness | 5 |
| Compression molding | Charge placement, flow, fiber orientation for SMC and BMC | Squeeze flow with fiber orientation | Short-fiber envelope as injection molding | Published SMC panels [unverified] | 5 |

## Forming and joining

### Sheet forming

MEC owns sheet-metal design (flanges, bends, reliefs, flat patterns, bend allowance), and MFG owns how sheet parts are made. AutoForm is the leading sheet-forming suite to match. Its products include DieDesigner, Compensator and Sigma for forming, ProgDie for progressive dies, Tube for tube bending and hydroforming, and an Assembly suite for body-in-white [AutoForm].

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| One-step blank development | Inverse FEM from the formed Part -> blank outline and strain Field | `Infeasible` for non-developable regions beyond strain limits | Published benchmark blanks [unverified] | 3 |
| Formability | Incremental shell FEM in Flux -> thinning, major and minor strain, forming-limit margin Fields | `OutsideEnvelope` outside calibrated material curves | NUMISHEET-style benchmark parts [unverified] | 4 |
| Die face design | Binder, addendum, draw beads, trim and flange lines as Ingot features | `ResolveError` on lost references | Surface continuity checks (G1 or G2 per region) | 4 |
| Stage planning | Draw, trim, flange, restrike, pierce sequence with tonnage | `Infeasible` naming the failing stage | Tonnage recomputed | 4 |
| Progressive die strip layout | Wasm component: station assignment, carrier, pilots and pitch to minimize material and stations | `Infeasible` when a station overloads | Material utilization recomputed; collision-free strip | 4 |
| Springback | Unloading analysis after forming -> displacement Field | `OutsideEnvelope` when the material model lacks kinematic hardening | Published springback benchmarks; measured parts | 4 |
| Springback compensation | D-MFG-13 applied to die faces, iterated to tolerance | Non-convergence reported with the residual | Re-simulated part within tolerance | 4 |
| Robustness | Variation of thickness, material properties and friction -> capability Fields (for example Cpk on thinning) | None | Monte Carlo with seeded generator; reproducible | 5 |
| Tube bending | Rotary-draw sequence (length, rotation, angle), tooling, collision, thinning, ovality, springback | `Collision` or `Infeasible` with fixes (split, re-sequence, increase centerline radius) | Bend simulation; measured tubes | 3 |
| Roll forming | Flower pattern, pass count, roll design, edge-strain check | Edge strain beyond limit reported | Published roll-forming cases [unverified] | 5 |
| Hydroforming | Tube and sheet; pressure and axial feed paths; burst and wrinkle margins | `Infeasible` without a safe process window | Published hydroforming benchmarks [unverified] | 5 |

### Welding

MEC owns weld joint design and symbols. MFG owns weld procedures, sequence, fixtures, robot paths and distortion.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Weld procedure specification | Process, consumable, positions, parameters and preheat per joint; linked to qualification records | `MissingData` for unqualified combinations | Every joint references a qualified procedure | 2 |
| Heat input and bead geometry | Heat input per pass from parameters; pass plan for multi-pass joints | `OutsideEnvelope` outside the qualified range | Pass areas sum to the joint area | 2 |
| Weld sequencing | Wasm component: order and direction of welds to minimize predicted distortion and robot or welder travel | Reports the trade-off front | Distortion recomputed by Flux | 2 |
| Weld distortion, structure scale | Shrinkage-based inherent-strain method on shells or solids in Flux | `OutsideEnvelope` for thick multi-pass joints outside calibration | Golden product 4 measured distortion | 2 |
| Weld distortion, joint scale | Transient thermo-elasto-plastic analysis with a moving volumetric heat source [unverified] | Long run times flagged in interactive mode | Published weld benchmarks [unverified] | 4 |
| Fixture design | Clamps and locators as Assemblies (see Assembly) | As fixtures | As fixtures | 2 |
| Robot weld paths | Seam Bodies -> robot programs with torch angles, weaving and seam tracking (see Robot offline programming) | `Collision`, `Unreachable` | Robot simulation | 3 |

### Mechanical joining and bonding

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Riveting and clinching | Fastener selection, pitch, edge distance, process (solid, blind, self-pierce, clinch, flow-drill screw), tool access | Check failures with fixes | Pitch and edge-distance rules; access check | 3 |
| Adhesive bonding | Bead paths for dispensing, bondline thickness, surface preparation, cure schedule as routing steps | `MissingData` without adhesive data | Bead volume equals the bondline volume | 3 |
| Fastening specification | Tightening method, target torque or angle with scatter, sequence, tool and audit rules derived from MEC's preload requirement | `Infeasible` when the scatter cannot meet the preload range | Preload range from the torque-tension model with friction scatter contains MEC's requirement | 2 |

### Composite layup

MEC owns laminate design: plies, orientations, drop-offs and the structural model. MFG owns how laminates are made. Drone airframes (golden product 6) commonly use carbon-fiber plates or molded shells, so this arrives in phase 4.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Draping | Kinematic (fishnet) draping of each ply on the tool surface -> fiber-angle and shear Fields, plus flat ply patterns | Shear above the material's locking angle flagged with fixes (darts, splits, seed point) | Analytic draping on a hemisphere; flat pattern area balance | 4 |
| Ply nesting and cutting | Flat plies nested with grain constraints by the 2D nesting Wasm component; cutter programs for ply cutters | As nesting | As nesting | 4 |
| Layup sequence and laser projection | Ordered plies with locating data for projectors and work instructions | Missing ply references reported | Every ply placed once, in order | 4 |
| AFP and ATL paths | Fiber-placement courses with steering-radius, gap and overlap limits, posted to the machine | `Infeasible` where steering limits are exceeded | Gap and overlap Fields within limits | 5 |
| Cure cycle | Autoclave or oven cycle with Flux thermo-chemical cure and residual stress for spring-in | `OutsideEnvelope` without resin kinetics | Spring-in on calibration L-sections | 5 |
| Plate machining | Carbon-fiber plates cut by the milling stack with composite-specific tools and dust rules | As machining | As machining | 3 |

The fastening specification maps MEC's required preload range to a shop instruction. Torque control carries a large preload scatter from friction, so the `tightening` function selects torque-angle or yield-controlled tightening when the range is narrow. It states the resulting preload range explicitly.

## Surface and heat treatment

Treatments are typed records attached to faces through Queries, plus routing steps. Each record changes dimensions and properties that downstream Checks read.

```
part.treat(anodize(type: hard, thickness: 50um ± 10um, seal: none))
    .mask(part.faces(threads) + part.face(mating))
part.heat_treat(solution_and_age(spec: shop::t6_6061), inspect: hardness(points: 3))
```

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Coating specification | Process, standard, thickness `Tol`, color, masking Queries, pre-treatment | Unknown standards are `MissingData`; conflicting masks fail | Every treated face has a resolved record | 1 |
| Dimensional effect | Thickness build-up per face as a Field, including growth into the substrate for conversion coatings | `MissingData` without growth ratio | Post-treatment dimensions recomputed; tolerance checks use them | 2 |
| Plating distribution | Primary and secondary current distribution in Flux for electroplating thickness | `OutsideEnvelope` for unmodeled bath chemistry | Analytic parallel-plate and cylinder cases | 4 |
| Paint and powder coat | Film thickness, cure schedule, masking, robot spray paths (offline programming) | As coatings | Film-thickness model against measured panels | 4 |
| Heat-treatment specification | Recipe (temperatures, times, atmosphere, quench) and target property Fields (hardness, case depth) | `OutsideEnvelope` when COV's models do not cover the alloy and recipe | Target properties within COV-predicted bands | 2 |
| Heat-treatment distortion | Quench and transformation distortion from COV models, compensated per D-MFG-13 | As above | Measured distortion on golden parts | 5 |
| Hot isostatic pressing and stress relief for AM | Routing steps with recipes; COV predicts property changes | As above | As above | 3 |

COV owns the physics: phase transformation, diffusion and quench models. MFG owns the specification, the routing step, masking, inspection requirements and dimensional consequences.

## Electronics manufacturing handoff

ELX owns board design: stackup, netlist, placement, routing, design rules and the ECAD-MCAD exchange over IDX V6. MFG owns everything the factory needs to fabricate, assemble and test the board, plus the fab-capability and assembly-line knowledge that DFM and DFA Checks use.

**Decision D-MFG-16:** IPC-2581 revision C is the primary fabrication and assembly package, with Gerber X2 plus drill files as the universal fallback. ODB++ is available only through a licensed translator plugin. *Why:* IPC-2581 is an open, bi-directional standard [IPC-2581], and revision C carries DFX feedback between design and manufacturing [IPC-2581C]. Gerber is the format fabricators most widely accept [unverified], and its specification is current (revision 2024.05) [Ucamco Gerber]. The contract routes proprietary formats through plugins. *Rejected:* Gerber only (no stackup, BOM or DFX feedback); ODB++ as primary (vendor-controlled).

IPC released IPC-2581 revision C on 1 December 2020. It adds bi-directional DFX exchange and support for rigid-flex boards, embedded passive and active parts, cavities, coins, edge plating, counterbores and intended net shorts [IPC-2581C]. Ucamco's current Gerber specification is revision 2024.05 [Ucamco Gerber].

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Fabrication outputs | Board model -> IPC-2581C, Gerber X2 layers, drill and route files, fabrication drawing, impedance and stackup tables | Unsupported constructs listed per output; never dropped silently | Re-import into an independent viewer; layer-by-layer XOR against the board model is empty | 3 |
| Assembly outputs | Placement (centroid) data, assembly BOM with approved manufacturers, polarity and rotation conventions per line, assembly drawings | `MissingData` for parts without a rotation convention | Placement re-derived from the 3D Assembly matches within 0.01 mm and 0.1 deg | 3 |
| Panelization | Boards -> panel with rails, tabs, mouse bites or V-score, fiducials and tooling holes, using the 2D nesting Wasm component for mixed panels | `Infeasible` when the panel exceeds line limits | Panel rules checked; depanelization stress check on parts near break lines (Flux) | 3 |
| Stencil design | Paste layer -> apertures with area-ratio checks, step stencils, home-plate and window-pane reductions | Reports apertures below the area-ratio limit | Area ratio recomputed for every aperture | 3 |
| Fab DFM | Annular ring, trace and space, drill-to-copper, mask slivers, acid traps, copper balance, aspect ratio, against a fabricator capability profile | Check failures located on the board with fixes; feedback returned as IPC-2581C DFX records | Seeded-defect boards; every planted defect found | 3 |
| Assembly DFA | Part spacing by package class, fiducials, polarity marks, tombstoning risk from pad asymmetry, thermal relief, via-in-pad, wave-solder shadowing, rework access | As above | As above | 3 |
| Test programs | Test-point coverage, flying-probe and bed-of-nails fixture data, boundary-scan hand-off | Reports untestable nets | Coverage recomputed from the netlist | 4 |
| Reflow profile specification | Profile limits from paste and part ratings; thermal simulation of the populated board in Flux for large thermal masses | `OutsideEnvelope` without part ratings | Profile inside every part's rating | 4 |
| Box build | Board Instances inside the product Assembly feed assembly planning and work instructions | As Assembly | As Assembly | 3 |

Fabricator and assembly-line capability profiles are dated data packages. A board passes DFM for a specific fabricator, never in the abstract.

## Assembly

### Sequence planning

Tian and colleagues plan assembly by disassembly with physics simulation. Their method generalizes to screws and puzzles, and it solves 80-part assemblies in several minutes [Tian et al. 2022].

**Decision D-MFG-17:** Assembly sequence planning is disassembly search over continuous collision-free motions: translations, screw motions and short compound paths. Gravity stability of each sub-assembly is checked with Flux rigid-body contact, and the output is an AND/OR precedence graph. *Why:* disassembly from the final state handles tight clearances and fasteners that forward planning misses. One graph also feeds line balancing, work instructions, repairability and recyclability. *Rejected:* direction-cone heuristics only (fail on screws and interlocking parts); hand-entered precedence (not regenerated from geometry).

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Disassembly paths | `disassemble(assembly, seed, budget) -> PrecedenceGraph` with a removal motion per Instance | `Infeasible` listing interlocked Instances and the blocking pairs; fix: split a part, add clearance or change the joint | Every motion replayed with continuous collision detection | 2 |
| Sequence optimization | Picks a linear or parallel sequence minimizing reorientations, tool changes and unstable states | Reports infeasible constraints | Optimum on small instances by exhaustive search | 2 |
| Fastening steps | Fasteners and their tightening specifications become steps with tool and torque | `MissingData` without specifications | Every fastener appears in exactly one step | 2 |
| Tool and hand access | Swept volumes of tools and hands at each step | `Unreachable` with the step and fixes | Access volume collision-free | 3 |

### Design-for-assembly analysis

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Part-count analysis | `dfa(assembly) -> DfaReport`: for each Instance, whether it must be separate (relative motion, different material, service access), with candidates for consolidation | Instances without material or motion data are listed as undetermined, never as consolidatable | Seeded assemblies with known minimum part counts | 2 |
| Handling and insertion estimate | Times per Instance from size, symmetry, weight, fastening method and access, using calibratable tables in the tradition of Boothroyd and Dewhurst [unverified] | `MissingData` when a table lacks the case | Times trace to table rows; totals recomputed | 2 |
| Design-efficiency index | Theoretical minimum time over estimated total, with each factor's contribution shown | None | Index recomputed from the report | 2 |

### 3D work instructions

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Instruction generation | Precedence graph + routing -> ordered steps with exploded views, motion animations, tools, torques, Checks and safety notes | Steps without a view are reported | Every MBOM item consumed in some step; every step resolves to Instances | 2 |
| Output formats | glTF 2.0 scenes with an accessible HTML viewer and PDF for print; OpenUSD scenes from phase 3 | None | Schema validation; accessibility checks on the HTML | 2 |
| Live linkage | Instructions regenerate on design change; released instructions are immutable and versioned with the MBOM | Changed steps highlighted for review | Diff of unchanged designs is empty | 2 |
| Localization | Text in Ingot string tables, translated per locale | Missing translations reported | Coverage per locale | 3 |

### Line balancing

The branch, bound and remember (BB&R) algorithm solves all 269 instances of the combined Hoffmann, Talbot and Scholl benchmarks to proven optimality [BB&R]. It averages under half a second per problem, where the previous best method solved 257 instances [BB&R].

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Simple line balancing | Tasks, times and precedence -> stations minimizing count for a takt time, or takt for a station count | `Infeasible` when one task exceeds takt | Optimal on all 269 benchmark instances (target, matching BB&R) | 3 |
| Mixed-model and practical constraints | Zoning, resources, operator skills, two-sided lines, mixed models | `Infeasible` with the binding constraints | Feasibility checker; lower bounds reported with the gap | 4 |
| Times | Task times from motion standards data packages or measured data, with uncertainty | `MissingData` | Times trace to a source | 3 |

### Robot offline programming

Robots are Machines: serial-link Assemblies with kinematic mates, joint limits and controller records. They share forward kinematics, inverse kinematics, collision detection and post-processing with machine tools.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Targets and paths | Weld seams, glue beads, spray paths, pick-and-place poses and machining paths -> robot targets with tool frames | `Unreachable` with the pose and fixes (move base, add positioner, change approach) | `fk(ik(p)) == p` within tolerance | 3 |
| Redundancy resolution | External axes, tracks and positioners coordinated by optimization over a declared objective (joint-limit distance, singularity distance, stiffness for robot machining) | `Infeasible` with the binding constraint | Objective recomputed; continuity along the path | 3 |
| Motion planning | Collision-free point-to-point motion in the cell with a sampling planner on a counter-based seed | `BudgetExhausted` with the best partial plan | Replayed path collision-free | 3 |
| Robot posts | Wasm component posts to vendor languages (ABB RAPID, KUKA KRL, FANUC TP, Yaskawa INFORM, Universal Robots URScript) [unverified] | `Unsupported` per instruction | Re-interpreter per language reproduces the motion | 3 |
| Cycle time | Kinematic simulation with vendor-calibrated accelerations | None | Within 10% of measured after calibration (target) | 3 |

### Fixture and jig design

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Locating analysis | Locator contacts -> form-closure and determinacy check (rank of the contact wrench matrix) | `Infeasible` naming the unconstrained motions; fix: add or move locators | Rank test against analytic 3-2-1 cases | 2 |
| Clamping | Clamp positions and forces resisting cutting or welding loads with friction, checked against part deflection in Flux | Reports slip or deflection above tolerance | Static equilibrium; deflection within tolerance | 3 |
| Modular fixtures | Plates, locators and clamps as Catalog parts placed on a grid | `Collision` with toolpaths | Toolpath collision check including the fixture | 2 |
| Soft jaws and nests | Jaw Bodies derived from the part (offset pocket with clearance) and machined by their own program | As machining | Part seated without interference | 2 |
| Weld and assembly jigs | Locators and clamps for multi-part Assemblies with access for tools and torches | `Unreachable` for blocked seams | Access check | 2 |

## Inspection and quality

MEC owns GD&T semantics and tolerance analysis. MFG owns how characteristics are measured, evaluated, reported and controlled in production.

### Inspection planning and CMM programming

QIF is ISO 23952:2020, which ISO reviewed and confirmed in 2026 [ISO 23952]. QIF carries plans, results, rules, resources and statistics, all linked to model-based definition [unverified for the part list]. DMIS remains the most common CMM program language [unverified].

**Decision D-MFG-18:** Characteristics are first-class records generated from the design's GD&T, each with a stable identity derived from provenance. The inspection plan, CMM program, results, SPC, FAI and PPAP all reference those identities. *Why:* one identity per characteristic lets a design diff compute exactly which characteristics changed, which drives partial first-article inspection and re-validation. *Rejected:* balloon numbers as identity (renumbering breaks traceability); documents as the source of truth (they drift from the model).

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Characteristic extraction | Design -> characteristics (dimensions, GD&T controls, notes, special characteristics) with balloons | Characteristics MEC cannot resolve are reported | Every GD&T control yields one characteristic | 2 |
| Method selection | Per characteristic: CMM, gauge, scan, vision or functional test, by uncertainty ratio to tolerance | `Infeasible` when no available method meets the ratio | Uncertainty ratio recomputed | 3 |
| Sampling strategy | Point count and distribution per measured face or feature of size, for a target evaluation uncertainty | None | Simulated evaluation uncertainty within target | 3 |
| Probe path planning | Collision-free CMM paths with articulating heads, stylus selection and alignment routines | `Unreachable` points with fixes (another stylus, orientation or setup) | Collision check on the CMM model | 3 |
| Program output | DMIS and QIF Plans; on-machine probing through the machining posts | `Unsupported` per construct | Re-interpretation of the program | 3 |
| Results import | QIF Results and DMIS output -> measured values and point clouds on the characteristics | Unmatched results reported | Round trip of the public QIF samples | 3 |
| Evaluation | Associated features (least squares, minimum zone, maximum inscribed, minimum circumscribed) and datum reference frames | `OutsideEnvelope` for insufficient point coverage | Reference data sets for fitting algorithms in the style of ISO 10360-6 [unverified] | 3 |

### Scan-to-CAD deviation

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Registration | Point cloud or mesh -> Transform by robust iterative closest point, best fit, or datum-constrained alignment per the drawing's datum reference frame | Non-convergence reported with the residual | Synthetic scans with known transforms and noise recovered within tolerance | 2 |
| Deviation Field | Signed distance from scan to design as a Field on the design faces, with scanner uncertainty | Coverage gaps reported as regions | Analytic offsets of known bodies | 2 |
| Tolerance evaluation on scans | Profile, flatness and position from scan data per characteristic | `OutsideEnvelope` for sparse coverage | As evaluation above | 3 |

### Statistical process control

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Control charts | X-bar and R, X-bar and S, individuals and moving range, p, np, c, u, EWMA, CUSUM per characteristic | `MissingData` below the minimum subgroup count | Published worked examples reproduced exactly | 3 |
| Run rules | Configurable out-of-control rules as data | None | Synthetic sequences trigger exactly the expected rules | 3 |
| Capability | Cp, Cpk, Pp, Ppk with confidence intervals; non-normal capability by declared distribution fits | Normality assumption tested and reported | Reference datasets | 3 |
| Feedback | Out-of-control signals become typed events linked to the machine, program and tool used | None | Event replay | 4 |

### First-article inspection and PPAP

The IAQG summary of 9102 revision C changes (dated 11 July 2023) states that FAI is not a product acceptance document. It requires a separate FAI for each item and removes the unique single-run production order exemption. Form 1 requires the FAIR identifier, a reason for full or partial FAI, and a "FAIR Verified By" field; Forms 2 and 3 drop their signature fields [IAQG 9102C].

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| AS9102 Form 1 | Part number accountability from the `repo` BOM, with the reason for full or partial FAI | Missing fields block the report | Field-by-field schema check against revision C | 3 |
| AS9102 Form 2 | Raw material, special processes and functional tests from routing records and supplier certificates | `MissingData` per uncertified process | Every special process in the routing has evidence | 3 |
| AS9102 Form 3 | Design characteristics with results from QIF Results, recording the software used | Unmeasured characteristics block the report | Every characteristic has one result or one documented reason | 3 |
| Partial FAI scope | Design diff -> characteristics invalidated by the change, through D-MFG-18 identities | Ambiguous changes listed for a person to decide | Seeded design changes produce the expected scope | 3 |
| PPAP | Submission package with process flow (from routing), PFMEA and control plan links, MSA, dimensional results, capability studies, material results and the part submission warrant [unverified for element list] | Missing elements listed against the requested submission level | Element completeness check | 4 |
| PFMEA and control plan | Failure modes per routing step with controls linked to characteristics and inspection methods | Uncontrolled special characteristics reported | Every special characteristic has a control | 4 |
| Nonconformance | Nonconformance reports linked to serials, characteristics and dispositions | None | Traceability queries | 3 |

### Measurement uncertainty

The GUM is JCGM 100:2008, and its Amendment 1 (2026) addresses nonlinear measurement models [BIPM JCGM]. Supplement 1 (JCGM 101:2008) propagates distributions by Monte Carlo, Supplement 2 (JCGM 102:2011) extends to multiple outputs, and JCGM 106:2012 covers conformity assessment [BIPM JCGM].

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Uncertainty budgets | Typed budgets: input quantities, distributions, sensitivity coefficients and correlations | Unit mismatches fail to compile | Published worked examples reproduced | 2 |
| Linear propagation | Law of propagation with sensitivities from Flux algorithmic differentiation | Flags nonlinearity when the second-order term exceeds a threshold | Agreement with Monte Carlo on linear cases | 2 |
| Monte Carlo propagation | JCGM 101 with adaptive trial count and a counter-based seeded generator | `BudgetExhausted` with the achieved numerical tolerance | Reproducible results; JCGM 101 examples | 3 |
| Decision rules | Guard-banded acceptance per JCGM 106 with stated producer and consumer risk | None | Analytic risk cases | 3 |
| Task-specific CMM uncertainty | Virtual CMM Monte Carlo over the probe path with machine and probe error models | `MissingData` without error models | Comparison with calibrated artifacts | 4 |

## Cost

### Should-cost models

aPriori estimates cost, cycle time and CO2e from CAD geometry with physics-based process models across machining, casting, sheet metal, forging, molding, additive, finishing and electronics [aPriori]. Crucible instead costs the actual process plan, with its real toolpaths, cycle times, nests and molds. It falls back to geometric proxies only where no plan exists yet.

**Decision D-MFG-19:** Cost is a typed roll-up over the process plan, carried as `Money<C>` (a decimal amount in ISO 4217 currency `C`) with a price date and an uncertainty interval, and painted on Bodies as cost-density Fields. Currency is not a physical dimension, so `Money` is a plain value rather than a `Quantity<D>`. Each estimate states its fidelity: `parametric` (from geometric attributes), `planned` (from generated routings) or `quoted` (from a supplier). *Why:* one mechanism serves every process and makes the estimate's basis visible. Cost painted on faces shows designers which features drive it. *Rejected:* a separate costing database (drifts from the design); single-number estimates (hide uncertainty).

| Cost element | Source in the plan | Phase |
| --- | --- | --- |
| Material | Stock or blank Body volume times density times price, plus scrap from nests and gating yield | 1 |
| Machine time | Simulated cycle time per workingstep times machine-hour rate | 1 |
| Setup | Setups and tool changes from the program, times setup rates, divided by batch size | 1 |
| Tooling amortization | Tooling Bodies (molds, dies, fixtures) costed by their own plans, divided by tool life or program volume | 3 |
| Labor | Routing step times from work instructions and line balance | 2 |
| Consumables and energy | Tool wear, gas, powder refresh, electricity from machine power profiles | 2 |
| Overhead and margin | Declared rates per work center or supplier | 1 |
| Logistics and duties | Weight, volume, routes and duty tables from dated data packages | 4 |

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Per-process cost model | `should_cost(part, routing, rates, qty) -> Cost` (a record with `Money` per cost element, a total with its interval, and a cost-density Field) | `MissingData` for unknown rates; never a default price without a flag | Hand-computed reference parts per process | 1 (machining, AM), 2 (sheet, weld), 3 (molding), 4 (others) |
| Parametric early cost | Regressions on geometric attributes per process family, with stated training data and error | `OutsideEnvelope` outside the training range | Held-out quotes; error within the stated interval for 90% of parts (target) | 2 |
| BOM roll-up | `repo` BOM query, multiplying per-item cost by quantity per assembly, plus assembly labor | Items without cost listed; totals marked incomplete | Roll-up equals the sum of parts plus assembly | 1 |
| Volume curves | Cost per unit against quantity, including tooling breakpoints between processes | None | Curves pass through the computed points | 2 |
| Target costing | Target cost allocated down the BOM as Checks; gaps painted on the Assembly | Check failures name the largest contributors | Allocation sums to the target | 2 |
| Quoting plugins | Wasm components or `api` actions that submit a released technical data package to supplier services and return quotes as dated data packages | Network and rejection errors typed; never inside evaluation | Mock supplier endpoints in CI | 2 |
| Currency | Exchange rates as dated data packages; no implicit conversion | `Money<Eur> + Money<Usd>` without an explicit, dated rate fails to compile | Unit tests | 1 |

## Sourcing and supply chain

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Supplier capability records | Processes, machine envelopes, materials, tolerances, certifications (AS9100, IATF 16949, ISO 13485), capacity and lead times as signed, dated data packages | Expired certifications flagged | Schema validation; signature check | 2 |
| Capability matching | Part plan -> suppliers whose capabilities cover every routing step and tolerance | Lists the unmet requirement per supplier | Seeded mismatches detected | 2 |
| Make-or-buy | Compares internal planned cost and capacity with supplier quotes, including risk and lead time, under a declared objective | Reports when data are missing on either side | Decision recomputed from inputs | 3 |
| Lead time | Routing time plus queue and transport from data packages, as an interval | `MissingData` | Comparison with as-run history (factory feedback) | 3 |
| Alternates | Approved alternates for Catalog parts and suppliers, with form-fit-function Checks from MEC and ELX | Unchecked alternates cannot be approved | Checks pass for each approved alternate | 2 |
| Risk | Single-source items, geographic concentration, lifecycle status (obsolescence), compliance status, combined into a risk score per BOM line and painted as a per-Instance Field on the Assembly | Unknown data scores as unknown, never as low risk | Score recomputed; seeded risks surfaced | 3 |

Supplier, price and lifecycle data change daily, but evaluation must be deterministic. These data therefore enter only as dated snapshots (D-MFG-3, rule 5). Proposal review shows when a decision depended on a snapshot older than a declared age.

## Factory connection and digital twin

### Machine and MES connectivity

MTConnect 2.5.0 is the latest version found in this round; its Part 1 was prepared on 5 January 2026 [MTConnect 2.5]. Its REST API is read-only and does not produce side effects on the agent or the equipment [MTConnect 2.5].

OPC 40501-1, OPC UA for Machine Tools Part 1 (machine monitoring and job management), is at release 1.02.0 of 1 November 2024 [OPC 40501-1]. The async-opcua crate is an MPL-2.0 OPC UA client and server in Rust [async-opcua].

**Decision D-MFG-20:** Machine data enter through two native adapters, MTConnect (read) and OPC UA (read, plus write where the companion specification and the site allow), both running outside evaluation as `api` actions or gateway services. Collected data become immutable, signed data packages in CAS that evaluation can read. *Why:* both are open standards with published information models [MTConnect 2.5; OPC 40501-1], and snapshotting keeps evaluation deterministic. *Rejected:* vendor-specific protocols in the core (proprietary formats are plugins); live data inside evaluation (breaks determinism).

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| MTConnect adapter | Probe, current, sample and asset requests -> typed observations mapped to Machine axes, spindles, programs and tools | Schema-version mismatches reported; partial data marked | Conformance against the reference agent with recorded streams | 3 |
| OPC UA adapter | Machine Tools and Machinery companion information models -> the same typed observations; the specification's production jobs map to routing steps of a work order (not to Kiln Ops), and are written only where allowed | Security-policy failures typed; writes need approval like program transfer | Interop with reference servers in CI | 3 |
| Program transfer | Released programs to controllers, bound to the approval hash: signed file export first, then DNC, OPC UA and vendor plugins | Hash mismatch blocks transfer | End-to-end test against controller simulators | 1 (file export), 3 (DNC, OPC UA) |
| MES integration | Work orders, routings, routing-step status, scrap and labor bookings over OPC UA or REST plugins | Mapping errors reported per field | Round trip with mock MES endpoints | 4 |
| Gateway | Headless gateway on the shop network for machines, printers and CMMs; buffers data when offline | Gaps recorded explicitly | Replay tests | 1 |

### MBOM and routings

`repo` owns the MBOM view. MFG writes routings: ordered steps over work centers, each with its program, instructions, inspection, tooling, consumed items and times. A routing step references Instances in the MBOM, never copies of them.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| EBOM to MBOM | Restructuring rules (phantoms, kits, sub-assemblies by station, consumables) as Ingot functions over the EBOM query | Unconsumed EBOM items reported | Every EBOM item consumed exactly once | 2 |
| Routing generation | Process plans -> routing steps with times and work centers | `MissingData` for unmapped work centers | Times trace to programs or standards | 2 |
| Change impact | Engineering change -> affected routings, programs, tools, fixtures, instructions and inspection characteristics | None | Seeded changes produce the expected impact sets | 2 |
| Effectivity | Serial- and date-based effectivity on routing versions | Overlapping effectivity rejected | Unique routing per serial | 3 |

### OpenUSD export for factory simulation

AOUSD announced OpenUSD Core Specification 1.0 on 17 December 2025. It describes this as the first step toward ISO standardization, with Geometry, Materials and Physics specifications in development and Core 1.1 planned for 2026 [AOUSD Core 1.0].

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Cell and line export | Machines, robots, fixtures, conveyors, products and work-in-progress as USD layers with kinematic joints and stable prim paths derived from EntityIds | Unsupported schema constructs listed | Validation with the Core 1.0 compliance tools; round trip of transforms | 3 |
| Process animation | Toolpaths, robot programs and assembly sequences as time-sampled animation | None | Animation replays the simulated motion within tolerance | 3 |
| Incremental updates | A design or plan change edits only the affected layers | None | Unchanged prims keep identical content | 4 |

USD is an export target for factory and logistics simulators. Crucible's own model remains the source of truth (principle 7).

### As-built versus as-designed

[[DIAGRAM: Factory feedback loop. Boxes: Released design and plans in repo (as-planned) -> Machine gateway (MTConnect, OPC UA) -> Signed data package in CAS (as-run) and Inspection results via QIF (as-measured) -> Comparison per serial (deviation Fields, cycle-time and tool-life residuals) -> Calibration Proposal (data package change with held-out error before and after) -> Human approval -> Updated cutting data, distortion calibration and cost rates -> next evaluation. Side arrow from the comparison box to Nonconformance and SPC events.]]

The digital twin is the design plus three record streams keyed by serial number. They are as-planned (released routings and programs), as-run (machine data, tool changes, alarms, times) and as-measured (inspection results, scans).

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| As-built record | Per serial: consumed lots and serials, routing versions, programs by hash, operators, deviations and nonconformances, measurements | Gaps flagged; never back-filled with nominal values | Traceability queries return complete genealogy for test serials | 3 |
| Deviation Fields | Measured deviation per serial as a Field on the design | Coverage gaps reported | As scan-to-CAD | 3 |
| Model calibration | As-run data update model parameters (cutting coefficients, cycle-time factors, distortion calibration) through proposals with evidence | Updates outside declared bounds need human approval | Calibrated models predict held-out runs better than before; otherwise rejected | 4 |
| Product twin export | As-built Assembly with measured Fields for FMI or SSP co-simulation via Flux | Missing measurements fall back to nominal with an explicit flag | Export validation | 5 |

Calibration never edits a model silently. It opens a Proposal that changes a data package, with before-and-after prediction error on held-out data.

## Sustainability and compliance

### Life-cycle assessment

ISO 14044:2006, amended in 2017 and 2020 and confirmed in 2022, sets LCA requirements [ISO 14044]; ISO 14040 sets its principles and framework [unverified for current edition]. MFG computes the cradle-to-gate inventory directly from the process plan, and the end-of-life stage from the disassembly graph.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Goal and scope | Typed functional unit, system boundary and allocation rules per study | Missing scope elements fail to compile | Schema check | 3 |
| Inventory from plans | Material masses, energy from machine power profiles over simulated cycle time, consumables, scrap, transport -> inventory flows | Flows without factors reported, never zeroed | Mass balance per routing step | 3 |
| Impact assessment | Characterization with versioned factor datasets as data packages (for example EF 3.1 or ecoinvent under license) [unverified for current versions] | Unlicensed datasets unavailable; never substituted silently | Reference product systems reproduced | 3 |
| Embodied carbon | Global warming potential per BOM line, painted as a per-Instance Field on the Assembly and a density Field on Bodies; supplier-specific data override generic factors when provided | Uncertainty reported; generic versus specific flagged | Roll-up equals the sum | 2 |
| Hotspots | Contribution analysis by part, process and flow | None | Contributions sum to the total | 3 |
| Uncertainty | Monte Carlo over factor and inventory uncertainty | As Monte Carlo | Reproducible results | 4 |

### Recyclability and circularity

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Recoverable mass | `recyclability(assembly, streams) -> Report` with recoverable mass fraction per recycling stream, from the disassembly graph (D-MFG-17), joining methods and material compatibility tables (data packages) | Materials absent from the tables count as unrecoverable and are listed | Mass balance: streams plus losses equal the product mass | 3 |
| Contaminating joints | Adhesives, incompatible coatings and molded-in inserts that block separation, located on the Assembly | None | Seeded assemblies | 3 |
| Repairability | Disassembly depth and time to reach each declared service part, and the tools needed | `Unreachable` when no disassembly path reaches the part | Paths replayed with collision detection | 3 |

### EU Digital Product Passport

The Ecodesign for Sustainable Products Regulation, (EU) 2024/1781, has been in force since 18 July 2024 [EU ESPR]. Implementing Regulation (EU) 2026/1778, adopted 16 July 2026, governs the passport registry, which became operational on 20 July 2026 [Renoon DPP updates; Transition Pathways DPP]. The registry stores unique identifiers and registration data, supports passport discovery, and does not store passport content [Renoon DPP updates].

CEN and CENELEC have published all eight harmonized DPP standards [Renoon DPP updates]. Six were referenced through Implementing Decision (EU) 2026/1736, and EN 18239 and EN 18246 were expected to follow in September 2026 [Renoon DPP updates]. The ESPR ban on destroying unsold textiles and footwear concerns inventory and retail, so it stays outside MFG [EU ESPR].

The indicative timeline puts the first product delegated act, for iron and steel, in Q4 2026 [Renoon delegated acts]. Textiles, aluminium and tyres follow in Q3 to Q4 2027, furniture in 2028, and mattresses and ICT products in 2029 [Renoon delegated acts]. Requirements generally apply at least 18 months after adoption [Renoon delegated acts].

The battery passport under Regulation (EU) 2023/1542 becomes mandatory on 18 February 2027 for light-means-of-transport batteries, industrial batteries above 2 kWh and EV batteries [Renoon DPP updates].

**Decision D-MFG-21:** The Digital Product Passport is generated from the released model, as-built records and LCA. Each delegated act is a versioned data package that maps Crucible queries to the required data elements. Passports are published by `api` actions to the operator's chosen passport service, never from evaluation. *Why:* requirements differ per product group and keep changing, so the mapping must be data, while content must trace to the model. *Rejected:* one hard-coded passport schema (wrong for every product group); manual passport forms (drift from the product).

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Data mapping | Delegated-act package -> required elements mapped to queries over the model, BOM, LCA and as-built records | Unmapped elements block publication with a list | Every required element mapped or explicitly not applicable with a reason | 3 |
| Identifiers and data carriers | Unique product identifier per model, batch or item as the act requires; QR or other carrier generation | Identifier scheme conflicts reported | Carrier decodes to the identifier | 3 |
| Access tiers | Public, professional and authority views per act | Unauthorized fields never published | Field-level access tests | 3 |
| Registry registration | Registration via the Commission's API as an `api` action, storing the electronic proof of registration [Transition Pathways DPP; LexisNexis DPP] | Rejections typed and logged | Test environment round trip | 3 |
| Battery passport | Battery Regulation data elements for golden product 6's pack where in scope | As above | As above | 4 |

The eight EN standard numbers other than EN 18239 and EN 18246 were not verified in this round [unverified].

### RoHS, REACH and conflict minerals

| Regime | What is checked | Data source | Failure behavior | Phase |
| --- | --- | --- | --- | --- |
| RoHS (2011/65/EU, Annex II as amended by (EU) 2015/863) | Ten restricted substances [EU RoHS], checked per homogeneous material against the Annex II maximum concentration values and applicable exemptions [unverified for values] | Material declarations (IPC-1752A style [unverified]) on Materials and Catalog parts | Non-compliant or undeclared materials named with the part and substance | 2 |
| REACH (EC 1907/2006) | Candidate List substances above 0.1% w/w in articles, Annex XVII restrictions, communication duties [unverified for threshold text] | ECHA Candidate List as a dated data package | Unknown content reported as unknown, never as compliant | 2 |
| SCIP notification | Article data for SVHC-containing articles | As above | Missing data listed | 3 |
| Conflict minerals (EU 2017/821) | Tin, tantalum, tungsten and gold sources, with smelter lists and OECD five-step due-diligence evidence [EU conflict minerals] | Supplier declarations | Undeclared 3TG content flagged | 3 |
| Other regimes | Packaging, batteries, WEEE marking, US TSCA, California Proposition 65 [unverified] | Regime packages | As above | 4 |

The oracle for every regime is a set of seeded BOMs with planted restricted substances, missing declarations and undeclared 3TG content. Every planted case must be reported with the part, material and rule.

The ECHA Candidate List page showed about 50 rows with a latest entry dated 27 June 2024 when fetched, which suggests the page display was incomplete [ECHA Candidate List]. Crucible therefore never hard-codes the list. It ingests the published list as a dated data package and reports its date in every compliance result.

Compliance results are Checks over the BOM. A release fails when a required declaration is missing, unless a person records a time-bounded waiver in the change order.

## State of the art

All numeric goals in the last column are targets.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Adaptive clearing | Constant-engagement paths; parameter-varied trochoids [Li et al. 2025] | Mastercam Dynamic, Fusion adaptive, hyperMILL, NX [unverified: vendor pages not opened] | Medial-axis-seeded, stock-measured engagement control (D-MFG-7); FTO review of US 9,164,503 | Public pocket corpus: cycle time at equal maximum engagement within 3% of the best commercial result; zero engagement-bound violations |
| 3-axis finishing kernels | Drop-cutter and push-cutter (OpenCAMLib) [OpenCAMLib] | ModuleWorks 3-axis library [ModuleWorks] | Native Anvil `tool_drop` and `tool_push` on exact B-rep | Scallop and gouge error against analytic surfaces; throughput at least that of OpenCAMLib on the same machine |
| 5-axis strategies and collision | Collision-aware tilt with continuous collision detection | ModuleWorks 5-axis, used by more than 60% of leading CAM vendors [ModuleWorks] | Conservative-advancement collision on BVHs; tilt optimization | Seeded crash corpus: 100% detection, zero false negatives; run time per 1,000 blocks |
| Material removal simulation | Adaptive tri-dexel on GPU [Ozcan et al. 2024] | VERICUT, ModuleWorks GPU Simulation [unverified for VERICUT] | Narrow-band implicit stock (D-MFG-6) plus GPU tri-dexel render cache | Volume error against exact Booleans; 60 fps scrubbing on a 1-million-block program on the reference laptop |
| Feeds and speeds | Mechanistic force models with constraint-based optimization | CloudNC Cutting Parameters [CloudNC CAM Assist]; VERICUT Force [unverified] | Mechanistic models with calibrated, uncertainty-tagged coefficients | Cycle time within 5% of the leader with zero constraint violations on the shared benchmark |
| Chatter stability | Zero-order, multi-frequency and semi-discretization [Altintas et al. 2008] | CUTPRO [Altintas et al. 2008] | Zero-order interactive, semi-discretization sign-off (D-MFG-10) | Agreement with published lobes; time-domain reference |
| Post-processing | Controller-specific, configurable posts | NX Post Configurator, ModuleWorks Post Processor Framework [ModuleWorks] | Canonical ISO 14649 form, capability-flag posts (D-MFG-5) | Re-interpretation oracle; controller conformance corpora |
| Machining-target recognition | Panoptic graph segmentation on B-rep [FeatureFox] | AAGNet [FeatureFox] | Design semantics first; rule plus learned recognizer for imports | MFInstSeg PQ at least 97%; PQ above 0.9 with 250 training parts |
| AI-assisted programming | Strategy proposals with human review | CloudNC CAM Assist [CloudNC CAM Assist]; NX AI suggestions [Janus NX 2606] | Agents write Ingot on branches; human approval bound to hashes (D-MFG-4) | Share of agent proposals approved without edits on held-out parts; zero oracle bypasses |
| 2D nesting | Sparrow: feasibility sequence plus guided local search [Gardeyn et al. 2025] | Sparrow (MIT) and jagua-rs (MPL-2.0) | Adopt with deterministic budgets (D-MFG-9) | ESICUP and GARDEYN instances: within 1 point of sparrow's expected density at equal work |
| 3D packing | FFT spectral packing, interlock-free [Cui et al. 2023] | Netfabb [Cui et al. 2023]; Materialise Magics Nester [Materialise Magics] | Spectral packing with exact integer collision counts (D-MFG-12) | Thingi10K benchmark: within 2 points of published density at equal or lower GPU time |
| Variable-width perimeters | Adaptive bead-width framework [Kuipers et al. 2020] | PrusaSlicer, OrcaSlicer, CuraEngine (AGPL, reference only) | Clean-room implementation of the paper | Over- and under-fill on a thin-wall corpus no worse than the reference slicers |
| Multi-axis slicing | Quaternion-field curved layers [Zhang et al. 2022] | Research code [unverified] | Adopt in phase 4 | Support-free coverage and collision-free order on the paper's models |
| PBF distortion | Inherent strain (fast) and layer thermo-mechanics (sign-off) [unverified] | Materialise Magics with Ansys simulation [Materialise Magics]; Fusion print simulation [Fusion Manufacturing Extension] | Both, via Flux, with Field-driven compensation (D-MFG-13) | AM-Bench data where available [NIST AM-Bench 2025]; residual after compensation under 0.1 mm on golden product 2 |
| Injection molding | 3D non-isothermal flow with pVT; Hele-Shaw for thin walls | Moldflow [Moldflow] | Both, by validity envelope (D-MFG-15) | Analytic cases; golden product 5 short shots and warp within 20% of measured |
| Casting | Filling, solidification, dimensionless Niyama porosity [Carlson and Beckermann 2009] | MAGMASOFT [MAGMASOFT] | Flux solidification plus dimensionless Niyama, calibrated alloys only | Published WCB plate porosity; Stefan problem |
| Sheet forming and springback | Incremental shell FEM with compensation | AutoForm [AutoForm] | Flux shells plus Field-driven compensation | Published springback benchmarks [unverified] |
| Assembly planning | Physics-based assembly by disassembly [Tian et al. 2022] | Same (research) | Adopt with deterministic search (D-MFG-17) | Success rate on the paper's benchmark at least equal; 80-part assemblies in under 5 minutes |
| Line balancing | BB&R exact algorithm [BB&R] | BB&R | Adopt | All 269 benchmark instances optimal, mean under 1 s |
| Measurement uncertainty | GUM, JCGM 101 Monte Carlo [BIPM JCGM] | Commercial virtual CMMs [unverified] | Typed budgets, AD sensitivities, seeded Monte Carlo | JCGM worked examples reproduced exactly |
| Should-cost | Process-model cost from CAD [aPriori] | aPriori | Cost from actual generated plans (D-MFG-19) | Held-out quotes within the stated interval for 90% of parts |
| Machine connectivity | MTConnect 2.5 [MTConnect 2.5]; OPC 40501-1 [OPC 40501-1] | Vendor MES connectors [unverified] | Native adapters with signed snapshots (D-MFG-20) | Conformance against reference agents and servers |
| PCB handoff and DFM | IPC-2581C with DFX feedback [IPC-2581C]; Gerber 2024.05 [Ucamco Gerber] | Siemens Valor NPI [unverified] | IPC-2581C primary, Gerber X2 fallback (D-MFG-16) | Independent re-import and layer XOR; seeded-defect boards with 100% detection |
| Slicing and supports | Direct slicing; variable-width beads [Kuipers et al. 2020]; tree supports [OrcaSlicer] | OrcaSlicer and PrusaSlicer (reference only) | Direct slicing of all four Body representations (D-MFG-11) | Slice time and memory on a lattice corpus: at least 10x less memory than mesh-based slicing (target) |
| Lattices | Implicit, field-driven lattices | nTop [unverified] | `Implicit` Bodies with Field parameters, sliced without meshing | Relative density error under 1% against analytic values (target) |
| Weld distortion | Inherent-strain shrinkage (structure scale), transient thermo-mechanics (joint scale) [unverified] | Simufact Welding, ESI SYSWELD [unverified] | Both in Flux, by envelope | GP4 measured distortion inside the prediction band |
| Robot offline programming | Redundancy-resolved, collision-free planning | RoboDK, Siemens Process Simulate [unverified] | Robots as Machines sharing the CAM kinematics and posts | Re-interpreted robot programs reproduce motion; cycle time within 10% (target) |
| CMM programming and scan inspection | Model-based plans in QIF [ISO 23952] | PC-DMIS, ZEISS CALYPSO, PolyWorks [unverified] | Characteristics with provenance identity (D-MFG-18) | QIF round trip; synthetic registration cases recovered within tolerance |
| Life-cycle assessment | ISO 14040 and 14044 process LCA [ISO 14044] | openLCA, SimaPro [unverified] | Inventory generated from actual process plans | Mass balance; reference product systems reproduced |

## Platform notes

- **Identical features everywhere.** All strategies, nesting, slicing and simulations are Wasm components or core Rust, so desktop, browser and server run the same code. Large sign-off simulations may run on team servers, but every platform can start, inspect and review them. Given enough memory, the browser runs them locally with the same features.
- **Determinism across platforms.** Toolpaths and nests are bit-identical within a platform class. Across classes, results agree within the declared tolerance, and NC text is identical after quantization to the controller increment. The cross-platform suite compares posted programs, nests and slice contours on every commit.
- **GPU paths.** Wasm components never call the GPU directly; they call Anvil or Flux operations that do, such as `anvil::correlate_grids` and Flux solvers. These operations and the tri-dexel render cache run on wgpu with CPU fallbacks. Collision counts are integers (D-MFG-12). Every decision that depends on GPU floating point is re-checked on the CPU with exact predicates.
- **Wasm memory.** Browser Wasm memory is limited [unverified for current browser limits], so in-process stock, voxel grids and large nests are streamed and tiled. When an evaluation exceeds local memory, the platform offers server evaluation explicitly instead of failing silently.
- **Machine access.** Serial and USB devices are reached through the machine gateway on every platform, because Web Serial is not Baseline [MDN Web Serial]. MTConnect, OPC UA and DNC over TCP run in the gateway or on servers, never inside evaluation.
- **Controller files.** Posted files honor controller line endings (often CR-LF or bare LF), character sets, maximum line length, file-size limits and naming rules. These belong to the `Controller` record, not to the host OS. The platform layer writes bytes exactly as posted.
- **Air-gapped shops.** Machine, tool, material, supplier, regulatory and price packages install offline. Compliance results state the date of every data package used.
- **Tier 2 devices.** Tablets and phones view programs, simulations, work instructions and inspection results, and capture as-run notes and photos. Shop-floor approval requires a Tier 1 client or a Tier 2 client with an authenticated approval key, because approval releases physical risk.
- **Licensing.** No GPL or AGPL code is linked. PrusaSlicer, OrcaSlicer and CuraEngine are AGPL-3.0 and OpenCAMLib is LGPL-2.1; all are external reference oracles only. Sparrow (MIT), cavalier_contours (MIT or Apache-2.0), i_overlay (MIT), Manifold (Apache-2.0) and Clipper2 (BSL-1.0) are permissive [cavalier_contours; i_overlay; Manifold; Clipper2]. jagua-rs and async-opcua are MPL-2.0 and require PLT's approval as file-level copyleft.

## Interfaces with other subsystems

### What MFG consumes

| From | Canonical name or type | Used for |
| --- | --- | --- |
| Anvil | `anvil::boolean`, `anvil::slice`, `anvil::offset_curves_2d`, `anvil::medial_axis_2d`, `anvil::tool_drop`, `anvil::tool_push`, `anvil::swept_volume`, `anvil::distance`, `anvil::collide`, `anvil::deform`, `anvil::split`, `anvil::extend_surface`, `anvil::visibility`, `anvil::draft_map`, `anvil::voxelize`, `anvil::correlate_grids`, `anvil::fit` (each with behavior versions and `ErrorBound`) | Every planning capability |
| Anvil | Wire Bodies with line, arc and NURBS edges; `Implicit` narrow-band Bodies; `EntityId` and `HistoryRecord` | Toolpaths, stock, regeneration |
| Flux | Weak forms and solvers for: cutting mechanics, beam and solid deflection, modal analysis and receptance coupling, non-isothermal free-surface flow, solidification, incremental shell forming, thermo-elasto-plasticity with element activation, rigid-body contact, current distribution | Process physics |
| Flux | Algorithmic differentiation of forms | Uncertainty sensitivities, compensation, optimization |
| COV | `ValidityEnvelope` and constitutive models for cutting, polymer melts, cast alloys, forming, phase transformation | Envelope checks, heat treatment |
| MEC | Kinematic mates and joints; sheet-metal flat patterns and bend allowance; weld joint definitions; GD&T controls on faces; bolted-joint preload requirements; gear geometry; laminate definitions | Machines, forming, joining, inspection, gears, composites |
| ELX | Board model: layers, stackup, netlist, footprints, placements, design rules; Catalog part electronic data | Fabrication and assembly outputs |
| Kiln | Memoized `Op` evaluation, cancellation, coarse-first streaming, cost caps, seeded portfolio runs that keep the best result by (objective, seed) | All evaluation |
| CAS | Content hashes for programs, nests, builds, snapshots | Approval binding, release artifacts |
| `repo` | EBOM, MBOM and SBOM views; releases as signed tags; change orders; serial numbers | Routings, as-built, FAI, passports |
| `api` | Actions with capability-scoped permissions for transfer, connectivity, quoting and passport publication; Proposals | Everything that touches the network or a machine |
| AGT | Agent permissions, cost caps, Proposal format | Agent-proposed programs |
| UIX | Field painting, overlays, timeline scrubbing, proposal diff | Review of toolpaths, simulations, deviations |
| PLT | Machine gateway packaging, serial and USB access, certificate stores, license policy | Connectivity, licensing |
| ECO | Package registry for machine, tool, printer, material, supplier and regulatory packages; signed data packages | Every data package |
| ING | Records, enums, `Map`, `Interval`, `Money<C>` (CCR-MFG-4), `require`, templates as functions, string tables | Every Ingot interface |

### What MFG provides

| To | Provided | Type |
| --- | --- | --- |
| All tabs | `std::mfg` packages: `core`, `machining`, `am`, `molding`, `casting`, `forming`, `joining`, `treatment`, `electronics`, `assembly`, `inspection`, `cost`, `sourcing`, `factory`, `sustainability` | Ingot packages |
| ECO | WIT worlds for strategies, posts, nesting, packing, slicers, recognizers, quoting; reference Wasm components | WIT interfaces, Wasm components |
| MEC | DFM, DFA and DfAM Checks; manufacturing cost and carbon Fields for design trade-offs; as-built deviation Fields | `Check`, `Field` |
| ELX | Fab and assembly DFM findings as IPC-2581C DFX records and located Checks | `Check` |
| COV | Process histories as boundary conditions (temperature, deformation, residual stress) for downstream performance analysis | `Field` |
| `repo` | Routings, programs, work instructions, inspection plans and results attached to releases and serials | Release artifacts in CAS |
| UIX | Program, simulation and inspection views as Bodies and Fields, plus timeline data | `Body`, `Field` |
| AGT | Machinability and DFM reports, typed `MfgError` fixes as editable suggestions | Plain values |
| `api` | Actions: `transfer_program`, `start_build`, `collect_machine_data`, `request_quote`, `publish_passport`, `import_inspection_results` | `api` action schemas |

### Rust surface

```rust
// crates: std/mfg-wit (interfaces), io/nc-post, io/stepnc, io/qif, io/ipc2581, io/gerber,
// io/mtconnect, io/opcua-mfg, io/usd-factory, oracles/mfg (protected)
pub trait Strategy {
    fn generate(&self, req: &StrategyRequest) -> Result<Toolpath, MfgError>;
}
pub trait Post {
    fn post(&self, program: &Program, machine: &Machine) -> Result<(NcText, BlockMap), MfgError>;
}
pub trait NcInterpreter {            // independent implementation, used only by oracles
    fn interpret(&self, text: &NcText, machine: &Machine) -> Result<Vec<Motion>, InterpretError>;
}
```

## Oracles

All oracles live in `oracles/mfg/`, a protected directory that agents can read but not write. Held-out parts, programs, nests and measurement data are never shown to agents.

| Oracle | What it verifies | Gate |
| --- | --- | --- |
| Independent NC re-interpreter | Posted code reproduces the toolpath within tolerance for each controller family | Every post, every commit |
| Controller conformance corpora | Golden programs per controller family, checked against the vendor's simulator output where licensed, and on real machines at the reference shop | Every post release |
| Seeded crash corpus | 100% detection of planted collisions, near-misses and over-travels | Every commit; zero false negatives |
| Seeded gouge and leftover corpus | Planted gouges and leftovers detected with correct depth | Every commit |
| Engagement-bound check | Independent stock simulator recomputes engagement and chip thickness along adaptive paths | Every adaptive strategy change |
| Removal-volume conservation | Removed volume equals the integrated swept volume within the error bound | Every commit |
| Cycle-time calibration | Predicted against measured times on the reference machines | Weekly; 5% target |
| Nest validity | Exact overlap, rule and containment checks; utilization recomputed | Every nest |
| Nesting benchmark | ESICUP plus GARDEYN instances at fixed work budgets | Release; density target |
| Pack validity | Exact pairwise clearance and translational removability | Every pack |
| Slice validity | Per-layer area against integrated cross-section; closed contours; bead fill ratio | Every commit |
| 3MF validation | Consortium schema validation and round trip | Every writer change |
| AM-Bench comparisons | DED residual stress and deflection, cure depth | Phase 3 release |
| Molding analytics | Center-gated disk and other Hele-Shaw analytic solutions; mass conservation | Every solver change |
| Casting analytics | Stefan problem; published WCB plate porosity | Every solver change |
| Forming benchmarks | Published springback and formability parts | Phase 4 release |
| Assembly replay | Every disassembly motion replayed with continuous collision detection | Every plan |
| Line-balancing benchmark | All 269 Hoffmann, Talbot and Scholl instances optimal | Release |
| Locating rank test | Determinacy of fixture contact sets | Every fixture |
| GUM and JCGM examples | Uncertainty budgets and Monte Carlo results reproduced | Release |
| QIF and DMIS round trip | Public samples imported and exported without loss | Every change |
| AS9102 schema | Revision C form fields complete and consistent | Every FAI report |
| SPC reference data | Published control-chart and capability examples reproduced exactly | Release |
| Cost reference parts | Hand-computed costs per process | Every cost-model change |
| LCA mass balance | Inventory mass balance per routing step | Every study |
| Passport completeness | Every required element of the delegated-act package mapped or explicitly not applicable | Every passport |
| Compliance seeded BOMs | Planted restricted substances and undeclared 3TG found | Every regulatory package update |
| Determinism suite | Same inputs give identical programs, nests, builds and reports within a platform class, and within tolerance across classes | Every commit |
| Golden products | GP1 machined bracket programs run at the reference shop; GP2 printed lattice bracket measured; GP3 gears inspected; GP4 weld distortion measured; GP5 molded enclosure short shots, warp and board assembly; GP6 drone build records and passport | Phase gates |

## Phasing

| Phase | MFG scope | Gate evidence |
| --- | --- | --- |
| 0 | Core types and `MfgError`; determinism rules for searches; NC re-interpreter skeleton; protected oracle directory | Determinism suite covers a toy strategy and a toy nest |
| 1 | 2.5D and 3-axis milling, adaptive clearing (after the FTO review), drilling cycles; 3-axis Fanuc and Haas posts with signed file export; stock, gouge and collision simulation; feeds from chip thickness and power; tool libraries; templates, regeneration and agent proposals; FFF and polymer PBF build preparation, 2D plate nesting, slicing, variable-width perimeters, TPMS and beam lattices, DfAM checks, 3MF production output, printer connectivity through the gateway; coating specification; machining and AM cost with BOM roll-up; approval flow | GP1 machined bracket: programs pass every oracle and are cut at the reference shop within drawing tolerances, verified by external metrology. GP2 lattice bracket printed by FFF or polymer PBF and measured externally |
| 2 | 5-axis strategies and posts for all four controller families; Siemens and Heidenhain 3-axis posts; ISO 14649 export; turning; gear cutting; laser, plasma and waterjet cutting; press-brake planning; rule-based target recognition; tool deflection; metal PBF supports, inherent-strain simulation and compensation; vat photopolymerization; 3D packing; welding procedures, sequencing and structure-scale distortion; fastening specification; fixtures; assembly sequence planning, DFA and work instructions; moldability analysis; heat-treatment specification and coating dimensional effects; characteristic extraction, scan-to-CAD and uncertainty budgets; MBOM and routings; parametric cost, target costing and quoting plugins; supplier records and alternates; embodied carbon; RoHS and REACH checks | GP3 gearbox gears cut and inspected; GP4 welded frame distortion inside the prediction band, with sheet-metal guards bent from planned sequences; metal PBF build of GP2 within 0.1 mm after compensation |
| 3 | Injection mold design and fill, pack, cool and warp; PCB fabrication and assembly outputs with DFM and DFA; adaptive turning and mill-turn; 5-axis roughing and barrel finishing; wire EDM; turret punching and waterjet taper compensation; one-step blank development; tube bending; riveting and bonding; HIP and stress-relief routings; learned target recognition; CMM programming, QIF, SPC, AS9102 and gear inspection; line balancing; robot offline programming; chatter and stability lobes; AP238 export and STEP-NC import; MTConnect and OPC UA adapters, DNC transfer; OpenUSD export; as-built records; LCA, recyclability, SCIP and conflict minerals; DPP data mapping and registry registration; binder jetting, material jetting and DED; make-or-buy, lead time and supply risk | GP5 molded enclosure: short-shot sequence and warp inside the prediction bands; its PCB fabricated and assembled from Crucible outputs alone |
| 4 | Fiber orientation and molding variants; die casting; sand casting with gating, risers, solidification and porosity; thermoforming; sheet forming, progressive dies and springback compensation; composite draping and layup; joint-scale weld simulation; plating distribution and paint; Swiss-type; sinker EDM and STEP-NC EDM and AM parts; grinding; bevel cutting; board test programs and reflow profiles; PPAP and PFMEA; virtual CMM; tool-life and chatter feedback; MES integration; model calibration from as-run data; battery passport; curved-layer slicing; binder-jet sintering and extrusion warp | GP6 drone: build records, inspection, cost, carbon and passport generated from the model; predictions validated against physical data |
| 5+ | Investment casting and hot tears; forging; aluminum extrusion; blow, rotational and compression molding; roll forming and hydroforming; forming robustness; heat-treatment distortion; AFP and ATL; cure simulation; sheet lamination; product twin export; process-chain twins for large structures | Proposed golden products: a cast and machined pump housing (casting to machining chain) and an extruded, welded aluminum frame |

## Open questions

1. **Adaptive clearing freedom to operate.** Does an engagement-controlled spiral without a pre-roughing slot fall outside US 9,164,503's claims? Legal review is needed before phase 1 ships, and other vendor patents may exist.
2. **MPL-2.0 dependencies.** jagua-rs and async-opcua are file-level copyleft. PLT must decide whether the license policy admits them as linked dependencies or requires clean-room re-implementation.
3. **Controller conformance without vendor simulators.** Can the reference shop provide physical Fanuc, Siemens, Heidenhain and Haas controls for corpus capture, or must we license vendor virtual controllers?
4. **Determinism versus anytime quality.** Work-unit budgets make results reproducible but tie quality to hardware-independent counts. Is a fixed default budget per evaluation class acceptable to users who expect "run for 10 minutes"?
5. **Hele-Shaw validity threshold.** The default thickness-to-flow-length envelope needs calibration against the 3D solver in phase 3.
6. **Learned target recognition.** Training data licenses for MFInstSeg and similar datasets must permit commercial use of trained weights, and that is unconfirmed.
7. **Passport hosting.** Should Crucible operate a passport service, or only publish to third-party services? The ESPR back-up copy requirement through an independent third-party service provider favors the second [EU ESPR].
8. **Process-physics ownership.** Where exactly does COV's model ownership end and MFG's process setup begin for molding and casting material models (Cross-WLF, pVT, fraction-solid curves)?
9. **Tier 2 approval.** Is authenticated approval of a machine program from a tablet acceptable to safety reviewers?

## Contract change requests

1. **CCR-MFG-1: Fields over parameter domains.** Feeds over spindle speed, frequency response functions and stability lobes are quantities over a 1D parameter interval, not over a Body or region. Request: section 5 explicitly allows `Field<Interval<D>, V>` (a Field over a dimensioned interval). *Why:* without it, MFG and Flux would each invent a parallel "curve" or "table" type, which section 10 forbids.
2. **CCR-MFG-2: Signed data packages as evaluation inputs.** Prices, supplier capabilities, regulatory lists and machine data change outside the design. Request: the contract names "dated, signed data packages" as the only way external data enter evaluation, so every subsystem handles them the same way. *Why:* determinism (principle 4) and one mechanism for ECO, MFG, ELX and AGT.
3. **CCR-MFG-3: Approval bound to content hashes.** Request: section 7 states that actions with physical effects (machine transfer, print start, passport publication) need human approval bound to the artifact's CAS hash. *Why:* agents can already propose; the contract does not yet say who may release physical risk.
4. **CCR-MFG-4: A money type in std.** Cost appears in MFG, MEC trade studies, ELX sourcing and AGT cost caps. Request: std defines `Money<C>` (decimal amount, ISO 4217 currency as a type parameter, no implicit conversion), outside the physical-dimension system of `Quantity<D>`. *Why:* one type for every subsystem, and currency mixing becomes a compile error like unit mixing.

## Sources

- [Gardeyn et al. 2025] Gardeyn, Vanden Berghe, Wauters, "An open-source heuristic to reboot 2D nesting research", arXiv:2509.13329: https://arxiv.org/abs/2509.13329 and https://arxiv.org/html/2509.13329
- [sparrow] https://github.com/JeroenGar/sparrow
- [jagua-rs] https://github.com/JeroenGar/jagua-rs
- [OpenCAMLib] https://github.com/aewallin/opencamlib
- [Open Hub OpenCAMLib] https://www.openhub.net/p/opencamlib
- [ISO/ASTM 52900] https://www.iso.org/standard/74514.html
- [Loughborough AMRG] https://www.lboro.ac.uk/research/amrg/about/the7categoriesofadditivemanufacturing/
- [EU ESPR] https://environment.ec.europa.eu/strategy/circular-economy/ecodesign-sustainable-products-regulation_en and https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202401781
- [Transition Pathways DPP] https://transition-pathways.europa.eu/retail/news/digital-product-passport-registry-now-live
- [LexisNexis DPP] https://www.lexisnexis.co.uk/legal/news/commission-launches-digital-product-passport-registry-under-ecodesign-regulation
- [Renoon delegated acts] https://www.renoon.com/blog/delegated-acts-for-digital-product-passport-explainer-and-current-status
- [Renoon DPP updates] https://linguana.renoon.com/blog/digital-product-passport-latest-updates-the-next-developments-to-watch
- [3MF specifications] https://3mf.io/spec/
- [3MF Toolpath] https://github.com/3MFConsortium/spec_toolpath
- [MTConnect 2.5] https://docs.mtconnect.org/MBSD_MTConnect_Part_1_2-5-0.pdf
- [PrusaSlicer] https://github.com/prusa3d/PrusaSlicer
- [OrcaSlicer] https://github.com/OrcaSlicer/OrcaSlicer
- [CuraEngine] https://github.com/Ultimaker/CuraEngine
- [Clipper2] https://github.com/AngusJohnson/Clipper2
- [Kuipers et al. 2020] https://arxiv.org/abs/2004.13497
- [FeatureFox] Fuchs, Kacan, Haag, Lohse, arXiv:2604.26770: https://arxiv.org/pdf/2604.26770
- [STEP Tools AP238e3] https://www.steptools.com/docs/stp_aim/notes_ap238e3.html
- [ISO 10303-238] https://www.iso.org/standard/72030.html
- [Li et al. 2025] Li, Niu, Sun, Sun, Chinese Journal of Aeronautics 38(2): https://www.sciopen.com/article/10.1016/j.cja.2024.05.038
- [ISO 6983-1] https://www.iso.org/standard/34608.html
- [ISO 14649 catalog] https://store.accuristech.com/subgroups/29485
- [ISO 13399-1] https://www.iso.org/standard/36757.html
- [ISO 23952] https://www.iso.org/standard/77461.html
- [AOUSD Core 1.0] https://www.linuxfoundation.org/press/alliance-for-openusd-announces-core-specification-1.0-the-universal-language-for-building-3d-worlds
- [IAQG 9102C] https://ma.iaqg.org/wp-content/uploads/2019/10/9102_Changes_07112023.pdf
- [OPC 40501-1] https://reference.opcfoundation.org/MachineTool/v102/docs/
- [US 9,164,503] https://patents.google.com/patent/US9164503
- [ECHA Candidate List] https://echa.europa.eu/candidate-list-table
- [Moldflow] https://www.autodesk.com/products/moldflow/overview
- [AutoForm] https://www.autoform.com/en/products/
- [MAGMASOFT] https://www.magmasoft.de/en/solutions/magmasoft/
- [CloudNC CAM Assist] https://www.cloudnc.com/cam-assist
- [Altintas et al. 2008] Altintas, Stepan, Merdol, Dombovari, CIRP J. Manuf. Sci. Technol. 1: https://www.mm.bme.hu/~stepan/mm/journal2008/altintas_stepan_merdol_dombovari_CIRP.pdf
- [Janus NX 2606] https://blog.janus-engineering.com/en_en/details/article/siemens-nx-release-2606/
- [Siemens Lambda Function] https://blogs.sw.siemens.com/nx-manufacturing/siemens-partners-with-lambda-function-to-explore-ai-assisted-cnc-programming-for-nx-cam/
- [ModuleWorks] https://www.moduleworks.com/software-components/
- [NIST AM-Bench 2025] https://www.nist.gov/ambench/am-bench-2025-measurements-and-challenge-problems
- [Cui et al. 2023] Cui, Rong, Chen, Matusik, ACM TOG 42(4): https://cdfg.mit.edu/pdf/journal/2023-cui-dense-interlocking-free-and-scalable-spectral-packing-of.pdf
- [Zhang et al. 2022] https://history.siggraph.org/?p=216073
- [Manifold] https://github.com/elalish/manifold
- [aPriori] https://www.apriori.com/
- [MDN Web Serial] https://developer.mozilla.org/en-US/docs/Web/API/Web_Serial_API
- [IPC-2581] https://www.ipc2581.com/
- [IPC-2581C] https://www.electronics.org/news-release/ipc-releases-ipc-2581-revision-c-generic-requirements-printed-board-assembly-products
- [Ucamco Gerber] https://www.ucamco.com/en/gerber
- [Tian et al. 2022] https://arxiv.org/abs/2211.03977v1
- [async-opcua] https://github.com/FreeOpcUa/async-opcua
- [i_overlay] https://lib.rs/crates/i_overlay
- [Fusion Manufacturing Extension] https://www.autodesk.com/products/fusion-360/manufacturing-extension
- [Materialise Magics] https://www.materialise.com/en/industrial/software/magics-data-build-preparation
- [cavalier_contours] https://github.com/jbuckmccready/cavalier_contours
- [EU RoHS] https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en
- [EU conflict minerals] https://policy.trade.ec.europa.eu/development-and-sustainability/conflict-minerals-regulation/regulation-explained_en
- [BIPM JCGM] https://www.bipm.org/en/committees/jc/jcgm/publications
- [ISO 14044] https://www.iso.org/standard/38498.html
- [Carlson and Beckermann 2009] Metall. Mater. Trans. A 40: https://link.springer.com/article/10.1007/s11661-008-9715-y
- [BB&R] "A Branch, Bound, and Remember Algorithm for the Simple Assembly Line Balancing Problem", doi 10.1287/ijoc.1110.0462: https://pubsonline.informs.org/doi/10.1287/ijoc.1110.0462
- [Ozcan et al. 2024] Ozcan, Kushwaha, Qian, Reynaerts, euspen ICE 2024: https://euspen.eu/knowledge-base/ICE24301.pdf
