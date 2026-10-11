# Manufacturing (MFG)

`std::mfg` turns a released design into made parts through one typed plan: Ingot intent, Wasm planning, Anvil geometry and Flux physics. Every toolpath, nest, mold, routing, cost and passport is a deterministic function of the design, checked by oracles. A person approves each program over its posted text and simulation evidence, and Crucible never starts a machine tool, robot, laser, press or furnace.

## Scope, layering and core types

| Area | MFG owns | Others own |
| --- | --- | --- |
| Process planning | Setups, workingsteps, toolpaths, posts, nests, builds, routings, setup sheets | None |
| Process physics | Process setups, boundary conditions, process data, checks | Flux (forms, solvers); COV (models, envelopes) |
| Design checks | Process DFM, DFA and DfAM checks against process profiles | MEC (design-domain checks); ELX (board DRC) |
| Product structure | Routings, program Items, as-built records | KLN and `repo` (Items, BOM views, change orders) |
| Electronics and harnesses | Factory handoff: packages, rule packs, panels, stencils, test, harness package | ELX (board, DRC engine, connectivity); MEC (harness geometry); ECO (`io/` writers) |
| Connectivity | Protocol mappings for machines, printers and CMMs; the machine gateway | PLT (serial, sockets, certificates); AGT (`api`, Acts) |

**Decision D-MFG-1:** Every manufacturing capability is split along the contract's layers. Intent is Ingot, heavy search is a Wasm component, shared geometry is an Anvil operation and physics is a Flux form. *Why:* shops edit intent, while algorithms need sandboxed native speed, and the same operations serve CAM, slicing, molding and inspection. *Rejected:* a monolithic CAM engine (privileged code, which breaks principle 1); all-Ingot strategies (inner loops too hot).

**Decision D-MFG-2:** Manufacturing adds no geometry or result types. Physical things are Bodies, Parts and Assemblies; paths are wire Bodies carrying Fields; results are Fields. *Why:* the UI paints, diffs, caches and queries these types already, so every manufacturing artifact inherits those abilities. *Rejected:* a separate stock type, toolpath geometry type or simulation-result type (parallel abstractions that section 10 forbids).

Machines, fixtures, molds, nests and panels are Assemblies; cutting tools, holders and probes are catalog parts. An industry "operation" is a workingstep, after ISO 14649, and a "manufacturing feature" is a machining target found by a `Query`.

```
// std::mfg::core (illustrative; the Ingot tab fixes record syntax)
pub record Toolpath {
    path:    Body,                       // wire Body (D-MFG-22)
    tool:    Instance,                   // tool Assembly in its holder
    axis:    Field<Body, Direction>,
    feed:    Field<Body, Velocity>,
    spindle: Field<Body, AngularVelocity>,
    kinds:   Map<EntityId, MotionKind>,  // cut, plunge, link, rapid; one per edge
    error:   ErrorBound<Length>,
}
pub record WorkOffset  { number: WcsId, frame: CoordSys }   // G54 to G59, extended and fixture offsets
pub record Station     { part: Instance, stock: Body, wcs: WorkOffset }
pub record Setup       { machine: Machine, fixture: Assembly, stations: [Station], index: Option<RotaryIndex> }
pub record Workingstep { target: Query, strategy: StrategyCall, station: StationRef, toolpath: Toolpath }
pub record Program     { setups: [Setup], steps: [Workingstep], order: Order }   // Order: ByTool | ByStation
pub record Routing     { steps: [RoutingStep] }
```

**Decision D-MFG-22:** A toolpath is a wire Body with one edge per contiguous run of one motion kind. Each edge carries a polyline or arc-spline curve with per-vertex Field samples. A single move is addressed by (edge `EntityId`, vertex index), which is not a persistent name. *Why:* a finishing path has millions of moves, and an edge per move would carry an `EntityId`, lineage and history each (R2-45). *Rejected:* one edge per move (memory and hashing grow by orders of magnitude); a toolpath type outside `Body` (D-MFG-2).

**Decision D-MFG-3:** Searches that use randomness take an explicit `seed` input and a counter-based generator. Budgets count work units, never seconds, and parallelism runs as a seeded portfolio. *Why:* the contract forbids clocks and thread-order dependence, and anytime optimizers (nesting, orientation, sequencing) are where these dependences usually creep in. *Rejected:* wall-clock time limits (non-reproducible); shared-state parallel search (thread-order dependent).

Kiln keeps the best portfolio result by (objective, seed), and outputs quantize to their declared resolution before locale-free formatting. Outside data enter only as External inputs (prices, offers, supplier records, machine readings) or Evidence records (part measurements).

```rust
pub enum MfgError {
    Unreachable     { region: Query, reason: ReachReason, fixes: Vec<Fix> },
    Collision       { a: InstanceRef, b: InstanceRef, at: PathParam, block: Option<u32>, fixes: Vec<Fix> },
    Gouge           { depth: Length, at: PathParam, block: Option<u32>, fixes: Vec<Fix> },
    AxisLimit       { axis: AxisId, required: f64, limit: f64, fixes: Vec<Fix> },
    Unsupported     { capability: Capability, controller: ControllerId, fixes: Vec<Fix> },
    Infeasible      { constraint: ConstraintRef, witness: Option<ObjectId>, fixes: Vec<Fix> },
    OutsideEnvelope { model: ModelId, quantity: QuantityRef, value: f64, fixes: Vec<Fix> },
    MissingData     { what: DataRef, fixes: Vec<Fix> },
    OffsetMismatch  { register: OffsetRef, expected: Length, read: Length, tolerance: Length },
    HashMismatch    { expected: ObjectId, found: ObjectId },
    BudgetExhausted { best_so_far: Option<ObjectId>, work_done: u64 },
}
```

Each `Fix` is a typed edit, and no strategy substitutes a tool, direction or material silently. `BudgetExhausted` is a cacheable `Failure`, because a search budget is an argument; an Evaluation's `Budget` (AGT) running out is an Abort (contract 7.2).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Core manufacturing types | `std::mfg::core` records over Bodies, Fields and Assemblies | Typed compile errors | MFG-O-CORE-1 | 0 |
| Typed failures with fixes | Every `MfgError` carries ranked typed edits | The error itself | MFG-O-CORE-1 | 0 |
| Seeded, budgeted searches | `seed` and work-unit `budget` arguments; seeded portfolios | `BudgetExhausted` with the best feasible result | MFG-O-DET-1 | 0 |
| Outside data | External inputs and Evidence records, pinned by `ObjectId` in the `CheckOutcome` | `MissingData` naming the input | MFG-O-CORE-2 | 1 |
| Label invariance | Plans and costs unchanged when every name is re-randomized | None | MFG-O-LABEL-1 | 1 |
| Toolpath storage | D-MFG-22, target 10⁷ moves under 400 MB | `Infeasible` above the declared move count | MFG-O-CORE-3 | 2 |

## Approval, transfer and physical safety

Simulation proves a program consistent with the model; this path binds the model to the shop floor as far as software can.

1. CI simulates the posted NC text and runs every machining oracle on it.
2. A named person approves the program subject: the posted programs, machine and controller versions, tool table, setup sheet, simulation verdicts and `BlockMap`.
3. The program releases as an Item (contract 2) through KLN's manufacturing change order, in KLN's states `Prototype`, `Proven` after a passing first article and `Released` (D-KLN-38).
4. An assigned person approves a `send_to_machine` Act; the gateway checks the hash and offsets (D-MFG-24).
5. A person at the machine loads the program and starts the cycle, with tool-length checks and reduced override as the setup sheet says.

**Decision D-MFG-4:** Approval binds to the program subject's `ObjectId`, so a regenerated or edited program never inherits it. Agents may prepare transfer Acts; the server executes them only after a human Approval, and no agent can give an on-site confirmation. *Why:* regeneration is automatic, so trust must attach to exactly what was reviewed, and physical risk needs a person at the device (contract 7.6, R4-01, R5-18). *Rejected:* approval per workingstep name (survives geometry edits); agent approval or agent commit; signing the `ChangeId` or full CI report, which a rebase or CI re-run would void (R3-16). (revised in round 2)

| Act or method | Effect | Rule |
| --- | --- | --- |
| `send_to_machine` | Delivers a program to a control's memory or DNC queue | Never selects, loads or starts it |
| `send_robot_program` | Delivers a robot program | Proved in manual reduced-speed mode; never writes safety configuration |
| `store_machine_job` | OPC UA `Store` of a job order | `Start`, `StoreAndStart`, `Resume` and `RevokeStart` never called |
| `send_print_job` | Uploads a print job | Upload only |
| `start_print` | Starts a print | Contract 7.6 conditions; off by default per site |
| `read.machine_data` | Status, offsets, programs, alarms | A Read method (AGT), never an Act |

`run_rig_test`, the sixth physical-effect Act, serves hardware CI (contract 7.1). ISA-95 Job Control defines eleven job-order methods, among them `StoreAndStart`, `Start`, `RevokeStart` and `Resume` [ISA-95 Job Control]. Crucible calls `Store` only inside `store_machine_job`, and `Cancel` and `Clear` only on jobs it stored, to revoke them before start; a changed job is revoked and stored again. `unattended_safe` never covers machine tools, robots or lasers (contract 7.1).

The EU Machinery Regulation applies from 20 January 2027 with cyber-safety provisions for safety-relevant software [EU Machinery]. MFG's safety documentation states that Crucible issues no motion command.

**Decision D-MFG-24:** The machine gateway enforces three checks around transfer. Posts write item, revision, release id and a short content hash into the program header, and the gateway recomputes the hash on transfer and on read-back. It reads tool and work offsets and re-simulates with them before transfer, and it captures edits made at the control. *Why:* a control cannot verify signatures, operators edit programs, offsets and feeds there, and the real offsets decide whether the simulated program is the one that runs (R4-05). *Rejected:* trusting the file after export (approval ends at the cable); blocking every edit at the control (controls cannot enforce it).

Offsets come from a vendor connector or operator entry, and from phase 3 from MTConnect `ToolOffsets` and `WorkOffsets` or OPC UA [MTConnect 2.5 Part 3]. The gateway captures edits by DNC receive or a vendor connector, and from phase 3 by watching `ProgramEdit` and `ProgramHeader` [MTConnect 2.5 Part 3]. It uploads an edited program and opens a Proposal with its semantic NC diff, and parts made from it get an as-built deviation.

[[DIAGRAM: Program release flow. Boxes left to right: Design Part → Setup (machine, fixture, stations) → Workingsteps (target Query, strategy, tool) → strategy Wasm components → post engine with Ingot hooks → NC text and BlockMap → simulation of the posted text under the controller's motion semantics and independent re-interpretation → program subject → human Approval → manufacturing change order → send_to_machine Act → gateway (hash, offsets, re-simulation) → control memory; a person at the control starts the cycle. Red arrows from every check back to Workingsteps: "typed MfgError with fixes". Dashed arrow from the control's edits to a Proposal: "edit capture".]]

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Program subject | `ProgramSubject { programs, machine, controller, tool_table, setup_sheet, verdicts, block_map }`; Approvals sign its `ObjectId` | Changes inside the subject void the Approval; changes outside do not | MFG-O-SAFE-1 | 2 |
| Manufacturing change lane | MBOM, programs, routings, fixtures, work instructions and inspection plans release through KLN's manufacturing change order (D-KLN-38) | A change to an EBOM definition is rejected | MFG-O-SAFE-1 | 2 |
| Change impact | A design change invalidates exactly the programs whose targets or setups changed | None; the set is reported | MFG-O-SAFE-1 | 2 |
| Transfer Acts | The Act table above, committed after an assigned human Approval | Refused without an approved subject | MFG-O-SAFE-2 | 2 |
| Restricted print start | `start_print` per contract 7.6 | Refused without declarations or on-site confirmation | MFG-O-SAFE-2 | 2 |
| No motion commands | Connector worlds contain no cycle start, resume, jog, `Start`, `StoreAndStart`, `Resume` or `RevokeStart` | Not callable | MFG-O-SAFE-3 | 2 |
| Header hash and read-back | Recomputed on transfer and read-back | `HashMismatch` | MFG-O-SAFE-2 | 2 |
| Pre-run offset verification | Offsets read; collision re-simulated with actual gauge lengths | `OffsetMismatch` beyond setup-sheet tolerance | MFG-O-SAFE-4 | 2 |
| Edit capture | Edit watch, DNC receive, Proposal, as-built deviation | Controls without edit signals need an operator declaration | MFG-O-SAFE-4 | 2 |
| DNC and drip feed | Serial DNC with XON/XOFF or RTS/CTS flow control, and Ethernet DNC | A fault stops the feed; never resumed automatically | MFG-O-SAFE-5 | 2 |

## Machines, controllers and posts

A machine is an Assembly of links joined by MEC's kinematic mates, plus limits, spindles, tool changer and a controller record. Builders publish machine packages, shops extend them, and volumetric compensation stays on the control.

```
pub record Machine {
    structure: Assembly, chain: KinematicChain,
    axes:      [Axis],                   // linear and rotary (A, B, C) with limits
    spindles:  [Spindle],                // Field<AngularVelocity, Power>, Field<AngularVelocity, Torque>
    tool_changer: Option<ToolChanger>, channels: [Channel], controller: Controller, envelope: Body,
}
pub record Controller {
    family: ControllerFamily, dialect: Dialect, flags: CapabilityFlags,
    offsets: OffsetModel,                // work offsets, H and D registers
    motion:  MotionSemantics,            // D-MFG-23
    files:   FileRules,                  // line endings, character set, length, size, names
}
pub record MotionSemantics {
    rapid: Rapid,                        // Linear | PerAxis { rates }
    rotary_rapid: RotaryRapid,           // Shortest | Directional | Unwind
    tcp_in_rapid: Bool, reference_return: ReferenceReturn, cycle_retract: Retract,
    cutter_comp: CutterComp,             // look-ahead blocks, entry rule
    tool_change_envelope: Body,
}
```

**Decision D-MFG-23:** Collision simulation and the independent re-interpreter both execute the posted NC text under the controller's declared `MotionSemantics`, never the pre-post toolpath. Where a semantic is undeclared, the simulator sweeps a conservative envelope (for a rapid, the joint-space box between its endpoints) and returns `Unsupported` instead of passing. *Why:* verified programs crash in motion the control interpolates itself: dog-leg rapids, rotary unwinding, reference returns, retract planes, compensation entry and tool changes (R4-02). *Rejected:* checking the toolpath only; assuming straight rapids, since positioning fixes only the end point [ISO 6983-1] [unverified per control].

Posts convert G0 to G1 at a declared rapid-equivalent feed wherever that envelope comes closer to stock or fixture than the clearance. A family's post ships only after zero false negatives on the controller-semantics crash corpus.

**Decision D-MFG-5:** Programs are stored in one canonical intermediate form that mirrors ISO 14649: each workingstep binds a machining target, a strategy with its tool and technology, and a toolpath. One post engine, a Wasm component, maps it to a dialect, driven by the `Controller` record, builder customizations as data and Ingot hooks over typed block events. *Why:* STEP-NC export becomes a mapping, every block traces to its workingstep, one engine serves every strategy, and shop post editors work in Ingot (contract 4 tier rule, R4-08). *Rejected:* posting from raw cutter-location files (loses intent); one post per strategy and machine pair (combinatorial); Rust Wasm hooks as the default (shops will not write them). (revised in round 2)

Hooks run on `on_program_start`, `on_tool_change`, `on_wcs_change`, `on_rapid`, `on_cycle` and `on_program_end`; M-code maps, tool-change macros, coolant variants, chip conveyors and spindle warm-up are data. G-code comes only from this engine, through the `crucible:mfg` `post-processor` world; ECO has no separate G-code writer.

ISO 6983-1:2009 defines the format and address words, confirmed in 2025 [ISO 6983-1]. Posts read capability flags, not vendor names; the codes below come from manuals not opened [unverified], and each family's conformance corpus fixes them. Mazak Mazatrol conversational output is out of scope; Mazak machines get ISO-mode output.

| Capability flag | Fanuc | Siemens Sinumerik | Heidenhain TNC | Haas |
| --- | --- | --- | --- | --- |
| Tool center point control | G43.4 / G43.5 | TRAORI | M128 or FUNCTION TCPM | G234 |
| Tilted work plane | G68.2 | CYCLE800 | PLANE functions | G68.2 |
| High-speed contour mode | G05.1 | CYCLE832 | CYCL DEF 32 | G187 |
| Drilling cycles | G81 to G89 | CYCLE81 to CYCLE89 | CYCL DEF 200 series | G81 to G89 |
| Parametric programs | Macro B variables | R parameters, GUD variables | Q parameters | Macro variables |

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Forward and inverse kinematics | `fk` per channel; `ik` closed form for table-table, head-head and head-table, damped least squares otherwise, every branch returned | `AxisLimit`; `Unreachable` with the nearest pose | MFG-O-KIN-1 | 2 |
| Rotary indexing and wrapping | 3+1 indexing on A or B rotaries; 2D paths wrapped onto cylinders | `AxisLimit` | MFG-O-KIN-1 | 2 |
| Singularities and rotary linearization | Branches minimize rotary travel and keep continuity; points inserted until tip deviation is under tolerance | `Infeasible` with the singular segment | MFG-O-KIN-2 | 3 |
| Kinematic and spindle limits | Feed limited by per-axis velocity, acceleration and jerk; power and torque against spindle Fields | `Infeasible` with segment and margin | MFG-O-KIN-2 | 2 |
| Motion semantics | D-MFG-23 per controller; G0-to-G1 rule | `Unsupported` for undeclared semantics | MFG-O-SIM-2 | 2 |
| Generic ISO 6983 post | `post(program, machine) -> (NcText, BlockMap)` with arcs, helices, compensation and cycles | `Unsupported { capability, controller }` with fixes | MFG-O-POST-1 | 2 |
| Fanuc, Haas, Siemens and Heidenhain posts | 3-axis, 3+1 and 3+2 | As above | MFG-O-POST-1 | 2 |
| Simultaneous 5-axis posts | Four families; TCP, or joint space with inverse-time feed | `AxisLimit` or `Unsupported` with the block | MFG-O-POST-1 | 3 |
| Okuma OSP and Mazak ISO-mode posts | Family offset and cycle conventions | As above | MFG-O-POST-1 | 3 |
| Mitsubishi, Brother and Hurco posts | As above | As above | MFG-O-POST-1 | 4 |
| Post configuration and hooks | Builder customizations as Ingot data; Ingot hooks; Rust Wasm hooks only under contract 4 | Compile errors; hook failures name the hook | MFG-O-POST-2 | 2 |
| Post qualification | Shop's proven program against Crucible's for a reference part; record in the machine package | Undeclared differences block qualification | MFG-O-POST-3 | 2 |
| Semantic NC diff and block map | Motion and technology diff ignoring formatting; each block maps to workingstep, path parameter and design feature | None | MFG-O-POST-4 | 2 |

## Tools, stock, setups and workholding

A tool is an Assembly of catalog parts whose ISO 13399 properties are typed Quantities; ISO confirmed part 1 in 2021 [ISO 13399-1]. Vendors publish catalogs as packages built on ISO 13399 and DIN 4000 [unverified], shops keep libraries in their current CAM, and presetters measure assembled tools. Presetter readings and controller offset tables are machine readings, so they enter as External inputs.

**Decision D-MFG-6:** In-process stock serves leftover, rest machining and display only; gouge detection is independent of it. Stock is an `Implicit` Body on a sparse narrow-band grid, refined adaptively near the design surface, with an `ErrorBound` stated per setup. Gouges are found per cutting move as the certified minimum distance between the tool's exact swept envelope and the design B-rep. *Why:* a grid's accuracy is its spacing, GP1-sized stock at 5 µm needs about 8 × 10⁹ band cells against a 1 GiB target, and per-move distance is exact (R2-24). *Rejected:* gouge checks on the grid (resolution-limited); exact B-rep stock (Boolean cost grows with every move); meshes only (slivers accumulate). (revised in round 2)

A setup holds stations, so a double vise, first and second setups in one vise, an eight-offset tombstone and pallets are ordinary data. `setup_sheet` builds the machinist's document as an Ingot drawing that diffs and releases with the program. It shows the work-offset triad with dimensions to datums, fixtures, clamps and stock.

Its tool table lists T, pocket, H, D, holder, stick-out, gauge and flute length and expected life. Workingsteps with cycle times and first-run notes follow.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Tool catalog import | ISO 13399 Part 21 data in vendor packages, DIN 4000 mapping and documented incumbent tool-library formats → catalog parts | `MissingData` per absent property; never guesses | MFG-O-TOOL-1 | 2 |
| Tool assembly | `assemble_tool(cutter, holder, extensions, stickout) -> Instance`; holders and extensions are full collision Bodies | `Infeasible` on interface mismatch | MFG-O-TOOL-1 | 2 |
| Presetter readings | Length, radius and runout as External inputs keyed by assembly serial | Missing or stale readings flagged | MFG-O-TOOL-1 | 2 |
| Per-machine tool tables | Tool Assemblies → T number, pocket, H and D registers, read by posts | Conflicting entries fail the build | MFG-O-TOOL-1 | 2 |
| Cutting data | Vendor data, shop values, mechanistic coefficients and life parameters, each with source and uncertainty | `MissingData` only when no source exists | MFG-O-FEED-1 | 2 |
| Tool life | Count-based per edge from as-run records (2); model-based from engagement history (4) | Tools past life flagged before the program ends | MFG-O-TOOL-2 | 2, 4 |
| Blank and hand-off | `stock(kind, material, size or Body, cert)`; setup N's stock is setup N+1's blank | Part outside stock; fixture hits stock | MFG-O-STOCK-1 | 2 |
| In-process and rest stock | `simulate(program) -> (Body, Field<Body, u32>)`; `rest(stock, part, tolerance) -> Body` | `OutsideEnvelope` when the grid cannot meet the tolerance | MFG-O-STOCK-1 | 2 |
| Setups and stations | `Setup { machine, fixture, stations }`, `Program { setups, order }`; tombstones and pallets | Duplicate work-offset registers fail | MFG-O-SETUP-1 | 2 |
| Setup sheet | `setup_sheet(program, template) -> Drawing` | Tools without gauge data listed | MFG-O-SETUP-1 | 2 |
| Vises and modular fixtures | Catalog parts with jaw stroke and clamping force | `Collision` with toolpaths | MFG-O-SIM-2 | 2 |
| Soft jaws and offset probing | Jaw Bodies offset from the part, machined by their own program; probing cycles that set work offsets | Unreachable points reported | MFG-O-SETUP-2 | 2 |
| Locating, clamping and jigs | Form closure by contact-wrench rank; clamp forces against loads with friction and Flux deflection (3); weld and assembly jigs with access | `Infeasible` naming free motions; slip or deflection reported | MFG-O-SETUP-3 | 2, 3 |

## Milling, drilling and probing strategies

Each strategy is a Wasm component that turns a setup, target region, tool and parameters into a `Toolpath`, calling Anvil operations for geometry.

```
// WIT, abridged
interface strategy {
  record request { setup: setup-ref, region: list<entity-ref>, tool: instance-ref,
                   params: list<param>, tolerance: f64, seed: u64, budget: u64 }
  generate: func(r: request) -> result<toolpath, mfg-error>;
}
```

OpenCAMLib implements drop- and push-cutter under LGPL-2.1 [OpenCAMLib] with little recent activity [Open Hub OpenCAMLib]. Anvil's `tool_contact` re-implements the algorithms, and OpenCAMLib is only a reference oracle.

**Decision D-MFG-7:** Adaptive clearing is an engagement-controlled spiral seeded by the medial axis, measured against the true in-process stock rather than geometric offsets. Its quality bound is stated as maximum engagement angle and maximum chip thickness, and the oracle measures that bound independently. Crucible's implementation is clean-room and uses no vendor code. *Why:* vendors document the behavior (constant engagement, smooth motion) but not their algorithms, so the measurable bound is the contract. *Rejected:* offset-based "high-speed" pockets (engagement spikes at corners); adopting a single vendor's patented method.

1. Compute the medial axis of the region minus the tool radius with exact predicates.
2. Enter by helix or ramp at the vertex of maximal clearance, or at a pre-drilled hole.
3. Grow the cleared region in spiral steps, each solved so engagement against the current stock equals the requested angle.
4. Where the bound cannot hold (necks, corners), switch to variable-radius trochoids.
5. Link passes with tangent-continuous, collision-checked moves inside cleared material, and set feed from chip thinning.

Claim 1 of Boeing's US 9,164,503 requires a pre-roughing slot and curves spiraling outward from it, with expiry estimated for February 2034 [US 9,164,503]. Its citing documents include toolpath patents of Plethora, D.P. Technology and Siemens [US 9,164,503].

The freedom-to-operate review covers the family, continuations, other vendors' engagement-control patents and every execution path; adaptive clearing ships only after counsel's opinion.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Face, pocket, contour and rest (2.5D) | Region and depth steps → offset or zigzag passes, island-aware, ramp or helix entry; rest passes only where material remains | `Unreachable` where narrower than the tool | MFG-O-MILL-1 | 2 |
| Adaptive clearing and trochoidal slotting | D-MFG-7; trochoids with parameters varied per period [Li et al. 2025] | `Infeasible` with region and achieved maximum | MFG-O-MILL-2 | 2, after the opinion |
| Parallel, scallop and waterline finishing | `tool_contact` sampling to chord tolerance; constant scallop; steep-and-shallow split | Unreachable areas reported | MFG-O-MILL-3 | 2 |
| Pencil, flowline and isoparametric | Bi-tangent corner passes; iso-curves re-spaced to a scallop bound | Degenerate parameterization typed | MFG-O-MILL-3 | 2 |
| Deburr, chamfer, engraving and thread milling | Edge-chain passes at target size; V-carve from the medial axis; analytic helices | Unreachable edges; `Infeasible` tool fit | MFG-O-MILL-4 | 2 |
| Drilling cycles | Spot, drill, peck, ream, bore, tap, back-bore from MEC's `HoleSpec`; shortest tour | `Unsupported` cycle → expanded moves | MFG-O-MILL-4 | 2 |
| Probing paths | Touch points from the inspection plan | Unreachable points reported | MFG-O-SETUP-2 | 2 |
| 5-axis swarf, multi-axis and barrel finishing | Flank passes on ruled walls; collision-aware tilt from any 3-axis pattern; barrel profiles tangent to the surface | `Infeasible`, `Collision` or `AxisLimit` with fixes | MFG-O-MILL-5 | 3 |
| 5-axis roughing | Adaptive clearing in tilted frames chosen by access analysis | As adaptive | MFG-O-MILL-2 | 3 |

## Turning, EDM, gears and grinding

GP3 needs turning and gear cutting in phase 2. MEC owns gear geometry and rating; EDM technology tables come from machine packages, and MFG does not model spark physics.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Turning | Revolved Body → XZ profile; rough, finish, groove, part and thread passes with insert clearance | `Infeasible` for non-revolved faces; `Unreachable` undercuts | MFG-O-TURN-1 | 2 |
| Adaptive turning | Constant chip-thickness roughing for heat-resistant alloys [Janus NX 2606] | As above | MFG-O-TURN-1 | 3 |
| Mill-turn | C and Y milling, B tilting, sub-spindle transfer across channels | `Infeasible` with the conflicting window | MFG-O-TURN-2 | 3 |
| Swiss-type and channel balancing | Sliding headstock and gang tools; workingsteps assigned to channels | As above | MFG-O-TURN-2 | 4 |
| Wire EDM | 2-axis rough and skim with tabs; 4-axis taper with synchronized UV paths | `Infeasible` below wire radius plus overburn | MFG-O-EDM-1 | 3 |
| Sinker EDM electrodes | Electrode Body with spark gap, orbit and burn sequence | Typed error when not machinable | MFG-O-EDM-1 | 4 |
| Gear generating | Hobbing, shaping and power skiving from MEC's gear record through machine cycles | `Unsupported`; fix: 5-axis gear milling | MFG-O-GEAR-1 | 2 |
| 5-axis gear milling | Flank and root passes from the multi-axis strategies | As 5-axis | MFG-O-GEAR-1 | 3 |
| Gear inspection | Profile, helix and pitch plans for gear machines or CMMs | As inspection | MFG-O-GEAR-2 | 2 |
| Grinding, broaching, honing and lapping | Gear and profile grinding with distortion allowance; surface and cylindrical grinding with a burn-risk Field [unverified]; process records | `MissingData`; `OutsideEnvelope` for unmodeled pairs | MFG-O-GEAR-1 | 4 |

## Sheet cutting, nesting and press brake

GP4's guards need profile cutting, nesting and press-brake planning in phase 2. MEC owns flat patterns, flat DXF export, the bend-allowance model (`BendRule`, `BendTable`) and self-clinching hardware rules.

Sparrow (MIT) is the strongest published 2D irregular strip-packing heuristic, using guided local search on the jagua-rs collision engine (MPL-2.0) [Gardeyn et al. 2025; jagua-rs]. In 20-minute runs it matches or beats every best-known ESICUP density, most on SWIM (79.83% versus 75.94%) [Gardeyn et al. 2025]. It does not exploit repeated patterns.

**Decision D-MFG-8:** Press-brake sequencing is a search over bend orders with collision checks between the partially bent part, punch, die and machine. The bend allowance comes from MEC's sheet-metal model, and springback from Flux or measured data. *Why:* one search handles every part, and the physics stays in its owning tabs. *Rejected:* rule tables per part family (brittle, not general).

**Decision D-MFG-9:** The 2D nesting Wasm component adopts the sparrow approach on a jagua-rs-style collision engine. Wall-clock limits are replaced by work-unit budgets and seeded portfolios (D-MFG-3). *Why:* these are the leading open methods, both are Rust and both permit Wasm builds. *Rejected:* no-fit-polygon placement heuristics (lower density in published comparisons); closed vendor libraries (unauditable, license-bound).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Profile cutting and ordering | Laser, plasma or waterjet paths with kerf, lead-ins, micro-joints, pierce strategy, common lines; inner before outer, heat spread, minimal rapids | `Infeasible` below kerf plus minimum web | MFG-O-CUT-1 | 2 |
| Flat-pattern hand-off | MEC's `export_flat_dxf` (MEC-O-SM-4) with the layer convention and bend table chosen per cutting machine or shop | Unmapped entities listed | MFG-O-CUT-2 | 2 |
| Press-brake planning | Bend sequence, tool stations and backgauge (D-MFG-8); allowance tables per punch, die and material for MEC's `BendTable` | `Infeasible` with the colliding bend | MFG-O-CUT-3 | 2 |
| Waterjet taper, bevels and punching | Taper and corner compensation (3); 5-axis bevels (4); turret tooling, nibbling, repositioning (3) | `MissingData`; `AxisLimit`; missing tool | MFG-O-CUT-1 | 3, 4 |
| Sheet nesting | `nest(items, sheets, rules, seed, budget) -> Nest` with rotation, grain, spacing, zones and common lines | `Infeasible`; `BudgetExhausted` with the best nest | MFG-O-NEST-1 | 2 |
| Remnants, associativity and inventory | Remnant Parts; warm-started regeneration; mixed sheets and remnants by cost (3) | As nesting | MFG-O-NEST-1 | 2, 3 |

## Feeds, speeds and chatter

**Decision D-MFG-27:** Feeds and speeds default to the tool record's vendor cutting data or the shop's proven values, labelled by source. The mechanistic model runs as an advisory check that flags power, torque, chip-thickness and deflection violations; calibrated coefficients upgrade the label without changing the default flow. *Why:* shops start from vendor tables and proven values, and an uncalibrated user would otherwise get `MissingData` on every toolpath (R4-36). *Rejected:* mechanistic optimization as the default (it needs calibration first); vendor values without a label (hides their basis).

With calibrated coefficients, `cutting_conditions(toolpath, material, machine, objective)` returns feed and spindle Fields that maximize removal rate. They are piecewise constant, quantized to the controller increment, and reported with each segment's binding constraint. A calibration program cuts at varied feed and engagement and fits coefficients with uncertainty.

MFG's own receptance-coupling model gives the tool-tip frequency response from measured spindle FRFs and Flux's modal analysis of tool and holder. A tap test stored as a Field can replace it. Zero-order lobes are fast and accurate above about quarter-diameter immersion but miss lobes that semi-discretization finds at low immersion [Altintas et al. 2008].

**Decision D-MFG-10:** `Interactive` stability lobes use the zero-order solution and `SignOff` lobes use semi-discretization. Low radial immersion, variable-pitch tools and spindle-speed variation always use semi-discretization. *Why:* this matches each method's published validity and keeps interactive updates under one second. *Rejected:* zero-order everywhere (misses lobes at low immersion, which adaptive clearing uses constantly); time-domain simulation as the default (too slow for interactive use, kept as a reference oracle).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Source-labelled defaults and calibration | D-MFG-27; calibration cuts fit coefficients with uncertainty | `MissingData` only when no source exists; poor fits reported | MFG-O-FEED-1 | 2 |
| Advisory constraint check | Chip thinning, mechanistic force and power, spindle curve, kinematic roughness, cantilever or Flux deflection | `OutsideEnvelope` outside calibrated ranges | MFG-O-FEED-2 | 2 |
| Feed optimization and tool life | `cutting_conditions`; extended Taylor life per tool-material pair | `OutsideEnvelope`; never an extrapolated feed | MFG-O-FEED-3 | 3 |
| Tool-tip FRF | `frf(tool, machine) -> Field<Frequency, Complex<Compliance>>` | `MissingData` without spindle receptance; fix: tap test | MFG-O-CHAT-1 | 3 |
| Stability lobes and planning | `lobes(frf, coefficients, engagement) -> Field<AngularVelocity, Length>` with bands (D-MFG-10); speed and depth inside the stable region | `OutsideEnvelope` at low surface speed (no process damping); no stable speed reported | MFG-O-CHAT-1 | 3 |
| Chatter feedback | Spindle-load or vibration data flags chatter and updates the FRF | None | MFG-O-CHAT-1 | 4 |

## Machining simulation and NC verification

Simulation interprets the posted NC text under the controller's motion semantics (D-MFG-23). Continuous collision detection uses conservative advancement on bounding-volume hierarchies, so thin parts never slip between samples.

ModuleWorks states that more than 60% of leading CAM vendors use its 5-axis library [ModuleWorks]. Adaptive GPU tri-dexels report about a fivefold speedup [Ozcan et al. 2024].

The crash corpus plants dog-leg rapids, rotary unwinding, reference returns through parts, wrong retract planes, compensation-entry gouges and tool changes inside the envelope.

**Decision D-MFG-28:** A product NC interpreter, separate from the oracle's interpreter, verifies any NC text, including programs from other CAM systems and hand programming. `verify_nc` returns stock, collisions, gouges, cycle time and a `BlockMap`, and legacy programs import as Assets released as program Items (contract 2) that are never converted to workingsteps. *Why:* shops hold thousands of proven programs and need them verified and under revision control, and two interpreters keep the oracle independent (R4-09). *Rejected:* one interpreter for product and oracle (a shared bug passes both); converting legacy NC into workingsteps (guesses intent).

UIX's Manufacture mode shows NC text beside the toolpath with two-way highlighting through `BlockMap`, and a setup-sheet preview.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Material removal and leftover | `simulate(program)` streamed coarse to fine (D-MFG-6); signed stock-to-design distance Field | `OutsideEnvelope` when the grid cannot meet the tolerance | MFG-O-STOCK-1 | 2 |
| Certified gouge check | Per cutting move, certified distance between the exact swept envelope (`swept_volume`, `tool_contact`) and the design B-rep | `Gouge` with depth and block | MFG-O-SIM-1 | 2 |
| Machine collision and clearance | Continuous detection between links, tool, holder, fixture and stock along every posted move; near-miss Field against clearance | `Collision` with block, pair and fixes; warning below clearance | MFG-O-SIM-2 | 2 (to 3+2), 3 (5-axis) |
| Controller motion | Rapids, unwinding, reference returns, retract planes, compensation entry and tool-change envelopes | `Unsupported` for undeclared semantics | MFG-O-SIM-2 | 2 |
| External NC verification | `verify_nc(nc: Asset, machine, setup, tools) -> NcVerification`; legacy programs as program Items on the same approval path | Parse errors with the block | MFG-O-SIM-3 | 2 |
| Cycle time | Jerk-limited kinematics with look-ahead, tool changes and dwell | None; time per workingstep | MFG-O-SIM-4 | 2 |
| Viewer cache | GPU tri-dexel render cache for playback, never a model | CPU rendering fallback | MFG-O-SIM-5 | 2 |

## Programs, regeneration and agents

A workingstep finds its target through a `Query`, so Kiln recomputes only workingsteps whose inputs changed, and a lost target is a `ResolveError`. Templates are ordinary Ingot in the shop's package:

```
use std::mfg::{adaptive, finish_walls, StrategyCall, Pocket, Machine}

pub fn pocket_alu(p: Pocket, m: Machine) -> [StrategyCall] {
    let rougher  = shop::em_10mm_3fl
    let finisher = shop::em_6mm_4fl
    let rough = adaptive(p, tool: rougher, engagement: 12deg, stepdown: 1.5 * rougher.diameter)
    let walls = finish_walls(p, tool: finisher, allowance: 0mm, scallop: 2um)
    [rough, walls]
        .require(m.spindle.max_speed >= 12000rpm)
}
```

Native designs need no recognition: Ingot features know their holes, pockets and threads. Imported B-reps go through rule-based graph matching and a learned panoptic segmenter whose targets a person or agent confirms. AAGNet reaches 97.44% panoptic quality on MFInstSeg with full data, and FeatureFox exceeds 0.9 with about 250 parts [FeatureFox]; those are Crucible's targets.

Agents program as people do: Ingot on a branch, every oracle in CI, then a Proposal with rationale, cycle-time and tool-count deltas. AGT's CAM programmer role arrives in phase 2 with Crucible's CAM. CloudNC presents CAM Assist output as a draft to review [CloudNC CAM Assist], and NX 2606 suggests machining strategies [Janus NX 2606; Siemens Lambda Function].

STEP-NC is ISO 14649, in parts for process data, milling, turning, tools, EDM and additive [ISO 14649 catalog]. AP238 edition 3 (ISO 10303-238:2022) adds geometry, GD&T and kinematics [ISO 10303-238; STEP Tools AP238e3]. G-code stays the shop-floor output, since few controls run STEP-NC [unverified].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Incremental regeneration and diff | Only affected workingsteps recompute; geometric and technology diffs painted on geometry | `ResolveError` per lost target | MFG-O-PROG-1 | 2 |
| Templates, matching and setup planning | Ingot templates ranked by applicability predicates; targets grouped by access direction into setups | No match typed, never a silent default; `Unreachable` | MFG-O-PROG-2 | 2 |
| Target recognition | Rule-based (2) and learned (3) proposals; CPU inference with pinned weights | Unconfirmed targets never drive toolpaths | MFG-O-PROG-3 | 2, 3 |
| Agent-proposed programs | Branch, CI, Proposal, human Approval | Agents cannot approve, commit transfer Acts or edit oracles | MFG-O-PROG-4 | 2 |
| STEP-NC | ISO 14649 parts 10, 11, 12, 111 and 121 and AP238, read and written through ECO's codec at its catalog phase (3); parts 13, 14 and 17 (5) | `Unsupported` per workingstep; never invents feeds | MFG-O-PROG-5 | 3, 5 |

## Additive processes and build preparation

ISO/ASTM 52900:2021, confirmed in 2025, is the vocabulary standard [ISO/ASTM 52900]. Its seven categories, first formulated by ASTM F42 [Loughborough AMRG], share one pipeline: build, orient, pack, support, simulate, compensate, slice, emit.

| Category | Layer output | Phase |
| --- | --- | --- |
| Material extrusion (FFF, pellet, continuous fiber, concrete) | 3MF hand-off (1); G-code for Marlin, Klipper and RepRapFirmware, binary G-code (2) | 1, 2 |
| Powder bed fusion (laser, electron beam; metal, polymer) | 3MF production files for the vendor build processor (1); own scan vectors in 3MF Toolpath (2) | 1, 2 |
| Vat photopolymerization (SLA, DLP, mSLA) | Layer images with exposure | 2 |
| Material and binder jetting | Voxel or image stacks per material; layer bitmaps | 3 |
| Directed energy deposition | NC programs on the machining stack | 3 |
| Sheet lamination | Cut paths plus machining programs | 5 |

**Decision D-MFG-11:** The AM pipeline slices the design Body directly in any representation. It never converts to an STL as an intermediate step. Implicit lattices are sliced from their fields, and B-reps are sliced exactly, each with an `ErrorBound`. *Why:* triangulating a dense lattice is the bottleneck of conventional build preparation, and direct slicing removes both that cost and the facet error. *Rejected:* mesh-only pipelines (memory blow-up on lattices, faceting on curved faces).

**Decision D-MFG-25:** In phase 1, and for FFF until Crucible's slicer passes its comparison, Crucible hands builds to the user's slicer. It writes a 3MF build with plates, per-object orientation, modifiers and settings in the metadata that OrcaSlicer, Bambu Studio and PrusaSlicer read [unverified per slicer], and opens it there. *Why:* incumbent slicers carry years of printer and filament profiles, GP2 is printed with the vendor's slicer (contract 13.1), and some printers accept jobs only through the vendor's path (R4-13). *Rejected:* Crucible's slicer as the phase 1 default (unproven against those profiles); linking an AGPL slicer (contract 7.7).

Crucible's slicer serves what only it does: direct slicing of implicit lattices and Field-driven infill. It becomes the FFF default only after matching the reference slicers on the thin-wall corpus and on print time.

Bambu Connect "removes slicing functions while enabling remote control and print initiation", also in LAN mode [Bambu Lab 2025]. Crucible reaches Bambu printers only through that path.

Binary G-code follows the format description published with libbgcode, which is AGPL-3.0 and never linked [libbgcode].

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

Spectral packing computes every collision test for one placement as an FFT correlation of voxel grids and checks translational removability [Cui et al. 2023]. On the "pieces" benchmark it reaches 50.45% density in 103 s on a GPU; PolyDevs reaches 40.87% in 3,598 s [Cui et al. 2023].

**Decision D-MFG-12:** 3D packing adopts spectral packing. The correlation is the Anvil operation `anvil::correlate_grids`, collision counts use exact integer arithmetic, and proximity scores quantize to fixed point, with ties broken by grid index. *Why:* this is the best published density-speed trade-off, and integer collision counts make placements bit-identical across platforms, which floating-point FFT alone cannot guarantee. *Rejected:* heuristic bounding-box packers (low density); the floating-point method unchanged (platform-dependent argmin flips).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Orientation | `orient(part, printer, objectives, seed) -> [ParetoOrientation]` over support, height, critical faces, distortion, peel area and anisotropy against MEC load paths | Reports the front; never picks silently without weights | MFG-O-AM-1 | 1 |
| Slicer hand-off | D-MFG-25 3MF build for a named slicer | Settings the slicer cannot read are listed | MFG-O-AM-2 | 1 |
| Plate nesting and 3D packing | Footprint nesting (D-MFG-9); `pack(parts, volume, rules, seed, budget) -> Assembly`, interlock-free (D-MFG-12) | `Infeasible` when a part exceeds the volume | MFG-O-AM-3 | 2 |
| Supports | Tree supports (extrusion); point supports with peel and island checks (vat); block, line, cone and lattice supports (metal PBF) | Unsupported overhangs, islands and over-distorted regions with fixes | MFG-O-AM-4 | 2 |
| Labels and serials | Engraved or embossed identifiers linked to `repo` serials | Face too small | MFG-O-AM-4 | 2 |

## Slicing, lattices, process simulation and DfAM

Variable-width perimeters follow Kuipers, Doubrovski, Wu and Wang [Kuipers et al. 2020]. PrusaSlicer, OrcaSlicer and CuraEngine are AGPL-3.0 [PrusaSlicer; OrcaSlicer; CuraEngine], so Crucible implements the paper and uses them only as external reference oracles. Curved layers follow the quaternion-field framework of Zhang and colleagues [Zhang et al. 2022].

MEC's `lattice` feature generates TPMS and strut lattices from Flux density Fields; MFG checks them against printer limits and writes them without meshing.

**Decision D-MFG-13:** Distortion compensation is a geometry operation driven by a Field. MFG simulates the build, inverts the displacement Field, and applies it to the Body with `anvil::deform`. It iterates until the predicted as-built shape is within tolerance. *Why:* this uses the contract's "Fields driving geometry" mechanism, works on all four representations, and keeps the design Body untouched. *Rejected:* mesh-only morphing in an export step (breaks associativity and loses the B-rep).

FLX owns inherent-strain layer activation and prediction, from MFG's calibration coupons. The method is layer-lumped, so it needs per-machine calibration and cannot see melt-pool effects [unverified], which COV owns. DfAM checks are `require` predicates parameterized by the printer profile, each failure giving region, value, limit and fixes.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| DfAM checks | Minimum wall and detail from `anvil::thickness`, overhang, bridging, trapped powder or resin, drain holes, lattice strut and wall thickness (1); thermal-mass changes, slender features, support removal, machining allowance (2) | Located failures with fixes | MFG-O-AM-5 | 1, 2 |
| Conformal lattices and as-built struts | Cells mapped by a parameterization; as-printed strut diameters calibrated per process | Cells above a distortion bound reported | MFG-O-AM-5 | 2 |
| Planar slicing | `anvil::section` per layer on any representation, with `ErrorBound` (D-MFG-11) | Open contours name the defective faces | MFG-O-AM-6 | 2 |
| Extrusion, PBF and vat layers | Adaptive layer height, variable-width perimeters, Field-driven infill, seams and travel; hatch, stripes, islands and skin sets; anti-aliased masks | Regions thinner than one bead reported; `OutsideEnvelope` outside the profile | MFG-O-AM-6 | 2 |
| Multi-material, DED and curved layers | Per-region materials from Fields (3); bead paths on the machining stack (3); isosurface layers (4) | `MissingData`; `Collision`; `Infeasible` without a collision-free order | MFG-O-AM-6 | 3, 4 |
| Inherent-strain distortion | Layer-lumped strain from coupons, solved elastically by Flux | `OutsideEnvelope` outside the calibrated set | MFG-O-AM-7 | 1 |
| Recoater risk and thermo-mechanics | Displacement above recoater clearance (2); bead activation with plasticity for DED (3); PBF layer thermo-mechanics on COV's model (4) | Located failure; `OutsideEnvelope` at melt-pool scale | MFG-O-AM-7 | 2, 3, 4 |
| Compensation | Iterative pre-deformation (D-MFG-13) | `Infeasible` with the residual | MFG-O-AM-8 | 2 |
| Cure, sintering and warp | Vat working curve (2); binder-jet shrinkage and FFF warp (4) | `MissingData` without constants; `OutsideEnvelope` | MFG-O-AM-9 | 2, 4 |

## Printers, 3MF and print transfer

Printer profiles are packages holding the printer Assembly, parameter sets with envelopes, material profiles and calibration programs such as OrcaSlicer's flow and retraction prints [OrcaSlicer]. Calibrated values record date, serial and uncertainty. The 3MF suite is ISO/IEC 25422:2025; the Toolpath extension was updated on 17 September 2026 and is still a draft [3MF specifications; 3MF Toolpath].

ECO's catalog owns 3MF versions and writer phases: Core, Production, Materials and Properties and Beam Lattice in phase 1, Toolpath in 2, the rest in 3.

Every printer is reached through the machine gateway. Status is a Read (`read.machine_data`). Cancelling a job Crucible sent is the cancellation AGT declares for `send_print_job` and `start_print`, with no on-site confirmation; resuming is a new `start_print`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| 3MF production write | Build items, object references, UUIDs, materials, beam lattices and thumbnails through ECO's writer | Unsupported constructs listed, never dropped | MFG-O-AM-10 | 1 |
| Further 3MF extensions | Version-gated Toolpath (2); Boolean, Volumetric and Secure Content (3), through ECO's writer | Not written unless the target declares support | MFG-O-AM-10 | 2, 3 |
| Binary G-code | bgcode from the published description | Unsupported blocks listed | MFG-O-AM-11 | 2 |
| Printer profiles and calibration | Profiles with envelopes; calibration prints and coupons | `OutsideEnvelope` outside the profile | MFG-O-AM-11 | 2 |
| Print transfer and control | `send_print_job` to OctoPrint, Moonraker, PrusaLink and sanctioned vendor paths; the restricted `start_print`; cancellation of jobs Crucible sent | Never retried without a person; starts refused without contract 7.6 conditions | MFG-O-SAFE-2 | 2 |

## Molds and injection molding

Tooling is designed in Ingot as Parts and Assemblies, the process is simulated as Flux forms, and results are Fields that drive checks, compensation and inspection. MEC's `split_mold` returns core, cavity and side-action Bodies (phase 3); MFG supplies the shrink Field and designs the rest of the mold.

**Decision D-MFG-14:** Tooling geometry (cavities, cores, dies, patterns) is derived from the part by Anvil operations and remains associative. A part edit regenerates the tool, and tool-only edits (shutoffs, vents, cooling) are features applied to the derived Body. *Why:* associativity is the main lever against late tooling changes, and it reuses the `Query` regeneration machinery. *Rejected:* exported tool geometry edited separately (breaks the single model).

**Decision D-MFG-15:** Fill, pack and cool at `SignOff` run 3D non-isothermal solvers in Flux with a level-set fill front on the immersed octree for the Stokes-regime melt, with mass checks. A Hele-Shaw model on a mid-surface serves `Interactive` and is valid only inside a declared thickness-ratio envelope. *Why:* 3D handles thick sections and ribs that Hele-Shaw ignores, a level-set front conserves mass with a checkable error, and Hele-Shaw answers in seconds for thin walls (R1-41). *Rejected:* Hele-Shaw only (invalid for thick parts); 3D only (too slow for interactive design); an unnamed free-surface method. (revised in round 2)

**Decision D-MFG-29:** Short-fibre orientation uses an anisotropic rotary diffusion model with reduced strain closure (ARD-RSC) and a fitted closure, keeping Folgar–Tucker as the L0 model level (COV). Warpage comes from residual stress along the pvT path with frozen-layer pressure and mold constraint, plus crystallization kinetics for semicrystalline grades and optional viscoelastic relaxation after ejection. *Why:* Folgar–Tucker changes orientation too fast in concentrated suspensions, and pressure history and mold constraint dominate warpage accuracy (R1-41) [unverified: primary papers not opened]. *Rejected:* Folgar–Tucker alone; warpage from thermal shrinkage only.

The Hele-Shaw envelope defaults to local thickness under one tenth of local flow length, calibrated in phase 3 [unverified].

Moldflow covers fill, pack, cool, warp and process variants [Moldflow]. A short shot is a result (an unfilled-region Field with its frozen front), and non-convergence returns `Infeasible` with the last converged time.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Moldability and pull direction | Draft, undercut, thickness and sink-risk Fields; directions ranked by undercut area and side actions | Located failures with fixes; ties reported | MFG-O-MOLD-1 | 3 |
| Parting, shutoffs, core and cavity | Parting line from silhouettes; ruled or extended surfaces; MEC's `split_mold` with MFG's anisotropic shrink Field | `Infeasible` with the open loop; `ResolveError` | MFG-O-MOLD-1 | 3 |
| Side actions, ejection and mold base | Slides and lifters with travel; ejector pins with ejection force; standard plates and guides as catalog parts | `Collision` during opening; pin overload; unknown standards | MFG-O-MOLD-2 | 3 |
| Gates, runners, cooling and venting | Gate type and location, runner balancing, Pareto gate search; drilled, baffled and conformal channels; vents at air traps | Unmet constraints named; steel-distance violations; unvented traps | MFG-O-MOLD-2 | 3 |
| Fill, pack and cool | D-MFG-15 with Cross-WLF, Tait pVT, gate freeze and cyclic mold conduction | `OutsideEnvelope` outside the calibrated melt range; jetting out of scope | MFG-O-MOLD-3 | 3 |
| Fibre orientation, warpage and compensation | D-MFG-29; cavity pre-deformation by D-MFG-13 | `OutsideEnvelope` for long fibres; `Infeasible` when compensation stalls | MFG-O-MOLD-4 | 3 |
| Molding variants | Gas-assist, co-injection, overmolding, injection-compression, foaming | Each declared separately | MFG-O-MOLD-3 | 4 |

## Casting and bulk forming

Rule-based design precedes simulation, whose solidification comes from COV's physics package on Flux forms. HPDC jets atomize at gate velocities, which COV places out of reach (OOR-8). The gate Weber number is therefore a regime variable: above breakup, filling is `Extrapolated` and defect indicators are qualitative.

The dimensionless Niyama criterion was validated on WCB steel, A356 and AZ91D [Carlson and Beckermann 2009], and Crucible predicts porosity only for calibrated alloys. MAGMASOFT, the suite to match, adds virtual design of experiments [MAGMASOFT]; Crucible uses COV's generic exploration instead.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Patterns, gating and risers | Pattern with shrinkage, draft and allowance Fields, cores; ingates from fill time and pressurization ratio; risers by modulus and feeding distance | Velocities above the ingate limit; `Infeasible` with the isolated hot spot | MFG-O-CAST-1 | 4 |
| HPDC die and shot profile | Die halves, slides, overflows, vacuum vents, trim die; phases, switch-over, intensification | `OutsideEnvelope` beyond the machine | MFG-O-CAST-1 | 4 |
| Filling, solidification and die cycling | Free-surface filling with the Weber regime; enthalpy with fraction-solid curves; cyclic die steady state | `Extrapolated` above breakup, citing OOR-8; uncalibrated alloys | MFG-O-CAST-2 | 6 |
| Porosity and defect indicators | Dimensionless Niyama; air entrapment and cold shuts | Restricted to calibrated alloys | MFG-O-CAST-2 | 6 |
| Investment casting and hot tears | Wax trees, shells, radiation cooling; solidification stress | `OutsideEnvelope` for directional and single-crystal growth | MFG-O-CAST-2 | 6 |
| Forging and extrusion | Preforms and dies with flash, load and die stress by rigid-viscoplastic FEM; profile DFM and die bearings, portholes and bridges by ALE flow | Laps and folds flagged; seam welds out of scope | MFG-O-BULK-1 | 5 |
| Thermoforming | Molds with draft and vents; membrane thickness; trim programs | `OutsideEnvelope` outside the tested range | MFG-O-BULK-1 | 4 |
| Blow, rotational and compression molding | Parison and preform design; deposition wall thickness; SMC and BMC charge and flow | Rotational results flagged indicative | MFG-O-BULK-1 | 5 |

## Sheet forming

MEC owns sheet-metal design; MFG owns how sheet parts are made. AutoForm, the suite to match, covers die design, compensation, robustness, progressive dies and tubes [AutoForm].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Tube bending | Rotary-draw sequence, tooling, collision, thinning, ovality; springback from measured tables | `Collision` or `Infeasible` with fixes | MFG-O-FORM-1 | 3 |
| Blank development and formability | One-step inverse FEM; incremental shell FEM for thinning, strains and forming-limit margin | `OutsideEnvelope` outside calibrated curves | MFG-O-FORM-2 | 5 |
| Die faces, stages and progressive dies | Binder, addendum, beads, trim and flange lines; stages with tonnage; strip layout | `ResolveError`; `Infeasible` naming the stage | MFG-O-FORM-2 | 5 |
| Springback, compensation and robustness | Unloading analysis; compensation by D-MFG-13; capability Fields under variation | `OutsideEnvelope` without kinematic hardening | MFG-O-FORM-2 | 5 |
| Roll forming and hydroforming | Flower pattern and passes; pressure and feed paths with burst and wrinkle margins | Limits exceeded reported | MFG-O-FORM-2 | 5 |

## Welding, joining and composites

MEC owns weld joints, symbols and laminate design; MFG owns procedures, sequences, paths, distortion and laminate manufacture. Procedure, procedure-qualification and welder records follow ISO 15609-1, ISO 15614-1 and ISO 9606-1, or AWS D1.1 prequalified rules and ASME Section IX, with pinned editions [unverified editions]. The imperfection quality level (ISO 5817 B, C or D, or AWS D1.1 acceptance) sits on MEC's `Weld` record and drives MFG's inspection plans.

Torque control scatters preload through friction, so `tightening` picks torque-angle or yield control when MEC's preload range is narrow and states the resulting range.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Weld procedures and pass plans | WPS per joint linked to PQR and welder records; heat input and pass plans; visual and NDT plans per quality level | `MissingData` for unqualified combinations; `OutsideEnvelope` outside the qualified range | MFG-O-JOIN-1 | 2 |
| Weld sequencing and structure-scale distortion | Order and direction minimizing distortion and travel; inherent strain on shells or solids in Flux | Trade-off front; `OutsideEnvelope` for thick joints outside calibration | MFG-O-JOIN-2 | 2 |
| Joint-scale weld simulation | Transient thermo-elasto-plasticity with a moving heat source | Long runs flagged at `Interactive` | MFG-O-JOIN-2 | 4 |
| Robot weld paths | Torch angles, weaving and seam tracking | `Collision`, `Unreachable` | MFG-O-ASM-4 | 3 |
| Fastening specification | Method, target with scatter, sequence, tool and audit from MEC's preload range | `Infeasible` when scatter misses the range | MFG-O-JOIN-3 | 2 |
| Riveting, clinching and bonding | Fastener, pitch, edge distance and access; bead paths, bondline, preparation and cure | Rule failures; `MissingData` without adhesive data | MFG-O-JOIN-3 | 3 |
| Composite plates, plies and layup | Plate machining (3); MEC plies nested with grain; ordered plies with projector data (4) | Missing ply references reported | MFG-O-JOIN-4 | 3, 4 |
| AFP, ATL and cure cycles | Courses within steering, gap and overlap limits; cure cycle on COV's model with spring-in | `Infeasible` beyond steering limits; `OutsideEnvelope` without kinetics | MFG-O-JOIN-4 | 5 |

## Surface and heat treatment

Treatments are typed records attached to faces through Queries, plus routing steps whose dimensional and property effects downstream checks read. COV owns transformation and quench physics; MFG owns specification, routing, masking, inspection and dimensional consequences.

```
part.treat(anodize(type: hard, thickness: 50um ± 10um, seal: none))
    .mask(part.faces(threads) + part.face(mating))
part.heat_treat(solution_and_age(spec: shop::t6_6061), inspect: hardness(points: 3))
```

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Coating specification | Process, standard, thickness `Tol`, color, masking Queries, pre-treatment | Unknown standards; conflicting masks | MFG-O-TREAT-1 | 1 |
| Dimensional effect | Build-up per face as a Field, including substrate growth | `MissingData` without a growth ratio | MFG-O-TREAT-1 | 2 |
| Heat treatment and HIP | Recipes with hardness and case-depth targets (2); HIP and stress relief for AM (3); distortion from COV's phase-transformation models compensated by D-MFG-13 (6) | `OutsideEnvelope` when COV's models miss the alloy | MFG-O-TREAT-2 | 2, 3, 6 |
| Plating, paint and powder coat | Film thickness, cure, masking and spray paths (4); plating current distribution from COV's package (5) | `OutsideEnvelope` for unmodeled chemistry | MFG-O-TREAT-1 | 4, 5 |

## Electronics and harness manufacturing handoff

MFG owns the factory handoff: package choice, fabricator and assembler capability records and rule packs, panels, stencils, test strategy and the harness package. ELX owns the board model, the DRC engine that runs MFG's rule packs, the IPC-2152 current screen and `test_point` features; ECO owns every writer in `io/` and its phase. A board passes DFM for a specific fabricator and class, never in the abstract.

**Decision D-MFG-16:** The default fabrication package is IPC-2581 revision C together with Gerber X2 layers (Layer Format revision 2026.05), an XNC drill file and the Gerber job file, generated from one board model. ODB++ is the alternative for board houses that read it, from ECO's own writer in phase 3. MFG chooses the package per fabricator; ECO owns every writer, its phase and its oracles. *Why:* IPC-2581 is open and bi-directional [IPC-2581], revision C carries DFX feedback [IPC-2581C], Gerber is what fabricators most widely accept [unverified], and an open-source tool already writes ODB++ [KiCad 9.0] (R3-25, R4-24, R4-27). *Rejected:* Gerber only (no stackup, BOM or DFX feedback); ODB++ only through a licensed translator (weakens GP5's "outputs alone" gate at board houses that read ODB++). (revised in round 2)

Boards carry `fab_class` and `assembly_class` (Class 2, 3 or 3/A) that select rule packs citing IPC-6012, IPC-A-600, IPC-A-610 and J-STD-001, pinned in licensed packages [unverified revisions].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Fabrication package | Package choice per fabricator (D-MFG-16): IPC-2581C, Gerber X2, XNC drill and route, Gerber job file, impedance and stackup tables, or ODB++, all written by ECO's `io/` writers | Unsupported constructs listed per output | MFG-O-PCB-1 | 3 |
| Assembly package | Placement data, Gerber X3, assembly BOM with approved manufacturers, rotation conventions per line, assembly drawings | `MissingData` for parts without a rotation convention | MFG-O-PCB-2 | 3 |
| Classes, rule packs and fabrication drawing | Classes select annular ring, plating and acceptability rules; drawing notes for class, IPC-4101 material, finish, impedance tolerance and acceptance | A board without a class blocks the package | MFG-O-PCB-3 | 3 |
| Panels, stencils and reflow | Rails, tabs, V-score, fiducials and coupons, mixed panels by nesting, tab stress in Flux; apertures with area ratios and step stencils; reflow limits from paste and part ratings | `Infeasible` beyond line limits; apertures below the ratio; `OutsideEnvelope` without ratings | MFG-O-PCB-4 | 3 |
| Fab DFM and assembly DFA | Rule packs on ELX's DRC engine (annular ring, spacing, slivers, acid traps, copper balance; part spacing, tombstoning, shadowing, rework access); feedback as IPC-2581C DFX records | Located failures with fixes | MFG-O-PCB-5 | 3 |
| Test access and programs | Coverage, probe spacing and fixture side; a Proposal adding ELX `test_point` features where access is missing; flying-probe and bed-of-nails data; boundary-scan handoff | Untestable nets reported | MFG-O-PCB-6 | 3 |
| Box build | Board Instances feed sequence planning and work instructions | As assembly | MFG-O-ASM-1 | 3 |
| Harness manufacturing package | 1:1 formboard from MEC geometry with branch lengths and tolerances; connector face views from the mating side with cavity numbers; cut list with gauge, colour, cut and strip lengths; terminals and seals with crimp height and pull force; splices, markers, coverings; BOM in length units; continuity and insulation test netlist; IPC/WHMA-A-620 class [unverified revision] | `MissingData` for terminals without crimp data | MFG-O-HARN-1 | 4 |

## Assembly and work instructions

Tian and colleagues plan assembly by disassembly with physics simulation, handling screws and puzzles and 80-part assemblies in minutes [Tian et al. 2022]. The branch, bound and remember algorithm solves all 269 Hoffmann, Talbot and Scholl line-balancing instances optimally, under half a second on average [BB&R].

**Decision D-MFG-17:** Assembly sequence planning is disassembly search over continuous collision-free motions: translations, screw motions and short compound paths. Gravity stability of each sub-assembly is checked with Flux rigid-body contact, and the output is an AND/OR precedence graph. *Why:* disassembly from the final state handles tight clearances and fasteners that forward planning misses. One graph also feeds line balancing, work instructions, repairability and recyclability. *Rejected:* direction-cone heuristics only (fail on screws and interlocking parts); hand-entered precedence (not regenerated from geometry).

Robots are Machines sharing kinematics, collision and posts with machine tools. Robot programs are proved first in manual reduced-speed mode and never change safety-rated zones or speed limits. The safety documentation cites ISO 10218-1:2025 and ISO 10218-2:2025 [unverified].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Disassembly, sequences and fastening steps | `disassemble(assembly, seed, budget) -> PrecedenceGraph`; sequences minimizing reorientations and unstable states; fasteners as steps with tool and torque | `Infeasible` listing interlocked Instances; `MissingData` without specifications | MFG-O-ASM-1 | 2 |
| Tool and hand access | Swept volumes of tools and hands per step | `Unreachable` with fixes | MFG-O-ASM-1 | 3 |
| Design-for-assembly | `dfa(assembly) -> DfaReport`: separate-part test, handling and insertion times from tables after Boothroyd and Dewhurst [unverified], efficiency index | Instances without data listed as undetermined | MFG-O-ASM-2 | 2 |
| Work instructions | Steps with exploded views, animations, tools, torques, checks and safety notes; glTF 2.0 with an accessible HTML viewer and PDF (2); OpenUSD and locales (3) | Steps without a view; missing translations | MFG-O-ASM-3 | 2, 3 |
| Robot programming | Targets, external axes and positioners, collision-free planning on a counter-based seed; posts to RAPID, KRL, FANUC TP, INFORM and URScript [unverified] without safety configuration; cycle time | `Unreachable`; `BudgetExhausted` with the best plan; `Unsupported` per instruction | MFG-O-ASM-4 | 3 |
| Line balancing | Stations for a takt or takt for a station count (3); mixed models, zoning, skills and two-sided lines, times from standards or measurements (4) | `Infeasible` when a task exceeds takt; gap to the bound | MFG-O-ASM-5 | 3, 4 |

## Inspection and measurement

MEC owns GD&T semantics; MFG owns how characteristics are measured, evaluated and reported. QIF is ISO 23952:2020, confirmed in 2026 [ISO 23952]; DMIS remains common for CMMs [unverified].

A part measurement is an Evidence record addressed by its characteristic check and the part's `GeometryId`s. Evaluation reads the newest valid record, and releases pin the ones they cite.

**Decision D-MFG-18:** Characteristics are first-class records generated from the design's GD&T, each with a stable identity derived from provenance. The inspection plan, CMM program, results, SPC, FAI and PPAP all reference those identities. *Why:* one identity per characteristic lets a design diff compute exactly which characteristics changed, which drives partial first-article inspection and re-validation. *Rejected:* balloon numbers as identity (renumbering breaks traceability); documents as the source of truth (they drift from the model).

**Decision D-MFG-26:** Each characteristic's printed balloon label is allocated once per identity, never reused, kept while the characteristic is unchanged, and renumbered only by an explicit command. Each release produces the ballooned PDF that Form 3, inspection plans and reports cite. *Why:* AS9102 revision C defines ballooned design characteristics and ballooned documents [IAQG 9102C], and shops need labels that stay put (R4-14). *Rejected:* labels as identity (D-MFG-18); renumbering on every release (breaks open reports).

MEC draws the labels as a characteristic-balloon annotation. A customer PDF without a model imports as a controlled document whose balloons are placed by hand or by an agent extraction Proposal, creating typed characteristics. The GUM is JCGM 100:2008 with Amendment 1 (2026); JCGM 101, 102 and 106 cover Monte Carlo, multiple outputs and conformity [BIPM JCGM].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Characteristics and balloons | Extraction of dimensions, controls, notes and special characteristics; labels per D-MFG-26; foreign drawings with page coordinates | Unresolved characteristics reported; label conflicts fail the release | MFG-O-INSP-1 | 2 |
| Method selection and sampling | CMM, gauge, scan, vision or functional test by uncertainty ratio and measured %GRR; point counts for a target uncertainty | `Infeasible` when no method meets the ratio | MFG-O-INSP-2 | 3 |
| CMM paths and programs | Collision-free paths with articulating heads; DMIS and QIF Plans; on-machine probing through posts | `Unreachable` points with fixes | MFG-O-INSP-2 | 3 |
| Results as Evidence records | QIF Results and DMIS output → signed Evidence records on characteristics | Unmatched results reported | MFG-O-INSP-3 | 3 |
| Feature evaluation | Least squares, minimum zone, inscribed and circumscribed fits; datum frames; tolerances on scans | `OutsideEnvelope` for thin coverage | MFG-O-INSP-4 | 3 |
| Scan registration and deviation | Robust or datum-constrained alignment; signed deviation Field with scanner uncertainty | Residual reported; gaps as regions | MFG-O-INSP-4 | 2 |
| Uncertainty budgets and decisions | Typed budgets with Flux sensitivities (2); JCGM 101 Monte Carlo and JCGM 106 guard bands (3); virtual CMM (4) | Unit errors at compile time; `MissingData` without error models | MFG-O-INSP-5 | 2, 3, 4 |

## Quality records: SPC, MSA, FAI and PPAP

Process profiles declare Cp and Cpk per process and feature class. MEC's default distribution (`std::mech::tol::default_distribution`, D-MEC-28) reads them: uniform without data, normal with mean shift and spread with data (R1-37).

Per the IAQG summary of 9102 revision C, FAI is not product acceptance, each item needs its own FAI, and Form 1 gains "FAIR Verified By" [IAQG 9102C]. AIAG lists PPAP-4 [AIAG PPAP] and the AIAG & VDA FMEA Handbook [AIAG-VDA FMEA]; its 7-step structure and action priority are [unverified in the handbook itself].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Process capability profiles | Declared Cp and Cpk (2); computed from SPC data (3) | Unknown capability reported, never assumed | MFG-O-QUAL-1 | 2, 3 |
| SPC | Control charts (X-bar and R or S, individuals, p, np, c, u, EWMA, CUSUM), run rules as data, Cp, Cpk, Pp and Ppk with intervals; signals linked to machine, program and tool (4) | `MissingData` below the subgroup minimum | MFG-O-QUAL-1 | 3, 4 |
| Measurement system analysis | Gauge R&R by average and range and by ANOVA, bias, linearity, stability, attribute agreement | `MissingData` below the study design | MFG-O-QUAL-1 | 3 |
| AS9102 and partial FAI | Forms 1 to 3 from BOM, routing, certificates and results; partial scope from the design diff through D-MFG-18 | Missing fields and unmeasured characteristics block the report | MFG-O-QUAL-2 | 3 |
| Nonconformance | Reports linked to serials, characteristics and dispositions | None | MFG-O-QUAL-2 | 3 |
| PPAP, FMEA and control plans | 4th-edition elements with the level 1 to 5 retention matrix and customer overlays; 7-step PFMEA and DFMEA with action priority; controls linked to characteristics; special-characteristic symbols as data | Missing elements and uncontrolled special characteristics listed | MFG-O-QUAL-3 | 4 |

## Cost and sourcing

aPriori estimates cost, cycle time and CO2e from CAD geometry with physics-based process models [aPriori]. Crucible costs the actual process plan where one exists and geometric proxies otherwise, so phase 1 costs GP1 by proxies and GP2 from its build.

**Decision D-MFG-19:** Cost is a typed roll-up over the process plan, carried as `Money<C>` with a price date and an uncertainty interval, and painted on Bodies as cost-density Fields. Each estimate states its basis: `parametric` (geometric attributes), `planned` (generated routings and programs) or `quoted` (a supplier offer). *Why:* one mechanism serves every process and makes the estimate's basis visible, and cost painted on faces shows which features drive it. *Rejected:* a separate costing database (drifts from the design); single-number estimates (hide uncertainty); calling the basis a fidelity (contract 2 reserves that word). (revised in round 2)

Cost elements are material and scrap, machine and setup time, labor, consumables, energy, tooling amortization, overhead and logistics. Supplier records, offers, prices and rates are External inputs, and review flags inputs older than a declared age. Supplier endpoints live only in KLN's recipient records (R5-05), and data leave a tenant only through AGT's single Act family (R5-06).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Parametric cost | Regressions on geometric attributes per process family with stated training data and error | `OutsideEnvelope` outside the training range | MFG-O-COST-1 | 1 |
| Planned cost | `should_cost(part, routing, rates, qty) -> Cost` with `Money` per element, a total interval and a cost-density Field | `MissingData` for unknown rates; never an unflagged default | MFG-O-COST-2 | 1 (AM), 2 (machining, sheet, weld), 3 (molding), 4 (others) |
| BOM roll-up and currency | `repo` EBOM query × item cost plus assembly labor; rates as dated External inputs, no implicit conversion | Items without cost listed; `Money<Eur> + Money<Usd>` fails to compile | MFG-O-COST-3 | 1 |
| Volume curves and target costing | Cost against quantity with tooling breakpoints; targets allocated down the BOM as checks | Failures name the largest contributors | MFG-O-COST-3 | 2 |
| Quote requests | `request_quote` Acts carrying a released package to ECO's partner connectors (ECO's phase 2); quotes return as External inputs | Errors typed; never in evaluation | MFG-O-COST-4 | 2 |
| Suppliers and alternates | Processes, envelopes, materials, tolerances, certifications (AS9100, IATF 16949, ISO 13485), capacity; matching to routing steps; alternates with MEC and ELX form-fit-function checks | Expired certifications; unmet requirements listed; unchecked alternates blocked | MFG-O-SRC-1 | 2 |
| Make-or-buy, lead time and risk | Plan against quotes with risk and lead-time intervals; single source, geography, lifecycle and compliance as a per-Instance Field | Missing data reported; unknown scores as unknown, never low | MFG-O-SRC-2 | 3 |

## Factory connection and digital twin

MTConnect 2.5.0 Part 1 was prepared on 5 January 2026, and its REST API is "read-only and does not produce any side effects" [MTConnect 2.5]. OPC 40501-1 (Machine Tools) is at 1.02.0 [OPC 40501-1] and OPC 40001-3 (Machinery Job Management) at 1.0.1 of 1 May 2024 [OPC 40001-3]. The async-opcua client is MPL-2.0 [async-opcua], linked unmodified under contract 7.7.

**Decision D-MFG-20:** Machine data enter through two native adapters, MTConnect and OPC UA, running in the gateway or on servers outside evaluation. Both read; OPC UA additionally calls only non-motion job management (`Store` inside `store_machine_job`; `Cancel` and `Clear` on jobs Crucible stored). Collected data become External inputs signed by the gateway's device key. *Why:* both are open standards with published information models, reads cannot move a machine, and signed inputs keep evaluation deterministic (R4-01, R5-18). *Rejected:* vendor protocols in the core (they are connectors); live data inside evaluation (breaks determinism); OPC UA writes wherever a server allows them (a write can start motion). (revised in round 2)

ECO specifies the `erp-connector` and `mes-connector` worlds in `crucible:connect` with OAGIS and B2MML messages (D-ECO-30) [unverified versions]. MFG supplies routings and reads costs, lead times and inventory back as External inputs.

Routing steps reference MBOM Instances without copying them. The digital twin is the design plus as-planned, as-run and as-measured records per serial, and calibration is always a Proposal.

[[DIAGRAM: Factory feedback loop. Boxes: released design and plans in repo (as-planned) → machine gateway (MTConnect and OPC UA reads, offset reads, edit capture) → signed External inputs (as-run) and Evidence records from QIF (as-measured) → comparison per serial (deviation Fields, cycle-time and tool-life residuals) → calibration Proposal with held-out error before and after → human Approval → updated cutting data, distortion calibration, capability profiles and cost rates → next evaluation. Side arrow from the comparison to nonconformance and SPC events.]]

AOUSD announced OpenUSD Core Specification 1.0 on 17 December 2025 [AOUSD Core 1.0]. USD is an export target, never the source of truth.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Gateway | Shop-network gateway for machines, printers and CMMs; device key under measured boot; offline buffering | Gaps recorded explicitly | MFG-O-FAC-1 | 2 |
| MTConnect and OPC UA adapters | Observations on axes, spindles, programs, tools and offsets (MTConnect, at ECO's reader phase); Machine Tools and Machinery models, job orders mapped to routing steps (OPC UA) | Schema and security-policy failures typed; partial data marked | MFG-O-FAC-2 | 3 |
| MES and ERP mapping | Work orders, routing status, scrap and labor; routing fields through the `erp-connector` and `mes-connector` worlds | Mapping errors per field | MFG-O-FAC-3 | 4 |
| MBOM and routings | EBOM-to-MBOM rules as Ingot (phantoms, kits, stations, consumables); routing steps with times and work centers (2); effectivity by serial, date, work order or lot (3) | Unconsumed items; unmapped work centers; overlaps rejected | MFG-O-FAC-4 | 2, 3 |
| OpenUSD export | Cells as USD layers with joints and prim paths from `EntityId`s, process animation (3); incremental layers (4) | Unsupported constructs listed | MFG-O-FAC-5 | 3, 4 |
| As-built records and deviation | Per serial: lots, revisions, operators, deviations, nonconformances, Evidence records, deviation Fields | Gaps flagged, never back-filled with nominal values | MFG-O-FAC-6 | 3 |
| Model calibration | As-run data update coefficients, cycle-time factors and distortion calibration through Proposals | Updates outside declared bounds need human approval | MFG-O-FAC-7 | 4 |
| Product twin export | As-built Assembly with measured Fields for FMI or SSP co-simulation | Missing measurements flagged as nominal | MFG-O-FAC-5 | 5 |

## Sustainability and compliance

ISO 14044:2006, amended in 2017 and 2020 and confirmed in 2022, sets LCA requirements [ISO 14044]; ISO 14040's current edition is [unverified]. MFG computes the cradle-to-gate inventory from the process plan and end of life from the disassembly graph.

ESPR, Regulation (EU) 2024/1781, has been in force since 18 July 2024 [EU ESPR]. Implementing Regulation (EU) 2026/1778 of 16 July 2026 sets the registry arrangements [EUR-Lex 2026/1778]. The registry opened on 20 July 2026, with registration "through a web interface or an API" [Transition Pathways DPP].

Implementing Decision (EU) 2026/1736 references EN 18216, 18219, 18220, 18221, 18222 and 18223 [EUR-Lex 2026/1736]. EN 18239, EN 18246 and the delegated-act timetable come from vendor summaries [unverified] [Renoon DPP updates; Renoon delegated acts]. Article 10(4) requires a back-up copy through a passport service provider, an independent third party under Article 2(32) [EU ESPR].

**Decision D-MFG-21:** The Digital Product Passport is generated from the released model, as-built records and LCA. Each delegated act is a versioned package that maps Crucible queries to the required data elements. The `publish_passport` Act publishes to the operator's chosen passport service and mirrors a back-up copy to a second, independent provider named in the package; nothing is published from evaluation. *Why:* requirements differ per product group and keep changing, so the mapping must be data, while content must trace to the model, and ESPR requires the back-up copy (R5-35). *Rejected:* one hard-coded schema (wrong for every product group); manual passport forms (drift from the product). (revised in round 2)

Regulation (EU) 2017/821 "will only apply directly to EU-based importers of tin, tantalum, tungsten and gold" [EU conflict minerals]. MFG therefore returns a data-completeness check on 3TG sourcing data, never a compliance verdict (R5-34). Regulation packages carry dated lists, since the ECHA Candidate List page displayed incompletely when fetched [ECHA Candidate List].

A release fails on a missing required declaration unless a person records a time-bounded waiver in the change order.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Embodied carbon | Global warming potential per BOM line from COV's per-material `EnvironmentalRecord`s, as per-Instance and density Fields; supplier data override generic factors | Generic versus specific flagged | MFG-O-SUST-1 | 2 |
| LCA scope and inventory | Typed functional unit, boundary and allocation; flows from materials, power over cycle time, consumables, scrap and transport | Missing scope fails to compile; flows without factors reported, never zeroed | MFG-O-SUST-1 | 3 |
| Impact, hotspots and uncertainty | Versioned factor packages (EF or ecoinvent under licence [unverified versions]); contributions; Monte Carlo (4) | Unlicensed datasets unavailable, never substituted | MFG-O-SUST-2 | 3, 4 |
| Recyclability and repairability | Recoverable mass per stream from the disassembly graph; contaminating joints; depth, time and tools to each service part | Unlisted materials count as unrecoverable; `Unreachable` service parts | MFG-O-SUST-3 | 3 |
| Passport mapping and identifiers | Delegated-act elements mapped to queries; identifiers per model, batch or item; carriers; public, professional and authority views | Unmapped elements block publication; unauthorized fields never published | MFG-O-DPP-1 | 3 |
| Registration and back-up copy | Registration through the Commission's API inside `publish_passport`, keeping the proof; each passport mirrored to the independent provider; AGT phases the Act | Rejections typed; publication fails unless both copies succeed | MFG-O-DPP-2 | 3 |
| Battery passport | Battery Regulation elements for GP6's pack where in scope [unverified dates] | As mapping | MFG-O-DPP-1 | 4 |
| RoHS, REACH and SCIP | Ten RoHS substances per homogeneous material against Annex II [EU RoHS] [unverified values]; Candidate List above 0.1% w/w, Annex XVII, SCIP data (3); IPC-1752B declarations read in A and B forms [unverified], substances mapped through the package's declarable-substance list | Unknown content reported as unknown, never compliant | MFG-O-REG-1 | 2, 3 |
| 3TG sourcing data | Smelter lists and due-diligence evidence collected for reporting | Data-completeness check only | MFG-O-REG-2 | 3 |
| Other regimes | Packaging, batteries, WEEE marking, TSCA, Proposition 65 [unverified] | As RoHS | MFG-O-REG-1 | 4 |

## State of the art

All numeric goals in the last column are targets.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Adaptive clearing | Constant engagement; parameter-varied trochoids [Li et al. 2025] | Mastercam Dynamic, Fusion adaptive, hyperMILL, NX [unverified] | Medial-axis spiral measured on stock (D-MFG-7), after freedom-to-operate review | Pocket corpus: cycle time within 3% of the best commercial result at equal engagement; zero bound violations |
| 3-axis finishing | Drop- and push-cutter [OpenCAMLib] | ModuleWorks 3-axis library [ModuleWorks] | Anvil `tool_contact` on exact B-rep | Scallop and gouge error on analytic surfaces; throughput at least OpenCAMLib's |
| Collision and NC verification | Continuous collision detection on the posted code | ModuleWorks 5-axis [ModuleWorks]; VERICUT [unverified] | Posted text under declared motion semantics (D-MFG-23); certified per-move gouge distance | Crash corpus: zero false negatives per controller family; time per 1,000 blocks |
| Material removal | Adaptive tri-dexel on GPU [Ozcan et al. 2024] | ModuleWorks GPU simulation, VERICUT [unverified] | Adaptive narrow-band stock (D-MFG-6); tri-dexel as render cache and benchmark candidate | Volume error against exact Booleans; 60 fps scrubbing of a 1-million-block program |
| Feeds and speeds | Mechanistic force models with constrained optimization | CloudNC [CloudNC CAM Assist]; VERICUT Force [unverified] | Source-labelled defaults, advisory model, calibrated optimization (D-MFG-27) | Cycle time within 5% of the leader with zero constraint violations |
| Chatter | Zero-order, multi-frequency, semi-discretization [Altintas et al. 2008] | CUTPRO [Altintas et al. 2008] | Zero-order at `Interactive`, semi-discretization at `SignOff` (D-MFG-10) | Published lobes; time-domain reference |
| Posts | Configurable controller posts | NX Post Configurator, ModuleWorks post framework [ModuleWorks] | One post engine with Ingot hooks and qualification (D-MFG-5) | Re-interpretation; conformance and qualification corpora |
| Target recognition | Panoptic graph segmentation on B-rep [FeatureFox] | AAGNet [FeatureFox] | Design semantics first, then rule and learned recognizers | MFInstSeg panoptic quality at least 97%; above 0.9 with 250 parts |
| AI-assisted programming | Proposals with human review | CloudNC CAM Assist; NX suggestions [Janus NX 2606] | Agents write Ingot on branches; approval over program subjects (D-MFG-4) | Share approved without edits on held-out parts; zero oracle bypasses |
| 2D nesting | Sparrow [Gardeyn et al. 2025] | Sparrow (MIT), jagua-rs (MPL-2.0) | Adopt with deterministic budgets (D-MFG-9) | Within 1 point of sparrow's density at equal work |
| 3D packing | Interlock-free spectral packing [Cui et al. 2023] | Netfabb [Cui et al. 2023]; Magics nester [Materialise Magics] | Integer collision counts (D-MFG-12) | Thingi10K: within 2 points of published density at equal or lower GPU time |
| Slicing | Direct slicing; variable-width beads [Kuipers et al. 2020]; tree supports [OrcaSlicer] | OrcaSlicer, PrusaSlicer (reference only) | Hand-off first (D-MFG-25); direct slicing of every representation (D-MFG-11) | Fill error and print time on the thin-wall corpus no worse than the references; 10× less memory on lattices |
| Multi-axis slicing | Quaternion-field curved layers [Zhang et al. 2022] | Research code [unverified] | Adopt in phase 4 | Support-free coverage and collision-free order on the paper's models |
| Lattices | Implicit, Field-driven lattices | nTop [unverified] | MEC lattices checked and written without meshing | Relative density error under 1% |
| PBF distortion | Inherent strain; layer thermo-mechanics [unverified] | Magics with Ansys [Materialise Magics]; Fusion [Fusion Manufacturing Extension] | Both in Flux with Field-driven compensation (D-MFG-13) | AM-Bench data [NIST AM-Bench 2025]; residual under 0.1 mm on GP2 |
| Injection molding | 3D non-isothermal flow, pvT; ARD-RSC orientation [unverified] | Moldflow [Moldflow] | Level-set 3D at `SignOff`, Hele-Shaw at `Interactive` (D-MFG-15, D-MFG-29) | Analytic cases; GP5 short shots and warpage within 20% of measured |
| Casting | Filling, solidification, dimensionless Niyama [Carlson and Beckermann 2009] | MAGMASOFT [MAGMASOFT] | COV's solidification package, calibrated alloys only | WCB plate porosity; Stefan problem |
| Sheet forming | Incremental shell FEM with compensation | AutoForm [AutoForm] | Flux shells, Field-driven compensation | Published springback benchmarks [unverified] |
| Weld distortion | Inherent strain (structure); transient thermo-mechanics (joint) [unverified] | Simufact Welding, SYSWELD [unverified] | Both in Flux by envelope | GP4 distortion inside the prediction band |
| Assembly planning | Assembly by disassembly [Tian et al. 2022] | Same (research) | Adopt with deterministic search (D-MFG-17) | Paper's benchmark success; 80 parts under 5 minutes |
| Line balancing | BB&R [BB&R] | BB&R | Adopt | All 269 instances optimal, mean under 1 s |
| Robot offline programming | Redundancy-resolved collision-free planning | RoboDK, Process Simulate [unverified] | Robots as Machines sharing CAM kinematics and posts | Re-interpreted programs reproduce motion; cycle time within 10% |
| Inspection | Model-based QIF plans [ISO 23952]; GUM and JCGM 101 [BIPM JCGM] | PC-DMIS, CALYPSO, PolyWorks [unverified] | Provenance identities (D-MFG-18), stable balloons (D-MFG-26), typed budgets | QIF round trip; JCGM examples reproduced exactly |
| Should-cost | Process-model cost from CAD [aPriori] | aPriori | Cost from generated plans, basis labelled (D-MFG-19) | Held-out quotes within the stated interval for 90% of parts |
| Machine connectivity | MTConnect 2.5 [MTConnect 2.5]; OPC 40501-1 [OPC 40501-1] | Vendor MES connectors [unverified] | Read adapters, non-motion job management, signed inputs (D-MFG-20) | Conformance against reference agents and servers |
| PCB handoff | IPC-2581C with DFX [IPC-2581C]; Gerber 2026.05 [Ucamco Gerber downloads] | Siemens Valor NPI [unverified] | IPC-2581C with Gerber X2 by default, ODB++ through ECO's writer (D-MFG-16) | 1 µm XOR against independent readers; seeded-defect boards |
| Life-cycle assessment | ISO 14040 and 14044 process LCA [ISO 14044] | openLCA, SimaPro [unverified] | Inventory from actual process plans | Mass balance; reference product systems |

## Platform notes

- **Identical features.** Strategies, nesting, slicing and simulations are Wasm components or core Rust, so desktop, browser and server run the same code. Large `SignOff` simulations may run on team servers, and every platform starts, inspects and reviews them.
- **Determinism.** Programs, nests and slice contours are canonical results, so NC text is identical on every Tier 1 platform. `correlate_grids` is `Certified` with exact integer counts, and the GPU tri-dexel cache only renders.
- **Browser memory.** Stock grids, voxel grids and large nests stream in tiles. Evaluations above PLT's browser thresholds move to the heavy worker or a server, and the UI says so.
- **Machine access.** Every platform reaches serial, USB and networked devices through the gateway, because Web Serial is not Baseline [MDN Web Serial]. MTConnect, OPC UA and DNC never run inside evaluation.
- **Controller files.** Line endings, character sets, line lengths, size limits and names belong to the `Controller` record; the platform layer writes posted bytes unchanged.
- **Air-gapped shops.** Machine, tool, printer, material and regulation packages install offline; results state the date of every External input used.
- **Tier 2.** Tablets view programs, simulations, instructions and inspection results and approve physical-effect Acts; phones view only (contract 7.6, 9).
- **Licensing.** No LGPL, GPL or AGPL code is linked: PrusaSlicer, OrcaSlicer, CuraEngine, libbgcode, KiCad and OpenCAMLib are external references only. Sparrow, cavalier_contours, i_overlay and Manifold are permissive, Clipper2 is BSL-1.0 [cavalier_contours; i_overlay; Manifold; Clipper2], and jagua-rs and async-opcua are MPL-2.0 under contract 7.7.

## Interfaces with other subsystems

### What MFG consumes

| From | Canonical name or type | Used for |
| --- | --- | --- |
| Anvil | `section`, `offset_curve`, `medial_axis`, `tool_contact`, `swept_volume`, `distance`, `interference`, `deform`, `split`, `extend`, `visibility`, `draft_map`, `thickness`, `voxelize`, `correlate_grids`, `align`, `fit`, `boolean`; wire and `Implicit` Bodies | Every planning capability, at Anvil's phases |
| Flux | Modal analysis; element activation and inherent-strain prediction; thermo-elasto-plasticity; level-set free-surface flow and Hele-Shaw; shells, rigid-body contact, sensitivities; constrained topology optimization | Process physics; manufacturing constraints in design optimization |
| COV | Process models, `ValidityEnvelope`s and state Fields for cutting, melts, cast alloys, forming, transformation and cure; solidification and current-distribution packages on Flux forms; OOR-8; per-material `EnvironmentalRecord`s | Envelope checks; product LCA |
| MEC | Kinematic mates; `FlatPattern` and `export_flat_dxf`; `HoleSpec`, `ThreadSpec`, `Weld` with quality level; ply flats; core and cavity from `split_mold`; `lattice`; gear records; PMI; characteristic balloons that draw MFG's labels; harness geometry | Machines, forming, joining, molds, inspection |
| ELX | The board model (layers, stackup, classes, netlist, footprints, placements, `test_point` features, rules); the DRC engine; harness package data; findings shown on board objects | Electronics and harness handoff |
| KLN and `repo` | Items and revisions (programs among them, contract 2), late-bound fields, effectivity, BOM views, where-used, change orders and MCOs (D-KLN-38), parts policy, serials, recipient records, Evidence pins | Release, routings, FAI, as-built |
| AGT and `api` | Physical-effect and data-release Act classes with Approvals; `read.machine_data`; Proposals; the CAM programmer and cost engineer roles (phase 2) | Transfers, quotes, passports, agent programs |
| ECO | Manufacturing, board and tool-data readers and writers in `io/` (3MF, IPC-2581, Gerber, ODB++, QIF, STEP-NC, USD, ISO 13399 tool data) at ECO's phases; `parts::` publishing and the offer schema; NC migration; `crucible:connect` worlds; registry packages | Outputs, imports and packages |
| UIX | The Manufacture preset: toolpath playback, NC code panel with `BlockMap` highlighting, setup-sheet preview, cost panel | Review |
| PLT | Gateway packaging, serial and USB access, device keys, browser memory table | Connectivity |
| ING | Records, enums, `Map`, `Range` as interval, `Decimal` and `Money<C>`, `require`, kinds for parameter domains | Every Ingot interface |

### What MFG provides

| To | Provided | Type |
| --- | --- | --- |
| All tabs | `std::mfg` packages: `core`, `machining`, `am`, `molding`, `casting`, `forming`, `joining`, `treatment`, `electronics`, `assembly`, `inspection`, `cost`, `sourcing`, `factory`, `sustainability` | Ingot packages |
| MEC | Process profiles with Cp and Cpk, tooling minimums and press-brake allowance data, process cost models, characteristic identities and balloon labels (D-MFG-18, D-MFG-26), the harness manufacturing package, DFM, DFA and DfAM checks | `Check`, `Field`, packages |
| FLX | Process profiles for FLX's manufacturing-constraint forms (overhang angle, build and draw direction, minimum feature size), with Cp and Cpk; inherent-strain calibration data | `Field`, packages |
| COV | Process setups and data for the process capabilities MFG owns (contract 13.4) | Packages |
| ELX | Fabricator and assembler rule packs by class; the package choice, written by ECO; panels, stencils and test programs; DFX feedback; the harness manufacturing package | `Check`, packages |
| KLN and `repo` | Program subjects with simulation evidence; MBOM rules and routings; setup sheets, work instructions and inspection plans; as-built records and QIF results; substance rules | CAS objects |
| AGT | Act payloads for `send_to_machine`, `send_robot_program`, `store_machine_job`, `send_print_job`, `start_print`, `request_quote`, `publish_passport`; DFM rules, CAM, cost with intervals, the re-verifying gateway with edit capture and printer profiles for agent roles; `MfgError` fixes | Act plans, plain values |
| UIX | Toolpaths, stock, collisions, NC text with `BlockMap`, `setup_sheet`, DfAM check Fields and the 3MF build layout, cost lines and carbon Fields | `Body`, `Field` |
| ECO | The factory handoff; machine, tool and toolpath models; `verify_nc`; offer usage; partner flows; `crucible:mfg` worlds (`toolpath-strategy`, `post-processor`, nesting, packing, slicers, recognizers); machine-connector interfaces | WIT interfaces, packages |

```rust
// crates: std/mfg-wit, std/mfg-post, io/stepnc, io/qif, io/mtconnect, io/opcua-mfg, io/usd-factory, oracles/mfg
pub trait Strategy {
    fn generate(&self, req: &StrategyRequest) -> Result<Toolpath, MfgError>;
}
pub trait Post {
    fn post(&self, program: &Program, machine: &Machine) -> Result<(NcText, BlockMap), MfgError>;
}
pub trait NcInterpreter {   // two independent implementations: product (verify_nc) and oracle
    fn interpret(&self, text: &NcText, machine: &Machine) -> Result<Vec<Motion>, InterpretError>;
}
```

## Oracles

Oracles live in `oracles/mfg/`, which agents read but never write; held-out parts, programs, nests and measurements are never shown to agents.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| MFG-O-CORE-1 | Core records and fixes | Every artifact is a Body, Field, Assembly or plain value; every seeded failure carries a fix that clears it or says why not |
| MFG-O-CORE-2 | Outside data | Every External input and Evidence record a result read appears by `ObjectId` in its `CheckOutcome` |
| MFG-O-CORE-3 | Toolpath storage | 10⁷ moves under 400 MB (target); single moves addressable |
| MFG-O-DET-1 | Determinism | Identical programs, nests, builds and reports on every Tier 1 target |
| MFG-O-LABEL-1 | Label invariance | Plans and costs of GP1 to GP3 identical after re-randomizing every name |
| MFG-O-SAFE-1 | Subjects and change lane | Edits inside a subject void Approvals, rebases and re-runs do not; MCOs touching EBOM definitions rejected; a part change invalidates exactly its dependent programs |
| MFG-O-SAFE-2 | Transfers and print starts | A seeded corpus of unapproved, hash-mismatched, phone-approved or unconfirmed requests is refused 100% |
| MFG-O-SAFE-3 | No motion | Connector WIT worlds expose no motion or start method (the static interface is the product boundary) |
| MFG-O-SAFE-4 | Offsets and edits | Seeded offset mismatches blocked 100%; recorded edit sessions yield Proposals with exact diffs |
| MFG-O-SAFE-5 | DNC | Drip feed against controller simulators stops and reports every injected fault |
| MFG-O-KIN-1 | Kinematics | `fk` against a screw-theory implementation on 10,000 poses under 10⁻¹² m; `fk(ik(p))` equals `p` within 10⁻⁹ |
| MFG-O-KIN-2 | Singularities and limits | No unreported branch flip; tip deviation, axis derivatives, power and torque under their bounds |
| MFG-O-POST-1 | Posts | An independent interpreter reproduces each posted program; family corpora match vendor simulators where licensed and real controls at the reference shop |
| MFG-O-POST-2 | Configuration and hooks | Golden posted files for each configuration and hook set |
| MFG-O-POST-3 | Qualification | Reference programs equal the shops' proven programs modulo the declared list |
| MFG-O-POST-4 | Diff and block map | Self-diff empty; known edits found; every block maps to a toolpath point |
| MFG-O-TOOL-1 | Tools | Vendor package round trip within 1 µm with properties unchanged; gauge length equals the analytic stack-up; conflicting table entries fail |
| MFG-O-TOOL-2 | Tool life | Predicted changes against as-run records |
| MFG-O-STOCK-1 | Stock | Removed volume equals integrated swept volume within the bound; rest plus part covers stock; hand-off transforms exact |
| MFG-O-SETUP-1 | Stations and setup sheets | Tombstone corpus verified per work offset; posted offsets and every tool, with analytic gauge length, appear once on the sheet |
| MFG-O-SETUP-2 | Jaws and probing | Parts seat without interference; probe paths collision-free |
| MFG-O-SETUP-3 | Fixtures | Rank tests on 3-2-1 cases; equilibrium and deflection within tolerance; access clear |
| MFG-O-MILL-1 | 2.5D and rest | No material above floor plus allowance; rest Body empty after the pass |
| MFG-O-MILL-2 | Engagement | An independent stock simulator keeps engagement and chip thickness under bound plus tolerance |
| MFG-O-MILL-3 | Finishing | Scallop Field under target; certified gouge check passes |
| MFG-O-MILL-4 | Edges, threads, holes | Chamfer size, thread profile, hole depth and position on simulated stock |
| MFG-O-MILL-5 | 5-axis | Wall deviation within tolerance; machine collision passes; axis smoothness bounds hold |
| MFG-O-TURN-1 | Turning | Revolved profile equals the part; simulated profile within allowance |
| MFG-O-TURN-2 | Multi-channel | Schedules collision-free with synchronization honored; optimal on small instances |
| MFG-O-EDM-1 | EDM | Kerf and ruled surfaces within tolerance; electrode plus gap reproduces the cavity |
| MFG-O-GEAR-1 | Gear cutting and grinding | Simulated flanks within the design's quality grade; ground profiles within allowance |
| MFG-O-GEAR-2 | Gear inspection | Plans evaluate the design flank on reference gears |
| MFG-O-CUT-1 | Profile cutting | Kerf, taper, bevel and punched sheet match the part; tour against a lower bound |
| MFG-O-CUT-2 | Flat-pattern hand-off | Each shop convention maps every flat-pattern entity; re-import equals the flat pattern; layers follow the convention |
| MFG-O-CUT-3 | Press brake | Bend simulation collision-free; optimal on small instances |
| MFG-O-NEST-1 | Nests | Exact overlap, rule and containment checks; remnant plus parts plus kerf equals the sheet; warm starts never worsen; density target on ESICUP and GARDEYN |
| MFG-O-FEED-1 | Cutting data | Labels match sources; calibrated coefficients reproduce calibration cuts within uncertainty |
| MFG-O-FEED-2 | Constraint check | Predicted power matches measured; independent recomputation finds no missed violation |
| MFG-O-FEED-3 | Optimization | Zero violations; cycle time within 5% of the leader on the shared benchmark |
| MFG-O-CHAT-1 | Stability | Published FRFs and lobes; time-domain agreement; segments below lobe minus margin; recorded chatter flagged |
| MFG-O-SIM-1 | Gouges | Every planted gouge found with its depth |
| MFG-O-SIM-2 | Collision | Ordinary and controller-semantics crash corpora detected 100% per family; undeclared semantics never pass |
| MFG-O-SIM-3 | External NC | Hand-written and third-party programs with planted crashes all detected |
| MFG-O-SIM-4 | Cycle time | Within 5% of measured after calibration (target) |
| MFG-O-SIM-5 | Viewer | Visual regression Snapshots under a fixed `RenderProfile` |
| MFG-O-PROG-1 | Regeneration | Unchanged designs keep every `ObjectId`; identical programs diff empty |
| MFG-O-PROG-2 | Templates and setups | Golden programs for template parts; deterministic ranking; each target in exactly one setup |
| MFG-O-PROG-3 | Recognition | Panoptic quality targets on MFInstSeg |
| MFG-O-PROG-4 | Agent programs | Held-out agent Proposals pass every oracle; zero bypasses |
| MFG-O-PROG-5 | STEP-NC | Schema validation; round trips exact or within AP242 tolerance |
| MFG-O-AM-1 | Orientation | Objectives recomputed; brute force on small grids |
| MFG-O-AM-2 | Slicer hand-off | Each named slicer opens the 3MF with plates, orientation and settings intact |
| MFG-O-AM-3 | Nesting and packing | Exact clearance and translational removability |
| MFG-O-AM-4 | Supports and labels | Every overhang and island supported; removal access; labels legible on sliced layers |
| MFG-O-AM-5 | DfAM and lattices | Seeded-defect corpus per check: every defect found, no clean region flagged; as-built struts against sections |
| MFG-O-AM-6 | Slices | Layer area equals integrated cross-section within the bound; contours closed; bead fill ratio; DED deposition against target |
| MFG-O-AM-7 | Distortion prediction | Coupon deflection; AM-Bench residual stress and deflection where data exist [NIST AM-Bench 2025] |
| MFG-O-AM-8 | Compensation | Re-simulated build within tolerance; metal PBF build of GP2 within 0.1 mm in phase 2 |
| MFG-O-AM-9 | Cure, sintering, warp | AM-Bench cure depth; measured shrinkage and warp coupons |
| MFG-O-AM-10 | 3MF | Consortium validation and round trip |
| MFG-O-AM-11 | Printer data | bgcode decodes to the same moves with an independent reader; calibration prints reproduce recorded values |
| MFG-O-MOLD-1 | Moldability and split | Analytic draft; seeded undercuts; core plus cavity plus part equals the block |
| MFG-O-MOLD-2 | Mold design | Opening collision-free; pin stress, fill imbalance and steel distance within limits; coolant flow turbulent |
| MFG-O-MOLD-3 | Flow | Center-gated disk and power-law Hele-Shaw solutions; mass conserved within 0.1% |
| MFG-O-MOLD-4 | Orientation and warpage | A published plaque benchmark [unverified which]; GP5 short shots and warpage |
| MFG-O-CAST-1 | Casting design | Pattern minus allowances equals the part; velocities and moduli recomputed |
| MFG-O-CAST-2 | Casting simulation | Stefan problem; energy balance per cycle; WCB plate porosity |
| MFG-O-BULK-1 | Bulk forming | Published die-fill and load benchmarks; thickness against measured parts |
| MFG-O-FORM-1 | Tube bending | Collision-free simulation; measured tubes |
| MFG-O-FORM-2 | Forming | Published formability and springback benchmarks [unverified]; continuity and tonnage recomputed |
| MFG-O-JOIN-1 | Weld procedures | Every joint has a qualified procedure and quality level; pass areas sum to the joint |
| MFG-O-JOIN-2 | Weld distortion | GP4 measured distortion inside the prediction band; published joint-scale benchmarks [unverified] |
| MFG-O-JOIN-3 | Fastening and bonding | Preload range contains MEC's requirement; pitch, edge and access rules; bead volume equals bondline |
| MFG-O-JOIN-4 | Composites | Every ply placed once in order; gaps and overlaps within limits; spring-in on L-sections |
| MFG-O-TREAT-1 | Coatings | Every treated face resolved; dimensions recomputed; plating cases and film thickness |
| MFG-O-TREAT-2 | Heat treatment | Targets within COV bands; measured distortion on golden parts |
| MFG-O-PCB-1 | Fabrication packages | Each package holds every file its fabricator profile requires; independent readers and a 1 µm XOR against the board are empty; writer conformance, ODB++ against KiCad's writer included, is ECO-O-25 |
| MFG-O-PCB-2 | Assembly outputs | Placement from the 3D Assembly within 0.01 mm and 0.1° |
| MFG-O-PCB-3 | Classes and drawing | Each class selects its rule pack; notes equal the board values |
| MFG-O-PCB-4 | Panels, stencils, reflow | Panel rules hold; area ratios recomputed; profile inside every part's rating |
| MFG-O-PCB-5 | DFM and DFA | Seeded-defect boards: every defect found |
| MFG-O-PCB-6 | Test | Coverage recomputed from the netlist; proposed points reach every accessible net |
| MFG-O-HARN-1 | Harness package | Cut list, terminals and test netlist match ELX connectivity; formboard lengths match MEC |
| MFG-O-ASM-1 | Sequences | Every motion replayed collision-free; optimum on small instances; each fastener in one step |
| MFG-O-ASM-2 | DFA | Known minimum part counts; times trace to table rows |
| MFG-O-ASM-3 | Instructions | Every MBOM item consumed; schema and accessibility checks; unchanged designs diff empty |
| MFG-O-ASM-4 | Robots | Replayed paths collision-free; posts reproduce motion; no safety-configuration output |
| MFG-O-ASM-5 | Line balancing | All 269 benchmark instances optimal; bounds reported |
| MFG-O-INSP-1 | Characteristics | Each GD&T control yields one characteristic; a one-dimension revision changes one balloon's content and no labels; Form 3 rows equal the balloons |
| MFG-O-INSP-2 | Methods and CMM | Uncertainty ratios recomputed; paths collision-free on the CMM model |
| MFG-O-INSP-3 | Results | Public QIF samples round trip; records signed and pinned |
| MFG-O-INSP-4 | Evaluation and scans | Reference fitting sets in the style of ISO 10360-6 [unverified]; known transforms recovered |
| MFG-O-INSP-5 | Uncertainty | JCGM worked examples reproduced; analytic risk cases; calibrated artifacts |
| MFG-O-QUAL-1 | SPC, MSA, capability | Published chart, capability and gauge R&R examples reproduced exactly |
| MFG-O-QUAL-2 | FAI | Revision C fields complete; seeded changes give the expected partial scope; genealogy queries complete |
| MFG-O-QUAL-3 | PPAP and FMEA | Element completeness per level; every special characteristic controlled |
| MFG-O-COST-1 | Parametric cost | Held-out quotes within the interval for 90% of parts (target) |
| MFG-O-COST-2 | Planned cost | Hand-computed reference parts per process |
| MFG-O-COST-3 | Roll-ups | Roll-up equals the sum; allocations sum to targets; currency mixing fails to compile |
| MFG-O-COST-4 | Quotes | Mock supplier endpoints; requests only inside Acts |
| MFG-O-SRC-1 | Suppliers | Signatures checked; seeded mismatches detected; alternates' checks pass |
| MFG-O-SRC-2 | Decisions and risk | Decisions recomputed from inputs; seeded risks surfaced |
| MFG-O-FAC-1 | Gateway | Offline replay; records signed by the device key |
| MFG-O-FAC-2 | Adapters | Reference agents and servers with recorded streams |
| MFG-O-FAC-3 | MES and ERP | Mock-endpoint round trip with idempotent replay |
| MFG-O-FAC-4 | MBOM and routings | Every EBOM item consumed once; times trace to programs; one routing per serial |
| MFG-O-FAC-5 | USD and twin export | Core 1.0 validation; transforms and animation within tolerance |
| MFG-O-FAC-6 | As-built | Complete genealogy for test serials |
| MFG-O-FAC-7 | Calibration | Updated models predict held-out runs better, otherwise rejected |
| MFG-O-SUST-1 | Carbon and inventory | Roll-up equals the sum; mass balance per routing step |
| MFG-O-SUST-2 | Impact | Reference product systems; contributions sum to the total |
| MFG-O-SUST-3 | Circularity | Streams plus losses equal product mass; paths replayed |
| MFG-O-DPP-1 | Passport mapping | Every element mapped or justified as not applicable; carriers decode |
| MFG-O-DPP-2 | Publication | Test-registry round trip; back-up copy present at the second provider |
| MFG-O-REG-1 | Restricted substances | Seeded BOMs: every planted case reported with part, material and rule |
| MFG-O-REG-2 | 3TG data | Missing evidence reported; no compliance verdict emitted |
| MFG-O-GOLD-1 | Golden products | GP1 and GP2 costs and DfAM verdicts; GP3 parts cut from Crucible programs; GP4 distortion; GP5 warpage and board; GP6 build records and passport |

## Phasing

MFG-O-GOLD-1 collects the gate evidence below. Shared physics capabilities take their phase from contract 13.4, as the capability tables state; press-brake allowance data and metal PBF compensation keep MFG's phase 2.

| Phase | MFG contribution to the gate |
| --- | --- |
| 0 | Core types, `MfgError`, seeded search rules and the protected oracle directory; no manufacturing gate evidence |
| 1 | GP1: coating specification, parametric cost and BOM roll-up; the shop programs with its own CAM. GP2: DfAM and lattice checks, orientation, 3MF production output with beam lattices, slicer hand-off, inherent-strain prediction, AM cost. Deferred per contract 13.2: CAM, posts, stock simulation, slicing and nesting |
| 2 | GP3: Crucible CAM (2.5D and 3-axis, adaptive after the opinion, drilling, turning, gear generating), Fanuc, Haas, Siemens and Heidenhain posts, stock and posted-code simulation, `verify_nc`, setup sheets, tools, fixtures, transfer Acts, gateway, DNC. GP4: profile cutting, nesting, press brake, weld procedures and structure-scale distortion. One additive part through Crucible's slicer. Also metal PBF compensation |
| 3 | GP5: mold design, filling, orientation and warpage; board fabrication, assembly and test packages; CMM, SPC, MSA and AS9102. Also simultaneous 5-axis, stability lobes, MTConnect and OPC UA reads, and passport publication |
| 4 | GP6: harness package, composites layup and battery passport. Also joint-scale weld simulation, PBF thermo-mechanics, PPAP and MES mapping |
| 5 and later | Sheet forming, springback and plating current distribution (5); bulk forming; casting simulation and heat-treatment distortion (6) |

## Open questions

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

## Contract change requests

- CCR-MFG-5, one list of physical-effect Acts: accepted in contract v5; contract 2 (Act) and 7.6 (Physical safety).
- CCR-MFG-6, `unattended_safe` excludes machines that cut or move: accepted in contract v5; contract 7.1 (Hardware CI).

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
- [US 9,164,503] https://patents.google.com/patent/US9164503 and https://patents.google.com/patent/US9164503B2/en
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
- [ISA-95 Job Control] OPC 10031-4, ISA-95 Job Control, section 6.3: https://reference.opcfoundation.org/ISA95JOBCONTROL/v200/docs/6.3
- [OPC 40001-3] OPC UA for Machinery, Part 3: Job Management, 1.0.1: https://reference.opcfoundation.org/Machinery/Jobs/v100/docs/
- [MTConnect 2.5 Part 3] MTConnect Part 3, Observation Information Model, 2.5.0: https://docs.mtconnect.org/MBSD_MTConnect_Part_3_2-5-0.pdf
- [EU Machinery] European Commission, Machinery: https://single-market-economy.ec.europa.eu/sectors/mechanical-engineering/machinery_en
- [Bambu Lab 2025] Bambu Lab, "Firmware update introducing new authorization control system", 16 January 2025: https://blog.bambulab.com/firmware-update-introducing-new-authorization-control-system-2/
- [libbgcode] https://github.com/prusa3d/libbgcode
- [Ucamco Gerber downloads] https://www.ucamco.com/en/gerber/downloads
- [KiCad 9.0] KiCad 9.0.0 release notes: https://www.kicad.org/blog/2025/02/Version-9.0.0-Released/
- [AIAG PPAP] https://www.aiag.org/training-and-resources/manuals/details/PPAP-4
- [AIAG-VDA FMEA] https://www.aiag.org/training-and-resources/manuals/details/FMEAAV-1
- [EUR-Lex 2026/1778] Commission Implementing Regulation (EU) 2026/1778: https://eur-lex.europa.eu/eli/reg_impl/2026/1778/oj
- [EUR-Lex 2026/1736] Commission Implementing Decision (EU) 2026/1736: https://eur-lex.europa.eu/eli/dec_impl/2026/1736/oj
